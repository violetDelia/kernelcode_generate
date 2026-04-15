/*
功能说明:
- 提供 npu_demo 后端的逐元素算术、比较、显式 broadcast 与 matmul 轻量实现。

使用示例:
- #include "include/npu_demo/Nn.h"
- Status status = add(lhs, rhs, out);

创建者: 摸鱼小分队
最后修改人: 金铲铲大作战

关联文件:
- spec: spec/include/api/Nn.md
- test: test/include/api/test_nn.py
- 功能实现: include/npu_demo/Nn.h
*/

#ifndef KERNELCODE_GENERATE_INCLUDE_NPU_DEMO_NN_H_
#define KERNELCODE_GENERATE_INCLUDE_NPU_DEMO_NN_H_

#include "include/npu_demo/Memory.h"
#include "include/npu_demo/Core.h"

/*
功能说明:
- 对两个内存视图执行逐元素加法，结果写入输出视图。
- 允许输入与输出位于不同 `MemorySpace`，以支持 `TSM + TSM -> TLMx` 这类 npu_demo 片上流水线。

使用示例:
- Status status = add(lhs, rhs, out);

创建者: 摸鱼小分队
最后修改人: 金铲铲大作战

关联文件:
- spec: spec/include/api/Nn.md
- test: test/include/api/test_nn.py
- 功能实现: include/npu_demo/Nn.h
*/
template <MemorySpace LhsSpace, MemorySpace RhsSpace, MemorySpace OutSpace, typename T>
inline Status add(const Memory<LhsSpace, T>& lhs, const Memory<RhsSpace, T>& rhs, Memory<OutSpace, T>& out) {
    if (lhs.rank() != 1 || rhs.rank() != 1 || out.rank() != 1) {
        return StatusCode::kError;
    }
    const long long lhs_size = lhs.shape()[0];
    const long long rhs_size = rhs.shape()[0];
    const long long out_size = out.shape()[0];
    if (lhs_size <= 0 || rhs_size <= 0 || out_size <= 0) {
        return StatusCode::kError;
    }
    if (lhs_size != rhs_size || lhs_size != out_size) {
        return StatusCode::kError;
    }
    const long long lhs_stride = lhs.stride()[0];
    const long long rhs_stride = rhs.stride()[0];
    const long long out_stride = out.stride()[0];
    for (long long i = 0; i < lhs_size; ++i) {
        out.data()[i * out_stride] = lhs.data()[i * lhs_stride] + rhs.data()[i * rhs_stride];
    }
    return StatusCode::kOk;
}

template <MemorySpace Space, typename T>
inline Status add(const Memory<Space, T>& lhs, const Memory<Space, T>& rhs, Memory<Space, T>& out) {
    return add<Space, Space, Space, T>(lhs, rhs, out);
}

/*
功能说明:
- 对两个二维内存视图执行矩阵乘法，结果写入输出视图。

使用示例:
- Status status = matmul(lhs, rhs, out);

创建者: 小李飞刀
最后修改人: 小李飞刀

关联文件:
- spec: spec/include/api/Nn.md
- test: test/dsl/test_gen_kernel.py
- 功能实现: include/npu_demo/Nn.h
*/
template <MemorySpace LhsSpace, MemorySpace RhsSpace, MemorySpace OutSpace, typename T>
inline Status matmul(
    const Memory<LhsSpace, T>& lhs,
    const Memory<RhsSpace, T>& rhs,
    Memory<OutSpace, T>& out) {
    if (lhs.rank() != 2 || rhs.rank() != 2 || out.rank() != 2) {
        return StatusCode::kError;
    }
    const long long m = lhs.get_shape(0);
    const long long k = lhs.get_shape(1);
    const long long rhs_k = rhs.get_shape(0);
    const long long n = rhs.get_shape(1);
    if (m <= 0 || k <= 0 || rhs_k <= 0 || n <= 0) {
        return StatusCode::kError;
    }
    if (rhs_k != k || out.get_shape(0) != m || out.get_shape(1) != n) {
        return StatusCode::kError;
    }
    if (lhs.data() == nullptr || rhs.data() == nullptr || out.data() == nullptr) {
        return StatusCode::kError;
    }

    long long lhs_indices[2] = {0, 0};
    long long rhs_indices[2] = {0, 0};
    long long out_indices[2] = {0, 0};
    for (long long mi = 0; mi < m; ++mi) {
        lhs_indices[0] = mi;
        out_indices[0] = mi;
        for (long long ni = 0; ni < n; ++ni) {
            rhs_indices[1] = ni;
            out_indices[1] = ni;
            T acc = static_cast<T>(0);
            for (long long ki = 0; ki < k; ++ki) {
                lhs_indices[1] = ki;
                rhs_indices[0] = ki;
                acc += lhs.at(lhs_indices) * rhs.at(rhs_indices);
            }
            out.at(out_indices) = acc;
        }
    }
    return StatusCode::kOk;
}

