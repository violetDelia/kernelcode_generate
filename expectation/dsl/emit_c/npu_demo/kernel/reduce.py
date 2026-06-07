# [immutable-file]
"""emit_c npu_demo kernel expectation：reduce family。

创建者: 榕
最后一次更改: 榕

功能说明:
- 覆盖 `kernel.reduce` 与 `kernel.reduce_min` 的 `emit_c` expectation。
- 锁定目标源码分别为 `reduce_sum<...>(ctx, arg0, input, axis);`
  与 `reduce_min<...>(ctx, arg0, input, axis);`。
- `reduce` 口径允许输入与输出使用不同 element type。

使用示例:
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python expectation/dsl/emit_c/npu_demo/kernel/reduce.py`

关联文件:
- spec: [`spec/dsl/emit_c.md`](spec/dsl/emit_c.md)
- spec: [`spec/tools/ircheck.md`](spec/tools/ircheck.md)
- spec: [`spec/include/api/Kernel.md`](spec/include/api/Kernel.md)
- test: [`test/dsl/test_emit_c.py`](test/dsl/test_emit_c.py)
- 功能实现: [`kernel_gen/tools/ircheck.py`](kernel_gen/tools/ircheck.py)
- 功能实现: [`expectation/dsl/emit_c/npu_demo/kernel/reduce.py`](expectation/dsl/emit_c/npu_demo/kernel/reduce.py)
"""

# Case 列表:
# - emit_c-npu_demo-kernel-reduce-sum-static / emit_c-npu_demo-kernel-reduce-sum-dynamic: `kernel.reduce(kind="sum")` 静态/动态 shape 应生成 `reduce_sum<...>(ctx, out, input, axis);`，其中 axis 为随机合法值。
# - emit_c-npu_demo-kernel-reduce-min-static / emit_c-npu_demo-kernel-reduce-min-dynamic: `kernel.reduce_min` 静态/动态 shape 应生成 `reduce_min<...>(ctx, out, input, axis);`，其中 axis 为随机合法值。

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
from expectation.utils.random import get_random_arithmetic_numeric_types, get_random_int
from kernel_gen.symbol_variable.type import NumericType


def _build_reduce_case(
    op_name: str,
    helper_name: str,
    attr_prefix: str,
    *,
    dynamic: bool,
) -> tuple[str, str, str]:
    reduce_axis = get_random_int(0, 1)
    dims = (random_symbol_names(2) if dynamic else random_static_dims(2, min_value=2, max_value=8))
    output_dims = (1, dims[1]) if reduce_axis == 0 else (dims[0], 1)
    space = random_memory_spaces(1, unique=False)[0]
    space_ir = memory_space_ir_name(space)
    space_cpp = cpp_space_name(space)
    input_dtype, output_dtype = get_random_arithmetic_numeric_types(
        2,
        exclude=(NumericType.Float16, NumericType.BFloat16),
        unique=False,
    )
    input_dtype_ir = numeric_type_ir(input_dtype)
    output_dtype_ir = numeric_type_ir(output_dtype)
    input_dtype_cpp = cpp_numeric_type_name(input_dtype)
    output_dtype_cpp = cpp_numeric_type_name(output_dtype)
    if dynamic:
        alias_defs = f"""#S_M = #symbol.expr<{dims[0]}>
#S_N = #symbol.expr<{dims[1]}>
#C1 = #symbol.expr<1>
"""
        input_mem_type = f"!nn.memory<[#S_M, #S_N], [#S_N, #C1], {input_dtype_ir}, #nn.space<{space_ir}>>"
        if reduce_axis == 0:
            output_mem_type = f"!nn.memory<[#C1, #S_N], [#S_N, #C1], {output_dtype_ir}, #nn.space<{space_ir}>>"
        else:
            output_mem_type = f"!nn.memory<[#S_M, #C1], [#C1, #C1], {output_dtype_ir}, #nn.space<{space_ir}>>"
    else:
        alias_defs = f"""#C_M = #symbol.expr<{dims[0]}>
#C_N = #symbol.expr<{dims[1]}>
#C1 = #symbol.expr<1>
"""
        input_mem_type = f"!nn.memory<[#C_M, #C_N], [#C_N, #C1], {input_dtype_ir}, #nn.space<{space_ir}>>"
        if reduce_axis == 0:
            output_mem_type = f"!nn.memory<[#C1, #C_N], [#C_N, #C1], {output_dtype_ir}, #nn.space<{space_ir}>>"
        else:
            output_mem_type = f"!nn.memory<[#C_M, #C1], [#C1, #C1], {output_dtype_ir}, #nn.space<{space_ir}>>"
    function_name = f"{helper_name}_dynamic_case" if dynamic else f"{helper_name}_case"
    attr_text = f"axis = {reduce_axis} : i64, keepdim = true, {attr_prefix}"
    case_text = f"""// COMPILE_ARGS: --pass no-op
// CASE: {op_name} 应生成 out-first 的 {helper_name} 调用。
// CHECK: template <typename Context>
// CHECK: void {function_name}(Context& ctx, Memory<{space_cpp}, {output_dtype_cpp}>& [[OUT:{{val}}]], Memory<{space_cpp}, {input_dtype_cpp}>& [[IN:{{val}}]]) {{
// CHECK-NEXT:     {helper_name}<{space_cpp}, {input_dtype_cpp}, {output_dtype_cpp}>(ctx, [[OUT]] /*out*/, [[IN]] /*input*/, {reduce_axis} /*axis*/);
// CHECK-NEXT: }}

{alias_defs}
builtin.module {{
  func.func @{function_name}(
    %ctx : index {{name = "ctx"}},
    %0 : {output_mem_type},
    %1 : {input_mem_type}
  ) {{
    "{op_name}"(%1, %0) {{{attr_text} space = #nn.space<{space_ir}>}} : ({input_mem_type}, {output_mem_type}) -> ()
    func.return
  }}
}}"""
    return function_name, case_text, f"{helper_name}<{space_cpp}, {input_dtype_cpp}, {output_dtype_cpp}>(ctx,"


