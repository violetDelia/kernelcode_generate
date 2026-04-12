"""decompass pass。

创建者: 朽木露琪亚
最后一次更改: jcc你莫辜负

功能说明:
- 将 `func.func` 内已注册的 `nn.*` op 按 decompass 规则分解。
- 内置 `nn.softmax` 固定展开为 `nn.reduce_max -> nn.broadcast -> nn.sub -> nn.exp -> nn.reduce_sum -> nn.broadcast -> nn.truediv`。
- 在 pass 内把 `axis` 规整为非负下标，并显式拒绝越界 axis。
- 仅停留在 `nn` 方言层，不承担 `nn -> kernel` lowering。

使用示例:
- from kernel_gen.passes.lowering.decompass import DecompassPass
- module = DecompassPass().run(module)

关联文件:
- spec: spec/pass/lowering/decompass.md
- test: test/pass/test_decompose_nn_softmax.py
- 功能实现: kernel_gen/passes/lowering/decompass.py
"""

from __future__ import annotations

from collections.abc import Callable, Sequence

from xdsl.dialects import func
from xdsl.dialects.builtin import ArrayAttr, IntAttr, ModuleOp, StringAttr
from xdsl.ir import Attribute, Block, Operation, Region, SSAValue
from xdsl.utils.exceptions import VerifyException

from kernel_gen.dialect.nn import (
    NnBroadcastOp,
    NnExpOp,
    NnMemoryType,
    NnReduceMaxOp,
    NnReduceSumOp,
    NnSoftmaxOp,
    NnSubOp,
    NnTrueDivOp,
)
from ..pass_manager import Pass

DecompassRewrite = Callable[[Operation, Block], None]


class DecompassError(ValueError):
    """`decompass` pass 的显式错误。

    创建者: jcc你莫辜负
    最后一次更改: jcc你莫辜负

    功能说明:
    - 用于输出可机械匹配的错误短语，避免吞掉具体错误入口。

    使用示例:
    - raise DecompassError("DecompassError: normalized axis out of range")

    关联文件:
    - spec: spec/pass/lowering/decompass.md
    - test: test/pass/test_decompose_nn_softmax.py
    - 功能实现: kernel_gen/passes/lowering/decompass.py
    """


def _attr_product(factors: Sequence[Attribute]) -> Attribute:
    """把一组 shape 因子规整为 stride attribute。

    创建者: jcc你莫辜负
    最后一次更改: jcc你莫辜负

    功能说明:
    - 支持 IntAttr 与 StringAttr 组合，确保 stride 构造过程可处理符号维度。

    使用示例:
    - _ = _attr_product([IntAttr(2), StringAttr("B")])

    关联文件:
    - spec: spec/pass/lowering/decompass.md
    - test: test/pass/test_decompose_nn_softmax.py
    - 功能实现: kernel_gen/passes/lowering/decompass.py
    """

    int_product = 1
    expr_parts: list[str] = []
    for factor in factors:
        if isinstance(factor, IntAttr):
            int_product *= factor.data
            continue
        if isinstance(factor, StringAttr):
            expr_parts.append(factor.data)
            continue
        raise DecompassError(
            "DecompassError: shape entries must be IntAttr or StringAttr"
        )

    if not expr_parts:
        return IntAttr(int_product)

    parts: list[str] = []
    if int_product != 1:
        parts.append(str(int_product))
    parts.extend(part for part in expr_parts if part != "1")
    if not parts:
        return IntAttr(1)
    return StringAttr("*".join(parts))


def _build_contiguous_stride(shape: Sequence[Attribute]) -> ArrayAttr[Attribute]:
    """按 shape 生成连续布局 stride。

    创建者: jcc你莫辜负
    最后一次更改: jcc你莫辜负

    功能说明:
    - 以紧致布局规则生成 stride，满足 keepdim=true 的 reduce 输出要求。

    使用示例:
    - _ = _build_contiguous_stride([IntAttr(2), IntAttr(3)])

    关联文件:
    - spec: spec/pass/lowering/decompass.md
    - test: test/pass/test_decompose_nn_softmax.py
    - 功能实现: kernel_gen/passes/lowering/decompass.py
    """

    suffix_factors: list[Attribute] = []
    strides: list[Attribute] = []
    for dim in reversed(shape):
        strides.append(_attr_product(suffix_factors))
        suffix_factors.insert(0, dim)
    strides.reverse()
    return ArrayAttr(strides)


