# [immutable-file]
"""tile-elewise 的 `dma.broadcast` expectation。

创建者: 大闸蟹
最后一次更改: 大闸蟹

功能说明:
- 使用 `ircheck` 黑盒锁定 `tile-elewise` 消费已有 `tile.analysis` 后，
  只切分 `elewise` 轴，不再做 analysis。
- 覆盖静态与动态两条路径，并保持低 rank source view 仍使用 source 自身 rank。

使用示例:
- `PYTHONPATH=. python expectation/pass/tile/elewise/broadcast.py`

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
        memory_ir,
        random_rank2_static_dynamic,
    )
else:
    TILE_DIR = REPO_ROOT / "expectation" / "pass" / "tile"
    if str(TILE_DIR) not in sys.path:
        sys.path.insert(0, str(TILE_DIR))
    from _random_shared import (
        ARITH_DTYPE,
        ARITH_DTYPE_IR,
        memory_ir,
        random_rank2_static_dynamic,
    )

STATIC_M, STATIC_N, SYM_M, SYM_N = random_rank2_static_dynamic()
STATIC_TARGET_IR = memory_ir([STATIC_M, STATIC_N], ARITH_DTYPE)
STATIC_SOURCE_IR = memory_ir([1, STATIC_N], ARITH_DTYPE)
DYNAMIC_TARGET_IR = memory_ir([SYM_M, SYM_N], ARITH_DTYPE)
DYNAMIC_SOURCE_IR = memory_ir([1, SYM_N], ARITH_DTYPE)

def _build_case_text(*, func_name: str, target_ir: str, source_ir: str, dim0_expr: str, dim1_expr: str, src_dim0_expr: str) -> str:
    return rf"""// COMPILE_ARGS: --pass tile-elewise
