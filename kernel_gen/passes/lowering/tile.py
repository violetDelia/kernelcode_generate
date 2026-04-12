"""tile lowering pass.

创建者: 小李飞刀
最后一次更改: 小李飞刀

功能说明:
- 将已完成 nn -> kernel 与 out-param 收口的单函数 IR，显式改写为 `symbol.for` + `dma.view` 结构。
- elementwise 分支按 memory rank 生成多层 loop，并插入/复用 `tuner.param` 作为 step。
- matmul 分支按 M/N/K 三维生成 loop，并插入/复用对应 tile 参数。

使用示例:
- from kernel_gen.passes.lowering.tile import TilePass
- module = TilePass().run(module)

关联文件:
- spec: [spec/pass/lowering/tile.md](spec/pass/lowering/tile.md)
- test: [test/pass/test_lowering_tile.py](test/pass/test_lowering_tile.py)
- 功能实现: [kernel_gen/passes/lowering/tile.py](kernel_gen/passes/lowering/tile.py)
"""

from __future__ import annotations

from dataclasses import dataclass

from xdsl.dialects import func
from xdsl.dialects.builtin import ArrayAttr, DictionaryAttr, IntAttr, ModuleOp, StringAttr
from xdsl.ir import Attribute, Block, Operation, SSAValue
from xdsl.irdl import IRDLOperation, operand_def, irdl_op_definition, result_def
from xdsl.utils.exceptions import VerifyException

from kernel_gen.dialect.dma import DmaAllocOp, DmaViewOp
from kernel_gen.dialect.nn import NnMemoryType
from kernel_gen.dialect.symbol import SymbolDimType, SymbolForOp, SymbolGetDimOp, SymbolValueType
from kernel_gen.dialect.tuner import TunerParamOp
from kernel_gen.passes.pass_manager import Pass


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


class TilePassOptionError(ValueError):
    """tile pass 选项解析错误。

    创建者: 小李飞刀
    最后一次更改: 小李飞刀

    功能说明:
    - 表示 TilePass.from_options 解析 options 时的可预期失败。
    - `str(e)` 必须以 `TilePassOptionError:` 前缀开头，便于测试匹配。

    使用示例:
    - raise TilePassOptionError("TilePassOptionError: invalid analysis-only value")

    关联文件:
    - spec: [spec/pass/lowering/tile.md](spec/pass/lowering/tile.md)
    - test: [test/pass/test_lowering_tile.py](test/pass/test_lowering_tile.py)
    - 功能实现: [kernel_gen/passes/lowering/tile.py](kernel_gen/passes/lowering/tile.py)
    """


@irdl_op_definition
class _TileSymbolLiteralOp(IRDLOperation):
    """tile 内部使用的 symbol.int 字面量 op。

    创建者: 小李飞刀
    最后一次更改: 小李飞刀

    功能说明:
    - 为 tile loop 构造 `!symbol.int<"...">` 字面量 SSA。
    - 仅作为 tile pass 内部桥接 op，不对外暴露。

    使用示例:
    - start = _TileSymbolLiteralOp("0")

    关联文件:
    - spec: [spec/pass/lowering/tile.md](spec/pass/lowering/tile.md)
    - test: [test/pass/test_lowering_tile.py](test/pass/test_lowering_tile.py)
    - 功能实现: [kernel_gen/passes/lowering/tile.py](kernel_gen/passes/lowering/tile.py)
    """

    name = "tile.symbol_literal"

    result = result_def(SymbolValueType)

    def __init__(self: "_TileSymbolLiteralOp", expr: str) -> None:
        """构造 symbol 字面量。

        创建者: 小李飞刀
        最后一次更改: 小李飞刀

        功能说明:
        - 为 tile loop 生成 `0`、`1` 等 `!symbol.int<"...">` SSA。

        使用示例:
        - start = _TileSymbolLiteralOp("0")

        关联文件:
        - spec: [spec/pass/lowering/tile.md](spec/pass/lowering/tile.md)
        - test: [test/pass/test_lowering_tile.py](test/pass/test_lowering_tile.py)
        - 功能实现: [kernel_gen/passes/lowering/tile.py](kernel_gen/passes/lowering/tile.py)
        """

        super().__init__(result_types=[SymbolValueType.from_expr(expr)])

    def verify_(self: "_TileSymbolLiteralOp") -> None:
        """校验 symbol 字面量结果类型。

        创建者: 小李飞刀
        最后一次更改: 小李飞刀

        功能说明:
        - 结果必须为 `!symbol.int<"...">`。

        使用示例:
        - _TileSymbolLiteralOp("1").verify_()

        关联文件:
        - spec: [spec/pass/lowering/tile.md](spec/pass/lowering/tile.md)
        - test: [test/pass/test_lowering_tile.py](test/pass/test_lowering_tile.py)
        - 功能实现: [kernel_gen/passes/lowering/tile.py](kernel_gen/passes/lowering/tile.py)
        """

        if not isinstance(self.result.type, SymbolValueType):
            raise VerifyException("tile.symbol_literal result must be !symbol.int")


