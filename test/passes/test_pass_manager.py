"""pass_manager tests.


功能说明:
- 覆盖 kernel_gen/passes/pass_manager.py 的 Pass 管理行为。

当前覆盖率信息:
- 当前覆盖率: `100%`（语句覆盖 `100%`，分支覆盖 `100%`）。
- 达标判定: 已达到 `95%` 覆盖率达标线。
- 本文件覆盖 `TC-PASS-001..017`，并补充 `Pass` 缺少 `name` 属性的非法输入分支。

覆盖率命令:
- `pytest -q --cov=kernel_gen.passes.pass_manager --cov-branch --cov-report=term-missing test/passes/test_pass_manager.py`

使用示例:
- pytest -q test/passes/test_pass_manager.py

关联文件:
- 功能实现: kernel_gen/passes/pass_manager.py
- Spec 文档: spec/pass/pass_manager.md
- 测试文件: test/passes/test_pass_manager.py
"""

from __future__ import annotations

import contextlib
import sys
from pathlib import Path

import importlib
import pytest

from xdsl.context import Context
from xdsl.dialects import func
from xdsl.dialects.builtin import FunctionType, ModuleOp
from xdsl.ir import Block, Region
from xdsl.parser import Parser
from xdsl.passes import ModulePass

from kernel_gen.core.config import reset_config, set_dump_dir
from kernel_gen.core.context import build_default_context

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


def _parse_module(source_ir: str) -> ModuleOp:
    """解析测试用完整 module。

    功能说明:
    - 使用公开默认 context 构造含项目 dialect 的 module。

    使用示例:
    - module = _parse_module("builtin.module {}")
    """

    parsed = Parser(build_default_context(), source_ir).parse_module()
    assert isinstance(parsed, ModuleOp)
    return parsed


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
# 功能说明: 验证单 Pass 正常执行。
# 使用示例: pytest -q test/passes/test_pass_manager.py -k test_pass_manager_single_pass
# 对应功能实现文件路径: kernel_gen/passes/pass_manager.py
# 对应 spec 文件路径: spec/pass/pass_manager.md
# 对应测试文件路径: test/passes/test_pass_manager.py
def test_pass_manager_single_pass() -> None:
    order: list[str] = []

    class AddOnePass(Pass):
        name = "add-one"

        def apply(self: "AddOnePass", ctx: Context, target: ModuleOp) -> None:
            _ = ctx
            assert isinstance(target, ModuleOp)
            order.append("add-one")

    pm = PassManager(name="opt")
    pm.add_pass(AddOnePass())
    module = ModuleOp([])
    assert pm.run(module) is module
    assert order == ["add-one"]


# TC-PASS-002
# 功能说明: 验证多 Pass 顺序执行。
# 使用示例: pytest -q test/passes/test_pass_manager.py -k test_pass_manager_multiple_passes_order
# 对应功能实现文件路径: kernel_gen/passes/pass_manager.py
# 对应 spec 文件路径: spec/pass/pass_manager.md
# 对应测试文件路径: test/passes/test_pass_manager.py
def test_pass_manager_multiple_passes_order() -> None:
    order: list[str] = []

    class AddOnePass(Pass):
        name = "add-one"

        def apply(self: "AddOnePass", ctx: Context, target: ModuleOp) -> None:
            _ = ctx
            assert isinstance(target, ModuleOp)
            order.append("add-one")

    class TimesTwoPass(Pass):
        name = "times-two"

        def apply(self: "TimesTwoPass", ctx: Context, target: ModuleOp) -> None:
            _ = ctx
            assert isinstance(target, ModuleOp)
            order.append("times-two")

    pm = PassManager()
    pm.extend([AddOnePass(), TimesTwoPass()])
    module = ModuleOp([])
    assert pm.run(module) is module
    assert order == ["add-one", "times-two"]


# TC-PASS-003
# 功能说明: 验证空管理器返回原输入。
# 使用示例: pytest -q test/passes/test_pass_manager.py -k test_pass_manager_empty_returns_input
# 对应功能实现文件路径: kernel_gen/passes/pass_manager.py
# 对应 spec 文件路径: spec/pass/pass_manager.md
# 对应测试文件路径: test/passes/test_pass_manager.py
def test_pass_manager_empty_returns_input() -> None:
    pm = PassManager()
    module = ModuleOp([])
    assert pm.run(module) is module


