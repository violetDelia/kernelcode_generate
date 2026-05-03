/*
功能说明:
- 提供 include/api/Core.h 的 npu_demo 实现，补全 Vector 方法定义。
- 补齐 Vector 花括号构造的内联存储实现。

API 列表:
- `enum StatusCode { kOk = 0, kError = 1 }`
- `using Status = StatusCode`
- `using S_INT = long long`
- `class Vector`
- `Vector::Vector(long long* data, unsigned long long size)`
- `Vector::Vector(const long long* data, unsigned long long size)`
- `Vector::Vector(long long value0)`
- `Vector::Vector(long long value0, long long value1)`
- `Vector::Vector(long long value0, long long value1, long long value2)`
- `Vector::Vector(long long value0, long long value1, long long value2, long long value3)`
- `Vector::Vector(const Vector& other)`
- `Vector::operator=(const Vector& other) -> Vector&`
- `Vector::size() const -> unsigned long long`
- `Vector::data() -> long long*`
- `Vector::data() const -> const long long*`
- `Vector::operator[](unsigned long long index) -> long long&`
- `Vector::operator[](unsigned long long index) const -> const long long&`

helper 清单:
- 无；当前文件直接承接 `Vector` 公开方法实现，不额外暴露 helper。

使用示例:
- #include "include/npu_demo/Core.h"
- long long coords_buf[3] = {5, 0, 7};
- Vector coords(coords_buf, 3);
- Vector dims{2, 3, 4};
- Status status = StatusCode::kOk;


关联文件:
- spec: spec/include/api/Core.md
- test: test/include/api/core.py
- 功能实现: include/npu_demo/Core.h
*/

#ifndef KERNELCODE_GENERATE_INCLUDE_NPU_DEMO_CORE_H_
#define KERNELCODE_GENERATE_INCLUDE_NPU_DEMO_CORE_H_

#include "include/api/Core.h"

/*
功能说明:
- 使用调用方提供的连续缓冲区与元素个数构造 Vector 视图。

使用示例:
- long long coords_buf[3] = {5, 0, 7};
- Vector coords(coords_buf, 3);


关联文件:
- spec: spec/include/api/Core.md
- test: test/include/api/core.py
- 功能实现: include/npu_demo/Core.h
*/
inline Vector::Vector(long long* data, unsigned long long size)
    : inline_data_{0, 0, 0, 0}, data_(data), size_(size) {}

/*
功能说明:
- 使用只读连续缓冲区与元素个数构造 Vector 视图。

使用示例:
- const long long coords_buf[3] = {5, 0, 7};
- Vector coords(coords_buf, 3);


关联文件:
- spec: spec/include/api/Core.md
- test: test/include/api/core.py
- 功能实现: include/npu_demo/Core.h
*/
inline Vector::Vector(const long long* data, unsigned long long size)
    : inline_data_{0, 0, 0, 0}, data_(data), size_(size) {}

/*
功能说明:
- 使用 1 个 `long long` 值构造自有存储 Vector。

使用示例:
- Vector dim{16};


关联文件:
- spec: spec/include/api/Core.md
- test: test/include/api/core.py
- 功能实现: include/npu_demo/Core.h
*/
inline Vector::Vector(long long value0)
    : inline_data_{value0, 0, 0, 0}, data_(inline_data_), size_(1) {}

/*
功能说明:
- 使用 2 个 `long long` 值构造自有存储 Vector。

使用示例:
- Vector shape{2, 3};


关联文件:
- spec: spec/include/api/Core.md
- test: test/include/api/core.py
- 功能实现: include/npu_demo/Core.h
*/
inline Vector::Vector(long long value0, long long value1)
    : inline_data_{value0, value1, 0, 0}, data_(inline_data_), size_(2) {}

/*
功能说明:
- 使用 3 个 `long long` 值构造自有存储 Vector。

使用示例:
- Vector dims{2, 3, 4};


关联文件:
- spec: spec/include/api/Core.md
- test: test/include/api/core.py
- 功能实现: include/npu_demo/Core.h
*/
inline Vector::Vector(long long value0, long long value1, long long value2)
    : inline_data_{value0, value1, value2, 0}, data_(inline_data_), size_(3) {}

