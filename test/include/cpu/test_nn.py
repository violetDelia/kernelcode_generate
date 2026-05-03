"""CPU NN include tests.


功能说明:
- 通过编译并运行 C++ 片段验证 include/cpu/Nn.h 的逐元素、broadcast 与 img2col 语义。

覆盖率信息:
- 当前覆盖率: `N/A`。该链路的功能实现为 C++ 头文件，当前任务不使用 `pytest-cov` 直接统计覆盖率。
- 达标判定: C++ 实现按规则豁免 `95%` 覆盖率达标线。
- 当前以 `INC-NN-001..028` 对应测试作为覆盖基线。
- 最近一次测试核对: `2026-03-30 04:10:02 +0800`，本次执行 `pytest -q test/include/cpu/test_memory.py test/include/cpu/test_nn.py`，结果为 `30 passed`。

覆盖率命令:
- N/A（C++ 头文件实现，当前任务不使用 `pytest-cov` 统计覆盖率）

使用示例:
- pytest -q test/include/cpu/test_nn.py

关联文件:
- 功能实现: include/cpu/Nn.h
- Spec 文档: spec/include/cpu/cpu.md
- 测试文件: test/include/cpu/test_nn.py
"""

from __future__ import annotations

import subprocess
import tempfile
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]


def _compile_and_run(source: str) -> None:
    """编译并运行 C++ 测试片段。


    功能说明:
    - 使用 g++ 编译临时源码并执行生成的程序。

    使用示例:
    - _compile_and_run("int main() { return 0; }")

    关联文件:
    - spec: spec/include/cpu/cpu.md
    - test: test/include/cpu/test_nn.py
    - 功能实现: test/include/cpu/test_nn.py
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        source_path = Path(tmpdir) / "nn_test.cpp"
        binary_path = Path(tmpdir) / "nn_test"
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


def _compile_expect_failure(source: str, expected_stderr: str) -> None:
    """编译 C++ 片段并断言其编译失败且报错包含指定关键字。


    功能说明:
    - 使用 g++ 编译临时源码，并验证失败信息命中指定关键字。

    使用示例:
    - _compile_expect_failure("int main() { missing(); }", "missing")

    关联文件:
    - spec: spec/include/cpu/cpu.md
    - test: test/include/cpu/test_nn.py
    - 功能实现: test/include/cpu/test_nn.py
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        source_path = Path(tmpdir) / "nn_compile_fail.cpp"
        binary_path = Path(tmpdir) / "nn_compile_fail"
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
        if compile_result.returncode == 0:
            raise AssertionError("expected g++ compile failure, but compilation succeeded")
        if expected_stderr not in compile_result.stderr:
            raise AssertionError(
                "compile stderr does not contain expected text:\n"
                f"expected: {expected_stderr}\n"
                f"stdout:\n{compile_result.stdout}\n"
                f"stderr:\n{compile_result.stderr}"
            )


def _compile_and_run_expect_failure(source: str) -> None:
    """编译并运行 C++ 片段，断言程序因契约失败而非零退出。


    功能说明:
    - 使用 g++ 编译临时源码，并验证运行结果为非零退出码。

    使用示例:
    - _compile_and_run_expect_failure("int main() { __builtin_trap(); }")

    关联文件:
    - spec: spec/include/cpu/cpu.md
    - test: test/include/cpu/test_nn.py
    - 功能实现: test/include/cpu/test_nn.py
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        source_path = Path(tmpdir) / "nn_runtime_fail.cpp"
        binary_path = Path(tmpdir) / "nn_runtime_fail"
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
        if run_result.returncode == 0:
            raise AssertionError(
                "expected compiled program to fail, but it exited successfully:\n"
                f"stdout:\n{run_result.stdout}\n"
                f"stderr:\n{run_result.stderr}"
            )


# INC-NN-001
# 测试目的: 验证逐元素加法输出正确。
# 使用示例: pytest -q test/include/cpu/test_nn.py -k test_cpu_nn_add_success
# 对应功能实现文件路径: include/cpu/Nn.h
# 对应 spec 文件路径: spec/include/cpu/cpu.md
# 对应测试文件路径: test/include/cpu/test_nn.py
def test_cpu_nn_add_success() -> None:
    source = r"""
#include "include/cpu/Memory.h"
#include "include/cpu/Nn.h"

static int fail(int code) { return code; }

int main() {
    float lhs_data[6] = {1, 2, 3, 4, 5, 6};
    float rhs_data[6] = {6, 5, 4, 3, 2, 1};
    float out_data[6] = {0};
    long long shape[2] = {2, 3};
    long long stride[2] = {3, 1};

    cpu::Memory<cpu::GM, float> lhs(lhs_data, 2, shape, stride);
    cpu::Memory<cpu::GM, float> rhs(rhs_data, 2, shape, stride);
    cpu::Memory<cpu::GM, float> out(out_data, 2, shape, stride);

    cpu::add(lhs, rhs, out);

    if (out_data[0] != 7 || out_data[1] != 7 || out_data[5] != 7) {
        return fail(1);
    }
    return 0;
}
"""
    _compile_and_run(source)


# INC-NN-002
# 测试目的: 验证逐元素比较输出 predicate 语义结果。
# 使用示例: pytest -q test/include/cpu/test_nn.py -k test_cpu_nn_compare_eq
# 对应功能实现文件路径: include/cpu/Nn.h
# 对应 spec 文件路径: spec/include/cpu/cpu.md
# 对应测试文件路径: test/include/cpu/test_nn.py
def test_cpu_nn_compare_eq() -> None:
    source = r"""
