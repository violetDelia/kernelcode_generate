"""API cost compile tests.

创建者: 金铲铲大作战
最后一次更改: 守护最好的爱莉希雅

功能说明:
- 通过编译并运行 C++ 片段验证 `include/api/cost/*.h` 的公开成本 helper 声明。
- 结合 `include/npu_demo/cost/*.h` 提供的默认实现，锁定 compute / memory / DMA / MAC 四种 kind 与 `S_INT` 返回合同。

覆盖率信息:
- 当前覆盖率: `N/A`。该链路为 C++ 头文件，按规则豁免 `pytest-cov` 覆盖率统计。
- 达标判定: C++ 头文件实现按规则豁免 `95%` 覆盖率达标线。

使用示例:
- `pytest -q test/include/api/test_cost.py`

关联文件:
- 功能实现: [`include/api/cost/Core.h`](include/api/cost/Core.h)
- 功能实现: [`include/api/cost/Dma.h`](include/api/cost/Dma.h)
- 功能实现: [`include/api/cost/Kernel.h`](include/api/cost/Kernel.h)
- 功能实现: [`include/npu_demo/cost/Core.h`](include/npu_demo/cost/Core.h)
- 功能实现: [`include/npu_demo/cost/Dma.h`](include/npu_demo/cost/Dma.h)
- 功能实现: [`include/npu_demo/cost/Kernel.h`](include/npu_demo/cost/Kernel.h)
- Spec 文档: [`spec/include/api/cost/Core.md`](spec/include/api/cost/Core.md)
- Spec 文档: [`spec/include/api/cost/Dma.md`](spec/include/api/cost/Dma.md)
- Spec 文档: [`spec/include/api/cost/Kernel.md`](spec/include/api/cost/Kernel.md)
- 测试文件: [`test/include/api/test_cost.py`](test/include/api/test_cost.py)
"""

from __future__ import annotations

import subprocess
import tempfile
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]


