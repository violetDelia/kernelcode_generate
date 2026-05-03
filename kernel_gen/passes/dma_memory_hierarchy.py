"""dma-memory-hierarchy lowering pass.


功能说明:
- 实现 `lower-dma-memory-hierarchy` pass 的两条公开执行路径。
- 默认 `LowerDmaMemoryHierarchyPass()` 不配置 `apply_op` 时保持 no-op。
- `fold=False` 且不配置 `apply_op` 时保留 legacy `GM -> SM -> LM` / `LM -> SM -> GM`
  hierarchy 兼容路径。
- 配置 `apply_op="matmul{[...]}"` 时，对 `kernel.matmul` 的非空 target operand
  生成 `dma.alloc + dma.copy` 并替换 operand。

API 列表:
- `class LowerDmaMemoryHierarchyPass(fold: bool = True, apply_op: str | None = None)`
- `LowerDmaMemoryHierarchyPass.from_options(options: dict[str, str]) -> LowerDmaMemoryHierarchyPass`
- `LowerDmaMemoryHierarchyPass.apply(ctx: Context, module: ModuleOp) -> None`

使用示例:
- from kernel_gen.passes.dma_memory_hierarchy import LowerDmaMemoryHierarchyPass
- LowerDmaMemoryHierarchyPass().apply(Context(), module)

关联文件:
- spec: spec/pass/lowering/dma_memory_hierarchy/spec.md
- test: test/passes/test_dma_memory_hierarchy.py
- 功能实现: kernel_gen/passes/dma_memory_hierarchy.py
"""

from __future__ import annotations
import json
from dataclasses import dataclass

import kernel_gen.target.registry as targetregistry
from kernel_gen.core.error import ErrorKind, ErrorModule, KernelCodeError

from xdsl.context import Context
from xdsl.dialects import arith
from xdsl.dialects.builtin import (
    IntAttr,
    IntegerAttr,
    ModuleOp,
    StringAttr,
    UnrealizedConversionCastOp,
    i32,
)
from xdsl.ir import Block, Operation, SSAValue

from kernel_gen.dialect.dma import DmaAllocOp, DmaCopyOp, DmaDesliceOp, DmaSliceOp, DmaViewOp
from kernel_gen.dialect.nn import NnMemorySpaceAttr, NnMemoryType
from kernel_gen.dialect.symbol import SymbolGetDimOp, SymbolValueType
from kernel_gen.passes.pass_manager import Pass


_APPLY_OP_PREFIX = "matmul"
_APPLY_TARGETS = {"", "shared", "local", "tsm", "tlm1", "tlm2", "tlm3"}
_MATMUL_OPERAND_COUNT = 3


@dataclass(frozen=True)
class _ApplyOpRule:
    """保存 `apply_op` 解析后的内部规则。"""

    targets: tuple[str, str, str]


def _require_sm_lm_support() -> None:
    """校验当前 target 支持 SM/LM，否则显式失败。


    功能说明:
    - 读取当前 target 的 `sm_memory_size` 与 `lm_memory_size`。
    - 任一为 `None/<=0` 则视作不支持，抛出包含 `SM/LM` 关键字的错误。

    使用示例:
    - _require_sm_lm_support()

    关联文件:
    - spec: spec/pass/lowering/dma_memory_hierarchy/spec.md
    - test: test/passes/test_dma_memory_hierarchy.py
    - 功能实现: kernel_gen/passes/dma_memory_hierarchy.py
    """

    sm_size = targetregistry.get_current_target_hardware("sm_memory_size")
    lm_size = targetregistry.get_current_target_hardware("lm_memory_size")
    if sm_size is None or lm_size is None:
        raise KernelCodeError(ErrorKind.CONTRACT, ErrorModule.PASS, 
            "target must be selected and provide SM/LM hardware size for lower-dma-memory-hierarchy"
        )
    if sm_size <= 0 or lm_size <= 0:
        raise KernelCodeError(ErrorKind.CONTRACT, ErrorModule.PASS, 
            "target does not support SM/LM for lower-dma-memory-hierarchy"
        )


