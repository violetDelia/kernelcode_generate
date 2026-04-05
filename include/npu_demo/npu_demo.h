/*
功能说明:
- 定义 npu_demo 单入口 include，透传 include/api 的统一声明并汇聚后端实现。

使用示例:
- #include "include/npu_demo/npu_demo.h"
- Status status = npu_demo::launch<1, 4, 1>(kernel_body, output);

创建者: 朽木露琪亚
最后修改人: 小李飞刀

关联文件:
- spec: [spec/include/npu_demo/npu_demo.md](spec/include/npu_demo/npu_demo.md)
- test: [test/include/npu_demo/test_kernel_context.py](test/include/npu_demo/test_kernel_context.py)
- 功能实现: [include/npu_demo/npu_demo.h](include/npu_demo/npu_demo.h)
*/

#ifndef KERNELCODE_GENERATE_INCLUDE_NPU_DEMO_NPU_DEMO_H_
#define KERNELCODE_GENERATE_INCLUDE_NPU_DEMO_NPU_DEMO_H_

#include "include/api/Arch.h"
#include "include/api/Memory.h"
#include "include/api/Dma.h"
#include "include/api/Nn.h"
#include "include/npu_demo/Core.h"
#include "include/npu_demo/Arch.h"
#include "include/npu_demo/Memory.h"
#include "include/npu_demo/Dma.h"
#include "include/npu_demo/Nn.h"

#endif  // KERNELCODE_GENERATE_INCLUDE_NPU_DEMO_NPU_DEMO_H_
