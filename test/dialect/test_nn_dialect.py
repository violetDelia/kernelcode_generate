"""nn dialect tests.

创建者: 小李飞刀
最后一次更改: 小李飞刀

功能说明:
- 覆盖 nn dialect 的 attr/type/op verifier、parse/print 与 round-trip 行为。

使用示例:
- pytest -q test/dialect/test_nn_dialect.py

关联文件:
- 功能实现: kernel_gen/dialect/nn.py
- Spec 文档: spec/dialect/nn.md
- 测试文件: test/dialect/test_nn_dialect.py
"""

from __future__ import annotations

from collections.abc import Sequence
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

from kernel_gen.dialect import Nn, NnAddOp, NnBroadcastOp, NnEqOp, NnMatmulOp, NnMemorySpaceAttr, NnMemoryType


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
    - 功能实现: kernel_gen/dialect/nn.py
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


def _make_simple_memory_type(
    shape: list[Attribute],
    stride: list[Attribute],
    space: str = "global",
    element_type: IntegerType = i32,
) -> NnMemoryType:
    """构造指定 shape/stride 的 nn memory type。

    创建者: 金铲铲大作战
    最后一次更改: 金铲铲大作战

    功能说明:
    - 便于构造 broadcast 与隐式广播拒绝测试所需类型。

    使用示例:
    - _make_simple_memory_type([IntAttr(1), StringAttr(\"N\")], [IntAttr(1), IntAttr(1)])

    关联文件:
    - spec: spec/dialect/nn.md
    - test: test/dialect/test_nn_dialect.py
    - 功能实现: kernel_gen/dialect/nn.py
    """
    return NnMemoryType(
        ArrayAttr(shape),
        ArrayAttr(stride),
        element_type,
        _make_space(space),
    )


def _make_matrix_type(
    shape: Sequence[Attribute],
    stride: Sequence[Attribute],
    space: str = "global",
    element_type: IntegerType = i32,
) -> NnMemoryType:
    """构造 rank=2 的 nn memory type。

    创建者: 金铲铲大作战
    最后一次更改: 金铲铲大作战

    功能说明:
    - 便于构造 matmul 用的 rank=2 memory type。

    使用示例:
    - _make_matrix_type([StringAttr(\"M\"), StringAttr(\"N\")], [IntAttr(8), IntAttr(1)])

    关联文件:
    - spec: spec/dialect/nn.md
    - test: test/dialect/test_nn_dialect.py
    - 功能实现: kernel_gen/dialect/nn.py
    """

    return NnMemoryType(
        ArrayAttr(list(shape)),
        ArrayAttr(list(stride)),
        element_type,
        _make_space(space),
    )


# TY-001
# 创建者: 小李飞刀
# 最后一次更改: 小李飞刀
# 最近一次运行测试时间: 2026-03-19 01:01:56 +0800
# 最近一次运行成功时间: 2026-03-19 01:01:56 +0800
# 功能说明: 验证 memory type parse/print 可稳定 round-trip。
# 使用示例: pytest -q test/dialect/test_nn_dialect.py -k test_memory_type_round_trip
# 对应功能实现文件路径: kernel_gen/dialect/nn.py
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
# 最近一次运行测试时间: 2026-03-19 01:01:56 +0800
# 最近一次运行成功时间: 2026-03-19 01:01:56 +0800
# 功能说明: 验证五种合法 space text form 均可 parse/print round-trip。
# 使用示例: pytest -q test/dialect/test_nn_dialect.py -k test_space_attr_round_trip
# 对应功能实现文件路径: kernel_gen/dialect/nn.py
# 对应 spec 文件路径: spec/dialect/nn.md
# 对应测试文件路径: test/dialect/test_nn_dialect.py
def test_space_attr_round_trip() -> None:
    ctx = _build_context()
    for text in [
        "#nn.space<global>",
        "#nn.space<shared>",
        "#nn.space<local>",
        "#nn.space<tsm>",
        "#nn.space<tlm>",
    ]:
        space_attr = Parser(ctx, text).parse_attribute()
        assert isinstance(space_attr, NnMemorySpaceAttr)
        space_attr.verify()
        assert _print_ir(space_attr) == text


