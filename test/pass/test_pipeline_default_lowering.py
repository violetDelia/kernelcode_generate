"""default lowering pipeline tests.

创建者: 朽木露琪亚
最后一次更改: 朽木露琪亚

功能说明:
- 覆盖 kernel_gen/passes/pipeline/default_lowering.py 的默认 pipeline 构造与顺序。

当前覆盖率信息:
- 当前覆盖率: 未统计（本任务验证未启用 coverage 统计）。
- 达标判定: 待后续补充统计结果。

覆盖率命令:
- `pytest -q --cov=kernel_gen.passes.pipeline.default_lowering --cov-branch --cov-report=term-missing test/pass/test_pipeline_default_lowering.py`

使用示例:
- pytest -q test/pass/test_pipeline_default_lowering.py

关联文件:
- 功能实现: kernel_gen/passes/pipeline/default_lowering.py
- Spec 文档: spec/pass/pipeline/default_lowering.md
- 测试文件: test/pass/test_pipeline_default_lowering.py
"""

from __future__ import annotations

import sys
from pathlib import Path

import importlib
import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

pipeline_module = importlib.import_module("kernel_gen.passes.pipeline")
build_default_lowering_pipeline = pipeline_module.build_default_lowering_pipeline
buffer_results_module = importlib.import_module("kernel_gen.passes.buffer_results_to_out_params")
BufferResultsToOutParamsPass = buffer_results_module.BufferResultsToOutParamsPass

pass_manager_module = importlib.import_module("kernel_gen.passes.pass_manager")
PassManager = pass_manager_module.PassManager


# TC-PIPELINE-001
# 创建者: 朽木露琪亚
# 最后一次更改: 朽木露琪亚
# 最近一次运行测试时间: 2026-04-11 23:50:00 +0800
# 最近一次运行成功时间: 2026-04-11 23:50:00 +0800
# 功能说明: 验证默认 pipeline 构造返回 PassManager 且名称为 default-lowering。
# 测试目的: 固定 default-lowering pipeline 的公开名称与类型。
# 使用示例: pytest -q test/pass/test_pipeline_default_lowering.py -k test_default_lowering_pipeline_builds_pass_manager
# 对应功能实现文件路径: kernel_gen/passes/pipeline/default_lowering.py
# 对应 spec 文件路径: spec/pass/pipeline/default_lowering.md
# 对应测试文件路径: test/pass/test_pipeline_default_lowering.py
def test_default_lowering_pipeline_builds_pass_manager() -> None:
    pm = build_default_lowering_pipeline()
    assert isinstance(pm, PassManager)
    assert pm.name == "default-lowering"


# TC-PIPELINE-002
# 创建者: 朽木露琪亚
# 最后一次更改: 朽木露琪亚
# 最近一次运行测试时间: 2026-04-11 23:50:00 +0800
# 最近一次运行成功时间: 2026-04-11 23:50:00 +0800
# 功能说明: 验证默认 pipeline pass 顺序固定为 decompass -> lower-nn -> buffer-results-to-out-params -> lower-dma-memory-hierarchy。
# 测试目的: 锁定 default-lowering 顺序一致性，避免各处手工拼接不一致。
# 使用示例: pytest -q test/pass/test_pipeline_default_lowering.py -k test_default_lowering_pipeline_pass_order
# 对应功能实现文件路径: kernel_gen/passes/pipeline/default_lowering.py
# 对应 spec 文件路径: spec/pass/pipeline/default_lowering.md
# 对应测试文件路径: test/pass/test_pipeline_default_lowering.py
def test_default_lowering_pipeline_pass_order(monkeypatch: pytest.MonkeyPatch) -> None:
    lowering_module = importlib.import_module("kernel_gen.passes.lowering")
    decompose_module = importlib.import_module("kernel_gen.passes.decompass")
    DecompassPass = decompose_module.DecompassPass
    NnLoweringPass = lowering_module.NnLoweringPass
    LowerDmaMemoryHierarchyPass = lowering_module.LowerDmaMemoryHierarchyPass
    order: list[str] = []

    def _record_decompose(self: object, target: object) -> object:
        order.append("decompass")
        return target

    def _record_lower(self: object, target: object) -> object:
        order.append("lower-nn")
        return target

    def _record_buffer(self: object, target: object) -> object:
        order.append("buffer-results-to-out-params")
        return target

    def _record_dma(self: object, target: object) -> object:
        order.append("lower-dma-memory-hierarchy")
        return target

    monkeypatch.setattr(DecompassPass, "run", _record_decompose)
    monkeypatch.setattr(NnLoweringPass, "run", _record_lower)
    monkeypatch.setattr(BufferResultsToOutParamsPass, "run", _record_buffer)
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
