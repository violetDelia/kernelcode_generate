/*
功能说明:
- 定义 cpu::Memory 纯头文件张量视图模板，记录 data/shape/stride/format/space 元信息。

使用示例:
- #include "include/cpu/Memory.h"
- int data[6] = {0, 1, 2, 3, 4, 5};
- long long shape[2] = {2, 3};
- cpu::Memory<int, 2> mem(data, shape);

创建者: 神秘人
最后修改人: 神秘人

关联文件:
- spec: spec/include/cpu/Memory.md
- test: test/include/cpu/test_memory.py
- 功能实现: include/cpu/Memory.h
*/

#ifndef KERNELCODE_GENERATE_INCLUDE_CPU_MEMORY_H_
#define KERNELCODE_GENERATE_INCLUDE_CPU_MEMORY_H_

namespace cpu {

enum class MemoryFormat {
    Norm,
    CLast,
};

enum class MemorySpace {
    GM,
    SM,
    LM,
    TSM,
    TLM,
};

template <typename T, unsigned long long Rank>
class Memory {
public:
    static_assert(Rank > 0, "cpu::Memory Rank must be greater than zero");

    /*
    功能说明:
    - 使用显式 shape/stride 构造张量视图。

    使用示例:
    - long long shape[2] = {2, 3};
    - long long stride[2] = {3, 1};
    - cpu::Memory<int, 2> mem(data, shape, stride);

    创建者: 神秘人
    最后修改人: 神秘人

    关联文件:
    - spec: spec/include/cpu/Memory.md
    - test: test/include/cpu/test_memory.py
    - 功能实现: include/cpu/Memory.h
    */
    Memory(
        T* data,
        const long long (&shape)[Rank],
        const long long (&stride)[Rank],
        MemoryFormat format = MemoryFormat::Norm,
        MemorySpace space = MemorySpace::GM)
        : data_(data), format_(format), space_(space) {
        copy_array(shape, shape_);
        copy_array(stride, stride_);
    }

    /*
    功能说明:
    - 使用 shape 构造连续行主序张量视图，并自动推导 stride。

    使用示例:
    - long long shape[2] = {2, 3};
    - cpu::Memory<int, 2> mem(data, shape);

    创建者: 神秘人
    最后修改人: 神秘人

    关联文件:
    - spec: spec/include/cpu/Memory.md
    - test: test/include/cpu/test_memory.py
    - 功能实现: include/cpu/Memory.h
    */
    Memory(
        T* data,
        const long long (&shape)[Rank],
        MemoryFormat format = MemoryFormat::Norm,
        MemorySpace space = MemorySpace::GM)
        : data_(data), format_(format), space_(space) {
        copy_array(shape, shape_);
        fill_contiguous_stride();
    }

    /*
    功能说明:
    - 返回底层数据指针。

    使用示例:
    - int* ptr = mem.data();

    创建者: 神秘人
    最后修改人: 神秘人

    关联文件:
    - spec: spec/include/cpu/Memory.md
    - test: test/include/cpu/test_memory.py
    - 功能实现: include/cpu/Memory.h
    */
    T* data() {
        return data_;
    }

    /*
    功能说明:
    - 返回只读底层数据指针。

    使用示例:
    - const int* ptr = const_mem.data();

    创建者: 神秘人
    最后修改人: 神秘人

    关联文件:
    - spec: spec/include/cpu/Memory.md
    - test: test/include/cpu/test_memory.py
    - 功能实现: include/cpu/Memory.h
    */
    const T* data() const {
        return data_;
    }

    /*
    功能说明:
    - 返回 shape 数组首地址。

    使用示例:
    - const long long* shape = mem.shape();

    创建者: 神秘人
    最后修改人: 神秘人

    关联文件:
    - spec: spec/include/cpu/Memory.md
    - test: test/include/cpu/test_memory.py
    - 功能实现: include/cpu/Memory.h
    */
    const long long* shape() const {
        return shape_;
    }

    /*
    功能说明:
    - 返回 stride 数组首地址。

    使用示例:
    - const long long* stride = mem.stride();

    创建者: 神秘人
    最后修改人: 神秘人

    关联文件:
    - spec: spec/include/cpu/Memory.md
    - test: test/include/cpu/test_memory.py
    - 功能实现: include/cpu/Memory.h
    */
    const long long* stride() const {
        return stride_;
    }

    /*
    功能说明:
    - 返回编译期固定维度数。

    使用示例:
    - unsigned long long rank = mem.rank();

    创建者: 神秘人
    最后修改人: 神秘人

    关联文件:
    - spec: spec/include/cpu/Memory.md
    - test: test/include/cpu/test_memory.py
    - 功能实现: include/cpu/Memory.h
    */
    static constexpr unsigned long long rank() {
        return Rank;
    }

