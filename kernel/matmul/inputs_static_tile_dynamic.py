"""Matmul demo with static inputs and symbolic tiles.


功能说明:
- 实现 `inputs 静 + tile 动` 的二维 matmul kernel demo。
- 脚本入口每次运行先随机生成 `shape_seed/tile_seed`，再从受控范围选择本次 shape 与 runtime tile。
- static case 将本次随机 shape 具体化到 IR memory type。
- tile 使用 `TILE_H/TILE_W/TILE_K` 符号参数，运行期从轻量候选集合随机选择 int scalar 绑定，并通过 lowering 生成的 launch wrapper 触发真实 multi-block 执行。
- H/W/K 均大于对应 runtime tile，且至少触发两次 tile loop；局部 staging / accumulator 按 `min(tile, dim - iv)`
  effective tile 分配，覆盖 H/W/K 尾块并触发 lowering 中的 padded backing / logical alias 验收。
- K/reduce 维按 `tile_k` 分块：每个 H/W 输出 tile 初始化局部 accumulator，K loop 内用 `kernel.matmul/kernel.add` out-first helper 累加 partial，K loop 后按 optional rank-1 bias 分支累加并最终写回 output。

API 列表:
- `matmul_inputs_static_tile_dynamic_kernel(out: Tensor[f32, M, N], lhs: Tensor[f32, M, K], rhs: Tensor[f32, K, N], bias: Tensor[f32, N], tile_h: SymbolDim, tile_w: SymbolDim, tile_k: SymbolDim) -> None`
- `main() -> None`

使用示例:
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 kernel/matmul/inputs_static_tile_dynamic.py`

关联文件:
- 功能实现: `kernel/matmul/inputs_static_tile_dynamic.py`
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
from kernel_gen.operation.dma import alloc, broadcast, deslice, fill, reshape, view
from kernel_gen.operation.scf import loop
from kernel_gen.symbol_variable.memory import Memory, MemorySpace
from kernel_gen.symbol_variable.symbol_dim import SymbolDim
from kernel_gen.symbol_variable.type import NumericType

CASE_NAME = "matmul/inputs_static_tile_dynamic"
WRAPPER_ENTRY_NAME = "matmul_inputs_static_tile_dynamic_kernel"
TILE_SELECTION_SEED = 2026051713
TILE_ARG_CANDIDATES = ((64, 80, 64), (72, 88, 56), (48, 96, 64))
TILE_ARGS = random.Random(TILE_SELECTION_SEED).choice(TILE_ARG_CANDIDATES)
BIAS_CASE_ORDER_SEED = 2026051751
BIAS_CASE_ORDER = tuple(random.Random(BIAS_CASE_ORDER_SEED).sample(("absent", "present"), 2))
_STATIC_SHAPE_SEED = 2026051602
_STATIC_SHAPE_RNG = random.Random(_STATIC_SHAPE_SEED)
_STATIC_M = _STATIC_SHAPE_RNG.randint(160, 256)
_STATIC_K = _STATIC_SHAPE_RNG.randint(160, 256)
_STATIC_N = _STATIC_SHAPE_RNG.randint(160, 256)
MatmulCompileArg: TypeAlias = "Memory | SymbolDim"
MatmulRuntimeArg: TypeAlias = "np.ndarray | int | None"


def matmul_inputs_static_tile_dynamic_kernel(
    out: "Tensor[f32, 197, 184]",
    lhs: "Tensor[f32, 197, 178]",
    rhs: "Tensor[f32, 178, 184]",
    bias: "Tensor[f32, 184]",
    tile_h: SymbolDim,
    tile_w: SymbolDim,
    tile_k: SymbolDim,
) -> None:
    """执行静态输入、符号 tile 的 matmul。


    功能说明:
    - 输入和输出 shape 来自 `Tensor[...]` 静态标注。
    - `tile_h/tile_w/tile_k` 作为 `SymbolDim` 参数进入编译 IR，不在 Python 函数体内常量化。
    - K 维通过内层 loop 切分，局部 buffer 均按当前 effective tile shape 分配，
      每个 partial 通过 `kernel.matmul/kernel.add` out-first helper 累加到同一个局部 accumulator。
    - runtime bias 非空时，在 K reduce 后、写回 output 前广播 rank-1 bias 并累加。

    使用示例:
    - `matmul_inputs_static_tile_dynamic_kernel(out, lhs, rhs, bias, 13, 11, 5)`
    """

    h_size = lhs.get_shape()[0]
    k_size = lhs.get_shape()[1]
    w_size = rhs.get_shape()[1]

    for h0 in loop(0, h_size, tile_h):
        for w0 in loop(0, w_size, tile_w):
            cur_h = min(tile_h, h_size - h0)
            cur_w = min(tile_w, w_size - w0)
            acc = alloc([cur_h, cur_w], NumericType.Float32, MemorySpace.TSM)
            fill(acc, 0)
            bias_tile = alloc([cur_w], NumericType.Float32, MemorySpace.TSM)
            fill(bias_tile, 0)
            bias_row = reshape(bias_tile, [1, cur_w])
            bias_full = alloc([cur_h, cur_w], NumericType.Float32, MemorySpace.TSM)
            for k0 in loop(0, k_size, tile_k):
                cur_k = min(tile_k, k_size - k0)
                lhs_tile = alloc([cur_h, cur_k], NumericType.Float32, MemorySpace.TSM)
                rhs_tile = alloc([cur_k, cur_w], NumericType.Float32, MemorySpace.TSM)
                fill(lhs_tile, 0)
                fill(rhs_tile, 0)
                lhs_region = view(lhs, [h0, k0], [cur_h, cur_k], [1, 1])
                rhs_region = view(rhs, [k0, w0], [cur_k, cur_w], [1, 1])
                deslice(lhs_tile, lhs_region, [0, 0], [cur_h, cur_k], [1, 1])
                deslice(rhs_tile, rhs_region, [0, 0], [cur_k, cur_w], [1, 1])
                partial = alloc([cur_h, cur_w], NumericType.Float32, MemorySpace.TSM)
                kernel.matmul(partial, lhs_tile, rhs_tile)
                kernel.add(acc, acc, partial)
            if bias is not None:
                bias_region = view(bias, [w0], [cur_w], [1])
                deslice(bias_tile, bias_region, [0], [cur_w], [1])
                broadcast(bias_full, bias_row)
                kernel.add(acc, acc, bias_full)
            out_region = view(acc, [0, 0], [cur_h, cur_w], [1, 1])
            deslice(out, out_region, [h0, w0], [cur_h, cur_w], [1, 1])


def _symbolic_compile_args() -> tuple[MatmulCompileArg, ...]:
    """构造 static input / symbolic tile 的编译参数。


    功能说明:
    - output/lhs/rhs memory 使用 本次随机选中 static shape：`197x184`、`197x178`、`178x184`。
    - static case 将这些 本次随机选中 值具体化到 IR memory type。
    - tile 参数固定使用 `TILE_H/TILE_W/TILE_K`，用于锁定编译期符号 tile。

    使用示例:
    - `_symbolic_compile_args()`
    """

    return (
        Memory([_STATIC_M, _STATIC_N], NumericType.Float32),
        Memory([_STATIC_M, _STATIC_K], NumericType.Float32),
        Memory([_STATIC_K, _STATIC_N], NumericType.Float32),
        Memory([_STATIC_N], NumericType.Float32),
        SymbolDim("TILE_H"),
        SymbolDim("TILE_W"),
        SymbolDim("TILE_K"),
    )


def _assert_static_symbolic_tile_ir(module_text: str) -> None:
    """校验 lowering 后 IR 保留 static memory 与符号 tile。


    功能说明:
    - 确认 IR 包含 本次随机选中 static memory shape。
    - 确认 tile 来自 `TILE_H/TILE_W/TILE_K` 参数，K loop step 是 `TILE_K`。

    使用示例:
    - `_assert_static_symbolic_tile_ir(str(module))`
    """

    required_fragments = (
        f"!nn.memory<[#symbol.expr<{_STATIC_M}>, #symbol.expr<{_STATIC_N}>]",
        f"!nn.memory<[#symbol.expr<{_STATIC_M}>, #symbol.expr<{_STATIC_K}>]",
        f"!nn.memory<[#symbol.expr<{_STATIC_K}>, #symbol.expr<{_STATIC_N}>]",
        f"!nn.memory<[#symbol.expr<{_STATIC_N}>]",
        "!symbol.int<#symbol.expr<TILE_H>>",
        "!symbol.int<#symbol.expr<TILE_W>>",
        "!symbol.int<#symbol.expr<TILE_K>>",
        "step = #symbol.expr<TILE_K>",
        '"kernel.matmul"',
        '"kernel.binary_elewise"',
        '"dma.reinterpret"',
        '"dma.deslice"',
        "memory.get_data",
        "symbol.ne",
    )
    forbidden_fragments = (
        "!nn.memory<[#symbol.expr<H>, #symbol.expr<W>]",
        "!nn.memory<[#symbol.expr<H>, #symbol.expr<K>]",
        "!nn.memory<[#symbol.expr<K>, #symbol.expr<W>]",
        "!nn.memory<[#symbol.expr<s1>",
    )
    for fragment in required_fragments:
        if fragment not in module_text:
            raise AssertionError(f"static symbolic tile matmul IR missing fragment: {fragment}")
    for fragment in forbidden_fragments:
        if fragment in module_text:
            raise AssertionError(f"static symbolic tile matmul IR unexpectedly contains fragment: {fragment}")


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


def _assert_source_dump_matches(source: str) -> None:
    """校验生成源码与公开 dump/source.cpp 一致。


    功能说明:
    - 读取 `kernel/dump/matmul/inputs_static_tile_dynamic/source.cpp`。
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


