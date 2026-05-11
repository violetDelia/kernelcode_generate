"""DSL AST kernel operation nodes.


功能说明:
- 定义 `kernel_gen.operation.kernel` out-first helper 的 AST 节点。
- 节点发射到既有 `kernel` dialect op，不生成不存在的 `kernel.add` 等具名 op。

API 列表:
- `KernelBinaryElewiseAST(out: ValueAST, lhs: ValueAST, rhs: ValueAST, kind: KernelBinaryElewiseKind, location: SourceLocation | None = None)`
- `KernelAddAST(out: ValueAST, lhs: ValueAST, rhs: ValueAST, location: SourceLocation | None = None)`
- `KernelSubAST(out: ValueAST, lhs: ValueAST, rhs: ValueAST, location: SourceLocation | None = None)`
- `KernelMulAST(out: ValueAST, lhs: ValueAST, rhs: ValueAST, location: SourceLocation | None = None)`
- `KernelDivAST(out: ValueAST, lhs: ValueAST, rhs: ValueAST, location: SourceLocation | None = None)`
- `KernelTrueDivAST(out: ValueAST, lhs: ValueAST, rhs: ValueAST, location: SourceLocation | None = None)`
- `KernelEqAST(out: ValueAST, lhs: ValueAST, rhs: ValueAST, location: SourceLocation | None = None)`
- `KernelNeAST(out: ValueAST, lhs: ValueAST, rhs: ValueAST, location: SourceLocation | None = None)`
- `KernelLtAST(out: ValueAST, lhs: ValueAST, rhs: ValueAST, location: SourceLocation | None = None)`
- `KernelLeAST(out: ValueAST, lhs: ValueAST, rhs: ValueAST, location: SourceLocation | None = None)`
- `KernelGtAST(out: ValueAST, lhs: ValueAST, rhs: ValueAST, location: SourceLocation | None = None)`
- `KernelGeAST(out: ValueAST, lhs: ValueAST, rhs: ValueAST, location: SourceLocation | None = None)`
- `KernelExpAST(out: ValueAST, input_value: ValueAST, location: SourceLocation | None = None)`
- `KernelReduceAST(out: ValueAST, input_value: ValueAST, kind: KernelReduceKind, axis: int, keepdim: bool = False, location: SourceLocation | None = None)`
- `KernelMatmulAST(out: ValueAST, lhs: ValueAST, rhs: ValueAST, location: SourceLocation | None = None)`
- `KernelImg2Col1dAST(out: ValueAST, input_value: ValueAST, k: ValueAST, s: ValueAST | None = None, d: ValueAST | None = None, p_left: ValueAST | None = None, p_right: ValueAST | None = None, location: SourceLocation | None = None)`
- `KernelImg2Col2dAST(out: ValueAST, input_value: ValueAST, kh: ValueAST, kw: ValueAST, sh: ValueAST | None = None, sw: ValueAST | None = None, dh: ValueAST | None = None, dw: ValueAST | None = None, ph: ValueAST | None = None, pw: ValueAST | None = None, pl: ValueAST | None = None, pr: ValueAST | None = None, location: SourceLocation | None = None)`

使用示例:
- from kernel_gen.dsl.ast.nodes.kernel import KernelMatmulAST

关联文件:
- spec: spec/dsl/ast/nodes/kernel.md
- test: test/dsl/ast/nodes/test_kernel.py
- 功能实现: kernel_gen/dsl/ast/nodes/kernel.py
"""

from __future__ import annotations

from dataclasses import dataclass

from xdsl.context import Context
from xdsl.ir import Block, Operation, SSAValue

