"""pass registry tests.

创建者: 小李飞刀
最后一次更改: 小李飞刀

功能说明:
- 覆盖 kernel_gen/passes/registry.py 的 pass/pipeline 注册、查询与错误短语约束。

当前覆盖率信息:
- 当前覆盖率: 未统计（本任务验证未启用 coverage 统计）。
- 达标判定: 待后续补充统计结果。

覆盖率命令:
- `pytest -q --cov=kernel_gen.passes.registry --cov-branch --cov-report=term-missing test/pass/test_pass_registry.py`

使用示例:
- pytest -q test/pass/test_pass_registry.py

关联文件:
- 功能实现: kernel_gen/passes/registry.py
- Spec 文档: spec/pass/registry.md
- 测试文件: test/pass/test_pass_registry.py
"""

from __future__ import annotations

import sys
from pathlib import Path

import importlib
import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

registry_module = importlib.import_module("kernel_gen.passes.registry")
PassRegistryError = registry_module.PassRegistryError
register_pass = registry_module.register_pass
register_pipeline = registry_module.register_pipeline
build_registered_pass = registry_module.build_registered_pass
build_registered_pipeline = registry_module.build_registered_pipeline
load_builtin_passes = registry_module.load_builtin_passes
list_registered_passes = registry_module.list_registered_passes
list_registered_pipelines = registry_module.list_registered_pipelines
_reset_registry_for_test = registry_module._reset_registry_for_test

pass_manager_module = importlib.import_module("kernel_gen.passes.pass_manager")
Pass = pass_manager_module.Pass
PassManager = pass_manager_module.PassManager


@pytest.fixture(autouse=True)
def _isolate_registry_state() -> None:
    _reset_registry_for_test()
    yield
    _reset_registry_for_test()


# TC-REGISTRY-001
# 创建者: 小李飞刀
# 最后一次更改: 小李飞刀
# 最近一次运行测试时间: 2026-04-08 21:47:00 +0800
# 最近一次运行成功时间: 2026-04-08 21:47:00 +0800
# 功能说明: 验证重复注册同名 pass 立即失败，且错误短语可机械匹配。
# 使用示例: pytest -q test/pass/test_pass_registry.py -k test_register_pass_duplicate_fails
# 对应功能实现文件路径: kernel_gen/passes/registry.py
# 对应 spec 文件路径: spec/pass/registry.md
# 对应测试文件路径: test/pass/test_pass_registry.py
def test_register_pass_duplicate_fails() -> None:
    @register_pass
    class FirstPass(Pass):
        name = "dup-pass"

        def run(self: "FirstPass", target: object) -> object:
            return target

    class SecondPass(Pass):
        name = "dup-pass"

        def run(self: "SecondPass", target: object) -> object:
            return target

    with pytest.raises(PassRegistryError, match=r"^PassRegistryError: pass 'dup-pass' is already registered$"):
        register_pass(SecondPass)


# TC-REGISTRY-002
# 创建者: 小李飞刀
# 最后一次更改: 小李飞刀
# 最近一次运行测试时间: 2026-04-08 21:47:00 +0800
# 最近一次运行成功时间: 2026-04-08 21:47:00 +0800
# 功能说明: 验证重复注册同名 pipeline 立即失败，且错误短语可机械匹配。
# 使用示例: pytest -q test/pass/test_pass_registry.py -k test_register_pipeline_duplicate_fails
# 对应功能实现文件路径: kernel_gen/passes/registry.py
# 对应 spec 文件路径: spec/pass/registry.md
# 对应测试文件路径: test/pass/test_pass_registry.py
def test_register_pipeline_duplicate_fails() -> None:
    @register_pipeline("dup-pipeline")
    def build_first() -> PassManager:
        return PassManager(name="first")

    with pytest.raises(PassRegistryError, match=r"^PassRegistryError: pipeline 'dup-pipeline' is already registered$"):

        @register_pipeline("dup-pipeline")
        def build_second() -> PassManager:  # pragma: no cover - should not be reached
            return PassManager(name="second")


# TC-REGISTRY-003
# 创建者: 小李飞刀
# 最后一次更改: 小李飞刀
# 最近一次运行测试时间: 2026-04-08 21:47:00 +0800
# 最近一次运行成功时间: 2026-04-08 21:47:00 +0800
# 功能说明: 验证未知 pass 名称构造时报稳定错误短语。
# 使用示例: pytest -q test/pass/test_pass_registry.py -k test_build_registered_pass_unknown
# 对应功能实现文件路径: kernel_gen/passes/registry.py
# 对应 spec 文件路径: spec/pass/registry.md
# 对应测试文件路径: test/pass/test_pass_registry.py
def test_build_registered_pass_unknown() -> None:
    with pytest.raises(PassRegistryError, match=r"^PassRegistryError: unknown pass 'missing-pass'$"):
        _ = build_registered_pass("missing-pass")


