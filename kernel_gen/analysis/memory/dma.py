"""DMA memory-path analysis helpers.

创建者: 朽木露琪亚
最后一次更改: jcc你莫辜负 (2026-04-06)

功能说明:
- 收口公开 DMA 分支的访存分析逻辑。
- 为 `dma.copy/load/store/slice/deslice/cast` 统一生成 `MemoryPath`、`bytes`、`latency_ns`、`bandwidth` 与 `time_ns`。
- `dma.alloc/free/view/reshape` 视为零成本元数据或生命周期 op。
- `dma.fill` 仅统计 target 写入，标量来源不记 memory item。
- 写死 unknown / DMA 分支策略：公开 DMA 前置条件非法时报 `hard error`，未公开 DMA 分支返回 `None` 交由上层 `skip + warning`。

使用示例:
- from kernel_gen.analysis.memory.dma import analyze_dma_op
- result = analyze_dma_op(op, path_bandwidth=cfg.path_bandwidth, path_latency_ns=cfg.path_latency_ns, dtype_size_overrides=cfg.dtype_size_overrides)

关联文件:
- spec: spec/analysis/analysis_engine.md
- test: test/analysis/test_analysis.py
- 功能实现: kernel_gen/analysis/memory/dma.py
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass

import sympy as sp
from xdsl.ir import Attribute, Operation, SSAValue
from xdsl.utils.exceptions import VerifyException

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
    _is_contiguous,
)
from kernel_gen.dialect.nn import NnMemoryType
from kernel_gen.dialect.symbol import SymbolValueType

from . import MemoryPath, metric_value_to_expr, normalize_memory_path, time_from_memory_metrics

_SPACE_TOKENS = {
    "global": "GM",
    "shared": "SM",
    "local": "LM",
    "tsm": "TSM",
    "tlm": "TLM",
    "tlm1": "TLM",
    "tlm2": "TLM",
    "tlm3": "TLM",
}

PUBLIC_DMA_OPS = (
    DmaAllocOp,
    DmaFreeOp,
    DmaFillOp,
    DmaCopyOp,
    DmaLoadOp,
    DmaStoreOp,
    DmaSliceOp,
    DmaDesliceOp,
    DmaViewOp,
    DmaReshapeOp,
    DmaCastOp,
)


@dataclass(frozen=True)
class DmaMemoryAnalysis:
    """公开 DMA 分支的访存分析结果。

    创建者: 朽木露琪亚
    最后一次更改: 朽木露琪亚

    功能说明:
    - 承载单个 DMA op 的 path/bytes 统计。
    - 由 `analysis.py` 转换为统一 `_AnalyzedOp`。

    使用示例:
    - DmaMemoryAnalysis("dma.copy", memory_items=[...], read_bytes=sp.Integer(16), write_bytes=sp.Integer(16))

    关联文件:
    - spec: spec/analysis/analysis_engine.md
    - test: test/analysis/test_analysis.py
    - 功能实现: kernel_gen/analysis/memory/dma.py
    """

    op_name: str
    memory_items: tuple[tuple[MemoryPath, str, sp.Basic, sp.Basic | None, sp.Basic | None, sp.Basic | None], ...]
    read_bytes: sp.Basic
    write_bytes: sp.Basic
    value_reads: tuple[tuple[SSAValue, sp.Basic], ...] = ()
    direct_writes: tuple[tuple[SSAValue, sp.Basic], ...] = ()
    result_write_bytes: sp.Basic = sp.Integer(0)


def _space_token_from_mem_type(mem_type: NnMemoryType) -> str:
    """将 `nn.memory.space` 归一为固定 token。

    创建者: 朽木露琪亚
    最后一次更改: 朽木露琪亚

    功能说明:
    - 统一把 `global/shared/local/tsm/tlm` 映射到 `GM/SM/LM/TSM/TLM`。

    使用示例:
    - token = _space_token_from_mem_type(mem_type)

    关联文件:
    - spec: spec/analysis/analysis_engine.md
    - test: test/analysis/test_analysis.py
    - 功能实现: kernel_gen/analysis/memory/dma.py
    """

    raw = mem_type.space.space.data
    return _SPACE_TOKENS.get(raw, raw.upper())


def _memory_path_from_types(source: NnMemoryType, target: NnMemoryType) -> MemoryPath:
    """根据 source/target space 生成固定 `MemoryPath`。

    创建者: 朽木露琪亚
    最后一次更改: 朽木露琪亚

    功能说明:
    - 使用 `source.space -> target.space` 的稳定文本映射到 `MemoryPath`。
    - 未命中的路径统一收敛到 `MemoryPath.UNKNOWN`。

    使用示例:
    - path = _memory_path_from_types(src_type, dst_type)

    关联文件:
    - spec: spec/analysis/analysis_engine.md
    - test: test/analysis/test_analysis.py
    - 功能实现: kernel_gen/analysis/memory/dma.py
    """

    path_text = f"{_space_token_from_mem_type(source)}->{_space_token_from_mem_type(target)}"
    return normalize_memory_path(path_text)


def _element_size(element_type: Attribute, dtype_size_overrides: dict[str, int] | None) -> int | None:
    """从 element_type 解析元素字节大小。

    创建者: 朽木露琪亚
    最后一次更改: 朽木露琪亚

    功能说明:
    - 当前只覆盖 analysis A3 所需的 builtin integer/float 子集。
    - 若传入 override，则优先按 `dtype key` 覆盖。

    使用示例:
    - _element_size(f32, {"f32": 4}) == 4

    关联文件:
    - spec: spec/analysis/analysis_engine.md
    - test: test/analysis/test_analysis.py
    - 功能实现: kernel_gen/analysis/memory/dma.py
    """

    key = None
    from xdsl.dialects.builtin import BFloat16Type, Float16Type, Float32Type, Float64Type, IntegerType

    if isinstance(element_type, Float16Type):
        key = "f16"
    elif isinstance(element_type, BFloat16Type):
        key = "bf16"
    elif isinstance(element_type, Float32Type):
        key = "f32"
    elif isinstance(element_type, Float64Type):
        key = "f64"
    elif isinstance(element_type, IntegerType):
        key = f"i{element_type.width.data}"
    if key is None:
        return None
    if dtype_size_overrides and key in dtype_size_overrides:
        return dtype_size_overrides[key]
    if key == "f16" or key == "bf16":
        return 2
    if key == "f32":
        return 4
    if key == "f64":
        return 8
    if key.startswith("i"):
        width = int(key[1:])
        return max(1, width // 8)
    return None


def _dim_to_expr(dim: Attribute) -> sp.Basic | None:
    """将单个 shape 维度归一为 sympy 表达式。

    创建者: 朽木露琪亚
    最后一次更改: 朽木露琪亚

    功能说明:
    - 支持静态 `IntAttr` 与符号 `StringAttr`。

    使用示例:
    - expr = _dim_to_expr(dim)

    关联文件:
    - spec: spec/analysis/analysis_engine.md
    - test: test/analysis/test_analysis.py
    - 功能实现: kernel_gen/analysis/memory/dma.py
    """

    from xdsl.dialects.builtin import IntAttr, IntegerAttr, StringAttr

    if isinstance(dim, IntAttr):
        return sp.Integer(dim.data)
    if isinstance(dim, IntegerAttr):
        return sp.Integer(dim.value.data)
    if isinstance(dim, StringAttr):
        if dim.data == "?":
            return None
        return sp.Symbol(dim.data, integer=True, nonnegative=True)
    return None


def _numel_from_mem_type(mem_type: NnMemoryType) -> sp.Basic | None:
    """根据 `nn.memory.shape` 计算逻辑元素数。

    创建者: 朽木露琪亚
    最后一次更改: 朽木露琪亚

    功能说明:
    - 所有维度都可归一为 sympy 表达式时返回 numel。
    - 遇到未知维度时返回 `None`。

    使用示例:
    - numel = _numel_from_mem_type(mem_type)

    关联文件:
    - spec: spec/analysis/analysis_engine.md
    - test: test/analysis/test_analysis.py
    - 功能实现: kernel_gen/analysis/memory/dma.py
    """

    numel = sp.Integer(1)
    for dim in mem_type.shape.data:
        expr = _dim_to_expr(dim)
        if expr is None:
            return None
        numel *= expr
    return numel


def _numel_from_symbol_values(values: tuple[SSAValue, ...] | list[SSAValue]) -> sp.Basic | None:
    """根据 `!symbol.int` size 列表计算逻辑元素数。

    创建者: 朽木露琪亚
    最后一次更改: 朽木露琪亚

    功能说明:
    - 仅接受 `!symbol.int<\"expr\">` SSA value。

    使用示例:
    - numel = _numel_from_symbol_values(op.sizes)

    关联文件:
    - spec: spec/dialect/dma.md
    - test: test/analysis/test_analysis.py
    - 功能实现: kernel_gen/analysis/memory/dma.py
    """

    numel = sp.Integer(1)
    for value in values:
        if not isinstance(value.type, SymbolValueType):
            return None
        expr_text = value.type.expr.expr.data
        if expr_text.lstrip("-").isdigit():
            numel *= sp.Integer(int(expr_text))
            continue
        numel *= sp.Symbol(expr_text, integer=True, nonnegative=True)
    return numel


def _verify_public_dma_op(op: Operation) -> None:
    """校验公开 DMA 分支的前置条件。

    创建者: 朽木露琪亚
    最后一次更改: 朽木露琪亚

    功能说明:
    - 复用 DMA dialect verifier。
    - verifier 失败统一归因为 `hard error`，由调用方转成 `AnalysisError`。

    使用示例:
    - _verify_public_dma_op(op)

    关联文件:
    - spec: spec/analysis/analysis_kernel.md
    - test: test/analysis/test_analysis.py
    - 功能实现: kernel_gen/analysis/memory/dma.py
    """

    try:
        op.verify()
    except VerifyException as exc:
        raise ValueError(str(exc)) from exc


def _build_memory_item_tuple(
    path: MemoryPath,
    access: str,
    bytes_expr: sp.Basic,
    *,
    path_latency_ns: Mapping[MemoryPath | str, object],
    path_bandwidth: Mapping[MemoryPath | str, object],
) -> tuple[MemoryPath, str, sp.Basic, sp.Basic | None, sp.Basic | None, sp.Basic | None]:
    """构造 DMA 访存条目元组。

    创建者: 朽木露琪亚
    最后一次更改: 朽木露琪亚

    功能说明:
    - 按固定 `time_ns = latency_ns + bytes / bandwidth` 公式补齐时间。

    使用示例:
    - item = _build_memory_item_tuple(MemoryPath.GM_TO_LM, "read", sp.Integer(32), path_latency_ns=..., path_bandwidth=...)

    关联文件:
    - spec: spec/analysis/analysis_engine.md
    - test: test/analysis/test_analysis.py
    - 功能实现: kernel_gen/analysis/memory/dma.py
    """

    latency = metric_value_to_expr(path_latency_ns.get(path))
    bandwidth = metric_value_to_expr(path_bandwidth.get(path))
    time_ns = time_from_memory_metrics(bytes_expr, latency, bandwidth)
    return (path, access, bytes_expr, latency, bandwidth, time_ns)


def analyze_dma_op(
    op: Operation,
    *,
    path_latency_ns: Mapping[MemoryPath | str, object],
    path_bandwidth: Mapping[MemoryPath | str, object],
    dtype_size_overrides: dict[str, int] | None,
) -> DmaMemoryAnalysis | None:
    """分析当前已公开的 DMA 分支。

    创建者: 朽木露琪亚
    最后一次更改: 朽木露琪亚

    功能说明:
    - 当前公开并承接：`dma.alloc/free/fill/copy/load/store/slice/deslice/view/reshape/cast`。
    - 当前未公开 DMA 分支返回 `None`，由上层按 `skip + warning` 处理。
    - 公开 DMA 前置条件非法时，直接抛出异常作为 `hard error`。

    使用示例:
    - analyzed = analyze_dma_op(op, path_latency_ns=cfg.path_latency_ns, path_bandwidth=cfg.path_bandwidth, dtype_size_overrides=cfg.dtype_size_overrides)

    关联文件:
    - spec: spec/analysis/analysis_kernel.md
    - test: test/analysis/test_analysis.py
    - 功能实现: kernel_gen/analysis/memory/dma.py
    """

    if isinstance(op, DmaAllocOp):
        result = op.result
        if not isinstance(result.type, NnMemoryType):
            raise ValueError("dma.alloc result must be nn.memory")
        if not _is_contiguous(result.type):
            return None
        _verify_public_dma_op(op)
        return DmaMemoryAnalysis(
            op_name=op.name,
            memory_items=(),
            read_bytes=sp.Integer(0),
            write_bytes=sp.Integer(0),
        )
    if isinstance(op, DmaFreeOp):
        _verify_public_dma_op(op)
        return DmaMemoryAnalysis(
            op_name=op.name,
            memory_items=(),
            read_bytes=sp.Integer(0),
            write_bytes=sp.Integer(0),
        )
    if isinstance(op, DmaViewOp):
        _verify_public_dma_op(op)
        source = op.source
        result = op.result
        if not isinstance(source.type, NnMemoryType) or not isinstance(result.type, NnMemoryType):
            raise ValueError("dma.view source/result must be nn.memory")
        return DmaMemoryAnalysis(
            op_name=op.name,
            memory_items=(),
            read_bytes=sp.Integer(0),
            write_bytes=sp.Integer(0),
        )
    if isinstance(op, DmaReshapeOp):
        _verify_public_dma_op(op)
        source = op.source
        result = op.result
        if not isinstance(source.type, NnMemoryType) or not isinstance(result.type, NnMemoryType):
            raise ValueError("dma.reshape source/result must be nn.memory")
        return DmaMemoryAnalysis(
            op_name=op.name,
            memory_items=(),
            read_bytes=sp.Integer(0),
            write_bytes=sp.Integer(0),
        )
    if isinstance(op, DmaFillOp):
        _verify_public_dma_op(op)
        target = op.target
        if not isinstance(target.type, NnMemoryType):
            raise ValueError("dma.fill target must be nn.memory")
        numel = _numel_from_mem_type(target.type)
        if numel is None:
            raise ValueError("dma.fill shape unsupported")
        elem_size = _element_size(target.type.element_type, dtype_size_overrides)
        if elem_size is None:
            raise ValueError("dma.fill dtype unsupported")
        bytes_expr = numel * sp.Integer(elem_size)
        path_text = f"compute->{_space_token_from_mem_type(target.type)}"
        path = normalize_memory_path(path_text)
        items = (
            _build_memory_item_tuple(
                path,
                "write",
                bytes_expr,
                path_latency_ns=path_latency_ns,
                path_bandwidth=path_bandwidth,
            ),
        )
        return DmaMemoryAnalysis(
            op_name=op.name,
            memory_items=items,
            read_bytes=sp.Integer(0),
            write_bytes=bytes_expr,
            direct_writes=((target, bytes_expr),),
        )
    if isinstance(op, DmaCopyOp):
        _verify_public_dma_op(op)
        source = op.source
        target = op.target
        if not isinstance(source.type, NnMemoryType) or not isinstance(target.type, NnMemoryType):
            raise ValueError("dma.copy source/target must be nn.memory")
        numel = _numel_from_mem_type(source.type)
        if numel is None:
            raise ValueError("dma.copy shape unsupported")
        elem_size = _element_size(source.type.element_type, dtype_size_overrides)
        if elem_size is None:
            raise ValueError("dma.copy dtype unsupported")
        bytes_expr = numel * sp.Integer(elem_size)
        path = _memory_path_from_types(source.type, target.type)
        items = (
            _build_memory_item_tuple(path, "read", bytes_expr, path_latency_ns=path_latency_ns, path_bandwidth=path_bandwidth),
            _build_memory_item_tuple(path, "write", bytes_expr, path_latency_ns=path_latency_ns, path_bandwidth=path_bandwidth),
        )
        return DmaMemoryAnalysis(
            op_name=op.name,
            memory_items=items,
            read_bytes=bytes_expr,
            write_bytes=bytes_expr,
            value_reads=((source, bytes_expr),),
            direct_writes=((target, bytes_expr),),
        )
    if isinstance(op, DmaLoadOp):
        _verify_public_dma_op(op)
        target = op.target
        source = op.source
        if not isinstance(target.type, NnMemoryType):
            raise ValueError("dma.load target must be nn.memory")
        if not isinstance(source.type, NnMemoryType):
            raise ValueError("dma.load source must be nn.memory")
        numel = _numel_from_mem_type(target.type)
        if numel is None:
            raise ValueError("dma.load target shape unsupported")
        elem_size = _element_size(target.type.element_type, dtype_size_overrides)
        if elem_size is None:
            raise ValueError("dma.load target dtype unsupported")
        bytes_expr = numel * sp.Integer(elem_size)
        path = _memory_path_from_types(source.type, target.type)
        items = (
            _build_memory_item_tuple(path, "read", bytes_expr, path_latency_ns=path_latency_ns, path_bandwidth=path_bandwidth),
            _build_memory_item_tuple(path, "write", bytes_expr, path_latency_ns=path_latency_ns, path_bandwidth=path_bandwidth),
        )
        return DmaMemoryAnalysis(
            op_name=op.name,
            memory_items=items,
            read_bytes=bytes_expr,
            write_bytes=bytes_expr,
            value_reads=((source, bytes_expr),),
            direct_writes=((target, bytes_expr),),
        )
    if isinstance(op, DmaStoreOp):
        _verify_public_dma_op(op)
        source = op.source
        target = op.target
        if not isinstance(source.type, NnMemoryType) or not isinstance(target.type, NnMemoryType):
            raise ValueError("dma.store source/target must be nn.memory")
        numel = _numel_from_symbol_values(op.sizes)
        if numel is None:
            numel = _numel_from_mem_type(source.type)
        if numel is None:
            raise ValueError("dma.store sizes unsupported")
        elem_size = _element_size(source.type.element_type, dtype_size_overrides)
        if elem_size is None:
            raise ValueError("dma.store dtype unsupported")
        bytes_expr = numel * sp.Integer(elem_size)
        path = _memory_path_from_types(source.type, target.type)
        items = (
            _build_memory_item_tuple(path, "read", bytes_expr, path_latency_ns=path_latency_ns, path_bandwidth=path_bandwidth),
            _build_memory_item_tuple(path, "write", bytes_expr, path_latency_ns=path_latency_ns, path_bandwidth=path_bandwidth),
        )
        return DmaMemoryAnalysis(
            op_name=op.name,
            memory_items=items,
            read_bytes=bytes_expr,
            write_bytes=bytes_expr,
            value_reads=((source, bytes_expr),),
            direct_writes=((target, bytes_expr),),
        )
    if isinstance(op, DmaSliceOp):
        _verify_public_dma_op(op)
        source = op.source
        target = op.target
        if not isinstance(source.type, NnMemoryType) or not isinstance(target.type, NnMemoryType):
            raise ValueError("dma.slice source/target must be nn.memory")
        numel = _numel_from_symbol_values(op.sizes)
        if numel is None:
            numel = _numel_from_mem_type(target.type)
        if numel is None:
            raise ValueError("dma.slice sizes unsupported")
        elem_size = _element_size(target.type.element_type, dtype_size_overrides)
        if elem_size is None:
            raise ValueError("dma.slice dtype unsupported")
        bytes_expr = numel * sp.Integer(elem_size)
        path = _memory_path_from_types(source.type, target.type)
        items = (
            _build_memory_item_tuple(path, "read", bytes_expr, path_latency_ns=path_latency_ns, path_bandwidth=path_bandwidth),
            _build_memory_item_tuple(path, "write", bytes_expr, path_latency_ns=path_latency_ns, path_bandwidth=path_bandwidth),
        )
        return DmaMemoryAnalysis(
            op_name=op.name,
            memory_items=items,
            read_bytes=bytes_expr,
            write_bytes=bytes_expr,
            value_reads=((source, bytes_expr),),
            direct_writes=((target, bytes_expr),),
        )
    if isinstance(op, DmaDesliceOp):
        source = op.source
        target = op.target
        if not isinstance(source.type, NnMemoryType) or not isinstance(target.type, NnMemoryType):
            raise ValueError("dma.deslice source/target must be nn.memory")
        if not _is_contiguous(target.type):
            return None
        _verify_public_dma_op(op)
        numel = _numel_from_symbol_values(op.sizes)
        if numel is None:
            numel = _numel_from_mem_type(source.type)
        if numel is None:
            raise ValueError("dma.deslice sizes unsupported")
        elem_size = _element_size(source.type.element_type, dtype_size_overrides)
        if elem_size is None:
            raise ValueError("dma.deslice dtype unsupported")
        bytes_expr = numel * sp.Integer(elem_size)
        path = _memory_path_from_types(source.type, target.type)
        items = (
            _build_memory_item_tuple(path, "read", bytes_expr, path_latency_ns=path_latency_ns, path_bandwidth=path_bandwidth),
            _build_memory_item_tuple(path, "write", bytes_expr, path_latency_ns=path_latency_ns, path_bandwidth=path_bandwidth),
        )
        return DmaMemoryAnalysis(
            op_name=op.name,
            memory_items=items,
            read_bytes=bytes_expr,
            write_bytes=bytes_expr,
            value_reads=((source, bytes_expr),),
            direct_writes=((target, bytes_expr),),
        )
    if isinstance(op, DmaCastOp):
        _verify_public_dma_op(op)
        target = op.target
        source = op.source
        if not isinstance(source.type, NnMemoryType) or not isinstance(target.type, NnMemoryType):
            raise ValueError("dma.cast source/target must be nn.memory")
        numel = _numel_from_mem_type(target.type)
        if numel is None:
            raise ValueError("dma.cast target shape unsupported")
        source_elem_size = _element_size(source.type.element_type, dtype_size_overrides)
        if source_elem_size is None:
            raise ValueError("dma.cast source dtype unsupported")
        result_elem_size = _element_size(target.type.element_type, dtype_size_overrides)
        if result_elem_size is None:
            raise ValueError("dma.cast target dtype unsupported")
        read_bytes = numel * sp.Integer(source_elem_size)
        write_bytes = numel * sp.Integer(result_elem_size)
        path = _memory_path_from_types(source.type, target.type)
        items = (
            _build_memory_item_tuple(path, "read", read_bytes, path_latency_ns=path_latency_ns, path_bandwidth=path_bandwidth),
            _build_memory_item_tuple(path, "write", write_bytes, path_latency_ns=path_latency_ns, path_bandwidth=path_bandwidth),
        )
        return DmaMemoryAnalysis(
            op_name=op.name,
            memory_items=items,
            read_bytes=read_bytes,
            write_bytes=write_bytes,
            value_reads=((source, read_bytes),),
            direct_writes=((target, write_bytes),),
        )
    return None


__all__ = [
    "DmaMemoryAnalysis",
    "PUBLIC_DMA_OPS",
    "analyze_dma_op",
]