from kernel_gen.core.error import ErrorKind, ErrorModule, KernelCodeError
from kernel_gen.dialect.kernel import (
    KernelBinaryElewiseOp,
    KernelExpOp,
    KernelImg2col1dOp,
    KernelImg2col2dOp,
    KernelMatmulOp,
    KernelReduceOp,
)
from kernel_gen.dialect.nn import NnMemoryType
from kernel_gen.dialect.symbol import SymbolValueType
from kernel_gen.operation import kernel as kernel_ops
from kernel_gen.operation.kernel import KernelBinaryElewiseKind, KernelReduceKind
from kernel_gen.symbol_variable.memory import Memory
from kernel_gen.symbol_variable.symbol_dim import SymbolDim
from .attr import EmitMlirResult, SourceLocation
from .basic import MemoryAST, StatementAST, ValueAST
from .symbol import ConstValueAST


def _as_value_ast(value: ValueAST, location: SourceLocation | None) -> ValueAST:
    """规整 AST 输入。

    功能说明:
    - 允许 builder 传入常量或已有 ValueAST，并统一转成 ValueAST。

    使用示例:
    - node = _as_value_ast(value, location)
    """

    return value if isinstance(value, ValueAST) else ConstValueAST(value, location=location)


def _emit_ssa_value(node: ValueAST, ctx: Context, block: Block) -> SSAValue:
    """发射节点并返回 SSAValue。

    功能说明:
    - 若节点发射出 Operation，先加入当前 block，再取首个 result。
    - out-first kernel 语句所有 operand 都必须 lower 为 SSA value。

    使用示例:
    - value = _emit_ssa_value(node, ctx, block)
    """

    emitted = node.emit_mlir(ctx, block)
    if isinstance(emitted, Operation):
        block.add_op(emitted)
        if not emitted.results:
            raise KernelCodeError(ErrorKind.CONTRACT, ErrorModule.MLIR_GEN, "kernel operand operation has no result")
        return emitted.results[0]
    if not isinstance(emitted, SSAValue):
        raise KernelCodeError(ErrorKind.CONTRACT, ErrorModule.MLIR_GEN, "kernel operands must lower to SSA values")
    return emitted


def _ensure_memory_ssa(value: SSAValue, name: str) -> NnMemoryType:
    """校验 SSA value 是 nn.memory。

    功能说明:
    - kernel dialect op 当前只接受 `NnMemoryType` operand。

    使用示例:
    - memory_type = _ensure_memory_ssa(out, "out")
    """

    if not isinstance(value.type, NnMemoryType):
        raise KernelCodeError(ErrorKind.CONTRACT, ErrorModule.MLIR_GEN, f"kernel {name} must lower to nn.memory")
    return value.type


def _emit_symbol_operand(node: ValueAST, ctx: Context, block: Block) -> SSAValue:
    """发射 symbol 参数 operand。

    功能说明:
    - img2col 窗口参数必须 lower 为 `!symbol.int`。

    使用示例:
    - operand = _emit_symbol_operand(self.kh, ctx, block)
    """

    value = _emit_ssa_value(node, ctx, block)
    if not isinstance(value.type, SymbolValueType):
        raise KernelCodeError(ErrorKind.CONTRACT, ErrorModule.MLIR_GEN, "kernel img2col parameter must lower to symbol.int")
    return value


def _result_symbol(node: ValueAST) -> int | SymbolDim | None:
    """读取节点的公开 symbol 结果。

    功能说明:
    - 支持 ConstValueAST 与 SymbolDimAST 等公开 ValueAST 结果。

    使用示例:
    - value = _result_symbol(self.kh)
    """

    return node.result_symbol()


def _require_memory(node: ValueAST, name: str) -> Memory:
    """读取节点的解析期 Memory。

    功能说明:
    - operation.kernel 直接调用前需要可用的公开 Memory 语义。

    使用示例:
    - out = _require_memory(self.out, "out")
    """

    memory = node.result_memory()
    if not isinstance(memory, Memory):
        raise KernelCodeError(ErrorKind.CONTRACT, ErrorModule.MLIR_GEN, f"kernel {name} memory is unavailable")
    return memory


