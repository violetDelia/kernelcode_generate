"""`symbol-loop-hoist` pass expectation。

创建者: 大闸蟹
最后一次更改: 大闸蟹

功能说明:
- 使用 `ircheck` 黑盒锁定 `symbol-loop-hoist` 当前公开合同。
- 当前只覆盖 `symbol.const` 与首批标量 `symbol` 算术 `elewise` 计算
  `symbol.add/sub/mul/div/floordiv`。
- 对这类 op，只有 operands 全部来自当前 `symbol.for` 之外时才允许外提；
  若 operand 依赖 `symbol.iter` 或 loop 内 SSA，则必须保留在 loop 内。

使用示例:
- `PYTHONPATH=. python -m expectation.pass.symbol_loop_hoist`

关联文件:
- spec: [`spec/pass/lowering/symbol_loop_hoist.md`](spec/pass/lowering/symbol_loop_hoist.md)
- test: [`test/pass/test_symbol_loop_hoist.py`](test/pass/test_symbol_loop_hoist.py)
- 功能实现: [`kernel_gen/passes/lowering/symbol_loop_hoist.py`](kernel_gen/passes/lowering/symbol_loop_hoist.py)
"""

from __future__ import annotations

from pathlib import Path
import sys

CURRENT_DIR = Path(__file__).resolve().parent
if str(CURRENT_DIR) in sys.path:
    sys.path.remove(str(CURRENT_DIR))

REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from importlib import import_module

print_case_actual_ir = import_module("expectation.pass.lowing._shared").print_case_actual_ir
from expectation.utils.case_runner import raise_if_failures, run_case
from kernel_gen.tools.ircheck import run_ircheck_text

CASE_TEXT_CONST_HOIST = """// COMPILE_ARGS: --pass symbol-loop-hoist
// CASE: 正例：loop 内的 invariant `symbol.const` 应被向上提一层到 `symbol.for` 之前。
// CHECK: builtin.module {
// CHECK-NEXT: func.func @hoist_const() {
// CHECK-NEXT: %[[C0:.*]] = symbol.const 0 : !symbol.int<"0">
// CHECK-NEXT: %[[C1:.*]] = symbol.const 1 : !symbol.int<"1">
// CHECK-NEXT: %[[C2:.*]] = symbol.const 1 : !symbol.int<"1">
// CHECK-NEXT: %[[HC:.*]] = symbol.const 2 : !symbol.int<"2">
// CHECK-NEXT: symbol.for %[[IT:.*]] = %[[C0]] to %[[C1]] step %[[C2]] {iter = #symbol.iter<start = "0", end = "1", step = "1">} {
// CHECK-NEXT: }
// CHECK-NEXT: func.return
// CHECK-NEXT: }
// CHECK-NEXT: }

builtin.module {
  func.func @hoist_const() {
    %0 = symbol.const 0 : !symbol.int<"0">
    %1 = symbol.const 1 : !symbol.int<"1">
    %2 = symbol.const 1 : !symbol.int<"1">
    symbol.for %3 = %0 to %1 step %2 {iter = #symbol.iter<start = "0", end = "1", step = "1">} {
      %4 = symbol.const 2 : !symbol.int<"2">
    }
    func.return
  }
}
"""

