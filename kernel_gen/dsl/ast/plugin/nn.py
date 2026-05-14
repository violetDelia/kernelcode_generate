"""NN DSL AST builtin registration.


功能说明:
- 注册 `kernel_gen.operation.nn` helper 到 AST parser builtin 注册表。
- 每个 NN operation 使用一个 `@dsl_builtin(...)` builder 函数直接构造对应 AST 节点。
- 本文件无公开 API；导入本文件只触发 NN builtin 注册。

API 列表:
- 无；导入本文件只触发 NN builtin 注册。

使用示例:
- import kernel_gen.dsl.ast.plugin.nn

关联文件:
- spec: spec/dsl/ast/plugin/nn.md
- test: test/dsl/ast/plugin/test_nn.py
- 功能实现: kernel_gen/dsl/ast/plugin/nn.py
"""

from __future__ import annotations

from kernel_gen.core.error import ErrorKind, ErrorModule, KernelCodeError
from kernel_gen.dsl.ast.nodes import (
    ConvAST,
    ConstValueAST,
    Diagnostic,
    FCAST,
    MatmulAST,
    NnAddAST,
    NnBroadcastAST,
    NnBroadcastToAST,
    NnEqAST,
    NnExpAST,
    NnFloorDivAST,
    NnGeAST,
    NnGtAST,
    NnHardSigmoidAST,
    NnImg2Col1dAST,
    NnImg2Col2dAST,
    NnLeAST,
    NnLeakyReluAST,
    NnLtAST,
    NnMulAST,
    NnNeAST,
    NnReduceMaxAST,
    NnReduceMinAST,
    NnReduceSumAST,
    NnReluAST,
    NnSigmoidAST,
    NnSoftmaxAST,
    NnSubAST,
    NnTanhAST,
    NnTransposeAST,
    NnTrueDivAST,
    PythonObjectAttrAST,
    SymbolListAST,
)
from kernel_gen.dsl.ast.plugin.registry import BuiltinCall, dsl_builtin
from kernel_gen.operation import nn
from kernel_gen.symbol_variable.memory import MemorySpace

@dsl_builtin(nn.add, NnAddAST)
def _build_add(node: BuiltinCall) -> NnAddAST:
    """功能说明: 构造 nn.add AST；使用示例: registry 调用该 builder。"""

    if len(node.args) != 2 or node.kwargs:
        diagnostic = Diagnostic("Unsupported nn arithmetic arity", node.location)
        raise KernelCodeError(ErrorKind.CONTRACT, ErrorModule.AST, diagnostic.message)
    return NnAddAST(node.args[0], node.args[1], location=node.location)


@dsl_builtin(nn.sub, NnSubAST)
def _build_sub(node: BuiltinCall) -> NnSubAST:
    """功能说明: 构造 nn.sub AST；使用示例: registry 调用该 builder。"""

    if len(node.args) != 2 or node.kwargs:
        diagnostic = Diagnostic("Unsupported nn arithmetic arity", node.location)
        raise KernelCodeError(ErrorKind.CONTRACT, ErrorModule.AST, diagnostic.message)
    return NnSubAST(node.args[0], node.args[1], location=node.location)


@dsl_builtin(nn.mul, NnMulAST)
def _build_mul(node: BuiltinCall) -> NnMulAST:
    """功能说明: 构造 nn.mul AST；使用示例: registry 调用该 builder。"""

    if len(node.args) != 2 or node.kwargs:
        diagnostic = Diagnostic("Unsupported nn arithmetic arity", node.location)
        raise KernelCodeError(ErrorKind.CONTRACT, ErrorModule.AST, diagnostic.message)
    return NnMulAST(node.args[0], node.args[1], location=node.location)


@dsl_builtin(nn.truediv, NnTrueDivAST)
def _build_truediv(node: BuiltinCall) -> NnTrueDivAST:
    """功能说明: 构造 nn.truediv AST；使用示例: registry 调用该 builder。"""

    if len(node.args) != 2 or node.kwargs:
        diagnostic = Diagnostic("Unsupported nn arithmetic arity", node.location)
        raise KernelCodeError(ErrorKind.CONTRACT, ErrorModule.AST, diagnostic.message)
    return NnTrueDivAST(node.args[0], node.args[1], location=node.location)


