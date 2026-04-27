"""mlir_gen module builder tests.

创建者: 朽木露琪亚
最后一次更改: 朽木露琪亚

功能说明:
- 覆盖 module 组装与 callee 收集的基础行为。

当前覆盖率信息:
- 当前覆盖率: 未统计（本任务验证未启用 coverage 统计）。
- 达标判定: 待后续补充统计结果。

覆盖率命令:
- pytest -q --cov=kernel_gen.dsl.mlir_gen.module_builder --cov-branch --cov-report=term-missing test/dsl/mlir_gen/test_module_builder.py

使用示例:
- pytest -q test/dsl/mlir_gen/test_module_builder.py

关联文件:
- 功能实现: kernel_gen/dsl/mlir_gen/module_builder.py
- Spec 文档: spec/dsl/mlir_gen.md
- 测试文件: test/dsl/mlir_gen/test_module_builder.py
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest
from xdsl.dialects import func
from xdsl.dialects.builtin import ArrayAttr, IntAttr, StringAttr, f32, i32

REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from kernel_gen.dialect.nn import NnMemorySpaceAttr, NnMemoryType
from kernel_gen.dialect.symbol import SymbolValueType
from kernel_gen.dsl.ast.visitor import AstVisitorError
from kernel_gen.dsl.mlir_gen import MlirGenModuleError, mlir_gen
from kernel_gen.operation.arch import get_dynamic_memory
from kernel_gen.symbol_variable.memory import Memory
from kernel_gen.symbol_variable.memory import MemorySpace
from kernel_gen.symbol_variable.symbol_dim import SymbolDim
from kernel_gen.symbol_variable.type import NumericType


def _memory_type(
    shape: list[int | str],
    stride: list[int | str],
    *,
    space: str = "global",
) -> NnMemoryType:
    def _attr(value: int | str) -> IntAttr | StringAttr:
        if isinstance(value, int):
            return IntAttr(value)
        return StringAttr(value)

    return NnMemoryType(
        ArrayAttr([_attr(dim) for dim in shape]),
        ArrayAttr([_attr(dim) for dim in stride]),
        f32,
        NnMemorySpaceAttr.from_name(space),
    )


# TC-MLIR-GEN-MOD-001
# 创建者: 朽木露琪亚
# 最后一次更改: 朽木露琪亚
# 最近一次运行测试时间: 未运行
# 最近一次运行成功时间: 未运行
# 测试目的: module 需包含 root 与 callee func.func。
# 对应功能实现文件路径: kernel_gen/dsl/mlir_gen/module_builder.py
# 对应 spec 文件路径: spec/dsl/mlir_gen.md
# 示例: pytest -q test/dsl/mlir_gen/test_module_builder.py -k test_mlir_gen_collects_callee
def test_mlir_gen_collects_callee() -> None:
    def helper(x: "Tensor[f32, 4]") -> "Tensor[f32, 4]":
        return x

    def main(x: "Tensor[f32, 4]") -> "Tensor[f32, 4]":
        return helper(x)

    module = mlir_gen(main, Memory([4], NumericType.Float32))
    func_names = [
        op.sym_name.data for op in module.ops if isinstance(op, func.FuncOp) and hasattr(op, "sym_name")
    ]
    assert func_names[:2] == ["main", "helper"]


def test_mlir_gen_callee_signature_tracks_public_runtime_types() -> None:
    def helper(x: "Tensor[f32, 2, 3]", sym: int, count: int) -> "Tensor[f32, 2, 3]":
        return x

    def main(x: "Tensor[f32, 2, 3]", sym: int, count: int) -> "Tensor[f32, 2, 3]":
        return helper(x, sym, count)

    module = mlir_gen(main, Memory([2, 3], NumericType.Float32), SymbolDim("M"), 7)
    helper_op = next(op for op in module.ops if isinstance(op, func.FuncOp) and op.sym_name.data == "helper")

    assert list(helper_op.function_type.inputs) == [
        _memory_type([2, 3], [3, 1]),
        SymbolValueType.from_expr("M"),
        i32,
    ]


def test_mlir_gen_rejects_unsupported_closure_callee() -> None:
    def _make_closure():
        captured = 1

        def helper(x: "Tensor[f32, 4]") -> "Tensor[f32, 4]":
            return x + captured

        return helper

    closure = _make_closure()

    def main(x: "Tensor[f32, 4]") -> "Tensor[f32, 4]":
        return closure(x)

    with pytest.raises(MlirGenModuleError, match="unsupported callee function"):
        mlir_gen(main, Memory([4], NumericType.Float32))


def test_mlir_gen_rejects_invalid_dynamic_memory_in_root_and_callee() -> None:
    def bad_helper() -> "Tensor[i8, ?]":
        return get_dynamic_memory(MemorySpace.GM)

    def main_with_bad_callee() -> "Tensor[i8, ?]":
        return bad_helper()

    def bad_root() -> "Tensor[i8, ?]":
        return get_dynamic_memory(MemorySpace.GM)

    with pytest.raises(ValueError, match="get_dynamic_memory space must be on-chip MemorySpace"):
        mlir_gen(main_with_bad_callee)
    with pytest.raises(ValueError, match="get_dynamic_memory space must be on-chip MemorySpace"):
        mlir_gen(bad_root)


def test_mlir_gen_reuses_existing_callee_registry_entry() -> None:
    def helper(x: "Tensor[f32, 4]") -> "Tensor[f32, 4]":
        return x

    def main(x: "Tensor[f32, 4]") -> "Tensor[f32, 4]":
        y = helper(x)
        return helper(y)

    module = mlir_gen(main, Memory([4], NumericType.Float32))
    func_names = [op.sym_name.data for op in module.ops if isinstance(op, func.FuncOp)]
    assert func_names == ["main", "helper"]
