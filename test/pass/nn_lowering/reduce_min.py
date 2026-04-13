"""nn_lowering reduce_min tests.

创建者: 金铲铲大作战
最后一次更改: 金铲铲大作战

功能说明:
- 使用 ircheck 文本验证 `nn.reduce_min` lowering 目标为 `kernel.reduce(kind=min)`。

使用示例:
- pytest -q test/pass/nn_lowering/reduce_min.py

关联文件:
- spec: spec/pass/lowering/nn_lowering/reduce_softmax_lowering.md
- test: test/pass/nn_lowering/reduce_min.py
- 功能实现: kernel_gen/passes/lowering/nn_lowering/reduce_softmax_lowering.py
"""

from __future__ import annotations

import sys
from pathlib import Path

from kernel_gen.tools.ircheck import run_ircheck_text

REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))


CASE_TEXT_STATIC = """// COMPILE_ARGS: --pass lower-nn
// CASE: 正例：静态 nn.reduce_min 输入应 lower 为 dma.alloc + kernel.reduce(kind=min) + func.return。
// CHECK: builtin.module {
// CHECK-NEXT: func.func @reduce_min_kernel(%arg0 : !nn.memory<[4, 8], [8, 1], f32, #nn.space<global>>) -> !nn.memory<[4, 1], [1, 1], f32, #nn.space<global>> {
// CHECK-NEXT: %0 = "dma.alloc"() <{operandSegmentSizes = array<i32: 0>}> : () -> !nn.memory<[4, 1], [1, 1], f32, #nn.space<global>>
// CHECK-NEXT: "kernel.reduce"(%arg0, %0) {axis = 1 : i64, keepdim = true, kind = "min", space = #nn.space<global>} : (!nn.memory<[4, 8], [8, 1], f32, #nn.space<global>>, !nn.memory<[4, 1], [1, 1], f32, #nn.space<global>>) -> ()
// CHECK-NEXT: func.return %0 : !nn.memory<[4, 1], [1, 1], f32, #nn.space<global>>
// CHECK-NEXT: }
// CHECK-NEXT: }
// CHECK-NOT: nn.reduce_min

builtin.module {
  func.func @reduce_min_kernel(%arg0: !nn.memory<[4, 8], [8, 1], f32, #nn.space<global>>) -> !nn.memory<[4, 1], [1, 1], f32, #nn.space<global>> {
    %0 = "nn.reduce_min"(%arg0) {axes = [#builtin.int<1>], keepdim = #builtin.int<1>, space = #nn.space<global>} : (!nn.memory<[4, 8], [8, 1], f32, #nn.space<global>>) -> !nn.memory<[4, 1], [1, 1], f32, #nn.space<global>>
    func.return %0 : !nn.memory<[4, 1], [1, 1], f32, #nn.space<global>>
  }
}
"""

CASE_TEXT_DYNAMIC = """// COMPILE_ARGS: --pass lower-nn
// CASE: 正例：符号维度 nn.reduce_min 输入应 lower 为 dma.alloc + kernel.reduce(kind=min) + func.return。
// CHECK: builtin.module {
// CHECK-NEXT: func.func @reduce_min_kernel(%arg0 : !nn.memory<[M, N], [N, 1], f32, #nn.space<global>>) -> !nn.memory<[M, 1], [1, 1], f32, #nn.space<global>> {
// CHECK-NEXT: %0 = "symbol.get_dim"(%arg0) {axis = #builtin.int<0>} : (!nn.memory<[M, N], [N, 1], f32, #nn.space<global>>) -> !symbol.int<"M">
// CHECK-NEXT: %1 = "dma.alloc"(%0) <{operandSegmentSizes = array<i32: 1>}> : (!symbol.int<"M">) -> !nn.memory<[M, 1], [1, 1], f32, #nn.space<global>>
// CHECK-NEXT: "kernel.reduce"(%arg0, %1) {axis = 1 : i64, keepdim = true, kind = "min", space = #nn.space<global>} : (!nn.memory<[M, N], [N, 1], f32, #nn.space<global>>, !nn.memory<[M, 1], [1, 1], f32, #nn.space<global>>) -> ()
// CHECK-NEXT: func.return %1 : !nn.memory<[M, 1], [1, 1], f32, #nn.space<global>>
// CHECK-NEXT: }
// CHECK-NEXT: }
// CHECK-NOT: nn.reduce_min

builtin.module {
  func.func @reduce_min_kernel(%arg0: !nn.memory<[M, N], [N, 1], f32, #nn.space<global>>) -> !nn.memory<[M, 1], [1, 1], f32, #nn.space<global>> {
    %0 = "nn.reduce_min"(%arg0) {axes = [#builtin.int<1>], keepdim = #builtin.int<1>, space = #nn.space<global>} : (!nn.memory<[M, N], [N, 1], f32, #nn.space<global>>) -> !nn.memory<[M, 1], [1, 1], f32, #nn.space<global>>
    func.return %0 : !nn.memory<[M, 1], [1, 1], f32, #nn.space<global>>
  }
}
"""

