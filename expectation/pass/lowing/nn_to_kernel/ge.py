"""nn_to_kernel expectation.

创建者: 榕
最后一次更改: 榕

功能说明:
- 验证 `Memory >= Memory` 可通过 `build_func_op` 生成 `func op`，且函数体包含 `nn.ge`。
- 验证对该 `func op` 运行 `LowerNnToKernelPass` 后，`nn.ge` 被 lower 为 `kernel.ge`，并插入 `dma.alloc`。

使用示例:
- python expectation/pass/lowing/nn_to_kernel/ge.py

关联文件:
- spec: spec/pass/lowing/nn_to_kernel.md
- test: test/pass/test_lowing_nn_to_kernel.py
- 功能实现: kernel_gen/pass/lowing/nn_to_kernel.py
"""
# Case 列表:
# - Case-1: 参数合法：两个同 shape Memory 先生成 nn.ge，再执行 lowering，验证替换为 kernel.ge 并插入 dma.alloc。

from __future__ import annotations

from pathlib import Path
import sys

from xdsl.dialects.builtin import ModuleOp

REPO_ROOT = Path(__file__).resolve().parents[4]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from kernel_gen.dialect.dma import DmaAllocOp
from kernel_gen.dialect.nn import NnGeOp
from kernel_gen.dsl.mlir_gen import build_func_op
from kernel_gen.passes.lowing.nn_to_kernel import LowerNnToKernelPass
from kernel_gen.symbol_variable.memory import Memory, MemorySpace
from kernel_gen.symbol_variable.type import NumericType


def ge_memory(
    lhs: "Tensor[f32, 2, 2]",
    rhs: "Tensor[f32, 2, 2]",
) -> "Tensor[i1, 2, 2]":
    return lhs >= rhs


lhs_memory = Memory([2, 2], NumericType.Float32, space=MemorySpace.GM)
rhs_memory = Memory([2, 2], NumericType.Float32, space=MemorySpace.GM)

print("[CASE-1] 参数合法：两个同 shape Memory 先生成 nn.ge，再执行 lowering，验证替换为 kernel.ge 并插入 dma.alloc。")
func_op = build_func_op(ge_memory, lhs_memory, rhs_memory)
print(func_op)

before_ops = list(func_op.body.block.ops)
assert any(isinstance(op, NnGeOp) for op in before_ops)

module = ModuleOp([func_op])
LowerNnToKernelPass().run(module)

after_ops = list(func_op.body.block.ops)
assert any(op.name == "kernel.ge" for op in after_ops)
assert any(isinstance(op, DmaAllocOp) for op in after_ops)
assert not any(op.name.startswith("nn.") for op in after_ops)
