"""npu_demo cost public namespace compile tests.

创建者: 金铲铲大作战
最后一次更改: 金铲铲大作战

功能说明:
- 通过编译并运行 C++ 片段验证 `include/npu_demo/npu_demo.h` 对 cost family 的聚合入口。
- 锁定 `npu_demo::cost::{CostKind, add, copy}` 等公共消费方向，确保调用方无需额外 include 私有 cost 头文件。

覆盖率信息:
- 当前覆盖率: `N/A`。该链路为 C++ 头文件，按规则豁免 `pytest-cov` 覆盖率统计。
- 达标判定: C++ 头文件实现按规则豁免 `95%` 覆盖率达标线。

使用示例:
- `pytest -q test/include/npu_demo/test_cost.py`

关联文件:
- 功能实现: [`include/npu_demo/npu_demo.h`](include/npu_demo/npu_demo.h)
- 功能实现: [`include/npu_demo/cost/Core.h`](include/npu_demo/cost/Core.h)
- 功能实现: [`include/npu_demo/cost/Dma.h`](include/npu_demo/cost/Dma.h)
- 功能实现: [`include/npu_demo/cost/Kernel.h`](include/npu_demo/cost/Kernel.h)
- Spec 文档: [`spec/include/npu_demo/npu_demo.md`](spec/include/npu_demo/npu_demo.md)
- 测试文件: [`test/include/npu_demo/test_cost.py`](test/include/npu_demo/test_cost.py)
"""

from __future__ import annotations

import subprocess
import tempfile
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]


def _compile_and_run(source: str) -> None:
    """编译并运行 npu_demo cost 测试片段。

    创建者: 金铲铲大作战
    最后一次更改: 金铲铲大作战

    功能说明:
    - 使用 `g++ -std=c++17 -pthread` 编译临时源码并执行生成程序。
    - 统一复用 `Dma` 相关的保守 GCC 优化开关，避免模板 ICE 干扰聚合入口验证。

    使用示例:
    - `_compile_and_run("int main() { return 0; }")`

    关联文件:
    - spec: [`spec/include/npu_demo/npu_demo.md`](spec/include/npu_demo/npu_demo.md)
    - test: [`test/include/npu_demo/test_cost.py`](test/include/npu_demo/test_cost.py)
    - 功能实现: [`test/include/npu_demo/test_cost.py`](test/include/npu_demo/test_cost.py)
    """

    with tempfile.TemporaryDirectory() as tmpdir:
        source_path = Path(tmpdir) / "npu_demo_cost_test.cpp"
        binary_path = Path(tmpdir) / "npu_demo_cost_test"
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


# NPU-DEMO-COST-001
# 创建者: 金铲铲大作战
# 最后一次更改: 金铲铲大作战
# 测试目的: 验证 `include/npu_demo/npu_demo.h` 可直接消费 `npu_demo::cost::{CostKind, add, copy}` 公共入口。
# 使用示例: `pytest -q test/include/npu_demo/test_cost.py -k test_npu_demo_cost_public_namespace_compiles`
# 对应功能实现文件路径: `include/npu_demo/npu_demo.h`
# 对应 spec 文件路径: `spec/include/npu_demo/npu_demo.md`
# 对应测试文件路径: `test/include/npu_demo/test_cost.py`
def test_npu_demo_cost_public_namespace_compiles() -> None:
    source = r"""
#include "include/npu_demo/npu_demo.h"

static int fail(int code) { return code; }

int main() {
    float source_data[4] = {1.0f, 2.0f, 3.0f, 4.0f};
    float out_data[4] = {0.0f, 0.0f, 0.0f, 0.0f};
    long long shape[1] = {4};
    long long stride[1] = {1};

    Memory<GM, float> source(source_data, shape, stride, 1, MemoryFormat::Norm);
    Memory<GM, float> out(out_data, shape, stride, 1, MemoryFormat::Norm);
    Memory<TSM, float> tile(out_data, shape, stride, 1, MemoryFormat::Norm);

    S_INT add_cost =
        npu_demo::cost::add<GM, float, float, npu_demo::MAC>(out, source, source);
    S_INT copy_cost =
        npu_demo::cost::copy<TSM, GM, float, npu_demo::DMA>(tile, source);
    if (add_cost != 0 || copy_cost != 0) {
        return fail(1);
    }
    if (npu_demo::compute == npu_demo::memory) {
        return fail(2);
    }
    if (npu_demo::DMA == npu_demo::MAC) {
        return fail(3);
    }
    return 0;
}
"""
    _compile_and_run(source)


# NPU-DEMO-COST-002
# 创建者: 金铲铲大作战
# 最后一次更改: 金铲铲大作战
# 测试目的: 验证 `include/npu_demo/npu_demo.h` 已聚合 cost family，且不再残留 kind2 / kind3 文本。
# 使用示例: `pytest -q test/include/npu_demo/test_cost.py -k test_npu_demo_public_header_aggregates_cost_family`
# 对应功能实现文件路径: `include/npu_demo/npu_demo.h`
# 对应 spec 文件路径: `spec/include/npu_demo/npu_demo.md`
# 对应测试文件路径: `test/include/npu_demo/test_cost.py`
def test_npu_demo_public_header_aggregates_cost_family() -> None:
    header = (REPO_ROOT / "include" / "npu_demo" / "npu_demo.h").read_text(encoding="utf-8")

    assert '#include "include/api/cost/Core.h"' in header
    assert '#include "include/api/cost/Dma.h"' in header
    assert '#include "include/api/cost/Kernel.h"' in header
    assert '#include "include/npu_demo/cost/Core.h"' in header
    assert '#include "include/npu_demo/cost/Dma.h"' in header
    assert '#include "include/npu_demo/cost/Kernel.h"' in header
    assert "kind2" not in header
    assert "kind3" not in header
