"""dma dialect tests.

创建者: 小李飞刀
最后一次更改: 金铲铲大作战

功能说明:
- 覆盖 dma dialect 的 op verifier 与类型复用约束。
- 覆盖 SSA `!symbol.int<"expr">` operand 动态布局、parse/print round-trip 与默认连续 stride 约束。
- 覆盖 `dma.fill` 的 `i32 | !symbol.int<"expr"> -> i32 memory` 最小 verifier 闭环。

使用示例:
- pytest -q test/dialect/test_dma_dialect.py

当前覆盖率信息:
- `kernel_gen.dialect.dma`：`96%`（2026-03-22，`25 passed`）。

覆盖率命令:
- `pytest --cov=kernel_gen.dialect.dma --cov-report=term-missing test/dialect/test_dma_dialect.py`

关联文件:
- 功能实现: kernel_gen/dialect/dma.py
- Spec 文档: spec/dialect/dma.md
- 测试文件: test/dialect/test_dma_dialect.py
"""

from __future__ import annotations

import sys
from io import StringIO
from pathlib import Path

import pytest
from xdsl.context import Context
from xdsl.dialects.arith import Arith
from xdsl.dialects.builtin import (
    ArrayAttr,
    Builtin,
    IndexType,
    IntAttr,
    StringAttr,
    f32,
    i1,
    i8,
    i32,
)
from xdsl.dialects.builtin import ModuleOp
from xdsl.dialects.test import Test, TestOp as _TestOp
from xdsl.ir import Attribute, Operation, SSAValue
from xdsl.parser import Parser
from xdsl.printer import Printer
from xdsl.utils.exceptions import VerifyException

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from kernel_gen.dialect.dma import (
    Dma,
    DmaAllocOp,
    DmaBroadcastOp,
    DmaTransposeOp,
    DmaFillOp,
    DmaFreeOp,
    DmaCastOp,
    DmaCopyOp,
    DmaDesliceOp,
    DmaLoadOp,
    DmaReshapeOp,
    DmaSliceOp,
    DmaStoreOp,
    DmaViewOp,
)
from kernel_gen.dialect.nn import Nn, NnMemorySpaceAttr, NnMemoryType
from kernel_gen.dialect.symbol import Symbol, SymbolIterType, SymbolValueType


def _build_context() -> Context:
    """构造加载 builtin/test/symbol/nn/dma 的解析上下文。

    创建者: 小李飞刀
    最后一次更改: 小李飞刀

    功能说明:
    - 为 parser/printer/verify 测试提供统一 context。

    使用示例:
    - _build_context()

    关联文件:
    - spec: spec/dialect/dma.md
    - test: test/dialect/test_dma_dialect.py
    - 功能实现: kernel_gen/dialect/dma.py
    """

    ctx = Context()
    ctx.load_dialect(Builtin)
    ctx.load_dialect(Arith)
    ctx.load_dialect(Test)
    ctx.load_dialect(Symbol)
    ctx.load_dialect(Nn)
    ctx.load_dialect(Dma)
    return ctx


def _print_ir(value: object) -> str:
    """打印 attribute 或 operation/module 为文本。

    创建者: OpenAI
    最后一次更改: OpenAI

    功能说明:
    - 为 parse/print round-trip 测试生成稳定文本。

    使用示例:
    - _print_ir(module)

    关联文件:
    - spec: spec/dialect/dma.md
    - test: test/dialect/test_dma_dialect.py
    - 功能实现: kernel_gen/dialect/dma.py
    """

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
    """构造 space attribute。

    创建者: 小李飞刀
    最后一次更改: 小李飞刀

    功能说明:
    - 简化测试中的空间构造。

    使用示例:
    - _make_space("global")

    关联文件:
    - spec: spec/dialect/dma.md
    - test: test/dialect/test_dma_dialect.py
    - 功能实现: kernel_gen/dialect/dma.py
    """

    return NnMemorySpaceAttr(StringAttr(name))


def _make_memory_type(
    shape: ArrayAttr | None = None,
    stride: ArrayAttr | None = None,
    space: str = "global",
    element_type: Attribute | None = None,
) -> NnMemoryType:
    """构造 nn.memory type。

    创建者: 小李飞刀
    最后一次更改: 金铲铲大作战

    功能说明:
    - 提供默认可通过 verifier 的 memory type。
    - 允许显式指定 element_type，默认使用 i32。

    使用示例:
    - _make_memory_type()
    - _make_memory_type(element_type=i8)

    关联文件:
    - spec: spec/dialect/dma.md
    - test: test/dialect/test_dma_dialect.py
    - 功能实现: kernel_gen/dialect/dma.py
    """

    if shape is None:
        shape = ArrayAttr([IntAttr(2), IntAttr(4)])
    if stride is None:
        stride = ArrayAttr([IntAttr(4), IntAttr(1)])
    if element_type is None:
        element_type = i32
    return NnMemoryType(shape, stride, element_type, _make_space(space))


def _make_symbol_operands(values: list[int | str | None]) -> list[SSAValue]:
    """构造 `!symbol.int<"expr">` operand 列表。

    创建者: 小李飞刀
    最后一次更改: 小李飞刀

    功能说明:
    - `int` 映射为 `!symbol.int<"n">`。
    - `str` 映射为对应的符号表达式。
    - `None` 映射为运行期符号 SSA 值。

    使用示例:
    - _make_symbol_operands([0, "N"])

    关联文件:
    - spec: spec/dialect/dma.md
    - test: test/dialect/test_dma_dialect.py
    - 功能实现: kernel_gen/dialect/dma.py
    """

    operands: list[SSAValue] = []
    for index, value in enumerate(values):
        expr = f"dyn_{index}" if value is None else str(value)
        operands.append(_TestOp(result_types=[SymbolValueType.from_expr(expr)]).results[0])
    return operands


# TC-DMA-001
# 创建者: 小李飞刀
# 最后一次更改: 小李飞刀
# 最近一次运行测试时间: 2026-03-18 21:00:16 +0800
# 最近一次运行成功时间: 2026-03-18 21:00:16 +0800
# 功能说明: 验证 dma op 仅接受 nn.memory 作为 memory 类型。
# 使用示例: pytest -q test/dialect/test_dma_dialect.py -k test_dma_requires_nn_memory_type
# 对应功能实现文件路径: kernel_gen/dialect/dma.py
# 对应 spec 文件路径: spec/dialect/dma.md
# 对应测试文件路径: test/dialect/test_dma_dialect.py
def test_dma_requires_nn_memory_type() -> None:
    source = _TestOp(result_types=[i32]).results[0]
    target = _TestOp(result_types=[_make_memory_type()]).results[0]
    op = DmaCopyOp(source, target)
    with pytest.raises(VerifyException, match="nn.memory"):
        op.verify()


# TC-DMA-002
# 创建者: 小李飞刀
# 最后一次更改: 小李飞刀
# 最近一次运行测试时间: 2026-03-18 21:00:16 +0800
# 最近一次运行成功时间: 2026-03-18 21:00:16 +0800
# 功能说明: 验证 dma.copy 在合法输入下可通过 verifier。
# 使用示例: pytest -q test/dialect/test_dma_dialect.py -k test_dma_copy_verify_success
# 对应功能实现文件路径: kernel_gen/dialect/dma.py
# 对应 spec 文件路径: spec/dialect/dma.md
# 对应测试文件路径: test/dialect/test_dma_dialect.py
def test_dma_copy_verify_success() -> None:
    memory_type = _make_memory_type()
    source = _TestOp(result_types=[memory_type]).results[0]
    target = _TestOp(result_types=[memory_type]).results[0]
    op = DmaCopyOp(source, target)
    op.verify()


