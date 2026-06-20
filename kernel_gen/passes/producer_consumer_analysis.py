"""producer-consumer-analysis pass.


功能说明:
- 提供 `producer-consumer-analysis` pass，基于公开 `MemoryEffect` 标注生产 / 消费 event。
- 使用当前文件内 alias 规则处理 `dma.view`、`dma.reshape`、`dma.subview`、`dma.reinterpret` 与 `dma.deslice`。
- 对 `dma.alloc` 与 `dma.make_ring` init root 只连接第一组真实 READ / WRITE first-touch edge。
- 对 ring soft-pipeline 形态补充 `loop_first_*`、`loop_carried_*` 与 `after_loop_*` 标注。
- 同一 producer -> consumer edge 只写普通 event 对或一个控制流 event 对，不生成 wait/sign 或 runtime 同步 op。

API 列表:
- `class ProducerConsumerAnalysisPass(fold: bool = True)`
- `ProducerConsumerAnalysisPass.from_options(options: dict[str, str]) -> ProducerConsumerAnalysisPass`
- `ProducerConsumerAnalysisPass.apply(ctx: Context, module: ModuleOp) -> None`

使用示例:
- from kernel_gen.passes.producer_consumer_analysis import ProducerConsumerAnalysisPass
- ProducerConsumerAnalysisPass().apply(Context(), module)
- ProducerConsumerAnalysisPass.from_options({})

关联文件:
- spec: spec/pass/producer_consumer_analysis.md
- spec: spec/pass/registry.md
- test: test/passes/test_producer_consumer_analysis.py
- 功能实现: kernel_gen/passes/producer_consumer_analysis.py
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from typing import TypeAlias

from xdsl.context import Context
from xdsl.dialects import func, scf
from xdsl.dialects.builtin import ArrayAttr, IntegerAttr, IntAttr, ModuleOp
from xdsl.ir import Attribute, Block, BuiltinAttribute, Data, Operation, SSAValue
from xdsl.parser import AttrParser
from xdsl.printer import Printer
from xdsl.traits import MemoryEffectKind, get_effects

from kernel_gen.core.error import ErrorKind, ErrorModule, KernelCodeError
from kernel_gen.dialect.dma import (
    DmaAdvanceRingOp,
    DmaCurrentRingOp,
    DmaMakeRingOp,
    DmaReinterpretOp,
    DmaReshapeOp,
    DmaSubviewOp,
    DmaViewOp,
)
from kernel_gen.dialect.nn import NnMemoryType
from kernel_gen.dialect.symbol import SymbolForOp
from kernel_gen.passes.common import ensure_builtin_module
from kernel_gen.passes.pass_manager import Pass

_EVENT_ATTR_NAMES = (
    "productor",
    "consumer",
    "if_branch_productor",
    "if_branch_consumer",
    "after_if_productor",
    "after_if_consumer",
    "loop_body_productor",
    "loop_body_consumer",
    "after_loop_productor",
    "after_loop_consumer",
    "loop_first_productor",
    "loop_first_consumer",
    "loop_carried_productor",
    "loop_carried_consumer",
)

_ControlOp: TypeAlias = scf.IfOp | SymbolForOp


class _EventListAttr(BuiltinAttribute, Data[tuple[int, ...]]):
    """当前文件私有的简单整数列表 attr。


    功能说明:
    - 让 pass 输出 `productor = [0, 1]` 这种裸列表文本。
    - 不注册 dialect attribute，不作为公开 API 暴露。

    使用示例:
    - attr = _EventListAttr((0, 1))

    关联文件:
    - spec: spec/pass/producer_consumer_analysis.md
    - test: test/passes/test_producer_consumer_analysis.py
    - 功能实现: kernel_gen/passes/producer_consumer_analysis.py
    """

    @classmethod
    def parse_parameter(cls: type["_EventListAttr"], parser: AttrParser) -> tuple[int, ...]:
        """解析参数。

        功能说明:
        - 当前私有 attr 只由 pass 构造，不通过 dialect parser 公开解析。
        - 为满足 xDSL `Data` 抽象接口返回空 tuple。

        使用示例:
        - parsed = _EventListAttr.parse_parameter(parser)
        """

        _ = parser
        return ()

    def print_parameter(self: "_EventListAttr", printer: Printer) -> None:
        """打印参数。

        功能说明:
        - `BuiltinAttribute.print_builtin(...)` 已承载全部公开文本。
        - 该方法只满足 xDSL `Data` 抽象接口。

        使用示例:
        - attr.print_parameter(printer)
        """

        _ = printer

    def print_builtin(self: "_EventListAttr", printer: Printer) -> None:
        """打印裸整数列表。

        功能说明:
        - 输出 `[0]` 或 `[0, 1]`，避免 `#builtin.int`、`: i64` 或 `array<i64: ...>`。

        使用示例:
        - Printer(...).print_attribute(_EventListAttr((0, 1)))
        """

        printer.print_string("[")
        for index, event_id in enumerate(self.data):
            if index:
                printer.print_string(", ")
            printer.print_string(str(event_id))
        printer.print_string("]")


@dataclass(frozen=True)
class _ProducerCandidate:
    """单个 producer value 及其 owner op。

    功能说明:
    - 记录 `ALLOC/WRITE` effect 产生的 memory value，或 `dma.make_ring` 产生的 ring init root。
    - `kind` 区分 init first-touch candidate 与普通 WRITE data candidate。

    使用示例:
    - candidate = _ProducerCandidate(op, value, root, "write")
    """

    op: Operation
    value: SSAValue
    root: SSAValue
    kind: str


@dataclass(frozen=True)
class _EdgeRelation:
    """producer -> consumer edge 的控制流分类。

    功能说明:
    - `kind=None` 表示普通同一路径 edge。
    - `control_op` 用于 `scf.if` incoming branch consumer 按互斥路径共享 event。
    - `branch_index` 记录 consumer 所在 `scf.if` region，用于区分同一分支 fanout。
    - `share_control_event` 只在 if 外 producer 进入 then/else 互斥分支时为真。

    使用示例:
    - relation = _EdgeRelation("loop_body", loop_op, False)
    """

    kind: str | None
    control_op: _ControlOp | None
    share_control_event: bool
    branch_index: int | None = None


@dataclass(frozen=True)
class _ConsumerEdge:
    """单条 downstream consumer edge。

    功能说明:
    - 绑定 consumer op 与控制流分类。
    - `group_key` 由调用方基于 fanout / if branch 共享规则生成。

    使用示例:
    - edge = _ConsumerEdge(consumer_op, relation)
    """

    consumer_op: Operation
    relation: _EdgeRelation


@dataclass(frozen=True)
class _RingEventSpec:
    """ring-aware producer/consumer event 候选。

    功能说明:
    - 绑定 producer/consumer op 与最终写回的 ring-aware attr 名。
    - 由调用方按 op 顺序分配稳定 event id。

    使用示例:
    - spec = _RingEventSpec(producer_op, consumer_op, "loop_first_productor", "loop_first_consumer", 1, 2)
    """

    producer_op: Operation
    consumer_op: Operation
    producer_attr: str
    consumer_attr: str
    producer_order: int
    consumer_order: int


class _RingAwareAnalysis:
    """ring-aware producer-consumer 事件补充逻辑容器。

    功能说明:
    - 基于 `dma.current_ring` / `dma.advance_ring` 的 cursor 语义补充 loop_first / loop_carried / after_loop 标注。
    - 保留现有 SSA 依赖分析的普通 event 输出，不暴露共享 cursor API。

    使用示例:
    - next_event_id = _RingAwareAnalysis.add_ring_events(...)
    """

    @staticmethod
    def ring_roots_by_op(ops: tuple[Operation, ...], alias_roots: dict[SSAValue, SSAValue]) -> dict[SSAValue, SSAValue]:
        """构建 ring root -> ring operand 映射。

        功能说明:
        - `dma.current_ring` 的 result root 代表一个 ring cursor slot root。
        - `dma.reinterpret` alias 链会把后续写入/读取归一到同一 root。

        使用示例:
        - ring_roots = _RingAwareAnalysis.ring_roots_by_op(ops, alias_roots)
        """

        ring_roots: dict[SSAValue, SSAValue] = {}
        for op in ops:
            if not isinstance(op, DmaCurrentRingOp):
                continue
            root = _alias_root(SSAValue.get(op.result), alias_roots)
            ring_roots[root] = SSAValue.get(op.ring)
        return ring_roots

    @staticmethod
    def collect_accesses(
        ops: tuple[Operation, ...],
        alias_roots: dict[SSAValue, SSAValue],
        ring_roots: dict[SSAValue, SSAValue],
        kind: MemoryEffectKind,
    ) -> dict[SSAValue, list[tuple[int, Operation]]]:
        """按 ring 收集 READ/WRITE 访问。

        功能说明:
        - 只记录能归一到 ring root 的 `!nn.memory` effect。
        - 每个 `op`/`ring` 组合只记一次，避免同一 op 多个 effect value 重复污染事件顺序。

        使用示例:
        - writes = _RingAwareAnalysis.collect_accesses(loop_ops, alias_roots, ring_roots, MemoryEffectKind.WRITE)
        """

        accesses: dict[SSAValue, list[tuple[int, Operation]]] = defaultdict(list)
        seen: set[tuple[Operation, SSAValue]] = set()
        for op_order, op in enumerate(ops):
            for value in _effect_values(op, kind):
                root = _alias_root(value, alias_roots)
                ring = ring_roots.get(root)
                if ring is None:
                    continue
                key = (op, ring)
                if key in seen:
                    continue
                seen.add(key)
                accesses[ring].append((op_order, op))
        return accesses

    @staticmethod
    def add_ring_events(
        ops: tuple[Operation, ...],
        alias_roots: dict[SSAValue, SSAValue],
        event_attrs: dict[Operation, dict[str, list[int]]],
        next_event_id: int,
    ) -> int:
        """补充 ring-aware event 标注。

        功能说明:
        - 对每个 `symbol.for` 单独分析 prologue / loop body / epilogue 的 ring cursor 事实。
        - 生成 `loop_first_*`、`loop_carried_*`、`after_loop_*` 三类补充事件。

        使用示例:
        - next_event_id = _RingAwareAnalysis.add_ring_events(ops, alias_roots, event_attrs, 0)
        """

        ring_specs: list[_RingEventSpec] = []
        ring_roots = _RingAwareAnalysis.ring_roots_by_op(ops, alias_roots)
        op_order = {op: index for index, op in enumerate(ops)}
        for loop in (op for op in ops if isinstance(op, SymbolForOp)):
            parent_block = loop.parent_block()
            blocks = tuple(loop.body.blocks)
            if parent_block is None or len(blocks) != 1:
                continue
            body_block = blocks[0]
            before_ops = tuple(op for op in parent_block.ops if op is not loop and op.is_before_in_block(loop))
            after_ops = tuple(op for op in parent_block.ops if op is not loop and loop.is_before_in_block(op))
            loop_ops = tuple(body_block.ops)
            if not loop_ops:
                continue
            before_writes = _RingAwareAnalysis.collect_accesses(before_ops, alias_roots, ring_roots, MemoryEffectKind.WRITE)
            loop_reads = _RingAwareAnalysis.collect_accesses(loop_ops, alias_roots, ring_roots, MemoryEffectKind.READ)
            loop_writes = _RingAwareAnalysis.collect_accesses(loop_ops, alias_roots, ring_roots, MemoryEffectKind.WRITE)
            after_reads = _RingAwareAnalysis.collect_accesses(after_ops, alias_roots, ring_roots, MemoryEffectKind.READ)
            advance_index_by_ring: dict[SSAValue, int] = {}
            for index, op in enumerate(loop_ops):
                if isinstance(op, DmaAdvanceRingOp):
                    ring = SSAValue.get(op.ring)
                    advance_index_by_ring.setdefault(ring, index)
            for ring, advance_index in advance_index_by_ring.items():
                prologue_write = _RingAwareAnalysis.latest_access_before(tuple(before_writes.get(ring, ())))
                loop_read = _RingAwareAnalysis.first_access_before(tuple(loop_reads.get(ring, ())), advance_index)
                loop_write = _RingAwareAnalysis.first_access_after(tuple(loop_writes.get(ring, ())), advance_index)
                after_read = _RingAwareAnalysis.first_access_after(tuple(after_reads.get(ring, ())), -1)
                if prologue_write is not None and loop_read is not None:
                    ring_specs.append(
                        _RingEventSpec(
                            prologue_write[1],
                            loop_read[1],
                            "loop_first_productor",
                            "loop_first_consumer",
                            op_order.get(prologue_write[1], prologue_write[0]),
                            op_order.get(loop_read[1], loop_read[0]),
                        )
                    )
                if loop_write is not None and loop_read is not None:
                    ring_specs.append(
                        _RingEventSpec(
                            loop_write[1],
                            loop_read[1],
                            "loop_carried_productor",
                            "loop_carried_consumer",
                            op_order.get(loop_write[1], loop_write[0]),
                            op_order.get(loop_read[1], loop_read[0]),
                        )
                    )
                if loop_write is not None and after_read is not None:
                    ring_specs.append(
                        _RingEventSpec(
                            loop_write[1],
                            after_read[1],
                            "after_loop_productor",
                            "after_loop_consumer",
                            op_order.get(loop_write[1], loop_write[0]),
                            op_order.get(after_read[1], after_read[0]),
                        )
                    )
        for spec in sorted(ring_specs, key=lambda item: (item.producer_order, item.consumer_order, item.producer_attr, item.consumer_attr)):
            event_id = next_event_id
            next_event_id += 1
            _append_event(event_attrs, spec.producer_op, spec.producer_attr, event_id)
            _append_event(event_attrs, spec.consumer_op, spec.consumer_attr, event_id)
        return next_event_id

    @staticmethod
    def latest_access_before(accesses: tuple[tuple[int, Operation], ...]) -> tuple[int, Operation] | None:
        """返回一组访问中的最后一个元素。

        功能说明:
        - 用于 prologue producer 选择 loop 前最后一次写入。

        使用示例:
        - access = _RingAwareAnalysis.latest_access_before(accesses)
        """

        if not accesses:
            return None
        return accesses[-1]

    @staticmethod
    def first_access_before(
        accesses: tuple[tuple[int, Operation], ...],
        upper_bound: int,
    ) -> tuple[int, Operation] | None:
        """返回小于上界的第一个访问。

        功能说明:
        - 用于 loop body 内 first-read 的 cursor 选择。

        使用示例:
        - access = _RingAwareAnalysis.first_access_before(accesses, advance_index)
        """

        for access in accesses:
            if access[0] < upper_bound:
                return access
        return None

    @staticmethod
    def first_access_after(
        accesses: tuple[tuple[int, Operation], ...],
        lower_bound: int,
    ) -> tuple[int, Operation] | None:
        """返回大于下界的第一个访问。

        功能说明:
        - 用于 loop body 内 advance 之后的 carried producer 与 after-loop consumer 选择。

        使用示例:
        - access = _RingAwareAnalysis.first_access_after(accesses, advance_index)
        """

        for access in accesses:
            if access[0] > lower_bound:
                return access
        return None


def _raise_error(message: str) -> None:
    """抛出 producer-consumer-analysis 稳定合同错误。

    功能说明:
    - 统一错误前缀，供 registry / pytest / expectation 机械匹配。

    使用示例:
    - _raise_error("unknown option: mode")
    """

    raise KernelCodeError(
        ErrorKind.CONTRACT,
        ErrorModule.PASS,
        f"ProducerConsumerAnalysisPassError: {message}",
    )


def _event_list_values(attr: Attribute) -> tuple[int, ...]:
    """读取合法 event 列表 attr。

    功能说明:
    - 接受本 pass 私有 `_EventListAttr`。
    - 接受 parser 读回的 `ArrayAttr(IntegerAttr)` / `ArrayAttr(IntAttr)` 旧形态。
    - 其它形态或负数立即失败。

    使用示例:
    - values = _event_list_values(op.attributes["productor"])
    """

    if isinstance(attr, _EventListAttr):
        values = attr.data
    elif isinstance(attr, ArrayAttr):
        collected: list[int] = []
        for item in attr.data:
            if isinstance(item, IntAttr):
                value = int(item.data)
            elif isinstance(item, IntegerAttr):
                value = int(item.value.data)
            else:
                _raise_error("invalid event attr")
            collected.append(value)
        values = tuple(collected)
    else:
        _raise_error("invalid event attr")
    if any(value < 0 for value in values):
        _raise_error("invalid event attr")
    return values


def _clear_event_attrs(op: Operation) -> None:
    """校验并清理旧 event attrs。

    功能说明:
    - pass rerun 前先验证合法旧 attr，再删除旧结果，避免重复追加或吞掉非法输入。

    使用示例:
    - _clear_event_attrs(op)
    """

    for attr_name in _EVENT_ATTR_NAMES:
        if attr_name not in op.attributes:
            continue
        _event_list_values(op.attributes[attr_name])
        del op.attributes[attr_name]


def _is_memory_value(value: SSAValue) -> bool:
    """判断 SSA value 是否为 `!nn.memory`。

    功能说明:
    - producer-consumer-analysis 只处理 memory 数据流。

    使用示例:
    - if _is_memory_value(value): ...
    """

    return isinstance(value.type, NnMemoryType)


def _effect_values(op: Operation, kind: MemoryEffectKind) -> tuple[SSAValue, ...]:
    """读取 op 上指定 kind 的 memory effect value。

    功能说明:
    - 只使用 xDSL 公开 `get_effects(op)` 入口。
    - 忽略无 value 或非 `!nn.memory` 的 effect。

    使用示例:
    - reads = _effect_values(op, MemoryEffectKind.READ)
    """

    if isinstance(op, (func.FuncOp, scf.IfOp, SymbolForOp)):
        return ()
    effects = get_effects(op)
    if not effects:
        return ()
    values: list[SSAValue] = []
    for effect in effects:
        if effect.kind != kind or not isinstance(effect.value, SSAValue):
            continue
        value = SSAValue.get(effect.value)
        if _is_memory_value(value):
            values.append(value)
    return tuple(values)


def _walk_block_ops(block: Block) -> tuple[Operation, ...]:
    """按词法顺序遍历 block 与嵌套 region op。

    功能说明:
    - 用同一顺序驱动 producer candidate 排序和 event id 分配。
    - 控制流 op 本身先出现，随后遍历其 region，再继续后续 sibling。

    使用示例:
    - ops = _walk_block_ops(func_op.body.blocks[0])
    """

    ops: list[Operation] = []
    for op in block.ops:
        ops.append(op)
        for region in op.regions:
            for nested_block in region.blocks:
                ops.extend(_walk_block_ops(nested_block))
    return tuple(ops)


def _walk_func_ops(func_op: func.FuncOp) -> tuple[Operation, ...]:
    """遍历非声明函数体内 op。

    功能说明:
    - declaration 没有 body，保持 no-op。

    使用示例:
    - ops = _walk_func_ops(func_op)
    """

    if func_op.is_declaration:
        return ()
    ops: list[Operation] = []
    for block in func_op.body.blocks:
        ops.extend(_walk_block_ops(block))
    return tuple(ops)


def _alias_root(value: SSAValue, alias_roots: dict[SSAValue, SSAValue]) -> SSAValue:
    """返回 value 的 alias root。

    功能说明:
    - 对未命中 alias 表的 value 返回自身。
    - 检测自环后停止，避免错误 IR 造成无限追踪。

    使用示例:
    - root = _alias_root(value, alias_roots)
    """

    seen: set[SSAValue] = set()
    current = value
    while current in alias_roots and current not in seen:
        seen.add(current)
        current = alias_roots[current]
    return current


def _build_alias_roots(ops: tuple[Operation, ...]) -> dict[SSAValue, SSAValue]:
    """构建当前函数内 alias root 表。

    功能说明:
    - `dma.view/reshape/subview/reinterpret` 的 result alias source。
    - `dma.deslice` 是目标式写回 op，不产生 alias result。

    使用示例:
    - alias_roots = _build_alias_roots(ops)
    """

    alias_roots: dict[SSAValue, SSAValue] = {}

    for op in ops:
        if isinstance(op, (DmaViewOp, DmaReshapeOp, DmaSubviewOp, DmaReinterpretOp)):
            alias_roots[SSAValue.get(op.result)] = _alias_root(SSAValue.get(op.source), alias_roots)
    return {value: _alias_root(value, alias_roots) for value in alias_roots}


def _build_alias_groups(
    ops: tuple[Operation, ...],
    alias_roots: dict[SSAValue, SSAValue],
) -> dict[SSAValue, set[SSAValue]]:
    """按 alias root 收集 value 集合。

    功能说明:
    - downstream user 遍历需要同时查看 root value 与所有 alias result 的 uses。

    使用示例:
    - groups = _build_alias_groups(ops, alias_roots)
    """

    groups: dict[SSAValue, set[SSAValue]] = defaultdict(set)
    for op in ops:
        for value in (*op.operands, *op.results):
            ssa_value = SSAValue.get(value)
            if not _is_memory_value(ssa_value):
                continue
            groups[_alias_root(ssa_value, alias_roots)].add(ssa_value)
    return groups


def _if_branch_index(control_op: scf.IfOp, op: Operation) -> int | None:
    """返回 op 所属 `scf.if` region 序号。

    功能说明:
    - 仅用于 if-external producer 进入 branch consumer 的 event 分组。
    - 找不到所属 region 时返回 None，由调用方退回普通 fanout。

    使用示例:
    - branch_index = _if_branch_index(if_op, consumer_op)
    """

    for region_index, region in enumerate(control_op.regions):
        for block in region.blocks:
            if block.find_ancestor_op_in_block(op) is not None:
                return region_index
    return None


def _classify_edge(producer_op: Operation, consumer_op: Operation) -> _EdgeRelation | None:
    """判定 producer 到 consumer 是否是本阶段支持的 downstream edge。

    功能说明:
    - 支持同 block 词法后继。
    - 支持 if/loop 前 producer 进入分支或 loop body。
    - 支持 if/loop 内 producer 到控制流后 consumer。
    - 同一 block 内普通顺序 edge 保持主 `productor` / `consumer` 关系。

    使用示例:
    - relation = _classify_edge(producer_op, consumer_op)
    """

    if producer_op is consumer_op:
        return None
    producer_block = producer_op.parent_block()
    consumer_block = consumer_op.parent_block()
    if producer_block is None or consumer_block is None:
        return None
    if producer_block is consumer_block:
        if not producer_op.is_before_in_block(consumer_op):
            return None
        return _EdgeRelation(None, None, False)

    consumer_ancestor = producer_block.find_ancestor_op_in_block(consumer_op)
    if isinstance(consumer_ancestor, SymbolForOp) and producer_op.is_before_in_block(consumer_ancestor):
        return _EdgeRelation("loop_body", consumer_ancestor, False)
    if isinstance(consumer_ancestor, scf.IfOp) and producer_op.is_before_in_block(consumer_ancestor):
        return _EdgeRelation(
            "if_branch",
            consumer_ancestor,
            True,
            _if_branch_index(consumer_ancestor, consumer_op),
        )

    producer_ancestor = consumer_block.find_ancestor_op_in_block(producer_op)
    if isinstance(producer_ancestor, SymbolForOp) and producer_ancestor.is_before_in_block(consumer_op):
        return _EdgeRelation("after_loop", producer_ancestor, False)
    if isinstance(producer_ancestor, scf.IfOp) and producer_ancestor.is_before_in_block(consumer_op):
        return _EdgeRelation("after_if", producer_ancestor, False)
    return None


def _read_roots_by_op(
    ops: tuple[Operation, ...],
    alias_roots: dict[SSAValue, SSAValue],
) -> dict[Operation, set[SSAValue]]:
    """计算每个 op 的 READ alias root 集合。

    功能说明:
    - 用于判断某个 SSA use 是否是 meaningful consumer，而不是 target/write use。

    使用示例:
    - read_roots = _read_roots_by_op(ops, alias_roots)
    """

    roots: dict[Operation, set[SSAValue]] = {}
    for op in ops:
        op_roots = {_alias_root(value, alias_roots) for value in _effect_values(op, MemoryEffectKind.READ)}
        if op_roots:
            roots[op] = op_roots
    return roots


def _group_consumer_edges(edges: tuple[_ConsumerEdge, ...]) -> tuple[tuple[_ConsumerEdge, ...], ...]:
    """按 event 共享规则分组 downstream consumer edges。

    功能说明:
    - 普通 fanout 每个 consumer op 一个 event。
    - `scf.if` incoming producer 到 then/else branch 同序 consumer 时共享同一个 event。
    - 同一分支内多个 downstream consumer 按 ordinal 分配独立 event。

    使用示例:
    - groups = _group_consumer_edges(edges)
    """

    grouped_edges: dict[tuple[str, int, int], list[_ConsumerEdge]] = defaultdict(list)
    branch_ordinals: dict[tuple[int, int], int] = defaultdict(int)
    for edge in edges:
        relation = edge.relation
        if (
            relation.kind == "if_branch"
            and relation.control_op is not None
            and relation.share_control_event
            and relation.branch_index is not None
        ):
            branch_key = (id(relation.control_op), relation.branch_index)
            ordinal = branch_ordinals[branch_key]
            branch_ordinals[branch_key] += 1
            grouped_edges[("if_branch", id(relation.control_op), ordinal)].append(edge)
        else:
            grouped_edges[("consumer", id(edge.consumer_op), 0)].append(edge)
    return tuple(tuple(group) for group in grouped_edges.values())


def _relation_attr_names(relation: _EdgeRelation) -> tuple[str, str]:
    """返回当前 edge 唯一写入的 productor/consumer attr 名。

    功能说明:
    - 普通 edge 写主 `productor` / `consumer`。
    - 控制流 edge 写对应分类 attr，不再叠写主 `productor` / `consumer`。

    使用示例:
    - producer_attr, consumer_attr = _relation_attr_names(edge.relation)
    """

    if relation.kind is None:
        return "productor", "consumer"
    return f"{relation.kind}_productor", f"{relation.kind}_consumer"


def _append_event(
    event_attrs: dict[Operation, dict[str, list[int]]],
    op: Operation,
    attr_name: str,
    event_id: int,
) -> None:
    """向 op 的 event attr 暂存表追加 id。

    功能说明:
    - 保持 event id 插入顺序。
    - 同一 attr 内同一 event id 不重复追加。

    使用示例:
    - _append_event(event_attrs, op, "consumer", 0)
    """

    values = event_attrs[op][attr_name]
    if event_id not in values:
        values.append(event_id)


def _collect_consumer_edges(
    candidate: _ProducerCandidate,
    alias_groups: dict[SSAValue, set[SSAValue]],
    read_roots: dict[Operation, set[SSAValue]],
    op_order: dict[Operation, int],
) -> tuple[_ConsumerEdge, ...]:
    """从 producer value 遍历 downstream meaningful consumers。

    功能说明:
    - 遍历 root value 与 alias value 的 SSA users。
    - 仅当 user op 对同一 alias root 暴露 `READ` effect 时视为 consumer。

    使用示例:
    - edges = _collect_consumer_edges(candidate, groups, read_roots, op_order)
    """

    edges_by_op: dict[Operation, _ConsumerEdge] = {}
    for value in alias_groups.get(candidate.root, {candidate.root}):
        for use in tuple(value.uses):
            consumer_op = use.operation
            if candidate.root not in read_roots.get(consumer_op, set()):
                continue
            relation = _classify_edge(candidate.op, consumer_op)
            if relation is None:
                continue
            if consumer_op not in edges_by_op:
                edges_by_op[consumer_op] = _ConsumerEdge(consumer_op, relation)
    return tuple(sorted(edges_by_op.values(), key=lambda edge: op_order.get(edge.consumer_op, 0)))


def _apply_event_attrs(
    ops: tuple[Operation, ...],
    event_attrs: dict[Operation, dict[str, list[int]]],
) -> None:
    """把暂存 event attrs 写回 IR。

    功能说明:
    - 统一转换为 `_EventListAttr`，确保最终 IR 打印为简单整数列表。

    使用示例:
    - _apply_event_attrs(ops, event_attrs)
    """

    for op in ops:
        for attr_name, event_ids in event_attrs.get(op, {}).items():
            if event_ids:
                op.attributes[attr_name] = _EventListAttr(tuple(event_ids))


@dataclass(frozen=True)
class ProducerConsumerAnalysisPass(Pass):
    """生产消费分析 pass。

    功能说明:
    - 固定公开 pass name 为 `producer-consumer-analysis`。
    - 基于公开 `MemoryEffect` 与当前文件内 alias 规则标注 producer/consumer event。
    - 基于 `dma.current_ring` / `dma.advance_ring` cursor 事实补充 ring-aware loop event。
    - 第一阶段不接受 pass 专属 options。

    使用示例:
    - ProducerConsumerAnalysisPass().apply(Context(), module)
    - ProducerConsumerAnalysisPass.from_options({})

    关联文件:
    - spec: spec/pass/producer_consumer_analysis.md
    - test: test/passes/test_producer_consumer_analysis.py
    - 功能实现: kernel_gen/passes/producer_consumer_analysis.py
    """

    name = "producer-consumer-analysis"
    fold: bool = True

    def __init__(self: "ProducerConsumerAnalysisPass", fold: bool = True) -> None:
        """初始化 pass。

        功能说明:
        - 只记录通用 `fold` 开关。
        - 不提供 attr name、alias table 或 control-flow 策略自定义入口。

        使用示例:
        - pass_obj = ProducerConsumerAnalysisPass(fold=False)
        """

        object.__setattr__(self, "fold", bool(fold))

    @classmethod
    def from_options(
        cls: type["ProducerConsumerAnalysisPass"],
        options: dict[str, str],
    ) -> "ProducerConsumerAnalysisPass":
        """从 registry pass 专属 options 构造 pass。

        功能说明:
        - 第一阶段只接受空 pass 专属 options。
        - 通用 `fold` 由 registry 先拆分，不在本入口兼容。

        使用示例:
        - pass_obj = ProducerConsumerAnalysisPass.from_options({})
        """

        if options:
            unknown = ", ".join(sorted(options))
            _raise_error(f"unknown option: {unknown}")
        return cls()

    def apply(self: "ProducerConsumerAnalysisPass", ctx: Context, module: ModuleOp) -> None:
        """执行生产消费分析。

        功能说明:
        - 校验输入为 `builtin.module`。
        - 对每个非声明 `func.func` 分别标注 producer/consumer event。
        - 对 `dma.alloc` 与 `dma.make_ring` init candidate 只连接 first-touch edge group。

        使用示例:
        - ProducerConsumerAnalysisPass().apply(Context(), module)
        """

        _ = ctx
        target = ensure_builtin_module(module)
        for func_op in target.ops:
            if not isinstance(func_op, func.FuncOp) or func_op.is_declaration:
                continue
            ops = _walk_func_ops(func_op)
            for op in ops:
                _clear_event_attrs(op)
            alias_roots = _build_alias_roots(ops)
            alias_groups = _build_alias_groups(ops, alias_roots)
            read_roots = _read_roots_by_op(ops, alias_roots)
            touch_roots: dict[Operation, set[SSAValue]] = {}
            for op in ops:
                op_roots = {
                    _alias_root(value, alias_roots)
                    for value in (
                        *_effect_values(op, MemoryEffectKind.READ),
                        *_effect_values(op, MemoryEffectKind.WRITE),
                    )
                }
                if op_roots:
                    touch_roots[op] = op_roots
            init_alias_roots: dict[SSAValue, SSAValue] = {}
            ring_init_roots: dict[SSAValue, SSAValue] = {}
            for op in ops:
                if isinstance(op, DmaMakeRingOp):
                    ring_value = SSAValue.get(op.result)
                    ring_init_roots[ring_value] = ring_value
                    init_alias_roots[ring_value] = ring_value
                    continue
                if isinstance(op, (DmaCurrentRingOp, DmaAdvanceRingOp)):
                    ring_value = SSAValue.get(op.ring)
                    ring_root = ring_init_roots.get(ring_value)
                    if ring_root is not None:
                        init_alias_roots[_alias_root(SSAValue.get(op.result), alias_roots)] = ring_root
            op_order = {op: index for index, op in enumerate(ops)}
            event_attrs: dict[Operation, dict[str, list[int]]] = defaultdict(lambda: defaultdict(list))
            next_event_id = 0
            candidates: list[_ProducerCandidate] = []
            for op in ops:
                seen_roots: set[SSAValue] = set()
                for value in _effect_values(op, MemoryEffectKind.ALLOC):
                    root = _alias_root(value, alias_roots)
                    if root in seen_roots:
                        continue
                    seen_roots.add(root)
                    candidates.append(_ProducerCandidate(op, value, root, "init"))
                if isinstance(op, DmaMakeRingOp):
                    value = SSAValue.get(op.result)
                    root = init_alias_roots.get(value)
                    if root is not None and root not in seen_roots:
                        seen_roots.add(root)
                        candidates.append(_ProducerCandidate(op, value, root, "init"))
                for value in _effect_values(op, MemoryEffectKind.WRITE):
                    root = _alias_root(value, alias_roots)
                    if root in seen_roots:
                        continue
                    seen_roots.add(root)
                    candidates.append(_ProducerCandidate(op, value, root, "write"))
            for candidate in candidates:
                if candidate.kind == "init":
                    init_value_roots = (
                        candidate.root,
                        *(root for root, init_root in init_alias_roots.items() if init_root is candidate.root),
                    )
                    init_root_values: set[SSAValue] = set()
                    for root in init_value_roots:
                        init_root_values.update(alias_groups.get(root, {root}))
                    init_edges_by_op: dict[Operation, _ConsumerEdge] = {}
                    for value in init_root_values:
                        for use in tuple(value.uses):
                            consumer_op = use.operation
                            if not any(
                                root in touch_roots.get(consumer_op, set()) for root in init_value_roots
                            ):
                                continue
                            relation = _classify_edge(candidate.op, consumer_op)
                            if relation is None:
                                continue
                            if consumer_op not in init_edges_by_op:
                                init_edges_by_op[consumer_op] = _ConsumerEdge(consumer_op, relation)
                    sorted_init_edges = tuple(
                        sorted(init_edges_by_op.values(), key=lambda edge: op_order.get(edge.consumer_op, 0))
                    )
                    ordered_groups = sorted(
                        _group_consumer_edges(sorted_init_edges),
                        key=lambda group: min(op_order.get(edge.consumer_op, 0) for edge in group),
                    )[:1]
                else:
                    edges = _collect_consumer_edges(candidate, alias_groups, read_roots, op_order)
                    ordered_groups = sorted(
                        _group_consumer_edges(edges),
                        key=lambda group: min(op_order.get(edge.consumer_op, 0) for edge in group),
                    )
                for group in ordered_groups:
                    event_id = next_event_id
                    next_event_id += 1
                    producer_attr, consumer_attr = _relation_attr_names(group[0].relation)
                    _append_event(event_attrs, candidate.op, producer_attr, event_id)
                    for edge in group:
                        _append_event(event_attrs, edge.consumer_op, consumer_attr, event_id)
            next_event_id = _RingAwareAnalysis.add_ring_events(ops, alias_roots, event_attrs, next_event_id)
            _ = next_event_id
            _apply_event_attrs(ops, event_attrs)


__all__ = ["ProducerConsumerAnalysisPass"]
