"""API Core compile tests.

创建者: jcc你莫辜负
最后一次更改: jcc你莫辜负

功能说明:
- 通过编译并运行 C++ 片段验证 include/api/Core.h 的 Vector 与 Status 语义。

覆盖率信息:
- 当前覆盖率: `N/A`。该链路为 C++ 头文件，按规则豁免 `pytest-cov` 覆盖率统计。
- 达标判定: C++ 头文件实现按规则豁免 `95%` 覆盖率达标线。
- 当前覆盖基线: `API-CORE-001`。

覆盖率命令:
- `pytest -q test/include/api/test_core.py`
- `N/A`（C++ 头文件实现，按当前规则豁免 `pytest-cov` 覆盖率统计）

使用示例:
- pytest -q test/include/api/test_core.py

关联文件:
- 功能实现: include/api/Core.h
- Spec 文档: spec/include/api/Core.md
- 测试文件: test/include/api/test_core.py
"""

from __future__ import annotations

import subprocess
import tempfile
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]


def _compile_and_run(source: str) -> None:
    """编译并运行 C++ 测试片段。

    创建者: jcc你莫辜负
    最后一次更改: jcc你莫辜负

    功能说明:
    - 使用 g++ 编译临时源码并执行生成的程序。

    使用示例:
    - _compile_and_run("int main() { return 0; }")

    关联文件:
    - spec: spec/include/api/Core.md
    - test: test/include/api/test_core.py
    - 功能实现: test/include/api/test_core.py
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        source_path = Path(tmpdir) / "core_test.cpp"
        binary_path = Path(tmpdir) / "core_test"
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


# API-CORE-001
# 创建者: jcc你莫辜负
# 最后一次更改: jcc你莫辜负
# 最近一次运行测试时间: 2026-03-31 01:09:50 +0800
# 最近一次运行成功时间: 2026-03-31 01:09:50 +0800
# 测试目的: 验证 Vector 固定为 int64 视图，size 与元素访问符合 A0 验收口径。
# 使用示例: pytest -q test/include/api/test_core.py -k test_api_core_vector_uses_fixed_int64_without_template_parameter
# 对应功能实现文件路径: include/api/Core.h
# 对应 spec 文件路径: spec/include/api/Core.md
# 对应测试文件路径: test/include/api/test_core.py
def test_api_core_vector_uses_fixed_int64_without_template_parameter() -> None:
    source = r"""
#include "include/api/Core.h"

static int fail(int code) {
    return code;
}

int main() {
    long long coords_buf[3] = {5, 0, 7};
    Vector coords(coords_buf, 3);
    if (coords.size() != 3) {
        return fail(1);
    }
    if (coords[0] != 5) {
        return fail(2);
    }
    Status status = StatusCode::kOk;
    if (status != StatusCode::kOk) {
        return fail(3);
    }
    return 0;
}
"""
    _compile_and_run(source)
