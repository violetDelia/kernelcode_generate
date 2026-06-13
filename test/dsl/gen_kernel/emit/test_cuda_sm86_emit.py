"""CUDA SM86 emit backend tests.


功能说明:
- 通过公开 `gen_kernel(...)` / `emit_c(...)` 入口验证 CUDA SM86 backend 自动加载与 SourceBundle 输出。
- 覆盖 generated CUDA source 的 final IR comments、stable hash、entry ABI 和 npu_demo 残留扫描。

使用示例:
- pytest -q test/dsl/gen_kernel/emit/test_cuda_sm86_emit.py

关联文件:
- 功能实现: kernel_gen/dsl/gen_kernel/emit/cuda_sm86/__init__.py
- Spec 文档: spec/dsl/gen_kernel/emit/cuda_sm86.md
- 测试文件: test/dsl/gen_kernel/emit/test_cuda_sm86_emit.py
"""

from __future__ import annotations

import ast
from collections.abc import Callable
from pathlib import Path
import shutil
import sys

import pytest
from xdsl.dialects import func
from xdsl.dialects.builtin import ArrayAttr, ModuleOp, StringAttr, f32, i8
from xdsl.ir import Block, Region

REPO_ROOT = Path(__file__).resolve().parents[4]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from kernel.conv2d.inputs_static_tile_static import conv2d_inputs_static_tile_static_kernel
from kernel.flash_attention.inputs_static_tile_static import flash_attention_inputs_static_tile_static_kernel
from kernel.matmul.inputs_static_tile_static import matmul_inputs_static_tile_static_kernel
from kernel_gen.core.config import reset_config, set_dump_dir, set_target
from kernel_gen.core.error import KernelCodeError
from kernel_gen.dialect.dma import DmaAdvanceRingOp, DmaAllocOp, DmaCopyOp, DmaCurrentRingOp, DmaFreeOp, DmaMakeRingOp, DmaRingType
from kernel_gen.dialect.kernel import KernelMatmulOp
from kernel_gen.dialect.nn import NnMemorySpaceAttr, NnMemoryType
from kernel_gen.dialect.symbol import SymbolConstOp, SymbolExprAttr
from kernel_gen.dsl.ast.mlir_gen import mlir_gen
from kernel_gen.dsl.gen_kernel import EmitCContext, emit_c, gen_kernel
from kernel_gen.execute_engine import ExecutionEngine
from kernel_gen.pipeline import build_cuda_sm86_lowering_pipeline
from kernel_gen.symbol_variable.memory import Memory
from kernel_gen.symbol_variable.type import NumericType


@pytest.fixture(autouse=True)
def _reset_core_config_fixture() -> None:
    reset_config()
    set_target("cpu")
    try:
        yield
    finally:
        reset_config()
        set_dump_dir(None)


def _make_module(name: str = "cuda_matmul") -> ModuleOp:
    """构造最小公开 ModuleOp。

    功能说明:
    - 返回包含一个空 `func.func` 的 module。
    - 用于触发 CUDA SM86 target-specific ModuleOp handler。

    使用示例:
    - module = _make_module("cuda_matmul")
    """

    block = Block(arg_types=[])
    block.add_op(func.ReturnOp())
    func_op = func.FuncOp(name, ([], []), Region(block))
    module = ModuleOp([func_op])
    return module


def _make_spoofed_string_token_module(name: str = "spoofed_tokens") -> ModuleOp:
    """构造仅靠属性文本伪造 kernel op token 的 module。

    功能说明:
    - 函数类型伪造成 matmul rank pattern，但函数体没有任何 lowered kernel op。
    - 属性文本包含 `kernel.matmul` / `arch.launch`，用于证明 CUDA backend 不读取 printed IR 字符串做 source 判定。

    使用示例:
    - module = _make_spoofed_string_token_module()
    """

    mem2d = NnMemoryType(
        ArrayAttr([SymbolExprAttr.from_expr("2"), SymbolExprAttr.from_expr("4")]),
        ArrayAttr([SymbolExprAttr.from_expr("4"), SymbolExprAttr.from_expr("1")]),
        f32,
        NnMemorySpaceAttr.from_name("global"),
    )
    mem1d = NnMemoryType(
        ArrayAttr([SymbolExprAttr.from_expr("4")]),
        ArrayAttr([SymbolExprAttr.from_expr("1")]),
        f32,
        NnMemorySpaceAttr.from_name("global"),
    )
    input_types = [mem2d, mem2d, mem2d, mem1d]
    block = Block(arg_types=input_types)
    block.add_op(func.ReturnOp())
    func_op = func.FuncOp(name, (input_types, []), Region(block))
    func_op.attributes["fake_lowered_ops"] = StringAttr("kernel.matmul arch.launch")
    return ModuleOp([func_op])


