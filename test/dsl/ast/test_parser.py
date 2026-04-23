"""DSL AST parser tests.

创建者: 小李飞刀
最后一次更改: 小李飞刀

功能说明:
- 覆盖 `parse_function` 的基础解析、for 循环、常量与 helper 入口。
- 覆盖 `for range(..., step=0)` 在解析阶段直接报错。

当前覆盖率信息:
- 当前覆盖率: 未统计（本任务验证未启用 coverage 统计）。
- 达标判定: 待后续补充统计结果。

覆盖率命令:
- `pytest -q --cov=kernel_gen.dsl.ast.parser --cov-branch --cov-report=term-missing test/dsl/ast/test_parser.py`

使用示例:
- pytest -q test/dsl/ast/test_parser.py

关联文件:
- 功能实现: kernel_gen/dsl/ast/parser.py
- Spec 文档: spec/dsl/ast.md
- 测试文件: test/dsl/ast/test_parser.py
"""

from __future__ import annotations

import ast as py_ast
import importlib
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from kernel_gen.dsl.ast import (
    ConstAST,
    ForAST,
    FunctionAST,
    NnUnaryAST,
    parse_function,
)
from kernel_gen.dsl.ast.parser import AstParseError
from kernel_gen.symbol_variable.memory import Memory
from kernel_gen.symbol_variable.symbol_dim import SymbolDim
from kernel_gen.symbol_variable.type import NumericType

parser_module = importlib.import_module("kernel_gen.dsl.ast.parser")


# AST-S1-P-001
# 创建者: 小李飞刀
# 最后一次更改: 小李飞刀
# 最近一次运行测试时间: 2026-04-13 03:10:00 +0800
# 最近一次运行成功时间: 2026-04-13 03:10:00 +0800
# 功能说明: 解析基础赋值函数并生成 FunctionAST。
# 使用示例: pytest -q test/dsl/ast/test_parser.py -k test_parse_function_basic_assignment
# 对应功能实现文件路径: kernel_gen/dsl/ast/parser.py
# 对应 spec 文件路径: spec/dsl/ast.md
# 对应测试文件路径: test/dsl/ast/test_parser.py
def test_parse_function_basic_assignment() -> None:
    def copy_kernel(x: "Tensor[f32, 1]"):
        y = x
        return y

    func_ast = parse_function(copy_kernel)
    assert isinstance(func_ast, FunctionAST)
    assert func_ast.name == "copy_kernel"
    assert func_ast.has_explicit_return is True


# AST-S1-P-002
# 创建者: 小李飞刀
# 最后一次更改: 小李飞刀
# 最近一次运行测试时间: 2026-04-13 03:10:00 +0800
# 最近一次运行成功时间: 2026-04-13 03:10:00 +0800
# 功能说明: 解析 for range(...) 语法并生成 ForAST。
# 使用示例: pytest -q test/dsl/ast/test_parser.py -k test_parse_function_for_loop
# 对应功能实现文件路径: kernel_gen/dsl/ast/parser.py
# 对应 spec 文件路径: spec/dsl/ast.md
# 对应测试文件路径: test/dsl/ast/test_parser.py
def test_parse_function_for_loop() -> None:
    def loop_kernel(x: "Tensor[f32, 1]"):
        for i in range(0, 4, 1):
            x = x
        return x

    func_ast = parse_function(loop_kernel)
    for_nodes = [node for node in func_ast.body.statements if isinstance(node, ForAST)]
    assert for_nodes, "expected ForAST in function body"
    step_node = for_nodes[0].step
    assert isinstance(step_node, ConstAST)
    assert step_node.value == 1


# AST-S1-P-003
# 创建者: 小李飞刀
# 最后一次更改: 小李飞刀
# 最近一次运行测试时间: 2026-04-13 03:10:00 +0800
# 最近一次运行成功时间: 2026-04-13 03:10:00 +0800
# 功能说明: 解析常量表达式并保留 ConstAST。
# 使用示例: pytest -q test/dsl/ast/test_parser.py -k test_parse_function_constant
# 对应功能实现文件路径: kernel_gen/dsl/ast/parser.py
# 对应 spec 文件路径: spec/dsl/ast.md
# 对应测试文件路径: test/dsl/ast/test_parser.py
def test_parse_function_constant() -> None:
    def const_kernel(x: "Tensor[f32, 1]"):
        y = 1
        return y

    func_ast = parse_function(const_kernel)
    assert any(isinstance(node, ConstAST) for node in func_ast.body.statements)


