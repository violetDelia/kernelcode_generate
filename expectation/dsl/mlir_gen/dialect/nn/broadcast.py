"""DSL nn.broadcast expectation.

创建者: 大闸蟹
最后一次更改: 小李飞刀

功能说明:
- 演示 `dsl/mlir_gen` expectation 如何直接使用 `mlir_gen_compare_text(...)` 比较完整 `builtin.module`。
- 锁定 `broadcast(source, target)` 的目标公开合同：应生成显式 `nn.broadcast`。

使用示例:
- `PYTHONPATH=. python expectation/dsl/mlir_gen/dialect/nn/broadcast.py`

关联文件:
- spec: [`spec/dsl/mlir_gen.md`](spec/dsl/mlir_gen.md)
- spec: [`spec/dialect/nn.md`](spec/dialect/nn.md)
- spec: [`spec/operation/nn.md`](spec/operation/nn.md)
- spec: [`spec/tools/mlir_gen_compare.md`](spec/tools/mlir_gen_compare.md)
- test: [`test/dsl/test_mlir_gen.py`](test/dsl/test_mlir_gen.py)
- test: [`test/tools/test_mlir_gen_compare.py`](test/tools/test_mlir_gen_compare.py)
- 功能实现: [`kernel_gen/dsl/mlir_gen/__init__.py`](kernel_gen/dsl/mlir_gen/__init__.py)
- 功能实现: [`kernel_gen/tools/mlir_gen_compare.py`](kernel_gen/tools/mlir_gen_compare.py)
"""

# Case 列表:
# - CASE-1: 静态正向例子：`broadcast(source, target)` 的静态输入应生成显式 `nn.broadcast`。
# - CASE-2: 动态正向例子：`broadcast(source, target)` 的 symbol shape 输入应生成显式 `nn.broadcast`。
# - CASE-3: 失败例子：`broadcast(source, target)` 的维度不兼容时应在构造阶段拒绝。

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
from kernel_gen.operation.nn import broadcast
from kernel_gen.symbol_variable.memory import Memory, MemorySpace
from kernel_gen.symbol_variable.symbol_dim import SymbolDim
from kernel_gen.symbol_variable.type import Farmat, NumericType
from kernel_gen.tools.mlir_gen_compare import mlir_gen_compare_text

# CASE-1 IR：静态正向例子：`broadcast(source, target)` 的静态输入应生成显式 `nn.broadcast`。
CASE_1_IR = """builtin.module {
  func.func @broadcast_kernel_case_1(%0 : !nn.memory<[1, 4], [4, 1], f32, #nn.space<shared>>, %1 : !nn.memory<[3, 4], [4, 1], f32, #nn.space<local>>) -> !nn.memory<[3, 4], [4, 1], f32, #nn.space<local>> {
    %2 = "nn.broadcast"(%0) {space = #nn.space<local>} : (!nn.memory<[1, 4], [4, 1], f32, #nn.space<shared>>) -> !nn.memory<[3, 4], [4, 1], f32, #nn.space<local>>
    func.return %2 : !nn.memory<[3, 4], [4, 1], f32, #nn.space<local>>
  }
}"""

CASE_1_RUNTIME_ARGS = (
    Memory([1, 4], NumericType.Float32, space=MemorySpace.SM, format=Farmat.CLast),
    Memory([3, 4], NumericType.Float32, space=MemorySpace.LM, format=Farmat.Norm),
)

# broadcast_kernel_case_1
# 创建者: 大闸蟹
# 最后一次更改: 小李飞刀
# 功能说明:
# - 提供 `broadcast(value, target)` 的静态 shape DSL 函数体，验证结果空间与目标内存空间保持一致。
# 使用示例:
# - `mlir_gen_compare_text(fn=broadcast_kernel_case_1, runtime_args=CASE_1_RUNTIME_ARGS, config=None, mlir_text=CASE_1_IR)`
# 关联文件:
# - spec: [`spec/dialect/nn.md`](spec/dialect/nn.md)
# - test: [`test/dsl/test_mlir_gen.py`](test/dsl/test_mlir_gen.py)
# - 功能实现: [`expectation/dsl/mlir_gen/dialect/nn/broadcast.py`](expectation/dsl/mlir_gen/dialect/nn/broadcast.py)
# - 功能实现: [`kernel_gen/operation/nn.py`](kernel_gen/operation/nn.py)
def broadcast_kernel_case_1(value, target):
    return broadcast(value, target)

