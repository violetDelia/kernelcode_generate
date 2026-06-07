/*
功能说明:
- 提供 npu_demo 后端的 launch / barrier 运行时实现与 KernelContext 运行时视图。
- `TRANCE` 开启时在 launch 边界打印函数名、模板参数、KernelContext 与 forwarded args 参数摘要。
- `KG_TRANCE_DIR_PATH` 非空时，launch 在每个 block worker 内写入独立的 `block_XXXX.log`。

API 列表:
- `template <long long block, long long thread, long long subthread, long long shared_memory_size, auto name, typename Context, typename... Args> Status npu_demo::launch(Context& ctx, Args&&... args)`
- `class npu_demo::KernelContext`
- `npu_demo::block_id() -> S_INT`
- `npu_demo::thread_id() -> S_INT`
- `npu_demo::thread_num() -> S_INT`
- `npu_demo::barrier(std::initializer_list<BarrierVisibility> visibility, BarrierScope scope) -> void`
- `template <MemorySpace Space> npu_demo::get_dynamic_memory() -> DynamicMemoryRef<Space>`
- `block_id() -> S_INT`
- `thread_id() -> S_INT`
- `thread_num() -> S_INT`
- `template <MemorySpace Space> get_dynamic_memory() -> DynamicMemoryRef<Space>`

helper 清单:
- `class ScopedActiveKernelContext`
- `class LaunchBarrierState`
- `npu_demo::detail::*`：launch 上下文绑定、barrier 状态与动态内存承接辅助逻辑。

使用示例:
- #include "include/npu_demo/Arch.h"
- npu_demo::KernelContext ctx;
- Status status = npu_demo::launch<2, 1, 1, 0, kernel_body>(ctx, output);


关联文件:
- spec: spec/include/npu_demo/npu_demo.md
- test: test/include/npu_demo/kernel_context.py
- 功能实现: include/npu_demo/Arch.h
*/

#ifndef KERNELCODE_GENERATE_INCLUDE_NPU_DEMO_ARCH_H_
#define KERNELCODE_GENERATE_INCLUDE_NPU_DEMO_ARCH_H_

#include <cstddef>
#include <condition_variable>
#include <initializer_list>
#include <memory>
#include <mutex>
#include <sstream>
#include <stdexcept>
#include <string>
#include <thread>
#include <tuple>
#include <type_traits>
#include <utility>
#include <vector>

#include "include/api/Arch.h"
#include "include/npu_demo/Core.h"
#include "include/npu_demo/Memory.h"
#include "include/npu_demo/Trance.h"

namespace npu_demo {

class KernelContext;

namespace detail {

static constexpr long long kBlockCapability = 2;
static constexpr long long kThreadCapability = 1;
static constexpr long long kSubthreadCapability = 1;
static constexpr long long kSmMemorySize = 0;
static constexpr long long kLmMemorySize = 0;
static constexpr long long kTsmMemorySize = 2097152;
static constexpr long long kTlm1MemorySize = 524288;
static constexpr long long kTlm2MemorySize = 1048576;
static constexpr long long kTlm3MemorySize = 1048576;

struct KernelRuntimeState;
struct KernelContextRuntimeAccess;

/*
功能说明:
- 为当前线程绑定一次 launch 生命周期内可见的活动 runtime state 指针。

使用示例:
- npu_demo::detail::ScopedActiveKernelContext scoped_ctx(&runtime);


关联文件:
- spec: spec/include/npu_demo/npu_demo.md
- test: test/include/npu_demo/kernel_context.py
- 功能实现: include/npu_demo/Arch.h
*/
inline thread_local const KernelRuntimeState* active_kernel_runtime = nullptr;

/*
功能说明:
- 在单次作用域内安装并恢复当前线程可见的活动 runtime state。

使用示例:
- npu_demo::detail::ScopedActiveKernelContext scoped_ctx(&runtime);


关联文件:
- spec: spec/include/npu_demo/npu_demo.md
- test: test/include/npu_demo/kernel_context.py
- 功能实现: include/npu_demo/Arch.h
*/
class ScopedActiveKernelContext {
public:
    /*
    功能说明:
    - 安装新的活动 runtime state，并保存进入作用域前的旧指针。

    使用示例:
    - npu_demo::detail::ScopedActiveKernelContext scoped_ctx(&runtime);


    关联文件:
    - spec: spec/include/npu_demo/npu_demo.md
    - test: test/include/npu_demo/kernel_context.py
    - 功能实现: include/npu_demo/Arch.h
    */
    explicit ScopedActiveKernelContext(const KernelRuntimeState* runtime)
        : previous_(active_kernel_runtime) {
        active_kernel_runtime = runtime;
    }

