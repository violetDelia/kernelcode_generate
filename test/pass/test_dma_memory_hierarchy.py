"""lower-dma-memory-hierarchy pass tests.

创建者: 朽木露琪亚
最后一次更改: jcc你莫辜负

功能说明:
- 覆盖 `lower-dma-memory-hierarchy` pass 的最小正确性与边界失败口径：
  - GM->SM->LM 读路径与 LM->SM->GM 写路径必须通过 `dma.slice/dma.deslice` 显式表达；
  - 处理后的 `kernel.*` operand/out 仅使用 `LM`；
  - pass 新增改写不得引入 `dma.copy/load/store`；
  - target 缺失 SM/LM 必须显式失败；
  - LM-only 输入不应插入 staging（no-op）。

使用示例:
- pytest -q test/pass/test_dma_memory_hierarchy.py

覆盖率命令:
- pytest --cov=kernel_gen.passes.lowering.dma_memory_hierarchy --cov-report=term-missing test/pass/test_dma_memory_hierarchy.py

关联文件:
- 功能实现: kernel_gen/passes/lowering/dma_memory_hierarchy.py
- Spec 文档: spec/pass/lowering/dma_memory_hierarchy.md
- 测试文件: test/pass/test_dma_memory_hierarchy.py
"""

from __future__ import annotations

import importlib
import sys
from pathlib import Path

import pytest
from xdsl.dialects import func
from xdsl.dialects.builtin import ArrayAttr, FunctionType, IntAttr, ModuleOp, i32
from xdsl.ir import Block, Operation, Region, SSAValue

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from kernel_gen.dialect.dma import DmaDesliceOp, DmaSliceOp, DmaViewOp
from kernel_gen.dialect.kernel import KernelAddOp
from kernel_gen.dialect.nn import NnAddOp, NnMemorySpaceAttr, NnMemoryType
from kernel_gen.dialect.symbol import SymbolValueType
from kernel_gen.target import registry as target_registry

pass_module = importlib.import_module("kernel_gen.passes.lowering.dma_memory_hierarchy")
LowerDmaMemoryHierarchyError = pass_module.LowerDmaMemoryHierarchyError
LowerDmaMemoryHierarchyPass = pass_module.LowerDmaMemoryHierarchyPass


def _make_memory_type(space: str) -> NnMemoryType:
    """构造指定 space 的测试用 `nn.memory` 类型。

    创建者: 朽木露琪亚
    最后一次更改: 朽木露琪亚

    功能说明:
    - 统一生成 `[2, 3]`、`i32`、紧致 stride 的 memory 类型。

    使用示例:
    - gm = _make_memory_type("global")
    - lm = _make_memory_type("local")

    关联文件:
    - spec: spec/pass/lowering/dma_memory_hierarchy.md
    - test: test/pass/test_dma_memory_hierarchy.py
    - 功能实现: kernel_gen/passes/lowering/dma_memory_hierarchy.py
    """

    return NnMemoryType(
        ArrayAttr([IntAttr(2), IntAttr(3)]),
        ArrayAttr([IntAttr(3), IntAttr(1)]),
        i32,
        NnMemorySpaceAttr.from_name(space),
    )


def _build_kernel_add_module(space: str) -> tuple[ModuleOp, Block, KernelAddOp]:
    """构造包含单个 kernel.add 的 module。

    创建者: 朽木露琪亚
    最后一次更改: 朽木露琪亚

    功能说明:
    - func 签名包含 2 个输入与 1 个 out operand（均为 nn.memory）。
    - func 内插入 `kernel.add(lhs, rhs, out)` 与空 return。

    使用示例:
    - module, block, kernel_op = _build_kernel_add_module("global")

    关联文件:
    - spec: spec/pass/lowering/dma_memory_hierarchy.md
    - test: test/pass/test_dma_memory_hierarchy.py
    - 功能实现: kernel_gen/passes/lowering/dma_memory_hierarchy.py
    """

    mem_type = _make_memory_type(space)
    func_type = FunctionType.from_lists([mem_type, mem_type, mem_type], [])
    block = Block(arg_types=[mem_type, mem_type, mem_type])
    kernel_op = KernelAddOp(
        block.args[0],
        block.args[1],
        block.args[2],
        NnMemorySpaceAttr.from_name(space),
    )
    block.add_ops([kernel_op, func.ReturnOp()])
    func_op = func.FuncOp("main", func_type, Region(block))
    module = ModuleOp([func_op])
    return module, block, kernel_op


