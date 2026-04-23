"""nn_lowering reduce family tests.

创建者: jcc你莫辜负
最后一次更改: jcc你莫辜负

功能说明:
- 将 `nn.reduce_sum`、`nn.reduce_min`、`nn.reduce_max` 的直接 IR case 收口为参数化 pytest。
- 使用 `kernel_gen.tools.ircheck` 承接文本合同，保留静态形态、符号维度和 shape mismatch 的 direct pytest。

使用示例:
- pytest -q test/pass/nn_lowering/test_reduce_lowering.py

关联文件:
- 功能实现: [kernel_gen/passes/lowering/nn_lowering/nn_lowering.py](kernel_gen/passes/lowering/nn_lowering/nn_lowering.py)
- Spec 文档: [spec/pass/lowering/nn_lowering.md](spec/pass/lowering/nn_lowering.md)
- 测试文件: [test/pass/nn_lowering/test_reduce_lowering.py](test/pass/nn_lowering/test_reduce_lowering.py)
"""

from __future__ import annotations

import sys
from collections.abc import Sequence
from pathlib import Path

import pytest
from xdsl.dialects import func
from xdsl.dialects.builtin import ArrayAttr, FunctionType, IntAttr, ModuleOp, StringAttr, f32
from xdsl.ir import Block, Region

REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from kernel_gen.dialect.nn import (
    NnMemorySpaceAttr,
    NnMemoryType,
    NnReduceMaxOp,
    NnReduceMinOp,
    NnReduceSumOp,
)
from kernel_gen.passes.lowering.nn_lowering import NnLoweringError, NnLoweringPass
from kernel_gen.tools.ircheck import run_ircheck_text

GLOBAL_SPACE = "#nn.space<global>"
STATIC_INPUT_TYPE = f"!nn.memory<[4, 8], [8, 1], f32, {GLOBAL_SPACE}>"
STATIC_RESULT_TYPE = f"!nn.memory<[4, 1], [1, 1], f32, {GLOBAL_SPACE}>"
DYNAMIC_INPUT_TYPE = f"!nn.memory<[M, N], [N, 1], f32, {GLOBAL_SPACE}>"
DYNAMIC_RESULT_TYPE = f"!nn.memory<[M, 1], [1, 1], f32, {GLOBAL_SPACE}>"
SYMBOL_DIM_RESULT_TYPE = f"!nn.memory<[1, N], [N, 1], f32, {GLOBAL_SPACE}>"


def _make_ircheck_case_text(
    *,
    case_desc: str,
    func_name: str,
    input_type: str,
    result_type: str,
    op_name: str,
    check_body_lines: Sequence[str],
    body_lines: Sequence[str],
) -> str:
    """拼装 reduce family 的 ircheck 文本。

    创建者: jcc你莫辜负
    最后一次更改: jcc你莫辜负

    功能说明:
    - 统一生成 `CHECK` / 输入 IR 双部分文本，避免三个 reduce 文件各写一套重复样板。

    使用示例:
    - text = _make_ircheck_case_text(case_desc="...", func_name="reduce_sum_kernel", ...)

    关联文件:
    - spec: [spec/pass/lowering/nn_lowering.md](spec/pass/lowering/nn_lowering.md)
    - test: [test/pass/nn_lowering/test_reduce_lowering.py](test/pass/nn_lowering/test_reduce_lowering.py)
    - 功能实现: [kernel_gen/tools/ircheck.py](kernel_gen/tools/ircheck.py)
    """

    lines = [
        "// COMPILE_ARGS: --pass lower-nn",
        f"// CASE: {case_desc}",
        "// CHECK: builtin.module {",
        f"// CHECK-NEXT: func.func @{func_name}(%arg0 : {input_type}) -> {result_type} {{",
    ]
    lines.extend(f"// CHECK-NEXT: {line}" for line in check_body_lines)
    lines.extend(
        [
            "// CHECK-NEXT: }",
            "// CHECK-NEXT: }",
            f"// CHECK-NOT: {op_name}",
            "",
            "builtin.module {",
            f"  func.func @{func_name}(%arg0: {input_type}) -> {result_type} {{",
        ]
    )
    lines.extend(f"    {line}" for line in body_lines)
    lines.extend(["  }", "}"])
    return "\n".join(lines)


