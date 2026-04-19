"""Analysis utilities for computation and data movement.

创建者: 金铲铲大作战
最后一次更改: jcc你莫辜负 (2026-04-06)

功能说明:
- 基于 Memory 形状统计逐元素/比较/broadcast/matmul 的计算量与搬运量。
- 支持函数级聚合，区分中间结果是否物化。

覆盖率信息:
- 当前覆盖率: `100%` (`kernel_gen/analysis/analysis.py`，2026-03-22 15:24:43 +0800)。
- 对应覆盖率命令: coverage run -m pytest -q test/analysis/test_analysis.py && coverage report --include=kernel_gen/analysis/analysis.py -m

使用示例:
- from kernel_gen.analysis.analysis import analyze_add, analyze_function, MemoryRef, Operation
- result = analyze_add(lhs, rhs, out)
- summary = analyze_function([Operation("add", [MemoryRef("A", lhs), MemoryRef("B", rhs)], MemoryRef("C", out))])

关联文件:
- spec: spec/analysis/analysis_kernel.md
- test: test/analysis/test_analysis.py
- 功能实现: kernel_gen/analysis/analysis.py
"""

from __future__ import annotations

from collections.abc import Iterable as IterableABC, Mapping as MappingABC
from dataclasses import dataclass, field
from typing import Iterable, Sequence
import warnings

import sympy as sp
from xdsl.dialects import arith, func
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
)
from xdsl.ir import Attribute, Operation, SSAValue
from kernel_gen.analysis.compute import ComputeKind, iter_compute_analyzers_for_op
from kernel_gen.analysis.memory import (
    MemoryPath,
    iter_memory_analyzers_for_op,
    metric_value_to_expr,
    normalize_memory_path,
    time_from_memory_metrics,
)
from kernel_gen.analysis.memory.dma import DmaMemoryAnalysis
from kernel_gen.dialect.nn import NnMemoryType
from kernel_gen.dialect.symbol import SymbolValueType
from kernel_gen.symbol_variable.memory import Memory
from kernel_gen.symbol_variable.symbol_dim import SymbolDim
from kernel_gen.target import registry as target_registry


class AnalysisError(ValueError):
    """分析阶段错误。

    创建者: 金铲铲大作战
    最后一次更改: jcc你莫辜负

    功能说明:
    - 用于在分析阶段报告 shape 或规则不满足的错误。

    使用示例:
    - raise AnalysisError("Shape mismatch")

    关联文件:
    - spec: spec/analysis/analysis_kernel.md
    - test: test/analysis/test_analysis.py
    - 功能实现: kernel_gen/analysis/analysis.py
    """


@dataclass(frozen=True)
class AnalysisConfig:
    """统一分析入口配置。

    创建者: 朽木露琪亚
    最后一次更改: jcc你莫辜负

    功能说明:
    - 定义 `analysis(op, config, otherargs)` 的统一控制开关。
    - 默认同时启用 compute/memory 分析，但默认不写回 `analysis.*` 属性。
    - `path_bandwidth/path_latency_ns/theoretical_compute` 的正式来源是 `target registry` 中当前 target 的 analysis 默认参数；
      当前默认 target 固定为 `npu_demo`，调用方只能通过 `metric_overrides` 做显式覆盖。

    使用示例:
    - config = AnalysisConfig(enable_compute=True, enable_memory=False, target="npu_demo", write_op_attrs=True)

    关联文件:
    - spec: spec/analysis/analysis_engine.md
    - test: test/analysis/test_analysis.py
    - 功能实现: kernel_gen/analysis/analysis.py
    """

    enable_compute: bool = True
    enable_memory: bool = True
    target: str = "npu_demo"
    metric_overrides: MappingABC[str, MappingABC[str, object]] | None = None
    write_op_attrs: bool = False
    write_func_attrs: bool = False
    predicate_size: int = 1
    dtype_size_overrides: dict[str, int] | None = None
    otherargs: Iterable[object] | None = None
    path_bandwidth: MappingABC[str, object] = field(init=False, repr=False)
    path_latency_ns: MappingABC[str, object] = field(init=False, repr=False)
    theoretical_compute: MappingABC[str, object] = field(init=False, repr=False)

    def __post_init__(self) -> None:
        """从 target registry 解析 analysis 默认参数。

        创建者: jcc你莫辜负
        最后一次更改: jcc你莫辜负

        功能说明:
        - 当前固定从 `target registry` 读取 `path_bandwidth/path_latency_ns/theoretical_compute`。
        - 只允许在读取到完整 target 基线后，再叠加 `metric_overrides`。

        使用示例:
        - config = AnalysisConfig(target="npu_demo", metric_overrides={"path_bandwidth": {"GM->LM": 96}})

        关联文件:
        - spec: spec/analysis/analysis_engine.md
        - test: test/analysis/test_analysis.py
        - 功能实现: kernel_gen/analysis/analysis.py
        """

        defaults = _load_target_metric_defaults(self.target)
        overrides = _normalize_metric_overrides(self.metric_overrides)
        merged = _merge_metric_defaults(defaults, overrides)
        object.__setattr__(self, "path_bandwidth", merged["path_bandwidth"])
        object.__setattr__(self, "path_latency_ns", merged["path_latency_ns"])
        object.__setattr__(self, "theoretical_compute", merged["theoretical_compute"])


@dataclass(frozen=True)
class ComputeItem:
    """新分析结果中的单条计算项。

    创建者: 朽木露琪亚
    最后一次更改: 朽木露琪亚

    功能说明:
    - 显式记录计算分类、数量与 dtype。

    使用示例:
    - ComputeItem(kind=ComputeKind.SCALAR, amount=sp.Integer(1), dtype="i32")

    关联文件:
    - spec: spec/analysis/analysis_engine.md
    - test: test/analysis/test_analysis.py
    - 功能实现: kernel_gen/analysis/analysis.py
    """

    kind: ComputeKind
    amount: sp.Basic
    dtype: str


@dataclass(frozen=True)
class MemoryItem:
    """新分析结果中的单条访存项。

    创建者: 朽木露琪亚
    最后一次更改: 朽木露琪亚

    功能说明:
    - 显式记录 path、访问方向与字节数。
    - 若配置提供延迟/带宽参数，则补齐理论时间。

    使用示例:
    - MemoryItem(path="GM->LM", access="read", bytes=sp.Integer(32))

    关联文件:
    - spec: spec/analysis/analysis_engine.md
    - test: test/analysis/test_analysis.py
    - 功能实现: kernel_gen/analysis/analysis.py
    """

    path: MemoryPath
    access: str
    bytes: sp.Basic
    latency_ns: sp.Basic | None = None
    bandwidth: sp.Basic | None = None
    time_ns: sp.Basic | None = None


@dataclass(frozen=True)
class AnalysisResult:
    """统一分析入口结果结构。

    创建者: 朽木露琪亚
    最后一次更改: 朽木露琪亚

    功能说明:
    - 公开 `compute_items / memory_items` 与按 kind/path 聚合的 totals。
    - 兼容保留 `op_costs/value_traffic` 供 facade/pass 派生旧 summary。

    使用示例:
    - result = AnalysisResult(compute_items=[], memory_items=[], compute_totals_by_kind={}, memory_totals_by_path={})

    关联文件:
    - spec: spec/analysis/analysis_engine.md
    - test: test/analysis/test_analysis.py
    - 功能实现: kernel_gen/analysis/analysis.py
    """

    compute_items: Sequence[ComputeItem]
    memory_items: Sequence[MemoryItem]
    compute_totals_by_kind: MappingABC[ComputeKind, sp.Basic]
    memory_totals_by_path: MappingABC[MemoryPath, sp.Basic]
    op_costs: Sequence["KernelOpCost"] = ()
    value_traffic: Sequence["ValueTraffic"] = ()
    func_name: str | None = None
    _value_reads: Sequence[tuple[SSAValue, sp.Basic]] = ()
    _direct_writes: Sequence[tuple[SSAValue, sp.Basic]] = ()
    _result_write_bytes: sp.Basic = sp.Integer(0)

    @property
    def total_compute(self) -> sp.Basic:
        """兼容旧 compute 总量查询。

        创建者: 朽木露琪亚
        最后一次更改: 朽木露琪亚

        功能说明:
        - 由 `compute_totals_by_kind` 派生总计算量。

        使用示例:
        - total = result.total_compute

        关联文件:
        - spec: spec/analysis/analysis_engine.md
        - test: test/analysis/test_analysis.py
        - 功能实现: kernel_gen/analysis/analysis.py
        """

        return _sum_expr(self.compute_totals_by_kind.values())

    @property
    def total_read_bytes(self) -> sp.Basic:
        """兼容旧 read_bytes 总量查询。

        创建者: 朽木露琪亚
        最后一次更改: 朽木露琪亚

        功能说明:
        - 由 `memory_items` 中 `access=read` 的条目派生。

        使用示例:
        - total = result.total_read_bytes

        关联文件:
        - spec: spec/analysis/analysis_engine.md
        - test: test/analysis/test_analysis.py
        - 功能实现: kernel_gen/analysis/analysis.py
        """

        return _sum_expr(item.bytes for item in self.memory_items if item.access == "read")

    @property
    def total_write_bytes(self) -> sp.Basic:
        """兼容旧 write_bytes 总量查询。

        创建者: 朽木露琪亚
        最后一次更改: 朽木露琪亚

        功能说明:
        - 由 `memory_items` 中 `access=write` 的条目派生。

        使用示例:
        - total = result.total_write_bytes

        关联文件:
        - spec: spec/analysis/analysis_engine.md
        - test: test/analysis/test_analysis.py
        - 功能实现: kernel_gen/analysis/analysis.py
        """

        return _sum_expr(item.bytes for item in self.memory_items if item.access == "write")


