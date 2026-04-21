"""Compatibility wrapper for package-level `gen_kernel`.

创建者: 小李飞刀
最后一次更改: 小李飞刀

功能说明:
- 保留 `gen_kernel(obj, ctx)` 的公开兼容入口。
- 统一委托给包内 `emit_c(obj, ctx)` 生成完整源码，再把 `EmitCError` 折回旧公开错误类型。
- 让包根公开入口与旧模块级实现解耦，便于后续继续收口 `kernel_gen/dsl/gen_kernel.py` 的 legacy 逻辑。

使用示例:
- from kernel_gen.dsl.gen_kernel import EmitCContext, gen_kernel
- source = gen_kernel(func_op, EmitCContext(target="cpu"))

关联文件:
- spec: [spec/dsl/gen_kernel.md](../../../../spec/dsl/gen_kernel.md)
- spec: [spec/dsl/emit_c.md](../../../../spec/dsl/emit_c.md)
- test: [test/dsl/test_gen_kernel.py](../../../../test/dsl/test_gen_kernel.py)
- 功能实现: [kernel_gen/dsl/gen_kernel/](.)
"""

from __future__ import annotations

from ._legacy import load_legacy_gen_kernel_module
from .emit_c import EmitCContext, EmitCError

_legacy_gen_kernel = load_legacy_gen_kernel_module()

GenKernelError = _legacy_gen_kernel.GenKernelError
emit_c = None


def gen_kernel(obj: object, ctx: EmitCContext) -> str:
    """兼容保留旧函数名的源码发射入口。"""

    if emit_c is None:
        raise RuntimeError("gen_kernel wrapper emit_c binding is missing")
    try:
        return emit_c(obj, ctx)
    except EmitCError as exc:
        raise GenKernelError(str(exc)) from exc


__all__ = ["GenKernelError", "gen_kernel"]