def _build_kernel_add_module_with_window() -> tuple[ModuleOp, Block, KernelAddOp]:
    """构造包含 window view 的 kernel.add module。

    创建者: jcc你莫辜负
    最后一次更改: jcc你莫辜负

    功能说明:
    - 通过 dma.view 构造 GM window 视图，并作为 kernel.add 的输入与输出。
    - window 形状与 stride 固定为 `[2, 3]` / `[3, 1]`，offsets 使用非零常量。
    - 该 helper 仅负责构造原始 window 元信息；hierarchy lowering 生成的 `dma.slice/dma.deslice`
      必须保留 offsets/sizes，并把新路径 strides 规范化为 unit stride。

    使用示例:
    - module, block, kernel_op = _build_kernel_add_module_with_window()

    关联文件:
    - spec: spec/pass/lowering/dma_memory_hierarchy.md
    - test: test/pass/test_dma_memory_hierarchy.py
    - 功能实现: kernel_gen/passes/lowering/dma_memory_hierarchy.py
    """

    base_type = NnMemoryType(
        ArrayAttr([IntAttr(8), IntAttr(8)]),
        ArrayAttr([IntAttr(8), IntAttr(1)]),
        i32,
        NnMemorySpaceAttr.from_name("global"),
    )
    window_type = NnMemoryType(
        ArrayAttr([IntAttr(2), IntAttr(3)]),
        ArrayAttr([IntAttr(3), IntAttr(1)]),
        i32,
        NnMemorySpaceAttr.from_name("global"),
    )
    symbol_types = [
        SymbolValueType.from_expr("1"),
        SymbolValueType.from_expr("2"),
        SymbolValueType.from_expr("3"),
        SymbolValueType.from_expr("1"),
        SymbolValueType.from_expr("2"),
        SymbolValueType.from_expr("3"),
        SymbolValueType.from_expr("3"),
        SymbolValueType.from_expr("1"),
    ]
    func_type = FunctionType.from_lists([base_type, base_type, base_type, *symbol_types], [])
    block = Block(arg_types=[base_type, base_type, base_type, *symbol_types])
    in_offsets = [block.args[3], block.args[4]]
    out_offsets = [block.args[5], block.args[6]]
    sizes = [block.args[7], block.args[8]]
    strides = [block.args[9], block.args[10]]

    view_in0 = DmaViewOp(block.args[0], in_offsets, sizes, strides, window_type)
    view_in1 = DmaViewOp(block.args[1], in_offsets, sizes, strides, window_type)
    view_out = DmaViewOp(block.args[2], out_offsets, sizes, strides, window_type)
    kernel_op = KernelAddOp(
        view_in0.result,
        view_in1.result,
        view_out.result,
        NnMemorySpaceAttr.from_name("global"),
    )
    block.add_ops([view_in0, view_in1, view_out, kernel_op, func.ReturnOp()])
    func_op = func.FuncOp("main", func_type, Region(block))
    module = ModuleOp([func_op])
    return module, block, kernel_op


def _collect_ops(block: Block) -> list[Operation]:
    """收集 block 内 op 列表。

    创建者: 朽木露琪亚
    最后一次更改: 朽木露琪亚

    功能说明:
    - 便于在测试中按类型/名称检索插入的 staging op。

    使用示例:
    - ops = _collect_ops(block)

    关联文件:
    - spec: spec/pass/lowering/dma_memory_hierarchy.md
    - test: test/pass/test_dma_memory_hierarchy.py
    - 功能实现: kernel_gen/passes/lowering/dma_memory_hierarchy.py
    """

    return list(block.ops)


def _symbol_int_values(values: list[SSAValue]) -> list[int | str]:
    """读取 symbol.int SSA value 的公开整数值列表。

    创建者: jcc你莫辜负
    最后一次更改: jcc你莫辜负

    功能说明:
    - 将 `!symbol.int<"expr">` operand 解析为可比较的整数或表达字符串。
    - 便于在测试中断言 offsets/sizes/strides 是否符合预期。

    使用示例:
    - assert _symbol_int_values(list(op.offsets)) == [0, 0]

    关联文件:
    - spec: spec/pass/lowering/dma_memory_hierarchy.md
    - test: test/pass/test_dma_memory_hierarchy.py
    - 功能实现: kernel_gen/passes/lowering/dma_memory_hierarchy.py
    """

    results: list[int | str] = []
    for value in values:
        value_type = value.type
        if not isinstance(value_type, SymbolValueType):
            raise AssertionError("expected symbol.int operand")
        results.append(value_type.get_value())
    return results


