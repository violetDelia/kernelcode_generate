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

from typing import Any

from xdsl.ir import SSAValue

from ._legacy import load_legacy_emit_c_module, load_legacy_gen_kernel_module
from .emit_context import EmitCContext, EmitCError

_legacy_emit_c = load_legacy_emit_c_module()
_legacy_gen_kernel = load_legacy_gen_kernel_module()

GenKernelError = _legacy_gen_kernel.GenKernelError
emit_c_op = _legacy_emit_c.emit_c_op
emit_c_value = _legacy_emit_c.emit_c_value


def _call_legacy_gen_kernel(obj: object, ctx: EmitCContext) -> str:
    """调用旧版 `gen_kernel` 实现，并透传包根当前的片段发射导出。

    创建者: 小李飞刀
    最后一次更改: 小李飞刀

    功能说明:
    - 让旧实现继续执行原有函数级逻辑。
    - 在调用前临时把旧模块里的 `emit_c_op` / `emit_c_value` 指向包根当前导出，
      以便测试里的 monkeypatch 能直接影响这条兼容入口。

    使用示例:
    - source = _call_legacy_gen_kernel(func_op, EmitCContext(target="cpu"))

    关联文件:
    - spec: [spec/dsl/gen_kernel.md](../../../spec/dsl/gen_kernel.md)
    - test: [test/dsl/test_gen_kernel.py](../../../test/dsl/test_gen_kernel.py)
    - 功能实现: [kernel_gen/dsl/gen_kernel/](.)
    """

    legacy_emit_c_op = _legacy_gen_kernel.emit_c_op
    legacy_emit_c_value = _legacy_gen_kernel.emit_c_value
    _legacy_gen_kernel.emit_c_op = emit_c_op
    _legacy_gen_kernel.emit_c_value = emit_c_value
    try:
        return _legacy_gen_kernel.gen_kernel(obj, ctx)
    finally:
        _legacy_gen_kernel.emit_c_op = legacy_emit_c_op
        _legacy_gen_kernel.emit_c_value = legacy_emit_c_value


def emit_c(obj: object, ctx: EmitCContext) -> str:
    """统一发射 DSL 源码片段或完整函数源码。

    创建者: 小李飞刀
    最后一次更改: 小李飞刀

    功能说明:
    - 对 `SSAValue` 直接复用 `emit_c_value(...)`。
    - 其余对象统一委托旧版 `gen_kernel(...)` 兼容实现。
    - 这样既保留现有生成行为，也把公开入口收口到包根。

    使用示例:
    - source = emit_c(func_op, EmitCContext(target="cpu"))
    - expr = emit_c(block_arg, EmitCContext(target="cpu"))

    关联文件:
    - spec: [spec/dsl/emit_c.md](../../../spec/dsl/emit_c.md)
    - spec: [spec/dsl/gen_kernel.md](../../../spec/dsl/gen_kernel.md)
    - test: [test/dsl/test_emit_c.py](../../../test/dsl/test_emit_c.py)
    - test: [test/dsl/test_gen_kernel.py](../../../test/dsl/test_gen_kernel.py)
    - 功能实现: [kernel_gen/dsl/gen_kernel/](.)
    """

    if isinstance(obj, SSAValue):
        return emit_c_value(obj, ctx)
    return _call_legacy_gen_kernel(obj, ctx)


def gen_kernel(obj: object, ctx: EmitCContext) -> str:
    """兼容保留旧函数名的源码发射入口。

    创建者: 小李飞刀
    最后一次更改: 小李飞刀

    功能说明:
    - 保持历史 `gen_kernel(...)` 调用方式可用。
    - 直接复用包根 `emit_c(...)` 收口后的统一实现，不再额外维护一套新逻辑。

    使用示例:
    - source = gen_kernel(func_op, EmitCContext(target="cpu"))

    关联文件:
    - spec: [spec/dsl/gen_kernel.md](../../../spec/dsl/gen_kernel.md)
    - test: [test/dsl/test_gen_kernel.py](../../../test/dsl/test_gen_kernel.py)
    - 功能实现: [kernel_gen/dsl/gen_kernel/](.)
    """

    return emit_c(obj, ctx)


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
