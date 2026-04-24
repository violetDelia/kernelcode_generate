"""pass nn_lowering img2col expectation：img2col1d。
[immutable-file]


创建者: 大闸蟹
最后一次更改: 大闸蟹

功能说明:
- 使用完整 `CASE_TEXT` 运行 `ircheck` 版 `img2col1d` expectation。

使用示例:
- `PYTHONPATH=. python expectation/pass/lowing/nn_lowering/img2col/img2col1d.py`

关联文件:
- spec: [`spec/pass/lowering/nn_lowering.md`](spec/pass/lowering/nn_lowering.md)
- spec: [`spec/tools/ircheck.md`](spec/tools/ircheck.md)
- test: [`test/pass/test_lowering_nn_to_kernel.py`](test/pass/test_lowering_nn_to_kernel.py)
- 功能实现: [`expectation/pass/lowing/nn_lowering/img2col/_shared.py`](expectation/pass/lowing/nn_lowering/img2col/_shared.py)
"""

# Case 列表:
# - Case-1: 正例：静态 nn.img2col1d 输入应 lower 为 dma.alloc + kernel.img2col1d + func.return。
# - Case-2: 正例：符号维度 nn.img2col1d 输入应 lower 为 dma.alloc + kernel.img2col1d + func.return。

from __future__ import annotations

from importlib import import_module
from pathlib import Path
import sys

CURRENT_DIR = Path(__file__).resolve().parent
if str(CURRENT_DIR) not in sys.path:
    sys.path.insert(0, str(CURRENT_DIR))
PARENT_DIR = CURRENT_DIR.parent
if str(PARENT_DIR) not in sys.path:
    sys.path.insert(0, str(PARENT_DIR))
REPO_ROOT = next(parent for parent in Path(__file__).resolve().parents if (parent / "kernel_gen").exists())
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from expectation.utils.random_utils import (
    memory_space_ir_name,
    memory_type_from_memory,
    shape_tokens,
    symbol_int_type_ir,
)
from expectation.utils.sample_values import (
    get_random_arithmetic_numeric_type,
    get_random_int,
    get_random_memory_space,
    get_random_non_zero_int,
)
from kernel_gen.operation.nn import img2col1d
from kernel_gen.symbol_variable.memory import Memory
from kernel_gen.symbol_variable.symbol_dim import SymbolDim
from _random_utils import random_static_dims, random_symbol_names

run_single = import_module(
    "expectation.pass.lowing.nn_lowering.img2col._shared"
).run_single

DTYPE = get_random_arithmetic_numeric_type()
SPACE = get_random_memory_space()
SPACE_ATTR = f"#nn.space<{memory_space_ir_name(SPACE)}>"

STATIC_B, STATIC_C, STATIC_W = random_static_dims(3)
STATIC_INPUT = Memory([STATIC_B, STATIC_C, STATIC_W], DTYPE, space=SPACE)
while True:
    STATIC_KW = get_random_non_zero_int(1, 4)
    STATIC_SW = get_random_non_zero_int(1, 4)
    STATIC_DW = get_random_non_zero_int(1, 4)
    STATIC_PL = get_random_int(0, 4)
    STATIC_PR = get_random_int(0, 4)
    try:
        STATIC_OUTPUT = img2col1d(STATIC_INPUT, STATIC_KW, STATIC_SW, STATIC_DW, STATIC_PL, STATIC_PR)
        break
    except ValueError:
        continue

STATIC_SRC = memory_type_from_memory(STATIC_INPUT)
STATIC_DST = memory_type_from_memory(STATIC_OUTPUT)

(
    DYN_B_SUFFIX,
    DYN_C_SUFFIX,
    DYN_W_SUFFIX,
    DYN_KW_SUFFIX,
    DYN_SW_SUFFIX,
    DYN_DW_SUFFIX,
    DYN_PL_SUFFIX,
    DYN_PR_SUFFIX,
    DYN_SI0_SUFFIX,
    DYN_SI1_SUFFIX,
) = random_symbol_names(10)

