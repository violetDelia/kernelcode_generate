"""arch-parallelize pass implementation.


功能说明:
- 提供 standalone IR-level `arch-parallelize` pass。
- 遍历 `builtin.module` 中非声明 `func.func`，跳过 `entry_point` host dispatcher，对未带 block 并行语义的其余函数执行 block 级分发。
- 当前只支持 `parallel_level="block"`：单顶层 `symbol.for` 改写为 block-strided loop；非入口函数无顶层 loop 时用 block0 guard 包裹原 body。
- 唯一顶层 loop 前允许公开 symbol setup 以及 memory-pool / multi-buffer 产生的 `arch.get_dynamic_memory` / `dma.reinterpret` / `dma.make_ring` setup 前缀，并保留旧 alias 前缀兼容。
- 内部 `FuncOp` root pattern 承接单函数改写，`ArchParallelizePass` 只负责校验和 pattern walker 驱动。

API 列表:
- `class ArchParallelizePass(target: str = "npu_demo", parallel_level: str = "block")`
- `ArchParallelizePass.from_options(options: dict[str, str]) -> ArchParallelizePass`
- `ArchParallelizePass.apply(ctx: Context, module: ModuleOp) -> None`

使用示例:
- from xdsl.context import Context
- from kernel_gen.passes.arch.arch_parallelize import ArchParallelizePass
- ArchParallelizePass(target="npu_demo").apply(Context(), module)

关联文件:
- spec: spec/pass/arch/arch_parallelize.md
- test: test/passes/arch/test_arch_parallelize.py
- 功能实现: kernel_gen/passes/arch/arch_parallelize.py
"""

from __future__ import annotations

from dataclasses import dataclass

from xdsl.context import Context
from xdsl.dialects import arith, func, scf
from xdsl.dialects.builtin import ArrayAttr, ModuleOp
from xdsl.ir import Attribute, Block, Operation, Region, SSAValue
from xdsl.pattern_rewriter import (
    GreedyRewritePatternApplier,
    PatternRewriter,
    PatternRewriteWalker,
    RewritePattern,
    op_type_rewrite_pattern,
)

from kernel_gen.dialect.arch import ArchGetBlockIdOp, ArchGetBlockNumOp, ArchGetDynamicMemoryOp
from kernel_gen.dialect.dma import DmaMakeRingOp, DmaReinterpretOp, DmaReshapeOp, DmaRingType, DmaViewOp
from kernel_gen.dialect.memory import MemoryGetDataOp
from kernel_gen.dialect.nn import NnMemoryType
from kernel_gen.dialect.symbol import (
    SymbolAddOp,
    SymbolCastOp,
    SymbolConstOp,
    SymbolDivOp,
    SymbolFloorDivOp,
    SymbolExprAttr,
    SymbolIterAttr,
    SymbolForOp,
    SymbolGetDimOp,
    SymbolGetStrideOp,
    SymbolIterType,
    SymbolMaxOp,
    SymbolMinOp,
    SymbolMulOp,
    SymbolNeOp,
    SymbolSubOp,
    SymbolValueType,
)
from kernel_gen.core.error import ErrorKind, ErrorModule, KernelCodeError
from kernel_gen.passes.common import ensure_builtin_module, raise_pass_contract_error, verify_generated_ops
from kernel_gen.passes.pass_manager import Pass
from kernel_gen.target import registry as target_registry

_VALID_OPTIONS = {"target", "parallel_level"}
_SYMBOL_SETUP_OPS = (
    SymbolConstOp,
    SymbolAddOp,
    SymbolSubOp,
    SymbolMulOp,
    SymbolDivOp,
    SymbolFloorDivOp,
    SymbolMinOp,
    SymbolMaxOp,
    SymbolGetDimOp,
    SymbolGetStrideOp,
)
_MEMORY_POOL_SETUP_OPS = (
    ArchGetDynamicMemoryOp,
    DmaViewOp,
    DmaReshapeOp,
    DmaReinterpretOp,
    DmaMakeRingOp,
)
_PRESENCE_SETUP_OPS = (
    arith.ConstantOp,
    MemoryGetDataOp,
    SymbolCastOp,
    SymbolNeOp,
)
_UNKNOWN_SYMBOL_EXPR = "?"


