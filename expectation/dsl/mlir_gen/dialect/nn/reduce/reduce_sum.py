"""DSL nn reduce expectation: reduce_sum.

创建者: 大闸蟹
最后一次更改: 守护最好的爱莉希雅

功能说明:
- 演示 `dsl/mlir_gen` expectation 如何直接使用 `mlir_gen_compare_text(...)` 比较完整 `builtin.module`。
- 锁定 ``reduce_sum(src, axis=1, keepdim=True)` 应生成显式 `nn.reduce_sum`` 的目标公开合同。

使用示例:
- `PYTHONPATH=. python expectation/dsl/mlir_gen/dialect/nn/reduce/reduce_sum.py`

关联文件:
- spec: [`spec/dsl/mlir_gen.md`](spec/dsl/mlir_gen.md)
- spec: [`spec/dialect/nn.md`](spec/dialect/nn.md)
- spec: [`spec/operation/nn.md`](spec/operation/nn.md)
- spec: [`spec/tools/mlir_gen_compare.md`](spec/tools/mlir_gen_compare.md)
- test: [`test/dsl/test_ast_visitor.py`](test/dsl/test_ast_visitor.py)
- test: [`test/tools/test_mlir_gen_compare.py`](test/tools/test_mlir_gen_compare.py)
- 功能实现: [`kernel_gen/dsl/mlir_gen.py`](kernel_gen/dsl/mlir_gen.py)
- 功能实现: [`kernel_gen/tools/mlir_gen_compare.py`](kernel_gen/tools/mlir_gen_compare.py)
"""
# Case 列表:
# - CASE-1: 静态正向例子：`reduce_sum(src, axis=1, keepdim=True)` 的静态 shape 输入应生成显式 `nn.reduce_sum`。
# - CASE-2: 动态正向例子：`reduce_sum(src, axis=1, keepdim=True)` 的 symbol shape 输入应生成显式 `nn.reduce_sum`。
# - CASE-3: 静态正向例子：`reduce_sum(src, axis=1, keepdim=False)` 的静态 shape 输入应生成显式 `nn.reduce_sum`。
# - CASE-4: 动态正向例子：`reduce_sum(src, axis=2, keepdim=False)` 的 symbol shape 输入应生成显式 `nn.reduce_sum`。
# - CASE-5: 失败例子：`reduce_sum(src, axis=3, keepdim=True)` 的 axis 超出 rank 时应在构造阶段拒绝。

from __future__ import annotations

from pathlib import Path
import sys

CURRENT_DIR = Path(__file__).resolve().parent
if str(CURRENT_DIR) in sys.path:
    sys.path.remove(str(CURRENT_DIR))

REPO_ROOT = Path(__file__).resolve().parents[6]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from expectation.utils.case_runner import raise_if_failures, run_case
from kernel_gen.symbol_variable.memory import Memory, MemorySpace
from kernel_gen.symbol_variable.symbol_dim import SymbolDim
from kernel_gen.symbol_variable.type import NumericType
from kernel_gen.tools.mlir_gen_compare import mlir_gen_compare_text
from kernel_gen.operation.nn import reduce_sum
from xdsl.utils.exceptions import VerifyException

# CASE-1 IR：静态正向例子：`reduce_sum(src, axis=1, keepdim=True)` 的静态 shape 输入应生成显式 `nn.reduce_sum`。
CASE_1_IR = '''builtin.module {
  func.func @reduce_sum_kernel_case_1(%0 : !nn.memory<[2, 3, 4], [12, 4, 1], f32, #nn.space<global>>) -> !nn.memory<[2, 1, 4], [4, 4, 1], f32, #nn.space<global>> {
    %1 = "nn.reduce_sum"(%0) {axes = [1 : i64], keepdim = true, space = #nn.space<global>} : (!nn.memory<[2, 3, 4], [12, 4, 1], f32, #nn.space<global>>) -> !nn.memory<[2, 1, 4], [4, 4, 1], f32, #nn.space<global>>
    func.return %1 : !nn.memory<[2, 1, 4], [4, 4, 1], f32, #nn.space<global>>
  }
}'''

CASE_1_RUNTIME_ARGS = (
    Memory([2, 3, 4], NumericType.Float32, space=MemorySpace.GM),
)

def reduce_sum_kernel_case_1(src):
    return reduce_sum(src, axis=1, keepdim=True)

# CASE-2 IR：动态正向例子：`reduce_sum(src, axis=1, keepdim=True)` 的 symbol shape 输入应生成显式 `nn.reduce_sum`。
CASE_2_IR = '''builtin.module {
  func.func @reduce_sum_kernel_case_2(%0 : !nn.memory<[B, C, 4], [4*C, 4, 1], f32, #nn.space<global>>) -> !nn.memory<[B, 1, 4], [4, 4, 1], f32, #nn.space<global>> {
    %1 = "nn.reduce_sum"(%0) {axes = [1 : i64], keepdim = true, space = #nn.space<global>} : (!nn.memory<[B, C, 4], [4*C, 4, 1], f32, #nn.space<global>>) -> !nn.memory<[B, 1, 4], [4, 4, 1], f32, #nn.space<global>>
    func.return %1 : !nn.memory<[B, 1, 4], [4, 4, 1], f32, #nn.space<global>>
  }
}'''

CASE_2_RUNTIME_ARGS = (
    Memory([SymbolDim('B'), SymbolDim('C'), 4], NumericType.Float32, space=MemorySpace.GM),
)

