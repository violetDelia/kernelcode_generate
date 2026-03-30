"""NPU demo KernelContext include tests.

创建者: 朽木露琪亚
最后一次更改: jcc你莫辜负

功能说明:
- 通过编译并运行 C++ 片段验证 `include/npu_demo/npu_demo.h` 的 `KernelContext` accessor 与动态内存查询契约。

覆盖率信息:
- 当前覆盖率: `N/A`。该链路的功能实现为 C++ 头文件，按当前规则豁免 `pytest-cov` 覆盖率统计。
- 达标判定: C++ 头文件实现按规则豁免 `95%` 覆盖率达标线。
- 当前覆盖基线: `NPU-DEMO-KC-001..006`。

覆盖率命令:
- `pytest -q test/include/npu_demo/test_kernel_context.py`
- `N/A`（C++ 头文件实现，按当前规则豁免 `pytest-cov` 覆盖率统计）

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
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]


def _compile_and_run(source: str) -> None:
    """编译并运行 C++ 测试片段。

    创建者: 朽木露琪亚
    最后一次更改: 朽木露琪亚

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


# NPU-DEMO-KC-001
# 创建者: 朽木露琪亚
# 最后一次更改: 朽木露琪亚
# 测试目的: 验证 KernelContext 的 block/thread/subthread id 与 count accessor 返回固定模板值。
# 使用示例: pytest -q test/include/npu_demo/test_kernel_context.py -k test_npu_demo_kernel_context_exposes_id_and_count_accessors
# 对应功能实现文件链接: [include/npu_demo/npu_demo.h](include/npu_demo/npu_demo.h)
# 对应 spec 文件链接: [spec/include/npu_demo/npu_demo.md](spec/include/npu_demo/npu_demo.md)
# 对应测试文件链接: [test/include/npu_demo/test_kernel_context.py](test/include/npu_demo/test_kernel_context.py)
def test_npu_demo_kernel_context_exposes_id_and_count_accessors() -> None:
    source = r"""
#include "include/npu_demo/npu_demo.h"

static int fail(int code) { return code; }

int main() {
    npu_demo::KernelContext ctx;

    if (ctx.block_id() != 1) {
        return fail(1);
    }
    if (ctx.block_num() != 6) {
        return fail(2);
    }
    if (ctx.thread_id() != 3) {
        return fail(3);
    }
    if (ctx.thread_num() != 8) {
        return fail(4);
    }
    if (ctx.subthread_id() != 0) {
        return fail(5);
    }
    if (ctx.subthread_num() != 1) {
        return fail(6);
    }
    return 0;
}
"""
    _compile_and_run(source)


# NPU-DEMO-KC-002
# 创建者: 朽木露琪亚
# 最后一次更改: 朽木露琪亚
# 测试目的: 验证 get_dynamic_memory<float>(TSM) 返回固定 shape/stride/space 的 Memory 视图。
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
    auto mem = ctx.get_dynamic_memory<float>(npu_demo::MemorySpace::TSM);

    if (mem.rank() != 1) {
        return fail(1);
    }
    if (mem.shape()[0] != 24576) {
        return fail(2);
    }
    if (mem.stride()[0] != 1) {
        return fail(3);
    }
    if (mem.space() != npu_demo::MemorySpace::TSM) {
        return fail(4);
    }
    return 0;
}
"""
    _compile_and_run(source)


# NPU-DEMO-KC-003
# 创建者: 朽木露琪亚
# 最后一次更改: 朽木露琪亚
# 测试目的: 验证 get_dynamic_memory<float>(TLM) 返回固定 shape/stride/space 的 Memory 视图。
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
    auto mem = ctx.get_dynamic_memory<float>(npu_demo::MemorySpace::TLM);

    if (mem.rank() != 1) {
        return fail(1);
    }
    if (mem.shape()[0] != 2048) {
        return fail(2);
    }
    if (mem.stride()[0] != 1) {
        return fail(3);
    }
    if (mem.space() != npu_demo::MemorySpace::TLM) {
        return fail(4);
    }
    return 0;
}
"""
    _compile_and_run(source)


# NPU-DEMO-KC-004
# 创建者: 朽木露琪亚
# 最后一次更改: 朽木露琪亚
# 测试目的: 验证 get_dynamic_memory<float>(SM) 在 sm_memory_size=0 时抛出带关键字的运行期错误。
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
        auto mem = ctx.get_dynamic_memory<float>(npu_demo::MemorySpace::SM);
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
# 最后一次更改: 朽木露琪亚
# 测试目的: 验证 get_dynamic_memory<float>(LM) 在 lm_memory_size=0 时抛出带关键字的运行期错误。
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
        auto mem = ctx.get_dynamic_memory<float>(npu_demo::MemorySpace::LM);
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


# NPU-DEMO-KC-006
# 创建者: jcc你莫辜负
# 最后一次更改: jcc你莫辜负
# 测试目的: 验证 get_dynamic_memory<float>(GM) 对非法 MemorySpace 抛出 invalid_argument 且消息包含关键字。
# 使用示例: pytest -q test/include/npu_demo/test_kernel_context.py -k test_npu_demo_kernel_context_rejects_invalid_memory_space
# 对应功能实现文件链接: [include/npu_demo/npu_demo.h](include/npu_demo/npu_demo.h)
# 对应 spec 文件链接: [spec/include/npu_demo/npu_demo.md](spec/include/npu_demo/npu_demo.md)
# 对应测试文件链接: [test/include/npu_demo/test_kernel_context.py](test/include/npu_demo/test_kernel_context.py)
def test_npu_demo_kernel_context_rejects_invalid_memory_space() -> None:
    source = r"""
#include <stdexcept>
#include <string>

#include "include/npu_demo/npu_demo.h"

static int fail(int code) { return code; }

int main() {
    npu_demo::KernelContext ctx;
    try {
        auto mem = ctx.get_dynamic_memory<float>(npu_demo::MemorySpace::GM);
        (void)mem;
        return fail(1);
    } catch (const std::invalid_argument& err) {
        std::string message(err.what());
        if (message.find("requires on-chip MemorySpace") == std::string::npos) {
            return fail(2);
        }
        return 0;
    } catch (...) {
        return fail(3);
    }
}
"""
    _compile_and_run(source)