    /*
    功能说明:
    - 退出作用域时恢复进入前的活动 runtime state。

    使用示例:
    - { npu_demo::detail::ScopedActiveKernelContext scoped_ctx(&runtime); }


    关联文件:
    - spec: spec/include/npu_demo/npu_demo.md
    - test: test/include/npu_demo/kernel_context.py
    - 功能实现: include/npu_demo/Arch.h
    */
    ~ScopedActiveKernelContext() {
        active_kernel_runtime = previous_;
    }

    ScopedActiveKernelContext(const ScopedActiveKernelContext&) = delete;
    ScopedActiveKernelContext& operator=(const ScopedActiveKernelContext&) = delete;

private:
    const KernelRuntimeState* previous_;
};

/*
功能说明:
- 构造固定一维连续布局的 Memory 视图，并为运行期动态片上内存提供当前线程可写 backing storage。

使用示例:
- auto tsm = npu_demo::detail::make_linear_memory<TSM, float>(2097152);


关联文件:
- spec: spec/include/npu_demo/npu_demo.md
- test: test/include/npu_demo/kernel_context.py
- 功能实现: include/npu_demo/Arch.h
*/
template <MemorySpace Space, typename T>
inline Memory<Space, T> make_linear_memory(long long size) {
    long long shape[1] = {size};
    long long stride[1] = {1};
    thread_local std::vector<T> storage;
    if (size > 0 && storage.size() < static_cast<unsigned long long>(size)) {
        storage.resize(static_cast<unsigned long long>(size));
    }
    T* data = size > 0 ? storage.data() : static_cast<T*>(nullptr);
    return Memory<Space, T>(data, shape, stride, 1, MemoryFormat::Norm);
}

/*
功能说明:
- 在零容量片上空间访问时抛出带关键字的运行时错误。

使用示例:
- npu_demo::detail::throw_zero_sized_memory("sm_memory_size=0");


关联文件:
- spec: spec/include/npu_demo/npu_demo.md
- test: test/include/npu_demo/kernel_context.py
- 功能实现: include/npu_demo/Arch.h
*/
inline void throw_zero_sized_memory(const char* message) {
    throw std::runtime_error(message);
}

/*
功能说明:
- 为单次 launch 提供 block-scope barrier 的共享状态。

使用示例:
- auto barrier = std::make_shared<npu_demo::detail::LaunchBarrierState>(4);


关联文件:
- spec: spec/include/npu_demo/npu_demo.md
- test: test/include/npu_demo/kernel_context.py
- 功能实现: include/npu_demo/Arch.h
*/
class LaunchBarrierState {
public:
    /*
    功能说明:
    - 使用参与线程数构造一次可复用的 launch barrier 状态。

    使用示例:
    - npu_demo::detail::LaunchBarrierState barrier(4);


    关联文件:
    - spec: spec/include/npu_demo/npu_demo.md
    - test: test/include/npu_demo/kernel_context.py
    - 功能实现: include/npu_demo/Arch.h
    */
    explicit LaunchBarrierState(long long participants)
        : participants_(participants), arrived_(0), generation_(0) {}