def _ensure_sm_lm_target_registered() -> str:
    """注册一个支持 SM/LM 的测试 target，并返回 target 名称。

    创建者: 朽木露琪亚
    最后一次更改: 朽木露琪亚

    功能说明:
    - 使用 `target_registry.register_target` 注册一个带 `sm_memory_size/lm_memory_size` 的 target。
    - 若该 target 已存在则跳过注册（以避免同进程重复运行导致 ValueError）。

    使用示例:
    - name = _ensure_sm_lm_target_registered()
    - target_registry._set_current_target(name)

    关联文件:
    - spec: spec/pass/lowering/dma_memory_hierarchy.md
    - test: test/pass/test_dma_memory_hierarchy.py
    - 功能实现: kernel_gen/passes/lowering/dma_memory_hierarchy.py
    """

    name = "sm_lm_demo"
    spec = target_registry.TargetSpec(
        name=name,
        arch_supported_ops=None,
        arch_unsupported_ops=set(),
        hardware={
            "thread_num": 1,
            "block_num": 1,
            "subthread_num": 1,
            "sm_memory_size": 1024,
            "lm_memory_size": 1024,
            "tsm_memory_size": 0,
            "tlm_memory_size": 0,
        },
    )
    try:
        target_registry.register_target(spec)
    except ValueError as exc:
        if "target already registered" not in str(exc):
            raise
    return name


# COV-DMH-001 / COV-DMH-002 / COV-DMH-003 / COV-DMH-004
# 创建者: 朽木露琪亚
# 最后一次更改: 朽木露琪亚
# 最近一次运行测试时间: 2026-04-06 03:20:13 +0800
# 最近一次运行成功时间: 2026-04-06 03:20:13 +0800
# 测试目的: 验证 GM->SM->LM 读路径与 LM->SM->GM 写路径通过 slice/deslice 构造，且 kernel.* 最终仅使用 LM，并且不引入 copy/load/store。
# 使用示例: pytest -q test/pass/test_dma_memory_hierarchy.py -k test_dma_memory_hierarchy_stages_gm_to_lm_and_writeback
# 对应功能实现文件路径: kernel_gen/passes/lowering/dma_memory_hierarchy.py
# 对应 spec 文件路径: spec/pass/lowering/dma_memory_hierarchy.md
# 对应测试文件路径: test/pass/test_dma_memory_hierarchy.py
def test_dma_memory_hierarchy_stages_gm_to_lm_and_writeback() -> None:
    module, block, kernel_op = _build_kernel_add_module("global")
    target_name = _ensure_sm_lm_target_registered()
    target_registry._set_current_target(target_name)
    try:
        LowerDmaMemoryHierarchyPass().run(module)
    finally:
        target_registry._set_current_target(None)

    ops = _collect_ops(block)
    slices = [op for op in ops if isinstance(op, DmaSliceOp)]
    deslices = [op for op in ops if isinstance(op, DmaDesliceOp)]
    assert len(slices) == 4
    assert len(deslices) == 2

    # kernel.* operand/out 必须为 LM 且属性 space=local。
    assert kernel_op.attributes["space"] == NnMemorySpaceAttr.from_name("local")
    for operand in kernel_op.operands:
        operand_type = operand.type
        assert isinstance(operand_type, NnMemoryType)
        assert operand_type.space.space.data == "local"

    # 检查至少存在一条 GM->SM 与一条 SM->LM 的 slice，以及 LM->SM 与 SM->GM 的 deslice。
    assert any(
        isinstance(op.source.type, NnMemoryType)
        and isinstance(op.target.type, NnMemoryType)
        and op.source.type.space.space.data == "global"
        and op.target.type.space.space.data == "shared"
        for op in slices
    )
    assert any(
        isinstance(op.source.type, NnMemoryType)
        and isinstance(op.target.type, NnMemoryType)
        and op.source.type.space.space.data == "shared"
        and op.target.type.space.space.data == "local"
        for op in slices
    )
    assert any(
        isinstance(op.source.type, NnMemoryType)
        and isinstance(op.target.type, NnMemoryType)
        and op.source.type.space.space.data == "local"
        and op.target.type.space.space.data == "shared"
        for op in deslices
    )
    assert any(
        isinstance(op.source.type, NnMemoryType)
        and isinstance(op.target.type, NnMemoryType)
        and op.source.type.space.space.data == "shared"
        and op.target.type.space.space.data == "global"
        for op in deslices
    )

    forbidden = {"dma.copy", "dma.load", "dma.store"}
    assert not any(op.name in forbidden for op in ops)


