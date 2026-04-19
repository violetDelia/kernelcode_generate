"""matmul/img2col family lowering 实现。

创建者: 小李飞刀
最后一次更改: 小李飞刀

功能说明:
- 将 nn.matmul / nn.img2col1d / nn.img2col2d lower 为对应 kernel op。
- 统一在 lowering 内部创建 dma.alloc 结果 memory。

使用示例:
- from kernel_gen.passes.lowering.nn_lowering.matmul_img2col_lowering import lower_matmul_img2col_family
- handled = lower_matmul_img2col_family(block, op)

关联文件:
- spec: spec/pass/lowering/nn_lowering/matmul_img2col_lowering.md
- test: test/pass/nn_lowering/matmul.py
- 功能实现: kernel_gen/passes/lowering/nn_lowering/matmul_img2col_lowering.py
"""

from __future__ import annotations

from collections.abc import Iterable

from xdsl.dialects.builtin import ArrayAttr, IntAttr, IntegerAttr, StringAttr, i64
from xdsl.ir import Attribute, Block, Operation, SSAValue

from kernel_gen.dialect.dma import DmaAllocOp
from kernel_gen.dialect.kernel import KernelImg2col1dOp, KernelImg2col2dOp, KernelMatmulOp
from kernel_gen.dialect.nn import NnMemoryType
from kernel_gen.dialect.symbol import (
    SymbolAddOp,
    SymbolConstOp,
    SymbolFloorDivOp,
    SymbolGetDimOp,
    SymbolMulOp,
    SymbolSubOp,
    SymbolValueType,
    build_public_symbol_expr,
)
from .nn_lowering_utility import (
    NnLoweringError,
    ensure_operand_count,
    ensure_single_result,
    ensure_space_attr,
)


def _normalize_shape_dims(shape: Iterable[Attribute]) -> list[int | str]:
    """将 shape 维度规范化为 int 或 str。

    创建者: 小李飞刀
    最后一次更改: 小李飞刀

    功能说明:
    - IntAttr/IntegerAttr 转换为 int。
    - StringAttr 转换为 str。
    - 其它类型抛出 NnLoweringError。

    使用示例:
    - dims = _normalize_shape_dims(mem_type.shape.data)

    关联文件:
    - spec: spec/pass/lowering/nn_lowering/matmul_img2col_lowering.md
    - test: test/pass/nn_lowering/matmul.py
    - 功能实现: kernel_gen/passes/lowering/nn_lowering/matmul_img2col_lowering.py
    """

    dims: list[int | str] = []
    for dim in shape:
        if isinstance(dim, IntAttr):
            dims.append(dim.data)
            continue
        if isinstance(dim, IntegerAttr):
            dims.append(dim.value.data)
            continue
        if isinstance(dim, StringAttr):
            dims.append(dim.data)
            continue
        raise NnLoweringError("matmul shape must be IntAttr or StringAttr")
    return dims


def _ensure_matmul_shape(
    lhs_type: NnMemoryType,
    rhs_type: NnMemoryType,
    out_type: NnMemoryType,
) -> None:
    """校验 nn.matmul 的 shape 合同。

    创建者: 小李飞刀
    最后一次更改: 小李飞刀

    功能说明:
    - 确认 lhs/rhs/out 均为 rank-2。
    - 校验 `[M, K] x [K, N] -> [M, N]` 规则。

    使用示例:
    - _ensure_matmul_shape(lhs_type, rhs_type, out_type)

    关联文件:
    - spec: spec/pass/lowering/nn_lowering/matmul_img2col_lowering.md
    - test: test/pass/nn_lowering/matmul.py
    - 功能实现: kernel_gen/passes/lowering/nn_lowering/matmul_img2col_lowering.py
    """

    lhs_shape = _normalize_shape_dims(lhs_type.shape.data)
    rhs_shape = _normalize_shape_dims(rhs_type.shape.data)
    out_shape = _normalize_shape_dims(out_type.shape.data)
    if len(lhs_shape) != 2 or len(rhs_shape) != 2 or len(out_shape) != 2:
        raise NnLoweringError("matmul requires rank-2 memory types")
    if lhs_shape[1] != rhs_shape[0]:
        raise NnLoweringError("matmul contracting dimensions must match")
    if out_shape[0] != lhs_shape[0] or out_shape[1] != rhs_shape[1]:
        raise NnLoweringError("matmul output shape must match operands")


