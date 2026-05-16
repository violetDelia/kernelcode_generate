"""Matmul symbolic memory/tile demo tests.


功能说明:
- 覆盖 `kernel/matmul` 三条目标 demo 的公开 kernel 函数与脚本入口。
- 锁定 dynamic demo 使用 `H/K/W` 符号 memory、`TILE_H/TILE_W/TILE_K` 符号 tile。
- 锁定 static dynamic demo 保留 static memory shape，同时 K/reduce 维按 `TILE_K` 切分并累加 partial。
- 锁定尾块通过有效区域 `dma.view` 写入零填充 full tile，避免 `?` shape 参与 memory 默认 stride。
- 锁定 static-static demo 同样具备 K/reduce accumulator，不允许 partial 直接覆盖 output。

API 列表:
- 无（pytest 文件，不承载公开 API）

使用示例:
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/kernel/test_matmul_symbolic_memory_genkernel.py`

关联文件:
- 功能实现: `kernel/matmul/inputs_dynamic_tile_dynamic.py`
- 功能实现: `kernel/matmul/inputs_static_tile_dynamic.py`
- 功能实现: `kernel/matmul/inputs_static_tile_static.py`
- 公共运行器: `kernel/runner.py`
"""

from __future__ import annotations

import inspect
import os
from pathlib import Path
import subprocess
import sys

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from kernel.matmul.inputs_dynamic_tile_dynamic import matmul_inputs_dynamic_tile_dynamic_kernel
from kernel.matmul.inputs_static_tile_dynamic import matmul_inputs_static_tile_dynamic_kernel
from kernel.matmul.inputs_static_tile_static import matmul_inputs_static_tile_static_kernel
from kernel.runner import run_lowering_demo
from kernel_gen.symbol_variable.memory import Memory
from kernel_gen.symbol_variable.symbol_dim import SymbolDim
from kernel_gen.symbol_variable.type import NumericType


def _assert_source_uses_accumulator(source: str) -> None:
    """校验 npu_demo source 中 accumulator 顺序。


    功能说明:
    - 当前测试文件内 helper，只服务公开 demo 输出的源码文本断言。
    - 要求 `fill -> matmul -> add -> output deslice`，避免 K loop partial 直接覆盖 output。

    使用示例:
    - `_assert_source_uses_accumulator(source)`
    """

    fill_index = source.index("fill<")
    matmul_index = source.index("matmul<")
    add_index = source.index("add<")
    output_deslice_index = source.index("deslice(arg0", add_index)
    assert fill_index < matmul_index < add_index < output_deslice_index


def _assert_python_source_uses_kernel_out_first(fn) -> None:
    """校验 demo Python 源码使用 kernel out-first helper。


    功能说明:
    - 当前测试文件内 helper，只读取公开 demo 函数源码。
    - 防止 demo 主计算入口回退到 `nn.matmul/nn.add` 返回式 helper。

    使用示例:
    - `_assert_python_source_uses_kernel_out_first(matmul_inputs_static_tile_static_kernel)`
    """

    function_source = inspect.getsource(fn)
    assert "kernel.matmul(" in function_source
    assert "kernel.add(" in function_source
    assert "partial = matmul(" not in function_source
    assert "updated_acc = add(" not in function_source


