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
from xdsl.dialects import func
from xdsl.context import Context
from xdsl.dialects.builtin import ArrayAttr, FunctionType, IntAttr, ModuleOp, Region, StringAttr, i32
from xdsl.ir import Attribute, Block
from xdsl.passes import ModulePass
from xdsl.pattern_rewriter import PatternRewriter, RewritePattern, op_type_rewrite_pattern

REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from kernel_gen.core.error import KernelCodeError
from kernel_gen.dialect.nn import NnAddOp, NnMemorySpaceAttr, NnMemoryType
from kernel_gen.passes import lowering as lowering_pkg
from kernel_gen.passes.lowering.nn_lowering import (
    NnLoweringPass,
    nn_lowering_patterns,
)

nn_lowering_pkg = importlib.import_module("kernel_gen.passes.lowering.nn_lowering")
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

SPACE_GLOBAL = NnMemorySpaceAttr(StringAttr("global"))


def _nn_memory_type(
    shape: tuple[Attribute, ...],
    stride: tuple[Attribute, ...],
) -> NnMemoryType:
    return NnMemoryType(ArrayAttr(list(shape)), ArrayAttr(list(stride)), i32, SPACE_GLOBAL)


def _build_add_module() -> ModuleOp:
    lhs_type = _nn_memory_type((IntAttr(2), IntAttr(2)), (IntAttr(2), IntAttr(1)))
    rhs_type = _nn_memory_type((IntAttr(2), IntAttr(2)), (IntAttr(2), IntAttr(1)))
    result_type = _nn_memory_type((IntAttr(2), IntAttr(2)), (IntAttr(2), IntAttr(1)))
    block = Block(arg_types=[lhs_type, rhs_type])
    add_op = NnAddOp(block.args[0], block.args[1], result_type, SPACE_GLOBAL)
    block.add_op(add_op)
    block.add_op(func.ReturnOp(add_op.results[0]))
    func_op = func.FuncOp(
        "add",
        FunctionType.from_lists([lhs_type, rhs_type], [result_type]),
        Region(block),
    )
    return ModuleOp([func_op])


# TC-PASS-NNL-001
# 创建者: 小李飞刀
# 最后一次更改: 金铲铲大作战
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
    assert nn_lowering_pkg.NnLoweringPass is NnLoweringPass
    assert getattr(nn_lowering_pkg, "nn_lowering_patterns", None) is nn_lowering_patterns
    assert not hasattr(lowering_pkg, "LowerNnToKernelPass")
    assert not hasattr(lowering_pkg, "LowerNnToKernelError")
    assert not hasattr(nn_lowering_pkg, "LowerNnToKernelPass")
    assert not hasattr(nn_lowering_pkg, "LowerNnToKernelError")

    with pytest.raises(ModuleNotFoundError):
        importlib.import_module("kernel_gen.passes.lowering.nn_to_kernel")


