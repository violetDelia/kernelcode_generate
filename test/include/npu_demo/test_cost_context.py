"""npu_demo CostContext compile tests.


功能说明:
- 通过编译并运行 C++ 片段验证 `npu_demo::CostContext`、`CostSummary` 与 `format_cost_summary(...)`。
- 覆盖 DMA raw bytes finalize、MAC/VECTOR 累加、非法 kind、负值和 helper cost mode 不写业务输出。

使用示例:
- pytest -q test/include/npu_demo/test_cost_context.py

关联文件:
- 功能实现: include/npu_demo/Core.h
- 功能实现: include/npu_demo/Dma.h
- 功能实现: include/npu_demo/Kernel.h
- Spec 文档: spec/include/npu_demo/npu_demo.md
- 测试文件: test/include/npu_demo/test_cost_context.py
"""

from __future__ import annotations

import subprocess
import tempfile
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]


def _compile_and_run(source: str) -> None:
    """编译并运行 npu_demo CostContext 测试片段。


    功能说明:
    - 使用 `g++ -std=c++17 -pthread` 编译临时源码并执行生成程序。

    使用示例:
    - _compile_and_run("int main() { return 0; }")
    """

    with tempfile.TemporaryDirectory() as tmpdir:
        source_path = Path(tmpdir) / "npu_demo_cost_context_test.cpp"
        binary_path = Path(tmpdir) / "npu_demo_cost_context_test"
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
        run_result = subprocess.run([str(binary_path)], check=False, capture_output=True, text=True)
        if run_result.returncode != 0:
            raise AssertionError(
                "compiled program failed:\n"
                f"stdout:\n{run_result.stdout}\n"
                f"stderr:\n{run_result.stderr}"
            )


def test_npu_demo_cost_context_summary_and_format() -> None:
    """验证 CostContext 累计、finalize 和固定 JSON 输出。"""

    source = r"""
#include "include/npu_demo/npu_demo.h"

static int fail(int code) { return code; }

int main() {
    npu_demo::CostContext ctx;
    ctx.add_cost(npu_demo::DMA1, 65);
    ctx.add_cost(npu_demo::DMA2, 64);
    ctx.add_cost(npu_demo::MAC, 7);
    ctx.add_cost(npu_demo::VECTOR1, 128);
    ctx.add_cost(npu_demo::VECTOR2, 3);

    const npu_demo::CostSummary& summary = ctx.summary();
    if (summary.value(npu_demo::DMA) != 2 || summary.value(npu_demo::DMA1) != 2) {
        return fail(1);
    }
    if (summary.value(npu_demo::DMA2) != 1 || summary.value(npu_demo::DMA3) != 0 || summary.value(npu_demo::DMA4) != 0) {
        return fail(2);
    }
    if (summary.value(npu_demo::MAC) != 7 || summary.value(npu_demo::VECTOR1) != 128 || summary.value(npu_demo::VECTOR2) != 3) {
        return fail(3);
    }
    const std::string formatted = npu_demo::format_cost_summary(summary);
    if (formatted != "{\"DMA1\":2,\"DMA2\":1,\"DMA3\":0,\"DMA4\":0,\"MAC\":7,\"VECTOR1\":128,\"VECTOR2\":3}") {
        return fail(4);
    }

    try {
        ctx.add_cost(npu_demo::VECTOR1, -1);
        return fail(5);
    } catch (const std::invalid_argument& exc) {
        if (std::string(exc.what()) != "cost value must be non-negative") {
            return fail(6);
        }
    }
    try {
        ctx.add_cost(static_cast<npu_demo::cost::CostKind>(99), 1);
        return fail(7);
    } catch (const std::invalid_argument& exc) {
        if (std::string(exc.what()) != "unsupported cost kind") {
            return fail(8);
        }
    }
    try {
        (void)summary.value(static_cast<npu_demo::cost::CostKind>(99));
        return fail(9);
    } catch (const std::invalid_argument& exc) {
        if (std::string(exc.what()) != "unsupported cost kind") {
            return fail(10);
        }
    }
    return 0;
}
"""
    _compile_and_run(source)


