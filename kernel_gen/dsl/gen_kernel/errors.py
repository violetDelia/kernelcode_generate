"""`gen_kernel` error helpers.

创建者: OpenAI Codex
最后修改人: OpenAI Codex

功能说明:
- 提供 `gen_kernel` / `emit_c` 共享的公开错误构造 helper。
- 供 `emit/*` 及其 target 实现复用，避免重复拼接 target 错误前缀。

使用示例:
- `from kernel_gen.dsl.gen_kernel.errors import emit_c_error`

关联文件:
- spec: [`spec/dsl/gen_kernel/emit.md`](../../../../spec/dsl/gen_kernel/emit.md)
- test: [`test/dsl/gen_kernel/emit/test_emit.py`](../../../../test/dsl/gen_kernel/emit/test_emit.py)
- 功能实现: [`kernel_gen/dsl/gen_kernel/errors.py`](../../../kernel_gen/dsl/gen_kernel/errors.py)
"""

from __future__ import annotations

from .emit_context import EmitCContext, EmitCError


def emit_c_error(ctx: EmitCContext, subject: str, reason: str) -> EmitCError:
    return EmitCError(f"target={ctx.config['target']}: {subject}: {reason}")


__all__ = ["emit_c_error"]
