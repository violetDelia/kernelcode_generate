时间: 2026-04-05 10:39:19 +0800
经办人: 金铲铲大作战
任务: T-20260405-77b08592（npu_demo_include_kernel_gen S3：include/npu_demo 实现 view/slice/deslice/add）
任务目标: 在 npu_demo include 层补齐 view/slice/deslice/add 的 1-D 子集实现并完善最小验证测试。
改动:
- include/npu_demo/Dma.h：实现 1-D 优先的 view/slice/deslice，补齐步长与边界校验。
- include/npu_demo/Nn.h：实现 1-D add，补齐 shape/stride/data 校验。
- test/include/npu_demo/test_kernel_context.py：新增 NPU-DEMO-KC-006/007 覆盖 DMA 1-D 与 add 1-D；修正 MemorySpace 命名使用并同步最近运行时间。
结论: 测试通过。
- PYTHONPATH=. pytest -q test/include/npu_demo/test_kernel_context.py (exit=0)

时间: 2026-04-05 10:44:47 +0800
经办人: 金铲铲大作战
任务: T-20260405-77b08592（npu_demo_include_kernel_gen S3 复跑）
任务目标: 解决 g++ 偶发 SIGSEGV 并补齐复跑证据。
改动:
- test/include/npu_demo/test_kernel_context.py：为 g++ 添加 -Wl,--no-keep-memory 以缓解链接器偶发 SIGSEGV，同步最近运行时间。
结论: 测试通过。
- PYTHONPATH=. pytest -q test/include/npu_demo/test_kernel_context.py (exit=0)

时间: 2026-04-05 10:45:48 +0800
经办人: 不要啊教练
任务: T-20260405-f8efb199（npu_demo include S3 复审）
任务目标: 复核 1-D 边界校验、include/api 仅声明边界与 gate 证据。
改动:
- 复核 diff 范围：include/npu_demo/Dma.h、include/npu_demo/Nn.h、test/include/npu_demo/test_kernel_context.py；记录文件待纳入变更集。
- 复核 include/api 边界：include/api 未变更，保持仅声明边界未被破坏。
- 复跑 gate：PYTHONPATH=. pytest -q test/include/npu_demo/test_kernel_context.py（exit=0）。
结论: 需修改。
问题列表:
1) 文件/接口：include/npu_demo/Dma.h::view(标量/Vector)
   现象：1-D 视图缺少 offset/size/stride 非法值与越界校验，且未显式限定 rank==1 或明确失败机制。
   风险：负 offset/非正 size/stride 或越界时可能构造非法视图，导致越界访问/未定义行为。
   建议：为 view 增加 1-D 边界校验，并明确无效输入的失败机制（如 contract/显式返回空视图）；补充对应测试锁定。
   优先级：P1
2) 文件/接口：test/include/npu_demo/test_kernel_context.py（NPU-DEMO-KC-006/007）
   现象：新增测试仅覆盖正例与 add 形状不一致负例，未覆盖 view/slice/deslice 的 offset/size/stride 非法值、越界与 rank!=1 负例。
   风险：边界校验不被测试锁定，后续回归易引入越界/错误路径。
   建议：补齐 1-D 负例门禁（非法 offset/size/stride、越界、rank!=1）并断言 StatusCode::kError 或明确失败机制。
   优先级：P1
漏洞排查结果:
- 输入校验绕过：view 缺少 1-D 边界校验，存在绕过风险。
- 类型/形状绕过：slice/deslice/add 有基本校验，但 view 未覆盖；需补齐。
- 边界越界：view 未做越界校验，存在越界风险。
- 错误处理缺失：view 无明确失败机制，需要补充。
- 状态污染：本次改动未引入全局状态写入。
- 资源释放问题：测试使用临时目录与子进程，生命周期受框架管理。
改进建议:
- 补齐 view 1-D 边界校验与负例门禁后再复审。
最终结论: 需修改。建议派生修复任务后复核。

