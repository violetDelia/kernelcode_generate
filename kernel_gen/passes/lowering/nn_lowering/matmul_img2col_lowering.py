"""matmul/img2col lowering 实现。


功能说明:
- 将 nn.matmul / nn.img2col1d / nn.img2col2d lower 为对应 kernel op。
- 统一在 lowering 内部创建 dma.alloc 结果 memory。
- 仅允许可证明同名的 runtime type-level 维度在 matmul contracting 轴上互相匹配。
- img2col 结果含匿名 runtime type-level 维度时使用 full-rank dynamic shape，避免公式 operand 与类型临时名误配。
- surviving 模块级接口为 `matmul_img2col_patterns()`。

API 列表:
- `matmul_img2col_patterns() -> list[RewritePattern]`

使用示例:
- from kernel_gen.passes.lowering.nn_lowering.matmul_img2col_lowering import matmul_img2col_patterns
- patterns = matmul_img2col_patterns()

关联文件:
- spec: spec/pass/lowering/nn_lowering/matmul_img2col_lowering.md
- test: test/passes/lowering/nn_lowering/test_matmul.py
- 功能实现: kernel_gen/passes/lowering/nn_lowering/matmul_img2col_lowering.py
"""

from __future__ import annotations
from kernel_gen.core.error import ErrorKind, ErrorModule, KernelCodeError

from collections.abc import Iterable

from xdsl.dialects.builtin import ArrayAttr, IntAttr, IntegerAttr, StringAttr, i64
from xdsl.ir import Attribute, Block, Operation, SSAValue
from xdsl.pattern_rewriter import PatternRewriter, RewritePattern, op_type_rewrite_pattern

from kernel_gen.dialect.dma import DmaAllocOp
from kernel_gen.dialect.kernel import KernelImg2col1dOp, KernelImg2col2dOp, KernelMatmulOp
from kernel_gen.dialect.nn import NnImg2col1dOp, NnImg2col2dOp, NnMatmulOp, NnMemoryType
from kernel_gen.dialect.symbol import (
    SymbolAddOp,
    SymbolConstOp,
    SymbolExprAttr,
    SymbolFloorDivOp,
    SymbolGetDimOp,
    SymbolMulOp,
    SymbolSubOp,
    SymbolValueType,
)
from kernel_gen.symbol_variable.symbol_dim import SymbolDim
from .nn_lowering_utility import (
    ensure_operand_count,
    ensure_single_result,
    ensure_space_attr,
)


_RUNTIME_DIM_PREFIX = "runtime_dim_"


def _coerce_symbol_expr_operand(expr: str) -> int | SymbolDim:
    """将 symbol 表达式文本转换为公开 SymbolDim 运算操作数。

    功能说明:
    - 数字文本转换为 `int`，其余文本交给公开 `SymbolDim` 语义解析。
    使用示例:
    - operand = _coerce_symbol_expr_operand("W + PL")
    """

    normalized = str(expr).strip()
    try:
        return int(normalized)
    except ValueError:
        return SymbolDim(normalized)


def _build_symbol_expr(lhs_expr: str, rhs_expr: str, op_symbol: str) -> str:
    """按公开 SymbolDim 语义构造当前文件内部使用的 symbol 表达式。

    功能说明:
    - 保留二元表达式操作数边界，避免 `A - 1` 与 `* B` 拼接后被解析成 `A - 1 * B`。
    - 该 helper 只服务本文件内部 img2col lowering，不作为跨文件公开 API。
    使用示例:
    - expr = _build_symbol_expr("W - 1", "SW", "//")
    """

    lhs = SymbolDim(_coerce_symbol_expr_operand(lhs_expr))
    rhs = _coerce_symbol_expr_operand(rhs_expr)
    if op_symbol == "+":
        value = lhs + rhs
    elif op_symbol == "-":
        value = lhs - rhs
    elif op_symbol == "*":
        value = lhs * rhs
    elif op_symbol == "/":
        value = lhs / rhs
    elif op_symbol == "//":
        value = lhs // rhs
    else:
        raise KernelCodeError(ErrorKind.CONTRACT, ErrorModule.PASS, f"unsupported symbol op: {op_symbol}")
    return str(value.get_value())


