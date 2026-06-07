# [immutable-file]
"""emit_c npu_demo kernel expectation：img2col family。

创建者: 榕
最后一次更改: 守护最好的爱莉希雅

功能说明:
- 使用 `emit_c(target="npu_demo")` 运行 `kernel.img2col1d` 与 `kernel.img2col2d` 的源码 expectation。
- 锁定输入 IR 为 `out-first` 的 `kernel.img2col1d/2d` 写入类 op。
- 覆盖静态 shape、动态 shape 与动态 `symbol.int` 参数三类合同。

使用示例:
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python expectation/dsl/emit_c/npu_demo/kernel/img2col.py`

关联文件:
- spec: [`spec/dsl/emit_c.md`](spec/dsl/emit_c.md)
- spec: [`spec/include/api/Kernel.md`](spec/include/api/Kernel.md)
- test: [`test/dsl/test_emit_c.py`](test/dsl/test_emit_c.py)
- 功能实现: [`kernel_gen/tools/emitc_case_runner.py`](kernel_gen/tools/emitc_case_runner.py)
- 功能实现: [`expectation/dsl/emit_c/npu_demo/kernel/img2col.py`](expectation/dsl/emit_c/npu_demo/kernel/img2col.py)
"""

# Case 列表:
# - emit_c-npu_demo-kernel-img2col1d-static: 静态 shape 的 `kernel.img2col1d` 应生成 `img2col1d<...>(ctx, out, input, ...)`。
# - emit_c-npu_demo-kernel-img2col1d-dynamic: 动态 shape 的 `kernel.img2col1d` 也应生成同口径 helper 调用。
# - emit_c-npu_demo-kernel-img2col1d-symbol-args: 动态 `symbol.int` 参数直传的 `kernel.img2col1d` 应生成同口径 helper 调用。
# - emit_c-npu_demo-kernel-img2col2d-static: 静态 shape 的 `kernel.img2col2d` 应生成 `img2col2d<...>(ctx, out, input, ...)`。
# - emit_c-npu_demo-kernel-img2col2d-dynamic: 动态 shape 的 `kernel.img2col2d` 也应生成同口径 helper 调用。
# - emit_c-npu_demo-kernel-img2col2d-symbol-args: 动态 `symbol.int` 参数直传的 `kernel.img2col2d` 应生成同口径 helper 调用。

from __future__ import annotations

from pathlib import Path
import sys

CURRENT_DIR = Path(__file__).resolve().parent
REPO_ROOT = next(parent for parent in Path(__file__).resolve().parents if (parent / "kernel_gen").exists())
sys.path = [path for path in sys.path if Path(path or ".").resolve() != CURRENT_DIR]
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


