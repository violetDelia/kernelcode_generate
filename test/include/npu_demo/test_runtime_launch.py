"""NPU demo runtime launch tests.


功能说明:
- 通过编译并运行 C++ 片段验证 `npu_demo::launch<1, 4, 1, 0>` 的运行时行为：
  - 必须真实启动 `4` 个线程（禁止 for-loop 串行模拟）。
  - 同一次 launch 的 `KernelContext::barrier(...)` 必须共享同一 barrier 状态并能真实汇合。
  - `thread_id()` / `thread_num()` 返回值必须与 launch extent 一致。

使用示例:
- pytest -q test/include/npu_demo/test_runtime_launch.py

关联文件:
- spec: [spec/include/npu_demo/npu_demo.md](spec/include/npu_demo/npu_demo.md)
- test: [test/include/npu_demo/test_runtime_launch.py](test/include/npu_demo/test_runtime_launch.py)
- 功能实现: [include/npu_demo/Arch.h](include/npu_demo/Arch.h)
"""

from __future__ import annotations

import subprocess
import tempfile
import time
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]


def _compile_and_run(source: str, *, timeout_s: float = 5.0) -> None:
    """编译并运行 C++ 测试片段（带超时保护）。


    功能说明:
    - 使用 `g++ -std=c++17 -pthread` 编译临时源码并执行生成程序。
    - 通过 `timeout` 防止 barrier/launch 实现错误导致测试死锁。

    使用示例:
    - _compile_and_run("int main() { return 0; }")

    关联文件:
    - spec: [spec/include/npu_demo/npu_demo.md](spec/include/npu_demo/npu_demo.md)
    - test: [test/include/npu_demo/test_runtime_launch.py](test/include/npu_demo/test_runtime_launch.py)
    - 功能实现: [test/include/npu_demo/test_runtime_launch.py](test/include/npu_demo/test_runtime_launch.py)
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        source_path = Path(tmpdir) / "npu_demo_runtime_launch.cpp"
        binary_path = Path(tmpdir) / "npu_demo_runtime_launch"
        source_path.write_text(source, encoding="utf-8")

        compile_result = None
        max_attempts = 3
        for attempt in range(max_attempts):
            try:
                compile_result = subprocess.run(
                    [
                        "g++",
                        "-std=c++17",
                        "-pthread",
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
                    timeout=timeout_s,
                )
            except subprocess.TimeoutExpired as exc:
                raise AssertionError(
                    "g++ compile timed out. "
                    "This is usually a toolchain/environment issue, not launch logic."
                ) from exc
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
            timeout=timeout_s,
        )
        if run_result.returncode != 0:
            raise AssertionError(
                "compiled program failed:\n"
                f"stdout:\n{run_result.stdout}\n"
                f"stderr:\n{run_result.stderr}"
            )


# NPU-DEMO-RT-001
# 测试目的: 验证 `launch<1, 4, 1, 0>` 必须真实启动 4 线程，并共享同一 barrier 状态（禁止串行模拟/私有 barrier）。
# 使用示例: pytest -q test/include/npu_demo/test_runtime_launch.py -k test_npu_demo_launch_spawns_threads_and_barrier_waits_for_all_participants
# 对应功能实现文件链接: [include/npu_demo/Arch.h](include/npu_demo/Arch.h)
# 对应 spec 文件链接: [spec/include/npu_demo/npu_demo.md](spec/include/npu_demo/npu_demo.md)
# 对应测试文件链接: [test/include/npu_demo/test_runtime_launch.py](test/include/npu_demo/test_runtime_launch.py)
def test_npu_demo_launch_spawns_threads_and_barrier_waits_for_all_participants() -> None:
    source = r"""
#include <atomic>
#include <chrono>
#include <thread>

#include "include/npu_demo/npu_demo.h"

static int fail(int code) { return code; }

static void kernel_body(
    npu_demo::KernelContext& ctx,
    std::atomic<long long>* entered,
    long long* after_values,
    long long* thread_ids,
    long long* thread_nums) {
    const long long tid = ctx.thread_id();
    thread_ids[tid] = tid;
    thread_nums[tid] = ctx.thread_num();

    // Delay thread 0 before incrementing `entered` so that a missing/shared barrier
    // cannot "accidentally pass" due to scheduling.
    if (tid == 0) {
        std::this_thread::sleep_for(std::chrono::milliseconds(100));
    }
    entered->fetch_add(1);

    ctx.barrier({BarrierVisibility::TSM, BarrierVisibility::TLM}, BarrierScope::BLOCK);
    after_values[tid] = entered->load();
}

int main() {
    std::atomic<long long> entered(0);
    long long after_values[4] = {-1, -1, -1, -1};
    long long thread_ids[4] = {-1, -1, -1, -1};
    long long thread_nums[4] = {0, 0, 0, 0};

    if (npu_demo::launch<1, 4, 1, 0>(
            kernel_body,
            &entered,
            after_values,
            thread_ids,
            thread_nums)
        != StatusCode::kOk) {
        return fail(1);
    }

    for (long long i = 0; i < 4; ++i) {
        if (thread_ids[i] != i) {
            return fail(2);
        }
        if (thread_nums[i] != 4) {
            return fail(3);
        }
        // If barrier is missing / not shared / serially simulated, at least one
        // participant will observe entered < 4 after the barrier call.
        if (after_values[i] != 4) {
            return fail(4);
        }
    }
    return 0;
}
"""
    _compile_and_run(source, timeout_s=5.0)
