"""Analysis tests.

创建者: 金铲铲大作战
最后修改人: 朽木露琪亚

功能说明:
- 覆盖逐元素算术/比较、unary/reduce、broadcast/transpose、matmul 与函数级聚合统计。

使用示例:
- pytest -q test/analysis/test_analysis.py

覆盖率信息:
- 当前覆盖率: `100%` (`kernel_gen/analysis/analysis.py`，2026-03-22 15:24:43 +0800)。
- 达标判定: 已达到 `95%` 覆盖率达标线。
- 当前覆盖对象: `kernel_gen/analysis/analysis.py`。

覆盖率命令:
- coverage run -m pytest -q test/analysis/test_analysis.py && coverage report --include=kernel_gen/analysis/analysis.py -m

关联文件:
- 功能实现: kernel_gen/analysis/analysis.py
- Spec 文档: spec/analysis/analysis_kernel.md
- 测试文件: test/analysis/test_analysis.py
"""

from __future__ import annotations

import sys
from pathlib import Path
from collections.abc import Callable

import sympy as sp
import pytest
from xdsl.dialects import arith, func
from xdsl.dialects.builtin import (
    ArrayAttr,
    FunctionType,
    IntAttr,
    IntegerAttr,
    IntegerType,
    ModuleOp,
    StringAttr,
    f32,
    i1,
    i32,
)
from xdsl.irdl import IRDLOperation, attr_def, irdl_op_definition, operand_def, region_def, result_def
from xdsl.ir import Attribute, Block, Operation, Region, SSAValue

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from kernel_gen.analysis.analysis import (
    AnalysisConfig,
    AnalysisError,
    MemoryItem,
    ComputeItem,
    AnalysisResult,
    AnalysisSummary,
    AnalyzeKernelSummary,
    MemoryRef,
    OpStats,
    Operation,
    ValueTraffic,
    analysis,
    analyze_add,
    analyze_elementwise,
    analyze_broadcast,
    analyze_broadcast_op,
    analyze_eq,
    analyze_kernel,
    analyze_function,
    analyze_matmul,
    analyze_matmul_op,
)
import kernel_gen.analysis.analysis as analysis_module
from kernel_gen.analysis.compute import ComputeKind
from kernel_gen.analysis.memory import MemoryPath
from kernel_gen.passes.analysis.func_cost import AnalyzeFuncCostPass
from kernel_gen.dialect.dma import (
    DmaAllocOp,
    DmaCastOp,
    DmaCopyOp,
    DmaDesliceOp,
    DmaFillOp,
    DmaFreeOp,
    DmaLoadOp,
    DmaReshapeOp,
    DmaSliceOp,
    DmaStoreOp,
    DmaViewOp,
)
from kernel_gen.dialect.nn import (
    NnAddOp,
    NnEqOp,
    NnImg2col1dOp,
    NnImg2col2dOp,
    NnMatmulOp,
    NnMemorySpaceAttr,
    NnMemoryType,
    NnMulOp,
    NnSoftmaxOp,
)
from kernel_gen.dialect.symbol import SymbolValueType
from kernel_gen.symbol_variable.memory import Memory
from kernel_gen.symbol_variable.symbol_dim import SymbolDim
from kernel_gen.symbol_variable.type import NumericType
from kernel_gen.target import registry as target_registry


@irdl_op_definition
class FakeNnAddOp(IRDLOperation):
    """测试用 nn.add op，允许常量 operand。

    创建者: 金铲铲大作战
    最后修改人: 金铲铲大作战

    功能说明:
    - 用于构造 memory + const 的测试输入。

    使用示例:
    - FakeNnAddOp(lhs, const, result_type, space)

    关联文件:
    - spec: spec/analysis/analysis_kernel.md
    - test: test/analysis/test_analysis.py
    - 功能实现: kernel_gen/analysis/analysis.py
    """

    name = "nn.add"

    lhs = operand_def(Attribute)
    rhs = operand_def(Attribute)
    result = result_def(NnMemoryType)
    space = attr_def(NnMemorySpaceAttr)

    def __init__(
        self,
        lhs: SSAValue | Operation,
        rhs: SSAValue | Operation,
        result_type: NnMemoryType,
        space: NnMemorySpaceAttr,
    ) -> None:
        super().__init__(
            operands=[lhs, rhs],
            result_types=[result_type],
            attributes={"space": space},
        )


@irdl_op_definition
class FakeNnExpOp(IRDLOperation):
    """测试用 nn.exp op。

    创建者: 金铲铲大作战
    最后修改人: 金铲铲大作战

    功能说明:
    - 用于构造 nn.exp 的计算/访存测试输入。

    使用示例:
    - FakeNnExpOp(inp, result_type, space)

    关联文件:
    - spec: spec/analysis/analysis_engine.md
    - test: test/analysis/test_analysis.py
    - 功能实现: kernel_gen/analysis/analysis.py
    """

    name = "nn.exp"

    operand = operand_def(Attribute)
    result = result_def(NnMemoryType)
    space = attr_def(NnMemorySpaceAttr)

    def __init__(
        self,
        operand: SSAValue | Operation,
        result_type: NnMemoryType,
        space: NnMemorySpaceAttr,
    ) -> None:
        super().__init__(
            operands=[operand],
            result_types=[result_type],
            attributes={"space": space},
        )


@irdl_op_definition
class FakeNnReduceSumOp(IRDLOperation):
    """测试用 nn.reduce_sum op。

    创建者: 金铲铲大作战
    最后修改人: 金铲铲大作战

    功能说明:
    - 用于构造 nn.reduce_sum 的计算/访存测试输入。

    使用示例:
    - FakeNnReduceSumOp(inp, result_type, space)

    关联文件:
    - spec: spec/analysis/analysis_engine.md
    - test: test/analysis/test_analysis.py
    - 功能实现: kernel_gen/analysis/analysis.py
    """

    name = "nn.reduce_sum"

    operand = operand_def(Attribute)
    result = result_def(NnMemoryType)
    space = attr_def(NnMemorySpaceAttr)

    def __init__(
        self,
        operand: SSAValue | Operation,
        result_type: NnMemoryType,
        space: NnMemorySpaceAttr,
    ) -> None:
        super().__init__(
            operands=[operand],
            result_types=[result_type],
            attributes={"space": space},
        )


@irdl_op_definition
class FakeNnReduceMinOp(IRDLOperation):
    """测试用 nn.reduce_min op。

    创建者: 金铲铲大作战
    最后修改人: 金铲铲大作战

    功能说明:
    - 用于构造 nn.reduce_min 的计算/访存测试输入。

    使用示例:
    - FakeNnReduceMinOp(inp, result_type, space)

    关联文件:
    - spec: spec/analysis/analysis_engine.md
    - test: test/analysis/test_analysis.py
    - 功能实现: kernel_gen/analysis/analysis.py
    """

    name = "nn.reduce_min"

    operand = operand_def(Attribute)
    result = result_def(NnMemoryType)
    space = attr_def(NnMemorySpaceAttr)

    def __init__(
        self,
        operand: SSAValue | Operation,
        result_type: NnMemoryType,
        space: NnMemorySpaceAttr,
    ) -> None:
        super().__init__(
            operands=[operand],
            result_types=[result_type],
            attributes={"space": space},
        )


@irdl_op_definition
class FakeNnReduceMaxOp(IRDLOperation):
    """测试用 nn.reduce_max op。

    创建者: 金铲铲大作战
    最后修改人: 金铲铲大作战

    功能说明:
    - 用于构造 nn.reduce_max 的计算/访存测试输入。

    使用示例:
    - FakeNnReduceMaxOp(inp, result_type, space)

    关联文件:
    - spec: spec/analysis/analysis_engine.md
    - test: test/analysis/test_analysis.py
    - 功能实现: kernel_gen/analysis/analysis.py
    """

    name = "nn.reduce_max"

    operand = operand_def(Attribute)
    result = result_def(NnMemoryType)
    space = attr_def(NnMemorySpaceAttr)

    def __init__(
        self,
        operand: SSAValue | Operation,
        result_type: NnMemoryType,
        space: NnMemorySpaceAttr,
    ) -> None:
        super().__init__(
            operands=[operand],
            result_types=[result_type],
            attributes={"space": space},
        )


@irdl_op_definition
class FakeNnBroadcastOp(IRDLOperation):
    """测试用 nn.broadcast op。

    创建者: 金铲铲大作战
    最后修改人: 金铲铲大作战

    功能说明:
    - 用于构造 nn.broadcast 的访存测试输入。

    使用示例:
    - FakeNnBroadcastOp(inp, result_type, space)

    关联文件:
    - spec: spec/analysis/analysis_engine.md
    - test: test/analysis/test_analysis.py
    - 功能实现: kernel_gen/analysis/analysis.py
    """

    name = "nn.broadcast"

    operand = operand_def(Attribute)
    result = result_def(NnMemoryType)
    space = attr_def(NnMemorySpaceAttr)

    def __init__(
        self,
        operand: SSAValue | Operation,
        result_type: NnMemoryType,
        space: NnMemorySpaceAttr,
    ) -> None:
        super().__init__(
            operands=[operand],
            result_types=[result_type],
            attributes={"space": space},
        )


@irdl_op_definition
class FakeNnTransposeOp(IRDLOperation):
    """测试用 nn.transpose op。

    创建者: 金铲铲大作战
    最后修改人: 金铲铲大作战

    功能说明:
    - 用于构造 nn.transpose 的访存测试输入。

    使用示例:
    - FakeNnTransposeOp(inp, result_type, space)

    关联文件:
    - spec: spec/analysis/analysis_engine.md
    - test: test/analysis/test_analysis.py
    - 功能实现: kernel_gen/analysis/analysis.py
    """

    name = "nn.transpose"

    operand = operand_def(Attribute)
    result = result_def(NnMemoryType)
    space = attr_def(NnMemorySpaceAttr)

    def __init__(
        self,
        operand: SSAValue | Operation,
        result_type: NnMemoryType,
        space: NnMemorySpaceAttr,
    ) -> None:
        super().__init__(
            operands=[operand],
            result_types=[result_type],
            attributes={"space": space},
        )


@irdl_op_definition
class UnknownOp(IRDLOperation):
    """测试用未知 op。

    创建者: 金铲铲大作战
    最后一次更改: 金铲铲大作战

    功能说明:
    - 用于触发 analyze_kernel 的 unknown op warning。

    使用示例:
    - UnknownOp()

    关联文件:
    - spec: spec/analysis/analysis_kernel.md
    - test: test/analysis/test_analysis.py
    - 功能实现: kernel_gen/analysis/analysis.py
    """

    name = "test.unknown"

    def __init__(self) -> None:
        super().__init__(operands=[], result_types=[])


@irdl_op_definition
class FakeRegionOp(IRDLOperation):
    """测试用 region op。

    创建者: 朽木露琪亚
    最后一次更改: 朽木露琪亚

    功能说明:
    - 用于验证 region metadata + trip_count 的分析行为。

    使用示例:
    - FakeRegionOp(region, IntAttr(3))

    关联文件:
    - spec: spec/analysis/analysis_engine.md
    - test: test/analysis/test_analysis.py
    - 功能实现: kernel_gen/analysis/analysis.py
    """

    name = "test.region"
    body = region_def()

    def __init__(self, region: Region, trip_count: Attribute | None = None) -> None:
        attributes: dict[str, Attribute] = {}
        if trip_count is not None:
            attributes["trip_count"] = trip_count
        super().__init__(operands=[], result_types=[], attributes=attributes, regions=[region])


@irdl_op_definition
class FakeKernelScalarAddOp(IRDLOperation):
    """测试用标量 kernel.add op。

    创建者: 朽木露琪亚
    最后一次更改: 朽木露琪亚

    功能说明:
    - 为 A1 的单 op 统一入口测试提供 `kernel.add(i32, i32) -> i32` 形态。

    使用示例:
    - FakeKernelScalarAddOp(i32)

    关联文件:
    - spec: spec/analysis/analysis_engine.md
    - test: test/analysis/test_analysis.py
    - 功能实现: kernel_gen/analysis/analysis.py
    """

    name = "kernel.add"

    lhs = operand_def(Attribute)
    rhs = operand_def(Attribute)
    result = result_def(Attribute)

    def __init__(
        self,
        lhs: SSAValue | Operation,
        rhs: SSAValue | Operation,
        result_type: Attribute,
    ) -> None:
        super().__init__(operands=[lhs, rhs], result_types=[result_type])


@irdl_op_definition
class FakeKernelSelectOp(IRDLOperation):
    """测试用 kernel.select op。

    创建者: 朽木露琪亚
    最后一次更改: 朽木露琪亚

    功能说明:
    - 用于验证 kernel.select 计入标量计算。

    使用示例:
    - FakeKernelSelectOp(cond, lhs, rhs, i32)

    关联文件:
    - spec: spec/analysis/analysis_engine.md
    - test: test/analysis/test_analysis.py
    - 功能实现: kernel_gen/analysis/compute/kernel.py
    """

    name = "kernel.select"

    cond = operand_def(Attribute)
    lhs = operand_def(Attribute)
    rhs = operand_def(Attribute)
    result = result_def(Attribute)

    def __init__(
        self,
        cond: SSAValue | Operation,
        lhs: SSAValue | Operation,
        rhs: SSAValue | Operation,
        result_type: Attribute,
    ) -> None:
        super().__init__(operands=[cond, lhs, rhs], result_types=[result_type])


@irdl_op_definition
class FakeKernelCastOp(IRDLOperation):
    """测试用 kernel.cast op。

    创建者: 朽木露琪亚
    最后一次更改: 朽木露琪亚

    功能说明:
    - 用于验证 kernel.cast 计入标量计算。

    使用示例:
    - FakeKernelCastOp(value, i32)

    关联文件:
    - spec: spec/analysis/analysis_engine.md
    - test: test/analysis/test_analysis.py
    - 功能实现: kernel_gen/analysis/compute/kernel.py
    """

    name = "kernel.cast"

    value = operand_def(Attribute)
    result = result_def(Attribute)

    def __init__(self, value: SSAValue | Operation, result_type: Attribute) -> None:
        super().__init__(operands=[value], result_types=[result_type])


@irdl_op_definition
class FakeSymbolAddOp(IRDLOperation):
    """测试用 symbol.add op。

    创建者: 朽木露琪亚
    最后一次更改: 朽木露琪亚

    功能说明:
    - 用于验证 symbol.* 默认计入标量计算。

    使用示例:
    - FakeSymbolAddOp(lhs, rhs, symbol_type)

    关联文件:
    - spec: spec/analysis/analysis_engine.md
    - test: test/analysis/test_analysis.py
    - 功能实现: kernel_gen/analysis/compute/symbol.py
    """

    name = "symbol.add"

    lhs = operand_def(Attribute)
    rhs = operand_def(Attribute)
    result = result_def(SymbolValueType)

    def __init__(
        self,
        lhs: SSAValue | Operation,
        rhs: SSAValue | Operation,
        result_type: SymbolValueType,
    ) -> None:
        super().__init__(operands=[lhs, rhs], result_types=[result_type])


@irdl_op_definition
class FakeSymbolToIntOp(IRDLOperation):
    """测试用 symbol.to_int op。

    创建者: 朽木露琪亚
    最后一次更改: 朽木露琪亚

    功能说明:
    - 用于验证 symbol.to_int 仅统计访存。

    使用示例:
    - FakeSymbolToIntOp(value, i32)

    关联文件:
    - spec: spec/analysis/analysis_engine.md
    - test: test/analysis/test_analysis.py
    - 功能实现: kernel_gen/analysis/compute/symbol.py
    """

    name = "symbol.to_int"

    value = operand_def(Attribute)
    result = result_def(Attribute)

    def __init__(self, value: SSAValue | Operation, result_type: Attribute) -> None:
        super().__init__(operands=[value], result_types=[result_type])


@irdl_op_definition
class FakeSymbolToFloatOp(IRDLOperation):
    """测试用 symbol.to_float op。

    创建者: 朽木露琪亚
    最后一次更改: 朽木露琪亚

    功能说明:
    - 用于验证 symbol.to_float 仅统计访存。

    使用示例:
    - FakeSymbolToFloatOp(value, f32)

    关联文件:
    - spec: spec/analysis/analysis_engine.md
    - test: test/analysis/test_analysis.py
    - 功能实现: kernel_gen/analysis/compute/symbol.py
    """

    name = "symbol.to_float"

    value = operand_def(Attribute)
    result = result_def(Attribute)

    def __init__(self, value: SSAValue | Operation, result_type: Attribute) -> None:
        super().__init__(operands=[value], result_types=[result_type])


@irdl_op_definition
class FakeSymbolGetDimOp(IRDLOperation):
    """测试用 symbol.get_dim op。

    创建者: 朽木露琪亚
    最后一次更改: 朽木露琪亚

    功能说明:
    - 用于验证 symbol.get_dim 作为元信息 op 忽略。

    使用示例:
    - FakeSymbolGetDimOp()

    关联文件:
    - spec: spec/analysis/analysis_engine.md
    - test: test/analysis/test_analysis.py
    - 功能实现: kernel_gen/analysis/analysis.py
    """

    name = "symbol.get_dim"

    def __init__(self) -> None:
        super().__init__(operands=[], result_types=[])


