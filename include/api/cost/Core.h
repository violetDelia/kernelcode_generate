/*
功能说明:
- 定义 include/api/cost/Core.h 的统一公共成本类型声明。
- 当前公开 `npu_demo::cost::CostKind::{Compute, Memory, DMA, MAC}`，并额外公开
  `npu_demo::{compute, memory, DMA, MAC}` 作为模板实参别名。
- 全部 cost helper 继续沿用 `S_INT` 作为返回类型来源。

API 列表:
- `namespace npu_demo::cost`
- `enum class npu_demo::cost::CostKind { Compute, Memory, DMA, MAC }`
- `inline constexpr npu_demo::cost::CostKind npu_demo::compute`
- `inline constexpr npu_demo::cost::CostKind npu_demo::memory`
- `inline constexpr npu_demo::cost::CostKind npu_demo::DMA`
- `inline constexpr npu_demo::cost::CostKind npu_demo::MAC`

helper 清单:
- 无；当前文件只声明公开 cost 基础类型。

使用示例:
- #include "include/api/cost/Core.h"
- npu_demo::cost::CostKind kind = npu_demo::compute;
- S_INT cost = 0;


关联文件:
- spec: spec/include/api/cost/Core.md
- test: test/include/api/cost.py
- 功能实现: include/npu_demo/cost/Core.h
*/

#ifndef KERNELCODE_GENERATE_INCLUDE_API_COST_CORE_H_
#define KERNELCODE_GENERATE_INCLUDE_API_COST_CORE_H_

#include "include/api/Core.h"

namespace npu_demo {
namespace cost {

/*
功能说明:
- 定义当前公开的成本统计视角。
- `Compute` 对应 IR `cost_kind = "compute"`；`Memory` 对应 IR `cost_kind = "memory"`。
- `DMA` 对应 IR `cost_kind = "DMA"`；`MAC` 对应 IR `cost_kind = "MAC"`。

使用示例:
- cost::CostKind compute_kind = cost::CostKind::Compute;
- cost::CostKind memory_kind = cost::CostKind::Memory;


关联文件:
- spec: spec/include/api/cost/Core.md
- test: test/include/api/cost.py
- 功能实现: include/npu_demo/cost/Core.h
*/
enum class CostKind {
    Compute,
    Memory,
    DMA,
    MAC,
};

}  // namespace cost

/*
功能说明:
- 公开 `emit_c/gen_kernel(target="npu_demo")` 直接透传的成本 kind 模板实参别名。
- 让生成源码可直接写出 `compute` / `memory` / `DMA` / `MAC`，不再在 emit 阶段做额外映射。

使用示例:
- S_INT add_cost = npu_demo::cost::add<GM, float, float, npu_demo::compute>(out, lhs, rhs);
- S_INT copy_cost = npu_demo::cost::copy<TSM, GM, float, npu_demo::memory>(target, source);


关联文件:
- spec: spec/include/api/cost/Core.md
- test: test/include/api/cost.py
- 功能实现: include/npu_demo/cost/Core.h
*/
inline constexpr cost::CostKind compute = cost::CostKind::Compute;
inline constexpr cost::CostKind memory = cost::CostKind::Memory;
inline constexpr cost::CostKind DMA = cost::CostKind::DMA;
inline constexpr cost::CostKind MAC = cost::CostKind::MAC;
}  // namespace npu_demo

#endif  // KERNELCODE_GENERATE_INCLUDE_API_COST_CORE_H_
