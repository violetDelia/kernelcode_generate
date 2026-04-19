"""nn_lowering reduce_sum tests.

创建者: 金铲铲大作战
最后一次更改: 朽木露琪亚

功能说明:
- 使用 ircheck 文本验证 `nn.reduce_sum` lowering 目标为 `kernel.reduce(kind=sum)`。
- 补充输出形态不一致时的错误断言。

使用示例:
- pytest -q test/pass/nn_lowering/reduce_sum.py

关联文件:
- spec: spec/pass/lowering/nn_lowering.md
- test: test/pass/nn_lowering/reduce_sum.py
- 功能实现: kernel_gen/passes/lowering/nn_lowering/nn_lowering.py
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest
from xdsl.dialects import func
from xdsl.dialects.builtin import ArrayAttr, FunctionType, IntAttr, ModuleOp, StringAttr, f32
from xdsl.ir import Block, Region

from kernel_gen.dialect.nn import NnMemorySpaceAttr, NnMemoryType, NnReduceSumOp
from kernel_gen.passes.lowering import NnLoweringError, NnLoweringPass
from kernel_gen.tools.ircheck import run_ircheck_text

REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))


CASE_TEXT_STATIC = """// COMPILE_ARGS: --pass lower-nn
// CASE: 正例：静态 nn.reduce_sum 输入应 lower 为 dma.alloc + kernel.reduce(kind=sum) + func.return。
// CHECK: builtin.module {
// CHECK-NEXT: func.func @reduce_sum_kernel(%arg0 : !nn.memory<[4, 8], [8, 1], f32, #nn.space<global>>) -> !nn.memory<[4, 1], [1, 1], f32, #nn.space<global>> {
// CHECK-NEXT: %0 = "dma.alloc"() <{operandSegmentSizes = array<i32: 0>}> : () -> !nn.memory<[4, 1], [1, 1], f32, #nn.space<global>>
// CHECK-NEXT: "kernel.reduce"(%0, %arg0) {axis = 1 : i64, keepdim = true, kind = "sum", space = #nn.space<global>} : (!nn.memory<[4, 1], [1, 1], f32, #nn.space<global>>, !nn.memory<[4, 8], [8, 1], f32, #nn.space<global>>) -> ()
// CHECK-NEXT: func.return %0 : !nn.memory<[4, 1], [1, 1], f32, #nn.space<global>>
// CHECK-NEXT: }
// CHECK-NEXT: }
// CHECK-NOT: nn.reduce_sum

