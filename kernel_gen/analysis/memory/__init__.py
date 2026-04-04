"""Memory-path analysis helpers.

创建者: 朽木露琪亚
最后一次更改: 朽木露琪亚

功能说明:
- 定义访存主线公开使用的 `MemoryPath` 枚举。
- 提供 metric 值归一化与 `bytes + latency + bandwidth -> time_ns` 公式。
- 提供 memory analyzer 的注册装饰器与迭代入口。
- 为 `analysis.py` 与 `memory/dma.py` 提供统一的 path/时间辅助逻辑。

使用示例:
- from kernel_gen.analysis.memory import MemoryPath, normalize_memory_path, time_from_memory_metrics
- assert normalize_memory_path("GM->LM") is MemoryPath.GM_TO_LM

关联文件:
- spec: spec/analysis/analysis_engine.md
- test: test/analysis/test_analysis.py
- 功能实现: kernel_gen/analysis/memory/__init__.py
"""

from __future__ import annotations

from collections.abc import Callable, Iterable, Iterator
from enum import Enum
from typing import TYPE_CHECKING

import sympy as sp

if TYPE_CHECKING:
    from xdsl.ir import Operation

    from kernel_gen.analysis.analysis import AnalysisConfig
    from kernel_gen.analysis.memory.dma import DmaMemoryAnalysis


class MemoryPath(str, Enum):
    """访存路径枚举。

    创建者: 朽木露琪亚
    最后一次更改: 朽木露琪亚

    功能说明:
    - 冻结 analysis 侧访存 path 的正式口径。
    - 同时覆盖 O3/A4 之前已存在的 `compute` 读写路径，避免实现继续回退到自由字符串。

    使用示例:
    - MemoryPath.GM_TO_LM
    - MemoryPath.GM_TO_COMPUTE

    关联文件:
    - spec: spec/analysis/analysis_engine.md
    - test: test/analysis/test_analysis.py
    - 功能实现: kernel_gen/analysis/memory/__init__.py
    """

    GM_TO_GM = "GM->GM"
    GM_TO_SM = "GM->SM"
    SM_TO_LM = "SM->LM"
    GM_TO_LM = "GM->LM"
    LM_TO_GM = "LM->GM"
    GM_TO_TSM = "GM->TSM"
    TSM_TO_TLM = "TSM->TLM"
    FM_TO_TSM = "FM->TSM"
    GM_TO_COMPUTE = "GM->compute"
    LM_TO_COMPUTE = "LM->compute"
    COMPUTE_TO_GM = "compute->GM"
    COMPUTE_TO_LM = "compute->LM"
    UNKNOWN = "unknown"


def normalize_memory_path(path: str | MemoryPath) -> MemoryPath:
    """把 path 文本归一到 `MemoryPath`。

    创建者: 朽木露琪亚
    最后一次更改: 朽木露琪亚

    功能说明:
    - 已知路径统一返回对应 `MemoryPath`。
    - 未知字符串统一收敛为 `MemoryPath.UNKNOWN`，避免继续扩散自由字符串口径。

    使用示例:
    - normalize_memory_path("GM->LM") is MemoryPath.GM_TO_LM
    - normalize_memory_path("FOO->BAR") is MemoryPath.UNKNOWN

    关联文件:
    - spec: spec/analysis/analysis_engine.md
    - test: test/analysis/test_analysis.py
    - 功能实现: kernel_gen/analysis/memory/__init__.py
    """

    if isinstance(path, MemoryPath):
        return path
    try:
        return MemoryPath(path)
    except ValueError:
        return MemoryPath.UNKNOWN


def metric_value_to_expr(value: object) -> sp.Basic | None:
    """将 metric 值归一为 sympy 表达式。

    创建者: 朽木露琪亚
    最后一次更改: 朽木露琪亚

    功能说明:
    - 支持 `int/float/sympy.Basic` 三类正式 metric 值。
    - 其它类型返回 `None`，由上层决定是否视为缺失。

    使用示例:
    - metric_value_to_expr(64) == sp.Integer(64)

    关联文件:
    - spec: spec/analysis/analysis_engine.md
    - test: test/analysis/test_analysis.py
    - 功能实现: kernel_gen/analysis/memory/__init__.py
    """

    if isinstance(value, sp.Basic):
        return value
    if isinstance(value, int):
        return sp.Integer(value)
    if isinstance(value, float):
        return sp.Float(value)
    return None


