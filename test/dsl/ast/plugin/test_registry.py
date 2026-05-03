"""DSL AST builtin registry tests.


功能说明:
- 覆盖 `kernel_gen.dsl.ast.plugin.registry` 的 builtin 注册唯一性与 builder 返回值校验。
- 测试结构对应 `spec/dsl/ast/plugin/registry.md` 与 `kernel_gen/dsl/ast/plugin/registry.py`。

使用示例:
- pytest -q test/dsl/ast/plugin/test_registry.py

关联文件:
- 功能实现: kernel_gen/dsl/ast/plugin/registry.py
- Spec 文档: spec/dsl/ast/plugin/registry.md
- 测试文件: test/dsl/ast/plugin/test_registry.py
"""

from __future__ import annotations

import ast as py_ast

import pytest

from kernel_gen.core.error import KernelCodeError
from kernel_gen.dsl.ast import SourceLocation
from kernel_gen.dsl.ast.plugin import BuiltinCall, dsl_builtin, lookup_builtin


def test_dsl_builtin_operation_binds_to_one_ast_node() -> None:
    """同一个 operation 只能绑定一个唯一 AST 类型。"""

    def unique_op() -> None:
        return None

    class FirstAST:
        pass

    class SecondAST:
        pass

    @dsl_builtin(unique_op, FirstAST)
    def build_first(node: BuiltinCall) -> FirstAST:
        del node
        return FirstAST()

    with pytest.raises(KernelCodeError, match="already registered"):

        @dsl_builtin(unique_op, SecondAST)
        def build_second(node: BuiltinCall) -> SecondAST:
            del node
            return SecondAST()


def test_dsl_builtin_rejects_manual_name_argument() -> None:
    """`dsl_builtin(...)` 不再提供手写 `name` 参数。"""

    def named_op() -> None:
        return None

    class NamedAST:
        pass

    with pytest.raises(TypeError, match="unexpected keyword argument 'name'"):
        dsl_builtin(named_op, NamedAST, name="manual")


def test_dsl_builtin_ast_node_cannot_bind_multiple_operations() -> None:
    """同一个 AST 类型不能被多个 operation 复用。"""

    def first_op() -> None:
        return None

    def second_op() -> None:
        return None

    class SharedAST:
        pass

    @dsl_builtin(first_op, SharedAST)
    def build_first(node: BuiltinCall) -> SharedAST:
        del node
        return SharedAST()

    with pytest.raises(KernelCodeError, match="already bound"):

        @dsl_builtin(second_op, SharedAST)
        def build_second(node: BuiltinCall) -> SharedAST:
            del node
            return SharedAST()


def test_dsl_builtin_builder_must_return_declared_ast_node() -> None:
    """builder 返回值必须是 `@dsl_builtin(..., AST)` 声明的精确 AST 类型。"""

    def checked_op() -> None:
        return None

    class ExpectedAST:
        pass

    class OtherAST:
        pass

    @dsl_builtin(checked_op, ExpectedAST)
    def build_wrong(node: BuiltinCall) -> OtherAST:
        del node
        return OtherAST()

    entry = lookup_builtin(checked_op)
    assert entry is not None
    call = py_ast.parse("checked_op()").body[0].value
    assert isinstance(call, py_ast.Call)
    builtin_call = BuiltinCall(
        source=call,
        dsl_name="checked_op",
        ast_node=ExpectedAST,
        args=[],
        kwargs={},
        location=SourceLocation(1, 0),
    )

    with pytest.raises(KernelCodeError, match="builder returned OtherAST, expected ExpectedAST"):
        entry.builder(builtin_call)


def test_dsl_builtin_builder_rejects_declared_ast_subclass() -> None:
    """builder 返回声明 AST 的子类也不满足唯一 AST 合同。"""

    def subclass_op() -> None:
        return None

    class ExpectedAST:
        pass

    class SubExpectedAST(ExpectedAST):
        pass

    @dsl_builtin(subclass_op, ExpectedAST)
    def build_subclass(node: BuiltinCall) -> SubExpectedAST:
        del node
        return SubExpectedAST()

    entry = lookup_builtin(subclass_op)
    assert entry is not None
    call = py_ast.parse("subclass_op()").body[0].value
    assert isinstance(call, py_ast.Call)
    builtin_call = BuiltinCall(
        source=call,
        dsl_name="subclass_op",
        ast_node=ExpectedAST,
        args=[],
        kwargs={},
        location=SourceLocation(1, 0),
    )

    with pytest.raises(KernelCodeError, match="builder returned SubExpectedAST, expected ExpectedAST"):
        entry.builder(builtin_call)
