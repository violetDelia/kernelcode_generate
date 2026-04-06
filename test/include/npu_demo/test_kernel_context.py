"""NPU demo KernelContext include tests.

创建者: 朽木露琪亚
最后一次更改: 金铲铲大作战
最后修改人: 金铲铲大作战
最近一次运行测试时间: 2026-04-05 16:05:57 +0800
最近一次运行成功时间: 2026-04-05 16:05:57 +0800

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

    创建者: 朽木露琪亚
    最后一次更改: 金铲铲大作战
    最后修改人: 金铲铲大作战

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


# NPU-DEMO-KC-001
# 创建者: 朽木露琪亚
# 最后一次更改: 小李飞刀
# 最后修改人: 小李飞刀
# 最近一次运行测试时间: 2026-04-06 06:05:00 +0800
# 最近一次运行成功时间: 2026-04-06 06:05:00 +0800
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
    long long* block_nums,
    long long* thread_ids,
    long long* thread_nums,
    long long* subthread_ids,
    long long* subthread_nums) {
    const long long tid = ctx.thread_id();
    block_ids[tid] = ctx.block_id();
    block_nums[tid] = ctx.block_num();
    thread_ids[tid] = ctx.thread_id();
    thread_nums[tid] = ctx.thread_num();
    subthread_ids[tid] = ctx.subthread_id();
    subthread_nums[tid] = ctx.subthread_num();
}

int main() {
    long long block_ids[4] = {-1, -1, -1, -1};
    long long block_nums[4] = {0, 0, 0, 0};
    long long thread_ids[4] = {-1, -1, -1, -1};
    long long thread_nums[4] = {0, 0, 0, 0};
    long long subthread_ids[4] = {-1, -1, -1, -1};
    long long subthread_nums[4] = {0, 0, 0, 0};

    if (npu_demo::launch<1, 4, 1>(
            kernel_body,
            block_ids,
            block_nums,
            thread_ids,
            thread_nums,
            subthread_ids,
            subthread_nums)
        != StatusCode::kOk) {
        return fail(1);
    }

    for (long long i = 0; i < 4; ++i) {
        if (block_ids[i] != 0) {
            return fail(2);
        }
        if (block_nums[i] != 1) {
            return fail(3);
        }
        if (thread_ids[i] != i) {
            return fail(4);
        }
        if (thread_nums[i] != 4) {
            return fail(5);
        }
        if (subthread_ids[i] != 0) {
            return fail(6);
        }
        if (subthread_nums[i] != 1) {
            return fail(7);
        }
    }
    return 0;
}
"""
    _compile_and_run(source)


