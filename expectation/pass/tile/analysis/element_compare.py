# [immutable-file]
"""tile `analysis-only=true` 的 compare 类 `kernel.binary_elewise` 单 op 分析 expectation。

创建者: 大闸蟹
最后一次更改: 大闸蟹

功能说明:
- 使用 `ircheck` 黑盒锁定 `tile-analysis` 对 compare 类
  `kernel.binary_elewise(kind=eq/ne/ge/gt)` 只添加分析属性，不插入 loop/view/helper。
- 覆盖 rank2/rank1、静态/动态与不同 compare `kind` 组合，输出必须保持 `i1` memory。

使用示例:
- `PYTHONPATH=. python expectation/pass/tile/analysis/element_compare.py`

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
    from .._random_shared import (
        ARITH_DTYPE,
        BOOL_DTYPE,
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
        BOOL_DTYPE,
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


def _build_rank2_case(*, func_name: str, kind: str, input_ir: str, output_ir: str) -> str:
    """生成 rank-2 compare analysis expectation 文本。"""

    return rf"""// COMPILE_ARGS: --pass "tile-analysis"
// CHECK: builtin.module {{
// CHECK-NEXT: func.func @{func_name}(%[[OUT:{{reg}}]] : {output_ir}, %[[LHS:{{reg}}]] : {input_ir}, %[[RHS:{{reg}}]] : {input_ir}) {{
// CHECK-NEXT: "kernel.binary_elewise"(%[[OUT]], %[[LHS]], %[[RHS]]) {{kind = "{kind}", space = {SPACE_ATTR}, tile.analysis = \[\["elewise", "elewise"\], \["elewise", "elewise"\], \["elewise", "elewise"\]\], tile.tile_exprs = \[\["", ""\], \["", ""\], \["", ""\]\]}} : ({output_ir}, {input_ir}, {input_ir}) -> ()
// CHECK-NEXT: func.return
// CHECK-NEXT: }}
// CHECK-NEXT: }}
// CHECK-NOT: tuner.param
// CHECK-NOT: "symbol.get_dim"(
// CHECK-NOT: symbol.for
// CHECK-NOT: "dma.view"(

builtin.module {{
  func.func @{func_name}(%out : {output_ir}, %lhs : {input_ir}, %rhs : {input_ir}) {{
    "kernel.binary_elewise"(%out, %lhs, %rhs) {{kind = "{kind}", space = {SPACE_ATTR}}} : ({output_ir}, {input_ir}, {input_ir}) -> ()
    func.return
  }}
}}
"""


def _build_rank1_case(*, func_name: str, kind: str, input_ir: str, output_ir: str) -> str:
    """生成 rank-1 compare analysis expectation 文本。"""

    return rf"""// COMPILE_ARGS: --pass "tile-analysis"
// CHECK: builtin.module {{
// CHECK-NEXT: func.func @{func_name}(%[[OUT:{{reg}}]] : {output_ir}, %[[LHS:{{reg}}]] : {input_ir}, %[[RHS:{{reg}}]] : {input_ir}) {{
// CHECK-NEXT: "kernel.binary_elewise"(%[[OUT]], %[[LHS]], %[[RHS]]) {{kind = "{kind}", space = {SPACE_ATTR}, tile.analysis = \[\["elewise"\], \["elewise"\], \["elewise"\]\], tile.tile_exprs = \[\[""\], \[""\], \[""\]\]}} : ({output_ir}, {input_ir}, {input_ir}) -> ()
// CHECK-NEXT: func.return
// CHECK-NEXT: }}
// CHECK-NEXT: }}
// CHECK-NOT: tuner.param
// CHECK-NOT: "symbol.get_dim"(
// CHECK-NOT: symbol.for
// CHECK-NOT: "dma.view"(