#include "include/cpu/Memory.h"
#include "include/cpu/Nn.h"

static int fail(int code) { return code; }

int main() {
    float lhs_data[6] = {1, 2, 3, 4, 5, 6};
    float rhs_data[6] = {1, 0, 3, 0, 5, 0};
    int out_data[6] = {0};
    long long shape[2] = {2, 3};
    long long stride[2] = {3, 1};

    cpu::Memory<cpu::GM, float> lhs(lhs_data, 2, shape, stride);
    cpu::Memory<cpu::GM, float> rhs(rhs_data, 2, shape, stride);
    cpu::Memory<cpu::GM, int> out(out_data, 2, shape, stride);

    cpu::eq(lhs, rhs, out);

    if (out_data[0] != 1 || out_data[1] != 0 || out_data[2] != 1) {
        return fail(1);
    }
    if (out_data[5] != 0) {
        return fail(2);
    }
    return 0;
}
"""
    _compile_and_run(source)


# INC-NN-003
# 测试目的: 验证 broadcast 支持 singleton 扩张。
# 使用示例: pytest -q test/include/cpu/test_nn.py -k test_cpu_nn_broadcast_success
# 对应功能实现文件路径: include/cpu/Nn.h
# 对应 spec 文件路径: spec/include/cpu/cpu.md
# 对应测试文件路径: test/include/cpu/test_nn.py
def test_cpu_nn_broadcast_success() -> None:
    source = r"""
#include "include/cpu/Memory.h"
#include "include/cpu/Nn.h"

static int fail(int code) { return code; }

int main() {
    float in_data[4] = {1, 2, 3, 4};
    float out_data[12] = {0};
    long long in_shape[2] = {1, 4};
    long long out_shape[2] = {3, 4};
    long long in_stride[2] = {4, 1};
    long long out_stride[2] = {4, 1};

    cpu::Memory<cpu::GM, float> input(in_data, 2, in_shape, in_stride);
    cpu::Memory<cpu::GM, float> out(out_data, 2, out_shape, out_stride);

    cpu::broadcast(input, out);

    for (int row = 0; row < 3; ++row) {
        for (int col = 0; col < 4; ++col) {
            if (out_data[row * 4 + col] != in_data[col]) {
                return fail(1);
            }
        }
    }
    return 0;
}
"""
    _compile_and_run(source)


# INC-NN-004
# 测试目的: 验证 broadcast 支持前置维插入。
# 使用示例: pytest -q test/include/cpu/test_nn.py -k test_cpu_nn_broadcast_prepend_dim
# 对应功能实现文件路径: include/cpu/Nn.h
# 对应 spec 文件路径: spec/include/cpu/cpu.md
# 对应测试文件路径: test/include/cpu/test_nn.py
def test_cpu_nn_broadcast_prepend_dim() -> None:
    source = r"""
#include "include/cpu/Memory.h"
#include "include/cpu/Nn.h"

static int fail(int code) { return code; }

int main() {
    float in_data[4] = {1, 2, 3, 4};
    float out_data[12] = {0};
    long long in_shape[1] = {4};
    long long out_shape[2] = {3, 4};
    long long in_stride[1] = {1};
    long long out_stride[2] = {4, 1};

    cpu::Memory<cpu::GM, float> input(in_data, 1, in_shape, in_stride);
    cpu::Memory<cpu::GM, float> out(out_data, 2, out_shape, out_stride);

    cpu::broadcast(input, out);

    for (int row = 0; row < 3; ++row) {
        for (int col = 0; col < 4; ++col) {
            if (out_data[row * 4 + col] != in_data[col]) {
                return fail(1);
            }
        }
    }
    return 0;
}
"""
    _compile_and_run(source)


# INC-NN-005
# 测试目的: 验证逐元素乘法输出正确。
# 使用示例: pytest -q test/include/cpu/test_nn.py -k test_cpu_nn_mul_success
# 对应功能实现文件路径: include/cpu/Nn.h
# 对应 spec 文件路径: spec/include/cpu/cpu.md
# 对应测试文件路径: test/include/cpu/test_nn.py
def test_cpu_nn_mul_success() -> None:
    source = r"""
#include "include/cpu/Memory.h"
#include "include/cpu/Nn.h"

static int fail(int code) { return code; }

int main() {
    int lhs_data[6] = {1, 2, 3, 4, 5, 6};
    int rhs_data[6] = {2, 2, 2, 2, 2, 2};
    int out_data[6] = {0};
    long long shape[2] = {2, 3};
    long long stride[2] = {3, 1};

    cpu::Memory<cpu::GM, int> lhs(lhs_data, 2, shape, stride);
    cpu::Memory<cpu::GM, int> rhs(rhs_data, 2, shape, stride);
    cpu::Memory<cpu::GM, int> out(out_data, 2, shape, stride);

    cpu::mul(lhs, rhs, out);

    if (out_data[0] != 2 || out_data[1] != 4 || out_data[5] != 12) {
        return fail(1);
    }
    return 0;
}
"""
    _compile_and_run(source)


# INC-NN-006
# 测试目的: 验证逐元素减法输出正确。
# 使用示例: pytest -q test/include/cpu/test_nn.py -k test_cpu_nn_sub_success
# 对应功能实现文件路径: include/cpu/Nn.h
# 对应 spec 文件路径: spec/include/cpu/cpu.md
# 对应测试文件路径: test/include/cpu/test_nn.py
def test_cpu_nn_sub_success() -> None:
    source = r"""
