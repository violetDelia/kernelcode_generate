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
from xdsl.ir import Region

from ..register import emit_c_impl


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
