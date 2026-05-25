"""Flash attention symbolic memory/tile demo tests.

功能说明:
- 覆盖 `kernel/flash_attention` 三条目标 demo 的公开 kernel 函数与脚本入口。
- 锁定 static demo 保留固定 seed 随机生成并固化的具体 memory，dynamic demo 保留 `B/H/SL/D` 符号 memory。
- 锁定 static-dynamic 与 dynamic-dynamic demo 的 `BR/BC` tile 参数作为 runtime `SymbolDim` 进入 lowering。
- 锁定 Flash Attention 生成 `batch -> head -> query block -> key/value block` 四层循环并使用 online softmax 状态。

API 列表:
- 无（pytest 文件，不承载公开 API）

使用示例:
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/kernel/test_flash_attention_symbolic_memory_genkernel.py`

关联文件:
- 功能实现: `kernel/flash_attention/inputs_static_tile_static.py`
- 功能实现: `kernel/flash_attention/inputs_static_tile_dynamic.py`
- 功能实现: `kernel/flash_attention/inputs_dynamic_tile_dynamic.py`
- 公共运行器: `kernel/runner.py`
"""

from __future__ import annotations

import inspect
import os
from pathlib import Path
import re
import subprocess
import sys
from typing import TypeAlias

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from kernel.flash_attention.inputs_dynamic_tile_dynamic import flash_attention_inputs_dynamic_tile_dynamic_kernel
from kernel.flash_attention.inputs_static_tile_dynamic import flash_attention_inputs_static_tile_dynamic_kernel
from kernel.flash_attention.inputs_static_tile_static import flash_attention_inputs_static_tile_static_kernel
from kernel.runner import run_lowering_demo
from kernel_gen.symbol_variable.memory import Memory
from kernel_gen.symbol_variable.symbol_dim import SymbolDim
from kernel_gen.symbol_variable.type import NumericType

FlashCompileArg: TypeAlias = "Memory | SymbolDim"
STATIC_STATIC_FLASH_MEMORY = "!nn.memory<[#symbol.expr<2>, #symbol.expr<11>, #symbol.expr<389>, #symbol.expr<91>]"
STATIC_DYNAMIC_FLASH_MEMORY = "!nn.memory<[#symbol.expr<1>, #symbol.expr<8>, #symbol.expr<389>, #symbol.expr<98>]"
DYNAMIC_FLASH_MEMORY = "!nn.memory<[#symbol.expr<B>, #symbol.expr<H>, #symbol.expr<SL>, #symbol.expr<D>]"


def _assert_flash_source_uses_kernel_softmax(fn) -> None:
    """校验 flash attention demo 使用 kernel/dma out-first softmax 展开。

    功能说明:
    - 当前测试文件内 helper，只读取公开 demo 函数源码。
    - 防止主计算入口回退到 `nn.softmax` 或返回式 `nn.matmul`。

    使用示例:
    - `_assert_flash_source_uses_kernel_softmax(flash_attention_inputs_static_tile_static_kernel)`
    """

    function_source = inspect.getsource(fn)
    assert "kernel.matmul(" in function_source
    assert "kernel.reduce(" in function_source
    assert "kernel.binary_elewise(" in function_source
    assert "kernel.KernelBinaryElewiseKind.MAX" in function_source
    assert "broadcast(" in function_source
    assert "kernel.exp(" in function_source
    assert "kernel.truediv(" in function_source
    assert "m_state = alloc" in function_source
    assert "sum_state = alloc" in function_source
    assert "old_scale = alloc" in function_source
    assert "weighted_next = alloc" in function_source
    assert "softmax(" not in function_source
    assert "score = matmul(" not in function_source
    assert "weighted = matmul(" not in function_source
    assert "pair_tile" not in function_source
    assert "max_pair" not in function_source