# TC-DMA-003
# 创建者: 小李飞刀
# 最后一次更改: 小李飞刀
# 最近一次运行测试时间: 2026-03-18 21:00:16 +0800
# 最近一次运行成功时间: 2026-03-18 21:00:16 +0800
# 功能说明: 验证 dma.copy 的 shape mismatch 会触发 verifier。
# 使用示例: pytest -q test/dialect/test_dma_dialect.py -k test_dma_copy_shape_mismatch
# 对应功能实现文件路径: kernel_gen/dialect/dma.py
# 对应 spec 文件路径: spec/dialect/dma.md
# 对应测试文件路径: test/dialect/test_dma_dialect.py
def test_dma_copy_shape_mismatch() -> None:
    source_type = _make_memory_type(shape=ArrayAttr([IntAttr(2), IntAttr(4)]))
    target_type = _make_memory_type(shape=ArrayAttr([IntAttr(2), IntAttr(8)]))
    source = _TestOp(result_types=[source_type]).results[0]
    target = _TestOp(result_types=[target_type]).results[0]
    op = DmaCopyOp(source, target)
    with pytest.raises(VerifyException, match="shape mismatch"):
        op.verify()


# TC-DMA-004
# 创建者: 小李飞刀
# 最后一次更改: 小李飞刀
# 最近一次运行测试时间: 2026-03-18 21:00:16 +0800
# 最近一次运行成功时间: 2026-03-18 21:00:16 +0800
# 功能说明: 验证 dma.load 的 result.space 必须与 op.space 一致，且结果 shape 必须匹配 sizes。
# 使用示例: pytest -q test/dialect/test_dma_dialect.py -k test_dma_load_result_space_mismatch
# 对应功能实现文件路径: kernel_gen/dialect/dma.py
# 对应 spec 文件路径: spec/dialect/dma.md
# 对应测试文件路径: test/dialect/test_dma_dialect.py
def test_dma_load_result_space_mismatch() -> None:
    source_type = _make_memory_type(space="global")
    result_type = _make_memory_type(space="global")
    source = _TestOp(result_types=[source_type]).results[0]
    offsets = _make_symbol_operands([0, 0])
    sizes = _make_symbol_operands([2, 4])
    strides = _make_symbol_operands([1, 1])
    op = DmaLoadOp(source, offsets, sizes, strides, result_type, _make_space("shared"))
    with pytest.raises(VerifyException, match="space attribute must match result space"):
        op.verify()

    result_type = _make_memory_type(shape=ArrayAttr([IntAttr(2), IntAttr(3)]), space="global")
    op = DmaLoadOp(source, offsets, sizes, strides, result_type, _make_space("global"))
    with pytest.raises(VerifyException, match="shape must match sizes"):
        op.verify()


# TC-DMA-058
# 创建者: 金铲铲大作战
# 最后一次更改: 金铲铲大作战
# 功能说明: 验证 dma.load 可接受 symbol.iter 作为 offsets 输入。
# 使用示例: pytest -q test/dialect/test_dma_dialect.py -k test_dma_load_accepts_symbol_iter_offset
# 对应功能实现文件路径: kernel_gen/dialect/dma.py
# 对应 spec 文件路径: spec/dialect/dma.md
# 对应测试文件路径: test/dialect/test_dma_dialect.py
def test_dma_load_accepts_symbol_iter_offset() -> None:
    source_type = _make_memory_type()
    result_type = _make_memory_type()
    source = _TestOp(result_types=[source_type]).results[0]
    iter_offset = _TestOp(result_types=[SymbolIterType.from_expr("index")]).results[0]
    zero_offset = _make_symbol_operands([0])[0]
    offsets = [iter_offset, zero_offset]
    sizes = _make_symbol_operands([2, 4])
    strides = _make_symbol_operands([1, 1])
    op = DmaLoadOp(source, offsets, sizes, strides, result_type, _make_space("global"))
    op.verify()


# TC-DMA-005
# 创建者: 小李飞刀
# 最后一次更改: 小李飞刀
# 最近一次运行测试时间: 2026-03-18 21:00:16 +0800
# 最近一次运行成功时间: 2026-03-18 21:00:16 +0800
# 功能说明: 验证 dma.slice 索引长度与 rank 不一致、结果 shape 不匹配时会报错。
# 使用示例: pytest -q test/dialect/test_dma_dialect.py -k test_dma_slice_rank_mismatch
# 对应功能实现文件路径: kernel_gen/dialect/dma.py
# 对应 spec 文件路径: spec/dialect/dma.md
# 对应测试文件路径: test/dialect/test_dma_dialect.py
def test_dma_slice_rank_mismatch() -> None:
    source_type = _make_memory_type()
    source = _TestOp(result_types=[source_type]).results[0]
    target = _TestOp(result_types=[source_type]).results[0]
    offsets = _make_symbol_operands([0])
    sizes = _make_symbol_operands([2])
    strides = _make_symbol_operands([1])
    op = DmaSliceOp(target, source, offsets, sizes, strides)
    with pytest.raises(VerifyException, match="length must match rank"):
        op.verify()

    offsets = _make_symbol_operands([0, 0])
    sizes = _make_symbol_operands([2, 4])
    strides = _make_symbol_operands([1, 1])
    target_type = _make_memory_type(shape=ArrayAttr([IntAttr(2), IntAttr(3)]))
    target = _TestOp(result_types=[target_type]).results[0]
    op = DmaSliceOp(target, source, offsets, sizes, strides)
    with pytest.raises(VerifyException, match="shape must match sizes"):
        op.verify()


# TC-DMA-006
# 创建者: 小李飞刀
# 最后一次更改: 小李飞刀
# 最近一次运行测试时间: 2026-03-18 21:00:16 +0800
# 最近一次运行成功时间: 2026-03-18 21:00:16 +0800
# 功能说明: 验证 dma.slice 在非 1 stride 下明确报错。
# 使用示例: pytest -q test/dialect/test_dma_dialect.py -k test_dma_slice_non_unit_stride_rejected
# 对应功能实现文件路径: kernel_gen/dialect/dma.py
# 对应 spec 文件路径: spec/dialect/dma.md
# 对应测试文件路径: test/dialect/test_dma_dialect.py
def test_dma_slice_non_unit_stride_rejected() -> None:
    source_type = _make_memory_type()
    source = _TestOp(result_types=[source_type]).results[0]
    target = _TestOp(result_types=[source_type]).results[0]
    offsets = _make_symbol_operands([0, 0])
    sizes = _make_symbol_operands([2, 4])
    strides = _make_symbol_operands([1, 2])
    op = DmaSliceOp(target, source, offsets, sizes, strides)
    with pytest.raises(VerifyException, match="dma stride must be 1 in current implementation"):
        op.verify()


# TC-DMA-007
# 创建者: 小李飞刀
# 最后一次更改: 小李飞刀
# 最近一次运行测试时间: 2026-03-18 21:00:16 +0800
# 最近一次运行成功时间: 2026-03-18 21:00:16 +0800
# 功能说明: 验证 dma.store 的 source.shape 与 sizes 不一致会报错。
# 使用示例: pytest -q test/dialect/test_dma_dialect.py -k test_dma_store_size_mismatch
# 对应功能实现文件路径: kernel_gen/dialect/dma.py
# 对应 spec 文件路径: spec/dialect/dma.md
# 对应测试文件路径: test/dialect/test_dma_dialect.py
def test_dma_store_size_mismatch() -> None:
    source_type = _make_memory_type(shape=ArrayAttr([IntAttr(2), IntAttr(4)]))
    target_type = _make_memory_type(shape=ArrayAttr([IntAttr(8), IntAttr(4)]))
    source = _TestOp(result_types=[source_type]).results[0]
    target = _TestOp(result_types=[target_type]).results[0]
    offsets = _make_symbol_operands([0, 0])
    sizes = _make_symbol_operands([2, 2])
    strides = _make_symbol_operands([1, 1])
    op = DmaStoreOp(source, target, offsets, sizes, strides)
    with pytest.raises(VerifyException, match="source shape must match sizes"):
        op.verify()


