"""DSL AST attr node tests.


功能说明:
- 覆盖 `kernel_gen.dsl.ast.nodes.attr` 的属性节点构造与 `emit_mlir(...)`。
- 测试结构对应 `spec/dsl/ast/nodes/attr.md` 与 `kernel_gen/dsl/ast/nodes/attr.py`。

使用示例:
- pytest -q test/dsl/ast/nodes/test_attr.py

关联文件:
- 功能实现: kernel_gen/dsl/ast/nodes/attr.py
- Spec 文档: spec/dsl/ast/nodes/attr.md
- 测试文件: test/dsl/ast/nodes/test_attr.py
"""

from __future__ import annotations

import ast
from types import SimpleNamespace

import pytest
from xdsl.context import Context
from xdsl.dialects.builtin import BFloat16Type, Float16Type, Float32Type, Float64Type, IntAttr, IntegerType, i1, i32, i64, i8

from kernel_gen.core.error import KernelCodeError
from kernel_gen.dialect.nn import NnMemorySpaceAttr
from kernel_gen.dsl.ast.nodes.attr import (
    AttrAST,
    BoolTypeAttrAST,
    Diagnostic,
    FloatTypeAttrAST,
    IntTypeAttrAST,
    ListAST,
    MemorySpaceAttrAST,
    PythonObjectAttrAST,
    SourceLocation,
    TupleAST,
)
from kernel_gen.dsl.ast.nodes.symbol import ConstValueAST
from kernel_gen.symbol_variable.memory import MemorySpace
from kernel_gen.symbol_variable.type import NumericType


class MemoryTypeStub:
    """测试 `runtime_space_from_memory_type(...)` 所需的公开 space 载体。"""

    def __init__(self, space_name: str) -> None:
        self.space = NnMemorySpaceAttr.from_name(space_name)


class InvalidMemoryTypeStub:
    """测试非法 memory space 文本的公开错误边界。"""

    space = SimpleNamespace(space=SimpleNamespace(data="invalid"))


def test_attr_source_location_and_diagnostic_store_fields() -> None:
    """构造 SourceLocation / Diagnostic 并读取公开字段。"""

    loc = SourceLocation(line=1, column=2)
    diag = Diagnostic(message="Unsupported syntax", location=loc)
    parsed = ast.parse("x = 1").body[0]
    parsed_loc = SourceLocation.from_py_ast(parsed)

    assert loc.line == 1
    assert loc.column == 2
    assert diag.message == "Unsupported syntax"
    assert diag.location is loc
    assert parsed_loc == SourceLocation(line=1, column=0)


def test_attr_ast_emits_wrapped_xdsl_attribute() -> None:
    """AttrAST 作为公开节点直接返回承载的 xDSL Attribute。"""

    attr = IntAttr(7)
    node = AttrAST(attr)

    assert node.emit_mlir(Context(), None) is attr
    assert node == AttrAST(attr)
    assert node == attr


def test_python_list_and_tuple_attr_nodes_emit_public_items() -> None:
    """PythonObjectAttrAST/ListAST/TupleAST 保存并发射公开属性项。"""

    ctx = Context()
    py_attr = PythonObjectAttrAST("axis")
    list_node = ListAST([ConstValueAST(1), py_attr])
    tuple_node = TupleAST((ConstValueAST(2), py_attr))

    list_result = list_node.emit_mlir(ctx, None)
    tuple_result = tuple_node.emit_mlir(ctx, None)

    assert py_attr.emit_mlir(ctx, None) == "axis"
    assert isinstance(list_result, list)
    assert list_result[1] == "axis"
    assert isinstance(tuple_result, tuple)
    assert tuple_result[1] == "axis"


def test_specific_attr_nodes_emit_xdsl_attrs() -> None:
    """类型与 space 属性由公开 AttrNODE 承接。"""

    ctx = Context()

    bit_attr = IntTypeAttrAST(1).emit_mlir(ctx, None)
    int8_attr = IntTypeAttrAST(8).emit_mlir(ctx, None)
    uint8_attr = IntTypeAttrAST(8, signed=False).emit_mlir(ctx, None)
    int_attr = IntTypeAttrAST(32).emit_mlir(ctx, None)
    uint32_attr = IntTypeAttrAST(32, signed=False).emit_mlir(ctx, None)
    int64_attr = IntTypeAttrAST(64).emit_mlir(ctx, None)
    uint64_attr = IntTypeAttrAST(64, signed=False).emit_mlir(ctx, None)
    uint_attr = IntTypeAttrAST(16, signed=False).emit_mlir(ctx, None)
    float16_attr = FloatTypeAttrAST(NumericType.Float16).emit_mlir(ctx, None)
    bfloat16_attr = FloatTypeAttrAST(NumericType.BFloat16).emit_mlir(ctx, None)
    float_attr = FloatTypeAttrAST(NumericType.Float32).emit_mlir(ctx, None)
    float64_attr = FloatTypeAttrAST(NumericType.Float64).emit_mlir(ctx, None)
    bool_attr = BoolTypeAttrAST().emit_mlir(ctx, None)
    space_attr = MemorySpaceAttrAST(MemorySpace.GM).emit_mlir(ctx, None)

    assert bit_attr == i1
    assert int8_attr == i8
    assert isinstance(uint8_attr, IntegerType)
    assert int_attr == i32
    assert isinstance(uint32_attr, IntegerType)
    assert int64_attr == i64
    assert isinstance(uint64_attr, IntegerType)
    assert isinstance(uint_attr, IntegerType)
    assert isinstance(float16_attr, Float16Type)
    assert isinstance(bfloat16_attr, BFloat16Type)
    assert isinstance(float_attr, Float32Type)
    assert isinstance(float64_attr, Float64Type)
    assert bool_attr == i1
    assert isinstance(space_attr, NnMemorySpaceAttr)

    with pytest.raises(KernelCodeError, match="FloatTypeAttrAST dtype must be float NumericType"):
        FloatTypeAttrAST(NumericType.Int32).emit_mlir(ctx, None)


def test_memory_space_attr_restores_runtime_space() -> None:
    """MemorySpaceAttrAST 负责公开 memory space 双向转换。"""

    expected_names = {
        MemorySpace.GM: "global",
        MemorySpace.SM: "shared",
        MemorySpace.LM: "local",
        MemorySpace.TSM: "tsm",
        MemorySpace.TLM1: "tlm1",
        MemorySpace.TLM2: "tlm2",
        MemorySpace.TLM3: "tlm3",
    }

    for space, name in expected_names.items():
        space_attr = MemorySpaceAttrAST(space).emit_mlir(Context(), None)

        assert isinstance(space_attr, NnMemorySpaceAttr)
        assert space_attr.space.data == name
        assert MemorySpaceAttrAST.runtime_space_from_memory_type(MemoryTypeStub(name)) is space

    with pytest.raises(KernelCodeError, match="Unsupported callee memory space"):
        MemorySpaceAttrAST.runtime_space_from_memory_type(InvalidMemoryTypeStub)
    with pytest.raises(KernelCodeError, match="Unsupported memory space"):
        MemorySpaceAttrAST("invalid").emit_mlir(Context(), None)