@dataclass(frozen=True)
class OpStats:
    """算子级统计结果。

    创建者: 金铲铲大作战
    最后一次更改: 金铲铲大作战

    功能说明:
    - 保存计算量、读字节与写字节的符号表达式。

    使用示例:
    - stats = OpStats(sp.Integer(1), sp.Integer(4), sp.Integer(2))

    关联文件:
    - spec: spec/analysis/analysis_kernel.md
    - test: test/analysis/test_analysis.py
    - 功能实现: kernel_gen/analysis/analysis.py
    """

    compute: sp.Basic
    read_bytes: sp.Basic
    write_bytes: sp.Basic

    def __add__(self, other: "OpStats") -> "OpStats":
        """合并两个统计结果。

        创建者: 金铲铲大作战
        最后一次更改: 金铲铲大作战

        功能说明:
        - 累加计算量、读字节与写字节。

        使用示例:
        - total = stats1 + stats2

        关联文件:
        - spec: spec/analysis/analysis_kernel.md
        - test: test/analysis/test_analysis.py
        - 功能实现: kernel_gen/analysis/analysis.py
        """
        if not isinstance(other, OpStats):
            return NotImplemented
        return OpStats(
            self.compute + other.compute,
            self.read_bytes + other.read_bytes,
            self.write_bytes + other.write_bytes,
        )


@dataclass(frozen=True)
class MemoryRef:
    """具名 Memory 引用。

    创建者: 金铲铲大作战
    最后一次更改: 金铲铲大作战

    功能说明:
    - 绑定名称与 Memory 对象，用于函数级分析。

    使用示例:
    - MemoryRef("A", Memory(["A", "B"], NumericType.Float32))

    关联文件:
    - spec: spec/analysis/analysis_kernel.md
    - test: test/analysis/test_analysis.py
    - 功能实现: kernel_gen/analysis/analysis.py
    """

    name: str
    memory: Memory


@dataclass(frozen=True)
class Operation:
    """函数级算子描述。

    创建者: 金铲铲大作战
    最后一次更改: 金铲铲大作战

    功能说明:
    - 描述算子名称、输入、输出与是否物化。

    使用示例:
    - Operation("add", [MemoryRef("A", lhs)], MemoryRef("C", out))

    关联文件:
    - spec: spec/analysis/analysis_kernel.md
    - test: test/analysis/test_analysis.py
    - 功能实现: kernel_gen/analysis/analysis.py
    """

    op: str
    inputs: Sequence[MemoryRef]
    output: MemoryRef
    materialize: bool = True


@dataclass(frozen=True)
class AnalysisSummary:
    """函数级分析聚合结果。

    创建者: 金铲铲大作战
    最后一次更改: 金铲铲大作战

    功能说明:
    - 汇总算子统计与总计结果。

    使用示例:
    - summary = AnalysisSummary([stats], stats)

    关联文件:
    - spec: spec/analysis/analysis_kernel.md
    - test: test/analysis/test_analysis.py
    - 功能实现: kernel_gen/analysis/analysis.py
    """

    ops: Sequence[OpStats]
    total: OpStats


@dataclass(frozen=True)
class KernelOpCost:
    """单个 kernel op 的成本统计。

    创建者: 金铲铲大作战
    最后一次更改: 金铲铲大作战

    功能说明:
    - 保存 op 顺序索引、名称与 compute/read/write 统计。

    使用示例:
    - KernelOpCost(0, "nn.add", sp.Symbol("A"), sp.Symbol("B"), sp.Symbol("C"))

    关联文件:
    - spec: spec/analysis/analysis_kernel.md
    - test: test/analysis/test_analysis.py
    - 功能实现: kernel_gen/analysis/analysis.py
    """

    op_index: int
    op_name: str
    compute: sp.Basic
    read_bytes: sp.Basic
    write_bytes: sp.Basic


@dataclass(frozen=True)
class ValueTraffic:
    """单个 SSA value 的流量统计。

    创建者: 金铲铲大作战
    最后一次更改: 金铲铲大作战

    功能说明:
    - 使用稳定 value_key 记录读写流量。

    使用示例:
    - ValueTraffic("arg0", sp.Integer(0), sp.Integer(16))

    关联文件:
    - spec: spec/analysis/analysis_kernel.md
    - test: test/analysis/test_analysis.py
    - 功能实现: kernel_gen/analysis/analysis.py
    """

    value_key: str
    read_bytes: sp.Basic
    write_bytes: sp.Basic


@dataclass(frozen=True)
class AnalyzeKernelSummary:
    """kernel 分析汇总结构。

    创建者: 金铲铲大作战
    最后一次更改: 金铲铲大作战

    功能说明:
    - 汇总函数名、逐 op 成本与逐 value 流量。

    使用示例:
    - summary = AnalyzeKernelSummary("main", [], [], sp.Integer(0), sp.Integer(0), sp.Integer(0))

    关联文件:
    - spec: spec/analysis/analysis_kernel.md
    - test: test/analysis/test_analysis.py
    - 功能实现: kernel_gen/analysis/analysis.py
    """

    func_name: str
    op_costs: Sequence[KernelOpCost]
    value_traffic: Sequence[ValueTraffic]
    total_compute: sp.Basic
    total_read_bytes: sp.Basic
    total_write_bytes: sp.Basic


@dataclass(frozen=True)
class _AnalyzedOp:
    """统一入口内部的单 op 统计载体。

    创建者: 朽木露琪亚
    最后一次更改: 朽木露琪亚

    功能说明:
    - 为 `analysis(func.func, ...)` 聚合过程保存单 op 分析结果。

    使用示例:
    - _AnalyzedOp("nn.add", [], [], sp.Integer(1), sp.Integer(8), sp.Integer(4))

    关联文件:
    - spec: spec/analysis/analysis_engine.md
    - test: test/analysis/test_analysis.py
    - 功能实现: kernel_gen/analysis/analysis.py
    """

    op_name: str
    compute_items: Sequence[ComputeItem]
    memory_items: Sequence[MemoryItem]
    compute: sp.Basic
    read_bytes: sp.Basic
    write_bytes: sp.Basic
    value_reads: Sequence[tuple[SSAValue, sp.Basic]] = ()
    direct_writes: Sequence[tuple[SSAValue, sp.Basic]] = ()
    result_write_bytes: sp.Basic = sp.Integer(0)


from kernel_gen.analysis.compute import symbol as _symbol_compute


_SPACE_TOKENS = {
    "global": "GM",
    "shared": "SM",
    "local": "LM",
    "tsm": "TSM",
    "tlm": "TLM",
}
_ANALYSIS_METRIC_KEYS = ("path_bandwidth", "path_latency_ns", "theoretical_compute")


def _normalize_path_metric_mapping(
    values: MappingABC[object, object],
    *,
    target: str,
    metric_key: str,
) -> dict[MemoryPath, object]:
    """将 path metric 映射归一为 `MemoryPath` 键。

    创建者: 朽木露琪亚
    最后一次更改: 朽木露琪亚

    功能说明:
    - 只接受正式 `MemoryPath` 或其等价值文本。
    - 一旦出现未知 path，直接报错，避免继续回退到自由字符串口径。

    使用示例:
    - normalized = _normalize_path_metric_mapping({"GM->LM": 64}, target="npu_demo", metric_key="path_bandwidth")

    关联文件:
    - spec: spec/analysis/analysis_engine.md
    - test: test/analysis/test_analysis.py
    - 功能实现: kernel_gen/analysis/analysis.py
    """

    normalized: dict[MemoryPath, object] = {}
    for raw_key, raw_value in values.items():
        key_text = raw_key.value if isinstance(raw_key, MemoryPath) else str(raw_key)
        path = normalize_memory_path(key_text)
        if path is MemoryPath.UNKNOWN and key_text != MemoryPath.UNKNOWN.value:
            raise AnalysisError(
                f"target={target}: analysis metric {metric_key} uses unknown memory path {key_text}"
            )
        normalized[path] = raw_value
    return normalized


def _load_target_metric_defaults(target: str) -> dict[str, dict[str, object]]:
    """读取 target registry 中的 analysis 默认参数。

    创建者: jcc你莫辜负
    最后一次更改: jcc你莫辜负

    功能说明:
    - 当前只接受来自 `target registry` 的正式 baseline。
    - 若 target 未注册，或缺少 `path_bandwidth/path_latency_ns/theoretical_compute` 中任一类别，必须显式失败。

    使用示例:
    - defaults = _load_target_metric_defaults("npu_demo")

    关联文件:
    - spec: spec/analysis/analysis_engine.md
    - test: test/analysis/test_analysis.py
    - 功能实现: kernel_gen/analysis/analysis.py
    """

    try:
        defaults = target_registry.get_target_analysis_defaults(target)
    except ValueError as exc:
        raise AnalysisError(str(exc)) from exc
    missing = [key for key in _ANALYSIS_METRIC_KEYS if key not in defaults]
    if missing:
        raise AnalysisError(f"target={target}: missing analysis metric defaults: {', '.join(missing)}")
    normalized: dict[str, dict[str, object]] = {}
    for key in _ANALYSIS_METRIC_KEYS:
        value = defaults[key]
        if not isinstance(value, MappingABC):
            raise AnalysisError(f"target={target}: analysis metric {key} must be mapping")
        if key in {"path_bandwidth", "path_latency_ns"}:
            normalized[key] = _normalize_path_metric_mapping(value, target=target, metric_key=key)
        else:
            normalized[key] = dict(value)
    return normalized


def _normalize_metric_overrides(
    metric_overrides: MappingABC[str, MappingABC[str, object]] | None,
) -> dict[str, dict[str, object]]:
    """规范化显式 metric override 配置。

    创建者: jcc你莫辜负
    最后一次更改: jcc你莫辜负

    功能说明:
    - 只允许覆盖 `path_bandwidth/path_latency_ns/theoretical_compute` 三类正式 metric。
    - 不允许把任意嵌套字典当成公开输入。

    使用示例:
    - overrides = _normalize_metric_overrides({"path_bandwidth": {"GM->LM": 96}})

    关联文件:
    - spec: spec/analysis/analysis_engine.md
    - test: test/analysis/test_analysis.py
    - 功能实现: kernel_gen/analysis/analysis.py
    """

    if metric_overrides is None:
        return {}
    if not isinstance(metric_overrides, MappingABC):
        raise AnalysisError("metric_overrides must be mapping[str, mapping[str, object]]")
    unknown = set(metric_overrides.keys()) - set(_ANALYSIS_METRIC_KEYS)
    if unknown:
        raise AnalysisError(f"metric_overrides has unknown keys: {sorted(unknown)}")
    normalized: dict[str, dict[str, object]] = {}
    for key, value in metric_overrides.items():
        if not isinstance(value, MappingABC):
            raise AnalysisError(f"metric_overrides.{key} must be mapping")
        if key in {"path_bandwidth", "path_latency_ns"}:
            normalized[key] = _normalize_path_metric_mapping(
                value,
                target="override",
                metric_key=key,
            )
        else:
            normalized[key] = dict(value)
    return normalized


