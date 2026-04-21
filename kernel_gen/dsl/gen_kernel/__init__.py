"""Package-style public entry for DSL code generation.

创建者: 小李飞刀
最后一次更改: 小李飞刀

功能说明:
- 以包根形式汇总 `gen_kernel` 的公开入口、上下文对象与节点级片段发射接口。
- S1 阶段先把 `kernel_gen.dsl.gen_kernel` 变成稳定的包式导入点，再逐步拆分内部实现。
- `emit_c(obj, ctx)` 作为新的统一源码发射入口，`gen_kernel(obj, ctx)` 作为兼容包装继续保留。

使用示例:
- from kernel_gen.dsl.gen_kernel import EmitCContext, emit_c, gen_kernel
- source = emit_c(func_op, EmitCContext(target="cpu"))

关联文件:
- spec: [spec/dsl/emit_c.md](../../../spec/dsl/emit_c.md)
- spec: [spec/dsl/gen_kernel.md](../../../spec/dsl/gen_kernel.md)
- test: [test/dsl/test_emit_c.py](../../../test/dsl/test_emit_c.py)
- test: [test/dsl/test_gen_kernel.py](../../../test/dsl/test_gen_kernel.py)
- 功能实现: [kernel_gen/dsl/gen_kernel/](.)
"""

from __future__ import annotations

import importlib
from typing import Any

from xdsl.ir import SSAValue

from .gen_kernel import GenKernelError, gen_kernel
from .emit_c import EmitCContext, EmitCError
from .emit_c import function as _emit_c_function_module
from . import emit_c as _emit_c_module
emit_c_op = _emit_c_module.emit_c_op
emit_c_value = _emit_c_module.emit_c_value
_gen_kernel_entry_module = importlib.import_module(f"{__name__}.gen_kernel")


def emit_c(obj: object, ctx: EmitCContext) -> str:
    """统一发射 DSL 源码片段或完整函数源码。"""

    if isinstance(obj, SSAValue):
        return emit_c_value(obj, ctx)
    return _emit_c_function_module.emit_c_source(obj, ctx, emit_c_op, emit_c_value)

_gen_kernel_entry_module.emit_c = emit_c


def __getattr__(name: str) -> Any:
    """拒绝回流的 legacy 双接口公开访问。

    创建者: 小李飞刀
    最后一次更改: 小李飞刀

    功能说明:
    - 对历史 `gen_signature` / `gen_body` 名称给出统一的缺失语义，避免其被误当成公开稳定入口回流。
    - 不影响包根当前公开导出；仅用于模块级公开访问边界。

    使用示例:
    - getattr(gen_kernel_module, "gen_signature")  # raises AttributeError

    关联文件:
    - spec: [spec/dsl/gen_kernel.md](../../../spec/dsl/gen_kernel.md)
    - test: [test/dsl/test_gen_kernel.py](../../../test/dsl/test_gen_kernel.py)
    - 功能实现: [kernel_gen/dsl/gen_kernel/](.)
    """

    if name in {"gen_signature", "gen_body"}:
        raise AttributeError(f"{name} is no longer a public entry; use gen_kernel(...) instead")
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = [
    "GenKernelError",
    "gen_kernel",
    "EmitCContext",
    "EmitCError",
    "emit_c",
    "emit_c_op",
    "emit_c_value",
]
