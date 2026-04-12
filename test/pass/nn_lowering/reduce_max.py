"""nn_lowering reduce_max tests.

创建者: 金铲铲大作战
最后一次更改: 金铲铲大作战

功能说明:
- 使用 ircheck 文本验证 `nn.reduce_max` lowering 目标为 `kernel.reduce(kind=max)`。

使用示例:
- pytest -q test/pass/nn_lowering/reduce_max.py

关联文件:
- spec: spec/pass/lowering/nn_lowering.md
- test: test/pass/nn_lowering/reduce_max.py
- 功能实现: kernel_gen/passes/lowering/nn_to_kernel.py
"""

from __future__ import annotations

import sys
from pathlib import Path

from kernel_gen.tools.ircheck import run_ircheck_text

REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))


CASE_TEXT_STATIC = """// COMPILE_ARGS: --pass lower-nn
// CASE: 正例：静态 nn.reduce_max 输入应 lower 为 dma.alloc + kernel.reduce(kind=max) + func.return。
// CHECK: builtin.module {
// CHECK-NEXT: func.func @reduce_max_kernel(%arg0 : !nn.memory<[4, 8], [8, 1], f32, #nn.space<global>>) -> !nn.memory<[4, 1], [1, 1], f32, #nn.space<global>> {
// CHECK-NEXT: %0 = "dma.alloc"() <{operandSegmentSizes = array<i32: 0>}> : () -> !nn.memory<[4, 1], [1, 1], f32, #nn.space<global>>
// CHECK-NEXT: "kernel.reduce"(%arg0, %0) {kind = "max", axis = 1 : i64, keepdim = true, space = #nn.space<global>} : (!nn.memory<[4, 8], [8, 1], f32, #nn.space<global>>, !nn.memory<[4, 1], [1, 1], f32, #nn.space<global>>) -> ()
// CHECK-NEXT: func.return %0 : !nn.memory<[4, 1], [1, 1], f32, #nn.space<global>>
// CHECK-NEXT: }
// CHECK-NEXT: }
// CHECK-NOT: nn.reduce_max

builtin.module {
  func.func @reduce_max_kernel(%arg0: !nn.memory<[4, 8], [8, 1], f32, #nn.space<global>>) -> !nn.memory<[4, 1], [1, 1], f32, #nn.space<global>> {
    %0 = "nn.reduce_max"(%arg0) {axes = [#builtin.int<1>], keepdim = #builtin.int<1>, space = #nn.space<global>} : (!nn.memory<[4, 8], [8, 1], f32, #nn.space<global>>) -> !nn.memory<[4, 1], [1, 1], f32, #nn.space<global>>
    func.return %0 : !nn.memory<[4, 1], [1, 1], f32, #nn.space<global>>
  }
}
"""

CASE_TEXT_DYNAMIC = """// COMPILE_ARGS: --pass lower-nn
// CASE: 正例：符号维度 nn.reduce_max 输入应 lower 为 dma.alloc + kernel.reduce(kind=max) + func.return。
// CHECK: builtin.module {
// CHECK-NEXT: func.func @reduce_max_kernel(%arg0 : !nn.memory<[M, N], [N, 1], f32, #nn.space<global>>) -> !nn.memory<[M, 1], [1, 1], f32, #nn.space<global>> {
// CHECK-NEXT: %0 = "symbol.get_dim"(%arg0) {axis = #builtin.int<0>} : (!nn.memory<[M, N], [N, 1], f32, #nn.space<global>>) -> !symbol.int<"M">
// CHECK-NEXT: %1 = "dma.alloc"(%0) <{operandSegmentSizes = array<i32: 1>}> : (!symbol.int<"M">) -> !nn.memory<[M, 1], [1, 1], f32, #nn.space<global>>
// CHECK-NEXT: "kernel.reduce"(%arg0, %1) {kind = "max", axis = 1 : i64, keepdim = true, space = #nn.space<global>} : (!nn.memory<[M, N], [N, 1], f32, #nn.space<global>>, !nn.memory<[M, 1], [1, 1], f32, #nn.space<global>>) -> ()
// CHECK-NEXT: func.return %1 : !nn.memory<[M, 1], [1, 1], f32, #nn.space<global>>
// CHECK-NEXT: }
// CHECK-NEXT: }
// CHECK-NOT: nn.reduce_max

builtin.module {
  func.func @reduce_max_kernel(%arg0: !nn.memory<[M, N], [N, 1], f32, #nn.space<global>>) -> !nn.memory<[M, 1], [1, 1], f32, #nn.space<global>> {
    %0 = "nn.reduce_max"(%arg0) {axes = [#builtin.int<1>], keepdim = #builtin.int<1>, space = #nn.space<global>} : (!nn.memory<[M, N], [N, 1], f32, #nn.space<global>>) -> !nn.memory<[M, 1], [1, 1], f32, #nn.space<global>>
    func.return %0 : !nn.memory<[M, 1], [1, 1], f32, #nn.space<global>>
  }
}
"""


