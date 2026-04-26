# errors.md

## 功能简介

- 定义 `emit_c_error(...)` 的公开错误拼接合同。
- 统一生成 `target=<name>: <subject>: <reason>` 风格的 `EmitCError`。

## API 列表

- `emit_c_error(ctx: EmitCContext, subject: str, reason: str)`

## 文档信息

- 创建者：`OpenAI Codex`
- 最后一次更改：`OpenAI Codex`
- `spec`：[`spec/dsl/gen_kernel/errors.md`](../../../spec/dsl/gen_kernel/errors.md)
- `功能实现`：[`kernel_gen/dsl/gen_kernel/errors.py`](../../../kernel_gen/dsl/gen_kernel/errors.py)
- `test`：[`test/dsl/gen_kernel/emit/test_emit.py`](../../../test/dsl/gen_kernel/emit/test_emit.py)

## 依赖

- [`spec/dsl/gen_kernel/emit_context.md`](../../../spec/dsl/gen_kernel/emit_context.md)

## 目标

- 避免 target 实现手写错误前缀，统一错误消息格式。

## 限制与边界

- 本模块只负责 `EmitCError` 文本拼接，不负责异常转换策略。

## 测试

- 测试文件：[`test/dsl/gen_kernel/emit/test_emit.py`](../../../test/dsl/gen_kernel/emit/test_emit.py)
- 执行命令：`pytest -q test/dsl/gen_kernel/emit/test_emit.py`
- 测试目标：错误消息前缀稳定
