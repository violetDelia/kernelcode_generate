"""symbol-buffer-hoist pass.


功能说明:
- 定义 `symbol-buffer-hoist` 的公开 pass、公开 pattern 与公开 pattern getter。
- 只在 `symbol.for` 单 block 循环体内识别 `dma.alloc`，并在 shape 明确不依赖 loop 内 SSA、
  直接 use 仅属于输入 staging / output scratch 或受支持 alias producer，且存在唯一匹配 `dma.free`
  时，将其与 `dma.free` 成对外提一层。
- 当同一 `symbol.for` 直接 body 内存在唯一匹配 `dma.free` 且该 free 晚于所有 data use 时，
  外提 `dma.alloc` 的同时把对应 `dma.free` 移到同一 `symbol.for` 之后。
- 对 source、offset/shape/stride 等 operand 均支配当前 `symbol.for` 的 `dma.view`、`dma.reshape`
  和 `dma.subview`，作为独立 alias op 单次外提一层。
- 失败边界统一复用 `KernelCodeError(module="pass")`；不新增专题专属错误类型，也不承诺额外 compat path。

API 列表:
- `class DmaAllocInSymbolForHoistPattern()`
- `DmaAllocInSymbolForHoistPattern.match_and_rewrite(op: DmaAllocOp, rewriter: PatternRewriter) -> None`
- `get_symbol_buffer_hoist_patterns() -> list[RewritePattern]`
- `class SymbolBufferHoistPass(fold: bool = True)`
- `SymbolBufferHoistPass.apply(ctx: Context, module: ModuleOp) -> None`

使用示例:
- from xdsl.context import Context
- from xdsl.dialects.builtin import ModuleOp
- from kernel_gen.passes.symbol_buffer_hoist import SymbolBufferHoistPass
- module = ModuleOp([])
- SymbolBufferHoistPass().apply(Context(), module)

关联文件:
- spec: spec/pass/symbol_buffer_hoist.md
- test: test/passes/test_symbol_buffer_hoist.py
- test: test/passes/test_registry.py
- 功能实现: kernel_gen/passes/symbol_buffer_hoist.py
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass

from xdsl.context import Context
from xdsl.dialects.builtin import ModuleOp
from xdsl.ir import Block, BlockArgument, Operation, SSAValue, Use
from xdsl.pattern_rewriter import (
    GreedyRewritePatternApplier,
    PatternRewriter,
    PatternRewriteWalker,
    RewritePattern,
    op_type_rewrite_pattern,
)
from xdsl.rewriter import InsertPoint
from xdsl.utils.exceptions import VerifyException

from kernel_gen.core.error import ErrorKind, ErrorModule, KernelCodeError
from kernel_gen.dialect.dma import (
    DmaAllocOp,
    DmaCopyOp,
    DmaDesliceOp,
    DmaFillOp,
    DmaFreeOp,
    DmaReshapeOp,
    DmaSliceOp,
    DmaSubviewOp,
    DmaViewOp,
)
from kernel_gen.dialect.symbol import Symbol, SymbolForOp
from kernel_gen.passes.common import ensure_builtin_module
from kernel_gen.passes.pass_manager import Pass


@dataclass(frozen=True)
class _HoistUsePlan:
    """记录一次 alloc 外提可接受的 direct use 分类。


    功能说明:
    - `data_uses` 保存同一 loop body 内的 `dma.slice target` / `dma.deslice source` use。
    - `free_op` 表示可随 alloc 成对外提的唯一 `dma.free`。

    使用示例:
    - plan = _HoistUsePlan(data_uses=(slice_use,), free_op=free_op)

    关联文件:
    - spec: spec/pass/symbol_buffer_hoist.md
    - test: test/passes/test_symbol_buffer_hoist.py
    - 功能实现: kernel_gen/passes/symbol_buffer_hoist.py
    """

    data_uses: tuple[Use, ...]
    free_op: DmaFreeOp | None


def _value_dominates_symbol_for(value: SSAValue, symbol_for: SymbolForOp) -> bool:
    """判断 SSA 值是否在当前 `symbol.for` 前可见。


    功能说明:
    - 只接受定义在当前 loop body 外、且支配当前 `symbol.for` 的 SSA 值。
    - 当前 loop body、nested region 或 sibling block 内定义的值都保守视为不可外提。
    - 外层 loop body 中位于当前 `symbol.for` 前的值允许作为“当前层” invariant。

    使用示例:
    - _value_dominates_symbol_for(symbol_dim, symbol_for)

    关联文件:
    - spec: spec/pass/symbol_buffer_hoist.md
    - test: test/passes/test_symbol_buffer_hoist.py
    - 功能实现: kernel_gen/passes/symbol_buffer_hoist.py
    """

    loop_block = symbol_for.body.blocks[0]
    if isinstance(value, BlockArgument):
        return value.owner is not loop_block and value.owner.is_ancestor(symbol_for)
    owner = value.owner
    if not isinstance(owner, Operation):
        return True
    owner_block = owner.parent_block()
    if owner_block is None:
        return True
    if owner_block is loop_block or loop_block.is_ancestor(owner):
        return False
    if owner_block is symbol_for.parent_block():
        return owner.is_before_in_block(symbol_for)
    ancestor = owner_block.find_ancestor_op_in_block(symbol_for)
    if ancestor is None or owner is ancestor:
        return False
    return owner.is_before_in_block(ancestor)


def _shape_is_loop_invariant(op: DmaAllocOp, symbol_for: SymbolForOp) -> bool:
    """判断 `dma.alloc` 的 dynamic_shape 是否全部来自 loop 外。


    功能说明:
    - 空 `dynamic_shape` 视为满足 invariant。
    - 只要任一 shape operand 来自当前 loop body 或 loop-carried block argument，就保持 no-op。

    使用示例:
    - _shape_is_loop_invariant(alloc_op, symbol_for)

    关联文件:
    - spec: spec/pass/symbol_buffer_hoist.md
    - test: test/passes/test_symbol_buffer_hoist.py
    - 功能实现: kernel_gen/passes/symbol_buffer_hoist.py
    """

    return all(_value_dominates_symbol_for(SSAValue.get(value), symbol_for) for value in op.dynamic_shape)


def _is_supported_data_use(use: Use) -> bool:
    """判断 `dma.alloc` 的单个 direct data use 是否属于公开白名单。


    功能说明:
    - 输入 staging buffer：仅接受 `dma.slice` 的 `target` operand。
    - output scratch buffer：仅接受 `dma.deslice` 的 `source` operand。
    - `dma.free` 属于 lifecycle use，由独立规则处理。
    - 其他 direct use 一律视为未承接的逃逸形态。

    使用示例:
    - all(_is_supported_data_use(use) for use in alloc_op.result.uses)

    关联文件:
    - spec: spec/pass/symbol_buffer_hoist.md
    - test: test/passes/test_symbol_buffer_hoist.py
    - 功能实现: kernel_gen/passes/symbol_buffer_hoist.py
    """

    user = use.operation
    return (isinstance(user, DmaSliceOp) and use.index == 0) or (
        isinstance(user, DmaDesliceOp) and use.index == 1
    )


def _is_supported_alias_result_use(use: Use) -> bool:
    """判断 alias result 的 direct use 是否属于可捕获白名单。


    功能说明:
    - 允许 `dma.slice target`、`dma.deslice source`、`dma.fill target`、`dma.copy target/source`。
    - 允许 `symbol.get_dim` 读取 alias memory 的 shape 信息；它不移动 memory 生命周期。
    - `kernel.*` 属于当前计划的 alias escape/no-op 边界，不纳入 alias result 白名单。
    - 其它 direct use 保持 no-op，避免把未知副作用或逃逸形态做宽。

    使用示例:
    - if _is_supported_alias_result_use(use): ...

    关联文件:
    - spec: spec/pass/symbol_buffer_hoist.md
    - test: test/passes/test_symbol_buffer_hoist.py
    - 功能实现: kernel_gen/passes/symbol_buffer_hoist.py
    """

    user = use.operation
    if _is_supported_data_use(use):
        return True
    if isinstance(user, DmaFillOp) and use.index == 0:
        return True
    if isinstance(user, DmaCopyOp) and use.index in (0, 1):
        return True
    if user.name == "symbol.get_dim":
        return True
    return False


def _is_supported_alias_source_use(use: Use) -> bool:
    """判断 direct use 是否为受支持 alias op 的 source operand。


    功能说明:
    - 只允许 `dma.view`、`dma.reshape`、`dma.subview` 的 source use。
    - 该 helper 仅服务当前文件内 alloc/free 与 alias op 外提判定，不构成公开 API。

    使用示例:
    - if _is_supported_alias_source_use(use): ...

    关联文件:
    - spec: spec/pass/symbol_buffer_hoist.md
    - test: test/passes/test_symbol_buffer_hoist.py
    - 功能实现: kernel_gen/passes/symbol_buffer_hoist.py
    """

    user = use.operation
    return use.index == 0 and isinstance(user, (DmaViewOp, DmaReshapeOp, DmaSubviewOp))


def _collect_direct_uses(result: SSAValue) -> tuple[Use, ...]:
    """收集 alloc 结果的直接 use 列表。


    功能说明:
    - 把 xdsl use 链转成稳定 tuple，便于重复遍历与空 use 判定。

    使用示例:
    - uses = _collect_direct_uses(alloc_op.result)

    关联文件:
    - spec: spec/pass/symbol_buffer_hoist.md
    - test: test/passes/test_symbol_buffer_hoist.py
    - 功能实现: kernel_gen/passes/symbol_buffer_hoist.py
    """

    return tuple(cast_use for cast_use in result.uses)


def _operation_parent_block(op: Operation) -> Block | None:
    """返回 operation 的 parent block。


    功能说明:
    - 收口 xDSL parent block 读取，供 direct use 分类复用。

    使用示例:
    - block = _operation_parent_block(use.operation)

    关联文件:
    - spec: spec/pass/symbol_buffer_hoist.md
    - test: test/passes/test_symbol_buffer_hoist.py
    - 功能实现: kernel_gen/passes/symbol_buffer_hoist.py
    """

    return op.parent_block()


def _block_index_map(block: Block) -> dict[Operation, int]:
    """构造 block 内 operation 到顺序索引的映射。


    功能说明:
    - 用于判断 `dma.free` 是否晚于所有 data use。

    使用示例:
    - indexes = _block_index_map(loop_block)

    关联文件:
    - spec: spec/pass/symbol_buffer_hoist.md
    - test: test/passes/test_symbol_buffer_hoist.py
    - 功能实现: kernel_gen/passes/symbol_buffer_hoist.py
    """

    return {item: index for index, item in enumerate(block.ops)}


def _free_follows_data_uses(free_op: DmaFreeOp, data_uses: tuple[Use, ...], loop_block: Block) -> bool:
    """判断唯一 free 是否位于所有 data use 之后。


    功能说明:
    - free 和 data use 必须都在同一 owner loop body 内。
    - 任一 operation 不在 block 顺序表内时保守 no-op。

    使用示例:
    - if _free_follows_data_uses(free_op, data_uses, loop_block): ...

    关联文件:
    - spec: spec/pass/symbol_buffer_hoist.md
    - test: test/passes/test_symbol_buffer_hoist.py
    - 功能实现: kernel_gen/passes/symbol_buffer_hoist.py
    """

    if not data_uses:
        return False
    indexes = _block_index_map(loop_block)
    if free_op not in indexes:
        return False
    data_indexes: list[int] = []
    for use in data_uses:
        if use.operation not in indexes:
            return False
        data_indexes.append(indexes[use.operation])
    return indexes[free_op] > max(data_indexes)


def _collect_alias_data_uses(alias_op: Operation, loop_block: Block, visited: frozenset[Operation]) -> tuple[Use, ...] | None:
    """收集 alias result 最终承接的可捕获 use。


    功能说明:
    - `dma.view`、`dma.reshape`、`dma.subview` result 只能被同一 owner loop 直接 body 内的
      可捕获 memory use 或下一层受支持 alias op 使用。
    - nested/sibling region、`symbol.yield`、`func.return` 或未知 direct use 一律让外提 no-op。
    - 返回的 use 用于证明 matching free 晚于 alias 链真实消费。

    使用示例:
    - data_uses = _collect_alias_data_uses(view_op, loop_block, frozenset())

    关联文件:
    - spec: spec/pass/symbol_buffer_hoist.md
    - test: test/passes/test_symbol_buffer_hoist.py
    - 功能实现: kernel_gen/passes/symbol_buffer_hoist.py
    """

    if alias_op in visited:
        return None
    if _operation_parent_block(alias_op) is not loop_block:
        return None
    if len(alias_op.results) != 1:
        return None
    result_uses = _collect_direct_uses(alias_op.results[0])
    if not result_uses:
        return None

    next_visited = visited | frozenset((alias_op,))
    data_uses: list[Use] = []
    for use in result_uses:
        if _operation_parent_block(use.operation) is not loop_block:
            return None
        if _is_supported_alias_result_use(use):
            data_uses.append(use)
            continue
        if _is_supported_alias_source_use(use):
            nested_data_uses = _collect_alias_data_uses(use.operation, loop_block, next_visited)
            if nested_data_uses is None:
                return None
            data_uses.extend(nested_data_uses)
            continue
        return None
    return tuple(data_uses)


def _build_hoist_use_plan(uses: Iterable[Use], loop_block: Block) -> _HoistUsePlan | None:
    """判断 alloc 结果的 direct use 集合是否满足当前公开外提条件。


    功能说明:
    - 当前公开语义要求 alloc 至少存在一个 data use。
    - data use 必须是同一 loop body 内的 `dma.slice target`、`dma.deslice source`
      或受支持 alias 链最终导向的同类 data use。
    - lifecycle use 必须存在同一 loop body 内唯一 `dma.free`，且必须晚于所有 data use。
    - 多个 free、nested free、跨 loop free 或未知 direct use 均保持 no-op。

    使用示例:
    - plan = _build_hoist_use_plan(_collect_direct_uses(alloc_op.result), loop_block)

    关联文件:
    - spec: spec/pass/symbol_buffer_hoist.md
    - test: test/passes/test_symbol_buffer_hoist.py
    - 功能实现: kernel_gen/passes/symbol_buffer_hoist.py
    """

    collected_uses = tuple(uses)
    if not collected_uses:
        return None

    data_uses: list[Use] = []
    free_ops: list[DmaFreeOp] = []
    for use in collected_uses:
        user = use.operation
        if _operation_parent_block(user) is not loop_block:
            return None
        if _is_supported_data_use(use):
            data_uses.append(use)
            continue
        if _is_supported_alias_source_use(use):
            alias_data_uses = _collect_alias_data_uses(user, loop_block, frozenset())
            if alias_data_uses is None:
                return None
            data_uses.extend(alias_data_uses)
            continue
        if isinstance(user, DmaFreeOp) and use.index == 0:
            free_ops.append(user)
            continue
        return None

    if not data_uses or len(free_ops) != 1:
        return None
    free_op = free_ops[0]
    data_use_tuple = tuple(data_uses)
    if not _free_follows_data_uses(free_op, data_use_tuple, loop_block):
        return None
    return _HoistUsePlan(data_uses=data_use_tuple, free_op=free_op)


class DmaAllocInSymbolForHoistPattern(RewritePattern):
    """`symbol.for` 内 `dma.alloc` 外提 pattern。


    功能说明:
    - 只匹配当前 `symbol.for` body block 顶层的 `dma.alloc`。
    - 满足 shape invariant、direct use 白名单与唯一匹配 free 时，把 alloc 外提到所属 `symbol.for` 之前。
    - 若存在合法匹配 free，同步把 free 移到所属 `symbol.for` 之后，保持生命周期成对外提。

    使用示例:
    - pattern = DmaAllocInSymbolForHoistPattern()

    关联文件:
    - spec: spec/pass/symbol_buffer_hoist.md
    - test: test/passes/test_symbol_buffer_hoist.py
    - 功能实现: kernel_gen/passes/symbol_buffer_hoist.py
    """

    @op_type_rewrite_pattern
    def match_and_rewrite(self, op: DmaAllocOp, rewriter: PatternRewriter, /) -> None:
        """对满足公开条件的 loop 内 `dma.alloc` 执行外提。


        功能说明:
        - 仅当 alloc 位于 `symbol.for` 直接 body block 内时继续。
        - shape 或 direct use 任一条件不满足时保持 no-op。
        - 外提后复用原 op/result，不新建等价 alloc；合法 free 也复用原 op。

        使用示例:
        - DmaAllocInSymbolForHoistPattern().match_and_rewrite(op, rewriter)

        关联文件:
        - spec: spec/pass/symbol_buffer_hoist.md
        - test: test/passes/test_symbol_buffer_hoist.py
        - 功能实现: kernel_gen/passes/symbol_buffer_hoist.py
        """

        loop_block = op.parent_block()
        if loop_block is None:
            return
        symbol_for = loop_block.parent_op()
        if not isinstance(symbol_for, SymbolForOp):
            return
        if not _shape_is_loop_invariant(op, symbol_for):
            return
        use_plan = _build_hoist_use_plan(_collect_direct_uses(op.result), loop_block)
        if use_plan is None:
            return
        op.detach()
        rewriter.insert_op(op, InsertPoint.before(symbol_for))
        if use_plan.free_op is not None:
            use_plan.free_op.detach()
            rewriter.insert_op(use_plan.free_op, InsertPoint.after(symbol_for))
        rewriter.notify_op_modified(symbol_for)


def _alias_operands(op: Operation) -> tuple[SSAValue, ...]:
    """返回 alias op 外提所需检查的全部 operand。


    功能说明:
    - `dma.view` 检查 source、offsets、shape、stride。
    - `dma.reshape` 检查 source 与 shape。
    - `dma.subview` 检查 source、offset、size、stride。

    使用示例:
    - operands = _alias_operands(view_op)

    关联文件:
    - spec: spec/pass/symbol_buffer_hoist.md
    - test: test/passes/test_symbol_buffer_hoist.py
    - 功能实现: kernel_gen/passes/symbol_buffer_hoist.py
    """

    if isinstance(op, DmaViewOp):
        return (SSAValue.get(op.source), *tuple(op.offsets), *tuple(op.shape), *tuple(op.stride))
    if isinstance(op, DmaReshapeOp):
        return (SSAValue.get(op.source), *tuple(op.shape))
    if isinstance(op, DmaSubviewOp):
        return (*tuple(op.source), *tuple(op.offset), *tuple(op.size), *tuple(op.stride))
    return ()


def _alias_result_uses_are_supported(op: Operation, loop_block: Block) -> bool:
    """判断 alias op result 是否只流向当前 loop 直接 body 内的白名单 use。


    功能说明:
    - 至少需要一个 direct use，避免外提无用或逃逸 alias。
    - 支持 alias result 继续喂给 `dma.view`、`dma.reshape`、`dma.subview`，后续 pattern 会继续单 op 外提。
    - 支持 alias result 被同一 loop 直接 body 内的 `dma.fill`、`dma.copy` 或 `symbol.get_dim` 捕获。
    - `kernel.*` 不是当前 alias op 白名单；遇到时保守 no-op，避免把 kernel 副作用规则做宽。

    使用示例:
    - if _alias_result_uses_are_supported(view_op, loop_block): ...

    关联文件:
    - spec: spec/pass/symbol_buffer_hoist.md
    - test: test/passes/test_symbol_buffer_hoist.py
    - 功能实现: kernel_gen/passes/symbol_buffer_hoist.py
    """

    if len(op.results) != 1:
        return False
    result_uses = _collect_direct_uses(op.results[0])
    if not result_uses:
        return False
    for use in result_uses:
        if _operation_parent_block(use.operation) is not loop_block:
            return False
        if _is_supported_alias_result_use(use):
            continue
        if _is_supported_alias_source_use(use):
            continue
        return False
    return True


def _hoist_alias_op_if_safe(op: Operation, rewriter: PatternRewriter) -> None:
    """在满足公开边界时把单个 alias op 外提一层。


    功能说明:
    - 仅处理当前 `symbol.for` 直接 body 内的 alias op。
    - source 与布局 operand 必须全部支配当前 `symbol.for`。
    - result use 必须留在当前 loop 直接 body 的公开白名单内。

    使用示例:
    - _hoist_alias_op_if_safe(view_op, rewriter)

    关联文件:
    - spec: spec/pass/symbol_buffer_hoist.md
    - test: test/passes/test_symbol_buffer_hoist.py
    - 功能实现: kernel_gen/passes/symbol_buffer_hoist.py
    """

    loop_block = op.parent_block()
    if loop_block is None:
        return
    symbol_for = loop_block.parent_op()
    if not isinstance(symbol_for, SymbolForOp):
        return
    if not all(_value_dominates_symbol_for(operand, symbol_for) for operand in _alias_operands(op)):
        return
    if not _alias_result_uses_are_supported(op, loop_block):
        return
    op.detach()
    rewriter.insert_op(op, InsertPoint.before(symbol_for))
    rewriter.notify_op_modified(symbol_for)


class _DmaViewInSymbolForHoistPattern(RewritePattern):
    """`symbol.for` 内 `dma.view` 单 op 外提 pattern。


    功能说明:
    - 私有 pattern；不作为公开 API 导出。
    - 只在 source 与 offset/shape/stride 均对当前 loop invariant 时外提一层。

    使用示例:
    - pattern = _DmaViewInSymbolForHoistPattern()

    关联文件:
    - spec: spec/pass/symbol_buffer_hoist.md
    - test: test/passes/test_symbol_buffer_hoist.py
    - 功能实现: kernel_gen/passes/symbol_buffer_hoist.py
    """

    @op_type_rewrite_pattern
    def match_and_rewrite(self, op: DmaViewOp, rewriter: PatternRewriter, /) -> None:
        """对满足条件的 `dma.view` 执行单层外提。


        功能说明:
        - 不新增 loop argument；loop body 直接捕获外提后的 SSA result。
        - 任一 operand 不支配当前 loop 或 result use 不在白名单时保持 no-op。

        使用示例:
        - _DmaViewInSymbolForHoistPattern().match_and_rewrite(op, rewriter)

        关联文件:
        - spec: spec/pass/symbol_buffer_hoist.md
        - test: test/passes/test_symbol_buffer_hoist.py
        - 功能实现: kernel_gen/passes/symbol_buffer_hoist.py
        """

        _hoist_alias_op_if_safe(op, rewriter)


class _DmaReshapeInSymbolForHoistPattern(RewritePattern):
    """`symbol.for` 内 `dma.reshape` 单 op 外提 pattern。


    功能说明:
    - 私有 pattern；不作为公开 API 导出。
    - 只在 source 与 shape 均对当前 loop invariant 时外提一层。

    使用示例:
    - pattern = _DmaReshapeInSymbolForHoistPattern()

    关联文件:
    - spec: spec/pass/symbol_buffer_hoist.md
    - test: test/passes/test_symbol_buffer_hoist.py
    - 功能实现: kernel_gen/passes/symbol_buffer_hoist.py
    """

    @op_type_rewrite_pattern
    def match_and_rewrite(self, op: DmaReshapeOp, rewriter: PatternRewriter, /) -> None:
        """对满足条件的 `dma.reshape` 执行单层外提。


        功能说明:
        - 不新增 loop argument；loop body 直接捕获外提后的 SSA result。
        - shape 来自当前 loop body、loop iterator 或 loop-carried 值时保持 no-op。

        使用示例:
        - _DmaReshapeInSymbolForHoistPattern().match_and_rewrite(op, rewriter)

        关联文件:
        - spec: spec/pass/symbol_buffer_hoist.md
        - test: test/passes/test_symbol_buffer_hoist.py
        - 功能实现: kernel_gen/passes/symbol_buffer_hoist.py
        """

        _hoist_alias_op_if_safe(op, rewriter)


class _DmaSubviewInSymbolForHoistPattern(RewritePattern):
    """`symbol.for` 内 `dma.subview` 单 op 外提 pattern。


    功能说明:
    - 私有 pattern；不作为公开 API 导出。
    - 只在 source、offset、size、stride 均对当前 loop invariant 时外提一层。

    使用示例:
    - pattern = _DmaSubviewInSymbolForHoistPattern()

    关联文件:
    - spec: spec/pass/symbol_buffer_hoist.md
    - test: test/passes/test_symbol_buffer_hoist.py
    - 功能实现: kernel_gen/passes/symbol_buffer_hoist.py
    """

    @op_type_rewrite_pattern
    def match_and_rewrite(self, op: DmaSubviewOp, rewriter: PatternRewriter, /) -> None:
        """对满足条件的 `dma.subview` 执行单层外提。


        功能说明:
        - 不新增 loop argument；loop body 直接捕获外提后的 SSA result。
        - offset/size/stride 来自当前 loop body 时保持 no-op。

        使用示例:
        - _DmaSubviewInSymbolForHoistPattern().match_and_rewrite(op, rewriter)

        关联文件:
        - spec: spec/pass/symbol_buffer_hoist.md
        - test: test/passes/test_symbol_buffer_hoist.py
        - 功能实现: kernel_gen/passes/symbol_buffer_hoist.py
        """

        _hoist_alias_op_if_safe(op, rewriter)


def get_symbol_buffer_hoist_patterns() -> list[RewritePattern]:
    """返回 `symbol-buffer-hoist` 公开 pattern 列表。


    功能说明:
    - 公开返回 `dma.alloc/free` pattern 与私有 alias op pattern 实例。
    - 返回值顺序固定为 alloc/free、view、reshape、subview，便于 greedy walker 逐层收敛。

    使用示例:
    - patterns = get_symbol_buffer_hoist_patterns()

    关联文件:
    - spec: spec/pass/symbol_buffer_hoist.md
    - test: test/passes/test_symbol_buffer_hoist.py
    - 功能实现: kernel_gen/passes/symbol_buffer_hoist.py
    """

    return [
        DmaAllocInSymbolForHoistPattern(),
        _DmaViewInSymbolForHoistPattern(),
        _DmaReshapeInSymbolForHoistPattern(),
        _DmaSubviewInSymbolForHoistPattern(),
    ]


def _rewrite_module_once(ctx: Context, module: ModuleOp, *, fold: bool) -> None:
    """对 module 执行一轮 `symbol-buffer-hoist` pattern walker。


    功能说明:
    - 当前文件内部 helper；保持公开 pass API 不变。
    - 单轮 walker 仍遵守每个 pattern 只移动一个 op、一层 loop 的边界。

    使用示例:
    - _rewrite_module_once(ctx, module, fold=True)

    关联文件:
    - spec: spec/pass/symbol_buffer_hoist.md
    - test: test/passes/test_symbol_buffer_hoist.py
    - 功能实现: kernel_gen/passes/symbol_buffer_hoist.py
    """

    PatternRewriteWalker(
        GreedyRewritePatternApplier(
            get_symbol_buffer_hoist_patterns(),
            ctx=ctx,
            folding_enabled=fold,
            dce_enabled=False,
        )
    ).rewrite_module(module)


def _rewrite_module_to_fixed_point(ctx: Context, module: ModuleOp, *, fold: bool) -> None:
    """重复执行 walker，直到 alias op 外提达到稳定态。


    功能说明:
    - `dma.view` 外提后，依赖该 view 的 `dma.reshape` 可能才满足支配条件。
    - 通过模块文本稳定性检测追加有限轮收敛，避免单轮遍历漏掉后继 alias op。
    - 每轮仍复用公开 pattern 列表，不引入跨文件私有 API 或新公开入口。

    使用示例:
    - _rewrite_module_to_fixed_point(ctx, module, fold=True)

    关联文件:
    - spec: spec/pass/symbol_buffer_hoist.md
    - test: test/passes/test_symbol_buffer_hoist.py
    - 功能实现: kernel_gen/passes/symbol_buffer_hoist.py
    """

    for _iteration in range(8):
        before = str(module)
        _rewrite_module_once(ctx, module, fold=fold)
        if str(module) == before:
            return


class SymbolBufferHoistPass(Pass):
    """`symbol-buffer-hoist` pass。


    功能说明:
    - 通过 pattern walker fixed point 处理 module 中满足公开条件的 `dma.alloc/free` 与 alias op 外提。
    - 非 `builtin.module` 输入直接复用共享 `KernelCodeError("module must be builtin.module")`。
    - 最终 verifier 失败统一转成 `KernelCodeError("SymbolBufferHoistVerifierError: ...")`。

    使用示例:
    - from xdsl.context import Context
    - from xdsl.dialects.builtin import ModuleOp
    - module = ModuleOp([])
    - SymbolBufferHoistPass().apply(Context(), module)

    关联文件:
    - spec: spec/pass/symbol_buffer_hoist.md
    - test: test/passes/test_symbol_buffer_hoist.py
    - test: test/passes/test_registry.py
    - 功能实现: kernel_gen/passes/symbol_buffer_hoist.py
    """

    name = "symbol-buffer-hoist"

    def apply(self, ctx: Context, module: ModuleOp) -> None:
        """执行 `symbol-buffer-hoist` ModulePass。


        功能说明:
        - 只处理 `builtin.module`。
        - 用 greedy pattern walker 把 `symbol.for` 内可安全外提的 alloc/alias op 推进到稳定态。
        - 最终统一做一次 `module.verify()`，保持公开失败前缀稳定。

        使用示例:
        - SymbolBufferHoistPass().apply(Context(), module)

        关联文件:
        - spec: spec/pass/symbol_buffer_hoist.md
        - test: test/passes/test_symbol_buffer_hoist.py
        - test: test/passes/test_registry.py
        - 功能实现: kernel_gen/passes/symbol_buffer_hoist.py
        """

        module = ensure_builtin_module(module)
        if ctx.get_optional_dialect(Symbol.name) is None:
            ctx.load_dialect(Symbol)
        _rewrite_module_to_fixed_point(ctx, module, fold=self.fold)
        try:
            module.verify()
        except VerifyException as exc:
            raise KernelCodeError(ErrorKind.CONTRACT, ErrorModule.PASS, f"SymbolBufferHoistVerifierError: {exc}") from exc

__all__ = [
    "DmaAllocInSymbolForHoistPattern",
    "get_symbol_buffer_hoist_patterns",
    "SymbolBufferHoistPass",
]
