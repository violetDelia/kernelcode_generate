# [immutable-file]
"""tile-elewise 的 `fc` 组合链 expectation。

创建者: 大闸蟹
最后一次更改: 大闸蟹

功能说明:
- 使用 `ircheck` 黑盒锁定 `tile-elewise` 在 `fc` 风格链路上只切分
  `elewise` 轴，不切分 `reduce` 轴。
- 当前覆盖静态 / 动态 / mixed 三类输入。

使用示例:
- `PYTHONPATH=. python expectation/pass/tile/elewise/fc.py`

关联文件:
- spec: [`spec/pass/lowering/tile.md`](spec/pass/lowering/tile.md)
- test: [`test/pass/test_lowering_tile.py`](test/pass/test_lowering_tile.py)
- 功能实现: [`kernel_gen/passes/lowering/tile.py`](kernel_gen/passes/lowering/tile.py)
- 功能实现: [`kernel_gen/tools/ircheck.py`](kernel_gen/tools/ircheck.py)
"""

from __future__ import annotations

from pathlib import Path
import sys

REPO_ROOT = Path(__file__).resolve().parents[4]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from expectation.utils.case_runner import raise_if_failures, run_case
from kernel_gen.tools.ircheck import run_ircheck_text

if __package__:
    from .._random_shared import (
        FLOAT_DTYPE,
        SPACE_ATTR,
        memory_ir,
        random_rank3_static_dynamic,
    )
else:
    TILE_DIR = REPO_ROOT / "expectation" / "pass" / "tile"
    if str(TILE_DIR) not in sys.path:
        sys.path.insert(0, str(TILE_DIR))
    from _random_shared import (
        FLOAT_DTYPE,
        SPACE_ATTR,
        memory_ir,
        random_rank3_static_dynamic,
    )

STATIC_BATCH, STATIC_IN, STATIC_OUT, SYM_BATCH, SYM_IN, SYM_OUT = random_rank3_static_dynamic()

STATIC_OUT_IR = memory_ir([STATIC_BATCH, STATIC_OUT], FLOAT_DTYPE)
STATIC_X_IR = memory_ir([STATIC_BATCH, STATIC_IN], FLOAT_DTYPE)
STATIC_WEIGHT_T_IR = memory_ir([STATIC_IN, STATIC_OUT], FLOAT_DTYPE)
STATIC_BIAS_IR = memory_ir([STATIC_OUT], FLOAT_DTYPE)

DYNAMIC_OUT_IR = memory_ir([SYM_BATCH, SYM_OUT], FLOAT_DTYPE)
DYNAMIC_X_IR = memory_ir([SYM_BATCH, SYM_IN], FLOAT_DTYPE)
DYNAMIC_WEIGHT_T_IR = memory_ir([SYM_IN, SYM_OUT], FLOAT_DTYPE)
DYNAMIC_BIAS_IR = memory_ir([SYM_OUT], FLOAT_DTYPE)

MIXED_OUT_IR = memory_ir([STATIC_BATCH, SYM_OUT], FLOAT_DTYPE)
MIXED_X_IR = memory_ir([STATIC_BATCH, STATIC_IN], FLOAT_DTYPE)
MIXED_WEIGHT_T_IR = memory_ir([STATIC_IN, SYM_OUT], FLOAT_DTYPE)
MIXED_BIAS_IR = memory_ir([SYM_OUT], FLOAT_DTYPE)

