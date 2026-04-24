"""`NnLoweringPass` 的动态新符号维 `broadcast` expectation。
[immutable-file]


创建者: 榕
最后一次更改: 榕

功能说明:
- 定义一个合法的 `nn.broadcast` 场景：输入为 `[1, N]`，结果为 `[M, N]`，
  且 `M` 作为 in-scope `!symbol.int<"M">` 函数参数显式存在。
- 目标合同是 lowering 应使用该符号参数与 `symbol.get_dim(%arg0, 1)` 构造 `dma.alloc`，
  再生成 `dma.broadcast`。
- 当前若 lowering 仍错误地要求所有动态结果维都必须来自输入 memory，本 expectation 应失败并暴露真实缺口。

使用示例:
- `PYTHONPATH=. python expectation/pass/lowing/nn_lowering/broadcast_new_symbol_dim.py`

关联文件:
- spec: [`spec/pass/lowering/nn_lowering.md`](spec/pass/lowering/nn_lowering.md)
- spec: [`spec/tools/ircheck.md`](spec/tools/ircheck.md)
- test: [`test/pass/nn_lowering/test_expectation_broadcast_new_symbol_dim.py`](test/pass/nn_lowering/test_expectation_broadcast_new_symbol_dim.py)
- 功能实现: [`kernel_gen/tools/ircheck.py`](kernel_gen/tools/ircheck.py)
- 功能实现: [`kernel_gen/passes/lowering/nn_lowering/dma_structured_lowering.py`](kernel_gen/passes/lowering/nn_lowering/dma_structured_lowering.py)
"""

# Case 列表:
# - CASE-1: 目标合同：合法的 `[1, N] -> [M, N]` 动态 `nn.broadcast` 应 lower 成 `dma.alloc + dma.broadcast + func.return`。

from __future__ import annotations

from pathlib import Path
import sys

CURRENT_DIR = Path(__file__).resolve().parent
if str(CURRENT_DIR) not in sys.path:
    sys.path.insert(0, str(CURRENT_DIR))

REPO_ROOT = Path(__file__).resolve().parents[4]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from expectation.utils.case_runner import raise_if_failures, run_case
from _random_utils import (
    random_arithmetic_dtype_ir,
    random_space_attr_ir,
    random_symbol_names,
)
from kernel_gen.tools.ircheck import run_ircheck_text

SYM_M, SYM_N = random_symbol_names(2)
DTYPE_IR = random_arithmetic_dtype_ir()
SPACE_ATTR = random_space_attr_ir()
CASE_NAME = "CASE-broadcast-new-symbol-dim"
CASE_DESC = "目标合同：合法的 [1, N] -> [M, N] 动态 nn.broadcast 应 lower 成 dma.alloc + dma.broadcast + func.return。"

CASE_TEXT = f"""// COMPILE_ARGS: --pass lower-nn
// CASE: {CASE_DESC}
// CHECK: builtin.module {{
// CHECK-NEXT: func.func @broadcast_kernel(%[[ARG0:{{reg}}]] : !nn.memory<[1, {SYM_N}], [{SYM_N}, 1], {DTYPE_IR}, {SPACE_ATTR}>, %[[M:{{reg}}]] : !symbol.int<"{SYM_M}">) -> !nn.memory<[{SYM_M}, {SYM_N}], [{SYM_N}, 1], {DTYPE_IR}, {SPACE_ATTR}> {{
// CHECK-NEXT: %[[V0:{{reg}}]] = "symbol.get_dim"(%[[ARG0]]) {{axis = #builtin.int<1>}} : (!nn.memory<[1, {SYM_N}], [{SYM_N}, 1], {DTYPE_IR}, {SPACE_ATTR}>) -> !symbol.int<"{SYM_N}">
// CHECK-NEXT: %[[V1:{{reg}}]] = "dma.alloc"(%[[M]], %[[V0]]) <{{operandSegmentSizes = array<i32: 2>}}> : (!symbol.int<"{SYM_M}">, !symbol.int<"{SYM_N}">) -> !nn.memory<[{SYM_M}, {SYM_N}], [{SYM_N}, 1], {DTYPE_IR}, {SPACE_ATTR}>
// CHECK-NEXT: "dma.broadcast"(%[[V1]], %[[ARG0]]) : (!nn.memory<[{SYM_M}, {SYM_N}], [{SYM_N}, 1], {DTYPE_IR}, {SPACE_ATTR}>, !nn.memory<[1, {SYM_N}], [{SYM_N}, 1], {DTYPE_IR}, {SPACE_ATTR}>) -> ()
// CHECK-NEXT: func.return %[[V1]] : !nn.memory<[{SYM_M}, {SYM_N}], [{SYM_N}, 1], {DTYPE_IR}, {SPACE_ATTR}>
// CHECK-NEXT: }}
// CHECK-NEXT: }}
// CHECK-NOT: nn.broadcast

builtin.module {{
  func.func @broadcast_kernel(%arg0: !nn.memory<[1, {SYM_N}], [{SYM_N}, 1], {DTYPE_IR}, {SPACE_ATTR}>, %m: !symbol.int<"{SYM_M}">) -> !nn.memory<[{SYM_M}, {SYM_N}], [{SYM_N}, 1], {DTYPE_IR}, {SPACE_ATTR}> {{
    %0 = "nn.broadcast"(%arg0) {{space = {SPACE_ATTR}}} : (!nn.memory<[1, {SYM_N}], [{SYM_N}, 1], {DTYPE_IR}, {SPACE_ATTR}>) -> !nn.memory<[{SYM_M}, {SYM_N}], [{SYM_N}, 1], {DTYPE_IR}, {SPACE_ATTR}>
    func.return %0 : !nn.memory<[{SYM_M}, {SYM_N}], [{SYM_N}, 1], {DTYPE_IR}, {SPACE_ATTR}>
  }}
}}"""


def _case_1_new_symbol_dim_should_lower() -> None:
    """目标合同：合法的动态新符号维 broadcast 应能 lower。"""

    print(f"[{CASE_NAME}] {CASE_DESC}")
    result = run_ircheck_text(
        CASE_TEXT,
        source_path="expectation/pass/lowing/nn_lowering/broadcast_new_symbol_dim.py:case-1",
    )
    if result.ok is not True or result.exit_code != 0:
        raise AssertionError(
            "nn_lowering broadcast new-symbol-dim expectation 当前暴露真实缺口："
            "合法的 [1, N] -> [M, N] 动态 broadcast 仍被拒绝；"
            f"lowering 未正确使用 in-scope symbol 参数。原始错误: {result.message!r}"
        )
    assert "dma.broadcast" in result.actual_ir, "actual_ir must contain dma.broadcast"
    assert "nn.broadcast" not in result.actual_ir, "actual_ir must not contain residual nn.broadcast"


def main() -> None:
    """运行动态新符号维 broadcast expectation。"""

    failures: list[tuple[str, BaseException]] = []
    run_case(failures, CASE_NAME, _case_1_new_symbol_dim_should_lower)
    raise_if_failures("nn_lowering broadcast new-symbol-dim expectation", failures)


if __name__ == "__main__":
    main()
