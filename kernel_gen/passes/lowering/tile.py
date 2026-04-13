"""tile lowering pass.

创建者: 小李飞刀
最后一次更改: 小李飞刀

功能说明:
- 将已完成 nn -> kernel 与 out-param 收口的单函数 IR，显式改写为 `symbol.for` + `dma.view` 结构。
- elementwise 分支按 memory rank 生成多层 loop，并插入/复用 `tuner.param` 作为 step。
- matmul 分支按 D0/D1（可选 R0）生成 loop，并插入对应 tile 参数。

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
from xdsl.dialects.builtin import (
    ArrayAttr,
    DenseArrayBase,
    DictionaryAttr,
    IntAttr,
    IntegerAttr,
    IntegerType,
    ModuleOp,
    StringAttr,
    UnregisteredOp,
)
from xdsl.ir import Attribute, Block, Operation, SSAValue
from xdsl.irdl import IRDLOperation, operand_def, irdl_op_definition, result_def
from xdsl.utils.exceptions import VerifyException

from kernel_gen.dialect.dma import DmaAllocOp, DmaViewOp
from kernel_gen.dialect.kernel import KernelBinaryElewiseOp, KernelMatmulOp
from kernel_gen.dialect.nn import NnMemoryType
from kernel_gen.dialect.symbol import (
    SymbolDimType,
    SymbolForOp,
    SymbolGetDimOp,
    SymbolIterType,
    SymbolMulOp,
    SymbolValueType,
)
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
    最后一次更改: 金铲铲大作战

    功能说明:
    - 统一保存 loop 的 axis/tile 名称与 helper op。
    - 保存 `tuner.param` 与 `symbol.for` 的组合关系，便于后续插入与嵌套。

    使用示例:
    - spec = _TileLoopSpec(
        axis=0,
        tile_name="TILE_D0",
        tile_param=tile_param,
        tile_param_inserted=True,
        start=start,
        end=end,
        iter_type=iter_type,
        block=block,
        loop=loop,
      )

    关联文件:
    - spec: [spec/pass/lowering/tile.md](spec/pass/lowering/tile.md)
    - test: [test/pass/test_lowering_tile.py](test/pass/test_lowering_tile.py)
    - 功能实现: [kernel_gen/passes/lowering/tile.py](kernel_gen/passes/lowering/tile.py)
    """

    axis: int
    tile_name: str
    tile_param: TunerParamOp
    tile_param_inserted: bool
    start: Operation
    end: SymbolGetDimOp
    iter_type: SymbolIterType
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


def _symbol_expr_from_value(value: SSAValue) -> str:
    """从 `!symbol.int<"...">` SSA 获取表达式字符串。

    创建者: 金铲铲大作战
    最后一次更改: 金铲铲大作战

    功能说明:
    - 提取 `SymbolValueType` 内的表达式字符串，用于构造 `symbol.iter`。
    - 若类型不是 `!symbol.int<"...">`，抛出 tile pass 错误。

    使用示例:
    - expr = _symbol_expr_from_value(symbol_const.result)

    关联文件:
    - spec: [spec/pass/lowering/tile.md](spec/pass/lowering/tile.md)
    - test: [test/pass/test_lowering_tile.py](test/pass/test_lowering_tile.py)
    - 功能实现: [kernel_gen/passes/lowering/tile.py](kernel_gen/passes/lowering/tile.py)
    """

    value_type = value.type
    if not isinstance(value_type, SymbolValueType):
        _raise_tile_error("TilePassRankMismatch", "tile helper expects !symbol.int values")
    return value_type.expr.expr.data


def _make_symbol_const(value: int) -> Operation:
    """构造 tile pass 需要的 `symbol.const` 常量 op。

    创建者: 金铲铲大作战
    最后一次更改: 金铲铲大作战

    功能说明:
    - 使用 `UnregisteredOp` 生成带 `value` property 的 `"symbol.const"`。
    - 输出文本与 expectation 中的 `"symbol.const"() <{value = ...}>` 对齐。

    使用示例:
    - zero = _make_symbol_const(0)
    - one = _make_symbol_const(1)

    关联文件:
    - spec: [spec/dialect/symbol.md](spec/dialect/symbol.md)
    - test: [test/pass/test_lowering_tile.py](test/pass/test_lowering_tile.py)
    - 功能实现: [kernel_gen/passes/lowering/tile.py](kernel_gen/passes/lowering/tile.py)
    """

    op_cls = UnregisteredOp.with_name("symbol.const")
    value_attr = IntegerAttr(value, IntegerType(64))
    result_type = SymbolValueType.from_expr(str(value))
    return op_cls.create(properties={"value": value_attr}, result_types=[result_type])


def _parse_tile_analysis_roles(op: Operation) -> list[list[str]]:
    """解析并校验 tile.analysis 角色矩阵。

    创建者: 金铲铲大作战
    最后一次更改: 金铲铲大作战

    功能说明:
    - 读取 `tile.analysis` 并转为字符串矩阵。
    - 仅接受 `elewise` 与 `expand` 标签。

    使用示例:
    - roles = _parse_tile_analysis_roles(kernel_op)

    关联文件:
    - spec: [spec/pass/lowering/tile.md](spec/pass/lowering/tile.md)
    - test: [test/pass/test_lowering_tile.py](test/pass/test_lowering_tile.py)
    - 功能实现: [kernel_gen/passes/lowering/tile.py](kernel_gen/passes/lowering/tile.py)
    """

    attr = op.attributes.get("tile.analysis")
    if not isinstance(attr, ArrayAttr):
        _raise_tile_error("TilePassUnsupportedOp", "tile.analysis must be ArrayAttr")
    roles: list[list[str]] = []
    for row_attr in attr.data:
        if not isinstance(row_attr, ArrayAttr):
            _raise_tile_error("TilePassUnsupportedOp", "tile.analysis row must be ArrayAttr")
        row_roles: list[str] = []
        for entry in row_attr.data:
            if not isinstance(entry, StringAttr):
                _raise_tile_error("TilePassUnsupportedOp", "tile.analysis entry must be StringAttr")
            role = entry.data
            if role not in {"elewise", "expand"}:
                _raise_tile_error("TilePassUnsupportedOp", f"tile.analysis role {role!r} is unsupported")
            row_roles.append(role)
        roles.append(row_roles)
    if not roles:
        _raise_tile_error("TilePassUnsupportedOp", "tile.analysis must not be empty")
    return roles


def _loop_axes_from_roles(roles: list[list[str]]) -> list[int]:
    """从角色矩阵推导需要 loop 的轴。

    创建者: 金铲铲大作战
    最后一次更改: 金铲铲大作战

    功能说明:
    - 当所有 operand 在某个轴上均为 `elewise` 时，该轴进入 loop。
    - 其他角色组合（包含 `expand`）不会生成 loop。

    使用示例:
    - loop_axes = _loop_axes_from_roles([["elewise", "elewise"], ["expand", "elewise"]])

    关联文件:
    - spec: [spec/pass/lowering/tile.md](spec/pass/lowering/tile.md)
    - test: [test/pass/test_lowering_tile.py](test/pass/test_lowering_tile.py)
    - 功能实现: [kernel_gen/passes/lowering/tile.py](kernel_gen/passes/lowering/tile.py)
    """

    if not roles:
        return []
    rank = len(roles[0])
    for row in roles:
        if len(row) != rank:
            _raise_tile_error("TilePassRankMismatch", "tile.analysis roles must share the same rank")
    loop_axes: list[int] = []
    for axis in range(rank):
        if all(row[axis] == "elewise" for row in roles):
            loop_axes.append(axis)
    return loop_axes


