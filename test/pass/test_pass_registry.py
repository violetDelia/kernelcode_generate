"""pass registry tests.

创建者: 小李飞刀
最后一次更改: jcc你莫辜负

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

from xdsl.context import Context
from xdsl.passes import ModulePass

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
LaunchKernelCostFuncError = importlib.import_module(
    "kernel_gen.passes.tuning.launch_kernel_cost_func"
).LaunchKernelCostFuncError


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


# TC-REGISTRY-007A
# 创建者: 朽木露琪亚
# 最后一次更改: 朽木露琪亚
# 功能说明: 验证内置 pass 加载后可通过稳定名称构造 outline-device-kernel。
# 使用示例: pytest -q test/pass/test_pass_registry.py -k test_build_registered_outline_device_kernel_pass
# 对应功能实现文件路径: kernel_gen/passes/registry.py
# 对应 spec 文件路径: spec/pass/registry.md
# 对应测试文件路径: test/pass/test_pass_registry.py
def test_build_registered_outline_device_kernel_pass() -> None:
    load_builtin_passes()

    pass_obj = build_registered_pass("outline-device-kernel")

    assert pass_obj.name == "outline-device-kernel"
    assert type(pass_obj).__name__ == "OutlineDeviceKernelPass"
    assert isinstance(pass_obj, ModulePass)


# TC-REGISTRY-007A-0
# 创建者: 朽木露琪亚
# 最后一次更改: 朽木露琪亚
# 功能说明: 验证内置 pass 加载后可通过稳定名称构造 tile-analysis ModulePass。
# 使用示例: pytest -q test/pass/test_pass_registry.py -k test_build_registered_tile_analysis_pass
# 对应功能实现文件路径: kernel_gen/passes/registry.py
# 对应 spec 文件路径: spec/pass/registry.md
# 对应测试文件路径: test/pass/test_pass_registry.py
def test_build_registered_tile_analysis_pass() -> None:
    load_builtin_passes()

    pass_obj = build_registered_pass("tile-analysis")

    assert pass_obj.name == "tile-analysis"
    assert type(pass_obj).__name__ == "TileAnalysisPass"
    assert isinstance(pass_obj, ModulePass)
    assert pass_obj.__class__.__module__ == "kernel_gen.passes.lowering.tile_analysis"


# TC-REGISTRY-007A-0B
# 创建者: 金铲铲大作战
# 最后一次更改: 金铲铲大作战
# 功能说明: 验证内置 pass 加载后可通过稳定名称构造 tile-reduce ModulePass。
# 使用示例: pytest -q test/pass/test_pass_registry.py -k test_build_registered_tile_reduce_pass
# 对应功能实现文件路径: kernel_gen/passes/registry.py
# 对应 spec 文件路径: spec/pass/registry.md
# 对应测试文件路径: test/pass/test_pass_registry.py
def test_build_registered_tile_reduce_pass() -> None:
    load_builtin_passes()

    pass_obj = build_registered_pass("tile-reduce")

    assert pass_obj.name == "tile-reduce"
    assert type(pass_obj).__name__ == "TileReducePass"
    assert isinstance(pass_obj, ModulePass)
    assert pass_obj.__class__.__module__ == "kernel_gen.passes.lowering.tile_reduce"


# TC-REGISTRY-007A-1
# 创建者: 小李飞刀
# 最后一次更改: 小李飞刀
# 功能说明: 验证内置 pass 加载后可通过稳定名称构造 tile-elewise ModulePass。
# 使用示例: pytest -q test/pass/test_pass_registry.py -k test_build_registered_tile_elewise_pass
# 对应功能实现文件路径: kernel_gen/passes/registry.py
# 对应 spec 文件路径: spec/pass/registry.md
# 对应测试文件路径: test/pass/test_pass_registry.py
def test_build_registered_tile_elewise_pass() -> None:
    load_builtin_passes()

    pass_obj = build_registered_pass("tile-elewise")

    assert pass_obj.name == "tile-elewise"
    assert type(pass_obj).__name__ == "TileElewisePass"
    assert isinstance(pass_obj, ModulePass)
    assert pass_obj.__class__.__module__ == "kernel_gen.passes.lowering.tile_elewise"


# TC-REGISTRY-007A-2
# 创建者: 金铲铲大作战
# 最后一次更改: jcc你莫辜负
# 功能说明: 验证 registry caller 当前冻结的 surviving public path 与 compat consumer matrix。
# 使用示例: pytest -q test/pass/test_pass_registry.py -k test_registry_surviving_public_paths_match_consumer_matrix
# 对应功能实现文件路径: kernel_gen/passes/registry.py
# 对应 spec 文件路径: spec/pass/registry.md
# 对应测试文件路径: test/pass/test_pass_registry.py
def test_registry_surviving_public_paths_match_consumer_matrix() -> None:
    expected_exports = (
        ("kernel_gen.passes.registry", "build_registered_pass", registry_module.build_registered_pass),
        ("kernel_gen.passes.registry", "build_registered_pipeline", registry_module.build_registered_pipeline),
        ("kernel_gen.passes.registry", "load_builtin_passes", registry_module.load_builtin_passes),
        ("kernel_gen.passes.pass_manager", "Pass", Pass),
        ("kernel_gen.passes.pass_manager", "PassManager", PassManager),
        (
            "kernel_gen.passes.buffer_results_to_out_params",
            "BufferResultsToOutParamsPass",
            importlib.import_module("kernel_gen.passes.buffer_results_to_out_params").BufferResultsToOutParamsPass,
        ),
        ("kernel_gen.passes.inline", "InlinePass", importlib.import_module("kernel_gen.passes.inline").InlinePass),
        (
            "kernel_gen.passes.attach_arch_information",
            "AttachArchInformationPass",
            importlib.import_module("kernel_gen.passes.attach_arch_information").AttachArchInformationPass,
        ),
        (
            "kernel_gen.passes.decompass",
            "DecompassPass",
            importlib.import_module("kernel_gen.passes.decompass").DecompassPass,
        ),
        (
            "kernel_gen.passes.outline_device_kernel",
            "OutlineDeviceKernelPass",
            importlib.import_module("kernel_gen.passes.outline_device_kernel").OutlineDeviceKernelPass,
        ),
        (
            "kernel_gen.passes.symbol_loop_hoist",
            "SymbolLoopHoistPass",
            importlib.import_module("kernel_gen.passes.symbol_loop_hoist").SymbolLoopHoistPass,
        ),
        (
            "kernel_gen.passes.lowering",
            "NnLoweringPass",
            importlib.import_module("kernel_gen.passes.lowering.nn_lowering").NnLoweringPass,
        ),
        (
            "kernel_gen.passes.lowering",
            "LowerDmaMemoryHierarchyPass",
            importlib.import_module("kernel_gen.passes.dma_memory_hierarchy").LowerDmaMemoryHierarchyPass,
        ),
        (
            "kernel_gen.passes.lowering",
            "TileAnalysisPass",
            importlib.import_module("kernel_gen.passes.lowering.tile_analysis").TileAnalysisPass,
        ),
        (
            "kernel_gen.passes.lowering",
            "TileElewisePass",
            importlib.import_module("kernel_gen.passes.lowering.tile_elewise").TileElewisePass,
        ),
        (
            "kernel_gen.passes.lowering",
            "TileReducePass",
            importlib.import_module("kernel_gen.passes.lowering.tile_reduce").TileReducePass,
        ),
        (
            "kernel_gen.passes.dma_memory_hierarchy",
            "LowerDmaMemoryHierarchyPass",
            importlib.import_module("kernel_gen.passes.dma_memory_hierarchy").LowerDmaMemoryHierarchyPass,
        ),
        (
            "kernel_gen.passes.memory_pool",
            "MemoryPoolPass",
            importlib.import_module("kernel_gen.passes.memory_pool").MemoryPoolPass,
        ),
        (
            "kernel_gen.passes.lowering.tile_analysis",
            "TileAnalysisPass",
            importlib.import_module("kernel_gen.passes.lowering.tile_analysis").TileAnalysisPass,
        ),
        (
            "kernel_gen.passes.lowering.tile_elewise",
            "TileElewisePass",
            importlib.import_module("kernel_gen.passes.lowering.tile_elewise").TileElewisePass,
        ),
        (
            "kernel_gen.passes.lowering.tile_reduce",
            "TileReducePass",
            importlib.import_module("kernel_gen.passes.lowering.tile_reduce").TileReducePass,
        ),
        (
            "kernel_gen.passes.lowering.outline_device_kernel",
            "OutlineDeviceKernelPass",
            importlib.import_module("kernel_gen.passes.outline_device_kernel").OutlineDeviceKernelPass,
        ),
        (
            "kernel_gen.passes.lowering.symbol_loop_hoist",
            "SymbolLoopHoistPass",
            importlib.import_module("kernel_gen.passes.symbol_loop_hoist").SymbolLoopHoistPass,
        ),
    )

    for module_name, attr_name, expected_obj in expected_exports:
        module = importlib.import_module(module_name)
        assert getattr(module, attr_name) is expected_obj

    lowering_module = importlib.import_module("kernel_gen.passes.lowering")
    assert not hasattr(lowering_module, "BufferResultsToOutParamsPass")


# TC-REGISTRY-007A-3
# 创建者: 小李飞刀
# 最后一次更改: 小李飞刀
# 功能说明: 验证内置 nn lowering pass 加载后返回 ModulePass。
# 使用示例: pytest -q test/pass/test_pass_registry.py -k test_build_registered_nn_lowering_pass_is_module_pass
# 对应功能实现文件路径: kernel_gen/passes/registry.py
# 对应 spec 文件路径: spec/pass/registry.md
# 对应测试文件路径: test/pass/test_pass_registry.py
def test_build_registered_nn_lowering_pass_is_module_pass() -> None:
    load_builtin_passes()

    pass_obj = build_registered_pass("lower-nn")

    assert pass_obj.name == "lower-nn"
    assert type(pass_obj).__name__ == "NnLoweringPass"
    assert isinstance(pass_obj, ModulePass)


# TC-REGISTRY-007B
# 创建者: 小李飞刀
# 最后一次更改: 小李飞刀
# 最近一次运行测试时间: 2026-04-18 00:00:00 +0800
# 最近一次运行成功时间: 2026-04-18 00:00:00 +0800
# 功能说明: 验证内置 pass 加载后可通过稳定名称构造 launch-kernel-cost-func，并透传 cost_kind 选项。
# 使用示例: pytest -q test/pass/test_pass_registry.py -k test_build_registered_launch_kernel_cost_func_pass
# 对应功能实现文件路径: kernel_gen/passes/registry.py
# 对应 spec 文件路径: spec/pass/registry.md
# 对应测试文件路径: test/pass/test_pass_registry.py
def test_build_registered_launch_kernel_cost_func_pass() -> None:
    load_builtin_passes()

    pass_obj = build_registered_pass("launch-kernel-cost-func", {"cost_kind": "compute|memory"})

    assert pass_obj.name == "launch-kernel-cost-func"
    assert type(pass_obj).__name__ == "LaunchKernelCostFuncPass"
    assert getattr(pass_obj, "cost_kind") == "compute|memory"
    assert getattr(pass_obj, "cost_kinds") == ("compute", "memory")


# TC-REGISTRY-007C
# 创建者: 金铲铲大作战
# 最后一次更改: 金铲铲大作战
# 最近一次运行测试时间: 2026-04-18 02:00:00 +0800
# 最近一次运行成功时间: 2026-04-18 02:00:00 +0800
# 功能说明: 验证 registry 构造 launch-kernel-cost-func 时不会把非法 `cost_kind` 改写成通用 option error。
# 使用示例: pytest -q test/pass/test_pass_registry.py -k test_build_registered_launch_kernel_cost_func_rejects_invalid_kind
# 对应功能实现文件路径: kernel_gen/passes/registry.py
# 对应 spec 文件路径: spec/pass/registry.md
# 对应测试文件路径: test/pass/test_pass_registry.py
def test_build_registered_launch_kernel_cost_func_rejects_invalid_kind() -> None:
    load_builtin_passes()

    with pytest.raises(
        LaunchKernelCostFuncError,
        match=r"^LaunchKernelCostFuncError: cost_kind must be one of compute, memory$",
    ):
        build_registered_pass("launch-kernel-cost-func", {"cost_kind": "invalid"})


# TC-REGISTRY-007D
# 创建者: 朽木露琪亚
# 最后一次更改: 朽木露琪亚
# 功能说明: 验证 registry 可直接构造 xdsl ModulePass，并保持返回值为 ModulePass 实例。
# 使用示例: pytest -q test/pass/test_pass_registry.py -k test_build_registered_module_pass
# 对应功能实现文件路径: kernel_gen/passes/registry.py
# 对应 spec 文件路径: spec/pass/registry.md
# 对应测试文件路径: test/pass/test_pass_registry.py
def test_build_registered_module_pass() -> None:
    @register_pass
    class ModuleNoopPass(ModulePass):
        name = "module-noop-pass"

        def apply(self: "ModuleNoopPass", ctx: Context, module: dict[str, int]) -> None:
            assert isinstance(ctx, Context)
            module["value"] += 1

    pass_obj = build_registered_pass("module-noop-pass")

    assert isinstance(pass_obj, ModulePass)
    assert type(pass_obj).__name__ == "ModuleNoopPass"

    module = {"value": 1}
    pm = PassManager(name="module-noop")
    pm.add_pass(pass_obj)
    assert pm.run(module) is module
    assert module["value"] == 2


# TC-REGISTRY-007E
# 创建者: 朽木露琪亚
# 最后一次更改: 朽木露琪亚
# 功能说明: 验证 ModulePass 的 from_options 构造入口可被 registry 正常透传。
# 使用示例: pytest -q test/pass/test_pass_registry.py -k test_build_registered_module_pass_with_options
# 对应功能实现文件路径: kernel_gen/passes/registry.py
# 对应 spec 文件路径: spec/pass/registry.md
# 对应测试文件路径: test/pass/test_pass_registry.py
def test_build_registered_module_pass_with_options() -> None:
    @register_pass
    class ModuleScalePass(ModulePass):
        name = "module-scale-pass"

        def __init__(self: "ModuleScalePass", scale: int) -> None:
            self.scale = scale

        @classmethod
        def from_options(cls, options: dict[str, str]) -> "ModuleScalePass":
            return cls(int(options["scale"]))

        def apply(self: "ModuleScalePass", ctx: Context, module: dict[str, int]) -> None:
            assert isinstance(ctx, Context)
            module["value"] *= self.scale

    pass_obj = build_registered_pass("module-scale-pass", {"scale": "3"})

    assert isinstance(pass_obj, ModulePass)
    assert type(pass_obj).__name__ == "ModuleScalePass"
    assert getattr(pass_obj, "scale") == 3

    module = {"value": 2}
    pm = PassManager(name="module-scale")
    pm.add_pass(pass_obj)
    assert pm.run(module) is module
    assert module["value"] == 6


# TC-REGISTRY-007F
# 创建者: 金铲铲大作战
# 最后一次更改: 金铲铲大作战
# 功能说明: 验证内置加载后 buffer-results-to-out-params 通过 registry 返回 ModulePass。
# 使用示例: pytest -q test/pass/test_pass_registry.py -k test_build_registered_buffer_results_to_out_params_pass
# 对应功能实现文件路径: kernel_gen/passes/registry.py
# 对应 spec 文件路径: spec/pass/registry.md
# 对应测试文件路径: test/pass/test_pass_registry.py
def test_build_registered_buffer_results_to_out_params_pass() -> None:
    load_builtin_passes()

    pass_obj = build_registered_pass("buffer-results-to-out-params")

    assert isinstance(pass_obj, ModulePass)
    assert pass_obj.name == "buffer-results-to-out-params"
    assert type(pass_obj).__name__ == "BufferResultsToOutParamsPass"


# TC-REGISTRY-007G
# 创建者: 金铲铲大作战
# 最后一次更改: 金铲铲大作战
# 功能说明: 验证内置加载后 decompass 通过 registry 返回 ModulePass。
# 使用示例: pytest -q test/pass/test_pass_registry.py -k test_build_registered_decompass_pass
# 对应功能实现文件路径: kernel_gen/passes/registry.py
# 对应 spec 文件路径: spec/pass/registry.md
# 对应测试文件路径: test/pass/test_pass_registry.py
def test_build_registered_decompass_pass() -> None:
    load_builtin_passes()

    pass_obj = build_registered_pass("decompass")

    assert isinstance(pass_obj, ModulePass)
    assert pass_obj.name == "decompass"
    assert type(pass_obj).__name__ == "DecompassPass"


# TC-REGISTRY-007H
# 创建者: 金铲铲大作战
# 最后一次更改: 金铲铲大作战
# 功能说明: 验证内置加载后 inline 通过 registry 返回 ModulePass。
# 使用示例: pytest -q test/pass/test_pass_registry.py -k test_build_registered_inline_pass
# 对应功能实现文件路径: kernel_gen/passes/registry.py
# 对应 spec 文件路径: spec/pass/registry.md
# 对应测试文件路径: test/pass/test_pass_registry.py
def test_build_registered_inline_pass() -> None:
    load_builtin_passes()

    pass_obj = build_registered_pass("inline")

    assert isinstance(pass_obj, ModulePass)
    assert pass_obj.name == "inline"
    assert type(pass_obj).__name__ == "InlinePass"


# TC-REGISTRY-007I
# 创建者: 金铲铲大作战
# 最后一次更改: 金铲铲大作战
# 功能说明: 验证内置加载后 attach-arch-information 通过 registry 返回 ModulePass。
# 使用示例: pytest -q test/pass/test_pass_registry.py -k test_build_registered_attach_arch_information_pass
# 对应功能实现文件路径: kernel_gen/passes/registry.py
# 对应 spec 文件路径: spec/pass/registry.md
# 对应测试文件路径: test/pass/test_pass_registry.py
def test_build_registered_attach_arch_information_pass() -> None:
    load_builtin_passes()

    pass_obj = build_registered_pass("attach-arch-information")

    assert isinstance(pass_obj, ModulePass)
    assert pass_obj.name == "attach-arch-information"
    assert type(pass_obj).__name__ == "AttachArchInformationPass"


# TC-REGISTRY-007J
# 创建者: 金铲铲大作战
# 最后一次更改: jcc你莫辜负
# 功能说明: 验证已退场的 lowering 旧路径在 S1/S2 基线中稳定失败。
# 使用示例: pytest -q test/pass/test_pass_registry.py -k test_registry_old_lowering_paths_fail_fast
# 对应功能实现文件路径: kernel_gen/passes/registry.py
# 对应 spec 文件路径: spec/pass/registry.md
# 对应测试文件路径: test/pass/test_pass_registry.py
def test_registry_old_lowering_paths_fail_fast() -> None:
    old_module_paths = (
        "kernel_gen.passes.lowering.registry",
        "kernel_gen.passes.lowering.pass_manager",
        "kernel_gen.passes.lowering.inline",
        "kernel_gen.passes.lowering.attach_arch_information",
        "kernel_gen.passes.lowering.decompass",
        "kernel_gen.passes.lowering.buffer_results_to_out_params",
        "kernel_gen.passes.lowering.nn_to_kernel",
    )

    for module_name in old_module_paths:
        with pytest.raises(ModuleNotFoundError):
            importlib.import_module(module_name)


# TC-REGISTRY-007K
# 创建者: 朽木露琪亚
# 最后一次更改: 朽木露琪亚
# 功能说明: 验证内置 pipeline 加载后可通过稳定名称构造 npu-demo-lowering。
# 使用示例: pytest -q test/pass/test_pass_registry.py -k test_build_registered_npu_demo_lowering_pipeline
# 对应功能实现文件路径: kernel_gen/passes/registry.py
# 对应 spec 文件路径: spec/pass/registry.md
# 对应测试文件路径: test/pass/test_pass_registry.py
def test_build_registered_npu_demo_lowering_pipeline() -> None:
    load_builtin_passes()

    pm = build_registered_pipeline("npu-demo-lowering", {"target": "npu_demo"})

    assert isinstance(pm, PassManager)
    assert pm.name == "npu-demo-lowering"


# TC-REGISTRY-008
# 创建者: 小李飞刀
# 最后一次更改: 金铲铲大作战
# 最近一次运行测试时间: 2026-04-08 21:47:00 +0800
# 最近一次运行成功时间: 2026-04-08 21:47:00 +0800
# 功能说明: 验证 load_builtin_passes 满足幂等性，并提供基础内置 pass/pipeline、default-lowering 与 npu-demo-lowering。
# 使用示例: pytest -q test/pass/test_pass_registry.py -k test_load_builtin_passes_is_idempotent
# 对应功能实现文件路径: kernel_gen/passes/registry.py
# 对应 spec 文件路径: spec/pass/registry.md
# 对应测试文件路径: test/pass/test_pass_registry.py
def test_load_builtin_passes_is_idempotent() -> None:
    load_builtin_passes()
    load_builtin_passes()
    assert "no-op" in list_registered_passes()
    assert "inline" in list_registered_passes()
    assert "attach-arch-information" in list_registered_passes()
    assert "no-op-pipeline" in list_registered_pipelines()
    assert "default-lowering" in list_registered_pipelines()
    assert "npu-demo-lowering" in list_registered_pipelines()
    pm = build_registered_pipeline("default-lowering")
    assert isinstance(pm, PassManager)
    assert pm.name == "default-lowering"
    npu_pm = build_registered_pipeline("npu-demo-lowering", {"target": "npu_demo"})
    assert isinstance(npu_pm, PassManager)
    assert npu_pm.name == "npu-demo-lowering"


# TC-REGISTRY-008A
# 创建者: jcc你莫辜负
# 最后一次更改: jcc你莫辜负
# 最近一次运行测试时间: 2026-04-13 11:38:00 +0800
# 最近一次运行成功时间: 2026-04-13 11:38:00 +0800
# 功能说明: 验证重置 registry 后再次 load_builtin_passes 仍能注册 default-lowering 与 npu-demo-lowering。
# 使用示例: pytest -q test/pass/test_pass_registry.py -k test_load_builtin_passes_after_reset_registers_default_lowering
# 对应功能实现文件路径: kernel_gen/passes/registry.py
# 对应 spec 文件路径: spec/pass/registry.md
# 对应测试文件路径: test/pass/test_pass_registry.py
def test_load_builtin_passes_after_reset_registers_default_lowering() -> None:
    load_builtin_passes()
    _reset_registry_for_test()
    load_builtin_passes()
    assert "default-lowering" in list_registered_pipelines()
    assert "npu-demo-lowering" in list_registered_pipelines()
    pm = build_registered_pipeline("default-lowering")
    assert isinstance(pm, PassManager)
    assert pm.name == "default-lowering"
    npu_pm = build_registered_pipeline("npu-demo-lowering", {"target": "npu_demo"})
    assert isinstance(npu_pm, PassManager)
    assert npu_pm.name == "npu-demo-lowering"


# TC-REGISTRY-008B
# 创建者: 金铲铲大作战
# 最后一次更改: 金铲铲大作战
# 功能说明: 验证 npu-demo-lowering 接受 target 选项。
# 使用示例: pytest -q test/pass/test_pass_registry.py -k test_build_registered_npu_demo_lowering_pipeline_with_options
# 对应功能实现文件路径: kernel_gen/passes/registry.py
# 对应 spec 文件路径: spec/pass/registry.md
# 对应测试文件路径: test/pass/test_pass_registry.py
def test_build_registered_npu_demo_lowering_pipeline_with_options() -> None:
    load_builtin_passes()

    pm = build_registered_pipeline("npu-demo-lowering", {"target": "npu_demo"})
    assert isinstance(pm, PassManager)
    assert pm.name == "npu-demo-lowering"


# TC-REGISTRY-008C
# 创建者: 金铲铲大作战
# 最后一次更改: 金铲铲大作战
# 功能说明: 验证 npu-demo-lowering 的未知选项会显式失败。
# 使用示例: pytest -q test/pass/test_pass_registry.py -k test_build_registered_npu_demo_lowering_pipeline_rejects_unknown_option
# 对应功能实现文件路径: kernel_gen/passes/registry.py
# 对应 spec 文件路径: spec/pass/registry.md
# 对应测试文件路径: test/pass/test_pass_registry.py
def test_build_registered_npu_demo_lowering_pipeline_rejects_unknown_option() -> None:
    load_builtin_passes()

    with pytest.raises(
        PassRegistryError, match=r"^PassRegistryError: pipeline 'npu-demo-lowering' option error$"
    ):
        build_registered_pipeline("npu-demo-lowering", {"only-kernel": "true"})


# TC-REGISTRY-009
# 创建者: 金铲铲大作战
# 最后一次更改: 金铲铲大作战
# 最近一次运行测试时间: 2026-04-12 10:45:00 +0800
# 最近一次运行成功时间: 2026-04-12 10:45:00 +0800
# 功能说明: 验证带 options 的 pass 可通过 from_options 构造。
# 使用示例: pytest -q test/pass/test_pass_registry.py -k test_build_registered_pass_with_options
# 对应功能实现文件路径: kernel_gen/passes/registry.py
# 对应 spec 文件路径: spec/pass/registry.md
# 对应测试文件路径: test/pass/test_pass_registry.py
def test_build_registered_pass_with_options() -> None:
    @register_pass
    class OptionPass(Pass):
        name = "option-pass"

        def __init__(self: "OptionPass", mode: str) -> None:
            self.mode = mode

        @classmethod
        def from_options(cls, options: dict[str, str]) -> "OptionPass":
            return cls(options["mode"])

        def run(self: "OptionPass", target: object) -> object:
            return target

    pass_obj = build_registered_pass("option-pass", {"mode": "fast"})
    assert isinstance(pass_obj, OptionPass)
    assert pass_obj.mode == "fast"


# TC-REGISTRY-010
# 创建者: 金铲铲大作战
# 最后一次更改: 金铲铲大作战
# 最近一次运行测试时间: 2026-04-12 10:45:00 +0800
# 最近一次运行成功时间: 2026-04-12 10:45:00 +0800
# 功能说明: 验证不支持 options 的 pass 会报告稳定错误短语。
# 使用示例: pytest -q test/pass/test_pass_registry.py -k test_build_registered_pass_options_not_supported
# 对应功能实现文件路径: kernel_gen/passes/registry.py
# 对应 spec 文件路径: spec/pass/registry.md
# 对应测试文件路径: test/pass/test_pass_registry.py
def test_build_registered_pass_options_not_supported() -> None:
    @register_pass
    class PlainPass(Pass):
        name = "plain-pass"

        def run(self: "PlainPass", target: object) -> object:
            return target

    with pytest.raises(
        PassRegistryError, match=r"^PassRegistryError: pass 'plain-pass' does not accept options$"
    ):
        _ = build_registered_pass("plain-pass", {"mode": "fast"})


# TC-REGISTRY-011
# 创建者: 金铲铲大作战
# 最后一次更改: 金铲铲大作战
# 最近一次运行测试时间: 2026-04-12 10:45:00 +0800
# 最近一次运行成功时间: 2026-04-12 10:45:00 +0800
# 功能说明: 验证 pass 的 options 构造失败会报告稳定错误短语。
# 使用示例: pytest -q test/pass/test_pass_registry.py -k test_build_registered_pass_option_error
# 对应功能实现文件路径: kernel_gen/passes/registry.py
# 对应 spec 文件路径: spec/pass/registry.md
# 对应测试文件路径: test/pass/test_pass_registry.py
def test_build_registered_pass_option_error() -> None:
    @register_pass
    class ErrorPass(Pass):
        name = "error-pass"

        @classmethod
        def from_options(cls, options: dict[str, str]) -> "ErrorPass":
            raise ValueError("invalid options")

        def run(self: "ErrorPass", target: object) -> object:
            return target

    with pytest.raises(PassRegistryError, match=r"^PassRegistryError: pass 'error-pass' option error$"):
        _ = build_registered_pass("error-pass", {"mode": "fast"})


# TC-REGISTRY-012
# 创建者: 金铲铲大作战
# 最后一次更改: 金铲铲大作战
# 最近一次运行测试时间: 2026-04-12 10:45:00 +0800
# 最近一次运行成功时间: 2026-04-12 10:45:00 +0800
# 功能说明: 验证带 options 的 pipeline 会把 options 透传给 builder。
# 使用示例: pytest -q test/pass/test_pass_registry.py -k test_build_registered_pipeline_with_options
# 对应功能实现文件路径: kernel_gen/passes/registry.py
# 对应 spec 文件路径: spec/pass/registry.md
# 对应测试文件路径: test/pass/test_pass_registry.py
def test_build_registered_pipeline_with_options() -> None:
    @register_pipeline("option-pipeline")
    def _build_option_pipeline(options: dict[str, str]) -> PassManager:
        return PassManager(name=options["mode"])

    pm = build_registered_pipeline("option-pipeline", {"mode": "analysis"})
    assert isinstance(pm, PassManager)
    assert pm.name == "analysis"


# TC-REGISTRY-013
# 创建者: 金铲铲大作战
# 最后一次更改: 金铲铲大作战
# 最近一次运行测试时间: 2026-04-12 10:45:00 +0800
# 最近一次运行成功时间: 2026-04-12 10:45:00 +0800
# 功能说明: 验证不支持 options 的 pipeline 会报告稳定错误短语。
# 使用示例: pytest -q test/pass/test_pass_registry.py -k test_build_registered_pipeline_options_not_supported
# 对应功能实现文件路径: kernel_gen/passes/registry.py
# 对应 spec 文件路径: spec/pass/registry.md
# 对应测试文件路径: test/pass/test_pass_registry.py
def test_build_registered_pipeline_options_not_supported() -> None:
    @register_pipeline("plain-pipeline")
    def _build_plain_pipeline() -> PassManager:
        return PassManager(name="plain")

    with pytest.raises(
        PassRegistryError, match=r"^PassRegistryError: pipeline 'plain-pipeline' does not accept options$"
    ):
        _ = build_registered_pipeline("plain-pipeline", {"mode": "fast"})


# TC-REGISTRY-014
# 创建者: 金铲铲大作战
# 最后一次更改: 金铲铲大作战
# 最近一次运行测试时间: 2026-04-12 10:45:00 +0800
# 最近一次运行成功时间: 2026-04-12 10:45:00 +0800
# 功能说明: 验证 pipeline 的 options 构造失败会报告稳定错误短语。
# 使用示例: pytest -q test/pass/test_pass_registry.py -k test_build_registered_pipeline_option_error
# 对应功能实现文件路径: kernel_gen/passes/registry.py
# 对应 spec 文件路径: spec/pass/registry.md
# 对应测试文件路径: test/pass/test_pass_registry.py
def test_build_registered_pipeline_option_error() -> None:
    @register_pipeline("error-pipeline")
    def _build_error_pipeline(options: dict[str, str]) -> PassManager:
        raise ValueError("invalid options")

    with pytest.raises(
        PassRegistryError, match=r"^PassRegistryError: pipeline 'error-pipeline' option error$"
    ):
        _ = build_registered_pipeline("error-pipeline", {"mode": "fast"})
