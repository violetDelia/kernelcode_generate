/*
功能说明:
- 提供 CUDA SM89 后端 Dma 分层实现，承接 allocation、ring、view 与 DMA copy / fill / transpose / broadcast wrapper。
- 直接服务 `dma.*` lowering，不承载 Kernel compute、CUDA runtime launch 或 host/device copy glue。

API 列表:
- `template <MemorySpace Space, typename T, typename Context> __device__ Memory<Space, T> cuda_sm89::alloc(Context& ctx, const Vector& shape, const Vector& stride, MemoryFormat format = MemoryFormat::Norm)`
- `template <MemorySpace Space, typename SlotT, typename BackingT> class cuda_sm89::DmaRing`
- `template <MemorySpace Space, typename SlotT, typename BackingT> __device__ cuda_sm89::DmaRing<Space, SlotT, BackingT>::DmaRing(Memory<Space, BackingT>& backing, S_INT num, S_INT offset_bytes, const Vector& shape, const Vector& stride, MemoryFormat format)`
- `template <MemorySpace Space, typename SlotT, typename BackingT> __device__ Memory<Space, SlotT> cuda_sm89::DmaRing<Space, SlotT, BackingT>::current() const`
- `template <MemorySpace Space, typename SlotT, typename BackingT> __device__ Memory<Space, SlotT> cuda_sm89::DmaRing<Space, SlotT, BackingT>::advance()`
- `template <typename SlotT, MemorySpace Space, typename BackingT> __device__ cuda_sm89::DmaRing<Space, SlotT, BackingT> cuda_sm89::make_ring(Memory<Space, BackingT>& backing, S_INT num, S_INT offset_bytes, std::initializer_list<long long> shape, std::initializer_list<long long> stride, MemoryFormat format = MemoryFormat::Norm)`
- `template <MemorySpace Space, typename T, typename Context> __device__ Status cuda_sm89::fill(Context& ctx, Memory<Space, T>& target, const T& value)`
- `template <MemorySpace TargetSpace, MemorySpace SourceSpace, typename T, typename Context> __device__ Status cuda_sm89::slice(Context& ctx, Memory<TargetSpace, T>& target, const Memory<SourceSpace, T>& source, const Vector& offset, const Vector& size, const Vector& stride)`
- `template <MemorySpace TargetSpace, MemorySpace SourceSpace, typename T, typename Context> __device__ Status cuda_sm89::deslice(Context& ctx, Memory<TargetSpace, T>& target, const Memory<SourceSpace, T>& source, const Vector& offset, const Vector& size, const Vector& stride)`
- `template <MemorySpace TargetSpace, MemorySpace SourceSpace, typename TargetType, typename SourceType, typename Context> __device__ Status cuda_sm89::load(Context& ctx, Memory<TargetSpace, TargetType>& target, const Memory<SourceSpace, SourceType>& source, const Vector& offset, const Vector& size, const Vector& stride)`
- `template <MemorySpace TargetSpace, MemorySpace SourceSpace, typename TargetType, typename SourceType, typename Context> __device__ Status cuda_sm89::store(Context& ctx, Memory<TargetSpace, TargetType>& target, const Memory<SourceSpace, SourceType>& source, const Vector& offset, const Vector& size, const Vector& stride)`
- `template <MemorySpace TargetSpace, MemorySpace SourceSpace, typename TargetType, typename SourceType, typename Context> __device__ Status cuda_sm89::transpose(Context& ctx, Memory<TargetSpace, TargetType>& target, const Memory<SourceSpace, SourceType>& source, const Vector& perm)`
- `template <MemorySpace TargetSpace, MemorySpace SourceSpace, typename TargetType, typename SourceType, typename Context> __device__ Status cuda_sm89::broadcast(Context& ctx, Memory<TargetSpace, TargetType>& target, const Memory<SourceSpace, SourceType>& source)`
- `template <MemorySpace Space, typename T> __host__ __device__ Memory<Space, T> cuda_sm89::view(const Memory<Space, T>& source, long long offset, long long size, long long stride)`

helper 清单:
- `cuda_sm89::detail::copy_contiguous(...)`
- `cuda_sm89::detail::fill_contiguous(...)`
- `cuda_sm89::detail::broadcast_row_vector(...)`
- `cuda_sm89::detail::fill_memory(...)`
- `cuda_sm89::detail::copy_from_source_window(...)`
- `cuda_sm89::detail::copy_to_target_window(...)`
- `cuda_sm89::detail::transpose_memory(...)`
- `cuda_sm89::detail::broadcast_memory(...)`

使用示例:
- #include "include/cuda_sm89/Dma.h"
- cuda_sm89::fill(ctx, target, 0.0f);

关联文件:
- spec: spec/include/cuda_sm89/cuda_sm89.md
- 功能实现: include/cuda_sm89/Memory.h
- 功能实现: include/cuda_sm89/Kernel.h
*/

