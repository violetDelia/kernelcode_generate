"""decompass pass。


功能说明:
- 将 `func.func` 内命中的 `nn.softmax` 按 decompass 规则分解。
- 内置 `nn.softmax` 固定展开为 `nn.reduce_max -> nn.broadcast -> nn.sub -> nn.exp -> nn.reduce_sum -> nn.broadcast -> nn.truediv`。
- 在 pass 内显式拒绝负轴与越界 axis。
- 仅停留在 `nn` 方言层，不承担 `nn -> kernel` lowering。

API 列表:
- `class DecompassPass(fold: bool = True)`
- `class NnSoftmaxDecompPattern()`
- `get_decompass_pass_patterns() -> list[RewritePattern]`

使用示例:
- from xdsl.context import Context
- from kernel_gen.passes.decompass import DecompassPass
- DecompassPass().apply(Context(), module)

关联文件:
- spec: spec/pass/decompass.md
- test: test/passes/decompass/test_softmax.py
- 功能实现: kernel_gen/passes/decompass.py
"""

from __future__ import annotations
from kernel_gen.core.error import ErrorKind, ErrorModule, KernelCodeError

from xdsl.context import Context
from xdsl.dialects.builtin import ArrayAttr, IntAttr, ModuleOp, StringAttr
from xdsl.ir import Attribute
from xdsl.passes import ModulePass
from xdsl.pattern_rewriter import (
    GreedyRewritePatternApplier,
    PatternRewriter,
    PatternRewriteWalker,
    RewritePattern,
    op_type_rewrite_pattern,
)

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
from kernel_gen.dialect.symbol import Symbol
from kernel_gen.passes.common import (
    ensure_builtin_module,
    verify_generated_ops,
)


class NnSoftmaxDecompPattern(RewritePattern):
    """`nn.softmax` 的固定分解 pattern。


    功能说明:
    - 通过 `@op_type_rewrite_pattern` 直接匹配 `NnSoftmaxOp`。
    - 把单个 `nn.softmax` 固定展开为
      `nn.reduce_max -> nn.broadcast -> nn.sub -> nn.exp -> nn.reduce_sum -> nn.broadcast -> nn.truediv`。
    - 不承接其它 `nn.*` op 的通用注册或动态分发。

    使用示例:
    - `pattern = NnSoftmaxDecompPattern()`

    关联文件:
    - spec: spec/pass/decompass.md
    - test: test/passes/decompass/test_softmax.py
    - 功能实现: kernel_gen/passes/decompass.py
    """

    @op_type_rewrite_pattern
    def match_and_rewrite(self, op: NnSoftmaxOp, rewriter: PatternRewriter, /) -> None:
        input_type = op.input.type
        result_type = op.result.type
        if not isinstance(input_type, NnMemoryType) or not isinstance(result_type, NnMemoryType):
            raise KernelCodeError(ErrorKind.CONTRACT, ErrorModule.PASS, "operand and result must be nn.memory")
        if input_type.shape != result_type.shape or input_type.stride != result_type.stride:
            raise KernelCodeError(ErrorKind.CONTRACT, ErrorModule.PASS, "result type must match input shape and stride")
        rank = len(input_type.shape.data)
        axis = op.axis.value.data
        if axis < 0 or axis >= rank:
            raise KernelCodeError(ErrorKind.CONTRACT, ErrorModule.PASS, "normalized axis out of range")

        reduce_shape = list(input_type.shape.data)
        reduce_shape[axis] = IntAttr(1)
        suffix_factors: list[Attribute] = []
        reduce_strides: list[Attribute] = []
        for dim in reversed(reduce_shape):
            int_product = 1
            expr_parts: list[str] = []
            for factor in suffix_factors:
                if isinstance(factor, IntAttr):
                    int_product *= factor.data
                    continue
                if isinstance(factor, StringAttr):
                    expr_parts.append(factor.data)
                    continue
                raise KernelCodeError(ErrorKind.CONTRACT, ErrorModule.PASS, "shape entries must be IntAttr or StringAttr")
            if not expr_parts:
                reduce_strides.append(IntAttr(int_product))
            else:
                parts: list[str] = []
                if int_product != 1:
                    parts.append(str(int_product))
                parts.extend(part for part in expr_parts if part != "1")
                if not parts:
                    reduce_strides.append(IntAttr(1))
                else:
                    reduce_strides.append(StringAttr("*".join(parts)))
            suffix_factors.insert(0, dim)
        reduce_strides.reverse()
        reduce_type = NnMemoryType(
            ArrayAttr(reduce_shape),
            ArrayAttr(reduce_strides),
            input_type.element_type,
            input_type.space,
        )

        max_op = NnReduceMaxOp(op.input, reduce_type, axes=[axis], keepdim=True, space=op.space)
        max_broadcast = NnBroadcastOp(max_op.result, result_type, op.space)
        sub_op = NnSubOp(op.input, max_broadcast.result, result_type, op.space)
        exp_op = NnExpOp(sub_op.result, result_type, op.space)
        sum_op = NnReduceSumOp(
            exp_op.result,
            reduce_type,
            axes=[axis],
            keepdim=True,
            space=op.space,
        )
        sum_broadcast = NnBroadcastOp(sum_op.result, result_type, op.space)
        div_op = NnTrueDivOp(exp_op.result, sum_broadcast.result, result_type, op.space)
        new_ops = [max_op, max_broadcast, sub_op, exp_op, sum_op, sum_broadcast, div_op]

        verify_generated_ops(new_ops)
        rewriter.replace_matched_op(new_ops, [div_op.result])


