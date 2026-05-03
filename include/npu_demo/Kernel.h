/*
功能说明:
- 提供 npu_demo 后端的 Kernel helper 轻量实现，匹配 `include/api/Kernel.h` 的公开声明。
- 当前实现覆盖 same-shape 逐元素、reduce、matmul 与 img2col 的真实运行路径。

API 列表:
- `npu_demo::add<Space, InType, OutType>(Memory<Space, OutType>& out, const Memory<Space, InType>& lhs, const Memory<Space, InType>& rhs) -> Status`
- `npu_demo::sub<Space, InType, OutType>(Memory<Space, OutType>& out, const Memory<Space, InType>& lhs, const Memory<Space, InType>& rhs) -> Status`
- `npu_demo::mul<Space, InType, OutType>(Memory<Space, OutType>& out, const Memory<Space, InType>& lhs, const Memory<Space, InType>& rhs) -> Status`
- `npu_demo::truediv<Space, InType, OutType>(Memory<Space, OutType>& out, const Memory<Space, InType>& lhs, const Memory<Space, InType>& rhs) -> Status`
- `npu_demo::eq/ne/lt/le/gt/ge<Space, InType, OutType>(Memory<Space, OutType>& out, const Memory<Space, InType>& lhs, const Memory<Space, InType>& rhs) -> Status`
- `npu_demo::exp<Space, InType, OutType>(Memory<Space, OutType>& out, const Memory<Space, InType>& input) -> Status`
- `npu_demo::select<Space, InType, OutType>(Memory<Space, OutType>& out, const Memory<Space, bool>& cond, const Memory<Space, InType>& lhs, const Memory<Space, InType>& rhs) -> Status`
- `npu_demo::reduce_sum<Space, InType, OutType>(Memory<Space, OutType>& out, const Memory<Space, InType>& input, long long axis) -> Status`
- `npu_demo::reduce_min<Space, InType, OutType>(Memory<Space, OutType>& out, const Memory<Space, InType>& input, long long axis) -> Status`
- `npu_demo::reduce_max<Space, InType, OutType>(Memory<Space, OutType>& out, const Memory<Space, InType>& input, long long axis) -> Status`
- `npu_demo::matmul<LhsSpace, RhsSpace, OutSpace, LhsType, RhsType, OutType>(Memory<OutSpace, OutType>& out, const Memory<LhsSpace, LhsType>& lhs, const Memory<RhsSpace, RhsType>& rhs) -> Status`
- `npu_demo::img2col1d<InputSpace, OutputSpace, InType, OutType>(Memory<OutputSpace, OutType>& out, const Memory<InputSpace, InType>& input, long long k, long long s, long long d, long long p_left, long long p_right) -> Status`
- `npu_demo::img2col2d<InputSpace, OutputSpace, InType, OutType>(Memory<OutputSpace, OutType>& out, const Memory<InputSpace, InType>& input, long long kh, long long kw, long long sh, long long sw, long long dh, long long dw, long long ph, long long pw, long long pl, long long pr) -> Status`

使用示例:
- #include "include/npu_demo/Kernel.h"
- Status st = npu_demo::add<GM, float, float>(out, lhs, rhs);
- Status st2 = npu_demo::matmul<TSM, TSM, TLM1, float, float, float>(out, lhs, rhs);


关联文件:
- spec: spec/include/api/Kernel.md
- test: test/include/api/kernel.py
- 功能实现: include/npu_demo/Kernel.h
*/

#ifndef KERNELCODE_GENERATE_INCLUDE_NPU_DEMO_KERNEL_H_
#define KERNELCODE_GENERATE_INCLUDE_NPU_DEMO_KERNEL_H_

#include <cmath>
#include <limits>

#include "include/api/Kernel.h"
#include "include/npu_demo/Core.h"
#include "include/npu_demo/Memory.h"

