"""Conv2d symbolic memory gen_kernel tests.


功能说明:
- 覆盖 `kernel/conv2d/inputs_dynamic_tile_dynamic.py` 的符号 memory 编译形态。
- 覆盖两条 static conv2d demo 的固定 seed 具体 static shape 编译形态。
- 验证 `run_lowering_demo(...)` 通过公开 `mlir_gen -> lowering -> gen_kernel` 链路生成动态 memory IR/source。

API 列表:
- 无（pytest 文件，不承载公开 API）

使用示例:
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/kernel/test_conv2d_symbolic_memory_genkernel.py`

关联文件:
- 功能实现: `kernel/conv2d/inputs_dynamic_tile_dynamic.py`
- 功能实现: `kernel/conv2d/inputs_static_tile_dynamic.py`
- 功能实现: `kernel/conv2d/inputs_static_tile_static.py`
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
from kernel.conv2d.inputs_static_tile_dynamic import conv2d_inputs_static_tile_dynamic_kernel
from kernel.conv2d.inputs_static_tile_static import conv2d_inputs_static_tile_static_kernel
from kernel.runner import run_lowering_demo
from kernel_gen.symbol_variable.memory import Memory
from kernel_gen.symbol_variable.symbol_dim import SymbolDim
from kernel_gen.symbol_variable.type import NumericType

Conv2dCompileArg: TypeAlias = "Memory | SymbolDim"
STATIC_OUTPUT_MEMORY = "!nn.memory<[#symbol.expr<11>, #symbol.expr<2>, #symbol.expr<258>, #symbol.expr<262>]"
STATIC_INPUT_MEMORY = "!nn.memory<[#symbol.expr<11>, #symbol.expr<28>, #symbol.expr<260>, #symbol.expr<264>]"
STATIC_WEIGHT_MEMORY = "!nn.memory<[#symbol.expr<2>, #symbol.expr<28>, #symbol.expr<3>, #symbol.expr<3>]"
SEMANTIC_OUTPUT_MEMORY = (
    "!nn.memory<[#symbol.expr<B>, #symbol.expr<C>, #symbol.expr<-KH + XH + 1>, #symbol.expr<-KW + XW + 1>]"
)
SEMANTIC_OUTPUT_PREFIX = "!nn.memory<[#symbol.expr<B>, #symbol.expr<C>,"
SEMANTIC_INPUT_MEMORY = "!nn.memory<[#symbol.expr<B>, #symbol.expr<N>, #symbol.expr<XH>, #symbol.expr<XW>]"
SEMANTIC_WEIGHT_MEMORY = "!nn.memory<[#symbol.expr<C>, #symbol.expr<N>, #symbol.expr<KH>, #symbol.expr<KW>]"
SEMANTIC_RUNTIME_SYMBOLS = ("SH", "SW", "DH", "DW", "PT", "PB", "PL", "PR", "TF", "TC", "TN", "THO", "TWO")


def _symbolic_conv2d_compile_args() -> tuple[Conv2dCompileArg, ...]:
    """构造测试用符号 memory 编译参数。


    功能说明:
    - 用 conv2d 语义化符号名表达 output/input/weight memory 的编译期动态形状。
    - output 空间维使用 stride/dilation/padding 的完整符号表达式。
    - 标量参数均使用 runtime `SymbolDim`，锁定公开 scalar real args 合同。

    使用示例:
    - `_symbolic_conv2d_compile_args()`
    """

    xh_dim = SymbolDim("XH")
    xw_dim = SymbolDim("XW")
    kh_dim = SymbolDim("KH")
    kw_dim = SymbolDim("KW")
    sh_dim = SymbolDim("SH")
    sw_dim = SymbolDim("SW")
    dh_dim = SymbolDim("DH")
    dw_dim = SymbolDim("DW")
    pt_dim = SymbolDim("PT")
    pb_dim = SymbolDim("PB")
    pl_dim = SymbolDim("PL")
    pr_dim = SymbolDim("PR")
    tf_dim = SymbolDim("TF")
    tc_dim = SymbolDim("TC")
    tn_dim = SymbolDim("TN")
    tho_dim = SymbolDim("THO")
    two_dim = SymbolDim("TWO")
    output_h_dim = ((xh_dim + pt_dim + pb_dim - dh_dim * (kh_dim - 1) - 1) // sh_dim) + 1
    output_w_dim = ((xw_dim + pl_dim + pr_dim - dw_dim * (kw_dim - 1) - 1) // sw_dim) + 1

    return (
        Memory(["B", "C", output_h_dim, output_w_dim], NumericType.Float32),
        Memory(["B", "N", "XH", "XW"], NumericType.Float32),
        Memory(["C", "N", "KH", "KW"], NumericType.Float32),
        sh_dim,
        sw_dim,
        dh_dim,
        dw_dim,
        pt_dim,
        pb_dim,
        pl_dim,
        pr_dim,
        tf_dim,
        tc_dim,
        tn_dim,
        tho_dim,
        two_dim,
    )


def _seeded_static_conv2d_compile_args() -> tuple[Memory, Memory, Memory]:
    """构造测试用固定 seed static memory 编译参数。


    功能说明:
    - output/input/weight 均使用本计划固定 seed 生成并固化的具体数字 shape。
    - 只服务本 pytest 文件，不新增产品公开 API。

    使用示例:
    - `_seeded_static_conv2d_compile_args()`
    """

    return (
        Memory([11, 2, 258, 262], NumericType.Float32),
        Memory([11, 28, 260, 264], NumericType.Float32),
        Memory([2, 28, 3, 3], NumericType.Float32),
    )


# TC-KERNEL-CONV2D-SYMBOLIC-MEMORY-001
# 功能说明: 验证动态输入 demo 的 gen_kernel 编译参数使用语义化符号 Memory shape。
# 测试目的: 锁定 lowered IR/source 不回退为旧 s1/s2 匿名 shape 或运行期静态 shape，确保 demo 名称中的 dynamic 真实体现在编译形态。
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

    assert SEMANTIC_OUTPUT_PREFIX in module_text
    assert SEMANTIC_INPUT_MEMORY in module_text
    assert SEMANTIC_WEIGHT_MEMORY in module_text
    for symbol_name in SEMANTIC_RUNTIME_SYMBOLS:
        assert symbol_name in module_text
    assert "arch.get_dynamic_memory" in module_text
    assert "dma.view" in module_text
    assert "dma.subview" not in module_text
    assert "dma.alloc" not in module_text
    assert "allalloc" not in module_text
    assert "!nn.memory<[#symbol.expr<s1>, #symbol.expr<s2>, #symbol.expr<s3>, #symbol.expr<s4>]" not in module_text
    assert "!nn.memory<[#symbol.expr<s1>, #symbol.expr<s5>, #symbol.expr<s6>, #symbol.expr<s7>]" not in module_text
    assert "!nn.memory<[#symbol.expr<s2>, #symbol.expr<s5>, #symbol.expr<3>, #symbol.expr<3>]" not in module_text
    assert "!nn.memory<[#symbol.expr<11>, #symbol.expr<4>, #symbol.expr<258>, #symbol.expr<262>]" not in module_text
    assert "!nn.memory<[#symbol.expr<11>, #symbol.expr<30>, #symbol.expr<260>, #symbol.expr<264>]" not in module_text
    assert "!nn.memory<[#symbol.expr<4>, #symbol.expr<30>, #symbol.expr<3>, #symbol.expr<3>]" not in module_text
    assert "arg1.get_shape(2)" in source
    assert "arg1.get_shape(3)" in source
    assert "npu_demo::get_dynamic_memory<TSM>()" in source
    assert ".view<float>(Vector{" in source
    assert "alloc<TSM" not in source
    assert "S_INT c_6 = 258" not in source


# TC-KERNEL-CONV2D-SYMBOLIC-MEMORY-002
# 功能说明: 验证静态输入、动态 tile demo 的 lowered IR 保持固定 seed 具体 static shape。
# 测试目的: 锁定 static demo 不回退为默认 12/32/256/256 形状，也不误变为 dynamic 符号 shape。
# 使用示例: pytest -q test/kernel/test_conv2d_symbolic_memory_genkernel.py -k static_tile_dynamic
# 对应功能实现文件路径: kernel/conv2d/inputs_static_tile_dynamic.py
# 对应 spec 文件路径: spec/kernel/runner.md
# 对应测试文件路径: test/kernel/test_conv2d_symbolic_memory_genkernel.py
def test_inputs_static_tile_dynamic_gen_kernel_keeps_seeded_static_shapes() -> None:
    module, _source = run_lowering_demo(
        "test_conv2d/inputs_static_tile_dynamic_seeded_static_memory",
        conv2d_inputs_static_tile_dynamic_kernel,
        *_seeded_static_conv2d_compile_args(),
        2,
        2,
        1,
        1,
        7,
    )
    module_text = str(module)

    assert STATIC_OUTPUT_MEMORY in module_text
    assert STATIC_INPUT_MEMORY in module_text
    assert STATIC_WEIGHT_MEMORY in module_text
    assert "!nn.memory<[#symbol.expr<12>, #symbol.expr<4>, #symbol.expr<254>, #symbol.expr<254>]" not in module_text
    assert "!nn.memory<[#symbol.expr<12>, #symbol.expr<32>, #symbol.expr<256>, #symbol.expr<256>]" not in module_text
    assert "!nn.memory<[#symbol.expr<4>, #symbol.expr<32>, #symbol.expr<3>, #symbol.expr<3>]" not in module_text
    assert SEMANTIC_OUTPUT_MEMORY not in module_text
    assert SEMANTIC_INPUT_MEMORY not in module_text
    assert SEMANTIC_WEIGHT_MEMORY not in module_text
    assert "!nn.memory<[#symbol.expr<s1>" not in module_text


# TC-KERNEL-CONV2D-SYMBOLIC-MEMORY-003
# 功能说明: 验证静态输入、静态 tile demo 的 lowered IR 保持固定 seed 具体 static shape。
# 测试目的: 锁定 static demo 不回退为默认 12/32/256/256 形状，也不误变为 dynamic 符号 shape。
# 使用示例: pytest -q test/kernel/test_conv2d_symbolic_memory_genkernel.py -k static_tile_static
# 对应功能实现文件路径: kernel/conv2d/inputs_static_tile_static.py
# 对应 spec 文件路径: spec/kernel/runner.md
# 对应测试文件路径: test/kernel/test_conv2d_symbolic_memory_genkernel.py
def test_inputs_static_tile_static_gen_kernel_keeps_seeded_static_shapes() -> None:
    module, source = run_lowering_demo(
        "test_conv2d/inputs_static_tile_static_seeded_static_memory",
        conv2d_inputs_static_tile_static_kernel,
        *_seeded_static_conv2d_compile_args(),
    )
    module_text = str(module)

    assert STATIC_OUTPUT_MEMORY in module_text
    assert STATIC_INPUT_MEMORY in module_text
    assert STATIC_WEIGHT_MEMORY in module_text
    assert "!nn.memory<[#symbol.expr<12>, #symbol.expr<4>, #symbol.expr<254>, #symbol.expr<254>]" not in module_text
    assert "!nn.memory<[#symbol.expr<12>, #symbol.expr<32>, #symbol.expr<256>, #symbol.expr<256>]" not in module_text
    assert "!nn.memory<[#symbol.expr<4>, #symbol.expr<32>, #symbol.expr<3>, #symbol.expr<3>]" not in module_text
    assert SEMANTIC_OUTPUT_MEMORY not in module_text
    assert SEMANTIC_INPUT_MEMORY not in module_text
    assert SEMANTIC_WEIGHT_MEMORY not in module_text
    assert "!nn.memory<[#symbol.expr<s1>" not in module_text
    assert "? -" not in module_text
    assert "? -" not in source
