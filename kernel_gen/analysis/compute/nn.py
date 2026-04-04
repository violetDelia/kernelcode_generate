"""NN dialect compute analysis helpers.

创建者: jcc你莫辜负
最后一次更改: jcc你莫辜负

功能说明:
- 承接 `nn.*` 逐元素与 `nn.matmul` 的计算分类分析。
- 返回统一 `_AnalyzedOp` 结构，供 `analysis.py` 聚合。

使用示例:
- analyzed = analyze_nn_elementwise_op(op, config)

关联文件:
- spec: spec/analysis/analysis_engine.md
- test: test/analysis/test_analysis.py
- 功能实现: kernel_gen/analysis/compute/nn.py
"""

from __future__ import annotations

import sympy as sp
from xdsl.ir import Operation

from kernel_gen.analysis.analysis import (
    AnalysisConfig,
    AnalysisError,
    ComputeItem,
    _AnalyzedOp,
    _build_memory_item,
    _dim_to_expr,
    _dtype_string,
    _element_size,
    _is_predicate_type,
    _normalize_dtype_overrides,
    _numel_from_mem_type,
    _space_token_from_mem_type,
)
from kernel_gen.analysis.compute import ComputeKind
from kernel_gen.dialect.nn import NnMemoryType

_NN_ELEMENTWISE_OPS = {
    "nn.add",
    "nn.sub",
    "nn.mul",
    "nn.truediv",
    "nn.eq",
    "nn.ne",
    "nn.lt",
    "nn.le",
    "nn.gt",
    "nn.ge",
}
_NN_COMPARE_OPS = {"nn.eq", "nn.ne", "nn.lt", "nn.le", "nn.gt", "nn.ge"}


def analyze_nn_elementwise_op(op: Operation, config: AnalysisConfig) -> _AnalyzedOp | None:
    """分析 `nn.*` 逐元素算术/比较 op 的计算分类。

    创建者: jcc你莫辜负
    最后一次更改: jcc你莫辜负

    功能说明:
    - 对逐元素 `nn.*` memory op 统一产出 `ComputeKind.VECTOR`。
    - `tensor + const` 保留 `VECTOR` 计算分类，同时常量侧不计 memory traffic。
    - 比较输出 `i1` 的写回字节仍继续受 `predicate_size` 控制。

    使用示例:
    - analyzed = analyze_nn_elementwise_op(op, config)

    关联文件:
    - spec: spec/analysis/analysis_engine.md
    - test: test/analysis/test_analysis.py
    - 功能实现: kernel_gen/analysis/compute/nn.py
    """

    if op.name not in _NN_ELEMENTWISE_OPS:
        return None
    if len(op.operands) < 2 or len(op.results) != 1:
        raise AnalysisError("nn elementwise op must have 2 operands and 1 result")
    lhs = op.operands[0]
    rhs = op.operands[1]
    result = op.results[0]
    if not isinstance(result.type, NnMemoryType):
        raise AnalysisError("nn op result must be nn.memory")
    result_type = result.type
    numel = _numel_from_mem_type(result_type)
    if numel is None:
        raise AnalysisError("result shape must be supported")

    lhs_mem = isinstance(lhs.type, NnMemoryType)
    rhs_mem = isinstance(rhs.type, NnMemoryType)
    if not lhs_mem and not rhs_mem:
        raise AnalysisError("at least one nn.memory operand required")

    read_bytes = sp.Integer(0)
    memory_items: list[object] = []
    value_reads: list[tuple[object, sp.Basic]] = []
    overrides = _normalize_dtype_overrides(config.dtype_size_overrides)
    if lhs_mem:
        lhs_type = lhs.type
        if lhs_type.shape != result_type.shape:
            raise AnalysisError("result shape must match memory operand")
        lhs_size = _element_size(lhs_type.element_type, overrides)
        if lhs_size is None:
            raise AnalysisError("operand dtype unsupported")
        lhs_bytes = numel * sp.Integer(lhs_size)
        read_bytes += lhs_bytes
        value_reads.append((lhs, lhs_bytes))
        if config.enable_memory:
            memory_items.append(
                _build_memory_item(
                    f"{_space_token_from_mem_type(lhs_type)}->compute",
                    "read",
                    lhs_bytes,
                    config,
                )
            )
    if rhs_mem:
        rhs_type = rhs.type
        if rhs_type.shape != result_type.shape:
            raise AnalysisError("result shape must match memory operand")
        rhs_size = _element_size(rhs_type.element_type, overrides)
        if rhs_size is None:
            raise AnalysisError("operand dtype unsupported")
        rhs_bytes = numel * sp.Integer(rhs_size)
        read_bytes += rhs_bytes
        value_reads.append((rhs, rhs_bytes))
        if config.enable_memory:
            memory_items.append(
                _build_memory_item(
                    f"{_space_token_from_mem_type(rhs_type)}->compute",
                    "read",
                    rhs_bytes,
                    config,
                )
            )

    if op.name in _NN_COMPARE_OPS:
        if not _is_predicate_type(result_type.element_type):
            raise AnalysisError("compare result element_type must be i1")
        write_bytes = numel * sp.Integer(config.predicate_size)
    else:
        out_size = _element_size(result_type.element_type, overrides)
        if out_size is None:
            raise AnalysisError("result dtype unsupported")
        write_bytes = numel * sp.Integer(out_size)
    if config.enable_memory:
        memory_items.append(
            _build_memory_item(
                f"compute->{_space_token_from_mem_type(result_type)}",
                "write",
                write_bytes,
                config,
            )
        )

    compute_items: list[ComputeItem] = []
    if config.enable_compute:
        compute_items.append(
            ComputeItem(
                kind=ComputeKind.VECTOR,
                amount=numel,
                dtype=_dtype_string(result_type.element_type),
            )
        )
    return _AnalyzedOp(
        op_name=op.name,
        compute_items=compute_items,
        memory_items=memory_items,
        compute=numel if config.enable_compute else sp.Integer(0),
        read_bytes=read_bytes if config.enable_memory else sp.Integer(0),
        write_bytes=write_bytes if config.enable_memory else sp.Integer(0),
        value_reads=tuple(value_reads) if config.enable_memory else (),
        result_write_bytes=write_bytes if config.enable_memory else sp.Integer(0),
    )


