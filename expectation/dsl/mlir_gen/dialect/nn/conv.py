"""DSL nn.conv expectation.

创建者: 大闸蟹
最后一次更改: 守护最好的爱莉希雅

功能说明:
- 演示 `dsl/mlir_gen` expectation 如何直接使用 `mlir_gen_compare_text(...)` 比较完整 `builtin.module`。
- 锁定 `conv(value, weight, ...)` 的目标公开合同：应生成 `nn.img2col2d + dma.reshape + nn.matmul + dma.reshape` 链路。

使用示例:
- `PYTHONPATH=. python expectation/dsl/mlir_gen/dialect/nn/conv.py`

关联文件:
- spec: [`spec/dsl/mlir_gen.md`](spec/dsl/mlir_gen.md)
- spec: [`spec/dialect/nn.md`](spec/dialect/nn.md)
- spec: [`spec/operation/nn.md`](spec/operation/nn.md)
- spec: [`spec/tools/mlir_gen_compare.md`](spec/tools/mlir_gen_compare.md)
- test: [`test/dsl/test_mlir_gen.py`](test/dsl/test_mlir_gen.py)
- test: [`test/tools/test_mlir_gen_compare.py`](test/tools/test_mlir_gen_compare.py)
- 功能实现: [`kernel_gen/dsl/mlir_gen.py`](kernel_gen/dsl/mlir_gen.py)
- 功能实现: [`kernel_gen/tools/mlir_gen_compare.py`](kernel_gen/tools/mlir_gen_compare.py)
"""

# Case 列表:
# - CASE-1: 静态正向例子：`conv(value, weight, ...)` 的静态输入应生成完整 lowering 链路。
# - CASE-2: 动态正向例子：`conv(value, weight, ...)` 的 symbol shape 输入应生成完整 lowering 链路并保留 symbol 表达式。
# - CASE-3: 静态正向例子：`kh=1/pad=0` 的静态输入应生成完整 lowering 链路。
# - CASE-4: 静态正向例子：`kh=5/pad=2` 的静态输入应生成完整 lowering 链路。
# - CASE-5: 失败例子：`format=CLast` 的输入不属于当前 conv 的 NCHW 公开合同，应在构造阶段拒绝。
# - CASE-6: 动态正向例子：`kh/pad` 为 symbol 输入时应生成完整 lowering 链路并保留 symbol 表达式。
# - CASE-7: 失败例子：`conv(value, weight, ...)` 的输入通道与权重通道不匹配时应在构造阶段拒绝。

from __future__ import annotations

from pathlib import Path
import sys

CURRENT_DIR = Path(__file__).resolve().parent
if str(CURRENT_DIR) in sys.path:
    sys.path.remove(str(CURRENT_DIR))

REPO_ROOT = Path(__file__).resolve().parents[5]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from expectation.utils.case_runner import raise_if_failures, run_case
from kernel_gen.operation.nn import conv
from kernel_gen.symbol_variable.memory import Memory, MemorySpace
from kernel_gen.symbol_variable.symbol_dim import SymbolDim
from kernel_gen.symbol_variable.type import Farmat, NumericType
from kernel_gen.tools.mlir_gen_compare import mlir_gen_compare_text

