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
import inspect
import textwrap

import pytest
from xdsl.context import Context

from kernel_gen.core.error import KernelCodeError
from kernel_gen.dsl.ast import (
    BoolValueAST,
    ConstValueAST,
    DslAstVisitor,
    FunctionAST,
    MemoryAST,
    ModuleAST,
    SymbolDimAST,
    SymbolListAST,
    TupleAST,
    parse_function,
)
from kernel_gen.operation import arch as arch_ops
from kernel_gen.operation import dma as dma_ops
from kernel_gen.operation import nn as nn_ops
from kernel_gen.operation.arch import BarrierScope, BarrierVisibility
from kernel_gen.operation.arch import launch_kernel
from kernel_gen.operation.dma import store
from kernel_gen.operation.nn import add
from kernel_gen.symbol_variable.memory import Memory, MemorySpace
from kernel_gen.symbol_variable.symbol_dim import SymbolDim
from kernel_gen.symbol_variable.type import NumericType

GLOBAL_INT = 7
GLOBAL_FLOAT = 1.5
GLOBAL_BOOL = True
GLOBAL_MEMORY = Memory([2, 3], NumericType.Float32)
GLOBAL_SYMBOL = SymbolDim("G")
GLOBAL_DICT = {"space": MemorySpace.SM, "dtype": NumericType.Float32}


def visitor_public_key_kernel(x: Memory, n: int, flag: bool) -> None:
    return None


def callee_identity(x: Memory) -> Memory:
    return x


def callee_return_none(x: Memory) -> None:
    add(x, x)
    return


def callee_noop(x) -> None:
    return


def callee_recursive(x: Memory) -> None:
    callee_recursive(x)


def caller_uses_public_callee(x: Memory) -> None:
    callee_return_none(x)


def caller_uses_recursive_callee(x: Memory) -> None:
    callee_recursive(x)


def caller_uses_callee_keyword(x: Memory) -> None:
    callee_identity(x=x)


def caller_uses_callee_return_value(x: Memory) -> Memory:
    return callee_identity(x)


def caller_uses_callee_arity_mismatch(x: Memory) -> None:
    callee_identity(x, x)


def caller_uses_callee_unsupported_argument(x: Memory) -> None:
    callee_identity(MemorySpace.SM)


def caller_uses_callee_multiple_signatures(x: Memory, n: int) -> None:
    callee_noop(x)
    callee_noop(n)


def caller_reuses_public_callee(x: Memory) -> None:
    callee_return_none(x)
    callee_return_none(x)


def visitor_assignment_kernel(x: Memory, n: int) -> None:
    dims = x.get_shape()
    stride = x.get_stride()
    first, second = dims
    float(n)
    y = add(x, x)
    y = y + x
    n += 1
    n -= 1
    n *= 2
    n /= 2
    n //= 1
    store(x, y, [0, 0], [first, second], stride)
    return None


def visitor_control_kernel(x: Memory, n: int) -> None:
    for i in range(n):
        store(x, x, [0, 0], [1, 1], [1, 1])
    for j in range(0, n):
        store(x, x, [0, 0], [1, 1], [1, 1])
    for k in range(0, n, 1):
        store(x, x, [0, 0], [1, 1], [1, 1])
    if n == 1:
        store(x, x, [0, 0], [1, 1], [1, 1])
    return None


def visitor_return_tuple_kernel(x: Memory, n: int, flag: bool):
    return x, n, flag


def visitor_global_name_kernel(x: Memory) -> None:
    store(x, x, [0, 0], [GLOBAL_INT, 1], [1, 1])
    return None


def visitor_attribute_kernel(x: Memory) -> None:
    dtype = x.dtype
    space = GLOBAL_DICT.space
    other_dtype = GLOBAL_DICT.dtype
    store(x, x, [0, 0], [1, 1], [1, 1])
    return None