#ifndef KERNELCODE_GENERATE_INCLUDE_CUDA_SM89_DMA_H_
#define KERNELCODE_GENERATE_INCLUDE_CUDA_SM89_DMA_H_

#include <initializer_list>

#include "include/api/Dma.h"
#include "include/cuda_sm89/Memory.h"

namespace cuda_sm89 {
namespace detail {

/*
功能说明:
- device 侧连续 copy helper，服务 `dma.copy` materialization。
- 调用方负责保证 source/target 至少包含 `element_count` 个元素。
- 仅供 generated source 或 `cuda_sm89::detail` 后端实现层内部使用，不进入公开 API。

使用示例:
- `cuda_sm89::detail::copy_contiguous(dst, src, count);`
*/
template <typename T>
__device__ void copy_contiguous(T *target, const T *source, unsigned long long element_count) {
  for (unsigned long long index = 0; index < element_count; ++index) {
    target[index] = source[index];
  }
}

/*
功能说明:
- device 侧连续 fill helper，服务 `dma.fill` materialization。
- 调用方负责保证 target 至少包含 `element_count` 个元素。
- 仅供 generated source 或 `cuda_sm89::detail` 后端实现层内部使用，不进入公开 API。

使用示例:
- `cuda_sm89::detail::fill_contiguous(dst, 0.0f, count);`
*/
template <typename T>
__device__ void fill_contiguous(T *target, T value, unsigned long long element_count) {
  for (unsigned long long index = 0; index < element_count; ++index) {
    target[index] = value;
  }
}

/*
功能说明:
- device 侧 row-vector broadcast helper，服务 9 demo 中的 `dma.broadcast` materialization。
- `cols` 表示 source row 长度，target 按 row-major `[rows, cols]` 写入。
- 仅供 generated source 或 `cuda_sm89::detail` 后端实现层内部使用，不进入公开 API。

使用示例:
- `cuda_sm89::detail::broadcast_row_vector(dst, src, rows, cols);`
*/
template <typename T>
__device__ void broadcast_row_vector(T *target, const T *source, unsigned long long rows, unsigned long long cols) {
  const unsigned long long total = rows * cols;
  for (unsigned long long index = 0; index < total; ++index) {
    target[index] = source[index % cols];
  }
}


template <typename MemoryT, typename ValueT>
__device__ Status fill_memory(MemoryT &target, const ValueT &value) {
  if (!memory_ready(target)) {
    return kError;
  }
  const unsigned long long count = memory_element_count(target);
  for (unsigned long long index = 0; index < count; ++index) {
    long long target_indices[kCudaSm89MaxRank] = {0};
    memory_linear_to_indices(index, target.rank(), target.shape(), target_indices);
    target.at(target_indices) = static_cast<ValueT>(value);
  }
  return kOk;
}

template <typename TargetMemory, typename SourceMemory>
__device__ Status copy_from_source_window(TargetMemory &target, const SourceMemory &source, const Vector &offset, const Vector &size, const Vector &stride) {
  if (!memory_ready(target) || !memory_ready(source) || size.size() == 0 || size.size() > kCudaSm89MaxRank) {
    return kError;
  }
  const unsigned long long rank = size.size();
  const unsigned long long count = vector_element_count(size);
  for (unsigned long long index = 0; index < count; ++index) {
    long long logical[kCudaSm89MaxRank] = {0};
    long long source_indices[kCudaSm89MaxRank] = {0};
    long long target_indices[kCudaSm89MaxRank] = {0};
    linear_to_indices(index, size, logical);
    for (unsigned long long axis = 0; axis < rank; ++axis) {
      const long long axis_offset = axis < offset.size() ? offset[axis] : 0;
      const long long axis_stride = axis < stride.size() ? stride[axis] : 1;
      source_indices[axis] = axis_offset + logical[axis] * axis_stride;
      target_indices[axis] = logical[axis];
    }
    target.at(target_indices) = source.at(source_indices);
  }
  return kOk;
}

template <typename TargetMemory, typename SourceMemory>
__device__ Status copy_to_target_window(TargetMemory &target, const SourceMemory &source, const Vector &offset, const Vector &size, const Vector &stride) {
  if (!memory_ready(target) || !memory_ready(source) || size.size() == 0 || size.size() > kCudaSm89MaxRank) {
    return kError;
  }
  const unsigned long long rank = size.size();
  const unsigned long long count = vector_element_count(size);
  for (unsigned long long index = 0; index < count; ++index) {
    long long logical[kCudaSm89MaxRank] = {0};
    long long source_indices[kCudaSm89MaxRank] = {0};
    long long target_indices[kCudaSm89MaxRank] = {0};
    linear_to_indices(index, size, logical);
    for (unsigned long long axis = 0; axis < rank; ++axis) {
      const long long axis_offset = axis < offset.size() ? offset[axis] : 0;
      const long long axis_stride = axis < stride.size() ? stride[axis] : 1;
      target_indices[axis] = axis_offset + logical[axis] * axis_stride;
      source_indices[axis] = logical[axis];
    }
    target.at(target_indices) = source.at(source_indices);
  }
  return kOk;
}


template <typename TargetMemory, typename SourceMemory>
__device__ Status transpose_memory(TargetMemory &target, const SourceMemory &source, const Vector &perm) {
  if (!memory_ready(target) || !memory_ready(source) || target.rank() != source.rank() || perm.size() != source.rank()) {
    return kError;
  }
  bool seen[kCudaSm89MaxRank] = {false};
  for (unsigned long long target_axis = 0; target_axis < target.rank(); ++target_axis) {
    const long long source_axis_value = perm[target_axis];
    if (source_axis_value < 0 || source_axis_value >= static_cast<long long>(source.rank())) {
      return kError;
    }
    const unsigned long long source_axis = static_cast<unsigned long long>(source_axis_value);
    if (seen[source_axis] || target.get_shape(target_axis) != source.get_shape(source_axis)) {
      return kError;
    }
    seen[source_axis] = true;
  }
  const unsigned long long count = memory_element_count(target);
  for (unsigned long long index = 0; index < count; ++index) {
    long long target_indices[kCudaSm89MaxRank] = {0};
    long long source_indices[kCudaSm89MaxRank] = {0};
    memory_linear_to_indices(index, target.rank(), target.shape(), target_indices);
    for (unsigned long long target_axis = 0; target_axis < target.rank(); ++target_axis) {
      source_indices[static_cast<unsigned long long>(perm[target_axis])] = target_indices[target_axis];
    }
    target.at(target_indices) = source.at(source_indices);
  }
  return kOk;
}

template <typename TargetMemory, typename SourceMemory>
__device__ Status broadcast_memory(TargetMemory &target, const SourceMemory &source) {
  if (!memory_ready(target) || !memory_ready(source)) {
    return kError;
  }
  const unsigned long long count = memory_element_count(target);
  for (unsigned long long index = 0; index < count; ++index) {
    long long target_indices[kCudaSm89MaxRank] = {0};
    long long source_indices[kCudaSm89MaxRank] = {0};
    memory_linear_to_indices(index, target.rank(), target.shape(), target_indices);
    if (source.rank() == 1 && target.rank() >= 1) {
      source_indices[0] = target_indices[target.rank() - 1];
    } else {
      for (unsigned long long axis = 0; axis < source.rank() && axis < target.rank(); ++axis) {
        source_indices[axis] = source.get_shape(axis) == 1 ? 0 : target_indices[axis];
      }
    }
    target.at(target_indices) = source.at(source_indices);
  }
  return kOk;
}


}  // namespace detail

/*
功能说明:
- 按 final IR shape/stride 构造片上或 fragment memory descriptor。
- 第一阶段 wrapper 按 generated source 传入的 shape 分配 device storage，并用 stride 构造 descriptor。

使用示例:
- `auto tile = cuda_sm89::alloc<MemorySpace::TLM1, float>(ctx, Vector{16, 8}, Vector{8, 1});`
*/
template <MemorySpace Space, typename T, typename Context>
__device__ Memory<Space, T> alloc(Context &ctx, const Vector &shape, const Vector &stride, MemoryFormat format = MemoryFormat::Norm) {
  (void)ctx;
  T *data = detail::alloc_device_array<T>(shape);
  return Memory<Space, T>(data, shape.data(), stride.data(), shape.size(), format);
}

template <MemorySpace Space, typename SlotT, typename BackingT>
class DmaRing {
public:
  /*
  功能说明:
  - 保存 CUDA DMA ring 的 backing descriptor、slot layout、cursor 和 ring length。
  - 构造只由 `cuda_sm89::make_ring(...)` 正向调用。

  使用示例:
  - `auto ring = cuda_sm89::make_ring<float>(backing, 2, 64, {16}, {1});`
  */
  __device__ DmaRing(Memory<Space, BackingT> &backing, S_INT num, S_INT offset_bytes, const Vector &shape, const Vector &stride, MemoryFormat format)
      : backing_(backing), num_(num), offset_bytes_(offset_bytes), cursor_(0), shape_size_(shape.size() == 0 ? 1 : shape.size()), stride_size_(stride.size() == 0 ? 1 : stride.size()), shape_{1, 1, 1, 1, 1, 1, 1, 1}, stride_{1, 1, 1, 1, 1, 1, 1, 1}, format_(format) {
    if (shape_size_ > 8) {
      shape_size_ = 8;
    }
    if (stride_size_ > 8) {
      stride_size_ = 8;
    }
    for (unsigned long long axis = 0; axis < shape_size_; ++axis) {
      shape_[axis] = axis < shape.size() ? shape[axis] : 1;
    }
    for (unsigned long long axis = 0; axis < stride_size_; ++axis) {
      stride_[axis] = axis < stride.size() ? stride[axis] : 1;
    }
  }

