"""loop-soft-pipeline pass.


功能说明:
- 提供 `loop-soft-pipeline` pass，在可证明的 ring-backed matmul preload loop 上生成
  prologue / steady loop / epilogue 软流水结构。
- 当前阶段只改写单个 `symbol.for` 中两个 `dma.copy` 生产 `kernel.matmul` 的 A/B operand，
  且 matmul 后存在 ring cursor advance 的局部形态；不支持的 IR 与静态 zero-trip loop 保持 no-op。
- 静态 single-tile loop 退化为 prologue preload 与 epilogue matmul；无法静态证明正 trip
  的动态边界保持 no-op，避免生成无保护 prologue。
- 改写时清理旧 producer/consumer event attrs，后续由 `producer-consumer-analysis` 重新标注。

API 列表:
- `class LoopSoftPipelinePass(fold: bool = True)`
- `LoopSoftPipelinePass.from_options(options: dict[str, str]) -> LoopSoftPipelinePass`
- `LoopSoftPipelinePass.apply(ctx: Context, module: ModuleOp) -> None`

使用示例:
- from kernel_gen.passes.schedule.loop_soft_pipeline import LoopSoftPipelinePass
- LoopSoftPipelinePass().apply(Context(), module)
- LoopSoftPipelinePass.from_options({})

关联文件:
- spec: spec/pass/loop_soft_pipeline.md
- spec: spec/pass/pipeline/npu_demo_lowering.md
- test: test/passes/schedule/test_loop_soft_pipeline.py
- 功能实现: kernel_gen/passes/schedule/loop_soft_pipeline.py
"""

from __future__ import annotations

from dataclasses import dataclass

from xdsl.context import Context
from xdsl.dialects import func
from xdsl.dialects.builtin import ArrayAttr, ModuleOp
from xdsl.ir import Block, Operation, SSAValue
from xdsl.traits import MemoryEffectKind, get_effects

from kernel_gen.core.error import ErrorKind, ErrorModule, KernelCodeError
from kernel_gen.dialect.dma import DmaAdvanceRingOp, DmaCopyOp, DmaCurrentRingOp, DmaReinterpretOp
from kernel_gen.dialect.kernel import KernelMatmulOp
from kernel_gen.dialect.nn import NnMemoryType
from kernel_gen.dialect.symbol import (
    SymbolAddOp,
    SymbolConstOp,
    SymbolDivOp,
    SymbolExprAttr,
    SymbolFloorDivOp,
    SymbolForOp,
    SymbolIterAttr,
    SymbolIterType,
    SymbolMaxOp,
    SymbolMinOp,
    SymbolMulOp,
    SymbolSubOp,
    SymbolValueType,
)
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
_SYMBOL_BINARY_OP_CLASSES = {
    "symbol.add": SymbolAddOp,
    "symbol.sub": SymbolSubOp,
    "symbol.mul": SymbolMulOp,
    "symbol.div": SymbolDivOp,
    "symbol.floordiv": SymbolFloorDivOp,
    "symbol.min": SymbolMinOp,
    "symbol.max": SymbolMaxOp,
}


@dataclass(frozen=True)
class _LoopSoftPipelineCandidate:
    """可改写的单 loop soft-pipeline 候选。

    功能说明:
    - 保存原 loop、loop body block 与按依赖闭包拆出的 matmul setup / preload ops。
    - `advance_ops` 覆盖 matmul 后的 ring cursor 推进，供 steady loop 在 preload next 前复用。
    - `trip_count` 是静态证明出的正 trip 数，用于区分 single-tile 退化与多 tile steady loop。

    使用示例:
    - candidate = _LoopSoftPipelineCandidate(...)
    """

    loop: SymbolForOp
    body_block: Block
    matmul_op: KernelMatmulOp
    matmul_setup_ops: tuple[Operation, ...]
    preload_ops: tuple[Operation, ...]
    advance_ops: tuple[DmaAdvanceRingOp, ...]
    trip_count: int


