"""`NnLoweringPass` 的 `ir_text` 版 `transpose` expectation。
[immutable-file]


创建者: 大闸蟹
最后一次更改: 大闸蟹

功能说明:
- 使用内联 `CASE_TEXT` 构造 `ircheck` 文本，并调用 `run_ircheck_text(...)`
  验证 `nn.transpose` 在 `lower-nn` 中被改写为 `dma.alloc + dma.transpose + func.return`。
- 静态 case 使用随机正维度；动态 case 使用随机符号名输入，但校验只使用
  `ircheck` 的字面量 `CHECK` / `CHECK-NEXT` 语法，按需使用 `ircheck` 变量捕获/复用，避免依赖固定 SSA 名。

使用示例:
- `PYTHONPATH=. python expectation/pass/lowing/nn_lowering/transpose.py`

关联文件:
- spec: [`spec/pass/lowering/nn_lowering.md`](spec/pass/lowering/nn_lowering.md)
- spec: [`spec/tools/ircheck.md`](spec/tools/ircheck.md)
- test: [`test/pass/test_lowering_nn_to_kernel.py`](test/pass/test_lowering_nn_to_kernel.py)
- 功能实现: [`kernel_gen/tools/ircheck.py`](kernel_gen/tools/ircheck.py)
- 功能实现: [`kernel_gen/passes/lowering/nn_lowering/nn_lowering.py`](kernel_gen/passes/lowering/nn_lowering/nn_lowering.py)
"""

# Case 列表:
# - Case-1: 正例：静态 nn.transpose 输入应 lower 为 dma.alloc + dma.transpose + func.return。
# - Case-2: 正例：符号维度 nn.transpose 输入应 lower 为 dma.alloc + dma.transpose + func.return。

from __future__ import annotations

from pathlib import Path
import sys

CURRENT_DIR = Path(__file__).resolve().parent
if str(CURRENT_DIR) not in sys.path:
    sys.path.insert(0, str(CURRENT_DIR))

REPO_ROOT = Path(__file__).resolve().parents[4]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from importlib import import_module

print_case_actual_ir = import_module("expectation.pass.lowing._shared").print_case_actual_ir
from expectation.utils.case_runner import raise_if_failures, run_case
from _random_utils import (
    random_arithmetic_dtype_ir,
    random_space_attr_ir,
    random_static_dims,
    random_symbol_names,
)
from kernel_gen.tools.ircheck import run_ircheck_text

STATIC_M, STATIC_N = random_static_dims(2)
SYM_M, SYM_N = random_symbol_names(2)
DTYPE_IR = random_arithmetic_dtype_ir()
SPACE_ATTR = random_space_attr_ir()
CASE_STATIC_NAME = "CASE-transpose-static"
CASE_DYNAMIC_NAME = "CASE-transpose-dynamic"


def _build_case_static() -> tuple[str, str]:
    desc = "正例：静态 nn.transpose 输入应 lower 为 dma.alloc + dma.transpose + func.return。"
    case_text = f"""// COMPILE_ARGS: --pass lower-nn
// CASE: {desc}
// CHECK: builtin.module {{
// CHECK-NEXT: func.func @transpose_kernel(%[[ARG0:{{reg}}]] : !nn.memory<[{STATIC_M}, {STATIC_N}], [{STATIC_N}, 1], {DTYPE_IR}, {SPACE_ATTR}>) -> !nn.memory<[{STATIC_N}, {STATIC_M}], [1, {STATIC_N}], {DTYPE_IR}, {SPACE_ATTR}> {{
// CHECK-NEXT: %[[V0:{{reg}}]] = "dma.alloc"() <{{operandSegmentSizes = array<i32: 0>}}> : () -> !nn.memory<[{STATIC_N}, {STATIC_M}], [1, {STATIC_N}], {DTYPE_IR}, {SPACE_ATTR}>
// CHECK-NEXT: "dma.transpose"(%[[V0]], %[[ARG0]]) {{perm = [1 : i64, 0 : i64]}} : (!nn.memory<[{STATIC_N}, {STATIC_M}], [1, {STATIC_N}], {DTYPE_IR}, {SPACE_ATTR}>, !nn.memory<[{STATIC_M}, {STATIC_N}], [{STATIC_N}, 1], {DTYPE_IR}, {SPACE_ATTR}>) -> ()
// CHECK-NEXT: func.return %[[V0]] : !nn.memory<[{STATIC_N}, {STATIC_M}], [1, {STATIC_N}], {DTYPE_IR}, {SPACE_ATTR}>
// CHECK-NEXT: }}
// CHECK-NEXT: }}
// CHECK-NOT: nn.transpose

builtin.module {{
  func.func @transpose_kernel(%arg0: !nn.memory<[{STATIC_M}, {STATIC_N}], [{STATIC_N}, 1], {DTYPE_IR}, {SPACE_ATTR}>) -> !nn.memory<[{STATIC_N}, {STATIC_M}], [1, {STATIC_N}], {DTYPE_IR}, {SPACE_ATTR}> {{
    %0 = "nn.transpose"(%arg0) {{perm = [1 : i64, 0 : i64], space = {SPACE_ATTR}}} : (!nn.memory<[{STATIC_M}, {STATIC_N}], [{STATIC_N}, 1], {DTYPE_IR}, {SPACE_ATTR}>) -> !nn.memory<[{STATIC_N}, {STATIC_M}], [1, {STATIC_N}], {DTYPE_IR}, {SPACE_ATTR}>
    func.return %0 : !nn.memory<[{STATIC_N}, {STATIC_M}], [1, {STATIC_N}], {DTYPE_IR}, {SPACE_ATTR}>
  }}
}}"""
    return desc, case_text


