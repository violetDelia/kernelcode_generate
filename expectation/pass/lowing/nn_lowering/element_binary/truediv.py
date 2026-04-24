"""pass nn_lowering element_binary expectation：truediv。
[immutable-file]


创建者: 大闸蟹
最后一次更改: 大闸蟹

功能说明:
- 使用完整 `CASE_TEXT` 运行 `ircheck` 版 `truediv` expectation。

使用示例:
- `PYTHONPATH=. python expectation/pass/lowing/nn_lowering/element_binary/truediv.py`

关联文件:
- spec: [`spec/pass/lowering/nn_lowering.md`](spec/pass/lowering/nn_lowering.md)
- spec: [`spec/tools/ircheck.md`](spec/tools/ircheck.md)
- test: [`test/pass/test_lowering_nn_to_kernel.py`](test/pass/test_lowering_nn_to_kernel.py)
- 功能实现: [`expectation/pass/lowing/nn_lowering/element_binary/_shared.py`](expectation/pass/lowing/nn_lowering/element_binary/_shared.py)
"""

# Case 列表:
# - Case-1: 正例：静态 nn.truediv memory + memory 输入应 lower 为 dma.alloc + kernel.binary_elewise(kind=div) + func.return。
# - Case-2: 正例：静态 nn.truediv memory + const 输入应 lower 为 dma.alloc + dma.fill + kernel.binary_elewise(kind=div) + func.return。
# - Case-3: 正例：符号维度 nn.truediv memory + memory 输入应 lower 为 symbol.get_dim + dma.alloc + kernel.binary_elewise(kind=div) + func.return。
# - Case-4: 正例：符号维度 nn.truediv memory + symbol 输入应 lower 为 symbol.get_dim + dma.alloc + dma.fill + kernel.binary_elewise(kind=div) + func.return。
# - Case-5: 正例：符号维度 nn.truediv memory + (const + symbol) 输入应 lower 为 symbol.get_dim + dma.alloc + dma.fill + kernel.binary_elewise(kind=div) + func.return。

from __future__ import annotations

from pathlib import Path
import sys

CURRENT_DIR = Path(__file__).resolve().parent
if str(CURRENT_DIR) not in sys.path:
    sys.path.insert(0, str(CURRENT_DIR))
PARENT_DIR = CURRENT_DIR.parent
if str(PARENT_DIR) not in sys.path:
    sys.path.append(str(PARENT_DIR))

from _random_utils import (
    random_arithmetic_dtype_ir,
    random_space_attr_ir,
    random_static_dims,
    random_symbol_names,
)
from _shared import run_single

OP_NAME = "truediv"
KIND_NAME = "div"
STATIC_M, STATIC_N = random_static_dims(2)
SYM_M, SYM_N = random_symbol_names(2)
DATA_DTYPE_IR = random_arithmetic_dtype_ir()
SPACE_ATTR = random_space_attr_ir()
STATIC_SHAPE = f"[{STATIC_M}, {STATIC_N}]"
STATIC_STRIDE = f"[{STATIC_N}, 1]"
DYNAMIC_SHAPE = f"[{SYM_M}, {SYM_N}]"
DYNAMIC_STRIDE = f"[{SYM_N}, 1]"
STATIC_MEMORY_F32 = f"!nn.memory<{STATIC_SHAPE}, {STATIC_STRIDE}, {DATA_DTYPE_IR}, {SPACE_ATTR}>"
STATIC_MEMORY_I32 = f"!nn.memory<{STATIC_SHAPE}, {STATIC_STRIDE}, i32, {SPACE_ATTR}>"
DYNAMIC_MEMORY_F32 = f"!nn.memory<{DYNAMIC_SHAPE}, {DYNAMIC_STRIDE}, {DATA_DTYPE_IR}, {SPACE_ATTR}>"
DYNAMIC_MEMORY_I32 = f"!nn.memory<{DYNAMIC_SHAPE}, {DYNAMIC_STRIDE}, i32, {SPACE_ATTR}>"
SYM_M_TYPE = f'!symbol.int<"{SYM_M}">'
SYM_N_TYPE = f'!symbol.int<"{SYM_N}">'
SYM_ONE_PLUS_M_TYPE = f'!symbol.int<"1 + {SYM_M}">'

