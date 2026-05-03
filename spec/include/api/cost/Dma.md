# Dma

## 功能简介

定义 include/api/cost 层统一对外的 DMA 成本 helper 规范（`include/api/cost/Dma.h`），作为 `tuner.cost(op_name="dma.*")` 在 `target=npu_demo` 下的稳定 C++ 承接层。

- 当前成功路径覆盖 `tuner.cost(op_name="dma.copy") -> npu_demo::cost::copy(...)` 与 `tuner.cost(op_name="dma.slice" | "dma.deslice") -> npu_demo::cost::{slice, deslice}(...)`。
- `slice` / `deslice` 成本 helper 的模板顺序与参数顺序必须与 `include/api/Dma.h` 对齐。
- `alloc` 当前不属于成本 helper 输入域；`launch-kernel-cost-func` 现阶段不会为 `dma.alloc` 生成 `tuner.cost`。

## API 列表

- `template <MemorySpace TargetSpace, MemorySpace SourceSpace, typename T, CostKind Kind> S_INT npu_demo::cost::copy(const Memory<TargetSpace, T>& target, const Memory<SourceSpace, T>& source)`
- `template <MemorySpace TargetSpace, MemorySpace SourceSpace, typename T, CostKind Kind> S_INT npu_demo::cost::slice(const Memory<TargetSpace, T>& target, const Memory<SourceSpace, T>& source, const Vector& offset, const Vector& size, const Vector& stride)`
- `template <MemorySpace TargetSpace, MemorySpace SourceSpace, typename T, CostKind Kind> S_INT npu_demo::cost::deslice(const Memory<TargetSpace, T>& target, const Memory<SourceSpace, T>& source, const Vector& offset, const Vector& size, const Vector& stride)`

## 文档信息

- 创建者：`未记录`
- 最后一次更改：`小李飞刀`
- `spec`：[`spec/include/api/cost/Dma.md`](../../../../spec/include/api/cost/Dma.md)
- `统一头文件`：[`include/api/cost/Dma.h`](../../../../include/api/cost/Dma.h)
- `功能实现`：[`include/npu_demo/cost/Dma.h`](../../../../include/npu_demo/cost/Dma.h)
- `test`：
  - `test/include/api/test_cost.py`
  - [`test/dsl/gen_kernel/emit/test_package.py`](../../../../test/dsl/gen_kernel/emit/test_package.py)
  - [`test/dsl/gen_kernel/test_gen_kernel.py`](../../../../test/dsl/gen_kernel/test_gen_kernel.py)

## 依赖

- [`spec/include/api/cost/Core.md`](./Core.md)：提供 `CostKind` 与 `S_INT` 基础合同。
- [`spec/include/api/Dma.md`](../../../../spec/include/api/Dma.md)：提供 `slice` / `deslice` 的参数顺序与类型来源。
- [`spec/include/api/Memory.md`](../../../../spec/include/api/Memory.md)：提供 `Memory<Space, T>` 与 `MemorySpace` 语义。
- [`spec/dsl/gen_kernel/emit.md`](../../../../spec/dsl/gen_kernel/emit.md)：消费 `tuner.cost(op_name="dma.copy" | "dma.slice" | "dma.deslice")` 的节点级文本合同。

## 目标

- 提供 `dma.copy`、`dma.slice` 与 `dma.deslice` 的稳定成本 helper 名：`npu_demo::cost::copy/slice/deslice`。
- 统一 DMA 成本 helper 的返回类型为 `S_INT`。
- 固定 `slice` / `deslice` 成本 helper 与 `Dma` 公共 helper 的参数顺序一致，便于后续直接扩展。

## 额外补充

### 模块级补充

- 本小节只记录模块级非接口补充；接口级参数限制、错误语义、兼容要求与非目标必须维护在对应 API 的 `注意事项`。
- 当前 `emit_c/gen_kernel(target="npu_demo")` 的 Dma 成本成功路径至少覆盖 `dma.copy -> cost::copy` 与 `dma.slice/deslice -> cost::slice/deslice`。
- `alloc` 没有对应成本 helper；若后续需要表达分配成本，应在新专题里单独补公开合同。
- `slice` / `deslice` 是 `npu-demo-lowering` pipeline 末尾 cost pass 的可发射成本 helper；不得扩展到 `alloc` 或未定义的 DMA 旧别名。
- 成本 helper 不负责搬运真实数据，也不替代 [`spec/include/api/Dma.md`](../../../../spec/include/api/Dma.md) 的运行时 DMA public function。