时间: 2026-04-05 12:06:52 +0800
经办人: 金铲铲大作战
任务: T-20260405-382d7490（npu_demo include S3 修复：Dma.view 1-D 边界校验 + 负例门禁）
任务目标: 为 include/npu_demo/Dma.h 的 view(标量/Vector) 补齐 1-D 子集边界校验与明确失败机制，并补齐负例门禁锁定非法 offset/size/stride、越界与 rank!=1。
改动:
- include/npu_demo/Dma.h：为 view(标量/Vector) 补齐 rank==1、Vector 长度一致、非法 offset/size/stride、越界等校验；失败机制统一为抛出 `std::runtime_error("dma.view: ...")`。
- test/include/npu_demo/test_kernel_context.py：新增 NPU-DEMO-KC-008，覆盖 view 标量/Vector 的非法参数、越界与 rank!=1 负例，并断言 runtime_error 关键字（`dma.view`/`invalid offset/size/stride`/`vector_rank_mismatch`/`out_of_bounds`/`rank!=1`）。
结论: 测试通过。
- PYTHONPATH=. pytest -q test/include/npu_demo/test_kernel_context.py (exit=0, 8 passed)

时间: 2026-04-05 12:40:28 +0800
经办人: 不要啊教练
任务: T-20260405-5940bfee（复审：Dma.view 1-D 边界校验与负例门禁）
审查范围: `include/npu_demo/Dma.h` + `test/include/npu_demo/test_kernel_context.py` + 本记录文件（仅复核 Dma.view 相关口径与证据）。

两轮核对（不要轻易通过）:
1) diff 范围/证据完整性:
   - `git diff --name-only` 仍包含 3 个文件：`include/npu_demo/Dma.h`、`include/npu_demo/Nn.h`、`test/include/npu_demo/test_kernel_context.py`；本复审关注 Dma.view，但该链路存在额外文件变更的合并漏审风险（建议合并前明确范围/拆分）。
   - 本记录文件当前为新增文件，需在后续合并链路确保纳入变更集，避免日志漏合并。
2) Dma.view 边界校验与负例门禁复核:
   - 已补齐 1-D 子集校验：`rank==1`、Vector 参数长度==1、`offset>=0/size>0/stride>0`、`source shape/stride >0`、以及 `last_index < shape` 越界拒绝；负例门禁 `NPU-DEMO-KC-008` 已锁定 `invalid offset/size/stride`、`vector_rank_mismatch`、`out_of_bounds`、`rank!=1` 等关键字。
   - 发现高风险漏洞点（未被门禁覆盖）:
     - `last_index = offset + (size - 1) * stride`、`stride_buf[i] = base_stride * stride_i`、`linear_offset += offset_i * base_stride` 等均为 `long long` 运算，当前无 overflow 检查；在极端参数下可能溢出并绕过 `out_of_bounds` 判断，构造 OOB 视图/错误 stride（潜在越界/UB 风险）。
     - 当前负例门禁未覆盖“overflow 绕过”场景，证据不足以证明越界校验稳定。

复跑 gate 证据:
- `PYTHONPATH=. pytest -q test/include/npu_demo/test_kernel_context.py`（exit=0, 8 passed in 1.26s）

结论: 不通过（仍存在潜在越界/UB 风险 + 证据缺口；按规范有任何改进建议必须不通过）。
唯一下一步建议: 新建修复任务，允许修改 `include/npu_demo/Dma.h`、`test/include/npu_demo/test_kernel_context.py`、本记录文件；验收口径:
- 在 `view`(标量/Vector) 内对 `last_index/linear_offset/stride` 相关计算补齐 overflow-safe 校验（溢出视为 invalid/out_of_bounds 并明确失败）。
- 在 `test/include/npu_demo/test_kernel_context.py` 增加可复现的 overflow 负例门禁（至少覆盖标量与 Vector 各 1 条），并断言失败关键字稳定。
- 复跑 `PYTHONPATH=. pytest -q test/include/npu_demo/test_kernel_context.py`（exit=0），并将输出摘要写入记录。