@irdl_op_definition
class FakeSymbolGetStrideOp(IRDLOperation):
    """测试用 symbol.get_stride op。

    创建者: 朽木露琪亚
    最后一次更改: 朽木露琪亚

    功能说明:
    - 用于验证 symbol.get_stride 作为元信息 op 忽略。

    使用示例:
    - FakeSymbolGetStrideOp()

    关联文件:
    - spec: spec/analysis/analysis_engine.md
    - test: test/analysis/test_analysis.py
    - 功能实现: kernel_gen/analysis/analysis.py
    """

    name = "symbol.get_stride"

    def __init__(self) -> None:
        super().__init__(operands=[], result_types=[])


@irdl_op_definition
class FakeArchOp(IRDLOperation):
    """测试用 arch.* op。

    创建者: 朽木露琪亚
    最后一次更改: 朽木露琪亚

    功能说明:
    - 用于验证 arch.* 作为元信息 op 忽略。

    使用示例:
    - FakeArchOp()

    关联文件:
    - spec: spec/analysis/analysis_engine.md
    - test: test/analysis/test_analysis.py
    - 功能实现: kernel_gen/analysis/analysis.py
    """

    name = "arch.device"

    def __init__(self) -> None:
        super().__init__(operands=[], result_types=[])


@irdl_op_definition
class FakeTunerParamOp(IRDLOperation):
    """测试用 tuner.param op。

    创建者: 朽木露琪亚
    最后一次更改: 朽木露琪亚

    功能说明:
    - 用于验证 tuner.param 作为元信息 op 忽略。

    使用示例:
    - FakeTunerParamOp()

    关联文件:
    - spec: spec/analysis/analysis_engine.md
    - test: test/analysis/test_analysis.py
    - 功能实现: kernel_gen/analysis/analysis.py
    """

    name = "tuner.param"

    def __init__(self) -> None:
        super().__init__(operands=[], result_types=[])


def _make_space(space_name: str) -> NnMemorySpaceAttr:
    """构造 nn.memory 空间属性。

    创建者: 金铲铲大作战
    最后一次更改: 金铲铲大作战

    功能说明:
    - 统一从名称创建 NnMemorySpaceAttr。

    使用示例:
    - space = _make_space("global")

    关联文件:
    - spec: spec/analysis/analysis_kernel.md
    - test: test/analysis/test_analysis.py
    - 功能实现: kernel_gen/analysis/analysis.py
    """
    return NnMemorySpaceAttr.from_name(space_name)


def _make_memory_type(
    shape: list[Attribute],
    element_type: Attribute,
    space_name: str,
    stride: list[Attribute] | None = None,
) -> NnMemoryType:
    """构造 nn.memory type。

    创建者: 金铲铲大作战
    最后一次更改: 金铲铲大作战

    功能说明:
    - 以 shape/stride/element_type/space 生成 NnMemoryType。

    使用示例:
    - mem_type = _make_memory_type([IntAttr(2), IntAttr(4)], f32, "global")

    关联文件:
    - spec: spec/analysis/analysis_kernel.md
    - test: test/analysis/test_analysis.py
    - 功能实现: kernel_gen/analysis/analysis.py
    """
    if stride is None:
        stride = [IntAttr(1) for _ in shape]
    return NnMemoryType(
        ArrayAttr(shape),
        ArrayAttr(stride),
        element_type,
        _make_space(space_name),
    )


def _build_module(
    arg_types: list[Attribute],
    result_type: Attribute,
    op_builder: Callable[[Block], tuple[list[Operation], SSAValue]],
) -> tuple[ModuleOp, func.FuncOp, Block]:
    """构造包含单个 func 的 module。

    创建者: 金铲铲大作战
    最后一次更改: 金铲铲大作战

    功能说明:
    - 根据 op_builder 生成 ops，并追加 func.return。

    使用示例:
    - module, func_op, block = _build_module([lhs_type], result_type, builder)

    关联文件:
    - spec: spec/analysis/analysis_kernel.md
    - test: test/analysis/test_analysis.py
    - 功能实现: kernel_gen/analysis/analysis.py
    """
    block = Block(arg_types=arg_types)
    ops, return_value = op_builder(block)
    if not ops:
        raise ValueError("op_builder must return at least one operation")
    for op in ops:
        block.add_op(op)
    block.add_op(func.ReturnOp(return_value))
    func_type = FunctionType.from_lists(arg_types, [result_type])
    func_op = func.FuncOp("main", func_type, Region(block))
    module = ModuleOp([func_op])
    return module, func_op, block


def _assert_expr_equal(actual: sp.Basic, expected: sp.Basic) -> None:
    """断言 sympy 表达式等价。

    创建者: 金铲铲大作战
    最后一次更改: 金铲铲大作战

    功能说明:
    - 使用 sympy.simplify 校验表达式差值为 0。

    使用示例:
    - _assert_expr_equal(summary.total_compute, expected)

    关联文件:
    - spec: spec/analysis/analysis_kernel.md
    - test: test/analysis/test_analysis.py
    - 功能实现: kernel_gen/analysis/analysis.py
    """
    assert sp.simplify(actual - expected) == 0


def _value_traffic_map(summary: AnalyzeKernelSummary) -> dict[str, ValueTraffic]:
    """将 value_traffic 列表转为 dict。

    创建者: 金铲铲大作战
    最后一次更改: 金铲铲大作战

    功能说明:
    - 以 value_key 为 key 构造映射，方便断言。

    使用示例:
    - traffic = _value_traffic_map(summary)

    关联文件:
    - spec: spec/analysis/analysis_kernel.md
    - test: test/analysis/test_analysis.py
    - 功能实现: kernel_gen/analysis/analysis.py
    """
    return {item.value_key: item for item in summary.value_traffic}


def _build_mixed_analysis_module(
    *,
    include_signature_hints: bool,
) -> tuple[ModuleOp, func.FuncOp]:
    """构造 A4 混合函数测试样例。

    创建者: jcc你莫辜负
    最后一次更改: jcc你莫辜负

    功能说明:
    - 生成同时包含 elementwise、tensor+const、compare(i1)、dma.load/copy/store 的 `func.func`。
    - 可切换是否保留函数级签名提示，用于验证统一入口只依赖 body 内真实 op 链。

    使用示例:
    - module, func_op = _build_mixed_analysis_module(include_signature_hints=False)

    关联文件:
    - spec: spec/analysis/analysis_engine.md
    - test: test/analysis/test_analysis.py
    - 功能实现: kernel_gen/analysis/analysis.py
    """

    mem_type = _make_memory_type([IntAttr(2), IntAttr(2)], f32, "global")
    local_type = _make_memory_type([IntAttr(2), IntAttr(2)], f32, "local")
    pred_type = _make_memory_type([IntAttr(2), IntAttr(2)], i1, "global")
    space = _make_space("global")
    symbol_types = [
        SymbolValueType.from_expr("0"),
        SymbolValueType.from_expr("0"),
        SymbolValueType.from_expr("2"),
        SymbolValueType.from_expr("2"),
        SymbolValueType.from_expr("1"),
        SymbolValueType.from_expr("1"),
    ]
    arg_types = [mem_type, mem_type, local_type, *symbol_types]
    block = Block(arg_types=arg_types)

    offsets = [block.args[3], block.args[4]]
    sizes = [block.args[5], block.args[6]]
    strides = [block.args[7], block.args[8]]
    const_op = arith.ConstantOp(IntegerAttr(1, i32))
    add_op = NnAddOp(block.args[0], block.args[1], mem_type, space)
    add_const_op = FakeNnAddOp(add_op.result, const_op.result, mem_type, space)
    eq_op = NnEqOp(add_const_op.result, block.args[1], pred_type, space)
    load_op = DmaLoadOp(block.args[0], offsets, sizes, strides, mem_type, space)
    copy_op = DmaCopyOp(block.args[0], block.args[2])
    store_op = DmaStoreOp(load_op.result, block.args[2], offsets, sizes, strides)

    for op in (const_op, add_op, add_const_op, eq_op, load_op, copy_op, store_op):
        block.add_op(op)
    block.add_op(func.ReturnOp(add_const_op.result))

    if include_signature_hints:
        func_type = FunctionType.from_lists(arg_types, [mem_type])
    else:
        func_type = FunctionType.from_lists([], [])
    func_op = func.FuncOp("main", func_type, Region(block))
    module = ModuleOp([func_op])
    return module, func_op


# AN-001
# 创建者: 金铲铲大作战
# 最后一次更改: 小李飞刀
# 最近一次运行测试时间: 2026-03-22 15:24:43 +0800
# 最近一次运行成功时间: 2026-03-22 15:24:43 +0800
# 测试目的: 验证 add 的计算量与搬运量统计。
# 使用示例: pytest -q test/analysis/test_analysis.py -k test_analysis_add_counts
# 对应功能实现文件路径: kernel_gen/analysis/analysis.py
# 对应 spec 文件路径: spec/analysis/analysis_kernel.md
# 对应测试文件路径: test/analysis/test_analysis.py
def test_analysis_add_counts() -> None:
    lhs = Memory(["A", "B"], NumericType.Float32)
    rhs = Memory(["A", "B"], NumericType.Float32)
    out = Memory(["A", "B"], NumericType.Float32)
    stats = analyze_add(lhs, rhs, out)
    a, b, s = sp.Symbol("A"), sp.Symbol("B"), sp.Symbol("S")
    assert stats.compute == a * b
    assert stats.read_bytes == 2 * a * b * s
    assert stats.write_bytes == a * b * s

    sized = analyze_add(lhs, rhs, out, dtype_size=4)
    assert sized.read_bytes == 2 * a * b * sp.Integer(4)
    assert sized.write_bytes == a * b * sp.Integer(4)


# AN-002
# 创建者: 金铲铲大作战
# 最后一次更改: 小李飞刀
# 最近一次运行测试时间: 2026-03-22 15:24:43 +0800
# 最近一次运行成功时间: 2026-03-22 15:24:43 +0800
# 测试目的: 验证 eq 的计算量与搬运量统计。
# 使用示例: pytest -q test/analysis/test_analysis.py -k test_analysis_eq_counts
# 对应功能实现文件路径: kernel_gen/analysis/analysis.py
# 对应 spec 文件路径: spec/analysis/analysis_kernel.md
# 对应测试文件路径: test/analysis/test_analysis.py
def test_analysis_eq_counts() -> None:
    lhs = Memory(["A", "B"], NumericType.Float32)
    rhs = Memory(["A", "B"], NumericType.Float32)
    out = Memory(["A", "B"], NumericType.Int32)
    stats = analyze_eq(lhs, rhs, out)
    a, b, s, p = sp.Symbol("A"), sp.Symbol("B"), sp.Symbol("S"), sp.Symbol("P")
    assert stats.compute == a * b
    assert stats.read_bytes == 2 * a * b * s
    assert stats.write_bytes == a * b * p


# AN-003
# 创建者: 金铲铲大作战
# 最后一次更改: 小李飞刀
# 最近一次运行测试时间: 2026-03-22 15:24:43 +0800
# 最近一次运行成功时间: 2026-03-22 15:24:43 +0800
# 测试目的: 验证 broadcast 的读写量统计。
# 使用示例: pytest -q test/analysis/test_analysis.py -k test_analysis_broadcast_counts
# 对应功能实现文件路径: kernel_gen/analysis/analysis.py
# 对应 spec 文件路径: spec/analysis/analysis_kernel.md
# 对应测试文件路径: test/analysis/test_analysis.py
def test_analysis_broadcast_counts() -> None:
    inp = Memory([1, "N"], NumericType.Float32)
    out = Memory(["M", "N"], NumericType.Float32)
    stats = analyze_broadcast_op(inp, out)
    m, n, s = sp.Symbol("M"), sp.Symbol("N"), sp.Symbol("S")
    assert stats.compute == 0
    assert stats.read_bytes == n * s
    assert stats.write_bytes == m * n * s


# AN-004
# 创建者: 金铲铲大作战
# 最后一次更改: 小李飞刀
# 最近一次运行测试时间: 2026-03-22 15:24:43 +0800
# 最近一次运行成功时间: 2026-03-22 15:24:43 +0800
# 测试目的: 验证 matmul 的计算量与读写量统计。
# 使用示例: pytest -q test/analysis/test_analysis.py -k test_analysis_matmul_counts
# 对应功能实现文件路径: kernel_gen/analysis/analysis.py
# 对应 spec 文件路径: spec/analysis/analysis_kernel.md
# 对应测试文件路径: test/analysis/test_analysis.py
def test_analysis_matmul_counts() -> None:
    lhs = Memory(["M", "K"], NumericType.Float32)
    rhs = Memory(["K", "N"], NumericType.Float32)
    out = Memory(["M", "N"], NumericType.Float32)
    stats = analyze_matmul_op(lhs, rhs, out)
    m, n, k, s = sp.Symbol("M"), sp.Symbol("N"), sp.Symbol("K"), sp.Symbol("S")
    assert stats.compute == 2 * m * n * k
    expected_read = (m * k + k * n) * s
    assert sp.simplify(stats.read_bytes - expected_read) == 0
    assert stats.write_bytes == m * n * s


# AN-005
# 创建者: 金铲铲大作战
# 最后一次更改: 小李飞刀
# 最近一次运行测试时间: 2026-03-22 15:24:43 +0800
# 最近一次运行成功时间: 2026-03-22 15:24:43 +0800
# 测试目的: 验证函数级聚合统计会计入中间物化。
# 使用示例: pytest -q test/analysis/test_analysis.py -k test_analysis_materialized_intermediate
# 对应功能实现文件路径: kernel_gen/analysis/analysis.py
# 对应 spec 文件路径: spec/analysis/analysis_kernel.md
# 对应测试文件路径: test/analysis/test_analysis.py
def test_analysis_materialized_intermediate() -> None:
    a1 = Memory(["A", "B"], NumericType.Float32)
    a2 = Memory(["A", "B"], NumericType.Float32)
    a3 = Memory(["A", "B"], NumericType.Float32)
    c = Memory(["A", "B"], NumericType.Float32)
    d = Memory(["A", "B"], NumericType.Float32)

    ops = [
        Operation("add", [MemoryRef("A1", a1), MemoryRef("A2", a2)], MemoryRef("C", c)),
        Operation("mul", [MemoryRef("C", c), MemoryRef("A3", a3)], MemoryRef("D", d)),
    ]
    summary = analyze_function(ops)
    assert isinstance(summary, AnalysisSummary)

    a, b, s = sp.Symbol("A"), sp.Symbol("B"), sp.Symbol("S")
    assert summary.total.compute == 2 * a * b
    assert summary.total.read_bytes == 4 * a * b * s
    assert summary.total.write_bytes == 2 * a * b * s


# AN-006
# 创建者: 金铲铲大作战
# 最后一次更改: 小李飞刀
# 最近一次运行测试时间: 2026-03-22 15:24:43 +0800
# 最近一次运行成功时间: 2026-03-22 15:24:43 +0800
# 测试目的: 验证函数级聚合在融合场景不计入中间物化。
# 使用示例: pytest -q test/analysis/test_analysis.py -k test_analysis_fused_intermediate
# 对应功能实现文件路径: kernel_gen/analysis/analysis.py
# 对应 spec 文件路径: spec/analysis/analysis_kernel.md
# 对应测试文件路径: test/analysis/test_analysis.py
def test_analysis_fused_intermediate() -> None:
    a1 = Memory(["A", "B"], NumericType.Float32)
    a2 = Memory(["A", "B"], NumericType.Float32)
    a3 = Memory(["A", "B"], NumericType.Float32)
    c = Memory(["A", "B"], NumericType.Float32)
    d = Memory(["A", "B"], NumericType.Float32)

    ops = [
        Operation(
            "add",
            [MemoryRef("A1", a1), MemoryRef("A2", a2)],
            MemoryRef("C", c),
            materialize=False,
        ),
        Operation("mul", [MemoryRef("C", c), MemoryRef("A3", a3)], MemoryRef("D", d)),
    ]
    summary = analyze_function(ops)

    a, b, s = sp.Symbol("A"), sp.Symbol("B"), sp.Symbol("S")
    assert summary.total.compute == 2 * a * b
    assert summary.total.read_bytes == 3 * a * b * s
    assert summary.total.write_bytes == a * b * s


# AN-007
# 创建者: 金铲铲大作战
# 最后一次更改: 小李飞刀
# 最近一次运行测试时间: 2026-03-22 15:24:43 +0800
# 最近一次运行成功时间: 2026-03-22 15:24:43 +0800
# 测试目的: 验证 read_mask 长度不匹配时报 AnalysisError。
# 使用示例: pytest -q test/analysis/test_analysis.py -k test_analysis_read_mask_length_mismatch
# 对应功能实现文件路径: kernel_gen/analysis/analysis.py
# 对应 spec 文件路径: spec/analysis/analysis_kernel.md
# 对应测试文件路径: test/analysis/test_analysis.py
def test_analysis_read_mask_length_mismatch() -> None:
    lhs = Memory(["A", "B"], NumericType.Float32)
    rhs = Memory(["A", "B"], NumericType.Float32)
    out = Memory(["A", "B"], NumericType.Float32)
    with pytest.raises(AnalysisError, match="read_mask length mismatch"):
        analyze_elementwise(lhs, rhs, out, read_mask=[True])


