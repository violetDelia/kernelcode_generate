# [immutable-file]
"""emit_c npu_demo dma expectation：transpose。

创建者: 榕
最后一次更改: 榕

功能说明:
- 为 `dma.transpose` 提供单独的 `emit_c` expectation。
- 锁定目标源码 helper 形态为
  `transpose<TargetSpace, SourceSpace, TargetType, SourceType>(ctx, arg0, source, {1, 0});`。
- 同时覆盖静态与动态 symbol-shape 两条路径。

使用示例:
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python expectation/dsl/emit_c/npu_demo/dma/transpose.py`

关联文件:
- spec: [`spec/dsl/emit_c.md`](spec/dsl/emit_c.md)
- spec: [`spec/tools/ircheck.md`](spec/tools/ircheck.md)
- spec: [`spec/include/api/Dma.md`](spec/include/api/Dma.md)
- test: [`test/dsl/test_emit_c.py`](test/dsl/test_emit_c.py)
- 功能实现: [`kernel_gen/tools/ircheck.py`](kernel_gen/tools/ircheck.py)
- 功能实现: [`expectation/dsl/emit_c/npu_demo/dma/transpose.py`](expectation/dsl/emit_c/npu_demo/dma/transpose.py)
"""

# Case 列表:
# - emit_c-npu_demo-dma-transpose-static: 静态 shape 的 `dma.transpose` 应生成 `transpose<TargetSpace, SourceSpace, TargetType, SourceType>(ctx, dst, source, {1, 0});`。
# - emit_c-npu_demo-dma-transpose-dynamic: 动态 shape 的 `dma.transpose` 也应生成同口径 helper 调用。

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


def _transpose_types_and_spaces():
    target_space, source_space = random_memory_spaces(2, unique=False)
    target_dtype, source_dtype = get_random_arithmetic_numeric_types(
        2,
        exclude=(NumericType.Float16, NumericType.BFloat16),
        unique=False,
    )
    return target_space, source_space, target_dtype, source_dtype


def _case_dma_transpose_static() -> None:
    """运行静态 `dma.transpose` expectation。"""

    static_m, static_n = random_static_dims(2, min_value=2, max_value=8)
    target_space, source_space, target_dtype, source_dtype = _transpose_types_and_spaces()
    target_space_cpp = cpp_space_name(target_space)
    source_space_cpp = cpp_space_name(source_space)
    target_space_ir = memory_space_ir_name(target_space)
    source_space_ir = memory_space_ir_name(source_space)
    target_dtype_cpp = cpp_numeric_type_name(target_dtype)
    source_dtype_cpp = cpp_numeric_type_name(source_dtype)
    target_dtype_ir = numeric_type_ir(target_dtype)
    source_dtype_ir = numeric_type_ir(source_dtype)
    transpose_src = f"!nn.memory<[#C_M, #C_N], [#C_N, #C1], {source_dtype_ir}, #nn.space<{source_space_ir}>>"
    transpose_dst = f"!nn.memory<[#C_N, #C_M], [#C_M, #C1], {target_dtype_ir}, #nn.space<{target_space_ir}>>"
    alias_defs = f"""#C_M = #symbol.expr<{static_m}>
#C_N = #symbol.expr<{static_n}>
#C1 = #symbol.expr<1>
"""
    case_text = f"""// COMPILE_ARGS: --pass no-op
// CHECK: template <typename Context>
// CHECK: void dma_transpose_case(Context& ctx, Memory<{target_space_cpp}, {target_dtype_cpp}>& [[DST:{{val}}]], Memory<{source_space_cpp}, {source_dtype_cpp}>& [[SRC:{{val}}]]) {{
// CHECK-NEXT:     transpose<{target_space_cpp}, {source_space_cpp}, {target_dtype_cpp}, {source_dtype_cpp}>(ctx, [[DST]] /*dst*/, [[SRC]] /*source*/, {{1, 0}} /*perm*/);
// CHECK-NEXT: }}

{alias_defs}
builtin.module {{
  func.func @dma_transpose_case(
    %ctx : index {{name = "ctx"}},
    %0 : {transpose_dst},
    %1 : {transpose_src}
  ) {{
    "dma.transpose"(%0, %1) {{perm = [1 : i64, 0 : i64]}} : ({transpose_dst}, {transpose_src}) -> ()
    func.return
  }}
}}"""


    print_case_input_ir(
        "emit_c-npu_demo-dma-transpose-static",
        case_text,
        fallback="emit_c-npu_demo-dma-transpose-static",
    )
    run_emitc_case(
        case_text,
        source_path="expectation/dsl/emit_c/npu_demo/dma/transpose.py",
        op_name="dma.transpose",
        expected_snippets=[
            "template <typename Context>\nvoid dma_transpose_case(Context& ctx,",
            f"transpose<{target_space_cpp}, {source_space_cpp}, {target_dtype_cpp}, {source_dtype_cpp}>(ctx,",
            "{",
        ],
        forbidden_snippets=["dma.transpose", "Vector(", "static_cast<long long>"],
    )


