"""Function/module source emission bridge.

创建者: 小李飞刀
最后一次更改: 小李飞刀

功能说明:
- 作为 `emit_c` 的函数级与 module 级源码入口桥接层。
- 把包根当前的 `emit_c_op` / `emit_c_value` 传给旧实现，确保新公开入口与既有节点级注册保持一致。
- 负责把旧 `GenKernelError` 统一折叠成 `EmitCError`，供 `emit_c(...)` 直接对外使用。

使用示例:
- from kernel_gen.dsl.gen_kernel.emit_c.function import emit_c_source
- source = emit_c_source(func_op, ctx, emit_c_op, emit_c_value)

关联文件:
- spec: [spec/dsl/emit_c.md](../../../../spec/dsl/emit_c.md)
- spec: [spec/dsl/gen_kernel.md](../../../../spec/dsl/gen_kernel.md)
- test: [test/dsl/test_emit_c.py](../../../../test/dsl/test_emit_c.py)
- test: [test/dsl/test_gen_kernel.py](../../../../test/dsl/test_gen_kernel.py)
- 功能实现: [kernel_gen/dsl/gen_kernel/emit_c/](.)
"""

from __future__ import annotations

from typing import Callable

from xdsl.ir import Operation, SSAValue

from .._legacy import load_legacy_gen_kernel_module
from ..emit_context import EmitCContext, EmitCError


def emit_c_source(
    obj: object,
    ctx: EmitCContext,
    emit_op: Callable[[Operation, EmitCContext], str],
    emit_value: Callable[[SSAValue, EmitCContext], str],
) -> str:
    """使用当前注册表与旧函数级策略生成完整源码。

    创建者: 小李飞刀
    最后一次更改: 小李飞刀

    功能说明:
    - 该入口由 `kernel_gen.dsl.gen_kernel.emit_c` 与包根 `emit_c(...)` 共享。
    - 对外保留“完整源码生成”路径，对内仍复用旧函数级策略与 prelude 组合方式。
    - 任何旧 `GenKernelError` 都会被折叠为 `EmitCError`，避免直接公开到 `emit_c(...)` 调用方。

    使用示例:
    - source = emit_c_source(module_op, ctx, emit_c_op, emit_c_value)

    关联文件:
    - spec: [spec/dsl/emit_c.md](../../../../spec/dsl/emit_c.md)
    - spec: [spec/dsl/gen_kernel.md](../../../../spec/dsl/gen_kernel.md)
    - test: [test/dsl/test_emit_c.py](../../../../test/dsl/test_emit_c.py)
    - test: [test/dsl/test_gen_kernel.py](../../../../test/dsl/test_gen_kernel.py)
    - 功能实现: [kernel_gen/dsl/gen_kernel/emit_c/](.)
    """

    legacy_gen_kernel = load_legacy_gen_kernel_module()
    legacy_emit_c_op = legacy_gen_kernel.emit_c_op
    legacy_emit_c_value = legacy_gen_kernel.emit_c_value
    legacy_gen_kernel.emit_c_op = emit_op
    legacy_gen_kernel.emit_c_value = emit_value
    try:
        try:
            return legacy_gen_kernel.gen_kernel(obj, ctx)
        except legacy_gen_kernel.GenKernelError as exc:  # type: ignore[attr-defined]
            raise EmitCError(str(exc)) from exc
    finally:
        legacy_gen_kernel.emit_c_op = legacy_emit_c_op
        legacy_gen_kernel.emit_c_value = legacy_emit_c_value


__all__ = ["emit_c_source"]
