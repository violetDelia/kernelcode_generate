"""Kernel DSL AST builtin registration.


功能说明:
- 注册 `kernel_gen.operation.kernel` out-first helper 到 AST parser builtin 注册表。
- 所有 helper 生成无结果 statement AST，lower 到 `kernel` dialect op。

API 列表:
- 无；导入本文件只触发 kernel builtin 注册。

使用示例:
- import kernel_gen.dsl.ast.plugin.kernel

关联文件:
- spec: spec/dsl/ast/plugin/kernel.md
- test: test/dsl/ast/plugin/test_kernel.py
- 功能实现: kernel_gen/dsl/ast/plugin/kernel.py
"""

from __future__ import annotations

from kernel_gen.core.error import ErrorKind, ErrorModule, KernelCodeError
from kernel_gen.dsl.ast.nodes import (
    BoolValueAST,
    ConstValueAST,
    DSLNode,
    Diagnostic,
    KernelAddAST,
    KernelBinaryElewiseAST,
    KernelDivAST,
    KernelEqAST,
    KernelExpAST,
    KernelGeAST,
    KernelGtAST,
    KernelImg2Col1dAST,
    KernelImg2Col2dAST,
    KernelLeAST,
    KernelLtAST,
    KernelMatmulAST,
    KernelMulAST,
    KernelNeAST,
    KernelReduceAST,
    PythonObjectAttrAST,
    KernelSubAST,
    KernelTrueDivAST,
)
from kernel_gen.dsl.ast.plugin.registry import BuiltinCall, dsl_builtin
from kernel_gen.operation import kernel
from kernel_gen.operation.kernel import KernelBinaryElewiseKind, KernelReduceKind


def _unwrap_kind(value: PythonObjectAttrAST | KernelBinaryElewiseKind) -> KernelBinaryElewiseKind:
    """读取公开 kernel kind 枚举。

    功能说明:
    - 支持 parser 传入的 `PythonObjectAttrAST` 和直接 enum 值。
    - 字符串 kind 不是公开 API，保持拒绝。

    使用示例:
    - kind = _unwrap_kind(PythonObjectAttrAST(KernelBinaryElewiseKind.ADD))
    """

    if isinstance(value, PythonObjectAttrAST):
        value = value.attr
    if isinstance(value, KernelBinaryElewiseKind):
        return value
    raise KernelCodeError(ErrorKind.CONTRACT, ErrorModule.AST, "kernel.binary_elewise kind must be KernelBinaryElewiseKind")


def _unwrap_reduce_kind(value: PythonObjectAttrAST | KernelReduceKind) -> KernelReduceKind:
    """读取公开 kernel reduce kind 枚举。

    功能说明:
    - 支持 parser 传入的 `PythonObjectAttrAST` 和直接 enum 值。
    - 字符串 kind 不是公开 API，保持拒绝。

    使用示例:
    - kind = _unwrap_reduce_kind(PythonObjectAttrAST(KernelReduceKind.SUM))
    """

    if isinstance(value, PythonObjectAttrAST):
        value = value.attr
    if isinstance(value, KernelReduceKind):
        return value
    raise KernelCodeError(ErrorKind.CONTRACT, ErrorModule.AST, "kernel.reduce kind must be KernelReduceKind")


def _unwrap_int_attr(value: DSLNode, message: str) -> int:
    """读取 int 常量参数。

    功能说明:
    - 支持 parser 传入的 `ConstValueAST` 或 `PythonObjectAttrAST`。
    - bool 不属于合法 int 参数。

    使用示例:
    - axis = _unwrap_int_attr(node.kwargs["axis"], "kernel.reduce axis must be int")
    """

    if isinstance(value, PythonObjectAttrAST):
        raw_value = value.attr
    elif isinstance(value, (BoolValueAST, ConstValueAST)):
        raw_value = value.raw_value
    else:
        raw_value = value
    if isinstance(raw_value, bool) or not isinstance(raw_value, int):
        raise KernelCodeError(ErrorKind.CONTRACT, ErrorModule.AST, message)
    return raw_value


def _unwrap_bool_attr(value: DSLNode, message: str) -> bool:
    """读取 bool 常量参数。

    功能说明:
    - 支持 parser 传入的 `ConstValueAST` 或 `PythonObjectAttrAST`。
    - int 不属于合法 bool 参数。

    使用示例:
    - keepdim = _unwrap_bool_attr(node.kwargs["keepdim"], "kernel.reduce keepdim must be bool")
    """

    if isinstance(value, PythonObjectAttrAST):
        raw_value = value.attr
    elif isinstance(value, (BoolValueAST, ConstValueAST)):
        raw_value = value.raw_value
    else:
        raw_value = value
    if not isinstance(raw_value, bool):
        raise KernelCodeError(ErrorKind.CONTRACT, ErrorModule.AST, message)
    return raw_value


