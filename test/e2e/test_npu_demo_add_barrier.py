"""npu_demo add+barrier end-to-end runtime tests.

创建者: 小李飞刀
最后一次更改: 朽木露琪亚

功能说明:
- 端到端验证 `gen_kernel(target="npu_demo")` 生成的 `add_barrier` 双函数源码可编译为真实可执行程序。
- 追加“线程 0 故意慢一步”的 barrier 探针，证明其他线程不会越过同一次 launch 的共享 barrier。

使用示例:
- pytest -q test/e2e/test_npu_demo_add_barrier.py

关联文件:
- 功能实现: kernel_gen/dsl/gen_kernel/gen_kernel.py
- Spec 文档: spec/dsl/gen_kernel/gen_kernel.md
- 测试文件: test/e2e/test_npu_demo_add_barrier.py
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
GEN_KERNEL_TEST_PATH = REPO_ROOT / "test/dsl/gen_kernel/test_gen_kernel.py"


def _load_gen_kernel_test_module():
    """加载 `test/dsl/gen_kernel/test_gen_kernel.py` 中的 `npu_demo add+barrier` 测试辅助函数。

    创建者: 小李飞刀
    最后一次更改: 小李飞刀

    功能说明:
    - 复用 DSL 测试文件里已冻结的 `npu_demo add+barrier` module builder 与运行时编译辅助逻辑。
    - 避免 e2e 用例复制另一份 IR 构造骨架，确保 DSL smoke 与 e2e 使用同一受控 module 形态。

    使用示例:
    - helpers = _load_gen_kernel_test_module()

    关联文件:
    - spec: spec/dsl/gen_kernel/gen_kernel.md
    - test: test/e2e/test_npu_demo_add_barrier.py
    - 功能实现: test/e2e/test_npu_demo_add_barrier.py
    """

    module_name = "test_dsl_test_gen_kernel_runtime_helpers"
    if module_name in sys.modules:
        return sys.modules[module_name]

    spec = importlib.util.spec_from_file_location(module_name, GEN_KERNEL_TEST_PATH)
    if spec is None or spec.loader is None:
        raise AssertionError(f"failed to load helper module: {GEN_KERNEL_TEST_PATH}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


# NPU-DEMO-E2E-001
# 创建者: 小李飞刀
# 最后一次更改: 小李飞刀
# 最近一次运行测试时间: 2026-04-06 13:20:00 +0800
# 最近一次运行成功时间: 2026-04-06 13:20:00 +0800
# 功能说明: 验证 `npu_demo add+barrier` 双函数可从 DSL module 生成源码、编译为可执行程序，并在运行时证明共享 barrier 生效。
# 测试目的: 锁定端到端链路不是“只生成源码”，且至少一个 case 构造“有人慢一步”时其他线程不会越过 barrier。
# 使用示例: pytest -q test/e2e/test_npu_demo_add_barrier.py -k test_npu_demo_add_barrier_runs_end_to_end_with_real_barrier
# 对应功能实现文件路径: kernel_gen/dsl/gen_kernel/gen_kernel.py
# 对应 spec 文件路径: spec/dsl/gen_kernel/gen_kernel.md
# 对应测试文件路径: test/e2e/test_npu_demo_add_barrier.py
def test_npu_demo_add_barrier_runs_end_to_end_with_real_barrier() -> None:
    helpers = _load_gen_kernel_test_module()

    module = helpers._make_npu_demo_add_barrier_module()
    source = helpers.gen_kernel(module, helpers._npu_ctx())

    assert "void add_barrier(" in source
    assert "npu_demo::barrier({BarrierVisibility::TSM, BarrierVisibility::TLM}, BarrierScope::BLOCK);" in source
    helpers._compile_and_run_npu_demo_add_barrier_source(source, prove_barrier_runtime=True)