DYN_B = f"B_{DYN_B_SUFFIX}"
DYN_C = f"C_{DYN_C_SUFFIX}"
DYN_W = f"W_{DYN_W_SUFFIX}"
DYN_KW = f"KW_{DYN_KW_SUFFIX}"
DYN_SW = f"SW_{DYN_SW_SUFFIX}"
DYN_DW = f"DW_{DYN_DW_SUFFIX}"
DYN_PL = f"PL_{DYN_PL_SUFFIX}"
DYN_PR = f"PR_{DYN_PR_SUFFIX}"
DYN_SI0 = f"SI0_{DYN_SI0_SUFFIX}"
DYN_SI1 = f"SI1_{DYN_SI1_SUFFIX}"

DYNAMIC_INPUT = Memory(
    [SymbolDim(DYN_B), SymbolDim(DYN_C), SymbolDim(DYN_W)],
    DTYPE,
    space=SPACE,
    stride=[SymbolDim(DYN_SI0), SymbolDim(DYN_SI1), 1],
)
DYNAMIC_OUTPUT = img2col1d(
    DYNAMIC_INPUT,
    SymbolDim(DYN_KW),
    SymbolDim(DYN_SW),
    SymbolDim(DYN_DW),
    SymbolDim(DYN_PL),
    SymbolDim(DYN_PR),
)

DYN_SRC = memory_type_from_memory(DYNAMIC_INPUT)
DYN_DST = memory_type_from_memory(DYNAMIC_OUTPUT)
DYN_B_TYPE = symbol_int_type_ir(DYN_B)
DYN_C_TYPE = symbol_int_type_ir(DYN_C)
DYN_W_TYPE = symbol_int_type_ir(DYN_W)
DYN_KW_TYPE = symbol_int_type_ir(DYN_KW)
DYN_SW_TYPE = symbol_int_type_ir(DYN_SW)
DYN_DW_TYPE = symbol_int_type_ir(DYN_DW)
DYN_PL_TYPE = symbol_int_type_ir(DYN_PL)
DYN_PR_TYPE = symbol_int_type_ir(DYN_PR)
DYN_W_OUT = shape_tokens(DYNAMIC_OUTPUT.shape)[3]
DYN_W_OUT_TYPE = symbol_int_type_ir(DYN_W_OUT)
DYN_KW_MINUS_ONE = f"{DYN_KW} - 1"
DYN_DW_MUL = f"{DYN_DW}*({DYN_KW_MINUS_ONE})"
DYN_W_PL = f"{DYN_W} + {DYN_PL}"
DYN_W_PL_PR = f"{DYN_W_PL} + {DYN_PR}"
DYN_W_MINUS_DW = f"{DYN_W_PL_PR} - {DYN_DW_MUL}"
DYN_W_MINUS_ONE = f"{DYN_W_MINUS_DW} - 1"
DYN_W_DIV = f"({DYN_W_MINUS_ONE}) // {DYN_SW}"

