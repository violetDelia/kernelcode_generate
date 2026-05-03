"""API DMA compile tests.


功能说明:
- 通过编译并运行 C++ 片段验证 `include/api/Dma.h` 的 `slice/deslice` 声明，
  并结合 `Memory` 的成员式 `view` 接口与 `include/npu_demo/Dma.h` 提供的后端实现。

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


    功能说明:
    - 使用 `g++` 编译临时源码并执行生成的程序。
    - 对 GCC 13 在 `include/npu_demo/Dma.h` 上偶发的 internal compiler error 做有限重试，
      保持测试关注点仍是公开头文件合同而不是编译器偶发现象。

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

        compile_result = None
        max_attempts = 3
        for _attempt in range(max_attempts):
            compile_result = subprocess.run(
                [
                    "g++",
                    "-std=c++17",
                    # GCC 13 会在 include/npu_demo/Dma.h 的某些模板组合上触发 ICE，
                    # 这里用较保守的优化开关保持“可编译”门槛可测，不改变语义。
                    "-fno-tree-ccp",
                    "-fno-tree-dce",
                    "-fno-tree-forwprop",
                    "-fno-tree-scev-cprop",
                    "-fno-tree-vrp",
                    "-fno-tree-ter",
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
                break
            stderr = compile_result.stderr
            if "internal compiler error" not in stderr and "ld terminated with signal" not in stderr:
                break
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
    - 使用 `g++` 编译临时源码，并验证其因 DMA 旧公共接口已删除而编译失败。

    使用示例:
    - `stderr = _compile_expect_failure("int main() { return missing; }")`

    关联文件:
    - spec: [`spec/include/api/Dma.md`](spec/include/api/Dma.md)
    - test: [`test/include/api/test_dma.py`](test/include/api/test_dma.py)
    - 功能实现: [`test/include/api/test_dma.py`](test/include/api/test_dma.py)
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        source_path = Path(tmpdir) / "dma_test_fail.cpp"
        binary_path = Path(tmpdir) / "dma_test_fail"
        source_path.write_text(source, encoding="utf-8")

        compile_result = subprocess.run(
            [
                "g++",
                "-std=c++17",
                "-fno-tree-ccp",
                "-fno-tree-dce",
                "-fno-tree-forwprop",
                "-fno-tree-scev-cprop",
                "-fno-tree-vrp",
                "-fno-tree-ter",
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


# API-DMA-001
# 功能说明: 验证成员式 `view` 配合 `slice/deslice` 的基础调用链可编译并正确运行。
# 测试目的: 验证 `source.view<T>(...)` 与 `slice/deslice` 的公共层组合调用可配合 `npu_demo` 后端完成 1-D 基础路径。
# 使用示例: `pytest -q test/include/api/test_dma.py -k test_dma_member_view_and_target_first_deslice_contract`
# 对应功能实现文件路径: `include/npu_demo/Dma.h`
# 对应 spec 文件路径: `spec/include/api/Dma.md`
# 对应测试文件路径: `test/include/api/test_dma.py`
def test_dma_member_view_and_target_first_deslice_contract() -> None:
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
    Memory<GM, float> source(source_data, shape, stride, 1, MemoryFormat::Norm);

    long long offset_buf[1] = {1};
    long long size_buf[1] = {4};
    long long stride_buf[1] = {2};
    Vector offset(offset_buf, 1);
    Vector size(size_buf, 1);
    Vector stride_vec(stride_buf, 1);

    Memory<GM, float> sub = source.view<float>(offset, size, stride_vec);
    if (sub.rank() != 1 || sub.get_shape(0) != 4) {
        return fail(1);
    }
    if (sub.get_stride(0) != 2) {
        return fail(2);
    }
    if (sub.data() != source.data() + 1) {
        return fail(3);
    }

    float tile_data[4] = {0};
    long long tile_shape[1] = {4};
    long long tile_stride[1] = {1};
    Memory<TSM, float> tile(
        tile_data,
        tile_shape,
        tile_stride,
        1,
        MemoryFormat::Norm);
    if (npu_demo::slice(tile, source, offset, size, stride_vec) != StatusCode::kOk) {
        return fail(4);
    }
    if (tile_data[0] != 1.0f || tile_data[1] != 3.0f || tile_data[2] != 5.0f || tile_data[3] != 7.0f) {
        return fail(5);
    }

    float target_data[10] = {0};
    Memory<GM, float> target(
        target_data,
        shape,
        stride,
        1,
        MemoryFormat::Norm);
    if (npu_demo::deslice(target, tile, offset, size, stride_vec) != StatusCode::kOk) {
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
# 功能说明: 验证成员式 `view` 与 DMA 入口在非法 vector rank 下保持稳定错误边界。
# 测试目的: 验证 `include/api/Dma.h` 入口在非法 vector rank 下保持后端约定的错误边界。
# 使用示例: `pytest -q test/include/api/test_dma.py -k test_dma_cross_space_templates_rejects_invalid_vector_rank`
# 对应功能实现文件路径: `include/npu_demo/Dma.h`
# 对应 spec 文件路径: `spec/include/api/Dma.md`
# 对应测试文件路径: `test/include/api/test_dma.py`
def test_dma_cross_space_templates_rejects_invalid_vector_rank() -> None:
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
    Memory<GM, float> source(source_data, shape, stride, 1, MemoryFormat::Norm);

    long long offset_buf[2] = {0, 0};
    long long size_buf[2] = {1, 1};
    long long stride_buf[2] = {1, 1};
    Vector offset(offset_buf, 2);
    Vector size(size_buf, 2);
    Vector stride_vec(stride_buf, 2);

    try {
        auto bad = source.view<float>(offset, size, stride_vec);
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
    Memory<TSM, float> tile(
        tile_data,
        tile_shape,
        tile_stride,
        1,
        MemoryFormat::Norm);
    if (npu_demo::slice(tile, source, offset, size, stride_vec) != StatusCode::kError) {
        return fail(3);
    }

    float target_data[10] = {0};
    Memory<GM, float> target(
        target_data,
        shape,
        stride,
        1,
        MemoryFormat::Norm);
    if (npu_demo::deslice(target, tile, offset, size, stride_vec) != StatusCode::kError) {
        return fail(4);
    }
    return 0;
}
"""
    _compile_and_run(source)