def _make_minimal_c5_matmul_module(
    *,
    lhs_space: str = "tlm1",
    include_writeback: bool = True,
    matmul_attr_probe: str | None = None,
    extra_lhs_copy: bool = False,
    square_operand_types: bool = False,
    swap_lhs_rhs_sources: bool = False,
) -> ModuleOp:
    """构造最小 C5 `kernel.matmul` final IR module。

    功能说明:
    - 使用公开 dialect op 构造 `dma.alloc/copy/free + kernel.matmul` final IR 片段。
    - 可控制 lhs space、out write-back、op sequence 与同类型 lhs/rhs source dataflow，用于验证 C5 marker 与 executable source。

    使用示例:
    - module = _make_minimal_c5_matmul_module(lhs_space="tlm2")
    """

    if swap_lhs_rhs_sources and not square_operand_types:
        raise ValueError("swap_lhs_rhs_sources requires equal lhs/rhs public types")
    out_shape = ArrayAttr([SymbolExprAttr.from_expr("2"), SymbolExprAttr.from_expr("4")])
    out_stride = ArrayAttr([SymbolExprAttr.from_expr("4"), SymbolExprAttr.from_expr("1")])
    lhs_shape = ArrayAttr([SymbolExprAttr.from_expr("2"), SymbolExprAttr.from_expr("3")])
    lhs_stride = ArrayAttr([SymbolExprAttr.from_expr("3"), SymbolExprAttr.from_expr("1")])
    rhs_shape = ArrayAttr([SymbolExprAttr.from_expr("3"), SymbolExprAttr.from_expr("4")])
    rhs_stride = ArrayAttr([SymbolExprAttr.from_expr("4"), SymbolExprAttr.from_expr("1")])
    if square_operand_types:
        out_shape = ArrayAttr([SymbolExprAttr.from_expr("4"), SymbolExprAttr.from_expr("4")])
        out_stride = ArrayAttr([SymbolExprAttr.from_expr("4"), SymbolExprAttr.from_expr("1")])
        lhs_shape = out_shape
        lhs_stride = out_stride
        rhs_shape = out_shape
        rhs_stride = out_stride
    out_type = NnMemoryType(out_shape, out_stride, f32, NnMemorySpaceAttr.from_name("global"))
    lhs_type = NnMemoryType(lhs_shape, lhs_stride, f32, NnMemorySpaceAttr.from_name("global"))
    rhs_type = NnMemoryType(rhs_shape, rhs_stride, f32, NnMemorySpaceAttr.from_name("global"))
    block = Block(arg_types=[out_type, lhs_type, rhs_type])
    staged_out_type = NnMemoryType(out_shape, out_stride, f32, NnMemorySpaceAttr.from_name("tlm1"))
    staged_lhs_type = NnMemoryType(lhs_shape, lhs_stride, f32, NnMemorySpaceAttr.from_name(lhs_space))
    staged_rhs_type = NnMemoryType(rhs_shape, rhs_stride, f32, NnMemorySpaceAttr.from_name("tlm1"))
    staged_out = DmaAllocOp([], staged_out_type)
    staged_lhs = DmaAllocOp([], staged_lhs_type)
    staged_rhs = DmaAllocOp([], staged_rhs_type)
    copy_out_in = DmaCopyOp(staged_out.result, block.args[0])
    lhs_source = block.args[2] if swap_lhs_rhs_sources else block.args[1]
    rhs_source = block.args[1] if swap_lhs_rhs_sources else block.args[2]
    copy_lhs_in = DmaCopyOp(staged_lhs.result, lhs_source)
    copy_rhs_in = DmaCopyOp(staged_rhs.result, rhs_source)
    matmul = KernelMatmulOp(staged_out.result, staged_lhs.result, staged_rhs.result, NnMemorySpaceAttr.from_name("tlm1"))
    if matmul_attr_probe is not None:
        matmul.attributes["review_probe"] = StringAttr(matmul_attr_probe)
    pre_matmul_ops = [staged_out, staged_lhs, staged_rhs, copy_out_in, copy_lhs_in, copy_rhs_in]
    if extra_lhs_copy:
        pre_matmul_ops.append(DmaCopyOp(staged_lhs.result, block.args[1]))
    block.add_ops([*pre_matmul_ops, matmul])
    if include_writeback:
        block.add_op(DmaCopyOp(block.args[0], staged_out.result))
    block.add_ops([DmaFreeOp(staged_out.result), DmaFreeOp(staged_lhs.result), DmaFreeOp(staged_rhs.result), func.ReturnOp()])
    func_op = func.FuncOp("minimal_c5_matmul", ([out_type, lhs_type, rhs_type], []), Region(block))
    return ModuleOp([func_op])


def _make_minimal_dma_ring_matmul_module() -> ModuleOp:
    """构造含 `dma.make_ring/current/advance` 的最小 CUDA final IR。

    功能说明:
    - 使用一维 i8 `dma.alloc` byte-pool backing 构造 tlm1 f32 ring slot。
    - 将 current slot 作为 matmul lhs，保留 advance side effect，并写回 global out。

    使用示例:
    - module = _make_minimal_dma_ring_matmul_module()
    """

    out_shape = ArrayAttr([SymbolExprAttr.from_expr("2"), SymbolExprAttr.from_expr("4")])
    out_stride = ArrayAttr([SymbolExprAttr.from_expr("4"), SymbolExprAttr.from_expr("1")])
    lhs_shape = ArrayAttr([SymbolExprAttr.from_expr("2"), SymbolExprAttr.from_expr("3")])
    lhs_stride = ArrayAttr([SymbolExprAttr.from_expr("3"), SymbolExprAttr.from_expr("1")])
    rhs_shape = ArrayAttr([SymbolExprAttr.from_expr("3"), SymbolExprAttr.from_expr("4")])
    rhs_stride = ArrayAttr([SymbolExprAttr.from_expr("4"), SymbolExprAttr.from_expr("1")])
    out_type = NnMemoryType(out_shape, out_stride, f32, NnMemorySpaceAttr.from_name("global"))
    lhs_type = NnMemoryType(lhs_shape, lhs_stride, f32, NnMemorySpaceAttr.from_name("global"))
    rhs_type = NnMemoryType(rhs_shape, rhs_stride, f32, NnMemorySpaceAttr.from_name("global"))
    block = Block(arg_types=[out_type, lhs_type, rhs_type])
    staged_out_type = NnMemoryType(out_shape, out_stride, f32, NnMemorySpaceAttr.from_name("tlm1"))
    ring_slot_type = NnMemoryType(lhs_shape, lhs_stride, f32, NnMemorySpaceAttr.from_name("tlm1"))
    staged_rhs_type = NnMemoryType(rhs_shape, rhs_stride, f32, NnMemorySpaceAttr.from_name("tlm1"))
    backing_type = NnMemoryType(
        ArrayAttr([SymbolExprAttr.from_expr("64")]),
        ArrayAttr([SymbolExprAttr.from_expr("1")]),
        i8,
        NnMemorySpaceAttr.from_name("tlm1"),
    )
    staged_out = DmaAllocOp([], staged_out_type)
    staged_rhs = DmaAllocOp([], staged_rhs_type)
    backing = DmaAllocOp([], backing_type)
    ring_count = SymbolConstOp(2)
    ring_offset = SymbolConstOp(32)
    ring = DmaMakeRingOp(backing.result, ring_count.result, ring_offset.result, DmaRingType(ring_slot_type))
    current_lhs = DmaCurrentRingOp(ring.result)
    advance_lhs = DmaAdvanceRingOp(ring.result)
    block.add_ops(
        [
            staged_out,
            staged_rhs,
            backing,
            ring_count,
            ring_offset,
            ring,
            current_lhs,
            DmaCopyOp(staged_out.result, block.args[0]),
            DmaCopyOp(current_lhs.result, block.args[1]),
            DmaCopyOp(staged_rhs.result, block.args[2]),
            KernelMatmulOp(staged_out.result, current_lhs.result, staged_rhs.result, NnMemorySpaceAttr.from_name("tlm1")),
            advance_lhs,
            DmaCopyOp(block.args[0], staged_out.result),
            DmaFreeOp(staged_out.result),
            DmaFreeOp(staged_rhs.result),
            DmaFreeOp(backing.result),
            func.ReturnOp(),
        ]
    )
    func_op = func.FuncOp("minimal_dma_ring_matmul", ([out_type, lhs_type, rhs_type], []), Region(block))
    return ModuleOp([func_op])


MATMUL_ANNOTATIONS = {
    "out": "Tensor[f32, 2, 4]",
    "lhs": "Tensor[f32, 2, 3]",
    "rhs": "Tensor[f32, 3, 4]",
    "bias": "Tensor[f32, 4]",
}
MATMUL_ARGS = (
    Memory([2, 4], NumericType.Float32),
    Memory([2, 3], NumericType.Float32),
    Memory([3, 4], NumericType.Float32),
    Memory([4], NumericType.Float32),
)

