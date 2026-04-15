"""symbol.for expectation.

创建者: 榕
最后一次更改: 守护最好的爱莉希雅

功能说明:
- 演示 `dsl/mlir_gen` expectation 如何直接使用 `mlir_gen_compare_text(...)` 比较完整 `builtin.module`。
- 锁定 `LoopRange(...)` 的目标公开合同：常量边界与 symbol 边界都应生成带 `#symbol.iter<...>` 属性的 `symbol.for`，并让 DMA offset 直接复用 `!symbol.iter<...>` 迭代变量。

使用示例:
- `PYTHONPATH=. python expectation/dsl/mlir_gen/dialect/symbol/for_loop.py`

关联文件:
- spec: [`spec/dialect/symbol.md`](spec/dialect/symbol.md)
- spec: [`spec/dsl/mlir_gen.md`](spec/dsl/mlir_gen.md)
- spec: [`spec/tools/mlir_gen_compare.md`](spec/tools/mlir_gen_compare.md)
- test: [`test/dsl/test_mlir_gen.py`](test/dsl/test_mlir_gen.py)
- test: [`test/tools/test_mlir_gen_compare.py`](test/tools/test_mlir_gen_compare.py)
- 功能实现: [`kernel_gen/dsl/mlir_gen.py`](kernel_gen/dsl/mlir_gen.py)
- 功能实现: [`kernel_gen/tools/mlir_gen_compare.py`](kernel_gen/tools/mlir_gen_compare.py)
"""

# Case 列表:
# - CASE-1: const 正向例子：`LoopRange(0, 8, 2)` 应生成带 `#symbol.iter<...>` 的 `symbol.for` 并保留 DMA/nn 链路。
# - CASE-2: symbol 正向例子：`LoopRange(start, end, step)` 应生成带 `#symbol.iter<...>` 的 `symbol.for` 并保留 DMA/nn 链路。
# - CASE-3: 失败例子：`LoopRange(0, 8, 0)` 的 step 为 0 时应在前端 lowering 阶段拒绝。

from pathlib import Path
import sys

CURRENT_DIR = Path(__file__).resolve().parent
if str(CURRENT_DIR) in sys.path:
    sys.path.remove(str(CURRENT_DIR))

REPO_ROOT = Path(__file__).resolve().parents[5]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from expectation.utils.case_runner import raise_if_failures, run_case
from kernel_gen.dsl.ast_visitor import AstVisitorError
from kernel_gen.operation.dma import deslice, slice
from kernel_gen.operation.scf import LoopRange
from kernel_gen.symbol_variable.memory import Memory
from kernel_gen.symbol_variable.symbol_dim import SymbolDim
from kernel_gen.symbol_variable.type import NumericType
from kernel_gen.tools.mlir_gen_compare import mlir_gen_compare_text

