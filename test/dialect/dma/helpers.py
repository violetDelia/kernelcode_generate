"""dma dialect tests.


功能说明:
- 覆盖 dma dialect 的 op verifier 与类型复用约束。
- 覆盖 SSA `!symbol.int<#symbol.expr<expr>>` operand 动态布局、parse/print round-trip 与默认连续 stride 约束。
- 覆盖 `dma.fill` 的非 bool 数值 memory 与数值 scalar verifier 闭环。
- 覆盖 `dma.fill` / `dma.view` / `dma.reshape` 的公开 canonicalization 边界。

使用示例:
- pytest -q test/dialect/dma/

当前覆盖率信息:
- `kernel_gen.dialect.dma` package root 公开行为。。

覆盖率命令:
- `pytest --cov=kernel_gen.dialect.dma --cov-report=term-missing test/dialect/dma/`

关联文件:
- 功能实现: kernel_gen/dialect/dma/
- Spec 文档: spec/dialect/dma.md
- 测试文件: test/dialect/dma/
"""

from __future__ import annotations

import sys
from collections.abc import Sequence
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
    IntegerAttr,
    IntegerType,
    StringAttr,
    f16,
    f32,
    f64,
    i1,
    i8,
    i32,
)
from xdsl.dialects.builtin import ModuleOp
from xdsl.dialects.test import Test, TestOp as _TestOp, TestTermOp as _TestTermOp
from xdsl.ir import Attribute, Block, Operation, Region, SSAValue
from xdsl.parser import Parser
from xdsl.printer import Printer
from xdsl.traits import MemoryEffectKind, get_effects
from xdsl.transforms.canonicalize import CanonicalizePass
from xdsl.utils.exceptions import VerifyException

REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from kernel_gen.dialect.dma import (
    Dma,
    DmaAllocOp,
    DmaBroadcastOp,
    DmaTransposeOp,
    DmaFillOp,
    DmaFreeOp,
    DmaAdvanceRingOp,
    DmaCastOp,
    DmaCopyOp,
    DmaCurrentRingOp,
    DmaDesliceOp,
    DmaLoadOp,
    DmaMakeRingOp,
    DmaReinterpretOp,
    DmaRingType,
    DmaReshapeOp,
    DmaSliceOp,
    DmaStoreOp,
    DmaSubviewOp,
    DmaViewOp,
)
from kernel_gen.dialect.nn import Nn, NnMemorySpaceAttr, NnMemoryType
from kernel_gen.dialect.symbol import Symbol, SymbolExprAttr, SymbolIterType, SymbolValueType
from kernel_gen.passes.pass_manager import Pass, PassManager


class _NoopPass(Pass):
    """测试用公开 Pass 子类。"""

    name = "test-noop"

    def apply(self, ctx: Context, module: ModuleOp) -> None:
        """不修改 module。

        功能说明:
        - 通过 `PassManager` 公共入口触发 pass 后 DCE sweep。

        使用示例:
        - PassManager().add_pass(_NoopPass())
        """

        _ = ctx
        _ = module


def _build_context() -> Context:
    """构造加载 builtin/test/symbol/nn/dma 的解析上下文。


    功能说明:
    - 为 parser/printer/verify 测试提供统一 context。

    使用示例:
    - _build_context()

    关联文件:
    - spec: spec/dialect/dma.md
    - test: test/dialect/dma/
    - 功能实现: kernel_gen/dialect/dma/
    """

    ctx = Context()
    ctx.load_dialect(Builtin)
    ctx.load_dialect(Arith)
    ctx.load_dialect(Test)
    ctx.load_dialect(Symbol)
    ctx.load_dialect(Nn)
    ctx.load_dialect(Dma)
    return ctx


