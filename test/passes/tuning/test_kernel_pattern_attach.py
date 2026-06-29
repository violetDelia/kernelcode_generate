"""kernel-pattern-attach pass public tests.

功能说明:
- 覆盖 `KernelPatternAttachPass` 的公开 dispatcher 生成、多 matmul patternize、no-op 与失败边界。

使用示例:
- pytest -q test/passes/tuning/test_kernel_pattern_attach.py

关联文件:
- 功能实现: kernel_gen/passes/tuning/kernel_pattern_attach.py
- Spec 文档: spec/pass/tuning/kernel_pattern_attach.md
- 测试文件: test/passes/tuning/test_kernel_pattern_attach.py
"""

from __future__ import annotations

from io import StringIO
from pathlib import Path
import sys

import pytest
from xdsl.context import Context
from xdsl.dialects.builtin import ModuleOp
from xdsl.parser import Parser
from xdsl.printer import Printer

REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from kernel_gen.core.context import build_default_context
from kernel_gen.core.error import KernelCodeError
from kernel_gen.passes.tuning.kernel_pattern_attach import KernelPatternAttachPass

_TSM_OUT = "!nn.memory<[#symbol.expr<8>, #symbol.expr<16>], [#symbol.expr<16>, #symbol.expr<1>], f32, #nn.space<tsm>>"
_TSM_LHS = "!nn.memory<[#symbol.expr<8>, #symbol.expr<32>], [#symbol.expr<32>, #symbol.expr<1>], f32, #nn.space<tsm>>"
_TSM_RHS = "!nn.memory<[#symbol.expr<32>, #symbol.expr<16>], [#symbol.expr<16>, #symbol.expr<1>], f32, #nn.space<tsm>>"
_GLOBAL_OUT = "!nn.memory<[#symbol.expr<8>, #symbol.expr<16>], [#symbol.expr<16>, #symbol.expr<1>], f32, #nn.space<global>>"
_GLOBAL_LHS = "!nn.memory<[#symbol.expr<8>, #symbol.expr<32>], [#symbol.expr<32>, #symbol.expr<1>], f32, #nn.space<global>>"
_GLOBAL_RHS = "!nn.memory<[#symbol.expr<32>, #symbol.expr<16>], [#symbol.expr<16>, #symbol.expr<1>], f32, #nn.space<global>>"
_TLM1_TLM1_PIPELINE = '--pass "lower-dma-memory-hierarchy={fold=true,apply_op=matmul{[\\"\\", \\"tlm1\\", \\"tlm1\\"]}}" --pass canonicalize'


def _parse_module(text: str) -> ModuleOp:
    """解析 kernel-pattern-attach 测试 IR。

    功能说明:
    - 使用仓库默认公开 context，确保 kernel/nn/symbol/tuner dialect 均按公开入口加载。

    使用示例:
    - module = _parse_module("builtin.module {...}")
    """

    return Parser(build_default_context(), text).parse_module()


def _print_ir(module: ModuleOp) -> str:
    """打印 module 为稳定文本。

    功能说明:
    - 只通过公开 printer 观察 pass 输出，不直连内部 helper。

    使用示例:
    - text = _print_ir(module)
    """

    stream = StringIO()
    Printer(stream=stream).print_op(module)
    return stream.getvalue()


def _matmul_func(name: str, *, entry_point: bool, space: str = "tsm") -> str:
    """构造 kernel.matmul 测试函数。

    功能说明:
    - `space="tsm"` 生成合格 pattern 输入，`space="global"` 生成 no-op 输入。

    使用示例:
    - text = _matmul_func("entry", entry_point=True)
    """

    attrs = " attributes {entry_point}" if entry_point else ""
    out_type = _TSM_OUT if space == "tsm" else _GLOBAL_OUT
    lhs_type = _TSM_LHS if space == "tsm" else _GLOBAL_LHS
    rhs_type = _TSM_RHS if space == "tsm" else _GLOBAL_RHS
    return f"""
  func.func @{name}(%out : {out_type}, %lhs : {lhs_type}, %rhs : {rhs_type}){attrs} {{
    "kernel.matmul"(%out, %lhs, %rhs) {{space = #nn.space<{space}>}} : ({out_type}, {lhs_type}, {rhs_type}) -> ()
    func.return
  }}
"""


def test_kernel_pattern_attach_generates_dispatcher_and_two_patterns() -> None:
    module = _parse_module(f"builtin.module {{{_matmul_func('matmul_entry', entry_point=True)}}}")

    KernelPatternAttachPass().apply(Context(), module)
    text = _print_ir(module)

    assert "func.func @matmul_entry(" in text
    assert "attributes {entry_point}" in text
    assert "tuner.select args(%out, %lhs, %rhs) {patterns = [@matmul_entry_pattern0, @matmul_entry_pattern1]}" in text
    assert "tuner_args(" not in text
    assert "tuner.launch(@matmul_entry_pattern0" in text
    assert "tuner.launch(@matmul_entry_pattern1" in text
    assert "func.func @matmul_entry_pattern0" in text
    assert "func.func @matmul_entry_pattern1" in text
    assert "kernel.pattern_id = #builtin.int<0>" in text
    assert "kernel.pattern_id = #builtin.int<1>" in text
    assert "lower-dma-memory-hierarchy" in text
    assert "tuner.pattern_ref" not in text