def _ensure_arg_count(node: BuiltinCall, expected: int, message: str) -> None:
    """校验 builtin 位置参数个数。

    功能说明:
    - 当前文件内统一 arity 错误文本。

    使用示例:
    - _ensure_arg_count(node, 3, "Unsupported kernel.add arity")
    """

    if len(node.args) != expected:
        diagnostic = Diagnostic(message, node.location)
        raise KernelCodeError(ErrorKind.CONTRACT, ErrorModule.AST, diagnostic.message)


def _build_binary(node: BuiltinCall, kind: KernelBinaryElewiseKind) -> KernelBinaryElewiseAST:
    """构造 kernel.binary_elewise AST。

    功能说明:
    - out/lhs/rhs 三个位置参数固定。

    使用示例:
    - ast_node = _build_binary(node, KernelBinaryElewiseKind.ADD)
    """

    _ensure_arg_count(node, 3, "Unsupported kernel binary elewise arity")
    if node.kwargs:
        diagnostic = Diagnostic("Unsupported kernel binary elewise kwargs", node.location)
        raise KernelCodeError(ErrorKind.CONTRACT, ErrorModule.AST, diagnostic.message)
    return KernelBinaryElewiseAST(node.args[0], node.args[1], node.args[2], kind, location=node.location)


def _ensure_binary_call(node: BuiltinCall, message: str) -> None:
    """校验 kernel helper 的二元 out-first 调用形态。

    功能说明:
    - 公开 helper 固定为 out/lhs/rhs 三个位置参数，不接受 keyword。

    使用示例:
    - _ensure_binary_call(node, "Unsupported kernel.add arity")
    """

    _ensure_arg_count(node, 3, message)
    if node.kwargs:
        diagnostic = Diagnostic("Unsupported kernel binary elewise kwargs", node.location)
        raise KernelCodeError(ErrorKind.CONTRACT, ErrorModule.AST, diagnostic.message)


def _arg_or_kw(node: BuiltinCall, name: str, index: int) -> DSLNode | None:
    """读取位置或关键字参数。

    功能说明:
    - img2col DSL helper 同时支持窗口参数以位置参数或 keyword 形式传入。
    - 同一参数不能同时以位置参数和 keyword 传入。

    使用示例:
    - k = _arg_or_kw(node, "k", 2)
    """

    has_keyword = name in node.kwargs
    has_position = len(node.args) > index
    if has_keyword and has_position:
        diagnostic = Diagnostic(f"kernel.img2col parameter passed by position and keyword: {name}", node.location)
        raise KernelCodeError(ErrorKind.CONTRACT, ErrorModule.AST, diagnostic.message)
    if has_keyword:
        return node.kwargs[name]
    if has_position:
        return node.args[index]
    return None


def _require_arg_or_kw(node: BuiltinCall, name: str, index: int) -> DSLNode:
    """读取必填的位置或关键字参数。

    功能说明:
    - 缺少必填参数时抛出稳定 AST 合同错误。

    使用示例:
    - kh = _require_arg_or_kw(node, "kh", 2)
    """

    value = _arg_or_kw(node, name, index)
    if value is None:
        diagnostic = Diagnostic(f"kernel.{name} is required", node.location)
        raise KernelCodeError(ErrorKind.CONTRACT, ErrorModule.AST, diagnostic.message)
    return value


@dsl_builtin(kernel.binary_elewise, KernelBinaryElewiseAST)
def _build_binary_elewise(node: BuiltinCall) -> KernelBinaryElewiseAST:
    """功能说明: 构造 kernel.binary_elewise AST；使用示例: registry 调用该 builder。"""

    _ensure_arg_count(node, 3, "Unsupported kernel.binary_elewise arity")
    if set(node.kwargs) != {"kind"}:
        diagnostic = Diagnostic("kernel.binary_elewise kind is required", node.location)
        raise KernelCodeError(ErrorKind.CONTRACT, ErrorModule.AST, diagnostic.message)
    return KernelBinaryElewiseAST(node.args[0], node.args[1], node.args[2], _unwrap_kind(node.kwargs["kind"]), location=node.location)


@dsl_builtin(kernel.add, KernelAddAST)
def _build_add(node: BuiltinCall) -> KernelAddAST:
    """功能说明: 构造 kernel.add AST；使用示例: registry 调用该 builder。"""

    _ensure_binary_call(node, "Unsupported kernel.add arity")
    return KernelAddAST(node.args[0], node.args[1], node.args[2], location=node.location)