def _case_dma_transpose_dynamic() -> None:
    """运行动态 `dma.transpose` expectation。"""

    sym_m, sym_n = random_symbol_names(2)
    target_space, source_space, target_dtype, source_dtype = _transpose_types_and_spaces()
    target_space_cpp = cpp_space_name(target_space)
    source_space_cpp = cpp_space_name(source_space)
    target_space_ir = memory_space_ir_name(target_space)
    source_space_ir = memory_space_ir_name(source_space)
    target_dtype_cpp = cpp_numeric_type_name(target_dtype)
    source_dtype_cpp = cpp_numeric_type_name(source_dtype)
    target_dtype_ir = numeric_type_ir(target_dtype)
    source_dtype_ir = numeric_type_ir(source_dtype)
    transpose_src_dynamic = f"!nn.memory<[#S_M, #S_N], [#S_N, #C1], {source_dtype_ir}, #nn.space<{source_space_ir}>>"
    transpose_dst_dynamic = f"!nn.memory<[#S_N, #S_M], [#S_M, #C1], {target_dtype_ir}, #nn.space<{target_space_ir}>>"
    alias_defs = f"""#S_M = #symbol.expr<{sym_m}>
#S_N = #symbol.expr<{sym_n}>
#C1 = #symbol.expr<1>
"""
    case_text = f"""// COMPILE_ARGS: --pass no-op
// CHECK: template <typename Context>
// CHECK: void dma_transpose_dynamic_case(Context& ctx, Memory<{target_space_cpp}, {target_dtype_cpp}>& [[DST:{{val}}]], Memory<{source_space_cpp}, {source_dtype_cpp}>& [[SRC:{{val}}]]) {{
// CHECK-NEXT:     transpose<{target_space_cpp}, {source_space_cpp}, {target_dtype_cpp}, {source_dtype_cpp}>(ctx, [[DST]] /*dst*/, [[SRC]] /*source*/, {{1, 0}} /*perm*/);
// CHECK-NEXT: }}

{alias_defs}
builtin.module {{
  func.func @dma_transpose_dynamic_case(
    %ctx : index {{name = "ctx"}},
    %0 : {transpose_dst_dynamic},
    %1 : {transpose_src_dynamic}
  ) {{
    "dma.transpose"(%0, %1) {{perm = [1 : i64, 0 : i64]}} : ({transpose_dst_dynamic}, {transpose_src_dynamic}) -> ()
    func.return
  }}
}}"""


    print_case_input_ir(
        "emit_c-npu_demo-dma-transpose-dynamic",
        case_text,
        fallback="emit_c-npu_demo-dma-transpose-dynamic",
    )
    run_emitc_case(
        case_text,
        source_path="expectation/dsl/emit_c/npu_demo/dma/transpose.py#dynamic",
        op_name="dma.transpose.dynamic",
        expected_snippets=[
            "template <typename Context>\nvoid dma_transpose_dynamic_case(Context& ctx,",
            f"transpose<{target_space_cpp}, {source_space_cpp}, {target_dtype_cpp}, {source_dtype_cpp}>(ctx,",
            "{",
        ],
        forbidden_snippets=["dma.transpose", "Vector(", "static_cast<long long>"],
    )


def main() -> None:
    """运行 `dma.transpose` 的 emit_c expectation。"""

    failures: list[tuple[str, BaseException]] = []
    run_case(
        failures,
        "emit_c-npu_demo-dma-transpose-static",
        _case_dma_transpose_static,
    )
    run_case(
        failures,
        "emit_c-npu_demo-dma-transpose-dynamic",
        _case_dma_transpose_dynamic,
    )
    raise_if_failures("emit_c npu_demo dma transpose expectation", failures)


if __name__ == "__main__":
    main()
