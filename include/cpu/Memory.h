/*
功能说明:
- 定义 cpu::Memory 纯头文件张量视图模板，记录 data/shape/stride/rank/format/space 元信息。

使用示例:
- #include "include/cpu/Memory.h"
- int data[6] = {0, 1, 2, 3, 4, 5};
- long long shape[2] = {2, 3};
- cpu::Memory<int> mem(data, 2, shape);

创建者: 神秘人
最后修改人: 金铲铲大作战

关联文件:
- spec: spec/include/cpu/cpu.md
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

static constexpr unsigned long long MAX_DIM = 8;

template <typename T>
class Memory {
public:
    /*
    功能说明:
    - 使用显式 rank/shape/stride 构造张量视图。

    使用示例:
    - long long shape[2] = {2, 3};
    - long long stride[2] = {3, 1};
    - cpu::Memory<int> mem(data, 2, shape, stride);

    创建者: 神秘人
    最后修改人: 金铲铲大作战

    关联文件:
    - spec: spec/include/cpu/cpu.md
    - test: test/include/cpu/test_memory.py
    - 功能实现: include/cpu/Memory.h
    */
    Memory(
        T* data,
        unsigned long long rank,
        const long long* shape,
        const long long* stride,
        MemoryFormat format = MemoryFormat::Norm,
        MemorySpace space = MemorySpace::GM)
        : data_(data), rank_(0), format_(format), space_(space) {
        init_shape_and_stride(rank, shape, stride);
    }

    /*
    功能说明:
    - 使用显式 rank/shape 构造连续行主序张量视图，并自动推导 stride。

    使用示例:
    - long long shape[2] = {2, 3};
    - cpu::Memory<int> mem(data, 2, shape);

    创建者: 神秘人
    最后修改人: 金铲铲大作战

    关联文件:
    - spec: spec/include/cpu/cpu.md
    - test: test/include/cpu/test_memory.py
    - 功能实现: include/cpu/Memory.h
    */
    Memory(
        T* data,
        unsigned long long rank,
        const long long* shape,
        MemoryFormat format = MemoryFormat::Norm,
        MemorySpace space = MemorySpace::GM)
        : data_(data), rank_(0), format_(format), space_(space) {
        init_shape_and_stride(rank, shape, 0);
    }

    /*
    功能说明:
    - 返回底层数据指针。

    使用示例:
    - int* ptr = mem.data();

    创建者: 神秘人
    最后修改人: 金铲铲大作战

    关联文件:
    - spec: spec/include/cpu/cpu.md
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
    最后修改人: 金铲铲大作战

    关联文件:
    - spec: spec/include/cpu/cpu.md
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
    最后修改人: 金铲铲大作战

    关联文件:
    - spec: spec/include/cpu/cpu.md
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
    最后修改人: 金铲铲大作战

    关联文件:
    - spec: spec/include/cpu/cpu.md
    - test: test/include/cpu/test_memory.py
    - 功能实现: include/cpu/Memory.h
    */
    const long long* stride() const {
        return stride_;
    }

    /*
    功能说明:
    - 返回运行期维度数。

    使用示例:
    - unsigned long long rank = mem.rank();

    创建者: 神秘人
    最后修改人: 金铲铲大作战

    关联文件:
    - spec: spec/include/cpu/cpu.md
    - test: test/include/cpu/test_memory.py
    - 功能实现: include/cpu/Memory.h
    */
    unsigned long long rank() const {
        return rank_;
    }

    /*
    功能说明:
    - 返回布局格式。

    使用示例:
    - cpu::MemoryFormat format = mem.format();

    创建者: 神秘人
    最后修改人: 金铲铲大作战

    关联文件:
    - spec: spec/include/cpu/cpu.md
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
    最后修改人: 金铲铲大作战

    关联文件:
    - spec: spec/include/cpu/cpu.md
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
    最后修改人: 金铲铲大作战

    关联文件:
    - spec: spec/include/cpu/cpu.md
    - test: test/include/cpu/test_memory.py
    - 功能实现: include/cpu/Memory.h
    */
    long long element_count() const {
        long long count = 1;
        for (unsigned long long i = 0; i < rank_; ++i) {
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
    最后修改人: 金铲铲大作战

    关联文件:
    - spec: spec/include/cpu/cpu.md
    - test: test/include/cpu/test_memory.py
    - 功能实现: include/cpu/Memory.h
    */
    bool is_contiguous() const {
        long long expected = 1;
        for (unsigned long long reverse_index = 0; reverse_index < rank_; ++reverse_index) {
            const unsigned long long i = rank_ - 1 - reverse_index;
            if (stride_[i] != expected) {
                return false;
            }
            expected *= shape_[i];
        }
        return true;
    }

    /*
    功能说明:
    - 根据运行期 rank 的多维索引计算线性偏移。

    使用示例:
    - long long index[2] = {1, 2};
    - long long offset = mem.linear_offset(index);

    创建者: 神秘人
    最后修改人: 金铲铲大作战

    关联文件:
    - spec: spec/include/cpu/cpu.md
    - test: test/include/cpu/test_memory.py
    - 功能实现: include/cpu/Memory.h
    */
    long long linear_offset(const long long* indices) const {
        long long offset = 0;
        for (unsigned long long i = 0; i < rank_; ++i) {
            offset += indices[i] * stride_[i];
        }
        return offset;
    }

    template <unsigned long long Rank>
    long long linear_offset(const long long (&indices)[Rank]) const {
        return linear_offset(static_cast<const long long*>(indices));
    }

    /*
    功能说明:
    - 返回索引位置的元素引用。

    使用示例:
    - long long index[2] = {1, 2};
    - int& value = mem.at(index);

    创建者: 神秘人
    最后修改人: 金铲铲大作战

    关联文件:
    - spec: spec/include/cpu/cpu.md
    - test: test/include/cpu/test_memory.py
    - 功能实现: include/cpu/Memory.h
    */
    T& at(const long long* indices) {
        return data_[linear_offset(indices)];
    }

    template <unsigned long long Rank>
    T& at(const long long (&indices)[Rank]) {
        return at(static_cast<const long long*>(indices));
    }

    /*
    功能说明:
    - 返回只读索引位置元素引用。

    使用示例:
    - long long index[2] = {1, 2};
    - const int& value = const_mem.at(index);

    创建者: 神秘人
    最后修改人: 金铲铲大作战

    关联文件:
    - spec: spec/include/cpu/cpu.md
    - test: test/include/cpu/test_memory.py
    - 功能实现: include/cpu/Memory.h
    */
    const T& at(const long long* indices) const {
        return data_[linear_offset(indices)];
    }

    template <unsigned long long Rank>
    const T& at(const long long (&indices)[Rank]) const {
        return at(static_cast<const long long*>(indices));
    }

private:
    static void contract_or_trap(bool condition) {
        if (!condition) {
#if defined(__clang__) || defined(__GNUC__)
            __builtin_trap();
#else
            *(volatile int*)0 = 0;
#endif
        }
    }

    void init_shape_and_stride(
        unsigned long long rank,
        const long long* shape,
        const long long* stride) {
        contract_or_trap(rank > 0);
        contract_or_trap(rank <= MAX_DIM);
        rank_ = rank;
        for (unsigned long long i = 0; i < rank_; ++i) {
            shape_[i] = shape[i];
        }
        if (stride != 0) {
            for (unsigned long long i = 0; i < rank_; ++i) {
                stride_[i] = stride[i];
            }
            return;
        }
        fill_contiguous_stride();
    }

    void fill_contiguous_stride() {
        long long current = 1;
        for (unsigned long long reverse_index = 0; reverse_index < rank_; ++reverse_index) {
            const unsigned long long i = rank_ - 1 - reverse_index;
            stride_[i] = current;
            current *= shape_[i];
        }
    }

    T* data_;
    unsigned long long rank_;
    long long shape_[MAX_DIM];
    long long stride_[MAX_DIM];
    MemoryFormat format_;
    MemorySpace space_;
};

}  // namespace cpu

#endif  // KERNELCODE_GENERATE_INCLUDE_CPU_MEMORY_H_
