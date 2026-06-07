# [immutable-file]
"""emit_c npu_demo kernel expectation：binary elewise。

创建者: 大闸蟹
最后一次更改: 大闸蟹

功能说明:
- 使用 `ircheck emitc_target="npu_demo"` 运行 `kernel.binary_elewise(kind=...)` 的源码 expectation。
- 统一覆盖 `add/sub/mul/div` 四类二元逐元素算子。
- 验证源码应生成 `Context& ctx` 首参函数，并生成
  `add/sub/mul/truediv<Space, InType, OutType>(ctx, out, lhs, rhs);` 调用。

使用示例:
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python expectation/dsl/emit_c/npu_demo/kernel/binary_elewise.py`

关联文件:
- spec: [`spec/dsl/gen_kernel/emit.md`](spec/dsl/gen_kernel/emit.md)
- spec: [`spec/dsl/gen_kernel/emit/npu_demo.md`](spec/dsl/gen_kernel/emit/npu_demo.md)
- spec: [`spec/tools/ircheck.md`](spec/tools/ircheck.md)
- spec: [`spec/include/api/Kernel.md`](spec/include/api/Kernel.md)
- test: [`test/dsl/test_emit_c.py`](test/dsl/test_emit_c.py)
- test: [`test/tools/test_ircheck_runner.py`](test/tools/test_ircheck_runner.py)
- 功能实现: [`kernel_gen/tools/ircheck.py`](kernel_gen/tools/ircheck.py)
- 功能实现: [`expectation/dsl/emit_c/npu_demo/kernel/binary_elewise.py`](expectation/dsl/emit_c/npu_demo/kernel/binary_elewise.py)
"""

# Case 列表:
# - emit_c-npu_demo-kernel-binary-elewise-add-static / emit_c-npu_demo-kernel-binary-elewise-add-dynamic: `kind="add"` 在 `ircheck --emit target=npu_demo` 下应生成 context-first helper 调用。
# - emit_c-npu_demo-kernel-binary-elewise-sub-static / emit_c-npu_demo-kernel-binary-elewise-sub-dynamic: `kind="sub"` 在 `ircheck --emit target=npu_demo` 下应生成同口径源码。
# - emit_c-npu_demo-kernel-binary-elewise-mul-static / emit_c-npu_demo-kernel-binary-elewise-mul-dynamic: `kind="mul"` 在 `ircheck --emit target=npu_demo` 下应生成同口径源码。
# - emit_c-npu_demo-kernel-binary-elewise-div-static / emit_c-npu_demo-kernel-binary-elewise-div-dynamic: `kind="div"` 在 `ircheck --emit target=npu_demo` 下应生成同口径源码。

from __future__ import annotations

from pathlib import Path
import sys

REPO_ROOT = next(parent for parent in Path(__file__).resolve().parents if (parent / "kernel_gen").exists())
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from expectation.utils.case_runner import print_case_input_ir, raise_if_failures, run_case
from expectation.utils.random import get_random_arithmetic_numeric_types
from expectation.utils.random_utils import memory_space_ir_name, numeric_type_ir, random_memory_spaces, random_static_dims, random_symbol_names
from kernel_gen.symbol_variable.memory import MemorySpace
from kernel_gen.symbol_variable.type import NumericType
from kernel_gen.tools.ircheck import run_ircheck_text


_KIND_TO_HELPER = {
    "add": "add",
    "sub": "sub",
    "mul": "mul",
    "div": "truediv",
}


def _space_enum_name(space: MemorySpace) -> str:
    from expectation.utils.emitc import cpp_space_name

    return cpp_space_name(space)


def _cpp_type_name(dtype: NumericType) -> str:
    from expectation.utils.emitc import cpp_numeric_type_name

    return cpp_numeric_type_name(dtype)