def _case_kernel_img2col1d_static() -> None:
    """运行静态 `kernel.img2col1d` expectation。"""

    static_n, static_c = random_static_dims(2, min_value=1, max_value=4)
    static_w = random_static_dims(1, min_value=6, max_value=16)[0]
    kernel_size, stride, dilation, pad_left, pad_right = 3, 2, 1, 1, 1
    static_ow = (static_w + pad_left + pad_right - dilation * (kernel_size - 1) - 1) // stride + 1
    dtype = _random_dtype()
    space = random_memory_spaces(1, unique=False)[0]
    dtype_ir = numeric_type_ir(dtype)
    space_ir = memory_space_ir_name(space)
    src_ir = f"!nn.memory<[#C_N, #C_C, #C_W], [#S1, #C_W, #C1], {dtype_ir}, #nn.space<{space_ir}>>"
    dst_ir = f"!nn.memory<[#C_N, #C_C, #C_K, #C_OW], [#S2, #S3, #C_OW, #C1], {dtype_ir}, #nn.space<{space_ir}>>"
    const_types = tuple(symbol_int_type_ir(value) for value in (kernel_size, stride, dilation, pad_left, pad_right))
    space_cpp = _space_enum_name(space)
    dtype_cpp = _cpp_type_name(dtype)
    alias_defs = f"""#C_N = #symbol.expr<{static_n}>
#C_C = #symbol.expr<{static_c}>
#C_W = #symbol.expr<{static_w}>
#C_K = #symbol.expr<{kernel_size}>
#C_OW = #symbol.expr<{static_ow}>
#S1 = #symbol.expr<{static_c} * {static_w}>
#S2 = #symbol.expr<{static_c} * {kernel_size} * {static_ow}>
#S3 = #symbol.expr<{kernel_size} * {static_ow}>
#C1 = #symbol.expr<1>
"""
    case_text = f"""// COMPILE_ARGS: --pass no-op
// CASE: 静态 shape 的 kernel.img2col1d 应生成 img2col1d<...>(ctx, out, input, ...) helper。
// CHECK: template <typename Context>
// CHECK: void kernel_img2col1d_case(Context& ctx,
// CHECK: img2col1d<

{alias_defs}
builtin.module {{
  func.func @kernel_img2col1d_case(
    %ctx : index {{name = "ctx"}},
    %0 : {dst_ir},
    %1 : {src_ir}
  ) {{
    %2 = symbol.const {kernel_size} : {const_types[0]}
    %3 = symbol.const {stride} : {const_types[1]}
    %4 = symbol.const {dilation} : {const_types[2]}
    %5 = symbol.const {pad_left} : {const_types[3]}
    %6 = symbol.const {pad_right} : {const_types[4]}
    "kernel.img2col1d"(%0, %1, %2, %3, %4, %5, %6) {{space = #nn.space<{space_ir}>}} : ({dst_ir}, {src_ir}, {const_types[0]}, {const_types[1]}, {const_types[2]}, {const_types[3]}, {const_types[4]}) -> ()
    func.return
  }}
}}"""
    print_case_input_ir(
        "emit_c-npu_demo-kernel-img2col1d-static",
        case_text,
        fallback="静态 shape 的 kernel.img2col1d 应生成 img2col1d helper 调用。",
    )

    run_emitc_case(
        case_text,
        source_path="expectation/dsl/emit_c/npu_demo/kernel/img2col.py#img2col1d_static",
        op_name="kernel.img2col1d",
        expected_snippets=[
            "template <typename Context>\nvoid kernel_img2col1d_case(Context& ctx,",
            f"img2col1d<{space_cpp}, {space_cpp}, {dtype_cpp}, {dtype_cpp}>(ctx,",
        ],
        forbidden_snippets=["kernel.img2col1d", "npu_demo::img2col1d"],
    )


def _case_kernel_img2col1d_dynamic() -> None:
    """运行动态 shape `kernel.img2col1d` expectation。"""

    sym_n, sym_c, sym_w, sym_ow = random_symbol_names(4)
    kernel_size, stride, dilation, pad_left, pad_right = 3, 2, 1, 1, 1
    dtype = _random_dtype()
    space = random_memory_spaces(1, unique=False)[0]
    dtype_ir = numeric_type_ir(dtype)
    space_ir = memory_space_ir_name(space)
    src_ir = f"!nn.memory<[#S_N, #S_C, #S_W], [#S1, #S_W, #C1], {dtype_ir}, #nn.space<{space_ir}>>"
    dst_ir = f"!nn.memory<[#S_N, #S_C, #C_K, #S_OW], [#S2, #S3, #S_OW, #C1], {dtype_ir}, #nn.space<{space_ir}>>"
    const_types = tuple(symbol_int_type_ir(value) for value in (kernel_size, stride, dilation, pad_left, pad_right))
    space_cpp = _space_enum_name(space)
    dtype_cpp = _cpp_type_name(dtype)
    alias_defs = f"""#S_N = #symbol.expr<{sym_n}>
#S_C = #symbol.expr<{sym_c}>
#S_W = #symbol.expr<{sym_w}>
#S_OW = #symbol.expr<{sym_ow}>
#C_K = #symbol.expr<{kernel_size}>
#S1 = #symbol.expr<{sym_c} * {sym_w}>
#S2 = #symbol.expr<{sym_c} * {kernel_size} * {sym_ow}>
#S3 = #symbol.expr<{kernel_size} * {sym_ow}>
#C1 = #symbol.expr<1>
"""
    case_text = f"""// COMPILE_ARGS: --pass no-op
// CASE: 动态 shape 的 kernel.img2col1d 也应生成 img2col1d<...>(ctx, out, input, ...) helper。
// CHECK: template <typename Context>
// CHECK: void kernel_img2col1d_dynamic_case(Context& ctx,
// CHECK: img2col1d<

{alias_defs}
builtin.module {{
  func.func @kernel_img2col1d_dynamic_case(
    %ctx : index {{name = "ctx"}},
    %0 : {dst_ir},
    %1 : {src_ir}
  ) {{
    %2 = symbol.const {kernel_size} : {const_types[0]}
    %3 = symbol.const {stride} : {const_types[1]}
    %4 = symbol.const {dilation} : {const_types[2]}
    %5 = symbol.const {pad_left} : {const_types[3]}
    %6 = symbol.const {pad_right} : {const_types[4]}
    "kernel.img2col1d"(%0, %1, %2, %3, %4, %5, %6) {{space = #nn.space<{space_ir}>}} : ({dst_ir}, {src_ir}, {const_types[0]}, {const_types[1]}, {const_types[2]}, {const_types[3]}, {const_types[4]}) -> ()
    func.return
  }}
}}"""
    print_case_input_ir(
        "emit_c-npu_demo-kernel-img2col1d-dynamic",
        case_text,
        fallback="动态 shape 的 kernel.img2col1d 应生成 img2col1d helper 调用。",
    )

    run_emitc_case(
        case_text,
        source_path="expectation/dsl/emit_c/npu_demo/kernel/img2col.py#img2col1d_dynamic",
        op_name="kernel.img2col1d.dynamic",
        expected_snippets=[
            "template <typename Context>\nvoid kernel_img2col1d_dynamic_case(Context& ctx,",
            f"img2col1d<{space_cpp}, {space_cpp}, {dtype_cpp}, {dtype_cpp}>(ctx,",
        ],
        forbidden_snippets=["kernel.img2col1d", "npu_demo::img2col1d"],
    )


