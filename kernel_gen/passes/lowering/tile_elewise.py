"""tile-elewise pass.

创建者: 小李飞刀
最后一次更改: 小李飞刀

功能说明:
- 提供 `tile-elewise` 的公开 `ModulePass` 入口。
- 消费已有 `tile.analysis` / `tile.tile_exprs` 输入合同，只切分 elewise 轴并保留最终合同属性。
- 不生成 `tile.step_value` / `kernel_split.tile_value` 这类旧桥接 op。

使用示例:
- from xdsl.context import Context
- from xdsl.dialects.builtin import ModuleOp
- from kernel_gen.passes.lowering.tile_elewise import TileElewisePass
- TileElewisePass().apply(Context(), ModuleOp([]))

关联文件:
- spec: [spec/pass/lowering/tile_elewise.md](spec/pass/lowering/tile_elewise.md)
- test: [test/pass/test_lowering_tile_elewise.py](test/pass/test_lowering_tile_elewise.py)
- 功能实现: [kernel_gen/passes/lowering/tile_elewise.py](kernel_gen/passes/lowering/tile_elewise.py)
"""

from __future__ import annotations

from xdsl.context import Context
from xdsl.dialects.builtin import ArrayAttr, ModuleOp, StringAttr
from xdsl.ir import SSAValue
from xdsl.passes import ModulePass

from kernel_gen.dialect.symbol import SymbolValueType

from . import tile as tile_module


def _build_tile_exprs_attr(plan: tile_module._TileOpPlan, analysis_attr: ArrayAttr) -> ArrayAttr:
    """根据 tile 计划与 analysis 形状构造 `tile.tile_exprs`。

    创建者: 小李飞刀
    最后一次更改: 小李飞刀

    功能说明:
    - 保持 `tile.tile_exprs` 与 `tile.analysis` 同形状。
    - 仅在实际参与切分的 axis 上写入 tile 名称，未切分轴保持空串。

    使用示例:
    - tile_exprs = _build_tile_exprs_attr(plan, analysis_attr)

    关联文件:
    - spec: [spec/pass/lowering/tile_elewise.md](spec/pass/lowering/tile_elewise.md)
    - test: [test/pass/test_lowering_tile_elewise.py](test/pass/test_lowering_tile_elewise.py)
    - 功能实现: [kernel_gen/passes/lowering/tile_elewise.py](kernel_gen/passes/lowering/tile_elewise.py)
    """

    axis_to_tile = {axis: plan.tile_names[index] for index, axis in enumerate(plan.loop_axes)}
    rows: list[ArrayAttr] = []
    for row in analysis_attr.data:
        if not isinstance(row, ArrayAttr):
            tile_module._raise_tile_error("TilePassUnsupportedOp", "tile.analysis must be a 2d array")
        exprs = [StringAttr(axis_to_tile.get(axis_index, "")) for axis_index, _ in enumerate(row.data)]
        rows.append(ArrayAttr(exprs))
    return ArrayAttr(rows)