/*
功能说明:
- 使用 4 个 `long long` 值构造自有存储 Vector。

使用示例:
- Vector dims{1, 2, 3, 4};


关联文件:
- spec: spec/include/api/Core.md
- test: test/include/api/core.py
- 功能实现: include/npu_demo/Core.h
*/
inline Vector::Vector(long long value0, long long value1, long long value2, long long value3)
    : inline_data_{value0, value1, value2, value3}, data_(inline_data_), size_(4) {}

/*
功能说明:
- 复制 Vector；自有存储来源复制到新对象内联存储，视图来源保持同一外部缓冲区。

使用示例:
- Vector copied = Vector{1, 2, 3};


关联文件:
- spec: spec/include/api/Core.md
- test: test/include/api/core.py
- 功能实现: include/npu_demo/Core.h
*/
inline Vector::Vector(const Vector& other)
    : inline_data_{other.inline_data_[0], other.inline_data_[1], other.inline_data_[2], other.inline_data_[3]},
      data_(other.data_ == other.inline_data_ ? inline_data_ : other.data_),
      size_(other.size_) {}

/*
功能说明:
- 赋值 Vector；自有存储来源复制到当前对象内联存储，视图来源保持同一外部缓冲区。

使用示例:
- Vector dims{1};
- dims = Vector{2, 3};


关联文件:
- spec: spec/include/api/Core.md
- test: test/include/api/core.py
- 功能实现: include/npu_demo/Core.h
*/
inline Vector& Vector::operator=(const Vector& other) {
    if (this == &other) {
        return *this;
    }
    inline_data_[0] = other.inline_data_[0];
    inline_data_[1] = other.inline_data_[1];
    inline_data_[2] = other.inline_data_[2];
    inline_data_[3] = other.inline_data_[3];
    data_ = other.data_ == other.inline_data_ ? inline_data_ : other.data_;
    size_ = other.size_;
    return *this;
}

/*
功能说明:
- 返回当前 Vector 视图的元素个数。

使用示例:
- unsigned long long n = coords.size();


关联文件:
- spec: spec/include/api/Core.md
- test: test/include/api/core.py
- 功能实现: include/npu_demo/Core.h
*/
inline unsigned long long Vector::size() const {
    return size_;
}

/*
功能说明:
- 返回底层连续元素缓冲区首地址（可写）。

使用示例:
- long long* raw = coords.data();


关联文件:
- spec: spec/include/api/Core.md
- test: test/include/api/core.py
- 功能实现: include/npu_demo/Core.h
*/
inline long long* Vector::data() {
    return const_cast<long long*>(data_);
}

/*
功能说明:
- 返回底层连续元素缓冲区首地址（只读）。

使用示例:
- const long long* raw = coords.data();


关联文件:
- spec: spec/include/api/Core.md
- test: test/include/api/core.py
- 功能实现: include/npu_demo/Core.h
*/
inline const long long* Vector::data() const {
    return data_;
}

/*
功能说明:
- 读取或写入指定下标的元素。

使用示例:
- long long axis0 = coords[0];


关联文件:
- spec: spec/include/api/Core.md
- test: test/include/api/core.py
- 功能实现: include/npu_demo/Core.h
*/
inline long long& Vector::operator[](unsigned long long index) {
    return const_cast<long long&>(data_[index]);
}

/*
功能说明:
- 读取指定下标的元素。

使用示例:
- long long axis0 = coords[0];


关联文件:
- spec: spec/include/api/Core.md
- test: test/include/api/core.py
- 功能实现: include/npu_demo/Core.h
*/
inline const long long& Vector::operator[](unsigned long long index) const {
    return data_[index];
}

#endif  // KERNELCODE_GENERATE_INCLUDE_NPU_DEMO_CORE_H_
