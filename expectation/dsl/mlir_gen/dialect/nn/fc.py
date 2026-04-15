"""DSL nn.fc expectation.

创建者: 大闸蟹
最后一次更改: 守护最好的爱莉希雅

功能说明:
- 演示 `dsl/mlir_gen` expectation 如何直接使用 `mlir_gen_compare_text(...)` 比较完整 `builtin.module`。
- 锁定 `fc(value, weight)` 的目标公开合同：应生成 `nn.transpose + nn.matmul` 链路。

使用示例:
- `PYTHONPATH=. python expectation/dsl/mlir_gen/dialect/nn/fc.py`

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
# - CASE-1: 静态正向例子：`fc(value, weight)` 的静态输入应生成 `nn.transpose + nn.matmul`。
# - CASE-2: 动态正向例子：`fc(value, weight)` 的 symbol shape 输入应生成 `nn.transpose + nn.matmul`。
# - CASE-3: 失败例子：`fc(value, weight)` 的输入特征维不匹配时应在构造阶段拒绝。

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
from kernel_gen.operation.nn import fc
from kernel_gen.symbol_variable.memory import Memory, MemorySpace
from kernel_gen.symbol_variable.symbol_dim import SymbolDim
from kernel_gen.symbol_variable.type import NumericType
from kernel_gen.tools.mlir_gen_compare import mlir_gen_compare_text
from xdsl.utils.exceptions import VerifyException

# CASE-1 IR：静态正向例子：`fc(value, weight)` 的静态输入应生成 `nn.transpose + nn.matmul`。
CASE_1_IR = """builtin.module {
  func.func @fc_kernel_case_1(%0 : !nn.memory<[2, 3], [3, 1], f32, #nn.space<global>>, %1 : !nn.memory<[4, 3], [3, 1], f32, #nn.space<global>>) -> !nn.memory<[2, 4], [4, 1], f32, #nn.space<global>> {
    %2 = "nn.transpose"(%1) {perm = [#builtin.int<1>, #builtin.int<0>], space = #nn.space<global>} : (!nn.memory<[4, 3], [3, 1], f32, #nn.space<global>>) -> !nn.memory<[3, 4], [1, 3], f32, #nn.space<global>>
    %3 = "nn.matmul"(%0, %2) {space = #nn.space<global>} : (!nn.memory<[2, 3], [3, 1], f32, #nn.space<global>>, !nn.memory<[3, 4], [1, 3], f32, #nn.space<global>>) -> !nn.memory<[2, 4], [4, 1], f32, #nn.space<global>>
    func.return %3 : !nn.memory<[2, 4], [4, 1], f32, #nn.space<global>>
  }
}"""

CASE_1_RUNTIME_ARGS = (
    Memory([2, 3], NumericType.Float32, space=MemorySpace.GM),
    Memory([4, 3], NumericType.Float32, space=MemorySpace.GM),
)

def fc_kernel_case_1(value, weight):
    return fc(value, weight)

# CASE-2 IR：动态正向例子：`fc(value, weight)` 的 symbol shape 输入应生成 `nn.transpose + nn.matmul`。
CASE_2_IR = """builtin.module {
  func.func @fc_kernel_case_2(%0 : !nn.memory<[B, K], [K, 1], f32, #nn.space<global>>, %1 : !nn.memory<[N, K], [K, 1], f32, #nn.space<global>>) -> !nn.memory<[B, N], [N, 1], f32, #nn.space<global>> {
    %2 = "nn.transpose"(%1) {perm = [#builtin.int<1>, #builtin.int<0>], space = #nn.space<global>} : (!nn.memory<[N, K], [K, 1], f32, #nn.space<global>>) -> !nn.memory<[K, N], [1, K], f32, #nn.space<global>>
    %3 = "nn.matmul"(%0, %2) {space = #nn.space<global>} : (!nn.memory<[B, K], [K, 1], f32, #nn.space<global>>, !nn.memory<[K, N], [1, K], f32, #nn.space<global>>) -> !nn.memory<[B, N], [N, 1], f32, #nn.space<global>>
    func.return %3 : !nn.memory<[B, N], [N, 1], f32, #nn.space<global>>
  }
}"""

CASE_2_RUNTIME_ARGS = (
    Memory([SymbolDim("B"), SymbolDim("K")], NumericType.Float32, space=MemorySpace.GM),
    Memory([SymbolDim("N"), SymbolDim("K")], NumericType.Float32, space=MemorySpace.GM),
)

def fc_kernel_case_2(value, weight):
    return fc(value, weight)

# CASE-3 描述：失败例子：`fc(value, weight)` 的输入特征维不匹配时应在构造阶段拒绝。
CASE_3_RUNTIME_ARGS = (
    Memory([2, 3], NumericType.Float32, space=MemorySpace.GM),
    Memory([4, 5], NumericType.Float32, space=MemorySpace.GM),
)

def fc_kernel_case_3(value, weight):
    return fc(value, weight)


def _case_1_true():
    print("[CASE-1] 静态正向例子：fc(value, weight) -> nn.transpose + nn.matmul")
    ok = mlir_gen_compare_text(fn=fc_kernel_case_1, runtime_args=CASE_1_RUNTIME_ARGS, config=None, mlir_text=CASE_1_IR)
    assert ok is True, "expected mlir_gen_compare_text(...) to return True for static fc module text"


def _case_2_true():
    print("[CASE-2] 动态正向例子：fc(value, weight) symbol shape -> nn.transpose + nn.matmul")
    ok = mlir_gen_compare_text(fn=fc_kernel_case_2, runtime_args=CASE_2_RUNTIME_ARGS, config=None, mlir_text=CASE_2_IR)
    assert ok is True, "expected mlir_gen_compare_text(...) to return True for dynamic fc module text"


def _case_3_reject_feature_mismatch():
    print("[CASE-3] 失败例子：fc(value, weight) 的输入特征维不匹配时应在构造阶段拒绝")
    try:
        mlir_gen_compare_text(fn=fc_kernel_case_3, runtime_args=CASE_3_RUNTIME_ARGS, config=None, mlir_text=CASE_1_IR)
    except VerifyException as exc:
        assert "nn.matmul contracting dimensions must match" in str(exc)
    else:
        raise AssertionError("fc with mismatched input feature dimension should be rejected before MLIR compare")


def main():
    failures: list[tuple[str, BaseException]] = []
    run_case(failures, "CASE-1", _case_1_true)
    run_case(failures, "CASE-2", _case_2_true)
    run_case(failures, "CASE-3", _case_3_reject_feature_mismatch)
    raise_if_failures("dsl mlir_gen nn fc expectation", failures)


if __name__ == "__main__":
    main()
