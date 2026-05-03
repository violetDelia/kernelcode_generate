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

from kernel_gen.dialect.dma import DmaLoadOp
from kernel_gen.dialect.symbol import SymbolConstOp

from ...register import emit_c_impl, emit_c_value_impl


@emit_c_impl(SymbolConstOp, target="npu_demo")
def _emit_npu_demo_symbol_const(op: SymbolConstOp, ctx) -> str:
    """发射 npu_demo `symbol.const` 语句。

    功能说明:
    - 每个 `SymbolConstOp` 通过公开 `emit_c_op(...)` 生成独立 `S_INT` 声明。
    - 若该常量只作为 `dma.load` 的索引/尺寸输入，由 dma emitter 内联消费，不重复生成声明。

    使用示例:
    - emit_c_op(SymbolConstOp(7), EmitCContext())

    关联文件:
    - spec: spec/dsl/gen_kernel/emit/npu_demo/symbol/__init__.md
    - test: test/dsl/gen_kernel/emit/test_package.py
    - 功能实现: kernel_gen/dsl/gen_kernel/emit/npu_demo/symbol/const.py
    """

    value_text = str(op.value.data)
    result = op.result
    int(value_text)
    if result.uses and all(isinstance(use.operation, DmaLoadOp) for use in result.uses):
        return ""
    name = ctx.create_or_get_name(result)
    return f"{ctx.current_indent}S_INT {name} = {value_text};"


@emit_c_value_impl(SymbolConstOp, target="npu_demo")
def _emit_npu_demo_symbol_const_value(value, ctx) -> str:
    """发射 npu_demo `symbol.const` value 表达式。

    功能说明:
    - 注册表只会把 `SymbolConstOp` owner 的 SSA value 分发到本函数。
    - 已绑定名称由公开 `emit_c_value(...)` 入口提前复用，未绑定结果按字面值返回。

    使用示例:
    - emit_c_value(SymbolConstOp(7).result, EmitCContext())

    关联文件:
    - spec: spec/dsl/gen_kernel/emit/npu_demo/symbol/__init__.md
    - test: test/dsl/gen_kernel/emit/test_package.py
    - 功能实现: kernel_gen/dsl/gen_kernel/emit/npu_demo/symbol/const.py
    """

    owner = value.owner
    return str(owner.value.data)
