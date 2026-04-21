"""tile-reduce pass.

创建者: 金铲铲大作战
最后一次更改: 金铲铲大作战

功能说明:
- 提供 `tile-reduce` 的公开 `ModulePass` 入口。
- 只消费 `tile.analysis + tile.tile_exprs`，并仅收口 matmul reduction 轴。
- 不生成 `tile.step_value` / `kernel_split.tile_value`，与 expectation/pass/tile/reduce 的黑盒口径一致。

使用示例:
- from xdsl.context import Context
- from xdsl.dialects.builtin import ModuleOp
- from kernel_gen.passes.lowering.tile_reduce import TileReducePass
- TileReducePass().apply(Context(), ModuleOp([]))

关联文件:
- spec: [spec/pass/lowering/tile_reduce.md](spec/pass/lowering/tile_reduce.md)
- test: [test/pass/test_lowering_tile_reduce.py](test/pass/test_lowering_tile_reduce.py)
- 功能实现: [kernel_gen/passes/lowering/tile_reduce.py](kernel_gen/passes/lowering/tile_reduce.py)
"""

from __future__ import annotations

from xdsl.context import Context
from xdsl.dialects import func
from xdsl.dialects.builtin import ArrayAttr, IntAttr, ModuleOp, StringAttr, UnregisteredOp
from xdsl.ir import Attribute, Block, Operation, SSAValue
from xdsl.irdl import IRDLOperation, irdl_op_definition, result_def
from xdsl.passes import ModulePass
from xdsl.pattern_rewriter import (
    GreedyRewritePatternApplier,
    PatternRewriter,
    PatternRewriteWalker,
    RewritePattern,
    op_type_rewrite_pattern,
)
from xdsl.utils.exceptions import VerifyException

from kernel_gen.dialect.dma import DmaViewOp
from kernel_gen.dialect.kernel import KernelBinaryElewiseOp
from kernel_gen.dialect.nn import NnMemorySpaceAttr, NnMemoryType
from kernel_gen.dialect.symbol import SymbolGetDimOp, SymbolIterType, SymbolValueType
from kernel_gen.passes.lowering import tile as tile_module


class TileReduceError(ValueError):
    """tile-reduce pass 的显式错误。

    创建者: 金铲铲大作战
    最后一次更改: 金铲铲大作战

    功能说明:
    - 统一承载 `TileReduce*` 关键短语错误，便于测试与上层稳定匹配。

    使用示例:
    - raise TileReduceError("TileReduceRequiresLoweredKernelIR: missing tile.analysis")

    关联文件:
    - spec: [spec/pass/lowering/tile_reduce.md](spec/pass/lowering/tile_reduce.md)
    - test: [test/pass/test_lowering_tile_reduce.py](test/pass/test_lowering_tile_reduce.py)
    - 功能实现: [kernel_gen/passes/lowering/tile_reduce.py](kernel_gen/passes/lowering/tile_reduce.py)
    """


def _raise_tile_reduce_error(keyword: str, detail: str) -> None:
    """抛出统一格式的 tile-reduce 错误。

    创建者: 金铲铲大作战
    最后一次更改: 金铲铲大作战

    功能说明:
    - 统一拼接 `TileReduce*` 前缀，避免不同路径返回不一致短语。

    使用示例:
    - _raise_tile_reduce_error("TileReduceRequiresLoweredKernelIR", "missing tile.analysis")

    关联文件:
    - spec: [spec/pass/lowering/tile_reduce.md](spec/pass/lowering/tile_reduce.md)
    - test: [test/pass/test_lowering_tile_reduce.py](test/pass/test_lowering_tile_reduce.py)
    - 功能实现: [kernel_gen/passes/lowering/tile_reduce.py](kernel_gen/passes/lowering/tile_reduce.py)
    """

    raise TileReduceError(f"{keyword}: {detail}")


