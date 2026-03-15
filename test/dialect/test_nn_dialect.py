"""nn dialect tests.

创建者: 小李飞刀
最后一次更改: 小李飞刀

功能说明:
- 覆盖 nn dialect 的 attr/type/op verifier、parse/print 与 round-trip 行为。

使用示例:
- pytest -q test/dialect/test_nn_dialect.py

关联文件:
- 功能实现: python/dialect/nn.py
- Spec 文档: spec/dialect/nn.md
- 测试文件: test/dialect/test_nn_dialect.py
"""

from __future__ import annotations

from io import StringIO
import sys
from pathlib import Path

import pytest
from xdsl.context import Context
from xdsl.dialects.builtin import ArrayAttr, Builtin, IntAttr, IntegerType, ModuleOp, StringAttr, i32
from xdsl.dialects.test import Test, TestOp as _TestOp
from xdsl.ir import Attribute, Operation
from xdsl.parser import Parser
from xdsl.printer import Printer
from xdsl.utils.exceptions import ParseError, VerifyException

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from python.dialect import Nn, NnAddOp, NnEqOp, NnMemorySpaceAttr, NnMemoryType


def _build_context() -> Context:
    """构造加载 builtin/test/nn 的解析上下文。

    创建者: 小李飞刀
    最后一次更改: 小李飞刀

    功能说明:
    - 为 parser/printer/verify 测试提供统一 context。

    使用示例:
    - _build_context()

    关联文件:
    - spec: spec/dialect/nn.md
    - test: test/dialect/test_nn_dialect.py
    - 功能实现: python/dialect/nn.py
    """

    ctx = Context()
    ctx.load_dialect(Builtin)
    ctx.load_dialect(Test)
    ctx.load_dialect(Nn)
    return ctx


def _print_ir(value: object) -> str:
    """打印 attribute 或 operation/module 为文本。"""

    stream = StringIO()
    printer = Printer(stream=stream)
    if isinstance(value, Attribute):
        printer.print_attribute(value)
    elif isinstance(value, Operation):
        printer.print_op(value)
    else:
        printer.print(value)
    return stream.getvalue()


def _make_space(name: str) -> NnMemorySpaceAttr:
    """构造 space attribute。"""

    return NnMemorySpaceAttr(StringAttr(name))


def _make_memory_type(space: str = "global", element_type: IntegerType = i32) -> NnMemoryType:
    """构造合法的 nn memory type。"""

    return NnMemoryType(
        ArrayAttr([StringAttr("M"), StringAttr("?"), IntAttr(4)]),
        ArrayAttr([IntAttr(4), IntAttr(1), StringAttr("?")]),
        element_type,
        _make_space(space),
    )


# TY-001
# 创建者: 小李飞刀
# 最后一次更改: 小李飞刀
# 最近一次运行测试时间: 2026-03-16 02:18:40 +0800
# 最近一次运行成功时间: 2026-03-16 02:18:40 +0800
# 功能说明: 验证 memory type parse/print 可稳定 round-trip。
# 使用示例: pytest -q test/dialect/test_nn_dialect.py -k test_memory_type_round_trip
# 对应功能实现文件路径: python/dialect/nn.py
# 对应 spec 文件路径: spec/dialect/nn.md
# 对应测试文件路径: test/dialect/test_nn_dialect.py
def test_memory_type_round_trip() -> None:
    ctx = _build_context()
    text = "!nn.memory<[M, ?, 4], [4, 1, ?], i32, #nn.space<global>>"
    memory_type = Parser(ctx, text).parse_attribute()
    assert isinstance(memory_type, NnMemoryType)
    memory_type.verify()
    assert _print_ir(memory_type) == text


