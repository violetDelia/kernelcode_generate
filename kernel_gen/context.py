"""Compatibility import bridge for context helpers.

创建者: OpenAI Codex
最后一次更改: OpenAI Codex

功能说明:
- 为历史 expectation 中的 `kernel_gen.context` 导入路径提供最小桥接。
- 实际实现仍由 `kernel_gen.core.context` 承载，本文件不引入新的上下文状态。

API 列表:
- 无公开 API；仅保留历史导入路径。

使用示例:
- from kernel_gen.context import build_default_context

关联文件:
- spec: spec/core/context.md
- test: expectation/dsl/emit_c/npu_demo/cost/basic.py
- 功能实现: kernel_gen/core/context.py
"""

from __future__ import annotations

from kernel_gen.core.context import build_default_context