def reduce_sum_kernel_case_2(src):
    return reduce_sum(src, axis=1, keepdim=True)

# CASE-3 IR：静态正向例子：`reduce_sum(src, axis=1, keepdim=False)` 的静态 shape 输入应生成显式 `nn.reduce_sum`。
CASE_3_IR = '''builtin.module {
  func.func @reduce_sum_kernel_case_3(%0 : !nn.memory<[2, 3, 4], [12, 4, 1], f32, #nn.space<global>>) -> !nn.memory<[2, 4], [4, 1], f32, #nn.space<global>> {
    %1 = "nn.reduce_sum"(%0) {axes = [1 : i64], keepdim = false, space = #nn.space<global>} : (!nn.memory<[2, 3, 4], [12, 4, 1], f32, #nn.space<global>>) -> !nn.memory<[2, 4], [4, 1], f32, #nn.space<global>>
    func.return %1 : !nn.memory<[2, 4], [4, 1], f32, #nn.space<global>>
  }
}'''

CASE_3_RUNTIME_ARGS = (
    Memory([2, 3, 4], NumericType.Float32, space=MemorySpace.GM),
)

def reduce_sum_kernel_case_3(src):
    return reduce_sum(src, axis=1, keepdim=False)

# CASE-4 IR：动态正向例子：`reduce_sum(src, axis=2, keepdim=False)` 的 symbol shape 输入应生成显式 `nn.reduce_sum`。
CASE_4_IR = '''builtin.module {
  func.func @reduce_sum_kernel_case_4(%0 : !nn.memory<[B, C, W], [C*W, W, 1], f32, #nn.space<global>>) -> !nn.memory<[B, C], [C, 1], f32, #nn.space<global>> {
    %1 = "nn.reduce_sum"(%0) {axes = [2 : i64], keepdim = false, space = #nn.space<global>} : (!nn.memory<[B, C, W], [C*W, W, 1], f32, #nn.space<global>>) -> !nn.memory<[B, C], [C, 1], f32, #nn.space<global>>
    func.return %1 : !nn.memory<[B, C], [C, 1], f32, #nn.space<global>>
  }
}'''

CASE_4_RUNTIME_ARGS = (
    Memory([SymbolDim('B'), SymbolDim('C'), SymbolDim('W')], NumericType.Float32, space=MemorySpace.GM),
)

def reduce_sum_kernel_case_4(src):
    return reduce_sum(src, axis=2, keepdim=False)

# CASE-5 描述：失败例子：`reduce_sum(src, axis=3, keepdim=True)` 的 axis 超出 rank 时应在构造阶段拒绝。
CASE_5_RUNTIME_ARGS = (
    Memory([2, 3, 4], NumericType.Float32, space=MemorySpace.GM),
)

def reduce_sum_kernel_case_5(src):
    return reduce_sum(src, axis=3, keepdim=True)

def _case_1_true() -> None:
    print('[CASE-1] 静态正向例子：reduce_sum(src, axis=1, keepdim=True) -> nn.reduce_sum')
    ok = mlir_gen_compare_text(fn=reduce_sum_kernel_case_1, runtime_args=CASE_1_RUNTIME_ARGS, config=None, mlir_text=CASE_1_IR)
    assert ok is True

def _case_2_true() -> None:
    print('[CASE-2] 动态正向例子：reduce_sum(src, axis=1, keepdim=True) symbol shape -> nn.reduce_sum')
    ok = mlir_gen_compare_text(fn=reduce_sum_kernel_case_2, runtime_args=CASE_2_RUNTIME_ARGS, config=None, mlir_text=CASE_2_IR)
    assert ok is True

def _case_3_true() -> None:
    print('[CASE-3] 静态正向例子：reduce_sum(src, axis=1, keepdim=False) -> nn.reduce_sum')
    ok = mlir_gen_compare_text(fn=reduce_sum_kernel_case_3, runtime_args=CASE_3_RUNTIME_ARGS, config=None, mlir_text=CASE_3_IR)
    assert ok is True

def _case_4_true() -> None:
    print('[CASE-4] 动态正向例子：reduce_sum(src, axis=2, keepdim=False) symbol shape -> nn.reduce_sum')
    ok = mlir_gen_compare_text(fn=reduce_sum_kernel_case_4, runtime_args=CASE_4_RUNTIME_ARGS, config=None, mlir_text=CASE_4_IR)
    assert ok is True

def _case_5_reject_axis_out_of_range() -> None:
    print('[CASE-5] 失败例子：reduce_sum(src, axis=3, keepdim=True) 的 axis 超出 rank 时应在构造阶段拒绝')
    try:
        mlir_gen_compare_text(fn=reduce_sum_kernel_case_5, runtime_args=CASE_5_RUNTIME_ARGS, config=None, mlir_text=CASE_1_IR)
    except VerifyException as exc:
        assert 'axes-must-be-non-empty-unique-and-in-range' in str(exc)
    else:
        raise AssertionError('reduce_sum with out-of-range axis should be rejected before MLIR compare')

def main() -> None:
    failures: list[tuple[str, BaseException]] = []
    run_case(failures, 'CASE-1', _case_1_true)
    run_case(failures, 'CASE-2', _case_2_true)
    run_case(failures, 'CASE-3', _case_3_true)
    run_case(failures, 'CASE-4', _case_4_true)
    run_case(failures, 'CASE-5', _case_5_reject_axis_out_of_range)
    raise_if_failures('dsl mlir_gen nn reduce expectation', failures)


if __name__ == '__main__':
    main()
