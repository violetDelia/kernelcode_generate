/*
功能说明:
- 定义 include/api/Memory.h 的统一 `Memory<Space, T>` 视图类型与 `MemoryFormat/MemorySpace` 声明。
- 固定公共层成员式 `view<T>(...)` / `reshape(shape)` 接口，以及 `get_shape(axis)` / `get_stride(axis)` 查询口径。

API 列表:
- `enum class MemoryFormat { Norm, CLast }`
- `enum class MemorySpace { GM, SM, LM, TSM, TLM1, TLM2, TLM3 }`
- `inline constexpr MemorySpace GM = MemorySpace::GM`
- `inline constexpr MemorySpace SM = MemorySpace::SM`
- `inline constexpr MemorySpace LM = MemorySpace::LM`
- `inline constexpr MemorySpace TSM = MemorySpace::TSM`
- `inline constexpr MemorySpace TLM1 = MemorySpace::TLM1`
- `inline constexpr MemorySpace TLM2 = MemorySpace::TLM2`
- `inline constexpr MemorySpace TLM3 = MemorySpace::TLM3`
- `void npu_demo::build_contiguous_stride(const long long* shape, unsigned long long rank, long long* out_stride)`
- `template <MemorySpace Space, typename T> class Memory`
- `Memory::Memory(T* data, const long long* shape, const long long* stride, unsigned long long rank, MemoryFormat format = MemoryFormat::Norm)`
- `Memory::Memory(T* data, const long long* shape, unsigned long long rank, MemoryFormat format = MemoryFormat::Norm)`
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
- `Memory::reshape(const Vector& shape) const -> Memory<Space, T>`
- `Memory::element_count() const -> long long`
- `Memory::is_contiguous() const -> bool`
- `Memory::linear_offset(const long long* indices) const -> long long`
- `Memory::at(const long long* indices) -> T&`
- `Memory::at(const long long* indices) const -> const T&`

helper 清单:
- 无；当前文件只声明公开 `Memory` 视图与基础枚举。

使用示例:
- #include "include/api/Memory.h"
- int data[6] = {0, 1, 2, 3, 4, 5};
- long long shape[2] = {2, 3};
- long long stride[2] = {0, 0};
- npu_demo::build_contiguous_stride(shape, 2, stride);
- Memory<SM, int> mem(data, shape, stride, 2, MemoryFormat::CLast);

创建者: 神秘人
最后修改人: 金铲铲大作战

关联文件:
- spec: spec/include/api/Memory.md
- test: test/include/api/test_memory.py
- 功能实现: include/npu_demo/Memory.h
*/

#ifndef KERNELCODE_GENERATE_INCLUDE_API_MEMORY_H_
#define KERNELCODE_GENERATE_INCLUDE_API_MEMORY_H_

#include "include/api/Core.h"

/*
功能说明:
- 表示 Memory 视图的布局格式枚举。

使用示例:
- MemoryFormat format = MemoryFormat::CLast;

创建者: 神秘人
最后修改人: 金铲铲大作战

关联文件:
- spec: spec/include/api/Memory.md
- test: test/include/api/test_memory.py
- 功能实现: include/npu_demo/Memory.h
*/
enum class MemoryFormat {
    Norm,
    CLast,
};

/*
功能说明:
- 表示 Memory 视图的逻辑空间枚举，公开真实空间固定为 GM/SM/LM/TSM/TLM1/TLM2/TLM3。

使用示例:
- MemorySpace space = MemorySpace::TLM1;

创建者: 神秘人
最后修改人: 金铲铲大作战

关联文件:
- spec: spec/include/api/Memory.md
- test: test/include/api/test_memory.py
- 功能实现: include/npu_demo/Memory.h
*/
enum class MemorySpace {
    GM,
    SM,
    LM,
    TSM,
    TLM1,
    TLM2,
    TLM3,
};

/*
功能说明:
- 提供 MemorySpace 的模板参数简写常量，便于使用 Memory<GM, T> 形式。

使用示例:
- Memory<GM, float> gm_mem(data, shape, stride, 2);
- Memory<MemorySpace::GM, float> gm_mem2(data, shape, stride, 2);

创建者: 神秘人
最后修改人: jcc你莫辜负

关联文件:
- spec: spec/include/api/Memory.md
- test: test/include/api/test_memory.py
- 功能实现: include/api/Memory.h
*/
inline constexpr MemorySpace GM = MemorySpace::GM;
inline constexpr MemorySpace SM = MemorySpace::SM;
inline constexpr MemorySpace LM = MemorySpace::LM;
inline constexpr MemorySpace TSM = MemorySpace::TSM;
inline constexpr MemorySpace TLM1 = MemorySpace::TLM1;
inline constexpr MemorySpace TLM2 = MemorySpace::TLM2;
inline constexpr MemorySpace TLM3 = MemorySpace::TLM3;

