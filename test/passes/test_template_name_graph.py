"""template-name graph tests.


功能说明:
- 覆盖 `kernel_gen.passes.template_name_graph` 的公开 graph API。

使用示例:
- pytest -q test/passes/test_template_name_graph.py

关联文件:
- 功能实现: kernel_gen/passes/template_name_graph.py
- Spec 文档: spec/pass/template_name_graph.md
- 测试文件: test/passes/test_template_name_graph.py
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest
from xdsl.dialects.builtin import ArrayAttr, FunctionType, i32
from xdsl.dialects import func
from xdsl.ir import Block, Region

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from kernel_gen.core.error import KernelCodeError
from kernel_gen.dialect.nn import NnMemorySpaceAttr, NnMemoryType
from kernel_gen.dialect.symbol import SymbolExprAttr
from kernel_gen.passes.template_name_graph import Same, TemplateNameGraph, TemplateNameValue


def _symbol_array(values: tuple[str, ...]) -> ArrayAttr:
    """构造 SymbolExprAttr 数组。"""

    return ArrayAttr([SymbolExprAttr.from_expr(value) for value in values])


def _memory_type(template_name: str | None = None) -> NnMemoryType:
    """构造测试用公开 memory type。"""

    return NnMemoryType(
        _symbol_array(("M",)),
        _symbol_array(("1",)),
        i32,
        NnMemorySpaceAttr.from_name("global"),
        template_name=template_name,
    )


def _arg_items(*types: NnMemoryType) -> tuple[TemplateNameValue, ...]:
    """构造函数参数对应的 TemplateNameValue。"""

    block = Block(arg_types=types)
    func_op = func.FuncOp("graph_kernel", FunctionType.from_lists(types, []), Region(block))
    return tuple(TemplateNameValue(arg, func_op, "block_arg", index) for index, arg in enumerate(func_op.args))


def test_template_name_graph_assigns_seeded_same_family() -> None:
    """验证 signature seed 触发稳定默认 template name。"""

    lhs, rhs = _arg_items(_memory_type(), _memory_type())
    graph = TemplateNameGraph()
    graph.add_signature_seed(lhs)
    graph.add_constraint(Same(lhs, rhs))
    solution = graph.solve()
    assert solution.name_of(lhs.value) == "T1"
    assert solution.name_of(rhs.value) == "T1"


def test_template_name_graph_keeps_unseeded_family_empty() -> None:
    """验证无显式 name 且无 signature seed 的 family 不进入 solution。"""

    (item,) = _arg_items(_memory_type())
    graph = TemplateNameGraph()
    graph.add_value(item)
    assert graph.solve().name_of(item.value) is None


def test_template_name_graph_keeps_explicit_name_without_seed() -> None:
    """验证显式 template name 不依赖 signature seed。"""

    (item,) = _arg_items(_memory_type("Tout"))
    graph = TemplateNameGraph()
    graph.add_value(item)
    assert graph.solve().name_of(item.value) == "Tout"


def test_template_name_graph_rejects_conflicting_same_family_names() -> None:
    """验证 Same 等价类内多个显式 name 按公开错误语义失败。"""

    lhs, rhs = _arg_items(_memory_type("T1"), _memory_type("T2"))
    graph = TemplateNameGraph()
    graph.add_constraint(Same(lhs, rhs))
    with pytest.raises(KernelCodeError, match="conflicting template_name"):
        graph.solve()


def test_template_name_graph_auto_names_skip_later_explicit_names() -> None:
    """验证自动 `Tn` 会预先避让所有显式 template name。"""

    auto_item, explicit_item = _arg_items(_memory_type(), _memory_type("T1"))
    graph = TemplateNameGraph()
    graph.add_signature_seed(auto_item)
    graph.add_value(explicit_item)

    solution = graph.solve()

    assert solution.name_of(auto_item.value) == "T2"
    assert solution.name_of(explicit_item.value) == "T1"