CONV2D_ANNOTATIONS = {
    "out": "Tensor[f32, 1, 3, 4, 5]",
    "input_tensor": "Tensor[f32, 1, 2, 4, 5]",
    "weight": "Tensor[f32, 3, 2, 2, 2]",
    "bias": "Tensor[f32, 3]",
}
CONV2D_ARGS = (
    Memory([1, 3, 4, 5], NumericType.Float32),
    Memory([1, 2, 4, 5], NumericType.Float32),
    Memory([3, 2, 2, 2], NumericType.Float32),
    Memory([3], NumericType.Float32),
)

FLASH_ATTENTION_ANNOTATIONS = {
    "out": "Tensor[f32, 1, 2, 4, 3]",
    "q": "Tensor[f32, 1, 2, 4, 3]",
    "k": "Tensor[f32, 1, 2, 4, 3]",
    "v": "Tensor[f32, 1, 2, 4, 3]",
}
FLASH_ATTENTION_ARGS = (
    Memory([1, 2, 4, 3], NumericType.Float32),
    Memory([1, 2, 4, 3], NumericType.Float32),
    Memory([1, 2, 4, 3], NumericType.Float32),
    Memory([1, 2, 4, 3], NumericType.Float32),
)


def _make_lowered_demo_module(
    kernel_fn: Callable[..., None],
    annotations: dict[str, str],
    compile_args: tuple[Memory, ...],
) -> ModuleOp:
    """通过公开 demo 入口构造 CUDA lowered ModuleOp。

    功能说明:
    - 临时设置公开 kernel 函数 annotations 后调用 `mlir_gen(...)`。
    - 运行公开 `build_cuda_sm86_lowering_pipeline()`，让 emit 测试基于真实 final IR traversal 判定 source。

    使用示例:
    - module = _make_lowered_demo_module(matmul_inputs_static_tile_static_kernel, MATMUL_ANNOTATIONS, MATMUL_ARGS)
    """

    original_annotations = dict(kernel_fn.__annotations__)
    kernel_fn.__annotations__.update(annotations)
    try:
        reset_config()
        set_target("cuda_sm86")
        module = mlir_gen(kernel_fn, *compile_args)
        build_cuda_sm86_lowering_pipeline().run(module)
        return module
    finally:
        kernel_fn.__annotations__.clear()
        kernel_fn.__annotations__.update(original_annotations)
        reset_config()


OLD_CUDA_SM86_SOURCE_TOKENS = (
    "kg_cuda_sm86_" + "selected_kernel_kind",
    "kg_cuda_sm86_" + "run_" + "matmul",
    "kg_cuda_sm86_" + "run_" + "conv2d",
    "kg_cuda_sm86_" + "run_" + "flash_attention",
    "emit_" + "matmul_source",
    "emit_" + "conv2d_source",
    "emit_" + "flash_attention_source",
)


def _extract_cuda_sm86_ir_hash(source: str) -> str:
    """读取 generated source 中的 final IR hash。

    功能说明:
    - 只解析公开 `emit_c(...)` 返回的 SourceBundle aggregate string。
    - 找不到 hash marker 时让测试显式失败。

    使用示例:
    - stable_hash = _extract_cuda_sm86_ir_hash(source)
    """

    marker_prefix = "// kg.cuda.ir.hash: "
    for line in source.splitlines():
        if not line.startswith(marker_prefix):
            continue
        stable_hash = line.removeprefix(marker_prefix)
        return stable_hash
    raise AssertionError("missing kg.cuda.ir.hash marker")


def _extract_cuda_sm86_device_body(source: str) -> str:
    """读取 generated CUDA device body 的非注释可执行内容。

    功能说明:
    - 只解析公开 `emit_c(...)` 返回的 SourceBundle aggregate string。
    - 剥离空行与纯注释行后返回 hash 专属 device body，固定模板假绿时会找不到真实 wrapper calls。

    使用示例:
    - body = _extract_cuda_sm86_device_body(source)
    """

    lines = source.splitlines()
    start_index = -1
    for index, line in enumerate(lines):
        if line.startswith("__device__ void kg_cuda_sm86_device_body_"):
            start_index = index
            break
    if start_index < 0:
        raise AssertionError("missing generated CUDA SM86 device body")
    depth = 0
    in_body = False
    executable_lines: list[str] = []
    for line in lines[start_index:]:
        if not in_body:
            if "{" not in line:
                continue
            in_body = True
            depth = line.count("{") - line.count("}")
            continue
        depth += line.count("{")
        depth -= line.count("}")
        if depth < 0:
            break
        stripped = line.strip()
        if stripped and not stripped.startswith("//"):
            executable_lines.append(stripped)
        if depth == 0:
            break
    return "\n".join(executable_lines)


