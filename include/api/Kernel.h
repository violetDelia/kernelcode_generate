/*
功能说明:
- 定义 include/api 层统一对外的 Kernel 计算 helper 声明。
- 当前公开集合只覆盖已进入 `kernel dialect emit` 合同真源的 helper，并统一使用 `out-first` 参数顺序。

API 列表:
- `template <MemorySpace Space, typename InType, typename OutType> Status npu_demo::add(Memory<Space, OutType>& out, const Memory<Space, InType>& lhs, const Memory<Space, InType>& rhs)`
- `template <MemorySpace Space, typename InType, typename OutType> Status npu_demo::sub(Memory<Space, OutType>& out, const Memory<Space, InType>& lhs, const Memory<Space, InType>& rhs)`
- `template <MemorySpace Space, typename InType, typename OutType> Status npu_demo::mul(Memory<Space, OutType>& out, const Memory<Space, InType>& lhs, const Memory<Space, InType>& rhs)`
- `template <MemorySpace Space, typename InType, typename OutType> Status npu_demo::truediv(Memory<Space, OutType>& out, const Memory<Space, InType>& lhs, const Memory<Space, InType>& rhs)`
- `template <MemorySpace Space, typename InType, typename OutType> Status npu_demo::eq(Memory<Space, OutType>& out, const Memory<Space, InType>& lhs, const Memory<Space, InType>& rhs)`
- `template <MemorySpace Space, typename InType, typename OutType> Status npu_demo::ne(Memory<Space, OutType>& out, const Memory<Space, InType>& lhs, const Memory<Space, InType>& rhs)`
- `template <MemorySpace Space, typename InType, typename OutType> Status npu_demo::lt(Memory<Space, OutType>& out, const Memory<Space, InType>& lhs, const Memory<Space, InType>& rhs)`
- `template <MemorySpace Space, typename InType, typename OutType> Status npu_demo::le(Memory<Space, OutType>& out, const Memory<Space, InType>& lhs, const Memory<Space, InType>& rhs)`
- `template <MemorySpace Space, typename InType, typename OutType> Status npu_demo::gt(Memory<Space, OutType>& out, const Memory<Space, InType>& lhs, const Memory<Space, InType>& rhs)`
- `template <MemorySpace Space, typename InType, typename OutType> Status npu_demo::ge(Memory<Space, OutType>& out, const Memory<Space, InType>& lhs, const Memory<Space, InType>& rhs)`
- `template <MemorySpace Space, typename InType, typename OutType> Status npu_demo::exp(Memory<Space, OutType>& out, const Memory<Space, InType>& input)`
- `template <MemorySpace Space, typename InType, typename OutType> Status npu_demo::select(Memory<Space, OutType>& out, const Memory<Space, bool>& cond, const Memory<Space, InType>& lhs, const Memory<Space, InType>& rhs)`
- `template <MemorySpace Space, typename InType, typename OutType> Status npu_demo::reduce_sum(Memory<Space, OutType>& out, const Memory<Space, InType>& input, long long axis)`
- `template <MemorySpace Space, typename InType, typename OutType> Status npu_demo::reduce_min(Memory<Space, OutType>& out, const Memory<Space, InType>& input, long long axis)`
- `template <MemorySpace LhsSpace, MemorySpace RhsSpace, MemorySpace OutSpace, typename LhsType, typename RhsType, typename OutType> Status npu_demo::matmul(Memory<OutSpace, OutType>& out, const Memory<LhsSpace, LhsType>& lhs, const Memory<RhsSpace, RhsType>& rhs)`
- `template <MemorySpace InputSpace, MemorySpace OutputSpace, typename InType, typename OutType> Status npu_demo::img2col1d(Memory<OutputSpace, OutType>& out, const Memory<InputSpace, InType>& input, long long k, long long s, long long d, long long p_left, long long p_right)`
- `template <MemorySpace InputSpace, MemorySpace OutputSpace, typename InType, typename OutType> Status npu_demo::img2col2d(Memory<OutputSpace, OutType>& out, const Memory<InputSpace, InType>& input, long long kh, long long kw, long long sh, long long sw, long long dh, long long dw, long long ph, long long pw, long long pl, long long pr)`

helper 清单:
- 无；当前文件只声明公开 Kernel helper。

使用示例:
- #include "include/api/Kernel.h"
- Status status = npu_demo::add<GM, float, float>(out, lhs, rhs);
- Status status2 = npu_demo::matmul<TSM, TSM, TLM1, float, float, float>(out, lhs, rhs);

创建者: 小李飞刀
最后修改人: 小李飞刀

关联文件:
- spec: spec/include/api/Kernel.md
- test: test/include/api/test_kernel.py
- 功能实现: include/npu_demo/Kernel.h
*/

#ifndef KERNELCODE_GENERATE_INCLUDE_API_KERNEL_H_
#define KERNELCODE_GENERATE_INCLUDE_API_KERNEL_H_

#include "include/api/Core.h"
#include "include/api/Memory.h"

