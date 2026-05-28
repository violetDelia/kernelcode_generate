"""Flash attention demo with dynamic inputs and dynamic tiles.


功能说明:
- 实现 `inputs 动 + tile 动` 的 Flash Attention kernel demo。
- 输入 batch/head/sequence/dim 使用 `B/H/SL/D` 符号维度，并由本次随机选出的真实 NumPy ndarray 运行时 shape 绑定。
- 本次随机 shape 所有维度均不超过 1024，序列长度大于两类 tile 并触发 query/key 尾块。
- tile 由 `br/bc` runtime `SymbolDim` 参数绑定，运行期 tile 从候选集合随机选出。
- 使用四层循环 `batch -> head -> query block -> key/value block` 实现 online softmax。
- softmax 显式展开为 running max、running sum、`kernel.exp` 与归一化，不调用 `nn.softmax`。
- 通过 `ExecutionEngine` 真实执行 lowering 生成的源码，并和 NumPy softmax attention 参考结果对齐。

API 列表:
- `flash_attention_inputs_dynamic_tile_dynamic_kernel(out: Tensor[f32, B, H, SL, D], q: Tensor[f32, B, H, SL, D], k: Tensor[f32, B, H, SL, D], v: Tensor[f32, B, H, SL, D], br: SymbolDim, bc: SymbolDim) -> None`
- `main() -> None`

使用示例:
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 kernel/flash_attention/inputs_dynamic_tile_dynamic.py`

关联文件:
- 功能实现: `kernel/flash_attention/inputs_dynamic_tile_dynamic.py`
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
from kernel_gen.operation.dma import alloc, broadcast, deslice, fill, reshape, view
from kernel_gen.operation.nn import transpose
from kernel_gen.operation.scf import loop
from kernel_gen.symbol_variable.memory import Memory, MemorySpace
from kernel_gen.symbol_variable.symbol_dim import SymbolDim
from kernel_gen.symbol_variable.type import NumericType

CASE_NAME = "flash_attention/inputs_dynamic_tile_dynamic"
WRAPPER_ENTRY_NAME = "flash_attention_inputs_dynamic_tile_dynamic_kernel"
_DYNAMIC_SHAPE_SEED = 2026052723
_DYNAMIC_SHAPE_RNG = random.Random(_DYNAMIC_SHAPE_SEED)
_DYNAMIC_BATCH = _DYNAMIC_SHAPE_RNG.choice((1, 2))
_DYNAMIC_HEADS = _DYNAMIC_SHAPE_RNG.choice((4, 8))
_DYNAMIC_SEQ_LEN = _DYNAMIC_SHAPE_RNG.choice((257, 321, 389))
_DYNAMIC_DIM = _DYNAMIC_SHAPE_RNG.choice((48, 64, 80))
_TILE_SELECTION_SEED = 2026051729
_TILE_CANDIDATES = ((48, 64), (64, 80), (80, 96))
_RUNTIME_TILE_ARGS = random.Random(_TILE_SELECTION_SEED).choice(_TILE_CANDIDATES)
FlashCompileArg: TypeAlias = "Memory | SymbolDim"
FlashRuntimeArg: TypeAlias = "np.ndarray | int"


def _softmax_last_axis(value: np.ndarray) -> np.ndarray:
    """计算最后一维 softmax。


    功能说明:
    - 使用 max-shift 形式提升 NumPy 参考值稳定性。
    - 只服务本 demo 的 reference 计算，不新增跨文件 helper。

    使用示例:
    - `_softmax_last_axis(scores)`
    """

    shifted = value - np.max(value, axis=-1, keepdims=True)
    exp_value = np.exp(shifted).astype(np.float32)
    return exp_value / np.sum(exp_value, axis=-1, keepdims=True)


def _flash_attention_reference(q: np.ndarray, k: np.ndarray, v: np.ndarray) -> np.ndarray:
    """计算 Flash Attention NumPy 参考输出。


    功能说明:
    - 参考语义固定为 `softmax(q @ k^T) @ v`。
    - 输入布局为 `[B, H, SL, D]`。

    使用示例:
    - `_flash_attention_reference(q, k, v)`
    """

    score = np.matmul(q, np.swapaxes(k, -1, -2))
    return np.matmul(_softmax_last_axis(score), v).astype(np.float32)


def flash_attention_inputs_dynamic_tile_dynamic_kernel(
    out: "Tensor[f32, B, H, SL, D]",
    q: "Tensor[f32, B, H, SL, D]",
    k: "Tensor[f32, B, H, SL, D]",
    v: "Tensor[f32, B, H, SL, D]",
    br: SymbolDim,
    bc: SymbolDim,
) -> None:
    """执行动态输入、动态 tile 的 Flash Attention。


    功能说明:
    - `Q/K/V/out` 的 batch/head/sequence/dim 维度为符号维度。
    - `br/bc` 使用 本次随机选中 runtime scalar 作为 query block 与 key/value block 两层分块大小。
    - 主计算入口使用 kernel out-first helper，softmax 以 running max/running sum online 形式展开。
    - 输出写回 `out[B, H, SL, D]`。

    使用示例:
    - `flash_attention_inputs_dynamic_tile_dynamic_kernel(out, q, k, v, 64, 64)`
    """

    batch_size, head_size, seq_len, dim_size = q.get_shape()
    unit_tile = br - br + 1
    for b0 in loop(0, batch_size, 1):
        for h0 in loop(0, head_size, 1):
            for m0 in loop(0, seq_len, br):
                cur_br = min(br, seq_len - m0)
                q_full_4d = alloc([1, 1, br, dim_size], NumericType.Float32, MemorySpace.TSM)
                fill(q_full_4d, 0)
                q_4d = view(q, [b0, h0, m0, 0], [1, 1, cur_br, dim_size], [1, 1, 1, 1])
                deslice(q_full_4d, q_4d, [0, 0, 0, 0], [1, 1, cur_br, dim_size], [1, 1, 1, 1])
                q_full = reshape(q_full_4d, [br, dim_size])
                m_state = alloc([br, unit_tile], NumericType.Float32, MemorySpace.TSM)
                sum_state = alloc([br, unit_tile], NumericType.Float32, MemorySpace.TSM)
                weighted = alloc([br, dim_size], NumericType.Float32, MemorySpace.TSM)
                fill(m_state, "-inf")
                fill(sum_state, 0)
                fill(weighted, 0)
                for n0 in loop(0, seq_len, bc):
                    cur_bc = min(bc, seq_len - n0)
                    k_full_4d = alloc([1, 1, bc, dim_size], NumericType.Float32, MemorySpace.TSM)
                    fill(k_full_4d, 0)
                    k_4d = view(k, [b0, h0, n0, 0], [1, 1, cur_bc, dim_size], [1, 1, 1, 1])
                    deslice(k_full_4d, k_4d, [0, 0, 0, 0], [1, 1, cur_bc, dim_size], [1, 1, 1, 1])
                    k_full = reshape(k_full_4d, [bc, dim_size])
                    k_transposed = transpose(k_full, [1, 0])
                    matmul_score = alloc([br, bc], NumericType.Float32, MemorySpace.TSM)
                    kernel.matmul(matmul_score, q_full, k_transposed)
                    score_tile = alloc([br, bc], NumericType.Float32, MemorySpace.TSM)
                    fill(score_tile, "-inf")
                    score_region = view(matmul_score, [0, 0], [cur_br, cur_bc], [1, 1])
                    deslice(score_tile, score_region, [0, 0], [cur_br, cur_bc], [1, 1])
                    tile_max = alloc([br, unit_tile], NumericType.Float32, MemorySpace.TSM)
                    kernel.reduce(tile_max, score_tile, kind=kernel.KernelReduceKind.MAX, axis=1, keepdim=True)
                    m_next = alloc([br, unit_tile], NumericType.Float32, MemorySpace.TSM)
                    kernel.binary_elewise(
                        m_next,
                        m_state,
                        tile_max,
                        kind=kernel.KernelBinaryElewiseKind.MAX,
                    )
                    m_next_full = alloc([br, bc], NumericType.Float32, MemorySpace.TSM)
                    broadcast(m_next_full, m_next)
                    shifted_score = alloc([br, bc], NumericType.Float32, MemorySpace.TSM)
                    kernel.sub(shifted_score, score_tile, m_next_full)
                    exp_score = alloc([br, bc], NumericType.Float32, MemorySpace.TSM)
                    kernel.exp(exp_score, shifted_score)
                    tile_sum = alloc([br, unit_tile], NumericType.Float32, MemorySpace.TSM)
                    kernel.reduce(tile_sum, exp_score, kind=kernel.KernelReduceKind.SUM, axis=1, keepdim=True)
                    old_shift = alloc([br, unit_tile], NumericType.Float32, MemorySpace.TSM)
                    kernel.sub(old_shift, m_state, m_next)
                    old_scale = alloc([br, unit_tile], NumericType.Float32, MemorySpace.TSM)
                    kernel.exp(old_scale, old_shift)
                    scaled_sum = alloc([br, unit_tile], NumericType.Float32, MemorySpace.TSM)
                    kernel.mul(scaled_sum, sum_state, old_scale)
                    sum_next = alloc([br, unit_tile], NumericType.Float32, MemorySpace.TSM)
                    kernel.add(sum_next, scaled_sum, tile_sum)
                    v_full_4d = alloc([1, 1, bc, dim_size], NumericType.Float32, MemorySpace.TSM)
                    fill(v_full_4d, 0)
                    v_4d = view(v, [b0, h0, n0, 0], [1, 1, cur_bc, dim_size], [1, 1, 1, 1])
                    deslice(v_full_4d, v_4d, [0, 0, 0, 0], [1, 1, cur_bc, dim_size], [1, 1, 1, 1])
                    v_full = reshape(v_full_4d, [bc, dim_size])
                    partial = alloc([br, dim_size], NumericType.Float32, MemorySpace.TSM)
                    kernel.matmul(partial, exp_score, v_full)
                    old_scale_full = alloc([br, dim_size], NumericType.Float32, MemorySpace.TSM)
                    broadcast(old_scale_full, old_scale)
                    scaled_weighted = alloc([br, dim_size], NumericType.Float32, MemorySpace.TSM)
                    kernel.mul(scaled_weighted, weighted, old_scale_full)
                    weighted_next = alloc([br, dim_size], NumericType.Float32, MemorySpace.TSM)
                    kernel.add(weighted_next, scaled_weighted, partial)
                    deslice(m_state, m_next, [0, 0], [br, unit_tile], [1, 1])
                    deslice(sum_state, sum_next, [0, 0], [br, unit_tile], [1, 1])
                    deslice(weighted, weighted_next, [0, 0], [br, dim_size], [1, 1])
                sum_full = alloc([br, dim_size], NumericType.Float32, MemorySpace.TSM)
                broadcast(sum_full, sum_state)
                output_tile = alloc([br, dim_size], NumericType.Float32, MemorySpace.TSM)
                kernel.truediv(output_tile, weighted, sum_full)
                output_region = view(output_tile, [0, 0], [cur_br, dim_size], [1, 1])
                o_4d = reshape(output_region, [1, 1, cur_br, dim_size])
                deslice(out, o_4d, [b0, h0, m0, 0], [1, 1, cur_br, dim_size], [1, 1, 1, 1])


def _symbolic_compile_args() -> tuple[FlashCompileArg, ...]:
    """构造 dynamic input / symbolic tile 的编译参数。


    功能说明:
    - output/Q/K/V 均使用 `B/H/SL/D` 语义符号 memory shape。
    - tile 参数固定使用 `BR/BC`，用于锁定编译期符号 tile。
    - 只服务本 demo 的符号编译入口，不新增跨文件公开 API。

    使用示例:
    - `_symbolic_compile_args()`
    """

    dynamic_memory = Memory(["B", "H", "SL", "D"], NumericType.Float32)
    return (
        dynamic_memory,
        dynamic_memory,
        dynamic_memory,
        dynamic_memory,
        SymbolDim("BR"),
        SymbolDim("BC"),
    )


def _assert_dynamic_symbolic_tile_ir(module_text: str) -> None:
    """校验 lowering 后 IR 保留 dynamic memory 与符号 tile。


    功能说明:
    - 确认 IR 包含 `B/H/SL/D` memory 与 `BR/BC` tile。
    - 确认 query/key loop step 分别是 `BR/BC`。
    - 确认 IR 不回退为本次真实运行 shape 或 runtime tile 常量。

    使用示例:
    - `_assert_dynamic_symbolic_tile_ir(str(module))`
    """

    required_fragments = (
        "!nn.memory<[#symbol.expr<B>, #symbol.expr<H>, #symbol.expr<SL>, #symbol.expr<D>]",
        "!symbol.int<#symbol.expr<BR>>",
        "!symbol.int<#symbol.expr<BC>>",
        "step = #symbol.expr<BR>",
        "step = #symbol.expr<BC>",
    )
    static_fragment = (
        f"!nn.memory<[#symbol.expr<{_DYNAMIC_BATCH}>, #symbol.expr<{_DYNAMIC_HEADS}>, "
        f"#symbol.expr<{_DYNAMIC_SEQ_LEN}>, #symbol.expr<{_DYNAMIC_DIM}>]"
    )
    forbidden_fragments = (
        static_fragment,
    )
    for fragment in required_fragments:
        if fragment not in module_text:
            raise AssertionError(f"{CASE_NAME}: dynamic symbolic tile IR missing fragment: {fragment}")
    for fragment in forbidden_fragments:
        if fragment in module_text:
            raise AssertionError(f"{CASE_NAME}: dynamic symbolic tile IR unexpectedly contains fragment: {fragment}")


def _assert_source_dump_matches(source: str) -> None:
    """校验生成源码与公开 dump/source.cpp 一致。


    功能说明:
    - 读取 `kernel/dump/flash_attention/inputs_dynamic_tile_dynamic/source.cpp`。
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