def _build_case_text(*, func_name: str, out_ir: str, x_ir: str, weight_t_ir: str, bias_ir: str, batch_expr: str, in_expr: str, out_expr: str) -> str:
    return rf"""// COMPILE_ARGS: --pass tile-elewise
// CHECK: builtin.module {{
// CHECK-NEXT: func.func @{func_name}(%[[OUT:{{reg}}]] : {out_ir}, %[[X:{{reg}}]] : {x_ir}, %[[W:{{reg}}]] : {weight_t_ir}, %[[B:{{reg}}]] : {bias_ir}) {{
// CHECK: %[[OUTD0:{{reg}}]] = "symbol.get_dim"(%[[OUT]]) {{axis = #builtin.int<0>}} : ({out_ir}) -> !symbol.int<"{batch_expr}">
// CHECK-NEXT: %[[OUTD1:{{reg}}]] = "symbol.get_dim"(%[[OUT]]) {{axis = #builtin.int<1>}} : ({out_ir}) -> !symbol.int<"{out_expr}">
// CHECK-NEXT: %[[BIASB:{{reg}}]] = "dma.alloc"(%[[OUTD0]], %[[OUTD1]]) <{{operandSegmentSizes = array<i32: 2>}}> : (!symbol.int<"{batch_expr}">, !symbol.int<"{out_expr}">) -> {out_ir}
// CHECK-NEXT: %[[MATOUT:{{reg}}]] = "dma.alloc"(%[[OUTD0]], %[[OUTD1]]) <{{operandSegmentSizes = array<i32: 2>}}> : (!symbol.int<"{batch_expr}">, !symbol.int<"{out_expr}">) -> {out_ir}
// CHECK-NEXT: %[[B0:{{reg}}]] = tuner.param : !symbol.int<"[[B0_VAL:{{val}}]]">
// CHECK-NEXT: %[[M0:{{reg}}]] = tuner.param : !symbol.int<"[[M0_VAL:{{val}}]]">
// CHECK-NEXT: %[[M1:{{reg}}]] = tuner.param : !symbol.int<"[[M1_VAL:{{val}}]]">
// CHECK-NEXT: %[[E0:{{reg}}]] = tuner.param : !symbol.int<"[[E0_VAL:{{val}}]]">
// CHECK-NEXT: %[[E1:{{reg}}]] = tuner.param : !symbol.int<"[[E1_VAL:{{val}}]]">
// CHECK-NEXT: %[[ZB0:{{reg}}]] = "symbol.const"() <{{value = 0 : i64}}> : () -> !symbol.int<"0">
// CHECK-NEXT: %[[BD0:{{reg}}]] = "symbol.get_dim"(%[[BIASB]]) {{axis = #builtin.int<0>}} : ({out_ir}) -> !symbol.int<"{batch_expr}">
// CHECK-NEXT: %[[ZB1:{{reg}}]] = "symbol.const"() <{{value = 0 : i64}}> : () -> !symbol.int<"0">
// CHECK-NEXT: %[[BD1:{{reg}}]] = "symbol.get_dim"(%[[BIASB]]) {{axis = #builtin.int<1>}} : ({out_ir}) -> !symbol.int<"{out_expr}">
// CHECK-NEXT: symbol.for %[[BIT:{{reg}}]] = %[[ZB1]] to %[[BD1]] step %[[B0]] {{iter = #symbol.iter<start = "0", end = "{out_expr}", step = "[[B0_VAL]]">}} {{
// CHECK-NEXT:   %[[BIASV_ONE:{{reg}}]] = "symbol.const"() <{{value = 1 : i64}}> : () -> !symbol.int<"1">
// CHECK-NEXT:   %[[BIASV:{{reg}}]] = "dma.view"(%[[BIASB]], %[[ZB0]], %[[BIT]], %[[BD0]], %[[B0]], %[[B0]], %[[BIASV_ONE]])
// CHECK-NEXT:   %[[SRCBIAS:{{reg}}]] = "dma.view"(%[[B]], %[[BIT]], %[[B0]], %[[BIASV_ONE]])
// CHECK-NEXT:   "dma.broadcast"(%[[BIASV]], %[[SRCBIAS]]) {{tile.tile_exprs = \[\["", "TILE_B0"\], \["", "TILE_B0"\]\], tile.analysis = \[\["elewise", "elewise"\], \["expand", "elewise"\]\]}} :
// CHECK-NEXT: }}
// CHECK-NEXT: %[[ZM0:{{reg}}]] = "symbol.const"() <{{value = 0 : i64}}> : () -> !symbol.int<"0">
// CHECK-NEXT: %[[WD0:{{reg}}]] = "symbol.get_dim"(%[[W]]) {{axis = #builtin.int<0>}} : ({weight_t_ir}) -> !symbol.int<"{in_expr}">
// CHECK-NEXT: %[[ZM1:{{reg}}]] = "symbol.const"() <{{value = 0 : i64}}> : () -> !symbol.int<"0">
// CHECK-NEXT: %[[OD1:{{reg}}]] = "symbol.get_dim"(%[[MATOUT]]) {{axis = #builtin.int<1>}} : ({out_ir}) -> !symbol.int<"{out_expr}">
// CHECK-NEXT: %[[WD1:{{reg}}]] = "symbol.get_dim"(%[[W]]) {{axis = #builtin.int<1>}} : ({weight_t_ir}) -> !symbol.int<"{out_expr}">
// CHECK-NEXT: symbol.for %[[MIT0:{{reg}}]] = %[[ZM0]] to %[[WD0]] step %[[M0]] {{
// CHECK-NEXT:   symbol.for %[[MIT1:{{reg}}]] = %[[ZM1]] to %[[OD1]] step %[[M1]] {{
// CHECK-NEXT:     %[[WV_ONE:{{reg}}]] = "symbol.const"() <{{value = 1 : i64}}> : () -> !symbol.int<"1">
// CHECK-NEXT:     %[[WV:{{reg}}]] = "dma.view"(%[[W]], %[[MIT0]], %[[ZM0]], %[[M0]], %[[WD1]], %[[WD1]], %[[WV_ONE]])
// CHECK-NEXT:     %[[MATV:{{reg}}]] = "dma.view"(%[[MATOUT]], %[[ZM0]], %[[MIT1]], %[[WD1]], %[[M1]], %[[M1]], %[[WV_ONE]])
// CHECK-NEXT:     %[[XV:{{reg}}]] = "dma.view"(%[[X]], %[[MIT0]], %[[MIT1]], %[[M0]], %[[M1]], %[[M1]], %[[WV_ONE]])
// CHECK-NEXT:     "kernel.matmul"(%[[XV]], %[[WV]], %[[MATV]]) {{space = {SPACE_ATTR}, tile.analysis = \[\["elewise", "reduce"\], \["reduce", "elewise"\], \["elewise", "elewise"\]\], tile.tile_exprs = \[\["TILE_M0", "TILE_M1"\], \["TILE_M0", "TILE_M1"\], \["TILE_M0", "TILE_M1"\]\]}}
// CHECK-NEXT: }}
// CHECK-NEXT: }}
// CHECK-NEXT: %[[ZE0:{{reg}}]] = "symbol.const"() <{{value = 0 : i64}}> : () -> !symbol.int<"0">
// CHECK-NEXT: %[[ED0:{{reg}}]] = "symbol.get_dim"(%[[BIASB]]) {{axis = #builtin.int<0>}} : ({out_ir}) -> !symbol.int<"{batch_expr}">
// CHECK-NEXT: %[[ZE1:{{reg}}]] = "symbol.const"() <{{value = 0 : i64}}> : () -> !symbol.int<"0">
// CHECK-NEXT: %[[ED1:{{reg}}]] = "symbol.get_dim"(%[[BIASB]]) {{axis = #builtin.int<1>}} : ({out_ir}) -> !symbol.int<"{out_expr}">
// CHECK-NEXT: symbol.for %[[EIT0:{{reg}}]] = %[[ZE0]] to %[[ED0]] step %[[E0]] {{
// CHECK-NEXT:   symbol.for %[[EIT1:{{reg}}]] = %[[ZE1]] to %[[ED1]] step %[[E1]] {{
// CHECK-NEXT:     %[[OUTV_ONE:{{reg}}]] = "symbol.const"() <{{value = 1 : i64}}> : () -> !symbol.int<"1">
// CHECK-NEXT:     %[[OUTV:{{reg}}]] = "dma.view"(%[[OUT]], %[[EIT0]], %[[EIT1]], %[[E0]], %[[E1]], %[[E1]], %[[OUTV_ONE]])
// CHECK-NEXT:     %[[MATOUTV:{{reg}}]] = "dma.view"(%[[MATOUT]], %[[EIT0]], %[[EIT1]], %[[E0]], %[[E1]], %[[E1]], %[[OUTV_ONE]])
// CHECK-NEXT:     %[[BIASOUTV:{{reg}}]] = "dma.view"(%[[BIASB]], %[[EIT0]], %[[EIT1]], %[[E0]], %[[E1]], %[[E1]], %[[OUTV_ONE]])
// CHECK-NEXT:     "kernel.binary_elewise"(%[[OUTV]], %[[MATOUTV]], %[[BIASOUTV]]) {{kind = "add", space = {SPACE_ATTR}, tile.tile_exprs = \[\["TILE_E0", "TILE_E1"\], \["TILE_E0", "TILE_E1"\], \["TILE_E0", "TILE_E1"\]\], tile.analysis = \[\["elewise", "elewise"\], \["elewise", "elewise"\], \["elewise", "elewise"\]\]}}
// CHECK-NEXT: }}
// CHECK-NEXT: }}
// CHECK-NEXT: func.return
// CHECK-NEXT: }}
// CHECK-NEXT: }}
builtin.module {{
  func.func @{func_name}(%out : {out_ir}, %x : {x_ir}, %weight_t : {weight_t_ir}, %bias : {bias_ir}) {{
    %d0 = "symbol.get_dim"(%out) {{axis = #builtin.int<0>}} : ({out_ir}) -> !symbol.int<"{batch_expr}">
    %d1 = "symbol.get_dim"(%out) {{axis = #builtin.int<1>}} : ({out_ir}) -> !symbol.int<"{out_expr}">
    %bias_b = "dma.alloc"(%d0, %d1) <{{operandSegmentSizes = array<i32: 2>}}> : (!symbol.int<"{batch_expr}">, !symbol.int<"{out_expr}">) -> {out_ir}
    %mat_out = "dma.alloc"(%d0, %d1) <{{operandSegmentSizes = array<i32: 2>}}> : (!symbol.int<"{batch_expr}">, !symbol.int<"{out_expr}">) -> {out_ir}
    "dma.broadcast"(%bias_b, %bias) {{tile.analysis = [["elewise", "elewise"], ["expand", "elewise"]], tile.tile_exprs = [["", ""], ["", ""]]}} : ({out_ir}, {bias_ir}) -> ()
    "kernel.matmul"(%x, %weight_t, %mat_out) {{space = {SPACE_ATTR}, tile.analysis = [["elewise", "reduce"], ["reduce", "elewise"], ["elewise", "elewise"]], tile.tile_exprs = [["", ""], ["", ""], ["", ""]]}} : ({x_ir}, {weight_t_ir}, {out_ir}) -> ()
    "kernel.binary_elewise"(%out, %mat_out, %bias_b) {{kind = "add", space = {SPACE_ATTR}, tile.analysis = [["elewise", "elewise"], ["elewise", "elewise"], ["elewise", "elewise"]], tile.tile_exprs = [["", ""], ["", ""], ["", ""]]}} : ({out_ir}, {out_ir}, {out_ir}) -> ()
    func.return
  }}
}}
"""