# CASE-1 IR：静态正向例子：`conv(value, weight, ...)` 的静态输入应生成完整 lowering 链路。
CASE_1_IR = """builtin.module {
  func.func @conv_kernel_case_1(%0 : !nn.memory<[1, 3, 5, 5], [75, 25, 5, 1], f32, #nn.space<global>>, %1 : !nn.memory<[8, 3, 3, 3], [27, 9, 3, 1], f32, #nn.space<global>>) -> !nn.memory<[1, 8, 5, 5], [200, 25, 5, 1], f32, #nn.space<global>> {
    %2 = symbol.const 3 : !symbol.int<"3">
    %3 = symbol.const 3 : !symbol.int<"3">
    %4 = symbol.const 1 : !symbol.int<"1">
    %5 = symbol.const 1 : !symbol.int<"1">
    %6 = symbol.const 1 : !symbol.int<"1">
    %7 = symbol.const 1 : !symbol.int<"1">
    %8 = symbol.const 1 : !symbol.int<"1">
    %9 = symbol.const 1 : !symbol.int<"1">
    %10 = symbol.const 1 : !symbol.int<"1">
    %11 = symbol.const 1 : !symbol.int<"1">
    %12 = "nn.img2col2d"(%0, %2, %3, %4, %5, %6, %7, %8, %9, %10, %11) {space = #nn.space<global>} : (!nn.memory<[1, 3, 5, 5], [75, 25, 5, 1], f32, #nn.space<global>>, !symbol.int<"3">, !symbol.int<"3">, !symbol.int<"1">, !symbol.int<"1">, !symbol.int<"1">, !symbol.int<"1">, !symbol.int<"1">, !symbol.int<"1">, !symbol.int<"1">, !symbol.int<"1">) -> !nn.memory<[1, 3, 3, 3, 5, 5], [675, 225, 75, 25, 5, 1], f32, #nn.space<global>>
    %13 = "symbol.get_dim"(%12) {axis = #builtin.int<0>} : (!nn.memory<[1, 3, 3, 3, 5, 5], [675, 225, 75, 25, 5, 1], f32, #nn.space<global>>) -> !symbol.int<"1">
    %14 = "symbol.get_dim"(%12) {axis = #builtin.int<4>} : (!nn.memory<[1, 3, 3, 3, 5, 5], [675, 225, 75, 25, 5, 1], f32, #nn.space<global>>) -> !symbol.int<"5">
    %15 = "symbol.get_dim"(%12) {axis = #builtin.int<5>} : (!nn.memory<[1, 3, 3, 3, 5, 5], [675, 225, 75, 25, 5, 1], f32, #nn.space<global>>) -> !symbol.int<"5">
    %16 = symbol.const 8 : !symbol.int<"8">
    %17 = symbol.const 27 : !symbol.int<"27">
    %18 = "dma.reshape"(%1, %16, %17) <{operandSegmentSizes = array<i32: 1, 2>}> : (!nn.memory<[8, 3, 3, 3], [27, 9, 3, 1], f32, #nn.space<global>>, !symbol.int<"8">, !symbol.int<"27">) -> !nn.memory<[8, 27], [27, 1], f32, #nn.space<global>>
    %19 = symbol.const 27 : !symbol.int<"27">
    %23 = symbol.mul %13, %14 : !symbol.int<"1">, !symbol.int<"5"> -> !symbol.int<"5">
    %24 = symbol.mul %23, %15 : !symbol.int<"5">, !symbol.int<"5"> -> !symbol.int<"25">
    %25 = "dma.reshape"(%12, %19, %24) <{operandSegmentSizes = array<i32: 1, 2>}> : (!nn.memory<[1, 3, 3, 3, 5, 5], [675, 225, 75, 25, 5, 1], f32, #nn.space<global>>, !symbol.int<"27">, !symbol.int<"25">) -> !nn.memory<[27, 25], [25, 1], f32, #nn.space<global>>
    %26 = "nn.matmul"(%18, %25) {space = #nn.space<global>} : (!nn.memory<[8, 27], [27, 1], f32, #nn.space<global>>, !nn.memory<[27, 25], [25, 1], f32, #nn.space<global>>) -> !nn.memory<[8, 25], [25, 1], f32, #nn.space<global>>
    %27 = symbol.const 8 : !symbol.int<"8">
    %28 = "dma.reshape"(%26, %13, %27, %14, %15) <{operandSegmentSizes = array<i32: 1, 4>}> : (!nn.memory<[8, 25], [25, 1], f32, #nn.space<global>>, !symbol.int<"1">, !symbol.int<"8">, !symbol.int<"5">, !symbol.int<"5">) -> !nn.memory<[1, 8, 5, 5], [200, 25, 5, 1], f32, #nn.space<global>>
    func.return %28 : !nn.memory<[1, 8, 5, 5], [200, 25, 5, 1], f32, #nn.space<global>>
  }
}"""

CASE_1_RUNTIME_ARGS = (
    Memory([1, 3, 5, 5], NumericType.Float32, space=MemorySpace.GM),
    Memory([8, 3, 3, 3], NumericType.Float32, space=MemorySpace.GM),
)

def conv_kernel_case_1(value, weight):
    return conv(value, weight, sh=1, sw=1, dh=1, dw=1, ph=1, pw=1, pl=1, pr=1)

