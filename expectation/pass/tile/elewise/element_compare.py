# [immutable-file]
"""tile-elewise 的 compare 类 `kernel.binary_elewise` expectation。

创建者: 大闸蟹
最后一次更改: 大闸蟹

功能说明:
- 使用 `ircheck` 黑盒锁定 `tile-elewise` 在 compare 类
  `kernel.binary_elewise(kind=eq/ne/ge/gt)` 上也只切分 `elewise` 轴。
- 当前覆盖 rank2/rank1、静态/动态、多 kind 组合。

使用示例:
- `PYTHONPATH=. python expectation/pass/tile/elewise/element_compare.py`

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
        ARITH_DTYPE,
        ARITH_DTYPE_IR,
        BOOL_DTYPE,
        BOOL_DTYPE_IR,
        SPACE_ATTR,
        memory_ir,
        random_compare_kinds,
        random_rank1_static_dynamic,
        random_rank2_static_dynamic,
    )
else:
    TILE_DIR = REPO_ROOT / "expectation" / "pass" / "tile"
    if str(TILE_DIR) not in sys.path:
        sys.path.insert(0, str(TILE_DIR))
    from _random_shared import (
        ARITH_DTYPE,
        ARITH_DTYPE_IR,
        BOOL_DTYPE,
        BOOL_DTYPE_IR,
        SPACE_ATTR,
        memory_ir,
        random_compare_kinds,
        random_rank1_static_dynamic,
        random_rank2_static_dynamic,
    )

STATIC_M, STATIC_N, SYM_M, SYM_N = random_rank2_static_dynamic()
STATIC_P, SYM_P = random_rank1_static_dynamic()

R2_STATIC_INPUT_IR = memory_ir([STATIC_M, STATIC_N], ARITH_DTYPE)
R2_STATIC_OUTPUT_IR = memory_ir([STATIC_M, STATIC_N], BOOL_DTYPE)
R2_DYNAMIC_INPUT_IR = memory_ir([SYM_M, SYM_N], ARITH_DTYPE)
R2_DYNAMIC_OUTPUT_IR = memory_ir([SYM_M, SYM_N], BOOL_DTYPE)
R1_STATIC_INPUT_IR = memory_ir([STATIC_P], ARITH_DTYPE)
R1_STATIC_OUTPUT_IR = memory_ir([STATIC_P], BOOL_DTYPE)
R1_DYNAMIC_INPUT_IR = memory_ir([SYM_P], ARITH_DTYPE)
R1_DYNAMIC_OUTPUT_IR = memory_ir([SYM_P], BOOL_DTYPE)
R2_STATIC_KIND, R2_DYNAMIC_KIND, R1_STATIC_KIND, R1_DYNAMIC_KIND = random_compare_kinds()

def _build_rank2_case(*, func_name: str, input_ir: str, output_ir: str, dim0_expr: str, dim1_expr: str, kind: str) -> str:
    return rf"""// COMPILE_ARGS: --pass tile-elewise