def _ensure_matmul_stride(mem_type: NnMemoryType) -> None:
    """校验 nn.matmul 的 stride 连续性。

    创建者: 小李飞刀
    最后一次更改: 小李飞刀

    功能说明:
    - 当 shape/stride 可静态求值时，要求 stride 为连续布局。

    使用示例:
    - _ensure_matmul_stride(out_type)

    关联文件:
    - spec: spec/pass/lowering/nn_lowering/matmul_img2col_lowering.md
    - test: test/pass/nn_lowering/matmul.py
    - 功能实现: kernel_gen/passes/lowering/nn_lowering/matmul_img2col_lowering.py
    """

    shape = mem_type.shape.data
    stride = mem_type.stride.data
    if len(shape) != 2 or len(stride) != 2:
        raise NnLoweringError("matmul stride must be contiguous")
    if not all(isinstance(dim, IntAttr) for dim in shape):
        return
    if not all(isinstance(dim, IntAttr) for dim in stride):
        return
    expected_stride0 = shape[1].data
    expected_stride1 = 1
    if stride[0].data != expected_stride0 or stride[1].data != expected_stride1:
        raise NnLoweringError("matmul stride must be contiguous")


def _ensure_symbol_int(
    block: Block,
    op: Operation,
    operand: SSAValue | Operation,
) -> tuple[SSAValue, SymbolConstOp | None]:
    """确保 img2col 参数为 symbol.int。

    创建者: 小李飞刀
    最后一次更改: 小李飞刀

    功能说明:
    - 若 operand 为 symbol.const，则克隆为新的 symbol.const 并返回。
    - 若 operand 为 symbol.int（非 symbol.const）直接返回。
    - 其余类型统一抛出 NnLoweringError。

    使用示例:
    - kw, _ = _ensure_symbol_int(block, op, op.operands[1])

    关联文件:
    - spec: spec/pass/lowering/nn_lowering/matmul_img2col_lowering.md
    - test: test/pass/nn_lowering/img2col1d.py
    - 功能实现: kernel_gen/passes/lowering/nn_lowering/matmul_img2col_lowering.py
    """

    if isinstance(operand, Operation):
        operand = operand.results[0]
    if isinstance(operand.type, SymbolValueType):
        owner = operand.owner
        if isinstance(owner, SymbolConstOp):
            cloned = SymbolConstOp(owner.value)
            block.insert_op_before(cloned, op)
            return cloned.result, owner
        return operand, None
    if isinstance(operand, SSAValue):
        raise NnLoweringError("nn img2col parameters must be symbol.int")
    raise NnLoweringError("nn img2col parameters must be symbol.int")


def _ensure_img2col_params(
    block: Block,
    op: Operation,
    operand_count: int,
    dynamic_count: int,
) -> tuple[SSAValue, list[SSAValue], list[SymbolConstOp]]:
    """校验并提取 img2col 参数。

    创建者: 小李飞刀
    最后一次更改: 小李飞刀

    功能说明:
    - 校验参数数量，并提取 dynamic 参数列表。

    使用示例:
    - operand, params, cleanup = _ensure_img2col_params(block, op, 6, 5)

    关联文件:
    - spec: spec/pass/lowering/nn_lowering/matmul_img2col_lowering.md
    - test: test/pass/nn_lowering/img2col1d.py
    - 功能实现: kernel_gen/passes/lowering/nn_lowering/matmul_img2col_lowering.py
    """

    ensure_operand_count(op, operand_count)
    operand = op.operands[0]
    params: list[SSAValue] = []
    cleanup_ops: list[SymbolConstOp] = []
    for idx in range(dynamic_count):
        value, cleanup_op = _ensure_symbol_int(block, op, op.operands[idx + 1])
        params.append(value)
        if cleanup_op is not None and cleanup_op not in cleanup_ops:
            cleanup_ops.append(cleanup_op)
    return operand, params, cleanup_ops


