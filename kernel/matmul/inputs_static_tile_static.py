"""Matmul demo with static inputs and static tiles.


功能说明:
- 实现 `inputs 静 + tile 静` 的二维 matmul kernel demo。
- 输入 shape 由固定 seed `2026051601` 随机生成并固化为具体数字：`lhs[166, 217]`、`rhs[217, 172]`、`out[166, 172]`。
- tile 固定为 `TILE_M=64`、`TILE_N=64`、`TILE_K=64`，每个维度都至少触发三轮 tile 循环。
- M/N/K 均大于对应 tile，且至少触发两次 tile loop；K 维尾块通过 `min(tile_k, k_size - k0)` 覆盖。
- K/reduce 维按 `TILE_K` 分块，每个 H/W 输出 tile 初始化 accumulator，K loop 内用 `kernel.matmul/kernel.add` 累加 partial，loop 后写回 output。
- 通过 `dsl_run` 真实执行，并和 NumPy `matmul` 参考结果对齐。

API 列表:
- `matmul_inputs_static_tile_static_kernel(out: Tensor[f32, 166, 172], lhs: Tensor[f32, 166, 217], rhs: Tensor[f32, 217, 172]) -> None`
- `main() -> None`

使用示例:
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 kernel/matmul/inputs_static_tile_static.py`

关联文件:
- 功能实现: `kernel/matmul/inputs_static_tile_static.py`
- 公共运行器: `kernel/runner.py`
"""

from __future__ import annotations

import random
import sys
from pathlib import Path

import numpy as np

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from kernel.runner import run_numpy_demo
from kernel_gen.operation import kernel
from kernel_gen.operation.dma import alloc, deslice, fill, view
from kernel_gen.operation.scf import loop
from kernel_gen.symbol_variable.memory import MemorySpace
from kernel_gen.symbol_variable.type import NumericType

_STATIC_SHAPE_SEED = 2026051601
_STATIC_SHAPE_RNG = random.Random(_STATIC_SHAPE_SEED)
_STATIC_M = _STATIC_SHAPE_RNG.randint(160, 256)
_STATIC_K = _STATIC_SHAPE_RNG.randint(160, 256)
_STATIC_N = _STATIC_SHAPE_RNG.randint(160, 256)
_TILE_M = 64
_TILE_N = 64
_TILE_K = 64


def matmul_inputs_static_tile_static_kernel(
    out: "Tensor[f32, 166, 172]",
    lhs: "Tensor[f32, 166, 217]",
    rhs: "Tensor[f32, 217, 172]",
) -> None:
    """执行静态输入、静态 tile 的 matmul。


    功能说明:
    - 读取 `lhs/rhs/out` 的静态 shape。
    - 以固定 `64x64x64` tile 做三维循环，输入维度均大于 tile 并覆盖尾块。
    - K 维按 `tile_k` 切分，并通过 `kernel.matmul/kernel.add` out-first helper 累加到局部 accumulator。

    使用示例:
    - `matmul_inputs_static_tile_static_kernel(out, lhs, rhs)`
    """

    m_size = lhs.get_shape()[0]
    k_size = lhs.get_shape()[1]
    n_size = rhs.get_shape()[1]
    tile_m = 64
    tile_n = 64
    tile_k = 64

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
    - 构造固定 seed 随机 shape 对应的真实 NumPy ndarray 输入。
    - 调用公共 runner 执行 `dsl_run`，并写入 `kernel/dump/matmul/inputs_static_tile_static/`。
    - 用 `np.matmul(lhs, rhs)` 校验输出。

    使用示例:
    - `python3 kernel/matmul/inputs_static_tile_static.py`
    """

    rng = np.random.default_rng(_STATIC_SHAPE_SEED)
    lhs = rng.normal(size=(_STATIC_M, _STATIC_K)).astype(np.float32)
    rhs = rng.normal(size=(_STATIC_K, _STATIC_N)).astype(np.float32)
    out = np.empty((_STATIC_M, _STATIC_N), dtype=np.float32)
    expected = np.matmul(lhs, rhs)
    result = run_numpy_demo(
        "matmul/inputs_static_tile_static",
        matmul_inputs_static_tile_static_kernel,
        (out, lhs, rhs),
        out,
        expected,
    )
    print(result.dsl_result.module)
    print(result.dsl_result.source)
    print(
        "[ARGS] "
        f"seed={_STATIC_SHAPE_SEED} shape=(M={_STATIC_M},K={_STATIC_K},N={_STATIC_N}) "
        f"tile=({_TILE_M},{_TILE_K},{_TILE_N}) multi_tile=True tail=True"
    )
    print(f"[CHECK] {result.case_name} max_abs_diff={result.max_abs_diff}")


if __name__ == "__main__":
    main()
