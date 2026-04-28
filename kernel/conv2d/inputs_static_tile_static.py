"""Conv2d demo with static inputs and static tiles.

创建者: 大闸蟹
最后一次更改: 大闸蟹

功能说明:
- 实现 `inputs 静 + tile 静` 的 NCHW conv2d kernel demo。
- 使用 `img2col2d + matmul` 实现卷积。
- 输入固定为 `input[1, 3, 8, 8]`、`weight[4, 3, 3, 3]`、`out[1, 4, 6, 6]`。

API 列表:
- `conv2d_inputs_static_tile_static_kernel(input: Memory, weight: Memory, out: Memory) -> None`
- `main() -> None`

使用示例:
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 kernel/conv2d/inputs_static_tile_static.py`

关联文件:
- 功能实现: `kernel/conv2d/inputs_static_tile_static.py`
- 公共运行器: `kernel/runner.py`
"""

from __future__ import annotations

import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from kernel.runner import run_lowering_demo
from kernel_gen.operation.dma import deslice, reshape, slice
from kernel_gen.operation.nn import img2col2d, matmul, transpose
from kernel_gen.operation.scf import loop
from kernel_gen.symbol_variable.memory import Memory, MemorySpace
from kernel_gen.symbol_variable.type import NumericType


def conv2d_inputs_static_tile_static_kernel(input: Memory, weight: Memory, out: Memory) -> None:
    """执行静态输入、静态 tile 的 conv2d。

    创建者: 大闸蟹
    最后一次更改: 大闸蟹

    功能说明:
    - 输入布局为 `input[N, C, H, W]`，权重布局为 `weight[F, C, KH, KW]`，输出布局为 `out[N, F, Ho, Wo]`。
    - 固定 stride=1、dilation=1、padding=0。
    - 固定 tile 为 `TF=2, TC=3, TN=1, THO=3, TWO=3`。

    使用示例:
    - `conv2d_inputs_static_tile_static_kernel(input, weight, out)`
    """

    n_size, c_size, h_size, w_size = input.shape.get_shape()
    f_size = weight.shape.get_shape()[0]
    kh_size = weight.shape.get_shape()[2]
    kw_size = weight.shape.get_shape()[3]
    tile_f = 2
    tile_c = 3
    tile_n = 1
    tile_ho = 3
    tile_wo = 3
    stride_h = 1
    stride_w = 1
    dilation_h = 1
    dilation_w = 1
    pad_top = 0
    pad_bottom = 0
    pad_left = 0
    pad_right = 0
    ho_size = ((h_size + pad_top + pad_bottom - dilation_h * (kh_size - 1) - 1) // stride_h) + 1
    wo_size = ((w_size + pad_left + pad_right - dilation_w * (kw_size - 1) - 1) // stride_w) + 1
    k_tile = tile_c * kh_size * kw_size
    out_tile = tile_n * tile_ho * tile_wo
    input_h_tile = (tile_ho - 1) * stride_h + (kh_size - 1) * dilation_h + 1 - pad_top - pad_bottom
    input_w_tile = (tile_wo - 1) * stride_w + (kw_size - 1) * dilation_w + 1 - pad_left - pad_right

    for f0 in loop(0, f_size, tile_f):
        for c0 in loop(0, c_size, tile_c):
            for n0 in loop(0, n_size, tile_n):
                for ho0 in loop(0, ho_size, tile_ho):
                    for wo0 in loop(0, wo_size, tile_wo):
                        input_tile = slice(
                            input,
                            [n0, c0, ho0 * stride_h, wo0 * stride_w],
                            [tile_n, tile_c, input_h_tile, input_w_tile],
                            [1, 1, 1, 1],
                            MemorySpace.TSM,
                        )
                        weight_tile = slice(weight, [f0, c0, 0, 0], [tile_f, tile_c, kh_size, kw_size], [1, 1, 1, 1], MemorySpace.TSM)
                        col = img2col2d(input_tile, kh=kh_size, kw=kw_size, sh=stride_h, sw=stride_w, dh=dilation_h, dw=dilation_w, ph=pad_top, pw=pad_bottom, pl=pad_left, pr=pad_right)
                        col2 = reshape(col, [k_tile, out_tile])
                        weight2 = reshape(weight_tile, [tile_f, k_tile])
                        out2 = matmul(weight2, col2)
                        out_fnhw = reshape(out2, [tile_f, tile_n, tile_ho, tile_wo])
                        out_tile_mem = transpose(out_fnhw, [1, 0, 2, 3])
                        deslice(out, out_tile_mem, [n0, f0, ho0, wo0], [tile_n, tile_f, tile_ho, tile_wo], [1, 1, 1, 1])


def main() -> None:
    """运行静态输入、静态 tile 的 conv2d demo。

    创建者: 大闸蟹
    最后一次更改: 大闸蟹

    功能说明:
    - 构造静态卷积输入。
    - 写入 `kernel/dump/conv2d/inputs_static_tile_static/`。

    使用示例:
    - `python3 kernel/conv2d/inputs_static_tile_static.py`
    """

    input_mem = Memory([1, 3, 8, 8], NumericType.Float32, space=MemorySpace.GM)
    weight = Memory([4, 3, 3, 3], NumericType.Float32, space=MemorySpace.GM)
    out = Memory([1, 4, 6, 6], NumericType.Float32, space=MemorySpace.GM)
    module, source = run_lowering_demo(
        "conv2d/inputs_static_tile_static",
        conv2d_inputs_static_tile_static_kernel,
        input_mem,
        weight,
        out,
    )
    print(module)
    print(source)


if __name__ == "__main__":
    main()