# TC-DMA-008
# 创建者: 小李飞刀
# 最后一次更改: 小李飞刀
# 最近一次运行测试时间: 2026-03-18 21:00:16 +0800
# 最近一次运行成功时间: 2026-03-18 21:00:16 +0800
# 功能说明: 验证 dma.deslice 在合法输入下通过 verifier。
# 使用示例: pytest -q test/dialect/test_dma_dialect.py -k test_dma_deslice_verify_success
# 对应功能实现文件路径: kernel_gen/dialect/dma.py
# 对应 spec 文件路径: spec/dialect/dma.md
# 对应测试文件路径: test/dialect/test_dma_dialect.py
def test_dma_deslice_verify_success() -> None:
    source_type = _make_memory_type(shape=ArrayAttr([IntAttr(2), IntAttr(4)]))
    target_type = _make_memory_type(shape=ArrayAttr([IntAttr(8), IntAttr(4)]))
    source = _TestOp(result_types=[source_type]).results[0]
    target = _TestOp(result_types=[target_type]).results[0]
    offsets = _make_symbol_operands([0, 0])
    sizes = _make_symbol_operands([2, 4])
    strides = _make_symbol_operands([1, 1])
    op = DmaDesliceOp(source, target, offsets, sizes, strides, target_type)
    op.verify()


# TC-DMA-009
# 创建者: 小李飞刀
# 最后一次更改: 小李飞刀
# 最近一次运行测试时间: 2026-03-18 21:00:16 +0800
# 最近一次运行成功时间: 2026-03-18 21:00:16 +0800
# 功能说明: 验证 dma op 透传 nn.memory 的类型 verifier 错误。
# 使用示例: pytest -q test/dialect/test_dma_dialect.py -k test_dma_nn_memory_type_verifier_passthrough
# 对应功能实现文件路径: kernel_gen/dialect/dma.py
# 对应 spec 文件路径: spec/dialect/dma.md
# 对应测试文件路径: test/dialect/test_dma_dialect.py
def test_dma_nn_memory_type_verifier_passthrough(monkeypatch: pytest.MonkeyPatch) -> None:
    memory_type = _make_memory_type()
    source = _TestOp(result_types=[memory_type]).results[0]
    target = _TestOp(result_types=[memory_type]).results[0]
    op = DmaCopyOp(source, target)

    def _raise_verify(_: NnMemoryType) -> None:
        raise VerifyException("nn memory shape and stride rank must match")

    monkeypatch.setattr(NnMemoryType, "verify", _raise_verify)
    with pytest.raises(VerifyException, match="nn memory shape and stride rank must match"):
        op.verify()


# TC-DMA-010
# 创建者: 朽木露琪亚
# 最后一次更改: OpenAI
# 最近一次运行测试时间: 2026-03-22 22:00:45 +0800
# 最近一次运行成功时间: 2026-03-22 22:00:45 +0800
# 功能说明: 验证动态 offsets/sizes/strides 通过 SSA `!symbol.int<"expr">` operand 传入时，load/store/slice/deslice 均可通过 verifier。
# 使用示例: pytest -q test/dialect/test_dma_dialect.py -k test_dma_dynamic_symbol_int_operands_valid
# 对应功能实现文件路径: kernel_gen/dialect/dma.py
# 对应 spec 文件路径: spec/dialect/dma.md
# 对应测试文件路径: test/dialect/test_dma_dialect.py
def test_dma_dynamic_symbol_int_operands_valid() -> None:
    source_type = _make_memory_type(
        shape=ArrayAttr([StringAttr("TM"), StringAttr("TN")]),
        stride=ArrayAttr([StringAttr("TN"), IntAttr(1)]),
    )
    result_type = _make_memory_type(
        shape=ArrayAttr([StringAttr("TM"), StringAttr("TN")]),
        stride=ArrayAttr([StringAttr("TN"), IntAttr(1)]),
        space="shared",
    )
    source = _TestOp(result_types=[source_type]).results[0]
    target = _TestOp(result_types=[source_type]).results[0]
    tile = _TestOp(result_types=[result_type]).results[0]
    offsets = _make_symbol_operands(["TO", "TI"])
    sizes = _make_symbol_operands(["TM", "TN"])
    strides = _make_symbol_operands([1, 1])

    DmaLoadOp(source, offsets, sizes, strides, result_type, _make_space("shared")).verify()
    DmaSliceOp(tile, source, offsets, sizes, strides).verify()
    DmaStoreOp(tile, target, offsets, sizes, strides).verify()
    DmaDesliceOp(tile, target, offsets, sizes, strides, source_type).verify()


# TC-DMA-011
# 创建者: 金铲铲大作战
# 最后一次更改: 金铲铲大作战
# 最近一次运行测试时间: 2026-03-21 18:26:48 +0800
# 最近一次运行成功时间: 2026-03-21 18:26:48 +0800
# 功能说明: 验证 dma.cast 在 shape/stride/space 一致时允许 element_type 不同。
# 使用示例: pytest -q test/dialect/test_dma_dialect.py -k test_dma_cast_verify_success
# 对应功能实现文件路径: kernel_gen/dialect/dma.py
# 对应 spec 文件路径: spec/dialect/dma.md
# 对应测试文件路径: test/dialect/test_dma_dialect.py
def test_dma_cast_verify_success() -> None:
    source_type = _make_memory_type()
    source = _TestOp(result_types=[source_type]).results[0]
    result_type = NnMemoryType(source_type.shape, source_type.stride, i1, source_type.space)
    op = DmaCastOp(source, result_type)
    op.verify()


# TC-DMA-012
# 创建者: 金铲铲大作战
# 最后一次更改: 金铲铲大作战
# 最近一次运行测试时间: 2026-03-21 18:26:48 +0800
# 最近一次运行成功时间: 2026-03-21 18:26:48 +0800
# 功能说明: 验证 dma.cast 在 shape/stride/space 不一致时会报错。
# 使用示例: pytest -q test/dialect/test_dma_dialect.py -k test_dma_cast_layout_or_space_mismatch
# 对应功能实现文件路径: kernel_gen/dialect/dma.py
# 对应 spec 文件路径: spec/dialect/dma.md
# 对应测试文件路径: test/dialect/test_dma_dialect.py
def test_dma_cast_layout_or_space_mismatch() -> None:
    source_type = _make_memory_type()
    source = _TestOp(result_types=[source_type]).results[0]

    result_type = _make_memory_type(shape=ArrayAttr([IntAttr(2), IntAttr(5)]))
    op = DmaCastOp(source, result_type)
    with pytest.raises(VerifyException, match="dma.cast shape mismatch"):
        op.verify()

    result_type = _make_memory_type(stride=ArrayAttr([IntAttr(5), IntAttr(1)]))
    op = DmaCastOp(source, result_type)
    with pytest.raises(VerifyException, match="dma.cast stride mismatch"):
        op.verify()

    result_type = _make_memory_type(space="shared")
    op = DmaCastOp(source, result_type)
    with pytest.raises(VerifyException, match="dma.cast space mismatch"):
        op.verify()


# TC-DMA-013
# 创建者: 朽木露琪亚
# 最后一次更改: 朽木露琪亚
# 最近一次运行测试时间: 2026-03-22 15:01:08 +0800
# 最近一次运行成功时间: 2026-03-22 15:01:08 +0800
# 功能说明: 验证 dma.alloc 在 dynamic_shape operand 与结果 rank/shape 一致时可通过 verifier。
# 使用示例: pytest -q test/dialect/test_dma_dialect.py -k test_dma_alloc_verify_success
# 对应功能实现文件路径: kernel_gen/dialect/dma.py
# 对应 spec 文件路径: spec/dialect/dma.md
# 对应测试文件路径: test/dialect/test_dma_dialect.py
def test_dma_alloc_verify_success() -> None:
    result_type = _make_memory_type()
    op = DmaAllocOp(_make_symbol_operands([2, 4]), result_type)
    op.verify()