def _assert_ircheck_ok(case_text: str, source_path: str) -> None:
    """运行 ircheck 文本并断言通过。

    创建者: 金铲铲大作战
    最后一次更改: 金铲铲大作战

    功能说明:
    - 调用 `run_ircheck_text` 并校验 ok/exit_code。

    使用示例:
    - _assert_ircheck_ok(CASE_TEXT_STATIC, "reduce_max.py:static")

    关联文件:
    - spec: spec/pass/lowering/nn_lowering.md
    - test: test/pass/nn_lowering/reduce_max.py
    - 功能实现: kernel_gen/tools/ircheck.py
    """

    result = run_ircheck_text(case_text, source_path=source_path)
    assert result.ok is True, (
        f"expected ok=True, got ok={result.ok}, exit_code={result.exit_code}, message={result.message!r}"
    )
    assert result.exit_code == 0, f"expected exit_code=0, got {result.exit_code}"
    assert "kernel.reduce" in result.actual_ir, "actual_ir must contain kernel.reduce"
    assert "nn.reduce_max" not in result.actual_ir, "actual_ir must not contain residual nn.reduce_max"


# TC-PASS-NNL-011
# 创建者: 金铲铲大作战
# 最后一次更改: 金铲铲大作战
# 最近一次运行测试时间: 2026-04-12 08:20:00 +0800
# 最近一次运行成功时间: 2026-04-12 08:20:00 +0800
# 测试目的: 验证 nn.reduce_max lowering 目标为 kernel.reduce(kind=max)（静态形态）。
# 使用示例: pytest -q test/pass/nn_lowering/reduce_max.py -k test_nn_lowering_reduce_max_static
# 对应功能实现文件路径: kernel_gen/passes/lowering/nn_to_kernel.py
# 对应 spec 文件路径: spec/pass/lowering/nn_lowering.md
# 对应测试文件路径: test/pass/nn_lowering/reduce_max.py
def test_nn_lowering_reduce_max_static() -> None:
    _assert_ircheck_ok(CASE_TEXT_STATIC, "test/pass/nn_lowering/reduce_max.py:static")


# TC-PASS-NNL-011
# 创建者: 金铲铲大作战
# 最后一次更改: 金铲铲大作战
# 最近一次运行测试时间: 2026-04-12 08:20:00 +0800
# 最近一次运行成功时间: 2026-04-12 08:20:00 +0800
# 测试目的: 验证 nn.reduce_max lowering 目标为 kernel.reduce(kind=max)（符号维度）。
# 使用示例: pytest -q test/pass/nn_lowering/reduce_max.py -k test_nn_lowering_reduce_max_dynamic
# 对应功能实现文件路径: kernel_gen/passes/lowering/nn_to_kernel.py
# 对应 spec 文件路径: spec/pass/lowering/nn_lowering.md
# 对应测试文件路径: test/pass/nn_lowering/reduce_max.py
def test_nn_lowering_reduce_max_dynamic() -> None:
    _assert_ircheck_ok(CASE_TEXT_DYNAMIC, "test/pass/nn_lowering/reduce_max.py:dynamic")
