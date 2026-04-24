# [immutable-file]
"""`buffer_results_to_out_params` mixed output ircheck expectation。

创建者: 守护最好的爱莉希雅
最后一次更改: 守护最好的爱莉希雅

功能说明:
- 使用 `ircheck` 黑盒锁定 `BufferResultsToOutParamsPass` 对 mixed returns 的改写结果。
- 在基础 `memory + scalar` 之外，再补一个 `scalar + memory + scalar` 的交错输出
  场景，确保当前 IR 不是只对 `memory` 在前的顺序生效。

使用示例:
- `PYTHONPATH=. python expectation/pass/buffer_results_to_out_params/mixed_output.py`

关联文件:
- spec: [`spec/pass/lowering/buffer_results_to_out_params.md`](../../../spec/pass/lowering/buffer_results_to_out_params.md)
- spec: [`spec/tools/ircheck.md`](../../../spec/tools/ircheck.md)
- test: [`test/pass/test_buffer_results_to_out_params.py`](../../../test/pass/test_buffer_results_to_out_params.py)
- 功能实现: [`expectation/pass/buffer_results_to_out_params/mixed_output.py`](../../../expectation/pass/buffer_results_to_out_params/mixed_output.py)
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
    random_scalar_type_ir,
    random_static_memory_spec,
    scalar_constant_literal,
)
from expectation.utils.case_runner import raise_if_failures, run_case
from kernel_gen.tools.ircheck import run_ircheck_text

STATIC_SRC = random_static_memory_spec("src", rank=random_rank())
DYNAMIC_SRC = random_dynamic_memory_spec("src", rank=random_rank())
CASE1_SCALAR = random_scalar_type_ir()
CASE2_SCALAR = random_scalar_type_ir()
CASE3_SCALAR_A = random_scalar_type_ir()
CASE3_SCALAR_B = random_scalar_type_ir()
CASE4_MEM_A = random_static_memory_spec("lhs", rank=random_rank())
CASE4_MEM_B = random_static_memory_spec("rhs", rank=random_rank())
CASE4_SCALAR_A = random_scalar_type_ir()
CASE4_SCALAR_B = random_scalar_type_ir()

CASE_TEXT = f"""// COMPILE_ARGS: --pass buffer-results-to-out-params
// CASE: case-mixed-output-static: mixed output 重写后，memory 走 arg0，scalar 保留 return。
// CHECK: builtin.module {{
// CHECK-NEXT: func.func @reduce(%0: {STATIC_SRC.type_ir} {{name = "arg0"}}, %1: {STATIC_SRC.type_ir} {{name = "src"}}) -> {CASE1_SCALAR} {{
// CHECK-NEXT: %2 = arith.constant {scalar_constant_literal(CASE1_SCALAR)} : {CASE1_SCALAR}
// CHECK-NEXT: func.return %2 : {CASE1_SCALAR}
// CHECK-NEXT: }}
// CHECK-NEXT: func.func @caller(%0: {STATIC_SRC.type_ir} {{name = "src"}}) -> {CASE1_SCALAR} {{
// CHECK-NEXT: %1 = "dma.alloc"() <{{operandSegmentSizes = array<i32: 0>}}> : () -> {STATIC_SRC.type_ir}
// CHECK-NEXT: %2 = func.call @reduce(%1, %0) : ({STATIC_SRC.type_ir}, {STATIC_SRC.type_ir}) -> {CASE1_SCALAR}
// CHECK-NEXT: func.return %2 : {CASE1_SCALAR}
// CHECK-NEXT: }}
// CHECK-NEXT: }}
// CHECK-NOT: %1, %2 = func.call @reduce(%0)