def _build_reduce_result_type(input_type: NnMemoryType, axis: int) -> NnMemoryType:
    """构造 keepdim=true 的 reduce 结果类型。

    创建者: jcc你莫辜负
    最后一次更改: jcc你莫辜负

    功能说明:
    - 把指定 axis 的 shape 维度改成 1，并生成对应连续布局 stride。

    使用示例:
    - _ = _build_reduce_result_type(input_type, axis=1)

    关联文件:
    - spec: spec/pass/lowering/decompass.md
    - test: test/pass/test_decompose_nn_softmax.py
    - 功能实现: kernel_gen/passes/lowering/decompass.py
    """

    result_shape = list(input_type.shape.data)
    result_shape[axis] = IntAttr(1)
    return NnMemoryType(
        ArrayAttr(result_shape),
        _build_contiguous_stride(result_shape),
        input_type.element_type,
        input_type.space,
    )


def _normalize_axis(axis: int, rank: int) -> int:
    """把 softmax axis 规整为非负下标。

    创建者: jcc你莫辜负
    最后一次更改: jcc你莫辜负

    功能说明:
    - 对负轴执行 rank + axis 规整，并在越界时抛出固定错误短语。

    使用示例:
    - assert _normalize_axis(-1, 3) == 2

    关联文件:
    - spec: spec/pass/lowering/decompass.md
    - test: test/pass/test_decompose_nn_softmax.py
    - 功能实现: kernel_gen/passes/lowering/decompass.py
    """

    normalized = axis if axis >= 0 else rank + axis
    if normalized < 0 or normalized >= rank:
        raise DecompassError("DecompassError: normalized axis out of range")
    return normalized


def _ensure_operand_and_result_types(op: NnSoftmaxOp) -> tuple[NnMemoryType, NnMemoryType]:
    """校验 softmax operand/result 基础类型。

    创建者: jcc你莫辜负
    最后一次更改: jcc你莫辜负

    功能说明:
    - 确保 operand/result 都为 nn.memory，避免对非法类型继续生成分解链。

    使用示例:
    - _ = _ensure_operand_and_result_types(softmax_op)

    关联文件:
    - spec: spec/pass/lowering/decompass.md
    - test: test/pass/test_decompose_nn_softmax.py
    - 功能实现: kernel_gen/passes/lowering/decompass.py
    """

    input_type = op.input.type
    result_type = op.result.type
    if not isinstance(input_type, NnMemoryType) or not isinstance(result_type, NnMemoryType):
        raise DecompassError(
            "DecompassError: operand and result must be nn.memory"
        )
    return input_type, result_type


def _ensure_softmax_result_matches_input(op: NnSoftmaxOp) -> tuple[NnMemoryType, NnMemoryType]:
    """校验 softmax 结果类型与输入 shape/stride 一致。

    创建者: jcc你莫辜负
    最后一次更改: jcc你莫辜负

    功能说明:
    - 软约束 softmax 输出类型与输入一致，避免产生半合法 IR。

    使用示例:
    - _ = _ensure_softmax_result_matches_input(softmax_op)

    关联文件:
    - spec: spec/pass/lowering/decompass.md
    - test: test/pass/test_decompose_nn_softmax.py
    - 功能实现: kernel_gen/passes/lowering/decompass.py
    """

    input_type, result_type = _ensure_operand_and_result_types(op)
    if input_type.shape != result_type.shape or input_type.stride != result_type.stride:
        raise DecompassError(
            "DecompassError: result type must match input shape and stride"
        )
    return input_type, result_type