# CASE-2 IR：动态正向例子：`conv(value, weight, ...)` 的 symbol shape 输入应生成完整 lowering 链路并保留 symbol 表达式。
CASE_2_IR = """builtin.module {
  func.func @conv_kernel_case_2(%0 : !nn.memory<[B, 3, H, W], [3*H*W, H*W, W, 1], f32, #nn.space<global>>, %1 : !nn.memory<[8, 3, 3, 3], [27, 9, 3, 1], f32, #nn.space<global>>) -> !nn.memory<[B, 8, (H - 1)/1 + 1, (W - 1)/1 + 1], [8*((H - 1)/1 + 1)*((W - 1)/1 + 1), ((H - 1)/1 + 1)*((W - 1)/1 + 1), (W - 1)/1 + 1, 1], f32, #nn.space<global>> {
    %2 = symbol.const 3 : !symbol.int<"3">
    %3 = symbol.const 3 : !symbol.int<"3">
    %4 = symbol.const 1 : !symbol.int<"1">
    %5 = symbol.const 1 : !symbol.int<"1">
    %6 = symbol.const 1 : !symbol.int<"1">
    %7 = symbol.const 1 : !symbol.int<"1">
    %8 = symbol.const 1 : !symbol.int<"1">
    %9 = symbol.const 1 : !symbol.int<"1">
    %10 = symbol.const 1 : !symbol.int<"1">
    %11 = symbol.const 1 : !symbol.int<"1">
    %12 = "nn.img2col2d"(%0, %2, %3, %4, %5, %6, %7, %8, %9, %10, %11) {space = #nn.space<global>} : (!nn.memory<[B, 3, H, W], [3*H*W, H*W, W, 1], f32, #nn.space<global>>, !symbol.int<"3">, !symbol.int<"3">, !symbol.int<"1">, !symbol.int<"1">, !symbol.int<"1">, !symbol.int<"1">, !symbol.int<"1">, !symbol.int<"1">, !symbol.int<"1">, !symbol.int<"1">) -> !nn.memory<[B, 3, 3, 3, (H - 1)/1 + 1, (W - 1)/1 + 1], [27*((H - 1)/1 + 1)*((W - 1)/1 + 1), 9*((H - 1)/1 + 1)*((W - 1)/1 + 1), 3*((H - 1)/1 + 1)*((W - 1)/1 + 1), ((H - 1)/1 + 1)*((W - 1)/1 + 1), (W - 1)/1 + 1, 1], f32, #nn.space<global>>
    %13 = "symbol.get_dim"(%12) {axis = #builtin.int<0>} : (!nn.memory<[B, 3, 3, 3, (H - 1)/1 + 1, (W - 1)/1 + 1], [27*((H - 1)/1 + 1)*((W - 1)/1 + 1), 9*((H - 1)/1 + 1)*((W - 1)/1 + 1), 3*((H - 1)/1 + 1)*((W - 1)/1 + 1), ((H - 1)/1 + 1)*((W - 1)/1 + 1), (W - 1)/1 + 1, 1], f32, #nn.space<global>>) -> !symbol.int<"B">
    %14 = "symbol.get_dim"(%12) {axis = #builtin.int<4>} : (!nn.memory<[B, 3, 3, 3, (H - 1)/1 + 1, (W - 1)/1 + 1], [27*((H - 1)/1 + 1)*((W - 1)/1 + 1), 9*((H - 1)/1 + 1)*((W - 1)/1 + 1), 3*((H - 1)/1 + 1)*((W - 1)/1 + 1), ((H - 1)/1 + 1)*((W - 1)/1 + 1), (W - 1)/1 + 1, 1], f32, #nn.space<global>>) -> !symbol.int<"(H - 1)/1 + 1">
    %15 = "symbol.get_dim"(%12) {axis = #builtin.int<5>} : (!nn.memory<[B, 3, 3, 3, (H - 1)/1 + 1, (W - 1)/1 + 1], [27*((H - 1)/1 + 1)*((W - 1)/1 + 1), 9*((H - 1)/1 + 1)*((W - 1)/1 + 1), 3*((H - 1)/1 + 1)*((W - 1)/1 + 1), ((H - 1)/1 + 1)*((W - 1)/1 + 1), (W - 1)/1 + 1, 1], f32, #nn.space<global>>) -> !symbol.int<"(W - 1)/1 + 1">
    %16 = symbol.const 8 : !symbol.int<"8">
    %17 = symbol.const 27 : !symbol.int<"27">
    %18 = "dma.reshape"(%1, %16, %17) <{operandSegmentSizes = array<i32: 1, 2>}> : (!nn.memory<[8, 3, 3, 3], [27, 9, 3, 1], f32, #nn.space<global>>, !symbol.int<"8">, !symbol.int<"27">) -> !nn.memory<[8, 27], [27, 1], f32, #nn.space<global>>
    %19 = symbol.const 27 : !symbol.int<"27">
    %23 = symbol.mul %13, %14 : !symbol.int<"B">, !symbol.int<"(H - 1)/1 + 1"> -> !symbol.int<"B*((H - 1)/1 + 1)">
    %24 = symbol.mul %23, %15 : !symbol.int<"B*((H - 1)/1 + 1)">, !symbol.int<"(W - 1)/1 + 1"> -> !symbol.int<"B*((H - 1)/1 + 1)*((W - 1)/1 + 1)">
    %25 = "dma.reshape"(%12, %19, %24) <{operandSegmentSizes = array<i32: 1, 2>}> : (!nn.memory<[B, 3, 3, 3, (H - 1)/1 + 1, (W - 1)/1 + 1], [27*((H - 1)/1 + 1)*((W - 1)/1 + 1), 9*((H - 1)/1 + 1)*((W - 1)/1 + 1), 3*((H - 1)/1 + 1)*((W - 1)/1 + 1), ((H - 1)/1 + 1)*((W - 1)/1 + 1), (W - 1)/1 + 1, 1], f32, #nn.space<global>>, !symbol.int<"27">, !symbol.int<"B*((H - 1)/1 + 1)*((W - 1)/1 + 1)">) -> !nn.memory<[27, B*((H - 1)/1 + 1)*((W - 1)/1 + 1)], [B*((H - 1)/1 + 1)*((W - 1)/1 + 1), 1], f32, #nn.space<global>>
    %26 = "nn.matmul"(%18, %25) {space = #nn.space<global>} : (!nn.memory<[8, 27], [27, 1], f32, #nn.space<global>>, !nn.memory<[27, B*((H - 1)/1 + 1)*((W - 1)/1 + 1)], [B*((H - 1)/1 + 1)*((W - 1)/1 + 1), 1], f32, #nn.space<global>>) -> !nn.memory<[8, B*((H - 1)/1 + 1)*((W - 1)/1 + 1)], [B*((H - 1)/1 + 1)*((W - 1)/1 + 1), 1], f32, #nn.space<global>>
    %27 = symbol.const 8 : !symbol.int<"8">
    %28 = "dma.reshape"(%26, %13, %27, %14, %15) <{operandSegmentSizes = array<i32: 1, 4>}> : (!nn.memory<[8, B*((H - 1)/1 + 1)*((W - 1)/1 + 1)], [B*((H - 1)/1 + 1)*((W - 1)/1 + 1), 1], f32, #nn.space<global>>, !symbol.int<"B">, !symbol.int<"8">, !symbol.int<"(H - 1)/1 + 1">, !symbol.int<"(W - 1)/1 + 1">) -> !nn.memory<[B, 8, (H - 1)/1 + 1, (W - 1)/1 + 1], [8*((H - 1)/1 + 1)*((W - 1)/1 + 1), ((H - 1)/1 + 1)*((W - 1)/1 + 1), (W - 1)/1 + 1, 1], f32, #nn.space<global>>
    func.return %28 : !nn.memory<[B, 8, (H - 1)/1 + 1, (W - 1)/1 + 1], [8*((H - 1)/1 + 1)*((W - 1)/1 + 1), ((H - 1)/1 + 1)*((W - 1)/1 + 1), (W - 1)/1 + 1, 1], f32, #nn.space<global>>
  }
}"""

