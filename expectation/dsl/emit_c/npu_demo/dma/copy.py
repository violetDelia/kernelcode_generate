# [immutable-file]
"""emit_c npu_demo dma expectation：copy。

创建者: 榕
最后一次更改: 榕

功能说明:
- 为 `dma.copy` 提供单独的 `emit_c` expectation。
- 锁定目标源码 helper 形态为公开 `slice(ctx, dst, source, offset, size, stride)` 搬运调用。
- `dma.copy` 的 `dst/src space` 由 `Memory<Space, Type>` 参数签名承接；`src/dst` 元素类型保持同一 `Type`，对齐公开 `slice(ctx, ...)` helper。

使用示例:
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python expectation/dsl/emit_c/npu_demo/dma/copy.py`

关联文件:
- spec: [`spec/dsl/gen_kernel/emit.md`](spec/dsl/gen_kernel/emit.md)
- spec: [`spec/dsl/gen_kernel/emit/npu_demo.md`](spec/dsl/gen_kernel/emit/npu_demo.md)
- spec: [`spec/tools/ircheck.md`](spec/tools/ircheck.md)
- spec: [`spec/include/api/Dma.md`](spec/include/api/Dma.md)
- test: [`test/dsl/test_emit_c.py`](test/dsl/test_emit_c.py)
- 功能实现: [`kernel_gen/tools/ircheck.py`](kernel_gen/tools/ircheck.py)
- 功能实现: [`expectation/dsl/emit_c/npu_demo/dma/copy.py`](expectation/dsl/emit_c/npu_demo/dma/copy.py)
"""

# Case 列表:
# - emit_c-npu_demo-dma-copy-static: 静态 shape 的 `dma.copy` 应生成公开 `slice(ctx, dst, source, offset, size, stride)` 搬运调用。
# - emit_c-npu_demo-dma-copy-dynamic: 动态 shape 的 `dma.copy` 也应生成同口径 `slice(ctx, ...)` 搬运调用。

from __future__ import annotations

from pathlib import Path
import sys

REPO_ROOT = next(parent for parent in Path(__file__).resolve().parents if (parent / "kernel_gen").exists())
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from expectation.utils.emitc import COMMON_MEMORY_SPACES, cpp_numeric_type_name, cpp_space_name
from kernel_gen.tools.emitc_case_runner import run_emitc_case
from expectation.utils.case_runner import print_case_input_ir, raise_if_failures, run_case
from expectation.utils.random_utils import memory_space_ir_name, numeric_type_ir, random_memory_spaces, random_static_dims, random_symbol_names
from expectation.utils.random import get_random_arithmetic_numeric_types
from kernel_gen.symbol_variable.type import NumericType


def _copy_types_and_spaces():
    src_space, dst_space = random_memory_spaces(2, unique=False)
    (dtype,) = get_random_arithmetic_numeric_types(
        1,
        exclude=(NumericType.Float16, NumericType.BFloat16),
    )
    return src_space, dst_space, dtype, dtype


def _case_dma_copy_static() -> None:
    """运行静态 `dma.copy` expectation。"""

    static_m, static_n = random_static_dims(2, min_value=2, max_value=8)
    src_space, dst_space, src_dtype, dst_dtype = _copy_types_and_spaces()
    src_space_cpp = cpp_space_name(src_space)
    dst_space_cpp = cpp_space_name(dst_space)
    src_space_ir = memory_space_ir_name(src_space)
    dst_space_ir = memory_space_ir_name(dst_space)
    src_dtype_cpp = cpp_numeric_type_name(src_dtype)
    dst_dtype_cpp = cpp_numeric_type_name(dst_dtype)
    src_mem_type = f"!nn.memory<[#C_M, #C_N], [#C_N, #C1], {numeric_type_ir(src_dtype)}, #nn.space<{src_space_ir}>>"
    dst_mem_type = f"!nn.memory<[#C_M, #C_N], [#C_N, #C1], {numeric_type_ir(dst_dtype)}, #nn.space<{dst_space_ir}>>"
    alias_defs = f"""#C_M = #symbol.expr<{static_m}>
#C_N = #symbol.expr<{static_n}>
#C1 = #symbol.expr<1>
"""
    case_text = f"""// COMPILE_ARGS: --pass no-op
// CHECK: template <typename Context>
// CHECK: void dma_copy_case(Context& ctx, Memory<{dst_space_cpp}, {dst_dtype_cpp}>& [[DST:{{val}}]], Memory<{src_space_cpp}, {src_dtype_cpp}>& [[SRC:{{val}}]]) {{
// CHECK-NEXT:     slice(ctx, [[DST]] /*dst*/, [[SRC]] /*source*/, {{0, 0}} /*offset*/, {{[[DST]].get_shape(0), [[DST]].get_shape(1)}} /*size*/, {{1, 1}} /*stride*/);
// CHECK-NEXT: }}

{alias_defs}
builtin.module {{
  func.func @dma_copy_case(
    %ctx : index {{name = "ctx"}},
    %0 : {dst_mem_type} {{name = "dst"}},
    %1 : {src_mem_type} {{name = "src"}}
  ) {{
    "dma.copy"(%0, %1) : ({dst_mem_type}, {src_mem_type}) -> ()
    func.return
  }}
}}"""


    print_case_input_ir(
        "emit_c-npu_demo-dma-copy-static",
        case_text,
        fallback="emit_c-npu_demo-dma-copy-static",
    )
    run_emitc_case(
        case_text,
        source_path="expectation/dsl/emit_c/npu_demo/dma/copy.py",
        op_name="dma.copy",
        expected_snippets=[
            "template <typename Context>\nvoid dma_copy_case(Context& ctx,",
            f"Memory<{dst_space_cpp}, {dst_dtype_cpp}>&",
            f"Memory<{src_space_cpp}, {src_dtype_cpp}>&",
            "slice(ctx,",
            "{",
            " /*dst*/, ",
            " /*source*/, ",
            "/*offset*/",
            "/*size*/",
            "/*stride*/",
        ],
        forbidden_snippets=[
            "dma.copy",
            "Vector(", "static_cast<long long>",
            "void dma_copy_case(Memory<",
            "slice(dst /*dst*/, src /*source*/",
        ],
    )