def test_cuda_sm86_emit_module_returns_source_bundle() -> None:
    """验证 CUDA backend 返回 SourceBundle aggregate string。

    功能说明:
    - 通过公开 `emit_c(...)` 触发 backend auto-load。
    - 锁定 `.cu/.cuh` artifact marker、CUDA include、final IR comments/hash、C5 all-TLM1 和 C ABI entry。

    使用示例:
    - pytest -q test/dsl/gen_kernel/emit/test_cuda_sm86_emit.py -k source_bundle
    """

    module = _make_lowered_demo_module(matmul_inputs_static_tile_static_kernel, MATMUL_ANNOTATIONS, MATMUL_ARGS)
    set_target("cuda_sm86")
    source = emit_c(module, EmitCContext())

    assert source.startswith("// __KG_BUNDLE_FILE__:kernel.cu\n")
    assert '// __KG_BUNDLE_FILE__:include/cuda_sm86/generated_entry.cuh' in source
    assert '#include "include/cuda_sm86/cuda_sm86.cuh"' in source
    assert "// cuda_sm86 generated from final IR" in source
    assert "// kg.cuda.ir.hash: " in source
    stable_hash = _extract_cuda_sm86_ir_hash(source)
    assert f"// kg.cuda.ir.entry_symbol: kg_cuda_sm86_execute_{stable_hash}_ir" in source
    assert f"// kg.cuda.ir.generated_kernel_symbol: kg_cuda_sm86_generated_kernel_{stable_hash}" in source
    assert f"// kg.cuda.ir.device_body_symbol: kg_cuda_sm86_device_body_{stable_hash}" in source
    assert "// kg.cuda.ir.memory_spaces: global,tlm1,tsm" in source
    assert "// kg.cuda.ir.op: tuner.select" in source
    assert "// kg.cuda.ir.op: arch.launch" in source
    assert "// kg.cuda.ir.op: dma.reinterpret" in source
    assert "// kg.cuda.ir.op: dma.copy" in source
    assert "// kg.cuda.ir.op: kernel.matmul" in source
    assert "// kg.cuda.ir.matmul.materialization: out=tlm1,lhs=tlm1,rhs=tlm1,write_back=visible" in source
    assert f"__device__ void kg_cuda_sm86_device_body_{stable_hash}" in source
    assert f"__global__ void kg_cuda_sm86_generated_kernel_{stable_hash}" in source
    assert f"cuda_sm86::launch<1, 256, 1, 49152, kg_cuda_sm86_generated_kernel_{stable_hash}>" in source
    assert "if (threadIdx.x == 0)" in source
    assert "cuda_sm86::ArgSlot* kg_cuda_sm86_device_slots = nullptr" in source
    assert "cuda_sm86::ArgSlot* kg_cuda_sm86_host_device_slots = nullptr" in source
    assert "long long** kg_cuda_sm86_device_shapes = nullptr" in source
    assert "long long** kg_cuda_sm86_device_strides = nullptr" in source
    assert "void** kg_cuda_sm86_device_data = nullptr" in source
    assert "cuda_sm86::detail::copy_host_to_device<long long>" in source
    assert "cuda_sm86::detail::copy_host_to_device<float>" in source
    assert "cuda_sm86::detail::copy_host_to_device<cuda_sm86::ArgSlot>" in source
    assert "cuda_sm86::detail::copy_device_to_host<float>" in source
    assert "kg_cuda_sm86_host_device_slots[kg_cuda_sm86_slot_index].shape = kg_cuda_sm86_device_shapes" in source
    assert "kg_cuda_sm86_host_device_slots[kg_cuda_sm86_slot_index].data = kg_cuda_sm86_device_data" in source
    assert "host_ctx, kg_cuda_sm86_device_slots, count, kg_cuda_sm86_device_status" in source
    assert "host_ctx, slots, count, kg_cuda_sm86_device_status" not in source
    assert "int* kg_cuda_sm86_device_status = nullptr" in source
    assert "cudaMemcpy(&kg_cuda_sm86_host_status, kg_cuda_sm86_device_status, sizeof(int), cudaMemcpyDeviceToHost)" in source
    assert "mma.sync.aligned.m16n8k8" in source
    assert "tensor_core_probe" not in source
    assert "acc += lhs" not in source
    assert "cuda_sm86::detail::memory_from_slot" in source
    assert "cuda_sm86::load<" in source
    assert "cuda_sm86::deslice<MemorySpace::GM" in source
    assert "cuda_sm86::matmul<" in source
    assert "(void)cuda_sm86::" not in source
    assert "delete[] kg_v_" in source
    assert 'extern "C" int kg_execute_entry(cuda_sm86::ArgSlot* slots, unsigned long long count)' in source
    assert f"int kg_cuda_sm86_execute_{stable_hash}_ir(cuda_sm86::ArgSlot* slots, unsigned long long count)" in source
    assert f"return kg_cuda_sm86_execute_{stable_hash}_ir(slots, count);" in source
    fixed_matmul_entry = "kg_cuda_sm86_execute_" + "matmul_ir"
    assert f"return {fixed_matmul_entry}(slots, count);" not in source
    assert f"int {fixed_matmul_entry}(" not in source
    assert "kg_cuda_sm86_ir_record_words" in _extract_cuda_sm86_device_body(source)
    for token in OLD_CUDA_SM86_SOURCE_TOKENS:
        assert token not in source
    include_text = Path("include/cuda_sm86/cuda_sm86.cuh").read_text(encoding="utf-8")
    arch_text = Path("include/cuda_sm86/Arch.h").read_text(encoding="utf-8")
    source_builder_text = Path("kernel_gen/dsl/gen_kernel/emit/cuda_sm86/source_bundle.py").read_text(encoding="utf-8")
    arch_api_block = arch_text.split("API 列表:", 1)[1].split("helper 清单:", 1)[0]
    spec_text = Path("spec/include/cuda_sm86/cuda_sm86.md").read_text(encoding="utf-8")
    spec_api_block = spec_text.split("## API 列表", 1)[1].split("## 文档信息", 1)[0]
    assert "matmul_f32_kernel" not in include_text
    assert "DeviceMemory" not in include_text
    assert "GmView" not in include_text
    assert "SharedTile" not in include_text
    assert "MmaTileConfig" not in include_text
    assert '#include "include/api/Arch.h"' in include_text
    assert '#include "include/cuda_sm86/Arch.h"' in include_text
    assert "template <typename T>" not in include_text
    assert "`struct cuda_sm86::ArgSlot`" in arch_api_block
    assert "cuda_sm86::detail" not in arch_api_block
    assert "`struct cuda_sm86::ArgSlot`" in spec_api_block
    assert "cuda_sm86::detail" not in spec_api_block
    dmar_ring_ctor_signature = "`template <MemorySpace Space, typename SlotT, typename BackingT> __device__ cuda_sm86::DmaRing<Space, SlotT, BackingT>::DmaRing(Memory<Space, BackingT>& backing, S_INT num, S_INT offset_bytes, const Vector& shape, const Vector& stride, MemoryFormat format)`"
    dmar_ring_current_signature = "`template <MemorySpace Space, typename SlotT, typename BackingT> __device__ Memory<Space, SlotT> cuda_sm86::DmaRing<Space, SlotT, BackingT>::current() const`"
    dmar_ring_advance_signature = "`template <MemorySpace Space, typename SlotT, typename BackingT> __device__ Memory<Space, SlotT> cuda_sm86::DmaRing<Space, SlotT, BackingT>::advance()`"
    dmar_ring_detail_block = spec_text.split("### `cuda_sm86::DmaRing<Space, SlotT, BackingT>`", 1)[1].split(
        "## 后端实现层边界",
        1,
    )[0]
    for signature in (dmar_ring_ctor_signature, dmar_ring_current_signature, dmar_ring_advance_signature):
        assert signature in arch_api_block
        assert signature in spec_api_block
        assert signature in dmar_ring_detail_block
    assert "cuda_sm86::detail::*" in arch_text
    assert "namespace detail" in arch_text
    assert "device_alloc" in arch_text
    assert "copy_host_to_device" in arch_text
    assert "copy_device_to_host" in arch_text
    assert "is_f32_memory" in arch_text
    assert "const unsigned long long requested_rank = size.size() == 0 ? 1 : size.size();" in arch_text
    assert "const unsigned long long view_rank = requested_rank < kMaxDim ? requested_rank : kMaxDim;" in arch_text
    assert "const long long source_stride = axis < rank_ ? stride_[axis] : 1;" in arch_text
    assert "const long long axis_stride = axis < stride.size() ? stride[axis] : 1;" in arch_text
    assert "stride_buf[axis] = source_stride * axis_stride;" in arch_text
    assert "if (offset.size() == 1 && shape.size() > 1)" in arch_text
    assert "linear_offset = offset[0];" in arch_text
    assert 'if alias_kind == "reinterpret":' in source_builder_text
    assert "cuda_sm86::detail::fragment_alias<{result_space_cpp}, float>" in source_builder_text
    assert "detail::copy_from_source_window(target, source, offset, size, stride)" in arch_text
    assert "detail::copy_to_target_window(target, source, offset, size, stride)" in arch_text
    assert "return detail::transpose_memory(target, source, perm);" in arch_text
    assert "const long long source_axis_value = perm[target_axis];" in arch_text
    assert "source_indices[static_cast<unsigned long long>(perm[target_axis])] = target_indices[target_axis];" in arch_text
    assert "target.at(target_indices) = source.at(source_indices)" in arch_text
    assert "detail::matmul_memory(out, lhs, rhs, acc)" in arch_text
    assert 'asm volatile(\n      "mma.sync.aligned.m16n8k8.row.col.f32.tf32.tf32.f32 "' in arch_text
    assert "(void)tensor_core_matmul_path(out, lhs, rhs, acc)" not in arch_text
    assert "kg_cuda_sm86_mma_observable" not in arch_text
    assert "const bool kg_cuda_sm86_tensor_core_used = !acc && tensor_core_matmul_path(out, lhs, rhs, acc);" in arch_text
    assert "out.at(out_indices) = mma_d0" in arch_text
    assert "out.at(out_indices) = mma_d1" in arch_text
    assert "out.at(out_indices) = mma_d2" in arch_text
    assert "out.at(out_indices) = mma_d3" in arch_text
    assert "const bool kg_cuda_sm86_mma_prefix" in arch_text
    assert "const float kg_cuda_sm86_mma_seed = static_cast<float>(out.at(out_indices));" in arch_text
    assert "sum += kg_cuda_sm86_mma_seed - kg_cuda_sm86_mma_seed;" in arch_text
    assert "const unsigned long long k_start = kg_cuda_sm86_mma_prefix" not in arch_text
    assert "if (kg_cuda_sm86_mma_prefix && depth <= kCudaSm86MmaK)" not in arch_text
    assert "tensor_core_seeded_output" not in arch_text
    assert "linear == 0" not in arch_text
    assert "mma_tail" not in arch_text
    assert "out.at(out_indices) = base + mma_d0" not in arch_text
    assert "out.at(out_indices) = sum" in arch_text
    assert "detail::img2col2d_memory(out, input, kh, kw, sh, sw, dh, dw, ph, pw, pl, pr)" in arch_text
    assert "(out.rank() != 2 && out.rank() != 6)" in arch_text
    assert "for (unsigned long long index = 0; index < count; ++index)" in arch_text
    assert "static_cast<unsigned long long>(threadIdx.x); index < count; index += blockDim.x" not in arch_text
    assert "(void)out;\n  (void)lhs;\n  (void)rhs;\n  (void)acc;\n  return kOk;" not in arch_text
    assert "(void)target;\n  (void)source;\n  (void)offset;\n  (void)size;\n  (void)stride;\n  return kOk;" not in arch_text
    assert "include/npu_demo" not in source
    assert "npu_demo::" not in source
    assert "get_dynamic_memory<TLM" not in source


