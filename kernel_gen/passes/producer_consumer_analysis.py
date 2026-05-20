"""producer-consumer-analysis pass.


功能说明:
- 提供 `producer-consumer-analysis` pass，基于公开 `MemoryEffect` 标注生产 / 消费 event。
- 使用当前文件内 alias 规则处理 `dma.view`、`dma.reshape`、`dma.subview` 与 `dma.deslice`。
- 只写 `productor` / `consumer` 与控制流分类 event attr，不生成 wait/sign 或 runtime 同步 op。

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
from kernel_gen.dialect.dma import DmaDesliceOp, DmaReshapeOp, DmaSubviewOp, DmaViewOp
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
    - 记录 `ALLOC/WRITE` effect 产生的 memory value。
    - 每个 candidate 独立遍历 downstream meaningful consumer。

    使用示例:
    - candidate = _ProducerCandidate(op, value, root)
    """

    op: Operation
    value: SSAValue
    root: SSAValue


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
    - `dma.view/reshape/subview` 的 result alias source。
    - `dma.deslice` 的 result alias target。

    使用示例:
    - alias_roots = _build_alias_roots(ops)
    """

    alias_roots: dict[SSAValue, SSAValue] = {}

    for op in ops:
        if isinstance(op, (DmaViewOp, DmaReshapeOp, DmaSubviewOp)):
            alias_roots[SSAValue.get(op.result)] = _alias_root(SSAValue.get(op.source), alias_roots)
        elif isinstance(op, DmaDesliceOp):
            alias_roots[SSAValue.get(op.result)] = _alias_root(SSAValue.get(op.target), alias_roots)
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


def _common_enclosing_control_op(producer_op: Operation, consumer_op: Operation) -> _ControlOp | None:
    """返回 producer/consumer 最近共同控制流父 op。

    功能说明:
    - 同一 `symbol.for` body 内的普通 edge 应标为 `loop_body_*`。
    - 同一 `scf.if` branch 内的普通 edge 应标为 `if_branch_*`。

    使用示例:
    - control = _common_enclosing_control_op(producer_op, consumer_op)
    """

    producer_controls: list[_ControlOp] = []
    parent = producer_op.parent_op()
    while parent is not None:
        if isinstance(parent, (SymbolForOp, scf.IfOp)):
            producer_controls.append(parent)
        parent = parent.parent_op()
    parent = consumer_op.parent_op()
    while parent is not None:
        if isinstance(parent, (SymbolForOp, scf.IfOp)) and parent in producer_controls:
            return parent
        parent = parent.parent_op()
    return None


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
        common_control = _common_enclosing_control_op(producer_op, consumer_op)
        if isinstance(common_control, SymbolForOp):
            return _EdgeRelation("loop_body", common_control, False)
        if isinstance(common_control, scf.IfOp):
            return _EdgeRelation("if_branch", common_control, False)
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


def _producer_candidates(
    ops: tuple[Operation, ...],
    alias_roots: dict[SSAValue, SSAValue],
) -> tuple[_ProducerCandidate, ...]:
    """收集 ALLOC / WRITE producer candidates。

    功能说明:
    - `ALLOC` 与 `WRITE` 都作为 producer value 起点。
    - 后续只有找到 downstream consumer 时才写 `productor`。

    使用示例:
    - candidates = _producer_candidates(ops, alias_roots)
    """

    candidates: list[_ProducerCandidate] = []
    for op in ops:
        values = [
            *_effect_values(op, MemoryEffectKind.ALLOC),
            *_effect_values(op, MemoryEffectKind.WRITE),
        ]
        seen_roots: set[SSAValue] = set()
        for value in values:
            root = _alias_root(value, alias_roots)
            if root in seen_roots:
                continue
            seen_roots.add(root)
            candidates.append(_ProducerCandidate(op, value, root))
    return tuple(candidates)


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


def _relation_attr_names(relation: _EdgeRelation) -> tuple[str | None, str | None]:
    """返回 relation 对应的 productor/consumer 分类 attr 名。

    功能说明:
    - 分类 attr 只补充 event 分类，不替代主 `productor` / `consumer`。

    使用示例:
    - producer_attr, consumer_attr = _relation_attr_names(edge.relation)
    """

    if relation.kind is None:
        return None, None
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


class ProducerConsumerAnalysisPass(Pass):
    """生产消费分析 pass。

    功能说明:
    - 固定公开 pass name 为 `producer-consumer-analysis`。
    - 基于公开 `MemoryEffect` 与当前文件内 alias 规则标注 producer/consumer event。
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

    def __init__(self: "ProducerConsumerAnalysisPass", fold: bool = True) -> None:
        """初始化 pass。

        功能说明:
        - 只记录通用 `fold` 开关。
        - 不提供 attr name、alias table 或 control-flow 策略自定义入口。

        使用示例:
        - pass_obj = ProducerConsumerAnalysisPass(fold=False)
        """

        super().__init__(fold=fold)

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

    def _apply_to_func(self: "ProducerConsumerAnalysisPass", func_op: func.FuncOp) -> None:
        """分析单个函数。

        功能说明:
        - 每个 `func.func` 内 event id 从 0 开始分配。
        - 先清理旧 event attrs，再根据当前 IR 重新标注。

        使用示例:
        - pass_obj._apply_to_func(func_op)
        """

        ops = _walk_func_ops(func_op)
        for op in ops:
            _clear_event_attrs(op)
        alias_roots = _build_alias_roots(ops)
        alias_groups = _build_alias_groups(ops, alias_roots)
        read_roots = _read_roots_by_op(ops, alias_roots)
        op_order = {op: index for index, op in enumerate(ops)}
        event_attrs: dict[Operation, dict[str, list[int]]] = defaultdict(lambda: defaultdict(list))
        next_event_id = 0
        for candidate in _producer_candidates(ops, alias_roots):
            edges = _collect_consumer_edges(candidate, alias_groups, read_roots, op_order)
            ordered_groups = sorted(
                _group_consumer_edges(edges),
                key=lambda group: min(op_order.get(edge.consumer_op, 0) for edge in group),
            )
            for group in ordered_groups:
                event_id = next_event_id
                next_event_id += 1
                _append_event(event_attrs, candidate.op, "productor", event_id)
                for edge in group:
                    _append_event(event_attrs, edge.consumer_op, "consumer", event_id)
                    producer_attr, consumer_attr = _relation_attr_names(edge.relation)
                    if producer_attr is not None and consumer_attr is not None:
                        _append_event(event_attrs, candidate.op, producer_attr, event_id)
                        _append_event(event_attrs, edge.consumer_op, consumer_attr, event_id)
        _apply_event_attrs(ops, event_attrs)

    def apply(self: "ProducerConsumerAnalysisPass", ctx: Context, module: ModuleOp) -> None:
        """执行生产消费分析。

        功能说明:
        - 校验输入为 `builtin.module`。
        - 对每个非声明 `func.func` 分别标注 producer/consumer event。

        使用示例:
        - ProducerConsumerAnalysisPass().apply(Context(), module)
        """

        _ = ctx
        target = ensure_builtin_module(module)
        for op in target.ops:
            if isinstance(op, func.FuncOp) and not op.is_declaration:
                self._apply_to_func(op)


__all__ = ["ProducerConsumerAnalysisPass"]
