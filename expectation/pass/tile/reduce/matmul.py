# [immutable-file]
"""tile-reduce `kernel.matmul` expectation.

创建者: 金铲铲大作战
最后一次更改: 朽木露琪亚

功能说明:
- 使用 `ircheck` 验证 `tile-reduce` 对 out-first `kernel.matmul` 的公开输出。
- 覆盖静态、动态、mixed 三类形状，锁定 `tuner.param`、三层 `symbol.for`、
  `dma.view`、`dma.fill`、`dma.alloc` 与 `tile.analysis + tile.tile_exprs`。
- 不再绑定 SSA 名称，也不再检查旧桥接 op。

使用示例:
- `PYTHONPATH=/path/to/worktree:/home/lfr/kernelcode_generate python -m expectation.pass.tile.reduce.matmul`

关联文件:
- spec: [`spec/pass/lowering/tile_reduce.md`](spec/pass/lowering/tile_reduce.md)
- test: [`test/pass/test_lowering_tile_reduce.py`](test/pass/test_lowering_tile_reduce.py)
- 功能实现: [`kernel_gen/passes/lowering/tile_reduce.py`](kernel_gen/passes/lowering/tile_reduce.py)
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

STATIC_M, STATIC_K, STATIC_N, SYM_M, SYM_K, SYM_N = random_rank3_static_dynamic()

STATIC_OUT_IR = memory_ir([STATIC_M, STATIC_N], FLOAT_DTYPE)
STATIC_LHS_IR = memory_ir([STATIC_M, STATIC_K], FLOAT_DTYPE)
STATIC_RHS_IR = memory_ir([STATIC_K, STATIC_N], FLOAT_DTYPE)

DYNAMIC_OUT_IR = memory_ir([SYM_M, SYM_N], FLOAT_DTYPE)
DYNAMIC_LHS_IR = memory_ir([SYM_M, SYM_K], FLOAT_DTYPE)
DYNAMIC_RHS_IR = memory_ir([SYM_K, SYM_N], FLOAT_DTYPE)

MIXED_OUT_IR = memory_ir([STATIC_M, STATIC_N], FLOAT_DTYPE)
MIXED_LHS_IR = memory_ir([STATIC_M, SYM_K], FLOAT_DTYPE)
MIXED_RHS_IR = memory_ir([SYM_K, STATIC_N], FLOAT_DTYPE)


def _build_case_text(*, func_name: str, out_ir: str, lhs_ir: str, rhs_ir: str) -> str:
    """生成单个 matmul reduce expectation 文本。

    创建者: 金铲铲大作战
    最后一次更改: 朽木露琪亚

    功能说明:
    - 输入使用当前 kernel 合同的 out-first operand 顺序。
    - CHECK 行只锁定稳定结构，完整矩阵属性交给 Python 断言检查。

    使用示例:
    - `text = _build_case_text(func_name="case", out_ir=out_ir, lhs_ir=lhs_ir, rhs_ir=rhs_ir)`

    关联文件:
    - spec: [`spec/pass/lowering/tile_reduce.md`](spec/pass/lowering/tile_reduce.md)
    - test: [`test/pass/test_lowering_tile_reduce.py`](test/pass/test_lowering_tile_reduce.py)
    - 功能实现: [`expectation/pass/tile/reduce/matmul.py`](expectation/pass/tile/reduce/matmul.py)
    """

    return rf"""// COMPILE_ARGS: --pass tile-reduce
// CHECK: builtin.module {{
// CHECK: func.func @{func_name}
// CHECK: tuner.param : !symbol.int<"TILE_D0">
// CHECK: tuner.param : !symbol.int<"TILE_D1">
// CHECK: tuner.param : !symbol.int<"TILE_R0">
// CHECK: step = "TILE_D0"
// CHECK: step = "TILE_D1"
// CHECK: "dma.fill"
// CHECK: step = "TILE_R0"
// CHECK: "dma.alloc"
// CHECK: "kernel.matmul"
// CHECK: "kernel.binary_elewise"

