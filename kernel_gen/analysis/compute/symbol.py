"""Symbol dialect compute analysis helpers.

创建者: 朽木露琪亚
最后一次更改: 朽木露琪亚

功能说明:
- 承接 `symbol.*` 计算/访存分析，返回统一 `_AnalyzedOp` 结构。
- 默认 `symbol.*` 计入 SCALAR 计算；`symbol.to_int/to_float` 计入 1 字节访存。
- `symbol.get_dim/get_stride` 在 analysis 主线中作为元信息 op 忽略。

使用示例:
- analyzed = analyze_symbol_op(fake_symbol_op, config)

关联文件:
- spec: spec/analysis/analysis_engine.md
- test: test/analysis/test_analysis.py
- 功能实现: kernel_gen/analysis/compute/symbol.py
"""

from __future__ import annotations

import sympy as sp
from xdsl.ir import Operation

from kernel_gen.analysis.analysis import AnalysisConfig, ComputeItem, MemoryItem, _AnalyzedOp
from kernel_gen.analysis.compute import ComputeKind, register_compute_analyzer
from kernel_gen.analysis.memory import MemoryPath

_SYMBOL_CAST_OPS = {"symbol.to_int", "symbol.to_float"}
_SYMBOL_META_OPS = {"symbol.get_dim", "symbol.get_stride"}


def _symbol_result_dtype(op: Operation) -> str:
    """为 symbol op 生成 dtype 字符串。

    创建者: 朽木露琪亚
    最后一次更改: 朽木露琪亚

    功能说明:
    - 优先使用首个 result 的类型字符串。
    - 无 result 时回退为 "symbol"。

    使用示例:
    - dtype = _symbol_result_dtype(op)

    关联文件:
    - spec: spec/analysis/analysis_engine.md
    - test: test/analysis/test_analysis.py
    - 功能实现: kernel_gen/analysis/compute/symbol.py
    """
    if op.results:
        return str(op.results[0].type)
    return "symbol"


@register_compute_analyzer
def analyze_symbol_op(op: Operation, config: AnalysisConfig) -> _AnalyzedOp | None:
    """分析 `symbol.*` op 的计算/访存分类。

    创建者: 朽木露琪亚
    最后一次更改: 朽木露琪亚

    功能说明:
    - `symbol.*` 默认计入 SCALAR 计算 1。
    - `symbol.to_int/to_float` 计入 1 字节访存，compute 为 0。
    - `symbol.get_dim/get_stride` 返回 None，交由上层忽略。

    使用示例:
    - analyzed = analyze_symbol_op(op, config)

    关联文件:
    - spec: spec/analysis/analysis_engine.md
    - test: test/analysis/test_analysis.py
    - 功能实现: kernel_gen/analysis/compute/symbol.py
    """
    op_name = getattr(op, "name", None)
    if not isinstance(op_name, str) or not op_name.startswith("symbol."):
        return None
    if op_name in _SYMBOL_META_OPS:
        return None
    if op_name in _SYMBOL_CAST_OPS:
        memory_items: list[MemoryItem] = []
        read_bytes = sp.Integer(0)
        if config.enable_memory:
            read_bytes = sp.Integer(1)
            memory_items.append(
                MemoryItem(
                    path=MemoryPath.GM_TO_GM,
                    access="read",
                    bytes=sp.Integer(1),
                )
            )
        return _AnalyzedOp(
            op_name=op_name,
            compute_items=[],
            memory_items=memory_items,
            compute=sp.Integer(0),
            read_bytes=read_bytes,
            write_bytes=sp.Integer(0),
        )

    compute_items: list[ComputeItem] = []
    compute_amount = sp.Integer(0)
    if config.enable_compute:
        compute_amount = sp.Integer(1)
        compute_items.append(
            ComputeItem(
                kind=ComputeKind.SCALAR,
                amount=sp.Integer(1),
                dtype=_symbol_result_dtype(op),
            )
        )
    return _AnalyzedOp(
        op_name=op_name,
        compute_items=compute_items,
        memory_items=[],
        compute=compute_amount,
        read_bytes=sp.Integer(0),
        write_bytes=sp.Integer(0),
    )


__all__ = ["analyze_symbol_op"]
