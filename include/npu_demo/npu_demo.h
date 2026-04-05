/*
功能说明:
- 定义 npu_demo 后端私有 KernelContext 头文件接口，提供固定硬件模板下的 id/count 查询与动态片上内存查询。
- 作为 npu_demo 单入口 include，透传 include/api/Memory.h、Dma.h、Nn.h 并汇聚后端实现。

使用示例:
- #include "include/npu_demo/npu_demo.h"
- npu_demo::KernelContext ctx;
- long long bid = ctx.block_id();
- auto tsm = ctx.get_dynamic_memory<float>(npu_demo::MemorySpace::TSM);

创建者: 朽木露琪亚
最后修改人: jcc你莫辜负

关联文件:
- spec: [spec/include/npu_demo/npu_demo.md](spec/include/npu_demo/npu_demo.md)
- test: [test/include/npu_demo/test_kernel_context.py](test/include/npu_demo/test_kernel_context.py)
- 功能实现: [include/npu_demo/npu_demo.h](include/npu_demo/npu_demo.h)
*/

#ifndef KERNELCODE_GENERATE_INCLUDE_NPU_DEMO_NPU_DEMO_H_
#define KERNELCODE_GENERATE_INCLUDE_NPU_DEMO_NPU_DEMO_H_

#include <stdexcept>

#include "include/api/Memory.h"
#include "include/api/Dma.h"
#include "include/api/Nn.h"
#include "include/npu_demo/Core.h"
#include "include/npu_demo/Memory.h"
#include "include/npu_demo/Dma.h"
#include "include/npu_demo/Nn.h"

namespace npu_demo {

namespace detail {

static constexpr long long kBlockId = 1;
static constexpr long long kBlockNum = 6;
static constexpr long long kThreadId = 3;
static constexpr long long kThreadNum = 8;
static constexpr long long kSubthreadId = 0;
static constexpr long long kSubthreadNum = 1;
static constexpr long long kSmMemorySize = 0;
static constexpr long long kLmMemorySize = 0;
static constexpr long long kTsmMemorySize = 24576;
static constexpr long long kTlmMemorySize = 2048;

/*
功能说明:
- 构造固定一维连续布局的 Memory 视图，供 TSM/TLM 静态动态内存入口复用。

使用示例:
- auto mem = npu_demo::detail::make_linear_memory<float>(24576, npu_demo::MemorySpace::TSM);

创建者: 朽木露琪亚
最后修改人: 金铲铲大作战

关联文件:
- spec: [spec/include/npu_demo/npu_demo.md](spec/include/npu_demo/npu_demo.md)
- test: [test/include/npu_demo/test_kernel_context.py](test/include/npu_demo/test_kernel_context.py)
- 功能实现: [include/npu_demo/npu_demo.h](include/npu_demo/npu_demo.h)
*/
template <typename T>
inline Memory<T> make_linear_memory(long long size, MemorySpace space) {
    long long shape[1] = {size};
    long long stride[1] = {1};
    return Memory<T>(static_cast<T*>(nullptr), shape, stride, 1, MemoryFormat::Norm, space);
}

/*
功能说明:
- 当 SM/LM 动态内存大小为 0 时抛出带关键字的运行期错误。

使用示例:
- npu_demo::detail::throw_zero_sized_memory("sm_memory_size=0");

创建者: 朽木露琪亚
最后修改人: 金铲铲大作战

关联文件:
- spec: [spec/include/npu_demo/npu_demo.md](spec/include/npu_demo/npu_demo.md)
- test: [test/include/npu_demo/test_kernel_context.py](test/include/npu_demo/test_kernel_context.py)
- 功能实现: [include/npu_demo/npu_demo.h](include/npu_demo/npu_demo.h)
*/
inline void throw_zero_sized_memory(const char* message) {
    throw std::runtime_error(message);
}

}  // namespace detail

/*
功能说明:
- 表示 npu_demo 固定硬件模板的内核上下文，提供 block/thread/subthread id/count 与动态片上内存查询。

使用示例:
- npu_demo::KernelContext ctx;
- long long tid = ctx.thread_id();
- auto tlm = ctx.get_dynamic_memory<float>(npu_demo::MemorySpace::TLM);

创建者: 朽木露琪亚
最后修改人: 金铲铲大作战

关联文件:
- spec: [spec/include/npu_demo/npu_demo.md](spec/include/npu_demo/npu_demo.md)
- test: [test/include/npu_demo/test_kernel_context.py](test/include/npu_demo/test_kernel_context.py)
- 功能实现: [include/npu_demo/npu_demo.h](include/npu_demo/npu_demo.h)
*/
class KernelContext {
public:
    /*
    功能说明:
    - 返回固定硬件模板中的 block id。

    使用示例:
    - long long bid = ctx.block_id();

    创建者: 朽木露琪亚
    最后修改人: 金铲铲大作战

    关联文件:
    - spec: [spec/include/npu_demo/npu_demo.md](spec/include/npu_demo/npu_demo.md)
    - test: [test/include/npu_demo/test_kernel_context.py](test/include/npu_demo/test_kernel_context.py)
    - 功能实现: [include/npu_demo/npu_demo.h](include/npu_demo/npu_demo.h)
    */
    long long block_id() const {
        return detail::kBlockId;
    }

