# outline_device_kernel.md

## 功能简介

- 定义 `outline-device-kernel` pass 的公开合同：把显式标记的 device 风格 `func.func` outline 成 `host wrapper + device body` 双函数 IR。
- 首轮能力固定为纯 IR host launch outline：触发仍只消费 `launch_block / launch_thread / launch_subthread` 三项显式属性，不从 target registry、函数名或 IR 结构做隐式推断；`shared_memory_size` 作为 device metadata 与 wrapper 的第 4 个 `arch.launch` extent 一并承接。
- 首轮 ABI 边界固定为“只接受零返回 / 已完成 out-param ABI 的 `func.func`”；命中非空返回值时显式报错，不在本轮同步承担返回值改写。

## 文档信息

- 创建者：`咯咯咯`
- 最后一次更改：`咯咯咯`
- `spec`：[`spec/pass/outline_device_kernel.md`](../../../spec/pass/outline_device_kernel.md)
- `功能实现`：
  - [`kernel_gen/passes/outline_device_kernel.py`](../../../kernel_gen/passes/outline_device_kernel.py)
  - [`kernel_gen/passes/lowering/__init__.py`](../../../kernel_gen/passes/lowering/__init__.py)
  - [`kernel_gen/passes/registry.py`](../../../kernel_gen/passes/registry.py)
- `test`：
  - [`test/pass/outline_device_kernel/test_outline_device_kernel.py`](../../../test/pass/outline_device_kernel/test_outline_device_kernel.py)
  - [`test/pass/test_pass_registry.py`](../../../test/pass/test_pass_registry.py)
  - [`test/pass/test_pipeline_default_lowering.py`](../../../test/pass/test_pipeline_default_lowering.py)

## 依赖

- Pass 管理与排序：[`spec/pass/pass_manager.md`](../../../spec/pass/pass_manager.md)
- pass 注册表：[`spec/pass/registry.md`](../../../spec/pass/registry.md)
- 默认 pipeline 边界：[`spec/pass/pipeline/default_lowering.md`](../../../spec/pass/pipeline/default_lowering.md)
- `arch.launch` IR 语义：[`spec/dialect/arch.md`](../../../spec/dialect/arch.md)
- 前置 ABI 改写能力：[`spec/pass/lowering/buffer_results_to_out_params.md`](../../../spec/pass/lowering/buffer_results_to_out_params.md)

## 术语

- `host wrapper`：保留原函数名、只负责常量 launch extent、单个 `arch.launch` 与 `func.return` 的 host 侧 wrapper。
- `device body`：由原函数主体改写得到的新 `func.func @<orig>_device`。
- `trigger attrs`：`launch_block / launch_thread / launch_subthread` 三项显式属性；三者必须同时存在才能触发 outline。
- `metadata-plus-launch-extent`：`shared_memory_size` 仅保留在 outlined device function 的 `func.func attributes` 中，并作为 host wrapper 的第 4 个 `arch.launch` extent operand 一并写出。

## 目标

- 固定 pass 公开名称：`outline-device-kernel`。
- 固定实现唯一入口：[`kernel_gen/passes/outline_device_kernel.py`](../../../kernel_gen/passes/outline_device_kernel.py)。
- 固定触发合同：只对带 `launch_block / launch_thread / launch_subthread` 三项属性的 `func.func` 生效。
- 固定输出 IR 形状：原函数名保留为 host wrapper，新函数名固定追加 `_device`。
- 固定首轮 ABI 边界：只接受零返回 / 已完成 out-param ABI 的输入。
- 固定默认 pipeline 边界：`default-lowering remains unchanged`，`outline-device-kernel` 作为 standalone pass 单独启用。

## 限制与边界

- 本 pass 是 standalone lowering pass，不自动并入 `default-lowering`。
- 只允许 `launch_block / launch_thread / launch_subthread` 三项属性同时存在时触发；不允许属性缺省、默认 extent 或启发式推断。
- 输入 `func.func` 必须是零返回；若上游已完成 out-param ABI，本 pass 直接沿用该零返回签名；命中非空返回值时必须显式报错。
- host wrapper 保留原函数名与原参数顺序，且函数体只允许 outline pass 新增的 extent 常量、单个 `arch.launch` 与 `func.return`。
- device body 函数名固定为 `@<orig>_device`，继承原参数顺序与原主体 op 序列。
- wrapper 上不得保留 `launch_block / launch_thread / launch_subthread`；`shared_memory_size` 若存在，只保留在 device function attributes 上，并由 wrapper 的 `arch.launch` 透传为第 4 个 extent operand。
- `shared_memory_size` 仅做 metadata 合法性校验：需要是 int-like attr，且值必须大于等于 `0`；本轮扩展 `arch.launch` op 的第 4 个 extent operand，但不改写其它 op 属性形状。
- 旧路径 `kernel_gen.passes.lowering.outline_device_kernel` 只保留兼容导入，不再承载独立实现文件。
- 本轮范围排除 `gen_kernel(target="npu_demo")` / `ctx` 专用适配，也不把 `buffer-results-to-out-params` 并入本 pass 职责面。

## 公开接口

### `class OutlineDeviceKernelError(ValueError)`

功能说明：

- 表示 `outline-device-kernel` pass 的稳定错误类型。

参数说明：

- `message (str)`：错误文本。

使用示例：

```python
raise OutlineDeviceKernelError("outline-device-kernel requires zero-result func.func")
```

注意事项：

- 非空返回值、属性缺失、非法 extent、非法 `shared_memory_size` 或命名冲突等显式失败路径都应统一抛出该错误。

返回与限制：

