/*
功能说明:
- 提供 include/api/cost/Kernel.h 的 npu_demo 默认实现。
- 当前所有 Kernel cost helper 统一返回 `0`，只承接可编译、可实例化的成本接口合同。

使用示例:
- #include "include/npu_demo/cost/Kernel.h"
- S_INT add_cost = npu_demo::cost::add<GM, float, float, npu_demo::cost::CostKind::Compute>(out, lhs, rhs);

创建者: 金铲铲大作战
最后修改人: 金铲铲大作战

关联文件:
- spec: spec/include/api/cost/Kernel.md
- test: test/include/npu_demo/test_cost.py
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

template <typename... Args>
inline S_INT zero_cost(Args&&...) {
    return 0;
}

}  // namespace detail

/*
功能说明:
- 提供逐元素二元算术成本 helper 的 npu_demo 默认实现，统一返回 `0`。

使用示例:
- S_INT add_cost = npu_demo::cost::add<GM, float, float, npu_demo::cost::CostKind::Compute>(out, lhs, rhs);

创建者: 金铲铲大作战
最后修改人: 金铲铲大作战

关联文件:
- spec: spec/include/api/cost/Kernel.md
- test: test/include/npu_demo/test_cost.py
- 功能实现: include/npu_demo/cost/Kernel.h
*/
template <MemorySpace Space, typename InType, typename OutType, CostKind Kind>
inline S_INT add(
    const Memory<Space, OutType>& out,
    const Memory<Space, InType>& lhs,
    const Memory<Space, InType>& rhs) {
    return detail::zero_cost(out, lhs, rhs, Kind);
}
template <MemorySpace Space, typename InType, typename OutType, CostKind Kind>
inline S_INT sub(
    const Memory<Space, OutType>& out,
    const Memory<Space, InType>& lhs,
    const Memory<Space, InType>& rhs) {
    return detail::zero_cost(out, lhs, rhs, Kind);
}
template <MemorySpace Space, typename InType, typename OutType, CostKind Kind>
inline S_INT mul(
    const Memory<Space, OutType>& out,
    const Memory<Space, InType>& lhs,
    const Memory<Space, InType>& rhs) {
    return detail::zero_cost(out, lhs, rhs, Kind);
}
template <MemorySpace Space, typename InType, typename OutType, CostKind Kind>
inline S_INT truediv(
    const Memory<Space, OutType>& out,
    const Memory<Space, InType>& lhs,
    const Memory<Space, InType>& rhs) {
    return detail::zero_cost(out, lhs, rhs, Kind);
}

/*
功能说明:
- 提供逐元素比较成本 helper 的 npu_demo 默认实现，统一返回 `0`。

使用示例:
- S_INT eq_cost = npu_demo::cost::eq<GM, float, bool, npu_demo::cost::CostKind::Compute>(out, lhs, rhs);

创建者: 金铲铲大作战
最后修改人: 金铲铲大作战

关联文件:
- spec: spec/include/api/cost/Kernel.md
- test: test/include/npu_demo/test_cost.py
- 功能实现: include/npu_demo/cost/Kernel.h
*/
template <MemorySpace Space, typename InType, typename OutType, CostKind Kind>
inline S_INT eq(
    const Memory<Space, OutType>& out,
    const Memory<Space, InType>& lhs,
    const Memory<Space, InType>& rhs) {
    return detail::zero_cost(out, lhs, rhs, Kind);
}
template <MemorySpace Space, typename InType, typename OutType, CostKind Kind>
inline S_INT ne(
    const Memory<Space, OutType>& out,
    const Memory<Space, InType>& lhs,
    const Memory<Space, InType>& rhs) {
    return detail::zero_cost(out, lhs, rhs, Kind);
}
template <MemorySpace Space, typename InType, typename OutType, CostKind Kind>
inline S_INT lt(
    const Memory<Space, OutType>& out,
    const Memory<Space, InType>& lhs,
    const Memory<Space, InType>& rhs) {
    return detail::zero_cost(out, lhs, rhs, Kind);
}
template <MemorySpace Space, typename InType, typename OutType, CostKind Kind>
inline S_INT le(
    const Memory<Space, OutType>& out,
    const Memory<Space, InType>& lhs,
    const Memory<Space, InType>& rhs) {
    return detail::zero_cost(out, lhs, rhs, Kind);
}
template <MemorySpace Space, typename InType, typename OutType, CostKind Kind>
inline S_INT gt(
    const Memory<Space, OutType>& out,
    const Memory<Space, InType>& lhs,
    const Memory<Space, InType>& rhs) {
    return detail::zero_cost(out, lhs, rhs, Kind);
}
template <MemorySpace Space, typename InType, typename OutType, CostKind Kind>
inline S_INT ge(
    const Memory<Space, OutType>& out,
    const Memory<Space, InType>& lhs,
    const Memory<Space, InType>& rhs) {
    return detail::zero_cost(out, lhs, rhs, Kind);
}

/*
功能说明:
- 提供一元、select 与 reduce 成本 helper 的 npu_demo 默认实现，统一返回 `0`。

使用示例:
- S_INT exp_cost = npu_demo::cost::exp<GM, float, float, npu_demo::cost::CostKind::Compute>(out, input);

创建者: 金铲铲大作战
最后修改人: 金铲铲大作战

关联文件:
- spec: spec/include/api/cost/Kernel.md
- test: test/include/npu_demo/test_cost.py
- 功能实现: include/npu_demo/cost/Kernel.h
*/
template <MemorySpace Space, typename InType, typename OutType, CostKind Kind>
inline S_INT exp(const Memory<Space, OutType>& out, const Memory<Space, InType>& input) {
    return detail::zero_cost(out, input, Kind);
}
template <MemorySpace Space, typename InType, typename OutType, CostKind Kind>
inline S_INT select(
    const Memory<Space, OutType>& out,
    const Memory<Space, bool>& cond,
    const Memory<Space, InType>& lhs,
    const Memory<Space, InType>& rhs) {
    return detail::zero_cost(out, cond, lhs, rhs, Kind);
}
template <MemorySpace Space, typename InType, typename OutType, CostKind Kind>
inline S_INT reduce_sum(const Memory<Space, OutType>& out, const Memory<Space, InType>& input, long long axis) {
    return detail::zero_cost(out, input, axis, Kind);
}
template <MemorySpace Space, typename InType, typename OutType, CostKind Kind>
inline S_INT reduce_min(const Memory<Space, OutType>& out, const Memory<Space, InType>& input, long long axis) {
    return detail::zero_cost(out, input, axis, Kind);
}

/*
功能说明:
- 提供 matmul 与 img2col family 成本 helper 的 npu_demo 默认实现，统一返回 `0`。

使用示例:
- S_INT matmul_cost = npu_demo::cost::matmul<TSM, TSM, TLM1, float, float, float, npu_demo::cost::CostKind::Memory>(out, lhs, rhs);

创建者: 金铲铲大作战
最后修改人: 金铲铲大作战

关联文件:
- spec: spec/include/api/cost/Kernel.md
- test: test/include/npu_demo/test_cost.py
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
    return detail::zero_cost(out, lhs, rhs, Kind);
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
    return detail::zero_cost(out, input, k, s, d, p_left, p_right, Kind);
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
    return detail::zero_cost(out, input, kh, kw, sh, sw, dh, dw, ph, pw, pl, pr, Kind);
}

}  // namespace cost
}  // namespace npu_demo

#endif  // KERNELCODE_GENERATE_INCLUDE_NPU_DEMO_COST_KERNEL_H_