namespace npu_demo {
namespace detail {

/*
功能说明:
- 判断输入指针是否非空，供各个 Kernel helper 的前置检查复用。

使用示例:
- bool ok = npu_demo::detail::is_non_null(mem.data());


关联文件:
- spec: spec/include/api/Kernel.md
- test: test/include/api/kernel.py
- 功能实现: include/npu_demo/Kernel.h
*/
template <typename T>
inline bool is_non_null(const T* ptr) {
    return ptr != nullptr;
}

/*
功能说明:
- 复用 same-shape 多维逐元素二元计算的公共前置检查与遍历逻辑。
- 由 `add/sub/mul/truediv` 和 compare family 共享。

使用示例:
- Status st = npu_demo::detail::elementwise_binary_same_shape(out, lhs, rhs, [](auto a, auto b) { return a + b; });


关联文件:
- spec: spec/include/api/Kernel.md
- test: test/include/api/kernel.py
- 功能实现: include/npu_demo/Kernel.h
*/
template <MemorySpace Space, typename InType, typename OutType, typename BinaryFn>
inline Status elementwise_binary_same_shape(
    Memory<Space, OutType>& out,
    const Memory<Space, InType>& lhs,
    const Memory<Space, InType>& rhs,
    BinaryFn fn) {
    const unsigned long long rank = out.rank();
    if (rank == 0 || rank > 8 || lhs.rank() != rank || rhs.rank() != rank) {
        return StatusCode::kError;
    }
    if (!is_non_null(lhs.data()) || !is_non_null(rhs.data()) || !is_non_null(out.data())) {
        return StatusCode::kError;
    }
    long long element_count = 1;
    for (unsigned long long axis = 0; axis < rank; ++axis) {
        const long long extent = out.get_shape(axis);
        if (extent <= 0 || lhs.get_shape(axis) != extent || rhs.get_shape(axis) != extent) {
            return StatusCode::kError;
        }
        if (out.get_stride(axis) <= 0 || lhs.get_stride(axis) <= 0 || rhs.get_stride(axis) <= 0) {
            return StatusCode::kError;
        }
        if (element_count > std::numeric_limits<long long>::max() / extent) {
            return StatusCode::kError;
        }
        element_count *= extent;
    }
    long long indices[8] = {0};
    for (long long linear = 0; linear < element_count; ++linear) {
        long long remainder = linear;
        for (unsigned long long reverse_index = 0; reverse_index < rank; ++reverse_index) {
            const unsigned long long axis = rank - 1 - reverse_index;
            indices[axis] = remainder % out.get_shape(axis);
            remainder /= out.get_shape(axis);
        }
        out.at(indices) = static_cast<OutType>(fn(lhs.at(indices), rhs.at(indices)));
    }
    return StatusCode::kOk;
}

/*
功能说明:
- 复用 same-shape 多维逐元素一元计算的公共前置检查与遍历逻辑。
- 由 `exp` 等一元 helper 共享。

使用示例:
- Status st = npu_demo::detail::elementwise_unary_same_shape(out, input, [](auto value) { return value; });


关联文件:
- spec: spec/include/api/Kernel.md
- test: test/include/api/kernel.py
- 功能实现: include/npu_demo/Kernel.h
*/
template <MemorySpace Space, typename InType, typename OutType, typename UnaryFn>
inline Status elementwise_unary_same_shape(
    Memory<Space, OutType>& out,
    const Memory<Space, InType>& input,
    UnaryFn fn) {
    const unsigned long long rank = out.rank();
    if (rank == 0 || rank > 8 || input.rank() != rank) {
        return StatusCode::kError;
    }
    if (!is_non_null(input.data()) || !is_non_null(out.data())) {
        return StatusCode::kError;
    }
    long long element_count = 1;
    for (unsigned long long axis = 0; axis < rank; ++axis) {
        const long long extent = out.get_shape(axis);
        if (extent <= 0 || input.get_shape(axis) != extent) {
            return StatusCode::kError;
        }
        if (out.get_stride(axis) <= 0 || input.get_stride(axis) <= 0) {
            return StatusCode::kError;
        }
        if (element_count > std::numeric_limits<long long>::max() / extent) {
            return StatusCode::kError;
        }
        element_count *= extent;
    }
    long long indices[8] = {0};
    for (long long linear = 0; linear < element_count; ++linear) {
        long long remainder = linear;
        for (unsigned long long reverse_index = 0; reverse_index < rank; ++reverse_index) {
            const unsigned long long axis = rank - 1 - reverse_index;
            indices[axis] = remainder % out.get_shape(axis);
            remainder /= out.get_shape(axis);
        }
        out.at(indices) = static_cast<OutType>(fn(input.at(indices)));
    }
    return StatusCode::kOk;
}

/*
功能说明:
- 复用 same-shape 多维逐元素比较 helper 的公共遍历逻辑。
- 由 `eq/ne/lt/le/gt/ge` 共享。

使用示例:
- Status st = npu_demo::detail::compare_same_shape(out, lhs, rhs, [](auto a, auto b) { return a == b; });


关联文件:
- spec: spec/include/api/Kernel.md
- test: test/include/api/kernel.py
- 功能实现: include/npu_demo/Kernel.h
*/
template <MemorySpace Space, typename InType, typename OutType, typename CompareFn>
inline Status compare_same_shape(
    Memory<Space, OutType>& out,
    const Memory<Space, InType>& lhs,
    const Memory<Space, InType>& rhs,
    CompareFn fn) {
    return elementwise_binary_same_shape(out, lhs, rhs, fn);
}

}  // namespace detail

/*
功能说明:
- 执行 same-shape 多维逐元素加法并把结果写入 `out`。

使用示例:
- Status st = npu_demo::add<GM, float, float>(out, lhs, rhs);


关联文件:
- spec: spec/include/api/Kernel.md
- test: test/include/api/kernel.py
- 功能实现: include/npu_demo/Kernel.h
*/
template <MemorySpace Space, typename InType, typename OutType>
inline Status add(Memory<Space, OutType>& out, const Memory<Space, InType>& lhs, const Memory<Space, InType>& rhs) {
    return detail::elementwise_binary_same_shape(out, lhs, rhs, [](const InType& a, const InType& b) { return a + b; });
}

/*
功能说明:
- 执行 same-shape 多维逐元素减法并把结果写入 `out`。

使用示例:
- Status st = npu_demo::sub<GM, float, float>(out, lhs, rhs);


关联文件:
- spec: spec/include/api/Kernel.md
- test: test/include/api/kernel.py
- 功能实现: include/npu_demo/Kernel.h
*/
template <MemorySpace Space, typename InType, typename OutType>
inline Status sub(Memory<Space, OutType>& out, const Memory<Space, InType>& lhs, const Memory<Space, InType>& rhs) {
    return detail::elementwise_binary_same_shape(out, lhs, rhs, [](const InType& a, const InType& b) { return a - b; });
}

/*
功能说明:
- 执行 same-shape 多维逐元素乘法并把结果写入 `out`。

使用示例:
- Status st = npu_demo::mul<GM, float, float>(out, lhs, rhs);


关联文件:
- spec: spec/include/api/Kernel.md
- test: test/include/api/kernel.py
- 功能实现: include/npu_demo/Kernel.h
*/
template <MemorySpace Space, typename InType, typename OutType>
inline Status mul(Memory<Space, OutType>& out, const Memory<Space, InType>& lhs, const Memory<Space, InType>& rhs) {
    return detail::elementwise_binary_same_shape(out, lhs, rhs, [](const InType& a, const InType& b) { return a * b; });
}

/*
功能说明:
- 执行 same-shape 多维逐元素真除法并把结果写入 `out`。

使用示例:
- Status st = npu_demo::truediv<GM, float, float>(out, lhs, rhs);


关联文件:
- spec: spec/include/api/Kernel.md
- test: test/include/api/kernel.py
- 功能实现: include/npu_demo/Kernel.h
*/
template <MemorySpace Space, typename InType, typename OutType>
inline Status truediv(Memory<Space, OutType>& out, const Memory<Space, InType>& lhs, const Memory<Space, InType>& rhs) {
    return detail::elementwise_binary_same_shape(
        out,
        lhs,
        rhs,
        [](const InType& a, const InType& b) -> OutType {
            return static_cast<OutType>(static_cast<double>(a) / static_cast<double>(b));
        });
}

/*
功能说明:
- 执行 same-shape 多维逐元素相等比较并把结果写入 `out`。

使用示例:
- Status st = npu_demo::eq<GM, float, bool>(out, lhs, rhs);


关联文件:
- spec: spec/include/api/Kernel.md
- test: test/include/api/kernel.py
- 功能实现: include/npu_demo/Kernel.h
*/
template <MemorySpace Space, typename InType, typename OutType>
inline Status eq(Memory<Space, OutType>& out, const Memory<Space, InType>& lhs, const Memory<Space, InType>& rhs) {
    return detail::compare_same_shape(out, lhs, rhs, [](const InType& a, const InType& b) { return a == b; });
}

/*
功能说明:
- 执行 same-shape 多维逐元素不等比较并把结果写入 `out`。

使用示例:
- Status st = npu_demo::ne<GM, float, bool>(out, lhs, rhs);


关联文件:
- spec: spec/include/api/Kernel.md
- test: test/include/api/kernel.py
- 功能实现: include/npu_demo/Kernel.h
*/
template <MemorySpace Space, typename InType, typename OutType>
inline Status ne(Memory<Space, OutType>& out, const Memory<Space, InType>& lhs, const Memory<Space, InType>& rhs) {
    return detail::compare_same_shape(out, lhs, rhs, [](const InType& a, const InType& b) { return a != b; });
}

/*
功能说明:
- 执行 same-shape 多维逐元素小于比较并把结果写入 `out`。

使用示例:
- Status st = npu_demo::lt<GM, float, bool>(out, lhs, rhs);


关联文件:
- spec: spec/include/api/Kernel.md
- test: test/include/api/kernel.py
- 功能实现: include/npu_demo/Kernel.h
*/
template <MemorySpace Space, typename InType, typename OutType>
inline Status lt(Memory<Space, OutType>& out, const Memory<Space, InType>& lhs, const Memory<Space, InType>& rhs) {
    return detail::compare_same_shape(out, lhs, rhs, [](const InType& a, const InType& b) { return a < b; });
}

/*
功能说明:
- 执行 same-shape 多维逐元素小于等于比较并把结果写入 `out`。

使用示例:
- Status st = npu_demo::le<GM, float, bool>(out, lhs, rhs);


关联文件:
- spec: spec/include/api/Kernel.md
- test: test/include/api/kernel.py
- 功能实现: include/npu_demo/Kernel.h
*/
template <MemorySpace Space, typename InType, typename OutType>
inline Status le(Memory<Space, OutType>& out, const Memory<Space, InType>& lhs, const Memory<Space, InType>& rhs) {
    return detail::compare_same_shape(out, lhs, rhs, [](const InType& a, const InType& b) { return a <= b; });
}

/*
功能说明:
- 执行 same-shape 多维逐元素大于比较并把结果写入 `out`。

使用示例:
- Status st = npu_demo::gt<GM, float, bool>(out, lhs, rhs);


关联文件:
- spec: spec/include/api/Kernel.md
- test: test/include/api/kernel.py
- 功能实现: include/npu_demo/Kernel.h
*/
template <MemorySpace Space, typename InType, typename OutType>
inline Status gt(Memory<Space, OutType>& out, const Memory<Space, InType>& lhs, const Memory<Space, InType>& rhs) {
    return detail::compare_same_shape(out, lhs, rhs, [](const InType& a, const InType& b) { return a > b; });
}

/*
功能说明:
- 执行 same-shape 多维逐元素大于等于比较并把结果写入 `out`。

使用示例:
- Status st = npu_demo::ge<GM, float, bool>(out, lhs, rhs);


关联文件:
- spec: spec/include/api/Kernel.md
- test: test/include/api/kernel.py
- 功能实现: include/npu_demo/Kernel.h
*/
template <MemorySpace Space, typename InType, typename OutType>
inline Status ge(Memory<Space, OutType>& out, const Memory<Space, InType>& lhs, const Memory<Space, InType>& rhs) {
    return detail::compare_same_shape(out, lhs, rhs, [](const InType& a, const InType& b) { return a >= b; });
}

/*
功能说明:
- 执行 same-shape 多维逐元素指数计算并把结果写入 `out`。

使用示例:
- Status st = npu_demo::exp<GM, float, float>(out, input);


关联文件:
- spec: spec/include/api/Kernel.md
- test: test/include/api/kernel.py
- 功能实现: include/npu_demo/Kernel.h
*/
template <MemorySpace Space, typename InType, typename OutType>
inline Status exp(Memory<Space, OutType>& out, const Memory<Space, InType>& input) {
    return detail::elementwise_unary_same_shape(out, input, [](const InType& value) {
        return static_cast<OutType>(std::exp(static_cast<double>(value)));
    });
}

/*
功能说明:
- 按 `cond` 执行一维逐元素条件选择，并把结果写入 `out`。

使用示例:
- Status st = npu_demo::select<GM, float, float>(out, cond, lhs, rhs);


关联文件:
- spec: spec/include/api/Kernel.md
- test: test/include/api/kernel.py
- 功能实现: include/npu_demo/Kernel.h
*/
template <MemorySpace Space, typename InType, typename OutType>
inline Status select(
    Memory<Space, OutType>& out,
    const Memory<Space, bool>& cond,
    const Memory<Space, InType>& lhs,
    const Memory<Space, InType>& rhs) {
    if (cond.rank() != 1 || lhs.rank() != 1 || rhs.rank() != 1 || out.rank() != 1) {
        return StatusCode::kError;
    }
    if (!detail::is_non_null(cond.data()) || !detail::is_non_null(lhs.data()) || !detail::is_non_null(rhs.data()) ||
        !detail::is_non_null(out.data())) {
        return StatusCode::kError;
    }
    const long long size = cond.get_shape(0);
    if (size <= 0 || lhs.get_shape(0) != size || rhs.get_shape(0) != size || out.get_shape(0) != size) {
        return StatusCode::kError;
    }
    for (long long i = 0; i < size; ++i) {
        const long long cond_index = i * cond.get_stride(0);
        const long long lhs_index = i * lhs.get_stride(0);
        const long long rhs_index = i * rhs.get_stride(0);
        const long long out_index = i * out.get_stride(0);
        out.data()[out_index] = static_cast<OutType>(cond.data()[cond_index] ? lhs.data()[lhs_index] : rhs.data()[rhs_index]);
    }
    return StatusCode::kOk;
}

/*
功能说明:
- 对二维输入在指定 `axis` 上执行 `reduce_sum`，并把结果写入 `out`。

使用示例:
- Status st = npu_demo::reduce_sum<GM, float, float>(out, input, 1);


关联文件:
- spec: spec/include/api/Kernel.md
- test: test/include/api/kernel.py
- 功能实现: include/npu_demo/Kernel.h
*/
template <MemorySpace Space, typename InType, typename OutType>
inline Status reduce_sum(Memory<Space, OutType>& out, const Memory<Space, InType>& input, long long axis) {
    if (input.rank() != 2 || out.rank() != 2) {
        return StatusCode::kError;
    }
    if (!detail::is_non_null(input.data()) || !detail::is_non_null(out.data())) {
        return StatusCode::kError;
    }
    if (axis == 1) {
        if (out.get_shape(0) != input.get_shape(0) || out.get_shape(1) != 1) {
            return StatusCode::kError;
        }
        for (long long i = 0; i < input.get_shape(0); ++i) {
            OutType acc = static_cast<OutType>(0);
            for (long long j = 0; j < input.get_shape(1); ++j) {
                long long index[2] = {i, j};
                acc = static_cast<OutType>(acc + static_cast<OutType>(input.at(index)));
            }
            long long out_index[2] = {i, 0};
            out.at(out_index) = acc;
        }
        return StatusCode::kOk;
    }
    if (axis == 0) {
        if (out.get_shape(0) != 1 || out.get_shape(1) != input.get_shape(1)) {
            return StatusCode::kError;
        }
        for (long long j = 0; j < input.get_shape(1); ++j) {
            OutType acc = static_cast<OutType>(0);
            for (long long i = 0; i < input.get_shape(0); ++i) {
                long long index[2] = {i, j};
                acc = static_cast<OutType>(acc + static_cast<OutType>(input.at(index)));
            }
            long long out_index[2] = {0, j};
            out.at(out_index) = acc;
        }
        return StatusCode::kOk;
    }
    return StatusCode::kError;
}

/*
功能说明:
- 对二维输入在指定 `axis` 上执行 `reduce_min`，并把结果写入 `out`。

使用示例:
- Status st = npu_demo::reduce_min<GM, float, float>(out, input, 1);


关联文件:
- spec: spec/include/api/Kernel.md
- test: test/include/api/kernel.py
- 功能实现: include/npu_demo/Kernel.h
*/
template <MemorySpace Space, typename InType, typename OutType>
inline Status reduce_min(Memory<Space, OutType>& out, const Memory<Space, InType>& input, long long axis) {
    if (input.rank() != 2 || out.rank() != 2) {
        return StatusCode::kError;
    }
    if (!detail::is_non_null(input.data()) || !detail::is_non_null(out.data())) {
        return StatusCode::kError;
    }
    if (axis == 1) {
        if (out.get_shape(0) != input.get_shape(0) || out.get_shape(1) != 1) {
            return StatusCode::kError;
        }
        for (long long i = 0; i < input.get_shape(0); ++i) {
            long long start_index[2] = {i, 0};
            OutType current = static_cast<OutType>(input.at(start_index));
            for (long long j = 1; j < input.get_shape(1); ++j) {
                long long index[2] = {i, j};
                const OutType value = static_cast<OutType>(input.at(index));
                current = value < current ? value : current;
            }
            long long out_index[2] = {i, 0};
            out.at(out_index) = current;
        }
        return StatusCode::kOk;
    }
    if (axis == 0) {
        if (out.get_shape(0) != 1 || out.get_shape(1) != input.get_shape(1)) {
            return StatusCode::kError;
        }
        for (long long j = 0; j < input.get_shape(1); ++j) {
            long long start_index[2] = {0, j};
            OutType current = static_cast<OutType>(input.at(start_index));
            for (long long i = 1; i < input.get_shape(0); ++i) {
                long long index[2] = {i, j};
                const OutType value = static_cast<OutType>(input.at(index));
                current = value < current ? value : current;
            }
            long long out_index[2] = {0, j};
            out.at(out_index) = current;
        }
        return StatusCode::kOk;
    }
    return StatusCode::kError;
}

/*
功能说明:
- 对二维输入在指定 `axis` 上执行 `reduce_max`，并把结果写入 `out`。

使用示例:
- Status st = npu_demo::reduce_max<GM, float, float>(out, input, 1);


关联文件:
- spec: spec/include/api/Kernel.md
- test: test/include/api/kernel.py
- 功能实现: include/npu_demo/Kernel.h
*/
template <MemorySpace Space, typename InType, typename OutType>
inline Status reduce_max(Memory<Space, OutType>& out, const Memory<Space, InType>& input, long long axis) {
    if (input.rank() != 2 || out.rank() != 2) {
        return StatusCode::kError;
    }
    if (!detail::is_non_null(input.data()) || !detail::is_non_null(out.data())) {
        return StatusCode::kError;
    }
    if (axis == 1) {
        if (out.get_shape(0) != input.get_shape(0) || out.get_shape(1) != 1) {
            return StatusCode::kError;
        }
        for (long long i = 0; i < input.get_shape(0); ++i) {
            long long start_index[2] = {i, 0};
            OutType current = static_cast<OutType>(input.at(start_index));
            for (long long j = 1; j < input.get_shape(1); ++j) {
                long long index[2] = {i, j};
                const OutType value = static_cast<OutType>(input.at(index));
                current = value > current ? value : current;
            }
            long long out_index[2] = {i, 0};
            out.at(out_index) = current;
        }
        return StatusCode::kOk;
    }
    if (axis == 0) {
        if (out.get_shape(0) != 1 || out.get_shape(1) != input.get_shape(1)) {
            return StatusCode::kError;
        }
        for (long long j = 0; j < input.get_shape(1); ++j) {
            long long start_index[2] = {0, j};
            OutType current = static_cast<OutType>(input.at(start_index));
            for (long long i = 1; i < input.get_shape(0); ++i) {
                long long index[2] = {i, j};
                const OutType value = static_cast<OutType>(input.at(index));
                current = value > current ? value : current;
            }
            long long out_index[2] = {0, j};
            out.at(out_index) = current;
        }
        return StatusCode::kOk;
    }
    return StatusCode::kError;
}

/*
功能说明:
- 对二维输入执行矩阵乘法，并把结果写入 `out`。

使用示例:
- Status st = npu_demo::matmul<TSM, TSM, TLM1, float, float, float>(out, lhs, rhs);


关联文件:
- spec: spec/include/api/Kernel.md
- test: test/include/api/kernel.py
- 功能实现: include/npu_demo/Kernel.h
*/
template <MemorySpace LhsSpace, MemorySpace RhsSpace, MemorySpace OutSpace, typename LhsType, typename RhsType, typename OutType>
inline Status matmul(
    Memory<OutSpace, OutType>& out,
    const Memory<LhsSpace, LhsType>& lhs,
    const Memory<RhsSpace, RhsType>& rhs) {
    if (lhs.rank() != 2 || rhs.rank() != 2 || out.rank() != 2) {
        return StatusCode::kError;
    }
    if (!detail::is_non_null(lhs.data()) || !detail::is_non_null(rhs.data()) || !detail::is_non_null(out.data())) {
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
    long long lhs_indices[2] = {0, 0};
    long long rhs_indices[2] = {0, 0};
    long long out_indices[2] = {0, 0};
    for (long long mi = 0; mi < m; ++mi) {
        lhs_indices[0] = mi;
        out_indices[0] = mi;
        for (long long ni = 0; ni < n; ++ni) {
            rhs_indices[1] = ni;
            out_indices[1] = ni;
            OutType acc = static_cast<OutType>(0);
            for (long long ki = 0; ki < k; ++ki) {
                lhs_indices[1] = ki;
                rhs_indices[0] = ki;
                acc = static_cast<OutType>(
                    acc + static_cast<OutType>(lhs.at(lhs_indices)) * static_cast<OutType>(rhs.at(rhs_indices)));
            }
            out.at(out_indices) = acc;
        }
    }
    return StatusCode::kOk;
}

/*
功能说明:
- 提供 `img2col1d` 的公开承接实现，按 `[N, C, W] -> [N, C, K, Wo]` 物化展开窗口。

使用示例:
- Status st = npu_demo::img2col1d<GM, TSM, float, float>(out, input, 3, 2, 1, 1, 1);


关联文件:
- spec: spec/include/api/Kernel.md
- test: test/include/api/kernel.py
- 功能实现: include/npu_demo/Kernel.h
*/
template <MemorySpace InputSpace, MemorySpace OutputSpace, typename InType, typename OutType>
inline Status img2col1d(
    Memory<OutputSpace, OutType>& out,
    const Memory<InputSpace, InType>& input,
    long long k,
    long long s,
    long long d,
    long long p_left,
    long long p_right) {
    if (input.rank() != 3 || out.rank() != 4) {
        return StatusCode::kError;
    }
    if (!detail::is_non_null(input.data()) || !detail::is_non_null(out.data())) {
        return StatusCode::kError;
    }
    if (input.format() != MemoryFormat::Norm || out.format() != MemoryFormat::Norm) {
        return StatusCode::kError;
    }
    if (k <= 0 || s <= 0 || d <= 0 || p_left < 0 || p_right < 0) {
        return StatusCode::kError;
    }

    const long long n = input.get_shape(0);
    const long long c = input.get_shape(1);
    const long long w = input.get_shape(2);
    const long long w_out = ((w + p_left + p_right - d * (k - 1) - 1) / s) + 1;
    if (n <= 0 || c <= 0 || w <= 0 || w_out <= 0) {
        return StatusCode::kError;
    }
    if (out.get_shape(0) != n || out.get_shape(1) != c || out.get_shape(2) != k || out.get_shape(3) != w_out) {
        return StatusCode::kError;
    }

    long long input_index[3] = {0, 0, 0};
    long long out_index[4] = {0, 0, 0, 0};
    for (long long ni = 0; ni < n; ++ni) {
        input_index[0] = ni;
        out_index[0] = ni;
        for (long long ci = 0; ci < c; ++ci) {
            input_index[1] = ci;
            out_index[1] = ci;
            for (long long ki = 0; ki < k; ++ki) {
                out_index[2] = ki;
                for (long long wo = 0; wo < w_out; ++wo) {
                    out_index[3] = wo;
                    const long long source_w = wo * s + ki * d - p_left;
                    if (source_w < 0 || source_w >= w) {
                        out.at(out_index) = static_cast<OutType>(0);
                        continue;
                    }
                    input_index[2] = source_w;
                    out.at(out_index) = static_cast<OutType>(input.at(input_index));
                }
            }
        }
    }
    return StatusCode::kOk;
}

/*
功能说明:
- 提供 `img2col2d` 的公开承接实现，按 `[N, C, H, W] -> [N, C, KH, KW, Ho, Wo]` 物化展开窗口。

使用示例:
- Status st = npu_demo::img2col2d<GM, TSM, float, float>(out, input, 3, 2, 1, 2, 1, 1, 1, 0, 0, 1);


关联文件:
- spec: spec/include/api/Kernel.md
- test: test/include/api/kernel.py
- 功能实现: include/npu_demo/Kernel.h
*/
template <MemorySpace InputSpace, MemorySpace OutputSpace, typename InType, typename OutType>
inline Status img2col2d(
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
    long long pr) {
    if (input.rank() != 4 || out.rank() != 6) {
        return StatusCode::kError;
    }
    if (!detail::is_non_null(input.data()) || !detail::is_non_null(out.data())) {
        return StatusCode::kError;
    }
    if (input.format() != MemoryFormat::Norm || out.format() != MemoryFormat::Norm) {
        return StatusCode::kError;
    }
    if (kh <= 0 || kw <= 0 || sh <= 0 || sw <= 0 || dh <= 0 || dw <= 0) {
        return StatusCode::kError;
    }
    if (ph < 0 || pw < 0 || pl < 0 || pr < 0) {
        return StatusCode::kError;
    }

    const long long n = input.get_shape(0);
    const long long c = input.get_shape(1);
    const long long h = input.get_shape(2);
    const long long w = input.get_shape(3);
    const long long h_out = ((h + ph + pw - dh * (kh - 1) - 1) / sh) + 1;
    const long long w_out = ((w + pl + pr - dw * (kw - 1) - 1) / sw) + 1;
    if (n <= 0 || c <= 0 || h <= 0 || w <= 0 || h_out <= 0 || w_out <= 0) {
        return StatusCode::kError;
    }
    if (out.get_shape(0) != n || out.get_shape(1) != c || out.get_shape(2) != kh || out.get_shape(3) != kw ||
        out.get_shape(4) != h_out || out.get_shape(5) != w_out) {
        return StatusCode::kError;
    }

    long long input_index[4] = {0, 0, 0, 0};
    long long out_index[6] = {0, 0, 0, 0, 0, 0};
    for (long long ni = 0; ni < n; ++ni) {
        input_index[0] = ni;
        out_index[0] = ni;
        for (long long ci = 0; ci < c; ++ci) {
            input_index[1] = ci;
            out_index[1] = ci;
            for (long long khi = 0; khi < kh; ++khi) {
                out_index[2] = khi;
                for (long long kwi = 0; kwi < kw; ++kwi) {
                    out_index[3] = kwi;
                    for (long long ho = 0; ho < h_out; ++ho) {
                        out_index[4] = ho;
                        const long long source_h = ho * sh + khi * dh - ph;
                        for (long long wo = 0; wo < w_out; ++wo) {
                            out_index[5] = wo;
                            const long long source_w = wo * sw + kwi * dw - pl;
                            if (source_h < 0 || source_h >= h || source_w < 0 || source_w >= w) {
                                out.at(out_index) = static_cast<OutType>(0);
                                continue;
                            }
                            input_index[2] = source_h;
                            input_index[3] = source_w;
                            out.at(out_index) = static_cast<OutType>(input.at(input_index));
                        }
                    }
                }
            }
        }
    }
    return StatusCode::kOk;
}

}  // namespace npu_demo

/*
功能说明:
- 为 `gen_kernel(target="npu_demo")` 的 `add_barrier` 骨架提供跨 MemorySpace 的私有 `add(lhs, rhs, out)` 承接。
- 仅用于单入口源码中 `TSM + TSM -> TLMx` 这类受控路径；不改变 `include/api/Kernel.h` 的公开 `out-first` 合同。

使用示例:
- Status st = add(lhs_tsm, rhs_tsm, out_tlm);


关联文件:
- spec: spec/include/npu_demo/npu_demo.md
- test: test/dsl/gen_kernel/gen_kernel.py
- 功能实现: include/npu_demo/Kernel.h
*/
template <MemorySpace LhsSpace, MemorySpace RhsSpace, MemorySpace OutSpace, typename T>
inline Status add(const Memory<LhsSpace, T>& lhs, const Memory<RhsSpace, T>& rhs, Memory<OutSpace, T>& out) {
    if (lhs.rank() != 1 || rhs.rank() != 1 || out.rank() != 1) {
        return StatusCode::kError;
    }
    if (!npu_demo::detail::is_non_null(lhs.data()) || !npu_demo::detail::is_non_null(rhs.data())
        || !npu_demo::detail::is_non_null(out.data())) {
        return StatusCode::kError;
    }
    const long long lhs_size = lhs.get_shape(0);
    const long long rhs_size = rhs.get_shape(0);
    const long long out_size = out.get_shape(0);
    if (lhs_size <= 0 || rhs_size <= 0 || out_size <= 0) {
        return StatusCode::kError;
    }
    if (lhs_size != rhs_size || lhs_size != out_size) {
        return StatusCode::kError;
    }
    const long long lhs_stride = lhs.get_stride(0);
    const long long rhs_stride = rhs.get_stride(0);
    const long long out_stride = out.get_stride(0);
    if (lhs_stride <= 0 || rhs_stride <= 0 || out_stride <= 0) {
        return StatusCode::kError;
    }
    for (long long i = 0; i < lhs_size; ++i) {
        out.data()[i * out_stride] = lhs.data()[i * lhs_stride] + rhs.data()[i * rhs_stride];
    }
    return StatusCode::kOk;
}

#endif  // KERNELCODE_GENERATE_INCLUDE_NPU_DEMO_KERNEL_H_