CASE_2_RUNTIME_ARGS = (
    Memory([SymbolDim("B"), 3, SymbolDim("H"), SymbolDim("W")], NumericType.Float32, space=MemorySpace.GM),
    Memory([8, 3, 3, 3], NumericType.Float32, space=MemorySpace.GM),
)

def conv_kernel_case_2(value, weight):
    return conv(value, weight, sh=1, sw=1, dh=1, dw=1, ph=1, pw=1, pl=1, pr=1)

# CASE-3 IR：静态正向例子：`kh=1/pad=0` 的静态输入应生成完整 lowering 链路。
CASE_3_IR = """builtin.module {
  func.func @conv_kernel_case_3(%0 : !nn.memory<[1, 3, 4, 4], [48, 16, 4, 1], f32, #nn.space<global>>, %1 : !nn.memory<[2, 3, 1, 1], [3, 1, 1, 1], f32, #nn.space<global>>) -> !nn.memory<[1, 2, 4, 4], [32, 16, 4, 1], f32, #nn.space<global>> {
    %2 = symbol.const 1 : !symbol.int<"1">
    %3 = symbol.const 1 : !symbol.int<"1">
    %4 = symbol.const 1 : !symbol.int<"1">
    %5 = symbol.const 1 : !symbol.int<"1">
    %6 = symbol.const 1 : !symbol.int<"1">
    %7 = symbol.const 1 : !symbol.int<"1">
    %8 = symbol.const 0 : !symbol.int<"0">
    %9 = symbol.const 0 : !symbol.int<"0">
    %10 = symbol.const 0 : !symbol.int<"0">
    %11 = symbol.const 0 : !symbol.int<"0">
    %12 = "nn.img2col2d"(%0, %2, %3, %4, %5, %6, %7, %8, %9, %10, %11) {space = #nn.space<global>} : (!nn.memory<[1, 3, 4, 4], [48, 16, 4, 1], f32, #nn.space<global>>, !symbol.int<"1">, !symbol.int<"1">, !symbol.int<"1">, !symbol.int<"1">, !symbol.int<"1">, !symbol.int<"1">, !symbol.int<"0">, !symbol.int<"0">, !symbol.int<"0">, !symbol.int<"0">) -> !nn.memory<[1, 3, 1, 1, 4, 4], [48, 16, 16, 16, 4, 1], f32, #nn.space<global>>
    %13 = "symbol.get_dim"(%12) {axis = #builtin.int<0>} : (!nn.memory<[1, 3, 1, 1, 4, 4], [48, 16, 16, 16, 4, 1], f32, #nn.space<global>>) -> !symbol.int<"1">
    %14 = "symbol.get_dim"(%12) {axis = #builtin.int<4>} : (!nn.memory<[1, 3, 1, 1, 4, 4], [48, 16, 16, 16, 4, 1], f32, #nn.space<global>>) -> !symbol.int<"4">
    %15 = "symbol.get_dim"(%12) {axis = #builtin.int<5>} : (!nn.memory<[1, 3, 1, 1, 4, 4], [48, 16, 16, 16, 4, 1], f32, #nn.space<global>>) -> !symbol.int<"4">
    %16 = symbol.const 2 : !symbol.int<"2">
    %17 = symbol.const 3 : !symbol.int<"3">
    %18 = "dma.reshape"(%1, %16, %17) <{operandSegmentSizes = array<i32: 1, 2>}> : (!nn.memory<[2, 3, 1, 1], [3, 1, 1, 1], f32, #nn.space<global>>, !symbol.int<"2">, !symbol.int<"3">) -> !nn.memory<[2, 3], [3, 1], f32, #nn.space<global>>
    %19 = symbol.const 3 : !symbol.int<"3">
    %23 = symbol.mul %13, %14 : !symbol.int<"1">, !symbol.int<"4"> -> !symbol.int<"4">
    %24 = symbol.mul %23, %15 : !symbol.int<"4">, !symbol.int<"4"> -> !symbol.int<"16">
    %25 = "dma.reshape"(%12, %19, %24) <{operandSegmentSizes = array<i32: 1, 2>}> : (!nn.memory<[1, 3, 1, 1, 4, 4], [48, 16, 16, 16, 4, 1], f32, #nn.space<global>>, !symbol.int<"3">, !symbol.int<"16">) -> !nn.memory<[3, 16], [16, 1], f32, #nn.space<global>>
    %26 = "nn.matmul"(%18, %25) {space = #nn.space<global>} : (!nn.memory<[2, 3], [3, 1], f32, #nn.space<global>>, !nn.memory<[3, 16], [16, 1], f32, #nn.space<global>>) -> !nn.memory<[2, 16], [16, 1], f32, #nn.space<global>>
    %27 = symbol.const 2 : !symbol.int<"2">
    %28 = "dma.reshape"(%26, %13, %27, %14, %15) <{operandSegmentSizes = array<i32: 1, 4>}> : (!nn.memory<[2, 16], [16, 1], f32, #nn.space<global>>, !symbol.int<"1">, !symbol.int<"2">, !symbol.int<"4">, !symbol.int<"4">) -> !nn.memory<[1, 2, 4, 4], [32, 16, 4, 1], f32, #nn.space<global>>
    func.return %28 : !nn.memory<[1, 2, 4, 4], [32, 16, 4, 1], f32, #nn.space<global>>
  }
}"""

CASE_3_RUNTIME_ARGS = (
    Memory([1, 3, 4, 4], NumericType.Float32, space=MemorySpace.GM),
    Memory([2, 3, 1, 1], NumericType.Float32, space=MemorySpace.GM),
)

