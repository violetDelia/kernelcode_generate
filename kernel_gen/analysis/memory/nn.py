"""NN dialect memory-path analysis helpers.

创建者: 金铲铲大作战
最后修改人: 金铲铲大作战

功能说明:
- 承接 `nn.*` elementwise/unary/reduce/broadcast/transpose/matmul 的访存统计。
- 仅生成 memory item 与读写字节统计，不负责 ComputeKind 分类。

使用示例:
- analyzed = analyze_nn_memory_op(op, config)

关联文件:
- spec: spec/analysis/analysis_engine.md
- test: test/analysis/test_analysis.py
- 功能实现: kernel_gen/analysis/memory/nn.py
"""

from __future__ import annotations

from collections.abc import Sequence

import sympy as sp
from xdsl.ir import Operation, SSAValue

from kernel_gen.analysis.analysis import (
    AnalysisConfig,
    AnalysisError,
    _AnalyzedOp,
    _build_memory_item,
    _dim_to_expr,
    _element_size,
    _is_predicate_type,
    _normalize_dtype_overrides,
    _numel_from_mem_type,
    _space_token_from_mem_type,
)
from kernel_gen.analysis.memory import register_memory
from kernel_gen.dialect.nn import NnMemoryType

_NN_ELEMENTWISE_OPS = (
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
)
_NN_COMPARE_OPS = {"nn.eq", "nn.ne", "nn.lt", "nn.le", "nn.gt", "nn.ge"}
_NN_UNARY_OPS = ("nn.exp",)
_NN_REDUCE_OPS = ("nn.reduce_sum", "nn.reduce_min", "nn.reduce_max")
_NN_DIRECT_OPS = ("nn.broadcast", "nn.transpose")
_NN_MATMUL_OPS = ("nn.matmul",)
_NN_MEMORY_OPS = _NN_ELEMENTWISE_OPS + _NN_UNARY_OPS + _NN_REDUCE_OPS + _NN_DIRECT_OPS + _NN_MATMUL_OPS


def _compute_path(space_token: str, access: str) -> str:
    """构造 compute 读写路径文本。

    创建者: 金铲铲大作战
    最后修改人: 金铲铲大作战

    功能说明:
    - 读路径固定为 `<space_token>->compute`。
    - 写路径固定为 `compute-><space_token>`。

    使用示例:
    - _compute_path("GM", "read") == "GM->compute"

    关联文件:
    - spec: spec/analysis/analysis_engine.md
    - test: test/analysis/test_analysis.py
    - 功能实现: kernel_gen/analysis/memory/nn.py
    """
    if access == "read":
        return f"{space_token}->compute"
    if access == "write":
        return f"compute->{space_token}"
    raise AnalysisError(f"unsupported memory access: {access}")


def _finalize_memory_analysis(
    *,
    op_name: str,
    read_bytes: sp.Basic,
    write_bytes: sp.Basic,
    memory_items: Sequence[object],
    value_reads: Sequence[tuple[SSAValue, sp.Basic]],
    result_write_bytes: sp.Basic,
    config: AnalysisConfig,
) -> _AnalyzedOp:
    """规范化 memory analyzer 输出。

    创建者: 金铲铲大作战
    最后修改人: 金铲铲大作战

    功能说明:
    - 当 `enable_memory=False` 时清空所有访存统计。
    - 始终返回 `_AnalyzedOp` 便于统一聚合。

    使用示例:
    - result = _finalize_memory_analysis(op_name="nn.add", read_bytes=sp.Integer(4), write_bytes=sp.Integer(4), ...)

    关联文件:
    - spec: spec/analysis/analysis_engine.md
    - test: test/analysis/test_analysis.py
    - 功能实现: kernel_gen/analysis/memory/nn.py
    """
    if not config.enable_memory:
        return _AnalyzedOp(
            op_name=op_name,
            compute_items=(),
            memory_items=(),
            compute=sp.Integer(0),
            read_bytes=sp.Integer(0),
            write_bytes=sp.Integer(0),
            value_reads=(),
            result_write_bytes=sp.Integer(0),
        )
    return _AnalyzedOp(
        op_name=op_name,
        compute_items=(),
        memory_items=tuple(memory_items),
        compute=sp.Integer(0),
        read_bytes=read_bytes,
        write_bytes=write_bytes,
        value_reads=tuple(value_reads),
        result_write_bytes=result_write_bytes,
    )


