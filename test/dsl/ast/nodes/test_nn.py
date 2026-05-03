"""DSL AST NN node tests.


功能说明:
- 覆盖 `kernel_gen.dsl.ast.nodes.nn` 的公开节点构造与小范围字段归一。
- 测试结构对应 `spec/dsl/ast/nodes/nn.md` 与 `kernel_gen/dsl/ast/nodes/nn.py`。

使用示例:
- pytest -q test/dsl/ast/nodes/test_nn.py

关联文件:
- 功能实现: kernel_gen/dsl/ast/nodes/nn.py
- Spec 文档: spec/dsl/ast/nodes/nn.md
- 测试文件: test/dsl/ast/nodes/test_nn.py
"""

from __future__ import annotations

from dataclasses import fields

from kernel_gen.dsl.ast.nodes.attr import FloatTypeAttrAST, MemorySpaceAttrAST
from kernel_gen.dsl.ast.nodes.basic import MemoryAST
from kernel_gen.dsl.ast.nodes.symbol import ConstValueAST, SymbolListAST
from kernel_gen.dsl.ast.nodes.nn import ConvAST, MatmulAST, NnAddAST, NnBroadcastToAST, NnEqAST, NnImg2Col1dAST, NnReduceAST, NnReduceMaxAST, NnReduceMinAST, NnReduceSumAST, NnReluAST
from kernel_gen.symbol_variable.memory import MemorySpace
from kernel_gen.symbol_variable.type import NumericType


def test_nn_binary_node_stores_exact_operation_kind_and_operands() -> None:
    """每个 NN 二元 op 节点保存唯一 op kind 与两个 DSLNode operand。"""

    lhs = MemoryAST("lhs", SymbolListAST([4]), SymbolListAST([1]), FloatTypeAttrAST(NumericType.Float32), MemorySpaceAttrAST(MemorySpace.GM))
    rhs = MemoryAST("rhs", SymbolListAST([4]), SymbolListAST([1]), FloatTypeAttrAST(NumericType.Float32), MemorySpaceAttrAST(MemorySpace.GM))
    node = NnAddAST(lhs, rhs)

    assert node.lhs is lhs
    assert node.rhs is rhs


def test_nn_unary_node_stores_kind_and_optional_parameters() -> None:
    """NnReluAST 继承 unary 节点字段并保留 alpha/beta 形态。"""

    value = MemoryAST("x", SymbolListAST([4]), SymbolListAST([1]), FloatTypeAttrAST(NumericType.Float32), MemorySpaceAttrAST(MemorySpace.GM))
    node = NnReluAST(value)

    assert node.value is value


def test_nn_broadcast_to_normalizes_shape_and_space_nodes() -> None:
    """broadcast_to 的 target_shape 与 space 使用公开属性节点承接。"""

    source = MemoryAST("x", SymbolListAST([1, 4]), SymbolListAST([4, 1]), FloatTypeAttrAST(NumericType.Float32), MemorySpaceAttrAST(MemorySpace.GM))
    node = NnBroadcastToAST(source, SymbolListAST([2, 4]), MemorySpace.TSM)

    assert node.source is source
    assert isinstance(node.target_shape, SymbolListAST)
    assert isinstance(node.space, MemorySpaceAttrAST)
    assert node.space.space is MemorySpace.TSM


def test_nn_matmul_and_img2col_store_structured_members() -> None:
    """matmul / img2col 节点不下沉到 Python callable 桥接结构。"""

    lhs = MemoryAST("lhs", SymbolListAST([4, 8]), SymbolListAST([8, 1]), FloatTypeAttrAST(NumericType.Float32), MemorySpaceAttrAST(MemorySpace.GM))
    rhs = MemoryAST("rhs", SymbolListAST([8, 16]), SymbolListAST([16, 1]), FloatTypeAttrAST(NumericType.Float32), MemorySpaceAttrAST(MemorySpace.GM))
    matmul = MatmulAST(lhs, rhs, MemorySpace.TSM)
    img2col = NnImg2Col1dAST(lhs, ConstValueAST(3))

    assert matmul.lhs is lhs
    assert matmul.rhs is rhs
    assert isinstance(matmul.memoryspace, MemorySpaceAttrAST)
    assert img2col.source is lhs
    assert isinstance(img2col.kw, ConstValueAST)


def test_nn_nodes_do_not_expose_legacy_dispatch_fields() -> None:
    """NN 节点字段不再使用旧 op/kind/args/kwargs 分派结构。"""

    legacy_fields = {"op", "kind", "args", "kwargs"}

    for node_type in (NnAddAST, NnEqAST, NnReluAST, NnReduceAST, NnReduceSumAST, NnImg2Col1dAST, ConvAST):
        assert legacy_fields.isdisjoint({field.name for field in fields(node_type)})


def test_nn_reduce_nodes_share_public_base_fields() -> None:
    """reduce family 共享公开 base 字段，不重复维护 axis/keepdim 结构。"""

    value = MemoryAST("x", SymbolListAST([2, 4]), SymbolListAST([4, 1]), FloatTypeAttrAST(NumericType.Float32), MemorySpaceAttrAST(MemorySpace.GM))

    for node_type in (NnReduceSumAST, NnReduceMinAST, NnReduceMaxAST):
        node = node_type(value, ConstValueAST(1), True)
        assert isinstance(node, NnReduceAST)
        assert node.value is value
        assert isinstance(node.axis, ConstValueAST)
        assert node.keepdim_value() is True
        assert node.result_memory() is not None