// CHECK: builtin.module {{
// CHECK-NEXT: func.func @{func_name}(%[[ARG0:{{reg}}]] : {input_ir}, %[[ARG1:{{reg}}]] : {input_ir}, %[[ARG2:{{reg}}]] : {output_ir}) {{
// CHECK: %[[LOOP_STEP0:{{reg}}]] = tuner.param : !symbol.int<"[[TILE0:{{val}}]]">
// CHECK-NEXT: %[[LOOP_STEP1:{{reg}}]] = tuner.param : !symbol.int<"[[TILE1:{{val}}]]">
// CHECK-NEXT: %[[LOOP_ZERO0:{{reg}}]] = "symbol.const"() <{{value = 0 : i64}}> : () -> !symbol.int<"0">
// CHECK-NEXT: %[[LOOP_D0:{{reg}}]] = "symbol.get_dim"(%[[ARG2]]) {{axis = #builtin.int<0>}} : ({output_ir}) -> !symbol.int<"{dim0_expr}">
// CHECK-NEXT: %[[LOOP_ZERO1:{{reg}}]] = "symbol.const"() <{{value = 0 : i64}}> : () -> !symbol.int<"0">
// CHECK-NEXT: %[[LOOP_D1:{{reg}}]] = "symbol.get_dim"(%[[ARG2]]) {{axis = #builtin.int<1>}} : ({output_ir}) -> !symbol.int<"{dim1_expr}">
// CHECK-NEXT: symbol.for %[[IT0:{{reg}}]] = %[[LOOP_ZERO0]] to %[[LOOP_D0]] step %[[LOOP_STEP0]] {{iter = #symbol.iter<start = "0", end = "{dim0_expr}", step = "[[TILE0]]">}} {{
// CHECK-NEXT:   symbol.for %[[IT1:{{reg}}]] = %[[LOOP_ZERO1]] to %[[LOOP_D1]] step %[[LOOP_STEP1]] {{iter = #symbol.iter<start = "0", end = "{dim1_expr}", step = "[[TILE1]]">}} {{
// CHECK-NEXT:     %[[OUT_ONE:{{reg}}]] = "symbol.const"() <{{value = 1 : i64}}> : () -> !symbol.int<"1">
// CHECK-NEXT:     %[[OUT:{{reg}}]] = "dma.view"(%[[ARG2]], %[[IT0]], %[[IT1]], %[[LOOP_STEP0]], %[[LOOP_STEP1]], %[[LOOP_STEP1]], %[[OUT_ONE]])
// CHECK-NEXT:     %[[LHS:{{reg}}]] = "dma.view"(%[[ARG0]], %[[IT0]], %[[IT1]], %[[LOOP_STEP0]], %[[LOOP_STEP1]], %[[LOOP_STEP1]], %[[OUT_ONE]])
// CHECK-NEXT:     %[[RHS:{{reg}}]] = "dma.view"(%[[ARG1]], %[[IT0]], %[[IT1]], %[[LOOP_STEP0]], %[[LOOP_STEP1]], %[[LOOP_STEP1]], %[[OUT_ONE]])
// CHECK-NEXT:     "kernel.binary_elewise"(%[[OUT]], %[[LHS]], %[[RHS]]) {{kind = "{kind}", space = {SPACE_ATTR}, tile.tile_exprs = \[\["TILE_D0", "TILE_D1"\], \["TILE_D0", "TILE_D1"\], \["TILE_D0", "TILE_D1"\]\], tile.analysis = \[\["elewise", "elewise"\], \["elewise", "elewise"\], \["elewise", "elewise"\]\]}}
// CHECK-NEXT: }}
// CHECK-NEXT: }}
// CHECK-NEXT: func.return
// CHECK-NEXT: }}
// CHECK-NEXT: }}
builtin.module {{
  func.func @{func_name}(%arg0 : {input_ir}, %arg1 : {input_ir}, %arg2 : {output_ir}) {{
    "kernel.binary_elewise"(%arg0, %arg1, %arg2) {{kind = "{kind}", space = {SPACE_ATTR}, tile.analysis = [["elewise", "elewise"], ["elewise", "elewise"], ["elewise", "elewise"]], tile.tile_exprs = [["", ""], ["", ""], ["", ""]]}} : ({input_ir}, {input_ir}, {output_ir}) -> ()
    func.return
  }}
}}
"""


def _build_rank1_case(*, func_name: str, input_ir: str, output_ir: str, dim_expr: str, kind: str) -> str:
    return rf"""// COMPILE_ARGS: --pass tile-elewise