def _memory_space(value_type: NnMemoryType) -> str:
    """读取 nn.memory 的 space 名称。


    功能说明:
    - 返回 `global/shared/local/tsm/tlm1/tlm2/tlm3` 中的字符串。

    使用示例:
    - space = _memory_space(SSAValue.get(op.operands[0]).type)

    关联文件:
    - spec: spec/pass/lowering/dma_memory_hierarchy/spec.md
    - test: test/passes/test_dma_memory_hierarchy.py
    - 功能实现: kernel_gen/passes/dma_memory_hierarchy.py
    """

    return value_type.space.space.data


def _parse_apply_op(apply_op: str | None) -> _ApplyOpRule | None:
    """解析并校验 `lower-dma-memory-hierarchy` 的 `apply_op` 规则。


    功能说明:
    - 当前仅支持 `matmul{["", "tlm1", "tlm2"]}` 形式的单条规则。
    - 列表固定对应 `kernel.matmul` 的 `out/lhs/rhs` 三个 operand。

    使用示例:
    - rule = _parse_apply_op('matmul{["", "tlm1", "tlm2"]}')

    关联文件:
    - spec: spec/pass/lowering/dma_memory_hierarchy/spec.md
    - test: test/passes/test_dma_memory_hierarchy.py
    - 功能实现: kernel_gen/passes/dma_memory_hierarchy.py
    """

    if apply_op is None:
        return None
    text = apply_op.strip()
    if not text.startswith(f"{_APPLY_OP_PREFIX}{{") or not text.endswith("}"):
        raise KernelCodeError(
            ErrorKind.CONTRACT,
            ErrorModule.PASS,
            "unsupported apply_op; apply_op must be matmul{[...]}; only matmul is supported",
        )
    payload = text[len(_APPLY_OP_PREFIX) + 1 : -1]
    try:
        targets = json.loads(payload)
    except json.JSONDecodeError as exc:
        raise KernelCodeError(
            ErrorKind.CONTRACT,
            ErrorModule.PASS,
            "apply_op matmul target list must be valid JSON",
        ) from exc
    if not isinstance(targets, list):
        raise KernelCodeError(
            ErrorKind.CONTRACT,
            ErrorModule.PASS,
            "apply_op matmul target list must be a list",
        )
    if len(targets) != _MATMUL_OPERAND_COUNT:
        raise KernelCodeError(
            ErrorKind.CONTRACT,
            ErrorModule.PASS,
            "apply_op matmul target list must contain exactly 3 entries for out/lhs/rhs",
        )
    normalized: list[str] = []
    for target in targets:
        if not isinstance(target, str):
            raise KernelCodeError(
                ErrorKind.CONTRACT,
                ErrorModule.PASS,
                "apply_op matmul target entries must be strings",
            )
        if target not in _APPLY_TARGETS:
            allowed = ", ".join(sorted(space for space in _APPLY_TARGETS if space))
            raise KernelCodeError(
                ErrorKind.CONTRACT,
                ErrorModule.PASS,
                f"apply_op matmul target space must be one of [{allowed}] or empty string",
            )
        normalized.append(target)
    return _ApplyOpRule((normalized[0], normalized[1], normalized[2]))


def _with_space(value_type: NnMemoryType, space: str) -> NnMemoryType:
    """构造同 shape/stride/element_type、不同 space 的 nn.memory type。


    功能说明:
    - 用于为 staging buffer 生成 `SM/LM` 空间的类型。

    使用示例:
    - lm_type = _with_space(gm_type, "local")

    关联文件:
    - spec: spec/pass/lowering/dma_memory_hierarchy/spec.md
    - test: test/passes/test_dma_memory_hierarchy.py
    - 功能实现: kernel_gen/passes/dma_memory_hierarchy.py
    """

    return NnMemoryType(
        value_type.shape,
        value_type.stride,
        value_type.element_type,
        NnMemorySpaceAttr.from_name(space),
    )