def _require_symbol(node: ValueAST, name: str) -> int | SymbolDim:
    """读取节点的解析期 symbol 参数。

    功能说明:
    - img2col 参数必须是 int 或 SymbolDim。

    使用示例:
    - kh = _require_symbol(self.kh, "kh")
    """

    value = _result_symbol(node)
    if isinstance(value, (int, SymbolDim)):
        return value
    raise KernelCodeError(ErrorKind.CONTRACT, ErrorModule.MLIR_GEN, f"kernel {name} parameter is unavailable")


@dataclass
class KernelBinaryElewiseAST(StatementAST):
    """kernel.binary_elewise AST 节点。

    功能说明:
    - 承载显式 `binary_elewise(..., kind=...)` 调用。

    使用示例:
    - KernelBinaryElewiseAST(out, lhs, rhs, KernelBinaryElewiseKind.ADD)
    """

    out: ValueAST
    lhs: ValueAST
    rhs: ValueAST
    kind: KernelBinaryElewiseKind
    location: SourceLocation | None = None

    def __post_init__(self) -> None:
        self.out = _as_value_ast(self.out, self.location)
        self.lhs = _as_value_ast(self.lhs, self.location)
        self.rhs = _as_value_ast(self.rhs, self.location)
        if not isinstance(self.kind, KernelBinaryElewiseKind):
            raise KernelCodeError(ErrorKind.CONTRACT, ErrorModule.MLIR_GEN, "kernel.binary_elewise kind must be KernelBinaryElewiseKind")

    def emit_mlir(self, ctx: Context, block: Block | None = None) -> EmitMlirResult:
        """发射 kernel.binary_elewise。

        功能说明:
        - out/lhs/rhs lower 为 memory operand。
        - `kernel.add` 等 helper 统一 lower 到 `kernel.binary_elewise(kind=...)`。

        使用示例:
        - op = node.emit_mlir(ctx, block)
        """

        assert isinstance(ctx, Context)
        assert isinstance(block, Block)
        out_memory = _require_memory(self.out, "out")
        lhs_memory = _require_memory(self.lhs, "lhs")
        rhs_memory = _require_memory(self.rhs, "rhs")
        kernel_ops.binary_elewise(out_memory, lhs_memory, rhs_memory, kind=self.kind)
        out_value = _emit_ssa_value(self.out, ctx, block)
        lhs_value = _emit_ssa_value(self.lhs, ctx, block)
        rhs_value = _emit_ssa_value(self.rhs, ctx, block)
        out_type = _ensure_memory_ssa(out_value, "out")
        _ensure_memory_ssa(lhs_value, "lhs")
        _ensure_memory_ssa(rhs_value, "rhs")
        return KernelBinaryElewiseOp(out_value, lhs_value, rhs_value, kind=self.kind.value, space=out_type.space)


@dataclass(init=False)
class _FixedKernelBinaryElewiseAST(KernelBinaryElewiseAST):
    """固定 kind 的 kernel.binary_elewise AST 基类。

    功能说明:
    - 给 `kernel.add/sub/...` 公开 helper 提供独立 AST 类型，满足 builtin 注册表一 op 一节点约束。

    使用示例:
    - KernelAddAST(out, lhs, rhs)
    """

    KIND: KernelBinaryElewiseKind = KernelBinaryElewiseKind.ADD

    def __init__(
        self,
        out: ValueAST,
        lhs: ValueAST,
        rhs: ValueAST,
        location: SourceLocation | None = None,
    ) -> None:
        super().__init__(out, lhs, rhs, self.KIND, location=location)


class KernelAddAST(_FixedKernelBinaryElewiseAST):
    """kernel.add AST 节点。

    功能说明:
    - 固定 lower 为 `kernel.binary_elewise(kind=add)`。

    使用示例:
    - KernelAddAST(out, lhs, rhs)
    """

    KIND = KernelBinaryElewiseKind.ADD


class KernelSubAST(_FixedKernelBinaryElewiseAST):
    """kernel.sub AST 节点。

    功能说明:
    - 固定 lower 为 `kernel.binary_elewise(kind=sub)`。

    使用示例:
    - KernelSubAST(out, lhs, rhs)
    """

    KIND = KernelBinaryElewiseKind.SUB