namespace npu_demo {

using ::matmul;

}  // namespace npu_demo

/*
功能说明:
- 对两个内存视图执行逐元素减法，结果写入输出视图。

使用示例:
- Status status = sub(lhs, rhs, out);

创建者: 摸鱼小分队
最后修改人: jcc你莫辜负

关联文件:
- spec: spec/include/api/Nn.md
- test: test/include/api/test_nn.py
- 功能实现: include/npu_demo/Nn.h
*/
template <MemorySpace Space, typename T>
inline Status sub(const Memory<Space, T>& lhs, const Memory<Space, T>& rhs, Memory<Space, T>& out) {
    (void)lhs;
    (void)rhs;
    (void)out;
    return StatusCode::kOk;
}

/*
功能说明:
- 对两个内存视图执行逐元素乘法，结果写入输出视图。

使用示例:
- Status status = mul(lhs, rhs, out);

创建者: 摸鱼小分队
最后修改人: jcc你莫辜负

关联文件:
- spec: spec/include/api/Nn.md
- test: test/include/api/test_nn.py
- 功能实现: include/npu_demo/Nn.h
*/
template <MemorySpace Space, typename T>
inline Status mul(const Memory<Space, T>& lhs, const Memory<Space, T>& rhs, Memory<Space, T>& out) {
    (void)lhs;
    (void)rhs;
    (void)out;
    return StatusCode::kOk;
}

/*
功能说明:
- 对两个内存视图执行逐元素真除法，结果写入输出视图。

使用示例:
- Status status = truediv(lhs, rhs, out);

创建者: 摸鱼小分队
最后修改人: jcc你莫辜负

关联文件:
- spec: spec/include/api/Nn.md
- test: test/include/api/test_nn.py
- 功能实现: include/npu_demo/Nn.h
*/
template <MemorySpace Space, typename T>
inline Status truediv(const Memory<Space, T>& lhs, const Memory<Space, T>& rhs, Memory<Space, T>& out) {
    (void)lhs;
    (void)rhs;
    (void)out;
    return StatusCode::kOk;
}

/*
功能说明:
- 对两个内存视图执行逐元素相等比较。

使用示例:
- Status status = eq(lhs, rhs, out);

创建者: 摸鱼小分队
最后修改人: jcc你莫辜负

关联文件:
- spec: spec/include/api/Nn.md
- test: test/include/api/test_nn.py
- 功能实现: include/npu_demo/Nn.h
*/
template <MemorySpace Space, typename T, typename PredT>
inline Status eq(const Memory<Space, T>& lhs, const Memory<Space, T>& rhs, Memory<Space, PredT>& out) {
    (void)lhs;
    (void)rhs;
    (void)out;
    return StatusCode::kOk;
}