def test_cuda_sm86_emit_dma_ring_byte_pool_source_and_compile_gate() -> None:
    """验证 CUDA ring lowering 使用 i8 backing 且可编译。

    功能说明:
    - 通过公开 `emit_c(...)` 构造含 `DmaMakeRingOp/DmaCurrentRingOp/DmaAdvanceRingOp` 的 final IR。
    - 锁定 i8 byte-pool backing 不再被发射为 `float` alloc，并用公开 CUDA compile strategy 做 nvcc compile gate。

    使用示例:
    - pytest -q test/dsl/gen_kernel/emit/test_cuda_sm86_emit.py -k dma_ring_byte_pool
    """

    set_target("cuda_sm86")
    source = emit_c(_make_minimal_dma_ring_matmul_module(), EmitCContext())
    body = _extract_cuda_sm86_device_body(source)

    assert "// kg.cuda.ir.op: dma.make_ring" in source
    assert "// kg.cuda.ir.op: dma.current_ring" in source
    assert "// kg.cuda.ir.op: dma.advance_ring" in source
    assert "cuda_sm86::alloc<MemorySpace::TLM1, unsigned char>(ctx, Vector{64}, Vector{1})" in body
    assert "cuda_sm86::make_ring<float, MemorySpace::TLM1, unsigned char>" in body
    assert ".current();" in body
    assert ".advance();" in body
    assert "cuda_sm86::alloc<MemorySpace::TLM1, float>(ctx, Vector{64}, Vector{1})" not in body

    arch_text = Path("include/cuda_sm86/Arch.h").read_text(encoding="utf-8")
    assert "normalized_cursor * offset_bytes_" in arch_text
    assert "shape_size_" in arch_text
    assert "stride_[axis]" in arch_text
    nvcc = shutil.which("nvcc")
    if nvcc is None:
        pytest.skip("nvcc is not available in PATH")
    kernel = ExecutionEngine(target="cuda_sm86", compiler=nvcc).compile(source=source, function="minimal_dma_ring_matmul")
    try:
        assert kernel.target == "cuda_sm86"
        assert Path(kernel.soname_path).is_file()
    finally:
        kernel.close()


