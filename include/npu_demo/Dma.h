/*
功能说明:
- 提供 npu_demo 后端的 view/slice/deslice 轻量实现，用于匹配 gen_kernel 骨架。

使用示例:
- #include "include/npu_demo/Dma.h"
- auto tile = view(source, 0, 16, 1);

创建者: 大闸蟹
最后修改人: jcc你莫辜负

关联文件:
- spec: spec/include/api/Dma.md
- test: test/include/api/test_dma.py
- 功能实现: include/npu_demo/Dma.h
*/

#ifndef KERNELCODE_GENERATE_INCLUDE_NPU_DEMO_DMA_H_
#define KERNELCODE_GENERATE_INCLUDE_NPU_DEMO_DMA_H_

#include <limits>
#include <stdexcept>

#include "include/api/Dma.h"
#include "include/npu_demo/Memory.h"
#include "include/npu_demo/Core.h"

namespace {

constexpr unsigned long long kMaxDmaRank = 8;

inline void contract_or_throw(bool condition, const char* message) {
    if (!condition) {
        throw std::runtime_error(message);
    }
}

inline bool checked_mul_non_negative(long long lhs, long long rhs, long long* out) {
    if (lhs < 0 || rhs < 0) {
        return false;
    }
    if (lhs == 0 || rhs == 0) {
        *out = 0;
        return true;
    }
    if (lhs > std::numeric_limits<long long>::max() / rhs) {
        return false;
    }
    *out = lhs * rhs;
    return true;
}

inline bool checked_add_non_negative(long long lhs, long long rhs, long long* out) {
    if (lhs < 0 || rhs < 0) {
        return false;
    }
    if (lhs > std::numeric_limits<long long>::max() - rhs) {
        return false;
    }
    *out = lhs + rhs;
    return true;
}

}  // namespace

/*
功能说明:
- 返回 source 的逻辑子视图（Vector offset/size/stride 版本），当前优先覆盖 1-D 子集。

使用示例:
- long long offset_buf[2] = {0, 16};
- long long size_buf[2] = {8, 8};
- long long stride_buf[2] = {1, 1};
- Vector offset(offset_buf, 2);
- Vector size(size_buf, 2);
- Vector stride(stride_buf, 2);
- auto sub = view(source, offset, size, stride);

创建者: 大闸蟹
最后修改人: jcc你莫辜负

关联文件:
- spec: spec/include/api/Dma.md
- test: test/include/api/test_dma.py
- 功能实现: include/npu_demo/Dma.h
*/
template <MemorySpace Space, typename T>
inline Memory<Space, T> view(
    const Memory<Space, T>& source,
    const Vector& offset,
    const Vector& size,
    const Vector& stride) {
    contract_or_throw(source.rank() == 1, "dma.view: unsupported rank!=1");
    contract_or_throw(offset.size() == 1, "dma.view: vector_rank_mismatch");
    contract_or_throw(size.size() == 1, "dma.view: vector_rank_mismatch");
    contract_or_throw(stride.size() == 1, "dma.view: vector_rank_mismatch");
    contract_or_throw(offset[0] >= 0, "dma.view: invalid offset/size/stride");
    contract_or_throw(size[0] > 0, "dma.view: invalid offset/size/stride");
    contract_or_throw(stride[0] > 0, "dma.view: invalid offset/size/stride");
    contract_or_throw(source.get_shape(0) > 0, "dma.view: invalid source shape");
    contract_or_throw(source.get_stride(0) > 0, "dma.view: invalid source stride");
    long long span = 0;
    contract_or_throw(
        checked_mul_non_negative(size[0] - 1, stride[0], &span),
        "dma.view: overflow"
    );
    long long last_index = 0;
    contract_or_throw(
        checked_add_non_negative(offset[0], span, &last_index),
        "dma.view: overflow"
    );
    contract_or_throw(last_index < source.get_shape(0), "dma.view: out_of_bounds");

    const unsigned long long rank = source.rank();
    long long shape_buf[kMaxDmaRank] = {0};
    long long stride_buf[kMaxDmaRank] = {0};
    long long linear_offset = 0;
    const unsigned long long offset_rank = offset.size();
    const unsigned long long size_rank = size.size();
    const unsigned long long stride_rank = stride.size();

    for (unsigned long long i = 0; i < rank; ++i) {
        const long long offset_i = i < offset_rank ? offset[i] : 0;
        const long long size_i = i < size_rank ? size[i] : source.get_shape(i);
        const long long stride_i = i < stride_rank ? stride[i] : 1;
        const long long base_stride = source.get_stride(i);
        shape_buf[i] = size_i;
        contract_or_throw(
            checked_mul_non_negative(base_stride, stride_i, &stride_buf[i]),
            "dma.view: overflow"
        );
        long long offset_delta = 0;
        contract_or_throw(
            checked_mul_non_negative(offset_i, base_stride, &offset_delta),
            "dma.view: overflow"
        );
        contract_or_throw(
            checked_add_non_negative(linear_offset, offset_delta, &linear_offset),
            "dma.view: overflow"
        );
    }

    T* data = const_cast<T*>(source.data());
    if (data != nullptr) {
        data += linear_offset;
    }
    return Memory<Space, T>(data, shape_buf, stride_buf, rank, source.format());
}