@irdl_op_definition
class _TileReduceTunerParamOp(IRDLOperation):
    """tile-reduce 内部使用的 `tuner.param` bridge。

    创建者: 金铲铲大作战
    最后一次更改: 金铲铲大作战

    功能说明:
    - 生成 `tuner.param : !symbol.int<"...">` 形式的局部 tile step。
    - 仅作为 tile-reduce 内部 bridge，不对外暴露为公开 dialect API。

    使用示例:
    - param = _TileReduceTunerParamOp("TILE_R0")

    关联文件:
    - spec: [spec/pass/lowering/tile_reduce.md](spec/pass/lowering/tile_reduce.md)
    - test: [test/pass/test_lowering_tile_reduce.py](test/pass/test_lowering_tile_reduce.py)
    - 功能实现: [kernel_gen/passes/lowering/tile_reduce.py](kernel_gen/passes/lowering/tile_reduce.py)
    """

    name = "tuner.param"

    result = result_def(SymbolValueType)

    def __init__(self: "_TileReduceTunerParamOp", tile_name: str) -> None:
        """构造 tile-reduce 内部 `tuner.param`。

        创建者: 金铲铲大作战
        最后一次更改: 金铲铲大作战

        功能说明:
        - 使用 `!symbol.int<"tile_name">` 作为结果类型。

        使用示例:
        - param = _TileReduceTunerParamOp("TILE_R0")

        关联文件:
        - spec: [spec/pass/lowering/tile_reduce.md](spec/pass/lowering/tile_reduce.md)
        - test: [test/pass/test_lowering_tile_reduce.py](test/pass/test_lowering_tile_reduce.py)
        - 功能实现: [kernel_gen/passes/lowering/tile_reduce.py](kernel_gen/passes/lowering/tile_reduce.py)
        """

        super().__init__(result_types=[SymbolValueType.from_expr(tile_name)])

    def verify_(self: "_TileReduceTunerParamOp") -> None:
        """校验 tile-reduce 内部 `tuner.param`。

        创建者: 金铲铲大作战
        最后一次更改: 金铲铲大作战

        功能说明:
        - 结果必须为 `!symbol.int<"...">`。

        使用示例:
        - _TileReduceTunerParamOp("TILE_R0").verify_()

        关联文件:
        - spec: [spec/pass/lowering/tile_reduce.md](spec/pass/lowering/tile_reduce.md)
        - test: [test/pass/test_lowering_tile_reduce.py](test/pass/test_lowering_tile_reduce.py)
        - 功能实现: [kernel_gen/passes/lowering/tile_reduce.py](kernel_gen/passes/lowering/tile_reduce.py)
        """

        if not isinstance(self.result.type, SymbolValueType):
            raise VerifyException("tuner.param result must be !symbol.int")

    def print(self: "_TileReduceTunerParamOp", printer) -> None:
        """打印 tile-reduce 内部 `tuner.param`。

        创建者: 金铲铲大作战
        最后一次更改: 金铲铲大作战

        功能说明:
        - 输出 `tuner.param : !symbol.int<"...">` 的黑盒口径。

        使用示例:
        - _TileReduceTunerParamOp("TILE_R0").print(printer)

        关联文件:
        - spec: [spec/pass/lowering/tile_reduce.md](spec/pass/lowering/tile_reduce.md)
        - test: [test/pass/test_lowering_tile_reduce.py](test/pass/test_lowering_tile_reduce.py)
        - 功能实现: [kernel_gen/passes/lowering/tile_reduce.py](kernel_gen/passes/lowering/tile_reduce.py)
        """

        printer.print_string(" : ")
        printer.print_attribute(self.result.type)


def _parse_tile_exprs(op: Operation) -> list[list[str]]:
    """解析 tile.tile_exprs 角色矩阵。

    创建者: 金铲铲大作战
    最后一次更改: 金铲铲大作战

    功能说明:
    - 将 `ArrayAttr(ArrayAttr(StringAttr))` 解析为二维字符串列表。
    - 只允许空字符串作为 tile-reduce 的输入占位。

    使用示例:
    - exprs = _parse_tile_exprs(matmul_op)

    关联文件:
    - spec: [spec/pass/lowering/tile_reduce.md](spec/pass/lowering/tile_reduce.md)
    - test: [test/pass/test_lowering_tile_reduce.py](test/pass/test_lowering_tile_reduce.py)
    - 功能实现: [kernel_gen/passes/lowering/tile_reduce.py](kernel_gen/passes/lowering/tile_reduce.py)
    """

    attr = op.attributes.get("tile.tile_exprs")
    if not isinstance(attr, ArrayAttr):
        _raise_tile_reduce_error("TileReduceRequiresLoweredKernelIR", "kernel.matmul must carry tile.tile_exprs")
    rows: list[list[str]] = []
    for row in attr.data:
        if not isinstance(row, ArrayAttr):
            _raise_tile_reduce_error("TileReduceRequiresLoweredKernelIR", "tile.tile_exprs must be a 2d array")
        row_exprs: list[str] = []
        for item in row.data:
            if not isinstance(item, StringAttr):
                _raise_tile_reduce_error("TileReduceRequiresLoweredKernelIR", "tile.tile_exprs entries must be string")
            row_exprs.append(item.data)
        rows.append(row_exprs)
    return rows


