/*
功能说明:
- 定义 include/api/cost/Kernel.h 的统一公共成本 helper 声明。
- 当前 helper 集合与 include/api/Kernel.h 保持一致，并在模板参数末尾追加 `npu_demo::cost::CostKind Kind`。

API 列表:
- `template <MemorySpace Space, typename InType, typename OutType, CostKind Kind> S_INT npu_demo::cost::add(const Memory<Space, OutType>& out, const Memory<Space, InType>& lhs, const Memory<Space, InType>& rhs)`
- `template <MemorySpace Space, typename InType, typename OutType, CostKind Kind> S_INT npu_demo::cost::sub(const Memory<Space, OutType>& out, const Memory<Space, InType>& lhs, const Memory<Space, InType>& rhs)`
- `template <MemorySpace Space, typename InType, typename OutType, CostKind Kind> S_INT npu_demo::cost::mul(const Memory<Space, OutType>& out, const Memory<Space, InType>& lhs, const Memory<Space, InType>& rhs)`
- `template <MemorySpace Space, typename InType, typename OutType, CostKind Kind> S_INT npu_demo::cost::truediv(const Memory<Space, OutType>& out, const Memory<Space, InType>& lhs, const Memory<Space, InType>& rhs)`
- `template <MemorySpace Space, typename InType, typename OutType, CostKind Kind> S_INT npu_demo::cost::eq(const Memory<Space, OutType>& out, const Memory<Space, InType>& lhs, const Memory<Space, InType>& rhs)`
- `template <MemorySpace Space, typename InType, typename OutType, CostKind Kind> S_INT npu_demo::cost::ne(const Memory<Space, OutType>& out, const Memory<Space, InType>& lhs, const Memory<Space, InType>& rhs)`
- `template <MemorySpace Space, typename InType, typename OutType, CostKind Kind> S_INT npu_demo::cost::lt(const Memory<Space, OutType>& out, const Memory<Space, InType>& lhs, const Memory<Space, InType>& rhs)`
- `template <MemorySpace Space, typename InType, typename OutType, CostKind Kind> S_INT npu_demo::cost::le(const Memory<Space, OutType>& out, const Memory<Space, InType>& lhs, const Memory<Space, InType>& rhs)`
- `template <MemorySpace Space, typename InType, typename OutType, CostKind Kind> S_INT npu_demo::cost::gt(const Memory<Space, OutType>& out, const Memory<Space, InType>& lhs, const Memory<Space, InType>& rhs)`
- `template <MemorySpace Space, typename InType, typename OutType, CostKind Kind> S_INT npu_demo::cost::ge(const Memory<Space, OutType>& out, const Memory<Space, InType>& lhs, const Memory<Space, InType>& rhs)`
- `template <MemorySpace Space, typename InType, typename OutType, CostKind Kind> S_INT npu_demo::cost::exp(const Memory<Space, OutType>& out, const Memory<Space, InType>& input)`
- `template <MemorySpace Space, typename InType, typename OutType, CostKind Kind> S_INT npu_demo::cost::select(const Memory<Space, OutType>& out, const Memory<Space, bool>& cond, const Memory<Space, InType>& lhs, const Memory<Space, InType>& rhs)`
- `template <MemorySpace Space, typename InType, typename OutType, CostKind Kind> S_INT npu_demo::cost::reduce_sum(const Memory<Space, OutType>& out, const Memory<Space, InType>& input, long long axis)`
- `template <MemorySpace Space, typename InType, typename OutType, CostKind Kind> S_INT npu_demo::cost::reduce_min(const Memory<Space, OutType>& out, const Memory<Space, InType>& input, long long axis)`
- `template <MemorySpace Space, typename InType, typename OutType, CostKind Kind> S_INT npu_demo::cost::reduce_max(const Memory<Space, OutType>& out, const Memory<Space, InType>& input, long long axis)`
- `template <MemorySpace LhsSpace, MemorySpace RhsSpace, MemorySpace OutSpace, typename LhsType, typename RhsType, typename OutType, CostKind Kind> S_INT npu_demo::cost::matmul(const Memory<OutSpace, OutType>& out, const Memory<LhsSpace, LhsType>& lhs, const Memory<RhsSpace, RhsType>& rhs)`
- `template <MemorySpace InputSpace, MemorySpace OutputSpace, typename InType, typename OutType, CostKind Kind> S_INT npu_demo::cost::img2col1d(const Memory<OutputSpace, OutType>& out, const Memory<InputSpace, InType>& input, long long k, long long s, long long d, long long p_left, long long p_right)`
- `template <MemorySpace InputSpace, MemorySpace OutputSpace, typename InType, typename OutType, CostKind Kind> S_INT npu_demo::cost::img2col2d(const Memory<OutputSpace, OutType>& out, const Memory<InputSpace, InType>& input, long long kh, long long kw, long long sh, long long sw, long long dh, long long dw, long long ph, long long pw, long long pl, long long pr)`

helper 清单:
- 无；当前文件只声明公开 Kernel 成本 helper。

使用示例:
- #include "include/api/cost/Kernel.h"
- S_INT add_cost = npu_demo::cost::add<GM, float, float, npu_demo::compute>(out, lhs, rhs);
- S_INT matmul_cost = npu_demo::cost::matmul<TSM, TSM, TLM1, float, float, float, npu_demo::memory>(out, lhs, rhs);


关联文件:
- spec: spec/include/api/cost/Kernel.md
- test: test/include/api/cost.py
- 功能实现: include/npu_demo/cost/Kernel.h
*/

