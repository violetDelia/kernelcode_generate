"""npu demo lowering pipeline tests.

创建者: 朽木露琪亚
最后一次更改: 朽木露琪亚

功能说明:
- 覆盖 kernel_gen/passes/pipeline/npu_demo_lowering.py 的公开 builder 与顺序。

当前覆盖率信息:
- 当前覆盖率: 未统计（本任务验证未启用 coverage 统计）。
- 达标判定: 待后续补充统计结果。

覆盖率命令:
- `pytest -q --cov=kernel_gen.passes.pipeline.npu_demo_lowering --cov-branch --cov-report=term-missing test/pass/test_pipeline_npu_demo_lowering.py`

使用示例:
- pytest -q test/pass/test_pipeline_npu_demo_lowering.py

关联文件:
- 功能实现: kernel_gen/passes/pipeline/npu_demo_lowering.py
- Spec 文档: spec/pass/pipeline/npu_demo_lowering.md
- 测试文件: test/pass/test_pipeline_npu_demo_lowering.py
"""

from __future__ import annotations

import importlib
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

pipeline_module = importlib.import_module("kernel_gen.passes.pipeline")
build_npu_demo_lowering_pipeline = pipeline_module.build_npu_demo_lowering_pipeline

pass_manager_module = importlib.import_module("kernel_gen.passes.pass_manager")
PassManager = pass_manager_module.PassManager
InlinePass = importlib.import_module("kernel_gen.passes.inline").InlinePass
AttachArchInformationPass = importlib.import_module("kernel_gen.passes.attach_arch_information").AttachArchInformationPass
DecompassPass = importlib.import_module("kernel_gen.passes.decompass").DecompassPass
NnLoweringPass = importlib.import_module("kernel_gen.passes.lowering").NnLoweringPass
OutlineDeviceKernelPass = importlib.import_module("kernel_gen.passes.outline_device_kernel").OutlineDeviceKernelPass
SymbolLoopHoistPass = importlib.import_module("kernel_gen.passes.symbol_loop_hoist").SymbolLoopHoistPass


# TC-PIPELINE-100
# 创建者: 朽木露琪亚
# 最后一次更改: 朽木露琪亚
# 最近一次运行测试时间: 未运行
# 最近一次运行成功时间: 未运行
# 功能说明: 验证 npu-demo-lowering builder 返回 PassManager 且名称固定。
# 测试目的: 锁定 npu-demo-lowering pipeline 的公开名称与类型。
# 使用示例: pytest -q test/pass/test_pipeline_npu_demo_lowering.py -k test_npu_demo_lowering_pipeline_builds_pass_manager
# 对应功能实现文件路径: kernel_gen/passes/pipeline/npu_demo_lowering.py
# 对应 spec 文件路径: spec/pass/pipeline/npu_demo_lowering.md
# 对应测试文件路径: test/pass/test_pipeline_npu_demo_lowering.py
def test_npu_demo_lowering_pipeline_builds_pass_manager() -> None:
    pm = build_npu_demo_lowering_pipeline({"target": "npu_demo"})
    assert isinstance(pm, PassManager)
    assert pm.name == "npu-demo-lowering"


# TC-PIPELINE-101
# 创建者: 朽木露琪亚
# 最后一次更改: 朽木露琪亚
# 最近一次运行测试时间: 未运行
# 最近一次运行成功时间: 未运行
# 功能说明: 验证 npu-demo-lowering 的固定顺序为 inline -> decompass -> lower-nn -> symbol-loop-hoist -> attach-arch-information -> outline-device-kernel。
# 测试目的: 锁定 dsl_run 新正向管线的最小公开顺序。
# 使用示例: pytest -q test/pass/test_pipeline_npu_demo_lowering.py -k test_npu_demo_lowering_pipeline_pass_order
# 对应功能实现文件路径: kernel_gen/passes/pipeline/npu_demo_lowering.py
# 对应 spec 文件路径: spec/pass/pipeline/npu_demo_lowering.md
# 对应测试文件路径: test/pass/test_pipeline_npu_demo_lowering.py
@pytest.mark.nn_lowering
def test_npu_demo_lowering_pipeline_pass_order(monkeypatch: pytest.MonkeyPatch) -> None:
    order: list[str] = []

    def _record_inline(self: object, target: object) -> object:
        order.append("inline")
        return target

    def _record_decompose(self: object, target: object) -> object:
        order.append("decompass")
        return target

    def _record_lower(self: object, target: object) -> object:
        order.append("lower-nn")
        return target

    def _record_hoist(self: object, target: object) -> object:
        order.append("symbol-loop-hoist")
        return target

    def _record_attach(self: object, target: object) -> object:
        order.append("attach-arch-information")
        return target

    def _record_outline(self: object, target: object) -> object:
        order.append("outline-device-kernel")
        return target

    monkeypatch.setattr(InlinePass, "run", _record_inline)
    monkeypatch.setattr(DecompassPass, "run", _record_decompose)
    monkeypatch.setattr(NnLoweringPass, "run", _record_lower)
    monkeypatch.setattr(SymbolLoopHoistPass, "run", _record_hoist)
    monkeypatch.setattr(AttachArchInformationPass, "run", _record_attach)
    monkeypatch.setattr(OutlineDeviceKernelPass, "run", _record_outline)

    pm = build_npu_demo_lowering_pipeline({"target": "npu_demo"})
    sentinel = object()
    assert pm.run(sentinel) is sentinel
    assert order == [
        "inline",
        "decompass",
        "lower-nn",
        "symbol-loop-hoist",
        "attach-arch-information",
        "outline-device-kernel",
    ]


def test_npu_demo_lowering_pipeline_rejects_unknown_option() -> None:
    with pytest.raises(ValueError, match=r"^npu-demo-lowering only accepts target option; got only-kernel$"):
        build_npu_demo_lowering_pipeline({"only-kernel": "true"})
