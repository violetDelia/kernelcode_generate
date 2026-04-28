"""Flash attention demo with dynamic inputs and dynamic tiles.

创建者: 大闸蟹
最后一次更改: 大闸蟹

功能说明:
- 实现 `inputs 动 + tile 动` 的 Flash Attention kernel demo。
- 输入 shape 使用 `B/H/SL/D` 符号维度。
- `br/bc` 作为动态 tile 符号参数传入。

API 列表:
- `flash_attention_inputs_dynamic_tile_dynamic_kernel(q: Memory, k: Memory, v: Memory, out: Memory, br: SymbolDim, bc: SymbolDim) -> None`
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

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from kernel.runner import run_lowering_demo
from kernel_gen.operation.dma import alloc, deslice, fill, reshape, slice
from kernel_gen.operation.nn import add, broadcast_to, exp, matmul, mul, reduce_max, reduce_sum, sub, transpose, truediv
from kernel_gen.operation.scf import loop
from kernel_gen.symbol_variable.memory import Memory, MemorySpace
from kernel_gen.symbol_variable.symbol_dim import SymbolDim
from kernel_gen.symbol_variable.type import NumericType


def flash_attention_inputs_dynamic_tile_dynamic_kernel(
    q: Memory,
    k: Memory,
    v: Memory,
    out: Memory,
    br: SymbolDim,
    bc: SymbolDim,
) -> None:
    """执行动态输入、动态 tile 的 Flash Attention。

    创建者: 大闸蟹
    最后一次更改: 大闸蟹

    功能说明:
    - `Q/K/V/out` 的 shape 均为符号维度。
    - `br/bc` 作为在线 softmax 分块大小。
    - 输出写回 `out[B, H, SL, D]`。

    使用示例:
    - `flash_attention_inputs_dynamic_tile_dynamic_kernel(q, k, v, out, br, bc)`
    """

    batch_size, head_size, seq_len, dim_size = q.shape.get_shape()
    dtype = q.dtype

    for b0 in loop(0, batch_size, 1):
        for h0 in loop(0, head_size, 1):
            for m0 in loop(0, seq_len, br):
                q_4d = slice(q, [b0, h0, m0, 0], [1, 1, br, dim_size], [1, 1, 1, 1], MemorySpace.TSM)
                q_tile = reshape(q_4d, [br, dim_size])
                o_acc = alloc([br, dim_size], dtype, MemorySpace.TSM)
                fill(o_acc, 0)
                m_acc = alloc([br, 1], dtype, MemorySpace.TSM)
                fill(m_acc, "-inf")
                l_acc = alloc([br, 1], dtype, MemorySpace.TSM)
                fill(l_acc, 0)

                for n0 in loop(0, seq_len, bc):
                    k_4d = slice(k, [b0, h0, n0, 0], [1, 1, bc, dim_size], [1, 1, 1, 1], MemorySpace.TSM)
                    k_tile = reshape(k_4d, [bc, dim_size])
                    v_4d = slice(v, [b0, h0, n0, 0], [1, 1, bc, dim_size], [1, 1, 1, 1], MemorySpace.TSM)
                    v_tile = reshape(v_4d, [bc, dim_size])
                    score = matmul(q_tile, transpose(k_tile, [1, 0]))
                    m_new = reduce_max(score, axis=1, keepdim=True)
                    alpha = exp(sub(m_acc, m_new))
                    m_bc = broadcast_to(m_new, [br, bc], MemorySpace.TSM)
                    prob = exp(sub(score, m_bc))
                    alpha_d = broadcast_to(alpha, [br, dim_size], MemorySpace.TSM)
                    o_acc = mul(o_acc, alpha_d)
                    l_acc = add(mul(l_acc, alpha), reduce_sum(prob, axis=1, keepdim=True))
                    m_acc = m_new
                    o_acc = add(o_acc, matmul(prob, v_tile))

                l_d = broadcast_to(l_acc, [br, dim_size], MemorySpace.TSM)
                o_acc = truediv(o_acc, l_d)
                o_4d = reshape(o_acc, [1, 1, br, dim_size])
                deslice(out, o_4d, [b0, h0, m0, 0], [1, 1, br, dim_size], [1, 1, 1, 1])


def main() -> None:
    """运行动态输入、动态 tile 的 Flash Attention demo。

    创建者: 大闸蟹
    最后一次更改: 大闸蟹

    功能说明:
    - 构造符号 `Q/K/V/out` 和动态 tile 符号。
    - 写入 `kernel/dump/flash_attention/inputs_dynamic_tile_dynamic/`。

    使用示例:
    - `python3 kernel/flash_attention/inputs_dynamic_tile_dynamic.py`
    """

    q = Memory(["B", "H", "SL", "D"], NumericType.Float32, space=MemorySpace.GM)
    k = Memory(["B", "H", "SL", "D"], NumericType.Float32, space=MemorySpace.GM)
    v = Memory(["B", "H", "SL", "D"], NumericType.Float32, space=MemorySpace.GM)
    out = Memory(["B", "H", "SL", "D"], NumericType.Float32, space=MemorySpace.GM)
    br = SymbolDim("BR")
    bc = SymbolDim("BC")
    module, source = run_lowering_demo(
        "flash_attention/inputs_dynamic_tile_dynamic",
        flash_attention_inputs_dynamic_tile_dynamic_kernel,
        q,
        k,
        v,
        out,
        br,
        bc,
    )
    print(module)
    print(source)


if __name__ == "__main__":
    main()
