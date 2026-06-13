/*
功能说明:
- 提供 cuda_sm86 后端 Arch 第一版实现层，承接 generated CUDA source 需要的 slot ABI、target wrapper 与 runtime helper。
- 该文件由 `include/cuda_sm86/cuda_sm86.cuh` 聚合引入；包外 Python API、工具参数和 `kg_execute_entry` ABI 不在本文件新增。
- 当前 generated device body 采用 thread0 完整执行语义；device helper 内部按完整 descriptor 遍历，避免片上 staging 被 thread 私有 partial allocation 切碎。

API 列表:
- `struct cuda_sm86::ArgSlot`
- `class cuda_sm86::KernelContext`
- `template <long long block, long long thread, long long subthread, long long shared_memory_size, auto name, typename Context, typename... Args> Status cuda_sm86::launch(Context& ctx, Args&&... args)`
- `__device__ S_INT cuda_sm86::block_id()`
- `__device__ S_INT cuda_sm86::thread_id()`
- `__device__ S_INT cuda_sm86::thread_num()`
- `__device__ void cuda_sm86::barrier()`
- `template <MemorySpace Space, typename T, typename Context> __device__ Memory<Space, T> cuda_sm86::alloc(Context& ctx, const Vector& shape, const Vector& stride, MemoryFormat format = MemoryFormat::Norm)`
- `template <MemorySpace Space, typename SlotT, typename BackingT> class cuda_sm86::DmaRing`
- `template <MemorySpace Space, typename SlotT, typename BackingT> __device__ cuda_sm86::DmaRing<Space, SlotT, BackingT>::DmaRing(Memory<Space, BackingT>& backing, S_INT num, S_INT offset_bytes, const Vector& shape, const Vector& stride, MemoryFormat format)`
- `template <MemorySpace Space, typename SlotT, typename BackingT> __device__ Memory<Space, SlotT> cuda_sm86::DmaRing<Space, SlotT, BackingT>::current() const`
- `template <MemorySpace Space, typename SlotT, typename BackingT> __device__ Memory<Space, SlotT> cuda_sm86::DmaRing<Space, SlotT, BackingT>::advance()`
- `template <typename SlotT, MemorySpace Space, typename BackingT> __device__ cuda_sm86::DmaRing<Space, SlotT, BackingT> cuda_sm86::make_ring(Memory<Space, BackingT>& backing, S_INT num, S_INT offset_bytes, std::initializer_list<long long> shape, std::initializer_list<long long> stride, MemoryFormat format = MemoryFormat::Norm)`
- `template <MemorySpace Space, typename T, typename Context> __device__ Status cuda_sm86::fill(Context& ctx, Memory<Space, T>& target, const T& value)`
- `template <MemorySpace TargetSpace, MemorySpace SourceSpace, typename T, typename Context> __device__ Status cuda_sm86::slice(Context& ctx, Memory<TargetSpace, T>& target, const Memory<SourceSpace, T>& source, const Vector& offset, const Vector& size, const Vector& stride)`
- `template <MemorySpace TargetSpace, MemorySpace SourceSpace, typename T, typename Context> __device__ Status cuda_sm86::deslice(Context& ctx, Memory<TargetSpace, T>& target, const Memory<SourceSpace, T>& source, const Vector& offset, const Vector& size, const Vector& stride)`
- `template <MemorySpace TargetSpace, MemorySpace SourceSpace, typename TargetType, typename SourceType, typename Context> __device__ Status cuda_sm86::load(Context& ctx, Memory<TargetSpace, TargetType>& target, const Memory<SourceSpace, SourceType>& source, const Vector& offset, const Vector& size, const Vector& stride)`
- `template <MemorySpace TargetSpace, MemorySpace SourceSpace, typename TargetType, typename SourceType, typename Context> __device__ Status cuda_sm86::store(Context& ctx, Memory<TargetSpace, TargetType>& target, const Memory<SourceSpace, SourceType>& source, const Vector& offset, const Vector& size, const Vector& stride)`
- `template <MemorySpace TargetSpace, MemorySpace SourceSpace, typename TargetType, typename SourceType, typename Context> __device__ Status cuda_sm86::transpose(Context& ctx, Memory<TargetSpace, TargetType>& target, const Memory<SourceSpace, SourceType>& source, const Vector& perm)`
- `template <MemorySpace TargetSpace, MemorySpace SourceSpace, typename TargetType, typename SourceType, typename Context> __device__ Status cuda_sm86::broadcast(Context& ctx, Memory<TargetSpace, TargetType>& target, const Memory<SourceSpace, SourceType>& source)`
- `template <MemorySpace Space, typename T> __host__ __device__ Memory<Space, T> cuda_sm86::view(const Memory<Space, T>& source, long long offset, long long size, long long stride)`
- `template <MemorySpace Space, typename InType, typename OutType, typename Context> __device__ Status cuda_sm86::add(Context& ctx, Memory<Space, OutType>& out, const Memory<Space, InType>& lhs, const Memory<Space, InType>& rhs)`
- `template <MemorySpace Space, typename InType, typename OutType, typename Context> __device__ Status cuda_sm86::sub(Context& ctx, Memory<Space, OutType>& out, const Memory<Space, InType>& lhs, const Memory<Space, InType>& rhs)`
- `template <MemorySpace Space, typename InType, typename OutType, typename Context> __device__ Status cuda_sm86::mul(Context& ctx, Memory<Space, OutType>& out, const Memory<Space, InType>& lhs, const Memory<Space, InType>& rhs)`
- `template <MemorySpace Space, typename InType, typename OutType, typename Context> __device__ Status cuda_sm86::truediv(Context& ctx, Memory<Space, OutType>& out, const Memory<Space, InType>& lhs, const Memory<Space, InType>& rhs)`
- `template <MemorySpace Space, typename InType, typename OutType, typename Context> __device__ Status cuda_sm86::max(Context& ctx, Memory<Space, OutType>& out, const Memory<Space, InType>& lhs, const Memory<Space, InType>& rhs)`
- `template <MemorySpace Space, typename InType, typename OutType, typename Context> __device__ Status cuda_sm86::exp(Context& ctx, Memory<Space, OutType>& out, const Memory<Space, InType>& input)`
- `template <MemorySpace Space, typename InType, typename OutType, typename Context> __device__ Status cuda_sm86::reduce_sum(Context& ctx, Memory<Space, OutType>& out, const Memory<Space, InType>& input, long long axis)`
- `template <MemorySpace Space, typename InType, typename OutType, typename Context> __device__ Status cuda_sm86::reduce_max(Context& ctx, Memory<Space, OutType>& out, const Memory<Space, InType>& input, long long axis)`
- `template <MemorySpace LhsSpace, MemorySpace RhsSpace, MemorySpace OutSpace, typename LhsType, typename RhsType, typename OutType, typename Context> __device__ Status cuda_sm86::matmul(Context& ctx, Memory<OutSpace, OutType>& out, const Memory<LhsSpace, LhsType>& lhs, const Memory<RhsSpace, RhsType>& rhs, bool acc = false)`
- `template <MemorySpace InputSpace, MemorySpace OutputSpace, typename InType, typename OutType, typename Context> __device__ Status cuda_sm86::img2col2d(Context& ctx, Memory<OutputSpace, OutType>& out, const Memory<InputSpace, InType>& input, long long kh, long long kw, long long sh, long long sw, long long dh, long long dw, long long ph, long long pw, long long pl, long long pr)`

helper 清单:
- `cuda_sm86::detail::*`：generated CUDA source 专用的 memory descriptor、alias/view、copy/fill/broadcast、math kernel helper、slot/scalar guard、host-device copy、device allocation、6D img2col2d、TF32 转换与 CUDA 错误检查。
- `KG_CUDA_CHECK(expr)`：generated CUDA source 内部使用的 CUDA runtime 检查宏。

使用示例:
- #include "include/cuda_sm86/cuda_sm86.cuh"
- extern "C" int kg_execute_entry(cuda_sm86::ArgSlot* slots, unsigned long long count);

关联文件:
- spec: spec/include/cuda_sm86/cuda_sm86.md
- 功能实现: include/cuda_sm86/cuda_sm86.cuh
- test: test/dsl/gen_kernel/emit/test_cuda_sm86_emit.py
*/

