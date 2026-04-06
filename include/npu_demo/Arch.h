/*
功能说明:
- 提供 npu_demo 后端的 launch / barrier 运行时实现与 KernelContext 运行时视图。

使用示例:
- #include "include/npu_demo/Arch.h"
- Status status = npu_demo::launch<1, 4, 1>(kernel_body, output);

创建者: 小李飞刀
最后修改人: jcc你莫辜负

关联文件:
- spec: spec/include/npu_demo/npu_demo.md
- test: test/include/npu_demo/test_kernel_context.py
- 功能实现: include/npu_demo/Arch.h
*/

#ifndef KERNELCODE_GENERATE_INCLUDE_NPU_DEMO_ARCH_H_
#define KERNELCODE_GENERATE_INCLUDE_NPU_DEMO_ARCH_H_

#include <condition_variable>
#include <initializer_list>
#include <memory>
#include <mutex>
#include <stdexcept>
#include <thread>
#include <tuple>
#include <type_traits>
#include <utility>
#include <vector>

#include "include/api/Arch.h"
#include "include/npu_demo/Core.h"
#include "include/npu_demo/Memory.h"

namespace npu_demo {

namespace detail {

static constexpr long long kBlockCapability = 1;
static constexpr long long kThreadCapability = 8;
static constexpr long long kSubthreadCapability = 1;
static constexpr long long kSmMemorySize = 0;
static constexpr long long kLmMemorySize = 0;
static constexpr long long kTsmMemorySize = 24576;
static constexpr long long kTlmMemorySize = 2048;

/*
功能说明:
- 构造固定一维连续布局的 Memory 视图，供动态片上内存入口复用。

使用示例:
- auto tsm = npu_demo::detail::make_linear_memory<TSM, float>(24576);

创建者: 小李飞刀
最后修改人: jcc你莫辜负

关联文件:
- spec: spec/include/npu_demo/npu_demo.md
- test: test/include/npu_demo/test_kernel_context.py
- 功能实现: include/npu_demo/Arch.h
*/
template <MemorySpace Space, typename T>
inline Memory<Space, T> make_linear_memory(long long size) {
    long long shape[1] = {size};
    long long stride[1] = {1};
    return Memory<Space, T>(static_cast<T*>(nullptr), shape, stride, 1, MemoryFormat::Norm);
}

/*
功能说明:
- 在零容量片上空间访问时抛出带关键字的运行时错误。

使用示例:
- npu_demo::detail::throw_zero_sized_memory("sm_memory_size=0");

创建者: 小李飞刀
最后修改人: 小李飞刀

关联文件:
- spec: spec/include/npu_demo/npu_demo.md
- test: test/include/npu_demo/test_kernel_context.py
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

创建者: 小李飞刀
最后修改人: 小李飞刀

关联文件:
- spec: spec/include/npu_demo/npu_demo.md
- test: test/include/npu_demo/test_kernel_context.py
- 功能实现: include/npu_demo/Arch.h
*/
class LaunchBarrierState {
public:
    /*
    功能说明:
    - 使用参与线程数构造一次可复用的 launch barrier 状态。

    使用示例:
    - npu_demo::detail::LaunchBarrierState barrier(4);

    创建者: 小李飞刀
    最后修改人: 小李飞刀

    关联文件:
    - spec: spec/include/npu_demo/npu_demo.md
    - test: test/include/npu_demo/test_kernel_context.py
    - 功能实现: include/npu_demo/Arch.h
    */
    explicit LaunchBarrierState(long long participants)
        : participants_(participants), arrived_(0), generation_(0) {}

    /*
    功能说明:
    - 让当前线程等待到本次 launch 的全部参与线程到达。

    使用示例:
    - barrier.arrive_and_wait();

    创建者: 小李飞刀
    最后修改人: 小李飞刀

    关联文件:
    - spec: spec/include/npu_demo/npu_demo.md
    - test: test/include/npu_demo/test_kernel_context.py
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
        cv_.wait(lock, [this, current_generation]() { return generation_ != current_generation; });
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
- 表示 launched body 内可见的运行时上下文视图，提供 extent/id、barrier 与动态内存入口。

使用示例:
- long long tid = ctx.thread_id();
- ctx.barrier({MemorySpace::TSM, MemorySpace::TLM}, BarrierScope::BLOCK);

创建者: 小李飞刀
最后修改人: 小李飞刀

关联文件:
- spec: spec/include/npu_demo/npu_demo.md
- test: test/include/npu_demo/test_kernel_context.py
- 功能实现: include/npu_demo/Arch.h
*/
class KernelContext {
public:
    /*
    功能说明:
    - 构造默认 runtime 视图，用于无 launch 上下文的轻量访问场景。

    使用示例:
    - npu_demo::KernelContext ctx;

    创建者: 小李飞刀
    最后修改人: 小李飞刀

    关联文件:
    - spec: spec/include/npu_demo/npu_demo.md
    - test: test/include/npu_demo/test_kernel_context.py
    - 功能实现: include/npu_demo/Arch.h
    */
    KernelContext()
        : block_id_(0),
          block_num_(1),
          thread_id_(0),
          thread_num_(1),
          subthread_id_(0),
          subthread_num_(1),
          barrier_state_(nullptr) {}

