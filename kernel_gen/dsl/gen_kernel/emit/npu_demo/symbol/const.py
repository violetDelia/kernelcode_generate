"""npu_demo symbol const emitter.


功能说明:
- 生成 npu_demo target 下 `symbol.const` 的源码片段。
- 每条 `symbol.const` SSA op 都生成独立源码声明，不按字面值复用，避免 EmitC 阶段隐式合并 IR 常量。

API 列表:
- 无（仅 target 私有注册实现）

使用示例:
- from kernel_gen.dsl.gen_kernel import EmitCContext, emit_c_op
- stmt = emit_c_op(SymbolConstOp(7), EmitCContext())

关联文件:
- spec: [spec/dsl/gen_kernel/emit.md](../../../../../../spec/dsl/gen_kernel/emit.md)
- test: [test/dsl/gen_kernel/emit/test_package.py](../../../../../../test/dsl/gen_kernel/emit/test_package.py)
- 功能实现: [kernel_gen/dsl/gen_kernel/emit/npu_demo/symbol/const.py](.)
"""

from __future__ import annotations

from xdsl.dialects.builtin import StringAttr
from kernel_gen.dialect.dma import DmaLoadOp
from kernel_gen.dialect.symbol import SymbolConstOp, SymbolValueType

from ...register import emit_c_impl, emit_c_value_impl


@emit_c_impl(SymbolConstOp, target="npu_demo")
def _emit_npu_demo_symbol_const(op, ctx) -> str:
    if isinstance(op, SymbolConstOp):
        value_text = str(op.value.data)
        result = op.result
    else:
        if not op.results or not isinstance(op.results[0].type, SymbolValueType):
            raise ctx.emit_error(op.name, "symbol.const result must be !symbol.int")
        value_attr = op.attributes.get("value")
        if not hasattr(value_attr, "value") or not hasattr(value_attr.value, "data"):
            raise ctx.emit_error(op.name, "symbol.const value must be integer attribute")
        value_text = str(value_attr.value.data)
        result = op.results[0]
    int(value_text)
    if result.uses and all(isinstance(use.operation, DmaLoadOp) for use in result.uses):
        return ""
    name = ctx.create_or_get_name(result)
    return f"{ctx.current_indent}S_INT {name} = {value_text};"


@emit_c_value_impl(SymbolConstOp, target="npu_demo")
def _emit_npu_demo_symbol_const_value(value, ctx) -> str:
    bound = ctx.lookup_name(value)
    if bound is not None:
        return bound
    owner = value.owner
    if isinstance(owner, SymbolConstOp):
        return str(owner.value.data)
    op_name_attr = getattr(owner, "attributes", {}).get("op_name__")
    if (
        getattr(owner, "name", None) == "builtin.unregistered"
        and isinstance(op_name_attr, StringAttr)
        and op_name_attr.data == "symbol.const"
        and owner.results
        and isinstance(owner.results[0].type, SymbolValueType)
    ):
        return owner.results[0].type.expr.expr.data
    raise ctx.emit_error(owner.name, "symbol.const result must be !symbol.int")