def _assert_flash_source_uses_query_and_key_tile_loops(fn) -> None:
    """校验 flash attention demo 源码同时包含 query/key tile loop。

    功能说明:
    - 当前测试文件内 helper，只读取公开 demo 函数源码。
    - 防止 flash attention 回退为只按 `br` 分块、K/V 一次性全序列切入的单 loop 形态。

    使用示例:
    - `_assert_flash_source_uses_query_and_key_tile_loops(flash_attention_inputs_static_tile_dynamic_kernel)`
    """

    function_source = inspect.getsource(fn)
    assert "for b0 in loop(0, batch_size, 1)" in function_source
    assert "for h0 in loop(0, head_size, 1)" in function_source
    assert "for m0 in loop(0, seq_len, br)" in function_source
    assert function_source.count("for n0 in loop(0, seq_len, bc)") == 1
    assert "cur_br = min(br, seq_len - m0)" in function_source
    assert "cur_bc = min(bc, seq_len - n0)" in function_source
    assert "[b0, h0, n0, 0]" in function_source


def _assert_flash_static_static_source_uses_fixed_upper_bound_scratch() -> None:
    """校验 static-static flash attention scratch 使用固定 tile 上界。

    功能说明:
    - 只读取公开 demo 函数源码，确认可改写 score/state/output scratch 不再用 `cur_br/cur_bc` 直接分配。
    - 锁定 tail 通过 `view/deslice` 写入 fixed upper-bound storage。

    使用示例:
    - `_assert_flash_static_static_source_uses_fixed_upper_bound_scratch()`
    """

    function_source = inspect.getsource(flash_attention_inputs_static_tile_static_kernel)
    assert "unit_tile = br - br + 1" in function_source
    assert "m_state = alloc([br, unit_tile]" in function_source
    assert "sum_state = alloc([br, unit_tile]" in function_source
    assert "weighted = alloc([br, dim_size]" in function_source
    assert "matmul_score = alloc([br, bc]" in function_source
    assert "score_tile = alloc([br, bc]" in function_source
    assert "score_region = view(matmul_score, [0, 0], [cur_br, cur_bc]" in function_source
    assert "deslice(score_tile, score_region, [0, 0], [cur_br, cur_bc]" in function_source
    assert "output_region = view(output_tile, [0, 0], [cur_br, dim_size]" in function_source
    assert "m_state = alloc([cur_br" not in function_source
    assert "sum_state = alloc([cur_br" not in function_source
    assert "matmul_score = alloc([cur_br, cur_bc]" not in function_source
    assert "score_tile = alloc([cur_br, cur_bc]" not in function_source


def _read_first_ir(case_name: str) -> str:
    """读取公开 dump 目录中的生成侧 first-ir。

    功能说明:
    - 只读取 `run_lowering_demo(...)` 公开写出的 `kernel/dump/<case>/01-first-ir.mlir`。
    - 用于验证 DSL/kernel 生成侧已产生 fixed upper-bound scratch，而不是依赖后续 pass 掩盖。

    使用示例:
    - `_read_first_ir("test/flash_attention/static_static")`
    """

    return (_REPO_ROOT / "kernel" / "dump" / Path(case_name) / "01-first-ir.mlir").read_text(encoding="utf-8")


def _assert_flash_static_static_first_ir_uses_fixed_upper_bound_scratch() -> None:
    """校验 static-static flash attention 生成侧 first-ir 的 fixed upper-bound scratch。

    功能说明:
    - 锁定可改写 scratch alloc 均使用 `br/bc/dim` 固定上界。
    - 锁定 current query/key tile 由 `dma.view/deslice` 表达，first-ir 中不再以 tail `#S2` 直接分配 scratch。

    使用示例:
    - `_assert_flash_static_static_first_ir_uses_fixed_upper_bound_scratch()`
    """

    first_ir = _read_first_ir("test/flash_attention/static_static")
    assert '!nn.memory<[#C64, #C64], [#C64, #C1], f32, #nn.space<tsm>>' in first_ir
    assert '!nn.memory<[#C64, #C1], [#C1, #C1], f32, #nn.space<tsm>>' in first_ir
    assert '!nn.memory<[#C64, #C91], [#C91, #C1], f32, #nn.space<tsm>>' in first_ir
    assert '"kernel.binary_elewise"' in first_ir
    assert 'kind = "max"' in first_ir
    assert '!nn.memory<[#C64, #C2], [#C2, #C1], f32, #nn.space<tsm>>' not in first_ir
    assert re.search(r'"dma\.view".*-> !nn\.memory<\[#S2, #S2\]', first_ir) is not None
    assert re.search(r'"dma\.view".*-> !nn\.memory<\[#S2, #C91\]', first_ir) is not None
    assert re.search(r'"dma\.alloc".*#S2', first_ir) is None


