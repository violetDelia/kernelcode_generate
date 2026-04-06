"""API NN compile tests.

创建者: 小李飞刀
最后一次更改: 金铲铲大作战

功能说明:
- 通过编译并运行 C++ 片段验证 `include/api/Nn.h` 的逐元素运算声明，
  并使用 `include/npu_demo/Nn.h` 提供实现。

覆盖率信息:
- 当前覆盖率: `N/A`。该链路为 C++ 头文件，按规则豁免 `pytest-cov` 覆盖率统计。
- 达标判定: C++ 头文件实现按规则豁免 `95%` 覆盖率达标线。
- 当前覆盖基线: `API-NN-001..002`。

覆盖率命令:
- `pytest -q test/include/api/test_nn.py`
- `N/A`（C++ 头文件实现，按当前规则豁免 `pytest-cov` 覆盖率统计）

使用示例:
- `pytest -q test/include/api/test_nn.py`

关联文件:
- 功能实现: [`include/npu_demo/Nn.h`](include/npu_demo/Nn.h)
- Spec 文档: [`spec/include/api/Nn.md`](spec/include/api/Nn.md)
- 测试文件: [`test/include/api/test_nn.py`](test/include/api/test_nn.py)
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
    - spec: [`spec/include/api/Nn.md`](spec/include/api/Nn.md)
    - test: [`test/include/api/test_nn.py`](test/include/api/test_nn.py)
    - 功能实现: [`test/include/api/test_nn.py`](test/include/api/test_nn.py)
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


# API-NN-001
# 创建者: 小李飞刀
# 最后一次更改: 金铲铲大作战
# 功能说明: 验证 NN 逐元素算子声明可编译并在基础数据上运行通过。
# 最近一次运行测试时间: 2026-04-05 23:44:24 +0800
# 最近一次运行成功时间: 2026-04-05 23:44:24 +0800
# 测试目的: 验证 `include/api/Nn.h` 公开声明可配合 `npu_demo` 后端实例化，并覆盖 `add` 基础路径。
# 使用示例: `pytest -q test/include/api/test_nn.py -k test_nn_compare_ops_keep_same_space_template`
# 对应功能实现文件路径: `include/npu_demo/Nn.h`
# 对应 spec 文件路径: `spec/include/api/Nn.md`
# 对应测试文件路径: `test/include/api/test_nn.py`
def test_nn_compare_ops_keep_same_space_template() -> None:
    source = r"""
#include "include/api/Nn.h"
#include "include/npu_demo/Nn.h"

static int fail(int code) { return code; }

int main() {
    float lhs_data[4] = {1.0f, 2.0f, 3.0f, 4.0f};
    float rhs_data[4] = {10.0f, 20.0f, 30.0f, 40.0f};
    float out_data[4] = {0};
    int pred_data[4] = {0};
    long long shape[1] = {4};
    long long stride[1] = {1};

    Memory<GM, float> lhs(lhs_data, shape, stride, 1, MemoryFormat::Norm);
    Memory<GM, float> rhs(rhs_data, shape, stride, 1, MemoryFormat::Norm);
    Memory<GM, float> out(out_data, shape, stride, 1, MemoryFormat::Norm);
    Memory<GM, int> pred(pred_data, shape, stride, 1, MemoryFormat::Norm);

    if (add(lhs, rhs, out) != StatusCode::kOk) {
        return fail(1);
    }
    if (out_data[0] != 11.0f || out_data[1] != 22.0f || out_data[2] != 33.0f || out_data[3] != 44.0f) {
        return fail(2);
    }

    if (sub(lhs, rhs, out) != StatusCode::kOk) {
        return fail(3);
    }
    if (mul(lhs, rhs, out) != StatusCode::kOk) {
        return fail(4);
    }
    if (truediv(lhs, rhs, out) != StatusCode::kOk) {
        return fail(5);
    }
    if (eq(lhs, rhs, pred) != StatusCode::kOk) {
        return fail(6);
    }
    if (ne(lhs, rhs, pred) != StatusCode::kOk) {
        return fail(7);
    }
    if (lt(lhs, rhs, pred) != StatusCode::kOk) {
        return fail(8);
    }
    if (le(lhs, rhs, pred) != StatusCode::kOk) {
        return fail(9);
    }
    if (gt(lhs, rhs, pred) != StatusCode::kOk) {
        return fail(10);
    }
    if (ge(lhs, rhs, pred) != StatusCode::kOk) {
        return fail(11);
    }
    if (broadcast(lhs, out) != StatusCode::kOk) {
        return fail(12);
    }
    return 0;
}
"""
    _compile_and_run(source)


# API-NN-002
# 创建者: 小李飞刀
# 最后一次更改: 金铲铲大作战
# 功能说明: 验证 add 在 shape/rank 不满足时返回失败而非静默成功。
# 最近一次运行测试时间: 2026-04-05 23:44:24 +0800
# 最近一次运行成功时间: 2026-04-05 23:44:24 +0800
# 测试目的: 验证 `add` 在 shape 或 rank 不满足公开约束时返回失败状态，而不是静默成功。
# 使用示例: `pytest -q test/include/api/test_nn.py -k test_nn_same_space_template_rejects_invalid_shape_or_rank`
# 对应功能实现文件路径: `include/npu_demo/Nn.h`
# 对应 spec 文件路径: `spec/include/api/Nn.md`
# 对应测试文件路径: `test/include/api/test_nn.py`
def test_nn_same_space_template_rejects_invalid_shape_or_rank() -> None:
    source = r"""
