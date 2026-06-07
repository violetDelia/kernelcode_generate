# [immutable-file]
"""emit_c npu_demo dma expectation：slice。

创建者: 榕
最后一次更改: 守护最好的爱莉希雅

功能说明:
- 使用 `emit_c(target="npu_demo")` 运行 `dma.slice` 的源码 expectation。
- 验证 `dma.slice` 应生成 `slice(ctx, dst, source, offset, size, stride);` helper 调用。
- 覆盖静态参数、函数参数直传与 `symbol.add` materialize 三类合同。

使用示例:
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python expectation/dsl/emit_c/npu_demo/dma/slice.py`

关联文件:
- spec: [`spec/dsl/emit_c.md`](spec/dsl/emit_c.md)
- spec: [`spec/include/api/Dma.md`](spec/include/api/Dma.md)
- test: [`test/tools/test_emitc_case_runner.py`](test/tools/test_emitc_case_runner.py)
- 功能实现: [`kernel_gen/tools/emitc_case_runner.py`](kernel_gen/tools/emitc_case_runner.py)
- 功能实现: [`expectation/dsl/emit_c/npu_demo/dma/slice.py`](expectation/dsl/emit_c/npu_demo/dma/slice.py)
"""

# Case 列表:
# - emit_c-npu_demo-dma-slice-static: 静态 1D `dma.slice` 应生成 `slice(ctx, dst, source, {offset}, {size}, {stride})`。
# - emit_c-npu_demo-dma-slice-symbol-body-rank3: rank-3 `symbol.const` 参数的 `dma.slice` 应先 materialize 再生成 `slice(...)`。
# - emit_c-npu_demo-dma-slice-symbol-args-rank3: rank-3 动态 `symbol.int` 参数直传的 `dma.slice` 应生成 `slice(...)`。
# - emit_c-npu_demo-dma-slice-symbol-add-args-rank3: rank-3 `symbol.add` 结果作为 offset/size/stride 的 `dma.slice` 应先 materialize 再生成 `slice(...)`。

from __future__ import annotations

from pathlib import Path
import sys

REPO_ROOT = next(parent for parent in Path(__file__).resolve().parents if (parent / "kernel_gen").exists())
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from expectation.utils.case_runner import print_case_input_ir, raise_if_failures, run_case
from expectation.utils.random import get_random_arithmetic_numeric_types
from expectation.utils.random_utils import (
    memory_space_ir_name,
    numeric_type_ir,
    random_memory_spaces,
    random_static_dims,
    random_symbol_names,
    symbol_int_type_ir,
)
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


def _case_dma_slice_static() -> None:
    """运行静态 1D `dma.slice` expectation。"""

    tile_n = random_static_dims(1, min_value=4, max_value=12)[0]
    pad_n = random_static_dims(1, min_value=1, max_value=4)[0]
    source_n = tile_n + pad_n
    dtype = _random_dtype()
    source_space, target_space = random_memory_spaces(2, unique=False)
    dtype_ir = numeric_type_ir(dtype)
    target_ir = f"!nn.memory<[#C{tile_n}], [#C1], {dtype_ir}, #nn.space<{memory_space_ir_name(target_space)}>>"
    source_ir = f"!nn.memory<[#C{source_n}], [#C1], {dtype_ir}, #nn.space<{memory_space_ir_name(source_space)}>>"
    offset_type = symbol_int_type_ir(0)
    size_type = symbol_int_type_ir(tile_n)
    stride_type = symbol_int_type_ir(1)
    target_space_cpp = _space_enum_name(target_space)
    source_space_cpp = _space_enum_name(source_space)
    dtype_cpp = _cpp_type_name(dtype)
    alias_defs = f"""#C{source_n} = #symbol.expr<{source_n}>
#C{tile_n} = #symbol.expr<{tile_n}>
#C1 = #symbol.expr<1>
"""
    case_text = f"""// COMPILE_ARGS: --pass no-op
// CASE: 静态 1D dma.slice 应生成 slice(ctx, dst, source, offset, size, stride) helper。
// CHECK: template <typename Context>
// CHECK: void dma_slice_case(Context& ctx,
// CHECK: slice(ctx,

{alias_defs}
builtin.module {{
  func.func @dma_slice_case(
    %ctx : index {{name = "ctx"}},
    %0 : {target_ir},
    %1 : {source_ir},
    %2 : {offset_type},
    %3 : {size_type},
    %4 : {stride_type}
  ) {{
    "dma.slice"(%0, %1, %2, %3, %4) <{{operandSegmentSizes = array<i32: 1, 1, 1, 1, 1>}}> : ({target_ir}, {source_ir}, {offset_type}, {size_type}, {stride_type}) -> ()
    func.return
  }}
}}"""


    print_case_input_ir(
        "emit_c-npu_demo-dma-slice-static",
        case_text,
        fallback="emit_c-npu_demo-dma-slice-static",
    )
    run_emitc_case(
        case_text,
        source_path="expectation/dsl/emit_c/npu_demo/dma/slice.py#static",
        op_name="dma.slice",
        expected_snippets=[
            "template <typename Context>\nvoid dma_slice_case(Context& ctx,",
            f"Memory<{target_space_cpp}, {dtype_cpp}>",
            "slice(ctx,",
            "{",
        ],
        forbidden_snippets=["dma.slice", "Vector(", "static_cast<long long>"],
    )


