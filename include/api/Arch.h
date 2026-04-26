/*
功能说明:
- 定义 include/api 层统一对外的 launch / barrier 公开接口声明。

使用示例:
- #include "include/api/Arch.h"
- BarrierVisibility vis = BarrierVisibility::TLM;
- BarrierScope scope = BarrierScope::GLOBAL;

创建者: 小李飞刀
最后修改人: 金铲铲大作战

关联文件:
- spec: spec/include/api/Arch.md
- test: test/include/api/test_arch.py
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

创建者: 金铲铲大作战
最后修改人: 金铲铲大作战

关联文件:
- spec: spec/include/api/Arch.md
- test: test/include/api/test_arch.py
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

创建者: 小李飞刀
最后修改人: 金铲铲大作战

关联文件:
- spec: spec/include/api/Arch.md
- test: test/include/api/test_arch.py
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
- 声明 include/api 层公开承诺的最小运行时上下文接口面。
- 该类只固定公开方法名与参数面，不承接 npu_demo 等后端的线程实现、barrier 共享状态或动态内存 backing store。

使用示例:
- void inspect(KernelContext& ctx) {
-     long long tid = ctx.thread_id();
-     long long tnum = ctx.thread_num();
-     ctx.barrier({BarrierVisibility::TSM, BarrierVisibility::TLM}, BarrierScope::BLOCK);
-     (void)tid;
-     (void)tnum;
- }

创建者: 金铲铲大作战
最后修改人: 金铲铲大作战

关联文件:
- spec: spec/include/api/Arch.md
- test: test/include/api/test_arch.py
- 功能实现: include/npu_demo/Arch.h
*/
class KernelContext {
public:
    /*
    功能说明:
    - 返回当前 launch 运行时视图中的线程索引。

    使用示例:
    - long long tid = ctx.thread_id();

    创建者: 金铲铲大作战
    最后修改人: 金铲铲大作战

    关联文件:
    - spec: spec/include/api/Arch.md
    - test: test/include/api/test_arch.py
    - 功能实现: include/npu_demo/Arch.h
    */
    virtual long long thread_id() const = 0;

    /*
    功能说明:
    - 返回当前 launch 运行时视图中的线程总数。

    使用示例:
    - long long tnum = ctx.thread_num();

    创建者: 金铲铲大作战
    最后修改人: 金铲铲大作战

    关联文件:
    - spec: spec/include/api/Arch.md
    - test: test/include/api/test_arch.py
    - 功能实现: include/npu_demo/Arch.h
    */
    virtual long long thread_num() const = 0;

    /*
    功能说明:
    - 声明公开 barrier 同步接口，固定 visibility 与 scope 两个参数面。

    使用示例:
    - ctx.barrier({BarrierVisibility::TSM, BarrierVisibility::TLM}, BarrierScope::BLOCK);

    创建者: 金铲铲大作战
    最后修改人: 金铲铲大作战

    关联文件:
    - spec: spec/include/api/Arch.md
    - test: test/include/api/test_arch.py
    - 功能实现: include/npu_demo/Arch.h
    */
    virtual void barrier(
        std::initializer_list<BarrierVisibility> visibility,
        BarrierScope scope) const = 0;

    /*
    功能说明:
    - 声明公开动态内存模板入口，具体返回语义由后端私有 include 提供。

    使用示例:
    - auto tsm = ctx.get_dynamic_memory<TSM, float>();

    创建者: 金铲铲大作战
    最后修改人: 金铲铲大作战

    关联文件:
    - spec: spec/include/api/Arch.md
    - test: test/include/api/test_arch.py
    - 功能实现: include/npu_demo/Arch.h
    */
    template <MemorySpace Space, typename T>
    Memory<Space, T> get_dynamic_memory() const;

protected:
    /*
    功能说明:
    - 保护构造函数，避免业务侧直接实例化只声明接口面的公开运行时上下文。

    使用示例:
    - class BackendContext : public KernelContext {};

    创建者: 金铲铲大作战
    最后修改人: 金铲铲大作战

    关联文件:
    - spec: spec/include/api/Arch.md
    - test: test/include/api/test_arch.py
    - 功能实现: include/npu_demo/Arch.h
    */
    KernelContext() = default;