@dsl_builtin(kernel.sub, KernelSubAST)
def _build_sub(node: BuiltinCall) -> KernelSubAST:
    """功能说明: 构造 kernel.sub AST；使用示例: registry 调用该 builder。"""

    _ensure_binary_call(node, "Unsupported kernel.sub arity")
    return KernelSubAST(node.args[0], node.args[1], node.args[2], location=node.location)


@dsl_builtin(kernel.mul, KernelMulAST)
def _build_mul(node: BuiltinCall) -> KernelMulAST:
    """功能说明: 构造 kernel.mul AST；使用示例: registry 调用该 builder。"""

    _ensure_binary_call(node, "Unsupported kernel.mul arity")
    return KernelMulAST(node.args[0], node.args[1], node.args[2], location=node.location)


@dsl_builtin(kernel.div, KernelDivAST)
def _build_div(node: BuiltinCall) -> KernelDivAST:
    """功能说明: 构造 kernel.div AST；使用示例: registry 调用该 builder。"""

    _ensure_binary_call(node, "Unsupported kernel.div arity")
    return KernelDivAST(node.args[0], node.args[1], node.args[2], location=node.location)


@dsl_builtin(kernel.truediv, KernelTrueDivAST)
def _build_truediv(node: BuiltinCall) -> KernelTrueDivAST:
    """功能说明: 构造 kernel.truediv AST；使用示例: registry 调用该 builder。"""

    _ensure_binary_call(node, "Unsupported kernel.truediv arity")
    return KernelTrueDivAST(node.args[0], node.args[1], node.args[2], location=node.location)


@dsl_builtin(kernel.eq, KernelEqAST)
def _build_eq(node: BuiltinCall) -> KernelEqAST:
    """功能说明: 构造 kernel.eq AST；使用示例: registry 调用该 builder。"""

    _ensure_binary_call(node, "Unsupported kernel.eq arity")
    return KernelEqAST(node.args[0], node.args[1], node.args[2], location=node.location)


@dsl_builtin(kernel.ne, KernelNeAST)
def _build_ne(node: BuiltinCall) -> KernelNeAST:
    """功能说明: 构造 kernel.ne AST；使用示例: registry 调用该 builder。"""

    _ensure_binary_call(node, "Unsupported kernel.ne arity")
    return KernelNeAST(node.args[0], node.args[1], node.args[2], location=node.location)


@dsl_builtin(kernel.lt, KernelLtAST)
def _build_lt(node: BuiltinCall) -> KernelLtAST:
    """功能说明: 构造 kernel.lt AST；使用示例: registry 调用该 builder。"""

    _ensure_binary_call(node, "Unsupported kernel.lt arity")
    return KernelLtAST(node.args[0], node.args[1], node.args[2], location=node.location)


@dsl_builtin(kernel.le, KernelLeAST)
def _build_le(node: BuiltinCall) -> KernelLeAST:
    """功能说明: 构造 kernel.le AST；使用示例: registry 调用该 builder。"""

    _ensure_binary_call(node, "Unsupported kernel.le arity")
    return KernelLeAST(node.args[0], node.args[1], node.args[2], location=node.location)


@dsl_builtin(kernel.gt, KernelGtAST)
def _build_gt(node: BuiltinCall) -> KernelGtAST:
    """功能说明: 构造 kernel.gt AST；使用示例: registry 调用该 builder。"""

    _ensure_binary_call(node, "Unsupported kernel.gt arity")
    return KernelGtAST(node.args[0], node.args[1], node.args[2], location=node.location)


@dsl_builtin(kernel.ge, KernelGeAST)
def _build_ge(node: BuiltinCall) -> KernelGeAST:
    """功能说明: 构造 kernel.ge AST；使用示例: registry 调用该 builder。"""

    _ensure_binary_call(node, "Unsupported kernel.ge arity")
    return KernelGeAST(node.args[0], node.args[1], node.args[2], location=node.location)


@dsl_builtin(kernel.exp, KernelExpAST)
def _build_exp(node: BuiltinCall) -> KernelExpAST:
    """功能说明: 构造 kernel.exp AST；使用示例: registry 调用该 builder。"""

    _ensure_arg_count(node, 2, "Unsupported kernel.exp arity")
    if node.kwargs:
        diagnostic = Diagnostic("Unsupported kernel.exp kwargs", node.location)
        raise KernelCodeError(ErrorKind.CONTRACT, ErrorModule.AST, diagnostic.message)
    return KernelExpAST(node.args[0], node.args[1], location=node.location)


