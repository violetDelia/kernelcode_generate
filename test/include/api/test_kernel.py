"""API Kernel compile tests.

创建者: 小李飞刀
最后一次更改: 守护最好的爱莉希雅

功能说明:
- 通过编译并运行 C++ 片段验证 `include/api/Kernel.h` 的公开 helper 声明，
  并使用 `include/npu_demo/Kernel.h` 提供实现。

覆盖率信息:
- 当前覆盖率: `N/A`。该链路为 C++ 头文件，按规则豁免 `pytest-cov` 覆盖率统计。
- 达标判定: C++ 头文件实现按规则豁免 `95%` 覆盖率达标线。

覆盖率命令:
- `pytest -q test/include/api/test_kernel.py`
- `N/A`（C++ 头文件实现，按当前规则豁免 `pytest-cov` 覆盖率统计）

使用示例:
- `pytest -q test/include/api/test_kernel.py`

关联文件:
- 功能实现: [`include/api/Kernel.h`](include/api/Kernel.h)
- 功能实现: [`include/npu_demo/Kernel.h`](include/npu_demo/Kernel.h)
- Spec 文档: [`spec/include/api/Kernel.md`](spec/include/api/Kernel.md)
- 测试文件: [`test/include/api/test_kernel.py`](test/include/api/test_kernel.py)
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
    - spec: [`spec/include/api/Kernel.md`](spec/include/api/Kernel.md)
    - test: [`test/include/api/test_kernel.py`](test/include/api/test_kernel.py)
    - 功能实现: [`test/include/api/test_kernel.py`](test/include/api/test_kernel.py)
    """

    with tempfile.TemporaryDirectory() as tmpdir:
        source_path = Path(tmpdir) / "kernel_test.cpp"
        binary_path = Path(tmpdir) / "kernel_test"
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


def _compile_expect_failure(source: str) -> str:
    """编译并断言 C++ 片段失败，返回编译 stderr。

    创建者: 小李飞刀
    最后一次更改: 小李飞刀

    功能说明:
    - 使用 `g++` 编译临时源码，并验证其因公开接口顺序错误而失败。

    使用示例:
    - `stderr = _compile_expect_failure("int main() { return missing; }")`

    关联文件:
    - spec: [`spec/include/api/Kernel.md`](spec/include/api/Kernel.md)
    - test: [`test/include/api/test_kernel.py`](test/include/api/test_kernel.py)
    - 功能实现: [`test/include/api/test_kernel.py`](test/include/api/test_kernel.py)
    """

    with tempfile.TemporaryDirectory() as tmpdir:
        source_path = Path(tmpdir) / "kernel_test_fail.cpp"
        binary_path = Path(tmpdir) / "kernel_test_fail"
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
            raise AssertionError("expected g++ compile failure, but compile succeeded")
        return compile_result.stderr


# API-KERNEL-001
# 创建者: 小李飞刀
# 最后一次更改: 小李飞刀
# 最近一次运行测试时间: N/A
# 最近一次运行成功时间: N/A
# 测试目的: 验证 `Kernel` 公共层只保留新 helper 集合，并且公共 `Nn` 头文件已删除。
# 使用示例: `pytest -q test/include/api/test_kernel.py -k test_include_api_kernel_exports_only_public_kernel_helpers`
# 对应功能实现文件路径: `include/api/Kernel.h`
# 对应 spec 文件路径: `spec/include/api/Kernel.md`
# 对应测试文件路径: `test/include/api/test_kernel.py`
def test_include_api_kernel_exports_only_public_kernel_helpers() -> None:
    public_header = (REPO_ROOT / "include" / "api" / "Kernel.h").read_text(encoding="utf-8")
    npu_demo_entry = (REPO_ROOT / "include" / "npu_demo" / "npu_demo.h").read_text(encoding="utf-8")

    assert "namespace npu_demo" in public_header
    assert "Status add(" in public_header
    assert "Status matmul(" in public_header
    assert "Status img2col2d(" in public_header
    assert "Status reduce_max(" in public_header
    assert "Status broadcast(" not in public_header
    assert "Status softmax(" not in public_header
    assert not (REPO_ROOT / "include" / "api" / "Nn.h").exists()
    assert not (REPO_ROOT / "include" / "npu_demo" / "Nn.h").exists()
    assert '#include "include/npu_demo/Nn.h"' not in npu_demo_entry


