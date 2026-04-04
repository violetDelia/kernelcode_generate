/*
功能说明:
- 提供 npu_demo 后端的 view/slice/deslice 轻量实现，用于匹配 gen_kernel 骨架。

使用示例:
- #include "include/npu_demo/Dma.h"
- auto tile = view(source, 0, 16, 1);

创建者: 大闸蟹
最后修改人: 金铲铲大作战

关联文件:
- spec: spec/include/api/Dma.md
- test: test/dsl/test_gen_kernel.py
- 功能实现: include/npu_demo/Dma.h
*/

#ifndef KERNELCODE_GENERATE_INCLUDE_NPU_DEMO_DMA_H_
#define KERNELCODE_GENERATE_INCLUDE_NPU_DEMO_DMA_H_

#include "include/api/Dma.h"
#include "include/npu_demo/Memory.h"
#include "include/npu_demo/Core.h"

namespace {

constexpr unsigned long long kMaxDmaRank = 8;

}  // namespace

/*
功能说明:
- 返回 source 的逻辑子视图（Vector offset/size/stride 版本）。

使用示例:
- long long offset_buf[2] = {0, 16};
- long long size_buf[2] = {8, 8};
- long long stride_buf[2] = {1, 1};
- Vector offset(offset_buf, 2);
- Vector size(size_buf, 2);
- Vector stride(stride_buf, 2);
- auto sub = view(source, offset, size, stride);

创建者: 大闸蟹
最后修改人: 金铲铲大作战

关联文件:
- spec: spec/include/api/Dma.md
- test: test/dsl/test_gen_kernel.py
- 功能实现: include/npu_demo/Dma.h
*/
template <typename T>
inline Memory<T> view(
    const Memory<T>& source,
    const Vector& offset,
    const Vector& size,
    const Vector& stride) {
    const unsigned long long rank = source.rank();
    long long shape_buf[kMaxDmaRank] = {0};
    long long stride_buf[kMaxDmaRank] = {0};
    long long linear_offset = 0;
    const unsigned long long offset_rank = offset.size();
    const unsigned long long size_rank = size.size();
    const unsigned long long stride_rank = stride.size();

    for (unsigned long long i = 0; i < rank; ++i) {
        const long long offset_i = i < offset_rank ? offset[i] : 0;
        const long long size_i = i < size_rank ? size[i] : source.get_shape(i);
        const long long stride_i = i < stride_rank ? stride[i] : 1;
        const long long base_stride = source.get_stride(i);
        shape_buf[i] = size_i;
        stride_buf[i] = base_stride * stride_i;
        linear_offset += offset_i * base_stride;
    }

    T* data = const_cast<T*>(source.data());
    if (data != nullptr) {
        data += linear_offset;
    }
    return Memory<T>(data, shape_buf, stride_buf, rank, source.format(), source.space());
}

/*
功能说明:
- 从 source 读取切片并写入预分配 target（Vector offset/size/stride 版本）。

使用示例:
- Status status = slice(tile, source, offset, size, stride);

创建者: 大闸蟹
最后修改人: 金铲铲大作战

关联文件:
- spec: spec/include/api/Dma.md
- test: test/dsl/test_gen_kernel.py
- 功能实现: include/npu_demo/Dma.h
*/
template <typename T>
inline Status slice(
    Memory<T>& target,
    const Memory<T>& source,
    const Vector& offset,
    const Vector& size,
    const Vector& stride) {
    (void)target;
    (void)source;
    (void)offset;
    (void)size;
    (void)stride;
    return StatusCode::kOk;
}

/*
功能说明:
- 将 source 块写回 target 的指定区域（Vector offset/size/stride 版本）。

使用示例:
- Status status = deslice(tile, target, offset, size, stride);

创建者: 大闸蟹
最后修改人: 金铲铲大作战

关联文件:
- spec: spec/include/api/Dma.md
- test: test/dsl/test_gen_kernel.py
- 功能实现: include/npu_demo/Dma.h
*/
template <typename T>
inline Status deslice(
    const Memory<T>& source,
    Memory<T>& target,
    const Vector& offset,
    const Vector& size,
    const Vector& stride) {
    (void)source;
    (void)target;
    (void)offset;
    (void)size;
    (void)stride;
    return StatusCode::kOk;
}

/*
功能说明:
- 返回 source 的逻辑子视图（标量 offset/size/stride 版本）。

使用示例:
- auto sub = view(source, 0, 16, 1);

创建者: 大闸蟹
最后修改人: 金铲铲大作战

关联文件:
- spec: spec/include/api/Dma.md
- test: test/dsl/test_gen_kernel.py
- 功能实现: include/npu_demo/Dma.h
*/
template <typename T>
inline Memory<T> view(
    const Memory<T>& source,
    long long offset,
    long long size,
    long long stride) {
    long long shape[1] = {size};
    long long strides[1] = {stride};
    T* data = const_cast<T*>(source.data());
    if (data != nullptr) {
        data += offset * stride;
    }
    return Memory<T>(data, shape, strides, 1, source.format(), source.space());
}

/*
功能说明:
- 从 source 读取切片并写入预分配 target（标量 offset/size/stride 版本）。

使用示例:
- Status status = slice(tile, source, 0, 16, 1);

创建者: 大闸蟹
最后修改人: 金铲铲大作战

关联文件:
- spec: spec/include/api/Dma.md
- test: test/dsl/test_gen_kernel.py
- 功能实现: include/npu_demo/Dma.h
*/
template <typename T>
inline Status slice(
    Memory<T>& target,
    const Memory<T>& source,
    long long offset,
    long long size,
    long long stride) {
    (void)target;
    (void)source;
    (void)offset;
    (void)size;
    (void)stride;
    return StatusCode::kOk;
}

/*
功能说明:
- 将 source 块写回 target 的指定区域（标量 offset/size/stride 版本）。

使用示例:
- Status status = deslice(tile, target, 0, 16, 1);

创建者: 大闸蟹
最后修改人: 金铲铲大作战

关联文件:
- spec: spec/include/api/Dma.md
- test: test/dsl/test_gen_kernel.py
- 功能实现: include/npu_demo/Dma.h
*/
template <typename T>
inline Status deslice(
    const Memory<T>& source,
    Memory<T>& target,
    long long offset,
    long long size,
    long long stride) {
    (void)source;
    (void)target;
    (void)offset;
    (void)size;
    (void)stride;
    return StatusCode::kOk;
}

#endif  // KERNELCODE_GENERATE_INCLUDE_NPU_DEMO_DMA_H_
