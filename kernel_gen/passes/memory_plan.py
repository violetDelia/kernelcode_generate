"""memory-plan pass.

功能说明:
- 提供 `memory-plan` pass，用于在显式 `insert-free=True` 时为受控
  `dma.alloc` 结果补插 `dma.free`。
- `reuse=True` 且 `insert_free=True` 时，在同一受支持 owner block 内对类型完全一致、
  生命周期不重叠的 `dma.alloc` 做保守线性扫描复用。
- 当前阶段只分析 `func.func` body 与 `symbol.for` body 内的单块生命周期；
  owner block 中单块 `scf.if` 分支内的 use 会映射到 `scf.if` 后统一释放。
- `scf.if` 分支内新建 `dma.alloc` 仍按 unsupported control flow 拒绝。
- 通过当前文件内 helper 计算 alias closure，不依赖 `memory_pool` 或其它 pass 私有实现。
- `dma.reinterpret` 与 `dma.view` / `dma.reshape` / `dma.subview` 一样只产生 source alias。

API 列表:
- `class MemoryPlanPass(insert_free: bool = False, fold: bool = True, reuse: bool = False)`
- `MemoryPlanPass.from_options(options: dict[str, str]) -> MemoryPlanPass`
- `MemoryPlanPass.apply(ctx: Context, module: ModuleOp) -> None`

使用示例:
- from kernel_gen.passes.memory_plan import MemoryPlanPass
- pass_obj = MemoryPlanPass(insert_free=True, fold=False, reuse=True)
- pass_obj.apply(ctx, module)

关联文件:
- spec: spec/pass/memory_plan.md
- spec: spec/pass/registry.md
- test: test/passes/test_memory_plan.py
- test: test/passes/test_registry.py
- 功能实现: kernel_gen/passes/memory_plan.py
"""

from __future__ import annotations

from dataclasses import dataclass

from xdsl.context import Context
from xdsl.dialects import func, scf
from xdsl.dialects.builtin import ModuleOp
from xdsl.ir import Block, Operation, SSAValue

from kernel_gen.core.error import ErrorKind, ErrorModule, KernelCodeError
from kernel_gen.dialect.dma import (
    DmaAllocOp,
    DmaDesliceOp,
    DmaFreeOp,
    DmaReinterpretOp,
    DmaReshapeOp,
    DmaSubviewOp,
    DmaViewOp,
)
from kernel_gen.dialect.nn import NnMemoryType
from kernel_gen.dialect.symbol import SymbolForOp, SymbolYieldOp
from kernel_gen.passes.pass_manager import Pass

_TRUE_VALUES = {"1", "true", "yes", "on"}
_FALSE_VALUES = {"0", "false", "no", "off"}


@dataclass(frozen=True)
class _UseRecord:
    """记录 alias closure 中一次 use 的 owner block 锚点与完整位置。

    功能说明:
    - `op` 是真实 use op。
    - `anchor` 是同一 owner block 中能代表该 use 的 op。
    - `position` 是从 owner block 到真实 use 的索引路径，用于区分同一 nested
      `symbol.for` anchor 内部的先后顺序。

    使用示例:
    - record = _UseRecord(use_op, anchor_op, 3, (3, 1))
    """

    op: Operation
    anchor: Operation
    index: int
    position: tuple[int, ...]


@dataclass(frozen=True)
class _AllocationPlan:
    """记录单个 alloc 的 free 插入决策。

    功能说明:
    - `insert_after` 为缺少 free 时的插入锚点。
    - 已存在合法 free 时 `insert_after` 为 `None`。

    使用示例:
    - plan = _AllocationPlan(alloc, owner_block, last_use, None)
    """

    alloc: DmaAllocOp
    owner_block: Block
    insert_after: Operation | None


@dataclass
class _ReuseInterval:
    """记录可参与保守复用的 alloc 生命周期。

    功能说明:
    - `alloc_record` 与 `free_record` 来自同一 owner block 的线性位置。
    - `free_record.op` 是当前生命周期的最终释放点，复用后会延长到后续 interval。

    使用示例:
    - interval = _ReuseInterval(alloc, block, record, free_record)
    """

    alloc: DmaAllocOp
    owner_block: Block
    alloc_record: _UseRecord
    free_record: _UseRecord


