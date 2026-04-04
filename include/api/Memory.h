/*
功能说明:
- 定义 include/api/Memory.h 的统一 Memory 视图类型与 MemoryFormat/MemorySpace 声明。

使用示例:
- #include "include/api/Memory.h"
- int data[6] = {0, 1, 2, 3, 4, 5};
- long long shape[2] = {2, 3};
- long long stride[2] = {0, 0};
- build_contiguous_stride(shape, 2, stride);
- Memory<int> mem(data, shape, stride, 2, MemoryFormat::CLast, MemorySpace::SM);

创建者: 神秘人
最后修改人: 金铲铲大作战

关联文件:
- spec: spec/include/api/Memory.md
- test: test/include/npu_demo/test_kernel_context.py
- 功能实现: include/npu_demo/Memory.h
*/

#ifndef KERNELCODE_GENERATE_INCLUDE_API_MEMORY_H_
#define KERNELCODE_GENERATE_INCLUDE_API_MEMORY_H_

/*
功能说明:
- 表示 Memory 视图的布局格式枚举。

使用示例:
- MemoryFormat format = MemoryFormat::CLast;

创建者: 神秘人
最后修改人: 金铲铲大作战

关联文件:
- spec: spec/include/api/Memory.md
- test: test/include/npu_demo/test_kernel_context.py
- 功能实现: include/npu_demo/Memory.h
*/
enum class MemoryFormat {
    Norm,
    CLast,
};

/*
功能说明:
- 表示 Memory 视图的逻辑空间枚举。

使用示例:
- MemorySpace space = MemorySpace::SM;

创建者: 神秘人
最后修改人: 金铲铲大作战

关联文件:
- spec: spec/include/api/Memory.md
- test: test/include/npu_demo/test_kernel_context.py
- 功能实现: include/npu_demo/Memory.h
*/
enum class MemorySpace {
    GM,
    SM,
    LM,
    TSM,
    TLM,
};

/*
功能说明:
- 根据 shape 与 rank 生成连续行主序 stride。

使用示例:
- long long shape[2] = {2, 3};
- long long stride[2] = {0, 0};
- build_contiguous_stride(shape, 2, stride);

创建者: 神秘人
最后修改人: 金铲铲大作战

关联文件:
- spec: spec/include/api/Memory.md
- test: test/include/npu_demo/test_kernel_context.py
- 功能实现: include/npu_demo/Memory.h
*/
void build_contiguous_stride(const long long* shape, unsigned long long rank, long long* out_stride);

/*
功能说明:
- 定义统一 Memory 视图模板，记录 data/shape/stride/rank/format/space 元信息。

使用示例:
- int data[6] = {0, 1, 2, 3, 4, 5};
- long long shape[2] = {2, 3};
- long long stride[2] = {0, 0};
- build_contiguous_stride(shape, 2, stride);
- Memory<int> mem(data, shape, stride, 2);

创建者: 神秘人
最后修改人: 金铲铲大作战

关联文件:
- spec: spec/include/api/Memory.md
- test: test/include/npu_demo/test_kernel_context.py
- 功能实现: include/npu_demo/Memory.h
*/
template <typename T>
class Memory {
public:
    /*
    功能说明:
    - 使用显式 rank/shape/stride 构造 Memory 视图。

    使用示例:
    - long long shape[2] = {2, 3};
    - long long stride[2] = {3, 1};
    - Memory<int> mem(data, shape, stride, 2);

    创建者: 神秘人
    最后修改人: 金铲铲大作战

    关联文件:
    - spec: spec/include/api/Memory.md
    - test: test/include/npu_demo/test_kernel_context.py
    - 功能实现: include/npu_demo/Memory.h
    */
    Memory(
        T* data,
        const long long* shape,
        const long long* stride,
        unsigned long long rank,
        MemoryFormat format = MemoryFormat::Norm,
        MemorySpace space = MemorySpace::GM);

