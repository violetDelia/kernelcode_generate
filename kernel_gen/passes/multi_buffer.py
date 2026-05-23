"""multi-buffer pass.


功能说明:
- 提供 `multi-buffer` pass，把可证明的 matmul lhs/rhs staging buffer 改写为 DMA ring。
- 只匹配同一 `symbol.for` 直接 body 内的 `dma.alloc + dma.copy + kernel.matmul + dma.free` 成对生命周期。
- 对不满足公开边界的 IR 保持 no-op，不引入宽泛 alias 或跨 region 推断。

API 列表:
- `class MultiBufferPass(memory_stage: int = 3, fold: bool = True)`
- `MultiBufferPass.from_options(options: dict[str, str]) -> MultiBufferPass`
- `MultiBufferPass.apply(ctx: Context, module: ModuleOp) -> None`

使用示例:
- from kernel_gen.passes.multi_buffer import MultiBufferPass
- MultiBufferPass(memory_stage=3).apply(Context(), module)

关联文件:
- spec: spec/pass/multi_buffer.md
- test: test/passes/test_multi_buffer.py
- 功能实现: kernel_gen/passes/multi_buffer.py
"""

from __future__ import annotations

from dataclasses import dataclass

from xdsl.context import Context
from xdsl.dialects.builtin import (
    ArrayAttr,
    BFloat16Type,
    Float16Type,
    Float32Type,
    Float64Type,
    IntegerType,
    ModuleOp,
    i8,
)
from xdsl.ir import Attribute, Block, Operation, SSAValue, Use

from kernel_gen.dialect.dma import (
    DmaAdvanceRingOp,
    DmaAllocOp,
    DmaCopyOp,
    DmaCurrentRingOp,
    DmaFreeOp,
    DmaMakeRingOp,
    DmaRingType,
)
from kernel_gen.core.error import ErrorKind, ErrorModule, KernelCodeError
from kernel_gen.dialect.kernel import KernelMatmulOp
from kernel_gen.dialect.nn import NnMemoryType
from kernel_gen.dialect.symbol import SymbolConstOp, SymbolExprAttr, SymbolForOp
from kernel_gen.passes.common import ensure_builtin_module, raise_pass_contract_error
from kernel_gen.passes.pass_manager import Pass


@dataclass(frozen=True)
class _StagingCandidate:
    """单个 matmul staging buffer 的 ring 化候选。"""

    alloc_op: DmaAllocOp
    copy_op: DmaCopyOp
    free_op: DmaFreeOp
    matmul_op: KernelMatmulOp
    operand_index: int
    slot_bytes: int
    offset_bytes: int
    backing_bytes: int


def _parse_memory_stage_option(value: str) -> int:
    """解析 `memory-stage` pass option。

    功能说明:
    - 将 registry 传入的字符串解析成正整数 stage 数。

    使用示例:
    - stage = _parse_memory_stage_option("3")

    关联文件:
    - spec: spec/pass/multi_buffer.md
    - test: test/passes/test_multi_buffer.py
    - 功能实现: kernel_gen/passes/multi_buffer.py
    """

    try:
        stage = int(value.strip())
    except ValueError as exc:
        raise KernelCodeError(
            ErrorKind.CONTRACT,
            ErrorModule.PASS,
            "MultiBufferOptionError: memory-stage must be integer",
        ) from exc
    if stage <= 0:
        raise_pass_contract_error("MultiBufferOptionError", "memory-stage must be positive")
    return stage


def _operation_block(op: Operation) -> Block | None:
    """返回 operation 所在 block。

    功能说明:
    - 收口 parent block 读取，便于候选生命周期判定复用。

    使用示例:
    - block = _operation_block(op)

    关联文件:
    - spec: spec/pass/multi_buffer.md
    - test: test/passes/test_multi_buffer.py
    - 功能实现: kernel_gen/passes/multi_buffer.py
    """

    return op.parent_block()


def _block_index_map(block: Block) -> dict[Operation, int]:
    """构造 block 内 operation 的线性顺序索引。

    功能说明:
    - 用于判定 alloc/copy/use/free 是否满足同一直接 body 内的生命周期顺序。

    使用示例:
    - indexes = _block_index_map(loop_block)

    关联文件:
    - spec: spec/pass/multi_buffer.md
    - test: test/passes/test_multi_buffer.py
    - 功能实现: kernel_gen/passes/multi_buffer.py
    """

    return {op: index for index, op in enumerate(block.ops)}