def _case_kernel_img2col1d_symbol_args() -> None:
    """运行动态参数直传 `kernel.img2col1d` expectation。"""

    arg_n, arg_c, arg_w, arg_ow = random_symbol_names(4)
    arg_k, arg_s, arg_d, arg_pl, arg_pr = random_symbol_names(5)
    dtype = _random_dtype()
    space = random_memory_spaces(1, unique=False)[0]
    dtype_ir = numeric_type_ir(dtype)
    space_ir = memory_space_ir_name(space)
    src_ir = f"!nn.memory<[#S_N, #S_C, #S_W], [#S1, #S_W, #C1], {dtype_ir}, #nn.space<{space_ir}>>"
    dst_ir = f"!nn.memory<[#S_N, #S_C, #S_K, #S_OW], [#S2, #S3, #S_OW, #C1], {dtype_ir}, #nn.space<{space_ir}>>"
    arg_types = tuple(symbol_int_type_ir(value) for value in (arg_k, arg_s, arg_d, arg_pl, arg_pr))
    space_cpp = _space_enum_name(space)
    dtype_cpp = _cpp_type_name(dtype)
    alias_defs = f"""#S_N = #symbol.expr<{arg_n}>
#S_C = #symbol.expr<{arg_c}>
#S_W = #symbol.expr<{arg_w}>
#S_K = #symbol.expr<{arg_k}>
#S_OW = #symbol.expr<{arg_ow}>
#S1 = #symbol.expr<{arg_c} * {arg_w}>
#S2 = #symbol.expr<{arg_c} * {arg_k} * {arg_ow}>
#S3 = #symbol.expr<{arg_k} * {arg_ow}>
#C1 = #symbol.expr<1>
"""
    case_text = f"""// COMPILE_ARGS: --pass no-op
// CASE: 动态 symbol.int 参数应从函数参数直传到 kernel.img2col1d。
// CHECK: template <typename Context>
// CHECK: void kernel_img2col1d_symbol_arg_case(Context& ctx,
// CHECK: img2col1d<

{alias_defs}
builtin.module {{
  func.func @kernel_img2col1d_symbol_arg_case(
    %ctx : index {{name = "ctx"}},
    %0 : {dst_ir},
    %1 : {src_ir},
    %2 : {arg_types[0]},
    %3 : {arg_types[1]},
    %4 : {arg_types[2]},
    %5 : {arg_types[3]},
    %6 : {arg_types[4]}
  ) {{
    "kernel.img2col1d"(%0, %1, %2, %3, %4, %5, %6) {{space = #nn.space<{space_ir}>}} : ({dst_ir}, {src_ir}, {arg_types[0]}, {arg_types[1]}, {arg_types[2]}, {arg_types[3]}, {arg_types[4]}) -> ()
    func.return
  }}
}}"""
    print_case_input_ir(
        "emit_c-npu_demo-kernel-img2col1d-symbol-args",
        case_text,
        fallback="动态 symbol.int 参数直传的 kernel.img2col1d 应生成 img2col1d helper 调用。",
    )

    run_emitc_case(
        case_text,
        source_path="expectation/dsl/emit_c/npu_demo/kernel/img2col.py#img2col1d_symbol_args",
        op_name="kernel.img2col1d.symbol_args",
        expected_snippets=[
            "template <typename Context>\nvoid kernel_img2col1d_symbol_arg_case(Context& ctx,",
            f"img2col1d<{space_cpp}, {space_cpp}, {dtype_cpp}, {dtype_cpp}>(ctx,",
        ],
        forbidden_snippets=["kernel.img2col1d", "npu_demo::img2col1d"],
    )


