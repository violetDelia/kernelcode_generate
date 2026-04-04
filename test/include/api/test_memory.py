"""API Memory compile tests.

创建者: 小李飞刀
最后一次更改: 小李飞刀

功能说明:
- 通过编译并运行 C++ 片段验证 include/api/Memory.h 的 Memory 视图声明，
  并使用 include/npu_demo/Memory.h 提供实现。

覆盖率信息:
- 当前覆盖率: `N/A`。该链路为 C++ 头文件，按规则豁免 `pytest-cov` 覆盖率统计。
- 达标判定: C++ 头文件实现按规则豁免 `95%` 覆盖率达标线。
- 当前覆盖基线: `API-MEMORY-001`。

覆盖率命令:
- `pytest -q test/include/api/test_memory.py`
- `N/A`（C++ 头文件实现，按当前规则豁免 `pytest-cov` 覆盖率统计）

使用示例:
- pytest -q test/include/api/test_memory.py

关联文件:
- 功能实现: include/npu_demo/Memory.h
- Spec 文档: spec/include/api/Memory.md
- 测试文件: test/include/api/test_memory.py
"""

from __future__ import annotations

import subprocess
import tempfile
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]


def _compile_and_run(source: str) -> None:
    """编译并运行 C++ 测试片段。

    创建者: 小李飞刀
    最后一次更改: 小李飞刀

    功能说明:
    - 使用 g++ 编译临时源码并执行生成的程序。

    使用示例:
    - _compile_and_run("int main() { return 0; }")

    关联文件:
    - spec: spec/include/api/Memory.md
    - test: test/include/api/test_memory.py
    - 功能实现: test/include/api/test_memory.py
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


# API-MEMORY-001
# 创建者: 小李飞刀
# 最后一次更改: 小李飞刀
# 最近一次运行测试时间: 2026-04-05 03:47:00 +0800
# 最近一次运行成功时间: 2026-04-05 03:47:00 +0800
# 测试目的: 验证 Memory API 声明可配合 npu_demo 实现编译运行，基础访问语义符合规范。
# 对应功能实现文件路径: include/npu_demo/Memory.h
# 对应 spec 文件路径: spec/include/api/Memory.md
# 对应测试文件路径: test/include/api/test_memory.py
def test_api_memory_compile_and_basic_usage() -> None:
    source = r"""
#include "include/api/Memory.h"
#include "include/npu_demo/Memory.h"

static int fail(int code) {
    return code;
}

int main() {
    int data[6] = {0, 1, 2, 3, 4, 5};
    long long shape[2] = {2, 3};
    long long stride[2] = {0, 0};
    build_contiguous_stride(shape, 2, stride);

    Memory<int> mem(data, shape, stride, 2, MemoryFormat::CLast, MemorySpace::SM);
    if (mem.rank() != 2) {
        return fail(1);
    }
    if (mem.get_shape(0) != 2 || mem.get_shape(1) != 3) {
        return fail(2);
    }
    if (mem.get_stride(0) != 3 || mem.get_stride(1) != 1) {
        return fail(3);
    }
    if (!mem.is_contiguous()) {
        return fail(4);
    }
    if (mem.element_count() != 6) {
        return fail(5);
    }
    long long index[2] = {1, 2};
    if (mem.linear_offset(index) != 5) {
        return fail(6);
    }
    if (mem.at(index) != 5) {
        return fail(7);
    }
    mem.at(index) = 9;
    if (data[5] != 9) {
        return fail(8);
    }
    if (mem.format() != MemoryFormat::CLast) {
        return fail(9);
    }
    if (mem.space() != MemorySpace::SM) {
        return fail(10);
    }
    Memory<int> mem2(data, shape, 2);
    if (!mem2.is_contiguous()) {
        return fail(11);
    }
    return 0;
}
"""
    _compile_and_run(source)
