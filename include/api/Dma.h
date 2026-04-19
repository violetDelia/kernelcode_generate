/*
功能说明:
- 定义 include/api/Dma.h 的统一 DMA 接口声明。
- 公共层只保留 `slice` / `deslice`；`view` / `reshape` 已移动到 `Memory` 的成员接口。

使用示例:
- #include "include/api/Dma.h"
- Vector offset(offset_buf, 1);
- Vector size(size_buf, 1);
- Vector stride(stride_buf, 1);
- Status status = slice(tile, source, offset, size, stride);

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
- 将 source 块写回 target 的指定区域，公开参数顺序固定为 `target-first`。

使用示例:
- Status status = deslice(target, tile, offset, size, stride);

创建者: 大闸蟹
最后修改人: jcc你莫辜负

关联文件:
- spec: spec/include/api/Dma.md
- test: test/include/api/test_dma.py
- 功能实现: include/npu_demo/Dma.h
*/
template <MemorySpace TargetSpace, MemorySpace SourceSpace, typename T>
Status deslice(
    Memory<TargetSpace, T>& target,
    const Memory<SourceSpace, T>& source,
    const Vector& offset,
    const Vector& size,
    const Vector& stride);

#endif  // KERNELCODE_GENERATE_INCLUDE_API_DMA_H_