def _const_symbol_int(value: int) -> tuple[arith.ConstantOp, UnrealizedConversionCastOp]:
    """构造 `!symbol.int<\"value\">` 常量的 IR op 对。


    功能说明:
    - 先创建 i32 常量，再用 `builtin.unrealized_conversion_cast` 转成 `!symbol.int<\"expr\">`。
    - 返回两条 op，调用者决定插入到 block 中的位置。

    使用示例:
    - const_i32, cast = _const_symbol_int(1)
    - block.insert_ops_before([const_i32, cast], anchor_op)
    - one = cast.results[0]

    关联文件:
    - spec: spec/pass/lowering/dma_memory_hierarchy/spec.md
    - test: test/passes/test_dma_memory_hierarchy.py
    - 功能实现: kernel_gen/passes/dma_memory_hierarchy.py
    """

    const = arith.ConstantOp(IntegerAttr(value, i32))
    result_type = SymbolValueType.from_expr(str(value))
    cast = UnrealizedConversionCastOp(operands=[const.result], result_types=[result_type])
    return const, cast


def _build_full_window_operands(
    source: SSAValue,
    *,
    rank: int,
    zero: SSAValue,
    one: SSAValue,
) -> tuple[list[Operation], list[SSAValue], list[SSAValue], list[SSAValue]]:
    """为整块窗口搬运构造 offsets/sizes/strides operand。


    功能说明:
    - offsets: 全 0
    - strides: 全 1
    - sizes: 通过 `symbol.get_dim(source, axis)` 从 source 的 shape 中读取，保证与静态 shape 对齐，
      且当 source 存在匿名动态值 `?` 且没有可恢复的显式 symbol 来源时，pass 必须显式失败。

    使用示例:
    - ops, offsets, sizes, strides = _build_full_window_operands(gm, rank=2, zero=zero, one=one)

    关联文件:
    - spec: spec/pass/lowering/dma_memory_hierarchy/spec.md
    - test: test/passes/test_dma_memory_hierarchy.py
    - 功能实现: kernel_gen/passes/dma_memory_hierarchy.py
    """

    source_type = source.type
    if not isinstance(source_type, NnMemoryType):
        raise KernelCodeError(ErrorKind.CONTRACT, ErrorModule.PASS, "dynamic_shape source must be nn.memory")

    ops: list[Operation] = []
    sizes: list[SSAValue] = []
    for axis in range(rank):
        shape_dim = source_type.shape.data[axis]
        if isinstance(shape_dim, StringAttr) and shape_dim.data == "?":
            raise KernelCodeError(ErrorKind.CONTRACT, ErrorModule.PASS, 
                "dynamic_shape must come from explicit symbol source; anonymous '?' dimension is unsupported in lower-dma-memory-hierarchy"
            )
        get_dim = SymbolGetDimOp(source, IntAttr(axis))
        ops.append(get_dim)
        sizes.append(get_dim.result)
    offsets = [zero] * rank
    strides = [one] * rank
    return ops, offsets, sizes, strides