def _print_ir(value: Attribute | Operation) -> str:
    """打印 attribute 或 operation/module 为文本。


    功能说明:
    - 为 parse/print round-trip 测试生成稳定文本。

    使用示例:
    - _print_ir(module)

    关联文件:
    - spec: spec/dialect/dma.md
    - test: test/dialect/dma/
    - 功能实现: kernel_gen/dialect/dma/
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


    功能说明:
    - 简化测试中的空间构造。

    使用示例:
    - _make_space("global")

    关联文件:
    - spec: spec/dialect/dma.md
    - test: test/dialect/dma/
    - 功能实现: kernel_gen/dialect/dma/
    """

    return NnMemorySpaceAttr(StringAttr(name))


def _expr_attr(value: int | str) -> SymbolExprAttr:
    """构造公开 SymbolExprAttr。

    功能说明:
    - 为 dma dialect 测试统一生成结构化 memory shape/stride 表达。

    使用示例:
    - _expr_attr("N")

    关联文件:
    - spec: spec/dialect/dma.md
    - test: test/dialect/dma/
    - 功能实现: kernel_gen/dialect/dma/
    """

    return SymbolExprAttr.from_expr(str(value))


def _dim_array(values: list[int | str | SymbolExprAttr]) -> ArrayAttr[Attribute]:
    """构造 memory shape/stride 结构化维度。

    功能说明:
    - 使用公开 `SymbolExprAttr` 表达 memory layout，避免旧 `IntAttr/StringAttr` layout 入口。

    使用示例:
    - _dim_array([2, "N"])

    关联文件:
    - spec: spec/dialect/dma.md
    - test: test/dialect/dma/
    - 功能实现: kernel_gen/dialect/dma/
    """

    return ArrayAttr([value if isinstance(value, SymbolExprAttr) else _expr_attr(value) for value in values])


def _make_memory_type(
    shape: ArrayAttr | None = None,
    stride: ArrayAttr | None = None,
    space: str = "global",
    element_type: Attribute | None = None,
) -> NnMemoryType:
    """构造 nn.memory type。


    功能说明:
    - 提供默认可通过 verifier 的 memory type。
    - 允许显式指定 element_type，默认使用 i32。

    使用示例:
    - _make_memory_type()
    - _make_memory_type(element_type=i8)

    关联文件:
    - spec: spec/dialect/dma.md
    - test: test/dialect/dma/
    - 功能实现: kernel_gen/dialect/dma/
    """

    if shape is None:
        shape = _dim_array([2, 4])
    if stride is None:
        stride = _dim_array([4, 1])
    if element_type is None:
        element_type = i32
    return NnMemoryType(shape, stride, element_type, _make_space(space))


def _raise_memory_verify_rank_mismatch(_: NnMemoryType) -> None:
    """构造 monkeypatch 使用的 memory verifier 失败路径。

    功能说明:
    - 为 `test_dma_nn_memory_type_verifier_passthrough` 提供顶层 helper，避免测试内嵌套函数。

    使用示例:
    - monkeypatch.setattr(NnMemoryType, "verify", _raise_memory_verify_rank_mismatch)

    关联文件:
    - spec: spec/dialect/dma.md
    - test: test/dialect/dma/
    - 功能实现: kernel_gen/dialect/dma/
    """

    raise VerifyException("nn memory shape and stride rank must match")


def _make_symbol_operands(values: list[int | str | None]) -> list[SSAValue]:
    """构造 `!symbol.int<#symbol.expr<expr>>` operand 列表。


    功能说明:
    - `int` 映射为 `!symbol.int<#symbol.expr<n>>`。
    - `str` 映射为对应的符号表达式。
    - `None` 映射为运行期符号 SSA 值。

    使用示例:
    - _make_symbol_operands([0, "N"])

    关联文件:
    - spec: spec/dialect/dma.md
    - test: test/dialect/dma/
    - 功能实现: kernel_gen/dialect/dma/
    """

    operands: list[SSAValue] = []
    for index, value in enumerate(values):
        expr = f"dyn_{index}" if value is None else str(value)
        operands.append(_TestOp(result_types=[SymbolValueType.from_expr(expr)]).results[0])
    return operands


