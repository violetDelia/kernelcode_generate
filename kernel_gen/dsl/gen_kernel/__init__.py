"""兼容保留的 `kernel_gen.dsl.gen_kernel` 包根入口。

创建者: 小李飞刀
最后一次更改: 金铲铲大作战

功能说明:
- 以包根形式汇总 `gen_kernel` 的公开入口、上下文对象与节点级片段发射接口。
- 当前 `kernel_gen.dsl.gen_kernel` 就是 canonical 公开路径。
- 包根承认 `gen_kernel(...)` / `dsl_gen_kernel(...)` / `emit_c(...)` / `emit_c_op(...)` / `emit_c_value(...)` 这组稳定公开入口。
- `KernelEmitter` 继续作为 package-root 可达的公开类型导出保留，但函数源码生成仍统一经 `gen_kernel(...)` / `dsl_gen_kernel(...)` 收口。

API 列表:
- `gen_kernel(obj: object, ctx: EmitCContext) -> str`
- `dsl_gen_kernel(fn: Callable[..., object], *runtime_args: object, ctx: EmitCContext, config: dict[str, object] | None = None) -> str`
- `emit_c(obj: object, ctx: EmitCContext) -> str`
- `emit_c_op(op: Operation, ctx: EmitCContext) -> str`
- `emit_c_value(value: SSAValue, ctx: EmitCContext) -> str`
- `KernelEmitter(ctx: EmitCContext, emit_op: Callable[[Operation, EmitCContext], str | None] | None = None, emit_value: Callable[[SSAValue, EmitCContext], str | None] | None = None)`
- `EmitCContext(*, config: dict[str, object] | None = None)`
- `EmitCError(message: str)`
- `GenKernelError(message: str)`

helper 清单:
- `__getattr__(name: str) -> object`

使用示例:
- from kernel_gen.dsl.gen_kernel import EmitCContext, emit_c, gen_kernel
- source = emit_c(func_op, EmitCContext(config={"target": "cpu"}))

关联文件:
- spec: [spec/dsl/gen_kernel/emit.md](../../../spec/dsl/gen_kernel/emit.md)
- spec: [spec/dsl/gen_kernel/gen_kernel.md](../../../spec/dsl/gen_kernel/gen_kernel.md)
- test: [test/dsl/gen_kernel/emit/test_emit.py](../../../test/dsl/gen_kernel/emit/test_emit.py)
- test: [test/dsl/gen_kernel/test_gen_kernel.py](../../../test/dsl/gen_kernel/test_gen_kernel.py)
- 功能实现: [kernel_gen/dsl/gen_kernel/__init__.py](.)
"""

from __future__ import annotations

from .emit import emit_c, emit_c_op, emit_c_value
from .emit_context import EmitCContext, EmitCError
from .gen_kernel import GenKernelError, dsl_gen_kernel, gen_kernel
from .kernel_emitter import KernelEmitter


def __getattr__(name: str) -> object:
    """阻断已退场的旧公开名，避免回退到过时 gen_kernel facade。

    创建者: 金铲铲大作战
    最后一次更改: 金铲铲大作战

    功能说明:
    - 只对历史公开名 `gen_signature` / `gen_body` 给出稳定失败短语。
    - 其余未知属性继续走标准 `AttributeError`。

    使用示例:
    - import kernel_gen.dsl.gen_kernel as gen_kernel_pkg
    - with pytest.raises(AttributeError):
    -     _ = gen_kernel_pkg.gen_signature

    关联文件:
    - spec: [spec/dsl/gen_kernel/gen_kernel.md](../../../spec/dsl/gen_kernel/gen_kernel.md)
    - test: [test/dsl/test_package_api.py](../../../test/dsl/test_package_api.py)
    - 功能实现: [kernel_gen/dsl/gen_kernel/__init__.py](.)
    """

    if name in {"gen_signature", "gen_body"}:
        raise AttributeError(f"{name} is no longer a public entry; use gen_kernel(...) instead")
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = [
    "GenKernelError",
    "KernelEmitter",
    "dsl_gen_kernel",
    "gen_kernel",
    "EmitCContext",
    "EmitCError",
    "emit_c",
    "emit_c_op",
    "emit_c_value",
]
