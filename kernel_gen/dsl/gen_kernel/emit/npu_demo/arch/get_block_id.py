"""npu_demo block_id emitter.

功能说明:
- 生成 npu_demo target 下 `arch.get_block_id` 的源码片段。
- value 表达式直接映射到 `npu_demo::block_id()`；已绑定名称由公开 `emit_c_value(...)` 入口统一复用。

API 列表:
- 无（仅 target 私有注册实现）

使用示例:
- from kernel_gen.dsl.gen_kernel import EmitCContext, emit_c_op
- stmt = emit_c_op(ArchGetBlockIdOp(), EmitCContext())

关联文件:
- spec: spec/dsl/gen_kernel/emit/npu_demo/arch/__init__.md
- test: test/dsl/gen_kernel/emit/test_package.py
- 功能实现: kernel_gen/dsl/gen_kernel/emit/npu_demo/arch/get_block_id.py
"""

from __future__ import annotations

from kernel_gen.dialect.arch import ArchGetBlockIdOp

from ...register import emit_c_impl, emit_c_value_impl


@emit_c_impl(ArchGetBlockIdOp, target="npu_demo")
def _emit_npu_demo_get_block_id_op(op: ArchGetBlockIdOp, ctx) -> str:
    """发射 npu_demo `arch.get_block_id` 语句。

    功能说明:
    - 通过公开 `emit_c_op(...)` 入口生成 `S_INT name = npu_demo::block_id();`。

    使用示例:
    - emit_c_op(ArchGetBlockIdOp(), EmitCContext())

    关联文件:
    - spec: spec/dsl/gen_kernel/emit/npu_demo/arch/__init__.md
    - test: test/dsl/gen_kernel/emit/test_package.py
    - 功能实现: kernel_gen/dsl/gen_kernel/emit/npu_demo/arch/get_block_id.py
    """

    result_name = ctx.create_or_get_name(op.result)
    result_type = ctx.dispatch_type(op.result.type)
    return f"{ctx.current_indent}{result_type} {result_name} = npu_demo::block_id();"


@emit_c_value_impl(ArchGetBlockIdOp, target="npu_demo")
def _emit_npu_demo_get_block_id_value(value, ctx) -> str:
    """发射 npu_demo `arch.get_block_id` value 表达式。

    功能说明:
    - 通过公开 `emit_c_value(...)` 入口生成 `npu_demo::block_id()` 右值。

    使用示例:
    - emit_c_value(ArchGetBlockIdOp().result, EmitCContext())

    关联文件:
    - spec: spec/dsl/gen_kernel/emit/npu_demo/arch/__init__.md
    - test: test/dsl/gen_kernel/emit/test_package.py
    - 功能实现: kernel_gen/dsl/gen_kernel/emit/npu_demo/arch/get_block_id.py
    """

    return "npu_demo::block_id()"