#include "include/cpu/Memory.h"
#include "include/cpu/Nn.h"

static int fail(int code) { return code; }

int main() {
    int lhs_data[4] = {10, 8, 6, 4};
    int rhs_data[4] = {1, 2, 3, 4};
    int out_data[4] = {0};
    long long shape[1] = {4};
    long long stride[1] = {1};

    cpu::Memory<cpu::GM, int> lhs(lhs_data, 1, shape, stride);
    cpu::Memory<cpu::GM, int> rhs(rhs_data, 1, shape, stride);
    cpu::Memory<cpu::GM, int> out(out_data, 1, shape, stride);

    cpu::sub(lhs, rhs, out);

    if (out_data[0] != 9 || out_data[1] != 6 || out_data[3] != 0) {
        return fail(1);
    }
    return 0;
}
"""
    _compile_and_run(source)


# INC-NN-007
# 测试目的: 验证逐元素除法输出正确。
# 使用示例: pytest -q test/include/cpu/test_nn.py -k test_cpu_nn_truediv_success
# 对应功能实现文件路径: include/cpu/Nn.h
# 对应 spec 文件路径: spec/include/cpu/cpu.md
# 对应测试文件路径: test/include/cpu/test_nn.py
def test_cpu_nn_truediv_success() -> None:
    source = r"""
#include "include/cpu/Memory.h"
#include "include/cpu/Nn.h"

static int fail(int code) { return code; }

int main() {
    float lhs_data[4] = {8.0f, 6.0f, 4.0f, 2.0f};
    float rhs_data[4] = {2.0f, 3.0f, 4.0f, 2.0f};
    float out_data[4] = {0};
    long long shape[1] = {4};
    long long stride[1] = {1};

    cpu::Memory<cpu::GM, float> lhs(lhs_data, 1, shape, stride);
    cpu::Memory<cpu::GM, float> rhs(rhs_data, 1, shape, stride);
    cpu::Memory<cpu::GM, float> out(out_data, 1, shape, stride);

    cpu::truediv(lhs, rhs, out);

    if (out_data[0] != 4.0f || out_data[1] != 2.0f || out_data[2] != 1.0f) {
        return fail(1);
    }
    return 0;
}
"""
    _compile_and_run(source)


# INC-NN-008
# 测试目的: 验证逐元素不等比较输出 predicate 语义结果。
# 使用示例: pytest -q test/include/cpu/test_nn.py -k test_cpu_nn_compare_ne
# 对应功能实现文件路径: include/cpu/Nn.h
# 对应 spec 文件路径: spec/include/cpu/cpu.md
# 对应测试文件路径: test/include/cpu/test_nn.py
def test_cpu_nn_compare_ne() -> None:
    source = r"""
#include "include/cpu/Memory.h"
#include "include/cpu/Nn.h"

static int fail(int code) { return code; }

int main() {
    float lhs_data[4] = {1, 2, 3, 4};
    float rhs_data[4] = {1, 0, 3, 5};
    int out_data[4] = {0};
    long long shape[1] = {4};
    long long stride[1] = {1};

    cpu::Memory<cpu::GM, float> lhs(lhs_data, 1, shape, stride);
    cpu::Memory<cpu::GM, float> rhs(rhs_data, 1, shape, stride);
    cpu::Memory<cpu::GM, int> out(out_data, 1, shape, stride);

    cpu::ne(lhs, rhs, out);

    if (out_data[0] != 0 || out_data[1] != 1 || out_data[3] != 1) {
        return fail(1);
    }
    return 0;
}
"""
    _compile_and_run(source)


# INC-NN-009
# 测试目的: 验证逐元素小于比较输出 predicate 语义结果。
# 使用示例: pytest -q test/include/cpu/test_nn.py -k test_cpu_nn_compare_lt
# 对应功能实现文件路径: include/cpu/Nn.h
# 对应 spec 文件路径: spec/include/cpu/cpu.md
# 对应测试文件路径: test/include/cpu/test_nn.py
def test_cpu_nn_compare_lt() -> None:
    source = r"""
#include "include/cpu/Memory.h"
#include "include/cpu/Nn.h"

static int fail(int code) { return code; }

int main() {
    float lhs_data[3] = {1, 2, 3};
    float rhs_data[3] = {2, 2, 1};
    int out_data[3] = {0};
    long long shape[1] = {3};
    long long stride[1] = {1};

    cpu::Memory<cpu::GM, float> lhs(lhs_data, 1, shape, stride);
    cpu::Memory<cpu::GM, float> rhs(rhs_data, 1, shape, stride);
    cpu::Memory<cpu::GM, int> out(out_data, 1, shape, stride);

    cpu::lt(lhs, rhs, out);

    if (out_data[0] != 1 || out_data[1] != 0 || out_data[2] != 0) {
        return fail(1);
    }
    return 0;
}
"""
    _compile_and_run(source)


# INC-NN-010
# 测试目的: 验证逐元素小于等于比较输出 predicate 语义结果。
# 使用示例: pytest -q test/include/cpu/test_nn.py -k test_cpu_nn_compare_le
# 对应功能实现文件路径: include/cpu/Nn.h
# 对应 spec 文件路径: spec/include/cpu/cpu.md
# 对应测试文件路径: test/include/cpu/test_nn.py
def test_cpu_nn_compare_le() -> None:
    source = r"""