@irdl_op_definition
class _TileStepValueOp(IRDLOperation):
    """把 `tuner.param` bridge 为 symbol loop step 的内部 op。

    创建者: 小李飞刀
    最后一次更改: 小李飞刀

    功能说明:
    - 将 `!symbol.dim<"...">` 转为 `!symbol.int<"...">`，便于 `symbol.for` 使用。
    - 保留明确的 step 生成痕迹，便于测试定位。

    使用示例:
    - step = _TileStepValueOp(tile_param.result, "TILE_M")

    关联文件:
    - spec: [spec/pass/lowering/tile.md](spec/pass/lowering/tile.md)
    - test: [test/pass/test_lowering_tile.py](test/pass/test_lowering_tile.py)
    - 功能实现: [kernel_gen/passes/lowering/tile.py](kernel_gen/passes/lowering/tile.py)
    """

    name = "tile.step_value"

    source = operand_def(SymbolDimType)
    result = result_def(SymbolValueType)

    def __init__(self: "_TileStepValueOp", source: SSAValue | Operation, tile_name: str) -> None:
        """构造 tile step bridge。

        创建者: 小李飞刀
        最后一次更改: 小李飞刀

        功能说明:
        - 明确保留 `tuner.param -> !symbol.int<tile>` 的桥接痕迹。
        - 让 loop step 由 `tuner.param` 驱动而非隐藏常量。

        使用示例:
        - step = _TileStepValueOp(tile_param.result, "TILE_M")

        关联文件:
        - spec: [spec/pass/lowering/tile.md](spec/pass/lowering/tile.md)
        - test: [test/pass/test_lowering_tile.py](test/pass/test_lowering_tile.py)
        - 功能实现: [kernel_gen/passes/lowering/tile.py](kernel_gen/passes/lowering/tile.py)
        """

        super().__init__(
            operands=[source],
            result_types=[SymbolValueType.from_expr(tile_name)],
        )

    def verify_(self: "_TileStepValueOp") -> None:
        """校验 tile step bridge。

        创建者: 小李飞刀
        最后一次更改: 小李飞刀

        功能说明:
        - source 必须为 `!symbol.dim<"...">`。
        - result expr 必须与 source dim 名称一致。

        使用示例:
        - _TileStepValueOp(tile_param.result, "TILE_M").verify_()

        关联文件:
        - spec: [spec/pass/lowering/tile.md](spec/pass/lowering/tile.md)
        - test: [test/pass/test_lowering_tile.py](test/pass/test_lowering_tile.py)
        - 功能实现: [kernel_gen/passes/lowering/tile.py](kernel_gen/passes/lowering/tile.py)
        """

        source_type = SSAValue.get(self.source).type
        if not isinstance(source_type, SymbolDimType):
            raise VerifyException("tile.step_value source must be !symbol.dim")
        expected = SymbolValueType.from_expr(source_type.dim.data)
        if self.result.type != expected:
            raise VerifyException("tile.step_value result must match tuner.param dim name")


