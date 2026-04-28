# attach_arch_information.md

## 功能简介

- 定义 `attach-arch-information` pass 的公开合同：从 target registry 读取 launch extent 与 `shared_memory_size`，并把 `launch_block / launch_thread / launch_subthread / shared_memory_size` 写回入口 `func.func`。
- 该 pass 不承担 outline 逻辑，只负责把 IR 级 launch 信息补齐到后续 `outline-device-kernel` 可消费的状态。
- 当前文件只公开 `AttachArchInformationPass` 的构造、registry 构造与 `run(module)` 入口；当前文件内校验、属性规整和错误前缀拼接 helper 若存在，均不属于公开 API。
- `apply(ctx, module)` 只保留为 xdsl `ModulePass` 协议 hook，不再作为旧业务兼容入口；实现与测试不得把它当成稳定跨文件 API。

## API 列表

- `class AttachArchInformationPass(target: str = "npu_demo")`
- `AttachArchInformationPass.from_options(options: dict[str, str]) -> AttachArchInformationPass`
- `AttachArchInformationPass.run(module: object) -> ModuleOp`

## 文档信息

- 创建者：`金铲铲大作战`
- 最后一次更改：`咯咯咯`
- `spec`：[`spec/pass/attach_arch_information.md`](../../../spec/pass/attach_arch_information.md)
- `功能实现`：[`kernel_gen/passes/attach_arch_information.py`](../../../kernel_gen/passes/attach_arch_information.py)
- `test`：[`test/pass/test_attach_arch_information.py`](../../../test/pass/test_attach_arch_information.py)

## 依赖

- Pass 管理与执行：[`spec/pass/pass_manager.md`](../../../spec/pass/pass_manager.md)
- pass 注册表：[`spec/pass/registry.md`](../../../spec/pass/registry.md)
- pass 公共错误：[`kernel_gen/passes/common.py`](../../../kernel_gen/passes/common.py)
- target 注册中心：[`spec/target/registry.md`](../../../spec/target/registry.md)
- `func.func` / `launch_*` IR 语义：[`spec/pass/outline_device_kernel.md`](../../../spec/pass/outline_device_kernel.md)

## 术语

- `entry func`：module 中唯一的非 declaration `func.func`，作为 attach 的默认入口。
- `launch extent`：从 target registry 读取的 `block_num / thread_num / subthread_num / sm_memory_size` 四层 launch 数值。

## 目标

- 为入口函数补齐 `launch_block / launch_thread / launch_subthread / shared_memory_size`。
- 让 `npu_demo` 的 launch extent 统一从 `kernel_gen/target/targets/npu_demo.txt` 读取。
- 若入口已存在 launch 属性，则必须与 target registry 的 extent 完全一致。

## 限制与边界

- 只接受 `builtin.module` 输入。
- 只对 module 中唯一的 non-declaration `func.func` 生效；缺失或多个时必须显式失败，不得静默选择首个函数。
- 四项 launch 属性必须同时存在；部分存在时必须显式失败。
- `launch_block / launch_thread / launch_subthread / shared_memory_size` 仅写回 `func.func attributes`，不扩展 `arch.launch` 形状。
- 当前文件的公开 API 只有 `AttachArchInformationPass`；不得跨文件调用当前文件模块级 helper、常量或错误文本规整步骤。
- `AttachArchInformationPass.run(module)` 是面向业务调用方与 pytest 的稳定执行入口；`apply(ctx, module)` 只允许由 `PassManager` / xdsl `ModulePass` 协议消费，不再承诺 `AttachArchInformationPass().apply(Context(), module)` 这条旧兼容用法。
- `apply(ctx, module)` 即使暂时不消费 `ctx` 里的业务信息，也不得通过 `del ctx` 或其他显式丢弃语句把该协议形参写成“已废弃入口”。
- 所有预期失败统一抛出 [`KernelCodeError`](../../../kernel_gen/passes/common.py)，错误消息仍以 `AttachArchInformationError:` 前缀开头，供测试做稳定匹配。

## 公开行为说明

### `AttachArchInformationPass` 构造与公开入口

功能说明：

- 为入口 `func.func` 补齐 launch extent。

使用示例：

```python
from kernel_gen.passes.attach_arch_information import AttachArchInformationPass

module = AttachArchInformationPass(target="npu_demo").run(module)
```

- `AttachArchInformationPass(target="npu_demo")`：按目标名构造 pass 实例。
- `AttachArchInformationPass.from_options({"target": "npu_demo"})`：通过 registry options 构造 pass。
- `AttachArchInformationPass.run(module)`：对业务调用方暴露稳定执行入口，并返回写回 launch 属性后的 `ModuleOp`。

使用示例：

```python
from kernel_gen.passes.attach_arch_information import AttachArchInformationPass

pass_obj = AttachArchInformationPass.from_options({"target": "npu_demo"})
module = AttachArchInformationPass(target="npu_demo").run(module)
```

注意事项：

- `run(module)` 必须与 registry / `PassManager` 路径保持同一公开语义。
- `apply(ctx, module)` 仍可作为 xdsl 框架 hook 存在，但它不是当前文件的业务公开 API；测试不得直连 `apply(...)` 验收本文件合同。

## 测试

- 测试文件：[`test/pass/test_attach_arch_information.py`](../../../test/pass/test_attach_arch_information.py)、[`test/pass/test_pass_registry.py`](../../../test/pass/test_pass_registry.py)、[`test/pass/test_pipeline_npu_demo_lowering.py`](../../../test/pass/test_pipeline_npu_demo_lowering.py)
- 执行命令：`pytest -q test/pass/test_attach_arch_information.py test/pass/test_pass_registry.py -k 'attach_arch_information or attach-arch-information'`
- 测试目标：
  - 公开导入路径只暴露 `AttachArchInformationPass`，不再暴露自定义错误类
  - target registry 的 launch extent 可以写回入口函数
  - module 中存在多个非 declaration `func.func` 时必须显式失败
  - 已存在 launch 属性时必须与 target registry 一致
  - 部分 launch 属性缺失时显式失败
  - registry 返回值与 `npu-demo-lowering` 固定顺序继续通过 `AttachArchInformationPass` 的公开名字生效
  - 测试只通过 `AttachArchInformationPass` 的公开构造 / `run(module)` 入口验收，不直连当前文件内非公开 helper，也不把 `apply(ctx, module)` 当业务 API
