"""symbol-loop-hoist pass.


功能说明:
- 作为 `ModulePass` 实现 `symbol-loop-hoist` pass，仅处理 `symbol.for`；当 module 中不存在
  `symbol.for` 时保持 no-op。
- 把循环体内仅依赖循环外 SSA 的受支持 symbol/tuner op 外提到 `symbol.for` 之前，减少循环体内重复
  的符号常量、参数与元信息计算。
- 通过 `PatternRewriteWalker` 以单 op pattern 驱动外提到稳定态，不做通用 LICM。

API 列表:
- `class SymbolLoopHoistPass(fold: bool = True)`
- `class SymbolConstHoistPattern()`
- `SymbolConstHoistPattern.match_and_rewrite(op: SymbolConstOp, rewriter: PatternRewriter) -> None`
- `class TunerParamHoistPattern()`
- `TunerParamHoistPattern.match_and_rewrite(op: TunerParamOp, rewriter: PatternRewriter) -> None`
- `class SymbolGetDimHoistPattern()`
- `SymbolGetDimHoistPattern.match_and_rewrite(op: SymbolGetDimOp, rewriter: PatternRewriter) -> None`
- `class SymbolGetStrideHoistPattern()`
- `SymbolGetStrideHoistPattern.match_and_rewrite(op: SymbolGetStrideOp, rewriter: PatternRewriter) -> None`
- `class SymbolAddHoistPattern()`
- `SymbolAddHoistPattern.match_and_rewrite(op: SymbolAddOp, rewriter: PatternRewriter) -> None`
- `class SymbolSubHoistPattern()`
- `SymbolSubHoistPattern.match_and_rewrite(op: SymbolSubOp, rewriter: PatternRewriter) -> None`
- `class SymbolMulHoistPattern()`
- `SymbolMulHoistPattern.match_and_rewrite(op: SymbolMulOp, rewriter: PatternRewriter) -> None`
- `class SymbolDivHoistPattern()`
- `SymbolDivHoistPattern.match_and_rewrite(op: SymbolDivOp, rewriter: PatternRewriter) -> None`
- `class SymbolFloorDivHoistPattern()`
- `SymbolFloorDivHoistPattern.match_and_rewrite(op: SymbolFloorDivOp, rewriter: PatternRewriter) -> None`
- `class SymbolMinHoistPattern()`
- `SymbolMinHoistPattern.match_and_rewrite(op: SymbolMinOp, rewriter: PatternRewriter) -> None`
- `class SymbolMaxHoistPattern()`
- `SymbolMaxHoistPattern.match_and_rewrite(op: SymbolMaxOp, rewriter: PatternRewriter) -> None`
- `get_symbol_loop_hoist_patterns() -> list[RewritePattern]`

使用示例:
- from xdsl.context import Context
- from xdsl.dialects.builtin import ModuleOp
- from kernel_gen.passes.symbol_loop_hoist import SymbolLoopHoistPass
- module = ModuleOp([])
- SymbolLoopHoistPass().apply(Context(), module)

关联文件:
- spec: spec/pass/symbol_loop_hoist.md
- test: test/passes/test_symbol_loop_hoist.py
- 功能实现: kernel_gen/passes/symbol_loop_hoist.py
"""

from __future__ import annotations
from kernel_gen.core.error import ErrorKind, ErrorModule, KernelCodeError

from xdsl.context import Context
from xdsl.dialects.builtin import ModuleOp
from xdsl.ir import Block, BlockArgument, Operation, SSAValue
from xdsl.pattern_rewriter import (
    GreedyRewritePatternApplier,
    PatternRewriteWalker,
    PatternRewriter,
    RewritePattern,
    op_type_rewrite_pattern,
)
from xdsl.rewriter import InsertPoint
from xdsl.utils.exceptions import VerifyException

from kernel_gen.dialect.symbol import (
    Symbol,
    SymbolAddOp,
    SymbolConstOp,
    SymbolFloorDivOp,
    SymbolForOp,
    SymbolGetDimOp,
    SymbolGetStrideOp,
    SymbolMaxOp,
    SymbolMinOp,
    SymbolMulOp,
    SymbolSubOp,
    SymbolDivOp,
)
from kernel_gen.dialect.tuner import TunerParamOp
from kernel_gen.passes.pass_manager import Pass