# TC-DMA-023
# 创建者: 小李飞刀
# 最后一次更改: 小李飞刀
# 最近一次运行测试时间: 2026-03-27 23:48:38 +0800
# 最近一次运行成功时间: 2026-03-27 23:48:38 +0800
# 功能说明: 验证 dma.free 仅接受 nn.memory 类型，非内存类型报错。
# 使用示例: pytest -q test/dialect/test_dma_dialect.py -k test_dma_free_requires_nn_memory_type
# 对应功能实现文件路径: kernel_gen/dialect/dma.py
# 对应 spec 文件路径: spec/dialect/dma.md
# 对应测试文件路径: test/dialect/test_dma_dialect.py
def test_dma_free_requires_nn_memory_type() -> None:
    memory_type = _make_memory_type()
    source = _TestOp(result_types=[memory_type]).results[0]
    op = DmaFreeOp(source)
    op.verify()

    bad_source = _TestOp(result_types=[i32]).results[0]
    op = DmaFreeOp(bad_source)
    with pytest.raises(VerifyException, match="nn.memory"):
        op.verify()


# TC-DMA-014
# 创建者: 金铲铲大作战
# 最后一次更改: 金铲铲大作战
# 最近一次运行测试时间: 2026-03-21 21:58:00 +0800
# 最近一次运行成功时间: 2026-03-21 21:58:00 +0800
# 功能说明: 验证 dma.view 在 element_type 或 space 不一致时会报错。
# 使用示例: pytest -q test/dialect/test_dma_dialect.py -k test_dma_view_type_or_space_mismatch
# 对应功能实现文件路径: kernel_gen/dialect/dma.py
# 对应 spec 文件路径: spec/dialect/dma.md
# 对应测试文件路径: test/dialect/test_dma_dialect.py
def test_dma_view_type_or_space_mismatch() -> None:
    source_type = _make_memory_type()
    source = _TestOp(result_types=[source_type]).results[0]
    offsets = _make_symbol_operands([0, 0])
    shape = _make_symbol_operands([2, 4])
    stride = _make_symbol_operands([4, 1])

    result_type = NnMemoryType(source_type.shape, source_type.stride, i1, source_type.space)
    op = DmaViewOp(source, offsets, shape, stride, result_type)
    with pytest.raises(VerifyException, match="element_type mismatch"):
        op.verify()

    result_type = _make_memory_type(space="shared")
    op = DmaViewOp(source, offsets, shape, stride, result_type)
    with pytest.raises(VerifyException, match="space mismatch"):
        op.verify()


# TC-DMA-015
# 创建者: 金铲铲大作战
# 最后一次更改: 金铲铲大作战
# 最近一次运行测试时间: 2026-03-21 21:58:00 +0800
# 最近一次运行成功时间: 2026-03-21 21:58:00 +0800
# 功能说明: 验证 dma.view 在可判定元素总数不一致时会报错。
# 使用示例: pytest -q test/dialect/test_dma_dialect.py -k test_dma_view_numel_mismatch
# 对应功能实现文件路径: kernel_gen/dialect/dma.py
# 对应 spec 文件路径: spec/dialect/dma.md
# 对应测试文件路径: test/dialect/test_dma_dialect.py
def test_dma_view_numel_mismatch() -> None:
    source_type = _make_memory_type(shape=ArrayAttr([IntAttr(2), IntAttr(4)]))
    source = _TestOp(result_types=[source_type]).results[0]
    result_type = _make_memory_type(
        shape=ArrayAttr([IntAttr(2), IntAttr(5)]),
        stride=ArrayAttr([IntAttr(5), IntAttr(1)]),
    )
    op = DmaViewOp(
        source,
        _make_symbol_operands([0, 0]),
        _make_symbol_operands([2, 5]),
        _make_symbol_operands([5, 1]),
        result_type,
    )
    with pytest.raises(VerifyException, match="numel mismatch"):
        op.verify()


# TC-DMA-016
# 创建者: 金铲铲大作战
# 最后一次更改: 金铲铲大作战
# 最近一次运行测试时间: 2026-03-21 21:58:00 +0800
# 最近一次运行成功时间: 2026-03-21 21:58:00 +0800
# 功能说明: 验证 dma.reshape 在非连续布局时会报错。
# 使用示例: pytest -q test/dialect/test_dma_dialect.py -k test_dma_reshape_requires_contiguous
# 对应功能实现文件路径: kernel_gen/dialect/dma.py
# 对应 spec 文件路径: spec/dialect/dma.md
# 对应测试文件路径: test/dialect/test_dma_dialect.py
def test_dma_reshape_requires_contiguous() -> None:
    source_type = _make_memory_type(
        shape=ArrayAttr([IntAttr(2), IntAttr(4)]),
        stride=ArrayAttr([IntAttr(5), IntAttr(1)]),
    )
    result_type = _make_memory_type(
        shape=ArrayAttr([IntAttr(4), IntAttr(2)]),
        stride=ArrayAttr([IntAttr(2), IntAttr(1)]),
    )
    source = _TestOp(result_types=[source_type]).results[0]
    op = DmaReshapeOp(source, _make_symbol_operands([4, 2]), result_type)
    with pytest.raises(VerifyException, match="contiguous source"):
        op.verify()


# TC-DMA-017
# 创建者: 朽木露琪亚
# 最后一次更改: OpenAI
# 最近一次运行测试时间: 2026-03-22 22:00:45 +0800
# 最近一次运行成功时间: 2026-03-22 22:00:45 +0800
# 功能说明: 验证 dma.reshape 支持通过 SSA shape operand 表达动态结果形状，且结果 stride 必须满足默认连续布局。
# 使用示例: pytest -q test/dialect/test_dma_dialect.py -k test_dma_reshape_allows_dynamic_symbol_int_shape_operands
# 对应功能实现文件路径: kernel_gen/dialect/dma.py
# 对应 spec 文件路径: spec/dialect/dma.md
# 对应测试文件路径: test/dialect/test_dma_dialect.py
def test_dma_reshape_allows_dynamic_symbol_int_shape_operands() -> None:
    source_type = _make_memory_type(
        shape=ArrayAttr([IntAttr(2), IntAttr(4)]),
        stride=ArrayAttr([IntAttr(4), IntAttr(1)]),
    )
    result_type = _make_memory_type(
        shape=ArrayAttr([StringAttr("M"), StringAttr("N")]),
        stride=ArrayAttr([StringAttr("N"), IntAttr(1)]),
    )
    source = _TestOp(result_types=[source_type]).results[0]
    op = DmaReshapeOp(source, _make_symbol_operands(["M", "N"]), result_type)
    op.verify()

    bad_result_type = _make_memory_type(
        shape=ArrayAttr([StringAttr("M"), StringAttr("N")]),
        stride=ArrayAttr([StringAttr("M"), IntAttr(1)]),
    )
    op = DmaReshapeOp(source, _make_symbol_operands(["M", "N"]), bad_result_type)
    with pytest.raises(VerifyException, match="dma.reshape requires contiguous result stride"):
        op.verify()


# TC-DMA-018
# 创建者: 朽木露琪亚
# 最后一次更改: 朽木露琪亚
# 最近一次运行测试时间: 2026-03-22 15:01:08 +0800
# 最近一次运行成功时间: 2026-03-22 15:01:08 +0800
# 功能说明: 验证 dma.reshape 在 SSA shape operand 与 source 元素总数不一致时会报错。
# 使用示例: pytest -q test/dialect/test_dma_dialect.py -k test_dma_reshape_numel_mismatch
# 对应功能实现文件路径: kernel_gen/dialect/dma.py
# 对应 spec 文件路径: spec/dialect/dma.md
# 对应测试文件路径: test/dialect/test_dma_dialect.py
def test_dma_reshape_numel_mismatch() -> None:
    source_type = _make_memory_type(
        shape=ArrayAttr([IntAttr(2), IntAttr(4)]),
        stride=ArrayAttr([IntAttr(4), IntAttr(1)]),
    )
    result_type = _make_memory_type(
        shape=ArrayAttr([IntAttr(3), IntAttr(3)]),
        stride=ArrayAttr([IntAttr(3), IntAttr(1)]),
    )
    source = _TestOp(result_types=[source_type]).results[0]
    op = DmaReshapeOp(source, _make_symbol_operands([3, 3]), result_type)
    with pytest.raises(VerifyException, match="numel mismatch"):
        op.verify()


