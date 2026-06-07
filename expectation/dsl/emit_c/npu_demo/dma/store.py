# [immutable-file]
"""emit_c npu_demo dma expectation：store。

创建者: 榕
最后一次更改: 榕

功能说明:
- 为 `dma.store` 提供单独的 `emit_c` expectation。
- 锁定 `dma.store` 按目标规范生成显式 `target-first`、带模板参数的
  `store<TargetSpace, SourceSpace, TargetType, SourceType>(ctx, dst, source, ...)`。

使用示例:
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python expectation/dsl/emit_c/npu_demo/dma/store.py`

关联文件:
- spec: [`spec/dsl/emit_c.md`](spec/dsl/emit_c.md)
- spec: [`spec/tools/ircheck.md`](spec/tools/ircheck.md)
- spec: [`spec/include/api/Dma.md`](spec/include/api/Dma.md)
- test: [`test/dsl/test_emit_c.py`](test/dsl/test_emit_c.py)
- 功能实现: [`kernel_gen/tools/ircheck.py`](kernel_gen/tools/ircheck.py)
- 功能实现: [`expectation/dsl/emit_c/npu_demo/dma/store.py`](expectation/dsl/emit_c/npu_demo/dma/store.py)
"""

# Case 列表:
# - emit_c-npu_demo-dma-store-static: 静态 offset/size/stride 的 `dma.store` 应生成 `store<...>(ctx, dst, src, ...)`。
# - emit_c-npu_demo-dma-store-dynamic: 动态 symbol 参数的 `dma.store` 也应生成同口径 helper 调用。
# - emit_c-npu_demo-dma-store-symbol-add: `symbol.add` 结果作为 offset/size/stride 时，应先 materialize 再 `store<...>`。

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


