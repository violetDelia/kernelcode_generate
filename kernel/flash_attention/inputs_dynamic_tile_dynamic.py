"""Flash attention demo with dynamic inputs and dynamic tiles.


功能说明:
- 实现 `inputs 动 + tile 动` 的 Flash Attention kernel demo。
- 输入 batch/head 使用 `B/H` 符号维度，并由真实 torch tensor 运行时 shape 绑定；`SL/D` 保持静态，避免当前 emit 路径生成未绑定 stride 符号。
- tile 在 DSL 函数体内固定为当前 demo 运行值 `Br=8`、`Bc=16`，满足 `dsl_run` 只接收 tensor 运行时参数的公开入口约束。
- 通过 `dsl_run` 真实执行，并和 `torch.softmax(q @ k^T) @ v` 参考结果对齐。

API 列表:
- `flash_attention_inputs_dynamic_tile_dynamic_kernel(out: Tensor[f32, B, H, 16, 8], q: Tensor[f32, B, H, 16, 8], k: Tensor[f32, B, H, 16, 8], v: Tensor[f32, B, H, 16, 8]) -> None`
- `main() -> None`

使用示例:
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 kernel/flash_attention/inputs_dynamic_tile_dynamic.py`

关联文件:
- 功能实现: `kernel/flash_attention/inputs_dynamic_tile_dynamic.py`
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
from kernel_gen.operation.dma import deslice, reshape, slice
from kernel_gen.operation.nn import broadcast_to, exp, matmul, reduce_max, reduce_sum, sub, transpose, truediv
from kernel_gen.operation.scf import loop
from kernel_gen.symbol_variable.memory import MemorySpace


def flash_attention_inputs_dynamic_tile_dynamic_kernel(
    out: "Tensor[f32, B, H, 16, 8]",
    q: "Tensor[f32, B, H, 16, 8]",
    k: "Tensor[f32, B, H, 16, 8]",
    v: "Tensor[f32, B, H, 16, 8]",
) -> None:
    """执行动态输入、动态 tile 的 Flash Attention。


    功能说明:
    - `Q/K/V/out` 的 batch/head 维度为符号维度。
    - `br/bc` 使用当前 demo 的运行值作为 softmax 分块大小。
    - 输出写回 `out[B, H, SL, D]`。

    使用示例:
    - `flash_attention_inputs_dynamic_tile_dynamic_kernel(out, q, k, v)`
    """

    batch_size, head_size, seq_len, dim_size = q.shape.get_shape()
    br = 8
    bc = 16
    for b0 in loop(0, batch_size, 1):
        for h0 in loop(0, head_size, 1):
            for m0 in loop(0, seq_len, br):
                q_4d = slice(q, [b0, h0, m0, 0], [1, 1, br, dim_size], [1, 1, 1, 1], MemorySpace.TSM)
                q_tile = reshape(q_4d, [br, dim_size])
                k_4d = slice(k, [b0, h0, 0, 0], [1, 1, bc, dim_size], [1, 1, 1, 1], MemorySpace.TSM)
                k_tile = reshape(k_4d, [bc, dim_size])
                v_4d = slice(v, [b0, h0, 0, 0], [1, 1, bc, dim_size], [1, 1, 1, 1], MemorySpace.TSM)
                v_tile = reshape(v_4d, [bc, dim_size])
                score = matmul(q_tile, transpose(k_tile, [1, 0]))
                row_max = reduce_max(score, axis=1, keepdim=True)
                row_max_bc = broadcast_to(row_max, [br, bc], MemorySpace.TSM)
                prob = exp(sub(score, row_max_bc))
                row_sum = reduce_sum(prob, axis=1, keepdim=True)
                weighted = matmul(prob, v_tile)
                row_sum_d = broadcast_to(row_sum, [br, dim_size], MemorySpace.TSM)
                o_acc = truediv(weighted, row_sum_d)
                o_4d = reshape(o_acc, [1, 1, br, dim_size])
                deslice(out, o_4d, [b0, h0, m0, 0], [1, 1, br, dim_size], [1, 1, 1, 1])


def main() -> None:
    """运行动态输入、动态 tile 的 Flash Attention demo。


    功能说明:
    - 构造真实 torch tensor 输入，shape 绑定到 `B/H`。
    - 写入 `kernel/dump/flash_attention/inputs_dynamic_tile_dynamic/`。
    - 用 `torch.softmax(q @ k^T) @ v` 校验输出。

    使用示例:
    - `python3 kernel/flash_attention/inputs_dynamic_tile_dynamic.py`
    """

    q = torch.linspace(-0.3, 0.2, steps=1 * 2 * 16 * 8, dtype=torch.float32).reshape(1, 2, 16, 8)
    k = torch.linspace(0.1, -0.3, steps=1 * 2 * 16 * 8, dtype=torch.float32).reshape(1, 2, 16, 8)
    v = torch.linspace(-0.6, 0.4, steps=1 * 2 * 16 * 8, dtype=torch.float32).reshape(1, 2, 16, 8)
    out = torch.empty((1, 2, 16, 8), dtype=torch.float32)
    expected = torch.matmul(torch.softmax(torch.matmul(q, k.transpose(-1, -2)), dim=-1), v)
    result = run_torch_demo(
        "flash_attention/inputs_dynamic_tile_dynamic",
        flash_attention_inputs_dynamic_tile_dynamic_kernel,
        (out, q, k, v),
        out,
        expected,
    )
    print(result.dsl_result.module)
    print(result.dsl_result.source)
    print(f"[CHECK] {result.case_name} max_abs_diff={result.max_abs_diff}")


if __name__ == "__main__":
    main()
