# [immutable-file]
"""emit_c npu_demo dma expectation：fill。

创建者: 榕
最后一次更改: 榕

功能说明:
- 为 `dma.fill` 提供单独的 `emit_c` expectation。
- 锁定 `symbol.const -> !symbol.int<...>` 在源码侧应先物化为 `S_INT` 常量绑定，
  再按随机目标 dtype 经通用 `symbol.cast` 对齐后生成
- `fill<Space, Type>(ctx, arg0, <cast-value-name>);`，其中 cast 临时变量名只按正则捕获，不强制具体命名。
- 同时覆盖动态值从 `func.func` 传入、参数类型为 `!symbol.int<...>` 的规范写法。

使用示例:
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python expectation/dsl/emit_c/npu_demo/dma/fill.py`

关联文件:
- spec: [`spec/dsl/emit_c.md`](spec/dsl/emit_c.md)
- spec: [`spec/tools/ircheck.md`](spec/tools/ircheck.md)
- spec: [`spec/include/api/Dma.md`](spec/include/api/Dma.md)
- test: [`test/dsl/test_emit_c.py`](test/dsl/test_emit_c.py)
- 功能实现: [`kernel_gen/tools/ircheck.py`](kernel_gen/tools/ircheck.py)
- 功能实现: [`expectation/dsl/emit_c/npu_demo/dma/fill.py`](expectation/dsl/emit_c/npu_demo/dma/fill.py)
"""

# Case 列表:
# - emit_c-npu_demo-dma-fill-static: 静态 `symbol.const -> symbol.cast -> dma.fill` 应先 materialize `S_INT` 常量，再生成 `fill<Space, Type>(ctx, dst, value);`。
# - emit_c-npu_demo-dma-fill-dynamic: 动态 `!symbol.int<...>` 参数经 `symbol.cast` 后也应生成同口径 `fill` 调用。

from __future__ import annotations

from pathlib import Path
import re
import sys

REPO_ROOT = next(parent for parent in Path(__file__).resolve().parents if (parent / "kernel_gen").exists())
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from expectation.utils.emitc import cpp_numeric_type_name, cpp_space_name
from kernel_gen.tools.emitc_case_runner import run_emitc_case
from expectation.utils.case_runner import print_case_input_ir, raise_if_failures, run_case
from expectation.utils.random_utils import (
    memory_space_ir_name,
    numeric_type_ir,
    random_memory_spaces,
    random_static_dims,
    random_symbol_names,
    symbol_int_type_ir,
)
from expectation.utils.random import get_random_arithmetic_numeric_type
from kernel_gen.symbol_variable.type import NumericType


def _case_dma_fill_static() -> None:
    """运行静态 `dma.fill` expectation。"""

    fill_value = 7
    static_m, static_n = random_static_dims(2, min_value=2, max_value=8)
    space = random_memory_spaces(1, unique=False)[0]
    space_cpp = cpp_space_name(space)
    space_ir = memory_space_ir_name(space)
    dtype = get_random_arithmetic_numeric_type(
        exclude=(NumericType.Float16, NumericType.BFloat16, NumericType.Float64),
    )
    dtype_ir = numeric_type_ir(dtype)
    dtype_cpp = cpp_numeric_type_name(dtype)
    fill_mem_type = f"!nn.memory<[#C_M, #C_N], [#C_N, #C1], {dtype_ir}, #nn.space<{space_ir}>>"
    fill_value_type = symbol_int_type_ir(fill_value)
    alias_defs = f"""#C_M = #symbol.expr<{static_m}>
#C_N = #symbol.expr<{static_n}>
#C1 = #symbol.expr<1>
"""
    case_text = f"""// COMPILE_ARGS: --pass no-op
// CHECK: template <typename Context>
// CHECK: void dma_fill_case(Context& ctx, Memory<{space_cpp}, {dtype_cpp}>& [[DST:{{val}}]]) {{
// CHECK-NEXT:     S_INT [[C_VALUE:{{val}}]] = {fill_value};
// CHECK-NEXT:     {dtype_cpp} [[CAST_VALUE:{{val}}]] = [[C_VALUE]];
// CHECK-NEXT:     fill<{space_cpp}, {dtype_cpp}>(ctx, [[DST]] /*dst*/, [[CAST_VALUE]] /*value*/);
// CHECK-NEXT: }}

{alias_defs}
builtin.module {{
  func.func @dma_fill_case(
    %ctx : index {{name = "ctx"}},
    %0 : {fill_mem_type}
  ) {{
    %1 = symbol.const {fill_value} : {fill_value_type}
    %2 = "symbol.cast"(%1) : ({fill_value_type}) -> {dtype_ir}
    "dma.fill"(%0, %2) : ({fill_mem_type}, {dtype_ir}) -> ()
    func.return
  }}
}}"""


    print_case_input_ir(
        "emit_c-npu_demo-dma-fill-static",
        case_text,
        fallback="emit_c-npu_demo-dma-fill-static",
    )
    source = run_emitc_case(
        case_text,
        source_path="expectation/dsl/emit_c/npu_demo/dma/fill.py",
        op_name="dma.fill",
        expected_snippets=[
            "template <typename Context>\nvoid dma_fill_case(Context& ctx,",
            "S_INT ",
            f"fill<{space_cpp}, {dtype_cpp}>(ctx,",
        ],
        forbidden_snippets=["dma.fill"],
    )
    const_match = re.search(
        rf"S_INT (?P<const_name>[A-Za-z_][A-Za-z0-9_]*) = {fill_value};",
        source,
    )
    assert const_match is not None, f"expected S_INT constant binding in source:\n{source}"
    c_value_name = const_match.group("const_name")
    match = re.search(
        rf"{re.escape(dtype_cpp)} (?P<cast_name>[A-Za-z_][A-Za-z0-9_]*) = {re.escape(c_value_name)};",
        source,
    )
    assert match is not None, f"expected cast binding from {c_value_name!r} in source:\n{source}"
    cast_name = match.group("cast_name")
    assert f"fill<{space_cpp}, {dtype_cpp}>(ctx," in source and f"{cast_name} /*value*/" in source, (
        f"expected fill to consume captured cast value {cast_name!r}\n{source}"
    )