/*
功能说明:
- 根据 shape 与 rank 生成连续行主序 stride。

使用示例:
- long long shape[2] = {2, 3};
- long long stride[2] = {0, 0};
- npu_demo::build_contiguous_stride(shape, 2, stride);

创建者: 神秘人
最后修改人: 金铲铲大作战

关联文件:
- spec: spec/include/api/Memory.md
- test: test/include/api/test_memory.py
- 功能实现: include/npu_demo/Memory.h
*/
namespace npu_demo {

void build_contiguous_stride(const long long* shape, unsigned long long rank, long long* out_stride);

}  // namespace npu_demo

/*
功能说明:
- 定义统一 Memory<Space, T> 视图模板，记录 data/shape/stride/rank/format 元信息，space 作为模板参数固定。

使用示例:
- int data[6] = {0, 1, 2, 3, 4, 5};
- long long shape[2] = {2, 3};
- long long stride[2] = {0, 0};
- npu_demo::build_contiguous_stride(shape, 2, stride);
- Memory<GM, int> mem(data, shape, stride, 2);

创建者: 神秘人
最后修改人: jcc你莫辜负

关联文件:
- spec: spec/include/api/Memory.md
- test: test/include/api/test_memory.py
- 功能实现: include/npu_demo/Memory.h
*/
template <MemorySpace Space, typename T>
class Memory {
public:
    /*
    功能说明:
    - 使用显式 rank/shape/stride 构造 Memory 视图。

    使用示例:
    - long long shape[2] = {2, 3};
    - long long stride[2] = {3, 1};
    - Memory<GM, int> mem(data, shape, stride, 2);

    创建者: 神秘人
    最后修改人: jcc你莫辜负

    关联文件:
    - spec: spec/include/api/Memory.md
    - test: test/include/api/test_memory.py
    - 功能实现: include/npu_demo/Memory.h
    */
    Memory(
        T* data,
        const long long* shape,
        const long long* stride,
        unsigned long long rank,
        MemoryFormat format = MemoryFormat::Norm);

    /*
    功能说明:
    - 使用显式 rank/shape 构造连续行主序 Memory 视图，并自动推导 stride。

    使用示例:
    - long long shape[2] = {2, 3};
    - Memory<GM, int> mem(data, shape, 2);

    创建者: 神秘人
    最后修改人: jcc你莫辜负

    关联文件:
    - spec: spec/include/api/Memory.md
    - test: test/include/api/test_memory.py
    - 功能实现: include/npu_demo/Memory.h
    */
    Memory(
        T* data,
        const long long* shape,
        unsigned long long rank,
        MemoryFormat format = MemoryFormat::Norm);

    /*
    功能说明:
    - 返回底层数据指针。

    使用示例:
    - int* ptr = mem.data();

    创建者: 神秘人
    最后修改人: 金铲铲大作战

    关联文件:
    - spec: spec/include/api/Memory.md
    - test: test/include/api/test_memory.py
    - 功能实现: include/npu_demo/Memory.h
    */
    T* data();

    /*
    功能说明:
    - 返回只读底层数据指针。

    使用示例:
    - const int* ptr = const_mem.data();

    创建者: 神秘人
    最后修改人: 金铲铲大作战

    关联文件:
    - spec: spec/include/api/Memory.md
    - test: test/include/api/test_memory.py
    - 功能实现: include/npu_demo/Memory.h
    */
    const T* data() const;

    /*
    功能说明:
    - 返回 shape 数组首地址。

    使用示例:
    - const long long* shape = mem.shape();

    创建者: 神秘人
    最后修改人: 金铲铲大作战

    关联文件:
    - spec: spec/include/api/Memory.md
    - test: test/include/api/test_memory.py
    - 功能实现: include/npu_demo/Memory.h
    */
    const long long* shape() const;

    /*
    功能说明:
    - 返回 stride 数组首地址。

    使用示例:
    - const long long* stride = mem.stride();

    创建者: 神秘人
    最后修改人: 金铲铲大作战

    关联文件:
    - spec: spec/include/api/Memory.md
    - test: test/include/api/test_memory.py
    - 功能实现: include/npu_demo/Memory.h
    */
    const long long* stride() const;

    /*
    功能说明:
    - 返回运行期维度数。

    使用示例:
    - unsigned long long rank = mem.rank();

    创建者: 神秘人
    最后修改人: 金铲铲大作战

    关联文件:
    - spec: spec/include/api/Memory.md
    - test: test/include/api/test_memory.py
    - 功能实现: include/npu_demo/Memory.h
    */
    unsigned long long rank() const;

    /*
    功能说明:
    - 返回布局格式。

    使用示例:
    - MemoryFormat format = mem.format();

    创建者: 神秘人
    最后修改人: 金铲铲大作战

    关联文件:
    - spec: spec/include/api/Memory.md
    - test: test/include/api/test_memory.py
    - 功能实现: include/npu_demo/Memory.h
    */
    MemoryFormat format() const;

    /*
    功能说明:
    - 返回模板参数指定的内存空间。

    使用示例:
    - MemorySpace space = mem.space();

    创建者: 神秘人
    最后修改人: jcc你莫辜负

    关联文件:
    - spec: spec/include/api/Memory.md
    - test: test/include/api/test_memory.py
    - 功能实现: include/npu_demo/Memory.h
    */
    MemorySpace space() const;

