# outline_device_kernel.md

## 功能简介

- 定义 `outline-device-kernel` pass 的公开合同：把显式标记的 device 风格 `func.func` outline 成 `host wrapper + device body` 双函数 IR。
- 首轮能力固定为纯 IR host launch outline：触发仍只消费 `launch_block / launch_thread / launch_subthread` 三项显式属性，不从 target registry、函数名或 IR 结构做隐式推断；`shared_memory_size` 作为 device metadata 与 wrapper 的第 4 个 `arch.launch` extent 一并承接。
- 首轮 ABI 边界固定为“只接受零返回 / 已完成 out-param ABI 的 `func.func`”；命中非空返回值时显式报错，不在本轮同步承担返回值改写。
- 当前文件本轮只公开 `OutlineDeviceKernelPass` 及其执行入口；pattern、候选收集与 wrapper/device 改写步骤若存在，仅允许作为当前文件内部协作 helper 存在。

## API 列表

- `class OutlineDeviceKernelPass()`
- `OutlineDeviceKernelPass.apply(ctx: Context, module: ModuleOp) -> None`

## 文档信息

- 创建者：`未记录`
- 最后一次更改：`小李飞刀`
- `spec`：[`spec/pass/outline_device_kernel.md`](../../../spec/pass/outline_device_kernel.md)
- `功能实现`：
  - [`kernel_gen/passes/outline_device_kernel.py`](../../../kernel_gen/passes/outline_device_kernel.py)
  - [`kernel_gen/passes/lowering/__init__.py`](../../../kernel_gen/passes/lowering/__init__.py)
  - [`kernel_gen/passes/registry.py`](../../../kernel_gen/passes/registry.py)
- `test`：
  - [`test/passes/test_outline_device_kernel.py`](../../../test/passes/test_outline_device_kernel.py)
  - [`test/passes/test_registry.py`](../../../test/passes/test_registry.py)

## 依赖

- Pass 管理与排序：[`spec/pass/pass_manager.md`](../../../spec/pass/pass_manager.md)
- pass 注册表：[`spec/pass/registry.md`](../../../spec/pass/registry.md)
- `npu-demo-lowering` pipeline 边界：[`spec/pass/pipeline/npu_demo_lowering.md`](../../../spec/pass/pipeline/npu_demo_lowering.md)
- `arch.launch` IR 语义：[`spec/dialect/arch.md`](../../../spec/dialect/arch.md)
- 前置 ABI 改写能力：[`spec/pass/buffer_results_to_out_params.md`](buffer_results_to_out_params.md)

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
- 固定 pipeline 分层：`outline-device-kernel` 既可 standalone 运行，也可作为 `npu-demo-lowering` 中 cost function 生成前的 outline 阶段；当前文件不扩展到 `default-lowering`。

## 额外补充

### 模块级补充

- 本小节只记录模块级非接口补充；接口级参数限制、错误语义、兼容要求与非目标必须维护在对应 API 的 `注意事项`。
- 本 pass 是 standalone lowering pass，也可被 `npu-demo-lowering` 复用；当前文件不把它并入 `default-lowering`。
- 只允许 `launch_block / launch_thread / launch_subthread` 三项属性同时存在时触发；不允许属性缺省、默认 extent 或启发式推断。
- 输入 `func.func` 必须是零返回；若上游已完成 out-param ABI，本 pass 直接沿用该零返回签名；命中非空返回值时必须显式报错。
- host wrapper 保留原函数名与原参数顺序，且函数体只允许 outline pass 新增的 extent 常量、单个 `arch.launch` 与 `func.return`。
- device body 函数名固定为 `@<orig>_device`，继承原参数顺序与原主体 op 序列。
- wrapper 上不得保留 `launch_block / launch_thread / launch_subthread`；`shared_memory_size` 若存在，只保留在 device function attributes 上，并由 wrapper 的 `arch.launch` 透传为第 4 个 extent operand。
- `shared_memory_size` 仅做 metadata 合法性校验：需要是 int-like attr，且值必须大于等于 `0`；本轮扩展 `arch.launch` op 的第 4 个 extent operand，但不改写其它 op 属性形状。
- 旧路径 `kernel_gen.passes.lowering.outline_device_kernel` 只保留兼容导入，不再承载独立实现文件。
- 公开错误类型统一使用 `kernel_gen.core.error.KernelCodeError`。
- 当前文件级公开 API 只包含 `OutlineDeviceKernelPass`；pattern、候选收集、属性规整与 wrapper/device 改写步骤不额外暴露文件级 helper，跨文件实现与测试不得直连这些内部步骤。
- 本轮范围排除 `gen_kernel(target="npu_demo")` / `ctx` 专用适配，也不把 `buffer-results-to-out-params` 并入本 pass 职责面。

### `class OutlineDeviceKernelPass(Pass)`

