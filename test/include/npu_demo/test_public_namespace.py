"""NPU demo public namespace compile tests.

创建者: jcc你莫辜负
最后一次更改: jcc你莫辜负

功能说明:
- 通过编译并运行 C++ 片段验证 include/npu_demo/npu_demo.h 的最小 public function namespace 消费面。
- 覆盖 `Vector{...}` 用作 Memory shape/stride，以及 `npu_demo::add` / `npu_demo::launch` 的正向调用。

覆盖率信息:
- 当前覆盖率: `N/A`。该链路为 C++ 头文件，按规则豁免 `pytest-cov` 覆盖率统计。
- 达标判定: C++ 头文件实现按规则豁免 `95%` 覆盖率达标线。
- 当前覆盖基线: `NPU-DEMO-PUBLIC-001`。

覆盖率命令:
- `pytest -q test/include/npu_demo/test_public_namespace.py`
- `N/A`（C++ 头文件实现，按当前规则豁免 `pytest-cov` 覆盖率统计）

使用示例:
- pytest -q test/include/npu_demo/test_public_namespace.py

关联文件:
- spec: [spec/include/npu_demo/npu_demo.md](spec/include/npu_demo/npu_demo.md)
- test: [test/include/npu_demo/test_public_namespace.py](test/include/npu_demo/test_public_namespace.py)
- 功能实现: [include/npu_demo/npu_demo.h](include/npu_demo/npu_demo.h)
"""

from __future__ import annotations

import subprocess
import tempfile
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]


def _compile_and_run(source: str) -> None:
    """编译并运行 C++ public namespace 测试片段。

    创建者: jcc你莫辜负
    最后一次更改: jcc你莫辜负

    功能说明:
    - 使用 `g++ -std=c++17 -pthread` 编译临时源码并执行生成程序。

    使用示例:
    - _compile_and_run("int main() { return 0; }")

    关联文件:
    - spec: [spec/include/npu_demo/npu_demo.md](spec/include/npu_demo/npu_demo.md)
    - test: [test/include/npu_demo/test_public_namespace.py](test/include/npu_demo/test_public_namespace.py)
    - 功能实现: [test/include/npu_demo/test_public_namespace.py](test/include/npu_demo/test_public_namespace.py)
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        source_path = Path(tmpdir) / "npu_demo_public_namespace.cpp"
        binary_path = Path(tmpdir) / "npu_demo_public_namespace"
        source_path.write_text(source, encoding="utf-8")

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
    """编译并断言 C++ public namespace 测试片段失败。

    创建者: 小李飞刀
    最后一次更改: 小李飞刀

    功能说明:
    - 使用 `g++ -std=c++17 -pthread` 编译临时源码，并返回失败 stderr。
    - 用于验证旧全局 public function 消费面不再作为成功路径。

    使用示例:
    - stderr = _compile_expect_failure("int main() { return missing; }")

    关联文件:
    - spec: [spec/include/npu_demo/npu_demo.md](spec/include/npu_demo/npu_demo.md)
    - test: [test/include/npu_demo/test_public_namespace.py](test/include/npu_demo/test_public_namespace.py)
    - 功能实现: [test/include/npu_demo/test_public_namespace.py](test/include/npu_demo/test_public_namespace.py)
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        source_path = Path(tmpdir) / "npu_demo_public_namespace_fail.cpp"
        binary_path = Path(tmpdir) / "npu_demo_public_namespace_fail"
        source_path.write_text(source, encoding="utf-8")

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


# NPU-DEMO-PUBLIC-001
# 创建者: jcc你莫辜负
# 最后一次更改: jcc你莫辜负
# 最近一次运行测试时间: 2026-04-21 21:00:00 +0800
# 最近一次运行成功时间: 2026-04-21 21:00:00 +0800
# 测试目的: 验证 npu_demo public function 最小正向调用可通过单入口头文件编译运行。
# 使用示例: pytest -q test/include/npu_demo/test_public_namespace.py -k test_npu_demo_public_namespace_smoke_compiles_vector_kernel_and_launch
# 对应功能实现文件链接: [include/npu_demo/npu_demo.h](include/npu_demo/npu_demo.h)
# 对应 spec 文件链接: [spec/include/npu_demo/npu_demo.md](spec/include/npu_demo/npu_demo.md)
# 对应测试文件链接: [test/include/npu_demo/test_public_namespace.py](test/include/npu_demo/test_public_namespace.py)
def test_npu_demo_public_namespace_smoke_compiles_vector_kernel_and_launch() -> None:
    source = r"""
#include "include/npu_demo/npu_demo.h"

static int fail(int code) {
    return code;
}

static void kernel_body(npu_demo::KernelContext& ctx, long long* thread_nums) {
    thread_nums[ctx.thread_id()] = ctx.thread_num();
}

int main() {
    Vector shape{2};
    Vector stride = {1};

    float lhs_data[2] = {1.5f, 2.5f};
    float rhs_data[2] = {2.0f, 3.0f};
    float out_data[2] = {0.0f, 0.0f};

    Memory<GM, float> lhs(lhs_data, shape.data(), stride.data(), shape.size(), MemoryFormat::Norm);
    Memory<GM, float> rhs(rhs_data, shape.data(), stride.data(), shape.size(), MemoryFormat::Norm);
    Memory<GM, float> out(out_data, shape.data(), stride.data(), shape.size(), MemoryFormat::Norm);

    Status add_status = npu_demo::add<GM, float, float>(out, lhs, rhs);
    if (add_status != StatusCode::kOk) {
        return fail(1);
    }
    if (out_data[0] != 3.5f || out_data[1] != 5.5f) {
        return fail(2);
    }

    long long thread_nums[2] = {0, 0};
    Status launch_status = npu_demo::launch<1, 2, 1, 0>(kernel_body, &thread_nums[0]);
    if (launch_status != StatusCode::kOk) {
        return fail(3);
    }
    if (thread_nums[0] != 2 || thread_nums[1] != 2) {
        return fail(4);
    }

    return 0;
}
"""
    assert "npu_demo::add" in source
    assert "npu_demo::launch" in source
    assert "npu_demo::detail" not in source
    assert "npu_demo_dma_detail" not in source
    assert "npu_demo_memory_detail" not in source
    _compile_and_run(source)


