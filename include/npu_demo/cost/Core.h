/*
功能说明:
- 提供 include/api/cost/Core.h 的 npu_demo 默认承接层。
- 当前只复用公共 `CostKind` 与 `S_INT`，并承接 `compute/memory/DMA/MAC` 四个公开 kind 别名。

使用示例:
- #include "include/npu_demo/cost/Core.h"
- npu_demo::cost::CostKind kind = npu_demo::memory;


关联文件:
- spec: spec/include/api/cost/Core.md
- test: test/include/npu_demo/cost.py
- 功能实现: include/npu_demo/cost/Core.h
*/

#ifndef KERNELCODE_GENERATE_INCLUDE_NPU_DEMO_COST_CORE_H_
#define KERNELCODE_GENERATE_INCLUDE_NPU_DEMO_COST_CORE_H_

#include "include/api/cost/Core.h"

#endif  // KERNELCODE_GENERATE_INCLUDE_NPU_DEMO_COST_CORE_H_