时间: 2026-04-05 12:47:51 +0800
经办人: 金铲铲大作战
任务: T-20260405-a71c06ae（npu_demo Dma.view overflow 风险修复）
任务目标: 为 Dma.view(标量/Vector) 补齐 last_index/linear_offset/stride 的 overflow-safe 校验，并新增 overflow 负例门禁后复跑 kernel_context gate。
改动:
- include/npu_demo/Dma.h：新增非负乘加 checked helper；对 view(标量/Vector) 的 last_index、stride、linear_offset 计算统一加上 overflow-safe 校验，溢出时抛出 `std::runtime_error("dma.view: overflow")`。
- test/include/npu_demo/test_kernel_context.py：新增 NPU-DEMO-KC-009，覆盖标量 last_index overflow、标量 linear_offset overflow、Vector stride overflow 三条负例，并断言 `overflow` 关键字。
- 变更范围说明：本任务未触碰现有 `include/npu_demo/Nn.h` 脏改动；当前 gate 仅验证 Dma.view 链路。
结论: 测试通过。
- PYTHONPATH=. pytest -q test/include/npu_demo/test_kernel_context.py (exit=0, 9 passed)

时间: 2026-04-05 12:55:14 +0800
经办人: 不要啊教练
任务: T-20260405-f17533bc（复审：Dma.view overflow-safe 修复）
审查范围: `include/npu_demo/Dma.h` + `test/include/npu_demo/test_kernel_context.py` + 本记录文件（聚焦 Dma.view overflow 失败关键字、边界校验、变更集范围与 gate 证据）。

两轮核对（不要轻易通过）:
1) 变更集范围/越界风险:
   - `git status --porcelain` 显示工作区改动文件为：`include/npu_demo/Dma.h`、`include/npu_demo/Nn.h`、`test/include/npu_demo/test_kernel_context.py`，另本记录文件为新增未跟踪。
   - 与“仅修复 Dma.view overflow-safe”目标相比，当前变更集仍包含 `include/npu_demo/Nn.h` 的历史脏改动；若后续直接合并，存在合并范围不清/漏审风险（建议合并前明确是否一并合入或拆分收口）。
2) Dma.view overflow-safe 与失败关键字:
   - `Dma.view`(标量/Vector) 已引入 `checked_mul_non_negative/checked_add_non_negative`，对 `span/last_index/linear_offset/stride` 计算加上 overflow-safe 校验；溢出统一抛 `std::runtime_error("dma.view: overflow")`，满足关键字稳定性要求。
   - 负例门禁 `NPU-DEMO-KC-009` 已覆盖：标量 last_index overflow、标量 linear_offset overflow、Vector stride overflow，并断言 `overflow` 关键字（覆盖点满足“overflow 失败关键字”口径）。
   - 额外风险提示（未在本任务目标内但属于同类漏洞面）：`slice/deslice` 仍存在 `offset + (size - 1) * stride`、`offset * source_stride` 等乘加计算无 overflow-safe 校验，理论上仍可溢出绕过越界判断并导致 OOB/UB；如后续要给 S3 全量通过，建议一并补齐与加门禁。

gate 复跑证据（不满足验收）:
- `PYTHONPATH=. pytest -q test/include/npu_demo/test_kernel_context.py`（exit=1）
  - 失败摘要：`collect2: fatal error: ld terminated with signal 11 [Segmentation fault]`（g++ 链接器偶发崩溃，导致用例 `test_npu_demo_dma_view_slice_deslice_supports_1d_subset` 编译失败）。

结论: 不通过（gate exit!=0；且存在合并范围不清风险）。
唯一下一步建议: 派生“稳定 include gate”修复任务，允许修改 `test/include/npu_demo/test_kernel_context.py` + 本记录文件（必要时增加一次性重试/替换链接器/稳定编译参数），并要求在记录中提供连续多次复跑均 exit=0 的证据。