def _build_dynamic_shape_operands(
    source: SSAValue,
    source_type: NnMemoryType,
) -> tuple[list[Operation], list[SSAValue]]:
    """构造 `dma.alloc` 所需的动态 shape operand。


    功能说明:
    - 静态 shape 返回空列表，让 `dma.alloc` 使用零 operand 形式。
    - 显式符号维度通过 `symbol.get_dim(source, axis)` 读取。
    - 匿名动态维度 `?` 没有稳定 symbol 来源，必须显式失败。

    使用示例:
    - ops, dynamic_shape = _build_dynamic_shape_operands(lhs, lhs_type)

    关联文件:
    - spec: spec/pass/lowering/dma_memory_hierarchy/spec.md
    - test: test/passes/test_dma_memory_hierarchy.py
    - 功能实现: kernel_gen/passes/dma_memory_hierarchy.py
    """

    source_type.verify()
    ops: list[Operation] = []
    dynamic_shape: list[SSAValue] = []
    for axis, shape_dim in enumerate(source_type.shape.data):
        if isinstance(shape_dim, IntAttr):
            continue
        if isinstance(shape_dim, StringAttr):
            if shape_dim.data == "?":
                raise KernelCodeError(
                    ErrorKind.CONTRACT,
                    ErrorModule.PASS,
                    "dynamic_shape must come from explicit symbol source; anonymous '?' dimension is unsupported in lower-dma-memory-hierarchy",
                )
            get_dim = SymbolGetDimOp(source, IntAttr(axis))
            ops.append(get_dim)
            dynamic_shape.append(get_dim.result)
            continue
        raise KernelCodeError(
            ErrorKind.CONTRACT,
            ErrorModule.PASS,
            "dynamic_shape result shape entries must be IntAttr or StringAttr",
        )
    return ops, dynamic_shape


def _resolve_window_operands(
    value: SSAValue,
    *,
    rank: int,
    zero: SSAValue,
    one: SSAValue,
) -> tuple[list[Operation], SSAValue, list[SSAValue], list[SSAValue], list[SSAValue]]:
    """解析 GM 侧窗口参数与基准 source/target。


    功能说明:
    - 若 operand 来自 `dma.view`，保留其 offsets/shape 作为 window 参数，并将 base 设为 view.source。
    - `dma.slice/dma.deslice` 当前仅支持单位 stride；因此即使 `dma.view` 自身记录了非单位窗口 stride，hierarchy 新路径也只继承原窗口的 offsets/shape，并统一把 stride 规范化为 unit stride。
    - 非 window 情况下回退为 full window：offsets=0、sizes=shape、strides=1。

    使用示例:
    - ops, base, offsets, sizes, strides = _resolve_window_operands(gm, rank=2, zero=zero, one=one)

    关联文件:
    - spec: spec/pass/lowering/dma_memory_hierarchy/spec.md
    - test: test/passes/test_dma_memory_hierarchy.py
    - 功能实现: kernel_gen/passes/dma_memory_hierarchy.py
    """

    owner = getattr(value, "owner", None)
    if isinstance(owner, DmaViewOp):
        offsets = list(owner.offsets)
        sizes = list(owner.shape)
        if len(offsets) != rank or len(sizes) != rank:
            raise KernelCodeError(ErrorKind.CONTRACT, ErrorModule.PASS, "dma.view window rank mismatch for lower-dma-memory-hierarchy")
        return [], SSAValue.get(owner.source), offsets, sizes, [one] * rank
    ops, offsets, sizes, strides = _build_full_window_operands(
        value, rank=rank, zero=zero, one=one
    )
    return ops, value, offsets, sizes, strides


def _ensure_static_rank(memory_type: NnMemoryType, context: str) -> int:
    """确保 nn.memory 的 rank 可确定，返回 rank。


    功能说明:
    - 目前 rank 由 shape 列表长度决定；这里同步触发类型校验并返回 rank。

    使用示例:
    - rank = _ensure_static_rank(mem_type, "kernel operand")

    关联文件:
    - spec: spec/pass/lowering/dma_memory_hierarchy/spec.md
    - test: test/passes/test_dma_memory_hierarchy.py
    - 功能实现: kernel_gen/passes/dma_memory_hierarchy.py
    """

    memory_type.verify()
    rank = len(memory_type.shape.data)
    if rank <= 0:
        raise KernelCodeError(ErrorKind.CONTRACT, ErrorModule.PASS, f"{context} rank must be >= 1")
    return rank


def _is_kernel_op(op: Operation) -> bool:
    """判断 op 是否为 kernel dialect op。


    功能说明:
    - 当前以 `op.name.startswith(\"kernel.\")` 判定。

    使用示例:
    - if _is_kernel_op(op): ...

    关联文件:
    - spec: spec/pass/lowering/dma_memory_hierarchy/spec.md
    - test: test/passes/test_dma_memory_hierarchy.py
    - 功能实现: kernel_gen/passes/dma_memory_hierarchy.py
    """

    return op.name.startswith("kernel.")