class KernelMulAST(_FixedKernelBinaryElewiseAST):
    """kernel.mul AST 节点。

    功能说明:
    - 固定 lower 为 `kernel.binary_elewise(kind=mul)`。

    使用示例:
    - KernelMulAST(out, lhs, rhs)
    """

    KIND = KernelBinaryElewiseKind.MUL


class KernelDivAST(_FixedKernelBinaryElewiseAST):
    """kernel.div AST 节点。

    功能说明:
    - 固定 lower 为 `kernel.binary_elewise(kind=div)`。

    使用示例:
    - KernelDivAST(out, lhs, rhs)
    """

    KIND = KernelBinaryElewiseKind.DIV


class KernelTrueDivAST(_FixedKernelBinaryElewiseAST):
    """kernel.truediv AST 节点。

    功能说明:
    - 固定 lower 为 `kernel.binary_elewise(kind=truediv)`。

    使用示例:
    - KernelTrueDivAST(out, lhs, rhs)
    """

    KIND = KernelBinaryElewiseKind.TRUEDIV


class KernelEqAST(_FixedKernelBinaryElewiseAST):
    """kernel.eq AST 节点。

    功能说明:
    - 固定 lower 为 `kernel.binary_elewise(kind=eq)`。

    使用示例:
    - KernelEqAST(out, lhs, rhs)
    """

    KIND = KernelBinaryElewiseKind.EQ


class KernelNeAST(_FixedKernelBinaryElewiseAST):
    """kernel.ne AST 节点。

    功能说明:
    - 固定 lower 为 `kernel.binary_elewise(kind=ne)`。

    使用示例:
    - KernelNeAST(out, lhs, rhs)
    """

    KIND = KernelBinaryElewiseKind.NE


class KernelLtAST(_FixedKernelBinaryElewiseAST):
    """kernel.lt AST 节点。

    功能说明:
    - 固定 lower 为 `kernel.binary_elewise(kind=lt)`。

    使用示例:
    - KernelLtAST(out, lhs, rhs)
    """

    KIND = KernelBinaryElewiseKind.LT


class KernelLeAST(_FixedKernelBinaryElewiseAST):
    """kernel.le AST 节点。

    功能说明:
    - 固定 lower 为 `kernel.binary_elewise(kind=le)`。

    使用示例:
    - KernelLeAST(out, lhs, rhs)
    """

    KIND = KernelBinaryElewiseKind.LE


class KernelGtAST(_FixedKernelBinaryElewiseAST):
    """kernel.gt AST 节点。

    功能说明:
    - 固定 lower 为 `kernel.binary_elewise(kind=gt)`。

    使用示例:
    - KernelGtAST(out, lhs, rhs)
    """

    KIND = KernelBinaryElewiseKind.GT


class KernelGeAST(_FixedKernelBinaryElewiseAST):
    """kernel.ge AST 节点。

    功能说明:
    - 固定 lower 为 `kernel.binary_elewise(kind=ge)`。

    使用示例:
    - KernelGeAST(out, lhs, rhs)
    """

    KIND = KernelBinaryElewiseKind.GE


@dataclass
class KernelExpAST(StatementAST):
    """kernel.exp AST 节点。

    功能说明:
    - 承载 out-first `kernel.exp(out, input_value)` 调用。

    使用示例:
    - KernelExpAST(out, input_value)
    """

    out: ValueAST
    input_value: ValueAST
    location: SourceLocation | None = None

    def __post_init__(self) -> None:
        self.out = _as_value_ast(self.out, self.location)
        self.input_value = _as_value_ast(self.input_value, self.location)

    def emit_mlir(self, ctx: Context, block: Block | None = None) -> EmitMlirResult:
        """发射 kernel.exp。

        功能说明:
        - out/input lower 为 memory operand。
        - 生成 `kernel.exp` dialect op，返回无结果 Operation。

        使用示例:
        - op = node.emit_mlir(ctx, block)
        """

        assert isinstance(ctx, Context)
        assert isinstance(block, Block)
        kernel_ops.exp(_require_memory(self.out, "out"), _require_memory(self.input_value, "input"))
        out_value = _emit_ssa_value(self.out, ctx, block)
        input_value = _emit_ssa_value(self.input_value, ctx, block)
        out_type = _ensure_memory_ssa(out_value, "out")
        _ensure_memory_ssa(input_value, "input")
        return KernelExpOp(input_value, out_value, out_type.space)


