# gen_kernel.md

## 功能简介

- 定义 `kernel_gen.dsl.gen_kernel` 包根的公开入口合同。
- 包根当前稳定导出 `GenKernelError`、`KernelEmitter`、`EmitCContext`、`EmitCError`、`gen_kernel(...)`、`emit_c(...)`、`emit_c_op(...)`、`emit_c_value(...)`。
- 其中 `gen_kernel(...)` 负责公开包装：
  - 构造 `KernelEmitter`
  - 绑定节点级 `emit_c_op(...)`
  - 为完整源码补 `emit_include()`
  - 把内部 `EmitCError` 折回 `GenKernelError`

## API 列表

- `GenKernelError(message: str)`
- `KernelEmitter(ctx: EmitCContext, *, emit_op: Callable[[Operation, EmitCContext], str] = emit_c_op)`
- `EmitCContext(target: str, indent: str = "    ", naming: Any | None = None, type_converter: Any | None = None, config: dict[str, Any] | None = None)`
- `EmitCError(message: str)`
- `gen_kernel(op_or_func: object, ctx: EmitCContext) -> str`
- `emit_c(op_or_module, ctx: EmitCContext) -> str`
- `emit_c_op(op, ctx: EmitCContext) -> str`
- `emit_c_value(value, ctx: EmitCContext) -> str`

## 公开 API 清单

- `GenKernelError(message: str)`
- `KernelEmitter(ctx: EmitCContext, *, emit_op: Callable[[Operation, EmitCContext], str] = emit_c_op)`
- `EmitCContext(target: str, indent: str = "    ", naming: Any | None = None, type_converter: Any | None = None, config: dict[str, Any] | None = None)`
- `EmitCError(message: str)`
- `gen_kernel(op_or_func: object, ctx: EmitCContext) -> str`
- `emit_c(op_or_module, ctx: EmitCContext) -> str`
- `emit_c_op(op, ctx: EmitCContext) -> str`
- `emit_c_value(value, ctx: EmitCContext) -> str`

## helper 清单

- 无

## 文档信息

- 创建者：`小李飞刀`
- 最后一次更改：`朽木露琪亚`
- `spec`：[`spec/dsl/gen_kernel/gen_kernel.md`](../../../spec/dsl/gen_kernel/gen_kernel.md)
- `功能实现`：[`kernel_gen/dsl/gen_kernel/__init__.py`](../../../kernel_gen/dsl/gen_kernel/__init__.py)
- `功能实现`：[`kernel_gen/dsl/gen_kernel/gen_kernel.py`](../../../kernel_gen/dsl/gen_kernel/gen_kernel.py)
- `test`：[`test/dsl/gen_kernel/test_gen_kernel.py`](../../../test/dsl/gen_kernel/test_gen_kernel.py)
- `test`：[`test/dsl/test_package_api.py`](../../../test/dsl/test_package_api.py)

## 依赖

- [`spec/dsl/gen_kernel/kernel_emitter.md`](../../../spec/dsl/gen_kernel/kernel_emitter.md)
- [`spec/dsl/gen_kernel/emit_context.md`](../../../spec/dsl/gen_kernel/emit_context.md)
- [`spec/dsl/gen_kernel/emit.md`](../../../spec/dsl/gen_kernel/emit.md)

## 目标

- 保持 `kernel_gen.dsl.gen_kernel` 包根导出与当前实现、pytest 一致。
- 保持 `gen_kernel(...)` 为源码级主入口，不回退到旧 `gen_signature` / `gen_body` 双接口。
- 避免在本模块内再维护第二份 emit 逻辑或 target 特化逻辑。

## 限制与边界

- 本模块不定义节点级 emit 细节；这些由 `emit/` 子系统负责。
- 本模块不对外暴露内部函数级 helper。
- 若输入为普通 op，只允许直接委托节点级 `emit_c_op(...)`。

## 测试

- 测试文件：[`test/dsl/gen_kernel/test_gen_kernel.py`](../../../test/dsl/gen_kernel/test_gen_kernel.py)
- 包根公开入口测试：[`test/dsl/test_package_api.py`](../../../test/dsl/test_package_api.py)
- 执行命令：`pytest -q test/dsl/gen_kernel/test_gen_kernel.py`
- 测试目标：
  - `gen_kernel(...)` 入口稳定
  - package-root 导出列表与 legacy 入口拒绝保持稳定
  - 普通 op / `func.func` / 受控 `builtin.module` 路径保持当前合同
