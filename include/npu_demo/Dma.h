/*
功能说明:
- 提供 npu_demo 后端的 `alloc/fill/slice/deslice/transpose/store/load/broadcast` 轻量实现，并复用 `Memory` 的成员式 `view/reshape` 接口。
- 提供 runtime `DmaRing` 与 `make_ring`，供 EmitC multi-buffer ring 使用 cursor-bearing slot view。

API 列表:
- `npu_demo::alloc<Space, T, Context>(Context& ctx, const Vector& shape, const Vector& stride, MemoryFormat format = MemoryFormat::Norm) -> Memory<Space, T>`
- `template <MemorySpace Space, typename SlotT, typename BackingT> class npu_demo::DmaRing`
- `npu_demo::DmaRing.current() const -> Memory<Space, SlotT>`
- `npu_demo::DmaRing.advance() -> Memory<Space, SlotT>`
- `npu_demo::make_ring<SlotT, Space, BackingT>(Memory<Space, BackingT>& backing, S_INT num, S_INT offset_bytes, std::initializer_list<long long> shape, std::initializer_list<long long> stride, MemoryFormat format = MemoryFormat::Norm) -> DmaRing<Space, SlotT, BackingT>`
- `npu_demo::fill<Space, T, Context>(Context& ctx, Memory<Space, T>& target, const T& value) -> Status`
- `npu_demo::slice<TargetSpace, SourceSpace, T, Context>(Context& ctx, Memory<TargetSpace, T>& target, const Memory<SourceSpace, T>& source, const Vector& offset, const Vector& size, const Vector& stride) -> Status`
- `npu_demo::deslice<TargetSpace, SourceSpace, T, Context>(Context& ctx, Memory<TargetSpace, T>& target, const Memory<SourceSpace, T>& source, const Vector& offset, const Vector& size, const Vector& stride) -> Status`
- `npu_demo::transpose<TargetSpace, SourceSpace, TargetType, SourceType, Context>(Context& ctx, Memory<TargetSpace, TargetType>& target, const Memory<SourceSpace, SourceType>& source, const Vector& perm) -> Status`
- `npu_demo::store<TargetSpace, SourceSpace, TargetType, SourceType, Context>(Context& ctx, Memory<TargetSpace, TargetType>& target, const Memory<SourceSpace, SourceType>& source, const Vector& offset, const Vector& size, const Vector& stride) -> Status`
- `npu_demo::load<TargetSpace, SourceSpace, TargetType, SourceType, Context>(Context& ctx, Memory<TargetSpace, TargetType>& target, const Memory<SourceSpace, SourceType>& source, const Vector& offset, const Vector& size, const Vector& stride) -> Status`
- `npu_demo::broadcast<TargetSpace, SourceSpace, TargetType, SourceType, Context>(Context& ctx, Memory<TargetSpace, TargetType>& target, const Memory<SourceSpace, SourceType>& source) -> Status`

使用示例:
- #include "include/npu_demo/Dma.h"
- Status status = npu_demo::slice(ctx, tile, source, offset, size, stride);


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
- 初始化 runtime DmaRing 私有状态；调用方只能通过 `make_ring(...)` 获得对象。
- shape/stride 已由 factory 校验，构造函数只复制短生命周期布局数组。

使用示例:
- auto ring = npu_demo::make_ring<float>(backing, 2, 64, {4, 4}, {4, 1});


关联文件:
- spec: spec/include/api/Dma.md
- test: test/include/api/test_dma.py
- 功能实现: include/npu_demo/Dma.h
*/
template <MemorySpace Space, typename SlotT, typename BackingT>
inline DmaRing<Space, SlotT, BackingT>::DmaRing(
    BackingT* backing_data,
    S_INT num,
    S_INT offset_bytes,
    const long long* shape,
    const long long* stride,
    unsigned long long rank,
    MemoryFormat format)
    : backing_data_(backing_data),
      num_(num),
      offset_bytes_(offset_bytes),
      shape_{0, 0, 0, 0, 0, 0, 0, 0},
      stride_{0, 0, 0, 0, 0, 0, 0, 0},
      rank_(rank),
      format_(format),
      cursor_(0) {
    for (unsigned long long i = 0; i < rank_; ++i) {
        shape_[i] = shape[i];
        stride_[i] = stride[i];
    }
}

