/*
功能说明:
- 定义 include/api/Dma.h 的 view/slice/deslice 统一 DMA 视图接口声明。

使用示例:
- #include "include/api/Dma.h"
- Vector offset(offset_buf, 1);
- Vector size(size_buf, 1);
- Vector stride(stride_buf, 1);
- auto tile = view(source, offset, size, stride);

创建者: 大闸蟹
最后修改人: jcc你莫辜负

关联文件:
- spec: spec/include/api/Dma.md
- test: test/include/api/test_dma.py
- 功能实现: include/npu_demo/Dma.h
*/

#ifndef KERNELCODE_GENERATE_INCLUDE_API_DMA_H_
#define KERNELCODE_GENERATE_INCLUDE_API_DMA_H_

#include "include/api/Core.h"
#include "include/api/Memory.h"

/*
功能说明:
- 返回 source 的逻辑子视图。

使用示例:
- auto sub = view(source, offset, size, stride);

创建者: 大闸蟹
最后修改人: jcc你莫辜负

关联文件:
- spec: spec/include/api/Dma.md
- test: test/include/api/test_dma.py
- 功能实现: include/npu_demo/Dma.h
*/
template <MemorySpace Space, typename T>
Memory<Space, T> view(
    const Memory<Space, T>& source,
    const Vector& offset,
    const Vector& size,
    const Vector& stride);

/*
功能说明:
- 从 source 读取切片并写入预分配 target。

使用示例:
- Status status = slice(tile, source, offset, size, stride);

创建者: 大闸蟹
最后修改人: jcc你莫辜负

关联文件:
- spec: spec/include/api/Dma.md
- test: test/include/api/test_dma.py
- 功能实现: include/npu_demo/Dma.h
*/
template <MemorySpace TargetSpace, MemorySpace SourceSpace, typename T>
Status slice(
    Memory<TargetSpace, T>& target,
    const Memory<SourceSpace, T>& source,
    const Vector& offset,
    const Vector& size,
    const Vector& stride);

/*
功能说明:
- 将 source 块写回 target 的指定区域。

使用示例:
- Status status = deslice(tile, target, offset, size, stride);

创建者: 大闸蟹
最后修改人: jcc你莫辜负

关联文件:
- spec: spec/include/api/Dma.md
- test: test/include/api/test_dma.py
- 功能实现: include/npu_demo/Dma.h
*/
template <MemorySpace SourceSpace, MemorySpace TargetSpace, typename T>
Status deslice(
    const Memory<SourceSpace, T>& source,
    Memory<TargetSpace, T>& target,
    const Vector& offset,
    const Vector& size,
    const Vector& stride);

#endif  // KERNELCODE_GENERATE_INCLUDE_API_DMA_H_