def _static_int_dim(dim: Attribute) -> int | None:
    """从公开 `SymbolExprAttr` 维度读取静态正整数。

    功能说明:
    - 仅接受十进制整数字面量；符号维、复合表达式与 `?` 返回 None。

    使用示例:
    - value = _static_int_dim(SymbolExprAttr.from_expr("16"))

    关联文件:
    - spec: spec/pass/multi_buffer.md
    - test: test/passes/test_multi_buffer.py
    - 功能实现: kernel_gen/passes/multi_buffer.py
    """

    if not isinstance(dim, SymbolExprAttr):
        return None
    text = dim.expr.data
    return int(text) if text.isdecimal() else None


def _element_size_bytes(element_type: Attribute) -> int | None:
    """返回公开 numeric dtype 的字节数。

    功能说明:
    - 支持当前 kernel/memory 链路中使用的整数和浮点 dtype。

    使用示例:
    - size = _element_size_bytes(i8)

    关联文件:
    - spec: spec/pass/multi_buffer.md
    - test: test/passes/test_multi_buffer.py
    - 功能实现: kernel_gen/passes/multi_buffer.py
    """

    if isinstance(element_type, IntegerType):
        width = int(element_type.width.data)
        if width in {1, 8}:
            return 1
        if width == 16:
            return 2
        if width == 32:
            return 4
        if width == 64:
            return 8
        return None
    if isinstance(element_type, (Float16Type, BFloat16Type)):
        return 2
    if isinstance(element_type, Float32Type):
        return 4
    if isinstance(element_type, Float64Type):
        return 8
    return None


def _static_memory_bytes(memory_type: NnMemoryType) -> int | None:
    """计算静态 `nn.memory` 的字节数。

    功能说明:
    - 所有 shape 维度和 element type 都静态可判定时返回字节数。
    - 动态 shape 或未承接 dtype 返回 None，调用方保持 no-op。

    使用示例:
    - slot_bytes = _static_memory_bytes(memory_type)

    关联文件:
    - spec: spec/pass/multi_buffer.md
    - test: test/passes/test_multi_buffer.py
    - 功能实现: kernel_gen/passes/multi_buffer.py
    """

    element_size = _element_size_bytes(memory_type.element_type)
    if element_size is None:
        return None
    numel = 1
    for dim in memory_type.shape.data:
        static_dim = _static_int_dim(dim)
        if static_dim is None or static_dim <= 0:
            return None
        numel *= static_dim
    return numel * element_size


def _ring_offset_bytes(slot_bytes: int) -> int:
    """计算单个 ring stage 的 byte offset。

    功能说明:
    - 当前 v1 只要求 `shape_bytes < offset`，使用 `slot_bytes + 1` 保持最小可验证间隔。

    使用示例:
    - offset = _ring_offset_bytes(slot_bytes)

    关联文件:
    - spec: spec/pass/multi_buffer.md
    - test: test/passes/test_multi_buffer.py
    - 功能实现: kernel_gen/passes/multi_buffer.py
    """

    return slot_bytes + 1


def _backing_memory_type(slot_type: NnMemoryType, backing_bytes: int) -> NnMemoryType:
    """构造 DMA ring backing memory 类型。

    功能说明:
    - 使用与 slot 相同的 memory space，类型固定为一维 `i8` byte pool。

    使用示例:
    - backing_type = _backing_memory_type(slot_type, 4096)

    关联文件:
    - spec: spec/pass/multi_buffer.md
    - test: test/passes/test_multi_buffer.py
    - 功能实现: kernel_gen/passes/multi_buffer.py
    """

    return NnMemoryType(
        ArrayAttr([SymbolExprAttr.from_expr(str(backing_bytes))]),
        ArrayAttr([SymbolExprAttr.from_expr("1")]),
        i8,
        slot_type.space,
    )


def _use_is_target_matmul_operand(use: Use, matmul: KernelMatmulOp, operand_index: int) -> bool:
    """判断 use 是否为目标 matmul operand。

    功能说明:
    - 仅将当前 matmul 的 lhs/rhs operand use 计入合法 compute use。

    使用示例:
    - if _use_is_target_matmul_operand(use, matmul, 1): ...

    关联文件:
    - spec: spec/pass/multi_buffer.md
    - test: test/passes/test_multi_buffer.py
    - 功能实现: kernel_gen/passes/multi_buffer.py
    """

    return use.operation is matmul and use.index == operand_index