#include "include/api/Nn.h"
#include "include/npu_demo/Nn.h"

static int fail(int code) { return code; }

int main() {
    float lhs_data[4] = {1.0f, 2.0f, 3.0f, 4.0f};
    float rhs_data[4] = {10.0f, 20.0f, 30.0f, 40.0f};
    float out_data[4] = {0};
    long long shape[1] = {4};
    long long short_shape[1] = {3};
    long long stride[1] = {1};
    long long rank2_shape[2] = {2, 2};
    long long rank2_stride[2] = {2, 1};

    Memory<GM, float> lhs(lhs_data, shape, stride, 1, MemoryFormat::Norm);
    Memory<GM, float> rhs(rhs_data, shape, stride, 1, MemoryFormat::Norm);
    Memory<GM, float> out(out_data, shape, stride, 1, MemoryFormat::Norm);
    Memory<GM, float> bad_shape(lhs_data, short_shape, stride, 1, MemoryFormat::Norm);
    Memory<GM, float> bad_rank(lhs_data, rank2_shape, rank2_stride, 2, MemoryFormat::Norm);

    if (add(bad_shape, rhs, out) == StatusCode::kOk) {
        return fail(1);
    }
    if (add(lhs, bad_shape, out) == StatusCode::kOk) {
        return fail(2);
    }
    if (add(lhs, rhs, bad_shape) == StatusCode::kOk) {
        return fail(3);
    }
    if (add(bad_rank, rhs, out) == StatusCode::kOk) {
        return fail(4);
    }
    if (add(lhs, bad_rank, out) == StatusCode::kOk) {
        return fail(5);
    }
    if (add(lhs, rhs, bad_rank) == StatusCode::kOk) {
        return fail(6);
    }
    return 0;
}
"""
    _compile_and_run(source)


# API-NN-003
# 创建者: 金铲铲大作战
# 最后一次更改: 金铲铲大作战
# 功能说明: 验证 broadcast 在同一空间模板参数下可编译并返回成功。
# 最近一次运行测试时间: N/A
# 最近一次运行成功时间: N/A
# 测试目的: 验证 `broadcast` 在 `Memory<Space, T>` 口径下保持公开调用形态。
# 使用示例: `pytest -q test/include/api/test_nn.py -k test_nn_broadcast_keeps_space_template`
# 对应功能实现文件路径: `include/npu_demo/Nn.h`
# 对应 spec 文件路径: `spec/include/api/Nn.md`
# 对应测试文件路径: `test/include/api/test_nn.py`
def test_nn_broadcast_keeps_space_template() -> None:
    source = r"""
#include "include/api/Nn.h"
#include "include/npu_demo/Nn.h"

static int fail(int code) { return code; }

int main() {
    float input_data[4] = {1.0f, 2.0f, 3.0f, 4.0f};
    float out_data[4] = {0};
    long long shape[1] = {4};
    long long stride[1] = {1};

    Memory<GM, float> input(input_data, shape, stride, 1, MemoryFormat::Norm);
    Memory<GM, float> out(out_data, shape, stride, 1, MemoryFormat::Norm);

    if (broadcast(input, out) != StatusCode::kOk) {
        return fail(1);
    }
    return 0;
}
"""
    _compile_and_run(source)