- 功能说明：

- 对带显式 launch 属性的 `func.func` 执行 host launch outline。

- 参数：

- 无参数。

- 使用示例：

```python
from kernel_gen.passes.outline_device_kernel import OutlineDeviceKernelPass

OutlineDeviceKernelPass().apply(Context(), module)
```

- 注意事项：

- 公开 pass 名称固定为 `outline-device-kernel`。
- 只接受零返回 / 已完成 out-param ABI 的输入函数。
- 可 standalone 运行，也可作为 `npu-demo-lowering` 中 `launch-kernel-cost-func` 前的 outline 阶段运行。
- `KernelCodeError` 仍是稳定错误类型，但它属于 `kernel_gen.passes` 共享公开 API，不新增为当前文件的独立公开入口。

- 返回值：

- 返回改写后的同一 `ModuleOp`。

### `build_registered_pass("outline-device-kernel")`

- 功能说明：

- 通过 registry 的稳定 pass 名称构造 `OutlineDeviceKernelPass`。
- 该入口属于 [`spec/pass/registry.md`](../../../spec/pass/registry.md) 的公开合同；当前文件只在 outline 语义层面补充与本 pass 对齐的约束。

- 参数：

- `name (str)`：固定为 `outline-device-kernel`。

- 使用示例：

```python
from kernel_gen.passes.registry import build_registered_pass, load_builtin_passes

load_builtin_passes()
pass_obj = build_registered_pass("outline-device-kernel")
pass_obj.apply(Context(), module)
```

- 注意事项：

- 构造前必须先调用 `load_builtin_passes()`。
- 首轮不接受 `options`。

- 返回值：

- 返回 `Pass` 实例。

### 输入触发合同：`func.func` launch attrs

- 功能说明：

- 定义 pass 触发所需的输入函数属性与 ABI 约束。

- 参数：

- `launch_block (int-like)`：block extent。
- `launch_thread (int-like)`：thread extent。
- `launch_subthread (int-like)`：subthread extent。
- `shared_memory_size (int-like | optional)`：device metadata。

- 使用示例：

```text
func.func @matmul_kernel(%lhs: !nn.memory<value>, %rhs: !nn.memory<value>, %out: !nn.memory<value>) attributes {
  launch_block = 1 : i64,
  launch_thread = 4 : i64,
  launch_subthread = 1 : i64,
  shared_memory_size = 0 : i64
} {
  value
  func.return
}
```

- 注意事项：

- 三项 launch 属性必须同时存在。
- extent 必须能规整为正整数语义的 `!symbol.int`。
- `shared_memory_size` 若存在，必须是 int-like attr，且值必须大于等于 `0`。
- 输入函数必须是零返回；非空返回值显式失败。

- 返回值：

- 满足合同的函数可被 outline；未标记函数保持原样。

### 输出 IR 合同：`host wrapper + device body`

- 功能说明：

- 定义 outline 后 host wrapper 与 device body 的最小公开 IR 形状。

- 参数：

- 无参数。

- 使用示例：

```text
builtin.module {
  func.func @matmul_kernel(%lhs: !nn.memory<value>, %rhs: !nn.memory<value>, %out: !nn.memory<value>) {
    %b = symbol.const 1 : !symbol.int<"1">
    %t = symbol.const 4 : !symbol.int<"4">
    %s = symbol.const 1 : !symbol.int<"1">
    arch.launch<%b, %t, %s, %smem>(@matmul_kernel_device, %lhs, %rhs, %out)
    func.return
  }

  func.func @matmul_kernel_device(%lhs: !nn.memory<value>, %rhs: !nn.memory<value>, %out: !nn.memory<value>)
  attributes {shared_memory_size = 0 : i64} {
    value
    func.return
  }
}
```

- 注意事项：

- wrapper 中应出现且只出现单个 `arch.launch`。
- wrapper 上不保留 `launch_block / launch_thread / launch_subthread`。
- device function 名称固定追加 `_device`。
- `shared_memory_size` 只留在 device function attributes。

- 返回值：

- 输出 IR 保持零返回 ABI，不引入隐式返回值改写。

## API详细说明

### `class OutlineDeviceKernelPass()`

- api：`class OutlineDeviceKernelPass()`
- 参数：无。
- 返回值：`OutlineDeviceKernelPass` 实例。
- 使用示例：

  ```python
  outline_device_kernel_pass = OutlineDeviceKernelPass()
  ```
- 功能说明：定义 `OutlineDeviceKernelPass` pass 对象。
- 注意事项：构造参数必须符合本条目参数说明；实例内部缓存、状态字典和派生字段不作为外部可变入口。

### `OutlineDeviceKernelPass.apply(ctx: Context, module: ModuleOp) -> None`