@dsl_builtin(nn.floordiv, NnFloorDivAST)
def _build_floordiv(node: BuiltinCall) -> NnFloorDivAST:
    """功能说明: 构造 nn.floordiv AST；使用示例: registry 调用该 builder。"""

    if len(node.args) != 2 or node.kwargs:
        diagnostic = Diagnostic("Unsupported nn arithmetic arity", node.location)
        raise KernelCodeError(ErrorKind.CONTRACT, ErrorModule.AST, diagnostic.message)
    return NnFloorDivAST(node.args[0], node.args[1], location=node.location)


@dsl_builtin(nn.eq, NnEqAST)
def _build_eq(node: BuiltinCall) -> NnEqAST:
    """功能说明: 构造 nn.eq AST；使用示例: registry 调用该 builder。"""

    if len(node.args) != 2 or node.kwargs:
        diagnostic = Diagnostic("Unsupported nn arithmetic arity", node.location)
        raise KernelCodeError(ErrorKind.CONTRACT, ErrorModule.AST, diagnostic.message)
    return NnEqAST(node.args[0], node.args[1], location=node.location)


@dsl_builtin(nn.ne, NnNeAST)
def _build_ne(node: BuiltinCall) -> NnNeAST:
    """功能说明: 构造 nn.ne AST；使用示例: registry 调用该 builder。"""

    if len(node.args) != 2 or node.kwargs:
        diagnostic = Diagnostic("Unsupported nn arithmetic arity", node.location)
        raise KernelCodeError(ErrorKind.CONTRACT, ErrorModule.AST, diagnostic.message)
    return NnNeAST(node.args[0], node.args[1], location=node.location)


@dsl_builtin(nn.lt, NnLtAST)
def _build_lt(node: BuiltinCall) -> NnLtAST:
    """功能说明: 构造 nn.lt AST；使用示例: registry 调用该 builder。"""

    if len(node.args) != 2 or node.kwargs:
        diagnostic = Diagnostic("Unsupported nn arithmetic arity", node.location)
        raise KernelCodeError(ErrorKind.CONTRACT, ErrorModule.AST, diagnostic.message)
    return NnLtAST(node.args[0], node.args[1], location=node.location)


@dsl_builtin(nn.le, NnLeAST)
def _build_le(node: BuiltinCall) -> NnLeAST:
    """功能说明: 构造 nn.le AST；使用示例: registry 调用该 builder。"""

    if len(node.args) != 2 or node.kwargs:
        diagnostic = Diagnostic("Unsupported nn arithmetic arity", node.location)
        raise KernelCodeError(ErrorKind.CONTRACT, ErrorModule.AST, diagnostic.message)
    return NnLeAST(node.args[0], node.args[1], location=node.location)


@dsl_builtin(nn.gt, NnGtAST)
def _build_gt(node: BuiltinCall) -> NnGtAST:
    """功能说明: 构造 nn.gt AST；使用示例: registry 调用该 builder。"""

    if len(node.args) != 2 or node.kwargs:
        diagnostic = Diagnostic("Unsupported nn arithmetic arity", node.location)
        raise KernelCodeError(ErrorKind.CONTRACT, ErrorModule.AST, diagnostic.message)
    return NnGtAST(node.args[0], node.args[1], location=node.location)


@dsl_builtin(nn.ge, NnGeAST)
def _build_ge(node: BuiltinCall) -> NnGeAST:
    """功能说明: 构造 nn.ge AST；使用示例: registry 调用该 builder。"""

    if len(node.args) != 2 or node.kwargs:
        diagnostic = Diagnostic("Unsupported nn arithmetic arity", node.location)
        raise KernelCodeError(ErrorKind.CONTRACT, ErrorModule.AST, diagnostic.message)
    return NnGeAST(node.args[0], node.args[1], location=node.location)