def visitor_enum_attribute_kernel(x: Memory) -> None:
    store(x, x, [0, 0], [1, 1], [1, 1], MemorySpace.GM)
    BarrierVisibility.TSM == BarrierVisibility.TLM
    BarrierScope.BLOCK != BarrierScope.THREAD
    NumericType.Float32 == NumericType.Float16
    return None


def visitor_subscript_kernel(x: Memory) -> None:
    item = x[0]
    dims = x.get_shape()
    first = dims[0]
    store(x, x, [0, 0], [first, 1], [1, 1])
    return None


def visitor_docstring_else_and_symbol_ops_kernel(x: Memory, n: int) -> None:
    """exercise docstring skip, else block and public symbol arithmetic."""

    alias = x
    flag = True
    as_float = float(n)
    a = n + 1
    b = n - 1
    c = n * 2
    d = n / 2
    e = n // 2
    if n != 1:
        store(x, x, [0, 0], [a, b], [1, 1])
    else:
        store(x, x, [0, 0], [c, e], [1, 1])
    return None


def visitor_symbol_compare_matrix_kernel(n: int) -> None:
    n == 1
    n != 1
    n < 1
    n <= 1
    n > 1
    n >= 1
    return None


def visitor_memory_compare_matrix_kernel(x: Memory) -> None:
    x == x
    x != x
    x < x
    x <= x
    x > x
    x >= x
    return None


def visitor_for_docstring_kernel(x: Memory, n: int) -> None:
    for i in range(n):
        """empty loop body expression is ignored."""
    return None


def visitor_module_helper_kernel(x: Memory):
    copied = dma_ops.copy(x, MemorySpace.SM)
    product = nn_ops.mul(copied, copied)
    return product


def visitor_arch_module_query_kernel():
    return arch_ops.get_thread_num()


def visitor_arch_module_launch_kernel(x: Memory) -> None:
    arch_ops.launch_kernel[2, 8, 1, 0](callee_identity, x)
    return None


def visitor_launch_kernel_public_name_kernel(x: Memory) -> None:
    launch_kernel[2, 8, 1, 0](callee_identity, x)
    return None


def visitor_global_memory_dtype_kernel(x: Memory) -> None:
    dtype = GLOBAL_MEMORY.dtype
    store(x, x, [0, 0], [1, 1], [1, 1])
    return None


def visitor_get_shape_bad_arity_kernel(x: Memory) -> None:
    dims = x.get_shape(1)
    return None


def visitor_unimported_default_helper_kernel(x: Memory) -> None:
    copy(x)
    return None


def visitor_unknown_call_kernel(x: Memory) -> None:
    missing_call()
    return None


def visitor_non_callable_global_call_kernel(x: Memory) -> None:
    GLOBAL_INT()
    return None


def visitor_unknown_attribute_call_kernel(x: Memory) -> None:
    MissingNamespace.run()
    return None


def visitor_nested_attribute_call_kernel(x: Memory) -> None:
    GLOBAL_DICT.space.run()
    return None


def visitor_external_return_kernel(x: Memory):
    return GLOBAL_MEMORY


def visitor_bad_return_tuple_kernel(x: Memory):
    return x, GLOBAL_MEMORY


def visitor_non_value_return_kernel(x: Memory):
    return GLOBAL_DICT


def visitor_bool_constant_return_kernel():
    return True


def visitor_after_return_kernel(x: Memory):
    return x
    store(x, x, [0, 0], [1, 1], [1, 1])


def visitor_float_arity_kernel(n: int) -> None:
    float(n, n)
    return None


def visitor_unsupported_binary_kernel(n: int) -> None:
    n % 2
    return None


def visitor_unsupported_compare_kernel(n: int) -> None:
    n in [1, 2]
    return None


def visitor_non_value_binary_kernel(x: Memory) -> None:
    GLOBAL_DICT + 1
    return None


def visitor_non_value_compare_kernel(x: Memory) -> None:
    GLOBAL_DICT == 1
    return None


def visitor_chained_compare_kernel(n: int) -> None:
    n < 1 < 2
    return None


