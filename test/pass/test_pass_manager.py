"""pass_manager tests.

创建者: 李白
最后一次更改: 朽木露琪亚

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

import sys
from pathlib import Path

import importlib
import pytest

from xdsl.dialects.builtin import ModuleOp
from xdsl.passes import ModulePass

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

pass_module = importlib.import_module("kernel_gen.passes.pass_manager")
Pass = pass_module.Pass
PassManager = pass_module.PassManager
pipeline_module = importlib.import_module("kernel_gen.passes.pipeline")
build_default_lowering_pipeline = pipeline_module.build_default_lowering_pipeline
registry_module = importlib.import_module("kernel_gen.passes.registry")
build_registered_pass = registry_module.build_registered_pass
load_builtin_passes = registry_module.load_builtin_passes
_reset_registry_for_test = registry_module._reset_registry_for_test


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
    _reset_registry_for_test()
    try:
        load_builtin_passes()
        pass_obj = build_registered_pass("lower-nn")
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
        _reset_registry_for_test()


# TC-PASS-006
# 创建者: 金铲铲大作战
# 最后一次更改: 朽木露琪亚
# 最近一次运行测试时间: 2026-04-06 09:53:59 +0800
# 最近一次运行成功时间: 2026-04-06 09:53:59 +0800
# 功能说明: 验证默认 lowering pipeline 会固定注册 `DecompassPass -> NnLoweringPass -> BufferResultsToOutParamsPass -> LowerDmaMemoryHierarchyPass`。
# 使用示例: pytest -q test/pass/test_pass_manager.py -k test_pass_manager_builds_default_lowering_pipeline_for_buffer_results_to_out_params
# 对应功能实现文件路径: kernel_gen/passes/pass_manager.py
# 对应 spec 文件路径: spec/pass/pass_manager.md
# 对应测试文件路径: test/pass/test_pass_manager.py
@pytest.mark.nn_lowering
def test_pass_manager_builds_default_lowering_pipeline_for_buffer_results_to_out_params(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    lowering_module = importlib.import_module("kernel_gen.passes.lowering")
    decompose_module = importlib.import_module("kernel_gen.passes.decompass")
    DecompassPass = decompose_module.DecompassPass
    NnLoweringPass = lowering_module.NnLoweringPass
    BufferResultsToOutParamsPass = lowering_module.BufferResultsToOutParamsPass
    LowerDmaMemoryHierarchyPass = lowering_module.LowerDmaMemoryHierarchyPass
    order: list[str] = []

    def _record_decompose(self: object, ctx: object, module: object) -> None:
        order.append("decompass")
        return None

    def _record_lower(self: object, target: object) -> object:
        order.append("lower-nn")
        return target

    def _record_buffer(self: object, ctx: object, module: object) -> None:
        order.append("buffer-results-to-out-params")
        return None

    def _record_dma(self: object, target: object) -> object:
        order.append("lower-dma-memory-hierarchy")
        return target

    monkeypatch.setattr(DecompassPass, "apply", _record_decompose)
    monkeypatch.setattr(NnLoweringPass, "run", _record_lower)
    monkeypatch.setattr(BufferResultsToOutParamsPass, "apply", _record_buffer)
    monkeypatch.setattr(LowerDmaMemoryHierarchyPass, "run", _record_dma)

    pm = build_default_lowering_pipeline()
    sentinel = object()
    assert pm.run(sentinel) is sentinel
    assert order == [
        "decompass",
        "lower-nn",
        "buffer-results-to-out-params",
        "lower-dma-memory-hierarchy",
    ]


# TC-PASS-007
# 创建者: 金铲铲大作战
# 最后一次更改: 朽木露琪亚
# 最近一次运行测试时间: 2026-04-04 00:00:00 +0800
# 最近一次运行成功时间: 2026-04-04 00:00:00 +0800
# 功能说明: 验证 `buffer-results-to-out-params` 放在 `lower-nn` 之前会被显式拒绝。
# 使用示例: pytest -q test/pass/test_pass_manager.py -k test_pass_manager_rejects_buffer_results_to_out_params_before_lowering
# 对应功能实现文件路径: kernel_gen/passes/pass_manager.py
# 对应 spec 文件路径: spec/pass/pass_manager.md
# 对应测试文件路径: test/pass/test_pass_manager.py
@pytest.mark.nn_lowering
def test_pass_manager_rejects_buffer_results_to_out_params_before_lowering() -> None:
    lowering_module = importlib.import_module("kernel_gen.passes.lowering")
    BufferResultsToOutParamsPass = lowering_module.BufferResultsToOutParamsPass
    NnLoweringPass = lowering_module.NnLoweringPass

    pm = PassManager(name="lowering")
    pm.add_pass(BufferResultsToOutParamsPass())
    pm.add_pass(NnLoweringPass())

    with pytest.raises(ValueError, match="lowered IR"):
        pm.run(object())


# TC-PASS-008
# 创建者: 小李飞刀
# 最后一次更改: 朽木露琪亚
# 最近一次运行测试时间: 2026-04-05 00:00:00 +0800
# 最近一次运行成功时间: 2026-04-05 00:00:00 +0800
# 功能说明: 验证 buffer-results-to-out-params 可在 lowering 之后、其他 pass 之前/之后运行。
# 测试目的: 锁定顺序约束仅要求 `lower-nn` 先于 `buffer-results-to-out-params`，允许中间插入其他 pass。
# 使用示例: pytest -q test/pass/test_pass_manager.py -k test_pass_manager_allows_buffer_results_to_out_params_after_lowering_with_intermediate_pass
# 对应功能实现文件路径: kernel_gen/passes/pass_manager.py
# 对应 spec 文件路径: spec/pass/pass_manager.md
# 对应测试文件路径: test/pass/test_pass_manager.py
@pytest.mark.nn_lowering
def test_pass_manager_allows_buffer_results_to_out_params_after_lowering_with_intermediate_pass(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    lowering_module = importlib.import_module("kernel_gen.passes.lowering")
    NnLoweringPass = lowering_module.NnLoweringPass
    BufferResultsToOutParamsPass = lowering_module.BufferResultsToOutParamsPass
    order: list[str] = []

    class NoopPass(Pass):
        name = "noop"

        def run(self: "NoopPass", target: object) -> object:
            order.append("noop")
            return target

    def _record_lower(self: object, target: object) -> object:
        order.append("lower-nn")
        return target

    def _record_buffer(self: object, ctx: object, module: object) -> None:
        order.append("buffer-results-to-out-params")
        return None

    monkeypatch.setattr(NnLoweringPass, "run", _record_lower)
    monkeypatch.setattr(BufferResultsToOutParamsPass, "apply", _record_buffer)

    pm = PassManager(name="lowering")
    pm.add_pass(NnLoweringPass())
    pm.add_pass(NoopPass())
    pm.add_pass(BufferResultsToOutParamsPass())

    sentinel = object()
    assert pm.run(sentinel) is sentinel
    assert order == ["lower-nn", "noop", "buffer-results-to-out-params"]


# TC-PASS-009
# 创建者: 金铲铲大作战
# 最后一次更改: 朽木露琪亚
# 最近一次运行测试时间: 2026-04-07 13:50:00 +0800
# 最近一次运行成功时间: 2026-04-07 13:50:00 +0800
# 功能说明: 验证 `TilePass` 为显式开启 pass，默认 lowering builder 不会自动插入。
# 测试目的: 锁定默认 `build_default_lowering_pipeline()` 的 pass 集合只包含 decompose + lowering + out-params + dma hierarchy。
# 使用示例: pytest -q test/pass/test_pass_manager.py -k test_tile_pipeline_requires_explicit_enable
# 对应功能实现文件路径: kernel_gen/passes/pass_manager.py
# 对应 spec 文件路径: spec/pass/pass_manager.md
# 对应测试文件路径: test/pass/test_pass_manager.py
@pytest.mark.nn_lowering
def test_tile_pipeline_requires_explicit_enable() -> None:
    pm = build_default_lowering_pipeline()
    pass_names = [item.name for item in pm._passes]  # noqa: SLF001 - test asserts pipeline boundary
    assert pass_names == [
        "decompass",
        "lower-nn",
        "buffer-results-to-out-params",
        "lower-dma-memory-hierarchy",
    ]
    assert "tile" not in pass_names
    assert "tile-reduce" not in pass_names


# TC-PASS-010
# 创建者: 金铲铲大作战
# 最后一次更改: 朽木露琪亚
# 最近一次运行测试时间: 2026-04-07 13:50:00 +0800
# 最近一次运行成功时间: 2026-04-07 13:50:00 +0800
# 功能说明: 验证显式开启 `TilePass` 时，其顺序必须位于 `LowerDmaMemoryHierarchyPass` 之前。
# 测试目的: 机械锁定推荐 pipeline：`NnLoweringPass -> BufferResultsToOutParamsPass -> TilePass -> LowerDmaMemoryHierarchyPass`。
# 使用示例: pytest -q test/pass/test_pass_manager.py -k test_default_lowering_pipeline_orders_tile_after_out_params
# 对应功能实现文件路径: kernel_gen/passes/pass_manager.py
# 对应 spec 文件路径: spec/pass/pass_manager.md
# 对应测试文件路径: test/pass/test_pass_manager.py
@pytest.mark.nn_lowering
def test_default_lowering_pipeline_orders_tile_after_out_params(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    lowering_module = importlib.import_module("kernel_gen.passes.lowering")
    NnLoweringPass = lowering_module.NnLoweringPass
    BufferResultsToOutParamsPass = lowering_module.BufferResultsToOutParamsPass
    LowerDmaMemoryHierarchyPass = lowering_module.LowerDmaMemoryHierarchyPass
    tile_module = importlib.import_module("kernel_gen.passes.lowering.tile")
    TilePass = tile_module.TilePass
    order: list[str] = []

    def _record_lower(self: object, target: object) -> object:
        order.append("lower-nn")
        return target

    def _record_buffer(self: object, ctx: object, module: object) -> None:
        order.append("buffer-results-to-out-params")
        return None

    def _record_dma(self: object, target: object) -> object:
        order.append("lower-dma-memory-hierarchy")
        return target

    def _record_tile(self: object, target: object) -> object:
        order.append("tile")
        return target

    monkeypatch.setattr(NnLoweringPass, "run", _record_lower)
    monkeypatch.setattr(BufferResultsToOutParamsPass, "apply", _record_buffer)
    monkeypatch.setattr(LowerDmaMemoryHierarchyPass, "run", _record_dma)
    monkeypatch.setattr(TilePass, "run", _record_tile)

    pm = PassManager(name="tile-lowering")
    pm.add_pass(NnLoweringPass())
    pm.add_pass(BufferResultsToOutParamsPass())
    pm.add_pass(TilePass())
    pm.add_pass(LowerDmaMemoryHierarchyPass())

    sentinel = object()
    assert pm.run(sentinel) is sentinel
    assert order == [
        "lower-nn",
        "buffer-results-to-out-params",
        "tile",
        "lower-dma-memory-hierarchy",
    ]


# TC-PASS-010B
# 创建者: 金铲铲大作战
# 最后一次更改: 金铲铲大作战
# 最近一次运行测试时间: 2026-04-21 00:00:00 +0800
# 最近一次运行成功时间: 2026-04-21 00:00:00 +0800
# 功能说明: 验证显式开启 `TileReducePass` 时，其顺序必须位于 `LowerDmaMemoryHierarchyPass` 之前。
# 测试目的: 机械锁定推荐 pipeline：`NnLoweringPass -> BufferResultsToOutParamsPass -> TileReducePass -> LowerDmaMemoryHierarchyPass`。
# 使用示例: pytest -q test/pass/test_pass_manager.py -k test_default_lowering_pipeline_orders_tile_reduce_after_out_params
# 对应功能实现文件路径: kernel_gen/passes/pass_manager.py
# 对应 spec 文件路径: spec/pass/pass_manager.md
# 对应测试文件路径: test/pass/test_pass_manager.py
@pytest.mark.nn_lowering
def test_default_lowering_pipeline_orders_tile_reduce_after_out_params(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    lowering_module = importlib.import_module("kernel_gen.passes.lowering")
    NnLoweringPass = lowering_module.NnLoweringPass
    BufferResultsToOutParamsPass = lowering_module.BufferResultsToOutParamsPass
    LowerDmaMemoryHierarchyPass = lowering_module.LowerDmaMemoryHierarchyPass
    tile_reduce_module = importlib.import_module("kernel_gen.passes.lowering.tile_reduce")
    TileReducePass = tile_reduce_module.TileReducePass
    order: list[str] = []

    def _record_lower(self: object, target: object) -> object:
        order.append("lower-nn")
        return target

    def _record_buffer(self: object, ctx: object, module: object) -> None:
        order.append("buffer-results-to-out-params")
        return None

    def _record_dma(self: object, target: object) -> object:
        order.append("lower-dma-memory-hierarchy")
        return target

    def _record_tile_reduce(self: object, ctx: object, module: object) -> None:
        order.append("tile-reduce")
        return None

    monkeypatch.setattr(NnLoweringPass, "run", _record_lower)
    monkeypatch.setattr(BufferResultsToOutParamsPass, "apply", _record_buffer)
    monkeypatch.setattr(LowerDmaMemoryHierarchyPass, "run", _record_dma)
    monkeypatch.setattr(TileReducePass, "apply", _record_tile_reduce)

    pm = PassManager(name="tile-reduce-lowering")
    pm.add_pass(NnLoweringPass())
    pm.add_pass(BufferResultsToOutParamsPass())
    pm.add_pass(TileReducePass())
    pm.add_pass(LowerDmaMemoryHierarchyPass())

    sentinel = object()
    assert pm.run(sentinel) is sentinel
    assert order == [
        "lower-nn",
        "buffer-results-to-out-params",
        "tile-reduce",
        "lower-dma-memory-hierarchy",
    ]


# TC-PASS-011
# 创建者: 金铲铲大作战
# 最后一次更改: 朽木露琪亚
# 最近一次运行测试时间: 2026-04-07 13:50:00 +0800
# 最近一次运行成功时间: 2026-04-07 13:50:00 +0800
# 功能说明: 验证 tile pipeline 的 `tuner.param` 来源口径为“由 tile pass 在函数体内插入/复用”。
# 测试目的: 锁定 PassManager 端不引入额外前置合同：tile 所需的 `tuner.param` 由 `TilePass.run` 负责物化。
# 使用示例: pytest -q test/pass/test_pass_manager.py -k test_tile_pipeline_materializes_tuner_params_before_codegen
# 对应功能实现文件路径: kernel_gen/passes/pass_manager.py
# 对应 spec 文件路径: spec/pass/pass_manager.md
# 对应测试文件路径: test/pass/test_pass_manager.py
@pytest.mark.nn_lowering
def test_tile_pipeline_materializes_tuner_params_before_codegen(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    lowering_module = importlib.import_module("kernel_gen.passes.lowering")
    NnLoweringPass = lowering_module.NnLoweringPass
    BufferResultsToOutParamsPass = lowering_module.BufferResultsToOutParamsPass
    LowerDmaMemoryHierarchyPass = lowering_module.LowerDmaMemoryHierarchyPass
    tile_module = importlib.import_module("kernel_gen.passes.lowering.tile")
    TilePass = tile_module.TilePass

    def _noop_run(self: object, target: object) -> object:
        return target

    def _noop_apply(self: object, ctx: object, module: object) -> None:
        return None

    def _materialize_tuner_param(self: object, target: object) -> object:
        assert isinstance(target, dict)
        target["tuner.param"] = True
        return target

    monkeypatch.setattr(NnLoweringPass, "run", _noop_run)
    monkeypatch.setattr(BufferResultsToOutParamsPass, "apply", _noop_apply)
    monkeypatch.setattr(TilePass, "run", _materialize_tuner_param)
    monkeypatch.setattr(LowerDmaMemoryHierarchyPass, "run", _noop_run)

    pm = PassManager(name="tile-lowering")
    pm.add_pass(NnLoweringPass())
    pm.add_pass(BufferResultsToOutParamsPass())
    pm.add_pass(TilePass())
    pm.add_pass(LowerDmaMemoryHierarchyPass())

    module = {"tuner.param": False}
    result = pm.run(module)
    assert result is module
    assert module["tuner.param"] is True


# TC-PASS-012
# 创建者: 金铲铲大作战
# 最后一次更改: 朽木露琪亚
# 最近一次运行测试时间: 2026-04-07 13:50:00 +0800
# 最近一次运行成功时间: 2026-04-07 13:50:00 +0800
# 功能说明: 验证错误 tile 顺序会被显式拒绝，并包含固定错误关键字 `TilePassOrderError`。
# 测试目的: 机械锁定 tile 顺序边界，避免错误 pipeline 导致 ABI 双重改写或 DMA hierarchy 口径偏差。
# 使用示例: pytest -q test/pass/test_pass_manager.py -k test_tile_pipeline_rejects_wrong_order
# 对应功能实现文件路径: kernel_gen/passes/pass_manager.py
# 对应 spec 文件路径: spec/pass/pass_manager.md
# 对应测试文件路径: test/pass/test_pass_manager.py
@pytest.mark.nn_lowering
def test_tile_pipeline_rejects_wrong_order() -> None:
    lowering_module = importlib.import_module("kernel_gen.passes.lowering")
    NnLoweringPass = lowering_module.NnLoweringPass
    BufferResultsToOutParamsPass = lowering_module.BufferResultsToOutParamsPass
    tile_module = importlib.import_module("kernel_gen.passes.lowering.tile")
    TilePass = tile_module.TilePass
    tile_reduce_module = importlib.import_module("kernel_gen.passes.lowering.tile_reduce")
    TileReducePass = tile_reduce_module.TileReducePass
    dma_hierarchy_module = importlib.import_module("kernel_gen.passes.lowering.dma_memory_hierarchy")
    LowerDmaMemoryHierarchyPass = dma_hierarchy_module.LowerDmaMemoryHierarchyPass

    pm = PassManager(name="bad-tile-order")
    pm.add_pass(NnLoweringPass())
    pm.add_pass(TilePass())
    pm.add_pass(BufferResultsToOutParamsPass())
    with pytest.raises(ValueError, match="TilePassOrderError"):
        pm.run(object())

    pm = PassManager(name="bad-tile-dma-order")
    pm.add_pass(NnLoweringPass())
    pm.add_pass(BufferResultsToOutParamsPass())
    pm.add_pass(LowerDmaMemoryHierarchyPass())
    pm.add_pass(TilePass())
    with pytest.raises(ValueError, match="TilePassOrderError"):
        pm.run(object())

    pm = PassManager(name="bad-tile-reduce-order")
    pm.add_pass(NnLoweringPass())
    pm.add_pass(TileReducePass())
    pm.add_pass(BufferResultsToOutParamsPass())
    with pytest.raises(ValueError, match="TilePassOrderError"):
        pm.run(object())

    pm = PassManager(name="bad-tile-reduce-dma-order")
    pm.add_pass(NnLoweringPass())
    pm.add_pass(BufferResultsToOutParamsPass())
    pm.add_pass(LowerDmaMemoryHierarchyPass())
    pm.add_pass(TileReducePass())
    with pytest.raises(ValueError, match="TilePassOrderError"):
        pm.run(object())


# TC-PASS-013
# 创建者: 金铲铲大作战
# 最后一次更改: 朽木露琪亚
# 最近一次运行测试时间: 2026-04-07 13:50:00 +0800
# 最近一次运行成功时间: 2026-04-07 13:50:00 +0800
# 功能说明: 验证显式 tile pipeline 不会隐式引入新的“函数抽取阶段”pass，保持单函数合同的 pipeline 组成可审计。
# 测试目的: 锁定显式 tile pipeline 只包含 lowering + out-params + tile + dma hierarchy，不夹带额外 pass。
# 使用示例: pytest -q test/pass/test_pass_manager.py -k test_tile_pipeline_keeps_single_function_contract
# 对应功能实现文件路径: kernel_gen/passes/pass_manager.py
# 对应 spec 文件路径: spec/pass/pass_manager.md
# 对应测试文件路径: test/pass/test_pass_manager.py
@pytest.mark.nn_lowering
def test_tile_pipeline_keeps_single_function_contract() -> None:
    tile_module = importlib.import_module("kernel_gen.passes.lowering.tile")
    TilePass = tile_module.TilePass
    lowering_module = importlib.import_module("kernel_gen.passes.lowering")
    NnLoweringPass = lowering_module.NnLoweringPass
    BufferResultsToOutParamsPass = lowering_module.BufferResultsToOutParamsPass
    LowerDmaMemoryHierarchyPass = lowering_module.LowerDmaMemoryHierarchyPass

    pm = PassManager(name="tile-lowering")
    pm.add_pass(NnLoweringPass())
    pm.add_pass(BufferResultsToOutParamsPass())
    pm.add_pass(TilePass())
    pm.add_pass(LowerDmaMemoryHierarchyPass())
    pass_names = [item.name for item in pm._passes]  # noqa: SLF001 - test asserts pipeline boundary
    assert pass_names == [
        "lower-nn",
        "buffer-results-to-out-params",
        "tile",
        "lower-dma-memory-hierarchy",
    ]


# TC-PASS-013A
# 创建者: 小李飞刀
# 最后一次更改: 小李飞刀
# 功能说明: 验证 tile-analysis / tile-elewise 作为 tile family 可按顺序位于 out-params 与 dma hierarchy 之间。
# 使用示例: pytest -q test/pass/test_pass_manager.py -k test_tile_family_orders_tile_analysis_and_tile_elewise_before_dma_memory_hierarchy
# 对应功能实现文件路径: kernel_gen/passes/pass_manager.py
# 对应 spec 文件路径: spec/pass/pass_manager.md
# 对应测试文件路径: test/pass/test_pass_manager.py
@pytest.mark.nn_lowering
def test_tile_family_orders_tile_analysis_and_tile_elewise_before_dma_memory_hierarchy(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    lowering_module = importlib.import_module("kernel_gen.passes.lowering")
    NnLoweringPass = lowering_module.NnLoweringPass
    BufferResultsToOutParamsPass = lowering_module.BufferResultsToOutParamsPass
    LowerDmaMemoryHierarchyPass = lowering_module.LowerDmaMemoryHierarchyPass
    tile_analysis_module = importlib.import_module("kernel_gen.passes.lowering.tile_analysis")
    TileAnalysisPass = tile_analysis_module.TileAnalysisPass
    tile_elewise_module = importlib.import_module("kernel_gen.passes.lowering.tile_elewise")
    TileElewisePass = tile_elewise_module.TileElewisePass
    order: list[str] = []

    def _record_lower(self: object, target: object) -> object:
        order.append("lower-nn")
        return target

    def _record_buffer(self: object, ctx: object, module: object) -> None:
        order.append("buffer-results-to-out-params")
        return None

    def _record_tile_analysis(self: object, ctx: object, module: object) -> None:
        order.append("tile-analysis")
        return None

    def _record_tile_elewise(self: object, ctx: object, module: object) -> None:
        order.append("tile-elewise")
        return None

    def _record_dma(self: object, target: object) -> object:
        order.append("lower-dma-memory-hierarchy")
        return target

    monkeypatch.setattr(NnLoweringPass, "run", _record_lower)
    monkeypatch.setattr(BufferResultsToOutParamsPass, "apply", _record_buffer)
    monkeypatch.setattr(TileAnalysisPass, "apply", _record_tile_analysis)
    monkeypatch.setattr(TileElewisePass, "apply", _record_tile_elewise)
    monkeypatch.setattr(LowerDmaMemoryHierarchyPass, "run", _record_dma)

    pm = PassManager(name="tile-family")
    pm.add_pass(NnLoweringPass())
    pm.add_pass(BufferResultsToOutParamsPass())
    pm.add_pass(TileAnalysisPass())
    pm.add_pass(TileElewisePass())
    pm.add_pass(LowerDmaMemoryHierarchyPass())

    sentinel = object()
    assert pm.run(sentinel) is sentinel
    assert order == [
        "lower-nn",
        "buffer-results-to-out-params",
        "tile-analysis",
        "tile-elewise",
        "lower-dma-memory-hierarchy",
    ]


# TC-PASS-013B
# 创建者: 小李飞刀
# 最后一次更改: 小李飞刀
# 功能说明: 验证 symbol-loop-hoist 若插在 tile-analysis 与 tile-elewise 之间会被拒绝。
# 使用示例: pytest -q test/pass/test_pass_manager.py -k test_pass_manager_rejects_symbol_loop_hoist_before_tile_elewise
# 对应功能实现文件路径: kernel_gen/passes/pass_manager.py
# 对应 spec 文件路径: spec/pass/pass_manager.md
# 对应测试文件路径: test/pass/test_pass_manager.py
@pytest.mark.nn_lowering
def test_pass_manager_rejects_symbol_loop_hoist_before_tile_elewise() -> None:
    lowering_module = importlib.import_module("kernel_gen.passes.lowering")
    NnLoweringPass = lowering_module.NnLoweringPass
    BufferResultsToOutParamsPass = lowering_module.BufferResultsToOutParamsPass
    tile_analysis_module = importlib.import_module("kernel_gen.passes.lowering.tile_analysis")
    TileAnalysisPass = tile_analysis_module.TileAnalysisPass
    tile_elewise_module = importlib.import_module("kernel_gen.passes.lowering.tile_elewise")
    TileElewisePass = tile_elewise_module.TileElewisePass
    symbol_loop_hoist_module = importlib.import_module("kernel_gen.passes.symbol_loop_hoist")
    SymbolLoopHoistPass = symbol_loop_hoist_module.SymbolLoopHoistPass

    pm = PassManager(name="bad-symbol-loop-hoist-tile-family")
    pm.add_pass(NnLoweringPass())
    pm.add_pass(BufferResultsToOutParamsPass())
    pm.add_pass(TileAnalysisPass())
    pm.add_pass(SymbolLoopHoistPass())
    pm.add_pass(TileElewisePass())
    with pytest.raises(ValueError, match="SymbolLoopHoistRequiresSymbolFor"):
        pm.run(object())


# TC-PASS-014
# 创建者: jcc你莫辜负
# 最后一次更改: 朽木露琪亚
# 最近一次运行测试时间: 2026-04-06 09:53:59 +0800
# 最近一次运行成功时间: 2026-04-06 09:53:59 +0800
# 功能说明: 验证 lower-dma-memory-hierarchy 必须位于 buffer-results-to-out-params 之后，否则显式失败。
# 测试目的: 锁定 dma hierarchy 顺序约束，避免 out-params 合同尚未建立即开始层级搬运。
# 使用示例: pytest -q test/pass/test_pass_manager.py -k test_pass_manager_rejects_dma_memory_hierarchy_before_out_params
# 对应功能实现文件路径: kernel_gen/passes/pass_manager.py
# 对应 spec 文件路径: spec/pass/pass_manager.md
# 对应测试文件路径: test/pass/test_pass_manager.py
@pytest.mark.nn_lowering
def test_pass_manager_rejects_dma_memory_hierarchy_before_out_params() -> None:
    lowering_module = importlib.import_module("kernel_gen.passes.lowering")
    NnLoweringPass = lowering_module.NnLoweringPass
    BufferResultsToOutParamsPass = lowering_module.BufferResultsToOutParamsPass
    LowerDmaMemoryHierarchyPass = lowering_module.LowerDmaMemoryHierarchyPass

    pm = PassManager(name="bad-dma-order")
    pm.add_pass(NnLoweringPass())
    pm.add_pass(LowerDmaMemoryHierarchyPass())
    pm.add_pass(BufferResultsToOutParamsPass())
    with pytest.raises(ValueError, match="DmaMemoryHierarchyOrderError"):
        pm.run(object())

    pm = PassManager(name="missing-out-params")
    pm.add_pass(NnLoweringPass())
    pm.add_pass(LowerDmaMemoryHierarchyPass())
    with pytest.raises(ValueError, match="DmaMemoryHierarchyOrderError"):
        pm.run(object())


# TC-PASS-015
# 创建者: 朽木露琪亚
# 最后一次更改: 朽木露琪亚
# 最近一次运行测试时间: 2026-04-07 13:50:00 +0800
# 最近一次运行成功时间: 2026-04-07 13:50:00 +0800
# 功能说明: 验证显式启用 symbol-loop-hoist 但缺少 tile family 时保持 no-op。
# 使用示例: pytest -q test/pass/test_pass_manager.py -k test_pass_manager_allows_symbol_loop_hoist_without_tile
# 对应功能实现文件路径: kernel_gen/passes/pass_manager.py
# 对应 spec 文件路径: spec/pass/pass_manager.md
# 对应测试文件路径: test/pass/test_pass_manager.py
@pytest.mark.nn_lowering
def test_pass_manager_allows_symbol_loop_hoist_without_tile() -> None:
    lowering_module = importlib.import_module("kernel_gen.passes.lowering")
    NnLoweringPass = lowering_module.NnLoweringPass
    BufferResultsToOutParamsPass = lowering_module.BufferResultsToOutParamsPass
    LowerDmaMemoryHierarchyPass = lowering_module.LowerDmaMemoryHierarchyPass

    order: list[str] = []

    class SymbolLoopHoistPass(Pass):
        name = "symbol-loop-hoist"

        def run(self: "SymbolLoopHoistPass", target: object) -> object:
            order.append("symbol-loop-hoist")
            return target

    class _RecordLoweringPass(Pass):
        name = "lower-nn"

        def run(self: "_RecordLoweringPass", target: object) -> object:
            order.append("lower-nn")
            return target

    class _RecordBufferPass(Pass):
        name = "buffer-results-to-out-params"

        def run(self: "_RecordBufferPass", target: object) -> object:
            order.append("buffer-results-to-out-params")
            return target

    pm = PassManager(name="missing-tile")
    pm.add_pass(_RecordLoweringPass())
    pm.add_pass(_RecordBufferPass())
    pm.add_pass(SymbolLoopHoistPass())

    sentinel = object()
    assert pm.run(sentinel) is sentinel
    assert order == ["lower-nn", "buffer-results-to-out-params", "symbol-loop-hoist"]


# TC-PASS-016
# 创建者: 朽木露琪亚
# 最后一次更改: 朽木露琪亚
# 最近一次运行测试时间: 2026-04-07 13:50:00 +0800
# 最近一次运行成功时间: 2026-04-07 13:50:00 +0800
# 功能说明: 验证 symbol-loop-hoist 必须位于 tile 之后，否则显式失败。
# 使用示例: pytest -q test/pass/test_pass_manager.py -k test_pass_manager_rejects_symbol_loop_hoist_before_tile
# 对应功能实现文件路径: kernel_gen/passes/pass_manager.py
# 对应 spec 文件路径: spec/pass/pass_manager.md
# 对应测试文件路径: test/pass/test_pass_manager.py
@pytest.mark.nn_lowering
def test_pass_manager_rejects_symbol_loop_hoist_before_tile() -> None:
    lowering_module = importlib.import_module("kernel_gen.passes.lowering")
    NnLoweringPass = lowering_module.NnLoweringPass
    BufferResultsToOutParamsPass = lowering_module.BufferResultsToOutParamsPass
    dma_hierarchy_module = importlib.import_module("kernel_gen.passes.lowering.dma_memory_hierarchy")
    LowerDmaMemoryHierarchyPass = dma_hierarchy_module.LowerDmaMemoryHierarchyPass
    tile_module = importlib.import_module("kernel_gen.passes.lowering.tile")
    TilePass = tile_module.TilePass

    class SymbolLoopHoistPass(Pass):
        name = "symbol-loop-hoist"

        def run(self: "SymbolLoopHoistPass", target: object) -> object:
            return target

    pm = PassManager(name="bad-symbol-loop-hoist-order")
    pm.add_pass(NnLoweringPass())
    pm.add_pass(BufferResultsToOutParamsPass())
    pm.add_pass(SymbolLoopHoistPass())
    pm.add_pass(TilePass())
    pm.add_pass(LowerDmaMemoryHierarchyPass())
    with pytest.raises(ValueError, match="SymbolLoopHoistRequiresSymbolFor"):
        pm.run(object())


# TC-PASS-016A
# 创建者: 金铲铲大作战
# 最后一次更改: 金铲铲大作战
# 最近一次运行测试时间: 2026-04-21 00:00:00 +0800
# 最近一次运行成功时间: 2026-04-21 00:00:00 +0800
# 功能说明: 验证 symbol-loop-hoist 必须位于 tile-reduce 之后，否则显式失败。
# 使用示例: pytest -q test/pass/test_pass_manager.py -k test_pass_manager_rejects_symbol_loop_hoist_before_tile_reduce
# 对应功能实现文件路径: kernel_gen/passes/pass_manager.py
# 对应 spec 文件路径: spec/pass/pass_manager.md
# 对应测试文件路径: test/pass/test_pass_manager.py
@pytest.mark.nn_lowering
def test_pass_manager_rejects_symbol_loop_hoist_before_tile_reduce() -> None:
    lowering_module = importlib.import_module("kernel_gen.passes.lowering")
    NnLoweringPass = lowering_module.NnLoweringPass
    BufferResultsToOutParamsPass = lowering_module.BufferResultsToOutParamsPass
    dma_hierarchy_module = importlib.import_module("kernel_gen.passes.lowering.dma_memory_hierarchy")
    LowerDmaMemoryHierarchyPass = dma_hierarchy_module.LowerDmaMemoryHierarchyPass
    tile_reduce_module = importlib.import_module("kernel_gen.passes.lowering.tile_reduce")
    TileReducePass = tile_reduce_module.TileReducePass

    class SymbolLoopHoistPass(Pass):
        name = "symbol-loop-hoist"

        def run(self: "SymbolLoopHoistPass", target: object) -> object:
            return target

    pm = PassManager(name="bad-symbol-loop-hoist-reduce-order")
    pm.add_pass(NnLoweringPass())
    pm.add_pass(BufferResultsToOutParamsPass())
    pm.add_pass(SymbolLoopHoistPass())
    pm.add_pass(TileReducePass())
    pm.add_pass(LowerDmaMemoryHierarchyPass())
    with pytest.raises(ValueError, match="SymbolLoopHoistRequiresSymbolFor: symbol-loop-hoist must run after tile-reduce"):
        pm.run(object())


# TC-PASS-017
# 创建者: 朽木露琪亚
# 最后一次更改: 朽木露琪亚
# 最近一次运行测试时间: 2026-04-07 13:50:00 +0800
# 最近一次运行成功时间: 2026-04-07 13:50:00 +0800
# 功能说明: 验证 symbol-loop-hoist 必须位于 lower-dma-memory-hierarchy 之前，否则显式失败。
# 使用示例: pytest -q test/pass/test_pass_manager.py -k test_pass_manager_rejects_symbol_loop_hoist_after_dma_memory_hierarchy
# 对应功能实现文件路径: kernel_gen/passes/pass_manager.py
# 对应 spec 文件路径: spec/pass/pass_manager.md
# 对应测试文件路径: test/pass/test_pass_manager.py
@pytest.mark.nn_lowering
def test_pass_manager_rejects_symbol_loop_hoist_after_dma_memory_hierarchy() -> None:
    lowering_module = importlib.import_module("kernel_gen.passes.lowering")
    NnLoweringPass = lowering_module.NnLoweringPass
    BufferResultsToOutParamsPass = lowering_module.BufferResultsToOutParamsPass
    dma_hierarchy_module = importlib.import_module("kernel_gen.passes.lowering.dma_memory_hierarchy")
    LowerDmaMemoryHierarchyPass = dma_hierarchy_module.LowerDmaMemoryHierarchyPass
    tile_module = importlib.import_module("kernel_gen.passes.lowering.tile")
    TilePass = tile_module.TilePass

    class SymbolLoopHoistPass(Pass):
        name = "symbol-loop-hoist"

        def run(self: "SymbolLoopHoistPass", target: object) -> object:
            return target

    pm = PassManager(name="bad-symbol-loop-hoist-dma-order")
    pm.add_pass(NnLoweringPass())
    pm.add_pass(BufferResultsToOutParamsPass())
    pm.add_pass(TilePass())
    pm.add_pass(LowerDmaMemoryHierarchyPass())
    pm.add_pass(SymbolLoopHoistPass())
    with pytest.raises(ValueError, match="SymbolLoopHoistRequiresSymbolFor"):
        pm.run(object())


# TC-PASS-017A
# 创建者: 金铲铲大作战
# 最后一次更改: 金铲铲大作战
# 最近一次运行测试时间: 2026-04-21 00:00:00 +0800
# 最近一次运行成功时间: 2026-04-21 00:00:00 +0800
# 功能说明: 验证 symbol-loop-hoist 在 tile-reduce 之后、lower-dma-memory-hierarchy 之前可以正常排队。
# 使用示例: pytest -q test/pass/test_pass_manager.py -k test_pass_manager_allows_symbol_loop_hoist_after_tile_reduce
# 对应功能实现文件路径: kernel_gen/passes/pass_manager.py
# 对应 spec 文件路径: spec/pass/pass_manager.md
# 对应测试文件路径: test/pass/test_pass_manager.py
@pytest.mark.nn_lowering
def test_pass_manager_allows_symbol_loop_hoist_after_tile_reduce(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    lowering_module = importlib.import_module("kernel_gen.passes.lowering")
    NnLoweringPass = lowering_module.NnLoweringPass
    BufferResultsToOutParamsPass = lowering_module.BufferResultsToOutParamsPass
    dma_hierarchy_module = importlib.import_module("kernel_gen.passes.lowering.dma_memory_hierarchy")
    LowerDmaMemoryHierarchyPass = dma_hierarchy_module.LowerDmaMemoryHierarchyPass
    tile_reduce_module = importlib.import_module("kernel_gen.passes.lowering.tile_reduce")
    TileReducePass = tile_reduce_module.TileReducePass

    class SymbolLoopHoistPass(Pass):
        name = "symbol-loop-hoist"

        def run(self: "SymbolLoopHoistPass", target: object) -> object:
            order.append("symbol-loop-hoist")
            return target

    order: list[str] = []

    def _record_lower(self: object, target: object) -> object:
        order.append("lower-nn")
        return target

    def _record_buffer(self: object, ctx: object, module: object) -> None:
        order.append("buffer-results-to-out-params")
        return None

    def _record_dma(self: object, target: object) -> object:
        order.append("lower-dma-memory-hierarchy")
        return target

    def _record_tile_reduce(self: object, ctx: object, module: object) -> None:
        order.append("tile-reduce")
        return None

    monkeypatch.setattr(NnLoweringPass, "run", _record_lower)
    monkeypatch.setattr(BufferResultsToOutParamsPass, "apply", _record_buffer)
    monkeypatch.setattr(LowerDmaMemoryHierarchyPass, "run", _record_dma)
    monkeypatch.setattr(TileReducePass, "apply", _record_tile_reduce)

    pm = PassManager(name="symbol-loop-hoist-after-tile-reduce")
    pm.add_pass(NnLoweringPass())
    pm.add_pass(BufferResultsToOutParamsPass())
    pm.add_pass(TileReducePass())
    pm.add_pass(SymbolLoopHoistPass())
    pm.add_pass(LowerDmaMemoryHierarchyPass())

    sentinel = object()
    assert pm.run(sentinel) is sentinel
    assert order == [
        "lower-nn",
        "buffer-results-to-out-params",
        "tile-reduce",
        "symbol-loop-hoist",
        "lower-dma-memory-hierarchy",
    ]


# TC-PASS-018
# 创建者: jcc你莫辜负
# 最后一次更改: 朽木露琪亚
# 最近一次运行测试时间: 2026-04-08 10:19:36 +0800
# 最近一次运行成功时间: 2026-04-08 10:19:36 +0800
# 功能说明: 验证 lowering 管理器可前置 decompass，并与后续 pass 顺序协同。
# 测试目的: 保障 decompass 能与 lower-nn 与 buffer-results-to-out-params 正常串联。
# 使用示例: pytest -q test/pass/test_pass_manager.py -k test_pass_manager_allows_decompass_before_lowering
# 对应功能实现文件路径: kernel_gen/passes/pass_manager.py
# 对应 spec 文件路径: spec/pass/pass_manager.md
# 对应测试文件路径: test/pass/test_pass_manager.py
@pytest.mark.nn_lowering
def test_pass_manager_allows_decompass_before_lowering() -> None:
    class DecomposeSoftmaxPass(Pass):
        name = "decompass"

        def run(self: "DecomposeSoftmaxPass", target: object) -> object:
            order.append("decompass")
            return target

    class NnLoweringPass(Pass):
        name = "lower-nn"

        def run(self: "NnLoweringPass", target: object) -> object:
            order.append("lower-nn")
            return target

    class BufferResultsToOutParamsPass(Pass):
        name = "buffer-results-to-out-params"

        def run(self: "BufferResultsToOutParamsPass", target: object) -> object:
            order.append("buffer-results-to-out-params")
            return target

    order: list[str] = []
    pm = PassManager(name="lowering-with-softmax")
    pm.add_pass(DecomposeSoftmaxPass())
    pm.add_pass(NnLoweringPass())
    pm.add_pass(BufferResultsToOutParamsPass())

    sentinel = object()
    assert pm.run(sentinel) is sentinel
    assert order == ["decompass", "lower-nn", "buffer-results-to-out-params"]