def _assert_emitc_case_success(
    case_text: str,
    *,
    source_path: str,
    function_name: str,
    kind: str,
    helper_name: str,
    expected_call_snippet: str,
) -> None:
    result = run_ircheck_text(case_text, source_path=source_path, emitc_target="npu_demo")
    assert result.ok is True, (
        f"binary_elewise:{kind}:{function_name}: expected ok=True, got ok={result.ok}, "
        f"exit_code={result.exit_code}, message={result.message!r}"
    )
    assert result.exit_code == 0, (
        f"binary_elewise:{kind}:{function_name}: expected exit_code=0, got {result.exit_code}"
    )
    assert "kernel.binary_elewise" not in result.actual_ir, (
        f"binary_elewise:{kind}:{function_name}: actual_ir must not leak kernel.binary_elewise, "
        f"got {result.actual_ir!r}"
    )
    assert "cpu::" not in result.actual_ir, (
        f"binary_elewise:{kind}:{function_name}: actual_ir must stay on npu_demo helper, "
        f"got {result.actual_ir!r}"
    )
    assert helper_name in result.actual_ir, (
        f"binary_elewise:{kind}:{function_name}: actual_ir must contain helper {helper_name!r}, "
        f"got {result.actual_ir!r}"
    )
    assert "template <typename Context>" in result.actual_ir, (
        f"binary_elewise:{kind}:{function_name}: actual_ir must declare generic Context template, "
        f"got {result.actual_ir!r}"
    )
    assert f"void {function_name}(Context& ctx," in result.actual_ir, (
        f"binary_elewise:{kind}:{function_name}: actual_ir must take Context& ctx as first argument, "
        f"got {result.actual_ir!r}"
    )
    assert expected_call_snippet in result.actual_ir, (
        f"binary_elewise:{kind}:{function_name}: actual_ir must call {expected_call_snippet!r}, "
        f"got {result.actual_ir!r}"
    )


def _build_static_case(kind: str, helper_name: str) -> tuple[str, str, str]:
    static_m, static_n = random_static_dims(2)
    input_dtype, output_dtype = get_random_arithmetic_numeric_types(
        2,
        exclude=(NumericType.Float16, NumericType.BFloat16),
        unique=False,
    )
    space = random_memory_spaces(1, unique=False)[0]
    input_dtype_ir = numeric_type_ir(input_dtype)
    output_dtype_ir = numeric_type_ir(output_dtype)
    space_ir = memory_space_ir_name(space)
    input_mem_type = f"!nn.memory<[#C_M, #C_N], [#C_N, #C1], {input_dtype_ir}, #nn.space<{space_ir}>>"
    output_mem_type = f"!nn.memory<[#C_M, #C_N], [#C_N, #C1], {output_dtype_ir}, #nn.space<{space_ir}>>"
    space_cpp = _space_enum_name(space)
    input_dtype_cpp = _cpp_type_name(input_dtype)
    output_dtype_cpp = _cpp_type_name(output_dtype)
    function_name = f"kernel_binary_{kind}_case"
    alias_defs = f"""#C_M = #symbol.expr<{static_m}>
#C_N = #symbol.expr<{static_n}>
#C1 = #symbol.expr<1>
"""
    case_text = f"""// COMPILE_ARGS: --pass no-op
// CHECK: template <typename Context>
// CHECK: void {function_name}(Context& ctx, Memory<{space_cpp}, {output_dtype_cpp}>& [[OUT:{{val}}]], Memory<{space_cpp}, {input_dtype_cpp}>& [[LHS:{{val}}]], Memory<{space_cpp}, {input_dtype_cpp}>& [[RHS:{{val}}]]) {{
// CHECK-NEXT:     {helper_name}<{space_cpp}, {input_dtype_cpp}, {output_dtype_cpp}>(ctx, [[OUT]] /*out*/, [[LHS]] /*lhs*/, [[RHS]] /*rhs*/);
// CHECK-NEXT: }}

{alias_defs}
builtin.module {{
  func.func @{function_name}(
    %ctx : index {{name = "ctx"}},
    %0 : {output_mem_type} {{name = "out"}},
    %1 : {input_mem_type} {{name = "lhs"}},
    %2 : {input_mem_type} {{name = "rhs"}}
  ) {{
    "kernel.binary_elewise"(%0, %1, %2) {{kind = "{kind}", space = #nn.space<{space_ir}>}} : ({output_mem_type}, {input_mem_type}, {input_mem_type}) -> ()
    func.return
  }}
}}"""
    return case_text, function_name, f"{helper_name}<{space_cpp}, {input_dtype_cpp}, {output_dtype_cpp}>(ctx,"


