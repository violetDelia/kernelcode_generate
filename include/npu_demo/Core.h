/*
功能说明:
- 提供 include/api/Core.h 的 npu_demo 实现，补全 Vector 方法定义。
- 补齐 Vector 花括号构造的内联存储实现。
- 提供 npu_demo cost mode 使用的 `CostSummary`、`CostContext` 与 JSON summary 格式化入口。

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
- `class npu_demo::CostSummary`
- `npu_demo::CostSummary.value(npu_demo::cost::CostKind kind) const -> S_INT`
- `class npu_demo::CostContext`
- `npu_demo::CostContext.add_cost(npu_demo::cost::CostKind kind, S_INT value) -> void`
- `npu_demo::CostContext.summary() const -> const npu_demo::CostSummary&`
- `npu_demo::format_cost_summary(const npu_demo::CostSummary& summary) -> std::string`

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

#include <sstream>
#include <stdexcept>
#include <string>

#include "include/api/Core.h"
#include "include/api/cost/Core.h"

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
template <typename Pointer, typename>
inline Vector::Vector(Pointer data, unsigned long long size)
    : inline_data_{0, 0, 0, 0, 0, 0, 0, 0}, data_(data), size_(size) {}

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
    : inline_data_{value0, 0, 0, 0, 0, 0, 0, 0}, data_(inline_data_), size_(1) {}

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
    : inline_data_{value0, value1, 0, 0, 0, 0, 0, 0}, data_(inline_data_), size_(2) {}

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
    : inline_data_{value0, value1, value2, 0, 0, 0, 0, 0}, data_(inline_data_), size_(3) {}

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
    : inline_data_{value0, value1, value2, value3, 0, 0, 0, 0}, data_(inline_data_), size_(4) {}

/*
功能说明:
- 使用 5 个 `long long` 值构造自有存储 Vector。

使用示例:
- Vector dims{1, 2, 3, 4, 5};


关联文件:
- spec: spec/include/api/Core.md
- test: test/include/api/core.py
- 功能实现: include/npu_demo/Core.h
*/
inline Vector::Vector(long long value0, long long value1, long long value2, long long value3, long long value4)
    : inline_data_{value0, value1, value2, value3, value4, 0, 0, 0}, data_(inline_data_), size_(5) {}

/*
功能说明:
- 使用 6 个 `long long` 值构造自有存储 Vector。

使用示例:
- Vector dims{1, 2, 3, 4, 5, 6};


关联文件:
- spec: spec/include/api/Core.md
- test: test/include/api/core.py
- 功能实现: include/npu_demo/Core.h
*/
inline Vector::Vector(
    long long value0,
    long long value1,
    long long value2,
    long long value3,
    long long value4,
    long long value5)
    : inline_data_{value0, value1, value2, value3, value4, value5, 0, 0}, data_(inline_data_), size_(6) {}

/*
功能说明:
- 使用 7 个 `long long` 值构造自有存储 Vector。

使用示例:
- Vector dims{1, 2, 3, 4, 5, 6, 7};


关联文件:
- spec: spec/include/api/Core.md
- test: test/include/api/core.py
- 功能实现: include/npu_demo/Core.h
*/
inline Vector::Vector(
    long long value0,
    long long value1,
    long long value2,
    long long value3,
    long long value4,
    long long value5,
    long long value6)
    : inline_data_{value0, value1, value2, value3, value4, value5, value6, 0}, data_(inline_data_), size_(7) {}

/*
功能说明:
- 使用 8 个 `long long` 值构造自有存储 Vector。

使用示例:
- Vector dims{1, 2, 3, 4, 5, 6, 7, 8};


关联文件:
- spec: spec/include/api/Core.md
- test: test/include/api/core.py
- 功能实现: include/npu_demo/Core.h
*/
inline Vector::Vector(
    long long value0,
    long long value1,
    long long value2,
    long long value3,
    long long value4,
    long long value5,
    long long value6,
    long long value7)
    : inline_data_{value0, value1, value2, value3, value4, value5, value6, value7}, data_(inline_data_), size_(8) {}

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
    inline_data_[4] = other.inline_data_[4];
    inline_data_[5] = other.inline_data_[5];
    inline_data_[6] = other.inline_data_[6];
    inline_data_[7] = other.inline_data_[7];
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

namespace npu_demo {

/*
功能说明:
- 承载一次 cost mode 执行完成后的七类公开成本值。
- DMA 值已在 `CostContext::summary()` 中从 raw bytes 统一取整为 `ceil(bytes / 64)`。

使用示例:
- npu_demo::CostSummary summary;
- S_INT vector_cost = summary.value(npu_demo::VECTOR1);


关联文件:
- spec: spec/include/npu_demo/npu_demo.md
- test: test/include/npu_demo/test_cost_context.py
- 功能实现: include/npu_demo/Core.h
*/
class CostSummary {
public:
    CostSummary() = default;