CASE_TEXT_STATIC_MEMORY = f"""// COMPILE_ARGS: --pass lower-nn
// CASE: 正例：静态 nn.{OP_NAME} memory + memory 输入应 lower 为 dma.alloc + kernel.binary_elewise(kind={KIND_NAME}) + func.return。
// CHECK: builtin.module {{
// CHECK-NEXT: func.func @{OP_NAME}_kernel(%[[LHS:{{reg}}]] : {STATIC_MEMORY_F32}, %[[RHS:{{reg}}]] : {STATIC_MEMORY_F32}) -> {STATIC_MEMORY_F32} {{
// CHECK-NEXT: %[[V0:{{reg}}]] = "dma.alloc"() <{{operandSegmentSizes = array<i32: 0>}}> : () -> {STATIC_MEMORY_F32}
// CHECK-NEXT: "kernel.binary_elewise"(%[[V0]], %[[LHS]], %[[RHS]]) {{kind = "{KIND_NAME}", space = {SPACE_ATTR}}} : ({STATIC_MEMORY_F32}, {STATIC_MEMORY_F32}, {STATIC_MEMORY_F32}) -> ()
// CHECK-NEXT: func.return %[[V0]] : {STATIC_MEMORY_F32}
// CHECK-NEXT: }}
// CHECK-NEXT: }}
// CHECK-NOT: nn.{OP_NAME}

builtin.module {{
  func.func @{OP_NAME}_kernel(%lhs: {STATIC_MEMORY_F32}, %rhs: {STATIC_MEMORY_F32}) -> {STATIC_MEMORY_F32} {{
    %0 = "nn.{OP_NAME}"(%lhs, %rhs) {{space = {SPACE_ATTR}}} : ({STATIC_MEMORY_F32}, {STATIC_MEMORY_F32}) -> {STATIC_MEMORY_F32}
    func.return %0 : {STATIC_MEMORY_F32}
  }}
}}"""

CASE_TEXT_STATIC_CONST = f"""// COMPILE_ARGS: --pass lower-nn
// CASE: 正例：静态 nn.{OP_NAME} memory + const 输入应 lower 为 dma.alloc + dma.fill + kernel.binary_elewise(kind={KIND_NAME}) + func.return。
// CHECK: builtin.module {{
// CHECK-NEXT: func.func @{OP_NAME}_kernel_const(%[[LHS:{{reg}}]] : {STATIC_MEMORY_I32}) -> {STATIC_MEMORY_I32} {{
// CHECK-NEXT: %[[V0:{{reg}}]] = symbol.const 3 : !symbol.int<"3">
// CHECK-NEXT: %[[V1:{{reg}}]] = "dma.alloc"() <{{operandSegmentSizes = array<i32: 0>}}> : () -> {STATIC_MEMORY_I32}
// CHECK-NEXT: %[[V2:{{reg}}]] = "dma.alloc"() <{{operandSegmentSizes = array<i32: 0>}}> : () -> {STATIC_MEMORY_I32}
// CHECK-NEXT: "dma.fill"(%[[V2]], %[[V0]]) : ({STATIC_MEMORY_I32}, !symbol.int<"3">) -> ()
// CHECK-NEXT: "kernel.binary_elewise"(%[[V1]], %[[LHS]], %[[V2]]) {{kind = "{KIND_NAME}", space = {SPACE_ATTR}}} : ({STATIC_MEMORY_I32}, {STATIC_MEMORY_I32}, {STATIC_MEMORY_I32}) -> ()
// CHECK-NEXT: func.return %[[V1]] : {STATIC_MEMORY_I32}
// CHECK-NEXT: }}
// CHECK-NEXT: }}
// CHECK-NOT: nn.{OP_NAME}

builtin.module {{
  func.func @{OP_NAME}_kernel_const(%lhs: {STATIC_MEMORY_I32}) -> {STATIC_MEMORY_I32} {{
    %c0 = symbol.const 3 : !symbol.int<"3">
    %0 = "nn.{OP_NAME}"(%lhs, %c0) {{space = {SPACE_ATTR}}} : ({STATIC_MEMORY_I32}, !symbol.int<"3">) -> {STATIC_MEMORY_I32}
    func.return %0 : {STATIC_MEMORY_I32}
  }}
}}"""