@dataclass
class KernelReduceAST(StatementAST):
    """kernel.reduce AST 节点。

    功能说明:
    - 承载 out-first `kernel.reduce(out, input_value, kind=..., axis=..., keepdim=...)` 调用。

    使用示例:
    - KernelReduceAST(out, input_value, KernelReduceKind.SUM, axis=1, keepdim=True)
    """

    out: ValueAST
    input_value: ValueAST
    kind: KernelReduceKind
    axis: int
    keepdim: bool = False
    location: SourceLocation | None = None

    def __post_init__(self) -> None:
        self.out = _as_value_ast(self.out, self.location)
        self.input_value = _as_value_ast(self.input_value, self.location)
        if not isinstance(self.kind, KernelReduceKind):
            raise KernelCodeError(ErrorKind.CONTRACT, ErrorModule.MLIR_GEN, "kernel.reduce kind must be KernelReduceKind")
        if isinstance(self.axis, bool) or not isinstance(self.axis, int):
            raise KernelCodeError(ErrorKind.CONTRACT, ErrorModule.MLIR_GEN, "kernel.reduce axis must be int")
        if not isinstance(self.keepdim, bool):
            raise KernelCodeError(ErrorKind.CONTRACT, ErrorModule.MLIR_GEN, "kernel.reduce keepdim must be bool")

    def emit_mlir(self, ctx: Context, block: Block | None = None) -> EmitMlirResult:
        """发射 kernel.reduce。

        功能说明:
        - out/input lower 为 memory operand。
        - kind/axis/keepdim lower 为 kernel.reduce attrs。

        使用示例:
        - op = node.emit_mlir(ctx, block)
        """

        assert isinstance(ctx, Context)
        assert isinstance(block, Block)
        kernel_ops.reduce(
            _require_memory(self.out, "out"),
            _require_memory(self.input_value, "input"),
            kind=self.kind,
            axis=self.axis,
            keepdim=self.keepdim,
        )
        out_value = _emit_ssa_value(self.out, ctx, block)
        input_value = _emit_ssa_value(self.input_value, ctx, block)
        out_type = _ensure_memory_ssa(out_value, "out")
        _ensure_memory_ssa(input_value, "input")
        return KernelReduceOp(
            out_value,
            input_value,
            kind=self.kind.value,
            axis=self.axis,
            keepdim=self.keepdim,
            space=out_type.space,
        )


@dataclass
class KernelMatmulAST(StatementAST):
    """kernel.matmul AST 节点。

    功能说明:
    - 承载 out-first `kernel.matmul(out, lhs, rhs)` 调用。

    使用示例:
    - KernelMatmulAST(out, lhs, rhs)
    """

    out: ValueAST
    lhs: ValueAST
    rhs: ValueAST
    location: SourceLocation | None = None

    def __post_init__(self) -> None:
        self.out = _as_value_ast(self.out, self.location)
        self.lhs = _as_value_ast(self.lhs, self.location)
        self.rhs = _as_value_ast(self.rhs, self.location)

    def emit_mlir(self, ctx: Context, block: Block | None = None) -> EmitMlirResult:
        """发射 kernel.matmul。

        功能说明:
        - 校验 out/lhs/rhs 公开 Memory 合同。
        - 生成 `kernel.matmul` dialect op，返回无结果 Operation。

        使用示例:
        - op = node.emit_mlir(ctx, block)
        """

        assert isinstance(ctx, Context)
        assert isinstance(block, Block)
        kernel_ops.matmul(_require_memory(self.out, "out"), _require_memory(self.lhs, "lhs"), _require_memory(self.rhs, "rhs"))
        out_value = _emit_ssa_value(self.out, ctx, block)
        lhs_value = _emit_ssa_value(self.lhs, ctx, block)
        rhs_value = _emit_ssa_value(self.rhs, ctx, block)
        out_type = _ensure_memory_ssa(out_value, "out")
        _ensure_memory_ssa(lhs_value, "lhs")
        _ensure_memory_ssa(rhs_value, "rhs")
        return KernelMatmulOp(out_value, lhs_value, rhs_value, out_type.space)


