"""pass nn_lowering reduce expectation：reduce_max。
[immutable-file]


创建者: 大闸蟹
最后一次更改: 大闸蟹

功能说明:
- 使用完整 `CASE_TEXT` 运行 `ircheck` 版 `reduce_max` expectation。

使用示例:
- `PYTHONPATH=. python expectation/pass/lowing/nn_lowering/reduce/reduce_max.py`

关联文件:
- spec: [`spec/pass/lowering/nn_lowering.md`](spec/pass/lowering/nn_lowering.md)
- spec: [`spec/tools/ircheck.md`](spec/tools/ircheck.md)
- test: [`test/pass/nn_lowering/reduce_max.py`](test/pass/nn_lowering/reduce_max.py)
- 功能实现: [`expectation/pass/lowing/nn_lowering/reduce/_shared.py`](expectation/pass/lowing/nn_lowering/reduce/_shared.py)
"""

# Case 列表:
# - Case-1: 正例：静态 nn.reduce_max 输入应 lower 为 dma.alloc + kernel.reduce(kind=max) + func.return。
# - Case-2: 正例：符号维度 nn.reduce_max 输入应 lower 为 dma.alloc + kernel.reduce(kind=max) + func.return。

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

STATIC_M, STATIC_N = random_static_dims(2)
SYM_M, SYM_N = random_symbol_names(2)
DTYPE_IR = random_arithmetic_dtype_ir()
SPACE_ATTR = random_space_attr_ir()
STATIC_SRC = f"!nn.memory<[{STATIC_M}, {STATIC_N}], [{STATIC_N}, 1], {DTYPE_IR}, {SPACE_ATTR}>"
STATIC_DST = f"!nn.memory<[{STATIC_M}, 1], [1, 1], {DTYPE_IR}, {SPACE_ATTR}>"
DYNAMIC_SRC = f"!nn.memory<[{SYM_M}, {SYM_N}], [{SYM_N}, 1], {DTYPE_IR}, {SPACE_ATTR}>"
DYNAMIC_DST = f"!nn.memory<[{SYM_M}, 1], [1, 1], {DTYPE_IR}, {SPACE_ATTR}>"
SYM_M_TYPE = f'!symbol.int<"{SYM_M}">'

CASE_TEXT_STATIC = f"""// COMPILE_ARGS: --pass lower-nn
// CASE: 正例：静态 nn.reduce_max 输入应 lower 为 dma.alloc + kernel.reduce(kind=max) + func.return。
// CHECK: builtin.module {{
// CHECK-NEXT: func.func @reduce_max_kernel(%[[ARG0:{{reg}}]] : {STATIC_SRC}) -> {STATIC_DST} {{
// CHECK-NEXT: %[[V0:{{reg}}]] = "dma.alloc"() <{{operandSegmentSizes = array<i32: 0>}}> : () -> {STATIC_DST}
// CHECK-NEXT: "kernel.reduce"(%[[V0]], %[[ARG0]]) {{axis = 1 : i64, keepdim = true, kind = "max", space = {SPACE_ATTR}}} : ({STATIC_DST}, {STATIC_SRC}) -> ()
// CHECK-NEXT: func.return %[[V0]] : {STATIC_DST}
// CHECK-NEXT: }}
// CHECK-NEXT: }}
// CHECK-NOT: nn.reduce_max

builtin.module {{
  func.func @reduce_max_kernel(%arg0: {STATIC_SRC}) -> {STATIC_DST} {{
    %0 = "nn.reduce_max"(%arg0) {{axes = [#builtin.int<1>], keepdim = #builtin.int<1>, space = {SPACE_ATTR}}} : ({STATIC_SRC}) -> {STATIC_DST}
    func.return %0 : {STATIC_DST}
  }}
}}"""

CASE_TEXT_DYNAMIC = f"""// COMPILE_ARGS: --pass lower-nn
// CASE: 正例：符号维度 nn.reduce_max 输入应 lower 为 dma.alloc + kernel.reduce(kind=max) + func.return。
// CHECK: builtin.module {{
// CHECK-NEXT: func.func @reduce_max_kernel(%[[ARG0:{{reg}}]] : {DYNAMIC_SRC}) -> {DYNAMIC_DST} {{
// CHECK-NEXT: %[[V0:{{reg}}]] = "symbol.get_dim"(%[[ARG0]]) {{axis = #builtin.int<0>}} : ({DYNAMIC_SRC}) -> {SYM_M_TYPE}
// CHECK-NEXT: %[[V1:{{reg}}]] = "dma.alloc"(%[[V0]]) <{{operandSegmentSizes = array<i32: 1>}}> : ({SYM_M_TYPE}) -> {DYNAMIC_DST}
// CHECK-NEXT: "kernel.reduce"(%[[V1]], %[[ARG0]]) {{axis = 1 : i64, keepdim = true, kind = "max", space = {SPACE_ATTR}}} : ({DYNAMIC_DST}, {DYNAMIC_SRC}) -> ()
// CHECK-NEXT: func.return %[[V1]] : {DYNAMIC_DST}
// CHECK-NEXT: }}
// CHECK-NEXT: }}
// CHECK-NOT: nn.reduce_max

builtin.module {{
  func.func @reduce_max_kernel(%arg0: {DYNAMIC_SRC}) -> {DYNAMIC_DST} {{
    %0 = "nn.reduce_max"(%arg0) {{axes = [#builtin.int<1>], keepdim = #builtin.int<1>, space = {SPACE_ATTR}}} : ({DYNAMIC_SRC}) -> {DYNAMIC_DST}
    func.return %0 : {DYNAMIC_DST}
  }}
}}"""


def main() -> None:
    """运行 `reduce_max` ircheck expectation。"""

    run_single("reduce_max", CASE_TEXT_STATIC, CASE_TEXT_DYNAMIC)


if __name__ == "__main__":
    main()
