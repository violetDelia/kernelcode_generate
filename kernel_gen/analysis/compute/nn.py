"""NN dialect compute analysis helpers.

创建者: jcc你莫辜负
最后修改人: 朽木露琪亚

功能说明:
- 承接 `nn.*` 逐元素/一元/reduce/softmax/img2col 与 `nn.matmul` 的计算分类分析。
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
from xdsl.dialects.builtin import BFloat16Type, Float16Type, Float32Type, Float64Type, IntAttr, IntegerAttr
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
_NN_SOFTMAX_OPS = {"nn.softmax"}
_NN_IMG2COL_OPS = {"nn.img2col1d", "nn.img2col2d"}


def _get_i64_attr(op: Operation, name: str) -> int:
    """读取 op 的 i64 整数属性。

    创建者: 朽木露琪亚
    最后修改人: 朽木露琪亚

    功能说明:
    - 仅接受 IntAttr/IntegerAttr。
    - 缺失或类型不匹配时抛 AnalysisError。

    使用示例:
    - axis = _get_i64_attr(op, "axis")

    关联文件:
    - spec: spec/analysis/analysis_engine.md
    - test: test/analysis/test_analysis.py
    - 功能实现: kernel_gen/analysis/compute/nn.py
    """
    attr = op.attributes.get(name)
    if isinstance(attr, IntAttr):
        return int(attr.data)
    if isinstance(attr, IntegerAttr):
        return int(attr.value.data)
    raise AnalysisError(f"{op.name} {name} must be integer")


def _img2col_output_dim(
    input_dim: sp.Basic,
    kernel: int,
    stride: int,
    dilation: int,
    pad_before: int,
    pad_after: int,
) -> sp.Basic:
    """计算 img2col 输出维度表达式。

    创建者: 朽木露琪亚
    最后修改人: 朽木露琪亚

    功能说明:
    - 复用卷积输出维度公式，返回 floor(...) + 1 的表达式。

    使用示例:
    - out = _img2col_output_dim(sp.Integer(8), 3, 1, 1, 1, 1)

    关联文件:
    - spec: spec/dialect/nn.md
    - test: test/analysis/test_analysis.py
    - 功能实现: kernel_gen/analysis/compute/nn.py
    """
    kernel_expr = sp.Integer(kernel)
    stride_expr = sp.Integer(stride)
    dilation_expr = sp.Integer(dilation)
    pad_before_expr = sp.Integer(pad_before)
    pad_after_expr = sp.Integer(pad_after)
    numerator = input_dim + pad_before_expr + pad_after_expr - dilation_expr * (kernel_expr - 1) - 1
    return numerator // stride_expr + 1


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


@register_compute(_NN_SOFTMAX_OPS)
def analyze_nn_softmax_op(op: Operation, config: AnalysisConfig) -> _AnalyzedOp | None:
    """分析 `nn.softmax` 的计算分类。

    创建者: 朽木露琪亚
    最后修改人: 朽木露琪亚

    功能说明:
    - 校验 axis 范围与输入/输出 shape 一致性。
    - 计算量按 `VECTOR = 4*N - 2*G`、`MATH = N` 统计，`N=numel(input)`、`G=axis 之外维度乘积`。
    - 同时产出 `ComputeKind.VECTOR` 与 `ComputeKind.MATH`。

    使用示例:
    - analyzed = analyze_nn_softmax_op(op, config)

    关联文件:
    - spec: spec/dialect/nn.md
    - test: test/analysis/test_analysis.py
    - 功能实现: kernel_gen/analysis/compute/nn.py
    """

    if op.name not in _NN_SOFTMAX_OPS:
        return None
    if len(op.operands) != 1 or len(op.results) != 1:
        raise AnalysisError("nn.softmax must have 1 operand and 1 result")
    operand = op.operands[0]
    result = op.results[0]
    if not isinstance(operand.type, NnMemoryType):
        raise AnalysisError("nn.softmax operand must be nn.memory")
    if not isinstance(result.type, NnMemoryType):
        raise AnalysisError("nn.softmax result must be nn.memory")
    input_type = operand.type
    result_type = result.type
    if input_type.shape != result_type.shape:
        raise AnalysisError("nn.softmax input/result shape mismatch")
    if input_type.element_type != result_type.element_type:
        raise AnalysisError("nn.softmax input/result element_type mismatch")
    if not isinstance(input_type.element_type, (Float16Type, BFloat16Type, Float32Type, Float64Type)):
        raise AnalysisError("nn.softmax element_type must be float")

    rank = len(input_type.shape.data)
    if rank <= 0:
        raise AnalysisError("nn.softmax input rank must be positive")
    axis_value = _get_i64_attr(op, "axis")
    if axis_value < -rank or axis_value >= rank:
        raise AnalysisError("nn.softmax axis out of range")
    axis = axis_value + rank if axis_value < 0 else axis_value

    dims: list[sp.Basic] = []
    for dim in input_type.shape.data:
        dim_expr = _dim_to_expr(dim)
        if dim_expr is None:
            raise AnalysisError("nn.softmax shape unsupported")
        dims.append(dim_expr)

    numel = sp.Integer(1)
    groups = sp.Integer(1)
    for idx, dim in enumerate(dims):
        numel *= dim
        if idx != axis:
            groups *= dim
    vector_compute = sp.Integer(4) * numel - sp.Integer(2) * groups
    math_compute = numel

    compute_items: list[ComputeItem] = []
    if config.enable_compute:
        dtype = _dtype_string(result_type.element_type)
        compute_items.append(
            ComputeItem(
                kind=ComputeKind.VECTOR,
                amount=vector_compute,
                dtype=dtype,
            )
        )
        compute_items.append(
            ComputeItem(
                kind=ComputeKind.MATH,
                amount=math_compute,
                dtype=dtype,
            )
        )
    return _AnalyzedOp(
        op_name=op.name,
        compute_items=compute_items,
        memory_items=(),
        compute=vector_compute + math_compute if config.enable_compute else sp.Integer(0),
        read_bytes=sp.Integer(0),
        write_bytes=sp.Integer(0),
        value_reads=(),
        result_write_bytes=sp.Integer(0),
    )


@register_compute(_NN_IMG2COL_OPS)
def analyze_nn_img2col_op(op: Operation, config: AnalysisConfig) -> _AnalyzedOp | None:
    """分析 `nn.img2col1d/img2col2d` 的计算分类。

    创建者: 朽木露琪亚
    最后修改人: 朽木露琪亚

    功能说明:
    - 校验 img2col rank/attr 合同与输出形状约束。
    - 只做合同校验，不统计 compute。

    使用示例:
    - analyzed = analyze_nn_img2col_op(op, config)

    关联文件:
    - spec: spec/dialect/nn.md
    - test: test/analysis/test_analysis.py
    - 功能实现: kernel_gen/analysis/compute/nn.py
    """

    if op.name not in _NN_IMG2COL_OPS:
        return None
    if len(op.operands) != 1 or len(op.results) != 1:
        raise AnalysisError("nn.img2col must have 1 operand and 1 result")
    operand = op.operands[0]
    result = op.results[0]
    if not isinstance(operand.type, NnMemoryType):
        raise AnalysisError("nn.img2col operand must be nn.memory")
    if not isinstance(result.type, NnMemoryType):
        raise AnalysisError("nn.img2col result must be nn.memory")
    input_type = operand.type
    result_type = result.type
    if input_type.element_type != result_type.element_type:
        raise AnalysisError("nn.img2col element_type mismatch")

    input_dims: list[sp.Basic] = []
    for dim in input_type.shape.data:
        dim_expr = _dim_to_expr(dim)
        if dim_expr is None:
            raise AnalysisError("nn.img2col shape unsupported")
        input_dims.append(dim_expr)
    result_dims: list[sp.Basic] = []
    for dim in result_type.shape.data:
        dim_expr = _dim_to_expr(dim)
        if dim_expr is None:
            raise AnalysisError("nn.img2col shape unsupported")
        result_dims.append(dim_expr)

    if op.name == "nn.img2col1d":
        if len(input_dims) != 3:
            raise AnalysisError("nn.img2col1d requires rank-3 input")
        if len(result_dims) != 4:
            raise AnalysisError("nn.img2col1d requires rank-4 result")
        kw = _get_i64_attr(op, "kw")
        sw = _get_i64_attr(op, "sw")
        dw = _get_i64_attr(op, "dw")
        pl = _get_i64_attr(op, "pl")
        pr = _get_i64_attr(op, "pr")
        if kw <= 0 or sw <= 0 or dw <= 0:
            raise AnalysisError("nn.img2col1d kw/sw/dw must be positive")
        if pl < 0 or pr < 0:
            raise AnalysisError("nn.img2col1d pl/pr must be non-negative")
        n_dim, c_dim, w_dim = input_dims
        w_out = _img2col_output_dim(w_dim, kw, sw, dw, pl, pr)
        if isinstance(w_out, sp.Integer) and int(w_out) <= 0:
            raise AnalysisError("nn.img2col1d output shape invalid")
        expected_shape = [n_dim, c_dim, sp.Integer(kw), w_out]
        if result_dims != expected_shape:
            raise AnalysisError("nn.img2col1d output shape mismatch")
    else:
        if len(input_dims) != 4:
            raise AnalysisError("nn.img2col2d requires rank-4 input")
        if len(result_dims) != 6:
            raise AnalysisError("nn.img2col2d requires rank-6 result")
        kh = _get_i64_attr(op, "kh")
        kw = _get_i64_attr(op, "kw")
        sh = _get_i64_attr(op, "sh")
        sw = _get_i64_attr(op, "sw")
        dh = _get_i64_attr(op, "dh")
        dw = _get_i64_attr(op, "dw")
        ph = _get_i64_attr(op, "ph")
        pw = _get_i64_attr(op, "pw")
        pl = _get_i64_attr(op, "pl")
        pr = _get_i64_attr(op, "pr")
        if kh <= 0 or kw <= 0 or sh <= 0 or sw <= 0 or dh <= 0 or dw <= 0:
            raise AnalysisError("nn.img2col2d kh/kw/sh/sw/dh/dw must be positive")
        if ph < 0 or pw < 0 or pl < 0 or pr < 0:
            raise AnalysisError("nn.img2col2d ph/pw/pl/pr must be non-negative")
        n_dim, c_dim, h_dim, w_dim = input_dims
        h_out = _img2col_output_dim(h_dim, kh, sh, dh, ph, pw)
        w_out = _img2col_output_dim(w_dim, kw, sw, dw, pl, pr)
        if isinstance(h_out, sp.Integer) and int(h_out) <= 0:
            raise AnalysisError("nn.img2col2d output shape invalid")
        if isinstance(w_out, sp.Integer) and int(w_out) <= 0:
            raise AnalysisError("nn.img2col2d output shape invalid")
        expected_shape = [n_dim, c_dim, sp.Integer(kh), sp.Integer(kw), h_out, w_out]
        if result_dims != expected_shape:
            raise AnalysisError("nn.img2col2d output shape mismatch")

    compute_items: list[ComputeItem] = []
    return _AnalyzedOp(
        op_name=op.name,
        compute_items=compute_items,
        memory_items=(),
        compute=sp.Integer(0),
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
    "analyze_nn_softmax_op",
    "analyze_nn_img2col_op",
    "analyze_nn_reduce_op",
    "analyze_nn_matmul_ir_op",
]
