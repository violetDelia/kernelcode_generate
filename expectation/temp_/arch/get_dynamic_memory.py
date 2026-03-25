"""arch.get_dynamic_memory expectation.

创建者: 榕
最后一次更改: 金铲铲大作战

功能说明:
- 使用统一 expectation 结构描述 `arch.get_dynamic_memory` 的 DSL 调用方式。
- 验证 `build_func_op` 可将动态片上内存入口 lowering 为 `arch.get_dynamic_memory`。

使用示例:
- python expectation/temp_/arch/get_dynamic_memory.py

关联文件:
- spec: spec/dsl/ast.md, spec/dsl/emit_mlir.md, spec/dsl/mlir_gen.md
- test: test/dsl/test_ast_visitor.py
- 功能实现: kernel_gen/dsl/ast.py, kernel_gen/dsl/emit_mlir.py, kernel_gen/dsl/mlir_gen.py
"""

from pathlib import Path
import sys

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path = [
    search_path
    for search_path in sys.path
    if Path(search_path or ".").resolve() != SCRIPT_DIR
]

REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from xdsl.dialects.builtin import IntAttr, StringAttr, i8
from xdsl.dialects.func import FuncOp, ReturnOp

from kernel_gen.dialect.arch import ArchGetDynamicMemoryOp
from kernel_gen.dialect.nn import NnMemoryType, NnMemorySpaceAttr
from kernel_gen.dsl.mlir_gen import build_func_op
from kernel_gen.symbol_variable.memory import MemorySpace


def get_dynamic_memory_kernel() -> "Tensor[i8, ?]":
    return get_dynamic_memory(MemorySpace.SM)


func_op = build_func_op(get_dynamic_memory_kernel)
assert isinstance(func_op, FuncOp)

memory_ops = [op for op in func_op.body.block.ops if isinstance(op, ArchGetDynamicMemoryOp)]
return_ops = [op for op in func_op.body.block.ops if isinstance(op, ReturnOp)]

assert len(memory_ops) == 1
assert isinstance(memory_ops[0].result.type, NnMemoryType)
assert memory_ops[0].result.type.shape.data[0] == StringAttr("?")
assert memory_ops[0].result.type.stride.data[0] == IntAttr(1)
assert memory_ops[0].result.type.element_type == i8
assert memory_ops[0].result.type.space == NnMemorySpaceAttr.from_name("shared")
assert len(return_ops) == 1
assert return_ops[0].arguments[0].type == memory_ops[0].result.type