# TY-002A
# 创建者: 小李飞刀
# 最后一次更改: 小李飞刀
# 最近一次运行测试时间: 2026-03-19 01:01:56 +0800
# 最近一次运行成功时间: 2026-03-19 01:01:56 +0800
# 功能说明: 验证非法 space attribute 会触发 verifier。
# 使用示例: pytest -q test/dialect/test_nn_dialect.py -k test_invalid_space_attr_rejected
# 对应功能实现文件路径: kernel_gen/dialect/nn.py
# 对应 spec 文件路径: spec/dialect/nn.md
# 对应测试文件路径: test/dialect/test_nn_dialect.py
def test_invalid_space_attr_rejected() -> None:
    with pytest.raises(VerifyException, match="global/shared/local/tsm/tlm"):
        _make_space("register").verify()


# TY-003
# 创建者: 小李飞刀
# 最后一次更改: 小李飞刀
# 最近一次运行测试时间: 2026-03-19 01:01:56 +0800
# 最近一次运行成功时间: 2026-03-19 01:01:56 +0800
# 功能说明: 验证 memory type 的 shape/stride rank mismatch 会触发 verifier。
# 使用示例: pytest -q test/dialect/test_nn_dialect.py -k test_memory_type_rank_mismatch_rejected
# 对应功能实现文件路径: kernel_gen/dialect/nn.py
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
# 最近一次运行测试时间: 2026-03-19 01:01:56 +0800
# 最近一次运行成功时间: 2026-03-19 01:01:56 +0800
# 功能说明: 验证 nn.add 在 operand/result/space 一致时可通过 verifier。
# 使用示例: pytest -q test/dialect/test_nn_dialect.py -k test_add_op_verify_success
# 对应功能实现文件路径: kernel_gen/dialect/nn.py
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
# 最近一次运行测试时间: 2026-03-19 01:01:56 +0800
# 最近一次运行成功时间: 2026-03-19 01:01:56 +0800
# 功能说明: 验证 nn.add operand space mismatch 会触发 verifier。
# 使用示例: pytest -q test/dialect/test_nn_dialect.py -k test_add_op_rejects_operand_space_mismatch
# 对应功能实现文件路径: kernel_gen/dialect/nn.py
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
# 最近一次运行测试时间: 2026-03-19 01:01:56 +0800
# 最近一次运行成功时间: 2026-03-19 01:01:56 +0800
# 功能说明: 验证 op attribute space 与 type space 不一致时会触发 verifier。
# 使用示例: pytest -q test/dialect/test_nn_dialect.py -k test_add_op_rejects_attr_space_mismatch
# 对应功能实现文件路径: kernel_gen/dialect/nn.py
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
# 最近一次运行测试时间: 2026-03-19 01:01:56 +0800
# 最近一次运行成功时间: 2026-03-19 01:01:56 +0800
# 功能说明: 验证比较 op 结果 element_type 必须固定为 i1。
# 使用示例: pytest -q test/dialect/test_nn_dialect.py -k test_compare_op_requires_i1_result
# 对应功能实现文件路径: kernel_gen/dialect/nn.py
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
# 最近一次运行测试时间: 2026-03-19 01:01:56 +0800
# 最近一次运行成功时间: 2026-03-19 01:01:56 +0800
# 功能说明: 验证模块 parse/print 可在 nn op 上保持 round-trip。
# 使用示例: pytest -q test/dialect/test_nn_dialect.py -k test_module_round_trip
# 对应功能实现文件路径: kernel_gen/dialect/nn.py
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
# 最近一次运行测试时间: 2026-03-19 01:01:56 +0800
# 最近一次运行成功时间: 2026-03-19 01:01:56 +0800
# 功能说明: 验证 parse 后的 nn.add 在 space mismatch 场景下会被 verifier 捕获。
# 使用示例: pytest -q test/dialect/test_nn_dialect.py -k test_space_mismatch_from_text_rejected
# 对应功能实现文件路径: kernel_gen/dialect/nn.py
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
# 最近一次运行测试时间: 2026-03-19 01:01:56 +0800
# 最近一次运行成功时间: 2026-03-19 01:01:56 +0800
# 功能说明: 验证文本 assembly 中 op attribute space 与 type space 不一致时会在 verify 阶段失败。
# 使用示例: pytest -q test/dialect/test_nn_dialect.py -k test_attr_space_mismatch_from_text_rejected
# 对应功能实现文件路径: kernel_gen/dialect/nn.py
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
# 最近一次运行测试时间: 2026-03-19 01:01:56 +0800
# 最近一次运行成功时间: 2026-03-19 01:01:56 +0800
# 功能说明: 验证缺失字段的 nn.memory 文本会在 parse 阶段失败。
# 使用示例: pytest -q test/dialect/test_nn_dialect.py -k test_memory_type_parse_requires_all_fields
# 对应功能实现文件路径: kernel_gen/dialect/nn.py
# 对应 spec 文件路径: spec/dialect/nn.md
# 对应测试文件路径: test/dialect/test_nn_dialect.py
def test_memory_type_parse_requires_all_fields() -> None:
    ctx = _build_context()
    with pytest.raises(ParseError):
        Parser(ctx, "!nn.memory<[1], i32, #nn.space<global>>").parse_attribute()