CASE_TEXT_ADD_HOIST = """// COMPILE_ARGS: --pass symbol-loop-hoist
// CASE: 正例：loop 内的 invariant `symbol.add` 应被向上提一层到 `symbol.for` 之前。
// CHECK: builtin.module {
// CHECK-NEXT: func.func @hoist_add() {
// CHECK-NEXT: %[[C0:.*]] = symbol.const 0 : !symbol.int<"0">
// CHECK-NEXT: %[[C1:.*]] = symbol.const 1 : !symbol.int<"1">
// CHECK-NEXT: %[[C2:.*]] = symbol.const 1 : !symbol.int<"1">
// CHECK-NEXT: %[[LHS:.*]] = symbol.const 4 : !symbol.int<"4">
// CHECK-NEXT: %[[RHS:.*]] = symbol.const 5 : !symbol.int<"5">
// CHECK-NEXT: %[[SUM:.*]] = symbol.add %[[LHS]], %[[RHS]] : !symbol.int<"4">, !symbol.int<"5"> -> !symbol.int<"9">
// CHECK-NEXT: symbol.for %[[IT:.*]] = %[[C0]] to %[[C1]] step %[[C2]] {iter = #symbol.iter<start = "0", end = "1", step = "1">} {
// CHECK-NEXT: }
// CHECK-NEXT: func.return
// CHECK-NEXT: }
// CHECK-NEXT: }

builtin.module {
  func.func @hoist_add() {
    %0 = symbol.const 0 : !symbol.int<"0">
    %1 = symbol.const 1 : !symbol.int<"1">
    %2 = symbol.const 1 : !symbol.int<"1">
    %3 = symbol.const 4 : !symbol.int<"4">
    %4 = symbol.const 5 : !symbol.int<"5">
    symbol.for %5 = %0 to %1 step %2 {iter = #symbol.iter<start = "0", end = "1", step = "1">} {
      %6 = symbol.add %3, %4 : !symbol.int<"4">, !symbol.int<"5"> -> !symbol.int<"9">
    }
    func.return
  }
}
"""

CASE_TEXT_SUB_HOIST = """// COMPILE_ARGS: --pass symbol-loop-hoist
// CASE: 正例：loop 内的 invariant `symbol.sub` 应被向上提一层到 `symbol.for` 之前。
// CHECK: builtin.module {
// CHECK-NEXT: func.func @hoist_sub() {
// CHECK-NEXT: %[[C0:.*]] = symbol.const 0 : !symbol.int<"0">
// CHECK-NEXT: %[[C1:.*]] = symbol.const 1 : !symbol.int<"1">
// CHECK-NEXT: %[[C2:.*]] = symbol.const 1 : !symbol.int<"1">
// CHECK-NEXT: %[[LHS:.*]] = symbol.const 9 : !symbol.int<"9">
// CHECK-NEXT: %[[RHS:.*]] = symbol.const 4 : !symbol.int<"4">
// CHECK-NEXT: %[[DIFF:.*]] = symbol.sub %[[LHS]], %[[RHS]] : !symbol.int<"9">, !symbol.int<"4"> -> !symbol.int<"5">
// CHECK-NEXT: symbol.for %[[IT:.*]] = %[[C0]] to %[[C1]] step %[[C2]] {iter = #symbol.iter<start = "0", end = "1", step = "1">} {
// CHECK-NEXT: }
// CHECK-NEXT: func.return
// CHECK-NEXT: }
// CHECK-NEXT: }

builtin.module {
  func.func @hoist_sub() {
    %0 = symbol.const 0 : !symbol.int<"0">
    %1 = symbol.const 1 : !symbol.int<"1">
    %2 = symbol.const 1 : !symbol.int<"1">
    %3 = symbol.const 9 : !symbol.int<"9">
    %4 = symbol.const 4 : !symbol.int<"4">
    symbol.for %5 = %0 to %1 step %2 {iter = #symbol.iter<start = "0", end = "1", step = "1">} {
      %6 = symbol.sub %3, %4 : !symbol.int<"9">, !symbol.int<"4"> -> !symbol.int<"5">
    }
    func.return
  }
}
"""

