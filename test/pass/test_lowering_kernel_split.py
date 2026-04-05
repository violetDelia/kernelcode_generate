"""kernel split pass tests.

创建者: 小李飞刀
最后一次更改: 小李飞刀

功能说明:
- 覆盖 `KernelSplitPass` 的公开合同、显式 split body 行为与错误短语边界。

使用示例:
- pytest -q test/pass/test_lowering_kernel_split.py

当前覆盖率信息:
- `kernel_gen.passes.lowering.kernel_split`：`94%`（2026-04-06 01:40:00 +0800，`14 passed`）。

覆盖率命令:
- `pytest --cov=kernel_gen.passes.lowering.kernel_split --cov-report=term-missing -q test/pass/test_lowering_kernel_split.py`

关联文件:
- 功能实现: kernel_gen/passes/lowering/kernel_split.py
- Spec 文档: spec/pass/lowering/kernel_split.md
- 测试文件: test/pass/test_lowering_kernel_split.py
"""

from __future__ import annotations

import importlib
import sys
from pathlib import Path

import pytest
from xdsl.dialects import func
from xdsl.dialects.builtin import ArrayAttr, DictionaryAttr, FunctionType, IntAttr, ModuleOp, StringAttr, i32
from xdsl.irdl import IRDLOperation, irdl_op_definition
from xdsl.ir import Block, Operation, Region, SSAValue

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from kernel_gen.dialect.dma import DmaAllocOp
from kernel_gen.dialect.kernel import KernelAddOp
from kernel_gen.dialect.nn import NnAddOp, NnMemorySpaceAttr, NnMemoryType
from kernel_gen.dialect.symbol import SymbolForOp, SymbolGetDimOp, SymbolValueType
from kernel_gen.dialect.tuner import TunerParamOp

pass_module = importlib.import_module("kernel_gen.passes.lowering.kernel_split")
KernelSplitError = pass_module.KernelSplitError
KernelSplitPass = pass_module.KernelSplitPass
_KernelSplitTileValueOp = pass_module._KernelSplitTileValueOp


@irdl_op_definition
class _UnsupportedOp(IRDLOperation):
    """测试用非法输入 op。

    创建者: 小李飞刀
    最后一次更改: 小李飞刀

    功能说明:
    - 用于构造不属于 `kernel/dma/func` 允许子集的输入，验证 fail-fast。

    使用示例:
    - _UnsupportedOp()

    关联文件:
    - spec: spec/pass/lowering/kernel_split.md
    - test: test/pass/test_lowering_kernel_split.py
    - 功能实现: kernel_gen/passes/lowering/kernel_split.py
    """

    name = "test.unsupported"

    def __init__(self: "_UnsupportedOp") -> None:
        """构造测试用非法输入 op。

        创建者: 小李飞刀
        最后一次更改: 小李飞刀

        功能说明:
        - 生成一个最小无副作用 op，专门命中 `KernelSplitRequiresLoweredKernelIR`。

        使用示例:
        - op = _UnsupportedOp()

        关联文件:
        - spec: spec/pass/lowering/kernel_split.md
        - test: test/pass/test_lowering_kernel_split.py
        - 功能实现: kernel_gen/passes/lowering/kernel_split.py
        """

        super().__init__()


def _make_memory_type(shape: tuple[int, ...] = (8, 4)) -> NnMemoryType:
    """构造测试用 `nn.memory` 类型。

    创建者: 小李飞刀
    最后一次更改: 小李飞刀

    功能说明:
    - 按紧致布局自动推导 stride。
    - 统一生成 `i32` / `global` memory，避免测试重复拼装类型。

    使用示例:
    - mem_type = _make_memory_type((8, 4))

    关联文件:
    - spec: spec/pass/lowering/kernel_split.md
    - test: test/pass/test_lowering_kernel_split.py
    - 功能实现: kernel_gen/passes/lowering/kernel_split.py
    """

    strides: list[int] = []
    acc = 1
    for dim in reversed(shape):
        strides.append(acc)
        acc *= dim
    strides.reverse()
    return NnMemoryType(
        ArrayAttr([IntAttr(dim) for dim in shape]),
        ArrayAttr([IntAttr(dim) for dim in strides]),
        i32,
        NnMemorySpaceAttr.from_name("global"),
    )