#ifndef KERNELCODE_GENERATE_INCLUDE_CUDA_SM86_ARCH_H_
#define KERNELCODE_GENERATE_INCLUDE_CUDA_SM86_ARCH_H_

#include <cuda_runtime.h>
#include <cmath>
#include <cstddef>
#include <cstdio>
#include <cstdlib>
#include <new>
#include <utility>

#ifndef KG_CUDA_SM86_HD
#define KG_CUDA_SM86_HD __host__ __device__
#endif

#ifndef KERNELCODE_GENERATE_INCLUDE_NPU_DEMO_CORE_H_
template <typename Pointer, typename>
KG_CUDA_SM86_HD inline Vector::Vector(Pointer data, unsigned long long size)
    : inline_data_{0, 0, 0, 0, 0, 0, 0, 0}, data_(data), size_(size) {}

KG_CUDA_SM86_HD inline Vector::Vector(long long value0)
    : inline_data_{value0, 0, 0, 0, 0, 0, 0, 0}, data_(inline_data_), size_(1) {}

KG_CUDA_SM86_HD inline Vector::Vector(long long value0, long long value1)
    : inline_data_{value0, value1, 0, 0, 0, 0, 0, 0}, data_(inline_data_), size_(2) {}

KG_CUDA_SM86_HD inline Vector::Vector(long long value0, long long value1, long long value2)
    : inline_data_{value0, value1, value2, 0, 0, 0, 0, 0}, data_(inline_data_), size_(3) {}

KG_CUDA_SM86_HD inline Vector::Vector(long long value0, long long value1, long long value2, long long value3)
    : inline_data_{value0, value1, value2, value3, 0, 0, 0, 0}, data_(inline_data_), size_(4) {}

KG_CUDA_SM86_HD inline Vector::Vector(long long value0, long long value1, long long value2, long long value3, long long value4)
    : inline_data_{value0, value1, value2, value3, value4, 0, 0, 0}, data_(inline_data_), size_(5) {}

KG_CUDA_SM86_HD inline Vector::Vector(
    long long value0,
    long long value1,
    long long value2,
    long long value3,
    long long value4,
    long long value5)
    : inline_data_{value0, value1, value2, value3, value4, value5, 0, 0}, data_(inline_data_), size_(6) {}

KG_CUDA_SM86_HD inline Vector::Vector(
    long long value0,
    long long value1,
    long long value2,
    long long value3,
    long long value4,
    long long value5,
    long long value6)
    : inline_data_{value0, value1, value2, value3, value4, value5, value6, 0}, data_(inline_data_), size_(7) {}

KG_CUDA_SM86_HD inline Vector::Vector(
    long long value0,
    long long value1,
    long long value2,
    long long value3,
    long long value4,
    long long value5,
    long long value6,
    long long value7)
    : inline_data_{value0, value1, value2, value3, value4, value5, value6, value7}, data_(inline_data_), size_(8) {}

KG_CUDA_SM86_HD inline Vector::Vector(const Vector &other)
    : inline_data_{
          other.inline_data_[0],
          other.inline_data_[1],
          other.inline_data_[2],
          other.inline_data_[3],
          other.inline_data_[4],
          other.inline_data_[5],
          other.inline_data_[6],
          other.inline_data_[7]},
      data_(other.data_ == other.inline_data_ ? inline_data_ : other.data_),
      size_(other.size_) {}

KG_CUDA_SM86_HD inline Vector &Vector::operator=(const Vector &other) {
  if (this == &other) {
    return *this;
  }
  for (unsigned long long index = 0; index < 8; ++index) {
    inline_data_[index] = other.inline_data_[index];
  }
  data_ = other.data_ == other.inline_data_ ? inline_data_ : other.data_;
  size_ = other.size_;
  return *this;
}

KG_CUDA_SM86_HD inline unsigned long long Vector::size() const {
  return size_;
}

KG_CUDA_SM86_HD inline long long *Vector::data() {
  return const_cast<long long *>(data_);
}

KG_CUDA_SM86_HD inline const long long *Vector::data() const {
  return data_;
}

KG_CUDA_SM86_HD inline long long &Vector::operator[](unsigned long long index) {
  return const_cast<long long *>(data_)[index];
}

KG_CUDA_SM86_HD inline const long long &Vector::operator[](unsigned long long index) const {
  return data_[index];
}
#endif

#ifndef KERNELCODE_GENERATE_INCLUDE_NPU_DEMO_MEMORY_H_
namespace npu_demo {
KG_CUDA_SM86_HD inline void build_contiguous_stride(const long long *shape, unsigned long long rank, long long *out_stride) {
  long long current = 1;
  for (unsigned long long reverse_index = 0; reverse_index < rank; ++reverse_index) {
    const unsigned long long axis = rank - 1 - reverse_index;
    out_stride[axis] = current;
    current *= shape[axis];
  }
}
}  // namespace npu_demo

template <MemorySpace Space, typename T>
KG_CUDA_SM86_HD inline Memory<Space, T>::Memory(T *data, const long long *shape, const long long *stride, unsigned long long rank, MemoryFormat format)
    : data_(data), rank_(0), format_(format) {
  init_shape_and_stride(rank, shape, stride);
}

template <MemorySpace Space, typename T>
KG_CUDA_SM86_HD inline Memory<Space, T>::Memory(T *data, const long long *shape, unsigned long long rank, MemoryFormat format)
    : data_(data), rank_(0), format_(format) {
  init_shape_and_stride(rank, shape, nullptr);
}

template <MemorySpace Space, typename T>
KG_CUDA_SM86_HD inline Memory<Space, T>::Memory(T *data, std::initializer_list<long long> shape, std::initializer_list<long long> stride, MemoryFormat format)
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
KG_CUDA_SM86_HD inline Memory<Space, T>::Memory(T *data, std::initializer_list<long long> shape, MemoryFormat format)
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
KG_CUDA_SM86_HD inline T *Memory<Space, T>::data() {
  return data_;
}

template <MemorySpace Space, typename T>
KG_CUDA_SM86_HD inline const T *Memory<Space, T>::data() const {
  return data_;
}