CASE_TEXT_STATIC = f"""// COMPILE_ARGS: --pass lower-nn
// CASE: 正例：静态 nn.img2col1d 输入应 lower 为 dma.alloc + kernel.img2col1d + func.return。
// CHECK: builtin.module {{
// CHECK-NEXT: func.func @img2col1d_kernel(%[[ARG0:{{reg}}]] : {STATIC_SRC}) -> {STATIC_DST} {{
// CHECK-NEXT: %[[V0:{{reg}}]] = symbol.const {STATIC_KW} : !symbol.int<"{STATIC_KW}">
// CHECK-NEXT: %[[V1:{{reg}}]] = symbol.const {STATIC_SW} : !symbol.int<"{STATIC_SW}">
// CHECK-NEXT: %[[V2:{{reg}}]] = symbol.const {STATIC_DW} : !symbol.int<"{STATIC_DW}">
// CHECK-NEXT: %[[V3:{{reg}}]] = symbol.const {STATIC_PL} : !symbol.int<"{STATIC_PL}">
// CHECK-NEXT: %[[V4:{{reg}}]] = symbol.const {STATIC_PR} : !symbol.int<"{STATIC_PR}">
// CHECK-NEXT: %[[V5:{{reg}}]] = "dma.alloc"() <{{operandSegmentSizes = array<i32: 0>}}> : () -> {STATIC_DST}
// CHECK-NEXT: "kernel.img2col1d"(%[[V5]], %[[ARG0]], %[[V0]], %[[V1]], %[[V2]], %[[V3]], %[[V4]]) {{space = {SPACE_ATTR}, stride = [{STATIC_SW}], dilation = [{STATIC_DW}], pad = [{STATIC_PL}, {STATIC_PR}]}} : ({STATIC_DST}, {STATIC_SRC}, !symbol.int<"{STATIC_KW}">, !symbol.int<"{STATIC_SW}">, !symbol.int<"{STATIC_DW}">, !symbol.int<"{STATIC_PL}">, !symbol.int<"{STATIC_PR}">) -> ()
// CHECK-NEXT: func.return %[[V5]] : {STATIC_DST}
// CHECK-NEXT: }}
// CHECK-NEXT: }}
// CHECK-NOT: nn.img2col1d

builtin.module {{
  func.func @img2col1d_kernel(%arg0: {STATIC_SRC}) -> {STATIC_DST} {{
    %kw = symbol.const {STATIC_KW} : !symbol.int<"{STATIC_KW}">
    %sw = symbol.const {STATIC_SW} : !symbol.int<"{STATIC_SW}">
    %dw = symbol.const {STATIC_DW} : !symbol.int<"{STATIC_DW}">
    %pl = symbol.const {STATIC_PL} : !symbol.int<"{STATIC_PL}">
    %pr = symbol.const {STATIC_PR} : !symbol.int<"{STATIC_PR}">
    %0 = "nn.img2col1d"(%arg0, %kw, %sw, %dw, %pl, %pr) {{space = {SPACE_ATTR}}} : ({STATIC_SRC}, !symbol.int<"{STATIC_KW}">, !symbol.int<"{STATIC_SW}">, !symbol.int<"{STATIC_DW}">, !symbol.int<"{STATIC_PL}">, !symbol.int<"{STATIC_PR}">) -> {STATIC_DST}
    func.return %0 : {STATIC_DST}
  }}
}}"""

