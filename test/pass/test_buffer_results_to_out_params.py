"""buffer-results-to-out-params pass tests.

创建者: 朽木露琪亚
最后一次更改: 金铲铲大作战

功能说明:
- 覆盖 buffer-results-to-out-params pass 的最小骨架行为与失败边界。

使用示例:
- pytest -q test/pass/test_buffer_results_to_out_params.py

关联文件:
- 功能实现: kernel_gen/passes/lowering/buffer_results_to_out_params.py
- Spec 文档: spec/pass/lowering/buffer_results_to_out_params.md
- 测试文件: test/pass/test_buffer_results_to_out_params.py
"""

from __future__ import annotations

import importlib
import sys
from pathlib import Path

import pytest
from xdsl.dialects import arith, func
from xdsl.dialects.builtin import (
    ArrayAttr,
    DictionaryAttr,
    FunctionType,
    IntAttr,
    IntegerAttr,
    ModuleOp,
    StringAttr,
    i32,
)
from xdsl.ir import Block, Region

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from kernel_gen.dialect.dma import DmaAllocOp, DmaFillOp
from kernel_gen.dialect.nn import NnMemorySpaceAttr, NnMemoryType
from kernel_gen.passes.lowering.nn_to_kernel import LowerNnToKernelPass
from kernel_gen.passes.pass_manager import PassManager

pass_module = importlib.import_module(
    "kernel_gen.passes.lowering.buffer_results_to_out_params"
)
BufferResultsToOutParamsError = pass_module.BufferResultsToOutParamsError
BufferResultsToOutParamsPass = pass_module.BufferResultsToOutParamsPass


def _make_memory_type() -> NnMemoryType:
    """构造测试用 `nn.memory` 类型。

    创建者: 朽木露琪亚
    最后一次更改: 朽木露琪亚

    功能说明:
    - 统一生成 `[2, 3]`、`i32`、`global` 的 memory 类型。

    使用示例:
    - mem_type = _make_memory_type()

    关联文件:
    - spec: spec/pass/lowering/buffer_results_to_out_params.md
    - test: test/pass/test_buffer_results_to_out_params.py
    - 功能实现: kernel_gen/passes/lowering/buffer_results_to_out_params.py
    """

    return NnMemoryType(
        ArrayAttr([IntAttr(2), IntAttr(3)]),
        ArrayAttr([IntAttr(3), IntAttr(1)]),
        i32,
        NnMemorySpaceAttr.from_name("global"),
    )


def _make_memory_type_with_shape(shape: tuple[int, ...]) -> NnMemoryType:
    """构造指定 shape 的测试用 `nn.memory` 类型。

    创建者: 金铲铲大作战
    最后一次更改: 金铲铲大作战

    功能说明:
    - 为多 output 顺序测试生成可区分的 memory 类型。
    - stride 固定按紧致布局自动推导。

    使用示例:
    - mem_type = _make_memory_type_with_shape((2, 4))

    关联文件:
    - spec: spec/pass/lowering/buffer_results_to_out_params.md
    - test: test/pass/test_buffer_results_to_out_params.py
    - 功能实现: kernel_gen/passes/lowering/buffer_results_to_out_params.py
    """

    stride: list[int] = []
    acc = 1
    for dim in reversed(shape):
        stride.append(acc)
        acc *= dim
    stride.reverse()
    return NnMemoryType(
        ArrayAttr([IntAttr(dim) for dim in shape]),
        ArrayAttr([IntAttr(dim) for dim in stride]),
        i32,
        NnMemorySpaceAttr.from_name("global"),
    )


def _arg_attrs(*names: str) -> ArrayAttr[DictionaryAttr]:
    """构造函数参数名称属性。

    创建者: 朽木露琪亚
    最后一次更改: 朽木露琪亚

    功能说明:
    - 为测试中的 `func.FuncOp` 统一构造 `arg_attrs.name`。

    使用示例:
    - attrs = _arg_attrs("src")

    关联文件:
    - spec: spec/pass/lowering/buffer_results_to_out_params.md
    - test: test/pass/test_buffer_results_to_out_params.py
    - 功能实现: kernel_gen/passes/lowering/buffer_results_to_out_params.py
    """

    return ArrayAttr([DictionaryAttr({"name": StringAttr(name)}) for name in names])


