"""DSL import-bound helper expectation.

创建者: 大闸蟹
最后一次更改: 守护最好的爱莉希雅

功能说明:
- 使用 `mlir_gen_compare_text(...)` 比较完整 `builtin.module`。
- 锁定 `dma` / `arch` helper 的导入绑定解析正向合同。

使用示例:
- `PYTHONPATH=. python expectation/dsl/mlir_gen/import_bound_helper.py`

关联文件:
- spec: [`spec/dsl/ast.md`](spec/dsl/ast.md)
- spec: [`spec/dsl/mlir_gen.md`](spec/dsl/mlir_gen.md)
- spec: [`spec/tools/mlir_gen_compare.md`](spec/tools/mlir_gen_compare.md)
- test: [`test/dsl/test_ast.py`](test/dsl/test_ast.py)
- test: [`test/tools/test_mlir_gen_compare.py`](test/tools/test_mlir_gen_compare.py)
- 功能实现: [`kernel_gen/dsl/ast.py`](kernel_gen/dsl/ast.py)
- 功能实现: [`kernel_gen/dsl/mlir_gen.py`](kernel_gen/dsl/mlir_gen.py)
- 功能实现: [`kernel_gen/tools/mlir_gen_compare.py`](kernel_gen/tools/mlir_gen_compare.py)
"""

# Case 列表:
# - CASE-1: `import kernel_gen.operation.dma as cc` 后，`cc.slice(...)` 应可解析。
# - CASE-2: `from kernel_gen.operation import dma as dma_pkg` 后，`dma_pkg.view(...)` 应可解析。
# - CASE-3: `from kernel_gen.operation.dma import slice as cut` 后，`cut(...)` 应可解析。
# - CASE-4: `import kernel_gen.operation.arch as hw` 后，`hw.get_dynamic_memory(...)` 应可解析。
# - CASE-5: `from kernel_gen.operation.arch import get_dynamic_memory as dyn` 后，`dyn(...)` 应可解析。
# - CASE-6: `dyn(MemorySpace.GM)` 应在构造阶段因非片上空间被拒绝。

from __future__ import annotations

from pathlib import Path
import sys

REPO_ROOT = next(parent for parent in Path(__file__).resolve().parents if (parent / "kernel_gen").exists())
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from expectation.utils.case_runner import raise_if_failures, run_case
from kernel_gen.symbol_variable.memory import Memory, MemorySpace
from kernel_gen.symbol_variable.type import NumericType
from kernel_gen.tools.mlir_gen_compare import mlir_gen_compare_text
import kernel_gen.operation.arch as hw
import kernel_gen.operation.dma as cc
from kernel_gen.operation import dma as dma_pkg
from kernel_gen.operation.arch import get_dynamic_memory as dyn
from kernel_gen.operation.dma import slice as cut


# CASE-1 IR：`import kernel_gen.operation.dma as cc` 后，`cc.slice(...)` 应可解析。
CASE_1_IR = """builtin.module {
  func.func @dma_module_alias_slice_case(%0 : !nn.memory<[4, 4], [4, 1], f32, #nn.space<global>>) -> !nn.memory<[2, 2], [2, 1], f32, #nn.space<local>> {
    %1 = symbol.const 0 : !symbol.int<"0">
    %2 = symbol.const 0 : !symbol.int<"0">
    %3 = symbol.const 2 : !symbol.int<"2">
    %4 = symbol.const 2 : !symbol.int<"2">
    %5 = symbol.const 1 : !symbol.int<"1">
    %6 = symbol.const 1 : !symbol.int<"1">
    %9 = "dma.alloc"() <{operandSegmentSizes = array<i32: 0>}> : () -> !nn.memory<[2, 2], [2, 1], f32, #nn.space<local>>
    "dma.slice"(%9, %0, %1, %2, %3, %4, %5, %6) <{operandSegmentSizes = array<i32: 1, 1, 2, 2, 2>}> : (!nn.memory<[2, 2], [2, 1], f32, #nn.space<local>>, !nn.memory<[4, 4], [4, 1], f32, #nn.space<global>>, !symbol.int<"0">, !symbol.int<"0">, !symbol.int<"2">, !symbol.int<"2">, !symbol.int<"1">, !symbol.int<"1">) -> ()
    func.return %9 : !nn.memory<[2, 2], [2, 1], f32, #nn.space<local>>
  }
}"""

