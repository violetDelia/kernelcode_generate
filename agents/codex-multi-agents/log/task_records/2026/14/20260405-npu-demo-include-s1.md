时间: 2026-04-05 02:27:54 +0800
经办人: 金铲铲大作战
任务: T-20260405-d1d6ada1（npu_demo_include_kernel_gen_green_plan S1）
任务目标: 冻结 include/api(仅声明) vs include/npu_demo(实现) 分层职责，并明确 gen_kernel 生成源码 include 与 compile gate 目标。
改动:
- include/api/Core.h/Memory.h/Dma.h/Nn.h 调整为声明式 API，npu_demo 对应实现放入 include/npu_demo/{Core,Memory,Dma,Nn}.h。
- include/npu_demo/Dma.h 增补 Vector 版本 view/slice/deslice 实现与包含 include/api/Dma.h，保证 API 声明与实现分层一致。
- include/npu_demo/npu_demo.h 汇聚 Core/Memory/Dma/Nn 实现，make_linear_memory 调整构造顺序。
- kernel_gen/dsl/gen_kernel.py 在 target=npu_demo 时注入 #include "include/npu_demo/npu_demo.h"。
- spec/include/api/{Core,Memory,Dma,Nn}.md 与 spec/include/npu_demo/npu_demo.md 写明 include/api 仅声明、include/npu_demo 承载实现；spec/dsl/gen_kernel.md 写明 include 与 compile gate（-c）。
- test/dsl/test_gen_kernel.py 增加 npu_demo compile-only gate，调整 GK-017 断言 include；test/include/api/test_core.py 改为引入 include/npu_demo/Core.h 实现层。
结论: 测试通过。
- pytest -q test/dsl/test_gen_kernel.py -k "npu_demo" (exit=0)
- pytest -q test/include/api/test_core.py (exit=0)

- 时间：`2026-04-05 02:31:26 +0800`
- 经办人：`不要啊教练`
- 任务：`T-20260405-49cc719b`
- 任务目标：
  - 复审 include/api 仅声明、include/npu_demo 承接实现与 gen_kernel include 注入；复跑 npu_demo gate。
- 改动：
  - 追加复审记录；未修改实现/测试。
- 核对：
  - `git diff --name-only` 范围仅 `include/api/Core.h`、`include/npu_demo/npu_demo.h`、`kernel_gen/dsl/gen_kernel.py`、`spec/include/api/*.md`、`spec/include/npu_demo/npu_demo.md`、`spec/dsl/gen_kernel.md`、`test/dsl/test_gen_kernel.py`、`test/include/api/test_core.py` 与记录文件，符合回报清单。
  - `include/api/Core.h` 仅包含类型/方法声明，无函数体实现；实现集中于 `include/npu_demo/*.h`。
  - `test/dsl/test_gen_kernel.py` 通过 compile-only gate 验证 include 注入；断言包含 `#include "include/npu_demo/npu_demo.h"` 稳定。
- 测试：
  - `pytest -q test/dsl/test_gen_kernel.py -k npu_demo`（exit=0）
  - `pytest -q test/include/api/test_core.py`（exit=0）
- 结论：
  - 实现/规格/测试对齐；include/api 未混入实现，compile-only gate 稳定；未发现越界、类型绕过、异常处理缺失等风险，通过。

时间: 2026-04-05 03:07:12 +0800
经办人: 李白
任务: T-20260405-251880e3
任务目标: 合并收口 npu_demo include S1；合入 include/api 仅声明、include/npu_demo 实现分层、gen_kernel include 注入 + compile-only gate 相关文件与记录。
改动: 无（合并前范围核对）

范围核对:
- cd wt-20260405-npu-demo-include-s1 && git diff --name-only
  - include/api/Core.h
  - include/npu_demo/npu_demo.h
  - kernel_gen/dsl/gen_kernel.py
  - spec/dsl/gen_kernel.md
  - spec/include/api/Core.md
  - spec/include/api/Dma.md
  - spec/include/api/Memory.md
  - spec/include/api/Nn.md
  - spec/include/npu_demo/npu_demo.md
  - test/dsl/test_gen_kernel.py
  - test/include/api/test_core.py
- 未跟踪新增文件（git status）:
  - include/api/Dma.h
  - include/api/Memory.h
  - include/api/Nn.h
  - include/npu_demo/Core.h
  - include/npu_demo/Dma.h
  - include/npu_demo/Memory.h
  - include/npu_demo/Nn.h
  - agents/codex-multi-agents/log/task_records/2026/14/20260405-npu-demo-include-s1.md
结论: 范围符合要求；复测证据已在记录中（exit=0），可执行合并收口。
