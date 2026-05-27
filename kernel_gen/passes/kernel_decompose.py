"""kernel decompose pass.

功能说明:
- 提供 `kernel-decompose` pass，把中间 kernel 聚合 op 规整成下游可消费 kernel IR。
- 第一版处理 `kernel.matmul_fusion`，输出带动态 acc operand 的 `kernel.matmul`。
- 在可机械证明安全时删除 fusion 对应的初始 `dma.fill(out, 0)`。

API 列表:
- `class KernelDecomposePass(fold: bool = True)`
- `KernelDecomposePass.from_options(options: dict[str, str]) -> KernelDecomposePass`
- `KernelDecomposePass.apply(ctx: Context, module: ModuleOp) -> None`

使用示例:
- from kernel_gen.passes.kernel_decompose import KernelDecomposePass
- KernelDecomposePass().apply(Context(), module)
- KernelDecomposePass.from_options({})

关联文件:
- spec: spec/pass/kernel_decompose.md
- test: test/passes/test_kernel_decompose.py
- 功能实现: kernel_gen/passes/kernel_decompose.py
"""

from __future__ import annotations

from xdsl.context import Context
from xdsl.dialects import arith
from xdsl.dialects.builtin import FloatAttr, IntAttr, IntegerAttr, ModuleOp
from xdsl.ir import Operation, SSAValue
from xdsl.pattern_rewriter import (
    GreedyRewritePatternApplier,
    PatternRewriter,
    PatternRewriteWalker,
    RewritePattern,
    op_type_rewrite_pattern,
)
from xdsl.rewriter import InsertPoint

from kernel_gen.core.error import ErrorKind, ErrorModule, KernelCodeError
from kernel_gen.dialect.dma import DmaFillOp, DmaReinterpretOp, DmaReshapeOp, DmaSubviewOp, DmaViewOp
from kernel_gen.dialect.kernel import KernelMatmulFusionOp, KernelMatmulOp
from kernel_gen.dialect.symbol import SymbolForOp, SymbolNeOp
from kernel_gen.passes.common import ensure_builtin_module, verify_generated_ops
from kernel_gen.passes.pass_manager import Pass


def _kernel_decompose_error(message: str) -> KernelCodeError:
    """构造 kernel-decompose 错误。

    功能说明:
    - 统一 pass 内稳定错误短语前缀，便于 spec、pytest 与 expectation 机械匹配。
    - 空白 detail 归一为 `unknown error`，避免抛出空消息。
    - 返回 KernelCodeError，由调用点决定是否链式抛出。

    使用示例:
    - raise _kernel_decompose_error("matmul acc")
    """

    detail = message.strip()
    if not detail:
        detail = "unknown error"
    prefix = "kernel-decompose"
    text = f"{prefix} {detail}"
    return KernelCodeError(ErrorKind.CONTRACT, ErrorModule.PASS, text)


class KernelDecomposePass(Pass):
    """分解 kernel 中间聚合 op 的公开 pass。

    功能说明:
    - 将 `kernel.matmul_fusion(out,lhs,rhs,acc)` 规整为单条
      `kernel.matmul(out,lhs,rhs,acc)` 动态 acc op。
    - 不生成旧 `scf.if` 双分支，不复制 `fusion_list` metadata。
    - 对可证明安全的首轮覆盖场景删除初始 `dma.fill(out, 0)`。

    使用示例:
    - KernelDecomposePass().apply(Context(), module)
    """

    name = "kernel-decompose"

    def __init__(self, fold: bool = True) -> None:
        """初始化 kernel-decompose pass。

        功能说明:
        - 记录通用 fold 开关。
        - 第一版不接受 pass 专属 option。

        使用示例:
        - KernelDecomposePass()
        """

        super().__init__(fold=fold)

    @classmethod
    def from_options(cls, options: dict[str, str]) -> "KernelDecomposePass":
        """从 registry options 构造 pass。

        功能说明:
        - 第一版不接受自定义 option。
        - unknown option 稳定失败，错误短语包含 `kernel-decompose options`。

        使用示例:
        - KernelDecomposePass.from_options({})
        """

        if options:
            names = ", ".join(sorted(options))
            raise KernelCodeError(
                ErrorKind.CONTRACT,
                ErrorModule.PASS,
                f"kernel-decompose options unknown: {names}",
            )
        return cls()

    def apply(self, ctx: Context, module: ModuleOp) -> None:
        """执行 kernel 中间 op 分解。

        功能说明:
        - 遍历 builtin.module 中的 `kernel.matmul_fusion`。
        - 将 fusion 替换为动态 acc `kernel.matmul`。
        - 尝试按安全证明删除同 out 的 initial zero fill。

        使用示例:
        - KernelDecomposePass().apply(Context(), module)
        """

        ensure_builtin_module(module)
        PatternRewriteWalker(
            GreedyRewritePatternApplier(
                [_KernelMatmulFusionToDynamicAccPattern(module)],
                ctx=ctx,
                folding_enabled=self.fold,
                dce_enabled=False,
            ),
            apply_recursively=True,
        ).rewrite_module(module)


