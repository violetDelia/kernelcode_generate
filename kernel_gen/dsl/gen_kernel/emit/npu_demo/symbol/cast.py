"""npu_demo symbol cast emitter.


功能说明:
- 生成 npu_demo target 下 `symbol.cast` / `symbol.to_int` 的源码片段。
- `symbol.ptr` source 发射为地址整数表达式，供 None memory compare 使用。
- 结果命名统一委托给 `EmitCContext.create_or_get_name(...)` 与 target name handler。

API 列表:
- 无（仅 target 私有注册实现）

使用示例:
- from kernel_gen.dsl.gen_kernel import EmitCContext, emit_c_op
- stmt = emit_c_op(SymbolCastOp(src, i32), EmitCContext())

关联文件:
- spec: [spec/dsl/gen_kernel/emit.md](../../../../../../spec/dsl/gen_kernel/emit.md)
- test: [test/dsl/gen_kernel/emit/test_package.py](../../../../../../test/dsl/gen_kernel/emit/test_package.py)
- 功能实现: [kernel_gen/dsl/gen_kernel/emit/npu_demo/symbol/cast.py](.)
"""

from __future__ import annotations

from kernel_gen.dialect.symbol import SymbolCastOp, SymbolPtrType, SymbolToIntOp

from ...register import emit_c_impl, emit_c_value_impl


@emit_c_impl(SymbolToIntOp, SymbolCastOp, target="npu_demo")
def _emit_npu_demo_symbol_cast(op, ctx) -> str:
    """发射 npu_demo symbol cast statement。

    功能说明:
    - statement 绑定 cast result 名字，表达式生成统一走 result value emitter。
    - ptr-to-int cast 必须在 result value emitter 中完成，避免直接把指针赋给 `S_INT`。

    使用示例:
    - stmt = _emit_npu_demo_symbol_cast(op, ctx)
    """

    value_expr = _emit_npu_demo_symbol_cast_value(op.result, ctx)
    result_name = ctx.lookup_name(op.result)
    if result_name is None:
        result_name = ctx.create_or_get_name(op.result)
    return f"{ctx.current_indent}{ctx.dispatch_type(op.result.type)} {result_name} = {value_expr};"


@emit_c_value_impl(SymbolToIntOp, SymbolCastOp, target="npu_demo")
def _emit_npu_demo_symbol_cast_value(value, ctx) -> str:
    """发射 npu_demo symbol cast value 表达式。

    功能说明:
    - 普通 symbol int cast 透传 source 表达式。
    - symbol.ptr cast 生成 `reinterpret_cast<S_INT>(ptr)`，用于 None memory compare 的零值比较。

    使用示例:
    - expr = _emit_npu_demo_symbol_cast_value(cast.result, ctx)
    """

    bound = ctx.lookup_name(value)
    if bound is not None:
        return bound
    from ... import emit_c_value
    source = value.owner.source
    expr = emit_c_value(source, ctx)
    if isinstance(source.type, SymbolPtrType):
        return f"reinterpret_cast<S_INT>({expr})"
    return expr
