/*
功能说明:
- 定义 cpu::Memory 的逐元素算术、比较、显式 broadcast 与 img2col 头文件接口。

使用示例:
- #include "include/cpu/Nn.h"
- cpu::add(A, B, C);

创建者: 神秘人
最后修改人: 金铲铲大作战

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

/*
功能说明:
- 将多维索引数组初始化为全 0。

使用示例:
- long long indices[MAX_DIM];
- cpu::detail::init_indices(3, indices);

创建者: 小李飞刀
最后修改人: 小李飞刀

关联文件:
- spec: spec/include/cpu/cpu.md
- test: test/include/cpu/test_nn.py
- 功能实现: include/cpu/Nn.h
*/
inline void init_indices(unsigned long long rank, long long* indices) {
    for (unsigned long long i = 0; i < rank; ++i) {
        indices[i] = 0;
    }
}

/*
功能说明:
- 按行主序递增多维索引。

使用示例:
- cpu::detail::advance_indices(rank, shape, indices);

创建者: 小李飞刀
最后修改人: 小李飞刀

关联文件:
- spec: spec/include/cpu/cpu.md
- test: test/include/cpu/test_nn.py
- 功能实现: include/cpu/Nn.h
*/
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

/*
功能说明:
- 在契约不满足时直接终止，用于无异常 CPU 头文件前置条件检查。

使用示例:
- cpu::detail::contract_or_trap(rank == 3);

创建者: 小李飞刀
最后修改人: 小李飞刀

关联文件:
- spec: spec/include/cpu/cpu.md
- test: test/include/cpu/test_nn.py
- 功能实现: include/cpu/Nn.h
*/
inline void contract_or_trap(bool condition) {
    if (!condition) {
#if defined(__clang__) || defined(__GNUC__)
        __builtin_trap();
#else
        *(volatile int*)0 = 0;
#endif
    }
}

/*
功能说明:
- 判断 Memory 是否满足给定 rank 的连续行主序布局。

使用示例:
- bool ok = cpu::detail::has_contiguous_rank(mem, 3);

创建者: 小李飞刀
最后修改人: 小李飞刀

关联文件:
- spec: spec/include/cpu/cpu.md
- test: test/include/cpu/test_nn.py
- 功能实现: include/cpu/Nn.h
*/
template <typename T>
bool has_contiguous_rank(const Memory<T>& mem, unsigned long long expected_rank) {
    return mem.rank() == expected_rank && mem.is_contiguous();
}

/*
功能说明:
- 计算 1D img2col 的输出宽度。

使用示例:
- long long wo = cpu::detail::compute_img2col1d_output_width(width, 3, 1, 1, 1, 1);

创建者: 小李飞刀
最后修改人: 小李飞刀

关联文件:
- spec: spec/include/cpu/cpu.md
- test: test/include/cpu/test_nn.py
- 功能实现: include/cpu/Nn.h
*/
inline long long compute_img2col1d_output_width(
    long long width,
    long long kw,
    long long sw,
    long long dw,
    long long pl,
    long long pr) {
    return (width + pl + pr - dw * (kw - 1) - 1) / sw + 1;
}

/*
功能说明:
- 校验 1D img2col 的 rank、shape 与 stride 前置条件。

使用示例:
- cpu::detail::verify_img2col1d_contract(value, out, 3, 1, 1, 1, 1);

创建者: 小李飞刀
最后修改人: 小李飞刀

关联文件:
- spec: spec/include/cpu/cpu.md
- test: test/include/cpu/test_nn.py
- 功能实现: include/cpu/Nn.h
*/
template <typename T>
void verify_img2col1d_contract(
    const Memory<T>& value,
    const Memory<T>& out,
    long long kw,
    long long sw,
    long long dw,
    long long pl,
    long long pr) {
    contract_or_trap(kw > 0);
    contract_or_trap(sw > 0);
    contract_or_trap(dw > 0);
    contract_or_trap(pl >= 0);
    contract_or_trap(pr >= 0);
    contract_or_trap(has_contiguous_rank(value, 3));
    contract_or_trap(has_contiguous_rank(out, 3));

    const long long n = value.shape()[0];
    const long long c = value.shape()[1];
    const long long width = value.shape()[2];
    const long long wo = compute_img2col1d_output_width(width, kw, sw, dw, pl, pr);

    contract_or_trap(wo > 0);
    contract_or_trap(out.shape()[0] == n);
    contract_or_trap(out.shape()[1] == c * kw);
    contract_or_trap(out.shape()[2] == wo);
}

