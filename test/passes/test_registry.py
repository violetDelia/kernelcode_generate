"""pass registry tests.


功能说明:
- 覆盖 kernel_gen/passes/registry.py 的 pass/pipeline 注册、查询与错误短语约束。

当前覆盖率信息:
- 当前覆盖率: 未统计（本任务验证未启用 coverage 统计）。
- 达标判定: 待后续补充统计结果。

覆盖率命令:
- `pytest -q --cov=kernel_gen.passes.registry --cov-branch --cov-report=term-missing test/passes/test_registry.py`

使用示例:
- pytest -q test/passes/test_registry.py

关联文件:
- 功能实现: kernel_gen/passes/registry.py
- Spec 文档: spec/pass/registry.md
- 测试文件: test/passes/test_registry.py
"""

from __future__ import annotations

import contextlib
import sys
from pathlib import Path
from types import ModuleType

import importlib
import pytest

from xdsl.context import Context
from xdsl.dialects import func
from xdsl.dialects.builtin import ArrayAttr, FunctionType, ModuleOp, i32
from xdsl.ir import Block, Region
from xdsl.passes import ModulePass
from kernel_gen.core.error import KernelCodeError

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
WORKTREE_FALLBACK_REPO = REPO_ROOT.parent if REPO_ROOT.name.startswith("wt-") else None

registry_module = importlib.import_module("kernel_gen.passes.registry")
register_pass = registry_module.register_pass
register_pipeline = registry_module.register_pipeline
build_registered_pass = registry_module.build_registered_pass
build_registered_pipeline = registry_module.build_registered_pipeline
load_builtin_passes = registry_module.load_builtin_passes
list_registered_passes = registry_module.list_registered_passes
list_registered_pipelines = registry_module.list_registered_pipelines

pass_manager_module = importlib.import_module("kernel_gen.passes.pass_manager")
Pass = pass_manager_module.Pass
PassManager = pass_manager_module.PassManager


def _make_registry_memory_type(
    *,
    shape: tuple[int, int],
    stride: tuple[int, int],
    space: str,
) -> "NnMemoryType":
    """构造 registry 测试用公开 nn.memory type。"""

    from kernel_gen.dialect.nn import NnMemorySpaceAttr, NnMemoryType
    from kernel_gen.dialect.symbol import SymbolExprAttr

    return NnMemoryType(
        ArrayAttr([SymbolExprAttr.from_expr(str(dim)) for dim in shape]),
        ArrayAttr([SymbolExprAttr.from_expr(str(dim)) for dim in stride]),
        i32,
        NnMemorySpaceAttr.from_name(space),
    )


def _build_registry_matmul_module() -> tuple[ModuleOp, "KernelMatmulOp"]:
    """构造 registry apply_op 透传测试使用的 `kernel.matmul` module。"""

    from kernel_gen.dialect.kernel import KernelMatmulOp
    from kernel_gen.dialect.nn import NnMemorySpaceAttr

    out_type = _make_registry_memory_type(shape=(2, 4), stride=(4, 1), space="shared")
    lhs_type = _make_registry_memory_type(shape=(2, 3), stride=(3, 1), space="shared")
    rhs_type = _make_registry_memory_type(shape=(3, 4), stride=(4, 1), space="shared")
    func_type = FunctionType.from_lists([out_type, lhs_type, rhs_type], [])
    block = Block(arg_types=[out_type, lhs_type, rhs_type])
    matmul = KernelMatmulOp(
        block.args[0],
        block.args[1],
        block.args[2],
        NnMemorySpaceAttr.from_name("shared"),
    )
    block.add_ops([matmul, func.ReturnOp()])
    func_op = func.FuncOp("matmul", func_type, Region(block))
    return ModuleOp([func_op]), matmul


def _registry_memory_space(value_type: "NnMemoryType") -> str:
    """读取公开 nn.memory type 的 space 名称。"""

    return value_type.space.space.data


def _bind_registry_api(module: ModuleType) -> None:
    """把 registry 模块的公开 API 重新绑定到当前测试文件。"""

    global registry_module
    global register_pass
    global register_pipeline
    global build_registered_pass
    global build_registered_pipeline
    global load_builtin_passes
    global list_registered_passes
    global list_registered_pipelines

    registry_module = module
    register_pass = module.register_pass
    register_pipeline = module.register_pipeline
    build_registered_pass = module.build_registered_pass
    build_registered_pipeline = module.build_registered_pipeline
    load_builtin_passes = module.load_builtin_passes
    list_registered_passes = module.list_registered_passes
    list_registered_pipelines = module.list_registered_pipelines


def _reload_registry_api() -> None:
    """重新导入 registry 模块并恢复其公开入口状态。"""

    _bind_registry_api(importlib.reload(importlib.import_module("kernel_gen.passes.registry")))


@pytest.fixture(autouse=True)
def _isolate_registry_state() -> None:
    _reload_registry_api()
    yield
    _reload_registry_api()


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


# TC-REGISTRY-001
# 功能说明: 验证重复注册同名 pass 立即失败，且错误短语可机械匹配。
# 使用示例: pytest -q test/passes/test_registry.py -k test_register_pass_duplicate_fails
# 对应功能实现文件路径: kernel_gen/passes/registry.py
# 对应 spec 文件路径: spec/pass/registry.md
# 对应测试文件路径: test/passes/test_registry.py
def test_register_pass_duplicate_fails() -> None:
    @register_pass
    class FirstPass(Pass):
        name = "dup-pass"

        def apply(self: "FirstPass", ctx: Context, target: ModuleOp) -> None:
            _ = ctx
            _ = target

    class SecondPass(Pass):
        name = "dup-pass"

        def apply(self: "SecondPass", ctx: Context, target: ModuleOp) -> None:
            _ = ctx
            _ = target

    with pytest.raises(KernelCodeError, match=r"^PassRegistryError: pass 'dup-pass' is already registered$"):
        register_pass(SecondPass)