def _assert_no_flash_tail_shape_alloc(first_ir: str, tail_symbols: tuple[str, ...]) -> None:
    """校验 flash attention first-ir 的 alloc result shape 不直接使用 tail 维。

    功能说明:
    - 只解析公开 dump 文本中的 `dma.alloc` result shape。
    - 防止 dynamic/static-dynamic case 回退为 `cur_br/cur_bc` scratch alloc。

    使用示例:
    - `_assert_no_flash_tail_shape_alloc(first_ir, ("#S2", "#S5"))`
    """

    for line in first_ir.splitlines():
        if '"dma.alloc"' not in line or "-> !nn.memory<[" not in line:
            continue
        result_shape = line.split("-> !nn.memory<[", 1)[1].split("]", 1)[0]
        assert not any(tail_symbol in result_shape for tail_symbol in tail_symbols), line


def _assert_flash_symbolic_tile_first_ir_uses_fixed_upper_bound_scratch(case_name: str, tail_symbols: tuple[str, ...]) -> None:
    """校验 symbolic tile flash attention first-ir 使用 BR/BC 上界 scratch。

    功能说明:
    - 锁定 static-dynamic 与 dynamic-dynamic demo 的 scratch alloc 使用 `BR/BC` 上界。
    - 锁定当前 query/key tile 通过 `dma.view/deslice` 表达。

    使用示例:
    - `_assert_flash_symbolic_tile_first_ir_uses_fixed_upper_bound_scratch("test/flash_attention/static_dynamic", ("#S2", "#S5"))`
    """

    first_ir = _read_first_ir(case_name)
    assert '!nn.memory<[#S_BR, #S_BC], [#S_BC, #C1], f32, #nn.space<tsm>>' in first_ir
    assert '!nn.memory<[#S_BR, #C1], [#C1, #C1], f32, #nn.space<tsm>>' in first_ir
    assert '"kernel.binary_elewise"' in first_ir
    assert 'kind = "max"' in first_ir
    assert '!nn.memory<[#S_BR, #C2], [#C2, #C1], f32, #nn.space<tsm>>' not in first_ir
    assert re.search(r'"dma\.view".*-> !nn\.memory<\[' + re.escape(tail_symbols[0]) + r",", first_ir) is not None
    assert re.search(r'"dma\.view".*-> !nn\.memory<\[' + re.escape(tail_symbols[0]) + r", " + re.escape(tail_symbols[1]) + r"\]", first_ir) is not None
    _assert_no_flash_tail_shape_alloc(first_ir, tail_symbols)


def _assert_flash_script_reports_tail(stdout: str) -> None:
    """校验 demo 脚本输出显式证明 multi-tile 与 tail。

    功能说明:
    - 只解析公开脚本输出 `[ARGS]` 摘要。
    - 防止脚本继续用可整除序列长度假通过。

    使用示例:
    - `_assert_flash_script_reports_tail(completed.stdout)`
    """

    assert "query_tiles=" in stdout
    assert "key_tiles=" in stdout
    assert "query_tail=" in stdout
    assert "key_tail=" in stdout
    assert "multi_tile=True" in stdout
    assert "tail=True" in stdout


