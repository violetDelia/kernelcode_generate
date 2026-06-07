/*
功能说明:
- 定义 include/api 层统一对外的 launch / barrier 公开接口声明。

API 列表:
- `enum class BarrierVisibility { TSM, TLM }`
- `enum class BarrierScope { BLOCK, THREAD, SUBTHREAD, GLOBAL }`
- `template <long long block, long long thread, long long subthread, long long shared_memory_size, auto name, typename Context, typename... Args> Status launch(Context& ctx, Args&&... args)`
- `class KernelContext`
- `block_id() -> S_INT`
- `thread_id() -> S_INT`
- `thread_num() -> S_INT`
- `template <MemorySpace Space> get_dynamic_memory() -> DynamicMemoryRef<Space>`

helper 清单:
- 无；当前文件只声明公开运行时接口，不承接后端 helper。

使用示例:
- #include "include/api/Arch.h"
- BarrierVisibility vis = BarrierVisibility::TLM;
- BarrierScope scope = BarrierScope::GLOBAL;


关联文件:
- spec: spec/include/api/Arch.md
- test: test/include/api/arch.py
- 功能实现: include/npu_demo/Arch.h
*/

#ifndef KERNELCODE_GENERATE_INCLUDE_API_ARCH_H_
#define KERNELCODE_GENERATE_INCLUDE_API_ARCH_H_

#include <initializer_list>

#include "include/api/Core.h"
#include "include/api/Memory.h"

template <MemorySpace Space>
class DynamicMemoryRef;

/*
功能说明:
- 定义公开 barrier 可见域枚举，`TLM` 表示覆盖 `TLM1/TLM2/TLM3` 的聚合可见域。

使用示例:
- BarrierVisibility vis = BarrierVisibility::TLM;


关联文件:
- spec: spec/include/api/Arch.md
- test: test/include/api/arch.py
- 功能实现: include/npu_demo/Arch.h
*/
enum class BarrierVisibility {
    TSM,
    TLM,
};

/*
功能说明:
- 定义公开 barrier 同步范围枚举。

使用示例:
- BarrierScope scope = BarrierScope::BLOCK;


关联文件:
- spec: spec/include/api/Arch.md
- test: test/include/api/arch.py
- 功能实现: include/npu_demo/Arch.h
*/
enum class BarrierScope {
    BLOCK,
    THREAD,
    SUBTHREAD,
    GLOBAL,
};

/*
功能说明:
- 声明 include/api 层公开上下文类型；运行时查询、同步和动态内存访问由 Arch free helper 承接。
- 该类不公开 runtime member API，不承接 npu_demo 等后端的线程实现、barrier 共享状态或动态内存 backing store。

使用示例:
- void inspect(KernelContext& ctx) { (void)ctx; }


关联文件:
- spec: spec/include/api/Arch.md
- test: test/include/api/arch.py
- 功能实现: include/npu_demo/Arch.h
*/
class KernelContext {
public:
    /*
    功能说明:
    - 构造 opaque 公开上下文对象。

    使用示例:
    - KernelContext ctx;


    关联文件:
    - spec: spec/include/api/Arch.md
    - test: test/include/api/arch.py
    - 功能实现: include/npu_demo/Arch.h
    */
    KernelContext() = default;

    /*
    功能说明:
    - 析构 opaque 公开上下文对象。

    使用示例:
    - KernelContext ctx;


    关联文件:
    - spec: spec/include/api/Arch.md
    - test: test/include/api/arch.py
    - 功能实现: include/npu_demo/Arch.h
    */
    ~KernelContext() = default;
};

/*
功能说明:
- 返回当前 launch 运行时视图中的 block 索引，作为公开 free helper 供代码生成直接调用。

使用示例:
- S_INT bid = block_id();


关联文件:
- spec: spec/include/api/Arch.md
- test: test/include/api/arch.py
- 功能实现: include/npu_demo/Arch.h
*/
S_INT block_id();

/*
功能说明:
- 返回当前 launch 运行时视图中的线程索引，作为公开 free helper 供代码生成直接调用。

使用示例:
- S_INT tid = thread_id();


关联文件:
- spec: spec/include/api/Arch.md
- test: test/include/api/arch.py
- 功能实现: include/npu_demo/Arch.h
*/
S_INT thread_id();

/*
功能说明:
- 返回当前 launch 运行时视图中的线程总数，作为公开 free helper 供代码生成直接调用。

使用示例:
- S_INT tnum = thread_num();


关联文件:
- spec: spec/include/api/Arch.md
- test: test/include/api/arch.py
- 功能实现: include/npu_demo/Arch.h
*/
S_INT thread_num();

/*
功能说明:
- 返回指定片上空间的动态内存视图，作为公开 free helper 供代码生成直接调用。
- 返回值是可隐式转换到 `Memory<Space, T>` 的代理对象，元素类型由赋值目标决定。

使用示例:
- Memory<TSM, float> tsm = get_dynamic_memory<TSM>();


关联文件:
- spec: spec/include/api/Arch.md
- test: test/include/api/arch.py
- 功能实现: include/npu_demo/Arch.h
*/
template <MemorySpace Space>
DynamicMemoryRef<Space> get_dynamic_memory();

/*
功能说明:
- 表示 `get_dynamic_memory<Space>()` 返回的公开转换代理；通常不直接使用该类型，而是赋值到 `Memory<Space, T>`。

使用示例:
- Memory<TSM, float> tsm = get_dynamic_memory<TSM>();


关联文件:
- spec: spec/include/api/Arch.md
- test: test/include/api/arch.py
- 功能实现: include/npu_demo/Arch.h
*/
template <MemorySpace Space>
class DynamicMemoryRef {
public:
    /*
    功能说明:
    - 使用后端上下文句柄构造动态内存转换代理；业务侧通常不直接调用。

    使用示例:
    - Memory<TSM, float> tsm = get_dynamic_memory<TSM>();


    关联文件:
    - spec: spec/include/api/Arch.md
    - test: test/include/api/arch.py
    - 功能实现: include/npu_demo/Arch.h
    */
    explicit DynamicMemoryRef(const void* context);

    /*
    功能说明:
    - 按赋值目标元素类型将代理转换为具体 `Memory<Space, T>` 视图。

    使用示例:
    - Memory<TSM, float> tsm = get_dynamic_memory<TSM>();


    关联文件:
    - spec: spec/include/api/Arch.md
    - test: test/include/api/arch.py
    - 功能实现: include/npu_demo/Arch.h
    */
    template <typename T>
    operator Memory<Space, T>() const;

private:
    const void* context_;
};

/*
功能说明:
- 声明公开 kernel launch 入口，具体后端实现由私有 include 提供；callee/name 固定在模板参数。

使用示例:
- KernelContext ctx;
- Status status = launch<2, 1, 1, 0, kernel_body>(ctx, input, output);


关联文件:
- spec: spec/include/api/Arch.md
- test: test/include/api/arch.py
- 功能实现: include/npu_demo/Arch.h
*/
template <long long block, long long thread, long long subthread, long long shared_memory_size, auto name, typename Context, typename... Args>
Status launch(Context& ctx, Args&&... args);

#endif  // KERNELCODE_GENERATE_INCLUDE_API_ARCH_H_
