"""Template-name inference graph.


功能说明:
- 提供 `nn.memory.template_name` 推导所需的等价类图与求解结果。
- 图只处理公开 `NnMemoryType` SSA 值，非 memory SSA 不进入求解域。
- 当前文件内 helper 仅服务图构建与求解，不作为公开 API。

API 列表:
- `class TemplateNameValue(value: SSAValue, op: Operation, kind: Literal["operand", "result", "block_arg"], index: int)`
- `class Same(lhs: TemplateNameValue, rhs: TemplateNameValue)`
- `class VerifyOnly(item: TemplateNameValue)`
- `class TemplateNameSolution(names: Mapping[SSAValue, str])`
- `TemplateNameSolution.name_of(self, value: SSAValue) -> str | None`
- `class TemplateNameGraph()`
- `TemplateNameGraph.add_value(self, item: TemplateNameValue) -> None`
- `TemplateNameGraph.add_constraint(self, constraint: TemplateNameConstraint) -> None`
- `TemplateNameGraph.add_constraints(self, constraints: Sequence[TemplateNameConstraint]) -> None`
- `TemplateNameGraph.add_signature_seed(self, item: TemplateNameValue) -> None`
- `TemplateNameGraph.solve(self) -> TemplateNameSolution`

使用示例:
- graph = TemplateNameGraph()
- graph.add_constraint(Same(lhs, rhs))
- solution = graph.solve()

关联文件:
- spec: spec/pass/template_name_graph.md
- test: test/passes/test_template_name_infer.py
- 功能实现: kernel_gen/passes/template_name_graph.py
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Literal, TypeAlias

from xdsl.ir import Operation, SSAValue

from kernel_gen.core.error import ErrorKind, ErrorModule, KernelCodeError
from kernel_gen.dialect.nn import NnMemoryType


@dataclass(frozen=True)
class TemplateNameValue:
    """Template-name 图节点。

    功能说明:
    - 记录参与 template-name 推导的 SSA value 及其来源位置。
    - `kind/index` 仅用于错误诊断与稳定顺序，不改变 SSA 本身。

    使用示例:
    - item = TemplateNameValue(value, op, "operand", 0)

    关联文件:
    - spec: spec/pass/template_name_graph.md
    - test: test/passes/test_template_name_infer.py
    - 功能实现: kernel_gen/passes/template_name_graph.py
    """

    value: SSAValue
    op: Operation
    kind: Literal["operand", "result", "block_arg"]
    index: int


@dataclass(frozen=True)
class Same:
    """两个 memory SSA 必须共享 template name。

    功能说明:
    - 表示同一 dtype/template family 的等价约束。

    使用示例:
    - constraint = Same(lhs, rhs)

    关联文件:
    - spec: spec/pass/template_name_graph.md
    - test: test/passes/test_template_name_infer.py
    - 功能实现: kernel_gen/passes/template_name_graph.py
    """

    lhs: TemplateNameValue
    rhs: TemplateNameValue


@dataclass(frozen=True)
class VerifyOnly:
    """只校验 memory SSA 可承载 template name，不建立等价关系。

    功能说明:
    - 用于 `kernel.matmul`、`dma.alloc` 等不应强制共享 template name 的 memory 位置。

    使用示例:
    - constraint = VerifyOnly(item)

    关联文件:
    - spec: spec/pass/template_name_graph.md
    - test: test/passes/test_template_name_infer.py
    - 功能实现: kernel_gen/passes/template_name_graph.py
    """

    item: TemplateNameValue


TemplateNameConstraint: TypeAlias = Same | VerifyOnly


@dataclass(frozen=True)
class TemplateNameSolution:
    """Template-name 求解结果。

    功能说明:
    - 按 SSA value 保存推导出的 template name。
    - 未进入图的 value 返回 `None`。

    使用示例:
    - name = solution.name_of(value)

    关联文件:
    - spec: spec/pass/template_name_graph.md
    - test: test/passes/test_template_name_infer.py
    - 功能实现: kernel_gen/passes/template_name_graph.py
    """

    names: Mapping[SSAValue, str]

    def name_of(self, value: SSAValue) -> str | None:
        """读取指定 SSA value 的 template name。

        功能说明:
        - 对未进入图的 value 返回 `None`。

        使用示例:
        - assert solution.name_of(value) == "T1"
        """

        return self.names.get(value)


def _template_graph_error(message: str) -> KernelCodeError:
    """构造 template-name 图错误。

    功能说明:
    - 统一错误模块与稳定前缀。

    使用示例:
    - raise _template_graph_error("conflicting template_name")
    """

    return KernelCodeError(ErrorKind.CONTRACT, ErrorModule.PASS, f"TemplateNameGraphError: {message}")


class TemplateNameGraph:
    """Template-name 等价类图。

    功能说明:
    - 收集 `Same` 与 `VerifyOnly` 约束并求解稳定 `T1/T2/...` 名称。
    - 已显式携带 template name 的 memory type 作为等价类种子。

    使用示例:
    - graph = TemplateNameGraph()
    - graph.add_value(item)
    - solution = graph.solve()

    关联文件:
    - spec: spec/pass/template_name_graph.md
    - test: test/passes/test_template_name_infer.py
    - 功能实现: kernel_gen/passes/template_name_graph.py
    """

    def __init__(self) -> None:
        self._items: dict[SSAValue, TemplateNameValue] = {}
        self._order: list[SSAValue] = []
        self._signature_seeds: set[SSAValue] = set()
        self._constraints: list[TemplateNameConstraint] = []

    def add_value(self, item: TemplateNameValue) -> None:
        """添加 memory SSA value。

        功能说明:
        - 仅接受 `NnMemoryType` SSA。
        - 重复添加同一个 SSA value 保留首次顺序。

        使用示例:
        - graph.add_value(item)
        """

        if not isinstance(item.value.type, NnMemoryType):
            raise _template_graph_error("value must be nn.memory")
        if item.value not in self._items:
            self._order.append(item.value)
        self._items[item.value] = item

    def add_constraint(self, constraint: TemplateNameConstraint) -> None:
        """添加单条约束。

        功能说明:
        - `Same` 自动添加左右两侧 value。
        - `VerifyOnly` 自动添加目标 value。

        使用示例:
        - graph.add_constraint(Same(lhs, rhs))
        """

        if isinstance(constraint, Same):
            self.add_value(constraint.lhs)
            self.add_value(constraint.rhs)
        else:
            self.add_value(constraint.item)
        self._constraints.append(constraint)

    def add_constraints(self, constraints: Sequence[TemplateNameConstraint]) -> None:
        """批量添加约束。

        功能说明:
        - 保持输入顺序写入图，保证求解名称稳定。

        使用示例:
        - graph.add_constraints(constraints)
        """

        for constraint in constraints:
            self.add_constraint(constraint)

    def add_signature_seed(self, item: TemplateNameValue) -> None:
        """添加函数签名侧 memory 种子。

        功能说明:
        - 签名种子不强制建立等价关系，只参与稳定命名顺序。

        使用示例:
        - graph.add_signature_seed(item)
        """

        self.add_value(item)
        self._signature_seeds.add(item.value)

    def solve(self) -> TemplateNameSolution:
        """求解 template name。

        功能说明:
        - `Same` 约束形成等价类。
        - 等价类存在多个不同显式 template name 时稳定失败。
        - 无显式名称的等价类按首次出现顺序生成 `T1/T2/...`。

        使用示例:
        - solution = graph.solve()
        """

        parent: dict[SSAValue, SSAValue] = {value: value for value in self._order}

        for constraint in self._constraints:
            if isinstance(constraint, Same):
                self._union(parent, constraint.lhs.value, constraint.rhs.value)

        explicit_names: dict[SSAValue, set[str]] = {}
        for value in self._order:
            root = self._find(parent, value)
            value.type.verify()
            explicit_name = value.type.template_name.data
            if not explicit_name:
                continue
            explicit_names.setdefault(root, set()).add(explicit_name)

        seeded_roots = {self._find(parent, value) for value in self._signature_seeds}
        used_names = {name for names in explicit_names.values() for name in names}
        class_name: dict[SSAValue, str] = {}
        next_id = 1
        for value in self._order:
            root = self._find(parent, value)
            if root in class_name:
                continue
            names = explicit_names.get(root, set())
            if len(names) > 1:
                raise _template_graph_error("conflicting template_name in same equivalence class")
            if names:
                name = next(iter(names))
            elif root in seeded_roots:
                name = f"T{next_id}"
                while name in used_names:
                    next_id += 1
                    name = f"T{next_id}"
                next_id += 1
            else:
                continue
            class_name[root] = name
            used_names.add(name)

        return TemplateNameSolution(
            {
                value: class_name[self._find(parent, value)]
                for value in self._order
                if self._find(parent, value) in class_name
            }
        )

    def _find(self, parent: dict[SSAValue, SSAValue], value: SSAValue) -> SSAValue:
        """查找并压缩并查集根。

        功能说明:
        - 仅供当前图求解内部使用。

        使用示例:
        - root = self._find(parent, value)
        """

        root = parent[value]
        if root is not value:
            root = self._find(parent, root)
            parent[value] = root
        return root

    def _union(self, parent: dict[SSAValue, SSAValue], lhs: SSAValue, rhs: SSAValue) -> None:
        """合并两个并查集分量。

        功能说明:
        - 保持首次出现的根作为合并后代表，稳定后续命名顺序。

        使用示例:
        - self._union(parent, lhs, rhs)
        """

        lhs_root = self._find(parent, lhs)
        rhs_root = self._find(parent, rhs)
        if lhs_root is rhs_root:
            return
        parent[rhs_root] = lhs_root
