"""kernel split lowering pass.

创建者: 小李飞刀
最后一次更改: 小李飞刀

功能说明:
- 对带 `kernel_split = { axis = <i64>, tile = "<TILE_NAME>" }` 标记的单函数 IR 执行最小显式切分。
- 固化 `tuner.param` 驱动 tile、单函数合同，以及 carry memory / 错误短语的首轮实现。

使用示例:
- from kernel_gen.passes.lowering.kernel_split import KernelSplitPass
- module = KernelSplitPass().run(module)

关联文件:
- spec: spec/pass/lowering/kernel_split.md
- test: test/pass/test_lowering_kernel_split.py
- 功能实现: kernel_gen/passes/lowering/kernel_split.py
"""

from __future__ import annotations

from dataclasses import dataclass

from xdsl.dialects import func
from xdsl.dialects.builtin import DictionaryAttr, IntAttr, ModuleOp, StringAttr
from xdsl.ir import Block, Operation, SSAValue
from xdsl.irdl import IRDLOperation, operand_def, irdl_op_definition, result_def
from xdsl.utils.exceptions import VerifyException

from kernel_gen.dialect.dma import DmaAllocOp
from kernel_gen.dialect.nn import NnMemoryType
from kernel_gen.dialect.symbol import SymbolDimType, SymbolForOp, SymbolGetDimOp, SymbolValueType
from kernel_gen.dialect.tuner import TunerParamOp
from kernel_gen.passes.pass_manager import Pass


class KernelSplitError(ValueError):
    """kernel split pass 的显式错误。

    创建者: 小李飞刀
    最后一次更改: 小李飞刀

    功能说明:
    - 统一承载 `KernelSplit*` 关键短语错误，便于测试与上层任务链稳定匹配。

    使用示例:
    - raise KernelSplitError("KernelSplitMissingTrigger: module has no marked func")

    关联文件:
    - spec: spec/pass/lowering/kernel_split.md
    - test: test/pass/test_lowering_kernel_split.py
    - 功能实现: kernel_gen/passes/lowering/kernel_split.py
    """


@dataclass(frozen=True)
class _KernelSplitMarker:
    """记录函数级 split marker。

    创建者: 小李飞刀
    最后一次更改: 小李飞刀

    功能说明:
    - 保存 `kernel_split` 属性中的 axis 与 tile 名称。
    - 供校验、bridge 与重写阶段复用，避免重复解析 attribute。

    使用示例:
    - marker = _parse_kernel_split_marker(func_op)

    关联文件:
    - spec: spec/pass/lowering/kernel_split.md
    - test: test/pass/test_lowering_kernel_split.py
    - 功能实现: kernel_gen/passes/lowering/kernel_split.py
    """

    axis: int
    tile_name: str


@irdl_op_definition
class _KernelSplitSymbolLiteralOp(IRDLOperation):
    """kernel_split 内部使用的 symbol.int 字面量 op。"""

    name = "kernel_split.symbol_literal"

    result = result_def(SymbolValueType)

    def __init__(self: "_KernelSplitSymbolLiteralOp", expr: str) -> None:
        """构造内部 symbol 字面量。

        创建者: 小李飞刀
        最后一次更改: 小李飞刀

        功能说明:
        - 为 split loop 生成 `0` 等 `!symbol.int<"...">` SSA 起始值。

        使用示例:
        - start = _KernelSplitSymbolLiteralOp("0")

        关联文件:
        - spec: spec/pass/lowering/kernel_split.md
        - test: test/pass/test_lowering_kernel_split.py
        - 功能实现: kernel_gen/passes/lowering/kernel_split.py
        """

        super().__init__(result_types=[SymbolValueType.from_expr(expr)])

    def verify_(self: "_KernelSplitSymbolLiteralOp") -> None:
        """校验内部 symbol 字面量结果类型。

        创建者: 小李飞刀
        最后一次更改: 小李飞刀

        功能说明:
        - 要求结果类型固定为 `!symbol.int<"...">`。

        使用示例:
        - _KernelSplitSymbolLiteralOp("0").verify_()

        关联文件:
        - spec: spec/pass/lowering/kernel_split.md
        - test: test/pass/test_lowering_kernel_split.py
        - 功能实现: kernel_gen/passes/lowering/kernel_split.py
        """

        if not isinstance(self.result.type, SymbolValueType):
            raise VerifyException("kernel_split.symbol_literal result must be !symbol.int")