# TC-REGISTRY-004
# 创建者: 小李飞刀
# 最后一次更改: 小李飞刀
# 最近一次运行测试时间: 2026-04-08 21:47:00 +0800
# 最近一次运行成功时间: 2026-04-08 21:47:00 +0800
# 功能说明: 验证不可无参构造的 pass 会报告稳定错误短语。
# 使用示例: pytest -q test/pass/test_pass_registry.py -k test_build_registered_pass_not_constructible
# 对应功能实现文件路径: kernel_gen/passes/registry.py
# 对应 spec 文件路径: spec/pass/registry.md
# 对应测试文件路径: test/pass/test_pass_registry.py
def test_build_registered_pass_not_constructible() -> None:
    @register_pass
    class NeedsArgPass(Pass):
        name = "needs-arg"

        def __init__(self: "NeedsArgPass", value: int) -> None:
            self.value = value

        def run(self: "NeedsArgPass", target: object) -> object:
            return target

    with pytest.raises(PassRegistryError, match=r"^PassRegistryError: pass 'needs-arg' is not constructible$"):
        _ = build_registered_pass("needs-arg")


# TC-REGISTRY-005
# 创建者: 小李飞刀
# 最后一次更改: 小李飞刀
# 最近一次运行测试时间: 2026-04-08 21:47:00 +0800
# 最近一次运行成功时间: 2026-04-08 21:47:00 +0800
# 功能说明: 验证未知 pipeline 名称构造时报稳定错误短语。
# 使用示例: pytest -q test/pass/test_pass_registry.py -k test_build_registered_pipeline_unknown
# 对应功能实现文件路径: kernel_gen/passes/registry.py
# 对应 spec 文件路径: spec/pass/registry.md
# 对应测试文件路径: test/pass/test_pass_registry.py
def test_build_registered_pipeline_unknown() -> None:
    with pytest.raises(PassRegistryError, match=r"^PassRegistryError: unknown pipeline 'missing-pipeline'$"):
        _ = build_registered_pipeline("missing-pipeline")


# TC-REGISTRY-006
# 创建者: 小李飞刀
# 最后一次更改: 小李飞刀
# 最近一次运行测试时间: 2026-04-08 21:47:00 +0800
# 最近一次运行成功时间: 2026-04-08 21:47:00 +0800
# 功能说明: 验证 pipeline builder 返回值非法时会报告稳定错误短语。
# 使用示例: pytest -q test/pass/test_pass_registry.py -k test_build_registered_pipeline_must_return_pass_manager
# 对应功能实现文件路径: kernel_gen/passes/registry.py
# 对应 spec 文件路径: spec/pass/registry.md
# 对应测试文件路径: test/pass/test_pass_registry.py
def test_build_registered_pipeline_must_return_pass_manager() -> None:
    @register_pipeline("bad-pipeline")
    def _build_bad_pipeline() -> PassManager:  # type: ignore[return-value]
        return object()

    with pytest.raises(
        PassRegistryError, match=r"^PassRegistryError: pipeline 'bad-pipeline' did not return PassManager$"
    ):
        _ = build_registered_pipeline("bad-pipeline")


# TC-REGISTRY-007
# 创建者: 小李飞刀
# 最后一次更改: 小李飞刀
# 最近一次运行测试时间: 2026-04-08 21:47:00 +0800
# 最近一次运行成功时间: 2026-04-08 21:47:00 +0800
# 功能说明: 验证 list_registered_* 返回值顺序确定且不含重复项。
# 使用示例: pytest -q test/pass/test_pass_registry.py -k test_list_registered_are_sorted
# 对应功能实现文件路径: kernel_gen/passes/registry.py
# 对应 spec 文件路径: spec/pass/registry.md
# 对应测试文件路径: test/pass/test_pass_registry.py
def test_list_registered_are_sorted() -> None:
    @register_pass
    class PassB(Pass):
        name = "b-pass"

        def run(self: "PassB", target: object) -> object:
            return target

    @register_pass
    class PassA(Pass):
        name = "a-pass"

        def run(self: "PassA", target: object) -> object:
            return target

    @register_pipeline("b-pipeline")
    def _build_b() -> PassManager:
        return PassManager(name="b")

    @register_pipeline("a-pipeline")
    def _build_a() -> PassManager:
        return PassManager(name="a")

    assert list_registered_passes() == ["a-pass", "b-pass"]
    assert list_registered_pipelines() == ["a-pipeline", "b-pipeline"]


