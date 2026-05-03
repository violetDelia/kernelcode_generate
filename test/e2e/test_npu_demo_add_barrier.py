"""npu_demo add+barrier end-to-end runtime tests.


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

from kernel_gen.dsl.gen_kernel import gen_kernel
from test.e2e.test_npu_demo_add_barrier_asset import (
    build_npu_demo_add_barrier_module,
    compile_and_run_npu_demo_add_barrier_source,
    make_npu_demo_context,
)


# NPU-DEMO-E2E-001
# 功能说明: 验证 `npu_demo add+barrier` 双函数可从 DSL module 生成源码、编译为可执行程序，并在运行时证明共享 barrier 生效。
# 测试目的: 锁定端到端链路不是“只生成源码”，且至少一个 case 构造“有人慢一步”时其他线程不会越过 barrier。
# 使用示例: pytest -q test/e2e/test_npu_demo_add_barrier.py -k test_npu_demo_add_barrier_runs_end_to_end_with_real_barrier
# 对应功能实现文件路径: kernel_gen/dsl/gen_kernel/gen_kernel.py
# 对应 spec 文件路径: spec/dsl/gen_kernel/gen_kernel.md
# 对应测试文件路径: test/e2e/test_npu_demo_add_barrier.py
def test_npu_demo_add_barrier_runs_end_to_end_with_real_barrier() -> None:
    module = build_npu_demo_add_barrier_module()
    source = gen_kernel(module, make_npu_demo_context())

    assert "void add_barrier(" in source
    assert "npu_demo::barrier({BarrierVisibility::TSM, BarrierVisibility::TLM}, BarrierScope::BLOCK);" in source
    compile_and_run_npu_demo_add_barrier_source(source, prove_barrier_runtime=True)
