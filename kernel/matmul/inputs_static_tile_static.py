"""Matmul demo with static inputs and static tiles.


功能说明:
- 实现 `inputs 静 + tile 静` 的二维 matmul kernel demo。
- 输入 shape 由固定 seed `2026051601` 随机生成并固化为具体数字：`lhs[166, 217]`、`rhs[217, 172]`、`out[166, 172]`。
- tile 从轻量候选集合按固定 seed 选择，本次默认 `TILE_M=72`、`TILE_N=56`、`TILE_K=48`，每个维度都至少触发多轮 tile 循环。
- M/N/K 均大于对应 tile，且至少触发两次 tile loop；K 维尾块通过 `min(tile_k, k_size - k0)` 覆盖。
- K/reduce 维按 `TILE_K` 分块，每个 H/W 输出 tile 初始化 accumulator，K loop 内用 `kernel.matmul/kernel.add` 累加 partial，loop 后写回 output。
- 通过 `dsl_run` 真实执行，并分别校验 absent bias 的 NumPy `matmul` 与 present bias 的 `matmul + bias[None, :]`。

API 列表:
- `matmul_inputs_static_tile_static_kernel(out: Tensor[f32, 166, 172], lhs: Tensor[f32, 166, 217], rhs: Tensor[f32, 217, 172], bias: Tensor[f32, 172]) -> None`
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
from kernel_gen.operation.dma import alloc, broadcast, deslice, fill, reshape, view
from kernel_gen.operation.scf import loop
from kernel_gen.symbol_variable.memory import MemorySpace
from kernel_gen.symbol_variable.type import NumericType

_STATIC_SHAPE_SEED = 2026051601
_STATIC_SHAPE_RNG = random.Random(_STATIC_SHAPE_SEED)
_STATIC_M = _STATIC_SHAPE_RNG.randint(160, 256)
_STATIC_K = _STATIC_SHAPE_RNG.randint(160, 256)
_STATIC_N = _STATIC_SHAPE_RNG.randint(160, 256)
_TILE_SELECTION_SEED = 2026051700
_TILE_CANDIDATES = ((64, 64, 64), (72, 56, 48), (48, 80, 56))
_TILE_M, _TILE_N, _TILE_K = random.Random(_TILE_SELECTION_SEED).choice(_TILE_CANDIDATES)
_BIAS_CASE_ORDER_SEED = 2026051750
_BIAS_CASE_ORDER = tuple(random.Random(_BIAS_CASE_ORDER_SEED).sample(("absent", "present"), 2))


def matmul_inputs_static_tile_static_kernel(
    out: "Tensor[f32, 166, 172]",
    lhs: "Tensor[f32, 166, 217]",
    rhs: "Tensor[f32, 217, 172]",
    bias: "Tensor[f32, 172]",
) -> None:
    """执行静态输入、静态 tile 的 matmul。


    功能说明:
    - 读取 `lhs/rhs/out` 的静态 shape。
    - 以模块级固定 seed 选择的静态 tile 做三维循环，输入维度均大于 tile 并覆盖尾块。
    - K 维按 `tile_k` 切分，并通过 `kernel.matmul/kernel.add` out-first helper 累加到局部 accumulator。
    - 若 runtime bias 非空，则在 reduce 后、写回前广播 rank-1 bias 并累加。

    使用示例:
    - `matmul_inputs_static_tile_static_kernel(out, lhs, rhs, bias)`
    """

    m_size = lhs.get_shape()[0]
    k_size = lhs.get_shape()[1]
    n_size = rhs.get_shape()[1]
    tile_m = _TILE_M
    tile_n = _TILE_N
    tile_k = _TILE_K

    for m0 in loop(0, m_size, tile_m):
        for n0 in loop(0, n_size, tile_n):
            cur_m = min(tile_m, m_size - m0)
            cur_n = min(tile_n, n_size - n0)
            acc = alloc([tile_m, tile_n], NumericType.Float32, MemorySpace.TSM)
            fill(acc, 0)
            bias_tile = alloc([tile_n], NumericType.Float32, MemorySpace.TSM)
            fill(bias_tile, 0)
            bias_row = reshape(bias_tile, [1, tile_n])
            bias_full = alloc([tile_m, tile_n], NumericType.Float32, MemorySpace.TSM)
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
            if bias is not None:
                bias_region = view(bias, [n0], [cur_n], [1])
                deslice(bias_tile, bias_region, [0], [cur_n], [1])
                broadcast(bias_full, bias_row)
                kernel.add(acc, acc, bias_full)
            out_region = view(acc, [0, 0], [cur_m, cur_n], [1, 1])
            deslice(out, out_region, [m0, n0], [cur_m, cur_n], [1, 1])


def main() -> None:
    """运行静态输入、静态 tile 的 matmul demo。


    功能说明:
    - 构造固定 seed 随机 shape 对应的真实 NumPy ndarray 输入。
    - 调用公共 runner 执行 `dsl_run`，并写入 `kernel/dump/matmul/inputs_static_tile_static/`。
    - 分别用 `np.matmul(lhs, rhs)` 与 `np.matmul(lhs, rhs) + bias[None, :]` 校验输出。

    使用示例:
    - `python3 kernel/matmul/inputs_static_tile_static.py`
    """

    rng = np.random.default_rng(_STATIC_SHAPE_SEED)
    lhs = rng.normal(size=(_STATIC_M, _STATIC_K)).astype(np.float32)
    rhs = rng.normal(size=(_STATIC_K, _STATIC_N)).astype(np.float32)
    bias = rng.normal(size=(_STATIC_N,)).astype(np.float32)
    absent_out = np.empty((_STATIC_M, _STATIC_N), dtype=np.float32)
    present_out = np.empty((_STATIC_M, _STATIC_N), dtype=np.float32)
    absent_expected = np.matmul(lhs, rhs)
    present_expected = absent_expected + bias[None, :]
    results = {}
    for bias_case in _BIAS_CASE_ORDER:
        if bias_case == "absent":
            results[bias_case] = run_numpy_demo(
                "matmul/inputs_static_tile_static_absent_bias",
                matmul_inputs_static_tile_static_kernel,
                (absent_out, lhs, rhs, None),
                absent_out,
                absent_expected,
            )
            continue
        results[bias_case] = run_numpy_demo(
            "matmul/inputs_static_tile_static_present_bias",
            matmul_inputs_static_tile_static_kernel,
            (present_out, lhs, rhs, bias),
            present_out,
            present_expected,
        )
    absent_result = results["absent"]
    present_result = results["present"]
    print(
        "[ARGS] "
        f"seed={_STATIC_SHAPE_SEED} shape=(M={_STATIC_M},K={_STATIC_K},N={_STATIC_N}) "
        f"tile_seed={_TILE_SELECTION_SEED} tile_candidates={_TILE_CANDIDATES} "
        f"selected_tile=(M={_TILE_M},N={_TILE_N},K={_TILE_K}) "
        f"bias_case_order={_BIAS_CASE_ORDER} multi_tile=True tail=True bias_rank=1"
    )
    print(f"[CHECK] {absent_result.case_name} max_abs_diff={absent_result.max_abs_diff}")
    print(f"[CHECK] {present_result.case_name} max_abs_diff={present_result.max_abs_diff}")


if __name__ == "__main__":
    main()
