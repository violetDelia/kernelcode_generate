"""buffer-results-to-out-params pass tests.

创建者: 朽木露琪亚
最后一次更改: 朽木露琪亚

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
# 功能说明: 验证在未实现 callsite 同步改写前，模块内调用待改写函数会显式失败。
# 测试目的: 锁定 pass 不会只改 callee 签名和 return，而把 caller 留在旧口径。
# 使用示例: pytest -q test/pass/test_buffer_results_to_out_params.py -k test_rewrite_rejects_unrewritten_callsite
# 对应功能实现文件路径: kernel_gen/passes/lowering/buffer_results_to_out_params.py
# 对应 spec 文件路径: spec/pass/lowering/buffer_results_to_out_params.md
# 对应测试文件路径: test/pass/test_buffer_results_to_out_params.py
def test_rewrite_rejects_unrewritten_callsite() -> None:
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
    call_op = func.CallOp("callee", [caller_block.args[0]], [mem_type])
    caller_return = func.ReturnOp(call_op.results[0])
    caller_block.add_ops([call_op, caller_return])
    caller = func.FuncOp(
        "caller",
        FunctionType.from_lists([mem_type], [mem_type]),
        Region(caller_block),
        arg_attrs=_arg_attrs("src"),
    )

    module = ModuleOp([callee, caller])

    with pytest.raises(BufferResultsToOutParamsError, match="callsite rewrite"):
        BufferResultsToOutParamsPass().run(module)
