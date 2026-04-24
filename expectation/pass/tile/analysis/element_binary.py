# [immutable-file]
"""tile `analysis-only=true` 的 `kernel.binary_elewise` 单 op 分析 expectation。

创建者: 大闸蟹
最后一次更改: 大闸蟹

功能说明:
- 使用 `ircheck` 黑盒锁定 `tile-analysis` 对单个
  `kernel.binary_elewise` 只添加分析属性，不插入 loop/view/helper。
- 覆盖 rank2/rank1、静态/动态与不同 `kind` 组合，和 `tile-elewise`
  的 case 面保持一致。

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
    from .._random_shared import (
        ARITH_DTYPE,
        SPACE_ATTR,
        memory_ir,
        random_element_binary_kinds,
        random_rank1_static_dynamic,
        random_rank2_static_dynamic,
    )
else:
    TILE_DIR = REPO_ROOT / "expectation" / "pass" / "tile"
    if str(TILE_DIR) not in sys.path:
        sys.path.insert(0, str(TILE_DIR))
    from _random_shared import (
        ARITH_DTYPE,
        SPACE_ATTR,
        memory_ir,
        random_element_binary_kinds,
        random_rank1_static_dynamic,
        random_rank2_static_dynamic,
    )

STATIC_M, STATIC_N, SYM_M, SYM_N = random_rank2_static_dynamic()
STATIC_P, SYM_P = random_rank1_static_dynamic()

R2_STATIC_IR = memory_ir([STATIC_M, STATIC_N], ARITH_DTYPE)
R2_DYNAMIC_IR = memory_ir([SYM_M, SYM_N], ARITH_DTYPE)
R1_STATIC_IR = memory_ir([STATIC_P], ARITH_DTYPE)
R1_DYNAMIC_IR = memory_ir([SYM_P], ARITH_DTYPE)
R2_STATIC_KIND, R2_DYNAMIC_KIND, R1_STATIC_KIND, R1_DYNAMIC_KIND = random_element_binary_kinds()


def _build_rank2_case(*, func_name: str, mem_ir: str, kind: str) -> str:
    """生成 rank-2 binary analysis expectation 文本。

    创建者: 大闸蟹
    最后一次更改: 大闸蟹

    功能说明:
    - 锁定 analysis pass 对 rank-2 binary op 只补 `tile.analysis/tile.tile_exprs`。
    - 拒绝 `tuner.param`、`symbol.for`、`symbol.get_dim` 与 `dma.view`。

    使用示例:
    - `_build_rank2_case(func_name="case", mem_ir=R2_STATIC_IR, kind="add")`

    关联文件:
    - spec: [`spec/pass/lowering/tile.md`](spec/pass/lowering/tile.md)
    - test: [`test/pass/test_lowering_tile.py`](test/pass/test_lowering_tile.py)
    - 功能实现: [`expectation/pass/tile/analysis/element_binary.py`](expectation/pass/tile/analysis/element_binary.py)
    """

    return rf"""// COMPILE_ARGS: --pass "tile-analysis"
// CHECK: builtin.module {{
// CHECK-NEXT: func.func @{func_name}(%[[OUT:{{reg}}]] : {mem_ir}, %[[LHS:{{reg}}]] : {mem_ir}, %[[RHS:{{reg}}]] : {mem_ir}) {{
// CHECK-NEXT: "kernel.binary_elewise"(%[[OUT]], %[[LHS]], %[[RHS]]) {{kind = "{kind}", space = {SPACE_ATTR}, tile.analysis = \[\["elewise", "elewise"\], \["elewise", "elewise"\], \["elewise", "elewise"\]\], tile.tile_exprs = \[\["", ""\], \["", ""\], \["", ""\]\]}} : ({mem_ir}, {mem_ir}, {mem_ir}) -> ()
// CHECK-NEXT: func.return
// CHECK-NEXT: }}
// CHECK-NEXT: }}
// CHECK-NOT: tuner.param
// CHECK-NOT: "symbol.get_dim"(
// CHECK-NOT: symbol.for
// CHECK-NOT: "dma.view"(

builtin.module {{
  func.func @{func_name}(%arg0 : {mem_ir}, %arg1 : {mem_ir}, %arg2 : {mem_ir}) {{
    "kernel.binary_elewise"(%arg0, %arg1, %arg2) {{kind = "{kind}", space = {SPACE_ATTR}}} : ({mem_ir}, {mem_ir}, {mem_ir}) -> ()
    func.return
  }}
}}
"""


def _build_rank1_case(*, func_name: str, mem_ir: str, kind: str) -> str:
    """生成 rank-1 binary analysis expectation 文本。

    创建者: 大闸蟹
    最后一次更改: 大闸蟹

    功能说明:
    - 锁定 rank-1 binary op 的 analysis 矩阵必须降为一维。
    - 与 rank-2 case 一样确认 analysis 阶段不做实际切分。

    使用示例:
    - `_build_rank1_case(func_name="case", mem_ir=R1_STATIC_IR, kind="mul")`

    关联文件:
    - spec: [`spec/pass/lowering/tile.md`](spec/pass/lowering/tile.md)
    - test: [`test/pass/test_lowering_tile.py`](test/pass/test_lowering_tile.py)
    - 功能实现: [`expectation/pass/tile/analysis/element_binary.py`](expectation/pass/tile/analysis/element_binary.py)
    """

    return rf"""// COMPILE_ARGS: --pass "tile-analysis"
