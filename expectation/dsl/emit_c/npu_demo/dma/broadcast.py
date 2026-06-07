# [immutable-file]
"""emit_c npu_demo dma expectation：broadcast。

创建者: 榕
最后一次更改: 榕

功能说明:
- 为 `dma.broadcast` 提供单独的 `emit_c` expectation。
- 锁定目标源码 helper 形态为
  `broadcast<DstSpace, SrcSpace, DstType, SrcType>(ctx, dst, source);`。
- 同时覆盖静态与动态 symbol-shape 两条路径。

使用示例:
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python expectation/dsl/emit_c/npu_demo/dma/broadcast.py`

关联文件:
- spec: [`spec/dsl/emit_c.md`](spec/dsl/emit_c.md)
- spec: [`spec/tools/ircheck.md`](spec/tools/ircheck.md)
- spec: [`spec/include/api/Dma.md`](spec/include/api/Dma.md)
- test: [`test/dsl/test_emit_c.py`](test/dsl/test_emit_c.py)
- 功能实现: [`kernel_gen/tools/ircheck.py`](kernel_gen/tools/ircheck.py)
- 功能实现: [`expectation/dsl/emit_c/npu_demo/dma/broadcast.py`](expectation/dsl/emit_c/npu_demo/dma/broadcast.py)
"""

# Case 列表:
# - emit_c-npu_demo-dma-broadcast-static: 静态 shape 的 `dma.broadcast` 应生成 `broadcast<DstSpace, SrcSpace, DstType, SrcType>(ctx, dst, source);`。
# - emit_c-npu_demo-dma-broadcast-dynamic: 动态 shape 的 `dma.broadcast` 也应生成同口径 helper 调用。

from __future__ import annotations

from pathlib import Path
import sys

REPO_ROOT = next(parent for parent in Path(__file__).resolve().parents if (parent / "kernel_gen").exists())
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from expectation.utils.emitc import COMMON_MEMORY_SPACES, cpp_numeric_type_name, cpp_space_name
from kernel_gen.tools.emitc_case_runner import run_emitc_case
from expectation.utils.case_runner import print_case_input_ir, raise_if_failures, run_case
from expectation.utils.random_utils import memory_space_ir_name, numeric_type_ir, random_memory_spaces, random_static_dims, random_symbol_names
from expectation.utils.random import get_random_arithmetic_numeric_types
from kernel_gen.symbol_variable.type import NumericType


def _broadcast_types_and_spaces():
    dst_space, src_space = random_memory_spaces(2, unique=False)
    dst_dtype, src_dtype = get_random_arithmetic_numeric_types(
        2,
        exclude=(NumericType.Float16, NumericType.BFloat16),
        unique=False,
    )
    return dst_space, src_space, dst_dtype, src_dtype


def _case_dma_broadcast_static() -> None:
    """运行静态 `dma.broadcast` expectation。"""

    static_m, static_n = random_static_dims(2, min_value=2, max_value=8)
    dst_space, src_space, dst_dtype, src_dtype = _broadcast_types_and_spaces()
    dst_space_cpp = cpp_space_name(dst_space)
    src_space_cpp = cpp_space_name(src_space)
    dst_space_ir = memory_space_ir_name(dst_space)
    src_space_ir = memory_space_ir_name(src_space)
    dst_dtype_cpp = cpp_numeric_type_name(dst_dtype)
    src_dtype_cpp = cpp_numeric_type_name(src_dtype)
    dst_dtype_ir = numeric_type_ir(dst_dtype)
    src_dtype_ir = numeric_type_ir(src_dtype)
    broadcast_src = f"!nn.memory<[#C1, #C_N], [#C_N, #C1], {src_dtype_ir}, #nn.space<{src_space_ir}>>"
    broadcast_dst = f"!nn.memory<[#C_M, #C_N], [#C_N, #C1], {dst_dtype_ir}, #nn.space<{dst_space_ir}>>"
    alias_defs = f"""#C_M = #symbol.expr<{static_m}>
#C_N = #symbol.expr<{static_n}>
#C1 = #symbol.expr<1>
"""
    case_text = f"""// COMPILE_ARGS: --pass no-op
// CHECK: template <typename Context>
// CHECK: void dma_broadcast_case(Context& ctx, Memory<{dst_space_cpp}, {dst_dtype_cpp}>& [[DST:{{val}}]], Memory<{src_space_cpp}, {src_dtype_cpp}>& [[SRC:{{val}}]]) {{
// CHECK-NEXT:     broadcast<{dst_space_cpp}, {src_space_cpp}, {dst_dtype_cpp}, {src_dtype_cpp}>(ctx, [[DST]] /*dst*/, [[SRC]] /*source*/);
// CHECK-NEXT: }}

{alias_defs}
builtin.module {{
  func.func @dma_broadcast_case(
    %ctx : index {{name = "ctx"}},
    %0 : {broadcast_dst},
    %1 : {broadcast_src}
  ) {{
    "dma.broadcast"(%0, %1) : ({broadcast_dst}, {broadcast_src}) -> ()
    func.return
  }}
}}"""


    print_case_input_ir(
        "emit_c-npu_demo-dma-broadcast-static",
        case_text,
        fallback="emit_c-npu_demo-dma-broadcast-static",
    )
    run_emitc_case(
        case_text,
        source_path="expectation/dsl/emit_c/npu_demo/dma/broadcast.py",
        op_name="dma.broadcast",
        expected_snippets=[
            "template <typename Context>\nvoid dma_broadcast_case(Context& ctx,",
            f"broadcast<{dst_space_cpp}, {src_space_cpp}, {dst_dtype_cpp}, {src_dtype_cpp}>(ctx,",
        ],
        forbidden_snippets=["dma.broadcast"],
    )