def _case_kernel_img2col2d_static() -> None:
    """运行静态 `kernel.img2col2d` expectation。"""

    static_n, static_c = random_static_dims(2, min_value=1, max_value=4)
    static_h, static_w = random_static_dims(2, min_value=5, max_value=12)
    kh, kw, sh, sw, dh, dw, ph, pw, pl, pr = 3, 2, 1, 2, 1, 1, 1, 0, 0, 1
    static_oh = (static_h + ph + pw - dh * (kh - 1) - 1) // sh + 1
    static_ow = (static_w + pl + pr - dw * (kw - 1) - 1) // sw + 1
    dtype = _random_dtype()
    space = random_memory_spaces(1, unique=False)[0]
    dtype_ir = numeric_type_ir(dtype)
    space_ir = memory_space_ir_name(space)
    src_ir = f"!nn.memory<[#C_N, #C_C, #C_H, #C_W], [#S1, #S2, #C_W, #C1], {dtype_ir}, #nn.space<{space_ir}>>"
    dst_ir = f"!nn.memory<[#C_N, #C_C, #C_KH, #C_KW, #C_OH, #C_OW], [#S3, #S4, #S5, #S6, #C_OW, #C1], {dtype_ir}, #nn.space<{space_ir}>>"
    const_types = tuple(symbol_int_type_ir(value) for value in (kh, kw, sh, sw, dh, dw, ph, pw, pl, pr))
    space_cpp = _space_enum_name(space)
    dtype_cpp = _cpp_type_name(dtype)
    alias_defs = f"""#C_N = #symbol.expr<{static_n}>
#C_C = #symbol.expr<{static_c}>
#C_H = #symbol.expr<{static_h}>
#C_W = #symbol.expr<{static_w}>
#C_KH = #symbol.expr<{kh}>
#C_KW = #symbol.expr<{kw}>
#C_OH = #symbol.expr<{static_oh}>
#C_OW = #symbol.expr<{static_ow}>
#S1 = #symbol.expr<{static_c} * {static_h} * {static_w}>
#S2 = #symbol.expr<{static_h} * {static_w}>
#S3 = #symbol.expr<{static_c} * {kh} * {kw} * {static_oh} * {static_ow}>
#S4 = #symbol.expr<{kh} * {kw} * {static_oh} * {static_ow}>
#S5 = #symbol.expr<{kw} * {static_oh} * {static_ow}>
#S6 = #symbol.expr<{static_oh} * {static_ow}>
#C1 = #symbol.expr<1>
"""
    case_text = f"""// COMPILE_ARGS: --pass no-op
// CASE: 静态 shape 的 kernel.img2col2d 应生成 img2col2d<...>(ctx, out, input, ...) helper。
// CHECK: template <typename Context>
// CHECK: void kernel_img2col2d_case(Context& ctx,
// CHECK: img2col2d<

{alias_defs}
builtin.module {{
  func.func @kernel_img2col2d_case(
    %ctx : index {{name = "ctx"}},
    %0 : {dst_ir},
    %1 : {src_ir}
  ) {{
    %2 = symbol.const {kh} : {const_types[0]}
    %3 = symbol.const {kw} : {const_types[1]}
    %4 = symbol.const {sh} : {const_types[2]}
    %5 = symbol.const {sw} : {const_types[3]}
    %6 = symbol.const {dh} : {const_types[4]}
    %7 = symbol.const {dw} : {const_types[5]}
    %8 = symbol.const {ph} : {const_types[6]}
    %9 = symbol.const {pw} : {const_types[7]}
    %10 = symbol.const {pl} : {const_types[8]}
    %11 = symbol.const {pr} : {const_types[9]}
    "kernel.img2col2d"(%0, %1, %2, %3, %4, %5, %6, %7, %8, %9, %10, %11) {{space = #nn.space<{space_ir}>}} : ({dst_ir}, {src_ir}, {const_types[0]}, {const_types[1]}, {const_types[2]}, {const_types[3]}, {const_types[4]}, {const_types[5]}, {const_types[6]}, {const_types[7]}, {const_types[8]}, {const_types[9]}) -> ()
    func.return
  }}
}}"""
    print_case_input_ir(
        "emit_c-npu_demo-kernel-img2col2d-static",
        case_text,
        fallback="静态 shape 的 kernel.img2col2d 应生成 img2col2d helper 调用。",
    )

    run_emitc_case(
        case_text,
        source_path="expectation/dsl/emit_c/npu_demo/kernel/img2col.py#img2col2d_static",
        op_name="kernel.img2col2d",
        expected_snippets=[
            "template <typename Context>\nvoid kernel_img2col2d_case(Context& ctx,",
            f"img2col2d<{space_cpp}, {space_cpp}, {dtype_cpp}, {dtype_cpp}>(ctx,",
        ],
        forbidden_snippets=["kernel.img2col2d", "npu_demo::img2col2d"],
    )


