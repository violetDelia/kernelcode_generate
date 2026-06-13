"""npu_demo symbol binary/compare EmitC 注册实现。

功能说明:
- 注册 target=`npu_demo` 的 `symbol.add/sub/mul/div/floordiv/min/max` 与比较 op 发射实现。
- `symbol.min` / `symbol.max` 发射为公开合同要求的 C++ 三目表达式。
- 本文件不提供跨文件公开 API；调用方必须通过 emit registry 与 `emit_c_op(...)` / `emit_c_value(...)` 公开入口调度。

API 列表:
- 无公开 API。

使用示例:
- source = emit_c_value(value, ctx)

关联文件:
- spec: spec/dsl/gen_kernel/emit/npu_demo/symbol/__init__.md
- test: test/dsl/gen_kernel/emit/test_package.py
- 功能实现: kernel_gen/dsl/gen_kernel/emit/npu_demo/symbol/binary.py
"""

from __future__ import annotations

from xdsl.dialects.builtin import IntAttr, IntegerAttr, StringAttr, UnregisteredOp
from xdsl.ir import SSAValue

from kernel_gen.dialect.symbol import (
    SymbolAddOp,
    SymbolConstOp,
    SymbolDivOp,
    SymbolEqOp,
    SymbolFloorDivOp,
    SymbolGeOp,
    SymbolGtOp,
    SymbolLeOp,
    SymbolLtOp,
    SymbolMaxOp,
    SymbolMinOp,
    SymbolMulOp,
    SymbolNeOp,
    SymbolSubOp,
    SymbolValueType,
)

from ...register import emit_c_impl, emit_c_value_impl

_BINARY_SIGILS = {
    SymbolAddOp: "+",
    SymbolSubOp: "-",
    SymbolMulOp: "*",
    SymbolDivOp: "/",
    SymbolFloorDivOp: "/",
}

_COMPARE_SIGILS = {
    SymbolEqOp: "==",
    SymbolNeOp: "!=",
    SymbolLtOp: "<",
    SymbolLeOp: "<=",
    SymbolGtOp: ">",
    SymbolGeOp: ">=",
}

_GENERIC_BINARY_SIGILS = {
    "symbol.add": "+",
    "symbol.sub": "-",
    "symbol.mul": "*",
    "symbol.div": "/",
    "symbol.floordiv": "/",
}

_GENERIC_COMPARE_SIGILS = {
    "symbol.eq": "==",
    "symbol.ne": "!=",
    "symbol.lt": "<",
    "symbol.le": "<=",
    "symbol.gt": ">",
    "symbol.ge": ">=",
}


@emit_c_impl(
    SymbolAddOp,
    SymbolSubOp,
    SymbolMulOp,
    SymbolDivOp,
    SymbolFloorDivOp,
    SymbolMinOp,
    SymbolMaxOp,
    SymbolEqOp,
    SymbolNeOp,
    SymbolLtOp,
    SymbolLeOp,
    SymbolGtOp,
    SymbolGeOp,
    UnregisteredOp,
    target="npu_demo",
)
def _emit_npu_demo_symbol_binary_or_compare(op, ctx) -> str:
    """发射 npu_demo symbol binary/compare 赋值语句。

    功能说明:
    - 通过公开 `emit_c_value(...)` 路径取得右值表达式，再绑定当前 op 结果名。
    - 仅作为当前文件内注册实现使用，不作为跨文件公开 API。

    使用示例:
    - stmt = _emit_npu_demo_symbol_binary_or_compare(op, ctx)
    """

    from ... import emit_c_value

    op_name_attr = op.attributes.get("op_name__")
    op_name = op_name_attr.data if isinstance(op_name_attr, StringAttr) else op.name
    if op_name == "symbol.const":
        return ""
    if op_name not in _GENERIC_BINARY_SIGILS and op_name not in _GENERIC_COMPARE_SIGILS and op_name not in {
        "symbol.min",
        "symbol.max",
    }:
        if isinstance(op, UnregisteredOp):
            raise ctx.emit_error(op.name, "unsupported op")
    result = op.results[0]
    result_type = ctx.dispatch_type(result.type)
    expr = emit_c_value(result, ctx)
    result_name = ctx.create_or_get_name(result)
    return f"{ctx.current_indent}{result_type} {result_name} = {expr};"