# TC-PASS-003A
# 功能说明: 验证 PassManager dump_dir 会写入初始 IR 与逐 pass 后 IR。
# 使用示例: pytest -q test/passes/test_pass_manager.py -k test_pass_manager_dump_dir_writes_pass_ir
# 对应功能实现文件路径: kernel_gen/passes/pass_manager.py
# 对应 spec 文件路径: spec/pass/pass_manager.md
# 对应测试文件路径: test/passes/test_pass_manager.py
def test_pass_manager_dump_dir_writes_pass_ir(tmp_path: Path) -> None:
    class NoOpPass(Pass):
        name = "no-op"

        def apply(self: "NoOpPass", ctx: Context, target: ModuleOp) -> None:
            _ = ctx
            assert isinstance(target, ModuleOp)

    pm = PassManager(name="dump-pipeline")
    pm.add_pass(NoOpPass())
    module = _parse_module(
        """
builtin.module {
  func.func @dump_alias(%n : !symbol.int<#symbol.expr<N>>) {
    %zero = "symbol.const"() {value = #builtin.int<0>} : () -> !symbol.int<#symbol.expr<0>>
    func.return
  }
}
"""
    )

    try:
        set_dump_dir(tmp_path)
        assert pm.run(module) is module
    finally:
        reset_config()

    first_ir = (tmp_path / "01-first-ir.mlir").read_text(encoding="utf-8")
    pass_ir = (tmp_path / "02-no-op.mlir").read_text(encoding="utf-8")
    assert "builtin.module" in first_ir
    assert "#C0 = #symbol.expr<0>" in first_ir
    assert "#S_N = #symbol.expr<N>" in first_ir
    assert "#symbol.expr<" not in first_ir.split("builtin.module", 1)[1]
    assert pass_ir.splitlines()[0] == "no-op"
    assert "builtin.module" in pass_ir
    assert "#S_N = #symbol.expr<N>" in pass_ir
    assert "#symbol.expr<" not in pass_ir.split("builtin.module", 1)[1]


# TC-PASS-003B
# 功能说明: 验证 pass 默认开启 fold + DCE，PassManager 在 pass 后折叠 symbol 算术并删除死 symbol op。
# 使用示例: pytest -q test/passes/test_pass_manager.py -k test_pass_manager_folds_symbol_ops_by_default
# 对应功能实现文件路径: kernel_gen/passes/pass_manager.py
# 对应 spec 文件路径: spec/pass/pass_manager.md
# 对应测试文件路径: test/passes/test_pass_manager.py
def test_pass_manager_folds_symbol_ops_by_default() -> None:
    from kernel_gen.dialect.symbol import SymbolAddOp, SymbolConstOp, SymbolValueType

    class NoOpPass(Pass):
        name = "no-op"

        def apply(self: "NoOpPass", ctx: Context, target: ModuleOp) -> None:
            _ = ctx
            assert isinstance(target, ModuleOp)

    lhs = SymbolConstOp(2)
    rhs = SymbolConstOp(3)
    add = SymbolAddOp(lhs.result, rhs.result, SymbolValueType.from_expr("5"))
    dead_lhs = SymbolConstOp(7)
    dead_rhs = SymbolConstOp(8)
    dead_add = SymbolAddOp(dead_lhs.result, dead_rhs.result, SymbolValueType.from_expr("15"))
    block = Block()
    block.add_ops([lhs, rhs, add, dead_lhs, dead_rhs, dead_add, func.ReturnOp(add.result)])
    func_op = func.FuncOp(
        "fold_case",
        FunctionType.from_lists([], [SymbolValueType.from_expr("5")]),
        Region(block),
    )
    module = ModuleOp([func_op])

    pm = PassManager(name="fold-pipeline")
    pm.add_pass(NoOpPass())
    result = pm.run(module)

    assert result is module
    module_text = str(module)
    assert "symbol.add" not in module_text
    assert "symbol.const 5 : !symbol.int<#symbol.expr<5>>" in module_text
    assert "symbol.const 2 : !symbol.int<#symbol.expr<2>>" not in module_text
    assert "symbol.const 3 : !symbol.int<#symbol.expr<3>>" not in module_text
    assert "symbol.const 7 : !symbol.int<#symbol.expr<7>>" not in module_text
    assert "symbol.const 8 : !symbol.int<#symbol.expr<8>>" not in module_text
    assert "symbol.const 15 : !symbol.int<#symbol.expr<15>>" not in module_text


