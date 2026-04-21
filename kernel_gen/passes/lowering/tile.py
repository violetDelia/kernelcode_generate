"""tile lowering helpers.

创建者: 小李飞刀
最后一次更改: 朽木露琪亚

功能说明:
- 为 `tile-analysis` / `tile-elewise` / `tile-reduce` 提供共享校验、分析和改写 helper。
- 统一维护 `tile.analysis` / `tile.tile_exprs` 合同与 tile loop/view 组装逻辑。
- 不再公开历史 pass 入口与旧 bridge 合同。

使用示例:
- from kernel_gen.passes.lowering import tile as tile_module
- plans, ordered_tile_names = tile_module._plan_tile_ops(func_op, block, tile_reduce=False)

关联文件:
- spec: [spec/pass/lowering/tile.md](spec/pass/lowering/tile.md)
- test: [test/pass/test_lowering_tile_analysis.py](test/pass/test_lowering_tile_analysis.py)
- test: [test/pass/test_lowering_tile_elewise.py](test/pass/test_lowering_tile_elewise.py)
- test: [test/pass/test_lowering_tile_reduce.py](test/pass/test_lowering_tile_reduce.py)
- 功能实现: [kernel_gen/passes/lowering/tile.py](kernel_gen/passes/lowering/tile.py)
"""

from __future__ import annotations

from dataclasses import dataclass

from xdsl.dialects import func
from xdsl.dialects.builtin import (
    ArrayAttr,
    IntAttr,
    IntegerAttr,
    StringAttr,
    UnregisteredOp,
    i1,
    i32,
)
from xdsl.ir import Attribute, Block, Operation, SSAValue

from kernel_gen.dialect.dma import DmaAllocOp, DmaFillOp, DmaViewOp
from kernel_gen.dialect.kernel import KernelBinaryElewiseOp, KernelMatmulOp
from kernel_gen.dialect.nn import NnMemorySpaceAttr, NnMemoryType
from kernel_gen.dialect.symbol import SymbolForOp, SymbolGetDimOp, SymbolIterType, SymbolValueType
from kernel_gen.dialect.tuner import TunerParamOp
from kernel_gen.symbol_variable.type import NumericType


class TilePassError(ValueError):
    """tile pass 的显式错误类型。

    创建者: 小李飞刀
    最后一次更改: 小李飞刀

    功能说明:
    - 统一承载 `TilePass*` 关键短语错误，便于测试与上层稳定匹配。

    使用示例:
    - raise TilePassError("TilePassUnsupportedOp: module has reduce op")

    关联文件:
    - spec: [spec/pass/lowering/tile.md](spec/pass/lowering/tile.md)
    - test: [test/pass/test_lowering_tile.py](test/pass/test_lowering_tile.py)
    - 功能实现: [kernel_gen/passes/lowering/tile.py](kernel_gen/passes/lowering/tile.py)
    """


def _raise_tile_error(keyword: str, detail: str) -> None:
    """抛出统一格式的 tile 错误。

    创建者: 小李飞刀
    最后一次更改: 小李飞刀

    功能说明:
    - 统一拼接 `TilePass*` 前缀，避免不同路径返回不一致短语。

    使用示例:
    - _raise_tile_error("TilePassUnsupportedOp", "reduce is not supported")

    关联文件:
    - spec: [spec/pass/lowering/tile.md](spec/pass/lowering/tile.md)
    - test: [test/pass/test_lowering_tile.py](test/pass/test_lowering_tile.py)
    - 功能实现: [kernel_gen/passes/lowering/tile.py](kernel_gen/passes/lowering/tile.py)
    """

    raise TilePassError(f"{keyword}: {detail}")


def _get_single_block(func_op: func.FuncOp) -> Block:
    """获取并校验单块函数体。

    创建者: 小李飞刀
    最后一次更改: 小李飞刀

    功能说明:
    - 当前实现仅支持单个 block 的 `func.func`。

    使用示例:
    - block = _get_single_block(func_op)

    关联文件:
    - spec: [spec/pass/lowering/tile.md](spec/pass/lowering/tile.md)
    - test: [test/pass/test_lowering_tile.py](test/pass/test_lowering_tile.py)
    - 功能实现: [kernel_gen/passes/lowering/tile.py](kernel_gen/passes/lowering/tile.py)
    """

    blocks = list(func_op.body.blocks)
    if len(blocks) != 1:
        _raise_tile_error(
            "TilePassRequiresLoweredKernelIR",
            f"function {func_op.sym_name.data} must contain exactly one block",
        )
    return blocks[0]


def _collect_kernel_ops(block: Block) -> list[Operation]:
    """收集函数体中的 kernel op。

    创建者: 小李飞刀
    最后一次更改: 小李飞刀

    功能说明:
    - 以 op.name 前缀 `kernel.` 作为识别条件。

    使用示例:
    - kernel_ops = _collect_kernel_ops(block)

    关联文件:
    - spec: [spec/pass/lowering/tile.md](spec/pass/lowering/tile.md)
    - test: [test/pass/test_lowering_tile.py](test/pass/test_lowering_tile.py)
    - 功能实现: [kernel_gen/passes/lowering/tile.py](kernel_gen/passes/lowering/tile.py)
    """

    return [op for op in block.ops if op.name.startswith("kernel.")]


def _is_bool_memory(value: SSAValue) -> bool:
    """判断 SSAValue 是否为布尔 memory。

    创建者: 金铲铲大作战
    最后一次更改: 金铲铲大作战

    功能说明:
    - 兼容 builtin `i1` 与 `NumericType.Bool` 两种布尔表达。

    使用示例:
    - if _is_bool_memory(value): ...

    关联文件:
    - spec: [spec/pass/lowering/tile.md](spec/pass/lowering/tile.md)
    - test: [test/pass/test_lowering_tile.py](test/pass/test_lowering_tile.py)
    - 功能实现: [kernel_gen/passes/lowering/tile.py](kernel_gen/passes/lowering/tile.py)
    """

    if not isinstance(value.type, NnMemoryType):
        return False
    return value.type.element_type == i1 or value.type.element_type == NumericType.Bool


def _normalize_binary_elewise_compare_compat(block: Block) -> None:
    """把旧 compare 文本顺序重排为当前 `out-first` 规范。

    创建者: 金铲铲大作战
    最后一次更改: 金铲铲大作战

    功能说明:
    - 只处理 compare kind 且第三个 operand 明确是布尔输出的旧文本。
    - 保持当前公开 API 与专属测试使用的 `out, lhs, rhs` 规范不变。
    - 重排时同步保留 `tile.analysis` 与 `tile.tile_exprs`，避免分析/表达信息在兼容路径中丢失。

    使用示例:
    - _normalize_binary_elewise_compare_compat(block)

    关联文件:
    - spec: [spec/pass/lowering/tile.md](spec/pass/lowering/tile.md)
    - test: [test/pass/test_lowering_tile.py](test/pass/test_lowering_tile.py)
    - 功能实现: [kernel_gen/passes/lowering/tile.py](kernel_gen/passes/lowering/tile.py)
    """

    compare_kinds = {"eq", "ne", "lt", "le", "gt", "ge"}
    for op in list(block.ops):
        if not isinstance(op, KernelBinaryElewiseOp):
            continue
        kind = getattr(op.kind, "data", None)
        if kind not in compare_kinds:
            continue
        if _is_bool_memory(op.out):
            continue
        if not _is_bool_memory(op.rhs):
            continue
        reordered = KernelBinaryElewiseOp(op.rhs, op.out, op.lhs, kind=op.kind, space=op.space)
        if "tile.analysis" in op.attributes:
            reordered.attributes["tile.analysis"] = op.attributes["tile.analysis"]
        if "tile.tile_exprs" in op.attributes:
            reordered.attributes["tile.tile_exprs"] = op.attributes["tile.tile_exprs"]
        block.insert_op_before(reordered, op)
        block.erase_op(op)