def _merge_metric_defaults(
    defaults: dict[str, dict[str, object]],
    overrides: dict[str, dict[str, object]],
) -> dict[str, dict[str, object]]:
    """把显式 override 叠加到 target baseline 上。

    创建者: jcc你莫辜负
    最后一次更改: jcc你莫辜负

    功能说明:
    - 先复制 target registry 的 baseline，再按类别覆盖键值。
    - 不改变 baseline 的来源边界；override 仅作为显式 hook。

    使用示例:
    - merged = _merge_metric_defaults(defaults, overrides)

    关联文件:
    - spec: spec/analysis/analysis_engine.md
    - test: test/analysis/test_analysis.py
    - 功能实现: kernel_gen/analysis/analysis.py
    """

    merged = {key: dict(value) for key, value in defaults.items()}
    for key, override_map in overrides.items():
        merged[key].update(override_map)
    return merged


def _space_token_from_mem_type(mem_type: NnMemoryType) -> str:
    """将 nn.memory space 归一到简写 token。

    创建者: 朽木露琪亚
    最后一次更改: 朽木露琪亚

    功能说明:
    - 将 `global/shared/local/tsm/tlm` 映射为 `GM/SM/LM/TSM/TLM`。

    使用示例:
    - token = _space_token_from_mem_type(mem_type)

    关联文件:
    - spec: spec/analysis/analysis_engine.md
    - test: test/analysis/test_analysis.py
    - 功能实现: kernel_gen/analysis/analysis.py
    """

    raw = mem_type.space.space.data
    return _SPACE_TOKENS.get(raw, raw.upper())


def _build_memory_item(
    path: MemoryPath | str,
    access: str,
    bytes_expr: sp.Basic,
    config: AnalysisConfig,
) -> MemoryItem:
    """构造单条 MemoryItem。

    创建者: 朽木露琪亚
    最后一次更改: 朽木露琪亚

    功能说明:
    - 若配置中提供 path 对应的带宽/延迟，则补齐 `time_ns`。

    使用示例:
    - item = _build_memory_item("GM->LM", "read", sp.Integer(32), config)

    关联文件:
    - spec: spec/analysis/analysis_engine.md
    - test: test/analysis/test_analysis.py
    - 功能实现: kernel_gen/analysis/analysis.py
    """

    normalized_path = normalize_memory_path(path)
    latency = None
    bandwidth = None
    if config.path_latency_ns is not None:
        latency = metric_value_to_expr(config.path_latency_ns.get(normalized_path))
    if config.path_bandwidth is not None:
        bandwidth = metric_value_to_expr(config.path_bandwidth.get(normalized_path))
    time_ns = time_from_memory_metrics(bytes_expr, latency, bandwidth)
    return MemoryItem(
        path=normalized_path,
        access=access,
        bytes=bytes_expr,
        latency_ns=latency,
        bandwidth=bandwidth,
        time_ns=time_ns,
    )


def _totals_by_compute_kind(items: Sequence[ComputeItem]) -> dict[ComputeKind, sp.Basic]:
    """按 compute kind 聚合 totals。

    创建者: 朽木露琪亚
    最后一次更改: 朽木露琪亚

    功能说明:
    - 将 `ComputeItem.amount` 按 `kind` 归并求和。

    使用示例:
    - totals = _totals_by_compute_kind(items)

    关联文件:
    - spec: spec/analysis/analysis_engine.md
    - test: test/analysis/test_analysis.py
    - 功能实现: kernel_gen/analysis/analysis.py
    """

    totals: dict[ComputeKind, sp.Basic] = {}
    for item in items:
        totals[item.kind] = totals.get(item.kind, sp.Integer(0)) + item.amount
    return totals


def _totals_by_memory_path(items: Sequence[MemoryItem]) -> dict[MemoryPath, sp.Basic]:
    """按 memory path 聚合 totals。

    创建者: 朽木露琪亚
    最后一次更改: 朽木露琪亚

    功能说明:
    - 将 `MemoryItem.bytes` 按 `path` 归并求和。

    使用示例:
    - totals = _totals_by_memory_path(items)

    关联文件:
    - spec: spec/analysis/analysis_engine.md
    - test: test/analysis/test_analysis.py
    - 功能实现: kernel_gen/analysis/analysis.py
    """

    totals: dict[MemoryPath, sp.Basic] = {}
    for item in items:
        totals[item.path] = totals.get(item.path, sp.Integer(0)) + item.bytes
    return totals


def _write_analysis_attrs(target: Operation, result: AnalysisResult) -> None:
    """按统一入口结果写回 `analysis.*` 属性。

    创建者: 朽木露琪亚
    最后一次更改: 朽木露琪亚

    功能说明:
    - 写入 derived alias 总量。
    - 追加首层 `compute_items/memory_items` 索引属性，供后续 pass 机械读取。

    使用示例:
    - _write_analysis_attrs(op, result)

    关联文件:
    - spec: spec/analysis/analysis_engine.md
    - test: test/analysis/test_analysis.py
    - 功能实现: kernel_gen/analysis/analysis.py
    """

    target.attributes["analysis.compute"] = StringAttr(str(result.total_compute))
    target.attributes["analysis.read_bytes"] = StringAttr(str(result.total_read_bytes))
    target.attributes["analysis.write_bytes"] = StringAttr(str(result.total_write_bytes))
    for index, item in enumerate(result.compute_items):
        target.attributes[f"analysis.compute.kind{index}"] = StringAttr(item.kind.value)
        target.attributes[f"analysis.compute.amount{index}"] = StringAttr(str(item.amount))
        target.attributes[f"analysis.compute.dtype{index}"] = StringAttr(item.dtype)
    for index, item in enumerate(result.memory_items):
        target.attributes[f"analysis.memory.path{index}"] = StringAttr(item.path.value)
        target.attributes[f"analysis.memory.access{index}"] = StringAttr(item.access)
        target.attributes[f"analysis.memory.bytes{index}"] = StringAttr(str(item.bytes))
        if item.time_ns is not None:
            target.attributes[f"analysis.memory.time_ns{index}"] = StringAttr(str(item.time_ns))


def _to_analysis_result(
    compute_items: Sequence[ComputeItem],
    memory_items: Sequence[MemoryItem],
    *,
    op_costs: Sequence[KernelOpCost] = (),
    value_traffic: Sequence[ValueTraffic] = (),
    func_name: str | None = None,
    value_reads: Sequence[tuple[SSAValue, sp.Basic]] = (),
    direct_writes: Sequence[tuple[SSAValue, sp.Basic]] = (),
    result_write_bytes: sp.Basic = sp.Integer(0),
) -> AnalysisResult:
    """基于 items 构造统一入口结果。

    创建者: 朽木露琪亚
    最后一次更改: 朽木露琪亚

    功能说明:
    - 统一填充 totals 与可选 facade 字段。

    使用示例:
    - result = _to_analysis_result(compute_items, memory_items)

    关联文件:
    - spec: spec/analysis/analysis_engine.md
    - test: test/analysis/test_analysis.py
    - 功能实现: kernel_gen/analysis/analysis.py
    """

    return AnalysisResult(
        compute_items=tuple(compute_items),
        memory_items=tuple(memory_items),
        compute_totals_by_kind=_totals_by_compute_kind(compute_items),
        memory_totals_by_path=_totals_by_memory_path(memory_items),
        op_costs=list(op_costs),
        value_traffic=list(value_traffic),
        func_name=func_name,
        _value_reads=tuple(value_reads),
        _direct_writes=tuple(direct_writes),
        _result_write_bytes=result_write_bytes,
    )


def _to_symbol(value: int | str) -> sp.Basic:
    """将维度值转换为 sympy 表达式。

    创建者: 金铲铲大作战
    最后一次更改: 金铲铲大作战

    功能说明:
    - int 转为 Integer，str 转为 Symbol。

    使用示例:
    - _to_symbol("N")

    关联文件:
    - spec: spec/analysis/analysis_kernel.md
    - test: test/analysis/test_analysis.py
    - 功能实现: kernel_gen/analysis/analysis.py
    """
    if isinstance(value, int):
        return sp.Integer(value)
    if isinstance(value, str):
        return sp.Symbol(value)
    raise AnalysisError(f"Unsupported dimension: {value!r}")


def _product(values: Iterable[int | str]) -> sp.Basic:
    """将维度列表转换为乘积表达式。

    创建者: 金铲铲大作战
    最后一次更改: 金铲铲大作战

    功能说明:
    - 按顺序累乘维度表达式。

    使用示例:
    - _product([\"A\", \"B\"])

    关联文件:
    - spec: spec/analysis/analysis_kernel.md
    - test: test/analysis/test_analysis.py
    - 功能实现: kernel_gen/analysis/analysis.py
    """
    result: sp.Basic = sp.Integer(1)
    for value in values:
        result *= _to_symbol(value)
    return result


def _size_symbol(value: int | None, fallback: str) -> sp.Basic:
    """解析 dtype 或 predicate size。

    创建者: 金铲铲大作战
    最后一次更改: 金铲铲大作战

    功能说明:
    - 缺失时返回符号占位（S/P）。

    使用示例:
    - _size_symbol(None, \"S\")

    关联文件:
    - spec: spec/analysis/analysis_kernel.md
    - test: test/analysis/test_analysis.py
    - 功能实现: kernel_gen/analysis/analysis.py
    """
    if value is None:
        return sp.Symbol(fallback)
    return sp.Integer(value)


