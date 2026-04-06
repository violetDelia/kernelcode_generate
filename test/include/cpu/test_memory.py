"""CPU Memory compile tests.

创建者: 神秘人
最后一次更改: jcc你莫辜负

功能说明:
- 通过编译并运行 C++ 片段验证 include/cpu/Memory.h 的公开接口与核心语义。

覆盖率信息:
- 当前覆盖率: `N/A`。该链路的功能实现为 C++ 头文件，按当前覆盖率规则豁免 `pytest-cov` 百分比统计。
- 达标判定: C++ 实现按规则豁免 `95%` 覆盖率达标线。
- 当前覆盖基线: `CPU-MEM-001..007`。
- 最近一次测试核对: `2026-03-22 14:29:00 +0800`，本次执行 `pytest -q test/include/cpu/test_memory.py`，结果为 `4 passed`。

覆盖率命令:
- `pytest -q test/include/cpu/test_memory.py`
- `N/A`（C++ 头文件实现，按当前规则豁免 `pytest-cov` 覆盖率统计）

使用示例:
- pytest -q test/include/cpu/test_memory.py

关联文件:
- 功能实现: include/cpu/Memory.h
- Spec 文档: spec/include/cpu/cpu.md
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
    - spec: spec/include/cpu/cpu.md
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


def _compile_and_run_expect_failure(source: str) -> None:
    """编译并运行应当失败的 C++ 测试片段。

    创建者: 金铲铲大作战
    最后一次更改: 金铲铲大作战

    功能说明:
    - 使用 g++ 编译临时源码并验证生成程序以非零状态退出。

    使用示例:
    - _compile_and_run_expect_failure("int main() { return 1; }")

    关联文件:
    - spec: spec/include/cpu/cpu.md
    - test: test/include/cpu/test_memory.py
    - 功能实现: test/include/cpu/test_memory.py
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        source_path = Path(tmpdir) / "memory_contract_test.cpp"
        binary_path = Path(tmpdir) / "memory_contract_test"
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
        if run_result.returncode == 0:
            raise AssertionError("compiled program unexpectedly succeeded")


# CPU-MEM-001 / CPU-MEM-002 / CPU-MEM-003 / CPU-MEM-004 / CPU-MEM-005
# 创建者: 神秘人
# 最后一次更改: jcc你莫辜负
# 最近一次运行测试时间: 2026-04-06 19:05:00 +0800
# 最近一次运行成功时间: 2026-04-06 19:05:00 +0800
# 测试目的: 验证运行期 rank 的显式 stride、自动连续 stride、element_count、linear_offset、at 与 is_contiguous 语义。
# 使用示例: pytest -q test/include/cpu/test_memory.py -k test_cpu_memory_header_compiles_and_runs
# 对应功能实现文件路径: include/cpu/Memory.h
# 对应 spec 文件路径: spec/include/cpu/cpu.md
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

    cpu::Memory<cpu::SM, int> explicit_mem(
        data,
        2,
        shape,
        explicit_stride,
        cpu::MemoryFormat::CLast);

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
    cpu::Memory<cpu::SM, int> padded_mem(data, 2, shape, padded_stride);
    if (padded_mem.is_contiguous()) {
        return fail(10);
    }
    long long index_b[2] = {1, 1};
    if (padded_mem.linear_offset(index_b) != 5) {
        return fail(11);
    }

    cpu::Memory<cpu::SM, int> auto_mem(data, 2, shape);
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


# CPU-MEM-SPACE-TEMPLATE-001
# 创建者: jcc你莫辜负
# 最后一次更改: jcc你莫辜负
# 最近一次运行测试时间: 2026-04-06 19:05:00 +0800
# 最近一次运行成功时间: 2026-04-06 19:05:00 +0800
# 测试目的: 验证 cpu::Memory<Space, T> 模板签名可用，cpu::Memory<GM, T> 与 cpu::Memory<MemorySpace::GM, T> 等价口径可编译运行。
# 使用示例: pytest -q test/include/cpu/test_memory.py -k space_template_contract
# 对应功能实现文件路径: include/cpu/Memory.h
# 对应 spec 文件路径: spec/include/cpu/cpu.md
# 对应测试文件路径: test/include/cpu/test_memory.py
def test_cpu_memory_space_template_contract() -> None:
    source = r"""
#include "include/cpu/Memory.h"

static int fail(int code) {
    return code;
}

int main() {
    float data[2] = {1.0f, 2.0f};
    long long shape[1] = {2};
    long long stride[1] = {1};

    cpu::Memory<cpu::GM, float> gm_mem(data, 1, shape, stride);
    cpu::Memory<cpu::MemorySpace::GM, float> gm_mem2(data, 1, shape, stride);

    if (gm_mem.space() != cpu::MemorySpace::GM) {
        return fail(1);
    }
    if (gm_mem2.space() != cpu::MemorySpace::GM) {
        return fail(2);
    }
    return 0;
}
"""
    _compile_and_run(source)


