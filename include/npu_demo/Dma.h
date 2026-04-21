/*
功能说明:
- 提供 npu_demo 后端的 `alloc/slice/deslice` 轻量实现，并复用 `Memory` 的成员式 `view/reshape` 接口。

使用示例:
- #include "include/npu_demo/Dma.h"
- Status status = npu_demo::slice(tile, source, offset, size, stride);

创建者: 大闸蟹
最后修改人: 金铲铲大作战

关联文件:
- spec: spec/include/api/Dma.md
- test: test/include/api/test_dma.py
- 功能实现: include/npu_demo/Dma.h
*/

#ifndef KERNELCODE_GENERATE_INCLUDE_NPU_DEMO_DMA_H_
#define KERNELCODE_GENERATE_INCLUDE_NPU_DEMO_DMA_H_

#include <initializer_list>
#include <limits>
#include <stdexcept>

#include "include/api/Dma.h"
#include "include/npu_demo/Core.h"
#include "include/npu_demo/Memory.h"

namespace npu_demo {
namespace detail {

constexpr unsigned long long kMaxDmaRank = 8;

inline bool dma_checked_mul_non_negative(long long lhs, long long rhs, long long* out) {
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

inline bool dma_checked_add_non_negative(long long lhs, long long rhs, long long* out) {
    if (lhs < 0 || rhs < 0) {
        return false;
    }
    if (lhs > std::numeric_limits<long long>::max() - rhs) {
        return false;
    }
    *out = lhs + rhs;
    return true;
}

}  // namespace detail

/*
功能说明:
- 按给定 shape/stride 创建一块新的 `Memory<Space, T>`，供 npu_demo DMA helper 使用。
- backing storage 由 helper 在堆上分配，并按 shape/stride 复制到返回的 Memory 元信息中。

使用示例:
- Memory<TSM, float> tile = npu_demo::alloc<TSM, float>({16}, {1});

创建者: 小李飞刀
最后修改人: 小李飞刀

关联文件:
- spec: spec/include/api/Dma.md
- test: test/include/api/test_dma.py
- 功能实现: include/npu_demo/Dma.h
*/
template <MemorySpace Space, typename T>
inline Memory<Space, T> alloc(
    std::initializer_list<long long> shape,
    std::initializer_list<long long> stride,
    MemoryFormat format) {
    const unsigned long long rank = shape.size();
    if (rank == 0 || rank != stride.size() || rank > npu_demo::detail::kMaxDmaRank) {
        throw std::runtime_error("dma.alloc: invalid shape/stride");
    }

    long long shape_buf[npu_demo::detail::kMaxDmaRank] = {0};
    long long stride_buf[npu_demo::detail::kMaxDmaRank] = {0};
    long long max_linear_offset = 0;
    auto shape_it = shape.begin();
    auto stride_it = stride.begin();
    for (unsigned long long i = 0; i < rank; ++i, ++shape_it, ++stride_it) {
        if (*shape_it <= 0 || *stride_it <= 0) {
            throw std::runtime_error("dma.alloc: invalid shape/stride");
        }
        shape_buf[i] = *shape_it;
        stride_buf[i] = *stride_it;

        long long span = 0;
        if (!npu_demo::detail::dma_checked_mul_non_negative(shape_buf[i] - 1, stride_buf[i], &span)) {
            throw std::runtime_error("dma.alloc: overflow");
        }
        if (!npu_demo::detail::dma_checked_add_non_negative(max_linear_offset, span, &max_linear_offset)) {
            throw std::runtime_error("dma.alloc: overflow");
        }
    }

    long long storage_size = 0;
    if (!npu_demo::detail::dma_checked_add_non_negative(max_linear_offset, 1, &storage_size)) {
        throw std::runtime_error("dma.alloc: overflow");
    }
    T* data = new T[static_cast<unsigned long long>(storage_size)]();
    return Memory<Space, T>(data, shape_buf, stride_buf, rank, format);
}

/*
功能说明:
- 从 source 读取切片并写入预分配 target（Vector offset/size/stride 版本），支持与 source/target rank 一致的多维子集。

使用示例:
- Status status = npu_demo::slice(tile, source, offset, size, stride);

创建者: 大闸蟹
最后修改人: 金铲铲大作战

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
    if (rank == 0 || rank > npu_demo::detail::kMaxDmaRank) {
        return StatusCode::kError;
    }
    if (target.rank() != rank || offset.size() != rank || size.size() != rank || stride.size() != rank) {
        return StatusCode::kError;
    }
    if (source.data() == nullptr || target.data() == nullptr) {
        return StatusCode::kError;
    }

    long long element_count = 1;
    long long max_source_linear_offset = 0;
    long long max_target_linear_offset = 0;
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
        if (!npu_demo::detail::dma_checked_mul_non_negative(size[i] - 1, stride[i], &span)) {
            return StatusCode::kError;
        }
        long long last_index = 0;
        if (!npu_demo::detail::dma_checked_add_non_negative(offset[i], span, &last_index)) {
            return StatusCode::kError;
        }
        if (last_index >= source.get_shape(i)) {
            return StatusCode::kError;
        }
        long long source_offset_limit = 0;
        if (!npu_demo::detail::dma_checked_mul_non_negative(last_index, source.get_stride(i), &source_offset_limit)) {
            return StatusCode::kError;
        }
        if (!npu_demo::detail::dma_checked_add_non_negative(
                max_source_linear_offset, source_offset_limit, &max_source_linear_offset)) {
            return StatusCode::kError;
        }
        long long target_offset_limit = 0;
        if (!npu_demo::detail::dma_checked_mul_non_negative(
                size[i] - 1, target.get_stride(i), &target_offset_limit)) {
            return StatusCode::kError;
        }
        if (!npu_demo::detail::dma_checked_add_non_negative(
                max_target_linear_offset, target_offset_limit, &max_target_linear_offset)) {
            return StatusCode::kError;
        }
        long long next_element_count = 0;
        if (!npu_demo::detail::dma_checked_mul_non_negative(element_count, size[i], &next_element_count)) {
            return StatusCode::kError;
        }
        element_count = next_element_count;
    }

    long long logical_indices[npu_demo::detail::kMaxDmaRank] = {0};
    long long source_indices[npu_demo::detail::kMaxDmaRank] = {0};
    long long target_indices[npu_demo::detail::kMaxDmaRank] = {0};
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
            if (!npu_demo::detail::dma_checked_mul_non_negative(
                    logical_indices[dim], stride[dim], &source_delta)) {
                return StatusCode::kError;
            }
            if (!npu_demo::detail::dma_checked_add_non_negative(offset[dim], source_delta, &source_indices[dim])) {
                return StatusCode::kError;
            }
        }
        target.at(target_indices) = source.at(source_indices);
    }
    return StatusCode::kOk;
}

/*
功能说明:
- 提供 `gen_kernel/emit_c(target=npu_demo)` 使用的一维标量 `npu_demo::slice(...)` 包装，
  让生成源码可显式消费 `npu_demo::slice(target, source, offset, size, stride)`。

使用示例:
- Status status = npu_demo::slice(tile, source, 0, 16, 1);

创建者: jcc你莫辜负
最后修改人: jcc你莫辜负

关联文件:
- spec: spec/include/npu_demo/npu_demo.md
- test: test/dsl/test_gen_kernel.py
- 功能实现: include/npu_demo/Dma.h
*/
template <MemorySpace TargetSpace, MemorySpace SourceSpace, typename T>
inline Status slice(
    Memory<TargetSpace, T>& target,
    const Memory<SourceSpace, T>& source,
    long long offset,
    long long size,
    long long stride) {
    long long offset_buf[1] = {offset};
    long long size_buf[1] = {size};
    long long stride_buf[1] = {stride};
    Vector offset_vec(offset_buf, 1);
    Vector size_vec(size_buf, 1);
    Vector stride_vec(stride_buf, 1);
    return slice(target, source, offset_vec, size_vec, stride_vec);
}

/*
功能说明:
- 将 source 块写回 target 的指定区域（Vector offset/size/stride 版本），公开参数顺序固定为 `target-first`。

使用示例:
- Status status = npu_demo::deslice(target, tile, offset, size, stride);

创建者: 大闸蟹
最后修改人: 金铲铲大作战

关联文件:
- spec: spec/include/api/Dma.md
- test: test/include/api/test_dma.py
- 功能实现: include/npu_demo/Dma.h
*/
template <MemorySpace TargetSpace, MemorySpace SourceSpace, typename T>
inline Status deslice(
    Memory<TargetSpace, T>& target,
    const Memory<SourceSpace, T>& source,
    const Vector& offset,
    const Vector& size,
    const Vector& stride) {
    const unsigned long long rank = source.rank();
    if (rank == 0 || rank > npu_demo::detail::kMaxDmaRank) {
        return StatusCode::kError;
    }
    if (target.rank() != rank || offset.size() != rank || size.size() != rank || stride.size() != rank) {
        return StatusCode::kError;
    }
    if (source.data() == nullptr || target.data() == nullptr) {
        return StatusCode::kError;
    }

    long long element_count = 1;
    long long max_source_linear_offset = 0;
    long long max_target_linear_offset = 0;
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
        if (!npu_demo::detail::dma_checked_mul_non_negative(size[i] - 1, stride[i], &span)) {
            return StatusCode::kError;
        }
        long long last_index = 0;
        if (!npu_demo::detail::dma_checked_add_non_negative(offset[i], span, &last_index)) {
            return StatusCode::kError;
        }
        if (last_index >= target.get_shape(i)) {
            return StatusCode::kError;
        }
        long long source_offset_limit = 0;
        if (!npu_demo::detail::dma_checked_mul_non_negative(
                size[i] - 1, source.get_stride(i), &source_offset_limit)) {
            return StatusCode::kError;
        }
        if (!npu_demo::detail::dma_checked_add_non_negative(
                max_source_linear_offset, source_offset_limit, &max_source_linear_offset)) {
            return StatusCode::kError;
        }
        long long target_offset_limit = 0;
        if (!npu_demo::detail::dma_checked_mul_non_negative(last_index, target.get_stride(i), &target_offset_limit)) {
            return StatusCode::kError;
        }
        if (!npu_demo::detail::dma_checked_add_non_negative(
                max_target_linear_offset, target_offset_limit, &max_target_linear_offset)) {
            return StatusCode::kError;
        }
        long long next_element_count = 0;
        if (!npu_demo::detail::dma_checked_mul_non_negative(element_count, size[i], &next_element_count)) {
            return StatusCode::kError;
        }
        element_count = next_element_count;
    }