CASE_TEXT_SUM_STATIC = _make_ircheck_case_text(
    case_desc="正例：静态 nn.reduce_sum 输入应 lower 为 dma.alloc + kernel.reduce(kind=sum) + func.return。",
    func_name="reduce_sum_kernel",
    input_type=STATIC_INPUT_TYPE,
    result_type=STATIC_RESULT_TYPE,
    op_name="nn.reduce_sum",
    check_body_lines=(
        f'%0 = "dma.alloc"() <{{operandSegmentSizes = array<i32: 0>}}> : () -> {STATIC_RESULT_TYPE}',
        f'"kernel.reduce"(%0, %arg0) {{axis = 1 : i64, keepdim = true, kind = "sum", space = {GLOBAL_SPACE}}} : ({STATIC_RESULT_TYPE}, {STATIC_INPUT_TYPE}) -> ()',
        f'func.return %0 : {STATIC_RESULT_TYPE}',
    ),
    body_lines=(
        f'%0 = "nn.reduce_sum"(%arg0) {{axes = [#builtin.int<1>], keepdim = #builtin.int<1>, space = {GLOBAL_SPACE}}} : ({STATIC_INPUT_TYPE}) -> {STATIC_RESULT_TYPE}',
        f'func.return %0 : {STATIC_RESULT_TYPE}',
    ),
)

CASE_TEXT_SUM_DYNAMIC = _make_ircheck_case_text(
    case_desc="正例：符号维度 nn.reduce_sum 输入应 lower 为 dma.alloc + kernel.reduce(kind=sum) + func.return。",
    func_name="reduce_sum_kernel",
    input_type=DYNAMIC_INPUT_TYPE,
    result_type=DYNAMIC_RESULT_TYPE,
    op_name="nn.reduce_sum",
    check_body_lines=(
        f'%0 = "symbol.get_dim"(%arg0) {{axis = #builtin.int<0>}} : ({DYNAMIC_INPUT_TYPE}) -> !symbol.int<"M">',
        f'%1 = "dma.alloc"(%0) <{{operandSegmentSizes = array<i32: 1>}}> : (!symbol.int<"M">) -> {DYNAMIC_RESULT_TYPE}',
        f'"kernel.reduce"(%1, %arg0) {{axis = 1 : i64, keepdim = true, kind = "sum", space = {GLOBAL_SPACE}}} : ({DYNAMIC_RESULT_TYPE}, {DYNAMIC_INPUT_TYPE}) -> ()',
        f'func.return %1 : {DYNAMIC_RESULT_TYPE}',
    ),
    body_lines=(
        f'%0 = "nn.reduce_sum"(%arg0) {{axes = [#builtin.int<1>], keepdim = #builtin.int<1>, space = {GLOBAL_SPACE}}} : ({DYNAMIC_INPUT_TYPE}) -> {DYNAMIC_RESULT_TYPE}',
        f'func.return %0 : {DYNAMIC_RESULT_TYPE}',
    ),
)

CASE_TEXT_MIN_STATIC = _make_ircheck_case_text(
    case_desc="正例：静态 nn.reduce_min 输入应 lower 为 dma.alloc + kernel.reduce(kind=min) + func.return。",
    func_name="reduce_min_kernel",
    input_type=STATIC_INPUT_TYPE,
    result_type=STATIC_RESULT_TYPE,
    op_name="nn.reduce_min",
    check_body_lines=(
        f'%0 = "dma.alloc"() <{{operandSegmentSizes = array<i32: 0>}}> : () -> {STATIC_RESULT_TYPE}',
        f'"kernel.reduce"(%0, %arg0) {{axis = 1 : i64, keepdim = true, kind = "min", space = {GLOBAL_SPACE}}} : ({STATIC_RESULT_TYPE}, {STATIC_INPUT_TYPE}) -> ()',
        f'func.return %0 : {STATIC_RESULT_TYPE}',
    ),
    body_lines=(
        f'%0 = "nn.reduce_min"(%arg0) {{axes = [#builtin.int<1>], keepdim = #builtin.int<1>, space = {GLOBAL_SPACE}}} : ({STATIC_INPUT_TYPE}) -> {STATIC_RESULT_TYPE}',
        f'func.return %0 : {STATIC_RESULT_TYPE}',
    ),
)