# CASE-1 IR：const 正向例子：`LoopRange(0, 8, 2)` 应生成带 `#symbol.iter<...>` 的 `symbol.for` 并保留 DMA/nn 链路。
CASE_1_IR = """builtin.module {
  func.func @for_loop_case_1(%0 : !nn.memory<[8], [1], f32, #nn.space<global>>, %1 : !nn.memory<[8], [1], f32, #nn.space<global>>, %2 : !nn.memory<[8], [1], f32, #nn.space<global>>) {
    %3 = symbol.const 0 : !symbol.int<"0">
    %4 = symbol.const 8 : !symbol.int<"8">
    %5 = symbol.const 2 : !symbol.int<"2">
    symbol.for %6 = %3 to %4 step %5 {iter = #symbol.iter<start = "0", end = "8", step = "2">} {
      %7 = symbol.const 2 : !symbol.int<"2">
      %8 = symbol.const 1 : !symbol.int<"1">
      %9 = "dma.alloc"() <{operandSegmentSizes = array<i32: 0>}> : () -> !nn.memory<[2], [1], f32, #nn.space<global>>
      "dma.slice"(%9, %0, %6, %7, %8) <{operandSegmentSizes = array<i32: 1, 1, 1, 1, 1>}> : (!nn.memory<[2], [1], f32, #nn.space<global>>, !nn.memory<[8], [1], f32, #nn.space<global>>, !symbol.iter<start = "0", end = "8", step = "2">, !symbol.int<"2">, !symbol.int<"1">) -> ()
      %10 = symbol.const 2 : !symbol.int<"2">
      %11 = symbol.const 1 : !symbol.int<"1">
      %12 = "dma.alloc"() <{operandSegmentSizes = array<i32: 0>}> : () -> !nn.memory<[2], [1], f32, #nn.space<global>>
      "dma.slice"(%12, %1, %6, %10, %11) <{operandSegmentSizes = array<i32: 1, 1, 1, 1, 1>}> : (!nn.memory<[2], [1], f32, #nn.space<global>>, !nn.memory<[8], [1], f32, #nn.space<global>>, !symbol.iter<start = "0", end = "8", step = "2">, !symbol.int<"2">, !symbol.int<"1">) -> ()
      %13 = "nn.add"(%9, %12) {space = #nn.space<global>} : (!nn.memory<[2], [1], f32, #nn.space<global>>, !nn.memory<[2], [1], f32, #nn.space<global>>) -> !nn.memory<[2], [1], f32, #nn.space<global>>
      %14 = symbol.const 2 : !symbol.int<"2">
      %15 = symbol.const 1 : !symbol.int<"1">
      %16 = "dma.deslice"(%13, %2, %6, %14, %15) <{operandSegmentSizes = array<i32: 1, 1, 1, 1, 1>}> : (!nn.memory<[2], [1], f32, #nn.space<global>>, !nn.memory<[8], [1], f32, #nn.space<global>>, !symbol.iter<start = "0", end = "8", step = "2">, !symbol.int<"2">, !symbol.int<"1">) -> !nn.memory<[8], [1], f32, #nn.space<global>>
    }
    func.return
  }
}"""

CASE_1_RUNTIME_ARGS = (
    Memory([8], NumericType.Float32),
    Memory([8], NumericType.Float32),
    Memory([8], NumericType.Float32),
)

def for_loop_case_1(a, b, c):
    for index in LoopRange(0, 8, 2):
        slice_a = slice(a, [index], [2], [1])
        slice_b = slice(b, [index], [2], [1])
        slice_c = slice_a + slice_b
        deslice(slice_c, c, [index], [2], [1])

# CASE-2 IR：symbol 正向例子：`LoopRange(start, end, step)` 应生成带 `#symbol.iter<...>` 的 `symbol.for`，循环变量直接保持 `!symbol.iter<...>`。
CASE_2_IR = """builtin.module {
  func.func @for_loop_case_2(%0 : !nn.memory<[DIM], [1], f32, #nn.space<global>>, %1 : !nn.memory<[DIM], [1], f32, #nn.space<global>>, %2 : !nn.memory<[DIM], [1], f32, #nn.space<global>>, %3 : !symbol.int<"START">, %4 : !symbol.int<"END">, %5 : !symbol.int<"STEP">) {
    symbol.for %6 = %3 to %4 step %5 {iter = #symbol.iter<start = "START", end = "END", step = "STEP">} {
      %7 = symbol.const 1 : !symbol.int<"1">
      %8 = "dma.alloc"(%5) <{operandSegmentSizes = array<i32: 1>}> : (!symbol.int<"STEP">) -> !nn.memory<[STEP], [1], f32, #nn.space<global>>
      "dma.slice"(%8, %0, %6, %5, %7) <{operandSegmentSizes = array<i32: 1, 1, 1, 1, 1>}> : (!nn.memory<[STEP], [1], f32, #nn.space<global>>, !nn.memory<[DIM], [1], f32, #nn.space<global>>, !symbol.iter<start = "START", end = "END", step = "STEP">, !symbol.int<"STEP">, !symbol.int<"1">) -> ()
      %9 = symbol.const 1 : !symbol.int<"1">
      %10 = "dma.alloc"(%5) <{operandSegmentSizes = array<i32: 1>}> : (!symbol.int<"STEP">) -> !nn.memory<[STEP], [1], f32, #nn.space<global>>
      "dma.slice"(%10, %1, %6, %5, %9) <{operandSegmentSizes = array<i32: 1, 1, 1, 1, 1>}> : (!nn.memory<[STEP], [1], f32, #nn.space<global>>, !nn.memory<[DIM], [1], f32, #nn.space<global>>, !symbol.iter<start = "START", end = "END", step = "STEP">, !symbol.int<"STEP">, !symbol.int<"1">) -> ()
      %11 = "nn.add"(%8, %10) {space = #nn.space<global>} : (!nn.memory<[STEP], [1], f32, #nn.space<global>>, !nn.memory<[STEP], [1], f32, #nn.space<global>>) -> !nn.memory<[STEP], [1], f32, #nn.space<global>>
      %12 = symbol.const 1 : !symbol.int<"1">
      %13 = "dma.deslice"(%11, %2, %6, %5, %12) <{operandSegmentSizes = array<i32: 1, 1, 1, 1, 1>}> : (!nn.memory<[STEP], [1], f32, #nn.space<global>>, !nn.memory<[DIM], [1], f32, #nn.space<global>>, !symbol.iter<start = "START", end = "END", step = "STEP">, !symbol.int<"STEP">, !symbol.int<"1">) -> !nn.memory<[DIM], [1], f32, #nn.space<global>>
    }
    func.return
  }
}"""

