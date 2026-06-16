/*
功能说明:
- 提供 CUDA SM89 后端 Memory 分层实现，补全 `Memory<Space, T>` 视图方法和 memory descriptor glue。
- 承接 generated source 使用的 slot / descriptor / index helper，不承载 DMA 搬运、Kernel compute 或 Arch launch 实现。

API 列表:
- `enum class MemoryFormat { Norm, CLast }`
- `enum class MemorySpace { GM, SM, LM, TSM, TLM1, TLM2, TLM3 }`
- `void npu_demo::build_contiguous_stride(const long long* shape, unsigned long long rank, long long* out_stride)`
- `template <MemorySpace Space, typename T> class Memory`
- `Memory::Memory(T* data, const long long* shape, const long long* stride, unsigned long long rank, MemoryFormat format = MemoryFormat::Norm)`
- `Memory::Memory(T* data, const long long* shape, unsigned long long rank, MemoryFormat format = MemoryFormat::Norm)`
- `Memory::Memory(T* data, std::initializer_list<long long> shape, std::initializer_list<long long> stride, MemoryFormat format = MemoryFormat::Norm)`
- `Memory::Memory(T* data, std::initializer_list<long long> shape, MemoryFormat format = MemoryFormat::Norm)`
- `Memory::data() -> T*`
- `Memory::data() const -> const T*`
- `Memory::shape() const -> const long long*`
- `Memory::stride() const -> const long long*`
- `Memory::rank() const -> unsigned long long`
- `Memory::format() const -> MemoryFormat`
- `Memory::space() const -> MemorySpace`
- `Memory::get_shape(unsigned long long axis) const -> long long`
- `Memory::get_stride(unsigned long long axis) const -> long long`
- `template <typename ViewT> Memory::view(const Vector& offset, const Vector& size, const Vector& stride) const -> Memory<Space, ViewT>`
- `template <typename ViewT> Memory::view(std::initializer_list<long long> offset, std::initializer_list<long long> size, std::initializer_list<long long> stride) const -> Memory<Space, ViewT>`
- `Memory::reshape(const Vector& shape) const -> Memory<Space, T>`
- `Memory::reshape(std::initializer_list<long long> shape) const -> Memory<Space, T>`
- `Memory::element_count() const -> long long`
- `Memory::is_contiguous() const -> bool`
- `Memory::trance_print(const kernelcode::trance::TranceSink& sink, const char* name) const -> void`
- `Memory::linear_offset(const long long* indices) const -> long long`
- `Memory::at(const long long* indices) -> T&`
- `Memory::at(const long long* indices) const -> const T&`

helper 清单:
- `cuda_sm89::detail::MemoryDescriptor`
- `cuda_sm89::detail::is_f32_memory(...)`
- `cuda_sm89::detail::has_memory_data(...)`
- `cuda_sm89::detail::has_int_arg(...)`
- `cuda_sm89::detail::int_arg_or(...)`
- `cuda_sm89::detail::element_count(...)`
- `cuda_sm89::detail::descriptor_from_slot(...)`
- `cuda_sm89::detail::memory_from_slot(...)`
- `cuda_sm89::detail::fragment_alias(...)`
- `cuda_sm89::detail::memory_data_token(...)`
- `cuda_sm89::detail::alias_descriptor(...)`
- `cuda_sm89::detail::descriptor_element_count(...)`
- `cuda_sm89::detail::memory_ready(...)`
- `cuda_sm89::detail::vector_element_count(...)`
- `cuda_sm89::detail::memory_element_count(...)`
- `cuda_sm89::detail::linear_to_indices(...)`
- `cuda_sm89::detail::memory_linear_to_indices(...)`
- `cuda_sm89::detail::alloc_device_array(...)`

使用示例:
- #include "include/cuda_sm89/Memory.h"
- auto memory = cuda_sm89::detail::memory_from_slot<GM, float>(slots, count, 0);

关联文件:
- spec: spec/include/cuda_sm89/cuda_sm89.md
- 功能实现: include/cuda_sm89/Core.h
- 功能实现: include/cuda_sm89/Dma.h
*/