CASE_TEXT_MIN_DYNAMIC = _make_ircheck_case_text(
    case_desc="正例：符号维度 nn.reduce_min 输入应 lower 为 dma.alloc + kernel.reduce(kind=min) + func.return。",
    func_name="reduce_min_kernel",
    input_type=DYNAMIC_INPUT_TYPE,
    result_type=DYNAMIC_RESULT_TYPE,
    op_name="nn.reduce_min",
    check_body_lines=(
        f'%0 = "symbol.get_dim"(%arg0) {{axis = #builtin.int<0>}} : ({DYNAMIC_INPUT_TYPE}) -> !symbol.int<"M">',
        f'%1 = "dma.alloc"(%0) <{{operandSegmentSizes = array<i32: 1>}}> : (!symbol.int<"M">) -> {DYNAMIC_RESULT_TYPE}',
        f'"kernel.reduce"(%1, %arg0) {{axis = 1 : i64, keepdim = true, kind = "min", space = {GLOBAL_SPACE}}} : ({DYNAMIC_RESULT_TYPE}, {DYNAMIC_INPUT_TYPE}) -> ()',
        f'func.return %1 : {DYNAMIC_RESULT_TYPE}',
    ),
    body_lines=(
        f'%0 = "nn.reduce_min"(%arg0) {{axes = [#builtin.int<1>], keepdim = #builtin.int<1>, space = {GLOBAL_SPACE}}} : ({DYNAMIC_INPUT_TYPE}) -> {DYNAMIC_RESULT_TYPE}',
        f'func.return %0 : {DYNAMIC_RESULT_TYPE}',
    ),
)

CASE_TEXT_MIN_SYMBOL_DIM = _make_ircheck_case_text(
    case_desc="正例：reduce 维度为符号时 nn.reduce_min 仍应 lower 为 dma.alloc + kernel.reduce(kind=min) + func.return。",
    func_name="reduce_min_symbol_dim_kernel",
    input_type=DYNAMIC_INPUT_TYPE,
    result_type=SYMBOL_DIM_RESULT_TYPE,
    op_name="nn.reduce_min",
    check_body_lines=(
        f'%0 = "symbol.get_dim"(%arg0) {{axis = #builtin.int<1>}} : ({DYNAMIC_INPUT_TYPE}) -> !symbol.int<"N">',
        f'%1 = "dma.alloc"(%0) <{{operandSegmentSizes = array<i32: 1>}}> : (!symbol.int<"N">) -> {SYMBOL_DIM_RESULT_TYPE}',
        f'"kernel.reduce"(%1, %arg0) {{axis = 0 : i64, keepdim = true, kind = "min", space = {GLOBAL_SPACE}}} : ({SYMBOL_DIM_RESULT_TYPE}, {DYNAMIC_INPUT_TYPE}) -> ()',
        f'func.return %1 : {SYMBOL_DIM_RESULT_TYPE}',
    ),
    body_lines=(
        f'%0 = "nn.reduce_min"(%arg0) {{axes = [#builtin.int<0>], keepdim = #builtin.int<1>, space = {GLOBAL_SPACE}}} : ({DYNAMIC_INPUT_TYPE}) -> {SYMBOL_DIM_RESULT_TYPE}',
        f'func.return %0 : {SYMBOL_DIM_RESULT_TYPE}',
    ),
)