CASE_TEXT_MUL_HOIST = """// COMPILE_ARGS: --pass symbol-loop-hoist
// CASE: 正例：loop 内的 invariant `symbol.mul` 应被向上提一层到 `symbol.for` 之前。
// CHECK: builtin.module {
// CHECK-NEXT: func.func @hoist_mul() {
// CHECK-NEXT: %[[C0:.*]] = symbol.const 0 : !symbol.int<"0">
// CHECK-NEXT: %[[C1:.*]] = symbol.const 1 : !symbol.int<"1">
// CHECK-NEXT: %[[C2:.*]] = symbol.const 1 : !symbol.int<"1">
// CHECK-NEXT: %[[LHS:.*]] = symbol.const 3 : !symbol.int<"3">
// CHECK-NEXT: %[[RHS:.*]] = symbol.const 7 : !symbol.int<"7">
// CHECK-NEXT: %[[PROD:.*]] = symbol.mul %[[LHS]], %[[RHS]] : !symbol.int<"3">, !symbol.int<"7"> -> !symbol.int<"21">
// CHECK-NEXT: symbol.for %[[IT:.*]] = %[[C0]] to %[[C1]] step %[[C2]] {iter = #symbol.iter<start = "0", end = "1", step = "1">} {
// CHECK-NEXT: }
// CHECK-NEXT: func.return
// CHECK-NEXT: }
// CHECK-NEXT: }

builtin.module {
  func.func @hoist_mul() {
    %0 = symbol.const 0 : !symbol.int<"0">
    %1 = symbol.const 1 : !symbol.int<"1">
    %2 = symbol.const 1 : !symbol.int<"1">
    %3 = symbol.const 3 : !symbol.int<"3">
    %4 = symbol.const 7 : !symbol.int<"7">
    symbol.for %5 = %0 to %1 step %2 {iter = #symbol.iter<start = "0", end = "1", step = "1">} {
      %6 = symbol.mul %3, %4 : !symbol.int<"3">, !symbol.int<"7"> -> !symbol.int<"21">
    }
    func.return
  }
}
"""

CASE_TEXT_DIV_HOIST = """// COMPILE_ARGS: --pass symbol-loop-hoist
// CASE: 正例：loop 内的 invariant `symbol.div` 应被向上提一层到 `symbol.for` 之前。
// CHECK: builtin.module {
// CHECK-NEXT: func.func @hoist_div() {
// CHECK-NEXT: %[[C0:.*]] = symbol.const 0 : !symbol.int<"0">
// CHECK-NEXT: %[[C1:.*]] = symbol.const 1 : !symbol.int<"1">
// CHECK-NEXT: %[[C2:.*]] = symbol.const 1 : !symbol.int<"1">
// CHECK-NEXT: %[[LHS:.*]] = symbol.const 8 : !symbol.int<"8">
// CHECK-NEXT: %[[RHS:.*]] = symbol.const 2 : !symbol.int<"2">
// CHECK-NEXT: %[[QUOT:.*]] = symbol.div %[[LHS]], %[[RHS]] : !symbol.int<"8">, !symbol.int<"2"> -> !symbol.int<"4">
// CHECK-NEXT: symbol.for %[[IT:.*]] = %[[C0]] to %[[C1]] step %[[C2]] {iter = #symbol.iter<start = "0", end = "1", step = "1">} {
// CHECK-NEXT: }
// CHECK-NEXT: func.return
// CHECK-NEXT: }
// CHECK-NEXT: }

builtin.module {
  func.func @hoist_div() {
    %0 = symbol.const 0 : !symbol.int<"0">
    %1 = symbol.const 1 : !symbol.int<"1">
    %2 = symbol.const 1 : !symbol.int<"1">
    %3 = symbol.const 8 : !symbol.int<"8">
    %4 = symbol.const 2 : !symbol.int<"2">
    symbol.for %5 = %0 to %1 step %2 {iter = #symbol.iter<start = "0", end = "1", step = "1">} {
      %6 = symbol.div %3, %4 : !symbol.int<"8">, !symbol.int<"2"> -> !symbol.int<"4">
    }
    func.return
  }
}
"""

CASE_TEXT_FLOORDIV_HOIST = """// COMPILE_ARGS: --pass symbol-loop-hoist
// CASE: 正例：loop 内的 invariant `symbol.floordiv` 应被向上提一层到 `symbol.for` 之前。
// CHECK: builtin.module {
// CHECK-NEXT: func.func @hoist_floordiv() {
// CHECK-NEXT: %[[C0:.*]] = symbol.const 0 : !symbol.int<"0">
// CHECK-NEXT: %[[C1:.*]] = symbol.const 1 : !symbol.int<"1">
// CHECK-NEXT: %[[C2:.*]] = symbol.const 1 : !symbol.int<"1">
// CHECK-NEXT: %[[LHS:.*]] = symbol.const 9 : !symbol.int<"9">
// CHECK-NEXT: %[[RHS:.*]] = symbol.const 2 : !symbol.int<"2">
// CHECK-NEXT: %[[QUOT:.*]] = symbol.floordiv %[[LHS]], %[[RHS]] : !symbol.int<"9">, !symbol.int<"2"> -> !symbol.int<"4">
// CHECK-NEXT: symbol.for %[[IT:.*]] = %[[C0]] to %[[C1]] step %[[C2]] {iter = #symbol.iter<start = "0", end = "1", step = "1">} {
// CHECK-NEXT: }
// CHECK-NEXT: func.return
// CHECK-NEXT: }
// CHECK-NEXT: }

builtin.module {
  func.func @hoist_floordiv() {
    %0 = symbol.const 0 : !symbol.int<"0">
    %1 = symbol.const 1 : !symbol.int<"1">
    %2 = symbol.const 1 : !symbol.int<"1">
    %3 = symbol.const 9 : !symbol.int<"9">
    %4 = symbol.const 2 : !symbol.int<"2">
    symbol.for %5 = %0 to %1 step %2 {iter = #symbol.iter<start = "0", end = "1", step = "1">} {
      %6 = symbol.floordiv %3, %4 : !symbol.int<"9">, !symbol.int<"2"> -> !symbol.int<"4">
    }
    func.return
  }
}
"""