def _static_static_flash_args() -> tuple[Memory, Memory, Memory, Memory]:
    """构造 static-static flash attention 编译参数。

    功能说明:
    - output/Q/K/V 均使用固定 seed `2026051621` 生成并固化的 `2x11x389x91` 具体 static memory。

    使用示例:
    - `_static_static_flash_args()`
    """

    return (
        Memory([2, 11, 389, 91], NumericType.Float32),
        Memory([2, 11, 389, 91], NumericType.Float32),
        Memory([2, 11, 389, 91], NumericType.Float32),
        Memory([2, 11, 389, 91], NumericType.Float32),
    )


def _static_dynamic_flash_args() -> tuple[Memory, Memory, Memory, Memory]:
    """构造 static-dynamic flash attention 编译参数。

    功能说明:
    - output/Q/K/V 均使用固定 seed `2026051622` 生成并固化的 `1x8x389x98` 具体 static memory。

    使用示例:
    - `_static_dynamic_flash_args()`
    """

    return (
        Memory([1, 8, 389, 98], NumericType.Float32),
        Memory([1, 8, 389, 98], NumericType.Float32),
        Memory([1, 8, 389, 98], NumericType.Float32),
        Memory([1, 8, 389, 98], NumericType.Float32),
    )


def _dynamic_flash_args() -> tuple[Memory, Memory, Memory, Memory]:
    """构造 dynamic flash attention 编译参数。

    功能说明:
    - output/Q/K/V 的 batch/head/sequence/dim 全部使用 `B/H/SL/D` 符号维度。

    使用示例:
    - `_dynamic_flash_args()`
    """

    return (
        Memory(["B", "H", "SL", "D"], NumericType.Float32),
        Memory(["B", "H", "SL", "D"], NumericType.Float32),
        Memory(["B", "H", "SL", "D"], NumericType.Float32),
        Memory(["B", "H", "SL", "D"], NumericType.Float32),
    )


def _run_kernel_script(script: str) -> subprocess.CompletedProcess[str]:
    """运行 flash attention demo 脚本。

    功能说明:
    - 只通过公开脚本入口验证 demo，可捕获编译或执行失败。

    使用示例:
    - `_run_kernel_script("kernel/flash_attention/inputs_static_tile_static.py")`
    """

    env = os.environ.copy()
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    env["PYTHONPATH"] = str(_REPO_ROOT)
    return subprocess.run(
        [sys.executable, script],
        cwd=_REPO_ROOT,
        env=env,
        text=True,
        capture_output=True,
        check=True,
        timeout=240,
    )


def test_flash_static_static_demo_keeps_static_memory_and_tile() -> None:
    """static-static demo 应生成 static memory 与 static tile。"""

    module, source = run_lowering_demo(
        "test/flash_attention/static_static",
        flash_attention_inputs_static_tile_static_kernel,
        *_static_static_flash_args(),
    )
    module_text = str(module)

    _assert_flash_source_uses_kernel_softmax(flash_attention_inputs_static_tile_static_kernel)
    _assert_flash_source_uses_query_and_key_tile_loops(flash_attention_inputs_static_tile_static_kernel)
    _assert_flash_static_static_source_uses_fixed_upper_bound_scratch()
    _assert_flash_static_static_first_ir_uses_fixed_upper_bound_scratch()
    assert STATIC_STATIC_FLASH_MEMORY in module_text
    assert STATIC_DYNAMIC_FLASH_MEMORY not in module_text
    assert DYNAMIC_FLASH_MEMORY not in module_text
    assert "!symbol.int<#symbol.expr<BR>>" not in module_text
    assert "!symbol.int<#symbol.expr<BC>>" not in module_text
    assert "step = #symbol.expr<64>" in module_text
    assert '"kernel.binary_elewise"' in module_text
    assert 'kind = "max"' in module_text
    assert "matmul<" in source
    assert "max<" in source
    assert "reduce_max<" in source
    assert "reduce_sum<" in source
    assert "broadcast<" in source
    assert "exp<" in source
    assert "truediv<" in source
    assert "softmax" not in source