def _is_allowed_input_contract_op(op: Operation) -> bool:
    """判断输入 IR 是否命中 tile 的允许子集。

    创建者: 小李飞刀
    最后一次更改: 小李飞刀

    功能说明:
    - 允许已 lower 的 `kernel.*` / `dma.*` / `func.return`。
    - 允许 `tuner.param` / `symbol.get_dim` 作为 bridge op。

    使用示例:
    - if not _is_allowed_input_contract_op(op): ...

    关联文件:
    - spec: [spec/pass/lowering/tile.md](spec/pass/lowering/tile.md)
    - test: [test/pass/test_lowering_tile.py](test/pass/test_lowering_tile.py)
    - 功能实现: [kernel_gen/passes/lowering/tile.py](kernel_gen/passes/lowering/tile.py)
    """

    if op.name.startswith("kernel.") or op.name.startswith("dma."):
        return True
    if isinstance(op, (func.ReturnOp, TunerParamOp, SymbolGetDimOp)):
        return True
    return False


def _validate_input_contract(func_op: func.FuncOp, block: Block) -> None:
    """校验 tile pass 的输入合同。

    创建者: 小李飞刀
    最后一次更改: 小李飞刀

    功能说明:
    - 拒绝残留 `nn.*`。
    - 拒绝 memory-return ABI。
    - 拒绝 `func.call`。
    - 对非允许子集的 op 执行 fail-fast。

    使用示例:
    - _validate_input_contract(func_op, block)

    关联文件:
    - spec: [spec/pass/lowering/tile.md](spec/pass/lowering/tile.md)
    - test: [test/pass/test_lowering_tile.py](test/pass/test_lowering_tile.py)
    - 功能实现: [kernel_gen/passes/lowering/tile.py](kernel_gen/passes/lowering/tile.py)
    """

    if any(isinstance(output_type, NnMemoryType) for output_type in func_op.function_type.outputs.data):
        _raise_tile_error(
            "TilePassRequiresLoweredKernelIR",
            f"function {func_op.sym_name.data} still returns nn.memory results",
        )
    for op in block.ops:
        if op.name.startswith("nn."):
            _raise_tile_error(
                "TilePassRequiresLoweredKernelIR",
                f"function {func_op.sym_name.data} still contains {op.name}",
            )
        if isinstance(op, func.CallOp):
            _raise_tile_error(
                "TilePassRequiresLoweredKernelIR",
                f"function {func_op.sym_name.data} must not contain func.call in tile body",
            )
        if not _is_allowed_input_contract_op(op):
            _raise_tile_error(
                "TilePassRequiresLoweredKernelIR",
                "function "
                f"{func_op.sym_name.data} contains unsupported op {op.name}; "
                "only kernel/dma/func.return plus tuner.param/symbol.get_dim are allowed before tile",
            )


def _uses_value_as_input(op: Operation, value: SSAValue) -> bool:
    """判断 operation 是否把指定 SSA 作为输入消费。

    创建者: 小李飞刀
    最后一次更改: 小李飞刀

    功能说明:
    - 对 `kernel.*` op，最后一个 operand 视为 out，不算消费。
    - 其他 op 只要 operand 命中即视为消费。

    使用示例:
    - if _uses_value_as_input(op, alloc.result): ...

    关联文件:
    - spec: [spec/pass/lowering/tile.md](spec/pass/lowering/tile.md)
    - test: [test/pass/test_lowering_tile.py](test/pass/test_lowering_tile.py)
    - 功能实现: [kernel_gen/passes/lowering/tile.py](kernel_gen/passes/lowering/tile.py)
    """

    operands = list(op.operands)
    if op.name.startswith("kernel.") and operands:
        operands = operands[:-1]
    return any(SSAValue.get(operand) == value for operand in operands)


def _kernel_out_operand(op: Operation) -> SSAValue:
    """获取 kernel op 的 out operand。

    创建者: 小李飞刀
    最后一次更改: 小李飞刀

    功能说明:
    - 当前约定所有 `kernel.*` 的第一个 operand 为写出 buffer。

    使用示例:
    - out_value = _kernel_out_operand(kernel_op)

    关联文件:
    - spec: [spec/pass/lowering/tile.md](spec/pass/lowering/tile.md)
    - test: [test/pass/test_lowering_tile.py](test/pass/test_lowering_tile.py)
    - 功能实现: [kernel_gen/passes/lowering/tile.py](kernel_gen/passes/lowering/tile.py)
    """

    return SSAValue.get(op.operands[0])


def _validate_intermediate_materialization(func_op: func.FuncOp, block: Block) -> None:
    """校验跨 stage 中间值是否物化为 carry memory。

    创建者: 小李飞刀
    最后一次更改: 小李飞刀

    功能说明:
    - 若某个 `kernel.*` 的 out buffer 被后续 op 当作输入消费，则它是跨 stage 中间值。
    - 跨 stage 中间值必须来自 `dma.alloc`；否则视为输入合同不满足。
    - 来自 `dma.alloc` 的 carry memory 若未被后续 stage 消费，报 `TilePassDeadCarryMemory`。

    使用示例:
    - _validate_intermediate_materialization(func_op, block)

    关联文件:
    - spec: [spec/pass/lowering/tile.md](spec/pass/lowering/tile.md)
    - test: [test/pass/test_lowering_tile.py](test/pass/test_lowering_tile.py)
    - 功能实现: [kernel_gen/passes/lowering/tile.py](kernel_gen/passes/lowering/tile.py)
    """

    body_ops = list(block.ops)
    kernel_ops = [op for op in body_ops if op.name.startswith("kernel.")]
    consumed_carry_allocs: set[DmaAllocOp] = set()
    written_carry_allocs: set[DmaAllocOp] = set()

    for kernel_op in kernel_ops:
        out_value = _kernel_out_operand(kernel_op)
        owner = out_value.owner if isinstance(out_value.owner, Operation) else None
        if isinstance(owner, DmaAllocOp):
            written_carry_allocs.add(owner)
        if any(_uses_value_as_input(later_op, out_value) for later_op in body_ops[body_ops.index(kernel_op) + 1 :]):
            if not isinstance(owner, DmaAllocOp):
                _raise_tile_error(
                    "TilePassRequiresLoweredKernelIR",
                    f"function {func_op.sym_name.data} reuses {kernel_op.name} out buffer without dma.alloc carry memory",
                )
            consumed_carry_allocs.add(owner)

    dead_allocs = written_carry_allocs - consumed_carry_allocs
    if dead_allocs:
        alloc = next(iter(dead_allocs))
        _raise_tile_error(
            "TilePassDeadCarryMemory",
            f"function {func_op.sym_name.data} leaves carry memory {alloc.name} without later consumption",
        )


@dataclass(frozen=True)
class _TileOpPlan:
    """tile-only 的单 op 计划信息。

    创建者: 小李飞刀
    最后一次更改: 小李飞刀

    功能说明:
    - 记录 tile-only 阶段对单个 op 的改写计划。
    - 保存 op 类型、loop 轴顺序、tile 参数名称与 broadcast 角色矩阵。

    使用示例:
    - plan = _TileOpPlan(op=op, kind="elementwise", loop_axes=[0, 1], tile_names=["TILE_D0", "TILE_D1"])

    关联文件:
    - spec: [spec/pass/lowering/tile.md](spec/pass/lowering/tile.md)
    - test: [test/pass/test_lowering_tile.py](test/pass/test_lowering_tile.py)
    - 功能实现: [kernel_gen/passes/lowering/tile.py](kernel_gen/passes/lowering/tile.py)
    """

    op: Operation
    kind: str
    loop_axes: list[int]
    tile_names: list[str]
    reference_operand_index: int = 0
    roles: list[list[str]] | None = None
    reduce_tile_name: str | None = None


