"""hoist-dma-alias-ops pass.

功能说明:
- 提供 `hoist-dma-alias-ops` pass。
- 第一阶段只识别同一 block 内紧邻的 `dma.fill(%src, value)` 与
  `%alias = dma.reshape(%src, ...)`，并在 shape operand 已支配 `dma.fill` 时把
  `dma.reshape` 上移到 `dma.fill` 前，同时把 `dma.fill` target 改为 alias result。
- 变换通过当前文件内私有 `RewritePattern` 与 `PatternRewriteWalker` 驱动，不暴露 pattern getter。
- 不做 fold/combine/canonicalize，不跨 block、region 或控制流移动。

API 列表:
- `class HoistDmaAliasOpsPass(fold: bool = True)`
- `HoistDmaAliasOpsPass.apply(ctx: Context, module: ModuleOp) -> None`

使用示例:
- from xdsl.context import Context
- from kernel_gen.passes.hoist_dma_alias_ops import HoistDmaAliasOpsPass
- HoistDmaAliasOpsPass().apply(Context(), module)

关联文件:
- spec: [spec/pass/hoist_dma_alias_ops.md](spec/pass/hoist_dma_alias_ops.md)
- test: [test/passes/test_hoist_dma_alias_ops.py](test/passes/test_hoist_dma_alias_ops.py)
- 功能实现: [kernel_gen/passes/hoist_dma_alias_ops.py](kernel_gen/passes/hoist_dma_alias_ops.py)
"""

from __future__ import annotations

from xdsl.context import Context
from xdsl.dialects.builtin import ModuleOp
from xdsl.ir import BlockArgument, Operation, SSAValue
from xdsl.pattern_rewriter import (
    GreedyRewritePatternApplier,
    PatternRewriter,
    PatternRewriteWalker,
    RewritePattern,
    op_type_rewrite_pattern,
)
from xdsl.rewriter import InsertPoint
from xdsl.utils.exceptions import VerifyException

from kernel_gen.dialect.dma import DmaFillOp, DmaReshapeOp
from kernel_gen.passes.common import ensure_builtin_module
from kernel_gen.passes.pass_manager import Pass


def _same_value(candidate: SSAValue | Operation, value: SSAValue | Operation) -> bool:
    """判断两个 operand / result 是否指向同一个 SSA value。

    功能说明:
    - 统一处理 xDSL operand 可能传入 `Operation` 或 `SSAValue` 的形态。

    使用示例:
    - if _same_value(fill.target, reshape.source): ...
    """

    return SSAValue.get(candidate) is SSAValue.get(value)


def _value_dominates_op(value: SSAValue, op: Operation) -> bool:
    """判断 value 是否在 op 之前可见。

    功能说明:
    - 接受同 block 中位于 `op` 之前的 operation result。
    - 接受当前 block 或 ancestor block 的 block argument。
    - 对 sibling / descendant region 中的 value 保守返回 False，避免跨控制流移动。

    使用示例:
    - if all(_value_dominates_op(shape, fill) for shape in reshape.shape): ...
    """

    op_block = op.parent_block()
    if op_block is None:
        return False
    if isinstance(value, BlockArgument):
        return value.owner is op_block or value.owner.is_ancestor(op)
    owner = value.owner
    if not isinstance(owner, Operation):
        return True
    owner_block = owner.parent_block()
    if owner_block is None:
        return True
    if owner_block is op_block:
        return owner.is_before_in_block(op)
    ancestor = owner_block.find_ancestor_op_in_block(op)
    if ancestor is None or owner is ancestor:
        return False
    return owner.is_before_in_block(ancestor)


def _reshape_shape_dominates_fill(reshape: DmaReshapeOp, fill: DmaFillOp) -> bool:
    """判断 reshape 的 shape operands 是否都支配 fill。

    功能说明:
    - `dma.reshape` 上移到 `dma.fill` 前之后仍必须满足 SSA 支配关系。
    - 任一 shape operand 在 `fill` 之后或不在可见 ancestor 中定义时保持 no-op。

    使用示例:
    - if _reshape_shape_dominates_fill(reshape, fill): ...
    """

    return all(_value_dominates_op(SSAValue.get(shape), fill) for shape in reshape.shape)


def _candidate_fill(reshape: DmaReshapeOp) -> DmaFillOp | None:
    """返回可被当前 reshape 穿过的紧邻 dma.fill。

    功能说明:
    - 只接受 `reshape.prev_op` 是 `DmaFillOp` 且 fill target 等于 reshape source。
    - 其它非紧邻、不同源或跨 block 形态均保持 no-op。

    使用示例:
    - fill = _candidate_fill(reshape)
    """

    previous = reshape.prev_op
    if not isinstance(previous, DmaFillOp):
        return None
    if not _same_value(previous.target, reshape.source):
        return None
    if not _reshape_shape_dominates_fill(reshape, previous):
        return None
    return previous


