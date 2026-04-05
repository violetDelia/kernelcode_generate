时间：2026-04-05 16:06:27 +0800
经办人：jcc你莫辜负
任务：T-20260405-d2b940e5
任务目标：收口 include/npu_demo/npu_demo.h 为单入口 include，透传 include/api/{Memory,Dma,Nn}.h，并与 spec/include/npu_demo/npu_demo.md、test/include/npu_demo/test_kernel_context.py 对齐；完成 gate。
改动：
- include/npu_demo/npu_demo.h：更新头注释与 include 列表，新增 api/Dma.h、api/Nn.h 与 npu_demo/Nn.h，移除 npu_demo::add 本地实现。
- spec/include/npu_demo/npu_demo.md：更新限制与边界中 npu_demo.h 单入口+透传 API 头文件描述。
- test/include/npu_demo/test_kernel_context.py：KC-007 改为 include/npu_demo/npu_demo.h；更新实现链接与最近运行时间。
测试：
- PYTHONPATH=. pytest -q test/include/npu_demo/test_kernel_context.py（10 passed）
结论：npu_demo.h 单入口 include 透传 API 头并汇聚后端实现，spec/test 对齐，gate 通过。
时间：2026-04-05 17:20:00 +0800
经办人：提莫炖蘑菇
任务：T-20260405-d2b940e5（复审：npu_demo 单入口 include S5）
任务目标：核对 `include/npu_demo/npu_demo.h` 单入口透传 `include/api/{Memory,Dma,Nn}.h` 与后端实现汇聚，KC-007 使用 npu_demo.h 对齐；两轮核对 diff/--cached 范围并复跑 gate。

结论：通过。

范围核对：
- `git diff --name-only` 包含：
  - `include/npu_demo/npu_demo.h`
  - `spec/include/npu_demo/npu_demo.md`
  - `test/include/npu_demo/test_kernel_context.py`
- `git diff --name-only --cached` 为空（未发现额外 staged 越界）。

单入口 include 依赖核对：
- `include/npu_demo/npu_demo.h` 仅新增 `include/api/Dma.h`、`include/api/Nn.h` 与 `include/npu_demo/Nn.h`，并保留 `include/api/Memory.h` 与 `include/npu_demo/{Core,Memory,Dma}.h`，符合“单入口透传 API 头并汇聚后端实现”口径；未引入其它多余依赖。
- KC-007 已改为 `#include "include/npu_demo/npu_demo.h"` 并更新实现链接，符合单入口对齐目标。

复跑证据：
- 命令：`cd wt-20260405-npu-demo-include-s5 && PYTHONPATH=. pytest -q test/include/npu_demo/test_kernel_context.py`
- 结果：`10 passed in 2.07s`
- exit code：0

漏洞排查结果：
- 输入校验绕过：本轮未新增可绕过路径；单入口 include 仍依赖原有实现校验。
- 类型/形状绕过：本轮不涉及新增类型/形状合同。
- 边界越界：单入口 include 仅聚合头文件，不引入新边界。
- 错误处理缺失：未见新增缺失点。
- 状态污染：仅涉及指定文件与记录文件；未见额外越界文件。
- 资源释放问题：本轮不涉及。

问题列表：
- 未发现必须修改项。

改进建议：
- 未发现额外改进点。

最终结论：
- 通过。唯一下一步建议：进入合并收口任务，合并 `include/npu_demo/npu_demo.h`、`spec/include/npu_demo/npu_demo.md`、`test/include/npu_demo/test_kernel_context.py` 与同链记录文件。
时间：2026-04-05 16:20:00 +0800
经办人：提莫炖蘑菇
任务：T-20260405-e8dff9d6（同链复审任务；记录中 T-20260405-d2b940e5 为历史误写/旧任务号）
补充说明：
- 二次核对 `git diff --name-only` 仍仅包含 `include/npu_demo/npu_demo.h`、`spec/include/npu_demo/npu_demo.md`、`test/include/npu_demo/test_kernel_context.py`。
- 二次核对 `git diff --name-only --cached` 仍为空。
- 结论维持通过，后续合并任务以 T-20260405-e8dff9d6 流转。

时间：2026-04-05 16:21:21 +0800
经办人：李白
任务：T-20260405-4689e197（合并收口）
任务目标：复跑 gate 并记录；按限定范围合入 `include/npu_demo/npu_demo.h`、`spec/include/npu_demo/npu_demo.md`、`test/include/npu_demo/test_kernel_context.py` 与同链记录。
改动：
- 范围核对：
  - `git diff --name-only` 仅含：
    - `include/npu_demo/npu_demo.h`
    - `spec/include/npu_demo/npu_demo.md`
    - `test/include/npu_demo/test_kernel_context.py`
  - `git diff --name-only --cached` 为空
- 复跑 gate：
  - `PYTHONPATH=. pytest -q test/include/npu_demo/test_kernel_context.py`
  - 结果：`10 passed in 2.16s`
  - exit code：`0`
结论：范围与 gate 均满足合并条件。