/*
功能说明:
- 从 source 读取切片并写入预分配 target（Vector offset/size/stride 版本），支持与 source/target rank 一致的多维子集。

使用示例:
- Status status = slice(tile, source, offset, size, stride);

创建者: 大闸蟹
最后修改人: jcc你莫辜负

关联文件:
- spec: spec/include/api/Dma.md
- test: test/include/api/test_dma.py
- 功能实现: include/npu_demo/Dma.h
*/
template <MemorySpace TargetSpace, MemorySpace SourceSpace, typename T>
inline Status slice(
    Memory<TargetSpace, T>& target,
    const Memory<SourceSpace, T>& source,
    const Vector& offset,
    const Vector& size,
    const Vector& stride) {
    const unsigned long long rank = source.rank();
    if (rank == 0 || rank > kMaxDmaRank) {
        return StatusCode::kError;
    }
    if (target.rank() != rank || offset.size() != rank || size.size() != rank || stride.size() != rank) {
        return StatusCode::kError;
    }
    if (source.data() == nullptr || target.data() == nullptr) {
        return StatusCode::kError;
    }

    long long element_count = 1;
    for (unsigned long long i = 0; i < rank; ++i) {
        if (offset[i] < 0 || size[i] <= 0 || stride[i] <= 0) {
            return StatusCode::kError;
        }
        if (source.get_shape(i) <= 0 || target.get_shape(i) <= 0) {
            return StatusCode::kError;
        }
        if (source.get_stride(i) <= 0 || target.get_stride(i) <= 0) {
            return StatusCode::kError;
        }
        if (target.get_shape(i) != size[i]) {
            return StatusCode::kError;
        }
        long long span = 0;
        if (!checked_mul_non_negative(size[i] - 1, stride[i], &span)) {
            return StatusCode::kError;
        }
        long long last_index = 0;
        if (!checked_add_non_negative(offset[i], span, &last_index)) {
            return StatusCode::kError;
        }
        if (last_index >= source.get_shape(i)) {
            return StatusCode::kError;
        }
        long long next_element_count = 0;
        if (!checked_mul_non_negative(element_count, size[i], &next_element_count)) {
            return StatusCode::kError;
        }
        element_count = next_element_count;
    }

    long long logical_indices[kMaxDmaRank] = {0};
    long long source_indices[kMaxDmaRank] = {0};
    long long target_indices[kMaxDmaRank] = {0};
    for (long long linear = 0; linear < element_count; ++linear) {
        long long remainder = linear;
        for (unsigned long long reverse_index = 0; reverse_index < rank; ++reverse_index) {
            const unsigned long long dim = rank - 1 - reverse_index;
            logical_indices[dim] = remainder % size[dim];
            remainder /= size[dim];
        }
        for (unsigned long long dim = 0; dim < rank; ++dim) {
            target_indices[dim] = logical_indices[dim];
            long long source_delta = 0;
            if (!checked_mul_non_negative(logical_indices[dim], stride[dim], &source_delta)) {
                return StatusCode::kError;
            }
            if (!checked_add_non_negative(offset[dim], source_delta, &source_indices[dim])) {
                return StatusCode::kError;
            }
        }
        target.at(target_indices) = source.at(source_indices);
    }
    return StatusCode::kOk;
}