def _build_dynamic_case(kind: str, helper_name: str) -> tuple[str, str, str]:
    sym_m, sym_n = random_symbol_names(2)
    input_dtype, output_dtype = get_random_arithmetic_numeric_types(
        2,
        exclude=(NumericType.Float16, NumericType.BFloat16),
        unique=False,
    )
    space = random_memory_spaces(1, unique=False)[0]
    input_dtype_ir = numeric_type_ir(input_dtype)
    output_dtype_ir = numeric_type_ir(output_dtype)
    space_ir = memory_space_ir_name(space)
    dynamic_input_mem_type = f"!nn.memory<[#S_M, #S_N], [#S_N, #C1], {input_dtype_ir}, #nn.space<{space_ir}>>"
    dynamic_output_mem_type = f"!nn.memory<[#S_M, #S_N], [#S_N, #C1], {output_dtype_ir}, #nn.space<{space_ir}>>"
    space_cpp = _space_enum_name(space)
    input_dtype_cpp = _cpp_type_name(input_dtype)
    output_dtype_cpp = _cpp_type_name(output_dtype)
    function_name = f"kernel_binary_{kind}_dynamic_case"
    alias_defs = f"""#S_M = #symbol.expr<{sym_m}>
#S_N = #symbol.expr<{sym_n}>
#C1 = #symbol.expr<1>
"""
    case_text = f"""// COMPILE_ARGS: --pass no-op
// CHECK: template <typename Context>
// CHECK: void {function_name}(Context& ctx, Memory<{space_cpp}, {output_dtype_cpp}>& [[OUT:{{val}}]], Memory<{space_cpp}, {input_dtype_cpp}>& [[LHS:{{val}}]], Memory<{space_cpp}, {input_dtype_cpp}>& [[RHS:{{val}}]]) {{
// CHECK-NEXT:     {helper_name}<{space_cpp}, {input_dtype_cpp}, {output_dtype_cpp}>(ctx, [[OUT]] /*out*/, [[LHS]] /*lhs*/, [[RHS]] /*rhs*/);
// CHECK-NEXT: }}

{alias_defs}
builtin.module {{
  func.func @{function_name}(
    %ctx : index {{name = "ctx"}},
    %0 : {dynamic_output_mem_type} {{name = "out"}},
    %1 : {dynamic_input_mem_type} {{name = "lhs"}},
    %2 : {dynamic_input_mem_type} {{name = "rhs"}}
  ) {{
    "kernel.binary_elewise"(%0, %1, %2) {{kind = "{kind}", space = #nn.space<{space_ir}>}} : ({dynamic_output_mem_type}, {dynamic_input_mem_type}, {dynamic_input_mem_type}) -> ()
    func.return
  }}
}}"""
    return case_text, function_name, f"{helper_name}<{space_cpp}, {input_dtype_cpp}, {output_dtype_cpp}>(ctx,"


def _run_static_case(kind: str, helper_name: str) -> None:
    case_text, function_name, expected_call_snippet = _build_static_case(kind, helper_name)
    print_case_input_ir(
        f"emit_c-npu_demo-kernel-binary-elewise-{kind}-static",
        case_text,
        fallback=f'静态 shape 的 kernel.binary_elewise(kind="{kind}") 应生成对应 helper 调用。',
    )
    _assert_emitc_case_success(
        case_text,
        source_path=f"expectation/dsl/emit_c/npu_demo/kernel/binary_elewise.py#{kind}-static",
        function_name=function_name,
        kind=kind,
        helper_name=helper_name,
        expected_call_snippet=expected_call_snippet,
    )


def _run_dynamic_case(kind: str, helper_name: str) -> None:
    case_text, function_name, expected_call_snippet = _build_dynamic_case(kind, helper_name)
    print_case_input_ir(
        f"emit_c-npu_demo-kernel-binary-elewise-{kind}-dynamic",
        case_text,
        fallback=f'动态 shape 的 kernel.binary_elewise(kind="{kind}") 应生成对应 helper 调用。',
    )
    _assert_emitc_case_success(
        case_text,
        source_path=f"expectation/dsl/emit_c/npu_demo/kernel/binary_elewise.py#{kind}-dynamic",
        function_name=function_name,
        kind=kind,
        helper_name=helper_name,
        expected_call_snippet=expected_call_snippet,
    )


def main() -> None:
    """运行本文件定义的全部 expectation case。"""

    failures: list[tuple[str, BaseException]] = []
    for kind, helper_name in _KIND_TO_HELPER.items():
        run_case(
            failures,
            f"emit_c-npu_demo-kernel-binary-elewise-{kind}-static",
            lambda kind=kind, helper_name=helper_name: _run_static_case(kind, helper_name),
        )
        run_case(
            failures,
            f"emit_c-npu_demo-kernel-binary-elewise-{kind}-dynamic",
            lambda kind=kind, helper_name=helper_name: _run_dynamic_case(kind, helper_name),
        )
    raise_if_failures("emit_c npu_demo kernel binary_elewise expectation", failures)


if __name__ == "__main__":
    main()
