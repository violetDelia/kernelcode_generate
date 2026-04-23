# Dma

## 功能简介

定义 include/api/cost 层统一对外的 DMA 成本 helper 规范（`include/api/cost/Dma.h`），作为 `tuner.cost(op_name="dma.*")` 在 `target=npu_demo` 下的稳定 C++ 承接层。

- 当前最小成功路径是 `tuner.cost(op_name="dma.copy") -> npu_demo::cost::copy(...)`。
- 为保持目录结构与 `include/api/Dma.h` 一致，本文件也约束 `slice` / `deslice` 成本 helper 的模板顺序与参数顺序。
- `alloc` 当前不属于成本 helper 输入域；`launch-kernel-cost-func` 现阶段不会为 `dma.alloc` 生成 `tuner.cost`。

## 文档信息

- 创建者：`睡觉小分队`
- 最后一次更改：`睡觉小分队`
- `spec`：[`spec/include/api/cost/Dma.md`](../../../../spec/include/api/cost/Dma.md)
- `统一头文件`：[`include/api/cost/Dma.h`](../../../../include/api/cost/Dma.h)
- `功能实现`：[`include/npu_demo/cost/Dma.h`](../../../../include/npu_demo/cost/Dma.h)
- `test`：
  - `test/include/api/test_cost.py`
  - [`test/dsl/test_emit_c.py`](../../../../test/dsl/test_emit_c.py)
  - [`test/dsl/test_gen_kernel.py`](../../../../test/dsl/test_gen_kernel.py)

## 依赖

- [`spec/include/api/cost/Core.md`](./Core.md)：提供 `CostKind` 与 `S_INT` 基础合同。
- [`spec/include/api/Dma.md`](../../../../spec/include/api/Dma.md)：提供 `slice` / `deslice` 的参数顺序与类型来源。
- [`spec/include/api/Memory.md`](../../../../spec/include/api/Memory.md)：提供 `Memory<Space, T>` 与 `MemorySpace` 语义。
- [`spec/dsl/emit_c.md`](../../../../spec/dsl/emit_c.md)：消费 `tuner.cost(op_name="dma.copy")` 的节点级文本合同。

## 目标

- 提供 `dma.copy` 的稳定成本 helper 名：`npu_demo::cost::copy`。
- 统一 DMA 成本 helper 的返回类型为 `S_INT`。
- 固定 `slice` / `deslice` 成本 helper 与 `Dma` 公共 helper 的参数顺序一致，便于后续直接扩展。

## 限制与边界

- 当前 `emit_c/gen_kernel(target="npu_demo")` 的 Dma 成本成功路径至少覆盖 `dma.copy -> cost::copy`。
- `alloc` 没有对应成本 helper；若后续需要表达分配成本，应在新专题里单独补公开合同。
- `slice` / `deslice` 只作为本轮目录镜像与模板顺序的统一约束；若下游未生成对应 `tuner.cost(op_name)`，不得擅自引入额外 IR 名称。
- 成本 helper 不负责搬运真实数据，也不替代 [`spec/include/api/Dma.md`](../../../../spec/include/api/Dma.md) 的运行时 DMA public function。

## 公开接口

### `copy`

功能说明：

- 定义 `tuner.cost(op_name="dma.copy")` 的稳定 C++ 成本 helper。

参数说明：

- `TargetSpace (template MemorySpace)`：目标空间模板参数。
- `SourceSpace (template MemorySpace)`：源空间模板参数。
- `T (template type)`：元素类型。
- `Kind (template CostKind)`：成本统计视角。
- `target (const Memory<TargetSpace, T>&)`：目标视图。
- `source (const Memory<SourceSpace, T>&)`：源视图。

使用示例：

```cpp
#include "include/npu_demo/npu_demo.h"

using namespace npu_demo;
S_INT cost0 = cost::copy<TSM, GM, float, cost::CostKind::Memory>(target, source);
```

注意事项：