def conv_kernel_case_3(value, weight):
    return conv(value, weight, sh=1, sw=1, dh=1, dw=1, ph=0, pw=0, pl=0, pr=0)

# CASE-4 IR：静态正向例子：`kh=5/pad=2` 的静态输入应生成完整 lowering 链路。
CASE_4_IR = """builtin.module {
  func.func @conv_kernel_case_4(%0 : !nn.memory<[1, 3, 5, 5], [75, 25, 5, 1], f32, #nn.space<global>>, %1 : !nn.memory<[4, 3, 5, 5], [75, 25, 5, 1], f32, #nn.space<global>>) -> !nn.memory<[1, 4, 5, 5], [100, 25, 5, 1], f32, #nn.space<global>> {
    %2 = symbol.const 5 : !symbol.int<"5">
    %3 = symbol.const 5 : !symbol.int<"5">
    %4 = symbol.const 1 : !symbol.int<"1">
    %5 = symbol.const 1 : !symbol.int<"1">
    %6 = symbol.const 1 : !symbol.int<"1">
    %7 = symbol.const 1 : !symbol.int<"1">
    %8 = symbol.const 2 : !symbol.int<"2">
    %9 = symbol.const 2 : !symbol.int<"2">
    %10 = symbol.const 2 : !symbol.int<"2">
    %11 = symbol.const 2 : !symbol.int<"2">
    %12 = "nn.img2col2d"(%0, %2, %3, %4, %5, %6, %7, %8, %9, %10, %11) {space = #nn.space<global>} : (!nn.memory<[1, 3, 5, 5], [75, 25, 5, 1], f32, #nn.space<global>>, !symbol.int<"5">, !symbol.int<"5">, !symbol.int<"1">, !symbol.int<"1">, !symbol.int<"1">, !symbol.int<"1">, !symbol.int<"2">, !symbol.int<"2">, !symbol.int<"2">, !symbol.int<"2">) -> !nn.memory<[1, 3, 5, 5, 5, 5], [1875, 625, 125, 25, 5, 1], f32, #nn.space<global>>
    %13 = "symbol.get_dim"(%12) {axis = #builtin.int<0>} : (!nn.memory<[1, 3, 5, 5, 5, 5], [1875, 625, 125, 25, 5, 1], f32, #nn.space<global>>) -> !symbol.int<"1">
    %14 = "symbol.get_dim"(%12) {axis = #builtin.int<4>} : (!nn.memory<[1, 3, 5, 5, 5, 5], [1875, 625, 125, 25, 5, 1], f32, #nn.space<global>>) -> !symbol.int<"5">
    %15 = "symbol.get_dim"(%12) {axis = #builtin.int<5>} : (!nn.memory<[1, 3, 5, 5, 5, 5], [1875, 625, 125, 25, 5, 1], f32, #nn.space<global>>) -> !symbol.int<"5">
    %16 = symbol.const 4 : !symbol.int<"4">
    %17 = symbol.const 75 : !symbol.int<"75">
    %18 = "dma.reshape"(%1, %16, %17) <{operandSegmentSizes = array<i32: 1, 2>}> : (!nn.memory<[4, 3, 5, 5], [75, 25, 5, 1], f32, #nn.space<global>>, !symbol.int<"4">, !symbol.int<"75">) -> !nn.memory<[4, 75], [75, 1], f32, #nn.space<global>>
    %19 = symbol.const 75 : !symbol.int<"75">
    %23 = symbol.mul %13, %14 : !symbol.int<"1">, !symbol.int<"5"> -> !symbol.int<"5">
    %24 = symbol.mul %23, %15 : !symbol.int<"5">, !symbol.int<"5"> -> !symbol.int<"25">
    %25 = "dma.reshape"(%12, %19, %24) <{operandSegmentSizes = array<i32: 1, 2>}> : (!nn.memory<[1, 3, 5, 5, 5, 5], [1875, 625, 125, 25, 5, 1], f32, #nn.space<global>>, !symbol.int<"75">, !symbol.int<"25">) -> !nn.memory<[75, 25], [25, 1], f32, #nn.space<global>>
    %26 = "nn.matmul"(%18, %25) {space = #nn.space<global>} : (!nn.memory<[4, 75], [75, 1], f32, #nn.space<global>>, !nn.memory<[75, 25], [25, 1], f32, #nn.space<global>>) -> !nn.memory<[4, 25], [25, 1], f32, #nn.space<global>>
    %27 = symbol.const 4 : !symbol.int<"4">
    %28 = "dma.reshape"(%26, %13, %27, %14, %15) <{operandSegmentSizes = array<i32: 1, 4>}> : (!nn.memory<[4, 25], [25, 1], f32, #nn.space<global>>, !symbol.int<"1">, !symbol.int<"4">, !symbol.int<"5">, !symbol.int<"5">) -> !nn.memory<[1, 4, 5, 5], [100, 25, 5, 1], f32, #nn.space<global>>
    func.return %28 : !nn.memory<[1, 4, 5, 5], [100, 25, 5, 1], f32, #nn.space<global>>
  }
}"""

CASE_4_RUNTIME_ARGS = (
    Memory([1, 3, 5, 5], NumericType.Float32, space=MemorySpace.GM),
    Memory([4, 3, 5, 5], NumericType.Float32, space=MemorySpace.GM),
)

def conv_kernel_case_4(value, weight):
    return conv(value, weight, sh=1, sw=1, dh=1, dw=1, ph=2, pw=2, pl=2, pr=2)