def visitor_mixed_symbol_float_binary_kernel(n: int) -> None:
    n + GLOBAL_FLOAT
    return None


def visitor_mixed_symbol_float_compare_kernel(n: int) -> None:
    n < GLOBAL_FLOAT
    return None


def visitor_bad_for_target_kernel(x: Memory) -> None:
    for x[0] in range(1):
        store(x, x, [0, 0], [1, 1], [1, 1])
    return None


def visitor_bad_for_iter_kernel(x: Memory) -> None:
    for i in [1, 2]:
        store(x, x, [0, 0], [1, 1], [1, 1])
    return None


def visitor_bad_for_call_kernel(x: Memory) -> None:
    for i in enumerate([1, 2]):
        store(x, x, [0, 0], [1, 1], [1, 1])
    return None


def visitor_bad_for_arity_kernel(x: Memory) -> None:
    for i in range(0, 1, 1, 1):
        store(x, x, [0, 0], [1, 1], [1, 1])
    return None


def visitor_step_zero_kernel(x: Memory) -> None:
    for i in range(0, 1, 0):
        store(x, x, [0, 0], [1, 1], [1, 1])
    return None


def visitor_unsupported_subscript_kernel(n: int) -> None:
    n[0]
    return None


def visitor_unsupported_unary_kernel(flag: bool) -> None:
    -flag
    return None


def visitor_unsupported_augassign_kernel(n: int) -> None:
    n %= 2
    return None


def _statement(source: str) -> py_ast.stmt:
    module = py_ast.parse(source)
    return module.body[0]


def _visitor(fn=visitor_public_key_kernel) -> DslAstVisitor:
    return DslAstVisitor(fn, (Memory([2, 3], NumericType.Float32), SymbolDim("N"), True))


def _visit_module(fn, *runtime_args) -> ModuleAST:
    """通过公开 DslAstVisitor 访问函数源码并返回 ModuleAST。

    功能说明:
    - 当前测试文件内 helper，替代已删除的包根 `parse(...)` 公开入口。
    - 只使用公开 `DslAstVisitor` 验证 visitor 生成多函数 ModuleAST 的行为。

    使用示例:
    - `_visit_module(caller_uses_public_callee, Memory([2, 3], NumericType.Float32))`
    """

    source = textwrap.dedent(inspect.getsource(fn))
    visitor = DslAstVisitor(fn, tuple(runtime_args))
    visitor.source = source
    module = visitor.visit(py_ast.parse(source))
    assert isinstance(module, ModuleAST)
    return module


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


def test_dsl_ast_visitor_runtime_arg_key_public_variants() -> None:
    """runtime_arg_key 对公开 runtime/AST 输入生成稳定签名 key。"""

    visitor = _visitor()
    func_ast = parse_function(
        visitor_public_key_kernel,
        Memory([2, 3], NumericType.Float32),
        SymbolDim("N"),
        True,
    )

    assert isinstance(func_ast.inputs[0], MemoryAST)
    assert visitor.runtime_arg_key(func_ast.inputs[0])[0] == "MemoryAST"
    assert isinstance(func_ast.inputs[1], SymbolDimAST)
    assert visitor.runtime_arg_key(func_ast.inputs[1]) == ("SymbolDimAST", "n")
    assert isinstance(func_ast.inputs[2], BoolValueAST)
    assert visitor.runtime_arg_key(func_ast.inputs[2]) == ("bool", "True")
    assert visitor.runtime_arg_key(ConstValueAST(3)) == ("int", "3")
    assert visitor.runtime_arg_key(Memory([1], NumericType.Int32))[0] == "Memory"
    assert visitor.runtime_arg_key(SymbolDim("M")) == ("SymbolDim", "M")
    assert visitor.runtime_arg_key(False) == ("bool", "False")
    assert visitor.runtime_arg_key(2) == ("int", "2")
    assert visitor.runtime_arg_key(2.5) == ("float", "2.5")
    assert visitor.runtime_arg_key("x") == ("str", "'x'")
    assert visitor.runtime_arg_key(MemoryAST.from_memory("tmp", Memory([1, 2], NumericType.Float32)).to_mlir_type(Context()))[0] == "NnMemoryType"


