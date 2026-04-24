# [immutable-file]
"""tile-elewise 的 `kernel.matmul` expectation。

创建者: 大闸蟹
最后一次更改: 大闸蟹

功能说明:
- 使用 `ircheck` 黑盒锁定 `tile-elewise` 对带 `tile.analysis` 的 `kernel.matmul`
  只切分 `elewise` 轴，不切分 `reduce` 轴。
- 当前覆盖静态 / 动态 / mixed 三类输入。

使用示例:
- `PYTHONPATH=. python expectation/pass/tile/elewise/matmul.py`

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
        FLOAT_DTYPE_IR,
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
        FLOAT_DTYPE_IR,
        SPACE_ATTR,
        memory_ir,
        random_rank3_static_dynamic,
    )

STATIC_M, STATIC_K, STATIC_N, SYM_M, SYM_K, SYM_N = random_rank3_static_dynamic()

STATIC_LHS_IR = memory_ir([STATIC_M, STATIC_K], FLOAT_DTYPE)
STATIC_RHS_IR = memory_ir([STATIC_K, STATIC_N], FLOAT_DTYPE)
STATIC_OUT_IR = memory_ir([STATIC_M, STATIC_N], FLOAT_DTYPE)

DYNAMIC_LHS_IR = memory_ir([SYM_M, SYM_K], FLOAT_DTYPE)
DYNAMIC_RHS_IR = memory_ir([SYM_K, SYM_N], FLOAT_DTYPE)
DYNAMIC_OUT_IR = memory_ir([SYM_M, SYM_N], FLOAT_DTYPE)

MIXED_LHS_IR = memory_ir([STATIC_M, SYM_K], FLOAT_DTYPE)
MIXED_RHS_IR = memory_ir([SYM_K, SYM_N], FLOAT_DTYPE)
MIXED_OUT_IR = memory_ir([STATIC_M, SYM_N], FLOAT_DTYPE)

def _build_case_text(*, func_name: str, lhs_ir: str, rhs_ir: str, out_ir: str, k_expr: str, n_expr: str) -> str:
    return rf"""// COMPILE_ARGS: --pass tile-elewise
