"""pass_manager tests.

创建者: 李白
最后一次更改: 金铲铲大作战

功能说明:
- 覆盖 kernel_gen/passes/pass_manager.py 的 Pass 管理行为。

当前覆盖率信息:
- 当前覆盖率: `100%`（语句覆盖 `100%`，分支覆盖 `100%`）。
- 达标判定: 已达到 `95%` 覆盖率达标线。
- 本文件覆盖 `TC-PASS-001..005`，并补充 `Pass` 缺少 `name` 属性的非法输入分支。

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
# 最后一次更改: 金铲铲大作战
# 最近一次运行测试时间: 2026-04-04 00:00:00 +0800
# 最近一次运行成功时间: 2026-04-04 00:00:00 +0800
# 功能说明: 验证默认 lowering pipeline 会固定注册 `LowerNnToKernelPass -> BufferResultsToOutParamsPass`。
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
    order: list[str] = []

    def _record_lower(self: object, target: object) -> object:
        order.append("lower-nn-to-kernel")
        return target

    def _record_buffer(self: object, target: object) -> object:
        order.append("buffer-results-to-out-params")
        return target

    monkeypatch.setattr(LowerNnToKernelPass, "run", _record_lower)
    monkeypatch.setattr(BufferResultsToOutParamsPass, "run", _record_buffer)

    pm = build_default_lowering_pass_manager()
    sentinel = object()
    assert pm.run(sentinel) is sentinel
    assert order == ["lower-nn-to-kernel", "buffer-results-to-out-params"]


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
