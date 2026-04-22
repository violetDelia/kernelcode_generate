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