def test_flash_static_dynamic_demo_keeps_static_memory_and_symbolic_tile() -> None:
    """static-dynamic demo 应生成 static memory 与 BR/BC runtime tile。"""

    module, _source = run_lowering_demo(
        "test/flash_attention/static_dynamic",
        flash_attention_inputs_static_tile_dynamic_kernel,
        *_static_dynamic_flash_args(),
        SymbolDim("BR"),
        SymbolDim("BC"),
    )
    module_text = str(module)

    _assert_flash_source_uses_kernel_softmax(flash_attention_inputs_static_tile_dynamic_kernel)
    _assert_flash_source_uses_query_and_key_tile_loops(flash_attention_inputs_static_tile_dynamic_kernel)
    _assert_flash_symbolic_tile_first_ir_uses_fixed_upper_bound_scratch("test/flash_attention/static_dynamic", ("#S2", "#S5"))
    assert STATIC_DYNAMIC_FLASH_MEMORY in module_text
    assert STATIC_STATIC_FLASH_MEMORY not in module_text
    assert DYNAMIC_FLASH_MEMORY not in module_text
    assert "!symbol.int<#symbol.expr<BR>>" in module_text
    assert "!symbol.int<#symbol.expr<BC>>" in module_text
    assert "step = #symbol.expr<BR>" in module_text
    assert "step = #symbol.expr<BC>" in module_text
    assert '"kernel.reduce"' in module_text
    assert '"kernel.binary_elewise"' in module_text
    assert 'kind = "max"' in module_text
    assert '"kernel.exp"' in module_text
    assert '"dma.broadcast"' in module_text
    assert "!nn.memory<[#symbol.expr<s1>" not in module_text


def test_flash_dynamic_dynamic_demo_keeps_symbolic_memory_and_symbolic_tile() -> None:
    """dynamic-dynamic demo 应生成 B/H memory 与 BR/BC runtime tile。"""

    module, _source = run_lowering_demo(
        "test/flash_attention/dynamic_dynamic",
        flash_attention_inputs_dynamic_tile_dynamic_kernel,
        *_dynamic_flash_args(),
        SymbolDim("BR"),
        SymbolDim("BC"),
    )
    module_text = str(module)

    _assert_flash_source_uses_kernel_softmax(flash_attention_inputs_dynamic_tile_dynamic_kernel)
    _assert_flash_source_uses_query_and_key_tile_loops(flash_attention_inputs_dynamic_tile_dynamic_kernel)
    _assert_flash_symbolic_tile_first_ir_uses_fixed_upper_bound_scratch("test/flash_attention/dynamic_dynamic", ("#S4", "#S7"))
    assert DYNAMIC_FLASH_MEMORY in module_text
    assert STATIC_STATIC_FLASH_MEMORY not in module_text
    assert STATIC_DYNAMIC_FLASH_MEMORY not in module_text
    assert "!symbol.int<#symbol.expr<BR>>" in module_text
    assert "!symbol.int<#symbol.expr<BC>>" in module_text
    assert "step = #symbol.expr<BR>" in module_text
    assert "step = #symbol.expr<BC>" in module_text
    assert '"kernel.reduce"' in module_text
    assert '"kernel.binary_elewise"' in module_text
    assert 'kind = "max"' in module_text
    assert '"kernel.exp"' in module_text
    assert '"dma.broadcast"' in module_text
    assert "!nn.memory<[#symbol.expr<s1>" not in module_text


def test_flash_attention_target_scripts_execute() -> None:
    """三条 flash attention 脚本都应通过公开脚本入口。"""

    scripts = (
        "kernel/flash_attention/inputs_static_tile_static.py",
        "kernel/flash_attention/inputs_static_tile_dynamic.py",
        "kernel/flash_attention/inputs_dynamic_tile_dynamic.py",
    )
    for script in scripts:
        completed = _run_kernel_script(script)
        assert "[CHECK] flash_attention/" in completed.stdout
        assert "max_abs_diff=" in completed.stdout
        _assert_flash_script_reports_tail(completed.stdout)