#include "include/cpu/Memory.h"
#include "include/cpu/Nn.h"

static int fail(int code) { return code; }

int main() {
    float lhs_data[3] = {1, 2, 3};
    float rhs_data[3] = {1, 1, 4};
    int out_data[3] = {0};
    long long shape[1] = {3};
    long long stride[1] = {1};

    cpu::Memory<cpu::GM, float> lhs(lhs_data, 1, shape, stride);
    cpu::Memory<cpu::GM, float> rhs(rhs_data, 1, shape, stride);
    cpu::Memory<cpu::GM, int> out(out_data, 1, shape, stride);

    cpu::le(lhs, rhs, out);

    if (out_data[0] != 1 || out_data[1] != 0 || out_data[2] != 1) {
        return fail(1);
    }
    return 0;
}
"""
    _compile_and_run(source)


# INC-NN-011
# 测试目的: 验证逐元素大于比较输出 predicate 语义结果。
# 使用示例: pytest -q test/include/cpu/test_nn.py -k test_cpu_nn_compare_gt
# 对应功能实现文件路径: include/cpu/Nn.h
# 对应 spec 文件路径: spec/include/cpu/cpu.md
# 对应测试文件路径: test/include/cpu/test_nn.py
def test_cpu_nn_compare_gt() -> None:
    source = r"""
#include "include/cpu/Memory.h"
#include "include/cpu/Nn.h"

static int fail(int code) { return code; }

int main() {
    float lhs_data[3] = {3, 2, 1};
    float rhs_data[3] = {2, 2, 0};
    int out_data[3] = {0};
    long long shape[1] = {3};
    long long stride[1] = {1};

    cpu::Memory<cpu::GM, float> lhs(lhs_data, 1, shape, stride);
    cpu::Memory<cpu::GM, float> rhs(rhs_data, 1, shape, stride);
    cpu::Memory<cpu::GM, int> out(out_data, 1, shape, stride);

    cpu::gt(lhs, rhs, out);

    if (out_data[0] != 1 || out_data[1] != 0 || out_data[2] != 1) {
        return fail(1);
    }
    return 0;
}
"""
    _compile_and_run(source)


# INC-NN-012
# 测试目的: 验证逐元素大于等于比较输出 predicate 语义结果。
# 使用示例: pytest -q test/include/cpu/test_nn.py -k test_cpu_nn_compare_ge
# 对应功能实现文件路径: include/cpu/Nn.h
# 对应 spec 文件路径: spec/include/cpu/cpu.md
# 对应测试文件路径: test/include/cpu/test_nn.py
def test_cpu_nn_compare_ge() -> None:
    source = r"""
#include "include/cpu/Memory.h"
#include "include/cpu/Nn.h"

static int fail(int code) { return code; }

int main() {
    float lhs_data[3] = {3, 2, 1};
    float rhs_data[3] = {3, 3, 1};
    int out_data[3] = {0};
    long long shape[1] = {3};
    long long stride[1] = {1};

    cpu::Memory<cpu::GM, float> lhs(lhs_data, 1, shape, stride);
    cpu::Memory<cpu::GM, float> rhs(rhs_data, 1, shape, stride);
    cpu::Memory<cpu::GM, int> out(out_data, 1, shape, stride);

    cpu::ge(lhs, rhs, out);

    if (out_data[0] != 1 || out_data[1] != 0 || out_data[2] != 1) {
        return fail(1);
    }
    return 0;
}
"""
    _compile_and_run(source)


# INC-NN-013
# 测试目的: 验证 cpu::img2col1d 的固定签名与成功展开语义。
# 使用示例: pytest -q test/include/cpu/test_nn.py -k test_cpu_nn_img2col1d_success_and_signature
# 对应功能实现文件路径: include/cpu/Nn.h
# 对应 spec 文件路径: spec/include/cpu/cpu.md
# 对应测试文件路径: test/include/cpu/test_nn.py
def test_cpu_nn_img2col1d_success_and_signature() -> None:
    source = r"""
#include "include/cpu/Memory.h"
#include "include/cpu/Nn.h"

using Img2Col1dFn = void (*)(
    const cpu::Memory<cpu::GM, float>&,
    cpu::Memory<cpu::GM, float>&,
    long long,
    long long,
    long long,
    long long,
    long long);

static int fail(int code) { return code; }

int main() {
    Img2Col1dFn fn = &cpu::img2col1d;
    (void)fn;

    float value_data[4] = {1, 2, 3, 4};
    float out_data[12] = {0};
    long long value_shape[3] = {1, 1, 4};
    long long value_stride[3] = {4, 4, 1};
    long long out_shape[3] = {1, 3, 4};
    long long out_stride[3] = {12, 4, 1};

    cpu::Memory<cpu::GM, float> value(value_data, 3, value_shape, value_stride);
    cpu::Memory<cpu::GM, float> out(out_data, 3, out_shape, out_stride);

    cpu::img2col1d(value, out, 3, 1, 1, 1, 1);

    float expected[12] = {0, 1, 2, 3, 1, 2, 3, 4, 2, 3, 4, 0};
    for (int i = 0; i < 12; ++i) {
        if (out_data[i] != expected[i]) {
            return fail(i + 1);
        }
    }
    return 0;
}
"""
    _compile_and_run(source)


# INC-NN-014
# 测试目的: 验证 cpu::img2col2d 的固定签名与成功展开语义。
# 使用示例: pytest -q test/include/cpu/test_nn.py -k test_cpu_nn_img2col2d_success_and_signature
# 对应功能实现文件路径: include/cpu/Nn.h
# 对应 spec 文件路径: spec/include/cpu/cpu.md
# 对应测试文件路径: test/include/cpu/test_nn.py
def test_cpu_nn_img2col2d_success_and_signature() -> None:
    source = r"""