@dataclass(frozen=True)
class _LoopShape:
    """当前文件内的顶层 loop 分析结果。

    功能说明:
    - 保存 `ArchParallelizePass` 对单个函数 body 的最小分类结果。
    - 仅供本文件内部使用，不作为公开 API。

    使用示例:
    - shape = _LoopShape("no_loop")
    """

    kind: str
    outer_loop: SymbolForOp | None = None


def _fail(detail: str) -> None:
    """抛出 arch-parallelize pass 合同错误。

    功能说明:
    - 统一稳定错误前缀为 `ArchParallelizePassError`。

    使用示例:
    - _fail("unsupported loop structure")
    """

    raise_pass_contract_error("ArchParallelizePassError", detail)


def _validate_options(target: str, parallel_level: str) -> None:
    """校验 pass 构造参数。

    功能说明:
    - `target` 必须是非空字符串。
    - 当前只接受 `parallel_level="block"`。

    使用示例:
    - _validate_options("npu_demo", "block")
    """

    if not isinstance(target, str) or target.strip() == "":
        _fail("target must be non-empty string")
    if parallel_level != "block":
        if parallel_level == "block_thread":
            _fail("parallel_level block_thread is not supported yet")
        _fail("unsupported parallel_level")


def _validate_target_and_get_block_num(target: str) -> int:
    """校验 target 支持 block 并行并读取静态 block_num。

    功能说明:
    - 通过公开 target registry 查询 `arch.get_block_id` 支持性与 `block_num` 硬件字段。

    使用示例:
    - block_num = _validate_target_and_get_block_num("npu_demo")
    """

    try:
        has_block_id = target_registry.is_arch_op_supported(target, "arch.get_block_id")
        block_num = target_registry.get_target_hardware(target, "block_num")
    except ValueError as exc:
        raise KernelCodeError(
            ErrorKind.CONTRACT,
            ErrorModule.PASS,
            "ArchParallelizePassError: target not registered",
        ) from exc
    if not has_block_id:
        _fail("target does not support arch.get_block_id")
    if not isinstance(block_num, int) or isinstance(block_num, bool) or block_num <= 0:
        _fail("target block_num must be positive integer")
    return block_num


def _has_existing_block_parallel_ops(func_op: func.FuncOp) -> bool:
    """判断函数是否已包含 block 相关 arch op。

    功能说明:
    - 发现 `arch.get_block_id` 或 `arch.get_block_num` 时，当前函数直接跳过。

    使用示例:
    - if _has_existing_block_parallel_ops(func_op): return
    """

    return any(isinstance(op, (ArchGetBlockIdOp, ArchGetBlockNumOp)) for op in func_op.walk())


def _is_entry_point_func(func_op: func.FuncOp) -> bool:
    """判断函数是否为 host dispatcher 入口。

    功能说明:
    - 带 `entry_point` 属性的函数承载 host 调度职责，必须保持 no-op。
    - 该跳过边界避免 host launch 被 block-only guard 限制。
    - 该边界只识别当前公开 IR 属性，不扩大为所有无 kernel 标记函数跳过。

    使用示例:
    - if _is_entry_point_func(func_op): return
    """

    return "entry_point" in func_op.attributes


def _get_single_entry_block(func_op: func.FuncOp) -> Block:
    """校验并返回单块函数体。

    功能说明:
    - 拒绝有返回值函数和 multi-block 函数体。

    使用示例:
    - block = _get_single_entry_block(func_op)
    """

    if tuple(func_op.function_type.outputs.data):
        _fail("function return values are not supported")
    blocks = tuple(func_op.body.blocks)
    if len(blocks) != 1:
        _fail("multi-block func body is not supported")
    return blocks[0]


def _split_body_and_return(entry_block: Block) -> tuple[list[Operation], func.ReturnOp]:
    """拆分函数 body op 与末尾 `func.return`。

    功能说明:
    - 要求函数体以无 operand 的 `func.return` 结束。

    使用示例:
    - body_ops, return_op = _split_body_and_return(block)
    """

    ops = list(entry_block.ops)
    if not ops or not isinstance(ops[-1], func.ReturnOp):
        _fail("unsupported loop structure")
    return_op = ops[-1]
    if tuple(return_op.arguments):
        _fail("function return values are not supported")
    return ops[:-1], return_op


