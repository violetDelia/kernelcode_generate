"""template-name infer pass tests.


功能说明:
- 覆盖 `TemplateNameGraph`、constraint registry 与 `TemplateNameInferPass` 的公开合同。

使用示例:
- pytest -q test/passes/test_template_name_infer.py

关联文件:
- 功能实现: kernel_gen/passes/template_name_graph.py
- 功能实现: kernel_gen/passes/template_name_constraints.py
- 功能实现: kernel_gen/passes/template_name_infer.py
- Spec 文档: spec/pass/template_name_infer.md
- 测试文件: test/passes/test_template_name_infer.py
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest
from xdsl.context import Context
from xdsl.dialects import func
from xdsl.dialects.builtin import ArrayAttr, FunctionType, ModuleOp, i32
from xdsl.ir import Block, Region

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from kernel_gen.core.error import KernelCodeError
from kernel_gen.dialect.dma import DmaCopyOp
from kernel_gen.dialect.nn import NnMemorySpaceAttr, NnMemoryType, memory_template_name
from kernel_gen.dialect.symbol import SymbolExprAttr
from kernel_gen.passes.registry import build_registered_pass, load_builtin_passes
from kernel_gen.passes.template_name_graph import Same, TemplateNameGraph, TemplateNameValue
from kernel_gen.passes.template_name_infer import TemplateNameInferPass


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


def _copy_module(lhs_type: NnMemoryType, rhs_type: NnMemoryType) -> tuple[ModuleOp, func.FuncOp]:
    """构造包含 dma.copy 的测试 module。"""

    block = Block(arg_types=[lhs_type, rhs_type])
    copy_op = DmaCopyOp(block.args[0], block.args[1])
    block.add_ops([copy_op, func.ReturnOp()])
    func_op = func.FuncOp("copy_kernel", FunctionType.from_lists([lhs_type, rhs_type], []), Region(block))
    return ModuleOp([func_op]), func_op


def test_template_name_graph_solves_same_constraint() -> None:
    """验证图求解会把 Same 约束合并为同一 template name。"""

    module, func_op = _copy_module(_memory_type(), _memory_type())
    value0 = TemplateNameValue(func_op.args[0], func_op, "block_arg", 0)
    value1 = TemplateNameValue(func_op.args[1], func_op, "block_arg", 1)
    graph = TemplateNameGraph()
    graph.add_signature_seed(value0)
    graph.add_constraint(Same(value0, value1))
    solution = graph.solve()
    assert solution.name_of(func_op.args[0]) == "T1"
    assert solution.name_of(func_op.args[1]) == "T1"
    assert module is not None


def test_template_name_infer_pass_writes_function_arg_types() -> None:
    """验证 pass 按 dma.copy 约束写回函数参数 template_name。"""

    module, func_op = _copy_module(_memory_type(), _memory_type())
    TemplateNameInferPass().apply(Context(), module)
    assert memory_template_name(func_op.args[0].type) == "T1"
    assert memory_template_name(func_op.args[1].type) == "T1"
    assert memory_template_name(func_op.function_type.inputs.data[0]) == "T1"
    assert memory_template_name(func_op.function_type.inputs.data[1]) == "T1"


def test_template_name_infer_rejects_conflicting_explicit_names() -> None:
    """验证同一等价类内显式 template name 冲突会失败。"""

    module, _func_op = _copy_module(_memory_type("T1"), _memory_type("T2"))
    with pytest.raises(KernelCodeError, match="conflicting template_name"):
        TemplateNameInferPass().apply(Context(), module)


def test_template_name_infer_registered_as_builtin_pass() -> None:
    """验证 registry 可按公开名称构造 template-name-infer pass。"""

    load_builtin_passes()
    pass_obj = build_registered_pass("template-name-infer")
    assert isinstance(pass_obj, TemplateNameInferPass)