CASE_TEXT_DYNAMIC_MEMORY = f"""// COMPILE_ARGS: --pass lower-nn
// CASE: 正例：符号维度 nn.{OP_NAME} memory + memory 输入应 lower 为 symbol.get_dim + dma.alloc + kernel.binary_elewise(kind={KIND_NAME}) + func.return。
// CHECK: builtin.module {{
// CHECK-NEXT: func.func @{OP_NAME}_kernel_dynamic(%[[LHS:{{reg}}]] : {DYNAMIC_MEMORY_F32}, %[[RHS:{{reg}}]] : {DYNAMIC_MEMORY_F32}) -> {DYNAMIC_MEMORY_F32} {{
// CHECK-NEXT: %[[V0:{{reg}}]] = "symbol.get_dim"(%[[LHS]]) {{axis = #builtin.int<0>}} : ({DYNAMIC_MEMORY_F32}) -> {SYM_M_TYPE}
// CHECK-NEXT: %[[V1:{{reg}}]] = "symbol.get_dim"(%[[LHS]]) {{axis = #builtin.int<1>}} : ({DYNAMIC_MEMORY_F32}) -> {SYM_N_TYPE}
// CHECK-NEXT: %[[V2:{{reg}}]] = "dma.alloc"(%[[V0]], %[[V1]]) <{{operandSegmentSizes = array<i32: 2>}}> : ({SYM_M_TYPE}, {SYM_N_TYPE}) -> {DYNAMIC_MEMORY_F32}
// CHECK-NEXT: "kernel.binary_elewise"(%[[V2]], %[[LHS]], %[[RHS]]) {{kind = "{KIND_NAME}", space = {SPACE_ATTR}}} : ({DYNAMIC_MEMORY_F32}, {DYNAMIC_MEMORY_F32}, {DYNAMIC_MEMORY_F32}) -> ()
// CHECK-NEXT: func.return %[[V2]] : {DYNAMIC_MEMORY_F32}
// CHECK-NEXT: }}
// CHECK-NEXT: }}
// CHECK-NOT: nn.{OP_NAME}

builtin.module {{
  func.func @{OP_NAME}_kernel_dynamic(%lhs: {DYNAMIC_MEMORY_F32}, %rhs: {DYNAMIC_MEMORY_F32}) -> {DYNAMIC_MEMORY_F32} {{
    %0 = "nn.{OP_NAME}"(%lhs, %rhs) {{space = {SPACE_ATTR}}} : ({DYNAMIC_MEMORY_F32}, {DYNAMIC_MEMORY_F32}) -> {DYNAMIC_MEMORY_F32}
    func.return %0 : {DYNAMIC_MEMORY_F32}
  }}
}}"""

CASE_TEXT_DYNAMIC_SYMBOL = f"""// COMPILE_ARGS: --pass lower-nn
// CASE: 正例：符号维度 nn.{OP_NAME} memory + symbol 输入应 lower 为 symbol.get_dim + dma.alloc + dma.fill + kernel.binary_elewise(kind={KIND_NAME}) + func.return。
// CHECK: builtin.module {{
// CHECK-NEXT: func.func @{OP_NAME}_kernel_symbol(%[[LHS:{{reg}}]] : {DYNAMIC_MEMORY_I32}, %[[RHS:{{reg}}]] : {SYM_M_TYPE}) -> {DYNAMIC_MEMORY_I32} {{
// CHECK-NEXT: %[[V0:{{reg}}]] = "symbol.get_dim"(%[[LHS]]) {{axis = #builtin.int<0>}} : ({DYNAMIC_MEMORY_I32}) -> {SYM_M_TYPE}
// CHECK-NEXT: %[[V1:{{reg}}]] = "symbol.get_dim"(%[[LHS]]) {{axis = #builtin.int<1>}} : ({DYNAMIC_MEMORY_I32}) -> {SYM_N_TYPE}
// CHECK-NEXT: %[[V2:{{reg}}]] = "dma.alloc"(%[[V0]], %[[V1]]) <{{operandSegmentSizes = array<i32: 2>}}> : ({SYM_M_TYPE}, {SYM_N_TYPE}) -> {DYNAMIC_MEMORY_I32}
// CHECK-NEXT: %[[V3:{{reg}}]] = "dma.alloc"(%[[V0]], %[[V1]]) <{{operandSegmentSizes = array<i32: 2>}}> : ({SYM_M_TYPE}, {SYM_N_TYPE}) -> {DYNAMIC_MEMORY_I32}
// CHECK-NEXT: "dma.fill"(%[[V3]], %[[RHS]]) : ({DYNAMIC_MEMORY_I32}, {SYM_M_TYPE}) -> ()
// CHECK-NEXT: "kernel.binary_elewise"(%[[V2]], %[[LHS]], %[[V3]]) {{kind = "{KIND_NAME}", space = {SPACE_ATTR}}} : ({DYNAMIC_MEMORY_I32}, {DYNAMIC_MEMORY_I32}, {DYNAMIC_MEMORY_I32}) -> ()
// CHECK-NEXT: func.return %[[V2]] : {DYNAMIC_MEMORY_I32}
// CHECK-NEXT: }}
// CHECK-NEXT: }}
// CHECK-NOT: nn.{OP_NAME}

builtin.module {{
  func.func @{OP_NAME}_kernel_symbol(%lhs: {DYNAMIC_MEMORY_I32}, %rhs: {SYM_M_TYPE}) -> {DYNAMIC_MEMORY_I32} {{
    %0 = "nn.{OP_NAME}"(%lhs, %rhs) {{space = {SPACE_ATTR}}} : ({DYNAMIC_MEMORY_I32}, {SYM_M_TYPE}) -> {DYNAMIC_MEMORY_I32}
    func.return %0 : {DYNAMIC_MEMORY_I32}
  }}
}}"""