class MemoryPlanPass(Pass):
    """memory-plan pass 公开入口。

    功能说明:
    - `insert_free=True` 时补齐 `dma.alloc` 生命周期末尾的 `dma.free`。
    - `reuse=True` 且 `insert_free=True` 时保守复用同 block 内不重叠 alloc。
    - `insert_free=False` 时保持 no-op，不执行生命周期失败检查。

    使用示例:
    - pass_obj = MemoryPlanPass(insert_free=True, reuse=True)
    - pass_obj.apply(ctx, module)
    """

    name = "memory-plan"

    def __init__(
        self: "MemoryPlanPass",
        insert_free: bool = False,
        fold: bool = True,
        reuse: bool = False,
    ) -> None:
        """初始化 memory-plan pass。

        功能说明:
        - 记录 `insert_free` 与 `reuse` 业务开关。
        - 透传 `fold` 到通用 Pass 基类。

        使用示例:
        - MemoryPlanPass(insert_free=True, fold=False, reuse=True)
        """

        super().__init__(fold=fold)
        self.insert_free = bool(insert_free)
        self.reuse = bool(reuse)

    @classmethod
    def from_options(cls: type["MemoryPlanPass"], options: dict[str, str]) -> "MemoryPlanPass":
        """从 registry options 构造 memory-plan pass。

        功能说明:
        - 支持 `insert-free=true|false|1|0|yes|no|on|off`。
        - 支持 `reuse=true|false|1|0|yes|no|on|off`。
        - 未知 option 与非法 bool 使用稳定 `MemoryPlanOptionError` 文本失败。

        使用示例:
        - pass_obj = MemoryPlanPass.from_options({"insert-free": "true", "reuse": "true"})
        """

        insert_free = False
        reuse = False
        for name, value in options.items():
            if name == "insert-free":
                insert_free = _parse_bool_option(name, value)
                continue
            if name == "reuse":
                reuse = _parse_bool_option(name, value)
                continue
            _raise_memory_plan_error(f"MemoryPlanOptionError: unknown option '{name}'")
        return cls(insert_free=insert_free, reuse=reuse)

    def apply(self: "MemoryPlanPass", ctx: Context, module: ModuleOp) -> None:
        """对 module 执行 memory-plan。

        功能说明:
        - `insert_free=False` 时直接返回。
        - `insert_free=True` 时先分析所有 `dma.alloc`，再原地插入缺失的 `dma.free`。
        - `reuse=True` 时在线性 owner block 内把已释放的等价 alloc 复用给后续 alloc。

        使用示例:
        - MemoryPlanPass(insert_free=True, reuse=True).apply(ctx, module)
        """

        _ = ctx
        if not self.insert_free:
            return
        allocs = [op for op in module.walk() if isinstance(op, DmaAllocOp)]
        for alloc in allocs:
            plan = _analyze_allocation(alloc)
            if plan.insert_after is not None:
                plan.owner_block.insert_op_after(DmaFreeOp(alloc.result), plan.insert_after)
        if not self.reuse:
            return
        intervals: list[_ReuseInterval] = []
        for alloc in [op for op in module.walk() if isinstance(op, DmaAllocOp)]:
            owner_block = _owner_block_for_alloc(alloc)
            aliases = _collect_alias_closure(alloc)
            non_free_uses, free_uses = _collect_use_records(aliases, owner_block)
            last_use = _last_non_free_use(non_free_uses, alloc, owner_block)
            _validate_existing_free(free_uses, last_use)
            if len(free_uses) != 1:
                continue
            intervals.append(
                _ReuseInterval(
                    alloc=alloc,
                    owner_block=owner_block,
                    alloc_record=_record_use(alloc, owner_block),
                    free_record=free_uses[0],
                )
            )
        active: list[_ReuseInterval] = []
        for current in sorted(intervals, key=lambda interval: interval.alloc_record.position):
            current_type = current.alloc.result.type
            if not isinstance(current_type, NnMemoryType):
                continue
            reusable: _ReuseInterval | None = None
            for candidate in active:
                if candidate.owner_block is not current.owner_block:
                    continue
                if candidate.alloc.result.type != current_type:
                    continue
                if candidate.free_record.position < current.alloc_record.position:
                    reusable = candidate
                    break
            if reusable is None:
                active.append(current)
                continue
            current.alloc.result.replace_all_uses_with(reusable.alloc.result)
            reusable.owner_block.erase_op(reusable.free_record.op)
            current.owner_block.erase_op(current.alloc)
            reusable.free_record = current.free_record


