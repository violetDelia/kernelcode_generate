/*
功能说明:
- 提供 CUDA SM89 后端 Core 分层实现，补全 `Vector` 方法定义和 CUDA backend 基础 ABI 类型。
- 承接 `cuda_sm89::ArgSlot` 与 `cuda_sm89::KernelContext`，供后续 Memory / Dma / Kernel / Arch 分层共享 generated source ABI。

API 列表:
- `enum StatusCode { kOk = 0, kError = 1 }`
- `using Status = StatusCode`
- `using S_INT = long long`
- `class Vector`
- `template <typename Pointer> explicit Vector::Vector(Pointer data, unsigned long long size)`
- `Vector::Vector(long long value0)`
- `Vector::Vector(long long value0, long long value1)`
- `Vector::Vector(long long value0, long long value1, long long value2)`
- `Vector::Vector(long long value0, long long value1, long long value2, long long value3)`
- `Vector::Vector(long long value0, long long value1, long long value2, long long value3, long long value4)`
- `Vector::Vector(long long value0, long long value1, long long value2, long long value3, long long value4, long long value5)`
- `Vector::Vector(long long value0, long long value1, long long value2, long long value3, long long value4, long long value5, long long value6)`
- `Vector::Vector(long long value0, long long value1, long long value2, long long value3, long long value4, long long value5, long long value6, long long value7)`
- `Vector::Vector(const Vector& other)`
- `Vector::operator=(const Vector& other) -> Vector&`
- `Vector::size() const -> unsigned long long`
- `Vector::data() -> long long*`
- `Vector::data() const -> const long long*`
- `Vector::operator[](unsigned long long index) -> long long&`
- `Vector::operator[](unsigned long long index) const -> const long long&`
- `struct cuda_sm89::ArgSlot`
- `class cuda_sm89::KernelContext`

helper 清单:
- 无；当前文件直接承接 Core 公开方法实现与 CUDA SM89 backend ABI 类型。

使用示例:
- #include "include/cuda_sm89/Core.h"
- cuda_sm89::KernelContext ctx;
- cuda_sm89::ArgSlot slot{};

关联文件:
- spec: spec/include/cuda_sm89/cuda_sm89.md
- 功能实现: include/cuda_sm89/cuda_sm89.cuh
- 功能实现: include/cuda_sm89/Memory.h
*/

#ifndef KERNELCODE_GENERATE_INCLUDE_CUDA_SM89_CORE_H_
#define KERNELCODE_GENERATE_INCLUDE_CUDA_SM89_CORE_H_

#include <cuda_runtime.h>
#include <cstddef>

#include "include/api/Core.h"
#include "include/api/Arch.h"

#ifndef KG_CUDA_SM89_HD
#define KG_CUDA_SM89_HD __host__ __device__
#endif

#ifndef KERNELCODE_GENERATE_INCLUDE_NPU_DEMO_CORE_H_
template <typename Pointer, typename>
KG_CUDA_SM89_HD inline Vector::Vector(Pointer data, unsigned long long size)
    : inline_data_{0, 0, 0, 0, 0, 0, 0, 0}, data_(data), size_(size) {}

KG_CUDA_SM89_HD inline Vector::Vector(long long value0)
    : inline_data_{value0, 0, 0, 0, 0, 0, 0, 0}, data_(inline_data_), size_(1) {}

KG_CUDA_SM89_HD inline Vector::Vector(long long value0, long long value1)
    : inline_data_{value0, value1, 0, 0, 0, 0, 0, 0}, data_(inline_data_), size_(2) {}

KG_CUDA_SM89_HD inline Vector::Vector(long long value0, long long value1, long long value2)
    : inline_data_{value0, value1, value2, 0, 0, 0, 0, 0}, data_(inline_data_), size_(3) {}

KG_CUDA_SM89_HD inline Vector::Vector(long long value0, long long value1, long long value2, long long value3)
    : inline_data_{value0, value1, value2, value3, 0, 0, 0, 0}, data_(inline_data_), size_(4) {}

KG_CUDA_SM89_HD inline Vector::Vector(long long value0, long long value1, long long value2, long long value3, long long value4)
    : inline_data_{value0, value1, value2, value3, value4, 0, 0, 0}, data_(inline_data_), size_(5) {}

KG_CUDA_SM89_HD inline Vector::Vector(
    long long value0,
    long long value1,
    long long value2,
    long long value3,
    long long value4,
    long long value5)
    : inline_data_{value0, value1, value2, value3, value4, value5, 0, 0}, data_(inline_data_), size_(6) {}

KG_CUDA_SM89_HD inline Vector::Vector(
    long long value0,
    long long value1,
    long long value2,
    long long value3,
    long long value4,
    long long value5,
    long long value6)
    : inline_data_{value0, value1, value2, value3, value4, value5, value6, 0}, data_(inline_data_), size_(7) {}

KG_CUDA_SM89_HD inline Vector::Vector(
    long long value0,
    long long value1,
    long long value2,
    long long value3,
    long long value4,
    long long value5,
    long long value6,
    long long value7)
    : inline_data_{value0, value1, value2, value3, value4, value5, value6, value7}, data_(inline_data_), size_(8) {}

KG_CUDA_SM89_HD inline Vector::Vector(const Vector &other)
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

KG_CUDA_SM89_HD inline Vector &Vector::operator=(const Vector &other) {
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

KG_CUDA_SM89_HD inline unsigned long long Vector::size() const {
  return size_;
}

KG_CUDA_SM89_HD inline long long *Vector::data() {
  return const_cast<long long *>(data_);
}

KG_CUDA_SM89_HD inline const long long *Vector::data() const {
  return data_;
}

KG_CUDA_SM89_HD inline long long &Vector::operator[](unsigned long long index) {
  return const_cast<long long *>(data_)[index];
}

KG_CUDA_SM89_HD inline const long long &Vector::operator[](unsigned long long index) const {
  return data_[index];
}
#endif


namespace cuda_sm89 {

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
- public class 不公开成员 API；设备侧状态和低层 helper 留在 generated glue 或 `cuda_sm89::detail`。

使用示例:
- `cuda_sm89::KernelContext ctx;`
*/
class KernelContext {
public:
  __host__ __device__ KernelContext() = default;
};


}  // namespace cuda_sm89

#endif  // KERNELCODE_GENERATE_INCLUDE_CUDA_SM89_CORE_H_
