"""DSL AST nodes package facade tests.


功能说明:
- 覆盖 `kernel_gen.dsl.ast.nodes` 包根导出边界。
- 测试结构对应 `spec/dsl/ast/nodes/__init__.md` 与 `kernel_gen/dsl/ast/nodes/__init__.py`。

使用示例:
- pytest -q test/dsl/ast/nodes/test_package.py

关联文件:
- 功能实现: kernel_gen/dsl/ast/nodes/__init__.py
- Spec 文档: spec/dsl/ast/nodes/__init__.md
- 测试文件: test/dsl/ast/nodes/test_package.py
"""

from __future__ import annotations

import importlib


def test_nodes_package_reexports_current_public_nodes() -> None:
    """验证 nodes facade 导出节点类型保持可用，并拒绝旧中间节点。"""

    nodes = importlib.import_module("kernel_gen.dsl.ast.nodes")
    facade = importlib.import_module("kernel_gen.dsl.ast")

    assert facade.FunctionAST is nodes.FunctionAST
    assert facade.AttrAST is nodes.AttrAST
    assert facade.ConstValueAST is nodes.ConstValueAST
    assert facade.MemoryAST is nodes.MemoryAST
    assert facade.SymbolListAST is nodes.SymbolListAST
    assert facade.BoundExprAST is nodes.BoundExprAST
    assert facade.CallAST is nodes.CallAST
    assert facade.ForAST is nodes.ForAST
    assert facade.IfAST is nodes.IfAST
    assert facade.DmaLoadAST is nodes.DmaLoadAST
    assert facade.NnAddAST is nodes.NnAddAST
    assert facade.NnReduceAST is nodes.NnReduceAST
    assert facade.ArchGetThreadNumAST is nodes.ArchGetThreadNumAST
    assert not hasattr(facade, "Assign" + "AST")
    assert not hasattr(facade, "PythonCalleeCall" + "AST")
    assert not hasattr(facade, "LoadAST")
    assert not hasattr(facade, "StoreAST")