# TC-NN-BC-001
# 创建者: 小李飞刀
# 最后一次更改: 小李飞刀
# 最近一次运行测试时间: 2026-03-19 02:14:10 +0800
# 最近一次运行成功时间: 2026-03-19 02:14:10 +0800
# 功能说明: 验证 nn.broadcast 合法输入可通过 verifier。
# 使用示例: pytest -q test/dialect/test_nn_dialect.py -k test_broadcast_op_verify_success
# 对应功能实现文件路径: kernel_gen/dialect/nn.py
# 对应 spec 文件路径: spec/dialect/nn.md
# 对应测试文件路径: test/dialect/test_nn_dialect.py
def test_broadcast_op_verify_success() -> None:
    input_type = NnMemoryType(
        ArrayAttr([IntAttr(1), StringAttr("N")]),
        ArrayAttr([IntAttr(1), IntAttr(1)]),
        i32,
        _make_space("global"),
    )
    result_type = NnMemoryType(
        ArrayAttr([StringAttr("M"), StringAttr("N")]),
        ArrayAttr([IntAttr(1), IntAttr(1)]),
        i32,
        _make_space("global"),
    )
    inp = _TestOp(result_types=[input_type]).results[0]
    op = NnBroadcastOp(inp, result_type, _make_space("global"))
    op.verify()


# TC-NN-BC-002
# 创建者: 小李飞刀
# 最后一次更改: 小李飞刀
# 最近一次运行测试时间: 2026-03-19 02:14:10 +0800
# 最近一次运行成功时间: 2026-03-19 02:14:10 +0800
# 功能说明: 验证 nn.broadcast 在 space 不一致时报错。
# 使用示例: pytest -q test/dialect/test_nn_dialect.py -k test_broadcast_op_space_mismatch
# 对应功能实现文件路径: kernel_gen/dialect/nn.py
# 对应 spec 文件路径: spec/dialect/nn.md
# 对应测试文件路径: test/dialect/test_nn_dialect.py
def test_broadcast_op_space_mismatch() -> None:
    input_type = _make_memory_type("global", i32)
    result_type = _make_memory_type("shared", i32)
    inp = _TestOp(result_types=[input_type]).results[0]
    op = NnBroadcastOp(inp, result_type, _make_space("global"))
    with pytest.raises(VerifyException, match="space"):
        op.verify()


# TC-NN-BC-003
# 创建者: 小李飞刀
# 最后一次更改: 小李飞刀
# 最近一次运行测试时间: 2026-03-19 02:14:10 +0800
# 最近一次运行成功时间: 2026-03-19 02:14:10 +0800
# 功能说明: 验证 nn.broadcast 在 element_type 不一致时报错。
# 使用示例: pytest -q test/dialect/test_nn_dialect.py -k test_broadcast_op_element_type_mismatch
# 对应功能实现文件路径: kernel_gen/dialect/nn.py
# 对应 spec 文件路径: spec/dialect/nn.md
# 对应测试文件路径: test/dialect/test_nn_dialect.py
def test_broadcast_op_element_type_mismatch() -> None:
    input_type = _make_memory_type("global", i32)
    result_type = _make_memory_type("global", IntegerType(1))
    inp = _TestOp(result_types=[input_type]).results[0]
    op = NnBroadcastOp(inp, result_type, _make_space("global"))
    with pytest.raises(VerifyException, match="element_type"):
        op.verify()