def test_dsl_ast_visitor_python_callee_public_paths() -> None:
    """合法 Python callee 语句调用通过公开 visitor 生成 caller/callee 双函数 AST。"""

    module = _visit_module(caller_uses_public_callee, Memory([2, 3], NumericType.Float32))

    assert isinstance(module, ModuleAST)
    assert [function.name for function in module.functions] == [
        "caller_uses_public_callee",
        "callee_return_none",
    ]

    reused_module = _visit_module(caller_reuses_public_callee, Memory([2, 3], NumericType.Float32))
    assert [function.name for function in reused_module.functions] == [
        "caller_reuses_public_callee",
        "callee_return_none",
    ]


@pytest.mark.parametrize(
    ("fn", "message"),
    [
        pytest.param(caller_uses_callee_keyword, "Python callee keyword arguments are unsupported", id="callee-keyword"),
        pytest.param(caller_uses_callee_return_value, "Python callee return value is unsupported", id="callee-return-value"),
        pytest.param(caller_uses_callee_arity_mismatch, "Python callee arity mismatch", id="callee-arity"),
        pytest.param(caller_uses_callee_unsupported_argument, "Unsupported Python callee argument", id="callee-argument"),
        pytest.param(caller_uses_callee_multiple_signatures, "Python callee cannot use multiple signatures", id="callee-signature"),
        pytest.param(caller_uses_recursive_callee, "Recursive Python callee is unsupported", id="callee-recursive"),
    ],
)
def test_dsl_ast_visitor_python_callee_public_errors(fn, message: str) -> None:
    """Python callee 的 keyword 和值上下文按公开错误语义失败。"""

    runtime_args = (Memory([2, 3], NumericType.Float32),)
    if fn is caller_uses_callee_multiple_signatures:
        runtime_args = (Memory([2, 3], NumericType.Float32), SymbolDim("N"))

    with pytest.raises(KernelCodeError, match=message):
        _visit_module(fn, *runtime_args)


def test_dsl_ast_visitor_assign_control_and_public_attributes() -> None:
    """赋值、控制流、全局常量、枚举与 subscript 通过公开 parse_function 解析。"""

    memory = Memory([SymbolDim("M"), 3], NumericType.Float32)

    for fn, args in (
        (visitor_assignment_kernel, (memory, SymbolDim("N"))),
        (visitor_control_kernel, (memory, SymbolDim("N"))),
        (visitor_return_tuple_kernel, (memory, SymbolDim("N"), False)),
        (visitor_global_name_kernel, (memory,)),
        (visitor_attribute_kernel, (memory,)),
        (visitor_enum_attribute_kernel, (memory,)),
        (visitor_subscript_kernel, (Memory([2], NumericType.Float32),)),
        (visitor_docstring_else_and_symbol_ops_kernel, (memory, SymbolDim("N"))),
        (visitor_symbol_compare_matrix_kernel, (SymbolDim("N"),)),
        (visitor_memory_compare_matrix_kernel, (memory,)),
        (visitor_for_docstring_kernel, (memory, SymbolDim("N"))),
        (visitor_module_helper_kernel, (memory,)),
        (visitor_arch_module_query_kernel, ()),
        (visitor_arch_module_launch_kernel, (Memory([2, 3], NumericType.Float32),)),
        (visitor_launch_kernel_public_name_kernel, (Memory([2, 3], NumericType.Float32),)),
        (visitor_global_memory_dtype_kernel, (memory,)),
        (visitor_bool_constant_return_kernel, ()),
    ):
        assert isinstance(parse_function(fn, *args), FunctionAST)