def _case_kernel_img2col2d_dynamic() -> None:
    """运行动态 shape `kernel.img2col2d` expectation。"""

    sym_n, sym_c, sym_h, sym_w, sym_oh, sym_ow = random_symbol_names(6)
    kh, kw, sh, sw, dh, dw, ph, pw, pl, pr = 3, 2, 1, 2, 1, 1, 1, 0, 0, 1
    dtype = _random_dtype()
    space = random_memory_spaces(1, unique=False)[0]
    dtype_ir = numeric_type_ir(dtype)
    space_ir = memory_space_ir_name(space)
    src_ir = f"!nn.memory<[#S_N, #S_C, #S_H, #S_W], [#S1, #S2, #S_W, #C1], {dtype_ir}, #nn.space<{space_ir}>>"
    dst_ir = f"!nn.memory<[#S_N, #S_C, #C_KH, #C_KW, #S_OH, #S_OW], [#S3, #S4, #S5, #S6, #S_OW, #C1], {dtype_ir}, #nn.space<{space_ir}>>"
    const_types = tuple(symbol_int_type_ir(value) for value in (kh, kw, sh, sw, dh, dw, ph, pw, pl, pr))
    space_cpp = _space_enum_name(space)
    dtype_cpp = _cpp_type_name(dtype)
    alias_defs = f"""#S_N = #symbol.expr<{sym_n}>
#S_C = #symbol.expr<{sym_c}>
#S_H = #symbol.expr<{sym_h}>
#S_W = #symbol.expr<{sym_w}>
#S_OH = #symbol.expr<{sym_oh}>
#S_OW = #symbol.expr<{sym_ow}>
#C_KH = #symbol.expr<{kh}>
#C_KW = #symbol.expr<{kw}>
#S1 = #symbol.expr<{sym_c} * {sym_h} * {sym_w}>
#S2 = #symbol.expr<{sym_h} * {sym_w}>
#S3 = #symbol.expr<{sym_c} * {kh} * {kw} * {sym_oh} * {sym_ow}>
#S4 = #symbol.expr<{kh} * {kw} * {sym_oh} * {sym_ow}>
#S5 = #symbol.expr<{kw} * {sym_oh} * {sym_ow}>
#S6 = #symbol.expr<{sym_oh} * {sym_ow}>
#C1 = #symbol.expr<1>
"""
    case_text = f"""// COMPILE_ARGS: --pass no-op
// CASE: 动态 shape 的 kernel.img2col2d 也应生成 img2col2d<...>(ctx, out, input, ...) helper。
// CHECK: template <typename Context>
// CHECK: void kernel_img2col2d_dynamic_case(Context& ctx,
// CHECK: img2col2d<

{alias_defs}
builtin.module {{
  func.func @kernel_img2col2d_dynamic_case(
    %ctx : index {{name = "ctx"}},
    %0 : {dst_ir},
    %1 : {src_ir}
  ) {{
    %2 = symbol.const {kh} : {const_types[0]}
    %3 = symbol.const {kw} : {const_types[1]}
    %4 = symbol.const {sh} : {const_types[2]}
    %5 = symbol.const {sw} : {const_types[3]}
    %6 = symbol.const {dh} : {const_types[4]}
    %7 = symbol.const {dw} : {const_types[5]}
    %8 = symbol.const {ph} : {const_types[6]}
    %9 = symbol.const {pw} : {const_types[7]}
    %10 = symbol.const {pl} : {const_types[8]}
    %11 = symbol.const {pr} : {const_types[9]}
    "kernel.img2col2d"(%0, %1, %2, %3, %4, %5, %6, %7, %8, %9, %10, %11) {{space = #nn.space<{space_ir}>}} : ({dst_ir}, {src_ir}, {const_types[0]}, {const_types[1]}, {const_types[2]}, {const_types[3]}, {const_types[4]}, {const_types[5]}, {const_types[6]}, {const_types[7]}, {const_types[8]}, {const_types[9]}) -> ()
    func.return
  }}
}}"""
    print_case_input_ir(
        "emit_c-npu_demo-kernel-img2col2d-dynamic",
        case_text,
        fallback="动态 shape 的 kernel.img2col2d 应生成 img2col2d helper 调用。",
    )

    run_emitc_case(
        case_text,
        source_path="expectation/dsl/emit_c/npu_demo/kernel/img2col.py#img2col2d_dynamic",
        op_name="kernel.img2col2d.dynamic",
        expected_snippets=[
            "template <typename Context>\nvoid kernel_img2col2d_dynamic_case(Context& ctx,",
            f"img2col2d<{space_cpp}, {space_cpp}, {dtype_cpp}, {dtype_cpp}>(ctx,",
        ],
        forbidden_snippets=["kernel.img2col2d", "npu_demo::img2col2d"],
    )


