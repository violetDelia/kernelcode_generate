"""Compute analysis classification helpers.

创建者: jcc你莫辜负
最后一次更改: jcc你莫辜负

功能说明:
- 定义 A2 计算主线使用的 `ComputeKind` 枚举。
- 统一导出 kernel/nn 计算分类分析入口，供 `analysis.py` 做分发。

使用示例:
- from kernel_gen.analysis.compute import ComputeKind
- assert ComputeKind.SCALAR.value == "scalar"

关联文件:
- spec: spec/analysis/analysis_engine.md
- test: test/analysis/test_analysis.py
- 功能实现: kernel_gen/analysis/compute/__init__.py
"""

from __future__ import annotations

from enum import Enum


class ComputeKind(str, Enum):
    """统一计算分类枚举。

    创建者: jcc你莫辜负
    最后一次更改: jcc你莫辜负

    功能说明:
    - 收口 `analysis` 主线的正式计算分类。
    - 当前固定公开 `SCALAR / VECTOR / TENSOR / MATH` 四类。

    使用示例:
    - kind = ComputeKind.VECTOR
    - assert kind.value == "vector"

    关联文件:
    - spec: spec/analysis/analysis_engine.md
    - test: test/analysis/test_analysis.py
    - 功能实现: kernel_gen/analysis/compute/__init__.py
    """

    SCALAR = "scalar"
    VECTOR = "vector"
    TENSOR = "tensor"
    MATH = "math"


__all__ = ["ComputeKind"]