def _verify_new_ops(ops: Sequence[Operation]) -> None:
    """逐个验证新生成的分解 op。

    创建者: jcc你莫辜负
    最后一次更改: jcc你莫辜负

    功能说明:
    - 使用方言 verifier 校验新 op，失败时转为 DecompassError。

    使用示例:
    - _verify_new_ops([max_op, exp_op])

    关联文件:
    - spec: spec/pass/lowering/decompass.md
    - test: test/pass/test_decompose_nn_softmax.py
    - 功能实现: kernel_gen/passes/lowering/decompass.py
    """

    for op in ops:
        try:
            op.verify()
        except VerifyException as exc:
            raise DecompassError(f"DecompassError: {exc}") from exc


def _decompose_softmax_op(op: NnSoftmaxOp, block: Block) -> None:
    """把单个 `nn.softmax` 展开为固定 7 段链。

    创建者: jcc你莫辜负
    最后一次更改: jcc你莫辜负

    功能说明:
    - 按固定顺序生成 reduce_max/broadcast/sub/exp/reduce_sum/broadcast/truediv。
    - 替换原 softmax 结果并移除原 op。

    使用示例:
    - _decompose_softmax_op(softmax_op, block)

    关联文件:
    - spec: spec/pass/lowering/decompass.md
    - test: test/pass/test_decompose_nn_softmax.py
    - 功能实现: kernel_gen/passes/lowering/decompass.py
    """

    input_type, result_type = _ensure_softmax_result_matches_input(op)
    rank = len(input_type.shape.data)
    normalized_axis = _normalize_axis(op.axis.value.data, rank)
    reduce_type = _build_reduce_result_type(input_type, normalized_axis)

    max_op = NnReduceMaxOp(op.input, reduce_type, axes=[normalized_axis], keepdim=True, space=op.space)
    max_broadcast = NnBroadcastOp(max_op.result, result_type, op.space)
    sub_op = NnSubOp(op.input, max_broadcast.result, result_type, op.space)
    exp_op = NnExpOp(sub_op.result, result_type, op.space)
    sum_op = NnReduceSumOp(exp_op.result, reduce_type, axes=[normalized_axis], keepdim=True, space=op.space)
    sum_broadcast = NnBroadcastOp(sum_op.result, result_type, op.space)
    div_op = NnTrueDivOp(exp_op.result, sum_broadcast.result, result_type, op.space)
    new_ops = [max_op, max_broadcast, sub_op, exp_op, sum_op, sum_broadcast, div_op]

    _verify_new_ops(new_ops)
    block.insert_ops_before(new_ops, op)
    op.result.replace_by(div_op.result)
    block.erase_op(op)


def _rewrite_softmax_op(op: Operation, block: Block) -> None:
    """按 decompass 合同分解 `nn.softmax`。

    创建者: 小李飞刀
    最后一次更改: 小李飞刀

    功能说明:
    - 统一 decompass 注册重写入口，确保按 op 名称分发后仍能做类型校验。

    使用示例:
    - _rewrite_softmax_op(softmax_op, block)

    关联文件:
    - spec: spec/pass/lowering/decompass.md
    - test: test/pass/test_decompose_nn_softmax.py
    - 功能实现: kernel_gen/passes/lowering/decompass.py
    """

    if not isinstance(op, NnSoftmaxOp):
        raise DecompassError("DecompassError: nn.softmax rewrite expects NnSoftmaxOp")
    _decompose_softmax_op(op, block)


_DECOMPASS_REWRITES: dict[str, DecompassRewrite] = {"nn.softmax": _rewrite_softmax_op}


def register_decompass_rewrite(op_name: str, rewrite: DecompassRewrite) -> None:
    """注册 decompass 重写规则。

    创建者: 小李飞刀
    最后一次更改: 小李飞刀

    功能说明:
    - 支持为其它 op 追加分解重写逻辑。
    - 已存在同名规则时按最新规则覆盖。

    使用示例:
    - register_decompass_rewrite("nn.some_op", rewrite_fn)

    关联文件:
    - spec: spec/pass/lowering/decompass.md
    - test: test/pass/test_decompose_nn_softmax.py
    - 功能实现: kernel_gen/passes/lowering/decompass.py
    """

    op_name_trimmed = op_name.strip()
    if not op_name_trimmed:
        raise DecompassError("DecompassError: op name must be non-empty")
    _DECOMPASS_REWRITES[op_name_trimmed] = rewrite