def test_dsl_ast_visitor_public_module_attributes_and_literals() -> None:
    """公开 visitor 入口能解析模块 helper 属性与一元数字字面量。"""

    visitor = _visitor()

    for expression in ("dma_ops.copy", "nn_ops.add", "arch_ops.get_thread_num"):
        attr = visitor.visit_Attribute(py_ast.parse(expression).body[0].value)
        assert attr is not None

    for name in ("flag", "n", "x", "GLOBAL_BOOL", "GLOBAL_SYMBOL", "GLOBAL_INT"):
        value = visitor.visit_Name(py_ast.parse(name).body[0].value)
        assert value is not None

    negative = visitor.visit_UnaryOp(py_ast.parse("-3").body[0].value)
    positive = visitor.visit_UnaryOp(py_ast.parse("+4").body[0].value)

    assert isinstance(negative, ConstValueAST)
    assert negative.raw_value == -3
    assert isinstance(positive, ConstValueAST)
    assert positive.raw_value == 4
    with pytest.raises(KernelCodeError, match="Unsupported attribute"):
        visitor.visit_Attribute(py_ast.parse("GLOBAL_DICT.missing").body[0].value)


def test_dsl_ast_visitor_import_and_call_boundaries() -> None:
    """import / import-from 只开放 spec 定义的 helper 解析边界。"""

    visitor = _visitor()
    visitor.visit_Import(_statement("import kernel_gen.operation.dma"))
    with pytest.raises(KernelCodeError, match="Unknown name"):
        visitor.visit_Call(py_ast.parse("kernel_gen.copy(x)").body[0].value)
    with pytest.raises(KernelCodeError, match="Unsupported call expression"):
        visitor.visit_Call(py_ast.parse("kernel_gen.operation.dma.copy(x)").body[0].value)

    visitor = _visitor()
    visitor.visit_Import(_statement("import kernel_gen.operation.dma"))
    with pytest.raises(KernelCodeError, match="Unknown name"):
        visitor.visit_Attribute(py_ast.parse("kernel_gen.copy").body[0].value)

    visitor = _visitor()
    visitor.visit_ImportFrom(_statement("from kernel_gen.operation import dma"))
    with pytest.raises(KernelCodeError, match="Unsupported call expression"):
        visitor.visit_Call(py_ast.parse("dma.copy(x)").body[0].value)

    visitor = _visitor()
    visitor.visit_ImportFrom(_statement("from kernel_gen.operation import nn as nn_ops"))
    with pytest.raises(KernelCodeError, match="Unsupported attribute"):
        visitor.visit_Attribute(py_ast.parse("nn_ops.add").body[0].value)

    visitor = _visitor()
    visitor.visit_ImportFrom(_statement("from kernel_gen.operation import dma as dma_alias"))
    with pytest.raises(KernelCodeError, match="Unsupported call expression"):
        visitor.visit_Call(py_ast.parse("dma_alias(x)").body[0].value)

    visitor = _visitor()
    visitor.visit_Import(_statement("import kernel_gen.operation.dma as dma_mod"))
    with pytest.raises(KernelCodeError, match="Unknown name"):
        visitor.visit_Call(py_ast.parse("dma_mod(x)").body[0].value)

    visitor = _visitor()
    visitor.visit_ImportFrom(_statement("from kernel_gen.operation import arch as arch_alias"))
    with pytest.raises(KernelCodeError, match="Unsupported call expression"):
        visitor.visit_Call(py_ast.parse("arch_alias.launch_kernel[1](callee_identity, x)").body[0].value)

    visitor = _visitor()
    visitor.visit_Import(_statement("import kernel_gen.operation.arch as arch_mod"))
    with pytest.raises(KernelCodeError, match="Unknown name"):
        visitor.visit_Call(py_ast.parse("arch_mod.launch_kernel[1](callee_identity, x)").body[0].value)

    visitor = _visitor()
    with pytest.raises(KernelCodeError, match="Unsupported call expression"):
        visitor.visit_Call(py_ast.parse("arch_ops.get_thread_num[1]()").body[0].value)


