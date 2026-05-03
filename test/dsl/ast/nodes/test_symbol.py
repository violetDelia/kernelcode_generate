"""DSL AST symbol node tests.


功能说明:
- 覆盖 `kernel_gen.dsl.ast.nodes.symbol` 的 symbol dialect AST 节点边界。
- 测试结构对应 `spec/dsl/ast/nodes/symbol.md` 与 `kernel_gen/dsl/ast/nodes/symbol.py`。

使用示例:
- pytest -q test/dsl/ast/nodes/test_symbol.py

关联文件:
- 功能实现: kernel_gen/dsl/ast/nodes/symbol.py
- Spec 文档: spec/dsl/ast/nodes/symbol.md
- 测试文件: test/dsl/ast/nodes/test_symbol.py
"""

from __future__ import annotations

import importlib

from kernel_gen.dsl.ast.nodes.symbol import ConstValueAST, SymbolAddAST, SymbolDimAST, SymbolListAST, SymbolMinAST
from kernel_gen.symbol_variable.symbol_dim import SymbolDim


def test_symbol_nodes_live_in_symbol_module() -> None:
    """symbol.py 承载 symbol dialect AST 节点公开定义。"""

    symbol_module = importlib.import_module("kernel_gen.dsl.ast.nodes.symbol")
    basic_module = importlib.import_module("kernel_gen.dsl.ast.nodes.basic")

    assert symbol_module.SymbolAddAST is SymbolAddAST
    assert symbol_module.SymbolMinAST is SymbolMinAST
    assert symbol_module.SymbolDimAST is SymbolDimAST
    assert not hasattr(basic_module, "SymbolAddAST")
    assert not hasattr(basic_module, "SymbolDimAST")
    assert not hasattr(symbol_module, "ForAST")


def test_symbol_binary_and_list_expose_result_symbol_semantics() -> None:
    """Symbol 节点通过 result_symbol/result_symbols 暴露解析期符号语义。"""

    runtime_symbol = SymbolDim("N")
    lhs = SymbolDimAST("n", runtime_symbol=runtime_symbol)
    rhs = ConstValueAST(2)
    expr = SymbolAddAST(lhs, rhs)
    tail = SymbolMinAST(lhs, rhs)
    shape = SymbolListAST([lhs, rhs, expr, tail])

    assert lhs.result_symbol() == runtime_symbol
    assert rhs.result_symbol() == 2
    assert expr.result_symbol() == runtime_symbol + 2
    assert str(tail.result_symbol().get_value()) == "min(2, N)"
    assert shape.result_symbols() == [runtime_symbol, 2, runtime_symbol + 2, tail.result_symbol()]