def _build_floor_div_expr(lhs_expr: str, rhs_expr: str) -> str:
    """构造当前 symbol parser 可接受的 floordiv 表达式。


    功能说明:
    - 当前 `SymbolExprAttr` 公开文本不接受裸 `/` 或 `//`。
    - img2col lowering 仍使用 `symbol.floordiv` op，结果类型表达式写成 `floordiv` 关键字形式。

    使用示例:
    - expr = _build_floor_div_expr("W - 1", "SW")

    关联文件:
    - spec: spec/pass/lowering/nn_lowering/matmul_img2col_lowering.md
    - test: test/passes/lowering/nn_lowering/test_img2col1d.py
    - 功能实现: kernel_gen/passes/lowering/nn_lowering/matmul_img2col_lowering.py
    """

    return f"({lhs_expr}) floordiv ({rhs_expr})"


def _shape_dim_expr_text(dim: Attribute) -> str:
    """读取 nn.memory shape/stride 维度表达文本。


    功能说明:
    - 公开 `NnMemoryType` 使用 `SymbolExprAttr` 表示维度，本 helper 提取其中表达式。
    - 不再兼容旧 `IntAttr` / `StringAttr` memory layout。

    使用示例:
    - expr = _shape_dim_expr_text(mem_type.shape.data[0])

    关联文件:
    - spec: spec/pass/lowering/nn_lowering/matmul_img2col_lowering.md
    - test: test/tools/test_dsl_run.py
    - 功能实现: kernel_gen/passes/lowering/nn_lowering/matmul_img2col_lowering.py
    """

    if isinstance(dim, SymbolExprAttr):
        return dim.expr.data
    raise KernelCodeError(ErrorKind.CONTRACT, ErrorModule.PASS, "matmul shape must be SymbolExprAttr")


def _shape_dim_static_int(dim: Attribute) -> int | None:
    """把静态整数维度转换为 int。


    功能说明:
    - 数字 `SymbolExprAttr` 视为静态整数。
    - 符号名、`?` 和复合表达式返回 None，交给 dynamic shape 路径处理。

    使用示例:
    - value = _shape_dim_static_int(result_type.shape.data[0])

    关联文件:
    - spec: spec/pass/lowering/nn_lowering/matmul_img2col_lowering.md
    - test: test/tools/test_dsl_run.py
    - 功能实现: kernel_gen/passes/lowering/nn_lowering/matmul_img2col_lowering.py
    """

    expr = _shape_dim_expr_text(dim)
    if expr.lstrip("-").isdigit():
        return int(expr)
    return None


def _shape_dim_is_symbolic(dim: Attribute) -> bool:
    """判断维度是否需要 dynamic shape operand。


    功能说明:
    - 非静态整数维度均按符号维度处理，包括命名符号、`?` 和复合表达式。

    使用示例:
    - if _shape_dim_is_symbolic(dim):
    -     ...

    关联文件:
    - spec: spec/pass/lowering/nn_lowering/matmul_img2col_lowering.md
    - test: test/tools/test_dsl_run.py
    - 功能实现: kernel_gen/passes/lowering/nn_lowering/matmul_img2col_lowering.py
    """

    return _shape_dim_static_int(dim) is None


def _normalize_shape_dims(shape: Iterable[Attribute]) -> list[int | str]:
    """将 shape 维度规范化为 int 或 str。


    功能说明:
    - 静态整数 `SymbolExprAttr` 转换为 int。
    - 其它符号表达转换为 str。
    - 其它类型抛出 KernelCodeError。

    使用示例:
    - dims = _normalize_shape_dims(mem_type.shape.data)

    关联文件:
    - spec: spec/pass/lowering/nn_lowering/matmul_img2col_lowering.md
    - test: test/passes/lowering/nn_lowering/test_matmul.py
    - 功能实现: kernel_gen/passes/lowering/nn_lowering/matmul_img2col_lowering.py
    """

    dims: list[int | str] = []
    for dim in shape:
        static_value = _shape_dim_static_int(dim)
        if static_value is not None:
            dims.append(static_value)
        else:
            dims.append(_shape_dim_expr_text(dim))
    return dims