@register_memory(_NN_MEMORY_OPS)
def analyze_nn_memory_op(op: Operation, config: AnalysisConfig) -> _AnalyzedOp | None:
    """分析 `nn.*` 的访存统计。

    创建者: 金铲铲大作战
    最后修改人: 金铲铲大作战

    功能说明:
    - 覆盖 elementwise/unary/reduce/broadcast/transpose/matmul 的访存统计。
    - direct op 仅统计读写 bytes，不产出 compute item。

    使用示例:
    - analyzed = analyze_nn_memory_op(op, config)

    关联文件:
    - spec: spec/analysis/analysis_engine.md
    - test: test/analysis/test_analysis.py
    - 功能实现: kernel_gen/analysis/memory/nn.py
    """

    name = op.name
    overrides = _normalize_dtype_overrides(config.dtype_size_overrides)
    if name in _NN_ELEMENTWISE_OPS:
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
        value_reads: list[tuple[SSAValue, sp.Basic]] = []
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
                        _compute_path(_space_token_from_mem_type(lhs_type), "read"),
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
                        _compute_path(_space_token_from_mem_type(rhs_type), "read"),
                        "read",
                        rhs_bytes,
                        config,
                    )
                )
        if name in _NN_COMPARE_OPS:
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
                    _compute_path(_space_token_from_mem_type(result_type), "write"),
                    "write",
                    write_bytes,
                    config,
                )
            )
        return _finalize_memory_analysis(
            op_name=op.name,
            read_bytes=read_bytes,
            write_bytes=write_bytes,
            memory_items=memory_items,
            value_reads=value_reads,
            result_write_bytes=write_bytes,
            config=config,
        )

    if name in _NN_UNARY_OPS:
        if len(op.operands) != 1 or len(op.results) != 1:
            raise AnalysisError("nn.exp must have 1 operand and 1 result")
        operand = op.operands[0]
        result = op.results[0]
        if not isinstance(operand.type, NnMemoryType):
            raise AnalysisError("nn.exp operand must be nn.memory")
        if not isinstance(result.type, NnMemoryType):
            raise AnalysisError("nn.exp result must be nn.memory")
        if operand.type.shape != result.type.shape:
            raise AnalysisError("nn.exp operand/result shape mismatch")
        if operand.type.element_type != result.type.element_type:
            raise AnalysisError("nn.exp operand/result element_type mismatch")
        numel = _numel_from_mem_type(result.type)
        if numel is None:
            raise AnalysisError("nn.exp shape unsupported")
        elem_size = _element_size(result.type.element_type, overrides)
        if elem_size is None:
            raise AnalysisError("nn.exp dtype unsupported")
        read_bytes = numel * sp.Integer(elem_size)
        write_bytes = numel * sp.Integer(elem_size)
        memory_items: list[object] = []
        if config.enable_memory:
            token = _space_token_from_mem_type(operand.type)
            memory_items.append(
                _build_memory_item(
                    _compute_path(token, "read"),
                    "read",
                    read_bytes,
                    config,
                )
            )
            memory_items.append(
                _build_memory_item(
                    _compute_path(_space_token_from_mem_type(result.type), "write"),
                    "write",
                    write_bytes,
                    config,
                )
            )
        return _finalize_memory_analysis(
            op_name=op.name,
            read_bytes=read_bytes,
            write_bytes=write_bytes,
            memory_items=memory_items,
            value_reads=[(operand, read_bytes)],
            result_write_bytes=write_bytes,
            config=config,
        )

    if name in _NN_REDUCE_OPS:
        if len(op.operands) != 1 or len(op.results) != 1:
            raise AnalysisError("nn.reduce_* must have 1 operand and 1 result")
        operand = op.operands[0]
        result = op.results[0]
        if not isinstance(operand.type, NnMemoryType):
            raise AnalysisError("nn.reduce_* operand must be nn.memory")
        if not isinstance(result.type, NnMemoryType):
            raise AnalysisError("nn.reduce_* result must be nn.memory")
        if operand.type.element_type != result.type.element_type:
            raise AnalysisError("nn.reduce_* operand/result element_type mismatch")
        input_numel = _numel_from_mem_type(operand.type)
        result_numel = _numel_from_mem_type(result.type)
        if input_numel is None or result_numel is None:
            raise AnalysisError("nn.reduce_* shape unsupported")
        elem_size = _element_size(operand.type.element_type, overrides)
        if elem_size is None:
            raise AnalysisError("nn.reduce_* dtype unsupported")
        read_bytes = input_numel * sp.Integer(elem_size)
        write_bytes = result_numel * sp.Integer(elem_size)
        memory_items: list[object] = []
        if config.enable_memory:
            memory_items.append(
                _build_memory_item(
                    _compute_path(_space_token_from_mem_type(operand.type), "read"),
                    "read",
                    read_bytes,
                    config,
                )
            )
            memory_items.append(
                _build_memory_item(
                    _compute_path(_space_token_from_mem_type(result.type), "write"),
                    "write",
                    write_bytes,
                    config,
                )
            )
        return _finalize_memory_analysis(
            op_name=op.name,
            read_bytes=read_bytes,
            write_bytes=write_bytes,
            memory_items=memory_items,
            value_reads=[(operand, read_bytes)],
            result_write_bytes=write_bytes,
            config=config,
        )

    if name in _NN_DIRECT_OPS:
        if len(op.operands) != 1 or len(op.results) != 1:
            raise AnalysisError("nn.broadcast/transpose must have 1 operand and 1 result")
        operand = op.operands[0]
        result = op.results[0]
        if not isinstance(operand.type, NnMemoryType):
            raise AnalysisError("nn.broadcast/transpose operand must be nn.memory")
        if not isinstance(result.type, NnMemoryType):
            raise AnalysisError("nn.broadcast/transpose result must be nn.memory")
        if operand.type.element_type != result.type.element_type:
            raise AnalysisError("nn.broadcast/transpose element_type mismatch")
        input_numel = _numel_from_mem_type(operand.type)
        result_numel = _numel_from_mem_type(result.type)
        if input_numel is None or result_numel is None:
            raise AnalysisError("nn.broadcast/transpose shape unsupported")
        elem_size = _element_size(operand.type.element_type, overrides)
        if elem_size is None:
            raise AnalysisError("nn.broadcast/transpose dtype unsupported")
        if name == "nn.broadcast":
            read_bytes = input_numel * sp.Integer(elem_size)
        else:
            read_bytes = result_numel * sp.Integer(elem_size)
        write_bytes = result_numel * sp.Integer(elem_size)
        src_token = _space_token_from_mem_type(operand.type)
        dst_token = _space_token_from_mem_type(result.type)
        path = f"{src_token}->{dst_token}"
        memory_items: list[object] = []
        if config.enable_memory:
            memory_items.append(_build_memory_item(path, "read", read_bytes, config))
            memory_items.append(_build_memory_item(path, "write", write_bytes, config))
        return _finalize_memory_analysis(
            op_name=op.name,
            read_bytes=read_bytes,
            write_bytes=write_bytes,
            memory_items=memory_items,
            value_reads=[(operand, read_bytes)],
            result_write_bytes=write_bytes,
            config=config,
        )

    if name in _NN_MATMUL_OPS:
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
        if lhs_type.element_type != rhs_type.element_type or lhs_type.element_type != result_type.element_type:
            raise AnalysisError("nn.matmul operand/result element_type must match")
        elem_size = _element_size(lhs_type.element_type, overrides)
        if elem_size is None:
            raise AnalysisError("nn.matmul operand dtype unsupported")
        elem_size_expr = sp.Integer(elem_size)
        lhs_bytes = m_dim * k_dim * elem_size_expr
        rhs_bytes = k_dim * n_dim * elem_size_expr
        read_bytes = lhs_bytes + rhs_bytes
        write_bytes = m_dim * n_dim * elem_size_expr
        memory_items: list[object] = []
        if config.enable_memory:
            memory_items.append(
                _build_memory_item(
                    _compute_path(_space_token_from_mem_type(lhs_type), "read"),
                    "read",
                    lhs_bytes,
                    config,
                )
            )
            memory_items.append(
                _build_memory_item(
                    _compute_path(_space_token_from_mem_type(rhs_type), "read"),
                    "read",
                    rhs_bytes,
                    config,
                )
            )
            memory_items.append(
                _build_memory_item(
                    _compute_path(_space_token_from_mem_type(result_type), "write"),
                    "write",
                    write_bytes,
                    config,
                )
            )
        return _finalize_memory_analysis(
            op_name=op.name,
            read_bytes=read_bytes,
            write_bytes=write_bytes,
            memory_items=memory_items,
            value_reads=[(lhs, lhs_bytes), (rhs, rhs_bytes)],
            result_write_bytes=write_bytes,
            config=config,
        )

    return None


__all__ = ["analyze_nn_memory_op"]