    /*
    功能说明:
    - 返回布局格式。

    使用示例:
    - cpu::MemoryFormat format = mem.format();

    创建者: 神秘人
    最后修改人: 神秘人

    关联文件:
    - spec: spec/include/cpu/Memory.md
    - test: test/include/cpu/test_memory.py
    - 功能实现: include/cpu/Memory.h
    */
    MemoryFormat format() const {
        return format_;
    }

    /*
    功能说明:
    - 返回内存空间。

    使用示例:
    - cpu::MemorySpace space = mem.space();

    创建者: 神秘人
    最后修改人: 神秘人

    关联文件:
    - spec: spec/include/cpu/Memory.md
    - test: test/include/cpu/test_memory.py
    - 功能实现: include/cpu/Memory.h
    */
    MemorySpace space() const {
        return space_;
    }

    /*
    功能说明:
    - 返回元素总数，即 shape 各维乘积。

    使用示例:
    - long long count = mem.element_count();

    创建者: 神秘人
    最后修改人: 神秘人

    关联文件:
    - spec: spec/include/cpu/Memory.md
    - test: test/include/cpu/test_memory.py
    - 功能实现: include/cpu/Memory.h
    */
    long long element_count() const {
        long long count = 1;
        for (unsigned long long i = 0; i < Rank; ++i) {
            count *= shape_[i];
        }
        return count;
    }

    /*
    功能说明:
    - 判断当前 stride 是否为行主序连续布局。

    使用示例:
    - bool contiguous = mem.is_contiguous();

    创建者: 神秘人
    最后修改人: 神秘人

    关联文件:
    - spec: spec/include/cpu/Memory.md
    - test: test/include/cpu/test_memory.py
    - 功能实现: include/cpu/Memory.h
    */
    bool is_contiguous() const {
        long long expected = 1;
        for (unsigned long long reverse_index = 0; reverse_index < Rank; ++reverse_index) {
            const unsigned long long i = Rank - 1 - reverse_index;
            if (stride_[i] != expected) {
                return false;
            }
            expected *= shape_[i];
        }
        return true;
    }

    /*
    功能说明:
    - 根据多维索引计算线性偏移。

    使用示例:
    - long long index[2] = {1, 2};
    - long long offset = mem.linear_offset(index);

    创建者: 神秘人
    最后修改人: 神秘人

    关联文件:
    - spec: spec/include/cpu/Memory.md
    - test: test/include/cpu/test_memory.py
    - 功能实现: include/cpu/Memory.h
    */
    long long linear_offset(const long long (&indices)[Rank]) const {
        long long offset = 0;
        for (unsigned long long i = 0; i < Rank; ++i) {
            offset += indices[i] * stride_[i];
        }
        return offset;
    }

    /*
    功能说明:
    - 返回索引位置的元素引用。

    使用示例:
    - long long index[2] = {1, 2};
    - int& value = mem.at(index);

    创建者: 神秘人
    最后修改人: 神秘人

    关联文件:
    - spec: spec/include/cpu/Memory.md
    - test: test/include/cpu/test_memory.py
    - 功能实现: include/cpu/Memory.h
    */
    T& at(const long long (&indices)[Rank]) {
        return data_[linear_offset(indices)];
    }

    /*
    功能说明:
    - 返回只读索引位置元素引用。

    使用示例:
    - long long index[2] = {1, 2};
    - const int& value = const_mem.at(index);

    创建者: 神秘人
    最后修改人: 神秘人

    关联文件:
    - spec: spec/include/cpu/Memory.md
    - test: test/include/cpu/test_memory.py
    - 功能实现: include/cpu/Memory.h
    */
    const T& at(const long long (&indices)[Rank]) const {
        return data_[linear_offset(indices)];
    }

private:
    static void copy_array(const long long (&src)[Rank], long long (&dst)[Rank]) {
        for (unsigned long long i = 0; i < Rank; ++i) {
            dst[i] = src[i];
        }
    }

    void fill_contiguous_stride() {
        long long current = 1;
        for (unsigned long long reverse_index = 0; reverse_index < Rank; ++reverse_index) {
            const unsigned long long i = Rank - 1 - reverse_index;
            stride_[i] = current;
            current *= shape_[i];
        }
    }

    T* data_;
    long long shape_[Rank];
    long long stride_[Rank];
    MemoryFormat format_;
    MemorySpace space_;
};

}  // namespace cpu

#endif  // KERNELCODE_GENERATE_INCLUDE_CPU_MEMORY_H_
