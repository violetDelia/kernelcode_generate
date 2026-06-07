# [immutable-file]
"""emit_c npu_demo dma expectation：alloc。

创建者: 榕
最后一次更改: 榕

功能说明:
- 使用 `ircheck emitc_target="npu_demo"` 运行 `dma.alloc` 的源码 expectation。
- 验证 `dma.alloc` 经 `ircheck --emit` 后，应生成 context-first 接口式
  `alloc<Space, Type>(ctx, {...}, {...})` 调用，而不是直接展开底层 buffer + `Memory<...>` 构造。
- 该 expectation 按规范随机化 dtype 与 space，不迁就当前实现。

使用示例:
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python expectation/dsl/emit_c/npu_demo/dma/alloc.py`

关联文件:
- spec: [`spec/dsl/emit_c.md`](spec/dsl/emit_c.md)
- spec: [`spec/tools/ircheck.md`](spec/tools/ircheck.md)
- spec: [`spec/include/api/Dma.md`](spec/include/api/Dma.md)
- 功能实现: [`kernel_gen/tools/ircheck.py`](kernel_gen/tools/ircheck.py)
- 功能实现: [`expectation/dsl/emit_c/npu_demo/dma/alloc.py`](expectation/dsl/emit_c/npu_demo/dma/alloc.py)
"""

# Case 列表:
# - emit_c-npu_demo-dma-alloc-static: 静态 shape 的 `dma.alloc` 应生成 `alloc<Space, Type>(ctx, {shape}, {stride})`。
# - emit_c-npu_demo-dma-alloc-dynamic: 动态 shape 的 `dma.alloc` 应生成符号 shape + 连续 stride 的 context-first `alloc<...>`。
# - emit_c-npu_demo-dma-alloc-symbol-add: `symbol.add` 结果作为 shape 时，也应先 materialize 再生成 `alloc<...>`。

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
    symbol_int_type_ir,
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


def _random_dtype() -> NumericType:
    return get_random_arithmetic_numeric_types(
        1,
        exclude=(NumericType.Float16, NumericType.BFloat16),
        unique=False,
    )[0]


def _case_dma_alloc_static() -> None:
    """运行静态 `dma.alloc` expectation。"""

    static_m, static_n = random_static_dims(2, unique=True)
    dtype = _random_dtype()
    space = random_memory_spaces(1, unique=False)[0]
    dtype_ir = numeric_type_ir(dtype)
    space_ir = memory_space_ir_name(space)
    space_cpp = _space_enum_name(space)
    dtype_cpp = _cpp_type_name(dtype)
    case_text = f"""// COMPILE_ARGS: --pass no-op
// CHECK: template <typename Context>
// CHECK: void dma_alloc_case(Context& ctx) {{
// CHECK-NEXT:     Memory<{space_cpp}, {dtype_cpp}> [[OUT:{{val}}]] = alloc<{space_cpp}, {dtype_cpp}>(ctx, {{{static_m}, {static_n}}} /*shape*/, {{{static_n}, 1}} /*stride*/);
// CHECK-NEXT: }}

#C1 = #symbol.expr<1>
#C{static_m} = #symbol.expr<{static_m}>
#C{static_n} = #symbol.expr<{static_n}>
builtin.module {{
  func.func @dma_alloc_case(%ctx : index {{name = "ctx"}}) {{
    %0 = "dma.alloc"() <{{operandSegmentSizes = array<i32: 0>}}> : () -> !nn.memory<[#C{static_m}, #C{static_n}], [#C{static_n}, #C1], {dtype_ir}, #nn.space<{space_ir}>>
    func.return
  }}
}}"""


    print_case_input_ir(
        "emit_c-npu_demo-dma-alloc-static",
        case_text,
        fallback="emit_c-npu_demo-dma-alloc-static",
    )
    run_emitc_case(
        case_text,
        source_path="expectation/dsl/emit_c/npu_demo/dma/alloc.py",
        op_name="dma.alloc",
        expected_snippets=[
            "template <typename Context>\nvoid dma_alloc_case(Context& ctx",
            f"alloc<{space_cpp}, {dtype_cpp}>(ctx,",
            "{",
        ],
        forbidden_snippets=["dma.alloc", "Vector(", "static_cast<long long>"],
    )


