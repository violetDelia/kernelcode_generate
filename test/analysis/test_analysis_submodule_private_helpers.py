"""Analysis compute/memory submodule private helper regression tests.

创建者: jcc你莫辜负
最后修改人: jcc你莫辜负

功能说明:
- 按实际 diff 直接覆盖 `analysis.compute` / `analysis.memory` 子模块的 private helper 与 analyzer 分支。
- 这些 pytest 只用于 diff 反推自测，不依赖 expectation 资产。

使用示例:
- pytest -q test/analysis/test_analysis_submodule_private_helpers.py

关联文件:
- 功能实现: kernel_gen/analysis/compute/__init__.py
- 功能实现: kernel_gen/analysis/compute/kernel.py
- 功能实现: kernel_gen/analysis/compute/nn.py
- 功能实现: kernel_gen/analysis/compute/symbol.py
- 功能实现: kernel_gen/analysis/memory/__init__.py
- 功能实现: kernel_gen/analysis/memory/dma.py
- 功能实现: kernel_gen/analysis/memory/nn.py
- Spec 文档: spec/analysis/analysis_engine.md
- 测试文件: test/analysis/test_analysis.py
- 测试文件: test/analysis/test_analysis_private_helpers.py
- 测试文件: test/analysis/test_analysis_submodule_private_helpers.py
"""

from __future__ import annotations

import importlib
import sys
from pathlib import Path
from types import SimpleNamespace

import sympy as sp
import pytest
from xdsl.dialects import arith
from xdsl.dialects.builtin import (
    ArrayAttr,
    BFloat16Type,
    Float16Type,
    Float32Type,
    Float64Type,
    IntAttr,
    IntegerAttr,
    IntegerType,
    StringAttr,
    UnrealizedConversionCastOp,
    f32,
    i1,
    i32,
    i64,
)
from xdsl.ir import Block
from xdsl.utils.exceptions import VerifyException

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

analysis_tests = importlib.import_module("test.analysis.test_analysis")

import kernel_gen.analysis.compute as compute_module
import kernel_gen.analysis.compute.kernel as compute_kernel_module
import kernel_gen.analysis.compute.nn as compute_nn_module
import kernel_gen.analysis.compute.symbol as compute_symbol_module
import kernel_gen.analysis.memory as memory_module
import kernel_gen.analysis.memory.dma as memory_dma_module
import kernel_gen.analysis.memory.nn as memory_nn_module

from kernel_gen.analysis.analysis import AnalysisConfig, AnalysisError
from kernel_gen.analysis.compute import ComputeKind
from kernel_gen.analysis.memory import MemoryPath
from kernel_gen.analysis.memory.dma import DmaMemoryAnalysis
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
    NnBroadcastOp,
    NnCastOp,
    NnEqOp,
    NnGeOp,
    NnGtOp,
    NnLeOp,
    NnLtOp,
    NnMatmulOp,
    NnMemorySpaceAttr,
    NnMemoryType,
    NnMulOp,
    NnNeOp,
    NnReduceMaxOp,
    NnReduceMinOp,
    NnReduceSumOp,
    NnSelectOp,
    NnSoftmaxOp,
    NnSubOp,
    NnTransposeOp,
    NnTrueDivOp,
    NnImg2col1dOp,
    NnImg2col2dOp,
)
from kernel_gen.dialect.symbol import SymbolConstOp, SymbolValueType


def _mem(
    shape: list[object],
    element_type: object = f32,
    space_name: str = "global",
    stride: list[object] | None = None,
) -> NnMemoryType:
    return analysis_tests._make_memory_type(shape, element_type, space_name, stride)


def _ns_value(value_type: object) -> SimpleNamespace:
    return SimpleNamespace(type=value_type)


def _ns_op(
    name: str,
    operands: list[object],
    result_types: list[object],
    attributes: dict[str, object] | None = None,
) -> SimpleNamespace:
    return SimpleNamespace(
        name=name,
        operands=list(operands),
        results=[SimpleNamespace(type=result_type) for result_type in result_types],
        attributes=attributes or {},
        properties={},
    )


def _scalar_const(value: int, width: int = 64):
    return arith.ConstantOp(IntegerAttr.from_int_and_width(value, width))


# AN-SUB-001
# 创建者: jcc你莫辜负
# 最后更改: jcc你莫辜负
# 测试目的: 验证 compute/memory registry、normalize key 与 default 注册器的真实分支。
# 使用示例: pytest -q test/analysis/test_analysis_submodule_private_helpers.py -k registry
# 对应功能实现文件路径: kernel_gen/analysis/compute/__init__.py
# 对应功能实现文件路径: kernel_gen/analysis/memory/__init__.py
# 对应测试文件路径: test/analysis/test_analysis_submodule_private_helpers.py
def test_analysis_registry_helpers(monkeypatch: pytest.MonkeyPatch) -> None:
    for module, prefix in (
        (compute_module, "compute"),
        (memory_module, "memory"),
    ):
        monkeypatch.setattr(module, f"_DEFAULT_{prefix.upper()}_ANALYZERS", [], raising=False)
        monkeypatch.setattr(module, f"_CUSTOM_{prefix.upper()}_ANALYZERS", [], raising=False)
        monkeypatch.setattr(module, f"_{prefix.upper()}_OP_ANALYZERS", {}, raising=False)
        monkeypatch.setattr(module, "_DEFAULT_REGISTERED", False, raising=False)

        registry: list[object] = []

        def demo_analyzer(op: object, config: AnalysisConfig) -> object | None:
            return None

        assert module._register_analyzer(demo_analyzer, registry) is demo_analyzer
        assert module._register_analyzer(demo_analyzer, registry) is demo_analyzer
        assert registry == [demo_analyzer]

        assert module._normalize_op_keys("nn.add") == ("nn.add",)
        assert module._normalize_op_keys(SimpleNamespace(name="nn.sub")) == ("nn.sub",)
        assert module._normalize_op_keys(("nn.add", SimpleNamespace(name="nn.sub"))) == ("nn.add", "nn.sub")
        with pytest.raises(TypeError, match="unsupported op key"):
            module._normalize_op_keys(object())
        with pytest.raises(ValueError, match="at least one op key"):
            module._normalize_op_keys(())

        decorator = module.register_compute if prefix == "compute" else module.register_memory
        decorated = decorator("test.op")(demo_analyzer)
        assert decorated is demo_analyzer
        with pytest.raises(ValueError, match=f"{prefix} analyzer already registered"):
            decorator("test.op")(lambda op, config: None)

        analyzers = module.iter_compute_analyzers() if prefix == "compute" else module.iter_memory_analyzers()
        assert analyzers
        analyzers_again = module.iter_compute_analyzers() if prefix == "compute" else module.iter_memory_analyzers()
        assert analyzers_again == analyzers

        op = SimpleNamespace(name="test.op")
        matched = module.iter_compute_analyzers_for_op(op) if prefix == "compute" else module.iter_memory_analyzers_for_op(op)
        assert isinstance(matched, tuple)

        if prefix == "compute":
            assert module.__getattr__("analyze_scalar_kernel_op") is compute_kernel_module.analyze_scalar_kernel_op
            with pytest.raises(AttributeError):
                module.__getattr__("missing")