class TileElewisePass(ModulePass):
    """`tile-elewise` 公开入口。

    创建者: 小李飞刀
    最后一次更改: 小李飞刀

    功能说明:
    - 保持稳定公开名 `tile-elewise`。
    - 只消费已有 `tile.analysis` / `tile.tile_exprs` 合同并生成 tile loop / view 结构。
    - 生成的 `tuner.param` 结果类型为 `!symbol.int<"...">`，便于下游 codegen 直接绑定 tile 因子。

    使用示例:
    - from xdsl.context import Context
    - from xdsl.dialects.builtin import ModuleOp
    - TileElewisePass().apply(Context(), module)

    关联文件:
    - spec: [spec/pass/lowering/tile_elewise.md](spec/pass/lowering/tile_elewise.md)
    - test: [test/pass/test_lowering_tile_elewise.py](test/pass/test_lowering_tile_elewise.py)
    - 功能实现: [kernel_gen/passes/lowering/tile_elewise.py](kernel_gen/passes/lowering/tile_elewise.py)
    """

    name = "tile-elewise"

    def apply(self: "TileElewisePass", ctx: Context, module: ModuleOp) -> None:
        """执行 `tile-elewise` ModulePass。

        创建者: 小李飞刀
        最后更改: 小李飞刀

        功能说明:
        - 只接受 `builtin.module`。
        - 对单函数输入按 elementwise/broadcast/matmul 计划改写。
        - 保留 rewritten op 的 `tile.analysis` 与 `tile.tile_exprs`，其中 `tile.tile_exprs` 仅对真实切分轴写入 tile 名称。
        - 不生成 `tile.step_value` / `kernel_split.tile_value` 旧桥接 op。

        使用示例:
        - TileElewisePass().apply(Context(), module)

        关联文件:
        - spec: [spec/pass/lowering/tile_elewise.md](spec/pass/lowering/tile_elewise.md)
        - test: [test/pass/test_lowering_tile_elewise.py](test/pass/test_lowering_tile_elewise.py)
        - 功能实现: [kernel_gen/passes/lowering/tile_elewise.py](kernel_gen/passes/lowering/tile_elewise.py)
        """

        del ctx
        if not isinstance(module, ModuleOp):
            tile_module._raise_tile_error("TilePassRequiresLoweredKernelIR", "module must be builtin.module")

        for op in module.ops:
            if not isinstance(op, tile_module.func.FuncOp):
                continue

            block = tile_module._get_single_block(op)
            tile_module._normalize_binary_elewise_compare_compat(block)
            tile_module._validate_input_contract(op, block)
            tile_module._validate_intermediate_materialization(op, block)

            return_op = block.last_op
            if not isinstance(return_op, tile_module.func.ReturnOp):
                tile_module._raise_tile_error(
                    "TilePassRequiresLoweredKernelIR",
                    f"function {op.sym_name.data} must terminate with func.return",
                )

            plans, ordered_tile_names = tile_module._plan_tile_ops(op, block, tile_reduce=False)
            if not plans:
                continue

            planned_ops = {plan.op for plan in plans}
            preserved_ops = [candidate for candidate in block.ops if candidate not in planned_ops and candidate is not return_op]

            tile_params: list[object] = []
            tile_values: dict[str, SSAValue] = {}
            for tile_name in ordered_tile_names:
                param = tile_module.TunerParamOp(SymbolValueType.from_expr(tile_name))
                name_hint = tile_module._tile_param_hint(tile_name)
                if name_hint is not None:
                    param.result.name_hint = name_hint
                tile_params.append(param)
                tile_values[tile_name] = param.result

            new_ops: list[object] = [*preserved_ops, *tile_params]
            for plan in plans:
                analysis_attr = plan.op.attributes.get("tile.analysis")
                if not isinstance(analysis_attr, ArrayAttr):
                    tile_module._raise_tile_error(
                        "TilePassUnsupportedOp",
                        f"function {op.sym_name.data} requires tile.analysis before tile-elewise",
                    )
                tile_exprs_attr = _build_tile_exprs_attr(plan, analysis_attr)
                plan.op.attributes["tile.analysis"] = analysis_attr
                plan.op.attributes["tile.tile_exprs"] = tile_exprs_attr

                if plan.kind == "elementwise":
                    new_ops.extend(tile_module._rewrite_elementwise_plan(plan, tile_values=tile_values))
                elif plan.kind == "broadcast":
                    new_ops.extend(tile_module._rewrite_broadcast_plan(plan, tile_values=tile_values))
                elif plan.kind == "matmul":
                    new_ops.extend(
                        tile_module._rewrite_matmul_plan(plan, tile_values=tile_values, tile_reduce=False)
                    )
                else:
                    tile_module._raise_tile_error("TilePassUnsupportedOp", f"unsupported tile op {plan.op.name}")

                plan.op.attributes["tile.analysis"] = analysis_attr
                plan.op.attributes["tile.tile_exprs"] = tile_exprs_attr

            new_ops.append(return_op)
            for candidate in list(block.ops):
                candidate.detach()
            block.add_ops(new_ops)


__all__ = ["TileElewisePass"]
