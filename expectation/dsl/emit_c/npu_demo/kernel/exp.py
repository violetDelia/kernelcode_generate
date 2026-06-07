# [immutable-file]
"""emit_c npu_demo kernel expectation：exp。

创建者: 榕
最后一次更改: 榕

功能说明:
- 覆盖 `kernel.exp` 的 `emit_c` expectation。
- 锁定目标源码为 context-first、out-first 的 `exp<...>(ctx, arg0, input);`。

使用示例:
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python expectation/dsl/emit_c/npu_demo/kernel/exp.py`

关联文件:
- spec: [`spec/dsl/emit_c.md`](spec/dsl/emit_c.md)
- spec: [`spec/tools/ircheck.md`](spec/tools/ircheck.md)
- spec: [`spec/include/api/Kernel.md`](spec/include/api/Kernel.md)
- test: [`test/dsl/test_emit_c.py`](test/dsl/test_emit_c.py)
- 功能实现: [`kernel_gen/tools/ircheck.py`](kernel_gen/tools/ircheck.py)
- 功能实现: [`expectation/dsl/emit_c/npu_demo/kernel/exp.py`](expectation/dsl/emit_c/npu_demo/kernel/exp.py)
"""

# Case 列表:
# - emit_c-npu_demo-kernel-exp-static: 静态 shape 的 `kernel.exp` 应生成 `exp<Space, InputType, OutputType>(ctx, out, input);`。
# - emit_c-npu_demo-kernel-exp-dynamic: 动态 shape 的 `kernel.exp` 也应生成同口径 helper 调用。

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
from expectation.utils.random import get_random_float_numeric_type


def _build_case_kernel_exp_static() -> tuple[str, str]:
    """构造静态 `kernel.exp` expectation IR。"""
    static_m, static_n = random_static_dims(2)
    space = random_memory_spaces(1, unique=False)[0]
    space_ir = memory_space_ir_name(space)
    space_cpp = cpp_space_name(space)
    dtype = get_random_float_numeric_type()
    dtype_ir = numeric_type_ir(dtype)
    dtype_cpp = cpp_numeric_type_name(dtype)
    mem_type = f"!nn.memory<[#C_M, #C_N], [#C_N, #C1], {dtype_ir}, #nn.space<{space_ir}>>"
    alias_defs = f"""#C_M = #symbol.expr<{static_m}>
#C_N = #symbol.expr<{static_n}>
#C1 = #symbol.expr<1>
"""
    case_text = f"""// COMPILE_ARGS: --pass no-op
// CASE: kernel.exp 应生成 out-first 的 exp 调用。
// CHECK: template <typename Context>
// CHECK: void kernel_exp_case(Context& ctx, Memory<{space_cpp}, {dtype_cpp}>& [[OUT:{{val}}]], Memory<{space_cpp}, {dtype_cpp}>& [[IN:{{val}}]]) {{
// CHECK-NEXT:     exp<{space_cpp}, {dtype_cpp}, {dtype_cpp}>(ctx, [[OUT]] /*out*/, [[IN]] /*input*/);
// CHECK-NEXT: }}

{alias_defs}
builtin.module {{
  func.func @kernel_exp_case(
    %ctx : index {{name = "ctx"}},
    %0 : {mem_type},
    %1 : {mem_type}
  ) {{
    "kernel.exp"(%1, %0) {{space = #nn.space<{space_ir}>}} : ({mem_type}, {mem_type}) -> ()
    func.return
  }}
}}"""
    return case_text, f"exp<{space_cpp}, {dtype_cpp}, {dtype_cpp}>(ctx,"


