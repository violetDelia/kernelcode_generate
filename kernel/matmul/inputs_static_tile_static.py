"""Matmul demo with static inputs and static tiles.


功能说明:
- 实现 `inputs 静 + tile 静` 的二维 matmul kernel demo。
- 输入 shape 固定为 `lhs[32, 16]`、`rhs[16, 32]`、`out[32, 32]`。
- tile 固定为 `TILE_M=8`、`TILE_N=8`、`TILE_K=5`，避免 memory-pool rewrite 后超过 npu_demo TSM backing 容量。
- K/reduce 维按 `TILE_K` 分块，每个 H/W 输出 tile 初始化 accumulator，K loop 内用 `kernel.matmul/kernel.add` 累加 partial，loop 后写回 output。
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
from kernel_gen.operation import kernel
from kernel_gen.operation.dma import alloc, deslice, fill, view
from kernel_gen.operation.scf import loop
from kernel_gen.symbol_variable.memory import MemorySpace
from kernel_gen.symbol_variable.type import NumericType


def matmul_inputs_static_tile_static_kernel(
    out: "Tensor[f32, 32, 32]",
    lhs: "Tensor[f32, 32, 16]",
    rhs: "Tensor[f32, 16, 32]",
) -> None:
    """执行静态输入、静态 tile 的 matmul。


    功能说明:
    - 读取 `lhs/rhs/out` 的静态 shape。
    - 以固定 `8x8x5` tile 做三维循环。
    - K 维按 `tile_k` 切分，并通过 `kernel.matmul/kernel.add` out-first helper 累加到局部 accumulator。

    使用示例:
    - `matmul_inputs_static_tile_static_kernel(out, lhs, rhs)`
    """

    m_size = lhs.get_shape()[0]
    k_size = lhs.get_shape()[1]
    n_size = rhs.get_shape()[1]
    tile_m = 8
    tile_n = 8
    tile_k = 5

    for m0 in loop(0, m_size, tile_m):
        for n0 in loop(0, n_size, tile_n):
            cur_m = min(tile_m, m_size - m0)
            cur_n = min(tile_n, n_size - n0)
            acc = alloc([tile_m, tile_n], NumericType.Float32, MemorySpace.TSM)
            fill(acc, 0)
            for k0 in loop(0, k_size, tile_k):
                cur_k = min(tile_k, k_size - k0)
                lhs_tile = alloc([tile_m, tile_k], NumericType.Float32, MemorySpace.TSM)
                rhs_tile = alloc([tile_k, tile_n], NumericType.Float32, MemorySpace.TSM)
                fill(lhs_tile, 0)
                fill(rhs_tile, 0)
                lhs_region = view(lhs, [m0, k0], [cur_m, cur_k], [1, 1])
                rhs_region = view(rhs, [k0, n0], [cur_k, cur_n], [1, 1])
                deslice(lhs_tile, lhs_region, [0, 0], [cur_m, cur_k], [1, 1])
                deslice(rhs_tile, rhs_region, [0, 0], [cur_k, cur_n], [1, 1])
                partial = alloc([tile_m, tile_n], NumericType.Float32, MemorySpace.TSM)
                kernel.matmul(partial, lhs_tile, rhs_tile)
                kernel.add(acc, acc, partial)
            out_region = view(acc, [0, 0], [cur_m, cur_n], [1, 1])
            deslice(out, out_region, [m0, n0], [cur_m, cur_n], [1, 1])


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
