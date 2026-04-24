# [immutable-file]
"""`buffer_results_to_out_params` multi output ircheck expectation。

创建者: 守护最好的爱莉希雅
最后一次更改: 守护最好的爱莉希雅

功能说明:
- 使用 `ircheck` 黑盒锁定 `BufferResultsToOutParamsPass` 对多个 memory outputs 的
  固定改写顺序。
- 覆盖静态/动态 shape，并对 output 的 shape/type/space 做随机化，避免 case 长期
  固定在同一组 `i32/global/[2,3]` 文本。

使用示例:
- `PYTHONPATH=. python expectation/pass/buffer_results_to_out_params/multi_output.py`

关联文件:
- spec: [`spec/pass/lowering/buffer_results_to_out_params.md`](../../../spec/pass/lowering/buffer_results_to_out_params.md)
- spec: [`spec/tools/ircheck.md`](../../../spec/tools/ircheck.md)
- test: [`test/pass/test_buffer_results_to_out_params.py`](../../../test/pass/test_buffer_results_to_out_params.py)
- 功能实现: [`expectation/pass/buffer_results_to_out_params/multi_output.py`](../../../expectation/pass/buffer_results_to_out_params/multi_output.py)
- 功能实现: [`kernel_gen/passes/lowering/buffer_results_to_out_params.py`](../../../kernel_gen/passes/lowering/buffer_results_to_out_params.py)
"""

from __future__ import annotations

from pathlib import Path
import sys

REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
CURRENT_DIR = Path(__file__).resolve().parent
if str(CURRENT_DIR) not in sys.path:
    sys.path.insert(0, str(CURRENT_DIR))

from _shared import (
    print_case_actual_ir,
    random_dynamic_memory_spec,
    random_rank,
    random_static_memory_spec,
)
from expectation.utils.case_runner import raise_if_failures, run_case
from kernel_gen.tools.ircheck import run_ircheck_text

STATIC_LHS = random_static_memory_spec("lhs", rank=random_rank())
STATIC_RHS = random_static_memory_spec("rhs", rank=random_rank())
DYNAMIC_LHS = random_dynamic_memory_spec("lhs", rank=random_rank())
DYNAMIC_RHS = random_dynamic_memory_spec("rhs", rank=random_rank())
STATIC_THIRD = random_static_memory_spec("extra", rank=random_rank())
DYNAMIC_THIRD = random_dynamic_memory_spec("extra", rank=random_rank())

CASE_TEXT = f"""// COMPILE_ARGS: --pass buffer-results-to-out-params
// CASE: case-multi-output-static: 多个静态 memory outputs 固定重写成前置 arg0/arg1，caller 同步改写。
// CHECK: builtin.module {{
// CHECK-NEXT: func.func @split(%0: {STATIC_LHS.type_ir} {{name = "arg0"}}, %1: {STATIC_RHS.type_ir} {{name = "arg1"}}, %2: {STATIC_LHS.type_ir} {{name = "lhs"}}, %3: {STATIC_RHS.type_ir} {{name = "rhs"}}) {{
// CHECK-NEXT: func.return
// CHECK-NEXT: }}
// CHECK-NEXT: func.func @caller(%0: {STATIC_LHS.type_ir} {{name = "lhs"}}, %1: {STATIC_RHS.type_ir} {{name = "rhs"}}) {{
// CHECK-NEXT: %2 = "dma.alloc"() <{{operandSegmentSizes = array<i32: 0>}}> : () -> {STATIC_LHS.type_ir}
// CHECK-NEXT: %3 = "dma.alloc"() <{{operandSegmentSizes = array<i32: 0>}}> : () -> {STATIC_RHS.type_ir}
// CHECK-NEXT: func.call @split(%2, %3, %0, %1) : ({STATIC_LHS.type_ir}, {STATIC_RHS.type_ir}, {STATIC_LHS.type_ir}, {STATIC_RHS.type_ir}) -> ()
// CHECK-NEXT: func.return
// CHECK-NEXT: }}
// CHECK-NEXT: }}
// CHECK-NOT: %2, %3 = func.call @split(%0, %1)

builtin.module {{
  func.func @split(%0 : {STATIC_LHS.type_ir} {{name = "lhs"}}, %1 : {STATIC_RHS.type_ir} {{name = "rhs"}}) -> ({STATIC_LHS.type_ir}, {STATIC_RHS.type_ir}) {{
    func.return %0, %1 : {STATIC_LHS.type_ir}, {STATIC_RHS.type_ir}
  }}
  func.func @caller(%0 : {STATIC_LHS.type_ir} {{name = "lhs"}}, %1 : {STATIC_RHS.type_ir} {{name = "rhs"}}) {{
    %2, %3 = func.call @split(%0, %1) : ({STATIC_LHS.type_ir}, {STATIC_RHS.type_ir}) -> ({STATIC_LHS.type_ir}, {STATIC_RHS.type_ir})
    func.return
  }}
}}
"""