builtin.module {{
  func.func @reduce(%0 : {STATIC_SRC.type_ir} {{name = "src"}}) -> ({STATIC_SRC.type_ir}, {CASE1_SCALAR}) {{
    %1 = arith.constant {scalar_constant_literal(CASE1_SCALAR)} : {CASE1_SCALAR}
    func.return %0, %1 : {STATIC_SRC.type_ir}, {CASE1_SCALAR}
  }}
  func.func @caller(%0 : {STATIC_SRC.type_ir} {{name = "src"}}) -> {CASE1_SCALAR} {{
    %1, %2 = func.call @reduce(%0) : ({STATIC_SRC.type_ir}) -> ({STATIC_SRC.type_ir}, {CASE1_SCALAR})
    func.return %2 : {CASE1_SCALAR}
  }}
}}
"""

CASE_TEXT_DYNAMIC = f"""// COMPILE_ARGS: --pass buffer-results-to-out-params
// CASE: case-mixed-output-dynamic: mixed output 动态 shape 重写后，memory 走 arg0，scalar 保留 return。
// CHECK: builtin.module {{
// CHECK-NEXT: func.func @reduce(%0: {DYNAMIC_SRC.type_ir} {{name = "arg0"}}, %1: {DYNAMIC_SRC.type_ir} {{name = "src"}}) -> {CASE2_SCALAR} {{
// CHECK-NEXT: %2 = arith.constant {scalar_constant_literal(CASE2_SCALAR)} : {CASE2_SCALAR}
// CHECK-NEXT: func.return %2 : {CASE2_SCALAR}
// CHECK-NEXT: }}
// CHECK-NEXT: func.func @caller(%0: {DYNAMIC_SRC.type_ir} {{name = "src"}}) -> {CASE2_SCALAR} {{
// CHECK-NEXT: %1 = "dma.alloc"() <{{operandSegmentSizes = array<i32: 0>}}> : () -> {DYNAMIC_SRC.type_ir}
// CHECK-NEXT: %2 = func.call @reduce(%1, %0) : ({DYNAMIC_SRC.type_ir}, {DYNAMIC_SRC.type_ir}) -> {CASE2_SCALAR}
// CHECK-NEXT: func.return %2 : {CASE2_SCALAR}
// CHECK-NEXT: }}
// CHECK-NEXT: }}
// CHECK-NOT: %1, %2 = func.call @reduce(%0)

builtin.module {{
  func.func @reduce(%0 : {DYNAMIC_SRC.type_ir} {{name = "src"}}) -> ({DYNAMIC_SRC.type_ir}, {CASE2_SCALAR}) {{
    %1 = arith.constant {scalar_constant_literal(CASE2_SCALAR)} : {CASE2_SCALAR}
    func.return %0, %1 : {DYNAMIC_SRC.type_ir}, {CASE2_SCALAR}
  }}
  func.func @caller(%0 : {DYNAMIC_SRC.type_ir} {{name = "src"}}) -> {CASE2_SCALAR} {{
    %1, %2 = func.call @reduce(%0) : ({DYNAMIC_SRC.type_ir}) -> ({DYNAMIC_SRC.type_ir}, {CASE2_SCALAR})
    func.return %2 : {CASE2_SCALAR}
  }}
}}
"""

CASE_TEXT_INTERLEAVED = f"""// COMPILE_ARGS: --pass buffer-results-to-out-params
// CASE: case-mixed-output-interleaved: 交错输出重写后，memory 仍走 arg0，scalar 顺序保持不变。
// CHECK: builtin.module {{
// CHECK-NEXT: func.func @mix(%0: {STATIC_SRC.type_ir} {{name = "arg0"}}, %1: {STATIC_SRC.type_ir} {{name = "src"}}) -> ({CASE3_SCALAR_A}, {CASE3_SCALAR_B}) {{
// CHECK-NEXT: %2 = arith.constant {scalar_constant_literal(CASE3_SCALAR_A)} : {CASE3_SCALAR_A}
// CHECK-NEXT: %3 = arith.constant {scalar_constant_literal(CASE3_SCALAR_B)} : {CASE3_SCALAR_B}
// CHECK-NEXT: func.return %2, %3 : {CASE3_SCALAR_A}, {CASE3_SCALAR_B}
// CHECK-NEXT: }}
// CHECK-NEXT: func.func @caller(%0: {STATIC_SRC.type_ir} {{name = "src"}}) -> ({CASE3_SCALAR_A}, {CASE3_SCALAR_B}) {{
// CHECK-NEXT: %1 = "dma.alloc"() <{{operandSegmentSizes = array<i32: 0>}}> : () -> {STATIC_SRC.type_ir}
// CHECK-NEXT: %2, %3 = func.call @mix(%1, %0) : ({STATIC_SRC.type_ir}, {STATIC_SRC.type_ir}) -> ({CASE3_SCALAR_A}, {CASE3_SCALAR_B})
// CHECK-NEXT: func.return %2, %3 : {CASE3_SCALAR_A}, {CASE3_SCALAR_B}
// CHECK-NEXT: }}
// CHECK-NEXT: }}
// CHECK-NOT: %2, %3, %4 = func.call @mix(%0)

