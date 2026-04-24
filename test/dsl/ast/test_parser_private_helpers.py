"""DSL AST parser private helper tests.

创建者: 金铲铲大作战
最后一次更改: 金铲铲大作战

功能说明:
- 覆盖 `kernel_gen.dsl.ast.parser` 的 annotation、import 绑定与 call 解析私有 helper。
- 重点锁定 `parse_function` 前置的维度表达式、张量注解与 helper 名解析边界。

使用示例:
- pytest -q test/dsl/ast/test_parser_private_helpers.py

关联文件:
- 功能实现: [kernel_gen/dsl/ast/parser.py](kernel_gen/dsl/ast/parser.py)
- Spec 文档: [spec/dsl/ast.md](spec/dsl/ast.md)
- 测试文件: [test/dsl/ast/test_parser_private_helpers.py](test/dsl/ast/test_parser_private_helpers.py)
"""

from __future__ import annotations

import ast as py_ast
import importlib
import inspect
import sys
import types
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

parser_module = importlib.import_module("kernel_gen.dsl.ast.parser")
from kernel_gen.dsl.ast import ScalarArgAST, SymbolToFloatAST, TensorAST
from kernel_gen.dsl.ast import (
    ArchLaunchKernelAST,
    BinaryExprAST,
    CompareExprAST,
    ConstAST,
    ForAST,
    LoadAST,
    NnReduceAST,
    NnSoftmaxAST,
    NnUnaryAST,
    PythonCalleeCallAST,
    StoreAST,
    TensorAxisAccessAST,
    VarAST,
)
from kernel_gen.symbol_variable.memory import Memory, MemorySpace
from kernel_gen.symbol_variable.symbol_dim import SymbolDim
from kernel_gen.symbol_variable.type import NumericType

_BUILTINS_TABLE = __builtins__ if isinstance(__builtins__, dict) else __builtins__.__dict__


# AST-PARSER-HELPER-001
# 创建者: 金铲铲大作战
# 最后一次更改: 金铲铲大作战
# 功能说明: 验证符号维度解析与 Tensor 注解拆分的基础分支。
# 使用示例: pytest -q test/dsl/ast/test_parser_private_helpers.py -k test_parser_private_helpers_symbolic_dim_and_tensor_annotation_contracts
# 对应功能实现文件路径: kernel_gen/dsl/ast/parser.py
# 对应 spec 文件路径: spec/dsl/ast.md
# 对应测试文件路径: test/dsl/ast/test_parser_private_helpers.py
def test_parser_private_helpers_symbolic_dim_and_tensor_annotation_contracts() -> None:
    assert parser_module._location_from_node(None) is None

    dummy_node = py_ast.parse("0", mode="eval").body
    location = parser_module._location_from_node(dummy_node)
    assert location is not None
    assert (location.line, location.column) == (1, 0)

    assert parser_module._eval_symbolic_dim_node(py_ast.parse("3", mode="eval").body, None) == 3

    symbolic_dim = parser_module._eval_symbolic_dim_node(py_ast.parse("N", mode="eval").body, None)
    assert isinstance(symbolic_dim, SymbolDim)
    assert str(symbolic_dim) == "N"

    neg_symbolic_dim = parser_module._eval_symbolic_dim_node(py_ast.parse("-N", mode="eval").body, None)
    assert isinstance(neg_symbolic_dim, SymbolDim)
    assert str(neg_symbolic_dim) == "-N"

    assert parser_module._eval_symbolic_dim_expr("8 / 2", None) == 4
    assert parser_module._eval_symbolic_dim_expr("N + 2", None) == SymbolDim("N") + 2

    with pytest.raises(parser_module._ParseFailure, match="Unsupported tensor dimension expression"):
        parser_module._eval_symbolic_dim_expr("8 / 3", None)

    with pytest.raises(parser_module._ParseFailure, match="Unsupported tensor dimension expression"):
        parser_module._eval_symbolic_dim_expr("1 // 2", None)

    dtype, dims = parser_module._split_tensor_annotation("Tensor[f32, 'N', (M + 1) / 2 + 1]", None)
    assert dtype == NumericType.Float32
    assert dims[0] == "N"
    assert isinstance(dims[1], SymbolDim)

    dtype, dims = parser_module._split_tensor_annotation("Tensor[i64, 1, 2, '3']", None)
    assert dtype == NumericType.Int64
    assert dims == [1, 2, 3]

    with pytest.raises(parser_module._ParseFailure, match="Tensor annotation missing dimensions"):
        parser_module._split_tensor_annotation("Tensor[f32]", None)

    with pytest.raises(parser_module._ParseFailure, match="Unsupported tensor dtype"):
        parser_module._split_tensor_annotation("Tensor[x32, 1]", None)

    with pytest.raises(parser_module._ParseFailure, match="Unsupported annotation"):
        parser_module._split_tensor_annotation("Memory[f32, 1]", None)


# AST-PARSER-HELPER-002
# 创建者: 金铲铲大作战
# 最后一次更改: 金铲铲大作战
# 功能说明: 验证归一化注解文本、属性对象解析与 memory target 边界。
# 使用示例: pytest -q test/dsl/ast/test_parser_private_helpers.py -k test_parser_private_helpers_annotation_lookup_and_attribute_contracts
# 对应功能实现文件路径: kernel_gen/dsl/ast/parser.py
# 对应 spec 文件路径: spec/dsl/ast.md
# 对应测试文件路径: test/dsl/ast/test_parser_private_helpers.py
def test_parser_private_helpers_annotation_lookup_and_attribute_contracts() -> None:
    runtime_table = {"W": 4, "H": SymbolDim("H")}
    joined = py_ast.parse('f"Tensor[{W}]"', mode="eval").body
    assert parser_module._normalize_annotation_text(joined, {}, _BUILTINS_TABLE, runtime_table) == "Tensor[4]"

    with pytest.raises(parser_module._ParseFailure, match="Unsupported formatted annotation"):
        parser_module._normalize_annotation_text(py_ast.parse('f"{W!r}"', mode="eval").body, {}, _BUILTINS_TABLE, runtime_table)

    assert parser_module._lookup_python_name("MemorySpace", {"MemorySpace": MemorySpace}, _BUILTINS_TABLE) is MemorySpace
    assert parser_module._lookup_python_name("missing", {}, _BUILTINS_TABLE) is None

    attribute = py_ast.parse("MemorySpace.LM", mode="eval").body
    assert parser_module._parse_attribute_object(attribute, {"MemorySpace": MemorySpace}, _BUILTINS_TABLE) is MemorySpace.LM

    assert parser_module._is_allowed_attribute_value(MemorySpace.LM) is True
    assert parser_module._is_allowed_attribute_value(42) is False

    tensor_ast = TensorAST(name="out", memory=Memory([1], NumericType.Float32), location=None)
    assert parser_module._is_memory_target_ast(tensor_ast) is True

    assert parser_module._tensor_annotation_text_from_subscript(
        py_ast.parse("Tensor[f32, M]", mode="eval").body
    ) == "Tensor[f32, M]"


# AST-PARSER-HELPER-003
# 创建者: 金铲铲大作战
# 最后一次更改: 金铲铲大作战
# 功能说明: 验证 annotation 推断、PEP604 联合注解与 helper 绑定路径。
# 使用示例: pytest -q test/dsl/ast/test_parser_private_helpers.py -k test_parser_private_helpers_annotation_node_and_import_binding_contracts
# 对应功能实现文件路径: kernel_gen/dsl/ast/parser.py
# 对应 spec 文件路径: spec/dsl/ast.md
# 对应测试文件路径: test/dsl/ast/test_parser_private_helpers.py
def test_parser_private_helpers_annotation_node_and_import_binding_contracts() -> None:
    mem = Memory([SymbolDim("M")], NumericType.Float32)

    inferred_tensor = parser_module._annotation_from_runtime_value("arg", mem)
    assert isinstance(inferred_tensor, TensorAST)
    assert inferred_tensor.memory == mem

    inferred_symbol = parser_module._annotation_from_runtime_value("n", SymbolDim("N"))
    assert isinstance(inferred_symbol, ScalarArgAST)
    assert inferred_symbol.is_symbolic is True

    inferred_int = parser_module._annotation_from_runtime_value("n", 7)
    assert isinstance(inferred_int, ScalarArgAST)
    assert inferred_int.value_type is int

    assert parser_module._annotation_from_name_lookup("arg", {"arg": mem}) is not None
    assert parser_module._annotation_from_name_lookup("n", {"n": SymbolDim("N")}).is_symbolic is True

    assert parser_module._annotation_from_text("int", "x", None).value_type is int
    assert parser_module._annotation_from_text("bool", "x", None).value_type is bool
    assert parser_module._annotation_from_text("float", None, None).value_type is float

    tensor_ast = parser_module._parse_annotation_node(
        py_ast.parse("Tensor[f32, M, 2]", mode="eval").body,
        "x",
        {},
        _BUILTINS_TABLE,
    )
    assert isinstance(tensor_ast, TensorAST)

    union_ast = parser_module._parse_annotation_node(
        py_ast.parse("int | SymbolDim", mode="eval").body,
        "x",
        {},
        _BUILTINS_TABLE,
    )
    assert isinstance(union_ast, ScalarArgAST)
    assert union_ast.is_symbolic is True

    inferred_none = parser_module._parse_annotation_node(None, "arg", {}, _BUILTINS_TABLE, {"arg": mem})
    assert isinstance(inferred_none, TensorAST)

    with pytest.raises(parser_module._ParseFailure, match="Missing annotation"):
        parser_module._parse_annotation_node(None, "missing", {}, _BUILTINS_TABLE)

    dma_module = importlib.import_module("kernel_gen.operation.dma")
    expr = py_ast.parse("dma.load", mode="eval").body
    assert parser_module._resolve_call_base_object(expr.value, {"dma": dma_module}, _BUILTINS_TABLE) is dma_module
    assert parser_module._resolve_import_bound_helper_call(expr, {"dma": dma_module}, _BUILTINS_TABLE) == "load"
    assert parser_module._resolve_import_bound_helper_call(
        py_ast.parse("load_alias", mode="eval").body,
        {"load_alias": dma_module.load},
        _BUILTINS_TABLE,
    ) == "load"
    assert parser_module._resolve_import_bound_helper_call(
        py_ast.parse("kernel_gen.operation.dma.load", mode="eval").body,
        {"kernel_gen": importlib.import_module("kernel_gen")},
        _BUILTINS_TABLE,
    ) is None

    import_stmt = py_ast.parse("from kernel_gen.operation.dma import load as dma_load", mode="exec").body[0]
    import_bindings: dict[str, object] = {}
    parser_module._bind_safe_local_import(import_stmt, import_bindings)
    assert import_bindings["dma_load"] is dma_module.load

    module_import_stmt = py_ast.parse("import kernel_gen.operation.nn as nn_mod", mode="exec").body[0]
    module_bindings: dict[str, object] = {}
    parser_module._bind_safe_local_import(module_import_stmt, module_bindings)
    assert module_bindings["nn_mod"] is importlib.import_module("kernel_gen.operation.nn")

    float_call = py_ast.parse("float(n)", mode="eval").body
    parsed_float = parser_module._parse_symbol_to_float_call(float_call, {"n": SymbolDim("N")}, {}, _BUILTINS_TABLE)
    assert isinstance(parsed_float, SymbolToFloatAST)

    with pytest.raises(parser_module._ParseFailure, match="Unsupported float arity"):
        parser_module._parse_symbol_to_float_call(py_ast.parse("float(n, 1)", mode="eval").body, {}, {}, _BUILTINS_TABLE)

    union_nodes = parser_module._flatten_pep604_union_nodes(py_ast.parse("int | SymbolDim | int", mode="eval").body)
    assert [getattr(node, "id", None) for node in union_nodes] == ["int", "SymbolDim", "int"]


def _parser_private_identity_callee(value: object) -> object:
    """测试用 Python callee。

    创建者: 金铲铲大作战
    最后一次更改: 金铲铲大作战

    功能说明:
    - 为 `_parse_python_callee_call` 与 `launch_kernel[...]` 提供模块级可解析函数对象。

    使用示例:
    - _parser_private_identity_callee(x)

    关联文件:
    - 功能实现: [kernel_gen/dsl/ast/parser.py](kernel_gen/dsl/ast/parser.py)
    - Spec 文档: [spec/dsl/ast.md](spec/dsl/ast.md)
    - 测试文件: [test/dsl/ast/test_parser_private_helpers.py](test/dsl/ast/test_parser_private_helpers.py)
    """

    return value