def _assert_success(case_text: str, source_path: str) -> str:
    result = run_ircheck_text(case_text, source_path=source_path)
    assert result.ok is True, (
        f"expected ok=True, got ok={result.ok}, exit_code={result.exit_code}, message={result.message!r}"
    )
    assert result.exit_code == 0, f"expected exit_code=0, got {result.exit_code}"
    return result.actual_ir


def _case_1_const_hoist() -> None:
    actual_ir = _assert_success(
        CASE_TEXT_CONST_HOIST,
        "expectation/pass/symbol_loop_hoist/__main__.py:const-hoist",
    )
    print_case_actual_ir("CASE-1", CASE_TEXT_CONST_HOIST, actual_ir, fallback="symbol.const hoist")


def _case_2_add_hoist() -> None:
    actual_ir = _assert_success(
        CASE_TEXT_ADD_HOIST,
        "expectation/pass/symbol_loop_hoist/__main__.py:add-hoist",
    )
    print_case_actual_ir("CASE-2", CASE_TEXT_ADD_HOIST, actual_ir, fallback="symbol.add hoist")


def _case_3_sub_hoist() -> None:
    actual_ir = _assert_success(
        CASE_TEXT_SUB_HOIST,
        "expectation/pass/symbol_loop_hoist/__main__.py:sub-hoist",
    )
    print_case_actual_ir("CASE-3", CASE_TEXT_SUB_HOIST, actual_ir, fallback="symbol.sub hoist")


def _case_4_mul_hoist() -> None:
    actual_ir = _assert_success(
        CASE_TEXT_MUL_HOIST,
        "expectation/pass/symbol_loop_hoist/__main__.py:mul-hoist",
    )
    print_case_actual_ir("CASE-4", CASE_TEXT_MUL_HOIST, actual_ir, fallback="symbol.mul hoist")


def _case_5_div_hoist() -> None:
    actual_ir = _assert_success(
        CASE_TEXT_DIV_HOIST,
        "expectation/pass/symbol_loop_hoist/__main__.py:div-hoist",
    )
    print_case_actual_ir("CASE-5", CASE_TEXT_DIV_HOIST, actual_ir, fallback="symbol.div hoist")


def _case_6_floordiv_hoist() -> None:
    actual_ir = _assert_success(
        CASE_TEXT_FLOORDIV_HOIST,
        "expectation/pass/symbol_loop_hoist/__main__.py:floordiv-hoist",
    )
    print_case_actual_ir("CASE-6", CASE_TEXT_FLOORDIV_HOIST, actual_ir, fallback="symbol.floordiv hoist")


def main() -> None:
    failures: list[tuple[str, BaseException]] = []
    run_case(failures, "CASE-1", _case_1_const_hoist)
    run_case(failures, "CASE-2", _case_2_add_hoist)
    run_case(failures, "CASE-3", _case_3_sub_hoist)
    run_case(failures, "CASE-4", _case_4_mul_hoist)
    run_case(failures, "CASE-5", _case_5_div_hoist)
    run_case(failures, "CASE-6", _case_6_floordiv_hoist)
    raise_if_failures("symbol_loop_hoist expectation", failures)


if __name__ == "__main__":
    main()
