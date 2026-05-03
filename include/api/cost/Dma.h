/*
功能说明:
- 定义 include/api/cost/Dma.h 的统一公共 DMA 成本 helper 声明。
- 当前成功路径覆盖 `dma.copy -> npu_demo::cost::copy` 与
  `dma.slice/dma.deslice -> npu_demo::cost::slice/deslice`。

API 列表:
- `template <MemorySpace TargetSpace, MemorySpace SourceSpace, typename T, CostKind Kind> S_INT npu_demo::cost::copy(const Memory<TargetSpace, T>& target, const Memory<SourceSpace, T>& source)`
- `template <MemorySpace TargetSpace, MemorySpace SourceSpace, typename T, CostKind Kind> S_INT npu_demo::cost::slice(const Memory<TargetSpace, T>& target, const Memory<SourceSpace, T>& source, const Vector& offset, const Vector& size, const Vector& stride)`
- `template <MemorySpace TargetSpace, MemorySpace SourceSpace, typename T, CostKind Kind> S_INT npu_demo::cost::deslice(const Memory<TargetSpace, T>& target, const Memory<SourceSpace, T>& source, const Vector& offset, const Vector& size, const Vector& stride)`

helper 清单:
- 无；当前文件只声明公开 DMA 成本 helper。

使用示例:
- #include "include/api/cost/Dma.h"
- S_INT copy_cost = npu_demo::cost::copy<TSM, GM, float, npu_demo::DMA>(target, source);


关联文件:
- spec: spec/include/api/cost/Dma.md
- test: test/include/api/cost.py
- 功能实现: include/npu_demo/cost/Dma.h
*/

#ifndef KERNELCODE_GENERATE_INCLUDE_API_COST_DMA_H_
#define KERNELCODE_GENERATE_INCLUDE_API_COST_DMA_H_

#include "include/api/Memory.h"
#include "include/api/cost/Core.h"

namespace npu_demo {
namespace cost {

/*
功能说明:
- 声明 `dma.copy` 对应的公共成本 helper。

使用示例:
- S_INT copy_cost = npu_demo::cost::copy<TSM, GM, float, npu_demo::DMA>(target, source);


关联文件:
- spec: spec/include/api/cost/Dma.md
- test: test/include/api/cost.py
- 功能实现: include/npu_demo/cost/Dma.h
*/
template <MemorySpace TargetSpace, MemorySpace SourceSpace, typename T, CostKind Kind>
S_INT copy(const Memory<TargetSpace, T>& target, const Memory<SourceSpace, T>& source);

/*
功能说明:
- 声明 `slice/deslice` 成本 helper，参数顺序与 include/api/Dma.h 保持一致。

使用示例:
- S_INT slice_cost = npu_demo::cost::slice<TSM, GM, float, npu_demo::DMA>(target, source, offset, size, stride);
- S_INT deslice_cost = npu_demo::cost::deslice<GM, TSM, float, npu_demo::DMA>(target, source, offset, size, stride);


关联文件:
- spec: spec/include/api/cost/Dma.md
- test: test/include/api/cost.py
- 功能实现: include/npu_demo/cost/Dma.h
*/
template <MemorySpace TargetSpace, MemorySpace SourceSpace, typename T, CostKind Kind>
S_INT slice(
    const Memory<TargetSpace, T>& target,
    const Memory<SourceSpace, T>& source,
    const Vector& offset,
    const Vector& size,
    const Vector& stride);
template <MemorySpace TargetSpace, MemorySpace SourceSpace, typename T, CostKind Kind>
S_INT deslice(
    const Memory<TargetSpace, T>& target,
    const Memory<SourceSpace, T>& source,
    const Vector& offset,
    const Vector& size,
    const Vector& stride);

}  // namespace cost
}  // namespace npu_demo

#endif  // KERNELCODE_GENERATE_INCLUDE_API_COST_DMA_H_
