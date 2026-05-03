"""Conv2d demo with static inputs and dynamic tiles.


功能说明:
- 实现 `inputs 静 + tile 动` 的 NCHW conv2d kernel demo。
- 输入固定为 `input[1, 3, 8, 8]`、`weight[4, 3, 3, 3]`、`out[1, 4, 6, 6]`。
- tile 在 DSL 函数体内固定为当前 demo 运行值，满足 `dsl_run` 只接收 tensor 运行时参数的公开入口约束。
- 通过 `dsl_run` 真实执行，并和 `torch.nn.functional.conv2d` 参考结果对齐。

API 列表:
- `conv2d_inputs_static_tile_dynamic_kernel(out: Tensor[f32, 1, 4, 6, 6], input_tensor: Tensor[f32, 1, 3, 8, 8], weight: Tensor[f32, 4, 3, 3, 3]) -> None`
- `main() -> None`

使用示例:
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 kernel/conv2d/inputs_static_tile_dynamic.py`

关联文件:
- 功能实现: `kernel/conv2d/inputs_static_tile_dynamic.py`
- 公共运行器: `kernel/runner.py`
"""

from __future__ import annotations

import sys
from pathlib import Path

import torch
import torch.nn.functional as F

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from kernel.runner import run_torch_demo
from kernel_gen.operation.dma import deslice, reshape, slice
from kernel_gen.operation.nn import img2col2d, matmul, transpose
from kernel_gen.operation.scf import loop
from kernel_gen.symbol_variable.memory import MemorySpace


def conv2d_inputs_static_tile_dynamic_kernel(
    out: "Tensor[f32, 1, 4, 6, 6]",
    input_tensor: "Tensor[f32, 1, 3, 8, 8]",
    weight: "Tensor[f32, 4, 3, 3, 3]",
) -> None:
    """执行静态输入、动态 tile 的 conv2d。


    功能说明:
    - 输入 shape 固定，tile shape 使用当前 demo 的运行值。
    - 固定 stride=1、dilation=1、padding=0。
    - 使用 `img2col2d + matmul` 生成卷积主体。

    使用示例:
    - `conv2d_inputs_static_tile_dynamic_kernel(out, input_tensor, weight)`
    """

    n_size, c_size, h_size, w_size = input_tensor.shape.get_shape()
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
                        input_tile = slice(input_tensor, [n0, c0, ho0 * stride_h, wo0 * stride_w], [tile_n, tile_c, input_h_tile, input_w_tile], [1, 1, 1, 1], MemorySpace.TSM)
                        weight_tile = slice(weight, [f0, c0, 0, 0], [tile_f, tile_c, kh_size, kw_size], [1, 1, 1, 1], MemorySpace.TSM)
                        col = img2col2d(input_tile, kh=kh_size, kw=kw_size, sh=stride_h, sw=stride_w, dh=dilation_h, dw=dilation_w, ph=pad_top, pw=pad_bottom, pl=pad_left, pr=pad_right)
                        col2 = reshape(col, [k_tile, out_tile])
                        weight2 = reshape(weight_tile, [tile_f, k_tile])
                        out2 = matmul(weight2, col2)
                        out_fnhw = reshape(out2, [tile_f, tile_n, tile_ho, tile_wo])
                        out_tile_mem = transpose(out_fnhw, [1, 0, 2, 3])
                        deslice(out, out_tile_mem, [n0, f0, ho0, wo0], [tile_n, tile_f, tile_ho, tile_wo], [1, 1, 1, 1])


def main() -> None:
    """运行静态输入、动态 tile 的 conv2d demo。


    功能说明:
    - 构造真实 torch tensor 输入。
    - 写入 `kernel/dump/conv2d/inputs_static_tile_dynamic/`。
    - 用 `torch.nn.functional.conv2d` 校验输出。

    使用示例:
    - `python3 kernel/conv2d/inputs_static_tile_dynamic.py`
    """

    input_tensor = torch.arange(1 * 3 * 8 * 8, dtype=torch.float32).reshape(1, 3, 8, 8) / 127.0
    weight = torch.arange(4 * 3 * 3 * 3, dtype=torch.float32).reshape(4, 3, 3, 3) / 131.0
    out = torch.empty((1, 4, 6, 6), dtype=torch.float32)
    expected = F.conv2d(input_tensor, weight)
    result = run_torch_demo(
        "conv2d/inputs_static_tile_dynamic",
        conv2d_inputs_static_tile_dynamic_kernel,
        (out, input_tensor, weight),
        out,
        expected,
    )
    print(result.dsl_result.module)
    print(result.dsl_result.source)
    print(f"[CHECK] {result.case_name} max_abs_diff={result.max_abs_diff}")


if __name__ == "__main__":
    main()