# AN-SUB-002
# 创建者: jcc你莫辜负
# 最后更改: jcc你莫辜负
# 测试目的: 验证 compute kernel/symbol helper 的结果归属、dtype 回退与分支语义。
# 使用示例: pytest -q test/analysis/test_analysis_submodule_private_helpers.py -k kernel_and_symbol
# 对应功能实现文件路径: kernel_gen/analysis/compute/kernel.py
# 对应功能实现文件路径: kernel_gen/analysis/compute/symbol.py
# 对应测试文件路径: test/analysis/test_analysis_submodule_private_helpers.py
def test_compute_kernel_and_symbol_helpers() -> None:
    compute_cfg = AnalysisConfig(enable_compute=True, enable_memory=True)
    no_compute_cfg = AnalysisConfig(enable_compute=False, enable_memory=False)

    scalar_result = _ns_value(i32)
    scalar_op = _ns_op("kernel.binary_elewise", [], [i32])
    scalar_op.results = [scalar_result]
    analyzed = compute_kernel_module.analyze_scalar_kernel_op(scalar_op, compute_cfg)
    assert analyzed is not None
    assert analyzed.compute_items[0].kind is ComputeKind.SCALAR
    assert compute_kernel_module.analyze_scalar_kernel_op(SimpleNamespace(name="kernel.fake", results=[scalar_result]), compute_cfg) is None
    assert compute_kernel_module.analyze_scalar_kernel_op(SimpleNamespace(name="kernel.binary_elewise", results=[]), compute_cfg) is None
    assert compute_kernel_module.analyze_scalar_kernel_op(SimpleNamespace(name="kernel.binary_elewise", results=[_ns_value(_mem([IntAttr(2)], i32, "global"))]), compute_cfg) is None
    analyzed_off = compute_kernel_module.analyze_scalar_kernel_op(scalar_op, no_compute_cfg)
    assert analyzed_off is not None
    assert analyzed_off.compute == sp.Integer(0)

    assert compute_symbol_module._symbol_result_dtype(SimpleNamespace(results=[])) == "symbol"
    assert compute_symbol_module._symbol_result_dtype(SimpleNamespace(results=[_ns_value(i32)])) == "i32"

    generic_symbol = SimpleNamespace(name="symbol.add", results=[_ns_value(i32)])
    generic_result = compute_symbol_module.analyze_symbol_op(generic_symbol, compute_cfg)
    assert generic_result is not None
    assert generic_result.compute_items[0].kind is ComputeKind.SCALAR

    to_int = SimpleNamespace(name="symbol.to_int", results=[_ns_value(i32)])
    to_int_result = compute_symbol_module.analyze_symbol_op(to_int, AnalysisConfig(enable_compute=False, enable_memory=True))
    assert to_int_result is not None
    assert to_int_result.compute == sp.Integer(0)
    assert to_int_result.read_bytes == sp.Integer(1)
    assert to_int_result.memory_items[0].path is MemoryPath.GM_TO_GM

    assert compute_symbol_module.analyze_symbol_op(SimpleNamespace(name="symbol.get_dim", results=[]), compute_cfg) is None
    assert compute_symbol_module.analyze_symbol_op(SimpleNamespace(name="symbol.get_stride", results=[]), compute_cfg) is None
    assert compute_symbol_module.analyze_symbol_op(SimpleNamespace(name="other.op", results=[]), compute_cfg) is None