def _analyze_loop_shape(body_ops: list[Operation]) -> _LoopShape:
    """分析函数顶层 loop 结构。

    功能说明:
    - 无顶层 loop 时返回 `no_loop`。
    - 一个顶层 `symbol.for` 且同级仅包含 loop 前公开 setup 前缀时返回可改写结果。
    - 多个顶层 `symbol.for` 或 loop 同级出现不可判 op 时返回 unsupported。

    使用示例:
    - shape = _analyze_loop_shape(body_ops)
    """

    top_level_loops = [op for op in body_ops if isinstance(op, SymbolForOp)]
    if not top_level_loops:
        return _LoopShape("no_loop")
    if len(top_level_loops) > 1:
        return _LoopShape("multiple_top_level_loops")
    outer_loop = top_level_loops[0]
    outer_index = body_ops.index(outer_loop)
    parent_block = outer_loop.parent_block()
    allowed_values: set[SSAValue] = set(parent_block.args) if parent_block is not None else set()
    for index, op in enumerate(body_ops):
        if op is outer_loop:
            continue
        if index > outer_index or not _is_allowed_loop_prefix_setup_op(op):
            return _LoopShape("unsupported")
        if not _setup_operands_are_allowed(op, allowed_values):
            return _LoopShape("unsupported")
        allowed_values.update(op.results)
    if not _can_transform_loop_nest(outer_loop):
        return _LoopShape("loop_carried")
    return _LoopShape("transformable_loop_nest", outer_loop)


def _is_allowed_loop_prefix_setup_op(op: Operation) -> bool:
    """判断顶层 op 是否为唯一 loop 前允许的 setup 前缀。

    功能说明:
    - 放行公开 symbol dialect 的无副作用边界构造 op。
    - 放行 memory-pool / multi-buffer 生成的 `arch.get_dynamic_memory`、`dma.view`、`dma.reshape`、`dma.reinterpret` 与 `dma.make_ring`。
    - 放行 optional memory presence guard 需要的 `arith.constant`、`memory.get_data`、`symbol.cast` 与 `symbol.ne`。

    使用示例:
    - if _is_allowed_loop_prefix_setup_op(op): ...
    """

    return isinstance(op, _SYMBOL_SETUP_OPS + _MEMORY_POOL_SETUP_OPS + _PRESENCE_SETUP_OPS)


def _setup_operands_are_allowed(op: Operation, allowed_values: set[SSAValue]) -> bool:
    """校验 setup 前缀只依赖函数参数或更早的合法 setup。

    功能说明:
    - 保证放行 `arch.get_dynamic_memory` / `dma.view` / `dma.reshape` 不会扩大到任意顶层 op 结果。
    - operand 若不是函数参数或更早合法 setup result，则保持 `unsupported loop structure`。

    使用示例:
    - if not _setup_operands_are_allowed(op, allowed_values): ...
    """

    return all(operand in allowed_values for operand in op.operands)


def _can_transform_loop_nest(outer_loop: SymbolForOp) -> bool:
    """判断顶层 `symbol.for` 是否可按 block 分片。

    功能说明:
    - 当前仅支持无 carried-value 的单块 `symbol.for`，且 start/end/step 均为 `!symbol.int`。

    使用示例:
    - if _can_transform_loop_nest(loop): ...
    """

    if outer_loop.init is not None or outer_loop.result is not None:
        return False
    blocks = tuple(outer_loop.body.blocks)
    if len(blocks) != 1:
        return False
    if len(blocks[0].args) != 1:
        return False
    for value in (outer_loop.start, outer_loop.end, outer_loop.step):
        if not isinstance(SSAValue.get(value).type, SymbolValueType):
            return False
    return True


def _symbol_expr(value: SSAValue | Operation | Attribute) -> str:
    """提取 symbol.int 的公开表达式文本。

    功能说明:
    - 无法证明是 `SymbolValueType` 时返回 `?`，用于保持改写保守可验证。

    使用示例:
    - expr = _symbol_expr(loop.start)
    """

    if isinstance(value, Attribute):
        value_type = value
    else:
        value_type = SSAValue.get(value).type
    if isinstance(value_type, SymbolValueType):
        return value_type.expr.expr.data
    return _UNKNOWN_SYMBOL_EXPR