# COV-DMH-006
# 创建者: 朽木露琪亚
# 最后一次更改: 朽木露琪亚
# 最近一次运行测试时间: 2026-04-06 03:20:13 +0800
# 最近一次运行成功时间: 2026-04-06 03:20:13 +0800
# 测试目的: 验证 LM-only 输入为 no-op：不插入 staging（alloc/slice/deslice），但仍保证 kernel.* space 属性为 local。
# 使用示例: pytest -q test/pass/test_dma_memory_hierarchy.py -k test_dma_memory_hierarchy_lm_only_is_noop
# 对应功能实现文件路径: kernel_gen/passes/lowering/dma_memory_hierarchy.py
# 对应 spec 文件路径: spec/pass/lowering/dma_memory_hierarchy.md
# 对应测试文件路径: test/pass/test_dma_memory_hierarchy.py
def test_dma_memory_hierarchy_lm_only_is_noop() -> None:
    module, block, kernel_op = _build_kernel_add_module("local")
    target_name = _ensure_sm_lm_target_registered()
    target_registry._set_current_target(target_name)
    try:
        LowerDmaMemoryHierarchyPass().run(module)
    finally:
        target_registry._set_current_target(None)

    ops = _collect_ops(block)
    assert not any(isinstance(op, (DmaSliceOp, DmaDesliceOp)) for op in ops)
    assert kernel_op.attributes["space"] == NnMemorySpaceAttr.from_name("local")


# COV-DMH-008
# 创建者: jcc你莫辜负
# 最后一次更改: jcc你莫辜负
# 最近一次运行测试时间: 2026-04-06 03:20:13 +0800
# 最近一次运行成功时间: 2026-04-06 03:20:13 +0800
# 测试目的: 验证 hierarchy window 路径保留原窗口 offsets/sizes，并统一把 GM->SM、SM->LM、LM->SM、SM->GM 的新插入 strides 规范化为 unit stride。
# 使用示例: pytest -q test/pass/test_dma_memory_hierarchy.py -k test_dma_memory_hierarchy_window_offsets_and_unit_strides
# 对应功能实现文件路径: kernel_gen/passes/lowering/dma_memory_hierarchy.py
# 对应 spec 文件路径: spec/pass/lowering/dma_memory_hierarchy.md
# 对应测试文件路径: test/pass/test_dma_memory_hierarchy.py
def test_dma_memory_hierarchy_window_offsets_and_unit_strides() -> None:
    module, block, kernel_op = _build_kernel_add_module_with_window()
    target_name = _ensure_sm_lm_target_registered()
    target_registry._set_current_target(target_name)
    try:
        LowerDmaMemoryHierarchyPass().run(module)
    finally:
        target_registry._set_current_target(None)

    ops = _collect_ops(block)
    slices = [op for op in ops if isinstance(op, DmaSliceOp)]
    deslices = [op for op in ops if isinstance(op, DmaDesliceOp)]
    assert len(slices) == 4
    assert len(deslices) == 2

    gm_to_sm = [
        op
        for op in slices
        if op.source.type.space.space.data == "global"
        and op.target.type.space.space.data == "shared"
    ]
    sm_to_lm = [
        op
        for op in slices
        if op.source.type.space.space.data == "shared"
        and op.target.type.space.space.data == "local"
    ]
    assert len(gm_to_sm) == 2
    assert len(sm_to_lm) == 2

    in_offsets = [1, 2]
    out_offsets = [3, 1]
    window_sizes = [2, 3]
    unit_strides = [1, 1]

    for op in gm_to_sm:
        assert _symbol_int_values(list(op.offsets)) == in_offsets
        assert _symbol_int_values(list(op.sizes)) == window_sizes
        assert _symbol_int_values(list(op.strides)) == unit_strides

    for op in sm_to_lm:
        assert _symbol_int_values(list(op.offsets)) == [0, 0]
        assert _symbol_int_values(list(op.sizes)) == window_sizes
        assert _symbol_int_values(list(op.strides)) == unit_strides

    lm_to_sm = [
        op
        for op in deslices
        if op.source.type.space.space.data == "local"
        and op.target.type.space.space.data == "shared"
    ]
    sm_to_gm = [
        op
        for op in deslices
        if op.source.type.space.space.data == "shared"
        and op.target.type.space.space.data == "global"
    ]
    assert len(lm_to_sm) == 1
    assert len(sm_to_gm) == 1

    assert _symbol_int_values(list(lm_to_sm[0].offsets)) == [0, 0]
    assert _symbol_int_values(list(lm_to_sm[0].sizes)) == window_sizes
    assert _symbol_int_values(list(lm_to_sm[0].strides)) == unit_strides
    assert _symbol_int_values(list(sm_to_gm[0].offsets)) == out_offsets
    assert _symbol_int_values(list(sm_to_gm[0].sizes)) == window_sizes
    assert _symbol_int_values(list(sm_to_gm[0].strides)) == unit_strides

    assert kernel_op.attributes["space"] == NnMemorySpaceAttr.from_name("local")
    for operand in kernel_op.operands:
        operand_type = operand.type
        assert isinstance(operand_type, NnMemoryType)
        assert operand_type.space.space.data == "local"


