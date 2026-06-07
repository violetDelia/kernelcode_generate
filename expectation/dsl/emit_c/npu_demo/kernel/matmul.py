# [immutable-file]
"""emit_c npu_demo kernel expectation：matmul。

创建者: 榕
最后一次更改: 榕

功能说明:
- 使用 `ircheck emitc_target="npu_demo"` 运行 `kernel.matmul` 的源码 expectation。
- 验证 `kernel.matmul` 经 `ircheck --emit` 后，应生成包含显式模板参数且 context-first / out-first
  的 `matmul<...>(ctx, out, lhs, rhs);` 完整 C++ 源码。
- 该 expectation 按规范随机化输出、input、weight 的 dtype/space，允许三者不同，不迁就当前实现。

使用示例:
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python expectation/dsl/emit_c/npu_demo/kernel/matmul.py`

关联文件:
- spec: [`spec/dsl/emit_c.md`](spec/dsl/emit_c.md)
- spec: [`spec/tools/ircheck.md`](spec/tools/ircheck.md)
- spec: [`spec/include/api/Kernel.md`](spec/include/api/Kernel.md)
- 功能实现: [`kernel_gen/tools/ircheck.py`](kernel_gen/tools/ircheck.py)
- 功能实现: [`expectation/dsl/emit_c/npu_demo/kernel/matmul.py`](expectation/dsl/emit_c/npu_demo/kernel/matmul.py)
"""

# Case 列表:
# - emit_c-npu_demo-kernel-matmul-static: 静态 shape 的 `kernel.matmul` 应生成完整模板参数的 `matmul<...>(ctx, out, lhs, rhs)`。
# - emit_c-npu_demo-kernel-matmul-dynamic: 动态 shape 的 `kernel.matmul` 也应生成相同 helper 调用。

from __future__ import annotations

from pathlib import Path
import sys

REPO_ROOT = next(parent for parent in Path(__file__).resolve().parents if (parent / "kernel_gen").exists())
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from expectation.utils.case_runner import print_case_input_ir, raise_if_failures, run_case
from expectation.utils.random_utils import (
    memory_space_ir_name,
    numeric_type_ir,
    random_memory_spaces,
    random_static_dims,
    random_symbol_names,
)
from expectation.utils.random import get_random_arithmetic_numeric_types
from kernel_gen.symbol_variable.memory import MemorySpace
from kernel_gen.symbol_variable.type import NumericType
from kernel_gen.tools.emitc_case_runner import run_emitc_case


def _space_enum_name(space: MemorySpace) -> str:
    from expectation.utils.emitc import cpp_space_name

    return cpp_space_name(space)


def _cpp_type_name(dtype: NumericType) -> str:
    from expectation.utils.emitc import cpp_numeric_type_name

    return cpp_numeric_type_name(dtype)


def _random_dtypes() -> tuple[NumericType, NumericType, NumericType]:
    return get_random_arithmetic_numeric_types(
        3,
        exclude=(NumericType.Float16, NumericType.BFloat16),
        unique=False,
    )