@dsl_builtin(kernel.reduce, KernelReduceAST)
def _build_reduce(node: BuiltinCall) -> KernelReduceAST:
    """功能说明: 构造 kernel.reduce AST；使用示例: registry 调用该 builder。"""

    _ensure_arg_count(node, 2, "Unsupported kernel.reduce arity")
    allowed_kwargs = {"kind", "axis", "keepdim"}
    unexpected_kwargs = set(node.kwargs) - allowed_kwargs
    if unexpected_kwargs:
        kwargs_text = ", ".join(sorted(unexpected_kwargs))
        diagnostic = Diagnostic(f"Unsupported kernel.reduce kwargs: {kwargs_text}", node.location)
        raise KernelCodeError(ErrorKind.CONTRACT, ErrorModule.AST, diagnostic.message)
    if "kind" not in node.kwargs or "axis" not in node.kwargs:
        diagnostic = Diagnostic("kernel.reduce kind and axis are required", node.location)
        raise KernelCodeError(ErrorKind.CONTRACT, ErrorModule.AST, diagnostic.message)
    keepdim_node = node.kwargs.get("keepdim")
    keepdim = False if keepdim_node is None else _unwrap_bool_attr(keepdim_node, "kernel.reduce keepdim must be bool")
    return KernelReduceAST(
        node.args[0],
        node.args[1],
        _unwrap_reduce_kind(node.kwargs["kind"]),
        axis=_unwrap_int_attr(node.kwargs["axis"], "kernel.reduce axis must be int"),
        keepdim=keepdim,
        location=node.location,
    )


@dsl_builtin(kernel.matmul, KernelMatmulAST)
def _build_matmul(node: BuiltinCall) -> KernelMatmulAST:
    """功能说明: 构造 kernel.matmul AST；使用示例: registry 调用该 builder。"""

    _ensure_arg_count(node, 3, "Unsupported kernel.matmul arity")
    if node.kwargs:
        kwargs_text = ", ".join(sorted(node.kwargs))
        diagnostic = Diagnostic(f"Unsupported kernel.matmul kwargs: {kwargs_text}", node.location)
        raise KernelCodeError(ErrorKind.CONTRACT, ErrorModule.AST, diagnostic.message)
    return KernelMatmulAST(node.args[0], node.args[1], node.args[2], location=node.location)


@dsl_builtin(kernel.img2col1d, KernelImg2Col1dAST)
def _build_img2col1d(node: BuiltinCall) -> KernelImg2Col1dAST:
    """功能说明: 构造 kernel.img2col1d AST；使用示例: registry 调用该 builder。"""

    if len(node.args) < 2 or len(node.args) > 7:
        diagnostic = Diagnostic("Unsupported kernel.img2col1d arity", node.location)
        raise KernelCodeError(ErrorKind.CONTRACT, ErrorModule.AST, diagnostic.message)
    allowed = {"k", "s", "d", "p_left", "p_right"}
    if set(node.kwargs) - allowed:
        diagnostic = Diagnostic("Unsupported kernel.img2col1d kwargs", node.location)
        raise KernelCodeError(ErrorKind.CONTRACT, ErrorModule.AST, diagnostic.message)
    return KernelImg2Col1dAST(
        node.args[0],
        node.args[1],
        _require_arg_or_kw(node, "k", 2),
        _arg_or_kw(node, "s", 3),
        _arg_or_kw(node, "d", 4),
        _arg_or_kw(node, "p_left", 5),
        _arg_or_kw(node, "p_right", 6),
        location=node.location,
    )


@dsl_builtin(kernel.img2col2d, KernelImg2Col2dAST)
def _build_img2col2d(node: BuiltinCall) -> KernelImg2Col2dAST:
    """功能说明: 构造 kernel.img2col2d AST；使用示例: registry 调用该 builder。"""

    if len(node.args) < 2 or len(node.args) > 12:
        diagnostic = Diagnostic("Unsupported kernel.img2col2d arity", node.location)
        raise KernelCodeError(ErrorKind.CONTRACT, ErrorModule.AST, diagnostic.message)
    allowed = {"kh", "kw", "sh", "sw", "dh", "dw", "ph", "pw", "pl", "pr"}
    if set(node.kwargs) - allowed:
        diagnostic = Diagnostic("Unsupported kernel.img2col2d kwargs", node.location)
        raise KernelCodeError(ErrorKind.CONTRACT, ErrorModule.AST, diagnostic.message)
    return KernelImg2Col2dAST(
        node.args[0],
        node.args[1],
        _require_arg_or_kw(node, "kh", 2),
        _require_arg_or_kw(node, "kw", 3),
        _arg_or_kw(node, "sh", 4),
        _arg_or_kw(node, "sw", 5),
        _arg_or_kw(node, "dh", 6),
        _arg_or_kw(node, "dw", 7),
        _arg_or_kw(node, "ph", 8),
        _arg_or_kw(node, "pw", 9),
        _arg_or_kw(node, "pl", 10),
        _arg_or_kw(node, "pr", 11),
        location=node.location,
    )


__all__: list[str] = []