    /*
    功能说明:
    - 让当前线程等待到本次 launch 的全部参与线程到达。

    使用示例:
    - barrier.arrive_and_wait();


    关联文件:
    - spec: spec/include/npu_demo/npu_demo.md
    - test: test/include/npu_demo/kernel_context.py
    - 功能实现: include/npu_demo/Arch.h
    */
    inline void arrive_and_wait() {
        std::unique_lock<std::mutex> lock(mutex_);
        const long long current_generation = generation_;
        ++arrived_;
        if (arrived_ == participants_) {
            arrived_ = 0;
            ++generation_;
            lock.unlock();
            cv_.notify_all();
            return;
        }
        while (generation_ == current_generation) {
            cv_.wait(lock);
        }
    }

private:
    long long participants_;
    long long arrived_;
    long long generation_;
    std::mutex mutex_;
    std::condition_variable cv_;
};

}  // namespace detail

/*
功能说明:
- 表示 launched body 内显式传递的 npu_demo 上下文对象。
- 运行时查询、同步与动态内存访问不作为 KernelContext public member API 暴露，统一由 Arch free helper 承接。

使用示例:
- npu_demo::KernelContext ctx;
- (void)ctx;


关联文件:
- spec: spec/include/npu_demo/npu_demo.md
- test: test/include/npu_demo/kernel_context.py
- 功能实现: include/npu_demo/Arch.h
*/
class KernelContext {
public:
    /*
    功能说明:
    - 构造默认 opaque context；launch 会为 worker 副本注入私有运行时状态。

    使用示例:
    - npu_demo::KernelContext ctx;


    关联文件:
    - spec: spec/include/npu_demo/npu_demo.md
    - test: test/include/npu_demo/kernel_context.py
    - 功能实现: include/npu_demo/Arch.h
    */
    KernelContext() = default;
};

namespace detail {

/*
功能说明:
- 保存单个 launch worker 当前可见的运行时状态；该状态不存放在 `KernelContext` 对象内。

使用示例:
- npu_demo::detail::KernelRuntimeState runtime;


关联文件:
- spec: spec/include/npu_demo/npu_demo.md
- test: test/include/npu_demo/kernel_context.py
- 功能实现: include/npu_demo/Arch.h
*/
struct KernelRuntimeState {
    long long block_id = 0;
    long long block_num = 1;
    long long thread_id = 0;
    long long thread_num = 1;
    long long subthread_id = 0;
    long long subthread_num = 1;
    std::shared_ptr<LaunchBarrierState> barrier_state = nullptr;
};

inline const KernelRuntimeState& default_kernel_runtime() {
    static const KernelRuntimeState runtime;
    return runtime;
}

inline const KernelRuntimeState& current_kernel_runtime() {
    return active_kernel_runtime != nullptr ? *active_kernel_runtime : default_kernel_runtime();
}

/*
功能说明:
- 在 npu_demo 后端内部读写 launch runtime 状态，避免把 runtime 查询暴露成 `KernelContext` public member API。

使用示例:
- npu_demo::detail::KernelContextRuntimeAccess::configure(runtime, 0, 2, 0, 1, 0, 1, barrier);


关联文件:
- spec: spec/include/npu_demo/npu_demo.md
- test: test/include/npu_demo/kernel_context.py
- 功能实现: include/npu_demo/Arch.h
*/
struct KernelContextRuntimeAccess {
    static void configure(
        KernelRuntimeState& runtime,
        long long block_id,
        long long block_num,
        long long thread_id,
        long long thread_num,
        long long subthread_id,
        long long subthread_num,
        std::shared_ptr<LaunchBarrierState> barrier_state) {
        runtime.block_id = block_id;
        runtime.block_num = block_num;
        runtime.thread_id = thread_id;
        runtime.thread_num = thread_num;
        runtime.subthread_id = subthread_id;
        runtime.subthread_num = subthread_num;
        runtime.barrier_state = std::move(barrier_state);
    }