def time_from_memory_metrics(
    bytes_expr: sp.Basic,
    latency_ns: sp.Basic | None,
    bandwidth: sp.Basic | None,
) -> sp.Basic | None:
    """计算访存理论时间。

    创建者: 朽木露琪亚
    最后一次更改: 朽木露琪亚

    功能说明:
    - A3 正式公式固定为 `bytes + latency + bandwidth -> time_ns`，即：
      `time_ns = latency_ns + bytes_expr / bandwidth`
    - 只有 `latency_ns` 与 `bandwidth` 都存在且 `bandwidth != 0` 时才返回有效值。

    使用示例:
    - time_from_memory_metrics(sp.Integer(32), sp.Integer(20), sp.Integer(64)) == sp.Integer(20) + sp.Rational(1, 2)

    关联文件:
    - spec: spec/analysis/analysis_engine.md
    - test: test/analysis/test_analysis.py
    - 功能实现: kernel_gen/analysis/memory/__init__.py
    """

    if latency_ns is None or bandwidth is None or bandwidth == 0:
        return None
    return latency_ns + bytes_expr / bandwidth


MemoryAnalyzer = Callable[["Operation", "AnalysisConfig"], "DmaMemoryAnalysis | None"]
_DEFAULT_MEMORY_ANALYZERS: list[MemoryAnalyzer] = []
_CUSTOM_MEMORY_ANALYZERS: list[MemoryAnalyzer] = []
_MEMORY_OP_ANALYZERS: dict[str, MemoryAnalyzer] = {}
_DEFAULT_REGISTERED = False


def _register_analyzer(func: MemoryAnalyzer, registry: list[MemoryAnalyzer]) -> MemoryAnalyzer:
    if func not in registry:
        registry.append(func)
    return func


def register_memory_analyzer(func: MemoryAnalyzer) -> MemoryAnalyzer:
    """注册 memory analyzer。

    创建者: 金铲铲大作战
    最后一次更改: 金铲铲大作战

    功能说明:
    - 将 analyzer 追加到 memory registry。
    - 保持注册顺序用于稳定遍历。

    使用示例:
    - @register_memory_analyzer
      def analyze(op, config): ...

    关联文件:
    - spec: spec/analysis/analysis_engine.md
    - test: test/analysis/test_analysis.py
    - 功能实现: kernel_gen/analysis/memory/__init__.py
    """
    return _register_analyzer(func, _CUSTOM_MEMORY_ANALYZERS)


def _normalize_op_keys(ops: object) -> tuple[str, ...]:
    if isinstance(ops, (tuple, list, set)):
        items: Iterable[object] = ops
    else:
        items = (ops,)
    keys: list[str] = []
    for item in items:
        if isinstance(item, str):
            keys.append(item)
            continue
        op_name = getattr(item, "name", None)
        if isinstance(op_name, str):
            keys.append(op_name)
            continue
        raise TypeError(f"unsupported op key: {item!r}")
    if not keys:
        raise ValueError("register_memory requires at least one op key")
    return tuple(keys)


def register_memory(ops: object) -> Callable[[MemoryAnalyzer], MemoryAnalyzer]:
    """按 op 名称注册 memory analyzer。

    创建者: 金铲铲大作战
    最后一次更改: 金铲铲大作战

    功能说明:
    - 支持单 op 与 tuple/list/set 形式的 op 注册。
    - 同一 op 重复注册时抛错，避免多重命中歧义。

    使用示例:
    - @register_memory(nn.add)
      def analyze_add(op, config): ...
    - @register_memory((nn.add, nn.sub))
      def analyze_add_sub(op, config): ...

    关联文件:
    - spec: spec/analysis/analysis_engine.md
    - test: test/analysis/test_analysis.py
    - 功能实现: kernel_gen/analysis/memory/__init__.py
    """
    op_keys = _normalize_op_keys(ops)

    def decorator(func: MemoryAnalyzer) -> MemoryAnalyzer:
        for key in op_keys:
            existing = _MEMORY_OP_ANALYZERS.get(key)
            if existing is not None and existing is not func:
                raise ValueError(f"memory analyzer already registered for op: {key}")
            _MEMORY_OP_ANALYZERS[key] = func
        return func

    return decorator


