"""mlir_gen signature tests.

创建者: 朽木露琪亚
最后一次更改: 朽木露琪亚

功能说明:
- 覆盖签名推导与符号表达式解析的基础路径。

当前覆盖率信息:
- 当前覆盖率: 未统计（本任务验证未启用 coverage 统计）。
- 达标判定: 待后续补充统计结果。

覆盖率命令:
- pytest -q --cov=kernel_gen.dsl.mlir_gen.signature --cov-branch --cov-report=term-missing test/dsl/mlir_gen/test_signature.py

使用示例:
- pytest -q test/dsl/mlir_gen/test_signature.py

关联文件:
- 功能实现: kernel_gen/dsl/mlir_gen/signature.py
- Spec 文档: spec/dsl/mlir_gen.md
- 测试文件: test/dsl/mlir_gen/test_signature.py
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from kernel_gen.dialect.symbol import SymbolValueType
from kernel_gen.dsl.ast import parse_function
from kernel_gen.dsl.mlir_gen import _build_signature_types
from kernel_gen.dsl.mlir_gen.signature import _parse_symbolic_dim_expr
from kernel_gen.symbol_variable.symbol_dim import SymbolDim


# TC-MLIR-GEN-SIG-001
# 创建者: 朽木露琪亚
# 最后一次更改: 朽木露琪亚
# 最近一次运行测试时间: 未运行
# 最近一次运行成功时间: 未运行
# 测试目的: runtime_args 为 SymbolDim 时参数类型必须落在 SymbolValueType。
# 对应功能实现文件路径: kernel_gen/dsl/mlir_gen/signature.py
# 对应 spec 文件路径: spec/dsl/mlir_gen.md
# 示例: pytest -q test/dsl/mlir_gen/test_signature.py -k test_build_signature_types_symbol_dim
def test_build_signature_types_symbol_dim() -> None:
    def kernel(s: "int") -> "int":
        return s

    func_ast = parse_function(kernel)
    arg_types, type_map = _build_signature_types(func_ast, runtime_args=[SymbolDim("S")])
    assert len(arg_types) == 1
    assert isinstance(arg_types[0], SymbolValueType)
    assert any(isinstance(value, SymbolValueType) for value in type_map.values())


# TC-MLIR-GEN-SIG-002
# 创建者: 朽木露琪亚
# 最后一次更改: 朽木露琪亚
# 最近一次运行测试时间: 未运行
# 最近一次运行成功时间: 未运行
# 测试目的: 符号表达式解析应返回可用的 sympy 表达式。
# 对应功能实现文件路径: kernel_gen/dsl/mlir_gen/signature.py
# 对应 spec 文件路径: spec/dsl/mlir_gen.md
# 示例: pytest -q test/dsl/mlir_gen/test_signature.py -k test_parse_symbolic_dim_expr
def test_parse_symbolic_dim_expr() -> None:
    assert _parse_symbolic_dim_expr("M*N") is not None
