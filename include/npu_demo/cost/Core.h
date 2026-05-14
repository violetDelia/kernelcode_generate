/*
功能说明:
- 提供 include/api/cost/Core.h 的 npu_demo 默认承接层。
- 当前只复用公共 `CostKind` 与 `S_INT`，并承接 `DMA/DMA1/DMA2/DMA3/DMA4/MAC/VECTOR1/VECTOR2` kind 别名。

API 列表:
- `enum class npu_demo::cost::CostKind { DMA1, DMA2, DMA3, DMA4, MAC, VECTOR1, VECTOR2 }`
- `inline constexpr npu_demo::cost::CostKind npu_demo::DMA`
- `inline constexpr npu_demo::cost::CostKind npu_demo::DMA1`
- `inline constexpr npu_demo::cost::CostKind npu_demo::DMA2`
- `inline constexpr npu_demo::cost::CostKind npu_demo::DMA3`
- `inline constexpr npu_demo::cost::CostKind npu_demo::DMA4`
- `inline constexpr npu_demo::cost::CostKind npu_demo::MAC`
- `inline constexpr npu_demo::cost::CostKind npu_demo::VECTOR1`
- `inline constexpr npu_demo::cost::CostKind npu_demo::VECTOR2`

使用示例:
- #include "include/npu_demo/cost/Core.h"
- npu_demo::cost::CostKind kind = npu_demo::DMA1;


关联文件:
- spec: spec/include/api/cost/Core.md
- test: test/include/npu_demo/cost.py
- 功能实现: include/npu_demo/cost/Core.h
*/

#ifndef KERNELCODE_GENERATE_INCLUDE_NPU_DEMO_COST_CORE_H_
#define KERNELCODE_GENERATE_INCLUDE_NPU_DEMO_COST_CORE_H_

#include "include/api/cost/Core.h"

#endif  // KERNELCODE_GENERATE_INCLUDE_NPU_DEMO_COST_CORE_H_
