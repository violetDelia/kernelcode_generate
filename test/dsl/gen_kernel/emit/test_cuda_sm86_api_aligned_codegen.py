"""CUDA SM86 API-aligned generated source tests.

功能说明:
- 通过公开 DSL / pipeline / emit 入口验证 `cuda_sm86` SourceBundle 形态。
- 锁定 hash 专属 entry、slot C ABI、generated wrapper calls、dynamic symbol/control-flow 参数和三类 demo source 差异。

使用示例:
- pytest -q test/dsl/gen_kernel/emit/test_cuda_sm86_api_aligned_codegen.py

关联文件:
- 功能实现: kernel_gen/dsl/gen_kernel/emit/cuda_sm86/source_bundle.py
- Spec 文档: spec/dsl/gen_kernel/emit/cuda_sm86.md
- 测试文件: test/dsl/gen_kernel/emit/test_cuda_sm86_api_aligned_codegen.py
"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
import shutil
import sys

import pytest

REPO_ROOT = Path(__file__).resolve().parents[4]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from kernel.conv2d.inputs_dynamic_tile_dynamic import conv2d_inputs_dynamic_tile_dynamic_kernel
from kernel.conv2d.inputs_static_tile_static import conv2d_inputs_static_tile_static_kernel
from kernel.flash_attention.inputs_static_tile_static import flash_attention_inputs_static_tile_static_kernel
from kernel.matmul.inputs_dynamic_tile_dynamic import matmul_inputs_dynamic_tile_dynamic_kernel
from kernel.matmul.inputs_static_tile_static import matmul_inputs_static_tile_static_kernel
from kernel_gen.core.config import reset_config, set_target
from kernel_gen.dsl.ast.mlir_gen import mlir_gen
from kernel_gen.dsl.gen_kernel import EmitCContext, emit_c
from kernel_gen.execute_engine import ExecutionEngine
from kernel_gen.pipeline import build_cuda_sm86_lowering_pipeline
from kernel_gen.symbol_variable.memory import Memory
from kernel_gen.symbol_variable.symbol_dim import SymbolDim
from kernel_gen.symbol_variable.type import NumericType


def _emit_cuda_sm86_source(
    kernel_fn: Callable[..., None],
    annotations: dict[str, str],
    compile_args: tuple[object, ...],
) -> str:
    """通过公开入口生成 CUDA SM86 aggregate source。

    功能说明:
    - 临时设置 demo kernel annotations，生成公开 MLIR module。
    - 运行公开 `cuda-sm86-lowering` pipeline 后调用公开 `emit_c(...)`。
    - finally 恢复 annotations 和全局 target，避免污染其它用例。

    使用示例:
    - source = _emit_cuda_sm86_source(fn, annotations, args)
    """

    original_annotations = dict(kernel_fn.__annotations__)
    kernel_fn.__annotations__.update(annotations)
    try:
        reset_config()
        set_target("cuda_sm86")
        module = mlir_gen(kernel_fn, *compile_args)
        build_cuda_sm86_lowering_pipeline().run(module)
        source = emit_c(module, EmitCContext())
        if 'extern "C" int kg_execute_entry' not in source:
            raise AssertionError("missing CUDA SM86 C ABI entry")
        return source
    finally:
        kernel_fn.__annotations__.clear()
        kernel_fn.__annotations__.update(original_annotations)
        reset_config()


def _extract_cuda_sm86_ir_hash(source: str) -> str:
    """读取 generated source 中的 final IR hash marker。

    功能说明:
    - 只解析公开 `emit_c(...)` 返回的 aggregate source。
    - 找不到 marker 时显式失败，避免后续 entry symbol 断言假阳性。

    使用示例:
    - stable_hash = _extract_cuda_sm86_ir_hash(source)
    """

    marker_prefix = "// kg.cuda.ir.hash: "
    for line in source.splitlines():
        if line.startswith(marker_prefix):
            stable_hash = line.removeprefix(marker_prefix)
            if not stable_hash:
                raise AssertionError("empty CUDA SM86 IR hash")
            return stable_hash
    raise AssertionError("missing CUDA SM86 IR hash")


def test_cuda_sm86_api_aligned_source_uses_hash_entry_and_slot_abi() -> None:
    """验证 generated source 使用 hash entry 与 slot C ABI。

    功能说明:
    - 通过 matmul demo lowered final IR 生成 SourceBundle。
    - 锁定 `kg_execute_entry` 只转发到 hash 专属 entry，且 generated source 使用 CUDA SM86 slot ABI 与 per-op wrapper calls。

    使用示例:
    - pytest -q test/dsl/gen_kernel/emit/test_cuda_sm86_api_aligned_codegen.py -k hash_entry
    """

    source = _emit_cuda_sm86_source(
        matmul_inputs_static_tile_static_kernel,
        {
            "out": "Tensor[f32, 2, 4]",
            "lhs": "Tensor[f32, 2, 3]",
            "rhs": "Tensor[f32, 3, 4]",
            "bias": "Tensor[f32, 4]",
        },
        (
            Memory([2, 4], NumericType.Float32),
            Memory([2, 3], NumericType.Float32),
            Memory([3, 4], NumericType.Float32),
            Memory([4], NumericType.Float32),
        ),
    )
    stable_hash = _extract_cuda_sm86_ir_hash(source)

    assert source.startswith("// __KG_BUNDLE_FILE__:kernel.cu\n")
    assert "// __KG_BUNDLE_FILE__:include/cuda_sm86/generated_entry.cuh" in source
    assert f"// kg.cuda.ir.entry_symbol: kg_cuda_sm86_execute_{stable_hash}_ir" in source
    assert f"int kg_cuda_sm86_execute_{stable_hash}_ir(cuda_sm86::ArgSlot* slots, unsigned long long count)" in source
    assert f"// kg.cuda.ir.generated_kernel_symbol: kg_cuda_sm86_generated_kernel_{stable_hash}" in source
    assert f"// kg.cuda.ir.device_body_symbol: kg_cuda_sm86_device_body_{stable_hash}" in source
    assert f"return kg_cuda_sm86_execute_{stable_hash}_ir(slots, count);" in source
    assert 'extern "C" int kg_execute_entry(cuda_sm86::ArgSlot* slots, unsigned long long count)' in source
    assert "cuda_sm86::detail::memory_from_slot" in source
    assert "cuda_sm86::load<" in source
    assert "cuda_sm86::deslice<MemorySpace::GM" in source
    assert "cuda_sm86::matmul<" in source
    assert "mma.sync.aligned.m16n8k8" in source
    assert "(void)tensor_core_matmul_path(out, lhs, rhs, acc)" not in source
    assert "kg_cuda_sm86_mma_observable" not in source
    assert f"__device__ void kg_cuda_sm86_device_body_{stable_hash}" in source
    assert f"__global__ void kg_cuda_sm86_generated_kernel_{stable_hash}" in source
    assert f"cuda_sm86::launch<1, 256, 1, 49152, kg_cuda_sm86_generated_kernel_{stable_hash}>" in source
    assert "cuda_sm86::ArgSlot* kg_cuda_sm86_device_slots = nullptr" in source
    assert "cuda_sm86::detail::copy_host_to_device<cuda_sm86::ArgSlot>" in source
    assert "cuda_sm86::detail::copy_host_to_device<long long>" in source
    assert "cuda_sm86::detail::copy_host_to_device<float>" in source
    assert "cuda_sm86::detail::copy_device_to_host<float>" in source
    assert "host_ctx, kg_cuda_sm86_device_slots, count, kg_cuda_sm86_device_status" in source
    assert "host_ctx, slots, count, kg_cuda_sm86_device_status" not in source
    assert "kg_cuda_sm86_execute_" + "matmul_ir" not in source
    for forbidden in (
        '#include "include/npu_demo/npu_demo.h"',
        "include/npu_demo",
        "npu_demo::",
        "get_dynamic_memory<TLM",
        "cu" + "blas",
        "cu" + "BLAS",
        "cudaGet" + "DeviceProperties",
        "cudaDevice" + "GetAttribute",
    ):
        assert forbidden not in source


def test_cuda_sm86_demo_sources_are_final_ir_specific() -> None:
    """验证三类 demo 的 generated source 随 final IR 改变。

    功能说明:
    - 分别从 matmul、conv2d 和 flash_attention 公开 demo 入口生成 CUDA source。
    - 锁定 hash、op comments、wrapper call 和 device kernel 形态互不相同。

    使用示例:
    - pytest -q test/dsl/gen_kernel/emit/test_cuda_sm86_api_aligned_codegen.py -k final_ir_specific
    """

    matmul_source = _emit_cuda_sm86_source(
        matmul_inputs_static_tile_static_kernel,
        {
            "out": "Tensor[f32, 2, 4]",
            "lhs": "Tensor[f32, 2, 3]",
            "rhs": "Tensor[f32, 3, 4]",
            "bias": "Tensor[f32, 4]",
        },
        (
            Memory([2, 4], NumericType.Float32),
            Memory([2, 3], NumericType.Float32),
            Memory([3, 4], NumericType.Float32),
            Memory([4], NumericType.Float32),
        ),
    )
    conv2d_source = _emit_cuda_sm86_source(
        conv2d_inputs_static_tile_static_kernel,
        {
            "out": "Tensor[f32, 1, 3, 4, 5]",
            "input_tensor": "Tensor[f32, 1, 2, 4, 5]",
            "weight": "Tensor[f32, 3, 2, 2, 2]",
            "bias": "Tensor[f32, 3]",
        },
        (
            Memory([1, 3, 4, 5], NumericType.Float32),
            Memory([1, 2, 4, 5], NumericType.Float32),
            Memory([3, 2, 2, 2], NumericType.Float32),
            Memory([3], NumericType.Float32),
        ),
    )
    flash_source = _emit_cuda_sm86_source(
        flash_attention_inputs_static_tile_static_kernel,
        {
            "out": "Tensor[f32, 1, 2, 4, 3]",
            "q": "Tensor[f32, 1, 2, 4, 3]",
            "k": "Tensor[f32, 1, 2, 4, 3]",
            "v": "Tensor[f32, 1, 2, 4, 3]",
        },
        (
            Memory([1, 2, 4, 3], NumericType.Float32),
            Memory([1, 2, 4, 3], NumericType.Float32),
            Memory([1, 2, 4, 3], NumericType.Float32),
            Memory([1, 2, 4, 3], NumericType.Float32),
        ),
    )

    matmul_hash = _extract_cuda_sm86_ir_hash(matmul_source)
    conv2d_hash = _extract_cuda_sm86_ir_hash(conv2d_source)
    flash_hash = _extract_cuda_sm86_ir_hash(flash_source)
    assert matmul_hash != conv2d_hash
    assert matmul_hash != flash_hash
    assert "// kg.cuda.ir.op: kernel.matmul" in matmul_source
    assert "cuda_sm86::matmul<" in matmul_source
    assert f"__global__ void kg_cuda_sm86_generated_kernel_{matmul_hash}" in matmul_source
    assert "// kg.cuda.ir.op: kernel.img2col2d" in conv2d_source
    assert "cuda_sm86::img2col2d<" in conv2d_source
    assert f"__global__ void kg_cuda_sm86_generated_kernel_{conv2d_hash}" in conv2d_source
    assert "// kg.cuda.ir.op: kernel.reduce" in flash_source
    assert "// kg.cuda.ir.op: kernel.exp" in flash_source
    assert "cuda_sm86::reduce_" in flash_source
    assert "cuda_sm86::exp<" in flash_source
    assert f"__global__ void kg_cuda_sm86_generated_kernel_{flash_hash}" in flash_source
    assert "kg_cuda_sm86_execute_" + "matmul_ir" not in matmul_source
    assert "kg_cuda_sm86_execute_" + "img2col2d_ir" not in conv2d_source
    assert "kg_cuda_sm86_execute_" + "reduce_exp_ir" not in flash_source
    assert matmul_source != conv2d_source
    assert matmul_source != flash_source
    assert conv2d_source != flash_source


def test_cuda_sm86_dynamic_matmul_source_uses_symbol_operands_and_control_flow() -> None:
    """验证 dynamic matmul 的 symbol/control-flow 进入 generated body。

    功能说明:
    - 从公开 dynamic matmul demo 生成 CUDA SM86 source。
    - 锁定 runtime symbol slot、`symbol.for` 循环、descriptor/window 参数和 deslice write-back 都来自 SSA operand。

    使用示例:
    - pytest -q test/dsl/gen_kernel/emit/test_cuda_sm86_api_aligned_codegen.py -k dynamic_matmul_source
    """

    source = _emit_cuda_sm86_source(
        matmul_inputs_dynamic_tile_dynamic_kernel,
        {
            "out": "Tensor[f32, H, W]",
            "lhs": "Tensor[f32, H, K]",
            "rhs": "Tensor[f32, K, W]",
            "bias": "Tensor[f32, W]",
            "tile_h": "SymbolDim",
            "tile_w": "SymbolDim",
            "tile_k": "SymbolDim",
        },
        (
            Memory(["H", "W"], NumericType.Float32),
            Memory(["H", "K"], NumericType.Float32),
            Memory(["K", "W"], NumericType.Float32),
            Memory(["W"], NumericType.Float32),
            6,
            7,
            5,
        ),
    )

    assert "cuda_sm86::detail::int_arg_or(slots, count, 4, 6)" in source
    assert "cuda_sm86::detail::int_arg_or(slots, count, 5, 7)" in source
    assert "cuda_sm86::detail::int_arg_or(slots, count, 6, 5)" in source
    assert "for (S_INT kg_arg_" in source
    assert "cuda_sm86::detail::fragment_alias<MemorySpace::GM, float>" in source
    assert "Vector{kg_arg_" in source
    assert "Vector{kg_v_" in source
    assert "cuda_sm86::deslice<MemorySpace::GM, MemorySpace::TSM" in source
    assert "// kg.cuda.ir.exec[" in source
    assert "symbol.for operands=" in source
    for line in source.splitlines():
        stripped = line.strip()
        assert not (stripped.startswith("S_INT kg_arg_") and stripped.endswith("= 0;"))


def test_cuda_sm86_dynamic_conv2d_source_uses_symbol_operands_and_img2col() -> None:
    """验证 dynamic conv2d 的 symbol/control-flow 驱动 img2col 与搬运参数。

    功能说明:
    - 从公开 dynamic conv2d demo 生成 CUDA SM86 source。
    - 锁定 dynamic tile/runtime padding/stride/dilation operand 进入 `img2col2d`，view/slice/deslice 使用 SSA vector。

    使用示例:
    - pytest -q test/dsl/gen_kernel/emit/test_cuda_sm86_api_aligned_codegen.py -k dynamic_conv2d_source
    """

    source = _emit_cuda_sm86_source(
        conv2d_inputs_dynamic_tile_dynamic_kernel,
        {
            "out": "Tensor[f32, B, C, HO, WO]",
            "input_tensor": "Tensor[f32, B, N, XH, XW]",
            "weight": "Tensor[f32, C, N, KH, KW]",
            "bias": "Tensor[f32, C]",
            "stride_h": "SymbolDim",
            "stride_w": "SymbolDim",
            "dilation_h": "SymbolDim",
            "dilation_w": "SymbolDim",
            "pad_top": "SymbolDim",
            "pad_bottom": "SymbolDim",
            "pad_left": "SymbolDim",
            "pad_right": "SymbolDim",
            "tile_f": "SymbolDim",
            "tile_c": "SymbolDim",
            "tile_n": "SymbolDim",
            "tile_ho": "SymbolDim",
            "tile_wo": "SymbolDim",
        },
        (
            Memory(["B", "C", "HO", "WO"], NumericType.Float32),
            Memory(["B", "N", "XH", "XW"], NumericType.Float32),
            Memory(["C", "N", "KH", "KW"], NumericType.Float32),
            Memory(["C"], NumericType.Float32),
            1,
            1,
            1,
            1,
            0,
            0,
            0,
            0,
            2,
            2,
            1,
            1,
            7,
        ),
    )

    assert "cuda_sm86::detail::int_arg_or(slots, count, 4, 1)" in source
    assert "cuda_sm86::detail::int_arg_or(slots, count, 16, 7)" in source
    assert "for (S_INT kg_arg_" in source
    assert "cuda_sm86::img2col2d<MemorySpace::TSM, MemorySpace::TSM, float, float>" in source
    assert "if (cuda_sm86::img2col2d<MemorySpace::TSM, MemorySpace::TSM, float, float>" in source
    assert "(void)cuda_sm86::img2col2d" not in source
    assert "cuda_sm86::slice<MemorySpace::TSM, MemorySpace::GM" in source
    assert "cuda_sm86::deslice<MemorySpace::GM, MemorySpace::TSM" in source
    assert "delete[] kg_v_" in source
    assert "kg_cuda_sm86_host_status" in source
    assert "Vector{kg_arg_" in source
    assert "Vector{kg_v_" in source
    assert "arch.get_dynamic_memory" not in source
    for line in source.splitlines():
        stripped = line.strip()
        assert not (stripped.startswith("S_INT kg_arg_") and stripped.endswith("= 0;"))


def test_cuda_sm86_dynamic_conv2d_symbol_source_compiles_with_nvcc() -> None:
    """验证 dynamic conv2d SymbolDim SourceBundle 可通过 nvcc compile-only。

    功能说明:
    - 使用公开 dynamic conv2d demo 与 `SymbolDim` 编译实参生成 CUDA SM86 SourceBundle。
    - 通过公开 `ExecutionEngine(target="cuda_sm86").compile(...)` 实际触发 nvcc compile-only gate。

    使用示例:
    - pytest -q test/dsl/gen_kernel/emit/test_cuda_sm86_api_aligned_codegen.py -k dynamic_conv2d_symbol_source_compiles
    """

    if shutil.which("nvcc") is None:
        pytest.skip("nvcc is not available in PATH")

    source = _emit_cuda_sm86_source(
        conv2d_inputs_dynamic_tile_dynamic_kernel,
        {
            "out": "Tensor[f32, B, F, HO, WO]",
            "input_tensor": "Tensor[f32, B, C, H, W]",
            "weight": "Tensor[f32, F, C, KH, KW]",
            "bias": "Tensor[f32, F]",
            "stride_h": "SymbolDim",
            "stride_w": "SymbolDim",
            "dilation_h": "SymbolDim",
            "dilation_w": "SymbolDim",
            "pad_top": "SymbolDim",
            "pad_bottom": "SymbolDim",
            "pad_left": "SymbolDim",
            "pad_right": "SymbolDim",
            "tile_f": "SymbolDim",
            "tile_c": "SymbolDim",
            "tile_n": "SymbolDim",
            "tile_ho": "SymbolDim",
            "tile_wo": "SymbolDim",
        },
        (
            Memory(["B", "F", "HO", "WO"], NumericType.Float32),
            Memory(["B", "C", "H", "W"], NumericType.Float32),
            Memory(["F", "C", "KH", "KW"], NumericType.Float32),
            Memory(["F"], NumericType.Float32),
            SymbolDim("SH"),
            SymbolDim("SW"),
            SymbolDim("DH"),
            SymbolDim("DW"),
            SymbolDim("PT"),
            SymbolDim("PB"),
            SymbolDim("PL"),
            SymbolDim("PR"),
            SymbolDim("TF"),
            SymbolDim("TC"),
            SymbolDim("TN"),
            SymbolDim("THO"),
            SymbolDim("TWO"),
        ),
    )

    assert "cuda_sm86::img2col2d<MemorySpace::TSM, MemorySpace::TSM, float, float>" in source
    assert "cuda_sm86::matmul<MemorySpace::TLM1, MemorySpace::TLM1, MemorySpace::TLM1, float, float, float>" in source
    assert source.count("cuda_sm86::detail::memory_from_slot<MemorySpace::GM, float>(slots, count, 0)") == 1
    compiled = ExecutionEngine(target="cuda_sm86").compile(source=source, function=conv2d_inputs_dynamic_tile_dynamic_kernel.__name__)
    try:
        assert compiled.function == conv2d_inputs_dynamic_tile_dynamic_kernel.__name__
    finally:
        compiled.close()