def _ensure_default_analyzers_registered() -> None:
    global _DEFAULT_REGISTERED
    if _DEFAULT_REGISTERED:
        return
    _register_analyzer(analyze_dma_memory_op, _DEFAULT_MEMORY_ANALYZERS)
    _DEFAULT_REGISTERED = True


def _iter_unique_analyzers(analyzers: Iterable[MemoryAnalyzer]) -> Iterator[MemoryAnalyzer]:
    seen: set[MemoryAnalyzer] = set()
    for analyzer in analyzers:
        if analyzer in seen:
            continue
        seen.add(analyzer)
        yield analyzer


def iter_memory_analyzers() -> tuple[MemoryAnalyzer, ...]:
    """获取当前注册的 memory analyzers。

    创建者: 金铲铲大作战
    最后一次更改: 金铲铲大作战

    功能说明:
    - 返回 registry 中的 analyzer 列表副本。

    使用示例:
    - for analyzer in iter_memory_analyzers(): ...

    关联文件:
    - spec: spec/analysis/analysis_engine.md
    - test: test/analysis/test_analysis.py
    - 功能实现: kernel_gen/analysis/memory/__init__.py
    """
    _ensure_default_analyzers_registered()
    return tuple(_DEFAULT_MEMORY_ANALYZERS + _CUSTOM_MEMORY_ANALYZERS)


def iter_memory_analyzers_for_op(op: "Operation") -> tuple[MemoryAnalyzer, ...]:
    """按 op 返回适用的 memory analyzers。

    创建者: 金铲铲大作战
    最后一次更改: 金铲铲大作战

    功能说明:
    - 优先返回 op 定向注册的 analyzer。
    - 追加默认 + 自定义通用 analyzer，允许多命中合并。

    使用示例:
    - for analyzer in iter_memory_analyzers_for_op(op): ...

    关联文件:
    - spec: spec/analysis/analysis_engine.md
    - test: test/analysis/test_analysis.py
    - 功能实现: kernel_gen/analysis/memory/__init__.py
    """
    _ensure_default_analyzers_registered()
    op_name = getattr(op, "name", None)
    analyzers: list[MemoryAnalyzer] = []
    if isinstance(op_name, str):
        analyzer = _MEMORY_OP_ANALYZERS.get(op_name)
        if analyzer is not None:
            analyzers.append(analyzer)
    analyzers.extend(_DEFAULT_MEMORY_ANALYZERS)
    analyzers.extend(_CUSTOM_MEMORY_ANALYZERS)
    return tuple(_iter_unique_analyzers(analyzers))


def analyze_dma_memory_op(op: "Operation", config: "AnalysisConfig") -> "DmaMemoryAnalysis | None":
    """适配 DMA memory analyzer。

    创建者: 金铲铲大作战
    最后一次更改: 金铲铲大作战

    功能说明:
    - 将 `analysis` 配置注入 DMA memory analyzer。
    - 保持 DMA 前置条件非法的硬错误语义。

    使用示例:
    - analyzed = analyze_dma_memory_op(op, config)

    关联文件:
    - spec: spec/analysis/analysis_engine.md
    - test: test/analysis/test_analysis.py
    - 功能实现: kernel_gen/analysis/memory/__init__.py
    """
    from kernel_gen.analysis.analysis import AnalysisError, _normalize_dtype_overrides
    from kernel_gen.analysis.memory.dma import analyze_dma_op

    try:
        return analyze_dma_op(
            op,
            path_latency_ns=config.path_latency_ns,
            path_bandwidth=config.path_bandwidth,
            dtype_size_overrides=_normalize_dtype_overrides(config.dtype_size_overrides),
        )
    except ValueError as exc:
        raise AnalysisError(str(exc)) from exc


__all__ = [
    "MemoryPath",
    "metric_value_to_expr",
    "normalize_memory_path",
    "time_from_memory_metrics",
    "MemoryAnalyzer",
    "register_memory_analyzer",
    "register_memory",
    "iter_memory_analyzers",
    "iter_memory_analyzers_for_op",
    "analyze_dma_memory_op",
]
