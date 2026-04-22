# [immutable-file]
"""tile `analysis-only=true` 的 `kernel.matmul` 单 op 分析 expectation。

创建者: 大闸蟹
最后一次更改: 大闸蟹

功能说明:
- 使用 `ircheck` 黑盒锁定 `tile-analysis` 对单个
  `kernel.matmul` 只添加分析属性，不插入 loop/view/helper。
- 覆盖静态与动态两条路径，并固定 matmul 的三维分析结果：
  `M/N` 为 `elewise`，`K` 为 `reduce`。

使用示例:
- `PYTHONPATH=. python expectation/pass/tile/analysis/matmul.py`

关联文件:
- spec: [`spec/pass/lowering/tile.md`](spec/pass/lowering/tile.md)
- spec: [`spec/tools/ircheck.md`](spec/tools/ircheck.md)
- test: [`test/pass/test_lowering_tile.py`](test/pass/test_lowering_tile.py)
- 功能实现: [`kernel_gen/passes/lowering/tile.py`](kernel_gen/passes/lowering/tile.py)
- 功能实现: [`kernel_gen/dialect/kernel.py`](kernel_gen/dialect/kernel.py)
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
    from .._random_shared import FLOAT_DTYPE, memory_ir, random_rank3_static_dynamic
else:
    TILE_DIR = REPO_ROOT / "expectation" / "pass" / "tile"
    if str(TILE_DIR) not in sys.path:
        sys.path.insert(0, str(TILE_DIR))
    from _random_shared import FLOAT_DTYPE, memory_ir, random_rank3_static_dynamic

STATIC_M, STATIC_K, STATIC_N, SYM_M, SYM_K, SYM_N = random_rank3_static_dynamic()
STATIC_LHS_IR = memory_ir([STATIC_M, STATIC_K], FLOAT_DTYPE)
STATIC_RHS_IR = memory_ir([STATIC_K, STATIC_N], FLOAT_DTYPE)
STATIC_OUT_IR = memory_ir([STATIC_M, STATIC_N], FLOAT_DTYPE)
DYNAMIC_LHS_IR = memory_ir([SYM_M, SYM_K], FLOAT_DTYPE)
DYNAMIC_RHS_IR = memory_ir([SYM_K, SYM_N], FLOAT_DTYPE)
DYNAMIC_OUT_IR = memory_ir([SYM_M, SYM_N], FLOAT_DTYPE)

def _build_case_text(function_name: str, lhs_ir: str, rhs_ir: str, out_ir: str) -> str:
    return """// COMPILE_ARGS: --pass "tile-analysis"
// CHECK: builtin.module {{
// CHECK-NEXT: func.func @{function_name}(%[[ARG0:{{reg}}]] : {lhs_ir}, %[[ARG1:{{reg}}]] : {rhs_ir}, %[[ARG2:{{reg}}]] : {out_ir}) {{
// CHECK-NEXT: "kernel.matmul"(%arg0, %arg1, %arg2) {{space = #nn.space<global>, tile.analysis = \[\["elewise", "reduce"\], \["reduce", "elewise"\], \["elewise", "elewise"\]\], tile.tile_exprs = \[\["", ""\], \["", ""\], \["", ""\]\]}} : ({lhs_ir}, {rhs_ir}, {out_ir}) -> ()
// CHECK-NEXT: func.return
// CHECK-NEXT: }}
// CHECK-NEXT: }}
// CHECK-NOT: tuner.param
// CHECK-NOT: "symbol.get_dim"(
// CHECK-NOT: symbol.for
// CHECK-NOT: "dma.view"(

builtin.module {{
  func.func @{function_name}(%arg0 : {lhs_ir}, %arg1 : {rhs_ir}, %arg2 : {out_ir}) {{
    "kernel.matmul"(%arg0, %arg1, %arg2) {{space = #nn.space<global>}} : ({lhs_ir}, {rhs_ir}, {out_ir}) -> ()
    func.return
  }}
}}
""".format(
        function_name=function_name,
        lhs_ir=lhs_ir,
        rhs_ir=rhs_ir,
        out_ir=out_ir,
    )

CASE_TEXT_STATIC = _build_case_text(
    "matmul_static",
    STATIC_LHS_IR,
    STATIC_RHS_IR,
    STATIC_OUT_IR,
)
CASE_TEXT_DYNAMIC = _build_case_text(
    "matmul_dynamic",
    DYNAMIC_LHS_IR,
    DYNAMIC_RHS_IR,
    DYNAMIC_OUT_IR,
)


def _assert_common(result, analysis_text: str) -> None:
    assert result.ok is True, (
        f"expected ok=True, got ok={result.ok}, exit_code={result.exit_code}, message={result.message!r}"
    )
    assert result.exit_code == 0, f"expected exit_code=0, got {result.exit_code}"
    assert analysis_text in result.actual_ir
    assert 'tile.tile_exprs = [["", ""], ["", ""], ["", ""]]' in result.actual_ir
    assert "tuner.param" not in result.actual_ir
    assert '"symbol.get_dim"(' not in result.actual_ir
    assert "symbol.for" not in result.actual_ir
    assert '"dma.view"(' not in result.actual_ir


def _case_static() -> None:
    _assert_common(
        run_ircheck_text(
            CASE_TEXT_STATIC,
            source_path="expectation/pass/tile/analysis/matmul.py:static",
        ),
        'tile.analysis = [["elewise", "reduce"], ["reduce", "elewise"], ["elewise", "elewise"]]',
    )


def _case_dynamic() -> None:
    _assert_common(
        run_ircheck_text(
            CASE_TEXT_DYNAMIC,
            source_path="expectation/pass/tile/analysis/matmul.py:dynamic",
        ),
        'tile.analysis = [["elewise", "reduce"], ["reduce", "elewise"], ["elewise", "elewise"]]',
    )


def main() -> None:
    failures: list[tuple[str, BaseException]] = []
    run_case(failures, "CASE-static", _case_static)
    run_case(failures, "CASE-dynamic", _case_dynamic)
    raise_if_failures("tile analysis matmul expectation", failures)


if __name__ == "__main__":
    main()