/*
功能说明:
- 返回当前 cursor 对应的 typed slot view。
- slot 起点按 byte pointer arithmetic 计算，避免 `Memory::view<T>` 的 element-offset 语义误用于 byte offset。

使用示例:
- Memory<TLM1, float> cur = ring.current();


关联文件:
- spec: spec/include/api/Dma.md
- test: test/include/api/test_dma.py
- 功能实现: include/npu_demo/Dma.h
*/
template <MemorySpace Space, typename SlotT, typename BackingT>
inline Memory<Space, SlotT> DmaRing<Space, SlotT, BackingT>::current() const {
    unsigned char* base = reinterpret_cast<unsigned char*>(backing_data_);
    SlotT* slot_data = reinterpret_cast<SlotT*>(base + cursor_ * offset_bytes_);
    return Memory<Space, SlotT>(slot_data, shape_, stride_, rank_, format_);
}

/*
功能说明:
- 推进 cursor 并返回推进后的 typed slot view。
- `num` 由 `make_ring(...)` 保证为正数，因此 modulo 不会除零。

使用示例:
- Memory<TLM1, float> next = ring.advance();


关联文件:
- spec: spec/include/api/Dma.md
- test: test/include/api/test_dma.py
- 功能实现: include/npu_demo/Dma.h
*/
template <MemorySpace Space, typename SlotT, typename BackingT>
inline Memory<Space, SlotT> DmaRing<Space, SlotT, BackingT>::advance() {
    cursor_ = (cursor_ + 1) % num_;
    return current();
}