CASE_TEXT_DYNAMIC_CONST_SYMBOL = f"""// COMPILE_ARGS: --pass lower-nn
// CASE: 正例：符号维度 nn.{OP_NAME} memory + (const + symbol) 输入应 lower 为 symbol.get_dim + dma.alloc + dma.fill + kernel.binary_elewise(kind={KIND_NAME}) + func.return。
// CHECK: builtin.module {{
// CHECK-NEXT: func.func @{OP_NAME}_kernel_const_symbol(%[[LHS:{{reg}}]] : {DYNAMIC_MEMORY_I32}, %[[RHS:{{reg}}]] : {SYM_M_TYPE}) -> {DYNAMIC_MEMORY_I32} {{
// CHECK-NEXT: %[[V0:{{reg}}]] = symbol.const 1 : !symbol.int<"1">
// CHECK-NEXT: %[[V1:{{reg}}]] = symbol.add %[[V0]], %[[RHS]] : !symbol.int<"1">, {SYM_M_TYPE} -> {SYM_ONE_PLUS_M_TYPE}
// CHECK-NEXT: %[[V2:{{reg}}]] = "symbol.get_dim"(%[[LHS]]) {{axis = #builtin.int<0>}} : ({DYNAMIC_MEMORY_I32}) -> {SYM_M_TYPE}
// CHECK-NEXT: %[[V3:{{reg}}]] = "symbol.get_dim"(%[[LHS]]) {{axis = #builtin.int<1>}} : ({DYNAMIC_MEMORY_I32}) -> {SYM_N_TYPE}
// CHECK-NEXT: %[[V4:{{reg}}]] = "dma.alloc"(%[[V2]], %[[V3]]) <{{operandSegmentSizes = array<i32: 2>}}> : ({SYM_M_TYPE}, {SYM_N_TYPE}) -> {DYNAMIC_MEMORY_I32}
// CHECK-NEXT: %[[V5:{{reg}}]] = "dma.alloc"(%[[V2]], %[[V3]]) <{{operandSegmentSizes = array<i32: 2>}}> : ({SYM_M_TYPE}, {SYM_N_TYPE}) -> {DYNAMIC_MEMORY_I32}
// CHECK-NEXT: "dma.fill"(%[[V5]], %[[V1]]) : ({DYNAMIC_MEMORY_I32}, {SYM_ONE_PLUS_M_TYPE}) -> ()
// CHECK-NEXT: "kernel.binary_elewise"(%[[V4]], %[[LHS]], %[[V5]]) {{kind = "{KIND_NAME}", space = {SPACE_ATTR}}} : ({DYNAMIC_MEMORY_I32}, {DYNAMIC_MEMORY_I32}, {DYNAMIC_MEMORY_I32}) -> ()
// CHECK-NEXT: func.return %[[V4]] : {DYNAMIC_MEMORY_I32}
// CHECK-NEXT: }}
// CHECK-NEXT: }}
// CHECK-NOT: nn.{OP_NAME}

builtin.module {{
  func.func @{OP_NAME}_kernel_const_symbol(%lhs: {DYNAMIC_MEMORY_I32}, %rhs: {SYM_M_TYPE}) -> {DYNAMIC_MEMORY_I32} {{
    %c1 = symbol.const 1 : !symbol.int<"1">
    %sum = symbol.add %c1, %rhs : !symbol.int<"1">, {SYM_M_TYPE} -> {SYM_ONE_PLUS_M_TYPE}
    %0 = "nn.{OP_NAME}"(%lhs, %sum) {{space = {SPACE_ATTR}}} : ({DYNAMIC_MEMORY_I32}, {SYM_ONE_PLUS_M_TYPE}) -> {DYNAMIC_MEMORY_I32}
    func.return %0 : {DYNAMIC_MEMORY_I32}
  }}
}}"""

CASE_TEXT_STATIC = (CASE_TEXT_STATIC_MEMORY, CASE_TEXT_STATIC_CONST)
CASE_TEXT_DYNAMIC = (
    CASE_TEXT_DYNAMIC_MEMORY,
    CASE_TEXT_DYNAMIC_SYMBOL,
    CASE_TEXT_DYNAMIC_CONST_SYMBOL,
)


def main() -> None:
    """运行 `truediv` ircheck expectation。"""

    run_single(OP_NAME, CASE_TEXT_STATIC, CASE_TEXT_DYNAMIC)


if __name__ == "__main__":
    main()