# TC-DMA-019
# 创建者: 朽木露琪亚
# 最后一次更改: OpenAI
# 最近一次运行测试时间: 2026-03-22 22:00:45 +0800
# 最近一次运行成功时间: 2026-03-22 22:00:45 +0800
# 功能说明: 验证 dma.view 支持通过 SSA shape/stride operand 表达动态布局。
# 使用示例: pytest -q test/dialect/test_dma_dialect.py -k test_dma_view_dynamic_symbol_int_layout_operands_valid
# 对应功能实现文件路径: kernel_gen/dialect/dma.py
# 对应 spec 文件路径: spec/dialect/dma.md
# 对应测试文件路径: test/dialect/test_dma_dialect.py
def test_dma_view_dynamic_symbol_int_layout_operands_valid() -> None:
    source_type = _make_memory_type(
        shape=ArrayAttr([StringAttr("M"), StringAttr("N")]),
        stride=ArrayAttr([StringAttr("N"), IntAttr(1)]),
    )
    result_type = _make_memory_type(
        shape=ArrayAttr([StringAttr("TM"), StringAttr("TN")]),
        stride=ArrayAttr([StringAttr("TN"), IntAttr(1)]),
    )
    source = _TestOp(result_types=[source_type]).results[0]
    op = DmaViewOp(
        source,
        _make_symbol_operands(["TO", "TI"]),
        _make_symbol_operands(["TM", "TN"]),
        _make_symbol_operands(["TN", 1]),
        result_type,
    )
    op.verify()


# TC-DMA-019B
# 创建者: OpenAI
# 最后一次更改: OpenAI
# 最近一次运行测试时间: 2026-03-29 00:00:00 +0800
# 最近一次运行成功时间: 2026-03-29 00:00:00 +0800
# 功能说明: 验证 dma.view 在 numel 匹配时可接受与 source 不同的显式 stride/result 布局。
# 使用示例: pytest -q test/dialect/test_dma_dialect.py -k test_dma_view_accepts_matching_numel_subset_with_explicit_stride
# 对应功能实现文件路径: kernel_gen/dialect/dma.py
# 对应 spec 文件路径: spec/dialect/dma.md
# 对应测试文件路径: test/dialect/test_dma_dialect.py
def test_dma_view_accepts_matching_numel_subset_with_explicit_stride() -> None:
    source_type = _make_memory_type(
        shape=ArrayAttr([IntAttr(2), IntAttr(2)]),
        stride=ArrayAttr([IntAttr(2), IntAttr(1)]),
    )
    result_type = _make_memory_type(
        shape=ArrayAttr([IntAttr(2), IntAttr(2)]),
        stride=ArrayAttr([IntAttr(1), IntAttr(1)]),
    )
    source = _TestOp(result_types=[source_type]).results[0]
    op = DmaViewOp(
        source,
        _make_symbol_operands([0, 0]),
        _make_symbol_operands([2, 2]),
        _make_symbol_operands([1, 1]),
        result_type,
    )
    op.verify()


# TC-DMA-019D
# 创建者: 金铲铲大作战
# 最后一次更改: 金铲铲大作战
# 最近一次运行测试时间: 2026-04-07 23:00:00 +0800
# 最近一次运行成功时间: 2026-04-07 23:00:00 +0800
# 功能说明: 验证 dma.view 支持 i8 byte pool typed view 的字节数与边界校验。
# 使用示例: pytest -q test/dialect/test_dma_dialect.py -k test_dma_view_byte_pool_typed_view
# 对应功能实现文件路径: kernel_gen/dialect/dma.py
# 对应 spec 文件路径: spec/dialect/dma.md
# 对应测试文件路径: test/dialect/test_dma_dialect.py
def test_dma_view_byte_pool_typed_view() -> None:
    source_type = NnMemoryType(
        ArrayAttr([IntAttr(16)]),
        ArrayAttr([IntAttr(1)]),
        i8,
        _make_space("global"),
    )
    source = _TestOp(result_types=[source_type]).results[0]

    result_type = _make_memory_type(
        shape=ArrayAttr([IntAttr(2), IntAttr(2)]),
        stride=ArrayAttr([IntAttr(2), IntAttr(1)]),
        element_type=i32,
        space="global",
    )
    op = DmaViewOp(
        source,
        _make_symbol_operands([0, 0]),
        _make_symbol_operands([2, 2]),
        _make_symbol_operands([2, 1]),
        result_type,
    )
    op.verify()

    bad_length_type = _make_memory_type(
        shape=ArrayAttr([IntAttr(3), IntAttr(2)]),
        stride=ArrayAttr([IntAttr(2), IntAttr(1)]),
        element_type=i32,
        space="global",
    )
    op = DmaViewOp(
        source,
        _make_symbol_operands([0, 0]),
        _make_symbol_operands([3, 2]),
        _make_symbol_operands([2, 1]),
        bad_length_type,
    )
    with pytest.raises(VerifyException, match="byte length mismatch"):
        op.verify()

    bad_stride_type = _make_memory_type(
        shape=ArrayAttr([IntAttr(2), IntAttr(2)]),
        stride=ArrayAttr([IntAttr(3), IntAttr(1)]),
        element_type=i32,
        space="global",
    )
    op = DmaViewOp(
        source,
        _make_symbol_operands([2, 0]),
        _make_symbol_operands([2, 2]),
        _make_symbol_operands([3, 1]),
        bad_stride_type,
    )
    with pytest.raises(VerifyException, match="byte bounds mismatch"):
        op.verify()


# 创建者: OpenAI
# 最后一次更改: OpenAI
# 最近一次运行测试时间: 2026-03-28 19:26:00 +0800
# 最近一次运行成功时间: 2026-03-28 19:26:00 +0800
# 功能说明: 验证 dma.view 的 offsets 需要与 rank 一致且静态场景下会执行边界检查。
# 使用示例: pytest -q test/dialect/test_dma_dialect.py -k test_dma_view_rejects_invalid_offsets_or_bounds
# 对应功能实现文件路径: kernel_gen/dialect/dma.py
# 对应 spec 文件路径: spec/dialect/dma.md
# 对应测试文件路径: test/dialect/test_dma_dialect.py
def test_dma_view_rejects_invalid_offsets_or_bounds() -> None:
    source_type = _make_memory_type()
    source = _TestOp(result_types=[source_type]).results[0]
    result_type = _make_memory_type(
        shape=ArrayAttr([IntAttr(2), IntAttr(4)]),
        stride=ArrayAttr([IntAttr(1), IntAttr(1)]),
    )

    with pytest.raises(VerifyException, match="offsets length must match rank"):
        DmaViewOp(
            source,
            [],
            _make_symbol_operands([2, 4]),
            _make_symbol_operands([1, 1]),
            result_type,
        ).verify()

    with pytest.raises(TypeError, match="missing 1 required positional argument"):
        DmaViewOp(
            source,
            _make_symbol_operands([0]),
            _make_symbol_operands([2, 4]),
            _make_symbol_operands([1, 1]),
        )

    with pytest.raises(VerifyException, match="offsets entries must be >= 0"):
        DmaViewOp(
            source,
            _make_symbol_operands([-1, 0]),
            _make_symbol_operands([2, 4]),
            _make_symbol_operands([1, 1]),
            result_type,
        ).verify()

    with pytest.raises(VerifyException, match="dma.view bounds mismatch"):
        DmaViewOp(
            source,
            _make_symbol_operands([1, 0]),
            _make_symbol_operands([2, 4]),
            _make_symbol_operands([1, 1]),
            result_type,
        ).verify()