def _normalize_dtype_overrides(
    dtype_size_overrides: dict[str, int] | None,
) -> dict[str, int]:
    """规范化 dtype 覆盖表。

    创建者: 金铲铲大作战
    最后一次更改: 金铲铲大作战

    功能说明:
    - 将 key 统一为小写。
    - 校验 value 为正整数。

    使用示例:
    - overrides = _normalize_dtype_overrides({"F32": 4})

    关联文件:
    - spec: spec/analysis/analysis_kernel.md
    - test: test/analysis/test_analysis.py
    - 功能实现: kernel_gen/analysis/analysis.py
    """
    normalized: dict[str, int] = {}
    if dtype_size_overrides is None:
        return normalized
    for key, value in dtype_size_overrides.items():
        if not isinstance(value, int) or value <= 0:
            raise AnalysisError(f"dtype_size_overrides[{key}] must be positive int")
        normalized[str(key).lower()] = value
    return normalized


def _element_size(element_type: Attribute, dtype_size_overrides: dict[str, int]) -> int | None:
    """获取元素类型字节大小。

    创建者: 金铲铲大作战
    最后一次更改: 金铲铲大作战

    功能说明:
    - 先读取 dtype_size_overrides 覆盖。
    - 支持 i1/i8/i16/i32/i64 与 f16/bf16/f32/f64。

    使用示例:
    - size = _element_size(f32, {"f32": 4})

    关联文件:
    - spec: spec/analysis/analysis_kernel.md
    - test: test/analysis/test_analysis.py
    - 功能实现: kernel_gen/analysis/analysis.py
    """
    key = str(element_type).lower()
    if key in dtype_size_overrides:
        return dtype_size_overrides[key]
    if isinstance(element_type, IntegerType):
        width = int(element_type.width.data)
        if width in {1, 8}:
            return 1
        if width == 16:
            return 2
        if width == 32:
            return 4
        if width == 64:
            return 8
        return None
    if isinstance(element_type, (Float16Type, BFloat16Type)):
        return 2
    if isinstance(element_type, Float32Type):
        return 4
    if isinstance(element_type, Float64Type):
        return 8
    return None


def _is_predicate_type(element_type: Attribute) -> bool:
    """判断 element_type 是否为 i1 predicate。

    创建者: 金铲铲大作战
    最后一次更改: 金铲铲大作战

    功能说明:
    - IntegerType 且 width=1 时返回 True。

    使用示例:
    - _is_predicate_type(i1)

    关联文件:
    - spec: spec/analysis/analysis_kernel.md
    - test: test/analysis/test_analysis.py
    - 功能实现: kernel_gen/analysis/analysis.py
    """
    return isinstance(element_type, IntegerType) and int(element_type.width.data) == 1


def _dim_to_expr(dim: Attribute) -> sp.Basic | None:
    """将维度 attribute 转为 sympy 表达式。

    创建者: 金铲铲大作战
    最后一次更改: 金铲铲大作战

    功能说明:
    - IntAttr/IntegerAttr 转 Integer。
    - StringAttr 数字转 Integer，其它转 SymbolDim。
    - 空字符串或 '?' 返回 None。

    使用示例:
    - expr = _dim_to_expr(StringAttr("N"))

    关联文件:
    - spec: spec/analysis/analysis_kernel.md
    - test: test/analysis/test_analysis.py
    - 功能实现: kernel_gen/analysis/analysis.py
    """
    if isinstance(dim, IntAttr):
        return sp.Integer(dim.data)
    if isinstance(dim, IntegerAttr):
        return sp.Integer(dim.value.data)
    if isinstance(dim, StringAttr):
        raw = dim.data.strip()
        if raw == "" or raw == "?":
            return None
        if raw.isdigit():
            return sp.Integer(int(raw))
        return SymbolDim(raw).get_symbol()
    return None


def _trip_count_attr_to_expr(attr: Attribute) -> sp.Basic | None:
    """将 trip_count attribute 转为 sympy 表达式。

    创建者: 朽木露琪亚
    最后一次更改: 朽木露琪亚

    功能说明:
    - 支持 IntAttr/IntegerAttr/StringAttr。
    - StringAttr 数字转 Integer，其它转 SymbolDim。
    - 空字符串或 '?' 返回 None。

    使用示例:
    - expr = _trip_count_attr_to_expr(StringAttr("N"))

    关联文件:
    - spec: spec/analysis/analysis_engine.md
    - test: test/analysis/test_analysis.py
    - 功能实现: kernel_gen/analysis/analysis.py
    """
    if isinstance(attr, IntAttr):
        return sp.Integer(attr.data)
    if isinstance(attr, IntegerAttr):
        return sp.Integer(attr.value.data)
    if isinstance(attr, StringAttr):
        raw = attr.data.strip()
        if raw == "" or raw == "?":
            return None
        if raw.isdigit():
            return sp.Integer(int(raw))
        return SymbolDim(raw).get_symbol()
    return None


def _trip_count_from_op(op: Operation) -> sp.Basic:
    """解析 op.trip_count 属性。

    创建者: 朽木露琪亚
    最后一次更改: 朽木露琪亚

    功能说明:
    - 未配置 trip_count 时返回 1。
    - trip_count 需为整数或符号表达式。

    使用示例:
    - count = _trip_count_from_op(loop_op)

    关联文件:
    - spec: spec/analysis/analysis_engine.md
    - test: test/analysis/test_analysis.py
    - 功能实现: kernel_gen/analysis/analysis.py
    """
    attr = op.attributes.get("trip_count")
    if attr is None:
        return sp.Integer(1)
    expr = _trip_count_attr_to_expr(attr)
    if expr is None:
        raise AnalysisError("trip_count must be integer or symbol")
    return expr


def _numel_from_shape(shape: ArrayAttr) -> sp.Basic | None:
    """基于 shape 计算元素数量。

    创建者: 金铲铲大作战
    最后一次更改: 金铲铲大作战

    功能说明:
    - 按维度依次相乘生成表达式。

    使用示例:
    - numel = _numel_from_shape(mem_type.shape)

    关联文件:
    - spec: spec/analysis/analysis_kernel.md
    - test: test/analysis/test_analysis.py
    - 功能实现: kernel_gen/analysis/analysis.py
    """
    expr = sp.Integer(1)
    for dim in shape.data:
        dim_expr = _dim_to_expr(dim)
        if dim_expr is None:
            return None
        expr = expr * dim_expr
    return expr


def _numel_from_mem_type(mem_type: NnMemoryType) -> sp.Basic | None:
    """计算 nn.memory 的元素数量。

    创建者: 金铲铲大作战
    最后一次更改: 金铲铲大作战

    功能说明:
    - 使用 shape 维度乘积作为元素总数。

    使用示例:
    - numel = _numel_from_mem_type(mem_type)

    关联文件:
    - spec: spec/analysis/analysis_kernel.md
    - test: test/analysis/test_analysis.py
    - 功能实现: kernel_gen/analysis/analysis.py
    """
    return _numel_from_shape(mem_type.shape)


def _symbol_value_to_expr(value: SSAValue) -> sp.Basic | None:
    """将 `!symbol.int` SSA value 转为 sympy 表达式。

    创建者: 金铲铲大作战
    最后一次更改: 金铲铲大作战

    功能说明:
    - 静态整数返回 Integer。
    - 符号表达式返回对应 SymbolDim 符号。

    使用示例:
    - expr = _symbol_value_to_expr(op.sizes[0])

    关联文件:
    - spec: spec/analysis/analysis_kernel.md
    - test: test/analysis/test_analysis.py
    - 功能实现: kernel_gen/analysis/analysis.py
    """
    if not isinstance(value.type, SymbolValueType):
        return None
    return _to_symbol(value.type.get_value())


def _numel_from_symbol_values(values: Sequence[SSAValue]) -> sp.Basic | None:
    """将 `!symbol.int` operand 列表转为元素总数表达式。

    创建者: 金铲铲大作战
    最后一次更改: 金铲铲大作战

    功能说明:
    - 逐项转换为 sympy 表达式并相乘。
    - 任一 operand 不是 `!symbol.int` 时返回 None。

    使用示例:
    - numel = _numel_from_symbol_values(op.sizes)

    关联文件:
    - spec: spec/analysis/analysis_kernel.md
    - test: test/analysis/test_analysis.py
    - 功能实现: kernel_gen/analysis/analysis.py
    """
    expr = sp.Integer(1)
    for value in values:
        dim_expr = _symbol_value_to_expr(value)
        if dim_expr is None:
            return None
        expr = expr * dim_expr
    return expr


def _should_ignore_kernel_op(op: Operation) -> bool:
    """判断是否忽略 kernel 分析 op。

    创建者: 金铲铲大作战
    最后一次更改: 金铲铲大作战

    功能说明:
    - func.return 与 arith.constant 默认忽略。
    - symbol.get_dim/get_stride、arch.*、tuner.param 视为元信息 op 忽略。

    使用示例:
    - if _should_ignore_kernel_op(op): ...

    关联文件:
    - spec: spec/analysis/analysis_kernel.md
    - test: test/analysis/test_analysis.py
    - 功能实现: kernel_gen/analysis/analysis.py
    """
    if isinstance(op, func.ReturnOp):
        return True
    if isinstance(op, arith.ConstantOp):
        return True
    op_name = getattr(op, "name", None)
    if isinstance(op_name, str):
        if op_name in {"symbol.get_dim", "symbol.get_stride", "tuner.param"}:
            return True
        if op_name.startswith("arch."):
            return True
    return False


def _warn_skip_kernel_op(op: Operation, reason: str) -> None:
    """输出跳过 op 的告警。

    创建者: 金铲铲大作战
    最后一次更改: 金铲铲大作战

    功能说明:
    - 使用 warnings.warn 提示未知 op 被跳过。

    使用示例:
    - _warn_skip_kernel_op(op, "unsupported op")

    关联文件:
    - spec: spec/analysis/analysis_kernel.md
    - test: test/analysis/test_analysis.py
    - 功能实现: kernel_gen/analysis/analysis.py
    """
    warnings.warn(f"analysis_kernel skip {op.name}: {reason}", UserWarning)