def _case_dma_store_static() -> None:
    """运行静态 `dma.store` expectation。"""

    store_tile_m, store_tile_n = random_static_dims(2, min_value=2, max_value=4)
    store_target_m = store_tile_m + 2
    store_target_n = store_tile_n + 3
    store_offset_m = 1
    store_offset_n = 1
    store_stride = 1
    target_space, source_space = random_memory_spaces(2, unique=False)
    target_dtype, source_dtype = _random_dtype_pair()
    target_dtype_ir = numeric_type_ir(target_dtype)
    source_dtype_ir = numeric_type_ir(source_dtype)
    source_mem_type = f"!nn.memory<[#C_TILE_M, #C_TILE_N], [#C_TILE_N, #C1], {source_dtype_ir}, #nn.space<{memory_space_ir_name(source_space)}>>"
    target_mem_type = f"!nn.memory<[#C_TARGET_M, #C_TARGET_N], [#C_TARGET_N, #C1], {target_dtype_ir}, #nn.space<{memory_space_ir_name(target_space)}>>"
    store_offset_m_type = symbol_int_type_ir(store_offset_m)
    store_offset_n_type = symbol_int_type_ir(store_offset_n)
    store_size_m_type = symbol_int_type_ir(store_tile_m)
    store_size_n_type = symbol_int_type_ir(store_tile_n)
    store_stride_type = symbol_int_type_ir(store_stride)
    target_space_cpp = _space_enum_name(target_space)
    source_space_cpp = _space_enum_name(source_space)
    target_dtype_cpp = _cpp_type_name(target_dtype)
    source_dtype_cpp = _cpp_type_name(source_dtype)
    alias_defs = f"""#C_TILE_M = #symbol.expr<{store_tile_m}>
#C_TILE_N = #symbol.expr<{store_tile_n}>
#C_TARGET_M = #symbol.expr<{store_target_m}>
#C_TARGET_N = #symbol.expr<{store_target_n}>
#C1 = #symbol.expr<1>
"""
    case_text = f"""// COMPILE_ARGS: --pass no-op
// CHECK: template <typename Context>
// CHECK: void dma_store_case(Context& ctx, Memory<{target_space_cpp}, {target_dtype_cpp}>& [[DST:{{val}}]], Memory<{source_space_cpp}, {source_dtype_cpp}>& [[SRC:{{val}}]]) {{
// CHECK-NEXT:     S_INT [[OFFSET1_LOCAL:{{val}}]] = {store_offset_m};
// CHECK-NEXT:     S_INT [[OFFSET2_LOCAL:{{val}}]] = {store_offset_n};
// CHECK-NEXT:     S_INT [[SIZE1_LOCAL:{{val}}]] = {store_tile_m};
// CHECK-NEXT:     S_INT [[SIZE2_LOCAL:{{val}}]] = {store_tile_n};
// CHECK-NEXT:     S_INT [[STRIDE1_LOCAL:{{val}}]] = {store_stride};
// CHECK-NEXT:     S_INT [[STRIDE2_LOCAL:{{val}}]] = {store_stride};
// CHECK-NEXT:     store<{target_space_cpp}, {source_space_cpp}, {target_dtype_cpp}, {source_dtype_cpp}>(ctx, [[DST]] /*dst*/, [[SRC]] /*source*/, {{[[OFFSET1_LOCAL]], [[OFFSET2_LOCAL]]}} /*offset*/, {{[[SIZE1_LOCAL]], [[SIZE2_LOCAL]]}} /*size*/, {{[[STRIDE1_LOCAL]], [[STRIDE2_LOCAL]]}} /*stride*/);
// CHECK-NEXT: }}

{alias_defs}
builtin.module {{
  func.func @dma_store_case(
    %ctx : index {{name = "ctx"}},
    %0 : {target_mem_type},
    %1 : {source_mem_type}
  ) {{
    %2 = symbol.const {store_offset_m} : {store_offset_m_type}
    %3 = symbol.const {store_offset_n} : {store_offset_n_type}
    %4 = symbol.const {store_tile_m} : {store_size_m_type}
    %5 = symbol.const {store_tile_n} : {store_size_n_type}
    %6 = symbol.const {store_stride} : {store_stride_type}
    %7 = symbol.const {store_stride} : {store_stride_type}
    "dma.store"(%0, %1, %2, %3, %4, %5, %6, %7) <{{operandSegmentSizes = array<i32: 1, 1, 2, 2, 2>}}> : ({target_mem_type}, {source_mem_type}, {store_offset_m_type}, {store_offset_n_type}, {store_size_m_type}, {store_size_n_type}, {store_stride_type}, {store_stride_type}) -> ()
    func.return
  }}
}}"""


    print_case_input_ir(
        "emit_c-npu_demo-dma-store-static",
        case_text,
        fallback="emit_c-npu_demo-dma-store-static",
    )
    run_emitc_case(
        case_text,
        source_path="expectation/dsl/emit_c/npu_demo/dma/store.py",
        op_name="dma.store",
        expected_snippets=[
            "template <typename Context>\nvoid dma_store_case(Context& ctx,",
            f"store<{target_space_cpp}, {source_space_cpp}, {target_dtype_cpp}, {source_dtype_cpp}>(ctx,",
            "{",
        ],
        forbidden_snippets=["dma.store", "Vector(", "static_cast<long long>"],
    )


def _case_dma_store_dynamic() -> None:
    """运行动态 symbol 参数 `dma.store` expectation。"""

    dyn_size_m, dyn_size_n, dyn_target_m, dyn_target_n, dyn_offset_m, dyn_offset_n, dyn_stride_m, dyn_stride_n = random_symbol_names(8)
    target_space, source_space = random_memory_spaces(2, unique=False)
    target_dtype, source_dtype = _random_dtype_pair()
    target_dtype_ir = numeric_type_ir(target_dtype)
    source_dtype_ir = numeric_type_ir(source_dtype)
    source_mem_type_dynamic = f"!nn.memory<[#S_SIZE_M, #S_SIZE_N], [#S_SIZE_N, #C1], {source_dtype_ir}, #nn.space<{memory_space_ir_name(source_space)}>>"
    target_mem_type_dynamic = f"!nn.memory<[#S_TARGET_M, #S_TARGET_N], [#S_TARGET_N, #C1], {target_dtype_ir}, #nn.space<{memory_space_ir_name(target_space)}>>"
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
#S_TARGET_M = #symbol.expr<{dyn_target_m}>
#S_TARGET_N = #symbol.expr<{dyn_target_n}>
#C1 = #symbol.expr<1>
"""
    case_text = f"""// COMPILE_ARGS: --pass no-op
