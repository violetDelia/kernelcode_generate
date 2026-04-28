# Core

## 功能简介

定义 include/api/cost 层统一对外的基础成本类型规范（`include/api/cost/Core.h`），为 `tuner.cost -> emit_c/gen_kernel(target=npu_demo)` 的 helper 发射提供统一 kind 与返回类型边界。

- 当前公共层收口 `npu_demo::cost::CostKind`、`npu_demo::{compute, memory, DMA, MAC}` 四个模板实参别名，以及“全部 cost helper 返回 `S_INT`”这三类基础合同。
- `CostKind` 只代表成本统计视角，不携带 target、device func 或 evaluator 细节。
- `cost/Core` 不定义具体 `Kernel` 或 `Dma` helper 形态；这些由 [`Kernel.md`](./Kernel.md) 与 [`Dma.md`](./Dma.md) 承接。

## API 列表

- `namespace npu_demo::cost`
- `enum class npu_demo::cost::CostKind { Compute, Memory, DMA, MAC }`
- `inline constexpr npu_demo::cost::CostKind npu_demo::compute`
- `inline constexpr npu_demo::cost::CostKind npu_demo::memory`
- `inline constexpr npu_demo::cost::CostKind npu_demo::DMA`
- `inline constexpr npu_demo::cost::CostKind npu_demo::MAC`

## 文档信息

- 创建者：`睡觉小分队`
- 最后一次更改：`睡觉小分队`
- `spec`：[`spec/include/api/cost/Core.md`](../../../../spec/include/api/cost/Core.md)
- `统一头文件`：[`include/api/cost/Core.h`](../../../../include/api/cost/Core.h)
- `功能实现`：[`include/npu_demo/cost/Core.h`](../../../../include/npu_demo/cost/Core.h)
- `test`：
  - `test/include/api/test_cost.py`
  - `test/include/npu_demo/test_cost.py`

## 依赖

- [`spec/include/api/Core.md`](../../../../spec/include/api/Core.md)：提供 `S_INT` 与基础状态类型边界。
- [`spec/include/npu_demo/npu_demo.md`](../../../../spec/include/npu_demo/npu_demo.md)：定义 `npu_demo` 聚合入口与 `namespace npu_demo` 的消费方向。

## 目标

- 固定成本视角枚举：`npu_demo::cost::CostKind::{Compute, Memory, DMA, MAC}`。
- 固定生成源码使用的 kind 别名：`npu_demo::{compute, memory, DMA, MAC}`。
- 固定全部 cost helper 的返回类型：`S_INT`。
- 为 `include/api/cost/Kernel.h`、`include/api/cost/Dma.h`、`emit_c(target="npu_demo")` 与 `gen_kernel(target="npu_demo")` 提供统一基础类型来源。

## 限制与边界

- 本规范不定义真实成本模型、查表行为或返回值含义；当前 `npu_demo` 默认实现统一返回 `0`。
- 本规范只接受 `Compute`、`Memory`、`DMA` 与 `MAC` 四个公开 kind；不再公开 `Kind2`、`Kind3`、`All` 或 target 配置驱动的额外 kind。
- `CostKind` 只表达“统计视角”，不替代 IR 里的 `cost_kind` 字符串 verifier 逻辑。
- `include/api/cost/Core.h` 只定义公共声明；默认实现由 `include/npu_demo/cost/Core.h` 承接。

## 公开接口

### `namespace npu_demo::cost`

功能说明：

- 承载全部 cost helper 与基础成本枚举的统一命名空间。

参数说明：

- 无参数。

使用示例：

```cpp
#include "include/npu_demo/npu_demo.h"

using namespace npu_demo;
cost::CostKind kind = compute;
```

注意事项：

- `cost` 只作为 `namespace npu_demo` 下的子命名空间公开；不得回退到全局 `cost::...` 或 `npu_demo::detail::...`。
- `emit_c/gen_kernel(target="npu_demo")` 生成源码时，允许在 `using namespace npu_demo;` 后同时使用 `cost::...` 与裸 `compute/memory/DMA/MAC`。

返回与限制：

- 返回类型：`namespace`。
- 限制条件：本轮只承接成本 helper 与 kind 枚举，不承接运行时调度或 evaluator 工具。

