"""DMA deslice expectation.

创建者: 榕
最后一次更改: 朽木露琪亚

功能说明:
- 使用统一 expectation 结构描述 `deslice(...)` 的 DSL 调用方式。
- 采用固定尺寸，避免解析阶段拒绝函数体外部常量引用。

使用示例:
- python expectation/dsl/mlir_gen/dialect/dma/deslice.py

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

REPO_ROOT = None
for candidate in Path(__file__).resolve().parents:
    if (candidate / "kernel_gen").exists():
        REPO_ROOT = candidate
        break
if REPO_ROOT is None:
    raise RuntimeError("Failed to locate repository root for expectation script.")
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from xdsl.dialects.func import FuncOp, ReturnOp

from kernel_gen.dialect.dma import DmaDesliceOp, DmaStoreOp
from kernel_gen.dsl.mlir_gen import build_func_op
from kernel_gen.operation.dma import deslice
from kernel_gen.symbol_variable.memory import Memory, MemorySpace
from kernel_gen.symbol_variable.type import NumericType

TARGET_ROWS = 4
TARGET_COLS = 4
TILE_ROWS = 2
TILE_COLS = 2

SOURCE_MEMORY = Memory([TILE_ROWS, TILE_COLS], NumericType.Float32, space=MemorySpace.LM)
TARGET_MEMORY = Memory([TARGET_ROWS, TARGET_COLS], NumericType.Float32, space=MemorySpace.GM)


def deslice_kernel(
    tile: f"Tensor[f32, {TILE_ROWS}, {TILE_COLS}]",
    target: f"Tensor[f32, {TARGET_ROWS}, {TARGET_COLS}]",
):
    deslice(tile, target, [1, 1], [2, 2], [1, 1])


func_op = build_func_op(deslice_kernel, SOURCE_MEMORY, TARGET_MEMORY)
assert isinstance(func_op, FuncOp)

deslice_ops = [op for op in func_op.body.block.ops if isinstance(op, DmaDesliceOp)]
store_ops = [op for op in func_op.body.block.ops if isinstance(op, DmaStoreOp)]
return_ops = [op for op in func_op.body.block.ops if isinstance(op, ReturnOp)]

assert len(deslice_ops) == 1
assert len(store_ops) == 0
assert len(return_ops) == 1
assert len(return_ops[0].arguments) == 0
