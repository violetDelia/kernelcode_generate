"""CPU Memory compile tests.

创建者: 神秘人
最后一次更改: 神秘人

功能说明:
- 通过编译并运行 C++ 片段验证 include/cpu/Memory.h 的公开接口与核心语义。

使用示例:
- pytest -q test/include/cpu/test_memory.py

关联文件:
- 功能实现: include/cpu/Memory.h
- Spec 文档: spec/include/cpu/Memory.md
- 测试文件: test/include/cpu/test_memory.py
"""

from __future__ import annotations

import subprocess
import sys
import tempfile
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]


def _compile_and_run(source: str) -> None:
    """编译并运行 C++ 测试片段。

    创建者: 神秘人
    最后一次更改: 神秘人

    功能说明:
    - 使用 g++ 编译临时源码并执行生成的程序。

    使用示例:
    - _compile_and_run("int main() { return 0; }")

    关联文件:
    - spec: spec/include/cpu/Memory.md
    - test: test/include/cpu/test_memory.py
    - 功能实现: test/include/cpu/test_memory.py
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        source_path = Path(tmpdir) / "memory_test.cpp"
        binary_path = Path(tmpdir) / "memory_test"
        source_path.write_text(source, encoding="utf-8")

        compile_result = subprocess.run(
            [
                "g++",
                "-std=c++17",
                "-I",
                str(REPO_ROOT),
                str(source_path),
                "-o",
                str(binary_path),
            ],
            check=False,
            capture_output=True,
            text=True,
        )
        if compile_result.returncode != 0:
            raise AssertionError(
                "g++ compile failed:\n"
                f"stdout:\n{compile_result.stdout}\n"
                f"stderr:\n{compile_result.stderr}"
            )

        run_result = subprocess.run(
            [str(binary_path)],
            check=False,
            capture_output=True,
            text=True,
        )
        if run_result.returncode != 0:
            raise AssertionError(
                "compiled program failed:\n"
                f"stdout:\n{run_result.stdout}\n"
                f"stderr:\n{run_result.stderr}"
            )


# CPU-MEM-001 / CPU-MEM-002 / CPU-MEM-003 / CPU-MEM-004 / CPU-MEM-005
# 创建者: 神秘人
# 最后一次更改: 神秘人
# 最近一次运行测试时间: 2026-03-19 00:00:00 +0800
# 最近一次运行成功时间: 2026-03-19 00:00:00 +0800
# 功能说明: 验证显式 stride、自动连续 stride、element_count、linear_offset、at 与 is_contiguous 语义。
# 使用示例: pytest -q test/include/cpu/test_memory.py -k test_cpu_memory_header_compiles_and_runs
# 对应功能实现文件路径: include/cpu/Memory.h
# 对应 spec 文件路径: spec/include/cpu/Memory.md
# 对应测试文件路径: test/include/cpu/test_memory.py
def test_cpu_memory_header_compiles_and_runs() -> None:
    source = r"""
#include "include/cpu/Memory.h"

static int fail(int code) {
    return code;
}

int main() {
    int data[6] = {0, 1, 2, 3, 4, 5};
    long long shape[2] = {2, 3};
    long long explicit_stride[2] = {3, 1};

    cpu::Memory<int, 2> explicit_mem(
        data,
        shape,
        explicit_stride,
        cpu::MemoryFormat::CLast,
        cpu::MemorySpace::SM);

    if (explicit_mem.rank() != 2) {
        return fail(1);
    }
    if (explicit_mem.shape()[0] != 2 || explicit_mem.shape()[1] != 3) {
        return fail(2);
    }
    if (explicit_mem.stride()[0] != 3 || explicit_mem.stride()[1] != 1) {
        return fail(3);
    }
    if (explicit_mem.format() != cpu::MemoryFormat::CLast) {
        return fail(4);
    }
    if (explicit_mem.space() != cpu::MemorySpace::SM) {
        return fail(5);
    }
    if (explicit_mem.element_count() != 6) {
        return fail(6);
    }
    if (!explicit_mem.is_contiguous()) {
        return fail(7);
    }

    long long index_a[2] = {1, 2};
    if (explicit_mem.linear_offset(index_a) != 5) {
        return fail(8);
    }
    if (explicit_mem.at(index_a) != 5) {
        return fail(9);
    }

    long long padded_stride[2] = {4, 1};
    cpu::Memory<int, 2> padded_mem(data, shape, padded_stride);
    if (padded_mem.is_contiguous()) {
        return fail(10);
    }
    long long index_b[2] = {1, 1};
    if (padded_mem.linear_offset(index_b) != 5) {
        return fail(11);
    }

    cpu::Memory<int, 2> auto_mem(data, shape);
    if (auto_mem.stride()[0] != 3 || auto_mem.stride()[1] != 1) {
        return fail(12);
    }
    if (!auto_mem.is_contiguous()) {
        return fail(13);
    }
    auto_mem.at(index_b) = 4;
    if (data[4] != 4) {
        return fail(14);
    }

    return 0;
}
"""
    _compile_and_run(source)


# CPU-MEM-005
# 创建者: 神秘人
# 最后一次更改: 神秘人
# 最近一次运行测试时间: 2026-03-19 00:00:00 +0800
# 最近一次运行成功时间: 2026-03-19 00:00:00 +0800
# 功能说明: 验证头文件自身不依赖标准库头文件即可被最小程序编译。
# 使用示例: pytest -q test/include/cpu/test_memory.py -k test_cpu_memory_header_without_std_headers
# 对应功能实现文件路径: include/cpu/Memory.h
# 对应 spec 文件路径: spec/include/cpu/Memory.md
# 对应测试文件路径: test/include/cpu/test_memory.py
def test_cpu_memory_header_without_std_headers() -> None:
    source = r"""
#include "include/cpu/Memory.h"

int main() {
    float data[4] = {1.0f, 2.0f, 3.0f, 4.0f};
    long long shape[2] = {2, 2};
    cpu::Memory<float, 2> mem(data, shape, cpu::MemoryFormat::Norm, cpu::MemorySpace::GM);
    return mem.element_count() == 4 ? 0 : 1;
}
"""
    _compile_and_run(source)