def _make_kernel_split_attr(axis: int, tile: str) -> DictionaryAttr:
    """构造测试用 `kernel_split` 属性。

    创建者: 小李飞刀
    最后一次更改: 小李飞刀

    功能说明:
    - 固定公开写法 `kernel_split = { axis = <i64>, tile = "<TILE_NAME>" }`。

    使用示例:
    - func_op.attributes["kernel_split"] = _make_kernel_split_attr(1, "TILE_M")

    关联文件:
    - spec: spec/pass/lowering/kernel_split.md
    - test: test/pass/test_lowering_kernel_split.py
    - 功能实现: kernel_gen/passes/lowering/kernel_split.py
    """

    return DictionaryAttr({"axis": IntAttr(axis), "tile": StringAttr(tile)})


def _alloc_ops(source_memory: SSAValue) -> tuple[list[Operation], DmaAllocOp]:
    """构造带 shape operand 的 `dma.alloc`。

    创建者: 小李飞刀
    最后一次更改: 小李飞刀

    功能说明:
    - 通过 `symbol.get_dim` 从现有 `nn.memory` 参数生成 dynamic_shape operand。
    - 同时返回 shape query op 与 `dma.alloc`，便于测试顺序插入。

    使用示例:
    - ops, alloc = _alloc_ops(block.args[2])

    关联文件:
    - spec: spec/pass/lowering/kernel_split.md
    - test: test/pass/test_lowering_kernel_split.py
    - 功能实现: kernel_gen/passes/lowering/kernel_split.py
    """

    mem_type = source_memory.type
    if not isinstance(mem_type, NnMemoryType):
        raise TypeError("source_memory must be nn.memory")
    shape_ops = [SymbolGetDimOp(source_memory, axis) for axis, _ in enumerate(mem_type.shape.data)]
    alloc = DmaAllocOp([op.result for op in shape_ops], mem_type)
    return [*shape_ops, alloc], alloc


def _make_marked_kernel_module(
    *,
    include_temp_alloc: bool,
    reuse_temp_as_input: bool,
    func_outputs: list[object] | None = None,
    axis: int = 1,
    tile: str = "TILE_M",
    existing_tuner_param: bool = False,
) -> tuple[ModuleOp, func.FuncOp]:
    """构造带 `kernel_split` 标记的 kernel IR 模块。

    创建者: 小李飞刀
    最后一次更改: 小李飞刀

    功能说明:
    - 统一生成 `kernel.add` 两阶段链路、可选 temp alloc 与可选已有 `tuner.param`。
    - 供成功路径与错误路径测试复用同一最小骨架。

    使用示例:
    - module, func_op = _make_marked_kernel_module(include_temp_alloc=True, reuse_temp_as_input=True)

    关联文件:
    - spec: spec/pass/lowering/kernel_split.md
    - test: test/pass/test_lowering_kernel_split.py
    - 功能实现: kernel_gen/passes/lowering/kernel_split.py
    """

    mem_type = _make_memory_type()
    outputs = [] if func_outputs is None else func_outputs
    block = Block(arg_types=[mem_type, mem_type, mem_type])
    ops: list[Operation] = []
    space = NnMemorySpaceAttr.from_name("global")

    if existing_tuner_param:
        ops.append(TunerParamOp(pass_module.SymbolDimType.from_name(tile)))

    temp_alloc: DmaAllocOp | None = None
    temp_value = block.args[2]
    if include_temp_alloc:
        alloc_setup, temp_alloc = _alloc_ops(block.args[2])
        ops.extend(alloc_setup)
        temp_value = temp_alloc.result

    first_out = temp_value if reuse_temp_as_input else block.args[2]
    ops.append(KernelAddOp(block.args[0], block.args[1], first_out, space))
    ops.append(KernelAddOp(first_out, block.args[1], block.args[2], space))
    ops.append(func.ReturnOp())
    block.add_ops(ops)

    func_op = func.FuncOp(
        "kernel_split_target",
        FunctionType.from_lists([mem_type, mem_type, mem_type], outputs),
        Region(block),
    )
    func_op.attributes["kernel_split"] = _make_kernel_split_attr(axis, tile)
    return ModuleOp([func_op]), func_op