## API详细说明

### `template <MemorySpace TargetSpace, MemorySpace SourceSpace, typename T, CostKind Kind> S_INT npu_demo::cost::copy(const Memory<TargetSpace, T>& target, const Memory<SourceSpace, T>& source)`

- api：`template <MemorySpace TargetSpace, MemorySpace SourceSpace, typename T, CostKind Kind> S_INT npu_demo::cost::copy(const Memory<TargetSpace, T>& target, const Memory<SourceSpace, T>& source)`
- 参数：
  - `target`：目标对象、目标名称或目标缓冲区，指定当前操作写入或作用的位置；类型 `const Memory<TargetSpace, T>&`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
  - `source`：源对象、源缓冲区或源文本，提供当前操作读取的数据来源；类型 `const Memory<SourceSpace, T>&`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
- 返回值：`S_INT`。
- 使用示例：

  ```cpp
  #include "include/npu_demo/npu_demo.h"

  using namespace npu_demo;
  S_INT copy_cost = cost::copy<TSM, GM, float, memory>(target, source);
  ```
- 功能说明：定义 `tuner.cost(op_name="dma.copy")` 的稳定 C++ 成本 helper。
- 注意事项：输入 memory 和 dtype 必须符合 DMA operation 合同；参数顺序固定为 `target -> source`；模板顺序固定为 `TargetSpace -> SourceSpace -> T -> Kind`；当前不接收 `offset`、`size` 或 `stride`，这些由 `slice` / `deslice` 成本 helper 表达；非法组合必须稳定失败。

### `template <MemorySpace TargetSpace, MemorySpace SourceSpace, typename T, CostKind Kind> S_INT npu_demo::cost::slice(const Memory<TargetSpace, T>& target, const Memory<SourceSpace, T>& source, const Vector& offset, const Vector& size, const Vector& stride)`

- api：`template <MemorySpace TargetSpace, MemorySpace SourceSpace, typename T, CostKind Kind> S_INT npu_demo::cost::slice(const Memory<TargetSpace, T>& target, const Memory<SourceSpace, T>& source, const Vector& offset, const Vector& size, const Vector& stride)`
- 参数：
  - `target`：目标对象、目标名称或目标缓冲区，指定当前操作写入或作用的位置；类型 `const Memory<TargetSpace, T>&`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
  - `source`：源对象、源缓冲区或源文本，提供当前操作读取的数据来源；类型 `const Memory<SourceSpace, T>&`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
  - `offset`：偏移序列或起始偏移，指定切片、访存或源码定位的起点；类型 `const Vector&`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
  - `size`：尺寸序列或元素数量，指定切片、缓冲区或范围的大小；类型 `const Vector&`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
  - `stride`：步长序列，定义各维度在底层线性布局中的跨距；类型 `const Vector&`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
- 返回值：`S_INT`。
- 使用示例：

  ```cpp
  #include "include/npu_demo/npu_demo.h"

  using namespace npu_demo;
  S_INT slice_cost = cost::slice<TSM, GM, float, memory>(target, source, offset, size, stride);
  ```
- 功能说明：定义 `tuner.cost(op_name="dma.slice")` 的稳定 C++ 成本 helper。
- 注意事项：输入 memory、offset、size、stride 和 dtype 必须符合 DMA operation 合同；参数顺序与 [`spec/include/api/Dma.md`](../../../../spec/include/api/Dma.md) 的 `slice` 完全一致；模板顺序固定为 `TargetSpace -> SourceSpace -> T -> Kind`；不得扩展为 `alloc` 成本 helper 或未定义 DMA 旧别名；非法组合必须稳定失败。

### `template <MemorySpace TargetSpace, MemorySpace SourceSpace, typename T, CostKind Kind> S_INT npu_demo::cost::deslice(const Memory<TargetSpace, T>& target, const Memory<SourceSpace, T>& source, const Vector& offset, const Vector& size, const Vector& stride)`