def _tile_exprs_attr(roles: list[list[str]], tile_name: str) -> ArrayAttr:
    """构造 tile-reduce 的 tile.tile_exprs 属性。

    创建者: 金铲铲大作战
    最后一次更改: 金铲铲大作战

    功能说明:
    - 将 reduce 角色位置替换为当前 tile 名称，其余位置保持空串。

    使用示例:
    - exprs = _tile_exprs_attr([["elewise", "reduce"]], "TILE_R0")

    关联文件:
    - spec: [spec/pass/lowering/tile_reduce.md](spec/pass/lowering/tile_reduce.md)
    - test: [test/pass/test_lowering_tile_reduce.py](test/pass/test_lowering_tile_reduce.py)
    - 功能实现: [kernel_gen/passes/lowering/tile_reduce.py](kernel_gen/passes/lowering/tile_reduce.py)
    """

    return ArrayAttr(
        [
            ArrayAttr([StringAttr(tile_name if role == "reduce" else "") for role in row])
            for row in roles
        ]
    )


def _build_unit_stride_view_type(source_type: NnMemoryType, shape_values: list[SSAValue]) -> NnMemoryType:
    """构造 tile-reduce 使用的 unit-stride `dma.view` 结果类型。

    创建者: 金铲铲大作战
    最后一次更改: 金铲铲大作战

    功能说明:
    - shape 由 `shape_values` 的 symbol 表达式构造。
    - stride 固定为全 `1`，与 tile-reduce expectation 对齐。

    使用示例:
    - view_type = _build_unit_stride_view_type(src_type, [m_dim, n_dim])

    关联文件:
    - spec: [spec/pass/lowering/tile_reduce.md](spec/pass/lowering/tile_reduce.md)
    - test: [test/pass/test_lowering_tile_reduce.py](test/pass/test_lowering_tile_reduce.py)
    - 功能实现: [kernel_gen/passes/lowering/tile_reduce.py](kernel_gen/passes/lowering/tile_reduce.py)
    """

    if not isinstance(source_type, NnMemoryType):
        _raise_tile_reduce_error("TileReduceRequiresLoweredKernelIR", "dma.view source must be nn.memory")
    shape_attrs = ArrayAttr(
        [tile_module._expr_to_dim_attr(tile_module._symbol_expr_from_value(value)) for value in shape_values]
    )
    stride_attrs = ArrayAttr([IntAttr(1) for _ in shape_values])
    return NnMemoryType(shape_attrs, stride_attrs, source_type.element_type, source_type.space)


def _build_unit_stride_view(
    source: SSAValue,
    *,
    offsets: list[SSAValue],
    shape_values: list[SSAValue],
    stride_values: list[SSAValue],
) -> DmaViewOp:
    """构造 tile-reduce 使用的 `dma.view`。

    创建者: 金铲铲大作战
    最后一次更改: 金铲铲大作战

    功能说明:
    - 视图 stride 统一使用 `1`。
    - 通过 source 结果类型推导 view 的 nn.memory 类型。

    使用示例:
    - view = _build_unit_stride_view(out, offsets=[zero0, zero1], shape_values=[d0, d1], stride_values=[one0, one1])

    关联文件:
    - spec: [spec/pass/lowering/tile_reduce.md](spec/pass/lowering/tile_reduce.md)
    - test: [test/pass/test_lowering_tile_reduce.py](test/pass/test_lowering_tile_reduce.py)
    - 功能实现: [kernel_gen/passes/lowering/tile_reduce.py](kernel_gen/passes/lowering/tile_reduce.py)
    """

    if not isinstance(source.type, NnMemoryType):
        _raise_tile_reduce_error("TileReduceRequiresLoweredKernelIR", "dma.view source must be nn.memory")
    result_type = _build_unit_stride_view_type(source.type, shape_values)
    return DmaViewOp(source, offsets, shape_values, stride_values, result_type)