# API-DMA-003
# 功能说明: 验证 target-first `deslice` 在跨空间模板参数下可编译并返回成功。
# 测试目的: 验证 `deslice` 接口允许 `SourceSpace/TargetSpace` 跨空间模板组合。
# 使用示例: `pytest -q test/include/api/test_dma.py -k test_dma_deslice_supports_cross_space_templates`
# 对应功能实现文件路径: `include/npu_demo/Dma.h`
# 对应 spec 文件路径: `spec/include/api/Dma.md`
# 对应测试文件路径: `test/include/api/test_dma.py`
def test_dma_deslice_supports_cross_space_templates() -> None:
    source = r"""
#include "include/api/Dma.h"
#include "include/npu_demo/Dma.h"

static int fail(int code) { return code; }

int main() {
    float source_data[8];
    for (int i = 0; i < 8; ++i) {
        source_data[i] = static_cast<float>(i);
    }
    long long shape[1] = {8};
    long long stride[1] = {1};
    Memory<GM, float> source(source_data, shape, stride, 1, MemoryFormat::Norm);

    long long offset_buf[1] = {2};
    long long size_buf[1] = {4};
    long long stride_buf[1] = {1};
    Vector offset(offset_buf, 1);
    Vector size(size_buf, 1);
    Vector stride_vec(stride_buf, 1);

    float tile_data[4] = {0};
    long long tile_shape[1] = {4};
    long long tile_stride[1] = {1};
    Memory<TSM, float> tile(tile_data, tile_shape, tile_stride, 1, MemoryFormat::Norm);

    if (npu_demo::slice(tile, source, offset, size, stride_vec) != StatusCode::kOk) {
        return fail(1);
    }

    float target_data[8] = {0};
    Memory<GM, float> target(target_data, shape, stride, 1, MemoryFormat::Norm);
    if (npu_demo::deslice(target, tile, offset, size, stride_vec) != StatusCode::kOk) {
        return fail(2);
    }
    if (target_data[2] != 2.0f || target_data[3] != 3.0f || target_data[4] != 4.0f ||
        target_data[5] != 5.0f) {
        return fail(3);
    }
    return 0;
}
"""
    _compile_and_run(source)


