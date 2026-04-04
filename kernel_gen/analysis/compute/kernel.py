"""Kernel dialect compute analysis helpers.

创建者: jcc你莫辜负
最后一次更改: jcc你莫辜负

功能说明:
- 承接 `kernel.*` 标量计算分析，返回统一 `_AnalyzedOp` 结构。
- 仅处理 A2 当前冻结的标量 kernel 子集。

使用示例:
- analyzed = analyze_scalar_kernel_op(op, config)

关联文件:
- spec: spec/analysis/analysis_engine.md
- test: test/analysis/test_analysis.py
- 功能实现: kernel_gen/analysis/compute/kernel.py
"""

from __future__ import annotations

import sympy as sp
from xdsl.ir import Operation

from kernel_gen.analysis.analysis import AnalysisConfig, ComputeItem, _AnalyzedOp, _dtype_string, _is_scalar_type
from kernel_gen.analysis.compute import ComputeKind
from kernel_gen.dialect.nn import NnMemoryType

_SCALAR_KERNEL_OPS = {
    "kernel.add",
    "kernel.sub",
    "kernel.mul",
    "kernel.div",
    "kernel.eq",
    "kernel.ne",
    "kernel.lt",
    "kernel.le",
    "kernel.gt",
    "kernel.ge",
    "kernel.select",
    "kernel.cast",
}


def analyze_scalar_kernel_op(op: Operation, config: AnalysisConfig) -> _AnalyzedOp | None:
    """分析单个标量 `kernel.*` op 的计算分类。

    创建者: jcc你莫辜负
    最后一次更改: jcc你莫辜负

    功能说明:
    - 对 `kernel.add/sub/mul/div/eq/lt/gt/select/cast/...` 的单结果标量形态生成 `ComputeKind.SCALAR`。
    - 不负责访存分类；该类 op 当前只产出 compute item。

    使用示例:
    - analyzed = analyze_scalar_kernel_op(fake_kernel_add_op, config)

    关联文件:
    - spec: spec/analysis/analysis_engine.md
    - test: test/analysis/test_analysis.py
    - 功能实现: kernel_gen/analysis/compute/kernel.py
    """

    if op.name not in _SCALAR_KERNEL_OPS:
        return None
    if len(op.results) != 1:
        return None
    result_type = op.results[0].type
    if isinstance(result_type, NnMemoryType) or not _is_scalar_type(result_type):
        return None

    compute_items: list[ComputeItem] = []
    if config.enable_compute:
        compute_items.append(
            ComputeItem(
                kind=ComputeKind.SCALAR,
                amount=sp.Integer(1),
                dtype=_dtype_string(result_type),
            )
        )
    return _AnalyzedOp(
        op_name=op.name,
        compute_items=compute_items,
        memory_items=[],
        compute=sp.Integer(1) if config.enable_compute else sp.Integer(0),
        read_bytes=sp.Integer(0),
        write_bytes=sp.Integer(0),
    )


__all__ = ["analyze_scalar_kernel_op"]