def _symbol_expr_from_value(value: SSAValue) -> str:
    """从 symbol value SSA 提取表达式字符串。

    创建者: 小李飞刀
    最后一次更改: 小李飞刀

    功能说明:
    - 仅支持 `!symbol.int<"...">` 类型。
    - 返回对应的表达式字符串，用于构造 `symbol.iter` 与类型条目。

    使用示例:
    - expr = _symbol_expr_from_value(step_value)

    关联文件:
    - spec: [spec/dialect/symbol.md](spec/dialect/symbol.md)
    - test: [test/dialect/test_symbol_dialect.py](test/dialect/test_symbol_dialect.py)
    - 功能实现: [kernel_gen/passes/lowering/tile.py](kernel_gen/passes/lowering/tile.py)
    """

    value_type = value.type
    if not isinstance(value_type, SymbolValueType):
        _raise_tile_error("TilePassUnsupportedOp", "symbol value type must be !symbol.int")
    return value_type.expr.expr.data


def _expr_to_dim_attr(expr: str) -> Attribute:
    """把表达式字符串转换为 memory 维度 attribute。

    创建者: 小李飞刀
    最后一次更改: 小李飞刀

    功能说明:
    - 纯数字字符串转换为 `IntAttr`。
    - 其他表达式转换为 `StringAttr`。

    使用示例:
    - attr = _expr_to_dim_attr("TILE_D0")

    关联文件:
    - spec: [spec/dialect/nn.md](spec/dialect/nn.md)
    - test: [test/dialect/test_nn_dialect.py](test/dialect/test_nn_dialect.py)
    - 功能实现: [kernel_gen/passes/lowering/tile.py](kernel_gen/passes/lowering/tile.py)
    """

    expr = expr.strip()
    if expr.lstrip("-").isdigit():
        return IntAttr(int(expr))
    return StringAttr(expr)


def _row_major_stride_exprs(shape_exprs: list[str]) -> list[str]:
    """生成按行主序的 stride 表达式列表。

    创建者: 小李飞刀
    最后一次更改: 小李飞刀

    功能说明:
    - rank=1 时 stride 为 `1`。
    - rank>=2 时 stride[i] 取 shape[i+1]，最后一维为 `1`。
    - 该规则与当前 tile expectation 的 rank<=2 行为保持一致。

    使用示例:
    - stride_exprs = _row_major_stride_exprs(["TILE_D0", "TILE_D1"])

    关联文件:
    - spec: [spec/dialect/dma.md](spec/dialect/dma.md)
    - test: [test/pass/test_lowering_tile.py](test/pass/test_lowering_tile.py)
    - 功能实现: [kernel_gen/passes/lowering/tile.py](kernel_gen/passes/lowering/tile.py)
    """

    if not shape_exprs:
        return []
    if len(shape_exprs) == 1:
        return ["1"]
    stride_exprs: list[str] = []
    for index in range(len(shape_exprs)):
        if index == len(shape_exprs) - 1:
            stride_exprs.append("1")
        else:
            stride_exprs.append(shape_exprs[index + 1])
    return stride_exprs


def _build_symbol_const(value: int) -> Operation:
    """构造通用格式的 symbol.const op。

    创建者: 小李飞刀
    最后一次更改: 小李飞刀

    功能说明:
    - 使用 `UnregisteredOp` 生成 `"symbol.const"()` 的通用打印格式。
    - 返回值类型为 `!symbol.int<"...">`，满足 tile expectation。

    使用示例:
    - const0 = _build_symbol_const(0)

    关联文件:
    - spec: [spec/dialect/symbol.md](spec/dialect/symbol.md)
    - test: [test/pass/test_lowering_tile.py](test/pass/test_lowering_tile.py)
    - 功能实现: [kernel_gen/passes/lowering/tile.py](kernel_gen/passes/lowering/tile.py)
    """

    result_type = SymbolValueType.from_expr(str(value))
    return UnregisteredOp.with_name("symbol.const").create(
        operands=[],
        result_types=[result_type],
        properties={"value": IntegerAttr.from_int_and_width(value, 64)},
    )


def _tile_param_hint(tile_name: str) -> str | None:
    """生成 tile param 的 SSA name_hint。

    创建者: 小李飞刀
    最后一次更改: 小李飞刀

    功能说明:
    - 仅为 `TILE_B*` / `TILE_M*` / `TILE_E*` 生成稳定的提示名。
    - 返回值用于输出 `%b0` / `%m0` / `%e0` 形式，匹配 expectation。

    使用示例:
    - _tile_param_hint("TILE_B0") == "b0"
    - _tile_param_hint("TILE_D0") is None

    关联文件:
    - spec: [spec/pass/lowering/tile.md](spec/pass/lowering/tile.md)
    - test: [test/pass/test_lowering_tile.py](test/pass/test_lowering_tile.py)
    - 功能实现: [kernel_gen/passes/lowering/tile.py](kernel_gen/passes/lowering/tile.py)
    """

    if not tile_name.startswith("TILE_"):
        return None
    suffix = tile_name[len("TILE_") :]
    if len(suffix) < 2:
        return None
    prefix = suffix[0]
    index = suffix[1:]
    if prefix not in {"B", "M", "E"}:
        return None
    if not index.isdigit():
        return None
    return f"{prefix.lower()}{index}"


def _build_iter_type(start: SSAValue, end: SSAValue, step: SSAValue) -> SymbolIterType:
    """构造 symbol.iter 的 range 类型。

    创建者: 小李飞刀
    最后一次更改: 小李飞刀

    功能说明:
    - 以 start/end/step 的 symbol 表达式构造 `!symbol.iter<...>`。
    - 供 symbol.for 的块参数使用。

    使用示例:
    - iter_type = _build_iter_type(start, end, step)

    关联文件:
    - spec: [spec/dialect/symbol.md](spec/dialect/symbol.md)
    - test: [test/dialect/test_symbol_dialect.py](test/dialect/test_symbol_dialect.py)
    - 功能实现: [kernel_gen/passes/lowering/tile.py](kernel_gen/passes/lowering/tile.py)
    """

    return SymbolIterType.from_bounds(
        _symbol_expr_from_value(start),
        _symbol_expr_from_value(end),
        _symbol_expr_from_value(step),
    )


def _build_loop_nest(
    loop_specs: list[tuple[SSAValue, SSAValue, SSAValue]],
) -> tuple[SymbolForOp | None, Block | None, list[SSAValue]]:
    """构造多层嵌套的 symbol.for。

    创建者: 小李飞刀
    最后一次更改: 小李飞刀

    功能说明:
    - 依次构造 outer->inner 的 symbol.for 嵌套结构。
    - 返回最外层 loop、最内层 block 以及 loop 迭代变量列表。

    使用示例:
    - outer, inner, vars = _build_loop_nest([(start, end, step)])

    关联文件:
    - spec: [spec/dialect/symbol.md](spec/dialect/symbol.md)
    - test: [test/pass/test_lowering_tile.py](test/pass/test_lowering_tile.py)
    - 功能实现: [kernel_gen/passes/lowering/tile.py](kernel_gen/passes/lowering/tile.py)
    """

    if not loop_specs:
        return None, None, []

    outer_loop: SymbolForOp | None = None
    current_block: Block | None = None
    loop_vars: list[SSAValue] = []
    for start, end, step in loop_specs:
        iter_type = _build_iter_type(start, end, step)
        loop_block = Block(arg_types=[iter_type])
        loop_op = SymbolForOp(start, end, step, loop_block)
        if outer_loop is None:
            outer_loop = loop_op
        else:
            assert current_block is not None
            current_block.add_op(loop_op)
        current_block = loop_block
        loop_vars.append(loop_block.args[0])
    return outer_loop, current_block, loop_vars


def _collect_tile_ops(block: Block) -> list[Operation]:
    """收集待 tile 改写的 op 列表。

    创建者: 小李飞刀
    最后一次更改: 小李飞刀

    功能说明:
    - 返回携带 `tile.analysis` 的 kernel.* 与 dma.broadcast。
    - 保持原始顺序，用于稳定的 tuner.param 排序。

    使用示例:
    - ops = _collect_tile_ops(block)

    关联文件:
    - spec: [spec/pass/lowering/tile.md](spec/pass/lowering/tile.md)
    - test: [test/pass/test_lowering_tile.py](test/pass/test_lowering_tile.py)
    - 功能实现: [kernel_gen/passes/lowering/tile.py](kernel_gen/passes/lowering/tile.py)
    """

    tile_ops: list[Operation] = []
    for op in block.ops:
        if "tile.analysis" not in op.attributes:
            continue
        if op.name == "dma.broadcast" or op.name.startswith("kernel."):
            tile_ops.append(op)
        else:
            _raise_tile_error("TilePassUnsupportedOp", f"unsupported tile op {op.name}")
    return tile_ops