def test_npu_demo_cost_context_helpers_record_cost_without_writing_output() -> None:
    """验证 DMA / Kernel helper 在 CostContext 下只累计成本，不写业务输出。"""

    source = r"""
#include "include/npu_demo/npu_demo.h"

static int fail(int code) { return code; }

int main() {
    int lhs_data[4] = {1, 2, 3, 4};
    int rhs_data[4] = {5, 6, 7, 8};
    int out_data[4] = {-1, -1, -1, -1};
    int tile_data[4] = {0, 0, 0, 0};

    Memory<GM, int32_t> lhs(lhs_data, {4}, {1}, MemoryFormat::Norm);
    Memory<GM, int32_t> rhs(rhs_data, {4}, {1}, MemoryFormat::Norm);
    Memory<GM, int32_t> out(out_data, {4}, {1}, MemoryFormat::Norm);
    Memory<TSM, int32_t> tile(tile_data, {4}, {1}, MemoryFormat::Norm);

    npu_demo::CostContext ctx;
    if (npu_demo::add<GM, int32_t, int32_t>(ctx, out, lhs, rhs) != StatusCode::kOk) {
        return fail(1);
    }
    if (npu_demo::slice<TSM, GM, int32_t>(ctx, tile, lhs, {0}, {4}, {1}) != StatusCode::kOk) {
        return fail(2);
    }
    if (npu_demo::deslice<GM, TSM, int32_t>(ctx, out, tile, {0}, {4}, {1}) != StatusCode::kOk) {
        return fail(3);
    }
    for (int value : out_data) {
        if (value != -1) {
            return fail(4);
        }
    }
    for (int value : tile_data) {
        if (value != 0) {
            return fail(5);
        }
    }

    float lhs_mat_data[6] = {0};
    float rhs_mat_data[12] = {0};
    float out_mat_data[8] = {-1, -1, -1, -1, -1, -1, -1, -1};
    Memory<TSM, float> lhs_mat(lhs_mat_data, {2, 3}, {3, 1}, MemoryFormat::Norm);
    Memory<TSM, float> rhs_mat(rhs_mat_data, {3, 4}, {4, 1}, MemoryFormat::Norm);
    Memory<TLM1, float> out_mat(out_mat_data, {2, 4}, {4, 1}, MemoryFormat::Norm);
    if (npu_demo::matmul<TSM, TSM, TLM1, float, float, float>(ctx, out_mat, lhs_mat, rhs_mat) != StatusCode::kOk) {
        return fail(6);
    }
    for (float value : out_mat_data) {
        if (value != -1.0f) {
            return fail(7);
        }
    }

    float img_data[4] = {0};
    float col_data[6] = {-1, -1, -1, -1, -1, -1};
    Memory<TSM, float> img(img_data, {1, 1, 4}, {4, 4, 1}, MemoryFormat::Norm);
    Memory<TLM1, float> col(col_data, {1, 1, 2, 3}, {6, 6, 3, 1}, MemoryFormat::Norm);
    if (npu_demo::img2col1d<TSM, TLM1, float, float>(ctx, col, img, 2, 1, 1, 0, 0) != StatusCode::kOk) {
        return fail(8);
    }
    for (float value : col_data) {
        if (value != -1.0f) {
            return fail(9);
        }
    }

    const npu_demo::CostSummary& summary = ctx.summary();
    if (summary.value(npu_demo::VECTOR1) != 4) {
        return fail(10);
    }
    if (summary.value(npu_demo::DMA1) != 1 || summary.value(npu_demo::DMA2) != 1 || summary.value(npu_demo::DMA3) != 1) {
        return fail(11);
    }
    if (summary.value(npu_demo::MAC) != 24) {
        return fail(12);
    }
    return 0;
}
"""
    _compile_and_run(source)


def test_npu_demo_cost_context_kernel_helpers_validate_layout_before_cost() -> None:
    """验证 Kernel helper 在 CostContext 下先校验布局再累计成本。

    功能说明:
    - 覆盖 elementwise / unary / compare helper 的非法 shape / data 负向，防止静默记录 `VECTOR1` summary。

    使用示例:
    - pytest -q test/include/npu_demo/test_cost_context.py -k validate_layout_before_cost
    """

    source = r"""
#include "include/npu_demo/npu_demo.h"

static int fail(int code) { return code; }

int main() {
    int out_data[4] = {-1, -1, -1, -1};
    int lhs_short_data[2] = {1, 2};
    int lhs_data[4] = {1, 2, 3, 4};
    int rhs_data[4] = {5, 6, 7, 8};
    bool cmp_data[4] = {false, false, false, false};

    Memory<GM, int32_t> out(out_data, {4}, {1}, MemoryFormat::Norm);
    Memory<GM, int32_t> lhs_short(lhs_short_data, {2}, {1}, MemoryFormat::Norm);
    Memory<GM, int32_t> lhs(lhs_data, {4}, {1}, MemoryFormat::Norm);
    Memory<GM, int32_t> rhs(rhs_data, {4}, {1}, MemoryFormat::Norm);
    Memory<GM, bool> cmp(cmp_data, {4}, {1}, MemoryFormat::Norm);
    Memory<GM, int32_t> null_input(nullptr, {4}, {1}, MemoryFormat::Norm);

    npu_demo::CostContext ctx;
    if (npu_demo::add<GM, int32_t, int32_t>(ctx, out, lhs_short, rhs) != StatusCode::kError) {
        return fail(1);
    }
    if (ctx.summary().value(npu_demo::VECTOR1) != 0) {
        return fail(2);
    }
    if (npu_demo::exp<GM, int32_t, int32_t>(ctx, out, null_input) != StatusCode::kError) {
        return fail(3);
    }
    if (ctx.summary().value(npu_demo::VECTOR1) != 0) {
        return fail(4);
    }
    if (npu_demo::eq<GM, int32_t, bool>(ctx, cmp, lhs_short, rhs) != StatusCode::kError) {
        return fail(5);
    }
    if (ctx.summary().value(npu_demo::VECTOR1) != 0) {
        return fail(6);
    }
    if (npu_demo::add<GM, int32_t, int32_t>(ctx, out, lhs, rhs) != StatusCode::kOk) {
        return fail(7);
    }
    if (ctx.summary().value(npu_demo::VECTOR1) != 4) {
        return fail(8);
    }
    for (int value : out_data) {
        if (value != -1) {
            return fail(9);
        }
    }
    return 0;
}
"""
    _compile_and_run(source)