# AN-008
# 创建者: 金铲铲大作战
# 最后一次更改: 小李飞刀
# 最近一次运行测试时间: 2026-03-22 15:24:43 +0800
# 最近一次运行成功时间: 2026-03-22 15:24:43 +0800
# 测试目的: 验证 analyze_function 输入数量不匹配时报 AnalysisError。
# 使用示例: pytest -q test/analysis/test_analysis.py -k test_analysis_function_inputs_mismatch
# 对应功能实现文件路径: kernel_gen/analysis/analysis.py
# 对应 spec 文件路径: spec/analysis/analysis_kernel.md
# 对应测试文件路径: test/analysis/test_analysis.py
def test_analysis_function_inputs_mismatch() -> None:
    a1 = Memory(["A", "B"], NumericType.Float32)
    out = Memory(["A", "B"], NumericType.Float32)
    ops = [Operation("add", [MemoryRef("A1", a1)], MemoryRef("C", out))]
    with pytest.raises(AnalysisError, match="Operation inputs length mismatch"):
        analyze_function(ops)


# AN-009
# 创建者: 小李飞刀
# 最后一次更改: 小李飞刀
# 最近一次运行测试时间: 2026-03-22 15:24:43 +0800
# 最近一次运行成功时间: 2026-03-22 15:24:43 +0800
# 测试目的: 验证 OpStats 与非 OpStats 相加返回 NotImplemented。
# 使用示例: pytest -q test/analysis/test_analysis.py -k test_opstats_add_returns_notimplemented
# 对应功能实现文件路径: kernel_gen/analysis/analysis.py
# 对应 spec 文件路径: spec/analysis/analysis_kernel.md
# 对应测试文件路径: test/analysis/test_analysis.py
def test_opstats_add_returns_notimplemented() -> None:
    stats = OpStats(sp.Integer(1), sp.Integer(2), sp.Integer(3))
    assert stats.__add__("invalid") is NotImplemented


# AN-010
# 创建者: 小李飞刀
# 最后一次更改: 小李飞刀
# 最近一次运行测试时间: 2026-03-22 15:24:43 +0800
# 最近一次运行成功时间: 2026-03-22 15:24:43 +0800
# 测试目的: 验证 _to_symbol 遇到非法类型抛出 AnalysisError。
# 使用示例: pytest -q test/analysis/test_analysis.py -k test_to_symbol_rejects_invalid_type
# 对应功能实现文件路径: kernel_gen/analysis/analysis.py
# 对应 spec 文件路径: spec/analysis/analysis_kernel.md
# 对应测试文件路径: test/analysis/test_analysis.py
def test_to_symbol_rejects_invalid_type() -> None:
    with pytest.raises(AnalysisError, match="Unsupported dimension"):
        analysis_module._to_symbol(1.5)


# AN-011
# 创建者: 小李飞刀
# 最后一次更改: 小李飞刀
# 最近一次运行测试时间: 2026-03-22 15:24:43 +0800
# 最近一次运行成功时间: 2026-03-22 15:24:43 +0800
# 测试目的: 验证逐元素输出 shape 不一致时抛 AnalysisError。
# 使用示例: pytest -q test/analysis/test_analysis.py -k test_analysis_elementwise_output_shape_mismatch
# 对应功能实现文件路径: kernel_gen/analysis/analysis.py
# 对应 spec 文件路径: spec/analysis/analysis_kernel.md
# 对应测试文件路径: test/analysis/test_analysis.py
def test_analysis_elementwise_output_shape_mismatch() -> None:
    lhs = Memory(["A", "B"], NumericType.Float32)
    rhs = Memory(["A", "B"], NumericType.Float32)
    out = Memory(["A", "C"], NumericType.Float32)
    with pytest.raises(AnalysisError, match="Elementwise output shape mismatch"):
        analyze_add(lhs, rhs, out)


# AN-012
# 创建者: 小李飞刀
# 最后一次更改: 小李飞刀
# 最近一次运行测试时间: 2026-03-22 15:24:43 +0800
# 最近一次运行成功时间: 2026-03-22 15:24:43 +0800
# 测试目的: 验证 broadcast 形状不合法时抛 AnalysisError。
# 使用示例: pytest -q test/analysis/test_analysis.py -k test_analysis_broadcast_shape_mismatch
# 对应功能实现文件路径: kernel_gen/analysis/analysis.py
# 对应 spec 文件路径: spec/analysis/analysis_kernel.md
# 对应测试文件路径: test/analysis/test_analysis.py
def test_analysis_broadcast_shape_mismatch() -> None:
    inp = Memory(["A", "B"], NumericType.Float32)
    out_rank = Memory(["B"], NumericType.Float32)
    with pytest.raises(AnalysisError, match="Broadcast output rank must be"):
        analyze_broadcast_op(inp, out_rank)

    out_dim = Memory(["A", "C"], NumericType.Float32)
    with pytest.raises(AnalysisError, match="Broadcast dimension mismatch"):
        analyze_broadcast_op(inp, out_dim)


# AN-013
# 创建者: 小李飞刀
# 最后一次更改: 小李飞刀
# 最近一次运行测试时间: 2026-03-22 15:24:43 +0800
# 最近一次运行成功时间: 2026-03-22 15:24:43 +0800
# 测试目的: 验证 broadcast read_mask 长度不正确时抛 AnalysisError。
# 使用示例: pytest -q test/analysis/test_analysis.py -k test_analysis_broadcast_read_mask_length_mismatch
# 对应功能实现文件路径: kernel_gen/analysis/analysis.py
# 对应 spec 文件路径: spec/analysis/analysis_kernel.md
# 对应测试文件路径: test/analysis/test_analysis.py
def test_analysis_broadcast_read_mask_length_mismatch() -> None:
    inp = Memory([1, "N"], NumericType.Float32)
    out = Memory(["M", "N"], NumericType.Float32)
    with pytest.raises(AnalysisError, match="read_mask length mismatch"):
        analyze_broadcast(inp, out, read_mask=[True, False])


# AN-014
# 创建者: 小李飞刀
# 最后一次更改: 小李飞刀
# 最近一次运行测试时间: 2026-03-22 15:24:43 +0800
# 最近一次运行成功时间: 2026-03-22 15:24:43 +0800
# 测试目的: 验证 matmul 形状不合法时抛 AnalysisError。
# 使用示例: pytest -q test/analysis/test_analysis.py -k test_analysis_matmul_shape_mismatch
# 对应功能实现文件路径: kernel_gen/analysis/analysis.py
# 对应 spec 文件路径: spec/analysis/analysis_kernel.md
# 对应测试文件路径: test/analysis/test_analysis.py
def test_analysis_matmul_shape_mismatch() -> None:
    lhs = Memory(["M"], NumericType.Float32)
    rhs = Memory(["M", "N"], NumericType.Float32)
    out = Memory(["M", "N"], NumericType.Float32)
    with pytest.raises(AnalysisError, match="Matmul requires rank-2 tensors"):
        analyze_matmul_op(lhs, rhs, out)

    lhs = Memory(["M", "K"], NumericType.Float32)
    rhs = Memory(["Q", "N"], NumericType.Float32)
    out = Memory(["M", "N"], NumericType.Float32)
    with pytest.raises(AnalysisError, match="Matmul inner dimension mismatch"):
        analyze_matmul_op(lhs, rhs, out)

    lhs = Memory(["M", "K"], NumericType.Float32)
    rhs = Memory(["K", "N"], NumericType.Float32)
    out = Memory(["M", "Q"], NumericType.Float32)
    with pytest.raises(AnalysisError, match="Matmul output shape mismatch"):
        analyze_matmul_op(lhs, rhs, out)


# AN-015
# 创建者: 小李飞刀
# 最后一次更改: 小李飞刀
# 最近一次运行测试时间: 2026-03-22 15:24:43 +0800
# 最近一次运行成功时间: 2026-03-22 15:24:43 +0800
# 测试目的: 验证 matmul read_mask 长度不正确时抛 AnalysisError。
# 使用示例: pytest -q test/analysis/test_analysis.py -k test_analysis_matmul_read_mask_length_mismatch
# 对应功能实现文件路径: kernel_gen/analysis/analysis.py
# 对应 spec 文件路径: spec/analysis/analysis_kernel.md
# 对应测试文件路径: test/analysis/test_analysis.py
def test_analysis_matmul_read_mask_length_mismatch() -> None:
    lhs = Memory(["M", "K"], NumericType.Float32)
    rhs = Memory(["K", "N"], NumericType.Float32)
    out = Memory(["M", "N"], NumericType.Float32)
    with pytest.raises(AnalysisError, match="read_mask length mismatch"):
        analyze_matmul(lhs, rhs, out, read_mask=[True])


# AN-016
# 创建者: 小李飞刀
# 最后一次更改: 小李飞刀
# 最近一次运行测试时间: 2026-03-22 15:24:43 +0800
# 最近一次运行成功时间: 2026-03-22 15:24:43 +0800
# 测试目的: 验证 analyze_function 覆盖 compare/broadcast/matmul 分支统计。
# 使用示例: pytest -q test/analysis/test_analysis.py -k test_analysis_function_branches
# 对应功能实现文件路径: kernel_gen/analysis/analysis.py
# 对应 spec 文件路径: spec/analysis/analysis_kernel.md
# 对应测试文件路径: test/analysis/test_analysis.py
def test_analysis_function_branches() -> None:
    eq_lhs = Memory(["A", "B"], NumericType.Float32)
    eq_rhs = Memory(["A", "B"], NumericType.Float32)
    eq_out = Memory(["A", "B"], NumericType.Int32)
    bc_inp = Memory([1, "N"], NumericType.Float32)
    bc_out = Memory(["M", "N"], NumericType.Float32)
    mm_lhs = Memory(["M", "K"], NumericType.Float32)
    mm_rhs = Memory(["K", "N"], NumericType.Float32)
    mm_out = Memory(["M", "N"], NumericType.Float32)

    ops = [
        Operation("eq", [MemoryRef("EQ1", eq_lhs), MemoryRef("EQ2", eq_rhs)], MemoryRef("EQO", eq_out)),
        Operation("broadcast", [MemoryRef("BCI", bc_inp)], MemoryRef("BCO", bc_out)),
        Operation("matmul", [MemoryRef("ML", mm_lhs), MemoryRef("MR", mm_rhs)], MemoryRef("MO", mm_out)),
    ]
    summary = analyze_function(ops, predicate_size=1)
    a, b, m, n, k, s = (
        sp.Symbol("A"),
        sp.Symbol("B"),
        sp.Symbol("M"),
        sp.Symbol("N"),
        sp.Symbol("K"),
        sp.Symbol("S"),
    )
    expected_compute = a * b + sp.Integer(2) * m * n * k
    expected_read = 2 * a * b * s + n * s + (m * k + k * n) * s
    expected_write = a * b * sp.Integer(1) + 2 * m * n * s
    assert sp.simplify(summary.total.compute - expected_compute) == 0
    assert sp.simplify(summary.total.read_bytes - expected_read) == 0
    assert sp.simplify(summary.total.write_bytes - expected_write) == 0


# AN-017
# 创建者: 小李飞刀
# 最后一次更改: 小李飞刀
# 最近一次运行测试时间: 2026-03-22 15:24:43 +0800
# 最近一次运行成功时间: 2026-03-22 15:24:43 +0800
# 测试目的: 验证 analyze_function 遇到不支持的 op 会报错。
# 使用示例: pytest -q test/analysis/test_analysis.py -k test_analysis_function_unsupported_op
# 对应功能实现文件路径: kernel_gen/analysis/analysis.py
# 对应 spec 文件路径: spec/analysis/analysis_kernel.md
# 对应测试文件路径: test/analysis/test_analysis.py
def test_analysis_function_unsupported_op() -> None:
    inp = Memory(["A", "B"], NumericType.Float32)
    ops = [Operation("noop", [MemoryRef("A1", inp)], MemoryRef("B1", inp))]
    with pytest.raises(AnalysisError, match="Unsupported op for analysis"):
        analyze_function(ops)


# AN-018
# 创建者: 朽木露琪亚
# 最后一次更改: 朽木露琪亚
# 最近一次运行测试时间: 2026-04-03 00:00:00 +0800
# 最近一次运行成功时间: 2026-04-03 00:00:00 +0800
# 测试目的: 验证单 op 统一入口返回新结果结构，且默认不写 analysis.* 属性。
# 使用示例: pytest -q test/analysis/test_analysis.py -k test_analysis_entry_returns_new_result_for_scalar_kernel_add
# 对应功能实现文件路径: kernel_gen/analysis/analysis.py
# 对应 spec 文件路径: spec/analysis/analysis_engine.md
# 对应测试文件路径: test/analysis/test_analysis.py
def test_analysis_entry_returns_new_result_for_scalar_kernel_add() -> None:
    lhs = arith.ConstantOp(IntegerAttr(1, i32))
    rhs = arith.ConstantOp(IntegerAttr(2, i32))
    add_op = FakeKernelScalarAddOp(lhs.result, rhs.result, i32)

    result = analysis(
        add_op,
        AnalysisConfig(
            enable_compute=True,
            enable_memory=False,
            write_op_attrs=False,
            write_func_attrs=False,
        ),
    )

    assert isinstance(result, AnalysisResult)
    assert len(result.compute_items) == 1
    item = result.compute_items[0]
    assert item.kind is ComputeKind.SCALAR
    _assert_expr_equal(item.amount, sp.Integer(1))
    assert item.dtype == "i32"
    assert result.memory_items == ()
    assert result.compute_totals_by_kind == {ComputeKind.SCALAR: sp.Integer(1)}
    assert "analysis.compute" not in add_op.attributes


# AN-019
# 创建者: 朽木露琪亚
# 最后一次更改: 朽木露琪亚
# 最近一次运行测试时间: 2026-04-03 00:00:00 +0800
# 最近一次运行成功时间: 2026-04-03 00:00:00 +0800
# 测试目的: 验证统一入口只有在 write_op_attrs=True 时才写回 op attributes。
# 使用示例: pytest -q test/analysis/test_analysis.py -k test_analysis_entry_write_op_attrs_is_explicit
# 对应功能实现文件路径: kernel_gen/analysis/analysis.py
# 对应 spec 文件路径: spec/analysis/analysis_engine.md
# 对应测试文件路径: test/analysis/test_analysis.py
def test_analysis_entry_write_op_attrs_is_explicit() -> None:
    lhs = arith.ConstantOp(IntegerAttr(1, i32))
    rhs = arith.ConstantOp(IntegerAttr(2, i32))
    add_op = FakeKernelScalarAddOp(lhs.result, rhs.result, i32)

    analysis(
        add_op,
        AnalysisConfig(
            enable_compute=True,
            enable_memory=False,
            write_op_attrs=True,
            write_func_attrs=False,
        ),
    )

    assert add_op.attributes["analysis.compute"].data == "1"
    assert add_op.attributes["analysis.read_bytes"].data == "0"
    assert add_op.attributes["analysis.write_bytes"].data == "0"
    assert add_op.attributes["analysis.compute.kind0"].data == "scalar"
    assert add_op.attributes["analysis.compute.amount0"].data == "1"
    assert add_op.attributes["analysis.compute.dtype0"].data == "i32"


# AN-020
# 创建者: 朽木露琪亚
# 最后一次更改: jcc你莫辜负
# 最近一次运行测试时间: 2026-04-03 00:00:00 +0800
# 最近一次运行成功时间: 2026-04-03 00:00:00 +0800
# 测试目的: 验证 `write_op_attrs` / `write_func_attrs` 仅在显式开启时受控写回。
# 使用示例: pytest -q test/analysis/test_analysis.py -k test_analysis_write_attrs_are_explicit_and_controlled
# 对应功能实现文件路径: kernel_gen/analysis/analysis.py
# 对应 spec 文件路径: spec/analysis/analysis_engine.md
# 对应测试文件路径: test/analysis/test_analysis.py
def test_analysis_write_attrs_are_explicit_and_controlled() -> None:
    mem_type = _make_memory_type([IntAttr(2), IntAttr(3)], f32, "global")
    space = _make_space("global")

    def _build_case() -> tuple[func.FuncOp, NnAddOp]:
        captured: dict[str, NnAddOp] = {}

        def _builder(block: Block) -> tuple[list[Operation], SSAValue]:
            add_op = NnAddOp(block.args[0], block.args[1], mem_type, space)
            captured["add"] = add_op
            return [add_op], add_op.result

        _, func_op, _ = _build_module([mem_type, mem_type], mem_type, _builder)
        return func_op, captured["add"]

    func_default, add_default = _build_case()
    analysis(
        func_default,
        AnalysisConfig(
            enable_compute=True,
            enable_memory=True,
            write_op_attrs=False,
            write_func_attrs=False,
            dtype_size_overrides={"f32": 4},
        ),
    )
    assert "analysis.compute" not in add_default.attributes
    assert "analysis.compute" not in func_default.attributes

    func_op_only, add_op_only = _build_case()
    analysis(
        func_op_only,
        AnalysisConfig(
            enable_compute=True,
            enable_memory=True,
            write_op_attrs=True,
            write_func_attrs=False,
            dtype_size_overrides={"f32": 4},
        ),
    )
    assert add_op_only.attributes["analysis.compute"].data == "6"
    assert "analysis.compute" not in func_op_only.attributes

    func_func_only, add_func_only = _build_case()
    analysis(
        func_func_only,
        AnalysisConfig(
            enable_compute=True,
            enable_memory=True,
            write_op_attrs=False,
            write_func_attrs=True,
            dtype_size_overrides={"f32": 4},
        ),
    )
    assert "analysis.compute" not in add_func_only.attributes
    assert func_func_only.attributes["analysis.compute"].data == "6"
    assert func_func_only.attributes["analysis.read_bytes"].data == "48"
    assert func_func_only.attributes["analysis.write_bytes"].data == "24"

    func_both, add_both = _build_case()
    analysis(
        func_both,
        AnalysisConfig(
            enable_compute=True,
            enable_memory=True,
            write_op_attrs=True,
            write_func_attrs=True,
            dtype_size_overrides={"f32": 4},
        ),
    )
    assert add_both.attributes["analysis.compute"].data == "6"
    assert func_both.attributes["analysis.compute"].data == "6"


