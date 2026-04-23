"""tile-reduce implementation landing module.

创建者: 金铲铲大作战
最后一次更改: 金铲铲大作战

功能说明:
- 承接 `tile-reduce` 的真实 rewrite 主链。
- 保持公开 `ModulePass` 壳在 `kernel_gen.passes.lowering.tile_reduce`，把 matmul reduce rewrite 的 canonical path 收口到 `kernel_gen.tile.reduce`。
- S4 阶段不改最终 reduce 逻辑，只整理 helper/path。

使用示例:
- from kernel_gen.tile.reduce import apply_tile_reduce
- apply_tile_reduce(module)

关联文件:
- spec: [spec/pass/lowering/tile_reduce.md](spec/pass/lowering/tile_reduce.md)
- test: [test/pass/test_lowering_tile_reduce.py](test/pass/test_lowering_tile_reduce.py)
- test: [test/dsl/test_gen_kernel.py](test/dsl/test_gen_kernel.py)
- 功能实现: [kernel_gen/tile/reduce.py](kernel_gen/tile/reduce.py)
"""

from __future__ import annotations

from xdsl.dialects.builtin import ArrayAttr, ModuleOp, StringAttr
from xdsl.ir import SSAValue

from kernel_gen.dialect.symbol import SymbolValueType

from . import common as tile_common


def _build_tile_exprs_attr(plan: tile_common._TileOpPlan, analysis_attr: ArrayAttr) -> ArrayAttr:
    """根据 tile 计划与 analysis 形状构造 `tile.tile_exprs`。

    创建者: 金铲铲大作战
    最后一次更改: 金铲铲大作战

    功能说明:
    - 保持 `tile.tile_exprs` 与 `tile.analysis` 同形状。
    - 仅在实际参与外层切分的 axis 上写入 tile 名称，reduce 轴不写入 operand 维度矩阵。

    使用示例:
    - tile_exprs = _build_tile_exprs_attr(plan, analysis_attr)

    关联文件:
    - spec: [spec/pass/lowering/tile_reduce.md](spec/pass/lowering/tile_reduce.md)
    - test: [test/pass/test_lowering_tile_reduce.py](test/pass/test_lowering_tile_reduce.py)
    - 功能实现: [kernel_gen/tile/reduce.py](kernel_gen/tile/reduce.py)
    """

    axis_to_tile = {axis: plan.tile_names[index] for index, axis in enumerate(plan.loop_axes)}
    rows: list[ArrayAttr] = []
    for row in analysis_attr.data:
        if not isinstance(row, ArrayAttr):
            tile_common._raise_tile_error("TilePassUnsupportedOp", "tile.analysis must be a 2d array")
        exprs = [StringAttr(axis_to_tile.get(axis_index, "")) for axis_index, _ in enumerate(row.data)]
        rows.append(ArrayAttr(exprs))
    return ArrayAttr(rows)


def apply_tile_reduce(module: ModuleOp) -> None:
    """执行 tile-reduce 的公开 rewrite 主链。

    创建者: 金铲铲大作战
    最后一次更改: 金铲铲大作战

    功能说明:
    - 只接受 `builtin.module`。
    - 只对 `kernel.matmul` 补齐 reduce 轴循环和 `dma.fill` 累加结构。
    - 保留 rewritten op 的 `tile.analysis` 与 `tile.tile_exprs`。

    使用示例:
    - apply_tile_reduce(module)

    关联文件:
    - spec: [spec/pass/lowering/tile_reduce.md](spec/pass/lowering/tile_reduce.md)
    - test: [test/pass/test_lowering_tile_reduce.py](test/pass/test_lowering_tile_reduce.py)
    - test: [test/dsl/test_gen_kernel.py](test/dsl/test_gen_kernel.py)
    - 功能实现: [kernel_gen/tile/reduce.py](kernel_gen/tile/reduce.py)
    """

    if not isinstance(module, ModuleOp):
        tile_common._raise_tile_error("TilePassRequiresLoweredKernelIR", "module must be builtin.module")

    for op in module.ops:
        if not isinstance(op, tile_common.func.FuncOp):
            continue

        block = tile_common._get_single_block(op)
        tile_common._normalize_binary_elewise_compare_compat(block)
        tile_common._validate_input_contract(op, block)
        tile_common._validate_intermediate_materialization(op, block)
        for candidate in block.ops:
            if candidate.name != "kernel.matmul":
                continue
            if "tile.analysis" in candidate.attributes and "tile.tile_exprs" in candidate.attributes:
                continue
            tile_common._raise_tile_error(
                "TilePassUnsupportedOp",
                f"function {op.sym_name.data} requires tile.analysis and tile.tile_exprs before tile-reduce",
            )

        return_op = block.last_op
        if not isinstance(return_op, tile_common.func.ReturnOp):
            tile_common._raise_tile_error(
                "TilePassRequiresLoweredKernelIR",
                f"function {op.sym_name.data} must terminate with func.return",
            )

        plans, _ordered_tile_names = tile_common._plan_tile_ops(op, block, tile_reduce=True)
        reduce_plans = [plan for plan in plans if plan.kind == "matmul"]
        if not reduce_plans:
            continue

        planned_ops = {plan.op for plan in reduce_plans}
        preserved_ops = [candidate for candidate in block.ops if candidate not in planned_ops and candidate is not return_op]
        reduce_tile_names: list[str] = []
        for plan in reduce_plans:
            for tile_name in plan.tile_names:
                if tile_name not in reduce_tile_names:
                    reduce_tile_names.append(tile_name)
            if plan.reduce_tile_name is not None and plan.reduce_tile_name not in reduce_tile_names:
                reduce_tile_names.append(plan.reduce_tile_name)

        tile_params: list[object] = []
        tile_values: dict[str, SSAValue] = {}
        for tile_name in reduce_tile_names:
            if tile_name in tile_values:
                continue
            param = tile_common.TunerParamOp(SymbolValueType.from_expr(tile_name))
            name_hint = tile_common._tile_param_hint(tile_name)
            if name_hint is not None:
                param.result.name_hint = name_hint
            tile_params.append(param)
            tile_values[tile_name] = param.result

        new_ops: list[object] = [*preserved_ops, *tile_params]
        for plan in reduce_plans:
            analysis_attr = plan.op.attributes.get("tile.analysis")
            if not isinstance(analysis_attr, ArrayAttr):
                tile_common._raise_tile_error(
                    "TilePassUnsupportedOp",
                    f"function {op.sym_name.data} requires tile.analysis before tile-reduce",
                )
            tile_exprs_attr = _build_tile_exprs_attr(plan, analysis_attr)
            plan.op.attributes["tile.analysis"] = analysis_attr
            plan.op.attributes["tile.tile_exprs"] = tile_exprs_attr
            new_ops.extend(tile_common._rewrite_matmul_plan(plan, tile_values=tile_values, tile_reduce=True))
            plan.op.attributes["tile.analysis"] = analysis_attr
            plan.op.attributes["tile.tile_exprs"] = tile_exprs_attr

        new_ops.append(return_op)
        for candidate in list(block.ops):
            candidate.detach()
        block.add_ops(new_ops)


__all__ = ["apply_tile_reduce"]