# AN-SUB-003
# 创建者: jcc你莫辜负
# 最后更改: jcc你莫辜负
# 测试目的: 验证 compute/memory nn analyzer shared helper 与主分支的成功/失败路径。
# 使用示例: pytest -q test/analysis/test_analysis_submodule_private_helpers.py -k nn_helpers
# 对应功能实现文件路径: kernel_gen/analysis/compute/nn.py
# 对应功能实现文件路径: kernel_gen/analysis/memory/nn.py
# 对应测试文件路径: test/analysis/test_analysis_submodule_private_helpers.py
def test_compute_and_memory_nn_helpers() -> None:
    compute_on = AnalysisConfig(enable_compute=True, enable_memory=False)
    compute_off = AnalysisConfig(enable_compute=False, enable_memory=False)
    memory_on = AnalysisConfig(enable_compute=False, enable_memory=True)
    memory_off = AnalysisConfig(enable_compute=False, enable_memory=False)

    for module in (compute_nn_module, memory_nn_module):
        attr_op = SimpleNamespace(name="nn.softmax", attributes={"axis": IntegerAttr.from_int_and_width(3, 64)})
        assert module._get_i64_attr(attr_op, "axis") == 3
        attr_op.attributes["axis"] = IntAttr(4)
        assert module._get_i64_attr(attr_op, "axis") == 4
        with pytest.raises(AnalysisError, match="must be integer"):
            module._get_i64_attr(SimpleNamespace(name="nn.softmax", attributes={}), "axis")

        assert module._is_symbol_int_type(SymbolValueType.from_expr("K"))
        assert module._is_int_or_symbol_type(i32)
        assert module._is_int_or_symbol_type(SymbolValueType.from_expr("K"))

        const_op = _scalar_const(4)
        cast_op = UnrealizedConversionCastOp(operands=[const_op.result], result_types=[i32])
        symbol_const = SymbolConstOp(7)
        block_arg = Block(arg_types=[i32]).args[0]
        assert module._static_int_from_operand(const_op.result) == 4
        assert module._static_int_from_operand(cast_op.results[0]) == 4
        assert module._static_int_from_operand(symbol_const.result) == 7
        assert module._static_int_from_operand(block_arg) is None

        assert module._verify_img2col_param_operands(
            [SymbolConstOp(3).result, SymbolConstOp(1).result, SymbolConstOp(1).result],
            allow_zero=False,
            type_error_phrase="bad type",
            value_error_phrase="bad value",
        ) == [3, 1, 1]
        assert module._verify_img2col_param_operands(
            [SymbolConstOp(0).result],
            allow_zero=True,
            type_error_phrase="bad type",
            value_error_phrase="bad value",
        ) == [0]
        with pytest.raises(AnalysisError, match="bad type"):
            module._verify_img2col_param_operands(
                [Block(arg_types=[f32]).args[0]],
                allow_zero=False,
                type_error_phrase="bad type",
                value_error_phrase="bad value",
            )
        with pytest.raises(AnalysisError, match="bad value"):
            module._verify_img2col_param_operands(
                [SymbolConstOp(0).result],
                allow_zero=False,
                type_error_phrase="bad type",
                value_error_phrase="bad value",
            )

        assert str(module._img2col_output_dim(sp.Integer(8), 3, 1, 1, 1, 1)) == "8"

    shape_type = _mem([IntAttr(2), IntAttr(3)], i32, "global")
    compare_result_type = _mem([IntAttr(2), IntAttr(3)], i1, "global")
    element_op = _ns_op("nn.add", [_ns_value(shape_type), _ns_value(shape_type)], [shape_type])
    mixed_rhs_op = _ns_op("nn.add", [_ns_value(shape_type), _ns_value(i32)], [shape_type])
    mixed_lhs_op = _ns_op("nn.add", [_ns_value(i32), _ns_value(shape_type)], [shape_type])
    compare_op = _ns_op("nn.eq", [_ns_value(shape_type), _ns_value(shape_type)], [compare_result_type])
    bad_compare_op = _ns_op("nn.eq", [_ns_value(shape_type), _ns_value(shape_type)], [shape_type])
    bad_element_op = _ns_op("nn.add", [_ns_value(i32), _ns_value(i32)], [shape_type])
    bad_shape_op = _ns_op("nn.add", [_ns_value(shape_type), _ns_value(shape_type)], [_mem([StringAttr("?")], i32, "global")])

    for module, compute_cfg, memory_cfg in (
        (compute_nn_module, compute_on, memory_off),
        (memory_nn_module, compute_off, memory_on),
    ):
        analyze_elementwise = (
            module.analyze_nn_elementwise_op
            if module is compute_nn_module
            else module.analyze_nn_memory_op
        )
        active_cfg = compute_cfg if module is compute_nn_module else memory_cfg
        both = analyze_elementwise(element_op, active_cfg)
        assert both is not None
        mixed_rhs = analyze_elementwise(mixed_rhs_op, active_cfg)
        assert mixed_rhs is not None
        mixed_lhs = analyze_elementwise(mixed_lhs_op, active_cfg)
        assert mixed_lhs is not None
        compare = analyze_elementwise(compare_op, active_cfg)
        assert compare is not None
        if module is compute_nn_module:
            assert compare.compute_items[0].kind is ComputeKind.VECTOR
        else:
            assert compare.read_bytes > 0
            assert compare.write_bytes == sp.Integer(6)

        with pytest.raises(AnalysisError, match="at least one nn.memory operand required"):
            analyze_elementwise(bad_element_op, active_cfg)
        with pytest.raises(AnalysisError, match="compare result element_type must be i1"):
            analyze_elementwise(bad_compare_op, active_cfg)
        with pytest.raises(AnalysisError, match="result shape must be supported"):
            analyze_elementwise(bad_shape_op, active_cfg)
        assert analyze_elementwise(element_op, compute_off if module is compute_nn_module else memory_off) is not None

    unary_op = _ns_op("nn.exp", [_ns_value(shape_type)], [shape_type])
    unary_bad_op = _ns_op("nn.exp", [_ns_value(i32)], [shape_type])
    unary_shape_bad = _ns_op("nn.exp", [_ns_value(shape_type)], [_mem([IntAttr(2), IntAttr(4)], i32, "global")])
    for module, cfg in ((compute_nn_module, compute_on), (memory_nn_module, memory_on)):
        unary = module.analyze_nn_unary_op(unary_op, cfg) if module is compute_nn_module else module.analyze_nn_memory_op(unary_op, cfg)
        assert unary is not None
        with pytest.raises(AnalysisError, match="operand must be nn.memory"):
            (module.analyze_nn_unary_op if module is compute_nn_module else module.analyze_nn_memory_op)(unary_bad_op, cfg)
        with pytest.raises(AnalysisError, match="shape mismatch"):
            (module.analyze_nn_unary_op if module is compute_nn_module else module.analyze_nn_memory_op)(unary_shape_bad, cfg)
        assert (module.analyze_nn_unary_op if module is compute_nn_module else module.analyze_nn_memory_op)(unary_op, compute_off if module is compute_nn_module else memory_off) is not None

    soft_type = _mem([IntAttr(2), IntAttr(3)], f32, "global")
    soft_op = _ns_op("nn.softmax", [_ns_value(soft_type)], [soft_type], {"axis": IntegerAttr.from_int_and_width(-1, 64)})
    soft_bad_axis = _ns_op("nn.softmax", [_ns_value(soft_type)], [soft_type], {"axis": IntegerAttr.from_int_and_width(3, 64)})
    soft_bad_type = _ns_op("nn.softmax", [_ns_value(_mem([IntAttr(2), IntAttr(3)], i32, "global"))], [_mem([IntAttr(2), IntAttr(3)], i32, "global")], {"axis": IntAttr(1)})
    for module, cfg in ((compute_nn_module, compute_on), (memory_nn_module, memory_on)):
        soft = module.analyze_nn_softmax_op(soft_op, cfg) if module is compute_nn_module else module.analyze_nn_memory_op(soft_op, cfg)
        assert soft is not None
        with pytest.raises(AnalysisError, match="axis out of range"):
            (module.analyze_nn_softmax_op if module is compute_nn_module else module.analyze_nn_memory_op)(soft_bad_axis, cfg)
        with pytest.raises(AnalysisError, match="element_type must be float"):
            (module.analyze_nn_softmax_op if module is compute_nn_module else module.analyze_nn_memory_op)(soft_bad_type, cfg)
        assert (module.analyze_nn_softmax_op if module is compute_nn_module else module.analyze_nn_memory_op)(soft_op, compute_off if module is compute_nn_module else memory_off) is not None

    reduce_input = _mem([IntAttr(2), IntAttr(3)], f32, "global")
    reduce_result = _mem([IntAttr(2)], f32, "global")
    reduce_op = _ns_op(
        "nn.reduce_sum",
        [_ns_value(reduce_input)],
        [reduce_result],
        {"axes": ArrayAttr([IntegerAttr.from_int_and_width(1, 64)]), "keepdim": IntAttr(0)},
    )
    reduce_bad = _ns_op("nn.reduce_sum", [_ns_value(reduce_input)], [_mem([IntAttr(2)], i32, "global")], {"axes": ArrayAttr([IntegerAttr.from_int_and_width(1, 64)]), "keepdim": IntAttr(0)})
    for module, cfg in ((compute_nn_module, compute_on), (memory_nn_module, memory_on)):
        reduced = module.analyze_nn_reduce_op(reduce_op, cfg) if module is compute_nn_module else module.analyze_nn_memory_op(reduce_op, cfg)
        assert reduced is not None
        with pytest.raises(AnalysisError, match="operand/result element_type mismatch"):
            (module.analyze_nn_reduce_op if module is compute_nn_module else module.analyze_nn_memory_op)(reduce_bad, cfg)
        assert (module.analyze_nn_reduce_op if module is compute_nn_module else module.analyze_nn_memory_op)(reduce_op, compute_off if module is compute_nn_module else memory_off) is not None

    lhs = _mem([IntAttr(2), IntAttr(3)], f32, "global")
    rhs = _mem([IntAttr(3), IntAttr(4)], f32, "global")
    out = _mem([IntAttr(2), IntAttr(4)], f32, "global")
    matmul_op = _ns_op("nn.matmul", [_ns_value(lhs), _ns_value(rhs)], [out])
    matmul_bad_rank = _ns_op("nn.matmul", [_ns_value(_mem([IntAttr(2)], f32, "global")), _ns_value(rhs)], [out])
    matmul_bad_inner = _ns_op("nn.matmul", [_ns_value(lhs), _ns_value(_mem([IntAttr(5), IntAttr(4)], f32, "global"))], [out])
    matmul_bad_shape = _ns_op("nn.matmul", [_ns_value(lhs), _ns_value(rhs)], [_mem([IntAttr(2), IntAttr(5)], f32, "global")])
    matmul_bad_type = _ns_op("nn.matmul", [_ns_value(lhs), _ns_value(_mem([IntAttr(3), IntAttr(4)], i32, "global"))], [out])
    for module, cfg in ((compute_nn_module, compute_on), (memory_nn_module, memory_on)):
        matmul = module.analyze_nn_matmul_ir_op(matmul_op, cfg) if module is compute_nn_module else module.analyze_nn_memory_op(matmul_op, cfg)
        assert matmul is not None
        with pytest.raises(AnalysisError, match="requires rank-2"):
            (module.analyze_nn_matmul_ir_op if module is compute_nn_module else module.analyze_nn_memory_op)(matmul_bad_rank, cfg)
        with pytest.raises(AnalysisError, match="inner dimension mismatch"):
            (module.analyze_nn_matmul_ir_op if module is compute_nn_module else module.analyze_nn_memory_op)(matmul_bad_inner, cfg)
        with pytest.raises(AnalysisError, match="output shape mismatch"):
            (module.analyze_nn_matmul_ir_op if module is compute_nn_module else module.analyze_nn_memory_op)(matmul_bad_shape, cfg)
        with pytest.raises(AnalysisError, match="operand/result element_type must match"):
            (module.analyze_nn_matmul_ir_op if module is compute_nn_module else module.analyze_nn_memory_op)(matmul_bad_type, cfg)
        assert (module.analyze_nn_matmul_ir_op if module is compute_nn_module else module.analyze_nn_memory_op)(matmul_op, compute_off if module is compute_nn_module else memory_off) is not None

    img1_input = _mem([IntAttr(2), IntAttr(3), IntAttr(8)], f32, "global")
    img1_result = _mem([IntAttr(2), IntAttr(3), IntAttr(3), IntAttr(8)], f32, "global")
    kw = SymbolConstOp(3).result
    sw = SymbolConstOp(1).result
    dw = SymbolConstOp(1).result
    pl = SymbolConstOp(1).result
    pr = SymbolConstOp(1).result
    img1_op = _ns_op("nn.img2col1d", [_ns_value(img1_input), kw, sw, dw, pl, pr], [img1_result])
    img1_bad = _ns_op("nn.img2col1d", [_ns_value(_mem([IntAttr(2), IntAttr(3)], f32, "global")), kw, sw, dw, pl, pr], [img1_result])
    img2_input = _mem([IntAttr(2), IntAttr(3), IntAttr(8), IntAttr(8)], f32, "global")
    img2_result = _mem([IntAttr(2), IntAttr(3), IntAttr(3), IntAttr(3), IntAttr(8), IntAttr(8)], f32, "global")
    kh = SymbolConstOp(3).result
    kw2 = SymbolConstOp(3).result
    sh = SymbolConstOp(1).result
    sw2 = SymbolConstOp(1).result
    dh = SymbolConstOp(1).result
    dw2 = SymbolConstOp(1).result
    ph = SymbolConstOp(1).result
    pw = SymbolConstOp(1).result
    pl2 = SymbolConstOp(1).result
    pr2 = SymbolConstOp(1).result
    img2_op = _ns_op("nn.img2col2d", [_ns_value(img2_input), kh, kw2, sh, sw2, dh, dw2, ph, pw, pl2, pr2], [img2_result])
    img2_bad = _ns_op("nn.img2col2d", [_ns_value(_mem([IntAttr(2), IntAttr(3), IntAttr(8)], f32, "global")), kh, kw2, sh, sw2, dh, dw2, ph, pw, pl2, pr2], [img2_result])
    for module, cfg in ((compute_nn_module, compute_on), (memory_nn_module, memory_on)):
        img1 = module.analyze_nn_img2col_op(img1_op, cfg) if module is compute_nn_module else module.analyze_nn_memory_op(img1_op, cfg)
        assert img1 is not None
        img2 = module.analyze_nn_img2col_op(img2_op, cfg) if module is compute_nn_module else module.analyze_nn_memory_op(img2_op, cfg)
        assert img2 is not None
        with pytest.raises(AnalysisError, match="requires rank-3 input"):
            (module.analyze_nn_img2col_op if module is compute_nn_module else module.analyze_nn_memory_op)(img1_bad, cfg)
        with pytest.raises(AnalysisError, match="requires rank-4 input"):
            (module.analyze_nn_img2col_op if module is compute_nn_module else module.analyze_nn_memory_op)(img2_bad, cfg)
        assert (module.analyze_nn_img2col_op if module is compute_nn_module else module.analyze_nn_memory_op)(img1_op, compute_off if module is compute_nn_module else memory_off) is not None


