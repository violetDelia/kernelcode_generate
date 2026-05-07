"""emit_c expectation helper runner tests.


功能说明:
- 覆盖 `kernel_gen.tools.emitc_case_runner` 的 case 解析与源码片段断言行为。
- 锁定当前 `npu_demo` cost expectation 共享 helper 不再依赖缺失的旧目录结构。

使用示例:
- pytest -q test/tools/test_emitc_case_runner.py

关联文件:
- 功能实现: kernel_gen/tools/emitc_case_runner.py
- Spec 文档: spec/tools/emitc_case_runner.md
- 测试文件: test/tools/test_emitc_case_runner.py
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from kernel_gen.tools.emitc_case_runner import run_emitc_case


_MEM_TYPE = "!nn.memory<[#symbol.expr<4>], [#symbol.expr<1>], f32, #nn.space<global>>"


# TC-EMITC-CASE-RUNNER-001
# 功能说明: 验证 helper 可把 `tuner.cost(kernel.add)` expectation case 执行到 npu_demo 源码文本。
# 使用示例: pytest -q test/tools/test_emitc_case_runner.py -k test_run_emitc_case_lowers_npu_demo_tuner_cost_kernel_add
# 对应功能实现文件路径: kernel_gen/tools/emitc_case_runner.py
# 对应 spec 文件路径: spec/tools/emitc_case_runner.md
# 对应测试文件路径: test/tools/test_emitc_case_runner.py
def test_run_emitc_case_lowers_npu_demo_tuner_cost_kernel_add() -> None:
    case_text = f"""// COMPILE_ARGS: --pass no-op
// CHECK: void cost_add_case(