/*
功能说明:
- 将 source 块写回 target 的指定区域（Vector offset/size/stride 版本），支持与 source/target rank 一致的多维子集。

使用示例:
- Status status = deslice(tile, target, offset, size, stride);

创建者: 大闸蟹
最后修改人: jcc你莫辜负

关联文件:
- spec: spec/include/api/Dma.md
- test: test/include/api/test_dma.py
- 功能实现: include/npu_demo/Dma.h
*/
template <MemorySpace SourceSpace, MemorySpace TargetSpace, typename T>
inline Status deslice(
    const Memory<SourceSpace, T>& source,
    Memory<TargetSpace, T>& target,
    const Vector& offset,
    const Vector& size,
    const Vector& stride) {
    const unsigned long long rank = source.rank();
    if (rank == 0 || rank > kMaxDmaRank) {
        return StatusCode::kError;
    }
    if (target.rank() != rank || offset.size() != rank || size.size() != rank || stride.size() != rank) {
        return StatusCode::kError;
    }
    if (source.data() == nullptr || target.data() == nullptr) {
        return StatusCode::kError;
    }

    long long element_count = 1;
    for (unsigned long long i = 0; i < rank; ++i) {
        if (offset[i] < 0 || size[i] <= 0 || stride[i] <= 0) {
            return StatusCode::kError;
        }
        if (source.get_shape(i) <= 0 || target.get_shape(i) <= 0) {
            return StatusCode::kError;
        }
        if (source.get_stride(i) <= 0 || target.get_stride(i) <= 0) {
            return StatusCode::kError;
        }
        if (source.get_shape(i) != size[i]) {
            return StatusCode::kError;
        }
        long long span = 0;
        if (!checked_mul_non_negative(size[i] - 1, stride[i], &span)) {
            return StatusCode::kError;
        }
        long long last_index = 0;
        if (!checked_add_non_negative(offset[i], span, &last_index)) {
            return StatusCode::kError;
        }
        if (last_index >= target.get_shape(i)) {
            return StatusCode::kError;
        }
        long long next_element_count = 0;
        if (!checked_mul_non_negative(element_count, size[i], &next_element_count)) {
            return StatusCode::kError;
        }
        element_count = next_element_count;
    }

    long long logical_indices[kMaxDmaRank] = {0};
    long long source_indices[kMaxDmaRank] = {0};
    long long target_indices[kMaxDmaRank] = {0};
    for (long long linear = 0; linear < element_count; ++linear) {
        long long remainder = linear;
        for (unsigned long long reverse_index = 0; reverse_index < rank; ++reverse_index) {
            const unsigned long long dim = rank - 1 - reverse_index;
            logical_indices[dim] = remainder % size[dim];
            remainder /= size[dim];
        }
        for (unsigned long long dim = 0; dim < rank; ++dim) {
            source_indices[dim] = logical_indices[dim];
            long long target_delta = 0;
            if (!checked_mul_non_negative(logical_indices[dim], stride[dim], &target_delta)) {
                return StatusCode::kError;
            }
            if (!checked_add_non_negative(offset[dim], target_delta, &target_indices[dim])) {
                return StatusCode::kError;
            }
        }
        target.at(target_indices) = source.at(source_indices);
    }
    return StatusCode::kOk;
}

