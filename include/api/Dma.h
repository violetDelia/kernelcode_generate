/*
功能说明:
- 定义 include/api/Dma.h 的统一 DMA 接口声明。
- 公共层提供 `alloc / fill / slice / deslice / transpose / broadcast` 六类 DMA helper 声明；
  `view` / `reshape` 已移动到 `Memory` 的成员接口。

API 列表:
- `template <MemorySpace Space, typename T> Memory<Space, T> npu_demo::alloc(std::initializer_list<long long> shape, std::initializer_list<long long> stride, MemoryFormat format = MemoryFormat::Norm)`
- `template <MemorySpace Space, typename T> Status npu_demo::fill(Memory<Space, T>& target, const T& value)`
- `template <MemorySpace TargetSpace, MemorySpace SourceSpace, typename T> Status npu_demo::slice(Memory<TargetSpace, T>& target, const Memory<SourceSpace, T>& source, const Vector& offset, const Vector& size, const Vector& stride)`
- `template <MemorySpace TargetSpace, MemorySpace SourceSpace, typename T> Status npu_demo::deslice(Memory<TargetSpace, T>& target, const Memory<SourceSpace, T>& source, const Vector& offset, const Vector& size, const Vector& stride)`
- `template <MemorySpace TargetSpace, MemorySpace SourceSpace, typename TargetType, typename SourceType> Status npu_demo::transpose(Memory<TargetSpace, TargetType>& target, const Memory<SourceSpace, SourceType>& source, const Vector& perm)`
- `template <MemorySpace TargetSpace, MemorySpace SourceSpace, typename TargetType, typename SourceType> Status npu_demo::broadcast(Memory<TargetSpace, TargetType>& target, const Memory<SourceSpace, SourceType>& source)`

helper 清单:
- 无；当前文件只声明公开 DMA helper。

使用示例:
- #include "include/api/Dma.h"
- Vector offset(offset_buf, 1);
- Vector size(size_buf, 1);
- Vector stride(stride_buf, 1);
- Status status = npu_demo::slice(tile, source, offset, size, stride);
- Status filled = npu_demo::fill(tile, 0.0f);

创建者: 大闸蟹
最后修改人: 大闸蟹

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
- 使用标量值填充 `target` 的全部逻辑元素。

使用示例:
- Status status = npu_demo::fill<TSM, float>(target, 0.0f);

创建者: 大闸蟹
最后修改人: 大闸蟹

关联文件:
- spec: spec/include/api/Dma.md
- test: test/include/api/test_dma.py
- 功能实现: include/npu_demo/Dma.h
*/
template <MemorySpace Space, typename T>
Status fill(Memory<Space, T>& target, const T& value);

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

/*
功能说明:
- 按 `perm` 将 source 物化转置到预分配 target，公开参数顺序固定为 `target-first`。

使用示例:
- Status status = npu_demo::transpose(target, source, Vector{1, 0});

创建者: 大闸蟹
最后修改人: 大闸蟹

关联文件:
- spec: spec/include/api/Dma.md
- test: test/include/api/test_dma.py
- 功能实现: include/npu_demo/Dma.h
*/
template <MemorySpace TargetSpace, MemorySpace SourceSpace, typename TargetType, typename SourceType>
Status transpose(
    Memory<TargetSpace, TargetType>& target,
    const Memory<SourceSpace, SourceType>& source,
    const Vector& perm);

/*
功能说明:
- 将 `source` 按 trailing-dimension broadcast 规则物化到预分配 `target`。

使用示例:
- Status status = npu_demo::broadcast<TSM, TSM, float, float>(target, source);

创建者: 大闸蟹
最后修改人: 大闸蟹

关联文件:
- spec: spec/include/api/Dma.md
- test: test/include/api/test_dma.py
- 功能实现: include/npu_demo/Dma.h
*/
template <MemorySpace TargetSpace, MemorySpace SourceSpace, typename TargetType, typename SourceType>
Status broadcast(
    Memory<TargetSpace, TargetType>& target,
    const Memory<SourceSpace, SourceType>& source);

}  // namespace npu_demo

#endif  // KERNELCODE_GENERATE_INCLUDE_API_DMA_H_
