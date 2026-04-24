# [immutable-file]
"""tile-reduce `kernel.matmul` expectation.

创建者: 金铲铲大作战
最后一次更改: 大闸蟹

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


def _build_case_text(
    *,
    func_name: str,
    out_ir: str,
    lhs_ir: str,
    rhs_ir: str,
    m_expr: str,
    k_expr: str,
    n_expr: str,
) -> str:
    """生成单个 matmul reduce expectation 文本。

    创建者: 金铲铲大作战
    最后一次更改: 朽木露琪亚

    功能说明:
    - 输入使用当前 kernel 合同的 out-first operand 顺序。
    - CHECK 行锁定三层循环、三类 view、fill、临时 alloc、matmul 与累加 binary。

    使用示例:
    - `text = _build_case_text(func_name="case", out_ir=out_ir, lhs_ir=lhs_ir, rhs_ir=rhs_ir)`

    关联文件:
    - spec: [`spec/pass/lowering/tile_reduce.md`](spec/pass/lowering/tile_reduce.md)
    - test: [`test/pass/test_lowering_tile_reduce.py`](test/pass/test_lowering_tile_reduce.py)
    - 功能实现: [`expectation/pass/tile/reduce/matmul.py`](expectation/pass/tile/reduce/matmul.py)
    """

    return rf"""// COMPILE_ARGS: --pass tile-reduce
// CHECK: builtin.module {{
// CHECK-NEXT: func.func @{func_name}(%[[OUT:{{reg}}]] : {out_ir}, %[[LHS:{{reg}}]] : {lhs_ir}, %[[RHS:{{reg}}]] : {rhs_ir}) {{
// CHECK: %[[D0:{{reg}}]] = tuner.param : !symbol.int<"TILE_D0">
// CHECK-NEXT: %[[D1:{{reg}}]] = tuner.param : !symbol.int<"TILE_D1">
// CHECK-NEXT: %[[R0:{{reg}}]] = tuner.param : !symbol.int<"TILE_R0">
// CHECK: %[[ZERO0:{{reg}}]] = "symbol.const"() <{{value = 0 : i64}}> : () -> !symbol.int<"0">
// CHECK-NEXT: %[[M_DIM:{{reg}}]] = "symbol.get_dim"(%[[LHS]]) {{axis = #builtin.int<0>}} : ({lhs_ir}) -> !symbol.int<"{m_expr}">
// CHECK: %[[ZERO1:{{reg}}]] = "symbol.const"() <{{value = 0 : i64}}> : () -> !symbol.int<"0">
// CHECK-NEXT: %[[N_DIM:{{reg}}]] = "symbol.get_dim"(%[[RHS]]) {{axis = #builtin.int<1>}} : ({rhs_ir}) -> !symbol.int<"{n_expr}">
// CHECK-NEXT: %[[K_DIM:{{reg}}]] = "symbol.get_dim"(%[[LHS]]) {{axis = #builtin.int<1>}} : ({lhs_ir}) -> !symbol.int<"{k_expr}">
// CHECK: symbol.for %[[M_IT:{{reg}}]] = %[[ZERO0]] to %[[M_DIM]] step %[[D0]] {{iter = #symbol.iter<start = "0", end = "{m_expr}", step = "TILE_D0">}} {{
// CHECK-NEXT:   symbol.for %[[N_IT:{{reg}}]] = %[[ZERO1]] to %[[N_DIM]] step %[[D1]] {{iter = #symbol.iter<start = "0", end = "{n_expr}", step = "TILE_D1">}} {{
// CHECK:     %[[ONE:{{reg}}]] = "symbol.const"() <{{value = 1 : i64}}> : () -> !symbol.int<"1">
// CHECK-NEXT:     %[[OUT_VIEW:{{reg}}]] = "dma.view"(%[[OUT]], %[[M_IT]], %[[N_IT]], %[[D0]], %[[D1]], %[[D1]], %[[ONE]])
// CHECK-NEXT:     "dma.fill"(%[[OUT_VIEW]], %[[ZERO0]])
// CHECK-NEXT:     symbol.for %[[K_IT:{{reg}}]] = %[[ZERO0]] to %[[K_DIM]] step %[[R0]] {{iter = #symbol.iter<start = "0", end = "{k_expr}", step = "TILE_R0">}} {{
// CHECK-NEXT:       %[[LHS_VIEW:{{reg}}]] = "dma.view"(%[[LHS]], %[[M_IT]], %[[K_IT]], %[[D0]], %[[R0]], %[[R0]], %[[ONE]])
// CHECK-NEXT:       %[[RHS_VIEW:{{reg}}]] = "dma.view"(%[[RHS]], %[[K_IT]], %[[N_IT]], %[[R0]], %[[D1]], %[[D1]], %[[ONE]])
// CHECK-NEXT:       %[[ACC:{{reg}}]] = "dma.alloc"(%[[D0]], %[[D1]])
// CHECK-NEXT:       "kernel.matmul"(%[[ACC]], %[[LHS_VIEW]], %[[RHS_VIEW]]) {{space = {SPACE_ATTR}, tile.analysis = \[\["elewise", "reduce"\], \["reduce", "elewise"\], \["elewise", "elewise"\]\], tile.tile_exprs = \[\["TILE_D0", "TILE_D1"\], \["TILE_D0", "TILE_D1"\], \["TILE_D0", "TILE_D1"\]\]}}
// CHECK-NEXT:       "kernel.binary_elewise"(%[[OUT_VIEW]], %[[ACC]], %[[OUT_VIEW]]) {{kind = "add", space = {SPACE_ATTR}}}
// CHECK-NOT: "tile.step_value"(
// CHECK-NOT: "kernel_split.tile_value"(
// CHECK-NOT: "tile.symbol_literal"(
// CHECK-NOT: "kernel_split.symbol_literal"(

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
    m_expr=str(STATIC_M),
    k_expr=str(STATIC_K),
    n_expr=str(STATIC_N),
)

CASE_TEXT_DYNAMIC = _build_case_text(
    func_name="matmul_reduce_dynamic",
    out_ir=DYNAMIC_OUT_IR,
    lhs_ir=DYNAMIC_LHS_IR,
    rhs_ir=DYNAMIC_RHS_IR,
    m_expr=SYM_M,
    k_expr=SYM_K,
    n_expr=SYM_N,
)

CASE_TEXT_MIXED = _build_case_text(
    func_name="matmul_reduce_mixed",
    out_ir=MIXED_OUT_IR,
    lhs_ir=MIXED_LHS_IR,
    rhs_ir=MIXED_RHS_IR,
    m_expr=str(STATIC_M),
    k_expr=SYM_K,
    n_expr=str(STATIC_N),
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
    assert result.actual_ir.count('"symbol.get_dim"') == 3
    assert "axis = #builtin.int<0>" in result.actual_ir
    assert result.actual_ir.count("axis = #builtin.int<1>") >= 2
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