builtin.module {{
  func.func @cost_add_case(
    %0 : {_MEM_TYPE},
    %1 : {_MEM_TYPE},
    %2 : {_MEM_TYPE}
  ) {{
    %3 = tuner.cost(%0, %1, %2) {{space = #nn.space<global>, cost_kind = "VECTOR1", op_name = "kernel.add"}} : ({_MEM_TYPE}, {_MEM_TYPE}, {_MEM_TYPE}) -> !symbol.int<#symbol.expr<LOCAL>>
    %4 = symbol.add %3, %3 : !symbol.int<#symbol.expr<LOCAL>>, !symbol.int<#symbol.expr<LOCAL>> -> !symbol.int<#symbol.expr<LOCAL>>
    func.return
  }}
}}"""

    source = run_emitc_case(
        case_text,
        source_path="inline#kernel_add",
        expected_snippets=[
            '#include "include/npu_demo/npu_demo.h"',
            "S_INT cost0 = cost::add<GM, float, float, VECTOR1>(arg0 /*out*/, arg1 /*lhs*/, arg2 /*rhs*/);",
            "S_INT v0 = (cost0 + cost0);",
        ],
        forbidden_snippets=[
            "tuner.cost(",
            '"kernel.add"',
        ],
    )

    assert "void cost_add_case(" in source


# TC-EMITC-CASE-RUNNER-002
# 功能说明: 验证 helper 只接受当前 expectation 需要的最小 `COMPILE_ARGS` 集合。
# 使用示例: pytest -q test/tools/test_emitc_case_runner.py -k test_run_emitc_case_rejects_unsupported_compile_args
# 对应功能实现文件路径: kernel_gen/tools/emitc_case_runner.py
# 对应 spec 文件路径: spec/tools/emitc_case_runner.md
# 对应测试文件路径: test/tools/test_emitc_case_runner.py
def test_run_emitc_case_rejects_unsupported_compile_args() -> None:
    case_text = """// COMPILE_ARGS: --pass fake-pass

builtin.module {
  func.func @main() {
    func.return
  }
}"""

    with pytest.raises(
        ValueError,
        match=r"only supports '// COMPILE_ARGS: --pass no-op' or '// COMPILE_ARGS: --pass buffer-results-to-out-params'",
    ):
        run_emitc_case(
            case_text,
            source_path="inline#bad_compile_args",
            expected_snippets=["func.return"],
        )


# TC-EMITC-CASE-RUNNER-003
# 功能说明: 验证 helper 可执行不带 `arch.launch` wrapper 的 npu_demo plain symbol module。
# 使用示例: pytest -q test/tools/test_emitc_case_runner.py -k test_run_emitc_case_lowers_plain_symbol_cast_module_without_launch_wrapper
# 对应功能实现文件路径: kernel_gen/tools/emitc_case_runner.py
# 对应 spec 文件路径: spec/tools/emitc_case_runner.md
# 对应测试文件路径: test/tools/test_emitc_case_runner.py
def test_run_emitc_case_lowers_plain_symbol_cast_module_without_launch_wrapper() -> None:
    case_text = """// COMPILE_ARGS: --pass no-op
// CHECK: void symbol_cast_case() {

builtin.module {
  func.func @symbol_cast_case() {
    %0 = symbol.const 9 : !symbol.int<#symbol.expr<9>>
    %1 = "symbol.cast"(%0) : (!symbol.int<#symbol.expr<9>>) -> i32
    func.return
  }
}"""

    source = run_emitc_case(
        case_text,
        source_path="inline#plain_symbol_cast",
        op_name="symbol.cast",
        expected_snippets=[
            "void symbol_cast_case()",
            "S_INT c_0 = 9;",
            "int32_t c_0_cast_int32_t = c_0;",
        ],
        forbidden_snippets=["launch<", "arch.launch"],
    )

    assert "void symbol_cast_case()" in source


# TC-EMITC-CASE-RUNNER-003A
# 功能说明: 验证 helper 可执行不带 `arch.launch` wrapper 的 npu_demo return-only plain module。
# 使用示例: pytest -q test/tools/test_emitc_case_runner.py -k test_run_emitc_case_lowers_return_only_plain_module_without_launch_wrapper
# 对应功能实现文件路径: kernel_gen/tools/emitc_case_runner.py
# 对应 spec 文件路径: spec/tools/emitc_case_runner.md
# 对应测试文件路径: test/tools/test_emitc_case_runner.py
def test_run_emitc_case_lowers_return_only_plain_module_without_launch_wrapper() -> None:
    case_text = """// COMPILE_ARGS: --pass no-op
// CHECK: void npu_demo_header_case() {

builtin.module {
  func.func @npu_demo_header_case() {
    func.return
  }
}"""

    source = run_emitc_case(
        case_text,
        source_path="inline#plain_return_only_module",
        op_name="npu_demo.header",
        expected_snippets=[
            '#include "include/npu_demo/npu_demo.h"',
            "using namespace npu_demo;",
            "void npu_demo_header_case()",
        ],
        forbidden_snippets=["launch<", "arch.launch"],
    )

    assert "void npu_demo_header_case()" in source


# TC-EMITC-CASE-RUNNER-004
# 功能说明: 验证 helper 支持 `--pass buffer-results-to-out-params` 预处理后再发射 `dma.cast`。
# 使用示例: pytest -q test/tools/test_emitc_case_runner.py -k test_run_emitc_case_applies_buffer_results_to_out_params_before_emit_c
# 对应功能实现文件路径: kernel_gen/tools/emitc_case_runner.py
# 对应 spec 文件路径: spec/tools/emitc_case_runner.md
# 对应测试文件路径: test/tools/test_emitc_case_runner.py
def test_run_emitc_case_applies_buffer_results_to_out_params_before_emit_c() -> None:
    case_text = """// COMPILE_ARGS: --pass buffer-results-to-out-params

builtin.module {
  func.func @dma_cast_case(%0 : !nn.memory<[#symbol.expr<2>, #symbol.expr<3>], [#symbol.expr<3>, #symbol.expr<1>], f32, #nn.space<global>>) -> !nn.memory<[#symbol.expr<2>, #symbol.expr<3>], [#symbol.expr<3>, #symbol.expr<1>], i32, #nn.space<global>> {
    %1 = "dma.cast"(%0) : (!nn.memory<[#symbol.expr<2>, #symbol.expr<3>], [#symbol.expr<3>, #symbol.expr<1>], f32, #nn.space<global>>) -> !nn.memory<[#symbol.expr<2>, #symbol.expr<3>], [#symbol.expr<3>, #symbol.expr<1>], i32, #nn.space<global>>
    func.return %1 : !nn.memory<[#symbol.expr<2>, #symbol.expr<3>], [#symbol.expr<3>, #symbol.expr<1>], i32, #nn.space<global>>
  }
}"""

    source = run_emitc_case(
        case_text,
        source_path="inline#dma_cast_buffer_results",
        op_name="dma.cast",
        expected_snippets=["cast<GM, int32_t, float>(arg0 /*dst*/, arg1 /*source*/);"],
        forbidden_snippets=["dma.cast"],
    )

    assert "void dma_cast_case(Memory<GM, int32_t>& arg0, Memory<GM, float>& arg1)" in source


# TC-EMITC-CASE-RUNNER-005
# 功能说明: 验证 helper 允许“只校验 forbidden_snippets”的 expectation 合同。
# 使用示例: pytest -q test/tools/test_emitc_case_runner.py -k test_run_emitc_case_allows_forbidden_only_contract
# 对应功能实现文件路径: kernel_gen/tools/emitc_case_runner.py
# 对应 spec 文件路径: spec/tools/emitc_case_runner.md
# 对应测试文件路径: test/tools/test_emitc_case_runner.py
def test_run_emitc_case_allows_forbidden_only_contract() -> None:
    case_text = """// COMPILE_ARGS: --pass no-op

builtin.module {
  func.func @kernel_exp_case(
    %0 : !nn.memory<[#symbol.expr<2>, #symbol.expr<3>], [#symbol.expr<3>, #symbol.expr<1>], f32, #nn.space<global>>,
    %1 : !nn.memory<[#symbol.expr<2>, #symbol.expr<3>], [#symbol.expr<3>, #symbol.expr<1>], f32, #nn.space<global>>
  ) {
    "kernel.exp"(%1, %0) {space = #nn.space<global>} : (!nn.memory<[#symbol.expr<2>, #symbol.expr<3>], [#symbol.expr<3>, #symbol.expr<1>], f32, #nn.space<global>>, !nn.memory<[#symbol.expr<2>, #symbol.expr<3>], [#symbol.expr<3>, #symbol.expr<1>], f32, #nn.space<global>>) -> ()
    func.return
  }
}"""

    source = run_emitc_case(
        case_text,
        source_path="inline#kernel_exp_forbidden_only",
        op_name="kernel.exp",
        expected_snippets=[],
        forbidden_snippets=["kernel.exp"],
    )

    assert "exp<GM, float, float>(arg0 /*out*/, arg1 /*input*/);" in source