# TC-PASS-003B1
# 功能说明: 验证 pass 默认 fold 可把静态 memory shape 查询折叠为 symbol.const。
# 使用示例: pytest -q test/passes/test_pass_manager.py -k test_pass_manager_folds_static_get_dim_by_default
# 对应功能实现文件路径: kernel_gen/passes/pass_manager.py
# 对应 spec 文件路径: spec/pass/pass_manager.md
# 对应测试文件路径: test/passes/test_pass_manager.py
def test_pass_manager_folds_static_get_dim_by_default() -> None:
    from xdsl.dialects.builtin import ArrayAttr, IntAttr, StringAttr, i32

    from kernel_gen.dialect.nn import NnMemorySpaceAttr, NnMemoryType
    from kernel_gen.dialect.symbol import SymbolExprAttr, SymbolGetDimOp, SymbolValueType

    class NoOpPass(Pass):
        name = "no-op"

        def apply(self: "NoOpPass", ctx: Context, target: ModuleOp) -> None:
            _ = ctx
            assert isinstance(target, ModuleOp)

    memory_type = NnMemoryType(
        ArrayAttr([SymbolExprAttr.from_expr("12"), SymbolExprAttr.from_expr("N")]),
        ArrayAttr([SymbolExprAttr.from_expr("32"), SymbolExprAttr.from_expr("1")]),
        i32,
        NnMemorySpaceAttr(StringAttr("global")),
    )
    block = Block(arg_types=[memory_type])
    get_dim = SymbolGetDimOp(block.args[0], 0)
    block.add_ops([get_dim, func.ReturnOp(get_dim.result)])
    func_op = func.FuncOp(
        "fold_static_get_dim_case",
        FunctionType.from_lists([memory_type], [SymbolValueType.from_expr("12")]),
        Region(block),
    )
    module = ModuleOp([func_op])

    pm = PassManager(name="fold-memory-query-pipeline")
    pm.add_pass(NoOpPass())
    result = pm.run(module)

    assert result is module
    module_text = str(module)
    assert "symbol.get_dim" not in module_text
    assert "symbol.const 12 : !symbol.int<#symbol.expr<12>>" in module_text


# TC-PASS-003C
# 功能说明: 验证 pass 可通过 `fold=False` 关闭默认 fold。
# 使用示例: pytest -q test/passes/test_pass_manager.py -k test_pass_manager_fold_can_be_disabled_per_pass
# 对应功能实现文件路径: kernel_gen/passes/pass_manager.py
# 对应 spec 文件路径: spec/pass/pass_manager.md
# 对应测试文件路径: test/passes/test_pass_manager.py
def test_pass_manager_fold_can_be_disabled_per_pass() -> None:
    from kernel_gen.dialect.symbol import SymbolAddOp, SymbolConstOp, SymbolValueType

    class NoOpPass(Pass):
        name = "no-op"

        def apply(self: "NoOpPass", ctx: Context, target: ModuleOp) -> None:
            _ = ctx
            assert isinstance(target, ModuleOp)

    lhs = SymbolConstOp(2)
    rhs = SymbolConstOp(3)
    add = SymbolAddOp(lhs.result, rhs.result, SymbolValueType.from_expr("5"))
    module = ModuleOp([lhs, rhs, add])

    pm = PassManager(name="fold-disabled-pipeline")
    pm.add_pass(NoOpPass(fold=False))
    result = pm.run(module)

    assert result is module
    assert "symbol.add" in str(module)


