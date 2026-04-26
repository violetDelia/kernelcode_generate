# gen_kernel.md

## 功能简介

- 定义 `kernel_gen.dsl.gen_kernel.gen_kernel` 模块的公开入口合同。
- 该模块只负责 `gen_kernel(...)` 公开包装：
  - 构造 `KernelEmitter`
  - 绑定节点级 `emit_c_op(...)`
  - 为完整源码补 `emit_include()`
  - 把内部 `EmitCError` 折回 `GenKernelError`

## API 列表

- `GenKernelError`
- `KernelEmitter`
- `gen_kernel(op_or_func, ctx: EmitCContext)`

## 文档信息

- 创建者：`小李飞刀`
- 最后一次更改：`OpenAI Codex`
- `spec`：[`spec/dsl/gen_kernel/gen_kernel.md`](../../../spec/dsl/gen_kernel/gen_kernel.md)
- `功能实现`：[`kernel_gen/dsl/gen_kernel/gen_kernel.py`](../../../kernel_gen/dsl/gen_kernel/gen_kernel.py)
- `test`：[`test/dsl/gen_kernel/test_gen_kernel.py`](../../../test/dsl/gen_kernel/test_gen_kernel.py)

## 依赖

- [`spec/dsl/gen_kernel/kernel_emitter.md`](../../../spec/dsl/gen_kernel/kernel_emitter.md)
- [`spec/dsl/gen_kernel/emit_context.md`](../../../spec/dsl/gen_kernel/emit_context.md)
- [`spec/dsl/gen_kernel/emit.md`](../../../spec/dsl/gen_kernel/emit.md)

## 目标

- 保持 `gen_kernel(...)` 为唯一稳定公开入口。
- 避免在本模块内再维护第二份 emit 逻辑或 target 特化逻辑。

## 限制与边界

- 本模块不定义节点级 emit 细节；这些由 `emit/` 子系统负责。
- 本模块不对外暴露内部函数级 helper。
- 若输入为普通 op，只允许直接委托节点级 `emit_c_op(...)`。

## 测试

- 测试文件：[`test/dsl/gen_kernel/test_gen_kernel.py`](../../../test/dsl/gen_kernel/test_gen_kernel.py)
- 执行命令：`pytest -q test/dsl/gen_kernel/test_gen_kernel.py`
- 测试目标：
  - `gen_kernel(...)` 入口稳定
  - 普通 op / `func.func` / 受控 `builtin.module` 路径保持当前合同