def test_cuda_sm86_emit_selects_different_sources_from_lowered_entry() -> None:
    """验证 CUDA backend source 随 final IR op 集合变化。

    功能说明:
    - 通过不同公开 lowered demo IR 触发 matmul、conv2d 和 attention SourceBundle。
    - 锁定 generated source 的 entry symbol、op comments、wrapper calls 和 hash 互不相同。

    使用示例:
    - pytest -q test/dsl/gen_kernel/emit/test_cuda_sm86_emit.py -k different_sources
    """

    matmul_module = _make_lowered_demo_module(matmul_inputs_static_tile_static_kernel, MATMUL_ANNOTATIONS, MATMUL_ARGS)
    conv2d_module = _make_lowered_demo_module(conv2d_inputs_static_tile_static_kernel, CONV2D_ANNOTATIONS, CONV2D_ARGS)
    flash_module = _make_lowered_demo_module(
        flash_attention_inputs_static_tile_static_kernel,
        FLASH_ATTENTION_ANNOTATIONS,
        FLASH_ATTENTION_ARGS,
    )
    set_target("cuda_sm86")
    matmul_source = emit_c(matmul_module, EmitCContext())
    conv2d_source = emit_c(conv2d_module, EmitCContext())
    flash_source = emit_c(flash_module, EmitCContext())

    matmul_hash = _extract_cuda_sm86_ir_hash(matmul_source)
    conv2d_hash = _extract_cuda_sm86_ir_hash(conv2d_source)
    flash_hash = _extract_cuda_sm86_ir_hash(flash_source)
    assert f"// kg.cuda.ir.entry_symbol: kg_cuda_sm86_execute_{matmul_hash}_ir" in matmul_source
    assert f"// kg.cuda.ir.entry_symbol: kg_cuda_sm86_execute_{conv2d_hash}_ir" in conv2d_source
    assert f"// kg.cuda.ir.entry_symbol: kg_cuda_sm86_execute_{flash_hash}_ir" in flash_source
    assert f"// kg.cuda.ir.generated_kernel_symbol: kg_cuda_sm86_generated_kernel_{matmul_hash}" in matmul_source
    assert f"// kg.cuda.ir.generated_kernel_symbol: kg_cuda_sm86_generated_kernel_{conv2d_hash}" in conv2d_source
    assert f"// kg.cuda.ir.generated_kernel_symbol: kg_cuda_sm86_generated_kernel_{flash_hash}" in flash_source
    assert f"// kg.cuda.ir.device_body_symbol: kg_cuda_sm86_device_body_{matmul_hash}" in matmul_source
    assert f"// kg.cuda.ir.device_body_symbol: kg_cuda_sm86_device_body_{conv2d_hash}" in conv2d_source
    assert f"// kg.cuda.ir.device_body_symbol: kg_cuda_sm86_device_body_{flash_hash}" in flash_source
    assert "// kg.cuda.ir.op: kernel.matmul" in matmul_source
    assert "// kg.cuda.ir.op: kernel.img2col2d" in conv2d_source
    assert "// kg.cuda.ir.op: kernel.reduce" in flash_source
    assert "// kg.cuda.ir.op: kernel.exp" in flash_source
    assert "cuda_sm86::matmul<" in matmul_source
    assert "cuda_sm86::img2col2d<" in conv2d_source
    assert "cuda_sm86::reduce_" in flash_source
    assert "cuda_sm86::exp<" in flash_source
    assert "cuda_sm86::transpose<MemorySpace::TSM, MemorySpace::TSM, float, float>(ctx" in conv2d_source
    assert "Vector{1, 0, 2, 3}" in conv2d_source
    assert "Vector{1, 0, 1, 1}" not in conv2d_source
    assert "cuda_sm86::transpose<MemorySpace::TSM, MemorySpace::TSM, float, float>(ctx" in flash_source
    assert "cuda_sm86::detail::fragment_alias<MemorySpace::GM, float>" in flash_source
    assert "Vector{1, 0}" in flash_source
    assert "cuda_sm86::transpose<MemorySpace::TSM, MemorySpace::TSM, float, float>(ctx, kg_v_199_0, kg_v_198_0, Vector{1, 1})" not in flash_source
    assert "-INFINITY" in flash_source
    assert "float kg_v_155_0 = 0.0f;" not in flash_source
    assert f"__global__ void kg_cuda_sm86_generated_kernel_{matmul_hash}" in matmul_source
    assert f"__global__ void kg_cuda_sm86_generated_kernel_{conv2d_hash}" in conv2d_source
    assert f"__global__ void kg_cuda_sm86_generated_kernel_{flash_hash}" in flash_source
    assert matmul_hash != conv2d_hash
    assert matmul_hash != flash_hash
    assert matmul_source != conv2d_source
    assert matmul_source != flash_source
    assert conv2d_source != flash_source


def test_cuda_sm86_ir_hash_is_stable_and_op_sequence_specific() -> None:
    """验证 CUDA final IR hash 稳定且随 op 集合变化。

    功能说明:
    - 同一 lowered ModuleOp 重复 `emit_c(...)` 必须得到相同 hash。
    - 不同 demo final IR 的 op 集合不同时，hash 必须不同。

    使用示例:
    - pytest -q test/dsl/gen_kernel/emit/test_cuda_sm86_emit.py -k cuda_sm86_ir_hash
    """

    matmul_module = _make_lowered_demo_module(matmul_inputs_static_tile_static_kernel, MATMUL_ANNOTATIONS, MATMUL_ARGS)
    conv2d_module = _make_lowered_demo_module(conv2d_inputs_static_tile_static_kernel, CONV2D_ANNOTATIONS, CONV2D_ARGS)
    set_target("cuda_sm86")
    first_matmul_source = emit_c(matmul_module, EmitCContext())
    second_matmul_source = emit_c(matmul_module, EmitCContext())
    conv2d_source = emit_c(conv2d_module, EmitCContext())

    first_hash = _extract_cuda_sm86_ir_hash(first_matmul_source)
    second_hash = _extract_cuda_sm86_ir_hash(second_matmul_source)
    conv2d_hash = _extract_cuda_sm86_ir_hash(conv2d_source)
    assert first_hash == second_hash
    assert first_hash != conv2d_hash
    assert first_matmul_source == second_matmul_source


def test_cuda_sm86_executable_trace_changes_with_same_entry_final_ir_op_sequence() -> None:
    """验证同类 compute 的可执行 code 随 final IR op sequence 变化。

    功能说明:
    - 构造两个同为 matmul compute 的公开 ModuleOp 输入，只改变 pre-matmul op sequence。
    - 通过公开 `emit_c(...)` 证明非注释的 generated device body 读取真实 final IR sequence。

    使用示例:
    - pytest -q test/dsl/gen_kernel/emit/test_cuda_sm86_emit.py -k same_entry_final_ir_op_sequence
    """

    base_module = _make_minimal_c5_matmul_module()
    sequence_module = _make_minimal_c5_matmul_module(extra_lhs_copy=True)
    set_target("cuda_sm86")
    base_source = emit_c(base_module, EmitCContext())
    sequence_source = emit_c(sequence_module, EmitCContext())
    base_body = _extract_cuda_sm86_device_body(base_source)
    sequence_body = _extract_cuda_sm86_device_body(sequence_source)

    base_hash = _extract_cuda_sm86_ir_hash(base_source)
    sequence_hash = _extract_cuda_sm86_ir_hash(sequence_source)
    assert f"// kg.cuda.ir.device_body_symbol: kg_cuda_sm86_device_body_{base_hash}" in base_source
    assert f"// kg.cuda.ir.device_body_symbol: kg_cuda_sm86_device_body_{sequence_hash}" in sequence_source
    assert base_hash != sequence_hash
    assert base_body != sequence_body
    assert "cuda_sm86::matmul<" in base_body
    assert "cuda_sm86::matmul<" in sequence_body
    assert "cuda_sm86::load<" in base_body
    assert "cuda_sm86::load<" in sequence_body
    assert "cuda_sm86::store<" in base_body
    assert "cuda_sm86::store<" in sequence_body
    assert sequence_body.count("cuda_sm86::load<") == base_body.count("cuda_sm86::load<") + 1