def test_kernel_pattern_attach_can_generate_single_pattern_dispatcher() -> None:
    module = _parse_module(f"builtin.module {{{_matmul_func('matmul_entry', entry_point=True)}}}")

    KernelPatternAttachPass(pattern_pipelines=(_TLM1_TLM1_PIPELINE,)).apply(Context(), module)
    text = _print_ir(module)

    assert "func.func @matmul_entry(" in text
    assert "attributes {entry_point}" in text
    assert "tuner.select" not in text
    assert "scf.if" not in text
    assert "tuner.launch(@matmul_entry_pattern0" in text
    assert "tuner.launch(@matmul_entry_pattern1" not in text
    assert "func.func @matmul_entry_pattern0" in text
    assert "func.func @matmul_entry_pattern1" not in text
    assert "kernel.pattern_id = #builtin.int<0>" in text
    assert "kernel.pattern_id = #builtin.int<1>" not in text
    assert "kernel.transform_pipeline" in text
    assert text.count("tlm1") == 2
    assert "tlm2" not in text


def test_kernel_pattern_attach_generates_patterns_for_nested_matmul() -> None:
    """验证 entry 内嵌套 region 的合格 matmul 也会生成 pattern。

    功能说明:
    - 通过公开 `KernelPatternAttachPass.apply(...)` 覆盖 npu-demo-lowering 中 loop body matmul 的实际形态。
    - 断言 host 变为 dispatcher，pattern body 保留嵌套 `kernel.matmul`。

    使用示例:
    - pytest -q test/passes/tuning/test_kernel_pattern_attach.py -k nested_matmul
    """

    module = _parse_module(
        f"""
builtin.module {{
  func.func @matmul_entry(%out : {_TSM_OUT}, %lhs : {_TSM_LHS}, %rhs : {_TSM_RHS}, %cond : i1) attributes {{entry_point}} {{
    scf.if %cond {{
      "kernel.matmul"(%out, %lhs, %rhs) {{space = #nn.space<tsm>}} : ({_TSM_OUT}, {_TSM_LHS}, {_TSM_RHS}) -> ()
    }}
    func.return
  }}
}}
"""
    )

    KernelPatternAttachPass().apply(Context(), module)
    text = _print_ir(module)

    assert "tuner.select args(%out, %lhs, %rhs, %cond) {patterns = [@matmul_entry_pattern0, @matmul_entry_pattern1]}" in text
    assert "tuner_args(" not in text
    assert "func.func @matmul_entry_pattern0" in text
    assert "func.func @matmul_entry_pattern1" in text
    assert text.count('"kernel.matmul"') == 2
    assert "tuner.pattern_ref" not in text


def test_kernel_pattern_attach_no_ops_without_tsm_matmul() -> None:
    module = _parse_module(f"builtin.module {{{_matmul_func('entry', entry_point=True, space='global')}}}")
    before = _print_ir(module)

    KernelPatternAttachPass().apply(Context(), module)

    assert _print_ir(module) == before


def test_kernel_pattern_attach_rejects_missing_entry_and_unknown_options() -> None:
    module = _parse_module(f"builtin.module {{{_matmul_func('matmul_entry', entry_point=False)}}}")

    with pytest.raises(KernelCodeError, match="kernel-pattern-attach entry_point must be exactly one"):
        KernelPatternAttachPass().apply(Context(), module)

    with pytest.raises(KernelCodeError, match="kernel-pattern-attach options unknown: extra"):
        KernelPatternAttachPass.from_options({"extra": "1"})

    with pytest.raises(KernelCodeError, match="kernel-pattern-attach pattern_pipelines must be non-empty"):
        KernelPatternAttachPass(pattern_pipelines=())

    with pytest.raises(KernelCodeError, match="kernel-pattern-attach pattern_pipelines supports at most two patterns"):
        KernelPatternAttachPass(pattern_pipelines=("a", "b", "c"))


def test_kernel_pattern_attach_patterns_multiple_eligible_matmul() -> None:
    module = _parse_module(
        f"""
builtin.module {{
  func.func @matmul_entry(%out : {_TSM_OUT}, %lhs : {_TSM_LHS}, %rhs : {_TSM_RHS}) attributes {{entry_point}} {{
    "kernel.matmul"(%out, %lhs, %rhs) {{space = #nn.space<tsm>}} : ({_TSM_OUT}, {_TSM_LHS}, {_TSM_RHS}) -> ()
    "kernel.matmul"(%out, %lhs, %rhs) {{space = #nn.space<tsm>}} : ({_TSM_OUT}, {_TSM_LHS}, {_TSM_RHS}) -> ()
    func.return
  }}
}}
"""
    )

    KernelPatternAttachPass().apply(Context(), module)
    text = _print_ir(module)

    assert "tuner.select args(%out, %lhs, %rhs) {patterns = [@matmul_entry_pattern0, @matmul_entry_pattern1]}" in text
    assert "tuner_args(" not in text
    assert "func.func @matmul_entry_pattern0" in text
    assert "func.func @matmul_entry_pattern1" in text
    assert text.count('"kernel.matmul"') == 4
    assert "tuner.pattern_ref" not in text
