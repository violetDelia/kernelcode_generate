"""pass nn_lowering expectation：cast。
[immutable-file]


创建者: 大闸蟹
最后一次更改: 大闸蟹

功能说明:
- 使用内联 `CASE_TEXT` 构造 `ircheck` 文本，并调用 `run_ircheck_text(...)`
  验证 `nn.cast` 在 `lower-nn` 中被改写为 `dma.alloc + dma.cast + func.return`。
- 静态 case 使用随机正维度；动态 case 使用随机符号名输入，但校验只使用
  `ircheck` 的字面量 `CHECK` / `CHECK-NEXT` 语法，按需使用 `ircheck` 变量捕获/复用，避免依赖固定 SSA 名。

使用示例:
- `PYTHONPATH=. python expectation/pass/lowing/nn_lowering/cast.py`

关联文件:
- spec: [`spec/pass/lowering/nn_lowering.md`](spec/pass/lowering/nn_lowering.md)
- spec: [`spec/dialect/dma.md`](spec/dialect/dma.md)
- spec: [`spec/tools/ircheck.md`](spec/tools/ircheck.md)
- test: [`test/pass/test_lowering_nn_to_kernel.py`](test/pass/test_lowering_nn_to_kernel.py)
- 功能实现: [`kernel_gen/tools/ircheck.py`](kernel_gen/tools/ircheck.py)
- 功能实现: [`kernel_gen/passes/lowering/nn_lowering/nn_lowering.py`](kernel_gen/passes/lowering/nn_lowering/nn_lowering.py)
"""

# Case 列表:
# - Case-cast-static: 正例：静态 nn.cast 输入应 lower 为 dma.alloc + dma.cast + func.return。
# - Case-cast-dynamic: 正例：符号维度 nn.cast 输入应 lower 为 dma.alloc + dma.cast + func.return。

from __future__ import annotations

from pathlib import Path
import sys

CURRENT_DIR = Path(__file__).resolve().parent
if str(CURRENT_DIR) not in sys.path:
    sys.path.insert(0, str(CURRENT_DIR))

REPO_ROOT = next(parent for parent in Path(__file__).resolve().parents if (parent / "kernel_gen").exists())
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from importlib import import_module

print_case_actual_ir = import_module("expectation.pass.lowing._shared").print_case_actual_ir
from expectation.utils.case_runner import raise_if_failures, run_case
from _random_utils import (
    random_cast_dtype_pair_irs,
    random_space_attr_ir,
    random_static_dims,
    random_symbol_names,
)
from kernel_gen.tools.ircheck import run_ircheck_text

STATIC_M, STATIC_N = random_static_dims(2)
SYM_M, SYM_N = random_symbol_names(2)
SRC_DTYPE_IR, DST_DTYPE_IR = random_cast_dtype_pair_irs()
SPACE_ATTR = random_space_attr_ir()