# TC-DMA-020
# 创建者: 朽木露琪亚
# 最后一次更改: 小李飞刀
# 最近一次运行测试时间: 2026-04-07 19:01:20 +0800
# 最近一次运行成功时间: 2026-04-07 19:01:20 +0800
# 功能说明: 验证 dma.alloc 支持通过 SSA dynamic_shape operand 表达动态形状，且结果 stride 可按显式值通过校验。
# 使用示例: pytest -q test/dialect/test_dma_dialect.py -k test_dma_alloc_dynamic_symbol_int_shape_operands_valid
# 对应功能实现文件路径: kernel_gen/dialect/dma.py
# 对应 spec 文件路径: spec/dialect/dma.md
# 对应测试文件路径: test/dialect/test_dma_dialect.py
def test_dma_alloc_dynamic_symbol_int_shape_operands_valid() -> None:
    result_type = _make_memory_type(
        shape=ArrayAttr([StringAttr("M"), StringAttr("N")]),
        stride=ArrayAttr([StringAttr("N"), IntAttr(1)]),
    )
    op = DmaAllocOp(_make_symbol_operands(["M", "N"]), result_type)
    op.verify()

    non_contiguous_result_type = _make_memory_type(
        shape=ArrayAttr([StringAttr("M"), StringAttr("N")]),
        stride=ArrayAttr([IntAttr(1), StringAttr("M")]),
    )
    op = DmaAllocOp(_make_symbol_operands(["M", "N"]), non_contiguous_result_type)
    op.verify()

    mixed_result_type = _make_memory_type(
        shape=ArrayAttr([StringAttr("M"), IntAttr(4)]),
        stride=ArrayAttr([IntAttr(4), IntAttr(1)]),
    )
    op = DmaAllocOp(_make_symbol_operands(["M"]), mixed_result_type)
    op.verify()


# TC-DMA-021
# 创建者: 朽木露琪亚
# 最后一次更改: 小李飞刀
# 最近一次运行测试时间: 2026-04-02 16:18:58 +0800
# 最近一次运行成功时间: 2026-04-02 16:18:58 +0800
# 功能说明: 验证 SSA `!symbol.int<"expr">` operand 版本的 dma.alloc/fill/view/load/store/slice/deslice/reshape/cast 支持 generic parse/print round-trip。
# 使用示例: pytest -q test/dialect/test_dma_dialect.py -k test_dma_dynamic_symbol_int_parse_print_round_trip
# 对应功能实现文件路径: kernel_gen/dialect/dma.py
# 对应 spec 文件路径: spec/dialect/dma.md
# 对应测试文件路径: test/dialect/test_dma_dialect.py
def test_dma_dynamic_symbol_int_parse_print_round_trip() -> None:
    ctx = _build_context()
    c0 = _TestOp(result_types=[SymbolValueType.from_expr("2")])
    c1 = _TestOp(result_types=[SymbolValueType.from_expr("4")])
    c2 = _TestOp(result_types=[SymbolValueType.from_expr("0")])
    c3 = _TestOp(result_types=[SymbolValueType.from_expr("1")])

    alloc_type = _make_memory_type()
    view_type = _make_memory_type(
        shape=ArrayAttr([IntAttr(2), IntAttr(4)]),
        stride=ArrayAttr([IntAttr(1), IntAttr(1)]),
    )
    reshape_type = _make_memory_type(
        shape=ArrayAttr([IntAttr(4), IntAttr(2)]),
        stride=ArrayAttr([IntAttr(2), IntAttr(1)]),
    )
    load_type = _make_memory_type(space="shared")

    alloc = DmaAllocOp([c0.results[0], c1.results[0]], alloc_type)
    fill = DmaFillOp(alloc.result, c0.results[0])
    view = DmaViewOp(
        alloc.result,
        [c2.results[0], c2.results[0]],
        [c0.results[0], c1.results[0]],
        [c3.results[0], c3.results[0]],
        view_type,
    )
    load = DmaLoadOp(
        alloc.result,
        [c2.results[0], c2.results[0]],
        [c0.results[0], c1.results[0]],
        [c3.results[0], c3.results[0]],
        load_type,
        _make_space("shared"),
    )
    store = DmaStoreOp(
        load.result,
        alloc.result,
        [c2.results[0], c2.results[0]],
        [c0.results[0], c1.results[0]],
        [c3.results[0], c3.results[0]],
    )
    slice_op = DmaSliceOp(
        alloc.result,
        alloc.result,
        [c2.results[0], c2.results[0]],
        [c0.results[0], c1.results[0]],
        [c3.results[0], c3.results[0]],
    )
    deslice = DmaDesliceOp(
        load.result,
        alloc.result,
        [c2.results[0], c2.results[0]],
        [c0.results[0], c1.results[0]],
        [c3.results[0], c3.results[0]],
        alloc_type,
    )
    reshape = DmaReshapeOp(alloc.result, [c1.results[0], c0.results[0]], reshape_type)
    cast = DmaCastOp(alloc.result, NnMemoryType(alloc_type.shape, alloc_type.stride, i1, alloc_type.space))

    module = ModuleOp([c0, c1, c2, c3, alloc, fill, view, load, store, slice_op, deslice, reshape, cast])
    printed = _print_ir(module).rstrip()
    reparsed = Parser(ctx, printed).parse_module()
    reparsed.verify()
    assert _print_ir(reparsed).rstrip() == printed


# TC-DMA-022
# 创建者: OpenAI
# 最后一次更改: OpenAI
# 最近一次运行测试时间: 2026-03-22 22:00:45 +0800
# 最近一次运行成功时间: 2026-03-22 22:00:45 +0800
# 功能说明: 验证 dma 受影响标量输入若使用 builtin `index` 等非 `!symbol.int<"expr">` 类型会被 verifier 拒绝。
# 使用示例: pytest -q test/dialect/test_dma_dialect.py -k test_dma_rejects_non_symbol_int_scalar_operands
# 对应功能实现文件路径: kernel_gen/dialect/dma.py
# 对应 spec 文件路径: spec/dialect/dma.md
# 对应测试文件路径: test/dialect/test_dma_dialect.py
def test_dma_rejects_non_symbol_int_scalar_operands() -> None:
    source_type = _make_memory_type()
    source = _TestOp(result_types=[source_type]).results[0]
    target = _TestOp(result_types=[source_type]).results[0]
    index_operand = _TestOp(result_types=[IndexType()]).results[0]
    symbol_sizes = _make_symbol_operands([2, 4])
    symbol_strides = _make_symbol_operands([1, 1])

    with pytest.raises(VerifyException, match="base attribute symbol.int"):
        DmaLoadOp(
            source,
            [index_operand, index_operand],
            symbol_sizes,
            symbol_strides,
            source_type,
            _make_space("global"),
        ).verify()

    with pytest.raises(VerifyException, match="base attribute symbol.int"):
        DmaAllocOp([index_operand, index_operand], source_type).verify()

    with pytest.raises(VerifyException, match="base attribute symbol.int"):
        DmaViewOp(
            source,
            [index_operand, index_operand],
            _make_symbol_operands([2, 4]),
            _make_symbol_operands([4, 1]),
            source_type,
        ).verify()

    with pytest.raises(VerifyException, match="base attribute symbol.int"):
        DmaReshapeOp(
            target,
            [index_operand, index_operand],
            source_type,
        ).verify()

    with pytest.raises(VerifyException, match="value must be builtin i32 or !symbol.int"):
        DmaFillOp(target, index_operand).verify()


# TC-DMA-024
# 创建者: 小李飞刀
# 最后一次更改: 小李飞刀
# 最近一次运行测试时间: 2026-04-02 15:27:34 +0800
# 最近一次运行成功时间: 2026-04-02 15:27:34 +0800
# 功能说明: 验证 dma.fill 接受 builtin i32 SSA value 并通过 verifier。
# 使用示例: pytest -q test/dialect/test_dma_dialect.py -k test_dma_fill_accepts_builtin_i32_scalar_operand
# 对应功能实现文件路径: kernel_gen/dialect/dma.py
# 对应 spec 文件路径: spec/dialect/dma.md
# 对应测试文件路径: test/dialect/test_dma_dialect.py
def test_dma_fill_accepts_builtin_i32_scalar_operand() -> None:
    target = _TestOp(result_types=[_make_memory_type()]).results[0]
    value = _TestOp(result_types=[i32]).results[0]

    DmaFillOp(target, value).verify()