def _resolve_tile_loop_names(
    func_op: func.FuncOp,
    loop_axes: list[int],
    rank: int,
) -> list[str]:
    """为 loop 轴生成 tile 名称列表。

    创建者: 金铲铲大作战
    最后一次更改: 金铲铲大作战

    功能说明:
    - 默认按 loop 顺序生成 `TILE_D0`、`TILE_D1`...
    - 若存在 kernel_split 且命中 loop 轴，则覆盖对应名称。

    使用示例:
    - tile_names = _resolve_tile_loop_names(func_op, [1], rank=2)

    关联文件:
    - spec: [spec/pass/lowering/tile.md](spec/pass/lowering/tile.md)
    - test: [test/pass/test_lowering_tile.py](test/pass/test_lowering_tile.py)
    - 功能实现: [kernel_gen/passes/lowering/tile.py](kernel_gen/passes/lowering/tile.py)
    """

    tile_names = [f"TILE_D{index}" for index in range(len(loop_axes))]
    kernel_split_spec = _read_kernel_split_tile_spec(func_op, rank)
    if kernel_split_spec is not None:
        axis, tile_name = kernel_split_spec
        if axis in loop_axes:
            tile_names[loop_axes.index(axis)] = tile_name
    _validate_tile_name_uniqueness(tile_names)
    return tile_names


def _build_axis_helpers(reference_memory: SSAValue) -> tuple[list[Operation], list[SymbolGetDimOp]]:
    """构造每个轴的 `symbol.const 0` 与 `symbol.get_dim`。

    创建者: 金铲铲大作战
    最后一次更改: 金铲铲大作战

    功能说明:
    - 为每个 axis 生成 `symbol.const 0` 与 `symbol.get_dim`。
    - 便于统一生成 loop 起点、offset 与非 loop 形状。

    使用示例:
    - zeros, dims = _build_axis_helpers(reference_memory)

    关联文件:
    - spec: [spec/pass/lowering/tile.md](spec/pass/lowering/tile.md)
    - test: [test/pass/test_lowering_tile.py](test/pass/test_lowering_tile.py)
    - 功能实现: [kernel_gen/passes/lowering/tile.py](kernel_gen/passes/lowering/tile.py)
    """

    mem_type = reference_memory.type
    if not isinstance(mem_type, NnMemoryType):
        _raise_tile_error("TilePassRankMismatch", "reference memory must be nn.memory")
    rank = len(mem_type.shape.data)
    zeros = [_make_symbol_const(0) for _ in range(rank)]
    dims = [SymbolGetDimOp(reference_memory, axis) for axis in range(rank)]
    return zeros, dims


def _build_tile_only_loop_specs(
    func_op: func.FuncOp,
    block: Block,
    loop_axes: list[int],
    tile_names: list[str],
    axis_zeros: list[Operation],
    axis_dims: list[SymbolGetDimOp],
) -> list[_TileLoopSpec]:
    """构造 tile-only 的 loop 规格列表。

    创建者: 金铲铲大作战
    最后一次更改: 金铲铲大作战

    功能说明:
    - 按 loop 轴与 tile 名称构造 `tuner.param` 与 `symbol.for`。
    - 使用 axis 对应的 `symbol.const 0` 与 `symbol.get_dim` 作为起止边界。

    使用示例:
    - specs = _build_tile_only_loop_specs(func_op, block, [1], ["TILE_D0"], zeros, dims)

    关联文件:
    - spec: [spec/pass/lowering/tile.md](spec/pass/lowering/tile.md)
    - test: [test/pass/test_lowering_tile.py](test/pass/test_lowering_tile.py)
    - 功能实现: [kernel_gen/passes/lowering/tile.py](kernel_gen/passes/lowering/tile.py)
    """

    specs: list[_TileLoopSpec] = []
    for loop_index, axis in enumerate(loop_axes):
        tile_name = tile_names[loop_index]
        tile_param, inserted = _find_or_insert_tile_param(block, tile_name)
        start_value = axis_zeros[axis]
        end_value = axis_dims[axis]
        start_expr = _symbol_expr_from_value(start_value.results[0])
        end_expr = _symbol_expr_from_value(end_value.result)
        step_expr = _symbol_expr_from_value(tile_param.result)
        iter_type = SymbolIterType.from_bounds(start_expr, end_expr, step_expr)
        loop_block = Block(arg_types=[iter_type])
        loop_op = SymbolForOp(start_value.results[0], end_value.result, tile_param.result, loop_block)
        specs.append(
            _TileLoopSpec(
                axis=axis,
                tile_name=tile_name,
                tile_param=tile_param,
                tile_param_inserted=inserted,
                start=start_value,
                end=end_value,
                iter_type=iter_type,
                block=loop_block,
                loop=loop_op,
            )
        )
    return specs


def _tile_name_from_dim(dim: Attribute, axis: int) -> str:
    """根据维度条目生成 tile 名称。

    创建者: 小李飞刀
    最后一次更改: 金铲铲大作战

    功能说明:
    - 默认使用 `TILE_D<axis>`。
    - 维度内容不再参与默认命名，避免静态/动态路径分叉。

    使用示例:
    - tile_name = _tile_name_from_dim(StringAttr("M"), 1)

    关联文件:
    - spec: [spec/pass/lowering/tile.md](spec/pass/lowering/tile.md)
    - test: [test/pass/test_lowering_tile.py](test/pass/test_lowering_tile.py)
    - 功能实现: [kernel_gen/passes/lowering/tile.py](kernel_gen/passes/lowering/tile.py)
    """

    if isinstance(dim, (StringAttr, IntAttr)):
        return f"TILE_D{axis}"
    _raise_tile_error("TilePassUnsupportedOp", "unsupported memory dim entry for tile")
    return "TILE_UNREACHABLE"


