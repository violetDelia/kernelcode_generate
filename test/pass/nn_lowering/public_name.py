"""nn_lowering public API tests.

创建者: 小李飞刀
最后一次更改: jcc你莫辜负

功能说明:
- 验证 NnLoweringPass 的公开名称与导出路径。
- 验证 nn_lowering pattern driver 的注册顺序与单 op pattern 结构。

使用示例:
- pytest -q test/pass/nn_lowering/public_name.py

关联文件:
- 功能实现: kernel_gen/passes/lowering/nn_lowering/nn_lowering.py
- Spec 文档: spec/pass/lowering/nn_lowering/spec.md
- 测试文件: test/pass/nn_lowering/public_name.py
"""

from __future__ import annotations

import importlib
import sys
from pathlib import Path

import pytest
from xdsl.context import Context
from xdsl.dialects.builtin import ModuleOp
from xdsl.passes import ModulePass

REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from kernel_gen.passes import lowering as lowering_pkg
from kernel_gen.passes.lowering.nn_lowering import NnLoweringError, NnLoweringPass

nn_lowering_module = importlib.import_module(
    "kernel_gen.passes.lowering.nn_lowering.nn_lowering"
)
element_binary_module = importlib.import_module(
    "kernel_gen.passes.lowering.nn_lowering.element_binary_lowering"
)
dma_structured_module = importlib.import_module(
    "kernel_gen.passes.lowering.nn_lowering.dma_structured_lowering"
)
select_cast_module = importlib.import_module(
    "kernel_gen.passes.lowering.nn_lowering.select_cast_lowering"
)
matmul_img2col_module = importlib.import_module(
    "kernel_gen.passes.lowering.nn_lowering.matmul_img2col_lowering"
)
reduce_softmax_module = importlib.import_module(
    "kernel_gen.passes.lowering.nn_lowering.reduce_softmax_lowering"
)


# TC-PASS-NNL-001
# 创建者: 小李飞刀
# 最后一次更改: jcc你莫辜负
# 最近一次运行测试时间: 2026-04-11 21:10:00 +0800
# 最近一次运行成功时间: 2026-04-11 21:10:00 +0800
# 测试目的: 验证 NnLoweringPass 使用新的公开名字。
# 使用示例: pytest -q test/pass/nn_lowering/public_name.py -k test_nn_lowering_pass_public_name
# 对应功能实现文件路径: kernel_gen/passes/lowering/nn_lowering/nn_lowering.py
# 对应 spec 文件路径: spec/pass/lowering/nn_lowering/spec.md
# 对应测试文件路径: test/pass/nn_lowering/public_name.py
def test_nn_lowering_pass_public_name() -> None:
    pass_obj = NnLoweringPass()
    assert pass_obj.name == "lower-nn"
    assert isinstance(pass_obj, ModulePass)


# TC-PASS-NNL-002
# 创建者: 小李飞刀
# 最后一次更改: jcc你莫辜负
# 最近一次运行测试时间: 2026-04-12 17:40:00 +0800
# 最近一次运行成功时间: 2026-04-12 17:40:00 +0800
# 测试目的: 验证 nn_lowering 以 canonical import 为主，旧 compat 模块失败且 compat 名称不再暴露。
# 使用示例: pytest -q test/pass/nn_lowering/public_name.py -k test_nn_lowering_pass_public_exports
# 对应功能实现文件路径: kernel_gen/passes/lowering/nn_lowering/__init__.py
# 对应 spec 文件路径: spec/pass/lowering/nn_lowering/spec.md
# 对应测试文件路径: test/pass/nn_lowering/public_name.py
def test_nn_lowering_pass_public_exports() -> None:
    assert lowering_pkg.NnLoweringPass is NnLoweringPass
    assert lowering_pkg.NnLoweringError is NnLoweringError
    assert "LowerNnToKernelPass" not in getattr(lowering_pkg, "__all__", [])
    assert "LowerNnToKernelError" not in getattr(lowering_pkg, "__all__", [])
    assert not hasattr(lowering_pkg, "LowerNnToKernelPass")
    assert not hasattr(lowering_pkg, "LowerNnToKernelError")

    with pytest.raises(ModuleNotFoundError):
        importlib.import_module("kernel_gen.passes.lowering.nn_to_kernel")