# TC-KS-001
# 创建者: 小李飞刀
# 最后一次更改: 小李飞刀
# 最近一次运行测试时间: 2026-04-06 00:00:00 +0800
# 最近一次运行成功时间: 2026-04-06 00:00:00 +0800
# 测试目的: 验证 split tile 因子通过 `tuner.param` bridge 驱动，而不是隐藏常量。
# 对应功能实现文件路径: kernel_gen/passes/lowering/kernel_split.py
# 对应 spec 文件路径: spec/pass/lowering/kernel_split.md
# 对应测试文件路径: test/pass/test_lowering_kernel_split.py
def test_kernel_split_pass_uses_tuner_param_tiles() -> None:
    module, func_op = _make_marked_kernel_module(
        include_temp_alloc=True,
        reuse_temp_as_input=True,
        existing_tuner_param=True,
    )

    KernelSplitPass().run(module)

    body_ops = list(func_op.body.blocks.first.ops)
    tuner_ops = [op for op in body_ops if isinstance(op, TunerParamOp)]
    assert len(tuner_ops) == 1
    loop_op = next(op for op in body_ops if isinstance(op, SymbolForOp))
    assert isinstance(loop_op.step.owner, _KernelSplitTileValueOp)
    assert loop_op.step.owner.source == tuner_ops[0].result


# TC-KS-002
# 创建者: 小李飞刀
# 最后一次更改: 小李飞刀
# 最近一次运行测试时间: 2026-04-06 00:00:00 +0800
# 最近一次运行成功时间: 2026-04-06 00:00:00 +0800
# 测试目的: 验证 pass 保持单个 `func.func`，并在函数体内生成显式 split body。
# 对应功能实现文件路径: kernel_gen/passes/lowering/kernel_split.py
# 对应 spec 文件路径: spec/pass/lowering/kernel_split.md
# 对应测试文件路径: test/pass/test_lowering_kernel_split.py
def test_kernel_split_pass_keeps_single_func_and_emits_split_body() -> None:
    module, func_op = _make_marked_kernel_module(
        include_temp_alloc=True,
        reuse_temp_as_input=True,
    )

    KernelSplitPass().run(module)

    funcs = [op for op in module.ops if isinstance(op, func.FuncOp)]
    assert len(funcs) == 1
    body_ops = list(func_op.body.blocks.first.ops)
    assert any(isinstance(op, TunerParamOp) for op in body_ops)
    assert any(isinstance(op, SymbolGetDimOp) for op in body_ops)
    loop_op = next(op for op in body_ops if isinstance(op, SymbolForOp))
    loop_body_ops = list(loop_op.body.blocks.first.ops)
    assert sum(1 for op in loop_body_ops if isinstance(op, KernelAddOp)) == 2
    assert not any(isinstance(op, func.CallOp) for op in loop_body_ops)


# TC-KS-003
# 创建者: 小李飞刀
# 最后一次更改: 小李飞刀
# 最近一次运行测试时间: 2026-04-06 00:00:00 +0800
# 最近一次运行成功时间: 2026-04-06 00:00:00 +0800
# 测试目的: 验证非法 tile 名称会稳定报 `KernelSplitMissingTileParam`。
# 对应功能实现文件路径: kernel_gen/passes/lowering/kernel_split.py
# 对应 spec 文件路径: spec/pass/lowering/kernel_split.md
# 对应测试文件路径: test/pass/test_lowering_kernel_split.py
def test_kernel_split_pass_rejects_missing_tuner_param() -> None:
    module, _ = _make_marked_kernel_module(
        include_temp_alloc=True,
        reuse_temp_as_input=True,
        tile="TILE-M",
    )

    with pytest.raises(KernelSplitError, match="KernelSplitMissingTileParam"):
        KernelSplitPass().run(module)