    static long long block_id(const KernelRuntimeState& runtime) {
        return runtime.block_id;
    }

    static long long thread_id(const KernelRuntimeState& runtime) {
        return runtime.thread_id;
    }

    static long long thread_num(const KernelRuntimeState& runtime) {
        return runtime.thread_num;
    }

    static void barrier(
        const KernelRuntimeState& runtime,
        std::initializer_list<BarrierVisibility> visibility,
        BarrierScope scope) {
        if (scope != BarrierScope::BLOCK) {
            throw std::invalid_argument(
                "npu_demo::barrier requires scope=BarrierScope::BLOCK");
        }
        if (visibility.size() != 2) {
            throw std::invalid_argument(
                "npu_demo::barrier visibility must contain BarrierVisibility::TSM "
                "and BarrierVisibility::TLM exactly once");
        }
        bool saw_tsm = false;
        bool saw_tlm = false;
        for (BarrierVisibility space : visibility) {
            switch (space) {
                case BarrierVisibility::TSM:
                    if (saw_tsm) {
                        throw std::invalid_argument(
                            "npu_demo::barrier visibility must contain BarrierVisibility::TSM "
                            "and BarrierVisibility::TLM exactly once");
                    }
                    saw_tsm = true;
                    break;
                case BarrierVisibility::TLM:
                    if (saw_tlm) {
                        throw std::invalid_argument(
                            "npu_demo::barrier visibility must contain BarrierVisibility::TSM "
                            "and BarrierVisibility::TLM exactly once");
                    }
                    saw_tlm = true;
                    break;
                default:
                    throw std::invalid_argument(
                        "npu_demo::barrier visibility only supports "
                        "BarrierVisibility::TSM and BarrierVisibility::TLM");
            }
        }
        if (!saw_tsm || !saw_tlm) {
            throw std::invalid_argument(
                "npu_demo::barrier visibility must contain BarrierVisibility::TSM "
                "and BarrierVisibility::TLM exactly once");
        }
        if (runtime.barrier_state == nullptr) {
            throw std::runtime_error(
                "npu_demo::barrier requires active launch context");
        }
        runtime.barrier_state->arrive_and_wait();
    }