def _make_symbol_value_op(value: int | str) -> _TestOp:
    """构造单个 `!symbol.int<#symbol.expr<expr>>` 测试 op。

    功能说明:
    - 为 canonicalization module 测试提供可插入 module 的常量来源。

    使用示例:
    - c0 = _make_symbol_value_op(0)

    关联文件:
    - spec: spec/dialect/dma.md
    - test: test/dialect/dma/
    - 功能实现: kernel_gen/dialect/dma/
    """

    return _TestOp(result_types=[SymbolValueType.from_expr(str(value))])


def _make_unknown_side_effect_op() -> _TestOp:
    """构造无 MemoryEffect trait 的测试 op。

    功能说明:
    - 为 dead-fill canonicalization 覆盖 unknown side effect 扫描边界。
    - `get_effects(op)` 返回 `None`，表示当前公开 effect 系统无法证明该 op 与 target 无关。

    使用示例:
    - unknown = _make_unknown_side_effect_op()

    关联文件:
    - spec: spec/dialect/dma.md
    - test: test/dialect/dma/
    - 功能实现: kernel_gen/dialect/dma/
    """

    return _TestOp()


def _make_region_side_effect_op() -> _TestOp:
    """构造带 region 的测试 op。

    功能说明:
    - 为 dead-fill canonicalization 覆盖 region op 扫描边界。
    - region 内放置公开 test dialect terminator，保证 module verifier 可通过。

    使用示例:
    - region_op = _make_region_side_effect_op()

    关联文件:
    - spec: spec/dialect/dma.md
    - test: test/dialect/dma/
    - 功能实现: kernel_gen/dialect/dma/
    """

    return _TestOp(regions=[Region(Block([_TestTermOp()]))])


def _canonicalized_module(ops: Sequence[Operation]) -> ModuleOp:
    """运行 xDSL CanonicalizePass 并返回 module。

    功能说明:
    - 使用公开 `CanonicalizePass` 验证 dma op canonicalization 行为。

    使用示例:
    - module = _canonicalized_module([producer, dma_op])

    关联文件:
    - spec: spec/dialect/dma.md
    - test: test/dialect/dma/
    - 功能实现: kernel_gen/dialect/dma/
    """

    ctx = _build_context()
    module = ModuleOp(list(ops))
    module.verify()
    CanonicalizePass().apply(ctx, module)
    module.verify()
    return module


def _count_ops(module: ModuleOp, op_type: type[Operation]) -> int:
    """统计 module 中指定 operation 类型数量。

    功能说明:
    - 通过公开 operation walk 黑盒观察 canonicalization 结果。

    使用示例:
    - fill_count = _count_ops(module, DmaFillOp)

    关联文件:
    - spec: spec/dialect/dma.md
    - test: test/dialect/dma/
    - 功能实现: kernel_gen/dialect/dma/
    """

    return sum(1 for op in module.walk() if isinstance(op, op_type))


def _effect_kinds_by_value(op: Operation) -> set[tuple[MemoryEffectKind, SSAValue | None]]:
    """读取 op 公开 MemoryEffect 的 kind/value 集合。


    功能说明:
    - 使用 xDSL 公开 `get_effects(op)` 验证 dma op 的读写/alloc/free 标注。

    使用示例:
    - effects = _effect_kinds_by_value(op)

    关联文件:
    - spec: spec/dialect/dma.md
    - test: test/dialect/dma/
    - 功能实现: kernel_gen/dialect/dma/
    """

    effects = get_effects(op)
    assert effects is not None
    return {(effect.kind, effect.value) for effect in effects}


# TC-DMA-001
# 功能说明: 验证 dma op 仅接受 nn.memory 作为 memory 类型。
# 使用示例: pytest -q test/dialect/dma/ -k test_dma_requires_nn_memory_type
# 对应功能实现文件路径: kernel_gen/dialect/dma/
# 对应 spec 文件路径: spec/dialect/dma.md
# 对应测试文件路径: test/dialect/dma/


__all__ = [name for name in globals() if not name.startswith("__")]