def _tile_op_kind(op: Operation) -> str:
    """归类 tile op 类型。

    创建者: 小李飞刀
    最后一次更改: 小李飞刀

    功能说明:
    - 返回 `elementwise` / `broadcast` / `matmul` 三类之一。

    使用示例:
    - kind = _tile_op_kind(op)

    关联文件:
    - spec: [spec/pass/lowering/tile.md](spec/pass/lowering/tile.md)
    - test: [test/pass/test_lowering_tile.py](test/pass/test_lowering_tile.py)
    - 功能实现: [kernel_gen/passes/lowering/tile.py](kernel_gen/passes/lowering/tile.py)
    """

    if op.name == "dma.broadcast":
        return "broadcast"
    if op.name == "kernel.matmul":
        return "matmul"
    if op.name.startswith("kernel.reduce"):
        _raise_tile_error("TilePassUnsupportedOp", "reduce kernel op is not supported")
    if op.name.startswith("kernel."):
        return "elementwise"
    _raise_tile_error("TilePassUnsupportedOp", f"unsupported tile op {op.name}")
    return "elementwise"


def _parse_tile_analysis_roles(op: Operation) -> list[list[str]]:
    """解析 tile.analysis 角色矩阵。

    创建者: 小李飞刀
    最后一次更改: 小李飞刀

    功能说明:
    - 将 `ArrayAttr(ArrayAttr(StringAttr))` 解析为二维字符串列表。
    - 任一维度不满足时抛出 TilePassUnsupportedOp。

    使用示例:
    - roles = _parse_tile_analysis_roles(op)

    关联文件:
    - spec: [spec/pass/lowering/tile.md](spec/pass/lowering/tile.md)
    - test: [test/pass/test_lowering_tile.py](test/pass/test_lowering_tile.py)
    - 功能实现: [kernel_gen/passes/lowering/tile.py](kernel_gen/passes/lowering/tile.py)
    """

    attr = op.attributes.get("tile.analysis")
    if not isinstance(attr, ArrayAttr):
        _raise_tile_error("TilePassUnsupportedOp", "tile.analysis must be an array")
    roles: list[list[str]] = []
    for row in attr.data:
        if not isinstance(row, ArrayAttr):
            _raise_tile_error("TilePassUnsupportedOp", "tile.analysis must be a 2d array")
        row_roles: list[str] = []
        for item in row.data:
            if not isinstance(item, StringAttr):
                _raise_tile_error("TilePassUnsupportedOp", "tile.analysis entries must be string")
            row_roles.append(item.data)
        roles.append(row_roles)
    return roles


def _plan_tile_ops(
    func_op: func.FuncOp,
    block: Block,
    *,
    tile_reduce: bool,
) -> tuple[list[_TileOpPlan], list[str]]:
    """生成 tile-only 的 op 计划与 tile 参数顺序。

    创建者: 小李飞刀
    最后一次更改: 小李飞刀

    功能说明:
    - 按 block 顺序生成 `_TileOpPlan`。
    - 输出按出现顺序展开的 tile 参数名称列表。

    使用示例:
    - plans, tile_names = _plan_tile_ops(func_op, block, tile_reduce=True)

    关联文件:
    - spec: [spec/pass/lowering/tile.md](spec/pass/lowering/tile.md)
    - test: [test/pass/test_lowering_tile.py](test/pass/test_lowering_tile.py)
    - 功能实现: [kernel_gen/passes/lowering/tile.py](kernel_gen/passes/lowering/tile.py)
    """

    tile_ops = _collect_tile_ops(block)
    multi_op = len(tile_ops) > 1
    counters: dict[str, int] = {"D": 0, "E": 0, "B": 0, "M": 0, "R": 0}
    plans: list[_TileOpPlan] = []
    ordered_tile_names: list[str] = []

    for op in tile_ops:
        kind = _tile_op_kind(op)
        if kind == "elementwise":
            memory_values = [SSAValue.get(operand) for operand in op.operands if isinstance(SSAValue.get(operand).type, NnMemoryType)]
            if not memory_values:
                _raise_tile_error("TilePassUnsupportedOp", "elementwise requires memory operands")
            reference = memory_values[0]
            if not isinstance(reference.type, NnMemoryType):
                _raise_tile_error("TilePassRankMismatch", "elementwise reference must be nn.memory")
            rank = len(reference.type.shape.data)
            prefix = "D" if not multi_op else "E"
            start_index = counters[prefix]
            tile_names = [f"TILE_{prefix}{start_index + axis}" for axis in range(rank)]
            counters[prefix] = start_index + rank
            reference_operand_index = len(memory_values) - 1 if multi_op else 0
            plans.append(
                _TileOpPlan(
                    op=op,
                    kind=kind,
                    loop_axes=list(range(rank)),
                    tile_names=tile_names,
                    reference_operand_index=reference_operand_index,
                )
            )
            ordered_tile_names.extend(tile_names)
            continue

        if kind == "broadcast":
            roles = _parse_tile_analysis_roles(op)
            if not roles:
                _raise_tile_error("TilePassUnsupportedOp", "broadcast requires tile.analysis roles")
            rank = len(roles[0])
            loop_axes = [
                axis
                for axis in range(rank)
                if all(axis < len(row) and row[axis] != "expand" for row in roles)
            ]
            prefix = "D" if not multi_op else "B"
            start_index = counters[prefix]
            tile_names = [f"TILE_{prefix}{start_index + idx}" for idx in range(len(loop_axes))]
            counters[prefix] = start_index + len(loop_axes)
            plans.append(
                _TileOpPlan(
                    op=op,
                    kind=kind,
                    loop_axes=loop_axes,
                    tile_names=tile_names,
                    roles=roles,
                )
            )
            ordered_tile_names.extend(tile_names)
            continue

        if kind == "matmul":
            prefix = "D" if not multi_op else "M"
            start_index = counters[prefix]
            tile_names = [f"TILE_{prefix}{start_index}", f"TILE_{prefix}{start_index + 1}"]
            counters[prefix] = start_index + 2
            reduce_tile_name: str | None = None
            if tile_reduce:
                reduce_index = counters["R"]
                reduce_tile_name = f"TILE_R{reduce_index}"
                counters["R"] = reduce_index + 1
            plans.append(
                _TileOpPlan(
                    op=op,
                    kind=kind,
                    loop_axes=[0, 1],
                    tile_names=tile_names,
                    reduce_tile_name=reduce_tile_name,
                )
            )
            ordered_tile_names.extend(tile_names)
            if reduce_tile_name is not None:
                ordered_tile_names.append(reduce_tile_name)
            continue

        _raise_tile_error("TilePassUnsupportedOp", f"unsupported tile op {op.name}")

    _validate_tile_name_uniqueness(ordered_tile_names)
    return plans, ordered_tile_names


def _build_view_type_from_exprs(source_type: NnMemoryType, shape_exprs: list[str]) -> NnMemoryType:
    """构造 dma.view 的结果类型。

    创建者: 小李飞刀
    最后一次更改: 小李飞刀

    功能说明:
    - 根据 shape_exprs 生成 shape/stride 的 `StringAttr`/`IntAttr` 组合。
    - stride 使用当前 tile expectation 的行主序规则。

    使用示例:
    - view_type = _build_view_type_from_exprs(src_type, ["TILE_D0", "TILE_D1"])

    关联文件:
    - spec: [spec/dialect/dma.md](spec/dialect/dma.md)
    - test: [test/pass/test_lowering_tile.py](test/pass/test_lowering_tile.py)
    - 功能实现: [kernel_gen/passes/lowering/tile.py](kernel_gen/passes/lowering/tile.py)
    """

    shape_attrs = ArrayAttr([_expr_to_dim_attr(expr) for expr in shape_exprs])
    stride_exprs = _row_major_stride_exprs(shape_exprs)
    stride_attrs = ArrayAttr([_expr_to_dim_attr(expr) for expr in stride_exprs])
    return NnMemoryType(shape_attrs, stride_attrs, source_type.element_type, source_type.space)


