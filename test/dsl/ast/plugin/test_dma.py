"""DSL AST DMA plugin tests.


功能说明:
- 覆盖 `kernel_gen.dsl.ast.plugin.dma` 注册后的 DMA helper 解析行为。
- 测试结构对应 `spec/dsl/ast/plugin/dma.md` 与 `kernel_gen/dsl/ast/plugin/dma.py`。

使用示例:
- pytest -q test/dsl/ast/plugin/test_dma.py

关联文件:
- 功能实现: kernel_gen/dsl/ast/plugin/dma.py
- Spec 文档: spec/dsl/ast/plugin/dma.md
- 测试文件: test/dsl/ast/plugin/test_dma.py
"""

from __future__ import annotations

from kernel_gen.dsl.ast import (
    BoundExprAST,
    DmaDesliceAST,
    DmaFillAST,
    DmaLoadAST,
    DmaSliceAST,
    DmaStoreAST,
    SymbolListAST,
    parse_function,
)
from kernel_gen.operation.dma import deslice, fill, load, slice, store
from kernel_gen.symbol_variable.memory import Memory
from kernel_gen.symbol_variable.type import NumericType


def test_dma_fill_parses_to_specific_node() -> None:
    """`fill(...)` 解析为 `DmaFillAST`，不再通过中间 StoreAST 表达。"""

    memory = Memory([4], NumericType.Float32)

    def kernel(x):
        fill(x, "-inf")

    func_ast = parse_function(kernel, memory)

    fill_nodes = [node for node in func_ast.body.statements if isinstance(node, DmaFillAST)]
    assert len(fill_nodes) == 1
    assert fill_nodes[0].target == func_ast.inputs[0]


def test_dma_load_slice_parse_to_specific_nodes() -> None:
    """source-first `load` / `slice` helper 解析为具体读取节点。"""

    memory = Memory([8], NumericType.Float32)

    def kernel(x):
        a = load(x, [0], [4], [1])
        b = slice(x, [4], [4], [1])
        return b

    func_ast = parse_function(kernel, memory)
    bound_values = [node.value for node in func_ast.body.statements if isinstance(node, BoundExprAST)]

    assert any(isinstance(node, DmaLoadAST) for node in bound_values)
    assert any(isinstance(node, DmaSliceAST) for node in bound_values)
    assert all(isinstance(node.size, SymbolListAST) for node in bound_values if isinstance(node, (DmaLoadAST, DmaSliceAST)))


def test_dma_store_deslice_parse_to_specific_nodes() -> None:
    """target-first `store` / `deslice` helper 解析为具体写回节点。"""

    target = Memory([8], NumericType.Float32)
    source = Memory([4], NumericType.Float32)

    def kernel(dst, src):
        store(dst, src, [0], [4], [1])
        deslice(dst, src, [4], [4], [1])

    func_ast = parse_function(kernel, target, source)

    assert any(isinstance(node, DmaStoreAST) for node in func_ast.body.statements)
    assert any(isinstance(node, DmaDesliceAST) for node in func_ast.body.statements)
    assert all(isinstance(node.size, SymbolListAST) for node in func_ast.body.statements if isinstance(node, (DmaStoreAST, DmaDesliceAST)))
