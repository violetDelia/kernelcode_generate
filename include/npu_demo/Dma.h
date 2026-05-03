/*
功能说明:
- 提供 npu_demo 后端的 `alloc/fill/slice/deslice/transpose/broadcast` 轻量实现，并复用 `Memory` 的成员式 `view/reshape` 接口。

API 列表:
- `npu_demo::alloc<Space, T>(std::initializer_list<long long> shape, std::initializer_list<long long> stride, MemoryFormat format = MemoryFormat::Norm) -> Memory<Space, T>`
- `npu_demo::fill<Space, T>(Memory<Space, T>& target, const T& value) -> Status`
- `npu_demo::slice<TargetSpace, SourceSpace, T>(Memory<TargetSpace, T>& target, const Memory<SourceSpace, T>& source, const Vector& offset, const Vector& size, const Vector& stride) -> Status`
- `npu_demo::deslice<TargetSpace, SourceSpace, T>(Memory<TargetSpace, T>& target, const Memory<SourceSpace, T>& source, const Vector& offset, const Vector& size, const Vector& stride) -> Status`
- `npu_demo::transpose<TargetSpace, SourceSpace, TargetType, SourceType>(Memory<TargetSpace, TargetType>& target, const Memory<SourceSpace, SourceType>& source, const Vector& perm) -> Status`
- `npu_demo::broadcast<TargetSpace, SourceSpace, TargetType, SourceType>(Memory<TargetSpace, TargetType>& target, const Memory<SourceSpace, SourceType>& source) -> Status`

使用示例:
- #include "include/npu_demo/Dma.h"
- Status status = npu_demo::slice(tile, source, offset, size, stride);


关联文件:
- spec: spec/include/api/Dma.md
- test: test/include/api/dma.py
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


关联文件:
- spec: spec/include/api/Dma.md
- test: test/include/api/dma.py
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
- 使用标量值填充 `target` 的全部逻辑元素。
- 支持非连续 stride；填充范围按 shape 逻辑坐标遍历。

使用示例:
- Status status = npu_demo::fill<TSM, float>(target, 0.0f);


关联文件:
- spec: spec/include/api/Dma.md
- test: test/include/api/dma.py
- 功能实现: include/npu_demo/Dma.h
*/
template <MemorySpace Space, typename T>
inline Status fill(Memory<Space, T>& target, const T& value) {
    const unsigned long long rank = target.rank();
    if (rank == 0 || rank > npu_demo::detail::kMaxDmaRank || target.data() == nullptr) {
        return StatusCode::kError;
    }
    long long element_count = 1;
    for (unsigned long long axis = 0; axis < rank; ++axis) {
        if (target.get_shape(axis) <= 0 || target.get_stride(axis) <= 0) {
            return StatusCode::kError;
        }
        long long next_element_count = 0;
        if (!npu_demo::detail::dma_checked_mul_non_negative(
                element_count, target.get_shape(axis), &next_element_count)) {
            return StatusCode::kError;
        }
        element_count = next_element_count;
    }

    long long target_indices[npu_demo::detail::kMaxDmaRank] = {0};
    for (long long linear = 0; linear < element_count; ++linear) {
        long long remainder = linear;
        for (unsigned long long reverse_index = 0; reverse_index < rank; ++reverse_index) {
            const unsigned long long axis = rank - 1 - reverse_index;
            target_indices[axis] = remainder % target.get_shape(axis);
            remainder /= target.get_shape(axis);
        }
        target.at(target_indices) = value;
    }
    return StatusCode::kOk;
}