def _raise_memory_plan_error(message: str) -> None:
    """抛出 memory-plan 稳定错误。

    功能说明:
    - 将本 pass 的所有可预期失败统一包装为 `KernelCodeError`。

    使用示例:
    - _raise_memory_plan_error("MemoryPlanInvalidLifetime: ...")
    """

    raise KernelCodeError(ErrorKind.CONTRACT, ErrorModule.PASS, message)


def _parse_bool_option(name: str, value: str) -> bool:
    """解析 memory-plan bool option。

    功能说明:
    - 接收常见 true/false 文本。
    - 非法文本报 `MemoryPlanOptionError: <name> expects bool`。

    使用示例:
    - enabled = _parse_bool_option("reuse", "true")
    """

    normalized = value.strip().lower()
    if normalized in _TRUE_VALUES:
        return True
    if normalized in _FALSE_VALUES:
        return False
    raise KernelCodeError(
        ErrorKind.CONTRACT,
        ErrorModule.PASS,
        f"MemoryPlanOptionError: {name} expects bool",
    )


def _same_value(candidate: SSAValue | Operation, value: SSAValue) -> bool:
    """判断 operand / operation 是否解析为指定 SSA value。

    功能说明:
    - 统一处理 xDSL operand 里可能出现的 `Operation` 或 `SSAValue` 输入。

    使用示例:
    - if _same_value(op.source, alloc.result): ...
    """

    return SSAValue.get(candidate) is value


def _value_in_operands(value: SSAValue, operands: tuple[SSAValue, ...]) -> bool:
    """判断 value 是否被某 op 的 operands 使用。

    功能说明:
    - 仅用公开 `Operation.operands` 数据判断 use 关系。

    使用示例:
    - used = _value_in_operands(alias, op.operands)
    """

    return any(operand is value for operand in operands)


def _operation_uses_alias(op: Operation, aliases: set[SSAValue]) -> bool:
    """判断 operation 是否使用 alias closure 中任一 value。

    功能说明:
    - 为生命周期分析筛选相关 use。

    使用示例:
    - if _operation_uses_alias(op, aliases): ...
    """

    return any(_value_in_operands(alias, op.operands) for alias in aliases)


def _alias_result_from_source(op: Operation, source: SSAValue) -> SSAValue | None:
    """识别单个 source value 产生的新 alias result。

    功能说明:
    - `dma.view`、`dma.reshape`、`dma.subview`、`dma.reinterpret` 的 result alias source。
    - `dma.deslice` 的 result alias target，不 alias source。

    使用示例:
    - new_alias = _alias_result_from_source(op, alloc.result)
    """

    if isinstance(op, DmaViewOp) and _same_value(op.source, source):
        return op.result
    if isinstance(op, DmaReshapeOp) and _same_value(op.source, source):
        return op.result
    if isinstance(op, DmaSubviewOp) and any(_same_value(operand, source) for operand in op.source):
        return op.result
    if isinstance(op, DmaReinterpretOp) and _same_value(op.source, source):
        return op.result
    if isinstance(op, DmaDesliceOp) and _same_value(op.target, source):
        return op.result
    return None