def _collect_candidate_uses(
    value: SSAValue,
    matmul: KernelMatmulOp,
    operand_index: int,
    loop_block: Block,
) -> tuple[DmaCopyOp, DmaFreeOp] | None:
    """收集并校验 staging alloc 的 direct use 集合。

    功能说明:
    - 只接受同一 loop body 中的唯一 `dma.copy target`、目标 matmul operand 和唯一 `dma.free`。
    - 任何 alias、nested/sibling region、额外 data use 或多 free 都让整对候选保持 no-op。

    使用示例:
    - pair = _collect_candidate_uses(alloc.result, matmul, 1, loop_block)

    关联文件:
    - spec: spec/pass/multi_buffer.md
    - test: test/passes/test_multi_buffer.py
    - 功能实现: kernel_gen/passes/multi_buffer.py
    """

    copy_ops: list[DmaCopyOp] = []
    free_ops: list[DmaFreeOp] = []
    saw_matmul_use = False
    for use in tuple(value.uses):
        user = use.operation
        if _operation_block(user) is not loop_block:
            return None
        if isinstance(user, DmaCopyOp) and use.index == 0:
            copy_ops.append(user)
            continue
        if isinstance(user, DmaFreeOp) and use.index == 0:
            free_ops.append(user)
            continue
        if _use_is_target_matmul_operand(use, matmul, operand_index):
            saw_matmul_use = True
            continue
        return None
    if len(copy_ops) != 1 or len(free_ops) != 1 or not saw_matmul_use:
        return None
    return copy_ops[0], free_ops[0]


def _candidate_order_is_valid(
    alloc_op: DmaAllocOp,
    copy_op: DmaCopyOp,
    matmul: KernelMatmulOp,
    free_op: DmaFreeOp,
    indexes: dict[Operation, int],
) -> bool:
    """校验 staging 生命周期顺序。

    功能说明:
    - 要求 `alloc < copy < matmul < free`，避免 free 早于 compute 或 stale use。

    使用示例:
    - if _candidate_order_is_valid(alloc, copy, matmul, free, indexes): ...

    关联文件:
    - spec: spec/pass/multi_buffer.md
    - test: test/passes/test_multi_buffer.py
    - 功能实现: kernel_gen/passes/multi_buffer.py
    """

    if alloc_op not in indexes or copy_op not in indexes or matmul not in indexes or free_op not in indexes:
        return False
    return indexes[alloc_op] < indexes[copy_op] < indexes[matmul] < indexes[free_op]


def _build_staging_candidate(
    matmul: KernelMatmulOp,
    operand_index: int,
    loop_block: Block,
    indexes: dict[Operation, int],
    memory_stage: int,
) -> _StagingCandidate | None:
    """为 matmul 的单个 lhs/rhs operand 构造 ring 化候选。

    功能说明:
    - 仅当 operand 来自同一 loop body 内的 `DmaAllocOp` 且直接 use 集合完整时返回候选。

    使用示例:
    - candidate = _build_staging_candidate(matmul, 1, loop_block, indexes, 3)

    关联文件:
    - spec: spec/pass/multi_buffer.md
    - test: test/passes/test_multi_buffer.py
    - 功能实现: kernel_gen/passes/multi_buffer.py
    """

    value = SSAValue.get(matmul.operands[operand_index])
    alloc_op = value.owner
    if not isinstance(alloc_op, DmaAllocOp):
        return None
    if _operation_block(alloc_op) is not loop_block:
        return None
    if not isinstance(alloc_op.result.type, NnMemoryType):
        return None
    direct_uses = _collect_candidate_uses(alloc_op.result, matmul, operand_index, loop_block)
    if direct_uses is None:
        return None
    copy_op, free_op = direct_uses
    if not _candidate_order_is_valid(alloc_op, copy_op, matmul, free_op, indexes):
        return None
    slot_bytes = _static_memory_bytes(alloc_op.result.type)
    if slot_bytes is None or slot_bytes <= 0:
        return None
    offset_bytes = _ring_offset_bytes(slot_bytes)
    return _StagingCandidate(
        alloc_op=alloc_op,
        copy_op=copy_op,
        free_op=free_op,
        matmul_op=matmul,
        operand_index=operand_index,
        slot_bytes=slot_bytes,
        offset_bytes=offset_bytes,
        backing_bytes=memory_stage * offset_bytes,
    )


def _replace_alloc_uses_with_current(candidate: _StagingCandidate, current: DmaCurrentRingOp) -> None:
    """把 staging alloc 的 data use 替换为 current ring slot。

    功能说明:
    - 保留原 `dma.free` 待删除，不把 free 重写为 current slot。

    使用示例:
    - _replace_alloc_uses_with_current(candidate, current)

    关联文件:
    - spec: spec/pass/multi_buffer.md
    - test: test/passes/test_multi_buffer.py
    - 功能实现: kernel_gen/passes/multi_buffer.py
    """

    for use in tuple(candidate.alloc_op.result.uses):
        if use.operation is candidate.free_op:
            continue
        use.operation.operands[use.index] = current.result


