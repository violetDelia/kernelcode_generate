"""memory dialect tests.


功能说明:
- 覆盖 `memory.get_data` 的公开构造、parse/print、verifier 与错误边界。

使用示例:
- pytest -q test/dialect/test_memory.py

关联文件:
- 功能实现: kernel_gen/dialect/memory.py
- Spec 文档: spec/dialect/memory.md
- 测试文件: test/dialect/test_memory.py
"""

from __future__ import annotations

from io import StringIO

import pytest
from xdsl.context import Context
from xdsl.dialects.builtin import ArrayAttr, Builtin, f32, i32
from xdsl.dialects.test import Test, TestOp
from xdsl.ir import Attribute, Operation
from xdsl.parser import Parser
from xdsl.printer import Printer
from xdsl.utils.exceptions import VerifyException

from kernel_gen.dialect.memory import Memory, MemoryGetDataOp
from kernel_gen.dialect.nn import Nn, NnMemorySpaceAttr, NnMemoryType
from kernel_gen.dialect.symbol import Symbol, SymbolExprAttr, SymbolPtrType


def _build_context() -> Context:
    """构造 memory dialect 解析上下文。

    功能说明:
    - 加载 `builtin/test/nn/symbol/memory` dialect，覆盖公开文本 round-trip。

    使用示例:
    - ctx = _build_context()
    """

    ctx = Context()
    ctx.load_dialect(Builtin)
    ctx.load_dialect(Test)
    ctx.load_dialect(Nn)
    ctx.load_dialect(Symbol)
    ctx.load_dialect(Memory)
    return ctx


def _print_op(op: Operation) -> str:
    """打印 operation 文本。

    功能说明:
    - 为 parse/print round-trip 测试提供统一输出入口。

    使用示例:
    - text = _print_op(op)
    """

    stream = StringIO()
    Printer(stream=stream).print_op(op)
    return stream.getvalue()


def _expr(value: int | str) -> SymbolExprAttr:
    """构造公开 symbol expr attr。

    功能说明:
    - 统一 memory shape/stride 的结构化维度表示。

    使用示例:
    - dim = _expr("N")
    """

    return SymbolExprAttr.from_expr(str(value))


def _memory_type(
    *,
    element_type: Attribute = f32,
    template_name: str | None = None,
) -> NnMemoryType:
    """构造一维 global memory type。

    功能说明:
    - 覆盖 `memory.get_data` 的 dtype/template 推导与 verifier。

    使用示例:
    - mem_type = _memory_type(template_name="T")
    """

    return NnMemoryType(
        ArrayAttr([_expr("N")]),
        ArrayAttr([_expr(1)]),
        element_type,
        NnMemorySpaceAttr.from_name("global"),
        template_name=template_name,
    )


def _memory_value(memory_type: NnMemoryType):
    """构造带 nn.memory type 的公开 test SSA value。

    功能说明:
    - 通过 `test.op` 生成 `memory.get_data` source，不直连实现私有 helper。

    使用示例:
    - value = _memory_value(_memory_type())
    """

    return TestOp(result_types=[memory_type]).results[0]


def test_memory_get_data_infers_symbol_ptr_type() -> None:
    """`MemoryGetDataOp(...)` 从 memory source 推导 ptr dtype/template。"""

    source = _memory_value(_memory_type(template_name="T_bias"))

    op = MemoryGetDataOp(source)

    op.verify()
    assert op.result.type == SymbolPtrType(f32, "T_bias")


def test_memory_get_data_round_trip_with_template() -> None:
    """`memory.get_data` 文本语法保留 source memory 与 ptr template。"""

    ctx = _build_context()
    module = Parser(
        ctx,
        """
builtin.module {
  %mem = "test.op"() : () -> !nn.memory<[#symbol.expr<N>], [#symbol.expr<1>], f32, #nn.space<global>, template = T_bias>
  %ptr = memory.get_data %mem : !nn.memory<[#symbol.expr<N>], [#symbol.expr<1>], f32, #nn.space<global>, template = T_bias> -> !symbol.ptr<f32, template = T_bias>
}
""",
    ).parse_module()

    module.verify()
    printed = _print_op(module)
    assert "memory.get_data %mem" in printed
    assert "-> !symbol.ptr<f32, template = T_bias>" in printed


def test_memory_get_data_rejects_non_memory_source() -> None:
    """`memory.get_data` 拒绝非 `!nn.memory` source。"""

    source = TestOp(result_types=[i32]).results[0]

    with pytest.raises(VerifyException, match="memory.get_data source must be !nn.memory"):
        MemoryGetDataOp(source, SymbolPtrType(i32)).verify()


def test_memory_get_data_rejects_non_ptr_result() -> None:
    """`memory.get_data` result 必须是 `!symbol.ptr`。"""

    source = _memory_value(_memory_type())

    with pytest.raises(VerifyException, match="memory.get_data result type must be !symbol.ptr"):
        MemoryGetDataOp(source, i32).verify()


def test_memory_get_data_rejects_dtype_or_template_mismatch() -> None:
    """`memory.get_data` result ptr 必须匹配 source element_type/template。"""

    source = _memory_value(_memory_type(template_name="T_bias"))

    with pytest.raises(VerifyException, match="memory.get_data ptr dtype must match memory element_type"):
        MemoryGetDataOp(source, SymbolPtrType(i32, "T_bias")).verify()
    with pytest.raises(VerifyException, match="memory.get_data ptr template_name must match memory template_name"):
        MemoryGetDataOp(source, SymbolPtrType(f32, "Other")).verify()
