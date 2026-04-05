/*
功能说明:
- 定义 include/api 层统一对外的 launch / barrier 公开接口声明。

使用示例:
- #include "include/api/Arch.h"
- BarrierScope scope = BarrierScope::BLOCK;

创建者: 小李飞刀
最后修改人: 小李飞刀

关联文件:
- spec: spec/include/api/Arch.md
- test: test/include/api/test_arch.py
- 功能实现: include/npu_demo/Arch.h
*/

#ifndef KERNELCODE_GENERATE_INCLUDE_API_ARCH_H_
#define KERNELCODE_GENERATE_INCLUDE_API_ARCH_H_

#include "include/api/Core.h"
#include "include/api/Memory.h"

/*
功能说明:
- 定义公开 barrier 同步范围枚举。

使用示例:
- BarrierScope scope = BarrierScope::BLOCK;

创建者: 小李飞刀
最后修改人: 小李飞刀

关联文件:
- spec: spec/include/api/Arch.md
- test: test/include/api/test_arch.py
- 功能实现: include/npu_demo/Arch.h
*/
enum class BarrierScope {
    BLOCK,
    THREAD,
};

/*
功能说明:
- 声明公开 kernel launch 入口，具体后端实现由私有 include 提供。

使用示例:
- Status status = launch<1, 4, 1>(kernel_body, input, output);

创建者: 小李飞刀
最后修改人: 小李飞刀

关联文件:
- spec: spec/include/api/Arch.md
- test: test/include/api/test_arch.py
- 功能实现: include/npu_demo/Arch.h
*/
template <long long block, long long thread, long long subthread, typename Callable, typename... Args>
Status launch(Callable&& callee, Args&&... args);

#endif  // KERNELCODE_GENERATE_INCLUDE_API_ARCH_H_
