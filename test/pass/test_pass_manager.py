"""pass_manager tests.

创建者: 李白
最后一次更改: jcc你莫辜负

功能说明:
- 覆盖 kernel_gen/passes/pass_manager.py 的 Pass 管理行为。

当前覆盖率信息:
- 当前覆盖率: `100%`（语句覆盖 `100%`，分支覆盖 `100%`）。
- 达标判定: 已达到 `95%` 覆盖率达标线。
- 本文件覆盖 `TC-PASS-001..013`，并补充 `Pass` 缺少 `name` 属性的非法输入分支。

覆盖率命令:
- `pytest -q --cov=kernel_gen.passes.pass_manager --cov-branch --cov-report=term-missing test/pass/test_pass_manager.py`

使用示例:
- pytest -q test/pass/test_pass_manager.py

关联文件:
- 功能实现: kernel_gen/passes/pass_manager.py
- Spec 文档: spec/pass/pass_manager.md
- 测试文件: test/pass/test_pass_manager.py
"""

from __future__ import annotations

import sys
from pathlib import Path

import importlib
import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

pass_module = importlib.import_module("kernel_gen.passes.pass_manager")
Pass = pass_module.Pass
PassManager = pass_module.PassManager
build_default_lowering_pass_manager = pass_module.build_default_lowering_pass_manager


# TC-PASS-001
# 创建者: 李白
# 最后一次更改: 我不是牛马
# 最近一次运行测试时间: 2026-03-22 13:24:21 +0800
# 最近一次运行成功时间: 2026-03-22 13:24:21 +0800
# 功能说明: 验证单 Pass 正常执行。
# 使用示例: pytest -q test/pass/test_pass_manager.py -k test_pass_manager_single_pass
# 对应功能实现文件路径: kernel_gen/passes/pass_manager.py
# 对应 spec 文件路径: spec/pass/pass_manager.md
# 对应测试文件路径: test/pass/test_pass_manager.py
def test_pass_manager_single_pass() -> None:
    class AddOnePass(Pass):
        name = "add-one"

        def run(self: "AddOnePass", target: int) -> int:
            return target + 1

    pm = PassManager(name="opt")
    pm.add_pass(AddOnePass())
    assert pm.run(1) == 2


# TC-PASS-002
# 创建者: 李白
# 最后一次更改: 我不是牛马
# 最近一次运行测试时间: 2026-03-22 13:24:21 +0800
# 最近一次运行成功时间: 2026-03-22 13:24:21 +0800
# 功能说明: 验证多 Pass 顺序执行。
# 使用示例: pytest -q test/pass/test_pass_manager.py -k test_pass_manager_multiple_passes_order
# 对应功能实现文件路径: kernel_gen/passes/pass_manager.py
# 对应 spec 文件路径: spec/pass/pass_manager.md
# 对应测试文件路径: test/pass/test_pass_manager.py
def test_pass_manager_multiple_passes_order() -> None:
    class AddOnePass(Pass):
        name = "add-one"

        def run(self: "AddOnePass", target: int) -> int:
            return target + 1

    class TimesTwoPass(Pass):
        name = "times-two"

        def run(self: "TimesTwoPass", target: int) -> int:
            return target * 2

    pm = PassManager()
    pm.extend([AddOnePass(), TimesTwoPass()])
    assert pm.run(2) == 6


# TC-PASS-003
# 创建者: 李白
# 最后一次更改: 我不是牛马
# 最近一次运行测试时间: 2026-03-22 13:24:21 +0800
# 最近一次运行成功时间: 2026-03-22 13:24:21 +0800
# 功能说明: 验证空管理器返回原输入。
# 使用示例: pytest -q test/pass/test_pass_manager.py -k test_pass_manager_empty_returns_input
# 对应功能实现文件路径: kernel_gen/passes/pass_manager.py
# 对应 spec 文件路径: spec/pass/pass_manager.md
# 对应测试文件路径: test/pass/test_pass_manager.py
def test_pass_manager_empty_returns_input() -> None:
    pm = PassManager()
    data = {"key": "value"}
    assert pm.run(data) is data