def _compile_and_run(source: str) -> None:
    """编译并运行 C++ 成本接口测试片段。

    创建者: 金铲铲大作战
    最后一次更改: 金铲铲大作战

    功能说明:
    - 使用 `g++` 编译临时源码并执行生成程序。
    - 因为该链路会间接包含 `Dma.h`，统一复用较保守的 GCC 优化开关，避免模板 ICE 干扰接口验证。

    使用示例:
    - `_compile_and_run("int main() { return 0; }")`

    关联文件:
    - spec: [`spec/include/api/cost/Core.md`](spec/include/api/cost/Core.md)
    - test: [`test/include/api/test_cost.py`](test/include/api/test_cost.py)
    - 功能实现: [`test/include/api/test_cost.py`](test/include/api/test_cost.py)
    """

    with tempfile.TemporaryDirectory() as tmpdir:
        source_path = Path(tmpdir) / "cost_test.cpp"
        binary_path = Path(tmpdir) / "cost_test"
        source_path.write_text(source, encoding="utf-8")

        compile_result = subprocess.run(
            [
                "g++",
                "-std=c++17",
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


# COST-API-001
# 创建者: 金铲铲大作战
# 最后一次更改: 金铲铲大作战
# 测试目的: 验证 `include/api/cost/Core.h` 公开 compute / memory / DMA / MAC 四种 kind，且不再残留 kind2 / kind3。
# 使用示例: `pytest -q test/include/api/test_cost.py -k test_include_api_cost_core_exports_compute_and_memory`
# 对应功能实现文件路径: `include/api/cost/Core.h`
# 对应 spec 文件路径: `spec/include/api/cost/Core.md`
# 对应测试文件路径: `test/include/api/test_cost.py`
def test_include_api_cost_core_exports_compute_and_memory() -> None:
    public_header = (REPO_ROOT / "include" / "api" / "cost" / "Core.h").read_text(encoding="utf-8")

    assert "enum class CostKind" in public_header
    assert "Compute" in public_header
    assert "Memory" in public_header
    assert "DMA" in public_header
    assert "MAC" in public_header
    assert "inline constexpr cost::CostKind compute" in public_header
    assert "inline constexpr cost::CostKind memory" in public_header
    assert "inline constexpr cost::CostKind DMA" in public_header
    assert "inline constexpr cost::CostKind MAC" in public_header
    assert "Kind2" not in public_header
    assert "Kind3" not in public_header

    source = r"""
#include "include/api/cost/Core.h"
#include "include/npu_demo/cost/Core.h"

int main() {
    npu_demo::cost::CostKind compute_kind = npu_demo::compute;
    npu_demo::cost::CostKind memory_kind = npu_demo::memory;
    npu_demo::cost::CostKind dma_kind = npu_demo::DMA;
    npu_demo::cost::CostKind mac_kind = npu_demo::MAC;
    S_INT cost = compute_kind == npu_demo::compute ? 0 : 1;
    if (memory_kind != npu_demo::memory) {
        return 1;
    }
    if (dma_kind != npu_demo::DMA || mac_kind != npu_demo::MAC) {
        return 2;
    }
    return static_cast<int>(cost);
}
"""
    _compile_and_run(source)


# COST-API-002
# 创建者: 金铲铲大作战
# 最后一次更改: 守护最好的爱莉希雅
# 测试目的: 验证 `include/api/cost/Kernel.h` 的 add / reduce_max / matmul 成本接口可独立实例化并返回 `S_INT`。
# 使用示例: `pytest -q test/include/api/test_cost.py -k test_include_api_cost_kernel_signatures_compile`
# 对应功能实现文件路径: `include/api/cost/Kernel.h`
# 对应 spec 文件路径: `spec/include/api/cost/Kernel.md`
# 对应测试文件路径: `test/include/api/test_cost.py`
def test_include_api_cost_kernel_signatures_compile() -> None:
    source = r"""
#include "include/api/cost/Kernel.h"
#include "include/npu_demo/cost/Kernel.h"

static int fail(int code) { return code; }

int main() {
    float lhs_data[4] = {1.0f, 2.0f, 3.0f, 4.0f};
    float rhs_data[4] = {5.0f, 6.0f, 7.0f, 8.0f};
    float out_data[4] = {0.0f, 0.0f, 0.0f, 0.0f};
    long long vec_shape[1] = {4};
    long long vec_stride[1] = {1};
    long long mat_shape[2] = {2, 2};
    long long mat_stride[2] = {2, 1};

    Memory<GM, float> lhs(lhs_data, vec_shape, vec_stride, 1, MemoryFormat::Norm);
    Memory<GM, float> rhs(rhs_data, vec_shape, vec_stride, 1, MemoryFormat::Norm);
    Memory<GM, float> out(out_data, vec_shape, vec_stride, 1, MemoryFormat::Norm);
    Memory<TSM, float> lhs_mat(lhs_data, mat_shape, mat_stride, 2, MemoryFormat::Norm);
    Memory<TSM, float> rhs_mat(rhs_data, mat_shape, mat_stride, 2, MemoryFormat::Norm);
    Memory<TLM1, float> out_mat(out_data, mat_shape, mat_stride, 2, MemoryFormat::Norm);

    S_INT add_cost =
        npu_demo::cost::add<GM, float, float, npu_demo::MAC>(out, lhs, rhs);
    S_INT reduce_max_cost =
        npu_demo::cost::reduce_max<TSM, float, float, npu_demo::compute>(lhs_mat, rhs_mat, 1);
    S_INT matmul_cost = npu_demo::cost::matmul<
        TSM,
        TSM,
        TLM1,
        float,
        float,
        float,
        npu_demo::MAC>(out_mat, lhs_mat, rhs_mat);
    if (add_cost != 0 || reduce_max_cost != 0 || matmul_cost != 0) {
        return fail(1);
    }
    return 0;
}
"""
    _compile_and_run(source)


# COST-API-003
# 创建者: 金铲铲大作战
# 最后一次更改: 金铲铲大作战
# 测试目的: 验证 `include/api/cost/Dma.h` 的 copy / slice / deslice 成本接口可独立实例化并返回 `S_INT`。
# 使用示例: `pytest -q test/include/api/test_cost.py -k test_include_api_cost_dma_signatures_compile`
# 对应功能实现文件路径: `include/api/cost/Dma.h`
# 对应 spec 文件路径: `spec/include/api/cost/Dma.md`
# 对应测试文件路径: `test/include/api/test_cost.py`
def test_include_api_cost_dma_signatures_compile() -> None:
    source = r"""
#include "include/api/cost/Dma.h"
#include "include/npu_demo/cost/Dma.h"

static int fail(int code) { return code; }

int main() {
    float source_data[4] = {1.0f, 2.0f, 3.0f, 4.0f};
    float target_data[4] = {0.0f, 0.0f, 0.0f, 0.0f};
    long long shape[1] = {4};
    long long stride[1] = {1};
    long long offset_buf[1] = {0};
    long long size_buf[1] = {4};
    long long step_buf[1] = {1};
    Vector offset(offset_buf, 1);
    Vector size(size_buf, 1);
    Vector step(step_buf, 1);

    Memory<GM, float> source(source_data, shape, stride, 1, MemoryFormat::Norm);
    Memory<TSM, float> target(target_data, shape, stride, 1, MemoryFormat::Norm);

    S_INT copy_cost =
        npu_demo::cost::copy<TSM, GM, float, npu_demo::DMA>(target, source);
    S_INT slice_cost =
        npu_demo::cost::slice<TSM, GM, float, npu_demo::memory>(target, source, offset, size, step);
    S_INT deslice_cost =
        npu_demo::cost::deslice<TSM, GM, float, npu_demo::compute>(target, source, offset, size, step);
    if (copy_cost != 0 || slice_cost != 0 || deslice_cost != 0) {
        return fail(1);
    }
    return 0;
}
"""
    _compile_and_run(source)
