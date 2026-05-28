"""Conv2d demo with dynamic inputs and dynamic tiles.


功能说明:
- 实现 `inputs 动 + tile 动` 的 NCHW conv2d kernel demo。
- 输入与输出使用符号维度标注，并由真实 NumPy ndarray 运行时 shape 绑定。
- 脚本入口每次运行先随机生成 `shape_seed/tile_seed`，再从受控范围选择本次 shape、`KH/KW`、padding 与 tile。
- 编译期 memory、stride、dilation、padding 与 tile 均保持 `SymbolDim` 语义符号。
- 本次随机 shape / conv attrs / tile 只作为 runtime ndarray shape 与 int scalar 传给 `ExecutionEngine` root wrapper，不静态化进入口 memory/tile 类型。
- 当 `tile_c < input channel` 时在每个输出 tile 内先初始化本地 accumulator，再在 `c0` tile 循环内用 `kernel.img2col2d/kernel.matmul/kernel.add` 累计 partial，最后一次写回输出。
- accumulator、bias 与 partial staging scratch 使用 iterator-independent tile 上界分配，真实 tail 通过 `dma.view/deslice` 表达；img2col 与 matmul reshape 链路因现有 layout 合同保持 current tile 分配。
- 编译期用 `B/N/C/XH/XW/KH/KW/SH/SW/DH/DW/PT/PB/PL/PR/TF/TC/TN/THO/TWO` 语义化符号走 `gen_kernel` 生成动态 memory IR/source。
- output 编译期 memory 形状为完整非对称 padding 公式：`((XH + PT + PB - DH * (KH - 1) - 1) floordiv SH) + 1` 与 `((XW + PL + PR - DW * (KW - 1) - 1) floordiv SW) + 1`。
- lowering 后 memory-pool 形态必须使用 `arch.get_dynamic_memory + dma.view`，不得残留 `dma.alloc` / `allalloc`。
- 运行期传入真实 NumPy ndarray shape，并和 NumPy conv2d 参考结果对齐。
- C/K reduce 完成后按 optional rank-1 bias 分支广播 `bias[None, :, None, None]`，再写回输出。

API 列表:
- `conv2d_inputs_dynamic_tile_dynamic_kernel(out: Tensor[f32, B, C, HO, WO], input_tensor: Tensor[f32, B, N, XH, XW], weight: Tensor[f32, C, N, KH, KW], bias: Tensor[f32, C], stride_h: SymbolDim, stride_w: SymbolDim, dilation_h: SymbolDim, dilation_w: SymbolDim, pad_top: SymbolDim, pad_bottom: SymbolDim, pad_left: SymbolDim, pad_right: SymbolDim, tile_f: SymbolDim, tile_c: SymbolDim, tile_n: SymbolDim, tile_ho: SymbolDim, tile_wo: SymbolDim) -> None`
- `main() -> None`

使用示例:
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 kernel/conv2d/inputs_dynamic_tile_dynamic.py`

关联文件:
- 功能实现: `kernel/conv2d/inputs_dynamic_tile_dynamic.py`
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

CASE_NAME = "conv2d/inputs_dynamic_tile_dynamic"
ROOT_ENTRY_NAME = "conv2d_inputs_dynamic_tile_dynamic_kernel"
_DYNAMIC_SHAPE_SEED = 2026052703
_DYNAMIC_TILE_SELECTION_SEED = 2026051726
_DYNAMIC_TILE_CANDIDATES = ((8, 16, 4, 8, 9), (7, 18, 3, 9, 8), (6, 20, 2, 10, 7))
_DYNAMIC_TILE_ARGS = random.Random(_DYNAMIC_TILE_SELECTION_SEED).choice(_DYNAMIC_TILE_CANDIDATES)
_BIAS_CASE_ORDER_SEED = 2026051755
_BIAS_CASE_ORDER = tuple(random.Random(_BIAS_CASE_ORDER_SEED).sample(("absent", "present"), 2))
Conv2dCompileArg: TypeAlias = "Memory | SymbolDim"
Conv2dRuntimeArg: TypeAlias = "np.ndarray | int | None"


def _conv2d_nchw_reference(
    input_tensor: np.ndarray,
    weight: np.ndarray,
    *,
    stride: tuple[int, int],
    dilation: tuple[int, int],
    padding: tuple[int, int, int, int],
) -> np.ndarray:
    """计算 NCHW conv2d NumPy 参考结果。


    功能说明:
    - 支持当前 dynamic demo 使用的非对称 padding、stride 与 dilation。
    - 通过 `np.pad(...)` 和 `np.einsum(...)` 生成参考输出，避免运行期依赖外部 tensor 框架。

    使用示例:
    - `_conv2d_nchw_reference(input_tensor, weight, stride=(1, 2), dilation=(1, 1), padding=(1, 2, 0, 3))`
    """

    pad_top, pad_bottom, pad_left, pad_right = padding
    padded_input = np.pad(input_tensor, ((0, 0), (0, 0), (pad_top, pad_bottom), (pad_left, pad_right)))
    n_size, _c_size, h_size, w_size = padded_input.shape
    f_size, _wc_size, kh_size, kw_size = weight.shape
    ho_size = ((h_size - dilation[0] * (kh_size - 1) - 1) // stride[0]) + 1
    wo_size = ((w_size - dilation[1] * (kw_size - 1) - 1) // stride[1]) + 1
    output = np.zeros((n_size, f_size, ho_size, wo_size), dtype=np.float32)
    for kh_index in range(kh_size):
        h_start = kh_index * dilation[0]
        h_stop = h_start + ho_size * stride[0]
        for kw_index in range(kw_size):
            w_start = kw_index * dilation[1]
            w_stop = w_start + wo_size * stride[1]
            window = padded_input[:, :, h_start:h_stop:stride[0], w_start:w_stop:stride[1]]
            output += np.einsum("nchw,fc->nfhw", window, weight[:, :, kh_index, kw_index], optimize=True)
    return output


def conv2d_inputs_dynamic_tile_dynamic_kernel(
    out: "Tensor[f32, B, C, HO, WO]",
    input_tensor: "Tensor[f32, B, N, XH, XW]",
    weight: "Tensor[f32, C, N, KH, KW]",
    bias: "Tensor[f32, C]",
    stride_h: SymbolDim,
    stride_w: SymbolDim,
    dilation_h: SymbolDim,
    dilation_w: SymbolDim,
    pad_top: SymbolDim,
    pad_bottom: SymbolDim,
    pad_left: SymbolDim,
    pad_right: SymbolDim,
    tile_f: SymbolDim,
    tile_c: SymbolDim,
    tile_n: SymbolDim,
    tile_ho: SymbolDim,
    tile_wo: SymbolDim,
) -> None:
    """执行动态输入、动态 tile 的 conv2d。


    功能说明:
    - 输入、输出与权重维度来自 `Tensor[...]` 符号维度，布局为 input[B,N,XH,XW]、weight[C,N,KH,KW]、out[B,C,HO,WO]。
    - stride/dilation/padding/tile shape 使用 本次随机选中 runtime scalar 绑定，不静态化进入编译入口类型。
    - K/reduce 维按输入通道 tile 切分，`kernel.matmul` 覆盖 `cur_c * KH * KW`，并通过本地 accumulator 累计所有 partial。
    - accumulator、bias 与 partial staging scratch 使用 tile 上界分配，真实 `cur_f/cur_ho/cur_wo` tail 通过 `view/deslice` 写入与读出。
    - runtime bias 非空时，在 reduce 后、写回前广播 rank-1 bias 并累加。

    使用示例:
    - `conv2d_inputs_dynamic_tile_dynamic_kernel(out, input_tensor, weight, bias, 1, 1, 1, 1, 0, 0, 0, 0, 2, 2, 1, 1, 7)`
    """

    n_size, c_size, h_size, w_size = input_tensor.get_shape()
    f_size = weight.get_shape()[0]
    kh_size = weight.get_shape()[2]
    kw_size = weight.get_shape()[3]
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


def _symbolic_compile_args() -> tuple[Conv2dCompileArg, ...]:
    """构造符号 Memory 编译参数。


    功能说明:
    - output/input/weight 的编译期 memory shape 使用 conv2d 语义化符号维度。
    - output 空间维使用 `SH/SW/DH/DW/PT/PB/PL/PR` 完整符号公式。
    - stride、dilation、padding 与 tile 均传 `SymbolDim`，真实值只在运行期 `ExecutionEngine` 参数里绑定。
    - 只服务本 demo 的符号编译入口，不新增跨文件公开 API。

    使用示例:
    - `_symbolic_compile_args()`
    """

    xh_dim = SymbolDim("XH")
    xw_dim = SymbolDim("XW")
    kh_dim = SymbolDim("KH")
    kw_dim = SymbolDim("KW")
    sh_dim = SymbolDim("SH")
    sw_dim = SymbolDim("SW")
    dh_dim = SymbolDim("DH")
    dw_dim = SymbolDim("DW")
    pt_dim = SymbolDim("PT")
    pb_dim = SymbolDim("PB")
    pl_dim = SymbolDim("PL")
    pr_dim = SymbolDim("PR")
    tf_dim = SymbolDim("TF")
    tc_dim = SymbolDim("TC")
    tn_dim = SymbolDim("TN")
    tho_dim = SymbolDim("THO")
    two_dim = SymbolDim("TWO")
    output_h_dim = ((xh_dim + pt_dim + pb_dim - dh_dim * (kh_dim - 1) - 1) // sh_dim) + 1
    output_w_dim = ((xw_dim + pl_dim + pr_dim - dw_dim * (kw_dim - 1) - 1) // sw_dim) + 1

    return (
        Memory(["B", "C", output_h_dim, output_w_dim], NumericType.Float32),
        Memory(["B", "N", "XH", "XW"], NumericType.Float32),
        Memory(["C", "N", "KH", "KW"], NumericType.Float32),
        Memory(["C"], NumericType.Float32),
        sh_dim,
        sw_dim,
        dh_dim,
        dw_dim,
        pt_dim,
        pb_dim,
        pl_dim,
        pr_dim,
        tf_dim,
        tc_dim,
        tn_dim,
        tho_dim,
        two_dim,
    )


def _assert_dynamic_memory_ir(
    module_text: str,
    actual_output_shape: tuple[int, int, int, int],
    actual_input_shape: tuple[int, int, int, int],
    actual_weight_shape: tuple[int, int, int, int],
) -> None:
    """校验 lowering 后 IR 保留符号 memory 形状。


    功能说明:
    - 确认输出 memory 类型包含 `B/C` 以及 `SH/SW/DH/DW/PT/PB/PL/PR` 组成的完整动态公式。
    - 确认输入 memory 类型包含 `!nn.memory<[#symbol.expr<B>, #symbol.expr<N>, #symbol.expr<XH>, #symbol.expr<XW>]`。
    - 确认权重 memory 类型包含 `!nn.memory<[#symbol.expr<C>, #symbol.expr<N>, #symbol.expr<KH>, #symbol.expr<KW>]`。
    - 确认 bias memory 类型包含 `!nn.memory<[#symbol.expr<C>]`，并通过 `memory.get_data/symbol.ne` 生成可空 presence guard。
    - 确认 IR 不回退为本次真实运行的 output/input/weight 静态 shape。
    - 确认 IR 不回退为旧 `s1/s2/...` 匿名符号 shape。
    - 确认 memory-pool 后 IR 已收口为 `arch.get_dynamic_memory + dma.view`，不残留 `dma.alloc` / `allalloc`。
    - 失败时抛出 `AssertionError`，让 demo 脚本直接暴露编译形态回退。

    使用示例:
    - `_assert_dynamic_memory_ir(str(module), (12, 2, 128, 128), (12, 32, 256, 256), (2, 32, 3, 3))`
    """

    required_dynamic_fragments = (
        ("output prefix", "!nn.memory<[#symbol.expr<B>, #symbol.expr<C>,"),
        ("output stride h symbol", "SH"),
        ("output stride w symbol", "SW"),
        ("output dilation h symbol", "DH"),
        ("output dilation w symbol", "DW"),
        ("output pad top symbol", "PT"),
        ("output pad bottom symbol", "PB"),
        ("output pad left symbol", "PL"),
        ("output pad right symbol", "PR"),
        ("tile f symbol", "TF"),
        ("tile c symbol", "TC"),
        ("tile n symbol", "TN"),
        ("tile ho symbol", "THO"),
        ("tile wo symbol", "TWO"),
        ("input", "!nn.memory<[#symbol.expr<B>, #symbol.expr<N>, #symbol.expr<XH>, #symbol.expr<XW>]"),
        ("weight", "!nn.memory<[#symbol.expr<C>, #symbol.expr<N>, #symbol.expr<KH>, #symbol.expr<KW>]"),
        ("bias", "!nn.memory<[#symbol.expr<C>]"),
        ("optional bias data ptr", "memory.get_data"),
        ("optional bias present guard", "symbol.ne"),
        ("memory-pool backing", "arch.get_dynamic_memory"),
        ("memory-pool view", "dma.view"),
    )
    static_memory_fragments = (
        (
            "output",
            f"!nn.memory<[#symbol.expr<{actual_output_shape[0]}>, #symbol.expr<{actual_output_shape[1]}>, "
            f"#symbol.expr<{actual_output_shape[2]}>, #symbol.expr<{actual_output_shape[3]}>]",
        ),
        (
            "input",
            f"!nn.memory<[#symbol.expr<{actual_input_shape[0]}>, #symbol.expr<{actual_input_shape[1]}>, "
            f"#symbol.expr<{actual_input_shape[2]}>, #symbol.expr<{actual_input_shape[3]}>]",
        ),
        (
            "weight",
            f"!nn.memory<[#symbol.expr<{actual_weight_shape[0]}>, #symbol.expr<{actual_weight_shape[1]}>, "
            f"#symbol.expr<{actual_weight_shape[2]}>, #symbol.expr<{actual_weight_shape[3]}>]",
        ),
    )
    old_symbol_fragments = (
        ("old output", "!nn.memory<[#symbol.expr<s1>, #symbol.expr<s2>, #symbol.expr<s3>, #symbol.expr<s4>]"),
        ("old input", "!nn.memory<[#symbol.expr<s1>, #symbol.expr<s5>, #symbol.expr<s6>, #symbol.expr<s7>]"),
        ("old weight", "!nn.memory<[#symbol.expr<s2>, #symbol.expr<s5>, #symbol.expr<3>, #symbol.expr<3>]"),
    )
    for label, fragment in required_dynamic_fragments:
        if fragment not in module_text:
            raise AssertionError(f"dynamic {label} fragment missing from lowered IR: {fragment}")
    for label, fragment in static_memory_fragments:
        if fragment in module_text:
            raise AssertionError(f"lowered IR unexpectedly contains static {label} memory shape: {fragment}")
    for label, fragment in old_symbol_fragments:
        if fragment in module_text:
            raise AssertionError(f"lowered IR unexpectedly contains {label} anonymous memory shape: {fragment}")
    forbidden_fragments = (
        ("dma.alloc", "dma.alloc"),
        ("allalloc", "allalloc"),
    )
    for label, fragment in forbidden_fragments:
        if fragment in module_text:
            raise AssertionError(f"lowered IR unexpectedly contains memory-pool forbidden {label}: {fragment}")


def _execute_device_source(source: str, real_args: tuple[Conv2dRuntimeArg, ...]) -> None:
    """编译并执行 lowering 生成的 root entry。


    功能说明:
    - 使用公开 `ExecutionEngine` 编译 `gen_kernel` 生成的完整源码。
    - 执行入口固定为 lowering 生成的 root wrapper，保留 `npu_demo::launch` block 分发语义。
    - `CompiledKernel` 使用完立即关闭，释放临时编译目录。

    使用示例:
    - `_execute_device_source(source, (out, input_tensor, weight, 8, 8, 1, 1, 1, 2, 3, 4, 7, 18, 3, 8, 8))`
    """

    compiled_kernel = ExecutionEngine(target="npu_demo").compile(source=source, function=ROOT_ENTRY_NAME)
    try:
        execute_result = compiled_kernel.execute(args=real_args)
        if not execute_result.ok:
            raise RuntimeError(f"{CASE_NAME}: execute failed: {execute_result.failure_phrase}")
    finally:
        compiled_kernel.close()


def _assert_source_dump_matches(source: str) -> None:
    """校验生成源码与公开 dump/source.cpp 一致。


    功能说明:
    - 读取 `kernel/dump/conv2d/inputs_dynamic_tile_dynamic/source.cpp`。
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
    for marker in (ROOT_ENTRY_NAME, "npu_demo::launch"):
        if marker not in dump_source:
            raise AssertionError(f"{CASE_NAME}: source dump missing marker {marker}")


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
    """运行动态输入、动态 tile 的 conv2d demo。


    功能说明:
    - 使用 per-run random profile 构造 runtime shape、conv attrs、tile 与 NumPy ndarray 输入。
    - 写入 `kernel/dump/conv2d/inputs_dynamic_tile_dynamic/`。
    - 编译期以符号 memory shape 生成 IR/source，运行期以 本次随机选中 tensor shape 执行 root wrapper。
    - 分别用 NumPy conv2d 与 `conv2d + bias[None, :, None, None]` 参考结果校验输出。

    使用示例:
    - `python3 kernel/conv2d/inputs_dynamic_tile_dynamic.py`
    """

    global _DYNAMIC_SHAPE_SEED, _DYNAMIC_TILE_SELECTION_SEED, _DYNAMIC_TILE_ARGS

    stride_args = (8, 8)
    dilation_args = (1, 1)
    system_rng = random.SystemRandom()
    for _attempt in range(128):
        shape_seed = system_rng.randrange(1, 2**31)
        tile_seed = system_rng.randrange(1, 2**31)
        shape_rng = random.Random(shape_seed)
        n_size = shape_rng.randint(4, 6)
        c_size = shape_rng.randint(48, 64)
        h_size = shape_rng.randint(241, 289)
        w_size = shape_rng.randint(225, 273)
        f_size = shape_rng.randint(18, 24)
        kh_size = shape_rng.choice((3, 5))
        kw_size = shape_rng.choice((3, 5))
        padding_args = tuple(shape_rng.choice((0, 1, 2, 3, 4)) for _ in range(4))
        tile_args = random.Random(tile_seed).choice(_DYNAMIC_TILE_CANDIDATES)
        ho_size = ((h_size + padding_args[0] + padding_args[1] - dilation_args[0] * (kh_size - 1) - 1) // stride_args[0]) + 1
        wo_size = ((w_size + padding_args[2] + padding_args[3] - dilation_args[1] * (kw_size - 1) - 1) // stride_args[1]) + 1
        tile_f, tile_c, tile_n, tile_ho, tile_wo = tile_args
        has_multi_tile = (
            f_size > tile_f
            and c_size > tile_c
            and n_size > tile_n
            and ho_size > tile_ho
            and wo_size > tile_wo
        )
        tail_count = sum(
            (
                f_size % tile_f != 0,
                c_size % tile_c != 0,
                n_size % tile_n != 0,
                ho_size % tile_ho != 0,
                wo_size % tile_wo != 0,
            )
        )
        if has_multi_tile and tail_count == 5:
            break
    else:
        raise RuntimeError("conv2d dynamic/dynamic random profile failed to satisfy tile invariants")

    _DYNAMIC_SHAPE_SEED = shape_seed
    _DYNAMIC_TILE_SELECTION_SEED = tile_seed
    _DYNAMIC_TILE_ARGS = tile_args
    rng = np.random.default_rng(_DYNAMIC_SHAPE_SEED)
    input_tensor = rng.standard_normal((n_size, c_size, h_size, w_size), dtype=np.float32)
    weight = rng.standard_normal((f_size, c_size, kh_size, kw_size), dtype=np.float32)
    bias = rng.standard_normal((f_size,), dtype=np.float32)
    absent_out = np.zeros((n_size, f_size, ho_size, wo_size), dtype=np.float32)
    present_out = np.zeros((n_size, f_size, ho_size, wo_size), dtype=np.float32)
    absent_expected = _conv2d_nchw_reference(input_tensor, weight, stride=stride_args, dilation=dilation_args, padding=padding_args)
    present_expected = absent_expected + bias[None, :, None, None]
    module, source = run_lowering_demo(
        CASE_NAME,
        conv2d_inputs_dynamic_tile_dynamic_kernel,
        *_symbolic_compile_args(),
    )
    module_text = str(module)
    _assert_dynamic_memory_ir(
        module_text,
        (n_size, f_size, ho_size, wo_size),
        (n_size, c_size, h_size, w_size),
        (f_size, c_size, kh_size, kw_size),
    )
    _assert_source_dump_matches(source)
    max_abs_diff_by_case = {}
    for bias_case in _BIAS_CASE_ORDER:
        if bias_case == "absent":
            _execute_device_source(
                source,
                (absent_out, input_tensor, weight, None, *stride_args, *dilation_args, *padding_args, *tile_args),
            )
            max_abs_diff_by_case[bias_case] = _assert_outputs_close(absent_out, absent_expected, atol=1e-4, rtol=1e-4)
            continue
        _execute_device_source(
            source,
            (present_out, input_tensor, weight, bias, *stride_args, *dilation_args, *padding_args, *tile_args),
        )
        max_abs_diff_by_case[bias_case] = _assert_outputs_close(present_out, present_expected, atol=1e-4, rtol=1e-4)
    absent_max_abs_diff = max_abs_diff_by_case["absent"]
    present_max_abs_diff = max_abs_diff_by_case["present"]
    print(
        "[ARGS] "
        "profile=per-run-random dynamic_ir=symbolic runtime=random "
        f"shape_seed={_DYNAMIC_SHAPE_SEED} "
        f"input={(n_size, c_size, h_size, w_size)} weight={(f_size, c_size, kh_size, kw_size)} "
        f"stride={stride_args} dilation={dilation_args} padding={padding_args} "
        f"tile_seed={_DYNAMIC_TILE_SELECTION_SEED} tile_candidates={_DYNAMIC_TILE_CANDIDATES} selected_tile={tile_args} "
        f"output={(n_size, f_size, ho_size, wo_size)} bias_case_order={_BIAS_CASE_ORDER} bias_rank=1"
    )
    print(
        "[IR] dynamic memory evidence: output/input/weight semantic symbolic memory present; "
        "memory-pool arch.get_dynamic_memory + dma.view present; dma.alloc/allalloc absent"
    )
    print(f"[CHECK] {CASE_NAME}/absent_bias max_abs_diff={absent_max_abs_diff}")
    print(f"[CHECK] {CASE_NAME}/present_bias max_abs_diff={present_max_abs_diff}")


if __name__ == "__main__":
    main()