#include "include/cpu/Memory.h"
#include "include/cpu/Nn.h"

using Img2Col2dFn = void (*)(
    const cpu::Memory<cpu::GM, float>&,
    cpu::Memory<cpu::GM, float>&,
    long long,
    long long,
    long long,
    long long,
    long long,
    long long,
    long long,
    long long,
    long long,
    long long);

static int fail(int code) { return code; }

int main() {
    Img2Col2dFn fn = &cpu::img2col2d;
    (void)fn;

    float value_data[6] = {1, 2, 3, 4, 5, 6};
    float out_data[8] = {0};
    long long value_shape[4] = {1, 1, 2, 3};
    long long value_stride[4] = {6, 6, 3, 1};
    long long out_shape[3] = {1, 4, 2};
    long long out_stride[3] = {8, 2, 1};

    cpu::Memory<cpu::GM, float> value(value_data, 4, value_shape, value_stride);
    cpu::Memory<cpu::GM, float> out(out_data, 3, out_shape, out_stride);

    cpu::img2col2d(value, out, 2, 2, 1, 1, 1, 1, 0, 0, 0, 0);

    float expected[8] = {1, 2, 2, 3, 4, 5, 5, 6};
    for (int i = 0; i < 8; ++i) {
        if (out_data[i] != expected[i]) {
            return fail(i + 1);
        }
    }
    return 0;
}
"""
    _compile_and_run(source)


# INC-NN-015
# 测试目的: 验证 cpu::img2col1d 在 rank 前置条件不满足时触发契约失败。
# 使用示例: pytest -q test/include/cpu/test_nn.py -k test_cpu_nn_img2col1d_contract_violation_traps
# 对应功能实现文件路径: include/cpu/Nn.h
# 对应 spec 文件路径: spec/include/cpu/cpu.md
# 对应测试文件路径: test/include/cpu/test_nn.py
def test_cpu_nn_img2col1d_contract_violation_traps() -> None:
    source = r"""
#include "include/cpu/Memory.h"
#include "include/cpu/Nn.h"

int main() {
    float value_data[4] = {1, 2, 3, 4};
    float out_data[12] = {0};
    long long value_shape[2] = {1, 4};
    long long value_stride[2] = {4, 1};
    long long out_shape[3] = {1, 3, 4};
    long long out_stride[3] = {12, 4, 1};

    cpu::Memory<cpu::GM, float> value(value_data, 2, value_shape, value_stride);
    cpu::Memory<cpu::GM, float> out(out_data, 3, out_shape, out_stride);

    cpu::img2col1d(value, out, 3, 1, 1, 1, 1);
    return 0;
}
"""
    _compile_and_run_expect_failure(source)


# INC-NN-016
# 测试目的: 验证 cpu::img2col2d 在 shape 前置条件不满足时触发契约失败。
# 使用示例: pytest -q test/include/cpu/test_nn.py -k test_cpu_nn_img2col2d_contract_violation_traps
# 对应功能实现文件路径: include/cpu/Nn.h
# 对应 spec 文件路径: spec/include/cpu/cpu.md
# 对应测试文件路径: test/include/cpu/test_nn.py
def test_cpu_nn_img2col2d_contract_violation_traps() -> None:
    source = r"""
#include "include/cpu/Memory.h"
#include "include/cpu/Nn.h"

int main() {
    float value_data[6] = {1, 2, 3, 4, 5, 6};
    float out_data[8] = {0};
    long long value_shape[4] = {1, 1, 2, 3};
    long long value_stride[4] = {6, 6, 3, 1};
    long long out_shape[3] = {1, 4, 3};
    long long out_stride[3] = {12, 3, 1};

    cpu::Memory<cpu::GM, float> value(value_data, 4, value_shape, value_stride);
    cpu::Memory<cpu::GM, float> out(out_data, 3, out_shape, out_stride);

    cpu::img2col2d(value, out, 2, 2, 1, 1, 1, 1, 0, 0, 0, 0);
    return 0;
}
"""
    _compile_and_run_expect_failure(source)


# INC-NN-017
# 测试目的: 验证 cpu::img2col1d 在 stride 前置条件不满足时触发契约失败。
# 使用示例: pytest -q test/include/cpu/test_nn.py -k test_cpu_nn_img2col1d_stride_violation_traps
# 对应功能实现文件路径: include/cpu/Nn.h
# 对应 spec 文件路径: spec/include/cpu/cpu.md
# 对应测试文件路径: test/include/cpu/test_nn.py
def test_cpu_nn_img2col1d_stride_violation_traps() -> None:
    source = r"""
#include "include/cpu/Memory.h"
#include "include/cpu/Nn.h"

