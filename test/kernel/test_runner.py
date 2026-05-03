"""Kernel runner public API tests.


功能说明:
- 覆盖 `kernel.runner` 对公开 `run_torch_demo(...)` 的真实执行链路。
- 锁定 runner 能把 `int|float` runtime scalar 原样传给 `dsl_run(...)`，并保持输出校验合同。

API 列表:
- 无（pytest 文件，不承载公开 API）

使用示例:
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/kernel/test_runner.py`

关联文件:
- 功能实现: `kernel/runner.py`
- test: `test/kernel/test_runner.py`
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import torch

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from kernel.runner import KernelTorchDemoResult, run_torch_demo
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


def test_run_torch_demo_accepts_runtime_scalar_tile() -> None:
    """run_torch_demo 应透传 runtime scalar 并完成真实执行校验。"""

    out = torch.full((6,), -1, dtype=torch.int32)
    lhs = torch.tensor([1, 2, 3, 4, 5, 6], dtype=torch.int32)
    rhs = np.array([6, 5, 4, 3, 2, 1], dtype=np.int32)
    expected = lhs + torch.from_numpy(rhs)

    result = run_torch_demo(
        "test_runner/dynamic_tile_add",
        runner_dynamic_tile_add_kernel,
        (out, lhs, rhs, 4),
        out,
        expected,
    )

    assert isinstance(result, KernelTorchDemoResult)
    assert result.dsl_result.runtime_args[-1] == 4
    assert torch.equal(out, expected)
