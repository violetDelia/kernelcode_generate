"""emit_c expectation helper runner tests.

创建者: 朽木露琪亚
最后一次更改: 朽木露琪亚

功能说明:
- 覆盖 `kernel_gen.tools.emitc_case_runner` 的 case 解析与源码片段断言行为。
- 锁定当前 `npu_demo` cost expectation 共享 helper 不再依赖缺失的旧目录结构。

使用示例:
- pytest -q test/tools/test_emitc_case_runner.py

关联文件:
- 功能实现: kernel_gen/tools/emitc_case_runner.py
- Spec 文档: spec/dsl/emit_c.md
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


_MEM_TYPE = "!nn.memory<[4], [1], f32, #nn.space<global>>"


# TC-EMITC-CASE-RUNNER-001
# 创建者: 朽木露琪亚
# 最后一次更改: 朽木露琪亚
# 功能说明: 验证 helper 可把 `tuner.cost(kernel.add)` expectation case 执行到 npu_demo 源码文本。
# 使用示例: pytest -q test/tools/test_emitc_case_runner.py -k test_run_emitc_case_lowers_npu_demo_tuner_cost_kernel_add
# 对应功能实现文件路径: kernel_gen/tools/emitc_case_runner.py
# 对应 spec 文件路径: spec/dsl/emit_c.md
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
    %3 = tuner.cost(%0, %1, %2) {{space = #nn.space<global>, cost_kind = "compute", op_name = "kernel.add"}} : ({_MEM_TYPE}, {_MEM_TYPE}, {_MEM_TYPE}) -> !symbol.int<"LOCAL">
    %4 = symbol.add %3, %3 : !symbol.int<"LOCAL">, !symbol.int<"LOCAL"> -> !symbol.int<"LOCAL">
    func.return
  }}
}}"""

    source = run_emitc_case(
        case_text,
        source_path="inline#kernel_add",
        expected_snippets=[
            '#include "include/npu_demo/npu_demo.h"',
            "S_INT cost0 = cost::add<GM, float, float, cost::CostKind::Compute>(arg0 /*out*/, arg1 /*lhs*/, arg2 /*rhs*/);",
            "S_INT v0 = (cost0 + cost0);",
        ],
        forbidden_snippets=[
            "tuner.cost(",
            '"kernel.add"',
        ],
    )

    assert "void cost_add_case(" in source


# TC-EMITC-CASE-RUNNER-002
# 创建者: 朽木露琪亚
# 最后一次更改: 朽木露琪亚
# 功能说明: 验证 helper 只接受当前 expectation 需要的 `--pass no-op` 头部。
# 使用示例: pytest -q test/tools/test_emitc_case_runner.py -k test_run_emitc_case_rejects_unsupported_compile_args
# 对应功能实现文件路径: kernel_gen/tools/emitc_case_runner.py
# 对应 spec 文件路径: spec/dsl/emit_c.md
# 对应测试文件路径: test/tools/test_emitc_case_runner.py
def test_run_emitc_case_rejects_unsupported_compile_args() -> None:
    case_text = """// COMPILE_ARGS: --pass fake-pass

builtin.module {
  func.func @main() {
    func.return
  }
}"""

    with pytest.raises(ValueError, match=r"only supports '// COMPILE_ARGS: --pass no-op'"):
        run_emitc_case(
            case_text,
            source_path="inline#bad_compile_args",
            expected_snippets=["func.return"],
        )