@dataclass(frozen=True)
class _TileLoopSpec:
    """描述单个 tile loop 的构造参数。

    创建者: 小李飞刀
    最后一次更改: 小李飞刀

    功能说明:
    - 统一保存 loop 的 axis/tile 名称与相关 helper op。
    - 便于批量插入 helper 与构造 loop 嵌套。

    使用示例:
    - spec = _TileLoopSpec(axis=0, tile_name="TILE_M", start=start, end=end, step=step, block=block, loop=loop)

    关联文件:
    - spec: [spec/pass/lowering/tile.md](spec/pass/lowering/tile.md)
    - test: [test/pass/test_lowering_tile.py](test/pass/test_lowering_tile.py)
    - 功能实现: [kernel_gen/passes/lowering/tile.py](kernel_gen/passes/lowering/tile.py)
    """

    axis: int
    tile_name: str
    start: _TileSymbolLiteralOp
    end: SymbolGetDimOp
    step: _TileStepValueOp
    block: Block
    loop: SymbolForOp


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
    - 当前约定所有 `kernel.*` 的最后一个 operand 为写出 buffer。

    使用示例:
    - out_value = _kernel_out_operand(kernel_op)

    关联文件:
    - spec: [spec/pass/lowering/tile.md](spec/pass/lowering/tile.md)
    - test: [test/pass/test_lowering_tile.py](test/pass/test_lowering_tile.py)
    - 功能实现: [kernel_gen/passes/lowering/tile.py](kernel_gen/passes/lowering/tile.py)
    """

    return SSAValue.get(op.operands[-1])


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
        "kernel.add",
        "kernel.sub",
        "kernel.mul",
        "kernel.div",
        "kernel.eq",
        "kernel.ne",
        "kernel.lt",
        "kernel.le",
        "kernel.gt",
        "kernel.ge",
        "kernel.select",
        "kernel.cast",
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


def _tile_name_from_dim(dim: Attribute, axis: int) -> str:
    """根据维度条目生成 tile 名称。

    创建者: 小李飞刀
    最后一次更改: 小李飞刀

    功能说明:
    - StringAttr 维度使用 `TILE_<DIM>`。
    - IntAttr 维度使用 `TILE_D<axis>`。

    使用示例:
    - tile_name = _tile_name_from_dim(StringAttr("M"), 1)

    关联文件:
    - spec: [spec/pass/lowering/tile.md](spec/pass/lowering/tile.md)
    - test: [test/pass/test_lowering_tile.py](test/pass/test_lowering_tile.py)
    - 功能实现: [kernel_gen/passes/lowering/tile.py](kernel_gen/passes/lowering/tile.py)
    """

    if isinstance(dim, StringAttr) and dim.data:
        return f"TILE_{dim.data}"
    if isinstance(dim, IntAttr):
        return f"TILE_D{axis}"
    _raise_tile_error("TilePassUnsupportedOp", "unsupported memory dim entry for tile")
    return "TILE_UNREACHABLE"


def _build_view_type(
    source_type: NnMemoryType,
    shape_names: list[str],
    stride_names: list[str],
) -> NnMemoryType:
    """构造 dma.view 的结果类型。

    创建者: 小李飞刀
    最后一次更改: 小李飞刀

    功能说明:
    - 形状与步长均使用字符串维度，避免隐藏常量。

    使用示例:
    - view_type = _build_view_type(source_type, ["TILE_M", "TILE_N"], ["S0", "S1"])

    关联文件:
    - spec: [spec/pass/lowering/tile.md](spec/pass/lowering/tile.md)
    - test: [test/pass/test_lowering_tile.py](test/pass/test_lowering_tile.py)
    - 功能实现: [kernel_gen/passes/lowering/tile.py](kernel_gen/passes/lowering/tile.py)
    """

    shape_attr = ArrayAttr([StringAttr(name) for name in shape_names])
    stride_attr = ArrayAttr([StringAttr(name) for name in stride_names])
    return NnMemoryType(shape_attr, stride_attr, source_type.element_type, source_type.space)


def _find_or_insert_tile_param(
    block: Block,
    tile_name: str,
) -> tuple[TunerParamOp, bool]:
    """查找或插入同名 tile 的 `tuner.param`。

    创建者: 小李飞刀
    最后一次更改: 小李飞刀

    功能说明:
    - 若函数体内已存在同名 `tuner.param`，直接复用。
    - 否则创建新的 `tuner.param : !symbol.dim<tile>`。
    - 若同名 `tuner.param` 出现多次，视为重复冲突。

    使用示例:
    - tile_param, inserted = _find_or_insert_tile_param(block, "TILE_M")

    关联文件:
    - spec: [spec/pass/lowering/tile.md](spec/pass/lowering/tile.md)
    - test: [test/pass/test_lowering_tile.py](test/pass/test_lowering_tile.py)
    - 功能实现: [kernel_gen/passes/lowering/tile.py](kernel_gen/passes/lowering/tile.py)
    """

    try:
        expected_type = SymbolDimType.from_name(tile_name)
    except VerifyException as exc:
        _raise_tile_error("TilePassUnsupportedOp", f"tile name {tile_name!r} is invalid: {exc}")
        raise

    matches: list[TunerParamOp] = []
    for op in block.ops:
        if isinstance(op, TunerParamOp) and op.result.type == expected_type:
            matches.append(op)
    if len(matches) > 1:
        _raise_tile_error("TilePassDuplicateTileParam", f"duplicate tuner.param for tile {tile_name}")
    if matches:
        return matches[0], False
    return TunerParamOp(expected_type), True


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


def _read_kernel_split_tile_spec(
    func_op: func.FuncOp,
    rank: int,
) -> tuple[int, str] | None:
    """读取 kernel_split tile 覆盖信息。

    创建者: 小李飞刀
    最后一次更改: 小李飞刀

    功能说明:
    - 从 `func.func` 的 `kernel_split` 属性读取 axis 与 tile 名称。
    - 仅用于 elementwise 场景，返回 axis 与 tile 名称以覆盖默认命名。

    使用示例:
    - spec = _read_kernel_split_tile_spec(func_op, rank)
    - if spec is not None: axis, tile_name = spec

    关联文件:
    - spec: [spec/pass/lowering/tile.md](spec/pass/lowering/tile.md)
    - test: [test/dsl/test_gen_kernel.py](test/dsl/test_gen_kernel.py)
    - 功能实现: [kernel_gen/passes/lowering/tile.py](kernel_gen/passes/lowering/tile.py)
    """

    if "kernel_split" not in func_op.attributes:
        return None
    attr = func_op.attributes["kernel_split"]
    if not isinstance(attr, DictionaryAttr):
        _raise_tile_error("TilePassUnsupportedOp", "kernel_split attr must be a dictionary")
    axis_attr = attr.data.get("axis")
    tile_attr = attr.data.get("tile")
    if not isinstance(axis_attr, IntAttr) or not isinstance(tile_attr, StringAttr):
        _raise_tile_error(
            "TilePassUnsupportedOp",
            "kernel_split attr must contain axis:int and tile:string",
        )
    axis = axis_attr.data
    if axis < 0 or axis >= rank:
        _raise_tile_error(
            "TilePassUnsupportedOp",
            "kernel_split axis must be within elementwise rank",
        )
    tile_name = tile_attr.data
    if not tile_name:
        _raise_tile_error(
            "TilePassUnsupportedOp",
            "kernel_split tile name must be non-empty",
        )
    return axis, tile_name


def _build_elementwise_loop_specs(
    func_op: func.FuncOp,
    block: Block,
    reference_memory: SSAValue,
) -> list[_TileLoopSpec]:
    """构造 elementwise 维度对应的 loop 规格。

    创建者: 小李飞刀
    最后一次更改: 小李飞刀

    功能说明:
    - 按 reference memory 的 rank 生成 N 组 loop 规格。
    - 为每个轴生成 `tuner.param` 与 `tile.step_value`。

    使用示例:
    - specs = _build_elementwise_loop_specs(func_op, block, reference_memory)

    关联文件:
    - spec: [spec/pass/lowering/tile.md](spec/pass/lowering/tile.md)
    - test: [test/pass/test_lowering_tile.py](test/pass/test_lowering_tile.py)
    - 功能实现: [kernel_gen/passes/lowering/tile.py](kernel_gen/passes/lowering/tile.py)
    """

    memory_type = reference_memory.type
    if not isinstance(memory_type, NnMemoryType):
        _raise_tile_error(
            "TilePassRankMismatch",
            f"function {func_op.sym_name.data} elementwise reference must be nn.memory",
        )
    tile_names = [
        _tile_name_from_dim(dim, axis) for axis, dim in enumerate(memory_type.shape.data)
    ]
    kernel_split_spec = _read_kernel_split_tile_spec(func_op, len(tile_names))
    if kernel_split_spec is not None:
        axis, tile_name = kernel_split_spec
        tile_names[axis] = tile_name
    _validate_tile_name_uniqueness(tile_names)

    specs: list[_TileLoopSpec] = []
    for axis, tile_name in enumerate(tile_names):
        tile_param, inserted = _find_or_insert_tile_param(block, tile_name)
        if inserted:
            block.insert_op_before(tile_param, block.last_op)
        start_value = _TileSymbolLiteralOp("0")
        end_value = SymbolGetDimOp(reference_memory, axis)
        step_value = _TileStepValueOp(tile_param.result, tile_name)
        loop_block = Block(arg_types=[step_value.result.type])
        loop_op = SymbolForOp(start_value.result, end_value.result, step_value.result, loop_block)
        specs.append(
            _TileLoopSpec(
                axis=axis,
                tile_name=tile_name,
                start=start_value,
                end=end_value,
                step=step_value,
                block=loop_block,
                loop=loop_op,
            )
        )
    return specs


def _build_matmul_loop_specs(
    block: Block,
    lhs: SSAValue,
    rhs: SSAValue,
    out: SSAValue,
) -> list[_TileLoopSpec]:
    """构造 matmul 的 M/N/K loop 规格。

    创建者: 小李飞刀
    最后一次更改: 小李飞刀

    功能说明:
    - 生成 TILE_M/TILE_N/TILE_K 三组 loop 规格。

    使用示例:
    - specs = _build_matmul_loop_specs(block, lhs, rhs, out)

    关联文件:
    - spec: [spec/pass/lowering/tile.md](spec/pass/lowering/tile.md)
    - test: [test/pass/test_lowering_tile.py](test/pass/test_lowering_tile.py)
    - 功能实现: [kernel_gen/passes/lowering/tile.py](kernel_gen/passes/lowering/tile.py)
    """

    tile_names = ["TILE_M", "TILE_N", "TILE_K"]
    _validate_tile_name_uniqueness(tile_names)
    memory_ref = [lhs, rhs, out]
    if not all(isinstance(mem.type, NnMemoryType) for mem in memory_ref):
        _raise_tile_error("TilePassRankMismatch", "matmul operands must be nn.memory")
    lhs_type = lhs.type
    rhs_type = rhs.type
    out_type = out.type
    if not isinstance(lhs_type, NnMemoryType) or not isinstance(rhs_type, NnMemoryType) or not isinstance(out_type, NnMemoryType):
        _raise_tile_error("TilePassRankMismatch", "matmul operands must be nn.memory")
    if len(lhs_type.shape.data) != 2 or len(rhs_type.shape.data) != 2 or len(out_type.shape.data) != 2:
        _raise_tile_error("TilePassRankMismatch", "matmul operands must be rank-2")
    if lhs_type.shape.data[1] != rhs_type.shape.data[0]:
        _raise_tile_error("TilePassRankMismatch", "matmul contracting dimensions must match")
    if lhs_type.shape.data[0] != out_type.shape.data[0] or rhs_type.shape.data[1] != out_type.shape.data[1]:
        _raise_tile_error("TilePassRankMismatch", "matmul output shape must match lhs/rhs")

    tile_params: list[tuple[str, TunerParamOp]] = []
    for tile_name in tile_names:
        tile_param, inserted = _find_or_insert_tile_param(block, tile_name)
        if inserted:
            block.insert_op_before(tile_param, block.last_op)
        tile_params.append((tile_name, tile_param))

    specs: list[_TileLoopSpec] = []
    for axis, tile_name in enumerate(tile_names):
        tile_param = dict(tile_params)[tile_name]
        start_value = _TileSymbolLiteralOp("0")
        if axis == 0:
            end_value = SymbolGetDimOp(out, 0)
        elif axis == 1:
            end_value = SymbolGetDimOp(out, 1)
        else:
            end_value = SymbolGetDimOp(lhs, 1)
        step_value = _TileStepValueOp(tile_param.result, tile_name)
        loop_block = Block(arg_types=[step_value.result.type])
        loop_op = SymbolForOp(start_value.result, end_value.result, step_value.result, loop_block)
        specs.append(
            _TileLoopSpec(
                axis=axis,
                tile_name=tile_name,
                start=start_value,
                end=end_value,
                step=step_value,
                block=loop_block,
                loop=loop_op,
            )
        )
    return specs


def _insert_tile_helpers(
    block: Block,
    specs: list[_TileLoopSpec],
    return_op: Operation,
) -> None:
    """将 tile helper ops 插入函数体。

    创建者: 小李飞刀
    最后一次更改: 小李飞刀

    功能说明:
    - 依次插入 start/end/step 以及最外层 loop op。

    使用示例:
    - _insert_tile_helpers(block, specs, return_op)

    关联文件:
    - spec: [spec/pass/lowering/tile.md](spec/pass/lowering/tile.md)
    - test: [test/pass/test_lowering_tile.py](test/pass/test_lowering_tile.py)
    - 功能实现: [kernel_gen/passes/lowering/tile.py](kernel_gen/passes/lowering/tile.py)
    """

    helper_ops: list[Operation] = []
    for spec in specs:
        helper_ops.extend([spec.start, spec.end, spec.step])
    if specs:
        helper_ops.append(specs[0].loop)
    block.insert_ops_before(helper_ops, return_op)


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
    """为 op 写入 tile.analysis 属性。

    创建者: 小李飞刀
    最后一次更改: 小李飞刀

    功能说明:
    - 仅在 roles 非空时写入 `tile.analysis`。
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
    lhs, rhs, out = operands[0], operands[1], operands[-1]
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
    - 为 kernel.* 与 dma.broadcast 追加 tile.analysis 属性。
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