def _symbol_type_for_binary(lhs: SSAValue | Operation, op: str, rhs: SSAValue | Operation) -> SymbolValueType:
    """为新建 symbol 二元 op 构造结果类型。

    功能说明:
    - 复用 `SymbolValueType.from_expr(...)` 的公开 canonical 规则。

    使用示例:
    - result_type = _symbol_type_for_binary(lhs, "*", rhs)
    """

    return SymbolValueType.from_expr(f"{_symbol_expr(lhs)} {op} {_symbol_expr(rhs)}")


def _loop_iter_type(start: SSAValue | Operation, end: SSAValue | Operation, step: SSAValue | Operation) -> SymbolIterType:
    """根据 loop 三个边界值构造 block argument 类型。

    功能说明:
    - 保证新 loop 的 `iter` 属性和 induction variable 类型与新边界一致。

    使用示例:
    - iter_type = _loop_iter_type(new_start.result, old_end, new_step.result)
    """

    return SymbolIterType.from_bounds(_symbol_expr(start), _symbol_expr(end), _symbol_expr(step))


def _iter_token(iter_type: SymbolIterType) -> str:
    """把 `SymbolIterType` 转成公开 `iter<...>` 文本 token。

    功能说明:
    - 用于在克隆后同步替换旧 loop 体里残留的 induction variable 表达式。

    使用示例:
    - token = _iter_token(SymbolIterType.from_bounds("0", "6", "4"))
    """

    return f"iter<{iter_type.start.expr.data},{iter_type.end.expr.data},{iter_type.step.expr.data}>"


def _replace_symbol_expr_text(expr: str, replacements: dict[str, str]) -> str:
    """按公开 token 表达式替换 symbol 文本。

    功能说明:
    - 仅替换已知旧 token，不做额外规范化。

    使用示例:
    - text = _replace_symbol_expr_text("6 - iter<0,6,4>", {"iter<0,6,4>": "iter<4*block_id,6,8>"})
    """

    for old, new in replacements.items():
        expr = expr.replace(old, new)
    return expr