def _case_dma_fill_dynamic() -> None:
    """运行动态 `dma.fill` expectation。"""

    dynamic_fill_name = random_symbol_names(1)[0]
    static_m, static_n = random_static_dims(2, min_value=2, max_value=8)
    space = random_memory_spaces(1, unique=False)[0]
    space_cpp = cpp_space_name(space)
    space_ir = memory_space_ir_name(space)
    dtype = get_random_arithmetic_numeric_type(
        exclude=(NumericType.Float16, NumericType.BFloat16, NumericType.Float64),
    )
    dtype_ir = numeric_type_ir(dtype)
    dtype_cpp = cpp_numeric_type_name(dtype)
    fill_mem_type = f"!nn.memory<[#C_M, #C_N], [#C_N, #C1], {dtype_ir}, #nn.space<{space_ir}>>"
    dynamic_fill_type = symbol_int_type_ir(dynamic_fill_name)
    alias_defs = f"""#C_M = #symbol.expr<{static_m}>
#C_N = #symbol.expr<{static_n}>
#C1 = #symbol.expr<1>
"""
    case_text = f"""// COMPILE_ARGS: --pass no-op
// CHECK: template <typename Context>
// CHECK: void dma_fill_dynamic_case(Context& ctx, Memory<{space_cpp}, {dtype_cpp}>& [[DST:{{val}}]], S_INT [[VALUE:{{val}}]]) {{
// CHECK-NEXT:     {dtype_cpp} [[CAST_VALUE:{{val}}]] = [[VALUE]];
// CHECK-NEXT:     fill<{space_cpp}, {dtype_cpp}>(ctx, [[DST]] /*dst*/, [[CAST_VALUE]] /*value*/);
// CHECK-NEXT: }}

{alias_defs}
builtin.module {{
  func.func @dma_fill_dynamic_case(
    %ctx : index {{name = "ctx"}},
    %0 : {fill_mem_type},
    %1 : {dynamic_fill_type}
  ) {{
    %2 = "symbol.cast"(%1) : ({dynamic_fill_type}) -> {dtype_ir}
    "dma.fill"(%0, %2) : ({fill_mem_type}, {dtype_ir}) -> ()
    func.return
  }}
}}"""


    print_case_input_ir(
        "emit_c-npu_demo-dma-fill-dynamic",
        case_text,
        fallback="emit_c-npu_demo-dma-fill-dynamic",
    )
    source = run_emitc_case(
        case_text,
        source_path="expectation/dsl/emit_c/npu_demo/dma/fill.py#dynamic",
        op_name="dma.fill.dynamic",
        expected_snippets=[
            "template <typename Context>\nvoid dma_fill_dynamic_case(Context& ctx,",
            f"{dtype_cpp} ",
            f"fill<{space_cpp}, {dtype_cpp}>(ctx,",
        ],
        forbidden_snippets=["dma.fill"],
    )
    match = re.search(
        rf"{re.escape(dtype_cpp)} (?P<cast_name>[A-Za-z_][A-Za-z0-9_]*) = [A-Za-z_][A-Za-z0-9_]*;",
        source,
    )
    assert match is not None, f"expected dynamic cast binding in source:\n{source}"
    cast_name = match.group("cast_name")
    assert f"fill<{space_cpp}, {dtype_cpp}>(ctx," in source and f"{cast_name} /*value*/" in source, (
        f"expected fill to consume captured cast value {cast_name!r}\n{source}"
    )


def main() -> None:
    """运行 `dma.fill` 的 emit_c expectation。"""

    failures: list[tuple[str, BaseException]] = []
    run_case(
        failures,
        "emit_c-npu_demo-dma-fill-static",
        _case_dma_fill_static,
    )
    run_case(
        failures,
        "emit_c-npu_demo-dma-fill-dynamic",
        _case_dma_fill_dynamic,
    )
    raise_if_failures("emit_c npu_demo dma fill expectation", failures)


if __name__ == "__main__":
    main()
