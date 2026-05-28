"""Conv2d demo with static inputs and dynamic tiles.


功能说明:
- 实现 `inputs 静 + tile 动` 的 NCHW conv2d kernel demo。
- 脚本入口每次运行先随机生成 `shape_seed/tile_seed`，再从受控范围选择本次 input/weight/output shape、`KH/KW`、padding 与 runtime tile。
- static case 将本次随机 input/weight/output shape 具体化到 IR memory type。
- 固定 stride=8，将大输入映射到可真实执行的输出规模；N/C/F/Ho/Wo 均大于 tile 并至少触发两轮 tile。
- 同一 shape seed 还选出非对称 padding，在编译期作为本次随机 static attr 写入 IR。
- lowering 后 IR 必须保持上述 本次随机选中 static shape，不得变成动态符号 shape。
- tile 由 `run_lowering_demo(...)` 以 `SymbolDim` 进入编译 IR，运行期以 Python `int` 传给 `ExecutionEngine` wrapper，尾块通过 DSL `min(...)` 生成 `symbol.min`。
- 当 `tile_c < input channel` 时在每个输出 tile 内先初始化本地 accumulator，再在 `c0` tile 循环内用 `kernel.img2col2d/kernel.matmul/kernel.add` 累计 partial，最后一次写回输出。
- accumulator、bias 与 partial staging scratch 使用 iterator-independent tile 上界分配，真实 tail 通过 `dma.view/deslice` 表达；img2col 与 matmul reshape 链路因现有 layout 合同保持 current tile 分配。
- C/K reduce 完成后按 optional rank-1 bias 分支广播 `bias[None, :, None, None]`，再写回输出。
- 通过 `ExecutionEngine` 真实执行 lowering 生成的源码，并分别校验 absent bias 与 present bias 的 NumPy conv2d 参考结果。

API 列表:
- `conv2d_inputs_static_tile_dynamic_kernel(out: Tensor[f32, B, F, HO, WO], input_tensor: Tensor[f32, B, C, H, W], weight: Tensor[f32, F, C, KH, KW], bias: Tensor[f32, F], tile_f: SymbolDim, tile_c: SymbolDim, tile_n: SymbolDim, tile_ho: SymbolDim, tile_wo: SymbolDim) -> None`
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
from typing import TypeAlias

import numpy as np

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from kernel.runner import run_lowering_demo
from kernel_gen.execute_engine import ExecutionEngine
from kernel_gen.operation import kernel
from kernel_gen.operation.dma import alloc, broadcast, deslice, fill, reshape, slice, view
from kernel_gen.operation.nn import transpose
from kernel_gen.operation.scf import loop
from kernel_gen.symbol_variable.memory import Memory, MemorySpace
from kernel_gen.symbol_variable.symbol_dim import SymbolDim
from kernel_gen.symbol_variable.type import NumericType

CASE_NAME = "conv2d/inputs_static_tile_dynamic"
WRAPPER_ENTRY_NAME = "conv2d_inputs_static_tile_dynamic_kernel"
_STATIC_SHAPE_SEED = 2026052702
_STATIC_SHAPE_RNG = random.Random(_STATIC_SHAPE_SEED)
_STATIC_BATCH = _STATIC_SHAPE_RNG.randint(4, 6)
_STATIC_IN_CHANNELS = _STATIC_SHAPE_RNG.randint(48, 64)
_STATIC_INPUT_H = _STATIC_SHAPE_RNG.randint(241, 289)
_STATIC_INPUT_W = _STATIC_SHAPE_RNG.randint(225, 273)
_STATIC_OUT_CHANNELS = _STATIC_SHAPE_RNG.randint(18, 24)
_STATIC_KERNEL_H = _STATIC_SHAPE_RNG.choice((3, 5))
_STATIC_KERNEL_W = _STATIC_SHAPE_RNG.choice((3, 5))
_STATIC_STRIDE_H = 8
_STATIC_STRIDE_W = 8
_STATIC_DILATION_H = 1
_STATIC_DILATION_W = 1
_STATIC_PAD_TOP = _STATIC_SHAPE_RNG.choice((0, 1, 2, 3, 4))
_STATIC_PAD_BOTTOM = _STATIC_SHAPE_RNG.choice((0, 1, 2, 3, 4))
_STATIC_PAD_LEFT = _STATIC_SHAPE_RNG.choice((0, 1, 2, 3, 4))
_STATIC_PAD_RIGHT = _STATIC_SHAPE_RNG.choice((0, 1, 2, 3, 4))
_STATIC_TILE_SELECTION_SEED = 2026051724
_STATIC_TILE_CANDIDATES = ((8, 16, 4, 8, 9), (7, 18, 3, 9, 8), (6, 20, 2, 10, 7))
_STATIC_TILE_ARGS = random.Random(_STATIC_TILE_SELECTION_SEED).choice(_STATIC_TILE_CANDIDATES)
_BIAS_CASE_ORDER_SEED = 2026051754
_BIAS_CASE_ORDER = tuple(random.Random(_BIAS_CASE_ORDER_SEED).sample(("absent", "present"), 2))
_STATIC_OUTPUT_H = (
    (_STATIC_INPUT_H + _STATIC_PAD_TOP + _STATIC_PAD_BOTTOM - _STATIC_DILATION_H * (_STATIC_KERNEL_H - 1) - 1)
    // _STATIC_STRIDE_H
) + 1
_STATIC_OUTPUT_W = (
    (_STATIC_INPUT_W + _STATIC_PAD_LEFT + _STATIC_PAD_RIGHT - _STATIC_DILATION_W * (_STATIC_KERNEL_W - 1) - 1)
    // _STATIC_STRIDE_W
) + 1
Conv2dCompileArg: TypeAlias = "Memory | SymbolDim"
Conv2dRuntimeArg: TypeAlias = "np.ndarray | int | None"


def _conv2d_nchw_reference(input_tensor: np.ndarray, weight: np.ndarray) -> np.ndarray:
    """计算 NCHW conv2d NumPy 参考结果。


    功能说明:
    - 当前 static demo 使用 本次随机选中 stride、dilation 与非对称 padding。
    - 通过 `np.einsum(...)` 对 kernel H/W 维展开累计，避免运行期依赖外部 tensor 框架。

    使用示例:
    - `_conv2d_nchw_reference(input_tensor, weight)`
    """

    padded_input = np.pad(
        input_tensor,
        ((0, 0), (0, 0), (_STATIC_PAD_TOP, _STATIC_PAD_BOTTOM), (_STATIC_PAD_LEFT, _STATIC_PAD_RIGHT)),
    )
    n_size, _c_size, h_size, w_size = padded_input.shape
    f_size, _wc_size, kh_size, kw_size = weight.shape
    ho_size = ((h_size - _STATIC_DILATION_H * (kh_size - 1) - 1) // _STATIC_STRIDE_H) + 1
    wo_size = ((w_size - _STATIC_DILATION_W * (kw_size - 1) - 1) // _STATIC_STRIDE_W) + 1
    output = np.zeros((n_size, f_size, ho_size, wo_size), dtype=np.float32)
    for kh_index in range(kh_size):
        h_start = kh_index * _STATIC_DILATION_H
        h_stop = h_start + ho_size * _STATIC_STRIDE_H
        for kw_index in range(kw_size):
            w_start = kw_index * _STATIC_DILATION_W
            w_stop = w_start + wo_size * _STATIC_STRIDE_W
            window = padded_input[:, :, h_start:h_stop:_STATIC_STRIDE_H, w_start:w_stop:_STATIC_STRIDE_W]
            output += np.einsum("nchw,fc->nfhw", window, weight[:, :, kh_index, kw_index], optimize=True)
    return output


def conv2d_inputs_static_tile_dynamic_kernel(
    out: "Tensor[f32, 4, 21, 33, 29]",
    input_tensor: "Tensor[f32, 4, 61, 254, 229]",
    weight: "Tensor[f32, 21, 61, 3, 5]",
    bias: "Tensor[f32, 21]",
    tile_f: SymbolDim,
    tile_c: SymbolDim,
    tile_n: SymbolDim,
    tile_ho: SymbolDim,
    tile_wo: SymbolDim,
) -> None:
    """执行静态输入、动态 tile 的 conv2d。


    功能说明:
    - 输入 shape 为 per-run random profile 选出的具体 static 值，tile shape 由 runtime scalar 绑定。
    - 固定 stride=8、dilation=1，padding 使用同一 profile 选出的非对称配置。
    - 使用 `kernel.img2col2d + kernel.matmul + kernel.add` 生成卷积主体，并按 `tile_c` 循环分块后累计所有 partial 到本地 accumulator。
    - runtime tile 从轻量候选集合按 seed 选择，确保 memory_pool 后的片上动态内存视图不越界。
    - accumulator、bias 与 partial staging scratch 使用 tile 上界分配，真实 `cur_f/cur_ho/cur_wo` tail 通过 `view/deslice` 写入与读出。
    - runtime bias 非空时，在 reduce 后、写回前广播 rank-1 bias 并累加。

    使用示例:
    - `conv2d_inputs_static_tile_dynamic_kernel(out, input_tensor, weight, bias, 2, 2, 1, 1, 7)`
    """

    n_size, c_size, h_size, w_size = input_tensor.get_shape()
    f_size = weight.get_shape()[0]
    kh_size = weight.get_shape()[2]
    kw_size = weight.get_shape()[3]
    stride_h = 8
    stride_w = 8
    dilation_h = _STATIC_DILATION_H
    dilation_w = _STATIC_DILATION_W
    pad_top = _STATIC_PAD_TOP
    pad_bottom = _STATIC_PAD_BOTTOM
    pad_left = _STATIC_PAD_LEFT
    pad_right = _STATIC_PAD_RIGHT
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
                    input_h_origin = ho0 * stride_h - pad_top
                    input_w_origin = wo0 * stride_w - pad_left
                    input_h_window_end = (ho0 + cur_ho - 1) * stride_h - pad_top + (kh_size - 1) * dilation_h + 1
                    input_w_window_end = (wo0 + cur_wo - 1) * stride_w - pad_left + (kw_size - 1) * dilation_w + 1
                    input_h_start = max(input_h_origin, 0)
                    input_w_start = max(input_w_origin, 0)
                    input_h_end = min(input_h_window_end, h_size)
                    input_w_end = min(input_w_window_end, w_size)
                    input_h_tile = input_h_end - input_h_start
                    input_w_tile = input_w_end - input_w_start
                    local_pad_top = max(pad_top - ho0 * stride_h, 0)
                    local_pad_left = max(pad_left - wo0 * stride_w, 0)
                    local_pad_bottom = max(input_h_window_end - h_size, 0)
                    local_pad_right = max(input_w_window_end - w_size, 0)
                    for ni in loop(0, cur_n, 1):
                        batch_index = n0 + ni
                        batch_tile = min(n_size, 1)
                        acc = alloc([batch_tile, tile_f, tile_ho, tile_wo], NumericType.Float32, MemorySpace.TSM)
                        fill(acc, 0)
                        bias_tile = alloc([tile_f], NumericType.Float32, MemorySpace.TSM)
                        fill(bias_tile, 0)
                        bias_nchw = reshape(bias_tile, [1, tile_f, 1, 1])
                        bias_full = alloc([batch_tile, tile_f, tile_ho, tile_wo], NumericType.Float32, MemorySpace.TSM)
                        for c0 in loop(0, c_size, tile_c):
                            cur_c = min(tile_c, c_size - c0)
                            k_tile = cur_c * kh_size * kw_size
                            out_tile = batch_tile * spatial_tile
                            input_tile = slice(input_tensor, [batch_index, c0, input_h_start, input_w_start], [batch_tile, cur_c, input_h_tile, input_w_tile], [1, 1, 1, 1], MemorySpace.TSM)
                            weight_tile = slice(weight, [f0, c0, 0, 0], [cur_f, cur_c, kh_size, kw_size], [1, 1, 1, 1], MemorySpace.TSM)
                            col = alloc([batch_tile, cur_c, kh_size, kw_size, cur_ho, cur_wo], NumericType.Float32, MemorySpace.TSM)
                            kernel.img2col2d(col, input_tile, kh=kh_size, kw=kw_size, sh=stride_h, sw=stride_w, dh=dilation_h, dw=dilation_w, ph=local_pad_top, pw=local_pad_bottom, pl=local_pad_left, pr=local_pad_right)
                            col2 = reshape(col, [k_tile, out_tile])
                            weight2 = reshape(weight_tile, [cur_f, k_tile])
                            out2 = alloc([cur_f, out_tile], NumericType.Float32, MemorySpace.TSM)
                            kernel.matmul(out2, weight2, col2)
                            out_fnhw = reshape(out2, [cur_f, batch_tile, cur_ho, cur_wo])
                            partial = transpose(out_fnhw, [1, 0, 2, 3])
                            partial_full = alloc([batch_tile, tile_f, tile_ho, tile_wo], NumericType.Float32, MemorySpace.TSM)
                            fill(partial_full, 0)
                            deslice(partial_full, partial, [0, 0, 0, 0], [batch_tile, cur_f, cur_ho, cur_wo], [1, 1, 1, 1])
                            kernel.add(acc, acc, partial_full)
                        if bias is not None:
                            bias_region = view(bias, [f0], [cur_f], [1])
                            bias_current = view(bias_tile, [0], [cur_f], [1])
                            deslice(bias_current, bias_region, [0], [cur_f], [1])
                            broadcast(bias_full, bias_nchw)
                            kernel.add(acc, acc, bias_full)
                        acc_current = view(acc, [0, 0, 0, 0], [batch_tile, cur_f, cur_ho, cur_wo], [1, 1, 1, 1])
                        deslice(
                            out,
                            acc_current,
                            [batch_index, f0, ho0, wo0],
                            [batch_tile, cur_f, cur_ho, cur_wo],
                            [1, 1, 1, 1],
                        )


def _assert_static_memory_ir(module_text: str) -> None:
    """校验 lowering 后 IR 保留具体 static memory 形状。


    功能说明:
    - 确认 output/input/weight memory 类型包含 本次随机选中 static shape。
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
        ("bias", f"!nn.memory<[#symbol.expr<{_STATIC_OUT_CHANNELS}>]"),
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
    for fragment in (
        "!symbol.int<#symbol.expr<TF>>",
        "!symbol.int<#symbol.expr<TC>>",
        "!symbol.int<#symbol.expr<TN>>",
        "!symbol.int<#symbol.expr<THO>>",
        "!symbol.int<#symbol.expr<TWO>>",
        "step = #symbol.expr<TC>",
    ):
        if fragment not in module_text:
            raise AssertionError(f"static dynamic tile symbol missing from lowered IR: {fragment}")
    for fragment in ("memory.get_data", "symbol.ne"):
        if fragment not in module_text:
            raise AssertionError(f"optional bias presence fragment missing from lowered IR: {fragment}")
    for label, fragment in dynamic_fragments:
        if fragment in module_text:
            raise AssertionError(f"lowered IR unexpectedly contains {label} memory shape: {fragment}")


