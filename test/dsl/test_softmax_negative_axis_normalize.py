"""softmax negative-axis normalization tests.

创建者: 金铲铲大作战
最后一次更改: 金铲铲大作战

功能说明:
- 验证 softmax helper 的默认轴与负轴在 build_func_op lowering 中会规整为正轴。
- 锁定 S4 helper call lowering 不再把 `axis=-1` 直接透传到 `nn.softmax`。

使用示例:
- pytest -q test/dsl/test_softmax_negative_axis_normalize.py

关联文件:
- 功能实现: kernel_gen/dsl/mlir_gen/emit/core.py
- test: test/dsl/test_softmax_negative_axis_normalize.py
- 功能实现: kernel_gen/dsl/mlir_gen/emit/core.py
"""

from __future__ import annotations

import sys
from pathlib import Path

from xdsl.dialects import func

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from kernel_gen.dialect.nn import NnSoftmaxOp
from kernel_gen.dsl.mlir_gen import build_func_op
from kernel_gen.operation.nn import softmax
from kernel_gen.symbol_variable.memory import Memory, MemorySpace
from kernel_gen.symbol_variable.type import NumericType


def test_build_func_op_normalizes_softmax_default_axis_to_last_dimension() -> None:
    source = Memory([2, 3], NumericType.Float32, space=MemorySpace.GM)

    def softmax_kernel(src: "Tensor[f32, 2, 3]") -> "Tensor[f32, 2, 3]":
        return softmax(src)

    func_op = build_func_op(softmax_kernel, source)
    softmax_ops = [op for op in func_op.body.block.ops if isinstance(op, NnSoftmaxOp)]
    return_ops = [op for op in func_op.body.block.ops if isinstance(op, func.ReturnOp)]

    assert len(softmax_ops) == 1
    assert len(return_ops) == 1
    assert softmax_ops[0].axis.value.data == 1
    assert return_ops[0].arguments[0].type == softmax_ops[0].result.type


def test_build_func_op_normalizes_softmax_negative_axis_to_positive_axis() -> None:
    source = Memory([2, 3, 4], NumericType.Float32, space=MemorySpace.GM)

    def softmax_kernel(src: "Tensor[f32, 2, 3, 4]") -> "Tensor[f32, 2, 3, 4]":
        return softmax(src, axis=-1)

    func_op = build_func_op(softmax_kernel, source)
    softmax_ops = [op for op in func_op.body.block.ops if isinstance(op, NnSoftmaxOp)]

    assert len(softmax_ops) == 1
    assert softmax_ops[0].axis.value.data == 2
