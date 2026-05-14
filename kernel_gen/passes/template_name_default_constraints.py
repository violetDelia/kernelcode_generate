"""Default template-name constraints.


功能说明:
- 注册仓库内置 dialect op 的 template-name 约束。
- 默认约束覆盖 `dma.*`、`kernel.*`、`arch.get_dynamic_memory` 与透明 cast。
- 当前文件内 builder 只作为注册表回调，不作为跨模块公开 API。

API 列表:
- `register_default_template_constraints() -> None`

使用示例:
- from kernel_gen.passes.template_name_default_constraints import register_default_template_constraints
- register_default_template_constraints()

关联文件:
- spec: spec/pass/template_name_default_constraints.md
- test: test/passes/test_template_name_infer.py
- 功能实现: kernel_gen/passes/template_name_default_constraints.py
"""

from __future__ import annotations

from xdsl.ir import Operation

from kernel_gen.core.error import KernelCodeError
from kernel_gen.dialect.nn import NnMemoryType
from kernel_gen.passes.template_name_constraints import (
    get_template_constraints,
    register_template_constraints,
)
from kernel_gen.passes.template_name_graph import Same, TemplateNameConstraint, TemplateNameValue, VerifyOnly

_DEFAULTS_REGISTERED = False


def _memory_values(op: Operation) -> tuple[TemplateNameValue, ...]:
    """收集 operation 中所有 memory operand/result。

    功能说明:
    - 按 operand 再 result 的公开顺序生成约束节点。

    使用示例:
    - values = _memory_values(op)
    """

    items: list[TemplateNameValue] = []
    for index, operand in enumerate(op.operands):
        if isinstance(operand.type, NnMemoryType):
            items.append(TemplateNameValue(operand, op, "operand", index))
    for index, result in enumerate(op.results):
        if isinstance(result.type, NnMemoryType):
            items.append(TemplateNameValue(result, op, "result", index))
    return tuple(items)


def _verify_all_memory_builder(op: Operation) -> tuple[TemplateNameConstraint, ...]:
    """生成仅校验所有 memory value 的约束。

    功能说明:
    - 用于 `kernel.matmul`、`dma.alloc`、`dma.cast` 等不强制共享 template name 的 op。

    使用示例:
    - constraints = _verify_all_memory_builder(op)
    """

    return tuple(VerifyOnly(item) for item in _memory_values(op))


def _same_all_memory_builder(op: Operation) -> tuple[TemplateNameConstraint, ...]:
    """生成所有 memory value 共享 template name 的约束。

    功能说明:
    - 用于 copy、view、reshape 与 elementwise kernel 等 element type 必须一致的 op。

    使用示例:
    - constraints = _same_all_memory_builder(op)
    """

    values = _memory_values(op)
    if not values:
        return ()
    first = values[0]
    constraints: list[TemplateNameConstraint] = [VerifyOnly(first)]
    constraints.extend(Same(first, item) for item in values[1:])
    return tuple(constraints)


def _register_default(op_name: str, builder) -> None:
    """注册单个默认约束。

    功能说明:
    - 对已存在约束保持 no-op，避免重复加载默认约束时失败。
    - 只通过公开 `get_template_constraints(...)` 判断注册状态。

    使用示例:
    - _register_default("dma.copy", _same_all_memory_builder)
    """

    try:
        get_template_constraints(op_name)
    except KernelCodeError:
        register_template_constraints(op_name, builder)


def register_default_template_constraints() -> None:
    """注册内置 operation 的 template-name 默认约束。

    功能说明:
    - 幂等注册 `dma.*`、`kernel.*`、`arch.get_dynamic_memory` 与透明 cast。
    - 未列入的 memory op 由 `build_template_constraints(...)` 稳定失败，暴露待补合同。

    使用示例:
    - register_default_template_constraints()

    关联文件:
    - spec: spec/pass/template_name_default_constraints.md
    - test: test/passes/test_template_name_infer.py
    - 功能实现: kernel_gen/passes/template_name_default_constraints.py
    """

    global _DEFAULTS_REGISTERED
    if _DEFAULTS_REGISTERED:
        return

    for op_name in (
        "dma.copy",
        "dma.broadcast",
        "dma.transpose",
        "dma.load",
        "dma.store",
        "dma.slice",
        "dma.deslice",
        "dma.view",
        "dma.reshape",
        "builtin.unrealized_conversion_cast",
        "kernel.binary_elewise",
        "kernel.exp",
        "kernel.reduce",
        "kernel.reduce_min",
        "kernel.img2col1d",
        "kernel.img2col2d",
        "kernel.select",
    ):
        _register_default(op_name, _same_all_memory_builder)

    for op_name in (
        "arch.get_dynamic_memory",
        "arch.launch",
        "dma.alloc",
        "dma.fill",
        "dma.free",
        "dma.cast",
        "dma.subview",
        "kernel.matmul",
        "symbol.get_dim",
        "symbol.get_stride",
    ):
        _register_default(op_name, _verify_all_memory_builder)

    _DEFAULTS_REGISTERED = True


__all__ = ["register_default_template_constraints"]