def _alias_result_from_aliases(op: Operation, aliases: set[SSAValue]) -> SSAValue | None:
    """识别 operation 是否从 alias closure 派生新 alias。

    功能说明:
    - 遍历已有 alias，返回第一个公开规则可证明的新 alias result。

    使用示例:
    - result = _alias_result_from_aliases(op, aliases)
    """

    for alias in aliases:
        result = _alias_result_from_source(op, alias)
        if result is not None:
            return result
    return None


def _collect_alias_closure(alloc: DmaAllocOp) -> set[SSAValue]:
    """收集 alloc result 的 alias closure。

    功能说明:
    - 从 `dma.alloc` result 出发，沿公开 alias 规则递归扩展。

    使用示例:
    - aliases = _collect_alias_closure(alloc)
    """

    aliases: set[SSAValue] = {alloc.result}
    queue = [alloc.result]
    cursor = 0
    while cursor < len(queue):
        value = queue[cursor]
        cursor += 1
        for use in list(value.uses):
            alias = _alias_result_from_source(use.operation, value)
            if alias is None or alias in aliases:
                continue
            aliases.add(alias)
            queue.append(alias)
    return aliases


def _operation_returns_memory(op: Operation) -> bool:
    """判断 operation 是否产生 nn.memory result。

    功能说明:
    - 用于识别无法在第一阶段证明 ownership 的 memory-producing op。

    使用示例:
    - if _operation_returns_memory(op): ...
    """

    return any(isinstance(result.type, NnMemoryType) for result in op.results)


def _owner_block_for_alloc(alloc: DmaAllocOp) -> Block:
    """返回 alloc 所在且被 memory-plan 支持的 owner block。

    功能说明:
    - 第一阶段只支持 `func.func` body 与 `symbol.for` body。

    使用示例:
    - block = _owner_block_for_alloc(alloc)
    """

    block = alloc.parent_block()
    if block is None:
        _raise_memory_plan_error("MemoryPlanUnsupportedEscape: dma.alloc escapes current supported region")
    _verify_supported_owner_block(block)
    return block


def _verify_supported_owner_block(block: Block) -> None:
    """校验 owner block 所属 region 是否受支持。

    功能说明:
    - 支持 `func.func` body 与 `symbol.for` body。
    - `scf.if` 分支内 alloc 暂不建模，仍显式报 unsupported control flow。
    - 其它控制流或多块 region 显式报 unsupported control flow。

    使用示例:
    - _verify_supported_owner_block(block)
    """

    parent = block.parent_op()
    if isinstance(parent, func.FuncOp):
        if len(list(parent.body.blocks)) != 1:
            _raise_memory_plan_error("MemoryPlanUnsupportedControlFlow: unsupported memory lifetime region")
        return
    if isinstance(parent, SymbolForOp):
        if len(list(parent.body.blocks)) != 1:
            _raise_memory_plan_error("MemoryPlanUnsupportedControlFlow: unsupported memory lifetime region")
        return
    _raise_memory_plan_error("MemoryPlanUnsupportedControlFlow: unsupported memory lifetime region")


def _scf_if_branch_index(if_op: scf.IfOp, block: Block) -> int:
    """返回 `scf.if` 单块分支索引。

    功能说明:
    - true 分支返回 `0`，false 分支返回 `1`。
    - 非单块或未知分支按当前 memory-plan 控制流边界稳定失败。

    使用示例:
    - branch = _scf_if_branch_index(if_op, use_block)
    """

    true_blocks = list(if_op.true_region.blocks)
    false_blocks = list(if_op.false_region.blocks)
    if len(true_blocks) != 1 or len(false_blocks) > 1:
        _raise_memory_plan_error("MemoryPlanUnsupportedControlFlow: unsupported memory lifetime region")
    if true_blocks and block is true_blocks[0]:
        return 0
    if false_blocks and block is false_blocks[0]:
        return 1
    _raise_memory_plan_error("MemoryPlanUnsupportedControlFlow: unsupported memory lifetime region")