@emit_c_value_impl(
    SymbolAddOp,
    SymbolSubOp,
    SymbolMulOp,
    SymbolDivOp,
    SymbolFloorDivOp,
    SymbolMinOp,
    SymbolMaxOp,
    SymbolEqOp,
    SymbolNeOp,
    SymbolLtOp,
    SymbolLeOp,
    SymbolGtOp,
    SymbolGeOp,
    UnregisteredOp,
    target="npu_demo",
)
def _emit_npu_demo_symbol_binary_or_compare_value(value, ctx) -> str:
    """发射 npu_demo symbol binary/compare C++ 右值表达式。

    功能说明:
    - 普通算术和比较使用固定中缀符号。
    - `symbol.min` 使用 `((lhs) < (rhs) ? (lhs) : (rhs))`，`symbol.max` 使用 `((lhs) > (rhs) ? (lhs) : (rhs))`，和计划确认的 EmitC 合同一致。

    使用示例:
    - expr = _emit_npu_demo_symbol_binary_or_compare_value(value, ctx)
    """

    owner = value.owner
    from ... import emit_c_value

    owner_name_attr = owner.attributes.get("op_name__")
    owner_name = owner_name_attr.data if isinstance(owner_name_attr, StringAttr) else owner.name
    if owner_name == "symbol.const":
        if isinstance(value.type, SymbolValueType):
            return value.type.expr.expr.data
        raise ctx.emit_error(owner.name, "symbol.const result must be !symbol.int")
    if owner_name == "symbol.eq":
        lhs_value = SSAValue.get(owner.operands[0])
        rhs_value = SSAValue.get(owner.operands[1])
        lhs_enum = ctx.lookup_cached_name("npu_demo_tuner_select_enum", id(lhs_value))
        rhs_enum = ctx.lookup_cached_name("npu_demo_tuner_select_enum", id(rhs_value))
        lhs_pattern_count = ctx.lookup_cached_name("npu_demo_tuner_select_pattern_count", id(lhs_value))
        rhs_pattern_count = ctx.lookup_cached_name("npu_demo_tuner_select_pattern_count", id(rhs_value))
        lhs_const: int | None = None
        rhs_const: int | None = None
        lhs_owner = lhs_value.owner
        rhs_owner = rhs_value.owner
        if isinstance(lhs_owner, SymbolConstOp):
            lhs_const = lhs_owner.value.data
        else:
            lhs_owner_name_attr = getattr(lhs_owner, "attributes", {}).get("op_name__")
            lhs_owner_name = lhs_owner_name_attr.data if isinstance(lhs_owner_name_attr, StringAttr) else getattr(lhs_owner, "name", "")
            lhs_value_attr = getattr(lhs_owner, "attributes", {}).get("value")
            if lhs_owner_name == "symbol.const" and isinstance(lhs_value_attr, IntAttr):
                lhs_const = lhs_value_attr.data
            elif lhs_owner_name == "symbol.const" and isinstance(lhs_value_attr, IntegerAttr):
                lhs_const = lhs_value_attr.value.data
        if isinstance(rhs_owner, SymbolConstOp):
            rhs_const = rhs_owner.value.data
        else:
            rhs_owner_name_attr = getattr(rhs_owner, "attributes", {}).get("op_name__")
            rhs_owner_name = rhs_owner_name_attr.data if isinstance(rhs_owner_name_attr, StringAttr) else getattr(rhs_owner, "name", "")
            rhs_value_attr = getattr(rhs_owner, "attributes", {}).get("value")
            if rhs_owner_name == "symbol.const" and isinstance(rhs_value_attr, IntAttr):
                rhs_const = rhs_value_attr.data
            elif rhs_owner_name == "symbol.const" and isinstance(rhs_value_attr, IntegerAttr):
                rhs_const = rhs_value_attr.value.data
        if lhs_enum is not None and lhs_pattern_count is not None and rhs_const is not None:
            pattern_count = int(lhs_pattern_count)
            if 0 <= rhs_const < pattern_count:
                lhs_expr = emit_c_value(lhs_value, ctx)
                return f"{lhs_expr} == {lhs_enum}::pattern{rhs_const}"
        if rhs_enum is not None and rhs_pattern_count is not None and lhs_const is not None:
            pattern_count = int(rhs_pattern_count)
            if 0 <= lhs_const < pattern_count:
                rhs_expr = emit_c_value(rhs_value, ctx)
                return f"{rhs_expr} == {rhs_enum}::pattern{lhs_const}"
    lhs = emit_c_value(owner.operands[0], ctx)
    rhs = emit_c_value(owner.operands[1], ctx)
    if isinstance(owner, SymbolMinOp) or owner_name == "symbol.min":
        return f"(({lhs}) < ({rhs}) ? ({lhs}) : ({rhs}))"
    if isinstance(owner, SymbolMaxOp) or owner_name == "symbol.max":
        return f"(({lhs}) > ({rhs}) ? ({lhs}) : ({rhs}))"
    sigil = (
        _BINARY_SIGILS.get(type(owner))
        or _COMPARE_SIGILS.get(type(owner))
        or _GENERIC_BINARY_SIGILS.get(owner_name)
        or _GENERIC_COMPARE_SIGILS.get(owner_name)
    )
    if sigil is None:
        raise ctx.emit_error(owner.name, "unsupported target")
    return f"({lhs} {sigil} {rhs})"
