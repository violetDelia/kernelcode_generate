"""DSL return-type-from-body expectation.

创建者: 大闸蟹
最后一次更改: 守护最好的爱莉希雅

功能说明:
- 使用 `mlir_gen_compare_text(...)` 比较完整 `builtin.module`。
- 锁定函数输出类型由 `runtime_args + return` 表达式决定，而不是由函数签名决定。

使用示例:
- `PYTHONPATH=. python expectation/dsl/mlir_gen/return_type_from_body_not_signature.py`

关联文件:
- spec: [`spec/dsl/ast.md`](spec/dsl/ast.md)
- spec: [`spec/dsl/mlir_gen.md`](spec/dsl/mlir_gen.md)
- spec: [`spec/tools/mlir_gen_compare.md`](spec/tools/mlir_gen_compare.md)
- test: [`test/dsl/test_mlir_gen.py`](test/dsl/test_mlir_gen.py)
- test: [`test/tools/test_mlir_gen_compare.py`](test/tools/test_mlir_gen_compare.py)
- 功能实现: [`kernel_gen/dsl/mlir_gen.py`](kernel_gen/dsl/mlir_gen.py)
- 功能实现: [`kernel_gen/tools/mlir_gen_compare.py`](kernel_gen/tools/mlir_gen_compare.py)
"""

# Case 列表:
# - CASE-1: 静态正向例子：`lhs + rhs` 的 i32 memory 输入应返回 i32 memory。
# - CASE-2: 动态正向例子：`lhs + rhs` 的 symbol shape i32 memory 输入应返回动态 i32 memory。
# - CASE-3: 静态正向例子：`lhs > rhs` 的 symbol 输入应返回 `i1`。
# - CASE-4: const 正向例子：`float(n)` 的 const 输入应返回 `f32`。
# - CASE-5: symbol 正向例子：`float(n)` 的 symbol 输入应返回 `f32`。
# - CASE-6: 静态正向例子：`view(src, ...)` 应返回 `dma.view` 的结果类型。
# - CASE-7: 失败例子：`view(src, ...)` 静态越界时应在构造阶段拒绝。

from __future__ import annotations

from pathlib import Path
import sys

REPO_ROOT = next(parent for parent in Path(__file__).resolve().parents if (parent / "kernel_gen").exists())
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from expectation.utils.case_runner import raise_if_failures, run_case
from kernel_gen.operation.dma import view
from kernel_gen.symbol_variable.memory import Memory, MemorySpace
from kernel_gen.symbol_variable.symbol_dim import SymbolDim
from kernel_gen.symbol_variable.type import NumericType
from kernel_gen.tools.mlir_gen_compare import mlir_gen_compare_text


# CASE-1 IR：静态正向例子：`lhs + rhs` 的 i32 memory 输入应返回 i32 memory。
CASE_1_IR = """builtin.module {
  func.func @add_memory_case_1(%0 : !nn.memory<[2, 3], [3, 1], i32, #nn.space<global>>, %1 : !nn.memory<[2, 3], [3, 1], i32, #nn.space<global>>) -> !nn.memory<[2, 3], [3, 1], i32, #nn.space<global>> {
    %2 = "nn.add"(%0, %1) {space = #nn.space<global>} : (!nn.memory<[2, 3], [3, 1], i32, #nn.space<global>>, !nn.memory<[2, 3], [3, 1], i32, #nn.space<global>>) -> !nn.memory<[2, 3], [3, 1], i32, #nn.space<global>>
    func.return %2 : !nn.memory<[2, 3], [3, 1], i32, #nn.space<global>>
  }
}"""

CASE_1_RUNTIME_ARGS = (
    Memory([2, 3], NumericType.Int32, space=MemorySpace.GM),
    Memory([2, 3], NumericType.Int32, space=MemorySpace.GM),
)


def add_memory_case_1(lhs, rhs):
    return lhs + rhs


# CASE-2 IR：动态正向例子：`lhs + rhs` 的 symbol shape i32 memory 输入应返回动态 i32 memory。
CASE_2_IR = """builtin.module {
  func.func @add_memory_case_2(%0 : !nn.memory<[M, N], [N, 1], i32, #nn.space<global>>, %1 : !nn.memory<[M, N], [N, 1], i32, #nn.space<global>>) -> !nn.memory<[M, N], [N, 1], i32, #nn.space<global>> {
    %2 = "nn.add"(%0, %1) {space = #nn.space<global>} : (!nn.memory<[M, N], [N, 1], i32, #nn.space<global>>, !nn.memory<[M, N], [N, 1], i32, #nn.space<global>>) -> !nn.memory<[M, N], [N, 1], i32, #nn.space<global>>
    func.return %2 : !nn.memory<[M, N], [N, 1], i32, #nn.space<global>>
  }
}"""

CASE_2_RUNTIME_ARGS = (
    Memory([SymbolDim("M"), SymbolDim("N")], NumericType.Int32, space=MemorySpace.GM),
    Memory([SymbolDim("M"), SymbolDim("N")], NumericType.Int32, space=MemorySpace.GM),
)


def add_memory_case_2(lhs, rhs):
    return lhs + rhs


# CASE-3 IR：静态正向例子：`lhs > rhs` 的 symbol 输入应返回 `i1`。
CASE_3_IR = """builtin.module {
  func.func @symbol_gt_case(%0 : !symbol.int<"M">, %1 : !symbol.int<"N">) -> i1 {
    %2 = symbol.gt %0, %1 : !symbol.int<"M">, !symbol.int<"N"> -> i1
    func.return %2 : i1
  }
}"""

CASE_3_RUNTIME_ARGS = (
    SymbolDim("M"),
    SymbolDim("N"),
)


def symbol_gt_case(lhs, rhs):
    return lhs > rhs