def _symbolic_compile_args() -> tuple[Conv2dCompileArg, ...]:
    """构造 static input / symbolic tile 的编译参数。


    功能说明:
    - output/input/weight/bias 均使用 per-run random profile 选出的 static memory shape。
    - static case 将这些 本次随机选中 值具体化到 IR memory type。
    - tile 参数固定使用 `TF/TC/TN/THO/TWO`，用于锁定编译期符号 tile。
    - stride、dilation 与 padding 保留在 DSL body 内的 static random attr。

    使用示例:
    - `_symbolic_compile_args()`
    """

    return (
        Memory([_STATIC_BATCH, _STATIC_OUT_CHANNELS, _STATIC_OUTPUT_H, _STATIC_OUTPUT_W], NumericType.Float32),
        Memory([_STATIC_BATCH, _STATIC_IN_CHANNELS, _STATIC_INPUT_H, _STATIC_INPUT_W], NumericType.Float32),
        Memory([_STATIC_OUT_CHANNELS, _STATIC_IN_CHANNELS, _STATIC_KERNEL_H, _STATIC_KERNEL_W], NumericType.Float32),
        Memory([_STATIC_OUT_CHANNELS], NumericType.Float32),
        SymbolDim("TF"),
        SymbolDim("TC"),
        SymbolDim("TN"),
        SymbolDim("THO"),
        SymbolDim("TWO"),
    )