CASE_TEXT_DYNAMIC = f"""// COMPILE_ARGS: --pass buffer-results-to-out-params
// CASE: case-multi-output-dynamic: 多个动态 memory outputs 固定重写成前置 arg0/arg1，caller 同步改写。
// CHECK: builtin.module {{
// CHECK-NEXT: func.func @split(%0: {DYNAMIC_LHS.type_ir} {{name = "arg0"}}, %1: {DYNAMIC_RHS.type_ir} {{name = "arg1"}}, %2: {DYNAMIC_LHS.type_ir} {{name = "lhs"}}, %3: {DYNAMIC_RHS.type_ir} {{name = "rhs"}}) {{
// CHECK-NEXT: func.return
// CHECK-NEXT: }}
// CHECK-NEXT: func.func @caller(%0: {DYNAMIC_LHS.type_ir} {{name = "lhs"}}, %1: {DYNAMIC_RHS.type_ir} {{name = "rhs"}}) {{
// CHECK-NEXT: %2 = "dma.alloc"() <{{operandSegmentSizes = array<i32: 0>}}> : () -> {DYNAMIC_LHS.type_ir}
// CHECK-NEXT: %3 = "dma.alloc"() <{{operandSegmentSizes = array<i32: 0>}}> : () -> {DYNAMIC_RHS.type_ir}
// CHECK-NEXT: func.call @split(%2, %3, %0, %1) : ({DYNAMIC_LHS.type_ir}, {DYNAMIC_RHS.type_ir}, {DYNAMIC_LHS.type_ir}, {DYNAMIC_RHS.type_ir}) -> ()
// CHECK-NEXT: func.return
// CHECK-NEXT: }}
// CHECK-NEXT: }}
// CHECK-NOT: %2, %3 = func.call @split(%0, %1)

builtin.module {{
  func.func @split(%0 : {DYNAMIC_LHS.type_ir} {{name = "lhs"}}, %1 : {DYNAMIC_RHS.type_ir} {{name = "rhs"}}) -> ({DYNAMIC_LHS.type_ir}, {DYNAMIC_RHS.type_ir}) {{
    func.return %0, %1 : {DYNAMIC_LHS.type_ir}, {DYNAMIC_RHS.type_ir}
  }}
  func.func @caller(%0 : {DYNAMIC_LHS.type_ir} {{name = "lhs"}}, %1 : {DYNAMIC_RHS.type_ir} {{name = "rhs"}}) {{
    %2, %3 = func.call @split(%0, %1) : ({DYNAMIC_LHS.type_ir}, {DYNAMIC_RHS.type_ir}) -> ({DYNAMIC_LHS.type_ir}, {DYNAMIC_RHS.type_ir})
    func.return
  }}
}}
"""

