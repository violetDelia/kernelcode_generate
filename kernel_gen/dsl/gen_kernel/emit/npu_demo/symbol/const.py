"""npu_demo symbol const emitter.

创建者: OpenAI Codex
最后一次更改: 大闸蟹

功能说明:
- 生成 npu_demo target 下 `symbol.const` 的源码片段。
- 同值常量复用通过 `EmitCContext` 单次状态维护。

API 列表:
- 无（仅 target 私有注册实现）

使用示例:
- from kernel_gen.dsl.gen_kernel import EmitCContext, emit_c_op
- stmt = emit_c_op(SymbolConstOp(7), EmitCContext())

关联文件:
- spec: [spec/dsl/gen_kernel/emit.md](../../../../../../spec/dsl/gen_kernel/emit.md)
- test: [test/dsl/gen_kernel/emit/test_emit.py](../../../../../../test/dsl/gen_kernel/emit/test_emit.py)
- 功能实现: [kernel_gen/dsl/gen_kernel/emit/npu_demo/symbol/const.py](.)
"""

from __future__ import annotations

from xdsl.dialects.builtin import StringAttr
from xdsl.ir import Operation

from kernel_gen.dialect.dma import DmaLoadOp
from kernel_gen.dialect.symbol import SymbolConstOp, SymbolValueType

from ...register import emit_c_impl, emit_c_value_impl


def _is_symbol_const_like(op: object) -> bool:
    if isinstance(op, SymbolConstOp):
        return True
    if not isinstance(op, Operation):
        return False
    op_name_attr = op.attributes.get("op_name__")
    return (
        op.name == "builtin.unregistered"
        and isinstance(op_name_attr, StringAttr)
        and op_name_attr.data == "symbol.const"
    )


def _symbol_const_cache_key(op: object, value: int) -> tuple[int | None, int]:
    """生成 `symbol.const` 名称复用 key。

    创建者: 大闸蟹
    最后一次更改: 大闸蟹

    功能说明:
    - 同一函数内相同静态值复用一个局部变量名。
    - 不同函数不能共享局部变量名，避免 module 级发射时 cost 函数引用别的函数作用域里的 `c_0`。

    使用示例:
    - cache_key = _symbol_const_cache_key(op, 0)
    """

    current = getattr(op, "parent", None)
    while current is not None:
        if getattr(current, "name", None) == "func.func":
            return (id(current), value)
        current = getattr(current, "parent", None)
    if current is None:
        return (None, value)
    return (id(current), value)


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
    value = int(value_text)
    if result.uses and all(isinstance(use.operation, DmaLoadOp) for use in result.uses):
        return ""
    cache_key = _symbol_const_cache_key(op, value)
    existing_name = ctx.lookup_cached_name("symbol_const_names", cache_key)
    if existing_name is not None:
        ctx.bind_name(result, existing_name)
        return ""
    name = ctx.create_or_get_name(result)
    ctx.bind_cached_name("symbol_const_names", cache_key, name)
    return f"{ctx.current_indent}S_INT {name} = {value_text};"


@emit_c_value_impl(SymbolConstOp, target="npu_demo")
def _emit_npu_demo_symbol_const_value(value, ctx) -> str:
    bound = ctx.lookup_name(value)
    if bound is not None:
        return bound
    owner = value.owner
    if isinstance(owner, SymbolConstOp):
        return str(owner.value.data)
    if _is_symbol_const_like(owner) and owner.results and isinstance(owner.results[0].type, SymbolValueType):
        return owner.results[0].type.expr.expr.data
    raise ctx.emit_error(owner.name, "symbol.const result must be !symbol.int")