def _case_kernel_reduce_sum_static() -> None:
    function_name, case_text, expected_call_snippet = _build_reduce_case(
        "kernel.reduce",
        "reduce_sum",
        'kind = "sum", ',
        dynamic=False,
    )
    print_case_input_ir(
        "emit_c-npu_demo-kernel-reduce-sum-static",
        case_text,
        fallback="静态 shape 的 kernel.reduce(kind=sum) 应生成 reduce_sum helper 调用。",
    )
    run_emitc_case(
        case_text,
        source_path=f"expectation/dsl/emit_c/npu_demo/kernel/reduce.py#{function_name}",
        op_name="kernel.reduce",
        expected_snippets=[
            f"template <typename Context>\nvoid {function_name}(Context& ctx,",
            expected_call_snippet,
        ],
        forbidden_snippets=["kernel.reduce"],
    )


def _case_kernel_reduce_sum_dynamic() -> None:
    function_name, case_text, expected_call_snippet = _build_reduce_case(
        "kernel.reduce",
        "reduce_sum",
        'kind = "sum", ',
        dynamic=True,
    )
    print_case_input_ir(
        "emit_c-npu_demo-kernel-reduce-sum-dynamic",
        case_text,
        fallback="动态 shape 的 kernel.reduce(kind=sum) 应生成 reduce_sum helper 调用。",
    )
    run_emitc_case(
        case_text,
        source_path=f"expectation/dsl/emit_c/npu_demo/kernel/reduce.py#{function_name}",
        op_name="kernel.reduce.dynamic",
        expected_snippets=[
            f"template <typename Context>\nvoid {function_name}(Context& ctx,",
            expected_call_snippet,
        ],
        forbidden_snippets=["kernel.reduce"],
    )


def _case_kernel_reduce_min_static() -> None:
    function_name, case_text, expected_call_snippet = _build_reduce_case(
        "kernel.reduce_min",
        "reduce_min",
        "",
        dynamic=False,
    )
    print_case_input_ir(
        "emit_c-npu_demo-kernel-reduce-min-static",
        case_text,
        fallback="静态 shape 的 kernel.reduce_min 应生成 reduce_min helper 调用。",
    )
    run_emitc_case(
        case_text,
        source_path=f"expectation/dsl/emit_c/npu_demo/kernel/reduce.py#{function_name}",
        op_name="kernel.reduce_min",
        expected_snippets=[
            f"template <typename Context>\nvoid {function_name}(Context& ctx,",
            expected_call_snippet,
        ],
        forbidden_snippets=["kernel.reduce_min"],
    )


def _case_kernel_reduce_min_dynamic() -> None:
    function_name, case_text, expected_call_snippet = _build_reduce_case(
        "kernel.reduce_min",
        "reduce_min",
        "",
        dynamic=True,
    )
    print_case_input_ir(
        "emit_c-npu_demo-kernel-reduce-min-dynamic",
        case_text,
        fallback="动态 shape 的 kernel.reduce_min 应生成 reduce_min helper 调用。",
    )
    run_emitc_case(
        case_text,
        source_path=f"expectation/dsl/emit_c/npu_demo/kernel/reduce.py#{function_name}",
        op_name="kernel.reduce_min.dynamic",
        expected_snippets=[
            f"template <typename Context>\nvoid {function_name}(Context& ctx,",
            expected_call_snippet,
        ],
        forbidden_snippets=["kernel.reduce_min"],
    )


def main() -> None:
    """运行 reduce family 的 emit_c expectation。"""

    failures: list[tuple[str, BaseException]] = []
    run_case(failures, "emit_c-npu_demo-kernel-reduce-sum-static", _case_kernel_reduce_sum_static)
    run_case(failures, "emit_c-npu_demo-kernel-reduce-sum-dynamic", _case_kernel_reduce_sum_dynamic)
    run_case(failures, "emit_c-npu_demo-kernel-reduce-min-static", _case_kernel_reduce_min_static)
    run_case(failures, "emit_c-npu_demo-kernel-reduce-min-dynamic", _case_kernel_reduce_min_dynamic)
    raise_if_failures("emit_c npu_demo kernel reduce expectation", failures)


if __name__ == "__main__":
    main()
