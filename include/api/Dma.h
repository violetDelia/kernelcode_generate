/*
功能说明:
- 定义 include/api/Dma.h 的统一 DMA 接口声明。
- 公共层提供 `alloc / slice / deslice` 三类 DMA helper 声明；
  `view` / `reshape` 已移动到 `Memory` 的成员接口。

使用示例:
- #include "include/api/Dma.h"
- Vector offset(offset_buf, 1);
- Vector size(size_buf, 1);
- Vector stride(stride_buf, 1);
- Status status = npu_demo::slice(tile, source, offset, size, stride);

创建者: 大闸蟹
最后修改人: jcc你莫辜负

关联文件:
- spec: spec/include/api/Dma.md
- test: test/include/api/test_dma.py
- 功能实现: include/npu_demo/Dma.h
*/

#ifndef KERNELCODE_GENERATE_INCLUDE_API_DMA_H_
#define KERNELCODE_GENERATE_INCLUDE_API_DMA_H_

#include <initializer_list>

#include "include/api/Core.h"
#include "include/api/Memory.h"

/*
功能说明:
- 按给定 shape/stride 创建 DMA 临时 `Memory<Space, T>` 视图。
- 该 helper 供 `target=npu_demo` 的 `emit_c/gen_kernel` 合同生成局部 temporary memory。

使用示例:
- Memory<TSM, float> tile = npu_demo::alloc<TSM, float>({16}, {1});

创建者: 小李飞刀
最后修改人: 小李飞刀

关联文件:
- spec: spec/include/api/Dma.md
- test: test/include/api/test_dma.py
- 功能实现: include/npu_demo/Dma.h
*/
namespace npu_demo {

template <MemorySpace Space, typename T>
Memory<Space, T> alloc(
    std::initializer_list<long long> shape,
    std::initializer_list<long long> stride,
    MemoryFormat format = MemoryFormat::Norm);

/*
功能说明:
- 从 source 读取切片并写入预分配 target。

使用示例:
- Status status = npu_demo::slice(tile, source, offset, size, stride);

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
- Status status = npu_demo::deslice(target, tile, offset, size, stride);

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

}  // namespace npu_demo

#endif  // KERNELCODE_GENERATE_INCLUDE_API_DMA_H_
