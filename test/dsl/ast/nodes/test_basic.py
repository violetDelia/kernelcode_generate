"""DSL AST basic node tests.


功能说明:
- 覆盖 `kernel_gen.dsl.ast.nodes.basic` 的基础节点字段、block 结构与输入迭代。
- 测试结构对应 `spec/dsl/ast/nodes/basic.md` 与 `kernel_gen/dsl/ast/nodes/basic.py`。

使用示例:
- pytest -q test/dsl/ast/nodes/test_basic.py

关联文件:
- 功能实现: kernel_gen/dsl/ast/nodes/basic.py
- Spec 文档: spec/dsl/ast/nodes/basic.md
- 测试文件: test/dsl/ast/nodes/test_basic.py
"""

from __future__ import annotations

import importlib

import pytest
from xdsl.context import Context

from kernel_gen.core.error import KernelCodeError
from kernel_gen.dialect.nn import NnMemoryType
from kernel_gen.dsl.ast.nodes.attr import SourceLocation
from kernel_gen.dsl.ast.nodes.basic import (
    BlockAST,
    BoolValueAST,
    BoundExprAST,
    CallAST,
    FunctionAST,
    MemoryAST,
    ReturnAST,
)
from kernel_gen.dsl.ast.nodes.symbol import ConstValueAST, SymbolAddAST, SymbolDimAST, SymbolListAST
from kernel_gen.dsl.ast.nodes.attr import FloatTypeAttrAST, MemorySpaceAttrAST
from kernel_gen.symbol_variable.memory import Memory, MemorySpace
from kernel_gen.symbol_variable.symbol_dim import SymbolDim
from kernel_gen.symbol_variable.type import NumericType


def test_basic_nodes_construct_expr_block() -> None:
    """构造表达式节点并挂载到 BlockAST。"""

    loc = SourceLocation(line=3, column=0)
    lhs = SymbolDimAST(SymbolDim("x"), location=loc)
    rhs = ConstValueAST(1, location=loc)
    expr = SymbolAddAST(lhs, rhs, location=loc)
    bound = BoundExprAST(name="tmp", target=SymbolDimAST("tmp", location=loc), value=expr, location=loc)
    block = BlockAST(statements=[bound], location=loc)

    assert block.statements[0] is bound
    assert bound.value is expr
    assert expr.rhs is rhs


def test_function_ast_iter_inputs_returns_declared_inputs() -> None:
    """FunctionAST.iter_inputs() 按声明顺序返回 tensor / scalar 输入。"""

    tensor = MemoryAST(
        "x",
        SymbolListAST([SymbolDim("N")]),
        SymbolListAST([1]),
        FloatTypeAttrAST(NumericType.Float32),
        MemorySpaceAttrAST(MemorySpace.GM),
    )
    scalar = SymbolDimAST("n")
    func_ast = FunctionAST("kernel", [tensor, scalar], [], BlockAST([]))

    assert list(func_ast.iter_inputs()) == [tensor, scalar]
    assert func_ast.name == "kernel"
    assert func_ast.body.statements == []


def test_function_ast_constructs_inputs_from_runtime_args() -> None:
    """FunctionAST.input_from_runtime_arg() 统一 runtime 参数到输入 AST 的构造。"""

    memory = Memory([SymbolDim("N")], NumericType.Float32, space=MemorySpace.TSM)
    memory_input = FunctionAST.input_from_runtime_arg("x", memory)
    symbol_input = FunctionAST.input_from_runtime_arg("n", SymbolDim("N"))
    int_input = FunctionAST.input_from_runtime_arg("tile", 8)
    float_input = FunctionAST.input_from_runtime_arg("scale", 1.5)
    bool_input = FunctionAST.input_from_runtime_arg("flag", True)

    assert isinstance(memory_input, MemoryAST)
    assert memory_input.memory == memory
    assert isinstance(symbol_input, SymbolDimAST)
    assert symbol_input.result_symbol() == SymbolDim("N")
    assert isinstance(int_input, SymbolDimAST)
    assert int_input.result_symbol() == 8
    assert isinstance(float_input, ConstValueAST)
    assert float_input.raw_value == 1.5
    assert isinstance(bool_input, BoolValueAST)
    assert bool_input.raw_value is True


