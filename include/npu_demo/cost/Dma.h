/*
功能说明:
- 提供 include/api/cost/Dma.h 的 npu_demo 默认实现。
- 当前 `copy/slice/deslice` 成本 helper 统一返回 `0`，只承接可编译、可实例化的成本接口合同。

使用示例:
- #include "include/npu_demo/cost/Dma.h"
- S_INT copy_cost = npu_demo::cost::copy<TSM, GM, float, npu_demo::memory>(target, source);

创建者: 金铲铲大作战
最后修改人: 金铲铲大作战

关联文件:
- spec: spec/include/api/cost/Dma.md
- test: test/include/npu_demo/test_cost.py
- 功能实现: include/npu_demo/cost/Dma.h
*/

#ifndef KERNELCODE_GENERATE_INCLUDE_NPU_DEMO_COST_DMA_H_
#define KERNELCODE_GENERATE_INCLUDE_NPU_DEMO_COST_DMA_H_

#include "include/api/cost/Dma.h"
#include "include/npu_demo/Core.h"
#include "include/npu_demo/Memory.h"

namespace npu_demo {
namespace cost {

namespace detail {

template <typename... Args>
inline S_INT zero_dma_cost(Args&&...) {
    return 0;
}

}  // namespace detail

/*
功能说明:
- 提供 `dma.copy` 成本 helper 的 npu_demo 默认实现，统一返回 `0`。

使用示例:
- S_INT copy_cost = npu_demo::cost::copy<TSM, GM, float, npu_demo::memory>(target, source);

创建者: 金铲铲大作战
最后修改人: 金铲铲大作战

关联文件:
- spec: spec/include/api/cost/Dma.md
- test: test/include/npu_demo/test_cost.py
- 功能实现: include/npu_demo/cost/Dma.h
*/
template <MemorySpace TargetSpace, MemorySpace SourceSpace, typename T, CostKind Kind>
inline S_INT copy(const Memory<TargetSpace, T>& target, const Memory<SourceSpace, T>& source) {
    return detail::zero_dma_cost(target, source, Kind);
}

/*
功能说明:
- 提供 `slice/deslice` 成本 helper 的 npu_demo 默认实现，统一返回 `0`。

使用示例:
- S_INT slice_cost = npu_demo::cost::slice<TSM, GM, float, npu_demo::memory>(target, source, offset, size, stride);

创建者: 金铲铲大作战
最后修改人: 金铲铲大作战

关联文件:
- spec: spec/include/api/cost/Dma.md
- test: test/include/npu_demo/test_cost.py
- 功能实现: include/npu_demo/cost/Dma.h
*/
template <MemorySpace TargetSpace, MemorySpace SourceSpace, typename T, CostKind Kind>
inline S_INT slice(
    const Memory<TargetSpace, T>& target,
    const Memory<SourceSpace, T>& source,
    const Vector& offset,
    const Vector& size,
    const Vector& stride) {
    return detail::zero_dma_cost(target, source, offset, size, stride, Kind);
}
template <MemorySpace TargetSpace, MemorySpace SourceSpace, typename T, CostKind Kind>
inline S_INT deslice(
    const Memory<TargetSpace, T>& target,
    const Memory<SourceSpace, T>& source,
    const Vector& offset,
    const Vector& size,
    const Vector& stride) {
    return detail::zero_dma_cost(target, source, offset, size, stride, Kind);
}

}  // namespace cost
}  // namespace npu_demo

#endif  // KERNELCODE_GENERATE_INCLUDE_NPU_DEMO_COST_DMA_H_
