# [immutable-file]
"""emit_c npu_demo kernel expectation：select。

创建者: 榕
最后一次更改: 榕

功能说明:
- 覆盖 `kernel.select` 的 `emit_c` expectation。
- 锁定目标源码为 context-first、out-first 的 `select<...>(ctx, arg0, cond, lhs, rhs);`。

使用示例:
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python expectation/dsl/emit_c/npu_demo/kernel/select.py`

关联文件:
- spec: [`spec/dsl/emit_c.md`](spec/dsl/emit_c.md)
- spec: [`spec/tools/ircheck.md`](spec/tools/ircheck.md)
- spec: [`spec/include/api/Kernel.md`](spec/include/api/Kernel.md)
- test: [`test/dsl/test_emit_c.py`](test/dsl/test_emit_c.py)
- 功能实现: [`kernel_gen/tools/ircheck.py`](kernel_gen/tools/ircheck.py)
- 功能实现: [`expectation/dsl/emit_c/npu_demo/kernel/select.py`](expectation/dsl/emit_c/npu_demo/kernel/select.py)
"""

# Case 列表:
# - emit_c-npu_demo-kernel-select-static: 静态 shape 的 `kernel.select` 应生成 `select<...>(ctx, out, cond, lhs, rhs);`。
# - emit_c-npu_demo-kernel-select-dynamic: 动态 shape 的 `kernel.select` 也应生成同口径 helper 调用。
from __future__ import annotations

from pathlib import Path
import sys

REPO_ROOT = next(parent for parent in Path(__file__).resolve().parents if (parent / "kernel_gen").exists())
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from expectation.utils.emitc import cpp_numeric_type_name, cpp_space_name
from kernel_gen.tools.emitc_case_runner import run_emitc_case
from expectation.utils.case_runner import print_case_input_ir, raise_if_failures, run_case
from expectation.utils.random_utils import memory_space_ir_name, numeric_type_ir, random_memory_spaces, random_static_dims, random_symbol_names
from expectation.utils.random import get_random_arithmetic_numeric_types
from kernel_gen.symbol_variable.type import NumericType


def _build_case_kernel_select_static() -> tuple[str, str]:
    """构造静态 `kernel.select` expectation IR。"""
    static_m, static_n = random_static_dims(2)
    space = random_memory_spaces(1, unique=False)[0]
    space_ir = memory_space_ir_name(space)
    space_cpp = cpp_space_name(space)
    data_dtype = get_random_arithmetic_numeric_types(
        1,
        exclude=(NumericType.Float16, NumericType.BFloat16),
        unique=False,
    )[0]
    data_dtype_ir = numeric_type_ir(data_dtype)
    data_dtype_cpp = cpp_numeric_type_name(data_dtype)
    data_mem_type = f"!nn.memory<[#C_M, #C_N], [#C_N, #C1], {data_dtype_ir}, #nn.space<{space_ir}>>"
    cond_mem_type = f"!nn.memory<[#C_M, #C_N], [#C_N, #C1], i1, #nn.space<{space_ir}>>"
    alias_defs = f"""#C_M = #symbol.expr<{static_m}>
#C_N = #symbol.expr<{static_n}>
#C1 = #symbol.expr<1>
"""
    case_text = f"""// COMPILE_ARGS: --pass no-op
// CASE: kernel.select 应生成 out-first 的 select 调用。
// CHECK: template <typename Context>
// CHECK: void kernel_select_case(Context& ctx, Memory<{space_cpp}, {data_dtype_cpp}>& [[OUT:{{val}}]], Memory<{space_cpp}, bool>& [[COND:{{val}}]], Memory<{space_cpp}, {data_dtype_cpp}>& [[LHS:{{val}}]], Memory<{space_cpp}, {data_dtype_cpp}>& [[RHS:{{val}}]]) {{
// CHECK-NEXT:     select<{space_cpp}, {data_dtype_cpp}, {data_dtype_cpp}>(ctx, [[OUT]] /*out*/, [[COND]] /*cond*/, [[LHS]] /*lhs*/, [[RHS]] /*rhs*/);
// CHECK-NEXT: }}

{alias_defs}
builtin.module {{
  func.func @kernel_select_case(
    %ctx : index {{name = "ctx"}},
    %0 : {data_mem_type},
    %1 : {cond_mem_type},
    %2 : {data_mem_type},
    %3 : {data_mem_type}
  ) {{
    "kernel.select"(%1, %2, %3, %0) {{space = #nn.space<{space_ir}>}} : ({cond_mem_type}, {data_mem_type}, {data_mem_type}, {data_mem_type}) -> ()
    func.return
  }}
}}"""
    return case_text, f"select<{space_cpp}, {data_dtype_cpp}, {data_dtype_cpp}>(ctx,"