// CHECK: builtin.module {{
// CHECK-NEXT: func.func @{func_name}(%[[TARGET:{{reg}}]] : {target_ir}, %[[SOURCE:{{reg}}]] : {source_ir}) {{
// CHECK-NEXT: %[[LOOP_STEP:{{reg}}]] = tuner.param : !symbol.int<"[[TILE0:{{val}}]]">
// CHECK-NEXT: %[[LOOP_ZERO0:{{reg}}]] = "symbol.const"() <{{value = 0 : i64}}> : () -> !symbol.int<"0">
// CHECK-NEXT: %[[LOOP_D0:{{reg}}]] = "symbol.get_dim"(%[[TARGET]]) {{axis = #builtin.int<0>}} : ({target_ir}) -> !symbol.int<"{dim0_expr}">
// CHECK-NEXT: %[[LOOP_ZERO1:{{reg}}]] = "symbol.const"() <{{value = 0 : i64}}> : () -> !symbol.int<"0">
// CHECK-NEXT: %[[LOOP_D1:{{reg}}]] = "symbol.get_dim"(%[[TARGET]]) {{axis = #builtin.int<1>}} : ({target_ir}) -> !symbol.int<"{dim1_expr}">
// CHECK-NEXT: %[[SV_D0:{{reg}}]] = "symbol.get_dim"(%[[SOURCE]]) {{axis = #builtin.int<0>}} : ({source_ir}) -> !symbol.int<"{src_dim0_expr}">
// CHECK-NEXT: symbol.for %[[IT:{{reg}}]] = %[[LOOP_ZERO1]] to %[[LOOP_D1]] step %[[LOOP_STEP]] {{iter = #symbol.iter<start = "0", end = "{dim1_expr}", step = "[[TILE0]]">}} {{
// CHECK-NEXT:   %[[TV_ONE:{{reg}}]] = "symbol.const"() <{{value = 1 : i64}}> : () -> !symbol.int<"1">
// CHECK-NEXT:   %[[TV:{{reg}}]] = "dma.view"(%[[TARGET]], %[[LOOP_ZERO0]], %[[IT]], %[[LOOP_D0]], %[[LOOP_STEP]], %[[LOOP_STEP]], %[[TV_ONE]]) <{{operandSegmentSizes = array<i32: 1, 2, 2, 2>}}> : ({target_ir}, !symbol.int<"0">, !symbol.iter<start = "0", end = "{dim1_expr}", step = "[[TILE0]]">, !symbol.int<"{dim0_expr}">, !symbol.int<"[[TILE0]]">, !symbol.int<"[[TILE0]]">, !symbol.int<"1">) -> !nn.memory<[{dim0_expr}, [[TILE0]]], [[[TILE0]], 1], {ARITH_DTYPE_IR}, #nn.space<global>>
// CHECK-NEXT:   %[[SV:{{reg}}]] = "dma.view"(%[[SOURCE]], %[[LOOP_ZERO0]], %[[IT]], %[[SV_D0]], %[[LOOP_STEP]], %[[LOOP_STEP]], %[[TV_ONE]]) <{{operandSegmentSizes = array<i32: 1, 2, 2, 2>}}> : ({source_ir}, !symbol.int<"0">, !symbol.iter<start = "0", end = "{dim1_expr}", step = "[[TILE0]]">, !symbol.int<"{src_dim0_expr}">, !symbol.int<"[[TILE0]]">, !symbol.int<"[[TILE0]]">, !symbol.int<"1">) -> !nn.memory<[{src_dim0_expr}, [[TILE0]]], [[[TILE0]], 1], {ARITH_DTYPE_IR}, #nn.space<global>>
// CHECK-NEXT:   "dma.broadcast"(%[[TV]], %[[SV]]) {{tile.tile_exprs = \[\["", "[[TILE0]]"\], \["", "[[TILE0]]"\]\], tile.analysis = \[\["elewise", "elewise"\], \["expand", "elewise"\]\]}} : (!nn.memory<[{dim0_expr}, [[TILE0]]], [[[TILE0]], 1], {ARITH_DTYPE_IR}, #nn.space<global>>, !nn.memory<[{src_dim0_expr}, [[TILE0]]], [[[TILE0]], 1], {ARITH_DTYPE_IR}, #nn.space<global>>) -> ()
// CHECK-NEXT: }}
// CHECK-NEXT: func.return
// CHECK-NEXT: }}
// CHECK-NEXT: }}
builtin.module {{
  func.func @{func_name}(%arg0 : {target_ir}, %arg1 : {source_ir}) {{
    "dma.broadcast"(%arg0, %arg1) {{tile.analysis = [["elewise", "elewise"], ["expand", "elewise"]], tile.tile_exprs = [["", ""], ["", ""]]}} : ({target_ir}, {source_ir}) -> ()
    func.return
  }}
}}
"""


CASE_TEXT_STATIC = _build_case_text(
    func_name="broadcast_tiled",
    target_ir=STATIC_TARGET_IR,
    source_ir=STATIC_SOURCE_IR,
    dim0_expr=str(STATIC_M),
    dim1_expr=str(STATIC_N),
    src_dim0_expr="1",
)

CASE_TEXT_DYNAMIC = _build_case_text(
    func_name="broadcast_tiled_dynamic",
    target_ir=DYNAMIC_TARGET_IR,
    source_ir=DYNAMIC_SOURCE_IR,
    dim0_expr=SYM_M,
    dim1_expr=SYM_N,
    src_dim0_expr="1",
)


def _assert_common(result) -> None:
    assert result.ok is True, (
        f"expected ok=True, got ok={result.ok}, exit_code={result.exit_code}, message={result.message!r}"
    )
    assert result.exit_code == 0, f"expected exit_code=0, got {result.exit_code}"
    assert result.actual_ir.count("symbol.for") == 1
    assert '"tile.step_value"(' not in result.actual_ir
    assert '"dma.view"(' in result.actual_ir
    assert '"dma.broadcast"' in result.actual_ir
    assert "tile.analysis" in result.actual_ir
    assert "tile.tile_exprs" in result.actual_ir
    assert 'tile.analysis = [["elewise", "elewise"], ["expand", "elewise"]]' in result.actual_ir
    assert (
        'tile.tile_exprs = [["", "TILE_B0"], ["", "TILE_B0"]]' in result.actual_ir
        or 'tile.tile_exprs = [["", "TILE0"], ["", "TILE0"]]' in result.actual_ir
        or 'tile.tile_exprs = [["", "TILE_D0"], ["", "TILE_D0"]]' in result.actual_ir
    )


def _case_static() -> None:
    _assert_common(
        run_ircheck_text(
            CASE_TEXT_STATIC,
            source_path="expectation/pass/tile/elewise/broadcast.py:static",
        )
    )


def _case_dynamic() -> None:
    _assert_common(
        run_ircheck_text(
            CASE_TEXT_DYNAMIC,
            source_path="expectation/pass/tile/elewise/broadcast.py:dynamic",
        )
    )


def main() -> None:
    failures: list[tuple[str, BaseException]] = []
    run_case(failures, "CASE-broadcast-static", _case_static)
    run_case(failures, "CASE-broadcast-dynamic", _case_dynamic)
    raise_if_failures("tile elewise broadcast expectation", failures)


if __name__ == "__main__":
    main()