def _rewrite_attribute_type(attr: Attribute, replacements: dict[str, str]) -> Attribute:
    """把克隆后属性中的旧 symbol token 重写为新 token。

    功能说明:
    - 只处理本文件当前会生成的公开类型：`SymbolValueType`、`SymbolIterType`、`NnMemoryType`、`DmaRingType` 和其包装的 `ArrayAttr`。
    - 其它属性保持原样，避免扩大改写面。

    使用示例:
    - new_attr = _rewrite_attribute_type(old_attr, {"iter<0,6,4>": "iter<4*block_id,6,8>"})
    """

    if isinstance(attr, SymbolValueType):
        expr = attr.expr.expr.data
        for old, new in replacements.items():
            expr = expr.replace(old, new)
        return SymbolValueType.from_expr(expr)
    if isinstance(attr, SymbolIterType):
        start_expr = attr.start.expr.data
        end_expr = attr.end.expr.data
        step_expr = attr.step.expr.data
        for old, new in replacements.items():
            start_expr = start_expr.replace(old, new)
            end_expr = end_expr.replace(old, new)
            step_expr = step_expr.replace(old, new)
        return SymbolIterType.from_bounds(
            start_expr,
            end_expr,
            step_expr,
        )
    if isinstance(attr, NnMemoryType):
        shape_entries: list[SymbolExprAttr] = []
        stride_entries: list[SymbolExprAttr] = []
        for dim in attr.shape.data:
            dim_expr = dim.expr.data
            for old, new in replacements.items():
                dim_expr = dim_expr.replace(old, new)
            shape_entries.append(SymbolExprAttr.from_expr(dim_expr))
        for dim in attr.stride.data:
            dim_expr = dim.expr.data
            for old, new in replacements.items():
                dim_expr = dim_expr.replace(old, new)
            stride_entries.append(SymbolExprAttr.from_expr(dim_expr))
        shape = ArrayAttr(
            shape_entries
        )
        stride = ArrayAttr(
            stride_entries
        )
        template_name = attr.template_name.data or None
        return NnMemoryType(
            shape,
            stride,
            attr.element_type,
            attr.space,
            template_name=template_name,
            external_attrs=attr.external_attrs,
        )
    if isinstance(attr, DmaRingType):
        memory_type = attr.memory_type
        shape_entries: list[SymbolExprAttr] = []
        stride_entries: list[SymbolExprAttr] = []
        for dim in memory_type.shape.data:
            dim_expr = dim.expr.data
            for old, new in replacements.items():
                dim_expr = dim_expr.replace(old, new)
            shape_entries.append(SymbolExprAttr.from_expr(dim_expr))
        for dim in memory_type.stride.data:
            dim_expr = dim.expr.data
            for old, new in replacements.items():
                dim_expr = dim_expr.replace(old, new)
            stride_entries.append(SymbolExprAttr.from_expr(dim_expr))
        template_name = memory_type.template_name.data or None
        return DmaRingType(
            NnMemoryType(
                ArrayAttr(shape_entries),
                ArrayAttr(stride_entries),
                memory_type.element_type,
                memory_type.space,
                template_name=template_name,
                external_attrs=memory_type.external_attrs,
            )
        )
    if isinstance(attr, SymbolIterAttr):
        start_expr = attr.start.expr.data
        end_expr = attr.end.expr.data
        step_expr = attr.step.expr.data
        for old, new in replacements.items():
            start_expr = start_expr.replace(old, new)
            end_expr = end_expr.replace(old, new)
            step_expr = step_expr.replace(old, new)
        return SymbolIterAttr.from_bounds(
            start_expr,
            end_expr,
            step_expr,
        )
    if isinstance(attr, ArrayAttr):
        rewritten_entries: list[Attribute] = []
        for entry in attr.data:
            if isinstance(entry, SymbolValueType):
                expr = entry.expr.expr.data
                for old, new in replacements.items():
                    expr = expr.replace(old, new)
                rewritten_entries.append(SymbolValueType.from_expr(expr))
                continue
            if isinstance(entry, SymbolIterType):
                start_expr = entry.start.expr.data
                end_expr = entry.end.expr.data
                step_expr = entry.step.expr.data
                for old, new in replacements.items():
                    start_expr = start_expr.replace(old, new)
                    end_expr = end_expr.replace(old, new)
                    step_expr = step_expr.replace(old, new)
                rewritten_entries.append(SymbolIterType.from_bounds(start_expr, end_expr, step_expr))
                continue
            if isinstance(entry, SymbolIterAttr):
                start_expr = entry.start.expr.data
                end_expr = entry.end.expr.data
                step_expr = entry.step.expr.data
                for old, new in replacements.items():
                    start_expr = start_expr.replace(old, new)
                    end_expr = end_expr.replace(old, new)
                    step_expr = step_expr.replace(old, new)
                rewritten_entries.append(SymbolIterAttr.from_bounds(start_expr, end_expr, step_expr))
                continue
            rewritten_entries.append(entry)
        return ArrayAttr(rewritten_entries)
    return attr


def _clone_region_with_rewritten_types(
    region: Region,
    value_mapper: dict[SSAValue, SSAValue],
    block_mapper: dict[Block, Block],
    replacements: dict[str, str],
) -> Region:
    """克隆 region 并同步替换 block argument 类型。

    功能说明:
    - 先按公开 `Block(arg_types=...)` 建立 block skeleton，再逐个克隆 op。
    - 避免直接写 xDSL `BlockArgument` 私有字段。

    使用示例:
    - region = _clone_region_with_rewritten_types(old_region, value_mapper, block_mapper, replacements)
    """

    old_blocks = tuple(region.blocks)
    new_blocks: list[Block] = []
    for old_block in old_blocks:
        new_block = Block(arg_types=[_rewrite_attribute_type(arg.type, replacements) for arg in old_block.args])
        for old_arg, new_arg in zip(old_block.args, new_block.args, strict=True):
            value_mapper[old_arg] = new_arg
            new_arg.name_hint = old_arg.name_hint
        block_mapper[old_block] = new_block
        new_blocks.append(new_block)
    new_region = Region(new_blocks)
    for old_block, new_block in zip(old_blocks, new_blocks, strict=True):
        for old_op in old_block.ops:
            new_block.add_op(_clone_operation_with_rewritten_types(old_op, value_mapper, block_mapper, replacements))
    return new_region