def _case_kernel_select_static() -> None:
    """运行静态 `kernel.select` expectation。"""

    case_text, expected_call_snippet = _build_case_kernel_select_static()
    print_case_input_ir(
        "emit_c-npu_demo-kernel-select-static",
        case_text,
        fallback="静态 shape 的 kernel.select 应生成 out-first select helper 调用。",
    )

    run_emitc_case(
        case_text,
        source_path="expectation/dsl/emit_c/npu_demo/kernel/select.py",
        op_name="kernel.select",
        expected_snippets=[
            "template <typename Context>\nvoid kernel_select_case(Context& ctx,",
            expected_call_snippet,
        ],
        forbidden_snippets=["kernel.select"],
    )


def _build_case_kernel_select_dynamic() -> tuple[str, str]:
    """构造动态 `kernel.select` expectation IR。"""
    sym_m, sym_n = random_symbol_names(2)
    space = random_memory_spaces(1, unique=False)[0]
    space_ir = memory_space_ir_name(space)
    space_cpp = cpp_space_name(space)
    data_dtype = get_random_arithmetic_numeric_types(
        1,
        exclude=(NumericType.Float16, NumericType.BFloat16),
        unique=False,
    )[0]
    data_dtype_ir = numeric_type_ir(data_dtype)
    data_dtype_cpp = cpp_numeric_type_name(data_dtype)
    dynamic_data_mem_type = f"!nn.memory<[#S_M, #S_N], [#S_N, #C1], {data_dtype_ir}, #nn.space<{space_ir}>>"
    dynamic_cond_mem_type = f"!nn.memory<[#S_M, #S_N], [#S_N, #C1], i1, #nn.space<{space_ir}>>"
    alias_defs = f"""#S_M = #symbol.expr<{sym_m}>
#S_N = #symbol.expr<{sym_n}>
#C1 = #symbol.expr<1>
"""
    case_text = f"""// COMPILE_ARGS: --pass no-op
// CASE: kernel.select 的动态 shape 版本也应生成 out-first 的 select 调用。
// CHECK: template <typename Context>
// CHECK: void kernel_select_dynamic_case(Context& ctx, Memory<{space_cpp}, {data_dtype_cpp}>& [[OUT:{{val}}]], Memory<{space_cpp}, bool>& [[COND:{{val}}]], Memory<{space_cpp}, {data_dtype_cpp}>& [[LHS:{{val}}]], Memory<{space_cpp}, {data_dtype_cpp}>& [[RHS:{{val}}]]) {{
// CHECK-NEXT:     select<{space_cpp}, {data_dtype_cpp}, {data_dtype_cpp}>(ctx, [[OUT]] /*out*/, [[COND]] /*cond*/, [[LHS]] /*lhs*/, [[RHS]] /*rhs*/);
// CHECK-NEXT: }}

{alias_defs}
builtin.module {{
  func.func @kernel_select_dynamic_case(
    %ctx : index {{name = "ctx"}},
    %0 : {dynamic_data_mem_type},
    %1 : {dynamic_cond_mem_type},
    %2 : {dynamic_data_mem_type},
    %3 : {dynamic_data_mem_type}
  ) {{
    "kernel.select"(%1, %2, %3, %0) {{space = #nn.space<{space_ir}>}} : ({dynamic_cond_mem_type}, {dynamic_data_mem_type}, {dynamic_data_mem_type}, {dynamic_data_mem_type}) -> ()
    func.return
  }}
}}"""
    return case_text, f"select<{space_cpp}, {data_dtype_cpp}, {data_dtype_cpp}>(ctx,"


def _case_kernel_select_dynamic() -> None:
    """运行动态 `kernel.select` expectation。"""

    case_text, expected_call_snippet = _build_case_kernel_select_dynamic()
    print_case_input_ir(
        "emit_c-npu_demo-kernel-select-dynamic",
        case_text,
        fallback="动态 shape 的 kernel.select 也应生成 out-first select helper 调用。",
    )

    run_emitc_case(
        case_text,
        source_path="expectation/dsl/emit_c/npu_demo/kernel/select.py#dynamic",
        op_name="kernel.select.dynamic",
        expected_snippets=[
            "template <typename Context>\nvoid kernel_select_dynamic_case(Context& ctx,",
            expected_call_snippet,
        ],
        forbidden_snippets=["kernel.select"],
    )


def main() -> None:
    """运行 `kernel.select` 的 emit_c expectation。"""

    failures: list[tuple[str, BaseException]] = []
    run_case(
        failures,
        "emit_c-npu_demo-kernel-select-static",
        _case_kernel_select_static,
    )
    run_case(
        failures,
        "emit_c-npu_demo-kernel-select-dynamic",
        _case_kernel_select_dynamic,
    )
    raise_if_failures("emit_c npu_demo kernel select expectation", failures)


if __name__ == "__main__":
    main()
