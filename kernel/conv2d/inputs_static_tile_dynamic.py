"""Conv2d demo with static inputs and dynamic tiles.


功能说明:
- 实现 `inputs 静 + tile 动` 的 NCHW conv2d kernel demo。
- 输入尺寸由固定 seed `20260503` 生成并固化为具体数字：`input[5, 65, 281, 262]`、`weight[20, 65, 3, 3]`、`out[5, 20, 35, 33]`。
- 固定 stride=8，将大输入映射到可真实执行的输出规模；N/C/F/Ho/Wo 均大于 tile 并至少触发两轮 tile。
- lowering 后 IR 必须保持上述具体数字 static shape，不得变成动态符号 shape。
- tile 由 `run_numpy_demo(...)` 以 `int` runtime scalar 传入，尾块通过 DSL `min(...)` 生成 `symbol.min`。
- 当 `tile_c < input channel` 时在每个输出 tile 内先初始化本地 accumulator，再在 `c0` tile 循环内用 `kernel.img2col2d/kernel.matmul/kernel.add` 累计 partial，最后一次写回输出。
- 通过 `dsl_run` 真实执行，并和 NumPy conv2d 参考结果对齐。

API 列表:
- `conv2d_inputs_static_tile_dynamic_kernel(out: Tensor[f32, 5, 20, 35, 33], input_tensor: Tensor[f32, 5, 65, 281, 262], weight: Tensor[f32, 20, 65, 3, 3], tile_f: SymbolDim, tile_c: SymbolDim, tile_n: SymbolDim, tile_ho: SymbolDim, tile_wo: SymbolDim) -> None`
- `main() -> None`

使用示例:
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 kernel/conv2d/inputs_static_tile_dynamic.py`

关联文件:
- 功能实现: `kernel/conv2d/inputs_static_tile_dynamic.py`
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
from kernel_gen.operation.dma import alloc, deslice, fill, reshape, slice
from kernel_gen.operation.nn import transpose
from kernel_gen.operation.scf import loop
from kernel_gen.symbol_variable.memory import MemorySpace
from kernel_gen.symbol_variable.symbol_dim import SymbolDim
from kernel_gen.symbol_variable.type import NumericType

_STATIC_SHAPE_SEED = 20260503
_STATIC_SHAPE_RNG = random.Random(_STATIC_SHAPE_SEED)
_STATIC_BATCH = _STATIC_SHAPE_RNG.randint(5, 7)
_STATIC_IN_CHANNELS = _STATIC_SHAPE_RNG.randint(65, 72)
_STATIC_INPUT_H = _STATIC_SHAPE_RNG.randint(281, 281)
_STATIC_INPUT_W = _STATIC_SHAPE_RNG.randint(262, 262)
_STATIC_OUT_CHANNELS = _STATIC_SHAPE_RNG.randint(20, 20)
_STATIC_KERNEL_H = 3
_STATIC_KERNEL_W = 3
_STATIC_STRIDE_H = 8
_STATIC_STRIDE_W = 8
_STATIC_TILE_ARGS = (8, 16, 4, 8, 8)
_STATIC_OUTPUT_H = ((_STATIC_INPUT_H - _STATIC_KERNEL_H) // _STATIC_STRIDE_H) + 1
_STATIC_OUTPUT_W = ((_STATIC_INPUT_W - _STATIC_KERNEL_W) // _STATIC_STRIDE_W) + 1


def _conv2d_nchw_reference(input_tensor: np.ndarray, weight: np.ndarray) -> np.ndarray:
    """计算 NCHW conv2d NumPy 参考结果。


    功能说明:
    - 当前 static demo 只使用 stride=8、dilation=1、padding=0。
    - 通过 `np.einsum(...)` 对 kernel H/W 维展开累计，避免运行期依赖外部 tensor 框架。

    使用示例:
    - `_conv2d_nchw_reference(input_tensor, weight)`
    """

    n_size, _c_size, h_size, w_size = input_tensor.shape
    f_size, _wc_size, kh_size, kw_size = weight.shape
    ho_size = ((h_size - kh_size) // _STATIC_STRIDE_H) + 1
    wo_size = ((w_size - kw_size) // _STATIC_STRIDE_W) + 1
    output = np.zeros((n_size, f_size, ho_size, wo_size), dtype=np.float32)
    for kh_index in range(kh_size):
        h_start = kh_index
        h_stop = h_start + ho_size * _STATIC_STRIDE_H
        for kw_index in range(kw_size):
            w_start = kw_index
            w_stop = w_start + wo_size * _STATIC_STRIDE_W
            window = input_tensor[:, :, h_start:h_stop:_STATIC_STRIDE_H, w_start:w_stop:_STATIC_STRIDE_W]
            output += np.einsum("nchw,fc->nfhw", window, weight[:, :, kh_index, kw_index], optimize=True)
    return output


def conv2d_inputs_static_tile_dynamic_kernel(
    out: "Tensor[f32, 5, 20, 35, 33]",
    input_tensor: "Tensor[f32, 5, 65, 281, 262]",
    weight: "Tensor[f32, 20, 65, 3, 3]",
    tile_f: SymbolDim,
    tile_c: SymbolDim,
    tile_n: SymbolDim,
    tile_ho: SymbolDim,
    tile_wo: SymbolDim,
) -> None:
    """执行静态输入、动态 tile 的 conv2d。


    功能说明:
    - 输入 shape 为固定 seed 生成并固化的具体数字，tile shape 由 runtime scalar 绑定。
    - 固定 stride=8、dilation=1、padding=0。
    - 使用 `kernel.img2col2d + kernel.matmul + kernel.add` 生成卷积主体，并按 `tile_c` 循环分块后累计所有 partial 到本地 accumulator。
    - 示例 tile 选择 npu_demo 容量安全的 `(8, 16, 4, 8, 8)`，确保 memory_pool 后的片上动态内存视图不越界。

    使用示例:
    - `conv2d_inputs_static_tile_dynamic_kernel(out, input_tensor, weight, 2, 2, 1, 1, 7)`
    """

    n_size, c_size, h_size, w_size = input_tensor.get_shape()
    f_size = weight.get_shape()[0]
    kh_size = weight.get_shape()[2]
    kw_size = weight.get_shape()[3]
    stride_h = 8
    stride_w = 8
    dilation_h = 1
    dilation_w = 1
    pad_top = 0
    pad_bottom = 0
    pad_left = 0
    pad_right = 0
    ho_size = ((h_size + pad_top + pad_bottom - dilation_h * (kh_size - 1) - 1) // stride_h) + 1
    wo_size = ((w_size + pad_left + pad_right - dilation_w * (kw_size - 1) - 1) // stride_w) + 1

    for f0 in loop(0, f_size, tile_f):
        for n0 in loop(0, n_size, tile_n):
            for ho0 in loop(0, ho_size, tile_ho):
                for wo0 in loop(0, wo_size, tile_wo):
                    cur_f = min(tile_f, f_size - f0)
                    cur_n = min(tile_n, n_size - n0)
                    cur_ho = min(tile_ho, ho_size - ho0)
                    cur_wo = min(tile_wo, wo_size - wo0)
                    spatial_tile = cur_ho * cur_wo
                    input_h_tile = (cur_ho - 1) * stride_h + (kh_size - 1) * dilation_h + 1 - pad_top - pad_bottom
                    input_w_tile = (cur_wo - 1) * stride_w + (kw_size - 1) * dilation_w + 1 - pad_left - pad_right
                    for ni in loop(0, cur_n, 1):
                        batch_index = n0 + ni
                        batch_tile = min(n_size, 1)
                        out_tile = batch_tile * spatial_tile
                        acc = alloc([batch_tile, cur_f, cur_ho, cur_wo], NumericType.Float32, MemorySpace.TSM)
                        fill(acc, 0)
                        for c0 in loop(0, c_size, tile_c):
                            cur_c = min(tile_c, c_size - c0)
                            k_tile = cur_c * kh_size * kw_size
                            input_tile = slice(input_tensor, [batch_index, c0, ho0 * stride_h, wo0 * stride_w], [batch_tile, cur_c, input_h_tile, input_w_tile], [1, 1, 1, 1], MemorySpace.TSM)
                            weight_tile = slice(weight, [f0, c0, 0, 0], [cur_f, cur_c, kh_size, kw_size], [1, 1, 1, 1], MemorySpace.TSM)
                            col = alloc([batch_tile, cur_c, kh_size, kw_size, cur_ho, cur_wo], NumericType.Float32, MemorySpace.TSM)
                            kernel.img2col2d(col, input_tile, kh=kh_size, kw=kw_size, sh=stride_h, sw=stride_w, dh=dilation_h, dw=dilation_w, ph=pad_top, pw=pad_bottom, pl=pad_left, pr=pad_right)
                            col2 = reshape(col, [k_tile, out_tile])
                            weight2 = reshape(weight_tile, [cur_f, k_tile])
                            out2 = alloc([cur_f, out_tile], NumericType.Float32, MemorySpace.TSM)
                            kernel.matmul(out2, weight2, col2)
                            out_fnhw = reshape(out2, [cur_f, batch_tile, cur_ho, cur_wo])
                            partial = transpose(out_fnhw, [1, 0, 2, 3])
                            kernel.add(acc, acc, partial)
                        deslice(
                            out,
                            acc,
                            [batch_index, f0, ho0, wo0],
                            [batch_tile, cur_f, cur_ho, cur_wo],
                            [1, 1, 1, 1],
                        )


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
    """运行静态输入、动态 tile 的 conv2d demo。


    功能说明:
    - 使用固定 seed 生成并固化的具体 shape 构造真实 NumPy ndarray 输入。
    - 写入 `kernel/dump/conv2d/inputs_static_tile_dynamic/`。
    - 校验 lowered IR 保持具体数字 static shape。
    - 用 NumPy conv2d 参考结果校验输出。

    使用示例:
    - `python3 kernel/conv2d/inputs_static_tile_dynamic.py`
    """

    rng = np.random.default_rng(2026051612)
    input_tensor = rng.standard_normal((_STATIC_BATCH, _STATIC_IN_CHANNELS, _STATIC_INPUT_H, _STATIC_INPUT_W), dtype=np.float32)
    weight = rng.standard_normal((_STATIC_OUT_CHANNELS, _STATIC_IN_CHANNELS, _STATIC_KERNEL_H, _STATIC_KERNEL_W), dtype=np.float32)
    out = np.zeros((_STATIC_BATCH, _STATIC_OUT_CHANNELS, _STATIC_OUTPUT_H, _STATIC_OUTPUT_W), dtype=np.float32)
    expected = _conv2d_nchw_reference(input_tensor, weight)
    tile_args = _STATIC_TILE_ARGS
    result = run_numpy_demo(
        "conv2d/inputs_static_tile_dynamic",
        conv2d_inputs_static_tile_dynamic_kernel,
        (out, input_tensor, weight, *tile_args),
        out,
        expected,
    )
    _assert_static_memory_ir(str(result.dsl_result.module))
    print(result.dsl_result.module)
    print(result.dsl_result.source)
    print(
        "[ARGS] "
        f"seed=2026051612 input={input_tensor.shape} weight={weight.shape} tile={tile_args} output={out.shape}"
    )
    print("[IR] static memory evidence: output/input/weight concrete shapes present; dynamic symbol shapes absent")
    print(f"[CHECK] {result.case_name} max_abs_diff={result.max_abs_diff}")


if __name__ == "__main__":
    main()