def _nest_loops(specs: list[_TileLoopSpec]) -> Block | None:
    """按顺序嵌套 loop，并返回最内层 block。

    创建者: 小李飞刀
    最后一次更改: 小李飞刀

    功能说明:
    - 将内层 loop op 放入外层 loop block。
    - 返回最内层 loop block 以便插入 view 与 kernel op。

    使用示例:
    - inner_block = _nest_loops(specs)

    关联文件:
    - spec: [spec/pass/lowering/tile.md](spec/pass/lowering/tile.md)
    - test: [test/pass/test_lowering_tile.py](test/pass/test_lowering_tile.py)
    - 功能实现: [kernel_gen/passes/lowering/tile.py](kernel_gen/passes/lowering/tile.py)
    """

    if not specs:
        return None
    for outer, inner in zip(specs, specs[1:]):
        outer.block.add_op(inner.loop)
    return specs[-1].block


def _insert_elementwise_views_and_ops(
    inner_block: Block,
    loop_vars: list[SSAValue],
    step_values: list[SSAValue],
    tile_names: list[str],
    kernel_ops: list[Operation],
) -> None:
    """在最内层 block 插入 elementwise view 与 kernel op。

    创建者: 小李飞刀
    最后一次更改: 小李飞刀

    功能说明:
    - 为 kernel op 使用到的 memory operand 创建 `dma.view`。
    - 将 kernel op 移入最内层 loop，并替换 operand。

    使用示例:
    - _insert_elementwise_views_and_ops(inner_block, loop_vars, step_values, tile_names, kernel_ops)

    关联文件:
    - spec: [spec/pass/lowering/tile.md](spec/pass/lowering/tile.md)
    - test: [test/pass/test_lowering_tile.py](test/pass/test_lowering_tile.py)
    - 功能实现: [kernel_gen/passes/lowering/tile.py](kernel_gen/passes/lowering/tile.py)
    """

    stride_one = _TileSymbolLiteralOp("1")
    inner_block.add_op(stride_one)
    memory_values = _collect_kernel_memory_operands(kernel_ops)
    view_map: dict[SSAValue, SSAValue] = {}
    for memory in memory_values:
        mem_type = memory.type
        if not isinstance(mem_type, NnMemoryType):
            _raise_tile_error("TilePassRankMismatch", "kernel operands must be nn.memory")
        rank = len(mem_type.shape.data)
        shape_names = list(tile_names)
        stride_names = [f"S{axis}" for axis in range(rank)]
        view_type = _build_view_type(mem_type, shape_names, stride_names)
        view_op = DmaViewOp(
            memory,
            offsets=list(loop_vars),
            shape=list(step_values),
            stride=[stride_one.result for _ in range(rank)],
            result_type=view_type,
        )
        inner_block.add_op(view_op)
        view_map[memory] = view_op.result

    for op in kernel_ops:
        op.detach()
        for index, operand in enumerate(op.operands):
            value = SSAValue.get(operand)
            if value in view_map:
                op.operands[index] = view_map[value]
        inner_block.add_op(op)