CASE_1_RUNTIME_ARGS = (
    Memory([4, 4], NumericType.Float32, space=MemorySpace.GM),
)


def dma_module_alias_slice_case(src):
    return cc.slice(src, [0, 0], [2, 2], [1, 1], MemorySpace.LM)


# CASE-2 IR：`from kernel_gen.operation import dma as dma_pkg` 后，`dma_pkg.view(...)` 应可解析。
CASE_2_IR = """builtin.module {
  func.func @dma_package_alias_view_case(%0 : !nn.memory<[4, 4], [4, 1], f32, #nn.space<global>>) -> !nn.memory<[2, 2], [1, 1], f32, #nn.space<global>> {
    %1 = symbol.const 1 : !symbol.int<"1">
    %2 = symbol.const 1 : !symbol.int<"1">
    %3 = symbol.const 2 : !symbol.int<"2">
    %4 = symbol.const 1 : !symbol.int<"1">
    %5 = symbol.const 1 : !symbol.int<"1">
    %6 = "dma.view"(%0, %1, %2, %3, %3, %4, %5) <{operandSegmentSizes = array<i32: 1, 2, 2, 2>}> : (!nn.memory<[4, 4], [4, 1], f32, #nn.space<global>>, !symbol.int<"1">, !symbol.int<"1">, !symbol.int<"2">, !symbol.int<"2">, !symbol.int<"1">, !symbol.int<"1">) -> !nn.memory<[2, 2], [1, 1], f32, #nn.space<global>>
    func.return %6 : !nn.memory<[2, 2], [1, 1], f32, #nn.space<global>>
  }
}"""

CASE_2_RUNTIME_ARGS = CASE_1_RUNTIME_ARGS


def dma_package_alias_view_case(src):
    return dma_pkg.view(src, [1, 1], [2, 2], [1, 1])


# CASE-3 IR：`from kernel_gen.operation.dma import slice as cut` 后，`cut(...)` 应可解析。
CASE_3_IR = """builtin.module {
  func.func @dma_direct_symbol_alias_slice_case(%0 : !nn.memory<[4, 4], [4, 1], f32, #nn.space<global>>) -> !nn.memory<[2, 2], [2, 1], f32, #nn.space<local>> {
    %1 = symbol.const 0 : !symbol.int<"0">
    %2 = symbol.const 0 : !symbol.int<"0">
    %3 = symbol.const 2 : !symbol.int<"2">
    %4 = symbol.const 2 : !symbol.int<"2">
    %5 = symbol.const 1 : !symbol.int<"1">
    %6 = symbol.const 1 : !symbol.int<"1">
    %9 = "dma.alloc"() <{operandSegmentSizes = array<i32: 0>}> : () -> !nn.memory<[2, 2], [2, 1], f32, #nn.space<local>>
    "dma.slice"(%9, %0, %1, %2, %3, %4, %5, %6) <{operandSegmentSizes = array<i32: 1, 1, 2, 2, 2>}> : (!nn.memory<[2, 2], [2, 1], f32, #nn.space<local>>, !nn.memory<[4, 4], [4, 1], f32, #nn.space<global>>, !symbol.int<"0">, !symbol.int<"0">, !symbol.int<"2">, !symbol.int<"2">, !symbol.int<"1">, !symbol.int<"1">) -> ()
    func.return %9 : !nn.memory<[2, 2], [2, 1], f32, #nn.space<local>>
  }
}"""

CASE_3_RUNTIME_ARGS = CASE_1_RUNTIME_ARGS


def dma_direct_symbol_alias_slice_case(src):
    return cut(src, [0, 0], [2, 2], [1, 1], MemorySpace.LM)


