/*
功能说明:
- 定义 include/api/cost/Core.h 的统一公共成本类型声明。
- 当前只公开 `npu_demo::cost::CostKind::{Compute, Memory}`，并沿用 `S_INT` 作为全部 cost helper 返回类型来源。

使用示例:
- #include "include/api/cost/Core.h"
- npu_demo::cost::CostKind kind = npu_demo::cost::CostKind::Compute;
- S_INT cost = 0;

创建者: 金铲铲大作战
最后修改人: 金铲铲大作战

关联文件:
- spec: spec/include/api/cost/Core.md
- test: test/include/api/test_cost.py
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

使用示例:
- cost::CostKind compute_kind = cost::CostKind::Compute;
- cost::CostKind memory_kind = cost::CostKind::Memory;

创建者: 金铲铲大作战
最后修改人: 金铲铲大作战

关联文件:
- spec: spec/include/api/cost/Core.md
- test: test/include/api/test_cost.py
- 功能实现: include/npu_demo/cost/Core.h
*/
enum class CostKind {
    Compute,
    Memory,
};

}  // namespace cost
}  // namespace npu_demo

#endif  // KERNELCODE_GENERATE_INCLUDE_API_COST_CORE_H_
