"""Function-level C-like kernel generation helpers.

创建者: 金铲铲大作战
最后一次更改: jcc你莫辜负

功能说明:
- 按 `emit_c` 的节点级规则，组装 `func.func` 的完整函数源码。
- 负责函数签名、参数顺序、输出参数与函数体遍历。

使用示例:
- from kernel_gen.dsl.gen_kernel import gen_kernel
- source = gen_kernel(func_op, EmitCContext(target="cpu"))

关联文件:
- spec: spec/dsl/gen_kernel.md
- test: test/dsl/test_gen_kernel.py
- 功能实现: kernel_gen/dsl/gen_kernel.py
"""

from __future__ import annotations

from typing import Any

from xdsl.dialects import func
from xdsl.dialects.builtin import ArrayAttr, DictionaryAttr, Float32Type, Float64Type, IntegerType, IndexType, StringAttr

from kernel_gen.dialect.nn import NnMemoryType
from kernel_gen.dialect.symbol import SymbolValueType

from .emit_c import EmitCContext, emit_c_op


class GenKernelError(ValueError):
    """Raised when `gen_kernel` cannot emit a valid target function."""


def _error(ctx: EmitCContext, func_name: str, reason: str) -> GenKernelError:
    return GenKernelError(f"target={ctx.target}: func {func_name}: {reason}")


def _extract_arg_names(func_op: func.FuncOp) -> list[str]:
    names: list[str] = []
    attrs = func_op.arg_attrs
    if isinstance(attrs, ArrayAttr):
        for index, attr in enumerate(attrs.data):
            if isinstance(attr, DictionaryAttr):
                name_attr = attr.data.get("name")
                if isinstance(name_attr, StringAttr) and name_attr.data:
                    names.append(name_attr.data)
                    continue
            names.append(f"arg{index}")
        return names
    return [f"arg{index}" for index, _ in enumerate(func_op.args)]


def _type_to_c(attr: Any) -> str:
    """将 xdsl Attribute 映射为 C 侧类型名。

    创建者: 金铲铲大作战
    最后一次更改: jcc你莫辜负

    功能说明:
    - 用于 `gen_signature` 生成函数签名时，将 IR 类型属性转换为 C/C++ 侧可用类型名。
    - 支持的类型映射清单：
      - `IntegerType(1)` -> `bool`
      - `IntegerType(N)` -> `int{N}_t`
      - `Float32Type` -> `float`
      - `Float64Type` -> `double`
      - `IndexType` -> `long long`
      - `NnMemoryType<T>` -> `Memory<...>`（递归映射 `element_type`）
      - `SymbolValueType` -> `long long`
    - 若遇到不支持类型，将抛出 `TypeError("unsupported type: ...")`。

    使用示例:
    - from xdsl.dialects.builtin import ArrayAttr, IntAttr, f32, f64
    - from kernel_gen.dialect.nn import NnMemorySpaceAttr, NnMemoryType
    - assert _type_to_c(f32) == "float"
    - assert _type_to_c(f64) == "double"
    - mem_f64 = NnMemoryType(ArrayAttr([IntAttr(2)]), ArrayAttr([IntAttr(1)]), f64, NnMemorySpaceAttr.from_name("global"))
    - assert _type_to_c(mem_f64) == "Memory<double>"

    关联文件:
    - spec: spec/dsl/gen_kernel.md
    - test: test/dsl/test_gen_kernel.py
    - 功能实现: kernel_gen/dsl/gen_kernel.py
    """
    if isinstance(attr, IntegerType):
        if attr.width.data == 1:
            return "bool"
        return f"int{attr.width.data}_t"
    if isinstance(attr, Float32Type):
        return "float"
    if isinstance(attr, Float64Type):
        return "double"
    if isinstance(attr, IndexType):
        return "long long"
    if isinstance(attr, NnMemoryType):
        return f"Memory<{_type_to_c(attr.element_type)}>"
    if isinstance(attr, SymbolValueType):
        return "long long"
    raise TypeError(f"unsupported type: {attr}")