/*
功能说明:
- 从一维 byte backing memory 创建 runtime DmaRing。
- 校验 num、offset、slot layout、slot span 与 backing storage 范围；失败时抛出 `std::runtime_error`。

使用示例:
- auto ring = npu_demo::make_ring<float>(backing, 2, 64, {4, 4}, {4, 1});


关联文件:
- spec: spec/include/api/Dma.md
- test: test/include/api/test_dma.py
- 功能实现: include/npu_demo/Dma.h
*/
template <typename SlotT, MemorySpace Space, typename BackingT>
inline DmaRing<Space, SlotT, BackingT> make_ring(
    Memory<Space, BackingT>& backing,
    S_INT num,
    S_INT offset_bytes,
    std::initializer_list<long long> shape,
    std::initializer_list<long long> stride,
    MemoryFormat format) {
    static_assert(sizeof(BackingT) == 1, "dma.make_ring backing element must be byte-sized");
    const unsigned long long rank = shape.size();
    if (rank == 0 || rank != stride.size() || rank > npu_demo::detail::kMaxDmaRank) {
        throw std::runtime_error("dma.make_ring: invalid slot layout");
    }
    if (backing.data() == nullptr || backing.rank() != 1 || backing.get_shape(0) <= 0 || backing.get_stride(0) <= 0) {
        throw std::runtime_error("dma.make_ring: invalid backing memory");
    }
    if (num <= 0 || offset_bytes <= 0) {
        throw std::runtime_error("dma.make_ring: invalid ring parameters");
    }

    long long shape_buf[npu_demo::detail::kMaxDmaRank] = {0};
    long long stride_buf[npu_demo::detail::kMaxDmaRank] = {0};
    long long max_slot_linear_offset = 0;
    auto shape_it = shape.begin();
    auto stride_it = stride.begin();
    for (unsigned long long i = 0; i < rank; ++i, ++shape_it, ++stride_it) {
        if (*shape_it <= 0 || *stride_it <= 0) {
            throw std::runtime_error("dma.make_ring: invalid slot layout");
        }
        shape_buf[i] = *shape_it;
        stride_buf[i] = *stride_it;
        long long axis_span = 0;
        if (!npu_demo::detail::dma_checked_mul_non_negative(shape_buf[i] - 1, stride_buf[i], &axis_span)) {
            throw std::runtime_error("dma.make_ring: slot span overflow");
        }
        if (!npu_demo::detail::dma_checked_add_non_negative(
                max_slot_linear_offset, axis_span, &max_slot_linear_offset)) {
            throw std::runtime_error("dma.make_ring: slot span overflow");
        }
    }

    long long slot_element_span = 0;
    if (!npu_demo::detail::dma_checked_add_non_negative(max_slot_linear_offset, 1, &slot_element_span)) {
        throw std::runtime_error("dma.make_ring: slot span overflow");
    }
    long long slot_span_bytes = 0;
    if (!npu_demo::detail::dma_checked_mul_non_negative(
            slot_element_span, static_cast<long long>(sizeof(SlotT)), &slot_span_bytes)) {
        throw std::runtime_error("dma.make_ring: slot span overflow");
    }
    if (slot_span_bytes > offset_bytes) {
        throw std::runtime_error("dma.make_ring: slot span exceeds offset");
    }

    long long backing_last_offset = 0;
    if (!npu_demo::detail::dma_checked_mul_non_negative(
            backing.get_shape(0) - 1, backing.get_stride(0), &backing_last_offset)) {
        throw std::runtime_error("dma.make_ring: backing span overflow");
    }
    long long backing_bytes = 0;
    if (!npu_demo::detail::dma_checked_add_non_negative(backing_last_offset, 1, &backing_bytes)) {
        throw std::runtime_error("dma.make_ring: backing span overflow");
    }
    long long required_bytes = 0;
    if (!npu_demo::detail::dma_checked_mul_non_negative(num, offset_bytes, &required_bytes)) {
        throw std::runtime_error("dma.make_ring: backing range overflow");
    }
    if (required_bytes > backing_bytes) {
        throw std::runtime_error("dma.make_ring: backing memory too small");
    }
    return DmaRing<Space, SlotT, BackingT>(
        backing.data(),
        num,
        offset_bytes,
        shape_buf,
        stride_buf,
        rank,
        format);
}