# TC-PASS-004
# 功能说明: 验证非法 Pass 类型报错。
# 使用示例: pytest -q test/passes/test_pass_manager.py -k test_pass_manager_invalid_pass_type
# 对应功能实现文件路径: kernel_gen/passes/pass_manager.py
# 对应 spec 文件路径: spec/pass/pass_manager.md
# 对应测试文件路径: test/passes/test_pass_manager.py
def test_pass_manager_invalid_pass_type() -> None:
    pm = PassManager()
    with pytest.raises(TypeError):
        pm.add_pass("not-a-pass")  # type: ignore[arg-type]

    with pytest.raises(TypeError):
        pm.extend([object()])  # type: ignore[arg-type]

    class MissingNamePass:
        def apply(self: "MissingNamePass", ctx: Context, target: ModuleOp) -> None:
            _ = ctx
            _ = target

    with pytest.raises(TypeError):
        pm.add_pass(MissingNamePass())  # type: ignore[arg-type]

    class BadNamePass(Pass):
        name = 123

        def apply(self: "BadNamePass", ctx: Context, target: ModuleOp) -> None:
            _ = ctx
            _ = target

    with pytest.raises(TypeError):
        pm.add_pass(BadNamePass())


# TC-PASS-005
# 功能说明: 验证 Pass 异常向上抛出。
# 使用示例: pytest -q test/passes/test_pass_manager.py -k test_pass_manager_exception_propagation
# 对应功能实现文件路径: kernel_gen/passes/pass_manager.py
# 对应 spec 文件路径: spec/pass/pass_manager.md
# 对应测试文件路径: test/passes/test_pass_manager.py
def test_pass_manager_exception_propagation() -> None:
    class FailPass(Pass):
        name = "fail-pass"

        def apply(self: "FailPass", ctx: Context, target: ModuleOp) -> None:
            _ = ctx
            _ = target
            raise ValueError("boom")

    pm = PassManager()
    pm.add_pass(FailPass())
    with pytest.raises(ValueError):
        _ = pm.run(ModuleOp([]))


# TC-PASS-005A
# 功能说明: 验证 ModulePass 仅实现 apply(...) 时，PassManager 仍可在 builtin.module 目标上执行。
# 使用示例: pytest -q test/passes/test_pass_manager.py -k test_pass_manager_module_pass_apply_only
# 对应功能实现文件路径: kernel_gen/passes/pass_manager.py
# 对应 spec 文件路径: spec/pass/pass_manager.md
# 对应测试文件路径: test/passes/test_pass_manager.py
def test_pass_manager_module_pass_apply_only() -> None:
    order: list[str] = []

    class ApplyOnlyPass(ModulePass):
        name = "apply-only"

        def apply(self, ctx: Context, op: ModuleOp) -> None:
            _ = ctx
            order.append("apply-only")
            assert isinstance(op, ModuleOp)

    pm = PassManager(name="module-pass")
    pm.add_pass(ApplyOnlyPass())
    module = ModuleOp([])
    assert pm.run(module) is module
    assert order == ["apply-only"]


# TC-PASS-005B
# 功能说明: 验证 registry 构造出的 lower-nn 可继续由 PassManager 执行。
# 使用示例: pytest -q test/passes/test_pass_manager.py -k test_pass_manager_runs_registered_lower_nn
# 对应功能实现文件路径: kernel_gen/passes/pass_manager.py
# 对应 spec 文件路径: spec/pass/pass_manager.md
# 对应测试文件路径: test/passes/test_pass_manager.py
def test_pass_manager_runs_registered_lower_nn(monkeypatch: pytest.MonkeyPatch) -> None:
    registry_module = _reload_registry_module()
    try:
        registry_module.load_builtin_passes()
        pass_obj = registry_module.build_registered_pass("lower-nn")
        order: list[str] = []

        def _record_apply(self: ModulePass, ctx: Context, target: ModuleOp) -> None:
            _ = ctx
            order.append(getattr(self, "name"))
            assert isinstance(target, ModuleOp)

        monkeypatch.setattr(type(pass_obj), "apply", _record_apply)

        pm = PassManager(name="registry-lower-nn")
        pm.add_pass(pass_obj)
        module = ModuleOp([])

        assert pm.run(module) is module
        assert order == ["lower-nn"]
    finally:
        _reload_registry_module()


