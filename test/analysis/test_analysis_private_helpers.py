"""Analysis private helper regression tests.

创建者: jcc你莫辜负
最后修改人: jcc你莫辜负

功能说明:
- 按实际 diff 直接覆盖 analysis.py 的 private helper 合同与边界路径。
- 这些 pytest 只用于 diff 反推自测，不依赖 expectation 资产。

使用示例:
- pytest -q test/analysis/test_analysis_private_helpers.py

关联文件:
- 功能实现: kernel_gen/analysis/analysis.py
- Spec 文档: spec/analysis/analysis_kernel.md
- 测试文件: test/analysis/test_analysis.py
- 测试文件: test/analysis/test_analysis_private_helpers.py
"""

from __future__ import annotations

import importlib
import sys
from pathlib import Path
from types import SimpleNamespace

import sympy as sp
import pytest
from xdsl.dialects import arith, func
from xdsl.dialects.builtin import (
    ArrayAttr,
    FunctionType,
    IntAttr,
    IntegerAttr,
    IntegerType,
    StringAttr,
    f16,
    bf16,
    f32,
    f64,
    i1,
    i32,
)
from xdsl.ir import Block, Region

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

analysis_tests = importlib.import_module("test.analysis.test_analysis")

from kernel_gen.analysis.analysis import (
    AnalysisConfig,
    AnalysisError,
    ComputeItem,
    MemoryItem,
    ValueTraffic,
)
import kernel_gen.analysis.analysis as analysis_module
from kernel_gen.analysis.compute import ComputeKind
from kernel_gen.analysis.memory import MemoryPath
from kernel_gen.analysis.memory.dma import DmaMemoryAnalysis
from kernel_gen.symbol_variable.memory import Memory
from kernel_gen.symbol_variable.type import NumericType
from kernel_gen.target import registry as target_registry


# AN-PH-001
# 创建者: jcc你莫辜负
# 最后更改: jcc你莫辜负
# 测试目的: 验证 analysis 的 metric baseline / override / merge helper 合同与错误边界。
# 使用示例: pytest -q test/analysis/test_analysis_private_helpers.py -k test_analysis_metric_helpers
# 对应功能实现文件路径: kernel_gen/analysis/analysis.py
# 对应 spec 文件路径: spec/analysis/analysis_kernel.md
# 对应测试文件路径: test/analysis/test_analysis_private_helpers.py
def test_analysis_metric_helpers(monkeypatch: pytest.MonkeyPatch) -> None:
    normalized = analysis_module._normalize_path_metric_mapping(
        {MemoryPath.GM_TO_LM: sp.Integer(8), "GM->SM": sp.Integer(4)},
        target="npu_demo",
        metric_key="path_bandwidth",
    )
    assert normalized[MemoryPath.GM_TO_LM] == sp.Integer(8)
    assert normalized[MemoryPath.GM_TO_SM] == sp.Integer(4)

    with pytest.raises(AnalysisError, match="unknown memory path"):
        analysis_module._normalize_path_metric_mapping(
            {"mystery": sp.Integer(1)},
            target="npu_demo",
            metric_key="path_bandwidth",
        )

    defaults = analysis_module._load_target_metric_defaults("npu_demo")
    assert set(defaults) == set(analysis_module._ANALYSIS_METRIC_KEYS)
    assert isinstance(defaults["path_bandwidth"], dict)

    monkeypatch.setattr(
        target_registry,
        "get_target_analysis_defaults",
        lambda target: (_ for _ in ()).throw(ValueError("boom")),
    )
    with pytest.raises(AnalysisError, match="boom"):
        analysis_module._load_target_metric_defaults("broken")

    monkeypatch.setattr(
        target_registry,
        "get_target_analysis_defaults",
        lambda target: {"path_bandwidth": {}, "path_latency_ns": {}},
    )
    with pytest.raises(AnalysisError, match="missing analysis metric defaults: theoretical_compute"):
        analysis_module._load_target_metric_defaults("broken")

    monkeypatch.setattr(
        target_registry,
        "get_target_analysis_defaults",
        lambda target: {"path_bandwidth": {}, "path_latency_ns": {}, "theoretical_compute": []},
    )
    with pytest.raises(AnalysisError, match="analysis metric theoretical_compute must be mapping"):
        analysis_module._load_target_metric_defaults("broken")

    assert analysis_module._normalize_metric_overrides(None) == {}
    overrides = analysis_module._normalize_metric_overrides(
        {
            "path_bandwidth": {"GM->LM": 16},
            "theoretical_compute": {"vector": 4},
        }
    )
    assert overrides["path_bandwidth"][MemoryPath.GM_TO_LM] == 16
    assert overrides["theoretical_compute"]["vector"] == 4

    with pytest.raises(AnalysisError, match="must be mapping"):
        analysis_module._normalize_metric_overrides(object())
    with pytest.raises(AnalysisError, match="unknown keys"):
        analysis_module._normalize_metric_overrides({"path_bandwidth": {}, "unexpected": {}})
    with pytest.raises(AnalysisError, match="metric_overrides.path_bandwidth must be mapping"):
        analysis_module._normalize_metric_overrides({"path_bandwidth": 1})

    merged = analysis_module._merge_metric_defaults(
        {
            "path_bandwidth": {MemoryPath.GM_TO_LM: 1},
            "path_latency_ns": {},
            "theoretical_compute": {"vector": 2},
        },
        {"path_bandwidth": {MemoryPath.GM_TO_LM: 3}},
    )
    assert merged["path_bandwidth"][MemoryPath.GM_TO_LM] == 3
    assert merged["theoretical_compute"]["vector"] == 2