def _case_dma_copy_dynamic() -> None:
    """运行动态 `dma.copy` expectation。"""

    sym_m, sym_n = random_symbol_names(2)
    src_space, dst_space, src_dtype, dst_dtype = _copy_types_and_spaces()
    src_space_cpp = cpp_space_name(src_space)
    dst_space_cpp = cpp_space_name(dst_space)
    src_space_ir = memory_space_ir_name(src_space)
    dst_space_ir = memory_space_ir_name(dst_space)
    src_dtype_cpp = cpp_numeric_type_name(src_dtype)
    dst_dtype_cpp = cpp_numeric_type_name(dst_dtype)
    src_mem_type_dynamic = f"!nn.memory<[#S_M, #S_N], [#S_N, #C1], {numeric_type_ir(src_dtype)}, #nn.space<{src_space_ir}>>"
    dst_mem_type_dynamic = f"!nn.memory<[#S_M, #S_N], [#S_N, #C1], {numeric_type_ir(dst_dtype)}, #nn.space<{dst_space_ir}>>"
    alias_defs = f"""#S_M = #symbol.expr<{sym_m}>
#S_N = #symbol.expr<{sym_n}>
#C1 = #symbol.expr<1>
"""
    case_text = f"""// COMPILE_ARGS: --pass no-op
// CHECK: template <typename Context>
// CHECK: void dma_copy_dynamic_case(Context& ctx, Memory<{dst_space_cpp}, {dst_dtype_cpp}>& [[DST:{{val}}]], Memory<{src_space_cpp}, {src_dtype_cpp}>& [[SRC:{{val}}]]) {{
// CHECK-NEXT:     slice(ctx, [[DST]] /*dst*/, [[SRC]] /*source*/, {{0, 0}} /*offset*/, {{[[DST]].get_shape(0), [[DST]].get_shape(1)}} /*size*/, {{1, 1}} /*stride*/);
// CHECK-NEXT: }}

{alias_defs}
builtin.module {{
  func.func @dma_copy_dynamic_case(
    %ctx : index {{name = "ctx"}},
    %0 : {dst_mem_type_dynamic} {{name = "dst"}},
    %1 : {src_mem_type_dynamic} {{name = "src"}}
  ) {{
    "dma.copy"(%0, %1) : ({dst_mem_type_dynamic}, {src_mem_type_dynamic}) -> ()
    func.return
  }}
}}"""


    print_case_input_ir(
        "emit_c-npu_demo-dma-copy-dynamic",
        case_text,
        fallback="emit_c-npu_demo-dma-copy-dynamic",
    )
    run_emitc_case(
        case_text,
        source_path="expectation/dsl/emit_c/npu_demo/dma/copy.py#dynamic",
        op_name="dma.copy.dynamic",
        expected_snippets=[
            "template <typename Context>\nvoid dma_copy_dynamic_case(Context& ctx,",
            f"Memory<{dst_space_cpp}, {dst_dtype_cpp}>&",
            f"Memory<{src_space_cpp}, {src_dtype_cpp}>&",
            "slice(ctx,",
            "{",
            " /*dst*/, ",
            " /*source*/, ",
            "/*offset*/",
            "/*size*/",
            "/*stride*/",
        ],
        forbidden_snippets=[
            "dma.copy",
            "Vector(", "static_cast<long long>",
            "void dma_copy_dynamic_case(Memory<",
            "slice(dst /*dst*/, src /*source*/",
        ],
    )


def main() -> None:
    """运行 `dma.copy` 的 emit_c expectation。"""

    failures: list[tuple[str, BaseException]] = []
    run_case(
        failures,
        "emit_c-npu_demo-dma-copy-static",
        _case_dma_copy_static,
    )
    run_case(
        failures,
        "emit_c-npu_demo-dma-copy-dynamic",
        _case_dma_copy_dynamic,
    )
    raise_if_failures("emit_c npu_demo dma copy expectation", failures)


if __name__ == "__main__":
    main()
