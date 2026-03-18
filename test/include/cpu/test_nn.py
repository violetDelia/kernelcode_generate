"""CPU NN include tests.

创建者: 小李飞刀
最后一次更改: 小李飞刀

功能说明:
- 通过编译并运行 C++ 片段验证 include/cpu/Nn.h 的逐元素与 broadcast 语义。

使用示例:
- pytest -q test/include/cpu/test_nn.py

关联文件:
- 功能实现: include/cpu/Nn.h
- Spec 文档: spec/include/cpu/Nn.md
- 测试文件: test/include/cpu/test_nn.py
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
    - 使用 g++ 编译临时源码并执行生成的程序。

    使用示例:
    - _compile_and_run("int main() { return 0; }")

    关联文件:
    - spec: spec/include/cpu/Nn.md
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


# INC-NN-001
# 创建者: 小李飞刀
# 最后一次更改: 小李飞刀
# 最近一次运行测试时间: 2026-03-19 04:07:35 +0800
# 最近一次运行成功时间: 2026-03-19 04:07:35 +0800
# 功能说明: 验证逐元素加法输出正确。
# 使用示例: pytest -q test/include/cpu/test_nn.py -k test_cpu_nn_add_success
# 对应功能实现文件路径: include/cpu/Nn.h
# 对应 spec 文件路径: spec/include/cpu/Nn.md
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

    cpu::Memory<float, 2> lhs(lhs_data, shape, stride);
    cpu::Memory<float, 2> rhs(rhs_data, shape, stride);
    cpu::Memory<float, 2> out(out_data, shape, stride);

    cpu::add(lhs, rhs, out);

    if (out_data[0] != 7 || out_data[1] != 7 || out_data[5] != 7) {
        return fail(1);
    }
    return 0;
}
"""
    _compile_and_run(source)


# INC-NN-002
# 创建者: 小李飞刀
# 最后一次更改: 小李飞刀
# 最近一次运行测试时间: 2026-03-19 04:07:35 +0800
# 最近一次运行成功时间: 2026-03-19 04:07:35 +0800
# 功能说明: 验证逐元素比较输出 predicate 语义结果。
# 使用示例: pytest -q test/include/cpu/test_nn.py -k test_cpu_nn_compare_eq
# 对应功能实现文件路径: include/cpu/Nn.h
# 对应 spec 文件路径: spec/include/cpu/Nn.md
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

    cpu::Memory<float, 2> lhs(lhs_data, shape, stride);
    cpu::Memory<float, 2> rhs(rhs_data, shape, stride);
    cpu::Memory<int, 2> out(out_data, shape, stride);

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
# 创建者: 小李飞刀
# 最后一次更改: 小李飞刀
# 最近一次运行测试时间: 2026-03-19 04:07:35 +0800
# 最近一次运行成功时间: 2026-03-19 04:07:35 +0800
# 功能说明: 验证 broadcast 支持 singleton 扩张。
# 使用示例: pytest -q test/include/cpu/test_nn.py -k test_cpu_nn_broadcast_success
# 对应功能实现文件路径: include/cpu/Nn.h
# 对应 spec 文件路径: spec/include/cpu/Nn.md
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

    cpu::Memory<float, 2> input(in_data, in_shape, in_stride);
    cpu::Memory<float, 2> out(out_data, out_shape, out_stride);

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
# 创建者: 小李飞刀
# 最后一次更改: 小李飞刀
# 最近一次运行测试时间: 2026-03-19 04:07:35 +0800
# 最近一次运行成功时间: 2026-03-19 04:07:35 +0800
# 功能说明: 验证 broadcast 支持前置维插入。
# 使用示例: pytest -q test/include/cpu/test_nn.py -k test_cpu_nn_broadcast_prepend_dim
# 对应功能实现文件路径: include/cpu/Nn.h
# 对应 spec 文件路径: spec/include/cpu/Nn.md
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

    cpu::Memory<float, 1> input(in_data, in_shape, in_stride);
    cpu::Memory<float, 2> out(out_data, out_shape, out_stride);

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
# 创建者: 小李飞刀
# 最后一次更改: 小李飞刀
# 最近一次运行测试时间: 2026-03-19 04:07:35 +0800
# 最近一次运行成功时间: 2026-03-19 04:07:35 +0800
# 功能说明: 验证逐元素乘法输出正确。
# 使用示例: pytest -q test/include/cpu/test_nn.py -k test_cpu_nn_mul_success
# 对应功能实现文件路径: include/cpu/Nn.h
# 对应 spec 文件路径: spec/include/cpu/Nn.md
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

    cpu::Memory<int, 2> lhs(lhs_data, shape, stride);
    cpu::Memory<int, 2> rhs(rhs_data, shape, stride);
    cpu::Memory<int, 2> out(out_data, shape, stride);

    cpu::mul(lhs, rhs, out);

    if (out_data[0] != 2 || out_data[1] != 4 || out_data[5] != 12) {
        return fail(1);
    }
    return 0;
}
"""
    _compile_and_run(source)