#ifndef KERNELCODE_GENERATE_INCLUDE_CUDA_SM89_MEMORY_H_
#define KERNELCODE_GENERATE_INCLUDE_CUDA_SM89_MEMORY_H_

#include <initializer_list>
#include <new>

#include "include/api/Memory.h"
#include "include/cuda_sm89/Core.h"

#ifndef KERNELCODE_GENERATE_INCLUDE_NPU_DEMO_MEMORY_H_
namespace npu_demo {
KG_CUDA_SM89_HD inline void build_contiguous_stride(const long long *shape, unsigned long long rank, long long *out_stride) {
  long long current = 1;
  for (unsigned long long reverse_index = 0; reverse_index < rank; ++reverse_index) {
    const unsigned long long axis = rank - 1 - reverse_index;
    out_stride[axis] = current;
    current *= shape[axis];
  }
}
}  // namespace npu_demo

template <MemorySpace Space, typename T>
KG_CUDA_SM89_HD inline Memory<Space, T>::Memory(T *data, const long long *shape, const long long *stride, unsigned long long rank, MemoryFormat format)
    : data_(data), rank_(0), format_(format) {
  init_shape_and_stride(rank, shape, stride);
}

template <MemorySpace Space, typename T>
KG_CUDA_SM89_HD inline Memory<Space, T>::Memory(T *data, const long long *shape, unsigned long long rank, MemoryFormat format)
    : data_(data), rank_(0), format_(format) {
  init_shape_and_stride(rank, shape, nullptr);
}

template <MemorySpace Space, typename T>
KG_CUDA_SM89_HD inline Memory<Space, T>::Memory(T *data, std::initializer_list<long long> shape, std::initializer_list<long long> stride, MemoryFormat format)
    : data_(data), rank_(0), format_(format) {
  long long shape_buf[kMaxDim] = {0};
  long long stride_buf[kMaxDim] = {0};
  unsigned long long rank = 0;
  auto shape_it = shape.begin();
  auto stride_it = stride.begin();
  for (; rank < shape.size() && rank < stride.size() && rank < kMaxDim; ++rank, ++shape_it, ++stride_it) {
    shape_buf[rank] = *shape_it;
    stride_buf[rank] = *stride_it;
  }
  init_shape_and_stride(rank == 0 ? 1 : rank, shape_buf, stride_buf);
}

template <MemorySpace Space, typename T>
KG_CUDA_SM89_HD inline Memory<Space, T>::Memory(T *data, std::initializer_list<long long> shape, MemoryFormat format)
    : data_(data), rank_(0), format_(format) {
  long long shape_buf[kMaxDim] = {0};
  unsigned long long rank = 0;
  auto shape_it = shape.begin();
  for (; rank < shape.size() && rank < kMaxDim; ++rank, ++shape_it) {
    shape_buf[rank] = *shape_it;
  }
  init_shape_and_stride(rank == 0 ? 1 : rank, shape_buf, nullptr);
}

template <MemorySpace Space, typename T>
KG_CUDA_SM89_HD inline T *Memory<Space, T>::data() {
  return data_;
}

template <MemorySpace Space, typename T>
KG_CUDA_SM89_HD inline const T *Memory<Space, T>::data() const {
  return data_;
}

template <MemorySpace Space, typename T>
KG_CUDA_SM89_HD inline const long long *Memory<Space, T>::shape() const {
  return shape_;
}

template <MemorySpace Space, typename T>
KG_CUDA_SM89_HD inline const long long *Memory<Space, T>::stride() const {
  return stride_;
}

template <MemorySpace Space, typename T>
KG_CUDA_SM89_HD inline unsigned long long Memory<Space, T>::rank() const {
  return rank_;
}