def _iter_block_ops(ops: Iterable[Operation]) -> Iterable[Operation]:
    """递归遍历 block 内 ops。

    创建者: 金铲铲大作战
    最后一次更改: 金铲铲大作战

    功能说明:
    - 逐 op 遍历并展开其 region 内嵌套 block。

    使用示例:
    - for op in _iter_block_ops(block.ops): ...

    关联文件:
    - spec: spec/analysis/analysis_kernel.md
    - test: test/analysis/test_analysis.py
    - 功能实现: kernel_gen/analysis/analysis.py
    """
    for op in ops:
        yield op
        for region in op.regions:
            for block in region.blocks:
                yield from _iter_block_ops(block.ops)


def _iter_func_ops(func_op: func.FuncOp) -> Iterable[Operation]:
    """遍历 func.func 内所有 ops。

    创建者: 金铲铲大作战
    最后一次更改: 金铲铲大作战

    功能说明:
    - 对 func.body 中所有 block 进行递归遍历。

    使用示例:
    - for op in _iter_func_ops(func_op): ...

    关联文件:
    - spec: spec/analysis/analysis_kernel.md
    - test: test/analysis/test_analysis.py
    - 功能实现: kernel_gen/analysis/analysis.py
    """
    for block in func_op.body.blocks:
        yield from _iter_block_ops(block.ops)


def _sum_expr(items: Iterable[sp.Basic]) -> sp.Basic:
    """求和 sympy 表达式列表。

    创建者: 金铲铲大作战
    最后一次更改: 金铲铲大作战

    功能说明:
    - 逐项累加并返回求和结果。

    使用示例:
    - total = _sum_expr([expr_a, expr_b])

    关联文件:
    - spec: spec/analysis/analysis_kernel.md
    - test: test/analysis/test_analysis.py
    - 功能实现: kernel_gen/analysis/analysis.py
    """
    total = sp.Integer(0)
    for item in items:
        total = total + item
    return total


def _record_value_read(
    value: SSAValue,
    amount: sp.Basic,
    value_keys: dict[SSAValue, str],
    traffic_map: dict[str, list[sp.Basic]],
) -> None:
    """记录 value 的读流量。

    创建者: 金铲铲大作战
    最后一次更改: 金铲铲大作战

    功能说明:
    - 若 value 未登记稳定 key，则忽略记录。

    使用示例:
    - _record_value_read(arg0, bytes_expr, value_keys, traffic_map)

    关联文件:
    - spec: spec/analysis/analysis_kernel.md
    - test: test/analysis/test_analysis.py
    - 功能实现: kernel_gen/analysis/analysis.py
    """
    key = value_keys.get(value)
    if key is None:
        return
    traffic = traffic_map.setdefault(key, [sp.Integer(0), sp.Integer(0)])
    traffic[0] = traffic[0] + amount


def _record_value_write(
    value: SSAValue,
    amount: sp.Basic,
    value_keys: dict[SSAValue, str],
    traffic_map: dict[str, list[sp.Basic]],
) -> None:
    """记录 value 的写流量。

    创建者: 金铲铲大作战
    最后一次更改: 金铲铲大作战

    功能说明:
    - 若 value 未登记稳定 key，则忽略记录。

    使用示例:
    - _record_value_write(result, bytes_expr, value_keys, traffic_map)

    关联文件:
    - spec: spec/analysis/analysis_kernel.md
    - test: test/analysis/test_analysis.py
    - 功能实现: kernel_gen/analysis/analysis.py
    """
    key = value_keys.get(value)
    if key is None:
        return
    traffic = traffic_map.setdefault(key, [sp.Integer(0), sp.Integer(0)])
    traffic[1] = traffic[1] + amount


def _register_op_results(
    op: Operation,
    op_index: int,
    write_bytes: sp.Basic,
    value_keys: dict[SSAValue, str],
    traffic_map: dict[str, list[sp.Basic]],
) -> None:
    """为 op 结果注册稳定 key，并记录写流量。

    创建者: 金铲铲大作战
    最后一次更改: 金铲铲大作战

    功能说明:
    - 统一生成 `op{idx}.result{n}` 形式的 value key。
    - 将写流量累计到结果 value。

    使用示例:
    - _register_op_results(op, 0, bytes_expr, value_keys, traffic_map)

    关联文件:
    - spec: spec/analysis/analysis_kernel.md
    - test: test/analysis/test_analysis.py
    - 功能实现: kernel_gen/analysis/analysis.py
    """
    for result_index, result_value in enumerate(op.results):
        key = f"op{op_index}.result{result_index}"
        value_keys[result_value] = key
        traffic_map.setdefault(key, [sp.Integer(0), sp.Integer(0)])
        _record_value_write(result_value, write_bytes, value_keys, traffic_map)


def _ensure_same_shape(lhs: Memory, rhs: Memory, message: str) -> None:
    """校验两份 Memory 形状完全一致。

    创建者: 金铲铲大作战
    最后一次更改: 金铲铲大作战

    功能说明:
    - 若形状不一致则抛出 AnalysisError。

    使用示例:
    - _ensure_same_shape(lhs, rhs, \"Shape mismatch\")

    关联文件:
    - spec: spec/analysis/analysis_kernel.md
    - test: test/analysis/test_analysis.py
    - 功能实现: kernel_gen/analysis/analysis.py
    """
    if lhs.shape.get_values() != rhs.shape.get_values():
        raise AnalysisError(message)


def _element_count(memory: Memory) -> sp.Basic:
    """计算 Memory 的元素数量表达式。

    创建者: 金铲铲大作战
    最后一次更改: 金铲铲大作战

    功能说明:
    - 将 Memory.shape 转换为乘积表达式。

    使用示例:
    - _element_count(Memory([\"A\", \"B\"], dtype))

    关联文件:
    - spec: spec/analysis/analysis_kernel.md
    - test: test/analysis/test_analysis.py
    - 功能实现: kernel_gen/analysis/analysis.py
    """
    return _product(memory.shape.get_values())


def _ensure_broadcastable(input_mem: Memory, output_mem: Memory) -> None:
    """校验 broadcast 形状规则。

    创建者: 金铲铲大作战
    最后一次更改: 金铲铲大作战

    功能说明:
    - 输出 rank 不小于输入 rank。
    - 尾维对齐，维度相等或输入维为 1。

    使用示例:
    - _ensure_broadcastable(inp, out)

    关联文件:
    - spec: spec/analysis/analysis_kernel.md
    - test: test/analysis/test_analysis.py
    - 功能实现: kernel_gen/analysis/analysis.py
    """
    input_shape = input_mem.shape.get_values()
    output_shape = output_mem.shape.get_values()
    if len(output_shape) < len(input_shape):
        raise AnalysisError("Broadcast output rank must be >= input rank")
    offset = len(output_shape) - len(input_shape)
    for idx, in_dim in enumerate(input_shape):
        out_dim = output_shape[offset + idx]
        if in_dim == out_dim:
            continue
        if isinstance(in_dim, int) and in_dim == 1:
            continue
        raise AnalysisError("Broadcast dimension mismatch")


def _ensure_matmul_shape(lhs: Memory, rhs: Memory, out: Memory) -> None:
    """校验 matmul 形状规则。

    创建者: 金铲铲大作战
    最后一次更改: 金铲铲大作战

    功能说明:
    - 仅支持 rank-2。
    - inner 维度相等，输出匹配 [M, N]。

    使用示例:
    - _ensure_matmul_shape(lhs, rhs, out)

    关联文件:
    - spec: spec/analysis/analysis_kernel.md
    - test: test/analysis/test_analysis.py
    - 功能实现: kernel_gen/analysis/analysis.py
    """
    lhs_shape = lhs.shape.get_values()
    rhs_shape = rhs.shape.get_values()
    out_shape = out.shape.get_values()
    if len(lhs_shape) != 2 or len(rhs_shape) != 2 or len(out_shape) != 2:
        raise AnalysisError("Matmul requires rank-2 tensors")
    if lhs_shape[1] != rhs_shape[0]:
        raise AnalysisError("Matmul inner dimension mismatch")
    if out_shape[0] != lhs_shape[0] or out_shape[1] != rhs_shape[1]:
        raise AnalysisError("Matmul output shape mismatch")


def analyze_elementwise(
    lhs: Memory,
    rhs: Memory | int,
    out: Memory,
    *,
    dtype_size: int | None = None,
    predicate_size: int | None = None,
    op_kind: str = "arith",
    read_mask: Sequence[bool] | None = None,
    write_output: bool = True,
) -> OpStats:
    """分析逐元素算术或比较算子的统计量。

    创建者: 金铲铲大作战
    最后一次更改: 金铲铲大作战

    功能说明:
    - 逐元素算术与比较遵循形状完全一致约束。
    - 比较输出写入使用 predicate_size。

    使用示例:
    - analyze_elementwise(lhs, rhs, out, op_kind="arith")

    关联文件:
    - spec: spec/analysis/analysis_kernel.md
    - test: test/analysis/test_analysis.py
    - 功能实现: kernel_gen/analysis/analysis.py
    """
    if isinstance(rhs, Memory):
        _ensure_same_shape(lhs, rhs, "Elementwise input shape mismatch")
    _ensure_same_shape(lhs, out, "Elementwise output shape mismatch")

    element_count = _element_count(out)
    compute = element_count
    dtype_expr = _size_symbol(dtype_size, "S")
    pred_expr = _size_symbol(predicate_size, "P")

    if read_mask is None:
        read_mask = [True, True] if isinstance(rhs, Memory) else [True]
    else:
        expected_len = 2 if isinstance(rhs, Memory) else 1
        if len(read_mask) != expected_len:
            raise AnalysisError("read_mask length mismatch")

    read_bytes = sp.Integer(0)
    if read_mask[0]:
        read_bytes += element_count * dtype_expr
    if isinstance(rhs, Memory) and read_mask[1]:
        read_bytes += element_count * dtype_expr

    if op_kind == "compare":
        write_bytes = element_count * pred_expr if write_output else sp.Integer(0)
    else:
        write_bytes = element_count * dtype_expr if write_output else sp.Integer(0)
    return OpStats(compute, read_bytes, write_bytes)