# TC-REGISTRY-002
# 功能说明: 验证重复注册同名 pipeline 立即失败，且错误短语可机械匹配。
# 使用示例: pytest -q test/passes/test_registry.py -k test_register_pipeline_duplicate_fails
# 对应功能实现文件路径: kernel_gen/passes/registry.py
# 对应 spec 文件路径: spec/pass/registry.md
# 对应测试文件路径: test/passes/test_registry.py
def test_register_pipeline_duplicate_fails() -> None:
    @register_pipeline("dup-pipeline")
    def build_first() -> PassManager:
        return PassManager(name="first")

    with pytest.raises(KernelCodeError, match=r"^PassRegistryError: pipeline 'dup-pipeline' is already registered$"):

        @register_pipeline("dup-pipeline")
        def build_second() -> PassManager:  # pragma: no cover - should not be reached
            return PassManager(name="second")


# TC-REGISTRY-003
# 功能说明: 验证未知 pass 名称构造时报稳定错误短语。
# 使用示例: pytest -q test/passes/test_registry.py -k test_build_registered_pass_unknown
# 对应功能实现文件路径: kernel_gen/passes/registry.py
# 对应 spec 文件路径: spec/pass/registry.md
# 对应测试文件路径: test/passes/test_registry.py
def test_build_registered_pass_unknown() -> None:
    with pytest.raises(KernelCodeError, match=r"^PassRegistryError: unknown pass 'missing-pass'$"):
        _ = build_registered_pass("missing-pass")


# TC-REGISTRY-004
# 功能说明: 验证不可无参构造的 pass 会报告稳定错误短语。
# 使用示例: pytest -q test/passes/test_registry.py -k test_build_registered_pass_not_constructible
# 对应功能实现文件路径: kernel_gen/passes/registry.py
# 对应 spec 文件路径: spec/pass/registry.md
# 对应测试文件路径: test/passes/test_registry.py
def test_build_registered_pass_not_constructible() -> None:
    @register_pass
    class NeedsArgPass(Pass):
        name = "needs-arg"

        def __init__(self: "NeedsArgPass", value: int) -> None:
            self.value = value

        def apply(self: "NeedsArgPass", ctx: Context, target: ModuleOp) -> None:
            _ = ctx
            _ = target

    with pytest.raises(KernelCodeError, match=r"^PassRegistryError: pass 'needs-arg' is not constructible$"):
        _ = build_registered_pass("needs-arg")


# TC-REGISTRY-005
# 功能说明: 验证未知 pipeline 名称构造时报稳定错误短语。
# 使用示例: pytest -q test/passes/test_registry.py -k test_build_registered_pipeline_unknown
# 对应功能实现文件路径: kernel_gen/passes/registry.py
# 对应 spec 文件路径: spec/pass/registry.md
# 对应测试文件路径: test/passes/test_registry.py
def test_build_registered_pipeline_unknown() -> None:
    with pytest.raises(KernelCodeError, match=r"^PassRegistryError: unknown pipeline 'missing-pipeline'$"):
        _ = build_registered_pipeline("missing-pipeline")


# TC-REGISTRY-006
# 功能说明: 验证 pipeline builder 返回值非法时会报告稳定错误短语。
# 使用示例: pytest -q test/passes/test_registry.py -k test_build_registered_pipeline_must_return_pass_manager
# 对应功能实现文件路径: kernel_gen/passes/registry.py
# 对应 spec 文件路径: spec/pass/registry.md
# 对应测试文件路径: test/passes/test_registry.py
def test_build_registered_pipeline_must_return_pass_manager() -> None:
    @register_pipeline("bad-pipeline")
    def _build_bad_pipeline() -> PassManager:  # type: ignore[return-value]
        return object()

    with pytest.raises(
        KernelCodeError, match=r"^PassRegistryError: pipeline 'bad-pipeline' did not return PassManager$"
    ):
        _ = build_registered_pipeline("bad-pipeline")


# TC-REGISTRY-007
# 功能说明: 验证 list_registered_* 返回值顺序确定且不含重复项。
# 使用示例: pytest -q test/passes/test_registry.py -k test_list_registered_are_sorted
# 对应功能实现文件路径: kernel_gen/passes/registry.py
# 对应 spec 文件路径: spec/pass/registry.md
# 对应测试文件路径: test/passes/test_registry.py
def test_list_registered_are_sorted() -> None:
    @register_pass
    class PassB(Pass):
        name = "b-pass"

        def apply(self: "PassB", ctx: Context, target: ModuleOp) -> None:
            _ = ctx
            _ = target

    @register_pass
    class PassA(Pass):
        name = "a-pass"

        def apply(self: "PassA", ctx: Context, target: ModuleOp) -> None:
            _ = ctx
            _ = target

    @register_pipeline("b-pipeline")
    def _build_b() -> PassManager:
        return PassManager(name="b")

    @register_pipeline("a-pipeline")
    def _build_a() -> PassManager:
        return PassManager(name="a")

    assert list_registered_passes() == ["a-pass", "b-pass"]
    assert list_registered_pipelines() == ["a-pipeline", "b-pipeline"]


# TC-REGISTRY-007A
# 功能说明: 验证内置 pass 加载后可通过稳定名称构造 outline-device-kernel。
# 使用示例: pytest -q test/passes/test_registry.py -k test_build_registered_outline_device_kernel_pass
# 对应功能实现文件路径: kernel_gen/passes/registry.py
# 对应 spec 文件路径: spec/pass/registry.md
# 对应测试文件路径: test/passes/test_registry.py
def test_build_registered_outline_device_kernel_pass() -> None:
    load_builtin_passes()

    pass_obj = build_registered_pass("outline-device-kernel")

    assert pass_obj.name == "outline-device-kernel"
    assert type(pass_obj).__name__ == "OutlineDeviceKernelPass"
    assert isinstance(pass_obj, ModulePass)