CASE_TEXT_MAX_STATIC = _make_ircheck_case_text(
    case_desc="正例：静态 nn.reduce_max 输入应 lower 为 dma.alloc + kernel.reduce(kind=max) + func.return。",
    func_name="reduce_max_kernel",
    input_type=STATIC_INPUT_TYPE,
    result_type=STATIC_RESULT_TYPE,
    op_name="nn.reduce_max",
    check_body_lines=(
        f'%0 = "dma.alloc"() <{{operandSegmentSizes = array<i32: 0>}}> : () -> {STATIC_RESULT_TYPE}',
        f'"kernel.reduce"(%0, %arg0) {{axis = 1 : i64, keepdim = true, kind = "max", space = {GLOBAL_SPACE}}} : ({STATIC_RESULT_TYPE}, {STATIC_INPUT_TYPE}) -> ()',
        f'func.return %0 : {STATIC_RESULT_TYPE}',
    ),
    body_lines=(
        f'%0 = "nn.reduce_max"(%arg0) {{axes = [#builtin.int<1>], keepdim = #builtin.int<1>, space = {GLOBAL_SPACE}}} : ({STATIC_INPUT_TYPE}) -> {STATIC_RESULT_TYPE}',
        f'func.return %0 : {STATIC_RESULT_TYPE}',
    ),
)

CASE_TEXT_MAX_DYNAMIC = _make_ircheck_case_text(
    case_desc="正例：符号维度 nn.reduce_max 输入应 lower 为 dma.alloc + kernel.reduce(kind=max) + func.return。",
    func_name="reduce_max_kernel",
    input_type=DYNAMIC_INPUT_TYPE,
    result_type=DYNAMIC_RESULT_TYPE,
    op_name="nn.reduce_max",
    check_body_lines=(
        f'%0 = "symbol.get_dim"(%arg0) {{axis = #builtin.int<0>}} : ({DYNAMIC_INPUT_TYPE}) -> !symbol.int<"M">',
        f'%1 = "dma.alloc"(%0) <{{operandSegmentSizes = array<i32: 1>}}> : (!symbol.int<"M">) -> {DYNAMIC_RESULT_TYPE}',
        f'"kernel.reduce"(%1, %arg0) {{axis = 1 : i64, keepdim = true, kind = "max", space = {GLOBAL_SPACE}}} : ({DYNAMIC_RESULT_TYPE}, {DYNAMIC_INPUT_TYPE}) -> ()',
        f'func.return %1 : {DYNAMIC_RESULT_TYPE}',
    ),
    body_lines=(
        f'%0 = "nn.reduce_max"(%arg0) {{axes = [#builtin.int<1>], keepdim = #builtin.int<1>, space = {GLOBAL_SPACE}}} : ({DYNAMIC_INPUT_TYPE}) -> {DYNAMIC_RESULT_TYPE}',
        f'func.return %0 : {DYNAMIC_RESULT_TYPE}',
    ),
)


def _assert_ircheck_ok(case_text: str, source_path: str, residual_op_name: str) -> None:
    """运行 ircheck 文本并断言通过。

    创建者: jcc你莫辜负
    最后一次更改: jcc你莫辜负

    功能说明:
    - 调用 `run_ircheck_text` 校验 reduce family 的 `CHECK` 合同。
    - 机械断言 `kernel.reduce` 出现且残留的 nn op 名称已清除。

    使用示例:
    - _assert_ircheck_ok(CASE_TEXT_SUM_STATIC, "test/pass/nn_lowering/test_reduce_lowering.py:sum_static", "nn.reduce_sum")

    关联文件:
    - spec: [spec/pass/lowering/nn_lowering.md](spec/pass/lowering/nn_lowering.md)
    - test: [test/pass/nn_lowering/test_reduce_lowering.py](test/pass/nn_lowering/test_reduce_lowering.py)
    - 功能实现: [kernel_gen/tools/ircheck.py](kernel_gen/tools/ircheck.py)
    """

    result = run_ircheck_text(case_text, source_path=source_path)
    assert result.ok is True, (
        f"expected ok=True, got ok={result.ok}, exit_code={result.exit_code}, message={result.message!r}"
    )
    assert result.exit_code == 0, f"expected exit_code=0, got {result.exit_code}"
    assert "kernel.reduce" in result.actual_ir, "actual_ir must contain kernel.reduce"
    assert residual_op_name not in result.actual_ir, f"actual_ir must not contain residual {residual_op_name}"