def _block_index_map(block: Block) -> dict[Operation, int]:
    """构造 block 内 operation 到线性位置的映射。

    功能说明:
    - 用于比较 free 与最后有效 use 的顺序。

    使用示例:
    - indexes = _block_index_map(block)
    """

    return {op: index for index, op in enumerate(block.ops)}


def _map_use_to_owner_block(op: Operation, owner_block: Block) -> tuple[Operation, tuple[int, ...]]:
    """把嵌套 use 映射为 owner block 内的插入锚点和位置路径。

    功能说明:
    - 同 block use 返回自身和单段位置。
    - 位于嵌套 `symbol.for` body 内的 use 返回 owner block 中对应的 ancestor
      `symbol.for`，并保留 nested block 内部位置。
    - 位于 owner block 单块 `scf.if` 分支内的 use 返回对应 `scf.if`，并用
      true/false 分支索引区分同 anchor 内部顺序。
    - 其它控制流或跨 region use 显式失败。

    使用示例:
    - anchor, position = _map_use_to_owner_block(use_op, owner_block)
    """

    block = op.parent_block()
    current_op = op
    reversed_position: list[int] = []
    while True:
        if block is None:
            _raise_memory_plan_error("MemoryPlanUnsupportedEscape: dma.alloc escapes current supported region")
        indexes = _block_index_map(block)
        if current_op not in indexes:
            _raise_memory_plan_error("MemoryPlanUnsupportedEscape: dma.alloc escapes current supported region")
        reversed_position.append(indexes[current_op])
        if block is owner_block:
            return current_op, tuple(reversed(reversed_position))
        parent = block.parent_op()
        if isinstance(parent, func.FuncOp):
            _raise_memory_plan_error("MemoryPlanUnsupportedEscape: dma.alloc escapes current supported region")
        if isinstance(parent, scf.ForOp):
            _raise_memory_plan_error("MemoryPlanUnsupportedControlFlow: unsupported memory lifetime region")
        if isinstance(parent, scf.IfOp):
            reversed_position.append(_scf_if_branch_index(parent, block))
            current_op = parent
            block = parent.parent_block()
            continue
        if not isinstance(parent, SymbolForOp):
            _raise_memory_plan_error("MemoryPlanUnsupportedControlFlow: unsupported memory lifetime region")
        current_op = parent
        block = parent.parent_block()


def _record_use(op: Operation, owner_block: Block) -> _UseRecord:
    """记录 use op 在 owner block 内的线性位置。

    功能说明:
    - 使用 `_map_use_to_owner_block` 处理嵌套 `symbol.for`。

    使用示例:
    - record = _record_use(use_op, block)
    """

    anchor, position = _map_use_to_owner_block(op, owner_block)
    indexes = _block_index_map(owner_block)
    if anchor not in indexes:
        _raise_memory_plan_error("MemoryPlanUnsupportedEscape: dma.alloc escapes current supported region")
    return _UseRecord(op=op, anchor=anchor, index=indexes[anchor], position=position)


def _is_free_for_alias(op: Operation, aliases: set[SSAValue]) -> bool:
    """判断 op 是否释放 alias closure 中的 value。

    功能说明:
    - 当前只识别公开 `dma.free`。

    使用示例:
    - if _is_free_for_alias(op, aliases): ...
    """

    return isinstance(op, DmaFreeOp) and any(_same_value(op.source, alias) for alias in aliases)


def _is_escape_op(op: Operation, aliases: set[SSAValue]) -> bool:
    """判断 use 是否代表当前阶段不支持的逃逸。

    功能说明:
    - `func.return` 与 `symbol.yield` 携带 alias 时视为逃逸。

    使用示例:
    - if _is_escape_op(op, aliases): ...
    """

    if isinstance(op, (func.ReturnOp, SymbolYieldOp)):
        return _operation_uses_alias(op, aliases)
    return op.name in {"func.return", "symbol.yield"} and _operation_uses_alias(op, aliases)