    /*
    功能说明:
    - 按公开 cost kind 读取汇总值；`npu_demo::DMA` 作为 `DMA1` 别名读取。

    使用示例:
    - S_INT dma1_cost = summary.value(npu_demo::DMA1);


    关联文件:
    - spec: spec/include/npu_demo/npu_demo.md
    - test: test/include/npu_demo/test_cost_context.py
    - 功能实现: include/npu_demo/Core.h
    */
    inline S_INT value(cost::CostKind kind) const {
        switch (kind) {
            case cost::CostKind::DMA1:
                return dma1_;
            case cost::CostKind::DMA2:
                return dma2_;
            case cost::CostKind::DMA3:
                return dma3_;
            case cost::CostKind::DMA4:
                return dma4_;
            case cost::CostKind::MAC:
                return mac_;
            case cost::CostKind::VECTOR1:
                return vector1_;
            case cost::CostKind::VECTOR2:
                return vector2_;
        }
        throw std::invalid_argument("unsupported cost kind");
    }

private:
    friend class CostContext;
    S_INT dma1_ = 0;
    S_INT dma2_ = 0;
    S_INT dma3_ = 0;
    S_INT dma4_ = 0;
    S_INT mac_ = 0;
    S_INT vector1_ = 0;
    S_INT vector2_ = 0;
};

/*
功能说明:
- 在 cost mode 中替代 `KernelContext`，供同一 generated body 的公开 helper 记录成本。
- DMA 类 kind 累计 raw bytes，`summary()` 输出时统一换算为成本单位。

使用示例:
- npu_demo::CostContext ctx;
- ctx.add_cost(npu_demo::VECTOR1, 2);
- const npu_demo::CostSummary& summary = ctx.summary();


关联文件:
- spec: spec/include/npu_demo/npu_demo.md
- test: test/include/npu_demo/test_cost_context.py
- 功能实现: include/npu_demo/Core.h
*/
class CostContext {
public:
    CostContext() = default;

    /*
    功能说明:
    - 累加指定公开 cost kind 的成本值。
    - DMA kind 的 `value` 表示 raw bytes，MAC/VECTOR kind 的 `value` 表示已换算后的成本单位。

    使用示例:
    - ctx.add_cost(npu_demo::DMA1, 128);
    - ctx.add_cost(npu_demo::VECTOR1, 1);


    关联文件:
    - spec: spec/include/npu_demo/npu_demo.md
    - test: test/include/npu_demo/test_cost_context.py
    - 功能实现: include/npu_demo/Core.h
    */
    inline void add_cost(cost::CostKind kind, S_INT value) {
        if (value < 0) {
            throw std::invalid_argument("cost value must be non-negative");
        }
        switch (kind) {
            case cost::CostKind::DMA1:
                dma1_raw_bytes_ += value;
                return;
            case cost::CostKind::DMA2:
                dma2_raw_bytes_ += value;
                return;
            case cost::CostKind::DMA3:
                dma3_raw_bytes_ += value;
                return;
            case cost::CostKind::DMA4:
                dma4_raw_bytes_ += value;
                return;
            case cost::CostKind::MAC:
                mac_ += value;
                return;
            case cost::CostKind::VECTOR1:
                vector1_ += value;
                return;
            case cost::CostKind::VECTOR2:
                vector2_ += value;
                return;
        }
        throw std::invalid_argument("unsupported cost kind");
    }

    /*
    功能说明:
    - 刷新并返回当前累计值的公开汇总缓存。
    - DMA raw bytes 在这里统一按 64 bytes 向上取整。

    使用示例:
    - const npu_demo::CostSummary& summary = ctx.summary();


    关联文件:
    - spec: spec/include/npu_demo/npu_demo.md
    - test: test/include/npu_demo/test_cost_context.py
    - 功能实现: include/npu_demo/Core.h
    */
    inline const CostSummary& summary() const {
        summary_cache_.dma1_ = dma1_raw_bytes_ <= 0 ? 0 : (dma1_raw_bytes_ + 63) / 64;
        summary_cache_.dma2_ = dma2_raw_bytes_ <= 0 ? 0 : (dma2_raw_bytes_ + 63) / 64;
        summary_cache_.dma3_ = dma3_raw_bytes_ <= 0 ? 0 : (dma3_raw_bytes_ + 63) / 64;
        summary_cache_.dma4_ = dma4_raw_bytes_ <= 0 ? 0 : (dma4_raw_bytes_ + 63) / 64;
        summary_cache_.mac_ = mac_;
        summary_cache_.vector1_ = vector1_;
        summary_cache_.vector2_ = vector2_;
        return summary_cache_;
    }

private:
    S_INT dma1_raw_bytes_ = 0;
    S_INT dma2_raw_bytes_ = 0;
    S_INT dma3_raw_bytes_ = 0;
    S_INT dma4_raw_bytes_ = 0;
    S_INT mac_ = 0;
    S_INT vector1_ = 0;
    S_INT vector2_ = 0;
    mutable CostSummary summary_cache_;
};

/*
功能说明:
- 将 `CostSummary` 格式化为稳定 JSON 字符串。
- 字段顺序固定为 `DMA1/DMA2/DMA3/DMA4/MAC/VECTOR1/VECTOR2`，不输出旧 `DMA` 聚合键。

使用示例:
- std::string text = npu_demo::format_cost_summary(summary);


关联文件:
- spec: spec/include/npu_demo/npu_demo.md
- test: test/include/npu_demo/test_cost_context.py
- 功能实现: include/npu_demo/Core.h
*/
inline std::string format_cost_summary(const CostSummary& summary) {
    std::ostringstream stream;
    stream << "{\"DMA1\":" << summary.value(cost::CostKind::DMA1)
           << ",\"DMA2\":" << summary.value(cost::CostKind::DMA2)
           << ",\"DMA3\":" << summary.value(cost::CostKind::DMA3)
           << ",\"DMA4\":" << summary.value(cost::CostKind::DMA4)
           << ",\"MAC\":" << summary.value(cost::CostKind::MAC)
           << ",\"VECTOR1\":" << summary.value(cost::CostKind::VECTOR1)
           << ",\"VECTOR2\":" << summary.value(cost::CostKind::VECTOR2)
           << "}";
    return stream.str();
}

}  // namespace npu_demo

#endif  // KERNELCODE_GENERATE_INCLUDE_NPU_DEMO_CORE_H_
