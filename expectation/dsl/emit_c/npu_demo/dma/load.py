# [immutable-file]
"""emit_c npu_demo dma expectation：load。

创建者: 榕
最后一次更改: 榕

功能说明:
- 为 `dma.load` 提供单独的 `emit_c` expectation。
- 锁定 `dma.load` 按目标规范生成显式 `target-first`、带模板参数的
  `load<TargetSpace, SourceSpace, TargetType, SourceType>(ctx, dst, source, ...)`。
- 额外冻结 `target` 必须是连续布局 memory 的公开合同。

使用示例:
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python expectation/dsl/emit_c/npu_demo/dma/load.py`

关联文件:
- spec: [`spec/dsl/emit_c.md`](spec/dsl/emit_c.md)
- spec: [`spec/tools/ircheck.md`](spec/tools/ircheck.md)
- spec: [`spec/include/api/Dma.md`](spec/include/api/Dma.md)
- test: [`test/dsl/test_emit_c.py`](test/dsl/test_emit_c.py)
- 功能实现: [`kernel_gen/tools/ircheck.py`](kernel_gen/tools/ircheck.py)
- 功能实现: [`expectation/dsl/emit_c/npu_demo/dma/load.py`](expectation/dsl/emit_c/npu_demo/dma/load.py)
"""

# Case 列表:
# - emit_c-npu_demo-dma-load-static: 静态 offset/size/stride 的 `dma.load` 应生成 `load<...>(ctx, dst, src, ...)`。
# - emit_c-npu_demo-dma-load-dynamic: 动态 symbol 参数的 `dma.load` 也应生成同口径 helper 调用。
# - emit_c-npu_demo-dma-load-symbol-add: `symbol.add` 结果作为 offset/size/stride 时，应先 materialize 再 `load<...>`。

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


def _random_dtype_pair() -> tuple[NumericType, NumericType]:
    return get_random_arithmetic_numeric_types(
        2,
        exclude=(NumericType.Float16, NumericType.BFloat16),
        unique=False,
    )