/*
功能说明:
- 从 source 读取切片并写入预分配 target（Vector offset/size/stride 版本），支持与 source/target rank 一致的多维子集。

使用示例:
- Status status = npu_demo::slice(tile, source, offset, size, stride);


关联文件:
- spec: spec/include/api/Dma.md
- test: test/include/api/dma.py
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


关联文件:
- spec: spec/include/npu_demo/npu_demo.md
- test: test/dsl/gen_kernel/gen_kernel.py
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


关联文件:
- spec: spec/include/api/Dma.md
- test: test/include/api/dma.py
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


关联文件:
- spec: spec/include/npu_demo/npu_demo.md
- test: test/dsl/gen_kernel/gen_kernel.py
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

/*
功能说明:
- 提供 `gen_kernel/emit_c(target=npu_demo)` 使用的 `dma.store` 后端 helper。
- 参数顺序固定为 `target-first`，并允许 source/target 元素类型不同，写回时按 target 类型显式转换。
- 该 helper 属于 `include/npu_demo` 后端实现层，不上提为 `include/api/Dma.h` 的公共声明。

使用示例:
- Status status = store<GM, TSM, float, int32_t>(target, tile, Vector{0}, Vector{16}, Vector{1});


关联文件:
- spec: spec/dsl/gen_kernel/emit.md
- test: expectation/dsl/emit_c/npu_demo/dma/store.py
- 功能实现: include/npu_demo/Dma.h
*/
template <MemorySpace TargetSpace, MemorySpace SourceSpace, typename TargetType, typename SourceType>
inline Status store(
    Memory<TargetSpace, TargetType>& target,
    const Memory<SourceSpace, SourceType>& source,
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
        target.at(target_indices) = static_cast<TargetType>(source.at(source_indices));
    }
    return StatusCode::kOk;
}

/*
功能说明:
- 按 `perm` 将 source 物化转置到预分配 target。
- `perm[target_axis]` 表示 target 轴从 source 的哪一轴读取。
- 允许 source/target 元素类型不同，写入时按 target 类型显式转换。

使用示例:
- Status status = transpose<TSM, TSM, float, float>(target, source, Vector{1, 0});


关联文件:
- spec: spec/include/api/Dma.md
- test: test/include/api/dma.py
- 功能实现: include/npu_demo/Dma.h
*/
template <MemorySpace TargetSpace, MemorySpace SourceSpace, typename TargetType, typename SourceType>
inline Status transpose(
    Memory<TargetSpace, TargetType>& target,
    const Memory<SourceSpace, SourceType>& source,
    const Vector& perm) {
    const unsigned long long rank = source.rank();
    if (rank == 0 || rank > npu_demo::detail::kMaxDmaRank) {
        return StatusCode::kError;
    }
    if (target.rank() != rank || perm.size() != rank) {
        return StatusCode::kError;
    }
    if (source.data() == nullptr || target.data() == nullptr) {
        return StatusCode::kError;
    }

    bool seen[npu_demo::detail::kMaxDmaRank] = {false};
    long long element_count = 1;
    for (unsigned long long axis = 0; axis < rank; ++axis) {
        const long long source_axis_value = perm[axis];
        if (source_axis_value < 0 || source_axis_value >= static_cast<long long>(rank)) {
            return StatusCode::kError;
        }
        const unsigned long long source_axis = static_cast<unsigned long long>(source_axis_value);
        if (seen[source_axis]) {
            return StatusCode::kError;
        }
        seen[source_axis] = true;
        if (target.get_shape(axis) != source.get_shape(source_axis)) {
            return StatusCode::kError;
        }
        if (target.get_shape(axis) <= 0 || source.get_shape(source_axis) <= 0) {
            return StatusCode::kError;
        }
        if (target.get_stride(axis) <= 0 || source.get_stride(source_axis) <= 0) {
            return StatusCode::kError;
        }
        long long next_element_count = 0;
        if (!npu_demo::detail::dma_checked_mul_non_negative(
                element_count, target.get_shape(axis), &next_element_count)) {
            return StatusCode::kError;
        }
        element_count = next_element_count;
    }

    long long target_indices[npu_demo::detail::kMaxDmaRank] = {0};
    long long source_indices[npu_demo::detail::kMaxDmaRank] = {0};
    for (long long linear = 0; linear < element_count; ++linear) {
        long long remainder = linear;
        for (unsigned long long reverse_index = 0; reverse_index < rank; ++reverse_index) {
            const unsigned long long dim = rank - 1 - reverse_index;
            target_indices[dim] = remainder % target.get_shape(dim);
            remainder /= target.get_shape(dim);
        }
        for (unsigned long long target_axis = 0; target_axis < rank; ++target_axis) {
            const unsigned long long source_axis = static_cast<unsigned long long>(perm[target_axis]);
            source_indices[source_axis] = target_indices[target_axis];
        }
        target.at(target_indices) = static_cast<TargetType>(source.at(source_indices));
    }
    return StatusCode::kOk;
}