    /*
    功能说明:
    - 保护析构函数，限制公开接口层只作为后端运行时上下文基类使用。

    使用示例:
    - class BackendContext : public KernelContext {};

    创建者: 金铲铲大作战
    最后修改人: 金铲铲大作战

    关联文件:
    - spec: spec/include/api/Arch.md
    - test: test/include/api/test_arch.py
    - 功能实现: include/npu_demo/Arch.h
    */
    ~KernelContext() = default;
};

/*
功能说明:
- 返回当前 launch 运行时视图中的线程索引，作为公开 free helper 供代码生成直接调用。

使用示例:
- S_INT tid = thread_id();

创建者: OpenAI Codex
最后修改人: OpenAI Codex

关联文件:
- spec: spec/include/api/Arch.md
- test: test/include/api/test_arch.py
- 功能实现: include/npu_demo/Arch.h
*/
S_INT thread_id();

/*
功能说明:
- 返回当前 launch 运行时视图中的线程总数，作为公开 free helper 供代码生成直接调用。

使用示例:
- S_INT tnum = thread_num();

创建者: OpenAI Codex
最后修改人: OpenAI Codex

关联文件:
- spec: spec/include/api/Arch.md
- test: test/include/api/test_arch.py
- 功能实现: include/npu_demo/Arch.h
*/
S_INT thread_num();

/*
功能说明:
- 返回指定片上空间的动态内存视图，作为公开 free helper 供代码生成直接调用。
- 返回值是可隐式转换到 `Memory<Space, T>` 的代理对象，元素类型由赋值目标决定。

使用示例:
- Memory<TSM, float> tsm = get_dynamic_memory<TSM>();

创建者: OpenAI Codex
最后修改人: OpenAI Codex

关联文件:
- spec: spec/include/api/Arch.md
- test: test/include/api/test_arch.py
- 功能实现: include/npu_demo/Arch.h
*/
template <MemorySpace Space>
DynamicMemoryRef<Space> get_dynamic_memory();

/*
功能说明:
- 表示 `get_dynamic_memory<Space>()` 返回的公开转换代理；通常不直接使用该类型，而是赋值到 `Memory<Space, T>`。

使用示例:
- Memory<TSM, float> tsm = get_dynamic_memory<TSM>();

创建者: OpenAI Codex
最后修改人: OpenAI Codex

关联文件:
- spec: spec/include/api/Arch.md
- test: test/include/api/test_arch.py
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

    创建者: OpenAI Codex
    最后修改人: OpenAI Codex

    关联文件:
    - spec: spec/include/api/Arch.md
    - test: test/include/api/test_arch.py
    - 功能实现: include/npu_demo/Arch.h
    */
    explicit DynamicMemoryRef(const void* context);

    /*
    功能说明:
    - 按赋值目标元素类型将代理转换为具体 `Memory<Space, T>` 视图。

    使用示例:
    - Memory<TSM, float> tsm = get_dynamic_memory<TSM>();

    创建者: OpenAI Codex
    最后修改人: OpenAI Codex

    关联文件:
    - spec: spec/include/api/Arch.md
    - test: test/include/api/test_arch.py
    - 功能实现: include/npu_demo/Arch.h
    */
    template <typename T>
    operator Memory<Space, T>() const;

private:
    const void* context_;
};

/*
功能说明:
- 声明公开 kernel launch 入口，具体后端实现由私有 include 提供。

使用示例:
- Status status = launch<1, 4, 1, 0>(kernel_body, input, output);

创建者: 小李飞刀
最后修改人: 小李飞刀

关联文件:
- spec: spec/include/api/Arch.md
- test: test/include/api/test_arch.py
- 功能实现: include/npu_demo/Arch.h
*/
template <long long block, long long thread, long long subthread, long long shared_memory_size, typename Callable, typename... Args>
Status launch(Callable&& callee, Args&&... args);

#endif  // KERNELCODE_GENERATE_INCLUDE_API_ARCH_H_
