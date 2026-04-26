# kernel_emitter.md

## 功能简介

- 定义 `KernelEmitter` 的函数级 / module 级源码生成合同。
- 该模块负责：
  - `func.func` 的签名与函数体组织
  - `builtin.module` 的受控 module 组织
  - `target="npu_demo"` 的 wrapper/body 骨架收口

## API 列表

- `GenKernelError`
- `KernelEmitter`
  - `—— init(ctx: EmitCContext, emit_op=emit_c_op)`
  - `—— emit(obj: object)`
  - `—— emit_include()`
  - `—— emit_op(op)`
  - `—— emit_type(attr)`
  - `—— emit_attr(attr)`
  - `—— emit_value(value)`
  - `—— emit_module(module_op)`
  - `—— emit_func(func_op)`

## 文档信息

- 创建者：`金铲铲大作战`
- 最后一次更改：`OpenAI Codex`
- `spec`：[`spec/dsl/gen_kernel/kernel_emitter.md`](../../../spec/dsl/gen_kernel/kernel_emitter.md)
- `功能实现`：[`kernel_gen/dsl/gen_kernel/kernel_emitter.py`](../../../kernel_gen/dsl/gen_kernel/kernel_emitter.py)
- `test`：[`test/dsl/gen_kernel/test_gen_kernel.py`](../../../test/dsl/gen_kernel/test_gen_kernel.py)

## 依赖

- [`spec/dsl/gen_kernel/emit_context.md`](../../../spec/dsl/gen_kernel/emit_context.md)
- [`spec/dsl/gen_kernel/emit.md`](../../../spec/dsl/gen_kernel/emit.md)
- [`spec/include/npu_demo/npu_demo.md`](../../../spec/include/npu_demo/npu_demo.md)

## 目标

- 让 `KernelEmitter` 成为唯一函数级 emitter。
- 保持公开方法最小集合稳定，其余逻辑留在内部 helper。

## 限制与边界

- 除 `API 列表` 列出的公开方法外，其余函数 / 方法都属于内部实现细节。
- launch wrapper 识别、tile contract fail-fast、默认 return 收尾等逻辑不得作为公开 API 暴露。
- 非公开 helper 必须使用 `_` 前缀，且不得跨文件直接调用。

## 测试

- 测试文件：[`test/dsl/gen_kernel/test_gen_kernel.py`](../../../test/dsl/gen_kernel/test_gen_kernel.py)
- 执行命令：`pytest -q test/dsl/gen_kernel/test_gen_kernel.py`
- 测试目标：
  - `KernelEmitter` 公开方法可驱动完整源码生成
  - `npu_demo` body/wrapper 合同与默认路径保持稳定
