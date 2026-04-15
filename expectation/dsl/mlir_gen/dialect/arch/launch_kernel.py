"""arch.launch_kernel expectation.

创建者: 榕
最后一次更改: 守护最好的爱莉希雅

功能说明:
- 使用 `mlir_gen_compare_text(...)` 直接比较完整 `builtin.module`。
- 锁定 `launch_kernel(callee, block, thread, subthread, *args)` 的目标公开合同：
  - const extent 输入应直接生成 `!symbol.int` 形参并透传到 `arch.launch<...>(@callee, args...)`
  - symbol extent 输入应直接透传到 `arch.launch<...>`

使用示例:
- `PYTHONPATH=. python expectation/dsl/mlir_gen/dialect/arch/launch_kernel.py`

关联文件:
- spec: [`spec/dsl/mlir_gen.md`](spec/dsl/mlir_gen.md)
- spec: [`spec/dialect/arch.md`](spec/dialect/arch.md)
- spec: [`spec/tools/mlir_gen_compare.md`](spec/tools/mlir_gen_compare.md)
- test: [`test/dsl/test_mlir_gen.py`](test/dsl/test_mlir_gen.py)
- test: [`test/tools/test_mlir_gen_compare.py`](test/tools/test_mlir_gen_compare.py)
- 功能实现: [`kernel_gen/dsl/mlir_gen.py`](kernel_gen/dsl/mlir_gen.py)
- 功能实现: [`kernel_gen/tools/mlir_gen_compare.py`](kernel_gen/tools/mlir_gen_compare.py)
"""

# Case 列表:
# - CASE-1: const 正向例子：const block/thread/subthread 输入应直接生成 `!symbol.int` 形参并透传到 `arch.launch<...>`。
# - CASE-2: symbol 正向例子：symbol block/thread/subthread 输入应直接透传到 `arch.launch<...>`。
# - CASE-3: 失败例子：静态 `thread=0` 应在前端 lowering 阶段拒绝。

from pathlib import Path
import sys

CURRENT_DIR = Path(__file__).resolve().parent
if str(CURRENT_DIR) in sys.path:
    sys.path.remove(str(CURRENT_DIR))

REPO_ROOT = Path(__file__).resolve().parents[5]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from expectation.utils.case_runner import raise_if_failures, run_case
from kernel_gen.dsl.ast_visitor import AstVisitorError
from kernel_gen.operation.arch import BarrierScope, BarrierVisibility, barrier, launch_kernel
from kernel_gen.symbol_variable.memory import Memory, MemorySpace
from kernel_gen.symbol_variable.symbol_dim import SymbolDim
from kernel_gen.symbol_variable.type import NumericType
from kernel_gen.tools.mlir_gen_compare import mlir_gen_compare_text

# CASE-1 IR：const 正向例子：const block/thread/subthread 输入应直接生成 `!symbol.int` 形参并透传到 `arch.launch<...>`。
CASE_1_IR = """builtin.module {
  func.func @launch_kernel_case_1(%0 : !nn.memory<[2, 3], [3, 1], f32, #nn.space<global>>, %1 : !symbol.int<"1">, %2 : !symbol.int<"4">, %3 : !symbol.int<"1">) {
    arch.launch<%1, %2, %3>(@launch_kernel_body, %0) : (!nn.memory<[2, 3], [3, 1], f32, #nn.space<global>>) -> ()
    func.return
  }
}"""

CASE_1_RUNTIME_ARGS = (
    Memory([2, 3], NumericType.Float32, space=MemorySpace.GM),
    SymbolDim(1),
    SymbolDim(4),
    SymbolDim(1),
)


def launch_kernel_body(lhs):
    barrier(visibility=[BarrierVisibility.TSM, BarrierVisibility.TLM], scope=BarrierScope.BLOCK)


def launch_kernel_case_1(lhs, block, thread, subthread):
    launch_kernel(launch_kernel_body, block, thread, subthread, lhs)


# CASE-2 IR：symbol 正向例子：symbol block/thread/subthread 输入应直接透传到 `arch.launch<...>`。
CASE_2_IR = """builtin.module {
  func.func @launch_kernel_case_2(%0 : !nn.memory<[M, N], [N, 1], f32, #nn.space<global>>, %1 : !symbol.int<"B">, %2 : !symbol.int<"T">, %3 : !symbol.int<"S">) {
    arch.launch<%1, %2, %3>(@launch_kernel_body, %0) : (!nn.memory<[M, N], [N, 1], f32, #nn.space<global>>) -> ()
    func.return
  }
}"""

CASE_2_RUNTIME_ARGS = (
    Memory([SymbolDim("M"), SymbolDim("N")], NumericType.Float32, space=MemorySpace.GM),
    SymbolDim("B"),
    SymbolDim("T"),
    SymbolDim("S"),
)


def launch_kernel_case_2(lhs, block, thread, subthread):
    launch_kernel(launch_kernel_body, block, thread, subthread, lhs)


CASE_3_RUNTIME_ARGS = (
    Memory([2, 3], NumericType.Float32, space=MemorySpace.GM),
)


def launch_kernel_case_3(lhs):
    launch_kernel(launch_kernel_body, 1, 0, 1, lhs)


def _case_1_true() -> None:
    print("[CASE-1] const 正向例子：launch_kernel(..., block, thread, subthread, lhs) 的 const 输入应直接生成 !symbol.int 形参并透传到 arch.launch")
    ok = mlir_gen_compare_text(fn=launch_kernel_case_1, runtime_args=CASE_1_RUNTIME_ARGS, config=None, mlir_text=CASE_1_IR)
    assert ok is True


def _case_2_true() -> None:
    print("[CASE-2] symbol 正向例子：launch_kernel(..., B, T, S, lhs) -> arch.launch<B,T,S>")
    ok = mlir_gen_compare_text(fn=launch_kernel_case_2, runtime_args=CASE_2_RUNTIME_ARGS, config=None, mlir_text=CASE_2_IR)
    assert ok is True


def _case_3_reject_zero_thread() -> None:
    print("[CASE-3] 失败例子：launch_kernel(..., thread=0, ...) 应在前端 lowering 阶段因非法 extent 被拒绝")
    try:
        mlir_gen_compare_text(fn=launch_kernel_case_3, runtime_args=CASE_3_RUNTIME_ARGS, config=None, mlir_text=CASE_1_IR)
    except AstVisitorError as exc:
        assert "thread must be > 0" in str(exc)
    else:
        raise AssertionError("launch_kernel with thread=0 should be rejected during MLIR lowering")


def main() -> None:
    failures: list[tuple[str, BaseException]] = []
    run_case(failures, "CASE-1", _case_1_true)
    run_case(failures, "CASE-2", _case_2_true)
    run_case(failures, "CASE-3", _case_3_reject_zero_thread)
    raise_if_failures("dsl mlir_gen arch.launch_kernel expectation", failures)


if __name__ == "__main__":
    main()