def _is_runtime_dim(value: int | str) -> bool:
    """判断维度文本是否为当前 DSL 生成的匿名 runtime type-level 维度。


    功能说明:
    - 仅识别 `MemoryAST.type_from_memory` 为匿名 `?` 维度生成的 `runtime_dim_*` 形态。
    - 该 helper 只服务本文件内部 matmul shape 校验，不作为跨文件公开 API。

    使用示例:
    - if _is_runtime_dim("runtime_dim_0"):
    -     ...

    关联文件:
    - spec: spec/pass/lowering/nn_lowering/matmul_img2col_lowering.md
    - test: test/passes/lowering/nn_lowering/test_matmul.py
    - 功能实现: kernel_gen/passes/lowering/nn_lowering/matmul_img2col_lowering.py
    """

    return isinstance(value, str) and value.startswith(_RUNTIME_DIM_PREFIX)


def _matmul_contract_dims_match(lhs_dim: int | str, rhs_dim: int | str) -> bool:
    """校验 matmul contracting 维度是否兼容。


    功能说明:
    - 静态维度、命名符号与 runtime type-level 维度都要求精确相等。
    - 不把任意两个 `runtime_dim_*` 互相匹配，避免 lowering 放行 verifier 无法证明的 contracting 维度。

    使用示例:
    - if not _matmul_contract_dims_match(lhs_shape[1], rhs_shape[0]):
    -     raise KernelCodeError(...)

    关联文件:
    - spec: spec/pass/lowering/nn_lowering/matmul_img2col_lowering.md
    - test: test/passes/lowering/nn_lowering/test_matmul.py
    - 功能实现: kernel_gen/passes/lowering/nn_lowering/matmul_img2col_lowering.py
    """

    if lhs_dim == rhs_dim:
        return True
    if _is_runtime_dim(lhs_dim) or _is_runtime_dim(rhs_dim):
        return False
    return False


def _uses_runtime_dim_shape(mem_type: NnMemoryType) -> bool:
    """判断 memory 类型 shape 是否包含匿名 runtime type-level 维度。


    功能说明:
    - 仅识别 DSL 为匿名 `?` 维度生成的 `runtime_dim_*` shape。
    - 该 helper 只服务本文件内部 alloc dynamic shape 选择。

    使用示例:
    - if _uses_runtime_dim_shape(result_type):
    -     ...

    关联文件:
    - spec: spec/pass/lowering/nn_lowering/matmul_img2col_lowering.md
    - test: test/passes/lowering/nn_lowering/test_img2col2d.py
    - 功能实现: kernel_gen/passes/lowering/nn_lowering/matmul_img2col_lowering.py
    """

    return any(_is_runtime_dim(dim) for dim in _normalize_shape_dims(mem_type.shape.data))


def _result_static_symbol(block: Block, op: Operation, result_type: NnMemoryType, axis: int) -> SSAValue:
    """为结果静态 shape 维度构造 symbol 常量 operand。


    功能说明:
    - full-rank dynamic shape 需要每个轴都有 SSA operand；静态轴用 `symbol.const` 表达。
    - 非静态轴调用该 helper 会稳定失败，避免隐藏 shape 生成错误。

    使用示例:
    - static_dim = _result_static_symbol(block, op, result_type, 2)

    关联文件:
    - spec: spec/pass/lowering/nn_lowering/matmul_img2col_lowering.md
    - test: test/passes/lowering/nn_lowering/test_img2col2d.py
    - 功能实现: kernel_gen/passes/lowering/nn_lowering/matmul_img2col_lowering.py
    """

    dim_value = _shape_dim_static_int(result_type.shape.data[axis])
    if dim_value is not None:
        const = SymbolConstOp(dim_value)
        block.insert_op_before(const, op)
        return const.result
    raise KernelCodeError(ErrorKind.CONTRACT, ErrorModule.PASS, "nn img2col static result dim must be integer")


