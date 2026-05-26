"""symbol-hoist-pipeline pass tests.

功能说明:
- 覆盖 `symbol-hoist-pipeline` 的公开 pass class、registry、旧路径删除与组合 pattern 行为。
- 测试只通过公开 pass / registry / ircheck API 观察行为，不直连文件内 helper。

使用示例:
- pytest -q test/passes/test_symbol_hoist_pipeline.py

关联文件:
- spec: spec/pass/symbol_hoist_pipeline.md
- 功能实现: kernel_gen/passes/hoist/symbol_hoist_pipeline.py
- 测试文件: test/passes/test_symbol_hoist_pipeline.py
"""

from __future__ import annotations

import importlib

import pytest

from kernel_gen.core.error import KernelCodeError
from kernel_gen.passes.registry import build_registered_pass, load_builtin_passes
from kernel_gen.tools.ircheck import run_ircheck_text

pass_module = importlib.import_module("kernel_gen.passes.hoist.symbol_hoist_pipeline")
SymbolHoistPipelinePass = pass_module.SymbolHoistPipelinePass


def _run_public_ircheck_case(case_text: str) -> str:
    """运行公开 ircheck inline case。

    功能说明:
    - 只调用公开 `run_ircheck_text(...)`。
    - 返回 actual IR 供测试补充检查组合 pass 的可观察改写。

    使用示例:
    - actual_ir = _run_public_ircheck_case(case_text)
    """

    result = run_ircheck_text(case_text, source_path="test/passes/test_symbol_hoist_pipeline.py:inline")
    message = result.message
    actual_ir = result.actual_ir
    assert result.ok is True, message
    assert result.exit_code == 0
    return actual_ir


def test_symbol_hoist_pipeline_registry_and_public_path() -> None:
    """验证 `symbol-hoist-pipeline` 公开 registry 和 module path。

    功能说明:
    - 通过 registry 构造 `fold=false` pass。
    - 锁定新 canonical module path。

    使用示例:
    - pytest -q test/passes/test_symbol_hoist_pipeline.py -k registry_and_public_path
    """

    load_builtin_passes()

    pass_obj = build_registered_pass("symbol-hoist-pipeline", {"fold": "false"})

    assert isinstance(pass_obj, SymbolHoistPipelinePass)
    assert pass_obj.name == "symbol-hoist-pipeline"
    assert pass_obj.fold is False
    assert pass_obj.__class__.__module__ == "kernel_gen.passes.hoist.symbol_hoist_pipeline"


def test_symbol_hoist_pipeline_rejects_private_options() -> None:
    """验证 `symbol-hoist-pipeline` 不接受专属 option。

    功能说明:
    - 当前公开 API 只承接 registry 通用 `fold`。
    - 未确认的 `hoist-ops` option 必须按 registry 稳定错误失败。

    使用示例:
    - pytest -q test/passes/test_symbol_hoist_pipeline.py -k rejects_private_options
    """

    load_builtin_passes()

    with pytest.raises(
        KernelCodeError,
        match=r"^PassRegistryError: pass 'symbol-hoist-pipeline' does not accept options$",
    ):
        build_registered_pass("symbol-hoist-pipeline", {"hoist-ops": "dma.fill"})


def test_symbol_hoist_pipeline_combines_reinterpret_and_loop_hoist() -> None:
    """验证组合 pass 同时包含 alias 归一和 symbol loop hoist 能力。

    功能说明:
    - 输入在 `symbol.for` 内包含 `dma.view` 和 loop-invariant `symbol.add`。
    - 输出必须先把 alias 归一为 `dma.reinterpret`，并把可外提 op 移到 loop 前。

    使用示例:
    - pytest -q test/passes/test_symbol_hoist_pipeline.py -k combines_reinterpret
    """

    actual_ir = _run_public_ircheck_case(
        """// COMPILE_ARGS: --pass "symbol-hoist-pipeline={fold=false}"
// CHECK: func.func @combined_reinterpret_and_symbol_hoist
// CHECK: %[[ALIAS:.*]] = "dma.reinterpret"
// CHECK: %[[ADD:.*]] = symbol.add
// CHECK: symbol.for
// CHECK: "dma.deslice"
// CHECK-NOT: "dma.view"

builtin.module {
  func.func @combined_reinterpret_and_symbol_hoist(
      %src : !nn.memory<[#symbol.expr<8>, #symbol.expr<8>], [#symbol.expr<8>, #symbol.expr<1>], f32, #nn.space<global>>,
      %dst : !nn.memory<[#symbol.expr<2>, #symbol.expr<4>], [#symbol.expr<4>, #symbol.expr<1>], f32, #nn.space<tsm>>) {
    %c0 = symbol.const 0 : !symbol.int<#symbol.expr<0>>
    %c1 = symbol.const 1 : !symbol.int<#symbol.expr<1>>
    %c2 = symbol.const 2 : !symbol.int<#symbol.expr<2>>
    %c4 = symbol.const 4 : !symbol.int<#symbol.expr<4>>
    %c8 = symbol.const 8 : !symbol.int<#symbol.expr<8>>
    symbol.for %i = %c0 to %c8 step %c1 {iter = #symbol.iter<start = #symbol.expr<0>, end = #symbol.expr<8>, step = #symbol.expr<1>>} {
      %sum = symbol.add %c2, %c4 : !symbol.int<#symbol.expr<2>>, !symbol.int<#symbol.expr<4>> -> !symbol.int<#symbol.expr<2+4>>
      %view = "dma.view"(%src, %c0, %c0, %c2, %c4, %c1, %c1) <{operandSegmentSizes = array<i32: 1, 2, 2, 2>}> : (!nn.memory<[#symbol.expr<8>, #symbol.expr<8>], [#symbol.expr<8>, #symbol.expr<1>], f32, #nn.space<global>>, !symbol.int<#symbol.expr<0>>, !symbol.int<#symbol.expr<0>>, !symbol.int<#symbol.expr<2>>, !symbol.int<#symbol.expr<4>>, !symbol.int<#symbol.expr<1>>, !symbol.int<#symbol.expr<1>>) -> !nn.memory<[#symbol.expr<2>, #symbol.expr<4>], [#symbol.expr<8>, #symbol.expr<1>], f32, #nn.space<global>>
      "dma.deslice"(%dst, %view, %c0, %c0, %c2, %c4, %c1, %c1) <{operandSegmentSizes = array<i32: 1, 1, 2, 2, 2>}> : (!nn.memory<[#symbol.expr<2>, #symbol.expr<4>], [#symbol.expr<4>, #symbol.expr<1>], f32, #nn.space<tsm>>, !nn.memory<[#symbol.expr<2>, #symbol.expr<4>], [#symbol.expr<8>, #symbol.expr<1>], f32, #nn.space<global>>, !symbol.int<#symbol.expr<0>>, !symbol.int<#symbol.expr<0>>, !symbol.int<#symbol.expr<2>>, !symbol.int<#symbol.expr<4>>, !symbol.int<#symbol.expr<1>>, !symbol.int<#symbol.expr<1>>) -> !nn.memory<[#symbol.expr<2>, #symbol.expr<4>], [#symbol.expr<4>, #symbol.expr<1>], f32, #nn.space<tsm>>
    }
    func.return
  }
}
"""
    )

    assert '"dma.view"' not in actual_ir
    assert actual_ir.index("symbol.add") < actual_ir.index("symbol.for")
    assert actual_ir.index('"dma.reinterpret"') < actual_ir.index("symbol.for")