# TY-002
# 创建者: 小李飞刀
# 最后一次更改: 小李飞刀
# 最近一次运行测试时间: 2026-03-16 02:18:40 +0800
# 最近一次运行成功时间: 2026-03-16 02:18:40 +0800
# 功能说明: 验证三种合法 space text form 均可 parse/print round-trip。
# 使用示例: pytest -q test/dialect/test_nn_dialect.py -k test_space_attr_round_trip
# 对应功能实现文件路径: python/dialect/nn.py
# 对应 spec 文件路径: spec/dialect/nn.md
# 对应测试文件路径: test/dialect/test_nn_dialect.py
def test_space_attr_round_trip() -> None:
    ctx = _build_context()
    for text in ["#nn.space<global>", "#nn.space<shared>", "#nn.space<local>"]:
        space_attr = Parser(ctx, text).parse_attribute()
        assert isinstance(space_attr, NnMemorySpaceAttr)
        space_attr.verify()
        assert _print_ir(space_attr) == text


# TY-002A
# 创建者: 小李飞刀
# 最后一次更改: 小李飞刀
# 最近一次运行测试时间: 2026-03-16 02:18:40 +0800
# 最近一次运行成功时间: 2026-03-16 02:18:40 +0800
# 功能说明: 验证非法 space attribute 会触发 verifier。
# 使用示例: pytest -q test/dialect/test_nn_dialect.py -k test_invalid_space_attr_rejected
# 对应功能实现文件路径: python/dialect/nn.py
# 对应 spec 文件路径: spec/dialect/nn.md
# 对应测试文件路径: test/dialect/test_nn_dialect.py
def test_invalid_space_attr_rejected() -> None:
    with pytest.raises(VerifyException, match="global/shared/local"):
        _make_space("register").verify()


# TY-003
# 创建者: 小李飞刀
# 最后一次更改: 小李飞刀
# 最近一次运行测试时间: 2026-03-16 02:18:40 +0800
# 最近一次运行成功时间: 2026-03-16 02:18:40 +0800
# 功能说明: 验证 memory type 的 shape/stride rank mismatch 会触发 verifier。
# 使用示例: pytest -q test/dialect/test_nn_dialect.py -k test_memory_type_rank_mismatch_rejected
# 对应功能实现文件路径: python/dialect/nn.py
# 对应 spec 文件路径: spec/dialect/nn.md
# 对应测试文件路径: test/dialect/test_nn_dialect.py
def test_memory_type_rank_mismatch_rejected() -> None:
    with pytest.raises(VerifyException, match="rank must match"):
        NnMemoryType(
            ArrayAttr([IntAttr(4), IntAttr(8)]),
            ArrayAttr([IntAttr(1)]),
            i32,
            _make_space("global"),
        )


# TY-004
# 创建者: 小李飞刀
# 最后一次更改: 小李飞刀
# 最近一次运行测试时间: 2026-03-16 02:18:40 +0800
# 最近一次运行成功时间: 2026-03-16 02:18:40 +0800
# 功能说明: 验证 nn.add 在 operand/result/space 一致时可通过 verifier。
# 使用示例: pytest -q test/dialect/test_nn_dialect.py -k test_add_op_verify_success
# 对应功能实现文件路径: python/dialect/nn.py
# 对应 spec 文件路径: spec/dialect/nn.md
# 对应测试文件路径: test/dialect/test_nn_dialect.py
def test_add_op_verify_success() -> None:
    memory_type = _make_memory_type()
    lhs = _TestOp(result_types=[memory_type]).results[0]
    rhs = _TestOp(result_types=[memory_type]).results[0]
    op = NnAddOp(lhs, rhs, memory_type, _make_space("global"))
    op.verify()