    /*
    功能说明:
    - 使用 launch 注入的运行时值构造 KernelContext。

    使用示例:
    - npu_demo::KernelContext ctx(0, 1, 2, 4, 0, 1, barrier);

    创建者: 小李飞刀
    最后修改人: 小李飞刀

    关联文件:
    - spec: spec/include/npu_demo/npu_demo.md
    - test: test/include/npu_demo/test_kernel_context.py
    - 功能实现: include/npu_demo/Arch.h
    */
    KernelContext(
        long long block_id,
        long long block_num,
        long long thread_id,
        long long thread_num,
        long long subthread_id,
        long long subthread_num,
        std::shared_ptr<detail::LaunchBarrierState> barrier_state)
        : block_id_(block_id),
          block_num_(block_num),
          thread_id_(thread_id),
          thread_num_(thread_num),
          subthread_id_(subthread_id),
          subthread_num_(subthread_num),
          barrier_state_(std::move(barrier_state)) {}

    /*
    功能说明:
    - 返回当前 launch 的 block 索引。

    使用示例:
    - long long bid = ctx.block_id();

    创建者: 小李飞刀
    最后修改人: 小李飞刀

    关联文件:
    - spec: spec/include/npu_demo/npu_demo.md
    - test: test/include/npu_demo/test_kernel_context.py
    - 功能实现: include/npu_demo/Arch.h
    */
    long long block_id() const {
        return block_id_;
    }

    /*
    功能说明:
    - 返回当前 launch 的 block extent。

    使用示例:
    - long long bnum = ctx.block_num();

    创建者: 小李飞刀
    最后修改人: 小李飞刀

    关联文件:
    - spec: spec/include/npu_demo/npu_demo.md
    - test: test/include/npu_demo/test_kernel_context.py
    - 功能实现: include/npu_demo/Arch.h
    */
    long long block_num() const {
        return block_num_;
    }

    /*
    功能说明:
- 返回当前 launch 的 thread 索引。

    使用示例:
    - long long tid = ctx.thread_id();

    创建者: 小李飞刀
    最后修改人: 小李飞刀

    关联文件:
    - spec: spec/include/npu_demo/npu_demo.md
    - test: test/include/npu_demo/test_kernel_context.py
    - 功能实现: include/npu_demo/Arch.h
    */
    long long thread_id() const {
        return thread_id_;
    }

    /*
    功能说明:
    - 返回当前 launch 的 thread extent。

    使用示例:
    - long long tnum = ctx.thread_num();

    创建者: 小李飞刀
    最后修改人: 小李飞刀

    关联文件:
    - spec: spec/include/npu_demo/npu_demo.md
    - test: test/include/npu_demo/test_kernel_context.py
    - 功能实现: include/npu_demo/Arch.h
    */
    long long thread_num() const {
        return thread_num_;
    }

    /*
    功能说明:
    - 返回当前 launch 的 subthread 索引。

    使用示例:
    - long long sid = ctx.subthread_id();

    创建者: 小李飞刀
    最后修改人: 小李飞刀

    关联文件:
    - spec: spec/include/npu_demo/npu_demo.md
    - test: test/include/npu_demo/test_kernel_context.py
    - 功能实现: include/npu_demo/Arch.h
    */
    long long subthread_id() const {
        return subthread_id_;
    }

    /*
    功能说明:
    - 返回当前 launch 的 subthread extent。

    使用示例:
    - long long snum = ctx.subthread_num();

    创建者: 小李飞刀
    最后修改人: 小李飞刀

    关联文件:
    - spec: spec/include/npu_demo/npu_demo.md
    - test: test/include/npu_demo/test_kernel_context.py
    - 功能实现: include/npu_demo/Arch.h
    */
    long long subthread_num() const {
        return subthread_num_;
    }

    /*
    功能说明:
    - 在当前 launch block 内执行一次带 visibility / scope 的同步。

    使用示例:
    - ctx.barrier({MemorySpace::TSM, MemorySpace::TLM}, BarrierScope::BLOCK);

    创建者: 小李飞刀
    最后修改人: 小李飞刀

    关联文件:
    - spec: spec/include/npu_demo/npu_demo.md
    - test: test/include/npu_demo/test_kernel_context.py
    - 功能实现: include/npu_demo/Arch.h
    */
    inline void barrier(std::initializer_list<MemorySpace> visibility, BarrierScope scope) const {
        if (scope != BarrierScope::BLOCK) {
            throw std::invalid_argument(
                "npu_demo::KernelContext::barrier requires scope=BarrierScope::BLOCK");
        }
        if (visibility.size() != 2) {
            throw std::invalid_argument(
                "npu_demo::KernelContext::barrier visibility must contain MemorySpace::TSM "
                "and MemorySpace::TLM exactly once");
        }
        bool saw_tsm = false;
        bool saw_tlm = false;
        for (MemorySpace space : visibility) {
            switch (space) {
                case MemorySpace::TSM:
                    if (saw_tsm) {
                        throw std::invalid_argument(
                            "npu_demo::KernelContext::barrier visibility must contain MemorySpace::TSM "
                            "and MemorySpace::TLM exactly once");
                    }
                    saw_tsm = true;
                    break;
                case MemorySpace::TLM:
                    if (saw_tlm) {
                        throw std::invalid_argument(
                            "npu_demo::KernelContext::barrier visibility must contain MemorySpace::TSM "
                            "and MemorySpace::TLM exactly once");
                    }
                    saw_tlm = true;
                    break;
                default:
                    throw std::invalid_argument(
                        "npu_demo::KernelContext::barrier visibility only supports "
                        "MemorySpace::TSM and MemorySpace::TLM");
            }
        }
        if (!saw_tsm || !saw_tlm) {
            throw std::invalid_argument(
                "npu_demo::KernelContext::barrier visibility must contain MemorySpace::TSM "
                "and MemorySpace::TLM exactly once");
        }
        if (barrier_state_ == nullptr) {
            throw std::runtime_error(
                "npu_demo::KernelContext::barrier requires active launch context");
        }
        barrier_state_->arrive_and_wait();
    }