    template <MemorySpace Space, typename T>
    static Memory<Space, T> dynamic_memory(const KernelRuntimeState&) {
        if constexpr (Space == MemorySpace::TSM) {
            return make_linear_memory<MemorySpace::TSM, T>(kTsmMemorySize);
        } else if constexpr (Space == MemorySpace::TLM1) {
            return make_linear_memory<MemorySpace::TLM1, T>(kTlm1MemorySize);
        } else if constexpr (Space == MemorySpace::TLM2) {
            return make_linear_memory<MemorySpace::TLM2, T>(kTlm2MemorySize);
        } else if constexpr (Space == MemorySpace::TLM3) {
            return make_linear_memory<MemorySpace::TLM3, T>(kTlm3MemorySize);
        } else if constexpr (Space == MemorySpace::SM) {
            throw_zero_sized_memory(
                "npu_demo::get_dynamic_memory rejected MemorySpace::SM because "
                "sm_memory_size=0");
            return make_linear_memory<MemorySpace::SM, T>(0);
        } else if constexpr (Space == MemorySpace::LM) {
            throw_zero_sized_memory(
                "npu_demo::get_dynamic_memory rejected MemorySpace::LM because "
                "lm_memory_size=0");
            return make_linear_memory<MemorySpace::LM, T>(0);
        } else {
            throw std::invalid_argument(
                "npu_demo::get_dynamic_memory requires on-chip MemorySpace");
        }
    }
};

/*
功能说明:
- 调用 launch 模板参数中的 kernel body，并把 `Context& ctx` 作为首个普通实参传入。

使用示例:
- npu_demo::detail::invoke_launch_name<kernel_body>(ctx, args_tuple);

关联文件:
- spec: spec/include/npu_demo/npu_demo.md
- test: test/include/npu_demo/kernel_context.py
- 功能实现: include/npu_demo/Arch.h
*/
template <auto name, typename Context, typename Tuple, std::size_t... Indices>
inline void invoke_launch_name_with_indices(Context& ctx, Tuple& args, std::index_sequence<Indices...>) {
    Context& active_ctx = ctx;
    Tuple& forwarded_args = args;
    (void)forwarded_args;
    name(active_ctx, std::get<Indices>(forwarded_args)...);
}

/*
功能说明:
- 按 tuple 元素个数展开 launch 普通参数，供 worker 线程调用 body。

使用示例:
- npu_demo::detail::invoke_launch_name<kernel_body>(ctx, forwarded_args);

关联文件:
- spec: spec/include/npu_demo/npu_demo.md
- test: test/include/npu_demo/kernel_context.py
- 功能实现: include/npu_demo/Arch.h
*/
template <auto name, typename Context, typename Tuple>
inline void invoke_launch_name(Context& ctx, Tuple& args) {
    constexpr std::size_t arg_count = std::tuple_size<typename std::remove_reference<Tuple>::type>::value;
    using Indices = std::make_index_sequence<arg_count>;
    Context& active_ctx = ctx;
    Tuple& forwarded_args = args;
    invoke_launch_name_with_indices<name>(active_ctx, forwarded_args, Indices{});
}

/*
功能说明:
- 按顺序打印 launch tuple 中的普通参数，供 TRANCE block 级日志复用。

使用示例:
- npu_demo::detail::print_launch_tuple_args<0>(sink, args, index);

关联文件:
- spec: spec/include/npu_demo/npu_demo.md
- test: test/include/npu_demo/kernel_context.py
- 功能实现: include/npu_demo/Arch.h
*/
template <std::size_t Index, typename Tuple>
inline void print_launch_tuple_args(const kernelcode::trance::TranceSink& sink, Tuple& args, long long& arg_index) {
    constexpr std::size_t arg_count = std::tuple_size<typename std::remove_reference<Tuple>::type>::value;
    if constexpr (Index < arg_count) {
        kernelcode::trance::print_value_arg(
            sink,
            (std::string("arg") + std::to_string(arg_index++)).c_str(),
            std::get<Index>(args));
        print_launch_tuple_args<Index + 1>(sink, args, arg_index);
    }
}

/*
功能说明:
- 执行一个 npu_demo launch worker，负责注入 worker context、绑定 active context、写 TRANCE block 日志并调用 body。

使用示例:
- npu_demo::detail::run_launch_worker<2, 1, 1, 0, kernel_body>(ctx, &args, 0, 0, barrier, false);

关联文件:
- spec: spec/include/npu_demo/npu_demo.md
- test: test/include/npu_demo/kernel_context.py
- 功能实现: include/npu_demo/Arch.h
*/
template <
    long long block,
    long long thread,
    long long subthread,
    long long shared_memory_size,
    auto name,
    typename Context,
    typename Tuple>
inline void run_launch_worker(
    Context ctx,
    Tuple* forwarded_args,
    long long block_index,
    long long thread_index,
    std::shared_ptr<LaunchBarrierState> barrier_state,
    bool trace_block_enabled) {
    Context worker_ctx = ctx;
    KernelRuntimeState worker_runtime;
    const KernelRuntimeState* active_runtime = nullptr;
    if constexpr (std::is_same<typename std::decay<Context>::type, KernelContext>::value) {
        KernelContextRuntimeAccess::configure(
            worker_runtime,
            block_index,
            block,
            thread_index,
            thread,
            0,
            subthread,
            std::move(barrier_state));
        active_runtime = &worker_runtime;
    }
    ScopedActiveKernelContext scoped_active_ctx(active_runtime);
    Tuple& args = *forwarded_args;
#ifdef TRANCE
    if (trace_block_enabled) {
        kernelcode::trance::ScopedBlockTranceSink __kg_block_trance_scope(
            KG_TRANCE_DIR_PATH,
            block_index,
            block,
            thread_index,
            thread);
        const kernelcode::trance::TranceSink& __kg_block_trance_sink =
            kernelcode::trance::current_sink();
        std::ostringstream __kg_block_trance_template;
        __kg_block_trance_template
            << "template=<block=" << block
            << ", thread=" << thread
            << ", subthread=" << subthread
            << ", shared_memory_size=" << shared_memory_size
            << ">";
        kernelcode::trance::print_func_begin(
            __kg_block_trance_sink,
            "npu_demo::launch",
            __kg_block_trance_template.str().c_str());
        kernelcode::trance::write_line(__kg_block_trance_sink, "args =");
        kernelcode::trance::write_line(__kg_block_trance_sink, "  arg0 = KernelContext");
        long long __kg_block_trance_arg_index = 1;
        print_launch_tuple_args<0>(__kg_block_trance_sink, args, __kg_block_trance_arg_index);
        invoke_launch_name<name>(worker_ctx, args);
        return;
    }
#else
    (void)trace_block_enabled;
#endif
    invoke_launch_name<name>(worker_ctx, args);
}

}  // namespace detail

/*
功能说明:
- 返回当前 launch 运行时视图中的 block 索引，供生成代码以 free helper 形式直接调用。

使用示例:
- S_INT bid = npu_demo::block_id();


关联文件:
- spec: spec/include/npu_demo/npu_demo.md
- test: test/include/npu_demo/kernel_context.py
- 功能实现: include/npu_demo/Arch.h
*/
inline S_INT block_id() {
    return static_cast<S_INT>(detail::KernelContextRuntimeAccess::block_id(detail::current_kernel_runtime()));
}

/*
功能说明:
- 返回当前 launch 运行时视图中的线程索引，供生成代码以 free helper 形式直接调用。

使用示例:
- S_INT tid = npu_demo::thread_id();


关联文件:
- spec: spec/include/npu_demo/npu_demo.md
- test: test/include/npu_demo/kernel_context.py
- 功能实现: include/npu_demo/Arch.h
*/
inline S_INT thread_id() {
    return static_cast<S_INT>(detail::KernelContextRuntimeAccess::thread_id(detail::current_kernel_runtime()));
}

/*
功能说明:
- 返回当前 launch 运行时视图中的线程总数，供生成代码以 free helper 形式直接调用。

使用示例:
- S_INT tnum = npu_demo::thread_num();


关联文件:
- spec: spec/include/npu_demo/npu_demo.md
- test: test/include/npu_demo/kernel_context.py
- 功能实现: include/npu_demo/Arch.h
*/
inline S_INT thread_num() {
    return static_cast<S_INT>(detail::KernelContextRuntimeAccess::thread_num(detail::current_kernel_runtime()));
}

/*
功能说明:
- 返回指定片上空间的动态内存视图，供生成代码以 free helper 形式直接调用。
- 返回值是可隐式转换到 `Memory<Space, T>` 的代理对象，元素类型由赋值目标决定。

使用示例:
- Memory<TSM, float> tsm = npu_demo::get_dynamic_memory<TSM>();


关联文件:
- spec: spec/include/npu_demo/npu_demo.md
- test: test/include/npu_demo/kernel_context.py
- 功能实现: include/npu_demo/Arch.h
*/
template <MemorySpace Space>
inline ::DynamicMemoryRef<Space> get_dynamic_memory() {
    return ::DynamicMemoryRef<Space>(&detail::current_kernel_runtime());
}

/*
功能说明:
- 通过当前 launch 活动上下文执行 barrier，供生成代码以 free helper 形式直接调用。

使用示例:
- npu_demo::barrier({BarrierVisibility::TSM, BarrierVisibility::TLM}, BarrierScope::BLOCK);


关联文件:
- spec: spec/include/npu_demo/npu_demo.md
- test: test/include/npu_demo/kernel_context.py
- 功能实现: include/npu_demo/Arch.h
*/
inline void barrier(std::initializer_list<BarrierVisibility> visibility, BarrierScope scope) {
    detail::KernelContextRuntimeAccess::barrier(detail::current_kernel_runtime(), visibility, scope);
}

}  // namespace npu_demo