def _symbol_expr(value: SSAValue) -> str:
    """读取 symbol.int 的表达式字符串。

    创建者: 小李飞刀
    最后一次更改: 小李飞刀

    功能说明:
    - 将 `!symbol.int<"...">` 的表达式文本提取为字符串。
    - 非 `symbol.int` 时抛出 `NnLoweringError`。

    使用示例:
    - expr = _symbol_expr(symbol_value)

    关联文件:
    - spec: spec/pass/lowering/nn_lowering/matmul_img2col_lowering.md
    - test: test/pass/nn_lowering/img2col1d.py
    - 功能实现: kernel_gen/passes/lowering/nn_lowering/matmul_img2col_lowering.py
    """

    if not isinstance(value.type, SymbolValueType):
        raise NnLoweringError("symbol expression must be symbol.int")
    return value.type.expr.expr.data


def _build_symbol_attr(value: SSAValue, *, prefer_i64: bool) -> Attribute:
    """将 symbol.int SSAValue 转为适配的 attribute。

    创建者: 小李飞刀
    最后一次更改: 小李飞刀

    功能说明:
    - 数值表达式转为 IntAttr / IntegerAttr。
    - 其余表达式转为 StringAttr。

    使用示例:
    - attr = _build_symbol_attr(sw, prefer_i64=False)

    关联文件:
    - spec: spec/pass/lowering/nn_lowering/matmul_img2col_lowering.md
    - test: test/pass/nn_lowering/img2col2d.py
    - 功能实现: kernel_gen/passes/lowering/nn_lowering/matmul_img2col_lowering.py
    """

    expr = _symbol_expr(value)
    if expr.lstrip("-").isdigit():
        number = int(expr)
        if prefer_i64:
            return IntegerAttr(number, i64)
        return IntAttr(number)
    return StringAttr(expr)


def _get_symbol_dim_by_axis(
    block: Block,
    op: Operation,
    operand: SSAValue,
    axis: int,
    cache: dict[int, SSAValue],
) -> SSAValue:
    """按轴读取输入 memory 的符号维度。

    创建者: 小李飞刀
    最后一次更改: 小李飞刀

    功能说明:
    - 仅当指定轴为符号维度时，插入一次 `symbol.get_dim`。
    - 使用缓存避免同一轴重复生成 `symbol.get_dim`。

    使用示例:
    - width = _get_symbol_dim_by_axis(block, op, operand, 2, cache)

    关联文件:
    - spec: spec/pass/lowering/nn_lowering/matmul_img2col_lowering.md
    - test: test/pass/nn_lowering/img2col1d.py
    - 功能实现: kernel_gen/passes/lowering/nn_lowering/matmul_img2col_lowering.py
    """

    if not isinstance(operand.type, NnMemoryType):
        raise NnLoweringError("nn img2col operand must be nn.memory")
    cached = cache.get(axis)
    if cached is not None:
        return cached
    dims = list(operand.type.shape.data)
    if axis < 0 or axis >= len(dims):
        raise NnLoweringError("nn img2col operand axis out of range")
    dim = dims[axis]
    if not isinstance(dim, StringAttr):
        raise NnLoweringError("nn img2col symbolic dim must come from symbolic source axis")
    symbol_op = SymbolGetDimOp(operand, axis)
    block.insert_op_before(symbol_op, op)
    cache[axis] = symbol_op.result
    return symbol_op.result