// CHECK: builtin.module {{
// CHECK-NEXT: func.func @{func_name}(%[[ARG0:{{reg}}]] : {input_ir}, %[[ARG1:{{reg}}]] : {input_ir}, %[[ARG2:{{reg}}]] : {output_ir}) {{
// CHECK: %[[LOOP_STEP0:{{reg}}]] = tuner.param : !symbol.int<"[[TILE0:{{val}}]]">
// CHECK-NEXT: %[[LOOP_ZERO:{{reg}}]] = "symbol.const"() <{{value = 0 : i64}}> : () -> !symbol.int<"0">
// CHECK-NEXT: %[[LOOP_D0:{{reg}}]] = "symbol.get_dim"(%[[ARG2]]) {{axis = #builtin.int<0>}} : ({output_ir}) -> !symbol.int<"{dim_expr}">
// CHECK-NEXT: symbol.for %[[IT0:{{reg}}]] = %[[LOOP_ZERO]] to %[[LOOP_D0]] step %[[LOOP_STEP0]] {{iter = #symbol.iter<start = "0", end = "{dim_expr}", step = "[[TILE0]]">}} {{
// CHECK-NEXT:   %[[OUT_ONE:{{reg}}]] = "symbol.const"() <{{value = 1 : i64}}> : () -> !symbol.int<"1">
// CHECK-NEXT:   %[[OUT:{{reg}}]] = "dma.view"(%[[ARG2]], %[[IT0]], %[[LOOP_STEP0]], %[[OUT_ONE]])
// CHECK-NEXT:   %[[LHS:{{reg}}]] = "dma.view"(%[[ARG0]], %[[IT0]], %[[LOOP_STEP0]], %[[OUT_ONE]])
// CHECK-NEXT:   %[[RHS:{{reg}}]] = "dma.view"(%[[ARG1]], %[[IT0]], %[[LOOP_STEP0]], %[[OUT_ONE]])
// CHECK-NEXT:   "kernel.binary_elewise"(%[[OUT]], %[[LHS]], %[[RHS]]) {{kind = "{kind}", space = {SPACE_ATTR}, tile.tile_exprs = \[\["TILE_D0"\], \["TILE_D0"\], \["TILE_D0"\]\], tile.analysis = \[\["elewise"\], \["elewise"\], \["elewise"\]\]}}
// CHECK-NEXT: }}
// CHECK-NEXT: func.return
// CHECK-NEXT: }}
// CHECK-NEXT: }}
builtin.module {{
  func.func @{func_name}(%arg0 : {input_ir}, %arg1 : {input_ir}, %arg2 : {output_ir}) {{
    "kernel.binary_elewise"(%arg0, %arg1, %arg2) {{kind = "{kind}", space = {SPACE_ATTR}, tile.analysis = [["elewise"], ["elewise"], ["elewise"]], tile.tile_exprs = [[""], [""], [""]]}} : ({input_ir}, {input_ir}, {output_ir}) -> ()
    func.return
  }}
}}
"""


CASE_TEXT_R2_STATIC_EQ = _build_rank2_case(
    func_name="compare_rank2_static",
    input_ir=R2_STATIC_INPUT_IR,
    output_ir=R2_STATIC_OUTPUT_IR,
    dim0_expr=str(STATIC_M),
    dim1_expr=str(STATIC_N),
    kind=R2_STATIC_KIND,
)

CASE_TEXT_R2_DYNAMIC_GT = _build_rank2_case(
    func_name="compare_rank2_dynamic",
    input_ir=R2_DYNAMIC_INPUT_IR,
    output_ir=R2_DYNAMIC_OUTPUT_IR,
    dim0_expr=SYM_M,
    dim1_expr=SYM_N,
    kind=R2_DYNAMIC_KIND,
)

CASE_TEXT_R1_STATIC_NE = _build_rank1_case(
    func_name="compare_rank1_static",
    input_ir=R1_STATIC_INPUT_IR,
    output_ir=R1_STATIC_OUTPUT_IR,
    dim_expr=str(STATIC_P),
    kind=R1_STATIC_KIND,
)

CASE_TEXT_R1_DYNAMIC_GE = _build_rank1_case(
    func_name="compare_rank1_dynamic",
    input_ir=R1_DYNAMIC_INPUT_IR,
    output_ir=R1_DYNAMIC_OUTPUT_IR,
    dim_expr=SYM_P,
    kind=R1_DYNAMIC_KIND,
)


def _assert_rank2(result) -> None:
    assert result.ok is True, (
        f"expected ok=True, got ok={result.ok}, exit_code={result.exit_code}, message={result.message!r}"
    )
    assert result.exit_code == 0, f"expected exit_code=0, got {result.exit_code}"
    assert result.actual_ir.count("symbol.for") == 2
    assert result.actual_ir.count('"dma.view"(') == 3
    assert '"tile.step_value"(' not in result.actual_ir
    assert '"kernel.binary_elewise"' in result.actual_ir
    assert "tile.analysis" in result.actual_ir
    assert "tile.tile_exprs" in result.actual_ir


def _assert_rank1(result) -> None:
    assert result.ok is True, (
        f"expected ok=True, got ok={result.ok}, exit_code={result.exit_code}, message={result.message!r}"
    )
    assert result.exit_code == 0, f"expected exit_code=0, got {result.exit_code}"
    assert result.actual_ir.count("symbol.for") == 1
    assert result.actual_ir.count('"dma.view"(') == 3
    assert '"tile.step_value"(' not in result.actual_ir
    assert '"kernel.binary_elewise"' in result.actual_ir
    assert "tile.analysis" in result.actual_ir
    assert "tile.tile_exprs" in result.actual_ir


def _case_r2_static_eq() -> None:
    _assert_rank2(
        run_ircheck_text(
            CASE_TEXT_R2_STATIC_EQ,
            source_path="expectation/pass/tile/elewise/element_compare.py:r2-static-eq",
        )
    )


def _case_r2_dynamic_gt() -> None:
    _assert_rank2(
        run_ircheck_text(
            CASE_TEXT_R2_DYNAMIC_GT,
            source_path="expectation/pass/tile/elewise/element_compare.py:r2-dynamic-gt",
        )
    )


def _case_r1_static_ne() -> None:
    _assert_rank1(
        run_ircheck_text(
            CASE_TEXT_R1_STATIC_NE,
            source_path="expectation/pass/tile/elewise/element_compare.py:r1-static-ne",
        )
    )


def _case_r1_dynamic_ge() -> None:
    _assert_rank1(
        run_ircheck_text(
            CASE_TEXT_R1_DYNAMIC_GE,
            source_path="expectation/pass/tile/elewise/element_compare.py:r1-dynamic-ge",
        )
    )


def main() -> None:
    failures: list[tuple[str, BaseException]] = []
    run_case(failures, "CASE-r2-static-eq", _case_r2_static_eq)
    run_case(failures, "CASE-r2-dynamic-gt", _case_r2_dynamic_gt)
    run_case(failures, "CASE-r1-static-ne", _case_r1_static_ne)
    run_case(failures, "CASE-r1-dynamic-ge", _case_r1_dynamic_ge)
    raise_if_failures("tile elewise element_compare expectation", failures)


if __name__ == "__main__":
    main()