def _clone_operation_with_rewritten_types(
    op: Operation,
    value_mapper: dict[SSAValue, SSAValue],
    block_mapper: dict[Block, Block],
    replacements: dict[str, str],
) -> Operation:
    """克隆 op 并用公开构造入口替换结果类型文本。

    功能说明:
    - 通过 `op.__class__.create(...)` 传入重写后的 result_types / attributes / properties / regions。
    - 不直接写 `OpResult` 或 `BlockArgument` 的私有 `_type` 字段。

    使用示例:
    - cloned = _clone_operation_with_rewritten_types(old_op, value_mapper, block_mapper, replacements)
    """

    cloned_regions = [
        _clone_region_with_rewritten_types(region, value_mapper, block_mapper, replacements) for region in op.regions
    ]
    cloned_op = op.__class__.create(
        operands=tuple(value_mapper.get(operand, operand) for operand in op.operands),
        result_types=[_rewrite_attribute_type(result_type, replacements) for result_type in op.result_types],
        attributes={name: _rewrite_attribute_type(attr, replacements) for name, attr in op.attributes.items()},
        properties={name: _rewrite_attribute_type(prop, replacements) for name, prop in op.properties.items()},
        location=op.location,
        successors=[block_mapper.get(successor, successor) for successor in op.successors],
        regions=cloned_regions,
    )
    for old_result, new_result in zip(op.results, cloned_op.results, strict=True):
        value_mapper[old_result] = new_result
        new_result.name_hint = old_result.name_hint
    return cloned_op


def _clone_loop_body_with_iter_type(old_loop: SymbolForOp, iter_type: SymbolIterType) -> Block:
    """克隆 loop body 并替换 induction variable 类型。

    功能说明:
    - 不直接修改 xDSL `BlockArgument` 内部字段；通过新建 block 与公开 clone 入口保持 SSA 映射。

    使用示例:
    - new_block = _clone_loop_body_with_iter_type(loop, iter_type)
    """

    old_block = tuple(old_loop.body.blocks)[0]
    new_block = Block(arg_types=[iter_type])
    old_iter_type = old_block.args[0].type
    if not isinstance(old_iter_type, SymbolIterType):
        _fail("loop body it must have type !symbol.iter<...>")
    replacements = {_iter_token(old_iter_type): _iter_token(iter_type)}
    value_mapper: dict[SSAValue, SSAValue] = {old_block.args[0]: new_block.args[0]}
    block_mapper: dict[Block, Block] = {old_block: new_block}
    for old_op in old_block.ops:
        cloned = _clone_operation_with_rewritten_types(old_op, value_mapper, block_mapper, replacements)
        new_block.add_op(cloned)
    return new_block


def _rewrite_outer_loop_for_blocks(outer_loop: SymbolForOp, block_num: int, rewriter: PatternRewriter) -> None:
    """把唯一顶层 `symbol.for` 改写为 block-strided loop。

    功能说明:
    - 在旧 loop 前插入 `arch.get_block_id`、静态 `symbol.const block_num` 与新边界计算。
    - 通过 `PatternRewriter.replace_op(...)` 用克隆出的新 loop 替换旧 loop，保持 walker worklist 一致。

    使用示例:
    - _rewrite_outer_loop_for_blocks(loop, 1, rewriter)
    """

    parent_block = outer_loop.parent_block()
    if parent_block is None:
        _fail("unsupported loop structure")
    old_start = SSAValue.get(outer_loop.start)
    old_end = SSAValue.get(outer_loop.end)
    old_step = SSAValue.get(outer_loop.step)
    block_id = ArchGetBlockIdOp()
    block_count = SymbolConstOp(block_num)
    block_offset = SymbolMulOp(
        block_id.result,
        old_step,
        _symbol_type_for_binary(block_id.result, "*", old_step),
    )
    new_start = SymbolAddOp(
        old_start,
        block_offset.result,
        _symbol_type_for_binary(old_start, "+", block_offset.result),
    )
    new_step = SymbolMulOp(
        old_step,
        block_count.result,
        _symbol_type_for_binary(old_step, "*", block_count.result),
    )
    new_block = _clone_loop_body_with_iter_type(
        outer_loop,
        _loop_iter_type(new_start.result, old_end, new_step.result),
    )
    new_loop = SymbolForOp(new_start.result, old_end, new_step.result, new_block)
    rewriter.replace_op(
        outer_loop,
        [block_id, block_count, block_offset, new_start, new_step, new_loop],
        [],
    )