template <MemorySpace Space, typename T>
KG_CUDA_SM89_HD inline MemoryFormat Memory<Space, T>::format() const {
  return format_;
}

template <MemorySpace Space, typename T>
KG_CUDA_SM89_HD inline MemorySpace Memory<Space, T>::space() const {
  return Space;
}

template <MemorySpace Space, typename T>
KG_CUDA_SM89_HD inline long long Memory<Space, T>::get_shape(unsigned long long axis) const {
  return shape_[axis];
}

template <MemorySpace Space, typename T>
KG_CUDA_SM89_HD inline long long Memory<Space, T>::get_stride(unsigned long long axis) const {
  return stride_[axis];
}

template <MemorySpace Space, typename T>
template <typename ViewT>
KG_CUDA_SM89_HD inline Memory<Space, ViewT> Memory<Space, T>::view(const Vector &offset, const Vector &size, const Vector &stride) const {
  long long shape_buf[kMaxDim] = {0};
  long long stride_buf[kMaxDim] = {0};
  long long linear_offset_value = 0;
  const unsigned long long requested_rank = size.size() == 0 ? 1 : size.size();
  const unsigned long long view_rank = requested_rank < kMaxDim ? requested_rank : kMaxDim;
  if (offset.size() == 1 && size.size() > 1) {
    linear_offset_value = offset[0];
  }
  for (unsigned long long axis = 0; axis < view_rank; ++axis) {
    const long long axis_offset = axis < offset.size() ? offset[axis] : 0;
    const long long source_stride = axis < rank_ ? stride_[axis] : 1;
    const long long axis_stride = axis < stride.size() ? stride[axis] : 1;
    shape_buf[axis] = size[axis];
    stride_buf[axis] = source_stride * axis_stride;
    if (offset.size() != 1 || size.size() <= 1) {
      linear_offset_value += axis_offset * source_stride;
    }
  }
  ViewT *view_data = reinterpret_cast<ViewT *>(data_);
  if (view_data != nullptr) {
    view_data += linear_offset_value;
  }
  return Memory<Space, ViewT>(view_data, shape_buf, stride_buf, view_rank == 0 ? 1 : view_rank, format_);
}

template <MemorySpace Space, typename T>
template <typename ViewT>
KG_CUDA_SM89_HD inline Memory<Space, ViewT> Memory<Space, T>::view(
    std::initializer_list<long long> offset,
    std::initializer_list<long long> size,
    std::initializer_list<long long> stride) const {
  long long offset_buf[kMaxDim] = {0};
  long long size_buf[kMaxDim] = {0};
  long long stride_buf[kMaxDim] = {1, 1, 1, 1, 1, 1, 1, 1};
  unsigned long long rank = 0;
  auto offset_it = offset.begin();
  auto size_it = size.begin();
  auto stride_it = stride.begin();
  for (; rank < offset.size() && rank < size.size() && rank < stride.size() && rank < kMaxDim; ++rank, ++offset_it, ++size_it, ++stride_it) {
    offset_buf[rank] = *offset_it;
    size_buf[rank] = *size_it;
    stride_buf[rank] = *stride_it;
  }
  return view<ViewT>(Vector(offset_buf, rank == 0 ? 1 : rank), Vector(size_buf, rank == 0 ? 1 : rank), Vector(stride_buf, rank == 0 ? 1 : rank));
}

template <MemorySpace Space, typename T>
KG_CUDA_SM89_HD inline Memory<Space, T> Memory<Space, T>::reshape(const Vector &shape) const {
  long long shape_buf[kMaxDim] = {0};
  long long stride_buf[kMaxDim] = {0};
  const unsigned long long new_rank = shape.size() == 0 ? 1 : (shape.size() < kMaxDim ? shape.size() : kMaxDim);
  for (unsigned long long axis = 0; axis < new_rank; ++axis) {
    shape_buf[axis] = shape[axis];
  }
  npu_demo::build_contiguous_stride(shape_buf, new_rank, stride_buf);
  return Memory<Space, T>(data_, shape_buf, stride_buf, new_rank, format_);
}