def _build_img2col1d_dynamic_dims(
    block: Block,
    op: Operation,
    operand: SSAValue,
    params: list[SSAValue],
    result_type: NnMemoryType,
) -> list[SSAValue]:
    """构造 img2col1d 的 dynamic shape operand 列表。

    创建者: 小李飞刀
    最后一次更改: 小李飞刀

    功能说明:
    - 当输出包含符号维度时，生成 `symbol.get_dim` 与 `symbol` 算术链。
    - 返回 `dma.alloc` 所需的 dynamic shape operand 列表。

    使用示例:
    - dynamic_dims = _build_img2col1d_dynamic_dims(block, op, operand, params, result_type)

    关联文件:
    - spec: spec/pass/lowering/nn_lowering/matmul_img2col_lowering.md
    - test: test/pass/nn_lowering/img2col1d.py
    - 功能实现: kernel_gen/passes/lowering/nn_lowering/matmul_img2col_lowering.py
    """

    if not any(isinstance(dim, StringAttr) for dim in result_type.shape.data):
        return []
    one = SymbolConstOp(1)
    block.insert_op_before(one, op)
    source_dims: dict[int, SSAValue] = {}
    for axis in range(3):
        if isinstance(operand.type.shape.data[axis], StringAttr):
            _get_symbol_dim_by_axis(block, op, operand, axis, source_dims)
    kw, sw, dw, pl, pr = params
    w = _get_symbol_dim_by_axis(block, op, operand, 2, source_dims)
    one_expr = _symbol_expr(one.result)
    kw_expr = _symbol_expr(kw)
    sw_expr = _symbol_expr(sw)
    dw_expr = _symbol_expr(dw)
    pl_expr = _symbol_expr(pl)
    pr_expr = _symbol_expr(pr)
    w_expr = _symbol_expr(w)

    kw_minus_one_expr = f"{kw_expr} - {one_expr}"
    kw_minus_one = SymbolSubOp(kw, one, SymbolValueType.from_expr(kw_minus_one_expr))
    block.insert_op_before(kw_minus_one, op)

    dw_mul_expr = f"{dw_expr}*({kw_minus_one_expr})"
    dw_mul = SymbolMulOp(dw, kw_minus_one, SymbolValueType.from_expr(dw_mul_expr))
    block.insert_op_before(dw_mul, op)

    w_pl_expr = f"{w_expr} + {pl_expr}"
    w_pl = SymbolAddOp(w, pl, SymbolValueType.from_expr(w_pl_expr))
    block.insert_op_before(w_pl, op)

    w_pl_pr_expr = f"{w_pl_expr} + {pr_expr}"
    w_pl_pr = SymbolAddOp(w_pl, pr, SymbolValueType.from_expr(w_pl_pr_expr))
    block.insert_op_before(w_pl_pr, op)

    w_minus_dw_expr = f"{w_pl_pr_expr} - {dw_mul_expr}"
    w_minus_dw = SymbolSubOp(w_pl_pr, dw_mul, SymbolValueType.from_expr(w_minus_dw_expr))
    block.insert_op_before(w_minus_dw, op)

    w_minus_one_expr = f"{w_minus_dw_expr} - {one_expr}"
    w_minus_one = SymbolSubOp(w_minus_dw, one, SymbolValueType.from_expr(w_minus_one_expr))
    block.insert_op_before(w_minus_one, op)

    w_div_expr = f"({w_minus_one_expr}) // {sw_expr}"
    w_div = SymbolFloorDivOp(w_minus_one, sw, SymbolValueType.from_expr(w_div_expr))
    block.insert_op_before(w_div, op)

    w_out_expr = build_public_symbol_expr(w_div_expr, one_expr, "+")
    w_out = SymbolAddOp(w_div, one, SymbolValueType.from_expr(w_out_expr))
    block.insert_op_before(w_out, op)

    dynamic_dims: list[SSAValue] = []
    for axis, dim in enumerate(result_type.shape.data):
        if isinstance(dim, StringAttr):
            if axis == 0:
                dynamic_dims.append(_get_symbol_dim_by_axis(block, op, operand, 0, source_dims))
            elif axis == 1:
                dynamic_dims.append(_get_symbol_dim_by_axis(block, op, operand, 1, source_dims))
            elif axis == 2:
                dynamic_dims.append(kw)
            elif axis == 3:
                dynamic_dims.append(w_out.result)
            else:
                raise NnLoweringError("nn img2col1d result rank must be 4")
    return dynamic_dims


