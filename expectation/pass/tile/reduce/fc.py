# [immutable-file]
"""tile-reduce fc-chain expectation.

创建者: 金铲铲大作战
最后一次更改: 大闸蟹

功能说明:
- 使用 `ircheck` 验证 fc 风格组合链路中的 out-first `kernel.matmul` reduce 改写。
- 覆盖 `dma.broadcast -> kernel.matmul -> kernel.binary_elewise` 输入链路。
- 检查当前输出中的 `TILE_M0/TILE_M1/TILE_R0`、三层 `symbol.for`
  以及 rewritten matmul 的 `tile.analysis + tile.tile_exprs`，并拒绝组合链路中未被 reduce 消费的 tile 参数。

使用示例:
- `PYTHONPATH=/path/to/worktree:/home/lfr/kernelcode_generate python -m expectation.pass.tile.reduce.fc`

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

STATIC_BATCH, STATIC_IN, STATIC_OUT, SYM_BATCH, SYM_IN, SYM_OUT = random_rank3_static_dynamic()

STATIC_OUT_IR = memory_ir([STATIC_BATCH, STATIC_OUT], FLOAT_DTYPE)
STATIC_X_IR = memory_ir([STATIC_BATCH, STATIC_IN], FLOAT_DTYPE)
STATIC_WEIGHT_T_IR = memory_ir([STATIC_IN, STATIC_OUT], FLOAT_DTYPE)
STATIC_BIAS_IR = memory_ir([STATIC_OUT], FLOAT_DTYPE)

DYNAMIC_OUT_IR = memory_ir([SYM_BATCH, SYM_OUT], FLOAT_DTYPE)
DYNAMIC_X_IR = memory_ir([SYM_BATCH, SYM_IN], FLOAT_DTYPE)
DYNAMIC_WEIGHT_T_IR = memory_ir([SYM_IN, SYM_OUT], FLOAT_DTYPE)
DYNAMIC_BIAS_IR = memory_ir([SYM_OUT], FLOAT_DTYPE)

MIXED_OUT_IR = memory_ir([STATIC_BATCH, STATIC_OUT], FLOAT_DTYPE)
MIXED_X_IR = memory_ir([STATIC_BATCH, SYM_IN], FLOAT_DTYPE)
MIXED_WEIGHT_T_IR = memory_ir([SYM_IN, STATIC_OUT], FLOAT_DTYPE)
MIXED_BIAS_IR = memory_ir([STATIC_OUT], FLOAT_DTYPE)


def _build_case_text(
    *,
    func_name: str,
    out_ir: str,
    x_ir: str,
    weight_t_ir: str,
    bias_ir: str,
    batch_expr: str,
    reduce_expr: str,
    out_expr: str,
) -> str:
    """生成单个 fc reduce expectation 文本。

    创建者: 金铲铲大作战
    最后一次更改: 朽木露琪亚

    功能说明:
    - 输入链路中 `kernel.matmul` 使用当前 out-first operand 顺序。
    - CHECK 同时约束未被 reduce 消费的 broadcast/final binary，以及 reduce 改写后的三层循环。

    使用示例:
    - `text = _build_case_text(func_name="case", out_ir=out_ir, x_ir=x_ir, weight_t_ir=weight_ir, bias_ir=bias_ir, batch_expr="B", out_expr="O")`

    关联文件:
    - spec: [`spec/pass/lowering/tile_reduce.md`](spec/pass/lowering/tile_reduce.md)
    - test: [`test/pass/test_lowering_tile_reduce.py`](test/pass/test_lowering_tile_reduce.py)
    - 功能实现: [`expectation/pass/tile/reduce/fc.py`](expectation/pass/tile/reduce/fc.py)
    """

    return rf"""// COMPILE_ARGS: --pass tile-reduce
