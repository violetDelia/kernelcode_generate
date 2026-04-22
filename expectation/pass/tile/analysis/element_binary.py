# [immutable-file]
"""tile `analysis-only=true` 的 `kernel.binary_elewise` 单 op 分析 expectation。

创建者: 大闸蟹
最后一次更改: 大闸蟹

功能说明:
- 使用 `ircheck` 黑盒锁定 `tile-analysis` 对单个
  `kernel.binary_elewise` 只添加分析属性，不插入 loop/view/helper。
- 覆盖 element binary 类中的静态/动态与不同 `kind` 组合。

使用示例:
- `PYTHONPATH=. python expectation/pass/tile/analysis/element_binary.py`

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
    from .._random_shared import ARITH_DTYPE, memory_ir, random_rank2_static_dynamic
else:
    TILE_DIR = REPO_ROOT / "expectation" / "pass" / "tile"
    if str(TILE_DIR) not in sys.path:
        sys.path.insert(0, str(TILE_DIR))
    from _random_shared import ARITH_DTYPE, memory_ir, random_rank2_static_dynamic

STATIC_M, STATIC_N, SYM_M, SYM_N = random_rank2_static_dynamic()
STATIC_MEM_IR = memory_ir([STATIC_M, STATIC_N], ARITH_DTYPE)
DYNAMIC_MEM_IR = memory_ir([SYM_M, SYM_N], ARITH_DTYPE)

def _build_case_text(function_name: str, kind: str, mem_ir: str) -> str:
    return """// COMPILE_ARGS: --pass "tile-analysis"
// CHECK: builtin.module {{
// CHECK-NEXT: func.func @{function_name}(%[[ARG0:{{reg}}]] : {mem_ir}, %[[ARG1:{{reg}}]] : {mem_ir}, %[[ARG2:{{reg}}]] : {mem_ir}) {{
// CHECK-NEXT: "kernel.binary_elewise"(%arg0, %arg1, %arg2) {{kind = "{kind}", space = #nn.space<global>, tile.analysis = \[\["elewise", "elewise"\], \["elewise", "elewise"\], \["elewise", "elewise"\]\], tile.tile_exprs = \[\["", ""\], \["", ""\], \["", ""\]\]}} : ({mem_ir}, {mem_ir}, {mem_ir}) -> ()
// CHECK-NEXT: func.return
// CHECK-NEXT: }}
// CHECK-NEXT: }}
// CHECK-NOT: tuner.param
// CHECK-NOT: "symbol.get_dim"(
// CHECK-NOT: symbol.for
// CHECK-NOT: "dma.view"(

builtin.module {{
  func.func @{function_name}(%arg0 : {mem_ir}, %arg1 : {mem_ir}, %arg2 : {mem_ir}) {{
    "kernel.binary_elewise"(%arg0, %arg1, %arg2) {{kind = "{kind}", space = #nn.space<global>}} : ({mem_ir}, {mem_ir}, {mem_ir}) -> ()
    func.return
  }}
}}
""".format(
        function_name=function_name,
        kind=kind,
        mem_ir=mem_ir,
    )

CASE_TEXT_ADD_STATIC = _build_case_text("binary_add_static", "add", STATIC_MEM_IR)
CASE_TEXT_ADD_DYNAMIC = _build_case_text("binary_add_dynamic", "add", DYNAMIC_MEM_IR)
CASE_TEXT_MUL_STATIC = _build_case_text("binary_mul_static", "mul", STATIC_MEM_IR)
CASE_TEXT_DIV_DYNAMIC = _build_case_text("binary_div_dynamic", "div", DYNAMIC_MEM_IR)


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


def _case_add_static() -> None:
    _assert_common(
        run_ircheck_text(
            CASE_TEXT_ADD_STATIC,
            source_path="expectation/pass/tile/analysis/element_binary.py:add-static",
        ),
        'tile.analysis = [["elewise", "elewise"], ["elewise", "elewise"], ["elewise", "elewise"]]',
    )


def _case_add_dynamic() -> None:
    _assert_common(
        run_ircheck_text(
            CASE_TEXT_ADD_DYNAMIC,
            source_path="expectation/pass/tile/analysis/element_binary.py:add-dynamic",
        ),
        'tile.analysis = [["elewise", "elewise"], ["elewise", "elewise"], ["elewise", "elewise"]]',
    )


def _case_mul_static() -> None:
    _assert_common(
        run_ircheck_text(
            CASE_TEXT_MUL_STATIC,
            source_path="expectation/pass/tile/analysis/element_binary.py:mul-static",
        ),
        'tile.analysis = [["elewise", "elewise"], ["elewise", "elewise"], ["elewise", "elewise"]]',
    )


def _case_div_dynamic() -> None:
    _assert_common(
        run_ircheck_text(
            CASE_TEXT_DIV_DYNAMIC,
            source_path="expectation/pass/tile/analysis/element_binary.py:div-dynamic",
        ),
        'tile.analysis = [["elewise", "elewise"], ["elewise", "elewise"], ["elewise", "elewise"]]',
    )


def main() -> None:
    failures: list[tuple[str, BaseException]] = []
    run_case(failures, "CASE-add-static", _case_add_static)
    run_case(failures, "CASE-add-dynamic", _case_add_dynamic)
    run_case(failures, "CASE-mul-static", _case_mul_static)
    run_case(failures, "CASE-div-dynamic", _case_div_dynamic)
    raise_if_failures("tile analysis element_binary expectation", failures)


if __name__ == "__main__":
    main()