// CHECK: builtin.module {{
// CHECK-NEXT: func.func @{func_name}(%[[LHS:{{reg}}]] : {lhs_ir}, %[[RHS:{{reg}}]] : {rhs_ir}, %[[OUT:{{reg}}]] : {out_ir}) {{
// CHECK: %[[LOOP_STEP0:{{reg}}]] = tuner.param : !symbol.int<"[[TILE0:{{val}}]]">
// CHECK-NEXT: %[[LOOP_STEP1:{{reg}}]] = tuner.param : !symbol.int<"[[TILE1:{{val}}]]">
// CHECK-NEXT: %[[LOOP_ZERO0:{{reg}}]] = "symbol.const"() <{{value = 0 : i64}}> : () -> !symbol.int<"0">
// CHECK-NEXT: %[[LOOP_KDIM:{{reg}}]] = "symbol.get_dim"(%[[RHS]]) {{axis = #builtin.int<0>}} : ({rhs_ir}) -> !symbol.int<"{k_expr}">
// CHECK-NEXT: %[[LOOP_ZERO1:{{reg}}]] = "symbol.const"() <{{value = 0 : i64}}> : () -> !symbol.int<"0">
// CHECK-NEXT: %[[LOOP_NDIM:{{reg}}]] = "symbol.get_dim"(%[[OUT]]) {{axis = #builtin.int<1>}} : ({out_ir}) -> !symbol.int<"{n_expr}">
// CHECK-NEXT: %[[LOOP_RHSDIM1:{{reg}}]] = "symbol.get_dim"(%[[RHS]]) {{axis = #builtin.int<1>}} : ({rhs_ir}) -> !symbol.int<"{n_expr}">
// CHECK-NEXT: symbol.for %[[IT0:{{reg}}]] = %[[LOOP_ZERO0]] to %[[LOOP_KDIM]] step %[[LOOP_STEP0]] {{iter = #symbol.iter<start = "0", end = "{k_expr}", step = "[[TILE0]]">}} {{
// CHECK-NEXT:   symbol.for %[[IT1:{{reg}}]] = %[[LOOP_ZERO1]] to %[[LOOP_NDIM]] step %[[LOOP_STEP1]] {{iter = #symbol.iter<start = "0", end = "{n_expr}", step = "[[TILE1]]">}} {{
// CHECK-NEXT:     %[[RV_ONE:{{reg}}]] = "symbol.const"() <{{value = 1 : i64}}> : () -> !symbol.int<"1">
// CHECK-NEXT:     %[[RV:{{reg}}]] = "dma.view"(%[[RHS]], %[[IT0]], %[[LOOP_ZERO0]], %[[LOOP_STEP0]], %[[LOOP_RHSDIM1]], %[[LOOP_RHSDIM1]], %[[RV_ONE]])
// CHECK-NEXT:     %[[OV:{{reg}}]] = "dma.view"(%[[OUT]], %[[LOOP_ZERO0]], %[[IT1]], %[[LOOP_RHSDIM1]], %[[LOOP_STEP1]], %[[LOOP_STEP1]], %[[RV_ONE]])
// CHECK-NEXT:     %[[LV:{{reg}}]] = "dma.view"(%[[LHS]], %[[IT0]], %[[IT1]], %[[LOOP_STEP0]], %[[LOOP_STEP1]], %[[LOOP_STEP1]], %[[RV_ONE]])
// CHECK-NEXT:     "kernel.matmul"(%[[LV]], %[[RV]], %[[OV]]) {{space = {SPACE_ATTR}, tile.analysis = \[\["elewise", "reduce"\], \["reduce", "elewise"\], \["elewise", "elewise"\]\], tile.tile_exprs = \[\["TILE_D0", "TILE_D1"\], \["TILE_D0", "TILE_D1"\], \["TILE_D0", "TILE_D1"\]\]}}
// CHECK-NEXT: }}
// CHECK-NEXT: }}
// CHECK-NEXT: func.return
// CHECK-NEXT: }}
// CHECK-NEXT: }}
builtin.module {{
  func.func @{func_name}(%arg0 : {lhs_ir}, %arg1 : {rhs_ir}, %arg2 : {out_ir}) {{
    "kernel.matmul"(%arg0, %arg1, %arg2) {{space = {SPACE_ATTR}, tile.analysis = [["elewise", "reduce"], ["reduce", "elewise"], ["elewise", "elewise"]], tile.tile_exprs = [["", ""], ["", ""], ["", ""]]}} : ({lhs_ir}, {rhs_ir}, {out_ir}) -> ()
    func.return
  }}
}}
"""


CASE_TEXT_STATIC = _build_case_text(
    func_name="matmul_elewise_static",
    lhs_ir=STATIC_LHS_IR,
    rhs_ir=STATIC_RHS_IR,
    out_ir=STATIC_OUT_IR,
    k_expr=str(STATIC_K),
    n_expr=str(STATIC_N),
)

CASE_TEXT_DYNAMIC = _build_case_text(
    func_name="matmul_elewise_dynamic",
    lhs_ir=DYNAMIC_LHS_IR,
    rhs_ir=DYNAMIC_RHS_IR,
    out_ir=DYNAMIC_OUT_IR,
    k_expr=SYM_K,
    n_expr=SYM_N,
)

CASE_TEXT_MIXED = _build_case_text(
    func_name="matmul_elewise_mixed",
    lhs_ir=MIXED_LHS_IR,
    rhs_ir=MIXED_RHS_IR,
    out_ir=MIXED_OUT_IR,
    k_expr=SYM_K,
    n_expr=SYM_N,
)


def _assert_common(result) -> None:
    assert result.ok is True, (
        f"expected ok=True, got ok={result.ok}, exit_code={result.exit_code}, message={result.message!r}"
    )
    assert result.exit_code == 0, f"expected exit_code=0, got {result.exit_code}"
    assert result.actual_ir.count("symbol.for") == 2
    assert result.actual_ir.count('"dma.view"(') == 3
    assert '"tile.step_value"(' not in result.actual_ir
    assert '"kernel.matmul"' in result.actual_ir
    assert "tile.analysis" in result.actual_ir
    assert "tile.tile_exprs" in result.actual_ir


def _case_static() -> None:
    _assert_common(
        run_ircheck_text(
            CASE_TEXT_STATIC,
            source_path="expectation/pass/tile/elewise/matmul.py:static",
        )
    )


def _case_dynamic() -> None:
    _assert_common(
        run_ircheck_text(
            CASE_TEXT_DYNAMIC,
            source_path="expectation/pass/tile/elewise/matmul.py:dynamic",
        )
    )


def _case_mixed() -> None:
    _assert_common(
        run_ircheck_text(
            CASE_TEXT_MIXED,
            source_path="expectation/pass/tile/elewise/matmul.py:mixed",
        )
    )


def main() -> None:
    failures: list[tuple[str, BaseException]] = []
    run_case(failures, "CASE-matmul-elewise-static", _case_static)
    run_case(failures, "CASE-matmul-elewise-dynamic", _case_dynamic)
    run_case(failures, "CASE-matmul-elewise-mixed", _case_mixed)
    raise_if_failures("tile elewise matmul expectation", failures)


if __name__ == "__main__":
    main()
