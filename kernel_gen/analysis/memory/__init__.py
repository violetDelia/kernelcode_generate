"""Memory-path analysis helpers.

创建者: 朽木露琪亚
最后一次更改: 朽木露琪亚

功能说明:
- 定义访存主线公开使用的 `MemoryPath` 枚举。
- 提供 metric 值归一化与 `bytes + latency + bandwidth -> time_ns` 公式。
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

from enum import Enum

import sympy as sp


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


__all__ = [
    "MemoryPath",
    "metric_value_to_expr",
    "normalize_memory_path",
    "time_from_memory_metrics",
]