/*
功能说明:
- 计算 2D img2col 的输出高度或宽度。

使用示例:
- long long ho = cpu::detail::compute_img2col2d_output_extent(height, 3, 1, 1, 1, 1);

创建者: 小李飞刀
最后修改人: 小李飞刀

关联文件:
- spec: spec/include/cpu/cpu.md
- test: test/include/cpu/test_nn.py
- 功能实现: include/cpu/Nn.h
*/
inline long long compute_img2col2d_output_extent(
    long long extent,
    long long kernel,
    long long stride,
    long long dilation,
    long long pad_before,
    long long pad_after) {
    return (extent + pad_before + pad_after - dilation * (kernel - 1) - 1) / stride + 1;
}

/*
功能说明:
- 校验 2D img2col 的 rank、shape 与 stride 前置条件。

使用示例:
- cpu::detail::verify_img2col2d_contract(value, out, kh, kw, sh, sw, dh, dw, ph, pw, pl, pr);

创建者: 小李飞刀
最后修改人: 小李飞刀

关联文件:
- spec: spec/include/cpu/cpu.md
- test: test/include/cpu/test_nn.py
- 功能实现: include/cpu/Nn.h
*/
template <typename T>
void verify_img2col2d_contract(
    const Memory<T>& value,
    const Memory<T>& out,
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
    contract_or_trap(kh > 0);
    contract_or_trap(kw > 0);
    contract_or_trap(sh > 0);
    contract_or_trap(sw > 0);
    contract_or_trap(dh > 0);
    contract_or_trap(dw > 0);
    contract_or_trap(ph >= 0);
    contract_or_trap(pw >= 0);
    contract_or_trap(pl >= 0);
    contract_or_trap(pr >= 0);
    contract_or_trap(has_contiguous_rank(value, 4));
    contract_or_trap(has_contiguous_rank(out, 3));

    const long long n = value.shape()[0];
    const long long c = value.shape()[1];
    const long long height = value.shape()[2];
    const long long width = value.shape()[3];
    const long long ho = compute_img2col2d_output_extent(height, kh, sh, dh, ph, pw);
    const long long wo = compute_img2col2d_output_extent(width, kw, sw, dw, pl, pr);

    contract_or_trap(ho > 0);
    contract_or_trap(wo > 0);
    contract_or_trap(out.shape()[0] == n);
    contract_or_trap(out.shape()[1] == c * kh * kw);
    contract_or_trap(out.shape()[2] == ho * wo);
}

/*
功能说明:
- 统一执行逐元素二元算子。

使用示例:
- cpu::detail::apply_binary(lhs, rhs, out, [](float a, float b) { return a + b; });

创建者: 小李飞刀
最后修改人: 小李飞刀

关联文件:
- spec: spec/include/cpu/cpu.md
- test: test/include/cpu/test_nn.py
- 功能实现: include/cpu/Nn.h
*/
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

/*
功能说明:
- 统一执行逐元素二元算子（Memory + scalar）。

使用示例:
- cpu::detail::apply_binary_scalar_rhs(lhs, 3.0f, out, [](float a, float b) { return a + b; });

创建者: 金铲铲大作战
最后修改人: 金铲铲大作战

关联文件:
- spec: spec/include/cpu/cpu.md
- test: test/include/cpu/test_nn.py
- 功能实现: include/cpu/Nn.h
*/
template <typename T, typename Op>
void apply_binary_scalar_rhs(const Memory<T>& lhs, T rhs_scalar, Memory<T>& out, Op op) {
    long long indices[MAX_DIM];
    init_indices(out.rank(), indices);
    const long long total = out.element_count();
    for (long long linear = 0; linear < total; ++linear) {
        out.at(indices) = op(lhs.at(indices), rhs_scalar);
        advance_indices(out.rank(), out.shape(), indices);
    }
}