def _case_kernel_img2col2d_symbol_args() -> None:
    """运行动态参数直传 `kernel.img2col2d` expectation。"""

    arg_n, arg_c, arg_h, arg_w, arg_oh, arg_ow = random_symbol_names(6)
    arg_kh, arg_kw, arg_sh, arg_sw, arg_dh, arg_dw, arg_ph, arg_pw, arg_pl, arg_pr = random_symbol_names(10)
    dtype = _random_dtype()
    space = random_memory_spaces(1, unique=False)[0]
    dtype_ir = numeric_type_ir(dtype)
    space_ir = memory_space_ir_name(space)
    src_ir = f"!nn.memory<[#S_N, #S_C, #S_H, #S_W], [#S1, #S2, #S_W, #C1], {dtype_ir}, #nn.space<{space_ir}>>"
    dst_ir = f"!nn.memory<[#S_N, #S_C, #S_KH, #S_KW, #S_OH, #S_OW], [#S3, #S4, #S5, #S6, #S_OW, #C1], {dtype_ir}, #nn.space<{space_ir}>>"
    arg_types = tuple(
        symbol_int_type_ir(value)
        for value in (arg_kh, arg_kw, arg_sh, arg_sw, arg_dh, arg_dw, arg_ph, arg_pw, arg_pl, arg_pr)
    )
    space_cpp = _space_enum_name(space)
    dtype_cpp = _cpp_type_name(dtype)
    alias_defs = f"""#S_N = #symbol.expr<{arg_n}>
#S_C = #symbol.expr<{arg_c}>
#S_H = #symbol.expr<{arg_h}>
#S_W = #symbol.expr<{arg_w}>
#S_KH = #symbol.expr<{arg_kh}>
#S_KW = #symbol.expr<{arg_kw}>
#S_OH = #symbol.expr<{arg_oh}>
#S_OW = #symbol.expr<{arg_ow}>
#S1 = #symbol.expr<{arg_c} * {arg_h} * {arg_w}>
#S2 = #symbol.expr<{arg_h} * {arg_w}>
#S3 = #symbol.expr<{arg_c} * {arg_kh} * {arg_kw} * {arg_oh} * {arg_ow}>
#S4 = #symbol.expr<{arg_kh} * {arg_kw} * {arg_oh} * {arg_ow}>
#S5 = #symbol.expr<{arg_kw} * {arg_oh} * {arg_ow}>
#S6 = #symbol.expr<{arg_oh} * {arg_ow}>
#C1 = #symbol.expr<1>
"""
    case_text = f"""// COMPILE_ARGS: --pass no-op
// CASE: 动态 symbol.int 参数应从函数参数直传到 kernel.img2col2d。
// CHECK: template <typename Context>
// CHECK: void kernel_img2col2d_symbol_arg_case(Context& ctx,
// CHECK: img2col2d<

{alias_defs}
builtin.module {{
  func.func @kernel_img2col2d_symbol_arg_case(
    %ctx : index {{name = "ctx"}},
    %0 : {dst_ir},
    %1 : {src_ir},
    %2 : {arg_types[0]},
    %3 : {arg_types[1]},
    %4 : {arg_types[2]},
    %5 : {arg_types[3]},
    %6 : {arg_types[4]},
    %7 : {arg_types[5]},
    %8 : {arg_types[6]},
    %9 : {arg_types[7]},
    %10 : {arg_types[8]},
    %11 : {arg_types[9]}
  ) {{
    "kernel.img2col2d"(%0, %1, %2, %3, %4, %5, %6, %7, %8, %9, %10, %11) {{space = #nn.space<{space_ir}>}} : ({dst_ir}, {src_ir}, {arg_types[0]}, {arg_types[1]}, {arg_types[2]}, {arg_types[3]}, {arg_types[4]}, {arg_types[5]}, {arg_types[6]}, {arg_types[7]}, {arg_types[8]}, {arg_types[9]}) -> ()
    func.return
  }}
}}"""
    print_case_input_ir(
        "emit_c-npu_demo-kernel-img2col2d-symbol-args",
        case_text,
        fallback="动态 symbol.int 参数直传的 kernel.img2col2d 应生成 img2col2d helper 调用。",
    )

    run_emitc_case(
        case_text,
        source_path="expectation/dsl/emit_c/npu_demo/kernel/img2col.py#img2col2d_symbol_args",
        op_name="kernel.img2col2d.symbol_args",
        expected_snippets=[
            "template <typename Context>\nvoid kernel_img2col2d_symbol_arg_case(Context& ctx,",
            f"img2col2d<{space_cpp}, {space_cpp}, {dtype_cpp}, {dtype_cpp}>(ctx,",
        ],
        forbidden_snippets=["kernel.img2col2d", "npu_demo::img2col2d"],
    )


def main() -> None:
    failures: list[tuple[str, BaseException]] = []
    run_case(failures, "emit_c-npu_demo-kernel-img2col1d-static", _case_kernel_img2col1d_static)
    run_case(failures, "emit_c-npu_demo-kernel-img2col1d-dynamic", _case_kernel_img2col1d_dynamic)
    run_case(failures, "emit_c-npu_demo-kernel-img2col1d-symbol-args", _case_kernel_img2col1d_symbol_args)
    run_case(failures, "emit_c-npu_demo-kernel-img2col2d-static", _case_kernel_img2col2d_static)
    run_case(failures, "emit_c-npu_demo-kernel-img2col2d-dynamic", _case_kernel_img2col2d_dynamic)
    run_case(failures, "emit_c-npu_demo-kernel-img2col2d-symbol-args", _case_kernel_img2col2d_symbol_args)
    raise_if_failures("emit_c npu_demo kernel img2col expectation", failures)


if __name__ == "__main__":
    main()