def _case_dma_slice_symbol_const_body() -> None:
    """运行 rank-3 `symbol.const` 参数 `dma.slice` expectation。"""

    tile_d0, tile_d1, tile_d2 = random_static_dims(3, min_value=2, max_value=6)
    pad_d0, pad_d1, pad_d2 = random_static_dims(3, min_value=1, max_value=4)
    source_d0 = tile_d0 + pad_d0
    source_d1 = tile_d1 + pad_d1
    source_d2 = tile_d2 + pad_d2
    dtype = _random_dtype()
    source_space, target_space = random_memory_spaces(2, unique=False)
    dtype_ir = numeric_type_ir(dtype)
    target_ir = f"!nn.memory<[#C_TILE_D0, #C_TILE_D1, #C_TILE_D2], [#S1, #C_TILE_D2, #C1], {dtype_ir}, #nn.space<{memory_space_ir_name(target_space)}>>"
    source_ir = f"!nn.memory<[#C_SOURCE_D0, #C_SOURCE_D1, #C_SOURCE_D2], [#S2, #C_SOURCE_D2, #C1], {dtype_ir}, #nn.space<{memory_space_ir_name(source_space)}>>"
    zero_type = symbol_int_type_ir(0)
    one_type = symbol_int_type_ir(1)
    size_types = tuple(symbol_int_type_ir(value) for value in (tile_d0, tile_d1, tile_d2))
    alias_defs = f"""#C_TILE_D0 = #symbol.expr<{tile_d0}>
#C_TILE_D1 = #symbol.expr<{tile_d1}>
#C_TILE_D2 = #symbol.expr<{tile_d2}>
#C_SOURCE_D0 = #symbol.expr<{source_d0}>
#C_SOURCE_D1 = #symbol.expr<{source_d1}>
#C_SOURCE_D2 = #symbol.expr<{source_d2}>
#S1 = #symbol.expr<{tile_d1} * {tile_d2}>
#S2 = #symbol.expr<{source_d1} * {source_d2}>
#C1 = #symbol.expr<1>
"""
    case_text = f"""// COMPILE_ARGS: --pass no-op
// CASE: rank-3 symbol.const 参数的 dma.slice 应先 materialize 再生成 slice(...)。
// CHECK: template <typename Context>
// CHECK: void dma_slice_symbol_const_case(Context& ctx,
// CHECK: slice(ctx,

{alias_defs}
builtin.module {{
  func.func @dma_slice_symbol_const_case(
    %ctx : index {{name = "ctx"}},
    %0 : {target_ir},
    %1 : {source_ir}
  ) {{
    %2 = symbol.const 0 : {zero_type}
    %3 = symbol.const 0 : {zero_type}
    %4 = symbol.const 0 : {zero_type}
    %5 = symbol.const {tile_d0} : {size_types[0]}
    %6 = symbol.const {tile_d1} : {size_types[1]}
    %7 = symbol.const {tile_d2} : {size_types[2]}
    %8 = symbol.const 1 : {one_type}
    %9 = symbol.const 1 : {one_type}
    %10 = symbol.const 1 : {one_type}
    "dma.slice"(%0, %1, %2, %3, %4, %5, %6, %7, %8, %9, %10) <{{operandSegmentSizes = array<i32: 1, 1, 3, 3, 3>}}> : ({target_ir}, {source_ir}, {zero_type}, {zero_type}, {zero_type}, {size_types[0]}, {size_types[1]}, {size_types[2]}, {one_type}, {one_type}, {one_type}) -> ()
    func.return
  }}
}}"""


    print_case_input_ir(
        "emit_c-npu_demo-dma-slice-symbol-body-rank3",
        case_text,
        fallback="emit_c-npu_demo-dma-slice-symbol-body-rank3",
    )
    run_emitc_case(
        case_text,
        source_path="expectation/dsl/emit_c/npu_demo/dma/slice.py#symbol_const_body",
        op_name="dma.slice.symbol_const",
        expected_snippets=[
            "template <typename Context>\nvoid dma_slice_symbol_const_case(Context& ctx,",
            "slice(ctx,",
            "{",
        ],
        forbidden_snippets=["dma.slice", "Vector(", "static_cast<long long>"],
    )