@irdl_op_definition
class _KernelSplitTileValueOp(IRDLOperation):
    """把 `tuner.param` bridge 为 symbol loop step 的内部 op。"""

    name = "kernel_split.tile_value"

    source = operand_def(SymbolDimType)
    result = result_def(SymbolValueType)

    def __init__(self: "_KernelSplitTileValueOp", source: SSAValue | Operation, tile_name: str) -> None:
        """构造 tile step bridge。

        创建者: 小李飞刀
        最后一次更改: 小李飞刀

        功能说明:
        - 显式保留 `tuner.param -> !symbol.int<tile>` 的桥接痕迹。
        - 让 split loop 的 step 由 `tuner.param` 驱动而非隐藏常量。

        使用示例:
        - step = _KernelSplitTileValueOp(tile_param.result, "TILE_M")

        关联文件:
        - spec: spec/pass/lowering/kernel_split.md
        - test: test/pass/test_lowering_kernel_split.py
        - 功能实现: kernel_gen/passes/lowering/kernel_split.py
        """

        super().__init__(
            operands=[source],
            result_types=[SymbolValueType.from_expr(tile_name)],
        )

    def verify_(self: "_KernelSplitTileValueOp") -> None:
        """校验 tile step bridge。

        创建者: 小李飞刀
        最后一次更改: 小李飞刀

        功能说明:
        - 要求 source 为 `!symbol.dim<"...">`。
        - 要求 result expr 与 source 中的 dim 名称一致。

        使用示例:
        - _KernelSplitTileValueOp(tile_param.result, "TILE_M").verify_()

        关联文件:
        - spec: spec/pass/lowering/kernel_split.md
        - test: test/pass/test_lowering_kernel_split.py
        - 功能实现: kernel_gen/passes/lowering/kernel_split.py
        """

        source_type = SSAValue.get(self.source).type
        if not isinstance(source_type, SymbolDimType):
            raise VerifyException("kernel_split.tile_value source must be !symbol.dim")
        expected = SymbolValueType.from_expr(source_type.dim.data)
        if self.result.type != expected:
            raise VerifyException("kernel_split.tile_value result must match tuner.param dim name")


def _raise_kernel_split_error(keyword: str, detail: str) -> None:
    """抛出统一格式的 kernel split 错误。

    创建者: 小李飞刀
    最后一次更改: 小李飞刀

    功能说明:
    - 统一组装 `KernelSplit*` 前缀，避免不同路径返回不稳定错误短语。

    使用示例:
    - _raise_kernel_split_error("KernelSplitMissingTrigger", "module has no marked func")

    关联文件:
    - spec: spec/pass/lowering/kernel_split.md
    - test: test/pass/test_lowering_kernel_split.py
    - 功能实现: kernel_gen/passes/lowering/kernel_split.py
    """

    raise KernelSplitError(f"{keyword}: {detail}")


def _get_single_block(func_op: func.FuncOp) -> Block:
    """获取并校验单块函数体。

    创建者: 小李飞刀
    最后一次更改: 小李飞刀

    功能说明:
    - 当前首轮实现仅支持单个 block 的 `func.func`。
    - 当函数体为空、多块或缺少 `func.return` 时，由 verifier error 路径统一承接。

    使用示例:
    - block = _get_single_block(func_op)

    关联文件:
    - spec: spec/pass/lowering/kernel_split.md
    - test: test/pass/test_lowering_kernel_split.py
    - 功能实现: kernel_gen/passes/lowering/kernel_split.py
    """

    blocks = list(func_op.body.blocks)
    if len(blocks) != 1:
        _raise_kernel_split_error(
            "KernelSplitVerifierError",
            f"function {func_op.sym_name.data} must contain exactly one block",
        )
    return blocks[0]


