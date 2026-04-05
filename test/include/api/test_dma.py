"""API DMA compile tests.

创建者: 小李飞刀
最后一次更改: jcc你莫辜负

功能说明:
- 通过编译并运行 C++ 片段验证 `include/api/Dma.h` 的 `view/slice/deslice` 声明，
  并使用 `include/npu_demo/Dma.h` 提供实现。

覆盖率信息:
- 当前覆盖率: `N/A`。该链路为 C++ 头文件，按规则豁免 `pytest-cov` 覆盖率统计。
- 达标判定: C++ 头文件实现按规则豁免 `95%` 覆盖率达标线。
- 当前覆盖基线: `API-DMA-001..002`。

覆盖率命令:
- `pytest -q test/include/api/test_dma.py`
- `N/A`（C++ 头文件实现，按当前规则豁免 `pytest-cov` 覆盖率统计）

使用示例:
- `pytest -q test/include/api/test_dma.py`

关联文件:
- 功能实现: [`include/npu_demo/Dma.h`](include/npu_demo/Dma.h)
- Spec 文档: [`spec/include/api/Dma.md`](spec/include/api/Dma.md)
- 测试文件: [`test/include/api/test_dma.py`](test/include/api/test_dma.py)
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
    - 使用 `g++` 编译临时源码并执行生成的程序。

    使用示例:
    - `_compile_and_run("int main() { return 0; }")`

    关联文件:
    - spec: [`spec/include/api/Dma.md`](spec/include/api/Dma.md)
    - test: [`test/include/api/test_dma.py`](test/include/api/test_dma.py)
    - 功能实现: [`test/include/api/test_dma.py`](test/include/api/test_dma.py)
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        source_path = Path(tmpdir) / "dma_test.cpp"
        binary_path = Path(tmpdir) / "dma_test"
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


# API-DMA-001
# 创建者: 小李飞刀
# 最后一次更改: jcc你莫辜负
# 功能说明: 验证 DMA view/slice/deslice 的基础调用链可编译并正确运行。
# 最近一次运行测试时间: 2026-04-05 23:44:24 +0800
# 最近一次运行成功时间: 2026-04-05 23:44:24 +0800
# 测试目的: 验证 `include/api/Dma.h` 声明可配合 `npu_demo` 后端完成 1-D `view/slice/deslice` 基础路径。
# 使用示例: `pytest -q test/include/api/test_dma.py -k test_api_dma_compile_and_basic_vector_usage`
# 对应功能实现文件路径: `include/npu_demo/Dma.h`
# 对应 spec 文件路径: `spec/include/api/Dma.md`
# 对应测试文件路径: `test/include/api/test_dma.py`
def test_api_dma_compile_and_basic_vector_usage() -> None:
    source = r"""
#include "include/api/Dma.h"
#include "include/npu_demo/Dma.h"

static int fail(int code) { return code; }

int main() {
    float source_data[10];
    for (int i = 0; i < 10; ++i) {
        source_data[i] = static_cast<float>(i);
    }
    long long shape[1] = {10};
    long long stride[1] = {1};
    Memory<float> source(source_data, shape, stride, 1, MemoryFormat::Norm, MemorySpace::GM);

    long long offset_buf[1] = {1};
    long long size_buf[1] = {4};
    long long stride_buf[1] = {2};
    Vector offset(offset_buf, 1);
    Vector size(size_buf, 1);
    Vector stride_vec(stride_buf, 1);

    Memory<float> sub = view(source, offset, size, stride_vec);
    if (sub.rank() != 1 || sub.shape()[0] != 4) {
        return fail(1);
    }
    if (sub.stride()[0] != 2) {
        return fail(2);
    }
    if (sub.data() != source.data() + 1) {
        return fail(3);
    }

    float tile_data[4] = {0};
    long long tile_shape[1] = {4};
    long long tile_stride[1] = {1};
    Memory<float> tile(
        tile_data,
        tile_shape,
        tile_stride,
        1,
        MemoryFormat::Norm,
        MemorySpace::TSM);
    if (slice(tile, source, offset, size, stride_vec) != StatusCode::kOk) {
        return fail(4);
    }
    if (tile_data[0] != 1.0f || tile_data[1] != 3.0f || tile_data[2] != 5.0f || tile_data[3] != 7.0f) {
        return fail(5);
    }

    float target_data[10] = {0};
    Memory<float> target(
        target_data,
        shape,
        stride,
        1,
        MemoryFormat::Norm,
        MemorySpace::GM);
    if (deslice(tile, target, offset, size, stride_vec) != StatusCode::kOk) {
        return fail(6);
    }
    if (target_data[1] != 1.0f || target_data[3] != 3.0f || target_data[5] != 5.0f ||
        target_data[7] != 7.0f) {
        return fail(7);
    }
    return 0;
}
"""
    _compile_and_run(source)


# API-DMA-002
# 创建者: 小李飞刀
# 最后一次更改: jcc你莫辜负
# 功能说明: 验证 DMA 入口在非法 vector rank 下返回稳定错误边界。
# 最近一次运行测试时间: 2026-04-05 23:44:24 +0800
# 最近一次运行成功时间: 2026-04-05 23:44:24 +0800
# 测试目的: 验证 `include/api/Dma.h` 入口在非法 vector rank 下保持后端约定的错误边界。
# 使用示例: `pytest -q test/include/api/test_dma.py -k test_api_dma_rejects_invalid_vector_rank`
# 对应功能实现文件路径: `include/npu_demo/Dma.h`
# 对应 spec 文件路径: `spec/include/api/Dma.md`
# 对应测试文件路径: `test/include/api/test_dma.py`
def test_api_dma_rejects_invalid_vector_rank() -> None:
    source = r"""
#include <stdexcept>
#include <string>

#include "include/api/Dma.h"
#include "include/npu_demo/Dma.h"

static int fail(int code) { return code; }

static bool contains(const std::string& value, const char* needle) {
    return value.find(needle) != std::string::npos;
}

int main() {
    float source_data[10] = {0};
    long long shape[1] = {10};
    long long stride[1] = {1};
    Memory<float> source(source_data, shape, stride, 1, MemoryFormat::Norm, MemorySpace::GM);

    long long offset_buf[2] = {0, 0};
    long long size_buf[2] = {1, 1};
    long long stride_buf[2] = {1, 1};
    Vector offset(offset_buf, 2);
    Vector size(size_buf, 2);
    Vector stride_vec(stride_buf, 2);

    try {
        auto bad = view(source, offset, size, stride_vec);
        (void)bad;
        return fail(1);
    } catch (const std::runtime_error& err) {
        if (!contains(err.what(), "vector_rank_mismatch")) {
            return fail(2);
        }
    }

    float tile_data[1] = {0};
    long long tile_shape[1] = {1};
    long long tile_stride[1] = {1};
    Memory<float> tile(
        tile_data,
        tile_shape,
        tile_stride,
        1,
        MemoryFormat::Norm,
        MemorySpace::TSM);
    if (slice(tile, source, offset, size, stride_vec) != StatusCode::kError) {
        return fail(3);
    }

    float target_data[10] = {0};
    Memory<float> target(
        target_data,
        shape,
        stride,
        1,
        MemoryFormat::Norm,
        MemorySpace::GM);
    if (deslice(tile, target, offset, size, stride_vec) != StatusCode::kError) {
        return fail(4);
    }
    return 0;
}
"""
    _compile_and_run(source)