CASE_TEXT_THREE_OUTPUTS = f"""// COMPILE_ARGS: --pass buffer-results-to-out-params
// CASE: case-multi-output-three: 三个 memory outputs 固定重写成前置 arg0/arg1/arg2。
// CHECK: builtin.module {{
// CHECK-NEXT: func.func @split3(%0: {STATIC_LHS.type_ir} {{name = "arg0"}}, %1: {STATIC_RHS.type_ir} {{name = "arg1"}}, %2: {STATIC_THIRD.type_ir} {{name = "arg2"}}) {{
// CHECK-NEXT: func.return
// CHECK-NEXT: }}
// CHECK-NEXT: func.func @caller() {{
// CHECK-NEXT: %0 = "dma.alloc"() <{{operandSegmentSizes = array<i32: 0>}}> : () -> {STATIC_LHS.type_ir}
// CHECK-NEXT: %1 = "dma.alloc"() <{{operandSegmentSizes = array<i32: 0>}}> : () -> {STATIC_RHS.type_ir}
// CHECK-NEXT: %2 = "dma.alloc"() <{{operandSegmentSizes = array<i32: 0>}}> : () -> {STATIC_THIRD.type_ir}
// CHECK-NEXT: func.call @split3(%0, %1, %2) : ({STATIC_LHS.type_ir}, {STATIC_RHS.type_ir}, {STATIC_THIRD.type_ir}) -> ()
// CHECK-NEXT: func.return
// CHECK-NEXT: }}
// CHECK-NEXT: }}
// CHECK-NOT: %0, %1, %2 = func.call @split3()

builtin.module {{
  func.func @split3() -> ({STATIC_LHS.type_ir}, {STATIC_RHS.type_ir}, {STATIC_THIRD.type_ir}) {{
    %0 = "dma.alloc"() <{{operandSegmentSizes = array<i32: 0>}}> : () -> {STATIC_LHS.type_ir}
    %1 = "dma.alloc"() <{{operandSegmentSizes = array<i32: 0>}}> : () -> {STATIC_RHS.type_ir}
    %2 = "dma.alloc"() <{{operandSegmentSizes = array<i32: 0>}}> : () -> {STATIC_THIRD.type_ir}
    func.return %0, %1, %2 : {STATIC_LHS.type_ir}, {STATIC_RHS.type_ir}, {STATIC_THIRD.type_ir}
  }}
  func.func @caller() {{
    %0, %1, %2 = func.call @split3() : () -> ({STATIC_LHS.type_ir}, {STATIC_RHS.type_ir}, {STATIC_THIRD.type_ir})
    func.return
  }}
}}
"""

CASE_TEXT_THREE_OUTPUTS_DYNAMIC = f"""// COMPILE_ARGS: --pass buffer-results-to-out-params
// CASE: case-multi-output-three-dynamic: 三个动态 memory outputs 固定重写成前置 arg0/arg1/arg2。
// CHECK: builtin.module {{
// CHECK-NEXT: func.func @split3(%0: {DYNAMIC_LHS.type_ir} {{name = "arg0"}}, %1: {DYNAMIC_RHS.type_ir} {{name = "arg1"}}, %2: {DYNAMIC_THIRD.type_ir} {{name = "arg2"}}) {{
// CHECK-NEXT: func.return
// CHECK-NEXT: }}
// CHECK-NEXT: func.func @caller() {{
// CHECK-NEXT: %0 = "dma.alloc"() <{{operandSegmentSizes = array<i32: 0>}}> : () -> {DYNAMIC_LHS.type_ir}
// CHECK-NEXT: %1 = "dma.alloc"() <{{operandSegmentSizes = array<i32: 0>}}> : () -> {DYNAMIC_RHS.type_ir}
// CHECK-NEXT: %2 = "dma.alloc"() <{{operandSegmentSizes = array<i32: 0>}}> : () -> {DYNAMIC_THIRD.type_ir}
// CHECK-NEXT: func.call @split3(%0, %1, %2) : ({DYNAMIC_LHS.type_ir}, {DYNAMIC_RHS.type_ir}, {DYNAMIC_THIRD.type_ir}) -> ()
// CHECK-NEXT: func.return
// CHECK-NEXT: }}
// CHECK-NEXT: }}
// CHECK-NOT: %0, %1, %2 = func.call @split3()

builtin.module {{
  func.func @split3() -> ({DYNAMIC_LHS.type_ir}, {DYNAMIC_RHS.type_ir}, {DYNAMIC_THIRD.type_ir}) {{
    %0 = "dma.alloc"() <{{operandSegmentSizes = array<i32: 0>}}> : () -> {DYNAMIC_LHS.type_ir}
    %1 = "dma.alloc"() <{{operandSegmentSizes = array<i32: 0>}}> : () -> {DYNAMIC_RHS.type_ir}
    %2 = "dma.alloc"() <{{operandSegmentSizes = array<i32: 0>}}> : () -> {DYNAMIC_THIRD.type_ir}
    func.return %0, %1, %2 : {DYNAMIC_LHS.type_ir}, {DYNAMIC_RHS.type_ir}, {DYNAMIC_THIRD.type_ir}
  }}
  func.func @caller() {{
    %0, %1, %2 = func.call @split3() : () -> ({DYNAMIC_LHS.type_ir}, {DYNAMIC_RHS.type_ir}, {DYNAMIC_THIRD.type_ir})
    func.return
  }}
}}
"""