    /*
    功能说明:
    - 使用显式 rank/shape 构造连续行主序 Memory 视图，并自动推导 stride。

    使用示例:
    - long long shape[2] = {2, 3};
    - Memory<int> mem(data, shape, 2);

    创建者: 神秘人
    最后修改人: 金铲铲大作战

    关联文件:
    - spec: spec/include/api/Memory.md
    - test: test/include/npu_demo/test_kernel_context.py
    - 功能实现: include/npu_demo/Memory.h
    */
    Memory(
        T* data,
        const long long* shape,
        unsigned long long rank,
        MemoryFormat format = MemoryFormat::Norm,
        MemorySpace space = MemorySpace::GM);

    /*
    功能说明:
    - 返回底层数据指针。

    使用示例:
    - int* ptr = mem.data();

    创建者: 神秘人
    最后修改人: 金铲铲大作战

    关联文件:
    - spec: spec/include/api/Memory.md
    - test: test/include/npu_demo/test_kernel_context.py
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
    - test: test/include/npu_demo/test_kernel_context.py
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
    - test: test/include/npu_demo/test_kernel_context.py
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
    - test: test/include/npu_demo/test_kernel_context.py
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
    - test: test/include/npu_demo/test_kernel_context.py
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
    - test: test/include/npu_demo/test_kernel_context.py
    - 功能实现: include/npu_demo/Memory.h
    */
    MemoryFormat format() const;

    /*
    功能说明:
    - 返回内存空间。

    使用示例:
    - MemorySpace space = mem.space();

    创建者: 神秘人
    最后修改人: 金铲铲大作战

    关联文件:
    - spec: spec/include/api/Memory.md
    - test: test/include/npu_demo/test_kernel_context.py
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
    - test: test/include/npu_demo/test_kernel_context.py
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
    - test: test/include/npu_demo/test_kernel_context.py
    - 功能实现: include/npu_demo/Memory.h
    */
    long long get_stride(unsigned long long axis) const;

    /*
    功能说明:
    - 返回元素总数，即 shape 各维乘积。

    使用示例:
    - long long count = mem.element_count();

    创建者: 神秘人
    最后修改人: 金铲铲大作战

    关联文件:
    - spec: spec/include/api/Memory.md
    - test: test/include/npu_demo/test_kernel_context.py
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
    - test: test/include/npu_demo/test_kernel_context.py
    - 功能实现: include/npu_demo/Memory.h
    */
    bool is_contiguous() const;

    /*
    功能说明:
    - 根据运行期 rank 的多维索引计算线性偏移。

    使用示例:
    - long long index[2] = {1, 2};
    - long long offset = mem.linear_offset(index);

    创建者: 神秘人
    最后修改人: 金铲铲大作战

    关联文件:
    - spec: spec/include/api/Memory.md
    - test: test/include/npu_demo/test_kernel_context.py
    - 功能实现: include/npu_demo/Memory.h
    */
    long long linear_offset(const long long* indices) const;

    /*
    功能说明:
    - 返回索引位置的元素引用。

    使用示例:
    - long long index[2] = {1, 2};
    - int& value = mem.at(index);

    创建者: 神秘人
    最后修改人: 金铲铲大作战

    关联文件:
    - spec: spec/include/api/Memory.md
    - test: test/include/npu_demo/test_kernel_context.py
    - 功能实现: include/npu_demo/Memory.h
    */
    T& at(const long long* indices);

    /*
    功能说明:
    - 返回只读索引位置元素引用。

    使用示例:
    - long long index[2] = {1, 2};
    - const int& value = const_mem.at(index);

    创建者: 神秘人
    最后修改人: 金铲铲大作战

    关联文件:
    - spec: spec/include/api/Memory.md
    - test: test/include/npu_demo/test_kernel_context.py
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
    MemorySpace space_;
};

#endif  // KERNELCODE_GENERATE_INCLUDE_API_MEMORY_H_