def _build_stride_values(shape_values: list[SSAValue], const_one: SSAValue) -> list[SSAValue]:
    """构造 dma.view stride 的 SSA 列表。

    创建者: 小李飞刀
    最后一次更改: 小李飞刀

    功能说明:
    - rank=1 返回 `[1]`。
    - rank>=2 返回 `[shape[1], 1]`。

    使用示例:
    - stride_values = _build_stride_values(shape_values, const_one)

    关联文件:
    - spec: [spec/dialect/dma.md](spec/dialect/dma.md)
    - test: [test/pass/test_lowering_tile.py](test/pass/test_lowering_tile.py)
    - 功能实现: [kernel_gen/passes/lowering/tile.py](kernel_gen/passes/lowering/tile.py)
    """

    if not shape_values:
        return []
    if len(shape_values) == 1:
        return [const_one]
    return [shape_values[1], const_one]


def _build_view(
    source: SSAValue,
    *,
    offsets: list[SSAValue],
    shape_values: list[SSAValue],
    const_one: SSAValue,
) -> DmaViewOp:
    """构造 dma.view 并推导结果类型。

    创建者: 小李飞刀
    最后一次更改: 小李飞刀

    功能说明:
    - 根据 shape 值推导 view 的 memory type。
    - stride 使用当前 tile expectation 的行主序规则。

    使用示例:
    - view = _build_view(src, offsets=[off0], shape_values=[shape0], const_one=one)

    关联文件:
    - spec: [spec/dialect/dma.md](spec/dialect/dma.md)
    - test: [test/pass/test_lowering_tile.py](test/pass/test_lowering_tile.py)
    - 功能实现: [kernel_gen/passes/lowering/tile.py](kernel_gen/passes/lowering/tile.py)
    """

    if not isinstance(source.type, NnMemoryType):
        _raise_tile_error("TilePassRankMismatch", "dma.view source must be nn.memory")
    shape_exprs = [_symbol_expr_from_value(value) for value in shape_values]
    result_type = _build_view_type_from_exprs(source.type, shape_exprs)
    stride_values = _build_stride_values(shape_values, const_one)
    return DmaViewOp(source, offsets, shape_values, stride_values, result_type)


def _rewrite_elementwise_plan(
    plan: _TileOpPlan,
    *,
    tile_values: dict[str, SSAValue],
) -> list[Operation]:
    """按 elementwise 计划生成 tile 改写 ops。

    创建者: 小李飞刀
    最后一次更改: 小李飞刀

    功能说明:
    - 生成 `symbol.const` / `symbol.get_dim` / `symbol.for` / `dma.view`。
    - 将原 kernel.* op 迁移至最内层 loop。

    使用示例:
    - ops = _rewrite_elementwise_plan(plan, tile_values=tile_values)

    关联文件:
    - spec: [spec/pass/lowering/tile.md](spec/pass/lowering/tile.md)
    - test: [test/pass/test_lowering_tile.py](test/pass/test_lowering_tile.py)
    - 功能实现: [kernel_gen/passes/lowering/tile.py](kernel_gen/passes/lowering/tile.py)
    """

    op = plan.op
    memory_values = [SSAValue.get(operand) for operand in op.operands if isinstance(SSAValue.get(operand).type, NnMemoryType)]
    if not memory_values:
        _raise_tile_error("TilePassUnsupportedOp", "elementwise requires memory operands")
    reference_index = plan.reference_operand_index
    if reference_index < 0 or reference_index >= len(memory_values):
        reference_index = 0
    reference = memory_values[reference_index]
    if not isinstance(reference.type, NnMemoryType):
        _raise_tile_error("TilePassRankMismatch", "elementwise reference must be nn.memory")
    rank = len(reference.type.shape.data)
    for value in memory_values:
        mem_type = value.type
        if not isinstance(mem_type, NnMemoryType):
            _raise_tile_error("TilePassRankMismatch", "elementwise operands must be nn.memory")
        if len(mem_type.shape.data) != rank:
            _raise_tile_error("TilePassRankMismatch", "elementwise operands must share rank")

    helper_ops: list[Operation] = []
    start_values: list[SSAValue] = []
    end_values: list[SSAValue] = []
    for axis in range(rank):
        const0 = _build_symbol_const(0)
        end = SymbolGetDimOp(reference, axis)
        helper_ops.extend([const0, end])
        start_values.append(const0.results[0])
        end_values.append(end.result)

    loop_specs = [
        (start_values[axis], end_values[axis], tile_values[plan.tile_names[axis]])
        for axis in range(rank)
    ]
    outer_loop, inner_block, loop_vars = _build_loop_nest(loop_specs)
    if outer_loop is None or inner_block is None:
        return helper_ops

    const_one = _build_symbol_const(1)
    inner_block.add_op(const_one)
    loop_var_map = {axis: loop_vars[axis] for axis in range(rank)}

    view_map: dict[SSAValue, SSAValue] = {}
    for value in memory_values:
        offsets = [loop_var_map[axis] for axis in range(rank)]
        shape_values = [tile_values[plan.tile_names[axis]] for axis in range(rank)]
        view = _build_view(value, offsets=offsets, shape_values=shape_values, const_one=const_one.results[0])
        inner_block.add_op(view)
        view_map[value] = view.result

    op.detach()
    op.attributes.pop("tile.analysis", None)
    for index, operand in enumerate(op.operands):
        value = SSAValue.get(operand)
        if value in view_map:
            op.operands[index] = view_map[value]
    inner_block.add_op(op)
    helper_ops.append(outer_loop)
    return helper_ops


