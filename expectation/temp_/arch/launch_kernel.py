"""arch.launch_kernel expectation.

创建者: 榕
最后一次更改: 榕

功能说明:
- 使用统一 expectation 结构描述 `arch.launch_kernel` 的 DSL 调用方式。
- 验证 `build_func_op` 可将启动描述 lowering 为 `arch.launch_kernel`。

使用示例:
- python expectation/temp_/arch/launch_kernel.py

关联文件:
- spec: spec/dialect/arch.md
- test: test/dialect/test_arch_dialect.py
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

from expectation.utils.compare import assert_dynamic_symbol_int, assert_static_symbol_int
from expectation.utils.random import get_random_alpha_string, get_random_non_zero_int
from kernel_gen.dialect.arch import ArchLaunchKernelOp
from kernel_gen.dsl.mlir_gen import build_func_op
from kernel_gen.symbol_variable.symbol_dim import SymbolDim

BLOCK_NAME = get_random_alpha_string().upper()
while BLOCK_NAME in {"THREAD", "SUBTHREAD"}:
    BLOCK_NAME = get_random_alpha_string().upper()

BLOCK = SymbolDim(BLOCK_NAME)
THREAD = get_random_non_zero_int(1, 16)
SUBTHREAD = get_random_non_zero_int(1, 4)


def launch_kernel_func(block: int, thread: int, subthread: int) -> None:
    launch_kernel("generated_kernel", block, thread, subthread)


func_op = build_func_op(launch_kernel_func, BLOCK, THREAD, SUBTHREAD)
assert isinstance(func_op, FuncOp)

assert_dynamic_symbol_int(func_op.args[0].type, BLOCK)
assert_static_symbol_int(func_op.args[1].type, THREAD)
assert_static_symbol_int(func_op.args[2].type, SUBTHREAD)

launch_ops = [op for op in func_op.body.block.ops if isinstance(op, ArchLaunchKernelOp)]
return_ops = [op for op in func_op.body.block.ops if isinstance(op, ReturnOp)]

assert len(launch_ops) == 1
assert launch_ops[0].kernel_name.data == "generated_kernel"
assert len(return_ops) == 1
