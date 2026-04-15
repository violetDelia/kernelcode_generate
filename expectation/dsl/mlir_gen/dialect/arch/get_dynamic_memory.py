"""arch.get_dynamic_memory expectation.

创建者: 榕
最后一次更改: 守护最好的爱莉希雅

功能说明:
- 使用 `mlir_gen_compare_text(...)` 直接比较完整 `builtin.module`。
- 锁定 `arch.get_dynamic_memory` 的目标公开合同：按不同 `MemorySpace` 生成显式查询 op。

使用示例:
- `PYTHONPATH=. python expectation/dsl/mlir_gen/dialect/arch/get_dynamic_memory.py`

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
# - CASE-1: 正向例子：`MemorySpace.SM` 应生成带 `SM_SIZE` 静态容量的 `arch.get_dynamic_memory #nn.space<shared>`。
# - CASE-2: 正向例子：`MemorySpace.LM` 应生成带 `LM_SIZE` 静态容量的 `arch.get_dynamic_memory #nn.space<local>`。
# - CASE-3: 失败例子：`MemorySpace.GM` 不是片上空间，应在构造阶段拒绝。

from pathlib import Path
import sys

CURRENT_DIR = Path(__file__).resolve().parent
if str(CURRENT_DIR) in sys.path:
    sys.path.remove(str(CURRENT_DIR))

REPO_ROOT = Path(__file__).resolve().parents[5]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from expectation.utils.case_runner import raise_if_failures, run_case
from kernel_gen.operation.arch import get_dynamic_memory
from kernel_gen.symbol_variable.memory import MemorySpace
from kernel_gen.tools.mlir_gen_compare import mlir_gen_compare_text

# CASE-1 IR：正向例子：`MemorySpace.SM` 应生成带 `SM_SIZE` 静态容量的 `arch.get_dynamic_memory #nn.space<shared>`。
CASE_1_IR = """builtin.module {
  func.func @get_dynamic_memory_case_1() -> !nn.memory<[SM_SIZE], [1], i8, #nn.space<shared>> {
    %0 = arch.get_dynamic_memory #nn.space<shared> : !nn.memory<[SM_SIZE], [1], i8, #nn.space<shared>>
    func.return %0 : !nn.memory<[SM_SIZE], [1], i8, #nn.space<shared>>
  }
}"""


def get_dynamic_memory_case_1():
    return get_dynamic_memory(MemorySpace.SM)


# CASE-2 IR：正向例子：`MemorySpace.LM` 应生成带 `LM_SIZE` 静态容量的 `arch.get_dynamic_memory #nn.space<local>`。
CASE_2_IR = """builtin.module {
  func.func @get_dynamic_memory_case_2() -> !nn.memory<[LM_SIZE], [1], i8, #nn.space<local>> {
    %0 = arch.get_dynamic_memory #nn.space<local> : !nn.memory<[LM_SIZE], [1], i8, #nn.space<local>>
    func.return %0 : !nn.memory<[LM_SIZE], [1], i8, #nn.space<local>>
  }
}"""


def get_dynamic_memory_case_2():
    return get_dynamic_memory(MemorySpace.LM)


def get_dynamic_memory_case_3():
    return get_dynamic_memory(MemorySpace.GM)


def _case_1_true() -> None:
    print("[CASE-1] 正向例子：get_dynamic_memory(MemorySpace.SM) -> arch.get_dynamic_memory #nn.space<shared>，结果类型固定为 !nn.memory<[SM_SIZE], [1], i8, #nn.space<shared>>")
    ok = mlir_gen_compare_text(fn=get_dynamic_memory_case_1, runtime_args=(), config=None, mlir_text=CASE_1_IR)
    assert ok is True


def _case_2_true() -> None:
    print("[CASE-2] 正向例子：get_dynamic_memory(MemorySpace.LM) -> arch.get_dynamic_memory #nn.space<local>，结果类型固定为 !nn.memory<[LM_SIZE], [1], i8, #nn.space<local>>")
    ok = mlir_gen_compare_text(fn=get_dynamic_memory_case_2, runtime_args=(), config=None, mlir_text=CASE_2_IR)
    assert ok is True


def _case_3_reject_offchip_space() -> None:
    print("[CASE-3] 失败例子：get_dynamic_memory(MemorySpace.GM) 应在构造阶段因 space 非片上 MemorySpace 被拒绝")
    try:
        mlir_gen_compare_text(fn=get_dynamic_memory_case_3, runtime_args=(), config=None, mlir_text=CASE_1_IR)
    except ValueError as exc:
        assert "space must be on-chip MemorySpace" in str(exc)
    else:
        raise AssertionError("get_dynamic_memory(MemorySpace.GM) should be rejected before MLIR compare")


def main() -> None:
    failures: list[tuple[str, BaseException]] = []
    run_case(failures, "CASE-1", _case_1_true)
    run_case(failures, "CASE-2", _case_2_true)
    run_case(failures, "CASE-3", _case_3_reject_offchip_space)
    raise_if_failures("dsl mlir_gen arch.get_dynamic_memory expectation", failures)


if __name__ == "__main__":
    main()