# TC-NN-BC-004
# 创建者: 小李飞刀
# 最后一次更改: 小李飞刀
# 最近一次运行测试时间: 2026-03-19 02:14:10 +0800
# 最近一次运行成功时间: 2026-03-19 02:14:10 +0800
# 功能说明: 验证含 nn.broadcast 的模块可 round-trip。
# 使用示例: pytest -q test/dialect/test_nn_dialect.py -k test_broadcast_module_round_trip
# 对应功能实现文件路径: kernel_gen/dialect/nn.py
# 对应 spec 文件路径: spec/dialect/nn.md
# 对应测试文件路径: test/dialect/test_nn_dialect.py
def test_broadcast_module_round_trip() -> None:
    ctx = _build_context()
    text = """builtin.module {
  %0 = "test.op"() : () -> !nn.memory<[1, N], [1, 1], i32, #nn.space<global>>
  %1 = "nn.broadcast"(%0) {space = #nn.space<global>} : (!nn.memory<[1, N], [1, 1], i32, #nn.space<global>>) -> !nn.memory<[M, N], [1, 1], i32, #nn.space<global>>
}
"""
    module = Parser(ctx, text).parse_module()
    module.verify()
    assert _print_ir(module) == text.rstrip()


# TC-NN-MM-001
# 创建者: 金铲铲大作战
# 最后一次更改: 金铲铲大作战
# 最近一次运行测试时间: 2026-03-19 01:53:30 +0800
# 最近一次运行成功时间: 2026-03-19 01:53:30 +0800
# 功能说明: 验证 nn.matmul 在合法输入下通过 verifier。
# 使用示例: pytest -q test/dialect/test_nn_dialect.py -k test_matmul_op_verify_success
# 对应功能实现文件路径: kernel_gen/dialect/nn.py
# 对应 spec 文件路径: spec/dialect/nn.md
# 对应测试文件路径: test/dialect/test_nn_dialect.py
def test_matmul_op_verify_success() -> None:
    lhs_type = _make_matrix_type([StringAttr("M"), StringAttr("K")], [IntAttr(8), IntAttr(1)])
    rhs_type = _make_matrix_type([StringAttr("K"), StringAttr("N")], [IntAttr(8), IntAttr(1)])
    result_type = _make_matrix_type([StringAttr("M"), StringAttr("N")], [IntAttr(8), IntAttr(1)])
    lhs = _TestOp(result_types=[lhs_type]).results[0]
    rhs = _TestOp(result_types=[rhs_type]).results[0]
    op = NnMatmulOp(lhs, rhs, result_type, _make_space("global"))
    op.verify()


# TC-NN-MM-002
# 创建者: 金铲铲大作战
# 最后一次更改: 金铲铲大作战
# 最近一次运行测试时间: 2026-03-19 01:53:30 +0800
# 最近一次运行成功时间: 2026-03-19 01:53:30 +0800
# 功能说明: 验证 contracting 维度不匹配时 nn.matmul 抛错。
# 使用示例: pytest -q test/dialect/test_nn_dialect.py -k test_matmul_op_shape_mismatch
# 对应功能实现文件路径: kernel_gen/dialect/nn.py
# 对应 spec 文件路径: spec/dialect/nn.md
# 对应测试文件路径: test/dialect/test_nn_dialect.py
def test_matmul_op_shape_mismatch() -> None:
    lhs_type = _make_matrix_type([StringAttr("M"), StringAttr("K")], [IntAttr(8), IntAttr(1)])
    rhs_type = _make_matrix_type([StringAttr("Q"), StringAttr("N")], [IntAttr(8), IntAttr(1)])
    result_type = _make_matrix_type([StringAttr("M"), StringAttr("N")], [IntAttr(8), IntAttr(1)])
    lhs = _TestOp(result_types=[lhs_type]).results[0]
    rhs = _TestOp(result_types=[rhs_type]).results[0]
    op = NnMatmulOp(lhs, rhs, result_type, _make_space("global"))
    with pytest.raises(VerifyException, match="contracting"):
        op.verify()


