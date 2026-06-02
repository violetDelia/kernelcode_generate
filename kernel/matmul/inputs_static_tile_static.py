"""Matmul demo with static inputs and static tiles.


功能说明:
- 实现 `inputs 静 + tile 静` 的二维 matmul kernel demo。
- 脚本入口每次运行先随机生成 `shape_seed/tile_seed`，再从受控范围选择本次 shape 与 tile。
- static case 将本次随机 shape 具体化到 IR memory type。
- tile 从候选集合随机选择，并作为 static IR tile 常量进入 loop。
- M/N/K 均大于对应 tile，且至少触发两次 tile loop；K 维尾块通过 `min(tile_k, k_size - k0)` 覆盖。
- K/reduce 维按 `TILE_K` 分块，每个 H/W 输出 tile 按当前有效区域分配 accumulator，K loop 内用 `kernel.matmul/kernel.add` 累加 partial，loop 后写回 output。
- 通过 `dsl_run` 真实执行，并分别校验 absent bias 的 NumPy `matmul` 与 present bias 的 `matmul + bias[None, :]`。

API 列表:
- `matmul_inputs_static_tile_static_kernel(out: Tensor[f32, M, N], lhs: Tensor[f32, M, K], rhs: Tensor[f32, K, N], bias: Tensor[f32, N]) -> None`
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
_TILE_CANDIDATES = ((72, 56, 48), (48, 80, 56))
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
    - 读取由 per-run random profile 选出并在 static IR 中具体化的 `lhs/rhs/out` shape。
    - 以模块级 本次随机选中 静态 tile 做三维循环，输入维度均大于 tile 并覆盖尾块。
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
            acc = alloc([cur_m, cur_n], NumericType.Float32, MemorySpace.TSM)
            fill(acc, 0)
            bias_tile = alloc([cur_n], NumericType.Float32, MemorySpace.TSM)
            bias_full = alloc([cur_m, cur_n], NumericType.Float32, MemorySpace.TSM)
            for k0 in loop(0, k_size, tile_k):
                cur_k = min(tile_k, k_size - k0)
                lhs_tile = alloc([cur_m, cur_k], NumericType.Float32, MemorySpace.TSM)
                rhs_tile = alloc([cur_k, cur_n], NumericType.Float32, MemorySpace.TSM)
                fill(lhs_tile, 0)
                fill(rhs_tile, 0)
                lhs_region = view(lhs, [m0, k0], [cur_m, cur_k], [1, 1])
                rhs_region = view(rhs, [k0, n0], [cur_k, cur_n], [1, 1])
                deslice(lhs_tile, lhs_region, [0, 0], [cur_m, cur_k], [1, 1])
                deslice(rhs_tile, rhs_region, [0, 0], [cur_k, cur_n], [1, 1])
                partial = alloc([cur_m, cur_n], NumericType.Float32, MemorySpace.TSM)
                kernel.matmul(partial, lhs_tile, rhs_tile)
                kernel.add(acc, acc, partial)
            if bias is not None:
                bias_region = view(bias, [n0], [cur_n], [1])
                bias_row = reshape(bias_tile, [1, cur_n])
                fill(bias_tile, 0)
                deslice(bias_tile, bias_region, [0], [cur_n], [1])
                broadcast(bias_full, bias_row)
                kernel.add(acc, acc, bias_full)
            deslice(out, acc, [m0, n0], [cur_m, cur_n], [1, 1])


def main() -> None:
    """运行静态输入、静态 tile 的 matmul demo。


    功能说明:
    - 按 per-run random profile 构造真实 NumPy ndarray 输入。
    - static IR 中的 shape/tile 必须等于本轮 本次随机选中 值。
    - 调用公共 runner 执行 `dsl_run`，并写入 `kernel/dump/matmul/inputs_static_tile_static/`。
    - 分别用 `np.matmul(lhs, rhs)` 与 `np.matmul(lhs, rhs) + bias[None, :]` 校验输出。

    使用示例:
    - `python3 kernel/matmul/inputs_static_tile_static.py`
    """

    global _STATIC_SHAPE_SEED, _STATIC_M, _STATIC_K, _STATIC_N
    global _TILE_SELECTION_SEED, _TILE_M, _TILE_N, _TILE_K

    system_rng = random.SystemRandom()
    for _attempt in range(128):
        shape_seed = system_rng.randrange(1, 2**31)
        tile_seed = system_rng.randrange(1, 2**31)
        shape_rng = random.Random(shape_seed)
        candidate_m = shape_rng.randint(160, 256)
        candidate_k = shape_rng.randint(160, 256)
        candidate_n = shape_rng.randint(160, 256)
        candidate_tile_m, candidate_tile_n, candidate_tile_k = random.Random(tile_seed).choice(_TILE_CANDIDATES)
        has_multi_tile = (
            candidate_m > candidate_tile_m
            and candidate_k > candidate_tile_k
            and candidate_n > candidate_tile_n
        )
        has_tail = (
            candidate_m % candidate_tile_m != 0
            and candidate_k % candidate_tile_k != 0
            and candidate_n % candidate_tile_n != 0
        )
        if has_multi_tile and has_tail:
            break
    else:
        raise RuntimeError("matmul static/static random profile failed to satisfy tile invariants")

    _STATIC_SHAPE_SEED = shape_seed
    _STATIC_M = candidate_m
    _STATIC_K = candidate_k
    _STATIC_N = candidate_n
    _TILE_SELECTION_SEED = tile_seed
    _TILE_M = candidate_tile_m
    _TILE_N = candidate_tile_n
    _TILE_K = candidate_tile_k
    matmul_inputs_static_tile_static_kernel.__annotations__.update(
        {
            "out": f"Tensor[f32, {_STATIC_M}, {_STATIC_N}]",
            "lhs": f"Tensor[f32, {_STATIC_M}, {_STATIC_K}]",
            "rhs": f"Tensor[f32, {_STATIC_K}, {_STATIC_N}]",
            "bias": f"Tensor[f32, {_STATIC_N}]",
        }
    )

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
        "profile=per-run-random static_ir=random-concrete "
        f"shape_seed={_STATIC_SHAPE_SEED} shape=(M={_STATIC_M},K={_STATIC_K},N={_STATIC_N}) "
        f"tile_seed={_TILE_SELECTION_SEED} tile_candidates={_TILE_CANDIDATES} "
        f"selected_tile=(M={_TILE_M},N={_TILE_N},K={_TILE_K}) "
        f"bias_case_order={_BIAS_CASE_ORDER} multi_tile=True tail=True bias_rank=1"
    )
    print(f"[CHECK] {absent_result.case_name} max_abs_diff={absent_result.max_abs_diff}")
    print(f"[CHECK] {present_result.case_name} max_abs_diff={present_result.max_abs_diff}")


if __name__ == "__main__":
    main()