def analyze_nn_matmul_ir_op(op: Operation, config: AnalysisConfig) -> _AnalyzedOp | None:
    """分析 `nn.matmul` 的计算分类。

    创建者: jcc你莫辜负
    最后一次更改: jcc你莫辜负

    功能说明:
    - 对二维收缩 `nn.matmul` 统一产出 `ComputeKind.TENSOR`。
    - 保持现有 `2*M*N*K` 理论计算量与访存 alias 行为不变。

    使用示例:
    - analyzed = analyze_nn_matmul_ir_op(op, config)

    关联文件:
    - spec: spec/analysis/analysis_engine.md
    - test: test/analysis/test_analysis.py
    - 功能实现: kernel_gen/analysis/compute/nn.py
    """

    if op.name != "nn.matmul":
        return None
    if len(op.operands) < 2 or len(op.results) != 1:
        raise AnalysisError("nn.matmul must have 2 operands and 1 result")
    lhs = op.operands[0]
    rhs = op.operands[1]
    result = op.results[0]
    if not isinstance(lhs.type, NnMemoryType) or not isinstance(rhs.type, NnMemoryType):
        raise AnalysisError("nn.matmul operands must be nn.memory")
    if not isinstance(result.type, NnMemoryType):
        raise AnalysisError("nn.matmul result must be nn.memory")
    lhs_type = lhs.type
    rhs_type = rhs.type
    result_type = result.type
    if len(lhs_type.shape.data) != 2 or len(rhs_type.shape.data) != 2 or len(result_type.shape.data) != 2:
        raise AnalysisError("nn.matmul requires rank-2 tensors")

    m_dim = _dim_to_expr(lhs_type.shape.data[0])
    k_dim = _dim_to_expr(lhs_type.shape.data[1])
    rhs_k_dim = _dim_to_expr(rhs_type.shape.data[0])
    n_dim = _dim_to_expr(rhs_type.shape.data[1])
    out_m_dim = _dim_to_expr(result_type.shape.data[0])
    out_n_dim = _dim_to_expr(result_type.shape.data[1])
    if None in {m_dim, k_dim, rhs_k_dim, n_dim, out_m_dim, out_n_dim}:
        raise AnalysisError("nn.matmul shape unsupported")
    if k_dim != rhs_k_dim:
        raise AnalysisError("nn.matmul inner dimension mismatch")
    if out_m_dim != m_dim or out_n_dim != n_dim:
        raise AnalysisError("nn.matmul output shape mismatch")

    overrides = _normalize_dtype_overrides(config.dtype_size_overrides)
    elem_size = _element_size(lhs_type.element_type, overrides)
    if elem_size is None:
        raise AnalysisError("nn.matmul operand dtype unsupported")
    if lhs_type.element_type != rhs_type.element_type or lhs_type.element_type != result_type.element_type:
        raise AnalysisError("nn.matmul operand/result element_type must match")
    elem_size_expr = sp.Integer(elem_size)
    compute = sp.Integer(2) * m_dim * n_dim * k_dim
    lhs_bytes = m_dim * k_dim * elem_size_expr
    rhs_bytes = k_dim * n_dim * elem_size_expr
    read_bytes = lhs_bytes + rhs_bytes
    write_bytes = m_dim * n_dim * elem_size_expr
    memory_items: list[object] = []
    if config.enable_memory:
        memory_items.extend(
            [
                _build_memory_item(
                    f"{_space_token_from_mem_type(lhs_type)}->compute",
                    "read",
                    lhs_bytes,
                    config,
                ),
                _build_memory_item(
                    f"{_space_token_from_mem_type(rhs_type)}->compute",
                    "read",
                    rhs_bytes,
                    config,
                ),
                _build_memory_item(
                    f"compute->{_space_token_from_mem_type(result_type)}",
                    "write",
                    write_bytes,
                    config,
                ),
            ]
        )
    compute_items: list[ComputeItem] = []
    if config.enable_compute:
        compute_items.append(
            ComputeItem(
                kind=ComputeKind.TENSOR,
                amount=compute,
                dtype=_dtype_string(result_type.element_type),
            )
        )
    return _AnalyzedOp(
        op_name=op.name,
        compute_items=compute_items,
        memory_items=memory_items,
        compute=compute if config.enable_compute else sp.Integer(0),
        read_bytes=read_bytes if config.enable_memory else sp.Integer(0),
        write_bytes=write_bytes if config.enable_memory else sp.Integer(0),
        value_reads=((lhs, lhs_bytes), (rhs, rhs_bytes)) if config.enable_memory else (),
        result_write_bytes=write_bytes if config.enable_memory else sp.Integer(0),
    )


__all__ = ["analyze_nn_elementwise_op", "analyze_nn_matmul_ir_op"]