builtin.module {{
  func.func @mix(%0 : {STATIC_SRC.type_ir} {{name = "src"}}) -> ({CASE3_SCALAR_A}, {STATIC_SRC.type_ir}, {CASE3_SCALAR_B}) {{
    %1 = arith.constant {scalar_constant_literal(CASE3_SCALAR_A)} : {CASE3_SCALAR_A}
    %2 = arith.constant {scalar_constant_literal(CASE3_SCALAR_B)} : {CASE3_SCALAR_B}
    func.return %1, %0, %2 : {CASE3_SCALAR_A}, {STATIC_SRC.type_ir}, {CASE3_SCALAR_B}
  }}
  func.func @caller(%0 : {STATIC_SRC.type_ir} {{name = "src"}}) -> ({CASE3_SCALAR_A}, {CASE3_SCALAR_B}) {{
    %1, %2, %3 = func.call @mix(%0) : ({STATIC_SRC.type_ir}) -> ({CASE3_SCALAR_A}, {STATIC_SRC.type_ir}, {CASE3_SCALAR_B})
    func.return %1, %3 : {CASE3_SCALAR_A}, {CASE3_SCALAR_B}
  }}
}}
"""

CASE_TEXT_MULTI_MEMORY_INTERLEAVED = f"""// COMPILE_ARGS: --pass buffer-results-to-out-params
// CASE: case-mixed-output-two-memories: 交错 mixed outputs 含两个 memory 时，caller 需补两个 out 且保留 scalar 顺序。
// CHECK: builtin.module {{
// CHECK-NEXT: func.func @mix2(%0: {CASE4_MEM_A.type_ir} {{name = "arg0"}}, %1: {CASE4_MEM_B.type_ir} {{name = "arg1"}}, %2: {CASE4_MEM_A.type_ir} {{name = "lhs"}}, %3: {CASE4_MEM_B.type_ir} {{name = "rhs"}}) -> ({CASE4_SCALAR_A}, {CASE4_SCALAR_B}) {{
// CHECK-NEXT: %4 = arith.constant {scalar_constant_literal(CASE4_SCALAR_A)} : {CASE4_SCALAR_A}
// CHECK-NEXT: %5 = arith.constant {scalar_constant_literal(CASE4_SCALAR_B)} : {CASE4_SCALAR_B}
// CHECK-NEXT: func.return %4, %5 : {CASE4_SCALAR_A}, {CASE4_SCALAR_B}
// CHECK-NEXT: }}
// CHECK-NEXT: func.func @caller(%0: {CASE4_MEM_A.type_ir} {{name = "lhs"}}, %1: {CASE4_MEM_B.type_ir} {{name = "rhs"}}) -> ({CASE4_SCALAR_A}, {CASE4_SCALAR_B}) {{
// CHECK-NEXT: %2 = "dma.alloc"() <{{operandSegmentSizes = array<i32: 0>}}> : () -> {CASE4_MEM_A.type_ir}
// CHECK-NEXT: %3 = "dma.alloc"() <{{operandSegmentSizes = array<i32: 0>}}> : () -> {CASE4_MEM_B.type_ir}
// CHECK-NEXT: %4, %5 = func.call @mix2(%2, %3, %0, %1) : ({CASE4_MEM_A.type_ir}, {CASE4_MEM_B.type_ir}, {CASE4_MEM_A.type_ir}, {CASE4_MEM_B.type_ir}) -> ({CASE4_SCALAR_A}, {CASE4_SCALAR_B})
// CHECK-NEXT: func.return %4, %5 : {CASE4_SCALAR_A}, {CASE4_SCALAR_B}
// CHECK-NEXT: }}
// CHECK-NEXT: }}
// CHECK-NOT: %2, %3, %4, %5 = func.call @mix2(%0, %1)

