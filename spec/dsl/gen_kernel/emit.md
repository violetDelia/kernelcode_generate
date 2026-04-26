# emit.md

## 功能简介

- 定义 `kernel_gen.dsl.gen_kernel.emit` package 的当前公开合同。
- 负责节点级 emit、target 注册和 dispatch。
- `func.func` / `builtin.module` 的完整源码组织仍经由当前目录中的 `KernelEmitter` 协作完成，但该 helper 不属于本 package 的公开 API。

## API 列表

- `emit_c(obj: object, ctx: EmitCContext) -> str`
- `emit_c_op(op: Operation, ctx: EmitCContext) -> str`
- `emit_c_value(value: SSAValue, ctx: EmitCContext) -> str`

## 文档信息

- 创建者：`OpenAI Codex`
- 最后一次更改：`睡觉小分队`
- `spec`：[`spec/dsl/gen_kernel/emit.md`](../../../spec/dsl/gen_kernel/emit.md)
- `功能实现`：
  - [`kernel_gen/dsl/gen_kernel/emit/__init__.py`](../../../kernel_gen/dsl/gen_kernel/emit/__init__.py)
  - [`kernel_gen/dsl/gen_kernel/emit/register.py`](../../../kernel_gen/dsl/gen_kernel/emit/register.py)
  - [`kernel_gen/dsl/gen_kernel/emit/cpu/__init__.py`](../../../kernel_gen/dsl/gen_kernel/emit/cpu/__init__.py)
  - [`kernel_gen/dsl/gen_kernel/emit/npu_demo/__init__.py`](../../../kernel_gen/dsl/gen_kernel/emit/npu_demo/__init__.py)
- `test`：[`test/dsl/gen_kernel/emit/test_emit.py`](../../../test/dsl/gen_kernel/emit/test_emit.py)

## 依赖

- [`spec/dsl/gen_kernel/emit/register.md`](../../../spec/dsl/gen_kernel/emit/register.md)
- [`spec/dsl/gen_kernel/emit_context.md`](../../../spec/dsl/gen_kernel/emit_context.md)
- [`spec/dsl/gen_kernel/emit/cpu/__init__.md`](../../../spec/dsl/gen_kernel/emit/cpu/__init__.md)
- [`spec/dsl/gen_kernel/emit/npu_demo.md`](../../../spec/dsl/gen_kernel/emit/npu_demo.md)

## 目标

- 把 `emit` package 的公开面限定在 3 个发射入口。
- 保持 target-specific 实现仅通过注册体系接入。

## 限制与边界

- 不公开 target 目录中的私有实现 helper。
- 不得把 type、space、include 再拆成平行公开工具模块。
- 注册器与 dispatch 合同单独定义在 [`spec/dsl/gen_kernel/emit/register.md`](../../../spec/dsl/gen_kernel/emit/register.md)。
- `_dispatch_target`、target-specific helper、`KernelEmitter` 与 `kernel_emitter.py` 中的辅助步骤都不是当前 package 公开 API；实现、其他模块与测试不得跨文件直连。

## 测试

- 测试文件：[`test/dsl/gen_kernel/emit/test_emit.py`](../../../test/dsl/gen_kernel/emit/test_emit.py)
- 执行命令：`pytest -q test/dsl/gen_kernel/emit/test_emit.py`
- 测试目标：
  - package 级 emit 入口稳定
  - 注册 / dispatch 路径稳定
  - `func.func` / `builtin.module` 的 wrapper/body 兼容性通过 `emit_c(...)` 黑盒验收，不依赖当前目录内部 helper
  - 测试不得跨文件导入 `kernel_emitter.py` 或 target 私有 helper 作为公开接口