时间: 2026-04-05 13:07:38 +0800
经办人: 金铲铲大作战
任务: T-20260405-1d041b5c（npu_demo include S3 再修复）
任务目标: 为 slice/deslice 补齐 overflow-safe 校验与负例门禁；增强 _compile_and_run 对 ld SIGSEGV 的稳定性；连续多次复跑 gate 并保持 exit=0。
改动:
- include/npu_demo/Dma.h：为 slice/deslice 的 last_index/base/step/max_offset 等计算补齐 overflow-safe 校验（复用 checked_* helper），溢出即返回 StatusCode::kError。
- test/include/npu_demo/test_kernel_context.py：_compile_and_run 增加 ld SIGSEGV 编译重试（最多 3 次）；新增 NPU-DEMO-KC-010 覆盖 slice/deslice overflow 负例；更新覆盖基线与最近运行时间。
结论: 测试通过。
- PYTHONPATH=. pytest -q test/include/npu_demo/test_kernel_context.py (RUN 1, exit=0, 10 passed)
- PYTHONPATH=. pytest -q test/include/npu_demo/test_kernel_context.py (RUN 2, exit=0, 10 passed)
- PYTHONPATH=. pytest -q test/include/npu_demo/test_kernel_context.py (RUN 3, exit=0, 10 passed)

时间: 2026-04-05 13:19:18 +0800
经办人: 提莫炖蘑菇
任务: T-20260405-492208a9（npu_demo include S3 复审：slice/deslice overflow-safe + ld SIGSEGV 重试）
任务目标: 严格复核 include gate 的范围/关键字稳定性/重试不掩盖真实失败，并提供至少 3 次连续 gate exit=0 证据。

复核要点与证据:
1) diff 范围（硬断点：不得包含 include/npu_demo/Nn.h）:
   - `git diff --name-only` 包含: include/npu_demo/Dma.h、include/npu_demo/Nn.h、test/include/npu_demo/test_kernel_context.py
   - `git diff --name-only --cached` 为空（当前未暂存）
   - 结论: 不满足“diff/--cached 均不得包含 include/npu_demo/Nn.h”的硬断点；存在合并越界/漏审风险。

2) overflow 门禁 KC-010 与关键字稳定性:
   - `NPU-DEMO-KC-010` 已新增并覆盖 slice/deslice overflow 参数路径，断言返回 `StatusCode::kError`；对应实现中 overflow 路径返回 `kError`，未见静默成功。
   - `NPU-DEMO-KC-009` 对 view overflow 负例断言 `overflow` 关键字；实现抛 `std::runtime_error("dma.view: overflow")`，关键字稳定。

3) ld SIGSEGV 重试逻辑是否掩盖真实失败:
   - `_compile_and_run` 对编译阶段添加最多 3 次重试，仅在 stderr 命中 `ld terminated with signal`/`SIGSEGV`/`Segmentation fault` 时重试；否则立即抛出 AssertionError。
   - 重试后仍失败会抛出 "g++ compile failed after retries"，不会静默通过。

4) gate 复跑（至少 3 次连续 exit=0）:
   - RUN 1: `PYTHONPATH=. pytest -q test/include/npu_demo/test_kernel_context.py`（exit=0, 10 passed）
   - RUN 2: `PYTHONPATH=. pytest -q test/include/npu_demo/test_kernel_context.py`（exit=0, 10 passed）
   - RUN 3: `PYTHONPATH=. pytest -q test/include/npu_demo/test_kernel_context.py`（exit=0, 10 passed）

结论: 不通过。
不通过原因（唯一硬断点）:
- `include/npu_demo/Nn.h` 仍出现在工作区 diff（实现方提示为既有脏改动亦未清理），与任务要求“git diff --name-only 与 --cached 均不得包含 include/npu_demo/Nn.h”冲突；存在越界合并风险。

