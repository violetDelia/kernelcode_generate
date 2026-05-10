"""Conv2d dynamic symbol parameter contract tests.

功能说明:
- 锁定 `kernel/conv2d/inputs_dynamic_tile_dynamic.py` 的 stride、dilation、padding 与 tile 参数均以 runtime `SymbolDim` 进入 lowering。
- 通过公开 `run_lowering_demo(...)` 验证 dynamic conv2d 输出 shape 使用完整 stride/dilation/padding 公式。

API 列表:
- 无（pytest 文件，不承载公开 API）

使用示例:
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/kernel/test_conv2d_dynamic_symbol_params.py`

关联文件:
- 功能实现: `kernel/conv2d/inputs_dynamic_tile_dynamic.py`
- 公共运行器: `kernel/runner.py`
- spec: `spec/kernel/runner.md`
- test: `test/kernel/test_conv2d_dynamic_symbol_params.py`
"""

from __future__ import annotations

from typing import TypeAlias

from kernel.conv2d.inputs_dynamic_tile_dynamic import conv2d_inputs_dynamic_tile_dynamic_kernel
from kernel.runner import run_lowering_demo
from kernel_gen.symbol_variable.memory import Memory
from kernel_gen.symbol_variable.symbol_dim import SymbolDim
from kernel_gen.symbol_variable.type import NumericType

Conv2dCompileArg: TypeAlias = "Memory | SymbolDim"
SEMANTIC_OUTPUT_PREFIX = "!nn.memory<[#symbol.expr<B>, #symbol.expr<C>,"
SEMANTIC_INPUT_MEMORY = "!nn.memory<[#symbol.expr<B>, #symbol.expr<N>, #symbol.expr<XH>, #symbol.expr<XW>]"
SEMANTIC_WEIGHT_MEMORY = "!nn.memory<[#symbol.expr<C>, #symbol.expr<N>, #symbol.expr<KH>, #symbol.expr<KW>]"
RUNTIME_SYMBOLS = ("SH", "SW", "DH", "DW", "PT", "PB", "PL", "PR", "TF", "TC", "TN", "THO", "TWO")


def _dynamic_conv2d_compile_args() -> tuple[Conv2dCompileArg, ...]:
    """构造 dynamic conv2d 的公开编译参数。

    功能说明:
    - 使用 `Memory` 与 `SymbolDim` 公开 API 表达 conv2d 的输入、权重、输出和 runtime scalar 实参。
    - 输出空间维度固定使用完整非对称 padding、dilation 与 stride 公式。

    使用示例:
    - args = _dynamic_conv2d_compile_args()
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


def test_conv2d_dynamic_symbol_params_survive_lowering_and_codegen() -> None:
    """验证 dynamic conv2d runtime scalar 参数在 IR/source 中保留。

    功能说明:
    - 通过公开 `run_lowering_demo(...)` 执行 mlir_gen、默认 npu-demo-lowering 和 gen_kernel。
    - 断言 stride/dilation/padding/tile 参数不会回退为旧匿名 `s1` 或静态常量。

    使用示例:
    - `pytest -q test/kernel/test_conv2d_dynamic_symbol_params.py`
    """

    module, source = run_lowering_demo(
        "test_conv2d/dynamic_symbol_params",
        conv2d_inputs_dynamic_tile_dynamic_kernel,
        *_dynamic_conv2d_compile_args(),
    )
    module_text = str(module)

    assert SEMANTIC_OUTPUT_PREFIX in module_text
    assert SEMANTIC_INPUT_MEMORY in module_text
    assert SEMANTIC_WEIGHT_MEMORY in module_text
    for symbol_name in RUNTIME_SYMBOLS:
        assert symbol_name in module_text
    assert "arch.get_dynamic_memory" in module_text
    assert "dma.view" in module_text
    assert "dma.subview" not in module_text
    assert "dma.alloc" not in module_text
    assert "allalloc" not in module_text
    assert "!nn.memory<[#symbol.expr<s1>" not in module_text
    assert "!nn.memory<[#symbol.expr<11>" not in module_text
    assert "arg1.get_shape(2)" in source
    assert "arg1.get_shape(3)" in source
    assert "npu_demo::get_dynamic_memory<TSM>()" in source
    assert ".view<float>(Vector{" in source
    assert "alloc<TSM" not in source
    assert "S_INT c_6 = 258" not in source
