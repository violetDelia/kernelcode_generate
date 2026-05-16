"""Matmul demo with symbolic inputs and symbolic tiles.


功能说明:
- 实现 `inputs 动 + tile 动` 的二维 matmul kernel demo。
- 编译期 memory 使用 `H/K/W` 语义符号，tile 使用 `TILE_H/TILE_W/TILE_K` 符号参数。
- 运行期仍传入真实 NumPy ndarray 与 int tile，执行 device entry 后和 `np.matmul` 对齐。
- K/reduce 维按 `tile_k` 分块：每个 H/W 输出 tile 初始化局部 accumulator，K loop 内用 `kernel.matmul/kernel.add` out-first helper 累加 partial，K loop 后最终写回 output。
- H/W/K 尾块都通过 `min(tile, dim - iv)` 覆盖，避免只覆盖可整除 case。

API 列表:
- `matmul_inputs_dynamic_tile_dynamic_kernel(out: Tensor[f32, H, W], lhs: Tensor[f32, H, K], rhs: Tensor[f32, K, W], tile_h: SymbolDim, tile_w: SymbolDim, tile_k: SymbolDim) -> None`
- `main() -> None`

使用示例:
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 kernel/matmul/inputs_dynamic_tile_dynamic.py`

关联文件:
- 功能实现: `kernel/matmul/inputs_dynamic_tile_dynamic.py`
- 公共运行器: `kernel/runner.py`
- pytest: `test/kernel/test_matmul_symbolic_memory_genkernel.py`
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
from kernel_gen.operation.dma import alloc, deslice, fill, view
from kernel_gen.operation.scf import loop
from kernel_gen.symbol_variable.memory import Memory, MemorySpace
from kernel_gen.symbol_variable.symbol_dim import SymbolDim
from kernel_gen.symbol_variable.type import NumericType

CASE_NAME = "matmul/inputs_dynamic_tile_dynamic"
DEVICE_ENTRY_NAME = "matmul_inputs_dynamic_tile_dynamic_kernel_device"
TILE_ARGS = (80, 96, 72)
MatmulCompileArg: TypeAlias = "Memory | SymbolDim"
MatmulRuntimeArg: TypeAlias = "np.ndarray | int"


def matmul_inputs_dynamic_tile_dynamic_kernel(
    out: "Tensor[f32, H, W]",
    lhs: "Tensor[f32, H, K]",
    rhs: "Tensor[f32, K, W]",
    tile_h: SymbolDim,
    tile_w: SymbolDim,
    tile_k: SymbolDim,
) -> None:
    """执行符号输入、符号 tile 的 matmul。


    功能说明:
    - 输入和输出 shape 全部来自 `Tensor[...]` 的 `H/K/W` 符号维度。
    - `tile_h/tile_w/tile_k` 作为 `SymbolDim` 参数进入编译 IR，不在 Python 函数体内常量化。
    - K 维通过内层 loop 切分，每个 partial 通过 `kernel.matmul/kernel.add` out-first helper 累加到同一个局部 accumulator，loop 后只写回一次 output tile。

    使用示例:
    - `matmul_inputs_dynamic_tile_dynamic_kernel(out, lhs, rhs, 6, 7, 5)`
    """

    h_size = lhs.get_shape()[0]
    k_size = lhs.get_shape()[1]
    w_size = rhs.get_shape()[1]

    for h0 in loop(0, h_size, tile_h):
        for w0 in loop(0, w_size, tile_w):
            cur_h = min(tile_h, h_size - h0)
            cur_w = min(tile_w, w_size - w0)
            acc = alloc([tile_h, tile_w], NumericType.Float32, MemorySpace.TSM)
            fill(acc, 0)
            for k0 in loop(0, k_size, tile_k):
                cur_k = min(tile_k, k_size - k0)
                lhs_tile = alloc([tile_h, tile_k], NumericType.Float32, MemorySpace.TSM)
                rhs_tile = alloc([tile_k, tile_w], NumericType.Float32, MemorySpace.TSM)
                fill(lhs_tile, 0)
                fill(rhs_tile, 0)
                lhs_region = view(lhs, [h0, k0], [cur_h, cur_k], [1, 1])
                rhs_region = view(rhs, [k0, w0], [cur_k, cur_w], [1, 1])
                deslice(lhs_tile, lhs_region, [0, 0], [cur_h, cur_k], [1, 1])
                deslice(rhs_tile, rhs_region, [0, 0], [cur_k, cur_w], [1, 1])
                partial = alloc([tile_h, tile_w], NumericType.Float32, MemorySpace.TSM)
                kernel.matmul(partial, lhs_tile, rhs_tile)
                kernel.add(acc, acc, partial)
            out_region = view(acc, [0, 0], [cur_h, cur_w], [1, 1])
            deslice(out, out_region, [h0, w0], [cur_h, cur_w], [1, 1])


def _symbolic_compile_args() -> tuple[MatmulCompileArg, ...]:
    """构造 dynamic demo 的符号编译参数。


    功能说明:
    - output/lhs/rhs memory 分别使用 `H/W`、`H/K`、`K/W` 语义符号。
    - tile 参数固定使用 `TILE_H/TILE_W/TILE_K`，用于锁定编译期符号 IR。

    使用示例:
    - `_symbolic_compile_args()`
    """

    return (
        Memory(["H", "W"], NumericType.Float32),
        Memory(["H", "K"], NumericType.Float32),
        Memory(["K", "W"], NumericType.Float32),
        SymbolDim("TILE_H"),
        SymbolDim("TILE_W"),
        SymbolDim("TILE_K"),
    )


def _assert_dynamic_memory_ir(
    module_text: str,
    actual_output_shape: tuple[int, int],
    actual_lhs_shape: tuple[int, int],
    actual_rhs_shape: tuple[int, int],
) -> None:
    """校验 lowering 后 IR 保留 dynamic demo 的符号 memory。


    功能说明:
    - 确认 IR 包含 `H/K/W` memory 与 `TILE_H/TILE_W/TILE_K`。
    - 确认 IR 不回退为本次真实运行 shape 或旧匿名 `s1/s2/...`。

    使用示例:
    - `_assert_dynamic_memory_ir(str(module), (250, 228), (250, 192), (192, 228))`
    """

    required_fragments = (
        "!nn.memory<[#symbol.expr<H>, #symbol.expr<W>]",
        "!nn.memory<[#symbol.expr<H>, #symbol.expr<K>]",
        "!nn.memory<[#symbol.expr<K>, #symbol.expr<W>]",
        "!symbol.int<#symbol.expr<TILE_H>>",
        "!symbol.int<#symbol.expr<TILE_W>>",
        "!symbol.int<#symbol.expr<TILE_K>>",
        "step = #symbol.expr<TILE_K>",
        '"kernel.matmul"',
        '"kernel.binary_elewise"',
        '"dma.view"',
        '"dma.deslice"',
    )
    forbidden_fragments = (
        f"!nn.memory<[#symbol.expr<{actual_output_shape[0]}>, #symbol.expr<{actual_output_shape[1]}>]",
        f"!nn.memory<[#symbol.expr<{actual_lhs_shape[0]}>, #symbol.expr<{actual_lhs_shape[1]}>]",
        f"!nn.memory<[#symbol.expr<{actual_rhs_shape[0]}>, #symbol.expr<{actual_rhs_shape[1]}>]",
        "!nn.memory<[#symbol.expr<s1>",
    )
    for fragment in required_fragments:
        if fragment not in module_text:
            raise AssertionError(f"dynamic symbolic matmul IR missing fragment: {fragment}")
    for fragment in forbidden_fragments:
        if fragment in module_text:
            raise AssertionError(f"dynamic symbolic matmul IR unexpectedly contains fragment: {fragment}")


def _assert_accumulator_source(source: str) -> None:
    """校验源码中 accumulator 先累加后最终写回。


    功能说明:
    - 只检查公开生成源码的关键顺序：`fill -> matmul -> add -> output deslice`。
    - 防止 K loop partial 直接覆盖 output tile 的回退。

    使用示例:
    - `_assert_accumulator_source(source)`
    """

    fill_index = source.index("fill<")
    matmul_index = source.index("matmul<")
    add_index = source.index("add<")
    output_deslice_index = source.index("deslice(arg0", add_index)
    if not (fill_index < matmul_index < add_index < output_deslice_index):
        raise AssertionError("matmul accumulator source order must be fill -> matmul -> add -> output deslice")


def _execute_device_source(source: str, real_args: tuple[MatmulRuntimeArg, ...]) -> None:
    """编译并执行 lowering 生成的 device entry。


    功能说明:
    - 使用公开 `ExecutionEngine` 编译 `run_lowering_demo(...)` 生成的源码。
    - 直接执行 lowering 生成的 device 函数，运行期传入真实 tensor 与 int tile。

    使用示例:
    - `_execute_device_source(source, (out, lhs, rhs, 6, 7, 5))`
    """

    compiled_kernel = ExecutionEngine(target="npu_demo").compile(source=source, function=DEVICE_ENTRY_NAME)
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
    """校验真实输出与 NumPy matmul 参考一致。


    功能说明:
    - 返回最大绝对误差，供 demo 输出 `[CHECK]` 摘要。
    - 超出容差时抛 `AssertionError`。

    使用示例:
    - `_assert_outputs_close(out, np.matmul(lhs, rhs), atol=1e-3, rtol=1e-3)`
    """

    max_abs_diff = float(np.max(np.abs(output - expected)))
    if not np.allclose(output, expected, atol=atol, rtol=rtol):
        raise AssertionError(
            f"{CASE_NAME}: output does not match NumPy reference "
            f"(max_abs_diff={max_abs_diff}, atol={atol}, rtol={rtol})"
        )
    return max_abs_diff


def main() -> None:
    """运行动态输入、动态 tile 的 matmul demo。


    功能说明:
    - 使用固定 seed 选择不整除 H/W/K tile 的真实 shape。
    - 编译期以符号 memory/tile 生成 lowering IR 与 npu_demo source。
    - 运行期执行 device entry，并用 `np.matmul(lhs, rhs)` 校验输出。

    使用示例:
    - `python3 kernel/matmul/inputs_dynamic_tile_dynamic.py`
    """

    shape_rng = random.Random(2026051603)
    h_size = shape_rng.randint(160, 256)
    k_size = shape_rng.randint(160, 256)
    w_size = shape_rng.randint(160, 256)
    rng = np.random.default_rng(2026051603)
    lhs = rng.standard_normal((h_size, k_size), dtype=np.float32)
    rhs = rng.standard_normal((k_size, w_size), dtype=np.float32)
    out = np.empty((h_size, w_size), dtype=np.float32)
    expected = np.matmul(lhs, rhs)

    module, source = run_lowering_demo(CASE_NAME, matmul_inputs_dynamic_tile_dynamic_kernel, *_symbolic_compile_args())
    module_text = str(module)
    _assert_dynamic_memory_ir(module_text, tuple(out.shape), tuple(lhs.shape), tuple(rhs.shape))
    _assert_accumulator_source(source)
    _execute_device_source(source, (out, lhs, rhs, *TILE_ARGS))
    max_abs_diff = _assert_outputs_close(out, expected, atol=1e-3, rtol=1e-3)
    print(module_text)
    print(source)
    print(f"[ARGS] seed=2026051603 shape=(M={h_size},K={k_size},N={w_size}) tile={TILE_ARGS} multi_tile=True tail=True")
    print("[IR] dynamic memory evidence: H/K/W memory and TILE_H/TILE_W/TILE_K tile present; static and anonymous shapes absent")
    print(f"[CHECK] {CASE_NAME} max_abs_diff={max_abs_diff}")


if __name__ == "__main__":
    main()