def _rewrite_broadcast_plan(
    plan: _TileOpPlan,
    *,
    tile_values: dict[str, SSAValue],
) -> list[Operation]:
    """按 broadcast 计划生成 tile 改写 ops。

    创建者: 小李飞刀
    最后一次更改: 朽木露琪亚

    功能说明:
    - 对 `dma.broadcast` 生成 loop/view 并插入至最内层。
    - target view 按 target rank 构造，source view 保持 source 自身 rank。
    - expand 维度不再把低 rank source 强行补成高 rank `dma.view`。

    使用示例:
    - ops = _rewrite_broadcast_plan(plan, tile_values=tile_values)

    关联文件:
    - spec: [spec/pass/lowering/tile.md](spec/pass/lowering/tile.md)
    - test: [test/pass/test_lowering_tile.py](test/pass/test_lowering_tile.py)
    - 功能实现: [kernel_gen/passes/lowering/tile.py](kernel_gen/passes/lowering/tile.py)
    """

    op = plan.op
    roles = plan.roles or _parse_tile_analysis_roles(op)
    if roles is None:
        _raise_tile_error("TilePassUnsupportedOp", "broadcast requires tile.analysis roles")
    if len(roles) != 2:
        _raise_tile_error("TilePassUnsupportedOp", "broadcast requires two operands")
    target = SSAValue.get(op.operands[0])
    source = SSAValue.get(op.operands[1])
    if not isinstance(target.type, NnMemoryType):
        _raise_tile_error("TilePassRankMismatch", "broadcast target must be nn.memory")
    rank = len(target.type.shape.data)
    if any(len(row) != rank for row in roles):
        _raise_tile_error("TilePassRankMismatch", "broadcast roles must match rank")

    helper_ops: list[Operation] = []
    start_values: list[SSAValue] = []
    end_values: list[SSAValue] = []
    for axis in range(rank):
        const0 = _build_symbol_const(0)
        end = SymbolGetDimOp(target, axis)
        helper_ops.extend([const0, end])
        start_values.append(const0.results[0])
        end_values.append(end.result)

    loop_specs: list[tuple[SSAValue, SSAValue, SSAValue]] = []
    loop_axis_to_tile: dict[int, str] = {}
    for loop_index, axis in enumerate(plan.loop_axes):
        tile_name = plan.tile_names[loop_index]
        loop_axis_to_tile[axis] = tile_name
        loop_specs.append((start_values[axis], end_values[axis], tile_values[tile_name]))

    outer_loop, inner_block, loop_vars = _build_loop_nest(loop_specs)
    if outer_loop is None or inner_block is None:
        op.detach()
        op.attributes.pop("tile.analysis", None)
        helper_ops.append(op)
        return helper_ops

    const_one = _build_symbol_const(1)
    inner_block.add_op(const_one)
    loop_var_map = {axis: loop_vars[index] for index, axis in enumerate(plan.loop_axes)}
    source_target_axis_map: dict[int, int] = {}
    source_expand_dims: dict[int, SSAValue] = {}
    if isinstance(source.type, NnMemoryType):
        source_rank = len(source.type.shape.data)
        pad = rank - source_rank
        if pad < 0:
            _raise_tile_error("TilePassRankMismatch", "broadcast source rank must be <= target rank")
        for source_axis in range(source_rank):
            target_axis = pad + source_axis
            source_target_axis_map[target_axis] = source_axis
            if roles[1][target_axis] == "expand":
                source_dim = SymbolGetDimOp(source, source_axis)
                helper_ops.append(source_dim)
                source_expand_dims[target_axis] = source_dim.result

    def _build_target_view(value: SSAValue, operand_index: int) -> DmaViewOp:
        offsets: list[SSAValue] = []
        shape_values: list[SSAValue] = []
        for axis in range(rank):
            if axis in loop_var_map:
                offsets.append(loop_var_map[axis])
            else:
                offsets.append(start_values[axis])
            role = roles[operand_index][axis]
            if role == "expand":
                shape_values.append(const_one.results[0])
            elif axis in loop_axis_to_tile:
                shape_values.append(tile_values[loop_axis_to_tile[axis]])
            else:
                shape_values.append(end_values[axis])
        return _build_view(value, offsets=offsets, shape_values=shape_values, const_one=const_one.results[0])

    def _build_source_view(value: SSAValue) -> DmaViewOp:
        if not isinstance(value.type, NnMemoryType):
            _raise_tile_error("TilePassRankMismatch", "broadcast source must be nn.memory")
        source_offsets: list[SSAValue] = []
        source_shape_values: list[SSAValue] = []
        for target_axis in range(rank):
            if target_axis not in source_target_axis_map:
                continue
            role = roles[1][target_axis]
            if target_axis in loop_var_map and role != "expand":
                source_offsets.append(loop_var_map[target_axis])
                source_shape_values.append(tile_values[loop_axis_to_tile[target_axis]])
                continue
            source_offsets.append(start_values[target_axis])
            source_shape_values.append(source_expand_dims.get(target_axis, end_values[target_axis]))
        return _build_view(
            value,
            offsets=source_offsets,
            shape_values=source_shape_values,
            const_one=const_one.results[0],
        )

    target_view = _build_target_view(target, 0)
    source_view = _build_source_view(source)
    inner_block.add_ops([target_view, source_view])

    op.detach()
    op.attributes.pop("tile.analysis", None)
    op.operands[0] = target_view.result
    op.operands[1] = source_view.result
    inner_block.add_op(op)
    helper_ops.append(outer_loop)
    return helper_ops


def _rewrite_matmul_plan(
    plan: _TileOpPlan,
    *,
    tile_values: dict[str, SSAValue],
    tile_reduce: bool,
) -> list[Operation]:
    """按 matmul 计划生成 tile 改写 ops。

    创建者: 小李飞刀
    最后一次更改: 小李飞刀

    功能说明:
    - 生成 M/N（以及可选 K）循环结构。
    - tile-reduce=true 时插入 `dma.fill` 与 reduce 累加逻辑。

    使用示例:
    - ops = _rewrite_matmul_plan(plan, tile_values=tile_values, tile_reduce=True)

    关联文件:
    - spec: [spec/pass/lowering/tile.md](spec/pass/lowering/tile.md)
    - test: [test/pass/test_lowering_tile.py](test/pass/test_lowering_tile.py)
    - 功能实现: [kernel_gen/passes/lowering/tile.py](kernel_gen/passes/lowering/tile.py)
    """

    op = plan.op
    tile_analysis_attr = op.attributes.get("tile.analysis")
    tile_exprs_attr = op.attributes.get("tile.tile_exprs")

    def _copy_tile_attrs(target_op: Operation) -> None:
        if tile_analysis_attr is not None:
            target_op.attributes["tile.analysis"] = tile_analysis_attr
        if tile_exprs_attr is not None:
            target_op.attributes["tile.tile_exprs"] = tile_exprs_attr

    out = SSAValue.get(op.operands[0])
    lhs = SSAValue.get(op.operands[1])
    rhs = SSAValue.get(op.operands[2])
    if not (isinstance(lhs.type, NnMemoryType) and isinstance(rhs.type, NnMemoryType) and isinstance(out.type, NnMemoryType)):
        _raise_tile_error("TilePassRankMismatch", "matmul operands must be nn.memory")
    space_attr = op.attributes.get("space")
    space = space_attr if isinstance(space_attr, NnMemorySpaceAttr) else out.type.space

    tile_m = plan.tile_names[0]
    tile_n = plan.tile_names[1]
    helper_ops: list[Operation] = []

    const0_m = _build_symbol_const(0)
    dim_m = SymbolGetDimOp(lhs, 0)
    const0_n = _build_symbol_const(0)
    dim_n = SymbolGetDimOp(rhs, 1)
    dim_k = SymbolGetDimOp(lhs, 1)
    helper_ops.extend([const0_m, dim_m, const0_n, dim_n, dim_k])

    loop_specs = [
        (const0_m.results[0], dim_m.result, tile_values[tile_m]),
        (const0_n.results[0], dim_n.result, tile_values[tile_n]),
    ]
    outer_loop, inner_block, loop_vars = _build_loop_nest(loop_specs)
    if outer_loop is None or inner_block is None:
        return helper_ops

    const_one = _build_symbol_const(1)
    inner_block.add_op(const_one)
    m_var, n_var = loop_vars

    if tile_reduce and plan.reduce_tile_name is not None:
        out_view = _build_view(
            out,
            offsets=[m_var, n_var],
            shape_values=[tile_values[tile_m], tile_values[tile_n]],
            const_one=const_one.results[0],
        )
        inner_block.add_op(out_view)
        if isinstance(out_view.result.type, NnMemoryType) and out_view.result.type.element_type == i32:
            fill_op = DmaFillOp(out_view.result, const0_m.results[0])
        else:
            fill_op = UnregisteredOp.with_name("dma.fill").create(
                operands=[out_view.result, const0_m.results[0]],
                result_types=[],
            )
        inner_block.add_op(fill_op)
        reduce_step = tile_values[plan.reduce_tile_name]
        reduce_loop_specs = [
            (const0_m.results[0], dim_k.result, reduce_step),
        ]
        reduce_loop, reduce_block, reduce_vars = _build_loop_nest(reduce_loop_specs)
        if reduce_loop is not None and reduce_block is not None:
            k_var = reduce_vars[0]
            lhs_view = _build_view(
                lhs,
                offsets=[m_var, k_var],
                shape_values=[tile_values[tile_m], reduce_step],
                const_one=const_one.results[0],
            )
            rhs_view = _build_view(
                rhs,
                offsets=[k_var, n_var],
                shape_values=[reduce_step, tile_values[tile_n]],
                const_one=const_one.results[0],
            )
            reduce_block.add_ops([lhs_view, rhs_view])
            tmp_alloc = DmaAllocOp([tile_values[tile_m], tile_values[tile_n]], out_view.result.type)
            reduce_block.add_op(tmp_alloc)
            reduce_block.add_op(
                (tmp_kernel := KernelMatmulOp(
                    tmp_alloc.results[0],
                    lhs_view.result,
                    rhs_view.result,
                    space,
                ))
            )
            _copy_tile_attrs(tmp_kernel)
            reduce_block.add_op(
                KernelBinaryElewiseOp(
                    out_view.result,
                    tmp_alloc.results[0],
                    out_view.result,
                    kind="add",
                    space=space,
                )
            )
            inner_block.add_op(reduce_loop)
        helper_ops.append(outer_loop)
        return helper_ops

    lhs_view = _build_view(
        lhs,
        offsets=[m_var, const0_m.results[0]],
        shape_values=[tile_values[tile_m], dim_k.result],
        const_one=const_one.results[0],
    )
    rhs_view = _build_view(
        rhs,
        offsets=[const0_m.results[0], n_var],
        shape_values=[dim_k.result, tile_values[tile_n]],
        const_one=const_one.results[0],
    )
    inner_block.add_ops([lhs_view, rhs_view])
    out_view = _build_view(
        out,
        offsets=[m_var, n_var],
        shape_values=[tile_values[tile_m], tile_values[tile_n]],
        const_one=const_one.results[0],
    )
    inner_block.add_op(out_view)
    inner_block.add_op(
        (matmul_op := KernelMatmulOp(
            out_view.result,
            lhs_view.result,
            rhs_view.result,
            space,
        ))
    )
    _copy_tile_attrs(matmul_op)
    helper_ops.append(outer_loop)
    return helper_ops