    long long logical_indices[npu_demo::detail::kMaxDmaRank] = {0};
    long long source_indices[npu_demo::detail::kMaxDmaRank] = {0};
    long long target_indices[npu_demo::detail::kMaxDmaRank] = {0};
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
            if (!npu_demo::detail::dma_checked_mul_non_negative(
                    logical_indices[dim], stride[dim], &target_delta)) {
                return StatusCode::kError;
            }
            if (!npu_demo::detail::dma_checked_add_non_negative(offset[dim], target_delta, &target_indices[dim])) {
                return StatusCode::kError;
            }
        }
        target.at(target_indices) = source.at(source_indices);
    }
    return StatusCode::kOk;
}

/*
功能说明:
- 提供 `gen_kernel/emit_c(target=npu_demo)` 使用的一维标量 `npu_demo::deslice(...)` 包装，
  让生成源码可显式消费 `npu_demo::deslice(target, source, offset, size, stride)`。

使用示例:
- Status status = npu_demo::deslice(target, tile, tid * 16, 16, 1);

创建者: jcc你莫辜负
最后修改人: jcc你莫辜负

关联文件:
- spec: spec/include/npu_demo/npu_demo.md
- test: test/dsl/test_gen_kernel.py
- 功能实现: include/npu_demo/Dma.h
*/
template <MemorySpace TargetSpace, MemorySpace SourceSpace, typename T>
inline Status deslice(
    Memory<TargetSpace, T>& target,
    const Memory<SourceSpace, T>& source,
    long long offset,
    long long size,
    long long stride) {
    long long offset_buf[1] = {offset};
    long long size_buf[1] = {size};
    long long stride_buf[1] = {stride};
    Vector offset_vec(offset_buf, 1);
    Vector size_vec(size_buf, 1);
    Vector stride_vec(stride_buf, 1);
    return deslice(target, source, offset_vec, size_vec, stride_vec);
}

}  // namespace npu_demo

#endif  // KERNELCODE_GENERATE_INCLUDE_NPU_DEMO_DMA_H_
