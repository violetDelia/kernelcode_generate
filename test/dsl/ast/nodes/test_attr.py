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

from xdsl.context import Context
from xdsl.dialects.builtin import Float32Type, IntAttr, IntegerType, i1, i32

from kernel_gen.dialect.nn import NnMemorySpaceAttr
from kernel_gen.dsl.ast.nodes.attr import (
    AttrAST,
    BoolTypeAttrAST,
    Diagnostic,
    FloatTypeAttrAST,
    IntTypeAttrAST,
    MemorySpaceAttrAST,
    SourceLocation,
)
from kernel_gen.symbol_variable.memory import MemorySpace
from kernel_gen.symbol_variable.type import NumericType


def test_attr_source_location_and_diagnostic_store_fields() -> None:
    """构造 SourceLocation / Diagnostic 并读取公开字段。"""

    loc = SourceLocation(line=1, column=2)
    diag = Diagnostic(message="Unsupported syntax", location=loc)

    assert loc.line == 1
    assert loc.column == 2
    assert diag.message == "Unsupported syntax"
    assert diag.location is loc


def test_attr_ast_emits_wrapped_xdsl_attribute() -> None:
    """AttrAST 作为公开节点直接返回承载的 xDSL Attribute。"""

    attr = IntAttr(7)
    node = AttrAST(attr)

    assert node.emit_mlir(Context(), None) is attr


def test_specific_attr_nodes_emit_xdsl_attrs() -> None:
    """类型与 space 属性由公开 AttrNODE 承接。"""

    ctx = Context()

    int_attr = IntTypeAttrAST(32).emit_mlir(ctx, None)
    uint_attr = IntTypeAttrAST(16, signed=False).emit_mlir(ctx, None)
    float_attr = FloatTypeAttrAST(NumericType.Float32).emit_mlir(ctx, None)
    bool_attr = BoolTypeAttrAST().emit_mlir(ctx, None)
    space_attr = MemorySpaceAttrAST(MemorySpace.GM).emit_mlir(ctx, None)

    assert int_attr == i32
    assert isinstance(uint_attr, IntegerType)
    assert isinstance(float_attr, Float32Type)
    assert bool_attr == i1
    assert isinstance(space_attr, NnMemorySpaceAttr)


def test_memory_space_attr_restores_runtime_space() -> None:
    """MemorySpaceAttrAST 负责公开 memory space 双向转换。"""

    class MemoryTypeStub:
        space = NnMemorySpaceAttr.from_name("tsm")

    assert MemorySpaceAttrAST.runtime_space_from_memory_type(MemoryTypeStub) is MemorySpace.TSM