def _execute_device_source(source: str, real_args: tuple[FlashRuntimeArg, ...]) -> None:
    """编译并执行 lowering 生成的 root entry。


    功能说明:
    - 使用公开 `ExecutionEngine` 编译 `gen_kernel` 生成的完整源码。
    - 执行入口固定为 lowering 生成的 root wrapper，保留 `npu_demo::launch` block 分发语义。
    - `CompiledKernel` 使用完立即关闭，释放临时编译目录。

    使用示例:
    - `_execute_device_source(source, (out, q, k, v, 64, 80))`
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
    """运行动态输入、动态 tile 的 Flash Attention demo。


    功能说明:
    - 构造 per-run random profile 选出的真实 NumPy ndarray 输入，shape 绑定到 `B/H/SL/D`。
    - 编译期以 dynamic memory / symbolic tile 生成 IR/source 并写入公开 dump。
    - 用 NumPy softmax attention 参考结果校验输出。

    使用示例:
    - `python3 kernel/flash_attention/inputs_dynamic_tile_dynamic.py`
    """

    global _DYNAMIC_SHAPE_SEED, _DYNAMIC_BATCH, _DYNAMIC_HEADS, _DYNAMIC_SEQ_LEN, _DYNAMIC_DIM
    global _TILE_SELECTION_SEED, _RUNTIME_TILE_ARGS

    system_rng = random.SystemRandom()
    for _attempt in range(128):
        shape_seed = system_rng.randrange(1, 2**31)
        tile_seed = system_rng.randrange(1, 2**31)
        shape_rng = random.Random(shape_seed)
        batch = shape_rng.choice((1, 2))
        heads = shape_rng.choice((4, 8))
        seq_len = shape_rng.choice((257, 321, 389))
        dim = shape_rng.choice((48, 64, 80))
        tile_args = random.Random(tile_seed).choice(_TILE_CANDIDATES)
        has_multi_tile = seq_len > tile_args[0] and seq_len > tile_args[1]
        has_tail = seq_len % tile_args[0] != 0 or seq_len % tile_args[1] != 0
        if has_multi_tile and has_tail:
            break
    else:
        raise RuntimeError("flash attention dynamic/dynamic random profile failed to satisfy tile invariants")

    _DYNAMIC_SHAPE_SEED = shape_seed
    _DYNAMIC_BATCH = batch
    _DYNAMIC_HEADS = heads
    _DYNAMIC_SEQ_LEN = seq_len
    _DYNAMIC_DIM = dim
    _TILE_SELECTION_SEED = tile_seed
    _RUNTIME_TILE_ARGS = tile_args

    rng = np.random.default_rng(_DYNAMIC_SHAPE_SEED)
    q = rng.standard_normal((_DYNAMIC_BATCH, _DYNAMIC_HEADS, _DYNAMIC_SEQ_LEN, _DYNAMIC_DIM), dtype=np.float32)
    k = rng.standard_normal((_DYNAMIC_BATCH, _DYNAMIC_HEADS, _DYNAMIC_SEQ_LEN, _DYNAMIC_DIM), dtype=np.float32)
    v = rng.standard_normal((_DYNAMIC_BATCH, _DYNAMIC_HEADS, _DYNAMIC_SEQ_LEN, _DYNAMIC_DIM), dtype=np.float32)
    out = np.empty((_DYNAMIC_BATCH, _DYNAMIC_HEADS, _DYNAMIC_SEQ_LEN, _DYNAMIC_DIM), dtype=np.float32)
    expected = _flash_attention_reference(q, k, v)
    module, source = run_lowering_demo(CASE_NAME, flash_attention_inputs_dynamic_tile_dynamic_kernel, *_symbolic_compile_args())
    module_text = str(module)
    _assert_dynamic_symbolic_tile_ir(module_text)
    _assert_source_dump_matches(source)
    _execute_device_source(source, (out, q, k, v, *_RUNTIME_TILE_ARGS))
    max_abs_diff = _assert_outputs_close(out, expected, atol=1e-4, rtol=1e-4)
    print(
        "[ARGS] "
        "profile=per-run-random dynamic_ir=symbolic runtime=random "
        f"shape_seed={_DYNAMIC_SHAPE_SEED} shape={q.shape} "
        f"tile_seed={_TILE_SELECTION_SEED} tile_candidates={_TILE_CANDIDATES} tile={_RUNTIME_TILE_ARGS} "
        f"query_tiles={(_DYNAMIC_SEQ_LEN + _RUNTIME_TILE_ARGS[0] - 1) // _RUNTIME_TILE_ARGS[0]} "
        f"key_tiles={(_DYNAMIC_SEQ_LEN + _RUNTIME_TILE_ARGS[1] - 1) // _RUNTIME_TILE_ARGS[1]} "
        f"query_tail={_DYNAMIC_SEQ_LEN % _RUNTIME_TILE_ARGS[0]} key_tail={_DYNAMIC_SEQ_LEN % _RUNTIME_TILE_ARGS[1]} "
        f"multi_tile={_DYNAMIC_SEQ_LEN > _RUNTIME_TILE_ARGS[0] and _DYNAMIC_SEQ_LEN > _RUNTIME_TILE_ARGS[1]} "
        f"tail={_DYNAMIC_SEQ_LEN % _RUNTIME_TILE_ARGS[0] != 0 or _DYNAMIC_SEQ_LEN % _RUNTIME_TILE_ARGS[1] != 0} "
        "loops=batch/head/query/key online_softmax=True"
    )
    print("[IR] dynamic memory evidence: B/H/SL/D memory present; BR/BC tile symbols present")
    print(f"[CHECK] {CASE_NAME} max_abs_diff={max_abs_diff}")


if __name__ == "__main__":
    main()