唯一下一步建议:
- 派生“清理 Nn.h 脏改动并复跑 gate”任务：要求将 include/npu_demo/Nn.h 恢复到无 diff（working tree + staged 均无该文件），再复跑 3 次 gate 连续 exit=0，并在记录中写入两条 diff 证据与三次 gate 摘要。

时间: 2026-04-05 13:34:03 +0800
经办人: 金铲铲大作战
任务: T-20260405-1d041b5c（npu_demo include S3 修复补充：MemorySpace 声明与 add 调用）
任务目标: 清理 Nn.h 脏改动；修复 MemorySpace 未声明；避免依赖 Nn.h stub 的 add 并稳定通过测试。
改动:
- include/npu_demo/npu_demo.h：显式包含 include/api/Memory.h 引入 MemorySpace；新增 npu_demo::add 的 1-D 子集实现。
- test/include/npu_demo/test_kernel_context.py：add 用例改为调用 npu_demo::add；更新最近运行时间。
- include/npu_demo/Nn.h：已 restore，diff 清零。
结论: 测试通过。
- PYTHONPATH=. pytest -q test/include/npu_demo/test_kernel_context.py (RUN 1, exit=0, 10 passed)
- PYTHONPATH=. pytest -q test/include/npu_demo/test_kernel_context.py (RUN 2, exit=0, 10 passed)
- PYTHONPATH=. pytest -q test/include/npu_demo/test_kernel_context.py (RUN 3, exit=0, 10 passed)

时间: 2026-04-05 13:34:03 +0800
经办人: 金铲铲大作战
任务: T-20260405-90674db0（npu_demo include S3 修复：清理 Nn.h + gate 稳定性）
任务目标: 清理 include/npu_demo/Nn.h 脏改动；确保 MemorySpace 声明可用；连续 3 次复跑 gate 均 exit=0；记录 diff 证据并说明 KC-010/overflow 与 ld 重试口径。
改动:
- include/npu_demo/Nn.h：已 restore，diff/--cached 均不包含该文件。
- include/npu_demo/npu_demo.h：显式包含 include/api/Memory.h，新增 npu_demo::add 1-D 子集实现，避免依赖 Nn.h stub。
- test/include/npu_demo/test_kernel_context.py：add 用例改为 npu_demo::add；_compile_and_run 保留 ld SIGSEGV 重试策略；更新最近运行时间。
- diff 证据（--name-only）：
  - agents/codex-multi-agents/log/task_records/2026/14/20260405-npu-demo-include-s3.md
  - include/npu_demo/Dma.h
  - include/npu_demo/npu_demo.h
  - test/include/npu_demo/test_kernel_context.py
- diff 证据（--name-only --cached）：
  - agents/codex-multi-agents/log/task_records/2026/14/20260405-npu-demo-include-s3.md
结论: 测试通过。
- KC-010/overflow 关键字门禁未回退；ld SIGSEGV 重试仅在 stderr 含 SIGSEGV 关键字时触发，其他编译错误仍直接失败。
- PYTHONPATH=. pytest -q test/include/npu_demo/test_kernel_context.py (RUN 1, exit=0, 10 passed)
- PYTHONPATH=. pytest -q test/include/npu_demo/test_kernel_context.py (RUN 2, exit=0, 10 passed)
- PYTHONPATH=. pytest -q test/include/npu_demo/test_kernel_context.py (RUN 3, exit=0, 10 passed)

时间: 2026-04-05 13:45:20 +0800
经办人: 提莫炖蘑菇
任务: T-20260405-5a7c75e1（复审：Nn.h 清理 + npu_demo::add 实现与 gate 3 次稳定性）
任务目标: 复核 diff/--cached 不含 include/npu_demo/Nn.h；确认 MemorySpace 由 npu_demo.h 正确包含；核对 npu_demo::add 1-D 路径与测试使用不依赖 Nn.h stub；复跑 gate 至少 3 次 exit=0 并写证据。