- api：`OutlineDeviceKernelPass.apply(ctx: Context, module: ModuleOp) -> None`
- 参数：
  - `ctx`：公开上下文对象，提供代码生成、emit、pass 或工具执行所需的配置与状态；类型 `Context`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
  - `module`：模块级 IR 对象，作为 pass、校验或代码生成的处理主体；类型 `ModuleOp`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
- 返回值：无返回值；调用成功表示操作完成。
- 使用示例：

  ```python
  outline_device_kernel_pass = outline_device_kernel_pass
  outline_device_kernel_pass.apply(ctx=ctx, module=module)
  ```
- 功能说明：对模块执行 `OutlineDeviceKernelPass` pass。
- 注意事项：非法输入必须按本条目参数说明和公开错误语义处理；调用方不得依赖实现内部状态。

## 测试

- 测试文件：
  - `test/passes/test_outline_device_kernel.py`
  - `test/passes/test_registry.py`
- 执行命令：
  - `pytest -q test/passes/test_outline_device_kernel.py`
  - `pytest -q test/passes/test_registry.py -k outline_device_kernel`

### 测试目标

- 锁定显式 launch attrs 触发、双函数输出形状、`shared_memory_size` 校验、兼容导入与非空返回失败路径，并仅通过 `OutlineDeviceKernelPass` 的公开入口验收。
- 锁定 `outline-device-kernel` 的 registry 名称与构造入口。

### 功能与用例清单

| 用例 ID | 功能 | 场景 | 前置条件 | 操作 | 预期结果 | 建议测试 |
| --- | --- | --- | --- | --- | --- | --- |
| TC-PASS-OUTLINE-DEVICE-KERNEL-001 | pass 改写 | 显式 `launch_block / launch_thread / launch_subthread` 三项属性同时存在时才触发 outline。 | 准备包含目标 op、pass 名称或 pipeline 的公开 IR 输入。 | 运行 `HL-ODK-001`。 | IR 改写后的 op、属性、顺序或 no-op 行为体现“显式 `launch_block / launch_thread / launch_subthread` 三项属性同时存在时才触发 outline。”场景。 | `HL-ODK-001` |
| TC-PASS-OUTLINE-DEVICE-KERNEL-002 | 执行结果 | 输出 IR 固定为 `@name + @name_device` 双函数形状，wrapper 中只保留单个 `arch.launch`。 | 准备公开输入数据、执行入口或 CLI 状态文件。 | 运行 `HL-ODK-002`。 | 命令返回码、输出、执行结果或状态变更体现“输出 IR 固定为 `@name + @name_device` 双函数形状，wrapper 中只保留单个 `arch.launch`。”场景。 | `HL-ODK-002` |
| TC-PASS-OUTLINE-DEVICE-KERNEL-003 | pass 改写 | 非空返回值输入显式失败，不承担 ABI 改写。 | 准备包含目标 op、pass 名称或 pipeline 的公开 IR 输入。 | 运行 `HL-ODK-003`。 | IR 改写后的 op、属性、顺序或 no-op 行为体现“非空返回值输入显式失败，不承担 ABI 改写。”场景。 | `HL-ODK-003` |
| TC-PASS-OUTLINE-DEVICE-KERNEL-004 | 内存/DMA | `shared_memory_size` 只保留在 device function attributes，但 wrapper 必须把它透传为 `arch.launch` 的第 4 个 extent operand。 | 准备公开 Memory/DMA 参数，包括 shape、stride、dtype、space 或切片元信息。 | 运行 `HL-ODK-004`。 | 内存类型、布局、搬运结果或 verifier 行为体现“`shared_memory_size` 只保留在 device function attributes，但 wrapper 必须把它透传为 `arch.launch` 的第 4 个 extent operand。”场景。 | `HL-ODK-004` |
| TC-PASS-OUTLINE-DEVICE-KERNEL-005 | 内存/DMA | `shared_memory_size` 非 int-like 或负值时显式失败。 | 准备公开 Memory/DMA 参数，包括 shape、stride、dtype、space 或切片元信息。 | 运行 `HL-ODK-005`。 | 内存类型、布局、搬运结果或 verifier 行为体现“`shared_memory_size` 非 int-like 或负值时显式失败。”场景。 | `HL-ODK-005` |
| TC-PASS-OUTLINE-DEVICE-KERNEL-006 | pass 改写 | `npu-demo-lowering` 复用本 pass 时仍保持上述双函数输出合同，不要求测试直连 pattern / getter / 当前文件内部 helper。 | 准备包含目标 op、pass 名称或 pipeline 的公开 IR 输入。 | 运行 `HL-ODK-006`。 | IR 改写后的 op、属性、顺序或 no-op 行为体现“`npu-demo-lowering` 复用本 pass 时仍保持上述双函数输出合同，不要求测试直连 pattern / getter / 当前文件内部 helper。”场景。 | `HL-ODK-006` |