def _hoist_loop_invariant_op(op: Operation, rewriter: PatternRewriter) -> None:
    """外提当前 `symbol.for` 中循环不变的候选 op。


    功能说明:
    - 仅在候选 op 位于 `symbol.for` body 内，且全部 operand 都来自当前 loop body 外部时执行外提。
    - 该 helper 只服务本文件公开 pattern，避免各 pattern 复制同一套父级与 operand 判定逻辑。

    使用示例:
    - _hoist_loop_invariant_op(op, rewriter)

    关联文件:
    - spec: spec/pass/symbol_loop_hoist.md
    - test: test/passes/test_symbol_loop_hoist.py
    - 功能实现: kernel_gen/passes/symbol_loop_hoist.py
    """

    loop_block = getattr(op, "parent_block", lambda: None)()
    if loop_block is None:
        return
    symbol_for = getattr(loop_block, "parent_op", lambda: None)()
    if not isinstance(symbol_for, SymbolForOp):
        return
    for operand in op.operands:
        value = SSAValue.get(operand)
        if isinstance(value, BlockArgument):
            if value.owner is loop_block:
                return
            continue
        owner = getattr(value, "owner", None)
        if owner is None:
            continue
        if getattr(owner, "parent_block", lambda: None)() is loop_block:
            return
    op.detach()
    rewriter.insert_op(op, InsertPoint.before(symbol_for))
    rewriter.notify_op_modified(symbol_for)


class SymbolConstHoistPattern(RewritePattern):
    """`symbol.const` 外提 pattern。

    功能说明:
    - IR before:
      ```mlir
      symbol.for %i = %c0 to %n step %c1 {
        %v = "symbol.const"() {value = 1 : i64} : () -> !symbol.int<"1">
      }
      ```
    - IR after:
      ```mlir
      %v = "symbol.const"() {value = 1 : i64} : () -> !symbol.int<"1">
      symbol.for %i = %c0 to %n step %c1 {
      }
      ```
    - no-op unchanged after：不在 `symbol.for` 直接 body 内时 before IR 保持不变。
    """

    @op_type_rewrite_pattern
    def match_and_rewrite(self, op: SymbolConstOp, rewriter: PatternRewriter, /) -> None:
        _hoist_loop_invariant_op(op, rewriter)


class TunerParamHoistPattern(RewritePattern):
    """`tuner.param` 外提 pattern。

    功能说明:
    - IR before:
      ```mlir
      symbol.for %i = %c0 to %n step %c1 {
        %tile = "tuner.param"() {name = "tile_m"} : () -> !symbol.int<"tile_m">
      }
      ```
    - IR after:
      ```mlir
      %tile = "tuner.param"() {name = "tile_m"} : () -> !symbol.int<"tile_m">
      symbol.for %i = %c0 to %n step %c1 {
      }
      ```
    - no-op unchanged after：依赖 loop-local 值时 before IR 保持不变。
    """

    @op_type_rewrite_pattern
    def match_and_rewrite(self, op: TunerParamOp, rewriter: PatternRewriter, /) -> None:
        _hoist_loop_invariant_op(op, rewriter)


class SymbolGetDimHoistPattern(RewritePattern):
    """`symbol.get_dim` 外提 pattern。

    功能说明:
    - IR before:
      ```mlir
      symbol.for %i = %c0 to %n step %c1 {
        %d = "symbol.get_dim"(%mem) {axis = 0 : i64} : (value) -> !symbol.int<"N">
      }
      ```
    - IR after:
      ```mlir
      %d = "symbol.get_dim"(%mem) {axis = 0 : i64} : (value) -> !symbol.int<"N">
      symbol.for %i = %c0 to %n step %c1 {
      }
      ```
    - no-op unchanged after：`%mem` 由当前 loop body 生产时 before IR 保持不变。
    """

    @op_type_rewrite_pattern
    def match_and_rewrite(self, op: SymbolGetDimOp, rewriter: PatternRewriter, /) -> None:
        _hoist_loop_invariant_op(op, rewriter)