def _ring_ops_for_candidate(
    candidate: _StagingCandidate,
    memory_stage: int,
) -> tuple[list[Operation], DmaCurrentRingOp, DmaAdvanceRingOp]:
    """构造单个 candidate 对应的 ring IR op。

    功能说明:
    - loop 外生成 backing alloc、stage/offset/shape_bytes 常量和 `dma.make_ring`。
    - loop 内由调用方插入 `dma.current_ring` 与 `dma.advance_ring`。

    使用示例:
    - pre_ops, current, advance = _ring_ops_for_candidate(candidate, 3)

    关联文件:
    - spec: spec/pass/multi_buffer.md
    - test: test/passes/test_multi_buffer.py
    - 功能实现: kernel_gen/passes/multi_buffer.py
    """

    slot_type = candidate.alloc_op.result.type
    assert isinstance(slot_type, NnMemoryType)
    backing = DmaAllocOp([], _backing_memory_type(slot_type, candidate.backing_bytes))
    count = SymbolConstOp(memory_stage)
    offset = SymbolConstOp(candidate.offset_bytes)
    shape_bytes = SymbolConstOp(candidate.slot_bytes)
    ring_type = DmaRingType(SymbolExprAttr.from_expr(str(candidate.offset_bytes)), slot_type)
    make_ring = DmaMakeRingOp(backing.result, count.result, offset.result, shape_bytes.result, ring_type)
    current = DmaCurrentRingOp(make_ring.result)
    advance = DmaAdvanceRingOp(make_ring.result)
    return [backing, count, offset, shape_bytes, make_ring], current, advance


def _erase_original_lifecycle(loop_block: Block, candidate: _StagingCandidate) -> None:
    """删除原 loop 内 staging alloc/free。

    功能说明:
    - `dma.copy` 和 `kernel.matmul` 保留，只替换其 memory operand 为 ring current slot。

    使用示例:
    - _erase_original_lifecycle(loop_block, candidate)

    关联文件:
    - spec: spec/pass/multi_buffer.md
    - test: test/passes/test_multi_buffer.py
    - 功能实现: kernel_gen/passes/multi_buffer.py
    """

    loop_block.erase_op(candidate.free_op)
    loop_block.erase_op(candidate.alloc_op)


def _rewrite_pair(
    symbol_for: SymbolForOp,
    loop_block: Block,
    matmul: KernelMatmulOp,
    candidates: tuple[_StagingCandidate, _StagingCandidate],
    memory_stage: int,
) -> None:
    """改写一组成对 lhs/rhs staging candidate。

    功能说明:
    - 在 owner loop 前插入 ring backing 和 make_ring。
    - 在原 alloc 位置插入 current_ring，替换 copy 与 matmul use。
    - 在 matmul 后插入 advance_ring，删除原 alloc/free。

    使用示例:
    - _rewrite_pair(symbol_for, loop_block, matmul, (lhs, rhs), 3)

    关联文件:
    - spec: spec/pass/multi_buffer.md
    - test: test/passes/test_multi_buffer.py
    - 功能实现: kernel_gen/passes/multi_buffer.py
    """

    pre_loop_ops: list[Operation] = []
    current_ops: list[tuple[_StagingCandidate, DmaCurrentRingOp]] = []
    advance_ops: list[Operation] = []
    for candidate in candidates:
        pre_ops, current, advance = _ring_ops_for_candidate(candidate, memory_stage)
        pre_loop_ops.extend(pre_ops)
        current_ops.append((candidate, current))
        advance_ops.append(advance)

    parent_block = symbol_for.parent_block()
    if parent_block is None:
        return
    parent_block.insert_ops_before(pre_loop_ops, symbol_for)
    for candidate, current in current_ops:
        loop_block.insert_ops_before([current], candidate.alloc_op)
        _replace_alloc_uses_with_current(candidate, current)
    loop_block.insert_ops_after(advance_ops, matmul)
    for candidate in candidates:
        _erase_original_lifecycle(loop_block, candidate)