复核结论: 不通过（存在可改进点；按审查规范“有任何改进建议即不通过”）。

时间: 2026-04-05 13:53:32 +0800
经办人: 李白
任务: T-20260405-cbbec7d1（合并收口）
任务目标: 合并收口 npu_demo include S3，复跑 gate 并写入记录；确认 diff/--cached 不含 include/npu_demo/Nn.h。
改动:
- 复跑 gate：PYTHONPATH=. pytest -q test/include/npu_demo/test_kernel_context.py（exit=0；10 passed in 1.69s）。
- 范围核对：git diff --name-only 与 git diff --name-only --cached 均不包含 include/npu_demo/Nn.h。
结论: gate 通过，可进入合并收口；未触碰 include/npu_demo/Nn.h。

证据与核对点:
1) diff/--cached 范围（硬断点通过）:
   - `git diff --name-only`:
     - agents/codex-multi-agents/log/task_records/2026/14/20260405-npu-demo-include-s3.md
     - include/npu_demo/Dma.h
     - include/npu_demo/npu_demo.h
     - test/include/npu_demo/test_kernel_context.py
   - `git diff --name-only --cached`:
     - agents/codex-multi-agents/log/task_records/2026/14/20260405-npu-demo-include-s3.md
   - 结论: working tree 与 staged 均不包含 include/npu_demo/Nn.h（满足本轮复核硬断点）。

2) MemorySpace include（通过）:
   - include/npu_demo/npu_demo.h 已显式 `#include "include/api/Memory.h"`，测试中 `MemorySpace::{TSM,TLM,SM,LM}` 可用。

3) npu_demo::add 1-D 路径与测试依赖边界（需修正口径）:
   - include/npu_demo/npu_demo.h 已提供 `npu_demo::add` 的 1-D 子集实现；测试 `test_npu_demo_add_supports_1d_subset` 已调用 `npu_demo::add(...)`。
   - 但测试注释 `NPU-DEMO-KC-007` 的“对应功能实现文件链接”仍指向 [include/npu_demo/Nn.h](include/npu_demo/Nn.h)，与当前实现位置不一致，易造成“仍依赖 Nn.h stub”的误读与后续维护偏差。
   - 同时 include/npu_demo/npu_demo.h 仍包含 `#include "include/npu_demo/Nn.h"`；若目标口径为“测试不依赖 Nn.h stub（含编译期依赖）”，建议移除该 include（在无实际引用前提下）并仅保留 `npu_demo::add` 入口。

4) gate 复跑（通过；三次连续 exit=0）:
   - RUN 1: `PYTHONPATH=. pytest -q test/include/npu_demo/test_kernel_context.py`（exit=0, 10 passed）
   - RUN 2: `PYTHONPATH=. pytest -q test/include/npu_demo/test_kernel_context.py`（exit=0, 10 passed）
   - RUN 3: `PYTHONPATH=. pytest -q test/include/npu_demo/test_kernel_context.py`（exit=0, 10 passed）

唯一下一步建议:
- 派生修复任务：修正 `NPU-DEMO-KC-007` 的“对应功能实现文件链接”为 [include/npu_demo/npu_demo.h](include/npu_demo/npu_demo.h)，并评估移除 include/npu_demo/npu_demo.h 对 include/npu_demo/Nn.h 的不必要 include 以满足“不依赖 stub”口径；复跑 gate 3 次连续 exit=0，并补齐 `git diff --name-only` 与 `--cached` 证据。

时间: 2026-04-05 13:53:40 +0800
经办人: 提莫炖蘑菇
任务: T-20260405-8d3e80fe（复审：KC-007 链接修正与 npu_demo.h 去 Nn.h 依赖）
任务目标: 复核 include/npu_demo/npu_demo.h 已去除对 include/npu_demo/Nn.h 的依赖；KC-007 功能实现链接改为 include/npu_demo/npu_demo.h；diff/--cached 不含 Nn.h；复跑 gate 3 次 exit=0。