class SymbolGetStrideHoistPattern(RewritePattern):
    """`symbol.get_stride` 外提 pattern。

    功能说明:
    - IR before:
      ```mlir
      symbol.for %i = %c0 to %n step %c1 {
        %s = "symbol.get_stride"(%mem) {axis = 1 : i64} : (value) -> !symbol.int<"S">
      }
      ```
    - IR after:
      ```mlir
      %s = "symbol.get_stride"(%mem) {axis = 1 : i64} : (value) -> !symbol.int<"S">
      symbol.for %i = %c0 to %n step %c1 {
      }
      ```
    - no-op unchanged after：`%mem` 由当前 loop body 生产时 before IR 保持不变。
    """

    @op_type_rewrite_pattern
    def match_and_rewrite(self, op: SymbolGetStrideOp, rewriter: PatternRewriter, /) -> None:
        _hoist_loop_invariant_op(op, rewriter)


class SymbolAddHoistPattern(RewritePattern):
    """`symbol.add` 外提 pattern。

    功能说明:
    - IR before:
      ```mlir
      symbol.for %i = %c0 to %n step %c1 {
        %v = "symbol.add"(%a, %b) : (!symbol.int<"A">, !symbol.int<"B">) -> !symbol.int<"A+B">
      }
      ```
    - IR after:
      ```mlir
      %v = "symbol.add"(%a, %b) : (!symbol.int<"A">, !symbol.int<"B">) -> !symbol.int<"A+B">
      symbol.for %i = %c0 to %n step %c1 {
      }
      ```
    - no-op unchanged after：任一 operand 来自当前 loop body 时 before IR 保持不变。
    """

    @op_type_rewrite_pattern
    def match_and_rewrite(self, op: SymbolAddOp, rewriter: PatternRewriter, /) -> None:
        _hoist_loop_invariant_op(op, rewriter)


class SymbolSubHoistPattern(RewritePattern):
    """`symbol.sub` 外提 pattern。

    功能说明:
    - IR before:
      ```mlir
      symbol.for %i = %c0 to %n step %c1 {
        %v = "symbol.sub"(%a, %b) : (!symbol.int<"A">, !symbol.int<"B">) -> !symbol.int<"A-B">
      }
      ```
    - IR after:
      ```mlir
      %v = "symbol.sub"(%a, %b) : (!symbol.int<"A">, !symbol.int<"B">) -> !symbol.int<"A-B">
      symbol.for %i = %c0 to %n step %c1 {
      }
      ```
    - no-op unchanged after：任一 operand 来自当前 loop body 时 before IR 保持不变。
    """

    @op_type_rewrite_pattern
    def match_and_rewrite(self, op: SymbolSubOp, rewriter: PatternRewriter, /) -> None:
        _hoist_loop_invariant_op(op, rewriter)


class SymbolMulHoistPattern(RewritePattern):
    """`symbol.mul` 外提 pattern。

    功能说明:
    - IR before:
      ```mlir
      symbol.for %i = %c0 to %n step %c1 {
        %v = "symbol.mul"(%a, %b) : (!symbol.int<"A">, !symbol.int<"B">) -> !symbol.int<"A*B">
      }
      ```
    - IR after:
      ```mlir
      %v = "symbol.mul"(%a, %b) : (!symbol.int<"A">, !symbol.int<"B">) -> !symbol.int<"A*B">
      symbol.for %i = %c0 to %n step %c1 {
      }
      ```
    - no-op unchanged after：任一 operand 来自当前 loop body 时 before IR 保持不变。
    """

    @op_type_rewrite_pattern
    def match_and_rewrite(self, op: SymbolMulOp, rewriter: PatternRewriter, /) -> None:
        _hoist_loop_invariant_op(op, rewriter)


class SymbolDivHoistPattern(RewritePattern):
    """`symbol.div` 外提 pattern。

    功能说明:
    - IR before:
      ```mlir
      symbol.for %i = %c0 to %n step %c1 {
        %v = "symbol.div"(%a, %b) : (!symbol.int<"A">, !symbol.int<"B">) -> !symbol.int<"A/B">
      }
      ```
    - IR after:
      ```mlir
      %v = "symbol.div"(%a, %b) : (!symbol.int<"A">, !symbol.int<"B">) -> !symbol.int<"A/B">
      symbol.for %i = %c0 to %n step %c1 {
      }
      ```
    - no-op unchanged after：任一 operand 来自当前 loop body 时 before IR 保持不变。
    """

    @op_type_rewrite_pattern
    def match_and_rewrite(self, op: SymbolDivOp, rewriter: PatternRewriter, /) -> None:
        _hoist_loop_invariant_op(op, rewriter)