# TC-REGISTRY-007A-DMH
# 功能说明: 验证 lower-dma-memory-hierarchy 通过 registry 接收 apply_op 与通用 fold option。
# 使用示例: pytest -q test/passes/test_registry.py -k test_build_registered_dma_memory_hierarchy_apply_op_pass
# 对应功能实现文件路径: kernel_gen/passes/registry.py
# 对应 spec 文件路径: spec/pass/registry.md
# 对应测试文件路径: test/passes/test_registry.py
def test_build_registered_dma_memory_hierarchy_apply_op_pass() -> None:
    load_builtin_passes()
    module, matmul = _build_registry_matmul_module()

    pass_obj = build_registered_pass(
        "lower-dma-memory-hierarchy",
        {"fold": "false", "apply_op": 'matmul{["", "tlm1", "tlm2"]}'},
    )
    pass_obj.apply(Context(), module)
    from kernel_gen.dialect.dma import DmaCopyOp

    assert pass_obj.name == "lower-dma-memory-hierarchy"
    assert isinstance(pass_obj, ModulePass)
    assert pass_obj.fold is False
    assert len([op for op in module.walk() if isinstance(op, DmaCopyOp)]) == 2
    assert _registry_memory_space(matmul.operands[1].type) == "tlm1"
    assert _registry_memory_space(matmul.operands[2].type) == "tlm2"
    module.verify()


# TC-REGISTRY-007A-DMH-ERR
# 功能说明: 验证 lower-dma-memory-hierarchy 的 apply_op 规则错误通过 registry 保留 pass 专属原因。
# 使用示例: pytest -q test/passes/test_registry.py -k test_build_registered_dma_memory_hierarchy_apply_op_error_detail
# 对应功能实现文件路径: kernel_gen/passes/registry.py
# 对应 spec 文件路径: spec/pass/registry.md
# 对应测试文件路径: test/passes/test_registry.py
@pytest.mark.parametrize(
    ("apply_op", "detail"),
    [
        ('add{["", "tlm1", "tlm2"]}', "unsupported"),
        ('matmul{["tlm1", "tlm2"]}', "apply_op"),
        ('matmul{["global", "", ""]}', "apply_op"),
    ],
)
def test_build_registered_dma_memory_hierarchy_apply_op_error_detail(apply_op: str, detail: str) -> None:
    load_builtin_passes()

    with pytest.raises(KernelCodeError) as exc_info:
        build_registered_pass("lower-dma-memory-hierarchy", {"apply_op": apply_op})
    message = str(exc_info.value)
    assert message.startswith("PassRegistryError: pass 'lower-dma-memory-hierarchy' option error: ")
    assert detail in message


# TC-REGISTRY-007A-0
# 功能说明: 验证内置 pass 加载后可通过稳定名称构造 tile-analysis ModulePass。
# 使用示例: pytest -q test/passes/test_registry.py -k test_build_registered_tile_analysis_pass
# 对应功能实现文件路径: kernel_gen/passes/registry.py
# 对应 spec 文件路径: spec/pass/registry.md
# 对应测试文件路径: test/passes/test_registry.py
def test_build_registered_tile_analysis_pass() -> None:
    load_builtin_passes()

    pass_obj = build_registered_pass("tile-analysis")

    assert pass_obj.name == "tile-analysis"
    assert type(pass_obj).__name__ == "TileAnalysisPass"
    assert isinstance(pass_obj, ModulePass)
    assert pass_obj.__class__.__module__ == "kernel_gen.passes.tile.analysis"


# TC-REGISTRY-007A-0B
# 功能说明: 验证内置 pass 加载后可通过稳定名称构造 tile-reduce ModulePass。
# 使用示例: pytest -q test/passes/test_registry.py -k test_build_registered_tile_reduce_pass
# 对应功能实现文件路径: kernel_gen/passes/registry.py
# 对应 spec 文件路径: spec/pass/registry.md
# 对应测试文件路径: test/passes/test_registry.py
def test_build_registered_tile_reduce_pass() -> None:
    load_builtin_passes()

    pass_obj = build_registered_pass("tile-reduce")

    assert pass_obj.name == "tile-reduce"
    assert type(pass_obj).__name__ == "TileReducePass"
    assert isinstance(pass_obj, ModulePass)
    assert pass_obj.__class__.__module__ == "kernel_gen.passes.tile.reduce"


# TC-REGISTRY-007A-1
# 功能说明: 验证内置 pass 加载后可通过稳定名称构造 tile-elewise ModulePass。
# 使用示例: pytest -q test/passes/test_registry.py -k test_build_registered_tile_elewise_pass
# 对应功能实现文件路径: kernel_gen/passes/registry.py
# 对应 spec 文件路径: spec/pass/registry.md
# 对应测试文件路径: test/passes/test_registry.py
def test_build_registered_tile_elewise_pass() -> None:
    load_builtin_passes()

    pass_obj = build_registered_pass("tile-elewise")

    assert pass_obj.name == "tile-elewise"
    assert type(pass_obj).__name__ == "TileElewisePass"
    assert isinstance(pass_obj, ModulePass)
    assert pass_obj.__class__.__module__ == "kernel_gen.passes.tile.elewise"