def _case_dma_alloc_dynamic() -> None:
    """运行动态 `dma.alloc` expectation。"""

    dyn_m, dyn_n = random_symbol_names(2)
    dtype = _random_dtype()
    space = random_memory_spaces(1, unique=False)[0]
    dtype_ir = numeric_type_ir(dtype)
    dyn_m_type = f"!symbol.int<#S_{dyn_m}>"
    dyn_n_type = f"!symbol.int<#S_{dyn_n}>"
    space_ir = memory_space_ir_name(space)
    space_cpp = _space_enum_name(space)
    dtype_cpp = _cpp_type_name(dtype)
    case_text = f"""// COMPILE_ARGS: --pass no-op
// CHECK: template <typename Context>
// CHECK: void dma_alloc_dynamic_case(Context& ctx, S_INT [[M:{{val}}]], S_INT [[N:{{val}}]]) {{
// CHECK-NEXT:     Memory<{space_cpp}, {dtype_cpp}> [[OUT:{{val}}]] = alloc<{space_cpp}, {dtype_cpp}>(ctx, {{[[M]], [[N]]}} /*shape*/, {{[[N]], 1}} /*stride*/);
// CHECK-NEXT: }}

#S_{dyn_m} = #symbol.expr<{dyn_m}>
#S_{dyn_n} = #symbol.expr<{dyn_n}>
#C1 = #symbol.expr<1>
builtin.module {{
  func.func @dma_alloc_dynamic_case(
    %ctx : index {{name = "ctx"}},
    %0 : {dyn_m_type},
    %1 : {dyn_n_type}
  ) {{
    %2 = "dma.alloc"(%0, %1) <{{operandSegmentSizes = array<i32: 2>}}> : ({dyn_m_type}, {dyn_n_type}) -> !nn.memory<[#S_{dyn_m}, #S_{dyn_n}], [#S_{dyn_n}, #C1], {dtype_ir}, #nn.space<{space_ir}>>
    func.return
  }}
}}"""


    print_case_input_ir(
        "emit_c-npu_demo-dma-alloc-dynamic",
        case_text,
        fallback="emit_c-npu_demo-dma-alloc-dynamic",
    )
    run_emitc_case(
        case_text,
        source_path="expectation/dsl/emit_c/npu_demo/dma/alloc.py#dynamic",
        op_name="dma.alloc.dynamic",
        expected_snippets=[
            "template <typename Context>\nvoid dma_alloc_dynamic_case(Context& ctx,",
            f"alloc<{space_cpp}, {dtype_cpp}>(ctx,",
            "{",
        ],
        forbidden_snippets=["dma.alloc", "Vector(", "static_cast<long long>"],
    )


