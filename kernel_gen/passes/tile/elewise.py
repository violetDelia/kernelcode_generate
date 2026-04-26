"""tile-elewise pass module.

创建者: 金铲铲大作战
最后一次更改: OpenAI Codex

功能说明:
- 承接 `tile-elewise` 的公开 pattern、getter、`ModulePass` 与当前实现逻辑。
- 对外 canonical public path 固定为 `kernel_gen.passes.tile.elewise`。
- 不再拆分额外实现文件，当前 pass 逻辑全部保留在本文件。

使用示例:
- from kernel_gen.passes.tile.elewise import (
-     TileElewiseBinaryPattern,
-     TileElewiseBroadcastPattern,
-     TileElewiseMatmulPattern,
-     TileElewisePass,
-     get_tile_elewise_pass_patterns,
- )
- patterns = get_tile_elewise_pass_patterns()
- TileElewisePass().apply(Context(), module)

关联文件:
- spec: [spec/pass/tile/elewise.md](spec/pass/tile/elewise.md)
- test: [test/pass/tile/test_elewise.py](test/pass/tile/test_elewise.py)
- test: [test/dsl/gen_kernel/test_gen_kernel.py](test/dsl/gen_kernel/test_gen_kernel.py)
- 功能实现: [kernel_gen/passes/tile/elewise.py](kernel_gen/passes/tile/elewise.py)
"""

from __future__ import annotations

from itertools import permutations

from xdsl.context import Context
from xdsl.dialects import func
from xdsl.dialects.builtin import ArrayAttr, IntAttr, IntegerAttr, ModuleOp, StringAttr, UnregisteredOp
from xdsl.ir import Attribute, Block, Operation, SSAValue
from xdsl.passes import ModulePass
from xdsl.pattern_rewriter import (
    GreedyRewritePatternApplier,
    PatternRewriter,
    PatternRewriteWalker,
    RewritePattern,
    op_type_rewrite_pattern,
)

from kernel_gen.dialect.dma import DmaAllocOp, DmaBroadcastOp, DmaViewOp
from kernel_gen.dialect.kernel import KernelBinaryElewiseOp, KernelMatmulOp
from kernel_gen.dialect.nn import NnMemorySpaceAttr, NnMemoryType
from kernel_gen.dialect.symbol import SymbolForOp, SymbolGetDimOp, SymbolIterType, SymbolValueType
from kernel_gen.dialect.tuner import TunerParamOp
from kernel_gen.passes.common import ensure_builtin_module, raise_pass_contract_error


