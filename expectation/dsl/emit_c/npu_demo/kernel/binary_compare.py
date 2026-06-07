# [immutable-file]
"""emit_c npu_demo kernel expectation：binary compare。

创建者: 榕
最后一次更改: 榕

功能说明:
- 使用 `ircheck emitc_target="npu_demo"` 运行 `kernel.binary_elewise(kind=compare)` 的源码 expectation。
- 为 `eq/ne/lt/le/gt/ge` 每个 compare kind 提供至少一个 case。
- 锁定生成函数带 `Context& ctx` 首参，并调用
  `eq/ne/lt/le/gt/ge<Space, InType, bool>(ctx, out, lhs, rhs)`。
"""

# Case 列表:
# - emit_c-npu_demo-kernel-binary-compare-eq-static / emit_c-npu_demo-kernel-binary-compare-eq-dynamic: `eq` 静态/动态 shape 应生成 `eq<...>(ctx, out, lhs, rhs);`
# - emit_c-npu_demo-kernel-binary-compare-ne-static / emit_c-npu_demo-kernel-binary-compare-ne-dynamic: `ne` 静态/动态 shape 应生成 `ne<...>(ctx, out, lhs, rhs);`
# - emit_c-npu_demo-kernel-binary-compare-lt-static / emit_c-npu_demo-kernel-binary-compare-lt-dynamic: `lt` 静态/动态 shape 应生成 `lt<...>(ctx, out, lhs, rhs);`
# - emit_c-npu_demo-kernel-binary-compare-le-static / emit_c-npu_demo-kernel-binary-compare-le-dynamic: `le` 静态/动态 shape 应生成 `le<...>(ctx, out, lhs, rhs);`
# - emit_c-npu_demo-kernel-binary-compare-gt-static / emit_c-npu_demo-kernel-binary-compare-gt-dynamic: `gt` 静态/动态 shape 应生成 `gt<...>(ctx, out, lhs, rhs);`
# - emit_c-npu_demo-kernel-binary-compare-ge-static / emit_c-npu_demo-kernel-binary-compare-ge-dynamic: `ge` 静态/动态 shape 应生成 `ge<...>(ctx, out, lhs, rhs);`

from __future__ import annotations

from pathlib import Path
import sys

REPO_ROOT = next(parent for parent in Path(__file__).resolve().parents if (parent / "kernel_gen").exists())
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from expectation.utils.case_runner import print_case_input_ir, raise_if_failures, run_case
from expectation.utils.random_utils import memory_space_ir_name, numeric_type_ir, random_memory_spaces, random_static_dims, random_symbol_names
from expectation.utils.random import get_random_arithmetic_numeric_types
from kernel_gen.symbol_variable.memory import MemorySpace
from kernel_gen.symbol_variable.type import NumericType
from kernel_gen.tools.ircheck import run_ircheck_text


def _space_enum_name(space: MemorySpace) -> str:
    from expectation.utils.emitc import cpp_space_name

    return cpp_space_name(space)


def _cpp_type_name(dtype: NumericType) -> str:
    from expectation.utils.emitc import cpp_numeric_type_name

    return cpp_numeric_type_name(dtype)


def _assert_case(
    kind: str,
    function_name: str,
    expected_call_snippet: str,
    case_text: str,
    source_path: str,
) -> None:
    result = run_ircheck_text(case_text, source_path=source_path, emitc_target="npu_demo")
    assert result.ok is True, (
        f"{kind}: expected ok=True, got ok={result.ok}, exit_code={result.exit_code}, message={result.message!r}"
    )
    assert result.exit_code == 0, f"{kind}: expected exit_code=0, got {result.exit_code}"
    assert "kernel.binary_elewise" not in result.actual_ir, (
        f"{kind}: actual_ir must not leak kernel.binary_elewise, got {result.actual_ir!r}"
    )
    assert "template <typename Context>" in result.actual_ir, (
        f"{kind}: actual_ir must declare generic Context template, got {result.actual_ir!r}"
    )
    assert f"void {function_name}(Context& ctx," in result.actual_ir, (
        f"{kind}: actual_ir must take Context& ctx as first argument, got {result.actual_ir!r}"
    )
    assert expected_call_snippet in result.actual_ir, (
        f"{kind}: actual_ir must call {expected_call_snippet!r}, got {result.actual_ir!r}"
    )