# TC-PASS-NNL-003
# 创建者: 小李飞刀
# 最后一次更改: 朽木露琪亚
# 测试目的: 验证 nn_lowering pattern driver 通过各 child 模块公开 `*_patterns()` 顺序组合，且最后保留 reject 兜底模式。
# 使用示例: pytest -q test/pass/nn_lowering/public_name.py -k test_nn_lowering_patterns_compose_public_family_exports
# 对应功能实现文件路径: kernel_gen/passes/lowering/nn_lowering/__init__.py
# 对应 spec 文件路径: spec/pass/lowering/nn_lowering/spec.md
# 对应测试文件路径: test/pass/nn_lowering/public_name.py
def test_nn_lowering_patterns_compose_public_family_exports(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class _TokenPattern(RewritePattern):
        @op_type_rewrite_pattern
        def match_and_rewrite(self, op: NnAddOp, rewriter: PatternRewriter, /) -> None:
            _ = op
            _ = rewriter

    element_token = _TokenPattern()
    select_token = _TokenPattern()
    dma_token = _TokenPattern()
    matmul_token = _TokenPattern()
    reduce_token = _TokenPattern()

    monkeypatch.setattr(element_binary_module, "element_binary_patterns", lambda: [element_token])
    monkeypatch.setattr(select_cast_module, "select_cast_patterns", lambda: [select_token])
    monkeypatch.setattr(dma_structured_module, "dma_structured_patterns", lambda: [dma_token])
    monkeypatch.setattr(matmul_img2col_module, "matmul_img2col_patterns", lambda: [matmul_token])
    monkeypatch.setattr(reduce_softmax_module, "reduce_softmax_patterns", lambda: [reduce_token])

    patterns = nn_lowering_patterns()

    assert patterns[:-1] == [element_token, select_token, dma_token, matmul_token, reduce_token]
    assert len(patterns) == 6
    assert isinstance(patterns[-1], RewritePattern)
    assert patterns[-1] not in {element_token, select_token, dma_token, matmul_token, reduce_token}


# TC-PASS-NNL-003A
# 创建者: jcc你莫辜负
# 最后一次更改: 金铲铲大作战
# 测试目的: 验证 nn_lowering child 模块只暴露 `*_patterns()`，不再保留 `lower_*_family` 兼容导出。
# 使用示例: pytest -q test/pass/nn_lowering/public_name.py -k test_nn_lowering_child_pattern_exports
# 对应功能实现文件路径: kernel_gen/passes/lowering/nn_lowering/*.py
# 对应 spec 文件路径: spec/pass/lowering/nn_lowering/spec.md
# 对应测试文件路径: test/pass/nn_lowering/public_name.py
def test_nn_lowering_child_pattern_exports() -> None:
    assert callable(getattr(element_binary_module, "element_binary_patterns", None))
    assert callable(getattr(dma_structured_module, "dma_structured_patterns", None))
    assert callable(getattr(select_cast_module, "select_cast_patterns", None))
    assert callable(getattr(matmul_img2col_module, "matmul_img2col_patterns", None))
    assert callable(getattr(reduce_softmax_module, "reduce_softmax_patterns", None))
    assert not hasattr(element_binary_module, "lower_element_binary_family")
    assert not hasattr(dma_structured_module, "lower_dma_structured_family")
    assert not hasattr(select_cast_module, "lower_select_cast_family")
    assert not hasattr(matmul_img2col_module, "lower_matmul_img2col_family")
    assert not hasattr(reduce_softmax_module, "lower_reduce_softmax_family")


# TC-PASS-NNL-004
# 创建者: 小李飞刀
# 最后一次更改: jcc你莫辜负
# 测试目的: 验证 NnLoweringPass.apply(...) 必须直接消费公开 `nn_lowering_patterns()` driver。
# 使用示例: pytest -q test/pass/nn_lowering/public_name.py -k test_nn_lowering_apply_uses_pattern_driver
# 对应功能实现文件路径: kernel_gen/passes/lowering/nn_lowering/__init__.py
# 对应 spec 文件路径: spec/pass/lowering/nn_lowering/spec.md
# 对应测试文件路径: test/pass/nn_lowering/public_name.py
def test_nn_lowering_apply_uses_pattern_driver(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class _PatternDriverSentinel(RuntimeError):
        pass

    class _ExplodeOnAddPattern(RewritePattern):
        @op_type_rewrite_pattern
        def match_and_rewrite(self, op: NnAddOp, rewriter: PatternRewriter, /) -> None:
            _ = op
            _ = rewriter
            raise _PatternDriverSentinel("public nn_lowering_patterns driver reached apply")

    monkeypatch.setattr(nn_lowering_pkg, "nn_lowering_patterns", lambda: [_ExplodeOnAddPattern()])

    module = _build_add_module()
    with pytest.raises(_PatternDriverSentinel, match="public nn_lowering_patterns driver reached apply"):
        NnLoweringPass().apply(Context(), module)