# AN-SUB-004
# 创建者: jcc你莫辜负
# 最后更改: jcc你莫辜负
# 测试目的: 验证 DMA memory helper、公开 op 分支与 wrapper error mapping。
# 使用示例: pytest -q test/analysis/test_analysis_submodule_private_helpers.py -k dma_helpers
# 对应功能实现文件路径: kernel_gen/analysis/memory/dma.py
# 对应功能实现文件路径: kernel_gen/analysis/memory/__init__.py
# 对应测试文件路径: test/analysis/test_analysis_submodule_private_helpers.py
def test_memory_dma_helpers_and_wrapper(monkeypatch: pytest.MonkeyPatch) -> None:
    path_latency = {MemoryPath.GM_TO_LM: sp.Integer(20), MemoryPath.LM_TO_GM: sp.Integer(30)}
    path_bandwidth = {MemoryPath.GM_TO_LM: sp.Integer(10), MemoryPath.LM_TO_GM: sp.Integer(20)}
    dtype_overrides = {"f32": 8}

    contig_type = _mem([IntAttr(2), IntAttr(3)], f32, "global", stride=[IntAttr(3), IntAttr(1)])
    noncontig_type = _mem([IntAttr(2), IntAttr(3)], f32, "global", stride=[IntAttr(2), IntAttr(1)])
    global_type = _mem([IntAttr(2), IntAttr(3)], f32, "global")
    local_type = _mem([IntAttr(2), IntAttr(3)], f32, "local")

    assert memory_dma_module._space_token_from_mem_type(global_type) == "GM"
    assert memory_dma_module._space_token_from_mem_type(local_type) == "LM"
    assert memory_dma_module._memory_path_from_types(global_type, local_type) is MemoryPath.GM_TO_LM
    assert memory_dma_module._element_size(Float16Type(), None) == 2
    assert memory_dma_module._element_size(BFloat16Type(), None) == 2
    assert memory_dma_module._element_size(Float32Type(), None) == 4
    assert memory_dma_module._element_size(Float64Type(), None) == 8
    assert memory_dma_module._element_size(IntegerType(32), None) == 4
    assert memory_dma_module._element_size(IntegerType(32), {"i32": 8}) == 8
    assert memory_dma_module._element_size(StringAttr("x"), None) is None
    assert str(memory_dma_module._dim_to_expr(IntAttr(2))) == "2"
    assert str(memory_dma_module._dim_to_expr(IntegerAttr.from_int_and_width(3, 64))) == "3"
    assert str(memory_dma_module._dim_to_expr(StringAttr("N"))) == "N"
    assert memory_dma_module._dim_to_expr(StringAttr("?")) is None
    assert str(memory_dma_module._numel_from_mem_type(contig_type)) == "6"
    assert memory_dma_module._numel_from_mem_type(_mem([StringAttr("?")], f32, "global")) is None

    sym_block = Block(arg_types=[SymbolValueType.from_expr("K"), SymbolValueType.from_expr("3")])
    assert str(memory_dma_module._numel_from_symbol_values(sym_block.args)) == "3*K"
    assert memory_dma_module._numel_from_symbol_values([_ns_value(i32)]) is None

    class BrokenOp:
        name = "broken"

        def verify(self) -> None:
            raise VerifyException("boom")

    memory_dma_module._verify_public_dma_op(SimpleNamespace(verify=lambda: None))
    with pytest.raises(ValueError, match="boom"):
        memory_dma_module._verify_public_dma_op(BrokenOp())

    item = memory_dma_module._build_memory_item_tuple(
        MemoryPath.GM_TO_LM,
        "read",
        sp.Integer(32),
        path_latency_ns=path_latency,
        path_bandwidth=path_bandwidth,
    )
    assert item[0] is MemoryPath.GM_TO_LM
    assert item[-1] == sp.Rational(116, 5)

    alloc = DmaAllocOp([], contig_type)
    noncontig_alloc = DmaAllocOp([], noncontig_type)
    assert isinstance(memory_dma_module.analyze_dma_op(alloc, path_latency_ns=path_latency, path_bandwidth=path_bandwidth, dtype_size_overrides=dtype_overrides), DmaMemoryAnalysis)
    assert memory_dma_module.analyze_dma_op(noncontig_alloc, path_latency_ns=path_latency, path_bandwidth=path_bandwidth, dtype_size_overrides=dtype_overrides) is None

    free_op = DmaFreeOp(alloc.result)
    view_source = Block(arg_types=[contig_type]).args[0]
    view_offsets = [SymbolConstOp(0).result, SymbolConstOp(0).result]
    view_shape = [SymbolConstOp(2).result, SymbolConstOp(3).result]
    view_stride = [SymbolConstOp(3).result, SymbolConstOp(1).result]
    view_op = DmaViewOp(view_source, view_offsets, view_shape, view_stride, contig_type)