# TC-NN-MM-003
# 创建者: 金铲铲大作战
# 最后一次更改: 金铲铲大作战
# 最近一次运行测试时间: 2026-03-19 01:53:30 +0800
# 最近一次运行成功时间: 2026-03-19 01:53:30 +0800
# 功能说明: 验证结果 shape 不匹配时 nn.matmul 抛错。
# 使用示例: pytest -q test/dialect/test_nn_dialect.py -k test_matmul_op_result_shape_mismatch
# 对应功能实现文件路径: kernel_gen/dialect/nn.py
# 对应 spec 文件路径: spec/dialect/nn.md
# 对应测试文件路径: test/dialect/test_nn_dialect.py
def test_matmul_op_result_shape_mismatch() -> None:
    lhs_type = _make_matrix_type([StringAttr("M"), StringAttr("K")], [IntAttr(8), IntAttr(1)])
    rhs_type = _make_matrix_type([StringAttr("K"), StringAttr("N")], [IntAttr(8), IntAttr(1)])
    result_type = _make_matrix_type([StringAttr("M"), StringAttr("K")], [IntAttr(8), IntAttr(1)])
    lhs = _TestOp(result_types=[lhs_type]).results[0]
    rhs = _TestOp(result_types=[rhs_type]).results[0]
    op = NnMatmulOp(lhs, rhs, result_type, _make_space("global"))
    with pytest.raises(VerifyException, match="result shape"):
        op.verify()


# TC-NN-MM-004
# 创建者: 金铲铲大作战
# 最后一次更改: 金铲铲大作战
# 最近一次运行测试时间: 2026-03-19 01:53:30 +0800
# 最近一次运行成功时间: 2026-03-19 01:53:30 +0800
# 功能说明: 验证含 nn.matmul 的模块 parse/print round-trip。
# 使用示例: pytest -q test/dialect/test_nn_dialect.py -k test_matmul_module_round_trip
# 对应功能实现文件路径: kernel_gen/dialect/nn.py
# 对应 spec 文件路径: spec/dialect/nn.md
# 对应测试文件路径: test/dialect/test_nn_dialect.py
def test_matmul_module_round_trip() -> None:
    ctx = _build_context()
    text = """builtin.module {
  %0 = "test.op"() : () -> !nn.memory<[M, K], [8, 1], i32, #nn.space<global>>
  %1 = "test.op"() : () -> !nn.memory<[K, N], [8, 1], i32, #nn.space<global>>
  %2 = "nn.matmul"(%0, %1) {space = #nn.space<global>} : (!nn.memory<[M, K], [8, 1], i32, #nn.space<global>>, !nn.memory<[K, N], [8, 1], i32, #nn.space<global>>) -> !nn.memory<[M, N], [8, 1], i32, #nn.space<global>>
}
"""
    module = Parser(ctx, text).parse_module()
    module.verify()
    assert _print_ir(module) == text.rstrip()


# TC-NN-MM-005
# 创建者: 金铲铲大作战
# 最后一次更改: 金铲铲大作战
# 最近一次运行测试时间: 2026-03-19 02:24:51 +0800
# 最近一次运行成功时间: 2026-03-19 02:24:51 +0800
# 功能说明: 验证 matmul operand space mismatch 会触发 verifier。
# 使用示例: pytest -q test/dialect/test_nn_dialect.py -k test_matmul_op_space_mismatch
# 对应功能实现文件路径: kernel_gen/dialect/nn.py
# 对应 spec 文件路径: spec/dialect/nn.md
# 对应测试文件路径: test/dialect/test_nn_dialect.py
def test_matmul_op_space_mismatch() -> None:
    lhs_type = _make_matrix_type([StringAttr("M"), StringAttr("K")], [IntAttr(8), IntAttr(1)], space="global")
    rhs_type = _make_matrix_type([StringAttr("K"), StringAttr("N")], [IntAttr(8), IntAttr(1)], space="shared")
    result_type = _make_matrix_type([StringAttr("M"), StringAttr("N")], [IntAttr(8), IntAttr(1)], space="global")
    lhs = _TestOp(result_types=[lhs_type]).results[0]
    rhs = _TestOp(result_types=[rhs_type]).results[0]
    op = NnMatmulOp(lhs, rhs, result_type, _make_space("global"))
    with pytest.raises(VerifyException, match="same space"):
        op.verify()