def _assert_source_dump_matches(source: str) -> None:
    """校验生成源码与公开 dump/source.cpp 一致。


    功能说明:
    - 读取 `kernel/dump/conv2d/inputs_static_tile_dynamic/source.cpp`。
    - 使用去尾空白后的全文比较证明执行真源与公开 dump 一致。
    - 同时检查 wrapper entry 与 `npu_demo::launch` 关键 marker。

    使用示例:
    - `_assert_source_dump_matches(source)`
    """

    dump_source_path = _REPO_ROOT / "kernel" / "dump" / Path(CASE_NAME) / "source.cpp"
    dump_source = dump_source_path.read_text(encoding="utf-8")
    normalized_source = "\n".join(line.rstrip() for line in source.strip().splitlines())
    normalized_dump = "\n".join(line.rstrip() for line in dump_source.strip().splitlines())
    if normalized_source != normalized_dump:
        raise AssertionError(f"{CASE_NAME}: source dump does not match lowering source")
    for marker in (WRAPPER_ENTRY_NAME, "npu_demo::launch"):
        if marker not in dump_source:
            raise AssertionError(f"{CASE_NAME}: source dump missing marker {marker}")


def _execute_device_source(source: str, real_args: tuple[Conv2dRuntimeArg, ...]) -> None:
    """编译并执行 lowering 生成的 root entry。


    功能说明:
    - 使用公开 `ExecutionEngine` 编译 `gen_kernel` 生成的完整源码。
    - 执行入口固定为 lowering 生成的 root wrapper，保留 `npu_demo::launch` block 分发语义。
    - `CompiledKernel` 使用完立即关闭，释放临时编译目录。

    使用示例:
    - `_execute_device_source(source, (out, input_tensor, weight, None, 7, 18, 3, 9, 8))`
    """

    compiled_kernel = ExecutionEngine(target="npu_demo").compile(source=source, function=WRAPPER_ENTRY_NAME)
    try:
        execute_result = compiled_kernel.execute(args=real_args)
        if not execute_result.ok:
            raise RuntimeError(f"{CASE_NAME}: execute failed: {execute_result.failure_phrase}")
    finally:
        compiled_kernel.close()


