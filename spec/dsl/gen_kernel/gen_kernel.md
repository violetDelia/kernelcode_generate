# gen_kernel.md

## 功能简介

- 定义 `kernel_gen.dsl.gen_kernel` 目录在源码生成层的公开入口合同。
- 本轮新增的公开能力只有 `dsl_gen_kernel(...)` callable 入口；现有 `gen_kernel(obj, ctx)` 必须继续作为稳定 IR / op 源码生成入口保留。
- `dsl_gen_kernel(...)` 必须复用公开 `mlir_gen(...) + gen_kernel(...)` 链路，不允许在当前目录外跨文件直连 parser、module-builder 或 `kernel_emitter.py` 非公开 helper 来复制第二套 emitter。
- 包根 `kernel_gen.dsl.gen_kernel` 继续承接 sibling spec 已定义的 `EmitCContext`、`EmitCError`、`emit_c(...)`、`emit_c_op(...)`、`emit_c_value(...)` 与 `KernelEmitter`；本文件只展开 `GenKernelError`、`gen_kernel(...)` 与新增 `dsl_gen_kernel(...)` 这组入口。
- 当前文件内若保留参数归一化、目标默认值或兼容失败 helper，它们都只属于文件内实现细节，不属于公开 API。

## API 列表

- `GenKernelError(message: str)`
- `gen_kernel(obj: object, ctx: EmitCContext) -> str`
- `dsl_gen_kernel(fn: Callable[..., object], *runtime_args: object, ctx: EmitCContext, config: dict[str, object] | None = None) -> str`

## 文档信息

- 创建者：`小李飞刀`
- 最后一次更改：`咯咯咯`
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

- 为 `kernel_gen.dsl.gen_kernel` 包根新增 `dsl_gen_kernel(...)` callable 公开入口。
- 保持 `kernel_gen.dsl.gen_kernel` 包根导出与当前实现、pytest 一致。
- 保持 `gen_kernel(...)` 为源码级主入口，不回退到旧 `gen_signature` / `gen_body` 双接口。
- 避免在本模块内再维护第二份 emit 逻辑或 target 特化逻辑。
- 让 pass/pipeline 输出的 host wrapper + device body 双函数 IR 统一经由 `gen_kernel(...)` 消费，不要求调用方感知内部 emitter 拆分。

## 限制与边界

- 本模块不定义节点级 emit 细节；这些由 `emit/` 子系统负责。
- `dsl_gen_kernel(...)` 只接受 Python DSL callable + `runtime_args`；实现必须先调用公开 `mlir_gen(fn, *runtime_args, config=config)` 生成 `builtin.module`，再调用公开 `gen_kernel(module_or_func, ctx)` 生成源码。
- `gen_kernel(...)` 继续只消费 op / `func.func` / 受控 `builtin.module` IR；`dsl_gen_kernel(...)` 不是 `gen_kernel(...)` 的别名模式，也不能接管 `dsl_run`、`ircheck` 这类已有 IR 路径消费者。
- 本文件当前允许实现的公开入口只有 `GenKernelError`、`gen_kernel(...)` 与 `dsl_gen_kernel(...)`；除 sibling spec 已单独定义的包根 re-export 外，不得再新增平行 callable 别名或隐藏快捷入口。
- 若输入为普通 op，只允许直接委托节点级 `emit_c_op(...)`。
- `KernelEmitter`、`kernel_emitter.py` 内的 `_` 前缀 helper、`mlir_gen` 子系统的 parse-env / module-builder 私有 helper，以及 `emit_include()` 都不是当前文件公开 API；实现、其他模块与测试不得把它们当成稳定跨文件入口。
- package-root 仍必须稳定拒绝 `gen_signature` / `gen_body` 这类旧公开名；新增 `dsl_gen_kernel(...)` 不得回退这条 legacy 拒绝合同。

## 测试

- 测试文件：[`test/dsl/gen_kernel/test_gen_kernel.py`](../../../test/dsl/gen_kernel/test_gen_kernel.py)
- 包根公开入口测试：[`test/dsl/test_package_api.py`](../../../test/dsl/test_package_api.py)
- 执行命令：`pytest -q test/dsl/gen_kernel/test_gen_kernel.py`
- 测试目标：
  - `dsl_gen_kernel(...)` 可直接接受 Python DSL callable 与 `runtime_args` 生成源码，且输出与公开 `mlir_gen(...) + gen_kernel(...)` 组合路径一致
  - `gen_kernel(...)` 入口稳定
  - package-root 导出集合新增 `dsl_gen_kernel(...)`，同时保留已有 sibling public exports
  - package-root 导出列表与 legacy 入口拒绝保持稳定
  - 普通 op / `func.func` / 受控 `builtin.module` 路径保持当前合同
  - host wrapper + device body 双函数 IR 可经由 `gen_kernel(...)` 直接生成完整源码
  - `dsl_run(...)`、`ircheck` 相关回归继续只锁公开 `gen_kernel(op|func|module, ctx)` 旧 IR 路径，不把 `dsl_gen_kernel(...)` 当成替代入口
  - 测试只通过 `dsl_gen_kernel(...)`、`gen_kernel(...)`、package-root 导入和 `GenKernelError` 验收，不直连 `KernelEmitter`、`kernel_emitter.py` helper、`mlir_gen` 私有 helper 或其他跨文件非公开 API