CASE_5_RUNTIME_ARGS = (
    Memory([1, 5, 5, 3], NumericType.Float32, space=MemorySpace.GM, format=Farmat.CLast),
    Memory([8, 3, 3, 3], NumericType.Float32, space=MemorySpace.GM),
)

def conv_kernel_case_5(value, weight):
    return conv(value, weight, sh=1, sw=1, dh=1, dw=1, ph=1, pw=1, pl=1, pr=1)

# CASE-6 IR：动态正向例子：`kh/pad` 为 symbol 输入时应生成完整 lowering 链路并保留 symbol 表达式。
CASE_6_IR = """builtin.module {
  func.func @conv_kernel_case_6(%0 : !nn.memory<[1, 3, 8, 8], [192, 64, 8, 1], f32, #nn.space<global>>, %1 : !nn.memory<[4, 3, KH, KW], [3*KH*KW, KH*KW, KW, 1], f32, #nn.space<global>>, %2 : !symbol.int<"PH">, %3 : !symbol.int<"PW">, %4 : !symbol.int<"PL">, %5 : !symbol.int<"PR">) -> !nn.memory<[1, 4, (-KH + PH + PW + 8)/1 + 1, (-KW + PL + PR + 8)/1 + 1], [4*((-KH + PH + PW + 8)/1 + 1)*((-KW + PL + PR + 8)/1 + 1), ((-KH + PH + PW + 8)/1 + 1)*((-KW + PL + PR + 8)/1 + 1), (-KW + PL + PR + 8)/1 + 1, 1], f32, #nn.space<global>> {
    %6 = "symbol.get_dim"(%1) {axis = #builtin.int<2>} : (!nn.memory<[4, 3, KH, KW], [3*KH*KW, KH*KW, KW, 1], f32, #nn.space<global>>) -> !symbol.int<"KH">
    %7 = "symbol.get_dim"(%1) {axis = #builtin.int<3>} : (!nn.memory<[4, 3, KH, KW], [3*KH*KW, KH*KW, KW, 1], f32, #nn.space<global>>) -> !symbol.int<"KW">
    %8 = symbol.const 1 : !symbol.int<"1">
    %9 = symbol.const 1 : !symbol.int<"1">
    %10 = symbol.const 1 : !symbol.int<"1">
    %11 = symbol.const 1 : !symbol.int<"1">
    %12 = "nn.img2col2d"(%0, %6, %7, %8, %9, %10, %11, %2, %3, %4, %5) {space = #nn.space<global>} : (!nn.memory<[1, 3, 8, 8], [192, 64, 8, 1], f32, #nn.space<global>>, !symbol.int<"KH">, !symbol.int<"KW">, !symbol.int<"1">, !symbol.int<"1">, !symbol.int<"1">, !symbol.int<"1">, !symbol.int<"PH">, !symbol.int<"PW">, !symbol.int<"PL">, !symbol.int<"PR">) -> !nn.memory<[1, 3, KH, KW, (-KH + PH + PW + 8)/1 + 1, (-KW + PL + PR + 8)/1 + 1], [3*KH*KW*((-KH + PH + PW + 8)/1 + 1)*((-KW + PL + PR + 8)/1 + 1), KH*KW*((-KH + PH + PW + 8)/1 + 1)*((-KW + PL + PR + 8)/1 + 1), KW*((-KH + PH + PW + 8)/1 + 1)*((-KW + PL + PR + 8)/1 + 1), ((-KH + PH + PW + 8)/1 + 1)*((-KW + PL + PR + 8)/1 + 1), (-KW + PL + PR + 8)/1 + 1, 1], f32, #nn.space<global>>
    %13 = "symbol.get_dim"(%12) {axis = #builtin.int<0>} : (!nn.memory<[1, 3, KH, KW, (-KH + PH + PW + 8)/1 + 1, (-KW + PL + PR + 8)/1 + 1], [3*KH*KW*((-KH + PH + PW + 8)/1 + 1)*((-KW + PL + PR + 8)/1 + 1), KH*KW*((-KH + PH + PW + 8)/1 + 1)*((-KW + PL + PR + 8)/1 + 1), KW*((-KH + PH + PW + 8)/1 + 1)*((-KW + PL + PR + 8)/1 + 1), ((-KH + PH + PW + 8)/1 + 1)*((-KW + PL + PR + 8)/1 + 1), (-KW + PL + PR + 8)/1 + 1, 1], f32, #nn.space<global>>) -> !symbol.int<"1">
    %14 = "symbol.get_dim"(%12) {axis = #builtin.int<4>} : (!nn.memory<[1, 3, KH, KW, (-KH + PH + PW + 8)/1 + 1, (-KW + PL + PR + 8)/1 + 1], [3*KH*KW*((-KH + PH + PW + 8)/1 + 1)*((-KW + PL + PR + 8)/1 + 1), KH*KW*((-KH + PH + PW + 8)/1 + 1)*((-KW + PL + PR + 8)/1 + 1), KW*((-KH + PH + PW + 8)/1 + 1)*((-KW + PL + PR + 8)/1 + 1), ((-KH + PH + PW + 8)/1 + 1)*((-KW + PL + PR + 8)/1 + 1), (-KW + PL + PR + 8)/1 + 1, 1], f32, #nn.space<global>>) -> !symbol.int<"(-KH + PH + PW + 8)/1 + 1">
    %15 = "symbol.get_dim"(%12) {axis = #builtin.int<5>} : (!nn.memory<[1, 3, KH, KW, (-KH + PH + PW + 8)/1 + 1, (-KW + PL + PR + 8)/1 + 1], [3*KH*KW*((-KH + PH + PW + 8)/1 + 1)*((-KW + PL + PR + 8)/1 + 1), KH*KW*((-KH + PH + PW + 8)/1 + 1)*((-KW + PL + PR + 8)/1 + 1), KW*((-KH + PH + PW + 8)/1 + 1)*((-KW + PL + PR + 8)/1 + 1), ((-KH + PH + PW + 8)/1 + 1)*((-KW + PL + PR + 8)/1 + 1), (-KW + PL + PR + 8)/1 + 1, 1], f32, #nn.space<global>>) -> !symbol.int<"(-KW + PL + PR + 8)/1 + 1">
    %16 = symbol.const 4 : !symbol.int<"4">
    %17 = symbol.const 3 : !symbol.int<"3">
    %18 = symbol.mul %17, %6 : !symbol.int<"3">, !symbol.int<"KH"> -> !symbol.int<"3*KH">
    %19 = symbol.mul %18, %7 : !symbol.int<"3*KH">, !symbol.int<"KW"> -> !symbol.int<"3*KH*KW">
    %20 = "dma.reshape"(%1, %16, %19) <{operandSegmentSizes = array<i32: 1, 2>}> : (!nn.memory<[4, 3, KH, KW], [3*KH*KW, KH*KW, KW, 1], f32, #nn.space<global>>, !symbol.int<"4">, !symbol.int<"3*KH*KW">) -> !nn.memory<[4, 3*KH*KW], [3*KH*KW, 1], f32, #nn.space<global>>
    %21 = symbol.const 3 : !symbol.int<"3">
    %22 = symbol.mul %21, %6 : !symbol.int<"3">, !symbol.int<"KH"> -> !symbol.int<"3*KH">
    %23 = symbol.mul %22, %7 : !symbol.int<"3*KH">, !symbol.int<"KW"> -> !symbol.int<"3*KH*KW">
    %24 = symbol.mul %13, %14 : !symbol.int<"1">, !symbol.int<"(-KH + PH + PW + 8)/1 + 1"> -> !symbol.int<"(-KH + PH + PW + 8)/1 + 1">
    %25 = symbol.mul %24, %15 : !symbol.int<"(-KH + PH + PW + 8)/1 + 1">, !symbol.int<"(-KW + PL + PR + 8)/1 + 1"> -> !symbol.int<"((-KH + PH + PW + 8)/1 + 1)*((-KW + PL + PR + 8)/1 + 1)">
    %26 = "dma.reshape"(%12, %23, %25) <{operandSegmentSizes = array<i32: 1, 2>}> : (!nn.memory<[1, 3, KH, KW, (-KH + PH + PW + 8)/1 + 1, (-KW + PL + PR + 8)/1 + 1], [3*KH*KW*((-KH + PH + PW + 8)/1 + 1)*((-KW + PL + PR + 8)/1 + 1), KH*KW*((-KH + PH + PW + 8)/1 + 1)*((-KW + PL + PR + 8)/1 + 1), KW*((-KH + PH + PW + 8)/1 + 1)*((-KW + PL + PR + 8)/1 + 1), ((-KH + PH + PW + 8)/1 + 1)*((-KW + PL + PR + 8)/1 + 1), (-KW + PL + PR + 8)/1 + 1, 1], f32, #nn.space<global>>, !symbol.int<"3*KH*KW">, !symbol.int<"((-KH + PH + PW + 8)/1 + 1)*((-KW + PL + PR + 8)/1 + 1)">) -> !nn.memory<[3*KH*KW, ((-KH + PH + PW + 8)/1 + 1)*((-KW + PL + PR + 8)/1 + 1)], [((-KH + PH + PW + 8)/1 + 1)*((-KW + PL + PR + 8)/1 + 1), 1], f32, #nn.space<global>>
    %27 = "nn.matmul"(%20, %26) {space = #nn.space<global>} : (!nn.memory<[4, 3*KH*KW], [3*KH*KW, 1], f32, #nn.space<global>>, !nn.memory<[3*KH*KW, ((-KH + PH + PW + 8)/1 + 1)*((-KW + PL + PR + 8)/1 + 1)], [((-KH + PH + PW + 8)/1 + 1)*((-KW + PL + PR + 8)/1 + 1), 1], f32, #nn.space<global>>) -> !nn.memory<[4, ((-KH + PH + PW + 8)/1 + 1)*((-KW + PL + PR + 8)/1 + 1)], [((-KH + PH + PW + 8)/1 + 1)*((-KW + PL + PR + 8)/1 + 1), 1], f32, #nn.space<global>>
    %28 = symbol.const 4 : !symbol.int<"4">
    %29 = "dma.reshape"(%27, %13, %28, %14, %15) <{operandSegmentSizes = array<i32: 1, 4>}> : (!nn.memory<[4, ((-KH + PH + PW + 8)/1 + 1)*((-KW + PL + PR + 8)/1 + 1)], [((-KH + PH + PW + 8)/1 + 1)*((-KW + PL + PR + 8)/1 + 1), 1], f32, #nn.space<global>>, !symbol.int<"1">, !symbol.int<"4">, !symbol.int<"(-KH + PH + PW + 8)/1 + 1">, !symbol.int<"(-KW + PL + PR + 8)/1 + 1">) -> !nn.memory<[1, 4, (-KH + PH + PW + 8)/1 + 1, (-KW + PL + PR + 8)/1 + 1], [4*((-KH + PH + PW + 8)/1 + 1)*((-KW + PL + PR + 8)/1 + 1), ((-KH + PH + PW + 8)/1 + 1)*((-KW + PL + PR + 8)/1 + 1), (-KW + PL + PR + 8)/1 + 1, 1], f32, #nn.space<global>>
    func.return %29 : !nn.memory<[1, 4, (-KH + PH + PW + 8)/1 + 1, (-KW + PL + PR + 8)/1 + 1], [4*((-KH + PH + PW + 8)/1 + 1)*((-KW + PL + PR + 8)/1 + 1), ((-KH + PH + PW + 8)/1 + 1)*((-KW + PL + PR + 8)/1 + 1), (-KW + PL + PR + 8)/1 + 1, 1], f32, #nn.space<global>>
  }
}"""