/*
功能说明:
- 统一执行逐元素二元算子（scalar + Memory）。

使用示例:
- cpu::detail::apply_binary_scalar_lhs(3.0f, rhs, out, [](float a, float b) { return a + b; });

创建者: 金铲铲大作战
最后修改人: 金铲铲大作战

关联文件:
- spec: spec/include/cpu/cpu.md
- test: test/include/cpu/test_nn.py
- 功能实现: include/cpu/Nn.h
*/
template <typename T, typename Op>
void apply_binary_scalar_lhs(T lhs_scalar, const Memory<T>& rhs, Memory<T>& out, Op op) {
    long long indices[MAX_DIM];
    init_indices(out.rank(), indices);
    const long long total = out.element_count();
    for (long long linear = 0; linear < total; ++linear) {
        out.at(indices) = op(lhs_scalar, rhs.at(indices));
        advance_indices(out.rank(), out.shape(), indices);
    }
}

/*
功能说明:
- 统一执行逐元素比较算子，并把结果写成 predicate 数值。

使用示例:
- cpu::detail::apply_compare(lhs, rhs, out, [](float a, float b) { return a < b; });

创建者: 小李飞刀
最后修改人: 小李飞刀

关联文件:
- spec: spec/include/cpu/cpu.md
- test: test/include/cpu/test_nn.py
- 功能实现: include/cpu/Nn.h
*/
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