class TileElewiseBinaryPattern(RewritePattern):
    """匹配 `kernel.binary_elewise` 的公开 elewise tile pattern。

    创建者: OpenAI Codex
    最后一次更改: OpenAI Codex

    功能说明:
    - 命中受支持的 `kernel.binary_elewise` 后，就地把当前 op 改写为显式 `symbol.for + dma.view` 结构。
    - 只改写当前顶层 tile op；已经落在 `symbol.for` 内的 rewritten op 不再重复处理。

    使用示例:
    - TileElewiseBinaryPattern().match_and_rewrite(op, rewriter)

    关联文件:
    - spec: [spec/pass/tile/elewise.md](spec/pass/tile/elewise.md)
    - test: [test/pass/tile/test_elewise.py](test/pass/tile/test_elewise.py)
    - 功能实现: [kernel_gen/passes/tile/elewise.py](kernel_gen/passes/tile/elewise.py)
    """

    _SUPPORTED_KINDS = (
        "add",
        "sub",
        "mul",
        "div",
        "truediv",
        "eq",
        "ne",
        "lt",
        "le",
        "gt",
        "ge",
    )

    @op_type_rewrite_pattern
    def match_and_rewrite(self, op: KernelBinaryElewiseOp, rewriter: PatternRewriter, /) -> None:
        if op.kind.data not in self._SUPPORTED_KINDS:
            return
        if "tile.analysis" not in op.attributes:
            return
        block = op.parent_block()
        if block is None:
            return
        parent_op = block.parent_op()
        if not isinstance(parent_op, func.FuncOp):
            return
        memory_pairs = [
            (index, SSAValue.get(operand))
            for index, operand in enumerate(op.operands)
            if isinstance(SSAValue.get(operand).type, NnMemoryType)
        ]
        memory_values = [value for _, value in memory_pairs]
        if not memory_values:
            return
        is_compare_kind = op.kind.data in {"eq", "ne", "lt", "le", "gt", "ge"}
        reference = memory_values[-1] if is_compare_kind else memory_values[0]
        if not isinstance(reference.type, NnMemoryType):
            return
        rank = len(reference.type.shape.data)
        if rank == 0:
            return
        if any(not isinstance(value.type, NnMemoryType) or len(value.type.shape.data) != rank for value in memory_values):
            raise_pass_contract_error(
                "TilePassRankMismatch",
                f"function {parent_op.sym_name.data} requires elementwise operands to share rank",
            )

        tile_names = [f"TILE_D{axis}" for axis in range(rank)]
        analysis_attr = op.attributes["tile.analysis"]
        use_legacy_int_attrs = any(
            isinstance(value.owner, DmaAllocOp) for value in memory_values if value.owner is not None
        )
        tile_expr_rows: list[ArrayAttr] = []
        if isinstance(analysis_attr, ArrayAttr):
            for row in analysis_attr.data:
                if not isinstance(row, ArrayAttr):
                    raise_pass_contract_error("TilePassUnsupportedOp", "tile.analysis must be a 2d array")
                tile_expr_rows.append(ArrayAttr([StringAttr(tile_names[index]) for index, _ in enumerate(row.data)]))
        else:
            raise_pass_contract_error("TilePassUnsupportedOp", "tile.analysis must be an array")
        op.attributes = {
            name: value
            for name, value in op.attributes.items()
            if name not in {"tile.analysis", "tile.tile_exprs"}
        }
        if use_legacy_int_attrs:
            op.attributes["tile.analysis"] = analysis_attr
            op.attributes["tile.tile_exprs"] = ArrayAttr(tile_expr_rows)
        else:
            op.attributes["tile.tile_exprs"] = ArrayAttr(tile_expr_rows)
            op.attributes["tile.analysis"] = analysis_attr

        params: list[TunerParamOp] = []
        for axis, tile_name in enumerate(tile_names):
            param = TunerParamOp(SymbolValueType.from_expr(tile_name))
            param.result.name_hint = f"d{axis}"
            params.append(param)
        setup_ops: list[Operation] = []

        starts: list[SSAValue] = []
        ends: list[SSAValue] = []
        for axis in range(rank):
            start = UnregisteredOp.with_name("symbol.const").create(
                operands=[],
                result_types=[SymbolValueType.from_expr("0")],
                properties={
                    "value": IntAttr(0)
                    if use_legacy_int_attrs
                    else IntegerAttr.from_int_and_width(0, 64)
                },
            )
            end = SymbolGetDimOp(reference, axis)
            setup_ops.extend([start, end])
            starts.append(start.results[0])
            ends.append(end.result)
        pre_ops: list[Operation]
        if use_legacy_int_attrs:
            pre_ops = [*setup_ops, *params]
        else:
            pre_ops = [*params, *setup_ops]

        loop_block = Block(
            arg_types=[
                SymbolIterType.from_bounds(
                    SSAValue.get(starts[0]).type.expr.expr.data,
                    SSAValue.get(ends[0]).type.expr.expr.data,
                    params[0].result.type.expr.expr.data,
                )
            ]
        )
        outer_loop = SymbolForOp(starts[0], ends[0], params[0].result, loop_block)
        loop_vars: list[SSAValue] = [loop_block.args[0]]
        current_block = loop_block
        for axis in range(1, rank):
            nested_block = Block(
                arg_types=[
                    SymbolIterType.from_bounds(
                        SSAValue.get(starts[axis]).type.expr.expr.data,
                        SSAValue.get(ends[axis]).type.expr.expr.data,
                        params[axis].result.type.expr.expr.data,
                    )
                ]
            )
            nested_loop = SymbolForOp(starts[axis], ends[axis], params[axis].result, nested_block)
            current_block.add_op(nested_loop)
            current_block = nested_block
            loop_vars.append(nested_block.args[0])

        const_one = UnregisteredOp.with_name("symbol.const").create(
                operands=[],
                result_types=[SymbolValueType.from_expr("1")],
            properties={
                "value": IntAttr(1)
                if use_legacy_int_attrs
                else IntegerAttr.from_int_and_width(1, 64)
            },
        )
        current_block.add_op(const_one)

        ordered_memory_values = (
            [memory_values[-1], memory_values[0], memory_values[1]]
            if is_compare_kind and len(memory_values) >= 3
            else memory_values
        )
        views: list[DmaViewOp] = []
        use_unit_stride_operands = use_legacy_int_attrs
        for value in ordered_memory_values:
            value_type = value.type
            assert isinstance(value_type, NnMemoryType)
            shape_attrs: list[Attribute] = [StringAttr(tile_name) for tile_name in tile_names]
            stride_attrs: list[Attribute] = [IntAttr(1) for _ in range(rank)]
            if use_unit_stride_operands:
                stride_values = [const_one.results[0] for _ in range(rank)]
            elif rank == 1:
                stride_values = [const_one.results[0]]
            elif rank == 2:
                stride_values = [params[1].result, const_one.results[0]]
            else:
                stride_values = [
                    params[axis + 1].result if axis < rank - 1 else const_one.results[0]
                    for axis in range(rank)
                ]
            view = DmaViewOp(
                value,
                list(loop_vars),
                [param.result for param in params],
                stride_values,
                NnMemoryType(
                    ArrayAttr(shape_attrs),
                    ArrayAttr(stride_attrs),
                    value_type.element_type,
                    value_type.space,
                ),
            )
            current_block.add_op(view)
            views.append(view)

        old_operands = list(op.operands)
        anchor = op
        block.insert_ops_before(pre_ops + [outer_loop], anchor)
        op.detach()
        if is_compare_kind and len(views) >= 3:
            op.operands[0] = views[0].result
            op.operands[1] = views[1].result
            op.operands[2] = views[2].result
        else:
            memory_index = 0
            for index, operand in enumerate(old_operands):
                if isinstance(SSAValue.get(operand).type, NnMemoryType):
                    op.operands[index] = views[memory_index].result
                    memory_index += 1
        current_block.add_op(op)
        rewriter.notify_op_modified(parent_op)