def _build_case_kernel_matmul_static() -> tuple[str, str]:
    """构造静态 `kernel.matmul` expectation IR。"""
    static_m, static_k, static_n = random_static_dims(3)
    lhs_dtype, rhs_dtype, output_dtype = _random_dtypes()
    lhs_space, rhs_space, output_space = random_memory_spaces(3, unique=False)
    lhs_dtype_ir = numeric_type_ir(lhs_dtype)
    rhs_dtype_ir = numeric_type_ir(rhs_dtype)
    output_dtype_ir = numeric_type_ir(output_dtype)
    output_space_ir = memory_space_ir_name(output_space)
    lhs_static = f"!nn.memory<[#C_M, #C_K], [#C_K, #C1], {lhs_dtype_ir}, #nn.space<{memory_space_ir_name(lhs_space)}>>"
    rhs_static = f"!nn.memory<[#C_K, #C_N], [#C_N, #C1], {rhs_dtype_ir}, #nn.space<{memory_space_ir_name(rhs_space)}>>"
    out_static = f"!nn.memory<[#C_M, #C_N], [#C_N, #C1], {output_dtype_ir}, #nn.space<{output_space_ir}>>"
    lhs_space_cpp = _space_enum_name(lhs_space)
    rhs_space_cpp = _space_enum_name(rhs_space)
    output_space_cpp = _space_enum_name(output_space)
    lhs_dtype_cpp = _cpp_type_name(lhs_dtype)
    rhs_dtype_cpp = _cpp_type_name(rhs_dtype)
    output_dtype_cpp = _cpp_type_name(output_dtype)
    alias_defs = f"""#C_M = #symbol.expr<{static_m}>
#C_K = #symbol.expr<{static_k}>
#C_N = #symbol.expr<{static_n}>
#C1 = #symbol.expr<1>
"""
    case_text = f"""// COMPILE_ARGS: --pass no-op
// CHECK: template <typename Context>
// CHECK: void kernel_matmul_case(Context& ctx, Memory<{output_space_cpp}, {output_dtype_cpp}>& [[OUT:{{val}}]], Memory<{lhs_space_cpp}, {lhs_dtype_cpp}>& [[LHS:{{val}}]], Memory<{rhs_space_cpp}, {rhs_dtype_cpp}>& [[RHS:{{val}}]]) {{
// CHECK-NEXT:     matmul<{lhs_space_cpp}, {rhs_space_cpp}, {output_space_cpp}, {lhs_dtype_cpp}, {rhs_dtype_cpp}, {output_dtype_cpp}>(ctx, [[OUT]] /*out*/, [[LHS]] /*lhs*/, [[RHS]] /*rhs*/);
// CHECK-NEXT: }}

{alias_defs}
builtin.module {{
  func.func @kernel_matmul_case(
    %ctx : index {{name = "ctx"}},
    %0 : {out_static},
    %1 : {lhs_static},
    %2 : {rhs_static}
  ) {{
    "kernel.matmul"(%1, %2, %0) {{space = #nn.space<{output_space_ir}>}} : ({lhs_static}, {rhs_static}, {out_static}) -> ()
    func.return
  }}
}}"""
    return case_text, f"matmul<{lhs_space_cpp}, {rhs_space_cpp}, {output_space_cpp}, {lhs_dtype_cpp}, {rhs_dtype_cpp}, {output_dtype_cpp}>(ctx,"


def _case_kernel_matmul_static() -> None:
    """运行静态 `kernel.matmul` expectation。"""

    case_text, expected_snippet = _build_case_kernel_matmul_static()
    print_case_input_ir(
        "emit_c-npu_demo-kernel-matmul-static",
        case_text,
        fallback="静态 shape 的 kernel.matmul 应生成完整模板参数的 matmul helper 调用。",
    )

    run_emitc_case(
        case_text,
        source_path="expectation/dsl/emit_c/npu_demo/kernel/matmul.py#static",
        op_name="kernel.matmul",
        expected_snippets=[
            "template <typename Context>\nvoid kernel_matmul_case(Context& ctx,",
            expected_snippet,
        ],
        forbidden_snippets=["kernel.matmul"],
    )