@dsl_builtin(nn.relu, NnReluAST)
def _build_relu(node: BuiltinCall) -> NnReluAST:
    """功能说明: 构造 nn.relu AST；使用示例: registry 调用该 builder。"""

    if len(node.args) != 1 or node.kwargs:
        diagnostic = Diagnostic("Unsupported relu arity", node.location)
        raise KernelCodeError(ErrorKind.CONTRACT, ErrorModule.AST, diagnostic.message)
    return NnReluAST(node.args[0], location=node.location)


@dsl_builtin(nn.sigmoid, NnSigmoidAST)
def _build_sigmoid(node: BuiltinCall) -> NnSigmoidAST:
    """功能说明: 构造 nn.sigmoid AST；使用示例: registry 调用该 builder。"""

    if len(node.args) != 1 or node.kwargs:
        diagnostic = Diagnostic("Unsupported sigmoid arity", node.location)
        raise KernelCodeError(ErrorKind.CONTRACT, ErrorModule.AST, diagnostic.message)
    return NnSigmoidAST(node.args[0], location=node.location)


@dsl_builtin(nn.tanh, NnTanhAST)
def _build_tanh(node: BuiltinCall) -> NnTanhAST:
    """功能说明: 构造 nn.tanh AST；使用示例: registry 调用该 builder。"""

    if len(node.args) != 1 or node.kwargs:
        diagnostic = Diagnostic("Unsupported tanh arity", node.location)
        raise KernelCodeError(ErrorKind.CONTRACT, ErrorModule.AST, diagnostic.message)
    return NnTanhAST(node.args[0], location=node.location)


@dsl_builtin(nn.exp, NnExpAST)
def _build_exp(node: BuiltinCall) -> NnExpAST:
    """功能说明: 构造 nn.exp AST；使用示例: registry 调用该 builder。"""

    if len(node.args) != 1 or node.kwargs:
        diagnostic = Diagnostic("Unsupported exp arity", node.location)
        raise KernelCodeError(ErrorKind.CONTRACT, ErrorModule.AST, diagnostic.message)
    return NnExpAST(node.args[0], location=node.location)


@dsl_builtin(nn.leaky_relu, NnLeakyReluAST)
def _build_leaky_relu(node: BuiltinCall) -> NnLeakyReluAST:
    """功能说明: 构造 nn.leaky_relu AST；使用示例: registry 调用该 builder。"""

    args = node.args
    kwargs = node.kwargs
    location = node.location
    if "beta" in kwargs or len(args) < 1 or len(args) > 2 or (len(args) == 2 and "alpha" in kwargs):
        diagnostic = Diagnostic("Unsupported leaky_relu arity", location)
        raise KernelCodeError(ErrorKind.CONTRACT, ErrorModule.AST, diagnostic.message)
    alpha = kwargs.get("alpha", args[1] if len(args) > 1 else None)
    return NnLeakyReluAST(args[0], alpha, location=location)


@dsl_builtin(nn.hard_sigmoid, NnHardSigmoidAST)
def _build_hard_sigmoid(node: BuiltinCall) -> NnHardSigmoidAST:
    """功能说明: 构造 nn.hard_sigmoid AST；使用示例: registry 调用该 builder。"""

    args = node.args
    kwargs = node.kwargs
    location = node.location
    if (
        len(args) < 1
        or set(kwargs) - {"alpha", "beta"}
        or len(args) > 3
        or (len(args) >= 2 and "alpha" in kwargs)
        or (len(args) >= 3 and "beta" in kwargs)
    ):
        diagnostic = Diagnostic("Unsupported hard_sigmoid arity", location)
        raise KernelCodeError(ErrorKind.CONTRACT, ErrorModule.AST, diagnostic.message)
    alpha = kwargs.get("alpha", args[1] if len(args) > 1 else None)
    beta = kwargs.get("beta", args[2] if len(args) > 2 else None)
    return NnHardSigmoidAST(args[0], alpha, beta, location=location)


