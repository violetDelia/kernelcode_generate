"""decompose-nn-softmax pass tests.

创建者: 朽木露琪亚
最后一次更改: 朽木露琪亚

功能说明:
- 覆盖 `DecomposeNnSoftmaxPass` 的固定分解链、负轴规整与失败边界。

使用示例:
- pytest -q test/pass/test_decompose_nn_softmax.py

关联文件:
- 功能实现: kernel_gen/passes/lowering/decompose_nn_softmax.py
- Spec 文档: spec/pass/lowering/decompose_nn_softmax.md
- 测试文件: test/pass/test_decompose_nn_softmax.py
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest
from xdsl.dialects import func
from xdsl.dialects.builtin import ArrayAttr, FunctionType, IntAttr, ModuleOp, StringAttr, f32
from xdsl.ir import Attribute, Block, Region

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from kernel_gen.dialect.nn import (
    NnBroadcastOp,
    NnExpOp,
    NnMemorySpaceAttr,
    NnMemoryType,
    NnReduceMaxOp,
    NnReduceSumOp,
    NnSoftmaxOp,
    NnSubOp,
    NnTrueDivOp,
)
from kernel_gen.passes.lowering.decompose_nn_softmax import (
    DecomposeNnSoftmaxError,
    DecomposeNnSoftmaxPass,
)


def _build_contiguous_stride(shape: tuple[int | str, ...]) -> ArrayAttr[Attribute]:
    """为测试 shape 生成连续布局 stride。"""

    factors: list[str | int] = []
    strides: list[Attribute] = []
    for _dim in reversed(shape):
        if not factors:
            strides.append(IntAttr(1))
        else:
            int_product = 1
            expr_parts: list[str] = []
            for factor in factors:
                if isinstance(factor, int):
                    int_product *= factor
                else:
                    expr_parts.append(factor)
            if expr_parts:
                parts: list[str] = []
                if int_product != 1:
                    parts.append(str(int_product))
                parts.extend(expr_parts)
                strides.append(StringAttr("*".join(parts)))
            else:
                strides.append(IntAttr(int_product))
        factors.insert(0, _dim)
    strides.reverse()
    return ArrayAttr(strides)


def _make_memory_type(shape: tuple[int | str, ...]) -> NnMemoryType:
    """构造测试用 `nn.memory` 类型。"""

    shape_attr = ArrayAttr(
        [IntAttr(dim) if isinstance(dim, int) else StringAttr(dim) for dim in shape]
    )
    return NnMemoryType(
        shape_attr,
        _build_contiguous_stride(shape),
        f32,
        NnMemorySpaceAttr.from_name("global"),
    )


def _make_softmax_module(
    *,
    input_type: NnMemoryType,
    result_type: NnMemoryType | None = None,
    axis: int,
) -> tuple[ModuleOp, func.FuncOp]:
    """构造只包含一个 `nn.softmax` 的测试 module。"""

    actual_result_type = result_type or input_type
    block = Block(arg_types=[input_type])
    softmax_op = NnSoftmaxOp(block.args[0], actual_result_type, axis=axis, space=input_type.space)
    return_op = func.ReturnOp(softmax_op.result)
    block.add_ops([softmax_op, return_op])
    func_op = func.FuncOp(
        "softmax_kernel",
        FunctionType.from_lists([input_type], [actual_result_type]),
        Region(block),
    )
    return ModuleOp([func_op]), func_op


def _entry_ops(func_op: func.FuncOp) -> list[object]:
    """返回 entry block op 列表。"""

    return list(func_op.body.blocks.first.ops)


# DNS-001
# 创建者: 朽木露琪亚
# 最后一次更改: 朽木露琪亚
# 最近一次运行测试时间: 2026-04-07 16:00:00 +0800
# 最近一次运行成功时间: 2026-04-07 16:00:00 +0800
# 功能说明: 验证 decompose-nn-softmax 会把 nn.softmax 固定改写为 7 段链。
# 测试目的: 锁定 reduce_max -> broadcast -> sub -> exp -> reduce_sum -> broadcast -> truediv 的顺序与结果替换合同。
# 使用示例: pytest -q test/pass/test_decompose_nn_softmax.py -k test_decompose_softmax_into_fixed_nn_chain
# 对应功能实现文件路径: kernel_gen/passes/lowering/decompose_nn_softmax.py
# 对应 spec 文件路径: spec/pass/lowering/decompose_nn_softmax.md
# 对应测试文件路径: test/pass/test_decompose_nn_softmax.py
def test_decompose_softmax_into_fixed_nn_chain() -> None:
    mem_type = _make_memory_type((2, 3))
    module, func_op = _make_softmax_module(input_type=mem_type, axis=1)

    DecomposeNnSoftmaxPass().run(module)
    module.verify()

    body_ops = _entry_ops(func_op)
    assert [op.name for op in body_ops] == [
        "nn.reduce_max",
        "nn.broadcast",
        "nn.sub",
        "nn.exp",
        "nn.reduce_sum",
        "nn.broadcast",
        "nn.truediv",
        "func.return",
    ]
    assert not any(isinstance(op, NnSoftmaxOp) for op in body_ops)

    reduce_max = next(op for op in body_ops if isinstance(op, NnReduceMaxOp))
    reduce_sum = next(op for op in body_ops if isinstance(op, NnReduceSumOp))
    broadcasts = [op for op in body_ops if isinstance(op, NnBroadcastOp)]
    exp_op = next(op for op in body_ops if isinstance(op, NnExpOp))
    div_op = next(op for op in body_ops if isinstance(op, NnTrueDivOp))
    return_op = next(op for op in body_ops if isinstance(op, func.ReturnOp))

    assert [entry.value.data for entry in reduce_max.axes.data] == [1]
    assert reduce_max.keepdim.value.data != 0
    assert [entry.value.data for entry in reduce_sum.axes.data] == [1]
    assert reduce_sum.keepdim.value.data != 0
    assert len(broadcasts) == 2
    assert all(broadcast.result.type == mem_type for broadcast in broadcasts)
    assert exp_op.result.type == mem_type
    assert div_op.result.type == mem_type
    assert return_op.arguments[0] == div_op.result
    assert list(reduce_max.result.type.shape.data) == [IntAttr(2), IntAttr(1)]
    assert list(reduce_max.result.type.stride.data) == [IntAttr(1), IntAttr(1)]


# DNS-002
# 创建者: 朽木露琪亚
# 最后一次更改: 朽木露琪亚
# 最近一次运行测试时间: 2026-04-07 16:00:00 +0800
# 最近一次运行成功时间: 2026-04-07 16:00:00 +0800
# 功能说明: 验证负轴会在 pass 内规整为非负下标。
# 测试目的: 锁定 axis=-1 在 rank=3 时会落到 axes=[2]。
# 使用示例: pytest -q test/pass/test_decompose_nn_softmax.py -k test_decompose_softmax_normalizes_negative_axis
# 对应功能实现文件路径: kernel_gen/passes/lowering/decompose_nn_softmax.py
# 对应 spec 文件路径: spec/pass/lowering/decompose_nn_softmax.md
# 对应测试文件路径: test/pass/test_decompose_nn_softmax.py
def test_decompose_softmax_normalizes_negative_axis() -> None:
    mem_type = _make_memory_type((2, 3, 4))
    module, func_op = _make_softmax_module(input_type=mem_type, axis=-1)

    DecomposeNnSoftmaxPass().run(module)
    module.verify()

    reduce_max = next(op for op in _entry_ops(func_op) if isinstance(op, NnReduceMaxOp))
    reduce_sum = next(op for op in _entry_ops(func_op) if isinstance(op, NnReduceSumOp))
    assert [entry.value.data for entry in reduce_max.axes.data] == [2]
    assert [entry.value.data for entry in reduce_sum.axes.data] == [2]
    assert list(reduce_max.result.type.shape.data) == [IntAttr(2), IntAttr(3), IntAttr(1)]
    assert list(reduce_max.result.type.stride.data) == [IntAttr(3), IntAttr(1), IntAttr(1)]


# DNS-003
# 创建者: 朽木露琪亚
# 最后一次更改: 朽木露琪亚
# 最近一次运行测试时间: 2026-04-07 16:00:00 +0800
# 最近一次运行成功时间: 2026-04-07 16:00:00 +0800
# 功能说明: 验证规整后的 axis 越界时会返回固定短语。
# 测试目的: 锁定 pass 不依赖方言 verifier 的通用错误，而是显式给出 normalized axis out of range。
# 使用示例: pytest -q test/pass/test_decompose_nn_softmax.py -k test_decompose_softmax_rejects_normalized_axis_out_of_range
# 对应功能实现文件路径: kernel_gen/passes/lowering/decompose_nn_softmax.py
# 对应 spec 文件路径: spec/pass/lowering/decompose_nn_softmax.md
# 对应测试文件路径: test/pass/test_decompose_nn_softmax.py
def test_decompose_softmax_rejects_normalized_axis_out_of_range() -> None:
    mem_type = _make_memory_type((2, 3))
    module, _func_op = _make_softmax_module(input_type=mem_type, axis=3)

    with pytest.raises(
        DecomposeNnSoftmaxError,
        match="DecomposeNnSoftmaxError: normalized axis out of range",
    ):
        DecomposeNnSoftmaxPass().run(module)


# DNS-004
# 创建者: 朽木露琪亚
# 最后一次更改: 朽木露琪亚
# 最近一次运行测试时间: 2026-04-07 16:00:00 +0800
# 最近一次运行成功时间: 2026-04-07 16:00:00 +0800
# 功能说明: 验证 softmax 结果 shape/stride 与输入不一致时显式失败。
# 测试目的: 锁定 pass 在 malformed softmax 上给出固定失败短语，避免产生半合法分解链。
# 使用示例: pytest -q test/pass/test_decompose_nn_softmax.py -k test_decompose_softmax_rejects_result_type_mismatch
# 对应功能实现文件路径: kernel_gen/passes/lowering/decompose_nn_softmax.py
# 对应 spec 文件路径: spec/pass/lowering/decompose_nn_softmax.md
# 对应测试文件路径: test/pass/test_decompose_nn_softmax.py
def test_decompose_softmax_rejects_result_type_mismatch() -> None:
    input_type = _make_memory_type((2, 3))
    bad_result_type = NnMemoryType(
        ArrayAttr([IntAttr(2), IntAttr(3)]),
        ArrayAttr([IntAttr(1), IntAttr(3)]),
        f32,
        NnMemorySpaceAttr.from_name("global"),
    )
    module, _func_op = _make_softmax_module(
        input_type=input_type,
        result_type=bad_result_type,
        axis=1,
    )

    with pytest.raises(
        DecomposeNnSoftmaxError,
        match="DecomposeNnSoftmaxError: result type must match input shape and stride",
    ):
        DecomposeNnSoftmaxPass().run(module)