/*
功能说明:
- 返回 source 的逻辑子视图（标量 offset/size/stride 版本），当前优先覆盖 1-D 子集。

使用示例:
- auto sub = view(source, 0, 16, 1);

创建者: 大闸蟹
最后修改人: jcc你莫辜负

关联文件:
- spec: spec/include/api/Dma.md
- test: test/include/api/test_dma.py
- 功能实现: include/npu_demo/Dma.h
*/
template <MemorySpace Space, typename T>
inline Memory<Space, T> view(
    const Memory<Space, T>& source,
    long long offset,
    long long size,
    long long stride) {
    contract_or_throw(source.rank() == 1, "dma.view: unsupported rank!=1");
    contract_or_throw(offset >= 0, "dma.view: invalid offset/size/stride");
    contract_or_throw(size > 0, "dma.view: invalid offset/size/stride");
    contract_or_throw(stride > 0, "dma.view: invalid offset/size/stride");
    contract_or_throw(source.get_shape(0) > 0, "dma.view: invalid source shape");
    contract_or_throw(source.get_stride(0) > 0, "dma.view: invalid source stride");
    long long span = 0;
    contract_or_throw(checked_mul_non_negative(size - 1, stride, &span), "dma.view: overflow");
    long long last_index = 0;
    contract_or_throw(checked_add_non_negative(offset, span, &last_index), "dma.view: overflow");
    contract_or_throw(last_index < source.get_shape(0), "dma.view: out_of_bounds");

    long long shape[1] = {size};
    long long strides[1] = {0};
    contract_or_throw(
        checked_mul_non_negative(source.get_stride(0), stride, &strides[0]),
        "dma.view: overflow"
    );
    T* data = const_cast<T*>(source.data());
    if (data != nullptr) {
        long long linear_offset = 0;
        contract_or_throw(
            checked_mul_non_negative(offset, source.get_stride(0), &linear_offset),
            "dma.view: overflow"
        );
        data += linear_offset;
    }
    return Memory<Space, T>(data, shape, strides, 1, source.format());
}

/*
功能说明:
- 从 source 读取切片并写入预分配 target（标量 offset/size/stride 版本），当前优先覆盖 1-D 子集。

使用示例:
- Status status = slice(tile, source, 0, 16, 1);

创建者: 大闸蟹
最后修改人: jcc你莫辜负

关联文件:
- spec: spec/include/api/Dma.md
- test: test/include/api/test_dma.py
- 功能实现: include/npu_demo/Dma.h
*/
template <MemorySpace TargetSpace, MemorySpace SourceSpace, typename T>
inline Status slice(
    Memory<TargetSpace, T>& target,
    const Memory<SourceSpace, T>& source,
    long long offset,
    long long size,
    long long stride) {
    if (source.rank() != 1 || target.rank() != 1) {
        return StatusCode::kError;
    }
    if (offset < 0 || size <= 0 || stride <= 0) {
        return StatusCode::kError;
    }
    if (source.get_shape(0) <= 0 || target.get_shape(0) <= 0) {
        return StatusCode::kError;
    }
    if (source.get_stride(0) <= 0 || target.get_stride(0) <= 0) {
        return StatusCode::kError;
    }
    if (target.get_shape(0) != size) {
        return StatusCode::kError;
    }
    long long span = 0;
    if (!checked_mul_non_negative(size - 1, stride, &span)) {
        return StatusCode::kError;
    }
    long long last_index = 0;
    if (!checked_add_non_negative(offset, span, &last_index)) {
        return StatusCode::kError;
    }
    if (last_index >= source.get_shape(0)) {
        return StatusCode::kError;
    }
    const T* source_data = source.data();
    T* target_data = target.data();
    if (source_data == nullptr || target_data == nullptr) {
        return StatusCode::kError;
    }
    const long long source_stride = source.get_stride(0);
    const long long target_stride = target.get_stride(0);
    long long base = 0;
    if (!checked_mul_non_negative(offset, source_stride, &base)) {
        return StatusCode::kError;
    }
    long long step = 0;
    if (!checked_mul_non_negative(stride, source_stride, &step)) {
        return StatusCode::kError;
    }
    long long max_step = 0;
    if (!checked_mul_non_negative(size - 1, step, &max_step)) {
        return StatusCode::kError;
    }
    long long max_index = 0;
    if (!checked_add_non_negative(base, max_step, &max_index)) {
        return StatusCode::kError;
    }
    long long max_target_offset = 0;
    if (!checked_mul_non_negative(size - 1, target_stride, &max_target_offset)) {
        return StatusCode::kError;
    }
    for (long long i = 0; i < size; ++i) {
        target_data[i * target_stride] = source_data[base + i * step];
    }
    return StatusCode::kOk;
}