def _case_dma_load_static() -> None:
    """运行静态 `dma.load` expectation。"""

    load_tile_m, load_tile_n = random_static_dims(2, min_value=2, max_value=4)
    load_source_m = load_tile_m + 2
    load_source_n = load_tile_n + 3
    load_offset_m = 1
    load_offset_n = 1
    load_stride = 1
    target_space, source_space = random_memory_spaces(2, unique=False)
    target_dtype, source_dtype = _random_dtype_pair()
    target_dtype_ir = numeric_type_ir(target_dtype)
    source_dtype_ir = numeric_type_ir(source_dtype)
    target_mem_type = f"!nn.memory<[#C_TILE_M, #C_TILE_N], [#C_TILE_N, #C1], {target_dtype_ir}, #nn.space<{memory_space_ir_name(target_space)}>>"
    source_mem_type = f"!nn.memory<[#C_SOURCE_M, #C_SOURCE_N], [#C_SOURCE_N, #C1], {source_dtype_ir}, #nn.space<{memory_space_ir_name(source_space)}>>"
    load_offset_m_type = symbol_int_type_ir(load_offset_m)
    load_offset_n_type = symbol_int_type_ir(load_offset_n)
    load_size_m_type = symbol_int_type_ir(load_tile_m)
    load_size_n_type = symbol_int_type_ir(load_tile_n)
    load_stride_type = symbol_int_type_ir(load_stride)
    target_space_cpp = _space_enum_name(target_space)
    source_space_cpp = _space_enum_name(source_space)
    target_dtype_cpp = _cpp_type_name(target_dtype)
    source_dtype_cpp = _cpp_type_name(source_dtype)
    alias_defs = f"""#C_TILE_M = #symbol.expr<{load_tile_m}>
#C_TILE_N = #symbol.expr<{load_tile_n}>
#C_SOURCE_M = #symbol.expr<{load_source_m}>
#C_SOURCE_N = #symbol.expr<{load_source_n}>
#C1 = #symbol.expr<1>
"""
    case_text = f"""// COMPILE_ARGS: --pass no-op
// CHECK: template <typename Context>
// CHECK: void dma_load_case(Context& ctx, Memory<{target_space_cpp}, {target_dtype_cpp}>& [[DST:{{val}}]], Memory<{source_space_cpp}, {source_dtype_cpp}>& [[SRC:{{val}}]]) {{
// CHECK-NEXT:     load<{target_space_cpp}, {source_space_cpp}, {target_dtype_cpp}, {source_dtype_cpp}>(ctx, [[DST]] /*dst*/, [[SRC]] /*source*/, {{{load_offset_m}, {load_offset_n}}} /*offset*/, {{{load_tile_m}, {load_tile_n}}} /*size*/, {{{load_stride}, {load_stride}}} /*stride*/);
// CHECK-NEXT: }}

{alias_defs}
builtin.module {{
  func.func @dma_load_case(
    %ctx : index {{name = "ctx"}},
    %0 : {target_mem_type},
    %1 : {source_mem_type}
  ) {{
    %2 = symbol.const {load_offset_m} : {load_offset_m_type}
    %3 = symbol.const {load_offset_n} : {load_offset_n_type}
    %4 = symbol.const {load_tile_m} : {load_size_m_type}
    %5 = symbol.const {load_tile_n} : {load_size_n_type}
    %6 = symbol.const {load_stride} : {load_stride_type}
    %7 = symbol.const {load_stride} : {load_stride_type}
    "dma.load"(%0, %1, %2, %3, %4, %5, %6, %7) <{{operandSegmentSizes = array<i32: 1, 1, 2, 2, 2>}}> : ({target_mem_type}, {source_mem_type}, {load_offset_m_type}, {load_offset_n_type}, {load_size_m_type}, {load_size_n_type}, {load_stride_type}, {load_stride_type}) -> ()
    func.return
  }}
}}"""


    print_case_input_ir(
        "emit_c-npu_demo-dma-load-static",
        case_text,
        fallback="emit_c-npu_demo-dma-load-static",
    )
    run_emitc_case(
        case_text,
        source_path="expectation/dsl/emit_c/npu_demo/dma/load.py",
        op_name="dma.load",
        expected_snippets=[
            "template <typename Context>\nvoid dma_load_case(Context& ctx,",
            f"load<{target_space_cpp}, {source_space_cpp}, {target_dtype_cpp}, {source_dtype_cpp}>(ctx,",
            "{",
        ],
        forbidden_snippets=["dma.load", "Vector(", "static_cast<long long>"],
    )


