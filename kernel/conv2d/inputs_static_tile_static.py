"""Conv2d demo with static inputs and static tiles.


功能说明:
- 实现 `inputs 静 + tile 静` 的 NCHW conv2d kernel demo。
- 使用 `img2col2d + matmul` 实现卷积，tile 尾块显式通过 DSL `min(...)` 收口。
- 输入尺寸由固定 seed `20260503` 生成并固化为具体数字：`input[11, 28, 260, 264]`、`weight[2, 28, 3, 3]`、`out[11, 2, 258, 262]`。
- lowering 后 IR 必须保持上述具体数字 static shape，不得变成动态符号 shape。
- 通过 `dsl_run` 真实执行，并和 `torch.nn.functional.conv2d` 参考结果对齐。

API 列表:
- `conv2d_inputs_static_tile_static_kernel(out: Tensor[f32, 11, 2, 258, 262], input_tensor: Tensor[f32, 11, 28, 260, 264], weight: Tensor[f32, 2, 28, 3, 3]) -> None`
- `main() -> None`

使用示例:
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 kernel/conv2d/inputs_static_tile_static.py`

关联文件:
- 功能实现: `kernel/conv2d/inputs_static_tile_static.py`
- 公共运行器: `kernel/runner.py`
"""

from __future__ import annotations

import random
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

_STATIC_SHAPE_SEED = 20260503
_STATIC_SHAPE_RNG = random.Random(_STATIC_SHAPE_SEED)
_STATIC_BATCH = _STATIC_SHAPE_RNG.randint(10, 14)
_STATIC_IN_CHANNELS = _STATIC_SHAPE_RNG.randint(28, 36)
_STATIC_INPUT_H = _STATIC_SHAPE_RNG.randint(248, 264)
_STATIC_INPUT_W = _STATIC_SHAPE_RNG.randint(248, 264)
_STATIC_OUT_CHANNELS = _STATIC_SHAPE_RNG.randint(2, 5)
_STATIC_KERNEL_H = 3
_STATIC_KERNEL_W = 3
_STATIC_OUTPUT_H = _STATIC_INPUT_H - _STATIC_KERNEL_H + 1
_STATIC_OUTPUT_W = _STATIC_INPUT_W - _STATIC_KERNEL_W + 1


def conv2d_inputs_static_tile_static_kernel(
    out: "Tensor[f32, 11, 2, 258, 262]",
    input_tensor: "Tensor[f32, 11, 28, 260, 264]",
    weight: "Tensor[f32, 2, 28, 3, 3]",
) -> None:
    """执行静态输入、静态 tile 的 conv2d。


    功能说明:
    - 输入布局为 `input[N, C, H, W]`，权重布局为 `weight[F, C, KH, KW]`，输出布局为 `out[N, F, Ho, Wo]`。
    - 输入 shape 为固定 seed 生成并固化的具体数字。
    - 固定 stride=1、dilation=1、padding=0。
    - 固定 tile 为 `TF=2, TC=2, TN=1, THO=1, TWO=7`，确保 memory_pool 后的片上动态内存视图不越过 npu_demo 目标容量。
    - 当 `TC < C` 时在 `c0` tile 循环内对同一个输出 tile 做 C 维累计和。

    使用示例:
    - `conv2d_inputs_static_tile_static_kernel(out, input_tensor, weight)`
    """

    n_size, c_size, h_size, w_size = input_tensor.get_shape()
    f_size = weight.get_shape()[0]
    kh_size = weight.get_shape()[2]
    kw_size = weight.get_shape()[3]
    tile_f = 2
    tile_c = 2
    tile_n = 1
    tile_ho = 1
    tile_wo = 7
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
        for c0 in loop(0, c_size, tile_c):
            for n0 in loop(0, n_size, tile_n):
                for ho0 in loop(0, ho_size, tile_ho):
                    for wo0 in loop(0, wo_size, tile_wo):
                        cur_f = min(tile_f, f_size - f0)
                        cur_c = min(tile_c, c_size - c0)
                        cur_n = min(tile_n, n_size - n0)
                        cur_ho = min(tile_ho, ho_size - ho0)
                        cur_wo = min(tile_wo, wo_size - wo0)
                        k_tile = cur_c * kh_size * kw_size
                        out_tile = cur_n * cur_ho * cur_wo
                        input_h_tile = (cur_ho - 1) * stride_h + (kh_size - 1) * dilation_h + 1 - pad_top - pad_bottom
                        input_w_tile = (cur_wo - 1) * stride_w + (kw_size - 1) * dilation_w + 1 - pad_left - pad_right
                        input_tile = slice(
                            input_tensor,
                            [n0, c0, ho0 * stride_h, wo0 * stride_w],
                            [cur_n, cur_c, input_h_tile, input_w_tile],
                            [1, 1, 1, 1],
                            MemorySpace.TSM,
                        )
                        weight_tile = slice(weight, [f0, c0, 0, 0], [cur_f, cur_c, kh_size, kw_size], [1, 1, 1, 1], MemorySpace.TSM)
                        col = img2col2d(input_tile, kh=kh_size, kw=kw_size, sh=stride_h, sw=stride_w, dh=dilation_h, dw=dilation_w, ph=pad_top, pw=pad_bottom, pl=pad_left, pr=pad_right)
                        col2 = reshape(col, [k_tile, out_tile])
                        weight2 = reshape(weight_tile, [cur_f, k_tile])
                        out2 = matmul(weight2, col2)
                        out_fnhw = reshape(out2, [cur_f, cur_n, cur_ho, cur_wo])
                        out_tile_mem = add(
                            slice(out, [n0, f0, ho0, wo0], [cur_n, cur_f, cur_ho, cur_wo], [1, 1, 1, 1], MemorySpace.TSM),
                            transpose(out_fnhw, [1, 0, 2, 3]),
                        )
                        deslice(out, out_tile_mem, [n0, f0, ho0, wo0], [cur_n, cur_f, cur_ho, cur_wo], [1, 1, 1, 1])