# AN-PH-002
# 创建者: jcc你莫辜负
# 最后更改: jcc你莫辜负
# 测试目的: 验证 dtype / dimension / trip_count / numel helper 的边界分支。
# 使用示例: pytest -q test/analysis/test_analysis_private_helpers.py -k test_analysis_numeric_helpers
# 对应功能实现文件路径: kernel_gen/analysis/analysis.py
# 对应 spec 文件路径: spec/analysis/analysis_kernel.md
# 对应测试文件路径: test/analysis/test_analysis_private_helpers.py
def test_analysis_numeric_helpers() -> None:
    assert analysis_module._normalize_dtype_overrides(None) == {}
    assert analysis_module._normalize_dtype_overrides({"F32": 4, "i32": 8}) == {"f32": 4, "i32": 8}
    with pytest.raises(AnalysisError, match="must be positive int"):
        analysis_module._normalize_dtype_overrides({"f32": 0})

    assert analysis_module._size_symbol(None, "S") == sp.Symbol("S")
    assert analysis_module._size_symbol(5, "S") == sp.Integer(5)

    for dtype, expected in [
        (IntegerType(1), 1),
        (IntegerType(8), 1),
        (IntegerType(16), 2),
        (IntegerType(32), 4),
        (IntegerType(64), 8),
        (f16, 2),
        (bf16, 2),
        (f32, 4),
        (f64, 8),
    ]:
        assert analysis_module._element_size(dtype, {}) == expected
    assert analysis_module._element_size(IntegerType(24), {}) is None
    assert analysis_module._element_size(f32, {"f32": 9}) == 9

    dim_cases = [
        (IntAttr(3), sp.Integer(3)),
        (IntegerAttr.from_int_and_width(4, 64), sp.Integer(4)),
        (StringAttr("5"), sp.Integer(5)),
        (StringAttr("N"), "N"),
    ]
    for dim, expected in dim_cases:
        expr = analysis_module._dim_to_expr(dim)
        if isinstance(expected, str):
            assert isinstance(expr, sp.Symbol)
            assert expr.name == expected
        else:
            assert expr == expected
    assert analysis_module._dim_to_expr(StringAttr("")) is None
    assert analysis_module._dim_to_expr(StringAttr("?")) is None
    assert analysis_module._dim_to_expr(ArrayAttr([])) is None

    trip_cases = [
        (IntAttr(7), sp.Integer(7)),
        (IntegerAttr.from_int_and_width(8, 64), sp.Integer(8)),
        (StringAttr("9"), sp.Integer(9)),
        (StringAttr("M"), "M"),
    ]
    for attr, expected in trip_cases:
        expr = analysis_module._trip_count_attr_to_expr(attr)
        if isinstance(expected, str):
            assert isinstance(expr, sp.Symbol)
            assert expr.name == expected
        else:
            assert expr == expected
    assert analysis_module._trip_count_attr_to_expr(StringAttr("")) is None
    assert analysis_module._trip_count_attr_to_expr(StringAttr("?")) is None
    assert analysis_module._trip_count_attr_to_expr(ArrayAttr([])) is None

    loop_op = SimpleNamespace(name="test.loop", attributes={})
    assert analysis_module._trip_count_from_op(loop_op) == sp.Integer(1)
    loop_op.attributes["trip_count"] = StringAttr("N")
    expr = analysis_module._trip_count_from_op(loop_op)
    assert isinstance(expr, sp.Symbol)
    assert expr.name == "N"
    loop_op.attributes["trip_count"] = ArrayAttr([])
    with pytest.raises(AnalysisError, match="trip_count must be integer or symbol"):
        analysis_module._trip_count_from_op(loop_op)

    shape = ArrayAttr([IntAttr(2), StringAttr("N")])
    assert str(analysis_module._numel_from_shape(shape)) == "2*N"
    assert analysis_module._numel_from_shape(ArrayAttr([StringAttr("?")])) is None

    mem_type = analysis_tests._make_memory_type([IntAttr(2), StringAttr("N")], f32, "global")
    assert str(analysis_module._numel_from_mem_type(mem_type)) == "2*N"


