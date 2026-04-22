# npu_demo_lowering.md

## 功能简介

- 定义 `npu-demo-lowering` pipeline 的公开合同与 pass 顺序。
- 公开 builder：`build_npu_demo_lowering_pipeline()`。
- 该 pipeline 面向 `dsl_run` 的 `npu_demo` 正向链路，固定为最小可执行 lowering 组合，并在末尾输出可供 `gen_kernel(target="npu_demo")` 消费的 host wrapper + device body 双函数 IR。

## 文档信息

- 创建者：`朽木露琪亚`
- 最后一次更改：`朽木露琪亚`
- `spec`：[`spec/pass/pipeline/npu_demo_lowering.md`](../../../spec/pass/pipeline/npu_demo_lowering.md)
- `功能实现`：[`kernel_gen/passes/pipeline/npu_demo_lowering.py`](../../../kernel_gen/passes/pipeline/npu_demo_lowering.py)
- `test`：[`test/pass/test_pipeline_npu_demo_lowering.py`](../../../test/pass/test_pipeline_npu_demo_lowering.py)

## 依赖

- Pass 管理与排序：[`spec/pass/pass_manager.md`](../../../spec/pass/pass_manager.md)
- 注册表：[`spec/pass/registry.md`](../../../spec/pass/registry.md)
- `decompass` 公开入口：[`spec/pass/decompass.md`](../../../spec/pass/decompass.md)
- `nn` lowering：[`spec/pass/lowering/nn_lowering.md`](../../../spec/pass/lowering/nn_lowering.md)
- `symbol-loop-hoist`：[`spec/pass/symbol_loop_hoist.md`](../../../spec/pass/symbol_loop_hoist.md)
- `outline-device-kernel` 公开入口：[`spec/pass/outline_device_kernel.md`](../../../spec/pass/outline_device_kernel.md)

## 术语

- `npu-demo-lowering`：`dsl_run` 的 npu_demo 正向 pipeline 名称。
- `inline`：该 pipeline 的首个内联/展开阶段，作为 `dsl_run` 的前置规范化步骤。
- `lower-nn`：`NnLoweringPass` 的公开 pass 名称。
- `symbol-loop-hoist`：`SymbolLoopHoistPass` 的公开 pass 名称。
- `attach-arch-information`：在 outline 前为目标函数附加 launch / shared memory 等 arch 元信息的阶段。
- `outline-device-kernel`：将带 arch 元信息的函数 outline 成 host wrapper + device body 的阶段。

## 目标

- 提供一条不依赖 `tile` 的最小公开 pipeline，供 `dsl_run` 正向合同与 pytest 直接复用。
- 明确 `symbol-loop-hoist` 在无 `symbol.for` 时可以 no-op，因此可安全加入该最小 pipeline。
- 明确该 pipeline 的最终输出为 host wrapper + device body 双函数 IR，供 `gen_kernel(target="npu_demo")` 直接消费。
- 保持 `default-lowering` 作为独立公开 builder，不与本 pipeline 混用。

## 限制与边界

- builder 必须返回 `PassManager`。
- builder 必须通过 `register_pipeline("npu-demo-lowering")` 注册。
- builder 不接受 `options`；`only-kernel`、`only_kernel` 或其他选项都必须显式失败。
- 公开顺序必须固定为：
  1. `inline`
  2. `DecompassPass`
  3. `NnLoweringPass`
  4. `SymbolLoopHoistPass`
  5. `attach-arch-information`
  6. `OutlineDeviceKernelPass`
- 该 pipeline 不包含 `tile`、`buffer-results-to-out-params` 或 `lower-dma-memory-hierarchy`。
- 若输入 module 中不存在 `symbol.for`，`SymbolLoopHoistPass` 必须保持 no-op。

## 公开接口

### `build_npu_demo_lowering_pipeline() -> PassManager`

功能说明：

- 构造 `npu-demo-lowering` pipeline，并返回 `PassManager`。

参数说明：

- 无参数。

使用示例：

```python
from kernel_gen.passes.pipeline import build_npu_demo_lowering_pipeline

pm = build_npu_demo_lowering_pipeline()
module = pm.run(module)
```

注意事项：

- pipeline 名称必须固定为 `npu-demo-lowering`。
- pass 顺序必须固定为 `inline -> decompass -> lower-nn -> symbol-loop-hoist -> attach-arch-information -> outline-device-kernel`。
- 该 pipeline 是 `dsl_run` 的正向主合同，不要求 `tile` 先行。
- 该 pipeline 不接受 `only-kernel` 选项；任何 options 输入都必须显式失败。

返回与限制：

- 返回 `PassManager` 实例。

## 测试

- 测试文件：[`test/pass/test_pipeline_npu_demo_lowering.py`](../../../test/pass/test_pipeline_npu_demo_lowering.py)
- 执行命令：`pytest -q test/pass/test_pipeline_npu_demo_lowering.py`
- 测试目标：
  - builder 返回 `PassManager`
  - pipeline 名称为 `npu-demo-lowering`
  - pass 顺序固定为 `inline -> decompass -> lower-nn -> symbol-loop-hoist -> attach-arch-information -> outline-device-kernel`
  - `symbol-loop-hoist` 在无 `symbol.for` 时可安全加入该 pipeline
  - pipeline 输出 host wrapper + device body 双函数 IR
  - `only-kernel` / `only_kernel` options 显式失败