template <MemorySpace Space, typename T>
KG_CUDA_SM89_HD inline Memory<Space, T> Memory<Space, T>::reshape(std::initializer_list<long long> shape) const {
  long long shape_buf[kMaxDim] = {0};
  unsigned long long rank = 0;
  auto shape_it = shape.begin();
  for (; rank < shape.size() && rank < kMaxDim; ++rank, ++shape_it) {
    shape_buf[rank] = *shape_it;
  }
  return reshape(Vector(shape_buf, rank == 0 ? 1 : rank));
}

template <MemorySpace Space, typename T>
KG_CUDA_SM89_HD inline long long Memory<Space, T>::element_count() const {
  long long count = 1;
  for (unsigned long long axis = 0; axis < rank_; ++axis) {
    count *= shape_[axis];
  }
  return count;
}

template <MemorySpace Space, typename T>
KG_CUDA_SM89_HD inline bool Memory<Space, T>::is_contiguous() const {
  long long expected = 1;
  for (unsigned long long reverse_index = 0; reverse_index < rank_; ++reverse_index) {
    const unsigned long long axis = rank_ - 1 - reverse_index;
    if (stride_[axis] != expected) {
      return false;
    }
    expected *= shape_[axis];
  }
  return true;
}

template <MemorySpace Space, typename T>
inline void Memory<Space, T>::trance_print(const kernelcode::trance::TranceSink &sink, const char *name) const {
  (void)sink;
  (void)name;
}

template <MemorySpace Space, typename T>
KG_CUDA_SM89_HD inline long long Memory<Space, T>::linear_offset(const long long *indices) const {
  long long offset = 0;
  for (unsigned long long axis = 0; axis < rank_; ++axis) {
    offset += indices[axis] * stride_[axis];
  }
  return offset;
}

template <MemorySpace Space, typename T>
KG_CUDA_SM89_HD inline T &Memory<Space, T>::at(const long long *indices) {
  return data_[linear_offset(indices)];
}

template <MemorySpace Space, typename T>
KG_CUDA_SM89_HD inline const T &Memory<Space, T>::at(const long long *indices) const {
  return data_[linear_offset(indices)];
}

template <MemorySpace Space, typename T>
KG_CUDA_SM89_HD inline void Memory<Space, T>::contract_or_trap(bool condition) {
  if (condition) {
    return;
  }
#if defined(__CUDA_ARCH__)
  asm volatile("trap;");
#elif defined(__clang__) || defined(__GNUC__)
  __builtin_trap();
#else
  *(volatile int *)0 = 0;
#endif
}

template <MemorySpace Space, typename T>
KG_CUDA_SM89_HD inline void Memory<Space, T>::init_shape_and_stride(unsigned long long rank, const long long *shape, const long long *stride) {
  contract_or_trap(rank > 0 && rank <= kMaxDim);
  rank_ = rank;
  for (unsigned long long axis = 0; axis < rank_; ++axis) {
    shape_[axis] = shape == nullptr ? 1 : shape[axis];
  }
  if (stride != nullptr) {
    for (unsigned long long axis = 0; axis < rank_; ++axis) {
      stride_[axis] = stride[axis];
    }
    return;
  }
  fill_contiguous_stride();
}

template <MemorySpace Space, typename T>
KG_CUDA_SM89_HD inline void Memory<Space, T>::fill_contiguous_stride() {
  long long current = 1;
  for (unsigned long long reverse_index = 0; reverse_index < rank_; ++reverse_index) {
    const unsigned long long axis = rank_ - 1 - reverse_index;
    stride_[axis] = current;
    current *= shape_[axis];
  }
}
#endif