// CHECK: template <typename Context>
// CHECK: void dma_store_dynamic_case(Context& ctx, Memory<{target_space_cpp}, {target_dtype_cpp}>& [[DST:{{val}}]], Memory<{source_space_cpp}, {source_dtype_cpp}>& [[SRC:{{val}}]], S_INT [[OFFSET1:{{val}}]], S_INT [[OFFSET2:{{val}}]], S_INT [[SIZE1:{{val}}]], S_INT [[SIZE2:{{val}}]], S_INT [[STRIDE1:{{val}}]], S_INT [[STRIDE2:{{val}}]]) {{
// CHECK-NEXT:     store<{target_space_cpp}, {source_space_cpp}, {target_dtype_cpp}, {source_dtype_cpp}>(ctx, [[DST]] /*dst*/, [[SRC]] /*source*/, {{[[OFFSET1]], [[OFFSET2]]}} /*offset*/, {{[[SIZE1]], [[SIZE2]]}} /*size*/, {{[[STRIDE1]], [[STRIDE2]]}} /*stride*/);
// CHECK-NEXT: }}

{alias_defs}
builtin.module {{
  func.func @dma_store_dynamic_case(
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
    "dma.store"(%0, %1, %2, %3, %4, %5, %6, %7) <{{operandSegmentSizes = array<i32: 1, 1, 2, 2, 2>}}> : ({target_mem_type_dynamic}, {source_mem_type_dynamic}, {dyn_offset_m_type}, {dyn_offset_n_type}, {dyn_size_m_type}, {dyn_size_n_type}, {dyn_stride_m_type}, {dyn_stride_n_type}) -> ()
    func.return
  }}
}}"""


    print_case_input_ir(
        "emit_c-npu_demo-dma-store-dynamic",
        case_text,
        fallback="emit_c-npu_demo-dma-store-dynamic",
    )
    run_emitc_case(
        case_text,
        source_path="expectation/dsl/emit_c/npu_demo/dma/store.py#dynamic",
        op_name="dma.store.dynamic",
        expected_snippets=[
            "template <typename Context>\nvoid dma_store_dynamic_case(Context& ctx,",
            f"store<{target_space_cpp}, {source_space_cpp}, {target_dtype_cpp}, {source_dtype_cpp}>(ctx,",
            "{",
        ],
        forbidden_snippets=["dma.store", "Vector(", "static_cast<long long>"],
    )


def _case_dma_store_symbol_add() -> None:
    """运行 `symbol.add` 参数的 `dma.store` expectation。"""

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
    dyn_size_m, dyn_size_n, dyn_target_m, dyn_target_n = random_symbol_names(4)
    target_space, source_space = random_memory_spaces(2, unique=False)
    target_dtype, source_dtype = _random_dtype_pair()
    target_dtype_ir = numeric_type_ir(target_dtype)
    source_dtype_ir = numeric_type_ir(source_dtype)
    source_mem_type_dynamic = f"!nn.memory<[#S_SIZE_M, #S_SIZE_N], [#S_SIZE_N, #C1], {source_dtype_ir}, #nn.space<{memory_space_ir_name(source_space)}>>"
    target_mem_type_dynamic = f"!nn.memory<[#S_TARGET_M, #S_TARGET_N], [#S_TARGET_N, #C1], {target_dtype_ir}, #nn.space<{memory_space_ir_name(target_space)}>>"
    target_space_cpp = _space_enum_name(target_space)
    source_space_cpp = _space_enum_name(source_space)
    target_dtype_cpp = _cpp_type_name(target_dtype)
    source_dtype_cpp = _cpp_type_name(source_dtype)
    alias_defs = f"""#S_SIZE_M = #symbol.expr<{dyn_size_m}>
#S_SIZE_N = #symbol.expr<{dyn_size_n}>
#S_TARGET_M = #symbol.expr<{dyn_target_m}>
#S_TARGET_N = #symbol.expr<{dyn_target_n}>
#C1 = #symbol.expr<1>
"""
    case_text = f"""// COMPILE_ARGS: --pass no-op