# TC-REGISTRY-008
# 创建者: 小李飞刀
# 最后一次更改: 金铲铲大作战
# 最近一次运行测试时间: 2026-04-08 21:47:00 +0800
# 最近一次运行成功时间: 2026-04-08 21:47:00 +0800
# 功能说明: 验证 load_builtin_passes 满足幂等性，并提供基础内置 pass/pipeline 与默认 lowering pipeline。
# 使用示例: pytest -q test/pass/test_pass_registry.py -k test_load_builtin_passes_is_idempotent
# 对应功能实现文件路径: kernel_gen/passes/registry.py
# 对应 spec 文件路径: spec/pass/registry.md
# 对应测试文件路径: test/pass/test_pass_registry.py
def test_load_builtin_passes_is_idempotent() -> None:
    load_builtin_passes()
    load_builtin_passes()
    assert "no-op" in list_registered_passes()
    assert "no-op-pipeline" in list_registered_pipelines()
    assert "default-lowering" in list_registered_pipelines()
    pm = build_registered_pipeline("default-lowering")
    assert isinstance(pm, PassManager)
    assert pm.name == "default-lowering"


# TC-REGISTRY-009
# 创建者: 小李飞刀
# 最后一次更改: 小李飞刀
# 最近一次运行测试时间: 2026-04-12 10:20:00 +0800
# 最近一次运行成功时间: 2026-04-12 10:20:00 +0800
# 功能说明: 验证 pass 提供 from_options 时可构造带参实例。
# 使用示例: pytest -q test/pass/test_pass_registry.py -k test_build_registered_pass_accepts_options
# 对应功能实现文件路径: kernel_gen/passes/registry.py
# 对应 spec 文件路径: spec/pass/registry.md
# 对应测试文件路径: test/pass/test_pass_registry.py
def test_build_registered_pass_accepts_options() -> None:
    @register_pass
    class OptionPass(Pass):
        name = "opt-pass"

        def __init__(self, mode: str) -> None:
            self.mode = mode

        @classmethod
        def from_options(cls, options: dict[str, str]) -> "OptionPass":
            return cls(options["mode"])

        def run(self, target: object) -> object:
            return target

    pass_obj = build_registered_pass("opt-pass", {"mode": "fast"})
    assert isinstance(pass_obj, OptionPass)
    assert pass_obj.mode == "fast"


# TC-REGISTRY-010
# 创建者: 小李飞刀
# 最后一次更改: 小李飞刀
# 最近一次运行测试时间: 2026-04-12 10:20:00 +0800
# 最近一次运行成功时间: 2026-04-12 10:20:00 +0800
# 功能说明: 验证 pass 未声明 from_options 时拒绝带参构造。
# 使用示例: pytest -q test/pass/test_pass_registry.py -k test_build_registered_pass_rejects_options
# 对应功能实现文件路径: kernel_gen/passes/registry.py
# 对应 spec 文件路径: spec/pass/registry.md
# 对应测试文件路径: test/pass/test_pass_registry.py
def test_build_registered_pass_rejects_options() -> None:
    @register_pass
    class PlainPass(Pass):
        name = "plain-pass"

        def run(self, target: object) -> object:
            return target

    with pytest.raises(
        PassRegistryError, match=r"^PassRegistryError: pass 'plain-pass' does not accept options$"
    ):
        _ = build_registered_pass("plain-pass", {"mode": "fast"})


# TC-REGISTRY-011
# 创建者: 小李飞刀
# 最后一次更改: 小李飞刀
# 最近一次运行测试时间: 2026-04-12 10:20:00 +0800
# 最近一次运行成功时间: 2026-04-12 10:20:00 +0800
# 功能说明: 验证 pipeline builder 接受 options 时可成功构造。
# 使用示例: pytest -q test/pass/test_pass_registry.py -k test_build_registered_pipeline_accepts_options
# 对应功能实现文件路径: kernel_gen/passes/registry.py
# 对应 spec 文件路径: spec/pass/registry.md
# 对应测试文件路径: test/pass/test_pass_registry.py
def test_build_registered_pipeline_accepts_options() -> None:
    @register_pipeline("opt-pipeline")
    def _build_pipeline(options: dict[str, str]) -> PassManager:
        return PassManager(name=f"opt-{options['mode']}")

    pm = build_registered_pipeline("opt-pipeline", {"mode": "fast"})
    assert isinstance(pm, PassManager)
    assert pm.name == "opt-fast"


# TC-REGISTRY-012
# 创建者: 小李飞刀
# 最后一次更改: 小李飞刀
# 最近一次运行测试时间: 2026-04-12 10:20:00 +0800
# 最近一次运行成功时间: 2026-04-12 10:20:00 +0800
# 功能说明: 验证 pipeline 不接受 options 时返回固定错误短语。
# 使用示例: pytest -q test/pass/test_pass_registry.py -k test_build_registered_pipeline_rejects_options
# 对应功能实现文件路径: kernel_gen/passes/registry.py
# 对应 spec 文件路径: spec/pass/registry.md
# 对应测试文件路径: test/pass/test_pass_registry.py
def test_build_registered_pipeline_rejects_options() -> None:
    @register_pipeline("plain-pipeline")
    def _build_plain() -> PassManager:
        return PassManager(name="plain")

    with pytest.raises(
        PassRegistryError, match=r"^PassRegistryError: pipeline 'plain-pipeline' does not accept options$"
    ):
        _ = build_registered_pipeline("plain-pipeline", {"mode": "fast"})