# COV-DMH-005
# 创建者: 朽木露琪亚
# 最后一次更改: 朽木露琪亚
# 最近一次运行测试时间: 2026-04-06 03:20:13 +0800
# 最近一次运行成功时间: 2026-04-06 03:20:13 +0800
# 测试目的: 验证 target 缺失 SM/LM 时 pass 必须显式失败，并包含 SM/LM 关键短语。
# 使用示例: pytest -q test/pass/test_dma_memory_hierarchy.py -k test_dma_memory_hierarchy_requires_sm_lm
# 对应功能实现文件路径: kernel_gen/passes/lowering/dma_memory_hierarchy.py
# 对应 spec 文件路径: spec/pass/lowering/dma_memory_hierarchy.md
# 对应测试文件路径: test/pass/test_dma_memory_hierarchy.py
def test_dma_memory_hierarchy_requires_sm_lm() -> None:
    module, _, _ = _build_kernel_add_module("global")
    target_registry._set_current_target("cpu")
    try:
        with pytest.raises(LowerDmaMemoryHierarchyError, match="SM/LM"):
            LowerDmaMemoryHierarchyPass().run(module)
    finally:
        target_registry._set_current_target(None)


# COV-DMH-007
# 创建者: jcc你莫辜负
# 最后一次更改: jcc你莫辜负
# 最近一次运行测试时间: 2026-04-06 03:20:13 +0800
# 最近一次运行成功时间: 2026-04-06 03:20:13 +0800
# 测试目的: 验证输入含 nn.* op 时 pass 必须显式失败。
# 使用示例: pytest -q test/pass/test_dma_memory_hierarchy.py -k test_dma_memory_hierarchy_rejects_nn_ops_in_input
# 对应功能实现文件路径: kernel_gen/passes/lowering/dma_memory_hierarchy.py
# 对应 spec 文件路径: spec/pass/lowering/dma_memory_hierarchy.md
# 对应测试文件路径: test/pass/test_dma_memory_hierarchy.py
def test_dma_memory_hierarchy_rejects_nn_ops_in_input() -> None:
    mem_type = _make_memory_type("global")
    func_type = FunctionType.from_lists([mem_type, mem_type], [])
    block = Block(arg_types=[mem_type, mem_type])
    nn_add = NnAddOp(block.args[0], block.args[1], mem_type, NnMemorySpaceAttr.from_name("global"))
    block.add_ops([nn_add, func.ReturnOp()])
    func_op = func.FuncOp("main", func_type, Region(block))
    module = ModuleOp([func_op])
    target_name = _ensure_sm_lm_target_registered()
    target_registry._set_current_target(target_name)
    try:
        with pytest.raises(LowerDmaMemoryHierarchyError, match="nn"):
            LowerDmaMemoryHierarchyPass().run(module)
    finally:
        target_registry._set_current_target(None)