// CHECK: builtin.module {{
// CHECK-NEXT: func.func @{func_name}(%[[OUT:{{reg}}]] : {mem_ir}, %[[LHS:{{reg}}]] : {mem_ir}, %[[RHS:{{reg}}]] : {mem_ir}) {{
// CHECK-NEXT: "kernel.binary_elewise"(%[[OUT]], %[[LHS]], %[[RHS]]) {{kind = "{kind}", space = {SPACE_ATTR}, tile.analysis = \[\["elewise"\], \["elewise"\], \["elewise"\]\], tile.tile_exprs = \[\[""\], \[""\], \[""\]\]}} : ({mem_ir}, {mem_ir}, {mem_ir}) -> ()
// CHECK-NEXT: func.return
// CHECK-NEXT: }}
// CHECK-NEXT: }}
// CHECK-NOT: tuner.param
// CHECK-NOT: "symbol.get_dim"(
// CHECK-NOT: symbol.for
// CHECK-NOT: "dma.view"(

builtin.module {{
  func.func @{func_name}(%arg0 : {mem_ir}, %arg1 : {mem_ir}, %arg2 : {mem_ir}) {{
    "kernel.binary_elewise"(%arg0, %arg1, %arg2) {{kind = "{kind}", space = {SPACE_ATTR}}} : ({mem_ir}, {mem_ir}, {mem_ir}) -> ()
    func.return
  }}
}}
"""


CASE_TEXT_R2_STATIC = _build_rank2_case(
    func_name="binary_rank2_static",
    kind=R2_STATIC_KIND,
    mem_ir=R2_STATIC_IR,
)
CASE_TEXT_R2_DYNAMIC = _build_rank2_case(
    func_name="binary_rank2_dynamic",
    kind=R2_DYNAMIC_KIND,
    mem_ir=R2_DYNAMIC_IR,
)
CASE_TEXT_R1_STATIC = _build_rank1_case(
    func_name="binary_rank1_static",
    kind=R1_STATIC_KIND,
    mem_ir=R1_STATIC_IR,
)
CASE_TEXT_R1_DYNAMIC = _build_rank1_case(
    func_name="binary_rank1_dynamic",
    kind=R1_DYNAMIC_KIND,
    mem_ir=R1_DYNAMIC_IR,
)


def _assert_no_split(result, analysis_text: str, tile_expr_text: str) -> None:
    """检查 analysis-only 输出没有执行切分。

    创建者: 大闸蟹
    最后一次更改: 大闸蟹

    功能说明:
    - 检查 `ircheck` 成功。
    - 检查目标 analysis/tile_exprs 已补齐。
    - 检查没有生成后续 tile pass 才应产生的 loop/view/param。

    使用示例:
    - `_assert_no_split(result, "[[...]]", "[[...]]")`

    关联文件:
    - spec: [`spec/pass/lowering/tile.md`](spec/pass/lowering/tile.md)
    - test: [`test/pass/test_lowering_tile.py`](test/pass/test_lowering_tile.py)
    - 功能实现: [`expectation/pass/tile/analysis/element_binary.py`](expectation/pass/tile/analysis/element_binary.py)
    """

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


def _case_r2_static() -> None:
    """运行 rank-2 静态 binary analysis case。"""

    _assert_no_split(
        run_ircheck_text(
            CASE_TEXT_R2_STATIC,
            source_path="expectation/pass/tile/analysis/element_binary.py:r2-static",
        ),
        'tile.analysis = [["elewise", "elewise"], ["elewise", "elewise"], ["elewise", "elewise"]]',
        'tile.tile_exprs = [["", ""], ["", ""], ["", ""]]',
    )


def _case_r2_dynamic() -> None:
    """运行 rank-2 动态 binary analysis case。"""

    _assert_no_split(
        run_ircheck_text(
            CASE_TEXT_R2_DYNAMIC,
            source_path="expectation/pass/tile/analysis/element_binary.py:r2-dynamic",
        ),
        'tile.analysis = [["elewise", "elewise"], ["elewise", "elewise"], ["elewise", "elewise"]]',
        'tile.tile_exprs = [["", ""], ["", ""], ["", ""]]',
    )


def _case_r1_static() -> None:
    """运行 rank-1 静态 binary analysis case。"""

    _assert_no_split(
        run_ircheck_text(
            CASE_TEXT_R1_STATIC,
            source_path="expectation/pass/tile/analysis/element_binary.py:r1-static",
        ),
        'tile.analysis = [["elewise"], ["elewise"], ["elewise"]]',
        'tile.tile_exprs = [[""], [""], [""]]',
    )


def _case_r1_dynamic() -> None:
    """运行 rank-1 动态 binary analysis case。"""

    _assert_no_split(
        run_ircheck_text(
            CASE_TEXT_R1_DYNAMIC,
            source_path="expectation/pass/tile/analysis/element_binary.py:r1-dynamic",
        ),
        'tile.analysis = [["elewise"], ["elewise"], ["elewise"]]',
        'tile.tile_exprs = [[""], [""], [""]]',
    )


def main() -> None:
    """运行 binary analysis expectation。"""

    failures: list[tuple[str, BaseException]] = []
    run_case(failures, "CASE-r2-static", _case_r2_static)
    run_case(failures, "CASE-r2-dynamic", _case_r2_dynamic)
    run_case(failures, "CASE-r1-static", _case_r1_static)
    run_case(failures, "CASE-r1-dynamic", _case_r1_dynamic)
    raise_if_failures("tile analysis element_binary expectation", failures)


if __name__ == "__main__":
    main()