def _parse_function_from_source(
    monkeypatch: pytest.MonkeyPatch,
    source: str,
    *,
    use_impl: bool = False,
    globals_table: dict[str, object] | None = None,
    runtime_table: dict[str, object] | None = None,
    config: dict[str, object] | None = None,
) -> object:
    """根据源码文本解析测试函数。

    创建者: 金铲铲大作战
    最后一次更改: 金铲铲大作战

    功能说明:
    - 通过 monkeypatch `inspect.getsource` 固定源码输入，便于覆盖解析主链与异常路径。
    - 支持直接调用 `parse_function` 或 `_parse_function_impl`，用于覆盖配置分支。

    使用示例:
    - func_ast = _parse_function_from_source(monkeypatch, source)

    关联文件:
    - 功能实现: [kernel_gen/dsl/ast/parser.py](kernel_gen/dsl/ast/parser.py)
    - Spec 文档: [spec/dsl/ast.md](spec/dsl/ast.md)
    - 测试文件: [test/dsl/ast/test_parser_private_helpers.py](test/dsl/ast/test_parser_private_helpers.py)
    """

    def kernel(*args: object, **kwargs: object) -> object:
        del args, kwargs
        return None

    def fake_getsource(_obj: object) -> str:
        return source

    monkeypatch.setattr(inspect, "getsource", fake_getsource)
    kernel_globals = dict(getattr(kernel, "__globals__", {}))
    kernel_builtins = kernel_globals.get("__builtins__", __builtins__)
    builtins_table = kernel_builtins if isinstance(kernel_builtins, dict) else getattr(kernel_builtins, "__dict__", {})
    globals_table = globals_table or kernel_globals
    if use_impl:
        return parser_module._parse_function_impl(kernel, globals_table, builtins_table, runtime_table, config)
    return parser_module.parse_function(kernel)


# AST-PARSER-HELPER-004
# 创建者: 金铲铲大作战
# 最后一次更改: 金铲铲大作战
# 功能说明: 验证 parser 的 call/expr/stmt 主链路会命中 import 绑定、launch_kernel、float 与 parse_function_impl。
# 使用示例: pytest -q test/dsl/ast/test_parser_private_helpers.py -k test_parser_private_helpers_call_and_function_contracts
# 对应功能实现文件路径: kernel_gen/dsl/ast/parser.py
# 对应 spec 文件路径: spec/dsl/ast.md
# 对应测试文件路径: test/dsl/ast/test_parser_private_helpers.py
def test_parser_private_helpers_call_and_function_contracts() -> None:
    dma_module = importlib.import_module("kernel_gen.operation.dma")
    arch_module = importlib.import_module("kernel_gen.operation.arch")
    nn_module = importlib.import_module("kernel_gen.operation.nn")
    globals_table = {
        "load": dma_module.load,
        "slice": dma_module.slice,
        "store": dma_module.store,
        "deslice": dma_module.deslice,
        "launch_kernel": arch_module.launch_kernel,
        "add": nn_module.add,
        "eq": nn_module.eq,
        "relu": nn_module.relu,
        "reduce_sum": nn_module.reduce_sum,
        "softmax": nn_module.softmax,
        "MemorySpace": MemorySpace,
    }
    mem = Memory([SymbolDim("M"), SymbolDim("N")], NumericType.Float32)
    bool_mem = Memory([SymbolDim("M"), SymbolDim("N")], NumericType.Bool)
    tensor = TensorAST(name="tensor", memory=mem, location=None)
    bool_tensor = TensorAST(name="bool_tensor", memory=bool_mem, location=None)
    env = {
        "tensor": tensor,
        "bool_tensor": bool_tensor,
        "n": SymbolDim("N"),
        "callee": _parser_private_identity_callee,
    }

    load_ast = parser_module._parse_dma_call(py_ast.parse("load(tensor, [0, 1], [1, 2])", mode="eval").body, env, globals_table, _BUILTINS_TABLE)
    assert isinstance(load_ast, LoadAST)
    assert load_ast.kind == "slice"

    slice_ast = parser_module._parse_dma_call(py_ast.parse("slice(tensor, [0, 1], [1, 2])", mode="eval").body, env, globals_table, _BUILTINS_TABLE)
    assert isinstance(slice_ast, LoadAST)
    assert slice_ast.kind == "slice"

    store_ast = parser_module._parse_dma_call(py_ast.parse("store(bool_tensor, tensor, [0, 1], [1, 2])", mode="eval").body, env, globals_table, _BUILTINS_TABLE)
    assert isinstance(store_ast, StoreAST)
    assert store_ast.kind == "store"

    deslice_ast = parser_module._parse_dma_call(
        py_ast.parse("deslice(bool_tensor, tensor, [0, 1], [1, 2], [1, 1], MemorySpace.GM)", mode="eval").body,
        env,
        globals_table,
        _BUILTINS_TABLE,
    )
    assert isinstance(deslice_ast, StoreAST)
    assert deslice_ast.kind == "deslice"

    add_ast = parser_module._parse_dma_call(py_ast.parse("add(tensor, bool_tensor)", mode="eval").body, env, globals_table, _BUILTINS_TABLE)
    assert isinstance(add_ast, BinaryExprAST)
    assert add_ast.op == "add"

    compare_ast = parser_module._parse_dma_call(py_ast.parse("eq(tensor, bool_tensor)", mode="eval").body, env, globals_table, _BUILTINS_TABLE)
    assert isinstance(compare_ast, CompareExprAST)
    assert compare_ast.op == "eq"

    relu_ast = parser_module._parse_dma_call(py_ast.parse("relu(tensor)", mode="eval").body, env, globals_table, _BUILTINS_TABLE)
    assert isinstance(relu_ast, NnUnaryAST)
    assert relu_ast.kind == "relu"

    reduce_ast = parser_module._parse_dma_call(py_ast.parse("reduce_sum(tensor, 1, keepdim=False)", mode="eval").body, env, globals_table, _BUILTINS_TABLE)
    assert isinstance(reduce_ast, NnReduceAST)
    assert reduce_ast.kind == "reduce_sum"

    softmax_ast = parser_module._parse_dma_call(py_ast.parse("softmax(tensor, axis=1)", mode="eval").body, env, globals_table, _BUILTINS_TABLE)
    assert isinstance(softmax_ast, NnSoftmaxAST)

    launch_ast = parser_module._parse_dma_call(
        py_ast.parse("launch_kernel[1, 2, 3, 0](callee, tensor)", mode="eval").body,
        env,
        globals_table,
        _BUILTINS_TABLE,
    )
    assert isinstance(launch_ast, ArchLaunchKernelAST)
    assert launch_ast.callee == "_parser_private_identity_callee"
    assert isinstance(launch_ast.block, ConstAST)
    assert launch_ast.block.value == 1
    assert isinstance(launch_ast.thread, ConstAST)
    assert launch_ast.thread.value == 2
    assert isinstance(launch_ast.subthread, ConstAST)
    assert launch_ast.subthread.value == 3
    assert isinstance(launch_ast.shared_memory_size, ConstAST)
    assert launch_ast.shared_memory_size.value == 0
    assert len(launch_ast.args) == 1

    python_callee_ast = parser_module._parse_python_callee_call(
        py_ast.parse("callee(tensor, 1)", mode="eval").body,
        env,
        globals_table,
        _BUILTINS_TABLE,
    )
    assert isinstance(python_callee_ast, PythonCalleeCallAST)
    assert len(python_callee_ast.args) == 2

    parsed_shape = parser_module._parse_expr(
        py_ast.parse("tensor.get_shape()[1]", mode="eval").body,
        env,
        globals_table,
        _BUILTINS_TABLE,
    )
    assert isinstance(parsed_shape, TensorAxisAccessAST)
    assert parsed_shape.kind == "shape"

    parsed_negative = parser_module._parse_expr(
        py_ast.parse("-3", mode="eval").body,
        env,
        globals_table,
        _BUILTINS_TABLE,
    )
    assert isinstance(parsed_negative, ConstAST)
    assert parsed_negative.value == -3

    parsed_compare = parser_module._parse_expr(
        py_ast.parse("1 < 2", mode="eval").body,
        env,
        globals_table,
        _BUILTINS_TABLE,
    )
    assert isinstance(parsed_compare, CompareExprAST)

    parsed_float = parser_module._parse_symbol_to_float_call(
        py_ast.parse("float(n)", mode="eval").body,
        env,
        globals_table,
        _BUILTINS_TABLE,
    )
    assert isinstance(parsed_float, SymbolToFloatAST)

    def kernel(x: "Tensor[f32, 2]", y: "Tensor[f32, 2]", n: int) -> "Tensor[f32, 2]":
        from kernel_gen.operation.dma import load, store
        from kernel_gen.operation.nn import add

        tmp = load(x, [0, 0], [1, 1])
        for _idx in range(1, n, 1):
            tmp = add(tmp, y)
        store(tmp, x, [0, 0], [1, 1])
        return tmp

    func_ast = parser_module.parse_function(kernel)
    assert func_ast.has_explicit_return is True
    assert any(isinstance(stmt, ForAST) for stmt in func_ast.body.statements)


# AST-PARSER-HELPER-005
# 创建者: 金铲铲大作战
# 最后一次更改: 金铲铲大作战
# 功能说明: 验证 parser 的 stmt / for 主链会命中所有常见语句分支与边界异常。
# 使用示例: pytest -q test/dsl/ast/test_parser_private_helpers.py -k test_parser_private_helpers_stmt_and_for_contracts
# 对应功能实现文件路径: kernel_gen/dsl/ast/parser.py
# 对应 spec 文件路径: spec/dsl/ast.md
# 对应测试文件路径: test/dsl/ast/test_parser_private_helpers.py
def test_parser_private_helpers_stmt_and_for_contracts() -> None:
    mem = Memory([SymbolDim("M")], NumericType.Float32)
    env: dict[str, object] = {
        "x": TensorAST(name="x", memory=mem, location=None),
        "y": TensorAST(name="y", memory=mem, location=None),
        "n": SymbolDim("N"),
        "value": ConstAST(value=7, location=None),
    }
    globals_table = {
        "relu": importlib.import_module("kernel_gen.operation.nn").relu,
    }

    assign_stmt = py_ast.parse("alias = value", mode="exec").body[0]
    assigned = parser_module._parse_stmt(assign_stmt, env, globals_table, _BUILTINS_TABLE)
    assert isinstance(assigned, ConstAST)
    assert env["alias"] == assigned

    expr_stmt = py_ast.parse("relu(x)", mode="exec").body[0]
    expr_result = parser_module._parse_stmt(expr_stmt, env, globals_table, _BUILTINS_TABLE)
    assert isinstance(expr_result, NnUnaryAST)
    assert expr_result.kind == "relu"

    for_stmt = py_ast.parse("for i in range(0, n, 1):\n    alias = i", mode="exec").body[0]
    parsed_for = parser_module._parse_for(for_stmt, env, globals_table, _BUILTINS_TABLE)
    assert isinstance(parsed_for, ForAST)
    assert parsed_for.var.name == "i"
    assert isinstance(parsed_for.body.statements[0], VarAST)

    loop_stmt = py_ast.parse("for j in LoopRange(4):\n    alias = j", mode="exec").body[0]
    parsed_loop = parser_module._parse_for(loop_stmt, env, globals_table, _BUILTINS_TABLE)
    assert isinstance(parsed_loop, ForAST)
    assert isinstance(parsed_loop.start, ConstAST)
    assert parsed_loop.step.value == 1

    with pytest.raises(parser_module._ParseFailure, match="Unsupported for target"):
        parser_module._parse_for(py_ast.parse("for i, j in range(4):\n    alias = i", mode="exec").body[0], env, globals_table, _BUILTINS_TABLE)

    with pytest.raises(parser_module._ParseFailure, match="Unsupported for iterator"):
        parser_module._parse_for(py_ast.parse("for i in foo(4):\n    alias = i", mode="exec").body[0], env, globals_table, _BUILTINS_TABLE)

    with pytest.raises(parser_module._ParseFailure, match="Unsupported range arity"):
        parser_module._parse_for(py_ast.parse("for i in range(1, 2, 3, 4):\n    alias = i", mode="exec").body[0], env, globals_table, _BUILTINS_TABLE)

    with pytest.raises(parser_module._ParseFailure, match="for range step must not be zero"):
        parser_module._parse_for(py_ast.parse("for i in range(0, 4, 0):\n    alias = i", mode="exec").body[0], env, globals_table, _BUILTINS_TABLE)

    with pytest.raises(parser_module._ParseFailure, match="Return inside for-loop is unsupported"):
        parser_module._parse_for(py_ast.parse("for i in range(4):\n    return x", mode="exec").body[0], env, globals_table, _BUILTINS_TABLE)

    with pytest.raises(parser_module._ParseFailure, match="Unsupported assignment target"):
        parser_module._parse_stmt(py_ast.parse("a, b = value", mode="exec").body[0], env, globals_table, _BUILTINS_TABLE)

    with pytest.raises(parser_module._ParseFailure, match="Return value is required"):
        parser_module._parse_stmt(py_ast.parse("return", mode="exec").body[0], env, globals_table, _BUILTINS_TABLE)

    with pytest.raises(parser_module._ParseFailure, match="Nested function definition is not supported"):
        parser_module._parse_stmt(
            py_ast.parse("def inner():\n    return value", mode="exec").body[0],
            env,
            globals_table,
            _BUILTINS_TABLE,
        )

    with pytest.raises(parser_module._ParseFailure, match="Unsupported if bias is not None"):
        parser_module._parse_stmt(
            py_ast.parse("if bias is not None:\n    alias = value", mode="exec").body[0],
            env,
            globals_table,
            _BUILTINS_TABLE,
        )

    with pytest.raises(parser_module._ParseFailure, match="Unsupported if statement"):
        parser_module._parse_stmt(
            py_ast.parse("if flag:\n    alias = value", mode="exec").body[0],
            env,
            globals_table,
            _BUILTINS_TABLE,
        )

    with pytest.raises(parser_module._ParseFailure, match="Unsupported syntax"):
        parser_module._parse_stmt(
            py_ast.parse("while True:\n    alias = value", mode="exec").body[0],
            env,
            globals_table,
            _BUILTINS_TABLE,
        )