/*
功能说明:
- 对两个内存视图执行逐元素不等比较。

使用示例:
- Status status = ne(lhs, rhs, out);

创建者: 摸鱼小分队
最后修改人: jcc你莫辜负

关联文件:
- spec: spec/include/api/Nn.md
- test: test/include/api/test_nn.py
- 功能实现: include/npu_demo/Nn.h
*/
template <MemorySpace Space, typename T, typename PredT>
inline Status ne(const Memory<Space, T>& lhs, const Memory<Space, T>& rhs, Memory<Space, PredT>& out) {
    (void)lhs;
    (void)rhs;
    (void)out;
    return StatusCode::kOk;
}

/*
功能说明:
- 对两个内存视图执行逐元素小于比较。

使用示例:
- Status status = lt(lhs, rhs, out);

创建者: 摸鱼小分队
最后修改人: jcc你莫辜负

关联文件:
- spec: spec/include/api/Nn.md
- test: test/include/api/test_nn.py
- 功能实现: include/npu_demo/Nn.h
*/
template <MemorySpace Space, typename T, typename PredT>
inline Status lt(const Memory<Space, T>& lhs, const Memory<Space, T>& rhs, Memory<Space, PredT>& out) {
    (void)lhs;
    (void)rhs;
    (void)out;
    return StatusCode::kOk;
}

/*
功能说明:
- 对两个内存视图执行逐元素小于等于比较。

使用示例:
- Status status = le(lhs, rhs, out);

创建者: 摸鱼小分队
最后修改人: jcc你莫辜负

关联文件:
- spec: spec/include/api/Nn.md
- test: test/include/api/test_nn.py
- 功能实现: include/npu_demo/Nn.h
*/
template <MemorySpace Space, typename T, typename PredT>
inline Status le(const Memory<Space, T>& lhs, const Memory<Space, T>& rhs, Memory<Space, PredT>& out) {
    (void)lhs;
    (void)rhs;
    (void)out;
    return StatusCode::kOk;
}

/*
功能说明:
- 对两个内存视图执行逐元素大于比较。

使用示例:
- Status status = gt(lhs, rhs, out);

创建者: 摸鱼小分队
最后修改人: jcc你莫辜负

关联文件:
- spec: spec/include/api/Nn.md
- test: test/include/api/test_nn.py
- 功能实现: include/npu_demo/Nn.h
*/
template <MemorySpace Space, typename T, typename PredT>
inline Status gt(const Memory<Space, T>& lhs, const Memory<Space, T>& rhs, Memory<Space, PredT>& out) {
    (void)lhs;
    (void)rhs;
    (void)out;
    return StatusCode::kOk;
}

/*
功能说明:
- 对两个内存视图执行逐元素大于等于比较。

使用示例:
- Status status = ge(lhs, rhs, out);

创建者: 摸鱼小分队
最后修改人: jcc你莫辜负

关联文件:
- spec: spec/include/api/Nn.md
- test: test/include/api/test_nn.py
- 功能实现: include/npu_demo/Nn.h
*/
template <MemorySpace Space, typename T, typename PredT>
inline Status ge(const Memory<Space, T>& lhs, const Memory<Space, T>& rhs, Memory<Space, PredT>& out) {
    (void)lhs;
    (void)rhs;
    (void)out;
    return StatusCode::kOk;
}

/*
功能说明:
- 执行显式 broadcast，将 input 写入 out。

使用示例:
- Status status = broadcast(input, out);

创建者: 摸鱼小分队
最后修改人: jcc你莫辜负

关联文件:
- spec: spec/include/api/Nn.md
- test: test/include/api/test_nn.py
- 功能实现: include/npu_demo/Nn.h
*/
template <MemorySpace Space, typename T>
inline Status broadcast(const Memory<Space, T>& input, Memory<Space, T>& out) {
    (void)input;
    (void)out;
    return StatusCode::kOk;
}

#endif  // KERNELCODE_GENERATE_INCLUDE_NPU_DEMO_NN_H_