def _ensure_matmul_shape(
    lhs_type: NnMemoryType,
    rhs_type: NnMemoryType,
    out_type: NnMemoryType,
) -> None:
    """校验 nn.matmul 的 shape 合同。


    功能说明:
    - 确认 lhs/rhs/out 均为 rank-2。
    - 校验 `[M, K] x [K, N] -> [M, N]` 规则。
    - contracting 轴仅允许双侧维度文本完全一致；runtime type-level 维度也必须同名。

    使用示例:
    - _ensure_matmul_shape(lhs_type, rhs_type, out_type)

    关联文件:
    - spec: spec/pass/lowering/nn_lowering/matmul_img2col_lowering.md
    - test: test/passes/lowering/nn_lowering/test_matmul.py
    - 功能实现: kernel_gen/passes/lowering/nn_lowering/matmul_img2col_lowering.py
    """

    lhs_shape = _normalize_shape_dims(lhs_type.shape.data)
    rhs_shape = _normalize_shape_dims(rhs_type.shape.data)
    out_shape = _normalize_shape_dims(out_type.shape.data)
    if len(lhs_shape) != 2 or len(rhs_shape) != 2 or len(out_shape) != 2:
        raise KernelCodeError(ErrorKind.CONTRACT, ErrorModule.PASS, "matmul requires rank-2 memory types")
    if not _matmul_contract_dims_match(lhs_shape[1], rhs_shape[0]):
        raise KernelCodeError(ErrorKind.CONTRACT, ErrorModule.PASS, "matmul contracting dimensions must match")
    if out_shape[0] != lhs_shape[0] or out_shape[1] != rhs_shape[1]:
        raise KernelCodeError(ErrorKind.CONTRACT, ErrorModule.PASS, "matmul output shape must match operands")


def _ensure_matmul_stride(mem_type: NnMemoryType) -> None:
    """校验 nn.matmul 的 stride 连续性。


    功能说明:
    - 当 shape/stride 可静态求值时，要求 stride 为连续布局。

    使用示例:
    - _ensure_matmul_stride(out_type)

    关联文件:
    - spec: spec/pass/lowering/nn_lowering/matmul_img2col_lowering.md
    - test: test/passes/lowering/nn_lowering/test_matmul.py
    - 功能实现: kernel_gen/passes/lowering/nn_lowering/matmul_img2col_lowering.py
    """

    shape = mem_type.shape.data
    stride = mem_type.stride.data
    if len(shape) != 2 or len(stride) != 2:
        raise KernelCodeError(ErrorKind.CONTRACT, ErrorModule.PASS, "matmul stride must be contiguous")
    shape_values = [_shape_dim_static_int(dim) for dim in shape]
    stride_values = [_shape_dim_static_int(dim) for dim in stride]
    if any(value is None for value in shape_values):
        return
    if any(value is None for value in stride_values):
        return
    expected_stride0 = shape_values[1]
    expected_stride1 = 1
    if stride_values[0] != expected_stride0 or stride_values[1] != expected_stride1:
        raise KernelCodeError(ErrorKind.CONTRACT, ErrorModule.PASS, "matmul stride must be contiguous")