def _case_dma_slice_symbol_args() -> None:
    """运行 rank-3 动态参数直传 `dma.slice` expectation。"""

    dyn_tile_d0, dyn_tile_d1, dyn_tile_d2 = random_symbol_names(3)
    dyn_source_d0, dyn_source_d1, dyn_source_d2 = random_symbol_names(3)
    dyn_offset_0, dyn_offset_1, dyn_offset_2 = random_symbol_names(3)
    dyn_stride_0, dyn_stride_1, dyn_stride_2 = random_symbol_names(3)
    dtype = _random_dtype()
    source_space, target_space = random_memory_spaces(2, unique=False)
    dtype_ir = numeric_type_ir(dtype)
    target_ir = f"!nn.memory<[#S_TILE_D0, #S_TILE_D1, #S_TILE_D2], [#S1, #S_TILE_D2, #C1], {dtype_ir}, #nn.space<{memory_space_ir_name(target_space)}>>"
    source_ir = f"!nn.memory<[#S_SOURCE_D0, #S_SOURCE_D1, #S_SOURCE_D2], [#S2, #S_SOURCE_D2, #C1], {dtype_ir}, #nn.space<{memory_space_ir_name(source_space)}>>"
    offset_types = tuple(symbol_int_type_ir(symbol) for symbol in (dyn_offset_0, dyn_offset_1, dyn_offset_2))
    size_types = tuple(symbol_int_type_ir(symbol) for symbol in (dyn_tile_d0, dyn_tile_d1, dyn_tile_d2))
    stride_types = tuple(symbol_int_type_ir(symbol) for symbol in (dyn_stride_0, dyn_stride_1, dyn_stride_2))
    alias_defs = f"""#S_TILE_D0 = #symbol.expr<{dyn_tile_d0}>
#S_TILE_D1 = #symbol.expr<{dyn_tile_d1}>
#S_TILE_D2 = #symbol.expr<{dyn_tile_d2}>
#S_SOURCE_D0 = #symbol.expr<{dyn_source_d0}>
#S_SOURCE_D1 = #symbol.expr<{dyn_source_d1}>
#S_SOURCE_D2 = #symbol.expr<{dyn_source_d2}>
#S1 = #symbol.expr<{dyn_tile_d1} * {dyn_tile_d2}>
#S2 = #symbol.expr<{dyn_source_d1} * {dyn_source_d2}>
#C1 = #symbol.expr<1>
"""
    case_text = f"""// COMPILE_ARGS: --pass no-op
// CASE: rank-3 动态 symbol.int 参数应从函数参数直传到 dma.slice。
// CHECK: template <typename Context>
// CHECK: void dma_slice_symbol_arg_case(Context& ctx,
// CHECK: slice(ctx,

{alias_defs}
builtin.module {{
  func.func @dma_slice_symbol_arg_case(
    %ctx : index {{name = "ctx"}},
    %0 : {target_ir},
    %1 : {source_ir},
    %2 : {offset_types[0]},
    %3 : {offset_types[1]},
    %4 : {offset_types[2]},
    %5 : {size_types[0]},
    %6 : {size_types[1]},
    %7 : {size_types[2]},
    %8 : {stride_types[0]},
    %9 : {stride_types[1]},
    %10 : {stride_types[2]}
  ) {{
    "dma.slice"(%0, %1, %2, %3, %4, %5, %6, %7, %8, %9, %10) <{{operandSegmentSizes = array<i32: 1, 1, 3, 3, 3>}}> : ({target_ir}, {source_ir}, {offset_types[0]}, {offset_types[1]}, {offset_types[2]}, {size_types[0]}, {size_types[1]}, {size_types[2]}, {stride_types[0]}, {stride_types[1]}, {stride_types[2]}) -> ()
    func.return
  }}
}}"""


    print_case_input_ir(
        "emit_c-npu_demo-dma-slice-symbol-args-rank3",
        case_text,
        fallback="emit_c-npu_demo-dma-slice-symbol-args-rank3",
    )
    run_emitc_case(
        case_text,
        source_path="expectation/dsl/emit_c/npu_demo/dma/slice.py#symbol_args",
        op_name="dma.slice.symbol_args",
        expected_snippets=[
            "template <typename Context>\nvoid dma_slice_symbol_arg_case(Context& ctx,",
            "slice(ctx,",
            "{",
        ],
        forbidden_snippets=["dma.slice", "Vector(", "static_cast<long long>"],
    )


