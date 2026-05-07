"""default lowering pipeline tests.


功能说明:
- 覆盖 kernel_gen/passes/pipeline/default_lowering.py 的默认 pipeline 构造与顺序。

当前覆盖率信息:
- 当前覆盖率: 未统计（本任务验证未启用 coverage 统计）。
- 达标判定: 待后续补充统计结果。

覆盖率命令:
- `pytest -q --cov=kernel_gen.passes.pipeline.default_lowering --cov-branch --cov-report=term-missing test/passes/pipeline/test_default_lowering.py`

使用示例:
- pytest -q test/passes/pipeline/test_default_lowering.py

关联文件:
- 功能实现: kernel_gen/passes/pipeline/default_lowering.py
- Spec 文档: spec/pass/pipeline/default_lowering.md
- 测试文件: test/passes/pipeline/test_default_lowering.py
"""

from __future__ import annotations

import sys
from pathlib import Path

import importlib
import pytest

from xdsl.context import Context
from xdsl.dialects import func
from xdsl.dialects.builtin import ArrayAttr, FunctionType, ModuleOp, f32
from xdsl.ir import Block, Region

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

pipeline_module = importlib.import_module("kernel_gen.passes.pipeline")
build_default_lowering_pipeline = pipeline_module.build_default_lowering_pipeline
buffer_results_module = importlib.import_module("kernel_gen.passes.buffer_results_to_out_params")
BufferResultsToOutParamsPass = buffer_results_module.BufferResultsToOutParamsPass

pass_manager_module = importlib.import_module("kernel_gen.passes.pass_manager")
PassManager = pass_manager_module.PassManager
target_registry = importlib.import_module("kernel_gen.target.registry")
nn_module = importlib.import_module("kernel_gen.dialect.nn")
dma_module = importlib.import_module("kernel_gen.dialect.dma")
kernel_module = importlib.import_module("kernel_gen.dialect.kernel")
symbol_module = importlib.import_module("kernel_gen.dialect.symbol")

DmaDesliceOp = dma_module.DmaDesliceOp
DmaSliceOp = dma_module.DmaSliceOp
KernelBinaryElewiseOp = kernel_module.KernelBinaryElewiseOp
NnAddOp = nn_module.NnAddOp
NnMemorySpaceAttr = nn_module.NnMemorySpaceAttr
NnMemoryType = nn_module.NnMemoryType
SymbolExprAttr = symbol_module.SymbolExprAttr


def _pipeline_memory_type(space: str = "global") -> NnMemoryType:
    """构造 default-lowering 黑盒测试使用的 `nn.memory`。"""

    return NnMemoryType(
        ArrayAttr([SymbolExprAttr.from_expr("2"), SymbolExprAttr.from_expr("2")]),
        ArrayAttr([SymbolExprAttr.from_expr("2"), SymbolExprAttr.from_expr("1")]),
        f32,
        NnMemorySpaceAttr.from_name(space),
    )


def _build_add_memory_return_module() -> ModuleOp:
    """构造 `nn.add` memory-return module。"""

    mem = _pipeline_memory_type()
    block = Block(arg_types=[mem, mem])
    add_op = NnAddOp(block.args[0], block.args[1], mem, NnMemorySpaceAttr.from_name("global"))
    block.add_ops([add_op, func.ReturnOp(add_op.result)])
    func_op = func.FuncOp("add_direct", FunctionType.from_lists([mem, mem], [mem]), Region(block))
    return ModuleOp([func_op])


def _ensure_default_lowering_target() -> str:
    """注册 default-lowering legacy hierarchy 测试 target。"""

    name = "default_lowering_hierarchy_test"
    spec = target_registry.TargetSpec(
        name=name,
        arch_supported_ops=None,
        arch_unsupported_ops=set(),
        hardware={
            "thread_num": 1,
            "block_num": 1,
            "subthread_num": 1,
            "sm_memory_size": 1024,
            "lm_memory_size": 1024,
            "tsm_memory_size": 0,
            "tlm1_memory_size": 0,
            "tlm2_memory_size": 0,
            "tlm3_memory_size": 0,
        },
    )
    try:
        target_registry.register_target(spec)
    except ValueError as exc:
        if "target already registered" not in str(exc):
            raise
    return name


# TC-PIPELINE-001
# 功能说明: 验证默认 pipeline 构造返回 PassManager 且名称为 default-lowering。
# 测试目的: 固定 default-lowering pipeline 的公开名称与类型。
# 使用示例: pytest -q test/passes/pipeline/test_default_lowering.py -k test_default_lowering_pipeline_builds_pass_manager
# 对应功能实现文件路径: kernel_gen/passes/pipeline/default_lowering.py
# 对应 spec 文件路径: spec/pass/pipeline/default_lowering.md
# 对应测试文件路径: test/passes/pipeline/test_default_lowering.py
def test_default_lowering_pipeline_builds_pass_manager() -> None:
    pm = build_default_lowering_pipeline()
    assert isinstance(pm, PassManager)
    assert pm.name == "default-lowering"