  /*
  功能说明:
  - 返回当前 ring slot descriptor，不推进 cursor。
  - slot shape/stride 按 make_ring 发射后的 final IR slot layout 重建。

  使用示例:
  - `Memory<MemorySpace::TLM1, float> cur = ring.current();`
  */
  __device__ Memory<Space, SlotT> current() const {
    char *base = reinterpret_cast<char *>(backing_.data());
    const S_INT normalized_cursor = num_ <= 0 ? 0 : cursor_ % num_;
    const S_INT byte_offset = offset_bytes_ <= 0 ? 0 : normalized_cursor * offset_bytes_;
    char *slot = base == nullptr ? nullptr : base + byte_offset;
    return Memory<Space, SlotT>(reinterpret_cast<SlotT *>(slot), shape_, stride_, shape_size_, format_);
  }

  /*
  功能说明:
  - 推进 ring cursor 并返回推进后的 current slot descriptor。
  - advance 位置由 emitc 生命周期分析控制，wrapper 不自行推断生命周期。

  使用示例:
  - `Memory<MemorySpace::TLM1, float> next = ring.advance();`
  */
  __device__ Memory<Space, SlotT> advance() {
    cursor_ = num_ <= 0 ? 0 : (cursor_ + 1) % num_;
    return current();
  }

private:
  Memory<Space, BackingT> &backing_;
  S_INT num_;
  S_INT offset_bytes_;
  S_INT cursor_;
  unsigned long long shape_size_;
  unsigned long long stride_size_;
  long long shape_[8];
  long long stride_[8];
  MemoryFormat format_;
};

/*
功能说明:
- 按 final IR 发射后的 slot shape/stride 构造 CUDA DMA ring descriptor。
- wrapper 不查询 runtime 设备能力，不改变 target；unsupported dynamic TLM ring 由 emit 阶段 fail-fast。

使用示例:
- `auto ring = cuda_sm89::make_ring<float>(backing, 2, 0, {16, 8}, {8, 1});`
*/
template <typename SlotT, MemorySpace Space, typename BackingT>
__device__ DmaRing<Space, SlotT, BackingT> make_ring(
    Memory<Space, BackingT> &backing,
    S_INT num,
    S_INT offset_bytes,
    std::initializer_list<long long> shape,
    std::initializer_list<long long> stride,
    MemoryFormat format = MemoryFormat::Norm) {
  long long shape_buf[8] = {1, 1, 1, 1, 1, 1, 1, 1};
  long long stride_buf[8] = {1, 1, 1, 1, 1, 1, 1, 1};
  unsigned long long shape_size = 0;
  for (long long value : shape) {
    if (shape_size < 8) {
      shape_buf[shape_size++] = value;
    }
  }
  unsigned long long stride_size = 0;
  for (long long value : stride) {
    if (stride_size < 8) {
      stride_buf[stride_size++] = value;
    }
  }
  return DmaRing<Space, SlotT, BackingT>(backing, num, offset_bytes, Vector(shape_buf, shape_size == 0 ? 1 : shape_size), Vector(stride_buf, stride_size == 0 ? 1 : stride_size), format);
}

/*
功能说明:
- 承接一维 pointer-view space 的 public `cuda_sm89::view(...)` wrapper。
- TLM fragment ordinary view 不应由 emitc 调用；无法证明安全时应在 emit 阶段 fail-fast 或走 detail fragment glue。

使用示例:
- `auto tile = cuda_sm89::view<MemorySpace::GM, float>(source, 4, 16, 1);`
*/
template <MemorySpace Space, typename T>
__host__ __device__ Memory<Space, T> view(const Memory<Space, T> &source, long long offset, long long size, long long stride) {
  const T *base = source.data();
  T *data = const_cast<T *>(base == nullptr ? nullptr : base + offset);
  return Memory<Space, T>(data, {size}, {stride}, source.format());
}

/*
功能说明:
- 承接 `dma.fill` 的 CUDA device wrapper。
- wrapper 通过 `detail::fill_memory(...)` 按 target descriptor 写入 value。

使用示例:
- `cuda_sm89::fill(ctx, target, 0.0f);`
*/
template <MemorySpace Space, typename T, typename Context>
__device__ Status fill(Context &ctx, Memory<Space, T> &target, const T &value) {
  (void)ctx;
  return detail::fill_memory(target, value);
}

/*
功能说明:
- 承接 `dma.slice/deslice/load/store/transpose/broadcast` 的 CUDA device wrapper family。
- 每个 wrapper 的 template space 与参数绑定来自 final IR，offset/size/stride 驱动设备侧搬运或变换。

使用示例:
- `cuda_sm89::load(ctx, tile, source, Vector{0}, Vector{16}, Vector{1});`
*/
template <MemorySpace TargetSpace, MemorySpace SourceSpace, typename T, typename Context>
__device__ Status slice(Context &ctx, Memory<TargetSpace, T> &target, const Memory<SourceSpace, T> &source, const Vector &offset, const Vector &size, const Vector &stride) {
  (void)ctx;
  return detail::copy_from_source_window(target, source, offset, size, stride);
}

template <MemorySpace TargetSpace, MemorySpace SourceSpace, typename T, typename Context>
__device__ Status deslice(Context &ctx, Memory<TargetSpace, T> &target, const Memory<SourceSpace, T> &source, const Vector &offset, const Vector &size, const Vector &stride) {
  (void)ctx;
  return detail::copy_to_target_window(target, source, offset, size, stride);
}

template <MemorySpace TargetSpace, MemorySpace SourceSpace, typename TargetType, typename SourceType, typename Context>
__device__ Status load(Context &ctx, Memory<TargetSpace, TargetType> &target, const Memory<SourceSpace, SourceType> &source, const Vector &offset, const Vector &size, const Vector &stride) {
  (void)ctx;
  return detail::copy_from_source_window(target, source, offset, size, stride);
}

template <MemorySpace TargetSpace, MemorySpace SourceSpace, typename TargetType, typename SourceType, typename Context>
__device__ Status store(Context &ctx, Memory<TargetSpace, TargetType> &target, const Memory<SourceSpace, SourceType> &source, const Vector &offset, const Vector &size, const Vector &stride) {
  (void)ctx;
  return detail::copy_to_target_window(target, source, offset, size, stride);
}

template <MemorySpace TargetSpace, MemorySpace SourceSpace, typename TargetType, typename SourceType, typename Context>
__device__ Status transpose(Context &ctx, Memory<TargetSpace, TargetType> &target, const Memory<SourceSpace, SourceType> &source, const Vector &perm) {
  (void)ctx;
  return detail::transpose_memory(target, source, perm);
}

template <MemorySpace TargetSpace, MemorySpace SourceSpace, typename TargetType, typename SourceType, typename Context>
__device__ Status broadcast(Context &ctx, Memory<TargetSpace, TargetType> &target, const Memory<SourceSpace, SourceType> &source) {
  (void)ctx;
  return detail::broadcast_memory(target, source);
}


}  // namespace cuda_sm89

#endif  // KERNELCODE_GENERATE_INCLUDE_CUDA_SM89_DMA_H_