def _insert_matmul_views_and_ops(
    inner_block: Block,
    loop_vars: list[SSAValue],
    step_values: list[SSAValue],
    kernel_ops: list[Operation],
) -> None:
    """在最内层 block 插入 matmul view 与 kernel op。

    创建者: 小李飞刀
    最后一次更改: 小李飞刀

    功能说明:
    - 根据 M/N/K loop 变量与 step 构造 lhs/rhs/out 的 view。
    - 将 kernel.matmul op 移入最内层 loop，并替换 operand。

    使用示例:
    - _insert_matmul_views_and_ops(inner_block, loop_vars, step_values, kernel_ops)

    关联文件:
    - spec: [spec/pass/lowering/tile.md](spec/pass/lowering/tile.md)
    - test: [test/pass/test_lowering_tile.py](test/pass/test_lowering_tile.py)
    - 功能实现: [kernel_gen/passes/lowering/tile.py](kernel_gen/passes/lowering/tile.py)
    """

    if len(loop_vars) != 3 or len(step_values) != 3:
        _raise_tile_error("TilePassRankMismatch", "matmul requires 3 loop variables")
    stride_one = _TileSymbolLiteralOp("1")
    inner_block.add_op(stride_one)

    def _make_view(
        source: SSAValue,
        offsets: list[SSAValue],
        shape: list[SSAValue],
        shape_names: list[str],
    ) -> SSAValue:
        """构造 matmul 分支的 dma.view 并返回 view SSA。

        创建者: 小李飞刀
        最后一次更改: 小李飞刀

        功能说明:
        - 按给定 offsets/shape 生成 `dma.view`。
        - 统一封装 view 结果类型构造逻辑。

        使用示例:
        - lhs_view = _make_view(lhs, [m_var, k_var], [step_m, step_k], ["TILE_M", "TILE_K"])

        关联文件:
        - spec: [spec/pass/lowering/tile.md](spec/pass/lowering/tile.md)
        - test: [test/pass/test_lowering_tile.py](test/pass/test_lowering_tile.py)
        - 功能实现: [kernel_gen/passes/lowering/tile.py](kernel_gen/passes/lowering/tile.py)
        """
        mem_type = source.type
        if not isinstance(mem_type, NnMemoryType):
            _raise_tile_error("TilePassRankMismatch", "matmul operands must be nn.memory")
        view_type = _build_view_type(mem_type, shape_names, ["S0", "S1"])
        view_op = DmaViewOp(
            source,
            offsets=offsets,
            shape=shape,
            stride=[stride_one.result, stride_one.result],
            result_type=view_type,
        )
        inner_block.add_op(view_op)
        return view_op.result

    m_var, n_var, k_var = loop_vars
    step_m, step_n, step_k = step_values

    view_map: dict[SSAValue, SSAValue] = {}
    for op in kernel_ops:
        lhs = SSAValue.get(op.operands[0])
        rhs = SSAValue.get(op.operands[1])
        out = SSAValue.get(op.operands[-1])
        if lhs not in view_map:
            view_map[lhs] = _make_view(
                lhs,
                offsets=[m_var, k_var],
                shape=[step_m, step_k],
                shape_names=["TILE_M", "TILE_K"],
            )
        if rhs not in view_map:
            view_map[rhs] = _make_view(
                rhs,
                offsets=[k_var, n_var],
                shape=[step_k, step_n],
                shape_names=["TILE_K", "TILE_N"],
            )
        if out not in view_map:
            view_map[out] = _make_view(
                out,
                offsets=[m_var, n_var],
                shape=[step_m, step_n],
                shape_names=["TILE_M", "TILE_N"],
            )

    for op in kernel_ops:
        op.detach()
        for index, operand in enumerate(op.operands):
            value = SSAValue.get(operand)
            if value in view_map:
                op.operands[index] = view_map[value]
        inner_block.add_op(op)