#ifndef KERNELCODE_GENERATE_INCLUDE_API_COST_KERNEL_H_
#define KERNELCODE_GENERATE_INCLUDE_API_COST_KERNEL_H_

#include "include/api/Memory.h"
#include "include/api/cost/Core.h"

namespace npu_demo {
namespace cost {

/*
功能说明:
- 声明逐元素二元算术成本 helper，参数顺序固定为 `out -> lhs -> rhs`。

使用示例:
- S_INT add_cost = npu_demo::cost::add<GM, float, float, npu_demo::compute>(out, lhs, rhs);
- S_INT div_cost = npu_demo::cost::truediv<TSM, float, float, npu_demo::memory>(out, lhs, rhs);


关联文件:
- spec: spec/include/api/cost/Kernel.md
- test: test/include/api/cost.py
- 功能实现: include/npu_demo/cost/Kernel.h
*/
template <MemorySpace Space, typename InType, typename OutType, CostKind Kind>
S_INT add(
    const Memory<Space, OutType>& out,
    const Memory<Space, InType>& lhs,
    const Memory<Space, InType>& rhs);
template <MemorySpace Space, typename InType, typename OutType, CostKind Kind>
S_INT sub(
    const Memory<Space, OutType>& out,
    const Memory<Space, InType>& lhs,
    const Memory<Space, InType>& rhs);
template <MemorySpace Space, typename InType, typename OutType, CostKind Kind>
S_INT mul(
    const Memory<Space, OutType>& out,
    const Memory<Space, InType>& lhs,
    const Memory<Space, InType>& rhs);
template <MemorySpace Space, typename InType, typename OutType, CostKind Kind>
S_INT truediv(
    const Memory<Space, OutType>& out,
    const Memory<Space, InType>& lhs,
    const Memory<Space, InType>& rhs);

/*
功能说明:
- 声明逐元素比较成本 helper，参数顺序固定为 `out -> lhs -> rhs`。

使用示例:
- S_INT eq_cost = npu_demo::cost::eq<GM, float, bool, npu_demo::compute>(out, lhs, rhs);


关联文件:
- spec: spec/include/api/cost/Kernel.md
- test: test/include/api/cost.py
- 功能实现: include/npu_demo/cost/Kernel.h
*/
template <MemorySpace Space, typename InType, typename OutType, CostKind Kind>
S_INT eq(
    const Memory<Space, OutType>& out,
    const Memory<Space, InType>& lhs,
    const Memory<Space, InType>& rhs);
template <MemorySpace Space, typename InType, typename OutType, CostKind Kind>
S_INT ne(
    const Memory<Space, OutType>& out,
    const Memory<Space, InType>& lhs,
    const Memory<Space, InType>& rhs);
template <MemorySpace Space, typename InType, typename OutType, CostKind Kind>
S_INT lt(
    const Memory<Space, OutType>& out,
    const Memory<Space, InType>& lhs,
    const Memory<Space, InType>& rhs);
template <MemorySpace Space, typename InType, typename OutType, CostKind Kind>
S_INT le(
    const Memory<Space, OutType>& out,
    const Memory<Space, InType>& lhs,
    const Memory<Space, InType>& rhs);
template <MemorySpace Space, typename InType, typename OutType, CostKind Kind>
S_INT gt(
    const Memory<Space, OutType>& out,
    const Memory<Space, InType>& lhs,
    const Memory<Space, InType>& rhs);
template <MemorySpace Space, typename InType, typename OutType, CostKind Kind>
S_INT ge(
    const Memory<Space, OutType>& out,
    const Memory<Space, InType>& lhs,
    const Memory<Space, InType>& rhs);

/*
功能说明:
- 声明一元、select 与 reduce 成本 helper，参数顺序与 include/api/Kernel.h 保持一致。

使用示例:
- S_INT exp_cost = npu_demo::cost::exp<GM, float, float, npu_demo::compute>(out, input);
- S_INT reduce_cost = npu_demo::cost::reduce_sum<GM, float, float, npu_demo::memory>(out, input, 1);


关联文件:
- spec: spec/include/api/cost/Kernel.md
- test: test/include/api/cost.py
- 功能实现: include/npu_demo/cost/Kernel.h
*/
template <MemorySpace Space, typename InType, typename OutType, CostKind Kind>
S_INT exp(const Memory<Space, OutType>& out, const Memory<Space, InType>& input);
template <MemorySpace Space, typename InType, typename OutType, CostKind Kind>
S_INT select(
    const Memory<Space, OutType>& out,
    const Memory<Space, bool>& cond,
    const Memory<Space, InType>& lhs,
    const Memory<Space, InType>& rhs);
template <MemorySpace Space, typename InType, typename OutType, CostKind Kind>
S_INT reduce_sum(const Memory<Space, OutType>& out, const Memory<Space, InType>& input, long long axis);
template <MemorySpace Space, typename InType, typename OutType, CostKind Kind>
S_INT reduce_min(const Memory<Space, OutType>& out, const Memory<Space, InType>& input, long long axis);
template <MemorySpace Space, typename InType, typename OutType, CostKind Kind>
S_INT reduce_max(const Memory<Space, OutType>& out, const Memory<Space, InType>& input, long long axis);

/*
功能说明:
- 声明 matmul 与 img2col family 的成本 helper，模板顺序跟随原 Kernel helper，再在末尾追加 `Kind`。

使用示例:
- S_INT matmul_cost = npu_demo::cost::matmul<TSM, TSM, TLM1, float, float, float, npu_demo::compute>(out, lhs, rhs);


关联文件:
- spec: spec/include/api/cost/Kernel.md
- test: test/include/api/cost.py
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
S_INT matmul(
    const Memory<OutSpace, OutType>& out,
    const Memory<LhsSpace, LhsType>& lhs,
    const Memory<RhsSpace, RhsType>& rhs);
template <MemorySpace InputSpace, MemorySpace OutputSpace, typename InType, typename OutType, CostKind Kind>
S_INT img2col1d(
    const Memory<OutputSpace, OutType>& out,
    const Memory<InputSpace, InType>& input,
    long long k,
    long long s,
    long long d,
    long long p_left,
    long long p_right);
template <MemorySpace InputSpace, MemorySpace OutputSpace, typename InType, typename OutType, CostKind Kind>
S_INT img2col2d(
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
    long long pr);

}  // namespace cost
}  // namespace npu_demo

#endif  // KERNELCODE_GENERATE_INCLUDE_API_COST_KERNEL_H_