def _rewrite_no_loop_as_block0_only(entry_block: Block, body_ops: list[Operation], return_op: func.ReturnOp) -> None:
    """把无 loop 函数 body 包裹为 block0-only guard。

    功能说明:
    - 非 block0 分支只执行空 `scf.yield`。
    - block0 分支执行原 body，`func.return` 保持在 `scf.if` 外。

    使用示例:
    - _rewrite_no_loop_as_block0_only(block, body_ops, return_op)
    """

    block_id = ArchGetBlockIdOp()
    zero = SymbolConstOp(0)
    is_not_block0 = SymbolNeOp(block_id.result, zero.result)
    true_block = Block()
    true_block.add_op(scf.YieldOp())
    false_block = Block()
    for op in body_ops:
        op.detach()
        false_block.add_op(op)
    false_block.add_op(scf.YieldOp())
    if_op = scf.IfOp(is_not_block0.result, [], [true_block], [false_block])
    entry_block.insert_ops_before([block_id, zero, is_not_block0, if_op], return_op)


def _rewrite_func(func_op: func.FuncOp, block_num: int, rewriter: PatternRewriter) -> None:
    """处理单个非声明函数。

    功能说明:
    - 已有 block 并行 op 时跳过。
    - 否则按 loop 结构选择 block-strided rewrite、block0 guard 或稳定失败。

    使用示例:
    - _rewrite_func(func_op, block_num, rewriter)
    """

    if _has_existing_block_parallel_ops(func_op):
        return
    entry_block = _get_single_entry_block(func_op)
    body_ops, return_op = _split_body_and_return(entry_block)
    loop_shape = _analyze_loop_shape(body_ops)
    if loop_shape.kind == "no_loop":
        _rewrite_no_loop_as_block0_only(entry_block, body_ops, return_op)
        return
    if loop_shape.kind == "transformable_loop_nest" and loop_shape.outer_loop is not None:
        _rewrite_outer_loop_for_blocks(loop_shape.outer_loop, block_num, rewriter)
        return
    if loop_shape.kind == "multiple_top_level_loops":
        _fail("multiple top-level symbol.for loops are not supported")
    if loop_shape.kind == "loop_carried":
        _fail("loop-carried symbol.for is not supported")
    _fail("unsupported loop structure")


class _ArchParallelizeFuncPattern(RewritePattern):
    """公开的 `func.FuncOp` root arch-parallelize rewrite pattern。

    功能说明:
    - 以 `func.FuncOp` 为 root，处理单个函数内的 `entry_point`、已有 block 并行 op 和 `symbol.for` 结构。
    - `block_num` 由 `ArchParallelizePass.apply(...)` 预先校验为正整数，本 pattern 不新增独立稳定错误文本。

    IR before:
    ```mlir
    func.func @kernel() {
      %c0 = symbol.const 0 : !symbol.int<#symbol.expr<0>>
      %c8 = symbol.const 8 : !symbol.int<#symbol.expr<8>>
      %c1 = symbol.const 1 : !symbol.int<#symbol.expr<1>>
      symbol.for %i = %c0 to %c8 step %c1 {iter = #symbol.iter<start = #symbol.expr<0>, end = #symbol.expr<8>, step = #symbol.expr<1>>} {
      }
      func.return
    }
    ```

    IR after:
    ```mlir
    func.func @kernel() {
      %block = arch.get_block_id : !symbol.int<#symbol.expr<block_id>>
      %two = symbol.const 2 : !symbol.int<#symbol.expr<2>>
      symbol.for %i = %new_start to %c8 step %new_step {iter = #symbol.iter<start = #symbol.expr<block_id * 1>, end = #symbol.expr<8>, step = #symbol.expr<1 * 2>>} {
      }
      func.return
    }
    ```
    - 同一 pattern 对无 `symbol.for` 的非入口函数使用 `scf.if` block0 guard。

    使用示例:
    - _ArchParallelizeFuncPattern(block_num=2).match_and_rewrite(func_op, rewriter)
    """

    def __init__(self, block_num: int) -> None:
        """初始化函数级 arch-parallelize pattern。

        功能说明:
        - 保存已由 `ArchParallelizePass.apply(...)` 校验过的正整数 `block_num`。

        使用示例:
        - pattern = _ArchParallelizeFuncPattern(block_num=2)
        """

        self.block_num = block_num

    @op_type_rewrite_pattern
    def match_and_rewrite(self, op: func.FuncOp, rewriter: PatternRewriter) -> None:
        """匹配并改写单个 `func.FuncOp`。

        功能说明:
        - 声明函数和 `entry_point` host dispatcher 保持 no-op。
        - 其余函数复用当前文件内函数级 helper，保持既有 block-strided loop 与 block0 guard 行为。

        使用示例:
        - pattern.match_and_rewrite(func_op, rewriter)
        """

        if op.is_declaration or _is_entry_point_func(op):
            return
        _rewrite_func(op, self.block_num, rewriter)