/*
功能说明:
- 将 source 块写回 target 的指定区域（标量 offset/size/stride 版本），当前优先覆盖 1-D 子集。

使用示例:
- Status status = deslice(tile, target, 0, 16, 1);

创建者: 大闸蟹
最后修改人: jcc你莫辜负

关联文件:
- spec: spec/include/api/Dma.md
- test: test/include/api/test_dma.py
- 功能实现: include/npu_demo/Dma.h
*/
template <MemorySpace SourceSpace, MemorySpace TargetSpace, typename T>
inline Status deslice(
    const Memory<SourceSpace, T>& source,
    Memory<TargetSpace, T>& target,
    long long offset,
    long long size,
    long long stride) {
    if (source.rank() != 1 || target.rank() != 1) {
        return StatusCode::kError;
    }
    if (offset < 0 || size <= 0 || stride <= 0) {
        return StatusCode::kError;
    }
    if (source.get_shape(0) <= 0 || target.get_shape(0) <= 0) {
        return StatusCode::kError;
    }
    if (source.get_stride(0) <= 0 || target.get_stride(0) <= 0) {
        return StatusCode::kError;
    }
    if (source.get_shape(0) != size) {
        return StatusCode::kError;
    }
    long long span = 0;
    if (!checked_mul_non_negative(size - 1, stride, &span)) {
        return StatusCode::kError;
    }
    long long last_index = 0;
    if (!checked_add_non_negative(offset, span, &last_index)) {
        return StatusCode::kError;
    }
    if (last_index >= target.get_shape(0)) {
        return StatusCode::kError;
    }
    const T* source_data = source.data();
    T* target_data = target.data();
    if (source_data == nullptr || target_data == nullptr) {
        return StatusCode::kError;
    }
    const long long source_stride = source.get_stride(0);
    const long long target_stride = target.get_stride(0);
    long long base = 0;
    if (!checked_mul_non_negative(offset, target_stride, &base)) {
        return StatusCode::kError;
    }
    long long step = 0;
    if (!checked_mul_non_negative(stride, target_stride, &step)) {
        return StatusCode::kError;
    }
    long long max_step = 0;
    if (!checked_mul_non_negative(size - 1, step, &max_step)) {
        return StatusCode::kError;
    }
    long long max_index = 0;
    if (!checked_add_non_negative(base, max_step, &max_index)) {
        return StatusCode::kError;
    }
    long long max_source_offset = 0;
    if (!checked_mul_non_negative(size - 1, source_stride, &max_source_offset)) {
        return StatusCode::kError;
    }
    for (long long i = 0; i < size; ++i) {
        target_data[base + i * step] = source_data[i * source_stride];
    }
    return StatusCode::kOk;
}

#endif  // KERNELCODE_GENERATE_INCLUDE_NPU_DEMO_DMA_H_