# CASE-4 IR：`import kernel_gen.operation.arch as hw` 后，`hw.get_dynamic_memory(...)` 应可解析。
CASE_4_IR = """builtin.module {
  func.func @arch_module_alias_case() -> !nn.memory<[SM_SIZE], [1], i8, #nn.space<shared>> {
    %0 = arch.get_dynamic_memory #nn.space<shared> : !nn.memory<[SM_SIZE], [1], i8, #nn.space<shared>>
    func.return %0 : !nn.memory<[SM_SIZE], [1], i8, #nn.space<shared>>
  }
}"""


def arch_module_alias_case():
    return hw.get_dynamic_memory(MemorySpace.SM)


# CASE-5 IR：`from kernel_gen.operation.arch import get_dynamic_memory as dyn` 后，`dyn(...)` 应可解析。
CASE_5_IR = """builtin.module {
  func.func @arch_direct_symbol_alias_case() -> !nn.memory<[LM_SIZE], [1], i8, #nn.space<local>> {
    %0 = arch.get_dynamic_memory #nn.space<local> : !nn.memory<[LM_SIZE], [1], i8, #nn.space<local>>
    func.return %0 : !nn.memory<[LM_SIZE], [1], i8, #nn.space<local>>
  }
}"""


def arch_direct_symbol_alias_case():
    return dyn(MemorySpace.LM)


def arch_direct_symbol_alias_case_2():
    return dyn(MemorySpace.GM)


def _case_1_true() -> None:
    print("[CASE-1] module alias：cc.slice(...)")
    assert mlir_gen_compare_text(fn=dma_module_alias_slice_case, runtime_args=CASE_1_RUNTIME_ARGS, config=None, mlir_text=CASE_1_IR) is True


def _case_2_true() -> None:
    print("[CASE-2] package alias：dma_pkg.view(...)")
    assert mlir_gen_compare_text(fn=dma_package_alias_view_case, runtime_args=CASE_2_RUNTIME_ARGS, config=None, mlir_text=CASE_2_IR) is True


def _case_3_true() -> None:
    print("[CASE-3] direct symbol alias：cut(...)")
    assert mlir_gen_compare_text(fn=dma_direct_symbol_alias_slice_case, runtime_args=CASE_3_RUNTIME_ARGS, config=None, mlir_text=CASE_3_IR) is True


def _case_4_true() -> None:
    print("[CASE-4] module alias：hw.get_dynamic_memory(...)")
    assert mlir_gen_compare_text(fn=arch_module_alias_case, runtime_args=(), config=None, mlir_text=CASE_4_IR) is True


def _case_5_true() -> None:
    print("[CASE-5] direct symbol alias：dyn(...)")
    assert mlir_gen_compare_text(fn=arch_direct_symbol_alias_case, runtime_args=(), config=None, mlir_text=CASE_5_IR) is True


def _case_6_reject_offchip_space() -> None:
    print("[CASE-6] 失败例子：dyn(MemorySpace.GM) 应在构造阶段因非片上空间被拒绝")
    try:
        mlir_gen_compare_text(fn=arch_direct_symbol_alias_case_2, runtime_args=(), config=None, mlir_text=CASE_5_IR)
    except ValueError as exc:
        assert "space must be on-chip MemorySpace" in str(exc)
    else:
        raise AssertionError("dyn(MemorySpace.GM) should be rejected before MLIR compare")


def main() -> None:
    failures: list[tuple[str, BaseException]] = []
    run_case(failures, "CASE-1", _case_1_true)
    run_case(failures, "CASE-2", _case_2_true)
    run_case(failures, "CASE-3", _case_3_true)
    run_case(failures, "CASE-4", _case_4_true)
    run_case(failures, "CASE-5", _case_5_true)
    run_case(failures, "CASE-6", _case_6_reject_offchip_space)
    raise_if_failures("dsl mlir_gen import_bound_helper expectation", failures)


if __name__ == "__main__":
    main()
