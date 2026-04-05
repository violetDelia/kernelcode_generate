"""API Arch compile tests.

创建者: 小李飞刀
最后一次更改: 小李飞刀

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

    创建者: 小李飞刀
    最后一次更改: 小李飞刀

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

    创建者: 小李飞刀
    最后一次更改: 小李飞刀

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


# API-ARCH-001
# 创建者: 小李飞刀
# 最后一次更改: 小李飞刀
# 最近一次运行测试时间: 2026-04-06 06:05:00 +0800
# 最近一次运行成功时间: 2026-04-06 06:05:00 +0800
# 测试目的: 验证 `BarrierScope` 与 `launch<block, thread, subthread>(callee, args...)` 的公开接口面可配合后端实现编译运行。
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
    const long long tid = ctx.thread_id();
    seen_ids[tid] = tid;
    seen_thread_nums[tid] = ctx.thread_num();
}

int main() {
    if (BarrierScope::BLOCK == BarrierScope::THREAD) {
        return fail(1);
    }

    long long seen_ids[4] = {-1, -1, -1, -1};
    long long seen_thread_nums[4] = {0, 0, 0, 0};
    Status status = launch<1, 4, 1>(kernel_body, seen_ids, seen_thread_nums);
    if (status != StatusCode::kOk) {
        return fail(2);
    }
    for (long long i = 0; i < 4; ++i) {
        if (seen_ids[i] != i) {
            return fail(3);
        }
        if (seen_thread_nums[i] != 4) {
            return fail(4);
        }
    }
    return 0;
}
"""
    _compile_and_run(source)


# API-ARCH-002
# 创建者: 小李飞刀
# 最后一次更改: 小李飞刀
# 最近一次运行测试时间: 2026-04-06 06:05:00 +0800
# 最近一次运行成功时间: 2026-04-06 06:05:00 +0800
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
    return launch<1, 4, 1>("kernel_name");
}
"""
    )
    assert "function object" in stderr
    assert "string" in stderr


# API-ARCH-003
# 创建者: 小李飞刀
# 最后一次更改: 小李飞刀
# 最近一次运行测试时间: 2026-04-06 06:05:00 +0800
# 最近一次运行成功时间: 2026-04-06 06:05:00 +0800
# 测试目的: 验证 `include/api/Arch.h` 仅保留公共声明，不混入 npu_demo 私有实现细节。
# 使用示例: `pytest -q test/include/api/test_arch.py -k test_include_api_arch_keeps_backend_impl_out_of_api_header`
# 对应功能实现文件路径: `include/npu_demo/Arch.h`
# 对应 spec 文件路径: `spec/include/api/Arch.md`
# 对应测试文件路径: `test/include/api/test_arch.py`
def test_include_api_arch_keeps_backend_impl_out_of_api_header() -> None:
    header = (REPO_ROOT / "include" / "api" / "Arch.h").read_text(encoding="utf-8")

    assert "enum class BarrierScope" in header
    assert "Status launch" in header
    assert "namespace npu_demo" not in header
    assert "std::thread" not in header
    assert "condition_variable" not in header
    assert "kThreadCapability" not in header