int main() {
    float value_data[4] = {1, 2, 3, 4};
    float out_data[12] = {0};
    long long value_shape[3] = {1, 1, 4};
    long long value_stride[3] = {4, 4, 1};
    long long out_shape[3] = {1, 3, 4};
    long long out_stride[3] = {99, 4, 1};

    cpu::Memory<cpu::GM, float> value(value_data, 3, value_shape, value_stride);
    cpu::Memory<cpu::GM, float> out(out_data, 3, out_shape, out_stride);

    cpu::img2col1d(value, out, 3, 1, 1, 1, 1);
    return 0;
}
"""
    _compile_and_run_expect_failure(source)


# INC-NN-018
# 测试目的: 验证 include/cpu/Nn.h 不暴露笼统 cpu::img2col 公开名。
# 使用示例: pytest -q test/include/cpu/test_nn.py -k test_cpu_nn_img2col_generic_name_is_forbidden
# 对应功能实现文件路径: include/cpu/Nn.h
# 对应 spec 文件路径: spec/include/cpu/cpu.md
# 对应测试文件路径: test/include/cpu/test_nn.py
def test_cpu_nn_img2col_generic_name_is_forbidden() -> None:
    source = r"""
#include "include/cpu/Memory.h"
#include "include/cpu/Nn.h"

int main() {
    auto fn = &cpu::img2col;
    (void)fn;
    return 0;
}
"""
    _compile_expect_failure(source, "img2col")


# INC-NN-019
# 测试目的: 验证 cpu::exp 逐元素计算与元信息一致性。
# 使用示例: pytest -q test/include/cpu/test_nn.py -k test_cpu_nn_exp_success
# 对应功能实现文件路径: include/cpu/Nn.h
# 对应 spec 文件路径: spec/include/cpu/cpu.md
# 对应测试文件路径: test/include/cpu/test_nn.py
def test_cpu_nn_exp_success() -> None:
    source = r"""
#include "include/cpu/Memory.h"
#include "include/cpu/Nn.h"

static int fail(int code) { return code; }

static float absf(float v) { return v < 0.0f ? -v : v; }

int main() {
    float in_data[4] = {0.0f, 1.0f, -1.0f, 2.0f};
    float out_data[4] = {0.0f, 0.0f, 0.0f, 0.0f};
    long long shape[2] = {2, 2};
    long long stride[2] = {2, 1};

    cpu::Memory<cpu::GM, float> value(in_data, 2, shape, stride);
    cpu::Memory<cpu::GM, float> out(out_data, 2, shape, stride);
    cpu::exp(value, out);

    if (out.rank() != 2 || out.shape()[0] != 2 || out.shape()[1] != 2) {
        return fail(1);
    }
    if (out.stride()[0] != 2 || out.stride()[1] != 1) {
        return fail(2);
    }

    float expected[4] = {1.0f, 2.7182817f, 0.3678794f, 7.389056f};
    for (int i = 0; i < 4; ++i) {
        if (absf(out_data[i] - expected[i]) > 1e-3f) {
            return fail(10 + i);
        }
    }
    return 0;
}
"""
    _compile_and_run(source)


# INC-NN-020
# 测试目的: 验证 cpu::exp 在 rank/shape/stride 不匹配时触发契约失败。
# 使用示例: pytest -q test/include/cpu/test_nn.py -k test_cpu_nn_exp_contract_violation_traps
# 对应功能实现文件路径: include/cpu/Nn.h
# 对应 spec 文件路径: spec/include/cpu/cpu.md
# 对应测试文件路径: test/include/cpu/test_nn.py
def test_cpu_nn_exp_contract_violation_traps() -> None:
    source = r"""
#include "include/cpu/Memory.h"
#include "include/cpu/Nn.h"

int main() {
    float in_data[4] = {0.0f, 1.0f, -1.0f, 2.0f};
    float out_data[4] = {0.0f, 0.0f, 0.0f, 0.0f};
    long long shape[2] = {2, 2};
    long long in_stride[2] = {2, 1};
    long long out_stride[2] = {3, 1};

    cpu::Memory<cpu::GM, float> value(in_data, 2, shape, in_stride);
    cpu::Memory<cpu::GM, float> out(out_data, 2, shape, out_stride);
    cpu::exp(value, out);
    return 0;
}
"""
    _compile_and_run_expect_failure(source)


# INC-NN-021
# 测试目的: 验证 cpu::reduce_sum 归约成功路径与 keepdim=false 输出契约。
# 使用示例: pytest -q test/include/cpu/test_nn.py -k test_cpu_nn_reduce_sum_success
# 对应功能实现文件路径: include/cpu/Nn.h
# 对应 spec 文件路径: spec/include/cpu/cpu.md
# 对应测试文件路径: test/include/cpu/test_nn.py
def test_cpu_nn_reduce_sum_success() -> None:
    source = r"""
#include "include/cpu/Memory.h"
#include "include/cpu/Nn.h"

static int fail(int code) { return code; }

int main() {
    float in_data[24] = {
        1, 2, 3, 4,
        5, 6, 7, 8,
        9, 10, 11, 12,
        13, 14, 15, 16,
        17, 18, 19, 20,
        21, 22, 23, 24
    };
    float out_data[2] = {0.0f, 0.0f};
    long long in_shape[3] = {2, 3, 4};
    long long in_stride[3] = {12, 4, 1};
    long long out_shape[1] = {2};
    long long out_stride[1] = {1};
    long long axes[2] = {1, 2};

    cpu::Memory<cpu::GM, float> value(in_data, 3, in_shape, in_stride);
    cpu::Memory<cpu::GM, float> out(out_data, 1, out_shape, out_stride);
    cpu::reduce_sum(value, out, axes, 2, false);

    if (out_data[0] != 78.0f || out_data[1] != 222.0f) {
        return fail(1);
    }
    return 0;
}
"""
    _compile_and_run(source)


# INC-NN-022
# 测试目的: 验证 cpu::reduce_sum 在轴集合非法时触发契约失败。
# 使用示例: pytest -q test/include/cpu/test_nn.py -k test_cpu_nn_reduce_sum_axis_contract_violation_traps
# 对应功能实现文件路径: include/cpu/Nn.h
# 对应 spec 文件路径: spec/include/cpu/cpu.md
# 对应测试文件路径: test/include/cpu/test_nn.py
def test_cpu_nn_reduce_sum_axis_contract_violation_traps() -> None:
    source = r"""
