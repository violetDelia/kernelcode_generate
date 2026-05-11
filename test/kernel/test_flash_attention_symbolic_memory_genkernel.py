"""Flash attention symbolic memory/tile demo tests.

功能说明:
- 覆盖 `kernel/flash_attention` 三条目标 demo 的公开 kernel 函数与脚本入口。
- 锁定 static demo 保留具体 `4x4x8x4` memory，dynamic demo 保留 `B/H` 符号 memory。
- 锁定 static-dynamic 与 dynamic-dynamic demo 的 `BR/BC` tile 参数作为 runtime `SymbolDim` 进入 lowering。

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
STATIC_FLASH_MEMORY = "!nn.memory<[#symbol.expr<4>, #symbol.expr<4>, #symbol.expr<8>, #symbol.expr<4>]"
DYNAMIC_FLASH_MEMORY = "!nn.memory<[#symbol.expr<B>, #symbol.expr<H>, #symbol.expr<8>, #symbol.expr<4>]"


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
    assert "broadcast(" in function_source
    assert "kernel.exp(" in function_source
    assert "kernel.truediv(" in function_source
    assert "softmax(" not in function_source
    assert "score = matmul(" not in function_source
    assert "weighted = matmul(" not in function_source


def _static_flash_args() -> tuple[Memory, Memory, Memory, Memory]:
    """构造 static flash attention 编译参数。

    功能说明:
    - output/Q/K/V 均使用 `4x4x8x4` 的具体 static memory。

    使用示例:
    - `_static_flash_args()`
    """

    return (
        Memory([4, 4, 8, 4], NumericType.Float32),
        Memory([4, 4, 8, 4], NumericType.Float32),
        Memory([4, 4, 8, 4], NumericType.Float32),
        Memory([4, 4, 8, 4], NumericType.Float32),
    )


def _dynamic_flash_args() -> tuple[Memory, Memory, Memory, Memory]:
    """构造 dynamic flash attention 编译参数。

    功能说明:
    - output/Q/K/V 的 batch/head 使用 `B/H` 符号维度，序列长度和 dim 保持 static。

    使用示例:
    - `_dynamic_flash_args()`
    """

    return (
        Memory(["B", "H", 8, 4], NumericType.Float32),
        Memory(["B", "H", 8, 4], NumericType.Float32),
        Memory(["B", "H", 8, 4], NumericType.Float32),
        Memory(["B", "H", 8, 4], NumericType.Float32),
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
        *_static_flash_args(),
    )
    module_text = str(module)

    _assert_flash_source_uses_kernel_softmax(flash_attention_inputs_static_tile_static_kernel)
    assert STATIC_FLASH_MEMORY in module_text
    assert DYNAMIC_FLASH_MEMORY not in module_text
    assert "!symbol.int<#symbol.expr<BR>>" not in module_text
    assert "!symbol.int<#symbol.expr<BC>>" not in module_text
    assert "step = #symbol.expr<4>" in module_text
    assert "matmul<" in source
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
        *_static_flash_args(),
        SymbolDim("BR"),
        SymbolDim("BC"),
    )
    module_text = str(module)

    _assert_flash_source_uses_kernel_softmax(flash_attention_inputs_static_tile_dynamic_kernel)
    assert STATIC_FLASH_MEMORY in module_text
    assert DYNAMIC_FLASH_MEMORY not in module_text
    assert "!symbol.int<#symbol.expr<BR>>" in module_text
    assert "!symbol.int<#symbol.expr<BC>>" in module_text
    assert "step = #symbol.expr<BR>" in module_text
    assert '"kernel.reduce"' in module_text
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
    assert DYNAMIC_FLASH_MEMORY in module_text
    assert STATIC_FLASH_MEMORY not in module_text
    assert "!symbol.int<#symbol.expr<BR>>" in module_text
    assert "!symbol.int<#symbol.expr<BC>>" in module_text
    assert "step = #symbol.expr<BR>" in module_text
    assert '"kernel.reduce"' in module_text
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
