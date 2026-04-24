"""pass nn_lowering element_compare expectation。
[immutable-file]


创建者: 大闸蟹
最后一次更改: 大闸蟹

功能说明:
- 使用内联 `CASE_TEXT` 构造 `ircheck` 文本，并调用 `run_ircheck_text(...)`
  验证 compare 类算子从 `nn.*` 到 `kernel.binary_elewise(kind=...)` 的改写结果。
- 覆盖 `eq/ne/lt/le/gt/ge` 六个子用例，并同时覆盖静态与符号维度形态。
- 所有 case 都直接使用 `ircheck` 原生 `CHECK` / `CHECK-NEXT` / `CHECK-NOT`
  语法，按需使用 `ircheck` 变量捕获/复用，避免依赖固定 SSA 名。

使用示例:
- `PYTHONPATH=. python expectation/pass/lowing/nn_lowering/element_compare.py`

关联文件:
- spec: [`spec/pass/lowering/nn_lowering.md`](spec/pass/lowering/nn_lowering.md)
- spec: [`spec/tools/ircheck.md`](spec/tools/ircheck.md)
- test: [`test/pass/test_lowering_nn_to_kernel.py`](test/pass/test_lowering_nn_to_kernel.py)
- 功能实现: [`kernel_gen/tools/ircheck.py`](kernel_gen/tools/ircheck.py)
- 功能实现: [`kernel_gen/passes/lowering/nn_lowering/nn_lowering.py`](kernel_gen/passes/lowering/nn_lowering/nn_lowering.py)
"""

# Case 列表:
# - Case-eq: 正例：静态/符号维度 nn.eq 输入应 lower 为 dma.alloc + kernel.binary_elewise(kind=eq) + func.return。
# - Case-ne: 正例：静态/符号维度 nn.ne 输入应 lower 为 dma.alloc + kernel.binary_elewise(kind=ne) + func.return。
# - Case-lt: 正例：静态/符号维度 nn.lt 输入应 lower 为 dma.alloc + kernel.binary_elewise(kind=lt) + func.return。
# - Case-le: 正例：静态/符号维度 nn.le 输入应 lower 为 dma.alloc + kernel.binary_elewise(kind=le) + func.return。
# - Case-gt: 正例：静态/符号维度 nn.gt 输入应 lower 为 dma.alloc + kernel.binary_elewise(kind=gt) + func.return。
# - Case-ge: 正例：静态/符号维度 nn.ge 输入应 lower 为 dma.alloc + kernel.binary_elewise(kind=ge) + func.return。

from __future__ import annotations

from importlib import import_module
from pathlib import Path
import sys

CURRENT_DIR = Path(__file__).resolve().parent
if str(CURRENT_DIR) not in sys.path:
    sys.path.insert(0, str(CURRENT_DIR))

REPO_ROOT = next(parent for parent in Path(__file__).resolve().parents if (parent / "kernel_gen").exists())
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

print_case_actual_ir = import_module("expectation.pass.lowing._shared").print_case_actual_ir
from expectation.utils.case_runner import raise_if_failures, run_case
from _random_utils import (
    random_arithmetic_dtype_ir,
    random_space_attr_ir,
    random_static_dims,
    random_symbol_names,
)
from kernel_gen.tools.ircheck import run_ircheck_text

DATA_DTYPE_IR = random_arithmetic_dtype_ir()
SPACE_ATTR = random_space_attr_ir()


