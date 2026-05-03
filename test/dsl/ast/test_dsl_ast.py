"""DSL AST visitor tests.


功能说明:
- 覆盖 `DslAstVisitor` 的标准 `visit_*` 入口与稳定错误文本。
- 测试结构对应 `spec/dsl/ast/dsl_ast.md` 与 `kernel_gen/dsl/ast/dsl_ast.py`。

使用示例:
- pytest -q test/dsl/ast/test_dsl_ast.py

关联文件:
- 功能实现: kernel_gen/dsl/ast/dsl_ast.py
- Spec 文档: spec/dsl/ast/dsl_ast.md
- 测试文件: test/dsl/ast/test_dsl_ast.py
"""

from __future__ import annotations

import ast as py_ast

import pytest

from kernel_gen.core.error import KernelCodeError
from kernel_gen.dsl.ast import ConstValueAST, DslAstVisitor, SymbolListAST, TupleAST
from kernel_gen.symbol_variable.memory import Memory
from kernel_gen.symbol_variable.type import NumericType


def test_dsl_ast_visitor_exposes_standard_node_visitor_methods() -> None:
    """call 参数相关解析入口必须是标准 NodeVisitor 方法。"""

    def kernel():
        return None

    call = py_ast.parse("f([1, 2], key=(3, 4))").body[0].value
    assert isinstance(call, py_ast.Call)
    visitor = DslAstVisitor(kernel)

    values = visitor.visit(call.args[0])
    keyword_pair = visitor.visit(call.keywords[0])

    assert callable(visitor.visit_List)
    assert callable(visitor.visit_Tuple)
    assert callable(visitor.visit_keyword)
    assert not hasattr(visitor, "visit_CallArgs")
    assert not hasattr(visitor, "visit_CallKeywords")
    assert isinstance(values, SymbolListAST)
    assert len(values.values) == 2
    assert isinstance(keyword_pair, TupleAST)
    assert len(keyword_pair.items) == 2
    keyword_name, keyword_value = keyword_pair.items
    assert isinstance(keyword_name, ConstValueAST)
    assert keyword_name.raw_value == "key"
    assert isinstance(keyword_value, TupleAST)


def test_dsl_ast_unknown_attribute_base_reports_unknown_name() -> None:
    """未知属性基名必须报 Unknown name，而不是 Unsupported attribute。"""

    def kernel(x):
        return MissingEnum.TSM

    visitor = DslAstVisitor(kernel, (Memory([1], NumericType.Float32),))
    module = py_ast.parse("def kernel(x):\n    return MissingEnum.TSM\n")

    with pytest.raises(KernelCodeError, match="Unknown name"):
        visitor.visit(module)