def test_function_ast_constructs_inputs_from_bound_values() -> None:
    """FunctionAST.input_from_bound_value() 统一 caller 侧 DSL 值到 callee 输入 AST 的构造。"""

    source = MemoryAST(
        "tile",
        SymbolListAST([4]),
        SymbolListAST([1]),
        FloatTypeAttrAST(NumericType.Float32),
        MemorySpaceAttrAST(MemorySpace.TSM),
    )
    bound_memory = FunctionAST.input_from_bound_value("x", source)
    bound_symbol = FunctionAST.input_from_bound_value("n", SymbolDimAST("tile", runtime_symbol=SymbolDim("TILE")))
    bound_bool = FunctionAST.input_from_bound_value("flag", BoolValueAST(False))
    bound_const = FunctionAST.input_from_bound_value("scale", ConstValueAST(2.0))

    assert isinstance(bound_memory, MemoryAST)
    assert bound_memory.name == "x"
    assert bound_memory.memory == source.memory
    assert isinstance(bound_symbol, SymbolDimAST)
    assert bound_symbol.name == "n"
    assert bound_symbol.result_symbol() == SymbolDim("TILE")
    assert isinstance(bound_bool, BoolValueAST)
    assert bound_bool.raw_value is False
    assert isinstance(bound_const, ConstValueAST)
    assert bound_const.raw_value == 2.0


def test_value_result_semantics_are_owned_by_nodes() -> None:
    """ValueAST 子类通过公开 result_* 入口暴露解析期语义。"""

    runtime_symbol = SymbolDim("TILE")
    symbol = SymbolDimAST("step", runtime_symbol=runtime_symbol)
    const = ConstValueAST(4)
    shape = SymbolListAST([symbol, const])
    memory = MemoryAST(
        "x",
        shape,
        SymbolListAST([runtime_symbol, 1]),
        FloatTypeAttrAST(NumericType.Float32),
        MemorySpaceAttrAST(MemorySpace.GM),
    )

    assert symbol.name == "step"
    assert symbol.result_symbol() is runtime_symbol
    assert const.result_symbol() == 4
    assert const.result_scalar() == 4
    assert shape.result_symbols() == [runtime_symbol, 4]
    assert memory.result_memory() == memory.memory
    assert memory.binding_value() == memory.memory
    assert isinstance(memory.bind_target("alias", SourceLocation(line=8, column=2)), MemoryAST)
    assert isinstance(symbol.bind_target("tile", SourceLocation(line=9, column=2)), SymbolDimAST)
    assert isinstance(BoolValueAST(True).bind_target("flag", SourceLocation(line=10, column=2)), BoolValueAST)


def test_memory_ast_builds_mlir_type_from_runtime_memory() -> None:
    """MemoryAST.type_from_memory() 是 Memory -> NnMemoryType 的统一入口。"""

    memory = MemoryAST(
        "x",
        SymbolListAST([2, 4]),
        SymbolListAST([4, 1]),
        FloatTypeAttrAST(NumericType.Float32),
        MemorySpaceAttrAST(MemorySpace.TSM),
    )
    memory_type = MemoryAST.type_from_memory(Context(), memory.memory)

    assert isinstance(memory_type, NnMemoryType)
    assert str(memory_type) == "!nn.memory<[2, 4], [4, 1], f32, #nn.space<tsm>>"


def test_call_ast_constructs_from_parsed_callee() -> None:
    """CallAST 只允许构造无返回 Python callee 语句调用。"""

    scalar = SymbolDimAST("n")
    callee = FunctionAST(
        "helper",
        [scalar],
        [],
        BlockAST([]),
        returns_none=True,
        runtime_args=(SymbolDim("N"),),
    )
    call = CallAST(callee, [scalar])

    assert call.callee is callee
    assert call.args == [scalar]


def test_call_ast_rejects_callee_return_value() -> None:
    """CallAST 不推导 callee 返回类型，显式返回值直接失败。"""

    scalar = SymbolDimAST("n")
    callee = FunctionAST(
        "helper",
        [scalar],
        [],
        BlockAST([scalar]),
        has_explicit_return=True,
        returns_none=False,
        runtime_args=(SymbolDim("N"),),
    )

    with pytest.raises(KernelCodeError, match="Python callee return value is unsupported"):
        CallAST(callee, [scalar])


def test_return_ast_accepts_multiple_values() -> None:
    """ReturnAST 承接 0/1/N 个返回值，不再把函数返回压成最后一个表达式。"""

    lhs = SymbolDimAST("lhs")
    rhs = SymbolDimAST("rhs")
    empty_return = ReturnAST()
    single_return = ReturnAST(lhs)
    multi_return = ReturnAST([lhs, rhs])

    assert empty_return.values == ()
    assert single_return.values == (lhs,)
    assert multi_return.values == (lhs, rhs)


def test_basic_module_does_not_define_legacy_nodes() -> None:
    """basic.py 不再保留旧宽泛节点定义。"""

    basic = importlib.import_module("kernel_gen.dsl.ast.nodes.basic")

    for name in (
        "TensorAST",
        "ScalarArgAST",
        "PtrArgAST",
        "VarAST",
        "ConstAST",
        "BinaryExprAST",
        "CompareExprAST",
        "SymbolAddAST",
        "SymbolDimAST",
        "SymbolListAST",
        "IfAST",
    ):
        assert not hasattr(basic, name)
