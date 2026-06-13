"""CUDA SM86 launch mapping tests.

功能说明:
    - 通过公开 emit 和 compile 入口验证 generated CUDA launch wrapper 形态。
- 锁定 `cuda_sm86` 编译命令只使用显式 SM86 flag，不根据设备现场切换其它 SM。

使用示例:
- pytest -q test/dsl/gen_kernel/emit/test_cuda_sm86_launch_mapping.py

关联文件:
- 功能实现: kernel_gen/dsl/gen_kernel/emit/cuda_sm86/source_bundle.py
- 功能实现: kernel_gen/execute_engine/builtin_strategy/cuda_sm86.py
- 测试文件: test/dsl/gen_kernel/emit/test_cuda_sm86_launch_mapping.py
"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
import sys

REPO_ROOT = Path(__file__).resolve().parents[4]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from kernel.conv2d.inputs_static_tile_static import conv2d_inputs_static_tile_static_kernel
from kernel.flash_attention.inputs_static_tile_static import flash_attention_inputs_static_tile_static_kernel
from kernel.matmul.inputs_static_tile_static import matmul_inputs_static_tile_static_kernel
from kernel_gen.core.config import reset_config, set_target
from kernel_gen.dsl.ast.mlir_gen import mlir_gen
from kernel_gen.dsl.gen_kernel import EmitCContext, emit_c
from kernel_gen.execute_engine import ExecutionEngine
from kernel_gen.pipeline import build_cuda_sm86_lowering_pipeline
from kernel_gen.symbol_variable.memory import Memory
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
        if "cuda_sm86::launch<" not in source:
            raise AssertionError("missing CUDA SM86 launch wrapper call")
        return source
    finally:
        kernel_fn.__annotations__.clear()
        kernel_fn.__annotations__.update(original_annotations)
        reset_config()


def _write_fake_nvcc(path: Path, log_path: Path) -> Path:
    """写入测试 fake nvcc。

    功能说明:
    - 记录传入参数到 `log_path`。
    - 解析 `-o <path>` 并创建对应输出文件，模拟成功编译。
    - 只服务公开 `ExecutionEngine(target="cuda_sm86")` 编译命令断言。

    使用示例:
    - fake_nvcc = _write_fake_nvcc(tmp_path / "nvcc", tmp_path / "args.txt")
    """

    script = f"""#!/usr/bin/env bash
printf '%s\\n' "$@" > "{log_path}"
out=""
prev=""
for arg in "$@"; do
  if [ "$prev" = "-o" ]; then
    out="$arg"
    break
  fi
  prev="$arg"
done
if [ -z "$out" ]; then
  exit 2
fi
: > "$out"
exit 0
"""
    path.write_text(script, encoding="utf-8")
    path.chmod(0o755)
    return path


def test_cuda_sm86_generated_launches_match_demo_compute_ops() -> None:
    """验证 generated launch 形态随 demo compute op 变化。

    功能说明:
    - 从 matmul、conv2d 和 flash_attention 公开 demo final IR 生成 source。
    - 锁定对应 generated `__global__` kernel、launch wrapper、device context 和 `arch.launch` marker。

    使用示例:
    - pytest -q test/dsl/gen_kernel/emit/test_cuda_sm86_launch_mapping.py -k generated_launches
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

    assert "// kg.cuda.ir.op: arch.launch" in matmul_source
    assert "kg_cuda_sm86_generated_kernel_" in matmul_source
    assert "kg_cuda_sm86_device_body_" in matmul_source
    assert "cuda_sm86::KernelContext device_ctx" in matmul_source
    assert "cuda_sm86::launch<1, 256, 1, 49152, kg_cuda_sm86_generated_kernel_" in matmul_source
    assert "cuda_sm86::block_id()" in matmul_source
    assert "// kg.cuda.ir.op: arch.launch" in conv2d_source
    assert "kg_cuda_sm86_generated_kernel_" in conv2d_source
    assert "cuda_sm86::launch<1, 256, 1, 49152, kg_cuda_sm86_generated_kernel_" in conv2d_source
    assert "cuda_sm86::img2col2d<" in conv2d_source
    assert "// kg.cuda.ir.op: arch.launch" in flash_source
    assert "kg_cuda_sm86_generated_kernel_" in flash_source
    assert "cuda_sm86::launch<1, 256, 1, 49152, kg_cuda_sm86_generated_kernel_" in flash_source
    assert "cuda_sm86::reduce_" in flash_source
    assert "cuda_sm86::exp<" in flash_source


def test_cuda_sm86_compile_strategy_keeps_explicit_sm86_flag(tmp_path: Path) -> None:
    """验证编译策略固定使用显式 SM86 flag。

    功能说明:
    - 使用 fake nvcc 通过公开 `ExecutionEngine(target="cuda_sm86")` 编译 SourceBundle。
    - 锁定命令包含 `-arch=sm_86`，且不会根据本机设备现场替换为其它 SM。

    使用示例:
    - pytest -q test/dsl/gen_kernel/emit/test_cuda_sm86_launch_mapping.py -k explicit_sm86_flag
    """

    log_path = tmp_path / "nvcc_args.txt"
    fake_nvcc = _write_fake_nvcc(tmp_path / "nvcc", log_path)
    source = (
        "// __KG_BUNDLE_FILE__:kernel.cu\n"
        '#include "include/cuda_sm86/cuda_sm86.cuh"\n'
        'extern "C" int kg_execute_entry(cuda_sm86::ArgSlot* slots, unsigned long long count) {\n'
        "  (void)slots;\n"
        "  (void)count;\n"
        "  return 0;\n"
        "}\n"
        "// __KG_BUNDLE_FILE__:include/cuda_sm86/generated_entry.cuh\n"
        "#pragma once\n"
    )

    kernel = ExecutionEngine(target="cuda_sm86", compiler=str(fake_nvcc)).compile(source=source, function="cuda_sm86_probe")
    try:
        args_text = log_path.read_text(encoding="utf-8")
        assert "-arch=sm_86" in args_text
        assert "-arch=sm_89" not in args_text
        assert "-arch=sm_80" not in args_text
        assert "-arch=sm_90" not in args_text
        assert "kernel.cu" in args_text
        assert kernel.target == "cuda_sm86"
    finally:
        kernel.close()