# API-DMA-003T
# 功能说明: 验证 target-first `transpose` 在跨空间与跨元素类型模板参数下可编译并返回成功。
# 测试目的: 验证 `transpose` 接口按 `perm[target_axis] = source_axis` 物化转置。
# 使用示例: `pytest -q test/include/api/test_dma.py -k test_dma_transpose_materializes_permuted_layout`
# 对应功能实现文件路径: `include/npu_demo/Dma.h`
# 对应 spec 文件路径: `spec/include/api/Dma.md`
# 对应测试文件路径: `test/include/api/test_dma.py`
def test_dma_transpose_materializes_permuted_layout() -> None:
    source = r"""
#include "include/api/Dma.h"
#include "include/npu_demo/Dma.h"

static int fail(int code) { return code; }

int main() {
    float source_data[6] = {1.0f, 2.0f, 3.0f, 4.0f, 5.0f, 6.0f};
    long long source_shape[2] = {2, 3};
    long long source_stride[2] = {3, 1};
    Memory<TSM, float> source(source_data, source_shape, source_stride, 2, MemoryFormat::Norm);

    int target_data[6] = {0, 0, 0, 0, 0, 0};
    long long target_shape[2] = {3, 2};
    long long target_stride[2] = {2, 1};
    Memory<GM, int> target(target_data, target_shape, target_stride, 2, MemoryFormat::Norm);

    if (npu_demo::transpose(target, source, Vector{1, 0}) != StatusCode::kOk) {
        return fail(1);
    }
    if (target_data[0] != 1 || target_data[1] != 4 ||
        target_data[2] != 2 || target_data[3] != 5 ||
        target_data[4] != 3 || target_data[5] != 6) {
        return fail(2);
    }

    long long bad_shape[2] = {2, 3};
    long long bad_stride[2] = {3, 1};
    Memory<GM, int> bad_target(target_data, bad_shape, bad_stride, 2, MemoryFormat::Norm);
    if (npu_demo::transpose(bad_target, source, Vector{1, 0}) != StatusCode::kError) {
        return fail(3);
    }
    long long duplicate_perm_buf[2] = {0, 0};
    Vector duplicate_perm(duplicate_perm_buf, 2);
    if (npu_demo::transpose(target, source, duplicate_perm) != StatusCode::kError) {
        return fail(4);
    }
    return 0;
}
"""
    _compile_and_run(source)


# API-DMA-003B
# 功能说明: 验证 `fill/broadcast` 在 npu_demo 后端可编译并物化目标块。
# 测试目的: 锁定 `fill` 与 trailing-dimension `broadcast` 的公共 DMA helper 语义。
# 使用示例: `pytest -q test/include/api/test_dma.py -k test_dma_fill_and_broadcast_materialize_target`
# 对应功能实现文件路径: `include/npu_demo/Dma.h`
# 对应 spec 文件路径: `spec/include/api/Dma.md`
# 对应测试文件路径: `test/include/api/test_dma.py`
def test_dma_fill_and_broadcast_materialize_target() -> None:
    source = r"""
#include "include/api/Dma.h"
#include "include/npu_demo/Dma.h"

static int fail(int code) { return code; }

int main() {
    float fill_data[6] = {0.0f};
    long long fill_shape[2] = {2, 3};
    long long fill_stride[2] = {3, 1};
    Memory<TSM, float> fill_target(fill_data, fill_shape, fill_stride, 2, MemoryFormat::Norm);
    if (npu_demo::fill<TSM, float>(fill_target, 2.5f) != StatusCode::kOk) {
        return fail(1);
    }
    for (int i = 0; i < 6; ++i) {
        if (fill_data[i] != 2.5f) {
            return fail(2);
        }
    }

    float source_data[2] = {10.0f, 20.0f};
    long long source_shape[2] = {2, 1};
    long long source_stride[2] = {1, 1};
    Memory<TSM, float> source(source_data, source_shape, source_stride, 2, MemoryFormat::Norm);

    int target_data[6] = {0, 0, 0, 0, 0, 0};
    long long target_shape[2] = {2, 3};
    long long target_stride[2] = {3, 1};
    Memory<TSM, int> target(target_data, target_shape, target_stride, 2, MemoryFormat::Norm);
    if (npu_demo::broadcast<TSM, TSM, int, float>(target, source) != StatusCode::kOk) {
        return fail(3);
    }
    int expected[6] = {10, 10, 10, 20, 20, 20};
    for (int i = 0; i < 6; ++i) {
        if (target_data[i] != expected[i]) {
            return fail(4);
        }
    }

    long long bad_shape[2] = {3, 3};
    long long bad_stride[2] = {3, 1};
    Memory<TSM, int> bad_target(target_data, bad_shape, bad_stride, 2, MemoryFormat::Norm);
    if (npu_demo::broadcast<TSM, TSM, int, float>(bad_target, source) != StatusCode::kError) {
        return fail(5);
    }
    return 0;
}
"""
    _compile_and_run(source)


