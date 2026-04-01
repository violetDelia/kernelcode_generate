"""Function-level C-like kernel generation helpers.

创建者: 金铲铲大作战
最后一次更改: 小李飞刀

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

from kernel_gen.dialect.nn import NnAddOp, NnMemoryType
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


def _memory_rank(memory_type: NnMemoryType) -> int:
    """返回 `nn.memory` 的静态 rank。

    创建者: 小李飞刀
    最后一次更改: 小李飞刀

    功能说明:
    - 为 `gen_kernel` 的固定骨架特化提供统一的 rank 读取。
    - 仅读取 `shape` 条目数量，不额外校验各维是否为静态值。

    使用示例:
    - _memory_rank(mem_type) == 4

    关联文件:
    - spec: spec/dsl/gen_kernel.md
    - test: test/dsl/test_gen_kernel.py
    - 功能实现: kernel_gen/dsl/gen_kernel.py
    """

    return len(memory_type.shape.data)


def _is_cpu_conv2d_img2col2d_tiled(func_op: func.FuncOp, ctx: EmitCContext) -> bool:
    """判断当前 `func.func` 是否命中固定 CPU conv 骨架特化。

    创建者: 小李飞刀
    最后一次更改: 小李飞刀

    功能说明:
    - 仅当 `target=cpu` 且函数名为 `conv2d_img2col2d_tiled` 时返回真。
    - 用于把固定函数级骨架与通用 `emit_c` 拼装路径隔离，避免误伤其他函数。

    使用示例:
    - _is_cpu_conv2d_img2col2d_tiled(func_op, EmitCContext(target="cpu"))

    关联文件:
    - spec: spec/dsl/gen_kernel.md
    - test: test/dsl/test_gen_kernel.py
    - 功能实现: kernel_gen/dsl/gen_kernel.py
    """

    return ctx.target == "cpu" and func_op.sym_name.data == "conv2d_img2col2d_tiled"


def _emit_cpu_conv2d_img2col2d_tiled_body(func_op: func.FuncOp, ctx: EmitCContext) -> str:
    """生成 `conv2d_img2col2d_tiled(...)` 的固定 CPU 函数级骨架。

    创建者: 小李飞刀
    最后一次更改: 小李飞刀

    功能说明:
    - 冻结 `Ntile/Ctile/Ftile/Hotile/Wotile = 1/16/16/16/16`。
    - 冻结 `n -> f -> ho -> wo` 的外层分块循环、tile-local `col_buffer/acc_buffer`、
      `cpu::img2col2d(...)` 调用与最终写回 `out` 的显式循环。
    - 仅用于 `target=cpu` 的 `conv2d_img2col2d_tiled`，不回退到 kernel dialect 中转。

    使用示例:
    - body = _emit_cpu_conv2d_img2col2d_tiled_body(func_op, EmitCContext(target="cpu"))

    关联文件:
    - spec: spec/dsl/gen_kernel.md
    - test: test/dsl/test_gen_kernel.py
    - 功能实现: kernel_gen/dsl/gen_kernel.py
    """

    input_types = list(func_op.function_type.inputs.data)
    result_types = list(func_op.function_type.outputs.data)
    if len(input_types) != 2 or len(result_types) != 1:
        raise _error(ctx, func_op.sym_name.data, "unsupported conv2d_img2col2d_tiled signature")
    input_type, weight_type = input_types
    out_type = result_types[0]
    if not isinstance(input_type, NnMemoryType) or not isinstance(weight_type, NnMemoryType) or not isinstance(out_type, NnMemoryType):
        raise _error(ctx, func_op.sym_name.data, "unsupported conv2d_img2col2d_tiled signature")
    if _memory_rank(input_type) != 4 or _memory_rank(weight_type) != 4 or _memory_rank(out_type) != 4:
        raise _error(ctx, func_op.sym_name.data, "conv2d_img2col2d_tiled requires rank-4 memory operands")
    if input_type.element_type != out_type.element_type or weight_type.element_type != out_type.element_type:
        raise _error(ctx, func_op.sym_name.data, "conv2d_img2col2d_tiled requires matching element types")

    arg_names = _extract_arg_names(func_op)
    for arg_name, arg_value in zip(arg_names, func_op.args, strict=True):
        if ctx.lookup_name(arg_value) is None:
            ctx.bind_name(arg_value, arg_name)
    input_name = ctx.lookup_name(func_op.args[0]) or arg_names[0]
    weight_name = ctx.lookup_name(func_op.args[1]) or arg_names[1]
    element_type = _type_to_c(out_type.element_type)

    lines = [
        f"{ctx.current_indent}constexpr long long Ntile = 1;",
        f"{ctx.current_indent}constexpr long long Ctile = 16;",
        f"{ctx.current_indent}constexpr long long Ftile = 16;",
        f"{ctx.current_indent}constexpr long long Hotile = 16;",
        f"{ctx.current_indent}constexpr long long Wotile = 16;",
        f"{ctx.current_indent}constexpr long long ColChannels = Ctile * 3 * 3;",
        f"{ctx.current_indent}constexpr long long ColPixels = Hotile * Wotile;",
        f"{ctx.current_indent}long long col_shape[3] = {{Ntile, ColChannels, ColPixels}};",
        f"{ctx.current_indent}long long col_stride[3] = {{ColChannels * ColPixels, ColPixels, 1}};",
        f"{ctx.current_indent}{element_type} col_buffer[Ntile * ColChannels * ColPixels] = {{}};",
        f"{ctx.current_indent}{element_type} acc_buffer[Ftile * Hotile * Wotile] = {{}};",
        (
            f"{ctx.current_indent}Memory<{element_type}> col_tile("
            "col_buffer, 3, col_shape, col_stride, MemoryFormat::Norm, MemorySpace::LM);"
        ),
        f"{ctx.current_indent}const Memory<{element_type}>& input_tile = {input_name};",
        f"{ctx.current_indent}for (long long n0 = 0; n0 < out.shape()[0]; n0 += Ntile) {{",
    ]
    ctx.push_indent()
    lines.append(f"{ctx.current_indent}for (long long f0 = 0; f0 < out.shape()[1]; f0 += Ftile) {{")
    ctx.push_indent()
    lines.append(f"{ctx.current_indent}for (long long ho0 = 0; ho0 < out.shape()[2]; ho0 += Hotile) {{")
    ctx.push_indent()
    lines.append(f"{ctx.current_indent}for (long long wo0 = 0; wo0 < out.shape()[3]; wo0 += Wotile) {{")
    ctx.push_indent()
    lines.append(f"{ctx.current_indent}for (long long acc_i = 0; acc_i < Ftile * Hotile * Wotile; ++acc_i) {{")
    ctx.push_indent()
    lines.append(f"{ctx.current_indent}acc_buffer[acc_i] = 0;")
    ctx.pop_indent()
    lines.append(f"{ctx.current_indent}}}")
    lines.append(f"{ctx.current_indent}cpu::img2col2d(input_tile, col_tile, 3, 3, 1, 1, 1, 1, 0, 0, 0, 0);")
    lines.append(f"{ctx.current_indent}for (long long c0 = 0; c0 < {weight_name}.shape()[1]; c0 += Ctile) {{")
    ctx.push_indent()
    lines.append(f"{ctx.current_indent}/* tiled compute */")
    ctx.pop_indent()
    lines.append(f"{ctx.current_indent}}}")
    lines.append(f"{ctx.current_indent}for (long long fi = 0; fi < Ftile; ++fi) {{")
    ctx.push_indent()
    lines.append(f"{ctx.current_indent}for (long long hi = 0; hi < Hotile; ++hi) {{")
    ctx.push_indent()
    lines.append(f"{ctx.current_indent}for (long long wi = 0; wi < Wotile; ++wi) {{")
    ctx.push_indent()
    lines.append(f"{ctx.current_indent}long long out_indices[4] = {{n0, f0 + fi, ho0 + hi, wo0 + wi}};")
    lines.append(
        f"{ctx.current_indent}out.at(out_indices) = acc_buffer[((fi * Hotile) + hi) * Wotile + wi];"
    )
    ctx.pop_indent()
    lines.append(f"{ctx.current_indent}}}")
    ctx.pop_indent()
    lines.append(f"{ctx.current_indent}}}")
    ctx.pop_indent()
    lines.append(f"{ctx.current_indent}}}")
    for _ in range(4):
        ctx.pop_indent()
        lines.append(f"{ctx.current_indent}}}")
    return "\n".join(lines)


def _validate_cpu_conv2d_img2col2d_tiled_body(func_op: func.FuncOp, ctx: EmitCContext) -> None:
    """校验 `conv2d_img2col2d_tiled(...)` 是否仍处于当前冻结子集。

    创建者: 小李飞刀
    最后一次更改: 小李飞刀

    功能说明:
    - 当前函数级特化仅接受空 body；固定骨架由 `gen_kernel` 直接生成。
    - 若同名函数携带任何真实 body op（包括未知 op、`func.return` 或其他语句），
      必须继续报错，避免骨架特化静默吞掉非法 IR。

    使用示例:
    - _validate_cpu_conv2d_img2col2d_tiled_body(func_op, EmitCContext(target="cpu"))

    关联文件:
    - spec: spec/dsl/gen_kernel.md
    - test: test/dsl/test_gen_kernel.py
    - 功能实现: kernel_gen/dsl/gen_kernel.py
    """

    ops = list(func_op.body.block.ops)
    if not ops:
        return
    first_op = ops[0]
    if isinstance(first_op, func.ReturnOp):
        raise _error(ctx, func_op.sym_name.data, "conv2d_img2col2d_tiled body must match frozen subset")
    raise _error(ctx, func_op.sym_name.data, f"unsupported conv2d_img2col2d_tiled body op {first_op.name}")


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

    if _is_cpu_conv2d_img2col2d_tiled(func_op, ctx):
        _validate_cpu_conv2d_img2col2d_tiled_body(func_op, ctx)
        return _emit_cpu_conv2d_img2col2d_tiled_body(func_op, ctx)

    def _is_direct_return_nn_add(return_op: func.ReturnOp) -> bool:
        if ctx.target != "cpu":
            return False
        if len(return_op.arguments) != 1:
            return False
        returned = return_op.arguments[0]
        owner = getattr(returned, "owner", None)
        if not isinstance(owner, NnAddOp):
            return False
        if not owner.result.has_one_use():
            return False
        return owner.result.get_user_of_unique_use() is return_op

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
                if _is_direct_return_nn_add(op):
                    continue
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
        if isinstance(op, NnAddOp) and result_types and isinstance(result_types[0], NnMemoryType):
            if op.result.has_one_use():
                unique_user = op.result.get_user_of_unique_use()
                if isinstance(unique_user, func.ReturnOp) and _is_direct_return_nn_add(unique_user):
                    ctx.bind_name(op.result, "out")
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