def _build_binary_compare_case(kind: str, helper: str, *, dynamic: bool) -> tuple[str, str, str]:
    dims = random_symbol_names(2) if dynamic else random_static_dims(2)
    input_dtype = get_random_arithmetic_numeric_types(
        1,
        exclude=(NumericType.Float16, NumericType.BFloat16),
        unique=False,
    )[0]
    space = random_memory_spaces(
        1,
        unique=False,
    )[0]
    input_dtype_ir = numeric_type_ir(input_dtype)
    space_ir = memory_space_ir_name(space)
    if dynamic:
        alias_defs = f"""#S_M = #symbol.expr<{dims[0]}>
#S_N = #symbol.expr<{dims[1]}>
#C1 = #symbol.expr<1>
"""
        input_mem_type = f"!nn.memory<[#S_M, #S_N], [#S_N, #C1], {input_dtype_ir}, #nn.space<{space_ir}>>"
        pred_mem_type = f"!nn.memory<[#S_M, #S_N], [#S_N, #C1], i1, #nn.space<{space_ir}>>"
    else:
        alias_defs = f"""#C_M = #symbol.expr<{dims[0]}>
#C_N = #symbol.expr<{dims[1]}>
#C1 = #symbol.expr<1>
"""
        input_mem_type = f"!nn.memory<[#C_M, #C_N], [#C_N, #C1], {input_dtype_ir}, #nn.space<{space_ir}>>"
        pred_mem_type = f"!nn.memory<[#C_M, #C_N], [#C_N, #C1], i1, #nn.space<{space_ir}>>"
    space_cpp = _space_enum_name(space)
    input_dtype_cpp = _cpp_type_name(input_dtype)
    function_name = f"kernel_binary_{kind}_dynamic_case" if dynamic else f"kernel_binary_{kind}_case"
    case_text = f"""// COMPILE_ARGS: --pass no-op
// CHECK: template <typename Context>
// CHECK: void {function_name}(Context& ctx, Memory<{space_cpp}, bool>& [[OUT:{{val}}]], Memory<{space_cpp}, {input_dtype_cpp}>& [[LHS:{{val}}]], Memory<{space_cpp}, {input_dtype_cpp}>& [[RHS:{{val}}]]) {{
// CHECK-NEXT:     {helper}<{space_cpp}, {input_dtype_cpp}, bool>(ctx, [[OUT]] /*out*/, [[LHS]] /*lhs*/, [[RHS]] /*rhs*/);
// CHECK-NEXT: }}

{alias_defs}
builtin.module {{
  func.func @{function_name}(
    %ctx : index {{name = "ctx"}},
    %0 : {pred_mem_type},
    %1 : {input_mem_type},
    %2 : {input_mem_type}
  ) {{
    "kernel.binary_elewise"(%1, %2, %0) {{kind = "{kind}", space = #nn.space<{space_ir}>}} : ({input_mem_type}, {input_mem_type}, {pred_mem_type}) -> ()
    func.return
  }}
}}"""
    return function_name, case_text, f"{helper}<{space_cpp}, {input_dtype_cpp}, bool>(ctx,"


def _case_binary_eq_static() -> None:
    function_name, case_text, expected_call_snippet = _build_binary_compare_case("eq", "eq", dynamic=False)
    print_case_input_ir(
        "emit_c-npu_demo-kernel-binary-compare-eq-static",
        case_text,
        fallback='静态 shape 的 kernel.binary_elewise(kind="eq") 应生成 eq helper 调用。',
    )
    _assert_case("eq", function_name, expected_call_snippet, case_text, f"expectation/dsl/emit_c/npu_demo/kernel/binary_compare.py#{function_name}")