class SymbolFloorDivHoistPattern(RewritePattern):
    """`symbol.floordiv` 外提 pattern。

    功能说明:
    - IR before:
      ```mlir
      symbol.for %i = %c0 to %n step %c1 {
        %v = "symbol.floordiv"(%a, %b) : (!symbol.int<"A">, !symbol.int<"B">) -> !symbol.int<"A//B">
      }
      ```
    - IR after:
      ```mlir
      %v = "symbol.floordiv"(%a, %b) : (!symbol.int<"A">, !symbol.int<"B">) -> !symbol.int<"A//B">
      symbol.for %i = %c0 to %n step %c1 {
      }
      ```
    - no-op unchanged after：任一 operand 来自当前 loop body 时 before IR 保持不变。
    """

    @op_type_rewrite_pattern
    def match_and_rewrite(self, op: SymbolFloorDivOp, rewriter: PatternRewriter, /) -> None:
        _hoist_loop_invariant_op(op, rewriter)


class SymbolMinHoistPattern(RewritePattern):
    """`symbol.min` 外提 pattern。


    功能说明:
    - 对 loop-invariant 的 `symbol.min` 应用与其它 symbol 算术 op 相同的一层外提规则。
    - 任一 operand 来自当前 loop body、loop iterator 或 loop-carried 值时保持 no-op。
    - IR before:
      ```mlir
      symbol.for %i = %c0 to %n step %c1 {
        %v = "symbol.min"(%a, %b) : (!symbol.int<"A">, !symbol.int<"B">) -> !symbol.int<"min(A,B)">
      }
      ```
    - IR after:
      ```mlir
      %v = "symbol.min"(%a, %b) : (!symbol.int<"A">, !symbol.int<"B">) -> !symbol.int<"min(A,B)">
      symbol.for %i = %c0 to %n step %c1 {
      }
      ```
    - no-op unchanged after：任一 operand 来自当前 loop body 时 before IR 保持不变。

    使用示例:
    - pattern = SymbolMinHoistPattern()

    关联文件:
    - spec: spec/pass/symbol_loop_hoist.md
    - test: test/passes/test_symbol_loop_hoist.py
    - 功能实现: kernel_gen/passes/symbol_loop_hoist.py
    """

    @op_type_rewrite_pattern
    def match_and_rewrite(self, op: SymbolMinOp, rewriter: PatternRewriter, /) -> None:
        _hoist_loop_invariant_op(op, rewriter)


class SymbolMaxHoistPattern(RewritePattern):
    """`symbol.max` 外提 pattern。


    功能说明:
    - 对 loop-invariant 的 `symbol.max` 应用与其它 symbol 算术 op 相同的一层外提规则。
    - 任一 operand 来自当前 loop body、loop iterator 或 loop-carried 值时保持 no-op。
    - IR before:
      ```mlir
      symbol.for %i = %c0 to %n step %c1 {
        %v = "symbol.max"(%a, %b) : (!symbol.int<"A">, !symbol.int<"B">) -> !symbol.int<"max(A,B)">
      }
      ```
    - IR after:
      ```mlir
      %v = "symbol.max"(%a, %b) : (!symbol.int<"A">, !symbol.int<"B">) -> !symbol.int<"max(A,B)">
      symbol.for %i = %c0 to %n step %c1 {
      }
      ```
    - no-op unchanged after：任一 operand 来自当前 loop body 时 before IR 保持不变。

    使用示例:
    - pattern = SymbolMaxHoistPattern()

    关联文件:
    - spec: spec/pass/symbol_loop_hoist.md
    - test: test/passes/test_symbol_loop_hoist.py
    - 功能实现: kernel_gen/passes/symbol_loop_hoist.py
    """

    @op_type_rewrite_pattern
    def match_and_rewrite(self, op: SymbolMaxOp, rewriter: PatternRewriter, /) -> None:
        _hoist_loop_invariant_op(op, rewriter)