# AN-020A
# 创建者: jcc你莫辜负
# 最后一次更改: 朽木露琪亚
# 最近一次运行测试时间: 2026-04-04 00:00:00 +0800
# 最近一次运行成功时间: 2026-04-04 00:00:00 +0800
# 测试目的: 验证 analyze_kernel 只是 AnalysisResult 的 facade，不维护独立公式。
# 使用示例: pytest -q test/analysis/test_analysis.py -k test_analyze_kernel_is_facade_over_analysis_result
# 对应功能实现文件路径: kernel_gen/analysis/analysis.py
# 对应 spec 文件路径: spec/analysis/analysis_kernel.md
# 对应测试文件路径: test/analysis/test_analysis.py
def test_analyze_kernel_is_facade_over_analysis_result() -> None:
    mem_type = _make_memory_type([IntAttr(2), IntAttr(3)], f32, "global")
    space = _make_space("global")

    def _builder(block: Block) -> tuple[list[Operation], SSAValue]:
        add_op = NnAddOp(block.args[0], block.args[1], mem_type, space)
        return [add_op], add_op.result

    _, func_op, _ = _build_module([mem_type, mem_type], mem_type, _builder)
    result = analysis(
        func_op,
        AnalysisConfig(
            enable_compute=True,
            enable_memory=True,
            write_op_attrs=False,
            write_func_attrs=False,
            dtype_size_overrides={"f32": 4},
        ),
    )

    summary = analyze_kernel(func_op, dtype_size_overrides={"f32": 4})
    assert summary.op_costs == result.op_costs
    assert summary.value_traffic == result.value_traffic
    _assert_expr_equal(summary.total_compute, result.total_compute)
    _assert_expr_equal(summary.total_read_bytes, result.total_read_bytes)
    _assert_expr_equal(summary.total_write_bytes, result.total_write_bytes)