- api：`template <MemorySpace TargetSpace, MemorySpace SourceSpace, typename T, CostKind Kind> S_INT npu_demo::cost::deslice(const Memory<TargetSpace, T>& target, const Memory<SourceSpace, T>& source, const Vector& offset, const Vector& size, const Vector& stride)`
- 参数：
  - `target`：目标对象、目标名称或目标缓冲区，指定当前操作写入或作用的位置；类型 `const Memory<TargetSpace, T>&`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
  - `source`：源对象、源缓冲区或源文本，提供当前操作读取的数据来源；类型 `const Memory<SourceSpace, T>&`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
  - `offset`：偏移序列或起始偏移，指定切片、访存或源码定位的起点；类型 `const Vector&`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
  - `size`：尺寸序列或元素数量，指定切片、缓冲区或范围的大小；类型 `const Vector&`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
  - `stride`：步长序列，定义各维度在底层线性布局中的跨距；类型 `const Vector&`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
- 返回值：`S_INT`。
- 使用示例：

  ```cpp
  #include "include/npu_demo/npu_demo.h"

  using namespace npu_demo;
  S_INT deslice_cost = cost::deslice<GM, TSM, float, memory>(target, source, offset, size, stride);
  ```
- 功能说明：定义 `tuner.cost(op_name="dma.deslice")` 的稳定 C++ 成本 helper。
- 注意事项：输入 memory、offset、size、stride 和 dtype 必须符合 DMA operation 合同；参数顺序与 [`spec/include/api/Dma.md`](../../../../spec/include/api/Dma.md) 的 `deslice` 完全一致；模板顺序固定为 `TargetSpace -> SourceSpace -> T -> Kind`；不得扩展为 `alloc` 成本 helper 或未定义 DMA 旧别名；非法组合必须稳定失败。

## 测试

- 测试文件：
  - `test/dsl/gen_kernel/emit/test_package.py`
  - `test/dsl/gen_kernel/test_gen_kernel.py`
  - `test/include/api/test_cost.py`
- 执行命令：
  - `pytest -q test/include/api/test_cost.py`
  - `pytest -q test/dsl/gen_kernel/emit/test_package.py -k "tuner_cost or npu_demo"`
  - `pytest -q test/dsl/gen_kernel/test_gen_kernel.py -k "tuner_cost or cost_function or npu_demo"`

### 测试目标

- 通过当前聚合入口 `test_include_api_cost_dma_signatures_compile` 一次性验证 `copy`、`slice`、`deslice` 的模板顺序、参数顺序与 `S_INT` 返回合同。
- 验证 `tuner.cost(op_name="dma.copy" | "dma.slice" | "dma.deslice")` 的节点级文本发射。
- 验证完整 cost function 生成后可消费 `cost::copy`。

### 功能与用例清单

| 用例 ID | 功能 | 场景 | 前置条件 | 操作 | 预期结果 | 建议测试 |
| --- | --- | --- | --- | --- | --- | --- |
| TC-COST-DMA-001 | 生成/编译 | `cost::copy` 独立实例化 | 准备公开 DSL/IR 输入、目标配置与源码生成入口。 | 运行 `test_include_api_cost_dma_signatures_compile`。 | 生成源码、IR 文本或编译结果体现“`cost::copy` 独立实例化”场景。 | `test_include_api_cost_dma_signatures_compile` |
| TC-COST-DMA-002 | 生成/编译 | `cost::slice` / `cost::deslice` 独立实例化 | 准备公开 DSL/IR 输入、目标配置与源码生成入口。 | 运行 `test_include_api_cost_dma_signatures_compile`。 | 生成源码、IR 文本或编译结果体现“`cost::slice` / `cost::deslice` 独立实例化”场景。 | `test_include_api_cost_dma_signatures_compile` |
| TC-COST-DMA-003 | pass 改写 | `emit_c` 节点级发射 `dma.copy` 成本调用 | 准备包含目标 op、pass 名称或 pipeline 的公开 IR 输入。 | 运行 `test_emit_c_lowers_npu_demo_tuner_cost_dma_copy`。 | IR 改写后的 op、属性、顺序或 no-op 行为体现“`emit_c` 节点级发射 `dma.copy` 成本调用”场景。 | `test_emit_c_lowers_npu_demo_tuner_cost_dma_copy` |
| TC-COST-DMA-004 | pass 改写 | `emit_c` 节点级发射 `dma.slice/deslice` 成本调用 | 准备包含目标 op、pass 名称或 pipeline 的公开 IR 输入。 | 运行 `test_emit_c_lowers_npu_demo_tuner_cost_dma_slice_and_deslice`。 | IR 改写后的 op、属性、顺序或 no-op 行为体现“`emit_c` 节点级发射 `dma.slice/deslice` 成本调用”场景。 | `test_emit_c_lowers_npu_demo_tuner_cost_dma_slice_and_deslice` |
