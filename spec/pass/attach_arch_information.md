# attach_arch_information.md

## 功能简介

- 定义 `attach-arch-information` pass 的公开合同：从 target registry 读取 launch extent 与 `shared_memory_size`，并把 `launch_block / launch_thread / launch_subthread / shared_memory_size` 写回入口 `func.func`。
- 该 pass 不承担 outline 逻辑，只负责把 IR 级 launch 信息补齐到后续 `outline-device-kernel` 可消费的状态。

## API 列表

- `AttachArchInformationPass`
  - `—— init(target: str = "npu_demo")`
  - `—— from_options(options: dict[str, str])`
  - `—— apply(ctx: Context, module: ModuleOp)`
  - `—— run(module: object) -> ModuleOp`

## 文档信息

- 创建者：`金铲铲大作战`
- 最后一次更改：`OpenAI Codex`
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
- 当前文件的公开 API 只有 `AttachArchInformationPass`；不得跨文件调用模块级 helper、常量或自定义错误，因为这些都不再公开存在。
- 所有预期失败统一抛出 [`PassContractError`](../../../kernel_gen/passes/common.py)，错误消息仍以 `AttachArchInformationError:` 前缀开头，供测试做稳定匹配。

## 公开接口

### `class AttachArchInformationPass`

功能说明：

- 为入口 `func.func` 补齐 launch extent。

使用示例：

```python
from kernel_gen.passes.attach_arch_information import AttachArchInformationPass

module = AttachArchInformationPass(target="npu_demo").run(module)
```

### `AttachArchInformationPass.from_options({"target": "npu_demo"})`

功能说明：

- 通过 registry options 构造 attach pass。

使用示例：

```python
from kernel_gen.passes.attach_arch_information import AttachArchInformationPass

pass_obj = AttachArchInformationPass.from_options({"target": "npu_demo"})
```

## 测试

- 测试文件：[`test/pass/test_attach_arch_information.py`](../../../test/pass/test_attach_arch_information.py)
- 执行命令：`pytest -q test/pass/test_attach_arch_information.py`
- 测试目标：
  - 公开导入路径只暴露 `AttachArchInformationPass`，不再暴露自定义错误类
  - target registry 的 launch extent 可以写回入口函数
  - module 中存在多个非 declaration `func.func` 时必须显式失败
  - 已存在 launch 属性时必须与 target registry 一致
  - 部分 launch 属性缺失时显式失败