def _rewrite_function(func_op: func.FuncOp, analysis_only: bool) -> None:
    """改写单个函数为 tile loop 结构。

    创建者: 小李飞刀
    最后一次更改: 小李飞刀

    功能说明:
    - 对 elementwise/matmul 分支生成 `tuner.param`、`tile.step_value`、`symbol.for` 与 `dma.view`。
    - analysis_only=true 时仅输出 `tile.analysis`，不生成 loop/view/helper。
    - 保持单函数合同，不新增 `func.call`。

    使用示例:
    - _rewrite_function(func_op, analysis_only=False)

    关联文件:
    - spec: [spec/pass/lowering/tile.md](spec/pass/lowering/tile.md)
    - test: [test/pass/test_lowering_tile.py](test/pass/test_lowering_tile.py)
    - 功能实现: [kernel_gen/passes/lowering/tile.py](kernel_gen/passes/lowering/tile.py)
    """

    block = _get_single_block(func_op)
    _validate_input_contract(func_op, block)
    kernel_ops = _collect_kernel_ops(block)
    _validate_intermediate_materialization(func_op, block)

    return_op = block.last_op
    if not isinstance(return_op, func.ReturnOp):
        _raise_tile_error(
            "TilePassRequiresLoweredKernelIR",
            f"function {func_op.sym_name.data} must terminate with func.return",
        )

    if analysis_only:
        _annotate_tile_analysis(block)
        return

    mode = _classify_kernel_ops(kernel_ops)
    _clear_tile_analysis(block)
    if mode is None:
        return

    if mode == "elementwise":
        memory_values = _collect_kernel_memory_operands(kernel_ops)
        if not memory_values:
            _raise_tile_error("TilePassUnsupportedOp", "elementwise requires kernel memory operands")
        reference_memory = memory_values[0]
        reference_type = reference_memory.type
        if not isinstance(reference_type, NnMemoryType):
            _raise_tile_error("TilePassRankMismatch", "elementwise reference must be nn.memory")
        reference_rank = len(reference_type.shape.data)
        for index, memory in enumerate(memory_values):
            mem_type = memory.type
            if not isinstance(mem_type, NnMemoryType):
                _raise_tile_error("TilePassRankMismatch", "kernel operands must be nn.memory")
            if len(mem_type.shape.data) != reference_rank:
                _raise_tile_error(
                    "TilePassRankMismatch",
                    f"elementwise rank mismatch at operand {index}",
                )
        specs = _build_elementwise_loop_specs(func_op, block, reference_memory)
        inner_block = _nest_loops(specs)
        if inner_block is None:
            return
        _insert_tile_helpers(block, specs, return_op)
        loop_vars = [spec.block.args[0] for spec in specs]
        step_values = [spec.step.result for spec in specs]
        tile_names = [spec.tile_name for spec in specs]
        _insert_elementwise_views_and_ops(inner_block, loop_vars, step_values, tile_names, kernel_ops)
        return

    if mode == "matmul":
        if len(kernel_ops) != 1:
            _raise_tile_error("TilePassUnsupportedOp", "matmul expects single kernel.matmul op")
        matmul_op = kernel_ops[0]
        lhs = SSAValue.get(matmul_op.operands[0])
        rhs = SSAValue.get(matmul_op.operands[1])
        out = SSAValue.get(matmul_op.operands[-1])
        specs = _build_matmul_loop_specs(block, lhs, rhs, out)
        inner_block = _nest_loops(specs)
        if inner_block is None:
            return
        _insert_tile_helpers(block, specs, return_op)
        loop_vars = [spec.block.args[0] for spec in specs]
        step_values = [spec.step.result for spec in specs]
        _insert_matmul_views_and_ops(inner_block, loop_vars, step_values, kernel_ops)