CASE_TEXT_STATIC = _build_case_text(
    func_name="fc_elewise_static",
    out_ir=STATIC_OUT_IR,
    x_ir=STATIC_X_IR,
    weight_t_ir=STATIC_WEIGHT_T_IR,
    bias_ir=STATIC_BIAS_IR,
    batch_expr=str(STATIC_BATCH),
    in_expr=str(STATIC_IN),
    out_expr=str(STATIC_OUT),
)

CASE_TEXT_DYNAMIC = _build_case_text(
    func_name="fc_elewise_dynamic",
    out_ir=DYNAMIC_OUT_IR,
    x_ir=DYNAMIC_X_IR,
    weight_t_ir=DYNAMIC_WEIGHT_T_IR,
    bias_ir=DYNAMIC_BIAS_IR,
    batch_expr=SYM_BATCH,
    in_expr=SYM_IN,
    out_expr=SYM_OUT,
)

CASE_TEXT_MIXED = _build_case_text(
    func_name="fc_elewise_mixed",
    out_ir=MIXED_OUT_IR,
    x_ir=MIXED_X_IR,
    weight_t_ir=MIXED_WEIGHT_T_IR,
    bias_ir=MIXED_BIAS_IR,
    batch_expr=str(STATIC_BATCH),
    in_expr=str(STATIC_IN),
    out_expr=SYM_OUT,
)


