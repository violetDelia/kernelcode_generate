"""decompose-nn-softmax expectation.

创建者: 小李飞刀
最后一次更改: 小李飞刀

功能说明:
- 以黑盒方式锁定 `DecomposeNnSoftmaxPass` 对 `nn.softmax` 的固定分解链。
- 输出 before/after IR，并断言分解后不再保留 `nn.softmax`。
- 锁定 reduce_max/reduce_sum 的 axes 规整与 keepdim 合同。

使用示例:
- `PYTHONPATH=. python expectation/pass/lowering/decompose_nn_softmax.py`

关联文件:
- spec: `spec/pass/lowering/decompose_nn_softmax.md`
- test: `test/pass/test_decompose_nn_softmax.py`
- 功能实现: `kernel_gen/passes/lowering/decompose_nn_softmax.py`
"""

from __future__ import annotations

import sys
from pathlib import Path

from xdsl.dialects import func
from xdsl.dialects.builtin import ArrayAttr, FunctionType, IntAttr, ModuleOp, Region, StringAttr, f32
from xdsl.ir import Attribute, Block

REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from expectation.utils.case_runner import raise_if_failures, run_case
from kernel_gen.dialect.nn import (
    NnBroadcastOp,
    NnExpOp,
    NnMemorySpaceAttr,
    NnMemoryType,
    NnReduceMaxOp,
    NnReduceSumOp,
    NnSoftmaxOp,
    NnTrueDivOp,
)
from kernel_gen.passes.lowering.decompose_nn_softmax import DecomposeNnSoftmaxPass


def _build_contiguous_stride(shape: tuple[int | str, ...]) -> ArrayAttr[Attribute]:
    """为 expectation 生成 contiguous stride。"""

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
    """构造 expectation 用 `nn.memory` 类型。"""

    shape_attr = ArrayAttr(
        [IntAttr(dim) if isinstance(dim, int) else StringAttr(dim) for dim in shape]
    )
    return NnMemoryType(
        shape_attr,
        _build_contiguous_stride(shape),
        f32,
        NnMemorySpaceAttr.from_name("global"),
    )


def _make_softmax_module(*, input_type: NnMemoryType, axis: int) -> tuple[ModuleOp, func.FuncOp]:
    """构造只包含一个 `nn.softmax` 的 module。"""

    block = Block(arg_types=[input_type])
    softmax_op = NnSoftmaxOp(block.args[0], input_type, axis=axis, space=input_type.space)
    return_op = func.ReturnOp(softmax_op.result)
    block.add_ops([softmax_op, return_op])
    func_op = func.FuncOp(
        "softmax_kernel",
        FunctionType.from_lists([input_type], [input_type]),
        Region(block),
    )
    return ModuleOp([func_op]), func_op


def _entry_ops(func_op: func.FuncOp) -> list[object]:
    """返回 entry block op 列表。"""

    return list(func_op.body.blocks.first.ops)


def _case_1_fixed_chain() -> None:
    print("[CASE-1] nn.softmax must be decomposed into fixed 7-op nn chain")
    mem_type = _make_memory_type((2, 3))
    module, func_op = _make_softmax_module(input_type=mem_type, axis=1)

    print("[BEFORE]")
    print(module)
    DecomposeNnSoftmaxPass().run(module)
    module.verify()
    print("[AFTER]")
    print(module)

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

    reduce_max = next(op for op in body_ops if isinstance(op, NnReduceMaxOp))
    reduce_sum = next(op for op in body_ops if isinstance(op, NnReduceSumOp))
    broadcasts = [op for op in body_ops if isinstance(op, NnBroadcastOp)]
    exp_op = next(op for op in body_ops if isinstance(op, NnExpOp))
    div_op = next(op for op in body_ops if isinstance(op, NnTrueDivOp))

    assert [entry.value.data for entry in reduce_max.axes.data] == [1]
    assert reduce_max.keepdim.value.data != 0
    assert [entry.value.data for entry in reduce_sum.axes.data] == [1]
    assert reduce_sum.keepdim.value.data != 0
    assert len(broadcasts) == 2
    assert all(broadcast.result.type == mem_type for broadcast in broadcasts)
    assert exp_op.result.type == mem_type
    assert div_op.result.type == mem_type


def _case_2_negative_axis() -> None:
    print("[CASE-2] negative axis must be normalized before reduce ops")
    mem_type = _make_memory_type((2, 3, 4))
    module, func_op = _make_softmax_module(input_type=mem_type, axis=-1)

    print("[BEFORE]")
    print(module)
    DecomposeNnSoftmaxPass().run(module)
    module.verify()
    print("[AFTER]")
    print(module)

    reduce_max = next(op for op in _entry_ops(func_op) if isinstance(op, NnReduceMaxOp))
    reduce_sum = next(op for op in _entry_ops(func_op) if isinstance(op, NnReduceSumOp))
    assert [entry.value.data for entry in reduce_max.axes.data] == [2]
    assert [entry.value.data for entry in reduce_sum.axes.data] == [2]


def main() -> None:
    failures: list[tuple[str, BaseException]] = []
    run_case(failures, "CASE-1", _case_1_fixed_chain)
    run_case(failures, "CASE-2", _case_2_negative_axis)
    raise_if_failures("decompose-nn-softmax expectation", failures)


if __name__ == "__main__":
    main()