// CHECK: builtin.module {{
// CHECK-NEXT: func.func @{func_name}(%[[OUT:{{reg}}]] : {out_ir}, %[[X:{{reg}}]] : {x_ir}, %[[WEIGHT_T:{{reg}}]] : {weight_t_ir}, %[[BIAS:{{reg}}]] : {bias_ir}) {{
// CHECK-NEXT: %[[BATCH_DIM:{{reg}}]] = "symbol.get_dim"(%[[OUT]]) {{axis = #builtin.int<0>}} : ({out_ir}) -> !symbol.int<"{batch_expr}">
// CHECK-NEXT: %[[OUT_DIM:{{reg}}]] = "symbol.get_dim"(%[[OUT]]) {{axis = #builtin.int<1>}} : ({out_ir}) -> !symbol.int<"{out_expr}">
// CHECK-NEXT: %[[BIAS_B:{{reg}}]] = "dma.alloc"(%[[BATCH_DIM]], %[[OUT_DIM]])
// CHECK-NEXT: %[[MAT_OUT:{{reg}}]] = "dma.alloc"(%[[BATCH_DIM]], %[[OUT_DIM]])
// CHECK-NEXT: "dma.broadcast"(%[[BIAS_B]], %[[BIAS]]) {{tile.analysis = \[\["elewise", "elewise"\], \["expand", "elewise"\]\], tile.tile_exprs = \[\["", ""\], \["", ""\]\]}}
// CHECK-NEXT: "kernel.binary_elewise"(%[[OUT]], %[[MAT_OUT]], %[[BIAS_B]]) {{kind = "add", space = {SPACE_ATTR}, tile.analysis = \[\["elewise", "elewise"\], \["elewise", "elewise"\], \["elewise", "elewise"\]\], tile.tile_exprs = \[\["", ""\], \["", ""\], \["", ""\]\]}}
// CHECK-NEXT: %[[M0:{{reg}}]] = tuner.param : !symbol.int<"TILE_M0">
// CHECK-NEXT: %[[M1:{{reg}}]] = tuner.param : !symbol.int<"TILE_M1">
// CHECK-NEXT: %[[R0:{{reg}}]] = tuner.param : !symbol.int<"TILE_R0">
// CHECK: %[[ZERO0:{{reg}}]] = "symbol.const"() <{{value = 0 : i64}}> : () -> !symbol.int<"0">
// CHECK-NEXT: %[[X_BATCH:{{reg}}]] = "symbol.get_dim"(%[[X]]) {{axis = #builtin.int<0>}} : ({x_ir}) -> !symbol.int<"{batch_expr}">
// CHECK: %[[ZERO1:{{reg}}]] = "symbol.const"() <{{value = 0 : i64}}> : () -> !symbol.int<"0">
// CHECK-NEXT: %[[WEIGHT_OUT:{{reg}}]] = "symbol.get_dim"(%[[WEIGHT_T]]) {{axis = #builtin.int<1>}} : ({weight_t_ir}) -> !symbol.int<"{out_expr}">
// CHECK-NEXT: %[[X_REDUCE:{{reg}}]] = "symbol.get_dim"(%[[X]]) {{axis = #builtin.int<1>}} : ({x_ir}) -> !symbol.int<"{reduce_expr}">
// CHECK: symbol.for %[[M_IT:{{reg}}]] = %[[ZERO0]] to %[[X_BATCH]] step %[[M0]] {{iter = #symbol.iter<start = "0", end = "{batch_expr}", step = "TILE_M0">}} {{
// CHECK-NEXT:   symbol.for %[[N_IT:{{reg}}]] = %[[ZERO1]] to %[[WEIGHT_OUT]] step %[[M1]] {{iter = #symbol.iter<start = "0", end = "{out_expr}", step = "TILE_M1">}} {{
// CHECK:     %[[ONE:{{reg}}]] = "symbol.const"() <{{value = 1 : i64}}> : () -> !symbol.int<"1">
// CHECK-NEXT:     %[[OUT_VIEW:{{reg}}]] = "dma.view"(%[[MAT_OUT]], %[[M_IT]], %[[N_IT]], %[[M0]], %[[M1]], %[[M1]], %[[ONE]])
// CHECK-NEXT:     "dma.fill"(%[[OUT_VIEW]], %[[ZERO0]])
// CHECK-NEXT:     symbol.for %[[K_IT:{{reg}}]] = %[[ZERO0]] to %[[X_REDUCE]] step %[[R0]] {{iter = #symbol.iter<start = "0", end = "{reduce_expr}", step = "TILE_R0">}} {{
// CHECK-NEXT:       %[[X_VIEW:{{reg}}]] = "dma.view"(%[[X]], %[[M_IT]], %[[K_IT]], %[[M0]], %[[R0]], %[[R0]], %[[ONE]])
// CHECK-NEXT:       %[[WEIGHT_VIEW:{{reg}}]] = "dma.view"(%[[WEIGHT_T]], %[[K_IT]], %[[N_IT]], %[[R0]], %[[M1]], %[[M1]], %[[ONE]])
// CHECK-NEXT:       %[[ACC:{{reg}}]] = "dma.alloc"(%[[M0]], %[[M1]])
// CHECK-NEXT:       "kernel.matmul"(%[[ACC]], %[[X_VIEW]], %[[WEIGHT_VIEW]]) {{space = {SPACE_ATTR}, tile.analysis = \[\["elewise", "reduce"\], \["reduce", "elewise"\], \["elewise", "elewise"\]\], tile.tile_exprs = \[\["TILE_M0", "TILE_M1"\], \["TILE_M0", "TILE_M1"\], \["TILE_M0", "TILE_M1"\]\]}}
// CHECK-NEXT:       "kernel.binary_elewise"(%[[OUT_VIEW]], %[[ACC]], %[[OUT_VIEW]]) {{kind = "add", space = {SPACE_ATTR}}}
// CHECK-NOT: "tile.step_value"(
// CHECK-NOT: "kernel_split.tile_value"(
// CHECK-NOT: "tile.symbol_literal"(
// CHECK-NOT: "kernel_split.symbol_literal"(

