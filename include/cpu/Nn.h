/*
功能说明:
- 定义 cpu::Memory 的逐元素算术、比较与显式 broadcast 头文件接口。

使用示例:
- #include "include/cpu/Nn.h"
- cpu::add(A, B, C);

创建者: 神秘人
最后修改人: 朽木露琪亚

关联文件:
- spec: spec/include/cpu/cpu.md
- test: test/include/cpu/test_nn.py
- 功能实现: include/cpu/Nn.h
*/

#ifndef KERNELCODE_GENERATE_INCLUDE_CPU_NN_H_
#define KERNELCODE_GENERATE_INCLUDE_CPU_NN_H_

#include "include/cpu/Memory.h"

namespace cpu {

namespace detail {

inline void init_indices(unsigned long long rank, long long* indices) {
    for (unsigned long long i = 0; i < rank; ++i) {
        indices[i] = 0;
    }
}

inline void advance_indices(unsigned long long rank, const long long* shape, long long* indices) {
    for (unsigned long long reverse_index = 0; reverse_index < rank; ++reverse_index) {
        const unsigned long long i = rank - 1 - reverse_index;
        indices[i] += 1;
        if (indices[i] < shape[i]) {
            return;
        }
        indices[i] = 0;
    }
}

template <typename T, typename Op>
void apply_binary(const Memory<T>& lhs, const Memory<T>& rhs, Memory<T>& out, Op op) {
    long long indices[MAX_DIM];
    init_indices(out.rank(), indices);
    const long long total = out.element_count();
    for (long long linear = 0; linear < total; ++linear) {
        out.at(indices) = op(lhs.at(indices), rhs.at(indices));
        advance_indices(out.rank(), out.shape(), indices);
    }
}

template <typename T, typename PredT, typename Op>
void apply_compare(const Memory<T>& lhs, const Memory<T>& rhs, Memory<PredT>& out, Op op) {
    long long indices[MAX_DIM];
    init_indices(out.rank(), indices);
    const long long total = out.element_count();
    for (long long linear = 0; linear < total; ++linear) {
        out.at(indices) = op(lhs.at(indices), rhs.at(indices)) ? static_cast<PredT>(1)
                                                               : static_cast<PredT>(0);
        advance_indices(out.rank(), out.shape(), indices);
    }
}

}  // namespace detail

/*
功能说明:
- 逐元素加法（Memory + Memory）。

使用示例:
- cpu::add(lhs, rhs, out);

创建者: 神秘人
最后修改人: 朽木露琪亚

关联文件:
- spec: spec/include/cpu/cpu.md
- test: test/include/cpu/test_nn.py
- 功能实现: include/cpu/Nn.h
*/
template <typename T>
void add(const Memory<T>& lhs, const Memory<T>& rhs, Memory<T>& out) {
    detail::apply_binary(lhs, rhs, out, [](T a, T b) { return a + b; });
}

/*
功能说明:
- 逐元素减法。

使用示例:
- cpu::sub(lhs, rhs, out);

创建者: 神秘人
最后修改人: 朽木露琪亚

关联文件:
- spec: spec/include/cpu/cpu.md
- test: test/include/cpu/test_nn.py
- 功能实现: include/cpu/Nn.h
*/
template <typename T>
void sub(const Memory<T>& lhs, const Memory<T>& rhs, Memory<T>& out) {
    detail::apply_binary(lhs, rhs, out, [](T a, T b) { return a - b; });
}

/*
功能说明:
- 逐元素乘法。

使用示例:
- cpu::mul(lhs, rhs, out);

创建者: 神秘人
最后修改人: 朽木露琪亚

关联文件:
- spec: spec/include/cpu/cpu.md
- test: test/include/cpu/test_nn.py
- 功能实现: include/cpu/Nn.h
*/
template <typename T>
void mul(const Memory<T>& lhs, const Memory<T>& rhs, Memory<T>& out) {
    detail::apply_binary(lhs, rhs, out, [](T a, T b) { return a * b; });
}

/*
功能说明:
- 逐元素除法。

使用示例:
- cpu::truediv(lhs, rhs, out);

创建者: 神秘人
最后修改人: 朽木露琪亚

关联文件:
- spec: spec/include/cpu/cpu.md
- test: test/include/cpu/test_nn.py
- 功能实现: include/cpu/Nn.h
*/
template <typename T>
void truediv(const Memory<T>& lhs, const Memory<T>& rhs, Memory<T>& out) {
    detail::apply_binary(lhs, rhs, out, [](T a, T b) { return a / b; });
}

/*
功能说明:
- 逐元素相等比较。

使用示例:
- cpu::eq(lhs, rhs, out);

创建者: 神秘人
最后修改人: 朽木露琪亚

关联文件:
- spec: spec/include/cpu/cpu.md
- test: test/include/cpu/test_nn.py
- 功能实现: include/cpu/Nn.h
*/
template <typename T, typename PredT>
void eq(const Memory<T>& lhs, const Memory<T>& rhs, Memory<PredT>& out) {
    detail::apply_compare(lhs, rhs, out, [](T a, T b) { return a == b; });
}

/*
功能说明:
- 逐元素不等比较。

使用示例:
- cpu::ne(lhs, rhs, out);

创建者: 神秘人
最后修改人: 朽木露琪亚

关联文件:
- spec: spec/include/cpu/cpu.md
- test: test/include/cpu/test_nn.py
- 功能实现: include/cpu/Nn.h
*/
template <typename T, typename PredT>
void ne(const Memory<T>& lhs, const Memory<T>& rhs, Memory<PredT>& out) {
    detail::apply_compare(lhs, rhs, out, [](T a, T b) { return a != b; });
}

/*
功能说明:
- 逐元素小于比较。

使用示例:
- cpu::lt(lhs, rhs, out);

创建者: 神秘人
最后修改人: 朽木露琪亚

关联文件:
- spec: spec/include/cpu/cpu.md
- test: test/include/cpu/test_nn.py
- 功能实现: include/cpu/Nn.h
*/
template <typename T, typename PredT>
void lt(const Memory<T>& lhs, const Memory<T>& rhs, Memory<PredT>& out) {
    detail::apply_compare(lhs, rhs, out, [](T a, T b) { return a < b; });
}

/*
功能说明:
- 逐元素小于等于比较。

使用示例:
- cpu::le(lhs, rhs, out);

创建者: 神秘人
最后修改人: 朽木露琪亚

关联文件:
- spec: spec/include/cpu/cpu.md
- test: test/include/cpu/test_nn.py
- 功能实现: include/cpu/Nn.h
*/
template <typename T, typename PredT>
void le(const Memory<T>& lhs, const Memory<T>& rhs, Memory<PredT>& out) {
    detail::apply_compare(lhs, rhs, out, [](T a, T b) { return a <= b; });
}

/*
功能说明:
- 逐元素大于比较。

使用示例:
- cpu::gt(lhs, rhs, out);

创建者: 神秘人
最后修改人: 朽木露琪亚

关联文件:
- spec: spec/include/cpu/cpu.md
- test: test/include/cpu/test_nn.py
- 功能实现: include/cpu/Nn.h
*/
template <typename T, typename PredT>
void gt(const Memory<T>& lhs, const Memory<T>& rhs, Memory<PredT>& out) {
    detail::apply_compare(lhs, rhs, out, [](T a, T b) { return a > b; });
}

/*
功能说明:
- 逐元素大于等于比较。

使用示例:
- cpu::ge(lhs, rhs, out);

创建者: 神秘人
最后修改人: 朽木露琪亚

关联文件:
- spec: spec/include/cpu/cpu.md
- test: test/include/cpu/test_nn.py
- 功能实现: include/cpu/Nn.h
*/
template <typename T, typename PredT>
void ge(const Memory<T>& lhs, const Memory<T>& rhs, Memory<PredT>& out) {
    detail::apply_compare(lhs, rhs, out, [](T a, T b) { return a >= b; });
}

/*
功能说明:
- 显式 broadcast，将输入扩张到输出形状。

使用示例:
- cpu::broadcast(input, out);

创建者: 神秘人
最后修改人: 朽木露琪亚

关联文件:
- spec: spec/include/cpu/cpu.md
- test: test/include/cpu/test_nn.py
- 功能实现: include/cpu/Nn.h
*/
template <typename T>
void broadcast(const Memory<T>& input, Memory<T>& out) {
    long long out_indices[MAX_DIM];
    detail::init_indices(out.rank(), out_indices);
    const long long total = out.element_count();
    const unsigned long long leading = out.rank() - input.rank();
    long long in_indices[MAX_DIM];
    detail::init_indices(input.rank(), in_indices);

    for (long long linear = 0; linear < total; ++linear) {
        for (unsigned long long i = 0; i < input.rank(); ++i) {
            const unsigned long long out_dim = leading + i;
            if (input.shape()[i] == 1) {
                in_indices[i] = 0;
            } else {
                in_indices[i] = out_indices[out_dim];
            }
        }
        out.at(out_indices) = input.at(in_indices);
        detail::advance_indices(out.rank(), out.shape(), out_indices);
    }
}

}  // namespace cpu

#endif  // KERNELCODE_GENERATE_INCLUDE_CPU_NN_H_