# BROTP-001
# 创建者: 朽木露琪亚
# 最后一次更改: 朽木露琪亚
# 最近一次运行测试时间: 2026-04-04 00:00:00 +0800
# 最近一次运行成功时间: 2026-04-04 00:00:00 +0800
# 功能说明: 验证单个 memory 返回值会被改写为最前置 out 参数。
# 测试目的: 锁定 function_type.inputs 最前插入 arg0、outputs 清空、func.return 变为空 return，且函数体内对返回 buffer 的使用改写到 arg0。
# 使用示例: pytest -q test/pass/test_buffer_results_to_out_params.py -k test_rewrite_single_memory_result_to_front_out_param
# 对应功能实现文件路径: kernel_gen/passes/lowering/buffer_results_to_out_params.py
# 对应 spec 文件路径: spec/pass/lowering/buffer_results_to_out_params.md
# 对应测试文件路径: test/pass/test_buffer_results_to_out_params.py
def test_rewrite_single_memory_result_to_front_out_param() -> None:
    mem_type = _make_memory_type()
    block = Block(arg_types=[mem_type])
    fill_value = arith.ConstantOp(IntegerAttr(7, i32))
    alloc_op = DmaAllocOp([], mem_type)
    fill_op = DmaFillOp(alloc_op.result, fill_value.result)
    return_op = func.ReturnOp(alloc_op.result)
    block.add_ops([fill_value, alloc_op, fill_op, return_op])
    func_op = func.FuncOp(
        "single_memory_result",
        FunctionType.from_lists([mem_type], [mem_type]),
        Region(block),
        arg_attrs=_arg_attrs("src"),
    )
    module = ModuleOp([func_op])

    BufferResultsToOutParamsPass().run(module)

    assert list(func_op.function_type.inputs) == [mem_type, mem_type]
    assert list(func_op.function_type.outputs) == []
    assert func_op.arg_attrs.data[0].data["name"] == StringAttr("arg0")
    assert func_op.arg_attrs.data[1].data["name"] == StringAttr("src")
    body_ops = list(func_op.body.blocks.first.ops)
    assert not any(isinstance(op, DmaAllocOp) for op in body_ops)
    rewritten_fill = next(op for op in body_ops if isinstance(op, DmaFillOp))
    assert rewritten_fill.target == func_op.args[0]
    rewritten_return = next(op for op in body_ops if isinstance(op, func.ReturnOp))
    assert len(rewritten_return.arguments) == 0


# BROTP-002
# 创建者: 朽木露琪亚
# 最后一次更改: 朽木露琪亚
# 最近一次运行测试时间: 2026-04-04 00:00:00 +0800
# 最近一次运行成功时间: 2026-04-04 00:00:00 +0800
# 功能说明: 验证 external declaration 会被显式拒绝。
# 测试目的: 锁定未定义函数体的 memory-return 函数不会被半改写。
# 使用示例: pytest -q test/pass/test_buffer_results_to_out_params.py -k test_rewrite_rejects_external_declaration
# 对应功能实现文件路径: kernel_gen/passes/lowering/buffer_results_to_out_params.py
# 对应 spec 文件路径: spec/pass/lowering/buffer_results_to_out_params.md
# 对应测试文件路径: test/pass/test_buffer_results_to_out_params.py
def test_rewrite_rejects_external_declaration() -> None:
    mem_type = _make_memory_type()
    external_func = func.FuncOp(
        "external_memory_result",
        FunctionType.from_lists([mem_type], [mem_type]),
    )
    module = ModuleOp([external_func])

    with pytest.raises(BufferResultsToOutParamsError, match="external declaration"):
        BufferResultsToOutParamsPass().run(module)


