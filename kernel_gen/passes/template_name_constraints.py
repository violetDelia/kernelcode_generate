"""Template-name constraint registry.


功能说明:
- 提供 operation -> template-name constraint 的公开注册与构建入口。
- 约束只引用公开 operand/result 位置，不读取 operation 私有实现细节。
- 当前文件内 helper 仅负责 ref 解析与错误文本归一化，不属于公开 API。

API 列表:
- `class TemplateValueRef(kind: Literal["operand", "result"], index: int)`
- `class SameSpec(lhs: TemplateValueRef, rhs: TemplateValueRef)`
- `class VerifyOnlySpec(item: TemplateValueRef)`
- `register_template_constraints(op_name: str, constraints: tuple[TemplateConstraintSpec, ...] | TemplateConstraintBuilder) -> None`
- `get_template_constraints(op_name: str) -> tuple[TemplateConstraintSpec, ...] | TemplateConstraintBuilder`
- `build_template_constraints(op: Operation) -> tuple[TemplateNameConstraint, ...]`

使用示例:
- register_template_constraints("dma.copy", (SameSpec(TemplateValueRef("operand", 0), TemplateValueRef("operand", 1)),))
- constraints = build_template_constraints(op)

关联文件:
- spec: spec/pass/template_name_constraints.md
- test: test/passes/test_template_name_infer.py
- 功能实现: kernel_gen/passes/template_name_constraints.py
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Literal, TypeAlias

from xdsl.ir import Operation, SSAValue

from kernel_gen.core.error import ErrorKind, ErrorModule, KernelCodeError
from kernel_gen.dialect.nn import NnMemoryType
from kernel_gen.passes.template_name_graph import (
    Same,
    TemplateNameConstraint,
    TemplateNameValue,
    VerifyOnly,
)


@dataclass(frozen=True)
class TemplateValueRef:
    """Operation memory value 引用。

    功能说明:
    - 用公开 `operand/result` 序号描述约束位置。

    使用示例:
    - ref = TemplateValueRef("operand", 0)

    关联文件:
    - spec: spec/pass/template_name_constraints.md
    - test: test/passes/test_template_name_infer.py
    - 功能实现: kernel_gen/passes/template_name_constraints.py
    """

    kind: Literal["operand", "result"]
    index: int


@dataclass(frozen=True)
class SameSpec:
    """两个引用位置必须共享 template name。

    功能说明:
    - registry 层的静态 `Same` 约束规格。

    使用示例:
    - spec = SameSpec(TemplateValueRef("operand", 0), TemplateValueRef("result", 0))

    关联文件:
    - spec: spec/pass/template_name_constraints.md
    - test: test/passes/test_template_name_infer.py
    - 功能实现: kernel_gen/passes/template_name_constraints.py
    """

    lhs: TemplateValueRef
    rhs: TemplateValueRef


@dataclass(frozen=True)
class VerifyOnlySpec:
    """只校验引用位置承载 memory template name。

    功能说明:
    - registry 层的静态 `VerifyOnly` 约束规格。

    使用示例:
    - spec = VerifyOnlySpec(TemplateValueRef("operand", 0))

    关联文件:
    - spec: spec/pass/template_name_constraints.md
    - test: test/passes/test_template_name_infer.py
    - 功能实现: kernel_gen/passes/template_name_constraints.py
    """

    item: TemplateValueRef


TemplateConstraintSpec: TypeAlias = SameSpec | VerifyOnlySpec
TemplateConstraintBuilder: TypeAlias = Callable[[Operation], tuple[TemplateNameConstraint, ...]]
_ConstraintRegistryEntry: TypeAlias = tuple[TemplateConstraintSpec, ...] | TemplateConstraintBuilder

_TEMPLATE_CONSTRAINTS: dict[str, _ConstraintRegistryEntry] = {}


def _template_constraint_error(message: str) -> KernelCodeError:
    """构造 template-name constraint 错误。

    功能说明:
    - 统一 registry 与 builder 的错误归属。

    使用示例:
    - raise _template_constraint_error("unknown memory op")
    """

    return KernelCodeError(ErrorKind.CONTRACT, ErrorModule.PASS, f"TemplateNameConstraintError: {message}")


def register_template_constraints(op_name: str, constraints: _ConstraintRegistryEntry) -> None:
    """注册 operation 的 template-name 约束。

    功能说明:
    - `op_name` 使用 operation 公开 `name`。
    - 同名重复注册稳定失败，默认约束由默认注册入口保证幂等。

    使用示例:
    - register_template_constraints("dma.copy", constraints)

    关联文件:
    - spec: spec/pass/template_name_constraints.md
    - test: test/passes/test_template_name_infer.py
    - 功能实现: kernel_gen/passes/template_name_constraints.py
    """

    if not isinstance(op_name, str) or not op_name.strip():
        raise _template_constraint_error("op_name must be non-empty string")
    if op_name in _TEMPLATE_CONSTRAINTS:
        raise _template_constraint_error(f"constraints for '{op_name}' are already registered")
    if not isinstance(constraints, tuple) and not callable(constraints):
        raise _template_constraint_error("constraints must be tuple or callable builder")
    _TEMPLATE_CONSTRAINTS[op_name] = constraints


def get_template_constraints(op_name: str) -> _ConstraintRegistryEntry:
    """读取 operation 的 template-name 约束规格或 builder。

    功能说明:
    - 未注册时稳定失败，避免调用方把缺失约束误判为 no-op。

    使用示例:
    - entry = get_template_constraints("dma.copy")

    关联文件:
    - spec: spec/pass/template_name_constraints.md
    - test: test/passes/test_template_name_infer.py
    - 功能实现: kernel_gen/passes/template_name_constraints.py
    """

    if not isinstance(op_name, str) or not op_name.strip():
        raise _template_constraint_error("op_name must be non-empty string")
    try:
        return _TEMPLATE_CONSTRAINTS[op_name]
    except KeyError as exc:
        raise _template_constraint_error(f"constraints for '{op_name}' are not registered") from exc


def build_template_constraints(op: Operation) -> tuple[TemplateNameConstraint, ...]:
    """根据 operation 构造 template-name 约束。

    功能说明:
    - 对已注册 operation，返回静态或动态约束实例。
    - 未注册且携带 memory operand/result 的 operation 稳定失败，避免未知 pass 默默漏推导。
    - 未注册且不携带 memory operand/result 的 operation 返回空约束。

    使用示例:
    - constraints = build_template_constraints(op)

    关联文件:
    - spec: spec/pass/template_name_constraints.md
    - test: test/passes/test_template_name_infer.py
    - 功能实现: kernel_gen/passes/template_name_constraints.py
    """

    entry = _TEMPLATE_CONSTRAINTS.get(op.name)
    if entry is None:
        if _has_memory_values(op):
            raise _template_constraint_error(f"missing constraints for memory op '{op.name}'")
        return ()
    if callable(entry):
        return entry(op)
    return tuple(_constraint_from_spec(op, spec) for spec in entry)


def _has_memory_values(op: Operation) -> bool:
    """判断 operation 是否携带 memory operand/result。

    功能说明:
    - 仅检查公开 `operands/results` 序列。

    使用示例:
    - if _has_memory_values(op): ...
    """

    return any(isinstance(value.type, NnMemoryType) for value in (*op.operands, *op.results))


def _template_name_value(op: Operation, ref: TemplateValueRef) -> TemplateNameValue:
    """把静态引用转换为图节点。

    功能说明:
    - 校验引用 kind/index 与目标 SSA 类型。

    使用示例:
    - item = _template_name_value(op, TemplateValueRef("operand", 0))
    """

    values: tuple[SSAValue, ...]
    if ref.kind == "operand":
        values = tuple(op.operands)
    else:
        values = tuple(op.results)
    if ref.index < 0 or ref.index >= len(values):
        raise _template_constraint_error(f"invalid {ref.kind} index {ref.index} for '{op.name}'")
    value = values[ref.index]
    if not isinstance(value.type, NnMemoryType):
        raise _template_constraint_error(f"{op.name} {ref.kind} {ref.index} must be nn.memory")
    return TemplateNameValue(value, op, ref.kind, ref.index)


def _constraint_from_spec(op: Operation, spec: TemplateConstraintSpec) -> TemplateNameConstraint:
    """把 registry 静态规格转换为图约束。

    功能说明:
    - 仅处理公开 `SameSpec` / `VerifyOnlySpec`。

    使用示例:
    - constraint = _constraint_from_spec(op, spec)
    """

    if isinstance(spec, SameSpec):
        return Same(_template_name_value(op, spec.lhs), _template_name_value(op, spec.rhs))
    return VerifyOnly(_template_name_value(op, spec.item))


__all__ = [
    "TemplateValueRef",
    "SameSpec",
    "VerifyOnlySpec",
    "TemplateConstraintSpec",
    "TemplateConstraintBuilder",
    "register_template_constraints",
    "get_template_constraints",
    "build_template_constraints",
]