    /*
    功能说明:
    - 返回固定硬件模板中的 block 总数。

    使用示例:
    - long long bnum = ctx.block_num();

    创建者: 朽木露琪亚
    最后修改人: 金铲铲大作战

    关联文件:
    - spec: [spec/include/npu_demo/npu_demo.md](spec/include/npu_demo/npu_demo.md)
    - test: [test/include/npu_demo/test_kernel_context.py](test/include/npu_demo/test_kernel_context.py)
    - 功能实现: [include/npu_demo/npu_demo.h](include/npu_demo/npu_demo.h)
    */
    long long block_num() const {
        return detail::kBlockNum;
    }

    /*
    功能说明:
    - 返回固定硬件模板中的 thread id。

    使用示例:
    - long long tid = ctx.thread_id();

    创建者: 朽木露琪亚
    最后修改人: 金铲铲大作战

    关联文件:
    - spec: [spec/include/npu_demo/npu_demo.md](spec/include/npu_demo/npu_demo.md)
    - test: [test/include/npu_demo/test_kernel_context.py](test/include/npu_demo/test_kernel_context.py)
    - 功能实现: [include/npu_demo/npu_demo.h](include/npu_demo/npu_demo.h)
    */
    long long thread_id() const {
        return detail::kThreadId;
    }

    /*
    功能说明:
    - 返回固定硬件模板中的 thread 总数。

    使用示例:
    - long long tnum = ctx.thread_num();

    创建者: 朽木露琪亚
    最后修改人: 金铲铲大作战

    关联文件:
    - spec: [spec/include/npu_demo/npu_demo.md](spec/include/npu_demo/npu_demo.md)
    - test: [test/include/npu_demo/test_kernel_context.py](test/include/npu_demo/test_kernel_context.py)
    - 功能实现: [include/npu_demo/npu_demo.h](include/npu_demo/npu_demo.h)
    */
    long long thread_num() const {
        return detail::kThreadNum;
    }

    /*
    功能说明:
    - 返回固定硬件模板中的 subthread id。

    使用示例:
    - long long sid = ctx.subthread_id();

    创建者: 朽木露琪亚
    最后修改人: 金铲铲大作战

    关联文件:
    - spec: [spec/include/npu_demo/npu_demo.md](spec/include/npu_demo/npu_demo.md)
    - test: [test/include/npu_demo/test_kernel_context.py](test/include/npu_demo/test_kernel_context.py)
    - 功能实现: [include/npu_demo/npu_demo.h](include/npu_demo/npu_demo.h)
    */
    long long subthread_id() const {
        return detail::kSubthreadId;
    }

    /*
    功能说明:
    - 返回固定硬件模板中的 subthread 总数。

    使用示例:
    - long long snum = ctx.subthread_num();

    创建者: 朽木露琪亚
    最后修改人: 金铲铲大作战

    关联文件:
    - spec: [spec/include/npu_demo/npu_demo.md](spec/include/npu_demo/npu_demo.md)
    - test: [test/include/npu_demo/test_kernel_context.py](test/include/npu_demo/test_kernel_context.py)
    - 功能实现: [include/npu_demo/npu_demo.h](include/npu_demo/npu_demo.h)
    */
    long long subthread_num() const {
        return detail::kSubthreadNum;
    }

    /*
    功能说明:
    - 返回指定片上空间的动态内存视图；TSM/TLM 返回固定 shape/stride，SM/LM 在 size=0 时抛错。

    使用示例:
    - auto tsm = ctx.get_dynamic_memory<float>(npu_demo::MemorySpace::TSM);

    创建者: 朽木露琪亚
    最后修改人: 金铲铲大作战

    关联文件:
    - spec: [spec/include/npu_demo/npu_demo.md](spec/include/npu_demo/npu_demo.md)
    - test: [test/include/npu_demo/test_kernel_context.py](test/include/npu_demo/test_kernel_context.py)
    - 功能实现: [include/npu_demo/npu_demo.h](include/npu_demo/npu_demo.h)
    */
    template <typename T>
    Memory<T> get_dynamic_memory(MemorySpace space) const {
        switch (space) {
            case MemorySpace::TSM:
                return detail::make_linear_memory<T>(detail::kTsmMemorySize, MemorySpace::TSM);
            case MemorySpace::TLM:
                return detail::make_linear_memory<T>(detail::kTlmMemorySize, MemorySpace::TLM);
            case MemorySpace::SM:
                detail::throw_zero_sized_memory(
                    "npu_demo::KernelContext::get_dynamic_memory rejected MemorySpace::SM because sm_memory_size=0");
            case MemorySpace::LM:
                detail::throw_zero_sized_memory(
                    "npu_demo::KernelContext::get_dynamic_memory rejected MemorySpace::LM because lm_memory_size=0");
            default:
                throw std::invalid_argument(
                    "npu_demo::KernelContext::get_dynamic_memory requires on-chip MemorySpace");
        }
    }
};

}  // namespace npu_demo

#endif  // KERNELCODE_GENERATE_INCLUDE_NPU_DEMO_NPU_DEMO_H_