# TC-NN-MM-006
# 创建者: 金铲铲大作战
# 最后一次更改: 金铲铲大作战
# 最近一次运行测试时间: 2026-03-19 02:24:51 +0800
# 最近一次运行成功时间: 2026-03-19 02:24:51 +0800
# 功能说明: 验证 matmul attribute space mismatch 会触发 verifier。
# 使用示例: pytest -q test/dialect/test_nn_dialect.py -k test_matmul_op_attr_space_mismatch
# 对应功能实现文件路径: kernel_gen/dialect/nn.py
# 对应 spec 文件路径: spec/dialect/nn.md
# 对应测试文件路径: test/dialect/test_nn_dialect.py
def test_matmul_op_attr_space_mismatch() -> None:
    lhs_type = _make_matrix_type([StringAttr("M"), StringAttr("K")], [IntAttr(8), IntAttr(1)], space="local")
    rhs_type = _make_matrix_type([StringAttr("K"), StringAttr("N")], [IntAttr(8), IntAttr(1)], space="local")
    result_type = _make_matrix_type([StringAttr("M"), StringAttr("N")], [IntAttr(8), IntAttr(1)], space="local")
    lhs = _TestOp(result_types=[lhs_type]).results[0]
    rhs = _TestOp(result_types=[rhs_type]).results[0]
    op = NnMatmulOp(lhs, rhs, result_type, _make_space("global"))
    with pytest.raises(VerifyException, match="attribute space"):
        op.verify()


# TC-NN-MM-007
# 创建者: 金铲铲大作战
# 最后一次更改: 金铲铲大作战
# 最近一次运行测试时间: 2026-03-19 02:24:51 +0800
# 最近一次运行成功时间: 2026-03-19 02:24:51 +0800
# 功能说明: 验证 matmul rank!=2 会触发 verifier。
# 使用示例: pytest -q test/dialect/test_nn_dialect.py -k test_matmul_op_rank_mismatch
# 对应功能实现文件路径: kernel_gen/dialect/nn.py
# 对应 spec 文件路径: spec/dialect/nn.md
# 对应测试文件路径: test/dialect/test_nn_dialect.py
def test_matmul_op_rank_mismatch() -> None:
    lhs_type = _make_memory_type("global")
    rhs_type = _make_matrix_type([StringAttr("K"), StringAttr("N")], [IntAttr(8), IntAttr(1)], space="global")
    result_type = _make_matrix_type([StringAttr("M"), StringAttr("N")], [IntAttr(8), IntAttr(1)], space="global")
    lhs = _TestOp(result_types=[lhs_type]).results[0]
    rhs = _TestOp(result_types=[rhs_type]).results[0]
    op = NnMatmulOp(lhs, rhs, result_type, _make_space("global"))
    with pytest.raises(VerifyException, match="rank-2"):
        op.verify()


# TC-NN-MM-008
# 创建者: 金铲铲大作战
# 最后一次更改: 金铲铲大作战
# 最近一次运行测试时间: 2026-03-19 02:24:51 +0800
# 最近一次运行成功时间: 2026-03-19 02:24:51 +0800
# 功能说明: 验证 matmul element_type 不一致会触发 verifier。
# 使用示例: pytest -q test/dialect/test_nn_dialect.py -k test_matmul_op_element_type_mismatch
# 对应功能实现文件路径: kernel_gen/dialect/nn.py
# 对应 spec 文件路径: spec/dialect/nn.md
# 对应测试文件路径: test/dialect/test_nn_dialect.py
def test_matmul_op_element_type_mismatch() -> None:
    lhs_type = _make_matrix_type([StringAttr("M"), StringAttr("K")], [IntAttr(8), IntAttr(1)], element_type=i32)
    rhs_type = _make_matrix_type([StringAttr("K"), StringAttr("N")], [IntAttr(8), IntAttr(1)], element_type=i32)
    result_type = _make_matrix_type([StringAttr("M"), StringAttr("N")], [IntAttr(8), IntAttr(1)], element_type=IntegerType(16))
    lhs = _TestOp(result_types=[lhs_type]).results[0]
    rhs = _TestOp(result_types=[rhs_type]).results[0]
    op = NnMatmulOp(lhs, rhs, result_type, _make_space("global"))
    with pytest.raises(VerifyException, match="element_type"):
        op.verify()