def _build_case_kernel_matmul_dynamic() -> tuple[str, str]:
    """构造动态 `kernel.matmul` expectation IR。"""
    sym_m, sym_k, sym_n = random_symbol_names(3)
    lhs_dtype, rhs_dtype, output_dtype = _random_dtypes()
    lhs_space, rhs_space, output_space = random_memory_spaces(3, unique=False)
    lhs_dtype_ir = numeric_type_ir(lhs_dtype)
    rhs_dtype_ir = numeric_type_ir(rhs_dtype)
    output_dtype_ir = numeric_type_ir(output_dtype)
    output_space_ir = memory_space_ir_name(output_space)
    lhs_dynamic = f"!nn.memory<[#S_M, #S_K], [#S_K, #C1], {lhs_dtype_ir}, #nn.space<{memory_space_ir_name(lhs_space)}>>"
    rhs_dynamic = f"!nn.memory<[#S_K, #S_N], [#S_N, #C1], {rhs_dtype_ir}, #nn.space<{memory_space_ir_name(rhs_space)}>>"
    out_dynamic = f"!nn.memory<[#S_M, #S_N], [#S_N, #C1], {output_dtype_ir}, #nn.space<{output_space_ir}>>"
    lhs_space_cpp = _space_enum_name(lhs_space)
    rhs_space_cpp = _space_enum_name(rhs_space)
    output_space_cpp = _space_enum_name(output_space)
    lhs_dtype_cpp = _cpp_type_name(lhs_dtype)
    rhs_dtype_cpp = _cpp_type_name(rhs_dtype)
    output_dtype_cpp = _cpp_type_name(output_dtype)
    alias_defs = f"""#S_M = #symbol.expr<{sym_m}>
#S_K = #symbol.expr<{sym_k}>
#S_N = #symbol.expr<{sym_n}>
#C1 = #symbol.expr<1>
"""
    case_text = f"""// COMPILE_ARGS: --pass no-op
// CHECK: template <typename Context>
// CHECK: void kernel_matmul_dynamic_case(Context& ctx, Memory<{output_space_cpp}, {output_dtype_cpp}>& [[OUT:{{val}}]], Memory<{lhs_space_cpp}, {lhs_dtype_cpp}>& [[LHS:{{val}}]], Memory<{rhs_space_cpp}, {rhs_dtype_cpp}>& [[RHS:{{val}}]]) {{
// CHECK-NEXT:     matmul<{lhs_space_cpp}, {rhs_space_cpp}, {output_space_cpp}, {lhs_dtype_cpp}, {rhs_dtype_cpp}, {output_dtype_cpp}>(ctx, [[OUT]] /*out*/, [[LHS]] /*lhs*/, [[RHS]] /*rhs*/);
// CHECK-NEXT: }}

{alias_defs}
builtin.module {{
  func.func @kernel_matmul_dynamic_case(
    %ctx : index {{name = "ctx"}},
    %0 : {out_dynamic},
    %1 : {lhs_dynamic},
    %2 : {rhs_dynamic}
  ) {{
    "kernel.matmul"(%1, %2, %0) {{space = #nn.space<{output_space_ir}>}} : ({lhs_dynamic}, {rhs_dynamic}, {out_dynamic}) -> ()
    func.return
  }}
}}"""
    return case_text, f"matmul<{lhs_space_cpp}, {rhs_space_cpp}, {output_space_cpp}, {lhs_dtype_cpp}, {rhs_dtype_cpp}, {output_dtype_cpp}>(ctx,"


def _case_kernel_matmul_dynamic() -> None:
    """运行动态 `kernel.matmul` expectation。"""

    case_text, expected_snippet = _build_case_kernel_matmul_dynamic()
    print_case_input_ir(
        "emit_c-npu_demo-kernel-matmul-dynamic",
        case_text,
        fallback="动态 shape 的 kernel.matmul 也应生成完整模板参数的 matmul helper 调用。",
    )

    run_emitc_case(
        case_text,
        source_path="expectation/dsl/emit_c/npu_demo/kernel/matmul.py#dynamic",
        op_name="kernel.matmul.dynamic",
        expected_snippets=[
            "template <typename Context>\nvoid kernel_matmul_dynamic_case(Context& ctx,",
            expected_snippet,
        ],
        forbidden_snippets=["kernel.matmul"],
    )


def main() -> None:
    failures: list[tuple[str, BaseException]] = []
    run_case(failures, "emit_c-npu_demo-kernel-matmul-static", _case_kernel_matmul_static)
    run_case(failures, "emit_c-npu_demo-kernel-matmul-dynamic", _case_kernel_matmul_dynamic)
    raise_if_failures("emit_c npu_demo kernel matmul expectation", failures)


if __name__ == "__main__":
    main()
