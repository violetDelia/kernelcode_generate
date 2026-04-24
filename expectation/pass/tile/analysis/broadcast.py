# [immutable-file]
"""tile `analysis-only=true` 的 `dma.broadcast` 单 op 分析 expectation。

创建者: 大闸蟹
最后一次更改: 大闸蟹

功能说明:
- 使用 `ircheck` 黑盒锁定 `tile-analysis` 对单个 `dma.broadcast`
  只添加分析属性与 tile 表达式占位信息，不插入 loop/view/helper。
- 覆盖静态与动态两条路径，并固定 `broadcast` 的维度分析结果：
  可扩展维为 `expand`，对齐维为 `elewise`。

使用示例:
- `PYTHONPATH=. python expectation/pass/tile/analysis/broadcast.py`

关联文件:
- spec: [`spec/pass/lowering/tile.md`](spec/pass/lowering/tile.md)
- spec: [`spec/tools/ircheck.md`](spec/tools/ircheck.md)
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
    from .._random_shared import ARITH_DTYPE, memory_ir, random_rank2_static_dynamic
else:
    TILE_DIR = REPO_ROOT / "expectation" / "pass" / "tile"
    if str(TILE_DIR) not in sys.path:
        sys.path.insert(0, str(TILE_DIR))
    from _random_shared import ARITH_DTYPE, memory_ir, random_rank2_static_dynamic

STATIC_M, STATIC_N, SYM_M, SYM_N = random_rank2_static_dynamic()
STATIC_TARGET_IR = memory_ir([STATIC_M, STATIC_N], ARITH_DTYPE)
STATIC_SOURCE_IR = memory_ir([1, STATIC_N], ARITH_DTYPE)
DYNAMIC_TARGET_IR = memory_ir([SYM_M, SYM_N], ARITH_DTYPE)
DYNAMIC_SOURCE_IR = memory_ir([1, SYM_N], ARITH_DTYPE)

def _build_case_text(function_name: str, target_ir: str, source_ir: str) -> str:
    return r"""// COMPILE_ARGS: --pass "tile-analysis"
// CHECK: builtin.module {{
// CHECK-NEXT: func.func @{function_name}(%[[ARG0:{{reg}}]] : {target_ir}, %[[ARG1:{{reg}}]] : {source_ir}) {{
// CHECK-NEXT: "dma.broadcast"(%arg0, %arg1) {{tile.analysis = \[\["elewise", "elewise"\], \["expand", "elewise"\]\], tile.tile_exprs = \[\["", ""\], \["", ""\]\]}} : ({target_ir}, {source_ir}) -> ()
// CHECK-NEXT: func.return
// CHECK-NEXT: }}
// CHECK-NEXT: }}
// CHECK-NOT: tuner.param
// CHECK-NOT: "symbol.get_dim"(
// CHECK-NOT: symbol.for
// CHECK-NOT: "dma.view"(

builtin.module {{
  func.func @{function_name}(%arg0 : {target_ir}, %arg1 : {source_ir}) {{
    "dma.broadcast"(%arg0, %arg1) : ({target_ir}, {source_ir}) -> ()
    func.return
  }}
}}
""".format(
        function_name=function_name,
        target_ir=target_ir,
        source_ir=source_ir,
    )

CASE_TEXT_STATIC = _build_case_text("broadcast_static", STATIC_TARGET_IR, STATIC_SOURCE_IR)
CASE_TEXT_DYNAMIC = _build_case_text("broadcast_dynamic", DYNAMIC_TARGET_IR, DYNAMIC_SOURCE_IR)


def _case_static() -> None:
    result = run_ircheck_text(
        CASE_TEXT_STATIC,
        source_path="expectation/pass/tile/analysis/broadcast.py:static",
    )
    assert result.ok is True, (
        f"expected ok=True, got ok={result.ok}, exit_code={result.exit_code}, message={result.message!r}"
    )
    assert result.exit_code == 0, f"expected exit_code=0, got {result.exit_code}"
    assert 'tile.analysis = [["elewise", "elewise"], ["expand", "elewise"]]' in result.actual_ir
    assert 'tile.tile_exprs = [["", ""], ["", ""]]' in result.actual_ir
    assert "tuner.param" not in result.actual_ir
    assert '"symbol.get_dim"(' not in result.actual_ir


def _case_dynamic() -> None:
    result = run_ircheck_text(
        CASE_TEXT_DYNAMIC,
        source_path="expectation/pass/tile/analysis/broadcast.py:dynamic",
    )
    assert result.ok is True, (
        f"expected ok=True, got ok={result.ok}, exit_code={result.exit_code}, message={result.message!r}"
    )
    assert result.exit_code == 0, f"expected exit_code=0, got {result.exit_code}"
    assert 'tile.analysis = [["elewise", "elewise"], ["expand", "elewise"]]' in result.actual_ir
    assert 'tile.tile_exprs = [["", ""], ["", ""]]' in result.actual_ir
    assert "tuner.param" not in result.actual_ir
    assert '"symbol.get_dim"(' not in result.actual_ir


def main() -> None:
    failures: list[tuple[str, BaseException]] = []
    run_case(failures, "CASE-static", _case_static)
    run_case(failures, "CASE-dynamic", _case_dynamic)
    raise_if_failures("tile analysis broadcast expectation", failures)


if __name__ == "__main__":
    main()