def _build_reduce_expr_rows(roles: list[list[str]], tile_name: str) -> list[list[str]]:
    """根据 tile.analysis 生成 tile.tile_exprs 行列矩阵。

    创建者: 金铲铲大作战
    最后一次更改: 金铲铲大作战

    功能说明:
    - 仅在 reduce 角色位置写入当前 tile 名称。
    - 其余位置保持空字符串，满足 after IR 的公开合同。

    使用示例:
    - expr_rows = _build_reduce_expr_rows(roles, "TILE_R0")

    关联文件:
    - spec: [spec/pass/lowering/tile_reduce.md](spec/pass/lowering/tile_reduce.md)
    - test: [test/pass/test_lowering_tile_reduce.py](test/pass/test_lowering_tile_reduce.py)
    - 功能实现: [kernel_gen/passes/lowering/tile_reduce.py](kernel_gen/passes/lowering/tile_reduce.py)
    """

    return [[tile_name if role == "reduce" else "" for role in row] for row in roles]


def _lower_matmul_op(
    block: Block,
    op: Operation,
    *,
    reduce_tile_name: str,
) -> list[Operation]:
    """按 tile-reduce 合同改写单个 `kernel.matmul`。

    创建者: 金铲铲大作战
    最后一次更改: 金铲铲大作战

    功能说明:
    - 只切 reduce 轴，保留 elewise 轴不变。
    - 生成 `tuner.param + symbol.for + dma.view + dma.fill` 的收口结构。
    - 原 `kernel.matmul` 保留在 loop body 中，并把 `tile.tile_exprs` 更新为 reduce 名称。

    使用示例:
    - _lower_matmul_op(block, matmul_op, reduce_tile_name="TILE_R0")

    关联文件:
    - spec: [spec/pass/lowering/tile_reduce.md](spec/pass/lowering/tile_reduce.md)
    - test: [test/pass/test_lowering_tile_reduce.py](test/pass/test_lowering_tile_reduce.py)
    - 功能实现: [kernel_gen/passes/lowering/tile_reduce.py](kernel_gen/passes/lowering/tile_reduce.py)
    """

    out = SSAValue.get(op.operands[0])
    lhs = SSAValue.get(op.operands[1])
    rhs = SSAValue.get(op.operands[2])
    if not (
        isinstance(out.type, NnMemoryType)
        and isinstance(lhs.type, NnMemoryType)
        and isinstance(rhs.type, NnMemoryType)
    ):
        _raise_tile_reduce_error("TileReduceRequiresLoweredKernelIR", "matmul operands must be nn.memory")

    space_attr = op.attributes.get("space")
    space = space_attr if isinstance(space_attr, NnMemorySpaceAttr) else out.type.space

    try:
        roles = tile_module._parse_tile_analysis_roles(op)
    except Exception as exc:  # pragma: no cover - failure detail is validated by tests
        _raise_tile_reduce_error("TileReduceRequiresLoweredKernelIR", f"kernel.matmul requires tile.analysis: {exc}")

    expr_rows = _parse_tile_exprs(op)
    if len(roles) != len(expr_rows) or any(len(role_row) != len(expr_row) for role_row, expr_row in zip(roles, expr_rows, strict=True)):
        _raise_tile_reduce_error("TileReduceRequiresLoweredKernelIR", "tile.analysis and tile.tile_exprs must have the same shape")
    if any(expr.strip() for row in expr_rows for expr in row):
        _raise_tile_reduce_error("TileReduceRequiresLoweredKernelIR", "kernel.matmul is already split")

    loop_zero0 = tile_module._build_symbol_const(0)
    loop_zero1 = tile_module._build_symbol_const(0)
    kdim = SymbolGetDimOp(rhs, 0)
    tuner_param = _TileReduceTunerParamOp(reduce_tile_name)

    out_zero0 = tile_module._build_symbol_const(0)
    out_zero1 = tile_module._build_symbol_const(0)
    top_level_ops: list[Operation] = [loop_zero0, loop_zero1, kdim, tuner_param, out_zero0, out_zero1]

    out_dim0 = SymbolGetDimOp(out, 0)
    out_dim1 = SymbolGetDimOp(out, 1)
    out_one0 = tile_module._build_symbol_const(1)
    out_one1 = tile_module._build_symbol_const(1)
    top_level_ops.extend([out_dim0, out_dim1, out_one0, out_one1])

    out_view = _build_unit_stride_view(
        out,
        offsets=[out_zero0, out_zero1],
        shape_values=[out_dim0.result, out_dim1.result],
        stride_values=[out_one0.results[0], out_one1.results[0]],
    )
    top_level_ops.append(out_view)
    dma_fill = UnregisteredOp.with_name("dma.fill").create(
        operands=[out_view.result, loop_zero0.results[0]],
        result_types=[],
    )
    top_level_ops.append(dma_fill)

    reduce_loop, reduce_block, loop_vars = tile_module._build_loop_nest(
        [(loop_zero0.results[0], kdim.result, tuner_param.results[0])]
    )
    if reduce_loop is None or reduce_block is None or not loop_vars:
        _raise_tile_reduce_error("TileReduceRequiresLoweredKernelIR", "failed to build reduce loop")
    k_var = loop_vars[0]

    lhs_zero = tile_module._build_symbol_const(0)
    lhs_dim0 = SymbolGetDimOp(lhs, 0)
    lhs_one0 = tile_module._build_symbol_const(1)
    lhs_one1 = tile_module._build_symbol_const(1)
    lhs_view = _build_unit_stride_view(
        lhs,
        offsets=[lhs_zero.results[0], k_var],
        shape_values=[lhs_dim0.result, tuner_param.results[0]],
        stride_values=[lhs_one0.results[0], lhs_one1.results[0]],
    )

    rhs_zero = tile_module._build_symbol_const(0)
    rhs_dim1 = SymbolGetDimOp(rhs, 1)
    rhs_one0 = tile_module._build_symbol_const(1)
    rhs_one1 = tile_module._build_symbol_const(1)
    rhs_view = _build_unit_stride_view(
        rhs,
        offsets=[k_var, rhs_zero.results[0]],
        shape_values=[tuner_param.results[0], rhs_dim1.result],
        stride_values=[rhs_one0.results[0], rhs_one1.results[0]],
    )

    # The reduce loop body uses the original matmul op in-place, with the reduce tile
    # captured in tile.tile_exprs.
    reduce_block.add_ops(
        [
            lhs_zero,
            lhs_dim0,
            lhs_one0,
            lhs_one1,
            lhs_view,
            rhs_zero,
            rhs_dim1,
            rhs_one0,
            rhs_one1,
            rhs_view,
        ]
    )
    tmp_alloc = UnregisteredOp.with_name("dma.alloc").create(operands=[], result_types=[out_view.result.type])
    reduce_block.add_op(tmp_alloc)

    op.operands[0] = tmp_alloc.results[0]
    op.operands[1] = lhs_view.result
    op.operands[2] = rhs_view.result
    op.attributes["tile.tile_exprs"] = _tile_exprs_attr(roles, reduce_tile_name)

    accumulate = KernelBinaryElewiseOp(
        out_view.result,
        tmp_alloc.results[0],
        out_view.result,
        kind="add",
        space=space,
    )
    reduce_block.add_op(accumulate)
    top_level_ops.append(reduce_loop)
    block.insert_ops_before(top_level_ops, op)
    op.detach()
    reduce_block.add_op(op)
    return top_level_ops