# API-KERNEL-002
# 创建者: 小李飞刀
# 最后一次更改: 守护最好的爱莉希雅
# 最近一次运行测试时间: N/A
# 最近一次运行成功时间: N/A
# 测试目的: 验证 `Kernel` 公共层可按 `out-first` 口径编译并运行 add/matmul 基础路径。
# 使用示例: `pytest -q test/include/api/test_kernel.py -k test_include_api_kernel_compiles_out_first_helpers`
# 对应功能实现文件路径: `include/npu_demo/Kernel.h`
# 对应 spec 文件路径: `spec/include/api/Kernel.md`
# 对应测试文件路径: `test/include/api/test_kernel.py`
def test_include_api_kernel_compiles_out_first_helpers() -> None:
    source = r"""
#include "include/api/Kernel.h"
#include "include/npu_demo/Kernel.h"

static int fail(int code) { return code; }

int main() {
    float lhs_data[4] = {1.0f, 2.0f, 3.0f, 4.0f};
    float rhs_data[4] = {10.0f, 20.0f, 30.0f, 40.0f};
    float out_data[4] = {0.0f, 0.0f, 0.0f, 0.0f};
    long long vec_shape[1] = {4};
    long long vec_stride[1] = {1};
    Memory<GM, float> lhs(lhs_data, vec_shape, vec_stride, 1, MemoryFormat::Norm);
    Memory<GM, float> rhs(rhs_data, vec_shape, vec_stride, 1, MemoryFormat::Norm);
    Memory<GM, float> out(out_data, vec_shape, vec_stride, 1, MemoryFormat::Norm);

    if (npu_demo::add<GM, float, float>(out, lhs, rhs) != StatusCode::kOk) {
        return fail(1);
    }
    if (out_data[0] != 11.0f || out_data[1] != 22.0f || out_data[2] != 33.0f || out_data[3] != 44.0f) {
        return fail(2);
    }

    float lhs_matmul_data[4] = {1.0f, 2.0f, 3.0f, 4.0f};
    float rhs_matmul_data[4] = {5.0f, 6.0f, 7.0f, 8.0f};
    float out_matmul_data[4] = {0.0f, 0.0f, 0.0f, 0.0f};
    long long mat_shape[2] = {2, 2};
    long long mat_stride[2] = {2, 1};
    Memory<TSM, float> lhs_mat(lhs_matmul_data, mat_shape, mat_stride, 2, MemoryFormat::Norm);
    Memory<TSM, float> rhs_mat(rhs_matmul_data, mat_shape, mat_stride, 2, MemoryFormat::Norm);
    Memory<TLM1, float> out_mat(out_matmul_data, mat_shape, mat_stride, 2, MemoryFormat::Norm);

    if (npu_demo::matmul<TSM, TSM, TLM1, float, float, float>(out_mat, lhs_mat, rhs_mat) != StatusCode::kOk) {
        return fail(3);
    }
    if (out_matmul_data[0] != 19.0f || out_matmul_data[1] != 22.0f ||
        out_matmul_data[2] != 43.0f || out_matmul_data[3] != 50.0f) {
        return fail(4);
    }

    float reduce_data[6] = {1.0f, 9.0f, 3.0f, 7.0f, 2.0f, 5.0f};
    float reduce_out_data[2] = {0.0f, 0.0f};
    long long reduce_shape[2] = {2, 3};
    long long reduce_stride[2] = {3, 1};
    long long reduce_out_shape[2] = {2, 1};
    long long reduce_out_stride[2] = {1, 1};
    Memory<TSM, float> reduce_input(reduce_data, reduce_shape, reduce_stride, 2, MemoryFormat::Norm);
    Memory<TSM, float> reduce_out(reduce_out_data, reduce_out_shape, reduce_out_stride, 2, MemoryFormat::Norm);
    if (npu_demo::reduce_max<TSM, float, float>(reduce_out, reduce_input, 1) != StatusCode::kOk) {
        return fail(5);
    }
    if (reduce_out_data[0] != 9.0f || reduce_out_data[1] != 7.0f) {
        return fail(6);
    }
    return 0;
}
"""
    _compile_and_run(source)


# API-KERNEL-003
# 创建者: 小李飞刀
# 最后一次更改: 小李飞刀
# 最近一次运行测试时间: N/A
# 最近一次运行成功时间: N/A
# 测试目的: 验证旧 `lhs/rhs/out` 顺序不再属于公开 `Kernel` helper 合同。
# 使用示例: `pytest -q test/include/api/test_kernel.py -k test_include_api_kernel_rejects_old_lhs_rhs_out_order`
# 对应功能实现文件路径: `include/api/Kernel.h`
# 对应 spec 文件路径: `spec/include/api/Kernel.md`
# 对应测试文件路径: `test/include/api/test_kernel.py`
def test_include_api_kernel_rejects_old_lhs_rhs_out_order() -> None:
    stderr = _compile_expect_failure(
        r"""
#include "include/api/Kernel.h"
#include "include/npu_demo/Kernel.h"

int main() {
    float lhs_data[1] = {1.0f};
    float rhs_data[1] = {2.0f};
    bool out_data[1] = {false};
    long long shape[1] = {1};
    long long stride[1] = {1};
    Memory<GM, float> lhs(lhs_data, shape, stride, 1, MemoryFormat::Norm);
    Memory<GM, float> rhs(rhs_data, shape, stride, 1, MemoryFormat::Norm);
    Memory<GM, bool> out(out_data, shape, stride, 1, MemoryFormat::Norm);
    return npu_demo::add<GM, float, bool>(lhs, rhs, out);
}
"""
    )
    assert "invalid initialization of reference" in stderr
    assert "Memory<MemorySpace::GM, bool>&" in stderr
