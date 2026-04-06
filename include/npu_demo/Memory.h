/*
功能说明:
- 提供 include/api/Memory.h 的 npu_demo 实现，补全 Memory<Space, T> 视图方法与 stride 构造逻辑。

使用示例:
- #include "include/npu_demo/Memory.h"
- int data[6] = {0, 1, 2, 3, 4, 5};
- long long shape[2] = {2, 3};
- long long stride[2] = {0, 0};
- build_contiguous_stride(shape, 2, stride);
- Memory<GM, int> mem(data, shape, stride, 2);

创建者: 神秘人
最后修改人: jcc你莫辜负

关联文件:
- spec: spec/include/api/Memory.md
- test: test/include/npu_demo/test_kernel_context.py
- 功能实现: include/npu_demo/Memory.h
*/

#ifndef KERNELCODE_GENERATE_INCLUDE_NPU_DEMO_MEMORY_H_
#define KERNELCODE_GENERATE_INCLUDE_NPU_DEMO_MEMORY_H_

#include "include/api/Memory.h"

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
inline void build_contiguous_stride(const long long* shape, unsigned long long rank, long long* out_stride) {
    long long current = 1;
    for (unsigned long long reverse_index = 0; reverse_index < rank; ++reverse_index) {
        const unsigned long long i = rank - 1 - reverse_index;
        out_stride[i] = current;
        current *= shape[i];
    }
}

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
- test: test/include/npu_demo/test_kernel_context.py
- 功能实现: include/npu_demo/Memory.h
*/
template <MemorySpace Space, typename T>
inline Memory<Space, T>::Memory(
    T* data,
    const long long* shape,
    const long long* stride,
    unsigned long long rank,
    MemoryFormat format)
    : data_(data), rank_(0), format_(format) {
    init_shape_and_stride(rank, shape, stride);
}

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
- test: test/include/npu_demo/test_kernel_context.py
- 功能实现: include/npu_demo/Memory.h
*/
template <MemorySpace Space, typename T>
inline Memory<Space, T>::Memory(
    T* data,
    const long long* shape,
    unsigned long long rank,
    MemoryFormat format)
    : data_(data), rank_(0), format_(format) {
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
- spec: spec/include/api/Memory.md
- test: test/include/npu_demo/test_kernel_context.py
- 功能实现: include/npu_demo/Memory.h
*/
template <MemorySpace Space, typename T>
inline T* Memory<Space, T>::data() {
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
- spec: spec/include/api/Memory.md
- test: test/include/npu_demo/test_kernel_context.py
- 功能实现: include/npu_demo/Memory.h
*/
template <MemorySpace Space, typename T>
inline const T* Memory<Space, T>::data() const {
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
- spec: spec/include/api/Memory.md
- test: test/include/npu_demo/test_kernel_context.py
- 功能实现: include/npu_demo/Memory.h
*/
template <MemorySpace Space, typename T>
inline const long long* Memory<Space, T>::shape() const {
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
- spec: spec/include/api/Memory.md
- test: test/include/npu_demo/test_kernel_context.py
- 功能实现: include/npu_demo/Memory.h
*/
template <MemorySpace Space, typename T>
inline const long long* Memory<Space, T>::stride() const {
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
- spec: spec/include/api/Memory.md
- test: test/include/npu_demo/test_kernel_context.py
- 功能实现: include/npu_demo/Memory.h
*/
template <MemorySpace Space, typename T>
inline unsigned long long Memory<Space, T>::rank() const {
    return rank_;
}

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
template <MemorySpace Space, typename T>
inline MemoryFormat Memory<Space, T>::format() const {
    return format_;
}

/*
功能说明:
- 返回模板参数指定的内存空间。

使用示例:
- MemorySpace space = mem.space();

创建者: 神秘人
最后修改人: jcc你莫辜负

关联文件:
- spec: spec/include/api/Memory.md
- test: test/include/npu_demo/test_kernel_context.py
- 功能实现: include/npu_demo/Memory.h
*/
template <MemorySpace Space, typename T>
inline MemorySpace Memory<Space, T>::space() const {
    return Space;
}

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
template <MemorySpace Space, typename T>
inline long long Memory<Space, T>::get_shape(unsigned long long axis) const {
    return shape_[axis];
}

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
template <MemorySpace Space, typename T>
inline long long Memory<Space, T>::get_stride(unsigned long long axis) const {
    return stride_[axis];
}

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
template <MemorySpace Space, typename T>
inline long long Memory<Space, T>::element_count() const {
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
- spec: spec/include/api/Memory.md
- test: test/include/npu_demo/test_kernel_context.py
- 功能实现: include/npu_demo/Memory.h
*/
template <MemorySpace Space, typename T>
inline bool Memory<Space, T>::is_contiguous() const {
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
- spec: spec/include/api/Memory.md
- test: test/include/npu_demo/test_kernel_context.py
- 功能实现: include/npu_demo/Memory.h
*/
template <MemorySpace Space, typename T>
inline long long Memory<Space, T>::linear_offset(const long long* indices) const {
    long long offset = 0;
    for (unsigned long long i = 0; i < rank_; ++i) {
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
最后修改人: 金铲铲大作战

关联文件:
- spec: spec/include/api/Memory.md
- test: test/include/npu_demo/test_kernel_context.py
- 功能实现: include/npu_demo/Memory.h
*/
template <MemorySpace Space, typename T>
inline T& Memory<Space, T>::at(const long long* indices) {
    return data_[linear_offset(indices)];
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
- spec: spec/include/api/Memory.md
- test: test/include/npu_demo/test_kernel_context.py
- 功能实现: include/npu_demo/Memory.h
*/
template <MemorySpace Space, typename T>
inline const T& Memory<Space, T>::at(const long long* indices) const {
    return data_[linear_offset(indices)];
}

template <MemorySpace Space, typename T>
inline void Memory<Space, T>::contract_or_trap(bool condition) {
    if (!condition) {
#if defined(__clang__) || defined(__GNUC__)
        __builtin_trap();
#else
        *(volatile int*)0 = 0;
#endif
    }
}

template <MemorySpace Space, typename T>
inline void Memory<Space, T>::init_shape_and_stride(
    unsigned long long rank,
    const long long* shape,
    const long long* stride) {
    contract_or_trap(rank > 0);
    contract_or_trap(rank <= kMaxDim);
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

template <MemorySpace Space, typename T>
inline void Memory<Space, T>::fill_contiguous_stride() {
    long long current = 1;
    for (unsigned long long reverse_index = 0; reverse_index < rank_; ++reverse_index) {
        const unsigned long long i = rank_ - 1 - reverse_index;
        stride_[i] = current;
        current *= shape_[i];
    }
}

#endif  // KERNELCODE_GENERATE_INCLUDE_NPU_DEMO_MEMORY_H_
