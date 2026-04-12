"""DSL AST visitor tests.

创建者: 小李飞刀
最后一次更改: 小李飞刀

功能说明:
- 覆盖 `AstVisitor` 的基础遍历与错误分发行为。
- 验证不支持的节点会抛出 `AstVisitorError`。

当前覆盖率信息:
- 当前覆盖率: 未统计（本任务验证未启用 coverage 统计）。
- 达标判定: 待后续补充统计结果。

覆盖率命令:
- `pytest -q --cov=kernel_gen.dsl.ast.visitor --cov-branch --cov-report=term-missing test/dsl/ast/test_visitor.py`

使用示例:
- pytest -q test/dsl/ast/test_visitor.py

关联文件:
- 功能实现: kernel_gen/dsl/ast/visitor.py
- Spec 文档: spec/dsl/ast_visitor.md
- 测试文件: test/dsl/ast/test_visitor.py
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from kernel_gen.dsl.ast import BlockAST, SourceLocation
from kernel_gen.dsl.ast.visitor import AstVisitor, AstVisitorError


# AST-S1-V-001
# 创建者: 小李飞刀
# 最后一次更改: 小李飞刀
# 最近一次运行测试时间: 2026-04-13 03:15:00 +0800
# 最近一次运行成功时间: 2026-04-13 03:15:00 +0800
# 功能说明: 空 BlockAST 可被访问器遍历，返回 None。
# 使用示例: pytest -q test/dsl/ast/test_visitor.py -k test_ast_visitor_empty_block_returns_none
# 对应功能实现文件路径: kernel_gen/dsl/ast/visitor.py
# 对应 spec 文件路径: spec/dsl/ast_visitor.md
# 对应测试文件路径: test/dsl/ast/test_visitor.py
def test_ast_visitor_empty_block_returns_none() -> None:
    visitor = AstVisitor()
    block = BlockAST(statements=[], location=SourceLocation(1, 0))
    assert visitor.visit_block(block, ctx=object()) is None


# AST-S1-V-002
# 创建者: 小李飞刀
# 最后一次更改: 小李飞刀
# 最近一次运行测试时间: 2026-04-13 03:15:00 +0800
# 最近一次运行成功时间: 2026-04-13 03:15:00 +0800
# 功能说明: 不支持的 block 节点必须抛出 AstVisitorError。
# 使用示例: pytest -q test/dsl/ast/test_visitor.py -k test_ast_visitor_rejects_unknown_block
# 对应功能实现文件路径: kernel_gen/dsl/ast/visitor.py
# 对应 spec 文件路径: spec/dsl/ast_visitor.md
# 对应测试文件路径: test/dsl/ast/test_visitor.py
def test_ast_visitor_rejects_unknown_block() -> None:
    visitor = AstVisitor()
    with pytest.raises(AstVisitorError, match="Unsupported block node"):
        visitor.visit_block(block_ast=object(), ctx=object())


class _DummyNode:
    def __init__(self) -> None:
        self.location = SourceLocation(2, 1)


class _DummyVisitor(AstVisitor):
    _registry = {_DummyNode: "visit_dummy"}

    def visit_dummy(self, node: _DummyNode, ctx: object) -> str:
        return f"dummy:{ctx}"


# AST-S1-V-003
# 创建者: 金铲铲大作战
# 最后一次更改: 金铲铲大作战
# 最近一次运行测试时间: 2026-04-13 07:45:00 +0800
# 最近一次运行成功时间: 2026-04-13 07:45:00 +0800
# 功能说明: 已注册节点会被 visitor 正确分发。
# 使用示例: pytest -q test/dsl/ast/test_visitor.py -k test_ast_visitor_dispatches_registered_node
# 对应功能实现文件路径: kernel_gen/dsl/ast/visitor.py
# 对应 spec 文件路径: spec/dsl/ast_visitor.md
# 对应测试文件路径: test/dsl/ast/test_visitor.py
def test_ast_visitor_dispatches_registered_node() -> None:
    visitor = _DummyVisitor()
    assert visitor.visit(_DummyNode(), ctx="ctx") == "dummy:ctx"


# AST-S1-V-004
# 创建者: 金铲铲大作战
# 最后一次更改: 金铲铲大作战
# 最近一次运行测试时间: 2026-04-13 07:45:00 +0800
# 最近一次运行成功时间: 2026-04-13 07:45:00 +0800
# 功能说明: 未注册节点必须抛出 AstVisitorError。
# 使用示例: pytest -q test/dsl/ast/test_visitor.py -k test_ast_visitor_rejects_unregistered_node
# 对应功能实现文件路径: kernel_gen/dsl/ast/visitor.py
# 对应 spec 文件路径: spec/dsl/ast_visitor.md
# 对应测试文件路径: test/dsl/ast/test_visitor.py
def test_ast_visitor_rejects_unregistered_node() -> None:
    visitor = AstVisitor()
    with pytest.raises(AstVisitorError, match="Unsupported AST node"):
        visitor.visit(object(), ctx=object())
