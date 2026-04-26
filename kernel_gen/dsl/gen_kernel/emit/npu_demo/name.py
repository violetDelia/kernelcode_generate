from __future__ import annotations

from xdsl.ir import BlockArgument, SSAValue

from kernel_gen.dialect.symbol import SymbolConstOp
from kernel_gen.dialect.tuner import TunerCostOp

from ..register import emit_c_name_impl


@emit_c_name_impl(BlockArgument, target="npu_demo")
def _emit_npu_demo_block_arg_name(value: SSAValue, ctx, preferred: str | None, prefix: str) -> str:
    if preferred is not None:
        return preferred
    if prefix != "v":
        counters = ctx.config.setdefault("name_counters", {})
        current = int(counters.get(prefix, 0))
        counters[prefix] = current + 1
        return f"{prefix}{current}"
    return f"arg{value.index}"


@emit_c_name_impl(SymbolConstOp, target="npu_demo")
def _emit_npu_demo_symbol_const_name(value: SSAValue, _ctx, _preferred: str | None, _prefix: str) -> str:
    owner = value.owner
    if not isinstance(owner, SymbolConstOp):
        raise ValueError("symbol.const name handler only supports SymbolConstOp")
    literal = owner.value.data
    if literal >= 0:
        return f"c_{literal}"
    return f"c_m{abs(literal)}"


@emit_c_name_impl(TunerCostOp, target="npu_demo")
def _emit_npu_demo_tuner_cost_name(value: SSAValue, ctx, _preferred: str | None, _prefix: str) -> str:
    counters = ctx.config.setdefault("name_counters", {})
    current = int(counters.get("cost", 0))
    counters["cost"] = current + 1
    return f"cost{current}"
