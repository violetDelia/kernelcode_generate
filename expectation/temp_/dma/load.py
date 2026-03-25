"""DMA load expectation.

创建者: 榕
最后一次更改: 榕

功能说明:
- 使用统一 expectation 结构描述 `load(...)` 的 DSL 调用方式。
- 参数与 Memory shape 使用随机整数，便于覆盖不同输入规模。

使用示例:
- python expectation/temp/dma/load.py

关联文件:
- spec: spec/dsl/mlir_gen.md
- test: test/dsl/test_ast_visitor.py
- 功能实现: kernel_gen/dsl/mlir_gen.py
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

from xdsl.dialects.func import FuncOp, ReturnOp

from expectation.utils.random import get_random_int, get_random_non_zero_int
from kernel_gen.dialect.dma import DmaLoadOp
from kernel_gen.dsl.mlir_gen import build_func_op
from kernel_gen.operation.dma import load
from kernel_gen.symbol_variable.memory import Memory, MemorySpace
from kernel_gen.symbol_variable.type import NumericType

SOURCE_ROWS = get_random_non_zero_int(4, 8)
SOURCE_COLS = get_random_non_zero_int(4, 8)
TILE_ROWS = get_random_non_zero_int(1, SOURCE_ROWS)
TILE_COLS = get_random_non_zero_int(1, SOURCE_COLS)
OFFSET_ROW = get_random_int(0, SOURCE_ROWS - TILE_ROWS)
OFFSET_COL = get_random_int(0, SOURCE_COLS - TILE_COLS)

SOURCE_MEMORY = Memory([SOURCE_ROWS, SOURCE_COLS], NumericType.Float32, space=MemorySpace.GM)


def load_kernel(src: f"Tensor[f32, {SOURCE_ROWS}, {SOURCE_COLS}]") -> f"Tensor[f32, {TILE_ROWS}, {TILE_COLS}]":
    return load(src, [OFFSET_ROW, OFFSET_COL], [TILE_ROWS, TILE_COLS], [1, 1], MemorySpace.SM)


func_op = build_func_op(load_kernel, SOURCE_MEMORY)
assert isinstance(func_op, FuncOp)

load_ops = [op for op in func_op.body.block.ops if isinstance(op, DmaLoadOp)]
return_ops = [op for op in func_op.body.block.ops if isinstance(op, ReturnOp)]

assert len(load_ops) == 1
assert len(return_ops) == 1
