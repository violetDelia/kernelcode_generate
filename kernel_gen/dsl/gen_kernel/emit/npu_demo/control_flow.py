"""npu_demo scf control-flow emit helpers.

功能说明:
- 生成 `target="npu_demo"` 下 `scf.if` 的源码片段。
- 仅承接 block0 guard 与其它单块 if/else 直译场景，不公开额外 helper。

API 列表:
- 无公开 API。

使用示例:
- from kernel_gen.dsl.gen_kernel.emit import emit_c_op
- stmt = emit_c_op(scf_if_op, EmitCContext())

关联文件:
- spec: spec/dsl/gen_kernel/emit/npu_demo.md
- test: test/dsl/gen_kernel/emit/test_package.py
- 功能实现: kernel_gen/dsl/gen_kernel/emit/npu_demo/control_flow.py
"""

from __future__ import annotations

from xdsl.dialects import func, scf
from xdsl.dialects.builtin import IntAttr, IntegerAttr, StringAttr
from xdsl.ir import Operation, Region

from ..register import emit_c_impl


def _generic_op_name(op: Operation) -> str:
    """读取 generic op 的公开文本名。

    功能说明:
    - xDSL `UnregisteredOp` 的真实 `op.name` 是 `builtin.unregistered`，原始文本名保存在 `op_name__`。
    - 非 generic op 直接返回 `op.name`，供调用方按公开文本名分支。

    使用示例:
    - if _generic_op_name(op) == "symbol.const": ...
    """

    op_name_attr = op.attributes.get("op_name__")
    if isinstance(op_name_attr, StringAttr):
        return op_name_attr.data
    return op.name


def _emit_generic_symbol_const(op: Operation, ctx) -> str | None:
    """发射 generic `"symbol.const"`。

    功能说明:
    - `kernel-pattern-attach` 为锁定公开 IR 文本会生成 generic `"symbol.const"()`。
    - 当 dispatcher 被 `arch-parallelize` 包入 `scf.if` 后，本 helper 在分支发射路径中绑定该 SSA 名称。

    使用示例:
    - stmt = _emit_generic_symbol_const(op, ctx)
    """

    if _generic_op_name(op) != "symbol.const":
        return None
    if len(op.results) != 1:
        raise ctx.emit_error("symbol.const", "generic symbol.const must have one result")
    value_attr = op.attributes.get("value")
    if isinstance(value_attr, IntAttr):
        value = value_attr.data
    elif isinstance(value_attr, IntegerAttr):
        value = value_attr.value.data
    else:
        raise ctx.emit_error("symbol.const", "generic symbol.const value must be int attr")
    result_name = ctx.create_or_get_name(op.results[0])
    return f"{ctx.current_indent}S_INT {result_name} = {value};"


def _emit_generic_symbol_eq(op: Operation, ctx) -> str | None:
    """发射 generic `"symbol.eq"`。

    功能说明:
    - 将 generic compare 转成布尔局部变量，并复用公开 `emit_c_value(...)` 处理左右操作数。
    - 仅处理 `kernel-pattern-attach` dispatcher 生成的二元比较形态。

    使用示例:
    - stmt = _emit_generic_symbol_eq(op, ctx)
    """

    if _generic_op_name(op) != "symbol.eq":
        return None
    if len(op.operands) != 2 or len(op.results) != 1:
        raise ctx.emit_error("symbol.eq", "generic symbol.eq must have two operands and one result")
    from .. import emit_c_value

    lhs_expr = emit_c_value(op.operands[0], ctx)
    rhs_expr = emit_c_value(op.operands[1], ctx)
    result_type = ctx.dispatch_type(op.results[0].type)
    result_name = ctx.create_or_get_name(op.results[0])
    return f"{ctx.current_indent}{result_type} {result_name} = ({lhs_expr} == {rhs_expr});"


def _emit_npu_demo_if_region(region: Region, ctx) -> list[str]:
    """发射单个 `scf.if` 分支 region 的源码行。

    功能说明:
    - 接受单 block 分支；无 else 时 xDSL 会保留空 false region，此时发射空行列表。
    - 跳过 `scf.yield`，其余 op 通过公开 `emit_c_op(...)` 递归发射。

    使用示例:
    - lines = _emit_npu_demo_if_region(if_op.true_region, ctx)
    """

    from .. import emit_c_op

    if len(region.blocks) == 0:
        return []
    if len(region.blocks) != 1:
        raise ctx.emit_error("scf.if", "npu_demo scf.if region must have single block")
    block = region.blocks[0]
    lines: list[str] = []
    for body_op in block.ops:
        if isinstance(body_op, scf.YieldOp):
            continue
        if isinstance(body_op, func.ReturnOp):
            raise ctx.emit_error("scf.if", "func.return must remain outside scf.if")
        generic_const_stmt = _emit_generic_symbol_const(body_op, ctx)
        if generic_const_stmt is not None:
            lines.append(generic_const_stmt)
            continue
        generic_eq_stmt = _emit_generic_symbol_eq(body_op, ctx)
        if generic_eq_stmt is not None:
            lines.append(generic_eq_stmt)
            continue
        stmt = emit_c_op(body_op, ctx)
        if stmt:
            lines.append(stmt)
    return lines


@emit_c_impl(scf.IfOp, target="npu_demo")
def _emit_npu_demo_if(op: scf.IfOp, ctx) -> str:
    """发射 npu_demo `scf.if` 语句。

    功能说明:
    - 将 `scf.if` 直译为 C/C++ `if (...) { ... } else { ... }`。
    - 支持 block0 guard 的 then/else 结构，空分支保持空块，不回退到其它 helper。

    使用示例:
    - stmt = _emit_npu_demo_if(if_op, EmitCContext())
    """

    if op.results:
        raise ctx.emit_error("scf.if", "npu_demo scf.if with results is unsupported")
    cond_expr = _emit_condition_expr(op.cond, ctx)
    lines = [f"{ctx.current_indent}if ({cond_expr}) {{"]
    ctx.push_indent()
    then_lines = _emit_npu_demo_if_region(op.true_region, ctx)
    if then_lines:
        lines.extend(then_lines)
    ctx.pop_indent()
    if op.false_region is not None and len(op.false_region.blocks) > 0:
        lines.append(f"{ctx.current_indent}}} else {{")
        ctx.push_indent()
        else_lines = _emit_npu_demo_if_region(op.false_region, ctx)
        if else_lines:
            lines.extend(else_lines)
        ctx.pop_indent()
        lines.append(f"{ctx.current_indent}}}")
    else:
        lines.append(f"{ctx.current_indent}}}")
    return "\n".join(lines)


def _emit_condition_expr(condition, ctx) -> str:
    """发射 `scf.if` 条件表达式。

    功能说明:
    - 条件值只通过公开 `emit_c_value(...)` 转成右值文本。
    - 不为上下文能力补探测或私有兼容分支。

    使用示例:
    - expr = _emit_condition_expr(if_op.condition, ctx)
    """

    from .. import emit_c_value

    return emit_c_value(condition, ctx)