# TC-PASS-005C
# 功能说明: 验证 pass manager caller 当前冻结的 surviving import matrix。
# 使用示例: pytest -q test/passes/test_pass_manager.py -k test_pass_manager_surviving_import_matrix
# 对应功能实现文件路径: kernel_gen/passes/pass_manager.py
# 对应 spec 文件路径: spec/pass/pass_manager.md
# 对应测试文件路径: test/passes/test_pass_manager.py
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
# 功能说明: 验证已退场的旧 pass manager / registry lowering 路径、旧 tile submodule path 与 analysis family 路径稳定失败。
# 使用示例: pytest -q test/passes/test_pass_manager.py -k test_pass_manager_old_lowering_paths_fail_fast
# 对应功能实现文件路径: kernel_gen/passes/pass_manager.py
# 对应 spec 文件路径: spec/pass/pass_manager.md
# 对应测试文件路径: test/passes/test_pass_manager.py
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
# 功能说明: 验证 pass_manager 不再承载旧默认 lowering builder 兼容入口。
# 使用示例: pytest -q test/passes/test_pass_manager.py -k test_pass_manager_has_no_legacy_default_lowering_builder
# 对应功能实现文件路径: kernel_gen/passes/pass_manager.py
# 对应 spec 文件路径: spec/pass/pass_manager.md
# 对应测试文件路径: test/passes/test_pass_manager.py
@pytest.mark.nn_lowering
def test_pass_manager_has_no_legacy_default_lowering_builder() -> None:
    assert not hasattr(pass_module, "build_default_lowering_pass_manager")
    with pytest.raises(ImportError):
        exec("from kernel_gen.passes.pass_manager import build_default_lowering_pass_manager", {})
    pm = build_default_lowering_pipeline()
    assert isinstance(pm, PassManager)
    assert pm.name == "default-lowering"


# TC-PASS-007
# 功能说明: 验证 PassManager 不根据业务 pass 名称施加顺序约束，只按添加顺序执行。
# 使用示例: pytest -q test/passes/test_pass_manager.py -k test_pass_manager_does_not_enforce_business_order
# 对应功能实现文件路径: kernel_gen/passes/pass_manager.py
# 对应 spec 文件路径: spec/pass/pass_manager.md
# 对应测试文件路径: test/passes/test_pass_manager.py
def test_pass_manager_does_not_enforce_business_order() -> None:
    order: list[str] = []

    class LoweringPass(Pass):
        name = "lower-nn"

        def apply(self: "LoweringPass", ctx: Context, target: ModuleOp) -> None:
            _ = ctx
            _ = target
            order.append("lower-nn")

    class BufferPass(Pass):
        name = "buffer-results-to-out-params"

        def apply(self: "BufferPass", ctx: Context, target: ModuleOp) -> None:
            _ = ctx
            _ = target
            order.append("buffer-results-to-out-params")

    class TilePass(Pass):
        name = "tile-reduce"

        def apply(self: "TilePass", ctx: Context, target: ModuleOp) -> None:
            _ = ctx
            _ = target
            order.append("tile-reduce")

    class HoistPass(Pass):
        name = "symbol-loop-hoist"

        def apply(self: "HoistPass", ctx: Context, target: ModuleOp) -> None:
            _ = ctx
            _ = target
            order.append("symbol-loop-hoist")

    class DmaPass(Pass):
        name = "lower-dma-memory-hierarchy"

        def apply(self: "DmaPass", ctx: Context, target: ModuleOp) -> None:
            _ = ctx
            _ = target
            order.append("lower-dma-memory-hierarchy")

    pm = PassManager(name="business-order-is-caller-owned")
    pm.add_pass(BufferPass())
    pm.add_pass(TilePass())
    pm.add_pass(HoistPass())
    pm.add_pass(DmaPass())
    pm.add_pass(LoweringPass())

    sentinel = ModuleOp([])
    assert pm.run(sentinel) is sentinel
    assert order == [
        "buffer-results-to-out-params",
        "tile-reduce",
        "symbol-loop-hoist",
        "lower-dma-memory-hierarchy",
        "lower-nn",
    ]