builtin.module {{
  func.func @{func_name}(%out : {out_ir}, %lhs : {lhs_ir}, %rhs : {rhs_ir}) {{
    "kernel.matmul"(%out, %lhs, %rhs) {{space = {SPACE_ATTR}, tile.analysis = [["elewise", "reduce"], ["reduce", "elewise"], ["elewise", "elewise"]], tile.tile_exprs = [["", ""], ["", ""], ["", ""]]}} : ({out_ir}, {lhs_ir}, {rhs_ir}) -> ()
    func.return
  }}
}}
"""


CASE_TEXT_STATIC = _build_case_text(
    func_name="matmul_reduce_static",
    out_ir=STATIC_OUT_IR,
    lhs_ir=STATIC_LHS_IR,
    rhs_ir=STATIC_RHS_IR,
)

CASE_TEXT_DYNAMIC = _build_case_text(
    func_name="matmul_reduce_dynamic",
    out_ir=DYNAMIC_OUT_IR,
    lhs_ir=DYNAMIC_LHS_IR,
    rhs_ir=DYNAMIC_RHS_IR,
)

CASE_TEXT_MIXED = _build_case_text(
    func_name="matmul_reduce_mixed",
    out_ir=MIXED_OUT_IR,
    lhs_ir=MIXED_LHS_IR,
    rhs_ir=MIXED_RHS_IR,
)


def _assert_common(result) -> None:
    """检查 matmul reduce 输出的稳定合同。

    创建者: 金铲铲大作战
    最后一次更改: 金铲铲大作战

    功能说明:
    - 对 `ircheck` 结果做 Python 侧断言，覆盖 CHECK 不适合表达的矩阵属性。
    - 明确拒绝旧桥接 op 文本。
    - 锁定 matmul reduce 只生成输出轴与 reduce 轴三个 tile 参数。

    使用示例:
    - `_assert_common(run_ircheck_text(CASE_TEXT_STATIC))`

    关联文件:
    - spec: [`spec/pass/lowering/tile_reduce.md`](spec/pass/lowering/tile_reduce.md)
    - test: [`test/pass/test_lowering_tile_reduce.py`](test/pass/test_lowering_tile_reduce.py)
    - 功能实现: [`expectation/pass/tile/reduce/matmul.py`](expectation/pass/tile/reduce/matmul.py)
    """

    assert result.ok is True, (
        f"expected ok=True, got ok={result.ok}, exit_code={result.exit_code}, message={result.message!r}"
    )
    assert result.exit_code == 0, f"expected exit_code=0, got {result.exit_code}"
    assert result.actual_ir.count("tuner.param") == 3
    assert result.actual_ir.count("symbol.for") == 3
    assert '"tile.step_value"(' not in result.actual_ir
    assert '"kernel_split.tile_value"(' not in result.actual_ir
    assert '"tile.symbol_literal"(' not in result.actual_ir
    assert '"kernel_split.symbol_literal"(' not in result.actual_ir
    assert result.actual_ir.count('"dma.view"') == 3
    assert '"dma.alloc"' in result.actual_ir
    assert '"dma.fill"' in result.actual_ir
    assert '"kernel.matmul"' in result.actual_ir
    assert '"kernel.binary_elewise"' in result.actual_ir
    assert 'tile.analysis = [["elewise", "reduce"], ["reduce", "elewise"], ["elewise", "elewise"]]' in result.actual_ir
    assert (
        'tile.tile_exprs = [["TILE_D0", "TILE_D1"], ["TILE_D0", "TILE_D1"], ["TILE_D0", "TILE_D1"]]'
        in result.actual_ir
    )


def _case_static() -> None:
    _assert_common(
        run_ircheck_text(
            CASE_TEXT_STATIC,
            source_path="expectation/pass/tile/reduce/matmul.py:static",
        )
    )


def _case_dynamic() -> None:
    _assert_common(
        run_ircheck_text(
            CASE_TEXT_DYNAMIC,
            source_path="expectation/pass/tile/reduce/matmul.py:dynamic",
        )
    )


def _case_mixed() -> None:
    _assert_common(
        run_ircheck_text(
            CASE_TEXT_MIXED,
            source_path="expectation/pass/tile/reduce/matmul.py:mixed",
        )
    )


def main() -> None:
    """运行 matmul reduce expectation。

    创建者: 金铲铲大作战
    最后一次更改: 金铲铲大作战

    功能说明:
    - 顺序运行静态、动态、mixed 三个 case。
    - 汇总失败并抛出，便于目录入口返回稳定退出码。

    使用示例:
    - `main()`

    关联文件:
    - spec: [`spec/pass/lowering/tile_reduce.md`](spec/pass/lowering/tile_reduce.md)
    - test: [`test/pass/test_lowering_tile_reduce.py`](test/pass/test_lowering_tile_reduce.py)
    - 功能实现: [`expectation/pass/tile/reduce/matmul.py`](expectation/pass/tile/reduce/matmul.py)
    """

    failures: list[tuple[str, BaseException]] = []
    run_case(failures, "CASE-matmul-reduce-static", _case_static)
    run_case(failures, "CASE-matmul-reduce-dynamic", _case_dynamic)
    run_case(failures, "CASE-matmul-reduce-mixed", _case_mixed)
    raise_if_failures("tile reduce matmul expectation", failures)


if __name__ == "__main__":
    main()
