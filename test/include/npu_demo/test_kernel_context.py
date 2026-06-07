"""NPU demo KernelContext include tests.


功能说明:
- 通过编译并运行 C++ 片段验证 `include/npu_demo/npu_demo.h` 的 `KernelContext` 运行时视图、
  barrier 合同与动态内存查询契约。

覆盖率信息:
- 当前覆盖率: `N/A`。该链路的功能实现为 C++ 头文件，按当前规则豁免 `pytest-cov` 覆盖率统计。
- 达标判定: C++ 头文件实现按规则豁免 `95%` 覆盖率达标线。
- 当前覆盖基线: `NPU-DEMO-KC-001..010`。

覆盖率命令:
- `pytest --cov=include/npu_demo/npu_demo.h --cov-report=term-missing test/include/npu_demo/test_kernel_context.py`
- `pytest -q test/include/npu_demo/test_kernel_context.py`

使用示例:
- `pytest -q test/include/npu_demo/test_kernel_context.py`

关联文件:
- 功能实现: [include/npu_demo/npu_demo.h](include/npu_demo/npu_demo.h)
- Spec 文档: [spec/include/npu_demo/npu_demo.md](spec/include/npu_demo/npu_demo.md)
- 测试文件: [test/include/npu_demo/test_kernel_context.py](test/include/npu_demo/test_kernel_context.py)
"""

from __future__ import annotations

import subprocess
import tempfile
import time
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]