// CHECK: template <typename Context>
// CHECK: void dma_store_symbol_add_case(Context& ctx, Memory<{target_space_cpp}, {target_dtype_cpp}>& [[DST:{{val}}]], Memory<{source_space_cpp}, {source_dtype_cpp}>& [[SRC:{{val}}]], S_INT [[OFFSET1_BASE:{{val}}]], S_INT [[OFFSET1_DELTA:{{val}}]], S_INT [[OFFSET2_BASE:{{val}}]], S_INT [[OFFSET2_DELTA:{{val}}]], S_INT [[SIZE1_BASE:{{val}}]], S_INT [[SIZE1_DELTA:{{val}}]], S_INT [[SIZE2_BASE:{{val}}]], S_INT [[SIZE2_DELTA:{{val}}]], S_INT [[STRIDE1_BASE:{{val}}]], S_INT [[STRIDE1_DELTA:{{val}}]], S_INT [[STRIDE2_BASE:{{val}}]], S_INT [[STRIDE2_DELTA:{{val}}]]) {{
// CHECK-NEXT:     S_INT [[OFFSET1_LOCAL:{{val}}]] = ([[OFFSET1_BASE]] + [[OFFSET1_DELTA]]);
// CHECK-NEXT:     S_INT [[OFFSET2_LOCAL:{{val}}]] = ([[OFFSET2_BASE]] + [[OFFSET2_DELTA]]);
// CHECK-NEXT:     S_INT [[SIZE1_LOCAL:{{val}}]] = ([[SIZE1_BASE]] + [[SIZE1_DELTA]]);
// CHECK-NEXT:     S_INT [[SIZE2_LOCAL:{{val}}]] = ([[SIZE2_BASE]] + [[SIZE2_DELTA]]);
// CHECK-NEXT:     S_INT [[STRIDE1_LOCAL:{{val}}]] = ([[STRIDE1_BASE]] + [[STRIDE1_DELTA]]);
// CHECK-NEXT:     S_INT [[STRIDE2_LOCAL:{{val}}]] = ([[STRIDE2_BASE]] + [[STRIDE2_DELTA]]);
// CHECK-NEXT:     store<{target_space_cpp}, {source_space_cpp}, {target_dtype_cpp}, {source_dtype_cpp}>(ctx, [[DST]] /*dst*/, [[SRC]] /*source*/, {{[[OFFSET1_LOCAL]], [[OFFSET2_LOCAL]]}} /*offset*/, {{[[SIZE1_LOCAL]], [[SIZE2_LOCAL]]}} /*size*/, {{[[STRIDE1_LOCAL]], [[STRIDE2_LOCAL]]}} /*stride*/);
// CHECK-NEXT: }}

{alias_defs}
builtin.module {{
  func.func @dma_store_symbol_add_case(
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
    "dma.store"(%0, %1, %14, %15, %16, %17, %18, %19) <{{operandSegmentSizes = array<i32: 1, 1, 2, 2, 2>}}> : ({target_mem_type_dynamic}, {source_mem_type_dynamic}, {add_result_types[0]}, {add_result_types[1]}, {add_result_types[2]}, {add_result_types[3]}, {add_result_types[4]}, {add_result_types[5]}) -> ()
    func.return
  }}
}}"""


    print_case_input_ir(
        "emit_c-npu_demo-dma-store-symbol-add",
        case_text,
        fallback="emit_c-npu_demo-dma-store-symbol-add",
    )
    run_emitc_case(
        case_text,
        source_path="expectation/dsl/emit_c/npu_demo/dma/store.py#symbol_add",
        op_name="dma.store.symbol_add",
        expected_snippets=[
            "template <typename Context>\nvoid dma_store_symbol_add_case(Context& ctx,",
            f"store<{target_space_cpp}, {source_space_cpp}, {target_dtype_cpp}, {source_dtype_cpp}>(ctx,",
            "{",
        ],
        forbidden_snippets=["dma.store", "Vector(", "static_cast<long long>"],
    )


def main() -> None:
    failures: list[tuple[str, BaseException]] = []
    run_case(failures, "emit_c-npu_demo-dma-store-static", _case_dma_store_static)
    run_case(failures, "emit_c-npu_demo-dma-store-dynamic", _case_dma_store_dynamic)
    run_case(failures, "emit_c-npu_demo-dma-store-symbol-add", _case_dma_store_symbol_add)
    raise_if_failures("emit_c npu_demo dma store expectation", failures)


if __name__ == "__main__":
    main()