# TC-DMA-025
# 创建者: 小李飞刀
# 最后一次更改: 小李飞刀
# 最近一次运行测试时间: 2026-04-02 15:27:34 +0800
# 最近一次运行成功时间: 2026-04-02 15:27:34 +0800
# 功能说明: 验证 dma.fill 接受 !symbol.int SSA value 并通过 verifier。
# 使用示例: pytest -q test/dialect/test_dma_dialect.py -k test_dma_fill_accepts_symbol_int_scalar_operand
# 对应功能实现文件路径: kernel_gen/dialect/dma.py
# 对应 spec 文件路径: spec/dialect/dma.md
# 对应测试文件路径: test/dialect/test_dma_dialect.py
def test_dma_fill_accepts_symbol_int_scalar_operand() -> None:
    target = _TestOp(result_types=[_make_memory_type()]).results[0]
    value = _make_symbol_operands(["N"])[0]

    DmaFillOp(target, value).verify()


# TC-DMA-026
# 创建者: 小李飞刀
# 最后一次更改: 小李飞刀
# 最近一次运行测试时间: 2026-04-02 15:27:34 +0800
# 最近一次运行成功时间: 2026-04-02 15:27:34 +0800
# 功能说明: 验证 dma.fill 会拒绝非 i32 target memory 与未允许的 scalar family。
# 使用示例: pytest -q test/dialect/test_dma_dialect.py -k test_dma_fill_rejects_non_i32_target_or_unsupported_scalar
# 对应功能实现文件路径: kernel_gen/dialect/dma.py
# 对应 spec 文件路径: spec/dialect/dma.md
# 对应测试文件路径: test/dialect/test_dma_dialect.py
def test_dma_fill_rejects_non_i32_target_or_unsupported_scalar() -> None:
    bad_target_type = NnMemoryType(
        ArrayAttr([IntAttr(2), IntAttr(4)]),
        ArrayAttr([IntAttr(4), IntAttr(1)]),
        i1,
        _make_space("global"),
    )
    bad_target = _TestOp(result_types=[bad_target_type]).results[0]
    value = _TestOp(result_types=[i32]).results[0]

    with pytest.raises(VerifyException, match="dma.fill target element_type must be i32"):
        DmaFillOp(bad_target, value).verify()


# 创建者: OpenAI
# 最后一次更改: OpenAI
# 最近一次运行测试时间: 2026-03-22 23:58:00 +0800
# 最近一次运行成功时间: 2026-03-22 23:58:00 +0800
# 测试目的: 补充覆盖 dma.copy 的 stride / element_type mismatch verifier 语义。
# 对应功能实现文件路径: kernel_gen/dialect/dma.py
# 对应 spec 文件路径: spec/dialect/dma.md
# 对应测试文件路径: test/dialect/test_dma_dialect.py
def test_dma_copy_rejects_stride_or_element_type_mismatch() -> None:
    source_type = _make_memory_type()
    source = _TestOp(result_types=[source_type]).results[0]

    stride_mismatch = _make_memory_type(stride=ArrayAttr([IntAttr(8), IntAttr(1)]))
    op = DmaCopyOp(source, _TestOp(result_types=[stride_mismatch]).results[0])
    with pytest.raises(VerifyException, match="dma.copy source/target stride mismatch"):
        op.verify()

    element_type_mismatch = NnMemoryType(source_type.shape, source_type.stride, i1, source_type.space)
    op = DmaCopyOp(source, _TestOp(result_types=[element_type_mismatch]).results[0])
    with pytest.raises(VerifyException, match="dma.copy source/target element_type mismatch"):
        op.verify()


# 创建者: OpenAI
# 最后一次更改: OpenAI
# 最近一次运行测试时间: 2026-03-22 23:58:00 +0800
# 最近一次运行成功时间: 2026-03-22 23:58:00 +0800
# 测试目的: 补充覆盖 dma.load/store/slice/deslice 的 element_type / space / result 约束。
# 对应功能实现文件路径: kernel_gen/dialect/dma.py
# 对应 spec 文件路径: spec/dialect/dma.md
# 对应测试文件路径: test/dialect/test_dma_dialect.py
def test_dma_transfer_ops_reject_element_space_or_result_mismatch() -> None:
    source_type = _make_memory_type()
    target_type = _make_memory_type(shape=ArrayAttr([IntAttr(8), IntAttr(4)]))
    source = _TestOp(result_types=[source_type]).results[0]
    target = _TestOp(result_types=[target_type]).results[0]
    offsets = _make_symbol_operands([0, 0])
    sizes = _make_symbol_operands([2, 4])
    strides = _make_symbol_operands([1, 1])

    bad_load_type = NnMemoryType(source_type.shape, source_type.stride, i1, source_type.space)
    op = DmaLoadOp(source, offsets, sizes, strides, bad_load_type, _make_space("global"))
    with pytest.raises(VerifyException, match="dma.load element_type mismatch"):
        op.verify()

    store_source_type = NnMemoryType(source_type.shape, source_type.stride, i1, source_type.space)
    store_source = _TestOp(result_types=[store_source_type]).results[0]
    op = DmaStoreOp(store_source, target, offsets, sizes, strides)
    with pytest.raises(VerifyException, match="dma.store element_type mismatch"):
        op.verify()

    bad_slice_type = NnMemoryType(source_type.shape, source_type.stride, i1, source_type.space)
    bad_slice_target = _TestOp(result_types=[bad_slice_type]).results[0]
    op = DmaSliceOp(bad_slice_target, source, offsets, sizes, strides)
    with pytest.raises(VerifyException, match="dma.slice element_type mismatch"):
        op.verify()

    deslice_source = _TestOp(result_types=[source_type]).results[0]
    deslice_target_type = _make_memory_type(shape=ArrayAttr([IntAttr(8), IntAttr(4)]))
    deslice_target = _TestOp(result_types=[deslice_target_type]).results[0]
    bad_deslice_source_type = NnMemoryType(source_type.shape, source_type.stride, i1, source_type.space)
    bad_deslice_source = _TestOp(result_types=[bad_deslice_source_type]).results[0]
    op = DmaDesliceOp(
        bad_deslice_source,
        deslice_target,
        offsets,
        sizes,
        strides,
        deslice_target_type,
    )
    with pytest.raises(VerifyException, match="dma.deslice element_type mismatch"):
        op.verify()

    bad_result_type = _make_memory_type(shape=ArrayAttr([IntAttr(8), IntAttr(4)]), space="shared")
    op = DmaDesliceOp(deslice_source, deslice_target, offsets, sizes, strides, bad_result_type)
    with pytest.raises(VerifyException, match="dma.deslice result must match target type"):
        op.verify()


# 创建者: OpenAI
# 最后一次更改: OpenAI
# 最近一次运行测试时间: 2026-03-22 23:58:00 +0800
# 最近一次运行成功时间: 2026-03-22 23:58:00 +0800
# 测试目的: 补充覆盖 dma.reshape 的 element_type / space mismatch verifier 语义。
# 对应功能实现文件路径: kernel_gen/dialect/dma.py
# 对应 spec 文件路径: spec/dialect/dma.md
# 对应测试文件路径: test/dialect/test_dma_dialect.py
def test_dma_reshape_rejects_element_or_space_mismatch() -> None:
    source_type = _make_memory_type()
    source = _TestOp(result_types=[source_type]).results[0]
    shape = _make_symbol_operands([4, 2])

    bad_element_type = NnMemoryType(
        ArrayAttr([IntAttr(4), IntAttr(2)]),
        ArrayAttr([IntAttr(2), IntAttr(1)]),
        i1,
        source_type.space,
    )
    op = DmaReshapeOp(source, shape, bad_element_type)
    with pytest.raises(VerifyException, match="dma.reshape element_type mismatch"):
        op.verify()

    bad_space_type = _make_memory_type(
        shape=ArrayAttr([IntAttr(4), IntAttr(2)]),
        stride=ArrayAttr([IntAttr(2), IntAttr(1)]),
        space="shared",
    )
    op = DmaReshapeOp(source, shape, bad_space_type)
    with pytest.raises(VerifyException, match="dma.reshape space mismatch"):
        op.verify()


