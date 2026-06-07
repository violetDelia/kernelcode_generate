"""npu_demo include expectation：launch block grid。

创建者: OpenAI Codex
最后一次更改: OpenAI Codex

功能说明:
- 锁定 `npu_demo::launch<block, thread, subthread, shared_memory_size, body>` 在
  `block > 1` 时必须接收显式 context 并运行 block × thread 网格。
- 验证 launched body 接收 `KernelContext& ctx`，但运行时 id / extent 通过公开
  Arch free helper 读取，不依赖 `ctx.*` 成员函数。

API 列表:
- `main() -> None`

使用示例:
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 expectation/include/npu_demo/launch_block_grid.py`
- `PYTHONDONTWRITEBYTECODE=1 EXPECTATION_WORKTREE_ROOT=/path/to/worktree PYTHONPATH=/path/to/worktree:. python3 expectation/include/npu_demo/launch_block_grid.py`

关联文件:
- spec: [`spec/include/npu_demo/npu_demo.md`](spec/include/npu_demo/npu_demo.md)
- test: [`test/include/npu_demo/test_runtime_launch.py`](test/include/npu_demo/test_runtime_launch.py)
- 功能实现: [`include/npu_demo/Arch.h`](include/npu_demo/Arch.h)
- 功能实现: [`expectation/include/npu_demo/launch_block_grid.py`](expectation/include/npu_demo/launch_block_grid.py)
"""

# Case 列表:
# - include-npu_demo-launch-block-grid-1: `launch<2, 1, 1, 0, body>(ctx, args...)` 应运行 2×1 网格，并让每个 body 通过 Arch free helper 看到正确的 block/thread 运行时视图。

from __future__ import annotations

import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time

REPO_ROOT = next(parent for parent in Path(__file__).resolve().parents if (parent / "kernel_gen").exists())
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from expectation.utils.case_runner import raise_if_failures, run_case

_EXPECTATION_WORKTREE_ROOT_ENV = "EXPECTATION_WORKTREE_ROOT"


def _resolve_include_root() -> Path:
    """解析本 case 编译 C++ 片段时使用的 include 根目录。"""

    override = os.environ.get(_EXPECTATION_WORKTREE_ROOT_ENV)
    if not override:
        return REPO_ROOT
    include_root = Path(override).expanduser().resolve()
    expected_header = include_root / "include" / "npu_demo" / "npu_demo.h"
    if not expected_header.is_file():
        raise AssertionError(
            f"{_EXPECTATION_WORKTREE_ROOT_ENV} does not contain include/npu_demo/npu_demo.h: "
            f"{include_root}"
        )
    return include_root


def _compile_and_run(source: str, *, timeout_s: float = 5.0) -> None:
    """编译并运行 npu_demo include expectation 的 C++ 片段。"""

    with tempfile.TemporaryDirectory() as tmpdir:
        include_root = _resolve_include_root()
        source_path = Path(tmpdir) / "npu_demo_launch_block_grid.cpp"
        binary_path = Path(tmpdir) / "npu_demo_launch_block_grid"
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
                        str(include_root),
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
                raise AssertionError("g++ compile timed out") from exc
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
                f"returncode: {run_result.returncode}\n"
                f"stdout:\n{run_result.stdout}\n"
                f"stderr:\n{run_result.stderr}"
            )


def _case_launch_runs_block_thread_grid() -> None:
    """验证 `npu_demo::launch<..., body>(ctx, args...)` 按 block × thread 网格运行 body。"""

    source = r"""
#include "include/npu_demo/npu_demo.h"

static int fail(int code) { return code; }

static void kernel_body(
    npu_demo::KernelContext& ctx,
    long long* seen,
    long long* block_ids,
    long long* thread_ids,
    long long* thread_nums) {
    (void)ctx;
    const long long bid = npu_demo::block_id();
    const long long tid = npu_demo::thread_id();
    const long long idx = bid * npu_demo::thread_num() + tid;

    seen[idx] = 1;
    block_ids[idx] = bid;
    thread_ids[idx] = tid;
    thread_nums[idx] = npu_demo::thread_num();
}

int main() {
    constexpr long long kBlocks = 2;
    constexpr long long kThreads = 1;
    constexpr long long kTotal = kBlocks * kThreads;

    long long seen[kTotal] = {0};
    long long block_ids[kTotal] = {-1, -1};
    long long thread_ids[kTotal] = {-1, -1};
    long long thread_nums[kTotal] = {0};
    npu_demo::KernelContext ctx;

    if (npu_demo::launch<kBlocks, kThreads, 1, 0, kernel_body>(
            ctx,
            seen,
            block_ids,
            thread_ids,
            thread_nums)
        != StatusCode::kOk) {
        return fail(1);
    }

    for (long long bid = 0; bid < kBlocks; ++bid) {
        for (long long tid = 0; tid < kThreads; ++tid) {
            const long long idx = bid * kThreads + tid;
            if (seen[idx] != 1) {
                return fail(10 + static_cast<int>(idx));
            }
            if (block_ids[idx] != bid) {
                return fail(30 + static_cast<int>(idx));
            }
            if (thread_ids[idx] != tid) {
                return fail(70 + static_cast<int>(idx));
            }
            if (thread_nums[idx] != kThreads) {
                return fail(90 + static_cast<int>(idx));
            }
        }
    }
    return 0;
}
"""
    _compile_and_run(source, timeout_s=5.0)


def main() -> None:
    """运行 npu_demo launch block grid expectation。"""

    failures: list[tuple[str, BaseException]] = []
    run_case(
        failures,
        "include-npu_demo-launch-block-grid-1",
        _case_launch_runs_block_thread_grid,
    )
    raise_if_failures("npu_demo launch block grid expectation", failures)


if __name__ == "__main__":
    main()
