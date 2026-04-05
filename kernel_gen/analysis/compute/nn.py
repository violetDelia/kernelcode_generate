"""NN dialect compute analysis helpers.

创建者: jcc你莫辜负
最后修改人: 金铲铲大作战

功能说明:
- 承接 `nn.*` 逐元素/一元/reduce 与 `nn.matmul` 的计算分类分析。
- 仅产出 compute 统计，不直接生成 memory item。
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
    _dim_to_expr,
    _dtype_string,
    _is_predicate_type,
    _numel_from_mem_type,
)
from kernel_gen.analysis.compute import ComputeKind, register_compute
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
_NN_UNARY_OPS = {"nn.exp"}
_NN_REDUCE_OPS = {"nn.reduce_sum", "nn.reduce_min", "nn.reduce_max"}


@register_compute(_NN_ELEMENTWISE_OPS)
def analyze_nn_elementwise_op(op: Operation, config: AnalysisConfig) -> _AnalyzedOp | None:
    """分析 `nn.*` 逐元素算术/比较 op 的计算分类。

    创建者: jcc你莫辜负
    最后修改人: 金铲铲大作战

    功能说明:
    - 对逐元素 `nn.*` 统一产出 `ComputeKind.VECTOR`。
    - `tensor + const` 保留 `VECTOR` 计算分类。
    - 比较输出必须为 `i1` predicate。

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

    if lhs_mem:
        lhs_type = lhs.type
        if lhs_type.shape != result_type.shape:
            raise AnalysisError("result shape must match memory operand")
    if rhs_mem:
        rhs_type = rhs.type
        if rhs_type.shape != result_type.shape:
            raise AnalysisError("result shape must match memory operand")

    if op.name in _NN_COMPARE_OPS:
        if not _is_predicate_type(result_type.element_type):
            raise AnalysisError("compare result element_type must be i1")

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
        memory_items=(),
        compute=numel if config.enable_compute else sp.Integer(0),
        read_bytes=sp.Integer(0),
        write_bytes=sp.Integer(0),
        value_reads=(),
        result_write_bytes=sp.Integer(0),
    )


@register_compute(_NN_UNARY_OPS)
def analyze_nn_unary_op(op: Operation, config: AnalysisConfig) -> _AnalyzedOp | None:
    """分析 `nn.exp` 的计算分类。

    创建者: 金铲铲大作战
    最后修改人: 金铲铲大作战

    功能说明:
    - `nn.exp` 统一产出 `ComputeKind.MATH`。
    - 计算量为 `numel(result)`。

    使用示例:
    - analyzed = analyze_nn_unary_op(op, config)

    关联文件:
    - spec: spec/analysis/analysis_engine.md
    - test: test/analysis/test_analysis.py
    - 功能实现: kernel_gen/analysis/compute/nn.py
    """

    if op.name not in _NN_UNARY_OPS:
        return None
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

    compute_items: list[ComputeItem] = []
    if config.enable_compute:
        compute_items.append(
            ComputeItem(
                kind=ComputeKind.MATH,
                amount=numel,
                dtype=_dtype_string(result.type.element_type),
            )
        )
    return _AnalyzedOp(
        op_name=op.name,
        compute_items=compute_items,
        memory_items=(),
        compute=numel if config.enable_compute else sp.Integer(0),
        read_bytes=sp.Integer(0),
        write_bytes=sp.Integer(0),
        value_reads=(),
        result_write_bytes=sp.Integer(0),
    )


@register_compute(_NN_REDUCE_OPS)
def analyze_nn_reduce_op(op: Operation, config: AnalysisConfig) -> _AnalyzedOp | None:
    """分析 `nn.reduce_*` 的计算分类。

    创建者: 金铲铲大作战
    最后修改人: 金铲铲大作战

    功能说明:
    - `nn.reduce_*` 统一产出 `ComputeKind.VECTOR`。
    - 计算量为 `numel(input) - numel(result)`。

    使用示例:
    - analyzed = analyze_nn_reduce_op(op, config)

    关联文件:
    - spec: spec/analysis/analysis_engine.md
    - test: test/analysis/test_analysis.py
    - 功能实现: kernel_gen/analysis/compute/nn.py
    """

    if op.name not in _NN_REDUCE_OPS:
        return None
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
    compute = input_numel - result_numel

    compute_items: list[ComputeItem] = []
    if config.enable_compute:
        compute_items.append(
            ComputeItem(
                kind=ComputeKind.VECTOR,
                amount=compute,
                dtype=_dtype_string(result.type.element_type),
            )
        )
    return _AnalyzedOp(
        op_name=op.name,
        compute_items=compute_items,
        memory_items=(),
        compute=compute if config.enable_compute else sp.Integer(0),
        read_bytes=sp.Integer(0),
        write_bytes=sp.Integer(0),
        value_reads=(),
        result_write_bytes=sp.Integer(0),
    )


def analyze_nn_matmul_ir_op(op: Operation, config: AnalysisConfig) -> _AnalyzedOp | None:
    """分析 `nn.matmul` 的计算分类。

    创建者: jcc你莫辜负
    最后修改人: 金铲铲大作战

    功能说明:
    - 对二维收缩 `nn.matmul` 统一产出 `ComputeKind.TENSOR`。
    - 保持现有 `2*M*N*K` 理论计算量。

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

    if lhs_type.element_type != rhs_type.element_type or lhs_type.element_type != result_type.element_type:
        raise AnalysisError("nn.matmul operand/result element_type must match")
    compute = sp.Integer(2) * m_dim * n_dim * k_dim
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
        memory_items=(),
        compute=compute if config.enable_compute else sp.Integer(0),
        read_bytes=sp.Integer(0),
        write_bytes=sp.Integer(0),
        value_reads=(),
        result_write_bytes=sp.Integer(0),
    )


__all__ = [
    "analyze_nn_elementwise_op",
    "analyze_nn_unary_op",
    "analyze_nn_reduce_op",
    "analyze_nn_matmul_ir_op",
]
