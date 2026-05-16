"""Flash attention demo with static inputs and dynamic tiles.


功能说明:
- 实现 `inputs 静 + tile 动` 的 Flash Attention kernel demo。
- 输入 shape 由固定 seed `2026051622` 随机生成并固化为具体数字：`Q/K/V/out[1, 8, 389, 98]`。
- tile 由 `br/bc` runtime `SymbolDim` 参数绑定，序列长度大于两类 tile 并覆盖 query/key 尾块。
- 使用四层循环 `batch -> head -> query block -> key/value block` 实现 online softmax。
- softmax 显式展开为 running max、running sum、`kernel.exp` 与归一化，不调用 `nn.softmax`。
- 通过 `dsl_run` 真实执行，并和 NumPy softmax attention 参考结果对齐。

API 列表:
- `flash_attention_inputs_static_tile_dynamic_kernel(out: Tensor[f32, 1, 8, 389, 98], q: Tensor[f32, 1, 8, 389, 98], k: Tensor[f32, 1, 8, 389, 98], v: Tensor[f32, 1, 8, 389, 98], br: SymbolDim, bc: SymbolDim) -> None`
- `main() -> None`

使用示例:
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 kernel/flash_attention/inputs_static_tile_dynamic.py`

关联文件:
- 功能实现: `kernel/flash_attention/inputs_static_tile_dynamic.py`
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
from kernel_gen.operation.nn import transpose
from kernel_gen.operation.scf import loop
from kernel_gen.symbol_variable.memory import MemorySpace
from kernel_gen.symbol_variable.symbol_dim import SymbolDim
from kernel_gen.symbol_variable.type import NumericType

_STATIC_SHAPE_SEED = 2026051622
_STATIC_SHAPE_RNG = random.Random(_STATIC_SHAPE_SEED)
_STATIC_SEQ_LEN_CHOICES = (257, 321, 389, 449, 511)
_STATIC_BATCH = _STATIC_SHAPE_RNG.randint(1, 2)
_STATIC_HEADS = _STATIC_SHAPE_RNG.randint(8, 12)
_STATIC_SEQ_LEN = _STATIC_SEQ_LEN_CHOICES[_STATIC_SHAPE_RNG.randrange(len(_STATIC_SEQ_LEN_CHOICES))]
_STATIC_DIM = _STATIC_SHAPE_RNG.randint(32, 128)
_RUNTIME_TILE_ARGS = (64, 64)


def _softmax_last_axis(value: np.ndarray) -> np.ndarray:
    """计算最后一维 softmax。


    功能说明:
    - 使用 max-shift 形式提升 NumPy 参考值稳定性。
    - 只服务本 demo 的 reference 计算，不新增跨文件 helper。

    使用示例:
    - `_softmax_last_axis(scores)`
    """

    shifted = value - np.max(value, axis=-1, keepdims=True)
    exp_value = np.exp(shifted).astype(np.float32)
    return exp_value / np.sum(exp_value, axis=-1, keepdims=True)


def _flash_attention_reference(q: np.ndarray, k: np.ndarray, v: np.ndarray) -> np.ndarray:
    """计算 Flash Attention NumPy 参考输出。


    功能说明:
    - 参考语义固定为 `softmax(q @ k^T) @ v`。
    - 输入布局为 `[B, H, SL, D]`。

    使用示例:
    - `_flash_attention_reference(q, k, v)`
    """

    score = np.matmul(q, np.swapaxes(k, -1, -2))
    return np.matmul(_softmax_last_axis(score), v).astype(np.float32)


def flash_attention_inputs_static_tile_dynamic_kernel(
    out: "Tensor[f32, 1, 8, 389, 98]",
    q: "Tensor[f32, 1, 8, 389, 98]",
    k: "Tensor[f32, 1, 8, 389, 98]",
    v: "Tensor[f32, 1, 8, 389, 98]",
    br: SymbolDim,
    bc: SymbolDim,
) -> None:
    """执行静态输入、动态 tile 的 Flash Attention。


    功能说明:
    - 输入 shape 固定为固定 seed 生成并固化的具体数字。
    - `br/bc` 使用 runtime scalar 作为 query block 与 key/value block 两层分块大小。
    - 主计算入口使用 kernel out-first helper，softmax 以 running max/running sum online 形式展开。
    - 输出写回 `out[B, H, SL, D]`。

    使用示例:
    - `flash_attention_inputs_static_tile_dynamic_kernel(out, q, k, v, 64, 64)`
    """

    batch_size, head_size, seq_len, dim_size = q.get_shape()
    unit_tile = br - br + 1
    pair_tile = unit_tile + unit_tile
    for b0 in loop(0, batch_size, 1):
        for h0 in loop(0, head_size, 1):
            for m0 in loop(0, seq_len, br):
                cur_br = min(br, seq_len - m0)
                q_full_4d = alloc([1, 1, br, dim_size], NumericType.Float32, MemorySpace.TSM)
                fill(q_full_4d, 0)
                q_4d = view(q, [b0, h0, m0, 0], [1, 1, cur_br, dim_size], [1, 1, 1, 1])
                deslice(q_full_4d, q_4d, [0, 0, 0, 0], [1, 1, cur_br, dim_size], [1, 1, 1, 1])
                q_full = reshape(q_full_4d, [br, dim_size])
                m_state = alloc([br, unit_tile], NumericType.Float32, MemorySpace.TSM)
                sum_state = alloc([br, unit_tile], NumericType.Float32, MemorySpace.TSM)
                weighted = alloc([br, dim_size], NumericType.Float32, MemorySpace.TSM)
                fill(m_state, "-inf")
                fill(sum_state, 0)
                fill(weighted, 0)
                for n0 in loop(0, seq_len, bc):
                    cur_bc = min(bc, seq_len - n0)
                    k_full_4d = alloc([1, 1, bc, dim_size], NumericType.Float32, MemorySpace.TSM)
                    fill(k_full_4d, 0)
                    k_4d = view(k, [b0, h0, n0, 0], [1, 1, cur_bc, dim_size], [1, 1, 1, 1])
                    deslice(k_full_4d, k_4d, [0, 0, 0, 0], [1, 1, cur_bc, dim_size], [1, 1, 1, 1])
                    k_full = reshape(k_full_4d, [bc, dim_size])
                    k_transposed = transpose(k_full, [1, 0])
                    matmul_score = alloc([br, bc], NumericType.Float32, MemorySpace.TSM)
                    kernel.matmul(matmul_score, q_full, k_transposed)
                    score_tile = alloc([br, bc], NumericType.Float32, MemorySpace.TSM)
                    fill(score_tile, "-inf")
                    score_region = view(matmul_score, [0, 0], [cur_br, cur_bc], [1, 1])
                    deslice(score_tile, score_region, [0, 0], [cur_br, cur_bc], [1, 1])
                    tile_max = alloc([br, unit_tile], NumericType.Float32, MemorySpace.TSM)
                    kernel.reduce(tile_max, score_tile, kind=kernel.KernelReduceKind.MAX, axis=1, keepdim=True)
                    max_pair = alloc([br, pair_tile], NumericType.Float32, MemorySpace.TSM)
                    deslice(max_pair, m_state, [0, 0], [br, unit_tile], [1, 1])
                    deslice(max_pair, tile_max, [0, unit_tile], [br, unit_tile], [1, 1])
                    m_next = alloc([br, unit_tile], NumericType.Float32, MemorySpace.TSM)
                    kernel.reduce(m_next, max_pair, kind=kernel.KernelReduceKind.MAX, axis=1, keepdim=True)
                    m_next_full = alloc([br, bc], NumericType.Float32, MemorySpace.TSM)
                    broadcast(m_next_full, m_next)
                    shifted_score = alloc([br, bc], NumericType.Float32, MemorySpace.TSM)
                    kernel.sub(shifted_score, score_tile, m_next_full)
                    exp_score = alloc([br, bc], NumericType.Float32, MemorySpace.TSM)
                    kernel.exp(exp_score, shifted_score)
                    tile_sum = alloc([br, unit_tile], NumericType.Float32, MemorySpace.TSM)
                    kernel.reduce(tile_sum, exp_score, kind=kernel.KernelReduceKind.SUM, axis=1, keepdim=True)
                    old_shift = alloc([br, unit_tile], NumericType.Float32, MemorySpace.TSM)
                    kernel.sub(old_shift, m_state, m_next)
                    old_scale = alloc([br, unit_tile], NumericType.Float32, MemorySpace.TSM)
                    kernel.exp(old_scale, old_shift)
                    scaled_sum = alloc([br, unit_tile], NumericType.Float32, MemorySpace.TSM)
                    kernel.mul(scaled_sum, sum_state, old_scale)
                    sum_next = alloc([br, unit_tile], NumericType.Float32, MemorySpace.TSM)
                    kernel.add(sum_next, scaled_sum, tile_sum)
                    v_full_4d = alloc([1, 1, bc, dim_size], NumericType.Float32, MemorySpace.TSM)
                    fill(v_full_4d, 0)
                    v_4d = view(v, [b0, h0, n0, 0], [1, 1, cur_bc, dim_size], [1, 1, 1, 1])
                    deslice(v_full_4d, v_4d, [0, 0, 0, 0], [1, 1, cur_bc, dim_size], [1, 1, 1, 1])
                    v_full = reshape(v_full_4d, [bc, dim_size])
                    partial = alloc([br, dim_size], NumericType.Float32, MemorySpace.TSM)
                    kernel.matmul(partial, exp_score, v_full)
                    old_scale_full = alloc([br, dim_size], NumericType.Float32, MemorySpace.TSM)
                    broadcast(old_scale_full, old_scale)
                    scaled_weighted = alloc([br, dim_size], NumericType.Float32, MemorySpace.TSM)
                    kernel.mul(scaled_weighted, weighted, old_scale_full)
                    weighted_next = alloc([br, dim_size], NumericType.Float32, MemorySpace.TSM)
                    kernel.add(weighted_next, scaled_weighted, partial)
                    deslice(m_state, m_next, [0, 0], [br, unit_tile], [1, 1])
                    deslice(sum_state, sum_next, [0, 0], [br, unit_tile], [1, 1])
                    deslice(weighted, weighted_next, [0, 0], [br, dim_size], [1, 1])
                sum_full = alloc([br, dim_size], NumericType.Float32, MemorySpace.TSM)
                broadcast(sum_full, sum_state)
                output_tile = alloc([br, dim_size], NumericType.Float32, MemorySpace.TSM)
                kernel.truediv(output_tile, weighted, sum_full)
                output_region = view(output_tile, [0, 0], [cur_br, dim_size], [1, 1])
                o_4d = reshape(output_region, [1, 1, cur_br, dim_size])
                deslice(out, o_4d, [b0, h0, m0, 0], [1, 1, cur_br, dim_size], [1, 1, 1, 1])


def main() -> None:
    """运行静态输入、动态 tile 的 Flash Attention demo。


    功能说明:
    - 构造真实 NumPy ndarray 输入。
    - 写入 `kernel/dump/flash_attention/inputs_static_tile_dynamic/`。
    - 用 NumPy softmax attention 参考结果校验输出。

    使用示例:
    - `python3 kernel/flash_attention/inputs_static_tile_dynamic.py`
    """

    rng = np.random.default_rng(_STATIC_SHAPE_SEED)
    q = rng.standard_normal((_STATIC_BATCH, _STATIC_HEADS, _STATIC_SEQ_LEN, _STATIC_DIM), dtype=np.float32)
    k = rng.standard_normal((_STATIC_BATCH, _STATIC_HEADS, _STATIC_SEQ_LEN, _STATIC_DIM), dtype=np.float32)
    v = rng.standard_normal((_STATIC_BATCH, _STATIC_HEADS, _STATIC_SEQ_LEN, _STATIC_DIM), dtype=np.float32)
    out = np.empty((_STATIC_BATCH, _STATIC_HEADS, _STATIC_SEQ_LEN, _STATIC_DIM), dtype=np.float32)
    expected = _flash_attention_reference(q, k, v)
    result = run_numpy_demo(
        "flash_attention/inputs_static_tile_dynamic",
        flash_attention_inputs_static_tile_dynamic_kernel,
        (out, q, k, v, *_RUNTIME_TILE_ARGS),
        out,
        expected,
    )
    print(result.dsl_result.module)
    print(result.dsl_result.source)
    print(
        "[ARGS] "
        f"seed={_STATIC_SHAPE_SEED} shape={q.shape} tile={_RUNTIME_TILE_ARGS} "
        f"query_tiles={(_STATIC_SEQ_LEN + _RUNTIME_TILE_ARGS[0] - 1) // _RUNTIME_TILE_ARGS[0]} "
        f"key_tiles={(_STATIC_SEQ_LEN + _RUNTIME_TILE_ARGS[1] - 1) // _RUNTIME_TILE_ARGS[1]} "
        f"query_tail={_STATIC_SEQ_LEN % _RUNTIME_TILE_ARGS[0]} key_tail={_STATIC_SEQ_LEN % _RUNTIME_TILE_ARGS[1]} "
        f"multi_tile={_STATIC_SEQ_LEN > _RUNTIME_TILE_ARGS[0] and _STATIC_SEQ_LEN > _RUNTIME_TILE_ARGS[1]} "
        f"tail={_STATIC_SEQ_LEN % _RUNTIME_TILE_ARGS[0] != 0 or _STATIC_SEQ_LEN % _RUNTIME_TILE_ARGS[1] != 0} "
        "loops=batch/head/query/key online_softmax=True"
    )
    print(f"[CHECK] {result.case_name} max_abs_diff={result.max_abs_diff}")


if __name__ == "__main__":
    main()