# NPU-DEMO-PUBLIC-002
# 创建者: 小李飞刀
# 最后一次更改: 小李飞刀
# 最近一次运行测试时间: N/A
# 最近一次运行成功时间: N/A
# 测试目的: 验证 Memory/Dma public function 通过 npu_demo:: 命名空间调用，且 Vector{...} 可直接作为参数。
# 使用示例: pytest -q test/include/npu_demo/test_public_namespace.py -k test_npu_demo_public_namespace_memory_dma_helpers
# 对应功能实现文件链接: [include/npu_demo/npu_demo.h](include/npu_demo/npu_demo.h)
# 对应 spec 文件链接: [spec/include/npu_demo/npu_demo.md](spec/include/npu_demo/npu_demo.md)
# 对应测试文件链接: [test/include/npu_demo/test_public_namespace.py](test/include/npu_demo/test_public_namespace.py)
def test_npu_demo_public_namespace_memory_dma_helpers() -> None:
    source = r"""
#include "include/npu_demo/npu_demo.h"

static int fail(int code) {
    return code;
}

int main() {
    long long stride_buf[2] = {0, 0};
    long long shape_buf[2] = {2, 2};
    npu_demo::build_contiguous_stride(shape_buf, 2, stride_buf);
    if (stride_buf[0] != 2 || stride_buf[1] != 1) {
        return fail(1);
    }

    float line_data[4] = {1.0f, 2.0f, 3.0f, 4.0f};
    Memory<GM, float> line(line_data, Vector{4}.data(), Vector{1}.data(), 1, MemoryFormat::Norm);
    Memory<GM, float> row = npu_demo::view(line, 1, 2, 1);
    if (row.rank() != 1 || row.get_shape(0) != 2 || row.data() != line.data() + 1) {
        return fail(2);
    }

    auto tile = npu_demo::alloc<TSM, float>({2}, {1}, MemoryFormat::Norm);
    if (tile.rank() != 1 || tile.get_shape(0) != 2 || tile.get_stride(0) != 1) {
        return fail(3);
    }

    if (npu_demo::slice(tile, line, Vector{1}, Vector{2}, Vector{1}) != StatusCode::kOk) {
        return fail(4);
    }
    if (tile.data()[0] != 2.0f || tile.data()[1] != 3.0f) {
        return fail(5);
    }

    float target_data[4] = {0.0f, 0.0f, 0.0f, 0.0f};
    Memory<GM, float> target(target_data, Vector{4}.data(), Vector{1}.data(), 1, MemoryFormat::Norm);
    if (npu_demo::deslice(target, tile, Vector{1}, Vector{2}, Vector{1}) != StatusCode::kOk) {
        return fail(6);
    }
    if (target_data[1] != 2.0f || target_data[2] != 3.0f) {
        return fail(7);
    }
    return 0;
}
"""
    assert "npu_demo::build_contiguous_stride" in source
    assert "npu_demo::view" in source
    assert "npu_demo::alloc" in source
    assert "npu_demo::slice" in source
    assert "npu_demo::deslice" in source
    assert "npu_demo::detail" not in source
    assert "npu_demo_dma_detail" not in source
    assert "npu_demo_memory_detail" not in source
    _compile_and_run(source)


# NPU-DEMO-PUBLIC-003
# 创建者: 小李飞刀
# 最后一次更改: 小李飞刀
# 最近一次运行测试时间: N/A
# 最近一次运行成功时间: N/A
# 测试目的: 验证旧全局 Memory/Dma helper 不再作为成功消费面。
# 使用示例: pytest -q test/include/npu_demo/test_public_namespace.py -k test_npu_demo_public_namespace_rejects_global_memory_dma_helpers
# 对应功能实现文件链接: [include/npu_demo/npu_demo.h](include/npu_demo/npu_demo.h)
# 对应 spec 文件链接: [spec/include/npu_demo/npu_demo.md](spec/include/npu_demo/npu_demo.md)
# 对应测试文件链接: [test/include/npu_demo/test_public_namespace.py](test/include/npu_demo/test_public_namespace.py)
def test_npu_demo_public_namespace_rejects_global_memory_dma_helpers() -> None:
    stderr = _compile_expect_failure(
        r"""
#include "include/npu_demo/npu_demo.h"

int main() {
    long long shape[1] = {1};
    long long stride[1] = {0};
    build_contiguous_stride(shape, 1, stride);
    return 0;
}
"""
    )
    assert "build_contiguous_stride" in stderr

    stderr = _compile_expect_failure(
        r"""
#include "include/npu_demo/npu_demo.h"

int main() {
    auto tile = alloc<TSM, float>({1}, {1});
    return tile.rank() == 1 ? 0 : 1;
}
"""
    )
    assert "alloc" in stderr

    headers = "\n".join(
        [
            (REPO_ROOT / "include" / "npu_demo" / "Memory.h").read_text(encoding="utf-8"),
            (REPO_ROOT / "include" / "npu_demo" / "Dma.h").read_text(encoding="utf-8"),
        ]
    )
    assert "npu_demo_dma_detail" not in headers
    assert "npu_demo_memory_detail" not in headers
