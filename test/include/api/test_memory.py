"""API Memory compile tests.


功能说明:
- 通过编译并运行 C++ 片段验证 include/api/Memory.h 的 `Memory` 视图声明，
  包括成员式 `view/reshape` 与按轴查询接口，并使用 include/npu_demo/Memory.h 提供实现。

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


def _compile_expect_failure(source: str) -> str:
    """编译并断言 C++ 片段失败，返回编译 stderr。


    功能说明:
    - 使用 g++ 编译临时源码，并验证其因公开 MemorySpace 合同违例而失败。

    使用示例:
    - stderr = _compile_expect_failure("int main() { return missing; }")

    关联文件:
    - spec: spec/include/api/Memory.md
    - test: test/include/api/test_memory.py
    - 功能实现: test/include/api/test_memory.py
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        source_path = Path(tmpdir) / "memory_test_fail.cpp"
        binary_path = Path(tmpdir) / "memory_test_fail"
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
        if compile_result.returncode == 0:
            raise AssertionError("expected g++ compile failure, but compile succeeded")
        return compile_result.stderr


# API-MEMORY-001
# 测试目的: 验证 Memory API 声明可配合 npu_demo 实现编译运行，基础访问语义符合规范。
# 对应功能实现文件路径: include/npu_demo/Memory.h
# 对应 spec 文件路径: spec/include/api/Memory.md
# 对应测试文件路径: test/include/api/test_memory.py
def test_api_memory_compile_and_basic_usage() -> None:
    source = r"""
#include "include/api/Memory.h"
#include "include/npu_demo/Memory.h"

#include <cstdint>

static int fail(int code) {
    return code;
}

int main() {
    int data[6] = {0, 1, 2, 3, 4, 5};
    long long shape[2] = {2, 3};
    long long stride[2] = {0, 0};
    npu_demo::build_contiguous_stride(shape, 2, stride);

    Memory<SM, int> mem(data, shape, stride, 2, MemoryFormat::CLast);
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
    if (mem.data() != data) {
        return fail(6);
    }
    if (mem.data()[5] != 5) {
        return fail(7);
    }
    mem.data()[5] = 9;
    if (data[5] != 9) {
        return fail(8);
    }
    if (mem.format() != MemoryFormat::CLast) {
        return fail(9);
    }
    if (mem.space() != MemorySpace::SM) {
        return fail(10);
    }
    Memory<GM, int> mem2(data, shape, 2);
    if (!mem2.is_contiguous()) {
        return fail(11);
    }
    return 0;
}
"""
    _compile_and_run(source)


# API-MEMORY-SPACE-TEMPLATE-001
# 测试目的: 验证 Memory<Space, T> 模板签名可用，Memory<GM, T> 与 Memory<MemorySpace::GM, T> 等价口径可编译运行。
# 使用示例: pytest -q test/include/api/test_memory.py -k space_template_contract
# 对应功能实现文件路径: include/api/Memory.h
# 对应 spec 文件路径: spec/include/api/Memory.md
# 对应测试文件路径: test/include/api/test_memory.py
def test_memory_space_template_contract() -> None:
    source = r"""
#include "include/api/Memory.h"
#include "include/npu_demo/Memory.h"

static int fail(int code) {
    return code;
}

int main() {
    float data[4] = {0.0f, 1.0f, 2.0f, 3.0f};
    long long shape[1] = {4};
    long long stride[1] = {1};

    Memory<GM, float> gm_mem(data, shape, stride, 1);
    Memory<MemorySpace::GM, float> gm_mem2(data, shape, stride, 1, MemoryFormat::Norm);
    Memory<TLM1, float> tlm1_mem(data, shape, stride, 1);
    Memory<TLM2, float> tlm2_mem(data, shape, stride, 1);
    Memory<TLM3, float> tlm3_mem(data, shape, stride, 1);

    if (gm_mem.space() != MemorySpace::GM) {
        return fail(1);
    }
    if (gm_mem2.space() != MemorySpace::GM) {
        return fail(2);
    }
    if (tlm1_mem.space() != MemorySpace::TLM1) {
        return fail(3);
    }
    if (tlm2_mem.space() != MemorySpace::TLM2) {
        return fail(4);
    }
    if (tlm3_mem.space() != MemorySpace::TLM3) {
        return fail(5);
    }
    return 0;
}
"""
    _compile_and_run(source)


# API-MEMORY-SPACE-TEMPLATE-002
# 测试目的: 验证公开 MemorySpace 已拒绝旧 TLM 成员，调用方不能再以 `MemorySpace::TLM` 作为模板参数。
# 使用示例: pytest -q test/include/api/test_memory.py -k test_memory_space_rejects_legacy_tlm_contract
# 对应功能实现文件路径: include/api/Memory.h
# 对应 spec 文件路径: spec/include/api/Memory.md
# 对应测试文件路径: test/include/api/test_memory.py
def test_memory_space_rejects_legacy_tlm_contract() -> None:
    stderr = _compile_expect_failure(
        r"""
#include "include/api/Memory.h"
#include "include/npu_demo/Memory.h"

int main() {
    float data[1] = {0.0f};
    long long shape[1] = {1};
    long long stride[1] = {1};
    Memory<MemorySpace::TLM, float> mem(data, shape, stride, 1);
    return mem.space() == MemorySpace::TLM ? 0 : 1;
}
"""
    )
    assert "TLM" in stderr