@dsl_builtin(nn.reduce_sum, NnReduceSumAST)
def _build_reduce_sum(node: BuiltinCall) -> NnReduceSumAST:
    """功能说明: 构造 nn.reduce_sum AST；使用示例: registry 调用该 builder。"""

    args = node.args
    kwargs = node.kwargs
    location = node.location
    if len(args) < 1 or len(args) > 3 or (len(args) > 1 and "axis" in kwargs) or (len(args) > 2 and "keepdim" in kwargs) or (set(kwargs) - {"axis", "keepdim"}):
        diagnostic = Diagnostic("Unsupported reduce_sum arity", location)
        raise KernelCodeError(ErrorKind.CONTRACT, ErrorModule.AST, diagnostic.message)
    return NnReduceSumAST(args[0], kwargs.get("axis", args[1] if len(args) > 1 else None), kwargs.get("keepdim", args[2] if len(args) > 2 else None), location=location)


@dsl_builtin(nn.reduce_min, NnReduceMinAST)
def _build_reduce_min(node: BuiltinCall) -> NnReduceMinAST:
    """功能说明: 构造 nn.reduce_min AST；使用示例: registry 调用该 builder。"""

    args = node.args
    kwargs = node.kwargs
    location = node.location
    if len(args) < 1 or len(args) > 3 or (len(args) > 1 and "axis" in kwargs) or (len(args) > 2 and "keepdim" in kwargs) or (set(kwargs) - {"axis", "keepdim"}):
        diagnostic = Diagnostic("Unsupported reduce_min arity", location)
        raise KernelCodeError(ErrorKind.CONTRACT, ErrorModule.AST, diagnostic.message)
    return NnReduceMinAST(args[0], kwargs.get("axis", args[1] if len(args) > 1 else None), kwargs.get("keepdim", args[2] if len(args) > 2 else None), location=location)


@dsl_builtin(nn.reduce_max, NnReduceMaxAST)
def _build_reduce_max(node: BuiltinCall) -> NnReduceMaxAST:
    """功能说明: 构造 nn.reduce_max AST；使用示例: registry 调用该 builder。"""

    args = node.args
    kwargs = node.kwargs
    location = node.location
    if len(args) < 1 or len(args) > 3 or (len(args) > 1 and "axis" in kwargs) or (len(args) > 2 and "keepdim" in kwargs) or (set(kwargs) - {"axis", "keepdim"}):
        diagnostic = Diagnostic("Unsupported reduce_max arity", location)
        raise KernelCodeError(ErrorKind.CONTRACT, ErrorModule.AST, diagnostic.message)
    return NnReduceMaxAST(args[0], kwargs.get("axis", args[1] if len(args) > 1 else None), kwargs.get("keepdim", args[2] if len(args) > 2 else None), location=location)


@dsl_builtin(nn.softmax, NnSoftmaxAST)
def _build_softmax(node: BuiltinCall) -> NnSoftmaxAST:
    """功能说明: 构造 nn.softmax AST；使用示例: registry 调用该 builder。"""

    args = node.args
    kwargs = node.kwargs
    location = node.location
    if len(args) < 1 or len(args) > 2 or (len(args) > 1 and "axis" in kwargs) or (set(kwargs) - {"axis"}):
        diagnostic = Diagnostic("Unsupported softmax arity", location)
        raise KernelCodeError(ErrorKind.CONTRACT, ErrorModule.AST, diagnostic.message)
    return NnSoftmaxAST(args[0], kwargs.get("axis", args[1] if len(args) > 1 else None), location=location)


@dsl_builtin(nn.broadcast, NnBroadcastAST)
def _build_broadcast(node: BuiltinCall) -> NnBroadcastAST:
    """功能说明: 构造 nn.broadcast AST；使用示例: registry 调用该 builder。"""

    return NnBroadcastAST(node.args[0], node.args[1], location=node.location)