@dataclass(frozen=True)
class ArchParallelizePass(Pass):
    """arch-parallelize pass。

    功能说明:
    - 公开 pass 名称为 `arch-parallelize`。
    - 按 target registry 静态 `block_num` 物化 block 分片 IR。
    - 带 `entry_point` 属性的 host dispatcher 保持 no-op。
    - 无顶层 `symbol.for` 的其余函数改写为 block0 guard。

    使用示例:
    - ArchParallelizePass(target="npu_demo", parallel_level="block").apply(Context(), module)
    """

    name = "arch-parallelize"
    target: str = "npu_demo"
    parallel_level: str = "block"

    def __init__(self, target: str = "npu_demo", parallel_level: str = "block") -> None:
        """初始化 pass 参数。

        功能说明:
        - 保存目标 target 名称与并行层级。

        使用示例:
        - pass_obj = ArchParallelizePass("npu_demo", "block")
        """

        object.__setattr__(self, "target", target)
        object.__setattr__(self, "parallel_level", parallel_level)

    @classmethod
    def from_options(cls, options: dict[str, str]) -> "ArchParallelizePass":
        """从 registry options 构造 `ArchParallelizePass`。

        功能说明:
        - 只接受 `target` 与 `parallel_level` 两个 pass 专属 option。
        - 未提供时使用公开默认值。

        使用示例:
        - ArchParallelizePass.from_options({"target": "npu_demo", "parallel_level": "block"})
        """

        unknown_options = sorted(set(options) - _VALID_OPTIONS)
        if unknown_options:
            _fail("unknown option(s): " + ", ".join(unknown_options))
        return cls(
            target=options.get("target", "npu_demo"),
            parallel_level=options.get("parallel_level", "block"),
        )

    def apply(self, ctx: Context, module: ModuleOp) -> None:
        """执行 arch-parallelize pass。

        功能说明:
        - 校验参数与 target 后，通过 `PatternRewriteWalker` 驱动 `_ArchParallelizeFuncPattern` 改写非入口函数。
        - 最终运行 `module.verify()`，失败时转成稳定 pass 错误。

        使用示例:
        - ArchParallelizePass().apply(Context(), module)
        """

        ensure_builtin_module(module)
        _validate_options(self.target, self.parallel_level)
        block_num = _validate_target_and_get_block_num(self.target)
        PatternRewriteWalker(
            GreedyRewritePatternApplier(
                [_ArchParallelizeFuncPattern(block_num)],
                ctx=ctx,
                dce_enabled=False,
            ),
            apply_recursively=False,
        ).rewrite_module(module)
        try:
            verify_generated_ops([module])
        except KernelCodeError as exc:
            raise KernelCodeError(
                ErrorKind.CONTRACT,
                ErrorModule.PASS,
                f"ArchParallelizePassVerifierError: {exc}",
            ) from exc


__all__ = ["ArchParallelizePass"]