# API-MEMORY-002
# 测试目的: 验证成员式 `source.view<T>(...)` 与 `source.reshape(shape)` 已成为公共层稳定视图接口，且多维 view stride 由源 physical stride 与 logical stride 相乘得到。
# 使用示例: pytest -q test/include/api/test_memory.py -k test_memory_member_view_and_reshape_contract
# 对应功能实现文件路径: include/npu_demo/Memory.h
# 对应 spec 文件路径: spec/include/api/Memory.md
# 对应测试文件路径: test/include/api/test_memory.py
def test_memory_member_view_and_reshape_contract() -> None:
    source = r"""
#include <stdexcept>
#include <string>

#include "include/api/Memory.h"
#include "include/npu_demo/Memory.h"

static int fail(int code) {
    return code;
}

static bool contains(const std::string& value, const char* needle) {
    return value.find(needle) != std::string::npos;
}

int main() {
    float data[6] = {0, 1, 2, 3, 4, 5};
    long long shape[2] = {2, 3};
    long long stride[2] = {3, 1};
    Memory<GM, float> source(data, shape, stride, 2, MemoryFormat::Norm);

    long long offset_buf[2] = {1, 1};
    long long size_buf[2] = {1, 2};
    long long stride_buf[2] = {1, 1};
    Vector offset(offset_buf, 2);
    Vector size(size_buf, 2);
    Vector view_stride(stride_buf, 2);

    Memory<GM, float> tile = source.view<float>(offset, size, view_stride);
    if (tile.rank() != 2) {
        return fail(1);
    }
    if (tile.get_shape(0) != 1 || tile.get_shape(1) != 2) {
        return fail(2);
    }
    if (tile.get_stride(0) != 3 || tile.get_stride(1) != 1) {
        return fail(3);
    }
    if (tile.data() != source.data() + 4) {
        return fail(4);
    }

    int8_t byte_data[64] = {};
    long long byte_shape[1] = {64};
    long long byte_stride[1] = {1};
    Memory<GM, int8_t> byte_source(byte_data, byte_shape, byte_stride, 1, MemoryFormat::Norm);
    long long typed_offset_buf[1] = {1};
    long long typed_size_buf[1] = {2};
    long long typed_stride_buf[1] = {1};
    Vector typed_offset(typed_offset_buf, 1);
    Vector typed_size(typed_size_buf, 1);
    Vector typed_stride(typed_stride_buf, 1);
    Memory<GM, float> typed = byte_source.view<float>(typed_offset, typed_size, typed_stride);
    if (typed.rank() != 1 || typed.get_shape(0) != 2 || typed.get_stride(0) != 1) {
        return fail(5);
    }
    if (typed.data() != reinterpret_cast<float*>(byte_source.data()) + 1) {
        return fail(6);
    }
    long long typed_bad_size_buf[1] = {17};
    Vector typed_bad_size(typed_bad_size_buf, 1);
    try {
        auto bad = byte_source.view<float>(typed_offset, typed_bad_size, typed_stride);
        (void)bad;
        return fail(20);
    } catch (const std::runtime_error& err) {
        if (!contains(err.what(), "out_of_bounds")) {
            return fail(21);
        }
    }

    long long reshape_buf[2] = {2, 3};
    Vector reshape_shape(reshape_buf, 2);
    Memory<GM, float> reshaped = source.reshape(reshape_shape);
    if (reshaped.rank() != 2) {
        return fail(7);
    }
    if (reshaped.get_shape(0) != 2 || reshaped.get_shape(1) != 3) {
        return fail(8);
    }
    if (reshaped.get_stride(0) != 3 || reshaped.get_stride(1) != 1) {
        return fail(9);
    }
    if (reshaped.data() != source.data()) {
        return fail(10);
    }
    return 0;
}
"""
    _compile_and_run(source)


# API-MEMORY-003
# 测试目的: 验证旧自由函数 `reshape(source, shape)` 已退出公共层稳定口径。
# 使用示例: pytest -q test/include/api/test_memory.py -k test_memory_rejects_legacy_free_reshape_contract
# 对应功能实现文件路径: include/api/Memory.h
# 对应 spec 文件路径: spec/include/api/Memory.md
# 对应测试文件路径: test/include/api/test_memory.py
def test_memory_rejects_legacy_free_reshape_contract() -> None:
    stderr = _compile_expect_failure(
        r"""
#include "include/api/Memory.h"
#include "include/npu_demo/Memory.h"

int main() {
    float data[6] = {0, 1, 2, 3, 4, 5};
    long long shape[1] = {6};
    long long stride[1] = {1};
    long long reshape_buf[2] = {2, 3};
    Memory<GM, float> source(data, shape, stride, 1, MemoryFormat::Norm);
    Vector reshape_shape(reshape_buf, 2);
    auto bad = reshape(source, reshape_shape);
    return bad.rank();
}
"""
    )
    assert "reshape" in stderr