- `copy` 是当前 Dma 成本路径的最低公开集合。
- 参数顺序固定为 `target -> source`。
- 模板顺序固定为 `TargetSpace -> SourceSpace -> T -> Kind`。

返回与限制：

- 返回类型：`S_INT`。
- 限制条件：当前不接收 `offset/size/stride`；这些由 `slice` / `deslice` 成本 helper 表达。

### `slice` / `deslice`

功能说明：

- 定义与 [`spec/include/api/Dma.md`](../../../../spec/include/api/Dma.md) 对齐的成本 helper 形态，供后续直接扩展。

参数说明：

- `TargetSpace (template MemorySpace)`：目标空间模板参数。
- `SourceSpace (template MemorySpace)`：源空间模板参数。
- `T (template type)`：元素类型。
- `Kind (template CostKind)`：成本统计视角。
- `target (const Memory<TargetSpace, T>&)`：目标视图。
- `source (const Memory<SourceSpace, T>&)`：源视图。
- `offset (const Vector&)`：偏移。
- `size (const Vector&)`：逻辑大小。
- `stride (const Vector&)`：步进。

使用示例：

```cpp
using namespace npu_demo;
S_INT slice_cost = cost::slice<TSM, GM, float, cost::CostKind::Memory>(target, source, offset, size, stride);
S_INT deslice_cost = cost::deslice<GM, TSM, float, cost::CostKind::Memory>(target, source, offset, size, stride);
```

注意事项：

- 参数顺序与 [`spec/include/api/Dma.md`](../../../../spec/include/api/Dma.md) 完全一致。
- 模板顺序固定为 `TargetSpace -> SourceSpace -> T -> Kind`。
- 当下游尚未生成这两个 `op_name` 的 `tuner.cost` 时，本接口只提供声明层合同，不要求额外扩 IR 名称。

返回与限制：

- 返回类型：`S_INT`。
- 限制条件：本轮不定义 `alloc` 成本 helper，也不定义额外 DMA 旧别名。

## 测试

- 测试文件：`test/include/api/test_cost.py`
- 执行命令：`pytest -q test/include/api/test_cost.py`
- 测试目标：通过当前聚合入口 `test_include_api_cost_dma_signatures_compile` 一次性验证 `copy`、`slice`、`deslice` 的模板顺序、参数顺序与 `S_INT` 返回合同。

- 测试文件：[`test/dsl/test_emit_c.py`](../../../../test/dsl/test_emit_c.py)
- 执行命令：`pytest -q test/dsl/test_emit_c.py -k "tuner_cost or npu_demo"`
- 测试目标：验证 `tuner.cost(op_name="dma.copy")` 的节点级文本发射。

- 测试文件：[`test/dsl/test_gen_kernel.py`](../../../../test/dsl/test_gen_kernel.py)
- 执行命令：`pytest -q test/dsl/test_gen_kernel.py -k "tuner_cost or cost_function or npu_demo"`
- 测试目标：验证完整 cost function 生成后可消费 `cost::copy`。

- 合同验收资产：`expectation/dsl/emit_c/npu_demo/cost/dma_copy.py`

### 功能与用例清单

| 用例 ID | 场景 | 预期结果 | 对应测试 |
| --- | --- | --- | --- |
| COST-DMA-001 | `cost::copy` 独立实例化 | 模板顺序为 `TargetSpace -> SourceSpace -> T -> Kind`，返回 `S_INT` | `test_include_api_cost_dma_signatures_compile` |
| COST-DMA-002 | `cost::slice` / `cost::deslice` 独立实例化 | 与 `Dma` 公共 helper 的参数顺序一致，且同一编译入口验证返回 `S_INT` | `test_include_api_cost_dma_signatures_compile` |
| COST-DMA-003 | `emit_c` 节点级发射 `dma.copy` 成本调用 | 生成 `cost::copy<...>(target, source)` | `test_emit_c_lowers_npu_demo_tuner_cost_dma_copy` |
