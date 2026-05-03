/*
功能说明:
- 提供 include/api/cost/Dma.h 的 npu_demo 默认实现。
- 按公开 cost kind 合同实现 `dma.copy/slice/deslice` 的有效字节成本。
- `DMA1` 命中 GM -> TSM/TLM，`DMA2` 命中 TSM/TLM -> GM，`DMA3` 命中 TSM -> TLM，`DMA4` 命中 TSM -> TSM。
- 未命中 kind / space 组合返回 `0`。

API 列表:
- `npu_demo::cost::copy<TargetSpace, SourceSpace, T, Kind>(const Memory<TargetSpace, T>& target, const Memory<SourceSpace, T>& source) -> S_INT`
- `npu_demo::cost::slice<TargetSpace, SourceSpace, T, Kind>(const Memory<TargetSpace, T>& target, const Memory<SourceSpace, T>& source, const Vector& offset, const Vector& size, const Vector& stride) -> S_INT`
- `npu_demo::cost::deslice<TargetSpace, SourceSpace, T, Kind>(const Memory<TargetSpace, T>& target, const Memory<SourceSpace, T>& source, const Vector& offset, const Vector& size, const Vector& stride) -> S_INT`

使用示例:
- #include "include/npu_demo/cost/Dma.h"
- S_INT copy_cost = npu_demo::cost::copy<TSM, GM, float, npu_demo::DMA1>(target, source);


关联文件:
- spec: spec/include/api/cost/Dma.md
- test: test/include/npu_demo/cost.py
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

inline S_INT ceil_div_non_negative(S_INT value, S_INT divisor) {
    if (value <= 0) {
        return 0;
    }
    return (value + divisor - 1) / divisor;
}

template <typename T>
inline S_INT bytes_for_elements(S_INT elements) {
    return elements * static_cast<S_INT>(sizeof(T));
}

template <typename T>
inline S_INT dma_latency_for_elements(S_INT elements) {
    return ceil_div_non_negative(bytes_for_elements<T>(elements), 64);
}

inline S_INT vector_element_count(const Vector& size) {
    S_INT count = 1;
    for (unsigned long long i = 0; i < size.size(); ++i) {
        count *= size[i];
    }
    return count;
}

template <MemorySpace Space>
inline constexpr bool is_gm_space() {
    return Space == GM;
}

template <MemorySpace Space>
inline constexpr bool is_tsm_space() {
    return Space == TSM;
}

template <MemorySpace Space>
inline constexpr bool is_tlm_space() {
    return Space == TLM1 || Space == TLM2 || Space == TLM3;
}

template <MemorySpace Space>
inline constexpr bool is_tsm_or_tlm_space() {
    return is_tsm_space<Space>() || is_tlm_space<Space>();
}

template <MemorySpace TargetSpace, MemorySpace SourceSpace, CostKind Kind>
inline constexpr bool matches_dma_kind() {
    if constexpr (Kind == CostKind::DMA1) {
        return is_gm_space<SourceSpace>() && is_tsm_or_tlm_space<TargetSpace>();
    }
    if constexpr (Kind == CostKind::DMA2) {
        return is_tsm_or_tlm_space<SourceSpace>() && is_gm_space<TargetSpace>();
    }
    if constexpr (Kind == CostKind::DMA3) {
        return is_tsm_space<SourceSpace>() && is_tlm_space<TargetSpace>();
    }
    if constexpr (Kind == CostKind::DMA4) {
        return is_tsm_space<SourceSpace>() && is_tsm_space<TargetSpace>();
    }
    return false;
}

}  // namespace detail

/*
功能说明:
- 提供 `dma.copy` 成本 helper 的 npu_demo 默认实现。
- 命中公开 DMA kind/space 组合时返回 `ceil(target.element_count() * sizeof(T) / 64)`，否则返回 `0`。

使用示例:
- S_INT copy_cost = npu_demo::cost::copy<TSM, GM, float, npu_demo::DMA1>(target, source);


关联文件:
- spec: spec/include/api/cost/Dma.md
- test: test/include/npu_demo/cost.py
- 功能实现: include/npu_demo/cost/Dma.h
*/
template <MemorySpace TargetSpace, MemorySpace SourceSpace, typename T, CostKind Kind>
inline S_INT copy(const Memory<TargetSpace, T>& target, const Memory<SourceSpace, T>& source) {
    (void)source;
    if constexpr (detail::matches_dma_kind<TargetSpace, SourceSpace, Kind>()) {
        return detail::dma_latency_for_elements<T>(target.element_count());
    }
    return 0;
}

/*
功能说明:
- 提供 `slice/deslice` 成本 helper 的 npu_demo 默认实现。
- 命中公开 DMA kind/space 组合时按 `size` 向量乘积计算有效元素数，再返回 `ceil(elements * sizeof(T) / 64)`。

使用示例:
- S_INT slice_cost = npu_demo::cost::slice<TSM, GM, float, npu_demo::DMA1>(target, source, offset, size, stride);


关联文件:
- spec: spec/include/api/cost/Dma.md
- test: test/include/npu_demo/cost.py
- 功能实现: include/npu_demo/cost/Dma.h
*/
template <MemorySpace TargetSpace, MemorySpace SourceSpace, typename T, CostKind Kind>
inline S_INT slice(
    const Memory<TargetSpace, T>& target,
    const Memory<SourceSpace, T>& source,
    const Vector& offset,
    const Vector& size,
    const Vector& stride) {
    (void)target;
    (void)source;
    (void)offset;
    (void)stride;
    if constexpr (detail::matches_dma_kind<TargetSpace, SourceSpace, Kind>()) {
        return detail::dma_latency_for_elements<T>(detail::vector_element_count(size));
    }
    return 0;
}
template <MemorySpace TargetSpace, MemorySpace SourceSpace, typename T, CostKind Kind>
inline S_INT deslice(
    const Memory<TargetSpace, T>& target,
    const Memory<SourceSpace, T>& source,
    const Vector& offset,
    const Vector& size,
    const Vector& stride) {
    (void)target;
    (void)source;
    (void)offset;
    (void)stride;
    if constexpr (detail::matches_dma_kind<TargetSpace, SourceSpace, Kind>()) {
        return detail::dma_latency_for_elements<T>(detail::vector_element_count(size));
    }
    return 0;
}

}  // namespace cost
}  // namespace npu_demo

#endif  // KERNELCODE_GENERATE_INCLUDE_NPU_DEMO_COST_DMA_H_