def _case_dma_load_dynamic() -> None:
    """运行动态 symbol 参数 `dma.load` expectation。"""

    dyn_size_m, dyn_size_n, dyn_source_m, dyn_source_n, dyn_offset_m, dyn_offset_n, dyn_stride_m, dyn_stride_n = random_symbol_names(8)
    target_space, source_space = random_memory_spaces(2, unique=False)
    target_dtype, source_dtype = _random_dtype_pair()
    target_dtype_ir = numeric_type_ir(target_dtype)
    source_dtype_ir = numeric_type_ir(source_dtype)
    target_mem_type_dynamic = f"!nn.memory<[#S_SIZE_M, #S_SIZE_N], [#S_SIZE_N, #C1], {target_dtype_ir}, #nn.space<{memory_space_ir_name(target_space)}>>"
    source_mem_type_dynamic = f"!nn.memory<[#S_SOURCE_M, #S_SOURCE_N], [#S_SOURCE_N, #C1], {source_dtype_ir}, #nn.space<{memory_space_ir_name(source_space)}>>"
    dyn_offset_m_type = symbol_int_type_ir(dyn_offset_m)
    dyn_offset_n_type = symbol_int_type_ir(dyn_offset_n)
    dyn_size_m_type = symbol_int_type_ir(dyn_size_m)
    dyn_size_n_type = symbol_int_type_ir(dyn_size_n)
    dyn_stride_m_type = symbol_int_type_ir(dyn_stride_m)
    dyn_stride_n_type = symbol_int_type_ir(dyn_stride_n)
    target_space_cpp = _space_enum_name(target_space)
    source_space_cpp = _space_enum_name(source_space)
    target_dtype_cpp = _cpp_type_name(target_dtype)
    source_dtype_cpp = _cpp_type_name(source_dtype)
    alias_defs = f"""#S_SIZE_M = #symbol.expr<{dyn_size_m}>
#S_SIZE_N = #symbol.expr<{dyn_size_n}>
#S_SOURCE_M = #symbol.expr<{dyn_source_m}>
#S_SOURCE_N = #symbol.expr<{dyn_source_n}>
#C1 = #symbol.expr<1>
"""
    case_text = f"""// COMPILE_ARGS: --pass no-op
// CHECK: template <typename Context>
// CHECK: void dma_load_dynamic_case(Context& ctx, Memory<{target_space_cpp}, {target_dtype_cpp}>& [[DST:{{val}}]], Memory<{source_space_cpp}, {source_dtype_cpp}>& [[SRC:{{val}}]], S_INT [[OFFSET1:{{val}}]], S_INT [[OFFSET2:{{val}}]], S_INT [[SIZE1:{{val}}]], S_INT [[SIZE2:{{val}}]], S_INT [[STRIDE1:{{val}}]], S_INT [[STRIDE2:{{val}}]]) {{
// CHECK-NEXT:     load<{target_space_cpp}, {source_space_cpp}, {target_dtype_cpp}, {source_dtype_cpp}>(ctx, [[DST]] /*dst*/, [[SRC]] /*source*/, {{[[OFFSET1]], [[OFFSET2]]}} /*offset*/, {{[[SIZE1]], [[SIZE2]]}} /*size*/, {{[[STRIDE1]], [[STRIDE2]]}} /*stride*/);
// CHECK-NEXT: }}

{alias_defs}
builtin.module {{
  func.func @dma_load_dynamic_case(
    %ctx : index {{name = "ctx"}},
    %0 : {target_mem_type_dynamic},
    %1 : {source_mem_type_dynamic},
    %2 : {dyn_offset_m_type},
    %3 : {dyn_offset_n_type},
    %4 : {dyn_size_m_type},
    %5 : {dyn_size_n_type},
    %6 : {dyn_stride_m_type},
    %7 : {dyn_stride_n_type}
  ) {{
    "dma.load"(%0, %1, %2, %3, %4, %5, %6, %7) <{{operandSegmentSizes = array<i32: 1, 1, 2, 2, 2>}}> : ({target_mem_type_dynamic}, {source_mem_type_dynamic}, {dyn_offset_m_type}, {dyn_offset_n_type}, {dyn_size_m_type}, {dyn_size_n_type}, {dyn_stride_m_type}, {dyn_stride_n_type}) -> ()
    func.return
  }}
}}"""


    print_case_input_ir(
        "emit_c-npu_demo-dma-load-dynamic",
        case_text,
        fallback="emit_c-npu_demo-dma-load-dynamic",
    )
    run_emitc_case(
        case_text,
        source_path="expectation/dsl/emit_c/npu_demo/dma/load.py#dynamic",
        op_name="dma.load.dynamic",
        expected_snippets=[
            "template <typename Context>\nvoid dma_load_dynamic_case(Context& ctx,",
            f"load<{target_space_cpp}, {source_space_cpp}, {target_dtype_cpp}, {source_dtype_cpp}>(ctx,",
            "{",
        ],
        forbidden_snippets=["dma.load", "Vector(", "static_cast<long long>"],
    )