# AST-S1-P-004
# 创建者: 小李飞刀
# 最后一次更改: 小李飞刀
# 最近一次运行测试时间: 2026-04-13 03:10:00 +0800
# 最近一次运行成功时间: 2026-04-13 03:10:00 +0800
# 功能说明: 解析 helper 调用入口并生成相应 AST。
# 使用示例: pytest -q test/dsl/ast/test_parser.py -k test_parse_function_helper_call
# 对应功能实现文件路径: kernel_gen/dsl/ast/parser.py
# 对应 spec 文件路径: spec/dsl/ast.md
# 对应测试文件路径: test/dsl/ast/test_parser.py
def test_parse_function_helper_call() -> None:
    def helper_kernel(x: "Tensor[f32, 1]"):
        from kernel_gen.operation.nn import relu

        return relu(x)

    func_ast = parse_function(helper_kernel)
    assert any(isinstance(node, NnUnaryAST) for node in func_ast.body.statements)


# AST-S1-P-004A
# 创建者: 朽木露琪亚
# 最后一次更改: 朽木露琪亚
# 最近一次运行测试时间: 未运行
# 最近一次运行成功时间: 未运行
# 功能说明: 验证从 `kernel_gen.operation.nn` 直接导入到模块作用域的 helper alias 可被 parser 识别。
# 测试目的: 锁定 direct symbol alias 不依赖 helper 对象的 `__module__ == kernel_gen.operation.nn`，避免 `kernel_gen.operation._nn_*` 实现模块导致回退。
# 使用示例: pytest -q test/dsl/ast/test_parser.py -k test_parse_function_global_imported_nn_helper_call
# 对应功能实现文件路径: kernel_gen/dsl/ast/parser.py
# 对应 spec 文件路径: spec/dsl/ast.md
# 对应测试文件路径: test/dsl/ast/test_parser.py
def test_parse_function_global_imported_nn_helper_call(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from kernel_gen.operation.nn import relu

    def helper_kernel(x: "Tensor[f32, 1]"):
        return relu_alias(x)

    monkeypatch.setitem(helper_kernel.__globals__, "relu_alias", relu)

    func_ast = parse_function(helper_kernel)
    assert any(isinstance(node, NnUnaryAST) for node in func_ast.body.statements)


# AST-S1-P-005
# 创建者: 小李飞刀
# 最后一次更改: 小李飞刀
# 最近一次运行测试时间: 2026-04-13 03:10:00 +0800
# 最近一次运行成功时间: 2026-04-13 03:10:00 +0800
# 功能说明: `for range(..., step=0)` 在解析阶段直接报错。
# 使用示例: pytest -q test/dsl/ast/test_parser.py -k test_parse_function_step_zero_rejected
# 对应功能实现文件路径: kernel_gen/dsl/ast/parser.py
# 对应 spec 文件路径: spec/dsl/ast.md
# 对应测试文件路径: test/dsl/ast/test_parser.py
def test_parse_function_step_zero_rejected() -> None:
    def invalid_step_kernel(x: "Tensor[f32, 1]"):
        for i in range(0, 4, 0):
            x = x
        return x

    with pytest.raises(AstParseError, match="for range step must not be zero"):
        _ = parse_function(invalid_step_kernel)


# AST-S1-P-006
# 创建者: 金铲铲大作战
# 最后一次更改: 金铲铲大作战
# 功能说明: 覆盖 tensor 维度表达式与 Tensor 注解拆分 helper 的边界分支。
# 使用示例: pytest -q test/dsl/ast/test_parser.py -k test_parser_private_helpers_symbolic_dim_and_tensor_annotation
# 对应功能实现文件路径: kernel_gen/dsl/ast/parser.py
# 对应 spec 文件路径: spec/dsl/ast.md
# 对应测试文件路径: test/dsl/ast/test_parser.py
def test_parser_private_helpers_symbolic_dim_and_tensor_annotation() -> None:
    dim_expr = parser_module._eval_symbolic_dim_node(py_ast.parse("N + 1", mode="eval").body, None)
    neg_expr = parser_module._eval_symbolic_dim_expr("-N", None)
    div_expr = parser_module._eval_symbolic_dim_expr("8 / 2", None)

    assert isinstance(dim_expr, SymbolDim)
    assert str(dim_expr) == "N + 1"
    assert isinstance(neg_expr, SymbolDim)
    assert str(neg_expr) == "-N"
    assert div_expr == 4

    dtype, dims = parser_module._split_tensor_annotation('Tensor[f32, "M", N + 1, 2]', None)
    assert dtype is NumericType.Float32
    assert dims[0] == "M"
    assert isinstance(dims[1], SymbolDim)
    assert str(dims[1]) == "N + 1"
    assert dims[2] == 2

    with pytest.raises(parser_module._ParseFailure, match="Unsupported tensor dimension expression"):
        parser_module._eval_symbolic_dim_expr("N // 2", None)
    with pytest.raises(parser_module._ParseFailure, match="Tensor annotation missing dimensions"):
        parser_module._split_tensor_annotation("Tensor[f32]", None)
    with pytest.raises(parser_module._ParseFailure, match="Unsupported annotation"):
        parser_module._split_tensor_annotation("Vector[f32, 1]", None)


# AST-S1-P-007
# 创建者: 金铲铲大作战
# 最后一次更改: 金铲铲大作战
# 功能说明: 覆盖注解解析、PEP604 联合注解与安全 import 绑定 helper。
# 使用示例: pytest -q test/dsl/ast/test_parser.py -k test_parser_private_helpers_annotation_resolution_and_import_binding
# 对应功能实现文件路径: kernel_gen/dsl/ast/parser.py
# 对应 spec 文件路径: spec/dsl/ast.md
# 对应测试文件路径: test/dsl/ast/test_parser.py
def test_parser_private_helpers_annotation_resolution_and_import_binding(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    memory = Memory([SymbolDim("M")], NumericType.Float32)
    globals_table = {"A": memory}
    builtins_table = {"float": float}
    runtime_table = {"x": memory, "n": SymbolDim("N")}

    assert parser_module._parse_annotation_node(None, None, globals_table, builtins_table) is None

    inferred_runtime = parser_module._parse_annotation_node(
        None,
        "x",
        globals_table,
        builtins_table,
        runtime_table,
    )
    assert inferred_runtime is not None
    assert inferred_runtime.name == "x"

    scalar_union = parser_module._parse_annotation_node(
        py_ast.parse("int | SymbolDim", mode="eval").body,
        "n",
        globals_table,
        builtins_table,
    )
    assert scalar_union is not None
    assert scalar_union.name == "n"
    assert getattr(scalar_union, "is_symbolic", False) is True

    return_float = parser_module._parse_annotation_node(
        py_ast.parse("float", mode="eval").body,
        None,
        globals_table,
        builtins_table,
    )
    assert return_float is not None
    assert return_float.name == "ret0"
    assert return_float.value_type is float

    tensor_arg = parser_module._parse_annotation_node(
        py_ast.parse("Tensor[f32, M]", mode="eval").body,
        "arg0",
        globals_table,
        builtins_table,
    )
    assert tensor_arg is not None
    assert tensor_arg.name == "arg0"
    assert tensor_arg.memory == memory

    from kernel_gen.operation.nn import add, relu

    monkeypatch.setitem(globals_table, "relu_alias", relu)
    monkeypatch.setitem(globals_table, "nn_mod", importlib.import_module("kernel_gen.operation.nn"))
    assert (
        parser_module._resolve_import_bound_helper_call(
            py_ast.parse("relu_alias", mode="eval").body,
            globals_table,
            builtins_table,
        )
        == "relu"
    )
    assert (
        parser_module._resolve_import_bound_helper_call(
            py_ast.parse("nn_mod.add", mode="eval").body,
            globals_table,
            builtins_table,
        )
        == "add"
    )
    assert (
        parser_module._resolve_import_bound_helper_call(
            py_ast.parse("collections.deque", mode="eval").body,
            globals_table,
            builtins_table,
        )
        is None
    )

    local_globals: dict[str, object] = {}
    parser_module._bind_safe_local_import(
        py_ast.parse("import kernel_gen.operation.nn as nn_ops").body[0],
        local_globals,
    )
    assert local_globals["nn_ops"] is importlib.import_module("kernel_gen.operation.nn")
    parser_module._bind_safe_local_import(
        py_ast.parse("from kernel_gen.operation.nn import add as nn_add").body[0],
        local_globals,
    )
    assert local_globals["nn_add"] is add
    parser_module._bind_safe_local_import(
        py_ast.parse("import collections as collections_alias").body[0],
        local_globals,
    )
    assert local_globals["collections_alias"] is parser_module._LOCAL_IMPORT_SHADOW