# NPU-DEMO-KC-001A
# 创建者: 小李飞刀
# 最后一次更改: 小李飞刀
# 最后修改人: 小李飞刀
# 最近一次运行测试时间: 2026-04-06 06:05:00 +0800
# 最近一次运行成功时间: 2026-04-06 06:05:00 +0800
# 测试目的: 验证 KernelContext::barrier 需要显式 visibility / scope，且只接受 {TSM, TLM} + BLOCK。
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
    ctx.barrier({MemorySpace::TLM, MemorySpace::TSM}, BarrierScope::BLOCK);
    if (ctx.thread_id() != 0) {
        return;
    }

    try {
        ctx.barrier({}, BarrierScope::BLOCK);
        *result_code = 1;
        return;
    } catch (const std::invalid_argument& err) {
        if (!contains(err.what(), "visibility")) {
            *result_code = 2;
            return;
        }
    }

    try {
        ctx.barrier({MemorySpace::TSM}, BarrierScope::BLOCK);
        *result_code = 3;
        return;
    } catch (const std::invalid_argument& err) {
        if (!contains(err.what(), "TSM") || !contains(err.what(), "TLM")) {
            *result_code = 4;
            return;
        }
    }

    try {
        ctx.barrier({MemorySpace::TSM, MemorySpace::TSM}, BarrierScope::BLOCK);
        *result_code = 5;
        return;
    } catch (const std::invalid_argument& err) {
        if (!contains(err.what(), "exactly once")) {
            *result_code = 6;
            return;
        }
    }

    try {
        ctx.barrier({MemorySpace::TSM, MemorySpace::GM}, BarrierScope::BLOCK);
        *result_code = 7;
        return;
    } catch (const std::invalid_argument& err) {
        if (!contains(err.what(), "visibility")) {
            *result_code = 8;
            return;
        }
    }

    try {
        ctx.barrier({MemorySpace::TSM, MemorySpace::TLM}, BarrierScope::THREAD);
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
    int result_code = 99;
    if (npu_demo::launch<1, 2, 1>(kernel_body, &result_code) != StatusCode::kOk) {
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
# 创建者: 小李飞刀
# 最后一次更改: 小李飞刀
# 最后修改人: 小李飞刀
# 最近一次运行测试时间: 2026-04-06 06:05:00 +0800
# 最近一次运行成功时间: 2026-04-06 06:05:00 +0800
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
    if (npu_demo::launch<1, 2, 1>(noop) != StatusCode::kOk) {
        return fail(1);
    }
    if (npu_demo::launch<2, 2, 1>(noop) != StatusCode::kError) {
        return fail(2);
    }
    if (npu_demo::launch<1, 1, 1>(noop) != StatusCode::kError) {
        return fail(3);
    }
    if (npu_demo::launch<1, 9, 1>(noop) != StatusCode::kError) {
        return fail(4);
    }
    if (npu_demo::launch<1, 2, 2>(noop) != StatusCode::kError) {
        return fail(5);
    }
    return 0;
}
"""
    _compile_and_run(source)


# NPU-DEMO-KC-002
# 创建者: 朽木露琪亚
# 最后一次更改: 金铲铲大作战
# 最后修改人: 金铲铲大作战
# 最近一次运行测试时间: 2026-04-05 10:44:47 +0800
# 最近一次运行成功时间: 2026-04-05 10:44:47 +0800
# 测试目的: 验证 get_dynamic_memory<TSM, float>() 返回固定 shape/stride/space 的 Memory 视图。
# 使用示例: pytest -q test/include/npu_demo/test_kernel_context.py -k test_npu_demo_kernel_context_returns_typed_tsm_memory
# 对应功能实现文件链接: [include/npu_demo/npu_demo.h](include/npu_demo/npu_demo.h)
# 对应 spec 文件链接: [spec/include/npu_demo/npu_demo.md](spec/include/npu_demo/npu_demo.md)
# 对应测试文件链接: [test/include/npu_demo/test_kernel_context.py](test/include/npu_demo/test_kernel_context.py)
def test_npu_demo_kernel_context_returns_typed_tsm_memory() -> None:
    source = r"""
#include "include/npu_demo/npu_demo.h"

static int fail(int code) { return code; }

int main() {
    npu_demo::KernelContext ctx;
    auto mem = ctx.get_dynamic_memory<TSM, float>();

    if (mem.rank() != 1) {
        return fail(1);
    }
    if (mem.shape()[0] != 24576) {
        return fail(2);
    }
    if (mem.stride()[0] != 1) {
        return fail(3);
    }
    if (mem.space() != MemorySpace::TSM) {
        return fail(4);
    }
    return 0;
}
"""
    _compile_and_run(source)


# NPU-DEMO-KC-003
# 创建者: 朽木露琪亚
# 最后一次更改: 金铲铲大作战
# 最后修改人: 金铲铲大作战
# 最近一次运行测试时间: 2026-04-05 10:44:47 +0800
# 最近一次运行成功时间: 2026-04-05 10:44:47 +0800
# 测试目的: 验证 get_dynamic_memory<TLM, float>() 返回固定 shape/stride/space 的 Memory 视图。
# 使用示例: pytest -q test/include/npu_demo/test_kernel_context.py -k test_npu_demo_kernel_context_returns_typed_tlm_memory
# 对应功能实现文件链接: [include/npu_demo/npu_demo.h](include/npu_demo/npu_demo.h)
# 对应 spec 文件链接: [spec/include/npu_demo/npu_demo.md](spec/include/npu_demo/npu_demo.md)
# 对应测试文件链接: [test/include/npu_demo/test_kernel_context.py](test/include/npu_demo/test_kernel_context.py)
def test_npu_demo_kernel_context_returns_typed_tlm_memory() -> None:
    source = r"""
#include "include/npu_demo/npu_demo.h"

static int fail(int code) { return code; }

int main() {
    npu_demo::KernelContext ctx;
    auto mem = ctx.get_dynamic_memory<TLM, float>();

    if (mem.rank() != 1) {
        return fail(1);
    }
    if (mem.shape()[0] != 2048) {
        return fail(2);
    }
    if (mem.stride()[0] != 1) {
        return fail(3);
    }
    if (mem.space() != MemorySpace::TLM) {
        return fail(4);
    }
    return 0;
}
"""
    _compile_and_run(source)


# NPU-DEMO-KC-004
# 创建者: 朽木露琪亚
# 最后一次更改: 金铲铲大作战
# 最后修改人: 金铲铲大作战
# 最近一次运行测试时间: 2026-04-05 10:44:47 +0800
# 最近一次运行成功时间: 2026-04-05 10:44:47 +0800
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
    npu_demo::KernelContext ctx;
    try {
        auto mem = ctx.get_dynamic_memory<SM, float>();
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
# 创建者: 朽木露琪亚
# 最后一次更改: 金铲铲大作战
# 最后修改人: 金铲铲大作战
# 最近一次运行测试时间: 2026-04-05 10:44:47 +0800
# 最近一次运行成功时间: 2026-04-05 10:44:47 +0800
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
    npu_demo::KernelContext ctx;
    try {
        auto mem = ctx.get_dynamic_memory<LM, float>();
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
# 创建者: 金铲铲大作战
# 最后一次更改: 金铲铲大作战
# 最后修改人: 金铲铲大作战
# 最近一次运行测试时间: N/A
# 最近一次运行成功时间: N/A
# 测试目的: 验证 get_dynamic_memory 模板空间入口的成功与失败路径可编译并返回稳定结果。
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
    npu_demo::KernelContext ctx;
    auto tsm = ctx.get_dynamic_memory<TSM, float>();
    if (tsm.rank() != 1 || tsm.shape()[0] != 24576 || tsm.stride()[0] != 1 || tsm.space() != MemorySpace::TSM) {
        return fail(1);
    }

    auto tlm = ctx.get_dynamic_memory<TLM, float>();
    if (tlm.rank() != 1 || tlm.shape()[0] != 2048 || tlm.stride()[0] != 1 || tlm.space() != MemorySpace::TLM) {
        return fail(2);
    }

    try {
        auto sm = ctx.get_dynamic_memory<SM, float>();
        (void)sm;
        return fail(3);
    } catch (const std::runtime_error& err) {
        if (!contains(err.what(), "sm_memory_size=0")) {
            return fail(4);
        }
    } catch (...) {
        return fail(5);
    }

    try {
        auto lm = ctx.get_dynamic_memory<LM, float>();
        (void)lm;
        return fail(6);
    } catch (const std::runtime_error& err) {
        if (!contains(err.what(), "lm_memory_size=0")) {
            return fail(7);
        }
    } catch (...) {
        return fail(8);
    }
    return 0;
}
"""
    _compile_and_run(source)


# NPU-DEMO-KC-006
# 创建者: 金铲铲大作战
# 最后一次更改: 金铲铲大作战
# 最后修改人: 金铲铲大作战
# 最近一次运行测试时间: 2026-04-05 10:44:47 +0800
# 最近一次运行成功时间: 2026-04-05 10:44:47 +0800
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
    float data[10];
    for (int i = 0; i < 10; ++i) {
        data[i] = static_cast<float>(i);
    }
    long long shape[1] = {10};
    long long stride[1] = {1};
    Memory<MemorySpace::GM, float> source(data, shape, stride, 1, MemoryFormat::Norm);

    long long offset_buf[1] = {1};
    long long size_buf[1] = {4};
    long long stride_buf[1] = {2};
    Vector offset(offset_buf, 1);
    Vector size(size_buf, 1);
    Vector stride_vec(stride_buf, 1);

    auto sub = view(source, offset, size, stride_vec);
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
    Memory<MemorySpace::TSM, float> tile(tile_data, tile_shape, tile_stride, 1, MemoryFormat::Norm);
    if (slice(tile, source, offset, size, stride_vec) != StatusCode::kOk) {
        return fail(4);
    }
    if (tile_data[0] != 1.0f || tile_data[1] != 3.0f || tile_data[2] != 5.0f || tile_data[3] != 7.0f) {
        return fail(5);
    }

    float target_data[10] = {0};
    Memory<MemorySpace::GM, float> target(target_data, shape, stride, 1, MemoryFormat::Norm);
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


# NPU-DEMO-KC-008
# 创建者: 金铲铲大作战
# 最后一次更改: 金铲铲大作战
# 最后修改人: 金铲铲大作战
# 测试目的: 验证 view 在 1-D 子集下对非法 offset/size/stride、越界与 rank!=1 明确失败（抛出 runtime_error 并携带关键字）。
# 使用示例: pytest -q test/include/npu_demo/test_kernel_context.py -k test_npu_demo_dma_view_rejects_invalid_params
# 对应功能实现文件链接: [include/npu_demo/Dma.h](include/npu_demo/Dma.h)
# 对应 spec 文件链接: [spec/include/api/Dma.md](spec/include/api/Dma.md)
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
    long long shape[1] = {10};
    long long stride[1] = {1};
    Memory<MemorySpace::GM, float> source(data, shape, stride, 1, MemoryFormat::Norm);

    // 标量参数：非法 offset/size/stride 与越界。
    try {
        auto bad = view(source, -1, 4, 1);
        (void)bad;
        return fail(1);
    } catch (const std::runtime_error& err) {
        const int status = expect_runtime_error_contains(err, "dma.view", 2);
        if (status != 0) {
            return status;
        }
    }

    try {
        auto bad = view(source, 0, 0, 1);
        (void)bad;
        return fail(3);
    } catch (const std::runtime_error& err) {
        const int status = expect_runtime_error_contains(err, "invalid offset/size/stride", 4);
        if (status != 0) {
            return status;
        }
    }

    try {
        auto bad = view(source, 0, 4, 0);
        (void)bad;
        return fail(5);
    } catch (const std::runtime_error& err) {
        const int status = expect_runtime_error_contains(err, "invalid offset/size/stride", 6);
        if (status != 0) {
            return status;
        }
    }

    try {
        auto bad = view(source, 9, 2, 1);
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
        auto bad = view(source, offset_bad_rank, size_bad_rank, stride_bad_rank);
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
        auto bad = view(source, offset_neg, size_ok, stride_ok);
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
        auto bad = view(source, offset_oob, size_oob, stride_ok);
        (void)bad;
        return fail(13);
    } catch (const std::runtime_error& err) {
        const int status = expect_runtime_error_contains(err, "out_of_bounds", 14);
        if (status != 0) {
            return status;
        }
    }

    // rank!=1：1-D 子集实现必须明确拒绝。
    float data2[6] = {0};
    long long shape2[2] = {2, 3};
    long long stride2[2] = {3, 1};
    Memory<MemorySpace::GM, float> source2(data2, shape2, stride2, 2, MemoryFormat::Norm);

    try {
        auto bad = view(source2, 0, 1, 1);
        (void)bad;
        return fail(15);
    } catch (const std::runtime_error& err) {
        const int status = expect_runtime_error_contains(err, "rank!=1", 16);
        if (status != 0) {
            return status;
        }
    }

    Vector offset2(offset_bad_rank_buf, 2);
    Vector size2(size_bad_rank_buf, 2);
    Vector stride2_vec(stride_bad_rank_buf, 2);
    try {
        auto bad = view(source2, offset2, size2, stride2_vec);
        (void)bad;
        return fail(17);
    } catch (const std::runtime_error& err) {
        const int status = expect_runtime_error_contains(err, "rank!=1", 18);
        if (status != 0) {
            return status;
        }
    }

    return 0;
}
"""
    _compile_and_run(source)


# NPU-DEMO-KC-009
# 创建者: 金铲铲大作战
# 最后一次更改: 金铲铲大作战
# 最后修改人: 金铲铲大作战
# 测试目的: 验证 view 对 last_index/linear_offset/stride 的 overflow 风险明确失败并锁定 `overflow` 关键字。
# 使用示例: pytest -q test/include/npu_demo/test_kernel_context.py -k test_npu_demo_dma_view_rejects_overflow_params
# 对应功能实现文件链接: [include/npu_demo/Dma.h](include/npu_demo/Dma.h)
# 对应 spec 文件链接: [spec/include/api/Dma.md](spec/include/api/Dma.md)
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
    const long long kMax = std::numeric_limits<long long>::max();
    float data[1] = {0.0f};

    long long huge_shape[1] = {kMax};
    long long unit_stride[1] = {1};
    Memory<MemorySpace::GM, float> huge_source(data, huge_shape, unit_stride, 1, MemoryFormat::Norm);

    try {
        auto bad = view(huge_source, 1, kMax, 2);
        (void)bad;
        return fail(1);
    } catch (const std::runtime_error& err) {
        const int status = expect_overflow(err, 2);
        if (status != 0) {
            return status;
        }
    }

    long long huge_stride[1] = {kMax};
    Memory<MemorySpace::GM, float> huge_stride_source(data, huge_shape, huge_stride, 1, MemoryFormat::Norm);

    try {
        auto bad = view(huge_stride_source, 2, 1, 1);
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
        auto bad = view(huge_stride_source, offset, size, stride);
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
# 创建者: 金铲铲大作战
# 最后一次更改: 金铲铲大作战
# 最后修改人: 金铲铲大作战
# 测试目的: 验证 slice/deslice 对 overflow 参数返回 kError。
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
    const long long kMax = std::numeric_limits<long long>::max();
    float data[1] = {0.0f};

    long long huge_shape[1] = {kMax};
    long long huge_stride[1] = {kMax};
    Memory<MemorySpace::GM, float> huge_source(data, huge_shape, huge_stride, 1, MemoryFormat::Norm);
    Memory<MemorySpace::GM, float> huge_target(data, huge_shape, huge_stride, 1, MemoryFormat::Norm);

    long long tile_small_shape[1] = {1};
    long long tile_small_stride[1] = {1};
    Memory<MemorySpace::GM, float> tile_small(data, tile_small_shape, tile_small_stride, 1, MemoryFormat::Norm);

    long long tile_big_shape[1] = {kMax};
    long long tile_big_stride[1] = {1};
    Memory<MemorySpace::GM, float> tile_big(data, tile_big_shape, tile_big_stride, 1, MemoryFormat::Norm);

    if (slice(tile_small, huge_source, 2, 1, 1) != StatusCode::kError) {
        return fail(1);
    }
    if (slice(tile_big, huge_source, 1, kMax, 2) != StatusCode::kError) {
        return fail(2);
    }
    if (deslice(tile_small, huge_target, 2, 1, 1) != StatusCode::kError) {
        return fail(3);
    }
    if (deslice(tile_big, huge_target, 1, kMax, 2) != StatusCode::kError) {
        return fail(4);
    }
    return 0;
}
"""
    _compile_and_run(source)


