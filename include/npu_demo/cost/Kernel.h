/*
功能说明:
- 提供 include/api/cost/Kernel.h 的 npu_demo 默认实现。
- 按公开 cost kind 合同实现 Kernel family 的节点级成本。
- `MAC` 命中 matmul，`VECTOR1` 命中当前非 matmul kernel op，`DMA3` 命中 img2col1d/2d；其他组合返回 `0`。

API 列表:
- `npu_demo::cost::add/sub/mul/truediv<Space, InType, OutType, Kind>(const Memory<Space, OutType>& out, const Memory<Space, InType>& lhs, const Memory<Space, InType>& rhs) -> S_INT`
- `npu_demo::cost::eq/ne/lt/le/gt/ge<Space, InType, OutType, Kind>(const Memory<Space, OutType>& out, const Memory<Space, InType>& lhs, const Memory<Space, InType>& rhs) -> S_INT`
- `npu_demo::cost::exp<Space, InType, OutType, Kind>(const Memory<Space, OutType>& out, const Memory<Space, InType>& input) -> S_INT`
- `npu_demo::cost::select<Space, InType, OutType, Kind>(const Memory<Space, OutType>& out, const Memory<Space, bool>& cond, const Memory<Space, InType>& lhs, const Memory<Space, InType>& rhs) -> S_INT`
- `npu_demo::cost::reduce_sum/reduce_min/reduce_max<Space, InType, OutType, Kind>(const Memory<Space, OutType>& out, const Memory<Space, InType>& input, long long axis) -> S_INT`
- `npu_demo::cost::matmul<LhsSpace, RhsSpace, OutSpace, LhsType, RhsType, OutType, Kind>(const Memory<OutSpace, OutType>& out, const Memory<LhsSpace, LhsType>& lhs, const Memory<RhsSpace, RhsType>& rhs) -> S_INT`
- `npu_demo::cost::img2col1d<InputSpace, OutputSpace, InType, OutType, Kind>(const Memory<OutputSpace, OutType>& out, const Memory<InputSpace, InType>& input, long long k, long long s, long long d, long long p_left, long long p_right) -> S_INT`
- `npu_demo::cost::img2col2d<InputSpace, OutputSpace, InType, OutType, Kind>(const Memory<OutputSpace, OutType>& out, const Memory<InputSpace, InType>& input, long long kh, long long kw, long long sh, long long sw, long long dh, long long dw, long long ph, long long pw, long long pl, long long pr) -> S_INT`

使用示例:
- #include "include/npu_demo/cost/Kernel.h"
- S_INT add_cost = npu_demo::cost::add<GM, float, float, npu_demo::VECTOR1>(out, lhs, rhs);


关联文件:
- spec: spec/include/api/cost/Kernel.md
- test: test/include/npu_demo/cost.py
- 功能实现: include/npu_demo/cost/Kernel.h
*/

#ifndef KERNELCODE_GENERATE_INCLUDE_NPU_DEMO_COST_KERNEL_H_
#define KERNELCODE_GENERATE_INCLUDE_NPU_DEMO_COST_KERNEL_H_

#include "include/api/cost/Kernel.h"
#include "include/npu_demo/Core.h"
#include "include/npu_demo/Memory.h"