# TY-005
# 创建者: 小李飞刀
# 最后一次更改: 小李飞刀
# 最近一次运行测试时间: 2026-03-16 02:18:40 +0800
# 最近一次运行成功时间: 2026-03-16 02:18:40 +0800
# 功能说明: 验证 nn.add operand space mismatch 会触发 verifier。
# 使用示例: pytest -q test/dialect/test_nn_dialect.py -k test_add_op_rejects_operand_space_mismatch
# 对应功能实现文件路径: python/dialect/nn.py
# 对应 spec 文件路径: spec/dialect/nn.md
# 对应测试文件路径: test/dialect/test_nn_dialect.py
def test_add_op_rejects_operand_space_mismatch() -> None:
    lhs_type = _make_memory_type("global")
    rhs_type = _make_memory_type("shared")
    lhs = _TestOp(result_types=[lhs_type]).results[0]
    rhs = _TestOp(result_types=[rhs_type]).results[0]
    op = NnAddOp(lhs, rhs, lhs_type, _make_space("global"))
    with pytest.raises(VerifyException, match="same space"):
        op.verify()


# TY-006
# 创建者: 小李飞刀
# 最后一次更改: 小李飞刀
# 最近一次运行测试时间: 2026-03-16 02:18:40 +0800
# 最近一次运行成功时间: 2026-03-16 02:18:40 +0800
# 功能说明: 验证 op attribute space 与 type space 不一致时会触发 verifier。
# 使用示例: pytest -q test/dialect/test_nn_dialect.py -k test_add_op_rejects_attr_space_mismatch
# 对应功能实现文件路径: python/dialect/nn.py
# 对应 spec 文件路径: spec/dialect/nn.md
# 对应测试文件路径: test/dialect/test_nn_dialect.py
def test_add_op_rejects_attr_space_mismatch() -> None:
    memory_type = _make_memory_type("local")
    lhs = _TestOp(result_types=[memory_type]).results[0]
    rhs = _TestOp(result_types=[memory_type]).results[0]
    op = NnAddOp(lhs, rhs, memory_type, _make_space("global"))
    with pytest.raises(VerifyException, match="attribute space"):
        op.verify()


# TY-007
# 创建者: 小李飞刀
# 最后一次更改: 小李飞刀
# 最近一次运行测试时间: 2026-03-16 02:18:40 +0800
# 最近一次运行成功时间: 2026-03-16 02:18:40 +0800
# 功能说明: 验证比较 op 结果 element_type 必须固定为 i1。
# 使用示例: pytest -q test/dialect/test_nn_dialect.py -k test_compare_op_requires_i1_result
# 对应功能实现文件路径: python/dialect/nn.py
# 对应 spec 文件路径: spec/dialect/nn.md
# 对应测试文件路径: test/dialect/test_nn_dialect.py
def test_compare_op_requires_i1_result() -> None:
    operand_type = _make_memory_type("global", i32)
    result_type = _make_memory_type("global", i32)
    lhs = _TestOp(result_types=[operand_type]).results[0]
    rhs = _TestOp(result_types=[operand_type]).results[0]
    op = NnEqOp(lhs, rhs, result_type, _make_space("global"))
    with pytest.raises(VerifyException, match="must be i1"):
        op.verify()


# TY-008
# 创建者: 小李飞刀
# 最后一次更改: 小李飞刀
# 最近一次运行测试时间: 2026-03-16 02:18:40 +0800
# 最近一次运行成功时间: 2026-03-16 02:18:40 +0800
# 功能说明: 验证模块 parse/print 可在 nn op 上保持 round-trip。
# 使用示例: pytest -q test/dialect/test_nn_dialect.py -k test_module_round_trip
# 对应功能实现文件路径: python/dialect/nn.py
# 对应 spec 文件路径: spec/dialect/nn.md
# 对应测试文件路径: test/dialect/test_nn_dialect.py
def test_module_round_trip() -> None:
    ctx = _build_context()
    text = """builtin.module {
  %0 = "test.op"() : () -> !nn.memory<[M, ?, 4], [4, 1, ?], i32, #nn.space<global>>
  %1 = "test.op"() : () -> !nn.memory<[M, ?, 4], [4, 1, ?], i32, #nn.space<global>>
  %2 = "nn.add"(%0, %1) {space = #nn.space<global>} : (!nn.memory<[M, ?, 4], [4, 1, ?], i32, #nn.space<global>>, !nn.memory<[M, ?, 4], [4, 1, ?], i32, #nn.space<global>>) -> !nn.memory<[M, ?, 4], [4, 1, ?], i32, #nn.space<global>>
}
"""
    module = Parser(ctx, text).parse_module()
    module.verify()
    assert _print_ir(module) == text.rstrip()