def _move_reshape_before_fill(
    module: ModuleOp,
    reshape: DmaReshapeOp,
    fill: DmaFillOp,
    rewriter: PatternRewriter,
) -> bool:
    """执行一次 reshape 穿过 fill 的事务式改写。

    功能说明:
    - 复用原 `dma.reshape` op/result，不新建 alias。
    - 通过 `PatternRewriter` 把 op 插到 `dma.fill` 前，满足用户指定的 pattern rewrite 形态。
    - 先移动 op 并改写 fill target，再用 `module.verify()` 验证。
    - 验证失败时撤销本次移动与 operand 改写，保证失败原 module 零改动。

    使用示例:
    - changed = _move_reshape_before_fill(module, reshape, fill, rewriter)
    """

    block = reshape.parent_block()
    if block is None or fill.parent_block() is not block:
        return False
    original_target = fill.operands[0]
    reshape.detach()
    rewriter.insert_op(reshape, InsertPoint.before(fill))
    fill.operands[0] = reshape.result
    try:
        module.verify()
    except VerifyException:
        fill.operands[0] = original_target
        reshape.detach()
        block.insert_op_after(reshape, fill)
        return False
    rewriter.notify_op_modified(fill)
    return True


class _DmaReshapeThroughFillPattern(RewritePattern):
    """`dma.reshape` 穿过紧邻 `dma.fill` 的私有 pattern。

    功能说明:
    - 只匹配 `DmaReshapeOp`，并复用 `_candidate_fill(...)` 收口同 block、紧邻、同源与支配边界。
    - 该 pattern 不作为公开 API 导出，也不提供 getter。

    使用示例:
    - pattern = _DmaReshapeThroughFillPattern(module)
    """

    def __init__(self: "_DmaReshapeThroughFillPattern", module: ModuleOp) -> None:
        """初始化 pattern 持有的 module verifier 上下文。

        功能说明:
        - 保存当前 `builtin.module`，用于事务式 rewrite 后验证并在失败时回滚。
        - 记录已被 verifier 拒绝的 reshape op，避免 greedy walker 反复重试同一失败候选。

        使用示例:
        - pattern = _DmaReshapeThroughFillPattern(module)
        """

        self.module = module
        self.rejected_reshape_ops: set[int] = set()

    @op_type_rewrite_pattern
    def match_and_rewrite(self: "_DmaReshapeThroughFillPattern", op: DmaReshapeOp, rewriter: PatternRewriter, /) -> None:
        """执行单个 `fill -> reshape` 候选改写。

        功能说明:
        - 未满足候选条件时保持 no-op。
        - 满足条件时用 pattern rewriter 把 reshape 移到 fill 前，并将 fill target 改为 alias result。

        使用示例:
        - _DmaReshapeThroughFillPattern(module).match_and_rewrite(reshape, rewriter)
        """

        if id(op) in self.rejected_reshape_ops:
            return
        fill = _candidate_fill(op)
        if fill is None:
            return
        if not _move_reshape_before_fill(self.module, op, fill, rewriter):
            self.rejected_reshape_ops.add(id(op))


def _rewrite_module_to_fixed_point(ctx: Context, module: ModuleOp, *, fold: bool) -> None:
    """用 pattern walker 执行 alias op 上移直到稳定。

    功能说明:
    - 第一阶段只注册当前文件内私有 `DmaReshapeOp` pattern。
    - Greedy walker 负责对 module 内多个独立候选收敛，不做手工整段遍历搬 op。

    使用示例:
    - _rewrite_module_to_fixed_point(ctx, module, fold=True)
    """

    PatternRewriteWalker(
        GreedyRewritePatternApplier(
            [_DmaReshapeThroughFillPattern(module)],
            ctx=ctx,
            folding_enabled=fold,
            dce_enabled=False,
        )
    ).rewrite_module(module)


class HoistDmaAliasOpsPass(Pass):
    """`hoist-dma-alias-ops` pass 公开入口。

    功能说明:
    - 第一阶段只让 `dma.reshape` 穿过紧邻且同源的 `dma.fill`。
    - 内部通过 xDSL pattern rewrite 基础设施驱动，不提供公开 pattern getter。
    - 不提供 pass 专属 option；registry 只支持通用 `fold` option。

    使用示例:
    - HoistDmaAliasOpsPass().apply(Context(), module)
    """

    name = "hoist-dma-alias-ops"

    def apply(self: "HoistDmaAliasOpsPass", ctx: Context, module: ModuleOp) -> None:
        """执行 `hoist-dma-alias-ops` ModulePass。

        功能说明:
        - 校验输入为 `builtin.module`。
        - 对 module 内所有函数和 nested region 通过 pattern walker 执行紧邻 alias 上移。

        使用示例:
        - HoistDmaAliasOpsPass(fold=False).apply(Context(), module)
        """

        _ = ctx
        module = ensure_builtin_module(module)
        _rewrite_module_to_fixed_point(ctx, module, fold=self.fold)


__all__ = ["HoistDmaAliasOpsPass"]
