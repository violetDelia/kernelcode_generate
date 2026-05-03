"""Conv2d demo with static inputs and dynamic tiles.


功能说明:
- 实现 `inputs 静 + tile 动` 的 NCHW conv2d kernel demo。
- 输入固定为 `input[12, 32, 256, 256]`、`weight[4, 32, 3, 3]`、`out[12, 4, 254, 254]`。
- tile 由 `run_torch_demo(...)` 以 `int` runtime scalar 传入，尾块通过 DSL `min(...)` 生成 `symbol.min`。
- 当 `tile_c < C` 时在 `c0` tile 循环内对同一个输出 tile 做 C 维累计和，而不是拆成固定两段 matmul 后相加。
- 通过 `dsl_run` 真实执行，并和 `torch.nn.functional.conv2d` 参考结果对齐。

API 列表:
- `conv2d_inputs_static_tile_dynamic_kernel(out: Tensor[f32, 12, 4, 254, 254], input_tensor: Tensor[f32, 12, 32, 256, 256], weight: Tensor[f32, 4, 32, 3, 3], tile_f: SymbolDim, tile_c: SymbolDim, tile_n: SymbolDim, tile_ho: SymbolDim, tile_wo: SymbolDim) -> None`
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
from kernel_gen.operation.dma import deslice, fill, reshape, slice
from kernel_gen.operation.nn import add, img2col2d, matmul, transpose
from kernel_gen.operation.scf import loop
from kernel_gen.symbol_variable.memory import MemorySpace
from kernel_gen.symbol_variable.symbol_dim import SymbolDim


def conv2d_inputs_static_tile_dynamic_kernel(
    out: "Tensor[f32, 12, 4, 254, 254]",
    input_tensor: "Tensor[f32, 12, 32, 256, 256]",
    weight: "Tensor[f32, 4, 32, 3, 3]",
    tile_f: SymbolDim,
    tile_c: SymbolDim,
    tile_n: SymbolDim,
    tile_ho: SymbolDim,
    tile_wo: SymbolDim,
) -> None:
    """执行静态输入、动态 tile 的 conv2d。


    功能说明:
    - 输入 shape 固定，tile shape 由 runtime scalar 绑定。
    - 固定 stride=1、dilation=1、padding=0。
    - 使用 `img2col2d + matmul` 生成卷积主体，并按 `tile_c` 循环分块后累计所有 partial。

    使用示例:
    - `conv2d_inputs_static_tile_dynamic_kernel(out, input_tensor, weight, 2, 16, 1, 64, 64)`
    """

    n_size, c_size, h_size, w_size = input_tensor.shape.get_shape()
    f_size = weight.shape.get_shape()[0]
    kh_size = weight.shape.get_shape()[2]
    kw_size = weight.shape.get_shape()[3]
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

    fill(out, 0)
    for f0 in loop(0, f_size, tile_f):
        for n0 in loop(0, n_size, tile_n):
            for ho0 in loop(0, ho_size, tile_ho):
                for wo0 in loop(0, wo_size, tile_wo):
                    cur_f = min(tile_f, f_size - f0)
                    cur_n = min(tile_n, n_size - n0)
                    cur_ho = min(tile_ho, ho_size - ho0)
                    cur_wo = min(tile_wo, wo_size - wo0)
                    out_tile = cur_n * cur_ho * cur_wo
                    input_h_tile = (cur_ho - 1) * stride_h + (kh_size - 1) * dilation_h + 1 - pad_top - pad_bottom
                    input_w_tile = (cur_wo - 1) * stride_w + (kw_size - 1) * dilation_w + 1 - pad_left - pad_right
                    for c0 in loop(0, c_size, tile_c):
                        cur_c = min(tile_c, c_size - c0)
                        k_tile = cur_c * kh_size * kw_size
                        input_tile = slice(input_tensor, [n0, c0, ho0 * stride_h, wo0 * stride_w], [cur_n, cur_c, input_h_tile, input_w_tile], [1, 1, 1, 1], MemorySpace.TSM)
                        weight_tile = slice(weight, [f0, c0, 0, 0], [cur_f, cur_c, kh_size, kw_size], [1, 1, 1, 1], MemorySpace.TSM)
                        col = img2col2d(input_tile, kh=kh_size, kw=kw_size, sh=stride_h, sw=stride_w, dh=dilation_h, dw=dilation_w, ph=pad_top, pw=pad_bottom, pl=pad_left, pr=pad_right)
                        col2 = reshape(col, [k_tile, out_tile])
                        weight2 = reshape(weight_tile, [cur_f, k_tile])
                        out2 = matmul(weight2, col2)
                        out_fnhw = reshape(out2, [cur_f, cur_n, cur_ho, cur_wo])
                        deslice(
                            out,
                            add(
                                slice(out, [n0, f0, ho0, wo0], [cur_n, cur_f, cur_ho, cur_wo], [1, 1, 1, 1], MemorySpace.TSM),
                                transpose(out_fnhw, [1, 0, 2, 3]),
                            ),
                            [n0, f0, ho0, wo0],
                            [cur_n, cur_f, cur_ho, cur_wo],
                            [1, 1, 1, 1],
                        )


def main() -> None:
    """运行静态输入、动态 tile 的 conv2d demo。


    功能说明:
    - 构造真实 torch tensor 输入。
    - 写入 `kernel/dump/conv2d/inputs_static_tile_dynamic/`。
    - 用 `torch.nn.functional.conv2d` 校验输出。

    使用示例:
    - `python3 kernel/conv2d/inputs_static_tile_dynamic.py`
    """

    generator = torch.Generator().manual_seed(20260503)
    input_tensor = torch.randn((12, 32, 256, 256), generator=generator, dtype=torch.float32)
    weight = torch.randn((4, 32, 3, 3), generator=generator, dtype=torch.float32)
    out = torch.zeros((12, 4, 254, 254), dtype=torch.float32)
    expected = F.conv2d(input_tensor, weight)
    tile_args = (2, 16, 1, 64, 64)
    result = run_torch_demo(
        "conv2d/inputs_static_tile_dynamic",
        conv2d_inputs_static_tile_dynamic_kernel,
        (out, input_tensor, weight, *tile_args),
        out,
        expected,
    )
    print(result.dsl_result.module)
    print(result.dsl_result.source)
    print(f"[CHECK] {result.case_name} max_abs_diff={result.max_abs_diff}")


if __name__ == "__main__":
    main()