def _case_dma_broadcast_dynamic() -> None:
    """运行动态 `dma.broadcast` expectation。"""

    sym_m, sym_n = random_symbol_names(2)
    dst_space, src_space, dst_dtype, src_dtype = _broadcast_types_and_spaces()
    dst_space_cpp = cpp_space_name(dst_space)
    src_space_cpp = cpp_space_name(src_space)
    dst_space_ir = memory_space_ir_name(dst_space)
    src_space_ir = memory_space_ir_name(src_space)
    dst_dtype_cpp = cpp_numeric_type_name(dst_dtype)
    src_dtype_cpp = cpp_numeric_type_name(src_dtype)
    dst_dtype_ir = numeric_type_ir(dst_dtype)
    src_dtype_ir = numeric_type_ir(src_dtype)
    broadcast_src_dynamic = f"!nn.memory<[#C1, #S_N], [#S_N, #C1], {src_dtype_ir}, #nn.space<{src_space_ir}>>"
    broadcast_dst_dynamic = f"!nn.memory<[#S_M, #S_N], [#S_N, #C1], {dst_dtype_ir}, #nn.space<{dst_space_ir}>>"
    alias_defs = f"""#S_M = #symbol.expr<{sym_m}>
#S_N = #symbol.expr<{sym_n}>
#C1 = #symbol.expr<1>
"""
    case_text = f"""// COMPILE_ARGS: --pass no-op
// CHECK: template <typename Context>
// CHECK: void dma_broadcast_dynamic_case(Context& ctx, Memory<{dst_space_cpp}, {dst_dtype_cpp}>& [[DST:{{val}}]], Memory<{src_space_cpp}, {src_dtype_cpp}>& [[SRC:{{val}}]]) {{
// CHECK-NEXT:     broadcast<{dst_space_cpp}, {src_space_cpp}, {dst_dtype_cpp}, {src_dtype_cpp}>(ctx, [[DST]] /*dst*/, [[SRC]] /*source*/);
// CHECK-NEXT: }}

{alias_defs}
builtin.module {{
  func.func @dma_broadcast_dynamic_case(
    %ctx : index {{name = "ctx"}},
    %0 : {broadcast_dst_dynamic},
    %1 : {broadcast_src_dynamic}
  ) {{
    "dma.broadcast"(%0, %1) : ({broadcast_dst_dynamic}, {broadcast_src_dynamic}) -> ()
    func.return
  }}
}}"""


    print_case_input_ir(
        "emit_c-npu_demo-dma-broadcast-dynamic",
        case_text,
        fallback="emit_c-npu_demo-dma-broadcast-dynamic",
    )
    run_emitc_case(
        case_text,
        source_path="expectation/dsl/emit_c/npu_demo/dma/broadcast.py#dynamic",
        op_name="dma.broadcast.dynamic",
        expected_snippets=[
            "template <typename Context>\nvoid dma_broadcast_dynamic_case(Context& ctx,",
            f"broadcast<{dst_space_cpp}, {src_space_cpp}, {dst_dtype_cpp}, {src_dtype_cpp}>(ctx,",
        ],
        forbidden_snippets=["dma.broadcast"],
    )


def main() -> None:
    """运行 `dma.broadcast` 的 emit_c expectation。"""

    failures: list[tuple[str, BaseException]] = []
    run_case(
        failures,
        "emit_c-npu_demo-dma-broadcast-static",
        _case_dma_broadcast_static,
    )
    run_case(
        failures,
        "emit_c-npu_demo-dma-broadcast-dynamic",
        _case_dma_broadcast_dynamic,
    )
    raise_if_failures("emit_c npu_demo dma broadcast expectation", failures)


if __name__ == "__main__":
    main()