# CASE-4 IR：const 正向例子：`float(n)` 的 const 输入应返回 `f32`。
CASE_4_IR = """builtin.module {
  func.func @symbol_to_float_const_case(%0 : !symbol.int<"4">) -> f32 {
    %1 = symbol.to_float %0 : !symbol.int<"4"> -> f32
    func.return %1 : f32
  }
}"""

CASE_4_RUNTIME_ARGS = (4,)


def symbol_to_float_const_case(n):
    return float(n)


# CASE-5 IR：symbol 正向例子：`float(n)` 的 symbol 输入应返回 `f32`。
CASE_5_IR = """builtin.module {
  func.func @symbol_to_float_symbol_case(%0 : !symbol.int<"K">) -> f32 {
    %1 = symbol.to_float %0 : !symbol.int<"K"> -> f32
    func.return %1 : f32
  }
}"""

CASE_5_RUNTIME_ARGS = (SymbolDim("K"),)


def symbol_to_float_symbol_case(n):
    return float(n)


# CASE-6 IR：静态正向例子：`view(src, ...)` 应返回 `dma.view` 的结果类型。
CASE_6_IR = """builtin.module {
  func.func @view_kernel_case(%0 : !nn.memory<[4, 4], [4, 1], f32, #nn.space<global>>) -> !nn.memory<[2, 2], [1, 1], f32, #nn.space<global>> {
    %1 = symbol.const 1 : !symbol.int<"1">
    %2 = symbol.const 1 : !symbol.int<"1">
    %3 = symbol.const 2 : !symbol.int<"2">
    %4 = symbol.const 1 : !symbol.int<"1">
    %5 = symbol.const 1 : !symbol.int<"1">
    %6 = "dma.view"(%0, %1, %2, %3, %3, %4, %5) <{operandSegmentSizes = array<i32: 1, 2, 2, 2>}> : (!nn.memory<[4, 4], [4, 1], f32, #nn.space<global>>, !symbol.int<"1">, !symbol.int<"1">, !symbol.int<"2">, !symbol.int<"2">, !symbol.int<"1">, !symbol.int<"1">) -> !nn.memory<[2, 2], [1, 1], f32, #nn.space<global>>
    func.return %6 : !nn.memory<[2, 2], [1, 1], f32, #nn.space<global>>
  }
}"""

CASE_6_RUNTIME_ARGS = (
    Memory([4, 4], NumericType.Float32, space=MemorySpace.GM),
)


def view_kernel_case(src):
    return view(src, [1, 1], [2, 2], [1, 1])


CASE_7_RUNTIME_ARGS = (
    Memory([4, 4], NumericType.Float32, space=MemorySpace.GM),
)


def view_kernel_case_reject_oob(src):
    return view(src, [3, 3], [2, 2], [1, 1])


def _case_1_true() -> None:
    print("[CASE-1] 静态正向例子：lhs + rhs -> i32 memory")
    assert mlir_gen_compare_text(fn=add_memory_case_1, runtime_args=CASE_1_RUNTIME_ARGS, config=None, mlir_text=CASE_1_IR) is True


def _case_2_true() -> None:
    print("[CASE-2] 动态正向例子：lhs + rhs symbol shape -> i32 memory")
    assert mlir_gen_compare_text(fn=add_memory_case_2, runtime_args=CASE_2_RUNTIME_ARGS, config=None, mlir_text=CASE_2_IR) is True


def _case_3_true() -> None:
    print("[CASE-3] 静态正向例子：lhs > rhs -> i1")
    assert mlir_gen_compare_text(fn=symbol_gt_case, runtime_args=CASE_3_RUNTIME_ARGS, config=None, mlir_text=CASE_3_IR) is True


def _case_4_true() -> None:
    print("[CASE-4] const 正向例子：float(n) const -> f32")
    assert mlir_gen_compare_text(fn=symbol_to_float_const_case, runtime_args=CASE_4_RUNTIME_ARGS, config=None, mlir_text=CASE_4_IR) is True


def _case_5_true() -> None:
    print("[CASE-5] symbol 正向例子：float(n) symbol -> f32")
    assert mlir_gen_compare_text(fn=symbol_to_float_symbol_case, runtime_args=CASE_5_RUNTIME_ARGS, config=None, mlir_text=CASE_5_IR) is True


def _case_6_true() -> None:
    print("[CASE-6] 静态正向例子：view(src, ...) -> dma.view result type")
    assert mlir_gen_compare_text(fn=view_kernel_case, runtime_args=CASE_6_RUNTIME_ARGS, config=None, mlir_text=CASE_6_IR) is True


def _case_7_reject_invalid_view() -> None:
    print("[CASE-7] 失败例子：view(src, [3, 3], [2, 2], [1, 1]) 应在构造阶段因越界被拒绝")
    try:
        mlir_gen_compare_text(fn=view_kernel_case_reject_oob, runtime_args=CASE_7_RUNTIME_ARGS, config=None, mlir_text=CASE_6_IR)
    except ValueError as exc:
        assert "Index out of bounds" in str(exc)
    else:
        raise AssertionError("view with static out-of-bounds slice should be rejected before MLIR compare")


def main() -> None:
    failures: list[tuple[str, BaseException]] = []
    run_case(failures, "CASE-1", _case_1_true)
    run_case(failures, "CASE-2", _case_2_true)
    run_case(failures, "CASE-3", _case_3_true)
    run_case(failures, "CASE-4", _case_4_true)
    run_case(failures, "CASE-5", _case_5_true)
    run_case(failures, "CASE-6", _case_6_true)
    run_case(failures, "CASE-7", _case_7_reject_invalid_view)
    raise_if_failures("dsl mlir_gen return-type-from-body expectation", failures)


if __name__ == "__main__":
    main()