def _build_case_static() -> tuple[str, str]:
    """构造静态 `nn.cast` case 的描述与 `ircheck` 文本。"""

    desc = "Case-cast-static: 正例：静态 nn.cast 输入应 lower 为 dma.alloc + dma.cast + func.return。"
    case_text = f"""// COMPILE_ARGS: --pass lower-nn
// CASE: {desc}
// CHECK: builtin.module {{
// CHECK-NEXT: func.func @cast_kernel(%[[ARG0:{{reg}}]] : !nn.memory<[{STATIC_M}, {STATIC_N}], [{STATIC_N}, 1], {SRC_DTYPE_IR}, {SPACE_ATTR}>) -> !nn.memory<[{STATIC_M}, {STATIC_N}], [{STATIC_N}, 1], {DST_DTYPE_IR}, {SPACE_ATTR}> {{
// CHECK-NEXT: %[[V0:{{reg}}]] = "dma.alloc"() <{{operandSegmentSizes = array<i32: 0>}}> : () -> !nn.memory<[{STATIC_M}, {STATIC_N}], [{STATIC_N}, 1], {DST_DTYPE_IR}, {SPACE_ATTR}>
// CHECK-NEXT: "dma.cast"(%[[V0]], %[[ARG0]]) : (!nn.memory<[{STATIC_M}, {STATIC_N}], [{STATIC_N}, 1], {DST_DTYPE_IR}, {SPACE_ATTR}>, !nn.memory<[{STATIC_M}, {STATIC_N}], [{STATIC_N}, 1], {SRC_DTYPE_IR}, {SPACE_ATTR}>) -> ()
// CHECK-NEXT: func.return %[[V0]] : !nn.memory<[{STATIC_M}, {STATIC_N}], [{STATIC_N}, 1], {DST_DTYPE_IR}, {SPACE_ATTR}>
// CHECK-NEXT: }}
// CHECK-NEXT: }}
// CHECK-NOT: nn.cast

builtin.module {{
  func.func @cast_kernel(%arg0: !nn.memory<[{STATIC_M}, {STATIC_N}], [{STATIC_N}, 1], {SRC_DTYPE_IR}, {SPACE_ATTR}>) -> !nn.memory<[{STATIC_M}, {STATIC_N}], [{STATIC_N}, 1], {DST_DTYPE_IR}, {SPACE_ATTR}> {{
    %0 = "nn.cast"(%arg0) {{space = {SPACE_ATTR}}} : (!nn.memory<[{STATIC_M}, {STATIC_N}], [{STATIC_N}, 1], {SRC_DTYPE_IR}, {SPACE_ATTR}>) -> !nn.memory<[{STATIC_M}, {STATIC_N}], [{STATIC_N}, 1], {DST_DTYPE_IR}, {SPACE_ATTR}>
    func.return %0 : !nn.memory<[{STATIC_M}, {STATIC_N}], [{STATIC_N}, 1], {DST_DTYPE_IR}, {SPACE_ATTR}>
  }}
}}"""
    return desc, case_text


def _build_case_dynamic() -> tuple[str, str]:
    """构造动态 `nn.cast` case 的描述与 `ircheck` 文本。"""

    desc = "Case-cast-dynamic: 正例：符号维度 nn.cast 输入应 lower 为 dma.alloc + dma.cast + func.return。"
    case_text = f"""// COMPILE_ARGS: --pass lower-nn
// CASE: {desc}
// CHECK: builtin.module {{
// CHECK-NEXT: func.func @cast_kernel(%[[ARG0:{{reg}}]] : !nn.memory<[{SYM_M}, {SYM_N}], [{SYM_N}, 1], {SRC_DTYPE_IR}, {SPACE_ATTR}>) -> !nn.memory<[{SYM_M}, {SYM_N}], [{SYM_N}, 1], {DST_DTYPE_IR}, {SPACE_ATTR}> {{
// CHECK-NEXT: %[[V0:{{reg}}]] = "symbol.get_dim"(%[[ARG0]]) {{axis = #builtin.int<0>}} : (!nn.memory<[{SYM_M}, {SYM_N}], [{SYM_N}, 1], {SRC_DTYPE_IR}, {SPACE_ATTR}>) -> !symbol.int<"{SYM_M}">
// CHECK-NEXT: %[[V1:{{reg}}]] = "symbol.get_dim"(%[[ARG0]]) {{axis = #builtin.int<1>}} : (!nn.memory<[{SYM_M}, {SYM_N}], [{SYM_N}, 1], {SRC_DTYPE_IR}, {SPACE_ATTR}>) -> !symbol.int<"{SYM_N}">
// CHECK-NEXT: %[[V2:{{reg}}]] = "dma.alloc"(%[[V0]], %[[V1]]) <{{operandSegmentSizes = array<i32: 2>}}> : (!symbol.int<"{SYM_M}">, !symbol.int<"{SYM_N}">) -> !nn.memory<[{SYM_M}, {SYM_N}], [{SYM_N}, 1], {DST_DTYPE_IR}, {SPACE_ATTR}>
// CHECK-NEXT: "dma.cast"(%[[V2]], %[[ARG0]]) : (!nn.memory<[{SYM_M}, {SYM_N}], [{SYM_N}, 1], {DST_DTYPE_IR}, {SPACE_ATTR}>, !nn.memory<[{SYM_M}, {SYM_N}], [{SYM_N}, 1], {SRC_DTYPE_IR}, {SPACE_ATTR}>) -> ()
// CHECK-NEXT: func.return %[[V2]] : !nn.memory<[{SYM_M}, {SYM_N}], [{SYM_N}, 1], {DST_DTYPE_IR}, {SPACE_ATTR}>
// CHECK-NEXT: }}
// CHECK-NEXT: }}
// CHECK-NOT: nn.cast

builtin.module {{
  func.func @cast_kernel(%arg0: !nn.memory<[{SYM_M}, {SYM_N}], [{SYM_N}, 1], {SRC_DTYPE_IR}, {SPACE_ATTR}>) -> !nn.memory<[{SYM_M}, {SYM_N}], [{SYM_N}, 1], {DST_DTYPE_IR}, {SPACE_ATTR}> {{
    %0 = "nn.cast"(%arg0) {{space = {SPACE_ATTR}}} : (!nn.memory<[{SYM_M}, {SYM_N}], [{SYM_N}, 1], {SRC_DTYPE_IR}, {SPACE_ATTR}>) -> !nn.memory<[{SYM_M}, {SYM_N}], [{SYM_N}, 1], {DST_DTYPE_IR}, {SPACE_ATTR}>
    func.return %0 : !nn.memory<[{SYM_M}, {SYM_N}], [{SYM_N}, 1], {DST_DTYPE_IR}, {SPACE_ATTR}>
  }}
}}"""
    return desc, case_text