def _case_kernel_exp_static() -> None:
    """运行静态 `kernel.exp` expectation。"""

    case_text, expected_call_snippet = _build_case_kernel_exp_static()
    print_case_input_ir(
        "emit_c-npu_demo-kernel-exp-static",
        case_text,
        fallback="静态 shape 的 kernel.exp 应生成 out-first exp helper 调用。",
    )

    run_emitc_case(
        case_text,
        source_path="expectation/dsl/emit_c/npu_demo/kernel/exp.py",
        op_name="kernel.exp",
        expected_snippets=[
            "template <typename Context>\nvoid kernel_exp_case(Context& ctx,",
            expected_call_snippet,
        ],
        forbidden_snippets=["kernel.exp"],
    )


def _build_case_kernel_exp_dynamic() -> tuple[str, str]:
    """构造动态 `kernel.exp` expectation IR。"""
    sym_m, sym_n = random_symbol_names(2)
    space = random_memory_spaces(1, unique=False)[0]
    space_ir = memory_space_ir_name(space)
    space_cpp = cpp_space_name(space)
    dtype = get_random_float_numeric_type()
    dtype_ir = numeric_type_ir(dtype)
    dtype_cpp = cpp_numeric_type_name(dtype)
    dynamic_mem_type = f"!nn.memory<[#S_M, #S_N], [#S_N, #C1], {dtype_ir}, #nn.space<{space_ir}>>"
    alias_defs = f"""#S_M = #symbol.expr<{sym_m}>
#S_N = #symbol.expr<{sym_n}>
#C1 = #symbol.expr<1>
"""
    case_text = f"""// COMPILE_ARGS: --pass no-op
// CASE: kernel.exp 的动态 shape 版本也应生成 out-first 的 exp 调用。
// CHECK: template <typename Context>
// CHECK: void kernel_exp_dynamic_case(Context& ctx, Memory<{space_cpp}, {dtype_cpp}>& [[OUT:{{val}}]], Memory<{space_cpp}, {dtype_cpp}>& [[IN:{{val}}]]) {{
// CHECK-NEXT:     exp<{space_cpp}, {dtype_cpp}, {dtype_cpp}>(ctx, [[OUT]] /*out*/, [[IN]] /*input*/);
// CHECK-NEXT: }}

{alias_defs}
builtin.module {{
  func.func @kernel_exp_dynamic_case(
    %ctx : index {{name = "ctx"}},
    %0 : {dynamic_mem_type},
    %1 : {dynamic_mem_type}
  ) {{
    "kernel.exp"(%1, %0) {{space = #nn.space<{space_ir}>}} : ({dynamic_mem_type}, {dynamic_mem_type}) -> ()
    func.return
  }}
}}"""
    return case_text, f"exp<{space_cpp}, {dtype_cpp}, {dtype_cpp}>(ctx,"


def _case_kernel_exp_dynamic() -> None:
    """运行动态 `kernel.exp` expectation。"""

    case_text, expected_call_snippet = _build_case_kernel_exp_dynamic()
    print_case_input_ir(
        "emit_c-npu_demo-kernel-exp-dynamic",
        case_text,
        fallback="动态 shape 的 kernel.exp 也应生成 out-first exp helper 调用。",
    )

    run_emitc_case(
        case_text,
        source_path="expectation/dsl/emit_c/npu_demo/kernel/exp.py#dynamic",
        op_name="kernel.exp.dynamic",
        expected_snippets=[
            "template <typename Context>\nvoid kernel_exp_dynamic_case(Context& ctx,",
            expected_call_snippet,
        ],
        forbidden_snippets=["kernel.exp"],
    )


def main() -> None:
    """运行 `kernel.exp` 的 emit_c expectation。"""

    failures: list[tuple[str, BaseException]] = []
    run_case(
        failures,
        "emit_c-npu_demo-kernel-exp-static",
        _case_kernel_exp_static,
    )
    run_case(
        failures,
        "emit_c-npu_demo-kernel-exp-dynamic",
        _case_kernel_exp_dynamic,
    )
    raise_if_failures("emit_c npu_demo kernel exp expectation", failures)


if __name__ == "__main__":
    main()