def _marked_functions(module: ModuleOp) -> list[func.FuncOp]:
    """收集带 `kernel_split` 标记的函数。

    创建者: 小李飞刀
    最后一次更改: 小李飞刀

    功能说明:
    - 仅识别 `func.FuncOp.attributes["kernel_split"]`。
    - 若模块内不存在任何标记函数，立即抛出 `KernelSplitMissingTrigger`。

    使用示例:
    - funcs = _marked_functions(module)

    关联文件:
    - spec: spec/pass/lowering/kernel_split.md
    - test: test/pass/test_lowering_kernel_split.py
    - 功能实现: kernel_gen/passes/lowering/kernel_split.py
    """

    marked = [
        op
        for op in module.ops
        if isinstance(op, func.FuncOp) and "kernel_split" in op.attributes
    ]
    if not marked:
        _raise_kernel_split_error(
            "KernelSplitMissingTrigger",
            "module does not contain any func.func with kernel_split marker",
        )
    return marked


def _parse_kernel_split_marker(func_op: func.FuncOp) -> _KernelSplitMarker:
    """解析并校验函数级 split marker。

    创建者: 小李飞刀
    最后一次更改: 小李飞刀

    功能说明:
    - 读取 `kernel_split = { axis = <i64>, tile = "<TILE_NAME>" }`。
    - 缺少或非法 `tile` 报 `KernelSplitMissingTileParam`。
    - 缺少或非法 `axis` 报 `KernelSplitAxisMismatch`。

    使用示例:
    - marker = _parse_kernel_split_marker(func_op)

    关联文件:
    - spec: spec/pass/lowering/kernel_split.md
    - test: test/pass/test_lowering_kernel_split.py
    - 功能实现: kernel_gen/passes/lowering/kernel_split.py
    """

    attr = func_op.attributes.get("kernel_split")
    if not isinstance(attr, DictionaryAttr):
        _raise_kernel_split_error(
            "KernelSplitMissingTrigger",
            f"function {func_op.sym_name.data} is missing dictionary kernel_split marker",
        )
    tile_attr = attr.data.get("tile")
    if not isinstance(tile_attr, StringAttr):
        _raise_kernel_split_error(
            "KernelSplitMissingTileParam",
            f"function {func_op.sym_name.data} requires kernel_split.tile string",
        )
    try:
        tile_type = SymbolDimType.from_name(tile_attr.data)
    except VerifyException as exc:
        _raise_kernel_split_error(
            "KernelSplitMissingTileParam",
            f"function {func_op.sym_name.data} has invalid tile name {tile_attr.data!r}: {exc}",
        )
    axis_attr = attr.data.get("axis")
    if not isinstance(axis_attr, IntAttr):
        _raise_kernel_split_error(
            "KernelSplitAxisMismatch",
            f"function {func_op.sym_name.data} requires integer kernel_split.axis",
        )
    if axis_attr.data < 0:
        _raise_kernel_split_error(
            "KernelSplitAxisMismatch",
            f"function {func_op.sym_name.data} axis must be non-negative",
        )
    return _KernelSplitMarker(axis=int(axis_attr.data), tile_name=tile_type.dim.data)


def _get_memory_arguments(func_op: func.FuncOp) -> list[SSAValue]:
    """收集并校验参与 axis 推导的 `nn.memory` 参数。

    创建者: 小李飞刀
    最后一次更改: 小李飞刀

    功能说明:
    - 收集函数签名中的全部 `nn.memory` 参数，供 axis/rank 一致性校验复用。
    - 若函数签名中不存在 memory 参数，则无法确定目标轴范围，报 `KernelSplitAxisMismatch`。

    使用示例:
    - memory_arguments = _get_memory_arguments(func_op)

    关联文件:
    - spec: spec/pass/lowering/kernel_split.md
    - test: test/pass/test_lowering_kernel_split.py
    - 功能实现: kernel_gen/passes/lowering/kernel_split.py
    """

    memory_arguments = [argument for argument in func_op.args if isinstance(argument.type, NnMemoryType)]
    if memory_arguments:
        return memory_arguments
    _raise_kernel_split_error(
        "KernelSplitAxisMismatch",
        f"function {func_op.sym_name.data} has no nn.memory argument for split axis inference",
    )


