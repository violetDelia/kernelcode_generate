"""DMA cast expectation.

创建者: 榕
最后一次更改: 榕

功能说明:
- 使用统一 expectation 结构描述 `cast(...)` 的 DSL 调用方式。
- 参数与 Memory shape 使用随机整数，便于覆盖不同输入规模。

使用示例:
- python expectation/temp_/dma/cast.py

关联文件:
- spec: spec/dsl/emit_mlir.md, spec/dsl/mlir_gen.md
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

REPO_ROOT = Path(__file__).resolve().parents[5]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from xdsl.dialects.func import FuncOp, ReturnOp

from expectation.utils.compare import assert_memory
from expectation.utils.random import get_random_non_zero_int
from kernel_gen.dialect.dma import DmaCastOp
from kernel_gen.dsl.mlir_gen import build_func_op
from kernel_gen.operation.dma import cast
from kernel_gen.symbol_variable.memory import Memory, MemorySpace
from kernel_gen.symbol_variable.type import NumericType

SOURCE_ROWS = get_random_non_zero_int(1, 8)
SOURCE_COLS = get_random_non_zero_int(1, 8)
SOURCE_MEMORY = Memory([SOURCE_ROWS, SOURCE_COLS], NumericType.Float32, space=MemorySpace.GM)

DEFAULT_CAST_MEMORY = cast(SOURCE_MEMORY, NumericType.Float16)
OVERRIDE_CAST_MEMORY = cast(SOURCE_MEMORY, NumericType.Float16, memoryspace=MemorySpace.SM)


def cast_default_space_kernel(
    src: f"Tensor[f32, {SOURCE_ROWS}, {SOURCE_COLS}]",
) -> f"Tensor[f16, {SOURCE_ROWS}, {SOURCE_COLS}]":
    return cast(src, NumericType.Float16)


def cast_override_space_kernel(
    src: f"Tensor[f32, {SOURCE_ROWS}, {SOURCE_COLS}]",
) -> f"Tensor[f16, {SOURCE_ROWS}, {SOURCE_COLS}]":
    return cast(src, NumericType.Float16, memoryspace=MemorySpace.SM)


default_space_func_op = build_func_op(cast_default_space_kernel, SOURCE_MEMORY)
assert isinstance(default_space_func_op, FuncOp)
assert_memory(default_space_func_op.args[0].type, SOURCE_MEMORY)
default_space_cast_ops = [op for op in default_space_func_op.body.block.ops if isinstance(op, DmaCastOp)]
default_space_return_ops = [op for op in default_space_func_op.body.block.ops if isinstance(op, ReturnOp)]
assert len(default_space_cast_ops) == 1
assert len(default_space_return_ops) == 1
assert_memory(default_space_cast_ops[0].result.type, DEFAULT_CAST_MEMORY)
assert_memory(default_space_return_ops[0].arguments[0].type, DEFAULT_CAST_MEMORY)

override_space_func_op = build_func_op(cast_override_space_kernel, SOURCE_MEMORY)
assert isinstance(override_space_func_op, FuncOp)
assert_memory(override_space_func_op.args[0].type, SOURCE_MEMORY)
override_space_cast_ops = [op for op in override_space_func_op.body.block.ops if isinstance(op, DmaCastOp)]
override_space_return_ops = [op for op in override_space_func_op.body.block.ops if isinstance(op, ReturnOp)]
assert len(override_space_cast_ops) == 1
assert len(override_space_return_ops) == 1
assert_memory(override_space_cast_ops[0].result.type, OVERRIDE_CAST_MEMORY)
assert_memory(override_space_return_ops[0].arguments[0].type, OVERRIDE_CAST_MEMORY)