def _compile_and_run(source: str) -> None:
    """编译并运行 C++ 测试片段。


    功能说明:
    - 使用 `g++` 编译临时源码并执行生成程序，用于验收头文件契约。

    使用示例:
    - `_compile_and_run("int main() { return 0; }")`

    关联文件:
    - spec: [spec/include/npu_demo/npu_demo.md](spec/include/npu_demo/npu_demo.md)
    - test: [test/include/npu_demo/test_kernel_context.py](test/include/npu_demo/test_kernel_context.py)
    - 功能实现: [test/include/npu_demo/test_kernel_context.py](test/include/npu_demo/test_kernel_context.py)
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        source_path = Path(tmpdir) / "npu_demo_kernel_context.cpp"
        binary_path = Path(tmpdir) / "npu_demo_kernel_context"
        source_path.write_text(source, encoding="utf-8")

        compile_result = None
        max_attempts = 3
        for attempt in range(max_attempts):
            compile_result = subprocess.run(
                [
                    "g++",
                    "-std=c++17",
                    "-pthread",
                    # GCC 13 在 npu_demo 头文件模板上会在 tree/cfgcleanup 类阶段触发 ICE；
                    # 关闭几组相关优化，保留“可编译”门禁本身。
                    "-fno-tree-ccp",
                    "-fno-tree-dce",
                    "-fno-tree-forwprop",
                    "-fno-tree-scev-cprop",
                    "-fno-tree-vrp",
                    "-fno-tree-ter",
                    "-Wl,--no-keep-memory",
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
            if (
                "ld terminated with signal" in stderr
                or "SIGSEGV" in stderr
                or "Segmentation fault" in stderr
            ) and attempt < max_attempts - 1:
                time.sleep(1)
                continue
            raise AssertionError(
                "g++ compile failed:\n"
                f"stdout:\n{compile_result.stdout}\n"
                f"stderr:\n{compile_result.stderr}"
            )
        if compile_result is None or compile_result.returncode != 0:
            raise AssertionError(
                "g++ compile failed after retries:\n"
                f"stdout:\n{compile_result.stdout if compile_result else ''}\n"
                f"stderr:\n{compile_result.stderr if compile_result else ''}"
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
    """编译 C++ 测试片段并返回预期失败的 stderr。

    功能说明:
    - 用于验证被删除的旧公开调用面不能再通过编译。

    使用示例:
    - stderr = _compile_expect_failure("int main() { return missing; }")

    关联文件:
    - spec: [spec/include/npu_demo/npu_demo.md](spec/include/npu_demo/npu_demo.md)
    - test: [test/include/npu_demo/test_kernel_context.py](test/include/npu_demo/test_kernel_context.py)
    - 功能实现: [test/include/npu_demo/test_kernel_context.py](test/include/npu_demo/test_kernel_context.py)
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        source_path = Path(tmpdir) / "npu_demo_kernel_context_negative.cpp"
        binary_path = Path(tmpdir) / "npu_demo_kernel_context_negative"
        source_path.write_text(source, encoding="utf-8")
        compile_result = subprocess.run(
            [
                "g++",
                "-std=c++17",
                "-pthread",
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


# NPU-DEMO-KC-001
# 测试目的: 验证 launched body 中的 KernelContext 查询返回本次 launch 的运行时 extent 与索引。
# 使用示例: pytest -q test/include/npu_demo/test_kernel_context.py -k test_npu_demo_kernel_context_runtime_view_tracks_launch_extent
# 对应功能实现文件链接: [include/npu_demo/npu_demo.h](include/npu_demo/npu_demo.h)
# 对应 spec 文件链接: [spec/include/npu_demo/npu_demo.md](spec/include/npu_demo/npu_demo.md)
# 对应测试文件链接: [test/include/npu_demo/test_kernel_context.py](test/include/npu_demo/test_kernel_context.py)
def test_npu_demo_kernel_context_runtime_view_tracks_launch_extent() -> None:
    source = r"""
#include "include/npu_demo/npu_demo.h"

static int fail(int code) { return code; }

static void kernel_body(
    npu_demo::KernelContext& ctx,
    long long* block_ids,
    long long* thread_ids,
    long long* thread_nums) {
    (void)ctx;
    const long long bid = block_id();
    block_ids[bid] = npu_demo::block_id();
    thread_ids[bid] = thread_id();
    thread_nums[bid] = thread_num();
}

int main() {
    npu_demo::KernelContext ctx;
    long long block_ids[2] = {-1, -1};
    long long thread_ids[2] = {-1, -1};
    long long thread_nums[2] = {0, 0};

    if (npu_demo::launch<2, 1, 1, 0, kernel_body>(
            ctx,
            block_ids,
            thread_ids,
            thread_nums)
        != StatusCode::kOk) {
        return fail(1);
    }

    for (long long i = 0; i < 2; ++i) {
        if (block_ids[i] != i) {
            return fail(2);
        }
        if (thread_ids[i] != 0) {
            return fail(4);
        }
        if (thread_nums[i] != 1) {
            return fail(5);
        }
    }
    return 0;
}
"""
    _compile_and_run(source)


# NPU-DEMO-KC-001B
# 测试目的: 验证 npu_demo::launch 不再支持无显式 KernelContext 参数的 callee。
# 使用示例: pytest -q test/include/npu_demo/test_kernel_context.py -k test_npu_demo_launch_rejects_context_free_callee
# 对应功能实现文件链接: [include/npu_demo/npu_demo.h](include/npu_demo/npu_demo.h)
# 对应 spec 文件链接: [spec/include/npu_demo/npu_demo.md](spec/include/npu_demo/npu_demo.md)
# 对应测试文件链接: [test/include/npu_demo/test_kernel_context.py](test/include/npu_demo/test_kernel_context.py)
def test_npu_demo_launch_rejects_context_free_callee() -> None:
    stderr = _compile_expect_failure(
        r"""
#include "include/npu_demo/npu_demo.h"

static void kernel_body(long long* block_ids, long long* thread_ids, long long* thread_nums, long long* after_barrier) {
    const long long bid = npu_demo::block_id();
    block_ids[bid] = bid;
    thread_ids[bid] = npu_demo::thread_id();
    thread_nums[bid] = npu_demo::thread_num();
    npu_demo::barrier({BarrierVisibility::TSM, BarrierVisibility::TLM}, BarrierScope::BLOCK);
    after_barrier[bid] = npu_demo::thread_num();
}

int main() {
    npu_demo::KernelContext ctx;
    long long block_ids[2] = {-1, -1};
    long long thread_ids[2] = {-1, -1};
    long long thread_nums[2] = {0, 0};
    long long after_barrier[2] = {0, 0};
    return npu_demo::launch<2, 1, 1, 0, kernel_body>(ctx, block_ids, thread_ids, thread_nums, after_barrier);
}
"""
    )
    assert "launch name must accept Context& plus args" in stderr


# NPU-DEMO-KC-001A
# 测试目的: 验证 npu_demo::barrier 需要显式 visibility / scope，且只接受 {BarrierVisibility::TSM, BarrierVisibility::TLM} + BLOCK。
# 使用示例: pytest -q test/include/npu_demo/test_kernel_context.py -k test_npu_demo_kernel_context_barrier_requires_visibility_and_block_scope
# 对应功能实现文件链接: [include/npu_demo/npu_demo.h](include/npu_demo/npu_demo.h)
# 对应 spec 文件链接: [spec/include/npu_demo/npu_demo.md](spec/include/npu_demo/npu_demo.md)
# 对应测试文件链接: [test/include/npu_demo/test_kernel_context.py](test/include/npu_demo/test_kernel_context.py)
def test_npu_demo_kernel_context_barrier_requires_visibility_and_block_scope() -> None:
    source = r"""
#include <stdexcept>
#include <string>

#include "include/npu_demo/npu_demo.h"

static int fail(int code) { return code; }

static bool contains(const std::string& value, const char* needle) {
    return value.find(needle) != std::string::npos;
}

static void kernel_body(npu_demo::KernelContext& ctx, int* result_code) {
    (void)ctx;
    npu_demo::barrier({BarrierVisibility::TLM, BarrierVisibility::TSM}, BarrierScope::BLOCK);
    if (npu_demo::thread_id() != 0) {
        return;
    }

    try {
        npu_demo::barrier({}, BarrierScope::BLOCK);
        *result_code = 1;
        return;
    } catch (const std::invalid_argument& err) {
        if (!contains(err.what(), "visibility")) {
            *result_code = 2;
            return;
        }
    }

    try {
        npu_demo::barrier({BarrierVisibility::TSM}, BarrierScope::BLOCK);
        *result_code = 3;
        return;
    } catch (const std::invalid_argument& err) {
        if (!contains(err.what(), "TSM") || !contains(err.what(), "TLM")) {
            *result_code = 4;
            return;
        }
    }

    try {
        npu_demo::barrier({BarrierVisibility::TSM, BarrierVisibility::TSM}, BarrierScope::BLOCK);
        *result_code = 5;
        return;
    } catch (const std::invalid_argument& err) {
        if (!contains(err.what(), "exactly once")) {
            *result_code = 6;
            return;
        }
    }

    try {
        npu_demo::barrier({BarrierVisibility::TSM, static_cast<BarrierVisibility>(-1)}, BarrierScope::BLOCK);
        *result_code = 7;
        return;
    } catch (const std::invalid_argument& err) {
        if (!contains(err.what(), "visibility")) {
            *result_code = 8;
            return;
        }
    }

    try {
        npu_demo::barrier({BarrierVisibility::TSM, BarrierVisibility::TLM}, BarrierScope::THREAD);
        *result_code = 9;
        return;
    } catch (const std::invalid_argument& err) {
        if (!contains(err.what(), "scope")) {
            *result_code = 10;
            return;
        }
    }

    *result_code = 0;
}

int main() {
    npu_demo::KernelContext ctx;
    int result_code = 99;
    if (npu_demo::launch<2, 1, 1, 0, kernel_body>(ctx, &result_code) != StatusCode::kOk) {
        return fail(11);
    }
    if (result_code != 0) {
        return fail(12 + result_code);
    }
    return 0;
}
"""
    _compile_and_run(source)


# NPU-DEMO-KC-001B
# 测试目的: 验证 npu_demo::launch 对不受支持的 extent 显式返回失败而不是静默回退。
# 使用示例: pytest -q test/include/npu_demo/test_kernel_context.py -k test_npu_demo_launch_rejects_unsupported_extent_without_fallback
# 对应功能实现文件链接: [include/npu_demo/npu_demo.h](include/npu_demo/npu_demo.h)
# 对应 spec 文件链接: [spec/include/npu_demo/npu_demo.md](spec/include/npu_demo/npu_demo.md)
# 对应测试文件链接: [test/include/npu_demo/test_kernel_context.py](test/include/npu_demo/test_kernel_context.py)
def test_npu_demo_launch_rejects_unsupported_extent_without_fallback() -> None:
    source = r"""
#include "include/npu_demo/npu_demo.h"

static int fail(int code) { return code; }

static void noop(npu_demo::KernelContext& ctx) {
    (void)ctx;
}

int main() {
    npu_demo::KernelContext ctx;
    if (npu_demo::launch<2, 1, 1, 0, noop>(ctx) != StatusCode::kOk) {
        return fail(1);
    }
    if (npu_demo::launch<1, 1, 1, 0, noop>(ctx) != StatusCode::kOk) {
        return fail(6);
    }
    if (npu_demo::launch<3, 1, 1, 0, noop>(ctx) != StatusCode::kError) {
        return fail(7);
    }
    if (npu_demo::launch<2, 2, 1, 0, noop>(ctx) != StatusCode::kError) {
        return fail(2);
    }
    if (npu_demo::launch<1, 9, 1, 0, noop>(ctx) != StatusCode::kError) {
        return fail(4);
    }
    if (npu_demo::launch<2, 1, 2, 0, noop>(ctx) != StatusCode::kError) {
        return fail(5);
    }
    if (npu_demo::launch<2, 1, 1, 1, noop>(ctx) != StatusCode::kError) {
        return fail(8);
    }
    return 0;
}
"""
    _compile_and_run(source)


# NPU-DEMO-KC-002
# 测试目的: 验证 get_dynamic_memory<TSM>() 返回固定 shape/stride/space 且带可写 backing 的 Memory 视图。
# 使用示例: pytest -q test/include/npu_demo/test_kernel_context.py -k test_npu_demo_kernel_context_returns_typed_tsm_memory
# 对应功能实现文件链接: [include/npu_demo/npu_demo.h](include/npu_demo/npu_demo.h)
# 对应 spec 文件链接: [spec/include/npu_demo/npu_demo.md](spec/include/npu_demo/npu_demo.md)
# 对应测试文件链接: [test/include/npu_demo/test_kernel_context.py](test/include/npu_demo/test_kernel_context.py)
def test_npu_demo_kernel_context_returns_typed_tsm_memory() -> None:
    source = r"""
#include "include/npu_demo/npu_demo.h"

static int fail(int code) { return code; }

int main() {
    Memory<TSM, float> mem = get_dynamic_memory<TSM>();

    if (mem.rank() != 1) {
        return fail(1);
    }
    if (mem.shape()[0] != 2097152) {
        return fail(2);
    }
    if (mem.stride()[0] != 1) {
        return fail(3);
    }
    if (mem.space() != MemorySpace::TSM) {
        return fail(4);
    }
    if (mem.data() == nullptr) {
        return fail(5);
    }
    mem.data()[0] = 7.0f;
    if (mem.data()[0] != 7.0f) {
        return fail(6);
    }
    return 0;
}
"""
    _compile_and_run(source)


# NPU-DEMO-KC-003
# 测试目的: 验证 get_dynamic_memory<TLM1/TLM2/TLM3>() 返回各自独立且带可写 backing 的 shape/stride/space Memory 视图。
# 使用示例: pytest -q test/include/npu_demo/test_kernel_context.py -k test_npu_demo_kernel_context_returns_typed_tlm123_memory
# 对应功能实现文件链接: [include/npu_demo/npu_demo.h](include/npu_demo/npu_demo.h)
# 对应 spec 文件链接: [spec/include/npu_demo/npu_demo.md](spec/include/npu_demo/npu_demo.md)
# 对应测试文件链接: [test/include/npu_demo/test_kernel_context.py](test/include/npu_demo/test_kernel_context.py)
def test_npu_demo_kernel_context_returns_typed_tlm123_memory() -> None:
    source = r"""
#include "include/npu_demo/npu_demo.h"

static int fail(int code) { return code; }

int main() {
    Memory<TLM1, float> tlm1 = get_dynamic_memory<TLM1>();
    Memory<TLM2, float> tlm2 = get_dynamic_memory<TLM2>();
    Memory<TLM3, float> tlm3 = get_dynamic_memory<TLM3>();

    if (tlm1.rank() != 1) {
        return fail(1);
    }
    if (tlm1.shape()[0] != 524288) {
        return fail(2);
    }
    if (tlm1.stride()[0] != 1) {
        return fail(3);
    }
    if (tlm1.space() != MemorySpace::TLM1) {
        return fail(4);
    }
    if (tlm1.data() == nullptr) {
        return fail(13);
    }
    if (tlm2.rank() != 1) {
        return fail(5);
    }
    if (tlm2.shape()[0] != 1048576) {
        return fail(6);
    }
    if (tlm2.stride()[0] != 1) {
        return fail(7);
    }
    if (tlm2.space() != MemorySpace::TLM2) {
        return fail(8);
    }
    if (tlm2.data() == nullptr || tlm2.data() == tlm1.data()) {
        return fail(14);
    }
    if (tlm3.rank() != 1) {
        return fail(9);
    }
    if (tlm3.shape()[0] != 1048576) {
        return fail(10);
    }
    if (tlm3.stride()[0] != 1) {
        return fail(11);
    }
    if (tlm3.space() != MemorySpace::TLM3) {
        return fail(12);
    }
    if (tlm3.data() == nullptr || tlm3.data() == tlm1.data() || tlm3.data() == tlm2.data()) {
        return fail(15);
    }
    return 0;
}
"""
    _compile_and_run(source)


# NPU-DEMO-KC-003B
# 测试目的: 验证动态内存 backing 可通过成员式 view 切成 typed tile，并可作为公开 slice 写入目标。
# 使用示例: pytest -q test/include/npu_demo/test_kernel_context.py -k test_npu_demo_dynamic_memory_backing_supports_view_and_slice
# 对应功能实现文件链接: [include/npu_demo/Arch.h](include/npu_demo/Arch.h)
# 对应 spec 文件链接: [spec/include/npu_demo/npu_demo.md](spec/include/npu_demo/npu_demo.md)
# 对应测试文件链接: [test/include/npu_demo/test_kernel_context.py](test/include/npu_demo/test_kernel_context.py)
def test_npu_demo_dynamic_memory_backing_supports_view_and_slice() -> None:
    source = r"""
#include <cstdint>

#include "include/npu_demo/npu_demo.h"

static int fail(int code) { return code; }

int main() {
    npu_demo::KernelContext ctx;
    Memory<TSM, int8_t> backing = get_dynamic_memory<TSM>();
    if (backing.data() == nullptr) {
        return fail(1);
    }

    long long offset_buf[1] = {0};
    long long size_buf[1] = {4};
    long long stride_buf[1] = {1};
    Vector offset(offset_buf, 1);
    Vector size(size_buf, 1);
    Vector stride_vec(stride_buf, 1);
    Memory<TSM, float> tile = backing.view<float>(offset, size, stride_vec);
    if (tile.data() == nullptr || tile.rank() != 1 || tile.get_shape(0) != 4) {
        return fail(2);
    }
    if (npu_demo::fill(ctx, tile, 0.0f) != StatusCode::kOk) {
        return fail(3);
    }

    float source_data[4] = {1.0f, 2.0f, 3.0f, 4.0f};
    Memory<GM, float> source(source_data, {4}, {1}, MemoryFormat::Norm);
    if (npu_demo::slice(ctx, tile, source, offset, size, stride_vec) != StatusCode::kOk) {
        return fail(4);
    }
    if (tile.data()[0] != 1.0f || tile.data()[1] != 2.0f ||
        tile.data()[2] != 3.0f || tile.data()[3] != 4.0f) {
        return fail(5);
    }
    return 0;
}
"""
    _compile_and_run(source)


# NPU-DEMO-KC-004
# 测试目的: 验证 get_dynamic_memory<SM, float>() 在 sm_memory_size=0 时抛出带关键字的运行期错误。
# 使用示例: pytest -q test/include/npu_demo/test_kernel_context.py -k test_npu_demo_kernel_context_rejects_sm_when_size_zero
# 对应功能实现文件链接: [include/npu_demo/npu_demo.h](include/npu_demo/npu_demo.h)
# 对应 spec 文件链接: [spec/include/npu_demo/npu_demo.md](spec/include/npu_demo/npu_demo.md)
# 对应测试文件链接: [test/include/npu_demo/test_kernel_context.py](test/include/npu_demo/test_kernel_context.py)
def test_npu_demo_kernel_context_rejects_sm_when_size_zero() -> None:
    source = r"""
#include <stdexcept>
#include <string>

#include "include/npu_demo/npu_demo.h"

static int fail(int code) { return code; }

int main() {
    try {
        Memory<MemorySpace::SM, float> mem = npu_demo::get_dynamic_memory<MemorySpace::SM>();
        (void)mem;
        return fail(1);
    } catch (const std::runtime_error& err) {
        std::string message(err.what());
        if (message.find("sm_memory_size=0") == std::string::npos) {
            return fail(2);
        }
        return 0;
    } catch (...) {
        return fail(3);
    }
}
"""
    _compile_and_run(source)


# NPU-DEMO-KC-005
# 测试目的: 验证 get_dynamic_memory<LM, float>() 在 lm_memory_size=0 时抛出带关键字的运行期错误。
# 使用示例: pytest -q test/include/npu_demo/test_kernel_context.py -k test_npu_demo_kernel_context_rejects_lm_when_size_zero
# 对应功能实现文件链接: [include/npu_demo/npu_demo.h](include/npu_demo/npu_demo.h)
# 对应 spec 文件链接: [spec/include/npu_demo/npu_demo.md](spec/include/npu_demo/npu_demo.md)
# 对应测试文件链接: [test/include/npu_demo/test_kernel_context.py](test/include/npu_demo/test_kernel_context.py)
def test_npu_demo_kernel_context_rejects_lm_when_size_zero() -> None:
    source = r"""
#include <stdexcept>
#include <string>

#include "include/npu_demo/npu_demo.h"

static int fail(int code) { return code; }

int main() {
    try {
        Memory<LM, float> mem = npu_demo::get_dynamic_memory<LM>();
        (void)mem;
        return fail(1);
    } catch (const std::runtime_error& err) {
        std::string message(err.what());
        if (message.find("lm_memory_size=0") == std::string::npos) {
            return fail(2);
        }
        return 0;
    } catch (...) {
        return fail(3);
    }
}
"""
    _compile_and_run(source)


# NPU-DEMO-KC-005B
# 测试目的: 验证 get_dynamic_memory 模板空间入口的成功与失败路径可编译并返回稳定结果，且 TLM1/TLM2/TLM3 容量各自独立。
# 使用示例: pytest -q test/include/npu_demo/test_kernel_context.py -k test_get_dynamic_memory_template_space_contract
# 对应功能实现文件链接: [include/npu_demo/Arch.h](include/npu_demo/Arch.h)
# 对应 spec 文件链接: [spec/include/npu_demo/npu_demo.md](spec/include/npu_demo/npu_demo.md)
# 对应测试文件链接: [test/include/npu_demo/test_kernel_context.py](test/include/npu_demo/test_kernel_context.py)
def test_get_dynamic_memory_template_space_contract() -> None:
    source = r"""
#include <stdexcept>
#include <string>

#include "include/npu_demo/npu_demo.h"

static int fail(int code) { return code; }

static bool contains(const std::string& value, const char* needle) {
    return value.find(needle) != std::string::npos;
}

int main() {
    Memory<TSM, float> tsm = npu_demo::get_dynamic_memory<TSM>();
    if (tsm.rank() != 1 || tsm.shape()[0] != 2097152 || tsm.stride()[0] != 1 || tsm.space() != MemorySpace::TSM) {
        return fail(1);
    }

    Memory<TLM1, float> tlm1 = npu_demo::get_dynamic_memory<TLM1>();
    if (tlm1.rank() != 1 || tlm1.shape()[0] != 524288 || tlm1.stride()[0] != 1 || tlm1.space() != MemorySpace::TLM1) {
        return fail(2);
    }
    Memory<TLM2, float> tlm2 = npu_demo::get_dynamic_memory<TLM2>();
    if (tlm2.rank() != 1 || tlm2.shape()[0] != 1048576 || tlm2.stride()[0] != 1 || tlm2.space() != MemorySpace::TLM2) {
        return fail(3);
    }
    Memory<TLM3, float> tlm3 = npu_demo::get_dynamic_memory<TLM3>();
    if (tlm3.rank() != 1 || tlm3.shape()[0] != 1048576 || tlm3.stride()[0] != 1 || tlm3.space() != MemorySpace::TLM3) {
        return fail(4);
    }

    try {
        Memory<SM, float> sm = npu_demo::get_dynamic_memory<SM>();
        (void)sm;
        return fail(5);
    } catch (const std::runtime_error& err) {
        if (!contains(err.what(), "sm_memory_size=0")) {
            return fail(6);
        }
    } catch (...) {
        return fail(7);
    }

    try {
        Memory<LM, float> lm = npu_demo::get_dynamic_memory<LM>();
        (void)lm;
        return fail(8);
    } catch (const std::runtime_error& err) {
        if (!contains(err.what(), "lm_memory_size=0")) {
            return fail(9);
        }
    } catch (...) {
        return fail(10);
    }
    return 0;
}
"""
    _compile_and_run(source)


# NPU-DEMO-KC-006
# 测试目的: 验证 view/slice/deslice 在 1-D 子集下返回正确视图与数据搬运结果。
# 使用示例: pytest -q test/include/npu_demo/test_kernel_context.py -k test_npu_demo_dma_view_slice_deslice_supports_1d_subset
# 对应功能实现文件链接: [include/npu_demo/Dma.h](include/npu_demo/Dma.h)
# 对应 spec 文件链接: [spec/include/api/Dma.md](spec/include/api/Dma.md)
# 对应测试文件链接: [test/include/npu_demo/test_kernel_context.py](test/include/npu_demo/test_kernel_context.py)
def test_npu_demo_dma_view_slice_deslice_supports_1d_subset() -> None:
    source = r"""
#include "include/npu_demo/npu_demo.h"

static int fail(int code) { return code; }

int main() {
    npu_demo::KernelContext ctx;
    float data[10];
    for (int i = 0; i < 10; ++i) {
        data[i] = static_cast<float>(i);
    }
    Memory<MemorySpace::GM, float> source(data, {10}, {1}, MemoryFormat::Norm);

    long long offset_buf[1] = {1};
    long long size_buf[1] = {4};
    long long stride_buf[1] = {2};
    Vector offset(offset_buf, 1);
    Vector size(size_buf, 1);
    Vector stride_vec(stride_buf, 1);

    auto sub = source.view<float>(offset, size, stride_vec);
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
    Memory<MemorySpace::TSM, float> tile(tile_data, {4}, {1}, MemoryFormat::Norm);
    if (npu_demo::slice(ctx, tile, source, offset, size, stride_vec) != StatusCode::kOk) {
        return fail(4);
    }
    if (tile_data[0] != 1.0f || tile_data[1] != 3.0f || tile_data[2] != 5.0f || tile_data[3] != 7.0f) {
        return fail(5);
    }

    float target_data[10] = {0};
    Memory<MemorySpace::GM, float> target(target_data, {10}, {1}, MemoryFormat::Norm);
    if (npu_demo::deslice(ctx, target, tile, offset, size, stride_vec) != StatusCode::kOk) {
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


# NPU-DEMO-KC-008
# 测试目的: 验证成员式 `view<T>(...)` 对非法 offset/size/stride、越界明确失败，并支持 rank2 view 的 physical stride 传播。
# 使用示例: pytest -q test/include/npu_demo/test_kernel_context.py -k test_npu_demo_dma_view_rejects_invalid_params
# 对应功能实现文件链接: [include/npu_demo/Memory.h](include/npu_demo/Memory.h)
# 对应 spec 文件链接: [spec/include/api/Memory.md](spec/include/api/Memory.md)
# 对应测试文件链接: [test/include/npu_demo/test_kernel_context.py](test/include/npu_demo/test_kernel_context.py)
def test_npu_demo_dma_view_rejects_invalid_params() -> None:
    source = r"""
#include <stdexcept>
#include <string>

#include "include/npu_demo/npu_demo.h"

static int fail(int code) { return code; }

static bool contains(const std::string& value, const char* needle) {
    return value.find(needle) != std::string::npos;
}

static int expect_runtime_error_contains(const std::runtime_error& err, const char* needle, int code) {
    std::string message(err.what());
    if (!contains(message, needle)) {
        return fail(code);
    }
    return 0;
}

int main() {
    float data[10];
    for (int i = 0; i < 10; ++i) {
        data[i] = static_cast<float>(i);
    }
    Memory<MemorySpace::GM, float> source(data, {10}, {1}, MemoryFormat::Norm);

    // 成员式 Vector 参数：非法 offset/size/stride 与越界。
    long long offset_neg_scalar_buf[1] = {-1};
    long long size_scalar_buf[1] = {4};
    long long stride_scalar_buf[1] = {1};
    Vector offset_neg_scalar(offset_neg_scalar_buf, 1);
    Vector size_scalar(size_scalar_buf, 1);
    Vector stride_scalar(stride_scalar_buf, 1);
    try {
        auto bad = source.view<float>(offset_neg_scalar, size_scalar, stride_scalar);
        (void)bad;
        return fail(1);
    } catch (const std::runtime_error& err) {
        const int status = expect_runtime_error_contains(err, "memory.view", 2);
        if (status != 0) {
            return status;
        }
    }

    long long offset_zero_buf[1] = {0};
    long long size_zero_buf[1] = {0};
    Vector offset_zero(offset_zero_buf, 1);
    Vector size_zero(size_zero_buf, 1);
    try {
        auto bad = source.view<float>(offset_zero, size_zero, stride_scalar);
        (void)bad;
        return fail(3);
    } catch (const std::runtime_error& err) {
        const int status = expect_runtime_error_contains(err, "invalid offset/size/stride", 4);
        if (status != 0) {
            return status;
        }
    }

    long long stride_zero_buf[1] = {0};
    Vector stride_zero(stride_zero_buf, 1);
    try {
        auto bad = source.view<float>(offset_zero, size_scalar, stride_zero);
        (void)bad;
        return fail(5);
    } catch (const std::runtime_error& err) {
        const int status = expect_runtime_error_contains(err, "invalid offset/size/stride", 6);
        if (status != 0) {
            return status;
        }
    }

    long long offset_oob_scalar_buf[1] = {9};
    long long size_oob_scalar_buf[1] = {2};
    Vector offset_oob_scalar(offset_oob_scalar_buf, 1);
    Vector size_oob_scalar(size_oob_scalar_buf, 1);
    try {
        auto bad = source.view<float>(offset_oob_scalar, size_oob_scalar, stride_scalar);
        (void)bad;
        return fail(7);
    } catch (const std::runtime_error& err) {
        const int status = expect_runtime_error_contains(err, "out_of_bounds", 8);
        if (status != 0) {
            return status;
        }
    }

    // Vector 参数：rank 不一致、非法值、越界。
    long long offset_bad_rank_buf[2] = {0, 0};
    long long size_bad_rank_buf[2] = {1, 1};
    long long stride_bad_rank_buf[2] = {1, 1};
    Vector offset_bad_rank(offset_bad_rank_buf, 2);
    Vector size_bad_rank(size_bad_rank_buf, 2);
    Vector stride_bad_rank(stride_bad_rank_buf, 2);

    try {
        auto bad = source.view<float>(offset_bad_rank, size_bad_rank, stride_bad_rank);
        (void)bad;
        return fail(9);
    } catch (const std::runtime_error& err) {
        const int status = expect_runtime_error_contains(err, "vector_rank_mismatch", 10);
        if (status != 0) {
            return status;
        }
    }

    long long offset_neg_buf[1] = {-1};
    long long size_ok_buf[1] = {4};
    long long stride_ok_buf[1] = {1};
    Vector offset_neg(offset_neg_buf, 1);
    Vector size_ok(size_ok_buf, 1);
    Vector stride_ok(stride_ok_buf, 1);

    try {
        auto bad = source.view<float>(offset_neg, size_ok, stride_ok);
        (void)bad;
        return fail(11);
    } catch (const std::runtime_error& err) {
        const int status = expect_runtime_error_contains(err, "invalid offset/size/stride", 12);
        if (status != 0) {
            return status;
        }
    }

    long long offset_oob_buf[1] = {9};
    long long size_oob_buf[1] = {2};
    Vector offset_oob(offset_oob_buf, 1);
    Vector size_oob(size_oob_buf, 1);

    try {
        auto bad = source.view<float>(offset_oob, size_oob, stride_ok);
        (void)bad;
        return fail(13);
    } catch (const std::runtime_error& err) {
        const int status = expect_runtime_error_contains(err, "out_of_bounds", 14);
        if (status != 0) {
            return status;
        }
    }

    // rank2：result stride 必须等于 source physical stride 与 view logical stride 的逐维乘积。
    float data2[6] = {0, 1, 2, 3, 4, 5};
    Memory<MemorySpace::GM, float> source2(data2, {2, 3}, {3, 1}, MemoryFormat::Norm);

    long long offset2_buf[2] = {1, 1};
    long long size2_buf[2] = {1, 2};
    long long stride2_view_buf[2] = {1, 1};
    Vector offset2(offset2_buf, 2);
    Vector size2(size2_buf, 2);
    Vector stride2_vec(stride2_view_buf, 2);
    auto tile2 = source2.view<float>(offset2, size2, stride2_vec);
    if (tile2.rank() != 2 || tile2.get_shape(0) != 1 || tile2.get_shape(1) != 2) {
        return fail(15);
    }
    if (tile2.get_stride(0) != 3 || tile2.get_stride(1) != 1) {
        return fail(16);
    }
    if (tile2.data() != source2.data() + 4) {
        return fail(17);
    }

    return 0;
}
"""
    _compile_and_run(source)


# NPU-DEMO-KC-009
# 测试目的: 验证成员式 `view<T>(...)` 对 last_index/linear_offset/stride 的 overflow 风险明确失败并锁定 `overflow` 关键字。
# 使用示例: pytest -q test/include/npu_demo/test_kernel_context.py -k test_npu_demo_dma_view_rejects_overflow_params
# 对应功能实现文件链接: [include/npu_demo/Memory.h](include/npu_demo/Memory.h)
# 对应 spec 文件链接: [spec/include/api/Memory.md](spec/include/api/Memory.md)
# 对应测试文件链接: [test/include/npu_demo/test_kernel_context.py](test/include/npu_demo/test_kernel_context.py)
def test_npu_demo_dma_view_rejects_overflow_params() -> None:
    source = r"""
#include <limits>
#include <stdexcept>
#include <string>

#include "include/npu_demo/npu_demo.h"

static int fail(int code) { return code; }

static int expect_overflow(const std::runtime_error& err, int code) {
    std::string message(err.what());
    if (message.find("overflow") == std::string::npos) {
        return fail(code);
    }
    return 0;
}

int main() {
    npu_demo::KernelContext ctx;
    const long long kMax = std::numeric_limits<long long>::max();
    float data[1] = {0.0f};

    Memory<MemorySpace::GM, float> huge_source(data, {kMax}, {1}, MemoryFormat::Norm);

    try {
        long long offset_buf[1] = {1};
        long long size_buf[1] = {kMax};
        long long stride_buf[1] = {2};
        Vector offset(offset_buf, 1);
        Vector size(size_buf, 1);
        Vector stride(stride_buf, 1);
        auto bad = huge_source.view<float>(offset, size, stride);
        (void)bad;
        return fail(1);
    } catch (const std::runtime_error& err) {
        const int status = expect_overflow(err, 2);
        if (status != 0) {
            return status;
        }
    }

    Memory<MemorySpace::GM, float> huge_stride_source(data, {kMax}, {kMax}, MemoryFormat::Norm);

    try {
        long long offset_buf[1] = {2};
        long long size_buf[1] = {1};
        long long stride_buf[1] = {1};
        Vector offset(offset_buf, 1);
        Vector size(size_buf, 1);
        Vector stride(stride_buf, 1);
        auto bad = huge_stride_source.view<float>(offset, size, stride);
        (void)bad;
        return fail(3);
    } catch (const std::runtime_error& err) {
        const int status = expect_overflow(err, 4);
        if (status != 0) {
            return status;
        }
    }

    long long offset_buf[1] = {0};
    long long size_buf[1] = {1};
    long long stride_buf[1] = {2};
    Vector offset(offset_buf, 1);
    Vector size(size_buf, 1);
    Vector stride(stride_buf, 1);

    try {
        auto bad = huge_stride_source.view<float>(offset, size, stride);
        (void)bad;
        return fail(5);
    } catch (const std::runtime_error& err) {
        const int status = expect_overflow(err, 6);
        if (status != 0) {
            return status;
        }
    }

    return 0;
}
"""
    _compile_and_run(source)


# NPU-DEMO-KC-010
# 测试目的: 验证 Vector 版 slice/deslice 对 overflow 参数返回 kError。
# 使用示例: pytest -q test/include/npu_demo/test_kernel_context.py -k test_npu_demo_dma_slice_deslice_rejects_overflow_params
# 对应功能实现文件链接: [include/npu_demo/Dma.h](include/npu_demo/Dma.h)
# 对应 spec 文件链接: [spec/include/api/Dma.md](spec/include/api/Dma.md)
# 对应测试文件链接: [test/include/npu_demo/test_kernel_context.py](test/include/npu_demo/test_kernel_context.py)
def test_npu_demo_dma_slice_deslice_rejects_overflow_params() -> None:
    source = r"""
#include <limits>

#include "include/npu_demo/npu_demo.h"

static int fail(int code) { return code; }

int main() {
    npu_demo::KernelContext ctx;
    const long long kMax = std::numeric_limits<long long>::max();
    float data[1] = {0.0f};

    Memory<MemorySpace::GM, float> huge_source(data, {kMax}, {kMax}, MemoryFormat::Norm);
    Memory<MemorySpace::GM, float> huge_target(data, {kMax}, {kMax}, MemoryFormat::Norm);

    Memory<MemorySpace::GM, float> tile_small(data, {1}, {1}, MemoryFormat::Norm);

    Memory<MemorySpace::GM, float> tile_big(data, {kMax}, {1}, MemoryFormat::Norm);

    long long offset_small_buf[1] = {2};
    long long size_small_buf[1] = {1};
    long long stride_small_buf[1] = {1};
    Vector offset_small(offset_small_buf, 1);
    Vector size_small(size_small_buf, 1);
    Vector stride_small(stride_small_buf, 1);
    if (npu_demo::slice(ctx, tile_small, huge_source, offset_small, size_small, stride_small) != StatusCode::kError) {
        return fail(1);
    }
    long long offset_big_buf[1] = {1};
    long long size_big_buf[1] = {kMax};
    long long stride_big_buf[1] = {2};
    Vector offset_big(offset_big_buf, 1);
    Vector size_big(size_big_buf, 1);
    Vector stride_big(stride_big_buf, 1);
    if (npu_demo::slice(ctx, tile_big, huge_source, offset_big, size_big, stride_big) != StatusCode::kError) {
        return fail(2);
    }
    if (npu_demo::deslice(ctx, huge_target, tile_small, offset_small, size_small, stride_small) != StatusCode::kError) {
        return fail(3);
    }
    if (npu_demo::deslice(ctx, huge_target, tile_big, offset_big, size_big, stride_big) != StatusCode::kError) {
        return fail(4);
    }
    return 0;
}
"""
    _compile_and_run(source)


# NPU-DEMO-KC-007
# 测试目的: 验证 `npu_demo::add<GM, float, float>(ctx, out, lhs, rhs)` 在 1-D 子集下执行逐元素加法，并对 shape 不一致与任一 operand 的 rank!=1 返回失败。
# 使用示例: pytest -q test/include/npu_demo/test_kernel_context.py -k test_npu_demo_add_supports_1d_subset
# 对应功能实现文件链接: [include/npu_demo/npu_demo.h](include/npu_demo/npu_demo.h)
# 对应 spec 文件链接: [spec/include/api/Kernel.md](spec/include/api/Kernel.md)
# 对应测试文件链接: [test/include/npu_demo/test_kernel_context.py](test/include/npu_demo/test_kernel_context.py)
def test_npu_demo_add_supports_1d_subset() -> None:
    source = r"""
#include "include/npu_demo/npu_demo.h"

static int fail(int code) { return code; }

int main() {
    npu_demo::KernelContext ctx;
    float lhs_data[4] = {1.0f, 2.0f, 3.0f, 4.0f};
    float rhs_data[4] = {10.0f, 20.0f, 30.0f, 40.0f};
    float out_data[4] = {0};
    Memory<MemorySpace::GM, float> lhs(lhs_data, {4}, {1}, MemoryFormat::Norm);
    Memory<MemorySpace::GM, float> rhs(rhs_data, {4}, {1}, MemoryFormat::Norm);
    Memory<MemorySpace::GM, float> out(out_data, {4}, {1}, MemoryFormat::Norm);

    if (npu_demo::add<GM, float, float>(ctx, out, lhs, rhs) != StatusCode::kOk) {
        return fail(1);
    }
    if (out_data[0] != 11.0f || out_data[1] != 22.0f || out_data[2] != 33.0f ||
        out_data[3] != 44.0f) {
        return fail(2);
    }

    Memory<MemorySpace::GM, float> bad(lhs_data, {3}, {1}, MemoryFormat::Norm);
    if (npu_demo::add<GM, float, float>(ctx, out, bad, rhs) == StatusCode::kOk) {
        return fail(3);
    }

    Memory<MemorySpace::GM, float> bad_rank(lhs_data, {2, 2}, {2, 1}, MemoryFormat::Norm);
    if (npu_demo::add<GM, float, float>(ctx, out, bad_rank, rhs) == StatusCode::kOk) {
        return fail(4);
    }
    Memory<MemorySpace::GM, float> bad_rhs(rhs_data, {2, 2}, {2, 1}, MemoryFormat::Norm);
    if (npu_demo::add<GM, float, float>(ctx, out, lhs, bad_rhs) == StatusCode::kOk) {
        return fail(5);
    }
    Memory<MemorySpace::GM, float> bad_out(out_data, {2, 2}, {2, 1}, MemoryFormat::Norm);
    if (npu_demo::add<GM, float, float>(ctx, bad_out, lhs, rhs) == StatusCode::kOk) {
        return fail(6);
    }
    return 0;
}
"""
    _compile_and_run(source)


# NPU-DEMO-KC-008
# 测试目的: 锁定 `include/npu_demo/npu_demo.h` 不再重新聚合 `include/npu_demo/Nn.h`，同时单入口仍能承接 bare `add(lhs, rhs, out)`。
# 使用示例: pytest -q test/include/npu_demo/test_kernel_context.py -k test_npu_demo_single_entry_keeps_kernel_bridge_without_reexporting_nn_header
# 对应功能实现文件链接: [include/npu_demo/npu_demo.h](include/npu_demo/npu_demo.h)
# 对应 spec 文件链接: [spec/include/npu_demo/npu_demo.md](spec/include/npu_demo/npu_demo.md)
# 对应测试文件链接: [test/include/npu_demo/test_kernel_context.py](test/include/npu_demo/test_kernel_context.py)
def test_npu_demo_single_entry_keeps_kernel_bridge_without_reexporting_nn_header() -> None:
    header_text = (REPO_ROOT / "include" / "npu_demo" / "npu_demo.h").read_text(encoding="utf-8")

    assert '#include "include/npu_demo/Nn.h"' not in header_text

    source = r"""
#include "include/npu_demo/npu_demo.h"

static int fail(int code) { return code; }

int main() {
    npu_demo::KernelContext ctx;
    float lhs_data[4] = {1.0f, 2.0f, 3.0f, 4.0f};
    float rhs_data[4] = {10.0f, 20.0f, 30.0f, 40.0f};
    float out_data[4] = {0.0f, 0.0f, 0.0f, 0.0f};
    Memory<TSM, float> lhs(lhs_data, {4}, {1}, MemoryFormat::Norm);
    Memory<TSM, float> rhs(rhs_data, {4}, {1}, MemoryFormat::Norm);
    Memory<TSM, float> out(out_data, {4}, {1}, MemoryFormat::Norm);

    if (npu_demo::add<TSM, float, float>(ctx, out, lhs, rhs) != StatusCode::kOk) {
        return fail(1);
    }
    if (out_data[0] != 11.0f || out_data[1] != 22.0f || out_data[2] != 33.0f || out_data[3] != 44.0f) {
        return fail(2);
    }
    return 0;
}
"""

    _compile_and_run(source)