def _case_dma_slice_symbol_add_args() -> None:
    """运行 rank-3 `symbol.add` 参数 `dma.slice` expectation。"""

    add_arg_symbols = random_symbol_names(18)
    add_arg_types = tuple(symbol_int_type_ir(symbol) for symbol in add_arg_symbols)
    add_result_types = tuple(
        symbol_int_type_ir(f"{lhs} + {rhs}")
        for lhs, rhs in (
            (add_arg_symbols[0], add_arg_symbols[1]),
            (add_arg_symbols[2], add_arg_symbols[3]),
            (add_arg_symbols[4], add_arg_symbols[5]),
            (add_arg_symbols[6], add_arg_symbols[7]),
            (add_arg_symbols[8], add_arg_symbols[9]),
            (add_arg_symbols[10], add_arg_symbols[11]),
            (add_arg_symbols[12], add_arg_symbols[13]),
            (add_arg_symbols[14], add_arg_symbols[15]),
            (add_arg_symbols[16], add_arg_symbols[17]),
        )
    )
    dyn_tile_d0, dyn_tile_d1, dyn_tile_d2 = random_symbol_names(3)
    dyn_source_d0, dyn_source_d1, dyn_source_d2 = random_symbol_names(3)
    dtype = _random_dtype()
    source_space, target_space = random_memory_spaces(2, unique=False)
    dtype_ir = numeric_type_ir(dtype)
    target_ir = f"!nn.memory<[#S_TILE_D0, #S_TILE_D1, #S_TILE_D2], [#S1, #S_TILE_D2, #C1], {dtype_ir}, #nn.space<{memory_space_ir_name(target_space)}>>"
    source_ir = f"!nn.memory<[#S_SOURCE_D0, #S_SOURCE_D1, #S_SOURCE_D2], [#S2, #S_SOURCE_D2, #C1], {dtype_ir}, #nn.space<{memory_space_ir_name(source_space)}>>"
    alias_defs = f"""#S_TILE_D0 = #symbol.expr<{dyn_tile_d0}>
#S_TILE_D1 = #symbol.expr<{dyn_tile_d1}>
#S_TILE_D2 = #symbol.expr<{dyn_tile_d2}>
#S_SOURCE_D0 = #symbol.expr<{dyn_source_d0}>
#S_SOURCE_D1 = #symbol.expr<{dyn_source_d1}>
#S_SOURCE_D2 = #symbol.expr<{dyn_source_d2}>
#S1 = #symbol.expr<{dyn_tile_d1} * {dyn_tile_d2}>
#S2 = #symbol.expr<{dyn_source_d1} * {dyn_source_d2}>
#C1 = #symbol.expr<1>
"""
    case_text = f"""// COMPILE_ARGS: --pass no-op
// CASE: rank-3 symbol.add 结果应先 materialize，再传给 dma.slice。
// CHECK: template <typename Context>
// CHECK: void dma_slice_symbol_add_case(Context& ctx,
// CHECK: slice(ctx,

{alias_defs}
builtin.module {{
  func.func @dma_slice_symbol_add_case(
    %ctx : index {{name = "ctx"}},
    %0 : {target_ir},
    %1 : {source_ir},
    %2 : {add_arg_types[0]},
    %3 : {add_arg_types[1]},
    %4 : {add_arg_types[2]},
    %5 : {add_arg_types[3]},
    %6 : {add_arg_types[4]},
    %7 : {add_arg_types[5]},
    %8 : {add_arg_types[6]},
    %9 : {add_arg_types[7]},
    %10 : {add_arg_types[8]},
    %11 : {add_arg_types[9]},
    %12 : {add_arg_types[10]},
    %13 : {add_arg_types[11]},
    %14 : {add_arg_types[12]},
    %15 : {add_arg_types[13]},
    %16 : {add_arg_types[14]},
    %17 : {add_arg_types[15]},
    %18 : {add_arg_types[16]},
    %19 : {add_arg_types[17]}
  ) {{
    %20 = "symbol.add"(%2, %3) : ({add_arg_types[0]}, {add_arg_types[1]}) -> {add_result_types[0]}
    %21 = "symbol.add"(%4, %5) : ({add_arg_types[2]}, {add_arg_types[3]}) -> {add_result_types[1]}
    %22 = "symbol.add"(%6, %7) : ({add_arg_types[4]}, {add_arg_types[5]}) -> {add_result_types[2]}
    %23 = "symbol.add"(%8, %9) : ({add_arg_types[6]}, {add_arg_types[7]}) -> {add_result_types[3]}
    %24 = "symbol.add"(%10, %11) : ({add_arg_types[8]}, {add_arg_types[9]}) -> {add_result_types[4]}
    %25 = "symbol.add"(%12, %13) : ({add_arg_types[10]}, {add_arg_types[11]}) -> {add_result_types[5]}
    %26 = "symbol.add"(%14, %15) : ({add_arg_types[12]}, {add_arg_types[13]}) -> {add_result_types[6]}
    %27 = "symbol.add"(%16, %17) : ({add_arg_types[14]}, {add_arg_types[15]}) -> {add_result_types[7]}
    %28 = "symbol.add"(%18, %19) : ({add_arg_types[16]}, {add_arg_types[17]}) -> {add_result_types[8]}
    "dma.slice"(%0, %1, %20, %21, %22, %23, %24, %25, %26, %27, %28) <{{operandSegmentSizes = array<i32: 1, 1, 3, 3, 3>}}> : ({target_ir}, {source_ir}, {add_result_types[0]}, {add_result_types[1]}, {add_result_types[2]}, {add_result_types[3]}, {add_result_types[4]}, {add_result_types[5]}, {add_result_types[6]}, {add_result_types[7]}, {add_result_types[8]}) -> ()
    func.return
  }}
}}"""


    print_case_input_ir(
        "emit_c-npu_demo-dma-slice-symbol-add-args-rank3",
        case_text,
        fallback="emit_c-npu_demo-dma-slice-symbol-add-args-rank3",
    )
    run_emitc_case(
        case_text,
        source_path="expectation/dsl/emit_c/npu_demo/dma/slice.py#symbol_add_args",
        op_name="dma.slice.symbol_add_args",
        expected_snippets=[
            "template <typename Context>\nvoid dma_slice_symbol_add_case(Context& ctx,",
            "slice(ctx,",
            "{",
        ],
        forbidden_snippets=["dma.slice", "Vector(", "static_cast<long long>"],
    )


def main() -> None:
    failures: list[tuple[str, BaseException]] = []
    run_case(failures, "emit_c-npu_demo-dma-slice-static", _case_dma_slice_static)
    run_case(failures, "emit_c-npu_demo-dma-slice-symbol-body-rank3", _case_dma_slice_symbol_const_body)
    run_case(failures, "emit_c-npu_demo-dma-slice-symbol-args-rank3", _case_dma_slice_symbol_args)
    run_case(failures, "emit_c-npu_demo-dma-slice-symbol-add-args-rank3", _case_dma_slice_symbol_add_args)
    raise_if_failures("emit_c npu_demo dma slice expectation", failures)


if __name__ == "__main__":
    main()