def _lower_function(func_op: func.FuncOp) -> bool:
    """改写单个函数中的 matmul reduction 链。

    创建者: 金铲铲大作战
    最后一次更改: 金铲铲大作战

    功能说明:
    - 仅处理带 `tile.analysis + tile.tile_exprs` 的 `kernel.matmul`。
    - 只对 reduction family 执行收口，其他 op 原样保留。

    使用示例:
    - changed = _lower_function(func_op)

    关联文件:
    - spec: [spec/pass/lowering/tile_reduce.md](spec/pass/lowering/tile_reduce.md)
    - test: [test/pass/test_lowering_tile_reduce.py](test/pass/test_lowering_tile_reduce.py)
    - 功能实现: [kernel_gen/passes/lowering/tile_reduce.py](kernel_gen/passes/lowering/tile_reduce.py)
    """

    block = tile_module._get_single_block(func_op)
    matmul_ops = [op for op in list(block.ops) if op.name == "kernel.matmul"]
    if not matmul_ops:
        return False

    # `PatternRewriteWalker` 可能在本次改写后再次访问同一个 `func.func`。
    # 一旦函数里已经出现 tile-reduce 自己生成的 bridge op，就跳过
    # 旧输入合同校验，避免把新生成的 lowered IR 误判成非法输入。
    if not any(op.name in {"symbol.for", "dma.view", "dma.fill"} for op in block.ops):
        tile_module._validate_input_contract(func_op, block)
        tile_module._validate_intermediate_materialization(func_op, block)

    for reduce_index, matmul_op in enumerate(matmul_ops):
        _lower_matmul_op(
            block,
            matmul_op,
            reduce_tile_name=f"TILE_R{reduce_index}",
        )
    return True