def _ensure_symbol_int(
    block: Block,
    op: Operation,
    operand: SSAValue | Operation,
) -> tuple[SSAValue, SymbolConstOp | None]:
    """确保 img2col 参数为 symbol.int。


    功能说明:
    - 若 operand 为 symbol.const，则克隆为新的 symbol.const 并返回。
    - 若 operand 为 symbol.int（非 symbol.const）直接返回。
    - 其余类型统一抛出 KernelCodeError。

    使用示例:
    - kw, _ = _ensure_symbol_int(block, op, op.operands[1])

    关联文件:
    - spec: spec/pass/lowering/nn_lowering/matmul_img2col_lowering.md
    - test: test/passes/lowering/nn_lowering/test_img2col1d.py
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
        raise KernelCodeError(ErrorKind.CONTRACT, ErrorModule.PASS, "nn img2col parameters must be symbol.int")
    raise KernelCodeError(ErrorKind.CONTRACT, ErrorModule.PASS, "nn img2col parameters must be symbol.int")


def _ensure_img2col_params(
    block: Block,
    op: Operation,
    operand_count: int,
    dynamic_count: int,
) -> tuple[SSAValue, list[SSAValue], list[SymbolConstOp]]:
    """校验并提取 img2col 参数。


    功能说明:
    - 校验参数数量，并提取 dynamic 参数列表。

    使用示例:
    - operand, params, cleanup = _ensure_img2col_params(block, op, 6, 5)

    关联文件:
    - spec: spec/pass/lowering/nn_lowering/matmul_img2col_lowering.md
    - test: test/passes/lowering/nn_lowering/test_img2col1d.py
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


    功能说明:
    - 将 `!symbol.int<"...">` 的表达式文本提取为字符串。
    - 非 `symbol.int` 时抛出 `KernelCodeError`。

    使用示例:
    - expr = _symbol_expr(symbol_value)

    关联文件:
    - spec: spec/pass/lowering/nn_lowering/matmul_img2col_lowering.md
    - test: test/passes/lowering/nn_lowering/test_img2col1d.py
    - 功能实现: kernel_gen/passes/lowering/nn_lowering/matmul_img2col_lowering.py
    """

    if not isinstance(value.type, SymbolValueType):
        raise KernelCodeError(ErrorKind.CONTRACT, ErrorModule.PASS, "symbol expression must be symbol.int")
    return value.type.expr.expr.data


def _build_symbol_attr(value: SSAValue, *, prefer_i64: bool) -> Attribute:
    """将 symbol.int SSAValue 转为适配的 attribute。


    功能说明:
    - 数值表达式转为 IntAttr / IntegerAttr。
    - 其余表达式转为 StringAttr。

    使用示例:
    - attr = _build_symbol_attr(sw, prefer_i64=False)

    关联文件:
    - spec: spec/pass/lowering/nn_lowering/matmul_img2col_lowering.md
    - test: test/passes/lowering/nn_lowering/test_img2col2d.py
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


    功能说明:
    - 仅当指定轴为符号维度时，插入一次 `symbol.get_dim`。
    - 使用缓存避免同一轴重复生成 `symbol.get_dim`。

    使用示例:
    - width = _get_symbol_dim_by_axis(block, op, operand, 2, cache)

    关联文件:
    - spec: spec/pass/lowering/nn_lowering/matmul_img2col_lowering.md
    - test: test/passes/lowering/nn_lowering/test_img2col1d.py
    - 功能实现: kernel_gen/passes/lowering/nn_lowering/matmul_img2col_lowering.py
    """

    if not isinstance(operand.type, NnMemoryType):
        raise KernelCodeError(ErrorKind.CONTRACT, ErrorModule.PASS, "nn img2col operand must be nn.memory")
    cached = cache.get(axis)
    if cached is not None:
        return cached
    dims = list(operand.type.shape.data)
    if axis < 0 or axis >= len(dims):
        raise KernelCodeError(ErrorKind.CONTRACT, ErrorModule.PASS, "nn img2col operand axis out of range")
    dim = dims[axis]
    if not _shape_dim_is_symbolic(dim):
        raise KernelCodeError(ErrorKind.CONTRACT, ErrorModule.PASS, "nn img2col symbolic dim must come from symbolic source axis")
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


    功能说明:
    - 当输出包含符号维度时，生成 `symbol.get_dim` 与 `symbol` 算术链。
    - 返回 `dma.alloc` 所需的 dynamic shape operand 列表。

    使用示例:
    - dynamic_dims = _build_img2col1d_dynamic_dims(block, op, operand, params, result_type)

    关联文件:
    - spec: spec/pass/lowering/nn_lowering/matmul_img2col_lowering.md
    - test: test/passes/lowering/nn_lowering/test_img2col1d.py
    - 功能实现: kernel_gen/passes/lowering/nn_lowering/matmul_img2col_lowering.py
    """

    if not any(_shape_dim_is_symbolic(dim) for dim in result_type.shape.data):
        return []
    if len(result_type.shape.data) != 4:
        raise KernelCodeError(ErrorKind.CONTRACT, ErrorModule.PASS, "nn img2col1d result rank must be 4")
    one = SymbolConstOp(1)
    block.insert_op_before(one, op)
    source_dims: dict[int, SSAValue] = {}
    for axis in range(3):
        if _shape_dim_is_symbolic(operand.type.shape.data[axis]):
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

    w_div_expr = _build_floor_div_expr(w_minus_one_expr, sw_expr)
    w_div = SymbolFloorDivOp(w_minus_one, sw, SymbolValueType.from_expr(w_div_expr))
    block.insert_op_before(w_div, op)

    w_out_expr = f"{w_div_expr} + {one_expr}"
    w_out = SymbolAddOp(w_div, one, SymbolValueType.from_expr(w_out_expr))
    block.insert_op_before(w_out, op)

    full_rank_dims: list[SSAValue] = [
        _get_symbol_dim_by_axis(block, op, operand, 0, source_dims)
        if _shape_dim_is_symbolic(result_type.shape.data[0])
        else _result_static_symbol(block, op, result_type, 0),
        _get_symbol_dim_by_axis(block, op, operand, 1, source_dims)
        if _shape_dim_is_symbolic(result_type.shape.data[1])
        else _result_static_symbol(block, op, result_type, 1),
        kw,
        w_out.result,
    ]
    if _uses_runtime_dim_shape(result_type):
        return full_rank_dims
    dynamic_dims: list[SSAValue] = []
    for axis, dim in enumerate(result_type.shape.data):
        if _shape_dim_is_symbolic(dim):
            if axis < len(full_rank_dims):
                dynamic_dims.append(full_rank_dims[axis])
            else:
                raise KernelCodeError(ErrorKind.CONTRACT, ErrorModule.PASS, "nn img2col1d result rank must be 4")
    return dynamic_dims