/*
功能说明:
- 统一执行 float 归约算子，并校验 axes/keepdim/out 连续性等契约。

使用示例:
- cpu::detail::reduce_impl(value, out, axes, 1, false,
  [](float a, float b) { return a + b; }, 0.0f, false, false);

创建者: 金铲铲大作战
最后修改人: 金铲铲大作战

关联文件:
- spec: spec/include/cpu/cpu.md
- test: test/include/cpu/test_nn.py
- 功能实现: include/cpu/Nn.h
*/
template <typename Op>
void reduce_impl(
    const Memory<float>& value,
    Memory<float>& out,
    const long long* axes,
    unsigned long long axes_rank,
    bool keepdim,
    Op op,
    float init_value,
    bool init_with_first,
    bool require_non_empty) {
    const unsigned long long rank = value.rank();
    contract_or_trap(axes != 0);
    contract_or_trap(axes_rank > 0);
    contract_or_trap(axes_rank <= rank);

    bool reduce_axis[MAX_DIM] = {false};
    for (unsigned long long i = 0; i < axes_rank; ++i) {
        const long long axis = axes[i];
        contract_or_trap(axis >= 0);
        contract_or_trap(static_cast<unsigned long long>(axis) < rank);
        if (i > 0) {
            contract_or_trap(axis > axes[i - 1]);
        }
        reduce_axis[axis] = true;
    }

    unsigned long long non_reduce_rank = 0;
    unsigned long long non_reduce_axes[MAX_DIM] = {0};
    for (unsigned long long i = 0; i < rank; ++i) {
        if (!reduce_axis[i]) {
            non_reduce_axes[non_reduce_rank] = i;
            non_reduce_rank += 1;
        }
    }

    if (keepdim) {
        contract_or_trap(out.rank() == rank);
        for (unsigned long long i = 0; i < rank; ++i) {
            if (reduce_axis[i]) {
                contract_or_trap(out.shape()[i] == 1);
            } else {
                contract_or_trap(out.shape()[i] == value.shape()[i]);
            }
        }
    } else {
        if (axes_rank == rank) {
            contract_or_trap(out.rank() == 1);
            contract_or_trap(out.shape()[0] == 1);
        } else {
            contract_or_trap(out.rank() == non_reduce_rank);
            for (unsigned long long i = 0; i < non_reduce_rank; ++i) {
                contract_or_trap(out.shape()[i] == value.shape()[non_reduce_axes[i]]);
            }
        }
    }
    contract_or_trap(out.is_contiguous());

    if (require_non_empty) {
        for (unsigned long long i = 0; i < axes_rank; ++i) {
            contract_or_trap(value.shape()[axes[i]] > 0);
        }
    }

    long long reduce_shape[MAX_DIM] = {0};
    long long reduce_total = 1;
    for (unsigned long long i = 0; i < axes_rank; ++i) {
        reduce_shape[i] = value.shape()[axes[i]];
        reduce_total *= reduce_shape[i];
    }

    long long out_indices[MAX_DIM];
    long long in_indices[MAX_DIM];
    long long reduce_indices[MAX_DIM];
    init_indices(out.rank(), out_indices);
    const long long out_total = out.element_count();
    for (long long linear = 0; linear < out_total; ++linear) {
        for (unsigned long long dim = 0; dim < rank; ++dim) {
            in_indices[dim] = 0;
        }
        if (keepdim) {
            for (unsigned long long dim = 0; dim < rank; ++dim) {
                if (!reduce_axis[dim]) {
                    in_indices[dim] = out_indices[dim];
                }
            }
        } else {
            for (unsigned long long i = 0; i < non_reduce_rank; ++i) {
                in_indices[non_reduce_axes[i]] = out_indices[i];
            }
        }

        if (init_with_first) {
            bool first = true;
            init_indices(axes_rank, reduce_indices);
            for (long long r = 0; r < reduce_total; ++r) {
                for (unsigned long long i = 0; i < axes_rank; ++i) {
                    in_indices[axes[i]] = reduce_indices[i];
                }
                const float v = value.at(in_indices);
                if (first) {
                    out.at(out_indices) = v;
                    first = false;
                } else {
                    out.at(out_indices) = op(out.at(out_indices), v);
                }
                advance_indices(axes_rank, reduce_shape, reduce_indices);
            }
            if (first) {
                out.at(out_indices) = init_value;
            }
        } else {
            out.at(out_indices) = init_value;
            init_indices(axes_rank, reduce_indices);
            for (long long r = 0; r < reduce_total; ++r) {
                for (unsigned long long i = 0; i < axes_rank; ++i) {
                    in_indices[axes[i]] = reduce_indices[i];
                }
                out.at(out_indices) = op(out.at(out_indices), value.at(in_indices));
                advance_indices(axes_rank, reduce_shape, reduce_indices);
            }
        }
        advance_indices(out.rank(), out.shape(), out_indices);
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
- 逐元素加法（Memory + scalar）。

使用示例:
- cpu::add(lhs, 3.0f, out);

创建者: 金铲铲大作战
最后修改人: 金铲铲大作战

关联文件:
- spec: spec/include/cpu/cpu.md
- test: test/include/cpu/test_nn.py
- 功能实现: include/cpu/Nn.h
*/
template <typename T>
void add(const Memory<T>& lhs, T rhs_scalar, Memory<T>& out) {
    detail::apply_binary_scalar_rhs(lhs, rhs_scalar, out, [](T a, T b) { return a + b; });
}

/*
功能说明:
- 逐元素加法（scalar + Memory）。

使用示例:
- cpu::add(3.0f, rhs, out);

创建者: 金铲铲大作战
最后修改人: 金铲铲大作战

关联文件:
- spec: spec/include/cpu/cpu.md
- test: test/include/cpu/test_nn.py
- 功能实现: include/cpu/Nn.h
*/
template <typename T>
void add(T lhs_scalar, const Memory<T>& rhs, Memory<T>& out) {
    detail::apply_binary_scalar_lhs(lhs_scalar, rhs, out, [](T a, T b) { return a + b; });
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
- 对输入视图执行逐元素指数运算。

使用示例:
- cpu::exp(value, out);

创建者: 金铲铲大作战
最后修改人: 金铲铲大作战

关联文件:
- spec: spec/include/cpu/cpu.md
- test: test/include/cpu/test_nn.py
- 功能实现: include/cpu/Nn.h
*/
void exp(const Memory<float>& value, Memory<float>& out) {
    detail::contract_or_trap(value.rank() == out.rank());
    for (unsigned long long i = 0; i < value.rank(); ++i) {
        detail::contract_or_trap(value.shape()[i] == out.shape()[i]);
        detail::contract_or_trap(value.stride()[i] == out.stride()[i]);
    }

    long long indices[MAX_DIM];
    detail::init_indices(out.rank(), indices);
    const long long total = out.element_count();
    for (long long linear = 0; linear < total; ++linear) {
#if defined(__clang__) || defined(__GNUC__)
        out.at(indices) = __builtin_expf(value.at(indices));
#else
        const float x = value.at(indices);
        float term = 1.0f;
        float sum = 1.0f;
        for (int i = 1; i <= 6; ++i) {
            term *= x / static_cast<float>(i);
            sum += term;
        }
        out.at(indices) = sum;
#endif
        detail::advance_indices(out.rank(), out.shape(), indices);
    }
}

/*
功能说明:
- 按给定轴集合执行求和归约。

使用示例:
- cpu::reduce_sum(value, out, axes, 2, false);

创建者: 金铲铲大作战
最后修改人: 金铲铲大作战

关联文件:
- spec: spec/include/cpu/cpu.md
- test: test/include/cpu/test_nn.py
- 功能实现: include/cpu/Nn.h
*/
void reduce_sum(
    const Memory<float>& value,
    Memory<float>& out,
    const long long* axes,
    unsigned long long axes_rank,
    bool keepdim) {
    detail::reduce_impl(
        value,
        out,
        axes,
        axes_rank,
        keepdim,
        [](float a, float b) { return a + b; },
        0.0f,
        false,
        false);
}

/*
功能说明:
- 按给定轴集合执行最小值归约。

使用示例:
- cpu::reduce_min(value, out, axes, 1, false);

创建者: 金铲铲大作战
最后修改人: 金铲铲大作战

关联文件:
- spec: spec/include/cpu/cpu.md
- test: test/include/cpu/test_nn.py
- 功能实现: include/cpu/Nn.h
*/
void reduce_min(
    const Memory<float>& value,
    Memory<float>& out,
    const long long* axes,
    unsigned long long axes_rank,
    bool keepdim) {
    detail::reduce_impl(
        value,
        out,
        axes,
        axes_rank,
        keepdim,
        [](float a, float b) { return a < b ? a : b; },
        0.0f,
        true,
        true);
}

/*
功能说明:
- 按给定轴集合执行最大值归约。

使用示例:
- cpu::reduce_max(value, out, axes, 1, true);

创建者: 金铲铲大作战
最后修改人: 金铲铲大作战

关联文件:
- spec: spec/include/cpu/cpu.md
- test: test/include/cpu/test_nn.py
- 功能实现: include/cpu/Nn.h
*/
void reduce_max(
    const Memory<float>& value,
    Memory<float>& out,
    const long long* axes,
    unsigned long long axes_rank,
    bool keepdim) {
    detail::reduce_impl(
        value,
        out,
        axes,
        axes_rank,
        keepdim,
        [](float a, float b) { return a > b ? a : b; },
        0.0f,
        true,
        true);
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

/*
功能说明:
- 将 rank-3 输入视图 `[N, C, W]` 按 1D img2col 规则展开到 `[N, C * kw, Wo]`。

使用示例:
- cpu::img2col1d(value, out, 3, 1, 1, 1, 1);

创建者: 小李飞刀
最后修改人: 小李飞刀

关联文件:
- spec: spec/include/cpu/cpu.md
- test: test/include/cpu/test_nn.py
- 功能实现: include/cpu/Nn.h
*/
void img2col1d(
    const Memory<float>& value,
    Memory<float>& out,
    long long kw,
    long long sw,
    long long dw,
    long long pl,
    long long pr) {
    detail::verify_img2col1d_contract(value, out, kw, sw, dw, pl, pr);

    const long long n = value.shape()[0];
    const long long c = value.shape()[1];
    const long long width = value.shape()[2];
    const long long wo = out.shape()[2];
    const float zero = 0.0f;
    long long value_indices[3] = {0, 0, 0};
    long long out_indices[3] = {0, 0, 0};

    for (long long batch = 0; batch < n; ++batch) {
        for (long long channel = 0; channel < c; ++channel) {
            for (long long kernel_w = 0; kernel_w < kw; ++kernel_w) {
                const long long out_channel = channel * kw + kernel_w;
                for (long long out_w = 0; out_w < wo; ++out_w) {
                    const long long in_w = out_w * sw + kernel_w * dw - pl;
                    out_indices[0] = batch;
                    out_indices[1] = out_channel;
                    out_indices[2] = out_w;
                    if (in_w < 0 || in_w >= width) {
                        out.at(out_indices) = zero;
                        continue;
                    }
                    value_indices[0] = batch;
                    value_indices[1] = channel;
                    value_indices[2] = in_w;
                    out.at(out_indices) = value.at(value_indices);
                }
            }
        }
    }
}

/*
功能说明:
- 将 rank-4 输入视图 `[N, C, H, W]` 按 2D img2col 规则展开到 `[N, C * kh * kw, Ho * Wo]`。

使用示例:
- cpu::img2col2d(value, out, kh, kw, sh, sw, dh, dw, ph, pw, pl, pr);

创建者: 小李飞刀
最后修改人: 小李飞刀

关联文件:
- spec: spec/include/cpu/cpu.md
- test: test/include/cpu/test_nn.py
- 功能实现: include/cpu/Nn.h
*/
void img2col2d(
    const Memory<float>& value,
    Memory<float>& out,
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
    detail::verify_img2col2d_contract(value, out, kh, kw, sh, sw, dh, dw, ph, pw, pl, pr);

    const long long n = value.shape()[0];
    const long long c = value.shape()[1];
    const long long height = value.shape()[2];
    const long long width = value.shape()[3];
    const long long ho = detail::compute_img2col2d_output_extent(height, kh, sh, dh, ph, pw);
    const long long wo = detail::compute_img2col2d_output_extent(width, kw, sw, dw, pl, pr);
    const float zero = 0.0f;
    long long value_indices[4] = {0, 0, 0, 0};
    long long out_indices[3] = {0, 0, 0};

    for (long long batch = 0; batch < n; ++batch) {
        for (long long channel = 0; channel < c; ++channel) {
            for (long long kernel_h = 0; kernel_h < kh; ++kernel_h) {
                for (long long kernel_w = 0; kernel_w < kw; ++kernel_w) {
                    const long long out_channel = channel * kh * kw + kernel_h * kw + kernel_w;
                    for (long long out_h = 0; out_h < ho; ++out_h) {
                        const long long in_h = out_h * sh + kernel_h * dh - ph;
                        for (long long out_w = 0; out_w < wo; ++out_w) {
                            const long long in_w = out_w * sw + kernel_w * dw - pl;
                            out_indices[0] = batch;
                            out_indices[1] = out_channel;
                            out_indices[2] = out_h * wo + out_w;
                            if (in_h < 0 || in_h >= height || in_w < 0 || in_w >= width) {
                                out.at(out_indices) = zero;
                                continue;
                            }
                            value_indices[0] = batch;
                            value_indices[1] = channel;
                            value_indices[2] = in_h;
                            value_indices[3] = in_w;
                            out.at(out_indices) = value.at(value_indices);
                        }
                    }
                }
            }
        }
    }
}

}  // namespace cpu

#endif  // KERNELCODE_GENERATE_INCLUDE_CPU_NN_H_
