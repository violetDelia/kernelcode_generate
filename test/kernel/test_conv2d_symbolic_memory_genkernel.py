"""Conv2d symbolic memory gen_kernel tests.


功能说明:
- 覆盖 `kernel/conv2d/inputs_dynamic_tile_dynamic.py` 的符号 memory 编译形态。
- 验证 `run_lowering_demo(...)` 通过公开 `mlir_gen -> lowering -> gen_kernel` 链路生成动态 memory IR/source。

API 列表:
- 无（pytest 文件，不承载公开 API）

使用示例:
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/kernel/test_conv2d_symbolic_memory_genkernel.py`

关联文件:
- 功能实现: `kernel/conv2d/inputs_dynamic_tile_dynamic.py`
- 公共运行器: `kernel/runner.py`
- 测试文件: `test/kernel/test_conv2d_symbolic_memory_genkernel.py`
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import TypeAlias

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from kernel.conv2d.inputs_dynamic_tile_dynamic import conv2d_inputs_dynamic_tile_dynamic_kernel
from kernel.runner import run_lowering_demo
from kernel_gen.symbol_variable.memory import Memory
from kernel_gen.symbol_variable.type import NumericType

Conv2dCompileArg: TypeAlias = "Memory | int"


def _symbolic_conv2d_compile_args() -> tuple[Conv2dCompileArg, ...]:
    """构造测试用符号 memory 编译参数。


    功能说明:
    - 用 `s1/s2/...` 表达 output/input/weight memory 的编译期动态形状。
    - 标量参数保持本 demo 的固定真实值，避免扩大到未确认的符号 scalar 合同。

    使用示例:
    - `_symbolic_conv2d_compile_args()`
    """

    return (
        Memory(["s1", "s2", "s3", "s4"], NumericType.Float32),
        Memory(["s1", "s5", "s6", "s7"], NumericType.Float32),
        Memory(["s2", "s5", 3, 3], NumericType.Float32),
        1,
        1,
        1,
        1,
        0,
        0,
        0,
        0,
        2,
        16,
        1,
        64,
        64,
    )


# TC-KERNEL-CONV2D-SYMBOLIC-MEMORY-001
# 功能说明: 验证动态输入 demo 的 gen_kernel 编译参数使用符号 Memory shape。
# 测试目的: 锁定 lowered IR/source 不回退为运行期静态 shape，确保 demo 名称中的 dynamic 真实体现在编译形态。
# 使用示例: pytest -q test/kernel/test_conv2d_symbolic_memory_genkernel.py -k symbolic_memory
# 对应功能实现文件路径: kernel/conv2d/inputs_dynamic_tile_dynamic.py
# 对应 spec 文件路径: spec/kernel/runner.md
# 对应测试文件路径: test/kernel/test_conv2d_symbolic_memory_genkernel.py
def test_inputs_dynamic_tile_dynamic_gen_kernel_keeps_symbolic_memory_shapes() -> None:
    module, source = run_lowering_demo(
        "test_conv2d/inputs_dynamic_tile_dynamic_symbolic_memory",
        conv2d_inputs_dynamic_tile_dynamic_kernel,
        *_symbolic_conv2d_compile_args(),
    )
    module_text = str(module)

    assert "!nn.memory<[s1, s2, s3, s4]" in module_text
    assert "!nn.memory<[s1, s5, s6, s7]" in module_text
    assert "!nn.memory<[s2, s5, 3, 3]" in module_text
    assert "!nn.memory<[11, 4, 258, 262]" not in module_text
    assert "!nn.memory<[11, 30, 260, 264]" not in module_text
    assert "!nn.memory<[4, 30, 3, 3]" not in module_text
    assert "arg1.get_shape(2)" in source
    assert "arg1.get_shape(3)" in source
    assert "S_INT c_6 = 258" not in source