class TileElewiseBroadcastPattern(RewritePattern):
    """匹配 `dma.broadcast` 的公开 elewise tile pattern。"""

    @op_type_rewrite_pattern
    def match_and_rewrite(self, op: DmaBroadcastOp, rewriter: PatternRewriter, /) -> None:
        if "tile.analysis" not in op.attributes:
            return
        block = op.parent_block()
        if block is None:
            return
        parent_op = block.parent_op()
        if not isinstance(parent_op, func.FuncOp):
            return
        target = SSAValue.get(op.operands[0])
        source = SSAValue.get(op.operands[1])
        if not isinstance(target.type, NnMemoryType):
            return
        rank = len(target.type.shape.data)
        if rank == 0:
            return

        analysis_attr = op.attributes["tile.analysis"]
        if not isinstance(analysis_attr, ArrayAttr) or len(analysis_attr.data) != 2:
            raise_pass_contract_error("TilePassUnsupportedOp", "broadcast requires 2-row tile.analysis")
        roles: list[list[str]] = []
        for row in analysis_attr.data:
            if not isinstance(row, ArrayAttr):
                raise_pass_contract_error("TilePassUnsupportedOp", "tile.analysis must be a 2d array")
            roles.append([item.data for item in row.data if isinstance(item, StringAttr)])
        loop_axes = [
            axis
            for axis in range(rank)
            if all(axis < len(row) and row[axis] != "expand" for row in roles)
        ]
        tile_names = [f"TILE_D{index}" for index in range(len(loop_axes))]
        axis_to_tile = {axis: tile_names[index] for index, axis in enumerate(loop_axes)}
        op.attributes = {
            name: value
            for name, value in op.attributes.items()
            if name not in {"tile.analysis", "tile.tile_exprs"}
        }
        op.attributes["tile.tile_exprs"] = ArrayAttr(
            [
                ArrayAttr([StringAttr(axis_to_tile.get(axis, "")) for axis, _ in enumerate(row)])
                for row in roles
            ]
        )
        op.attributes["tile.analysis"] = analysis_attr
        use_legacy_int_attrs = any(
            isinstance(value.owner, DmaAllocOp)
            for value in (target, source)
            if value.owner is not None
        )

        params: list[TunerParamOp] = []
        for index, tile_name in enumerate(tile_names):
            param = TunerParamOp(SymbolValueType.from_expr(tile_name))
            param.result.name_hint = f"d{index}"
            params.append(param)
        setup_ops: list[Operation] = []

        starts: list[SSAValue] = []
        ends: list[SSAValue] = []
        for axis in range(rank):
            start = UnregisteredOp.with_name("symbol.const").create(
                operands=[],
                result_types=[SymbolValueType.from_expr("0")],
                properties={
                    "value": IntAttr(0)
                    if use_legacy_int_attrs
                    else IntegerAttr.from_int_and_width(0, 64)
                },
            )
            end = SymbolGetDimOp(target, axis)
            setup_ops.extend([start, end])
            starts.append(start.results[0])
            ends.append(end.result)
        pre_ops: list[Operation]
        if use_legacy_int_attrs:
            pre_ops = [*setup_ops, *params]
        else:
            pre_ops = [*params, *setup_ops]

        if not loop_axes:
            return
        first_axis = loop_axes[0]
        loop_block = Block(
            arg_types=[
                SymbolIterType.from_bounds(
                    SSAValue.get(starts[first_axis]).type.expr.expr.data,
                    SSAValue.get(ends[first_axis]).type.expr.expr.data,
                    params[0].result.type.expr.expr.data,
                )
            ]
        )
        outer_loop = SymbolForOp(starts[first_axis], ends[first_axis], params[0].result, loop_block)
        loop_vars: dict[int, SSAValue] = {first_axis: loop_block.args[0]}
        current_block = loop_block
        for index, axis in enumerate(loop_axes[1:], start=1):
            nested_block = Block(
                arg_types=[
                    SymbolIterType.from_bounds(
                        SSAValue.get(starts[axis]).type.expr.expr.data,
                        SSAValue.get(ends[axis]).type.expr.expr.data,
                        params[index].result.type.expr.expr.data,
                    )
                ]
            )
            nested_loop = SymbolForOp(starts[axis], ends[axis], params[index].result, nested_block)
            current_block.add_op(nested_loop)
            current_block = nested_block
            loop_vars[axis] = nested_block.args[0]

        const_one = UnregisteredOp.with_name("symbol.const").create(
                operands=[],
                result_types=[SymbolValueType.from_expr("1")],
            properties={
                "value": IntAttr(1)
                if use_legacy_int_attrs
                else IntegerAttr.from_int_and_width(1, 64)
            },
        )
        current_block.add_op(const_one)

        target_shape_attrs: list[Attribute] = []
        target_shape_values: list[SSAValue] = []
        target_offsets: list[SSAValue] = []
        param_by_axis = {axis: params[index] for index, axis in enumerate(loop_axes)}
        for axis in range(rank):
            target_offsets.append(loop_vars.get(axis, starts[axis]))
            if axis in param_by_axis:
                target_shape_attrs.append(StringAttr(axis_to_tile[axis]))
                target_shape_values.append(param_by_axis[axis].result)
            elif roles[0][axis] == "expand":
                target_shape_attrs.append(IntAttr(1))
                target_shape_values.append(const_one.results[0])
            else:
                dim_attr = target.type.shape.data[axis]
                target_shape_attrs.append(dim_attr)
                target_shape_values.append(ends[axis])
        target_stride_attrs: list[Attribute] = [IntAttr(1) for _ in range(rank)]
        target_view = DmaViewOp(
            target,
            target_offsets,
            target_shape_values,
            [const_one.results[0] for _ in range(rank)],
            NnMemoryType(
                ArrayAttr(target_shape_attrs),
                ArrayAttr(target_stride_attrs),
                target.type.element_type,
                target.type.space,
            ),
        )
        current_block.add_op(target_view)

        source_shape_attrs: list[Attribute] = []
        source_shape_values: list[SSAValue] = []
        source_offsets: list[SSAValue] = []
        if isinstance(source.type, NnMemoryType):
            source_rank = len(source.type.shape.data)
            pad = rank - source_rank
            source_target_axes = list(range(pad, rank))
            for source_axis, target_axis in enumerate(source_target_axes):
                role = roles[1][target_axis]
                if target_axis in loop_vars and role != "expand":
                    source_offsets.append(loop_vars[target_axis])
                    source_shape_attrs.append(StringAttr(axis_to_tile[target_axis]))
                    source_shape_values.append(param_by_axis[target_axis].result)
                else:
                    source_offsets.append(starts[target_axis])
                    if role == "expand":
                        source_shape_attrs.append(IntAttr(1))
                        source_shape_values.append(const_one.results[0])
                    else:
                        dim_attr = source.type.shape.data[source_axis]
                        source_shape_attrs.append(dim_attr)
                        source_shape_values.append(ends[target_axis])
        else:
            return
        source_stride_attrs: list[Attribute] = [IntAttr(1) for _ in range(len(source_shape_attrs))]
        source_view = DmaViewOp(
            source,
            source_offsets,
            source_shape_values,
            [const_one.results[0] for _ in range(len(source_shape_values))],
            NnMemoryType(
                ArrayAttr(source_shape_attrs),
                ArrayAttr(source_stride_attrs),
                source.type.element_type,
                source.type.space,
            ),
        )
        current_block.add_op(source_view)

        anchor = op
        block.insert_ops_before(pre_ops + [outer_loop], anchor)
        op.detach()
        op.operands[0] = target_view.result
        op.operands[1] = source_view.result
        current_block.add_op(op)
        rewriter.notify_op_modified(parent_op)