# AN-SUB-005
# 创建者: jcc你莫辜负
# 最后更改: jcc你莫辜负
# 测试目的: 补齐 compute/memory nn analyzer 的 fallback、错误短路与 direct op 分支。
# 使用示例: pytest -q test/analysis/test_analysis_submodule_private_helpers.py -k fallback_and_direct
# 对应功能实现文件路径: kernel_gen/analysis/compute/nn.py
# 对应功能实现文件路径: kernel_gen/analysis/memory/nn.py
# 对应功能实现文件路径: kernel_gen/analysis/memory/dma.py
# 对应测试文件路径: test/analysis/test_analysis_submodule_private_helpers.py
def test_compute_and_memory_nn_fallback_and_direct_branches(monkeypatch: pytest.MonkeyPatch) -> None:
    compute_cfg = AnalysisConfig(enable_compute=True, enable_memory=False)
    memory_cfg = AnalysisConfig(enable_compute=False, enable_memory=True)
    path_latency = {MemoryPath.GM_TO_LM: sp.Integer(20), MemoryPath.LM_TO_GM: sp.Integer(30)}
    path_bandwidth = {MemoryPath.GM_TO_LM: sp.Integer(10), MemoryPath.LM_TO_GM: sp.Integer(20)}
    dtype_overrides = {"f32": 8}

    const_owner = SimpleNamespace(
        name="arith.constant",
        attributes={},
        properties={"value": IntegerAttr.from_int_and_width(6, 64)},
    )
    assert compute_nn_module._static_int_from_operand(SimpleNamespace(owner=const_owner)) == 6
    assert compute_nn_module._static_int_from_operand(SimpleNamespace(owner=SimpleNamespace(name="mystery", attributes={}, properties={}))) is None
    assert memory_nn_module._static_int_from_operand(SimpleNamespace(owner=SimpleNamespace(name="mystery", attributes={}, properties={}))) is None

    empty = module_empty = []
    symbol_operand = Block(arg_types=[SymbolValueType.from_expr("K")]).args[0]
    negative_operand = SymbolConstOp(-1).result
    for module in (compute_nn_module, memory_nn_module):
        assert module._verify_img2col_param_operands(
            empty,
            allow_zero=False,
            type_error_phrase="bad type",
            value_error_phrase="bad value",
        ) == []
        assert module._verify_img2col_param_operands(
            [symbol_operand],
            allow_zero=False,
            type_error_phrase="bad type",
            value_error_phrase="bad value",
        ) == [None]
        with pytest.raises(AnalysisError, match="bad value"):
            module._verify_img2col_param_operands(
                [negative_operand],
                allow_zero=True,
                type_error_phrase="bad type",
                value_error_phrase="bad value",
            )

    mem_23 = _mem([IntAttr(2), IntAttr(3)], i32, "global")
    mem_24 = _mem([IntAttr(2), IntAttr(4)], i32, "global")
    mem_23_f32 = _mem([IntAttr(2), IntAttr(3)], f32, "global")
    mem_23_i1 = _mem([IntAttr(2), IntAttr(3)], i1, "global")
    mem_rank0 = _mem((), f32, "global")
    mem_unknown_shape = _mem([IntAttr(2), StringAttr("?")], f32, "global")

    for module, compute_on, analyzer_name in (
        (compute_nn_module, compute_cfg, "compute"),
        (memory_nn_module, memory_cfg, "memory"),
    ):
        elementwise = (
            module.analyze_nn_elementwise_op
            if module is compute_nn_module
            else module.analyze_nn_memory_op
        )
        unary = module.analyze_nn_unary_op if module is compute_nn_module else module.analyze_nn_memory_op
        softmax = (
            module.analyze_nn_softmax_op
            if module is compute_nn_module
            else module.analyze_nn_memory_op
        )
        reduce = module.analyze_nn_reduce_op if module is compute_nn_module else module.analyze_nn_memory_op
        matmul = (
            module.analyze_nn_matmul_ir_op
            if module is compute_nn_module
            else module.analyze_nn_memory_op
        )
        img2col = module.analyze_nn_img2col_op if module is compute_nn_module else module.analyze_nn_memory_op

        assert elementwise(_ns_op("nn.other", [], []), compute_on) is None
        assert unary(_ns_op("nn.other", [], []), compute_on) is None
        assert softmax(_ns_op("nn.other", [], []), compute_on) is None
        assert reduce(_ns_op("nn.other", [], []), compute_on) is None
        assert matmul(_ns_op("nn.other", [], []), compute_on) is None
        assert img2col(_ns_op("nn.other", [], []), compute_on) is None

        with pytest.raises(AnalysisError, match="2 operands and 1 result"):
            elementwise(_ns_op("nn.add", [_ns_value(mem_23)], [mem_23]), compute_on)
        with pytest.raises(AnalysisError, match="nn op result must be nn.memory"):
            elementwise(_ns_op("nn.add", [_ns_value(mem_23), _ns_value(mem_23)], [i32]), compute_on)
        with pytest.raises(AnalysisError, match="at least one nn.memory operand required"):
            elementwise(_ns_op("nn.add", [_ns_value(i32), _ns_value(i32)], [mem_23]), compute_on)
        with pytest.raises(AnalysisError, match="result shape must match memory operand"):
            elementwise(_ns_op("nn.add", [_ns_value(mem_23), _ns_value(mem_24)], [mem_23]), compute_on)
        with pytest.raises(AnalysisError, match="compare result element_type must be i1"):
            elementwise(_ns_op("nn.eq", [_ns_value(mem_23), _ns_value(mem_23)], [mem_23]), compute_on)
        with pytest.raises(AnalysisError, match="result shape must be supported"):
            elementwise(_ns_op("nn.add", [_ns_value(mem_23), _ns_value(mem_23)], [mem_unknown_shape]), compute_on)

        with pytest.raises(AnalysisError, match="1 operand and 1 result"):
            unary(_ns_op("nn.exp", [], [mem_23_f32]), compute_on)
        with pytest.raises(AnalysisError, match="operand must be nn.memory"):
            unary(_ns_op("nn.exp", [_ns_value(i32)], [mem_23_f32]), compute_on)
        with pytest.raises(AnalysisError, match="result must be nn.memory"):
            unary(_ns_op("nn.exp", [_ns_value(mem_23_f32)], [i32]), compute_on)
        with pytest.raises(AnalysisError, match="shape mismatch"):
            unary(_ns_op("nn.exp", [_ns_value(mem_23_f32)], [mem_24]), compute_on)
        with pytest.raises(AnalysisError, match="element_type mismatch"):
            unary(_ns_op("nn.exp", [_ns_value(mem_23)], [mem_23_f32]), compute_on)
        with pytest.raises(AnalysisError, match="shape unsupported"):
            unary(_ns_op("nn.exp", [_ns_value(mem_unknown_shape)], [mem_unknown_shape]), compute_on)

        with pytest.raises(AnalysisError, match="must have 1 operand and 1 result"):
            softmax(_ns_op("nn.softmax", [], [mem_23_f32], {"axis": IntegerAttr.from_int_and_width(0, 64)}), compute_on)
        with pytest.raises(AnalysisError, match="operand must be nn.memory"):
            softmax(_ns_op("nn.softmax", [_ns_value(i32)], [mem_23_f32], {"axis": IntegerAttr.from_int_and_width(0, 64)}), compute_on)
        with pytest.raises(AnalysisError, match="result must be nn.memory"):
            softmax(_ns_op("nn.softmax", [_ns_value(mem_23_f32)], [i32], {"axis": IntegerAttr.from_int_and_width(0, 64)}), compute_on)
        with pytest.raises(AnalysisError, match="input/result shape mismatch"):
            softmax(_ns_op("nn.softmax", [_ns_value(mem_23_f32)], [mem_24], {"axis": IntegerAttr.from_int_and_width(0, 64)}), compute_on)
        with pytest.raises(AnalysisError, match="input/result element_type mismatch"):
            softmax(_ns_op("nn.softmax", [_ns_value(mem_23)], [mem_23_f32], {"axis": IntegerAttr.from_int_and_width(0, 64)}), compute_on)
        with pytest.raises(AnalysisError, match="input rank must be positive"):
            softmax(_ns_op("nn.softmax", [_ns_value(mem_rank0)], [mem_rank0], {"axis": IntegerAttr.from_int_and_width(0, 64)}), compute_on)
        with pytest.raises(AnalysisError, match="axis out of range"):
            softmax(_ns_op("nn.softmax", [_ns_value(mem_23_f32)], [mem_23_f32], {"axis": IntegerAttr.from_int_and_width(2, 64)}), compute_on)
        with pytest.raises(AnalysisError, match="shape unsupported"):
            softmax(_ns_op("nn.softmax", [_ns_value(mem_unknown_shape)], [mem_unknown_shape], {"axis": IntegerAttr.from_int_and_width(0, 64)}), compute_on)

        with pytest.raises(AnalysisError, match="must have 1 operand and 1 result"):
            reduce(_ns_op("nn.reduce_sum", [], [mem_23_f32], {"axes": ArrayAttr([IntegerAttr.from_int_and_width(1, 64)]), "keepdim": IntAttr(0)}), compute_on)
        with pytest.raises(AnalysisError, match="operand must be nn.memory"):
            reduce(_ns_op("nn.reduce_sum", [_ns_value(i32)], [mem_23_f32], {"axes": ArrayAttr([IntegerAttr.from_int_and_width(1, 64)]), "keepdim": IntAttr(0)}), compute_on)
        with pytest.raises(AnalysisError, match="result must be nn.memory"):
            reduce(_ns_op("nn.reduce_sum", [_ns_value(mem_23_f32)], [i32], {"axes": ArrayAttr([IntegerAttr.from_int_and_width(1, 64)]), "keepdim": IntAttr(0)}), compute_on)
        with pytest.raises(AnalysisError, match="operand/result element_type mismatch"):
            reduce(_ns_op("nn.reduce_sum", [_ns_value(mem_23)], [mem_23_f32], {"axes": ArrayAttr([IntegerAttr.from_int_and_width(1, 64)]), "keepdim": IntAttr(0)}), compute_on)
        with pytest.raises(AnalysisError, match="shape unsupported"):
            reduce(_ns_op("nn.reduce_sum", [_ns_value(mem_unknown_shape)], [mem_unknown_shape], {"axes": ArrayAttr([IntegerAttr.from_int_and_width(0, 64)]), "keepdim": IntAttr(0)}), compute_on)

        with pytest.raises(AnalysisError, match="must have 2 operands and 1 result"):
            matmul(_ns_op("nn.matmul", [_ns_value(mem_23)], [mem_23_f32]), compute_on)
        with pytest.raises(AnalysisError, match="operands must be nn.memory"):
            matmul(_ns_op("nn.matmul", [_ns_value(i32), _ns_value(mem_23)], [mem_23_f32]), compute_on)
        with pytest.raises(AnalysisError, match="result must be nn.memory"):
            matmul(_ns_op("nn.matmul", [_ns_value(mem_23), _ns_value(mem_24)], [i32]), compute_on)
        with pytest.raises(AnalysisError, match="requires rank-2 tensors"):
            matmul(_ns_op("nn.matmul", [_ns_value(_mem([IntAttr(2)], f32, "global")), _ns_value(mem_24)], [mem_23_f32]), compute_on)
        with pytest.raises(AnalysisError, match="shape unsupported"):
            matmul(_ns_op("nn.matmul", [_ns_value(mem_unknown_shape), _ns_value(mem_unknown_shape)], [mem_unknown_shape]), compute_on)
        with pytest.raises(AnalysisError, match="inner dimension mismatch"):
            matmul(_ns_op("nn.matmul", [_ns_value(mem_23_f32), _ns_value(mem_24)], [mem_23_f32]), compute_on)
        with pytest.raises(AnalysisError, match="output shape mismatch"):
            matmul(
                _ns_op(
                    "nn.matmul",
                    [_ns_value(mem_23_f32), _ns_value(_mem([IntAttr(3), IntAttr(4)], f32, "global"))],
                    [_mem([IntAttr(2), IntAttr(5)], f32, "global")],
                ),
                compute_on,
            )
        with pytest.raises(AnalysisError, match="element_type must match"):
            matmul(_ns_op("nn.matmul", [_ns_value(mem_23_f32), _ns_value(_mem([IntAttr(3), IntAttr(4)], i1, "global"))], [_mem([IntAttr(2), IntAttr(4)], f32, "global")]), compute_on)

        with pytest.raises(AnalysisError, match="must have 6 operands"):
            img2col(_ns_op("nn.img2col1d", [_ns_value(mem_23_f32)], [mem_23_f32]), compute_on)
        with pytest.raises(AnalysisError, match="operand must be nn.memory"):
            img2col(
                _ns_op(
                    "nn.img2col1d",
                    [_ns_value(i32), SymbolConstOp(3).result, SymbolConstOp(1).result, SymbolConstOp(1).result, SymbolConstOp(1).result, SymbolConstOp(1).result],
                    [mem_23_f32],
                ),
                compute_on,
            )
        with pytest.raises(AnalysisError, match="result must be nn.memory"):
            img2col(
                _ns_op(
                    "nn.img2col1d",
                    [_ns_value(mem_23_f32), SymbolConstOp(3).result, SymbolConstOp(1).result, SymbolConstOp(1).result, SymbolConstOp(1).result, SymbolConstOp(1).result],
                    [i32],
                ),
                compute_on,
            )
        with pytest.raises(AnalysisError, match="requires rank-3 input"):
            img2col(
                _ns_op(
                    "nn.img2col1d",
                    [_ns_value(_mem([IntAttr(2), IntAttr(3)], f32, "global")), SymbolConstOp(3).result, SymbolConstOp(1).result, SymbolConstOp(1).result, SymbolConstOp(1).result, SymbolConstOp(1).result],
                    [mem_23_f32],
                ),
                compute_on,
            )
        with pytest.raises(AnalysisError, match="output shape invalid"):
            img2col(
                _ns_op(
                    "nn.img2col1d",
                    [_ns_value(_mem([IntAttr(1), IntAttr(1), IntAttr(1)], f32, "global")), SymbolConstOp(3).result, SymbolConstOp(1).result, SymbolConstOp(1).result, SymbolConstOp(0).result, SymbolConstOp(0).result],
                    [_mem([IntAttr(1), IntAttr(1), IntAttr(3), IntAttr(1)], f32, "global")],
                ),
                compute_on,
            )

    broadcast_result = _mem([IntAttr(2), IntAttr(3)], f32, "global")
    transpose_result = _mem([IntAttr(3), IntAttr(2)], f32, "global")
    broadcast_op = _ns_op("nn.broadcast", [_ns_value(broadcast_result)], [broadcast_result])
    transpose_op = _ns_op("nn.transpose", [_ns_value(broadcast_result)], [transpose_result])
    assert memory_nn_module.analyze_nn_memory_op(broadcast_op, memory_cfg) is not None
    assert memory_nn_module.analyze_nn_memory_op(transpose_op, memory_cfg) is not None
    with pytest.raises(AnalysisError, match="operand must be nn.memory"):
        memory_nn_module.analyze_nn_memory_op(_ns_op("nn.broadcast", [_ns_value(i32)], [broadcast_result]), memory_cfg)
    with pytest.raises(AnalysisError, match="result must be nn.memory"):
        memory_nn_module.analyze_nn_memory_op(_ns_op("nn.transpose", [_ns_value(broadcast_result)], [i32]), memory_cfg)
    with pytest.raises(AnalysisError, match="element_type mismatch"):
        memory_nn_module.analyze_nn_memory_op(
            _ns_op("nn.broadcast", [_ns_value(_mem([IntAttr(2), IntAttr(3)], i32, "global"))], [broadcast_result]),
            memory_cfg,
        )
    with pytest.raises(AnalysisError, match="shape unsupported"):
        memory_nn_module.analyze_nn_memory_op(
            _ns_op("nn.transpose", [_ns_value(mem_unknown_shape)], [mem_unknown_shape]),
            memory_cfg,
        )
    assert memory_nn_module.analyze_nn_memory_op(_ns_op("nn.other", [], []), memory_cfg) is None
    reshape_shape = [SymbolConstOp(2).result, SymbolConstOp(3).result]
    contig_type = _mem([IntAttr(2), IntAttr(3)], f32, "global", stride=[IntAttr(3), IntAttr(1)])
    view_source = Block(arg_types=[contig_type]).args[0]
    view_offsets = [SymbolConstOp(0).result, SymbolConstOp(0).result]
    view_shape = [SymbolConstOp(2).result, SymbolConstOp(3).result]
    view_stride = [SymbolConstOp(3).result, SymbolConstOp(1).result]
    reshape_op = DmaReshapeOp(view_source, reshape_shape, contig_type)
    fill_type = _mem([IntAttr(2), IntAttr(3)], i32, "global", stride=[IntAttr(3), IntAttr(1)])
    fill_value = Block(arg_types=[i32]).args[0]
    fill_target = Block(arg_types=[fill_type]).args[0]
    fill_op = DmaFillOp(fill_target, fill_value)
    free_op = DmaFreeOp(Block(arg_types=[contig_type]).args[0])
    view_op = DmaViewOp(view_source, view_offsets, view_shape, view_stride, contig_type)
    copy_target = Block(arg_types=[contig_type]).args[0]
    copy_op = DmaCopyOp(copy_target, view_source)
    offset0 = SymbolConstOp(0).result
    offset1 = SymbolConstOp(0).result
    size0 = SymbolConstOp(2).result
    size1 = SymbolConstOp(3).result
    unit_stride0 = SymbolConstOp(1).result
    unit_stride1 = SymbolConstOp(1).result
    load_op = DmaLoadOp(copy_target, view_source, [offset0, offset1], [size0, size1], [unit_stride0, unit_stride1])
    store_op = DmaStoreOp(view_source, copy_target, [offset0, offset1], [size0, size1], [unit_stride0, unit_stride1])
    slice_op = DmaSliceOp(copy_target, view_source, [offset0, offset1], [size0, size1], [unit_stride0, unit_stride1])
    deslice_op = DmaDesliceOp(view_source, copy_target, [offset0, offset1], [size0, size1], [unit_stride0, unit_stride1], contig_type)
    cast_op = DmaCastOp(copy_target, view_source)

    for op in [free_op, view_op, reshape_op, fill_op, copy_op, load_op, store_op, slice_op, deslice_op, cast_op]:
        analyzed = memory_dma_module.analyze_dma_op(op, path_latency_ns=path_latency, path_bandwidth=path_bandwidth, dtype_size_overrides=dtype_overrides)
        assert analyzed is not None
        assert analyzed.op_name == op.name

    monkeypatch.setattr(DmaFillOp, "verify", lambda self: None)
    bad_fill = DmaFillOp(Block(arg_types=[i32]).args[0], fill_value)
    with pytest.raises(ValueError, match="dma.fill target must be nn.memory"):
        memory_dma_module.analyze_dma_op(bad_fill, path_latency_ns=path_latency, path_bandwidth=path_bandwidth, dtype_size_overrides=dtype_overrides)
    with pytest.raises(AnalysisError, match="dma.fill target must be nn.memory"):
        memory_module.analyze_dma_memory_op(bad_fill, AnalysisConfig())

    valid_copy = DmaCopyOp(copy_target, view_source)
    assert isinstance(memory_module.analyze_dma_memory_op(valid_copy, AnalysisConfig()), DmaMemoryAnalysis)