@pytest.mark.parametrize(
    ("fn", "message"),
    [
        pytest.param(visitor_external_return_kernel, "cannot use external value inside function body", id="external-return"),
        pytest.param(visitor_bad_return_tuple_kernel, "return values must be ValueAST", id="bad-return-tuple"),
        pytest.param(visitor_non_value_return_kernel, "return values must be ValueAST", id="non-value-return"),
        pytest.param(visitor_after_return_kernel, "Return statement must be last", id="after-return"),
        pytest.param(visitor_float_arity_kernel, "Unsupported float arity", id="float-arity"),
        pytest.param(visitor_unsupported_binary_kernel, "Unsupported binary operator", id="bad-binary"),
        pytest.param(visitor_unsupported_compare_kernel, "Unsupported compare operator", id="bad-compare"),
        pytest.param(visitor_non_value_binary_kernel, "Unsupported binary op", id="non-value-binary"),
        pytest.param(visitor_non_value_compare_kernel, "Unsupported compare op", id="non-value-compare"),
        pytest.param(visitor_chained_compare_kernel, "Only single compare is supported", id="chained-compare"),
        pytest.param(visitor_mixed_symbol_float_binary_kernel, "Unsupported binary op", id="mixed-binary"),
        pytest.param(visitor_mixed_symbol_float_compare_kernel, "Unsupported compare op", id="mixed-compare"),
        pytest.param(visitor_unsupported_augassign_kernel, "Unsupported augmented assignment", id="bad-augassign"),
        pytest.param(visitor_bad_for_target_kernel, "for target must be a name", id="bad-for-target"),
        pytest.param(visitor_bad_for_iter_kernel, "for iterable must be range or loop", id="bad-for-iter"),
        pytest.param(visitor_bad_for_call_kernel, "for iterable must be range or loop", id="bad-for-call"),
        pytest.param(visitor_bad_for_arity_kernel, "for range arity must be 1, 2 or 3", id="bad-for-arity"),
        pytest.param(visitor_step_zero_kernel, "for range step must not be zero", id="step-zero"),
        pytest.param(visitor_unsupported_subscript_kernel, "Unsupported subscript", id="bad-subscript"),
        pytest.param(visitor_unsupported_unary_kernel, "Unsupported unary operator", id="bad-unary"),
        pytest.param(visitor_get_shape_bad_arity_kernel, "Unsupported get_shape arity", id="bad-get-shape"),
        pytest.param(visitor_unimported_default_helper_kernel, "Unsupported call expression", id="unimported-helper"),
        pytest.param(visitor_unknown_call_kernel, "Unknown name", id="unknown-call"),
        pytest.param(visitor_non_callable_global_call_kernel, "Unsupported call: GLOBAL_INT", id="non-callable-global"),
        pytest.param(visitor_unknown_attribute_call_kernel, "Unsupported call expression", id="unknown-attribute-call"),
        pytest.param(visitor_nested_attribute_call_kernel, "Unsupported call expression", id="nested-attribute-call"),
    ],
)
def test_dsl_ast_visitor_public_error_boundaries(fn, message: str) -> None:
    """不支持的公开语法边界必须稳定抛出 KernelCodeError。"""

    runtime_args = (Memory([2, 3], NumericType.Float32),)
    if fn in {
        visitor_float_arity_kernel,
        visitor_unsupported_binary_kernel,
        visitor_unsupported_compare_kernel,
        visitor_mixed_symbol_float_binary_kernel,
        visitor_mixed_symbol_float_compare_kernel,
        visitor_unsupported_subscript_kernel,
        visitor_chained_compare_kernel,
        visitor_unsupported_augassign_kernel,
    }:
        runtime_args = (SymbolDim("N"),)
    if fn is visitor_unsupported_unary_kernel:
        runtime_args = (False,)

    with pytest.raises(KernelCodeError, match=message):
        parse_function(fn, *runtime_args)
