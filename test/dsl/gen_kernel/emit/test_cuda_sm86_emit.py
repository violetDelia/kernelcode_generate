"""CUDA SM86 emit backend tests.


功能说明:
- 通过公开 `gen_kernel(...)` / `emit_c(...)` 入口验证 CUDA SM86 backend 自动加载与 SourceBundle 输出。
- 覆盖 generated CUDA source 的 include、generated demo kernels、entry ABI 和 npu_demo 残留扫描。

使用示例:
- pytest -q test/dsl/gen_kernel/emit/test_cuda_sm86_emit.py

关联文件:
- 功能实现: kernel_gen/dsl/gen_kernel/emit/cuda_sm86/__init__.py
- Spec 文档: spec/dsl/gen_kernel/emit/cuda_sm86.md
- 测试文件: test/dsl/gen_kernel/emit/test_cuda_sm86_emit.py
"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
import sys

import pytest
from xdsl.dialects import func
from xdsl.dialects.builtin import ArrayAttr, ModuleOp, StringAttr, f32
from xdsl.ir import Block, Region

REPO_ROOT = Path(__file__).resolve().parents[4]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from kernel.conv2d.inputs_static_tile_static import conv2d_inputs_static_tile_static_kernel
from kernel.flash_attention.inputs_static_tile_static import flash_attention_inputs_static_tile_static_kernel
from kernel.matmul.inputs_static_tile_static import matmul_inputs_static_tile_static_kernel
from kernel_gen.core.config import reset_config, set_dump_dir, set_target
from kernel_gen.core.error import KernelCodeError
from kernel_gen.dialect.nn import NnMemorySpaceAttr, NnMemoryType
from kernel_gen.dialect.symbol import SymbolExprAttr
from kernel_gen.dsl.ast.mlir_gen import mlir_gen
from kernel_gen.dsl.gen_kernel import EmitCContext, emit_c, gen_kernel
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
    - 属性文本包含 `kernel.matmul` / `arch.launch`，用于证明 CUDA backend 不读取 printed IR 字符串做 family 判定。

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
    - 运行公开 `build_cuda_sm86_lowering_pipeline()`，让 emit 测试基于真实 lowered IR 判定 kernel family。

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


def test_cuda_sm86_emit_module_returns_source_bundle() -> None:
    """验证 CUDA backend 返回 SourceBundle aggregate string。

    功能说明:
    - 通过公开 `emit_c(...)` 触发 backend auto-load。
    - 锁定 `.cu/.cuh` artifact marker、CUDA include、generated demo kernel 与 C ABI entry。

    使用示例:
    - pytest -q test/dsl/gen_kernel/emit/test_cuda_sm86_emit.py -k source_bundle
    """

    module = _make_lowered_demo_module(matmul_inputs_static_tile_static_kernel, MATMUL_ANNOTATIONS, MATMUL_ARGS)
    set_target("cuda_sm86")
    source = emit_c(module, EmitCContext())

    assert source.startswith("// __KG_BUNDLE_FILE__:kernel.cu\n")
    assert '// __KG_BUNDLE_FILE__:include/cuda_sm86/generated_entry.cuh' in source
    assert '#include "include/cuda_sm86/cuda_sm86.cuh"' in source
    assert 'kg_cuda_sm86_selected_kernel_kind = "matmul"' in source
    assert "__global__ void kg_cuda_sm86_generated_matmul_kernel" in source
    assert "__global__ void kg_cuda_sm86_conv2d_f32_kernel" not in source
    assert "__global__ void kg_cuda_sm86_flash_attention_f32_kernel" not in source
    assert "mma.sync.aligned.m16n8k8" in source
    assert "tensor_core_probe" not in source
    assert "acc += lhs" not in source
    assert "kg_cuda_sm86_device_alloc" in source
    assert "kg_cuda_sm86_is_f32_memory" in source
    assert 'extern "C" int kg_execute_entry(cuda_sm86::ArgSlot* slots, unsigned long long count)' in source
    assert "launch_matmul_entry" not in source
    assert "matmul_f32_kernel" not in source
    include_text = Path("include/cuda_sm86/cuda_sm86.cuh").read_text(encoding="utf-8")
    assert "matmul_f32_kernel" not in include_text
    assert "DeviceMemory" not in include_text
    assert "GmView" not in include_text
    assert "SharedTile" not in include_text
    assert "MmaTileConfig" not in include_text
    assert "device_alloc" not in include_text
    assert "copy_host_to_device" not in include_text
    assert "copy_device_to_host" not in include_text
    assert "is_f32_memory" not in include_text
    assert "include/npu_demo" not in source
    assert "npu_demo::" not in source
    assert "get_dynamic_memory<TLM" not in source


def test_cuda_sm86_emit_selects_different_sources_from_lowered_entry() -> None:
    """验证 CUDA backend 不输出固定三合一 SourceBundle。

    功能说明:
    - 通过不同公开 lowered demo IR 触发 matmul、conv2d 和 flash_attention SourceBundle。
    - 锁定 generated source 的 kernel kind 与 device kernel 互斥，证明 emit 不再是固定万能 dispatcher。

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

    assert 'kg_cuda_sm86_selected_kernel_kind = "matmul"' in matmul_source
    assert 'kg_cuda_sm86_selected_kernel_kind = "conv2d"' in conv2d_source
    assert 'kg_cuda_sm86_selected_kernel_kind = "flash_attention"' in flash_source
    assert "__global__ void kg_cuda_sm86_generated_matmul_kernel" in matmul_source
    assert "__global__ void kg_cuda_sm86_conv2d_f32_kernel" not in matmul_source
    assert "__global__ void kg_cuda_sm86_conv2d_f32_kernel" in conv2d_source
    assert "__global__ void kg_cuda_sm86_flash_attention_f32_kernel" in flash_source
    assert matmul_source != conv2d_source
    assert matmul_source != flash_source
    assert conv2d_source != flash_source


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
    - 通过公开 `emit_c(...)` 输入只有函数名、没有 lowered kernel op family 的 module。
    - 锁定 unsupported / unknown module 的稳定失败语义，防止 name-only 假绿。

    使用示例:
    - pytest -q test/dsl/gen_kernel/emit/test_cuda_sm86_emit.py -k name_only
    """

    set_target("cuda_sm86")
    with pytest.raises(KernelCodeError, match="unsupported kernel family"):
        emit_c(_make_module(name), EmitCContext())


def test_cuda_sm86_emit_rejects_printed_string_tokens_without_kernel_ops() -> None:
    """验证 CUDA backend 不用 printed IR 字符串 token 伪造 kernel family。

    功能说明:
    - 输入函数类型与属性文本足以骗过旧文本计数逻辑。
    - 当前 backend 必须遍历真实 `Operation.name`，无 actual kernel op 时稳定失败。

    使用示例:
    - pytest -q test/dsl/gen_kernel/emit/test_cuda_sm86_emit.py -k printed_string_tokens
    """

    set_target("cuda_sm86")
    with pytest.raises(KernelCodeError, match="unsupported kernel family"):
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
    assert "cuda_sm86 generated from lowered IR" in kernel_source
    assert "matmul_inputs_static_tile_static_kernel" not in kernel_source
    assert "mma.sync.aligned.m16n8k8" in kernel_source
    assert 'kg_cuda_sm86_selected_kernel_kind = "matmul"' in kernel_source
    assert "kg_cuda_sm86_run_matmul" in kernel_source
    assert "cuda_sm86::ArgSlot" in header_source
