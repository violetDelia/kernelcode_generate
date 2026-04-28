"""npu_demo target naming rules.

创建者: OpenAI Codex
最后一次更改: 守护最好的爱莉希雅

功能说明:
- 注册 npu_demo target 的 block arg / symbol / tuner cost 命名规则。
- 只承接当前 target 私有命名策略，不构成包根公开 API。

API 列表:
- 无（仅 target 私有注册实现）

使用示例:
- from kernel_gen.dsl.gen_kernel import EmitCContext, emit_c_op
- stmt = emit_c_op(op, EmitCContext())

关联文件:
- spec: [spec/dsl/gen_kernel/emit.md](../../../../../spec/dsl/gen_kernel/emit.md)
- spec: [spec/dsl/gen_kernel/emit/register.md](../../../../../spec/dsl/gen_kernel/emit/register.md)
- test: [test/dsl/gen_kernel/emit/test_emit.py](../../../../../test/dsl/gen_kernel/emit/test_emit.py)
- 功能实现: [kernel_gen/dsl/gen_kernel/emit/npu_demo/name.py](.)
"""

from __future__ import annotations

import re

from xdsl.dialects import scf
from xdsl.ir import BlockArgument, SSAValue

from kernel_gen.dialect.dma import DmaViewOp
from kernel_gen.dialect.symbol import SymbolCastOp, SymbolConstOp, SymbolForOp, SymbolToIntOp
from kernel_gen.dialect.tuner import TunerCostOp

from ..register import emit_c_name_impl


_C_IDENTIFIER = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


@emit_c_name_impl(BlockArgument, target="npu_demo")
def _emit_npu_demo_block_arg_name(value: SSAValue, ctx) -> str:
    parent_op = value.owner.parent_op()
    if value.index == 0 and isinstance(parent_op, (scf.ForOp, SymbolForOp)):
        return ctx.allocate_name("i")
    return f"arg{value.index}"


@emit_c_name_impl(SymbolConstOp, target="npu_demo")
def _emit_npu_demo_symbol_const_name(value: SSAValue, _ctx) -> str:
    owner = value.owner
    if not isinstance(owner, SymbolConstOp):
        raise ValueError("symbol.const name handler only supports SymbolConstOp")
    literal = owner.value.data
    if literal >= 0:
        return f"c_{literal}"
    return f"c_m{abs(literal)}"


@emit_c_name_impl(SymbolToIntOp, SymbolCastOp, target="npu_demo")
def _emit_npu_demo_symbol_cast_name(value: SSAValue, ctx) -> str:
    owner = value.owner
    if not isinstance(owner, (SymbolToIntOp, SymbolCastOp)):
        raise ValueError("symbol cast name handler only supports SymbolToIntOp / SymbolCastOp")
    from .. import emit_c_value

    source_name = emit_c_value(owner.source, ctx)
    type_name = ctx.dispatch_type(owner.result.type)
    if _C_IDENTIFIER.match(source_name):
        return f"{source_name}_cast_{type_name}"
    return f"value_cast_{type_name}"


@emit_c_name_impl(DmaViewOp, target="npu_demo")
def _emit_npu_demo_dma_view_name(value: SSAValue, ctx) -> str:
    """生成 npu_demo `dma.view` 结果名称。

    创建者: OpenAI Codex
    最后一次更改: OpenAI Codex

    功能说明:
    - 基于 source 名称生成 `source_1` 风格结果名。
    - 实际去重由 `EmitCContext.create_or_get_name(...)` 统一处理。

    使用示例:
    - name = _emit_npu_demo_dma_view_name(view_op.result, ctx)
    """

    owner = value.owner
    if not isinstance(owner, DmaViewOp):
        raise ValueError("dma.view name handler only supports DmaViewOp")
    source_name = ctx.lookup_name(owner.source)
    if source_name is None:
        source_name = ctx.create_or_get_name(owner.source)
    if _C_IDENTIFIER.match(source_name):
        return f"{source_name}_1"
    return "view"


@emit_c_name_impl(TunerCostOp, target="npu_demo")
def _emit_npu_demo_tuner_cost_name(value: SSAValue, ctx) -> str:
    return ctx.allocate_name("cost")
