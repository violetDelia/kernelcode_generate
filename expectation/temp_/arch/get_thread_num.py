"""arch.get_thread_num expectation.

创建者: 榕
最后一次更改: 榕

功能说明:
- 使用统一 expectation 结构描述 `arch.get_thread_num` 的 DSL 调用方式。
- 验证 `build_func_op` 可将无参函数 lowering 为 `arch.get_thread_num`。

使用示例:
- python expectation/temp_/arch/get_thread_num.py

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

from expectation.utils.compare import assert_dynamic_symbol_int
from kernel_gen.dialect.arch import ArchGetThreadNumOp
from kernel_gen.dsl.mlir_gen import build_func_op


def get_thread_num_kernel() -> int:
    return get_thread_num()


func_op = build_func_op(get_thread_num_kernel)
assert isinstance(func_op, FuncOp)

query_ops = [op for op in func_op.body.block.ops if isinstance(op, ArchGetThreadNumOp)]
return_ops = [op for op in func_op.body.block.ops if isinstance(op, ReturnOp)]

assert len(query_ops) == 1
assert_dynamic_symbol_int(query_ops[0].result.type, "thread_num")
assert len(return_ops) == 1
assert_dynamic_symbol_int(return_ops[0].arguments[0].type, "thread_num")