CASE_6_RUNTIME_ARGS = (
    Memory([1, 3, 8, 8], NumericType.Float32, space=MemorySpace.GM),
    Memory([4, 3, SymbolDim("KH"), SymbolDim("KW")], NumericType.Float32, space=MemorySpace.GM),
    SymbolDim("PH"),
    SymbolDim("PW"),
    SymbolDim("PL"),
    SymbolDim("PR"),
)

def conv_kernel_case_6(value, weight, ph, pw, pl, pr):
    return conv(value, weight, sh=1, sw=1, dh=1, dw=1, ph=ph, pw=pw, pl=pl, pr=pr)

# CASE-7 描述：失败例子：`conv(value, weight, ...)` 的输入通道与权重通道不匹配时应在构造阶段拒绝。
CASE_7_RUNTIME_ARGS = (
    Memory([1, 2, 5, 5], NumericType.Float32, space=MemorySpace.GM),
    Memory([8, 3, 3, 3], NumericType.Float32, space=MemorySpace.GM),
)

def conv_kernel_case_7(value, weight):
    return conv(value, weight, sh=1, sw=1, dh=1, dw=1, ph=1, pw=1, pl=1, pr=1)


def _case_1_true():
    print("[CASE-1] 静态正向例子：conv(value, weight, ...) -> lowering chain")
    ok = mlir_gen_compare_text(fn=conv_kernel_case_1, runtime_args=CASE_1_RUNTIME_ARGS, config=None, mlir_text=CASE_1_IR)
    assert ok is True, "expected mlir_gen_compare_text(...) to return True for static conv module text"