def _assert_outputs_close(
    output: np.ndarray,
    expected: np.ndarray,
    *,
    atol: float,
    rtol: float,
) -> float:
    """校验真实输出与 NumPy 参考结果一致。


    功能说明:
    - 仅服务本 demo 的 NumPy ndarray 输出校验。
    - 返回最大绝对误差，供脚本输出稳定检查摘要。
    - 校验失败时抛出 `AssertionError`。

    使用示例:
    - `_assert_outputs_close(out, expected, atol=1e-4, rtol=1e-4)`
    """

    max_abs_diff = float(np.max(np.abs(output - expected)))
    if not np.allclose(output, expected, atol=atol, rtol=rtol):
        raise AssertionError(
            f"{CASE_NAME}: output does not match NumPy reference "
            f"(max_abs_diff={max_abs_diff}, atol={atol}, rtol={rtol})"
        )
    return max_abs_diff


def main() -> None:
    """运行静态输入、动态 tile 的 conv2d demo。


    功能说明:
    - 使用 per-run random profile 选出的具体 shape 构造真实 NumPy ndarray 输入。
    - 写入 `kernel/dump/conv2d/inputs_static_tile_dynamic/`。
    - 编译期以 static memory / symbolic tile 生成 lowering IR 与 npu_demo source。
    - 校验 lowered IR 保持 本次随机选中 static shape 且 tile 保持 `TF/TC/TN/THO/TWO`。
    - 分别用 NumPy conv2d 与 `conv2d + bias[None, :, None, None]` 参考结果校验输出。

    使用示例:
    - `python3 kernel/conv2d/inputs_static_tile_dynamic.py`
    """

    global _STATIC_SHAPE_SEED, _STATIC_BATCH, _STATIC_IN_CHANNELS, _STATIC_INPUT_H, _STATIC_INPUT_W
    global _STATIC_OUT_CHANNELS, _STATIC_KERNEL_H, _STATIC_KERNEL_W
    global _STATIC_PAD_TOP, _STATIC_PAD_BOTTOM, _STATIC_PAD_LEFT, _STATIC_PAD_RIGHT
    global _STATIC_TILE_SELECTION_SEED, _STATIC_TILE_ARGS, _STATIC_OUTPUT_H, _STATIC_OUTPUT_W

    system_rng = random.SystemRandom()
    for _attempt in range(128):
        shape_seed = system_rng.randrange(1, 2**31)
        tile_seed = system_rng.randrange(1, 2**31)
        shape_rng = random.Random(shape_seed)
        batch = shape_rng.randint(4, 6)
        in_channels = shape_rng.randint(48, 64)
        input_h = shape_rng.randint(241, 289)
        input_w = shape_rng.randint(225, 273)
        out_channels = shape_rng.randint(18, 24)
        kernel_h = shape_rng.choice((3, 5))
        kernel_w = shape_rng.choice((3, 5))
        pad_top = shape_rng.choice((0, 1, 2, 3, 4))
        pad_bottom = shape_rng.choice((0, 1, 2, 3, 4))
        pad_left = shape_rng.choice((0, 1, 2, 3, 4))
        pad_right = shape_rng.choice((0, 1, 2, 3, 4))
        output_h = ((input_h + pad_top + pad_bottom - _STATIC_DILATION_H * (kernel_h - 1) - 1) // _STATIC_STRIDE_H) + 1
        output_w = ((input_w + pad_left + pad_right - _STATIC_DILATION_W * (kernel_w - 1) - 1) // _STATIC_STRIDE_W) + 1
        tile_args = random.Random(tile_seed).choice(_STATIC_TILE_CANDIDATES)
        tile_f, tile_c, tile_n, tile_ho, tile_wo = tile_args
        has_multi_tile = (
            out_channels > tile_f
            and in_channels > tile_c
            and batch > tile_n
            and output_h > tile_ho
            and output_w > tile_wo
        )
        tail_count = sum(
            (
                out_channels % tile_f != 0,
                in_channels % tile_c != 0,
                batch % tile_n != 0,
                output_h % tile_ho != 0,
                output_w % tile_wo != 0,
            )
        )
        if has_multi_tile and tail_count == 5:
            break
    else:
        raise RuntimeError("conv2d static/dynamic random profile failed to satisfy tile invariants")

    _STATIC_SHAPE_SEED = shape_seed
    _STATIC_BATCH = batch
    _STATIC_IN_CHANNELS = in_channels
    _STATIC_INPUT_H = input_h
    _STATIC_INPUT_W = input_w
    _STATIC_OUT_CHANNELS = out_channels
    _STATIC_KERNEL_H = kernel_h
    _STATIC_KERNEL_W = kernel_w
    _STATIC_PAD_TOP = pad_top
    _STATIC_PAD_BOTTOM = pad_bottom
    _STATIC_PAD_LEFT = pad_left
    _STATIC_PAD_RIGHT = pad_right
    _STATIC_TILE_SELECTION_SEED = tile_seed
    _STATIC_TILE_ARGS = tile_args
    _STATIC_OUTPUT_H = output_h
    _STATIC_OUTPUT_W = output_w
    conv2d_inputs_static_tile_dynamic_kernel.__annotations__.update(
        {
            "out": f"Tensor[f32, {_STATIC_BATCH}, {_STATIC_OUT_CHANNELS}, {_STATIC_OUTPUT_H}, {_STATIC_OUTPUT_W}]",
            "input_tensor": f"Tensor[f32, {_STATIC_BATCH}, {_STATIC_IN_CHANNELS}, {_STATIC_INPUT_H}, {_STATIC_INPUT_W}]",
            "weight": f"Tensor[f32, {_STATIC_OUT_CHANNELS}, {_STATIC_IN_CHANNELS}, {_STATIC_KERNEL_H}, {_STATIC_KERNEL_W}]",
            "bias": f"Tensor[f32, {_STATIC_OUT_CHANNELS}]",
        }
    )

    rng = np.random.default_rng(_STATIC_SHAPE_SEED)
    input_tensor = rng.standard_normal((_STATIC_BATCH, _STATIC_IN_CHANNELS, _STATIC_INPUT_H, _STATIC_INPUT_W), dtype=np.float32)
    weight = rng.standard_normal((_STATIC_OUT_CHANNELS, _STATIC_IN_CHANNELS, _STATIC_KERNEL_H, _STATIC_KERNEL_W), dtype=np.float32)
    bias = rng.standard_normal((_STATIC_OUT_CHANNELS,), dtype=np.float32)
    absent_out = np.zeros((_STATIC_BATCH, _STATIC_OUT_CHANNELS, _STATIC_OUTPUT_H, _STATIC_OUTPUT_W), dtype=np.float32)
    present_out = np.zeros((_STATIC_BATCH, _STATIC_OUT_CHANNELS, _STATIC_OUTPUT_H, _STATIC_OUTPUT_W), dtype=np.float32)
    absent_expected = _conv2d_nchw_reference(input_tensor, weight)
    present_expected = absent_expected + bias[None, :, None, None]
    tile_args = _STATIC_TILE_ARGS
    module, source = run_lowering_demo(CASE_NAME, conv2d_inputs_static_tile_dynamic_kernel, *_symbolic_compile_args())
    module_text = str(module)
    _assert_static_memory_ir(module_text)
    _assert_source_dump_matches(source)
    max_abs_diff_by_case = {}
    for bias_case in _BIAS_CASE_ORDER:
        if bias_case == "absent":
            _execute_device_source(source, (absent_out, input_tensor, weight, None, *tile_args))
            max_abs_diff_by_case[bias_case] = _assert_outputs_close(absent_out, absent_expected, atol=1e-4, rtol=1e-4)
            continue
        _execute_device_source(source, (present_out, input_tensor, weight, bias, *tile_args))
        max_abs_diff_by_case[bias_case] = _assert_outputs_close(present_out, present_expected, atol=1e-4, rtol=1e-4)
    absent_max_abs_diff = max_abs_diff_by_case["absent"]
    present_max_abs_diff = max_abs_diff_by_case["present"]
    print(
        "[ARGS] "
        "profile=per-run-random static_memory=random-concrete dynamic_tile=symbolic-runtime "
        f"shape_seed={_STATIC_SHAPE_SEED} input={input_tensor.shape} weight={weight.shape} "
        f"stride=({_STATIC_STRIDE_H},{_STATIC_STRIDE_W}) dilation=({_STATIC_DILATION_H},{_STATIC_DILATION_W}) "
        f"padding=({_STATIC_PAD_TOP},{_STATIC_PAD_BOTTOM},{_STATIC_PAD_LEFT},{_STATIC_PAD_RIGHT}) "
        f"tile_seed={_STATIC_TILE_SELECTION_SEED} tile_candidates={_STATIC_TILE_CANDIDATES} selected_tile={tile_args} "
        f"output={present_out.shape} bias_case_order={_BIAS_CASE_ORDER} bias_rank=1"
    )
    print("[IR] static memory evidence: 本次随机选中 concrete output/input/weight shapes present; TF/TC/TN/THO/TWO tile symbols present")
    print(f"[CHECK] {CASE_NAME}/absent_bias max_abs_diff={absent_max_abs_diff}")
    print(f"[CHECK] {CASE_NAME}/present_bias max_abs_diff={present_max_abs_diff}")


if __name__ == "__main__":
    main()