### `enum class CostKind`

功能说明：

- 定义当前公开的成本统计视角。

参数说明：

- 无参数。

使用示例：

```cpp
cost::CostKind compute_kind = cost::CostKind::Compute;
cost::CostKind memory_kind = cost::CostKind::Memory;
cost::CostKind dma_kind = cost::CostKind::DMA;
cost::CostKind mac_kind = cost::CostKind::MAC;
```

注意事项：

- `Compute` 对应 IR `cost_kind = "compute"`。
- `Memory` 对应 IR `cost_kind = "memory"`。
- `DMA` 对应 IR `cost_kind = "DMA"`。
- `MAC` 对应 IR `cost_kind = "MAC"`。
- 生成源码不得继续出现 `Kind2`、`Kind3` 或其他旧枚举值。

返回与限制：

- 返回类型：`enum class CostKind`。
- 限制条件：当前只公开 `Compute`、`Memory`、`DMA` 与 `MAC`。

### `constexpr compute / memory / DMA / MAC`

功能说明：

- 公开给 `emit_c/gen_kernel(target="npu_demo")` 直接透传的 kind 模板实参别名。

参数说明：

- 无参数。

使用示例：

```cpp
S_INT copy_cost = cost::copy<TSM, GM, float, memory>(target, source);
S_INT dma_cost = cost::copy<TSM, GM, float, DMA>(target, source);
S_INT mac_cost = cost::add<GM, float, float, MAC>(out, lhs, rhs);
```

注意事项：

- `compute` 等价于 `cost::CostKind::Compute`。
- `memory` 等价于 `cost::CostKind::Memory`。
- `DMA` 等价于 `cost::CostKind::DMA`。
- `MAC` 等价于 `cost::CostKind::MAC`。
- 生成源码应直接透传 IR 中的 `cost_kind` 文本，不再在 emit 阶段把 `compute/memory/DMA/MAC` 改写成 `CostKind::...`。

返回与限制：

- 返回类型：`constexpr cost::CostKind`。
- 限制条件：当前只公开 `compute`、`memory`、`DMA` 与 `MAC`。

### cost helper 公共返回语义

功能说明：

- 约束 `include/api/cost/Kernel.h` 与 `include/api/cost/Dma.h` 中全部 helper 的返回类型。

参数说明：

- 无参数。

使用示例：

```cpp
S_INT cost0 = compute == compute ? 0 : 0;
```

注意事项：

- 所有 cost helper 都返回 `S_INT`，不返回 `Status`、`Memory`、`double` 或 target 私有结构体。
- `S_INT` 的定义来源是 [`spec/include/api/Core.md`](../../../../spec/include/api/Core.md)。

返回与限制：

- 返回类型：`S_INT`。
- 返回语义：表示局部或函数级成本的整数承接值。
- 限制条件：本轮不定义非整数或带状态码的成本返回形态。

## 测试

- 测试文件：`test/include/api/test_cost.py`
- 执行命令：`pytest -q test/include/api/test_cost.py`
- 测试目标：验证 `CostKind::{Compute, Memory, DMA, MAC}`、`compute/memory/DMA/MAC` 与 `S_INT` 返回合同可独立 include、可模板实例化。

- 测试文件：`test/include/npu_demo/test_cost.py`
- 执行命令：`pytest -q test/include/npu_demo/test_cost.py`
- 测试目标：验证 `include/npu_demo/cost/Core.h` 的默认实现与 `include/npu_demo/npu_demo.h` 聚合入口一致。

### 功能与用例清单

| 用例 ID | 场景 | 预期结果 | 对应测试 |
| --- | --- | --- | --- |
| COST-CORE-001 | 独立 include `include/api/cost/Core.h` | 可见 `npu_demo::cost::CostKind::{Compute, Memory, DMA, MAC}` 与 `npu_demo::{compute, memory, DMA, MAC}` | `test_include_api_cost_core_exports_compute_and_memory` |
| COST-CORE-002 | `npu_demo` 聚合入口包含 cost core | `include/npu_demo/npu_demo.h` 可直接消费 `cost::CostKind` | `test_npu_demo_cost_core_is_visible_from_public_namespace` |