namespace npu_demo {
namespace cost {

namespace detail {

inline S_INT kernel_ceil_div_non_negative(S_INT value, S_INT divisor) {
    if (value <= 0) {
        return 0;
    }
    return (value + divisor - 1) / divisor;
}

template <typename T>
inline S_INT kernel_bytes_for_elements(S_INT elements) {
    return elements * static_cast<S_INT>(sizeof(T));
}

template <typename T>
inline S_INT kernel_dma_latency_for_elements(S_INT elements) {
    return kernel_ceil_div_non_negative(kernel_bytes_for_elements<T>(elements), 64);
}

template <CostKind Kind>
inline S_INT vector1_cost_for_elements(S_INT elements) {
    if constexpr (Kind == CostKind::VECTOR1) {
        return kernel_ceil_div_non_negative(elements, 64);
    }
    return 0;
}

template <typename OutType, CostKind Kind>
inline S_INT dma3_cost_for_elements(S_INT elements) {
    if constexpr (Kind == CostKind::DMA3) {
        return kernel_dma_latency_for_elements<OutType>(elements);
    }
    return 0;
}

}  // namespace detail

/*
功能说明:
- 提供逐元素二元算术成本 helper 的 npu_demo 默认实现。
- `VECTOR1` 返回 `ceil(out.element_count() / 64)`，其他 kind 返回 `0`。

使用示例:
- S_INT add_cost = npu_demo::cost::add<GM, float, float, npu_demo::VECTOR1>(out, lhs, rhs);


关联文件:
- spec: spec/include/api/cost/Kernel.md
- test: test/include/npu_demo/cost.py
- 功能实现: include/npu_demo/cost/Kernel.h
*/
template <MemorySpace Space, typename InType, typename OutType, CostKind Kind>
inline S_INT add(
    const Memory<Space, OutType>& out,
    const Memory<Space, InType>& lhs,
    const Memory<Space, InType>& rhs) {
    (void)lhs;
    (void)rhs;
    return detail::vector1_cost_for_elements<Kind>(out.element_count());
}
template <MemorySpace Space, typename InType, typename OutType, CostKind Kind>
inline S_INT sub(
    const Memory<Space, OutType>& out,
    const Memory<Space, InType>& lhs,
    const Memory<Space, InType>& rhs) {
    (void)lhs;
    (void)rhs;
    return detail::vector1_cost_for_elements<Kind>(out.element_count());
}
template <MemorySpace Space, typename InType, typename OutType, CostKind Kind>
inline S_INT mul(
    const Memory<Space, OutType>& out,
    const Memory<Space, InType>& lhs,
    const Memory<Space, InType>& rhs) {
    (void)lhs;
    (void)rhs;
    return detail::vector1_cost_for_elements<Kind>(out.element_count());
}
template <MemorySpace Space, typename InType, typename OutType, CostKind Kind>
inline S_INT truediv(
    const Memory<Space, OutType>& out,
    const Memory<Space, InType>& lhs,
    const Memory<Space, InType>& rhs) {
    (void)lhs;
    (void)rhs;
    return detail::vector1_cost_for_elements<Kind>(out.element_count());
}

/*
功能说明:
- 提供逐元素比较成本 helper 的 npu_demo 默认实现。
- `VECTOR1` 返回 `ceil(out.element_count() / 64)`，其他 kind 返回 `0`。

使用示例:
- S_INT eq_cost = npu_demo::cost::eq<GM, float, bool, npu_demo::VECTOR1>(out, lhs, rhs);


关联文件:
- spec: spec/include/api/cost/Kernel.md
- test: test/include/npu_demo/cost.py
- 功能实现: include/npu_demo/cost/Kernel.h
*/
template <MemorySpace Space, typename InType, typename OutType, CostKind Kind>
inline S_INT eq(
    const Memory<Space, OutType>& out,
    const Memory<Space, InType>& lhs,
    const Memory<Space, InType>& rhs) {
    (void)lhs;
    (void)rhs;
    return detail::vector1_cost_for_elements<Kind>(out.element_count());
}
template <MemorySpace Space, typename InType, typename OutType, CostKind Kind>
inline S_INT ne(
    const Memory<Space, OutType>& out,
    const Memory<Space, InType>& lhs,
    const Memory<Space, InType>& rhs) {
    (void)lhs;
    (void)rhs;
    return detail::vector1_cost_for_elements<Kind>(out.element_count());
}
template <MemorySpace Space, typename InType, typename OutType, CostKind Kind>
inline S_INT lt(
    const Memory<Space, OutType>& out,
    const Memory<Space, InType>& lhs,
    const Memory<Space, InType>& rhs) {
    (void)lhs;
    (void)rhs;
    return detail::vector1_cost_for_elements<Kind>(out.element_count());
}
template <MemorySpace Space, typename InType, typename OutType, CostKind Kind>
inline S_INT le(
    const Memory<Space, OutType>& out,
    const Memory<Space, InType>& lhs,
    const Memory<Space, InType>& rhs) {
    (void)lhs;
    (void)rhs;
    return detail::vector1_cost_for_elements<Kind>(out.element_count());
}
template <MemorySpace Space, typename InType, typename OutType, CostKind Kind>
inline S_INT gt(
    const Memory<Space, OutType>& out,
    const Memory<Space, InType>& lhs,
    const Memory<Space, InType>& rhs) {
    (void)lhs;
    (void)rhs;
    return detail::vector1_cost_for_elements<Kind>(out.element_count());
}
template <MemorySpace Space, typename InType, typename OutType, CostKind Kind>
inline S_INT ge(
    const Memory<Space, OutType>& out,
    const Memory<Space, InType>& lhs,
    const Memory<Space, InType>& rhs) {
    (void)lhs;
    (void)rhs;
    return detail::vector1_cost_for_elements<Kind>(out.element_count());
}

/*
功能说明:
- 提供一元、select 与 reduce 成本 helper 的 npu_demo 默认实现。
- `VECTOR1` 返回 `ceil(out.element_count() / 64)`，其他 kind 返回 `0`。

使用示例:
- S_INT exp_cost = npu_demo::cost::exp<GM, float, float, npu_demo::VECTOR1>(out, input);
- S_INT max_cost = npu_demo::cost::reduce_max<GM, float, float, npu_demo::VECTOR1>(out, input, 1);


关联文件:
- spec: spec/include/api/cost/Kernel.md
- test: test/include/npu_demo/cost.py
- 功能实现: include/npu_demo/cost/Kernel.h
*/
template <MemorySpace Space, typename InType, typename OutType, CostKind Kind>
inline S_INT exp(const Memory<Space, OutType>& out, const Memory<Space, InType>& input) {
    (void)input;
    return detail::vector1_cost_for_elements<Kind>(out.element_count());
}
template <MemorySpace Space, typename InType, typename OutType, CostKind Kind>
inline S_INT select(
    const Memory<Space, OutType>& out,
    const Memory<Space, bool>& cond,
    const Memory<Space, InType>& lhs,
    const Memory<Space, InType>& rhs) {
    (void)cond;
    (void)lhs;
    (void)rhs;
    return detail::vector1_cost_for_elements<Kind>(out.element_count());
}
template <MemorySpace Space, typename InType, typename OutType, CostKind Kind>
inline S_INT reduce_sum(const Memory<Space, OutType>& out, const Memory<Space, InType>& input, long long axis) {
    (void)input;
    (void)axis;
    return detail::vector1_cost_for_elements<Kind>(out.element_count());
}
template <MemorySpace Space, typename InType, typename OutType, CostKind Kind>
inline S_INT reduce_min(const Memory<Space, OutType>& out, const Memory<Space, InType>& input, long long axis) {
    (void)input;
    (void)axis;
    return detail::vector1_cost_for_elements<Kind>(out.element_count());
}
template <MemorySpace Space, typename InType, typename OutType, CostKind Kind>
inline S_INT reduce_max(const Memory<Space, OutType>& out, const Memory<Space, InType>& input, long long axis) {
    (void)input;
    (void)axis;
    return detail::vector1_cost_for_elements<Kind>(out.element_count());
}

/*
功能说明:
- 提供 matmul 与 img2col family 成本 helper 的 npu_demo 默认实现。
- `MAC` 返回 `ceil((2 * M * N * K) / (16 * 16 * 16 * 2))`。
- `DMA3` 对 img2col1d/2d 返回 `ceil(out.element_count() * sizeof(OutType) / 64)`。
- 其他组合返回 `0`。

使用示例:
- S_INT matmul_cost = npu_demo::cost::matmul<TSM, TSM, TLM1, float, float, float, npu_demo::MAC>(out, lhs, rhs);


关联文件:
- spec: spec/include/api/cost/Kernel.md
- test: test/include/npu_demo/cost.py
- 功能实现: include/npu_demo/cost/Kernel.h
*/
template <
    MemorySpace LhsSpace,
    MemorySpace RhsSpace,
    MemorySpace OutSpace,
    typename LhsType,
    typename RhsType,
    typename OutType,
    CostKind Kind>
inline S_INT matmul(
    const Memory<OutSpace, OutType>& out,
    const Memory<LhsSpace, LhsType>& lhs,
    const Memory<RhsSpace, RhsType>& rhs) {
    (void)rhs;
    if constexpr (Kind == CostKind::MAC) {
        if (out.rank() < 2 || lhs.rank() < 2) {
            return 0;
        }
        const S_INT m = out.get_shape(0);
        const S_INT n = out.get_shape(out.rank() - 1);
        const S_INT k = lhs.get_shape(lhs.rank() - 1);
        return detail::kernel_ceil_div_non_negative(2 * m * n * k, 16 * 16 * 16 * 2);
    }
    return 0;
}
template <MemorySpace InputSpace, MemorySpace OutputSpace, typename InType, typename OutType, CostKind Kind>
inline S_INT img2col1d(
    const Memory<OutputSpace, OutType>& out,
    const Memory<InputSpace, InType>& input,
    long long k,
    long long s,
    long long d,
    long long p_left,
    long long p_right) {
    (void)input;
    (void)k;
    (void)s;
    (void)d;
    (void)p_left;
    (void)p_right;
    return detail::dma3_cost_for_elements<OutType, Kind>(out.element_count());
}
template <MemorySpace InputSpace, MemorySpace OutputSpace, typename InType, typename OutType, CostKind Kind>
inline S_INT img2col2d(
    const Memory<OutputSpace, OutType>& out,
    const Memory<InputSpace, InType>& input,
    long long kh,
    long long kw,
    long long sh,
    long long sw,
    long long dh,
    long long dw,
    long long ph,
    long long pw,
    long long pl,
    long long pr) {
    (void)input;
    (void)kh;
    (void)kw;
    (void)sh;
    (void)sw;
    (void)dh;
    (void)dw;
    (void)ph;
    (void)pw;
    (void)pl;
    (void)pr;
    return detail::dma3_cost_for_elements<OutType, Kind>(out.element_count());
}

}  // namespace cost
}  // namespace npu_demo

#endif  // KERNELCODE_GENERATE_INCLUDE_NPU_DEMO_COST_KERNEL_H_