def _build_case_dynamic() -> tuple[str, str]:
    desc = "正例：符号维度 nn.transpose 输入应 lower 为 dma.alloc + dma.transpose + func.return。"
    case_text = f"""// COMPILE_ARGS: --pass lower-nn
// CASE: {desc}
// CHECK: builtin.module {{
// CHECK-NEXT: func.func @transpose_kernel(%[[ARG0:{{reg}}]] : !nn.memory<[{SYM_M}, {SYM_N}], [{SYM_N}, 1], {DTYPE_IR}, {SPACE_ATTR}>) -> !nn.memory<[{SYM_N}, {SYM_M}], [1, {SYM_N}], {DTYPE_IR}, {SPACE_ATTR}> {{
// CHECK-NEXT: %[[V0:{{reg}}]] = "symbol.get_dim"(%[[ARG0]]) {{axis = #builtin.int<0>}} : (!nn.memory<[{SYM_M}, {SYM_N}], [{SYM_N}, 1], {DTYPE_IR}, {SPACE_ATTR}>) -> !symbol.int<"{SYM_M}">
// CHECK-NEXT: %[[V1:{{reg}}]] = "symbol.get_dim"(%[[ARG0]]) {{axis = #builtin.int<1>}} : (!nn.memory<[{SYM_M}, {SYM_N}], [{SYM_N}, 1], {DTYPE_IR}, {SPACE_ATTR}>) -> !symbol.int<"{SYM_N}">
// CHECK-NEXT: %[[V2:{{reg}}]] = "dma.alloc"(%[[V1]], %[[V0]]) <{{operandSegmentSizes = array<i32: 2>}}> : (!symbol.int<"{SYM_N}">, !symbol.int<"{SYM_M}">) -> !nn.memory<[{SYM_N}, {SYM_M}], [1, {SYM_N}], {DTYPE_IR}, {SPACE_ATTR}>
// CHECK-NEXT: "dma.transpose"(%[[V2]], %[[ARG0]]) {{perm = [1 : i64, 0 : i64]}} : (!nn.memory<[{SYM_N}, {SYM_M}], [1, {SYM_N}], {DTYPE_IR}, {SPACE_ATTR}>, !nn.memory<[{SYM_M}, {SYM_N}], [{SYM_N}, 1], {DTYPE_IR}, {SPACE_ATTR}>) -> ()
// CHECK-NEXT: func.return %[[V2]] : !nn.memory<[{SYM_N}, {SYM_M}], [1, {SYM_N}], {DTYPE_IR}, {SPACE_ATTR}>
// CHECK-NEXT: }}
// CHECK-NEXT: }}
// CHECK-NOT: nn.transpose

builtin.module {{
  func.func @transpose_kernel(%arg0: !nn.memory<[{SYM_M}, {SYM_N}], [{SYM_N}, 1], {DTYPE_IR}, {SPACE_ATTR}>) -> !nn.memory<[{SYM_N}, {SYM_M}], [1, {SYM_N}], {DTYPE_IR}, {SPACE_ATTR}> {{
    %0 = "nn.transpose"(%arg0) {{perm = [1 : i64, 0 : i64], space = {SPACE_ATTR}}} : (!nn.memory<[{SYM_M}, {SYM_N}], [{SYM_N}, 1], {DTYPE_IR}, {SPACE_ATTR}>) -> !nn.memory<[{SYM_N}, {SYM_M}], [1, {SYM_N}], {DTYPE_IR}, {SPACE_ATTR}>
    func.return %0 : !nn.memory<[{SYM_N}, {SYM_M}], [1, {SYM_N}], {DTYPE_IR}, {SPACE_ATTR}>
  }}
}}"""
    return desc, case_text


def _run_case(case_text: str, *, source_path: str) -> str:
    result = run_ircheck_text(case_text, source_path=source_path)
    assert result.ok is True, (
        f"expected ok=True, got ok={result.ok}, exit_code={result.exit_code}, message={result.message!r}"
    )
    assert result.exit_code == 0, f"expected exit_code=0, got {result.exit_code}"
    return result.actual_ir


def _case_static_true() -> None:
    case_desc, case_text = _build_case_static()
    actual_ir = _run_case(case_text, source_path="expectation/pass/lowing/nn_lowering/transpose.py:static")
    assert "dma.transpose" in actual_ir, "actual_ir must contain dma.transpose"
    assert "nn.transpose" not in actual_ir, "actual_ir must not contain residual nn.transpose"
    print_case_actual_ir(CASE_STATIC_NAME, case_text, actual_ir, fallback=case_desc)


def _case_dynamic_true() -> None:
    case_desc, case_text = _build_case_dynamic()
    actual_ir = _run_case(case_text, source_path="expectation/pass/lowing/nn_lowering/transpose.py:dynamic")
    assert "dma.transpose" in actual_ir, "actual_ir must contain dma.transpose"
    assert "nn.transpose" not in actual_ir, "actual_ir must not contain residual nn.transpose"
    print_case_actual_ir(CASE_DYNAMIC_NAME, case_text, actual_ir, fallback=case_desc)


def main() -> None:
    failures: list[tuple[str, BaseException]] = []
    run_case(failures, CASE_STATIC_NAME, _case_static_true)
    run_case(failures, CASE_DYNAMIC_NAME, _case_dynamic_true)
    raise_if_failures("nn_lowering transpose expectation", failures)


if __name__ == "__main__":
    main()
