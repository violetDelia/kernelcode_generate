"""DSL nn.img2col2d expectation.

创建者: 大闸蟹
最后一次更改: 守护最好的爱莉希雅

功能说明:
- 演示 `dsl/mlir_gen` expectation 如何直接使用 `mlir_gen_compare_text(...)` 比较完整 `builtin.module`。
- 锁定 `img2col2d(src, kh, kw, sh, sw, dh, dw, ph, pw, pl, pr)` 的目标公开合同：应生成显式 `nn.img2col2d`。

使用示例:
- `PYTHONPATH=. python expectation/dsl/mlir_gen/dialect/nn/img2col2d.py`

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
# - CASE-1: 静态正向例子：`img2col2d(...)` 的 NCHW 静态输入应生成显式 `nn.img2col2d`。
# - CASE-2: 动态正向例子：`img2col2d(...)` 的 CLast symbol shape 输入应生成显式 `nn.img2col2d`。
# - CASE-3: 失败例子：`img2col2d(...)` 的输出高度非正时应在构造阶段拒绝。

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
from kernel_gen.operation.nn import img2col2d
from kernel_gen.symbol_variable.memory import Memory, MemorySpace
from kernel_gen.symbol_variable.symbol_dim import SymbolDim
from kernel_gen.symbol_variable.type import Farmat, NumericType
from kernel_gen.tools.mlir_gen_compare import mlir_gen_compare_text

# CASE-1 IR：静态正向例子：`img2col2d(...)` 的 NCHW 静态输入应生成显式 `nn.img2col2d`。
CASE_1_IR = """builtin.module {
  func.func @img2col2d_kernel_case_1(%0 : !nn.memory<[1, 3, 5, 5], [75, 25, 5, 1], f32, #nn.space<global>>) -> !nn.memory<[1, 3, 3, 3, 3, 3], [243, 81, 27, 9, 3, 1], f32, #nn.space<global>> {
    %1 = symbol.const 3 : !symbol.int<"3">
    %2 = symbol.const 3 : !symbol.int<"3">
    %3 = symbol.const 1 : !symbol.int<"1">
    %4 = symbol.const 1 : !symbol.int<"1">
    %5 = symbol.const 1 : !symbol.int<"1">
    %6 = symbol.const 1 : !symbol.int<"1">
    %7 = symbol.const 0 : !symbol.int<"0">
    %8 = symbol.const 0 : !symbol.int<"0">
    %9 = symbol.const 0 : !symbol.int<"0">
    %10 = symbol.const 0 : !symbol.int<"0">
    %11 = "nn.img2col2d"(%0, %1, %2, %3, %4, %5, %6, %7, %8, %9, %10) {space = #nn.space<global>} : (!nn.memory<[1, 3, 5, 5], [75, 25, 5, 1], f32, #nn.space<global>>, !symbol.int<"3">, !symbol.int<"3">, !symbol.int<"1">, !symbol.int<"1">, !symbol.int<"1">, !symbol.int<"1">, !symbol.int<"0">, !symbol.int<"0">, !symbol.int<"0">, !symbol.int<"0">) -> !nn.memory<[1, 3, 3, 3, 3, 3], [243, 81, 27, 9, 3, 1], f32, #nn.space<global>>
    func.return %11 : !nn.memory<[1, 3, 3, 3, 3, 3], [243, 81, 27, 9, 3, 1], f32, #nn.space<global>>
  }
}"""

CASE_1_RUNTIME_ARGS = (
    Memory([1, 3, 5, 5], NumericType.Float32, space=MemorySpace.GM, format=Farmat.Norm),
)

def img2col2d_kernel_case_1(src):
    return img2col2d(src, kh=3, kw=3, sh=1, sw=1, dh=1, dw=1, ph=0, pw=0, pl=0, pr=0)

# CASE-2 IR：动态正向例子：`img2col2d(...)` 的 CLast symbol shape 输入应生成显式 `nn.img2col2d`。
CASE_2_IR = """builtin.module {
  func.func @img2col2d_kernel_case_2(%0 : !nn.memory<[1, H, W, 3], [3*H*W, 3*W, 3, 1], f32, #nn.space<global>>) -> !nn.memory<[1, (H - 3)/1 + 1, (W - 3)/1 + 1, 3, 3, 3], [((H - 3)/1 + 1)*(27*(W - 3)/1 + 27), 27*(W - 3)/1 + 27, 27, 9, 3, 1], f32, #nn.space<global>> {
    %1 = symbol.const 3 : !symbol.int<"3">
    %2 = symbol.const 3 : !symbol.int<"3">
    %3 = symbol.const 1 : !symbol.int<"1">
    %4 = symbol.const 1 : !symbol.int<"1">
    %5 = symbol.const 1 : !symbol.int<"1">
    %6 = symbol.const 1 : !symbol.int<"1">
    %7 = symbol.const 0 : !symbol.int<"0">
    %8 = symbol.const 0 : !symbol.int<"0">
    %9 = symbol.const 0 : !symbol.int<"0">
    %10 = symbol.const 0 : !symbol.int<"0">
    %11 = "nn.img2col2d"(%0, %1, %2, %3, %4, %5, %6, %7, %8, %9, %10) {space = #nn.space<global>} : (!nn.memory<[1, H, W, 3], [3*H*W, 3*W, 3, 1], f32, #nn.space<global>>, !symbol.int<"3">, !symbol.int<"3">, !symbol.int<"1">, !symbol.int<"1">, !symbol.int<"1">, !symbol.int<"1">, !symbol.int<"0">, !symbol.int<"0">, !symbol.int<"0">, !symbol.int<"0">) -> !nn.memory<[1, (H - 3)/1 + 1, (W - 3)/1 + 1, 3, 3, 3], [((H - 3)/1 + 1)*(27*(W - 3)/1 + 27), 27*(W - 3)/1 + 27, 27, 9, 3, 1], f32, #nn.space<global>>
    func.return %11 : !nn.memory<[1, (H - 3)/1 + 1, (W - 3)/1 + 1, 3, 3, 3], [((H - 3)/1 + 1)*(27*(W - 3)/1 + 27), 27*(W - 3)/1 + 27, 27, 9, 3, 1], f32, #nn.space<global>>
  }
}"""

CASE_2_RUNTIME_ARGS = (
    Memory([1, SymbolDim("H"), SymbolDim("W"), 3], NumericType.Float32, space=MemorySpace.GM, format=Farmat.CLast),
)

def img2col2d_kernel_case_2(src):
    return img2col2d(src, kh=3, kw=3, sh=1, sw=1, dh=1, dw=1, ph=0, pw=0, pl=0, pr=0)

# CASE-3 描述：失败例子：`img2col2d(...)` 的输出高度非正时应在构造阶段拒绝。
CASE_3_RUNTIME_ARGS = (
    Memory([1, 4, 2, 5], NumericType.Float32, space=MemorySpace.GM, format=Farmat.Norm),
)

def img2col2d_kernel_case_3(src):
    return img2col2d(src, kh=5, kw=3, sh=1, sw=1, dh=1, dw=1, ph=0, pw=0, pl=0, pr=0)


def _case_1_true():
    print("[CASE-1] 静态正向例子：img2col2d(src, kh, kw, sh, sw, dh, dw, ph, pw, pl, pr) -> nn.img2col2d")
    ok = mlir_gen_compare_text(fn=img2col2d_kernel_case_1, runtime_args=CASE_1_RUNTIME_ARGS, config=None, mlir_text=CASE_1_IR)
    assert ok is True, "expected mlir_gen_compare_text(...) to return True for static img2col2d module text"


def _case_2_true():
    print("[CASE-2] 动态正向例子：img2col2d(src, kh, kw, sh, sw, dh, dw, ph, pw, pl, pr) symbol shape -> nn.img2col2d")
    ok = mlir_gen_compare_text(fn=img2col2d_kernel_case_2, runtime_args=CASE_2_RUNTIME_ARGS, config=None, mlir_text=CASE_2_IR)
    assert ok is True, "expected mlir_gen_compare_text(...) to return True for dynamic img2col2d module text"


def _case_3_reject_non_positive_output_height():
    print("[CASE-3] 失败例子：img2col2d(...) 的输出高度非正时应在构造阶段拒绝")
    try:
        mlir_gen_compare_text(fn=img2col2d_kernel_case_3, runtime_args=CASE_3_RUNTIME_ARGS, config=None, mlir_text=CASE_1_IR)
    except ValueError as exc:
        assert "img2col output height must be positive" in str(exc)
    else:
        raise AssertionError("img2col2d with non-positive output height should be rejected before MLIR compare")


def main():
    failures: list[tuple[str, BaseException]] = []
    run_case(failures, "CASE-1", _case_1_true)
    run_case(failures, "CASE-2", _case_2_true)
    run_case(failures, "CASE-3", _case_3_reject_non_positive_output_height)
    raise_if_failures("dsl mlir_gen nn img2col2d expectation", failures)


if __name__ == "__main__":
    main()
