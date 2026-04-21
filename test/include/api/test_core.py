"""API Core compile tests.

创建者: jcc你莫辜负
最后一次更改: jcc你莫辜负

功能说明:
- 通过编译并运行 C++ 片段验证 include/api/Core.h 的 Vector 与 Status 语义，并使用 include/npu_demo/Core.h 提供实现。
- 覆盖 `Vector{...}` 与 `Vector values = {...}` 的 1..4 个 long long 固定参数构造。

覆盖率信息:
- 当前覆盖率: `N/A`。该链路为 C++ 头文件，按规则豁免 `pytest-cov` 覆盖率统计。
- 达标判定: C++ 头文件实现按规则豁免 `95%` 覆盖率达标线。
- 当前覆盖基线: `API-CORE-001`、`API-CORE-002`。

覆盖率命令:
- `pytest -q test/include/api/test_core.py`
- `N/A`（C++ 头文件实现，按当前规则豁免 `pytest-cov` 覆盖率统计）

使用示例:
- pytest -q test/include/api/test_core.py

关联文件:
- 功能实现: include/npu_demo/Core.h
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
# 对应功能实现文件路径: include/npu_demo/Core.h
# 对应 spec 文件路径: spec/include/api/Core.md
# 对应测试文件路径: test/include/api/test_core.py
def test_api_core_vector_uses_fixed_int64_without_template_parameter() -> None:
    source = r"""
#include "include/api/Core.h"
#include "include/npu_demo/Core.h"

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


# API-CORE-002
# 创建者: jcc你莫辜负
# 最后一次更改: jcc你莫辜负
# 最近一次运行测试时间: 2026-04-21 21:00:00 +0800
# 最近一次运行成功时间: 2026-04-21 21:00:00 +0800
# 测试目的: 验证 Vector 花括号构造复制到对象自有存储，且 pointer-view 构造保持可用。
# 使用示例: pytest -q test/include/api/test_core.py -k test_api_core_vector_brace_constructors_keep_owned_values_without_std_helpers
# 对应功能实现文件链接: [include/npu_demo/Core.h](include/npu_demo/Core.h)
# 对应 spec 文件链接: [spec/include/api/Core.md](spec/include/api/Core.md)
# 对应测试文件链接: [test/include/api/test_core.py](test/include/api/test_core.py)
def test_api_core_vector_brace_constructors_keep_owned_values_without_std_helpers() -> None:
    api_header = (REPO_ROOT / "include/api/Core.h").read_text(encoding="utf-8")
    impl_header = (REPO_ROOT / "include/npu_demo/Core.h").read_text(encoding="utf-8")
    for token in (
        "<initializer_list>",
        "std::initializer_list",
        "std::vector",
        "std::array",
        "new ",
        "malloc",
    ):
        assert token not in api_header
        assert token not in impl_header

    source = r"""
#include "include/api/Core.h"
#include "include/npu_demo/Core.h"

static int fail(int code) {
    return code;
}

static int expect_vector(const Vector& values, unsigned long long size, const long long* expected) {
    if (values.size() != size) {
        return 1;
    }
    for (unsigned long long i = 0; i < size; ++i) {
        if (values.data()[i] != expected[i]) {
            return 2;
        }
        if (values[i] != expected[i]) {
            return 3;
        }
    }
    return 0;
}

int main() {
    long long one_expected[1] = {16};
    Vector one{16};
    if (expect_vector(one, 1, one_expected) != 0) {
        return fail(1);
    }

    long long two_expected[2] = {2, 3};
    Vector two{2, 3};
    if (expect_vector(two, 2, two_expected) != 0) {
        return fail(2);
    }

    long long three_expected[3] = {2, 3, 4};
    Vector dims = {2, 3, 4};
    if (expect_vector(dims, 3, three_expected) != 0) {
        return fail(3);
    }

    long long four_expected[4] = {1, 2, 3, 4};
    Vector full{1, 2, 3, 4};
    if (expect_vector(full, 4, four_expected) != 0) {
        return fail(4);
    }
    full[2] = 9;
    if (full.data()[2] != 9) {
        return fail(5);
    }

    Vector source{7, 8, 9};
    Vector copied(source);
    source[1] = 80;
    if (copied.size() != 3 || copied[0] != 7 || copied[1] != 8 || copied[2] != 9) {
        return fail(6);
    }

    Vector assigned{0};
    Vector assign_source{10, 11, 12, 13};
    assigned = assign_source;
    assign_source[0] = 100;
    if (assigned.size() != 4 || assigned[0] != 10 || assigned[3] != 13) {
        return fail(7);
    }

    long long external[2] = {30, 31};
    Vector view(external, 2);
    Vector view_copy(view);
    external[1] = 77;
    if (view_copy.size() != 2 || view_copy[0] != 30 || view_copy[1] != 77) {
        return fail(8);
    }

    const long long const_external[2] = {40, 41};
    Vector const_view(const_external, 2);
    if (const_view.size() != 2 || const_view.data()[0] != 40 || const_view[1] != 41) {
        return fail(9);
    }

    Status status = StatusCode::kOk;
    if (status != StatusCode::kOk) {
        return fail(10);
    }
    return 0;
}
"""
    _compile_and_run(source)