def _case_binary_eq_dynamic() -> None:
    function_name, case_text, expected_call_snippet = _build_binary_compare_case("eq", "eq", dynamic=True)
    print_case_input_ir(
        "emit_c-npu_demo-kernel-binary-compare-eq-dynamic",
        case_text,
        fallback='动态 shape 的 kernel.binary_elewise(kind="eq") 应生成 eq helper 调用。',
    )
    _assert_case("eq-dynamic", function_name, expected_call_snippet, case_text, f"expectation/dsl/emit_c/npu_demo/kernel/binary_compare.py#{function_name}")


def _case_binary_ne_static() -> None:
    function_name, case_text, expected_call_snippet = _build_binary_compare_case("ne", "ne", dynamic=False)
    print_case_input_ir(
        "emit_c-npu_demo-kernel-binary-compare-ne-static",
        case_text,
        fallback='静态 shape 的 kernel.binary_elewise(kind="ne") 应生成 ne helper 调用。',
    )
    _assert_case("ne", function_name, expected_call_snippet, case_text, f"expectation/dsl/emit_c/npu_demo/kernel/binary_compare.py#{function_name}")


def _case_binary_ne_dynamic() -> None:
    function_name, case_text, expected_call_snippet = _build_binary_compare_case("ne", "ne", dynamic=True)
    print_case_input_ir(
        "emit_c-npu_demo-kernel-binary-compare-ne-dynamic",
        case_text,
        fallback='动态 shape 的 kernel.binary_elewise(kind="ne") 应生成 ne helper 调用。',
    )
    _assert_case("ne-dynamic", function_name, expected_call_snippet, case_text, f"expectation/dsl/emit_c/npu_demo/kernel/binary_compare.py#{function_name}")


def _case_binary_lt_static() -> None:
    function_name, case_text, expected_call_snippet = _build_binary_compare_case("lt", "lt", dynamic=False)
    print_case_input_ir(
        "emit_c-npu_demo-kernel-binary-compare-lt-static",
        case_text,
        fallback='静态 shape 的 kernel.binary_elewise(kind="lt") 应生成 lt helper 调用。',
    )
    _assert_case("lt", function_name, expected_call_snippet, case_text, f"expectation/dsl/emit_c/npu_demo/kernel/binary_compare.py#{function_name}")


def _case_binary_lt_dynamic() -> None:
    function_name, case_text, expected_call_snippet = _build_binary_compare_case("lt", "lt", dynamic=True)
    print_case_input_ir(
        "emit_c-npu_demo-kernel-binary-compare-lt-dynamic",
        case_text,
        fallback='动态 shape 的 kernel.binary_elewise(kind="lt") 应生成 lt helper 调用。',
    )
    _assert_case("lt-dynamic", function_name, expected_call_snippet, case_text, f"expectation/dsl/emit_c/npu_demo/kernel/binary_compare.py#{function_name}")


def _case_binary_le_static() -> None:
    function_name, case_text, expected_call_snippet = _build_binary_compare_case("le", "le", dynamic=False)
    print_case_input_ir(
        "emit_c-npu_demo-kernel-binary-compare-le-static",
        case_text,
        fallback='静态 shape 的 kernel.binary_elewise(kind="le") 应生成 le helper 调用。',
    )
    _assert_case("le", function_name, expected_call_snippet, case_text, f"expectation/dsl/emit_c/npu_demo/kernel/binary_compare.py#{function_name}")


def _case_binary_le_dynamic() -> None:
    function_name, case_text, expected_call_snippet = _build_binary_compare_case("le", "le", dynamic=True)
    print_case_input_ir(
        "emit_c-npu_demo-kernel-binary-compare-le-dynamic",
        case_text,
        fallback='动态 shape 的 kernel.binary_elewise(kind="le") 应生成 le helper 调用。',
    )
    _assert_case("le-dynamic", function_name, expected_call_snippet, case_text, f"expectation/dsl/emit_c/npu_demo/kernel/binary_compare.py#{function_name}")


