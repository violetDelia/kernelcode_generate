"""DSL AST control-flow node tests.


功能说明:
- 覆盖 `kernel_gen.dsl.ast.nodes.control_flow` 的公开节点归属与构造归一。
- 测试结构对应 `spec/dsl/ast/nodes/control_flow.md` 与 `kernel_gen/dsl/ast/nodes/control_flow.py`。

使用示例:
- pytest -q test/dsl/ast/nodes/test_control_flow.py

关联文件:
- 功能实现: kernel_gen/dsl/ast/nodes/control_flow.py
- Spec 文档: spec/dsl/ast/nodes/control_flow.md
- 测试文件: test/dsl/ast/nodes/test_control_flow.py
"""

from __future__ import annotations

import importlib

from kernel_gen.dsl.ast.nodes.basic import BlockAST, BoolValueAST
from kernel_gen.dsl.ast.nodes.control_flow import ForAST, IfAST
from kernel_gen.dsl.ast.nodes.symbol import ConstValueAST, SymbolDimAST


def test_control_flow_nodes_live_in_control_flow_module() -> None:
    """控制流节点只由 control_flow.py 承载，同时保持包根导出。"""

    control_flow_module = importlib.import_module("kernel_gen.dsl.ast.nodes.control_flow")
    basic_module = importlib.import_module("kernel_gen.dsl.ast.nodes.basic")
    symbol_module = importlib.import_module("kernel_gen.dsl.ast.nodes.symbol")
    nodes_module = importlib.import_module("kernel_gen.dsl.ast.nodes")

    assert control_flow_module.ForAST is ForAST
    assert control_flow_module.IfAST is IfAST
    assert nodes_module.ForAST is ForAST
    assert nodes_module.IfAST is IfAST
    assert not hasattr(basic_module, "IfAST")
    assert not hasattr(symbol_module, "ForAST")


def test_for_ast_normalizes_bounds_and_default_step() -> None:
    """ForAST 把裸循环变量和整数边界归一为公开 AST 节点。"""

    body = BlockAST([])
    loop = ForAST("i", 0, 8, body)

    assert isinstance(loop.var, SymbolDimAST)
    assert loop.var.name == "i"
    assert isinstance(loop.start, ConstValueAST)
    assert loop.start.raw_value == 0
    assert isinstance(loop.end, ConstValueAST)
    assert loop.end.raw_value == 8
    assert loop.step is None
    assert loop.body is body


def test_if_ast_normalizes_python_bool_condition() -> None:
    """IfAST 把裸 Python bool 条件归一为 BoolValueAST。"""

    true_body = BlockAST([])
    false_body = BlockAST([])
    branch = IfAST(True, true_body, false_body)

    assert isinstance(branch.condition, BoolValueAST)
    assert branch.condition.raw_value is True
    assert branch.true_body is true_body
    assert branch.false_body is false_body
