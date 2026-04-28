# emit_context.md

## 功能简介

- 定义 `EmitCContext` 的稳定公开入口。
- 失败统一抛出 `KernelCodeError(ErrorModule.GEN_KERNEL, message)`；不再定义或导出上下文专属错误类。
- 负责：
  - emit 阶段命名状态
  - 节点 / value / type / attr / include 分发
  - target 相关 type / space 文本转换入口
- `EmitCContext` 只允许无参构造；target 等公开行为配置必须先通过 `kernel_gen.core.config` 设置。
- `EmitCContext` 只承载单次 emit 发射状态，不承载公开行为配置。

## API 列表

- `EmitCContext()`
- `EmitCContext.create_or_get_name(value: SSAValue) -> str`
- `EmitCContext.allocate_name(prefix: str) -> str`
- `EmitCContext.lookup_cached_name(scope: str, key: object) -> str | None`
- `EmitCContext.bind_cached_name(scope: str, key: object, name: str) -> str`
- `EmitCContext.is_target(name: str) -> bool`
- `EmitCContext.target_entry(table: Mapping[str, T], default: T | None = None) -> T | None`
- `EmitCContext.emit_error(subject: str, reason: str) -> KernelCodeError`
- `EmitCContext.dispatch(obj: Any) -> str | None`
- `EmitCContext.dispatch_op(op: Operation) -> str | None`
- `EmitCContext.dispatch_value(value: SSAValue) -> str | None`
- `EmitCContext.dispatch_type(attr: Any) -> str`
- `EmitCContext.dispatch_attr(attr: Any) -> str | None`
- `EmitCContext.dispatch_include() -> str`

## 文档信息

- 创建者：`小李飞刀`
- 最后一次更改：`守护最好的爱莉希雅`
- `spec`：[`spec/dsl/gen_kernel/emit_context.md`](../../../spec/dsl/gen_kernel/emit_context.md)
- `功能实现`：[`kernel_gen/dsl/gen_kernel/emit_context.py`](../../../kernel_gen/dsl/gen_kernel/emit_context.py)
- `test`：[`test/dsl/gen_kernel/emit/test_emit.py`](../../../test/dsl/gen_kernel/emit/test_emit.py)

## 依赖

- [`spec/dsl/gen_kernel/emit/register.md`](../../../spec/dsl/gen_kernel/emit/register.md)
- [`spec/dsl/gen_kernel/emit/npu_demo.md`](../../../spec/dsl/gen_kernel/emit/npu_demo.md)

## 目标

- 提供统一上下文，避免在 target 实现中再维护平行类型 / `space` 转换壳。
- `space` 相关文本统一走 `dispatch_attr(...)` 的 target 注册，不再在 context 上公开独立 `space_*_to_c` 接口。
- `EmitCContext()` 构造时从 `kernel_gen.core.config.get_target()` 读取 target 快照；target 未设置或不是非空字符串时必须失败。
- target 字符串不作为 `EmitCContext` 公开属性暴露；跨文件代码只能通过 `is_target(...)`、`target_entry(...)` 或更具体的公开方法访问 target 相关行为。

## 限制与边界

- `EmitCContext` 只定义 emit 上下文，不承接函数级策略。
- `EmitCContext()` 不接受 `target=`、`config=`、`indent=`、`naming=`、`type_converter=` 等公开关键字。
- 命名、局部缓存和转换状态统一收口到 context 单次状态；不得在 target 目录中维护第二套全局状态。
- 不公开可变状态字典；需要命名递增或局部名称缓存时，使用 `allocate_name(...)`、`lookup_cached_name(...)`、`bind_cached_name(...)`。

## 测试

- 测试文件：[`test/dsl/gen_kernel/emit/test_emit.py`](../../../test/dsl/gen_kernel/emit/test_emit.py)
- 执行命令：`pytest -q test/dsl/gen_kernel/emit/test_emit.py`
- 测试目标：
  - 上下文命名和 dispatch 保持稳定
  - `EmitCContext()` 读取 `core.config` 的 target 快照
  - target 缺失时显式失败
  - type / attr / include 分发入口工作正常
