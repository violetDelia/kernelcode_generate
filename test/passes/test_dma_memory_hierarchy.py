"""lower-dma-memory-hierarchy pass tests.


功能说明:
- 覆盖 `lower-dma-memory-hierarchy` 的公开构造、registry option 与 IR 改写行为。
- 默认不配置 `apply_op` 时 pass no-op。
- `fold=False` 且不配置 `apply_op` 时保留 legacy hierarchy 兼容路径。
- `apply_op="matmul{[...]}"` 时只通过公开 pass API 验证 `kernel.matmul` copy-based staging。

使用示例:
- pytest -q test/passes/test_dma_memory_hierarchy.py

覆盖率命令:
- pytest --cov=kernel_gen.passes.dma_memory_hierarchy --cov-report=term-missing test/passes/test_dma_memory_hierarchy.py

关联文件:
- 功能实现: kernel_gen/passes/dma_memory_hierarchy.py
- Spec 文档: spec/pass/lowering/dma_memory_hierarchy/spec.md
- 测试文件: test/passes/test_dma_memory_hierarchy.py
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest
from xdsl.context import Context
from xdsl.dialects import func
from xdsl.dialects.builtin import ArrayAttr, FunctionType, IntAttr, ModuleOp, StringAttr, i32
from xdsl.ir import Block, Operation, Region

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from kernel_gen.core.error import KernelCodeError
from kernel_gen.dialect.dma import DmaAllocOp, DmaCopyOp, DmaDesliceOp, DmaSliceOp
from kernel_gen.dialect.kernel import KernelBinaryElewiseOp, KernelMatmulOp
from kernel_gen.dialect.nn import NnMemorySpaceAttr, NnMemoryType
from kernel_gen.dialect.symbol import SymbolExprAttr
import kernel_gen.passes.registry as passregistry
from kernel_gen.passes.dma_memory_hierarchy import LowerDmaMemoryHierarchyPass
import kernel_gen.target.registry as targetregistry


class _TargetHardwareLookup:
    """测试用 target hardware 查询器。"""

    def __init__(self, sm_memory_size: int | None, lm_memory_size: int | None) -> None:
        self.hardware = {
            "sm_memory_size": sm_memory_size,
            "lm_memory_size": lm_memory_size,
        }

    def __call__(self, key: str) -> int | None:
        return self.hardware.get(key)


def _make_space(name: str) -> NnMemorySpaceAttr:
    """构造测试用 memory space。"""

    return NnMemorySpaceAttr.from_name(name)


def _symbol_expr_attr(value: int | str) -> SymbolExprAttr:
    """构造测试用 SymbolExprAttr 维度。"""

    return SymbolExprAttr.from_expr(str(value))


def _make_memory_type(
    *,
    shape: tuple[int, ...] = (2, 4),
    stride: tuple[int, ...] = (4, 1),
    space: str = "global",
) -> NnMemoryType:
    """构造静态 `nn.memory` 类型。"""

    return NnMemoryType(
        ArrayAttr([_symbol_expr_attr(dim) for dim in shape]),
        ArrayAttr([_symbol_expr_attr(dim) for dim in stride]),
        i32,
        _make_space(space),
    )


def _make_symbolic_memory_type(space: str = "global") -> NnMemoryType:
    """构造含显式符号维度的 `nn.memory` 类型。"""

    return NnMemoryType(
        ArrayAttr([_symbol_expr_attr("M"), _symbol_expr_attr(4)]),
        ArrayAttr([_symbol_expr_attr(4), _symbol_expr_attr(1)]),
        i32,
        _make_space(space),
    )


def _make_anonymous_dynamic_memory_type(space: str = "global") -> NnMemoryType:
    """构造含匿名动态维度的 `nn.memory` 类型。"""

    return NnMemoryType(
        ArrayAttr([_symbol_expr_attr("?"), _symbol_expr_attr(4)]),
        ArrayAttr([_symbol_expr_attr(4), _symbol_expr_attr(1)]),
        i32,
        _make_space(space),
    )


def _build_matmul_module(
    *,
    out_type: NnMemoryType | None = None,
    lhs_type: NnMemoryType | None = None,
    rhs_type: NnMemoryType | None = None,
    space: str = "global",
) -> tuple[ModuleOp, Block, KernelMatmulOp]:
    """构造单个 `kernel.matmul` module。"""

    if out_type is None:
        out_type = _make_memory_type(shape=(2, 4), stride=(4, 1), space=space)
    if lhs_type is None:
        lhs_type = _make_memory_type(shape=(2, 3), stride=(3, 1), space=space)
    if rhs_type is None:
        rhs_type = _make_memory_type(shape=(3, 4), stride=(4, 1), space=space)
    func_type = FunctionType.from_lists([out_type, lhs_type, rhs_type], [])
    block = Block(arg_types=[out_type, lhs_type, rhs_type])
    matmul = KernelMatmulOp(block.args[0], block.args[1], block.args[2], _make_space(space))
    block.add_ops([matmul, func.ReturnOp()])
    func_op = func.FuncOp("matmul", func_type, Region(block))
    return ModuleOp([func_op]), block, matmul


def _build_binary_elewise_module(space: str) -> tuple[ModuleOp, Block, KernelBinaryElewiseOp]:
    """构造单个 `kernel.binary_elewise(kind="add")` module。"""

    mem_type = _make_memory_type(space=space)
    func_type = FunctionType.from_lists([mem_type, mem_type, mem_type], [])
    block = Block(arg_types=[mem_type, mem_type, mem_type])
    add = KernelBinaryElewiseOp(
        block.args[0],
        block.args[1],
        block.args[2],
        kind="add",
        space=_make_space(space),
    )
    block.add_ops([add, func.ReturnOp()])
    func_op = func.FuncOp("add", func_type, Region(block))
    return ModuleOp([func_op]), block, add


def _collect_ops(block: Block) -> list[Operation]:
    """收集 block 内 op。"""

    return list(block.ops)


def _memory_space(value_type: NnMemoryType) -> str:
    """读取 `nn.memory` space 名称。"""

    return value_type.space.space.data


def _patch_target_hardware(
    monkeypatch: pytest.MonkeyPatch,
    *,
    sm_memory_size: int | None,
    lm_memory_size: int | None,
) -> None:
    """通过公开 target 查询入口提供测试 target 容量。"""

    monkeypatch.setattr(
        targetregistry,
        "get_current_target_hardware",
        _TargetHardwareLookup(sm_memory_size, lm_memory_size),
    )


# TC-DMH-001
# 测试目的: 验证默认不配置 apply_op 时 pass 不触碰 IR，也不要求 target SM/LM。
# 使用示例: pytest -q test/passes/test_dma_memory_hierarchy.py -k test_dma_memory_hierarchy_default_no_apply_op_is_noop
# 对应功能实现文件路径: kernel_gen/passes/dma_memory_hierarchy.py
# 对应 spec 文件路径: spec/pass/lowering/dma_memory_hierarchy/spec.md
# 对应测试文件路径: test/passes/test_dma_memory_hierarchy.py
def test_dma_memory_hierarchy_default_no_apply_op_is_noop() -> None:
    module, block, matmul = _build_matmul_module(space="global")
    original_operands = list(matmul.operands)

    LowerDmaMemoryHierarchyPass().apply(Context(), module)

    ops = _collect_ops(block)
    assert list(matmul.operands) == original_operands
    assert not any(isinstance(op, (DmaAllocOp, DmaCopyOp, DmaSliceOp, DmaDesliceOp)) for op in ops)
    module.verify()


# TC-DMH-002
# 测试目的: 验证 fold=False 且不配置 apply_op 时仍保留 legacy hierarchy 兼容路径。
# 使用示例: pytest -q test/passes/test_dma_memory_hierarchy.py -k test_dma_memory_hierarchy_fold_false_legacy_hierarchy
# 对应功能实现文件路径: kernel_gen/passes/dma_memory_hierarchy.py
# 对应 spec 文件路径: spec/pass/lowering/dma_memory_hierarchy/spec.md
# 对应测试文件路径: test/passes/test_dma_memory_hierarchy.py
def test_dma_memory_hierarchy_fold_false_legacy_hierarchy(monkeypatch: pytest.MonkeyPatch) -> None:
    module, block, add = _build_binary_elewise_module("global")
    _patch_target_hardware(monkeypatch, sm_memory_size=4096, lm_memory_size=2048)

    LowerDmaMemoryHierarchyPass(fold=False).apply(Context(), module)

    ops = _collect_ops(block)
    assert len([op for op in ops if isinstance(op, DmaSliceOp)]) == 4
    assert len([op for op in ops if isinstance(op, DmaDesliceOp)]) == 2
    assert not any(isinstance(op, DmaCopyOp) for op in ops)
    assert add.attributes["space"] == _make_space("local")
    for operand in add.operands:
        operand_type = operand.type
        assert isinstance(operand_type, NnMemoryType)
        assert _memory_space(operand_type) == "local"
    module.verify()


# TC-DMH-003
# 测试目的: 验证 apply_op 对 matmul lhs/rhs 生成 `dma.alloc + dma.copy` 并替换 operand。
# 使用示例: pytest -q test/passes/test_dma_memory_hierarchy.py -k test_dma_memory_hierarchy_apply_op_matmul_copies_lhs_rhs
# 对应功能实现文件路径: kernel_gen/passes/dma_memory_hierarchy.py
# 对应 spec 文件路径: spec/pass/lowering/dma_memory_hierarchy/spec.md
# 对应测试文件路径: test/passes/test_dma_memory_hierarchy.py
def test_dma_memory_hierarchy_apply_op_matmul_copies_lhs_rhs() -> None:
    module, block, matmul = _build_matmul_module(space="tsm")
    original_lhs = matmul.operands[1]
    original_rhs = matmul.operands[2]

    pass_obj = LowerDmaMemoryHierarchyPass(apply_op='matmul{["", "tlm1", "tlm2"]}')
    pass_obj.apply(Context(), module)

    ops = _collect_ops(block)
    allocs = [op for op in ops if isinstance(op, DmaAllocOp)]
    copies = [op for op in ops if isinstance(op, DmaCopyOp)]
    assert len(allocs) == 2
    assert len(copies) == 2
    assert _memory_space(matmul.operands[1].type) == "tlm1"
    assert _memory_space(matmul.operands[2].type) == "tlm2"
    assert copies[0].source is original_lhs
    assert copies[0].target is allocs[0].result
    assert copies[1].source is original_rhs
    assert copies[1].target is allocs[1].result
    assert not any(isinstance(op, (DmaSliceOp, DmaDesliceOp)) for op in ops)
    module.verify()


# TC-DMH-004
# 测试目的: 验证 apply_op 对 out operand 与 input operand 使用相同 copy 替换规则。
# 使用示例: pytest -q test/passes/test_dma_memory_hierarchy.py -k test_dma_memory_hierarchy_apply_op_can_copy_out
# 对应功能实现文件路径: kernel_gen/passes/dma_memory_hierarchy.py
# 对应 spec 文件路径: spec/pass/lowering/dma_memory_hierarchy/spec.md
# 对应测试文件路径: test/passes/test_dma_memory_hierarchy.py
def test_dma_memory_hierarchy_apply_op_can_copy_out() -> None:
    module, block, matmul = _build_matmul_module(space="global")
    original_out = matmul.operands[0]

    LowerDmaMemoryHierarchyPass(apply_op='matmul{["tlm1", "", ""]}').apply(Context(), module)

    allocs = [op for op in _collect_ops(block) if isinstance(op, DmaAllocOp)]
    copies = [op for op in _collect_ops(block) if isinstance(op, DmaCopyOp)]
    assert len(allocs) == 1
    assert len(copies) == 1
    assert copies[0].source is original_out
    assert copies[0].target is allocs[0].result
    assert matmul.operands[0] is allocs[0].result
    assert _memory_space(matmul.operands[0].type) == "tlm1"
    module.verify()


# TC-DMH-005
# 测试目的: 验证显式空 target 规则不插入搬运。
# 使用示例: pytest -q test/passes/test_dma_memory_hierarchy.py -k test_dma_memory_hierarchy_apply_op_empty_rule_noop
# 对应功能实现文件路径: kernel_gen/passes/dma_memory_hierarchy.py
# 对应 spec 文件路径: spec/pass/lowering/dma_memory_hierarchy/spec.md
# 对应测试文件路径: test/passes/test_dma_memory_hierarchy.py
def test_dma_memory_hierarchy_apply_op_empty_rule_noop() -> None:
    module, block, matmul = _build_matmul_module(space="local")
    original_operands = list(matmul.operands)

    LowerDmaMemoryHierarchyPass(apply_op='matmul{["", "", ""]}').apply(Context(), module)

    assert list(matmul.operands) == original_operands
    assert not any(isinstance(op, (DmaAllocOp, DmaCopyOp, DmaSliceOp, DmaDesliceOp)) for op in _collect_ops(block))
    module.verify()


# TC-DMH-006
# 测试目的: 验证 registry option 能公开构造 apply_op pass 并执行 copy rewrite。
# 使用示例: pytest -q test/passes/test_dma_memory_hierarchy.py -k test_dma_memory_hierarchy_registry_apply_op
# 对应功能实现文件路径: kernel_gen/passes/dma_memory_hierarchy.py
# 对应 spec 文件路径: spec/pass/lowering/dma_memory_hierarchy/spec.md
# 对应测试文件路径: test/passes/test_dma_memory_hierarchy.py
def test_dma_memory_hierarchy_registry_apply_op() -> None:
    module, block, matmul = _build_matmul_module(space="shared")
    passregistry.load_builtin_passes()

    pass_obj = passregistry.build_registered_pass(
        "lower-dma-memory-hierarchy",
        {"fold": "false", "apply_op": 'matmul{["", "tlm1", "tlm2"]}'},
    )
    pass_obj.apply(Context(), module)

    assert isinstance(pass_obj, LowerDmaMemoryHierarchyPass)
    assert len([op for op in _collect_ops(block) if isinstance(op, DmaCopyOp)]) == 2
    assert _memory_space(matmul.operands[1].type) == "tlm1"
    assert _memory_space(matmul.operands[2].type) == "tlm2"
    module.verify()


# TC-DMH-007
# 测试目的: 验证 apply_op 对显式符号维度生成 `symbol.get_dim` 并作为 `dma.alloc` dynamic_shape。
# 使用示例: pytest -q test/passes/test_dma_memory_hierarchy.py -k test_dma_memory_hierarchy_apply_op_symbol_shape
# 对应功能实现文件路径: kernel_gen/passes/dma_memory_hierarchy.py
# 对应 spec 文件路径: spec/pass/lowering/dma_memory_hierarchy/spec.md
# 对应测试文件路径: test/passes/test_dma_memory_hierarchy.py
def test_dma_memory_hierarchy_apply_op_symbol_shape() -> None:
    lhs_type = _make_symbolic_memory_type("global")
    rhs_type = _make_memory_type(shape=(4, 4), stride=(4, 1), space="global")
    out_type = _make_symbolic_memory_type("global")
    module, block, _ = _build_matmul_module(
        out_type=out_type,
        lhs_type=lhs_type,
        rhs_type=rhs_type,
        space="global",
    )

    LowerDmaMemoryHierarchyPass(apply_op='matmul{["", "tlm1", ""]}').apply(Context(), module)

    allocs = [op for op in _collect_ops(block) if isinstance(op, DmaAllocOp)]
    assert len(allocs) == 1
    assert len(list(allocs[0].dynamic_shape)) == 1
    assert allocs[0].dynamic_shape[0].type.get_value() == "M"
    module.verify()


# TC-DMH-008
# 测试目的: 验证匿名动态维度作为 apply_op staging 目标 shape 时使用 full-rank dynamic_shape。
# 使用示例: pytest -q test/passes/test_dma_memory_hierarchy.py -k test_dma_memory_hierarchy_apply_op_accepts_anonymous_dynamic_shape
# 对应功能实现文件路径: kernel_gen/passes/dma_memory_hierarchy.py
# 对应 spec 文件路径: spec/pass/lowering/dma_memory_hierarchy/spec.md
# 对应测试文件路径: test/passes/test_dma_memory_hierarchy.py
def test_dma_memory_hierarchy_apply_op_accepts_anonymous_dynamic_shape() -> None:
    lhs_type = _make_anonymous_dynamic_memory_type("global")
    rhs_type = _make_memory_type(shape=(4, 4), stride=(4, 1), space="global")
    out_type = _make_anonymous_dynamic_memory_type("global")
    module, block, _ = _build_matmul_module(
        out_type=out_type,
        lhs_type=lhs_type,
        rhs_type=rhs_type,
        space="global",
    )

    LowerDmaMemoryHierarchyPass(apply_op='matmul{["", "tlm1", ""]}').apply(Context(), module)

    allocs = [op for op in _collect_ops(block) if isinstance(op, DmaAllocOp)]
    assert len(allocs) == 1
    assert [operand.type.get_value() for operand in allocs[0].dynamic_shape] == ["?", 4]
    module.verify()


# TC-DMH-009
# 测试目的: 验证非法 apply_op 规则在公开构造入口稳定失败。
# 使用示例: pytest -q test/passes/test_dma_memory_hierarchy.py -k test_dma_memory_hierarchy_rejects_invalid_apply_op_rules
# 对应功能实现文件路径: kernel_gen/passes/dma_memory_hierarchy.py
# 对应 spec 文件路径: spec/pass/lowering/dma_memory_hierarchy/spec.md
# 对应测试文件路径: test/passes/test_dma_memory_hierarchy.py
@pytest.mark.parametrize(
    "apply_op",
    [
        'add{["", "tlm1", "tlm2"]}',
        'matmul{["tlm1", "tlm2"]}',
        'matmul{["global", "", ""]}',
        'matmul{[1, "", ""]}',
        'matmul{"tlm1"}',
        'matmul{["", "tlm1", "tlm2"]} extra',
    ],
)
def test_dma_memory_hierarchy_rejects_invalid_apply_op_rules(apply_op: str) -> None:
    with pytest.raises(KernelCodeError):
        LowerDmaMemoryHierarchyPass(apply_op=apply_op)
