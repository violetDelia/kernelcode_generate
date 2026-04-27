# register.md

## 功能简介

- 定义 `emit` 层的公开注册器与 dispatch 合同。
- 该模块是当前唯一允许下游扩展 target-specific emit 行为的公开入口。

## API 列表

- `emit_c_impl(*types: type[Any], target: str | None = None)`
- `emit_c_value_impl(*types: type[Any], target: str | None = None)`
- `emit_c_type_impl(*types: type[Any], target: str)`
- `emit_c_attr_impl(*types: type[Any], target: str)`
- `emit_c_include_impl(target: str)`
- `emit_c_name_impl(*types: type[Any], target: str)`
- `dispatch_op(op, ctx: EmitCContext)`
- `dispatch_value(value, ctx: EmitCContext)`
- `dispatch_type(attr, ctx: EmitCContext)`
- `dispatch_attr(attr, ctx: EmitCContext)`
- `dispatch_include(ctx: EmitCContext)`
- `dispatch_name(value, ctx: EmitCContext)`

## 文档信息

- 创建者：`OpenAI Codex`
- 最后一次更改：`OpenAI Codex`
- `spec`：[`spec/dsl/gen_kernel/emit/register.md`](../../../../spec/dsl/gen_kernel/emit/register.md)
- `功能实现`：[`kernel_gen/dsl/gen_kernel/emit/register.py`](../../../../kernel_gen/dsl/gen_kernel/emit/register.py)
- `test`：[`test/dsl/gen_kernel/emit/test_emit.py`](../../../../test/dsl/gen_kernel/emit/test_emit.py)

## 依赖

- [`spec/dsl/gen_kernel/emit_context.md`](../../../../spec/dsl/gen_kernel/emit_context.md)

## 目标

- 统一 target / type / attr / include 的注册入口。
- 避免在 target 目录之外维护第二套 dispatch 机制。

## 限制与边界

- 本模块之外不得新增平行注册器。
- 注册器以外的 helper 不构成公开 API。

## 测试

- 测试文件：[`test/dsl/gen_kernel/emit/test_emit.py`](../../../../test/dsl/gen_kernel/emit/test_emit.py)
- 执行命令：`pytest -q test/dsl/gen_kernel/emit/test_emit.py`
- 测试目标：
  - 注册器可接入 target 实现
  - dispatch 规则保持稳定
