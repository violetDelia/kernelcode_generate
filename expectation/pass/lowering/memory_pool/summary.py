"""memory_pool summary expectation.

创建者: 金铲铲大作战
最后一次更改: 小李飞刀

功能说明:
- 输出 before/after IR 与 summary 文本。
- 校验直线路径池化改写的结构结果。

使用示例:
- PYTHONPATH=. python expectation/pass/lowering/memory_pool/summary.py

关联文件:
- spec: spec/pass/lowering/memory_pool.md
- test: test/pass/test_memory_pool.py
- 功能实现: kernel_gen/passes/lowering/memory_pool.py
"""

from __future__ import annotations

import sys
from pathlib import Path

from xdsl.dialects import func
from xdsl.dialects.builtin import ArrayAttr, FunctionType, IntAttr, ModuleOp, i32
from xdsl.dialects.test import TestOp as _TestOp
from xdsl.ir import Block, Region

REPO_ROOT = Path(__file__).resolve().parents[4]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from kernel_gen.dialect.dma import DmaAllocOp, DmaFreeOp, DmaReshapeOp, DmaViewOp
from kernel_gen.dialect.nn import NnMemorySpaceAttr, NnMemoryType
from kernel_gen.dialect.symbol import SymbolValueType
from kernel_gen.passes.lowering.memory_pool import MemoryPoolPass

space = NnMemorySpaceAttr.from_name("global")
mem_type = NnMemoryType(
    ArrayAttr([IntAttr(2), IntAttr(4)]),
    ArrayAttr([IntAttr(4), IntAttr(1)]),
    i32,
    space,
)

shape_op_a = _TestOp(result_types=[SymbolValueType.from_expr("2")])
shape_op_b = _TestOp(result_types=[SymbolValueType.from_expr("4")])
shape_operands = [shape_op_a.results[0], shape_op_b.results[0]]

alloc_a = DmaAllocOp(shape_operands, mem_type)
free_a = DmaFreeOp(alloc_a.result)
alloc_b = DmaAllocOp(shape_operands, mem_type)
free_b = DmaFreeOp(alloc_b.result)

block = Block()
block.add_ops([shape_op_a, shape_op_b, alloc_a, free_a, alloc_b, free_b, func.ReturnOp()])
func_op = func.FuncOp("main", FunctionType.from_lists([], []), Region(block))
module = ModuleOp([func_op])

print("before_ir:")
print(module)

pass_obj = MemoryPoolPass(rewrite=True)
pass_obj.run(module)
summary = pass_obj.get_summary("main")

print("summary_text:")
print(summary.to_text())

print("after_ir:")
print(module)

block = func_op.body.blocks[0]
alloc_ops = [op for op in block.ops if isinstance(op, DmaAllocOp)]
free_ops = [op for op in block.ops if isinstance(op, DmaFreeOp)]
view_ops = [op for op in block.ops if isinstance(op, DmaViewOp)]
reshape_ops = [op for op in block.ops if isinstance(op, DmaReshapeOp)]

assert len(alloc_ops) == 1
assert len(free_ops) == 1
assert len(view_ops) == 2
assert len(reshape_ops) == 2