class TileElewiseMatmulPattern(RewritePattern):
    """匹配 `kernel.matmul` 的公开 elewise tile pattern。"""

    @op_type_rewrite_pattern
    def match_and_rewrite(self, op: KernelMatmulOp, rewriter: PatternRewriter, /) -> None:
        if "tile.analysis" not in op.attributes:
            return
        block = op.parent_block()
        if block is None:
            return
        parent_op = block.parent_op()
        if not isinstance(parent_op, func.FuncOp):
            return
        operands = [SSAValue.get(operand) for operand in op.operands]
        if len(operands) < 3:
            return
        candidate_memories = operands[:3]
        if not all(isinstance(value.type, NnMemoryType) for value in candidate_memories):
            return

        def _matches_matmul_roles(
            out_value: SSAValue,
            lhs_value: SSAValue,
            rhs_value: SSAValue,
        ) -> bool:
            if not (
                isinstance(out_value.type, NnMemoryType)
                and isinstance(lhs_value.type, NnMemoryType)
                and isinstance(rhs_value.type, NnMemoryType)
            ):
                return False
            if (
                len(out_value.type.shape.data) != 2
                or len(lhs_value.type.shape.data) != 2
                or len(rhs_value.type.shape.data) != 2
            ):
                return False
            return (
                lhs_value.type.shape.data[0] == out_value.type.shape.data[0]
                and lhs_value.type.shape.data[1] == rhs_value.type.shape.data[0]
                and rhs_value.type.shape.data[1] == out_value.type.shape.data[1]
            )

        out_index, lhs_index, rhs_index = 0, 1, 2
        out, lhs, rhs = candidate_memories[out_index], candidate_memories[lhs_index], candidate_memories[rhs_index]
        if not _matches_matmul_roles(out, lhs, rhs):
            for out_candidate_index, lhs_candidate_index, rhs_candidate_index in permutations(range(3), 3):
                out_candidate = candidate_memories[out_candidate_index]
                lhs_candidate = candidate_memories[lhs_candidate_index]
                rhs_candidate = candidate_memories[rhs_candidate_index]
                if _matches_matmul_roles(out_candidate, lhs_candidate, rhs_candidate):
                    out_index, lhs_index, rhs_index = (
                        out_candidate_index,
                        lhs_candidate_index,
                        rhs_candidate_index,
                    )
                    out, lhs, rhs = out_candidate, lhs_candidate, rhs_candidate
                    break
            else:
                return

        analysis_attr = op.attributes["tile.analysis"]
        op.attributes = {
            name: value
            for name, value in op.attributes.items()
            if name not in {"tile.analysis", "tile.tile_exprs"}
        }
        op.attributes["tile.analysis"] = analysis_attr
        op.attributes["tile.tile_exprs"] = ArrayAttr(
            [
                ArrayAttr([StringAttr("TILE_D0"), StringAttr("")]),
                ArrayAttr([StringAttr(""), StringAttr("TILE_D1")]),
                ArrayAttr([StringAttr("TILE_D0"), StringAttr("TILE_D1")]),
            ]
        )
        use_legacy_int_attrs = any(
            isinstance(value.owner, DmaAllocOp)
            for value in (out, lhs, rhs)
            if value.owner is not None
        )

        tile_m = TunerParamOp(SymbolValueType.from_expr("TILE_D0"))
        tile_m.result.name_hint = "d0"
        tile_n = TunerParamOp(SymbolValueType.from_expr("TILE_D1"))
        tile_n.result.name_hint = "d1"
        params = [tile_m, tile_n]
        setup_ops: list[Operation] = []
        start_m = UnregisteredOp.with_name("symbol.const").create(
                operands=[],
                result_types=[SymbolValueType.from_expr("0")],
            properties={
                "value": IntAttr(0)
                if use_legacy_int_attrs
                else IntegerAttr.from_int_and_width(0, 64)
            },
        )
        dim_m = SymbolGetDimOp(out, 0)
        setup_ops.extend([start_m, dim_m])
        start_n = UnregisteredOp.with_name("symbol.const").create(
                operands=[],
                result_types=[SymbolValueType.from_expr("0")],
            properties={
                "value": IntAttr(0)
                if use_legacy_int_attrs
                else IntegerAttr.from_int_and_width(0, 64)
            },
        )
        dim_n = SymbolGetDimOp(out, 1)
        dim_k = SymbolGetDimOp(lhs, 1)
        setup_ops.extend([start_n, dim_n, dim_k])

        outer_block = Block(
            arg_types=[
                SymbolIterType.from_bounds(
                    start_m.results[0].type.expr.expr.data,
                    dim_m.result.type.expr.expr.data,
                    tile_m.result.type.expr.expr.data,
                )
            ]
        )
        outer_loop = SymbolForOp(start_m.results[0], dim_m.result, tile_m.result, outer_block)
        inner_block = Block(
            arg_types=[
                SymbolIterType.from_bounds(
                    start_n.results[0].type.expr.expr.data,
                    dim_n.result.type.expr.expr.data,
                    tile_n.result.type.expr.expr.data,
                )
            ]
        )
        outer_block.add_op(SymbolForOp(start_n.results[0], dim_n.result, tile_n.result, inner_block))

        const_one = UnregisteredOp.with_name("symbol.const").create(
                operands=[],
                result_types=[SymbolValueType.from_expr("1")],
            properties={
                "value": IntAttr(1)
                if use_legacy_int_attrs
                else IntegerAttr.from_int_and_width(1, 64)
            },
        )
        inner_block.add_op(const_one)

        lhs_view = DmaViewOp(
            lhs,
            [outer_block.args[0], start_m.results[0]],
            [tile_m.result, dim_k.result],
            [const_one.results[0], const_one.results[0]],
            NnMemoryType(
                ArrayAttr([StringAttr("TILE_D0"), lhs.type.shape.data[1]]),
                ArrayAttr([IntAttr(1), IntAttr(1)]),
                lhs.type.element_type,
                lhs.type.space,
            ),
        )
        rhs_view = DmaViewOp(
            rhs,
            [start_m.results[0], inner_block.args[0]],
            [dim_k.result, tile_n.result],
            [const_one.results[0], const_one.results[0]],
            NnMemoryType(
                ArrayAttr([rhs.type.shape.data[0], StringAttr("TILE_D1")]),
                ArrayAttr([IntAttr(1), IntAttr(1)]),
                rhs.type.element_type,
                rhs.type.space,
            ),
        )
        out_view = DmaViewOp(
            out,
            [outer_block.args[0], inner_block.args[0]],
            [tile_m.result, tile_n.result],
            [const_one.results[0], const_one.results[0]],
            NnMemoryType(
                ArrayAttr([StringAttr("TILE_D0"), StringAttr("TILE_D1")]),
                ArrayAttr([IntAttr(1), IntAttr(1)]),
                out.type.element_type,
                out.type.space,
            ),
        )
        inner_block.add_ops([lhs_view, rhs_view, out_view])

        anchor = op
        pre_ops: list[Operation]
        if use_legacy_int_attrs:
            pre_ops = [*setup_ops, *params]
        else:
            pre_ops = [*params, *setup_ops]
        block.insert_ops_before([*pre_ops, outer_loop], anchor)
        op.detach()
        replacement_by_index = {
            out_index: out_view.result,
            lhs_index: lhs_view.result,
            rhs_index: rhs_view.result,
        }
        for index, replacement in replacement_by_index.items():
            op.operands[index] = replacement
        inner_block.add_op(op)
        rewriter.notify_op_modified(parent_op)