# CASE-2 IR：动态正向例子：`broadcast(source, target)` 的 symbol shape 输入应生成显式 `nn.broadcast`。
CASE_2_IR = """builtin.module {
  func.func @broadcast_kernel_case_2(%0 : !nn.memory<[1, K], [K, 1], f32, #nn.space<shared>>, %1 : !nn.memory<[M, K], [K, 1], f32, #nn.space<local>>) -> !nn.memory<[M, K], [K, 1], f32, #nn.space<local>> {
    %2 = "nn.broadcast"(%0) {space = #nn.space<local>} : (!nn.memory<[1, K], [K, 1], f32, #nn.space<shared>>) -> !nn.memory<[M, K], [K, 1], f32, #nn.space<local>>
    func.return %2 : !nn.memory<[M, K], [K, 1], f32, #nn.space<local>>
  }
}"""

CASE_2_RUNTIME_ARGS = (
    Memory([1, SymbolDim("K")], NumericType.Float32, space=MemorySpace.SM, format=Farmat.CLast),
    Memory([SymbolDim("M"), SymbolDim("K")], NumericType.Float32, space=MemorySpace.LM, format=Farmat.Norm),
)

# broadcast_kernel_case_2
# 创建者: 大闸蟹
# 最后一次更改: 小李飞刀
# 功能说明:
# - 提供 symbol 维度输入的 `broadcast(value, target)` DSL 函数体，验证动态 shape 下仍生成 `nn.broadcast`。
# 使用示例:
# - `mlir_gen_compare_text(fn=broadcast_kernel_case_2, runtime_args=CASE_2_RUNTIME_ARGS, config=None, mlir_text=CASE_2_IR)`
# 关联文件:
# - spec: [`spec/dialect/nn.md`](spec/dialect/nn.md)
# - test: [`test/dsl/test_mlir_gen.py`](test/dsl/test_mlir_gen.py)
# - 功能实现: [`expectation/dsl/mlir_gen/dialect/nn/broadcast.py`](expectation/dsl/mlir_gen/dialect/nn/broadcast.py)
# - 功能实现: [`kernel_gen/operation/nn.py`](kernel_gen/operation/nn.py)
def broadcast_kernel_case_2(value, target):
    return broadcast(value, target)

# CASE-3 描述：失败例子：`broadcast(source, target)` 的维度不兼容时应在构造阶段拒绝。
CASE_3_RUNTIME_ARGS = (
    Memory([2, 4], NumericType.Float32, space=MemorySpace.SM, format=Farmat.CLast),
    Memory([3, 5], NumericType.Float32, space=MemorySpace.LM, format=Farmat.Norm),
)

# broadcast_kernel_case_3
# 创建者: 大闸蟹
# 最后一次更改: 小李飞刀
# 功能说明:
# - 提供维度不兼容的 `broadcast(value, target)` DSL 函数体，用于验证构造阶段会直接拒绝。
# 使用示例:
# - `mlir_gen_compare_text(fn=broadcast_kernel_case_3, runtime_args=CASE_3_RUNTIME_ARGS, config=None, mlir_text=CASE_1_IR)`
# 关联文件:
# - spec: [`spec/dialect/nn.md`](spec/dialect/nn.md)
# - test: [`test/dsl/test_mlir_gen.py`](test/dsl/test_mlir_gen.py)
# - 功能实现: [`expectation/dsl/mlir_gen/dialect/nn/broadcast.py`](expectation/dsl/mlir_gen/dialect/nn/broadcast.py)
# - 功能实现: [`kernel_gen/operation/nn.py`](kernel_gen/operation/nn.py)
def broadcast_kernel_case_3(value, target):
    return broadcast(value, target)


def _case_1_true():
    """断言静态 shape 的 `broadcast` 文本合同成立。

    创建者: 大闸蟹
    最后一次更改: 小李飞刀

    功能说明:
    - 打印 CASE-1 说明并校验静态 `broadcast` 样例的完整 IR 文本。

    使用示例:
    - `_case_1_true()`

    关联文件:
    - spec: [`spec/tools/mlir_gen_compare.md`](spec/tools/mlir_gen_compare.md)
    - test: [`test/tools/test_mlir_gen_compare.py`](test/tools/test_mlir_gen_compare.py)
    - 功能实现: [`expectation/dsl/mlir_gen/dialect/nn/broadcast.py`](expectation/dsl/mlir_gen/dialect/nn/broadcast.py)
    - 功能实现: [`kernel_gen/tools/mlir_gen_compare.py`](kernel_gen/tools/mlir_gen_compare.py)
    """

    print("[CASE-1] 静态正向例子：broadcast(source, target) -> nn.broadcast")
    ok = mlir_gen_compare_text(fn=broadcast_kernel_case_1, runtime_args=CASE_1_RUNTIME_ARGS, config=None, mlir_text=CASE_1_IR)
    assert ok is True, "expected mlir_gen_compare_text(...) to return True for static broadcast module text"


