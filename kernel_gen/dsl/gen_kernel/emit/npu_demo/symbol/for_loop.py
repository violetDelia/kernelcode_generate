"""npu_demo symbol.for emitter.


功能说明:
- 生成 npu_demo target 下 `symbol.for` 的 for-loop 代码片段。
- 支持 `iter_args` 单个 `!symbol.int` loop-carried 累计值。
- 迭代变量命名统一委托给 `EmitCContext.create_or_get_name(...)`。
- 嵌套循环体内的 `builtin.unrealized_conversion_cast` 仅作为 SSA 别名绑定，不生成独立源码语句。

API 列表:
- 无（仅 target 私有注册实现）

使用示例:
- from kernel_gen.dsl.gen_kernel import EmitCContext, emit_c_op
- stmt = emit_c_op(symbol_for_op, EmitCContext())

关联文件:
- spec: [spec/dsl/gen_kernel/emit.md](../../../../../../spec/dsl/gen_kernel/emit.md)
- test: [test/dsl/gen_kernel/emit/test_package.py](../../../../../../test/dsl/gen_kernel/emit/test_package.py)
- 功能实现: [kernel_gen/dsl/gen_kernel/emit/npu_demo/symbol/for_loop.py](.)
"""

from __future__ import annotations

from kernel_gen.core.error import ErrorKind, ErrorModule, KernelCodeError
from kernel_gen.dialect.symbol import SymbolForOp, SymbolYieldOp
from xdsl.dialects import scf

from ...register import emit_c_impl


@emit_c_impl(SymbolForOp, target="npu_demo")
def _emit_npu_demo_symbol_for(op: SymbolForOp, ctx) -> str:
    """生成 npu_demo 目标的 `symbol.for` 源码。


    功能说明:
    - 将 `symbol.for` lowering 为 `for (S_INT ...)` 循环。
    - 循环体内保留可发射 op，跳过 `scf.yield`，并把 `symbol.yield` 发射为 carried 变量更新。
    - 对嵌套 `builtin.unrealized_conversion_cast` 做透明别名绑定，支持循环变量参与符号表达式。

    使用示例:
    - stmt = _emit_npu_demo_symbol_for(symbol_for_op, ctx)
    """

    from ... import emit_c_op, emit_c_value

    block = op.body.block
    iv_name = ctx.create_or_get_name(block.args[0])
    lower_expr = emit_c_value(op.start, ctx)
    upper_expr = emit_c_value(op.end, ctx)
    step_expr = emit_c_value(op.step, ctx)
    carried_name = None
    lines = []
    if op.init is not None:
        if op.result is None or len(block.args) < 2:
            raise KernelCodeError(
                ErrorKind.CONTRACT,
                ErrorModule.GEN_KERNEL,
                "symbol.for carried value requires result and accumulator block argument",
            )
        carried_name = ctx.create_or_get_name(op.result)
        ctx.bind_name(block.args[1], carried_name)
        lines.append(f"{ctx.current_indent}S_INT {carried_name} = {emit_c_value(op.init, ctx)};")
    lines.append(
        f"{ctx.current_indent}for (S_INT {iv_name} = {lower_expr}; {iv_name} < {upper_expr}; {iv_name} += {step_expr}) {{"
    )
    ctx.push_indent()
    for body_op in block.ops:
        if isinstance(body_op, scf.YieldOp):
            continue
        if isinstance(body_op, SymbolYieldOp):
            if carried_name is None:
                raise KernelCodeError(
                    ErrorKind.CONTRACT,
                    ErrorModule.GEN_KERNEL,
                    "symbol.yield requires carried symbol.for",
                )
            lines.append(f"{ctx.current_indent}{carried_name} = {emit_c_value(body_op.value, ctx)};")
            continue
        if body_op.name == "builtin.unrealized_conversion_cast":
            if len(body_op.operands) != 1 or len(body_op.results) != 1:
                raise KernelCodeError(
                    ErrorKind.CONTRACT,
                    ErrorModule.GEN_KERNEL,
                    "unrealized_conversion_cast must have exactly one operand and one result",
                )
            ctx.bind_name(body_op.results[0], emit_c_value(body_op.operands[0], ctx))
            continue
        stmt = emit_c_op(body_op, ctx)
        if stmt:
            lines.append(stmt)
    ctx.pop_indent()
    lines.append(f"{ctx.current_indent}}}")
    if op.result is not None and carried_name is not None:
        ctx.bind_name(op.result, carried_name)
    return "\n".join(lines)