# TC-REGISTRY-007A-2
# 功能说明: 验证 registry caller 当前冻结的 surviving public path 与 compat consumer matrix。
# 使用示例: pytest -q test/passes/test_registry.py -k test_registry_surviving_public_paths_match_consumer_matrix
# 对应功能实现文件路径: kernel_gen/passes/registry.py
# 对应 spec 文件路径: spec/pass/registry.md
# 对应测试文件路径: test/passes/test_registry.py
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
            "kernel_gen.passes.symbol_buffer_hoist",
            "SymbolBufferHoistPass",
            importlib.import_module("kernel_gen.passes.symbol_buffer_hoist").SymbolBufferHoistPass,
        ),
        (
            "kernel_gen.passes",
            "SymbolBufferHoistPass",
            importlib.import_module("kernel_gen.passes.symbol_buffer_hoist").SymbolBufferHoistPass,
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
            importlib.import_module("kernel_gen.passes.tile.analysis").TileAnalysisPass,
        ),
        (
            "kernel_gen.passes.lowering",
            "TileElewisePass",
            importlib.import_module("kernel_gen.passes.tile.elewise").TileElewisePass,
        ),
        (
            "kernel_gen.passes.lowering",
            "TileReducePass",
            importlib.import_module("kernel_gen.passes.tile.reduce").TileReducePass,
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
            "kernel_gen.passes.tile.analysis",
            "TileAnalysisPass",
            importlib.import_module("kernel_gen.passes.tile.analysis").TileAnalysisPass,
        ),
        (
            "kernel_gen.passes.tile.elewise",
            "TileElewisePass",
            importlib.import_module("kernel_gen.passes.tile.elewise").TileElewisePass,
        ),
        (
            "kernel_gen.passes.tile.reduce",
            "TileReducePass",
            importlib.import_module("kernel_gen.passes.tile.reduce").TileReducePass,
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
# 功能说明: 验证内置 nn lowering pass 加载后返回 ModulePass。
# 使用示例: pytest -q test/passes/test_registry.py -k test_build_registered_nn_lowering_pass_is_module_pass
# 对应功能实现文件路径: kernel_gen/passes/registry.py
# 对应 spec 文件路径: spec/pass/registry.md
# 对应测试文件路径: test/passes/test_registry.py
def test_build_registered_nn_lowering_pass_is_module_pass() -> None:
    load_builtin_passes()

    pass_obj = build_registered_pass("lower-nn")

    assert pass_obj.name == "lower-nn"
    assert type(pass_obj).__name__ == "NnLoweringPass"
    assert isinstance(pass_obj, ModulePass)


# TC-REGISTRY-007B
# 功能说明: 验证内置 pass 加载后可通过稳定名称构造 launch-kernel-cost-func，并透传公开 cost_kind 选项。
# 使用示例: pytest -q test/passes/test_registry.py -k test_build_registered_launch_kernel_cost_func_pass
# 对应功能实现文件路径: kernel_gen/passes/registry.py
# 对应 spec 文件路径: spec/pass/registry.md
# 对应测试文件路径: test/passes/test_registry.py
def test_build_registered_launch_kernel_cost_func_pass() -> None:
    load_builtin_passes()

    pass_obj = build_registered_pass("launch-kernel-cost-func", {"cost_kind": "DMA1|MAC|VECTOR1"})

    assert pass_obj.name == "launch-kernel-cost-func"
    assert type(pass_obj).__name__ == "LaunchKernelCostFuncPass"
    assert getattr(pass_obj, "cost_kind") == "DMA1|MAC|VECTOR1"


# TC-REGISTRY-007BA
# 功能说明: 验证 registry 无参构造 launch-kernel-cost-func 时使用公开默认七类成本 kind。
# 使用示例: pytest -q test/passes/test_registry.py -k test_build_registered_launch_kernel_cost_func_default_kind
# 对应功能实现文件路径: kernel_gen/passes/registry.py
# 对应 spec 文件路径: spec/pass/registry.md
# 对应测试文件路径: test/passes/test_registry.py
def test_build_registered_launch_kernel_cost_func_default_kind() -> None:
    load_builtin_passes()

    pass_obj = build_registered_pass("launch-kernel-cost-func")

    assert pass_obj.name == "launch-kernel-cost-func"
    assert type(pass_obj).__name__ == "LaunchKernelCostFuncPass"
    assert getattr(pass_obj, "cost_kind") == "DMA1|DMA2|DMA3|DMA4|MAC|VECTOR1|VECTOR2"


# TC-REGISTRY-007C
# 功能说明: 验证 registry 构造 launch-kernel-cost-func 时不会把非法 `cost_kind` 改写成通用 option error。
# 使用示例: pytest -q test/passes/test_registry.py -k test_build_registered_launch_kernel_cost_func_rejects_invalid_kind
# 对应功能实现文件路径: kernel_gen/passes/registry.py
# 对应 spec 文件路径: spec/pass/registry.md
# 对应测试文件路径: test/passes/test_registry.py
def test_build_registered_launch_kernel_cost_func_rejects_invalid_kind() -> None:
    load_builtin_passes()

    with pytest.raises(
        KernelCodeError,
        match=r"^LaunchKernelCostFuncError: cost_kind must be '\|' separated names from \[DMA,compute,memory,latency,DMA1,DMA2,DMA3,DMA4,MAC,VECTOR1,VECTOR2\]$",
    ):
        build_registered_pass("launch-kernel-cost-func", {"cost_kind": "DMA1|VECTOR1|DMA1"})


# TC-REGISTRY-007D
# 功能说明: 验证 registry 可直接构造 xdsl ModulePass，并保持返回值为 ModulePass 实例。
# 使用示例: pytest -q test/passes/test_registry.py -k test_build_registered_module_pass
# 对应功能实现文件路径: kernel_gen/passes/registry.py
# 对应 spec 文件路径: spec/pass/registry.md
# 对应测试文件路径: test/passes/test_registry.py
def test_build_registered_module_pass() -> None:
    seen: list[str] = []

    @register_pass
    class ModuleNoopPass(ModulePass):
        name = "module-noop-pass"

        def apply(self: "ModuleNoopPass", ctx: Context, module: ModuleOp) -> None:
            assert isinstance(ctx, Context)
            assert isinstance(module, ModuleOp)
            seen.append("module-noop-pass")

    pass_obj = build_registered_pass("module-noop-pass")

    assert isinstance(pass_obj, ModulePass)
    assert type(pass_obj).__name__ == "ModuleNoopPass"

    module = ModuleOp([])
    pm = PassManager(name="module-noop")
    pm.add_pass(pass_obj)
    assert pm.run(module) is module
    assert seen == ["module-noop-pass"]


# TC-REGISTRY-007E
# 功能说明: 验证 ModulePass 的 from_options 构造入口可被 registry 正常透传。
# 使用示例: pytest -q test/passes/test_registry.py -k test_build_registered_module_pass_with_options
# 对应功能实现文件路径: kernel_gen/passes/registry.py
# 对应 spec 文件路径: spec/pass/registry.md
# 对应测试文件路径: test/passes/test_registry.py
def test_build_registered_module_pass_with_options() -> None:
    seen: list[int] = []

    @register_pass
    class ModuleScalePass(ModulePass):
        name = "module-scale-pass"

        def __init__(self: "ModuleScalePass", scale: int) -> None:
            self.scale = scale

        @classmethod
        def from_options(cls, options: dict[str, str]) -> "ModuleScalePass":
            return cls(int(options["scale"]))

        def apply(self: "ModuleScalePass", ctx: Context, module: ModuleOp) -> None:
            assert isinstance(ctx, Context)
            assert isinstance(module, ModuleOp)
            seen.append(self.scale)

    pass_obj = build_registered_pass("module-scale-pass", {"scale": "3"})

    assert isinstance(pass_obj, ModulePass)
    assert type(pass_obj).__name__ == "ModuleScalePass"
    assert getattr(pass_obj, "scale") == 3

    module = ModuleOp([])
    pm = PassManager(name="module-scale")
    pm.add_pass(pass_obj)
    assert pm.run(module) is module
    assert seen == [3]


# TC-REGISTRY-007F
# 功能说明: 验证内置加载后 buffer-results-to-out-params 通过 registry 返回 ModulePass。
# 使用示例: pytest -q test/passes/test_registry.py -k test_build_registered_buffer_results_to_out_params_pass
# 对应功能实现文件路径: kernel_gen/passes/registry.py
# 对应 spec 文件路径: spec/pass/registry.md
# 对应测试文件路径: test/passes/test_registry.py
def test_build_registered_buffer_results_to_out_params_pass() -> None:
    load_builtin_passes()

    pass_obj = build_registered_pass("buffer-results-to-out-params")

    assert isinstance(pass_obj, ModulePass)
    assert pass_obj.name == "buffer-results-to-out-params"
    assert type(pass_obj).__name__ == "BufferResultsToOutParamsPass"


# TC-REGISTRY-007G
# 功能说明: 验证内置加载后 decompass 通过 registry 返回 ModulePass。
# 使用示例: pytest -q test/passes/test_registry.py -k test_build_registered_decompass_pass
# 对应功能实现文件路径: kernel_gen/passes/registry.py
# 对应 spec 文件路径: spec/pass/registry.md
# 对应测试文件路径: test/passes/test_registry.py
def test_build_registered_decompass_pass() -> None:
    load_builtin_passes()

    pass_obj = build_registered_pass("decompass")

    assert isinstance(pass_obj, ModulePass)
    assert pass_obj.name == "decompass"
    assert type(pass_obj).__name__ == "DecompassPass"


# TC-REGISTRY-007H
# 功能说明: 验证内置加载后 inline 通过 registry 返回 ModulePass。
# 使用示例: pytest -q test/passes/test_registry.py -k test_build_registered_inline_pass
# 对应功能实现文件路径: kernel_gen/passes/registry.py
# 对应 spec 文件路径: spec/pass/registry.md
# 对应测试文件路径: test/passes/test_registry.py
def test_build_registered_inline_pass() -> None:
    load_builtin_passes()

    pass_obj = build_registered_pass("inline")

    assert isinstance(pass_obj, ModulePass)
    assert pass_obj.name == "inline"
    assert type(pass_obj).__name__ == "InlinePass"


# TC-REGISTRY-007H1
# 功能说明: 验证 registry 的通用 `fold` 选项可作用于所有内置 pass。
# 使用示例: pytest -q test/passes/test_registry.py -k test_build_registered_pass_accepts_universal_fold_option
# 对应功能实现文件路径: kernel_gen/passes/registry.py
# 对应 spec 文件路径: spec/pass/registry.md
# 对应测试文件路径: test/passes/test_registry.py
def test_build_registered_pass_accepts_universal_fold_option() -> None:
    load_builtin_passes()

    pass_obj = build_registered_pass("inline", {"fold": "false"})
    module_pass_obj = build_registered_pass("decompass", {"fold": "false"})

    assert isinstance(pass_obj, ModulePass)
    assert pass_obj.name == "inline"
    assert pass_obj.fold is False
    assert isinstance(module_pass_obj, ModulePass)
    assert module_pass_obj.name == "decompass"
    assert module_pass_obj.fold is False


# TC-REGISTRY-007H2
# 功能说明: 验证 registry 对非法 `fold` bool 文本稳定失败。
# 使用示例: pytest -q test/passes/test_registry.py -k test_build_registered_pass_rejects_invalid_fold_option
# 对应功能实现文件路径: kernel_gen/passes/registry.py
# 对应 spec 文件路径: spec/pass/registry.md
# 对应测试文件路径: test/passes/test_registry.py
def test_build_registered_pass_rejects_invalid_fold_option() -> None:
    load_builtin_passes()

    with pytest.raises(KernelCodeError, match=r"^PassRegistryError: option 'fold' expects bool$"):
        build_registered_pass("inline", {"fold": "maybe"})


# TC-REGISTRY-007H3
# 功能说明: 验证 memory-pool 公开 options 可经 registry 构造并保留 alignment 边界。
# 使用示例: pytest -q test/passes/test_registry.py -k "memory_pool and alignment"
# 对应功能实现文件路径: kernel_gen/passes/registry.py
# 对应 spec 文件路径: spec/pass/registry.md
# 对应测试文件路径: test/passes/test_registry.py
def test_build_registered_memory_pool_alignment_options() -> None:
    load_builtin_passes()
    memory_pool_module = importlib.import_module("kernel_gen.passes.memory_pool")

    pass_obj = build_registered_pass(
        "memory-pool",
        {"rewrite": "true", "fold": "false", "alignment": "0"},
    )

    assert isinstance(pass_obj, memory_pool_module.MemoryPoolPass)
    assert pass_obj.rewrite is True
    assert pass_obj.fold is False
    assert pass_obj.alignment == 0


# TC-REGISTRY-007H4
# 功能说明: 验证 memory-pool alignment 与 option 文本非法时经 registry 稳定失败。
# 使用示例: pytest -q test/passes/test_registry.py -k "memory_pool and alignment"
# 对应功能实现文件路径: kernel_gen/passes/registry.py
# 对应 spec 文件路径: spec/pass/registry.md
# 对应测试文件路径: test/passes/test_registry.py
def test_build_registered_memory_pool_alignment_rejects_invalid_options() -> None:
    load_builtin_passes()

    invalid_cases = [
        ({"rewrite": "true", "alignment": "-1"}, "alignment must be non-negative integer"),
        ({"rewrite": "true", "alignment": "x"}, "alignment must be non-negative integer"),
        ({"rewrite": "maybe", "alignment": "0"}, "rewrite must be bool"),
        ({"rewrite": "true", "alignment": "0", "unknown": "1"}, "unknown option: unknown"),
    ]
    for options, expected in invalid_cases:
        with pytest.raises(KernelCodeError, match=expected):
            build_registered_pass("memory-pool", options)


# TC-REGISTRY-007H5
# 功能说明: 验证 memory-plan 公开 options 可经 registry 构造，并能与通用 fold 组合。
# 使用示例: pytest -q test/passes/test_registry.py -k test_build_registered_memory_plan_insert_free_options
# 对应功能实现文件路径: kernel_gen/passes/registry.py
# 对应 spec 文件路径: spec/pass/registry.md
# 对应测试文件路径: test/passes/test_registry.py
def test_build_registered_memory_plan_insert_free_options() -> None:
    load_builtin_passes()
    memory_plan_module = importlib.import_module("kernel_gen.passes.memory_plan")

    pass_obj = build_registered_pass("memory-plan", {"insert-free": "true", "fold": "false"})

    assert isinstance(pass_obj, memory_plan_module.MemoryPlanPass)
    assert pass_obj.name == "memory-plan"
    assert pass_obj.insert_free is True
    assert pass_obj.fold is False


# TC-REGISTRY-007H6
# 功能说明: 验证 memory-plan direct from_options 与 registry option 包装错误稳定。
# 使用示例: pytest -q test/passes/test_registry.py -k test_build_registered_memory_plan_rejects_invalid_options
# 对应功能实现文件路径: kernel_gen/passes/registry.py
# 对应 spec 文件路径: spec/pass/registry.md
# 对应测试文件路径: test/passes/test_registry.py
def test_build_registered_memory_plan_rejects_invalid_options() -> None:
    load_builtin_passes()
    memory_plan_module = importlib.import_module("kernel_gen.passes.memory_plan")

    with pytest.raises(KernelCodeError, match=r"^MemoryPlanOptionError: unknown option 'unknown'$"):
        memory_plan_module.MemoryPlanPass.from_options({"unknown": "true"})
    with pytest.raises(KernelCodeError, match=r"^MemoryPlanOptionError: insert-free expects bool$"):
        memory_plan_module.MemoryPlanPass.from_options({"insert-free": "maybe"})
    with pytest.raises(
        KernelCodeError,
        match=r"^PassRegistryError: pass 'memory-plan' option error: MemoryPlanOptionError: unknown option 'unknown'$",
    ):
        build_registered_pass("memory-plan", {"unknown": "true"})
    with pytest.raises(
        KernelCodeError,
        match=r"^PassRegistryError: pass 'memory-plan' option error: MemoryPlanOptionError: insert-free expects bool$",
    ):
        build_registered_pass("memory-plan", {"insert-free": "maybe"})


# TC-REGISTRY-007I
# 功能说明: 验证内置加载后 attach-arch-information 通过 registry 返回 ModulePass。
# 使用示例: pytest -q test/passes/test_registry.py -k test_build_registered_attach_arch_information_pass
# 对应功能实现文件路径: kernel_gen/passes/registry.py
# 对应 spec 文件路径: spec/pass/registry.md
# 对应测试文件路径: test/passes/test_registry.py
def test_build_registered_attach_arch_information_pass() -> None:
    load_builtin_passes()

    pass_obj = build_registered_pass("attach-arch-information")

    assert isinstance(pass_obj, ModulePass)
    assert pass_obj.name == "attach-arch-information"
    assert type(pass_obj).__name__ == "AttachArchInformationPass"


# TC-REGISTRY-007J
# 功能说明: 验证已退场的 lowering 旧路径、旧 tile submodule path 与 analysis family 路径在 S1/S7/S8 基线中稳定失败。
# 使用示例: pytest -q test/passes/test_registry.py -k test_registry_old_lowering_paths_fail_fast
# 对应功能实现文件路径: kernel_gen/passes/registry.py
# 对应 spec 文件路径: spec/pass/registry.md
# 对应测试文件路径: test/passes/test_registry.py
def test_registry_old_lowering_paths_fail_fast() -> None:
    old_module_paths = (
        "kernel_gen.analysis",
        "kernel_gen.analysis.analysis",
        "kernel_gen.analysis.compute",
        "kernel_gen.analysis.memory",
        "kernel_gen.passes.analysis",
        "kernel_gen.passes.analysis.func_cost",
        "kernel_gen.passes.lowering.registry",
        "kernel_gen.passes.lowering.pass_manager",
        "kernel_gen.passes.lowering.inline",
        "kernel_gen.passes.lowering.attach_arch_information",
        "kernel_gen.passes.lowering.decompass",
        "kernel_gen.passes.lowering.buffer_results_to_out_params",
        "kernel_gen.passes.lowering.nn_to_kernel",
        "kernel_gen.passes.lowering.symbol_buffer_hoist",
        "kernel_gen.passes.lowering.tile_analysis",
        "kernel_gen.passes.lowering.tile_elewise",
        "kernel_gen.passes.lowering.tile_reduce",
    )

    with _worktree_only_imports(*old_module_paths):
        for module_name in old_module_paths:
            with pytest.raises(ModuleNotFoundError):
                importlib.import_module(module_name)


# TC-REGISTRY-007J-1
# 功能说明: 验证 analysis family 退场后，registry 不再提供 analyze-func-cost 构造入口。
# 使用示例: pytest -q test/passes/test_registry.py -k test_registry_retired_analysis_pass_name_fails_fast
# 对应功能实现文件路径: kernel_gen/passes/registry.py
# 对应 spec 文件路径: spec/pass/registry.md
# 对应测试文件路径: test/passes/test_registry.py
def test_registry_retired_analysis_pass_name_fails_fast() -> None:
    load_builtin_passes()

    with pytest.raises(KernelCodeError, match=r"^PassRegistryError: unknown pass 'analyze-func-cost'$"):
        build_registered_pass("analyze-func-cost")


# TC-REGISTRY-007J-2
# 功能说明: 验证内置加载后 symbol-buffer-hoist 可通过稳定名称构造，并固定 canonical module path。
# 使用示例: pytest -q test/passes/test_registry.py -k test_build_registered_symbol_buffer_hoist_pass
# 对应功能实现文件路径: kernel_gen/passes/registry.py
# 对应 spec 文件路径: spec/pass/registry.md
# 对应测试文件路径: test/passes/test_registry.py
def test_build_registered_symbol_buffer_hoist_pass() -> None:
    load_builtin_passes()

    pass_obj = build_registered_pass("symbol-buffer-hoist")

    assert isinstance(pass_obj, ModulePass)
    assert pass_obj.name == "symbol-buffer-hoist"
    assert type(pass_obj).__name__ == "SymbolBufferHoistPass"
    assert pass_obj.__class__.__module__ == "kernel_gen.passes.symbol_buffer_hoist"


# TC-REGISTRY-007J-3
# 功能说明: 验证内置加载后 arch-parallelize 可通过稳定名称和 options 构造。
# 使用示例: pytest -q test/passes/test_registry.py -k test_build_registered_arch_parallelize_pass
# 对应功能实现文件路径: kernel_gen/passes/registry.py
# 对应 spec 文件路径: spec/pass/registry.md
# 对应测试文件路径: test/passes/test_registry.py
def test_build_registered_arch_parallelize_pass() -> None:
    load_builtin_passes()

    pass_obj = build_registered_pass(
        "arch-parallelize",
        {"target": "npu_demo", "parallel_level": "block"},
    )

    assert isinstance(pass_obj, ModulePass)
    assert pass_obj.name == "arch-parallelize"
    assert type(pass_obj).__name__ == "ArchParallelizePass"
    assert pass_obj.__class__.__module__ == "kernel_gen.passes.arch_parallelize"
    assert "arch-parallelize" in list_registered_passes()


# TC-REGISTRY-007K
# 功能说明: 验证内置 pipeline 加载后可通过稳定名称构造 npu-demo-lowering。
# 使用示例: pytest -q test/passes/test_registry.py -k test_build_registered_npu_demo_lowering_pipeline
# 对应功能实现文件路径: kernel_gen/passes/registry.py
# 对应 spec 文件路径: spec/pass/registry.md
# 对应测试文件路径: test/passes/test_registry.py
def test_build_registered_npu_demo_lowering_pipeline() -> None:
    load_builtin_passes()

    pm = build_registered_pipeline("npu-demo-lowering", {"target": "npu_demo"})

    assert isinstance(pm, PassManager)
    assert pm.name == "npu-demo-lowering"


# TC-REGISTRY-008
# 功能说明: 验证 load_builtin_passes 满足幂等性，并提供基础内置 pass/pipeline、default-lowering 与 npu-demo-lowering。
# 使用示例: pytest -q test/passes/test_registry.py -k test_load_builtin_passes_is_idempotent
# 对应功能实现文件路径: kernel_gen/passes/registry.py
# 对应 spec 文件路径: spec/pass/registry.md
# 对应测试文件路径: test/passes/test_registry.py
def test_load_builtin_passes_is_idempotent() -> None:
    load_builtin_passes()
    load_builtin_passes()
    assert "no-op" in list_registered_passes()
    assert "inline" in list_registered_passes()
    assert "attach-arch-information" in list_registered_passes()
    assert "memory-plan" in list_registered_passes()
    assert "arch-parallelize" in list_registered_passes()
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
# 功能说明: 验证重新导入 registry 后再次 load_builtin_passes 仍能注册 default-lowering 与 npu-demo-lowering。
# 使用示例: pytest -q test/passes/test_registry.py -k test_load_builtin_passes_after_reload_registers_default_lowering
# 对应功能实现文件路径: kernel_gen/passes/registry.py
# 对应 spec 文件路径: spec/pass/registry.md
# 对应测试文件路径: test/passes/test_registry.py
def test_load_builtin_passes_after_reload_registers_default_lowering() -> None:
    load_builtin_passes()
    _reload_registry_api()
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
# 功能说明: 验证 npu-demo-lowering 接受 target 选项。
# 使用示例: pytest -q test/passes/test_registry.py -k test_build_registered_npu_demo_lowering_pipeline_with_options
# 对应功能实现文件路径: kernel_gen/passes/registry.py
# 对应 spec 文件路径: spec/pass/registry.md
# 对应测试文件路径: test/passes/test_registry.py
def test_build_registered_npu_demo_lowering_pipeline_with_options() -> None:
    load_builtin_passes()

    pm = build_registered_pipeline("npu-demo-lowering", {"target": "npu_demo"})
    assert isinstance(pm, PassManager)
    assert pm.name == "npu-demo-lowering"


# TC-REGISTRY-008C
# 功能说明: 验证 npu-demo-lowering 的未知选项会显式失败。
# 使用示例: pytest -q test/passes/test_registry.py -k test_build_registered_npu_demo_lowering_pipeline_rejects_unknown_option
# 对应功能实现文件路径: kernel_gen/passes/registry.py
# 对应 spec 文件路径: spec/pass/registry.md
# 对应测试文件路径: test/passes/test_registry.py
def test_build_registered_npu_demo_lowering_pipeline_rejects_unknown_option() -> None:
    load_builtin_passes()

    with pytest.raises(
        KernelCodeError, match=r"^PassRegistryError: pipeline 'npu-demo-lowering' option error$"
    ):
        build_registered_pipeline("npu-demo-lowering", {"only-kernel": "true"})


# TC-REGISTRY-009
# 功能说明: 验证带 options 的 pass 可通过 from_options 构造。
# 使用示例: pytest -q test/passes/test_registry.py -k test_build_registered_pass_with_options
# 对应功能实现文件路径: kernel_gen/passes/registry.py
# 对应 spec 文件路径: spec/pass/registry.md
# 对应测试文件路径: test/passes/test_registry.py
def test_build_registered_pass_with_options() -> None:
    @register_pass
    class OptionPass(Pass):
        name = "option-pass"

        def __init__(self: "OptionPass", mode: str) -> None:
            self.mode = mode

        @classmethod
        def from_options(cls, options: dict[str, str]) -> "OptionPass":
            return cls(options["mode"])

        def apply(self: "OptionPass", ctx: Context, target: ModuleOp) -> None:
            _ = ctx
            _ = target

    pass_obj = build_registered_pass("option-pass", {"mode": "fast"})
    assert isinstance(pass_obj, OptionPass)
    assert pass_obj.mode == "fast"


# TC-REGISTRY-010
# 功能说明: 验证不支持 options 的 pass 会报告稳定错误短语。
# 使用示例: pytest -q test/passes/test_registry.py -k test_build_registered_pass_options_not_supported
# 对应功能实现文件路径: kernel_gen/passes/registry.py
# 对应 spec 文件路径: spec/pass/registry.md
# 对应测试文件路径: test/passes/test_registry.py
def test_build_registered_pass_options_not_supported() -> None:
    @register_pass
    class PlainPass(Pass):
        name = "plain-pass"

        def apply(self: "PlainPass", ctx: Context, target: ModuleOp) -> None:
            _ = ctx
            _ = target

    with pytest.raises(
        KernelCodeError, match=r"^PassRegistryError: pass 'plain-pass' does not accept options$"
    ):
        _ = build_registered_pass("plain-pass", {"mode": "fast"})


# TC-REGISTRY-011
# 功能说明: 验证 pass 的 options 构造失败会报告稳定错误短语。
# 使用示例: pytest -q test/passes/test_registry.py -k test_build_registered_pass_option_error
# 对应功能实现文件路径: kernel_gen/passes/registry.py
# 对应 spec 文件路径: spec/pass/registry.md
# 对应测试文件路径: test/passes/test_registry.py
def test_build_registered_pass_option_error() -> None:
    @register_pass
    class ErrorPass(Pass):
        name = "error-pass"

        @classmethod
        def from_options(cls, options: dict[str, str]) -> "ErrorPass":
            raise ValueError("invalid options")

        def apply(self: "ErrorPass", ctx: Context, target: ModuleOp) -> None:
            _ = ctx
            _ = target

    with pytest.raises(KernelCodeError, match=r"^PassRegistryError: pass 'error-pass' option error$"):
        _ = build_registered_pass("error-pass", {"mode": "fast"})


# TC-REGISTRY-012
# 功能说明: 验证带 options 的 pipeline 会把 options 透传给 builder。
# 使用示例: pytest -q test/passes/test_registry.py -k test_build_registered_pipeline_with_options
# 对应功能实现文件路径: kernel_gen/passes/registry.py
# 对应 spec 文件路径: spec/pass/registry.md
# 对应测试文件路径: test/passes/test_registry.py
def test_build_registered_pipeline_with_options() -> None:
    @register_pipeline("option-pipeline")
    def _build_option_pipeline(options: dict[str, str]) -> PassManager:
        return PassManager(name=options["mode"])

    pm = build_registered_pipeline("option-pipeline", {"mode": "analysis"})
    assert isinstance(pm, PassManager)
    assert pm.name == "analysis"


# TC-REGISTRY-013
# 功能说明: 验证不支持 options 的 pipeline 会报告稳定错误短语。
# 使用示例: pytest -q test/passes/test_registry.py -k test_build_registered_pipeline_options_not_supported
# 对应功能实现文件路径: kernel_gen/passes/registry.py
# 对应 spec 文件路径: spec/pass/registry.md
# 对应测试文件路径: test/passes/test_registry.py
def test_build_registered_pipeline_options_not_supported() -> None:
    @register_pipeline("plain-pipeline")
    def _build_plain_pipeline() -> PassManager:
        return PassManager(name="plain")

    with pytest.raises(
        KernelCodeError, match=r"^PassRegistryError: pipeline 'plain-pipeline' does not accept options$"
    ):
        _ = build_registered_pipeline("plain-pipeline", {"mode": "fast"})


# TC-REGISTRY-014
# 功能说明: 验证 pipeline 的 options 构造失败会报告稳定错误短语。
# 使用示例: pytest -q test/passes/test_registry.py -k test_build_registered_pipeline_option_error
# 对应功能实现文件路径: kernel_gen/passes/registry.py
# 对应 spec 文件路径: spec/pass/registry.md
# 对应测试文件路径: test/passes/test_registry.py
def test_build_registered_pipeline_option_error() -> None:
    @register_pipeline("error-pipeline")
    def _build_error_pipeline(options: dict[str, str]) -> PassManager:
        raise ValueError("invalid options")

    with pytest.raises(
        KernelCodeError, match=r"^PassRegistryError: pipeline 'error-pipeline' option error$"
    ):
        _ = build_registered_pipeline("error-pipeline", {"mode": "fast"})
