# gen_kernel.md

## 功能简介

- 定义 `kernel_gen.dsl.gen_kernel.gen_kernel` 模块的公开入口合同。
- 该模块只负责 `gen_kernel(...)` 公开包装：
  - 组装当前目录中的完整源码发射 helper
  - 绑定节点级 `emit_c_op(...)`
  - 为完整源码补 `emit_include()`
  - 把内部 `EmitCError` 折回 `GenKernelError`
- `KernelEmitter`、`emit_include()` 与 `kernel_emitter.py` 中的辅助步骤仍可作为当前目录内部协作实现存在，但不属于当前文件公开 API。

## API 列表

- `GenKernelError(message: str)`
- `gen_kernel(obj: object, ctx: EmitCContext) -> str`

## 文档信息

- 创建者：`小李飞刀`
- 最后一次更改：`睡觉小分队`
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
- 让 pass/pipeline 输出的 host wrapper + device body 双函数 IR 统一经由 `gen_kernel(...)` 消费，不要求调用方感知内部 emitter 拆分。

## 限制与边界

- 本模块不定义节点级 emit 细节；这些由 `emit/` 子系统负责。
- 本模块不对外暴露内部函数级 helper。
- 若输入为普通 op，只允许直接委托节点级 `emit_c_op(...)`。
- `KernelEmitter`、`kernel_emitter.py` 内的 `_` 前缀 helper 与 `emit_include()` 都不是当前文件公开 API；实现、其他模块与测试不得把它们当成稳定跨文件入口。

## 测试

- 测试文件：[`test/dsl/gen_kernel/test_gen_kernel.py`](../../../test/dsl/gen_kernel/test_gen_kernel.py)
- 包根公开入口测试：[`test/dsl/test_package_api.py`](../../../test/dsl/test_package_api.py)
- 执行命令：`pytest -q test/dsl/gen_kernel/test_gen_kernel.py`
- 测试目标：
  - `gen_kernel(...)` 入口稳定
  - package-root 导出列表与 legacy 入口拒绝保持稳定
  - 普通 op / `func.func` / 受控 `builtin.module` 路径保持当前合同
  - host wrapper + device body 双函数 IR 可经由 `gen_kernel(...)` 直接生成完整源码
  - 测试只通过 `gen_kernel(...)` 与 `GenKernelError` 验收，不直连 `KernelEmitter` 或 `kernel_emitter.py` helper