def _build_img2col2d_dynamic_dims(
    block: Block,
    op: Operation,
    operand: SSAValue,
    params: list[SSAValue],
    result_type: NnMemoryType,
) -> list[SSAValue]:
    """构造 img2col2d 的 dynamic shape operand 列表。

    创建者: 小李飞刀
    最后一次更改: 小李飞刀

    功能说明:
    - 当输出包含符号维度时，生成 `symbol.get_dim` 与 `symbol` 算术链。
    - 返回 `dma.alloc` 所需的 dynamic shape operand 列表。

    使用示例:
    - dynamic_dims = _build_img2col2d_dynamic_dims(block, op, operand, params, result_type)

    关联文件:
    - spec: spec/pass/lowering/nn_lowering/matmul_img2col_lowering.md
    - test: test/pass/nn_lowering/img2col2d.py
    - 功能实现: kernel_gen/passes/lowering/nn_lowering/matmul_img2col_lowering.py
    """

    if not any(isinstance(dim, StringAttr) for dim in result_type.shape.data):
        return []
    one = SymbolConstOp(1)
    block.insert_op_before(one, op)
    source_dims: dict[int, SSAValue] = {}
    for axis in range(4):
        if isinstance(operand.type.shape.data[axis], StringAttr):
            _get_symbol_dim_by_axis(block, op, operand, axis, source_dims)
    kh, kw, sh, sw, dh, dw, ph, pw, pl, pr = params
    h = _get_symbol_dim_by_axis(block, op, operand, 2, source_dims)
    w = _get_symbol_dim_by_axis(block, op, operand, 3, source_dims)
    one_expr = _symbol_expr(one.result)
    kh_expr = _symbol_expr(kh)
    kw_expr = _symbol_expr(kw)
    sh_expr = _symbol_expr(sh)
    sw_expr = _symbol_expr(sw)
    dh_expr = _symbol_expr(dh)
    dw_expr = _symbol_expr(dw)
    ph_expr = _symbol_expr(ph)
    pw_expr = _symbol_expr(pw)
    pl_expr = _symbol_expr(pl)
    pr_expr = _symbol_expr(pr)
    h_expr = _symbol_expr(h)
    w_expr = _symbol_expr(w)

    kh_minus_one_expr = f"{kh_expr} - {one_expr}"
    kh_minus_one = SymbolSubOp(kh, one, SymbolValueType.from_expr(kh_minus_one_expr))
    block.insert_op_before(kh_minus_one, op)
    kw_minus_one_expr = f"{kw_expr} - {one_expr}"
    kw_minus_one = SymbolSubOp(kw, one, SymbolValueType.from_expr(kw_minus_one_expr))
    block.insert_op_before(kw_minus_one, op)

    dh_mul_expr = f"{dh_expr}*({kh_minus_one_expr})"
    dh_mul = SymbolMulOp(dh, kh_minus_one, SymbolValueType.from_expr(dh_mul_expr))
    block.insert_op_before(dh_mul, op)
    dw_mul_expr = f"{dw_expr}*({kw_minus_one_expr})"
    dw_mul = SymbolMulOp(dw, kw_minus_one, SymbolValueType.from_expr(dw_mul_expr))
    block.insert_op_before(dw_mul, op)

    h_ph_expr = f"{h_expr} + {ph_expr}"
    h_ph = SymbolAddOp(h, ph, SymbolValueType.from_expr(h_ph_expr))
    block.insert_op_before(h_ph, op)
    h_ph_pw_expr = f"{h_ph_expr} + {pw_expr}"
    h_ph_pw = SymbolAddOp(h_ph, pw, SymbolValueType.from_expr(h_ph_pw_expr))
    block.insert_op_before(h_ph_pw, op)
    h_minus_dh_expr = f"{h_ph_pw_expr} - {dh_mul_expr}"
    h_minus_dh = SymbolSubOp(h_ph_pw, dh_mul, SymbolValueType.from_expr(h_minus_dh_expr))
    block.insert_op_before(h_minus_dh, op)
    h_minus_one_expr = f"{h_minus_dh_expr} - {one_expr}"
    h_minus_one = SymbolSubOp(h_minus_dh, one, SymbolValueType.from_expr(h_minus_one_expr))
    block.insert_op_before(h_minus_one, op)
    h_div_expr = f"({h_minus_one_expr}) // {sh_expr}"
    h_div = SymbolFloorDivOp(h_minus_one, sh, SymbolValueType.from_expr(h_div_expr))
    block.insert_op_before(h_div, op)
    h_out_expr = build_public_symbol_expr(h_div_expr, one_expr, "+")
    h_out = SymbolAddOp(h_div, one, SymbolValueType.from_expr(h_out_expr))
    block.insert_op_before(h_out, op)

    w_pl_expr = f"{w_expr} + {pl_expr}"
    w_pl = SymbolAddOp(w, pl, SymbolValueType.from_expr(w_pl_expr))
    block.insert_op_before(w_pl, op)
    w_pl_pr_expr = f"{w_pl_expr} + {pr_expr}"
    w_pl_pr = SymbolAddOp(w_pl, pr, SymbolValueType.from_expr(w_pl_pr_expr))
    block.insert_op_before(w_pl_pr, op)
    w_minus_dw_expr = f"{w_pl_pr_expr} - {dw_mul_expr}"
    w_minus_dw = SymbolSubOp(w_pl_pr, dw_mul, SymbolValueType.from_expr(w_minus_dw_expr))
    block.insert_op_before(w_minus_dw, op)
    w_minus_one_expr = f"{w_minus_dw_expr} - {one_expr}"
    w_minus_one = SymbolSubOp(w_minus_dw, one, SymbolValueType.from_expr(w_minus_one_expr))
    block.insert_op_before(w_minus_one, op)
    w_div_expr = f"({w_minus_one_expr}) // {sw_expr}"
    w_div = SymbolFloorDivOp(w_minus_one, sw, SymbolValueType.from_expr(w_div_expr))
    block.insert_op_before(w_div, op)
    w_out_expr = build_public_symbol_expr(w_div_expr, one_expr, "+")
    w_out = SymbolAddOp(w_div, one, SymbolValueType.from_expr(w_out_expr))
    block.insert_op_before(w_out, op)

    dynamic_dims: list[SSAValue] = []
    for axis, dim in enumerate(result_type.shape.data):
        if isinstance(dim, StringAttr):
            if axis == 0:
                dynamic_dims.append(_get_symbol_dim_by_axis(block, op, operand, 0, source_dims))
            elif axis == 1:
                dynamic_dims.append(_get_symbol_dim_by_axis(block, op, operand, 1, source_dims))
            elif axis == 2:
                dynamic_dims.append(kh)
            elif axis == 3:
                dynamic_dims.append(kw)
            elif axis == 4:
                dynamic_dims.append(h_out.result)
            elif axis == 5:
                dynamic_dims.append(w_out.result)
            else:
                raise NnLoweringError("nn img2col2d result rank must be 6")
    return dynamic_dims


