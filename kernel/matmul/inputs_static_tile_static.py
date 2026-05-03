"""Matmul demo with static inputs and static tiles.


功能说明:
- 实现 `inputs 静 + tile 静` 的二维 matmul kernel demo。
- 输入 shape 固定为 `lhs[32, 16]`、`rhs[16, 32]`、`out[32, 32]`。
- tile 固定为 `TILE_M=16`、`TILE_N=16`。
- 通过 `dsl_run` 真实执行，并和 `torch.matmul` 参考结果对齐。

API 列表:
- `matmul_inputs_static_tile_static_kernel(out: Tensor[f32, 32, 32], lhs: Tensor[f32, 32, 16], rhs: Tensor[f32, 16, 32]) -> None`
- `main() -> None`

使用示例:
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 kernel/matmul/inputs_static_tile_static.py`

关联文件:
- 功能实现: `kernel/matmul/inputs_static_tile_static.py`
- 公共运行器: `kernel/runner.py`
"""

from __future__ import annotations

import sys
from pathlib import Path

import torch

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from kernel.runner import run_torch_demo
from kernel_gen.operation.dma import deslice, slice
from kernel_gen.operation.nn import matmul
from kernel_gen.operation.scf import loop
from kernel_gen.symbol_variable.memory import MemorySpace


def matmul_inputs_static_tile_static_kernel(
    out: "Tensor[f32, 32, 32]",
    lhs: "Tensor[f32, 32, 16]",
    rhs: "Tensor[f32, 16, 32]",
) -> None:
    """执行静态输入、静态 tile 的 matmul。


    功能说明:
    - 读取 `lhs/rhs/out` 的静态 shape。
    - 以固定 `16x16` 输出 tile 做二维循环。
    - K 维不切分，每个 tile 执行一次 `nn.matmul` 并写回输出。

    使用示例:
    - `matmul_inputs_static_tile_static_kernel(out, lhs, rhs)`
    """

    m_size = lhs.shape.get_shape()[0]
    k_size = lhs.shape.get_shape()[1]
    n_size = rhs.shape.get_shape()[1]
    tile_m = 16
    tile_n = 16

    for m0 in loop(0, m_size, tile_m):
        for n0 in loop(0, n_size, tile_n):
            lhs_tile = slice(lhs, [m0, 0], [tile_m, k_size], [1, 1], MemorySpace.TSM)
            rhs_tile = slice(rhs, [0, n0], [k_size, tile_n], [1, 1], MemorySpace.TSM)
            partial = matmul(lhs_tile, rhs_tile)
            deslice(out, partial, [m0, n0], [tile_m, tile_n], [1, 1])


def main() -> None:
    """运行静态输入、静态 tile 的 matmul demo。


    功能说明:
    - 构造真实 torch tensor 输入。
    - 调用公共 runner 执行 `dsl_run`，并写入 `kernel/dump/matmul/inputs_static_tile_static/`。
    - 用 `torch.matmul(lhs, rhs)` 校验输出。

    使用示例:
    - `python3 kernel/matmul/inputs_static_tile_static.py`
    """

    lhs = torch.arange(32 * 16, dtype=torch.float32).reshape(32, 16) / 17.0
    rhs = torch.arange(16 * 32, dtype=torch.float32).reshape(16, 32) / 19.0
    out = torch.empty((32, 32), dtype=torch.float32)
    expected = torch.matmul(lhs, rhs)
    result = run_torch_demo(
        "matmul/inputs_static_tile_static",
        matmul_inputs_static_tile_static_kernel,
        (out, lhs, rhs),
        out,
        expected,
    )
    print(result.dsl_result.module)
    print(result.dsl_result.source)
    print(f"[CHECK] {result.case_name} max_abs_diff={result.max_abs_diff}")


if __name__ == "__main__":
    main()