def analyze_broadcast(
    input_mem: Memory,
    output_mem: Memory,
    *,
    dtype_size: int | None = None,
    read_mask: Sequence[bool] | None = None,
    write_output: bool = True,
) -> OpStats:
    """分析 broadcast 的统计量。

    创建者: 金铲铲大作战
    最后一次更改: 金铲铲大作战

    功能说明:
    - 校验尾维对齐与 singleton 维扩张规则。
    - 基线统计按物化输出计写。

    使用示例:
    - analyze_broadcast(inp, out)

    关联文件:
    - spec: spec/analysis/analysis_kernel.md
    - test: test/analysis/test_analysis.py
    - 功能实现: kernel_gen/analysis/analysis.py
    """
    _ensure_broadcastable(input_mem, output_mem)
    dtype_expr = _size_symbol(dtype_size, "S")
    input_count = _element_count(input_mem)
    output_count = _element_count(output_mem)
    if read_mask is None:
        read_mask = [True]
    elif len(read_mask) != 1:
        raise AnalysisError("read_mask length mismatch")
    read_bytes = input_count * dtype_expr if read_mask[0] else sp.Integer(0)
    write_bytes = output_count * dtype_expr if write_output else sp.Integer(0)
    return OpStats(sp.Integer(0), read_bytes, write_bytes)


def analyze_matmul(
    lhs: Memory,
    rhs: Memory,
    out: Memory,
    *,
    dtype_size: int | None = None,
    read_mask: Sequence[bool] | None = None,
    write_output: bool = True,
) -> OpStats:
    """分析 matmul 的统计量。

    创建者: 金铲铲大作战
    最后一次更改: 金铲铲大作战

    功能说明:
    - 校验二维收缩规则。
    - 统计 2*M*N*K 计算量。

    使用示例:
    - analyze_matmul(lhs, rhs, out)

    关联文件:
    - spec: spec/analysis/analysis_kernel.md
    - test: test/analysis/test_analysis.py
    - 功能实现: kernel_gen/analysis/analysis.py
    """
    _ensure_matmul_shape(lhs, rhs, out)
    dtype_expr = _size_symbol(dtype_size, "S")
    m, k = lhs.shape.get_values()
    _, n = rhs.shape.get_values()
    m_expr = _to_symbol(m)
    n_expr = _to_symbol(n)
    k_expr = _to_symbol(k)
    compute = sp.Integer(2) * m_expr * n_expr * k_expr
    if read_mask is None:
        read_mask = [True, True]
    elif len(read_mask) != 2:
        raise AnalysisError("read_mask length mismatch")
    read_bytes = sp.Integer(0)
    if read_mask[0]:
        read_bytes += _to_symbol(m) * _to_symbol(k) * dtype_expr
    if read_mask[1]:
        read_bytes += _to_symbol(k) * _to_symbol(n) * dtype_expr
    write_bytes = m_expr * n_expr * dtype_expr if write_output else sp.Integer(0)
    return OpStats(compute, read_bytes, write_bytes)


def _dtype_string(element_type: Attribute) -> str:
    """将类型属性转为稳定 dtype 字符串。

    创建者: 朽木露琪亚
    最后一次更改: 朽木露琪亚

    功能说明:
    - 统一复用 `str(element_type)` 作为展示与测试断言口径。

    使用示例:
    - text = _dtype_string(i32)

    关联文件:
    - spec: spec/analysis/analysis_engine.md
    - test: test/analysis/test_analysis.py
    - 功能实现: kernel_gen/analysis/analysis.py
    """

    return str(element_type)


def _is_scalar_type(attr: Attribute) -> bool:
    """判断是否为标量数值类型。

    创建者: 朽木露琪亚
    最后一次更改: 朽木露琪亚

    功能说明:
    - 当前支持整数与浮点标量。

    使用示例:
    - assert _is_scalar_type(i32)

    关联文件:
    - spec: spec/analysis/analysis_engine.md
    - test: test/analysis/test_analysis.py
    - 功能实现: kernel_gen/analysis/analysis.py
    """

    return isinstance(
        attr,
        (IntegerType, Float16Type, BFloat16Type, Float32Type, Float64Type),
    )


def _analyze_scalar_kernel_op(op: Operation, config: AnalysisConfig) -> _AnalyzedOp | None:
    """分析单个标量 kernel 风格 op。

    创建者: 朽木露琪亚
    最后一次更改: 朽木露琪亚

    功能说明:
    - 为 `kernel.binary_elewise/select` 的单结果标量形态生成新结果结构。
    - 该入口只服务 A1 的单 op 统一入口基线，不替代后续 A2 的完整分类收口。

    使用示例:
    - analyzed = _analyze_scalar_kernel_op(fake_kernel_add_op, config)

    关联文件:
    - spec: spec/analysis/analysis_engine.md
    - test: test/analysis/test_analysis.py
    - 功能实现: kernel_gen/analysis/analysis.py
    """

    from kernel_gen.analysis.compute.kernel import analyze_scalar_kernel_op

    return analyze_scalar_kernel_op(op, config)


def _analyze_nn_elementwise_op(op: Operation, config: AnalysisConfig) -> _AnalyzedOp | None:
    """分析 nn 逐元素算术/比较 op。

    创建者: 朽木露琪亚
    最后一次更改: 朽木露琪亚

    功能说明:
    - 生成 vector 分类 compute item。
    - 兼容保留旧 read/write alias。

    使用示例:
    - analyzed = _analyze_nn_elementwise_op(op, config)

    关联文件:
    - spec: spec/analysis/analysis_engine.md
    - test: test/analysis/test_analysis.py
    - 功能实现: kernel_gen/analysis/analysis.py
    """

    from kernel_gen.analysis.compute.nn import analyze_nn_elementwise_op

    return analyze_nn_elementwise_op(op, config)


def _analyze_nn_matmul_ir_op(op: Operation, config: AnalysisConfig) -> _AnalyzedOp | None:
    """分析 nn.matmul op。

    创建者: 朽木露琪亚
    最后一次更改: 朽木露琪亚

    功能说明:
    - 生成 tensor 分类 compute item。

    使用示例:
    - analyzed = _analyze_nn_matmul_ir_op(op, config)

    关联文件:
    - spec: spec/analysis/analysis_engine.md
    - test: test/analysis/test_analysis.py
    - 功能实现: kernel_gen/analysis/analysis.py
    """

    from kernel_gen.analysis.compute.nn import analyze_nn_matmul_ir_op

    return analyze_nn_matmul_ir_op(op, config)


def _analyze_dma_ir_op(op: Operation, config: AnalysisConfig) -> _AnalyzedOp | None:
    """分析当前公开 DMA 分支。

    创建者: 朽木露琪亚
    最后一次更改: 金铲铲大作战

    功能说明:
    - 当前承接 `dma.load/copy/store/slice`。
    - 其余 DMA 分支保持 `skip + warning` 口径；公开 DMA 前置条件非法保持 `hard error`。

    使用示例:
    - analyzed = _analyze_dma_ir_op(op, config)

    关联文件:
    - spec: spec/analysis/analysis_engine.md
    - test: test/analysis/test_analysis.py
    - 功能实现: kernel_gen/analysis/analysis.py
    """
    from kernel_gen.analysis.memory import analyze_dma_memory_op

    analyzed = analyze_dma_memory_op(op, config)
    if analyzed is None:
        return None
    return _coerce_memory_analyzer_result(op, analyzed, config)


def _merge_analyzed_ops(op: Operation, analyzed_ops: Sequence[_AnalyzedOp]) -> _AnalyzedOp:
    """合并多个 analyzer 的单 op 统计。

    创建者: 金铲铲大作战
    最后一次更改: 金铲铲大作战

    功能说明:
    - 汇总 compute/memory 的统计项。
    - compute/read/write 只作为 derived alias，由 items 求和得到。
    - 允许同一 op 同时命中 compute 与 memory analyzer。

    使用示例:
    - merged = _merge_analyzed_ops(op, [analyzed_compute, analyzed_memory])

    关联文件:
    - spec: spec/analysis/analysis_engine.md
    - test: test/analysis/test_analysis.py
    - 功能实现: kernel_gen/analysis/analysis.py
    """
    compute_items: list[ComputeItem] = []
    memory_items: list[MemoryItem] = []
    value_reads: list[tuple[SSAValue, sp.Basic]] = []
    direct_writes: list[tuple[SSAValue, sp.Basic]] = []
    result_write_bytes = sp.Integer(0)

    for analyzed in analyzed_ops:
        compute_items.extend(analyzed.compute_items)
        memory_items.extend(analyzed.memory_items)
        value_reads.extend(analyzed.value_reads)
        direct_writes.extend(analyzed.direct_writes)
        result_write_bytes += analyzed.result_write_bytes

    compute_total = _sum_expr(item.amount for item in compute_items)
    read_bytes_total = _sum_expr(item.bytes for item in memory_items if item.access == "read")
    write_bytes_total = _sum_expr(item.bytes for item in memory_items if item.access == "write")

    return _AnalyzedOp(
        op_name=op.name,
        compute_items=compute_items,
        memory_items=memory_items,
        compute=compute_total,
        read_bytes=read_bytes_total,
        write_bytes=write_bytes_total,
        value_reads=tuple(value_reads),
        direct_writes=tuple(direct_writes),
        result_write_bytes=result_write_bytes,
    )


