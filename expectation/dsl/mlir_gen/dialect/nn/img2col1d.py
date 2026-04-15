"""DSL nn.img2col1d expectation.

创建者: 大闸蟹
最后一次更改: 守护最好的爱莉希雅

功能说明:
- 演示 `dsl/mlir_gen` expectation 如何直接使用 `mlir_gen_compare_text(...)` 比较完整 `builtin.module`。
- 锁定 `img2col1d(src, kw, sw, dw, pl, pr)` 的目标公开合同：应生成显式 `nn.img2col1d`。

使用示例:
- `PYTHONPATH=. python expectation/dsl/mlir_gen/dialect/nn/img2col1d.py`

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
# - CASE-1: 静态正向例子：`img2col1d(...)` 的 NCHW 静态输入应生成显式 `nn.img2col1d`。
# - CASE-2: 动态正向例子：`img2col1d(...)` 的 CLast symbol shape 输入应生成显式 `nn.img2col1d`。
# - CASE-3: 动态正向例子：`img2col1d(src, kw, ...)` 的 memory + symbol 输入应生成显式 `nn.img2col1d`。
# - CASE-4: 动态正向例子：`img2col1d(...)` 的 Norm symbol shape 输入应生成显式 `nn.img2col1d`。
# - CASE-5: 失败例子：`img2col1d(...)` 的输出宽度非正时应在构造阶段拒绝。

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
from kernel_gen.operation.nn import img2col1d
from kernel_gen.symbol_variable.memory import Memory, MemorySpace
from kernel_gen.symbol_variable.symbol_dim import SymbolDim
from kernel_gen.symbol_variable.type import Farmat, NumericType
from kernel_gen.tools.mlir_gen_compare import mlir_gen_compare_text

# CASE-1 IR：静态正向例子：`img2col1d(...)` 的 NCHW 静态输入应生成显式 `nn.img2col1d`。
CASE_1_IR = """builtin.module {
  func.func @img2col1d_kernel_case_1(%0 : !nn.memory<[1, 4, 8], [32, 8, 1], f32, #nn.space<global>>) -> !nn.memory<[1, 4, 3, 8], [96, 24, 8, 1], f32, #nn.space<global>> {
    %1 = symbol.const 3 : !symbol.int<"3">
    %2 = symbol.const 1 : !symbol.int<"1">
    %3 = symbol.const 1 : !symbol.int<"1">
    %4 = symbol.const 1 : !symbol.int<"1">
    %5 = symbol.const 1 : !symbol.int<"1">
    %6 = "nn.img2col1d"(%0, %1, %2, %3, %4, %5) {space = #nn.space<global>} : (!nn.memory<[1, 4, 8], [32, 8, 1], f32, #nn.space<global>>, !symbol.int<"3">, !symbol.int<"1">, !symbol.int<"1">, !symbol.int<"1">, !symbol.int<"1">) -> !nn.memory<[1, 4, 3, 8], [96, 24, 8, 1], f32, #nn.space<global>>
    func.return %6 : !nn.memory<[1, 4, 3, 8], [96, 24, 8, 1], f32, #nn.space<global>>
  }
}"""

CASE_1_RUNTIME_ARGS = (
    Memory([1, 4, 8], NumericType.Float32, space=MemorySpace.GM, format=Farmat.Norm),
)

def img2col1d_kernel_case_1(src):
    return img2col1d(src, kw=3, sw=1, dw=1, pl=1, pr=1)

# CASE-2 IR：动态正向例子：`img2col1d(...)` 的 CLast symbol shape 输入应生成显式 `nn.img2col1d`。
CASE_2_IR = """builtin.module {
  func.func @img2col1d_kernel_case_2(%0 : !nn.memory<[1, W, 4], [4*W, 4, 1], f32, #nn.space<global>>) -> !nn.memory<[1, (W - 1)/1 + 1, 3, 4], [12*(W - 1)/1 + 12, 12, 4, 1], f32, #nn.space<global>> {
    %1 = symbol.const 3 : !symbol.int<"3">
    %2 = symbol.const 1 : !symbol.int<"1">
    %3 = symbol.const 1 : !symbol.int<"1">
    %4 = symbol.const 1 : !symbol.int<"1">
    %5 = symbol.const 1 : !symbol.int<"1">
    %6 = "nn.img2col1d"(%0, %1, %2, %3, %4, %5) {space = #nn.space<global>} : (!nn.memory<[1, W, 4], [4*W, 4, 1], f32, #nn.space<global>>, !symbol.int<"3">, !symbol.int<"1">, !symbol.int<"1">, !symbol.int<"1">, !symbol.int<"1">) -> !nn.memory<[1, (W - 1)/1 + 1, 3, 4], [12*(W - 1)/1 + 12, 12, 4, 1], f32, #nn.space<global>>
    func.return %6 : !nn.memory<[1, (W - 1)/1 + 1, 3, 4], [12*(W - 1)/1 + 12, 12, 4, 1], f32, #nn.space<global>>
  }
}"""

CASE_2_RUNTIME_ARGS = (
    Memory([1, SymbolDim("W"), 4], NumericType.Float32, space=MemorySpace.GM, format=Farmat.CLast),
)

def img2col1d_kernel_case_2(src):
    return img2col1d(src, kw=3, sw=1, dw=1, pl=1, pr=1)

# CASE-3 IR：动态正向例子：`img2col1d(src, kw, ...)` 的 memory + symbol 输入应生成显式 `nn.img2col1d`。
CASE_3_IR = """builtin.module {
  func.func @img2col1d_kernel_case_3(%0 : !nn.memory<[1, W, 4], [4*W, 4, 1], f32, #nn.space<global>>, %1 : !symbol.int<"KW">) -> !nn.memory<[1, (-KW + W + 2)/1 + 1, KW, 4], [4*KW*((-KW + W + 2)/1 + 1), 4*KW, 4, 1], f32, #nn.space<global>> {
    %2 = symbol.const 1 : !symbol.int<"1">
    %3 = symbol.const 1 : !symbol.int<"1">
    %4 = symbol.const 1 : !symbol.int<"1">
    %5 = symbol.const 1 : !symbol.int<"1">
    %6 = "nn.img2col1d"(%0, %1, %2, %3, %4, %5) {space = #nn.space<global>} : (!nn.memory<[1, W, 4], [4*W, 4, 1], f32, #nn.space<global>>, !symbol.int<"KW">, !symbol.int<"1">, !symbol.int<"1">, !symbol.int<"1">, !symbol.int<"1">) -> !nn.memory<[1, (-KW + W + 2)/1 + 1, KW, 4], [4*KW*((-KW + W + 2)/1 + 1), 4*KW, 4, 1], f32, #nn.space<global>>
    func.return %6 : !nn.memory<[1, (-KW + W + 2)/1 + 1, KW, 4], [4*KW*((-KW + W + 2)/1 + 1), 4*KW, 4, 1], f32, #nn.space<global>>
  }
}"""

CASE_3_RUNTIME_ARGS = (
    Memory([1, SymbolDim("W"), 4], NumericType.Float32, space=MemorySpace.GM, format=Farmat.CLast),
    SymbolDim("KW"),
)

def img2col1d_kernel_case_3(src, kw):
    return img2col1d(src, kw=kw, sw=1, dw=1, pl=1, pr=1)

# CASE-4 IR：动态正向例子：`img2col1d(...)` 的 Norm symbol shape 输入应生成显式 `nn.img2col1d`。
CASE_4_IR = """builtin.module {
  func.func @img2col1d_kernel_case_4(%0 : !nn.memory<[1, 4, W], [4*W, W, 1], f32, #nn.space<global>>) -> !nn.memory<[1, 4, 3, (W - 1)/1 + 1], [12*(W - 1)/1 + 12, 3*(W - 1)/1 + 3, (W - 1)/1 + 1, 1], f32, #nn.space<global>> {
    %1 = symbol.const 3 : !symbol.int<"3">
    %2 = symbol.const 1 : !symbol.int<"1">
    %3 = symbol.const 1 : !symbol.int<"1">
    %4 = symbol.const 1 : !symbol.int<"1">
    %5 = symbol.const 1 : !symbol.int<"1">
    %6 = "nn.img2col1d"(%0, %1, %2, %3, %4, %5) {space = #nn.space<global>} : (!nn.memory<[1, 4, W], [4*W, W, 1], f32, #nn.space<global>>, !symbol.int<"3">, !symbol.int<"1">, !symbol.int<"1">, !symbol.int<"1">, !symbol.int<"1">) -> !nn.memory<[1, 4, 3, (W - 1)/1 + 1], [12*(W - 1)/1 + 12, 3*(W - 1)/1 + 3, (W - 1)/1 + 1, 1], f32, #nn.space<global>>
    func.return %6 : !nn.memory<[1, 4, 3, (W - 1)/1 + 1], [12*(W - 1)/1 + 12, 3*(W - 1)/1 + 3, (W - 1)/1 + 1, 1], f32, #nn.space<global>>
  }
}"""

CASE_4_RUNTIME_ARGS = (
    Memory([1, 4, SymbolDim("W")], NumericType.Float32, space=MemorySpace.GM, format=Farmat.Norm),
)

def img2col1d_kernel_case_4(src):
    return img2col1d(src, kw=3, sw=1, dw=1, pl=1, pr=1)

# CASE-5 描述：失败例子：`img2col1d(...)` 的输出宽度非正时应在构造阶段拒绝。
CASE_5_RUNTIME_ARGS = (
    Memory([1, 4, 2], NumericType.Float32, space=MemorySpace.GM, format=Farmat.Norm),
)

def img2col1d_kernel_case_5(src):
    return img2col1d(src, kw=5, sw=1, dw=1, pl=0, pr=0)


def _case_1_true():
    print("[CASE-1] 静态正向例子：img2col1d(src, kw, sw, dw, pl, pr) -> nn.img2col1d")
    ok = mlir_gen_compare_text(fn=img2col1d_kernel_case_1, runtime_args=CASE_1_RUNTIME_ARGS, config=None, mlir_text=CASE_1_IR)
    assert ok is True, "expected mlir_gen_compare_text(...) to return True for static img2col1d module text"


def _case_2_true():
    print("[CASE-2] 动态正向例子：img2col1d(src, kw, sw, dw, pl, pr) symbol shape -> nn.img2col1d")
    ok = mlir_gen_compare_text(fn=img2col1d_kernel_case_2, runtime_args=CASE_2_RUNTIME_ARGS, config=None, mlir_text=CASE_2_IR)
    assert ok is True, "expected mlir_gen_compare_text(...) to return True for dynamic img2col1d module text"


def _case_3_true():
    print("[CASE-3] 动态正向例子：img2col1d(src, kw, ...) memory + symbol -> nn.img2col1d")
    ok = mlir_gen_compare_text(fn=img2col1d_kernel_case_3, runtime_args=CASE_3_RUNTIME_ARGS, config=None, mlir_text=CASE_3_IR)
    assert ok is True, "expected mlir_gen_compare_text(...) to return True for memory+symbol img2col1d module text"


def _case_4_true():
    print("[CASE-4] 动态正向例子：img2col1d(...) Norm symbol shape -> nn.img2col1d")
    ok = mlir_gen_compare_text(fn=img2col1d_kernel_case_4, runtime_args=CASE_4_RUNTIME_ARGS, config=None, mlir_text=CASE_4_IR)
    assert ok is True, "expected mlir_gen_compare_text(...) to return True for dynamic Norm img2col1d module text"


def _case_5_reject_non_positive_output_width():
    print("[CASE-5] 失败例子：img2col1d(...) 的输出宽度非正时应在构造阶段拒绝")
    try:
        mlir_gen_compare_text(fn=img2col1d_kernel_case_5, runtime_args=CASE_5_RUNTIME_ARGS, config=None, mlir_text=CASE_1_IR)
    except ValueError as exc:
        assert "img2col1d output width must be positive" in str(exc)
    else:
        raise AssertionError("img2col1d with non-positive output width should be rejected before MLIR compare")


def main():
    failures: list[tuple[str, BaseException]] = []
    run_case(failures, "CASE-1", _case_1_true)
    run_case(failures, "CASE-2", _case_2_true)
    run_case(failures, "CASE-3", _case_3_true)
    run_case(failures, "CASE-4", _case_4_true)
    run_case(failures, "CASE-5", _case_5_reject_non_positive_output_width)
    raise_if_failures("dsl mlir_gen nn img2col1d expectation", failures)


if __name__ == "__main__":
    main()