/*
功能说明:
- 使用后端活动上下文句柄构造 `get_dynamic_memory<Space>()` 返回的公开代理对象。

使用示例:
- Memory<TSM, float> tsm = get_dynamic_memory<TSM>();


关联文件:
- spec: spec/include/api/Arch.md
- test: test/include/api/arch.py
- 功能实现: include/npu_demo/Arch.h
*/
template <MemorySpace Space>
inline DynamicMemoryRef<Space>::DynamicMemoryRef(const void* context)
    : context_(context) {}

/*
功能说明:
- 按赋值目标元素类型把动态内存代理转换成具体 `Memory<Space, T>` 视图。

使用示例:
- Memory<TSM, float> tsm = get_dynamic_memory<TSM>();


关联文件:
- spec: spec/include/api/Arch.md
- test: test/include/api/arch.py
- 功能实现: include/npu_demo/Arch.h
*/
template <MemorySpace Space>
template <typename T>
inline DynamicMemoryRef<Space>::operator Memory<Space, T>() const {
    const auto* runtime = static_cast<const npu_demo::detail::KernelRuntimeState*>(context_);
    return npu_demo::detail::KernelContextRuntimeAccess::dynamic_memory<Space, T>(*runtime);
}

/*
功能说明:
- 返回当前 launch 运行时视图中的 block 索引，作为公开全局 free helper 供生成代码直接调用。

使用示例:
- S_INT bid = block_id();


关联文件:
- spec: spec/include/api/Arch.md
- test: test/include/api/arch.py
- 功能实现: include/npu_demo/Arch.h
*/
inline S_INT block_id() {
    return npu_demo::block_id();
}

