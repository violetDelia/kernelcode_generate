"""DMA reshape expectation.

创建者: 榕
最后一次更改: 金铲铲大作战

功能说明:
- 使用统一 expectation 结构描述 `reshape(...)` 的 DSL 调用方式。
- 参数与 Memory shape 使用随机整数，便于覆盖不同输入规模。

使用示例:
- python expectation/temp_/dma/reshape.py

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

REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from xdsl.dialects.func import FuncOp

from expectation.utils.random import get_random_non_zero_int
from kernel_gen.dialect.dma import DmaReshapeOp
from kernel_gen.dsl.mlir_gen import build_func_op
from kernel_gen.operation.dma import reshape
from kernel_gen.symbol_variable.memory import Memory, MemorySpace
from kernel_gen.symbol_variable.type import NumericType

SOURCE_ROWS = get_random_non_zero_int(1, 8)
SOURCE_COLS = get_random_non_zero_int(1, 8)
RESHAPE_ROWS = 1
RESHAPE_COLS = SOURCE_ROWS * SOURCE_COLS
SOURCE_MEMORY = Memory([SOURCE_ROWS, SOURCE_COLS], NumericType.Float32, space=MemorySpace.GM)


def reshape_kernel(src: f"Tensor[f32, {SOURCE_ROWS}, {SOURCE_COLS}]") -> f"Tensor[f32, {RESHAPE_ROWS}, {RESHAPE_COLS}]":
    return reshape(src, [RESHAPE_ROWS, RESHAPE_COLS])


func_op = build_func_op(reshape_kernel, SOURCE_MEMORY)
assert isinstance(func_op, FuncOp)

reshape_ops = [op for op in func_op.body.block.ops if isinstance(op, DmaReshapeOp)]
assert len(reshape_ops) == 1
