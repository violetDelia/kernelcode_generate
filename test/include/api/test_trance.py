"""API Trance compile tests.


功能说明:
- 通过编译并运行 C++ 片段验证 include/api/Trance.h 与 include/npu_demo/Trance.h 的公开 runtime trance 边界。
- 覆盖 `TRANCE` 关闭时的 no-op 行为、stdout sink、文件打开失败回退 stdout，以及 Memory/launch 参数打印格式。

使用示例:
- pytest -q test/include/api/test_trance.py

关联文件:
- 功能实现: include/api/Trance.h
- 功能实现: include/npu_demo/Trance.h
- 功能实现: include/npu_demo/Memory.h
- 功能实现: include/npu_demo/Arch.h
- Spec 文档: spec/include/api/Trance.md
- 测试文件: test/include/api/test_trance.py
"""

from __future__ import annotations

import subprocess
import tempfile
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]


def _compile_and_run_capture_stdout(source: str, compiler_flags: tuple[str, ...] = ()) -> str:
    """编译并运行 C++ Trance 测试片段，返回 stdout。


    功能说明:
    - 使用 `g++ -std=c++17 -pthread` 编译临时源码。
    - `compiler_flags` 只用于测试公开宏开关，例如 `-DTRANCE` 与 `KG_TRANCE_FILE_PATH`。

    使用示例:
    - stdout = _compile_and_run_capture_stdout("int main() { return 0; }")

    关联文件:
    - spec: spec/include/api/Trance.md
    - test: test/include/api/test_trance.py
    - 功能实现: test/include/api/test_trance.py
    """

    with tempfile.TemporaryDirectory() as tmpdir:
        source_path = Path(tmpdir) / "trance_test.cpp"
        binary_path = Path(tmpdir) / "trance_test"
        source_path.write_text(source, encoding="utf-8")

        compile_result = subprocess.run(
            [
                "g++",
                "-std=c++17",
                "-pthread",
                *compiler_flags,
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
        return run_result.stdout


# API-TRANCE-001
# 测试目的: 验证未定义 TRANCE 时 include/api/Trance.h 公开函数全部是无副作用 no-op。
# 对应功能实现文件路径: include/api/Trance.h
# 对应 spec 文件路径: spec/include/api/Trance.md
# 对应测试文件路径: test/include/api/test_trance.py
def test_api_trance_header_noop_without_macro() -> None:
    source = r"""
#include "include/api/Trance.h"

int main() {
    kernelcode::trance::TranceSink sink = kernelcode::trance::make_stdout_sink();
    kernelcode::trance::write_line(sink, "hidden");
    kernelcode::trance::print_func_begin(sink, "kernel", "template=<none>");
    kernelcode::trance::print_return_i64(sink, 7);
    kernelcode::trance::ScopedTranceSink scope;
    kernelcode::trance::close_sink(sink);
    return 0;
}
"""
    stdout = _compile_and_run_capture_stdout(source)

    assert stdout == ""


# API-TRANCE-002
# 测试目的: 验证 npu_demo Memory 实现不跨文件引用 Trance.h 的非公开 detail helper。
# 对应功能实现文件路径: include/npu_demo/Memory.h
# 对应 spec 文件路径: spec/include/api/Trance.md
# 对应测试文件路径: test/include/api/test_trance.py
def test_npu_demo_memory_does_not_use_trance_detail_helpers() -> None:
    memory_header = REPO_ROOT / "include" / "npu_demo" / "Memory.h"

    assert "kernelcode::trance::detail" not in memory_header.read_text(encoding="utf-8")


# API-TRANCE-003
# 测试目的: 验证 TRANCE 开启时 Memory 与 launch 的 stdout 参数格式符合公开合同。
# 对应功能实现文件路径: include/npu_demo/Trance.h
# 对应功能实现文件路径: include/npu_demo/Memory.h
# 对应功能实现文件路径: include/npu_demo/Arch.h
# 对应 spec 文件路径: spec/include/api/Trance.md
# 对应测试文件路径: test/include/api/test_trance.py
def test_npu_demo_trance_stdout_memory_and_launch_format() -> None:
    source = r"""
#include "include/npu_demo/npu_demo.h"

static void kernel_body(npu_demo::KernelContext& ctx, Memory<GM, float>& mem, long long scalar) {
    (void)ctx;
    (void)mem;
    (void)scalar;
}

int main() {
    kernelcode::trance::ScopedTranceSink scope;

    float data[6] = {0.0f, 1.0f, 2.0f, 3.0f, 4.0f, 5.0f};
    long long shape[2] = {2, 3};
    long long stride[2] = {3, 1};
    Memory<GM, float> mem(data, shape, stride, 2, MemoryFormat::Norm);

    Status status = npu_demo::launch<1, 2, 1, 0>(kernel_body, mem, 7LL);
    return status == StatusCode::kOk ? 0 : 1;
}
"""
    stdout = _compile_and_run_capture_stdout(source, ("-DTRANCE",))

    assert "in func: npu_demo::launch template=<block=1, thread=2, subthread=1, shared_memory_size=0>" in stdout
    assert "arg0 = callable[kernel_body]" in stdout
    assert "arg1 = mem[" in stdout
    assert "[2, 3] [3, 1] f32 GM" in stdout
    assert "arg2 = 7" in stdout
    assert stdout.index("arg1 = mem[") < stdout.index("arg2 = 7")


# API-TRANCE-004
# 测试目的: 验证 TRANCE 文件 sink 打开失败时输出 `log failed` 并回退 stdout。
# 对应功能实现文件路径: include/npu_demo/Trance.h
# 对应 spec 文件路径: spec/include/api/Trance.md
# 对应测试文件路径: test/include/api/test_trance.py
def test_npu_demo_trance_file_open_failure_falls_back_to_stdout(tmp_path: Path) -> None:
    missing_trace_path = tmp_path / "missing" / "kernel_trace.txt"
    source = r"""
#include "include/npu_demo/Trance.h"

int main() {
    kernelcode::trance::ScopedTranceSink scope;
    kernelcode::trance::write_line(kernelcode::trance::current_sink(), "fallback line");
    return 0;
}
"""
    stdout = _compile_and_run_capture_stdout(
        source,
        ("-DTRANCE", f'-DKG_TRANCE_FILE_PATH="{missing_trace_path}"'),
    )

    assert f"log failed: {missing_trace_path}" in stdout
    assert "fallback line" in stdout
    assert not missing_trace_path.exists()


# API-TRANCE-005
# 测试目的: 验证 ScopedTranceSink/current_sink 的活动 sink 不会跨线程泄漏。
# 对应功能实现文件路径: include/npu_demo/Trance.h
# 对应 spec 文件路径: spec/include/api/Trance.md
# 对应测试文件路径: test/include/api/test_trance.py
def test_npu_demo_scoped_sink_does_not_cross_thread(tmp_path: Path) -> None:
    trace_path = tmp_path / "owner_trace.txt"
    source = r"""
#include "include/npu_demo/Trance.h"

#include <thread>

int main() {
    {
        kernelcode::trance::ScopedTranceSink owner_scope;
        kernelcode::trance::write_line(kernelcode::trance::current_sink(), "owner line");
        std::thread observer([]() {
            kernelcode::trance::write_line(kernelcode::trance::current_sink(), "observer line");
        });
        observer.join();
    }
    return 0;
}
"""
    stdout = _compile_and_run_capture_stdout(
        source,
        ("-DTRANCE", f'-DKG_TRANCE_FILE_PATH="{trace_path}"'),
    )

    trace_text = trace_path.read_text(encoding="utf-8")
    assert "observer line" in stdout
    assert "owner line" not in stdout
    assert "owner line" in trace_text
    assert "observer line" not in trace_text