def _build_img2col2d_dynamic_dims(
    block: Block,
    op: Operation,
    operand: SSAValue,
    params: list[SSAValue],
    result_type: NnMemoryType,
) -> list[SSAValue]:
    """构造 img2col2d 的 dynamic shape operand 列表。


    功能说明:
    - 当输出包含符号维度时，生成 `symbol.get_dim` 与 `symbol` 算术链。
    - 返回 `dma.alloc` 所需的 dynamic shape operand 列表。

    使用示例:
    - dynamic_dims = _build_img2col2d_dynamic_dims(block, op, operand, params, result_type)

    关联文件:
    - spec: spec/pass/lowering/nn_lowering/matmul_img2col_lowering.md
    - test: test/passes/lowering/nn_lowering/test_img2col2d.py
    - 功能实现: kernel_gen/passes/lowering/nn_lowering/matmul_img2col_lowering.py
    """

    if not any(_shape_dim_is_symbolic(dim) for dim in result_type.shape.data):
        return []
    if len(result_type.shape.data) != 6:
        raise KernelCodeError(ErrorKind.CONTRACT, ErrorModule.PASS, "nn img2col2d result rank must be 6")
    one = SymbolConstOp(1)
    block.insert_op_before(one, op)
    source_dims: dict[int, SSAValue] = {}
    for axis in range(4):
        if _shape_dim_is_symbolic(operand.type.shape.data[axis]):
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
    h_div_expr = _build_floor_div_expr(h_minus_one_expr, sh_expr)
    h_div = SymbolFloorDivOp(h_minus_one, sh, SymbolValueType.from_expr(h_div_expr))
    block.insert_op_before(h_div, op)
    h_out_expr = f"{h_div_expr} + {one_expr}"
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
    w_div_expr = _build_floor_div_expr(w_minus_one_expr, sw_expr)
    w_div = SymbolFloorDivOp(w_minus_one, sw, SymbolValueType.from_expr(w_div_expr))
    block.insert_op_before(w_div, op)
    w_out_expr = f"{w_div_expr} + {one_expr}"
    w_out = SymbolAddOp(w_div, one, SymbolValueType.from_expr(w_out_expr))
    block.insert_op_before(w_out, op)

    full_rank_dims: list[SSAValue] = [
        _get_symbol_dim_by_axis(block, op, operand, 0, source_dims)
        if _shape_dim_is_symbolic(result_type.shape.data[0])
        else _result_static_symbol(block, op, result_type, 0),
        _get_symbol_dim_by_axis(block, op, operand, 1, source_dims)
        if _shape_dim_is_symbolic(result_type.shape.data[1])
        else _result_static_symbol(block, op, result_type, 1),
        kh,
        kw,
        h_out.result,
        w_out.result,
    ]
    if _uses_runtime_dim_shape(result_type):
        return full_rank_dims
    dynamic_dims: list[SSAValue] = []
    for axis, dim in enumerate(result_type.shape.data):
        if _shape_dim_is_symbolic(dim):
            if axis < len(full_rank_dims):
                dynamic_dims.append(full_rank_dims[axis])
            else:
                raise KernelCodeError(ErrorKind.CONTRACT, ErrorModule.PASS, "nn img2col2d result rank must be 6")
    return dynamic_dims