# TC-NN-IB-001
# 创建者: 金铲铲大作战
# 最后一次更改: 金铲铲大作战
# 最近一次运行测试时间: 2026-03-19 02:40:00 +0800
# 最近一次运行成功时间: 2026-03-19 02:40:00 +0800
# 功能说明: 验证 nn.add 拒绝隐式 broadcast 形状。
# 使用示例: pytest -q test/dialect/test_nn_dialect.py -k test_add_op_rejects_implicit_broadcast_shape_mismatch
# 对应功能实现文件路径: kernel_gen/dialect/nn.py
# 对应 spec 文件路径: spec/dialect/nn.md
# 对应测试文件路径: test/dialect/test_nn_dialect.py
def test_add_op_rejects_implicit_broadcast_shape_mismatch() -> None:
    lhs_type = _make_simple_memory_type([IntAttr(1), StringAttr("N")], [IntAttr(1), IntAttr(1)])
    rhs_type = _make_simple_memory_type([StringAttr("M"), StringAttr("N")], [IntAttr(1), IntAttr(1)])
    result_type = _make_simple_memory_type([StringAttr("M"), StringAttr("N")], [IntAttr(1), IntAttr(1)])
    lhs = _TestOp(result_types=[lhs_type]).results[0]
    rhs = _TestOp(result_types=[rhs_type]).results[0]
    op = NnAddOp(lhs, rhs, result_type, _make_space("global"))
    with pytest.raises(VerifyException, match="shape"):
        op.verify()


# TC-NN-IB-002
# 创建者: 金铲铲大作战
# 最后一次更改: 金铲铲大作战
# 最近一次运行测试时间: 2026-03-19 02:40:00 +0800
# 最近一次运行成功时间: 2026-03-19 02:40:00 +0800
# 功能说明: 验证 nn.eq 拒绝隐式 broadcast 形状。
# 使用示例: pytest -q test/dialect/test_nn_dialect.py -k test_compare_op_rejects_implicit_broadcast_shape_mismatch
# 对应功能实现文件路径: kernel_gen/dialect/nn.py
# 对应 spec 文件路径: spec/dialect/nn.md
# 对应测试文件路径: test/dialect/test_nn_dialect.py
def test_compare_op_rejects_implicit_broadcast_shape_mismatch() -> None:
    lhs_type = _make_simple_memory_type([IntAttr(1), StringAttr("N")], [IntAttr(1), IntAttr(1)])
    rhs_type = _make_simple_memory_type([StringAttr("M"), StringAttr("N")], [IntAttr(1), IntAttr(1)])
    result_type = _make_simple_memory_type([StringAttr("M"), StringAttr("N")], [IntAttr(1), IntAttr(1)])
    lhs = _TestOp(result_types=[lhs_type]).results[0]
    rhs = _TestOp(result_types=[rhs_type]).results[0]
    op = NnEqOp(lhs, rhs, result_type, _make_space("global"))
    with pytest.raises(VerifyException, match="shape"):
        op.verify()


# TC-NN-IB-003
# 创建者: 金铲铲大作战
# 最后一次更改: 金铲铲大作战
# 最近一次运行测试时间: 2026-03-19 02:40:00 +0800
# 最近一次运行成功时间: 2026-03-19 02:40:00 +0800
# 功能说明: 验证显式 broadcast 后再执行 nn.add 可通过 verifier。
# 使用示例: pytest -q test/dialect/test_nn_dialect.py -k test_explicit_broadcast_then_add_verify_success
# 对应功能实现文件路径: kernel_gen/dialect/nn.py
# 对应 spec 文件路径: spec/dialect/nn.md
# 对应测试文件路径: test/dialect/test_nn_dialect.py
def test_explicit_broadcast_then_add_verify_success() -> None:
    input_type = _make_simple_memory_type([IntAttr(1), StringAttr("N")], [IntAttr(1), IntAttr(1)])
    target_type = _make_simple_memory_type([StringAttr("M"), StringAttr("N")], [IntAttr(1), IntAttr(1)])
    other_type = _make_simple_memory_type([StringAttr("M"), StringAttr("N")], [IntAttr(1), IntAttr(1)])
    inp = _TestOp(result_types=[input_type]).results[0]
    other = _TestOp(result_types=[other_type]).results[0]
    broadcast_op = NnBroadcastOp(inp, target_type, _make_space("global"))
    broadcast_op.verify()
    add_op = NnAddOp(broadcast_op.result, other, target_type, _make_space("global"))
    add_op.verify()