# TC-KS-004
# 创建者: 小李飞刀
# 最后一次更改: 小李飞刀
# 最近一次运行测试时间: 2026-04-06 00:00:00 +0800
# 最近一次运行成功时间: 2026-04-06 00:00:00 +0800
# 测试目的: 验证输入中已有 `func.call` 时显式拒绝 helper/函数抽取式切分。
# 对应功能实现文件路径: kernel_gen/passes/lowering/kernel_split.py
# 对应 spec 文件路径: spec/pass/lowering/kernel_split.md
# 对应测试文件路径: test/pass/test_lowering_kernel_split.py
def test_kernel_split_pass_rejects_new_func_generation() -> None:
    mem_type = _make_memory_type()
    callee = func.FuncOp("callee", FunctionType.from_lists([mem_type], []), Region(Block(arg_types=[mem_type])))
    callee.body.blocks.first.add_op(func.ReturnOp())

    block = Block(arg_types=[mem_type, mem_type, mem_type])
    call = func.CallOp("callee", [block.args[0]], [])
    block.add_ops([call, func.ReturnOp()])
    caller = func.FuncOp(
        "caller",
        FunctionType.from_lists([mem_type, mem_type, mem_type], []),
        Region(block),
    )
    caller.attributes["kernel_split"] = _make_kernel_split_attr(1, "TILE_M")
    module = ModuleOp([callee, caller])

    with pytest.raises(KernelSplitError, match="KernelSplitUnexpectedFuncExtraction"):
        KernelSplitPass().run(module)


# TC-KS-005
# 创建者: 小李飞刀
# 最后一次更改: 小李飞刀
# 最近一次运行测试时间: 2026-04-06 00:00:00 +0800
# 最近一次运行成功时间: 2026-04-06 00:00:00 +0800
# 测试目的: 验证跨 stage 复用非 `dma.alloc` 输出时会报 `KernelSplitIntermediateMaterializationError`。
# 对应功能实现文件路径: kernel_gen/passes/lowering/kernel_split.py
# 对应 spec 文件路径: spec/pass/lowering/kernel_split.md
# 对应测试文件路径: test/pass/test_lowering_kernel_split.py
def test_kernel_split_pass_rejects_unmaterialized_intermediate() -> None:
    module, _ = _make_marked_kernel_module(
        include_temp_alloc=False,
        reuse_temp_as_input=False,
    )

    with pytest.raises(KernelSplitError, match="KernelSplitIntermediateMaterializationError"):
        KernelSplitPass().run(module)


# TC-KS-006
# 创建者: 小李飞刀
# 最后一次更改: 小李飞刀
# 最近一次运行测试时间: 2026-04-06 00:00:00 +0800
# 最近一次运行成功时间: 2026-04-06 00:00:00 +0800
# 测试目的: 验证残留 `nn.*` 时稳定报 `KernelSplitRequiresLoweredKernelIR`。
# 对应功能实现文件路径: kernel_gen/passes/lowering/kernel_split.py
# 对应 spec 文件路径: spec/pass/lowering/kernel_split.md
# 对应测试文件路径: test/pass/test_lowering_kernel_split.py
def test_kernel_split_pass_rejects_non_lowered_nn_ops() -> None:
    mem_type = _make_memory_type()
    block = Block(arg_types=[mem_type, mem_type, mem_type])
    nn_add = NnAddOp(block.args[0], block.args[1], mem_type, NnMemorySpaceAttr.from_name("global"))
    block.add_ops([nn_add, func.ReturnOp()])
    func_op = func.FuncOp(
        "non_lowered",
        FunctionType.from_lists([mem_type, mem_type, mem_type], []),
        Region(block),
    )
    func_op.attributes["kernel_split"] = _make_kernel_split_attr(1, "TILE_M")
    module = ModuleOp([func_op])

    with pytest.raises(KernelSplitError, match="KernelSplitRequiresLoweredKernelIR"):
        KernelSplitPass().run(module)


# TC-KS-007
# 创建者: 小李飞刀
# 最后一次更改: 小李飞刀
# 最近一次运行测试时间: 2026-04-06 00:00:00 +0800
# 最近一次运行成功时间: 2026-04-06 00:00:00 +0800
# 测试目的: 验证写入后从未被消费的 carry memory 会报 `KernelSplitDeadCarryMemory`。
# 对应功能实现文件路径: kernel_gen/passes/lowering/kernel_split.py
# 对应 spec 文件路径: spec/pass/lowering/kernel_split.md
# 对应测试文件路径: test/pass/test_lowering_kernel_split.py
def test_kernel_split_pass_rejects_dead_carry_memory() -> None:
    mem_type = _make_memory_type()
    block = Block(arg_types=[mem_type, mem_type, mem_type])
    alloc_setup, temp_alloc = _alloc_ops(block.args[2])
    block.add_ops(
        [
            *alloc_setup,
            KernelAddOp(block.args[0], block.args[1], temp_alloc.result, NnMemorySpaceAttr.from_name("global")),
            func.ReturnOp(),
        ]
    )
    func_op = func.FuncOp(
        "dead_carry",
        FunctionType.from_lists([mem_type, mem_type, mem_type], []),
        Region(block),
    )
    func_op.attributes["kernel_split"] = _make_kernel_split_attr(1, "TILE_M")
    module = ModuleOp([func_op])

    with pytest.raises(KernelSplitError, match="KernelSplitDeadCarryMemory"):
        KernelSplitPass().run(module)