def _assert_static_memory_ir(module_text: str) -> None:
    """校验 lowering 后 IR 保留具体 static memory 形状。


    功能说明:
    - 确认 output/input/weight memory 类型包含固定 seed 生成的具体数字 shape。
    - 确认 IR 不包含 dynamic demo 的语义化符号 shape 或旧匿名 `s1/s2/...` shape。
    - 失败时抛出 `AssertionError`，让 demo 脚本直接暴露 static shape 回退。

    使用示例:
    - `_assert_static_memory_ir(str(result.dsl_result.module))`
    """

    static_fragments = (
        (
            "output",
            f"!nn.memory<[#symbol.expr<{_STATIC_BATCH}>, #symbol.expr<{_STATIC_OUT_CHANNELS}>, "
            f"#symbol.expr<{_STATIC_OUTPUT_H}>, #symbol.expr<{_STATIC_OUTPUT_W}>]",
        ),
        (
            "input",
            f"!nn.memory<[#symbol.expr<{_STATIC_BATCH}>, #symbol.expr<{_STATIC_IN_CHANNELS}>, "
            f"#symbol.expr<{_STATIC_INPUT_H}>, #symbol.expr<{_STATIC_INPUT_W}>]",
        ),
        (
            "weight",
            f"!nn.memory<[#symbol.expr<{_STATIC_OUT_CHANNELS}>, #symbol.expr<{_STATIC_IN_CHANNELS}>, "
            f"#symbol.expr<{_STATIC_KERNEL_H}>, #symbol.expr<{_STATIC_KERNEL_W}>]",
        ),
    )
    dynamic_fragments = (
        (
            "semantic output",
            "!nn.memory<[#symbol.expr<B>, #symbol.expr<C>, #symbol.expr<-KH + XH + 1>, #symbol.expr<-KW + XW + 1>]",
        ),
        ("semantic input", "!nn.memory<[#symbol.expr<B>, #symbol.expr<N>, #symbol.expr<XH>, #symbol.expr<XW>]"),
        ("semantic weight", "!nn.memory<[#symbol.expr<C>, #symbol.expr<N>, #symbol.expr<KH>, #symbol.expr<KW>]"),
        ("anonymous dynamic", "!nn.memory<[#symbol.expr<s1>"),
    )
    for label, fragment in static_fragments:
        if fragment not in module_text:
            raise AssertionError(f"static {label} memory shape missing from lowered IR: {fragment}")
    for label, fragment in dynamic_fragments:
        if fragment in module_text:
            raise AssertionError(f"lowered IR unexpectedly contains {label} memory shape: {fragment}")


def main() -> None:
    """运行静态输入、静态 tile 的 conv2d demo。


    功能说明:
    - 使用固定 seed 生成并固化的具体 shape 构造真实 torch tensor 输入。
    - 写入 `kernel/dump/conv2d/inputs_static_tile_static/`。
    - 校验 lowered IR 保持具体数字 static shape。
    - 用 `torch.nn.functional.conv2d` 校验输出。

    使用示例:
    - `python3 kernel/conv2d/inputs_static_tile_static.py`
    """

    input_tensor = torch.arange(_STATIC_BATCH * _STATIC_IN_CHANNELS * _STATIC_INPUT_H * _STATIC_INPUT_W, dtype=torch.float32).reshape(
        _STATIC_BATCH, _STATIC_IN_CHANNELS, _STATIC_INPUT_H, _STATIC_INPUT_W
    ) / 100000000.0
    weight = torch.arange(_STATIC_OUT_CHANNELS * _STATIC_IN_CHANNELS * _STATIC_KERNEL_H * _STATIC_KERNEL_W, dtype=torch.float32).reshape(
        _STATIC_OUT_CHANNELS, _STATIC_IN_CHANNELS, _STATIC_KERNEL_H, _STATIC_KERNEL_W
    ) / 100000.0
    out = torch.empty((_STATIC_BATCH, _STATIC_OUT_CHANNELS, _STATIC_OUTPUT_H, _STATIC_OUTPUT_W), dtype=torch.float32)
    expected = F.conv2d(input_tensor, weight)
    result = run_torch_demo(
        "conv2d/inputs_static_tile_static",
        conv2d_inputs_static_tile_static_kernel,
        (out, input_tensor, weight),
        out,
        expected,
    )
    _assert_static_memory_ir(str(result.dsl_result.module))
    print(result.dsl_result.module)
    print(result.dsl_result.source)
    print("[IR] static memory evidence: output/input/weight concrete shapes present; dynamic symbol shapes absent")
    print(f"[CHECK] {result.case_name} max_abs_diff={result.max_abs_diff}")


if __name__ == "__main__":
    main()