# BROTP-003
# 创建者: 朽木露琪亚
# 最后一次更改: 朽木露琪亚
# 最近一次运行测试时间: 2026-04-04 00:00:00 +0800
# 最近一次运行成功时间: 2026-04-04 00:00:00 +0800
# 功能说明: 验证模块内 caller/callee 会同步改写为显式 out 实参 + 零 result 的 func.call。
# 测试目的: 锁定 pass 不再保留旧 memory call result SSA，caller 侧必须先提供 out buffer。
# 使用示例: pytest -q test/pass/test_buffer_results_to_out_params.py -k test_rewrite_callsite_replaces_old_memory_result_ssa
# 对应功能实现文件路径: kernel_gen/passes/lowering/buffer_results_to_out_params.py
# 对应 spec 文件路径: spec/pass/lowering/buffer_results_to_out_params.md
# 对应测试文件路径: test/pass/test_buffer_results_to_out_params.py
def test_rewrite_callsite_replaces_old_memory_result_ssa() -> None:
    mem_type = _make_memory_type()

    callee_block = Block(arg_types=[mem_type])
    callee_return = func.ReturnOp(callee_block.args[0])
    callee_block.add_op(callee_return)
    callee = func.FuncOp(
        "callee",
        FunctionType.from_lists([mem_type], [mem_type]),
        Region(callee_block),
        arg_attrs=_arg_attrs("src"),
    )

    caller_block = Block(arg_types=[mem_type])
    fill_value = arith.ConstantOp(IntegerAttr(7, i32))
    call_op = func.CallOp("callee", [caller_block.args[0]], [mem_type])
    fill_op = DmaFillOp(call_op.results[0], fill_value.result)
    caller_return = func.ReturnOp()
    caller_block.add_ops([fill_value, call_op, fill_op, caller_return])
    caller = func.FuncOp(
        "caller",
        FunctionType.from_lists([mem_type], []),
        Region(caller_block),
        arg_attrs=_arg_attrs("src"),
    )

    module = ModuleOp([callee, caller])

    BufferResultsToOutParamsPass().run(module)

    assert list(callee.function_type.inputs) == [mem_type, mem_type]
    assert list(callee.function_type.outputs) == []
    assert callee.arg_attrs.data[0].data["name"] == StringAttr("arg0")

    caller_ops = list(caller.body.blocks.first.ops)
    alloc_op = next(op for op in caller_ops if isinstance(op, DmaAllocOp))
    rewritten_call = next(op for op in caller_ops if isinstance(op, func.CallOp))
    rewritten_fill = next(op for op in caller_ops if isinstance(op, DmaFillOp))

    assert len(rewritten_call.results) == 0
    assert tuple(rewritten_call.arguments) == (alloc_op.result, caller.args[0])
    assert rewritten_fill.target == alloc_op.result


