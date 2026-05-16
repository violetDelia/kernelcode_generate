"""Kernel runner public API tests.


功能说明:
- 覆盖 `kernel.runner` 对公开 `run_numpy_demo(...)` 的真实执行链路。
- 锁定 runner 能把整数 runtime scalar 传给 `dsl_run(...)`，并保持输出校验合同。

API 列表:
- 无（pytest 文件，不承载公开 API）

使用示例:
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/kernel/test_runner.py`

关联文件:
- 功能实现: `kernel/runner.py`
- test: `test/kernel/test_runner.py`
"""

from __future__ import annotations

import importlib
import sys
from pathlib import Path

import numpy as np
import pytest

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from kernel.runner import KernelNumpyDemoResult, run_numpy_demo
from kernel_gen.operation import loop, slice, store
from kernel_gen.symbol_variable.memory import MemorySpace
from kernel_gen.symbol_variable.symbol_dim import SymbolDim


def runner_dynamic_tile_add_kernel(
    out: "Tensor[i32, 6]",
    lhs: "Tensor[i32, 6]",
    rhs: "Tensor[i32, 6]",
    tile_n: SymbolDim,
) -> None:
    """动态 tile runtime scalar 的 runner 测试 kernel。"""

    for index in loop(0, 6, tile_n):
        cur_n = min(tile_n, 6 - index)
        lhs_tile = slice(lhs, [index], [cur_n], [1], MemorySpace.TSM)
        rhs_tile = slice(rhs, [index], [cur_n], [1], MemorySpace.TSM)
        store(out, lhs_tile + rhs_tile, [index], [cur_n], [1])


def test_run_numpy_demo_accepts_runtime_scalar_tile() -> None:
    """run_numpy_demo 应透传 runtime scalar 并完成真实执行校验。"""

    out = np.full((6,), -1, dtype=np.int32)
    lhs = np.array([1, 2, 3, 4, 5, 6], dtype=np.int32)
    rhs = np.array([6, 5, 4, 3, 2, 1], dtype=np.int32)
    expected = lhs + rhs

    result = run_numpy_demo(
        "test_runner/dynamic_tile_add",
        runner_dynamic_tile_add_kernel,
        (out, lhs, rhs, 4),
        out,
        expected,
    )

    assert isinstance(result, KernelNumpyDemoResult)
    assert result.dsl_result.runtime_args[-1] == 4
    np.testing.assert_array_equal(out, expected)


def test_run_numpy_demo_rejects_numpy_integer_runtime_arg() -> None:
    """run_numpy_demo 应拒绝 np.integer，要求调用方显式转 Python int。"""

    out = np.full((6,), -1, dtype=np.int32)
    lhs = np.array([1, 2, 3, 4, 5, 6], dtype=np.int32)
    rhs = np.array([6, 5, 4, 3, 2, 1], dtype=np.int32)
    expected = lhs + rhs

    with pytest.raises(TypeError, match="real_args.*np.ndarray or int"):
        run_numpy_demo(
            "test_runner/reject_numpy_integer_tile",
            runner_dynamic_tile_add_kernel,
            (out, lhs, rhs, np.int64(4)),
            out,
            expected,
        )


def test_runner_old_torch_public_names_are_removed() -> None:
    """kernel.runner 不再公开旧 torch 命名入口。"""

    runner_module = importlib.import_module("kernel.runner")

    assert not hasattr(runner_module, "run_torch_demo")
    assert not hasattr(runner_module, "KernelTorchDemoResult")