def _build_view_type(
    source_type: NnMemoryType,
    shape_attrs: list[Attribute],
    stride_attrs: list[Attribute],
) -> NnMemoryType:
    """构造 dma.view 的结果类型。

    创建者: 小李飞刀
    最后一次更改: 金铲铲大作战

    功能说明:
    - 形状与步长使用显式 attr 列表，保持与 IR 输出一致。

    使用示例:
    - view_type = _build_view_type(
        source_type,
        [StringAttr("TILE_M"), StringAttr("TILE_N")],
        [StringAttr("TILE_N"), IntAttr(1)],
      )

    关联文件:
    - spec: [spec/pass/lowering/tile.md](spec/pass/lowering/tile.md)
    - test: [test/pass/test_lowering_tile.py](test/pass/test_lowering_tile.py)
    - 功能实现: [kernel_gen/passes/lowering/tile.py](kernel_gen/passes/lowering/tile.py)
    """

    shape_attr = ArrayAttr(list(shape_attrs))
    stride_attr = ArrayAttr(list(stride_attrs))
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
    - 否则创建新的 `tuner.param : !symbol.int<tile>`。
    - 若同名 `tuner.param` 出现多次，视为重复冲突。

    使用示例:
    - tile_param, inserted = _find_or_insert_tile_param(block, "TILE_M")

    关联文件:
    - spec: [spec/pass/lowering/tile.md](spec/pass/lowering/tile.md)
    - test: [test/pass/test_lowering_tile.py](test/pass/test_lowering_tile.py)
    - 功能实现: [kernel_gen/passes/lowering/tile.py](kernel_gen/passes/lowering/tile.py)
    """

    try:
        SymbolValueType.from_expr(tile_name).verify()
    except VerifyException as exc:
        _raise_tile_error("TilePassUnsupportedOp", f"tile name {tile_name!r} is invalid: {exc}")
        raise
    expected_type = SymbolValueType.from_expr(tile_name)

    matches: list[TunerParamOp] = []
    for op in block.ops:
        if isinstance(op, TunerParamOp) and op.result.type == expected_type:
            matches.append(op)
    if len(matches) > 1:
        _raise_tile_error("TilePassDuplicateTileParam", f"duplicate tuner.param for tile {tile_name}")
    def _set_tile_param_name(op: TunerParamOp) -> None:
        if not tile_name.startswith(("TILE_B", "TILE_M", "TILE_E")):
            return
        tile_suffix = tile_name
        if tile_suffix.startswith("TILE_"):
            tile_suffix = tile_suffix[len("TILE_") :]
        hint = tile_suffix.lower()
        if not hint:
            return
        name_hint = getattr(op.result, "name_hint", None)
        if not isinstance(name_hint, str) or not name_hint:
            op.result.name_hint = hint

    if matches:
        _set_tile_param_name(matches[0])
        return matches[0], False
    op = TunerParamOp(expected_type)
    _set_tile_param_name(op)
    return op, True


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
    最后一次更改: 金铲铲大作战

    功能说明:
    - 按 reference memory 的 rank 生成 N 组 loop 规格。
    - 为每个轴生成 `tuner.param` 与 `symbol.for` 迭代边界。

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
        start_value = _make_symbol_const(0)
        end_value = SymbolGetDimOp(reference_memory, axis)
        start_expr = _symbol_expr_from_value(start_value.results[0])
        end_expr = _symbol_expr_from_value(end_value.result)
        step_expr = _symbol_expr_from_value(tile_param.result)
        iter_type = SymbolIterType.from_bounds(start_expr, end_expr, step_expr)
        loop_block = Block(arg_types=[iter_type])
        loop_op = SymbolForOp(start_value.results[0], end_value.result, tile_param.result, loop_block)
        specs.append(
            _TileLoopSpec(
                axis=axis,
                tile_name=tile_name,
                tile_param=tile_param,
                tile_param_inserted=inserted,
                start=start_value,
                end=end_value,
                iter_type=iter_type,
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
    最后一次更改: 金铲铲大作战

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

    tile_params: list[tuple[str, TunerParamOp, bool]] = []
    for tile_name in tile_names:
        tile_param, inserted = _find_or_insert_tile_param(block, tile_name)
        tile_params.append((tile_name, tile_param, inserted))
    tile_param_map = {name: (param, inserted) for name, param, inserted in tile_params}

    specs: list[_TileLoopSpec] = []
    for axis, tile_name in enumerate(tile_names):
        tile_param, tile_param_inserted = tile_param_map[tile_name]
        start_value = _make_symbol_const(0)
        if axis == 0:
            end_value = SymbolGetDimOp(out, 0)
        elif axis == 1:
            end_value = SymbolGetDimOp(out, 1)
        else:
            end_value = SymbolGetDimOp(lhs, 1)
        start_expr = _symbol_expr_from_value(start_value.results[0])
        end_expr = _symbol_expr_from_value(end_value.result)
        step_expr = _symbol_expr_from_value(tile_param.result)
        iter_type = SymbolIterType.from_bounds(start_expr, end_expr, step_expr)
        loop_block = Block(arg_types=[iter_type])
        loop_op = SymbolForOp(start_value.results[0], end_value.result, tile_param.result, loop_block)
        specs.append(
            _TileLoopSpec(
                axis=axis,
                tile_name=tile_name,
                tile_param=tile_param,
                tile_param_inserted=tile_param_inserted,
                start=start_value,
                end=end_value,
                iter_type=iter_type,
                block=loop_block,
                loop=loop_op,
            )
        )
    return specs


def _validate_matmul_operands(
    lhs: SSAValue,
    rhs: SSAValue,
    out: SSAValue,
) -> tuple[NnMemoryType, NnMemoryType, NnMemoryType]:
    """校验 matmul 的输入输出类型与维度契约。

    创建者: 金铲铲大作战
    最后一次更改: 金铲铲大作战

    功能说明:
    - 要求 lhs/rhs/out 均为 rank-2 的 `nn.memory`。
    - 要求 contracting 维一致，且输出形状与输入一致。

    使用示例:
    - lhs_type, rhs_type, out_type = _validate_matmul_operands(lhs, rhs, out)

    关联文件:
    - spec: [spec/pass/lowering/tile.md](spec/pass/lowering/tile.md)
    - test: [test/pass/test_lowering_tile.py](test/pass/test_lowering_tile.py)
    - 功能实现: [kernel_gen/passes/lowering/tile.py](kernel_gen/passes/lowering/tile.py)
    """

    if not isinstance(lhs.type, NnMemoryType) or not isinstance(rhs.type, NnMemoryType) or not isinstance(
        out.type, NnMemoryType
    ):
        _raise_tile_error("TilePassRankMismatch", "matmul operands must be nn.memory")
    lhs_type = lhs.type
    rhs_type = rhs.type
    out_type = out.type
    if len(lhs_type.shape.data) != 2 or len(rhs_type.shape.data) != 2 or len(out_type.shape.data) != 2:
        _raise_tile_error("TilePassRankMismatch", "matmul operands must be rank-2")
    if lhs_type.shape.data[1] != rhs_type.shape.data[0]:
        _raise_tile_error("TilePassRankMismatch", "matmul contracting dimensions must match")
    if lhs_type.shape.data[0] != out_type.shape.data[0] or rhs_type.shape.data[1] != out_type.shape.data[1]:
        _raise_tile_error("TilePassRankMismatch", "matmul output shape must match lhs/rhs")
    return lhs_type, rhs_type, out_type


def _insert_tile_helpers(
    block: Block,
    specs: list[_TileLoopSpec],
    axis_zeros: list[Operation],
    axis_dims: list[SymbolGetDimOp],
    return_op: Operation,
) -> None:
    """将 tile helper ops 插入函数体。

    创建者: 小李飞刀
    最后一次更改: 金铲铲大作战

    功能说明:
    - 先插入 `tuner.param`（若新增）。
    - 再按 axis 顺序插入 `symbol.const 0` 与 `symbol.get_dim`。
    - 最后插入最外层 `symbol.for`。

    使用示例:
    - _insert_tile_helpers(block, specs, axis_zeros, axis_dims, return_op)

    关联文件:
    - spec: [spec/pass/lowering/tile.md](spec/pass/lowering/tile.md)
    - test: [test/pass/test_lowering_tile.py](test/pass/test_lowering_tile.py)
    - 功能实现: [kernel_gen/passes/lowering/tile.py](kernel_gen/passes/lowering/tile.py)
    """

    helper_ops: list[Operation] = []
    for spec in specs:
        if spec.tile_param_inserted:
            helper_ops.append(spec.tile_param)
    for zero_op, dim_op in zip(axis_zeros, axis_dims):
        helper_ops.append(zero_op)
        helper_ops.append(dim_op)
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

    def _visit(op: Operation) -> None:
        if "tile.analysis" in op.attributes:
            op.attributes.pop("tile.analysis", None)
        for region in op.regions:
            for inner_block in region.blocks:
                for inner_op in inner_block.ops:
                    _visit(inner_op)

    for op in block.ops:
        _visit(op)


def _build_elementwise_tile_roles(op: Operation) -> list[list[str]]:
    """构造 elementwise 的 tile.analysis 角色矩阵。

    创建者: 小李飞刀
    最后一次更改: 小李飞刀

    功能说明:
    - 对每个 memory operand 输出全 `elewise` 标签。
    - 若 memory operand 的 rank 不一致，抛出 `TilePassRankMismatch`。
    - 若 shape 内存在重复的符号维度名称，抛出 `TilePassDuplicateTileParam`。

    使用示例:
    - roles = _build_elementwise_tile_roles(kernel_op)

    关联文件:
    - spec: [spec/pass/lowering/tile.md](spec/pass/lowering/tile.md)
    - test: [test/pass/test_lowering_tile.py](test/pass/test_lowering_tile.py)
    - 功能实现: [kernel_gen/passes/lowering/tile.py](kernel_gen/passes/lowering/tile.py)
    """

    memory_values = [
        SSAValue.get(operand)
        for operand in op.operands
        if isinstance(SSAValue.get(operand).type, NnMemoryType)
    ]
    if not memory_values:
        return []
    first_type = memory_values[0].type
    if not isinstance(first_type, NnMemoryType):
        return []
    rank = len(first_type.shape.data)
    for value in memory_values:
        mem_type = value.type
        if not isinstance(mem_type, NnMemoryType):
            _raise_tile_error("TilePassRankMismatch", "tile operands must be nn.memory")
        if len(mem_type.shape.data) != rank:
            _raise_tile_error("TilePassRankMismatch", "tile operands must share the same rank")
        shape_names = [
            dim.data for dim in mem_type.shape.data if isinstance(dim, StringAttr)
        ]
        if len(shape_names) != len(set(shape_names)):
            _raise_tile_error("TilePassDuplicateTileParam", "tile names must be unique per function")
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


def _build_contiguous_stride(
    inner_block: Block,
    shape_values: list[SSAValue],
    shape_attrs: list[Attribute],
    const_one: Operation,
) -> tuple[list[SSAValue], list[Attribute]]:
    """构造 row-major contiguous stride 的 SSA 与类型 attr。

    创建者: 金铲铲大作战
    最后一次更改: 金铲铲大作战

    功能说明:
    - rank=1 时 stride 固定为 `1`。
    - rank=2 时 stride[0]=shape[1]，stride[1]=1。
    - rank>2 时使用 `symbol.mul` 计算乘积。

    使用示例:
    - stride_values, stride_attrs = _build_contiguous_stride(inner_block, shape_values, shape_attrs, const_one)

    关联文件:
    - spec: [spec/pass/lowering/tile.md](spec/pass/lowering/tile.md)
    - test: [test/pass/test_lowering_tile.py](test/pass/test_lowering_tile.py)
    - 功能实现: [kernel_gen/passes/lowering/tile.py](kernel_gen/passes/lowering/tile.py)
    """

    rank = len(shape_values)
    if rank == 0:
        return [], []
    if rank == 1:
        return [const_one.results[0]], [IntAttr(1)]
    if rank == 2:
        return [shape_values[1], const_one.results[0]], [shape_attrs[1], IntAttr(1)]

    stride_values: list[SSAValue] = []
    stride_attrs: list[Attribute] = []
    for axis in range(rank):
        if axis == rank - 1:
            stride_values.append(const_one.results[0])
            stride_attrs.append(IntAttr(1))
            continue
        product_value = shape_values[axis + 1]
        product_attr = shape_attrs[axis + 1]
        for next_value, next_attr in zip(shape_values[axis + 2 :], shape_attrs[axis + 2 :]):
            mul_op = SymbolMulOp(product_value, next_value, product_value.type)
            inner_block.add_op(mul_op)
            product_value = mul_op.result
            product_attr = StringAttr(
                f"{product_attr.data} * {next_attr.data}"
                if isinstance(product_attr, StringAttr) and isinstance(next_attr, StringAttr)
                else "symbol.mul"
            )
        stride_values.append(product_value)
        stride_attrs.append(product_attr)
    return stride_values, stride_attrs


def _insert_tile_only_views_and_ops(
    inner_block: Block,
    loop_axes: list[int],
    loop_vars: dict[int, SSAValue],
    tile_params: dict[int, TunerParamOp],
    tile_names: dict[int, str],
    axis_zeros: list[Operation],
    axis_dims: list[SymbolGetDimOp],
    reference_shape_attrs: list[Attribute],
    operand_values: list[SSAValue],
    roles: list[list[str]],
    ops_to_move: list[Operation],
) -> None:
    """在最内层 block 插入 view 并移动目标 op。

    创建者: 金铲铲大作战
    最后一次更改: 金铲铲大作战

    功能说明:
    - 按 `tile.analysis` 角色矩阵生成 `dma.view`。
    - `elewise` 轴使用 reference shape；`expand` 轴使用常量 1。
    - loop 轴使用 tile 参数，offset 使用 loop iter。

    使用示例:
    - _insert_tile_only_views_and_ops(
        inner_block,
        loop_axes,
        loop_vars,
        tile_params,
        tile_names,
        axis_zeros,
        axis_dims,
        reference_shape_attrs,
        operand_values,
        roles,
        ops_to_move,
      )

    关联文件:
    - spec: [spec/pass/lowering/tile.md](spec/pass/lowering/tile.md)
    - test: [test/pass/test_lowering_tile.py](test/pass/test_lowering_tile.py)
    - 功能实现: [kernel_gen/passes/lowering/tile.py](kernel_gen/passes/lowering/tile.py)
    """

    const_one = _make_symbol_const(1)
    inner_block.add_op(const_one)
    view_map: dict[SSAValue, SSAValue] = {}
    for operand_index, memory in enumerate(operand_values):
        mem_type = memory.type
        if not isinstance(mem_type, NnMemoryType):
            _raise_tile_error("TilePassRankMismatch", "tile operands must be nn.memory")
        role_row = roles[operand_index]
        if len(role_row) != len(reference_shape_attrs):
            _raise_tile_error("TilePassRankMismatch", "tile.analysis rank mismatch")

        offsets: list[SSAValue] = []
        shape_values: list[SSAValue] = []
        shape_attrs: list[Attribute] = []
        for axis, role in enumerate(role_row):
            if axis in loop_axes:
                offsets.append(loop_vars[axis])
                tile_param = tile_params[axis]
                shape_values.append(tile_param.result)
                shape_attrs.append(StringAttr(tile_names[axis]))
                continue
            offsets.append(axis_zeros[axis].results[0])
            if role == "expand":
                shape_values.append(const_one.results[0])
                shape_attrs.append(IntAttr(1))
            else:
                shape_values.append(axis_dims[axis].result)
                shape_attrs.append(reference_shape_attrs[axis])

        stride_values, stride_attrs = _build_contiguous_stride(
            inner_block,
            shape_values,
            shape_attrs,
            const_one,
        )
        view_type = _build_view_type(mem_type, shape_attrs, stride_attrs)
        if len(mem_type.shape.data) != len(view_type.shape.data):
            view_cls = UnregisteredOp.with_name("dma.view")
            operand_segment = DenseArrayBase.from_list(
                IntegerType(32),
                [1, len(offsets), len(shape_values), len(stride_values)],
            )
            view_op = view_cls.create(
                operands=[memory, *offsets, *shape_values, *stride_values],
                result_types=[view_type],
                properties={"operandSegmentSizes": operand_segment},
            )
        else:
            view_op = DmaViewOp(
                memory,
                offsets=offsets,
                shape=shape_values,
                stride=stride_values,
                result_type=view_type,
            )
        inner_block.add_op(view_op)
        view_map[memory] = view_op.results[0]

    for op in ops_to_move:
        op.detach()
        if "tile.analysis" in op.attributes:
            op.attributes.pop("tile.analysis", None)
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
    最后一次更改: 金铲铲大作战

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
    const_one = _make_symbol_const(1)
    inner_block.add_op(const_one)

    def _make_view(
        source: SSAValue,
        offsets: list[SSAValue],
        shape: list[SSAValue],
        shape_attrs: list[Attribute],
    ) -> SSAValue:
        """构造 matmul 分支的 dma.view 并返回 view SSA。

        创建者: 小李飞刀
        最后一次更改: 金铲铲大作战

        功能说明:
        - 按给定 offsets/shape 生成 `dma.view`。
        - 统一封装 view 结果类型构造逻辑。

        使用示例:
        - lhs_view = _make_view(
            lhs,
            [m_var, k_var],
            [step_m, step_k],
            [StringAttr("TILE_M"), StringAttr("TILE_K")],
          )

        关联文件:
        - spec: [spec/pass/lowering/tile.md](spec/pass/lowering/tile.md)
        - test: [test/pass/test_lowering_tile.py](test/pass/test_lowering_tile.py)
        - 功能实现: [kernel_gen/passes/lowering/tile.py](kernel_gen/passes/lowering/tile.py)
        """
        mem_type = source.type
        if not isinstance(mem_type, NnMemoryType):
            _raise_tile_error("TilePassRankMismatch", "matmul operands must be nn.memory")
        stride_values = [shape[1], const_one.results[0]]
        stride_attrs = [shape_attrs[1], IntAttr(1)]
        view_type = _build_view_type(mem_type, shape_attrs, stride_attrs)
        view_op = DmaViewOp(
            source,
            offsets=offsets,
            shape=shape,
            stride=stride_values,
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
                shape_attrs=[StringAttr("TILE_M"), StringAttr("TILE_K")],
            )
        if rhs not in view_map:
            view_map[rhs] = _make_view(
                rhs,
                offsets=[k_var, n_var],
                shape=[step_k, step_n],
                shape_attrs=[StringAttr("TILE_K"), StringAttr("TILE_N")],
            )
        if out not in view_map:
            view_map[out] = _make_view(
                out,
                offsets=[m_var, n_var],
                shape=[step_m, step_n],
                shape_attrs=[StringAttr("TILE_M"), StringAttr("TILE_N")],
            )

    for op in kernel_ops:
        op.detach()
        for index, operand in enumerate(op.operands):
            value = SSAValue.get(operand)
            if value in view_map:
                op.operands[index] = view_map[value]
        inner_block.add_op(op)


def _append_tile_only_stage(
    func_op: func.FuncOp,
    block: Block,
    stage_op: Operation,
    loop_prefix: str,
) -> None:
    """追加 tile-only stage 的 loop/view 改写。

    创建者: 金铲铲大作战
    最后一次更改: 金铲铲大作战

    功能说明:
    - 支持 `dma.broadcast` 与 elementwise kernel 的分支改写。
    - 使用前缀 `loop_prefix` 生成 `TILE_*` 名称（如 `TILE_B0`、`TILE_E0`）。
    - 生成 `symbol.const` / `symbol.get_dim` / `symbol.for` 并将 op 移入最内层 loop。

    使用示例:
    - _append_tile_only_stage(func_op, block, broadcast_op, "TILE_B")
    - _append_tile_only_stage(func_op, block, kernel_op, "TILE_E")

    关联文件:
    - spec: [spec/pass/lowering/tile.md](spec/pass/lowering/tile.md)
    - test: [test/pass/test_lowering_tile.py](test/pass/test_lowering_tile.py)
    - 功能实现: [kernel_gen/passes/lowering/tile.py](kernel_gen/passes/lowering/tile.py)
    """

    roles = _parse_tile_analysis_roles(stage_op)
    operand_values = [SSAValue.get(operand) for operand in stage_op.operands]
    if len(roles) != len(operand_values):
        _raise_tile_error("TilePassRankMismatch", "tile.analysis rows must match operands")
    reference_memory = operand_values[0]
    if stage_op.name.startswith("kernel."):
        for value in reversed(operand_values):
            if isinstance(value.type, NnMemoryType):
                reference_memory = value
                break
    if not isinstance(reference_memory.type, NnMemoryType):
        _raise_tile_error("TilePassRankMismatch", "tile reference must be nn.memory")
    loop_axes = _loop_axes_from_roles(roles)
    tile_names = [f"{loop_prefix}{index}" for index in range(len(loop_axes))]
    axis_zeros, axis_dims = _build_axis_helpers(reference_memory)
    specs = _build_tile_only_loop_specs(
        func_op,
        block,
        loop_axes,
        tile_names,
        axis_zeros,
        axis_dims,
    )

    helper_ops: list[Operation] = []
    for zero_op, dim_op in zip(axis_zeros, axis_dims):
        helper_ops.append(zero_op)
        helper_ops.append(dim_op)
    if specs:
        helper_ops.append(specs[0].loop)
    block.insert_ops_before(helper_ops, stage_op)

    inner_block = _nest_loops(specs)
    if inner_block is None:
        if "tile.analysis" in stage_op.attributes:
            stage_op.attributes.pop("tile.analysis", None)
        return

    loop_vars = {spec.axis: spec.block.args[0] for spec in specs}
    tile_params = {spec.axis: spec.tile_param for spec in specs}
    tile_name_map = {spec.axis: spec.tile_name for spec in specs}
    reference_shape_attrs = list(reference_memory.type.shape.data)
    _insert_tile_only_views_and_ops(
        inner_block,
        loop_axes,
        loop_vars,
        tile_params,
        tile_name_map,
        axis_zeros,
        axis_dims,
        reference_shape_attrs,
        operand_values,
        roles,
        [stage_op],
    )


def _append_matmul_stage(
    block: Block,
    matmul_op: Operation,
    tile_m0: TunerParamOp,
    tile_m1: TunerParamOp,
) -> None:
    """追加 matmul stage 的 loop/view 改写。

    创建者: 金铲铲大作战
    最后一次更改: 金铲铲大作战

    功能说明:
    - 使用 `TILE_M0` / `TILE_M1` 构造 M/N 维 loop。
    - 插入 `symbol.const` / `symbol.get_dim` 与对应 `dma.view`。
    - 在最内层 loop 内创建 `kernel.matmul`。

    使用示例:
    - _append_matmul_stage(block, matmul_op, tile_m0, tile_m1)

    关联文件:
    - spec: [spec/pass/lowering/tile.md](spec/pass/lowering/tile.md)
    - test: [test/pass/test_lowering_tile.py](test/pass/test_lowering_tile.py)
    - 功能实现: [kernel_gen/passes/lowering/tile.py](kernel_gen/passes/lowering/tile.py)
    """

    operands = [SSAValue.get(operand) for operand in matmul_op.operands]
    if len(operands) < 3:
        _raise_tile_error("TilePassRankMismatch", "matmul requires 3 operands")
    lhs, rhs, out = operands[0], operands[1], operands[-1]
    lhs_type, rhs_type, out_type = _validate_matmul_operands(lhs, rhs, out)

    const_zero_m = _make_symbol_const(0)
    dim_m = SymbolGetDimOp(lhs, 0)
    const_zero_n = _make_symbol_const(0)
    dim_n = SymbolGetDimOp(rhs, 1)
    dim_k = SymbolGetDimOp(lhs, 1)

    m_iter = SymbolIterType.from_bounds(
        _symbol_expr_from_value(const_zero_m.results[0]),
        _symbol_expr_from_value(dim_m.result),
        _symbol_expr_from_value(tile_m0.result),
    )
    m_block = Block(arg_types=[m_iter])
    m_loop = SymbolForOp(const_zero_m.results[0], dim_m.result, tile_m0.result, m_block)

    n_iter = SymbolIterType.from_bounds(
        _symbol_expr_from_value(const_zero_n.results[0]),
        _symbol_expr_from_value(dim_n.result),
        _symbol_expr_from_value(tile_m1.result),
    )
    n_block = Block(arg_types=[n_iter])
    n_loop = SymbolForOp(const_zero_n.results[0], dim_n.result, tile_m1.result, n_block)
    m_block.add_op(n_loop)

    block.insert_ops_before(
        [const_zero_m, dim_m, const_zero_n, dim_n, dim_k, m_loop],
        matmul_op,
    )

    const_one = _make_symbol_const(1)
    n_block.add_op(const_one)
    m_iter_value = m_block.args[0]
    n_iter_value = n_block.args[0]

    lhs_view_type = _build_view_type(
        lhs_type,
        [StringAttr("TILE_M0"), lhs_type.shape.data[1]],
        [lhs_type.stride.data[0], IntAttr(1)],
    )
    lhs_view = DmaViewOp(
        lhs,
        offsets=[m_iter_value, const_zero_m.results[0]],
        shape=[tile_m0.result, dim_k.result],
        stride=[dim_k.result, const_one.results[0]],
        result_type=lhs_view_type,
    )
    rhs_view_type = _build_view_type(
        rhs_type,
        [rhs_type.shape.data[0], StringAttr("TILE_M1")],
        [StringAttr("TILE_M1"), IntAttr(1)],
    )
    rhs_view = DmaViewOp(
        rhs,
        offsets=[const_zero_m.results[0], n_iter_value],
        shape=[dim_k.result, tile_m1.result],
        stride=[tile_m1.result, const_one.results[0]],
        result_type=rhs_view_type,
    )
    out_view_type = _build_view_type(
        out_type,
        [StringAttr("TILE_M0"), StringAttr("TILE_M1")],
        [StringAttr("TILE_M1"), IntAttr(1)],
    )
    out_view = DmaViewOp(
        out,
        offsets=[m_iter_value, n_iter_value],
        shape=[tile_m0.result, tile_m1.result],
        stride=[tile_m1.result, const_one.results[0]],
        result_type=out_view_type,
    )
    n_block.add_ops([lhs_view, rhs_view, out_view])

    matmul_op.detach()
    matmul_new = KernelMatmulOp(
        lhs_view.result,
        rhs_view.result,
        out_view.result,
        out_type.space,
    )
    n_block.add_op(matmul_new)


def _rewrite_multi_stage(
    func_op: func.FuncOp,
    block: Block,
    stage_ops: list[Operation],
    return_op: func.ReturnOp,
    tile_reduce: bool,
) -> None:
    """改写包含多 stage 的 tile-only 组合路径。

    创建者: 金铲铲大作战
    最后一次更改: 金铲铲大作战

    功能说明:
    - 支持 `dma.broadcast` + `kernel.matmul` + elementwise 的顺序组合。
    - 多 stage 场景使用 `TILE_B*` / `TILE_M*` / `TILE_E*` 前缀命名。
    - 清理非 stage op，保持输出只含 loop/view/kernel 结构。

    使用示例:
    - _rewrite_multi_stage(func_op, block, stage_ops, return_op, tile_reduce=False)

    关联文件:
    - spec: [spec/pass/lowering/tile.md](spec/pass/lowering/tile.md)
    - test: [test/pass/test_lowering_tile.py](test/pass/test_lowering_tile.py)
    - 功能实现: [kernel_gen/passes/lowering/tile.py](kernel_gen/passes/lowering/tile.py)
    """

    if tile_reduce:
        _raise_tile_error("TilePassUnsupportedOp", "tile-reduce is not supported for multi-stage tile")

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

    stage_specs: list[dict[str, object]] = []
    seen_broadcast = False
    seen_matmul = False
    seen_elementwise = False
    for op in stage_ops:
        if op.name == "dma.broadcast":
            if seen_broadcast:
                _raise_tile_error("TilePassUnsupportedOp", "multiple dma.broadcast are not supported")
            seen_broadcast = True
            roles = _parse_tile_analysis_roles(op)
            operand_values = [SSAValue.get(operand) for operand in op.operands]
            if len(roles) != len(operand_values):
                _raise_tile_error("TilePassRankMismatch", "tile.analysis rows must match broadcast operands")
            reference_memory = operand_values[0]
            if not isinstance(reference_memory.type, NnMemoryType):
                _raise_tile_error("TilePassRankMismatch", "broadcast target must be nn.memory")
            loop_axes = _loop_axes_from_roles(roles)
            tile_names = [f"TILE_B{index}" for index in range(len(loop_axes))]
            stage_specs.append(
                {
                    "kind": "broadcast",
                    "op": op,
                    "tile_names": tile_names,
                }
            )
            continue

        if op.name == "kernel.matmul":
            if seen_matmul:
                _raise_tile_error("TilePassUnsupportedOp", "multiple kernel.matmul are not supported")
            seen_matmul = True
            stage_specs.append(
                {
                    "kind": "matmul",
                    "op": op,
                    "tile_names": ["TILE_M0", "TILE_M1"],
                }
            )
            continue

        if op.name.startswith("kernel."):
            if _is_reduce_kernel(op):
                _raise_tile_error("TilePassUnsupportedOp", "reduce kernel op is not supported")
            if op.name not in allowed_elementwise:
                _raise_tile_error("TilePassUnsupportedOp", f"unsupported kernel op {op.name}")
            if seen_elementwise:
                _raise_tile_error("TilePassUnsupportedOp", "multiple elementwise kernel ops are not supported")
            seen_elementwise = True
            roles = _parse_tile_analysis_roles(op)
            operand_values = [SSAValue.get(operand) for operand in op.operands]
            if len(roles) != len(operand_values):
                _raise_tile_error("TilePassRankMismatch", "tile.analysis rows must match kernel operands")
            reference_memory = operand_values[0]
            if not isinstance(reference_memory.type, NnMemoryType):
                _raise_tile_error("TilePassRankMismatch", "elementwise reference must be nn.memory")
            loop_axes = _loop_axes_from_roles(roles)
            tile_names = [f"TILE_E{index}" for index in range(len(loop_axes))]
            stage_specs.append(
                {
                    "kind": "elementwise",
                    "op": op,
                    "tile_names": tile_names,
                }
            )

    for op in list(block.ops):
        if op not in stage_ops and not isinstance(op, func.ReturnOp):
            op.detach()

    tile_param_ops: list[TunerParamOp] = []
    tile_param_map: dict[str, TunerParamOp] = {}
    for spec in stage_specs:
        for tile_name in spec.get("tile_names", []):
            if tile_name in tile_param_map:
                continue
            tile_param, inserted = _find_or_insert_tile_param(block, tile_name)
            tile_param_map[tile_name] = tile_param
            if inserted:
                tile_param_ops.append(tile_param)

    if tile_param_ops:
        block.insert_ops_before(tile_param_ops, stage_ops[0])

    for spec in stage_specs:
        kind = spec["kind"]
        op = spec["op"]
        if not isinstance(op, Operation):
            continue
        if kind == "broadcast":
            _append_tile_only_stage(func_op, block, op, "TILE_B")
            continue
        if kind == "matmul":
            tile_m0 = tile_param_map["TILE_M0"]
            tile_m1 = tile_param_map["TILE_M1"]
            _append_matmul_stage(block, op, tile_m0, tile_m1)
            continue
        if kind == "elementwise":
            _append_tile_only_stage(func_op, block, op, "TILE_E")

    _clear_tile_analysis(block)
    if not isinstance(block.last_op, func.ReturnOp):
        block.add_op(return_op)


def _rewrite_function(func_op: func.FuncOp, analysis_only: bool, tile_reduce: bool) -> bool:
    """改写单个函数为 tile loop 结构。

    创建者: 小李飞刀
    最后一次更改: 金铲铲大作战

    功能说明:
    - analysis_only=true 时仅输出 `tile.analysis`，不生成 loop/view/helper。
    - analysis_only=false 时先生成 `tile.analysis`，再按角色矩阵改写为 loop + view。
    - tile_reduce 控制 matmul 是否额外切分 reduce 维并生成累加逻辑。
    - 返回值表示是否需要跳过 module.verify 的严格校验。
    - 保持单函数合同，不新增 `func.call`。

    使用示例:
    - skip_verify = _rewrite_function(func_op, analysis_only=False, tile_reduce=True)

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
        return False

    _annotate_tile_analysis(block)

    stage_ops = [
        op for op in block.ops if op.name == "dma.broadcast" or op.name.startswith("kernel.")
    ]
    if len(stage_ops) > 1:
        _rewrite_multi_stage(func_op, block, stage_ops, return_op, tile_reduce)
        return True

    broadcast_ops = [op for op in block.ops if op.name == "dma.broadcast"]

    if broadcast_ops:
        if len(broadcast_ops) != 1:
            _raise_tile_error("TilePassUnsupportedOp", "tile expects a single dma.broadcast op")
        broadcast_op = broadcast_ops[0]
        roles = _parse_tile_analysis_roles(broadcast_op)
        operand_values = [SSAValue.get(operand) for operand in broadcast_op.operands]
        if len(roles) != len(operand_values):
            _raise_tile_error("TilePassRankMismatch", "tile.analysis rows must match broadcast operands")
        reference_memory = operand_values[0]
        if not isinstance(reference_memory.type, NnMemoryType):
            _raise_tile_error("TilePassRankMismatch", "broadcast target must be nn.memory")
        rank = len(reference_memory.type.shape.data)
        loop_axes = _loop_axes_from_roles(roles)
        tile_names = _resolve_tile_loop_names(func_op, loop_axes, rank)
        axis_zeros, axis_dims = _build_axis_helpers(reference_memory)
        specs = _build_tile_only_loop_specs(func_op, block, loop_axes, tile_names, axis_zeros, axis_dims)
        inner_block = _nest_loops(specs)
        _insert_tile_helpers(block, specs, axis_zeros, axis_dims, return_op)
        if inner_block is None:
            _clear_tile_analysis(block)
            return
        loop_vars = {spec.axis: spec.block.args[0] for spec in specs}
        tile_params = {spec.axis: spec.tile_param for spec in specs}
        tile_name_map = {spec.axis: spec.tile_name for spec in specs}
        reference_shape_attrs = list(reference_memory.type.shape.data)
        _insert_tile_only_views_and_ops(
            inner_block,
            loop_axes,
            loop_vars,
            tile_params,
            tile_name_map,
            axis_zeros,
            axis_dims,
            reference_shape_attrs,
            operand_values,
            roles,
            [broadcast_op],
        )
        _clear_tile_analysis(block)
        return False

    mode = _classify_kernel_ops(kernel_ops)
    if mode is None:
        _clear_tile_analysis(block)
        return False

    if mode == "elementwise":
        if len(kernel_ops) != 1:
            _raise_tile_error("TilePassUnsupportedOp", "elementwise expects a single kernel op")
        kernel_op = kernel_ops[0]
        roles = _parse_tile_analysis_roles(kernel_op)
        operand_values = [SSAValue.get(operand) for operand in kernel_op.operands]
        if len(roles) != len(operand_values):
            _raise_tile_error("TilePassRankMismatch", "tile.analysis rows must match kernel operands")
        reference_memory = operand_values[0]
        if not isinstance(reference_memory.type, NnMemoryType):
            _raise_tile_error("TilePassRankMismatch", "elementwise reference must be nn.memory")
        rank = len(reference_memory.type.shape.data)
        loop_axes = _loop_axes_from_roles(roles)
        tile_names = _resolve_tile_loop_names(func_op, loop_axes, rank)
        axis_zeros, axis_dims = _build_axis_helpers(reference_memory)
        specs = _build_tile_only_loop_specs(func_op, block, loop_axes, tile_names, axis_zeros, axis_dims)
        inner_block = _nest_loops(specs)
        _insert_tile_helpers(block, specs, axis_zeros, axis_dims, return_op)
        if inner_block is None:
            _clear_tile_analysis(block)
            return
        loop_vars = {spec.axis: spec.block.args[0] for spec in specs}
        tile_params = {spec.axis: spec.tile_param for spec in specs}
        tile_name_map = {spec.axis: spec.tile_name for spec in specs}
        reference_shape_attrs = list(reference_memory.type.shape.data)
        _insert_tile_only_views_and_ops(
            inner_block,
            loop_axes,
            loop_vars,
            tile_params,
            tile_name_map,
            axis_zeros,
            axis_dims,
            reference_shape_attrs,
            operand_values,
            roles,
            kernel_ops,
        )
        _clear_tile_analysis(block)
        return False

    if mode == "matmul":
        if len(kernel_ops) != 1:
            _raise_tile_error("TilePassUnsupportedOp", "matmul expects single kernel.matmul op")
        matmul_op = kernel_ops[0]
        lhs = SSAValue.get(matmul_op.operands[0])
        rhs = SSAValue.get(matmul_op.operands[1])
        out = SSAValue.get(matmul_op.operands[-1])
        lhs_type, rhs_type, out_type = _validate_matmul_operands(lhs, rhs, out)

        tile_d0, inserted_d0 = _find_or_insert_tile_param(block, "TILE_D0")
        tile_d1, inserted_d1 = _find_or_insert_tile_param(block, "TILE_D1")
        tile_r0: TunerParamOp | None = None
        inserted_r0 = False
        if tile_reduce:
            tile_r0, inserted_r0 = _find_or_insert_tile_param(block, "TILE_R0")

        const_zero_m = _make_symbol_const(0)
        dim_m = SymbolGetDimOp(lhs, 0)
        const_zero_n = _make_symbol_const(0)
        dim_n = SymbolGetDimOp(rhs, 1)
        dim_k = SymbolGetDimOp(lhs, 1)

        d0_iter = SymbolIterType.from_bounds(
            _symbol_expr_from_value(const_zero_m.results[0]),
            _symbol_expr_from_value(dim_m.result),
            _symbol_expr_from_value(tile_d0.result),
        )
        d0_block = Block(arg_types=[d0_iter])
        d0_loop = SymbolForOp(const_zero_m.results[0], dim_m.result, tile_d0.result, d0_block)

        d1_iter = SymbolIterType.from_bounds(
            _symbol_expr_from_value(const_zero_n.results[0]),
            _symbol_expr_from_value(dim_n.result),
            _symbol_expr_from_value(tile_d1.result),
        )
        d1_block = Block(arg_types=[d1_iter])
        d1_loop = SymbolForOp(const_zero_n.results[0], dim_n.result, tile_d1.result, d1_block)
        d0_block.add_op(d1_loop)

        r0_block: Block | None = None
        r0_loop: SymbolForOp | None = None
        if tile_reduce:
            if tile_r0 is None:
                _raise_tile_error("TilePassUnsupportedOp", "tile-reduce=true requires TILE_R0")
            r0_iter = SymbolIterType.from_bounds(
                _symbol_expr_from_value(const_zero_m.results[0]),
                _symbol_expr_from_value(dim_k.result),
                _symbol_expr_from_value(tile_r0.result),
            )
            r0_block = Block(arg_types=[r0_iter])
            r0_loop = SymbolForOp(const_zero_m.results[0], dim_k.result, tile_r0.result, r0_block)

        helper_ops: list[Operation] = []
        if inserted_d0:
            helper_ops.append(tile_d0)
        if inserted_d1:
            helper_ops.append(tile_d1)
        if tile_reduce and inserted_r0 and tile_r0 is not None:
            helper_ops.append(tile_r0)
        helper_ops.extend([const_zero_m, dim_m, const_zero_n, dim_n, dim_k, d0_loop])
        block.insert_ops_before(helper_ops, return_op)

        const_one = _make_symbol_const(1)
        d1_block.add_op(const_one)
        d0_iter_value = d0_block.args[0]
        d1_iter_value = d1_block.args[0]

        if tile_reduce:
            if tile_r0 is None or r0_loop is None or r0_block is None:
                _raise_tile_error("TilePassUnsupportedOp", "tile-reduce=true requires R0 loop")
            out_view_type = _build_view_type(
                out_type,
                [StringAttr("TILE_D0"), StringAttr("TILE_D1")],
                [StringAttr("TILE_D1"), IntAttr(1)],
            )
            out_view = DmaViewOp(
                out,
                offsets=[d0_iter_value, d1_iter_value],
                shape=[tile_d0.result, tile_d1.result],
                stride=[tile_d1.result, const_one.results[0]],
                result_type=out_view_type,
            )
            d1_block.add_op(out_view)

            fill_op_cls = UnregisteredOp.with_name("dma.fill")
            fill_op = fill_op_cls.create(
                operands=[out_view.result, const_zero_m.results[0]],
            )
            d1_block.add_op(fill_op)
            d1_block.add_op(r0_loop)

            r0_iter_value = r0_block.args[0]
            lhs_view_type = _build_view_type(
                lhs_type,
                [StringAttr("TILE_D0"), StringAttr("TILE_R0")],
                [StringAttr("TILE_R0"), IntAttr(1)],
            )
            lhs_view = DmaViewOp(
                lhs,
                offsets=[d0_iter_value, r0_iter_value],
                shape=[tile_d0.result, tile_r0.result],
                stride=[tile_r0.result, const_one.results[0]],
                result_type=lhs_view_type,
            )
            rhs_view_type = _build_view_type(
                rhs_type,
                [StringAttr("TILE_R0"), StringAttr("TILE_D1")],
                [StringAttr("TILE_D1"), IntAttr(1)],
            )
            rhs_view = DmaViewOp(
                rhs,
                offsets=[r0_iter_value, d1_iter_value],
                shape=[tile_r0.result, tile_d1.result],
                stride=[tile_d1.result, const_one.results[0]],
                result_type=rhs_view_type,
            )
            r0_block.add_ops([lhs_view, rhs_view])

            alloc_op_cls = UnregisteredOp.with_name("dma.alloc")
            operand_segment = DenseArrayBase.from_list(IntegerType(32), [0])
            alloc_op = alloc_op_cls.create(
                operands=[],
                result_types=[out_view_type],
                properties={"operandSegmentSizes": operand_segment},
            )
            r0_block.add_op(alloc_op)

            matmul_op.detach()
            matmul_new = KernelMatmulOp(
                lhs_view.result,
                rhs_view.result,
                alloc_op.results[0],
                out_type.space,
            )
            r0_block.add_op(matmul_new)

            add_op = KernelBinaryElewiseOp(
                alloc_op.results[0],
                out_view.result,
                out_view.result,
                kind="add",
                space=out_type.space,
            )
            r0_block.add_op(add_op)
        else:
            lhs_view_type = _build_view_type(
                lhs_type,
                [StringAttr("TILE_D0"), lhs_type.shape.data[1]],
                [lhs_type.stride.data[0], IntAttr(1)],
            )
            lhs_view = DmaViewOp(
                lhs,
                offsets=[d0_iter_value, const_zero_m.results[0]],
                shape=[tile_d0.result, dim_k.result],
                stride=[dim_k.result, const_one.results[0]],
                result_type=lhs_view_type,
            )
            rhs_view_type = _build_view_type(
                rhs_type,
                [rhs_type.shape.data[0], StringAttr("TILE_D1")],
                [StringAttr("TILE_D1"), IntAttr(1)],
            )
            rhs_view = DmaViewOp(
                rhs,
                offsets=[const_zero_m.results[0], d1_iter_value],
                shape=[dim_k.result, tile_d1.result],
                stride=[tile_d1.result, const_one.results[0]],
                result_type=rhs_view_type,
            )
            out_view_type = _build_view_type(
                out_type,
                [StringAttr("TILE_D0"), StringAttr("TILE_D1")],
                [StringAttr("TILE_D1"), IntAttr(1)],
            )
            out_view = DmaViewOp(
                out,
                offsets=[d0_iter_value, d1_iter_value],
                shape=[tile_d0.result, tile_d1.result],
                stride=[tile_d1.result, const_one.results[0]],
                result_type=out_view_type,
            )
            d1_block.add_ops([lhs_view, rhs_view, out_view])

            matmul_op.detach()
            matmul_new = KernelMatmulOp(
                lhs_view.result,
                rhs_view.result,
                out_view.result,
                out_type.space,
            )
            d1_block.add_op(matmul_new)

        _clear_tile_analysis(block)
        return False


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

        skip_verify = False
        for op in module.ops:
            if isinstance(op, func.FuncOp):
                if _rewrite_function(op, analysis_only=self._analysis_only, tile_reduce=self._tile_reduce):
                    skip_verify = True
        try:
            module.verify()
        except VerifyException as exc:
            if skip_verify and "IsolatedFromAbove" in str(exc):
                return module
            _raise_tile_error("TilePassRequiresLoweredKernelIR", str(exc))
        return module


__all__ = [
    "TilePass",
    "TilePassError",
    "TilePassOptionError",
    "_TileSymbolLiteralOp",
    "_TileStepValueOp",
]
