/*
功能说明:
- 定义 npu_demo 单入口 include，透传 include/api 的统一声明并汇聚后端实现。
 - 当前聚合 `Core / Memory / Dma / Kernel / Arch / cost` 六类头文件，不再重新聚合 `Nn.h`。
- 调用方应通过 `npu_demo::` 消费后端 public function；基础类型继续沿用 include/api 的公开类型。

API 列表:
- `namespace npu_demo`
- `template <long long block, long long thread, long long subthread, long long shared_memory_size, typename Callable, typename... Args> Status npu_demo::launch(Callable&& callee, Args&&... args)`
- `class npu_demo::KernelContext`
- `npu_demo::thread_id() -> S_INT`
- `npu_demo::thread_num() -> S_INT`
- `npu_demo::barrier(std::initializer_list<BarrierVisibility> visibility, BarrierScope scope) -> void`
- `template <MemorySpace Space> npu_demo::get_dynamic_memory() -> DynamicMemoryRef<Space>`
- `void npu_demo::build_contiguous_stride(const long long* shape, unsigned long long rank, long long* out_stride)`
- `template <MemorySpace Space, typename T> Memory<Space, T> npu_demo::alloc(std::initializer_list<long long> shape, std::initializer_list<long long> stride, MemoryFormat format = MemoryFormat::Norm)`
- `template <MemorySpace Space, typename T> Status npu_demo::fill(Memory<Space, T>& target, const T& value)`
- `template <MemorySpace TargetSpace, MemorySpace SourceSpace, typename T> Status npu_demo::slice(Memory<TargetSpace, T>& target, const Memory<SourceSpace, T>& source, const Vector& offset, const Vector& size, const Vector& stride)`
- `template <MemorySpace TargetSpace, MemorySpace SourceSpace, typename T> Status npu_demo::deslice(Memory<TargetSpace, T>& target, const Memory<SourceSpace, T>& source, const Vector& offset, const Vector& size, const Vector& stride)`
- `template <MemorySpace TargetSpace, MemorySpace SourceSpace, typename TargetType, typename SourceType> Status npu_demo::transpose(Memory<TargetSpace, TargetType>& target, const Memory<SourceSpace, SourceType>& source, const Vector& perm)`
- `template <MemorySpace TargetSpace, MemorySpace SourceSpace, typename TargetType, typename SourceType> Status npu_demo::broadcast(Memory<TargetSpace, TargetType>& target, const Memory<SourceSpace, SourceType>& source)`
- `namespace npu_demo::cost`

helper 清单:
- 无；当前文件只做公开聚合入口，不承接独立 helper 实现。

使用示例:
- #include "include/npu_demo/npu_demo.h"
- Status status = npu_demo::launch<1, 4, 1, 0>(kernel_body, output);

创建者: 朽木露琪亚
最后修改人: 大闸蟹

关联文件:
- spec: [spec/include/npu_demo/npu_demo.md](spec/include/npu_demo/npu_demo.md)
- test: [test/include/npu_demo/test_public_namespace.py](test/include/npu_demo/test_public_namespace.py)
- 功能实现: [include/npu_demo/npu_demo.h](include/npu_demo/npu_demo.h)
*/

#ifndef KERNELCODE_GENERATE_INCLUDE_NPU_DEMO_NPU_DEMO_H_
#define KERNELCODE_GENERATE_INCLUDE_NPU_DEMO_NPU_DEMO_H_

#include "include/api/Arch.h"
#include "include/api/Memory.h"
#include "include/api/Dma.h"
#include "include/api/Kernel.h"
#include "include/api/cost/Core.h"
#include "include/api/cost/Dma.h"
#include "include/api/cost/Kernel.h"
#include "include/npu_demo/Core.h"
#include "include/npu_demo/Arch.h"
#include "include/npu_demo/Memory.h"
#include "include/npu_demo/Dma.h"
#include "include/npu_demo/Kernel.h"
#include "include/npu_demo/cost/Core.h"
#include "include/npu_demo/cost/Dma.h"
#include "include/npu_demo/cost/Kernel.h"

#endif  // KERNELCODE_GENERATE_INCLUDE_NPU_DEMO_NPU_DEMO_H_