# AST-PARSER-HELPER-006
# 创建者: 金铲铲大作战
# 最后一次更改: 金铲铲大作战
# 功能说明: 验证 parse_function_impl / parse_function 的源码主链、import 绑定与异常路径。
# 使用示例: pytest -q test/dsl/ast/test_parser_private_helpers.py -k test_parser_private_helpers_parse_function_impl_contracts
# 对应功能实现文件路径: kernel_gen/dsl/ast/parser.py
# 对应 spec 文件路径: spec/dsl/ast.md
# 对应测试文件路径: test/dsl/ast/test_parser_private_helpers.py
def test_parser_private_helpers_parse_function_impl_contracts(monkeypatch: pytest.MonkeyPatch) -> None:
    valid_source = """\
def kernel(x: "Tensor[f32, 2]", n: int) -> "Tensor[f32, 2]":
    \"\"\"parser contract test\"\"\"
    from kernel_gen.operation.dma import load
    from kernel_gen.operation.nn import relu

    tmp = load(x, [0, 0], [1, 1])
    for i in range(1, n, 1):
        tmp = relu(tmp)
    return tmp
"""
    func_ast = _parse_function_from_source(monkeypatch, valid_source)
    assert getattr(func_ast, "name", None) == "kernel"
    assert func_ast.has_explicit_return is True
    assert any(isinstance(stmt, ForAST) for stmt in func_ast.body.statements)

    missing_annotation_source = """\
def kernel(x):
    return x
"""
    with pytest.raises(parser_module.AstParseError, match="Missing annotation"):
        _parse_function_from_source(monkeypatch, missing_annotation_source)

    missing_return_source = """\
def kernel(x: "Tensor[f32, 1]") -> "Tensor[f32, 1]":
    x = x
"""
    with pytest.raises(parser_module.AstParseError, match="Missing return statement"):
        _parse_function_from_source(monkeypatch, missing_return_source)

    return_not_last_source = """\
def kernel(x: "Tensor[f32, 1]") -> "Tensor[f32, 1]":
    return x
    from kernel_gen.operation.dma import load
"""
    with pytest.raises(parser_module.AstParseError, match="Return statement must be last"):
        _parse_function_from_source(monkeypatch, return_not_last_source)

    function_not_found_source = """\
def other(x: "Tensor[f32, 1]"):
    return x
"""
    with pytest.raises(parser_module.AstParseError, match="Function definition not found"):
        _parse_function_from_source(monkeypatch, function_not_found_source)

    multiple_function_source = """\
def a(x: "Tensor[f32, 1]"):
    return x

def kernel(x: "Tensor[f32, 1]"):
    return x
"""
    with pytest.raises(parser_module.AstParseError, match="Multiple top-level function definitions are not supported"):
        _parse_function_from_source(monkeypatch, multiple_function_source)

    unsupported_return_source = """\
def kernel(x: int) -> float:
    return x
"""
    with pytest.raises(parser_module.AstParseError, match="Unsupported return annotation"):
        _parse_function_from_source(monkeypatch, unsupported_return_source)

    none_return_source = """\
def kernel(x: int) -> None:
    x = x
"""
    none_func_ast = _parse_function_from_source(monkeypatch, none_return_source)
    assert getattr(none_func_ast, "returns_none", False) is True

    def callee(value: object) -> object:
        return value

    python_callee_source = """\
def kernel(x: "Tensor[f32, 1]") -> "Tensor[f32, 1]":
    return callee(x)
"""
    python_callee_ast = _parse_function_from_source(
        monkeypatch,
        python_callee_source,
        use_impl=True,
        globals_table={"callee": callee},
        config={"allow_python_callee_calls": True},
    )
    assert python_callee_ast is not None

    reject_external_source = """\
def kernel(x: "Tensor[f32, 1]") -> "Tensor[f32, 1]":
    return external_value
"""
    with pytest.raises(parser_module._ParseFailure, match="cannot use external value inside function body"):
        _parse_function_from_source(
            monkeypatch,
            reject_external_source,
            use_impl=True,
            globals_table={"external_value": 7},
            config={"reject_external_values": True},
        )


# AST-PARSER-HELPER-007
# 创建者: 小李飞刀
# 最后一次更改: 小李飞刀
# 功能说明: 覆盖 formatted annotation 运算、DMA helper 扩展参数与 launch/barrier 的剩余边界。
# 使用示例: pytest -q test/dsl/ast/test_parser_private_helpers.py -k test_parser_private_helpers_formatted_annotation_dma_and_launch_edge_contracts
# 对应功能实现文件路径: kernel_gen/dsl/ast/parser.py
# 对应 spec 文件路径: spec/dsl/ast.md
# 对应测试文件路径: test/dsl/ast/test_parser_private_helpers.py
def test_parser_private_helpers_formatted_annotation_dma_and_launch_edge_contracts() -> None:
    dma_module = importlib.import_module("kernel_gen.operation.dma")
    nn_module = importlib.import_module("kernel_gen.operation.nn")
    arch_module = importlib.import_module("kernel_gen.operation.arch")
    runtime_table = {"N": SymbolDim("N"), "W": 8}

    neg_symbol = parser_module._eval_formatted_annotation_expr(
        py_ast.parse("-N", mode="eval").body,
        {},
        _BUILTINS_TABLE,
        runtime_table,
    )
    assert isinstance(neg_symbol, SymbolDim)
    assert str(neg_symbol) == "-N"
    assert parser_module._eval_formatted_annotation_expr(
        py_ast.parse("W + 2", mode="eval").body,
        {},
        _BUILTINS_TABLE,
        runtime_table,
    ) == 10
    assert parser_module._eval_formatted_annotation_expr(
        py_ast.parse("W - 2", mode="eval").body,
        {},
        _BUILTINS_TABLE,
        runtime_table,
    ) == 6
    assert parser_module._eval_formatted_annotation_expr(
        py_ast.parse("W * 2", mode="eval").body,
        {},
        _BUILTINS_TABLE,
        runtime_table,
    ) == 16
    assert parser_module._eval_formatted_annotation_expr(
        py_ast.parse("W / 2", mode="eval").body,
        {},
        _BUILTINS_TABLE,
        runtime_table,
    ) == 4
    symbol_div = parser_module._eval_formatted_annotation_expr(
        py_ast.parse("N / 2", mode="eval").body,
        {},
        _BUILTINS_TABLE,
        runtime_table,
    )
    assert isinstance(symbol_div, SymbolDim)
    formatted_value = parser_module._format_joinedstr_value(
        py_ast.parse('f"{W // 2}"', mode="eval").body.values[0],
        {},
        _BUILTINS_TABLE,
        runtime_table,
    )
    assert formatted_value == "4"
    with pytest.raises(parser_module._ParseFailure, match="Unsupported formatted annotation"):
        parser_module._eval_formatted_annotation_expr(
            py_ast.parse("W / 3", mode="eval").body,
            {},
            _BUILTINS_TABLE,
            runtime_table,
        )
    with pytest.raises(parser_module._ParseFailure, match="Unsupported formatted annotation"):
        parser_module._eval_formatted_annotation_expr(
            py_ast.parse("W // 0", mode="eval").body,
            {},
            _BUILTINS_TABLE,
            runtime_table,
        )

    globals_table = {
        "NumericType": NumericType,
        "MemorySpace": MemorySpace,
        "BarrierVisibility": arch_module.BarrierVisibility,
        "BarrierScope": arch_module.BarrierScope,
        "alloc": dma_module.alloc,
        "cast": dma_module.cast,
        "broadcast_to": nn_module.broadcast_to,
        "transpose": nn_module.transpose,
        "barrier": arch_module.barrier,
        "launch_kernel": arch_module.launch_kernel,
    }
    mem = Memory([SymbolDim("M"), SymbolDim("N")], NumericType.Float32)
    tensor = TensorAST(name="tensor", memory=mem, location=None)
    env = {
        "tensor": tensor,
        "n": SymbolDim("N"),
        "bad_float": ScalarArgAST(name="bad_float", value_type=float, is_symbolic=False, location=None),
        "callee": _parser_private_identity_callee,
    }

    alloc_ast = parser_module._parse_dma_call(
        py_ast.parse(
            "alloc([1, n], NumericType.Float32, space=MemorySpace.GM, stride=[n, 1])",
            mode="eval",
        ).body,
        env,
        globals_table,
        _BUILTINS_TABLE,
    )
    assert type(alloc_ast).__name__ == "DmaAllocAST"
    assert alloc_ast.space is MemorySpace.GM
    assert alloc_ast.stride[0] == SymbolDim("N")
    assert isinstance(alloc_ast.stride[1], ConstAST)
    assert alloc_ast.stride[1].value == 1

    cast_ast = parser_module._parse_dma_call(
        py_ast.parse(
            "cast(tensor, NumericType.Float32, memoryspace=MemorySpace.GM)",
            mode="eval",
        ).body,
        env,
        globals_table,
        _BUILTINS_TABLE,
    )
    assert type(cast_ast).__name__ == "DmaCastAST"
    assert cast_ast.memoryspace is MemorySpace.GM

    broadcast_to_ast = parser_module._parse_dma_call(
        py_ast.parse(
            "broadcast_to(tensor, [1, n], space=MemorySpace.GM)",
            mode="eval",
        ).body,
        env,
        globals_table,
        _BUILTINS_TABLE,
    )
    assert type(broadcast_to_ast).__name__ == "NnBroadcastToAST"
    transpose_ast = parser_module._parse_dma_call(
        py_ast.parse("transpose(tensor, perm=[1, 0])", mode="eval").body,
        env,
        globals_table,
        _BUILTINS_TABLE,
    )
    assert type(transpose_ast).__name__ == "NnTransposeAST"

    barrier_ast = parser_module._parse_dma_call(
        py_ast.parse(
            "barrier(visibility=[BarrierVisibility.TSM, BarrierVisibility.TLM], scope=BarrierScope.BLOCK)",
            mode="eval",
        ).body,
        env,
        globals_table,
        _BUILTINS_TABLE,
    )
    assert type(barrier_ast).__name__ == "ArchBarrierAST"
    assert [space.name for space in barrier_ast.visibility] == ["TSM", "TLM"]

    launch_ast = parser_module._parse_dma_call(
        py_ast.parse("launch_kernel(callee, n, 2, 1, 0, tensor)", mode="eval").body,
        env,
        globals_table,
        _BUILTINS_TABLE,
    )
    assert isinstance(launch_ast, ArchLaunchKernelAST)
    assert str(launch_ast.block) == "N"
    assert isinstance(launch_ast.thread, ConstAST)
    assert launch_ast.thread.value == 2

    with pytest.raises(parser_module._ParseFailure, match="Unsupported alloc arity"):
        parser_module._parse_dma_call(
            py_ast.parse(
                "alloc([1], NumericType.Float32, MemorySpace.GM, stride=[1], space=MemorySpace.GM)",
                mode="eval",
            ).body,
            env,
            globals_table,
            _BUILTINS_TABLE,
        )
    with pytest.raises(parser_module._ParseFailure, match="barrier visibility must be non-empty BarrierVisibility list"):
        parser_module._parse_dma_call(
            py_ast.parse(
                "barrier(visibility=[], scope=BarrierScope.BLOCK)",
                mode="eval",
            ).body,
            env,
            globals_table,
            _BUILTINS_TABLE,
        )
    with pytest.raises(parser_module._ParseFailure, match="launch_kernel block must be int or SymbolDim"):
        parser_module._parse_dma_call(
            py_ast.parse("launch_kernel[bad_float, 2, 1, 0](callee, tensor)", mode="eval").body,
            env,
            globals_table,
            _BUILTINS_TABLE,
        )
    with pytest.raises(parser_module._ParseFailure, match="Unsupported launch_kernel arity"):
        parser_module._parse_dma_call(
            py_ast.parse("launch_kernel(callee, 1, 2, 1)", mode="eval").body,
            env,
            globals_table,
            _BUILTINS_TABLE,
        )