# TC-PASS-004
# 创建者: 李白
# 最后一次更改: 我不是牛马
# 最近一次运行测试时间: 2026-03-22 13:24:21 +0800
# 最近一次运行成功时间: 2026-03-22 13:24:21 +0800
# 功能说明: 验证非法 Pass 类型报错。
# 使用示例: pytest -q test/pass/test_pass_manager.py -k test_pass_manager_invalid_pass_type
# 对应功能实现文件路径: kernel_gen/passes/pass_manager.py
# 对应 spec 文件路径: spec/pass/pass_manager.md
# 对应测试文件路径: test/pass/test_pass_manager.py
def test_pass_manager_invalid_pass_type() -> None:
    pm = PassManager()
    with pytest.raises(TypeError):
        pm.add_pass("not-a-pass")  # type: ignore[arg-type]

    with pytest.raises(TypeError):
        pm.extend([object()])  # type: ignore[arg-type]

    class MissingNamePass:
        def run(self: "MissingNamePass", target: object) -> object:
            return target

    with pytest.raises(TypeError):
        pm.add_pass(MissingNamePass())  # type: ignore[arg-type]

    class BadNamePass(Pass):
        name = 123

        def run(self: "BadNamePass", target: object) -> object:
            return target

    with pytest.raises(TypeError):
        pm.add_pass(BadNamePass())


# TC-PASS-005
# 创建者: 李白
# 最后一次更改: 我不是牛马
# 最近一次运行测试时间: 2026-03-22 13:24:21 +0800
# 最近一次运行成功时间: 2026-03-22 13:24:21 +0800
# 功能说明: 验证 Pass 异常向上抛出。
# 使用示例: pytest -q test/pass/test_pass_manager.py -k test_pass_manager_exception_propagation
# 对应功能实现文件路径: kernel_gen/passes/pass_manager.py
# 对应 spec 文件路径: spec/pass/pass_manager.md
# 对应测试文件路径: test/pass/test_pass_manager.py
def test_pass_manager_exception_propagation() -> None:
    class FailPass(Pass):
        name = "fail-pass"

        def run(self: "FailPass", target: object) -> object:
            raise ValueError("boom")

    pm = PassManager()
    pm.add_pass(FailPass())
    with pytest.raises(ValueError):
        _ = pm.run(1)


