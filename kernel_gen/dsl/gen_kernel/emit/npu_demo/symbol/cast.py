"""npu_demo symbol cast emitter.

创建者: OpenAI Codex
最后一次更改: OpenAI Codex

功能说明:
- 生成 npu_demo target 下 `symbol.cast` / `symbol.to_int` 的源码片段。
- 结果命名统一委托给 `EmitCContext.create_or_get_name(...)` 与 target name handler。

API 列表:
- 无（仅 target 私有注册实现）

使用示例:
- from kernel_gen.dsl.gen_kernel import EmitCContext, emit_c_op
- stmt = emit_c_op(SymbolCastOp(src, i32), EmitCContext(config={"target": "npu_demo"}))

关联文件:
- spec: [spec/dsl/gen_kernel/emit.md](../../../../../../spec/dsl/gen_kernel/emit.md)
- test: [test/dsl/gen_kernel/emit/test_emit.py](../../../../../../test/dsl/gen_kernel/emit/test_emit.py)
- 功能实现: [kernel_gen/dsl/gen_kernel/emit/npu_demo/symbol/cast.py](.)
"""

from __future__ import annotations

from kernel_gen.dialect.symbol import SymbolCastOp, SymbolToIntOp

from ...register import emit_c_impl, emit_c_value_impl

@emit_c_impl(SymbolToIntOp, SymbolCastOp, target="npu_demo")
def _emit_npu_demo_symbol_cast(op, ctx) -> str:
    result_name = ctx.lookup_name(op.result)
    if result_name is None:
        result_name = ctx.create_or_get_name(op.result)
    return f"{ctx.current_indent}{ctx.dispatch_type(op.result.type)} {result_name} = {_emit_npu_demo_symbol_cast_value(op.source, ctx)};"


@emit_c_value_impl(SymbolToIntOp, SymbolCastOp, target="npu_demo")
def _emit_npu_demo_symbol_cast_value(value, ctx) -> str:
    bound = ctx.lookup_name(value)
    if bound is not None:
        return bound
    from ... import emit_c_value

    return emit_c_value(value.owner.source, ctx)