def _run_case(case_text: str, *, source_path: str) -> str:
    """运行单个 `ircheck` case 并返回实际 IR 文本。"""

    result = run_ircheck_text(case_text, source_path=source_path)
    assert result.ok is True, (
        f"expected ok=True, got ok={result.ok}, exit_code={result.exit_code}, message={result.message!r}"
    )
    assert result.exit_code == 0, f"expected exit_code=0, got {result.exit_code}"
    return result.actual_ir


def _case_static_true() -> None:
    """正例：静态 `nn.cast` 输入应 lower 为 `dma.alloc + dma.cast + func.return`。"""

    case_desc, case_text = _build_case_static()
    actual_ir = _run_case(case_text, source_path="expectation/pass/lowing/nn_lowering/cast.py:static")
    assert "dma.cast" in actual_ir, "actual_ir must contain dma.cast"
    assert "nn.cast" not in actual_ir, "actual_ir must not contain residual nn.cast"
    print_case_actual_ir("CASE-cast-static", case_text, actual_ir, fallback=case_desc)


def _case_dynamic_true() -> None:
    """正例：符号维度 `nn.cast` 输入应 lower 为 `dma.alloc + dma.cast + func.return`。"""

    case_desc, case_text = _build_case_dynamic()
    actual_ir = _run_case(case_text, source_path="expectation/pass/lowing/nn_lowering/cast.py:dynamic")
    assert "dma.cast" in actual_ir, "actual_ir must contain dma.cast"
    assert "nn.cast" not in actual_ir, "actual_ir must not contain residual nn.cast"
    print_case_actual_ir("CASE-cast-dynamic", case_text, actual_ir, fallback=case_desc)


def main() -> None:
    """运行 `cast` ircheck expectation。"""

    failures: list[tuple[str, BaseException]] = []
    run_case(failures, "CASE-cast-static", _case_static_true)
    run_case(failures, "CASE-cast-dynamic", _case_dynamic_true)
    raise_if_failures("nn_lowering cast expectation", failures)


if __name__ == "__main__":
    main()
