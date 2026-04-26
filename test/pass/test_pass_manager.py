"""pass_manager tests.

创建者: 李白
最后一次更改: 金铲铲大作战

功能说明:
- 覆盖 kernel_gen/passes/pass_manager.py 的 Pass 管理行为。

当前覆盖率信息:
- 当前覆盖率: `100%`（语句覆盖 `100%`，分支覆盖 `100%`）。
- 达标判定: 已达到 `95%` 覆盖率达标线。
- 本文件覆盖 `TC-PASS-001..017`，并补充 `Pass` 缺少 `name` 属性的非法输入分支。

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

import contextlib
import sys
from pathlib import Path

import importlib
import pytest

from xdsl.dialects.builtin import ModuleOp
from xdsl.passes import ModulePass

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
WORKTREE_FALLBACK_REPO = REPO_ROOT.parent if REPO_ROOT.name.startswith("wt-") else None

pass_module = importlib.import_module("kernel_gen.passes.pass_manager")
Pass = pass_module.Pass
PassManager = pass_module.PassManager
pipeline_module = importlib.import_module("kernel_gen.passes.pipeline")
build_default_lowering_pipeline = pipeline_module.build_default_lowering_pipeline
buffer_results_module = importlib.import_module("kernel_gen.passes.buffer_results_to_out_params")
BufferResultsToOutParamsPass = buffer_results_module.BufferResultsToOutParamsPass


def _reload_registry_module():
    """重新导入 registry 模块并恢复其公开状态。"""

    return importlib.reload(importlib.import_module("kernel_gen.passes.registry"))


@contextlib.contextmanager
def _worktree_only_imports(*module_names: str):
    original_path = list(sys.path)
    if WORKTREE_FALLBACK_REPO is not None:
        sys.path[:] = [
            entry
            for entry in sys.path
            if Path(entry or ".").resolve() != WORKTREE_FALLBACK_REPO.resolve()
        ]
    isolated_modules = (
        "kernel_gen",
        "kernel_gen.passes",
        "kernel_gen.passes.lowering",
        *module_names,
    )
    previous_modules = {name: sys.modules.pop(name, None) for name in isolated_modules}
    try:
        yield
    finally:
        for name in isolated_modules:
            sys.modules.pop(name, None)
        for name, module in previous_modules.items():
            if module is not None:
                sys.modules[name] = module
        sys.path[:] = original_path


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


# TC-PASS-005A
# 创建者: 小李飞刀
# 最后一次更改: 小李飞刀
# 功能说明: 验证 ModulePass 仅实现 apply(...) 时，PassManager 仍可在 builtin.module 目标上执行。
# 使用示例: pytest -q test/pass/test_pass_manager.py -k test_pass_manager_module_pass_apply_only
# 对应功能实现文件路径: kernel_gen/passes/pass_manager.py
# 对应 spec 文件路径: spec/pass/pass_manager.md
# 对应测试文件路径: test/pass/test_pass_manager.py
def test_pass_manager_module_pass_apply_only() -> None:
    order: list[str] = []

    class ApplyOnlyPass(ModulePass):
        name = "apply-only"

        def apply(self, ctx: object, op: ModuleOp) -> None:
            _ = ctx
            order.append("apply-only")
            assert isinstance(op, ModuleOp)

    pm = PassManager(name="module-pass")
    pm.add_pass(ApplyOnlyPass())
    module = ModuleOp([])
    assert pm.run(module) is module
    assert order == ["apply-only"]


# TC-PASS-005B
# 创建者: 小李飞刀
# 最后一次更改: 小李飞刀
# 功能说明: 验证 registry 构造出的 lower-nn 可继续由 PassManager 执行。
# 使用示例: pytest -q test/pass/test_pass_manager.py -k test_pass_manager_runs_registered_lower_nn
# 对应功能实现文件路径: kernel_gen/passes/pass_manager.py
# 对应 spec 文件路径: spec/pass/pass_manager.md
# 对应测试文件路径: test/pass/test_pass_manager.py
def test_pass_manager_runs_registered_lower_nn(monkeypatch: pytest.MonkeyPatch) -> None:
    registry_module = _reload_registry_module()
    try:
        registry_module.load_builtin_passes()
        pass_obj = registry_module.build_registered_pass("lower-nn")
        order: list[str] = []

        def _record_run(self: object, target: ModuleOp) -> ModuleOp:
            order.append(getattr(self, "name"))
            assert isinstance(target, ModuleOp)
            return target

        monkeypatch.setattr(type(pass_obj), "run", _record_run)

        pm = PassManager(name="registry-lower-nn")
        pm.add_pass(pass_obj)
        module = ModuleOp([])

        assert pm.run(module) is module
        assert order == ["lower-nn"]
    finally:
        _reload_registry_module()


# TC-PASS-005C
# 创建者: 金铲铲大作战
# 最后一次更改: 金铲铲大作战
# 功能说明: 验证 pass manager caller 当前冻结的 surviving import matrix。
# 使用示例: pytest -q test/pass/test_pass_manager.py -k test_pass_manager_surviving_import_matrix
# 对应功能实现文件路径: kernel_gen/passes/pass_manager.py
# 对应 spec 文件路径: spec/pass/pass_manager.md
# 对应测试文件路径: test/pass/test_pass_manager.py
def test_pass_manager_surviving_import_matrix() -> None:
    lowering_module = importlib.import_module("kernel_gen.passes.lowering")
    buffer_results_module = importlib.import_module("kernel_gen.passes.buffer_results_to_out_params")
    default_lowering_pipeline_module = importlib.import_module(
        "kernel_gen.passes.pipeline.default_lowering"
    )
    npu_demo_pipeline_module = importlib.import_module("kernel_gen.passes.pipeline.npu_demo_lowering")
    dma_hierarchy_module = importlib.import_module("kernel_gen.passes.dma_memory_hierarchy")
    tile_analysis_module = importlib.import_module("kernel_gen.passes.tile.analysis")
    tile_elewise_module = importlib.import_module("kernel_gen.passes.tile.elewise")
    tile_reduce_module = importlib.import_module("kernel_gen.passes.tile.reduce")

    assert pass_module.Pass is Pass
    assert pass_module.PassManager is PassManager
    assert (
        pipeline_module.build_default_lowering_pipeline
        is default_lowering_pipeline_module.build_default_lowering_pipeline
    )
    assert (
        pipeline_module.build_npu_demo_lowering_pipeline
        is npu_demo_pipeline_module.build_npu_demo_lowering_pipeline
    )
    assert lowering_module.NnLoweringPass is importlib.import_module(
        "kernel_gen.passes.lowering.nn_lowering"
    ).NnLoweringPass
    assert BufferResultsToOutParamsPass is buffer_results_module.BufferResultsToOutParamsPass
    assert not hasattr(lowering_module, "BufferResultsToOutParamsPass")
    assert lowering_module.LowerDmaMemoryHierarchyPass is dma_hierarchy_module.LowerDmaMemoryHierarchyPass
    assert lowering_module.TileAnalysisPass is tile_analysis_module.TileAnalysisPass
    assert lowering_module.TileElewisePass is tile_elewise_module.TileElewisePass
    assert lowering_module.TileReducePass is tile_reduce_module.TileReducePass


# TC-PASS-005D
# 创建者: 金铲铲大作战
# 最后一次更改: 金铲铲大作战
# 功能说明: 验证已退场的旧 pass manager / registry lowering 路径、旧 tile submodule path 与 analysis family 路径稳定失败。
# 使用示例: pytest -q test/pass/test_pass_manager.py -k test_pass_manager_old_lowering_paths_fail_fast
# 对应功能实现文件路径: kernel_gen/passes/pass_manager.py
# 对应 spec 文件路径: spec/pass/pass_manager.md
# 对应测试文件路径: test/pass/test_pass_manager.py
def test_pass_manager_old_lowering_paths_fail_fast() -> None:
    old_module_paths = (
        "kernel_gen.analysis",
        "kernel_gen.analysis.analysis",
        "kernel_gen.analysis.compute",
        "kernel_gen.analysis.memory",
        "kernel_gen.passes.analysis",
        "kernel_gen.passes.analysis.func_cost",
        "kernel_gen.passes.lowering.pass_manager",
        "kernel_gen.passes.lowering.registry",
        "kernel_gen.passes.lowering.tile_analysis",
        "kernel_gen.passes.lowering.tile_elewise",
        "kernel_gen.passes.lowering.tile_reduce",
    )
    with _worktree_only_imports(*old_module_paths):
        for module_name in old_module_paths:
            with pytest.raises(ModuleNotFoundError):
                importlib.import_module(module_name)


# TC-PASS-006
# 创建者: 金铲铲大作战
# 最后一次更改: jcc你莫辜负
# 最近一次运行测试时间: 未运行
# 最近一次运行成功时间: 未运行
# 功能说明: 验证 pass_manager 不再承载旧默认 lowering builder 兼容入口。
# 使用示例: pytest -q test/pass/test_pass_manager.py -k test_pass_manager_has_no_legacy_default_lowering_builder
# 对应功能实现文件路径: kernel_gen/passes/pass_manager.py
# 对应 spec 文件路径: spec/pass/pass_manager.md
# 对应测试文件路径: test/pass/test_pass_manager.py
@pytest.mark.nn_lowering
def test_pass_manager_has_no_legacy_default_lowering_builder() -> None:
    assert not hasattr(pass_module, "build_default_lowering_pass_manager")
    with pytest.raises(ImportError):
        exec("from kernel_gen.passes.pass_manager import build_default_lowering_pass_manager", {})
    pm = build_default_lowering_pipeline()
    assert isinstance(pm, PassManager)
    assert pm.name == "default-lowering"


# TC-PASS-007
# 创建者: 金铲铲大作战
# 最后一次更改: 小李飞刀
# 功能说明: 验证 PassManager 不根据业务 pass 名称施加顺序约束，只按添加顺序执行。
# 使用示例: pytest -q test/pass/test_pass_manager.py -k test_pass_manager_does_not_enforce_business_order
# 对应功能实现文件路径: kernel_gen/passes/pass_manager.py
# 对应 spec 文件路径: spec/pass/pass_manager.md
# 对应测试文件路径: test/pass/test_pass_manager.py
def test_pass_manager_does_not_enforce_business_order() -> None:
    order: list[str] = []

    class LoweringPass(Pass):
        name = "lower-nn"

        def run(self: "LoweringPass", target: object) -> object:
            order.append("lower-nn")
            return target

    class BufferPass(Pass):
        name = "buffer-results-to-out-params"

        def run(self: "BufferPass", target: object) -> object:
            order.append("buffer-results-to-out-params")
            return target

    class TilePass(Pass):
        name = "tile-reduce"

        def run(self: "TilePass", target: object) -> object:
            order.append("tile-reduce")
            return target

    class HoistPass(Pass):
        name = "symbol-loop-hoist"

        def run(self: "HoistPass", target: object) -> object:
            order.append("symbol-loop-hoist")
            return target

    class DmaPass(Pass):
        name = "lower-dma-memory-hierarchy"

        def run(self: "DmaPass", target: object) -> object:
            order.append("lower-dma-memory-hierarchy")
            return target

    pm = PassManager(name="business-order-is-caller-owned")
    pm.add_pass(BufferPass())
    pm.add_pass(TilePass())
    pm.add_pass(HoistPass())
    pm.add_pass(DmaPass())
    pm.add_pass(LoweringPass())

    sentinel = object()
    assert pm.run(sentinel) is sentinel
    assert order == [
        "buffer-results-to-out-params",
        "tile-reduce",
        "symbol-loop-hoist",
        "lower-dma-memory-hierarchy",
        "lower-nn",
    ]
