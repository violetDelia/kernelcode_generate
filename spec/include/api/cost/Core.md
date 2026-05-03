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

- 创建者：`未记录`
- 最后一次更改：`小李飞刀`
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

## 额外补充

### 模块级补充

- 本小节只记录模块级非接口补充；接口级参数限制、错误语义、兼容要求与非目标必须维护在对应 API 的 `注意事项`。
- 本规范不定义真实成本模型、查表行为或返回值含义；当前 `npu_demo` 默认实现统一返回 `0`。
- 本规范只接受 `Compute`、`Memory`、`DMA` 与 `MAC` 四个公开 kind；不再公开 `Kind2`、`Kind3`、`All` 或 target 配置驱动的额外 kind。
- `CostKind` 只表达“统计视角”，不替代 IR 里的 `cost_kind` 字符串 verifier 逻辑。
- `include/api/cost/Core.h` 只定义公共声明；默认实现由 `include/npu_demo/cost/Core.h` 承接。

## API详细说明

### `namespace npu_demo::cost`

- api：`namespace npu_demo::cost`
- 参数：无。
- 返回值：`cost` 的返回值；返回类型以 API 签名为准。
- 使用示例：

  ```cpp
namespace cost_api = npu_demo::cost;
```
- 功能说明：承载全部 cost helper 与基础成本枚举的统一命名空间。
- 注意事项：`cost` 只作为 `namespace npu_demo` 下的子命名空间公开；不得回退到全局 `cost::...` 或 `npu_demo::detail::...`。

### `enum class npu_demo::cost::CostKind { Compute, Memory, DMA, MAC }`

- api：`enum class npu_demo::cost::CostKind { Compute, Memory, DMA, MAC }`
- 参数：无。
- 返回值：公开枚举类型对象。
- 使用示例：

  ```cpp
auto kind = npu_demo::cost::CostKind::Compute;
```
- 功能说明：定义当前公开的成本统计视角枚举。
- 注意事项：稳定成员仅包含 `Compute`、`Memory`、`DMA`、`MAC`；生成源码不得继续出现 `Kind2`、`Kind3` 或其他旧枚举值。

### `inline constexpr npu_demo::cost::CostKind npu_demo::compute`

- api：`inline constexpr npu_demo::cost::CostKind npu_demo::compute`
- 参数：无。
- 返回值：`npu_demo::cost::CostKind` 常量值。
- 使用示例：

  ```cpp
auto kind = npu_demo::compute;
```
- 功能说明：定义 `compute` 公开常量。
- 注意事项：`compute` 等价于 `npu_demo::cost::CostKind::Compute`；生成源码应直接透传该 kind，不在 emit 阶段改写成其他枚举文本。

### `inline constexpr npu_demo::cost::CostKind npu_demo::memory`

- api：`inline constexpr npu_demo::cost::CostKind npu_demo::memory`
- 参数：无。
- 返回值：`npu_demo::cost::CostKind` 常量值。
- 使用示例：

  ```cpp
auto kind = npu_demo::memory;
```
- 功能说明：定义 `memory` 公开常量。
- 注意事项：`memory` 等价于 `npu_demo::cost::CostKind::Memory`；生成源码应直接透传该 kind，不在 emit 阶段改写成其他枚举文本。

### `inline constexpr npu_demo::cost::CostKind npu_demo::DMA`

- api：`inline constexpr npu_demo::cost::CostKind npu_demo::DMA`
- 参数：无。
- 返回值：`npu_demo::cost::CostKind` 常量值。
- 使用示例：

  ```cpp
auto kind = npu_demo::DMA;
```
- 功能说明：定义 `DMA` 公开常量。
- 注意事项：`DMA` 等价于 `npu_demo::cost::CostKind::DMA`；生成源码应直接透传该 kind，不在 emit 阶段改写成其他枚举文本。

### `inline constexpr npu_demo::cost::CostKind npu_demo::MAC`

- api：`inline constexpr npu_demo::cost::CostKind npu_demo::MAC`
- 参数：无。
- 返回值：`npu_demo::cost::CostKind` 常量值。
- 使用示例：

  ```cpp
auto kind = npu_demo::MAC;
```
- 功能说明：定义 `MAC` 公开常量。
- 注意事项：`MAC` 等价于 `npu_demo::cost::CostKind::MAC`；生成源码应直接透传该 kind，不在 emit 阶段改写成其他枚举文本。

## 测试

- 测试文件：
  - `test/include/api/test_cost.py`
  - `test/include/npu_demo/test_cost.py`
- 执行命令：
  - `pytest -q test/include/api/test_cost.py`
  - `pytest -q test/include/npu_demo/test_cost.py`

### 测试目标

- 验证 `CostKind::{Compute, Memory, DMA, MAC}`、`compute/memory/DMA/MAC` 与 `S_INT` 返回合同可独立 include、可模板实例化。
- 验证 `include/npu_demo/cost/Core.h` 的默认实现与 `include/npu_demo/npu_demo.h` 聚合入口一致。

### 功能与用例清单

| 用例 ID | 功能 | 场景 | 前置条件 | 操作 | 预期结果 | 建议测试 |
| --- | --- | --- | --- | --- | --- | --- |
| TC-COST-CORE-001 | 公开入口 | 独立 include `include/api/cost/Core.h` | 按 spec 声明的导入路径、CLI 参数、注册名或命名空间访问公开入口。 | 运行 `test_include_api_cost_core_exports_compute_and_memory`。 | 公开入口在“独立 include `include/api/cost/Core.h`”场景下可导入、构造、注册或按名称发现。 | `test_include_api_cost_core_exports_compute_and_memory` |
| TC-COST-CORE-002 | 公开入口 | `npu_demo` 聚合入口包含 cost core | 按 spec 声明的导入路径、CLI 参数、注册名或命名空间访问公开入口。 | 运行 `test_npu_demo_cost_core_is_visible_from_public_namespace`。 | 公开入口在“`npu_demo` 聚合入口包含 cost core”场景下可导入、构造、注册或按名称发现。 | `test_npu_demo_cost_core_is_visible_from_public_namespace` |
