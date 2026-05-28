"""CUDA SM86 kernel demo runtime integration tests.

功能说明:
- 在具备 CUDA toolkit 与 GPU 的环境中，通过 9 个现有 kernel demo 的公开 kernel 函数生成 IR。
- 每个 case 都执行 `cuda-sm86-lowering -> emit_c(target="cuda_sm86") -> ExecutionEngine(target="cuda_sm86") -> execute`。
- 测试只验证本计划确认的 matmul / conv2d / flash_attention demo 范围，不扩大到任意 DSL kernel。

使用示例:
- pytest -q test/cuda/test_cuda_sm86_kernel_demos_runtime.py -m cuda

关联文件:
- 功能实现: include/cuda_sm86/cuda_sm86.cuh
- 功能实现: kernel_gen/dsl/gen_kernel/emit/cuda_sm86/__init__.py
- 功能实现: kernel_gen/execute_engine/builtin_strategy/cuda_sm86.py
- 测试文件: test/cuda/test_cuda_sm86_kernel_demos_runtime.py
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
import shutil
import subprocess
import sys
from typing import TypeAlias

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from kernel.conv2d.inputs_dynamic_tile_dynamic import conv2d_inputs_dynamic_tile_dynamic_kernel
from kernel.conv2d.inputs_static_tile_dynamic import conv2d_inputs_static_tile_dynamic_kernel
from kernel.conv2d.inputs_static_tile_static import conv2d_inputs_static_tile_static_kernel
from kernel.flash_attention.inputs_dynamic_tile_dynamic import flash_attention_inputs_dynamic_tile_dynamic_kernel
from kernel.flash_attention.inputs_static_tile_dynamic import flash_attention_inputs_static_tile_dynamic_kernel
from kernel.flash_attention.inputs_static_tile_static import flash_attention_inputs_static_tile_static_kernel
from kernel.matmul.inputs_dynamic_tile_dynamic import matmul_inputs_dynamic_tile_dynamic_kernel
from kernel.matmul.inputs_static_tile_dynamic import matmul_inputs_static_tile_dynamic_kernel
from kernel.matmul.inputs_static_tile_static import matmul_inputs_static_tile_static_kernel
from kernel_gen.core.config import reset_config, set_target
from kernel_gen.dsl.ast.mlir_gen import mlir_gen
from kernel_gen.dsl.gen_kernel import EmitCContext, emit_c
from kernel_gen.execute_engine import CompiledKernel, ExecutionEngine
from kernel_gen.pipeline import build_cuda_sm86_lowering_pipeline
from kernel_gen.symbol_variable.memory import Memory
from kernel_gen.symbol_variable.symbol_dim import SymbolDim
from kernel_gen.symbol_variable.type import NumericType

pytestmark = pytest.mark.cuda

CompileArg: TypeAlias = "Memory | SymbolDim | int | str"
KernelFn: TypeAlias = "Callable[..., None]"


@dataclass(frozen=True)
class KernelDemoCase:
    """CUDA demo 编译 case。

    功能说明:
    - 绑定一个现有 kernel demo 的公开 kernel 函数、临时编译 annotations 与公开 `mlir_gen(...)` 实参。
    - `path` 与真实 demo 脚本一一对应，review 可机械核对 9-demo 覆盖。

    使用示例:
    - case = KernelDemoCase("kernel/matmul/inputs_static_tile_static.py", fn, {}, ())
    """

    path: str
    kernel_fn: KernelFn
    annotations: dict[str, str]
    compile_args: tuple[CompileArg, ...]


def _memory(shape: list[int | str], dtype: NumericType = NumericType.Float32) -> Memory:
    """构造公开 Memory 编译实参。

    功能说明:
    - 使用公开 `Memory(...)` API 描述 demo kernel 的编译期 shape/dtype。
    - 允许 static int shape 与 dynamic symbol name 混合，匹配现有 9 个 demo 的公开签名。

    使用示例:
    - out = _memory([2, 4])
    """

    normalized_shape = list(shape)
    if not normalized_shape:
        raise AssertionError("memory shape must not be empty")
    dtype_value = dtype
    memory_value = Memory(normalized_shape, dtype_value)
    return memory_value


def _symbol(name: str) -> SymbolDim:
    """构造公开 SymbolDim 编译实参。

    功能说明:
    - 使用公开 `SymbolDim(...)` API 描述 dynamic tile 或 dynamic shape 参数。
    - 只服务 9-demo CUDA pipeline runtime gate。

    使用示例:
    - tile_m = _symbol("TM")
    """

    name_text = str(name)
    if not name_text:
        raise AssertionError("symbol name must not be empty")
    symbol_value = SymbolDim(name_text)
    return symbol_value


def _compile_cuda_demo_kernel(case: KernelDemoCase) -> CompiledKernel:
    """从现有 demo 公开入口编译 CUDA SM86 kernel。

    功能说明:
    - 临时设置 demo 函数 annotations，让 runtime gate 使用小规模、可快速验证的合法 profile。
    - 通过公开 `mlir_gen(...)` 读取并调用现有 demo kernel 函数，随后执行公开 `cuda-sm86-lowering` pipeline。
    - 通过公开 `emit_c(...)` 与 `ExecutionEngine(target="cuda_sm86")` 完成 SourceBundle 编译。

    使用示例:
    - kernel = _compile_cuda_demo_kernel(MATMUL_DEMO_CASES[0])
    """

    original_annotations = dict(case.kernel_fn.__annotations__)
    case.kernel_fn.__annotations__.update(case.annotations)
    try:
        reset_config()
        set_target("cuda_sm86")
        module = mlir_gen(case.kernel_fn, *case.compile_args)
        build_cuda_sm86_lowering_pipeline().run(module)
        source = emit_c(module, EmitCContext())
        return ExecutionEngine(target="cuda_sm86").compile(source=source, function=case.kernel_fn.__name__)
    finally:
        case.kernel_fn.__annotations__.clear()
        case.kernel_fn.__annotations__.update(original_annotations)
        reset_config()


def _emit_cuda_demo_source(case: KernelDemoCase) -> str:
    """从现有 demo 公开入口生成 CUDA SM86 SourceBundle。

    功能说明:
    - 经公开 `mlir_gen(...)`、`cuda-sm86-lowering` 和 `emit_c(...)` 生成 CUDA source。
    - 用于证明不同 demo 的 lowered IR 会影响 generated SourceBundle。

    使用示例:
    - source = _emit_cuda_demo_source(MATMUL_DEMO_CASES[0])
    """

    original_annotations = dict(case.kernel_fn.__annotations__)
    case.kernel_fn.__annotations__.update(case.annotations)
    try:
        reset_config()
        set_target("cuda_sm86")
        module = mlir_gen(case.kernel_fn, *case.compile_args)
        build_cuda_sm86_lowering_pipeline().run(module)
        return emit_c(module, EmitCContext())
    finally:
        case.kernel_fn.__annotations__.clear()
        case.kernel_fn.__annotations__.update(original_annotations)
        reset_config()


def _require_cuda_environment() -> None:
    """校验 CUDA runtime gate 环境。

    功能说明:
    - 缺 `nvcc` 或 CUDA device 时按计划记录为环境缺失 skip。
    - 存在环境时不跳过，确保 9-demo runtime gate 真实编译执行。

    使用示例:
    - _require_cuda_environment()
    """

    if shutil.which("nvcc") is None:
        pytest.skip("nvcc is not available in PATH")
    gpu_probe = subprocess.run(["nvidia-smi"], capture_output=True, text=True, check=False)
    if gpu_probe.returncode != 0:
        pytest.skip("CUDA device is not available")


def _softmax_attention_reference(q_value, k_value, v_value):
    """计算 Flash Attention 小形状 NumPy 参考。

    功能说明:
    - 使用最后一维 softmax 语义生成 expected。
    - 该 helper 只服务当前公开 runtime gate，不调用仓库非公开 API。

    使用示例:
    - expected = _softmax_attention_reference(q, k, v)
    """

    numpy = pytest.importorskip("numpy")
    score = numpy.matmul(q_value, numpy.swapaxes(k_value, -1, -2))
    shifted = score - numpy.max(score, axis=-1, keepdims=True)
    weights = numpy.exp(shifted).astype(numpy.float32)
    weights = weights / numpy.sum(weights, axis=-1, keepdims=True)
    return numpy.matmul(weights, v_value).astype(numpy.float32)


def _conv2d_reference(input_tensor, weight, bias, stride, dilation, padding):
    """计算 NCHW conv2d 小形状 NumPy 参考。

    功能说明:
    - 支持本 runtime gate 使用的 stride / dilation / 非对称 padding。
    - 返回与 generated CUDA conv2d entry 对齐的 NCHW 输出。

    使用示例:
    - expected = _conv2d_reference(x, w, bias, (1, 1), (1, 1), (0, 0, 0, 0))
    """

    numpy = pytest.importorskip("numpy")
    pad_top, pad_bottom, pad_left, pad_right = padding
    padded = numpy.pad(input_tensor, ((0, 0), (0, 0), (pad_top, pad_bottom), (pad_left, pad_right)))
    batch, _channels, in_h, in_w = padded.shape
    out_channels, _in_channels, kernel_h, kernel_w = weight.shape
    out_h = ((in_h - dilation[0] * (kernel_h - 1) - 1) // stride[0]) + 1
    out_w = ((in_w - dilation[1] * (kernel_w - 1) - 1) // stride[1]) + 1
    output = numpy.zeros((batch, out_channels, out_h, out_w), dtype=numpy.float32)
    for kh_index in range(kernel_h):
        h_start = kh_index * dilation[0]
        h_stop = h_start + out_h * stride[0]
        for kw_index in range(kernel_w):
            w_start = kw_index * dilation[1]
            w_stop = w_start + out_w * stride[1]
            window = padded[:, :, h_start:h_stop:stride[0], w_start:w_stop:stride[1]]
            output += numpy.einsum("nchw,fc->nfhw", window, weight[:, :, kh_index, kw_index], optimize=True)
    if bias is not None:
        output += bias[None, :, None, None]
    return output


MATMUL_DEMO_CASES = (
    KernelDemoCase(
        "kernel/matmul/inputs_static_tile_static.py",
        matmul_inputs_static_tile_static_kernel,
        {
            "out": "Tensor[f32, 2, 4]",
            "lhs": "Tensor[f32, 2, 3]",
            "rhs": "Tensor[f32, 3, 4]",
            "bias": "Tensor[f32, 4]",
        },
        (_memory([2, 4]), _memory([2, 3]), _memory([3, 4]), _memory([4])),
    ),
    KernelDemoCase(
        "kernel/matmul/inputs_static_tile_dynamic.py",
        matmul_inputs_static_tile_dynamic_kernel,
        {
            "out": "Tensor[f32, 2, 4]",
            "lhs": "Tensor[f32, 2, 3]",
            "rhs": "Tensor[f32, 3, 4]",
            "bias": "Tensor[f32, 4]",
        },
        (_memory([2, 4]), _memory([2, 3]), _memory([3, 4]), _memory([4]), _symbol("TM"), _symbol("TN"), _symbol("TK")),
    ),
    KernelDemoCase(
        "kernel/matmul/inputs_dynamic_tile_dynamic.py",
        matmul_inputs_dynamic_tile_dynamic_kernel,
        {
            "out": "Tensor[f32, M, N]",
            "lhs": "Tensor[f32, M, K]",
            "rhs": "Tensor[f32, K, N]",
            "bias": "Tensor[f32, N]",
        },
        (_memory(["M", "N"]), _memory(["M", "K"]), _memory(["K", "N"]), _memory(["N"]), _symbol("TM"), _symbol("TN"), _symbol("TK")),
    ),
)

CONV2D_DEMO_CASES = (
    KernelDemoCase(
        "kernel/conv2d/inputs_static_tile_static.py",
        conv2d_inputs_static_tile_static_kernel,
        {
            "out": "Tensor[f32, 1, 3, 4, 5]",
            "input_tensor": "Tensor[f32, 1, 2, 4, 5]",
            "weight": "Tensor[f32, 3, 2, 2, 2]",
            "bias": "Tensor[f32, 3]",
        },
        (_memory([1, 3, 4, 5]), _memory([1, 2, 4, 5]), _memory([3, 2, 2, 2]), _memory([3])),
    ),
    KernelDemoCase(
        "kernel/conv2d/inputs_static_tile_dynamic.py",
        conv2d_inputs_static_tile_dynamic_kernel,
        {
            "out": "Tensor[f32, 1, 3, 4, 5]",
            "input_tensor": "Tensor[f32, 1, 2, 4, 5]",
            "weight": "Tensor[f32, 3, 2, 2, 2]",
            "bias": "Tensor[f32, 3]",
        },
        (
            _memory([1, 3, 4, 5]),
            _memory([1, 2, 4, 5]),
            _memory([3, 2, 2, 2]),
            _memory([3]),
            _symbol("TF"),
            _symbol("TC"),
            _symbol("TN"),
            _symbol("THO"),
            _symbol("TWO"),
        ),
    ),
    KernelDemoCase(
        "kernel/conv2d/inputs_dynamic_tile_dynamic.py",
        conv2d_inputs_dynamic_tile_dynamic_kernel,
        {
            "out": "Tensor[f32, B, F, HO, WO]",
            "input_tensor": "Tensor[f32, B, C, H, W]",
            "weight": "Tensor[f32, F, C, KH, KW]",
            "bias": "Tensor[f32, F]",
        },
        (
            _memory(["B", "F", "HO", "WO"]),
            _memory(["B", "C", "H", "W"]),
            _memory(["F", "C", "KH", "KW"]),
            _memory(["F"]),
            _symbol("SH"),
            _symbol("SW"),
            _symbol("DH"),
            _symbol("DW"),
            _symbol("PT"),
            _symbol("PB"),
            _symbol("PL"),
            _symbol("PR"),
            _symbol("TF"),
            _symbol("TC"),
            _symbol("TN"),
            _symbol("THO"),
            _symbol("TWO"),
        ),
    ),
)

FLASH_ATTENTION_DEMO_CASES = (
    KernelDemoCase(
        "kernel/flash_attention/inputs_static_tile_static.py",
        flash_attention_inputs_static_tile_static_kernel,
        {
            "out": "Tensor[f32, 1, 2, 4, 3]",
            "q": "Tensor[f32, 1, 2, 4, 3]",
            "k": "Tensor[f32, 1, 2, 4, 3]",
            "v": "Tensor[f32, 1, 2, 4, 3]",
        },
        (_memory([1, 2, 4, 3]), _memory([1, 2, 4, 3]), _memory([1, 2, 4, 3]), _memory([1, 2, 4, 3])),
    ),
    KernelDemoCase(
        "kernel/flash_attention/inputs_static_tile_dynamic.py",
        flash_attention_inputs_static_tile_dynamic_kernel,
        {
            "out": "Tensor[f32, 1, 2, 4, 3]",
            "q": "Tensor[f32, 1, 2, 4, 3]",
            "k": "Tensor[f32, 1, 2, 4, 3]",
            "v": "Tensor[f32, 1, 2, 4, 3]",
        },
        (_memory([1, 2, 4, 3]), _memory([1, 2, 4, 3]), _memory([1, 2, 4, 3]), _memory([1, 2, 4, 3]), _symbol("BR"), _symbol("BC")),
    ),
    KernelDemoCase(
        "kernel/flash_attention/inputs_dynamic_tile_dynamic.py",
        flash_attention_inputs_dynamic_tile_dynamic_kernel,
        {
            "out": "Tensor[f32, B, H, SL, D]",
            "q": "Tensor[f32, B, H, SL, D]",
            "k": "Tensor[f32, B, H, SL, D]",
            "v": "Tensor[f32, B, H, SL, D]",
        },
        (_memory(["B", "H", "SL", "D"]), _memory(["B", "H", "SL", "D"]), _memory(["B", "H", "SL", "D"]), _memory(["B", "H", "SL", "D"]), _symbol("BR"), _symbol("BC")),
    ),
)


def test_cuda_sm86_demo_sources_are_lowered_ir_specific() -> None:
    """验证真实 demo lowered IR 会影响 CUDA SourceBundle。

    功能说明:
    - 通过 3 类现有 demo 公开入口生成 CUDA source。
    - 锁定 matmul / conv2d / flash_attention 不再共享固定三合一万能 dispatcher。

    使用示例:
    - pytest -q test/cuda/test_cuda_sm86_kernel_demos_runtime.py -m cuda -k sources_are_lowered
    """

    matmul_source = _emit_cuda_demo_source(MATMUL_DEMO_CASES[0])
    conv2d_source = _emit_cuda_demo_source(CONV2D_DEMO_CASES[0])
    flash_source = _emit_cuda_demo_source(FLASH_ATTENTION_DEMO_CASES[0])

    assert 'kg_cuda_sm86_selected_kernel_kind = "matmul"' in matmul_source
    assert 'kg_cuda_sm86_selected_kernel_kind = "conv2d"' in conv2d_source
    assert 'kg_cuda_sm86_selected_kernel_kind = "flash_attention"' in flash_source
    assert "kg_cuda_sm86_generated_matmul_kernel" in matmul_source
    assert "kg_cuda_sm86_conv2d_f32_kernel" not in matmul_source
    assert "kg_cuda_sm86_conv2d_f32_kernel" in conv2d_source
    assert "kg_cuda_sm86_flash_attention_f32_kernel" in flash_source
    assert "mma.sync.aligned.m16n8k8" in matmul_source
    assert matmul_source != conv2d_source
    assert matmul_source != flash_source
    assert conv2d_source != flash_source


@pytest.mark.parametrize("case", MATMUL_DEMO_CASES, ids=[item.path for item in MATMUL_DEMO_CASES])
def test_cuda_sm86_matmul_demo_runtime_cases(case: KernelDemoCase) -> None:
    """验证 3 个 matmul demo 公开入口的 CUDA runtime 路径。

    功能说明:
    - 每个 case 均从真实 demo kernel 函数走 CUDA pipeline / emit / compile。
    - 每个 case 同时覆盖 absent bias 与 present bias。

    使用示例:
    - pytest -q test/cuda/test_cuda_sm86_kernel_demos_runtime.py -m cuda -k matmul
    """

    _require_cuda_environment()
    numpy = pytest.importorskip("numpy")
    compiled_kernel = _compile_cuda_demo_kernel(case)
    try:
        lhs = numpy.arange(6, dtype=numpy.float32).reshape(2, 3)
        rhs = numpy.arange(12, dtype=numpy.float32).reshape(3, 4)
        bias = numpy.arange(4, dtype=numpy.float32)
        absent_out = numpy.zeros((2, 4), dtype=numpy.float32)
        present_out = numpy.zeros((2, 4), dtype=numpy.float32)
        absent_result = compiled_kernel.execute(args=(absent_out, lhs, rhs, None, 2, 2, 2))
        present_result = compiled_kernel.execute(args=(present_out, lhs, rhs, bias, 2, 2, 2))
        assert case.path.startswith("kernel/matmul/")
        assert absent_result.ok
        assert present_result.ok
        numpy.testing.assert_allclose(absent_out, lhs @ rhs, rtol=1e-5, atol=1e-5)
        numpy.testing.assert_allclose(present_out, lhs @ rhs + bias[None, :], rtol=1e-5, atol=1e-5)
    finally:
        compiled_kernel.close()


@pytest.mark.parametrize("case", CONV2D_DEMO_CASES, ids=[item.path for item in CONV2D_DEMO_CASES])
def test_cuda_sm86_conv2d_demo_runtime_cases(case: KernelDemoCase) -> None:
    """验证 3 个 conv2d demo 公开入口的 CUDA runtime 路径。

    功能说明:
    - 每个 case 均从真实 demo kernel 函数走 CUDA pipeline / emit / compile。
    - 每个 case 同时覆盖 absent bias 与 present bias。

    使用示例:
    - pytest -q test/cuda/test_cuda_sm86_kernel_demos_runtime.py -m cuda -k conv2d
    """

    _require_cuda_environment()
    numpy = pytest.importorskip("numpy")
    compiled_kernel = _compile_cuda_demo_kernel(case)
    try:
        stride = (1, 1)
        dilation = (1, 1)
        padding = (1, 0, 1, 0)
        input_tensor = numpy.arange(1 * 2 * 4 * 5, dtype=numpy.float32).reshape(1, 2, 4, 5)
        weight = numpy.arange(3 * 2 * 2 * 2, dtype=numpy.float32).reshape(3, 2, 2, 2) / numpy.float32(7.0)
        bias = numpy.arange(3, dtype=numpy.float32)
        expected_absent = _conv2d_reference(input_tensor, weight, None, stride, dilation, padding)
        expected_present = _conv2d_reference(input_tensor, weight, bias, stride, dilation, padding)
        absent_out = numpy.zeros_like(expected_absent)
        present_out = numpy.zeros_like(expected_present)
        conv_scalars = (*stride, *dilation, *padding, 1, 1, 1, 1, 1)
        absent_result = compiled_kernel.execute(args=(absent_out, input_tensor, weight, None, *conv_scalars))
        present_result = compiled_kernel.execute(args=(present_out, input_tensor, weight, bias, *conv_scalars))
        assert case.path.startswith("kernel/conv2d/")
        assert absent_result.ok
        assert present_result.ok
        numpy.testing.assert_allclose(absent_out, expected_absent, rtol=1e-5, atol=1e-5)
        numpy.testing.assert_allclose(present_out, expected_present, rtol=1e-5, atol=1e-5)
    finally:
        compiled_kernel.close()


@pytest.mark.parametrize("case", FLASH_ATTENTION_DEMO_CASES, ids=[item.path for item in FLASH_ATTENTION_DEMO_CASES])
def test_cuda_sm86_flash_attention_demo_runtime_cases(case: KernelDemoCase) -> None:
    """验证 3 个 Flash Attention demo 公开入口的 CUDA runtime 路径。

    功能说明:
    - 每个 case 均从真实 demo kernel 函数走 CUDA pipeline / emit / compile。
    - runtime tile 参数作为公开 int slots 传入但不改变当前 generated source 的结果语义。

    使用示例:
    - pytest -q test/cuda/test_cuda_sm86_kernel_demos_runtime.py -m cuda -k flash_attention
    """

    _require_cuda_environment()
    numpy = pytest.importorskip("numpy")
    compiled_kernel = _compile_cuda_demo_kernel(case)
    try:
        rng = numpy.random.default_rng(2026052901)
        q_value = rng.normal(size=(1, 2, 4, 3)).astype(numpy.float32)
        k_value = rng.normal(size=(1, 2, 4, 3)).astype(numpy.float32)
        v_value = rng.normal(size=(1, 2, 4, 3)).astype(numpy.float32)
        out = numpy.zeros_like(q_value)
        expected = _softmax_attention_reference(q_value, k_value, v_value)
        result = compiled_kernel.execute(args=(out, q_value, k_value, v_value, 2, 2))
        assert case.path.startswith("kernel/flash_attention/")
        assert result.ok
        numpy.testing.assert_allclose(out, expected, rtol=1e-4, atol=1e-4)
    finally:
        compiled_kernel.close()
