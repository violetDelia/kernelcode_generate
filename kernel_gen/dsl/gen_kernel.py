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
from xdsl.dialects.builtin import ArrayAttr, DictionaryAttr, IntegerType, IndexType, StringAttr

from kernel_gen.dialect.nn import NnMemoryType

from .emit_c import EmitCContext, emit_c_op


class GenKernelError(ValueError):
    """gen_kernel 阶段错误。"""


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
    if isinstance(attr, IntegerType):
        if attr.width.data == 1:
            return "bool"
        return f"int{attr.width.data}_t"
    if isinstance(attr, IndexType):
        return "long long"
    if isinstance(attr, NnMemoryType):
        return f"Memory<{_type_to_c(attr.element_type)}>"
    raise TypeError(f"unsupported type: {attr}")


def gen_signature(func_op: func.FuncOp, ctx: EmitCContext) -> str:
    """生成目标函数签名。"""

    func_name = func_op.sym_name.data
    input_types = list(func_op.function_type.inputs.data)
    result_types = list(func_op.function_type.outputs.data)
    if len(result_types) > 1:
        raise _error(ctx, func_name, "unsupported return form")
    if result_types and not isinstance(result_types[0], NnMemoryType):
        raise _error(ctx, func_name, "unsupported return form")

    arg_names = _extract_arg_names(func_op)
    params: list[str] = []
    for arg_name, arg_type, arg_value in zip(arg_names, input_types, func_op.args, strict=True):
        ctx.bind_name(arg_value, arg_name)
        if isinstance(arg_type, NnMemoryType):
            params.append(f"const {_type_to_c(arg_type)}& {arg_name}")
        else:
            params.append(f"{_type_to_c(arg_type)} {arg_name}")

    if result_types:
        params.append(f"{_type_to_c(result_types[0])}& out")

    return f"void {func_name}({', '.join(params)})"


def gen_body(func_op: func.FuncOp, ctx: EmitCContext) -> str:
    """按 op 顺序生成函数体。"""

    result_types = list(func_op.function_type.outputs.data)
    lines: list[str] = []
    for op in func_op.body.block.ops:
        if isinstance(op, func.ReturnOp):
            if not op.arguments:
                continue
            if len(result_types) != 1 or not isinstance(result_types[0], NnMemoryType):
                raise _error(ctx, func_op.sym_name.data, "unsupported return form")
            value_name = ctx.lookup_name(op.arguments[0])
            if value_name is None:
                from .emit_c import emit_c_value

                value_name = emit_c_value(op.arguments[0], ctx)
            lines.append(f"{ctx.current_indent}out = {value_name};")
            continue
        stmt = emit_c_op(op, ctx)
        if stmt:
            lines.append(stmt)
    return "\n".join(lines)


def gen_kernel(func_op: func.FuncOp, ctx: EmitCContext) -> str:
    """生成完整函数源码。"""

    signature = gen_signature(func_op, ctx)
    ctx.push_indent()
    body = gen_body(func_op, ctx)
    ctx.pop_indent()
    if body:
        return f"{signature} {{\n{body}\n}}"
    return f"{signature} {{\n}}"


__all__ = ["GenKernelError", "gen_body", "gen_kernel", "gen_signature"]