def _lower_matmul(block: Block, op: Operation) -> None:
    """lower nn.matmul。

    创建者: 小李飞刀
    最后一次更改: 小李飞刀

    功能说明:
    - 校验 shape 与 stride。
    - 当 result shape 含符号维度时，插入 symbol.get_dim 作为 dma.alloc dynamic shape。
    - 先创建 dma.alloc，再调用 kernel.matmul。

    使用示例:
    - _lower_matmul(block, op)

    关联文件:
    - spec: spec/pass/lowering/nn_lowering/matmul_img2col_lowering.md
    - test: test/pass/nn_lowering/matmul.py
    - 功能实现: kernel_gen/passes/lowering/nn_lowering/matmul_img2col_lowering.py
    """

    space = ensure_space_attr(op)
    result_type = ensure_single_result(op)
    ensure_operand_count(op, 2)
    lhs, rhs = op.operands
    if not isinstance(lhs.type, NnMemoryType) or not isinstance(rhs.type, NnMemoryType):
        raise NnLoweringError("nn.matmul operands must be nn.memory")
    _ensure_matmul_shape(lhs.type, rhs.type, result_type)
    _ensure_matmul_stride(lhs.type)
    _ensure_matmul_stride(rhs.type)
    _ensure_matmul_stride(result_type)
    result_shape = _normalize_shape_dims(result_type.shape.data)
    symbol_dims: list[SSAValue] = []
    if isinstance(result_shape[0], str):
        symbol_op = SymbolGetDimOp(lhs, 0)
        block.insert_op_before(symbol_op, op)
        symbol_dims.append(symbol_op.result)
    if isinstance(result_shape[1], str):
        symbol_op = SymbolGetDimOp(rhs, 1)
        block.insert_op_before(symbol_op, op)
        symbol_dims.append(symbol_op.result)
    alloc = DmaAllocOp(symbol_dims, result_type)
    block.insert_op_before(alloc, op)
    result = alloc.results[0]
    lowered = KernelMatmulOp(result, lhs, rhs, space)
    block.insert_op_before(lowered, op)
    op.results[0].replace_by(result)
    block.erase_op(op)