def _case_dma_alloc_symbol_add() -> None:
    """运行 `symbol.add` shape 的 `dma.alloc` expectation。"""

    add_shape_1_base, add_shape_1_delta, add_shape_2_base, add_shape_2_delta = random_symbol_names(4)
    add_shape_1_expr = f"{add_shape_1_base} + {add_shape_1_delta}"
    add_shape_2_expr = f"{add_shape_2_base} + {add_shape_2_delta}"
    add_arg_types = tuple(
        f"!symbol.int<#S_{symbol}>"
        for symbol in (
            add_shape_1_base,
            add_shape_1_delta,
            add_shape_2_base,
            add_shape_2_delta,
        )
    )
    add_result_types = ("!symbol.int<#S1>", "!symbol.int<#S2>")
    dtype = _random_dtype()
    space = random_memory_spaces(1, unique=False)[0]
    dtype_ir = numeric_type_ir(dtype)
    space_ir = memory_space_ir_name(space)
    space_cpp = _space_enum_name(space)
    dtype_cpp = _cpp_type_name(dtype)
    case_text = f"""// COMPILE_ARGS: --pass no-op
// CHECK: template <typename Context>
// CHECK: void dma_alloc_symbol_add_case(Context& ctx, S_INT [[SHAPE1_BASE:{{val}}]], S_INT [[SHAPE1_DELTA:{{val}}]], S_INT [[SHAPE2_BASE:{{val}}]], S_INT [[SHAPE2_DELTA:{{val}}]]) {{
// CHECK-NEXT:     S_INT [[SHAPE1_LOCAL:{{val}}]] = ([[SHAPE1_BASE]] + [[SHAPE1_DELTA]]);
// CHECK-NEXT:     S_INT [[SHAPE2_LOCAL:{{val}}]] = ([[SHAPE2_BASE]] + [[SHAPE2_DELTA]]);
// CHECK-NEXT:     Memory<{space_cpp}, {dtype_cpp}> [[OUT:{{val}}]] = alloc<{space_cpp}, {dtype_cpp}>(ctx, {{[[SHAPE1_LOCAL]], [[SHAPE2_LOCAL]]}} /*shape*/, {{[[SHAPE2_LOCAL]], 1}} /*stride*/);
// CHECK-NEXT: }}

#S_{add_shape_1_base} = #symbol.expr<{add_shape_1_base}>
#S_{add_shape_1_delta} = #symbol.expr<{add_shape_1_delta}>
#S_{add_shape_2_base} = #symbol.expr<{add_shape_2_base}>
#S_{add_shape_2_delta} = #symbol.expr<{add_shape_2_delta}>
#S1 = #symbol.expr<{add_shape_1_base} + {add_shape_1_delta}>
#S2 = #symbol.expr<{add_shape_2_base} + {add_shape_2_delta}>
#C1 = #symbol.expr<1>
builtin.module {{
  func.func @dma_alloc_symbol_add_case(
    %ctx : index {{name = "ctx"}},
    %0 : {add_arg_types[0]},
    %1 : {add_arg_types[1]},
    %2 : {add_arg_types[2]},
    %3 : {add_arg_types[3]}
  ) {{
    %4 = "symbol.add"(%0, %1) : ({add_arg_types[0]}, {add_arg_types[1]}) -> {add_result_types[0]}
    %5 = "symbol.add"(%2, %3) : ({add_arg_types[2]}, {add_arg_types[3]}) -> {add_result_types[1]}
    %6 = "dma.alloc"(%4, %5) <{{operandSegmentSizes = array<i32: 2>}}> : ({add_result_types[0]}, {add_result_types[1]}) -> !nn.memory<[#S1, #S2], [#S2, #C1], {dtype_ir}, #nn.space<{space_ir}>>
    func.return
  }}
}}"""


    print_case_input_ir(
        "emit_c-npu_demo-dma-alloc-symbol-add",
        case_text,
        fallback="emit_c-npu_demo-dma-alloc-symbol-add",
    )
    run_emitc_case(
        case_text,
        source_path="expectation/dsl/emit_c/npu_demo/dma/alloc.py#symbol_add",
        op_name="dma.alloc.symbol_add",
        expected_snippets=[
            "template <typename Context>\nvoid dma_alloc_symbol_add_case(Context& ctx,",
            f"alloc<{space_cpp}, {dtype_cpp}>(ctx,",
            "{",
        ],
        forbidden_snippets=["dma.alloc", "Vector(", "static_cast<long long>"],
    )


def main() -> None:
    failures: list[tuple[str, BaseException]] = []
    run_case(failures, "emit_c-npu_demo-dma-alloc-static", _case_dma_alloc_static)
    run_case(failures, "emit_c-npu_demo-dma-alloc-dynamic", _case_dma_alloc_dynamic)
    run_case(failures, "emit_c-npu_demo-dma-alloc-symbol-add", _case_dma_alloc_symbol_add)
    raise_if_failures("emit_c npu_demo dma alloc expectation", failures)


if __name__ == "__main__":
    main()