# AST-PARSER-HELPER-008
# 创建者: 小李飞刀
# 最后一次更改: 小李飞刀
# 功能说明: 覆盖 external value 约束、python callee 放行和 parse_function_impl 的剩余异常路径。
# 使用示例: pytest -q test/dsl/ast/test_parser_private_helpers.py -k test_parser_private_helpers_external_value_and_parse_function_edge_contracts
# 对应功能实现文件路径: kernel_gen/dsl/ast/parser.py
# 对应 spec 文件路径: spec/dsl/ast.md
# 对应测试文件路径: test/dsl/ast/test_parser_private_helpers.py
def test_parser_private_helpers_external_value_and_parse_function_edge_contracts(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    tensor = TensorAST(name="tensor", memory=Memory([SymbolDim("M")], NumericType.Float32), location=None)
    globals_table = {"callee": _parser_private_identity_callee, "external_int": 7, "external_obj": object()}
    reject_env = {parser_module._REJECT_EXTERNAL_VALUES_ENV_KEY: True, "tensor": tensor}
    allow_const_env = dict(reject_env)
    allow_const_env[parser_module._ALLOW_EXTERNAL_CONSTANTS_ENV_KEY] = True
    allow_python_callee_env = dict(reject_env)
    allow_python_callee_env[parser_module._ALLOW_PYTHON_CALLEE_CALL_ENV_KEY] = True

    allowed_const = parser_module._parse_expr(
        py_ast.parse("external_int", mode="eval").body,
        allow_const_env,
        globals_table,
        _BUILTINS_TABLE,
    )
    assert isinstance(allowed_const, ConstAST)
    assert allowed_const.value == 7

    with pytest.raises(parser_module._ParseFailure, match="cannot use external value inside function body"):
        parser_module._parse_expr(
            py_ast.parse("external_obj", mode="eval").body,
            reject_env,
            globals_table,
            _BUILTINS_TABLE,
        )
    with pytest.raises(parser_module._ParseFailure, match="Unsupported call expression"):
        parser_module._parse_expr(
            py_ast.parse("callee(tensor)", mode="eval").body,
            reject_env,
            globals_table,
            _BUILTINS_TABLE,
        )

    python_callee_expr = parser_module._parse_expr(
        py_ast.parse("callee(tensor)", mode="eval").body,
        allow_python_callee_env,
        globals_table,
        _BUILTINS_TABLE,
    )
    assert isinstance(python_callee_expr, PythonCalleeCallAST)

    source_with_module_builtins = """\
def kernel(x: "Tensor[f32, 1]") -> "Tensor[f32, 1]":
    return x
"""
    parsed = _parse_function_from_source(
        monkeypatch,
        source_with_module_builtins,
        use_impl=True,
        globals_table={"__builtins__": sys.modules["builtins"]},
    )
    assert parsed is not None

    unsupported_arg_source = """\
def kernel(x: NumericType.Float32):
    return x
"""
    with pytest.raises(parser_module._ParseFailure, match="Unsupported annotation"):
        _parse_function_from_source(
            monkeypatch,
            unsupported_arg_source,
            use_impl=True,
            globals_table={"NumericType": NumericType},
        )


# AST-PARSER-HELPER-009
# 创建者: 小李飞刀
# 最后一次更改: 小李飞刀
# 功能说明: 覆盖 parser 私有 helper 的异常表达式、launch extent 与 stmt/for 剩余边界。
# 使用示例: pytest -q test/dsl/ast/test_parser_private_helpers.py -k test_parser_private_helpers_expr_launch_stmt_edge_matrix
# 对应功能实现文件路径: kernel_gen/dsl/ast/parser.py
# 对应 spec 文件路径: spec/dsl/ast.md
# 对应测试文件路径: test/dsl/ast/test_parser_private_helpers.py
def test_parser_private_helpers_expr_launch_stmt_edge_matrix() -> None:
    def launch_callee(value: object) -> object:
        return value

    dummy_node = type("DummyNode", (), {"lineno": 3})()
    assert parser_module._location_from_node(dummy_node) is None
    assert parser_module._eval_symbolic_dim_node(py_ast.parse("-3", mode="eval").body, None) == -3
    assert isinstance(parser_module._eval_symbolic_dim_node(py_ast.parse("2 / N", mode="eval").body, None), SymbolDim)

    with pytest.raises(parser_module._ParseFailure, match="Unsupported tensor dimension expression"):
        parser_module._eval_symbolic_dim_node(py_ast.parse("8 / 0", mode="eval").body, None)
    with pytest.raises(parser_module._ParseFailure, match="Unsupported tensor dimension expression"):
        parser_module._eval_symbolic_dim_expr("(", None)

    runtime_table = {"W": 8, "S": SymbolDim("S")}
    assert parser_module._eval_formatted_annotation_expr(
        py_ast.parse("sym_expr", mode="eval").body,
        {"sym_expr": parser_module.sp.Symbol("Q")},
        _BUILTINS_TABLE,
        runtime_table,
    ) == SymbolDim(parser_module.sp.Symbol("Q"))
    assert parser_module._eval_formatted_annotation_expr(
        py_ast.parse("S / 2", mode="eval").body,
        {},
        _BUILTINS_TABLE,
        runtime_table,
    ) == SymbolDim("S") / 2
    with pytest.raises(parser_module._ParseFailure, match="Unsupported formatted annotation"):
        parser_module._eval_formatted_annotation_expr(
            py_ast.parse("bad", mode="eval").body,
            {"bad": object()},
            _BUILTINS_TABLE,
            runtime_table,
        )
    with pytest.raises(parser_module._ParseFailure, match="Unsupported annotation"):
        parser_module._normalize_annotation_text(py_ast.parse("1", mode="eval").body, {}, _BUILTINS_TABLE, runtime_table)

    tensor = TensorAST(name="tensor", memory=Memory([SymbolDim("M")], NumericType.Float32), location=None)
    env = {"tensor": tensor, "callee": launch_callee, "scale": 7, "sentinel": object()}
    globals_table = {"callee": launch_callee}

    launch_call = py_ast.parse("launch_kernel(callee, tensor)", mode="eval").body
    with pytest.raises(parser_module._ParseFailure, match="launch_kernel thread must be > 0"):
        parser_module._parse_launch_kernel_call(
            launch_call,
            env,
            globals_table,
            _BUILTINS_TABLE,
            launch_slice=py_ast.parse("(1, 0, 1, 0)", mode="eval").body,
        )
    with pytest.raises(parser_module._ParseFailure, match="launch_kernel callee must be function symbol reference"):
        parser_module._parse_launch_kernel_call(
            py_ast.parse("tensor(tensor)", mode="eval").body,
            env,
            globals_table,
            _BUILTINS_TABLE,
            launch_slice=py_ast.parse("(1, 1, 1, 0)", mode="eval").body,
        )
    with pytest.raises(parser_module._ParseFailure, match="Unsupported launch_kernel arity"):
        parser_module._parse_launch_kernel_call(
            py_ast.parse("launch_kernel(callee, tensor=1)", mode="eval").body,
            env,
            globals_table,
            _BUILTINS_TABLE,
            launch_slice=py_ast.parse("(1, 1, 1, 0)", mode="eval").body,
        )

    parsed_list = parser_module._parse_expr(py_ast.parse("[1, scale]", mode="eval").body, env, globals_table, _BUILTINS_TABLE)
    parsed_tuple = parser_module._parse_expr(py_ast.parse("(1, scale)", mode="eval").body, env, globals_table, _BUILTINS_TABLE)
    assert isinstance(parsed_list[0], ConstAST)
    assert parsed_list[0].value == 1
    assert parsed_list[1] == 7
    assert isinstance(parsed_tuple[0], ConstAST)
    assert parsed_tuple[0].value == 1
    assert parsed_tuple[1] == 7
    assert parser_module._parse_expr(py_ast.parse("sentinel", mode="eval").body, env, globals_table, _BUILTINS_TABLE) is env["sentinel"]

    with pytest.raises(parser_module._ParseFailure, match="Unsupported constant type"):
        parser_module._parse_expr(py_ast.parse("b'x'", mode="eval").body, env, globals_table, _BUILTINS_TABLE)
    with pytest.raises(parser_module._ParseFailure, match="get_shape source must be TensorAST"):
        parser_module._parse_expr(py_ast.parse("scale.get_shape()[0]", mode="eval").body, env, globals_table, _BUILTINS_TABLE)
    with pytest.raises(parser_module._ParseFailure, match="Unsupported expression"):
        parser_module._parse_expr(py_ast.parse("+1", mode="eval").body, env, globals_table, _BUILTINS_TABLE)
    with pytest.raises(parser_module._ParseFailure, match="Unsupported binary op"):
        parser_module._parse_expr(py_ast.parse("1 @ 2", mode="eval").body, env, globals_table, _BUILTINS_TABLE)
    with pytest.raises(parser_module._ParseFailure, match="Unsupported compare expression"):
        parser_module._parse_expr(py_ast.parse("1 < 2 < 3", mode="eval").body, env, globals_table, _BUILTINS_TABLE)

    prior_loop_var = ConstAST(value=9, location=None)
    loop_env = {"i": prior_loop_var}
    parsed_for = parser_module._parse_for(
        py_ast.parse("for i in range(1, 3):\n    i\n", mode="exec").body[0],
        loop_env,
        globals_table,
        _BUILTINS_TABLE,
    )
    assert isinstance(parsed_for, ForAST)
    assert loop_env["i"] is prior_loop_var

    with pytest.raises(parser_module._ParseFailure, match="Unsupported for target"):
        parser_module._parse_for(
            py_ast.parse("for i, j in range(2):\n    i\n", mode="exec").body[0],
            {},
            globals_table,
            _BUILTINS_TABLE,
        )
    with pytest.raises(parser_module._ParseFailure, match="Unsupported for iterator"):
        parser_module._parse_for(
            py_ast.parse("for i in items(2):\n    i\n", mode="exec").body[0],
            {},
            globals_table,
            _BUILTINS_TABLE,
        )
    with pytest.raises(parser_module._ParseFailure, match="Unsupported range arity"):
        parser_module._parse_for(
            py_ast.parse("for i in range(1, 2, 3, 4):\n    i\n", mode="exec").body[0],
            {},
            globals_table,
            _BUILTINS_TABLE,
        )
    with pytest.raises(parser_module._ParseFailure, match="for range step must not be zero"):
        parser_module._parse_for(
            py_ast.parse("for i in range(0, 2, 0):\n    i\n", mode="exec").body[0],
            {},
            globals_table,
            _BUILTINS_TABLE,
        )
    with pytest.raises(parser_module._ParseFailure, match="Return inside for-loop is unsupported"):
        parser_module._parse_for(
            py_ast.parse("for i in range(2):\n    return i\n", mode="exec").body[0],
            {},
            globals_table,
            _BUILTINS_TABLE,
        )

    with pytest.raises(parser_module._ParseFailure, match="Nested function definition is not supported"):
        parser_module._parse_stmt(py_ast.parse("def inner():\n    pass\n", mode="exec").body[0], {}, globals_table, _BUILTINS_TABLE)
    with pytest.raises(parser_module._ParseFailure, match="Unsupported if bias is not None"):
        parser_module._parse_stmt(
            py_ast.parse("if bias is not None:\n    x\n", mode="exec").body[0],
            {},
            globals_table,
            _BUILTINS_TABLE,
        )
    with pytest.raises(parser_module._ParseFailure, match="Unsupported assignment target"):
        parser_module._parse_stmt(py_ast.parse("x, y = 1, 2", mode="exec").body[0], {}, globals_table, _BUILTINS_TABLE)
    with pytest.raises(parser_module._ParseFailure, match="Return value is required"):
        parser_module._parse_stmt(py_ast.parse("return", mode="exec").body[0], {}, globals_table, _BUILTINS_TABLE)
    with pytest.raises(parser_module._ParseFailure, match="Unsupported syntax"):
        parser_module._parse_stmt(py_ast.parse("while True:\n    break\n", mode="exec").body[0], {}, globals_table, _BUILTINS_TABLE)


# AST-PARSER-HELPER-010
# 创建者: 小李飞刀
# 最后一次更改: 小李飞刀
# 功能说明: 覆盖 parse_function_impl 的 source/builtins/return 相关异常矩阵。
# 使用示例: pytest -q test/dsl/ast/test_parser_private_helpers.py -k test_parser_private_helpers_parse_function_impl_error_matrix
# 对应功能实现文件路径: kernel_gen/dsl/ast/parser.py
# 对应 spec 文件路径: spec/dsl/ast.md
# 对应测试文件路径: test/dsl/ast/test_parser_private_helpers.py
def test_parser_private_helpers_parse_function_impl_error_matrix(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def kernel(*args: object, **kwargs: object) -> object:
        del args, kwargs
        return None

    monkeypatch.setattr(inspect, "getsource", lambda _obj: (_ for _ in ()).throw(OSError("missing source")))
    with pytest.raises(parser_module.AstParseError, match="Unable to get source"):
        parser_module._parse_function_impl(kernel)

    with pytest.raises(parser_module._ParseFailure, match="Multiple top-level function definitions are not supported"):
        _parse_function_from_source(
            monkeypatch,
            'def kernel(x: "Tensor[f32, 1]") -> "Tensor[f32, 1]":\n    return x\n\ndef other():\n    return None\n',
            use_impl=True,
        )

    with pytest.raises(parser_module.AstParseError, match="Function definition not found"):
        _parse_function_from_source(
            monkeypatch,
            'def other(x: "Tensor[f32, 1]") -> "Tensor[f32, 1]":\n    return x\n',
            use_impl=True,
        )

    with pytest.raises(parser_module._ParseFailure, match="Missing annotation"):
        _parse_function_from_source(monkeypatch, "def kernel(x):\n    return x\n", use_impl=True)

    with pytest.raises(parser_module._ParseFailure, match="Unsupported annotation"):
        _parse_function_from_source(
            monkeypatch,
            'def kernel(x: "Tensor[f32, 1]") -> MemorySpace:\n    return x\n',
            use_impl=True,
            globals_table={"MemorySpace": MemorySpace},
        )

    with pytest.raises(parser_module.AstParseError, match="Missing return statement"):
        _parse_function_from_source(
            monkeypatch,
            'def kernel(x: "Tensor[f32, 1]") -> "Tensor[f32, 1]":\n    x\n',
            use_impl=True,
        )

    with pytest.raises(parser_module.AstParseError, match="Return statement must be last"):
        _parse_function_from_source(
            monkeypatch,
            'def kernel(x: "Tensor[f32, 1]") -> "Tensor[f32, 1]":\n    return x\n    x\n',
            use_impl=True,
        )

    with pytest.raises(parser_module.AstParseError, match="Return statement must be last"):
        _parse_function_from_source(
            monkeypatch,
            'def kernel(x: "Tensor[f32, 1]") -> "Tensor[f32, 1]":\n    return x\n    import math\n',
            use_impl=True,
        )


# AST-PARSER-HELPER-011
# 创建者: 小李飞刀
# 最后一次更改: 小李飞刀
# 功能说明: 继续覆盖 parser 在 DMA/NN/arch helper 与表达式入口上的剩余错误矩阵。
# 使用示例: pytest -q test/dsl/ast/test_parser_private_helpers.py -k test_parser_private_helpers_dma_arch_and_expr_error_matrix
# 对应功能实现文件路径: kernel_gen/dsl/ast/parser.py
# 对应 spec 文件路径: spec/dsl/ast.md
# 对应测试文件路径: test/dsl/ast/test_parser_private_helpers.py
def test_parser_private_helpers_dma_arch_and_expr_error_matrix() -> None:
    dma_module = importlib.import_module("kernel_gen.operation.dma")
    nn_module = importlib.import_module("kernel_gen.operation.nn")
    arch_module = importlib.import_module("kernel_gen.operation.arch")

    globals_table = {
        "MemorySpace": MemorySpace,
        "NumericType": NumericType,
        "BarrierVisibility": arch_module.BarrierVisibility,
        "BarrierScope": arch_module.BarrierScope,
        "load": dma_module.load,
        "slice": dma_module.slice,
        "store": dma_module.store,
        "deslice": dma_module.deslice,
        "alloc": dma_module.alloc,
        "copy": dma_module.copy,
        "cast": dma_module.cast,
        "view": dma_module.view,
        "reshape": dma_module.reshape,
        "flatten": dma_module.flatten,
        "free": dma_module.free,
        "launch_kernel": arch_module.launch_kernel,
        "barrier": arch_module.barrier,
        "get_dynamic_memory": arch_module.get_dynamic_memory,
        "get_thread_num": arch_module.get_thread_num,
        "eq": nn_module.eq,
        "reduce_sum": nn_module.reduce_sum,
        "softmax": nn_module.softmax,
        "broadcast": nn_module.broadcast,
        "broadcast_to": nn_module.broadcast_to,
        "transpose": nn_module.transpose,
        "fc": nn_module.fc,
        "matmul": nn_module.matmul,
        "relu": nn_module.relu,
    }

    mem = Memory([SymbolDim("M"), SymbolDim("N")], NumericType.Float32)
    tensor = TensorAST(name="tensor", memory=mem, location=None)
    symbol_scalar = ScalarArgAST(name="sym", value_type=int, is_symbolic=True, location=None)
    float_scalar = ScalarArgAST(name="float_arg", value_type=float, is_symbolic=False, location=None)
    env = {
        "tensor": tensor,
        "sym": symbol_scalar,
        "float_arg": float_scalar,
        "callee": _parser_private_identity_callee,
    }

    with pytest.raises(parser_module._ParseFailure, match="Unsupported nn compare arity"):
        parser_module._parse_nn_compare_call(
            py_ast.parse("eq(tensor)", mode="eval").body,
            env,
            globals_table,
            _BUILTINS_TABLE,
        )

    with pytest.raises(parser_module._ParseFailure, match="Unsupported relu arity"):
        parser_module._parse_unary_helper_call(
            "relu",
            py_ast.parse("relu(tensor, tensor)", mode="eval").body,
            env,
            globals_table,
            _BUILTINS_TABLE,
        )
    with pytest.raises(parser_module._ParseFailure, match="Unsupported leaky_relu arity"):
        parser_module._parse_unary_helper_call(
            "leaky_relu",
            py_ast.parse("leaky_relu(tensor)", mode="eval").body,
            env,
            globals_table,
            _BUILTINS_TABLE,
        )
    with pytest.raises(parser_module._ParseFailure, match="Unsupported hard_sigmoid arity"):
        parser_module._parse_unary_helper_call(
            "hard_sigmoid",
            py_ast.parse("hard_sigmoid(tensor, 1, alpha=2)", mode="eval").body,
            env,
            globals_table,
            _BUILTINS_TABLE,
        )
    with pytest.raises(parser_module._ParseFailure, match="Unsupported call expression"):
        parser_module._parse_unary_helper_call(
            "unknown",
            py_ast.parse("unknown(tensor)", mode="eval").body,
            env,
            globals_table,
            _BUILTINS_TABLE,
        )

    with pytest.raises(parser_module._ParseFailure, match="Unsupported softmax arity"):
        parser_module._parse_softmax_helper_call(
            py_ast.parse("softmax(tensor, 1, axis=2)", mode="eval").body,
            env,
            globals_table,
            _BUILTINS_TABLE,
        )
    with pytest.raises(parser_module._ParseFailure, match="Unsupported reduce_sum arity"):
        parser_module._parse_reduce_helper_call(
            "reduce_sum",
            py_ast.parse("reduce_sum(tensor, 1, axis=2)", mode="eval").body,
            env,
            globals_table,
            _BUILTINS_TABLE,
        )

    with pytest.raises(parser_module._ParseFailure, match="load source must be TensorAST"):
        parser_module._parse_dma_call(
            py_ast.parse("load(sym, [0], [1])", mode="eval").body,
            env,
            globals_table,
            _BUILTINS_TABLE,
        )
    with pytest.raises(parser_module._ParseFailure, match="slice space must be MemorySpace"):
        parser_module._parse_dma_call(
            py_ast.parse("slice(tensor, [0], [1], [1], 1)", mode="eval").body,
            env,
            globals_table,
            _BUILTINS_TABLE,
        )
    with pytest.raises(parser_module._ParseFailure, match="store target must be TensorAST"):
        parser_module._parse_dma_call(
            py_ast.parse("store(tensor, sym, [0], [1])", mode="eval").body,
            env,
            globals_table,
            _BUILTINS_TABLE,
        )
    with pytest.raises(parser_module._ParseFailure, match="deslice space must be MemorySpace"):
        parser_module._parse_dma_call(
            py_ast.parse("deslice(tensor, tensor, [0], [1], [1], 1)", mode="eval").body,
            env,
            globals_table,
            _BUILTINS_TABLE,
        )

    with pytest.raises(parser_module._ParseFailure, match="Unsupported alloc arity"):
        parser_module._parse_dma_call(
            py_ast.parse("alloc([1], NumericType.Float32, stride=[1], stride=[1])", mode="eval").body,
            env,
            globals_table,
            _BUILTINS_TABLE,
        )
    with pytest.raises(parser_module._ParseFailure, match="alloc dtype must be NumericType"):
        parser_module._parse_dma_call(
            py_ast.parse("alloc([1], tensor)", mode="eval").body,
            env,
            globals_table,
            _BUILTINS_TABLE,
        )
    with pytest.raises(parser_module._ParseFailure, match="alloc space must be MemorySpace"):
        parser_module._parse_dma_call(
            py_ast.parse("alloc([1], NumericType.Float32, 1)", mode="eval").body,
            env,
            globals_table,
            _BUILTINS_TABLE,
        )
    with pytest.raises(parser_module._ParseFailure, match="copy space must be MemorySpace"):
        parser_module._parse_dma_call(
            py_ast.parse("copy(tensor, 1)", mode="eval").body,
            env,
            globals_table,
            _BUILTINS_TABLE,
        )
    with pytest.raises(parser_module._ParseFailure, match="Unsupported cast arity"):
        parser_module._parse_dma_call(
            py_ast.parse("cast(tensor, NumericType.Float32, space=MemorySpace.GM)", mode="eval").body,
            env,
            globals_table,
            _BUILTINS_TABLE,
        )
    with pytest.raises(parser_module._ParseFailure, match="cast memoryspace must be MemorySpace"):
        parser_module._parse_dma_call(
            py_ast.parse("cast(tensor, NumericType.Float32, memoryspace=1)", mode="eval").body,
            env,
            globals_table,
            _BUILTINS_TABLE,
        )
    with pytest.raises(parser_module._ParseFailure, match="Unsupported view arity"):
        parser_module._parse_dma_call(
            py_ast.parse("view(tensor, [0], [1])", mode="eval").body,
            env,
            globals_table,
            _BUILTINS_TABLE,
        )
    with pytest.raises(parser_module._ParseFailure, match="Unsupported reshape arity"):
        parser_module._parse_dma_call(
            py_ast.parse("reshape(tensor, [1], [1])", mode="eval").body,
            env,
            globals_table,
            _BUILTINS_TABLE,
        )
    with pytest.raises(parser_module._ParseFailure, match="Unsupported flatten arity"):
        parser_module._parse_dma_call(
            py_ast.parse("flatten(tensor, 1)", mode="eval").body,
            env,
            globals_table,
            _BUILTINS_TABLE,
        )
    with pytest.raises(parser_module._ParseFailure, match="Unsupported free arity"):
        parser_module._parse_dma_call(
            py_ast.parse("free()", mode="eval").body,
            env,
            globals_table,
            _BUILTINS_TABLE,
        )
    with pytest.raises(parser_module._ParseFailure, match="Unsupported img2col1d arity"):
        parser_module._parse_dma_call(
            py_ast.parse("img2col1d()", mode="eval").body,
            env,
            {"img2col1d": nn_module.img2col1d},
            _BUILTINS_TABLE,
        )
    with pytest.raises(parser_module._ParseFailure, match="Unsupported conv arity"):
        parser_module._parse_dma_call(
            py_ast.parse("conv(tensor, tensor, sh=1, sh=2)", mode="eval").body,
            env,
            {"conv": nn_module.conv},
            _BUILTINS_TABLE,
        )
    with pytest.raises(parser_module._ParseFailure, match="Unsupported broadcast arity"):
        parser_module._parse_dma_call(
            py_ast.parse("broadcast(tensor)", mode="eval").body,
            env,
            globals_table,
            _BUILTINS_TABLE,
        )
    with pytest.raises(parser_module._ParseFailure, match="Unsupported broadcast_to arity"):
        parser_module._parse_dma_call(
            py_ast.parse("broadcast_to(tensor, [1])", mode="eval").body,
            env,
            globals_table,
            _BUILTINS_TABLE,
        )
    with pytest.raises(parser_module._ParseFailure, match="Unsupported broadcast_to arity"):
        parser_module._parse_dma_call(
            py_ast.parse("broadcast_to(tensor, [1], MemorySpace.GM, target_shape=[1])", mode="eval").body,
            env,
            globals_table,
            _BUILTINS_TABLE,
        )
    with pytest.raises(parser_module._ParseFailure, match="transpose perm is required"):
        parser_module._parse_dma_call(
            py_ast.parse("transpose(tensor)", mode="eval").body,
            env,
            globals_table,
            _BUILTINS_TABLE,
        )
    with pytest.raises(parser_module._ParseFailure, match="Unsupported transpose arity"):
        parser_module._parse_dma_call(
            py_ast.parse("transpose(tensor, [1, 0], perm=[1, 0])", mode="eval").body,
            env,
            globals_table,
            _BUILTINS_TABLE,
        )
    with pytest.raises(parser_module._ParseFailure, match="Unsupported fc arity"):
        parser_module._parse_dma_call(
            py_ast.parse("fc(tensor)", mode="eval").body,
            env,
            globals_table,
            _BUILTINS_TABLE,
        )
    with pytest.raises(parser_module._ParseFailure, match="Unsupported matmul arity"):
        parser_module._parse_dma_call(
            py_ast.parse("matmul(tensor, tensor, MemorySpace.GM, memoryspace=MemorySpace.GM)", mode="eval").body,
            env,
            globals_table,
            _BUILTINS_TABLE,
        )
    with pytest.raises(parser_module._ParseFailure, match="matmul memoryspace must be MemorySpace"):
        parser_module._parse_dma_call(
            py_ast.parse("matmul(tensor, tensor, memoryspace=1)", mode="eval").body,
            env,
            globals_table,
            _BUILTINS_TABLE,
        )
    with pytest.raises(parser_module._ParseFailure, match="Unsupported get_thread_num arity"):
        parser_module._parse_dma_call(
            py_ast.parse("get_thread_num(1)", mode="eval").body,
            env,
            globals_table,
            _BUILTINS_TABLE,
        )
    with pytest.raises(parser_module._ParseFailure, match="get_dynamic_memory space must be MemorySpace"):
        parser_module._parse_dma_call(
            py_ast.parse("get_dynamic_memory(1)", mode="eval").body,
            env,
            globals_table,
            _BUILTINS_TABLE,
        )
    with pytest.raises(parser_module._ParseFailure, match="get_dynamic_memory space must be on-chip MemorySpace"):
        parser_module._parse_dma_call(
            py_ast.parse("get_dynamic_memory(MemorySpace.GM)", mode="eval").body,
            env,
            globals_table,
            _BUILTINS_TABLE,
        )
    with pytest.raises(parser_module._ParseFailure, match="Unsupported barrier arity"):
        parser_module._parse_dma_call(
            py_ast.parse(
                "barrier(visibility=[BarrierVisibility.TSM], visibility=[BarrierVisibility.TLM])",
                mode="eval",
            ).body,
            env,
            globals_table,
            _BUILTINS_TABLE,
        )
    with pytest.raises(parser_module._ParseFailure, match="barrier scope must be BarrierScope"):
        parser_module._parse_dma_call(
            py_ast.parse(
                "barrier(visibility=[BarrierVisibility.TSM], scope=1)",
                mode="eval",
            ).body,
            env,
            globals_table,
            _BUILTINS_TABLE,
        )

    with pytest.raises(parser_module._ParseFailure, match="Unsupported launch_kernel arity"):
        parser_module._parse_launch_kernel_call(
            py_ast.parse("launch_kernel()", mode="eval").body,
            env,
            globals_table,
            _BUILTINS_TABLE,
        )
    with pytest.raises(parser_module._ParseFailure, match="launch_kernel callee must be function symbol reference"):
        parser_module._parse_launch_kernel_call(
            py_ast.parse("launch_kernel(1, tensor)", mode="eval").body,
            env,
            globals_table,
            _BUILTINS_TABLE,
        )
    with pytest.raises(parser_module._ParseFailure, match="Unsupported launch_kernel arity"):
        parser_module._parse_launch_kernel_call(
            py_ast.parse("launch_kernel(callee, tensor)", mode="eval").body,
            env,
            globals_table,
            _BUILTINS_TABLE,
            launch_slice=py_ast.parse("(1, 2, 3)", mode="eval").body,
        )
    with pytest.raises(parser_module._ParseFailure, match="launch_kernel shared_memory_size must be >= 0"):
        parser_module._parse_launch_kernel_call(
            py_ast.parse("launch_kernel(callee, tensor)", mode="eval").body,
            env,
            globals_table,
            _BUILTINS_TABLE,
            launch_slice=py_ast.parse("(1, 1, 1, -1)", mode="eval").body,
        )
    with pytest.raises(parser_module._ParseFailure, match="launch_kernel block must be int or SymbolDim"):
        parser_module._parse_launch_kernel_call(
            py_ast.parse("launch_kernel(callee, float_arg, 1, 1, 0, tensor)", mode="eval").body,
            env,
            globals_table,
            _BUILTINS_TABLE,
        )

    assert parser_module._parse_python_callee_call(
        py_ast.parse("tensor.helper()", mode="eval").body,
        env,
        globals_table,
        _BUILTINS_TABLE,
    ) is None
    assert parser_module._parse_python_callee_call(
        py_ast.parse("callee(value=tensor)", mode="eval").body,
        env,
        globals_table,
        _BUILTINS_TABLE,
    ) is None
    assert parser_module._parse_python_callee_call(
        py_ast.parse("not_callable(tensor)", mode="eval").body,
        env,
        {"not_callable": object()},
        _BUILTINS_TABLE,
    ) is None

    globals_expr_table = {
        "mem_arg": Memory([2], NumericType.Float32),
        "sym_arg": SymbolDim("K"),
        "raw_obj": object(),
    }
    parsed_mem = parser_module._parse_expr(
        py_ast.parse("mem_arg", mode="eval").body,
        {},
        globals_expr_table,
        _BUILTINS_TABLE,
    )
    assert isinstance(parsed_mem, TensorAST)
    parsed_sym = parser_module._parse_expr(
        py_ast.parse("sym_arg", mode="eval").body,
        {},
        globals_expr_table,
        _BUILTINS_TABLE,
    )
    assert isinstance(parsed_sym, ScalarArgAST)
    assert parser_module._parse_expr(
        py_ast.parse("raw_obj", mode="eval").body,
        {},
        globals_expr_table,
        _BUILTINS_TABLE,
    ) is globals_expr_table["raw_obj"]
    parsed_stride = parser_module._parse_expr(
        py_ast.parse("tensor.get_stride()[0]", mode="eval").body,
        env,
        globals_table,
        _BUILTINS_TABLE,
    )
    assert isinstance(parsed_stride, TensorAxisAccessAST)
    assert parsed_stride.kind == "stride"
    with pytest.raises(parser_module._ParseFailure, match="Unknown name"):
        parser_module._parse_expr(py_ast.parse("missing", mode="eval").body, {}, {}, _BUILTINS_TABLE)
    with pytest.raises(parser_module._ParseFailure, match="Unsupported get_shape arity"):
        parser_module._parse_expr(
            py_ast.parse("tensor.get_shape(1)[0]", mode="eval").body,
            env,
            globals_table,
            _BUILTINS_TABLE,
        )
    with pytest.raises(parser_module._ParseFailure, match="Unsupported compare op"):
        parser_module._parse_expr(
            py_ast.parse("1 in tensor", mode="eval").body,
            env,
            globals_table,
            _BUILTINS_TABLE,
        )


# AST-PARSER-HELPER-012
# 创建者: 小李飞刀
# 最后一次更改: 小李飞刀
# 功能说明: 补齐 annotation/import/helper 解析上的剩余异常和回退分支。
# 使用示例: pytest -q test/dsl/ast/test_parser_private_helpers.py -k test_parser_private_helpers_annotation_import_and_unary_remaining_edges
# 对应功能实现文件路径: kernel_gen/dsl/ast/parser.py
# 对应 spec 文件路径: spec/dsl/ast.md
# 对应测试文件路径: test/dsl/ast/test_parser_private_helpers.py
def test_parser_private_helpers_annotation_import_and_unary_remaining_edges(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    runtime_table = {"N": SymbolDim("N"), "M": SymbolDim("M"), "bad_text": "oops"}
    builtins_with_mem = dict(_BUILTINS_TABLE)
    builtins_with_mem["mem_builtin"] = Memory([4], NumericType.Float32)

    with pytest.raises(parser_module._ParseFailure, match="Unsupported tensor dimension expression"):
        parser_module._eval_symbolic_dim_node(py_ast.parse('-"x"', mode="eval").body, None)
    with pytest.raises(parser_module._ParseFailure, match="Unsupported tensor dimension expression"):
        parser_module._eval_symbolic_dim_node(py_ast.parse("helper(1)", mode="eval").body, None)

    formatted_div_int_symbol = parser_module._eval_formatted_annotation_expr(
        py_ast.parse("1 / N", mode="eval").body,
        {},
        _BUILTINS_TABLE,
        runtime_table,
    )
    formatted_div_symbol_symbol = parser_module._eval_formatted_annotation_expr(
        py_ast.parse("N / M", mode="eval").body,
        {},
        _BUILTINS_TABLE,
        runtime_table,
    )
    assert isinstance(formatted_div_int_symbol, SymbolDim)
    assert isinstance(formatted_div_symbol_symbol, SymbolDim)
    with pytest.raises(parser_module._ParseFailure, match="Unsupported formatted annotation"):
        parser_module._eval_formatted_annotation_expr(
            py_ast.parse("-bad_text", mode="eval").body,
            {},
            _BUILTINS_TABLE,
            runtime_table,
        )
    with pytest.raises(parser_module._ParseFailure, match="Unsupported formatted annotation"):
        parser_module._eval_formatted_annotation_expr(
            py_ast.parse("N // 2", mode="eval").body,
            {},
            _BUILTINS_TABLE,
            runtime_table,
        )
    with pytest.raises(parser_module._ParseFailure, match="Unsupported formatted annotation"):
        parser_module._eval_formatted_annotation_expr(
            py_ast.parse("unsupported()", mode="eval").body,
            {},
            _BUILTINS_TABLE,
            runtime_table,
        )

    formatted_value = py_ast.FormattedValue(value=py_ast.Name(id="N", ctx=py_ast.Load()), conversion=-1, format_spec=None)
    monkeypatch.setattr(parser_module, "_eval_formatted_annotation_expr", lambda *args, **kwargs: object())
    with pytest.raises(parser_module._ParseFailure, match="Unsupported formatted annotation"):
        parser_module._format_joinedstr_value(formatted_value, {}, _BUILTINS_TABLE, runtime_table)

    unsupported_joined = py_ast.JoinedStr(values=[py_ast.Name(id="bad", ctx=py_ast.Load())])
    with pytest.raises(parser_module._ParseFailure, match="Unsupported annotation"):
        parser_module._normalize_annotation_text(unsupported_joined, {}, _BUILTINS_TABLE, runtime_table)
    with pytest.raises(parser_module._ParseFailure, match="Unsupported annotation"):
        parser_module._normalize_annotation_text(py_ast.Name(id="bad", ctx=py_ast.Load()), {}, _BUILTINS_TABLE, runtime_table)
    with pytest.raises(parser_module._ParseFailure, match="Unsupported tensor annotation element"):
        parser_module._tensor_annotation_text_from_subscript(py_ast.parse("Tensor[f32, N + 1]", mode="eval").body)

    builtin_tensor = parser_module._parse_annotation_node(None, "mem_builtin", {}, builtins_with_mem)
    assert isinstance(builtin_tensor, TensorAST)
    assert builtin_tensor.name == "mem_builtin"
    with pytest.raises(parser_module._ParseFailure, match="Unsupported annotation"):
        parser_module._parse_annotation_node(py_ast.parse("None", mode="eval").body, "x", {}, _BUILTINS_TABLE)
    with pytest.raises(parser_module._ParseFailure, match="Unsupported annotation"):
        parser_module._parse_annotation_node(py_ast.parse("int | Tensor[f32, 1]", mode="eval").body, "x", {}, _BUILTINS_TABLE)
    with pytest.raises(parser_module._ParseFailure, match="Unsupported annotation"):
        parser_module._parse_annotation_node(py_ast.parse("int | bool", mode="eval").body, "x", {}, _BUILTINS_TABLE)
    parsed_bool = parser_module._parse_annotation_node(py_ast.parse("bool", mode="eval").body, "flag", {}, _BUILTINS_TABLE)
    assert isinstance(parsed_bool, ScalarArgAST)
    assert parsed_bool.value_type is bool
    global_mem = Memory([2], NumericType.Float32)
    parsed_global_mem = parser_module._parse_annotation_node(
        py_ast.parse("global_mem", mode="eval").body,
        "gm",
        {"global_mem": global_mem},
        _BUILTINS_TABLE,
    )
    assert isinstance(parsed_global_mem, TensorAST)
    assert parsed_global_mem.memory == global_mem
    with pytest.raises(parser_module._ParseFailure, match="Unsupported annotation"):
        parser_module._parse_annotation_node(py_ast.parse("List[int]", mode="eval").body, "x", {"List": list}, _BUILTINS_TABLE)

    with pytest.raises(parser_module._ParseFailure, match="Unknown name"):
        parser_module._parse_attribute_object(py_ast.parse("missing.attr", mode="eval").body, {}, _BUILTINS_TABLE)
    with pytest.raises(parser_module._ParseFailure, match="Unknown attribute"):
        parser_module._parse_attribute_object(
            py_ast.parse("MemorySpace.LM.missing_attr", mode="eval").body,
            {"MemorySpace": MemorySpace},
            _BUILTINS_TABLE,
        )
    with pytest.raises(parser_module._ParseFailure, match="Unsupported attribute expression"):
        parser_module._parse_attribute_object(py_ast.parse("(1 + 2).real", mode="eval").body, {}, _BUILTINS_TABLE)

    resolved_attr = parser_module._resolve_call_base_object(
        py_ast.parse("MemorySpace.LM", mode="eval").body,
        {"MemorySpace": MemorySpace},
        _BUILTINS_TABLE,
    )
    assert resolved_attr is MemorySpace.LM
    with pytest.raises(parser_module._ParseFailure, match="Unsupported call expression"):
        parser_module._resolve_call_base_object(py_ast.parse("1", mode="eval").body, {}, _BUILTINS_TABLE)

    dma_module = importlib.import_module("kernel_gen.operation.dma")
    fake_dma_alias = types.ModuleType("kernel_gen.operation.dma")
    assert (
        parser_module._resolve_import_bound_helper_call(
            py_ast.parse("fake_dma.load", mode="eval").body,
            {"fake_dma": fake_dma_alias},
            _BUILTINS_TABLE,
        )
        is None
    )
    assert (
        parser_module._resolve_import_bound_helper_call(
            py_ast.parse("dma.unknown", mode="eval").body,
            {"dma": dma_module},
            _BUILTINS_TABLE,
        )
        is None
    )
    star_import_bindings: dict[str, object] = {}
    parser_module._bind_safe_local_import(
        py_ast.parse("from kernel_gen.operation.dma import *", mode="exec").body[0],
        star_import_bindings,
    )
    assert star_import_bindings == {}

    float_shadow = parser_module._parse_symbol_to_float_call(
        py_ast.parse("float(n)", mode="eval").body,
        {"n": SymbolDim("N")},
        {"float": lambda value: value},
        _BUILTINS_TABLE,
    )
    assert float_shadow is None

    tensor = TensorAST(name="tensor", memory=Memory([2, 2], NumericType.Float32), location=None)
    globals_table = {
        "MemorySpace": MemorySpace,
        "NumericType": NumericType,
    }
    env = {"tensor": tensor}

    with pytest.raises(parser_module._ParseFailure, match="Unsupported leaky_relu arity"):
        parser_module._parse_unary_helper_call(
            "leaky_relu",
            py_ast.parse("leaky_relu(tensor, 1, 2)", mode="eval").body,
            env,
            globals_table,
            _BUILTINS_TABLE,
        )
    with pytest.raises(parser_module._ParseFailure, match="Unsupported leaky_relu arity"):
        parser_module._parse_unary_helper_call(
            "leaky_relu",
            py_ast.parse("leaky_relu(tensor, alpha=1, beta=2)", mode="eval").body,
            env,
            globals_table,
            _BUILTINS_TABLE,
        )
    with pytest.raises(parser_module._ParseFailure, match="Unsupported leaky_relu arity"):
        parser_module._parse_unary_helper_call(
            "leaky_relu",
            py_ast.parse("leaky_relu(tensor, 1, alpha=2)", mode="eval").body,
            env,
            globals_table,
            _BUILTINS_TABLE,
        )
    with pytest.raises(parser_module._ParseFailure, match="Unsupported hard_sigmoid arity"):
        parser_module._parse_unary_helper_call(
            "hard_sigmoid",
            py_ast.parse("hard_sigmoid(tensor, 1, 2, 3)", mode="eval").body,
            env,
            globals_table,
            _BUILTINS_TABLE,
        )
    with pytest.raises(parser_module._ParseFailure, match="Unsupported hard_sigmoid arity"):
        parser_module._parse_unary_helper_call(
            "hard_sigmoid",
            py_ast.parse("hard_sigmoid(tensor, alpha=1, beta=2, gamma=3)", mode="eval").body,
            env,
            globals_table,
            _BUILTINS_TABLE,
        )

    with pytest.raises(parser_module._ParseFailure, match="Unsupported softmax arity"):
        parser_module._parse_softmax_helper_call(
            py_ast.parse("softmax()", mode="eval").body,
            env,
            globals_table,
            _BUILTINS_TABLE,
        )
    with pytest.raises(parser_module._ParseFailure, match="Unsupported softmax arity"):
        parser_module._parse_softmax_helper_call(
            py_ast.parse("softmax(tensor, axis=1, axis=2)", mode="eval").body,
            env,
            globals_table,
            _BUILTINS_TABLE,
        )

    parsed_reduce = parser_module._parse_reduce_helper_call(
        "reduce_sum",
        py_ast.parse("reduce_sum(tensor, 1, False)", mode="eval").body,
        env,
        globals_table,
        _BUILTINS_TABLE,
    )
    assert isinstance(parsed_reduce, NnReduceAST)
    assert parsed_reduce.keepdim is not None
    with pytest.raises(parser_module._ParseFailure, match="Unsupported reduce_sum arity"):
        parser_module._parse_reduce_helper_call(
            "reduce_sum",
            py_ast.parse("reduce_sum()", mode="eval").body,
            env,
            globals_table,
            _BUILTINS_TABLE,
        )
    with pytest.raises(parser_module._ParseFailure, match="Unsupported reduce_sum arity"):
        parser_module._parse_reduce_helper_call(
            "reduce_sum",
            py_ast.parse("reduce_sum(tensor, 1, False, keepdim=True)", mode="eval").body,
            env,
            globals_table,
            _BUILTINS_TABLE,
        )
    with pytest.raises(parser_module._ParseFailure, match="Unsupported reduce_sum arity"):
        parser_module._parse_reduce_helper_call(
            "reduce_sum",
            py_ast.parse("reduce_sum(tensor, other=1)", mode="eval").body,
            env,
            globals_table,
            _BUILTINS_TABLE,
        )


# AST-PARSER-HELPER-013
# 创建者: 小李飞刀
# 最后一次更改: 小李飞刀
# 功能说明: 补齐 DMA/launch/query/表达式入口的剩余正反向分支。
# 使用示例: pytest -q test/dsl/ast/test_parser_private_helpers.py -k test_parser_private_helpers_dma_launch_query_remaining_edges
# 对应功能实现文件路径: kernel_gen/dsl/ast/parser.py
# 对应 spec 文件路径: spec/dsl/ast.md
# 对应测试文件路径: test/dsl/ast/test_parser_private_helpers.py
def test_parser_private_helpers_dma_launch_query_remaining_edges() -> None:
    dma_module = importlib.import_module("kernel_gen.operation.dma")
    nn_module = importlib.import_module("kernel_gen.operation.nn")
    arch_module = importlib.import_module("kernel_gen.operation.arch")
    mem = Memory([2, 2], NumericType.Float32)
    tensor = TensorAST(name="tensor", memory=mem, location=None)
    callee = _parser_private_identity_callee

    env = {"tensor": tensor, "callee": callee}
    globals_table = {
        "MemorySpace": MemorySpace,
        "NumericType": NumericType,
        "BarrierVisibility": arch_module.BarrierVisibility,
        "BarrierScope": arch_module.BarrierScope,
        "alloc": dma_module.alloc,
        "broadcast": nn_module.broadcast,
        "broadcast_to": nn_module.broadcast_to,
        "transpose": nn_module.transpose,
        "fc": nn_module.fc,
        "get_block_num": arch_module.get_block_num,
        "get_subthread_id": arch_module.get_subthread_id,
        "get_subthread_num": arch_module.get_subthread_num,
        "get_thread_id": arch_module.get_thread_id,
        "get_dynamic_memory": arch_module.get_dynamic_memory,
    }

    none_keyword_alloc = py_ast.Call(
        func=py_ast.Name(id="alloc", ctx=py_ast.Load()),
        args=[
            py_ast.List(elts=[py_ast.Constant(1)], ctx=py_ast.Load()),
            py_ast.Attribute(value=py_ast.Name(id="NumericType", ctx=py_ast.Load()), attr="Float32", ctx=py_ast.Load()),
        ],
        keywords=[py_ast.keyword(arg=None, value=py_ast.Constant(1))],
    )
    with pytest.raises(parser_module._ParseFailure, match="Unsupported alloc arity"):
        parser_module._parse_dma_call(none_keyword_alloc, env, globals_table, _BUILTINS_TABLE)
    with pytest.raises(parser_module._ParseFailure, match="Unsupported alloc arity"):
        parser_module._parse_dma_call(
            py_ast.parse(
                "alloc([1], NumericType.Float32, MemorySpace.GM, space=MemorySpace.GM)",
                mode="eval",
            ).body,
            env,
            globals_table,
            _BUILTINS_TABLE,
        )
    with pytest.raises(parser_module._ParseFailure, match="Unsupported alloc arity"):
        parser_module._parse_dma_call(
            py_ast.parse(
                "alloc([1], NumericType.Float32, stride=[1], stride=[2])",
                mode="eval",
            ).body,
            env,
            globals_table,
            _BUILTINS_TABLE,
        )
    with pytest.raises(parser_module._ParseFailure, match="Unsupported alloc arity"):
        parser_module._parse_dma_call(
            py_ast.parse("alloc([1], NumericType.Float32, other=1)", mode="eval").body,
            env,
            globals_table,
            _BUILTINS_TABLE,
        )

    parsed_broadcast = parser_module._parse_dma_call(
        py_ast.parse("broadcast(tensor, [2, 2])", mode="eval").body,
        env,
        {**globals_table, "broadcast": nn_module.broadcast},
        _BUILTINS_TABLE,
    )
    assert parsed_broadcast is not None
    with pytest.raises(parser_module._ParseFailure, match="Unsupported broadcast_to arity"):
        parser_module._parse_dma_call(
            py_ast.parse(
                "broadcast_to(tensor, target_shape=[2, 2], space=MemorySpace.GM, space=MemorySpace.GM)",
                mode="eval",
            ).body,
            env,
            {**globals_table, "broadcast_to": nn_module.broadcast_to},
            _BUILTINS_TABLE,
        )
    with pytest.raises(parser_module._ParseFailure, match="Unsupported broadcast_to arity"):
        parser_module._parse_dma_call(
            py_ast.parse("broadcast_to(tensor, target_shape=[2, 2], other=1)", mode="eval").body,
            env,
            {**globals_table, "broadcast_to": nn_module.broadcast_to},
            _BUILTINS_TABLE,
        )

    none_keyword_transpose = py_ast.Call(
        func=py_ast.Name(id="transpose", ctx=py_ast.Load()),
        args=[py_ast.Name(id="tensor", ctx=py_ast.Load())],
        keywords=[py_ast.keyword(arg=None, value=py_ast.List(elts=[py_ast.Constant(1), py_ast.Constant(0)], ctx=py_ast.Load()))],
    )
    with pytest.raises(parser_module._ParseFailure, match="Unsupported transpose arity"):
        parser_module._parse_dma_call(
            py_ast.parse("transpose()", mode="eval").body,
            env,
            {**globals_table, "transpose": nn_module.transpose},
            _BUILTINS_TABLE,
        )
    with pytest.raises(parser_module._ParseFailure, match="Unsupported transpose arity"):
        parser_module._parse_dma_call(
            none_keyword_transpose,
            env,
            {**globals_table, "transpose": nn_module.transpose},
            _BUILTINS_TABLE,
        )
    with pytest.raises(parser_module._ParseFailure, match="Unsupported transpose arity"):
        parser_module._parse_dma_call(
            py_ast.parse("transpose(tensor, other=1)", mode="eval").body,
            env,
            {**globals_table, "transpose": nn_module.transpose},
            _BUILTINS_TABLE,
        )

    parsed_fc = parser_module._parse_dma_call(
        py_ast.parse("fc(tensor, tensor)", mode="eval").body,
        env,
        {**globals_table, "fc": nn_module.fc},
        _BUILTINS_TABLE,
    )
    assert parsed_fc is not None

    for query_name in ("get_block_num", "get_subthread_id", "get_subthread_num", "get_thread_id"):
        with pytest.raises(parser_module._ParseFailure, match=f"Unsupported {query_name} arity"):
            parser_module._parse_dma_call(
                py_ast.parse(f"{query_name}(1)", mode="eval").body,
                env,
                globals_table,
                _BUILTINS_TABLE,
            )
    with pytest.raises(parser_module._ParseFailure, match="Unsupported get_dynamic_memory arity"):
        parser_module._parse_dma_call(
            py_ast.parse("get_dynamic_memory()", mode="eval").body,
            env,
            globals_table,
            _BUILTINS_TABLE,
        )

    nameless_callee = _parser_private_identity_callee
    original_name = nameless_callee.__name__
    nameless_callee.__name__ = ""
    try:
        with pytest.raises(parser_module._ParseFailure, match="launch_kernel callee must be function symbol reference"):
            parser_module._parse_launch_kernel_call(
                py_ast.parse("launch_kernel(callee, tensor)", mode="eval").body,
                {"callee": nameless_callee, "tensor": tensor},
                {},
                _BUILTINS_TABLE,
            )
    finally:
        nameless_callee.__name__ = original_name

    with pytest.raises(parser_module._ParseFailure, match="launch_kernel block must be int or SymbolDim"):
        parser_module._parse_launch_kernel_call(
            py_ast.parse("launch_kernel(callee, tensor)", mode="eval").body,
            {"callee": callee, "tensor": tensor},
            {},
            _BUILTINS_TABLE,
            launch_slice=py_ast.parse("(1.5, 1, 1, 0)", mode="eval").body,
        )

    with pytest.raises(parser_module._ParseFailure, match="Unsupported for iterator"):
        parser_module._parse_for(
            py_ast.parse("for i in 4:\n    x = i", mode="exec").body[0],
            {},
            globals_table,
            _BUILTINS_TABLE,
        )


# AST-PARSER-HELPER-014
# 创建者: 小李飞刀
# 最后一次更改: 小李飞刀
# 功能说明: 补齐 launch raw-int 校验与 DMA/NN helper 剩余 arity 回退分支。
# 使用示例: pytest -q test/dsl/ast/test_parser_private_helpers.py -k test_parser_private_helpers_launch_and_helper_remaining_edges
# 对应功能实现文件路径: kernel_gen/dsl/ast/parser.py
# 对应 spec 文件路径: spec/dsl/ast.md
# 对应测试文件路径: test/dsl/ast/test_parser_private_helpers.py
def test_parser_private_helpers_launch_and_helper_remaining_edges(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    dma_module = importlib.import_module("kernel_gen.operation.dma")
    nn_module = importlib.import_module("kernel_gen.operation.nn")
    arch_module = importlib.import_module("kernel_gen.operation.arch")

    tensor = TensorAST(name="tensor", memory=Memory([2, 2], NumericType.Float32), location=None)
    env = {
        "tensor": tensor,
        "callee": _parser_private_identity_callee,
        "block_i": 2,
        "thread_i": 3,
        "sub_i": 1,
        "shared_i": 0,
        "zero_block": 0,
        "neg_shared": -1,
        "bad_extent": 1.5,
    }
    globals_table = {
        "MemorySpace": MemorySpace,
        "NumericType": NumericType,
        "alloc": dma_module.alloc,
        "copy": dma_module.copy,
        "cast": dma_module.cast,
        "launch_kernel": arch_module.launch_kernel,
        "broadcast_to": nn_module.broadcast_to,
        "img2col1d": nn_module.img2col1d,
        "matmul": nn_module.matmul,
    }

    launch_call = py_ast.parse("launch_kernel(callee, tensor)", mode="eval").body
    parsed_launch = parser_module._parse_launch_kernel_call(
        launch_call,
        env,
        globals_table,
        _BUILTINS_TABLE,
        launch_slice=py_ast.parse("(block_i, thread_i, sub_i, shared_i)", mode="eval").body,
    )
    assert isinstance(parsed_launch, ArchLaunchKernelAST)

    with pytest.raises(parser_module._ParseFailure, match="launch_kernel block must be > 0"):
        parser_module._parse_launch_kernel_call(
            launch_call,
            env,
            globals_table,
            _BUILTINS_TABLE,
            launch_slice=py_ast.parse("(zero_block, thread_i, sub_i, shared_i)", mode="eval").body,
        )
    with pytest.raises(parser_module._ParseFailure, match="launch_kernel shared_memory_size must be >= 0"):
        parser_module._parse_launch_kernel_call(
            launch_call,
            env,
            globals_table,
            _BUILTINS_TABLE,
            launch_slice=py_ast.parse("(block_i, thread_i, sub_i, neg_shared)", mode="eval").body,
        )
    with pytest.raises(parser_module._ParseFailure, match="launch_kernel block must be int or SymbolDim"):
        parser_module._parse_launch_kernel_call(
            launch_call,
            env,
            globals_table,
            _BUILTINS_TABLE,
            launch_slice=py_ast.parse("(bad_extent, thread_i, sub_i, shared_i)", mode="eval").body,
        )

    with pytest.raises(parser_module._ParseFailure, match="Unsupported alloc arity"):
        parser_module._parse_dma_call(
            py_ast.parse("alloc([1])", mode="eval").body,
            env,
            globals_table,
            _BUILTINS_TABLE,
        )
    with pytest.raises(parser_module._ParseFailure, match="Unsupported alloc arity"):
        parser_module._parse_dma_call(
            py_ast.parse(
                "alloc([1], NumericType.Float32, space=MemorySpace.GM, stride=[1], other=1)",
                mode="eval",
            ).body,
            env,
            globals_table,
            _BUILTINS_TABLE,
        )
    with pytest.raises(parser_module._ParseFailure, match="Unsupported copy arity"):
        parser_module._parse_dma_call(
            py_ast.parse("copy(tensor, MemorySpace.GM, tensor)", mode="eval").body,
            env,
            globals_table,
            _BUILTINS_TABLE,
        )
    with pytest.raises(parser_module._ParseFailure, match="Unsupported cast arity"):
        parser_module._parse_dma_call(
            py_ast.parse("cast(tensor)", mode="eval").body,
            env,
            globals_table,
            _BUILTINS_TABLE,
        )
    with pytest.raises(parser_module._ParseFailure, match="Unsupported cast arity"):
        parser_module._parse_dma_call(
            py_ast.parse(
                "cast(tensor, NumericType.Float32, memoryspace=MemorySpace.GM, extra=MemorySpace.GM)",
                mode="eval",
            ).body,
            env,
            globals_table,
            _BUILTINS_TABLE,
        )
    with pytest.raises(parser_module._ParseFailure, match="Unsupported matmul arity"):
        parser_module._parse_dma_call(
            py_ast.parse("matmul(tensor, tensor, memoryspace=MemorySpace.GM, other=1)", mode="eval").body,
            env,
            globals_table,
            _BUILTINS_TABLE,
        )
    with pytest.raises(parser_module._ParseFailure, match="Unsupported broadcast_to arity"):
        parser_module._parse_dma_call(
            py_ast.parse("broadcast_to()", mode="eval").body,
            env,
            globals_table,
            _BUILTINS_TABLE,
        )

    img2col_none_keyword = py_ast.Call(
        func=py_ast.Name(id="img2col1d", ctx=py_ast.Load()),
        args=[py_ast.Name(id="tensor", ctx=py_ast.Load())],
        keywords=[py_ast.keyword(arg=None, value=py_ast.Constant(value=1))],
    )
    with pytest.raises(parser_module._ParseFailure, match="Unsupported img2col1d arity"):
        parser_module._parse_dma_call(
            img2col_none_keyword,
            env,
            globals_table,
            _BUILTINS_TABLE,
        )

    broadcast_to_none_keyword = py_ast.Call(
        func=py_ast.Name(id="broadcast_to", ctx=py_ast.Load()),
        args=[py_ast.Name(id="tensor", ctx=py_ast.Load())],
        keywords=[
            py_ast.keyword(
                arg=None,
                value=py_ast.List(elts=[py_ast.Constant(value=2), py_ast.Constant(value=2)], ctx=py_ast.Load()),
            )
        ],
    )
    with pytest.raises(parser_module._ParseFailure, match="Unsupported broadcast_to arity"):
        parser_module._parse_dma_call(
            broadcast_to_none_keyword,
            env,
            globals_table,
            _BUILTINS_TABLE,
        )

    monkeypatch.setattr(parser_module, "_resolve_import_bound_helper_call", lambda *_args, **_kwargs: "img2col")
    with pytest.raises(parser_module._ParseFailure, match="Unsupported img2col call"):
        parser_module._parse_dma_call(
            py_ast.parse("shim(tensor)", mode="eval").body,
            env,
            globals_table,
            _BUILTINS_TABLE,
        )

    monkeypatch.setattr(parser_module, "_resolve_import_bound_helper_call", lambda *_args, **_kwargs: "unknown_helper")
    assert (
        parser_module._parse_dma_call(
            py_ast.parse("shim(tensor)", mode="eval").body,
            env,
            globals_table,
            _BUILTINS_TABLE,
        )
        is None
    )