@dataclass(init=False)
class KernelImg2Col1dAST(StatementAST):
    """kernel.img2col1d AST 节点。

    功能说明:
    - 承载 out-first `kernel.img2col1d(...)` 调用。

    使用示例:
    - KernelImg2Col1dAST(out, input_value, k)
    """

    out: ValueAST
    input_value: ValueAST
    k: ValueAST
    s: ValueAST
    d: ValueAST
    p_left: ValueAST
    p_right: ValueAST
    location: SourceLocation | None = None

    def __init__(
        self,
        out: ValueAST,
        input_value: ValueAST,
        k: ValueAST,
        s: ValueAST | None = None,
        d: ValueAST | None = None,
        p_left: ValueAST | None = None,
        p_right: ValueAST | None = None,
        location: SourceLocation | None = None,
    ) -> None:
        self.out = _as_value_ast(out, location)
        self.input_value = _as_value_ast(input_value, location)
        self.k = _as_value_ast(k, location)
        self.s = _as_value_ast(s if s is not None else ConstValueAST(1), location)
        self.d = _as_value_ast(d if d is not None else ConstValueAST(1), location)
        self.p_left = _as_value_ast(p_left if p_left is not None else ConstValueAST(0), location)
        self.p_right = _as_value_ast(p_right if p_right is not None else ConstValueAST(0), location)
        self.location = location

    def emit_mlir(self, ctx: Context, block: Block | None = None) -> EmitMlirResult:
        """发射 kernel.img2col1d。

        功能说明:
        - out/input lower 为 memory operand。
        - k/s/d/padding lower 为 symbol operand。

        使用示例:
        - op = node.emit_mlir(ctx, block)
        """

        assert isinstance(ctx, Context)
        assert isinstance(block, Block)
        kernel_ops.img2col1d(
            _require_memory(self.out, "out"),
            _require_memory(self.input_value, "input"),
            _require_symbol(self.k, "k"),
            _require_symbol(self.s, "s"),
            _require_symbol(self.d, "d"),
            _require_symbol(self.p_left, "p_left"),
            _require_symbol(self.p_right, "p_right"),
        )
        out_value = _emit_ssa_value(self.out, ctx, block)
        input_value = _emit_ssa_value(self.input_value, ctx, block)
        k_value = _emit_symbol_operand(self.k, ctx, block)
        s_value = _emit_symbol_operand(self.s, ctx, block)
        d_value = _emit_symbol_operand(self.d, ctx, block)
        p_left_value = _emit_symbol_operand(self.p_left, ctx, block)
        p_right_value = _emit_symbol_operand(self.p_right, ctx, block)
        out_type = _ensure_memory_ssa(out_value, "out")
        _ensure_memory_ssa(input_value, "input")
        return KernelImg2col1dOp(out_value, input_value, k_value, s_value, d_value, p_left_value, p_right_value, out_type.space)