def _case_1() -> None:
    """正例：多个静态 outputs 固定映射到 arg0/arg1。"""

    result = run_ircheck_text(
        CASE_TEXT,
        source_path="expectation/pass/buffer_results_to_out_params/multi_output.py:case-1",
    )
    assert result.ok is True, result.message
    assert result.exit_code == 0, f"expected exit_code=0, got {result.exit_code}"
    assert "func.call @split(%2, %3, %0, %1)" in result.actual_ir
    assert "%2, %3 = func.call @split(%0, %1)" not in result.actual_ir
    print_case_actual_ir("CASE-1", CASE_TEXT, result.actual_ir, fallback="multi output static")


def _case_2() -> None:
    """正例：多个动态 outputs 也固定映射到 arg0/arg1。"""

    result = run_ircheck_text(
        CASE_TEXT_DYNAMIC,
        source_path="expectation/pass/buffer_results_to_out_params/multi_output.py:case-2",
    )
    assert result.ok is True, result.message
    assert result.exit_code == 0, f"expected exit_code=0, got {result.exit_code}"
    assert "func.call @split(%2, %3, %0, %1)" in result.actual_ir
    assert "%2, %3 = func.call @split(%0, %1)" not in result.actual_ir
    print_case_actual_ir("CASE-2", CASE_TEXT_DYNAMIC, result.actual_ir, fallback="multi output dynamic")


def _case_3() -> None:
    """正例：三个 outputs 也必须固定映射到 arg0/arg1/arg2。"""

    result = run_ircheck_text(
        CASE_TEXT_THREE_OUTPUTS,
        source_path="expectation/pass/buffer_results_to_out_params/multi_output.py:case-3",
    )
    assert result.ok is True, result.message
    assert result.exit_code == 0, f"expected exit_code=0, got {result.exit_code}"
    assert "func.call @split3(%0, %1, %2)" in result.actual_ir
    assert "%0, %1, %2 = func.call @split3()" not in result.actual_ir
    print_case_actual_ir("CASE-3", CASE_TEXT_THREE_OUTPUTS, result.actual_ir, fallback="multi output three")


def _case_4() -> None:
    """正例：三个动态 outputs 也必须固定映射到 arg0/arg1/arg2。"""

    result = run_ircheck_text(
        CASE_TEXT_THREE_OUTPUTS_DYNAMIC,
        source_path="expectation/pass/buffer_results_to_out_params/multi_output.py:case-4",
    )
    assert result.ok is True, result.message
    assert result.exit_code == 0, f"expected exit_code=0, got {result.exit_code}"
    assert "func.call @split3(%0, %1, %2)" in result.actual_ir
    assert "%0, %1, %2 = func.call @split3()" not in result.actual_ir
    print_case_actual_ir(
        "CASE-4",
        CASE_TEXT_THREE_OUTPUTS_DYNAMIC,
        result.actual_ir,
        fallback="multi output three dynamic",
    )


def main() -> None:
    """运行 multi output ircheck expectation。"""

    failures: list[tuple[str, BaseException]] = []
    run_case(failures, "CASE-1", _case_1)
    run_case(failures, "CASE-2", _case_2)
    run_case(failures, "CASE-3", _case_3)
    run_case(failures, "CASE-4", _case_4)
    raise_if_failures("buffer_results_to_out_params multi output expectation", failures)


if __name__ == "__main__":
    main()
