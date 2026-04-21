# [immutable-file]
"""tile-reduce fc-chain expectation.

创建者: 金铲铲大作战
最后一次更改: 朽木露琪亚

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
    out_expr: str,
) -> str:
    """生成单个 fc reduce expectation 文本。

    创建者: 金铲铲大作战
    最后一次更改: 朽木露琪亚

    功能说明:
    - 输入链路中 `kernel.matmul` 使用当前 out-first operand 顺序。
    - 只在 CHECK 中约束稳定结构，详细属性由 `_assert_common` 验证。

    使用示例:
    - `text = _build_case_text(func_name="case", out_ir=out_ir, x_ir=x_ir, weight_t_ir=weight_ir, bias_ir=bias_ir, batch_expr="B", out_expr="O")`

    关联文件:
    - spec: [`spec/pass/lowering/tile_reduce.md`](spec/pass/lowering/tile_reduce.md)
    - test: [`test/pass/test_lowering_tile_reduce.py`](test/pass/test_lowering_tile_reduce.py)
    - 功能实现: [`expectation/pass/tile/reduce/fc.py`](expectation/pass/tile/reduce/fc.py)
    """

    return rf"""// COMPILE_ARGS: --pass tile-reduce
// CHECK: builtin.module {{
// CHECK: func.func @{func_name}
// CHECK: "dma.broadcast"
// CHECK: tuner.param : !symbol.int<"TILE_M0">
// CHECK: tuner.param : !symbol.int<"TILE_M1">
// CHECK: tuner.param : !symbol.int<"TILE_R0">
// CHECK: step = "TILE_M0"
// CHECK: step = "TILE_M1"
// CHECK: "dma.fill"
// CHECK: step = "TILE_R0"
// CHECK: "dma.alloc"
// CHECK: "kernel.matmul"
// CHECK: "kernel.binary_elewise"

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
    out_expr=str(STATIC_OUT),
)

CASE_TEXT_DYNAMIC = _build_case_text(
    func_name="fc_reduce_dynamic",
    out_ir=DYNAMIC_OUT_IR,
    x_ir=DYNAMIC_X_IR,
    weight_t_ir=DYNAMIC_WEIGHT_T_IR,
    bias_ir=DYNAMIC_BIAS_IR,
    batch_expr=SYM_BATCH,
    out_expr=SYM_OUT,
)

CASE_TEXT_MIXED = _build_case_text(
    func_name="fc_reduce_mixed",
    out_ir=MIXED_OUT_IR,
    x_ir=MIXED_X_IR,
    weight_t_ir=MIXED_WEIGHT_T_IR,
    bias_ir=MIXED_BIAS_IR,
    batch_expr=str(STATIC_BATCH),
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