CASE_TEXT_DYNAMIC = f"""// COMPILE_ARGS: --pass lower-nn
// CASE: 正例：符号维度 nn.img2col1d 输入应 lower 为 dma.alloc + kernel.img2col1d + func.return。
// CHECK: builtin.module {{
// CHECK-NEXT: func.func @img2col1d_kernel(%[[ARG0:{{reg}}]] : {DYN_SRC}, %[[KW:{{reg}}]] : {DYN_KW_TYPE}, %[[SW:{{reg}}]] : {DYN_SW_TYPE}, %[[DW:{{reg}}]] : {DYN_DW_TYPE}, %[[PL:{{reg}}]] : {DYN_PL_TYPE}, %[[PR:{{reg}}]] : {DYN_PR_TYPE}) -> {DYN_DST} {{
// CHECK-NEXT: %[[V0:{{reg}}]] = symbol.const 1 : !symbol.int<"1">
// CHECK-NEXT: %[[V1:{{reg}}]] = "symbol.get_dim"(%[[ARG0]]) {{axis = #builtin.int<0>}} : ({DYN_SRC}) -> {DYN_B_TYPE}
// CHECK-NEXT: %[[V2:{{reg}}]] = "symbol.get_dim"(%[[ARG0]]) {{axis = #builtin.int<1>}} : ({DYN_SRC}) -> {DYN_C_TYPE}
// CHECK-NEXT: %[[V3:{{reg}}]] = "symbol.get_dim"(%[[ARG0]]) {{axis = #builtin.int<2>}} : ({DYN_SRC}) -> {DYN_W_TYPE}
// CHECK-NEXT: %[[V4:{{reg}}]] = symbol.sub %[[KW]], %[[V0]] : {DYN_KW_TYPE}, !symbol.int<"1"> -> !symbol.int<"{DYN_KW_MINUS_ONE}">
// CHECK-NEXT: %[[V5:{{reg}}]] = symbol.mul %[[DW]], %[[V4]] : {DYN_DW_TYPE}, !symbol.int<"{DYN_KW_MINUS_ONE}"> -> !symbol.int<"{DYN_DW_MUL}">
// CHECK-NEXT: %[[V6:{{reg}}]] = symbol.add %[[V3]], %[[PL]] : {DYN_W_TYPE}, {DYN_PL_TYPE} -> !symbol.int<"{DYN_W_PL}">
// CHECK-NEXT: %[[V7:{{reg}}]] = symbol.add %[[V6]], %[[PR]] : !symbol.int<"{DYN_W_PL}">, {DYN_PR_TYPE} -> !symbol.int<"{DYN_W_PL_PR}">
// CHECK-NEXT: %[[V8:{{reg}}]] = symbol.sub %[[V7]], %[[V5]] : !symbol.int<"{DYN_W_PL_PR}">, !symbol.int<"{DYN_DW_MUL}"> -> !symbol.int<"{DYN_W_MINUS_DW}">
// CHECK-NEXT: %[[V9:{{reg}}]] = symbol.sub %[[V8]], %[[V0]] : !symbol.int<"{DYN_W_MINUS_DW}">, !symbol.int<"1"> -> !symbol.int<"{DYN_W_MINUS_ONE}">
// CHECK-NEXT: %[[V10:{{reg}}]] = symbol.floordiv %[[V9]], %[[SW]] : !symbol.int<"{DYN_W_MINUS_ONE}">, {DYN_SW_TYPE} -> !symbol.int<"{DYN_W_DIV}">
// CHECK-NEXT: %[[V11:{{reg}}]] = symbol.add %[[V10]], %[[V0]] : !symbol.int<"{DYN_W_DIV}">, !symbol.int<"1"> -> {DYN_W_OUT_TYPE}
// CHECK-NEXT: %[[V12:{{reg}}]] = "dma.alloc"(%[[V1]], %[[V2]], %[[KW]], %[[V11]]) <{{operandSegmentSizes = array<i32: 4>}}> : ({DYN_B_TYPE}, {DYN_C_TYPE}, {DYN_KW_TYPE}, {DYN_W_OUT_TYPE}) -> {DYN_DST}
// CHECK-NEXT: "kernel.img2col1d"(%[[V12]], %[[ARG0]], %[[KW]], %[[SW]], %[[DW]], %[[PL]], %[[PR]]) {{space = {SPACE_ATTR}, stride = ["{DYN_SW}"], dilation = ["{DYN_DW}"], pad = ["{DYN_PL}", "{DYN_PR}"]}} : ({DYN_DST}, {DYN_SRC}, {DYN_KW_TYPE}, {DYN_SW_TYPE}, {DYN_DW_TYPE}, {DYN_PL_TYPE}, {DYN_PR_TYPE}) -> ()
// CHECK-NEXT: func.return %[[V12]] : {DYN_DST}
// CHECK-NEXT: }}
// CHECK-NEXT: }}
// CHECK-NOT: nn.img2col1d

builtin.module {{
  func.func @img2col1d_kernel(%arg0: {DYN_SRC}, %kw: {DYN_KW_TYPE}, %sw: {DYN_SW_TYPE}, %dw: {DYN_DW_TYPE}, %pl: {DYN_PL_TYPE}, %pr: {DYN_PR_TYPE}) -> {DYN_DST} {{
    %0 = "nn.img2col1d"(%arg0, %kw, %sw, %dw, %pl, %pr) {{space = {SPACE_ATTR}}} : ({DYN_SRC}, {DYN_KW_TYPE}, {DYN_SW_TYPE}, {DYN_DW_TYPE}, {DYN_PL_TYPE}, {DYN_PR_TYPE}) -> {DYN_DST}
    func.return %0 : {DYN_DST}
  }}
}}"""


def main() -> None:
    """运行 `img2col1d` ircheck expectation。"""

    run_single("img2col1d", CASE_TEXT_STATIC, CASE_TEXT_DYNAMIC)


if __name__ == "__main__":
    main()
