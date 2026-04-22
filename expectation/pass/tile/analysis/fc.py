# [immutable-file]
"""tile `analysis-only=true` 的 `fc` 组合链路分析 expectation。

创建者: 大闸蟹
最后一次更改: 大闸蟹

功能说明:
- 使用 `ircheck` 黑盒锁定 `tile-analysis` 对 `fc` 风格链路中的
  `dma.transpose` / `dma.broadcast` / `kernel.matmul` / `kernel.binary_elewise`
  只添加分析属性，不插入 loop/view/helper。
- 当前合同固定为“只保留维度角色，不出现维度值/符号名”：
  - `dma.broadcast(bias -> bias_b)`：`[["elewise", "elewise"], ["expand", "elewise"]]`
  - `kernel.matmul(x, weight_t, mat_out)`：`[["elewise", "reduce"], ["reduce", "elewise"], ["elewise", "elewise"]]`
  - `kernel.binary_elewise(kind=add)`：`[["elewise", "elewise"], ["elewise", "elewise"], ["elewise", "elewise"]]`

使用示例:
- `PYTHONPATH=. python expectation/pass/tile/analysis/fc.py`

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

CASE_TEXT_FC_STATIC = """// COMPILE_ARGS: --pass "tile-analysis"
// CHECK: builtin.module {
// CHECK-NEXT: func.func @fc_kernel(%[[OUT:{reg}]] : !nn.memory<[6, 7], [7, 1], f32, #nn.space<global>>, %[[X:{reg}]] : !nn.memory<[6, 6], [6, 1], f32, #nn.space<global>>, %[[WEIGHT:{reg}]] : !nn.memory<[7, 6], [6, 1], f32, #nn.space<global>>, %[[BIAS:{reg}]] : !nn.memory<[7], [1], f32, #nn.space<global>>) {
// CHECK-NEXT: %weight_t = "dma.alloc"() <{operandSegmentSizes = array<i32: 0>}> : () -> !nn.memory<[6, 7], [1, 6], f32, #nn.space<global>>
// CHECK-NEXT: %bias_b = "dma.alloc"() <{operandSegmentSizes = array<i32: 0>}> : () -> !nn.memory<[6, 7], [7, 1], f32, #nn.space<global>>
// CHECK-NEXT: %mat_out = "dma.alloc"() <{operandSegmentSizes = array<i32: 0>}> : () -> !nn.memory<[6, 7], [7, 1], f32, #nn.space<global>>
// CHECK-NEXT: "dma.transpose"(%weight_t, %weight) {perm = [1 : i64, 0 : i64]} : (!nn.memory<[6, 7], [1, 6], f32, #nn.space<global>>, !nn.memory<[7, 6], [6, 1], f32, #nn.space<global>>) -> ()
// CHECK-NEXT: "dma.broadcast"(%bias_b, %bias) {tile.analysis = \[\["elewise", "elewise"\], \["expand", "elewise"\]\], tile.tile_exprs = \[\["", ""\], \["", ""\]\]} : (!nn.memory<[6, 7], [7, 1], f32, #nn.space<global>>, !nn.memory<[7], [1], f32, #nn.space<global>>) -> ()
// CHECK-NEXT: "kernel.matmul"(%x, %weight_t, %mat_out) {space = #nn.space<global>, tile.analysis = \[\["elewise", "reduce"\], \["reduce", "elewise"\], \["elewise", "elewise"\]\], tile.tile_exprs = \[\["", ""\], \["", ""\], \["", ""\]\]} : (!nn.memory<[6, 6], [6, 1], f32, #nn.space<global>>, !nn.memory<[6, 7], [1, 6], f32, #nn.space<global>>, !nn.memory<[6, 7], [7, 1], f32, #nn.space<global>>) -> ()
// CHECK-NEXT: "kernel.binary_elewise"(%mat_out, %bias_b, %out) {kind = "add", space = #nn.space<global>, tile.analysis = \[\["elewise", "elewise"\], \["elewise", "elewise"\], \["elewise", "elewise"\]\], tile.tile_exprs = \[\["", ""\], \["", ""\], \["", ""\]\]} : (!nn.memory<[6, 7], [7, 1], f32, #nn.space<global>>, !nn.memory<[6, 7], [7, 1], f32, #nn.space<global>>, !nn.memory<[6, 7], [7, 1], f32, #nn.space<global>>) -> ()
// CHECK-NEXT: func.return
// CHECK-NEXT: }
// CHECK-NEXT: }
// CHECK-NOT: tuner.param
// CHECK-NOT: "symbol.get_dim"(
// CHECK-NOT: symbol.for
// CHECK-NOT: "dma.view"(