def test_cuda_sm86_executable_trace_changes_with_same_type_dataflow() -> None:
    """验证同类型 SSA dataflow 变化会改变 hash、trace body 和 source。

    功能说明:
    - 构造两个同 entry、同 op sequence、同 attrs、同 operand/result type 的公开 ModuleOp 输入。
    - 只交换 `dma.copy` 的 lhs/rhs public source SSA value，证明 operand identity 进入 stable record 和 wrapper call operands。

    使用示例:
    - pytest -q test/dsl/gen_kernel/emit/test_cuda_sm86_emit.py -k same_type_dataflow
    """

    base_module = _make_minimal_c5_matmul_module(square_operand_types=True)
    swapped_module = _make_minimal_c5_matmul_module(square_operand_types=True, swap_lhs_rhs_sources=True)
    set_target("cuda_sm86")
    base_source = emit_c(base_module, EmitCContext())
    swapped_source = emit_c(swapped_module, EmitCContext())
    base_body = _extract_cuda_sm86_device_body(base_source)
    swapped_body = _extract_cuda_sm86_device_body(swapped_source)
    base_loads = [line for line in base_body.splitlines() if "cuda_sm86::load<MemorySpace::TLM1, MemorySpace::GM" in line]
    swapped_loads = [line for line in swapped_body.splitlines() if "cuda_sm86::load<MemorySpace::TLM1, MemorySpace::GM" in line]

    base_hash = _extract_cuda_sm86_ir_hash(base_source)
    swapped_hash = _extract_cuda_sm86_ir_hash(swapped_source)
    assert f"// kg.cuda.ir.device_body_symbol: kg_cuda_sm86_device_body_{base_hash}" in base_source
    assert f"// kg.cuda.ir.device_body_symbol: kg_cuda_sm86_device_body_{swapped_hash}" in swapped_source
    assert base_source.count("// kg.cuda.ir.op: ") == swapped_source.count("// kg.cuda.ir.op: ")
    assert len(base_loads) == len(swapped_loads)
    assert base_loads != swapped_loads
    assert "cuda_sm86::matmul<" in base_body
    assert "cuda_sm86::matmul<" in swapped_body
    assert base_hash != swapped_hash
    assert base_body != swapped_body
    assert base_source != swapped_source


def test_cuda_sm86_matmul_materialization_rejects_non_all_tlm1() -> None:
    """验证 C5 marker 拒绝非 all-TLM1 matmul operand。

    功能说明:
    - 构造 lhs staged 到 `tlm2` 的公开 ModuleOp 输入。
    - 通过公开 `emit_c(...)` 证明 `kernel.matmul` marker 必须读取真实 operand memory space。

    使用示例:
    - pytest -q test/dsl/gen_kernel/emit/test_cuda_sm86_emit.py -k non_all_tlm1
    """

    set_target("cuda_sm86")
    with pytest.raises(KernelCodeError, match="kernel.matmul C5 materialization requires out/lhs/rhs tlm1; got tlm1,tlm2,tlm1"):
        emit_c(_make_minimal_c5_matmul_module(lhs_space="tlm2"), EmitCContext())


def test_cuda_sm86_matmul_materialization_rejects_missing_writeback() -> None:
    """验证 C5 marker 拒绝缺失 out write-back 的 matmul。

    功能说明:
    - 构造 out/lhs/rhs 均为 `tlm1` 但不写回原 out descriptor 的 ModuleOp 输入。
    - 通过公开 `emit_c(...)` 证明 marker 不会在 write-back 缺失时假阳性。

    使用示例:
    - pytest -q test/dsl/gen_kernel/emit/test_cuda_sm86_emit.py -k missing_writeback
    """

    set_target("cuda_sm86")
    with pytest.raises(KernelCodeError, match="kernel.matmul C5 materialization requires visible out write-back"):
        emit_c(_make_minimal_c5_matmul_module(include_writeback=False), EmitCContext())


@pytest.mark.parametrize(
    "name",
    [
        "unsupported_kernel",
        "matmul_name_only_kernel",
        "conv2d_name_only_kernel",
        "flash_attention_name_only_kernel",
    ],
)
def test_cuda_sm86_emit_rejects_name_only_or_unknown_module(name: str) -> None:
    """验证 CUDA backend 不用函数名或 fallback 生成 SourceBundle。

    功能说明:
    - 通过公开 `emit_c(...)` 输入只有函数名、没有 supported final IR compute op 的 module。
    - 锁定 unsupported / unknown module 的稳定失败语义，防止 name-only 假绿。

    使用示例:
    - pytest -q test/dsl/gen_kernel/emit/test_cuda_sm86_emit.py -k name_only
    """

    set_target("cuda_sm86")
    with pytest.raises(KernelCodeError, match="unsupported cuda_sm86 final IR op: <none>"):
        emit_c(_make_module(name), EmitCContext())


def test_cuda_sm86_emit_rejects_printed_string_tokens_without_kernel_ops() -> None:
    """验证 CUDA backend 不用 printed IR 字符串 token 伪造 final IR source。

    功能说明:
    - 输入函数类型与属性文本足以骗过旧文本计数逻辑。
    - 当前 backend 必须遍历真实 `Operation.name`，无 actual kernel op 时稳定失败。

    使用示例:
    - pytest -q test/dsl/gen_kernel/emit/test_cuda_sm86_emit.py -k printed_string_tokens
    """

    set_target("cuda_sm86")
    with pytest.raises(KernelCodeError, match="unsupported cuda_sm86 final IR op: <none>"):
        emit_c(_make_spoofed_string_token_module(), EmitCContext())


def test_cuda_sm86_gen_kernel_dump_writes_bundle_artifacts(tmp_path: Path) -> None:
    """验证 `gen_kernel(...)` 写出 CUDA SourceBundle artifact。

    功能说明:
    - 设置公开 `dump_dir` 后调用 `gen_kernel(...)`。
    - 核对 aggregate `source.cpp`、`kernel.cu` 和 generated entry header 均落盘。

    使用示例:
    - pytest -q test/dsl/gen_kernel/emit/test_cuda_sm86_emit.py -k dump_writes
    """

    module = _make_lowered_demo_module(matmul_inputs_static_tile_static_kernel, MATMUL_ANNOTATIONS, MATMUL_ARGS)
    set_target("cuda_sm86")
    set_dump_dir(tmp_path)

    source = gen_kernel(module, EmitCContext())

    assert (tmp_path / "source.cpp").read_text(encoding="utf-8") == source
    kernel_source = (tmp_path / "kernel.cu").read_text(encoding="utf-8")
    header_source = (tmp_path / "include" / "cuda_sm86" / "generated_entry.cuh").read_text(encoding="utf-8")
    assert "cuda_sm86 generated from final IR" in kernel_source
    assert "// kg.cuda.ir.func: matmul_inputs_static_tile_static_kernel" in kernel_source
    assert "mma.sync.aligned.m16n8k8" in kernel_source
    assert "// kg.cuda.ir.hash: " in kernel_source
    assert "// kg.cuda.ir.op: kernel.matmul" in kernel_source
    assert "// kg.cuda.ir.matmul.materialization: out=tlm1,lhs=tlm1,rhs=tlm1,write_back=visible" in kernel_source
    for token in OLD_CUDA_SM86_SOURCE_TOKENS:
        assert token not in kernel_source
    assert "cuda_sm86::ArgSlot" in header_source