def _case_dma_load_symbol_add() -> None:
    """运行 `symbol.add` 参数的 `dma.load` expectation。"""

    (
        add_offset_1_base,
        add_offset_1_delta,
        add_offset_2_base,
        add_offset_2_delta,
        add_size_1_base,
        add_size_1_delta,
        add_size_2_base,
        add_size_2_delta,
        add_stride_1_base,
        add_stride_1_delta,
        add_stride_2_base,
        add_stride_2_delta,
    ) = random_symbol_names(12)
    add_arg_symbols = (
        add_offset_1_base,
        add_offset_1_delta,
        add_offset_2_base,
        add_offset_2_delta,
        add_size_1_base,
        add_size_1_delta,
        add_size_2_base,
        add_size_2_delta,
        add_stride_1_base,
        add_stride_1_delta,
        add_stride_2_base,
        add_stride_2_delta,
    )
    add_arg_types = tuple(symbol_int_type_ir(symbol) for symbol in add_arg_symbols)
    add_result_types = tuple(
        symbol_int_type_ir(f"{lhs} + {rhs}")
        for lhs, rhs in (
            (add_offset_1_base, add_offset_1_delta),
            (add_offset_2_base, add_offset_2_delta),
            (add_size_1_base, add_size_1_delta),
            (add_size_2_base, add_size_2_delta),
            (add_stride_1_base, add_stride_1_delta),
            (add_stride_2_base, add_stride_2_delta),
        )
    )
    dyn_size_m, dyn_size_n, dyn_source_m, dyn_source_n = random_symbol_names(4)
    target_space, source_space = random_memory_spaces(2, unique=False)
    target_dtype, source_dtype = _random_dtype_pair()
    target_dtype_ir = numeric_type_ir(target_dtype)
    source_dtype_ir = numeric_type_ir(source_dtype)
    target_mem_type_dynamic = f"!nn.memory<[#S_SIZE_M, #S_SIZE_N], [#S_SIZE_N, #C1], {target_dtype_ir}, #nn.space<{memory_space_ir_name(target_space)}>>"
    source_mem_type_dynamic = f"!nn.memory<[#S_SOURCE_M, #S_SOURCE_N], [#S_SOURCE_N, #C1], {source_dtype_ir}, #nn.space<{memory_space_ir_name(source_space)}>>"
    target_space_cpp = _space_enum_name(target_space)
    source_space_cpp = _space_enum_name(source_space)
    target_dtype_cpp = _cpp_type_name(target_dtype)
    source_dtype_cpp = _cpp_type_name(source_dtype)
    alias_defs = f"""#S_SIZE_M = #symbol.expr<{dyn_size_m}>
#S_SIZE_N = #symbol.expr<{dyn_size_n}>
#S_SOURCE_M = #symbol.expr<{dyn_source_m}>
#S_SOURCE_N = #symbol.expr<{dyn_source_n}>
#C1 = #symbol.expr<1>
"""
    case_text = f"""// COMPILE_ARGS: --pass no-op
// CHECK: template <typename Context>
// CHECK: void dma_load_symbol_add_case(Context& ctx, Memory<{target_space_cpp}, {target_dtype_cpp}>& [[DST:{{val}}]], Memory<{source_space_cpp}, {source_dtype_cpp}>& [[SRC:{{val}}]], S_INT [[OFFSET1_BASE:{{val}}]], S_INT [[OFFSET1_DELTA:{{val}}]], S_INT [[OFFSET2_BASE:{{val}}]], S_INT [[OFFSET2_DELTA:{{val}}]], S_INT [[SIZE1_BASE:{{val}}]], S_INT [[SIZE1_DELTA:{{val}}]], S_INT [[SIZE2_BASE:{{val}}]], S_INT [[SIZE2_DELTA:{{val}}]], S_INT [[STRIDE1_BASE:{{val}}]], S_INT [[STRIDE1_DELTA:{{val}}]], S_INT [[STRIDE2_BASE:{{val}}]], S_INT [[STRIDE2_DELTA:{{val}}]]) {{
// CHECK-NEXT:     S_INT [[OFFSET1_LOCAL:{{val}}]] = ([[OFFSET1_BASE]] + [[OFFSET1_DELTA]]);
// CHECK-NEXT:     S_INT [[OFFSET2_LOCAL:{{val}}]] = ([[OFFSET2_BASE]] + [[OFFSET2_DELTA]]);
// CHECK-NEXT:     S_INT [[SIZE1_LOCAL:{{val}}]] = ([[SIZE1_BASE]] + [[SIZE1_DELTA]]);
// CHECK-NEXT:     S_INT [[SIZE2_LOCAL:{{val}}]] = ([[SIZE2_BASE]] + [[SIZE2_DELTA]]);
// CHECK-NEXT:     S_INT [[STRIDE1_LOCAL:{{val}}]] = ([[STRIDE1_BASE]] + [[STRIDE1_DELTA]]);
// CHECK-NEXT:     S_INT [[STRIDE2_LOCAL:{{val}}]] = ([[STRIDE2_BASE]] + [[STRIDE2_DELTA]]);
// CHECK-NEXT:     load<{target_space_cpp}, {source_space_cpp}, {target_dtype_cpp}, {source_dtype_cpp}>(ctx, [[DST]] /*dst*/, [[SRC]] /*source*/, {{[[OFFSET1_LOCAL]], [[OFFSET2_LOCAL]]}} /*offset*/, {{[[SIZE1_LOCAL]], [[SIZE2_LOCAL]]}} /*size*/, {{[[STRIDE1_LOCAL]], [[STRIDE2_LOCAL]]}} /*stride*/);
// CHECK-NEXT: }}

{alias_defs}
builtin.module {{
  func.func @dma_load_symbol_add_case(
    %ctx : index {{name = "ctx"}},
    %0 : {target_mem_type_dynamic},
    %1 : {source_mem_type_dynamic},
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
    %13 : {add_arg_types[11]}
  ) {{
    %14 = "symbol.add"(%2, %3) : ({add_arg_types[0]}, {add_arg_types[1]}) -> {add_result_types[0]}
    %15 = "symbol.add"(%4, %5) : ({add_arg_types[2]}, {add_arg_types[3]}) -> {add_result_types[1]}
    %16 = "symbol.add"(%6, %7) : ({add_arg_types[4]}, {add_arg_types[5]}) -> {add_result_types[2]}
    %17 = "symbol.add"(%8, %9) : ({add_arg_types[6]}, {add_arg_types[7]}) -> {add_result_types[3]}
    %18 = "symbol.add"(%10, %11) : ({add_arg_types[8]}, {add_arg_types[9]}) -> {add_result_types[4]}
    %19 = "symbol.add"(%12, %13) : ({add_arg_types[10]}, {add_arg_types[11]}) -> {add_result_types[5]}
    "dma.load"(%0, %1, %14, %15, %16, %17, %18, %19) <{{operandSegmentSizes = array<i32: 1, 1, 2, 2, 2>}}> : ({target_mem_type_dynamic}, {source_mem_type_dynamic}, {add_result_types[0]}, {add_result_types[1]}, {add_result_types[2]}, {add_result_types[3]}, {add_result_types[4]}, {add_result_types[5]}) -> ()
    func.return
  }}
}}"""


    print_case_input_ir(
        "emit_c-npu_demo-dma-load-symbol-add",
        case_text,
        fallback="emit_c-npu_demo-dma-load-symbol-add",
    )
    run_emitc_case(
        case_text,
        source_path="expectation/dsl/emit_c/npu_demo/dma/load.py#symbol_add",
        op_name="dma.load.symbol_add",
        expected_snippets=[
            "template <typename Context>\nvoid dma_load_symbol_add_case(Context& ctx,",
            f"load<{target_space_cpp}, {source_space_cpp}, {target_dtype_cpp}, {source_dtype_cpp}>(ctx,",
            "{",
        ],
        forbidden_snippets=["dma.load", "Vector(", "static_cast<long long>"],
    )


def main() -> None:
    failures: list[tuple[str, BaseException]] = []
    run_case(failures, "emit_c-npu_demo-dma-load-static", _case_dma_load_static)
    run_case(failures, "emit_c-npu_demo-dma-load-dynamic", _case_dma_load_dynamic)
    run_case(failures, "emit_c-npu_demo-dma-load-symbol-add", _case_dma_load_symbol_add)
    raise_if_failures("emit_c npu_demo dma load expectation", failures)


if __name__ == "__main__":
    main()
