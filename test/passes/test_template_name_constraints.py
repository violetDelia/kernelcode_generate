"""template-name constraint registry tests.


功能说明:
- 覆盖 `kernel_gen.passes.template_name_constraints` 与默认约束注册入口。

使用示例:
- pytest -q test/passes/test_template_name_constraints.py

关联文件:
- 功能实现: kernel_gen/passes/template_name_constraints.py
- 功能实现: kernel_gen/passes/template_name_default_constraints.py
- Spec 文档: spec/pass/template_name_constraints.md
- 测试文件: test/passes/test_template_name_constraints.py
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest
from xdsl.dialects.builtin import ArrayAttr, i32
from xdsl.ir import SSAValue
from xdsl.irdl import IRDLOperation, irdl_op_definition, operand_def
from xdsl.utils.test_value import create_ssa_value

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from kernel_gen.core.error import KernelCodeError
from kernel_gen.dialect.dma import DmaCopyOp
from kernel_gen.dialect.nn import NnMemorySpaceAttr, NnMemoryType
from kernel_gen.dialect.symbol import SymbolExprAttr
from kernel_gen.passes.template_name_constraints import (
    SameSpec,
    TemplateValueRef,
    VerifyOnlySpec,
    build_template_constraints,
    get_template_constraints,
    register_template_constraints,
)
from kernel_gen.passes.template_name_default_constraints import register_default_template_constraints
from kernel_gen.passes.template_name_graph import Same, VerifyOnly


@irdl_op_definition
class TemplateConstraintTestOp(IRDLOperation):
    """测试用公开 operation 形态。"""

    name = "test.template_constraint"
    lhs = operand_def(NnMemoryType)
    rhs = operand_def(NnMemoryType)

    def __init__(self, lhs: SSAValue, rhs: SSAValue) -> None:
        super().__init__(operands=[lhs, rhs])


@irdl_op_definition
class UnknownMemoryConstraintTestOp(IRDLOperation):
    """测试用未注册 memory operation。"""

    name = "test.template_constraint_unknown"
    source = operand_def(NnMemoryType)

    def __init__(self, source: SSAValue) -> None:
        super().__init__(operands=[source])


def _symbol_array(values: tuple[str, ...]) -> ArrayAttr:
    """构造 SymbolExprAttr 数组。"""

    return ArrayAttr([SymbolExprAttr.from_expr(value) for value in values])


def _memory_type() -> NnMemoryType:
    """构造测试用公开 memory type。"""

    return NnMemoryType(
        _symbol_array(("M",)),
        _symbol_array(("1",)),
        i32,
        NnMemorySpaceAttr.from_name("global"),
    )


def test_template_name_constraints_register_get_and_build_static_specs() -> None:
    """验证静态 constraint spec 可注册、读取并构造为 graph constraint。"""

    register_template_constraints(
        TemplateConstraintTestOp.name,
        (
            SameSpec(TemplateValueRef("operand", 0), TemplateValueRef("operand", 1)),
            VerifyOnlySpec(TemplateValueRef("operand", 0)),
        ),
    )
    assert get_template_constraints(TemplateConstraintTestOp.name) is not None
    op = TemplateConstraintTestOp(create_ssa_value(_memory_type()), create_ssa_value(_memory_type()))
    constraints = build_template_constraints(op)
    assert any(isinstance(item, Same) for item in constraints)
    assert any(isinstance(item, VerifyOnly) for item in constraints)


def test_template_name_constraints_reject_get_unknown_op() -> None:
    """验证公开 get 入口对未知 operation 稳定失败。"""

    with pytest.raises(KernelCodeError, match="not registered"):
        get_template_constraints("test.template_constraint_missing")


def test_template_name_constraints_reject_duplicate_registration() -> None:
    """验证重复注册同名 operation 约束稳定失败。"""

    with pytest.raises(KernelCodeError, match="already registered"):
        register_template_constraints(TemplateConstraintTestOp.name, ())


def test_template_name_constraints_reject_unknown_memory_op() -> None:
    """验证携带 memory operand 的未知 operation 不得静默跳过。"""

    op = UnknownMemoryConstraintTestOp(create_ssa_value(_memory_type()))
    with pytest.raises(KernelCodeError, match="missing constraints for memory op"):
        build_template_constraints(op)


def test_template_name_default_constraints_register_dma_copy_same_family() -> None:
    """验证默认约束覆盖 dma.copy 并建立 source/target Same family。"""

    register_default_template_constraints()
    op = DmaCopyOp(create_ssa_value(_memory_type()), create_ssa_value(_memory_type()))
    constraints = build_template_constraints(op)
    assert any(isinstance(item, Same) for item in constraints)