def _case_binary_gt_static() -> None:
    function_name, case_text, expected_call_snippet = _build_binary_compare_case("gt", "gt", dynamic=False)
    print_case_input_ir(
        "emit_c-npu_demo-kernel-binary-compare-gt-static",
        case_text,
        fallback='静态 shape 的 kernel.binary_elewise(kind="gt") 应生成 gt helper 调用。',
    )
    _assert_case("gt", function_name, expected_call_snippet, case_text, f"expectation/dsl/emit_c/npu_demo/kernel/binary_compare.py#{function_name}")


def _case_binary_gt_dynamic() -> None:
    function_name, case_text, expected_call_snippet = _build_binary_compare_case("gt", "gt", dynamic=True)
    print_case_input_ir(
        "emit_c-npu_demo-kernel-binary-compare-gt-dynamic",
        case_text,
        fallback='动态 shape 的 kernel.binary_elewise(kind="gt") 应生成 gt helper 调用。',
    )
    _assert_case("gt-dynamic", function_name, expected_call_snippet, case_text, f"expectation/dsl/emit_c/npu_demo/kernel/binary_compare.py#{function_name}")


def _case_binary_ge_static() -> None:
    function_name, case_text, expected_call_snippet = _build_binary_compare_case("ge", "ge", dynamic=False)
    print_case_input_ir(
        "emit_c-npu_demo-kernel-binary-compare-ge-static",
        case_text,
        fallback='静态 shape 的 kernel.binary_elewise(kind="ge") 应生成 ge helper 调用。',
    )
    _assert_case("ge", function_name, expected_call_snippet, case_text, f"expectation/dsl/emit_c/npu_demo/kernel/binary_compare.py#{function_name}")


def _case_binary_ge_dynamic() -> None:
    function_name, case_text, expected_call_snippet = _build_binary_compare_case("ge", "ge", dynamic=True)
    print_case_input_ir(
        "emit_c-npu_demo-kernel-binary-compare-ge-dynamic",
        case_text,
        fallback='动态 shape 的 kernel.binary_elewise(kind="ge") 应生成 ge helper 调用。',
    )
    _assert_case("ge-dynamic", function_name, expected_call_snippet, case_text, f"expectation/dsl/emit_c/npu_demo/kernel/binary_compare.py#{function_name}")


def main() -> None:
    failures: list[tuple[str, BaseException]] = []
    run_case(failures, "emit_c-npu_demo-kernel-binary-compare-eq-static", _case_binary_eq_static)
    run_case(failures, "emit_c-npu_demo-kernel-binary-compare-eq-dynamic", _case_binary_eq_dynamic)
    run_case(failures, "emit_c-npu_demo-kernel-binary-compare-ne-static", _case_binary_ne_static)
    run_case(failures, "emit_c-npu_demo-kernel-binary-compare-ne-dynamic", _case_binary_ne_dynamic)
    run_case(failures, "emit_c-npu_demo-kernel-binary-compare-lt-static", _case_binary_lt_static)
    run_case(failures, "emit_c-npu_demo-kernel-binary-compare-lt-dynamic", _case_binary_lt_dynamic)
    run_case(failures, "emit_c-npu_demo-kernel-binary-compare-le-static", _case_binary_le_static)
    run_case(failures, "emit_c-npu_demo-kernel-binary-compare-le-dynamic", _case_binary_le_dynamic)
    run_case(failures, "emit_c-npu_demo-kernel-binary-compare-gt-static", _case_binary_gt_static)
    run_case(failures, "emit_c-npu_demo-kernel-binary-compare-gt-dynamic", _case_binary_gt_dynamic)
    run_case(failures, "emit_c-npu_demo-kernel-binary-compare-ge-static", _case_binary_ge_static)
    run_case(failures, "emit_c-npu_demo-kernel-binary-compare-ge-dynamic", _case_binary_ge_dynamic)
    raise_if_failures("emit_c npu_demo kernel binary_compare expectation", failures)


if __name__ == "__main__":
    main()