def _validate_supported_use(op: Operation, aliases: set[SSAValue]) -> None:
    """校验单个 use 没有越过第一阶段边界。

    功能说明:
    - memory-return `func.call`、逃逸和未知 memory-producing use 会显式失败。

    使用示例:
    - _validate_supported_use(op, aliases)
    """

    if _is_escape_op(op, aliases):
        _raise_memory_plan_error("MemoryPlanUnsupportedEscape: dma.alloc escapes current supported region")
    if isinstance(op, func.CallOp) and _operation_returns_memory(op):
        _raise_memory_plan_error("MemoryPlanUnsupportedCall: func.call returning nn.memory requires ownership modelling")
    if isinstance(op, DmaDesliceOp):
        return
    if _alias_result_from_aliases(op, aliases) is not None:
        return
    if _operation_returns_memory(op):
        _raise_memory_plan_error("MemoryPlanUnsupportedEscape: dma.alloc escapes current supported region")


def _collect_use_records(aliases: set[SSAValue], owner_block: Block) -> tuple[list[_UseRecord], list[_UseRecord]]:
    """收集 alias closure 的 non-free use 与 free use。

    功能说明:
    - 返回 `(non_free_uses, free_uses)`。
    - `dma.free` 单列，不计入最后有效 use。

    使用示例:
    - non_free, free = _collect_use_records(aliases, block)
    """

    non_free_uses: list[_UseRecord] = []
    free_uses: list[_UseRecord] = []
    seen_ops: set[Operation] = set()
    for alias in aliases:
        for use in list(alias.uses):
            op = use.operation
            if op in seen_ops:
                continue
            if not _operation_uses_alias(op, aliases):
                continue
            seen_ops.add(op)
            _validate_supported_use(op, aliases)
            record = _record_use(op, owner_block)
            if _is_free_for_alias(op, aliases):
                free_uses.append(record)
            else:
                non_free_uses.append(record)
    return non_free_uses, free_uses


def _last_non_free_use(non_free_uses: list[_UseRecord], alloc: DmaAllocOp, owner_block: Block) -> _UseRecord:
    """返回最后有效 use，缺少 use 时以 alloc 自身为锚点。

    功能说明:
    - 用于决定缺失 `dma.free` 的插入位置。

    使用示例:
    - last_use = _last_non_free_use(records, alloc, block)
    """

    if non_free_uses:
        return max(non_free_uses, key=lambda record: record.position)
    return _record_use(alloc, owner_block)


def _validate_existing_free(free_uses: list[_UseRecord], last_use: _UseRecord) -> None:
    """校验已有 free 是否合法。

    功能说明:
    - 多个 free、nested body 内释放 owner-block alloc、free 早于后续 use
      均按稳定错误失败。

    使用示例:
    - _validate_existing_free(free_records, last_use)
    """

    if len(free_uses) > 1:
        _raise_memory_plan_error("MemoryPlanInvalidLifetime: multiple dma.free for same allocation")
    if not free_uses:
        return
    if free_uses[0].anchor is not free_uses[0].op:
        _raise_memory_plan_error("MemoryPlanInvalidLifetime: dma.free appears before last use")
    if free_uses[0].position < last_use.position:
        _raise_memory_plan_error("MemoryPlanInvalidLifetime: dma.free appears before last use")


def _analyze_allocation(alloc: DmaAllocOp) -> _AllocationPlan:
    """分析单个 `dma.alloc` 的 free 插入计划。

    功能说明:
    - 建立 alias closure。
    - 校验已有 free。
    - 缺少 free 时返回插入锚点。

    使用示例:
    - plan = _analyze_allocation(alloc)
    """

    owner_block = _owner_block_for_alloc(alloc)
    aliases = _collect_alias_closure(alloc)
    non_free_uses, free_uses = _collect_use_records(aliases, owner_block)
    last_use = _last_non_free_use(non_free_uses, alloc, owner_block)
    _validate_existing_free(free_uses, last_use)
    if free_uses:
        return _AllocationPlan(alloc=alloc, owner_block=owner_block, insert_after=None)
    return _AllocationPlan(alloc=alloc, owner_block=owner_block, insert_after=last_use.anchor)