def test_cuda_sm86_emit_package_structure_matches_plan() -> None:
    """验证 CUDA SM86 emit package 结构符合计划。

    功能说明:
    - 只读取文件和 AST，不 import / direct call `cuda_sm86` package 内部 helper。
    - 锁定 root 聚合、唯一 `module.py` handler、依赖方向和空 `__all__`。

    使用示例:
    - pytest -q test/dsl/gen_kernel/emit/test_cuda_sm86_emit.py -k package_structure
    """

    root = Path("kernel_gen/dsl/gen_kernel/emit/cuda_sm86")
    expected_files = {
        "__init__.py",
        "constants.py",
        "include.py",
        "module.py",
        "runtime.py",
        "source_bundle.py",
        "kernel/__init__.py",
        "kernel/binary_elewise.py",
        "kernel/exp.py",
        "kernel/img2col2d.py",
        "kernel/matmul.py",
        "kernel/reduce.py",
    }
    for rel_path in expected_files:
        assert (root / rel_path).is_file(), rel_path
    assert Path("include/cuda_sm86/Arch.h").is_file()

    init_text = (root / "__init__.py").read_text(encoding="utf-8")
    for token in (
        "_COMMON_CUDA_RUNTIME_SOURCE",
        "_MATMUL_CUDA_SOURCE",
        "_CONV2D_CUDA_SOURCE",
        "kg_cuda_sm86_" + "run_",
        "mma.sync",
        "__global__",
        "@emit_c_impl",
    ):
        assert token not in init_text, token

    assert not (root / "source").exists()

    emit_files: list[str] = []
    include_files: list[str] = []
    imports_by_path: dict[str, set[str]] = {}
    for path in sorted(root.rglob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        modules: set[str] = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                for decorator in node.decorator_list:
                    current = decorator
                    while isinstance(current, ast.Call):
                        current = current.func
                    parts: list[str] = []
                    while isinstance(current, ast.Attribute):
                        parts.append(current.attr)
                        current = current.value
                    if isinstance(current, ast.Name):
                        parts.append(current.id)
                    decorator_name = ".".join(reversed(parts))
                    if decorator_name.endswith("emit_c_impl"):
                        emit_files.append(path.as_posix())
                    if decorator_name.endswith("emit_c_include_impl"):
                        include_files.append(path.as_posix())
            if isinstance(node, ast.Import):
                modules.update(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom):
                prefix = "." * node.level
                if node.module:
                    base = prefix + node.module
                    parts = base.split(".")
                    if len(parts) >= 3 and parts[-2] == "kernel":
                        modules.add(base)
                    else:
                        modules.add(base)
                else:
                    for alias in node.names:
                        modules.add(prefix + alias.name)
        imports_by_path[path.as_posix()] = modules

    assert emit_files == [
        "kernel_gen/dsl/gen_kernel/emit/cuda_sm86/kernel/binary_elewise.py",
        "kernel_gen/dsl/gen_kernel/emit/cuda_sm86/kernel/exp.py",
        "kernel_gen/dsl/gen_kernel/emit/cuda_sm86/kernel/img2col2d.py",
        "kernel_gen/dsl/gen_kernel/emit/cuda_sm86/kernel/matmul.py",
        "kernel_gen/dsl/gen_kernel/emit/cuda_sm86/kernel/reduce.py",
        "kernel_gen/dsl/gen_kernel/emit/cuda_sm86/module.py",
    ]
    assert include_files == ["kernel_gen/dsl/gen_kernel/emit/cuda_sm86/include.py"]
    allowed_imports = {
        "kernel_gen/dsl/gen_kernel/emit/cuda_sm86/__init__.py": {".include", ".kernel", ".module"},
        "kernel_gen/dsl/gen_kernel/emit/cuda_sm86/constants.py": set(),
        "kernel_gen/dsl/gen_kernel/emit/cuda_sm86/module.py": {".constants", ".source_bundle"},
        "kernel_gen/dsl/gen_kernel/emit/cuda_sm86/source_bundle.py": {".constants", ".runtime"},
        "kernel_gen/dsl/gen_kernel/emit/cuda_sm86/include.py": {".constants"},
        "kernel_gen/dsl/gen_kernel/emit/cuda_sm86/runtime.py": {".constants"},
        "kernel_gen/dsl/gen_kernel/emit/cuda_sm86/kernel/__init__.py": {".binary_elewise", ".exp", ".img2col2d", ".matmul", ".reduce"},
        "kernel_gen/dsl/gen_kernel/emit/cuda_sm86/kernel/binary_elewise.py": {"..constants"},
        "kernel_gen/dsl/gen_kernel/emit/cuda_sm86/kernel/exp.py": {"..constants"},
        "kernel_gen/dsl/gen_kernel/emit/cuda_sm86/kernel/img2col2d.py": {"..constants"},
        "kernel_gen/dsl/gen_kernel/emit/cuda_sm86/kernel/matmul.py": {"..constants"},
        "kernel_gen/dsl/gen_kernel/emit/cuda_sm86/kernel/reduce.py": {"..constants"},
    }
    package_root = ".".join(("kernel_gen", "dsl", "gen_kernel", "emit", "cuda_sm86"))
    for rel, allowed in allowed_imports.items():
        imports = {
            item
            for item in imports_by_path[rel]
            if item.startswith(".") or item.startswith(package_root)
        }
        assert imports <= allowed, (rel, imports, allowed)

    for package_init in (root / "__init__.py", root / "kernel" / "__init__.py"):
        tree = ast.parse(package_init.read_text(encoding="utf-8"), filename=str(package_init))
        exports: list[ast.expr] = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Assign) and any(isinstance(target, ast.Name) and target.id == "__all__" for target in node.targets):
                exports.append(node.value)
            if isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name) and node.target.id == "__all__":
                exports.append(node.value)
        assert exports, f"missing __all__: {package_init}"
        assert isinstance(exports[-1], ast.List) and not exports[-1].elts, f"__all__ must be empty list: {package_init}"

    internal_children = {"constants", "module", "runtime", "source_bundle", "kernel"}
    forbidden_internal_path = package_root + "."
    for test_file in Path("test").rglob("*.py"):
        tree = ast.parse(test_file.read_text(encoding="utf-8"), filename=str(test_file))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    assert not alias.name.startswith(forbidden_internal_path), (test_file, alias.name)
            elif isinstance(node, ast.ImportFrom):
                module = node.module or ""
                if module.startswith(forbidden_internal_path):
                    raise AssertionError((test_file, module))
                if module == package_root:
                    for alias in node.names:
                        assert alias.name not in internal_children, (test_file, module, alias.name)
            elif isinstance(node, ast.Constant) and isinstance(node.value, str):
                assert forbidden_internal_path not in node.value, (test_file, node.value)