namespace cuda_sm89 {
namespace detail {

struct MemoryDescriptor {
  void *data;
  const long long *shape;
  const long long *stride;
  unsigned long long rank;
  int dtype_code;
};


/*
功能说明:
- 判断指定 slot 是否是 rank 匹配的 f32 memory 参数。
- generated source 用它在读取 memory slot 前校验 kind、dtype、rank、shape 和 stride 指针。
- 仅供 generated source 或 `cuda_sm89::detail` 后端实现层内部使用，不进入公开 API。

使用示例:
- `if (!cuda_sm89::detail::is_f32_memory(slots, count, 0, 2)) { return -1; }`
*/
inline bool is_f32_memory(const ArgSlot *slots, unsigned long long count, unsigned long long index, unsigned long long rank) {
  return slots != nullptr && index < count && slots[index].kind == 1 && slots[index].dtype_code == 1 && slots[index].rank == rank &&
         slots[index].shape != nullptr && slots[index].stride != nullptr;
}

/*
功能说明:
- 判断指定 slot 是否是带非空 data 指针的 memory 参数。
- generated source 用它区分可拷贝 memory 与缺失或非 memory slot。
- 仅供 generated source 或 `cuda_sm89::detail` 后端实现层内部使用，不进入公开 API。

使用示例:
- `if (!cuda_sm89::detail::has_memory_data(slots, count, 1)) { return -1; }`
*/
inline bool has_memory_data(const ArgSlot *slots, unsigned long long count, unsigned long long index) {
  return slots != nullptr && index < count && slots[index].kind == 1 && slots[index].data != nullptr;
}

/*
功能说明:
- 判断指定 slot 是否是整数标量参数。
- generated source 用它读取 runtime shape、stride 或 tile 相关整数参数前做 slot kind 校验。
- 仅供 generated source 或 `cuda_sm89::detail` 后端实现层内部使用，不进入公开 API。

使用示例:
- `if (!cuda_sm89::detail::has_int_arg(slots, count, 3)) { return -1; }`
*/
KG_CUDA_SM89_HD inline bool has_int_arg(const ArgSlot *slots, unsigned long long count, unsigned long long index) {
  return slots != nullptr && index < count && slots[index].kind == 2;
}

/*
功能说明:
- 读取整数标量 slot；slot 缺失或 kind 不匹配时返回调用方给定默认值。
- generated source 用它处理可选 runtime 参数，避免把缺省值逻辑散落在各 kernel wrapper 中。
- 仅供 generated source 或 `cuda_sm89::detail` 后端实现层内部使用，不进入公开 API。

使用示例:
- `long long stride = cuda_sm89::detail::int_arg_or(slots, count, 4, 1);`
*/
KG_CUDA_SM89_HD inline long long int_arg_or(const ArgSlot *slots, unsigned long long count, unsigned long long index, long long default_value) {
  if (!has_int_arg(slots, count, index)) {
    return default_value;
  }
  return slots[index].int_value;
}

/*
功能说明:
- 根据 memory slot 的 shape 计算元素总数；rank 为 0、shape 为空或任一维非正时返回 0。
- generated source 用它确定 device allocation 和 host/device copy 的元素数量。
- 仅供 generated source 或 `cuda_sm89::detail` 后端实现层内部使用，不进入公开 API。

使用示例:
- `unsigned long long elems = cuda_sm89::detail::element_count(slots[0]);`
*/
inline unsigned long long element_count(const ArgSlot &slot) {
  if (slot.shape == nullptr || slot.rank == 0) {
    return 0;
  }
  unsigned long long result = 1;
  for (unsigned long long idx = 0; idx < slot.rank; ++idx) {
    if (slot.shape[idx] <= 0) {
      return 0;
    }
    result *= static_cast<unsigned long long>(slot.shape[idx]);
  }
  return result;
}

/*
功能说明:
- 将 public `ArgSlot` 转成 generated source 内部 memory descriptor。
- descriptor 只保存指针和元数据引用，不拥有底层内存。
- 仅供 generated source 或 `cuda_sm89::detail` 后端实现层内部使用，不进入公开 API。

使用示例:
- `auto desc = cuda_sm89::detail::descriptor_from_slot(slots[0]);`
*/
inline MemoryDescriptor descriptor_from_slot(const ArgSlot &slot) {
  return MemoryDescriptor{slot.data, slot.shape, slot.stride, slot.rank, slot.dtype_code};
}

/*
功能说明:
- 将 runtime slot 绑定为 generated device body 可见的 `Memory<Space, T>` descriptor。
- slot 缺失或非 memory 时返回空 descriptor；调用方仍可通过 generated source 中的 wrapper call 暴露 operand 绑定。
- 仅供 generated source 或 `cuda_sm89::detail` 后端实现层内部使用，不进入公开 API。

使用示例:
- `auto arg0 = cuda_sm89::detail::memory_from_slot<MemorySpace::GM, float>(slots, count, 0);`
*/
template <MemorySpace Space, typename T>
__host__ __device__ Memory<Space, T> memory_from_slot(ArgSlot *slots, unsigned long long count, unsigned long long index) {
  if (slots == nullptr || index >= count || slots[index].kind != 1) {
    return Memory<Space, T>(nullptr, nullptr, nullptr, 0);
  }
  return Memory<Space, T>(reinterpret_cast<T *>(slots[index].data), slots[index].shape, slots[index].stride, slots[index].rank);
}

/*
功能说明:
- 为 TLM1 fragment alias 生成 descriptor glue，避免 generated source 对 fragment 发射 ordinary pointer-view API。
- shape/stride 由 final IR result type 发射；source 只提供 backing descriptor 与格式。
- 仅供 generated source 或 `cuda_sm89::detail` 后端实现层内部使用，不进入公开 API。

使用示例:
- `auto frag = cuda_sm89::detail::fragment_alias<MemorySpace::TLM1, float>(source, Vector{16}, Vector{1});`
*/
template <MemorySpace Space, typename T, MemorySpace SourceSpace, typename SourceT>
__device__ Memory<Space, T> fragment_alias(
    const Memory<SourceSpace, SourceT> &source,
    const Vector &offset,
    const Vector &shape,
    const Vector &stride) {
  long long linear_offset = 0;
  if (offset.size() == 1 && shape.size() > 1) {
    linear_offset = offset[0];
  } else {
    const unsigned long long rank = offset.size() < shape.size() ? offset.size() : shape.size();
    for (unsigned long long axis = 0; axis < rank && axis < source.rank(); ++axis) {
      linear_offset += offset[axis] * source.get_stride(axis);
    }
  }
  const SourceT *base = source.data();
  T *data = reinterpret_cast<T *>(const_cast<SourceT *>(base == nullptr ? nullptr : base + linear_offset));
  return Memory<Space, T>(data, shape.data(), stride.data(), shape.size(), source.format());
}

/*
功能说明:
- 将 memory descriptor 的 data pointer 转成 symbolic integer token，供 `memory.get_data` lowering 使用。
- TLM1 fragment 路径也只返回 token，不暴露普通 `.data()` 正向 wrapper 调用。
- 仅供 generated source 或 `cuda_sm89::detail` 后端实现层内部使用，不进入公开 API。

使用示例:
- `S_INT token = cuda_sm89::detail::memory_data_token(memory);`
*/
template <MemorySpace Space, typename T>
__device__ S_INT memory_data_token(const Memory<Space, T> &memory) {
  return reinterpret_cast<S_INT>(memory.data());
}

/*
功能说明:
- 构造 alias descriptor，用于 view / reinterpret / reshape 这类不复制数据的 final IR op。
- 调用方负责传入已计算好的 data 指针、shape、stride 和 rank。
- 仅供 generated source 或 `cuda_sm89::detail` 后端实现层内部使用，不进入公开 API。

使用示例:
- `auto alias = cuda_sm89::detail::alias_descriptor(base.data, shape, stride, 2, base.dtype_code);`
*/
inline MemoryDescriptor alias_descriptor(void *data, const long long *shape, const long long *stride, unsigned long long rank, int dtype_code) {
  return MemoryDescriptor{data, shape, stride, rank, dtype_code};
}

/*
功能说明:
- 按 descriptor shape 计算元素数量。
- rank 为 0、shape 为空或任一维非正时返回 0。
- 仅供 generated source 或 `cuda_sm89::detail` 后端实现层内部使用，不进入公开 API。

使用示例:
- `auto elems = cuda_sm89::detail::descriptor_element_count(desc);`
*/
inline unsigned long long descriptor_element_count(const MemoryDescriptor &desc) {
  if (desc.shape == nullptr || desc.rank == 0) {
    return 0;
  }
  unsigned long long result = 1;
  for (unsigned long long idx = 0; idx < desc.rank; ++idx) {
    if (desc.shape[idx] <= 0) {
      return 0;
    }
    result *= static_cast<unsigned long long>(desc.shape[idx]);
  }
  return result;
}


constexpr unsigned long long kCudaSm89MaxRank = 8;

template <typename MemoryT>
__device__ bool memory_ready(const MemoryT &memory) {
  return memory.data() != nullptr && memory.rank() > 0 && memory.rank() <= kCudaSm89MaxRank && memory.shape() != nullptr && memory.stride() != nullptr;
}

__device__ unsigned long long vector_element_count(const Vector &shape) {
  unsigned long long count = 1;
  for (unsigned long long axis = 0; axis < shape.size(); ++axis) {
    if (shape[axis] <= 0) {
      return 0;
    }
    count *= static_cast<unsigned long long>(shape[axis]);
  }
  return count;
}

template <typename MemoryT>
__device__ unsigned long long memory_element_count(const MemoryT &memory) {
  if (!memory_ready(memory)) {
    return 0;
  }
  unsigned long long count = 1;
  for (unsigned long long axis = 0; axis < memory.rank(); ++axis) {
    if (memory.get_shape(axis) <= 0) {
      return 0;
    }
    count *= static_cast<unsigned long long>(memory.get_shape(axis));
  }
  return count;
}

__device__ void linear_to_indices(unsigned long long linear, const Vector &shape, long long *indices) {
  for (unsigned long long reverse_axis = 0; reverse_axis < shape.size(); ++reverse_axis) {
    const unsigned long long axis = shape.size() - 1 - reverse_axis;
    const long long extent = shape[axis] <= 0 ? 1 : shape[axis];
    indices[axis] = static_cast<long long>(linear % static_cast<unsigned long long>(extent));
    linear /= static_cast<unsigned long long>(extent);
  }
}

__device__ void memory_linear_to_indices(unsigned long long linear, unsigned long long rank, const long long *shape, long long *indices) {
  for (unsigned long long reverse_axis = 0; reverse_axis < rank; ++reverse_axis) {
    const unsigned long long axis = rank - 1 - reverse_axis;
    const long long extent = shape[axis] <= 0 ? 1 : shape[axis];
    indices[axis] = static_cast<long long>(linear % static_cast<unsigned long long>(extent));
    linear /= static_cast<unsigned long long>(extent);
  }
}

template <typename T>
__device__ T *alloc_device_array(const Vector &shape) {
  const unsigned long long count = vector_element_count(shape);
  if (count == 0) {
    return nullptr;
  }
  T *data = new T[count];
  for (unsigned long long index = 0; index < count; ++index) {
    data[index] = T{};
  }
  return data;
}


}  // namespace detail
}  // namespace cuda_sm89

#endif  // KERNELCODE_GENERATE_INCLUDE_CUDA_SM89_MEMORY_H_