def _lower_gm_operand_to_lm(
    operand: SSAValue,
    operand_type: NnMemoryType,
    *,
    block: Block,
    anchor_op: Operation,
    zero: SSAValue,
    one: SSAValue,
) -> tuple[list[Operation], SSAValue]:
    """将单个 GM operand 改写为 GM->SM->LM 并返回 LM buffer。


    功能说明:
    - 为 operand 分配 SM/LM staging buffer，并插入两段 `dma.slice`：
      `GM -> SM`（保留 full/window offsets/sizes，strides 仍为 unit stride）与
      `SM -> LM`（zero offsets + unit strides）。
    - 返回需要插入到 `anchor_op` 之前的 ops 列表与最终 LM buffer SSA value。

    使用示例:
    - ops, lm = _lower_gm_operand_to_lm(gm, gm_type, block=block, anchor_op=kernel_op, zero=zero, one=one)
    - block.insert_ops_before(ops, kernel_op)

    关联文件:
    - spec: spec/pass/lowering/dma_memory_hierarchy/spec.md
    - test: test/passes/test_dma_memory_hierarchy.py
    - 功能实现: kernel_gen/passes/dma_memory_hierarchy.py
    """

    rank = _ensure_static_rank(operand_type, "kernel operand")
    sm_type = _with_space(operand_type, "shared")
    lm_type = _with_space(operand_type, "local")
    window_ops, window_source, window_offsets, window_sizes, window_strides = _resolve_window_operands(
        operand, rank=rank, zero=zero, one=one
    )
    alloc_sm = DmaAllocOp(window_sizes, sm_type)
    alloc_lm = DmaAllocOp(window_sizes, lm_type)
    slice_gm_to_sm = DmaSliceOp(
        alloc_sm.result, window_source, window_offsets, window_sizes, window_strides
    )
    zero_offsets = [zero] * rank
    unit_strides = [one] * rank
    slice_sm_to_lm = DmaSliceOp(alloc_lm.result, alloc_sm.result, zero_offsets, window_sizes, unit_strides)
    ops: list[Operation] = [*window_ops, alloc_sm, alloc_lm, slice_gm_to_sm, slice_sm_to_lm]
    return ops, alloc_lm.result


def _lower_gm_out_to_lm_with_writeback(
    out: SSAValue,
    out_type: NnMemoryType,
    *,
    block: Block,
    anchor_op: Operation,
    zero: SSAValue,
    one: SSAValue,
) -> tuple[list[Operation], list[Operation], SSAValue]:
    """将 GM out operand 改写为 LM out，并构造 LM->SM->GM 写回链路。


    功能说明:
    - 在 `anchor_op` 前插入 SM/LM alloc（out staging）。
    - 在 `anchor_op` 后插入两段 `dma.deslice`：`LM -> SM` 与 `SM -> GM`。
      第二段 deslice 的 source 使用第一段 deslice 的 result，匹配 `dma.deslice` 返回“更新后 target”的语义。
    - `LM -> SM` 使用 zero offsets + unit strides；`SM -> GM` 保留 full/window offsets/sizes，
      但回写 strides 仍统一使用 unit stride。
    - 返回：需插入到 `anchor_op` 前的 ops、需插入到 `anchor_op` 后的 ops、以及 LM out SSA value。

    使用示例:
    - pre_ops, post_ops, lm_out = _lower_gm_out_to_lm_with_writeback(gm_out, gm_type, block=block, anchor_op=kernel_op, zero=zero, one=one)
    - block.insert_ops_before(pre_ops, kernel_op)
    - block.insert_ops_after(post_ops, kernel_op)

    关联文件:
    - spec: spec/pass/lowering/dma_memory_hierarchy/spec.md
    - test: test/passes/test_dma_memory_hierarchy.py
    - 功能实现: kernel_gen/passes/dma_memory_hierarchy.py
    """

    rank = _ensure_static_rank(out_type, "kernel out")
    sm_type = _with_space(out_type, "shared")
    lm_type = _with_space(out_type, "local")
    window_ops, window_target, window_offsets, window_sizes, window_strides = _resolve_window_operands(
        out, rank=rank, zero=zero, one=one
    )
    if not isinstance(window_target.type, NnMemoryType):
        raise KernelCodeError(ErrorKind.CONTRACT, ErrorModule.PASS, "window target must be nn.memory")
    alloc_sm = DmaAllocOp(window_sizes, sm_type)
    alloc_lm = DmaAllocOp(window_sizes, lm_type)
    pre_ops: list[Operation] = [*window_ops, alloc_sm, alloc_lm]

    zero_offsets = [zero] * rank
    unit_strides = [one] * rank
    deslice_lm_to_sm = DmaDesliceOp(
        alloc_sm.result,
        alloc_lm.result,
        zero_offsets,
        window_sizes,
        unit_strides,
        sm_type,
    )
    deslice_sm_to_gm = DmaDesliceOp(
        window_target,
        deslice_lm_to_sm.result,
        window_offsets,
        window_sizes,
        window_strides,
        window_target.type,
    )
    post_ops: list[Operation] = [deslice_lm_to_sm, deslice_sm_to_gm]
    return pre_ops, post_ops, alloc_lm.result