def _execute_lowering_source(source: str, real_args: tuple[MatmulRuntimeArg, ...]) -> None:
    """编译并执行 lowering 生成的 launch wrapper。


    功能说明:
    - 使用公开 `ExecutionEngine` 编译 `run_lowering_demo(...)` 生成的源码。
    - 通过 wrapper 触发 `npu_demo::launch<...>`，确保 multi-block 执行现场绑定真实 `block_id()`。

    使用示例:
    - `_execute_lowering_source(source, (out, lhs, rhs, 13, 11, 5))`
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
    """运行静态输入、动态 tile 的 matmul demo。


    功能说明:
    - 使用 per-run random profile 选出的 `197x178x184` matmul shape。
    - 运行期 tile 由 per-run random 候选集合选出，编译期 tile 保持 `TILE_H/TILE_W/TILE_K` 符号。
    - 编译期以 static memory / symbolic tile 生成 lowering IR 与 npu_demo source。
    - 运行期分别执行 bias absent / present launch wrapper，并用 NumPy 参考校验输出。

    使用示例:
    - `python3 kernel/matmul/inputs_static_tile_dynamic.py`
    """

    global _STATIC_SHAPE_SEED, _STATIC_M, _STATIC_K, _STATIC_N
    global TILE_SELECTION_SEED, TILE_ARGS

    system_rng = random.SystemRandom()
    for _attempt in range(128):
        shape_seed = system_rng.randrange(1, 2**31)
        tile_seed = system_rng.randrange(1, 2**31)
        shape_rng = random.Random(shape_seed)
        candidate_m = shape_rng.randint(160, 256)
        candidate_k = shape_rng.randint(160, 256)
        candidate_n = shape_rng.randint(160, 256)
        candidate_tile = random.Random(tile_seed).choice(TILE_ARG_CANDIDATES)
        has_multi_tile = (
            candidate_m > candidate_tile[0]
            and candidate_n > candidate_tile[1]
            and candidate_k > candidate_tile[2]
        )
        has_tail = (
            candidate_m % candidate_tile[0] != 0
            and candidate_n % candidate_tile[1] != 0
            and candidate_k % candidate_tile[2] != 0
        )
        if has_multi_tile and has_tail:
            break
    else:
        raise RuntimeError("matmul static/dynamic random profile failed to satisfy tile invariants")

    _STATIC_SHAPE_SEED = shape_seed
    _STATIC_M = candidate_m
    _STATIC_K = candidate_k
    _STATIC_N = candidate_n
    TILE_SELECTION_SEED = tile_seed
    TILE_ARGS = candidate_tile
    matmul_inputs_static_tile_dynamic_kernel.__annotations__.update(
        {
            "out": f"Tensor[f32, {_STATIC_M}, {_STATIC_N}]",
            "lhs": f"Tensor[f32, {_STATIC_M}, {_STATIC_K}]",
            "rhs": f"Tensor[f32, {_STATIC_K}, {_STATIC_N}]",
            "bias": f"Tensor[f32, {_STATIC_N}]",
        }
    )

    rng = np.random.default_rng(_STATIC_SHAPE_SEED)
    lhs = rng.standard_normal((_STATIC_M, _STATIC_K), dtype=np.float32)
    rhs = rng.standard_normal((_STATIC_K, _STATIC_N), dtype=np.float32)
    bias = rng.standard_normal((_STATIC_N,), dtype=np.float32)
    absent_out = np.empty((_STATIC_M, _STATIC_N), dtype=np.float32)
    present_out = np.empty((_STATIC_M, _STATIC_N), dtype=np.float32)
    absent_expected = np.matmul(lhs, rhs)
    present_expected = absent_expected + bias[None, :]

    module, source = run_lowering_demo(CASE_NAME, matmul_inputs_static_tile_dynamic_kernel, *_symbolic_compile_args())
    module_text = str(module)
    _assert_static_symbolic_tile_ir(module_text)
    _assert_accumulator_source(source)
    _assert_source_dump_matches(source)
    max_abs_diff_by_case = {}
    for bias_case in BIAS_CASE_ORDER:
        if bias_case == "absent":
            _execute_lowering_source(source, (absent_out, lhs, rhs, None, *TILE_ARGS))
            max_abs_diff_by_case[bias_case] = _assert_outputs_close(absent_out, absent_expected, atol=1e-3, rtol=1e-3)
            continue
        _execute_lowering_source(source, (present_out, lhs, rhs, bias, *TILE_ARGS))
        max_abs_diff_by_case[bias_case] = _assert_outputs_close(present_out, present_expected, atol=1e-3, rtol=1e-3)
    absent_max_abs_diff = max_abs_diff_by_case["absent"]
    present_max_abs_diff = max_abs_diff_by_case["present"]
    print(
        "[ARGS] "
        "profile=per-run-random static_memory=random-concrete dynamic_tile=symbolic-runtime "
        f"shape_seed={_STATIC_SHAPE_SEED} shape=(M={_STATIC_M},K={_STATIC_K},N={_STATIC_N}) "
        f"tile_seed={TILE_SELECTION_SEED} tile_candidates={TILE_ARG_CANDIDATES} selected_tile={TILE_ARGS} "
        f"bias_case_order={BIAS_CASE_ORDER} multi_tile=True tail=True bias_rank=1"
    )
    print(
        "[IR] static memory evidence: "
        f"本次随机选中 {_STATIC_M}x{_STATIC_K}x{_STATIC_N} memory concrete; TILE_H/TILE_W/TILE_K tile symbols present"
    )
    print(f"[CHECK] {CASE_NAME}/absent_bias max_abs_diff={absent_max_abs_diff}")
    print(f"[CHECK] {CASE_NAME}/present_bias max_abs_diff={present_max_abs_diff}")


if __name__ == "__main__":
    main()