#include "include/cpu/Memory.h"
#include "include/cpu/Nn.h"

int main() {
    float in_data[24] = {0.0f};
    float out_data[2] = {0.0f, 0.0f};
    long long in_shape[3] = {2, 3, 4};
    long long in_stride[3] = {12, 4, 1};
    long long out_shape[1] = {2};
    long long out_stride[1] = {1};
    long long axes[2] = {2, 1};

    cpu::Memory<cpu::GM, float> value(in_data, 3, in_shape, in_stride);
    cpu::Memory<cpu::GM, float> out(out_data, 1, out_shape, out_stride);
    cpu::reduce_sum(value, out, axes, 2, false);
    return 0;
}
"""
    _compile_and_run_expect_failure(source)


# INC-NN-023
# 测试目的: 验证 cpu::reduce_min 归约成功路径与输出契约。
# 使用示例: pytest -q test/include/cpu/test_nn.py -k test_cpu_nn_reduce_min_success
# 对应功能实现文件路径: include/cpu/Nn.h
# 对应 spec 文件路径: spec/include/cpu/cpu.md
# 对应测试文件路径: test/include/cpu/test_nn.py
def test_cpu_nn_reduce_min_success() -> None:
    source = r"""
#include "include/cpu/Memory.h"
#include "include/cpu/Nn.h"

static int fail(int code) { return code; }

int main() {
    float in_data[12] = {
        1.0f, 3.0f,
        2.0f, 0.0f,
        -1.0f, 4.0f,
        5.0f, 6.0f,
        -2.0f, 7.0f,
        8.0f, 9.0f
    };
    float out_data[6] = {0.0f};
    long long in_shape[3] = {2, 3, 2};
    long long in_stride[3] = {6, 2, 1};
    long long out_shape[2] = {2, 3};
    long long out_stride[2] = {3, 1};
    long long axes[1] = {2};

    cpu::Memory<cpu::GM, float> value(in_data, 3, in_shape, in_stride);
    cpu::Memory<cpu::GM, float> out(out_data, 2, out_shape, out_stride);
    cpu::reduce_min(value, out, axes, 1, false);

    float expected[6] = {1.0f, 0.0f, -1.0f, 5.0f, -2.0f, 8.0f};
    for (int i = 0; i < 6; ++i) {
        if (out_data[i] != expected[i]) {
            return fail(i + 1);
        }
    }
    return 0;
}
"""
    _compile_and_run(source)


# INC-NN-024
# 测试目的: 验证 cpu::reduce_min 在空归约域时触发契约失败。
# 使用示例: pytest -q test/include/cpu/test_nn.py -k test_cpu_nn_reduce_min_empty_extent_traps
# 对应功能实现文件路径: include/cpu/Nn.h
# 对应 spec 文件路径: spec/include/cpu/cpu.md
# 对应测试文件路径: test/include/cpu/test_nn.py
def test_cpu_nn_reduce_min_empty_extent_traps() -> None:
    source = r"""
#include "include/cpu/Memory.h"
#include "include/cpu/Nn.h"

int main() {
    float in_data[1] = {0.0f};
    float out_data[6] = {0.0f};
    long long in_shape[3] = {2, 0, 3};
    long long in_stride[3] = {0, 0, 1};
    long long out_shape[2] = {2, 3};
    long long out_stride[2] = {3, 1};
    long long axes[1] = {1};

    cpu::Memory<cpu::GM, float> value(in_data, 3, in_shape, in_stride);
    cpu::Memory<cpu::GM, float> out(out_data, 2, out_shape, out_stride);
    cpu::reduce_min(value, out, axes, 1, false);
    return 0;
}
"""
    _compile_and_run_expect_failure(source)


# INC-NN-025
# 测试目的: 验证 cpu::reduce_max 归约成功路径与 keepdim=true 输出契约。
# 使用示例: pytest -q test/include/cpu/test_nn.py -k test_cpu_nn_reduce_max_success
# 对应功能实现文件路径: include/cpu/Nn.h
# 对应 spec 文件路径: spec/include/cpu/cpu.md
# 对应测试文件路径: test/include/cpu/test_nn.py
def test_cpu_nn_reduce_max_success() -> None:
    source = r"""
#include "include/cpu/Memory.h"
#include "include/cpu/Nn.h"

static int fail(int code) { return code; }

