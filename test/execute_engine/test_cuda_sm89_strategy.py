"""CUDA SM89 execute_engine strategy tests.


功能说明:
- 覆盖 `ExecutionEngine(target="cuda_sm89")` 的 compile strategy 注册、SourceBundle 写盘和 nvcc 命令合同。
- 使用测试 fake nvcc，不依赖本机 CUDA toolkit；真实 CUDA runtime 由 `test/cuda` 下 `-m cuda` 用例覆盖。

使用示例:
- pytest -q test/execute_engine/test_cuda_sm89_strategy.py

关联文件:
- 功能实现: kernel_gen/execute_engine/builtin_strategy/__init__.py
- 功能实现: kernel_gen/execute_engine/builtin_strategy/cuda_sm89.py
- 功能实现: kernel_gen/execute_engine/compiler.py
- Spec 文档: spec/execute_engine/execute_engine_target.md
- 测试文件: test/execute_engine/test_cuda_sm89_strategy.py
"""

from __future__ import annotations

from pathlib import Path
import sys

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from kernel_gen.core.error import KernelCodeError
from kernel_gen.execute_engine import CompiledKernel, ExecutionEngine


def _write_fake_nvcc(path: Path, log_path: Path) -> Path:
    """写入测试 fake nvcc。

    功能说明:
    - 记录传入参数到 `log_path`。
    - 解析 `-o <path>` 并创建对应输出文件，模拟成功编译。

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


def test_cuda_sm89_compile_strategy_registered() -> None:
    """验证 cuda_sm89 compile strategy 已注册。

    功能说明:
    - 通过公开 `ExecutionEngine.compile(...)` 触发 CUDA strategy。
    - 缺失 strategy 会报 `target_header_mismatch`，已注册但编译器缺失会收敛到 `compile_failed`。

    使用示例:
    - pytest -q test/execute_engine/test_cuda_sm89_strategy.py -k registered
    """

    source = (
        '#include "include/cuda_sm89/cuda_sm89.cuh"\n'
        'extern "C" int kg_execute_entry(cuda_sm89::ArgSlot* slots, unsigned long long count) {\n'
        "  (void)slots;\n"
        "  (void)count;\n"
        "  return 0;\n"
        "}\n"
    )

    with pytest.raises(KernelCodeError) as exc:
        ExecutionEngine(target="cuda_sm89", compiler="/not/found/nvcc").compile(source=source, function="cuda_matmul")

    assert exc.value.failure_phrase == "compile_failed"
    assert "compiler not found" in str(exc.value)


def test_cuda_sm89_compile_writes_source_bundle_and_nvcc_command(tmp_path: Path) -> None:
    """验证 CUDA SourceBundle 写盘与 nvcc 命令。

    功能说明:
    - 使用公开 `ExecutionEngine.compile(...)` 编译 SourceBundle aggregate。
    - fake nvcc 证明主 `.cu` 被选择，默认 `-arch=sm_89 -shared -Xcompiler -fPIC` 被追加。

    使用示例:
    - pytest -q test/execute_engine/test_cuda_sm89_strategy.py -k source_bundle
    """

    log_path = tmp_path / "nvcc_args.txt"
    fake_nvcc = _write_fake_nvcc(tmp_path / "nvcc", log_path)
    source = (
        "// __KG_BUNDLE_FILE__:kernel.cu\n"
        '#include "include/cuda_sm89/cuda_sm89.cuh"\n'
        'extern "C" int kg_execute_entry(cuda_sm89::ArgSlot* slots, unsigned long long count) {\n'
        "  (void)slots;\n"
        "  (void)count;\n"
        "  return 0;\n"
        "}\n"
        "// __KG_BUNDLE_FILE__:include/cuda_sm89/generated_entry.cuh\n"
        "#pragma once\n"
    )

    kernel = ExecutionEngine(target="cuda_sm89", compiler=str(fake_nvcc)).compile(source=source, function="cuda_matmul")
    try:
        source_root = Path(kernel.soname_path).parent / "source"
        assert kernel.target == "cuda_sm89"
        assert Path(kernel.soname_path).is_file()
        assert (source_root / "source.cpp").read_text(encoding="utf-8") == source
        assert (source_root / "kernel.cu").is_file()
        assert (source_root / "include" / "cuda_sm89" / "generated_entry.cuh").is_file()
        assert "launch_matmul_entry" not in (source_root / "kernel.cu").read_text(encoding="utf-8")
        args_text = log_path.read_text(encoding="utf-8")
        assert "-std=c++17" in args_text
        assert "-arch=sm_89" in args_text
        assert "-shared" in args_text
        assert "-Xcompiler" in args_text
        assert "-fPIC" in args_text
        assert "kernel.cu" in args_text
        assert "cuda-sm89 compile" in kernel.compile_stdout
    finally:
        kernel.close()


def test_cuda_sm89_compile_rejects_target_header_mismatch(tmp_path: Path) -> None:
    """验证 CUDA target 不接受 npu_demo include family。

    功能说明:
    - 通过公开 compile 入口传入错误 include family。
    - 锁定 failure phrase 仍复用 `target_header_mismatch`。

    使用示例:
    - pytest -q test/execute_engine/test_cuda_sm89_strategy.py -k header_mismatch
    """

    fake_nvcc = _write_fake_nvcc(tmp_path / "nvcc", tmp_path / "args.txt")
    source = '#include "include/npu_demo/npu_demo.h"\nvoid bad() {}\n'

    with pytest.raises(KernelCodeError) as exc:
        ExecutionEngine(target="cuda_sm89", compiler=str(fake_nvcc)).compile(source=source, function="bad")

    assert exc.value.failure_phrase == "target_header_mismatch"


def test_cuda_sm89_execute_rejects_non_none_stream(tmp_path: Path) -> None:
    """验证 CUDA execute stream 首版仍不支持。

    功能说明:
    - 直接构造公开 `CompiledKernel` 描述对象，不触发真实 CUDA 编译。
    - `stream` 非 `None` 必须稳定失败为 `stream_not_supported`。

    使用示例:
    - pytest -q test/execute_engine/test_cuda_sm89_strategy.py -k non_none_stream
    """

    soname = tmp_path / "libkernel.so"
    soname.write_text("", encoding="utf-8")
    kernel = CompiledKernel(target="cuda_sm89", soname_path=str(soname), function="cuda_matmul", entry_point="kg_execute_entry")

    with pytest.raises(KernelCodeError) as exc:
        kernel.execute(args=(), stream="stream-token")  # type: ignore[arg-type]

    assert exc.value.failure_phrase == "stream_not_supported"
    assert "cuda_sm89 does not support non-None stream" in str(exc.value)