# TC-PASS-006
# 创建者: 金铲铲大作战
# 最后一次更改: jcc你莫辜负
# 最近一次运行测试时间: 2026-04-06 09:53:59 +0800
# 最近一次运行成功时间: 2026-04-06 09:53:59 +0800
# 功能说明: 验证默认 lowering pipeline 会固定注册 `LowerNnToKernelPass -> BufferResultsToOutParamsPass -> LowerDmaMemoryHierarchyPass`。
# 使用示例: pytest -q test/pass/test_pass_manager.py -k test_pass_manager_builds_default_lowering_pipeline_for_buffer_results_to_out_params
# 对应功能实现文件路径: kernel_gen/passes/pass_manager.py
# 对应 spec 文件路径: spec/pass/pass_manager.md
# 对应测试文件路径: test/pass/test_pass_manager.py
def test_pass_manager_builds_default_lowering_pipeline_for_buffer_results_to_out_params(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    lowering_module = importlib.import_module("kernel_gen.passes.lowering")
    LowerNnToKernelPass = lowering_module.LowerNnToKernelPass
    BufferResultsToOutParamsPass = lowering_module.BufferResultsToOutParamsPass
    LowerDmaMemoryHierarchyPass = lowering_module.LowerDmaMemoryHierarchyPass
    order: list[str] = []

    def _record_lower(self: object, target: object) -> object:
        order.append("lower-nn-to-kernel")
        return target

    def _record_buffer(self: object, target: object) -> object:
        order.append("buffer-results-to-out-params")
        return target

    def _record_dma(self: object, target: object) -> object:
        order.append("lower-dma-memory-hierarchy")
        return target

    monkeypatch.setattr(LowerNnToKernelPass, "run", _record_lower)
    monkeypatch.setattr(BufferResultsToOutParamsPass, "run", _record_buffer)
    monkeypatch.setattr(LowerDmaMemoryHierarchyPass, "run", _record_dma)

    pm = build_default_lowering_pass_manager()
    sentinel = object()
    assert pm.run(sentinel) is sentinel
    assert order == [
        "lower-nn-to-kernel",
        "buffer-results-to-out-params",
        "lower-dma-memory-hierarchy",
    ]


# TC-PASS-007
# 创建者: 金铲铲大作战
# 最后一次更改: 金铲铲大作战
# 最近一次运行测试时间: 2026-04-04 00:00:00 +0800
# 最近一次运行成功时间: 2026-04-04 00:00:00 +0800
# 功能说明: 验证 `buffer-results-to-out-params` 放在 `lower-nn-to-kernel` 之前会被显式拒绝。
# 使用示例: pytest -q test/pass/test_pass_manager.py -k test_pass_manager_rejects_buffer_results_to_out_params_before_lowering
# 对应功能实现文件路径: kernel_gen/passes/pass_manager.py
# 对应 spec 文件路径: spec/pass/pass_manager.md
# 对应测试文件路径: test/pass/test_pass_manager.py
def test_pass_manager_rejects_buffer_results_to_out_params_before_lowering() -> None:
    lowering_module = importlib.import_module("kernel_gen.passes.lowering")
    BufferResultsToOutParamsPass = lowering_module.BufferResultsToOutParamsPass
    LowerNnToKernelPass = lowering_module.LowerNnToKernelPass

    pm = PassManager(name="lowering")
    pm.add_pass(BufferResultsToOutParamsPass())
    pm.add_pass(LowerNnToKernelPass())

    with pytest.raises(ValueError, match="lowered IR"):
        pm.run(object())


# TC-PASS-008
# 创建者: 小李飞刀
# 最后一次更改: 小李飞刀
# 最近一次运行测试时间: 2026-04-05 00:00:00 +0800
# 最近一次运行成功时间: 2026-04-05 00:00:00 +0800
# 功能说明: 验证 buffer-results-to-out-params 可在 lowering 之后、其他 pass 之前/之后运行。
# 测试目的: 锁定顺序约束仅要求 `lower-nn-to-kernel` 先于 `buffer-results-to-out-params`，允许中间插入其他 pass。
# 使用示例: pytest -q test/pass/test_pass_manager.py -k test_pass_manager_allows_buffer_results_to_out_params_after_lowering_with_intermediate_pass
# 对应功能实现文件路径: kernel_gen/passes/pass_manager.py
# 对应 spec 文件路径: spec/pass/pass_manager.md
# 对应测试文件路径: test/pass/test_pass_manager.py
def test_pass_manager_allows_buffer_results_to_out_params_after_lowering_with_intermediate_pass(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    lowering_module = importlib.import_module("kernel_gen.passes.lowering")
    LowerNnToKernelPass = lowering_module.LowerNnToKernelPass
    BufferResultsToOutParamsPass = lowering_module.BufferResultsToOutParamsPass
    order: list[str] = []

    class NoopPass(Pass):
        name = "noop"

        def run(self: "NoopPass", target: object) -> object:
            order.append("noop")
            return target

    def _record_lower(self: object, target: object) -> object:
        order.append("lower-nn-to-kernel")
        return target

    def _record_buffer(self: object, target: object) -> object:
        order.append("buffer-results-to-out-params")
        return target

    monkeypatch.setattr(LowerNnToKernelPass, "run", _record_lower)
    monkeypatch.setattr(BufferResultsToOutParamsPass, "run", _record_buffer)

    pm = PassManager(name="lowering")
    pm.add_pass(LowerNnToKernelPass())
    pm.add_pass(NoopPass())
    pm.add_pass(BufferResultsToOutParamsPass())

    sentinel = object()
    assert pm.run(sentinel) is sentinel
    assert order == ["lower-nn-to-kernel", "noop", "buffer-results-to-out-params"]


# TC-PASS-009
# 创建者: 金铲铲大作战
# 最后一次更改: jcc你莫辜负
# 最近一次运行测试时间: 2026-04-06 09:53:59 +0800
# 最近一次运行成功时间: 2026-04-06 09:53:59 +0800
# 功能说明: 验证 `KernelSplitPass` 为显式开启 pass，默认 lowering builder 不会自动插入。
# 测试目的: 锁定默认 `build_default_lowering_pass_manager()` 的 pass 集合只包含 lowering + out-params + dma hierarchy。
# 使用示例: pytest -q test/pass/test_pass_manager.py -k test_kernel_split_pipeline_requires_explicit_enable
# 对应功能实现文件路径: kernel_gen/passes/pass_manager.py
# 对应 spec 文件路径: spec/pass/pass_manager.md
# 对应测试文件路径: test/pass/test_pass_manager.py
def test_kernel_split_pipeline_requires_explicit_enable() -> None:
    pm = build_default_lowering_pass_manager()
    pass_names = [item.name for item in pm._passes]  # noqa: SLF001 - test asserts pipeline boundary
    assert pass_names == [
        "lower-nn-to-kernel",
        "buffer-results-to-out-params",
        "lower-dma-memory-hierarchy",
    ]
    assert "kernel-split" not in pass_names


# TC-PASS-010
# 创建者: 金铲铲大作战
# 最后一次更改: jcc你莫辜负
# 最近一次运行测试时间: 2026-04-06 09:53:59 +0800
# 最近一次运行成功时间: 2026-04-06 09:53:59 +0800
# 功能说明: 验证显式开启 `KernelSplitPass` 时，其顺序必须位于 `LowerDmaMemoryHierarchyPass` 之前。
# 测试目的: 机械锁定推荐 pipeline：`LowerNnToKernelPass -> BufferResultsToOutParamsPass -> KernelSplitPass -> LowerDmaMemoryHierarchyPass`。
# 使用示例: pytest -q test/pass/test_pass_manager.py -k test_default_lowering_pipeline_orders_kernel_split_after_out_params
# 对应功能实现文件路径: kernel_gen/passes/pass_manager.py
# 对应 spec 文件路径: spec/pass/pass_manager.md
# 对应测试文件路径: test/pass/test_pass_manager.py
def test_default_lowering_pipeline_orders_kernel_split_after_out_params(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    lowering_module = importlib.import_module("kernel_gen.passes.lowering")
    LowerNnToKernelPass = lowering_module.LowerNnToKernelPass
    BufferResultsToOutParamsPass = lowering_module.BufferResultsToOutParamsPass
    LowerDmaMemoryHierarchyPass = lowering_module.LowerDmaMemoryHierarchyPass
    kernel_split_module = importlib.import_module("kernel_gen.passes.lowering.kernel_split")
    KernelSplitPass = kernel_split_module.KernelSplitPass
    order: list[str] = []

    def _record_lower(self: object, target: object) -> object:
        order.append("lower-nn-to-kernel")
        return target

    def _record_buffer(self: object, target: object) -> object:
        order.append("buffer-results-to-out-params")
        return target

    def _record_dma(self: object, target: object) -> object:
        order.append("lower-dma-memory-hierarchy")
        return target

    def _record_kernel_split(self: object, target: object) -> object:
        order.append("kernel-split")
        return target

    monkeypatch.setattr(LowerNnToKernelPass, "run", _record_lower)
    monkeypatch.setattr(BufferResultsToOutParamsPass, "run", _record_buffer)
    monkeypatch.setattr(LowerDmaMemoryHierarchyPass, "run", _record_dma)
    monkeypatch.setattr(KernelSplitPass, "run", _record_kernel_split)

    pm = PassManager(name="split-lowering")
    pm.add_pass(LowerNnToKernelPass())
    pm.add_pass(BufferResultsToOutParamsPass())
    pm.add_pass(KernelSplitPass())
    pm.add_pass(LowerDmaMemoryHierarchyPass())

    sentinel = object()
    assert pm.run(sentinel) is sentinel
    assert order == [
        "lower-nn-to-kernel",
        "buffer-results-to-out-params",
        "kernel-split",
        "lower-dma-memory-hierarchy",
    ]


# TC-PASS-011
# 创建者: 金铲铲大作战
# 最后一次更改: jcc你莫辜负
# 最近一次运行测试时间: 2026-04-06 09:53:59 +0800
# 最近一次运行成功时间: 2026-04-06 09:53:59 +0800
# 功能说明: 验证 split pipeline 的 `tuner.param` 来源口径为“由 split pass 在函数体内插入/复用”。
# 测试目的: 锁定 PassManager 端不引入额外前置合同：split 所需的 `tuner.param` 由 `KernelSplitPass.run` 负责物化。
# 使用示例: pytest -q test/pass/test_pass_manager.py -k test_kernel_split_pipeline_materializes_tuner_params_before_codegen
# 对应功能实现文件路径: kernel_gen/passes/pass_manager.py
# 对应 spec 文件路径: spec/pass/pass_manager.md
# 对应测试文件路径: test/pass/test_pass_manager.py
def test_kernel_split_pipeline_materializes_tuner_params_before_codegen(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    lowering_module = importlib.import_module("kernel_gen.passes.lowering")
    LowerNnToKernelPass = lowering_module.LowerNnToKernelPass
    BufferResultsToOutParamsPass = lowering_module.BufferResultsToOutParamsPass
    LowerDmaMemoryHierarchyPass = lowering_module.LowerDmaMemoryHierarchyPass
    kernel_split_module = importlib.import_module("kernel_gen.passes.lowering.kernel_split")
    KernelSplitPass = kernel_split_module.KernelSplitPass

    def _noop(self: object, target: object) -> object:
        return target

    def _materialize_tuner_param(self: object, target: object) -> object:
        assert isinstance(target, dict)
        target["tuner.param"] = True
        return target

    monkeypatch.setattr(LowerNnToKernelPass, "run", _noop)
    monkeypatch.setattr(BufferResultsToOutParamsPass, "run", _noop)
    monkeypatch.setattr(KernelSplitPass, "run", _materialize_tuner_param)
    monkeypatch.setattr(LowerDmaMemoryHierarchyPass, "run", _noop)

    pm = PassManager(name="split-lowering")
    pm.add_pass(LowerNnToKernelPass())
    pm.add_pass(BufferResultsToOutParamsPass())
    pm.add_pass(KernelSplitPass())
    pm.add_pass(LowerDmaMemoryHierarchyPass())

    module = {"tuner.param": False}
    result = pm.run(module)
    assert result is module
    assert module["tuner.param"] is True


# TC-PASS-012
# 创建者: 金铲铲大作战
# 最后一次更改: 朽木露琪亚
# 最近一次运行测试时间: 2026-04-06 03:17:31 +0800
# 最近一次运行成功时间: 2026-04-06 03:17:31 +0800
# 功能说明: 验证错误 split 顺序会被显式拒绝，并包含固定错误关键字 `KernelSplitOrderError`。
# 测试目的: 机械锁定 split 顺序边界，避免错误 pipeline 导致 ABI 双重改写或 DMA hierarchy 口径漂移。
# 使用示例: pytest -q test/pass/test_pass_manager.py -k test_kernel_split_pipeline_rejects_wrong_order
# 对应功能实现文件路径: kernel_gen/passes/pass_manager.py
# 对应 spec 文件路径: spec/pass/pass_manager.md
# 对应测试文件路径: test/pass/test_pass_manager.py
def test_kernel_split_pipeline_rejects_wrong_order() -> None:
    lowering_module = importlib.import_module("kernel_gen.passes.lowering")
    LowerNnToKernelPass = lowering_module.LowerNnToKernelPass
    BufferResultsToOutParamsPass = lowering_module.BufferResultsToOutParamsPass
    kernel_split_module = importlib.import_module("kernel_gen.passes.lowering.kernel_split")
    KernelSplitPass = kernel_split_module.KernelSplitPass
    dma_hierarchy_module = importlib.import_module("kernel_gen.passes.lowering.dma_memory_hierarchy")
    LowerDmaMemoryHierarchyPass = dma_hierarchy_module.LowerDmaMemoryHierarchyPass

    pm = PassManager(name="bad-split-order")
    pm.add_pass(LowerNnToKernelPass())
    pm.add_pass(KernelSplitPass())
    pm.add_pass(BufferResultsToOutParamsPass())
    with pytest.raises(ValueError, match="KernelSplitOrderError"):
        pm.run(object())

    pm = PassManager(name="bad-split-dma-order")
    pm.add_pass(LowerNnToKernelPass())
    pm.add_pass(BufferResultsToOutParamsPass())
    pm.add_pass(LowerDmaMemoryHierarchyPass())
    pm.add_pass(KernelSplitPass())
    with pytest.raises(ValueError, match="KernelSplitOrderError"):
        pm.run(object())


# TC-PASS-013
# 创建者: 金铲铲大作战
# 最后一次更改: jcc你莫辜负
# 最近一次运行测试时间: 2026-04-06 09:53:59 +0800
# 最近一次运行成功时间: 2026-04-06 09:53:59 +0800
# 功能说明: 验证显式 split pipeline 不会隐式引入新的“函数抽取阶段”pass，保持单函数合同的 pipeline 组成可审计。
# 测试目的: 锁定显式 split pipeline 只包含 lowering + out-params + kernel-split + dma hierarchy，不夹带额外 pass。
# 使用示例: pytest -q test/pass/test_pass_manager.py -k test_kernel_split_pipeline_keeps_single_function_contract
# 对应功能实现文件路径: kernel_gen/passes/pass_manager.py
# 对应 spec 文件路径: spec/pass/pass_manager.md
# 对应测试文件路径: test/pass/test_pass_manager.py
def test_kernel_split_pipeline_keeps_single_function_contract() -> None:
    kernel_split_module = importlib.import_module("kernel_gen.passes.lowering.kernel_split")
    KernelSplitPass = kernel_split_module.KernelSplitPass
    lowering_module = importlib.import_module("kernel_gen.passes.lowering")
    LowerNnToKernelPass = lowering_module.LowerNnToKernelPass
    BufferResultsToOutParamsPass = lowering_module.BufferResultsToOutParamsPass
    LowerDmaMemoryHierarchyPass = lowering_module.LowerDmaMemoryHierarchyPass

    pm = PassManager(name="split-lowering")
    pm.add_pass(LowerNnToKernelPass())
    pm.add_pass(BufferResultsToOutParamsPass())
    pm.add_pass(KernelSplitPass())
    pm.add_pass(LowerDmaMemoryHierarchyPass())
    pass_names = [item.name for item in pm._passes]  # noqa: SLF001 - test asserts pipeline boundary
    assert pass_names == [
        "lower-nn-to-kernel",
        "buffer-results-to-out-params",
        "kernel-split",
        "lower-dma-memory-hierarchy",
    ]


# TC-PASS-014
# 创建者: jcc你莫辜负
# 最后一次更改: jcc你莫辜负
# 最近一次运行测试时间: 2026-04-06 09:53:59 +0800
# 最近一次运行成功时间: 2026-04-06 09:53:59 +0800
# 功能说明: 验证 lower-dma-memory-hierarchy 必须位于 buffer-results-to-out-params 之后，否则显式失败。
# 测试目的: 锁定 dma hierarchy 顺序门禁，避免 out-params 合同尚未建立即开始层级搬运。
# 使用示例: pytest -q test/pass/test_pass_manager.py -k test_pass_manager_rejects_dma_memory_hierarchy_before_out_params
# 对应功能实现文件路径: kernel_gen/passes/pass_manager.py
# 对应 spec 文件路径: spec/pass/pass_manager.md
# 对应测试文件路径: test/pass/test_pass_manager.py
def test_pass_manager_rejects_dma_memory_hierarchy_before_out_params() -> None:
    lowering_module = importlib.import_module("kernel_gen.passes.lowering")
    LowerNnToKernelPass = lowering_module.LowerNnToKernelPass
    BufferResultsToOutParamsPass = lowering_module.BufferResultsToOutParamsPass
    LowerDmaMemoryHierarchyPass = lowering_module.LowerDmaMemoryHierarchyPass

    pm = PassManager(name="bad-dma-order")
    pm.add_pass(LowerNnToKernelPass())
    pm.add_pass(LowerDmaMemoryHierarchyPass())
    pm.add_pass(BufferResultsToOutParamsPass())
    with pytest.raises(ValueError, match="DmaMemoryHierarchyOrderError"):
        pm.run(object())

    pm = PassManager(name="missing-out-params")
    pm.add_pass(LowerNnToKernelPass())
    pm.add_pass(LowerDmaMemoryHierarchyPass())
    with pytest.raises(ValueError, match="DmaMemoryHierarchyOrderError"):
        pm.run(object())