def _rewrite_matmul_if_pair(
    symbol_for: SymbolForOp,
    matmul: KernelMatmulOp,
    memory_stage: int,
) -> bool:
    """尝试把单个 matmul 的 lhs/rhs staging 成对 ring 化。

    功能说明:
    - lhs/rhs 任一缺失或失败时整对 no-op，避免 partial ring。

    使用示例:
    - changed = _rewrite_matmul_if_pair(symbol_for, matmul, 3)

    关联文件:
    - spec: spec/pass/multi_buffer.md
    - test: test/passes/test_multi_buffer.py
    - 功能实现: kernel_gen/passes/multi_buffer.py
    """

    loop_block = _operation_block(matmul)
    if loop_block is None or loop_block.parent_op() is not symbol_for:
        return False
    indexes = _block_index_map(loop_block)
    lhs_candidate = _build_staging_candidate(matmul, 1, loop_block, indexes, memory_stage)
    rhs_candidate = _build_staging_candidate(matmul, 2, loop_block, indexes, memory_stage)
    if lhs_candidate is None or rhs_candidate is None:
        return False
    if lhs_candidate.alloc_op is rhs_candidate.alloc_op:
        return False
    _rewrite_pair(symbol_for, loop_block, matmul, (lhs_candidate, rhs_candidate), memory_stage)
    return True


class MultiBufferPass(Pass):
    """multi-buffer pass。

    功能说明:
    - 将可证明的 matmul lhs/rhs staging buffer 成对改写为 `dma.ring`。
    - 默认 `memory_stage=3`，只处理同一 `symbol.for` 直接 body 内的公开模式。

    使用示例:
    - MultiBufferPass(memory_stage=3).apply(Context(), module)

    关联文件:
    - spec: spec/pass/multi_buffer.md
    - test: test/passes/test_multi_buffer.py
    - 功能实现: kernel_gen/passes/multi_buffer.py
    """

    name = "multi-buffer"

    def __init__(self, memory_stage: int = 3, fold: bool = True) -> None:
        """初始化 multi-buffer pass。

        功能说明:
        - 保存 ring stage 数和通用 fold 开关。

        使用示例:
        - pass_obj = MultiBufferPass(memory_stage=3, fold=False)

        关联文件:
        - spec: spec/pass/multi_buffer.md
        - test: test/passes/test_multi_buffer.py
        - 功能实现: kernel_gen/passes/multi_buffer.py
        """

        if isinstance(memory_stage, bool) or not isinstance(memory_stage, int):
            raise_pass_contract_error("MultiBufferOptionError", "memory_stage must be integer")
        if memory_stage <= 0:
            raise_pass_contract_error("MultiBufferOptionError", "memory_stage must be positive")
        super().__init__(fold=fold)
        self.memory_stage = memory_stage

    @classmethod
    def from_options(cls, options: dict[str, str]) -> "MultiBufferPass":
        """从 pass registry options 构造 multi-buffer pass。

        功能说明:
        - 仅接受 pass 专属 `memory-stage`。
        - `fold` 必须由 registry 通用选项处理，传到本方法时按未知 option 失败。

        使用示例:
        - pass_obj = MultiBufferPass.from_options({"memory-stage": "3"})

        关联文件:
        - spec: spec/pass/multi_buffer.md
        - test: test/passes/test_multi_buffer.py
        - 功能实现: kernel_gen/passes/multi_buffer.py
        """

        allowed = {"memory-stage"}
        unknown = sorted(set(options) - allowed)
        if unknown:
            raise_pass_contract_error("MultiBufferOptionError", f"unknown option: {unknown[0]}")
        if "memory-stage" not in options:
            return cls()
        return cls(memory_stage=_parse_memory_stage_option(options["memory-stage"]))

    def apply(self, ctx: Context, module: ModuleOp) -> None:
        """执行 multi-buffer rewrite。

        功能说明:
        - 遍历 `symbol.for` 直接 body 中的 `kernel.matmul`，匹配成对 lhs/rhs staging 生命周期。
        - 不满足条件的结构保持 no-op。

        使用示例:
        - MultiBufferPass().apply(Context(), module)

        关联文件:
        - spec: spec/pass/multi_buffer.md
        - test: test/passes/test_multi_buffer.py
        - 功能实现: kernel_gen/passes/multi_buffer.py
        """

        _ = ctx
        ensure_builtin_module(module)
        for symbol_for in [op for op in module.walk() if isinstance(op, SymbolForOp)]:
            loop_block = symbol_for.body.blocks[0]
            for op in list(loop_block.ops):
                if isinstance(op, KernelMatmulOp):
                    _rewrite_matmul_if_pair(symbol_for, op, self.memory_stage)


__all__ = ["MultiBufferPass"]
