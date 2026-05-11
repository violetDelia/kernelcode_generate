"""Flash attention demo with static inputs and dynamic tiles.


功能说明:
- 实现 `inputs 静 + tile 动` 的 Flash Attention kernel demo。
- 输入固定为 `Q/K/V/out[4, 4, 8, 4]`，避免过小 batch/head shape 且保持 npu_demo TSM 容量安全。
- tile 由 `br/bc` runtime `SymbolDim` 参数绑定，示例运行值为 `Br=4`、`Bc=8`。
- softmax 显式展开为 `kernel.reduce + dma.broadcast + kernel.exp + kernel.truediv`，不调用 `nn.softmax`。
- 通过 `dsl_run` 真实执行，并和 `torch.softmax(q @ k^T) @ v` 参考结果对齐。

API 列表:
- `flash_attention_inputs_static_tile_dynamic_kernel(out: Tensor[f32, 4, 4, 8, 4], q: Tensor[f32, 4, 4, 8, 4], k: Tensor[f32, 4, 4, 8, 4], v: Tensor[f32, 4, 4, 8, 4], br: SymbolDim, bc: SymbolDim) -> None`
- `main() -> None`

使用示例:
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 kernel/flash_attention/inputs_static_tile_dynamic.py`

关联文件:
- 功能实现: `kernel/flash_attention/inputs_static_tile_dynamic.py`
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
from kernel_gen.operation.dma import alloc, broadcast, deslice, reshape, slice
from kernel_gen.operation.nn import transpose
from kernel_gen.operation.scf import loop
from kernel_gen.symbol_variable.memory import MemorySpace
from kernel_gen.symbol_variable.symbol_dim import SymbolDim
from kernel_gen.symbol_variable.type import NumericType


def flash_attention_inputs_static_tile_dynamic_kernel(
    out: "Tensor[f32, 4, 4, 8, 4]",
    q: "Tensor[f32, 4, 4, 8, 4]",
    k: "Tensor[f32, 4, 4, 8, 4]",
    v: "Tensor[f32, 4, 4, 8, 4]",
    br: SymbolDim,
    bc: SymbolDim,
) -> None:
    """执行静态输入、动态 tile 的 Flash Attention。


    功能说明:
    - 输入 shape 固定。
    - `br/bc` 使用 runtime scalar 作为 softmax 分块大小。
    - 主计算入口使用 kernel out-first helper，softmax 展开为 reduce/broadcast/exp/truediv。
    - 输出写回 `out[B, H, SL, D]`。

    使用示例:
    - `flash_attention_inputs_static_tile_dynamic_kernel(out, q, k, v, 4, 8)`
    """

    batch_size, head_size, seq_len, _dim_size = q.get_shape()
    dim_size = 4
    dim_tile = br - br + dim_size
    keepdim_tile = br - br + 1
    for b0 in loop(0, batch_size, 1):
        for h0 in loop(0, head_size, 1):
            for m0 in loop(0, seq_len, br):
                q_4d = slice(q, [b0, h0, m0, 0], [1, 1, br, dim_size], [1, 1, 1, 1], MemorySpace.TSM)
                q_tile = reshape(q_4d, [br, dim_size])
                k_4d = slice(k, [b0, h0, 0, 0], [1, 1, bc, dim_size], [1, 1, 1, 1], MemorySpace.TSM)
                k_tile = reshape(k_4d, [bc, dim_size])
                v_4d = slice(v, [b0, h0, 0, 0], [1, 1, bc, dim_size], [1, 1, 1, 1], MemorySpace.TSM)
                v_tile = reshape(v_4d, [bc, dim_size])
                k_transposed = transpose(k_tile, [1, 0])
                score = alloc([br, bc], NumericType.Float32, MemorySpace.TSM)
                kernel.matmul(score, q_tile, k_transposed)
                row_max = alloc([br, keepdim_tile], NumericType.Float32, MemorySpace.TSM)
                kernel.reduce(row_max, score, kind=kernel.KernelReduceKind.MAX, axis=1, keepdim=True)
                row_max_full = alloc([br, bc], NumericType.Float32, MemorySpace.TSM)
                broadcast(row_max_full, row_max)
                shifted_score = alloc([br, bc], NumericType.Float32, MemorySpace.TSM)
                kernel.sub(shifted_score, score, row_max_full)
                exp_score = alloc([br, bc], NumericType.Float32, MemorySpace.TSM)
                kernel.exp(exp_score, shifted_score)
                row_sum = alloc([br, keepdim_tile], NumericType.Float32, MemorySpace.TSM)
                kernel.reduce(row_sum, exp_score, kind=kernel.KernelReduceKind.SUM, axis=1, keepdim=True)
                row_sum_full = alloc([br, bc], NumericType.Float32, MemorySpace.TSM)
                broadcast(row_sum_full, row_sum)
                prob = alloc([br, bc], NumericType.Float32, MemorySpace.TSM)
                kernel.truediv(prob, exp_score, row_sum_full)
                weighted = alloc([br, dim_tile], NumericType.Float32, MemorySpace.TSM)
                kernel.matmul(weighted, prob, v_tile)
                o_4d = reshape(weighted, [1, 1, br, dim_tile])
                deslice(out, o_4d, [b0, h0, m0, 0], [1, 1, br, dim_size], [1, 1, 1, 1])


def main() -> None:
    """运行静态输入、动态 tile 的 Flash Attention demo。


    功能说明:
    - 构造真实 torch tensor 输入。
    - 写入 `kernel/dump/flash_attention/inputs_static_tile_dynamic/`。
    - 用 `torch.softmax(q @ k^T) @ v` 校验输出。

    使用示例:
    - `python3 kernel/flash_attention/inputs_static_tile_dynamic.py`
    """

    q = torch.linspace(-0.2, 0.3, steps=4 * 4 * 8 * 4, dtype=torch.float32).reshape(4, 4, 8, 4)
    k = torch.linspace(0.3, -0.1, steps=4 * 4 * 8 * 4, dtype=torch.float32).reshape(4, 4, 8, 4)
    v = torch.linspace(-0.4, 0.6, steps=4 * 4 * 8 * 4, dtype=torch.float32).reshape(4, 4, 8, 4)
    out = torch.empty((4, 4, 8, 4), dtype=torch.float32)
    expected = torch.matmul(torch.softmax(torch.matmul(q, k.transpose(-1, -2)), dim=-1), v)
    result = run_torch_demo(
        "flash_attention/inputs_static_tile_dynamic",
        flash_attention_inputs_static_tile_dynamic_kernel,
        (out, q, k, v, 4, 8),
        out,
        expected,
    )
    print(result.dsl_result.module)
    print(result.dsl_result.source)
    print(f"[CHECK] {result.case_name} max_abs_diff={result.max_abs_diff}")


if __name__ == "__main__":
    main()
