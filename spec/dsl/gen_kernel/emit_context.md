# emit_context.md

## 功能简介

- 定义 `EmitCContext` / `EmitCError` 的稳定公开入口。
- 负责：
  - emit 阶段命名状态
  - 节点 / value / type / attr / include 分发
  - target 相关 type / space 文本转换入口
- 当前专题下，`EmitCContext` 既要承接 `config={"target": ...}` 形态，也要承接仍被只读 kernel 合同资产使用的 `target="..."` 关键字形态；两者公开语义必须一致。

## API 列表

- `EmitCError(message: str)`
- `EmitCContext(*, target: str | None = None, config: dict[str, Any] | None = None)`
- `EmitCContext.create_or_get_name(value: SSAValue) -> str`
- `EmitCContext.dispatch(obj: Any) -> str | None`
- `EmitCContext.dispatch_op(op: Operation) -> str | None`
- `EmitCContext.dispatch_value(value: SSAValue) -> str | None`
- `EmitCContext.dispatch_type(attr: Any) -> str`
- `EmitCContext.dispatch_attr(attr: Any) -> str | None`
- `EmitCContext.dispatch_include() -> str`

## 文档信息

- 创建者：`小李飞刀`
- 最后一次更改：`睡觉小分队`
- `spec`：[`spec/dsl/gen_kernel/emit_context.md`](../../../spec/dsl/gen_kernel/emit_context.md)
- `功能实现`：[`kernel_gen/dsl/gen_kernel/emit_context.py`](../../../kernel_gen/dsl/gen_kernel/emit_context.py)
- `test`：[`test/dsl/gen_kernel/emit/test_emit.py`](../../../test/dsl/gen_kernel/emit/test_emit.py)

## 依赖

- [`spec/dsl/gen_kernel/emit/register.md`](../../../spec/dsl/gen_kernel/emit/register.md)
- [`spec/dsl/gen_kernel/emit/npu_demo.md`](../../../spec/dsl/gen_kernel/emit/npu_demo.md)

## 目标

- 提供统一上下文，避免在 target 实现中再维护平行类型 / `space` 转换壳。
- `space` 相关文本统一走 `dispatch_attr(...)` 的 target 注册，不再在 context 上公开独立 `space_*_to_c` 接口。
- 兼容现有 `EmitCContext(target="npu_demo")` 与 `EmitCContext(config={"target": "npu_demo"})` 两条公开构造路径，不要求调用方为了当前专题只读资产去改写脚本。

## 限制与边界

- `EmitCContext` 只定义 emit 上下文，不承接函数级策略。
- 公开构造参数只承认 `target` 与 `config`：
  - `target` 是对 `config["target"]` 的公开快捷写法；
  - `indent`、`naming`、`type_converter` 仍只允许通过 `config` 传入，不再各自暴露平行关键字参数。
- 当同时传入 `target` 与 `config["target"]` 时，两者必须一致；不一致时必须显式抛出 `EmitCError`。
- 命名、局部缓存和转换状态统一收口到 `config` 与 context 私有状态；不得在 target 目录中维护第二套全局状态。

## 测试

- 测试文件：[`test/dsl/gen_kernel/emit/test_emit.py`](../../../test/dsl/gen_kernel/emit/test_emit.py)
- 执行命令：`pytest -q test/dsl/gen_kernel/emit/test_emit.py`
- 测试目标：
  - 上下文命名和 dispatch 保持稳定
  - `EmitCContext(target="npu_demo")` 与 `EmitCContext(config={"target": "npu_demo"})` 共享同一 target 语义
  - `target` 与 `config["target"]` 冲突时显式失败
  - type / attr / include 分发入口工作正常