- 抛错即终止当前 pass。

### `class OutlineDeviceKernelPass(Pass)`

功能说明：

- 对带显式 launch 属性的 `func.func` 执行 host launch outline。

参数说明：

- 无参数。

使用示例：

```python
from kernel_gen.passes.outline_device_kernel import OutlineDeviceKernelPass

module = OutlineDeviceKernelPass().run(module)
```

注意事项：

- 公开 pass 名称固定为 `outline-device-kernel`。
- 只接受零返回 / 已完成 out-param ABI 的输入函数。
- `default-lowering remains unchanged`；若调用方需要 host launch outline，必须显式追加本 pass。

返回与限制：

- 返回改写后的同一 `ModuleOp`。

### `build_registered_pass("outline-device-kernel")`

功能说明：

- 通过 registry 的稳定 pass 名称构造 `OutlineDeviceKernelPass`。

参数说明：

- `name (str)`：固定为 `outline-device-kernel`。

使用示例：

```python
from kernel_gen.passes.registry import build_registered_pass, load_builtin_passes

load_builtin_passes()
pass_obj = build_registered_pass("outline-device-kernel")
module = pass_obj.run(module)
```

注意事项：

- 构造前必须先调用 `load_builtin_passes()`。
- 首轮不接受 `options`。

返回与限制：

- 返回 `Pass` 实例。

### 输入触发合同：`func.func` launch attrs

功能说明：

- 定义 pass 触发所需的输入函数属性与 ABI 约束。

参数说明：

- `launch_block (int-like)`：block extent。
- `launch_thread (int-like)`：thread extent。
- `launch_subthread (int-like)`：subthread extent。
- `shared_memory_size (int-like | optional)`：device metadata。

使用示例：

```text
func.func @matmul_kernel(%lhs: !nn.memory<...>, %rhs: !nn.memory<...>, %out: !nn.memory<...>) attributes {
  launch_block = 1 : i64,
  launch_thread = 4 : i64,
  launch_subthread = 1 : i64,
  shared_memory_size = 0 : i64
} {
  ...
  func.return
}
```

注意事项：

- 三项 launch 属性必须同时存在。
- extent 必须能规整为正整数语义的 `!symbol.int`。
- `shared_memory_size` 若存在，必须是 int-like attr，且值必须大于等于 `0`。
- 输入函数必须是零返回；非空返回值显式失败。

返回与限制：

- 满足合同的函数可被 outline；未标记函数保持原样。

### 输出 IR 合同：`host wrapper + device body`

功能说明：

- 定义 outline 后 host wrapper 与 device body 的最小公开 IR 形状。

参数说明：

- 无参数。

使用示例：

```text
builtin.module {
  func.func @matmul_kernel(%lhs: !nn.memory<...>, %rhs: !nn.memory<...>, %out: !nn.memory<...>) {
    %b = symbol.const 1 : !symbol.int<"1">
    %t = symbol.const 4 : !symbol.int<"4">
    %s = symbol.const 1 : !symbol.int<"1">
    arch.launch<%b, %t, %s, %smem>(@matmul_kernel_device, %lhs, %rhs, %out)
    func.return
  }

  func.func @matmul_kernel_device(%lhs: !nn.memory<...>, %rhs: !nn.memory<...>, %out: !nn.memory<...>)
  attributes {shared_memory_size = 0 : i64} {
    ...
    func.return
  }
}
```

注意事项：

- wrapper 中应出现且只出现单个 `arch.launch`。
- wrapper 上不保留 `launch_block / launch_thread / launch_subthread`。
- device function 名称固定追加 `_device`。
- `shared_memory_size` 只留在 device function attributes。

返回与限制：

- 输出 IR 保持零返回 ABI，不引入隐式返回值改写。

## 测试

- 测试文件：[`test/pass/outline_device_kernel/test_outline_device_kernel.py`](../../../test/pass/outline_device_kernel/test_outline_device_kernel.py)
- 执行命令：`pytest -q test/pass/outline_device_kernel/test_outline_device_kernel.py`
- 测试目标：锁定显式 launch attrs 触发、双函数输出形状、`shared_memory_size` 校验、兼容导入与非空返回失败路径。

- 测试文件：[`test/pass/test_pass_registry.py`](../../../test/pass/test_pass_registry.py)
- 执行命令：`pytest -q test/pass/test_pass_registry.py -k outline_device_kernel`
- 测试目标：锁定 `outline-device-kernel` 的 registry 名称与构造入口。

- 测试文件：[`test/pass/test_pipeline_default_lowering.py`](../../../test/pass/test_pipeline_default_lowering.py)
- 执行命令：`pytest -q test/pass/test_pipeline_default_lowering.py`
- 测试目标：锁定 `default-lowering remains unchanged`，不把 `outline-device-kernel` 混入默认 pipeline。

- 功能与用例清单：
  - `HL-ODK-001`：显式 `launch_block / launch_thread / launch_subthread` 三项属性同时存在时才触发 outline。
  - `HL-ODK-002`：输出 IR 固定为 `@name + @name_device` 双函数形状，wrapper 中只保留单个 `arch.launch`。
  - `HL-ODK-003`：非空返回值输入显式失败，不承担 ABI 改写。
  - `HL-ODK-004`：`shared_memory_size` 只保留在 device function attributes，但 wrapper 必须把它透传为 `arch.launch` 的第 4 个 extent operand。
  - `HL-ODK-005`：`shared_memory_size` 非 int-like 或负值时显式失败。
  - `HL-ODK-006`：`default-lowering remains unchanged`，调用方必须显式追加 `outline-device-kernel`。
