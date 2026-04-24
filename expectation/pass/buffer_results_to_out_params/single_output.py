# [immutable-file]
"""`buffer_results_to_out_params` single output ircheck expectation。

创建者: 守护最好的爱莉希雅
最后一次更改: 守护最好的爱莉希雅

功能说明:
- 使用 `ircheck` 黑盒锁定 `BufferResultsToOutParamsPass` 对单个 memory result 的
  caller/callee 同步改写。
- 参考 MLIR 官方 `-buffer-results-to-out-params` 的模块级原子改写口径，同时保留
 本仓库当前 IR 已支持的动态符号 shape 场景。

使用示例:
- `PYTHONPATH=. python expectation/pass/buffer_results_to_out_params/single_output.py`

关联文件:
- spec: [`spec/pass/lowering/buffer_results_to_out_params.md`](../../../spec/pass/lowering/buffer_results_to_out_params.md)
- spec: [`spec/tools/ircheck.md`](../../../spec/tools/ircheck.md)
- test: [`test/pass/test_buffer_results_to_out_params.py`](../../../test/pass/test_buffer_results_to_out_params.py)
- 功能实现: [`expectation/pass/buffer_results_to_out_params/single_output.py`](../../../expectation/pass/buffer_results_to_out_params/single_output.py)
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

STATIC_SRC = random_static_memory_spec("src", rank=random_rank())
DYNAMIC_SRC = random_dynamic_memory_spec("src", rank=random_rank())

CASE_TEXT_STATIC = f"""// COMPILE_ARGS: --pass buffer-results-to-out-params
// CASE: case-single-output-static: 单个静态 memory result 重写为前置 arg0，caller 显式补 out 实参。
// CHECK: builtin.module {{
// CHECK-NEXT: func.func @copy(%0: {STATIC_SRC.type_ir} {{name = "arg0"}}, %1: {STATIC_SRC.type_ir} {{name = "src"}}) {{
// CHECK-NEXT: func.return
// CHECK-NEXT: }}
// CHECK-NEXT: func.func @caller(%0: {STATIC_SRC.type_ir} {{name = "src"}}) {{
// CHECK-NEXT: %1 = "dma.alloc"() <{{operandSegmentSizes = array<i32: 0>}}> : () -> {STATIC_SRC.type_ir}
// CHECK-NEXT: func.call @copy(%1, %0) : ({STATIC_SRC.type_ir}, {STATIC_SRC.type_ir}) -> ()
// CHECK-NEXT: func.return
// CHECK-NEXT: }}
// CHECK-NEXT: }}
// CHECK-NOT: %1 = func.call @copy(%0)

builtin.module {{
  func.func @copy(%0 : {STATIC_SRC.type_ir} {{name = "src"}}) -> ({STATIC_SRC.type_ir}) {{
    func.return %0 : {STATIC_SRC.type_ir}
  }}
  func.func @caller(%0 : {STATIC_SRC.type_ir} {{name = "src"}}) {{
    %1 = func.call @copy(%0) : ({STATIC_SRC.type_ir}) -> ({STATIC_SRC.type_ir})
    func.return
  }}
}}
"""

CASE_TEXT_DYNAMIC = f"""// COMPILE_ARGS: --pass buffer-results-to-out-params
// CASE: case-single-output-dynamic: 单个动态 memory result 重写为前置 arg0，caller 显式补 out 实参。
// CHECK: builtin.module {{
// CHECK-NEXT: func.func @copy(%0: {DYNAMIC_SRC.type_ir} {{name = "arg0"}}, %1: {DYNAMIC_SRC.type_ir} {{name = "src"}}) {{
// CHECK-NEXT: func.return
// CHECK-NEXT: }}
// CHECK-NEXT: func.func @caller(%0: {DYNAMIC_SRC.type_ir} {{name = "src"}}) {{
// CHECK-NEXT: %1 = "dma.alloc"() <{{operandSegmentSizes = array<i32: 0>}}> : () -> {DYNAMIC_SRC.type_ir}
// CHECK-NEXT: func.call @copy(%1, %0) : ({DYNAMIC_SRC.type_ir}, {DYNAMIC_SRC.type_ir}) -> ()
// CHECK-NEXT: func.return
// CHECK-NEXT: }}
// CHECK-NEXT: }}
// CHECK-NOT: %1 = func.call @copy(%0)

builtin.module {{
  func.func @copy(%0 : {DYNAMIC_SRC.type_ir} {{name = "src"}}) -> ({DYNAMIC_SRC.type_ir}) {{
    func.return %0 : {DYNAMIC_SRC.type_ir}
  }}
  func.func @caller(%0 : {DYNAMIC_SRC.type_ir} {{name = "src"}}) {{
    %1 = func.call @copy(%0) : ({DYNAMIC_SRC.type_ir}) -> ({DYNAMIC_SRC.type_ir})
    func.return
  }}
}}
"""


def _case_1() -> None:
    """正例：静态单输出必须改写成前置 out 参数。"""

    result = run_ircheck_text(
        CASE_TEXT_STATIC,
        source_path="expectation/pass/buffer_results_to_out_params/single_output.py:case-1",
    )
    assert result.ok is True, result.message
    assert result.exit_code == 0, f"expected exit_code=0, got {result.exit_code}"
    assert "func.call @copy(%1, %0)" in result.actual_ir
    assert "%1 = func.call @copy(%0)" not in result.actual_ir
    print_case_actual_ir("CASE-1", CASE_TEXT_STATIC, result.actual_ir, fallback="single output static")


def _case_2() -> None:
    """正例：动态单输出也必须改写成前置 out 参数。"""

    result = run_ircheck_text(
        CASE_TEXT_DYNAMIC,
        source_path="expectation/pass/buffer_results_to_out_params/single_output.py:case-2",
    )
    assert result.ok is True, result.message
    assert result.exit_code == 0, f"expected exit_code=0, got {result.exit_code}"
    assert "func.call @copy(%1, %0)" in result.actual_ir
    assert "%1 = func.call @copy(%0)" not in result.actual_ir
    print_case_actual_ir("CASE-2", CASE_TEXT_DYNAMIC, result.actual_ir, fallback="single output dynamic")


def main() -> None:
    """运行 single output ircheck expectation。"""

    failures: list[tuple[str, BaseException]] = []
    run_case(failures, "CASE-1", _case_1)
    run_case(failures, "CASE-2", _case_2)
    raise_if_failures("buffer_results_to_out_params single output expectation", failures)


if __name__ == "__main__":
    main()
