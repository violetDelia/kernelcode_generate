# [immutable-file]
"""tile `analysis-only=true` 的 `kernel.matmul` 单 op 分析 expectation。

创建者: 大闸蟹
最后一次更改: 大闸蟹

功能说明:
- 使用 `ircheck` 黑盒锁定 `tile-analysis` 对单个
  `kernel.matmul` 只添加分析属性，不插入 loop/view/helper。
- 覆盖静态、动态与 mixed 三条路径，并固定 matmul 的三维分析结果：
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
    from .._random_shared import FLOAT_DTYPE, SPACE_ATTR, memory_ir, random_rank3_static_dynamic
else:
    TILE_DIR = REPO_ROOT / "expectation" / "pass" / "tile"
    if str(TILE_DIR) not in sys.path:
        sys.path.insert(0, str(TILE_DIR))
    from _random_shared import FLOAT_DTYPE, SPACE_ATTR, memory_ir, random_rank3_static_dynamic

STATIC_M, STATIC_K, STATIC_N, SYM_M, SYM_K, SYM_N = random_rank3_static_dynamic()
STATIC_LHS_IR = memory_ir([STATIC_M, STATIC_K], FLOAT_DTYPE)
STATIC_RHS_IR = memory_ir([STATIC_K, STATIC_N], FLOAT_DTYPE)
STATIC_OUT_IR = memory_ir([STATIC_M, STATIC_N], FLOAT_DTYPE)
DYNAMIC_LHS_IR = memory_ir([SYM_M, SYM_K], FLOAT_DTYPE)
DYNAMIC_RHS_IR = memory_ir([SYM_K, SYM_N], FLOAT_DTYPE)
DYNAMIC_OUT_IR = memory_ir([SYM_M, SYM_N], FLOAT_DTYPE)
MIXED_LHS_IR = memory_ir([STATIC_M, SYM_K], FLOAT_DTYPE)
MIXED_RHS_IR = memory_ir([SYM_K, STATIC_N], FLOAT_DTYPE)
MIXED_OUT_IR = memory_ir([STATIC_M, STATIC_N], FLOAT_DTYPE)


def _build_case_text(function_name: str, lhs_ir: str, rhs_ir: str, out_ir: str) -> str:
    """生成 matmul analysis expectation 文本。"""

    return rf"""// COMPILE_ARGS: --pass "tile-analysis"
// CHECK: builtin.module {{
// CHECK-NEXT: func.func @{function_name}(%[[OUT:{{reg}}]] : {out_ir}, %[[LHS:{{reg}}]] : {lhs_ir}, %[[RHS:{{reg}}]] : {rhs_ir}) {{
// CHECK-NEXT: "kernel.matmul"(%[[OUT]], %[[LHS]], %[[RHS]]) {{space = {SPACE_ATTR}, tile.analysis = \[\["elewise", "reduce"\], \["reduce", "elewise"\], \["elewise", "elewise"\]\], tile.tile_exprs = \[\["", ""\], \["", ""\], \["", ""\]\]}} : ({out_ir}, {lhs_ir}, {rhs_ir}) -> ()
// CHECK-NEXT: func.return
// CHECK-NEXT: }}
// CHECK-NEXT: }}
// CHECK-NOT: tuner.param
// CHECK-NOT: "symbol.get_dim"(
// CHECK-NOT: symbol.for
// CHECK-NOT: "dma.view"(

builtin.module {{
  func.func @{function_name}(%out : {out_ir}, %lhs : {lhs_ir}, %rhs : {rhs_ir}) {{
    "kernel.matmul"(%out, %lhs, %rhs) {{space = {SPACE_ATTR}}} : ({out_ir}, {lhs_ir}, {rhs_ir}) -> ()
    func.return
  }}
}}
"""


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
CASE_TEXT_MIXED = _build_case_text(
    "matmul_mixed",
    MIXED_LHS_IR,
    MIXED_RHS_IR,
    MIXED_OUT_IR,
)


def _assert_common(result) -> None:
    """检查 matmul analysis-only 输出没有执行切分。"""

    assert result.ok is True, (
        f"expected ok=True, got ok={result.ok}, exit_code={result.exit_code}, message={result.message!r}"
    )
    assert result.exit_code == 0, f"expected exit_code=0, got {result.exit_code}"
    assert 'tile.analysis = [["elewise", "reduce"], ["reduce", "elewise"], ["elewise", "elewise"]]' in result.actual_ir
    assert 'tile.tile_exprs = [["", ""], ["", ""], ["", ""]]' in result.actual_ir
    assert "tuner.param" not in result.actual_ir
    assert '"symbol.get_dim"(' not in result.actual_ir
    assert "symbol.for" not in result.actual_ir
    assert '"dma.view"(' not in result.actual_ir
    assert result.actual_ir.count('"kernel.matmul"') == 1


def _case_static() -> None:
    """运行静态 matmul analysis case。"""

    _assert_common(
        run_ircheck_text(
            CASE_TEXT_STATIC,
            source_path="expectation/pass/tile/analysis/matmul.py:static",
        )
    )


def _case_dynamic() -> None:
    """运行动态 matmul analysis case。"""

    _assert_common(
        run_ircheck_text(
            CASE_TEXT_DYNAMIC,
            source_path="expectation/pass/tile/analysis/matmul.py:dynamic",
        )
    )


def _case_mixed() -> None:
    """运行 mixed matmul analysis case。"""

    _assert_common(
        run_ircheck_text(
            CASE_TEXT_MIXED,
            source_path="expectation/pass/tile/analysis/matmul.py:mixed",
        )
    )


def main() -> None:
    """运行 matmul analysis expectation。"""

    failures: list[tuple[str, BaseException]] = []
    run_case(failures, "CASE-static", _case_static)
    run_case(failures, "CASE-dynamic", _case_dynamic)
    run_case(failures, "CASE-mixed", _case_mixed)
    raise_if_failures("tile analysis matmul expectation", failures)


if __name__ == "__main__":
    main()