# TC-KS-008
# 创建者: 小李飞刀
# 最后一次更改: 小李飞刀
# 最近一次运行测试时间: 2026-04-06 00:00:00 +0800
# 最近一次运行成功时间: 2026-04-06 00:00:00 +0800
# 测试目的: 验证 module 内无 split marker 时稳定报 `KernelSplitMissingTrigger`。
# 对应功能实现文件路径: kernel_gen/passes/lowering/kernel_split.py
# 对应 spec 文件路径: spec/pass/lowering/kernel_split.md
# 对应测试文件路径: test/pass/test_lowering_kernel_split.py
def test_kernel_split_pass_rejects_missing_trigger() -> None:
    mem_type = _make_memory_type()
    block = Block(arg_types=[mem_type])
    block.add_op(func.ReturnOp())
    func_op = func.FuncOp("plain", FunctionType.from_lists([mem_type], []), Region(block))
    module = ModuleOp([func_op])

    with pytest.raises(KernelSplitError, match="KernelSplitMissingTrigger"):
        KernelSplitPass().run(module)


# TC-KS-009
# 创建者: 小李飞刀
# 最后一次更改: 小李飞刀
# 最近一次运行测试时间: 2026-04-06 00:00:00 +0800
# 最近一次运行成功时间: 2026-04-06 00:00:00 +0800
# 测试目的: 验证 axis 越界时稳定报 `KernelSplitAxisMismatch`。
# 对应功能实现文件路径: kernel_gen/passes/lowering/kernel_split.py
# 对应 spec 文件路径: spec/pass/lowering/kernel_split.md
# 对应测试文件路径: test/pass/test_lowering_kernel_split.py
def test_kernel_split_pass_rejects_axis_mismatch() -> None:
    module, _ = _make_marked_kernel_module(
        include_temp_alloc=True,
        reuse_temp_as_input=True,
        axis=2,
    )

    with pytest.raises(KernelSplitError, match="KernelSplitAxisMismatch"):
        KernelSplitPass().run(module)


# TC-KS-010
# 创建者: 小李飞刀
# 最后一次更改: 小李飞刀
# 最近一次运行测试时间: 2026-04-06 01:40:00 +0800
# 最近一次运行成功时间: 2026-04-06 01:40:00 +0800
# 测试目的: 验证输入包含非 `kernel/dma/func` 允许子集 op 时 fail-fast 报 `KernelSplitRequiresLoweredKernelIR`。
# 对应功能实现文件路径: kernel_gen/passes/lowering/kernel_split.py
# 对应 spec 文件路径: spec/pass/lowering/kernel_split.md
# 对应测试文件路径: test/pass/test_lowering_kernel_split.py
def test_kernel_split_pass_rejects_unsupported_input_op() -> None:
    module, func_op = _make_marked_kernel_module(
        include_temp_alloc=True,
        reuse_temp_as_input=True,
    )
    block = func_op.body.blocks.first
    block.insert_op_before(_UnsupportedOp(), block.last_op)

    with pytest.raises(KernelSplitError, match="KernelSplitRequiresLoweredKernelIR"):
        KernelSplitPass().run(module)