@dsl_builtin(nn.broadcast_to, NnBroadcastToAST)
def _build_broadcast_to(node: BuiltinCall) -> NnBroadcastToAST:
    """功能说明: 构造 nn.broadcast_to AST；使用示例: registry 调用该 builder。"""

    args = node.args
    kwargs = node.kwargs
    location = node.location
    if len(args) < 1 or len(args) > 3 or (len(args) > 1 and "target_shape" in kwargs) or (len(args) > 2 and "space" in kwargs):
        diagnostic = Diagnostic("Unsupported broadcast_to arity", location)
        raise KernelCodeError(ErrorKind.CONTRACT, ErrorModule.AST, diagnostic.message)
    if "target_shape" not in kwargs and len(args) < 2:
        diagnostic = Diagnostic("Unsupported broadcast_to arity", location)
        raise KernelCodeError(ErrorKind.CONTRACT, ErrorModule.AST, diagnostic.message)
    if "space" not in kwargs and len(args) < 3:
        diagnostic = Diagnostic("Unsupported broadcast_to arity", location)
        raise KernelCodeError(ErrorKind.CONTRACT, ErrorModule.AST, diagnostic.message)
    space_arg = args[2] if len(args) > 2 else kwargs["space"]
    if isinstance(space_arg, ConstValueAST):
        space = space_arg.raw_value
    elif isinstance(space_arg, PythonObjectAttrAST):
        space = space_arg.attr
    else:
        space = space_arg
    if not isinstance(space, MemorySpace):
        diagnostic = Diagnostic("broadcast_to space must be MemorySpace", location)
        raise KernelCodeError(ErrorKind.CONTRACT, ErrorModule.AST, diagnostic.message)
    return NnBroadcastToAST(args[0], args[1] if len(args) > 1 else kwargs["target_shape"], space, location=location)


@dsl_builtin(nn.transpose, NnTransposeAST)
def _build_transpose(node: BuiltinCall) -> NnTransposeAST:
    """功能说明: 构造 nn.transpose AST；使用示例: registry 调用该 builder。"""

    args = node.args
    kwargs = node.kwargs
    location = node.location
    if len(args) < 1 or len(args) > 2 or (len(args) > 1 and "perm" in kwargs) or (set(kwargs) - {"perm"}):
        message = "Unsupported transpose arity" if len(args) > 1 and "perm" in kwargs else "transpose perm is required"
        diagnostic = Diagnostic(message, location)
        raise KernelCodeError(ErrorKind.CONTRACT, ErrorModule.AST, diagnostic.message)
    if len(args) == 1 and "perm" not in kwargs:
        diagnostic = Diagnostic("transpose perm is required", location)
        raise KernelCodeError(ErrorKind.CONTRACT, ErrorModule.AST, diagnostic.message)
    return NnTransposeAST(args[0], args[1] if len(args) > 1 else kwargs["perm"], location=location)


@dsl_builtin(nn.matmul, MatmulAST)
def _build_matmul(node: BuiltinCall) -> MatmulAST:
    """功能说明: 构造 nn.matmul AST；使用示例: registry 调用该 builder。"""

    args = node.args
    kwargs = node.kwargs
    location = node.location
    if len(args) < 2 or len(args) > 3 or (len(args) > 2 and "memoryspace" in kwargs) or (set(kwargs) - {"memoryspace"}):
        diagnostic = Diagnostic("Unsupported matmul arity", location)
        raise KernelCodeError(ErrorKind.CONTRACT, ErrorModule.AST, diagnostic.message)
    memoryspace_arg = kwargs.get("memoryspace", args[2] if len(args) > 2 else None)
    if isinstance(memoryspace_arg, ConstValueAST):
        memoryspace = memoryspace_arg.raw_value
    elif isinstance(memoryspace_arg, PythonObjectAttrAST):
        memoryspace = memoryspace_arg.attr
    else:
        memoryspace = memoryspace_arg
    if memoryspace is not None and not isinstance(memoryspace, MemorySpace):
        diagnostic = Diagnostic("matmul memoryspace must be MemorySpace", location)
        raise KernelCodeError(ErrorKind.CONTRACT, ErrorModule.AST, diagnostic.message)
    return MatmulAST(args[0], args[1], memoryspace, location=location)