# TC-DMA-027
# 创建者: 小李飞刀
# 最后一次更改: 小李飞刀
# 最近一次运行测试时间: 2026-04-07 17:41:56 +0800
# 最近一次运行成功时间: 2026-04-07 17:41:56 +0800
# 测试目的: 验证 dma.broadcast 接受 memory source 的尾维对齐广播。
# 使用示例: pytest -q test/dialect/test_dma_dialect.py -k test_dma_broadcast_accepts_memory_source
# 对应功能实现文件路径: kernel_gen/dialect/dma.py
# 对应 spec 文件路径: spec/dialect/dma.md
# 对应测试文件路径: test/dialect/test_dma_dialect.py
def test_dma_broadcast_accepts_memory_source() -> None:
    source_type = _make_memory_type(
        shape=ArrayAttr([IntAttr(1), IntAttr(4)]),
        stride=ArrayAttr([IntAttr(4), IntAttr(1)]),
    )
    target_type = _make_memory_type(
        shape=ArrayAttr([IntAttr(2), IntAttr(4)]),
        stride=ArrayAttr([IntAttr(4), IntAttr(1)]),
    )
    source = _TestOp(result_types=[source_type]).results[0]
    target = _TestOp(result_types=[target_type]).results[0]

    DmaBroadcastOp(target, source).verify()


# TC-DMA-028
# 创建者: 小李飞刀
# 最后一次更改: 小李飞刀
# 最近一次运行测试时间: 2026-04-07 17:41:56 +0800
# 最近一次运行成功时间: 2026-04-07 17:41:56 +0800
# 测试目的: 验证 dma.broadcast 接受整数 symbol 标量广播。
# 使用示例: pytest -q test/dialect/test_dma_dialect.py -k test_dma_broadcast_accepts_symbol_int_scalar
# 对应功能实现文件路径: kernel_gen/dialect/dma.py
# 对应 spec 文件路径: spec/dialect/dma.md
# 对应测试文件路径: test/dialect/test_dma_dialect.py
def test_dma_broadcast_accepts_symbol_int_scalar() -> None:
    target = _TestOp(result_types=[_make_memory_type()]).results[0]
    scalar = _make_symbol_operands(["N"])[0]

    DmaBroadcastOp(target, scalar).verify()


# TC-DMA-029
# 创建者: 小李飞刀
# 最后一次更改: 小李飞刀
# 最近一次运行测试时间: 2026-04-07 17:41:56 +0800
# 最近一次运行成功时间: 2026-04-07 17:41:56 +0800
# 测试目的: 验证 dma.broadcast 在静态 shape 不兼容时失败。
# 使用示例: pytest -q test/dialect/test_dma_dialect.py -k test_dma_broadcast_rejects_static_shape_mismatch
# 对应功能实现文件路径: kernel_gen/dialect/dma.py
# 对应 spec 文件路径: spec/dialect/dma.md
# 对应测试文件路径: test/dialect/test_dma_dialect.py
def test_dma_broadcast_rejects_static_shape_mismatch() -> None:
    source_type = _make_memory_type(
        shape=ArrayAttr([IntAttr(2), IntAttr(4)]),
        stride=ArrayAttr([IntAttr(4), IntAttr(1)]),
    )
    target_type = _make_memory_type(
        shape=ArrayAttr([IntAttr(3), IntAttr(4)]),
        stride=ArrayAttr([IntAttr(4), IntAttr(1)]),
    )
    source = _TestOp(result_types=[source_type]).results[0]
    target = _TestOp(result_types=[target_type]).results[0]

    with pytest.raises(VerifyException, match="dma.broadcast shape mismatch"):
        DmaBroadcastOp(target, source).verify()


# TC-DMA-030
# 创建者: 小李飞刀
# 最后一次更改: 小李飞刀
# 最近一次运行测试时间: 2026-04-07 17:41:56 +0800
# 最近一次运行成功时间: 2026-04-07 17:41:56 +0800
# 测试目的: 验证 dma.broadcast 拒绝标量类型与目标元素类型不一致的情况。
# 使用示例: pytest -q test/dialect/test_dma_dialect.py -k test_dma_broadcast_rejects_scalar_type_mismatch
# 对应功能实现文件路径: kernel_gen/dialect/dma.py
# 对应 spec 文件路径: spec/dialect/dma.md
# 对应测试文件路径: test/dialect/test_dma_dialect.py
def test_dma_broadcast_rejects_scalar_type_mismatch() -> None:
    target = _TestOp(result_types=[_make_memory_type()]).results[0]
    scalar = _TestOp(result_types=[f32]).results[0]

    with pytest.raises(VerifyException, match="dma.broadcast scalar type mismatch"):
        DmaBroadcastOp(target, scalar).verify()


# TC-DMA-031
# 创建者: 小李飞刀
# 最后一次更改: 小李飞刀
# 最近一次运行测试时间: 2026-04-07 19:01:20 +0800
# 最近一次运行成功时间: 2026-04-07 19:01:20 +0800
# 测试目的: 验证 dma.transpose 接受合法 perm 并通过校验。
# 使用示例: pytest -q test/dialect/test_dma_dialect.py -k test_dma_transpose_accepts_valid_perm
# 对应功能实现文件路径: kernel_gen/dialect/dma.py
# 对应 spec 文件路径: spec/dialect/dma.md
# 对应测试文件路径: test/dialect/test_dma_dialect.py
def test_dma_transpose_accepts_valid_perm() -> None:
    source_type = _make_memory_type(
        shape=ArrayAttr([IntAttr(2), IntAttr(3)]),
        stride=ArrayAttr([IntAttr(3), IntAttr(1)]),
    )
    target_type = _make_memory_type(
        shape=ArrayAttr([IntAttr(3), IntAttr(2)]),
        stride=ArrayAttr([IntAttr(1), IntAttr(3)]),
    )
    source = _TestOp(result_types=[source_type]).results[0]
    target = _TestOp(result_types=[target_type]).results[0]

    DmaTransposeOp(target, source, perm=[1, 0]).verify()


# TC-DMA-032
# 创建者: 小李飞刀
# 最后一次更改: 小李飞刀
# 最近一次运行测试时间: 2026-04-07 19:01:20 +0800
# 最近一次运行成功时间: 2026-04-07 19:01:20 +0800
# 测试目的: 验证 dma.transpose 在 perm 非排列时失败。
# 使用示例: pytest -q test/dialect/test_dma_dialect.py -k test_dma_transpose_rejects_invalid_perm
# 对应功能实现文件路径: kernel_gen/dialect/dma.py
# 对应 spec 文件路径: spec/dialect/dma.md
# 对应测试文件路径: test/dialect/test_dma_dialect.py
def test_dma_transpose_rejects_invalid_perm() -> None:
    source_type = _make_memory_type(
        shape=ArrayAttr([IntAttr(2), IntAttr(3)]),
        stride=ArrayAttr([IntAttr(3), IntAttr(1)]),
    )
    target_type = _make_memory_type(
        shape=ArrayAttr([IntAttr(3), IntAttr(2)]),
        stride=ArrayAttr([IntAttr(1), IntAttr(3)]),
    )
    source = _TestOp(result_types=[source_type]).results[0]
    target = _TestOp(result_types=[target_type]).results[0]

    with pytest.raises(VerifyException, match="dma.transpose perm"):
        DmaTransposeOp(target, source, perm=[1, 1]).verify()
