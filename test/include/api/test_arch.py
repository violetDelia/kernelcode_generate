"""API Arch compile tests.


功能说明:
- 通过编译并运行 C++ 片段验证 `include/api/Arch.h` 的公开 launch / barrier 接口面，
  并使用 `include/npu_demo/Arch.h` 提供后端实现。

覆盖率信息:
- 当前覆盖率: `N/A`。该链路为 C++ 头文件，按规则豁免 `pytest-cov` 覆盖率统计。
- 达标判定: C++ 头文件实现按规则豁免 `95%` 覆盖率达标线。
- 当前覆盖基线: `API-ARCH-001..003`。

覆盖率命令:
- `pytest -q test/include/api/test_arch.py`
- `N/A`（C++ 头文件实现，按当前规则豁免 `pytest-cov` 覆盖率统计）

使用示例:
- `pytest -q test/include/api/test_arch.py`

关联文件:
- 功能实现: [`include/npu_demo/Arch.h`](include/npu_demo/Arch.h)
- Spec 文档: [`spec/include/api/Arch.md`](spec/include/api/Arch.md)
- 测试文件: [`test/include/api/test_arch.py`](test/include/api/test_arch.py)
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

    使用示例:
    - `_compile_and_run("int main() { return 0; }")`

    关联文件:
    - spec: [`spec/include/api/Arch.md`](spec/include/api/Arch.md)
    - test: [`test/include/api/test_arch.py`](test/include/api/test_arch.py)
    - 功能实现: [`test/include/api/test_arch.py`](test/include/api/test_arch.py)
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        source_path = Path(tmpdir) / "arch_test.cpp"
        binary_path = Path(tmpdir) / "arch_test"
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
    - 使用 `g++` 编译临时源码，并验证其因公开合同违例而编译失败。

    使用示例:
    - `stderr = _compile_expect_failure("int main() { return missing; }")`

    关联文件:
    - spec: [`spec/include/api/Arch.md`](spec/include/api/Arch.md)
    - test: [`test/include/api/test_arch.py`](test/include/api/test_arch.py)
    - 功能实现: [`test/include/api/test_arch.py`](test/include/api/test_arch.py)
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        source_path = Path(tmpdir) / "arch_test_fail.cpp"
        binary_path = Path(tmpdir) / "arch_test_fail"
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


def _compile_only(source: str) -> None:
    """仅编译 C++ 测试片段，不执行链接或运行。


    功能说明:
    - 使用 `g++ -c` 校验 `include/api/Arch.h` 的公开声明是否可被源码侧直接引用。
    - 适用于只暴露接口面、具体实现由私有 include 承接的头文件场景。

    使用示例:
    - `_compile_only("void f();")`

    关联文件:
    - spec: [`spec/include/api/Arch.md`](spec/include/api/Arch.md)
    - test: [`test/include/api/test_arch.py`](test/include/api/test_arch.py)
    - 功能实现: [`include/api/Arch.h`](include/api/Arch.h)
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        source_path = Path(tmpdir) / "arch_test_compile_only.cpp"
        object_path = Path(tmpdir) / "arch_test_compile_only.o"
        source_path.write_text(source, encoding="utf-8")

        compile_result = subprocess.run(
            [
                "g++",
                "-std=c++17",
                "-c",
                "-I",
                str(REPO_ROOT),
                str(source_path),
                "-o",
                str(object_path),
            ],
            check=False,
            capture_output=True,
            text=True,
        )
        if compile_result.returncode != 0:
            raise AssertionError(
                "g++ compile-only failed:\n"
                f"stdout:\n{compile_result.stdout}\n"
                f"stderr:\n{compile_result.stderr}"
            )


# API-ARCH-001
# 测试目的: 验证 `BarrierScope` 与 `launch<block, thread, subthread, shared_memory_size>(callee, args...)` 的公开接口面可配合后端实现编译运行。
# 使用示例: `pytest -q test/include/api/test_arch.py -k test_include_api_arch_exports_public_launch_and_scope_contract`
# 对应功能实现文件路径: `include/npu_demo/Arch.h`
# 对应 spec 文件路径: `spec/include/api/Arch.md`
# 对应测试文件路径: `test/include/api/test_arch.py`
def test_include_api_arch_exports_public_launch_and_scope_contract() -> None:
    source = r"""
#include "include/api/Arch.h"
#include "include/npu_demo/Arch.h"

static int fail(int code) { return code; }

static void kernel_body(npu_demo::KernelContext& ctx, long long* seen_ids, long long* seen_thread_nums) {
    ctx.barrier({BarrierVisibility::TSM, BarrierVisibility::TLM}, BarrierScope::BLOCK);
    const long long tid = thread_id();
    seen_ids[tid] = tid;
    seen_thread_nums[tid] = thread_num();
}

int main() {
    if (BarrierScope::BLOCK == BarrierScope::THREAD) {
        return fail(1);
    }
    if (BarrierScope::THREAD == BarrierScope::SUBTHREAD) {
        return fail(2);
    }
    if (BarrierScope::SUBTHREAD == BarrierScope::GLOBAL) {
        return fail(3);
    }
    if (BarrierVisibility::TSM == BarrierVisibility::TLM) {
        return fail(4);
    }

    long long seen_ids[4] = {-1, -1, -1, -1};
    long long seen_thread_nums[4] = {0, 0, 0, 0};
    Status status = launch<1, 4, 1, 0>(kernel_body, seen_ids, seen_thread_nums);
    if (status != StatusCode::kOk) {
        return fail(5);
    }
    for (long long i = 0; i < 4; ++i) {
        if (seen_ids[i] != i) {
            return fail(6);
        }
        if (seen_thread_nums[i] != 4) {
            return fail(7);
        }
    }
    return 0;
}
"""
    _compile_and_run(source)


