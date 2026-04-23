"""tile common helper canonical path.

创建者: 金铲铲大作战
最后一次更改: 金铲铲大作战

功能说明:
- 提供 tile family 共享 helper 的 canonical public path：`kernel_gen.tile.common`。
- S4 阶段先复用 `kernel_gen.passes.lowering.tile` 中已经稳定的 helper 实现，避免在 path 收口时同时做 logic rewrite。
- 旧路径 `kernel_gen.passes.lowering.tile` 仅保留兼容 helper 入口，不再作为长期默认依赖路径。

使用示例:
- from kernel_gen.tile import common as tile_common
- plans, ordered_tile_names = tile_common._plan_tile_ops(func_op, block, tile_reduce=False)

关联文件:
- spec: [spec/pass/lowering/tile.md](spec/pass/lowering/tile.md)
- test: [test/pass/test_lowering_tile.py](test/pass/test_lowering_tile.py)
- test: [test/pass/test_lowering_tile_private_helpers.py](test/pass/test_lowering_tile_private_helpers.py)
- 功能实现: [kernel_gen/tile/common.py](kernel_gen/tile/common.py)
"""

from __future__ import annotations

from kernel_gen.passes.lowering import tile as _legacy_tile

_EXPORTED_NAMES = [
    "TilePassError",
    "_raise_tile_error",
    "func",
    "TunerParamOp",
    "_TileOpPlan",
    "_get_single_block",
    "_collect_kernel_ops",
    "_is_bool_memory",
    "_normalize_binary_elewise_compare_compat",
    "_is_allowed_input_contract_op",
    "_validate_input_contract",
    "_uses_value_as_input",
    "_kernel_out_operand",
    "_validate_intermediate_materialization",
    "_symbol_expr_from_value",
    "_expr_to_dim_attr",
    "_row_major_stride_exprs",
    "_build_symbol_const",
    "_tile_param_hint",
    "_build_iter_type",
    "_build_loop_nest",
    "_collect_tile_ops",
    "_tile_op_kind",
    "_parse_tile_analysis_roles",
    "_plan_tile_ops",
    "_build_view_type_from_exprs",
    "_build_stride_values",
    "_build_view",
    "_rewrite_elementwise_plan",
    "_rewrite_broadcast_plan",
    "_rewrite_matmul_plan",
    "_is_reduce_kernel",
    "_classify_kernel_ops",
    "_collect_kernel_memory_operands",
    "_validate_tile_name_uniqueness",
    "_tile_analysis_attr",
    "_set_tile_analysis",
    "_clear_tile_analysis",
    "_build_elementwise_tile_roles",
    "_build_matmul_tile_roles",
    "_is_unit_dim",
    "_dim_equals",
    "_build_broadcast_tile_roles",
    "_annotate_tile_analysis",
]

for _name in _EXPORTED_NAMES:
    globals()[_name] = getattr(_legacy_tile, _name)

__all__ = list(_EXPORTED_NAMES)