# AN-PH-003
# 创建者: jcc你莫辜负
# 最后更改: jcc你莫辜负
# 测试目的: 验证迭代、traffic 记录与忽略规则 helper 的真实行为。
# 使用示例: pytest -q test/analysis/test_analysis_private_helpers.py -k test_analysis_iteration_and_traffic_helpers
# 对应功能实现文件路径: kernel_gen/analysis/analysis.py
# 对应 spec 文件路径: spec/analysis/analysis_kernel.md
# 对应测试文件路径: test/analysis/test_analysis_private_helpers.py
def test_analysis_iteration_and_traffic_helpers() -> None:
    inner_block = Block()
    inner_block.add_op(analysis_tests.FakeSymbolGetDimOp())
    nested_region = Region(inner_block)
    nested_op = analysis_tests.FakeRegionOp(nested_region, IntAttr(2))

    assert [op.name for op in analysis_module._iter_block_ops([nested_op])] == [
        "test.region",
        "symbol.get_dim",
    ]

    outer_block = Block()
    outer_block.add_op(nested_op)
    func_op = func.FuncOp("main", FunctionType.from_lists([], []), Region(outer_block))
    assert [op.name for op in analysis_module._iter_func_ops(func_op)] == [
        "test.region",
        "symbol.get_dim",
    ]

    assert analysis_module._should_ignore_kernel_op(func.ReturnOp())
    assert analysis_module._should_ignore_kernel_op(arith.ConstantOp(IntegerAttr.from_int_and_width(1, 32)))
    assert analysis_module._should_ignore_kernel_op(analysis_tests.FakeSymbolGetDimOp())
    assert analysis_module._should_ignore_kernel_op(analysis_tests.FakeSymbolGetStrideOp())
    assert analysis_module._should_ignore_kernel_op(analysis_tests.FakeArchOp())
    assert analysis_module._should_ignore_kernel_op(analysis_tests.FakeTunerParamOp())
    assert not analysis_module._should_ignore_kernel_op(analysis_tests.UnknownOp())

    traffic_block = Block(arg_types=[i32])
    value = traffic_block.args[0]
    value_keys: dict[object, str] = {value: "arg0"}
    traffic_map: dict[str, list[sp.Basic]] = {"arg0": [sp.Integer(0), sp.Integer(0)]}
    analysis_module._record_value_read(value, sp.Integer(4), value_keys, traffic_map)
    analysis_module._record_value_write(value, sp.Integer(6), value_keys, traffic_map)
    other_value = Block(arg_types=[i32]).args[0]
    analysis_module._record_value_read(other_value, sp.Integer(1), value_keys, traffic_map)
    analysis_module._record_value_write(other_value, sp.Integer(1), value_keys, traffic_map)
    assert traffic_map["arg0"] == [sp.Integer(4), sp.Integer(6)]

    kernel_op = analysis_tests.FakeKernelScalarBinaryElewiseOp(value, value, i32)
    value_keys_2: dict[object, str] = {}
    traffic_map_2: dict[str, list[sp.Basic]] = {}
    analysis_module._register_op_results(kernel_op, 3, sp.Integer(12), value_keys_2, traffic_map_2)
    assert value_keys_2[kernel_op.results[0]] == "op3.result0"
    assert traffic_map_2["op3.result0"] == [sp.Integer(0), sp.Integer(12)]