class _KernelMatmulFusionToDynamicAccPattern(RewritePattern):
    """kernel.matmul_fusion 到动态 acc matmul 的 pattern。"""

    def __init__(self, module: ModuleOp) -> None:
        """初始化 fusion 分解 pattern。

        功能说明:
        - 保存当前 `ModuleOp`，用于 fill 删除后的 verifier 与 rollback。
        - 不保存跨 module 状态，避免 greedy walker 多次运行共享脏状态。

        使用示例:
        - pattern = _KernelMatmulFusionToDynamicAccPattern(module)
        """

        self.module = module

    @op_type_rewrite_pattern
    def match_and_rewrite(self, fusion: KernelMatmulFusionOp, rewriter: PatternRewriter, /) -> None:
        """把 `kernel.matmul_fusion` 替换成动态 acc `kernel.matmul`。

        功能说明:
        - 生成单条 `KernelMatmulOp(..., acc=fusion.acc)`。
        - 先局部 verify 新 op，失败时报 `kernel-decompose matmul acc`。
        - 替换成功后按保守规则删除可证明安全的 initial zero fill。

        使用示例:
        - walker 运行时自动调用本方法。
        """

        matmul = KernelMatmulOp(fusion.out, fusion.lhs, fusion.rhs, fusion.space, acc=fusion.acc)
        try:
            verify_generated_ops([matmul])
        except KernelCodeError as exc:
            raise _kernel_decompose_error("matmul acc") from exc
        zero_fill = self.initial_zero_fill_for_fusion(fusion)
        rewriter.replace_matched_op([matmul], [])
        if zero_fill is not None:
            self.erase_fill_with_verify_rollback(zero_fill, rewriter)

    def initial_zero_fill_for_fusion(self, fusion: KernelMatmulFusionOp) -> DmaFillOp | None:
        """查找 fusion 可安全删除的 initial zero fill。

        功能说明:
        - 只接受 fusion 位于直接 `symbol.for` body 内的当前安全闭环。
        - 要求 loop 可证明至少执行一次，且 acc 为 `symbol.ne(iter, start)`。
        - 要求 fill 位于 loop 前同一 block，target 与 fusion.out 同 SSA，value 为精确 0。
        - 允许中间存在可追踪 NoMemoryEffect alias setup。
        - 要求 fill 与 loop 之间不存在 out alias 闭包的读写或逃逸；无法证明时返回 None。

        使用示例:
        - fill = self.initial_zero_fill_for_fusion(fusion)
        """

        owner_loop = self.owner_symbol_for(fusion)
        if owner_loop is None:
            return None
        if not self.has_positive_static_trip_count(owner_loop):
            return None
        if not self.acc_is_iter_ne_start(fusion, owner_loop):
            return None
        loop_block = owner_loop.parent_block()
        if loop_block is None:
            return None
        out_value = SSAValue.get(fusion.out)
        block_ops = list(loop_block.ops)
        loop_index = block_ops.index(owner_loop)
        aliases = self.alias_closure_before_index(block_ops, loop_index, out_value)
        if self.loop_body_before_fusion_blocks_initial_fill(fusion, owner_loop, set(aliases)):
            return None
        for index in range(loop_index - 1, -1, -1):
            op = block_ops[index]
            if not isinstance(op, DmaFillOp):
                if self.operation_blocks_alias_closure(op, aliases):
                    return None
                continue
            if SSAValue.get(op.target) is not out_value:
                if self.operation_blocks_alias_closure(op, aliases):
                    return None
                continue
            if not self.is_zero_fill_value(op):
                return None
            return op
        return None

    def loop_body_before_fusion_blocks_initial_fill(
        self,
        fusion: KernelMatmulFusionOp,
        loop: SymbolForOp,
        aliases: set[SSAValue],
    ) -> bool:
        """判断同一 loop body 内首轮覆盖前是否阻断 fill 删除。

        功能说明:
        - 只接受 fusion 是 owner `symbol.for` 直接 body 内的 op。
        - 从 body 起点扫描到 fusion 前，维护 out alias 闭包。
        - 任意读、写、逃逸、region capture 或未知 out/alias 使用都阻断删除。

        使用示例:
        - blocked = self.loop_body_before_fusion_blocks_initial_fill(fusion, loop, aliases)
        """

        body_ops = list(loop.body.block.ops)
        try:
            fusion_index = body_ops.index(fusion)
        except ValueError:
            return True
        return self.operations_before_index_block_alias_closure(body_ops, fusion_index, aliases)

    def operations_before_index_block_alias_closure(
        self,
        block_ops: list[Operation],
        end_index: int,
        aliases: set[SSAValue],
    ) -> bool:
        """扫描 block 前缀中是否存在 out alias 闭包使用。

        功能说明:
        - 按执行顺序扫描 `block_ops[:end_index]`。
        - 可识别的 DMA alias setup 会扩展 alias 闭包。
        - 其它命中闭包的 op 统一视为读写、逃逸或未知 effect。

        使用示例:
        - blocked = self.operations_before_index_block_alias_closure(ops, index, aliases)
        """

        for op in block_ops[:end_index]:
            if self.operation_blocks_alias_closure(op, aliases):
                return True
        return False

    def erase_fill_with_verify_rollback(self, fill: DmaFillOp, rewriter: PatternRewriter) -> None:
        """删除 fill 并在 module verify 失败时回滚。

        功能说明:
        - 保存原插入点、target 与 value operand。
        - 删除后运行 module verifier，失败则在原位置重建 `dma.fill`。
        - 回滚后再次 verify，若仍失败则抛出稳定 `kernel-decompose fill rollback` 错误。

        使用示例:
        - self.erase_fill_with_verify_rollback(fill, rewriter)
        """

        block = fill.parent_block()
        if block is None:
            return
        next_op = fill.next_op
        target = fill.target
        value = fill.value
        rewriter.erase_op(fill)
        try:
            verify_generated_ops([self.module])
        except KernelCodeError as exc:
            restored = DmaFillOp(target, value)
            if next_op is not None and next_op.parent_block() is block:
                insertion_point = InsertPoint.before(next_op)
            else:
                insertion_point = InsertPoint.at_end(block)
            rewriter.insert_op(restored, insertion_point)
            try:
                verify_generated_ops([self.module])
            except KernelCodeError as restore_exc:
                raise _kernel_decompose_error("fill rollback") from restore_exc

    def owner_symbol_for(self, op: Operation) -> SymbolForOp | None:
        """返回 op 所在的最近 symbol.for。

        功能说明:
        - 从当前 op 的 parent_op 向上查找。
        - 只返回最近一层 `SymbolForOp`，用于绑定 acc 的迭代变量。
        - 找不到时返回 None。

        使用示例:
        - loop = self.owner_symbol_for(fusion)
        """

        current = op.parent_op()
        while current is not None:
            if isinstance(current, SymbolForOp):
                return current
            current = current.parent_op()
        return None

    def has_positive_static_trip_count(self, loop: SymbolForOp) -> bool:
        """判断 symbol.for 是否可证明至少执行一次。

        功能说明:
        - 仅接受 iter attr 中 start/end/step 都是静态整数。
        - 当前安全闭环只支持正 step。
        - 若 end > start 且 step > 0，则至少执行一次。

        使用示例:
        - ok = self.has_positive_static_trip_count(loop)
        """

        start = self.static_int_expr(loop.iter_attr.start.expr.data)
        end = self.static_int_expr(loop.iter_attr.end.expr.data)
        step = self.static_int_expr(loop.iter_attr.step.expr.data)
        if start is None or end is None or step is None:
            return False
        return step > 0 and end > start

    def acc_is_iter_ne_start(self, fusion: KernelMatmulFusionOp, loop: SymbolForOp) -> bool:
        """判断 fusion acc 是否为 `symbol.ne(iter, start)`。

        功能说明:
        - 只按 SSA 身份判定，不按名称文本猜测。
        - lhs 必须是 loop body 第一个迭代参数。
        - rhs 必须是 loop start operand。

        使用示例:
        - ok = self.acc_is_iter_ne_start(fusion, loop)
        """

        acc_value = SSAValue.get(fusion.acc)
        owner = acc_value.owner
        if not isinstance(owner, SymbolNeOp):
            return False
        iter_arg = loop.body.block.args[0]
        return SSAValue.get(owner.lhs) is iter_arg and SSAValue.get(owner.rhs) is SSAValue.get(loop.start)

    def is_zero_fill_value(self, fill: DmaFillOp) -> bool:
        """判断 dma.fill 的 value 是否为精确零常量。

        功能说明:
        - 支持 arith.constant 的 IntegerAttr、IntAttr 与 FloatAttr。
        - 非常量、非零值或未知 attr 均视为不可删除。
        - 不推断符号表达式或运行时值。

        使用示例:
        - ok = self.is_zero_fill_value(fill)
        """

        value = SSAValue.get(fill.value)
        owner = value.owner
        if not isinstance(owner, arith.ConstantOp):
            return False
        attr = owner.value
        if isinstance(attr, IntegerAttr):
            return int(attr.value.data) == 0
        if isinstance(attr, IntAttr):
            return int(attr.data) == 0
        if isinstance(attr, FloatAttr):
            return float(attr.value.data) == 0.0
        return False

    def alias_closure_before_index(
        self, block_ops: list[Operation], end_index: int, root: SSAValue
    ) -> set[SSAValue]:
        """收集 loop 前可机械追踪的 out alias 闭包。

        功能说明:
        - 从 root memory value 出发，扫描 loop 前同 block op。
        - 只把 `dma.view/subview/reshape/reinterpret` 这类公开 NoMemoryEffect alias op 的结果加入闭包。
        - 不跨 region、不猜测未知 alias op，未知情况由后续阻断逻辑保守处理。

        使用示例:
        - aliases = self.alias_closure_before_index(block_ops, loop_index, out)
        """

        aliases = {root}
        for op in block_ops[:end_index]:
            self.extend_alias_closure(op, aliases)
        return aliases

    def extend_alias_closure(self, op: Operation, aliases: set[SSAValue]) -> bool:
        """尝试把公开 DMA alias op 的 result 加入 alias 闭包。

        功能说明:
        - 仅当 alias op 的 source 已在闭包中时扩展 result。
        - 支持 `dma.view`、`dma.subview`、`dma.reshape` 与 `dma.reinterpret`。
        - 返回值表示本 op 是否被识别为闭包内纯 alias setup。

        使用示例:
        - if self.extend_alias_closure(op, aliases): ...
        """

        if isinstance(op, DmaSubviewOp):
            sources = list(op.source)
        elif isinstance(op, (DmaViewOp, DmaReshapeOp, DmaReinterpretOp)):
            sources = [op.source]
        else:
            return False
        if len(sources) != 1 or SSAValue.get(sources[0]) not in aliases:
            return False
        for result in op.results:
            aliases.add(SSAValue.get(result))
        return True

    def operation_blocks_alias_closure(self, op: Operation, aliases: set[SSAValue]) -> bool:
        """判断 op 是否阻断 initial fill 删除。

        功能说明:
        - 闭包内纯 DMA alias setup 不阻断删除。
        - 任意其它 op 直接或嵌套使用闭包内 memory value 时视为读写、逃逸或未知 effect。
        - 不依赖 pass 外部私有 helper，保持证明逻辑局限在当前文件。

        使用示例:
        - if self.operation_blocks_alias_closure(op, aliases): return None
        """

        if self.extend_alias_closure(op, aliases):
            return False
        for nested in op.walk():
            for operand in nested.operands:
                if SSAValue.get(operand) in aliases:
                    return True
        return False

    def static_int_expr(self, expr: str) -> int | None:
        """解析静态整数 symbol 表达式。

        功能说明:
        - 接受十进制整数及前导负号。
        - 动态符号、问号和复合表达式返回 None。
        - 用于 loop trip count 的保守证明。

        使用示例:
        - value = self.static_int_expr("32")
        """

        signless = expr[1:] if expr.startswith("-") else expr
        if signless.isdecimal():
            return int(expr)
        return None


__all__ = ["KernelDecomposePass"]