class TilePass(Pass):
    """tile lowering pass。

    创建者: 小李飞刀
    最后一次更改: jcc你莫辜负

    功能说明:
    - 对 module 内满足输入合同的 func.func 执行 tile loop 改写。
    - elementwise 与 matmul 按固定规则插入 loop 与 view。
    - analysis-only=true 时只写 `tile.analysis` 角色矩阵（按 operand、按维度，且仅含角色标签）。
    - tile-only=true 时先执行 analysis，再按 `tile.analysis` 改写并清理该属性。

    使用示例:
    - module = TilePass().run(module)
    - module = TilePass.from_options({"analysis-only": "true", "tile-elewise": "true", "tile-reduce": "false"}).run(module)
    - module = TilePass.from_options({"tile-only": "true", "tile-elewise": "true", "tile-reduce": "true"}).run(module)

    关联文件:
    - spec: [spec/pass/lowering/tile.md](spec/pass/lowering/tile.md)
    - test: [test/pass/test_lowering_tile.py](test/pass/test_lowering_tile.py)
    - 功能实现: [kernel_gen/passes/lowering/tile.py](kernel_gen/passes/lowering/tile.py)
    """

    name = "tile"

    def __init__(
        self: "TilePass",
        analysis_only: bool = False,
        tile_only: bool | None = None,
        tile_elewise: bool = True,
        tile_reduce: bool = True,
    ) -> None:
        """初始化 tile pass。

        创建者: 金铲铲大作战
        最后一次更改: 小李飞刀

        功能说明:
        - analysis_only=true 时仅输出 `tile.analysis`。
        - tile_only=true 时先执行 analysis，再进入 tile 改写。
        - tile_elewise/tile_reduce 表示公开 option 的启用状态。

        使用示例:
        - pass_obj = TilePass()
        - pass_obj = TilePass(analysis_only=True)
        - pass_obj = TilePass(tile_only=True, tile_elewise=True, tile_reduce=False)

        关联文件:
        - spec: [spec/pass/lowering/tile.md](spec/pass/lowering/tile.md)
        - test: [test/pass/test_lowering_tile.py](test/pass/test_lowering_tile.py)
        - 功能实现: [kernel_gen/passes/lowering/tile.py](kernel_gen/passes/lowering/tile.py)
        """

        if tile_only is None:
            tile_only = not analysis_only
        if analysis_only and tile_only:
            _raise_tile_error("TilePassInvalidOption", "analysis-only conflicts with tile-only")
        if not analysis_only and not tile_only:
            _raise_tile_error("TilePassInvalidOption", "tile-only must be true when analysis-only=false")
        self._analysis_only = analysis_only
        self._tile_only = tile_only
        self._tile_elewise = tile_elewise
        self._tile_reduce = tile_reduce

    @classmethod
    def from_options(cls, options: dict[str, str]) -> "TilePass":
        """从 options 构造 TilePass。

        创建者: 金铲铲大作战
        最后一次更改: 小李飞刀

        功能说明:
        - 支持 `analysis-only/tile-only/tile-elewise/tile-reduce` 四类选项。
        - 仅接受 `true/false` 字符串。
        - 公开组合以 `spec/pass/lowering/tile.md` 为准。

        使用示例:
        - pass_obj = TilePass.from_options(
            {"analysis-only": "true", "tile-elewise": "true", "tile-reduce": "false"}
          )

        关联文件:
        - spec: [spec/pass/lowering/tile.md](spec/pass/lowering/tile.md)
        - test: [test/pass/test_lowering_tile.py](test/pass/test_lowering_tile.py)
        - 功能实现: [kernel_gen/passes/lowering/tile.py](kernel_gen/passes/lowering/tile.py)
        """

        if not options:
            return cls()

        allowed_keys = {"analysis-only", "tile-only", "tile-elewise", "tile-reduce"}
        extra_keys = set(options.keys()) - allowed_keys
        if extra_keys:
            _raise_tile_error("TilePassInvalidOption", "unsupported tile options")

        def _parse_flag(key: str) -> bool:
            if key not in options:
                return False
            value = options[key]
            if value == "true":
                return True
            if value == "false":
                return False
            _raise_tile_error("TilePassInvalidOption", f"{key} must be true or false")
            return False

        analysis_only = _parse_flag("analysis-only")
        tile_only = _parse_flag("tile-only")
        tile_elewise = _parse_flag("tile-elewise")
        tile_reduce = _parse_flag("tile-reduce")

        if analysis_only and tile_only:
            _raise_tile_error("TilePassInvalidOption", "analysis-only conflicts with tile-only")

        if analysis_only:
            if not tile_elewise or tile_reduce:
                _raise_tile_error("TilePassInvalidOption", "analysis-only must pair with tile-elewise=true,tile-reduce=false")
            return cls(
                analysis_only=True,
                tile_only=False,
                tile_elewise=tile_elewise,
                tile_reduce=tile_reduce,
            )

        if not tile_only:
            _raise_tile_error("TilePassInvalidOption", "tile-only must be true when analysis-only=false")
        if not tile_elewise:
            _raise_tile_error("TilePassInvalidOption", "tile-elewise must be true")

        return cls(
            analysis_only=False,
            tile_only=True,
            tile_elewise=tile_elewise,
            tile_reduce=tile_reduce,
        )

    def run(self: "TilePass", module: ModuleOp) -> ModuleOp:
        """执行 tile pass。

        创建者: 小李飞刀
        最后一次更改: jcc你莫辜负

        功能说明:
        - 遍历 module 中的 func.func 并执行改写。
        - `module.verify()` 失败时统一转译为 `TilePassRequiresLoweredKernelIR`。
        - analysis_only=true 时仅写 `tile.analysis`，不生成 loop/view/helper。
        - tile_only=true 时先执行 analysis，再进入改写阶段并清理 `tile.analysis`。

        使用示例:
        - lowered = TilePass().run(module)
        - lowered = TilePass.from_options({"analysis-only": "true", "tile-elewise": "true", "tile-reduce": "false"}).run(module)
        - lowered = TilePass.from_options({"tile-only": "true", "tile-elewise": "true", "tile-reduce": "true"}).run(module)

        关联文件:
        - spec: [spec/pass/lowering/tile.md](spec/pass/lowering/tile.md)
        - test: [test/pass/test_lowering_tile.py](test/pass/test_lowering_tile.py)
        - 功能实现: [kernel_gen/passes/lowering/tile.py](kernel_gen/passes/lowering/tile.py)
        """

        if self._analysis_only and self._tile_only:
            _raise_tile_error("TilePassInvalidOption", "analysis-only conflicts with tile-only")
        if not self._analysis_only and not self._tile_only:
            _raise_tile_error("TilePassInvalidOption", "tile-only must be true when analysis-only=false")

        for op in module.ops:
            if isinstance(op, func.FuncOp):
                _rewrite_function(op, analysis_only=self._analysis_only)
        try:
            module.verify()
        except VerifyException as exc:
            _raise_tile_error("TilePassRequiresLoweredKernelIR", str(exc))
        return module


__all__ = [
    "TilePass",
    "TilePassError",
    "TilePassOptionError",
    "_TileSymbolLiteralOp",
    "_TileStepValueOp",
]