# API-DMA-003A
# 功能说明: 验证 `alloc<Space, T>(shape, stride)` helper 可配合 npu_demo 后端编译运行。
# 测试目的: 锁定 DMA helper temporary memory 的公开源码形态存在对应实现，支持静态与动态 shape/stride。
# 使用示例: `pytest -q test/include/api/test_dma.py -k test_dma_alloc_helper_contract`
# 对应功能实现文件路径: `include/npu_demo/Dma.h`
# 对应 spec 文件路径: `spec/include/api/Dma.md`
# 对应测试文件路径: `test/include/api/test_dma.py`
def test_dma_alloc_helper_contract() -> None:
    source = r"""
#include "include/api/Dma.h"
#include "include/npu_demo/Dma.h"

static int fail(int code) { return code; }

int main() {
    auto tile = npu_demo::alloc<TSM, float>({2, 3}, {3, 1});
    if (tile.rank() != 2) {
        return fail(1);
    }
    if (tile.get_shape(0) != 2 || tile.get_shape(1) != 3) {
        return fail(2);
    }
    if (tile.get_stride(0) != 3 || tile.get_stride(1) != 1) {
        return fail(3);
    }
    if (tile.space() != MemorySpace::TSM) {
        return fail(4);
    }
    tile.data()[0] = 7.0f;
    if (tile.data()[0] != 7.0f) {
        return fail(5);
    }

    long long m = 4;
    long long n = 5;
    auto dyn = npu_demo::alloc<GM, float>({m, n}, {n, 1});
    if (dyn.rank() != 2) {
        return fail(6);
    }
    if (dyn.get_shape(0) != m || dyn.get_shape(1) != n) {
        return fail(7);
    }
    if (dyn.get_stride(0) != n || dyn.get_stride(1) != 1) {
        return fail(8);
    }
    if (dyn.space() != MemorySpace::GM) {
        return fail(9);
    }
    return 0;
}
"""
    _compile_and_run(source)


# API-DMA-004
# 测试目的: 验证旧自由函数 `view(source, ...)` 已退出 DMA 公共层稳定口径，且头文件中的 `deslice` 声明保持 target-first。
# 使用示例: `pytest -q test/include/api/test_dma.py -k test_dma_rejects_legacy_free_view_contract`
# 对应功能实现文件路径: `include/api/Dma.h`
# 对应 spec 文件路径: `spec/include/api/Dma.md`
# 对应测试文件路径: `test/include/api/test_dma.py`
def test_dma_rejects_legacy_free_view_contract() -> None:
    stderr = _compile_expect_failure(
        r"""
#include "include/api/Dma.h"
#include "include/npu_demo/Dma.h"

int main() {
    float source_data[4] = {0};
    long long shape[1] = {4};
    long long stride[1] = {1};
    long long offset_buf[1] = {0};
    long long size_buf[1] = {1};
    long long stride_buf[1] = {1};
    Memory<GM, float> source(source_data, shape, stride, 1, MemoryFormat::Norm);
    Vector offset(offset_buf, 1);
    Vector size(size_buf, 1);
    Vector stride_vec(stride_buf, 1);
    auto bad = view(source, offset, size, stride_vec);
    return bad.rank();
}
"""
    )
    assert "view" in stderr

    header = (REPO_ROOT / "include" / "api" / "Dma.h").read_text(encoding="utf-8")
    assert "Memory<Space, T> view(" not in header
    assert "Status deslice(" in header
    assert "Memory<TargetSpace, T>& target" in header
    assert "const Memory<SourceSpace, T>& source,\n    Memory<TargetSpace, T>& target" not in header