CASE_2_RUNTIME_ARGS = (
    Memory([SymbolDim("DIM")], NumericType.Float32),
    Memory([SymbolDim("DIM")], NumericType.Float32),
    Memory([SymbolDim("DIM")], NumericType.Float32),
    SymbolDim("START"),
    SymbolDim("END"),
    SymbolDim("STEP"),
)

def for_loop_case_2(a, b, c, start, end, step):
    for index in LoopRange(start, end, step):
        slice_a = slice(a, [index], [step], [1])
        slice_b = slice(b, [index], [step], [1])
        slice_c = slice_a + slice_b
        deslice(slice_c, c, [index], [step], [1])


# CASE-3 描述：失败例子：`LoopRange(0, 8, 0)` 的 step 为 0 时应在构造阶段拒绝。
CASE_3_RUNTIME_ARGS = (
    Memory([8], NumericType.Float32),
    Memory([8], NumericType.Float32),
    Memory([8], NumericType.Float32),
)

def for_loop_case_3(a, b, c):
    for index in LoopRange(0, 8, 0):
        slice_a = slice(a, [index], [2], [1])
        slice_b = slice(b, [index], [2], [1])
        slice_c = slice_a + slice_b
        deslice(slice_c, c, [index], [2], [1])


def _case_1_true():
    print("[CASE-1] const 正向例子：LoopRange(0, 8, 2) -> symbol.for")
    ok = mlir_gen_compare_text(fn=for_loop_case_1, runtime_args=CASE_1_RUNTIME_ARGS, config=None, mlir_text=CASE_1_IR)
    assert ok is True, "expected mlir_gen_compare_text(...) to return True for const for-loop module text"


def _case_2_true():
    print("[CASE-2] symbol 正向例子：LoopRange(start, end, step) -> symbol.for")
    ok = mlir_gen_compare_text(fn=for_loop_case_2, runtime_args=CASE_2_RUNTIME_ARGS, config=None, mlir_text=CASE_2_IR)
    assert ok is True, "expected mlir_gen_compare_text(...) to return True for symbol for-loop module text"


def _case_3_reject_zero_step():
    print("[CASE-3] 失败例子：LoopRange(0, 8, 0) 的 step 为 0 时应在前端 lowering 阶段拒绝")
    try:
        mlir_gen_compare_text(fn=for_loop_case_3, runtime_args=CASE_3_RUNTIME_ARGS, config=None, mlir_text=CASE_1_IR)
    except AstVisitorError as exc:
        assert "for range step must not be zero" in str(exc)
    else:
        raise AssertionError("LoopRange with zero step should be rejected during MLIR lowering")


def main():
    failures: list[tuple[str, BaseException]] = []
    run_case(failures, "CASE-1", _case_1_true)
    run_case(failures, "CASE-2", _case_2_true)
    run_case(failures, "CASE-3", _case_3_reject_zero_step)
    raise_if_failures("dsl mlir_gen symbol.for expectation", failures)


if __name__ == "__main__":
    main()