def _try_rewrite_registered_op(op: Operation, block: Block) -> None:
    """尝试按注册表分解 op。

    创建者: jcc你莫辜负
    最后修改人: 金铲铲大作战

    功能说明:
    - 按 op.name 查找已注册的分解规则并执行。
    - 未命中注册表时保持原样返回。

    使用示例:
    - _try_rewrite_registered_op(op, block)

    关联文件:
    - spec: spec/pass/lowering/decompass.md
    - test: test/pass/test_decompose_nn_softmax.py
    - 功能实现: kernel_gen/passes/lowering/decompass.py
    """

    rewrite = _DECOMPASS_REWRITES.get(op.name)
    if rewrite is None:
        return
    rewrite(op, block)


def _decompose_block(block: Block) -> None:
    """递归处理 block 内部全部已注册分解 op。

    创建者: jcc你莫辜负
    最后一次更改: jcc你莫辜负

    功能说明:
    - 对 block 内 op 递归处理 region，并替换命中的已注册分解 op。

    使用示例:
    - _decompose_block(block)

    关联文件:
    - spec: spec/pass/lowering/decompass.md
    - test: test/pass/test_decompose_nn_softmax.py
    - 功能实现: kernel_gen/passes/lowering/decompass.py
    """

    for op in list(block.ops):
        for region in op.regions:
            _decompose_region(region)
        _try_rewrite_registered_op(op, block)


def _decompose_region(region: Region) -> None:
    """递归处理 region。

    创建者: jcc你莫辜负
    最后一次更改: jcc你莫辜负

    功能说明:
    - 遍历 region 内 block，调用 block 级分解。

    使用示例:
    - _decompose_region(region)

    关联文件:
    - spec: spec/pass/lowering/decompass.md
    - test: test/pass/test_decompose_nn_softmax.py
    - 功能实现: kernel_gen/passes/lowering/decompass.py
    """

    for block in region.blocks:
        _decompose_block(block)


def _decompose_module(module: ModuleOp) -> None:
    """仅在 `func.func` 内执行 decompass 分解。

    创建者: jcc你莫辜负
    最后一次更改: jcc你莫辜负

    功能说明:
    - 限定 pass 只处理 func.func 内的已注册分解 op，避免影响其他方言结构。

    使用示例:
    - _decompose_module(module)

    关联文件:
    - spec: spec/pass/lowering/decompass.md
    - test: test/pass/test_decompose_nn_softmax.py
    - 功能实现: kernel_gen/passes/lowering/decompass.py
    """

    for op in module.ops:
        if isinstance(op, func.FuncOp):
            _decompose_region(op.body)


class DecompassPass(Pass):
    """执行 decompass 分解链。

    创建者: jcc你莫辜负
    最后一次更改: jcc你莫辜负

    功能说明:
    - 在 ModuleOp 的 func.func 内识别已注册 op，并替换为对应分解链。

    使用示例:
    - module = DecompassPass().run(module)

    关联文件:
    - spec: spec/pass/lowering/decompass.md
    - test: test/pass/test_decompose_nn_softmax.py
    - 功能实现: kernel_gen/passes/lowering/decompass.py
    """

    name = "decompass"

    def run(self: "DecompassPass", module: Operation) -> Operation:
        """执行 `decompass` pass。

        创建者: jcc你莫辜负
        最后一次更改: jcc你莫辜负

        功能说明:
        - 校验 module 类型，随后执行 decompass 分解。

        使用示例:
        - _ = DecompassPass().run(module)

        关联文件:
        - spec: spec/pass/lowering/decompass.md
        - test: test/pass/test_decompose_nn_softmax.py
        - 功能实现: kernel_gen/passes/lowering/decompass.py
        """

        if not isinstance(module, ModuleOp):
            raise DecompassError("DecompassError: module must be builtin.module")
        _decompose_module(module)
        return module


DecomposeNnSoftmaxPass = DecompassPass
DecomposeNnSoftmaxError = DecompassError

__all__ = [
    "DecompassPass",
    "DecompassError",
    "register_decompass_rewrite",
    "DecomposeNnSoftmaxPass",
    "DecomposeNnSoftmaxError",
]