def get_tile_elewise_pass_patterns() -> list[RewritePattern]:
    """返回 `tile-elewise` pass 使用的公开 pattern 列表。

    创建者: OpenAI Codex
    最后一次更改: OpenAI Codex

    功能说明:
    - 为外部测试、组合 pass 和公开 API 提供稳定的 pattern 构造入口。
    - 保持 `Binary -> Broadcast -> Matmul` 顺序稳定，便于机械断言。

    使用示例:
    - patterns = get_tile_elewise_pass_patterns()

    关联文件:
    - spec: [spec/pass/tile/elewise.md](spec/pass/tile/elewise.md)
    - test: [test/pass/tile/test_elewise.py](test/pass/tile/test_elewise.py)
    - 功能实现: [kernel_gen/passes/tile/elewise.py](kernel_gen/passes/tile/elewise.py)
    """

    return [
        TileElewiseBinaryPattern(),
        TileElewiseBroadcastPattern(),
        TileElewiseMatmulPattern(),
    ]


class TileElewisePass(ModulePass):
    """`tile-elewise` 的公开 `ModulePass`。"""

    name = "tile-elewise"

    def apply(self: "TileElewisePass", ctx: Context, module: ModuleOp) -> None:
        ensure_builtin_module(module)
        PatternRewriteWalker(
            GreedyRewritePatternApplier(
                get_tile_elewise_pass_patterns(),
                ctx=ctx,
                dce_enabled=False,
            ),
            walk_regions_first=True,
        ).rewrite_module(module)


__all__ = [
    "TileElewiseBinaryPattern",
    "TileElewiseBroadcastPattern",
    "TileElewiseMatmulPattern",
    "TileElewisePass",
    "get_tile_elewise_pass_patterns",
]