@dsl_builtin(nn.fc, FCAST)
def _build_fc(node: BuiltinCall) -> FCAST:
    """功能说明: 构造 nn.fc AST；使用示例: registry 调用该 builder。"""

    return FCAST(node.args[0], node.args[1], location=node.location)


@dsl_builtin(nn.conv, ConvAST)
def _build_conv(node: BuiltinCall) -> ConvAST:
    """功能说明: 构造 nn.conv AST；使用示例: registry 调用该 builder。"""

    args = node.args
    kwargs = node.kwargs
    location = node.location
    if len(args) != 2 or set(kwargs) - {"sh", "sw", "dh", "dw", "ph", "pw", "pl", "pr"}:
        diagnostic = Diagnostic("Unsupported conv arity", location)
        raise KernelCodeError(ErrorKind.CONTRACT, ErrorModule.AST, diagnostic.message)
    stride = SymbolListAST([kwargs.get("sh", ConstValueAST(1)), kwargs.get("sw", ConstValueAST(1))], location)
    padding = SymbolListAST([
        kwargs.get("ph", ConstValueAST(0)),
        kwargs.get("pw", ConstValueAST(0)),
        kwargs.get("pl", ConstValueAST(0)),
        kwargs.get("pr", ConstValueAST(0)),
    ], location)
    dilation = SymbolListAST([kwargs.get("dh", ConstValueAST(1)), kwargs.get("dw", ConstValueAST(1))], location)
    return ConvAST(args[0], args[1], stride, padding, dilation, location=location)


@dsl_builtin(nn.img2col1d, NnImg2Col1dAST)
def _build_img2col1d(node: BuiltinCall) -> NnImg2Col1dAST:
    """功能说明: 构造 nn.img2col1d AST；使用示例: registry 调用该 builder。"""

    if not node.args:
        diagnostic = Diagnostic("Unsupported img2col1d arity", node.location)
        raise KernelCodeError(ErrorKind.CONTRACT, ErrorModule.AST, diagnostic.message)
    args = node.args
    kwargs = node.kwargs
    return NnImg2Col1dAST(args[0], kwargs.get("kw", args[1] if len(args) > 1 else None), kwargs.get("sw", args[2] if len(args) > 2 else None), kwargs.get("dw", args[3] if len(args) > 3 else None), kwargs.get("pl", args[4] if len(args) > 4 else None), kwargs.get("pr", args[5] if len(args) > 5 else None), location=node.location)


@dsl_builtin(nn.img2col2d, NnImg2Col2dAST)
def _build_img2col2d(node: BuiltinCall) -> NnImg2Col2dAST:
    """功能说明: 构造 nn.img2col2d AST；使用示例: registry 调用该 builder。"""

    if not node.args:
        diagnostic = Diagnostic("Unsupported img2col2d arity", node.location)
        raise KernelCodeError(ErrorKind.CONTRACT, ErrorModule.AST, diagnostic.message)
    args = node.args
    kwargs = node.kwargs
    return NnImg2Col2dAST(
        args[0],
        kwargs.get("kh", args[1] if len(args) > 1 else None),
        kwargs.get("kw", args[2] if len(args) > 2 else None),
        kwargs.get("sh", args[3] if len(args) > 3 else None),
        kwargs.get("sw", args[4] if len(args) > 4 else None),
        kwargs.get("dh", args[5] if len(args) > 5 else None),
        kwargs.get("dw", args[6] if len(args) > 6 else None),
        kwargs.get("ph", args[7] if len(args) > 7 else None),
        kwargs.get("pw", args[8] if len(args) > 8 else None),
        kwargs.get("pl", args[9] if len(args) > 9 else None),
        kwargs.get("pr", args[10] if len(args) > 10 else None),
        location=node.location,
    )

__all__: list[str] = []