/*
功能说明:
- 将 `source` 按 trailing-dimension broadcast 规则物化到预分配 `target`。
- 允许 source rank 小于 target rank；缺失的前置维按 singleton 处理。

使用示例:
- Status status = npu_demo::broadcast<TSM, TSM, float, float>(target, source);


关联文件:
- spec: spec/include/api/Dma.md
- test: test/include/api/dma.py
- 功能实现: include/npu_demo/Dma.h
*/
template <MemorySpace TargetSpace, MemorySpace SourceSpace, typename TargetType, typename SourceType>
inline Status broadcast(
    Memory<TargetSpace, TargetType>& target,
    const Memory<SourceSpace, SourceType>& source) {
    const unsigned long long target_rank = target.rank();
    const unsigned long long source_rank = source.rank();
    if (target_rank == 0 || source_rank == 0 || target_rank > npu_demo::detail::kMaxDmaRank ||
        source_rank > npu_demo::detail::kMaxDmaRank || source_rank > target_rank) {
        return StatusCode::kError;
    }
    if (target.data() == nullptr || source.data() == nullptr) {
        return StatusCode::kError;
    }

    const unsigned long long rank_offset = target_rank - source_rank;
    long long element_count = 1;
    for (unsigned long long axis = 0; axis < target_rank; ++axis) {
        if (target.get_shape(axis) <= 0 || target.get_stride(axis) <= 0) {
            return StatusCode::kError;
        }
        if (axis >= rank_offset) {
            const unsigned long long source_axis = axis - rank_offset;
            const long long source_shape = source.get_shape(source_axis);
            if (source_shape <= 0 || source.get_stride(source_axis) <= 0) {
                return StatusCode::kError;
            }
            if (source_shape != 1 && source_shape != target.get_shape(axis)) {
                return StatusCode::kError;
            }
        }
        long long next_element_count = 0;
        if (!npu_demo::detail::dma_checked_mul_non_negative(
                element_count, target.get_shape(axis), &next_element_count)) {
            return StatusCode::kError;
        }
        element_count = next_element_count;
    }

    long long target_indices[npu_demo::detail::kMaxDmaRank] = {0};
    long long source_indices[npu_demo::detail::kMaxDmaRank] = {0};
    for (long long linear = 0; linear < element_count; ++linear) {
        long long remainder = linear;
        for (unsigned long long reverse_index = 0; reverse_index < target_rank; ++reverse_index) {
            const unsigned long long axis = target_rank - 1 - reverse_index;
            target_indices[axis] = remainder % target.get_shape(axis);
            remainder /= target.get_shape(axis);
        }
        for (unsigned long long source_axis = 0; source_axis < source_rank; ++source_axis) {
            const unsigned long long target_axis = source_axis + rank_offset;
            source_indices[source_axis] =
                source.get_shape(source_axis) == 1 ? 0 : target_indices[target_axis];
        }
        target.at(target_indices) = static_cast<TargetType>(source.at(source_indices));
    }
    return StatusCode::kOk;
}

}  // namespace npu_demo

#endif  // KERNELCODE_GENERATE_INCLUDE_NPU_DEMO_DMA_H_
