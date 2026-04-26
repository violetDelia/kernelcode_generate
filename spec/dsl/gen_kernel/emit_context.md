# emit_context.md

## 功能简介

- 定义 `EmitCContext` / `EmitCError` 的稳定公开入口。
- 负责：
  - emit 阶段命名状态
  - 节点 / value / type / attr / include 分发
  - target 相关 type / space 文本转换入口

## API 列表

- `EmitCError`
- `EmitCContext`
  - `—— init(target: str, indent: str = "    ", naming=None, type_converter=None, config=None)`
  - `—— create_or_get_name(value, preferred: str | None = None, prefix: str = "v")`
  - `—— dispatch(obj)`
  - `—— dispatch_op(op)`
  - `—— dispatch_value(value)`
  - `—— dispatch_type(attr)`
  - `—— dispatch_attr(attr)`
  - `—— dispatch_include()`

## 文档信息

- 创建者：`小李飞刀`
- 最后一次更改：`OpenAI Codex`
- `spec`：[`spec/dsl/gen_kernel/emit_context.md`](../../../spec/dsl/gen_kernel/emit_context.md)
- `功能实现`：[`kernel_gen/dsl/gen_kernel/emit_context.py`](../../../kernel_gen/dsl/gen_kernel/emit_context.py)
- `test`：[`test/dsl/gen_kernel/emit/test_emit.py`](../../../test/dsl/gen_kernel/emit/test_emit.py)

## 依赖

- [`spec/dsl/gen_kernel/emit/register.md`](../../../spec/dsl/gen_kernel/emit/register.md)
- [`spec/dsl/gen_kernel/emit/npu_demo.md`](../../../spec/dsl/gen_kernel/emit/npu_demo.md)

## 目标

- 提供统一上下文，避免在 target 实现中再维护平行类型 / `space` 转换壳。
- `space` 相关文本统一走 `dispatch_attr(...)` 的 target 注册，不再在 context 上公开独立 `space_*_to_c` 接口。

## 限制与边界

- `EmitCContext` 只定义 emit 上下文，不承接函数级策略。
- 命名、局部缓存和转换状态允许保存在 context 内；不得在 target 目录中维护第二套全局状态。

## 测试

- 测试文件：[`test/dsl/gen_kernel/emit/test_emit.py`](../../../test/dsl/gen_kernel/emit/test_emit.py)
- 执行命令：`pytest -q test/dsl/gen_kernel/emit/test_emit.py`
- 测试目标：
  - 上下文命名和 dispatch 保持稳定
- type / attr / include 分发入口工作正常
