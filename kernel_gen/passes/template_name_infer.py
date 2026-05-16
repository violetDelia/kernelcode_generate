"""Template-name inference pass.


功能说明:
- 为函数内 `NnMemoryType` block argument、operand 与 result 推导并写回 `template_name`。
- 基于 `TemplateNameGraph` 与已注册 operation 约束求解稳定 `T1/T2/...` 名称。
- 当前文件内 helper 仅服务本 pass 的 IR 遍历和 SSA type 写回，不属于公开 API。

API 列表:
- `class TemplateNameInferPass(fold: bool = True)`
- `TemplateNameInferPass.from_options(options: dict[str, str]) -> TemplateNameInferPass`
- `TemplateNameInferPass.apply(self, ctx: Context, module: ModuleOp) -> None`

使用示例:
- from kernel_gen.passes.template_name_infer import TemplateNameInferPass
- TemplateNameInferPass().apply(Context(), module)

关联文件:
- spec: spec/pass/template_name_infer.md
- test: test/passes/test_template_name_infer.py
- 功能实现: kernel_gen/passes/template_name_infer.py
"""

from __future__ import annotations

from xdsl.context import Context
from xdsl.dialects import func
from xdsl.dialects.builtin import ModuleOp
from xdsl.ir import Block, Operation, SSAValue
from xdsl.rewriter import Rewriter

from kernel_gen.dialect.arch import ArchLaunchOp
from kernel_gen.core.error import ErrorKind, ErrorModule, KernelCodeError
from kernel_gen.dialect.nn import NnMemoryType, copy_memory_type_with_template_name
from kernel_gen.passes.pass_manager import Pass
from kernel_gen.passes.template_name_constraints import build_template_constraints
from kernel_gen.passes.template_name_default_constraints import register_default_template_constraints
from kernel_gen.passes.template_name_graph import Same, TemplateNameGraph, TemplateNameValue


def _template_infer_error(message: str) -> KernelCodeError:
    """构造 template-name infer 错误。

    功能说明:
    - 统一 pass option 与 IR 合同错误文本。

    使用示例:
    - raise _template_infer_error("unknown option")
    """

    return KernelCodeError(ErrorKind.CONTRACT, ErrorModule.PASS, f"TemplateNameInferPassError: {message}")


def _block_owner_op(block: Block, fallback: Operation) -> Operation:
    """读取 block 所属 operation。

    功能说明:
    - `BlockArgument` 约束需要一个稳定 operation 来源；无父 op 时退回函数 op。

    使用示例:
    - owner = _block_owner_op(block, func_op)
    """

    owner = block.parent_op()
    return fallback if owner is None else owner


def _walk_blocks(op: Operation) -> tuple[Block, ...]:
    """递归收集 operation 下所有 block。

    功能说明:
    - 覆盖函数体和嵌套 region 的 block arguments。

    使用示例:
    - blocks = _walk_blocks(func_op)
    """

    blocks: list[Block] = []
    for region in op.regions:
        for block in region.blocks:
            blocks.append(block)
            for inner_op in block.ops:
                blocks.extend(_walk_blocks(inner_op))
    return tuple(blocks)


def _function_signature_memory_items(func_op: func.FuncOp) -> tuple[TemplateNameValue, ...]:
    """收集函数签名 memory block argument。

    功能说明:
    - 每个函数入口 `NnMemoryType` block argument 作为签名种子加入图。
    - 嵌套 region block argument 不作为默认命名种子。

    使用示例:
    - items = _function_signature_memory_items(func_op)
    """

    items: list[TemplateNameValue] = []
    for index, arg in enumerate(func_op.args):
        if isinstance(arg.type, NnMemoryType):
            items.append(TemplateNameValue(arg, func_op, "block_arg", index))
    return tuple(items)


def _memory_block_arg_items(func_op: func.FuncOp) -> tuple[TemplateNameValue, ...]:
    """收集非签名 memory block argument。

    功能说明:
    - 嵌套 region 的 memory block argument 进入图但不触发默认 `Tn` 命名。

    使用示例:
    - items = _memory_block_arg_items(func_op)
    """

    signature_values = set(func_op.args)
    items: list[TemplateNameValue] = []
    for block in _walk_blocks(func_op):
        owner = _block_owner_op(block, func_op)
        for index, arg in enumerate(block.args):
            if arg in signature_values:
                continue
            if isinstance(arg.type, NnMemoryType):
                items.append(TemplateNameValue(arg, owner, "block_arg", index))
    return tuple(items)


def _memory_result_items(op: Operation) -> tuple[TemplateNameValue, ...]:
    """收集 operation 的 memory result。

    功能说明:
    - 未被 constraints 覆盖的 memory result 也作为独立可命名节点。

    使用示例:
    - items = _memory_result_items(op)
    """

    return tuple(
        TemplateNameValue(result, op, "result", index)
        for index, result in enumerate(op.results)
        if isinstance(result.type, NnMemoryType)
    )


def _write_value_template_name(value: SSAValue, template_name: str) -> None:
    """把 template name 写回 SSA value type。

    功能说明:
    - 通过 xDSL 公开 rewriter 入口替换为带新类型的 SSA value。
    - 写入的新类型复用公开 `copy_memory_type_with_template_name(...)` 构造。

    使用示例:
    - _write_value_template_name(value, "T1")
    """

    if not isinstance(value.type, NnMemoryType):
        return
    Rewriter.replace_value_with_new_type(
        value,
        copy_memory_type_with_template_name(value.type, template_name),
    )