# AN-PH-004
# 创建者: jcc你莫辜负
# 最后更改: jcc你莫辜负
# 测试目的: 验证 scaling、result 写回、analyzer wrapper 与公开入口边界。
# 使用示例: pytest -q test/analysis/test_analysis_private_helpers.py -k test_analysis_scaling_and_entrypoint_helpers
# 对应功能实现文件路径: kernel_gen/analysis/analysis.py
# 对应 spec 文件路径: spec/analysis/analysis_kernel.md
# 对应测试文件路径: test/analysis/test_analysis_private_helpers.py
def test_analysis_scaling_and_entrypoint_helpers(monkeypatch: pytest.MonkeyPatch) -> None:
    item = MemoryItem(
        path=MemoryPath.GM_TO_LM,
        access="read",
        bytes=sp.Integer(8),
        latency_ns=sp.Integer(1),
        bandwidth=sp.Integer(2),
        time_ns=sp.Integer(4),
    )
    assert analysis_module._scale_memory_item(item, sp.Integer(1)) is item
    scaled_item = analysis_module._scale_memory_item(item, sp.Integer(3))
    assert scaled_item.bytes == sp.Integer(24)
    assert scaled_item.latency_ns == sp.Integer(3)
    assert scaled_item.time_ns == sp.Integer(12)
    assert scaled_item.bandwidth == sp.Integer(2)

    analyzed = analysis_module._AnalyzedOp(
        op_name="nn.fake",
        compute_items=[ComputeItem(ComputeKind.VECTOR, sp.Integer(5), "f32")],
        memory_items=[item],
        compute=sp.Integer(5),
        read_bytes=sp.Integer(8),
        write_bytes=sp.Integer(4),
        value_reads=((SimpleNamespace(), sp.Integer(2)),),
        direct_writes=((SimpleNamespace(), sp.Integer(1)),),
        result_write_bytes=sp.Integer(4),
    )
    assert analysis_module._scale_analyzed_op(analyzed, sp.Integer(1)) is analyzed
    scaled_analyzed = analysis_module._scale_analyzed_op(analyzed, sp.Integer(2))
    assert scaled_analyzed.compute == sp.Integer(10)
    assert scaled_analyzed.read_bytes == sp.Integer(16)
    assert scaled_analyzed.write_bytes == sp.Integer(8)
    assert scaled_analyzed.result_write_bytes == sp.Integer(8)

    target = SimpleNamespace(attributes={}, name="nn.fake")
    result = analysis_module._result_from_analyzed_op(target, analyzed, AnalysisConfig(write_op_attrs=True))
    assert result.op_costs[0].op_name == "nn.fake"
    assert target.attributes["analysis.compute"] == StringAttr("5")
    assert target.attributes["analysis.read_bytes"] == StringAttr("8")
    assert target.attributes["analysis.write_bytes"] == StringAttr("0")
    assert target.attributes["analysis.memory.time_ns0"] == StringAttr("4")

    result_alias = analysis_module._to_analysis_result(
        result.compute_items,
        result.memory_items,
        op_costs=result.op_costs,
        value_traffic=result.value_traffic,
    )
    assert result_alias.total_compute == sp.Integer(5)
    assert result_alias.total_read_bytes == sp.Integer(8)
    assert result_alias.total_write_bytes == sp.Integer(0)

    with pytest.raises(AnalysisError, match="unsupported memory analyzer result"):
        analysis_module._coerce_memory_analyzer_result(SimpleNamespace(name="dma.load"), object(), AnalysisConfig())

    same_analyzed = analysis_module._coerce_memory_analyzer_result(
        SimpleNamespace(name="dma.load"),
        analyzed,
        AnalysisConfig(),
    )
    assert same_analyzed is analyzed

    dma_analysis = DmaMemoryAnalysis(
        "dma.cast",
        (
            (MemoryPath.GM_TO_LM, "read", sp.Integer(8), sp.Integer(1), sp.Integer(2), sp.Integer(4)),
            (MemoryPath.GM_TO_LM, "write", sp.Integer(4), None, None, None),
        ),
        sp.Integer(8),
        sp.Integer(4),
    )
    fake_cast = SimpleNamespace(
        name="dma.cast",
        target=SimpleNamespace(type=analysis_tests._make_memory_type([IntAttr(2), IntAttr(2)], f32, "global")),
    )
    coerced = analysis_module._coerce_memory_analyzer_result(fake_cast, dma_analysis, AnalysisConfig())
    assert coerced.compute_items[0].kind == ComputeKind.VECTOR
    assert coerced.compute_items[0].amount == sp.Integer(4)
    assert coerced.compute_items[0].dtype == "f32"

    monkeypatch.setattr("kernel_gen.analysis.compute.kernel.analyze_scalar_kernel_op", lambda op, config: analyzed)
    assert analysis_module._analyze_scalar_kernel_op(SimpleNamespace(name="kernel.fake"), AnalysisConfig()) is analyzed

    monkeypatch.setattr("kernel_gen.analysis.compute.nn.analyze_nn_elementwise_op", lambda op, config: analyzed)
    assert analysis_module._analyze_nn_elementwise_op(SimpleNamespace(name="nn.add"), AnalysisConfig()) is analyzed

    monkeypatch.setattr("kernel_gen.analysis.compute.nn.analyze_nn_matmul_ir_op", lambda op, config: analyzed)
    assert analysis_module._analyze_nn_matmul_ir_op(SimpleNamespace(name="nn.matmul"), AnalysisConfig()) is analyzed

    monkeypatch.setattr("kernel_gen.analysis.memory.analyze_dma_memory_op", lambda op, config: None)
    assert analysis_module._analyze_dma_ir_op(SimpleNamespace(name="dma.load"), AnalysisConfig()) is None

    monkeypatch.setattr("kernel_gen.analysis.memory.analyze_dma_memory_op", lambda op, config: dma_analysis)
    assert analysis_module._analyze_dma_ir_op(fake_cast, AnalysisConfig()) is not None

    with pytest.raises(AnalysisError, match="config must be AnalysisConfig"):
        analysis_module.analysis(analysis_tests.UnknownOp(), object())
    with pytest.raises(AnalysisError, match="predicate_size must be positive"):
        analysis_module.analysis(analysis_tests.UnknownOp(), AnalysisConfig(predicate_size=0))
    with pytest.raises(AnalysisError, match="func_op must be func.FuncOp"):
        analysis_module._analysis_func(object(), AnalysisConfig(), None)