def get_symbol_loop_hoist_patterns() -> list[RewritePattern]:
    """返回 `symbol-loop-hoist` pass 使用的公开 pattern 列表。


    功能说明:
    - 以“每种受支持 op 一个 pattern”的形式公开当前 pass 的 pattern 列表。
    - 当前只覆盖 `symbol.const`、`tuner.param`、`symbol.get_dim/get_stride` 与
      `symbol.add/sub/mul/div/floordiv/min/max`。

    使用示例:
    - `patterns = get_symbol_loop_hoist_patterns()`

    关联文件:
    - spec: spec/pass/symbol_loop_hoist.md
    - test: test/passes/test_symbol_loop_hoist.py
    - 功能实现: kernel_gen/passes/symbol_loop_hoist.py
    """

    return [
        SymbolConstHoistPattern(),
        TunerParamHoistPattern(),
        SymbolGetDimHoistPattern(),
        SymbolGetStrideHoistPattern(),
        SymbolAddHoistPattern(),
        SymbolSubHoistPattern(),
        SymbolMulHoistPattern(),
        SymbolDivHoistPattern(),
        SymbolFloorDivHoistPattern(),
        SymbolMinHoistPattern(),
        SymbolMaxHoistPattern(),
    ]


class SymbolLoopHoistPass(Pass):
    """symbol-loop-hoist pass。


    功能说明:
    - 作为 `ModulePass` 通过 pattern 驱动遍历 module 中的 `symbol.for` 并外提循环 invariant 的对象。
    - 若 module 中不存在 `symbol.for`，则直接 no-op 并通过 `module.verify()`。
    - 在最终 `module.verify()` 失败时统一转译为 `SymbolLoopHoistVerifierError`。

    使用示例:
    - from xdsl.context import Context
    - module = ModuleOp([])
    - SymbolLoopHoistPass().apply(Context(), module)

    关联文件:
    - spec: spec/pass/symbol_loop_hoist.md
    - test: test/passes/test_symbol_loop_hoist.py
    - 功能实现: kernel_gen/passes/symbol_loop_hoist.py
    """

    name = "symbol-loop-hoist"

    def apply(self: "SymbolLoopHoistPass", ctx: Context, module: ModuleOp) -> None:
        """执行 symbol-loop-hoist ModulePass。


        功能说明:
        - 通过 `PatternRewriteWalker` 以单 op pattern 驱动 `symbol.for` 外提。
        - 依赖 greedy walker 把链式候选推进到稳定态。
        - 在最终 `module.verify()` 失败时统一转译为 `SymbolLoopHoistVerifierError`。

        使用示例:
        - from xdsl.context import Context
        - from xdsl.dialects.builtin import ModuleOp
        - module = ModuleOp([])
        - SymbolLoopHoistPass().apply(Context(), module)

        关联文件:
        - spec: spec/pass/symbol_loop_hoist.md
        - test: test/passes/test_symbol_loop_hoist.py
        - 功能实现: kernel_gen/passes/symbol_loop_hoist.py
        """

        if ctx.get_optional_dialect(Symbol.name) is None:
            ctx.load_dialect(Symbol)
        PatternRewriteWalker(
            GreedyRewritePatternApplier(
                get_symbol_loop_hoist_patterns(),
                ctx=ctx,
                folding_enabled=self.fold,
                dce_enabled=False,
            )
        ).rewrite_module(module)
        try:
            module.verify()
        except VerifyException as exc:
            raise KernelCodeError(ErrorKind.CONTRACT, ErrorModule.PASS, f"SymbolLoopHoistVerifierError: {exc}") from exc

__all__ = [
    "SymbolLoopHoistPass",
    "SymbolConstHoistPattern",
    "TunerParamHoistPattern",
    "SymbolGetDimHoistPattern",
    "SymbolGetStrideHoistPattern",
    "SymbolAddHoistPattern",
    "SymbolSubHoistPattern",
    "SymbolMulHoistPattern",
    "SymbolDivHoistPattern",
    "SymbolFloorDivHoistPattern",
    "SymbolMinHoistPattern",
    "SymbolMaxHoistPattern",
    "get_symbol_loop_hoist_patterns",
]