def get_decompass_pass_patterns() -> list[RewritePattern]:
    """返回 `decompass` pass 使用的公开 pattern 列表。


    功能说明:
    - 为外部测试、组合 pass 与公开 API 提供稳定的 pattern 构造入口。
    - 当前固定只返回 `NnSoftmaxDecompPattern`，顺序即为 pass 执行顺序。

    使用示例:
    - `patterns = get_decompass_pass_patterns()`
    - `walker = PatternRewriteWalker(GreedyRewritePatternApplier(patterns, ctx=ctx))`

    关联文件:
    - spec: spec/pass/decompass.md
    - test: test/passes/decompass/test_softmax.py
    - 功能实现: kernel_gen/passes/decompass.py
    """

    return [NnSoftmaxDecompPattern()]


class DecompassPass(ModulePass):
    """执行 decompass 分解链。


    功能说明:
    - 在 ModuleOp 的 func.func 内执行固定 `nn.softmax` 分解链。
    - 公开执行入口固定为 xdsl `ModulePass.apply(ctx, module)`，不再提供单 pass `run(...)` 兼容入口。

    使用示例:
    - from xdsl.context import Context
    - DecompassPass().apply(Context(), module)

    关联文件:
    - spec: spec/pass/decompass.md
    - test: test/passes/decompass/test_softmax.py
    - 功能实现: kernel_gen/passes/decompass.py
    """

    name = "decompass"

    def __init__(self: "DecompassPass", fold: bool = True) -> None:
        """初始化 decompass pass 公共选项。


        功能说明:
        - 记录 `fold` 开关，默认允许 pass 内 pattern walker 执行 folding。

        使用示例:
        - pass_obj = DecompassPass()
        - pass_obj = DecompassPass(fold=False)

        关联文件:
        - spec: spec/pass/decompass.md
        - test: test/passes/decompass/test_softmax.py
        - 功能实现: kernel_gen/passes/decompass.py
        """

        self.fold = bool(fold)

    def apply(self, ctx: Context, module: ModuleOp) -> None:
        """执行 `decompass` pass。


        功能说明:
        - 校验 module 类型，随后执行 decompass 分解。

        使用示例:
        - DecompassPass().apply(Context(), module)

        关联文件:
        - spec: spec/pass/decompass.md
        - test: test/passes/decompass/test_softmax.py
        - 功能实现: kernel_gen/passes/decompass.py
        """

        ensure_builtin_module(module)
        if ctx.get_optional_dialect(Symbol.name) is None:
            ctx.load_dialect(Symbol)
        PatternRewriteWalker(
            GreedyRewritePatternApplier([
                *get_decompass_pass_patterns(),
            ], ctx=ctx, folding_enabled=self.fold, dce_enabled=False)
        ).rewrite_module(module)

__all__ = [
    "DecompassPass",
    "NnSoftmaxDecompPattern",
    "get_decompass_pass_patterns",
]