class LowerDmaMemoryHierarchyPass(Pass):
    """执行 dma memory hierarchy 规则化 lowering。


    功能说明:
    - 默认无 `apply_op` 时保持 no-op。
    - `fold=False` 且无 `apply_op` 时保留 legacy hierarchy 兼容路径。
    - 有 `apply_op` 时按 `matmul{[...]}` 规则插入 `dma.alloc + dma.copy`。

    使用示例:
    - LowerDmaMemoryHierarchyPass(apply_op='matmul{["", "tlm1", "tlm2"]}').apply(Context(), module)

    关联文件:
    - spec: spec/pass/lowering/dma_memory_hierarchy/spec.md
    - test: test/passes/test_dma_memory_hierarchy.py
    - 功能实现: kernel_gen/passes/dma_memory_hierarchy.py
    """

    name = "lower-dma-memory-hierarchy"

    def __init__(self, fold: bool = True, apply_op: str | None = None) -> None:
        """初始化 `lower-dma-memory-hierarchy` pass。


        功能说明:
        - 保存 `fold` 兼容开关。
        - 解析可选 `apply_op` 规则。

        使用示例:
        - LowerDmaMemoryHierarchyPass(fold=False)
        - LowerDmaMemoryHierarchyPass(apply_op='matmul{["", "tlm1", "tlm2"]}')

        关联文件:
        - spec: spec/pass/lowering/dma_memory_hierarchy/spec.md
        - test: test/passes/test_dma_memory_hierarchy.py
        - 功能实现: kernel_gen/passes/dma_memory_hierarchy.py
        """

        self.fold = fold
        self.apply_op = apply_op
        self._rule = _parse_apply_op(apply_op)

    @classmethod
    def from_options(cls, options: dict[str, str]) -> "LowerDmaMemoryHierarchyPass":
        """通过 pass registry options 构造 pass。


        功能说明:
        - 当前只接受 `apply_op` pass 专属 option。
        - registry 的通用 `fold` option 由 registry 层剥离后写回 `fold` 属性。

        使用示例:
        - LowerDmaMemoryHierarchyPass.from_options({"apply_op": "matmul{[\\"\\", \\"tlm1\\", \\"tlm2\\"]}"})

        关联文件:
        - spec: spec/pass/lowering/dma_memory_hierarchy/spec.md
        - test: test/passes/test_dma_memory_hierarchy.py
        - 功能实现: kernel_gen/passes/dma_memory_hierarchy.py
        """

        allowed = {"apply_op"}
        unknown = sorted(set(options) - allowed)
        if unknown:
            names = ", ".join(unknown)
            raise KernelCodeError(
                ErrorKind.CONTRACT,
                ErrorModule.PASS,
                f"lower-dma-memory-hierarchy unsupported option(s): {names}",
            )
        return cls(apply_op=options.get("apply_op"))

    def apply(self, ctx: Context, module: ModuleOp) -> None:
        """执行 dma-memory-hierarchy lowering。


        功能说明:
        - 有 `apply_op` 时只处理 `kernel.matmul` 并生成 copy-based staging。
        - 无 `apply_op` 且 `fold=True` 时 no-op。
        - 无 `apply_op` 且 `fold=False` 时走 legacy hierarchy 兼容路径。

        使用示例:
        - LowerDmaMemoryHierarchyPass(apply_op='matmul{["", "tlm1", "tlm2"]}').apply(Context(), module)

        关联文件:
        - spec: spec/pass/lowering/dma_memory_hierarchy/spec.md
        - test: test/passes/test_dma_memory_hierarchy.py
        - 功能实现: kernel_gen/passes/dma_memory_hierarchy.py
        """

        _ = ctx
        if not isinstance(module, ModuleOp):
            raise KernelCodeError(ErrorKind.CONTRACT, ErrorModule.PASS, "module must be builtin.module")
        if self._rule is not None:
            self._apply_matmul_rule(module, self._rule)
            return
        if self.fold:
            return
        self._apply_legacy_hierarchy(module)

    def _apply_matmul_rule(self, module: ModuleOp, rule: _ApplyOpRule) -> None:
        """执行 `matmul{[...]}` copy-based rewrite。


        功能说明:
        - 遍历 module 内 `kernel.matmul` op。
        - 对规则中非空 target operand 插入 `dma.alloc + dma.copy` 并替换 operand。

        使用示例:
        - self._apply_matmul_rule(module, rule)

        关联文件:
        - spec: spec/pass/lowering/dma_memory_hierarchy/spec.md
        - test: test/passes/test_dma_memory_hierarchy.py
        - 功能实现: kernel_gen/passes/dma_memory_hierarchy.py
        """

        for op in [candidate for candidate in module.walk() if candidate.name == "kernel.matmul"]:
            if len(op.operands) != _MATMUL_OPERAND_COUNT:
                raise KernelCodeError(
                    ErrorKind.CONTRACT,
                    ErrorModule.PASS,
                    "kernel.matmul must have exactly 3 operands for apply_op matmul",
                )
            block = op.parent
            if not isinstance(block, Block):
                raise KernelCodeError(ErrorKind.CONTRACT, ErrorModule.PASS, "kernel.matmul must live in a block")
            for index, target_space in enumerate(rule.targets):
                if target_space == "":
                    continue
                source = SSAValue.get(op.operands[index])
                source_type = source.type
                if not isinstance(source_type, NnMemoryType):
                    raise KernelCodeError(
                        ErrorKind.CONTRACT,
                        ErrorModule.PASS,
                        "apply_op matmul target operand must be nn.memory",
                    )
                target_type = _with_space(source_type, target_space)
                shape_ops, dynamic_shape = _build_dynamic_shape_operands(source, source_type)
                alloc = DmaAllocOp(dynamic_shape, target_type)
                copy = DmaCopyOp(alloc.result, source)
                block.insert_ops_before([*shape_ops, alloc, copy], op)
                op.operands[index] = alloc.result

    def _apply_legacy_hierarchy(self, module: ModuleOp) -> None:
        """执行 legacy GM/SM/LM hierarchy 兼容路径。


        功能说明:
        - `fold=False` 且未配置 `apply_op` 时保留原 `dma.slice/dma.deslice` 行为。
        - 该路径服务历史 pipeline/basic 合同，不参与 `apply_op` copy rewrite。

        使用示例:
        - self._apply_legacy_hierarchy(module)

        关联文件:
        - spec: spec/pass/lowering/dma_memory_hierarchy/spec.md
        - test: test/passes/test_dma_memory_hierarchy.py
        - 功能实现: kernel_gen/passes/dma_memory_hierarchy.py
        """

        _require_sm_lm_support()
        if any(op.name.startswith("nn.") for op in module.walk()):
            raise KernelCodeError(ErrorKind.CONTRACT, ErrorModule.PASS, 
                "lower-dma-memory-hierarchy input must not contain nn.* ops"
            )

        kernel_ops = [op for op in module.walk() if _is_kernel_op(op)]
        for op in kernel_ops:
            block = op.parent
            if not isinstance(block, Block):
                raise KernelCodeError(ErrorKind.CONTRACT, ErrorModule.PASS, "kernel op must live in a block")
            if not op.operands:
                continue

            # 当前公开 kernel dialect 约定：第一个 nn.memory operand 为 out。
            out_index = 0
            out_value = SSAValue.get(op.operands[out_index])
            out_type = out_value.type
            if not isinstance(out_type, NnMemoryType):
                raise KernelCodeError(ErrorKind.CONTRACT, ErrorModule.PASS, "kernel out operand must be nn.memory")

            # 预检：只允许 GM/LM space，且仅当存在 GM 时才插入 staging op。
            gm_input_indices: list[int] = []
            for idx in range(len(op.operands)):
                if idx == out_index:
                    continue
                operand_value = SSAValue.get(op.operands[idx])
                operand_type = operand_value.type
                if not isinstance(operand_type, NnMemoryType):
                    continue
                space = _memory_space(operand_type)
                if space == "global":
                    gm_input_indices.append(idx)
                elif space == "local":
                    continue
                else:
                    raise KernelCodeError(ErrorKind.CONTRACT, ErrorModule.PASS, 
                        f"kernel operand space must be GM or LM, got {space}"
                    )

            out_space = _memory_space(out_type)
            if out_space not in {"global", "local"}:
                raise KernelCodeError(ErrorKind.CONTRACT, ErrorModule.PASS, 
                    f"kernel out space must be GM or LM, got {out_space}"
                )

            needs_staging = bool(gm_input_indices) or out_space == "global"
            if not needs_staging:
                op.attributes["space"] = NnMemorySpaceAttr.from_name("local")
                continue

            zero_const, zero_cast = _const_symbol_int(0)
            one_const, one_cast = _const_symbol_int(1)
            block.insert_ops_before([zero_const, zero_cast, one_const, one_cast], op)
            zero = zero_cast.results[0]
            one = one_cast.results[0]

            # 1) 先处理读 operand：所有非 out 的 nn.memory operand 必须最终成为 LM。
            for idx in gm_input_indices:
                operand_value = SSAValue.get(op.operands[idx])
                operand_type = operand_value.type
                assert isinstance(operand_type, NnMemoryType)
                pre_ops, lowered = _lower_gm_operand_to_lm(
                    operand_value,
                    operand_type,
                    block=block,
                    anchor_op=op,
                    zero=zero,
                    one=one,
                )
                block.insert_ops_before(pre_ops, op)
                op.operands[idx] = lowered

            # 2) 处理 out：GM -> LM + 写回；LM-only 则不插入 staging。
            if out_space == "local":
                pass
            elif out_space == "global":
                pre_ops, post_ops, lowered_out = _lower_gm_out_to_lm_with_writeback(
                    out_value,
                    out_type,
                    block=block,
                    anchor_op=op,
                    zero=zero,
                    one=one,
                )
                block.insert_ops_before(pre_ops, op)
                op.operands[out_index] = lowered_out
                block.insert_ops_after(post_ops, op)
            else:
                raise KernelCodeError(ErrorKind.CONTRACT, ErrorModule.PASS, 
                    f"kernel out space must be GM or LM, got {out_space}"
                )

            op.attributes["space"] = NnMemorySpaceAttr.from_name("local")


__all__ = ["LowerDmaMemoryHierarchyPass"]
