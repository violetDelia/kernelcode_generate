"""Matmul symbolic memory/tile demo tests.


功能说明:
- 覆盖 `kernel/matmul` 三条目标 demo 的公开 kernel 函数与脚本入口。
- 锁定 dynamic demo 使用 `H/K/W` 符号 memory、`TILE_H/TILE_W/TILE_K` 符号 tile。
- 锁定 static demo 将 fixed-seed 随机选值具体化到 static IR，同时 K/reduce 维按 `TILE_K` 切分并累加 partial。
- 锁定尾块通过有效区域 alias 写入零填充 full tile，避免 `?` shape 参与 memory 默认 stride。
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
import random
import re
import shutil
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

_MATMUL_SS_SHAPE_RNG = random.Random(2026051601)
_MATMUL_SS_M = _MATMUL_SS_SHAPE_RNG.randint(160, 256)
_MATMUL_SS_K = _MATMUL_SS_SHAPE_RNG.randint(160, 256)
_MATMUL_SS_N = _MATMUL_SS_SHAPE_RNG.randint(160, 256)
_MATMUL_SS_TILE = random.Random(2026051700).choice(((64, 64, 64), (72, 56, 48), (48, 80, 56)))
_MATMUL_SD_SHAPE_RNG = random.Random(2026051602)
_MATMUL_SD_M = _MATMUL_SD_SHAPE_RNG.randint(160, 256)
_MATMUL_SD_K = _MATMUL_SD_SHAPE_RNG.randint(160, 256)
_MATMUL_SD_N = _MATMUL_SD_SHAPE_RNG.randint(160, 256)
_MATMUL_SD_TILE = random.Random(2026051713).choice(((64, 80, 64), (72, 88, 56), (48, 96, 64)))
_MATMUL_DD_SHAPE_RNG = random.Random(2026051603)
_MATMUL_DD_M = _MATMUL_DD_SHAPE_RNG.randint(160, 256)
_MATMUL_DD_K = _MATMUL_DD_SHAPE_RNG.randint(160, 256)
_MATMUL_DD_N = _MATMUL_DD_SHAPE_RNG.randint(160, 256)
_MATMUL_DD_TILE = random.Random(2026051711).choice(((80, 96, 72), (72, 88, 56), (48, 96, 64)))


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


def _read_first_ir(case_name: str) -> str:
    """读取公开 dump 目录中的生成侧 first-ir。

    功能说明:
    - 只读取 `run_lowering_demo(...)` 公开写出的 `kernel/dump/<case>/01-first-ir.mlir`。
    - 用于验证 DSL/kernel 生成侧已产生 fixed upper-bound scratch，而不是依赖后续 pass 掩盖。

    使用示例:
    - `_read_first_ir("test/matmul/dynamic_symbolic_tile_reduce")`
    """

    return (_REPO_ROOT / "kernel" / "dump" / Path(case_name) / "01-first-ir.mlir").read_text(encoding="utf-8")


def _assert_matmul_first_ir_uses_fixed_upper_bound_scratch(case_name: str) -> None:
    """校验 matmul 生成侧 first-ir 中可改写 scratch 已用上界形态。

    功能说明:
    - 锁定 accumulator、bias tile、lhs/rhs staging scratch 使用 tile 上界分配。
    - 锁定当前 tail 只通过 `dma.view/deslice` 表达，不能回退成 current tile scratch alloc。

    使用示例:
    - `_assert_matmul_first_ir_uses_fixed_upper_bound_scratch("test/matmul/dynamic_symbolic_tile_reduce")`
    """

    first_ir = _read_first_ir(case_name)
    assert re.search(r'"dma\.alloc".*-> !nn\.memory<\[(#S_TILE_H|#C72), (#S_TILE_W|#C56)\]', first_ir)
    assert re.search(r'"dma\.alloc".*-> !nn\.memory<\[(#S_TILE_H|#C72), (#S_TILE_K|#C48)\]', first_ir)
    assert re.search(r'"dma\.alloc".*-> !nn\.memory<\[(#S_TILE_K|#C48), (#S_TILE_W|#C56)\]', first_ir)
    assert re.search(r'"dma\.alloc".*-> !nn\.memory<\[(#S_TILE_W|#C56)\], \[#C1\]', first_ir)
    assert re.search(r'"dma\.view".*-> !nn\.memory<\[#S2, #S4\]', first_ir)
    assert re.search(r'"dma\.alloc".*-> !nn\.memory<\[#S2, #S4\]', first_ir) is None
    assert re.search(r'"dma\.alloc".*-> !nn\.memory<\[#S2, #S6\]', first_ir) is None
    assert re.search(r'"dma\.alloc".*-> !nn\.memory<\[#S6, #S4\]', first_ir) is None
    assert re.search(r'"dma\.alloc".*-> !nn\.memory<\[#S4\], \[#C1\]', first_ir) is None


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

    dump_cases = {
        "kernel/matmul/inputs_static_tile_static.py": (
            "matmul/inputs_static_tile_static_absent_bias",
            "matmul/inputs_static_tile_static_present_bias",
        ),
        "kernel/matmul/inputs_static_tile_dynamic.py": ("matmul/inputs_static_tile_dynamic",),
        "kernel/matmul/inputs_dynamic_tile_dynamic.py": ("matmul/inputs_dynamic_tile_dynamic",),
    }
    for case_name in dump_cases[script]:
        shutil.rmtree(_REPO_ROOT / "kernel" / "dump" / Path(case_name), ignore_errors=True)
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
        timeout=300,
    )


def _assert_source_dump_contains(case_name: str, markers: tuple[str, ...]) -> None:
    """校验公开 source.cpp dump 来自本次脚本运行。

    功能说明:
    - 读取 `kernel/dump/<case_name>/source.cpp` 并核对关键源码 marker。
    - 只验证公开 dump 文件，不读取测试临时目录。

    使用示例:
    - `_assert_source_dump_contains("matmul/inputs_static_tile_dynamic", ("npu_demo::launch",))`
    """

    source_path = _REPO_ROOT / "kernel" / "dump" / Path(case_name) / "source.cpp"
    assert source_path.exists()
    source_dump = source_path.read_text(encoding="utf-8")
    missing_markers = tuple(marker for marker in markers if marker not in source_dump)
    assert source_dump.strip()
    assert not missing_markers


def _assert_first_ir_dump_contains(
    case_name: str,
    markers: tuple[str, ...],
    forbidden_markers: tuple[str, ...] = (),
) -> None:
    """校验公开 first-ir dump 的入口与 loop marker。

    功能说明:
    - 读取公开脚本写出的 `kernel/dump/<case_name>/01-first-ir.mlir`。
    - 核对入口 memory/tile 与 `symbol.for` step 正反 marker。
    - 防止测试只验证 stdout 或 test-only dump。

    使用示例:
    - `_assert_first_ir_dump_contains("matmul/inputs_static_tile_dynamic", ("func.func",))`
    """

    first_ir_path = _REPO_ROOT / "kernel" / "dump" / Path(case_name) / "01-first-ir.mlir"
    assert first_ir_path.exists()
    first_ir = first_ir_path.read_text(encoding="utf-8")
    missing_markers = tuple(marker for marker in markers if marker not in first_ir)
    unexpected_markers = tuple(marker for marker in forbidden_markers if marker in first_ir)
    assert first_ir.strip()
    assert not missing_markers
    assert not unexpected_markers


def test_dynamic_matmul_demo_uses_symbolic_memory_and_tile_reduce_accumulator() -> None:
    """dynamic demo 应生成 H/K/W memory、TILE_* tile 与 K loop accumulator。"""

    module, source = run_lowering_demo(
        "test/matmul/dynamic_symbolic_tile_reduce",
        matmul_inputs_dynamic_tile_dynamic_kernel,
        Memory(["H", "W"], NumericType.Float32),
        Memory(["H", "K"], NumericType.Float32),
        Memory(["K", "W"], NumericType.Float32),
        Memory(["W"], NumericType.Float32),
        SymbolDim("TILE_H"),
        SymbolDim("TILE_W"),
        SymbolDim("TILE_K"),
    )
    module_text = str(module)

    _assert_python_source_uses_kernel_out_first(matmul_inputs_dynamic_tile_dynamic_kernel)
    _assert_matmul_first_ir_uses_fixed_upper_bound_scratch("test/matmul/dynamic_symbolic_tile_reduce")
    assert "!nn.memory<[#symbol.expr<H>, #symbol.expr<W>]" in module_text
    assert "!nn.memory<[#symbol.expr<H>, #symbol.expr<K>]" in module_text
    assert "!nn.memory<[#symbol.expr<K>, #symbol.expr<W>]" in module_text
    assert "!nn.memory<[#symbol.expr<W>]" in module_text
    assert "!symbol.int<#symbol.expr<TILE_H>>" in module_text
    assert "!symbol.int<#symbol.expr<TILE_W>>" in module_text
    assert "!symbol.int<#symbol.expr<TILE_K>>" in module_text
    assert "step = #symbol.expr<TILE_K>" in module_text
    assert '"kernel.matmul"' in module_text
    assert '"kernel.binary_elewise"' in module_text
    assert '"dma.reinterpret"' in module_text
    assert '"dma.deslice"' in module_text
    assert "memory.get_data" in module_text
    assert "symbol.ne" in module_text
    assert "slice(" in source
    assert "!nn.memory<[#symbol.expr<17>, #symbol.expr<19>]" not in module_text
    assert "!nn.memory<[#symbol.expr<s1>" not in module_text
    _assert_source_uses_accumulator(source)


def test_static_dynamic_matmul_demo_keeps_static_memory_and_symbolic_tile_reduce() -> None:
    """static dynamic demo 应保留 static memory，并使用 TILE_* 和 K loop accumulator。"""

    module, source = run_lowering_demo(
        "test/matmul/static_symbolic_tile_reduce",
        matmul_inputs_static_tile_dynamic_kernel,
        Memory([_MATMUL_SD_M, _MATMUL_SD_N], NumericType.Float32),
        Memory([_MATMUL_SD_M, _MATMUL_SD_K], NumericType.Float32),
        Memory([_MATMUL_SD_K, _MATMUL_SD_N], NumericType.Float32),
        Memory([_MATMUL_SD_N], NumericType.Float32),
        SymbolDim("TILE_H"),
        SymbolDim("TILE_W"),
        SymbolDim("TILE_K"),
    )
    module_text = str(module)

    _assert_python_source_uses_kernel_out_first(matmul_inputs_static_tile_dynamic_kernel)
    _assert_matmul_first_ir_uses_fixed_upper_bound_scratch("test/matmul/static_symbolic_tile_reduce")
    assert f"!nn.memory<[#symbol.expr<{_MATMUL_SD_M}>, #symbol.expr<{_MATMUL_SD_N}>]" in module_text
    assert f"!nn.memory<[#symbol.expr<{_MATMUL_SD_M}>, #symbol.expr<{_MATMUL_SD_K}>]" in module_text
    assert f"!nn.memory<[#symbol.expr<{_MATMUL_SD_K}>, #symbol.expr<{_MATMUL_SD_N}>]" in module_text
    assert f"!nn.memory<[#symbol.expr<{_MATMUL_SD_N}>]" in module_text
    assert "!symbol.int<#symbol.expr<TILE_H>>" in module_text
    assert "!symbol.int<#symbol.expr<TILE_W>>" in module_text
    assert "!symbol.int<#symbol.expr<TILE_K>>" in module_text
    assert "step = #symbol.expr<TILE_K>" in module_text
    assert '"kernel.matmul"' in module_text
    assert '"kernel.binary_elewise"' in module_text
    assert '"dma.reinterpret"' in module_text
    assert '"dma.deslice"' in module_text
    assert "memory.get_data" in module_text
    assert "symbol.ne" in module_text
    assert "slice(" in source
    assert "!nn.memory<[#symbol.expr<H>, #symbol.expr<W>]" not in module_text
    assert "!nn.memory<[#symbol.expr<s1>" not in module_text
    _assert_source_uses_accumulator(source)


def test_static_static_matmul_demo_keeps_static_memory_and_static_tile_reduce() -> None:
    """static-static demo 应保留 static memory，并使用静态 K loop accumulator。"""

    module, source = run_lowering_demo(
        "test/matmul/static_static_tile_reduce",
        matmul_inputs_static_tile_static_kernel,
        Memory([_MATMUL_SS_M, _MATMUL_SS_N], NumericType.Float32),
        Memory([_MATMUL_SS_M, _MATMUL_SS_K], NumericType.Float32),
        Memory([_MATMUL_SS_K, _MATMUL_SS_N], NumericType.Float32),
        Memory([_MATMUL_SS_N], NumericType.Float32),
    )
    module_text = str(module)

    _assert_python_source_uses_kernel_out_first(matmul_inputs_static_tile_static_kernel)
    _assert_matmul_first_ir_uses_fixed_upper_bound_scratch("test/matmul/static_static_tile_reduce")
    assert f"!nn.memory<[#symbol.expr<{_MATMUL_SS_M}>, #symbol.expr<{_MATMUL_SS_N}>]" in module_text
    assert f"!nn.memory<[#symbol.expr<{_MATMUL_SS_M}>, #symbol.expr<{_MATMUL_SS_K}>]" in module_text
    assert f"!nn.memory<[#symbol.expr<{_MATMUL_SS_K}>, #symbol.expr<{_MATMUL_SS_N}>]" in module_text
    assert f"!nn.memory<[#symbol.expr<{_MATMUL_SS_N}>]" in module_text
    assert f"step = #symbol.expr<{_MATMUL_SS_TILE[2]}>" in module_text
    assert '"kernel.matmul"' in module_text
    assert '"kernel.binary_elewise"' in module_text
    assert '"dma.reinterpret"' in module_text
    assert '"dma.deslice"' in module_text
    assert "memory.get_data" in module_text
    assert "symbol.ne" in module_text
    assert "!nn.memory<[#symbol.expr<H>, #symbol.expr<W>]" not in module_text
    assert "!nn.memory<[#symbol.expr<s1>" not in module_text
    _assert_source_uses_accumulator(source)


def test_matmul_target_scripts_execute_and_tile_reduce_still_passes() -> None:
    """三条目标脚本都应通过公开脚本入口并报告 seed-selected profile。"""

    scripts = {
        "kernel/matmul/inputs_dynamic_tile_dynamic.py": (
            "profile=fixed-seed-random",
            "dynamic_ir=symbolic",
            "runtime=seed-selected",
            f"shape=(M={_MATMUL_DD_M},K={_MATMUL_DD_K},N={_MATMUL_DD_N})",
            f"selected_tile={_MATMUL_DD_TILE}",
        ),
        "kernel/matmul/inputs_static_tile_dynamic.py": (
            "profile=fixed-seed-random",
            "static_memory=seed-selected-concrete",
            "dynamic_tile=symbolic-runtime",
            f"shape=(M={_MATMUL_SD_M},K={_MATMUL_SD_K},N={_MATMUL_SD_N})",
            f"selected_tile={_MATMUL_SD_TILE}",
        ),
        "kernel/matmul/inputs_static_tile_static.py": (
            "profile=fixed-seed-random",
            "static_ir=seed-selected-concrete",
            f"shape=(M={_MATMUL_SS_M},K={_MATMUL_SS_K},N={_MATMUL_SS_N})",
            f"selected_tile=(M={_MATMUL_SS_TILE[0]},N={_MATMUL_SS_TILE[1]},K={_MATMUL_SS_TILE[2]})",
        ),
    }
    source_markers = {
        "kernel/matmul/inputs_static_tile_static.py": (
            (
                "matmul/inputs_static_tile_static_absent_bias",
                ("matmul_inputs_static_tile_static_kernel", "npu_demo::launch", "matmul<"),
            ),
            (
                "matmul/inputs_static_tile_static_present_bias",
                ("matmul_inputs_static_tile_static_kernel", "npu_demo::launch", "matmul<"),
            ),
        ),
        "kernel/matmul/inputs_static_tile_dynamic.py": (
            (
                "matmul/inputs_static_tile_dynamic",
                ("matmul_inputs_static_tile_dynamic_kernel", "npu_demo::launch"),
            ),
        ),
        "kernel/matmul/inputs_dynamic_tile_dynamic.py": (
            (
                "matmul/inputs_dynamic_tile_dynamic",
                ("matmul_inputs_dynamic_tile_dynamic_kernel", "npu_demo::launch"),
            ),
        ),
    }
    first_ir_markers = {
        "kernel/matmul/inputs_static_tile_static.py": (
            (
                "matmul/inputs_static_tile_static_absent_bias/matmul_inputs_static_tile_static_kernel",
                (
                    "func.func @matmul_inputs_static_tile_static_kernel",
                    f"!nn.memory<[#C{_MATMUL_SS_M}, #C{_MATMUL_SS_N}]",
                    f"!nn.memory<[#C{_MATMUL_SS_M}, #C{_MATMUL_SS_K}]",
                    f"!nn.memory<[#C{_MATMUL_SS_K}, #C{_MATMUL_SS_N}]",
                    f"!nn.memory<[#C{_MATMUL_SS_N}]",
                    f"#It1 = #symbol.iter<start = #C0, end = #C{_MATMUL_SS_M}, step = #C{_MATMUL_SS_TILE[0]}>",
                    f"#It2 = #symbol.iter<start = #C0, end = #C{_MATMUL_SS_N}, step = #C{_MATMUL_SS_TILE[1]}>",
                    f"#It3 = #symbol.iter<start = #C0, end = #C{_MATMUL_SS_K}, step = #C{_MATMUL_SS_TILE[2]}>",
                ),
                ("#S_TILE_H", "#S_TILE_W", "#S_TILE_K"),
            ),
            (
                "matmul/inputs_static_tile_static_present_bias/matmul_inputs_static_tile_static_kernel",
                (
                    "func.func @matmul_inputs_static_tile_static_kernel",
                    f"!nn.memory<[#C{_MATMUL_SS_M}, #C{_MATMUL_SS_N}]",
                    f"!nn.memory<[#C{_MATMUL_SS_M}, #C{_MATMUL_SS_K}]",
                    f"!nn.memory<[#C{_MATMUL_SS_K}, #C{_MATMUL_SS_N}]",
                    f"!nn.memory<[#C{_MATMUL_SS_N}]",
                    f"#It1 = #symbol.iter<start = #C0, end = #C{_MATMUL_SS_M}, step = #C{_MATMUL_SS_TILE[0]}>",
                    f"#It2 = #symbol.iter<start = #C0, end = #C{_MATMUL_SS_N}, step = #C{_MATMUL_SS_TILE[1]}>",
                    f"#It3 = #symbol.iter<start = #C0, end = #C{_MATMUL_SS_K}, step = #C{_MATMUL_SS_TILE[2]}>",
                ),
                ("#S_TILE_H", "#S_TILE_W", "#S_TILE_K"),
            ),
        ),
        "kernel/matmul/inputs_static_tile_dynamic.py": (
            (
                "matmul/inputs_static_tile_dynamic",
                (
                    "func.func @matmul_inputs_static_tile_dynamic_kernel",
                    f"!nn.memory<[#C{_MATMUL_SD_M}, #C{_MATMUL_SD_N}]",
                    f"!nn.memory<[#C{_MATMUL_SD_M}, #C{_MATMUL_SD_K}]",
                    f"!nn.memory<[#C{_MATMUL_SD_K}, #C{_MATMUL_SD_N}]",
                    f"!nn.memory<[#C{_MATMUL_SD_N}]",
                    "!symbol.int<#S_TILE_H>",
                    "!symbol.int<#S_TILE_W>",
                    "!symbol.int<#S_TILE_K>",
                    "step = #S_TILE_H",
                    "step = #S_TILE_W",
                    "step = #S_TILE_K",
                ),
                (
                    f"step = #C{_MATMUL_SD_TILE[0]}",
                    f"step = #C{_MATMUL_SD_TILE[1]}",
                    f"step = #C{_MATMUL_SD_TILE[2]}",
                ),
            ),
        ),
        "kernel/matmul/inputs_dynamic_tile_dynamic.py": (
            (
                "matmul/inputs_dynamic_tile_dynamic",
                (
                    "func.func @matmul_inputs_dynamic_tile_dynamic_kernel",
                    "!nn.memory<[#S_H, #S_W]",
                    "!nn.memory<[#S_H, #S_K]",
                    "!nn.memory<[#S_K, #S_W]",
                    "!nn.memory<[#S_W]",
                    "!symbol.int<#S_TILE_H>",
                    "!symbol.int<#S_TILE_W>",
                    "!symbol.int<#S_TILE_K>",
                    "step = #S_TILE_H",
                    "step = #S_TILE_W",
                    "step = #S_TILE_K",
                ),
                (
                    f"!nn.memory<[#C{_MATMUL_DD_M}, #C{_MATMUL_DD_N}]",
                    f"!nn.memory<[#C{_MATMUL_DD_M}, #C{_MATMUL_DD_K}]",
                    f"!nn.memory<[#C{_MATMUL_DD_K}, #C{_MATMUL_DD_N}]",
                    f"!nn.memory<[#C{_MATMUL_DD_N}]",
                    f"step = #C{_MATMUL_DD_TILE[0]}",
                    f"step = #C{_MATMUL_DD_TILE[1]}",
                    f"step = #C{_MATMUL_DD_TILE[2]}",
                ),
            ),
        ),
    }
    for script, expected_markers in scripts.items():
        completed = _run_kernel_script(script)
        assert "[CHECK] matmul/" in completed.stdout
        assert "absent_bias max_abs_diff=" in completed.stdout
        assert "present_bias max_abs_diff=" in completed.stdout
        assert "tile_seed=" in completed.stdout
        assert "tile_candidates=" in completed.stdout
        assert "bias_case_order=" in completed.stdout
        assert "max_abs_diff=" in completed.stdout
        for marker in expected_markers:
            assert marker in completed.stdout
        for case_name, markers in source_markers[script]:
            _assert_source_dump_contains(case_name, markers)
        for case_name, markers, forbidden_markers in first_ir_markers[script]:
            _assert_first_ir_dump_contains(case_name, markers, forbidden_markers)