def gen_signature(func_op: func.FuncOp, ctx: EmitCContext) -> str:
    """Generate a target signature for a single lowered `func.func`.

    Parameters:
        func_op: MLIR `func.func` operation to analyze.
        ctx: Shared emit context used to bind stable argument names.

    Returns:
        A function signature string without the function body.

    Raises:
        GenKernelError: If the function return form is unsupported.
        TypeError: If an input or output type cannot be mapped to the target.
    """

    func_name = func_op.sym_name.data
    input_types = list(func_op.function_type.inputs.data)
    result_types = list(func_op.function_type.outputs.data)
    if len(result_types) > 1:
        raise _error(ctx, func_name, "unsupported return form")
    if result_types and not isinstance(result_types[0], (NnMemoryType, SymbolValueType)):
        raise _error(ctx, func_name, "unsupported return form")
    if result_types and isinstance(result_types[0], SymbolValueType) and ctx.target != "cpu":
        raise _error(ctx, func_name, "symbol scalar return is cpu-only")

    arg_names = _extract_arg_names(func_op)
    params: list[str] = []
    for arg_name, arg_type, arg_value in zip(arg_names, input_types, func_op.args, strict=True):
        ctx.bind_name(arg_value, arg_name)
        if isinstance(arg_type, NnMemoryType):
            params.append(f"const {_type_to_c(arg_type)}& {arg_name}")
        else:
            params.append(f"{_type_to_c(arg_type)} {arg_name}")

    return_type = "void"
    if result_types and isinstance(result_types[0], SymbolValueType):
        return_type = _type_to_c(result_types[0])
    elif result_types:
        params.append(f"{_type_to_c(result_types[0])}& out")

    return f"{return_type} {func_name}({', '.join(params)})"


def gen_body(func_op: func.FuncOp, ctx: EmitCContext) -> str:
    """Generate the function body in IR order.

    Parameters:
        func_op: MLIR `func.func` operation whose entry block will be emitted.
        ctx: Shared emit context reused by `gen_signature` and `emit_c`.

    Returns:
        The emitted function body text without the signature wrapper.

    Raises:
        GenKernelError: If the function return form is unsupported.
        ValueError: Propagated from `emit_c` when an op cannot be emitted.
    """

    result_types = list(func_op.function_type.outputs.data)
    lines: list[str] = []
    for op in func_op.body.block.ops:
        if isinstance(op, func.ReturnOp):
            if not result_types:
                if op.arguments:
                    raise _error(ctx, func_op.sym_name.data, "unsupported return form")
                continue
            if len(result_types) != 1:
                raise _error(ctx, func_op.sym_name.data, "unsupported return form")
            result_type = result_types[0]
            if len(op.arguments) != 1:
                raise _error(ctx, func_op.sym_name.data, "unsupported return form")
            if op.arguments[0].type != result_type:
                raise _error(ctx, func_op.sym_name.data, "unsupported return form")
            if isinstance(result_type, NnMemoryType):
                value_name = ctx.lookup_name(op.arguments[0])
                if value_name is None:
                    from .emit_c import emit_c_value

                    value_name = emit_c_value(op.arguments[0], ctx)
                lines.append(f"{ctx.current_indent}out = {value_name};")
                continue
            if isinstance(result_type, SymbolValueType):
                if ctx.target != "cpu":
                    raise _error(ctx, func_op.sym_name.data, "symbol scalar return is cpu-only")
                from .emit_c import emit_c_value

                value_expr = emit_c_value(op.arguments[0], ctx)
                lines.append(f"{ctx.current_indent}return {value_expr};")
                continue
            raise _error(ctx, func_op.sym_name.data, "unsupported return form")
            continue
        stmt = emit_c_op(op, ctx)
        if stmt:
            lines.append(stmt)
    return "\n".join(lines)


def gen_kernel(func_op: func.FuncOp, ctx: EmitCContext) -> str:
    """Generate the full target function source for one lowered `func.func`.

    Parameters:
        func_op: MLIR `func.func` operation to emit.
        ctx: Shared emit context carrying target and naming state.

    Returns:
        Complete target function source text including signature and body.

    Raises:
        GenKernelError: If the function return contract is unsupported.
        ValueError: Propagated from `emit_c` for unsupported IR constructs.
        TypeError: If a type cannot be lowered to the target.
    """

    signature = gen_signature(func_op, ctx)
    ctx.push_indent()
    body = gen_body(func_op, ctx)
    ctx.pop_indent()
    if body:
        return f"{signature} {{\n{body}\n}}"
    return f"{signature} {{\n}}"


__all__ = ["GenKernelError", "gen_body", "gen_kernel", "gen_signature"]
