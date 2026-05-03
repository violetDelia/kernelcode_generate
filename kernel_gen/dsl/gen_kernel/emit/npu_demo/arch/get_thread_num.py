"""npu_demo thread_num emitter.


功能说明:
- 生成 npu_demo target 下 `arch.get_thread_num` 的源码片段。
- value 表达式直接映射到 `npu_demo::thread_num()`；已绑定名称由公开 `emit_c_value(...)` 入口统一复用。

API 列表:
- 无（仅 target 私有注册实现）

使用示例:
- from kernel_gen.dsl.gen_kernel import EmitCContext, emit_c_op
- stmt = emit_c_op(ArchGetThreadNumOp(), EmitCContext())

关联文件:
- spec: spec/dsl/gen_kernel/emit/npu_demo/arch/__init__.md
- test: test/dsl/gen_kernel/emit/test_package.py
- 功能实现: kernel_gen/dsl/gen_kernel/emit/npu_demo/arch/get_thread_num.py
"""

from __future__ import annotations

from kernel_gen.dialect.arch import ArchGetThreadNumOp

from ...register import emit_c_impl, emit_c_value_impl


@emit_c_impl(ArchGetThreadNumOp, target="npu_demo")
def _emit_npu_demo_get_thread_num_op(op: ArchGetThreadNumOp, ctx) -> str:
    """发射 npu_demo `arch.get_thread_num` 语句。

    功能说明:
    - 通过公开 `emit_c_op(...)` 入口生成 `S_INT name = npu_demo::thread_num();`。

    使用示例:
    - emit_c_op(ArchGetThreadNumOp(), EmitCContext())

    关联文件:
    - spec: spec/dsl/gen_kernel/emit/npu_demo/arch/__init__.md
    - test: test/dsl/gen_kernel/emit/test_package.py
    - 功能实现: kernel_gen/dsl/gen_kernel/emit/npu_demo/arch/get_thread_num.py
    """

    result_name = ctx.create_or_get_name(op.result)
    result_type = ctx.dispatch_type(op.result.type)
    return f"{ctx.current_indent}{result_type} {result_name} = npu_demo::thread_num();"


@emit_c_value_impl(ArchGetThreadNumOp, target="npu_demo")
def _emit_npu_demo_get_thread_num_value(value, ctx) -> str:
    """发射 npu_demo `arch.get_thread_num` value 表达式。

    功能说明:
    - 通过公开 `emit_c_value(...)` 入口生成 `npu_demo::thread_num()` 右值。

    使用示例:
    - emit_c_value(ArchGetThreadNumOp().result, EmitCContext())

    关联文件:
    - spec: spec/dsl/gen_kernel/emit/npu_demo/arch/__init__.md
    - test: test/dsl/gen_kernel/emit/test_package.py
    - 功能实现: kernel_gen/dsl/gen_kernel/emit/npu_demo/arch/get_thread_num.py
    """

    return "npu_demo::thread_num()"