# API-ARCH-002
# 测试目的: 验证字符串 callee 不属于公开 launch 合同。
# 使用示例: `pytest -q test/include/api/test_arch.py -k test_include_api_arch_rejects_string_callee_contract`
# 对应功能实现文件路径: `include/npu_demo/Arch.h`
# 对应 spec 文件路径: `spec/include/api/Arch.md`
# 对应测试文件路径: `test/include/api/test_arch.py`
def test_include_api_arch_rejects_string_callee_contract() -> None:
    stderr = _compile_expect_failure(
        r"""
#include "include/api/Arch.h"
#include "include/npu_demo/Arch.h"

int main() {
    return launch<1, 4, 1, 0>("kernel_name");
}
"""
    )
    assert "function object" in stderr
    assert "string" in stderr


# API-ARCH-003
# 测试目的: 验证 `include/api/Arch.h` 仅保留公共声明，不混入 npu_demo 私有实现细节。
# 使用示例: `pytest -q test/include/api/test_arch.py -k test_include_api_arch_keeps_backend_impl_out_of_api_header`
# 对应功能实现文件路径: `include/npu_demo/Arch.h`
# 对应 spec 文件路径: `spec/include/api/Arch.md`
# 对应测试文件路径: `test/include/api/test_arch.py`
def test_include_api_arch_keeps_backend_impl_out_of_api_header() -> None:
    header = (REPO_ROOT / "include" / "api" / "Arch.h").read_text(encoding="utf-8")

    assert "enum class BarrierVisibility" in header
    assert "enum class BarrierScope" in header
    assert "class KernelContext" in header
    assert "virtual long long thread_id() const = 0;" in header
    assert "virtual long long thread_num() const = 0;" in header
    assert "S_INT thread_id();" in header
    assert "S_INT thread_num();" in header
    assert "std::initializer_list<BarrierVisibility> visibility" in header
    assert "BarrierScope scope" in header
    assert "Memory<Space, T> get_dynamic_memory() const;" in header
    assert "class DynamicMemoryRef" in header
    assert "DynamicMemoryRef<Space> get_dynamic_memory();" in header
    assert "SUBTHREAD" in header
    assert "GLOBAL" in header
    assert "Status launch" in header
    assert "namespace npu_demo" not in header
    assert "std::thread" not in header
    assert "condition_variable" not in header
    assert "kThreadCapability" not in header


# API-ARCH-004
# 测试目的: 验证 npu_demo KernelContext 已暴露 TLM1/TLM2/TLM3 三块动态内存视图，且容量与公开合同一致。
# 使用示例: `pytest -q test/include/api/test_arch.py -k test_include_api_arch_exposes_tlm123_dynamic_memory_contract`
# 对应功能实现文件路径: `include/npu_demo/Arch.h`
# 对应 spec 文件路径: `spec/include/api/Arch.md`
# 对应测试文件路径: `test/include/api/test_arch.py`
def test_include_api_arch_exposes_tlm123_dynamic_memory_contract() -> None:
    source = r"""
#include "include/api/Arch.h"
#include "include/npu_demo/Arch.h"

static int fail(int code) { return code; }

int main() {
    Memory<TLM1, float> tlm1 = get_dynamic_memory<TLM1>();
    Memory<TLM2, float> tlm2 = get_dynamic_memory<TLM2>();
    Memory<TLM3, float> tlm3 = get_dynamic_memory<TLM3>();

    if (tlm1.rank() != 1 || tlm1.shape()[0] != 524288 || tlm1.stride()[0] != 1 || tlm1.space() != MemorySpace::TLM1) {
        return fail(1);
    }
    if (tlm2.rank() != 1 || tlm2.shape()[0] != 1048576 || tlm2.stride()[0] != 1 || tlm2.space() != MemorySpace::TLM2) {
        return fail(2);
    }
    if (tlm3.rank() != 1 || tlm3.shape()[0] != 1048576 || tlm3.stride()[0] != 1 || tlm3.space() != MemorySpace::TLM3) {
        return fail(3);
    }
    return 0;
}
"""
    _compile_and_run(source)


# API-ARCH-005
# 测试目的: 验证 `include/api/Arch.h` 已显式声明抽象 `KernelContext` 接口面，且源码侧可在不引入后端实现的前提下引用这些公开声明。
# 使用示例: `pytest -q test/include/api/test_arch.py -k test_include_api_arch_declares_public_kernel_context_surface`
# 对应功能实现文件路径: `include/api/Arch.h`
# 对应 spec 文件路径: `spec/include/api/Arch.md`
# 对应测试文件路径: `test/include/api/test_arch.py`
def test_include_api_arch_declares_public_kernel_context_surface() -> None:
    source = r"""
#include <type_traits>

#include "include/api/Arch.h"

static_assert(std::is_abstract<KernelContext>::value, "KernelContext must stay abstract in include/api");

void inspect(KernelContext& ctx) {
    (void)ctx.thread_id();
    (void)ctx.thread_num();
    ctx.barrier({BarrierVisibility::TSM, BarrierVisibility::TLM}, BarrierScope::BLOCK);
    (void)thread_id();
    (void)thread_num();
    (void)get_dynamic_memory<TSM>();
}
"""
    _compile_only(source)