def _make_memory_type(
    shape: list[int | str],
    *,
    element_type: object = f32,
    space: str = "global",
) -> NnMemoryType:
    """构造 nn.memory 类型。

    创建者: jcc你莫辜负
    最后一次更改: jcc你莫辜负

    功能说明:
    - 用于 shape mismatch 负例快速构造 `nn.memory` 类型。
    - 自动从 shape 推导 row-major stride，避免把测试重点放在样板构造上。

    使用示例:
    - mem_type = _make_memory_type([4, 8])

    关联文件:
    - spec: [spec/pass/lowering/nn_lowering.md](spec/pass/lowering/nn_lowering.md)
    - test: [test/pass/nn_lowering/test_reduce_lowering.py](test/pass/nn_lowering/test_reduce_lowering.py)
    - 功能实现: [kernel_gen/dialect/nn.py](kernel_gen/dialect/nn.py)
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


def _build_reduce_module(
    op_cls: type[object],
    func_name: str,
    input_type: NnMemoryType,
    result_type: NnMemoryType,
) -> ModuleOp:
    """构造包含单个 reduce op 的 module。

    创建者: jcc你莫辜负
    最后一次更改: jcc你莫辜负

    功能说明:
    - 用于 reduce family 的 shape mismatch 负例，统一构造 `func.func` + `reduce op` + `func.return`。

    使用示例:
    - module = _build_reduce_module(NnReduceSumOp, "reduce_sum_bad_shape", input_type, result_type)

    关联文件:
    - spec: [spec/pass/lowering/nn_lowering.md](spec/pass/lowering/nn_lowering.md)
    - test: [test/pass/nn_lowering/test_reduce_lowering.py](test/pass/nn_lowering/test_reduce_lowering.py)
    - 功能实现: [kernel_gen/dialect/nn.py](kernel_gen/dialect/nn.py)
    """

    block = Block(arg_types=[input_type])
    space = NnMemorySpaceAttr.from_name("global")
    reduce_op = op_cls(block.args[0], result_type, axes=[1], keepdim=True, space=space)
    block.add_ops([reduce_op, func.ReturnOp()])
    func_type = FunctionType.from_lists([input_type], [result_type])
    func_op = func.FuncOp(func_name, func_type, Region(block))
    return ModuleOp([func_op])


REDUCE_CASES = [
    pytest.param(
        CASE_TEXT_SUM_STATIC,
        "test/pass/nn_lowering/test_reduce_lowering.py:sum_static",
        "nn.reduce_sum",
        id="sum-static",
    ),
    pytest.param(
        CASE_TEXT_SUM_DYNAMIC,
        "test/pass/nn_lowering/test_reduce_lowering.py:sum_dynamic",
        "nn.reduce_sum",
        id="sum-dynamic",
    ),
    pytest.param(
        CASE_TEXT_MIN_STATIC,
        "test/pass/nn_lowering/test_reduce_lowering.py:min_static",
        "nn.reduce_min",
        id="min-static",
    ),
    pytest.param(
        CASE_TEXT_MIN_DYNAMIC,
        "test/pass/nn_lowering/test_reduce_lowering.py:min_dynamic",
        "nn.reduce_min",
        id="min-dynamic",
    ),
    pytest.param(
        CASE_TEXT_MIN_SYMBOL_DIM,
        "test/pass/nn_lowering/test_reduce_lowering.py:min_symbol_dim",
        "nn.reduce_min",
        id="min-symbol-dim",
    ),
    pytest.param(
        CASE_TEXT_MAX_STATIC,
        "test/pass/nn_lowering/test_reduce_lowering.py:max_static",
        "nn.reduce_max",
        id="max-static",
    ),
    pytest.param(
        CASE_TEXT_MAX_DYNAMIC,
        "test/pass/nn_lowering/test_reduce_lowering.py:max_dynamic",
        "nn.reduce_max",
        id="max-dynamic",
    ),
]


# TC-PASS-NNL-030
# 创建者: jcc你莫辜负
# 最后一次更改: jcc你莫辜负
# 最近一次运行测试时间: 未运行
# 最近一次运行成功时间: 未运行
# 功能说明: 验证 reduce family 的 IR 文本合同在静态、动态和符号维度形态下都能通过 ircheck。
# 测试目的: 将 reduce_sum / reduce_min / reduce_max 的同构 case 收口为一个参数化 pytest。
# 使用示例: pytest -q test/pass/nn_lowering/test_reduce_lowering.py -k test_nn_lowering_reduce_ircheck
# 对应功能实现文件路径: kernel_gen/passes/lowering/nn_lowering/nn_lowering.py
# 对应 spec 文件路径: spec/pass/lowering/nn_lowering.md
# 对应测试文件路径: test/pass/nn_lowering/test_reduce_lowering.py
@pytest.mark.nn_lowering
@pytest.mark.parametrize("case_text, source_path, residual_op_name", REDUCE_CASES)
def test_nn_lowering_reduce_ircheck(case_text: str, source_path: str, residual_op_name: str) -> None:
    """统一验证 reduce family 的 ircheck 文本合同。

    创建者: jcc你莫辜负
    最后一次更改: jcc你莫辜负

    功能说明:
    - 用参数化方式覆盖 reduce_sum / reduce_min / reduce_max 的静态与动态 IR case。
    - 保留 symbol 维度的边界 case，避免把独立形态拆成多个相近测试文件。

    使用示例:
    - pytest -q test/pass/nn_lowering/test_reduce_lowering.py -k test_nn_lowering_reduce_ircheck

    关联文件:
    - spec: [spec/pass/lowering/nn_lowering.md](spec/pass/lowering/nn_lowering.md)
    - test: [test/pass/nn_lowering/test_reduce_lowering.py](test/pass/nn_lowering/test_reduce_lowering.py)
    - 功能实现: [kernel_gen/tools/ircheck.py](kernel_gen/tools/ircheck.py)
    """

    _assert_ircheck_ok(case_text, source_path, residual_op_name)


REDUCE_MISMATCH_CASES = [
    pytest.param(NnReduceSumOp, "sum", id="sum"),
    pytest.param(NnReduceMinOp, "min", id="min"),
    pytest.param(NnReduceMaxOp, "max", id="max"),
]


# TC-PASS-NNL-031
# 创建者: jcc你莫辜负
# 最后一次更改: jcc你莫辜负
# 最近一次运行测试时间: 未运行
# 最近一次运行成功时间: 未运行
# 功能说明: 验证 reduce family 输出形态不一致时必须抛 NnLoweringError。
# 测试目的: 统一覆盖 sum/min/max 的 shape mismatch 负例，避免三份重复测试文件。
# 使用示例: pytest -q test/pass/nn_lowering/test_reduce_lowering.py -k test_nn_lowering_reduce_shape_mismatch
# 对应功能实现文件路径: kernel_gen/passes/lowering/nn_lowering/nn_lowering.py
# 对应 spec 文件路径: spec/pass/lowering/nn_lowering.md
# 对应测试文件路径: test/pass/nn_lowering/test_reduce_lowering.py
@pytest.mark.nn_lowering
@pytest.mark.parametrize("op_cls, kind", REDUCE_MISMATCH_CASES)
def test_nn_lowering_reduce_shape_mismatch(op_cls: type[object], kind: str) -> None:
    """验证 reduce family 的 shape mismatch 拒绝路径。

    创建者: jcc你莫辜负
    最后一次更改: jcc你莫辜负

    功能说明:
    - 构造输入输出形状不一致的 reduce module，并断言 `NnLoweringError` 直接抛出。
    - 将 sum/min/max 的同类负例收拢到一个参数化测试中，避免重复维护三份几乎一样的用例。

    使用示例:
    - pytest -q test/pass/nn_lowering/test_reduce_lowering.py -k test_nn_lowering_reduce_shape_mismatch

    关联文件:
    - spec: [spec/pass/lowering/nn_lowering.md](spec/pass/lowering/nn_lowering.md)
    - test: [test/pass/nn_lowering/test_reduce_lowering.py](test/pass/nn_lowering/test_reduce_lowering.py)
    - 功能实现: [kernel_gen/passes/lowering/nn_lowering/nn_lowering.py](kernel_gen/passes/lowering/nn_lowering/nn_lowering.py)
    """

    input_type = _make_memory_type([4, 8])
    result_type = _make_memory_type([4, 2])
    module = _build_reduce_module(op_cls, f"reduce_{kind}_bad_shape", input_type, result_type)
    with pytest.raises(NnLoweringError):
        NnLoweringPass().run(module)