def _should_skip_op_constraints(op: Operation) -> bool:
    """判断是否跳过 operation constraint 构建。

    功能说明:
    - `func.return` 只消费已推导的返回 operand，不定义新的 memory 等价关系。

    使用示例:
    - if _should_skip_op_constraints(op): ...
    """

    return op.name == "func.return"


def _module_func_map(module: ModuleOp) -> dict[str, func.FuncOp]:
    """收集 module 内顶层函数符号表。

    功能说明:
    - 为 `arch.launch @callee` 到 callee 函数签名的模板等价约束提供查找表。
    - 只记录公开 `func.func` 符号名，不读取其它隐藏状态。

    使用示例:
    - funcs = _module_func_map(module)
    """

    funcs: dict[str, func.FuncOp] = {}
    for op in module.ops:
        if isinstance(op, func.FuncOp):
            funcs[op.sym_name.data] = op
    return funcs


def _launch_template_constraints(
    launch_op: Operation,
    funcs: dict[str, func.FuncOp],
) -> tuple[Same, ...]:
    """构造 `arch.launch` wrapper arg 与 callee arg 的模板等价约束。

    功能说明:
    - `arch.launch` 只转发 wrapper 参数，C++ wrapper/device 模板名必须一致。
    - 非 memory 参数不参与 template-name 推导。

    使用示例:
    - constraints = _launch_template_constraints(launch_op, funcs)
    """

    if not isinstance(launch_op, ArchLaunchOp):
        return ()
    callee_name = launch_op.callee.root_reference.data
    callee = funcs.get(callee_name)
    if callee is None:
        return ()
    launch_args = [SSAValue.get(arg) for arg in launch_op.args]
    callee_args = list(callee.args)
    if len(launch_args) != len(callee_args):
        raise _template_infer_error("arch.launch arg count must match callee args")
    constraints: list[Same] = []
    for index, (launch_arg, callee_arg) in enumerate(zip(launch_args, callee_args, strict=True)):
        if not isinstance(launch_arg.type, NnMemoryType) and not isinstance(callee_arg.type, NnMemoryType):
            continue
        if not isinstance(launch_arg.type, NnMemoryType) or not isinstance(callee_arg.type, NnMemoryType):
            raise _template_infer_error("arch.launch memory arg type must match callee arg type")
        constraints.append(
            Same(
                TemplateNameValue(launch_arg, launch_op, "operand", index + 4),
                TemplateNameValue(callee_arg, callee, "block_arg", index),
            )
        )
    return tuple(constraints)


class TemplateNameInferPass(Pass):
    """推导 `NnMemoryType.template_name` 的 ModulePass。

    功能说明:
    - 对每个 `func.func` 独立求解 template-name 图。
    - 函数签名和 operation result 的 memory type 都会被写回 template name。

    使用示例:
    - TemplateNameInferPass().apply(Context(), module)

    关联文件:
    - spec: spec/pass/template_name_infer.md
    - test: test/passes/test_template_name_infer.py
    - 功能实现: kernel_gen/passes/template_name_infer.py
    """

    name = "template-name-infer"

    @classmethod
    def from_options(cls, options: dict[str, str]) -> "TemplateNameInferPass":
        """从 registry options 构造 pass。

        功能说明:
        - 当前 pass 不接受专属 options；非空 options 稳定失败。

        使用示例:
        - pass_obj = TemplateNameInferPass.from_options({})
        """

        if options:
            unknown = ", ".join(sorted(options))
            raise _template_infer_error(f"unknown options: {unknown}")
        return cls()

    def apply(self, ctx: Context, module: ModuleOp) -> None:
        """执行 template-name 推导。

        功能说明:
        - 注册默认约束。
        - 对 module 内函数统一建图，保证 `arch.launch` wrapper/device 参数模板名一致。

        使用示例:
        - TemplateNameInferPass().apply(Context(), module)
        """

        _ = ctx
        register_default_template_constraints()
        funcs = _module_func_map(module)
        graph = TemplateNameGraph()
        for func_op in funcs.values():
            if func_op.is_declaration:
                continue
            for item in _function_signature_memory_items(func_op):
                graph.add_signature_seed(item)
            for item in _memory_block_arg_items(func_op):
                graph.add_value(item)
            for op in func_op.walk():
                for item in _memory_result_items(op):
                    graph.add_value(item)
                if _should_skip_op_constraints(op):
                    continue
                graph.add_constraints(build_template_constraints(op))
                graph.add_constraints(_launch_template_constraints(op, funcs))
        solution = graph.solve()
        for value, template_name in solution.names.items():
            _write_value_template_name(value, template_name)
        for func_op in funcs.values():
            if not func_op.is_declaration:
                func_op.update_function_type()

    def _apply_to_func(self, func_op: func.FuncOp) -> None:
        """对单个函数执行推导。

        功能说明:
        - 函数内 memory block argument 和 result 均参与命名。

        使用示例:
        - self._apply_to_func(func_op)
        """

        if func_op.is_declaration:
            return
        graph = TemplateNameGraph()
        for item in _function_signature_memory_items(func_op):
            graph.add_signature_seed(item)
        for item in _memory_block_arg_items(func_op):
            graph.add_value(item)
        for op in func_op.walk():
            for item in _memory_result_items(op):
                graph.add_value(item)
            if _should_skip_op_constraints(op):
                continue
            graph.add_constraints(build_template_constraints(op))
        solution = graph.solve()
        for value, template_name in solution.names.items():
            _write_value_template_name(value, template_name)
        func_op.update_function_type()


__all__ = ["TemplateNameInferPass"]
