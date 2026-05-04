"""include/api public namespace compile tests.


功能说明:
- 验证 include/api 层公开头文件可被调用方直接包含。
- 锁定 `include/api/Trance.h` 在未定义 `TRANCE` 时不产生运行期输出。

使用示例:
- pytest -q test/include/api/test_public_namespace.py

关联文件:
- spec: spec/include/api/Trance.md
- spec: spec/include/api/Arch.md
- spec: spec/include/api/Memory.md
- test: test/include/api/test_public_namespace.py
- 功能实现: include/api/Trance.h
"""

from __future__ import annotations

import subprocess
import tempfile
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]


def _compile_only(source: str) -> None:
    """编译 include/api 公开头文件测试片段。


    功能说明:
    - 使用 `g++ -std=c++17 -c` 只验证 include/api 公开声明面，不链接后端实现。
    - 适用于 include/api 只声明接口、include/npu_demo 承接实现的头文件边界。

    使用示例:
    - _compile_only("#include \"include/api/Trance.h\"")

    关联文件:
    - spec: spec/include/api/Trance.md
    - test: test/include/api/test_public_namespace.py
    - 功能实现: test/include/api/test_public_namespace.py
    """

    with tempfile.TemporaryDirectory() as tmpdir:
        source_path = Path(tmpdir) / "include_api_public_namespace.cpp"
        object_path = Path(tmpdir) / "include_api_public_namespace.o"
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


def _compile_and_run(source: str) -> str:
    """编译并运行 include/api 公开头文件测试片段。


    功能说明:
    - 使用 `g++ -std=c++17` 编译并运行最小程序。
    - 仅验证 include/api 层有完整 inline no-op 行为的公开入口。

    使用示例:
    - stdout = _compile_and_run("int main() { return 0; }")

    关联文件:
    - spec: spec/include/api/Trance.md
    - test: test/include/api/test_public_namespace.py
    - 功能实现: test/include/api/test_public_namespace.py
    """

    with tempfile.TemporaryDirectory() as tmpdir:
        source_path = Path(tmpdir) / "include_api_public_namespace_run.cpp"
        binary_path = Path(tmpdir) / "include_api_public_namespace_run"
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

        run_result = subprocess.run([str(binary_path)], check=False, capture_output=True, text=True)
        if run_result.returncode != 0:
            raise AssertionError(
                "compiled program failed:\n"
                f"stdout:\n{run_result.stdout}\n"
                f"stderr:\n{run_result.stderr}"
            )
        return run_result.stdout


# API-PUBLIC-NAMESPACE-001
# 测试目的: 验证 include/api 公开头文件组合可直接 compile-only 消费。
# 对应功能实现文件路径: include/api/Trance.h
# 对应 spec 文件路径: spec/include/api/Trance.md
# 对应测试文件路径: test/include/api/test_public_namespace.py
def test_include_api_public_headers_compile_together() -> None:
    source = r"""
#include "include/api/Core.h"
#include "include/api/Arch.h"
#include "include/api/Trance.h"
#include "include/api/Memory.h"
#include "include/api/Dma.h"
#include "include/api/Kernel.h"

void consume_api_names() {
    Status status = StatusCode::kOk;
    BarrierScope scope = BarrierScope::BLOCK;
    MemorySpace space = GM;
    kernelcode::trance::TranceSink sink = kernelcode::trance::make_stdout_sink();
    (void)status;
    (void)scope;
    (void)space;
    (void)sink;
}
"""
    _compile_only(source)


# API-PUBLIC-NAMESPACE-002
# 测试目的: 验证 include/api/Trance.h 在未定义 TRANCE 时公开函数是无输出 no-op。
# 对应功能实现文件路径: include/api/Trance.h
# 对应 spec 文件路径: spec/include/api/Trance.md
# 对应测试文件路径: test/include/api/test_public_namespace.py
def test_include_api_trance_noop_public_runtime_boundary() -> None:
    source = r"""
#include "include/api/Trance.h"

int main() {
    kernelcode::trance::ScopedTranceSink scope;
    kernelcode::trance::TranceSink sink = kernelcode::trance::make_stdout_sink();
    kernelcode::trance::print_func_begin(sink, "kernel", "template=<none>");
    kernelcode::trance::write_line(kernelcode::trance::current_sink(), "hidden");
    kernelcode::trance::print_return_i64(sink, 1);
    kernelcode::trance::close_sink(sink);
    return 0;
}
"""
    stdout = _compile_and_run(source)

    assert stdout == ""