# TY-009
# 创建者: 小李飞刀
# 最后一次更改: 小李飞刀
# 最近一次运行测试时间: 2026-03-16 02:18:40 +0800
# 最近一次运行成功时间: 2026-03-16 02:18:40 +0800
# 功能说明: 验证 parse 后的 nn.add 在 space mismatch 场景下会被 verifier 捕获。
# 使用示例: pytest -q test/dialect/test_nn_dialect.py -k test_space_mismatch_from_text_rejected
# 对应功能实现文件路径: python/dialect/nn.py
# 对应 spec 文件路径: spec/dialect/nn.md
# 对应测试文件路径: test/dialect/test_nn_dialect.py
def test_space_mismatch_from_text_rejected() -> None:
    ctx = _build_context()
    text = """builtin.module {
  %0 = "test.op"() : () -> !nn.memory<[M], [1], i32, #nn.space<global>>
  %1 = "test.op"() : () -> !nn.memory<[M], [1], i32, #nn.space<shared>>
  %2 = "nn.add"(%0, %1) {space = #nn.space<global>} : (!nn.memory<[M], [1], i32, #nn.space<global>>, !nn.memory<[M], [1], i32, #nn.space<shared>>) -> !nn.memory<[M], [1], i32, #nn.space<global>>
}
"""
    module = Parser(ctx, text).parse_module()
    with pytest.raises(VerifyException, match="same space"):
        module.verify()


# TY-010
# 创建者: 小李飞刀
# 最后一次更改: 小李飞刀
# 最近一次运行测试时间: 2026-03-16 02:18:40 +0800
# 最近一次运行成功时间: 2026-03-16 02:18:40 +0800
# 功能说明: 验证文本 assembly 中 op attribute space 与 type space 不一致时会在 verify 阶段失败。
# 使用示例: pytest -q test/dialect/test_nn_dialect.py -k test_attr_space_mismatch_from_text_rejected
# 对应功能实现文件路径: python/dialect/nn.py
# 对应 spec 文件路径: spec/dialect/nn.md
# 对应测试文件路径: test/dialect/test_nn_dialect.py
def test_attr_space_mismatch_from_text_rejected() -> None:
    ctx = _build_context()
    text = """builtin.module {
  %0 = "test.op"() : () -> !nn.memory<[M], [1], i32, #nn.space<local>>
  %1 = "test.op"() : () -> !nn.memory<[M], [1], i32, #nn.space<local>>
  %2 = "nn.add"(%0, %1) {space = #nn.space<global>} : (!nn.memory<[M], [1], i32, #nn.space<local>>, !nn.memory<[M], [1], i32, #nn.space<local>>) -> !nn.memory<[M], [1], i32, #nn.space<local>>
}
"""
    module = Parser(ctx, text).parse_module()
    with pytest.raises(VerifyException, match="attribute space"):
        module.verify()


# TY-011
# 创建者: 小李飞刀
# 最后一次更改: 小李飞刀
# 最近一次运行测试时间: 2026-03-16 02:18:40 +0800
# 最近一次运行成功时间: 2026-03-16 02:18:40 +0800
# 功能说明: 验证缺失字段的 nn.memory 文本会在 parse 阶段失败。
# 使用示例: pytest -q test/dialect/test_nn_dialect.py -k test_memory_type_parse_requires_all_fields
# 对应功能实现文件路径: python/dialect/nn.py
# 对应 spec 文件路径: spec/dialect/nn.md
# 对应测试文件路径: test/dialect/test_nn_dialect.py
def test_memory_type_parse_requires_all_fields() -> None:
    ctx = _build_context()
    with pytest.raises(ParseError):
        Parser(ctx, "!nn.memory<[1], i32, #nn.space<global>>").parse_attribute()