builtin.module {
  func.func @reduce_sum_kernel(%arg0: !nn.memory<[4, 8], [8, 1], f32, #nn.space<global>>) -> !nn.memory<[4, 1], [1, 1], f32, #nn.space<global>> {
    %0 = "nn.reduce_sum"(%arg0) {axes = [#builtin.int<1>], keepdim = #builtin.int<1>, space = #nn.space<global>} : (!nn.memory<[4, 8], [8, 1], f32, #nn.space<global>>) -> !nn.memory<[4, 1], [1, 1], f32, #nn.space<global>>
    func.return %0 : !nn.memory<[4, 1], [1, 1], f32, #nn.space<global>>
  }
}
"""

CASE_TEXT_DYNAMIC = """// COMPILE_ARGS: --pass lower-nn
// CASE: 正例：符号维度 nn.reduce_sum 输入应 lower 为 dma.alloc + kernel.reduce(kind=sum) + func.return。
// CHECK: builtin.module {
// CHECK-NEXT: func.func @reduce_sum_kernel(%arg0 : !nn.memory<[M, N], [N, 1], f32, #nn.space<global>>) -> !nn.memory<[M, 1], [1, 1], f32, #nn.space<global>> {
// CHECK-NEXT: %0 = "symbol.get_dim"(%arg0) {axis = #builtin.int<0>} : (!nn.memory<[M, N], [N, 1], f32, #nn.space<global>>) -> !symbol.int<"M">
// CHECK-NEXT: %1 = "dma.alloc"(%0) <{operandSegmentSizes = array<i32: 1>}> : (!symbol.int<"M">) -> !nn.memory<[M, 1], [1, 1], f32, #nn.space<global>>
// CHECK-NEXT: "kernel.reduce"(%1, %arg0) {axis = 1 : i64, keepdim = true, kind = "sum", space = #nn.space<global>} : (!nn.memory<[M, 1], [1, 1], f32, #nn.space<global>>, !nn.memory<[M, N], [N, 1], f32, #nn.space<global>>) -> ()
// CHECK-NEXT: func.return %1 : !nn.memory<[M, 1], [1, 1], f32, #nn.space<global>>
// CHECK-NEXT: }
// CHECK-NEXT: }
// CHECK-NOT: nn.reduce_sum

builtin.module {
  func.func @reduce_sum_kernel(%arg0: !nn.memory<[M, N], [N, 1], f32, #nn.space<global>>) -> !nn.memory<[M, 1], [1, 1], f32, #nn.space<global>> {
    %0 = "nn.reduce_sum"(%arg0) {axes = [#builtin.int<1>], keepdim = #builtin.int<1>, space = #nn.space<global>} : (!nn.memory<[M, N], [N, 1], f32, #nn.space<global>>) -> !nn.memory<[M, 1], [1, 1], f32, #nn.space<global>>
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
    - _assert_ircheck_ok(CASE_TEXT_STATIC, "reduce_sum.py:static")

    关联文件:
    - spec: spec/pass/lowering/nn_lowering/reduce_softmax_lowering.md
    - test: test/pass/nn_lowering/reduce_sum.py
    - 功能实现: kernel_gen/tools/ircheck.py
    """

    result = run_ircheck_text(case_text, source_path=source_path)
    assert result.ok is True, (
        f"expected ok=True, got ok={result.ok}, exit_code={result.exit_code}, message={result.message!r}"
    )
    assert result.exit_code == 0, f"expected exit_code=0, got {result.exit_code}"
    assert "kernel.reduce" in result.actual_ir, "actual_ir must contain kernel.reduce"
    assert "nn.reduce_sum" not in result.actual_ir, "actual_ir must not contain residual nn.reduce_sum"


def _make_memory_type(
    shape: list[int | str],
    *,
    element_type: object = f32,
    space: str = "global",
) -> NnMemoryType:
    """构造 nn.memory 类型。

    创建者: 金铲铲大作战
    最后一次更改: 金铲铲大作战

    功能说明:
    - 用于 reduce_sum 负例中快速构造 memory 类型。

    使用示例:
    - mem_type = _make_memory_type([4, 8])

    关联文件:
    - spec: spec/pass/lowering/nn_lowering/reduce_softmax_lowering.md
    - test: test/pass/nn_lowering/reduce_sum.py
    - 功能实现: kernel_gen/dialect/nn.py
    """

    shape_attr = ArrayAttr([IntAttr(dim) if isinstance(dim, int) else StringAttr(dim) for dim in shape])
    stride_values: list[int] = []
    running = 1
    for dim in reversed(shape):
        dim_value = dim if isinstance(dim, int) else 1
        stride_values.append(running)
        running *= dim_value
    stride_values.reverse()
    stride_attr = ArrayAttr([IntAttr(value) for value in stride_values])
    return NnMemoryType(shape_attr, stride_attr, element_type, NnMemorySpaceAttr.from_name(space))


def _build_module(input_type: NnMemoryType, result_type: NnMemoryType) -> ModuleOp:
    """构造包含单个 nn.reduce_sum 的 module。

    创建者: 金铲铲大作战
    最后一次更改: 金铲铲大作战

    功能说明:
    - 用于 reduce_sum 负例路径构造不一致的输出类型。

    使用示例:
    - module = _build_module(input_type, result_type)

    关联文件:
    - spec: spec/pass/lowering/nn_lowering/reduce_softmax_lowering.md
    - test: test/pass/nn_lowering/reduce_sum.py
    - 功能实现: kernel_gen/dialect/nn.py
    """

    block = Block(arg_types=[input_type])
    space = NnMemorySpaceAttr.from_name("global")
    block.add_ops(
        [
            NnReduceSumOp(block.args[0], result_type, axes=[1], keepdim=True, space=space),
            func.ReturnOp(),
        ]
    )
    func_op = func.FuncOp(
        "reduce_sum_kernel",
        FunctionType.from_lists([input_type], [result_type]),
        Region(block),
    )
    return ModuleOp([func_op])


# TC-PASS-NNL-011
# 创建者: 金铲铲大作战
# 最后一次更改: 朽木露琪亚
# 最近一次运行测试时间: 2026-04-12 08:20:00 +0800
# 最近一次运行成功时间: 2026-04-12 08:20:00 +0800
# 测试目的: 验证 nn.reduce_sum lowering 目标为 kernel.reduce(kind=sum)（静态形态）。
# 使用示例: pytest -q test/pass/nn_lowering/reduce_sum.py -k test_nn_lowering_reduce_sum_static
# 对应功能实现文件路径: kernel_gen/passes/lowering/nn_lowering/nn_lowering.py
# 对应 spec 文件路径: spec/pass/lowering/nn_lowering.md
# 对应测试文件路径: test/pass/nn_lowering/reduce_sum.py
def test_nn_lowering_reduce_sum_static() -> None:
    _assert_ircheck_ok(CASE_TEXT_STATIC, "test/pass/nn_lowering/reduce_sum.py:static")


# TC-PASS-NNL-011
# 创建者: 金铲铲大作战
# 最后一次更改: 朽木露琪亚
# 最近一次运行测试时间: 2026-04-12 08:20:00 +0800
# 最近一次运行成功时间: 2026-04-12 08:20:00 +0800
# 测试目的: 验证 nn.reduce_sum lowering 目标为 kernel.reduce(kind=sum)（符号维度）。
# 使用示例: pytest -q test/pass/nn_lowering/reduce_sum.py -k test_nn_lowering_reduce_sum_dynamic
# 对应功能实现文件路径: kernel_gen/passes/lowering/nn_lowering/nn_lowering.py
# 对应 spec 文件路径: spec/pass/lowering/nn_lowering.md
# 对应测试文件路径: test/pass/nn_lowering/reduce_sum.py
def test_nn_lowering_reduce_sum_dynamic() -> None:
    _assert_ircheck_ok(CASE_TEXT_DYNAMIC, "test/pass/nn_lowering/reduce_sum.py:dynamic")


# TC-PASS-NNL-012
# 创建者: 金铲铲大作战
# 最后一次更改: 朽木露琪亚
# 最近一次运行测试时间: 2026-04-12 08:20:00 +0800
# 最近一次运行成功时间: 2026-04-12 08:20:00 +0800
# 测试目的: 验证 nn.reduce_sum 输出形态不一致时必须抛 NnLoweringError。
# 使用示例: pytest -q test/pass/nn_lowering/reduce_sum.py -k test_nn_lowering_reduce_sum_shape_mismatch
# 对应功能实现文件路径: kernel_gen/passes/lowering/nn_lowering/nn_lowering.py
# 对应 spec 文件路径: spec/pass/lowering/nn_lowering.md
# 对应测试文件路径: test/pass/nn_lowering/reduce_sum.py
def test_nn_lowering_reduce_sum_shape_mismatch() -> None:
    input_type = _make_memory_type([4, 8])
    result_type = _make_memory_type([4, 2])
    module = _build_module(input_type, result_type)
    with pytest.raises(NnLoweringError):
        NnLoweringPass().run(module)