/*
功能说明:
- 按给定 shape/stride 创建一块新的 `Memory<Space, T>`，供 npu_demo DMA helper 使用。
- backing storage 由 helper 在堆上分配，并按 shape/stride 复制到返回的 Memory 元信息中。

使用示例:
- npu_demo::KernelContext ctx;
- Memory<TSM, float> tile = npu_demo::alloc<TSM, float>(ctx, {16}, {1});


关联文件:
- spec: spec/include/api/Dma.md
- test: test/include/api/test_dma.py
- 功能实现: include/npu_demo/Dma.h
*/
template <MemorySpace Space, typename T, typename Context>
inline Memory<Space, T> alloc(
    Context& ctx,
    const Vector& shape,
    const Vector& stride,
    MemoryFormat format) {
    (void)ctx;
    const unsigned long long rank = shape.size();
    if (rank == 0 || rank != stride.size() || rank > npu_demo::detail::kMaxDmaRank) {
        throw std::runtime_error("dma.alloc: invalid shape/stride");
    }

    long long max_linear_offset = 0;
    for (unsigned long long i = 0; i < rank; ++i) {
        if (shape[i] <= 0 || stride[i] <= 0) {
            throw std::runtime_error("dma.alloc: invalid shape/stride");
        }

        long long span = 0;
        if (!npu_demo::detail::dma_checked_mul_non_negative(shape[i] - 1, stride[i], &span)) {
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
    switch (rank) {
        case 1:
            return Memory<Space, T>(data, {shape[0]}, {stride[0]}, format);
        case 2:
            return Memory<Space, T>(data, {shape[0], shape[1]}, {stride[0], stride[1]}, format);
        case 3:
            return Memory<Space, T>(
                data,
                {shape[0], shape[1], shape[2]},
                {stride[0], stride[1], stride[2]},
                format);
        case 4:
            return Memory<Space, T>(
                data,
                {shape[0], shape[1], shape[2], shape[3]},
                {stride[0], stride[1], stride[2], stride[3]},
                format);
        case 5:
            return Memory<Space, T>(
                data,
                {shape[0], shape[1], shape[2], shape[3], shape[4]},
                {stride[0], stride[1], stride[2], stride[3], stride[4]},
                format);
        case 6:
            return Memory<Space, T>(
                data,
                {shape[0], shape[1], shape[2], shape[3], shape[4], shape[5]},
                {stride[0], stride[1], stride[2], stride[3], stride[4], stride[5]},
                format);
        case 7:
            return Memory<Space, T>(
                data,
                {shape[0], shape[1], shape[2], shape[3], shape[4], shape[5], shape[6]},
                {stride[0], stride[1], stride[2], stride[3], stride[4], stride[5], stride[6]},
                format);
        case 8:
            return Memory<Space, T>(
                data,
                {shape[0], shape[1], shape[2], shape[3], shape[4], shape[5], shape[6], shape[7]},
                {stride[0], stride[1], stride[2], stride[3], stride[4], stride[5], stride[6], stride[7]},
                format);
    }
    throw std::runtime_error("dma.alloc: invalid shape/stride");
}

/*
功能说明:
- 使用标量值填充 `target` 的全部逻辑元素。
- 支持非连续 stride；填充范围按 shape 逻辑坐标遍历。

使用示例:
- Status status = npu_demo::fill<TSM, float>(ctx, target, 0.0f);


关联文件:
- spec: spec/include/api/Dma.md
- test: test/include/api/test_dma.py
- 功能实现: include/npu_demo/Dma.h
*/
template <MemorySpace Space, typename T, typename Context>
inline Status fill(Context& ctx, Memory<Space, T>& target, const T& value) {
    (void)ctx;
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
- Status status = npu_demo::slice(ctx, tile, source, offset, size, stride);


关联文件:
- spec: spec/include/api/Dma.md
- test: test/include/api/test_dma.py
- 功能实现: include/npu_demo/Dma.h
*/
template <MemorySpace TargetSpace, MemorySpace SourceSpace, typename T, typename Context>
inline Status slice(
    Context& ctx,
    Memory<TargetSpace, T>& target,
    const Memory<SourceSpace, T>& source,
    const Vector& offset,
    const Vector& size,
    const Vector& stride) {
    (void)ctx;
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
- 将 source 块写回 target 的指定区域（Vector offset/size/stride 版本），公开参数顺序固定为 `target-first`。

使用示例:
- Status status = npu_demo::deslice(ctx, target, tile, offset, size, stride);


关联文件:
- spec: spec/include/api/Dma.md
- test: test/include/api/test_dma.py
- 功能实现: include/npu_demo/Dma.h
*/
template <MemorySpace TargetSpace, MemorySpace SourceSpace, typename T, typename Context>
inline Status deslice(
    Context& ctx,
    Memory<TargetSpace, T>& target,
    const Memory<SourceSpace, T>& source,
    const Vector& offset,
    const Vector& size,
    const Vector& stride) {
    (void)ctx;
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
- 提供 `gen_kernel/emit_c(target=npu_demo)` 使用的 `dma.store` 后端 helper。
- 参数顺序固定为 `target-first`，并允许 source/target 元素类型不同，写回时按 target 类型显式转换。
- 该 helper 承接 `include/api/Dma.h` 的 context-first 公开声明。

使用示例:
- Status status = npu_demo::store<GM, TSM, float, int32_t>(ctx, target, tile, offset, size, stride);


关联文件:
- spec: spec/dsl/gen_kernel/emit.md
- test: expectation/dsl/emit_c/npu_demo/dma/store.py
- 功能实现: include/npu_demo/Dma.h
*/
template <MemorySpace TargetSpace, MemorySpace SourceSpace, typename TargetType, typename SourceType, typename Context>
inline Status store(
    Context& ctx,
    Memory<TargetSpace, TargetType>& target,
    const Memory<SourceSpace, SourceType>& source,
    const Vector& offset,
    const Vector& size,
    const Vector& stride) {
    (void)ctx;
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
- 提供 `dma.load` 的 Vector offset/size/stride 后端 helper，按 source 区域读取并写入预分配 target。
- 允许 source/target 元素类型不同，写入 target 时按 `TargetType` 显式转换；非法 rank、长度、边界或数据指针返回 `StatusCode::kError`。

使用示例:
- Status status = load<TSM, GM, float, int32_t>(ctx, tile, source, offset, size, stride);


关联文件:
- spec: spec/include/api/Dma.md
- test: test/include/api/test_dma.py
- 功能实现: include/npu_demo/Dma.h
*/
template <MemorySpace TargetSpace, MemorySpace SourceSpace, typename TargetType, typename SourceType, typename Context>
inline Status load(
    Context& ctx,
    Memory<TargetSpace, TargetType>& target,
    const Memory<SourceSpace, SourceType>& source,
    const Vector& offset,
    const Vector& size,
    const Vector& stride) {
    (void)ctx;
    const unsigned long long rank = source.rank();
    if (rank == 0 || rank > npu_demo::detail::kMaxDmaRank ||
        target.rank() != rank || offset.size() != rank || size.size() != rank || stride.size() != rank) {
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
        if (source.get_stride(i) <= 0 || target.get_stride(i) <= 0 || target.get_shape(i) != size[i]) {
            return StatusCode::kError;
        }
        long long span = 0;
        if (!npu_demo::detail::dma_checked_mul_non_negative(size[i] - 1, stride[i], &span)) {
            return StatusCode::kError;
        }
        long long last_index = 0;
        if (!npu_demo::detail::dma_checked_add_non_negative(offset[i], span, &last_index) ||
            last_index >= source.get_shape(i)) {
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
            if (!npu_demo::detail::dma_checked_add_non_negative(
                    offset[dim], source_delta, &source_indices[dim])) {
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
- Status status = npu_demo::transpose<TSM, TSM, float, float>(ctx, target, source, perm);


关联文件:
- spec: spec/include/api/Dma.md
- test: test/include/api/test_dma.py
- 功能实现: include/npu_demo/Dma.h
*/
template <MemorySpace TargetSpace, MemorySpace SourceSpace, typename TargetType, typename SourceType, typename Context>
inline Status transpose(
    Context& ctx,
    Memory<TargetSpace, TargetType>& target,
    const Memory<SourceSpace, SourceType>& source,
    const Vector& perm) {
    (void)ctx;
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
        if (source_axis_value < 0) {
            return StatusCode::kError;
        }
        const unsigned long long source_axis = static_cast<unsigned long long>(source_axis_value);
        if (source_axis >= rank) {
            return StatusCode::kError;
        }
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
- Status status = npu_demo::broadcast<TSM, TSM, float, float>(ctx, target, source);


关联文件:
- spec: spec/include/api/Dma.md
- test: test/include/api/test_dma.py
- 功能实现: include/npu_demo/Dma.h
*/
template <MemorySpace TargetSpace, MemorySpace SourceSpace, typename TargetType, typename SourceType, typename Context>
inline Status broadcast(
    Context& ctx,
    Memory<TargetSpace, TargetType>& target,
    const Memory<SourceSpace, SourceType>& source) {
    (void)ctx;
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