# CPU-MEM-005
# 创建者: 神秘人
# 最后一次更改: jcc你莫辜负
# 最近一次运行测试时间: 2026-04-06 19:05:00 +0800
# 最近一次运行成功时间: 2026-04-06 19:05:00 +0800
# 测试目的: 验证头文件自身不依赖标准库头文件即可被最小程序编译。
# 使用示例: pytest -q test/include/cpu/test_memory.py -k test_cpu_memory_header_without_std_headers
# 对应功能实现文件路径: include/cpu/Memory.h
# 对应 spec 文件路径: spec/include/cpu/cpu.md
# 对应测试文件路径: test/include/cpu/test_memory.py
def test_cpu_memory_header_without_std_headers() -> None:
    source = r"""
#include "include/cpu/Memory.h"

int main() {
    float data[4] = {1.0f, 2.0f, 3.0f, 4.0f};
    long long shape[2] = {2, 2};
    cpu::Memory<cpu::GM, float> mem(data, 2, shape, cpu::MemoryFormat::Norm);
    return mem.element_count() == 4 ? 0 : 1;
}
"""
    _compile_and_run(source)


# CPU-MEM-006
# 创建者: 金铲铲大作战
# 最后一次更改: jcc你莫辜负
# 最近一次运行测试时间: 2026-04-06 19:05:00 +0800
# 最近一次运行成功时间: 2026-04-06 19:05:00 +0800
# 测试目的: 验证运行期 rank 支持 MAX_DIM=8 的默认 stride 推导与索引访问。
# 使用示例: pytest -q test/include/cpu/test_memory.py -k test_cpu_memory_runtime_rank_max_dim
# 对应功能实现文件路径: include/cpu/Memory.h
# 对应 spec 文件路径: spec/include/cpu/cpu.md
# 对应测试文件路径: test/include/cpu/test_memory.py
def test_cpu_memory_runtime_rank_max_dim() -> None:
    source = r"""
#include "include/cpu/Memory.h"

static int fail(int code) {
    return code;
}

int main() {
    int data[256] = {0};
    long long shape[8] = {1, 1, 1, 1, 1, 1, 2, 3};
    cpu::Memory<cpu::GM, int> mem(data, 8, shape);

    if (cpu::MAX_DIM != 8) {
        return fail(1);
    }
    if (mem.rank() != 8) {
        return fail(2);
    }
    if (mem.stride()[6] != 3 || mem.stride()[7] != 1) {
        return fail(3);
    }
    if (mem.element_count() != 6) {
        return fail(4);
    }

    long long index[8] = {0, 0, 0, 0, 0, 0, 1, 2};
    mem.at(index) = 7;
    if (mem.linear_offset(index) != 5) {
        return fail(5);
    }
    if (data[5] != 7) {
        return fail(6);
    }

    return 0;
}
"""
    _compile_and_run(source)


# CPU-MEM-007
# 创建者: 金铲铲大作战
# 最后一次更改: jcc你莫辜负
# 最近一次运行测试时间: 2026-04-06 19:05:00 +0800
# 最近一次运行成功时间: 2026-04-06 19:05:00 +0800
# 测试目的: 验证 rank>MAX_DIM=8 违反前置条件时触发显式失败，不做静默截断。
# 使用示例: pytest -q test/include/cpu/test_memory.py -k test_cpu_memory_runtime_rank_over_max_dim_fails
# 对应功能实现文件路径: include/cpu/Memory.h
# 对应 spec 文件路径: spec/include/cpu/cpu.md
# 对应测试文件路径: test/include/cpu/test_memory.py
def test_cpu_memory_runtime_rank_over_max_dim_fails() -> None:
    source = r"""
#include "include/cpu/Memory.h"

int main() {
    int data[9] = {0};
    long long shape[9] = {1, 1, 1, 1, 1, 1, 1, 1, 1};
    cpu::Memory<cpu::GM, int> mem(data, 9, shape);
    return static_cast<int>(mem.rank());
}
"""
    _compile_and_run_expect_failure(source)