def _coerce_memory_analyzer_result(
    op: Operation,
    analyzed: DmaMemoryAnalysis | _AnalyzedOp,
    config: AnalysisConfig,
) -> _AnalyzedOp:
    """将 memory analyzer 结果归一为 `_AnalyzedOp`。

    创建者: 金铲铲大作战
    最后一次更改: 金铲铲大作战

    功能说明:
    - 兼容 DMA memory analyzer 现有输出结构。
    - read/write 作为 derived alias，来自 memory_items 求和。
    - 允许 memory analyzer 直接返回 `_AnalyzedOp`。
    - 对 `dma.cast` 追加 vector compute item，数量按结果 numel 计算。

    使用示例:
    - normalized = _coerce_memory_analyzer_result(op, analyzed, config)

    关联文件:
    - spec: spec/analysis/analysis_engine.md
    - test: test/analysis/test_analysis.py
    - 功能实现: kernel_gen/analysis/analysis.py
    """
    if isinstance(analyzed, _AnalyzedOp):
        return analyzed
    if isinstance(analyzed, DmaMemoryAnalysis):
        memory_items: list[MemoryItem] = []
        if config.enable_memory:
            memory_items = [
                MemoryItem(
                    path=item[0],
                    access=item[1],
                    bytes=item[2],
                    latency_ns=item[3],
                    bandwidth=item[4],
                    time_ns=item[5],
                )
                for item in analyzed.memory_items
            ]
        compute_items: list[ComputeItem] = []
        if config.enable_compute and op.name == "dma.cast" and op.results:
            result_type = op.results[0].type
            if isinstance(result_type, NnMemoryType):
                numel = _numel_from_mem_type(result_type)
                if numel is not None:
                    compute_items.append(
                        ComputeItem(
                            kind=ComputeKind.VECTOR,
                            amount=numel,
                            dtype=_dtype_string(result_type.element_type),
                        )
                    )
        compute_total = _sum_expr(item.amount for item in compute_items)
        read_bytes = _sum_expr(item.bytes for item in memory_items if item.access == "read")
        write_bytes = _sum_expr(item.bytes for item in memory_items if item.access == "write")
        return _AnalyzedOp(
            op_name=analyzed.op_name,
            compute_items=compute_items,
            memory_items=memory_items,
            compute=compute_total,
            read_bytes=read_bytes,
            write_bytes=write_bytes,
            value_reads=analyzed.value_reads if config.enable_memory else (),
            direct_writes=analyzed.direct_writes if config.enable_memory else (),
            result_write_bytes=analyzed.result_write_bytes if config.enable_memory else sp.Integer(0),
        )
    raise AnalysisError(f"unsupported memory analyzer result: {type(analyzed).__name__}")


def _analyze_ir_op(op: Operation, config: AnalysisConfig) -> _AnalyzedOp | None:
    """分析单个 IR op。

    创建者: 朽木露琪亚
    最后一次更改: 金铲铲大作战

    功能说明:
    - 统一分发 compute/memory registry。
    - 未支持 op 返回 `None`，由上层决定是否 warning/skip。
    - 允许同一 op 同时命中 compute 与 memory analyzer。

    使用示例:
    - analyzed = _analyze_ir_op(op, config)

    关联文件:
    - spec: spec/analysis/analysis_engine.md
    - test: test/analysis/test_analysis.py
    - 功能实现: kernel_gen/analysis/analysis.py
    """
    analyzed_ops: list[_AnalyzedOp] = []
    for analyzer in iter_compute_analyzers_for_op(op):
        analyzed = analyzer(op, config)
        if analyzed is not None:
            analyzed_ops.append(analyzed)
    for analyzer in iter_memory_analyzers_for_op(op):
        analyzed = analyzer(op, config)
        if analyzed is not None:
            analyzed_ops.append(_coerce_memory_analyzer_result(op, analyzed, config))
    if not analyzed_ops:
        return None
    return _merge_analyzed_ops(op, analyzed_ops)


def _scale_memory_item(item: MemoryItem, multiplier: sp.Basic) -> MemoryItem:
    """按倍数缩放 MemoryItem 的字节与时间指标。

    创建者: 朽木露琪亚
    最后一次更改: 朽木露琪亚

    功能说明:
    - bytes/latency/time 按倍率缩放，bandwidth 保持不变。

    使用示例:
    - scaled = _scale_memory_item(item, sp.Integer(4))

    关联文件:
    - spec: spec/analysis/analysis_engine.md
    - test: test/analysis/test_analysis.py
    - 功能实现: kernel_gen/analysis/analysis.py
    """
    if multiplier == 1:
        return item
    latency = item.latency_ns * multiplier if item.latency_ns is not None else None
    time_ns = item.time_ns * multiplier if item.time_ns is not None else None
    return MemoryItem(
        path=item.path,
        access=item.access,
        bytes=item.bytes * multiplier,
        latency_ns=latency,
        bandwidth=item.bandwidth,
        time_ns=time_ns,
    )


def _scale_analyzed_op(analyzed: _AnalyzedOp, multiplier: sp.Basic) -> _AnalyzedOp:
    """按倍数缩放 `_AnalyzedOp` 的统计量。

    创建者: 朽木露琪亚
    最后一次更改: 朽木露琪亚

    功能说明:
    - 统一缩放 compute/read/write 及 value traffic。

    使用示例:
    - scaled = _scale_analyzed_op(analyzed, sp.Integer(2))

    关联文件:
    - spec: spec/analysis/analysis_engine.md
    - test: test/analysis/test_analysis.py
    - 功能实现: kernel_gen/analysis/analysis.py
    """
    if multiplier == 1:
        return analyzed
    return _AnalyzedOp(
        op_name=analyzed.op_name,
        compute_items=[
            ComputeItem(item.kind, item.amount * multiplier, item.dtype)
            for item in analyzed.compute_items
        ],
        memory_items=[_scale_memory_item(item, multiplier) for item in analyzed.memory_items],
        compute=analyzed.compute * multiplier,
        read_bytes=analyzed.read_bytes * multiplier,
        write_bytes=analyzed.write_bytes * multiplier,
        value_reads=tuple((value, amount * multiplier) for value, amount in analyzed.value_reads),
        direct_writes=tuple((value, amount * multiplier) for value, amount in analyzed.direct_writes),
        result_write_bytes=analyzed.result_write_bytes * multiplier,
    )


def _result_from_analyzed_op(op: Operation, analyzed: _AnalyzedOp, config: AnalysisConfig) -> AnalysisResult:
    """将内部单 op 统计转换为公开 AnalysisResult。

    创建者: 朽木露琪亚
    最后一次更改: 朽木露琪亚

    功能说明:
    - 单 op 返回时附带一条 `KernelOpCost` derived alias。
    - 按配置决定是否写回 op attrs。

    使用示例:
    - result = _result_from_analyzed_op(op, analyzed, config)

    关联文件:
    - spec: spec/analysis/analysis_engine.md
    - test: test/analysis/test_analysis.py
    - 功能实现: kernel_gen/analysis/analysis.py
    """

    result = _to_analysis_result(
        analyzed.compute_items,
        analyzed.memory_items,
        op_costs=(
            KernelOpCost(
                op_index=0,
                op_name=analyzed.op_name,
                compute=analyzed.compute,
                read_bytes=analyzed.read_bytes,
                write_bytes=analyzed.write_bytes,
            ),
        ),
        value_reads=analyzed.value_reads,
        direct_writes=analyzed.direct_writes,
        result_write_bytes=analyzed.result_write_bytes,
    )
    if config.write_op_attrs:
        _write_analysis_attrs(op, result)
    return result


def analysis(
    op: Operation,
    config: AnalysisConfig,
    otherargs: Iterable[object] | None = None,
) -> AnalysisResult:
    """统一分析入口。

    创建者: 朽木露琪亚
    最后一次更改: 朽木露琪亚

    功能说明:
    - 支持单个 IR op 与 `func.func`。
    - `func.func` 路径通过逐 op 调用统一入口聚合，不再保留独立主线。

    使用示例:
    - result = analysis(op, AnalysisConfig(enable_compute=True, enable_memory=False))

    关联文件:
    - spec: spec/analysis/analysis_engine.md
    - test: test/analysis/test_analysis.py
    - 功能实现: kernel_gen/analysis/analysis.py
    """

    if not isinstance(config, AnalysisConfig):
        raise AnalysisError("config must be AnalysisConfig")
    if not isinstance(config.predicate_size, int) or config.predicate_size <= 0:
        raise AnalysisError("predicate_size must be positive")
    if isinstance(op, func.FuncOp):
        return _analysis_func(op, config, otherargs)
    if _should_ignore_kernel_op(op):
        return _to_analysis_result([], [])
    analyzed = _analyze_ir_op(op, config)
    if analyzed is None:
        _warn_skip_kernel_op(op, "unsupported op")
        return _to_analysis_result([], [])
    return _result_from_analyzed_op(op, analyzed, config)