builtin.module {{
  func.func @{func_name}(%out : {out_ir}, %x : {x_ir}, %weight_t : {weight_t_ir}, %bias : {bias_ir}) {{
    %d0 = "symbol.get_dim"(%out) {{axis = #builtin.int<0>}} : ({out_ir}) -> !symbol.int<"{batch_expr}">
    %d1 = "symbol.get_dim"(%out) {{axis = #builtin.int<1>}} : ({out_ir}) -> !symbol.int<"{out_expr}">
    %bias_b = "dma.alloc"(%d0, %d1) <{{operandSegmentSizes = array<i32: 2>}}> : (!symbol.int<"{batch_expr}">, !symbol.int<"{out_expr}">) -> {out_ir}
    %mat_out = "dma.alloc"(%d0, %d1) <{{operandSegmentSizes = array<i32: 2>}}> : (!symbol.int<"{batch_expr}">, !symbol.int<"{out_expr}">) -> {out_ir}
    "dma.broadcast"(%bias_b, %bias) {{tile.analysis = [["elewise", "elewise"], ["expand", "elewise"]], tile.tile_exprs = [["", ""], ["", ""]]}} : ({out_ir}, {bias_ir}) -> ()
    "kernel.matmul"(%mat_out, %x, %weight_t) {{space = {SPACE_ATTR}, tile.analysis = [["elewise", "reduce"], ["reduce", "elewise"], ["elewise", "elewise"]], tile.tile_exprs = [["", ""], ["", ""], ["", ""]]}} : ({out_ir}, {x_ir}, {weight_t_ir}) -> ()
    "kernel.binary_elewise"(%out, %mat_out, %bias_b) {{kind = "add", space = {SPACE_ATTR}, tile.analysis = [["elewise", "elewise"], ["elewise", "elewise"], ["elewise", "elewise"]], tile.tile_exprs = [["", ""], ["", ""], ["", ""]]}} : ({out_ir}, {out_ir}, {out_ir}) -> ()
    func.return
  }}
}}
"""


CASE_TEXT_STATIC = _build_case_text(
    func_name="fc_reduce_static",
    out_ir=STATIC_OUT_IR,
    x_ir=STATIC_X_IR,
    weight_t_ir=STATIC_WEIGHT_T_IR,
    bias_ir=STATIC_BIAS_IR,
    batch_expr=str(STATIC_BATCH),
    reduce_expr=str(STATIC_IN),
    out_expr=str(STATIC_OUT),
)

CASE_TEXT_DYNAMIC = _build_case_text(
    func_name="fc_reduce_dynamic",
    out_ir=DYNAMIC_OUT_IR,
    x_ir=DYNAMIC_X_IR,
    weight_t_ir=DYNAMIC_WEIGHT_T_IR,
    bias_ir=DYNAMIC_BIAS_IR,
    batch_expr=SYM_BATCH,
    reduce_expr=SYM_IN,
    out_expr=SYM_OUT,
)

CASE_TEXT_MIXED = _build_case_text(
    func_name="fc_reduce_mixed",
    out_ir=MIXED_OUT_IR,
    x_ir=MIXED_X_IR,
    weight_t_ir=MIXED_WEIGHT_T_IR,
    bias_ir=MIXED_BIAS_IR,
    batch_expr=str(STATIC_BATCH),
    reduce_expr=SYM_IN,
    out_expr=str(STATIC_OUT),
)


def _assert_common(result) -> None:
    """检查 fc reduce 输出的稳定合同。

    创建者: 金铲铲大作战
    最后一次更改: 金铲铲大作战

    功能说明:
    - 确认 fc 输入链路保留 broadcast 与最终 binary。
    - 确认 matmul reduce 改写后存在三层循环和新 tile 表达矩阵。
    - 确认组合链路没有生成未被 reduce 改写消费的额外 tile 参数。

    使用示例:
    - `_assert_common(run_ircheck_text(CASE_TEXT_STATIC))`

    关联文件:
    - spec: [`spec/pass/lowering/tile_reduce.md`](spec/pass/lowering/tile_reduce.md)
    - test: [`test/pass/test_lowering_tile_reduce.py`](test/pass/test_lowering_tile_reduce.py)
    - 功能实现: [`expectation/pass/tile/reduce/fc.py`](expectation/pass/tile/reduce/fc.py)
    """

    assert result.ok is True, (
        f"expected ok=True, got ok={result.ok}, exit_code={result.exit_code}, message={result.message!r}"
    )
    assert result.exit_code == 0, f"expected exit_code=0, got {result.exit_code}"
    assert result.actual_ir.count("tuner.param") == 3
    assert result.actual_ir.count("symbol.for") == 3
    assert result.actual_ir.count('"symbol.get_dim"') == 5
    assert 'symbol.int<"TILE_B0">' not in result.actual_ir
    assert 'symbol.int<"TILE_E0">' not in result.actual_ir
    assert 'symbol.int<"TILE_E1">' not in result.actual_ir
    assert '"tile.step_value"(' not in result.actual_ir
    assert '"kernel_split.tile_value"(' not in result.actual_ir
    assert '"tile.symbol_literal"(' not in result.actual_ir
    assert '"kernel_split.symbol_literal"(' not in result.actual_ir
    assert result.actual_ir.count('"dma.alloc"') >= 3
    assert result.actual_ir.count('"dma.view"') == 3
    assert '"dma.broadcast"' in result.actual_ir
    assert '"dma.fill"' in result.actual_ir
    assert '"kernel.matmul"' in result.actual_ir
    assert result.actual_ir.count('"kernel.binary_elewise"') >= 2
    assert 'tile.analysis = [["elewise", "reduce"], ["reduce", "elewise"], ["elewise", "elewise"]]' in result.actual_ir
    assert (
        'tile.tile_exprs = [["TILE_M0", "TILE_M1"], ["TILE_M0", "TILE_M1"], ["TILE_M0", "TILE_M1"]]'
        in result.actual_ir
    )


def _case_static() -> None:
    _assert_common(
        run_ircheck_text(
            CASE_TEXT_STATIC,
            source_path="expectation/pass/tile/reduce/fc.py:static",
        )
    )


def _case_dynamic() -> None:
    _assert_common(
        run_ircheck_text(
            CASE_TEXT_DYNAMIC,
            source_path="expectation/pass/tile/reduce/fc.py:dynamic",
        )
    )


def _case_mixed() -> None:
    _assert_common(
        run_ircheck_text(
            CASE_TEXT_MIXED,
            source_path="expectation/pass/tile/reduce/fc.py:mixed",
        )
    )


def main() -> None:
    """运行 fc reduce expectation。

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
    - 功能实现: [`expectation/pass/tile/reduce/fc.py`](expectation/pass/tile/reduce/fc.py)
    """

    failures: list[tuple[str, BaseException]] = []
    run_case(failures, "CASE-fc-reduce-static", _case_static)
    run_case(failures, "CASE-fc-reduce-dynamic", _case_dynamic)
    run_case(failures, "CASE-fc-reduce-mixed", _case_mixed)
    raise_if_failures("tile reduce fc expectation", failures)


if __name__ == "__main__":
    main()