class _TileReduceRewritePattern(RewritePattern):
    """把 tile-reduce 收口动作封装为单个 func.func rewrite pattern。

    创建者: 金铲铲大作战
    最后一次更改: 金铲铲大作战

    功能说明:
    - 通过 `PatternRewriteWalker` 驱动 `func.func` 级别的最小调度。
    - 真正的核心逻辑集中在 `_lower_function`，避免把整块 IR 重建散落在 walker 外。

    使用示例:
    - pattern = _TileReduceRewritePattern()

    关联文件:
    - spec: [spec/pass/lowering/tile_reduce.md](spec/pass/lowering/tile_reduce.md)
    - test: [test/pass/test_lowering_tile_reduce.py](test/pass/test_lowering_tile_reduce.py)
    - 功能实现: [kernel_gen/passes/lowering/tile_reduce.py](kernel_gen/passes/lowering/tile_reduce.py)
    """

    @op_type_rewrite_pattern
    def match_and_rewrite(self, op: func.FuncOp, rewriter: PatternRewriter, /) -> None:
        changed = _lower_function(op)
        if changed:
            rewriter.notify_op_modified(op)


class TileReducePass(ModulePass):
    """`tile-reduce` 公开入口。

    创建者: 金铲铲大作战
    最后一次更改: 金铲铲大作战

    功能说明:
    - 保持稳定公开名 `tile-reduce`。
    - 通过 pattern rewrite 驱动 matmul reduction 收口。

    使用示例:
    - from xdsl.context import Context
    - from xdsl.dialects.builtin import ModuleOp
    - TileReducePass().apply(Context(), module)

    关联文件:
    - spec: [spec/pass/lowering/tile_reduce.md](spec/pass/lowering/tile_reduce.md)
    - test: [test/pass/test_lowering_tile_reduce.py](test/pass/test_lowering_tile_reduce.py)
    - 功能实现: [kernel_gen/passes/lowering/tile_reduce.py](kernel_gen/passes/lowering/tile_reduce.py)
    """

    name = "tile-reduce"

    def apply(self: "TileReducePass", ctx: Context, module: ModuleOp) -> None:
        """执行 `tile-reduce` ModulePass。

        创建者: 金铲铲大作战
        最后一次更改: 金铲铲大作战

        功能说明:
        - 仅接受 `builtin.module`。
        - 只对带 `tile.analysis + tile.tile_exprs` 的 matmul reduction 链执行收口。
        - 不引入 `tile.step_value` / `kernel_split.tile_value`。

        使用示例:
        - TileReducePass().apply(Context(), module)

        关联文件:
        - spec: [spec/pass/lowering/tile_reduce.md](spec/pass/lowering/tile_reduce.md)
        - test: [test/pass/test_lowering_tile_reduce.py](test/pass/test_lowering_tile_reduce.py)
        - 功能实现: [kernel_gen/passes/lowering/tile_reduce.py](kernel_gen/passes/lowering/tile_reduce.py)
        """

        del ctx
        if not isinstance(module, ModuleOp):
            _raise_tile_reduce_error("TileReduceRequiresLoweredKernelIR", "module must be builtin.module")
        PatternRewriteWalker(
            GreedyRewritePatternApplier(
                [
                    _TileReduceRewritePattern(),
                ],
                dce_enabled=False,
            )
        ).rewrite_module(module)
        try:
            module.verify()
        except VerifyException as exc:  # pragma: no cover - verification failure is asserted via tests
            _raise_tile_reduce_error("TileReduceRequiresLoweredKernelIR", str(exc))


__all__ = ["TileReducePass", "TileReduceError"]