def _is_reduce_kernel(op: Operation) -> bool:
    """判断是否为 reduce kernel op。

    创建者: 小李飞刀
    最后一次更改: 小李飞刀

    功能说明:
    - 统一识别 `kernel.reduce_*` 的不支持分支。

    使用示例:
    - if _is_reduce_kernel(op): ...

    关联文件:
    - spec: [spec/pass/lowering/tile.md](spec/pass/lowering/tile.md)
    - test: [test/pass/test_lowering_tile.py](test/pass/test_lowering_tile.py)
    - 功能实现: [kernel_gen/passes/lowering/tile.py](kernel_gen/passes/lowering/tile.py)
    """

    return op.name.startswith("kernel.reduce")


def _classify_kernel_ops(kernel_ops: list[Operation]) -> str | None:
    """判断 kernel op 类型分支。

    创建者: 小李飞刀
    最后一次更改: 小李飞刀

    功能说明:
    - 若存在 `kernel.reduce_*`，直接拒绝。
    - 若包含 `kernel.matmul`，仅允许纯 matmul 场景。
    - 否则归类为 elementwise，并仅允许已知 elementwise op。

    使用示例:
    - mode = _classify_kernel_ops(kernel_ops)

    关联文件:
    - spec: [spec/pass/lowering/tile.md](spec/pass/lowering/tile.md)
    - test: [test/pass/test_lowering_tile.py](test/pass/test_lowering_tile.py)
    - 功能实现: [kernel_gen/passes/lowering/tile.py](kernel_gen/passes/lowering/tile.py)
    """

    if not kernel_ops:
        return None
    if any(_is_reduce_kernel(op) for op in kernel_ops):
        _raise_tile_error("TilePassUnsupportedOp", "reduce kernel op is not supported")
    if any(op.name == "kernel.matmul" for op in kernel_ops):
        if any(op.name != "kernel.matmul" for op in kernel_ops):
            _raise_tile_error("TilePassUnsupportedOp", "matmul must not mix with other kernel ops")
        return "matmul"

    allowed_elementwise = {
        "kernel.select",
        "kernel.binary_elewise",
    }
    for op in kernel_ops:
        if op.name not in allowed_elementwise:
            _raise_tile_error("TilePassUnsupportedOp", f"unsupported kernel op {op.name}")
    return "elementwise"


def _collect_kernel_memory_operands(kernel_ops: list[Operation]) -> list[SSAValue]:
    """收集 kernel op 使用的 memory operand。

    创建者: 小李飞刀
    最后一次更改: 小李飞刀

    功能说明:
    - 返回去重后的 memory operand 列表，并保持出现顺序。

    使用示例:
    - memory_values = _collect_kernel_memory_operands(kernel_ops)

    关联文件:
    - spec: [spec/pass/lowering/tile.md](spec/pass/lowering/tile.md)
    - test: [test/pass/test_lowering_tile.py](test/pass/test_lowering_tile.py)
    - 功能实现: [kernel_gen/passes/lowering/tile.py](kernel_gen/passes/lowering/tile.py)
    """

    seen: set[SSAValue] = set()
    ordered: list[SSAValue] = []
    for op in kernel_ops:
        for operand in op.operands:
            value = SSAValue.get(operand)
            if not isinstance(value.type, NnMemoryType):
                continue
            if value not in seen:
                seen.add(value)
                ordered.append(value)
    return ordered


def _validate_tile_name_uniqueness(tile_names: list[str]) -> None:
    """校验 tile 名称是否唯一。

    创建者: 小李飞刀
    最后一次更改: 小李飞刀

    功能说明:
    - 同一个函数内，不允许重复复用同名 tile 参数。

    使用示例:
    - _validate_tile_name_uniqueness(["TILE_M", "TILE_N"])

    关联文件:
    - spec: [spec/pass/lowering/tile.md](spec/pass/lowering/tile.md)
    - test: [test/pass/test_lowering_tile.py](test/pass/test_lowering_tile.py)
    - 功能实现: [kernel_gen/passes/lowering/tile.py](kernel_gen/passes/lowering/tile.py)
    """

    if len(set(tile_names)) != len(tile_names):
        _raise_tile_error("TilePassDuplicateTileParam", "tile names must be unique per function")


def _tile_analysis_attr(roles: list[list[str]]) -> ArrayAttr:
    """构造 tile.analysis 的嵌套属性。

    创建者: 小李飞刀
    最后一次更改: 小李飞刀

    功能说明:
    - 将角色标签矩阵转换为 `ArrayAttr(ArrayAttr(StringAttr))`。
    - 保持按 operand、按维度的输出顺序。

    使用示例:
    - attr = _tile_analysis_attr([["elewise", "elewise"], ["expand", "elewise"]])

    关联文件:
    - spec: [spec/pass/lowering/tile.md](spec/pass/lowering/tile.md)
    - test: [test/pass/test_lowering_tile.py](test/pass/test_lowering_tile.py)
    - 功能实现: [kernel_gen/passes/lowering/tile.py](kernel_gen/passes/lowering/tile.py)
    """

    return ArrayAttr([ArrayAttr([StringAttr(role) for role in row]) for row in roles])


def _set_tile_analysis(op: Operation, roles: list[list[str]]) -> None:
    """为 op 写入 tile.analysis 与 tile.tile_exprs 属性。

    创建者: 小李飞刀
    最后一次更改: 小李飞刀

    功能说明:
    - 仅在 roles 非空时写入 `tile.analysis` 与 `tile.tile_exprs`。
    - `tile.analysis` 保持角色标签矩阵，`tile.tile_exprs` 保持同形状空串矩阵。
    - 保持输出与 expectation 的矩阵文本一致。

    使用示例:
    - _set_tile_analysis(op, [["elewise", "elewise"]])

    关联文件:
    - spec: [spec/pass/lowering/tile.md](spec/pass/lowering/tile.md)
    - test: [test/pass/test_lowering_tile.py](test/pass/test_lowering_tile.py)
    - 功能实现: [kernel_gen/passes/lowering/tile.py](kernel_gen/passes/lowering/tile.py)
    """

    if not roles:
        return
    op.attributes["tile.analysis"] = _tile_analysis_attr(roles)
    op.attributes["tile.tile_exprs"] = ArrayAttr(
        [ArrayAttr([StringAttr("") for _ in row]) for row in roles]
    )


