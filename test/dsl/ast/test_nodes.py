"""DSL AST node tests.

创建者: OpenAI
最后一次更改: OpenAI

功能说明:
- 覆盖 `kernel_gen.dsl.ast.nodes` 的节点构造。
- 覆盖 `kernel_gen.dsl.ast` facade 的节点 re-export。

当前覆盖率信息:
- 当前覆盖率: 未统计（本任务验证未启用 coverage 统计）。
- 达标判定: 待后续补充统计结果。

覆盖率命令:
- `pytest -q --cov=kernel_gen.dsl.ast.nodes --cov-branch --cov-report=term-missing test/dsl/ast/test_nodes.py`

使用示例:
- `pytest -q test/dsl/ast/test_nodes.py`

关联文件:
- 功能实现: `kernel_gen/dsl/ast/nodes.py`
- Spec 文档: `spec/dsl/ast/nodes.md`
- 测试文件: `test/dsl/ast/test_nodes.py`
"""

from __future__ import annotations

import importlib
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

nodes = importlib.import_module("kernel_gen.dsl.ast.nodes")
facade = importlib.import_module("kernel_gen.dsl.ast")


def test_ast_nodes_construct_basic_types() -> None:
    """构造基础节点并读取字段。"""

    loc = nodes.SourceLocation(line=1, column=2)
    diag = nodes.Diagnostic(message="Unsupported syntax", location=loc)
    tensor = nodes.TensorAST(name="A", memory=object(), location=loc)

    assert loc.line == 1
    assert diag.location is loc
    assert tensor.name == "A"


def test_ast_nodes_construct_expr_block() -> None:
    """构造表达式节点并挂载到 BlockAST。"""

    loc = nodes.SourceLocation(line=3, column=0)
    lhs = nodes.VarAST(name="x", location=loc)
    rhs = nodes.ConstAST(value=1, location=loc)
    expr = nodes.BinaryExprAST(op="add", lhs=lhs, rhs=rhs, location=loc)
    block = nodes.BlockAST(statements=[expr], location=loc)

    assert block.statements[0] is expr


def test_ast_nodes_facade_reexport() -> None:
    """验证 facade 导出节点类型保持可用。"""

    assert facade.FunctionAST is nodes.FunctionAST
    assert facade.ConstAST is nodes.ConstAST