def _validate_axis(func_op: func.FuncOp, marker: _KernelSplitMarker, memory_arguments: list[SSAValue]) -> None:
    """校验 split axis 与全部 memory 参数的 rank/axis 一致。

    创建者: 小李飞刀
    最后一次更改: 小李飞刀

    功能说明:
    - 要求所有参与 split 推导的参数都为 `nn.memory`。
    - 要求所有 `nn.memory` 参数 rank 一致，且 `axis < rank`；否则抛出 `KernelSplitAxisMismatch`。

    使用示例:
    - _validate_axis(func_op, marker, memory_arguments)

    关联文件:
    - spec: spec/pass/lowering/kernel_split.md
    - test: test/pass/test_lowering_kernel_split.py
    - 功能实现: kernel_gen/passes/lowering/kernel_split.py
    """

    reference_rank: int | None = None
    for argument_index, argument in enumerate(memory_arguments):
        argument_type = argument.type
        if not isinstance(argument_type, NnMemoryType):
            _raise_kernel_split_error(
                "KernelSplitAxisMismatch",
                f"function {func_op.sym_name.data} split axis expects nn.memory reference",
            )
        rank = len(argument_type.shape.data)
        if reference_rank is None:
            reference_rank = rank
        elif rank != reference_rank:
            _raise_kernel_split_error(
                "KernelSplitAxisMismatch",
                f"function {func_op.sym_name.data} has inconsistent nn.memory rank {rank} at argument {argument_index}; expected {reference_rank}",
            )
        if marker.axis >= rank:
            _raise_kernel_split_error(
                "KernelSplitAxisMismatch",
                f"function {func_op.sym_name.data} axis {marker.axis} exceeds rank {rank} at argument {argument_index}",
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
    - spec: spec/pass/lowering/kernel_split.md
    - test: test/pass/test_lowering_kernel_split.py
    - 功能实现: kernel_gen/passes/lowering/kernel_split.py
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
    - spec: spec/pass/lowering/kernel_split.md
    - test: test/pass/test_lowering_kernel_split.py
    - 功能实现: kernel_gen/passes/lowering/kernel_split.py
    """

    return SSAValue.get(op.operands[-1])


def _is_allowed_input_contract_op(op: Operation) -> bool:
    """判断输入 IR 是否命中 kernel split 的允许子集。

    创建者: 小李飞刀
    最后一次更改: 小李飞刀

    功能说明:
    - 允许已 lower 的 `kernel.*` / `dma.*` 核心计算子集。
    - 允许 `func.return`、`tuner.param` 与 `symbol.get_dim` 等 split 所需桥接辅助 op。
    - 其余 op 统一由 fail-fast 路径拒绝，避免未冻结语义偷偷进入 split。

    使用示例:
    - if not _is_allowed_input_contract_op(op): ...

    关联文件:
    - spec: spec/pass/lowering/kernel_split.md
    - test: test/pass/test_lowering_kernel_split.py
    - 功能实现: kernel_gen/passes/lowering/kernel_split.py
    """

    if op.name.startswith("kernel.") or op.name.startswith("dma."):
        return True
    if isinstance(op, (func.ReturnOp, TunerParamOp, SymbolGetDimOp)):
        return True
    return False


def _validate_input_contract(func_op: func.FuncOp, block: Block) -> None:
    """校验 split 前输入 IR 是否满足已冻结合同。

    创建者: 小李飞刀
    最后一次更改: 小李飞刀

    功能说明:
    - 拒绝残留 `nn.*` 操作。
    - 拒绝 memory-return ABI。
    - 拒绝函数体内 `func.call`。
    - 对非 `kernel/dma/func` 允许子集以外的 op 执行 fail-fast。

    使用示例:
    - _validate_input_contract(func_op, block)

    关联文件:
    - spec: spec/pass/lowering/kernel_split.md
    - test: test/pass/test_lowering_kernel_split.py
    - 功能实现: kernel_gen/passes/lowering/kernel_split.py
    """

    if any(isinstance(output_type, NnMemoryType) for output_type in func_op.function_type.outputs.data):
        _raise_kernel_split_error(
            "KernelSplitRequiresOutParamsABI",
            f"function {func_op.sym_name.data} still returns nn.memory results",
        )
    for op in block.ops:
        if op.name.startswith("nn."):
            _raise_kernel_split_error(
                "KernelSplitRequiresLoweredKernelIR",
                f"function {func_op.sym_name.data} still contains {op.name}",
            )
        if isinstance(op, func.CallOp):
            _raise_kernel_split_error(
                "KernelSplitUnexpectedFuncExtraction",
                f"function {func_op.sym_name.data} must not contain func.call in split body",
            )
        if not _is_allowed_input_contract_op(op):
            _raise_kernel_split_error(
                "KernelSplitRequiresLoweredKernelIR",
                "function "
                f"{func_op.sym_name.data} contains unsupported op {op.name}; "
                "only kernel/dma/func.return plus tuner.param/symbol.get_dim are allowed before split",
            )


def _validate_intermediate_materialization(func_op: func.FuncOp, block: Block) -> None:
    """校验跨 stage 中间值是否物化为显式 carry memory。

    创建者: 小李飞刀
    最后一次更改: 小李飞刀

    功能说明:
    - 若某个 `kernel.*` 的 out buffer 会被后续 op 当作输入消费，则它是跨 stage 中间值。
    - 该 buffer 必须来自 `dma.alloc`；否则报 `KernelSplitIntermediateMaterializationError`。
    - 来自 `dma.alloc` 的 carry memory 若最终未被后续 stage 消费，则报 `KernelSplitDeadCarryMemory`。

    使用示例:
    - _validate_intermediate_materialization(func_op, block)

    关联文件:
    - spec: spec/pass/lowering/kernel_split.md
    - test: test/pass/test_lowering_kernel_split.py
    - 功能实现: kernel_gen/passes/lowering/kernel_split.py
    """

    body_ops = list(block.ops)
    kernel_ops = [op for op in body_ops if op.name.startswith("kernel.")]
    consumed_carry_allocs: set[DmaAllocOp] = set()
    written_carry_allocs: set[DmaAllocOp] = set()

    for index, kernel_op in enumerate(kernel_ops):
        out_value = _kernel_out_operand(kernel_op)
        owner = out_value.owner if isinstance(out_value.owner, Operation) else None
        if isinstance(owner, DmaAllocOp):
            written_carry_allocs.add(owner)
        if any(_uses_value_as_input(later_op, out_value) for later_op in body_ops[body_ops.index(kernel_op) + 1 :]):
            if not isinstance(owner, DmaAllocOp):
                _raise_kernel_split_error(
                    "KernelSplitIntermediateMaterializationError",
                    f"function {func_op.sym_name.data} reuses {kernel_op.name} out buffer without dma.alloc carry memory",
                )
            consumed_carry_allocs.add(owner)
        if index == len(kernel_ops) - 1:
            continue

    dead_allocs = written_carry_allocs - consumed_carry_allocs
    if dead_allocs:
        alloc = next(iter(dead_allocs))
        _raise_kernel_split_error(
            "KernelSplitDeadCarryMemory",
            f"function {func_op.sym_name.data} leaves carry memory {alloc.name} without later consumption",
        )


def _find_or_insert_tile_param(
    func_op: func.FuncOp,
    block: Block,
    marker: _KernelSplitMarker,
) -> tuple[TunerParamOp, bool]:
    """查找或插入与 split tile 对应的 `tuner.param`。

    创建者: 小李飞刀
    最后一次更改: 小李飞刀

    功能说明:
    - 若函数体内已存在同名 `tuner.param`，直接复用。
    - 否则创建新的 `tuner.param : !symbol.dim<tile>`，由调用方负责插入。

    使用示例:
    - tile_param, inserted = _find_or_insert_tile_param(func_op, block, marker)

    关联文件:
    - spec: spec/pass/lowering/kernel_split.md
    - test: test/pass/test_lowering_kernel_split.py
    - 功能实现: kernel_gen/passes/lowering/kernel_split.py
    """

    expected_type = SymbolDimType.from_name(marker.tile_name)
    for op in block.ops:
        if isinstance(op, TunerParamOp) and op.result.type == expected_type:
            return op, False
    return TunerParamOp(expected_type), True


def _rewrite_function(func_op: func.FuncOp) -> None:
    """把目标函数改写为单函数内显式 split body。

    创建者: 小李飞刀
    最后一次更改: 小李飞刀

    功能说明:
    - 在函数体内插入/复用 `tuner.param`。
    - 通过 `symbol.get_dim + symbol.for` 显式表达 split body。
    - 保持原 `func.func` 不拆出 helper。

    使用示例:
    - _rewrite_function(func_op)

    关联文件:
    - spec: spec/pass/lowering/kernel_split.md
    - test: test/pass/test_lowering_kernel_split.py
    - 功能实现: kernel_gen/passes/lowering/kernel_split.py
    """

    block = _get_single_block(func_op)
    marker = _parse_kernel_split_marker(func_op)
    memory_arguments = _get_memory_arguments(func_op)
    _validate_axis(func_op, marker, memory_arguments)
    reference_memory = memory_arguments[0]
    _validate_input_contract(func_op, block)
    _validate_intermediate_materialization(func_op, block)

    return_op = block.last_op
    if not isinstance(return_op, func.ReturnOp):
        _raise_kernel_split_error(
            "KernelSplitVerifierError",
            f"function {func_op.sym_name.data} must terminate with func.return",
        )

    tile_param, inserted = _find_or_insert_tile_param(func_op, block, marker)
    start_value = _KernelSplitSymbolLiteralOp("0")
    end_value = SymbolGetDimOp(reference_memory, marker.axis)
    step_value = _KernelSplitTileValueOp(tile_param.result, marker.tile_name)
    loop_block = Block(arg_types=[step_value.result.type])

    movable_ops = [
        op
        for op in list(block.ops)
        if op is not return_op and op is not tile_param and not isinstance(op, TunerParamOp)
    ]
    for op in movable_ops:
        op.detach()
        loop_block.add_op(op)

    loop_op = SymbolForOp(start_value.result, end_value.result, step_value.result, loop_block)
    new_ops: list[Operation] = []
    if inserted:
        new_ops.append(tile_param)
    new_ops.extend([start_value, end_value, step_value, loop_op])
    block.insert_ops_before(new_ops, return_op)


class KernelSplitPass(Pass):
    """kernel split lowering pass。

    创建者: 小李飞刀
    最后一次更改: 小李飞刀

    功能说明:
    - 对带 `kernel_split` 标记的函数执行首轮显式 tile split。
    - 固化 S1 公开合同中的 trigger / tuner.param / 单函数 / carry memory 错误边界。

    使用示例:
    - module = KernelSplitPass().run(module)

    关联文件:
    - spec: spec/pass/lowering/kernel_split.md
    - test: test/pass/test_lowering_kernel_split.py
    - 功能实现: kernel_gen/passes/lowering/kernel_split.py
    """

    name = "kernel-split"

    def run(self: "KernelSplitPass", module: ModuleOp) -> ModuleOp:
        """执行 kernel split pass。

        创建者: 小李飞刀
        最后一次更改: 小李飞刀

        功能说明:
        - 遍历所有带 marker 的函数并执行重写。
        - 在最终 `module.verify()` 失败时统一转译为 `KernelSplitVerifierError`。

        使用示例:
        - lowered = KernelSplitPass().run(module)

        关联文件:
        - spec: spec/pass/lowering/kernel_split.md
        - test: test/pass/test_lowering_kernel_split.py
        - 功能实现: kernel_gen/passes/lowering/kernel_split.py
        """

        for func_op in _marked_functions(module):
            _rewrite_function(func_op)
        try:
            module.verify()
        except VerifyException as exc:
            _raise_kernel_split_error("KernelSplitVerifierError", str(exc))
        return module


__all__ = ["KernelSplitError", "KernelSplitPass"]