def _assert_common(result) -> None:
    assert result.ok is True, (
        f"expected ok=True, got ok={result.ok}, exit_code={result.exit_code}, message={result.message!r}"
    )
    assert result.exit_code == 0, f"expected exit_code=0, got {result.exit_code}"
    assert result.actual_ir.count("symbol.for") == 5
    assert '"tile.step_value"(' not in result.actual_ir
    assert result.actual_ir.count('"dma.alloc"(') >= 2
    assert '"dma.broadcast"' in result.actual_ir
    assert '"kernel.matmul"' in result.actual_ir
    assert '"kernel.binary_elewise"' in result.actual_ir
    assert "tile.analysis" in result.actual_ir
    assert "tile.tile_exprs" in result.actual_ir


def _case_static() -> None:
    _assert_common(
        run_ircheck_text(
            CASE_TEXT_STATIC,
            source_path="expectation/pass/tile/elewise/fc.py:static",
        )
    )


def _case_dynamic() -> None:
    _assert_common(
        run_ircheck_text(
            CASE_TEXT_DYNAMIC,
            source_path="expectation/pass/tile/elewise/fc.py:dynamic",
        )
    )


def _case_mixed() -> None:
    _assert_common(
        run_ircheck_text(
            CASE_TEXT_MIXED,
            source_path="expectation/pass/tile/elewise/fc.py:mixed",
        )
    )


def main() -> None:
    failures: list[tuple[str, BaseException]] = []
    run_case(failures, "CASE-fc-elewise-static", _case_static)
    run_case(failures, "CASE-fc-elewise-dynamic", _case_dynamic)
    run_case(failures, "CASE-fc-elewise-mixed", _case_mixed)
    raise_if_failures("tile elewise fc expectation", failures)


if __name__ == "__main__":
    main()