builtin.module {{
  func.func @mix2(%0 : {CASE4_MEM_A.type_ir} {{name = "lhs"}}, %1 : {CASE4_MEM_B.type_ir} {{name = "rhs"}}) -> ({CASE4_SCALAR_A}, {CASE4_MEM_A.type_ir}, {CASE4_SCALAR_B}, {CASE4_MEM_B.type_ir}) {{
    %2 = arith.constant {scalar_constant_literal(CASE4_SCALAR_A)} : {CASE4_SCALAR_A}
    %3 = arith.constant {scalar_constant_literal(CASE4_SCALAR_B)} : {CASE4_SCALAR_B}
    func.return %2, %0, %3, %1 : {CASE4_SCALAR_A}, {CASE4_MEM_A.type_ir}, {CASE4_SCALAR_B}, {CASE4_MEM_B.type_ir}
  }}
  func.func @caller(%0 : {CASE4_MEM_A.type_ir} {{name = "lhs"}}, %1 : {CASE4_MEM_B.type_ir} {{name = "rhs"}}) -> ({CASE4_SCALAR_A}, {CASE4_SCALAR_B}) {{
    %2, %3, %4, %5 = func.call @mix2(%0, %1) : ({CASE4_MEM_A.type_ir}, {CASE4_MEM_B.type_ir}) -> ({CASE4_SCALAR_A}, {CASE4_MEM_A.type_ir}, {CASE4_SCALAR_B}, {CASE4_MEM_B.type_ir})
    func.return %2, %4 : {CASE4_SCALAR_A}, {CASE4_SCALAR_B}
  }}
}}
"""


def _case_1() -> None:
    """正例：静态 mixed output 保留 scalar return。"""

    result = run_ircheck_text(
        CASE_TEXT,
        source_path="expectation/pass/buffer_results_to_out_params/mixed_output.py:case-1",
    )
    assert result.ok is True, result.message
    assert result.exit_code == 0, f"expected exit_code=0, got {result.exit_code}"
    assert "%2 = func.call @reduce(%1, %0)" in result.actual_ir
    assert "%1, %2 = func.call @reduce(%0)" not in result.actual_ir
    print_case_actual_ir("CASE-1", CASE_TEXT, result.actual_ir, fallback="mixed output static")


def _case_2() -> None:
    """正例：动态 mixed output 也必须改写为前置 out 参数。"""

    result = run_ircheck_text(
        CASE_TEXT_DYNAMIC,
        source_path="expectation/pass/buffer_results_to_out_params/mixed_output.py:case-2",
    )
    assert result.ok is True, result.message
    assert result.exit_code == 0, f"expected exit_code=0, got {result.exit_code}"
    assert "%2 = func.call @reduce(%1, %0)" in result.actual_ir
    assert "%1, %2 = func.call @reduce(%0)" not in result.actual_ir
    print_case_actual_ir("CASE-2", CASE_TEXT_DYNAMIC, result.actual_ir, fallback="mixed output dynamic")


def _case_3() -> None:
    """正例：交错输出时 scalar 顺序保持不变。"""

    result = run_ircheck_text(
        CASE_TEXT_INTERLEAVED,
        source_path="expectation/pass/buffer_results_to_out_params/mixed_output.py:case-3",
    )
    assert result.ok is True, result.message
    assert result.exit_code == 0, f"expected exit_code=0, got {result.exit_code}"
    assert "func.call @mix(%1, %0)" in result.actual_ir
    assert "%1, %2, %3 = func.call @mix(%0)" not in result.actual_ir
    print_case_actual_ir("CASE-3", CASE_TEXT_INTERLEAVED, result.actual_ir, fallback="mixed output interleaved")


def _case_4() -> None:
    """正例：两个 memory 与两个 scalar 交错时仍保持 memory->out、scalar 顺序不变。"""

    result = run_ircheck_text(
        CASE_TEXT_MULTI_MEMORY_INTERLEAVED,
        source_path="expectation/pass/buffer_results_to_out_params/mixed_output.py:case-4",
    )
    assert result.ok is True, result.message
    assert result.exit_code == 0, f"expected exit_code=0, got {result.exit_code}"
    assert "func.call @mix2(%2, %3, %0, %1)" in result.actual_ir
    assert "%2, %3, %4, %5 = func.call @mix2(%0, %1)" not in result.actual_ir
    print_case_actual_ir(
        "CASE-4",
        CASE_TEXT_MULTI_MEMORY_INTERLEAVED,
        result.actual_ir,
        fallback="mixed output interleaved two memories",
    )


def main() -> None:
    """运行 mixed output ircheck expectation。"""

    failures: list[tuple[str, BaseException]] = []
    run_case(failures, "CASE-1", _case_1)
    run_case(failures, "CASE-2", _case_2)
    run_case(failures, "CASE-3", _case_3)
    run_case(failures, "CASE-4", _case_4)
    raise_if_failures("buffer_results_to_out_params mixed output expectation", failures)


if __name__ == "__main__":
    main()