/*
功能说明:
- 返回当前 launch 运行时视图中的线程索引，作为公开全局 free helper 供生成代码直接调用。

使用示例:
- S_INT tid = thread_id();


关联文件:
- spec: spec/include/api/Arch.md
- test: test/include/api/arch.py
- 功能实现: include/npu_demo/Arch.h
*/
inline S_INT thread_id() {
    return npu_demo::thread_id();
}

/*
功能说明:
- 返回当前 launch 运行时视图中的线程总数，作为公开全局 free helper 供生成代码直接调用。

使用示例:
- S_INT tnum = thread_num();


关联文件:
- spec: spec/include/api/Arch.md
- test: test/include/api/arch.py
- 功能实现: include/npu_demo/Arch.h
*/
inline S_INT thread_num() {
    return npu_demo::thread_num();
}

/*
功能说明:
- 返回指定片上空间的动态内存视图，作为公开全局 free helper 供生成代码直接调用。
- 返回值是可隐式转换到 `Memory<Space, T>` 的代理对象，元素类型由赋值目标决定。

使用示例:
- Memory<TSM, float> tsm = get_dynamic_memory<TSM>();


关联文件:
- spec: spec/include/api/Arch.md
- test: test/include/api/arch.py
- 功能实现: include/npu_demo/Arch.h
*/
template <MemorySpace Space>
inline DynamicMemoryRef<Space> get_dynamic_memory() {
    return npu_demo::get_dynamic_memory<Space>();
}

