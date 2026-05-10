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

from kernel_gen.dialect.symbol import (
    SymbolAddOp,
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

    lhs = emit_c_value(owner.operands[0], ctx)
    rhs = emit_c_value(owner.operands[1], ctx)
    if isinstance(owner, SymbolMinOp):
        return f"(({lhs}) < ({rhs}) ? ({lhs}) : ({rhs}))"
    if isinstance(owner, SymbolMaxOp):
        return f"(({lhs}) > ({rhs}) ? ({lhs}) : ({rhs}))"
    sigil = _BINARY_SIGILS.get(type(owner)) or _COMPARE_SIGILS.get(type(owner))
    if sigil is None:
        raise ctx.emit_error(owner.name, "unsupported target")
    return f"({lhs} {sigil} {rhs})"