    /*
    功能说明:
    - 返回指定片上空间的动态内存视图。

    使用示例:
    - auto tsm = ctx.get_dynamic_memory<TSM, float>();

    创建者: 小李飞刀
    最后修改人: jcc你莫辜负

    关联文件:
    - spec: spec/include/npu_demo/npu_demo.md
    - test: test/include/npu_demo/test_kernel_context.py
    - 功能实现: include/npu_demo/Arch.h
    */
    template <MemorySpace Space, typename T>
    Memory<Space, T> get_dynamic_memory() const {
        if constexpr (Space == MemorySpace::TSM) {
            return detail::make_linear_memory<MemorySpace::TSM, T>(detail::kTsmMemorySize);
        } else if constexpr (Space == MemorySpace::TLM) {
            return detail::make_linear_memory<MemorySpace::TLM, T>(detail::kTlmMemorySize);
        } else if constexpr (Space == MemorySpace::SM) {
            detail::throw_zero_sized_memory(
                "npu_demo::KernelContext::get_dynamic_memory rejected MemorySpace::SM because "
                "sm_memory_size=0");
            return detail::make_linear_memory<MemorySpace::SM, T>(0);
        } else if constexpr (Space == MemorySpace::LM) {
            detail::throw_zero_sized_memory(
                "npu_demo::KernelContext::get_dynamic_memory rejected MemorySpace::LM because "
                "lm_memory_size=0");
            return detail::make_linear_memory<MemorySpace::LM, T>(0);
        } else {
            throw std::invalid_argument(
                "npu_demo::KernelContext::get_dynamic_memory requires on-chip MemorySpace");
        }
    }

private:
    long long block_id_;
    long long block_num_;
    long long thread_id_;
    long long thread_num_;
    long long subthread_id_;
    long long subthread_num_;
    std::shared_ptr<detail::LaunchBarrierState> barrier_state_;
};

}  // namespace npu_demo

/*
功能说明:
- 启动一次 npu_demo P0 kernel 执行，并向 callee 注入运行时 KernelContext。

使用示例:
- Status status = launch<1, 4, 1>(kernel_body, output);

创建者: 小李飞刀
最后修改人: 小李飞刀

关联文件:
- spec: spec/include/api/Arch.md
- test: test/include/api/test_arch.py
- 功能实现: include/npu_demo/Arch.h
*/
template <long long block, long long thread, long long subthread, typename Callable, typename... Args>
inline Status launch(Callable&& callee, Args&&... args) {
    static_assert(
        !std::is_convertible<typename std::decay<Callable>::type, const char*>::value,
        "launch callee must be function object, not string");
    static_assert(
        std::is_invocable<typename std::decay<Callable>::type, npu_demo::KernelContext&, Args...>::value,
        "launch callee must accept npu_demo::KernelContext& as first argument");

    if constexpr (block <= 0 || thread <= 0 || subthread <= 0) {
        return StatusCode::kError;
    }
    if constexpr (
        block != npu_demo::detail::kBlockCapability
        || subthread != npu_demo::detail::kSubthreadCapability
        || thread < 2
        || thread > npu_demo::detail::kThreadCapability) {
        return StatusCode::kError;
    }

    auto barrier_state = std::make_shared<npu_demo::detail::LaunchBarrierState>(thread);
    typename std::decay<Callable>::type callable(std::forward<Callable>(callee));
    std::tuple<Args...> forwarded_args(std::forward<Args>(args)...);
    std::vector<std::thread> workers;
    workers.reserve(static_cast<unsigned long long>(thread));

    for (long long thread_id = 0; thread_id < thread; ++thread_id) {
        workers.emplace_back([&, thread_id]() {
            npu_demo::KernelContext ctx(
                0,
                block,
                thread_id,
                thread,
                0,
                subthread,
                barrier_state);
            std::apply(
                [&](auto&... unpacked_args) {
                    callable(ctx, unpacked_args...);
                },
                forwarded_args);
        });
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