def _case_2_true():
    print("[CASE-2] 动态正向例子：conv(value, weight, ...) symbol shape -> lowering chain")
    ok = mlir_gen_compare_text(fn=conv_kernel_case_2, runtime_args=CASE_2_RUNTIME_ARGS, config=None, mlir_text=CASE_2_IR)
    assert ok is True, "expected mlir_gen_compare_text(...) to return True for dynamic conv module text"


def _case_3_true():
    print("[CASE-3] 静态正向例子：kh=1/pad=0 -> lowering chain")
    ok = mlir_gen_compare_text(fn=conv_kernel_case_3, runtime_args=CASE_3_RUNTIME_ARGS, config=None, mlir_text=CASE_3_IR)
    assert ok is True, "expected mlir_gen_compare_text(...) to return True for kh=1/pad=0 conv module text"


def _case_4_true():
    print("[CASE-4] 静态正向例子：kh=5/pad=2 -> lowering chain")
    ok = mlir_gen_compare_text(fn=conv_kernel_case_4, runtime_args=CASE_4_RUNTIME_ARGS, config=None, mlir_text=CASE_4_IR)
    assert ok is True, "expected mlir_gen_compare_text(...) to return True for kh=5/pad=2 conv module text"


def _case_5_reject_clast_input_contract():
    print("[CASE-5] 失败例子：format=CLast 的输入不属于当前 conv 的 NCHW 公开合同")
    try:
        mlir_gen_compare_text(fn=conv_kernel_case_5, runtime_args=CASE_5_RUNTIME_ARGS, config=None, mlir_text=CASE_1_IR)
    except ValueError as exc:
        assert "conv input channel mismatch" in str(exc)
    else:
        raise AssertionError("conv with CLast input should be rejected under the current NCHW contract")


def _case_6_true():
    print("[CASE-6] 动态正向例子：kh/pad 为 symbol -> lowering chain")
    ok = mlir_gen_compare_text(fn=conv_kernel_case_6, runtime_args=CASE_6_RUNTIME_ARGS, config=None, mlir_text=CASE_6_IR)
    assert ok is True, "expected mlir_gen_compare_text(...) to return True for dynamic kh/pad conv module text"


def _case_7_reject_input_channel_mismatch():
    print("[CASE-7] 失败例子：conv(value, weight, ...) 的输入通道与权重通道不匹配时应在构造阶段拒绝")
    try:
        mlir_gen_compare_text(fn=conv_kernel_case_7, runtime_args=CASE_7_RUNTIME_ARGS, config=None, mlir_text=CASE_1_IR)
    except ValueError as exc:
        assert "conv input channel mismatch" in str(exc)
    else:
        raise AssertionError("conv with mismatched input/weight channels should be rejected before MLIR compare")


def main():
    failures: list[tuple[str, BaseException]] = []
    run_case(failures, "CASE-1", _case_1_true)
    run_case(failures, "CASE-2", _case_2_true)
    run_case(failures, "CASE-3", _case_3_true)
    run_case(failures, "CASE-4", _case_4_true)
    run_case(failures, "CASE-5", _case_5_reject_clast_input_contract)
    run_case(failures, "CASE-6", _case_6_true)
    run_case(failures, "CASE-7", _case_7_reject_input_channel_mismatch)
    raise_if_failures("dsl mlir_gen nn conv expectation", failures)


if __name__ == "__main__":
    main()
