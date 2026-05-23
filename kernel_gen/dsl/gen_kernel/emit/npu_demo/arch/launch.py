"""npu_demo arch.launch emitter.

功能说明:
- 将 `arch.launch<block, thread, subthread, shared_memory_size>(@callee, args...)`
  发射为 `npu_demo::launch<...>(callee, args...)`。
- 仅承接 outline 后的 host dispatcher / wrapper 启动语义。

API 列表:
- 无公开 API。

使用示例:
- source = emit_c_op(arch_launch_op, EmitCContext())

关联文件:
- spec: spec/dsl/gen_kernel/gen_kernel.md
- test: test/dsl/gen_kernel/test_gen_kernel.py
- 功能实现: kernel_gen/dsl/gen_kernel/emit/npu_demo/arch/launch.py
"""

from __future__ import annotations

from xdsl.dialects.builtin import IntAttr, IntegerAttr, StringAttr
from xdsl.ir import Operation, SSAValue

from kernel_gen.dialect.arch import ArchLaunchOp
from kernel_gen.dialect.nn import NnMemoryType
from kernel_gen.dialect.symbol import SymbolConstOp

from ...register import emit_c_impl


def _template_call_name(func_name: str, args: tuple[SSAValue, ...]) -> str:
    """生成 launch callee 的模板实参文本。

    功能说明:
    - 从 `arch.launch` args 的 `NnMemoryType.template_name` 中按出现顺序去重。
    - 无 template name 时返回原函数名。

    使用示例:
    - name = _template_call_name("kernel_device", args)
    """

    names: list[str] = []
    for arg in args:
        arg_type = arg.type
        if not isinstance(arg_type, NnMemoryType):
            continue
        arg_type.verify()
        template_name = arg_type.template_name.data
        if template_name and template_name not in names:
            names.append(template_name)
    if not names:
        return func_name
    return f"{func_name}<{', '.join(names)}>"


def _generic_op_name(op: Operation) -> str:
    """读取 generic op 的原始文本名。

    功能说明:
    - xDSL generic op 的真实类名是 `builtin.unregistered`，原始 op 名位于 `op_name__`。
    - 非 generic op 直接返回 `op.name`，用于统一处理 registered 与 generic `symbol.const`。

    使用示例:
    - op_name = _generic_op_name(value.owner)
    """

    op_name_attr = op.attributes.get("op_name__")
    if isinstance(op_name_attr, StringAttr):
        return op_name_attr.data
    return op.name


def _generic_symbol_const_value(op: Operation) -> int | None:
    """读取 generic `"symbol.const"` 的整数值。

    功能说明:
    - 仅处理 `kernel-pattern-attach` / outline 链路中保留的 generic const 形态。
    - 非 generic `symbol.const` 或非整数值返回 `None`，由调用方决定失败边界。

    使用示例:
    - value = _generic_symbol_const_value(op)
    """

    if _generic_op_name(op) != "symbol.const":
        return None
    value_attr = op.attributes.get("value")
    if isinstance(value_attr, IntAttr):
        return value_attr.data
    if isinstance(value_attr, IntegerAttr):
        return value_attr.value.data
    return None


def _launch_template_arg(value: SSAValue, ctx) -> str:
    """发射 C++ launch template 参数。

    功能说明:
    - `npu_demo::launch<...>` 的四个 extent 是 C++ 模板参数，必须是整数 literal。
    - 支持 registered `SymbolConstOp` 与 generic `"symbol.const"`；其它动态值按公开错误语义拒绝。

    使用示例:
    - block = _launch_template_arg(op.block, ctx)
    """

    owner = value.owner
    if isinstance(owner, SymbolConstOp):
        return str(owner.value.data)
    generic_value = _generic_symbol_const_value(owner)
    if generic_value is not None:
        return str(generic_value)
    raise ctx.emit_error("arch.launch", "launch extent must be symbol.const")


@emit_c_impl(ArchLaunchOp, target="npu_demo")
def _emit_npu_demo_arch_launch(op: ArchLaunchOp, ctx) -> str:
    """发射 npu_demo `arch.launch`。

    功能说明:
    - 四个 launch extent 必须是 `symbol.const`，源码中发射为 C++ template literal。
    - callee 必须是 flat SymbolRefAttr，runtime args 按 IR 顺序透传。

    使用示例:
    - line = _emit_npu_demo_arch_launch(op, ctx)
    """

    from ... import emit_c_value

    callee_name = op.callee.root_reference.data
    if not callee_name or len(op.callee.nested_references.data) != 0:
        raise ctx.emit_error("arch.launch", "callee must be flat @symbol")
    launch_args = tuple(SSAValue.get(arg) for arg in op.args)
    callee = _template_call_name(callee_name, launch_args)
    block = _launch_template_arg(op.block, ctx)
    thread = _launch_template_arg(op.thread, ctx)
    subthread = _launch_template_arg(op.subthread, ctx)
    shared_memory_size = _launch_template_arg(op.shared_memory_size, ctx)
    arg_text = ", ".join(emit_c_value(arg, ctx) for arg in launch_args)
    call_args = f"{callee}, {arg_text}" if arg_text else callee
    return (
        f"{ctx.current_indent}npu_demo::launch<{block}, {thread}, {subthread}, {shared_memory_size}>"
        f"({call_args});"
    )