# BROTP-004
# 创建者: 朽木露琪亚
# 最后一次更改: 朽木露琪亚
# 最近一次运行测试时间: 2026-04-04 00:00:00 +0800
# 最近一次运行成功时间: 2026-04-04 00:00:00 +0800
# 功能说明: 验证 lowering pipeline 中 BufferResultsToOutParamsPass 固定运行在 LowerNnToKernelPass 之后。
# 测试目的: 锁定 O2 的 pass 链路位置，避免实现又回退到手工拼接或错误顺序。
# 使用示例: pytest -q test/pass/test_buffer_results_to_out_params.py -k test_pass_manager_runs_lower_then_buffer_results_to_out_params
# 对应功能实现文件路径: kernel_gen/passes/lowering/buffer_results_to_out_params.py
# 对应 spec 文件路径: spec/pass/pass_manager.md
# 对应测试文件路径: test/pass/test_buffer_results_to_out_params.py
def _assert_pass_manager_runs_lower_then_buffer_results_to_out_params(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    order: list[str] = []
    original_lower_run = LowerNnToKernelPass.run
    original_buffer_run = BufferResultsToOutParamsPass.run

    def _record_lower(self: LowerNnToKernelPass, module: ModuleOp) -> ModuleOp:
        order.append(self.name)
        return original_lower_run(self, module)

    def _record_buffer(
        self: BufferResultsToOutParamsPass, module: ModuleOp
    ) -> ModuleOp:
        order.append(self.name)
        return original_buffer_run(self, module)

    monkeypatch.setattr(LowerNnToKernelPass, "run", _record_lower)
    monkeypatch.setattr(BufferResultsToOutParamsPass, "run", _record_buffer)

    mem_type = _make_memory_type()
    block = Block(arg_types=[mem_type])
    fill_value = arith.ConstantOp(IntegerAttr(7, i32))
    alloc_op = DmaAllocOp([], mem_type)
    fill_op = DmaFillOp(alloc_op.result, fill_value.result)
    return_op = func.ReturnOp(alloc_op.result)
    block.add_ops([fill_value, alloc_op, fill_op, return_op])
    func_op = func.FuncOp(
        "single_memory_result",
        FunctionType.from_lists([mem_type], [mem_type]),
        Region(block),
        arg_attrs=_arg_attrs("src"),
    )
    module = ModuleOp([func_op])

    pm = PassManager(name="lowering")
    pm.add_pass(LowerNnToKernelPass())
    pm.add_pass(BufferResultsToOutParamsPass())
    pm.run(module)

    assert order == ["lower-nn-to-kernel", "buffer-results-to-out-params"]


def test_pass_manager_runs_lower_then_buffer_results_to_out_params(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _assert_pass_manager_runs_lower_then_buffer_results_to_out_params(monkeypatch)


def test_pipeline_position_pass_manager_runs_lower_then_buffer_results_to_out_params(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _assert_pass_manager_runs_lower_then_buffer_results_to_out_params(monkeypatch)


# BROTP-006
# 创建者: 金铲铲大作战
# 最后一次更改: 金铲铲大作战
# 最近一次运行测试时间: 2026-04-04 00:00:00 +0800
# 最近一次运行成功时间: 2026-04-04 00:00:00 +0800
# 功能说明: 验证双 memory returns 会固定重排为最前置 `arg0/arg1`，并同步改写 caller 侧 callsite。
# 测试目的: 锁定多个 output 的前置顺序与 caller 显式 out 实参顺序，不允许交换或保留旧 memory call result SSA。
# 使用示例: pytest -q test/pass/test_buffer_results_to_out_params.py -k test_rewrite_multiple_memory_results_to_arg0_arg1
# 对应功能实现文件路径: kernel_gen/passes/lowering/buffer_results_to_out_params.py
# 对应 spec 文件路径: spec/pass/lowering/buffer_results_to_out_params.md
# 对应测试文件路径: test/pass/test_buffer_results_to_out_params.py
def test_rewrite_multiple_memory_results_to_arg0_arg1() -> None:
    mem_type_a = _make_memory_type_with_shape((2, 3))
    mem_type_b = _make_memory_type_with_shape((3, 2))

    callee_block = Block()
    fill_a_value = arith.ConstantOp(IntegerAttr(7, i32))
    fill_b_value = arith.ConstantOp(IntegerAttr(9, i32))
    alloc_a = DmaAllocOp([], mem_type_a)
    alloc_b = DmaAllocOp([], mem_type_b)
    fill_a = DmaFillOp(alloc_a.result, fill_a_value.result)
    fill_b = DmaFillOp(alloc_b.result, fill_b_value.result)
    callee_return = func.ReturnOp(alloc_a.result, alloc_b.result)
    callee_block.add_ops([fill_a_value, fill_b_value, alloc_a, alloc_b, fill_a, fill_b, callee_return])
    callee = func.FuncOp(
        "split",
        FunctionType.from_lists([], [mem_type_a, mem_type_b]),
        Region(callee_block),
        arg_attrs=_arg_attrs(),
    )

    caller_block = Block()
    call_op = func.CallOp("split", [], [mem_type_a, mem_type_b])
    use_a_value = arith.ConstantOp(IntegerAttr(1, i32))
    use_b_value = arith.ConstantOp(IntegerAttr(2, i32))
    use_a = DmaFillOp(call_op.results[0], use_a_value.result)
    use_b = DmaFillOp(call_op.results[1], use_b_value.result)
    caller_return = func.ReturnOp()
    caller_block.add_ops([call_op, use_a_value, use_b_value, use_a, use_b, caller_return])
    caller = func.FuncOp("caller", FunctionType.from_lists([], []), Region(caller_block), arg_attrs=_arg_attrs())

    module = ModuleOp([callee, caller])

    BufferResultsToOutParamsPass().run(module)

    assert list(callee.function_type.inputs) == [mem_type_a, mem_type_b]
    assert list(callee.function_type.outputs) == []
    assert callee.arg_attrs.data[0].data["name"] == StringAttr("arg0")
    assert callee.arg_attrs.data[1].data["name"] == StringAttr("arg1")
    callee_ops = list(callee.body.blocks.first.ops)
    assert not any(isinstance(op, DmaAllocOp) for op in callee_ops)
    rewritten_fill_ops = [op for op in callee_ops if isinstance(op, DmaFillOp)]
    assert rewritten_fill_ops[0].target == callee.args[0]
    assert rewritten_fill_ops[1].target == callee.args[1]
    rewritten_return = next(op for op in callee_ops if isinstance(op, func.ReturnOp))
    assert len(rewritten_return.arguments) == 0

    caller_ops = list(caller.body.blocks.first.ops)
    alloc_ops = [op for op in caller_ops if isinstance(op, DmaAllocOp)]
    rewritten_call = next(op for op in caller_ops if isinstance(op, func.CallOp))
    caller_fill_ops = [op for op in caller_ops if isinstance(op, DmaFillOp)]
    assert len(alloc_ops) == 2
    assert len(rewritten_call.results) == 0
    assert tuple(rewritten_call.arguments) == (alloc_ops[0].result, alloc_ops[1].result)
    assert caller_fill_ops[0].target == alloc_ops[0].result
    assert caller_fill_ops[1].target == alloc_ops[1].result


# BROTP-007
# 创建者: 金铲铲大作战
# 最后一次更改: 金铲铲大作战
# 最近一次运行测试时间: 2026-04-04 00:00:00 +0800
# 最近一次运行成功时间: 2026-04-04 00:00:00 +0800
# 功能说明: 验证 `memory + scalar` 混合返回会前置 memory out，同时保留 scalar 返回。
# 测试目的: 锁定 mixed returns 改写后 caller 侧 `func.call` 只保留 scalar result，旧 memory result SSA 不再存在。
# 使用示例: pytest -q test/pass/test_buffer_results_to_out_params.py -k test_rewrite_mixed_memory_and_scalar_results_preserves_scalar_return
# 对应功能实现文件路径: kernel_gen/passes/lowering/buffer_results_to_out_params.py
# 对应 spec 文件路径: spec/pass/lowering/buffer_results_to_out_params.md
# 对应测试文件路径: test/pass/test_buffer_results_to_out_params.py
def test_rewrite_mixed_memory_and_scalar_results_preserves_scalar_return() -> None:
    mem_type = _make_memory_type()

    callee_block = Block(arg_types=[mem_type])
    fill_value = arith.ConstantOp(IntegerAttr(7, i32))
    flag_value = arith.ConstantOp(IntegerAttr(1, i32))
    alloc_op = DmaAllocOp([], mem_type)
    fill_op = DmaFillOp(alloc_op.result, fill_value.result)
    callee_return = func.ReturnOp(alloc_op.result, flag_value.result)
    callee_block.add_ops([fill_value, flag_value, alloc_op, fill_op, callee_return])
    callee = func.FuncOp(
        "reduce",
        FunctionType.from_lists([mem_type], [mem_type, i32]),
        Region(callee_block),
        arg_attrs=_arg_attrs("src"),
    )

    caller_block = Block(arg_types=[mem_type])
    call_op = func.CallOp("reduce", [caller_block.args[0]], [mem_type, i32])
    use_value = arith.ConstantOp(IntegerAttr(9, i32))
    use_fill = DmaFillOp(call_op.results[0], use_value.result)
    caller_return = func.ReturnOp(call_op.results[1])
    caller_block.add_ops([call_op, use_value, use_fill, caller_return])
    caller = func.FuncOp(
        "caller",
        FunctionType.from_lists([mem_type], [i32]),
        Region(caller_block),
        arg_attrs=_arg_attrs("src"),
    )

    module = ModuleOp([callee, caller])

    BufferResultsToOutParamsPass().run(module)

    assert list(callee.function_type.inputs) == [mem_type, mem_type]
    assert list(callee.function_type.outputs) == [i32]
    assert callee.arg_attrs.data[0].data["name"] == StringAttr("arg0")
    assert callee.arg_attrs.data[1].data["name"] == StringAttr("src")
    callee_ops = list(callee.body.blocks.first.ops)
    assert not any(isinstance(op, DmaAllocOp) for op in callee_ops)
    rewritten_fill = next(op for op in callee_ops if isinstance(op, DmaFillOp))
    assert rewritten_fill.target == callee.args[0]
    rewritten_return = next(op for op in callee_ops if isinstance(op, func.ReturnOp))
    assert len(rewritten_return.arguments) == 1
    assert rewritten_return.arguments[0].type == i32

    caller_ops = list(caller.body.blocks.first.ops)
    alloc_op = next(op for op in caller_ops if isinstance(op, DmaAllocOp))
    rewritten_call = next(op for op in caller_ops if isinstance(op, func.CallOp))
    rewritten_fill = next(op for op in caller_ops if isinstance(op, DmaFillOp))
    rewritten_return = next(op for op in caller_ops if isinstance(op, func.ReturnOp))
    assert tuple(rewritten_call.arguments) == (alloc_op.result, caller.args[0])
    assert len(rewritten_call.results) == 1
    assert rewritten_call.results[0].type == i32
    assert rewritten_fill.target == alloc_op.result
    assert rewritten_return.arguments[0] == rewritten_call.results[0]