# TC-PASS-NNL-003
# 创建者: 小李飞刀
# 最后一次更改: 金铲铲大作战
# 测试目的: 验证 nn_lowering pattern driver 的注册顺序，elementwise/compare/select/cast/reduce/softmax 已按单 op pattern 注册，unsupported reject 保持最后。
# 使用示例: pytest -q test/pass/nn_lowering/public_name.py -k test_nn_lowering_patterns_register_reject_last
# 对应功能实现文件路径: kernel_gen/passes/lowering/nn_lowering/nn_lowering.py
# 对应 spec 文件路径: spec/pass/lowering/nn_lowering/spec.md
# 对应测试文件路径: test/pass/nn_lowering/public_name.py
def test_nn_lowering_patterns_register_reject_last() -> None:
    names = [type(pattern).__name__ for pattern in nn_lowering_module.nn_lowering_patterns()]

    assert names == [
        "_LowerNnAddPattern",
        "_LowerNnSubPattern",
        "_LowerNnMulPattern",
        "_LowerNnDivPattern",
        "_LowerNnTrueDivPattern",
        "_LowerNnEqPattern",
        "_LowerNnNePattern",
        "_LowerNnLtPattern",
        "_LowerNnLePattern",
        "_LowerNnGtPattern",
        "_LowerNnGePattern",
        "_LowerSelectPattern",
        "_LowerCastPattern",
        "_LowerExpPattern",
        "_LowerNnBroadcastPattern",
        "_LowerNnTransposePattern",
        "_LowerNnMatmulPattern",
        "_LowerNnImg2col1dPattern",
        "_LowerNnImg2col2dPattern",
        "_LowerNnReduceSumPattern",
        "_LowerNnReduceMinPattern",
        "_LowerNnReduceMaxPattern",
        "_RejectNnSoftmaxPattern",
        "_RejectUnsupportedNnOpPattern",
    ]
    assert "_LowerNnSupportedOpPattern" not in names
    assert "_LowerElementBinaryFamilyPattern" not in names
    assert "_LowerDmaStructuredFamilyPattern" not in names
    assert "_LowerMatmulImg2colFamilyPattern" not in names
    assert "_LowerReduceSoftmaxFamilyPattern" not in names
    assert "_RejectSoftmaxPattern" not in names


# TC-PASS-NNL-003A
# 创建者: jcc你莫辜负
# 最后一次更改: jcc你莫辜负
# 测试目的: 验证 nn_lowering child 模块只暴露 `*_patterns()`，不再保留 `lower_*_family` 兼容导出。
# 使用示例: pytest -q test/pass/nn_lowering/public_name.py -k test_nn_lowering_child_pattern_exports
# 对应功能实现文件路径: kernel_gen/passes/lowering/nn_lowering/*.py
# 对应 spec 文件路径: spec/pass/lowering/nn_lowering/spec.md
# 对应测试文件路径: test/pass/nn_lowering/public_name.py
def test_nn_lowering_child_pattern_exports() -> None:
    assert element_binary_module.__all__ == ["element_binary_patterns"]
    assert dma_structured_module.__all__ == ["dma_structured_patterns"]
    assert select_cast_module.__all__ == ["select_cast_patterns"]
    assert matmul_img2col_module.__all__ == ["matmul_img2col_patterns"]
    assert reduce_softmax_module.__all__ == ["reduce_softmax_patterns"]


# TC-PASS-NNL-004
# 创建者: 小李飞刀
# 最后一次更改: 小李飞刀
# 测试目的: 验证 NnLoweringPass.apply(...) 直接使用 nn_lowering_patterns() 驱动 PatternRewriteWalker。
# 使用示例: pytest -q test/pass/nn_lowering/public_name.py -k test_nn_lowering_apply_uses_pattern_driver
# 对应功能实现文件路径: kernel_gen/passes/lowering/nn_lowering/nn_lowering.py
# 对应 spec 文件路径: spec/pass/lowering/nn_lowering/spec.md
# 对应测试文件路径: test/pass/nn_lowering/public_name.py
def test_nn_lowering_apply_uses_pattern_driver(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: dict[str, object] = {}
    sentinel_pattern = object()

    class FakeApplier:
        def __init__(
            self,
            patterns: list[object],
            ctx: Context | None = None,
            *,
            folding_enabled: bool = False,
            dce_enabled: bool,
        ) -> None:
            calls["patterns"] = patterns
            calls["ctx"] = ctx
            calls["folding_enabled"] = folding_enabled
            calls["dce_enabled"] = dce_enabled

    class FakeWalker:
        def __init__(self, applier: FakeApplier) -> None:
            calls["applier"] = applier

        def rewrite_module(self, module: ModuleOp) -> None:
            calls["module"] = module

    monkeypatch.setattr(nn_lowering_module, "nn_lowering_patterns", lambda: [sentinel_pattern])
    monkeypatch.setattr(nn_lowering_module, "GreedyRewritePatternApplier", FakeApplier)
    monkeypatch.setattr(nn_lowering_module, "PatternRewriteWalker", FakeWalker)

    ctx = Context()
    module = ModuleOp([])
    NnLoweringPass().apply(ctx, module)

    assert calls["patterns"] == [sentinel_pattern]
    assert calls["ctx"] is ctx
    assert calls["folding_enabled"] is True
    assert calls["dce_enabled"] is False
    assert isinstance(calls["applier"], FakeApplier)
    assert calls["module"] is module