复核结论: 通过。

复核证据:
1) diff/--cached 范围:
   - `git diff --name-only`:
     - agents/codex-multi-agents/log/task_records/2026/14/20260405-npu-demo-include-s3.md
     - include/npu_demo/Dma.h
     - include/npu_demo/npu_demo.h
     - test/include/npu_demo/test_kernel_context.py
   - `git diff --name-only --cached`:
     - agents/codex-multi-agents/log/task_records/2026/14/20260405-npu-demo-include-s3.md
   - 结论: working tree 与 staged 均不包含 `include/npu_demo/Nn.h`。

2) `npu_demo.h` 依赖边界:
   - `include/npu_demo/npu_demo.h` 当前 include 为：
     - `include/api/Memory.h`
     - `include/npu_demo/Core.h`
     - `include/npu_demo/Dma.h`
     - `include/npu_demo/Memory.h`
   - 未再包含 `include/npu_demo/Nn.h`；`MemorySpace` 由 `include/api/Memory.h` 提供。

3) KC-007 链接与 add 路径:
   - `test/include/npu_demo/test_kernel_context.py` 的 `NPU-DEMO-KC-007` “对应功能实现文件链接”已改为 [include/npu_demo/npu_demo.h](include/npu_demo/npu_demo.h)。
   - 测试源码直接 `#include "include/npu_demo/npu_demo.h"` 并调用 `npu_demo::add(lhs, rhs, out)`，不再依赖 `Nn.h` stub。

4) gate 复跑（3 次连续 exit=0）:
   - RUN 1: `PYTHONPATH=. pytest -q test/include/npu_demo/test_kernel_context.py`（exit=0, 10 passed）
   - RUN 2: `PYTHONPATH=. pytest -q test/include/npu_demo/test_kernel_context.py`（exit=0, 10 passed）
   - RUN 3: `PYTHONPATH=. pytest -q test/include/npu_demo/test_kernel_context.py`（exit=0, 10 passed）

风险复核:
- 未发现 `Nn.h` 混入当前变更集或编译依赖回退。
- `npu_demo::add` 1-D 路径与 KC-007 正/负例保持一致；本轮指定 gate 未见回归。

唯一下一步建议:
- 进入同链路“合并收口”任务，限定合并当前 worktree 的业务文件与本记录文件。

时间: 2026-04-05 13:48:51 +0800
经办人: 金铲铲大作战
任务: T-20260405-21239a40（npu_demo include S3 修复：KC-007 链接与 Nn.h 解耦）
任务目标: 更新 KC-007 功能实现链接；移除 npu_demo.h 对 Nn.h 引用；连续 3 次复跑 gate 且 diff/--cached 不含 Nn.h。
改动:
- include/npu_demo/npu_demo.h：移除对 include/npu_demo/Nn.h 的引用，避免依赖 stub。
- test/include/npu_demo/test_kernel_context.py：KC-007 功能实现链接改为 include/npu_demo/npu_demo.h；更新最近运行时间。
- diff 证据（--name-only）：
  - agents/codex-multi-agents/log/task_records/2026/14/20260405-npu-demo-include-s3.md
  - include/npu_demo/Dma.h
  - include/npu_demo/npu_demo.h
  - test/include/npu_demo/test_kernel_context.py
- diff 证据（--name-only --cached）：
  - agents/codex-multi-agents/log/task_records/2026/14/20260405-npu-demo-include-s3.md
结论: 测试通过。
- PYTHONPATH=. pytest -q test/include/npu_demo/test_kernel_context.py (RUN 1, exit=0, 10 passed)
- PYTHONPATH=. pytest -q test/include/npu_demo/test_kernel_context.py (RUN 2, exit=0, 10 passed)
- PYTHONPATH=. pytest -q test/include/npu_demo/test_kernel_context.py (RUN 3, exit=0, 10 passed)