namespace npu_demo {

/*
功能说明:
- 定义逐元素二元算术 helper 的统一公开声明，固定参数顺序为 `out -> lhs -> rhs`。

使用示例:
- Status st = npu_demo::add<GM, float, float>(out, lhs, rhs);
- Status st2 = npu_demo::truediv<TSM, int32_t, float>(out, lhs, rhs);

创建者: 小李飞刀
最后修改人: 小李飞刀

关联文件:
- spec: spec/include/api/Kernel.md
- test: test/include/api/test_kernel.py
- 功能实现: include/npu_demo/Kernel.h
*/
template <MemorySpace Space, typename InType, typename OutType>
Status add(Memory<Space, OutType>& out, const Memory<Space, InType>& lhs, const Memory<Space, InType>& rhs);
template <MemorySpace Space, typename InType, typename OutType>
Status sub(Memory<Space, OutType>& out, const Memory<Space, InType>& lhs, const Memory<Space, InType>& rhs);
template <MemorySpace Space, typename InType, typename OutType>
Status mul(Memory<Space, OutType>& out, const Memory<Space, InType>& lhs, const Memory<Space, InType>& rhs);
template <MemorySpace Space, typename InType, typename OutType>
Status truediv(Memory<Space, OutType>& out, const Memory<Space, InType>& lhs, const Memory<Space, InType>& rhs);

/*
功能说明:
- 定义逐元素比较 helper 的统一公开声明，固定参数顺序为 `out -> lhs -> rhs`。

使用示例:
- Status st = npu_demo::eq<GM, float, bool>(out, lhs, rhs);
- Status st2 = npu_demo::ge<TSM, int32_t, bool>(out, lhs, rhs);

创建者: 小李飞刀
最后修改人: 小李飞刀

关联文件:
- spec: spec/include/api/Kernel.md
- test: test/include/api/test_kernel.py
- 功能实现: include/npu_demo/Kernel.h
*/
template <MemorySpace Space, typename InType, typename OutType>
Status eq(Memory<Space, OutType>& out, const Memory<Space, InType>& lhs, const Memory<Space, InType>& rhs);
template <MemorySpace Space, typename InType, typename OutType>
Status ne(Memory<Space, OutType>& out, const Memory<Space, InType>& lhs, const Memory<Space, InType>& rhs);
template <MemorySpace Space, typename InType, typename OutType>
Status lt(Memory<Space, OutType>& out, const Memory<Space, InType>& lhs, const Memory<Space, InType>& rhs);
template <MemorySpace Space, typename InType, typename OutType>
Status le(Memory<Space, OutType>& out, const Memory<Space, InType>& lhs, const Memory<Space, InType>& rhs);
template <MemorySpace Space, typename InType, typename OutType>
Status gt(Memory<Space, OutType>& out, const Memory<Space, InType>& lhs, const Memory<Space, InType>& rhs);
template <MemorySpace Space, typename InType, typename OutType>
Status ge(Memory<Space, OutType>& out, const Memory<Space, InType>& lhs, const Memory<Space, InType>& rhs);

/*
功能说明:
- 定义一元 helper 与条件选择 helper 的统一公开声明。

使用示例:
- Status st = npu_demo::exp<GM, float, float>(out, input);
- Status st2 = npu_demo::select<GM, float, float>(out, cond, lhs, rhs);

创建者: 小李飞刀
最后修改人: 小李飞刀

关联文件:
- spec: spec/include/api/Kernel.md
- test: test/include/api/test_kernel.py
- 功能实现: include/npu_demo/Kernel.h
*/
template <MemorySpace Space, typename InType, typename OutType>
Status exp(Memory<Space, OutType>& out, const Memory<Space, InType>& input);
template <MemorySpace Space, typename InType, typename OutType>
Status select(
    Memory<Space, OutType>& out,
    const Memory<Space, bool>& cond,
    const Memory<Space, InType>& lhs,
    const Memory<Space, InType>& rhs);

/*
功能说明:
- 定义 reduce family 的统一公开声明，固定参数顺序为 `out -> input -> axis`。

使用示例:
- Status st = npu_demo::reduce_sum<GM, float, float>(out, input, 1);
- Status st2 = npu_demo::reduce_min<TSM, int32_t, int32_t>(out, input, 0);

创建者: 小李飞刀
最后修改人: 小李飞刀

关联文件:
- spec: spec/include/api/Kernel.md
- test: test/include/api/test_kernel.py
- 功能实现: include/npu_demo/Kernel.h
*/
template <MemorySpace Space, typename InType, typename OutType>
Status reduce_sum(Memory<Space, OutType>& out, const Memory<Space, InType>& input, long long axis);
template <MemorySpace Space, typename InType, typename OutType>
Status reduce_min(Memory<Space, OutType>& out, const Memory<Space, InType>& input, long long axis);

/*
功能说明:
- 定义矩阵乘与 img2col family 的统一公开声明。
- `matmul` 与 `img2col*` 允许输入与输出使用不同的 MemorySpace。

使用示例:
- Status st = npu_demo::matmul<TSM, TSM, TLM1, float, float, float>(out, lhs, rhs);
- Status st2 = npu_demo::img2col1d<GM, TSM, float, float>(out, input, 3, 2, 1, 1, 1);

创建者: 小李飞刀
最后修改人: 小李飞刀

关联文件:
- spec: spec/include/api/Kernel.md
- test: test/include/api/test_kernel.py
- 功能实现: include/npu_demo/Kernel.h
*/
template <MemorySpace LhsSpace, MemorySpace RhsSpace, MemorySpace OutSpace, typename LhsType, typename RhsType, typename OutType>
Status matmul(
    Memory<OutSpace, OutType>& out,
    const Memory<LhsSpace, LhsType>& lhs,
    const Memory<RhsSpace, RhsType>& rhs);
template <MemorySpace InputSpace, MemorySpace OutputSpace, typename InType, typename OutType>
Status img2col1d(
    Memory<OutputSpace, OutType>& out,
    const Memory<InputSpace, InType>& input,
    long long k,
    long long s,
    long long d,
    long long p_left,
    long long p_right);
template <MemorySpace InputSpace, MemorySpace OutputSpace, typename InType, typename OutType>
Status img2col2d(
    Memory<OutputSpace, OutType>& out,
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

}  // namespace npu_demo

#endif  // KERNELCODE_GENERATE_INCLUDE_API_KERNEL_H_