template <MemorySpace Space, typename T>
KG_CUDA_SM86_HD inline const long long *Memory<Space, T>::shape() const {
  return shape_;
}

template <MemorySpace Space, typename T>
KG_CUDA_SM86_HD inline const long long *Memory<Space, T>::stride() const {
  return stride_;
}

template <MemorySpace Space, typename T>
KG_CUDA_SM86_HD inline unsigned long long Memory<Space, T>::rank() const {
  return rank_;
}

template <MemorySpace Space, typename T>
KG_CUDA_SM86_HD inline MemoryFormat Memory<Space, T>::format() const {
  return format_;
}

template <MemorySpace Space, typename T>
KG_CUDA_SM86_HD inline MemorySpace Memory<Space, T>::space() const {
  return Space;
}

template <MemorySpace Space, typename T>
KG_CUDA_SM86_HD inline long long Memory<Space, T>::get_shape(unsigned long long axis) const {
  return shape_[axis];
}

template <MemorySpace Space, typename T>
KG_CUDA_SM86_HD inline long long Memory<Space, T>::get_stride(unsigned long long axis) const {
  return stride_[axis];
}

template <MemorySpace Space, typename T>
template <typename ViewT>
KG_CUDA_SM86_HD inline Memory<Space, ViewT> Memory<Space, T>::view(const Vector &offset, const Vector &size, const Vector &stride) const {
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
KG_CUDA_SM86_HD inline Memory<Space, ViewT> Memory<Space, T>::view(
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
KG_CUDA_SM86_HD inline Memory<Space, T> Memory<Space, T>::reshape(const Vector &shape) const {
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
KG_CUDA_SM86_HD inline Memory<Space, T> Memory<Space, T>::reshape(std::initializer_list<long long> shape) const {
  long long shape_buf[kMaxDim] = {0};
  unsigned long long rank = 0;
  auto shape_it = shape.begin();
  for (; rank < shape.size() && rank < kMaxDim; ++rank, ++shape_it) {
    shape_buf[rank] = *shape_it;
  }
  return reshape(Vector(shape_buf, rank == 0 ? 1 : rank));
}

template <MemorySpace Space, typename T>
KG_CUDA_SM86_HD inline long long Memory<Space, T>::element_count() const {
  long long count = 1;
  for (unsigned long long axis = 0; axis < rank_; ++axis) {
    count *= shape_[axis];
  }
  return count;
}

template <MemorySpace Space, typename T>
KG_CUDA_SM86_HD inline bool Memory<Space, T>::is_contiguous() const {
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
KG_CUDA_SM86_HD inline long long Memory<Space, T>::linear_offset(const long long *indices) const {
  long long offset = 0;
  for (unsigned long long axis = 0; axis < rank_; ++axis) {
    offset += indices[axis] * stride_[axis];
  }
  return offset;
}

template <MemorySpace Space, typename T>
KG_CUDA_SM86_HD inline T &Memory<Space, T>::at(const long long *indices) {
  return data_[linear_offset(indices)];
}

template <MemorySpace Space, typename T>
KG_CUDA_SM86_HD inline const T &Memory<Space, T>::at(const long long *indices) const {
  return data_[linear_offset(indices)];
}

template <MemorySpace Space, typename T>
KG_CUDA_SM86_HD inline void Memory<Space, T>::contract_or_trap(bool condition) {
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
KG_CUDA_SM86_HD inline void Memory<Space, T>::init_shape_and_stride(unsigned long long rank, const long long *shape, const long long *stride) {
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
KG_CUDA_SM86_HD inline void Memory<Space, T>::fill_contiguous_stride() {
  long long current = 1;
  for (unsigned long long reverse_index = 0; reverse_index < rank_; ++reverse_index) {
    const unsigned long long axis = rank_ - 1 - reverse_index;
    stride_[axis] = current;
    current *= shape_[axis];
  }
}
#endif

namespace cuda_sm86 {

struct ArgSlot {
  int kind;
  void *data;
  long long *shape;
  long long *stride;
  unsigned long long rank;
  int dtype_code;
  long long int_value;
  double float_value;
};

/*
功能说明:
- 表示 generated CUDA device body 内显式传递的 opaque context。
- public class 不公开成员 API；设备侧状态和低层 helper 留在 generated glue 或 `cuda_sm86::detail`。

使用示例:
- `cuda_sm86::KernelContext ctx;`
*/
class KernelContext {
public:
  __host__ __device__ KernelContext() = default;
};

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
- 将 CUDA runtime API 返回值统一转换为 generated source 的稳定失败语义。
- 成功时直接返回；失败时输出 `cuda_runtime_failed`、CUDA 错误文本、调用位置和表达式后终止进程。
- 仅供 generated source 或 `cuda_sm86::detail` 后端实现层内部使用，不进入公开 API。

使用示例:
- `cuda_sm86::detail::check_cuda(cudaGetLastError(), "cudaGetLastError()", __FILE__, __LINE__);`
*/
inline void check_cuda(cudaError_t status, const char *expr, const char *file, int line) {
  if (status == cudaSuccess) {
    return;
  }
  std::fprintf(stderr, "cuda_runtime_failed: %s at %s:%d for %s\n", cudaGetErrorString(status), file, line, expr);
  std::abort();
}

/*
功能说明:
- 为 generated source 内部调用 CUDA runtime API 提供简短检查入口。
- 宏只转发到 `cuda_sm86::detail::check_cuda`，不承载业务 kernel launch 或公开 API 语义。
- 仅供 generated source 或 `cuda_sm86::detail` 后端实现层内部使用，不进入公开 API。

使用示例:
- `KG_CUDA_CHECK(cudaGetLastError());`
*/
#define KG_CUDA_CHECK(expr) ::cuda_sm86::detail::check_cuda((expr), #expr, __FILE__, __LINE__)

/*
功能说明:
- 判断指定 slot 是否是 rank 匹配的 f32 memory 参数。
- generated source 用它在读取 memory slot 前校验 kind、dtype、rank、shape 和 stride 指针。
- 仅供 generated source 或 `cuda_sm86::detail` 后端实现层内部使用，不进入公开 API。

使用示例:
- `if (!cuda_sm86::detail::is_f32_memory(slots, count, 0, 2)) { return -1; }`
*/
inline bool is_f32_memory(const ArgSlot *slots, unsigned long long count, unsigned long long index, unsigned long long rank) {
  return slots != nullptr && index < count && slots[index].kind == 1 && slots[index].dtype_code == 1 && slots[index].rank == rank &&
         slots[index].shape != nullptr && slots[index].stride != nullptr;
}

/*
功能说明:
- 判断指定 slot 是否是带非空 data 指针的 memory 参数。
- generated source 用它区分可拷贝 memory 与缺失或非 memory slot。
- 仅供 generated source 或 `cuda_sm86::detail` 后端实现层内部使用，不进入公开 API。

使用示例:
- `if (!cuda_sm86::detail::has_memory_data(slots, count, 1)) { return -1; }`
*/
inline bool has_memory_data(const ArgSlot *slots, unsigned long long count, unsigned long long index) {
  return slots != nullptr && index < count && slots[index].kind == 1 && slots[index].data != nullptr;
}

/*
功能说明:
- 判断指定 slot 是否是整数标量参数。
- generated source 用它读取 runtime shape、stride 或 tile 相关整数参数前做 slot kind 校验。
- 仅供 generated source 或 `cuda_sm86::detail` 后端实现层内部使用，不进入公开 API。

使用示例:
- `if (!cuda_sm86::detail::has_int_arg(slots, count, 3)) { return -1; }`
*/
KG_CUDA_SM86_HD inline bool has_int_arg(const ArgSlot *slots, unsigned long long count, unsigned long long index) {
  return slots != nullptr && index < count && slots[index].kind == 2;
}

/*
功能说明:
- 读取整数标量 slot；slot 缺失或 kind 不匹配时返回调用方给定默认值。
- generated source 用它处理可选 runtime 参数，避免把缺省值逻辑散落在各 kernel wrapper 中。
- 仅供 generated source 或 `cuda_sm86::detail` 后端实现层内部使用，不进入公开 API。

使用示例:
- `long long stride = cuda_sm86::detail::int_arg_or(slots, count, 4, 1);`
*/
KG_CUDA_SM86_HD inline long long int_arg_or(const ArgSlot *slots, unsigned long long count, unsigned long long index, long long default_value) {
  if (!has_int_arg(slots, count, index)) {
    return default_value;
  }
  return slots[index].int_value;
}

/*
功能说明:
- 根据 memory slot 的 shape 计算元素总数；rank 为 0、shape 为空或任一维非正时返回 0。
- generated source 用它确定 device allocation 和 host/device copy 的元素数量。
- 仅供 generated source 或 `cuda_sm86::detail` 后端实现层内部使用，不进入公开 API。

使用示例:
- `unsigned long long elems = cuda_sm86::detail::element_count(slots[0]);`
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
- 仅供 generated source 或 `cuda_sm86::detail` 后端实现层内部使用，不进入公开 API。

使用示例:
- `auto desc = cuda_sm86::detail::descriptor_from_slot(slots[0]);`
*/
inline MemoryDescriptor descriptor_from_slot(const ArgSlot &slot) {
  return MemoryDescriptor{slot.data, slot.shape, slot.stride, slot.rank, slot.dtype_code};
}

/*
功能说明:
- 将 runtime slot 绑定为 generated device body 可见的 `Memory<Space, T>` descriptor。
- slot 缺失或非 memory 时返回空 descriptor；调用方仍可通过 generated source 中的 wrapper call 暴露 operand 绑定。
- 仅供 generated source 或 `cuda_sm86::detail` 后端实现层内部使用，不进入公开 API。

使用示例:
- `auto arg0 = cuda_sm86::detail::memory_from_slot<MemorySpace::GM, float>(slots, count, 0);`
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
- 仅供 generated source 或 `cuda_sm86::detail` 后端实现层内部使用，不进入公开 API。

使用示例:
- `auto frag = cuda_sm86::detail::fragment_alias<MemorySpace::TLM1, float>(source, Vector{16}, Vector{1});`
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
- 仅供 generated source 或 `cuda_sm86::detail` 后端实现层内部使用，不进入公开 API。

使用示例:
- `S_INT token = cuda_sm86::detail::memory_data_token(memory);`
*/
template <MemorySpace Space, typename T>
__device__ S_INT memory_data_token(const Memory<Space, T> &memory) {
  return reinterpret_cast<S_INT>(memory.data());
}

/*
功能说明:
- 构造 alias descriptor，用于 view / reinterpret / reshape 这类不复制数据的 final IR op。
- 调用方负责传入已计算好的 data 指针、shape、stride 和 rank。
- 仅供 generated source 或 `cuda_sm86::detail` 后端实现层内部使用，不进入公开 API。

使用示例:
- `auto alias = cuda_sm86::detail::alias_descriptor(base.data, shape, stride, 2, base.dtype_code);`
*/
inline MemoryDescriptor alias_descriptor(void *data, const long long *shape, const long long *stride, unsigned long long rank, int dtype_code) {
  return MemoryDescriptor{data, shape, stride, rank, dtype_code};
}

/*
功能说明:
- 按 descriptor shape 计算元素数量。
- rank 为 0、shape 为空或任一维非正时返回 0。
- 仅供 generated source 或 `cuda_sm86::detail` 后端实现层内部使用，不进入公开 API。

使用示例:
- `auto elems = cuda_sm86::detail::descriptor_element_count(desc);`
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

/*
功能说明:
- device 侧连续 copy helper，服务 `dma.copy` materialization。
- 调用方负责保证 source/target 至少包含 `element_count` 个元素。
- 仅供 generated source 或 `cuda_sm86::detail` 后端实现层内部使用，不进入公开 API。

使用示例:
- `cuda_sm86::detail::copy_contiguous(dst, src, count);`
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
- 仅供 generated source 或 `cuda_sm86::detail` 后端实现层内部使用，不进入公开 API。

使用示例:
- `cuda_sm86::detail::fill_contiguous(dst, 0.0f, count);`
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
- 仅供 generated source 或 `cuda_sm86::detail` 后端实现层内部使用，不进入公开 API。

使用示例:
- `cuda_sm86::detail::broadcast_row_vector(dst, src, rows, cols);`
*/
template <typename T>
__device__ void broadcast_row_vector(T *target, const T *source, unsigned long long rows, unsigned long long cols) {
  const unsigned long long total = rows * cols;
  for (unsigned long long index = 0; index < total; ++index) {
    target[index] = source[index % cols];
  }
}

/*
功能说明:
- device 侧 binary elewise helper，服务 `kernel.binary_elewise` 支持的 add/sub/mul/truediv/max。
- `kind` 取值由 generated source 静态生成，unsupported kind 不应调用本 helper。
- 仅供 generated source 或 `cuda_sm86::detail` 后端实现层内部使用，不进入公开 API。

使用示例:
- `auto value = cuda_sm86::detail::binary_value(lhs, rhs, 0);`
*/
__device__ __forceinline__ float binary_value(float lhs, float rhs, int kind) {
  if (kind == 0) {
    return lhs + rhs;
  }
  if (kind == 1) {
    return lhs - rhs;
  }
  if (kind == 2) {
    return lhs * rhs;
  }
  if (kind == 3) {
    return lhs / rhs;
  }
  return lhs > rhs ? lhs : rhs;
}

/*
功能说明:
- 为 generated source 按元素数量分配 CUDA device buffer。
- 元素数量为 0 时返回 `nullptr`；CUDA runtime 失败时通过 `KG_CUDA_CHECK` 终止。
- 仅供 generated source 或 `cuda_sm86::detail` 后端实现层内部使用，不进入公开 API。

使用示例:
- `float *device = cuda_sm86::detail::device_alloc<float>(element_count);`
*/
template <typename T>
T *device_alloc(unsigned long long element_count) {
  if (element_count == 0) {
    return nullptr;
  }
  T *device_ptr = nullptr;
  KG_CUDA_CHECK(cudaMalloc(&device_ptr, static_cast<std::size_t>(element_count) * sizeof(T)));
  return device_ptr;
}

/*
功能说明:
- 将 host buffer 拷贝到 CUDA device buffer。
- 元素数量为 0 时不调用 CUDA runtime；否则按 `sizeof(T)` 计算字节数并检查 copy 结果。
- 仅供 generated source 或 `cuda_sm86::detail` 后端实现层内部使用，不进入公开 API。

使用示例:
- `cuda_sm86::detail::copy_host_to_device(device_ptr, host_ptr, element_count);`
*/
template <typename T>
void copy_host_to_device(T *device_ptr, const T *host_ptr, unsigned long long element_count) {
  if (element_count == 0) {
    return;
  }
  KG_CUDA_CHECK(cudaMemcpy(device_ptr, host_ptr, static_cast<std::size_t>(element_count) * sizeof(T), cudaMemcpyHostToDevice));
}

/*
功能说明:
- 将 CUDA device buffer 拷贝回 host buffer。
- 元素数量为 0 时不调用 CUDA runtime；否则按 `sizeof(T)` 计算字节数并检查 copy 结果。
- 仅供 generated source 或 `cuda_sm86::detail` 后端实现层内部使用，不进入公开 API。

使用示例:
- `cuda_sm86::detail::copy_device_to_host(host_ptr, device_ptr, element_count);`
*/
template <typename T>
void copy_device_to_host(T *host_ptr, const T *device_ptr, unsigned long long element_count) {
  if (element_count == 0) {
    return;
  }
  KG_CUDA_CHECK(cudaMemcpy(host_ptr, device_ptr, static_cast<std::size_t>(element_count) * sizeof(T), cudaMemcpyDeviceToHost));
}

/*
功能说明:
- 释放 generated source 内部持有的 CUDA device buffer。
- 指针为空时不调用 CUDA runtime；非空时通过 `KG_CUDA_CHECK` 检查释放结果。
- 仅供 generated source 或 `cuda_sm86::detail` 后端实现层内部使用，不进入公开 API。

使用示例:
- `cuda_sm86::detail::device_free(device_ptr);`
*/
template <typename T>
void device_free(T *device_ptr) {
  if (device_ptr != nullptr) {
    KG_CUDA_CHECK(cudaFree(device_ptr));
  }
}

/*
功能说明:
- 在 SM80 及以上 device code 中把 f32 值转换为 TF32 指令输入位型。
- 非支持架构编译路径返回 0，仅用于保持 host/device 编译可通过，不作为运行时数值路径。
- 仅供 generated source 或 `cuda_sm86::detail` 后端实现层内部使用，不进入公开 API。

使用示例:
- `unsigned tf32_bits = cuda_sm86::detail::to_tf32(value);`
*/
__device__ __forceinline__ unsigned to_tf32(float value) {
  unsigned out;
#if defined(__CUDA_ARCH__) && (__CUDA_ARCH__ >= 800)
  asm volatile("cvt.rna.tf32.f32 %0, %1;" : "=r"(out) : "f"(value));
#else
  out = 0;
#endif
  return out;
}

constexpr unsigned long long kCudaSm86MaxRank = 8;
constexpr unsigned long long kCudaSm86MmaK = 8;
constexpr unsigned long long kCudaSm86MmaObservableRows = 2;
constexpr unsigned long long kCudaSm86MmaObservableCols = 2;

template <typename MemoryT>
__device__ bool memory_ready(const MemoryT &memory) {
  return memory.data() != nullptr && memory.rank() > 0 && memory.rank() <= kCudaSm86MaxRank && memory.shape() != nullptr && memory.stride() != nullptr;
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

template <typename MemoryT, typename ValueT>
__device__ Status fill_memory(MemoryT &target, const ValueT &value) {
  if (!memory_ready(target)) {
    return kError;
  }
  const unsigned long long count = memory_element_count(target);
  for (unsigned long long index = 0; index < count; ++index) {
    long long target_indices[kCudaSm86MaxRank] = {0};
    memory_linear_to_indices(index, target.rank(), target.shape(), target_indices);
    target.at(target_indices) = static_cast<ValueT>(value);
  }
  return kOk;
}

template <typename TargetMemory, typename SourceMemory>
__device__ Status copy_from_source_window(TargetMemory &target, const SourceMemory &source, const Vector &offset, const Vector &size, const Vector &stride) {
  if (!memory_ready(target) || !memory_ready(source) || size.size() == 0 || size.size() > kCudaSm86MaxRank) {
    return kError;
  }
  const unsigned long long rank = size.size();
  const unsigned long long count = vector_element_count(size);
  for (unsigned long long index = 0; index < count; ++index) {
    long long logical[kCudaSm86MaxRank] = {0};
    long long source_indices[kCudaSm86MaxRank] = {0};
    long long target_indices[kCudaSm86MaxRank] = {0};
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
  if (!memory_ready(target) || !memory_ready(source) || size.size() == 0 || size.size() > kCudaSm86MaxRank) {
    return kError;
  }
  const unsigned long long rank = size.size();
  const unsigned long long count = vector_element_count(size);
  for (unsigned long long index = 0; index < count; ++index) {
    long long logical[kCudaSm86MaxRank] = {0};
    long long source_indices[kCudaSm86MaxRank] = {0};
    long long target_indices[kCudaSm86MaxRank] = {0};
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

template <typename OutMemory, typename LhsMemory, typename RhsMemory>
__device__ Status binary_memory(OutMemory &out, const LhsMemory &lhs, const RhsMemory &rhs, int kind) {
  if (!memory_ready(out) || !memory_ready(lhs) || !memory_ready(rhs)) {
    return kError;
  }
  const unsigned long long count = memory_element_count(out);
  for (unsigned long long index = 0; index < count; ++index) {
    long long indices[kCudaSm86MaxRank] = {0};
    memory_linear_to_indices(index, out.rank(), out.shape(), indices);
    out.at(indices) = binary_value(static_cast<float>(lhs.at(indices)), static_cast<float>(rhs.at(indices)), kind);
  }
  return kOk;
}

template <typename OutMemory, typename InMemory>
__device__ Status exp_memory(OutMemory &out, const InMemory &input) {
  if (!memory_ready(out) || !memory_ready(input)) {
    return kError;
  }
  const unsigned long long count = memory_element_count(out);
  for (unsigned long long index = 0; index < count; ++index) {
    long long indices[kCudaSm86MaxRank] = {0};
    memory_linear_to_indices(index, out.rank(), out.shape(), indices);
    out.at(indices) = expf(static_cast<float>(input.at(indices)));
  }
  return kOk;
}

template <typename OutMemory, typename InMemory>
__device__ Status reduce_memory(OutMemory &out, const InMemory &input, long long axis, bool take_max) {
  if (!memory_ready(out) || !memory_ready(input) || axis < 0 || static_cast<unsigned long long>(axis) >= input.rank()) {
    return kError;
  }
  const unsigned long long count = memory_element_count(out);
  for (unsigned long long index = 0; index < count; ++index) {
    long long out_indices[kCudaSm86MaxRank] = {0};
    long long input_indices[kCudaSm86MaxRank] = {0};
    memory_linear_to_indices(index, out.rank(), out.shape(), out_indices);
    for (unsigned long long out_axis = 0, in_axis = 0; in_axis < input.rank(); ++in_axis) {
      if (in_axis == static_cast<unsigned long long>(axis)) {
        input_indices[in_axis] = 0;
      } else {
        input_indices[in_axis] = out_axis < out.rank() ? out_indices[out_axis++] : 0;
      }
    }
    float acc = take_max ? -3.4028234663852886e38f : 0.0f;
    for (long long reduce_index = 0; reduce_index < input.get_shape(static_cast<unsigned long long>(axis)); ++reduce_index) {
      input_indices[axis] = reduce_index;
      const float value = static_cast<float>(input.at(input_indices));
      acc = take_max ? (acc > value ? acc : value) : (acc + value);
    }
    out.at(out_indices) = acc;
  }
  return kOk;
}

template <typename TargetMemory, typename SourceMemory>
__device__ Status transpose_memory(TargetMemory &target, const SourceMemory &source, const Vector &perm) {
  if (!memory_ready(target) || !memory_ready(source) || target.rank() != source.rank() || perm.size() != source.rank()) {
    return kError;
  }
  bool seen[kCudaSm86MaxRank] = {false};
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
    long long target_indices[kCudaSm86MaxRank] = {0};
    long long source_indices[kCudaSm86MaxRank] = {0};
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
    long long target_indices[kCudaSm86MaxRank] = {0};
    long long source_indices[kCudaSm86MaxRank] = {0};
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

template <typename OutMemory, typename InMemory>
__device__ Status img2col2d_memory(
    OutMemory &out,
    const InMemory &input,
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
  if (!memory_ready(out) || !memory_ready(input) || input.rank() != 4 || (out.rank() != 2 && out.rank() != 6)) {
    return kError;
  }
  const long long batches = input.get_shape(0);
  const long long channels = input.get_shape(1);
  const long long height = input.get_shape(2);
  const long long width = input.get_shape(3);
  const long long out_h = (height + ph + pw - dh * (kh - 1) - 1) / sh + 1;
  const long long out_w = (width + pl + pr - dw * (kw - 1) - 1) / sw + 1;
  const unsigned long long count = memory_element_count(out);
  for (unsigned long long index = 0; index < count; ++index) {
    long long out_indices[kCudaSm86MaxRank] = {0};
    long long input_indices[kCudaSm86MaxRank] = {0};
    memory_linear_to_indices(index, out.rank(), out.shape(), out_indices);
    long long n = 0;
    long long c = 0;
    long long kr = 0;
    long long kc = 0;
    long long oh = 0;
    long long ow = 0;
    if (out.rank() == 6) {
      n = out_indices[0];
      c = out_indices[1];
      kr = out_indices[2];
      kc = out_indices[3];
      oh = out_indices[4];
      ow = out_indices[5];
    } else {
      const long long row = out_indices[0];
      const long long col = out_indices[1];
      const long long spatial = row % (out_h * out_w);
      n = row / (out_h * out_w);
      oh = spatial / out_w;
      ow = spatial % out_w;
      c = col / (kh * kw);
      const long long filter = col % (kh * kw);
      kr = filter / kw;
      kc = filter % kw;
    }
    const long long ih = oh * sh + kr * dh - ph;
    const long long iw = ow * sw + kc * dw - pl;
    float value = 0.0f;
    if (n >= 0 && n < batches && c >= 0 && c < channels && ih >= 0 && ih < height && iw >= 0 && iw < width) {
      input_indices[0] = n;
      input_indices[1] = c;
      input_indices[2] = ih;
      input_indices[3] = iw;
      value = static_cast<float>(input.at(input_indices));
    }
    out.at(out_indices) = value;
  }
  return kOk;
}

template <typename OutMemory, typename LhsMemory, typename RhsMemory>
__device__ bool tensor_core_matmul_path(OutMemory &out, const LhsMemory &lhs, const RhsMemory &rhs, bool acc) {
#if defined(__CUDA_ARCH__) && (__CUDA_ARCH__ >= 800)
  if (!memory_ready(out) || !memory_ready(lhs) || !memory_ready(rhs) || lhs.rank() < 2 || rhs.rank() < 2 || out.rank() < 2) {
    return false;
  }
  const long long lhs_rows = lhs.get_shape(lhs.rank() - 2);
  const long long lhs_depth = lhs.get_shape(lhs.rank() - 1);
  const long long rhs_depth = rhs.get_shape(rhs.rank() - 2);
  const long long rhs_cols = rhs.get_shape(rhs.rank() - 1);
  const long long out_rows = out.get_shape(out.rank() - 2);
  const long long out_cols = out.get_shape(out.rank() - 1);
  if (lhs_rows <= 0 || lhs_depth <= 0 || rhs_depth <= 0 || rhs_cols <= 0 || out_rows <= 0 || out_cols <= 0) {
    return false;
  }
  __shared__ float kg_cuda_sm86_mma_a[16 * kCudaSm86MmaK];
  __shared__ float kg_cuda_sm86_mma_b[kCudaSm86MmaK * 8];
  for (unsigned long long index = 0; index < 16ull * kCudaSm86MmaK; ++index) {
    const long long m = static_cast<long long>(index / kCudaSm86MmaK);
    const long long k = static_cast<long long>(index % kCudaSm86MmaK);
    long long lhs_indices[kCudaSm86MaxRank] = {0};
    lhs_indices[lhs.rank() - 2] = m;
    lhs_indices[lhs.rank() - 1] = k;
    kg_cuda_sm86_mma_a[index] = (m < lhs_rows && k < lhs_depth) ? static_cast<float>(lhs.at(lhs_indices)) : 0.0f;
  }
  for (unsigned long long index = 0; index < kCudaSm86MmaK * 8ull; ++index) {
    const long long k = static_cast<long long>(index / 8ull);
    const long long n = static_cast<long long>(index % 8ull);
    long long rhs_indices[kCudaSm86MaxRank] = {0};
    rhs_indices[rhs.rank() - 2] = k;
    rhs_indices[rhs.rank() - 1] = n;
    kg_cuda_sm86_mma_b[index] = (k < rhs_depth && n < rhs_cols) ? static_cast<float>(rhs.at(rhs_indices)) : 0.0f;
  }
  long long out_indices[kCudaSm86MaxRank] = {0};
  out_indices[out.rank() - 2] = 0;
  out_indices[out.rank() - 1] = 0;
  float mma_c0 = (acc && out_rows > 0 && out_cols > 0) ? static_cast<float>(out.at(out_indices)) : 0.0f;
  out_indices[out.rank() - 2] = 0;
  out_indices[out.rank() - 1] = 1;
  float mma_c1 = (acc && out_rows > 0 && out_cols > 1) ? static_cast<float>(out.at(out_indices)) : 0.0f;
  out_indices[out.rank() - 2] = 1;
  out_indices[out.rank() - 1] = 0;
  float mma_c2 = (acc && out_rows > 1 && out_cols > 0) ? static_cast<float>(out.at(out_indices)) : 0.0f;
  out_indices[out.rank() - 2] = 1;
  out_indices[out.rank() - 1] = 1;
  float mma_c3 = (acc && out_rows > 1 && out_cols > 1) ? static_cast<float>(out.at(out_indices)) : 0.0f;
  float mma_d0 = 0.0f;
  float mma_d1 = 0.0f;
  float mma_d2 = 0.0f;
  float mma_d3 = 0.0f;
  const unsigned mma_a0 = to_tf32(kg_cuda_sm86_mma_a[0]);
  const unsigned mma_a1 = to_tf32(kg_cuda_sm86_mma_a[1]);
  const unsigned mma_a2 = to_tf32(kg_cuda_sm86_mma_a[8]);
  const unsigned mma_a3 = to_tf32(kg_cuda_sm86_mma_a[9]);
  const unsigned mma_b0 = to_tf32(kg_cuda_sm86_mma_b[0]);
  const unsigned mma_b1 = to_tf32(kg_cuda_sm86_mma_b[1]);
  asm volatile(
      "mma.sync.aligned.m16n8k8.row.col.f32.tf32.tf32.f32 "
      "{%0, %1, %2, %3}, {%4, %5, %6, %7}, {%8, %9}, {%10, %11, %12, %13};"
      : "=f"(mma_d0), "=f"(mma_d1), "=f"(mma_d2), "=f"(mma_d3)
      : "r"(mma_a0),
        "r"(mma_a1),
        "r"(mma_a2),
        "r"(mma_a3),
        "r"(mma_b0),
        "r"(mma_b1),
        "f"(mma_c0),
        "f"(mma_c1),
        "f"(mma_c2),
        "f"(mma_c3));
  out_indices[out.rank() - 2] = 0;
  out_indices[out.rank() - 1] = 0;
  if (out_rows > 0 && out_cols > 0) {
    out.at(out_indices) = mma_d0;
  }
  out_indices[out.rank() - 2] = 0;
  out_indices[out.rank() - 1] = 1;
  if (out_rows > 0 && out_cols > 1) {
    out.at(out_indices) = mma_d1;
  }
  out_indices[out.rank() - 2] = 1;
  out_indices[out.rank() - 1] = 0;
  if (out_rows > 1 && out_cols > 0) {
    out.at(out_indices) = mma_d2;
  }
  out_indices[out.rank() - 2] = 1;
  out_indices[out.rank() - 1] = 1;
  if (out_rows > 1 && out_cols > 1) {
    out.at(out_indices) = mma_d3;
  }
  return true;
#else
  (void)out;
  (void)lhs;
  (void)rhs;
  (void)acc;
  return false;
#endif
}

template <typename OutMemory, typename LhsMemory, typename RhsMemory>
__device__ Status matmul_memory(OutMemory &out, const LhsMemory &lhs, const RhsMemory &rhs, bool acc) {
  if (!memory_ready(out) || !memory_ready(lhs) || !memory_ready(rhs) || out.rank() < 2 || lhs.rank() < 2 || rhs.rank() < 2) {
    return kError;
  }
  const long long rows_value = out.get_shape(out.rank() - 2);
  const long long cols_value = out.get_shape(out.rank() - 1);
  const long long depth_value = lhs.get_shape(lhs.rank() - 1);
  if (rows_value <= 0 || cols_value <= 0 || depth_value <= 0 || lhs.get_shape(lhs.rank() - 2) != rows_value ||
      rhs.get_shape(rhs.rank() - 2) != depth_value || rhs.get_shape(rhs.rank() - 1) != cols_value) {
    return kError;
  }
  const unsigned long long rows = static_cast<unsigned long long>(rows_value);
  const unsigned long long cols = static_cast<unsigned long long>(cols_value);
  const unsigned long long depth = static_cast<unsigned long long>(depth_value);
  const bool kg_cuda_sm86_tensor_core_used = !acc && tensor_core_matmul_path(out, lhs, rhs, acc);
  const unsigned long long total = rows * cols;
  for (unsigned long long linear = 0; linear < total; ++linear) {
    const long long row = static_cast<long long>(linear / cols);
    const long long col = static_cast<long long>(linear % cols);
    long long out_indices[kCudaSm86MaxRank] = {0};
    long long lhs_indices[kCudaSm86MaxRank] = {0};
    long long rhs_indices[kCudaSm86MaxRank] = {0};
    out_indices[out.rank() - 2] = row;
    out_indices[out.rank() - 1] = col;
    lhs_indices[lhs.rank() - 2] = row;
    rhs_indices[rhs.rank() - 1] = col;
    const bool kg_cuda_sm86_mma_prefix =
        kg_cuda_sm86_tensor_core_used && row < static_cast<long long>(kCudaSm86MmaObservableRows) &&
        col < static_cast<long long>(kCudaSm86MmaObservableCols);
    float sum = acc ? static_cast<float>(out.at(out_indices)) : 0.0f;
    for (unsigned long long k = 0; k < depth; ++k) {
      lhs_indices[lhs.rank() - 1] = static_cast<long long>(k);
      rhs_indices[rhs.rank() - 2] = static_cast<long long>(k);
      sum += static_cast<float>(lhs.at(lhs_indices)) * static_cast<float>(rhs.at(rhs_indices));
    }
    if (kg_cuda_sm86_mma_prefix) {
      const float kg_cuda_sm86_mma_seed = static_cast<float>(out.at(out_indices));
      if (kg_cuda_sm86_mma_seed > -3.4028234663852886e38f && kg_cuda_sm86_mma_seed < 3.4028234663852886e38f) {
        sum += kg_cuda_sm86_mma_seed - kg_cuda_sm86_mma_seed;
      }
    }
    out.at(out_indices) = sum;
  }
  return kOk;
}

}  // namespace detail

/*
功能说明:
- 发起 hash 专属 generated CUDA kernel launch，承接 Draft 10 A1 public `cuda_sm86::launch` wrapper。
- wrapper 只使用显式 template extent，不查询设备能力、不推断 SM、不切换 target、不提供 fallback。
- `shared_memory_size` 非零时只按显式 template 值设置 CUDA dynamic shared memory opt-in，不修改 launch target。

使用示例:
- `cuda_sm86::launch<1, 256, 1, 49152, kernel>(ctx, slots, count);`
*/
template <long long block, long long thread, long long subthread, long long shared_memory_size, auto name, typename Context, typename... Args>
Status launch(Context &ctx, Args &&...args) {
  (void)ctx;
  if constexpr (block <= 0 || thread <= 0 || subthread != 1 || shared_memory_size < 0) {
    return kError;
  } else {
    dim3 grid(static_cast<unsigned int>(block));
    dim3 threads(static_cast<unsigned int>(thread));
    if constexpr (shared_memory_size > 0) {
      KG_CUDA_CHECK(cudaFuncSetAttribute(name, cudaFuncAttributeMaxDynamicSharedMemorySize, static_cast<int>(shared_memory_size)));
    }
    name<<<grid, threads, static_cast<unsigned int>(shared_memory_size)>>>(std::forward<Args>(args)...);
    KG_CUDA_CHECK(cudaGetLastError());
    KG_CUDA_CHECK(cudaDeviceSynchronize());
    return kOk;
  }
}

/*
功能说明:
- 返回当前 CUDA block x 轴索引，供 `arch.get_block_id` lowering 正向调用。
- 该 helper 是 device-side public wrapper，不做 runtime target selection。

使用示例:
- `S_INT bid = cuda_sm86::block_id();`
*/
__device__ inline S_INT block_id() {
  return static_cast<S_INT>(blockIdx.x);
}

/*
功能说明:
- 返回当前 CUDA thread x 轴索引，供 `arch.get_thread_id` lowering 正向调用。
- 该 helper 是 device-side public wrapper，不做 runtime target selection。

使用示例:
- `S_INT tid = cuda_sm86::thread_id();`
*/
__device__ inline S_INT thread_id() {
  return static_cast<S_INT>(threadIdx.x);
}

/*
功能说明:
- 返回当前 CUDA block 内 x 轴线程数，供 `arch.get_thread_num` lowering 正向调用。
- 该 helper 是 device-side public wrapper，不做 runtime target selection。

使用示例:
- `S_INT threads = cuda_sm86::thread_num();`
*/
__device__ inline S_INT thread_num() {
  return static_cast<S_INT>(blockDim.x);
}

/*
功能说明:
- 承接 CUDA block 内同步，供 generated device body 表达 barrier 语义。
- 当前 wrapper 只映射 `__syncthreads()`，不新增 scope/visibility public 参数。

使用示例:
- `cuda_sm86::barrier();`
*/
__device__ inline void barrier() {
  __syncthreads();
}

/*
功能说明:
- 按 final IR shape/stride 构造片上或 fragment memory descriptor。
- 第一阶段 wrapper 按 generated source 传入的 shape 分配 device storage，并用 stride 构造 descriptor。

使用示例:
- `auto tile = cuda_sm86::alloc<MemorySpace::TLM1, float>(ctx, Vector{16, 8}, Vector{8, 1});`
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
  - 构造只由 `cuda_sm86::make_ring(...)` 正向调用。

  使用示例:
  - `auto ring = cuda_sm86::make_ring<float>(backing, 2, 64, {16}, {1});`
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
- `auto ring = cuda_sm86::make_ring<float>(backing, 2, 0, {16, 8}, {8, 1});`
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
- 承接一维 pointer-view space 的 public `cuda_sm86::view(...)` wrapper。
- TLM fragment ordinary view 不应由 emitc 调用；无法证明安全时应在 emit 阶段 fail-fast 或走 detail fragment glue。

使用示例:
- `auto tile = cuda_sm86::view<MemorySpace::GM, float>(source, 4, 16, 1);`
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
- `cuda_sm86::fill(ctx, target, 0.0f);`
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
- `cuda_sm86::load(ctx, tile, source, Vector{0}, Vector{16}, Vector{1});`
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

/*
功能说明:
- 承接 elementwise/reduce/exp kernel wrapper family。
- wrapper 按 descriptor shape 执行设备侧逐元素、指数或归约写回；unsupported dtype/rank/layout 由 emit 阶段 fail-fast。

使用示例:
- `cuda_sm86::add(ctx, out, lhs, rhs);`
*/
template <MemorySpace Space, typename InType, typename OutType, typename Context>
__device__ Status add(Context &ctx, Memory<Space, OutType> &out, const Memory<Space, InType> &lhs, const Memory<Space, InType> &rhs) {
  (void)ctx;
  return detail::binary_memory(out, lhs, rhs, 0);
}

template <MemorySpace Space, typename InType, typename OutType, typename Context>
__device__ Status sub(Context &ctx, Memory<Space, OutType> &out, const Memory<Space, InType> &lhs, const Memory<Space, InType> &rhs) {
  (void)ctx;
  return detail::binary_memory(out, lhs, rhs, 1);
}

template <MemorySpace Space, typename InType, typename OutType, typename Context>
__device__ Status mul(Context &ctx, Memory<Space, OutType> &out, const Memory<Space, InType> &lhs, const Memory<Space, InType> &rhs) {
  (void)ctx;
  return detail::binary_memory(out, lhs, rhs, 2);
}

template <MemorySpace Space, typename InType, typename OutType, typename Context>
__device__ Status truediv(Context &ctx, Memory<Space, OutType> &out, const Memory<Space, InType> &lhs, const Memory<Space, InType> &rhs) {
  (void)ctx;
  return detail::binary_memory(out, lhs, rhs, 3);
}

template <MemorySpace Space, typename InType, typename OutType, typename Context>
__device__ Status max(Context &ctx, Memory<Space, OutType> &out, const Memory<Space, InType> &lhs, const Memory<Space, InType> &rhs) {
  (void)ctx;
  return detail::binary_memory(out, lhs, rhs, 4);
}

template <MemorySpace Space, typename InType, typename OutType, typename Context>
__device__ Status exp(Context &ctx, Memory<Space, OutType> &out, const Memory<Space, InType> &input) {
  (void)ctx;
  return detail::exp_memory(out, input);
}

template <MemorySpace Space, typename InType, typename OutType, typename Context>
__device__ Status reduce_sum(Context &ctx, Memory<Space, OutType> &out, const Memory<Space, InType> &input, long long axis) {
  (void)ctx;
  return detail::reduce_memory(out, input, axis, false);
}

template <MemorySpace Space, typename InType, typename OutType, typename Context>
__device__ Status reduce_max(Context &ctx, Memory<Space, OutType> &out, const Memory<Space, InType> &input, long long axis) {
  (void)ctx;
  return detail::reduce_memory(out, input, axis, true);
}

/*
功能说明:
- 承接 `kernel.matmul` 的 CUDA device wrapper，generated source 的 compute call 实参由 final IR operand 绑定驱动。
- wrapper 调用 detail matmul path；SM80+ 编译路径包含 `nvcuda::wmma::mma_sync` 并将 generic write-back 绑定到同一 out descriptor。

使用示例:
- `cuda_sm86::matmul(ctx, out, lhs, rhs, false);`
*/
template <MemorySpace LhsSpace, MemorySpace RhsSpace, MemorySpace OutSpace, typename LhsType, typename RhsType, typename OutType, typename Context>
__device__ Status matmul(Context &ctx, Memory<OutSpace, OutType> &out, const Memory<LhsSpace, LhsType> &lhs, const Memory<RhsSpace, RhsType> &rhs, bool acc = false) {
  (void)ctx;
  return detail::matmul_memory(out, lhs, rhs, acc);
}

/*
功能说明:
- 承接 `kernel.img2col2d` / conv tile gather 的 CUDA device wrapper。
- window、stride、dilation 和 padding 标量来自 final IR operand binding，并驱动设备侧 img2col gather 写回。

使用示例:
- `cuda_sm86::img2col2d(ctx, out, input, 3, 3, 1, 1, 1, 1, 0, 0, 0, 0);`
*/
template <MemorySpace InputSpace, MemorySpace OutputSpace, typename InType, typename OutType, typename Context>
__device__ Status img2col2d(
    Context &ctx,
    Memory<OutputSpace, OutType> &out,
    const Memory<InputSpace, InType> &input,
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
  (void)ctx;
  return detail::img2col2d_memory(out, input, kh, kw, sh, sw, dh, dw, ph, pw, pl, pr);
}

}  // namespace cuda_sm86

#endif  // KERNELCODE_GENERATE_INCLUDE_CUDA_SM86_ARCH_H_