# TC-PIPELINE-002
# 功能说明: 验证默认 pipeline pass 顺序固定为 decompass -> lower-nn -> buffer-results-to-out-params -> lower-dma-memory-hierarchy。
# 测试目的: 锁定 default-lowering 顺序一致性，避免各处手工拼接不一致。
# 使用示例: pytest -q test/passes/pipeline/test_default_lowering.py -k test_default_lowering_pipeline_pass_order
# 对应功能实现文件路径: kernel_gen/passes/pipeline/default_lowering.py
# 对应 spec 文件路径: spec/pass/pipeline/default_lowering.md
# 对应测试文件路径: test/passes/pipeline/test_default_lowering.py
def test_default_lowering_pipeline_pass_order(monkeypatch: pytest.MonkeyPatch) -> None:
    lowering_module = importlib.import_module("kernel_gen.passes.lowering")
    decompose_module = importlib.import_module("kernel_gen.passes.decompass")
    DecompassPass = decompose_module.DecompassPass
    NnLoweringPass = lowering_module.NnLoweringPass
    LowerDmaMemoryHierarchyPass = lowering_module.LowerDmaMemoryHierarchyPass
    order: list[str] = []

    def _record_decompose(self, ctx: Context, target: ModuleOp) -> None:
        _ = ctx
        order.append("decompass")

    def _record_lower(self, ctx: Context, target: ModuleOp) -> None:
        _ = ctx
        order.append("lower-nn")

    def _record_buffer(self, ctx: Context, target: ModuleOp) -> None:
        _ = ctx
        order.append("buffer-results-to-out-params")

    def _record_dma(self, ctx: Context, target: ModuleOp) -> None:
        _ = ctx
        order.append("lower-dma-memory-hierarchy")

    monkeypatch.setattr(DecompassPass, "apply", _record_decompose)
    monkeypatch.setattr(NnLoweringPass, "apply", _record_lower)
    monkeypatch.setattr(BufferResultsToOutParamsPass, "apply", _record_buffer)
    monkeypatch.setattr(LowerDmaMemoryHierarchyPass, "apply", _record_dma)

    pm = build_default_lowering_pipeline()
    sentinel = ModuleOp([])
    assert pm.run(sentinel) is sentinel
    assert order == [
        "decompass",
        "lower-nn",
        "buffer-results-to-out-params",
        "lower-dma-memory-hierarchy",
    ]


# TC-PIPELINE-003
# 功能说明: 验证默认 pipeline 对 `nn.add` memory-return 产出前置 out 参数、kernel.binary_elewise 与 dma.slice/deslice 链。
# 测试目的: 锁定 default-lowering 的公开黑盒合同，避免 lower-dma-memory-hierarchy 默认 no-op 破坏 spec。
# 使用示例: pytest -q test/passes/pipeline/test_default_lowering.py -k test_default_lowering_pipeline_add_uses_legacy_dma_hierarchy
# 对应功能实现文件路径: kernel_gen/passes/pipeline/default_lowering.py
# 对应 spec 文件路径: spec/pass/pipeline/default_lowering.md
# 对应测试文件路径: test/passes/pipeline/test_default_lowering.py
def test_default_lowering_pipeline_add_uses_legacy_dma_hierarchy() -> None:
    module = _build_add_memory_return_module()
    target_name = _ensure_default_lowering_target()
    previous_target = target_registry.get_current_target()
    target_registry.set_current_target(target_name)
    try:
        lowered = build_default_lowering_pipeline().run(module)
    finally:
        target_registry.set_current_target(previous_target)

    func_op = next(op for op in lowered.ops if isinstance(op, func.FuncOp))
    body_ops = list(func_op.body.block.ops)
    kernel_op = next(op for op in body_ops if isinstance(op, KernelBinaryElewiseOp))
    slice_count = sum(isinstance(op, DmaSliceOp) for op in body_ops)
    deslice_count = sum(isinstance(op, DmaDesliceOp) for op in body_ops)

    assert len(list(func_op.function_type.inputs)) == 3
    assert list(func_op.function_type.outputs) == []
    assert slice_count >= 2
    assert deslice_count >= 1
    assert getattr(kernel_op.attributes["kind"], "data", None) == "add"
    assert kernel_op.attributes["space"] == NnMemorySpaceAttr.from_name("local")