def _lower_matmul(block: Block, op: Operation) -> None:
    """lower nn.matmul。


    功能说明:
    - 校验 shape 与 stride。
    - 当 result shape 含符号维度时，插入 symbol.get_dim 作为 dma.alloc dynamic shape。
    - 先创建 dma.alloc，再调用 kernel.matmul。

    使用示例:
    - _lower_matmul(block, op)

    关联文件:
    - spec: spec/pass/lowering/nn_lowering/matmul_img2col_lowering.md
    - test: test/passes/lowering/nn_lowering/test_matmul.py
    - 功能实现: kernel_gen/passes/lowering/nn_lowering/matmul_img2col_lowering.py
    """

    space = ensure_space_attr(op)
    result_type = ensure_single_result(op)
    ensure_operand_count(op, 2)
    lhs, rhs = op.operands
    if not isinstance(lhs.type, NnMemoryType) or not isinstance(rhs.type, NnMemoryType):
        raise KernelCodeError(ErrorKind.CONTRACT, ErrorModule.PASS, "nn.matmul operands must be nn.memory")
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
    op.results[0].replace_all_uses_with(result)
    block.erase_op(op)


def _lower_img2col1d(block: Block, op: Operation) -> None:
    """lower nn.img2col1d。


    功能说明:
    - 将 img2col1d 参数转换为 symbol.int。
    - 先创建 dma.alloc，再调用 kernel.img2col1d。

    使用示例:
    - _lower_img2col1d(block, op)

    关联文件:
    - spec: spec/pass/lowering/nn_lowering/matmul_img2col_lowering.md
    - test: test/passes/lowering/nn_lowering/test_img2col1d.py
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
    op.results[0].replace_all_uses_with(result)
    block.erase_op(op)
    for cleanup_op in cleanup_ops:
        if all(result.uses.get_length() == 0 for result in cleanup_op.results):
            block.erase_op(cleanup_op)


def _lower_img2col2d(block: Block, op: Operation) -> None:
    """lower nn.img2col2d。


    功能说明:
    - 将 img2col2d 参数转换为 symbol.int。
    - 先创建 dma.alloc，再调用 kernel.img2col2d。

    使用示例:
    - _lower_img2col2d(block, op)

    关联文件:
    - spec: spec/pass/lowering/nn_lowering/matmul_img2col_lowering.md
    - test: test/passes/lowering/nn_lowering/test_img2col2d.py
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
    op.results[0].replace_all_uses_with(result)
    block.erase_op(op)
    for cleanup_op in cleanup_ops:
        if all(result.uses.get_length() == 0 for result in cleanup_op.results):
            block.erase_op(cleanup_op)