/*
功能说明:
- 启动一次 npu_demo P0 kernel 执行，并绑定当前线程可见的运行时 KernelContext。
- callee/name 固定为模板参数，函数普通实参固定为 `ctx, args...`，不提供 no-ctx fallback。

使用示例:
- npu_demo::KernelContext ctx;
- Status status = launch<2, 1, 1, 0, kernel_body>(ctx, output);


关联文件:
- spec: spec/include/api/Arch.md
- test: test/include/api/arch.py
- 功能实现: include/npu_demo/Arch.h
*/
template <long long block, long long thread, long long subthread, long long shared_memory_size, auto name, typename Context, typename... Args>
inline Status launch(Context& ctx, Args&&... args) {
    static_assert(
        !std::is_convertible<decltype(name), const char*>::value,
        "launch name must be function object, not string");
    static_assert(
        std::is_invocable<decltype(name), Context&, Args...>::value,
        "launch name must accept Context& plus args");

    if constexpr (block <= 0 || thread <= 0 || subthread <= 0 || shared_memory_size != 0) {
        return StatusCode::kError;
    }
    if constexpr (
        block > npu_demo::detail::kBlockCapability
        || subthread != npu_demo::detail::kSubthreadCapability
        || thread > npu_demo::detail::kThreadCapability) {
        return StatusCode::kError;
    }

#ifdef TRANCE
    const bool __kg_trance_block_trace_enabled = KG_TRANCE_DIR_PATH[0] != '\0';
    if (__kg_trance_block_trace_enabled) {
        kernelcode::trance::prepare_block_trace_dir(KG_TRANCE_DIR_PATH);
    }
    const kernelcode::trance::TranceSink& __kg_trance_sink = kernelcode::trance::current_sink();
    std::ostringstream __kg_trance_template;
    __kg_trance_template
        << "template=<block=" << block
        << ", thread=" << thread
        << ", subthread=" << subthread
        << ", shared_memory_size=" << shared_memory_size
        << ">";
    if (!__kg_trance_block_trace_enabled) {
        kernelcode::trance::print_func_begin(
            __kg_trance_sink,
            "npu_demo::launch",
            __kg_trance_template.str().c_str());
        kernelcode::trance::write_line(__kg_trance_sink, "args =");
        kernelcode::trance::write_line(__kg_trance_sink, "  arg0 = KernelContext");
        long long __kg_trance_arg_index = 1;
        ((kernelcode::trance::print_value_arg(
             __kg_trance_sink,
             (std::string("arg") + std::to_string(__kg_trance_arg_index++)).c_str(),
             args)), ...);
    }
#else
    const bool __kg_trance_block_trace_enabled = false;
#endif

    std::vector<std::shared_ptr<npu_demo::detail::LaunchBarrierState>> barrier_states;
    barrier_states.reserve(static_cast<unsigned long long>(block));
    for (long long block_index = 0; block_index < block; ++block_index) {
        barrier_states.emplace_back(std::make_shared<npu_demo::detail::LaunchBarrierState>(thread));
    }
    std::tuple<Args...> forwarded_args(std::forward<Args>(args)...);
    std::vector<std::thread> workers;
    workers.reserve(static_cast<unsigned long long>(block * thread));

    for (long long block_index = 0; block_index < block; ++block_index) {
        for (long long thread_index = 0; thread_index < thread; ++thread_index) {
            workers.emplace_back(
                &npu_demo::detail::run_launch_worker<
                    block,
                    thread,
                    subthread,
                    shared_memory_size,
                    name,
                    Context,
                    decltype(forwarded_args)>,
                ctx,
                &forwarded_args,
                block_index,
                thread_index,
                barrier_states[static_cast<unsigned long long>(block_index)],
                __kg_trance_block_trace_enabled);
        }
    }

    for (std::thread& worker : workers) {
        worker.join();
    }
    return StatusCode::kOk;
}

namespace npu_demo {

using ::launch;

}  // namespace npu_demo

#endif  // KERNELCODE_GENERATE_INCLUDE_NPU_DEMO_ARCH_H_