    /*
    功能说明:
    - 返回指定轴的维度长度。

    使用示例:
    - long long n = mem.get_shape(0);

    创建者: 神秘人
    最后修改人: 金铲铲大作战

    关联文件:
    - spec: spec/include/api/Memory.md
    - test: test/include/api/test_memory.py
    - 功能实现: include/npu_demo/Memory.h
    */
    long long get_shape(unsigned long long axis) const;

    /*
    功能说明:
    - 返回指定轴的步长。

    使用示例:
    - long long stride = mem.get_stride(0);

    创建者: 神秘人
    最后修改人: 金铲铲大作战

    关联文件:
    - spec: spec/include/api/Memory.md
    - test: test/include/api/test_memory.py
    - 功能实现: include/npu_demo/Memory.h
    */
    long long get_stride(unsigned long long axis) const;

    /*
    功能说明:
    - 返回成员式子视图，当前 expectation 子集下要求 `ViewT` 与原始元素类型一致。

    使用示例:
    - Memory<GM, float> tile = source.view<float>(offset, size, stride);

    创建者: 金铲铲大作战
    最后修改人: 金铲铲大作战

    关联文件:
    - spec: spec/include/api/Memory.md
    - test: test/include/api/test_memory.py
    - 功能实现: include/npu_demo/Memory.h
    */
    template <typename ViewT>
    Memory<Space, ViewT> view(
        const Vector& offset,
        const Vector& size,
        const Vector& stride) const;

    /*
    功能说明:
    - 返回成员式重解释视图，目标形状通过 `Vector` 提供。

    使用示例:
    - Memory<GM, float> reshaped = source.reshape(shape_vec);

    创建者: 金铲铲大作战
    最后修改人: 金铲铲大作战

    关联文件:
    - spec: spec/include/api/Memory.md
    - test: test/include/api/test_memory.py
    - 功能实现: include/npu_demo/Memory.h
    */
    Memory<Space, T> reshape(const Vector& shape) const;

    /*
    功能说明:
    - 返回元素总数，即 shape 各维乘积。

    使用示例:
    - long long count = mem.element_count();

    创建者: 神秘人
    最后修改人: 金铲铲大作战

    关联文件:
    - spec: spec/include/api/Memory.md
    - test: test/include/api/test_memory.py
    - 功能实现: include/npu_demo/Memory.h
    */
    long long element_count() const;

    /*
    功能说明:
    - 判断当前 stride 是否为行主序连续布局。

    使用示例:
    - bool contiguous = mem.is_contiguous();

    创建者: 神秘人
    最后修改人: 金铲铲大作战

    关联文件:
    - spec: spec/include/api/Memory.md
    - test: test/include/api/test_memory.py
    - 功能实现: include/npu_demo/Memory.h
    */
    bool is_contiguous() const;

    /*
    功能说明:
    - 根据运行期 rank 的多维索引计算线性偏移。
    - 当前实现保留该索引辅助接口，供 include 层实现复用；它不属于本轮稳定公开测试入口。

    使用示例:
    - long long index[2] = {1, 2};
    - long long offset = mem.linear_offset(index);

    创建者: 神秘人
    最后修改人: 金铲铲大作战

    关联文件:
    - spec: spec/include/api/Memory.md
    - test: test/include/api/test_memory.py
    - 功能实现: include/npu_demo/Memory.h
    */
    long long linear_offset(const long long* indices) const;

    /*
    功能说明:
    - 返回索引位置的元素引用。
    - 当前实现保留该索引辅助接口，供 include 层实现复用；它不属于本轮稳定公开测试入口。

    使用示例:
    - long long index[2] = {1, 2};
    - int& value = mem.at(index);

    创建者: 神秘人
    最后修改人: 金铲铲大作战

    关联文件:
    - spec: spec/include/api/Memory.md
    - test: test/include/api/test_memory.py
    - 功能实现: include/npu_demo/Memory.h
    */
    T& at(const long long* indices);

    /*
    功能说明:
    - 返回只读索引位置元素引用。
    - 当前实现保留该索引辅助接口，供 include 层实现复用；它不属于本轮稳定公开测试入口。

    使用示例:
    - long long index[2] = {1, 2};
    - const int& value = const_mem.at(index);

    创建者: 神秘人
    最后修改人: 金铲铲大作战

    关联文件:
    - spec: spec/include/api/Memory.md
    - test: test/include/api/test_memory.py
    - 功能实现: include/npu_demo/Memory.h
    */
    const T& at(const long long* indices) const;

private:
    static constexpr unsigned long long kMaxDim = 8;

    static void contract_or_trap(bool condition);

    void init_shape_and_stride(
        unsigned long long rank,
        const long long* shape,
        const long long* stride);

    void fill_contiguous_stride();

    T* data_;
    unsigned long long rank_;
    long long shape_[kMaxDim];
    long long stride_[kMaxDim];
    MemoryFormat format_;
};

#endif  // KERNELCODE_GENERATE_INCLUDE_API_MEMORY_H_