class _LoopSoftPipelineRewrite:
    """loop-soft-pipeline 当前文件内 rewrite 规则容器。

    功能说明:
    - 封装本 pass 的局部模式识别、依赖闭包拆分与 IR 克隆逻辑。
    - 方法名不以下划线开头，避免把当前文件内部复用误判为跨文件私有 API。

    使用示例:
    - changed = _LoopSoftPipelineRewrite.rewrite_func(func_op)
    """

    @staticmethod
    def symbol_expr(value: SSAValue) -> str | None:
        """读取 `!symbol.int` 或 `!symbol.iter` 的公开表达式文本。

        功能说明:
        - 从公开 symbol type 参数提取表达式，供新建 symbol arithmetic 与 iter attr 使用。
        - 不支持的 type 返回 None，由调用方保持 no-op。

        使用示例:
        - expr = _LoopSoftPipelineRewrite.symbol_expr(loop.end)
        """

        value_type = SSAValue.get(value).type
        if isinstance(value_type, SymbolValueType):
            return SymbolExprAttr.from_expr(value_type.expr.expr.data).expr.data
        if isinstance(value_type, SymbolIterType):
            start = SymbolExprAttr.from_expr(value_type.start.expr.data).expr.data
            end = SymbolExprAttr.from_expr(value_type.end.expr.data).expr.data
            step = SymbolExprAttr.from_expr(value_type.step.expr.data).expr.data
            return f"iter<{start},{end},{step}>"
        return None

    @staticmethod
    def binary_expr(op_name: str, lhs_expr: str, rhs_expr: str) -> str:
        """生成 symbol 二元表达式文本。

        功能说明:
        - 静态整数输入直接折叠，避免构造 `8 - 4` 这类可静态归约结果时触发 canonical 校验。
        - 动态输入通过 `SymbolExprAttr.from_expr(...)` 归一化为公开 symbol.expr 文本。

        使用示例:
        - expr = _LoopSoftPipelineRewrite.binary_expr("symbol.sub", "8", "4")
        """

        lhs_static = int(lhs_expr) if lhs_expr.lstrip("-").isdecimal() else None
        rhs_static = int(rhs_expr) if rhs_expr.lstrip("-").isdecimal() else None
        if lhs_static is not None and rhs_static is not None:
            if op_name == "symbol.add":
                return str(lhs_static + rhs_static)
            if op_name == "symbol.sub":
                return str(lhs_static - rhs_static)
            if op_name == "symbol.mul":
                return str(lhs_static * rhs_static)
            if op_name in {"symbol.div", "symbol.floordiv"} and rhs_static != 0:
                return str(lhs_static // rhs_static)
        if op_name == "symbol.mul":
            return SymbolExprAttr.from_expr(f"({lhs_expr}) * ({rhs_expr})").expr.data
        if op_name in {"symbol.div", "symbol.floordiv"}:
            return SymbolExprAttr.from_expr(f"({lhs_expr}) floordiv ({rhs_expr})").expr.data
        operator = "+" if op_name == "symbol.add" else "-"
        return SymbolExprAttr.from_expr(f"({lhs_expr}) {operator} ({rhs_expr})").expr.data

    @staticmethod
    def symbol_binary_op(op_name: str, lhs: SSAValue, rhs: SSAValue, result_expr: str) -> Operation:
        """构造 registered symbol binary op。

        功能说明:
        - 按已计算的 canonical 表达式生成公开 `symbol.add/sub` 等 registered op。
        - 使用 registered op 保证后续 dump 与 npu_demo EmitC 都能识别。

        使用示例:
        - op = _LoopSoftPipelineRewrite.symbol_binary_op("symbol.sub", end, step, "N - TILE")
        """

        op_cls = _SYMBOL_BINARY_OP_CLASSES[op_name]
        return op_cls(lhs, rhs, SymbolValueType.from_expr(result_expr))

    @staticmethod
    def registered_symbol_binary_expr(op_name: str, lhs: SSAValue, rhs: SSAValue) -> str | None:
        """根据已映射 operand 计算 registered symbol binary 结果类型表达。

        功能说明:
        - 用于克隆原 loop body 内依赖迭代变量的 registered symbol 算术 op。
        - 当 steady loop 的 iter type 被缩短时，重新推导 result type 以满足 symbol verifier。

        使用示例:
        - expr = _LoopSoftPipelineRewrite.registered_symbol_binary_expr("symbol.sub", lhs, rhs)
        """

        lhs_expr = _LoopSoftPipelineRewrite.symbol_expr(lhs)
        rhs_expr = _LoopSoftPipelineRewrite.symbol_expr(rhs)
        if lhs_expr is None or rhs_expr is None:
            return None
        if op_name in {"symbol.add", "symbol.sub"}:
            return _LoopSoftPipelineRewrite.binary_expr(op_name, lhs_expr, rhs_expr)
        if op_name == "symbol.mul":
            return SymbolExprAttr.from_expr(f"({lhs_expr}) * ({rhs_expr})").expr.data
        if op_name in {"symbol.div", "symbol.floordiv"}:
            return SymbolExprAttr.from_expr(f"({lhs_expr}) floordiv ({rhs_expr})").expr.data
        if op_name == "symbol.min":
            return SymbolExprAttr.from_expr(f"min({lhs_expr}, {rhs_expr})").expr.data
        if op_name == "symbol.max":
            return SymbolExprAttr.from_expr(f"max({lhs_expr}, {rhs_expr})").expr.data
        return None

    @staticmethod
    def clone_registered_symbol_binary(
        op: Operation,
        value_mapper: dict[SSAValue, SSAValue],
    ) -> Operation | None:
        """克隆 registered symbol binary op 并重算 result type。

        功能说明:
        - 对 `symbol.add/sub/min/...` 的两个 operand 应用当前 value mapper。
        - 重新构造对应 op 并更新 value mapper 中的 result 映射。

        使用示例:
        - cloned = _LoopSoftPipelineRewrite.clone_registered_symbol_binary(op, mapper)
        """

        op_cls = _SYMBOL_BINARY_OP_CLASSES.get(op.name)
        if op_cls is None or len(op.operands) != 2 or len(op.results) != 1:
            return None
        lhs = value_mapper.get(SSAValue.get(op.operands[0]), SSAValue.get(op.operands[0]))
        rhs = value_mapper.get(SSAValue.get(op.operands[1]), SSAValue.get(op.operands[1]))
        result_expr = _LoopSoftPipelineRewrite.registered_symbol_binary_expr(op.name, lhs, rhs)
        if result_expr is None:
            return None
        cloned_op = op_cls(lhs, rhs, SymbolValueType.from_expr(result_expr))
        value_mapper[SSAValue.get(op.results[0])] = SSAValue.get(cloned_op.results[0])
        return cloned_op

    @staticmethod
    def memory_type_from_symbol_operands(
        base_type: NnMemoryType,
        shape_values: tuple[SSAValue, ...],
        stride_values: tuple[SSAValue, ...],
    ) -> NnMemoryType | None:
        """按已映射 shape/stride operands 重建 `!nn.memory` 类型。

        功能说明:
        - 克隆 `dma.reinterpret` 后 shape/stride operand 可能随 steady loop iter type 改变。
        - 结果类型必须同步更新，否则 dialect verifier 会认为 operand 与 result layout 不一致。

        使用示例:
        - result_type = _LoopSoftPipelineRewrite.memory_type_from_symbol_operands(old_type, shape, stride)
        """

        if not all(isinstance(value.type, SymbolValueType) for value in (*shape_values, *stride_values)):
            return None
        shape = ArrayAttr([SymbolExprAttr.from_expr(value.type.expr.expr.data) for value in shape_values])
        stride = ArrayAttr([SymbolExprAttr.from_expr(value.type.expr.expr.data) for value in stride_values])
        return NnMemoryType(shape, stride, base_type.element_type, base_type.space)

    @staticmethod
    def clone_dma_reinterpret(
        op: Operation,
        value_mapper: dict[SSAValue, SSAValue],
    ) -> Operation | None:
        """克隆 `dma.reinterpret` 并重建 result memory type。

        功能说明:
        - 对 source/offset/shape/stride 应用当前 value mapper。
        - 当 shape/stride 来自被重算的 symbol op 时，同步更新 result type。

        使用示例:
        - cloned = _LoopSoftPipelineRewrite.clone_dma_reinterpret(op, mapper)
        """

        if not isinstance(op, DmaReinterpretOp):
            return None
        base_type = op.result.type
        if not isinstance(base_type, NnMemoryType):
            return None
        source = value_mapper.get(SSAValue.get(op.source), SSAValue.get(op.source))
        offset = value_mapper.get(SSAValue.get(op.offset), SSAValue.get(op.offset))
        shape = tuple(value_mapper.get(SSAValue.get(value), SSAValue.get(value)) for value in op.shape)
        stride = tuple(value_mapper.get(SSAValue.get(value), SSAValue.get(value)) for value in op.stride)
        result_type = _LoopSoftPipelineRewrite.memory_type_from_symbol_operands(base_type, shape, stride)
        if result_type is None:
            return None
        cloned_op = DmaReinterpretOp(source, offset, shape, stride, result_type)
        value_mapper[SSAValue.get(op.result)] = SSAValue.get(cloned_op.result)
        return cloned_op

    @staticmethod
    def static_int(value: SSAValue) -> int | None:
        """读取静态 symbol 整数。

        功能说明:
        - 仅当 operand type 是字面整数 `!symbol.int<#symbol.expr<N>>` 时返回 int。
        - 动态表达式返回 None，供调用方保守处理。

        使用示例:
        - maybe_step = _LoopSoftPipelineRewrite.static_int(loop.step)
        """

        expr = _LoopSoftPipelineRewrite.symbol_expr(value)
        if expr is None or not expr.lstrip("-").isdecimal():
            return None
        return int(expr)

    @staticmethod
    def static_trip_count(loop: SymbolForOp) -> int | None:
        """计算静态可证明的正向 trip count。

        功能说明:
        - 仅在 start/end/step 都是静态整数时返回 trip count。
        - 静态 zero-trip、负步长或零步长返回 0，调用方保持 no-op。
        - 动态边界返回 None，首版不构造 guard，避免生成无保护 prologue。

        使用示例:
        - trip_count = _LoopSoftPipelineRewrite.static_trip_count(loop)
        """

        start = _LoopSoftPipelineRewrite.static_int(SSAValue.get(loop.start))
        end = _LoopSoftPipelineRewrite.static_int(SSAValue.get(loop.end))
        step = _LoopSoftPipelineRewrite.static_int(SSAValue.get(loop.step))
        if start is None or end is None or step is None:
            return None
        if step <= 0 or end <= start:
            return 0
        return (end - start + step - 1) // step

    @staticmethod
    def ring_for_memory(value: SSAValue) -> SSAValue | None:
        """返回 memory value 来源的 ring operand。

        功能说明:
        - 识别 `dma.current_ring` 结果及其 `dma.reinterpret` alias 链。
        - 非 ring-backed memory 返回 None，使 unsupported 结构保持 no-op。

        使用示例:
        - ring = _LoopSoftPipelineRewrite.ring_for_memory(copy.target)
        """

        owner = SSAValue.get(value).owner
        if isinstance(owner, DmaCurrentRingOp):
            return SSAValue.get(owner.ring)
        if isinstance(owner, DmaReinterpretOp):
            return _LoopSoftPipelineRewrite.ring_for_memory(SSAValue.get(owner.source))
        return None

    @staticmethod
    def effect_values(op: Operation, kind: MemoryEffectKind) -> tuple[SSAValue, ...]:
        """读取 op 的公开 memory effect value。

        功能说明:
        - 只使用 xDSL 公开 `get_effects(op)` 入口。
        - 忽略无 value 或非 `!nn.memory` 的 effect。

        使用示例:
        - writes = _LoopSoftPipelineRewrite.effect_values(op, MemoryEffectKind.WRITE)
        """

        effects = get_effects(op)
        if not effects:
            return ()
        values: list[SSAValue] = []
        for effect in effects:
            if effect.kind != kind or not isinstance(effect.value, SSAValue):
                continue
            value = SSAValue.get(effect.value)
            if isinstance(value.type, NnMemoryType):
                values.append(value)
        return tuple(values)

    @staticmethod
    def copy_source_write_ops(
        copy_ops: tuple[DmaCopyOp, ...],
        op_pool: tuple[Operation, ...],
    ) -> tuple[Operation, ...]:
        """收集写入 copy source 的 preload side-effect op。

        功能说明:
        - `dma.deslice` 等 writer 通过 side effect 写入 copy source，不会出现在 SSA result 依赖闭包中。
        - 将这类 writer 作为 preload seed，保证 prologue 与 next preload 都刷新 staging source。

        使用示例:
        - writers = _LoopSoftPipelineRewrite.copy_source_write_ops(copy_ops, body_ops)
        """

        copy_sources = {SSAValue.get(copy_op.source) for copy_op in copy_ops}
        writer_ops: list[Operation] = []
        for op in op_pool:
            written_values = _LoopSoftPipelineRewrite.effect_values(op, MemoryEffectKind.WRITE)
            if any(value in copy_sources for value in written_values):
                writer_ops.append(op)
        return tuple(writer_ops)

    @staticmethod
    def dependency_ops(
        seed_ops: tuple[Operation, ...],
        op_pool: tuple[Operation, ...],
        *,
        include_seed_ops: bool,
    ) -> tuple[Operation, ...]:
        """按 SSA 依赖闭包收集需要克隆的 op。

        功能说明:
        - 从 seed op 的 operands 反向追踪同一 loop body 内的 result producer。
        - `include_seed_ops=True` 时把 seed op 本身也纳入结果，用于 preload copy 段。

        使用示例:
        - setup = _LoopSoftPipelineRewrite.dependency_ops((matmul,), body_ops, include_seed_ops=False)
        """

        required_values: set[SSAValue] = set()
        included_ops: set[Operation] = set(seed_ops) if include_seed_ops else set()
        for seed_op in seed_ops:
            for operand in seed_op.operands:
                required_values.add(SSAValue.get(operand))
        changed = True
        while changed:
            changed = False
            for op in reversed(op_pool):
                produced_values = {SSAValue.get(result) for result in op.results}
                if op not in seed_ops and not produced_values.intersection(required_values):
                    continue
                if op in included_ops and produced_values.issubset(required_values):
                    continue
                included_ops.add(op)
                for operand in op.operands:
                    value = SSAValue.get(operand)
                    if value not in required_values:
                        required_values.add(value)
                        changed = True
        return tuple(op for op in op_pool if op in included_ops)

    @staticmethod
    def find_candidate(loop: SymbolForOp) -> _LoopSoftPipelineCandidate | None:
        """识别单个 loop soft-pipeline 候选。

        功能说明:
        - 要求 loop body 单块、无 loop-carried result、只有一个 `kernel.matmul`。
        - 要求 matmul 的 lhs/rhs 分别由 matmul 前两个 ring-backed `dma.copy` target 生产。
        - 只接受可静态证明正 trip 的 loop；动态未知 trip 保持 no-op。

        使用示例:
        - candidate = _LoopSoftPipelineRewrite.find_candidate(symbol_for)
        """

        trip_count = _LoopSoftPipelineRewrite.static_trip_count(loop)
        if trip_count is None or trip_count == 0:
            return None
        blocks = tuple(loop.body.blocks)
        if len(blocks) != 1 or loop.result is not None or loop.init is not None:
            return None
        body_block = blocks[0]
        if len(body_block.args) != 1:
            return None
        body_ops = tuple(body_block.ops)
        matmul_ops = tuple(op for op in body_ops if isinstance(op, KernelMatmulOp))
        if len(matmul_ops) != 1:
            return None
        matmul_op = matmul_ops[0]
        matmul_index = body_ops.index(matmul_op)
        lhs = SSAValue.get(matmul_op.lhs)
        rhs = SSAValue.get(matmul_op.rhs)
        copy_ops = tuple(
            op
            for op in body_ops[:matmul_index]
            if isinstance(op, DmaCopyOp) and SSAValue.get(op.target) in {lhs, rhs}
        )
        if len(copy_ops) != 2 or {SSAValue.get(op.target) for op in copy_ops} != {lhs, rhs}:
            return None
        target_rings = tuple(_LoopSoftPipelineRewrite.ring_for_memory(SSAValue.get(op.target)) for op in copy_ops)
        if any(ring is None for ring in target_rings):
            return None
        target_ring_set = {ring for ring in target_rings if ring is not None}
        advance_ops = tuple(op for op in body_ops[matmul_index + 1 :] if isinstance(op, DmaAdvanceRingOp))
        advanced_rings = {SSAValue.get(op.ring) for op in advance_ops}
        if not target_ring_set.issubset(advanced_rings):
            return None
        matmul_setup_ops = _LoopSoftPipelineRewrite.dependency_ops((matmul_op,), body_ops[:matmul_index], include_seed_ops=False)
        copy_source_writes = _LoopSoftPipelineRewrite.copy_source_write_ops(copy_ops, body_ops[:matmul_index])
        preload_seeds = (*copy_source_writes, *copy_ops)
        preload_ops = _LoopSoftPipelineRewrite.dependency_ops(preload_seeds, body_ops[:matmul_index], include_seed_ops=True)
        if not matmul_setup_ops or len(preload_ops) <= len(copy_ops):
            return None
        return _LoopSoftPipelineCandidate(
            loop=loop,
            body_block=body_block,
            matmul_op=matmul_op,
            matmul_setup_ops=matmul_setup_ops,
            preload_ops=preload_ops,
            advance_ops=advance_ops,
            trip_count=trip_count,
        )

    @staticmethod
    def clear_event_attrs(op: Operation) -> None:
        """清理克隆 op 中的旧 producer/consumer attrs。

        功能说明:
        - 删除当前 pass 会失效的 producer/consumer 标注，包含新增 ring-aware 分类。
        - 递归处理嵌套 region，避免旧 attr 泄漏到改写后的 IR。

        使用示例:
        - _LoopSoftPipelineRewrite.clear_event_attrs(cloned_op)
        """

        for attr_name in _EVENT_ATTR_NAMES:
            op.attributes.pop(attr_name, None)
        for region in op.regions:
            for block in region.blocks:
                for child in block.ops:
                    _LoopSoftPipelineRewrite.clear_event_attrs(child)

    @staticmethod
    def clone_ops(
        ops: tuple[Operation, ...],
        value_mapper: dict[SSAValue, SSAValue],
    ) -> list[Operation]:
        """按给定 value mapper 克隆 op 序列。

        功能说明:
        - 复用 xDSL `Operation.clone` 的公开 value mapping。
        - 克隆后立即清理旧 event attrs，避免 producer-consumer 标注跨结构改写复用。

        使用示例:
        - cloned = _LoopSoftPipelineRewrite.clone_ops(candidate.preload_ops, mapper)
        """

        cloned_ops: list[Operation] = []
        for op in ops:
            cloned_op = _LoopSoftPipelineRewrite.clone_registered_symbol_binary(op, value_mapper)
            if cloned_op is None:
                cloned_op = _LoopSoftPipelineRewrite.clone_dma_reinterpret(op, value_mapper)
            if cloned_op is None:
                cloned_op = op.clone(value_mapper=value_mapper)
            _LoopSoftPipelineRewrite.clear_event_attrs(cloned_op)
            cloned_ops.append(cloned_op)
        return cloned_ops

    @staticmethod
    def build_steady_boundary(loop: SymbolForOp) -> tuple[tuple[Operation, ...], SSAValue, SymbolIterAttr] | None:
        """构造 steady loop 的最后迭代起点边界。

        功能说明:
        - 计算 `start + ((end - start - 1) floordiv step) * step` 作为 epilogue 迭代值。
        - steady loop 使用该值作为 exclusive end，避免动态 tail 时把 `end - step` 当作非法迭代点。
        - 无法读取 symbol 表达式时返回 None，调用方保持 no-op。

        使用示例:
        - boundary = _LoopSoftPipelineRewrite.build_steady_boundary(loop)
        """

        start_expr = _LoopSoftPipelineRewrite.symbol_expr(SSAValue.get(loop.start))
        end_expr = _LoopSoftPipelineRewrite.symbol_expr(SSAValue.get(loop.end))
        step_expr = _LoopSoftPipelineRewrite.symbol_expr(SSAValue.get(loop.step))
        if start_expr is None or end_expr is None or step_expr is None:
            return None
        one_op = SymbolConstOp(1)
        distance_expr = _LoopSoftPipelineRewrite.binary_expr("symbol.sub", end_expr, start_expr)
        distance_op = _LoopSoftPipelineRewrite.symbol_binary_op(
            "symbol.sub",
            SSAValue.get(loop.end),
            SSAValue.get(loop.start),
            distance_expr,
        )
        tail_distance_expr = _LoopSoftPipelineRewrite.binary_expr("symbol.sub", distance_expr, "1")
        tail_distance_op = _LoopSoftPipelineRewrite.symbol_binary_op(
            "symbol.sub",
            SSAValue.get(distance_op.results[0]),
            SSAValue.get(one_op.result),
            tail_distance_expr,
        )
        quotient_expr = _LoopSoftPipelineRewrite.binary_expr("symbol.floordiv", tail_distance_expr, step_expr)
        quotient_op = _LoopSoftPipelineRewrite.symbol_binary_op(
            "symbol.floordiv",
            SSAValue.get(tail_distance_op.results[0]),
            SSAValue.get(loop.step),
            quotient_expr,
        )
        offset_expr = _LoopSoftPipelineRewrite.binary_expr("symbol.mul", quotient_expr, step_expr)
        offset_op = _LoopSoftPipelineRewrite.symbol_binary_op(
            "symbol.mul",
            SSAValue.get(quotient_op.results[0]),
            SSAValue.get(loop.step),
            offset_expr,
        )
        last_iter_expr = _LoopSoftPipelineRewrite.binary_expr("symbol.add", start_expr, offset_expr)
        last_iter_op = _LoopSoftPipelineRewrite.symbol_binary_op(
            "symbol.add",
            SSAValue.get(loop.start),
            SSAValue.get(offset_op.results[0]),
            last_iter_expr,
        )
        iter_attr = SymbolIterAttr.from_bounds(start_expr, last_iter_expr, step_expr)
        boundary_ops = (one_op, distance_op, tail_distance_op, quotient_op, offset_op, last_iter_op)
        return boundary_ops, SSAValue.get(last_iter_op.results[0]), iter_attr

    @staticmethod
    def build_next_iter(iter_value: SSAValue, step_value: SSAValue) -> Operation | None:
        """构造 preload next 使用的 `it + step` symbol 值。

        功能说明:
        - steady loop 每轮先计算当前 tile，再 advance cursor 并 preload 下一 tile。
        - 如果无法形成公开 symbol 表达式，返回 None 并保持原 loop no-op。

        使用示例:
        - next_iter = _LoopSoftPipelineRewrite.build_next_iter(new_block.args[0], loop.step)
        """

        iter_expr = _LoopSoftPipelineRewrite.symbol_expr(iter_value)
        step_expr = _LoopSoftPipelineRewrite.symbol_expr(step_value)
        if iter_expr is None or step_expr is None:
            return None
        result_expr = _LoopSoftPipelineRewrite.binary_expr("symbol.add", iter_expr, step_expr)
        return _LoopSoftPipelineRewrite.symbol_binary_op("symbol.add", iter_value, step_value, result_expr)

    @staticmethod
    def rewrite_candidate(candidate: _LoopSoftPipelineCandidate) -> bool:
        """把候选 loop 改写为 prologue / steady / epilogue。

        功能说明:
        - prologue 在原 loop 前 preload 第一 tile。
        - single-tile 候选直接退化为 prologue preload 与 epilogue matmul。
        - steady loop 运行到最后一个有效迭代起点之前，每轮计算当前 tile、advance ring cursor、preload 下一 tile。
        - epilogue 在 loop 后计算最后一个已 preload tile。

        使用示例:
        - changed = _LoopSoftPipelineRewrite.rewrite_candidate(candidate)
        """

        loop = candidate.loop
        parent_block = loop.parent_block()
        if parent_block is None:
            return False
        old_iter = candidate.body_block.args[0]
        prologue_mapper = {SSAValue.get(old_iter): SSAValue.get(loop.start)}
        prologue_ops = _LoopSoftPipelineRewrite.clone_ops(candidate.preload_ops, prologue_mapper)
        if candidate.trip_count == 1:
            epilogue_mapper = {SSAValue.get(old_iter): SSAValue.get(loop.start)}
            epilogue_ops = _LoopSoftPipelineRewrite.clone_ops(candidate.matmul_setup_ops, epilogue_mapper)
            epilogue_ops.extend(_LoopSoftPipelineRewrite.clone_ops((candidate.matmul_op,), epilogue_mapper))
            parent_block.insert_ops_before([*prologue_ops, *epilogue_ops], loop)
            parent_block.erase_op(loop)
            return True
        boundary = _LoopSoftPipelineRewrite.build_steady_boundary(loop)
        if boundary is None:
            return False
        boundary_ops, last_iter_value, iter_attr = boundary
        steady_block = Block(arg_types=[SymbolIterType.from_attr(iter_attr)])
        steady_iter = steady_block.args[0]
        current_mapper = {SSAValue.get(old_iter): SSAValue.get(steady_iter)}
        for op in _LoopSoftPipelineRewrite.clone_ops(candidate.matmul_setup_ops, current_mapper):
            steady_block.add_op(op)
        for op in _LoopSoftPipelineRewrite.clone_ops((candidate.matmul_op,), current_mapper):
            steady_block.add_op(op)
        for op in _LoopSoftPipelineRewrite.clone_ops(candidate.advance_ops, current_mapper):
            steady_block.add_op(op)
        next_iter_op = _LoopSoftPipelineRewrite.build_next_iter(
            SSAValue.get(steady_iter),
            SSAValue.get(loop.step),
        )
        if next_iter_op is None:
            return False
        _LoopSoftPipelineRewrite.clear_event_attrs(next_iter_op)
        steady_block.add_op(next_iter_op)
        preload_mapper = {SSAValue.get(old_iter): SSAValue.get(next_iter_op.results[0])}
        for op in _LoopSoftPipelineRewrite.clone_ops(candidate.preload_ops, preload_mapper):
            steady_block.add_op(op)
        steady_loop = SymbolForOp(
            SSAValue.get(loop.start),
            last_iter_value,
            SSAValue.get(loop.step),
            steady_block,
            iter_attr=iter_attr,
        )
        epilogue_mapper = {SSAValue.get(old_iter): last_iter_value}
        epilogue_ops = _LoopSoftPipelineRewrite.clone_ops(candidate.matmul_setup_ops, epilogue_mapper)
        epilogue_ops.extend(_LoopSoftPipelineRewrite.clone_ops((candidate.matmul_op,), epilogue_mapper))
        parent_block.insert_ops_before([*prologue_ops, *boundary_ops, steady_loop], loop)
        parent_block.insert_ops_after(epilogue_ops, steady_loop)
        parent_block.erase_op(loop)
        return True

    @staticmethod
    def rewrite_func(func_op: func.FuncOp) -> bool:
        """改写函数内所有可证明 loop-soft-pipeline 候选。

        功能说明:
        - 先收集候选再改写，避免遍历过程中修改 block 影响待处理 op 列表。
        - 不支持或不匹配的函数保持 no-op。

        使用示例:
        - changed = _LoopSoftPipelineRewrite.rewrite_func(func_op)
        """

        if func_op.is_declaration:
            return False
        candidates: list[_LoopSoftPipelineCandidate] = []
        for op in tuple(func_op.walk()):
            if not isinstance(op, SymbolForOp):
                continue
            candidate = _LoopSoftPipelineRewrite.find_candidate(op)
            if candidate is not None:
                candidates.append(candidate)
        changed = False
        for candidate in candidates:
            changed = _LoopSoftPipelineRewrite.rewrite_candidate(candidate) or changed
        return changed


@dataclass(frozen=True)
class LoopSoftPipelinePass(Pass):
    """loop-soft-pipeline pass。

    功能说明:
    - 固定公开 pass name 为 `loop-soft-pipeline`。
    - 针对 ring-backed matmul preload loop 执行 prologue / steady / epilogue 改写。
    - single-tile loop 退化为 prologue / epilogue；动态未知 trip 保持 no-op。
    - 第一阶段不接受 pass 专属 options。

    使用示例:
    - LoopSoftPipelinePass().apply(Context(), module)
    - LoopSoftPipelinePass.from_options({})

    关联文件:
    - spec: spec/pass/loop_soft_pipeline.md
    - test: test/passes/schedule/test_loop_soft_pipeline.py
    - 功能实现: kernel_gen/passes/schedule/loop_soft_pipeline.py
    """

    name = "loop-soft-pipeline"
    fold: bool = True

    def __init__(self: "LoopSoftPipelinePass", fold: bool = True) -> None:
        """初始化 pass。

        功能说明:
        - 只记录通用 `fold` 开关。
        - 不提供模式选择、标注策略或 ring cursor 公开分析入口。

        使用示例:
        - pass_obj = LoopSoftPipelinePass(fold=False)
        """

        object.__setattr__(self, "fold", bool(fold))

    @classmethod
    def from_options(
        cls: type["LoopSoftPipelinePass"],
        options: dict[str, str],
    ) -> "LoopSoftPipelinePass":
        """从 registry pass 专属 options 构造 pass。

        功能说明:
        - 当前阶段只接受空 pass 专属 options。
        - 通用 `fold` 由 registry 先拆分，不在本入口兼容。

        使用示例:
        - pass_obj = LoopSoftPipelinePass.from_options({})
        """

        if options:
            unknown = ", ".join(sorted(options))
            raise KernelCodeError(ErrorKind.CONTRACT, ErrorModule.PASS, f"unknown option: {unknown}")
        return cls()

    def apply(self: "LoopSoftPipelinePass", ctx: Context, module: ModuleOp) -> None:
        """执行 loop-soft-pipeline。

        功能说明:
        - 校验输入为 `builtin.module`。
        - 对每个非声明 `func.func` 尝试执行局部 soft-pipeline 改写。

        使用示例:
        - LoopSoftPipelinePass().apply(Context(), module)
        """

        _ = ctx
        target = ensure_builtin_module(module)
        for op in target.ops:
            if isinstance(op, func.FuncOp) and not op.is_declaration:
                _LoopSoftPipelineRewrite.rewrite_func(op)


__all__ = ["LoopSoftPipelinePass"]