def _clear_tile_analysis(block: Block) -> None:
    """清理 block 中残留的 tile.analysis 属性。

    创建者: 小李飞刀
    最后一次更改: 小李飞刀

    功能说明:
    - 在 tile-only 路径移除 analysis 阶段残留的属性。

    使用示例:
    - _clear_tile_analysis(block)

    关联文件:
    - spec: [spec/pass/lowering/tile.md](spec/pass/lowering/tile.md)
    - test: [test/pass/test_lowering_tile.py](test/pass/test_lowering_tile.py)
    - 功能实现: [kernel_gen/passes/lowering/tile.py](kernel_gen/passes/lowering/tile.py)
    """

    for op in block.ops:
        if "tile.analysis" in op.attributes:
            op.attributes.pop("tile.analysis", None)


def _build_elementwise_tile_roles(op: Operation) -> list[list[str]]:
    """构造 elementwise 的 tile.analysis 角色矩阵。

    创建者: 小李飞刀
    最后一次更改: 小李飞刀

    功能说明:
    - 对每个 memory operand 输出全 `elewise` 标签。

    使用示例:
    - roles = _build_elementwise_tile_roles(kernel_op)

    关联文件:
    - spec: [spec/pass/lowering/tile.md](spec/pass/lowering/tile.md)
    - test: [test/pass/test_lowering_tile.py](test/pass/test_lowering_tile.py)
    - 功能实现: [kernel_gen/passes/lowering/tile.py](kernel_gen/passes/lowering/tile.py)
    """

    memory_values = [SSAValue.get(operand) for operand in op.operands if isinstance(SSAValue.get(operand).type, NnMemoryType)]
    if not memory_values:
        return []
    first_type = memory_values[0].type
    if not isinstance(first_type, NnMemoryType):
        return []
    rank = len(first_type.shape.data)
    return [["elewise"] * rank for _ in memory_values]


def _build_matmul_tile_roles(op: Operation) -> list[list[str]]:
    """构造 matmul 的 tile.analysis 角色矩阵。

    创建者: 小李飞刀
    最后一次更改: 小李飞刀

    功能说明:
    - 输出 `[elewise, reduce] / [reduce, elewise] / [elewise, elewise]` 的固定角色矩阵。

    使用示例:
    - roles = _build_matmul_tile_roles(matmul_op)

    关联文件:
    - spec: [spec/pass/lowering/tile.md](spec/pass/lowering/tile.md)
    - test: [test/pass/test_lowering_tile.py](test/pass/test_lowering_tile.py)
    - 功能实现: [kernel_gen/passes/lowering/tile.py](kernel_gen/passes/lowering/tile.py)
    """

    operands = [SSAValue.get(operand) for operand in op.operands]
    if len(operands) < 3:
        _raise_tile_error("TilePassRankMismatch", "matmul requires 3 operands")
    out, lhs, rhs = operands[0], operands[1], operands[2]
    if not isinstance(lhs.type, NnMemoryType) or not isinstance(rhs.type, NnMemoryType) or not isinstance(out.type, NnMemoryType):
        _raise_tile_error("TilePassRankMismatch", "matmul operands must be nn.memory")
    if len(lhs.type.shape.data) != 2 or len(rhs.type.shape.data) != 2 or len(out.type.shape.data) != 2:
        _raise_tile_error("TilePassRankMismatch", "matmul operands must be rank-2")
    return [
        ["elewise", "reduce"],
        ["reduce", "elewise"],
        ["elewise", "elewise"],
    ]


def _is_unit_dim(dim: Attribute) -> bool:
    """判断维度是否为 1。

    创建者: 小李飞刀
    最后一次更改: 小李飞刀

    功能说明:
    - 支持 `IntAttr(1)` 与 `StringAttr("1")`。

    使用示例:
    - if _is_unit_dim(dim): ...

    关联文件:
    - spec: [spec/pass/lowering/tile.md](spec/pass/lowering/tile.md)
    - test: [test/pass/test_lowering_tile.py](test/pass/test_lowering_tile.py)
    - 功能实现: [kernel_gen/passes/lowering/tile.py](kernel_gen/passes/lowering/tile.py)
    """

    return (isinstance(dim, IntAttr) and dim.data == 1) or (isinstance(dim, StringAttr) and dim.data == "1")


def _dim_equals(lhs: Attribute, rhs: Attribute) -> bool:
    """判断两个维度是否相同。

    创建者: 小李飞刀
    最后一次更改: 小李飞刀

    功能说明:
    - 支持 `StringAttr` 与 `IntAttr` 的一致性判断。

    使用示例:
    - if _dim_equals(lhs_dim, rhs_dim): ...

    关联文件:
    - spec: [spec/pass/lowering/tile.md](spec/pass/lowering/tile.md)
    - test: [test/pass/test_lowering_tile.py](test/pass/test_lowering_tile.py)
    - 功能实现: [kernel_gen/passes/lowering/tile.py](kernel_gen/passes/lowering/tile.py)
    """

    if isinstance(lhs, StringAttr) and isinstance(rhs, StringAttr):
        return lhs.data == rhs.data
    if isinstance(lhs, IntAttr) and isinstance(rhs, IntAttr):
        return lhs.data == rhs.data
    return False


def _build_broadcast_tile_roles(op: Operation) -> list[list[str]]:
    """构造 dma.broadcast 的 tile.analysis 角色矩阵。

    创建者: 小李飞刀
    最后一次更改: 小李飞刀

    功能说明:
    - target 维度统一标记为 `elewise`。
    - source 对齐到 target rank，维度一致标记 `elewise`，其余标记 `expand`。

    使用示例:
    - roles = _build_broadcast_tile_roles(broadcast_op)

    关联文件:
    - spec: [spec/pass/lowering/tile.md](spec/pass/lowering/tile.md)
    - test: [test/pass/test_lowering_tile.py](test/pass/test_lowering_tile.py)
    - 功能实现: [kernel_gen/passes/lowering/tile.py](kernel_gen/passes/lowering/tile.py)
    """

    target = SSAValue.get(op.operands[0])
    source = SSAValue.get(op.operands[1])
    if not isinstance(target.type, NnMemoryType):
        return []
    target_dims = list(target.type.shape.data)
    target_roles = ["elewise"] * len(target_dims)

    if not isinstance(source.type, NnMemoryType):
        source_roles = ["expand"] * len(target_dims)
        return [target_roles, source_roles]

    source_dims = list(source.type.shape.data)
    pad = len(target_dims) - len(source_dims)
    if pad < 0:
        _raise_tile_error("TilePassRankMismatch", "broadcast source rank must be <= target rank")
    aligned_source_dims: list[Attribute] = [IntAttr(1)] * pad + source_dims
    source_roles: list[str] = []
    for src_dim, tgt_dim in zip(aligned_source_dims, target_dims):
        if _dim_equals(src_dim, tgt_dim):
            source_roles.append("elewise")
        elif _is_unit_dim(src_dim):
            source_roles.append("expand")
        else:
            source_roles.append("expand")
    return [target_roles, source_roles]


def _annotate_tile_analysis(block: Block) -> None:
    """为 analysis-only 路径写入 tile.analysis。

    创建者: 小李飞刀
    最后一次更改: 小李飞刀

    功能说明:
    - 为 kernel.* 与 dma.broadcast 追加 tile.analysis 与 tile.tile_exprs 属性。
    - 仅在 analysis-only 路径使用。

    使用示例:
    - _annotate_tile_analysis(block)

    关联文件:
    - spec: [spec/pass/lowering/tile.md](spec/pass/lowering/tile.md)
    - test: [test/pass/test_lowering_tile.py](test/pass/test_lowering_tile.py)
    - 功能实现: [kernel_gen/passes/lowering/tile.py](kernel_gen/passes/lowering/tile.py)
    """

    for op in block.ops:
        if op.name == "dma.broadcast":
            roles = _build_broadcast_tile_roles(op)
            _set_tile_analysis(op, roles)
            continue
        if op.name == "kernel.matmul":
            roles = _build_matmul_tile_roles(op)
            _set_tile_analysis(op, roles)
            continue
        if op.name.startswith("kernel."):
            roles = _build_elementwise_tile_roles(op)
            _set_tile_analysis(op, roles)


__all__ = ["TilePassError", "_raise_tile_error"]