# NPU-DEMO-KC-007
# 创建者: 金铲铲大作战
# 最后一次更改: jcc你莫辜负
# 最后修改人: jcc你莫辜负
# 最近一次运行测试时间: 2026-04-05 16:05:57 +0800
# 最近一次运行成功时间: 2026-04-05 16:05:57 +0800
# 测试目的: 验证 add 在 1-D 子集下执行逐元素加法，并对 shape 不一致与任一 operand 的 rank!=1 返回失败。
# 使用示例: pytest -q test/include/npu_demo/test_kernel_context.py -k test_npu_demo_add_supports_1d_subset
# 对应功能实现文件链接: [include/npu_demo/npu_demo.h](include/npu_demo/npu_demo.h)
# 对应 spec 文件链接: [spec/include/api/Nn.md](spec/include/api/Nn.md)
# 对应测试文件链接: [test/include/npu_demo/test_kernel_context.py](test/include/npu_demo/test_kernel_context.py)
def test_npu_demo_add_supports_1d_subset() -> None:
    source = r"""
#include "include/npu_demo/npu_demo.h"

static int fail(int code) { return code; }

int main() {
    float lhs_data[4] = {1.0f, 2.0f, 3.0f, 4.0f};
    float rhs_data[4] = {10.0f, 20.0f, 30.0f, 40.0f};
    float out_data[4] = {0};
    long long shape[1] = {4};
    long long stride[1] = {1};
    Memory<MemorySpace::GM, float> lhs(lhs_data, shape, stride, 1, MemoryFormat::Norm);
    Memory<MemorySpace::GM, float> rhs(rhs_data, shape, stride, 1, MemoryFormat::Norm);
    Memory<MemorySpace::GM, float> out(out_data, shape, stride, 1, MemoryFormat::Norm);

    if (add(lhs, rhs, out) != StatusCode::kOk) {
        return fail(1);
    }
    if (out_data[0] != 11.0f || out_data[1] != 22.0f || out_data[2] != 33.0f ||
        out_data[3] != 44.0f) {
        return fail(2);
    }

    long long bad_shape[1] = {3};
    Memory<MemorySpace::GM, float> bad(lhs_data, bad_shape, stride, 1, MemoryFormat::Norm);
    if (add(bad, rhs, out) == StatusCode::kOk) {
        return fail(3);
    }

    long long rank2_shape[2] = {2, 2};
    long long rank2_stride[2] = {2, 1};
    Memory<MemorySpace::GM, float> bad_rank(lhs_data, rank2_shape, rank2_stride, 2, MemoryFormat::Norm);
    if (add(bad_rank, rhs, out) == StatusCode::kOk) {
        return fail(4);
    }
    Memory<MemorySpace::GM, float> bad_rhs(rhs_data, rank2_shape, rank2_stride, 2, MemoryFormat::Norm);
    if (add(lhs, bad_rhs, out) == StatusCode::kOk) {
        return fail(5);
    }
    Memory<MemorySpace::GM, float> bad_out(out_data, rank2_shape, rank2_stride, 2, MemoryFormat::Norm);
    if (add(lhs, rhs, bad_out) == StatusCode::kOk) {
        return fail(6);
    }
    return 0;
}
"""
    _compile_and_run(source)