builtin.module {{
  func.func @{func_name}(%out : {output_ir}, %lhs : {input_ir}, %rhs : {input_ir}) {{
    "kernel.binary_elewise"(%out, %lhs, %rhs) {{kind = "{kind}", space = {SPACE_ATTR}}} : ({output_ir}, {input_ir}, {input_ir}) -> ()
    func.return
  }}
}}
"""


CASE_TEXT_R2_STATIC = _build_rank2_case(
    func_name="compare_rank2_static",
    kind=R2_STATIC_KIND,
    input_ir=R2_STATIC_INPUT_IR,
    output_ir=R2_STATIC_OUTPUT_IR,
)
CASE_TEXT_R2_DYNAMIC = _build_rank2_case(
    func_name="compare_rank2_dynamic",
    kind=R2_DYNAMIC_KIND,
    input_ir=R2_DYNAMIC_INPUT_IR,
    output_ir=R2_DYNAMIC_OUTPUT_IR,
)
CASE_TEXT_R1_STATIC = _build_rank1_case(
    func_name="compare_rank1_static",
    kind=R1_STATIC_KIND,
    input_ir=R1_STATIC_INPUT_IR,
    output_ir=R1_STATIC_OUTPUT_IR,
)
CASE_TEXT_R1_DYNAMIC = _build_rank1_case(
    func_name="compare_rank1_dynamic",
    kind=R1_DYNAMIC_KIND,
    input_ir=R1_DYNAMIC_INPUT_IR,
    output_ir=R1_DYNAMIC_OUTPUT_IR,
)


def _assert_no_split(result, analysis_text: str, tile_expr_text: str) -> None:
    """检查 compare analysis-only 输出没有执行切分。"""

    assert result.ok is True, (
        f"expected ok=True, got ok={result.ok}, exit_code={result.exit_code}, message={result.message!r}"
    )
    assert result.exit_code == 0, f"expected exit_code=0, got {result.exit_code}"
    assert analysis_text in result.actual_ir
    assert tile_expr_text in result.actual_ir
    assert "tuner.param" not in result.actual_ir
    assert '"symbol.get_dim"(' not in result.actual_ir
    assert "symbol.for" not in result.actual_ir
    assert '"dma.view"(' not in result.actual_ir
    assert result.actual_ir.count('"kernel.binary_elewise"') == 1
    assert ", i1, #nn.space<global>>" in result.actual_ir


def _case_r2_static() -> None:
    """运行 rank-2 静态 compare analysis case。"""

    _assert_no_split(
        run_ircheck_text(
            CASE_TEXT_R2_STATIC,
            source_path="expectation/pass/tile/analysis/element_compare.py:r2-static",
        ),
        'tile.analysis = [["elewise", "elewise"], ["elewise", "elewise"], ["elewise", "elewise"]]',
        'tile.tile_exprs = [["", ""], ["", ""], ["", ""]]',
    )


def _case_r2_dynamic() -> None:
    """运行 rank-2 动态 compare analysis case。"""

    _assert_no_split(
        run_ircheck_text(
            CASE_TEXT_R2_DYNAMIC,
            source_path="expectation/pass/tile/analysis/element_compare.py:r2-dynamic",
        ),
        'tile.analysis = [["elewise", "elewise"], ["elewise", "elewise"], ["elewise", "elewise"]]',
        'tile.tile_exprs = [["", ""], ["", ""], ["", ""]]',
    )


def _case_r1_static() -> None:
    """运行 rank-1 静态 compare analysis case。"""

    _assert_no_split(
        run_ircheck_text(
            CASE_TEXT_R1_STATIC,
            source_path="expectation/pass/tile/analysis/element_compare.py:r1-static",
        ),
        'tile.analysis = [["elewise"], ["elewise"], ["elewise"]]',
        'tile.tile_exprs = [[""], [""], [""]]',
    )


def _case_r1_dynamic() -> None:
    """运行 rank-1 动态 compare analysis case。"""

    _assert_no_split(
        run_ircheck_text(
            CASE_TEXT_R1_DYNAMIC,
            source_path="expectation/pass/tile/analysis/element_compare.py:r1-dynamic",
        ),
        'tile.analysis = [["elewise"], ["elewise"], ["elewise"]]',
        'tile.tile_exprs = [[""], [""], [""]]',
    )


def main() -> None:
    """运行 compare analysis expectation。"""

    failures: list[tuple[str, BaseException]] = []
    run_case(failures, "CASE-r2-static", _case_r2_static)
    run_case(failures, "CASE-r2-dynamic", _case_r2_dynamic)
    run_case(failures, "CASE-r1-static", _case_r1_static)
    run_case(failures, "CASE-r1-dynamic", _case_r1_dynamic)
    raise_if_failures("tile analysis element_compare expectation", failures)


if __name__ == "__main__":
    main()