class _LowerNnMatmulPattern(RewritePattern):
    """将单个 nn.matmul lowering 为 kernel.matmul。


    功能说明:
    - 只匹配 NnMatmulOp，避免 family 级 op.name 分派。
    - 复用现有 matmul helper，保持 IR 输出与校验语义不变。

    使用示例:
    - pattern = _LowerNnMatmulPattern()

    关联文件:
    - spec: spec/pass/lowering/nn_lowering/matmul_img2col_lowering.md
    - test: test/passes/lowering/nn_lowering/test_public_name.py
    - 功能实现: kernel_gen/passes/lowering/nn_lowering/matmul_img2col_lowering.py
    """

    @op_type_rewrite_pattern
    def match_and_rewrite(self, op: NnMatmulOp, rewriter: PatternRewriter) -> None:
        block = op.parent_block()
        if block is None:
            raise KernelCodeError(ErrorKind.CONTRACT, ErrorModule.PASS, "nn op must be inside a block")
        _lower_matmul(block, op)
        rewriter.has_done_action = True


class _LowerNnImg2col1dPattern(RewritePattern):
    """将单个 nn.img2col1d lowering 为 kernel.img2col1d。


    功能说明:
    - 只匹配 NnImg2col1dOp，避免 family 级 op.name 分派。
    - 复用现有 img2col1d helper，保持 IR 输出与校验语义不变。

    使用示例:
    - pattern = _LowerNnImg2col1dPattern()

    关联文件:
    - spec: spec/pass/lowering/nn_lowering/matmul_img2col_lowering.md
    - test: test/passes/lowering/nn_lowering/test_img2col1d.py
    - 功能实现: kernel_gen/passes/lowering/nn_lowering/matmul_img2col_lowering.py
    """

    @op_type_rewrite_pattern
    def match_and_rewrite(self, op: NnImg2col1dOp, rewriter: PatternRewriter) -> None:
        block = op.parent_block()
        if block is None:
            raise KernelCodeError(ErrorKind.CONTRACT, ErrorModule.PASS, "nn op must be inside a block")
        _lower_img2col1d(block, op)
        rewriter.has_done_action = True


class _LowerNnImg2col2dPattern(RewritePattern):
    """将单个 nn.img2col2d lowering 为 kernel.img2col2d。


    功能说明:
    - 只匹配 NnImg2col2dOp，避免 family 级 op.name 分派。
    - 复用现有 img2col2d helper，保持 IR 输出与校验语义不变。

    使用示例:
    - pattern = _LowerNnImg2col2dPattern()

    关联文件:
    - spec: spec/pass/lowering/nn_lowering/matmul_img2col_lowering.md
    - test: test/passes/lowering/nn_lowering/test_img2col2d.py
    - 功能实现: kernel_gen/passes/lowering/nn_lowering/matmul_img2col_lowering.py
    """

    @op_type_rewrite_pattern
    def match_and_rewrite(self, op: NnImg2col2dOp, rewriter: PatternRewriter) -> None:
        block = op.parent_block()
        if block is None:
            raise KernelCodeError(ErrorKind.CONTRACT, ErrorModule.PASS, "nn op must be inside a block")
        _lower_img2col2d(block, op)
        rewriter.has_done_action = True


def matmul_img2col_patterns() -> list[RewritePattern]:
    """返回 matmul/img2col rewrite pattern 集合。


    功能说明:
    - 提供 nn_lowering 主 driver 的单 op pattern 注册入口。
    - 每个 pattern 只匹配一个具体 nn op，不再保留 family pattern 名称分派。

    使用示例:
    - patterns = matmul_img2col_patterns()

    关联文件:
    - spec: spec/pass/lowering/nn_lowering/matmul_img2col_lowering.md
    - test: test/passes/lowering/nn_lowering/test_public_name.py
    - 功能实现: kernel_gen/passes/lowering/nn_lowering/matmul_img2col_lowering.py
    """

    return [_LowerNnMatmulPattern(), _LowerNnImg2col1dPattern(), _LowerNnImg2col2dPattern()]


__all__ = ["matmul_img2col_patterns"]