int main() {
    float in_data[4] = {1.0f, 5.0f, 3.0f, 2.0f};
    float out_data[2] = {0.0f, 0.0f};
    long long in_shape[2] = {2, 2};
    long long in_stride[2] = {2, 1};
    long long out_shape[2] = {1, 2};
    long long out_stride[2] = {2, 1};
    long long axes[1] = {0};

    cpu::Memory<cpu::GM, float> value(in_data, 2, in_shape, in_stride);
    cpu::Memory<cpu::GM, float> out(out_data, 2, out_shape, out_stride);
    cpu::reduce_max(value, out, axes, 1, true);

    if (out_data[0] != 3.0f || out_data[1] != 5.0f) {
        return fail(1);
    }
    return 0;
}
"""
    _compile_and_run(source)


# INC-NN-026
# 测试目的: 验证 cpu::reduce_max 在空归约域时触发契约失败。
# 使用示例: pytest -q test/include/cpu/test_nn.py -k test_cpu_nn_reduce_max_empty_extent_traps
# 对应功能实现文件路径: include/cpu/Nn.h
# 对应 spec 文件路径: spec/include/cpu/cpu.md
# 对应测试文件路径: test/include/cpu/test_nn.py
def test_cpu_nn_reduce_max_empty_extent_traps() -> None:
    source = r"""
#include "include/cpu/Memory.h"
#include "include/cpu/Nn.h"

int main() {
    float in_data[1] = {0.0f};
    float out_data[2] = {0.0f, 0.0f};
    long long in_shape[2] = {0, 2};
    long long in_stride[2] = {0, 1};
    long long out_shape[2] = {1, 2};
    long long out_stride[2] = {2, 1};
    long long axes[1] = {0};

    cpu::Memory<cpu::GM, float> value(in_data, 2, in_shape, in_stride);
    cpu::Memory<cpu::GM, float> out(out_data, 2, out_shape, out_stride);
    cpu::reduce_max(value, out, axes, 1, true);
    return 0;
}
"""
    _compile_and_run_expect_failure(source)

# INC-NN-027
# 测试目的: 验证 cpu::add 支持 Memory + scalar overload。
# 使用示例: pytest -q test/include/cpu/test_nn.py -k test_cpu_nn_add_scalar_rhs_success
# 对应功能实现文件路径: include/cpu/Nn.h
# 对应 spec 文件路径: spec/include/cpu/cpu.md
# 对应测试文件路径: test/include/cpu/test_nn.py
def test_cpu_nn_add_scalar_rhs_success() -> None:
    source = r"""
#include "include/cpu/Memory.h"
#include "include/cpu/Nn.h"

static int fail(int code) { return code; }

int main() {
    float lhs_data[6] = {1, 2, 3, 4, 5, 6};
    float out_data[6] = {0};
    long long shape[2] = {2, 3};
    long long stride[2] = {3, 1};

    cpu::Memory<cpu::GM, float> lhs(lhs_data, 2, shape, stride);
    cpu::Memory<cpu::GM, float> out(out_data, 2, shape, stride);

    cpu::add(lhs, 3.0f, out);

    if (out_data[0] != 4 || out_data[1] != 5 || out_data[5] != 9) {
        return fail(1);
    }
    return 0;
}
"""
    _compile_and_run(source)


# INC-NN-027A
# 测试目的: 验证 cpu::add 支持 `Memory<int32_t> + long long`，以承接 `memory + symbol.int` 的 CPU 公开口径。
# 使用示例: pytest -q test/include/cpu/test_nn.py -k test_cpu_nn_add_scalar_rhs_long_long_success
# 对应功能实现文件路径: include/cpu/Nn.h
# 对应 spec 文件路径: spec/include/cpu/cpu.md
# 对应测试文件路径: test/include/cpu/test_nn.py
def test_cpu_nn_add_scalar_rhs_long_long_success() -> None:
    source = r"""
#include <cstdint>
#include "include/cpu/Memory.h"
#include "include/cpu/Nn.h"

static int fail(int code) { return code; }

int main() {
    int32_t lhs_data[4] = {1, 2, 3, 4};
    int32_t out_data[4] = {0, 0, 0, 0};
    long long shape[2] = {2, 2};
    long long stride[2] = {2, 1};
    long long bias = 7;

    cpu::Memory<cpu::GM, int32_t> lhs(lhs_data, 2, shape, stride);
    cpu::Memory<cpu::GM, int32_t> out(out_data, 2, shape, stride);

    cpu::add(lhs, bias, out);

    if (out_data[0] != 8 || out_data[1] != 9 || out_data[2] != 10 || out_data[3] != 11) {
        return fail(1);
    }
    return 0;
}
"""
    _compile_and_run(source)


# INC-NN-028
# 测试目的: 验证 cpu::add 支持 scalar + Memory overload。
# 使用示例: pytest -q test/include/cpu/test_nn.py -k test_cpu_nn_add_scalar_lhs_success
# 对应功能实现文件路径: include/cpu/Nn.h
# 对应 spec 文件路径: spec/include/cpu/cpu.md
# 对应测试文件路径: test/include/cpu/test_nn.py
def test_cpu_nn_add_scalar_lhs_success() -> None:
    source = r"""
#include "include/cpu/Memory.h"
#include "include/cpu/Nn.h"

static int fail(int code) { return code; }

int main() {
    float rhs_data[6] = {6, 5, 4, 3, 2, 1};
    float out_data[6] = {0};
    long long shape[2] = {2, 3};
    long long stride[2] = {3, 1};

    cpu::Memory<cpu::GM, float> rhs(rhs_data, 2, shape, stride);
    cpu::Memory<cpu::GM, float> out(out_data, 2, shape, stride);

    cpu::add(2.0f, rhs, out);

    if (out_data[0] != 8 || out_data[1] != 7 || out_data[5] != 3) {
        return fail(1);
    }
    return 0;
}
"""
    _compile_and_run(source)