def _build_case_static(op_name: str, static_m: int, static_n: int) -> tuple[str, str]:
    """构造静态 element_compare case。"""

    desc = (
        f"正例：静态 nn.{op_name} 输入应 lower 为 dma.alloc + "
        f'kernel.binary_elewise(kind={op_name}) + func.return。'
    )
    case_text = f"""// COMPILE_ARGS: --pass lower-nn
// CASE: {desc}
// CHECK: builtin.module {{
// CHECK-NEXT: func.func @{op_name}_kernel(%[[LHS:{{reg}}]] : !nn.memory<[{static_m}, {static_n}], [{static_n}, 1], {DATA_DTYPE_IR}, {SPACE_ATTR}>, %[[RHS:{{reg}}]] : !nn.memory<[{static_m}, {static_n}], [{static_n}, 1], {DATA_DTYPE_IR}, {SPACE_ATTR}>) -> !nn.memory<[{static_m}, {static_n}], [{static_n}, 1], i1, {SPACE_ATTR}> {{
// CHECK-NEXT: %[[V0:{{reg}}]] = "dma.alloc"() <{{operandSegmentSizes = array<i32: 0>}}> : () -> !nn.memory<[{static_m}, {static_n}], [{static_n}, 1], i1, {SPACE_ATTR}>
// CHECK-NEXT: "kernel.binary_elewise"(%[[V0]], %[[LHS]], %[[RHS]]) {{kind = "{op_name}", space = {SPACE_ATTR}}} : (!nn.memory<[{static_m}, {static_n}], [{static_n}, 1], i1, {SPACE_ATTR}>, !nn.memory<[{static_m}, {static_n}], [{static_n}, 1], {DATA_DTYPE_IR}, {SPACE_ATTR}>, !nn.memory<[{static_m}, {static_n}], [{static_n}, 1], {DATA_DTYPE_IR}, {SPACE_ATTR}>) -> ()
// CHECK-NEXT: func.return %[[V0]] : !nn.memory<[{static_m}, {static_n}], [{static_n}, 1], i1, {SPACE_ATTR}>
// CHECK-NEXT: }}
// CHECK-NEXT: }}
// CHECK-NOT: nn.{op_name}

builtin.module {{
  func.func @{op_name}_kernel(%lhs: !nn.memory<[{static_m}, {static_n}], [{static_n}, 1], {DATA_DTYPE_IR}, {SPACE_ATTR}>, %rhs: !nn.memory<[{static_m}, {static_n}], [{static_n}, 1], {DATA_DTYPE_IR}, {SPACE_ATTR}>) -> !nn.memory<[{static_m}, {static_n}], [{static_n}, 1], i1, {SPACE_ATTR}> {{
    %0 = "nn.{op_name}"(%lhs, %rhs) {{space = {SPACE_ATTR}}} : (!nn.memory<[{static_m}, {static_n}], [{static_n}, 1], {DATA_DTYPE_IR}, {SPACE_ATTR}>, !nn.memory<[{static_m}, {static_n}], [{static_n}, 1], {DATA_DTYPE_IR}, {SPACE_ATTR}>) -> !nn.memory<[{static_m}, {static_n}], [{static_n}, 1], i1, {SPACE_ATTR}>
    func.return %0 : !nn.memory<[{static_m}, {static_n}], [{static_n}, 1], i1, {SPACE_ATTR}>
  }}
}}"""
    return desc, case_text