CASE_TEXT_DYNAMIC_SYMBOL_DIM = """// COMPILE_ARGS: --pass lower-nn
// CASE: 正例：reduce 维度为符号时 nn.reduce_min 仍应 lower 为 dma.alloc + kernel.reduce(kind=min) + func.return。
// CHECK: builtin.module {
// CHECK-NEXT: func.func @reduce_min_symbol_dim_kernel(%arg0 : !nn.memory<[M, N], [N, 1], f32, #nn.space<global>>) -> !nn.memory<[1, N], [N, 1], f32, #nn.space<global>> {
// CHECK-NEXT: %0 = "symbol.get_dim"(%arg0) {axis = #builtin.int<1>} : (!nn.memory<[M, N], [N, 1], f32, #nn.space<global>>) -> !symbol.int<"N">
// CHECK-NEXT: %1 = "dma.alloc"(%0) <{operandSegmentSizes = array<i32: 1>}> : (!symbol.int<"N">) -> !nn.memory<[1, N], [N, 1], f32, #nn.space<global>>
// CHECK-NEXT: "kernel.reduce"(%arg0, %1) {axis = 0 : i64, keepdim = true, kind = "min", space = #nn.space<global>} : (!nn.memory<[M, N], [N, 1], f32, #nn.space<global>>, !nn.memory<[1, N], [N, 1], f32, #nn.space<global>>) -> ()
// CHECK-NEXT: func.return %1 : !nn.memory<[1, N], [N, 1], f32, #nn.space<global>>
// CHECK-NEXT: }
// CHECK-NEXT: }
// CHECK-NOT: nn.reduce_min

builtin.module {
  func.func @reduce_min_symbol_dim_kernel(%arg0: !nn.memory<[M, N], [N, 1], f32, #nn.space<global>>) -> !nn.memory<[1, N], [N, 1], f32, #nn.space<global>> {
    %0 = "nn.reduce_min"(%arg0) {axes = [#builtin.int<0>], keepdim = #builtin.int<1>, space = #nn.space<global>} : (!nn.memory<[M, N], [N, 1], f32, #nn.space<global>>) -> !nn.memory<[1, N], [N, 1], f32, #nn.space<global>>
    func.return %0 : !nn.memory<[1, N], [N, 1], f32, #nn.space<global>>
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
    - _assert_ircheck_ok(CASE_TEXT_STATIC, "reduce_min.py:static")

    关联文件:
    - spec: spec/pass/lowering/nn_lowering/reduce_softmax_lowering.md
    - test: test/pass/nn_lowering/reduce_min.py
    - 功能实现: kernel_gen/tools/ircheck.py
    """

    result = run_ircheck_text(case_text, source_path=source_path)
    assert result.ok is True, (
        f"expected ok=True, got ok={result.ok}, exit_code={result.exit_code}, message={result.message!r}"
    )
    assert result.exit_code == 0, f"expected exit_code=0, got {result.exit_code}"
    assert "kernel.reduce" in result.actual_ir, "actual_ir must contain kernel.reduce"
    assert "nn.reduce_min" not in result.actual_ir, "actual_ir must not contain residual nn.reduce_min"


# TC-PASS-NNL-011
# 创建者: 金铲铲大作战
# 最后一次更改: 金铲铲大作战
# 最近一次运行测试时间: 2026-04-12 08:20:00 +0800
# 最近一次运行成功时间: 2026-04-12 08:20:00 +0800
# 测试目的: 验证 nn.reduce_min lowering 目标为 kernel.reduce(kind=min)（静态形态）。
# 使用示例: pytest -q test/pass/nn_lowering/reduce_min.py -k test_nn_lowering_reduce_min_static
# 对应功能实现文件路径: kernel_gen/passes/lowering/nn_lowering/reduce_softmax_lowering.py
# 对应 spec 文件路径: spec/pass/lowering/nn_lowering/reduce_softmax_lowering.md
# 对应测试文件路径: test/pass/nn_lowering/reduce_min.py
def test_nn_lowering_reduce_min_static() -> None:
    _assert_ircheck_ok(CASE_TEXT_STATIC, "test/pass/nn_lowering/reduce_min.py:static")


# TC-PASS-NNL-011
# 创建者: 金铲铲大作战
# 最后一次更改: 金铲铲大作战
# 最近一次运行测试时间: 2026-04-12 08:20:00 +0800
# 最近一次运行成功时间: 2026-04-12 08:20:00 +0800
# 测试目的: 验证 nn.reduce_min lowering 目标为 kernel.reduce(kind=min)（符号维度）。
# 使用示例: pytest -q test/pass/nn_lowering/reduce_min.py -k test_nn_lowering_reduce_min_dynamic
# 对应功能实现文件路径: kernel_gen/passes/lowering/nn_lowering/reduce_softmax_lowering.py
# 对应 spec 文件路径: spec/pass/lowering/nn_lowering/reduce_softmax_lowering.md
# 对应测试文件路径: test/pass/nn_lowering/reduce_min.py
def test_nn_lowering_reduce_min_dynamic() -> None:
    _assert_ircheck_ok(CASE_TEXT_DYNAMIC, "test/pass/nn_lowering/reduce_min.py:dynamic")


# TC-PASS-NNL-011
# 创建者: 金铲铲大作战
# 最后一次更改: 金铲铲大作战
# 最近一次运行测试时间: 2026-04-12 08:20:00 +0800
# 最近一次运行成功时间: 2026-04-12 08:20:00 +0800
# 测试目的: 验证 reduce 维度为符号时仍能 lower 为 kernel.reduce(kind=min)。
# 使用示例: pytest -q test/pass/nn_lowering/reduce_min.py -k test_nn_lowering_reduce_min_symbol_dim
# 对应功能实现文件路径: kernel_gen/passes/lowering/nn_lowering/reduce_softmax_lowering.py
# 对应 spec 文件路径: spec/pass/lowering/nn_lowering/reduce_softmax_lowering.md
# 对应测试文件路径: test/pass/nn_lowering/reduce_min.py
def test_nn_lowering_reduce_min_symbol_dim() -> None:
    _assert_ircheck_ok(CASE_TEXT_DYNAMIC_SYMBOL_DIM, "test/pass/nn_lowering/reduce_min.py:symbol_dim")