# AN-020B
# 创建者: jcc你莫辜负
# 最后一次更改: jcc你莫辜负
# 最近一次运行测试时间: 2026-04-04 00:00:00 +0800
# 最近一次运行成功时间: 2026-04-04 00:00:00 +0800
# 测试目的: 验证 analysis.func 侧默认分析参数只来自 npu_demo target registry 单一来源。
# 使用示例: pytest -q test/analysis/test_analysis.py -k test_analysis_target_registry_is_single_source_for_analysis_defaults
# 对应功能实现文件路径: kernel_gen/analysis/analysis.py
# 对应 spec 文件路径: spec/analysis/analysis_engine.md
# 对应测试文件路径: test/analysis/test_analysis.py
def test_analysis_target_registry_is_single_source_for_analysis_defaults(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    custom_defaults = {
        "path_bandwidth": {"GM->LM": 96},
        "path_latency_ns": {"GM->LM": 11},
        "theoretical_compute": {"scalar": 3, "vector": 9, "tensor": 27, "math": 1},
    }

    def _fake_defaults(target: str) -> dict[str, dict[str, int]]:
        assert target == "npu_demo"
        return {key: dict(value) for key, value in custom_defaults.items()}

    monkeypatch.setattr(analysis_module.target_registry, "get_target_analysis_defaults", _fake_defaults)

    source_type = _make_memory_type([IntAttr(2), IntAttr(4)], f32, "global")
    target_type = _make_memory_type([IntAttr(2), IntAttr(4)], f32, "local")
    _, func_op, _ = _build_module(
        [source_type, target_type],
        target_type,
        lambda block: ([DmaCopyOp(block.args[0], block.args[1])], block.args[1]),
    )
    config = AnalysisConfig(target="npu_demo", enable_compute=False, enable_memory=True)
    result = analysis(func_op, config)

    assert config.path_bandwidth == custom_defaults["path_bandwidth"]
    assert config.path_latency_ns == custom_defaults["path_latency_ns"]
    assert config.theoretical_compute == custom_defaults["theoretical_compute"]
    _assert_expr_equal(result.memory_totals_by_path[MemoryPath.GM_TO_LM], sp.Integer(64))

    read_item, write_item = result.memory_items
    assert read_item.path is MemoryPath.GM_TO_LM
    assert read_item.latency_ns == sp.Integer(11)
    assert read_item.bandwidth == sp.Integer(96)
    _assert_expr_equal(read_item.time_ns or sp.Integer(0), sp.Integer(11) + sp.Rational(32, 96))
    assert write_item.path is MemoryPath.GM_TO_LM
    assert write_item.latency_ns == sp.Integer(11)
    assert write_item.bandwidth == sp.Integer(96)
    _assert_expr_equal(write_item.time_ns or sp.Integer(0), sp.Integer(11) + sp.Rational(32, 96))


# AN-020C
# 创建者: jcc你莫辜负
# 最后一次更改: jcc你莫辜负
# 最近一次运行测试时间: 2026-04-04 00:00:00 +0800
# 最近一次运行成功时间: 2026-04-04 00:00:00 +0800
# 测试目的: 验证 npu_demo target 缺少 analysis 默认参数时显式失败，不允许回退到手写常量。
# 使用示例: pytest -q test/analysis/test_analysis.py -k test_analysis_memory_missing_target_metric_fails_explicitly
# 对应功能实现文件路径: kernel_gen/analysis/analysis.py
# 对应 spec 文件路径: spec/analysis/analysis_engine.md
# 对应测试文件路径: test/analysis/test_analysis.py
def test_analysis_memory_missing_target_metric_fails_explicitly(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    broken_defaults = {
        "path_bandwidth": {"GM->LM": 64},
        "path_latency_ns": {"GM->LM": 20},
    }

    monkeypatch.setattr(
        analysis_module.target_registry,
        "get_target_analysis_defaults",
        lambda target: broken_defaults,
    )

    with pytest.raises(AnalysisError, match="missing analysis metric defaults: theoretical_compute"):
        AnalysisConfig(target="npu_demo")


# AN-020D-C
# 创建者: jcc你莫辜负
# 最后一次更改: jcc你莫辜负
# 最近一次运行测试时间: 2026-04-04 00:00:00 +0800
# 最近一次运行成功时间: 2026-04-04 00:00:00 +0800
# 测试目的: 验证标量 kernel.add 会落到 ComputeKind.SCALAR。
# 使用示例: pytest -q test/analysis/test_analysis.py -k test_analysis_scalar_compute_kind
# 对应功能实现文件路径: kernel_gen/analysis/analysis.py
# 对应 spec 文件路径: spec/analysis/analysis_engine.md
# 对应测试文件路径: test/analysis/test_analysis.py
def test_analysis_scalar_compute_kind() -> None:
    lhs = arith.ConstantOp(IntegerAttr(1, i32))
    rhs = arith.ConstantOp(IntegerAttr(2, i32))
    add_op = FakeKernelScalarAddOp(lhs.result, rhs.result, i32)

    result = analysis(add_op, AnalysisConfig(enable_compute=True, enable_memory=False))

    assert result.compute_items == (ComputeItem(kind=ComputeKind.SCALAR, amount=sp.Integer(1), dtype="i32"),)
    assert result.compute_totals_by_kind == {ComputeKind.SCALAR: sp.Integer(1)}


# AN-020E-C
# 创建者: jcc你莫辜负
# 最后一次更改: jcc你莫辜负
# 最近一次运行测试时间: 2026-04-04 00:00:00 +0800
# 最近一次运行成功时间: 2026-04-04 00:00:00 +0800
# 测试目的: 验证逐元素 nn.add 会落到 ComputeKind.VECTOR。
# 使用示例: pytest -q test/analysis/test_analysis.py -k test_analysis_vector_compute_kind
# 对应功能实现文件路径: kernel_gen/analysis/analysis.py
# 对应 spec 文件路径: spec/analysis/analysis_engine.md
# 对应测试文件路径: test/analysis/test_analysis.py
def test_analysis_vector_compute_kind() -> None:
    mem_type = _make_memory_type([StringAttr("A"), StringAttr("B")], f32, "global")
    space = _make_space("global")
    block = Block(arg_types=[mem_type, mem_type])
    add_op = NnAddOp(block.args[0], block.args[1], mem_type, space)

    result = analysis(
        add_op,
        AnalysisConfig(enable_compute=True, enable_memory=False, dtype_size_overrides={"f32": 4}),
    )

    expected_numel = SymbolDim("A").get_symbol() * SymbolDim("B").get_symbol()
    assert result.compute_items == (
        ComputeItem(kind=ComputeKind.VECTOR, amount=expected_numel, dtype="f32"),
    )
    assert result.compute_totals_by_kind == {ComputeKind.VECTOR: expected_numel}


# AN-020F-C
# 创建者: jcc你莫辜负
# 最后一次更改: jcc你莫辜负
# 最近一次运行测试时间: 2026-04-04 00:00:00 +0800
# 最近一次运行成功时间: 2026-04-04 00:00:00 +0800
# 测试目的: 验证 nn.matmul 会落到 ComputeKind.TENSOR。
# 使用示例: pytest -q test/analysis/test_analysis.py -k test_analysis_tensor_compute_kind
# 对应功能实现文件路径: kernel_gen/analysis/analysis.py
# 对应 spec 文件路径: spec/analysis/analysis_engine.md
# 对应测试文件路径: test/analysis/test_analysis.py
def test_analysis_tensor_compute_kind() -> None:
    lhs_type = _make_memory_type([StringAttr("M"), StringAttr("K")], f32, "global")
    rhs_type = _make_memory_type([StringAttr("K"), StringAttr("N")], f32, "global")
    out_type = _make_memory_type([StringAttr("M"), StringAttr("N")], f32, "global")
    space = _make_space("global")
    block = Block(arg_types=[lhs_type, rhs_type])
    matmul_op = NnMatmulOp(block.args[0], block.args[1], out_type, space)

    result = analysis(
        matmul_op,
        AnalysisConfig(enable_compute=True, enable_memory=False, dtype_size_overrides={"f32": 4}),
    )

    expected = sp.Integer(2) * SymbolDim("M").get_symbol() * SymbolDim("N").get_symbol() * SymbolDim("K").get_symbol()
    assert result.compute_items == (
        ComputeItem(kind=ComputeKind.TENSOR, amount=expected, dtype="f32"),
    )
    assert result.compute_totals_by_kind == {ComputeKind.TENSOR: expected}


# AN-020G-C
# 创建者: jcc你莫辜负
# 最后一次更改: jcc你莫辜负
# 最近一次运行测试时间: 2026-04-04 00:00:00 +0800
# 最近一次运行成功时间: 2026-04-04 00:00:00 +0800
# 测试目的: 验证 tensor + const 保留 ComputeKind.VECTOR，且常量不计 memory traffic。
# 使用示例: pytest -q test/analysis/test_analysis.py -k test_analysis_tensor_plus_const_preserves_compute_kind_without_const_memory_traffic
# 对应功能实现文件路径: kernel_gen/analysis/analysis.py
# 对应 spec 文件路径: spec/analysis/analysis_engine.md
# 对应测试文件路径: test/analysis/test_analysis.py
def test_analysis_tensor_plus_const_preserves_compute_kind_without_const_memory_traffic() -> None:
    mem_type = _make_memory_type([StringAttr("A"), StringAttr("B")], f32, "global")
    space = _make_space("global")
    block = Block(arg_types=[mem_type])
    const_op = arith.ConstantOp(IntegerAttr(1, i32))
    add_op = FakeNnAddOp(block.args[0], const_op.result, mem_type, space)

    result = analysis(
        add_op,
        AnalysisConfig(enable_compute=True, enable_memory=True, dtype_size_overrides={"f32": 4}),
    )

    expected_numel = SymbolDim("A").get_symbol() * SymbolDim("B").get_symbol()
    assert result.compute_items == (
        ComputeItem(kind=ComputeKind.VECTOR, amount=expected_numel, dtype="f32"),
    )
    assert result.compute_totals_by_kind == {ComputeKind.VECTOR: expected_numel}
    assert len(result.memory_items) == 2
    assert [item.access for item in result.memory_items] == ["read", "write"]
    _assert_expr_equal(result.total_read_bytes, expected_numel * 4)
    _assert_expr_equal(result.total_write_bytes, expected_numel * 4)


# AN-020H-C
# 创建者: jcc你莫辜负
# 最后一次更改: jcc你莫辜负
# 最近一次运行测试时间: 2026-04-04 00:00:00 +0800
# 最近一次运行成功时间: 2026-04-04 00:00:00 +0800
# 测试目的: 验证 compare(i1) 在新 schema 下保留 ComputeKind.VECTOR，且 predicate_size 仍生效。
# 使用示例: pytest -q test/analysis/test_analysis.py -k test_analysis_compare_i1_keeps_predicate_size_in_new_schema
# 对应功能实现文件路径: kernel_gen/analysis/analysis.py
# 对应 spec 文件路径: spec/analysis/analysis_engine.md
# 对应测试文件路径: test/analysis/test_analysis.py
def test_analysis_compare_i1_keeps_predicate_size_in_new_schema() -> None:
    lhs_type = _make_memory_type([IntAttr(2), IntAttr(3)], f32, "global")
    out_type = _make_memory_type([IntAttr(2), IntAttr(3)], i1, "global")
    space = _make_space("global")
    block = Block(arg_types=[lhs_type, lhs_type])
    eq_op = NnEqOp(block.args[0], block.args[1], out_type, space)

    result = analysis(
        eq_op,
        AnalysisConfig(enable_compute=True, enable_memory=True, predicate_size=2, dtype_size_overrides={"f32": 4}),
    )

    assert result.compute_items == (
        ComputeItem(kind=ComputeKind.VECTOR, amount=sp.Integer(6), dtype="i1"),
    )
    assert result.compute_totals_by_kind == {ComputeKind.VECTOR: sp.Integer(6)}
    _assert_expr_equal(result.total_write_bytes, sp.Integer(12))


# AN-020L-C
# 创建者: 金铲铲大作战
# 最后修改人: 金铲铲大作战
# 最近一次运行测试时间: 2026-04-05 00:00:00 +0800
# 最近一次运行成功时间: 2026-04-05 00:00:00 +0800
# 测试目的: 验证 nn.exp 产出 ComputeKind.MATH。
# 使用示例: pytest -q test/analysis/test_analysis.py -k test_analysis_exp_math_compute_kind
# 对应功能实现文件路径: kernel_gen/analysis/compute/nn.py
# 对应 spec 文件路径: spec/analysis/analysis_engine.md
# 对应测试文件路径: test/analysis/test_analysis.py
def test_analysis_exp_math_compute_kind() -> None:
    """创建者: 金铲铲大作战
    最后修改人: 金铲铲大作战

    功能说明:
    - 验证 nn.exp 产出 ComputeKind.MATH。

    使用示例:
    - pytest -q test/analysis/test_analysis.py -k test_analysis_exp_math_compute_kind

    关联文件:
    - spec: spec/analysis/analysis_engine.md
    - test: test/analysis/test_analysis.py
    - 功能实现: kernel_gen/analysis/compute/nn.py
    """
    mem_type = _make_memory_type([StringAttr("M"), StringAttr("N")], f32, "global")
    space = _make_space("global")
    block = Block(arg_types=[mem_type])
    exp_op = FakeNnExpOp(block.args[0], mem_type, space)

    result = analysis(
        exp_op,
        AnalysisConfig(enable_compute=True, enable_memory=False, dtype_size_overrides={"f32": 4}),
    )

    expected_numel = SymbolDim("M").get_symbol() * SymbolDim("N").get_symbol()
    assert result.compute_items == (
        ComputeItem(kind=ComputeKind.MATH, amount=expected_numel, dtype="f32"),
    )
    assert result.compute_totals_by_kind == {ComputeKind.MATH: expected_numel}


# AN-020M-C
# 创建者: 金铲铲大作战
# 最后修改人: 金铲铲大作战
# 最近一次运行测试时间: 2026-04-05 00:00:00 +0800
# 最近一次运行成功时间: 2026-04-05 00:00:00 +0800
# 测试目的: 验证 nn.reduce_* 产出 ComputeKind.VECTOR。
# 使用示例: pytest -q test/analysis/test_analysis.py -k test_analysis_reduce_vector_compute_kind
# 对应功能实现文件路径: kernel_gen/analysis/compute/nn.py
# 对应 spec 文件路径: spec/analysis/analysis_engine.md
# 对应测试文件路径: test/analysis/test_analysis.py
@pytest.mark.parametrize(
    "reduce_cls",
    [FakeNnReduceSumOp, FakeNnReduceMinOp, FakeNnReduceMaxOp],
)
def test_analysis_reduce_vector_compute_kind(reduce_cls: type[IRDLOperation]) -> None:
    """创建者: 金铲铲大作战
    最后修改人: 金铲铲大作战

    功能说明:
    - 验证 nn.reduce_* 产出 ComputeKind.VECTOR。

    使用示例:
    - pytest -q test/analysis/test_analysis.py -k test_analysis_reduce_vector_compute_kind

    关联文件:
    - spec: spec/analysis/analysis_engine.md
    - test: test/analysis/test_analysis.py
    - 功能实现: kernel_gen/analysis/compute/nn.py
    """
    in_type = _make_memory_type([StringAttr("M"), StringAttr("N")], f32, "global")
    out_type = _make_memory_type([StringAttr("M"), IntAttr(1)], f32, "global")
    space = _make_space("global")
    block = Block(arg_types=[in_type])
    reduce_op = reduce_cls(block.args[0], out_type, space)

    result = analysis(
        reduce_op,
        AnalysisConfig(enable_compute=True, enable_memory=False, dtype_size_overrides={"f32": 4}),
    )

    expected = SymbolDim("M").get_symbol() * SymbolDim("N").get_symbol() - SymbolDim("M").get_symbol()
    assert result.compute_items == (
        ComputeItem(kind=ComputeKind.VECTOR, amount=expected, dtype="f32"),
    )
    assert result.compute_totals_by_kind == {ComputeKind.VECTOR: expected}


# AN-025
# 创建者: 朽木露琪亚
# 最后修改人: 朽木露琪亚
# 最近一次运行测试时间: 2026-04-05 00:00:00 +0800
# 最近一次运行成功时间: 2026-04-05 00:00:00 +0800
# 测试目的: 验证 nn.softmax 同时产生 VECTOR/MATH compute 与对应读写量。
# 使用示例: pytest -q test/analysis/test_analysis.py -k test_analysis_softmax_compute_and_memory
# 对应功能实现文件路径: kernel_gen/analysis/compute/nn.py
# 对应 spec 文件路径: spec/analysis/analysis_engine.md
# 对应测试文件路径: test/analysis/test_analysis.py
def test_analysis_softmax_compute_and_memory() -> None:
    mem_type = _make_memory_type([IntAttr(2), IntAttr(3), IntAttr(4)], f32, "global")
    space = _make_space("global")
    block = Block(arg_types=[mem_type])
    softmax_op = NnSoftmaxOp(block.args[0], mem_type, axis=-1, space=space)

    result = analysis(
        softmax_op,
        AnalysisConfig(enable_compute=True, enable_memory=True, dtype_size_overrides={"f32": 4}),
    )

    numel = sp.Integer(24)
    groups = sp.Integer(6)
    vector_compute = sp.Integer(4) * numel - sp.Integer(2) * groups
    math_compute = numel
    assert result.compute_items == (
        ComputeItem(kind=ComputeKind.VECTOR, amount=vector_compute, dtype="f32"),
        ComputeItem(kind=ComputeKind.MATH, amount=math_compute, dtype="f32"),
    )
    assert result.compute_totals_by_kind == {
        ComputeKind.VECTOR: vector_compute,
        ComputeKind.MATH: math_compute,
    }
    _assert_expr_equal(result.total_compute, vector_compute + math_compute)
    _assert_expr_equal(result.total_read_bytes, numel * 4)
    _assert_expr_equal(result.total_write_bytes, numel * 4)
    assert len(result.memory_items) == 2
    assert all(item.path is not MemoryPath.UNKNOWN for item in result.memory_items)


# AN-026
# 创建者: 朽木露琪亚
# 最后修改人: 朽木露琪亚
# 最近一次运行测试时间: 2026-04-05 00:00:00 +0800
# 最近一次运行成功时间: 2026-04-05 00:00:00 +0800
# 测试目的: 验证 nn.img2col1d 不产生 compute 且读写按结构化输出 numel 统计。
# 使用示例: pytest -q test/analysis/test_analysis.py -k test_analysis_img2col1d_direct_memory_only
# 对应功能实现文件路径: kernel_gen/analysis/memory/nn.py
# 对应 spec 文件路径: spec/analysis/analysis_engine.md
# 对应测试文件路径: test/analysis/test_analysis.py
def test_analysis_img2col1d_direct_memory_only() -> None:
    input_type = _make_memory_type([IntAttr(1), IntAttr(2), IntAttr(8)], f32, "global")
    result_type = _make_memory_type([IntAttr(1), IntAttr(2), IntAttr(3), IntAttr(8)], f32, "global")
    space = _make_space("global")
    block = Block(arg_types=[input_type])
    img2col_op = NnImg2col1dOp(block.args[0], result_type, kw=3, sw=1, dw=1, pl=1, pr=1, space=space)

    result = analysis(
        img2col_op,
        AnalysisConfig(enable_compute=True, enable_memory=True, dtype_size_overrides={"f32": 4}),
    )

    expected_numel = sp.Integer(48)
    expected_bytes = expected_numel * 4
    assert result.compute_items == ()
    assert result.compute_totals_by_kind == {}
    _assert_expr_equal(result.total_compute, sp.Integer(0))
    _assert_expr_equal(result.total_read_bytes, expected_bytes)
    _assert_expr_equal(result.total_write_bytes, expected_bytes)
    assert len(result.memory_items) == 2
    assert all(item.path is not MemoryPath.UNKNOWN for item in result.memory_items)


# AN-026B
# 创建者: 金铲铲大作战
# 最后修改人: 金铲铲大作战
# 最近一次运行测试时间: 2026-04-05 15:40:00 +0800
# 最近一次运行成功时间: 2026-04-05 15:40:00 +0800
# 测试目的: 验证 symbolic img2col1d 结果形状不匹配时必须抛 AnalysisError（compute/memory 均需拒绝）。
# 使用示例: pytest -q test/analysis/test_analysis.py -k test_analysis_img2col1d_symbolic_shape_mismatch_rejected
# 对应功能实现文件路径: kernel_gen/analysis/compute/nn.py, kernel_gen/analysis/memory/nn.py
# 对应 spec 文件路径: spec/analysis/analysis_engine.md
# 对应测试文件路径: test/analysis/test_analysis.py
def test_analysis_img2col1d_symbolic_shape_mismatch_rejected() -> None:
    input_type = _make_memory_type(
        [StringAttr("N"), StringAttr("C"), StringAttr("W")],
        f32,
        "global",
    )
    result_type = _make_memory_type(
        [StringAttr("N"), StringAttr("C"), IntAttr(3), StringAttr("BAD")],
        f32,
        "global",
    )
    space = _make_space("global")
    block = Block(arg_types=[input_type])
    img2col_op = NnImg2col1dOp(block.args[0], result_type, kw=3, sw=1, dw=1, pl=1, pr=1, space=space)

    with pytest.raises(AnalysisError, match="nn.img2col1d output shape mismatch"):
        analysis(
            img2col_op,
            AnalysisConfig(enable_compute=True, enable_memory=False, dtype_size_overrides={"f32": 4}),
        )
    with pytest.raises(AnalysisError, match="nn.img2col1d output shape mismatch"):
        analysis(
            img2col_op,
            AnalysisConfig(enable_compute=False, enable_memory=True, dtype_size_overrides={"f32": 4}),
        )


# AN-027
# 创建者: 朽木露琪亚
# 最后修改人: 朽木露琪亚
# 最近一次运行测试时间: 2026-04-05 00:00:00 +0800
# 最近一次运行成功时间: 2026-04-05 00:00:00 +0800
# 测试目的: 验证 nn.img2col2d 不产生 compute 且读写按结构化输出 numel 统计。
# 使用示例: pytest -q test/analysis/test_analysis.py -k test_analysis_img2col2d_direct_memory_only
# 对应功能实现文件路径: kernel_gen/analysis/memory/nn.py
# 对应 spec 文件路径: spec/analysis/analysis_engine.md
# 对应测试文件路径: test/analysis/test_analysis.py
def test_analysis_img2col2d_direct_memory_only() -> None:
    input_type = _make_memory_type([IntAttr(1), IntAttr(2), IntAttr(5), IntAttr(5)], f32, "global")
    result_type = _make_memory_type(
        [IntAttr(1), IntAttr(2), IntAttr(3), IntAttr(3), IntAttr(5), IntAttr(5)],
        f32,
        "global",
    )
    space = _make_space("global")
    block = Block(arg_types=[input_type])
    img2col_op = NnImg2col2dOp(
        block.args[0],
        result_type,
        kh=3,
        kw=3,
        sh=1,
        sw=1,
        dh=1,
        dw=1,
        ph=1,
        pw=1,
        pl=1,
        pr=1,
        space=space,
    )

    result = analysis(
        img2col_op,
        AnalysisConfig(enable_compute=True, enable_memory=True, dtype_size_overrides={"f32": 4}),
    )

    expected_numel = sp.Integer(450)
    expected_bytes = expected_numel * 4
    assert result.compute_items == ()
    assert result.compute_totals_by_kind == {}
    _assert_expr_equal(result.total_compute, sp.Integer(0))
    _assert_expr_equal(result.total_read_bytes, expected_bytes)
    _assert_expr_equal(result.total_write_bytes, expected_bytes)
    assert len(result.memory_items) == 2
    assert all(item.path is not MemoryPath.UNKNOWN for item in result.memory_items)


# AN-027B
# 创建者: 金铲铲大作战
# 最后修改人: 金铲铲大作战
# 最近一次运行测试时间: 2026-04-05 15:40:00 +0800
# 最近一次运行成功时间: 2026-04-05 15:40:00 +0800
# 测试目的: 验证 symbolic img2col2d 结果形状不匹配时必须抛 AnalysisError（compute/memory 均需拒绝）。
# 使用示例: pytest -q test/analysis/test_analysis.py -k test_analysis_img2col2d_symbolic_shape_mismatch_rejected
# 对应功能实现文件路径: kernel_gen/analysis/compute/nn.py, kernel_gen/analysis/memory/nn.py
# 对应 spec 文件路径: spec/analysis/analysis_engine.md
# 对应测试文件路径: test/analysis/test_analysis.py
def test_analysis_img2col2d_symbolic_shape_mismatch_rejected() -> None:
    input_type = _make_memory_type(
        [StringAttr("N"), StringAttr("C"), StringAttr("H"), StringAttr("W")],
        f32,
        "global",
    )
    result_type = _make_memory_type(
        [
            StringAttr("N"),
            StringAttr("C"),
            IntAttr(3),
            IntAttr(3),
            StringAttr("BADH"),
            StringAttr("BADW"),
        ],
        f32,
        "global",
    )
    space = _make_space("global")
    block = Block(arg_types=[input_type])
    img2col_op = NnImg2col2dOp(
        block.args[0],
        result_type,
        kh=3,
        kw=3,
        sh=1,
        sw=1,
        dh=1,
        dw=1,
        ph=1,
        pw=1,
        pl=1,
        pr=1,
        space=space,
    )

    with pytest.raises(AnalysisError, match="nn.img2col2d output shape mismatch"):
        analysis(
            img2col_op,
            AnalysisConfig(enable_compute=True, enable_memory=False, dtype_size_overrides={"f32": 4}),
        )
    with pytest.raises(AnalysisError, match="nn.img2col2d output shape mismatch"):
        analysis(
            img2col_op,
            AnalysisConfig(enable_compute=False, enable_memory=True, dtype_size_overrides={"f32": 4}),
        )


# AN-020N-C
# 创建者: 金铲铲大作战
# 最后修改人: 金铲铲大作战
# 最近一次运行测试时间: 2026-04-05 00:00:00 +0800
# 最近一次运行成功时间: 2026-04-05 00:00:00 +0800
# 测试目的: 验证 nn.broadcast 只产出 direct memory item。
# 使用示例: pytest -q test/analysis/test_analysis.py -k test_analysis_broadcast_direct_memory_only
# 对应功能实现文件路径: kernel_gen/analysis/memory/nn.py
# 对应 spec 文件路径: spec/analysis/analysis_engine.md
# 对应测试文件路径: test/analysis/test_analysis.py
def test_analysis_broadcast_direct_memory_only() -> None:
    """创建者: 金铲铲大作战
    最后修改人: 金铲铲大作战

    功能说明:
    - 验证 nn.broadcast 仅产出 direct memory item。

    使用示例:
    - pytest -q test/analysis/test_analysis.py -k test_analysis_broadcast_direct_memory_only

    关联文件:
    - spec: spec/analysis/analysis_engine.md
    - test: test/analysis/test_analysis.py
    - 功能实现: kernel_gen/analysis/memory/nn.py
    """
    inp_type = _make_memory_type([IntAttr(1), StringAttr("N")], f32, "shared")
    out_type = _make_memory_type([StringAttr("M"), StringAttr("N")], f32, "shared")
    space = _make_space("shared")
    block = Block(arg_types=[inp_type])
    broadcast_op = FakeNnBroadcastOp(block.args[0], out_type, space)

    result = analysis(
        broadcast_op,
        AnalysisConfig(enable_compute=True, enable_memory=True, dtype_size_overrides={"f32": 4}),
    )

    expected_read = SymbolDim("N").get_symbol() * 4
    expected_write = SymbolDim("M").get_symbol() * SymbolDim("N").get_symbol() * 4
    assert result.compute_items == ()
    assert result.compute_totals_by_kind == {}
    _assert_expr_equal(result.total_read_bytes, expected_read)
    _assert_expr_equal(result.total_write_bytes, expected_write)
    assert len(result.memory_items) == 2
    assert all(item.path is not MemoryPath.UNKNOWN for item in result.memory_items)


# AN-020O-C
# 创建者: 金铲铲大作战
# 最后修改人: 金铲铲大作战
# 最近一次运行测试时间: 2026-04-05 00:00:00 +0800
# 最近一次运行成功时间: 2026-04-05 00:00:00 +0800
# 测试目的: 验证 nn.transpose 只产出 direct memory item。
# 使用示例: pytest -q test/analysis/test_analysis.py -k test_analysis_transpose_direct_memory_only
# 对应功能实现文件路径: kernel_gen/analysis/memory/nn.py
# 对应 spec 文件路径: spec/analysis/analysis_engine.md
# 对应测试文件路径: test/analysis/test_analysis.py
def test_analysis_transpose_direct_memory_only() -> None:
    """创建者: 金铲铲大作战
    最后修改人: 金铲铲大作战

    功能说明:
    - 验证 nn.transpose 仅产出 direct memory item。

    使用示例:
    - pytest -q test/analysis/test_analysis.py -k test_analysis_transpose_direct_memory_only

    关联文件:
    - spec: spec/analysis/analysis_engine.md
    - test: test/analysis/test_analysis.py
    - 功能实现: kernel_gen/analysis/memory/nn.py
    """
    inp_type = _make_memory_type([StringAttr("M"), StringAttr("N")], f32, "global")
    out_type = _make_memory_type([StringAttr("N"), StringAttr("M")], f32, "global")
    space = _make_space("global")
    block = Block(arg_types=[inp_type])
    transpose_op = FakeNnTransposeOp(block.args[0], out_type, space)

    result = analysis(
        transpose_op,
        AnalysisConfig(enable_compute=True, enable_memory=True, dtype_size_overrides={"f32": 4}),
    )

    expected_numel = SymbolDim("M").get_symbol() * SymbolDim("N").get_symbol()
    expected_bytes = expected_numel * 4
    assert result.compute_items == ()
    assert result.compute_totals_by_kind == {}
    _assert_expr_equal(result.total_read_bytes, expected_bytes)
    _assert_expr_equal(result.total_write_bytes, expected_bytes)
    assert len(result.memory_items) == 2
    assert all(item.path is not MemoryPath.UNKNOWN for item in result.memory_items)


# AN-020P-C
# 创建者: 金铲铲大作战
# 最后修改人: 金铲铲大作战
# 最近一次运行测试时间: 2026-04-05 00:00:00 +0800
# 最近一次运行成功时间: 2026-04-05 00:00:00 +0800
# 测试目的: 验证 shared/local/tsm/tlm 的 nn.* 不落到 UNKNOWN path。
# 使用示例: pytest -q test/analysis/test_analysis.py -k test_analysis_nn_memory_paths_not_unknown_for_non_global_spaces
# 对应功能实现文件路径: kernel_gen/analysis/memory/nn.py
# 对应 spec 文件路径: spec/analysis/analysis_engine.md
# 对应测试文件路径: test/analysis/test_analysis.py
@pytest.mark.parametrize("space_name", ["shared", "local", "tsm", "tlm"])
def test_analysis_nn_memory_paths_not_unknown_for_non_global_spaces(space_name: str) -> None:
    """创建者: 金铲铲大作战
    最后修改人: 金铲铲大作战

    功能说明:
    - 验证 shared/local/tsm/tlm 空间的 nn.* 不落到 UNKNOWN path。

    使用示例:
    - pytest -q test/analysis/test_analysis.py -k test_analysis_nn_memory_paths_not_unknown_for_non_global_spaces

    关联文件:
    - spec: spec/analysis/analysis_engine.md
    - test: test/analysis/test_analysis.py
    - 功能实现: kernel_gen/analysis/memory/nn.py
    """
    mem_type = _make_memory_type([IntAttr(2), IntAttr(2)], f32, space_name)
    space = _make_space(space_name)
    block = Block(arg_types=[mem_type, mem_type])
    add_op = NnAddOp(block.args[0], block.args[1], mem_type, space)

    result = analysis(
        add_op,
        AnalysisConfig(enable_compute=True, enable_memory=True, dtype_size_overrides={"f32": 4}),
    )

    assert len(result.memory_items) == 3
    assert all(item.path is not MemoryPath.UNKNOWN for item in result.memory_items)


# AN-020D
# 创建者: 朽木露琪亚
# 最后一次更改: 朽木露琪亚
# 最近一次运行测试时间: 2026-04-04 00:00:00 +0800
# 最近一次运行成功时间: 2026-04-04 00:00:00 +0800
# 测试目的: 验证 dma.copy 在新 schema 中报告固定 GM->LM path 与 time_ns。
# 使用示例: pytest -q test/analysis/test_analysis.py -k test_analysis_dma_copy_reports_gm_to_lm_path_and_time
# 对应功能实现文件路径: kernel_gen/analysis/analysis.py
# 对应 spec 文件路径: spec/analysis/analysis_engine.md
# 对应测试文件路径: test/analysis/test_analysis.py


def test_analysis_dma_copy_reports_gm_to_lm_path_and_time() -> None:
    source_type = _make_memory_type([IntAttr(2), IntAttr(2)], f32, "global")
    target_type = _make_memory_type([IntAttr(2), IntAttr(2)], f32, "local")
    block = Block(arg_types=[source_type, target_type])
    copy_op = DmaCopyOp(block.args[0], block.args[1])

    result = analysis(
        copy_op,
        AnalysisConfig(
            target="npu_demo",
            enable_compute=False,
            enable_memory=True,
            dtype_size_overrides={"f32": 4},
        ),
    )

    assert len(result.memory_items) == 2
    read_item, write_item = result.memory_items
    assert read_item.path is MemoryPath.GM_TO_LM
    assert write_item.path is MemoryPath.GM_TO_LM
    _assert_expr_equal(result.memory_totals_by_path[MemoryPath.GM_TO_LM], sp.Integer(32))
    assert read_item.latency_ns == sp.Integer(20)
    assert read_item.bandwidth == sp.Integer(64)
    _assert_expr_equal(read_item.time_ns or sp.Integer(0), sp.Integer(20) + sp.Rational(16, 64))
    _assert_expr_equal(write_item.time_ns or sp.Integer(0), sp.Integer(20) + sp.Rational(16, 64))


# AN-020E
# 创建者: 朽木露琪亚
# 最后一次更改: 朽木露琪亚
# 最近一次运行测试时间: 2026-04-04 00:00:00 +0800
# 最近一次运行成功时间: 2026-04-04 00:00:00 +0800
# 测试目的: 验证 dma.slice 在新 schema 中报告固定 GM->SM path 与 bytes。
# 使用示例: pytest -q test/analysis/test_analysis.py -k test_analysis_dma_slice_reports_gm_to_sm_path_and_bytes
# 对应功能实现文件路径: kernel_gen/analysis/analysis.py
# 对应 spec 文件路径: spec/analysis/analysis_engine.md
# 对应测试文件路径: test/analysis/test_analysis.py


def test_analysis_dma_slice_reports_gm_to_sm_path_and_bytes() -> None:
    source_type = _make_memory_type([IntAttr(2), IntAttr(4)], f32, "global")
    target_type = _make_memory_type([IntAttr(1), IntAttr(2)], f32, "shared")
    symbol_types = [
        SymbolValueType.from_expr("0"),
        SymbolValueType.from_expr("0"),
        SymbolValueType.from_expr("1"),
        SymbolValueType.from_expr("2"),
        SymbolValueType.from_expr("1"),
        SymbolValueType.from_expr("1"),
    ]
    block = Block(arg_types=[target_type, source_type, *symbol_types])
    slice_op = DmaSliceOp(
        block.args[0],
        block.args[1],
        [block.args[2], block.args[3]],
        [block.args[4], block.args[5]],
        [block.args[6], block.args[7]],
    )

    result = analysis(
        slice_op,
        AnalysisConfig(
            target="npu_demo",
            enable_compute=False,
            enable_memory=True,
            dtype_size_overrides={"f32": 4},
        ),
    )

    assert len(result.memory_items) == 2
    read_item, write_item = result.memory_items
    assert read_item.path is MemoryPath.GM_TO_SM
    assert write_item.path is MemoryPath.GM_TO_SM
    _assert_expr_equal(read_item.bytes, sp.Integer(8))
    _assert_expr_equal(write_item.bytes, sp.Integer(8))
    _assert_expr_equal(result.memory_totals_by_path[MemoryPath.GM_TO_SM], sp.Integer(16))


# AN-020Q
# 创建者: 朽木露琪亚
# 最后一次更改: 朽木露琪亚
# 最近一次运行测试时间: 2026-04-05 00:00:00 +0800
# 最近一次运行成功时间: 2026-04-05 00:00:00 +0800
# 测试目的: 验证 dma.fill 仅统计 compute->target 写流量且无读流量。
# 使用示例: pytest -q test/analysis/test_analysis.py -k test_analysis_dma_fill_reports_compute_to_target_write
# 对应功能实现文件路径: kernel_gen/analysis/analysis.py
# 对应 spec 文件路径: spec/analysis/analysis_engine.md
# 对应测试文件路径: test/analysis/test_analysis.py


def test_analysis_dma_fill_reports_compute_to_target_write() -> None:
    target_type = _make_memory_type([IntAttr(2), IntAttr(2)], i32, "global")
    block = Block(arg_types=[target_type])
    const_op = arith.ConstantOp(IntegerAttr(0, i32))
    block.add_op(const_op)
    fill_op = DmaFillOp(block.args[0], const_op.result)

    result = analysis(
        fill_op,
        AnalysisConfig(
            target="npu_demo",
            enable_compute=False,
            enable_memory=True,
            dtype_size_overrides={"i32": 4},
        ),
    )

    assert result.compute_items == ()
    assert len(result.memory_items) == 1
    item = result.memory_items[0]
    assert item.path is MemoryPath.COMPUTE_TO_GM
    _assert_expr_equal(item.bytes, sp.Integer(16))
    _assert_expr_equal(result.total_read_bytes, sp.Integer(0))
    _assert_expr_equal(result.total_write_bytes, sp.Integer(16))
    _assert_expr_equal(result.memory_totals_by_path[MemoryPath.COMPUTE_TO_GM], sp.Integer(16))


# AN-020R
# 创建者: 朽木露琪亚
# 最后一次更改: 朽木露琪亚
# 最近一次运行测试时间: 2026-04-05 00:00:00 +0800
# 最近一次运行成功时间: 2026-04-05 00:00:00 +0800
# 测试目的: 验证 dma.cast 同时产出 compute=VECTOR 与按 dtype 拆分的读写 bytes。
# 使用示例: pytest -q test/analysis/test_analysis.py -k test_analysis_dma_cast_reports_compute_and_memory
# 对应功能实现文件路径: kernel_gen/analysis/analysis.py
# 对应 spec 文件路径: spec/analysis/analysis_engine.md
# 对应测试文件路径: test/analysis/test_analysis.py


def test_analysis_dma_cast_reports_compute_and_memory() -> None:
    i8 = IntegerType(8)
    source_type = _make_memory_type([IntAttr(2), IntAttr(3)], i8, "global")
    result_type = _make_memory_type([IntAttr(2), IntAttr(3)], f32, "global")
    block = Block(arg_types=[source_type])
    cast_op = DmaCastOp(block.args[0], result_type)

    result = analysis(
        cast_op,
        AnalysisConfig(
            target="npu_demo",
            enable_compute=True,
            enable_memory=True,
            dtype_size_overrides={"f32": 4, "i8": 1},
        ),
    )

    assert result.compute_totals_by_kind == {ComputeKind.VECTOR: sp.Integer(6)}
    assert len(result.memory_items) == 2
    read_item, write_item = result.memory_items
    assert read_item.path is MemoryPath.GM_TO_GM
    assert write_item.path is MemoryPath.GM_TO_GM
    _assert_expr_equal(read_item.bytes, sp.Integer(6))
    _assert_expr_equal(write_item.bytes, sp.Integer(24))
    _assert_expr_equal(result.total_read_bytes, sp.Integer(6))
    _assert_expr_equal(result.total_write_bytes, sp.Integer(24))
    _assert_expr_equal(result.memory_totals_by_path[MemoryPath.GM_TO_GM], sp.Integer(30))


# AN-020S
# 创建者: 朽木露琪亚
# 最后一次更改: 朽木露琪亚
# 最近一次运行测试时间: 2026-04-05 00:00:00 +0800
# 最近一次运行成功时间: 2026-04-05 00:00:00 +0800
# 测试目的: 验证 dma.view/dma.reshape 为零成本且无 warning。
# 使用示例: pytest -q test/analysis/test_analysis.py -k test_analysis_dma_view_reshape_zero_cost
# 对应功能实现文件路径: kernel_gen/analysis/analysis.py
# 对应 spec 文件路径: spec/analysis/analysis_engine.md
# 对应测试文件路径: test/analysis/test_analysis.py


def test_analysis_dma_view_reshape_zero_cost(recwarn: pytest.WarningsRecorder) -> None:
    source_stride = [IntAttr(2), IntAttr(1)]
    view_stride = [IntAttr(1), IntAttr(1)]
    source_type = _make_memory_type([IntAttr(2), IntAttr(2)], f32, "global", stride=source_stride)
    view_type = _make_memory_type([IntAttr(2), IntAttr(2)], f32, "global", stride=view_stride)
    reshape_type = _make_memory_type([IntAttr(4)], f32, "global")
    symbol_types = [
        SymbolValueType.from_expr("0"),
        SymbolValueType.from_expr("0"),
        SymbolValueType.from_expr("2"),
        SymbolValueType.from_expr("2"),
        SymbolValueType.from_expr("1"),
        SymbolValueType.from_expr("1"),
        SymbolValueType.from_expr("4"),
    ]
    block = Block(arg_types=[source_type, *symbol_types])
    offsets = [block.args[1], block.args[2]]
    shape = [block.args[3], block.args[4]]
    strides = [block.args[5], block.args[6]]
    view_op = DmaViewOp(block.args[0], offsets, shape, strides, view_type)
    reshape_op = DmaReshapeOp(block.args[0], [block.args[7]], reshape_type)
    config = AnalysisConfig(enable_compute=True, enable_memory=True, dtype_size_overrides={"f32": 4})

    view_result = analysis(view_op, config)
    reshape_result = analysis(reshape_op, config)

    for result in (view_result, reshape_result):
        assert result.compute_items == ()
        assert result.memory_items == ()
        _assert_expr_equal(result.total_compute, sp.Integer(0))
        _assert_expr_equal(result.total_read_bytes, sp.Integer(0))
        _assert_expr_equal(result.total_write_bytes, sp.Integer(0))

    assert len(recwarn) == 0


# AN-020F
# 创建者: 朽木露琪亚
# 最后一次更改: 朽木露琪亚
# 最近一次运行测试时间: 2026-04-04 00:00:00 +0800
# 最近一次运行成功时间: 2026-04-04 00:00:00 +0800
# 测试目的: 验证未知 op 在新 schema 中执行 skip + warning，且不写入 compute/memory 桶。
# 使用示例: pytest -q test/analysis/test_analysis.py -k test_analysis_unknown_op_warns_and_skips_in_new_schema
# 对应功能实现文件路径: kernel_gen/analysis/analysis.py
# 对应 spec 文件路径: spec/analysis/analysis_engine.md
# 对应测试文件路径: test/analysis/test_analysis.py


def test_analysis_unknown_op_warns_and_skips_in_new_schema() -> None:
    with pytest.warns(UserWarning, match="test.unknown"):
        result = analysis(
            UnknownOp(),
            AnalysisConfig(
                enable_compute=True,
                enable_memory=True,
                write_op_attrs=False,
                write_func_attrs=False,
            ),
        )

    assert result.compute_items == ()
    assert result.memory_items == ()
    assert result.compute_totals_by_kind == {}
    assert result.memory_totals_by_path == {}


# AN-020G
# 创建者: 朽木露琪亚
# 最后一次更改: 朽木露琪亚
# 最近一次运行测试时间: 2026-04-04 00:00:00 +0800
# 最近一次运行成功时间: 2026-04-04 00:00:00 +0800
# 测试目的: 验证公开 DMA 分支前置条件非法时在新 schema 中显式报错。
# 使用示例: pytest -q test/analysis/test_analysis.py -k test_analysis_invalid_public_dma_raises
# 对应功能实现文件路径: kernel_gen/analysis/analysis.py
# 对应 spec 文件路径: spec/analysis/analysis_engine.md
# 对应测试文件路径: test/analysis/test_analysis.py


def test_analysis_invalid_public_dma_raises() -> None:
    source_type = _make_memory_type([IntAttr(2), IntAttr(2)], f32, "global")
    target_type = _make_memory_type([IntAttr(2), IntAttr(4)], f32, "global")
    block = Block(arg_types=[source_type, target_type])
    copy_op = DmaCopyOp(block.args[0], block.args[1])

    with pytest.raises(AnalysisError, match="dma.copy source/target shape mismatch"):
        analysis(
            copy_op,
            AnalysisConfig(
                target="npu_demo",
                enable_compute=False,
                enable_memory=True,
                dtype_size_overrides={"f32": 4},
            ),
        )


# AN-020H
# 创建者: 朽木露琪亚
# 最后一次更改: 朽木露琪亚
# 最近一次运行测试时间: 2026-04-05 00:00:00 +0800
# 最近一次运行成功时间: 2026-04-05 00:00:00 +0800
# 测试目的: 验证 kernel.select/cast 计入 SCALAR 计算且无 warning。
# 使用示例: pytest -q test/analysis/test_analysis.py -k test_analysis_kernel_select_cast_scalar_compute
# 对应功能实现文件路径: kernel_gen/analysis/compute/kernel.py
# 对应 spec 文件路径: spec/analysis/analysis_engine.md
# 对应测试文件路径: test/analysis/test_analysis.py
def test_analysis_kernel_select_cast_scalar_compute(recwarn: pytest.WarningsRecorder) -> None:
    cond = arith.ConstantOp(IntegerAttr(1, i1))
    lhs = arith.ConstantOp(IntegerAttr(1, i32))
    rhs = arith.ConstantOp(IntegerAttr(2, i32))

    select_op = FakeKernelSelectOp(cond, lhs, rhs, i32)
    cast_op = FakeKernelCastOp(lhs, i32)
    config = AnalysisConfig(enable_compute=True, enable_memory=True)

    select_result = analysis(select_op, config)
    cast_result = analysis(cast_op, config)

    assert len(recwarn) == 0
    assert select_result.compute_totals_by_kind == {ComputeKind.SCALAR: sp.Integer(1)}
    assert cast_result.compute_totals_by_kind == {ComputeKind.SCALAR: sp.Integer(1)}


# AN-020I
# 创建者: 朽木露琪亚
# 最后一次更改: 朽木露琪亚
# 最近一次运行测试时间: 2026-04-05 00:00:00 +0800
# 最近一次运行成功时间: 2026-04-05 00:00:00 +0800
# 测试目的: 验证 symbol.* 默认计入 SCALAR 计算。
# 使用示例: pytest -q test/analysis/test_analysis.py -k test_analysis_symbol_scalar_compute
# 对应功能实现文件路径: kernel_gen/analysis/compute/symbol.py
# 对应 spec 文件路径: spec/analysis/analysis_engine.md
# 对应测试文件路径: test/analysis/test_analysis.py
def test_analysis_symbol_scalar_compute(recwarn: pytest.WarningsRecorder) -> None:
    symbol_type = SymbolValueType.from_expr("N")
    lhs = arith.ConstantOp(IntegerAttr(1, i32))
    rhs = arith.ConstantOp(IntegerAttr(2, i32))
    symbol_op = FakeSymbolAddOp(lhs, rhs, symbol_type)

    result = analysis(symbol_op, AnalysisConfig(enable_compute=True, enable_memory=True))

    assert len(recwarn) == 0
    assert result.compute_totals_by_kind == {ComputeKind.SCALAR: sp.Integer(1)}
    assert result.memory_items == ()


# AN-020J
# 创建者: 朽木露琪亚
# 最后一次更改: 朽木露琪亚
# 最近一次运行测试时间: 2026-04-05 00:00:00 +0800
# 最近一次运行成功时间: 2026-04-05 00:00:00 +0800
# 测试目的: 验证 symbol.to_int/to_float 仅统计 1 字节访存。
# 使用示例: pytest -q test/analysis/test_analysis.py -k test_analysis_symbol_cast_reads_one_byte
# 对应功能实现文件路径: kernel_gen/analysis/compute/symbol.py
# 对应 spec 文件路径: spec/analysis/analysis_engine.md
# 对应测试文件路径: test/analysis/test_analysis.py
def test_analysis_symbol_cast_reads_one_byte(recwarn: pytest.WarningsRecorder) -> None:
    value = arith.ConstantOp(IntegerAttr(3, i32))
    to_int = FakeSymbolToIntOp(value, i32)
    to_float = FakeSymbolToFloatOp(value, f32)
    config = AnalysisConfig(enable_compute=True, enable_memory=True)

    int_result = analysis(to_int, config)
    float_result = analysis(to_float, config)

    assert len(recwarn) == 0
    _assert_expr_equal(int_result.total_compute, sp.Integer(0))
    _assert_expr_equal(float_result.total_compute, sp.Integer(0))
    _assert_expr_equal(int_result.total_read_bytes, sp.Integer(1))
    _assert_expr_equal(float_result.total_read_bytes, sp.Integer(1))
    assert int_result.memory_totals_by_path[MemoryPath.GM_TO_GM] == sp.Integer(1)
    assert float_result.memory_totals_by_path[MemoryPath.GM_TO_GM] == sp.Integer(1)


# AN-020K
# 创建者: 朽木露琪亚
# 最后一次更改: 朽木露琪亚
# 最近一次运行测试时间: 2026-04-05 00:00:00 +0800
# 最近一次运行成功时间: 2026-04-05 00:00:00 +0800
# 测试目的: 验证 symbol.get_dim/get_stride、arch.*、tuner.param 为零成本且无 warning。
# 使用示例: pytest -q test/analysis/test_analysis.py -k test_analysis_metadata_ops_skip_without_warning
# 对应功能实现文件路径: kernel_gen/analysis/analysis.py
# 对应 spec 文件路径: spec/analysis/analysis_engine.md
# 对应测试文件路径: test/analysis/test_analysis.py
def test_analysis_metadata_ops_skip_without_warning(recwarn: pytest.WarningsRecorder) -> None:
    ops = [FakeSymbolGetDimOp(), FakeSymbolGetStrideOp(), FakeArchOp(), FakeTunerParamOp()]
    config = AnalysisConfig(enable_compute=True, enable_memory=True)

    for op in ops:
        result = analysis(op, config)
        assert result.compute_items == ()
        assert result.memory_items == ()
        assert not result.op_costs

    assert len(recwarn) == 0


# AN-021
# 创建者: 金铲铲大作战
# 最后一次更改: 金铲铲大作战
# 最近一次运行测试时间: 2026-04-03 00:00:00 +0800
# 最近一次运行成功时间: 2026-04-03 00:00:00 +0800
# 测试目的: 验证 region trip_count 放大 body 成本，且元信息 op 不产生 warning。
# 使用示例: pytest -q test/analysis/test_analysis.py -k test_analysis_func_trip_count_scales_region_body
# 对应功能实现文件路径: kernel_gen/analysis/analysis.py
# 对应 spec 文件路径: spec/analysis/analysis_engine.md
# 对应测试文件路径: test/analysis/test_analysis.py
def test_analysis_func_trip_count_scales_region_body(recwarn: pytest.WarningsRecorder) -> None:
    mem_type = _make_memory_type([IntAttr(2), IntAttr(3)], f32, "global")
    space = _make_space("global")
    region_block = Block(arg_types=[mem_type, mem_type])
    region_add = NnAddOp(region_block.args[0], region_block.args[1], mem_type, space)
    region_block.add_op(region_add)
    region = Region(region_block)
    region_op = FakeRegionOp(region, IntAttr(3))

    block = Block(arg_types=[])
    block.add_op(region_op)
    const_op = arith.ConstantOp(IntegerAttr(0, i32))
    block.add_op(const_op)
    block.add_op(func.ReturnOp(const_op.result))
    func_type = FunctionType.from_lists([], [i32])
    func_op = func.FuncOp("main", func_type, Region(block))

    result = analysis(
        func_op,
        AnalysisConfig(
            enable_compute=True,
            enable_memory=True,
            write_op_attrs=False,
            write_func_attrs=False,
            dtype_size_overrides={"f32": 4},
        ),
    )

    assert len(recwarn) == 0
    assert len(result.op_costs) == 1
    assert result.op_costs[0].op_name == "nn.add"
    _assert_expr_equal(result.total_compute, sp.Integer(18))


# AN-022
# 创建者: 金铲铲大作战
# 最后一次更改: 金铲铲大作战
# 最近一次运行测试时间: 2026-04-03 00:00:00 +0800
# 最近一次运行成功时间: 2026-04-03 00:00:00 +0800
# 测试目的: 验证 `analysis(func_op, ...)` 在 `write_op_attrs=True` 时写回逐 op attrs，不抛运行时错误。
# 使用示例: pytest -q test/analysis/test_analysis.py -k test_analysis_func_write_op_attrs_via_public_entry
# 对应功能实现文件路径: kernel_gen/analysis/analysis.py
# 对应 spec 文件路径: spec/analysis/analysis_engine.md
# 对应测试文件路径: test/analysis/test_analysis.py
def test_analysis_func_write_op_attrs_via_public_entry() -> None:
    mem_type = _make_memory_type([IntAttr(2), IntAttr(3)], f32, "global")
    space = _make_space("global")
    captured_ops: dict[str, Operation] = {}

    def _builder(block: Block) -> tuple[list[Operation], SSAValue]:
        add_op = NnAddOp(block.args[0], block.args[1], mem_type, space)
        captured_ops["add"] = add_op
        return [add_op], add_op.result

    _, func_op, _ = _build_module([mem_type, mem_type], mem_type, _builder)
    result = analysis(
        func_op,
        AnalysisConfig(
            enable_compute=True,
            enable_memory=True,
            write_op_attrs=True,
            write_func_attrs=False,
            dtype_size_overrides={"f32": 4},
        ),
    )

    add_op = captured_ops["add"]
    assert add_op.attributes["analysis.compute"].data == "6"
    assert add_op.attributes["analysis.read_bytes"].data == "48"
    assert add_op.attributes["analysis.write_bytes"].data == "24"
    assert "analysis.compute" not in func_op.attributes
    assert result.op_costs[0].op_name == "nn.add"


# AN-023
# 创建者: jcc你莫辜负
# 最后一次更改: jcc你莫辜负
# 最近一次运行测试时间: 2026-04-04 00:00:00 +0800
# 最近一次运行成功时间: 2026-04-04 00:00:00 +0800
# 测试目的: 验证 mixed func 的总量等于各桶求和，且 analysis/analyze_kernel/func_cost 三路结果一致。
# 使用示例: pytest -q test/analysis/test_analysis.py -k test_analysis_mixed_func_totals_equal_bucket_sums
# 对应功能实现文件路径: kernel_gen/analysis/analysis.py
# 对应 spec 文件路径: spec/analysis/analysis_engine.md
# 对应测试文件路径: test/analysis/test_analysis.py
def test_analysis_mixed_func_totals_equal_bucket_sums() -> None:
    module, func_op = _build_mixed_analysis_module(include_signature_hints=True)
    config = AnalysisConfig(
        target="npu_demo",
        enable_compute=True,
        enable_memory=True,
        predicate_size=2,
        dtype_size_overrides={"f32": 4},
    )

    result = analysis(func_op, config)
    kernel_summary = analyze_kernel(func_op, predicate_size=2, dtype_size_overrides={"f32": 4})
    pass_obj = AnalyzeFuncCostPass(predicate_size=2, dtype_size_overrides={"f32": 4})
    pass_obj.run(module)
    pass_summary = pass_obj.get_summary("main")

    bucket_compute_total = sum(result.compute_totals_by_kind.values(), sp.Integer(0))
    bucket_memory_total = sum(result.memory_totals_by_path.values(), sp.Integer(0))
    _assert_expr_equal(result.total_compute, bucket_compute_total)
    _assert_expr_equal(result.total_read_bytes + result.total_write_bytes, bucket_memory_total)
    assert result.compute_totals_by_kind == {ComputeKind.VECTOR: sp.Integer(12)}
    assert MemoryPath.GM_TO_GM in result.memory_totals_by_path
    assert MemoryPath.GM_TO_LM in result.memory_totals_by_path

    assert kernel_summary.op_costs == result.op_costs
    assert kernel_summary.value_traffic == result.value_traffic
    _assert_expr_equal(kernel_summary.total_compute, result.total_compute)
    _assert_expr_equal(kernel_summary.total_read_bytes, result.total_read_bytes)
    _assert_expr_equal(kernel_summary.total_write_bytes, result.total_write_bytes)

    assert pass_summary.op_costs == result.op_costs
    assert pass_summary.value_traffic == result.value_traffic
    _assert_expr_equal(pass_summary.total_compute, result.total_compute)
    _assert_expr_equal(pass_summary.total_read_bytes, result.total_read_bytes)
    _assert_expr_equal(pass_summary.total_write_bytes, result.total_write_bytes)


# AN-024
# 创建者: jcc你莫辜负
# 最后一次更改: jcc你莫辜负
# 最近一次运行测试时间: 2026-04-04 00:00:00 +0800
# 最近一次运行成功时间: 2026-04-04 00:00:00 +0800
# 测试目的: 验证无函数签名提示时，统一入口与下游结果仍与完整签名版本完全一致。
# 使用示例: pytest -q test/analysis/test_analysis.py -k test_analysis_no_signature_hint_matches_full_signature_version
# 对应功能实现文件路径: kernel_gen/analysis/analysis.py
# 对应 spec 文件路径: spec/analysis/analysis_engine.md
# 对应测试文件路径: test/analysis/test_analysis.py
def test_analysis_no_signature_hint_matches_full_signature_version() -> None:
    full_module, full_func = _build_mixed_analysis_module(include_signature_hints=True)
    hintless_module, hintless_func = _build_mixed_analysis_module(include_signature_hints=False)
    config = AnalysisConfig(
        target="npu_demo",
        enable_compute=True,
        enable_memory=True,
        predicate_size=2,
        dtype_size_overrides={"f32": 4},
    )

    full_result = analysis(full_func, config)
    hintless_result = analysis(hintless_func, config)
    assert hintless_result.op_costs == full_result.op_costs
    assert hintless_result.value_traffic == full_result.value_traffic
    assert hintless_result.compute_totals_by_kind == full_result.compute_totals_by_kind
    assert hintless_result.memory_totals_by_path == full_result.memory_totals_by_path
    _assert_expr_equal(hintless_result.total_compute, full_result.total_compute)
    _assert_expr_equal(hintless_result.total_read_bytes, full_result.total_read_bytes)
    _assert_expr_equal(hintless_result.total_write_bytes, full_result.total_write_bytes)

    full_summary = analyze_kernel(full_func, predicate_size=2, dtype_size_overrides={"f32": 4})
    hintless_summary = analyze_kernel(hintless_func, predicate_size=2, dtype_size_overrides={"f32": 4})
    assert hintless_summary.op_costs == full_summary.op_costs
    assert hintless_summary.value_traffic == full_summary.value_traffic
    _assert_expr_equal(hintless_summary.total_compute, full_summary.total_compute)
    _assert_expr_equal(hintless_summary.total_read_bytes, full_summary.total_read_bytes)
    _assert_expr_equal(hintless_summary.total_write_bytes, full_summary.total_write_bytes)

    full_pass = AnalyzeFuncCostPass(predicate_size=2, dtype_size_overrides={"f32": 4})
    full_pass.run(full_module)
    hintless_pass = AnalyzeFuncCostPass(predicate_size=2, dtype_size_overrides={"f32": 4})
    hintless_pass.run(hintless_module)
    full_pass_summary = full_pass.get_summary("main")
    hintless_pass_summary = hintless_pass.get_summary("main")
    assert hintless_pass_summary.op_costs == full_pass_summary.op_costs
    assert hintless_pass_summary.value_traffic == full_pass_summary.value_traffic
    _assert_expr_equal(hintless_pass_summary.total_compute, full_pass_summary.total_compute)
    _assert_expr_equal(hintless_pass_summary.total_read_bytes, full_pass_summary.total_read_bytes)
    _assert_expr_equal(hintless_pass_summary.total_write_bytes, full_pass_summary.total_write_bytes)


# AK-001
# 创建者: 金铲铲大作战
# 最后一次更改: 金铲铲大作战
# 最近一次运行测试时间: 2026-03-31 00:00:00 +0800
# 最近一次运行成功时间: 2026-03-31 00:00:00 +0800
# 测试目的: 验证 analyze_kernel 逐元素统计。
# 使用示例: pytest -q test/analysis/test_analysis.py -k test_analyze_kernel_nn_add_symbolic_shape
# 对应功能实现文件路径: kernel_gen/analysis/analysis.py
# 对应 spec 文件路径: spec/analysis/analysis_kernel.md
# 对应测试文件路径: test/analysis/test_analysis.py
def test_analyze_kernel_nn_add_symbolic_shape() -> None:
    mem_type = _make_memory_type([StringAttr("A"), StringAttr("B")], f32, "global")
    space = _make_space("global")

    def _builder(block: Block) -> tuple[list[Operation], SSAValue]:
        add_op = NnAddOp(block.args[0], block.args[1], mem_type, space)
        return [add_op], add_op.result

    _, func_op, _ = _build_module([mem_type, mem_type], mem_type, _builder)
    summary = analyze_kernel(func_op, dtype_size_overrides={"f32": 4})

    expected_numel = SymbolDim("A").get_symbol() * SymbolDim("B").get_symbol()
    assert summary.func_name == "main"
    _assert_expr_equal(summary.total_compute, expected_numel)
    _assert_expr_equal(summary.total_read_bytes, expected_numel * 2 * 4)
    _assert_expr_equal(summary.total_write_bytes, expected_numel * 4)
    assert summary.op_costs[0].op_name == "nn.add"


# AK-002
# 创建者: 金铲铲大作战
# 最后一次更改: 金铲铲大作战
# 最近一次运行测试时间: 2026-03-31 00:00:00 +0800
# 最近一次运行成功时间: 2026-03-31 00:00:00 +0800
# 测试目的: 验证 analyze_kernel tensor + const 不计常量读流量。
# 使用示例: pytest -q test/analysis/test_analysis.py -k test_analyze_kernel_tensor_plus_const
# 对应功能实现文件路径: kernel_gen/analysis/analysis.py
# 对应 spec 文件路径: spec/analysis/analysis_kernel.md
# 对应测试文件路径: test/analysis/test_analysis.py
def test_analyze_kernel_tensor_plus_const() -> None:
    mem_type = _make_memory_type([StringAttr("A"), StringAttr("B")], f32, "global")
    space = _make_space("global")

    def _builder(block: Block) -> tuple[list[Operation], SSAValue]:
        const_op = arith.ConstantOp(IntegerAttr(1, i32))
        add_op = FakeNnAddOp(block.args[0], const_op.result, mem_type, space)
        return [const_op, add_op], add_op.result

    _, func_op, _ = _build_module([mem_type], mem_type, _builder)
    summary = analyze_kernel(func_op, dtype_size_overrides={"f32": 4})

    expected_numel = SymbolDim("A").get_symbol() * SymbolDim("B").get_symbol()
    _assert_expr_equal(summary.total_compute, expected_numel)
    _assert_expr_equal(summary.total_read_bytes, expected_numel * 4)
    _assert_expr_equal(summary.total_write_bytes, expected_numel * 4)
    traffic = _value_traffic_map(summary)
    assert set(traffic.keys()) == {"arg0", "op0.result0"}


# AK-003
# 创建者: 金铲铲大作战
# 最后一次更改: 金铲铲大作战
# 最近一次运行测试时间: 2026-03-31 00:00:00 +0800
# 最近一次运行成功时间: 2026-03-31 00:00:00 +0800
# 测试目的: 验证 value_traffic 对中间结果读写归属。
# 使用示例: pytest -q test/analysis/test_analysis.py -k test_analyze_kernel_chain_value_traffic
# 对应功能实现文件路径: kernel_gen/analysis/analysis.py
# 对应 spec 文件路径: spec/analysis/analysis_kernel.md
# 对应测试文件路径: test/analysis/test_analysis.py
def test_analyze_kernel_chain_value_traffic() -> None:
    mem_type = _make_memory_type([StringAttr("A"), StringAttr("B")], f32, "global")
    space = _make_space("global")

    def _builder(block: Block) -> tuple[list[Operation], SSAValue]:
        add_op = NnAddOp(block.args[0], block.args[1], mem_type, space)
        mul_op = NnMulOp(add_op.result, block.args[2], mem_type, space)
        return [add_op, mul_op], mul_op.result

    _, func_op, _ = _build_module([mem_type, mem_type, mem_type], mem_type, _builder)
    summary = analyze_kernel(func_op, dtype_size_overrides={"f32": 4})
    traffic = _value_traffic_map(summary)
    for key in ["arg0", "arg1", "arg2", "op0.result0", "op1.result0"]:
        assert key in traffic

    expected_bytes = SymbolDim("A").get_symbol() * SymbolDim("B").get_symbol() * 4
    _assert_expr_equal(traffic["op0.result0"].write_bytes, expected_bytes)
    _assert_expr_equal(traffic["op0.result0"].read_bytes, expected_bytes)


# AK-004
# 创建者: 金铲铲大作战
# 最后一次更改: 金铲铲大作战
# 最近一次运行测试时间: 2026-03-31 00:00:00 +0800
# 最近一次运行成功时间: 2026-03-31 00:00:00 +0800
# 测试目的: 验证 analyze_kernel matmul 公式。
# 使用示例: pytest -q test/analysis/test_analysis.py -k test_analyze_kernel_matmul_formula
# 对应功能实现文件路径: kernel_gen/analysis/analysis.py
# 对应 spec 文件路径: spec/analysis/analysis_kernel.md
# 对应测试文件路径: test/analysis/test_analysis.py
def test_analyze_kernel_matmul_formula() -> None:
    lhs_type = _make_memory_type([StringAttr("M"), StringAttr("K")], f32, "global")
    rhs_type = _make_memory_type([StringAttr("K"), StringAttr("N")], f32, "global")
    out_type = _make_memory_type([StringAttr("M"), StringAttr("N")], f32, "global")
    space = _make_space("global")

    def _builder(block: Block) -> tuple[list[Operation], SSAValue]:
        matmul_op = NnMatmulOp(block.args[0], block.args[1], out_type, space)
        return [matmul_op], matmul_op.result

    _, func_op, _ = _build_module([lhs_type, rhs_type], out_type, _builder)
    summary = analyze_kernel(func_op, dtype_size_overrides={"f32": 4})

    m = SymbolDim("M").get_symbol()
    n = SymbolDim("N").get_symbol()
    k = SymbolDim("K").get_symbol()
    _assert_expr_equal(summary.total_compute, sp.Integer(2) * m * n * k)
    _assert_expr_equal(summary.total_read_bytes, (m * k + k * n) * 4)
    _assert_expr_equal(summary.total_write_bytes, m * n * 4)


# AK-005
# 创建者: 金铲铲大作战
# 最后一次更改: 金铲铲大作战
# 最近一次运行测试时间: 2026-03-31 00:00:00 +0800
# 最近一次运行成功时间: 2026-03-31 00:00:00 +0800
# 测试目的: 验证 dma.load 同时记录源读与结果写流量。
# 使用示例: pytest -q test/analysis/test_analysis.py -k test_analyze_kernel_dma_load_tracks_source_and_result
# 对应功能实现文件路径: kernel_gen/analysis/analysis.py
# 对应 spec 文件路径: spec/analysis/analysis_kernel.md
# 对应测试文件路径: test/analysis/test_analysis.py
def test_analyze_kernel_dma_load_tracks_source_and_result() -> None:
    mem_type = _make_memory_type([IntAttr(2), IntAttr(2)], f32, "global")
    space = _make_space("global")
    symbol_types = [
        SymbolValueType.from_expr("0"),
        SymbolValueType.from_expr("0"),
        SymbolValueType.from_expr("2"),
        SymbolValueType.from_expr("2"),
        SymbolValueType.from_expr("1"),
        SymbolValueType.from_expr("1"),
    ]

    arg_types = [mem_type, *symbol_types]

    def _builder(block: Block) -> tuple[list[Operation], SSAValue]:
        offsets = [block.args[1], block.args[2]]
        sizes = [block.args[3], block.args[4]]
        strides = [block.args[5], block.args[6]]
        load_op = DmaLoadOp(block.args[0], offsets, sizes, strides, mem_type, space)
        return [load_op], load_op.result

    _, func_op, _ = _build_module(arg_types, mem_type, _builder)
    summary = analyze_kernel(func_op, dtype_size_overrides={"f32": 4})
    expected_bytes = sp.Integer(16)
    _assert_expr_equal(summary.total_compute, sp.Integer(0))
    _assert_expr_equal(summary.total_read_bytes, expected_bytes)
    _assert_expr_equal(summary.total_write_bytes, expected_bytes)

    traffic = _value_traffic_map(summary)
    _assert_expr_equal(traffic["arg0"].read_bytes, expected_bytes)
    _assert_expr_equal(traffic["op0.result0"].write_bytes, expected_bytes)


# AK-006
# 创建者: 金铲铲大作战
# 最后一次更改: 金铲铲大作战
# 最近一次运行测试时间: 2026-03-31 00:00:00 +0800
# 最近一次运行成功时间: 2026-03-31 00:00:00 +0800
# 测试目的: 验证 analyze_kernel 拒绝非 func 输入。
# 使用示例: pytest -q test/analysis/test_analysis.py -k test_analyze_kernel_rejects_non_func_input
# 对应功能实现文件路径: kernel_gen/analysis/analysis.py
# 对应 spec 文件路径: spec/analysis/analysis_kernel.md
# 对应测试文件路径: test/analysis/test_analysis.py
def test_analyze_kernel_rejects_non_func_input() -> None:
    module = ModuleOp([])
    with pytest.raises(AnalysisError, match="func.FuncOp"):
        analyze_kernel(module)


# AK-007
# 创建者: 金铲铲大作战
# 最后一次更改: 金铲铲大作战
# 最近一次运行测试时间: 2026-03-31 00:00:00 +0800
# 最近一次运行成功时间: 2026-03-31 00:00:00 +0800
# 测试目的: 验证 analyze_kernel 拒绝非 iterable args。
# 使用示例: pytest -q test/analysis/test_analysis.py -k test_analyze_kernel_rejects_non_iterable_args
# 对应功能实现文件路径: kernel_gen/analysis/analysis.py
# 对应 spec 文件路径: spec/analysis/analysis_kernel.md
# 对应测试文件路径: test/analysis/test_analysis.py
def test_analyze_kernel_rejects_non_iterable_args() -> None:
    mem_type = _make_memory_type([IntAttr(2), IntAttr(2)], f32, "global")
    space = _make_space("global")

    def _builder(block: Block) -> tuple[list[Operation], SSAValue]:
        add_op = NnAddOp(block.args[0], block.args[1], mem_type, space)
        return [add_op], add_op.result

    _, func_op, _ = _build_module([mem_type, mem_type], mem_type, _builder)
    with pytest.raises(AnalysisError, match="args must be iterable"):
        analyze_kernel(func_op, args=object())


# AK-008
# 创建者: 金铲铲大作战
# 最后一次更改: 金铲铲大作战
# 最近一次运行测试时间: 2026-03-31 00:00:00 +0800
# 最近一次运行成功时间: 2026-03-31 00:00:00 +0800
# 测试目的: 验证 analyze_kernel args 长度与参数位次不匹配时报错。
# 使用示例: pytest -q test/analysis/test_analysis.py -k test_analyze_kernel_rejects_args_length_mismatch
# 对应功能实现文件路径: kernel_gen/analysis/analysis.py
# 对应 spec 文件路径: spec/analysis/analysis_kernel.md
# 对应测试文件路径: test/analysis/test_analysis.py
def test_analyze_kernel_rejects_args_length_mismatch() -> None:
    mem_type = _make_memory_type([IntAttr(2), IntAttr(2)], f32, "global")
    space = _make_space("global")

    def _builder(block: Block) -> tuple[list[Operation], SSAValue]:
        add_op = NnAddOp(block.args[0], block.args[1], mem_type, space)
        return [add_op], add_op.result

    _, func_op, _ = _build_module([mem_type, mem_type], mem_type, _builder)
    with pytest.raises(AnalysisError, match="args length mismatch"):
        analyze_kernel(func_op, args=[object()])


# AK-009
# 创建者: 金铲铲大作战
# 最后一次更改: 金铲铲大作战
# 最近一次运行测试时间: 2026-04-02 05:49:01 +0800
# 最近一次运行成功时间: 2026-04-02 05:49:01 +0800
# 测试目的: 验证未知 op skip + warning。
# 使用示例: pytest -q test/analysis/test_analysis.py -k test_analyze_kernel_unknown_op_warns_and_skips
# 对应功能实现文件路径: kernel_gen/analysis/analysis.py
# 对应 spec 文件路径: spec/analysis/analysis_kernel.md
# 对应测试文件路径: test/analysis/test_analysis.py
def test_analyze_kernel_unknown_op_warns_and_skips() -> None:
    mem_type = _make_memory_type([StringAttr("A"), StringAttr("B")], f32, "global")
    space = _make_space("global")

    def _builder(block: Block) -> tuple[list[Operation], SSAValue]:
        unknown = UnknownOp()
        add_op = NnAddOp(block.args[0], block.args[1], mem_type, space)
        return [unknown, add_op], add_op.result

    _, func_op, _ = _build_module([mem_type, mem_type], mem_type, _builder)
    with pytest.warns(UserWarning, match="test.unknown"):
        summary = analyze_kernel(func_op, dtype_size_overrides={"f32": 4})

    expected_numel = SymbolDim("A").get_symbol() * SymbolDim("B").get_symbol()
    _assert_expr_equal(summary.total_compute, expected_numel)
    assert len(summary.op_costs) == 1
    assert summary.op_costs[0].op_name == "nn.add"
    traffic = _value_traffic_map(summary)
    assert set(traffic.keys()) == {"arg0", "arg1", "op0.result0"}


# AK-010
# 创建者: 金铲铲大作战
# 最后一次更改: 金铲铲大作战
# 最近一次运行测试时间: 2026-04-02 05:49:01 +0800
# 最近一次运行成功时间: 2026-04-02 05:49:01 +0800
# 测试目的: 验证 compare i1 写回使用 predicate_size 优先级。
# 使用示例: pytest -q test/analysis/test_analysis.py -k test_analyze_kernel_compare_i1_uses_predicate_size
# 对应功能实现文件路径: kernel_gen/analysis/analysis.py
# 对应 spec 文件路径: spec/analysis/analysis_kernel.md
# 对应测试文件路径: test/analysis/test_analysis.py
def test_analyze_kernel_compare_i1_uses_predicate_size() -> None:
    lhs_type = _make_memory_type([StringAttr("A"), StringAttr("B")], f32, "global")
    rhs_type = _make_memory_type([StringAttr("A"), StringAttr("B")], f32, "global")
    out_type = _make_memory_type([StringAttr("A"), StringAttr("B")], i1, "global")
    space = _make_space("global")

    def _builder(block: Block) -> tuple[list[Operation], SSAValue]:
        eq_op = NnEqOp(block.args[0], block.args[1], out_type, space)
        return [eq_op], eq_op.result

    _, func_op, _ = _build_module([lhs_type, rhs_type], out_type, _builder)
    summary = analyze_kernel(
        func_op,
        predicate_size=2,
        dtype_size_overrides={"f32": 4, "i1": 8},
    )

    expected_numel = SymbolDim("A").get_symbol() * SymbolDim("B").get_symbol()
    _assert_expr_equal(summary.total_write_bytes, expected_numel * 2)
    _assert_expr_equal(summary.op_costs[0].write_bytes, expected_numel * 2)
    traffic = _value_traffic_map(summary)
    _assert_expr_equal(traffic["op0.result0"].write_bytes, expected_numel * 2)


# AN-018
# 创建者: 金铲铲大作战
# 最后一次更改: 金铲铲大作战
# 最近一次运行测试时间: 2026-04-02 05:49:01 +0800
# 最近一次运行成功时间: 2026-04-02 05:49:01 +0800
# 测试目的: 验证公开 DMA 分支中的 dma.copy 与 dma.store 会记录源读/目标写流量。
# 使用示例: pytest -q test/analysis/test_analysis.py -k test_analyze_kernel_dma_copy_and_store_track_source_and_target_traffic
# 对应功能实现文件路径: kernel_gen/analysis/analysis.py
# 对应 spec 文件路径: spec/analysis/analysis_kernel.md
# 对应测试文件路径: test/analysis/test_analysis.py
def test_analyze_kernel_dma_copy_and_store_track_source_and_target_traffic() -> None:
    mem_type = _make_memory_type([IntAttr(2), IntAttr(2)], f32, "global")
    symbol_types = [
        SymbolValueType.from_expr("0"),
        SymbolValueType.from_expr("0"),
        SymbolValueType.from_expr("2"),
        SymbolValueType.from_expr("2"),
        SymbolValueType.from_expr("1"),
        SymbolValueType.from_expr("1"),
    ]

    arg_types = [mem_type, mem_type, *symbol_types]

    def _builder(block: Block) -> tuple[list[Operation], SSAValue]:
        copy_op = DmaCopyOp(block.args[0], block.args[1])
        store_op = DmaStoreOp(
            block.args[0],
            block.args[1],
            [block.args[2], block.args[3]],
            [block.args[4], block.args[5]],
            [block.args[6], block.args[7]],
        )
        return [copy_op, store_op], block.args[1]

    _, func_op, _ = _build_module(arg_types, mem_type, _builder)
    summary = analyze_kernel(func_op, dtype_size_overrides={"f32": 4})

    expected_bytes = sp.Integer(16)
    _assert_expr_equal(summary.total_compute, sp.Integer(0))
    _assert_expr_equal(summary.total_read_bytes, expected_bytes * 2)
    _assert_expr_equal(summary.total_write_bytes, expected_bytes * 2)
    traffic = _value_traffic_map(summary)
    _assert_expr_equal(traffic["arg0"].read_bytes, expected_bytes * 2)
    _assert_expr_equal(traffic["arg1"].write_bytes, expected_bytes * 2)


# AN-019
# 创建者: 金铲铲大作战
# 最后一次更改: 金铲铲大作战
# 最近一次运行测试时间: 2026-04-02 05:49:01 +0800
# 最近一次运行成功时间: 2026-04-02 05:49:01 +0800
# 测试目的: 验证公开 DMA 分支前置条件失败时 analyze_kernel 会抛出 AnalysisError。
# 使用示例: pytest -q test/analysis/test_analysis.py -k test_analyze_kernel_rejects_invalid_public_dma_op
# 对应功能实现文件路径: kernel_gen/analysis/analysis.py
# 对应 spec 文件路径: spec/analysis/analysis_kernel.md
# 对应测试文件路径: test/analysis/test_analysis.py
def test_analyze_kernel_rejects_invalid_public_dma_op() -> None:
    source_type = _make_memory_type([IntAttr(2), IntAttr(2)], f32, "global")
    target_type = _make_memory_type([IntAttr(2), IntAttr(4)], f32, "global")

    def _builder(block: Block) -> tuple[list[Operation], SSAValue]:
        copy_op = DmaCopyOp(block.args[0], block.args[1])
        return [copy_op], block.args[0]

    _, func_op, _ = _build_module([source_type, target_type], source_type, _builder)
    with pytest.raises(AnalysisError, match="dma.copy source/target shape mismatch"):
        analyze_kernel(func_op, dtype_size_overrides={"f32": 4})


# AN-020
# 创建者: 金铲铲大作战
# 最后一次更改: 朽木露琪亚
# 最近一次运行测试时间: 2026-04-05 00:00:00 +0800
# 最近一次运行成功时间: 2026-04-05 00:00:00 +0800
# 测试目的: 验证 dma.alloc/deslice/free 已支持且不再产生 warning。
# 使用示例: pytest -q test/analysis/test_analysis.py -k test_analyze_kernel_dma_ops_supported_without_warning
# 对应功能实现文件路径: kernel_gen/analysis/analysis.py
# 对应 spec 文件路径: spec/analysis/analysis_kernel.md
# 对应测试文件路径: test/analysis/test_analysis.py
def test_analyze_kernel_dma_ops_supported_without_warning(recwarn: pytest.WarningsRecorder) -> None:
    full_type = _make_memory_type([IntAttr(2), IntAttr(4)], f32, "global", stride=[IntAttr(4), IntAttr(1)])
    tile_type = _make_memory_type([IntAttr(1), IntAttr(2)], f32, "global", stride=[IntAttr(2), IntAttr(1)])
    symbol_types = [
        SymbolValueType.from_expr("0"),
        SymbolValueType.from_expr("0"),
        SymbolValueType.from_expr("1"),
        SymbolValueType.from_expr("2"),
        SymbolValueType.from_expr("1"),
        SymbolValueType.from_expr("1"),
    ]

    arg_types = [full_type, *symbol_types]

    def _builder(block: Block) -> tuple[list[Operation], SSAValue]:
        offsets = [block.args[1], block.args[2]]
        sizes = [block.args[3], block.args[4]]
        strides = [block.args[5], block.args[6]]
        alloc_op = DmaAllocOp(sizes, tile_type)
        slice_op = DmaSliceOp(alloc_op.result, block.args[0], offsets, sizes, strides)
        deslice_op = DmaDesliceOp(alloc_op.result, block.args[0], offsets, sizes, strides, full_type)
        free_op = DmaFreeOp(alloc_op.result)
        return [alloc_op, slice_op, deslice_op, free_op], block.args[0]

    _, func_op, _ = _build_module(arg_types, full_type, _builder)
    summary = analyze_kernel(func_op, dtype_size_overrides={"f32": 4})

    assert len(recwarn) == 0
    assert [item.op_name for item in summary.op_costs] == [
        "dma.alloc",
        "dma.slice",
        "dma.deslice",
        "dma.free",
    ]
    _assert_expr_equal(summary.op_costs[1].read_bytes, sp.Integer(8))
    _assert_expr_equal(summary.op_costs[1].write_bytes, sp.Integer(8))
    _assert_expr_equal(summary.op_costs[2].read_bytes, sp.Integer(8))
    _assert_expr_equal(summary.op_costs[2].write_bytes, sp.Integer(8))
    _assert_expr_equal(summary.total_compute, sp.Integer(0))
    _assert_expr_equal(summary.total_read_bytes, sp.Integer(16))
    _assert_expr_equal(summary.total_write_bytes, sp.Integer(16))
    traffic = _value_traffic_map(summary)
    expected_keys = {f"arg{index}" for index in range(len(arg_types))}
    expected_keys.update({"op0.result0", "op2.result0"})
    assert set(traffic.keys()) == expected_keys