builtin.module {
  func.func @fc_kernel(%out : !nn.memory<[6, 7], [7, 1], f32, #nn.space<global>>, %x : !nn.memory<[6, 6], [6, 1], f32, #nn.space<global>>, %weight : !nn.memory<[7, 6], [6, 1], f32, #nn.space<global>>, %bias : !nn.memory<[7], [1], f32, #nn.space<global>>) {
    %weight_t = "dma.alloc"() <{operandSegmentSizes = array<i32: 0>}> : () -> !nn.memory<[6, 7], [1, 6], f32, #nn.space<global>>
    %bias_b = "dma.alloc"() <{operandSegmentSizes = array<i32: 0>}> : () -> !nn.memory<[6, 7], [7, 1], f32, #nn.space<global>>
    %mat_out = "dma.alloc"() <{operandSegmentSizes = array<i32: 0>}> : () -> !nn.memory<[6, 7], [7, 1], f32, #nn.space<global>>
    "dma.transpose"(%weight_t, %weight) {perm = [1 : i64, 0 : i64]} : (!nn.memory<[6, 7], [1, 6], f32, #nn.space<global>>, !nn.memory<[7, 6], [6, 1], f32, #nn.space<global>>) -> ()
    "dma.broadcast"(%bias_b, %bias) : (!nn.memory<[6, 7], [7, 1], f32, #nn.space<global>>, !nn.memory<[7], [1], f32, #nn.space<global>>) -> ()
    "kernel.matmul"(%x, %weight_t, %mat_out) {space = #nn.space<global>} : (!nn.memory<[6, 6], [6, 1], f32, #nn.space<global>>, !nn.memory<[6, 7], [1, 6], f32, #nn.space<global>>, !nn.memory<[6, 7], [7, 1], f32, #nn.space<global>>) -> ()
    "kernel.binary_elewise"(%mat_out, %bias_b, %out) {kind = "add", space = #nn.space<global>} : (!nn.memory<[6, 7], [7, 1], f32, #nn.space<global>>, !nn.memory<[6, 7], [7, 1], f32, #nn.space<global>>, !nn.memory<[6, 7], [7, 1], f32, #nn.space<global>>) -> ()
    func.return
  }
}
"""

CASE_TEXT_FC_DYNAMIC = """// COMPILE_ARGS: --pass "tile-analysis"
// CHECK: builtin.module {
// CHECK-NEXT: func.func @fc_kernel_dynamic(%[[OUT:{reg}]] : !nn.memory<[N, OUT], [OUT, 1], f32, #nn.space<global>>, %[[X:{reg}]] : !nn.memory<[N, IN], [IN, 1], f32, #nn.space<global>>, %[[WEIGHT:{reg}]] : !nn.memory<[OUT, IN], [IN, 1], f32, #nn.space<global>>, %[[BIAS:{reg}]] : !nn.memory<[OUT], [1], f32, #nn.space<global>>, %[[N:{reg}]] : !symbol.int<"N">, %[[IN_DIM:{reg}]] : !symbol.int<"IN">, %[[OUT_DIM:{reg}]] : !symbol.int<"OUT">) {
// CHECK-NEXT: %weight_t = "dma.alloc"(%in_dim, %out_dim) <{operandSegmentSizes = array<i32: 2>}> : (!symbol.int<"IN">, !symbol.int<"OUT">) -> !nn.memory<[IN, OUT], [1, IN], f32, #nn.space<global>>
// CHECK-NEXT: %bias_b = "dma.alloc"(%n, %out_dim) <{operandSegmentSizes = array<i32: 2>}> : (!symbol.int<"N">, !symbol.int<"OUT">) -> !nn.memory<[N, OUT], [OUT, 1], f32, #nn.space<global>>
// CHECK-NEXT: %mat_out = "dma.alloc"(%n, %out_dim) <{operandSegmentSizes = array<i32: 2>}> : (!symbol.int<"N">, !symbol.int<"OUT">) -> !nn.memory<[N, OUT], [OUT, 1], f32, #nn.space<global>>
// CHECK-NEXT: "dma.transpose"(%weight_t, %weight) {perm = [1 : i64, 0 : i64]} : (!nn.memory<[IN, OUT], [1, IN], f32, #nn.space<global>>, !nn.memory<[OUT, IN], [IN, 1], f32, #nn.space<global>>) -> ()
// CHECK-NEXT: "dma.broadcast"(%bias_b, %bias) {tile.analysis = \[\["elewise", "elewise"\], \["expand", "elewise"\]\], tile.tile_exprs = \[\["", ""\], \["", ""\]\]} : (!nn.memory<[N, OUT], [OUT, 1], f32, #nn.space<global>>, !nn.memory<[OUT], [1], f32, #nn.space<global>>) -> ()
// CHECK-NEXT: "kernel.matmul"(%x, %weight_t, %mat_out) {space = #nn.space<global>, tile.analysis = \[\["elewise", "reduce"\], \["reduce", "elewise"\], \["elewise", "elewise"\]\], tile.tile_exprs = \[\["", ""\], \["", ""\], \["", ""\]\]} : (!nn.memory<[N, IN], [IN, 1], f32, #nn.space<global>>, !nn.memory<[IN, OUT], [1, IN], f32, #nn.space<global>>, !nn.memory<[N, OUT], [OUT, 1], f32, #nn.space<global>>) -> ()
// CHECK-NEXT: "kernel.binary_elewise"(%mat_out, %bias_b, %out) {kind = "add", space = #nn.space<global>, tile.analysis = \[\["elewise", "elewise"\], \["elewise", "elewise"\], \["elewise", "elewise"\]\], tile.tile_exprs = \[\["", ""\], \["", ""\], \["", ""\]\]} : (!nn.memory<[N, OUT], [OUT, 1], f32, #nn.space<global>>, !nn.memory<[N, OUT], [OUT, 1], f32, #nn.space<global>>, !nn.memory<[N, OUT], [OUT, 1], f32, #nn.space<global>>) -> ()
// CHECK-NEXT: func.return
// CHECK-NEXT: }
// CHECK-NEXT: }
// CHECK-NOT: tuner.param
// CHECK-NOT: "symbol.get_dim"(
// CHECK-NOT: symbol.for
// CHECK-NOT: "dma.view"(

builtin.module {
  func.func @fc_kernel_dynamic(%out : !nn.memory<[N, OUT], [OUT, 1], f32, #nn.space<global>>, %x : !nn.memory<[N, IN], [IN, 1], f32, #nn.space<global>>, %weight : !nn.memory<[OUT, IN], [IN, 1], f32, #nn.space<global>>, %bias : !nn.memory<[OUT], [1], f32, #nn.space<global>>, %n : !symbol.int<"N">, %in_dim : !symbol.int<"IN">, %out_dim : !symbol.int<"OUT">) {
    %weight_t = "dma.alloc"(%in_dim, %out_dim) <{operandSegmentSizes = array<i32: 2>}> : (!symbol.int<"IN">, !symbol.int<"OUT">) -> !nn.memory<[IN, OUT], [1, IN], f32, #nn.space<global>>
    %bias_b = "dma.alloc"(%n, %out_dim) <{operandSegmentSizes = array<i32: 2>}> : (!symbol.int<"N">, !symbol.int<"OUT">) -> !nn.memory<[N, OUT], [OUT, 1], f32, #nn.space<global>>
    %mat_out = "dma.alloc"(%n, %out_dim) <{operandSegmentSizes = array<i32: 2>}> : (!symbol.int<"N">, !symbol.int<"OUT">) -> !nn.memory<[N, OUT], [OUT, 1], f32, #nn.space<global>>
    "dma.transpose"(%weight_t, %weight) {perm = [1 : i64, 0 : i64]} : (!nn.memory<[IN, OUT], [1, IN], f32, #nn.space<global>>, !nn.memory<[OUT, IN], [IN, 1], f32, #nn.space<global>>) -> ()
    "dma.broadcast"(%bias_b, %bias) : (!nn.memory<[N, OUT], [OUT, 1], f32, #nn.space<global>>, !nn.memory<[OUT], [1], f32, #nn.space<global>>) -> ()
    "kernel.matmul"(%x, %weight_t, %mat_out) {space = #nn.space<global>} : (!nn.memory<[N, IN], [IN, 1], f32, #nn.space<global>>, !nn.memory<[IN, OUT], [1, IN], f32, #nn.space<global>>, !nn.memory<[N, OUT], [OUT, 1], f32, #nn.space<global>>) -> ()
    "kernel.binary_elewise"(%mat_out, %bias_b, %out) {kind = "add", space = #nn.space<global>} : (!nn.memory<[N, OUT], [OUT, 1], f32, #nn.space<global>>, !nn.memory<[N, OUT], [OUT, 1], f32, #nn.space<global>>, !nn.memory<[N, OUT], [OUT, 1], f32, #nn.space<global>>) -> ()
    func.return
  }
}
"""

CASE_TEXT_FC_MIXED = """// COMPILE_ARGS: --pass "tile-analysis"
// CHECK: builtin.module {
// CHECK-NEXT: func.func @fc_kernel_mixed(%[[OUT:{reg}]] : !nn.memory<[6, OUT], [OUT, 1], f32, #nn.space<global>>, %[[X:{reg}]] : !nn.memory<[6, 6], [6, 1], f32, #nn.space<global>>, %[[WEIGHT:{reg}]] : !nn.memory<[OUT, 6], [6, 1], f32, #nn.space<global>>, %[[BIAS:{reg}]] : !nn.memory<[OUT], [1], f32, #nn.space<global>>, %[[OUT_DIM:{reg}]] : !symbol.int<"OUT">) {
// CHECK-NEXT: %weight_t = "dma.alloc"(%out_dim) <{operandSegmentSizes = array<i32: 1>}> : (!symbol.int<"OUT">) -> !nn.memory<[6, OUT], [1, 6], f32, #nn.space<global>>
// CHECK-NEXT: %bias_b = "dma.alloc"(%out_dim) <{operandSegmentSizes = array<i32: 1>}> : (!symbol.int<"OUT">) -> !nn.memory<[6, OUT], [OUT, 1], f32, #nn.space<global>>
// CHECK-NEXT: %mat_out = "dma.alloc"(%out_dim) <{operandSegmentSizes = array<i32: 1>}> : (!symbol.int<"OUT">) -> !nn.memory<[6, OUT], [OUT, 1], f32, #nn.space<global>>
// CHECK-NEXT: "dma.transpose"(%weight_t, %weight) {perm = [1 : i64, 0 : i64]} : (!nn.memory<[6, OUT], [1, 6], f32, #nn.space<global>>, !nn.memory<[OUT, 6], [6, 1], f32, #nn.space<global>>) -> ()
// CHECK-NEXT: "dma.broadcast"(%bias_b, %bias) {tile.analysis = \[\["elewise", "elewise"\], \["expand", "elewise"\]\], tile.tile_exprs = \[\["", ""\], \["", ""\]\]} : (!nn.memory<[6, OUT], [OUT, 1], f32, #nn.space<global>>, !nn.memory<[OUT], [1], f32, #nn.space<global>>) -> ()
// CHECK-NEXT: "kernel.matmul"(%x, %weight_t, %mat_out) {space = #nn.space<global>, tile.analysis = \[\["elewise", "reduce"\], \["reduce", "elewise"\], \["elewise", "elewise"\]\], tile.tile_exprs = \[\["", ""\], \["", ""\], \["", ""\]\]} : (!nn.memory<[6, 6], [6, 1], f32, #nn.space<global>>, !nn.memory<[6, OUT], [1, 6], f32, #nn.space<global>>, !nn.memory<[6, OUT], [OUT, 1], f32, #nn.space<global>>) -> ()
// CHECK-NEXT: "kernel.binary_elewise"(%mat_out, %bias_b, %out) {kind = "add", space = #nn.space<global>, tile.analysis = \[\["elewise", "elewise"\], \["elewise", "elewise"\], \["elewise", "elewise"\]\], tile.tile_exprs = \[\["", ""\], \["", ""\], \["", ""\]\]} : (!nn.memory<[6, OUT], [OUT, 1], f32, #nn.space<global>>, !nn.memory<[6, OUT], [OUT, 1], f32, #nn.space<global>>, !nn.memory<[6, OUT], [OUT, 1], f32, #nn.space<global>>) -> ()
// CHECK-NEXT: func.return
// CHECK-NEXT: }
// CHECK-NEXT: }
// CHECK-NOT: tuner.param
// CHECK-NOT: "symbol.get_dim"(
// CHECK-NOT: symbol.for
// CHECK-NOT: "dma.view"(

builtin.module {
  func.func @fc_kernel_mixed(%out : !nn.memory<[6, OUT], [OUT, 1], f32, #nn.space<global>>, %x : !nn.memory<[6, 6], [6, 1], f32, #nn.space<global>>, %weight : !nn.memory<[OUT, 6], [6, 1], f32, #nn.space<global>>, %bias : !nn.memory<[OUT], [1], f32, #nn.space<global>>, %out_dim : !symbol.int<"OUT">) {
    %weight_t = "dma.alloc"(%out_dim) <{operandSegmentSizes = array<i32: 1>}> : (!symbol.int<"OUT">) -> !nn.memory<[6, OUT], [1, 6], f32, #nn.space<global>>
    %bias_b = "dma.alloc"(%out_dim) <{operandSegmentSizes = array<i32: 1>}> : (!symbol.int<"OUT">) -> !nn.memory<[6, OUT], [OUT, 1], f32, #nn.space<global>>
    %mat_out = "dma.alloc"(%out_dim) <{operandSegmentSizes = array<i32: 1>}> : (!symbol.int<"OUT">) -> !nn.memory<[6, OUT], [OUT, 1], f32, #nn.space<global>>
    "dma.transpose"(%weight_t, %weight) {perm = [1 : i64, 0 : i64]} : (!nn.memory<[6, OUT], [1, 6], f32, #nn.space<global>>, !nn.memory<[OUT, 6], [6, 1], f32, #nn.space<global>>) -> ()
    "dma.broadcast"(%bias_b, %bias) : (!nn.memory<[6, OUT], [OUT, 1], f32, #nn.space<global>>, !nn.memory<[OUT], [1], f32, #nn.space<global>>) -> ()
    "kernel.matmul"(%x, %weight_t, %mat_out) {space = #nn.space<global>} : (!nn.memory<[6, 6], [6, 1], f32, #nn.space<global>>, !nn.memory<[6, OUT], [1, 6], f32, #nn.space<global>>, !nn.memory<[6, OUT], [OUT, 1], f32, #nn.space<global>>) -> ()
    "kernel.binary_elewise"(%mat_out, %bias_b, %out) {kind = "add", space = #nn.space<global>} : (!nn.memory<[6, OUT], [OUT, 1], f32, #nn.space<global>>, !nn.memory<[6, OUT], [OUT, 1], f32, #nn.space<global>>, !nn.memory<[6, OUT], [OUT, 1], f32, #nn.space<global>>) -> ()
    func.return
  }
}
"""


def _case_fc_static() -> None:
    result = run_ircheck_text(
        CASE_TEXT_FC_STATIC,
        source_path="expectation/pass/tile/analysis/fc.py:static",
    )
    assert result.ok is True, (
        f"expected ok=True, got ok={result.ok}, exit_code={result.exit_code}, message={result.message!r}"
    )
    assert result.exit_code == 0, f"expected exit_code=0, got {result.exit_code}"
    assert 'tile.analysis = [["elewise", "elewise"], ["expand", "elewise"]]' in result.actual_ir
    assert 'tile.analysis = [["elewise", "reduce"], ["reduce", "elewise"], ["elewise", "elewise"]]' in result.actual_ir
    assert 'tile.analysis = [["elewise", "elewise"], ["elewise", "elewise"], ["elewise", "elewise"]]' in result.actual_ir
    assert "tuner.param" not in result.actual_ir
    assert '"symbol.get_dim"(' not in result.actual_ir
    assert "symbol.for" not in result.actual_ir
    assert '"dma.view"(' not in result.actual_ir


def _case_fc_dynamic() -> None:
    result = run_ircheck_text(
        CASE_TEXT_FC_DYNAMIC,
        source_path="expectation/pass/tile/analysis/fc.py:dynamic",
    )
    assert result.ok is True, (
        f"expected ok=True, got ok={result.ok}, exit_code={result.exit_code}, message={result.message!r}"
    )
    assert result.exit_code == 0, f"expected exit_code=0, got {result.exit_code}"
    assert 'tile.analysis = [["elewise", "elewise"], ["expand", "elewise"]]' in result.actual_ir
    assert 'tile.analysis = [["elewise", "reduce"], ["reduce", "elewise"], ["elewise", "elewise"]]' in result.actual_ir
    assert 'tile.analysis = [["elewise", "elewise"], ["elewise", "elewise"], ["elewise", "elewise"]]' in result.actual_ir
    assert "tuner.param" not in result.actual_ir
    assert '"symbol.get_dim"(' not in result.actual_ir
    assert "symbol.for" not in result.actual_ir
    assert '"dma.view"(' not in result.actual_ir


def _case_fc_mixed() -> None:
    result = run_ircheck_text(
        CASE_TEXT_FC_MIXED,
        source_path="expectation/pass/tile/analysis/fc.py:mixed",
    )
    assert result.ok is True, (
        f"expected ok=True, got ok={result.ok}, exit_code={result.exit_code}, message={result.message!r}"
    )
    assert result.exit_code == 0, f"expected exit_code=0, got {result.exit_code}"
    assert 'tile.analysis = [["elewise", "elewise"], ["expand", "elewise"]]' in result.actual_ir
    assert 'tile.analysis = [["elewise", "reduce"], ["reduce", "elewise"], ["elewise", "elewise"]]' in result.actual_ir
    assert 'tile.analysis = [["elewise", "elewise"], ["elewise", "elewise"], ["elewise", "elewise"]]' in result.actual_ir
    assert "tuner.param" not in result.actual_ir
    assert '"symbol.get_dim"(' not in result.actual_ir
    assert "symbol.for" not in result.actual_ir
    assert '"dma.view"(' not in result.actual_ir


def main() -> None:
    failures: list[tuple[str, BaseException]] = []
    run_case(failures, "CASE-fc-static", _case_fc_static)
    run_case(failures, "CASE-fc-dynamic", _case_fc_dynamic)
    run_case(failures, "CASE-fc-mixed", _case_fc_mixed)
    raise_if_failures("tile analysis fc expectation", failures)


if __name__ == "__main__":
    main()