def _case_2_true():
    """断言 symbol shape 的 `broadcast` 文本合同成立。

    创建者: 大闸蟹
    最后一次更改: 小李飞刀

    功能说明:
    - 打印 CASE-2 说明并校验动态维度 `broadcast` 样例的完整 IR 文本。

    使用示例:
    - `_case_2_true()`

    关联文件:
    - spec: [`spec/tools/mlir_gen_compare.md`](spec/tools/mlir_gen_compare.md)
    - test: [`test/tools/test_mlir_gen_compare.py`](test/tools/test_mlir_gen_compare.py)
    - 功能实现: [`expectation/dsl/mlir_gen/dialect/nn/broadcast.py`](expectation/dsl/mlir_gen/dialect/nn/broadcast.py)
    - 功能实现: [`kernel_gen/tools/mlir_gen_compare.py`](kernel_gen/tools/mlir_gen_compare.py)
    """

    print("[CASE-2] 动态正向例子：broadcast(source, target) symbol shape -> nn.broadcast")
    ok = mlir_gen_compare_text(fn=broadcast_kernel_case_2, runtime_args=CASE_2_RUNTIME_ARGS, config=None, mlir_text=CASE_2_IR)
    assert ok is True, "expected mlir_gen_compare_text(...) to return True for dynamic broadcast module text"


def _case_3_reject_dimension_mismatch():
    """断言维度不兼容的 `broadcast` 会在构造阶段被拒绝。

    创建者: 大闸蟹
    最后一次更改: 小李飞刀

    功能说明:
    - 打印 CASE-3 说明并验证不兼容维度不会进入正常 IR 对比流程。

    使用示例:
    - `_case_3_reject_dimension_mismatch()`

    关联文件:
    - spec: [`spec/dialect/nn.md`](spec/dialect/nn.md)
    - test: [`test/dsl/test_ast_visitor.py`](test/dsl/test_ast_visitor.py)
    - 功能实现: [`expectation/dsl/mlir_gen/dialect/nn/broadcast.py`](expectation/dsl/mlir_gen/dialect/nn/broadcast.py)
    - 功能实现: [`kernel_gen/operation/nn.py`](kernel_gen/operation/nn.py)
    """

    print("[CASE-3] 失败例子：broadcast(source, target) 的维度不兼容时应在构造阶段拒绝")
    try:
        mlir_gen_compare_text(fn=broadcast_kernel_case_3, runtime_args=CASE_3_RUNTIME_ARGS, config=None, mlir_text=CASE_1_IR)
    except ValueError as exc:
        assert "broadcast dimension mismatch" in str(exc)
    else:
        raise AssertionError("broadcast with incompatible dimensions should be rejected before MLIR compare")


def main():
    """运行 `nn.broadcast` expectation 的全部公开 case。

    创建者: 大闸蟹
    最后一次更改: 小李飞刀

    功能说明:
    - 顺序执行静态 shape、symbol shape 和维度不兼容三类 `broadcast` 合同样例。
    - 汇总失败 case，并通过共享 runner 输出统一错误摘要。

    使用示例:
    - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python expectation/dsl/mlir_gen/dialect/nn/broadcast.py`

    关联文件:
    - spec: [`spec/dialect/nn.md`](spec/dialect/nn.md)
    - test: [`test/dsl/test_mlir_gen.py`](test/dsl/test_mlir_gen.py)
    - 功能实现: [`expectation/dsl/mlir_gen/dialect/nn/broadcast.py`](expectation/dsl/mlir_gen/dialect/nn/broadcast.py)
    - 功能实现: [`expectation/utils/case_runner.py`](expectation/utils/case_runner.py)
    """

    failures: list[tuple[str, BaseException]] = []
    run_case(failures, "CASE-1", _case_1_true)
    run_case(failures, "CASE-2", _case_2_true)
    run_case(failures, "CASE-3", _case_3_reject_dimension_mismatch)
    raise_if_failures("dsl mlir_gen nn broadcast expectation", failures)


if __name__ == "__main__":
    main()