def _run_kernel_script(script: str) -> subprocess.CompletedProcess[str]:
    """运行 kernel demo 脚本并返回完成对象。


    功能说明:
    - 只通过公开 Python 脚本入口验证 demo。
    - 设置 `PYTHONDONTWRITEBYTECODE=1` 与当前 worktree `PYTHONPATH`。

    使用示例:
    - `_run_kernel_script("kernel/matmul/inputs_static_tile_static.py")`
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
        timeout=120,
    )


def test_dynamic_matmul_demo_uses_symbolic_memory_and_tile_reduce_accumulator() -> None:
    """dynamic demo 应生成 H/K/W memory、TILE_* tile 与 K loop accumulator。"""

    module, source = run_lowering_demo(
        "test/matmul/dynamic_symbolic_tile_reduce",
        matmul_inputs_dynamic_tile_dynamic_kernel,
        Memory(["H", "W"], NumericType.Float32),
        Memory(["H", "K"], NumericType.Float32),
        Memory(["K", "W"], NumericType.Float32),
        SymbolDim("TILE_H"),
        SymbolDim("TILE_W"),
        SymbolDim("TILE_K"),
    )
    module_text = str(module)

    _assert_python_source_uses_kernel_out_first(matmul_inputs_dynamic_tile_dynamic_kernel)
    assert "!nn.memory<[#symbol.expr<H>, #symbol.expr<W>]" in module_text
    assert "!nn.memory<[#symbol.expr<H>, #symbol.expr<K>]" in module_text
    assert "!nn.memory<[#symbol.expr<K>, #symbol.expr<W>]" in module_text
    assert "!symbol.int<#symbol.expr<TILE_H>>" in module_text
    assert "!symbol.int<#symbol.expr<TILE_W>>" in module_text
    assert "!symbol.int<#symbol.expr<TILE_K>>" in module_text
    assert "step = #symbol.expr<TILE_K>" in module_text
    assert '"kernel.matmul"' in module_text
    assert '"kernel.binary_elewise"' in module_text
    assert '"dma.view"' in module_text
    assert '"dma.deslice"' in module_text
    assert ".template view<T1>" in source
    assert "!nn.memory<[#symbol.expr<17>, #symbol.expr<19>]" not in module_text
    assert "!nn.memory<[#symbol.expr<s1>" not in module_text
    _assert_source_uses_accumulator(source)


def test_static_dynamic_matmul_demo_keeps_static_memory_and_symbolic_tile_reduce() -> None:
    """static dynamic demo 应保留 static memory，并使用 TILE_* 和 K loop accumulator。"""

    module, source = run_lowering_demo(
        "test/matmul/static_symbolic_tile_reduce",
        matmul_inputs_static_tile_dynamic_kernel,
        Memory([32, 32], NumericType.Float32),
        Memory([32, 16], NumericType.Float32),
        Memory([16, 32], NumericType.Float32),
        SymbolDim("TILE_H"),
        SymbolDim("TILE_W"),
        SymbolDim("TILE_K"),
    )
    module_text = str(module)

    _assert_python_source_uses_kernel_out_first(matmul_inputs_static_tile_dynamic_kernel)
    assert "!nn.memory<[#symbol.expr<32>, #symbol.expr<32>]" in module_text
    assert "!nn.memory<[#symbol.expr<32>, #symbol.expr<16>]" in module_text
    assert "!nn.memory<[#symbol.expr<16>, #symbol.expr<32>]" in module_text
    assert "!symbol.int<#symbol.expr<TILE_H>>" in module_text
    assert "!symbol.int<#symbol.expr<TILE_W>>" in module_text
    assert "!symbol.int<#symbol.expr<TILE_K>>" in module_text
    assert "step = #symbol.expr<TILE_K>" in module_text
    assert '"kernel.matmul"' in module_text
    assert '"kernel.binary_elewise"' in module_text
    assert '"dma.view"' in module_text
    assert '"dma.deslice"' in module_text
    assert ".template view<T1>" in source
    assert "!nn.memory<[#symbol.expr<H>, #symbol.expr<W>]" not in module_text
    assert "!nn.memory<[#symbol.expr<s1>" not in module_text
    _assert_source_uses_accumulator(source)


def test_static_static_matmul_demo_keeps_static_memory_and_static_tile_reduce() -> None:
    """static-static demo 应保留 static memory，并使用静态 K loop accumulator。"""

    module, source = run_lowering_demo(
        "test/matmul/static_static_tile_reduce",
        matmul_inputs_static_tile_static_kernel,
        Memory([32, 32], NumericType.Float32),
        Memory([32, 16], NumericType.Float32),
        Memory([16, 32], NumericType.Float32),
    )
    module_text = str(module)

    _assert_python_source_uses_kernel_out_first(matmul_inputs_static_tile_static_kernel)
    assert "!nn.memory<[#symbol.expr<32>, #symbol.expr<32>]" in module_text
    assert "!nn.memory<[#symbol.expr<32>, #symbol.expr<16>]" in module_text
    assert "!nn.memory<[#symbol.expr<16>, #symbol.expr<32>]" in module_text
    assert "step = #symbol.expr<5>" in module_text
    assert '"kernel.matmul"' in module_text
    assert '"kernel.binary_elewise"' in module_text
    assert '"dma.view"' in module_text
    assert '"dma.deslice"' in module_text
    assert "!nn.memory<[#symbol.expr<H>, #symbol.expr<W>]" not in module_text
    assert "!nn.memory<[#symbol.expr<s1>" not in module_text
    _assert_source_uses_accumulator(source)


def test_matmul_target_scripts_execute_and_tile_reduce_still_passes() -> None:
    """三条目标脚本都应通过公开脚本入口。"""

    scripts = (
        "kernel/matmul/inputs_dynamic_tile_dynamic.py",
        "kernel/matmul/inputs_static_tile_dynamic.py",
        "kernel/matmul/inputs_static_tile_static.py",
    )
    for script in scripts:
        completed = _run_kernel_script(script)
        assert "[CHECK] matmul/" in completed.stdout
        assert "max_abs_diff=" in completed.stdout