def _analysis_func(
    func_op: func.FuncOp,
    config: AnalysisConfig,
    otherargs: Iterable[object] | None,
) -> AnalysisResult:
    """分析单个 func.func。

    创建者: 朽木露琪亚
    最后一次更改: 朽木露琪亚

    功能说明:
    - 按 func body 递归遍历 ops，支持 loop/region trip_count 乘算。
    - 继续维护稳定 `value_traffic`，供 facade/pass 兼容使用。

    使用示例:
    - result = _analysis_func(func_op, config, None)

    关联文件:
    - spec: spec/analysis/analysis_engine.md
    - test: test/analysis/test_analysis.py
    - 功能实现: kernel_gen/analysis/analysis.py
    """

    if not isinstance(func_op, func.FuncOp):
        raise AnalysisError("func_op must be func.FuncOp")
    args = otherargs if otherargs is not None else config.otherargs
    if args is not None and not isinstance(args, IterableABC):
        raise AnalysisError("args must be iterable")
    arg_list = list(args) if args is not None else None
    func_args = list(func_op.body.blocks[0].args)
    if arg_list is not None and len(arg_list) != len(func_args):
        raise AnalysisError("args length mismatch")

    value_keys: dict[SSAValue, str] = {}
    traffic_map: dict[str, list[sp.Basic]] = {}
    for index, arg in enumerate(func_args):
        key = f"arg{index}"
        value_keys[arg] = key
        traffic_map[key] = [sp.Integer(0), sp.Integer(0)]

    compute_items: list[ComputeItem] = []
    memory_items: list[MemoryItem] = []
    op_costs: list[KernelOpCost] = []

    def _walk_ops(ops: Iterable[Operation], multiplier: sp.Basic) -> None:
        for op in ops:
            trip_count = _trip_count_from_op(op)
            self_multiplier = multiplier
            child_multiplier = multiplier
            if op.regions:
                child_multiplier = multiplier * trip_count
            else:
                self_multiplier = multiplier * trip_count

            analyzed: _AnalyzedOp | None = None
            if not _should_ignore_kernel_op(op):
                analyzed = _analyze_ir_op(op, config)

            if analyzed is None:
                if not _should_ignore_kernel_op(op) and not op.regions:
                    _warn_skip_kernel_op(op, "unsupported op")
            else:
                op_result = _result_from_analyzed_op(
                    op,
                    _scale_analyzed_op(analyzed, self_multiplier),
                    config,
                )
                if op_result.op_costs:
                    op_index = len(op_costs)
                    op_summary = op_result.op_costs[0]
                    op_costs.append(
                        KernelOpCost(
                            op_index=op_index,
                            op_name=op_summary.op_name,
                            compute=op_summary.compute,
                            read_bytes=op_summary.read_bytes,
                            write_bytes=op_summary.write_bytes,
                        )
                    )
                    compute_items.extend(op_result.compute_items)
                    memory_items.extend(op_result.memory_items)

                    if config.enable_memory:
                        for value, amount in op_result._value_reads:
                            _record_value_read(value, amount, value_keys, traffic_map)
                        for value, amount in op_result._direct_writes:
                            _record_value_write(value, amount, value_keys, traffic_map)
                        if op_result._result_write_bytes != 0:
                            _register_op_results(
                                op,
                                op_index,
                                op_result._result_write_bytes,
                                value_keys,
                                traffic_map,
                            )
                        elif len(op.results) > 0:
                            _register_op_results(
                                op,
                                op_index,
                                sp.Integer(0),
                                value_keys,
                                traffic_map,
                            )

            for region in op.regions:
                for block in region.blocks:
                    _walk_ops(block.ops, child_multiplier)

    for block in func_op.body.blocks:
        _walk_ops(block.ops, sp.Integer(1))

    value_traffic = [ValueTraffic(key, values[0], values[1]) for key, values in traffic_map.items()]
    result = _to_analysis_result(
        compute_items,
        memory_items,
        op_costs=op_costs,
        value_traffic=value_traffic,
        func_name=func_op.sym_name.data,
    )
    if config.write_func_attrs:
        _write_analysis_attrs(func_op, result)
    return result


def _analysis_result_to_kernel_summary(result: AnalysisResult) -> AnalyzeKernelSummary:
    """将统一入口结果适配为旧 AnalyzeKernelSummary。

    创建者: 朽木露琪亚
    最后一次更改: 朽木露琪亚

    功能说明:
    - 作为 `analyze_kernel(...)` facade 的唯一适配层。

    使用示例:
    - summary = _analysis_result_to_kernel_summary(result)

    关联文件:
    - spec: spec/analysis/analysis_kernel.md
    - test: test/analysis/test_analysis.py
    - 功能实现: kernel_gen/analysis/analysis.py
    """

    return AnalyzeKernelSummary(
        func_name=result.func_name or "",
        op_costs=list(result.op_costs),
        value_traffic=list(result.value_traffic),
        total_compute=result.total_compute,
        total_read_bytes=result.total_read_bytes,
        total_write_bytes=result.total_write_bytes,
    )


def analyze_kernel(
    func_op: func.FuncOp,
    args: Iterable[object] | None = None,
    *,
    predicate_size: int = 1,
    dtype_size_overrides: dict[str, int] | None = None,
    attach_attrs: bool = False,
) -> AnalyzeKernelSummary:
    """分析单个 func.func 的 compute/read/write 与 value_traffic。

    创建者: 金铲铲大作战
    最后一次更改: 金铲铲大作战

    功能说明:
    - 以 func.FuncOp 为输入，输出逐 op 统计与稳定 value_traffic。
    - 未知 op 执行 skip + warning，不计入总量。

    使用示例:
    - summary = analyze_kernel(func_op, dtype_size_overrides={"f32": 4})

    关联文件:
    - spec: spec/analysis/analysis_kernel.md
    - test: test/analysis/test_analysis.py
    - 功能实现: kernel_gen/analysis/analysis.py
    """
    if not isinstance(func_op, func.FuncOp):
        raise AnalysisError("func_op must be func.FuncOp")
    config = AnalysisConfig(
        enable_compute=True,
        enable_memory=True,
        write_op_attrs=False,
        write_func_attrs=attach_attrs,
        predicate_size=predicate_size,
        dtype_size_overrides=dtype_size_overrides,
        otherargs=args,
    )
    return _analysis_result_to_kernel_summary(analysis(func_op, config, args))


def analyze_function(
    ops: Sequence[Operation],
    *,
    dtype_size: int | None = None,
    predicate_size: int | None = None,
) -> AnalysisSummary:
    """按函数级算子序列聚合统计结果。

    创建者: 金铲铲大作战
    最后一次更改: 金铲铲大作战

    功能说明:
    - 逐算子统计并累加，区分中间结果是否物化。

    使用示例:
    - summary = analyze_function([op1, op2])

    关联文件:
    - spec: spec/analysis/analysis_kernel.md
    - test: test/analysis/test_analysis.py
    - 功能实现: kernel_gen/analysis/analysis.py
    """
    produced: dict[str, bool] = {}
    stats_list: list[OpStats] = []
    total = OpStats(sp.Integer(0), sp.Integer(0), sp.Integer(0))

    for op in ops:
        if op.op in {"add", "sub", "mul", "truediv", "eq", "ne", "lt", "le", "gt", "ge", "matmul"}:
            expected_inputs = 2
        elif op.op == "broadcast":
            expected_inputs = 1
        else:
            expected_inputs = None

        if expected_inputs is None:
            raise AnalysisError(f"Unsupported op for analysis: {op.op}")
        if len(op.inputs) != expected_inputs:
            raise AnalysisError("Operation inputs length mismatch")

        read_mask: list[bool] = []
        for ref in op.inputs:
            if ref.name in produced and not produced[ref.name]:
                read_mask.append(False)
            else:
                read_mask.append(True)

        write_output = op.materialize
        op_name = op.op
        if op_name in {"add", "sub", "mul", "truediv"}:
            stats = analyze_elementwise(
                op.inputs[0].memory,
                op.inputs[1].memory,
                op.output.memory,
                dtype_size=dtype_size,
                op_kind="arith",
                read_mask=read_mask,
                write_output=write_output,
            )
        elif op_name in {"eq", "ne", "lt", "le", "gt", "ge"}:
            stats = analyze_elementwise(
                op.inputs[0].memory,
                op.inputs[1].memory,
                op.output.memory,
                dtype_size=dtype_size,
                predicate_size=predicate_size,
                op_kind="compare",
                read_mask=read_mask,
                write_output=write_output,
            )
        elif op_name == "broadcast":
            stats = analyze_broadcast(
                op.inputs[0].memory,
                op.output.memory,
                dtype_size=dtype_size,
                read_mask=read_mask,
                write_output=write_output,
            )
        elif op_name == "matmul":
            stats = analyze_matmul(
                op.inputs[0].memory,
                op.inputs[1].memory,
                op.output.memory,
                dtype_size=dtype_size,
                read_mask=read_mask,
                write_output=write_output,
            )

        stats_list.append(stats)
        total = total + stats
        produced[op.output.name] = op.materialize

    return AnalysisSummary(stats_list, total)


def analyze_add(lhs: Memory, rhs: Memory, out: Memory, *, dtype_size: int | None = None) -> OpStats:
    """分析 add 的统计量。

    创建者: 金铲铲大作战
    最后一次更改: 金铲铲大作战

    功能说明:
    - 逐元素算术统计，形状必须一致。

    使用示例:
    - analyze_add(lhs, rhs, out)

    关联文件:
    - spec: spec/analysis/analysis_kernel.md
    - test: test/analysis/test_analysis.py
    - 功能实现: kernel_gen/analysis/analysis.py
    """
    return analyze_elementwise(lhs, rhs, out, dtype_size=dtype_size)


def analyze_eq(
    lhs: Memory,
    rhs: Memory,
    out: Memory,
    *,
    dtype_size: int | None = None,
    predicate_size: int | None = None,
) -> OpStats:
    """分析 eq 的统计量。

    创建者: 金铲铲大作战
    最后一次更改: 金铲铲大作战

    功能说明:
    - 逐元素比较统计，形状必须一致。

    使用示例:
    - analyze_eq(lhs, rhs, out)

    关联文件:
    - spec: spec/analysis/analysis_kernel.md
    - test: test/analysis/test_analysis.py
    - 功能实现: kernel_gen/analysis/analysis.py
    """
    return analyze_elementwise(
        lhs,
        rhs,
        out,
        dtype_size=dtype_size,
        predicate_size=predicate_size,
        op_kind="compare",
    )


def analyze_broadcast_op(
    input_mem: Memory,
    output_mem: Memory,
    *,
    dtype_size: int | None = None,
) -> OpStats:
    """分析 broadcast 的统计量。

    创建者: 金铲铲大作战
    最后一次更改: 金铲铲大作战

    功能说明:
    - 统计显式 broadcast 的读写量。

    使用示例:
    - analyze_broadcast_op(inp, out)

    关联文件:
    - spec: spec/analysis/analysis_kernel.md
    - test: test/analysis/test_analysis.py
    - 功能实现: kernel_gen/analysis/analysis.py
    """
    return analyze_broadcast(input_mem, output_mem, dtype_size=dtype_size)


def analyze_matmul_op(
    lhs: Memory,
    rhs: Memory,
    out: Memory,
    *,
    dtype_size: int | None = None,
) -> OpStats:
    """分析 matmul 的统计量。

    创建者: 金铲铲大作战
    最后一次更改: 金铲铲大作战

    功能说明:
    - 统计 matmul 的计算量与读写量。

    使用示例:
    - analyze_matmul_op(lhs, rhs, out)

    关联文件:
    - spec: spec/analysis/analysis_kernel.md
    - test: test/analysis/test_analysis.py
    - 功能实现: kernel_gen/analysis/analysis.py
    """
    return analyze_matmul(lhs, rhs, out, dtype_size=dtype_size)
