"""ast_nodes tests.

创建者: 朽木露琪亚
最后一次更改: 朽木露琪亚

功能说明:
- 覆盖 kernel_gen/dsl/ast_nodes.py 的节点构造与 facade re-export。

当前覆盖率信息:
- 当前覆盖率: 未统计（本任务验证未启用 coverage 统计）。
- 达标判定: 待后续补充统计结果。

覆盖率命令:
- `pytest -q --cov=kernel_gen.dsl.ast_nodes --cov-branch --cov-report=term-missing test/dsl/test_ast_nodes.py`

使用示例:
- pytest -q test/dsl/test_ast_nodes.py

关联文件:
- 功能实现: kernel_gen/dsl/ast_nodes.py
- Spec 文档: spec/dsl/ast_nodes.md
- 测试文件: test/dsl/test_ast_nodes.py
"""

from __future__ import annotations

import sys
from pathlib import Path

import importlib

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

nodes = importlib.import_module("kernel_gen.dsl.ast_nodes")
facade = importlib.import_module("kernel_gen.dsl.ast")


# AST-N-001
# 创建者: 朽木露琪亚
# 最后一次更改: 朽木露琪亚
# 最近一次运行测试时间: 2026-04-12 00:30:00 +0800
# 最近一次运行成功时间: 2026-04-12 00:30:00 +0800
# 功能说明: 构造基础节点并读取字段。
# 使用示例: pytest -q test/dsl/test_ast_nodes.py -k test_ast_nodes_construct_basic_types
# 对应功能实现文件路径: kernel_gen/dsl/ast_nodes.py
# 对应 spec 文件路径: spec/dsl/ast_nodes.md
# 对应测试文件路径: test/dsl/test_ast_nodes.py
def test_ast_nodes_construct_basic_types() -> None:
    loc = nodes.SourceLocation(line=1, column=2)
    diag = nodes.Diagnostic(message="Unsupported syntax", location=loc)
    tensor = nodes.TensorAST(name="A", memory=object(), location=loc)
    assert loc.line == 1
    assert diag.location is loc
    assert tensor.name == "A"


# AST-N-002
# 创建者: 朽木露琪亚
# 最后一次更改: 朽木露琪亚
# 最近一次运行测试时间: 2026-04-12 00:30:00 +0800
# 最近一次运行成功时间: 2026-04-12 00:30:00 +0800
# 功能说明: 构造表达式节点并挂载到 BlockAST。
# 使用示例: pytest -q test/dsl/test_ast_nodes.py -k test_ast_nodes_construct_expr_block
# 对应功能实现文件路径: kernel_gen/dsl/ast_nodes.py
# 对应 spec 文件路径: spec/dsl/ast_nodes.md
# 对应测试文件路径: test/dsl/test_ast_nodes.py
def test_ast_nodes_construct_expr_block() -> None:
    loc = nodes.SourceLocation(line=3, column=0)
    lhs = nodes.VarAST(name="x", location=loc)
    rhs = nodes.ConstAST(value=1, location=loc)
    expr = nodes.BinaryExprAST(op="add", lhs=lhs, rhs=rhs, location=loc)
    block = nodes.BlockAST(statements=[expr], location=loc)
    assert block.statements[0] is expr


# AST-N-003
# 创建者: 朽木露琪亚
# 最后一次更改: 朽木露琪亚
# 最近一次运行测试时间: 2026-04-12 00:30:00 +0800
# 最近一次运行成功时间: 2026-04-12 00:30:00 +0800
# 功能说明: 验证 facade 导出节点类型保持可用。
# 使用示例: pytest -q test/dsl/test_ast_nodes.py -k test_ast_nodes_facade_reexport
# 对应功能实现文件路径: kernel_gen/dsl/ast.py
# 对应 spec 文件路径: spec/dsl/ast_nodes.md
# 对应测试文件路径: test/dsl/test_ast_nodes.py
def test_ast_nodes_facade_reexport() -> None:
    assert facade.FunctionAST is nodes.FunctionAST
    assert facade.ConstAST is nodes.ConstAST