def _build_case_dynamic(op_name: str, sym_m: str, sym_n: str) -> tuple[str, str]:
    """构造符号维度 element_compare case。"""

    desc = (
        f"正例：符号维度 nn.{op_name} 输入应 lower 为 dma.alloc + "
        f'kernel.binary_elewise(kind={op_name}) + func.return。'
    )
    case_text = f"""// COMPILE_ARGS: --pass lower-nn
// CASE: {desc}
// CHECK: builtin.module {{
// CHECK-NEXT: func.func @{op_name}_kernel(%[[LHS:{{reg}}]] : !nn.memory<[{sym_m}, {sym_n}], [{sym_n}, 1], {DATA_DTYPE_IR}, {SPACE_ATTR}>, %[[RHS:{{reg}}]] : !nn.memory<[{sym_m}, {sym_n}], [{sym_n}, 1], {DATA_DTYPE_IR}, {SPACE_ATTR}>) -> !nn.memory<[{sym_m}, {sym_n}], [{sym_n}, 1], i1, {SPACE_ATTR}> {{
// CHECK-NEXT: %[[V0:{{reg}}]] = "symbol.get_dim"(%[[LHS]]) {{axis = #builtin.int<0>}} : (!nn.memory<[{sym_m}, {sym_n}], [{sym_n}, 1], {DATA_DTYPE_IR}, {SPACE_ATTR}>) -> !symbol.int<"{sym_m}">
// CHECK-NEXT: %[[V1:{{reg}}]] = "symbol.get_dim"(%[[LHS]]) {{axis = #builtin.int<1>}} : (!nn.memory<[{sym_m}, {sym_n}], [{sym_n}, 1], {DATA_DTYPE_IR}, {SPACE_ATTR}>) -> !symbol.int<"{sym_n}">
// CHECK-NEXT: %[[V2:{{reg}}]] = "dma.alloc"(%[[V0]], %[[V1]]) <{{operandSegmentSizes = array<i32: 2>}}> : (!symbol.int<"{sym_m}">, !symbol.int<"{sym_n}">) -> !nn.memory<[{sym_m}, {sym_n}], [{sym_n}, 1], i1, {SPACE_ATTR}>
// CHECK-NEXT: "kernel.binary_elewise"(%[[V2]], %[[LHS]], %[[RHS]]) {{kind = "{op_name}", space = {SPACE_ATTR}}} : (!nn.memory<[{sym_m}, {sym_n}], [{sym_n}, 1], i1, {SPACE_ATTR}>, !nn.memory<[{sym_m}, {sym_n}], [{sym_n}, 1], {DATA_DTYPE_IR}, {SPACE_ATTR}>, !nn.memory<[{sym_m}, {sym_n}], [{sym_n}, 1], {DATA_DTYPE_IR}, {SPACE_ATTR}>) -> ()
// CHECK-NEXT: func.return %[[V2]] : !nn.memory<[{sym_m}, {sym_n}], [{sym_n}, 1], i1, {SPACE_ATTR}>
// CHECK-NEXT: }}
// CHECK-NEXT: }}
// CHECK-NOT: nn.{op_name}

builtin.module {{
  func.func @{op_name}_kernel(%lhs: !nn.memory<[{sym_m}, {sym_n}], [{sym_n}, 1], {DATA_DTYPE_IR}, {SPACE_ATTR}>, %rhs: !nn.memory<[{sym_m}, {sym_n}], [{sym_n}, 1], {DATA_DTYPE_IR}, {SPACE_ATTR}>) -> !nn.memory<[{sym_m}, {sym_n}], [{sym_n}, 1], i1, {SPACE_ATTR}> {{
    %0 = "nn.{op_name}"(%lhs, %rhs) {{space = {SPACE_ATTR}}} : (!nn.memory<[{sym_m}, {sym_n}], [{sym_n}, 1], {DATA_DTYPE_IR}, {SPACE_ATTR}>, !nn.memory<[{sym_m}, {sym_n}], [{sym_n}, 1], {DATA_DTYPE_IR}, {SPACE_ATTR}>) -> !nn.memory<[{sym_m}, {sym_n}], [{sym_n}, 1], i1, {SPACE_ATTR}>
    func.return %0 : !nn.memory<[{sym_m}, {sym_n}], [{sym_n}, 1], i1, {SPACE_ATTR}>
  }}
}}"""
    return desc, case_text


def _run_case(case_text: str, *, source_path: str) -> str:
    """运行单个 `ircheck` case 并返回实际 IR。"""

    result = run_ircheck_text(case_text, source_path=source_path)
    assert result.ok is True, (
        f"expected ok=True, got ok={result.ok}, exit_code={result.exit_code}, message={result.message!r}"
    )
    assert result.exit_code == 0, f"expected exit_code=0, got {result.exit_code}"
    return result.actual_ir


def run_case_texts(op_name: str) -> None:
    """运行单个 element_compare 子用例。"""

    static_m, static_n = random_static_dims(2)
    sym_m, sym_n = random_symbol_names(2)
    cases = (
        ("static", *_build_case_static(op_name, static_m, static_n)),
        ("dynamic", *_build_case_dynamic(op_name, sym_m, sym_n)),
    )
    for variant, desc, case_text in cases:
        actual_ir = _run_case(
            case_text,
            source_path=f"expectation/pass/lowing/nn_lowering/element_compare.py:{op_name}:{variant}",
        )
        assert "kernel.binary_elewise" in actual_ir, "actual_ir must contain kernel.binary_elewise"
        assert f'kind = "{op_name}"' in actual_ir, f'actual_ir must contain kind = "{op_name}"'
        assert f"nn.{op_name}" not in actual_ir, f"actual_ir must not contain residual nn.{op_name}"
        print_case_actual_ir(
            f"CASE-{op_name}-{variant}",
            case_text,
            actual_ir,
            fallback=desc,
        )


def main(selected_ops: list[str] | None = None) -> None:
    """运行 element_compare `ir_text` expectation。"""

    selected = selected_ops or ["eq", "ne", "lt", "le", "gt", "ge"]
    failures: list[tuple[str, BaseException]] = []
    for op_name in selected:
        run_case(failures, f"CASE-{op_name}", lambda op=op_name: run_case_texts(op))
    raise_if_failures("nn_lowering element_compare expectation", failures)


if __name__ == "__main__":
    main()