# TC-KS-011
# 创建者: 小李飞刀
# 最后一次更改: 小李飞刀
# 最近一次运行测试时间: 2026-04-06 01:40:00 +0800
# 最近一次运行成功时间: 2026-04-06 01:40:00 +0800
# 测试目的: 验证多 `nn.memory` 参数 rank 不一致时稳定报 `KernelSplitAxisMismatch`。
# 对应功能实现文件路径: kernel_gen/passes/lowering/kernel_split.py
# 对应 spec 文件路径: spec/pass/lowering/kernel_split.md
# 对应测试文件路径: test/pass/test_lowering_kernel_split.py
def test_kernel_split_pass_rejects_inconsistent_memory_ranks() -> None:
    mem_2d = _make_memory_type((8, 4))
    mem_3d = _make_memory_type((8, 4, 2))
    block = Block(arg_types=[mem_2d, mem_3d, mem_2d])
    block.add_ops(
        [
            KernelAddOp(block.args[0], block.args[2], block.args[2], NnMemorySpaceAttr.from_name("global")),
            func.ReturnOp(),
        ]
    )
    func_op = func.FuncOp(
        "rank_mismatch",
        FunctionType.from_lists([mem_2d, mem_3d, mem_2d], []),
        Region(block),
    )
    func_op.attributes["kernel_split"] = _make_kernel_split_attr(1, "TILE_M")
    module = ModuleOp([func_op])

    with pytest.raises(KernelSplitError, match="KernelSplitAxisMismatch"):
        KernelSplitPass().run(module)


# TC-KS-012
# 创建者: 小李飞刀
# 最后一次更改: 小李飞刀
# 最近一次运行测试时间: 2026-04-06 01:40:00 +0800
# 最近一次运行成功时间: 2026-04-06 01:40:00 +0800
# 测试目的: 验证 `axis < 0` 时稳定报 `KernelSplitAxisMismatch`。
# 对应功能实现文件路径: kernel_gen/passes/lowering/kernel_split.py
# 对应 spec 文件路径: spec/pass/lowering/kernel_split.md
# 对应测试文件路径: test/pass/test_lowering_kernel_split.py
def test_kernel_split_pass_rejects_negative_axis() -> None:
    module, _ = _make_marked_kernel_module(
        include_temp_alloc=True,
        reuse_temp_as_input=True,
        axis=-1,
    )

    with pytest.raises(KernelSplitError, match="KernelSplitAxisMismatch"):
        KernelSplitPass().run(module)


# TC-KS-013
# 创建者: 小李飞刀
# 最后一次更改: 小李飞刀
# 最近一次运行测试时间: 2026-04-06 01:40:00 +0800
# 最近一次运行成功时间: 2026-04-06 01:40:00 +0800
# 测试目的: 验证非整型 `axis` 属性时稳定报 `KernelSplitAxisMismatch`。
# 对应功能实现文件路径: kernel_gen/passes/lowering/kernel_split.py
# 对应 spec 文件路径: spec/pass/lowering/kernel_split.md
# 对应测试文件路径: test/pass/test_lowering_kernel_split.py
def test_kernel_split_pass_rejects_non_integer_axis() -> None:
    module, func_op = _make_marked_kernel_module(
        include_temp_alloc=True,
        reuse_temp_as_input=True,
    )
    func_op.attributes["kernel_split"] = DictionaryAttr(
        {"axis": StringAttr("1"), "tile": StringAttr("TILE_M")}
    )

    with pytest.raises(KernelSplitError, match="KernelSplitAxisMismatch"):
        KernelSplitPass().run(module)


# TC-KS-014
# 创建者: 小李飞刀
# 最后一次更改: 小李飞刀
# 最近一次运行测试时间: 2026-04-06 01:40:00 +0800
# 最近一次运行成功时间: 2026-04-06 01:40:00 +0800
# 测试目的: 验证函数无 `nn.memory` 参数时稳定报 `KernelSplitAxisMismatch`。
# 对应功能实现文件路径: kernel_gen/passes/lowering/kernel_split.py
# 对应 spec 文件路径: spec/pass/lowering/kernel_split.md
# 对应测试文件路径: test/pass/test_lowering_kernel_split.py
def test_kernel_split_pass_rejects_missing_memory_arguments() -> None:
    block = Block(arg_types=[i32])
    block.add_op(func.ReturnOp())
    func_op = func.FuncOp("no_memory", FunctionType.from_lists([i32], []), Region(block))
    func_op.attributes["kernel_split"] = _make_kernel_split_attr(0, "TILE_M")
    module = ModuleOp([func_op])

    with pytest.raises(KernelSplitError, match="KernelSplitAxisMismatch"):
        KernelSplitPass().run(module)