@dataclass(init=False)
class KernelImg2Col2dAST(StatementAST):
    """kernel.img2col2d AST 节点。

    功能说明:
    - 承载 out-first `kernel.img2col2d(...)` 调用。

    使用示例:
    - KernelImg2Col2dAST(out, input_value, kh, kw)
    """

    out: ValueAST
    input_value: ValueAST
    kh: ValueAST
    kw: ValueAST
    sh: ValueAST
    sw: ValueAST
    dh: ValueAST
    dw: ValueAST
    ph: ValueAST
    pw: ValueAST
    pl: ValueAST
    pr: ValueAST
    location: SourceLocation | None = None

    def __init__(
        self,
        out: ValueAST,
        input_value: ValueAST,
        kh: ValueAST,
        kw: ValueAST,
        sh: ValueAST | None = None,
        sw: ValueAST | None = None,
        dh: ValueAST | None = None,
        dw: ValueAST | None = None,
        ph: ValueAST | None = None,
        pw: ValueAST | None = None,
        pl: ValueAST | None = None,
        pr: ValueAST | None = None,
        location: SourceLocation | None = None,
    ) -> None:
        self.out = _as_value_ast(out, location)
        self.input_value = _as_value_ast(input_value, location)
        self.kh = _as_value_ast(kh, location)
        self.kw = _as_value_ast(kw, location)
        self.sh = _as_value_ast(sh if sh is not None else ConstValueAST(1), location)
        self.sw = _as_value_ast(sw if sw is not None else ConstValueAST(1), location)
        self.dh = _as_value_ast(dh if dh is not None else ConstValueAST(1), location)
        self.dw = _as_value_ast(dw if dw is not None else ConstValueAST(1), location)
        self.ph = _as_value_ast(ph if ph is not None else ConstValueAST(0), location)
        self.pw = _as_value_ast(pw if pw is not None else ConstValueAST(0), location)
        self.pl = _as_value_ast(pl if pl is not None else ConstValueAST(0), location)
        self.pr = _as_value_ast(pr if pr is not None else ConstValueAST(0), location)
        self.location = location

    def emit_mlir(self, ctx: Context, block: Block | None = None) -> EmitMlirResult:
        """发射 kernel.img2col2d。

        功能说明:
        - out/input lower 为 memory operand。
        - kh/kw/stride/dilation/padding lower 为 symbol operand。

        使用示例:
        - op = node.emit_mlir(ctx, block)
        """

        assert isinstance(ctx, Context)
        assert isinstance(block, Block)
        kernel_ops.img2col2d(
            _require_memory(self.out, "out"),
            _require_memory(self.input_value, "input"),
            _require_symbol(self.kh, "kh"),
            _require_symbol(self.kw, "kw"),
            _require_symbol(self.sh, "sh"),
            _require_symbol(self.sw, "sw"),
            _require_symbol(self.dh, "dh"),
            _require_symbol(self.dw, "dw"),
            _require_symbol(self.ph, "ph"),
            _require_symbol(self.pw, "pw"),
            _require_symbol(self.pl, "pl"),
            _require_symbol(self.pr, "pr"),
        )
        out_value = _emit_ssa_value(self.out, ctx, block)
        input_value = _emit_ssa_value(self.input_value, ctx, block)
        kh_value = _emit_symbol_operand(self.kh, ctx, block)
        kw_value = _emit_symbol_operand(self.kw, ctx, block)
        sh_value = _emit_symbol_operand(self.sh, ctx, block)
        sw_value = _emit_symbol_operand(self.sw, ctx, block)
        dh_value = _emit_symbol_operand(self.dh, ctx, block)
        dw_value = _emit_symbol_operand(self.dw, ctx, block)
        ph_value = _emit_symbol_operand(self.ph, ctx, block)
        pw_value = _emit_symbol_operand(self.pw, ctx, block)
        pl_value = _emit_symbol_operand(self.pl, ctx, block)
        pr_value = _emit_symbol_operand(self.pr, ctx, block)
        out_type = _ensure_memory_ssa(out_value, "out")
        _ensure_memory_ssa(input_value, "input")
        return KernelImg2col2dOp(
            out_value,
            input_value,
            kh_value,
            kw_value,
            sh_value,
            sw_value,
            dh_value,
            dw_value,
            ph_value,
            pw_value,
            pl_value,
            pr_value,
            out_type.space,
        )