def _lower_img2col1d(block: Block, op: Operation) -> None:
    """lower nn.img2col1d。

    创建者: 小李飞刀
    最后一次更改: 小李飞刀

    功能说明:
    - 将 img2col1d 参数转换为 symbol.int。
    - 先创建 dma.alloc，再调用 kernel.img2col1d。

    使用示例:
    - _lower_img2col1d(block, op)

    关联文件:
    - spec: spec/pass/lowering/nn_lowering/matmul_img2col_lowering.md
    - test: test/pass/nn_lowering/img2col1d.py
    - 功能实现: kernel_gen/passes/lowering/nn_lowering/matmul_img2col_lowering.py
    """

    space = ensure_space_attr(op)
    result_type = ensure_single_result(op)
    operand, params, cleanup_ops = _ensure_img2col_params(block, op, 6, 5)
    dynamic_dims = _build_img2col1d_dynamic_dims(block, op, operand, params, result_type)
    alloc = DmaAllocOp(dynamic_dims, result_type)
    block.insert_op_before(alloc, op)
    result = alloc.results[0]
    lowered = KernelImg2col1dOp(result, operand, *params, space)
    lowered.attributes["stride"] = ArrayAttr([_build_symbol_attr(params[1], prefer_i64=False)])
    lowered.attributes["dilation"] = ArrayAttr([_build_symbol_attr(params[2], prefer_i64=False)])
    lowered.attributes["pad"] = ArrayAttr(
        [
            _build_symbol_attr(params[3], prefer_i64=False),
            _build_symbol_attr(params[4], prefer_i64=False),
        ]
    )
    block.insert_op_before(lowered, op)
    op.results[0].replace_by(result)
    block.erase_op(op)
    for cleanup_op in cleanup_ops:
        if all(result.uses.get_length() == 0 for result in cleanup_op.results):
            block.erase_op(cleanup_op)


def _lower_img2col2d(block: Block, op: Operation) -> None:
    """lower nn.img2col2d。

    创建者: 小李飞刀
    最后一次更改: 小李飞刀

    功能说明:
    - 将 img2col2d 参数转换为 symbol.int。
    - 先创建 dma.alloc，再调用 kernel.img2col2d。

    使用示例:
    - _lower_img2col2d(block, op)

    关联文件:
    - spec: spec/pass/lowering/nn_lowering/matmul_img2col_lowering.md
    - test: test/pass/nn_lowering/img2col2d.py
    - 功能实现: kernel_gen/passes/lowering/nn_lowering/matmul_img2col_lowering.py
    """

    space = ensure_space_attr(op)
    result_type = ensure_single_result(op)
    operand, params, cleanup_ops = _ensure_img2col_params(block, op, 11, 10)
    dynamic_dims = _build_img2col2d_dynamic_dims(block, op, operand, params, result_type)
    alloc = DmaAllocOp(dynamic_dims, result_type)
    block.insert_op_before(alloc, op)
    result = alloc.results[0]
    lowered = KernelImg2col2dOp(result, operand, *params, space)
    lowered.attributes["stride"] = ArrayAttr(
        [
            _build_symbol_attr(params[2], prefer_i64=True),
            _build_symbol_attr(params[3], prefer_i64=True),
        ]
    )
    lowered.attributes["dilation"] = ArrayAttr(
        [
            _build_symbol_attr(params[4], prefer_i64=True),
            _build_symbol_attr(params[5], prefer_i64=True),
        ]
    )
    lowered.attributes["pad"] = ArrayAttr(
        [
            _build_symbol_attr(params[6], prefer_i64=True),
            _build_symbol_attr(params[7], prefer_i64=True),
            _build_symbol_attr(params[8], prefer_i64=True),
            _build_symbol_attr(params[9], prefer_i64=True),
        ]
    )
    block.insert_op_before(lowered, op)
    op.results[0].replace_by(result)
    block.erase_op(op)
    for cleanup_op in cleanup_ops:
        if all(result.uses.get_length() == 0 for result in cleanup_op.results):
            block.erase_op(cleanup_op)


def lower_matmul_img2col_family(block: Block, op: Operation) -> bool:
    """处理 matmul/img2col family lowering。

    创建者: 小李飞刀
    最后一次更改: 小李飞刀

    功能说明:
    - 识别 nn.matmul / nn.img2col1d / nn.img2col2d 并执行 lowering。
    - 不匹配时返回 False。

    使用示例:
    - handled = lower_matmul_img2col_family(block, op)

    关联文件:
    - spec: spec/pass/lowering/nn_lowering/matmul_img2col_lowering.md
    - test: test/pass/nn_lowering/matmul.py
    - 功能实现: kernel_gen/passes/lowering/nn_lowering/matmul_img2col_lowering.py
    """

    if op.name == "nn.matmul":
        _lower_matmul(block, op)
        return True
    if op.name == "nn.img2col1d":
        _lower_img2col1d(block, op)
        return True
    if op.name == "nn.img2col2d":
        _lower_img2col2d(block, op)
        return True
    return False


__all__ = ["lower_matmul_img2col_family"]
