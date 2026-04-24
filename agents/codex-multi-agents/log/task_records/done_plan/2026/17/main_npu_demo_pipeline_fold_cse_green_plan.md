# main_npu_demo_pipeline_fold_cse_green_plan.md

> 说明：文件名沿用前一版计划主题，当前已按用户最新确认收口为 `launch_kernel[...] shared memory size + xdsl rewrite folding`。本轮不新增 `canonicalize`、`cse`、`fold-canonicalize` 独立 pass。

## 文档信息

- 创建者：`Codex`
- 最后一次更改：`小李飞刀`
- 目标 `spec`：
  - [`spec/operation/arch.md`](../../spec/operation/arch.md)
  - [`spec/dialect/arch.md`](../../spec/dialect/arch.md)
  - [`spec/dsl/ast.md`](../../spec/dsl/ast.md)
  - [`spec/dsl/mlir_gen.md`](../../spec/dsl/mlir_gen.md)
  - [`spec/dsl/emit_mlir.md`](../../spec/dsl/emit_mlir.md)
  - [`spec/dsl/gen_kernel.md`](../../spec/dsl/gen_kernel.md)
  - [`spec/tools/dsl_run.md`](../../spec/tools/dsl_run.md)
  - [`spec/pass/attach_arch_information.md`](../../spec/pass/attach_arch_information.md)
  - [`spec/pass/outline_device_kernel.md`](../../spec/pass/outline_device_kernel.md)
  - [`spec/pass/pipeline/npu_demo_lowering.md`](../../spec/pass/pipeline/npu_demo_lowering.md)
  - [`spec/include/api/Arch.md`](../../spec/include/api/Arch.md)
  - [`spec/include/npu_demo/npu_demo.md`](../../spec/include/npu_demo/npu_demo.md)
  - [`spec/target/registry.md`](../../spec/target/registry.md)
- 目标 `API`：
  - `launch_kernel[block, thread, subthread, shared_memory_size](callee, *args)`
  - `arch.launch<block, thread, subthread, shared_memory_size>(@callee, args...)`
  - `launch<block, thread, subthread, shared_memory_size>(callee, args...)`
  - `npu_demo::launch<block, thread, subthread, shared_memory_size>(callee, args...)`
  - `build_registered_pipeline("npu-demo-lowering", {"target": "npu_demo"})`
  - `dsl_run(fn, args, "npu-demo-lowering", EmitCContext(target="npu_demo"))`
  - `python3 main.py`
- 目标 `test`：
  - [`test/operation/test_operation_arch.py`](../../test/operation/test_operation_arch.py)
  - [`test/dialect/test_arch_dialect.py`](../../test/dialect/test_arch_dialect.py)
  - [`test/dsl/test_ast.py`](../../test/dsl/test_ast.py)
  - [`test/dsl/test_ast_visitor.py`](../../test/dsl/test_ast_visitor.py)
  - [`test/dsl/test_mlir_gen.py`](../../test/dsl/test_mlir_gen.py)
  - [`test/dsl/test_gen_kernel.py`](../../test/dsl/test_gen_kernel.py)
  - [`test/pass/test_attach_arch_information.py`](../../test/pass/test_attach_arch_information.py)
  - [`test/pass/outline_device_kernel/test_outline_device_kernel.py`](../../test/pass/outline_device_kernel/test_outline_device_kernel.py)
  - [`test/pass/test_pipeline_npu_demo_lowering.py`](../../test/pass/test_pipeline_npu_demo_lowering.py)
  - [`test/tools/test_dsl_run.py`](../../test/tools/test_dsl_run.py)
  - [`test/include/api/test_arch.py`](../../test/include/api/test_arch.py)
  - [`test/include/npu_demo/test_public_namespace.py`](../../test/include/npu_demo/test_public_namespace.py)
  - [`test/include/npu_demo/test_runtime_launch.py`](../../test/include/npu_demo/test_runtime_launch.py)
  - [`test/include/npu_demo/test_kernel_context.py`](../../test/include/npu_demo/test_kernel_context.py)
  - [`test/target/test_target_registry.py`](../../test/target/test_target_registry.py)
  - [`test/tools/test_ircheck_runner.py`](../../test/tools/test_ircheck_runner.py)
  - `test/test_main_npu_demo_pipeline.py`（本计划要求补齐）
- 目标 `验收资产`：
  - [`expectation/pass/tuning/launch_kernel_cost_func`](../../expectation/pass/tuning/launch_kernel_cost_func)
  - [`expectation/pass/tuning/launch_kernel_cost_func_compute_memory`](../../expectation/pass/tuning/launch_kernel_cost_func_compute_memory)
  - 当前不再纳入本计划保留合同集合的主动删除资产：
    - `expectation.operation.arch`
    - `expectation.dsl.mlir_gen.dialect.arch`
    - `expectation.pass.outline_device_kernel`
    - `expectation.execute_engine.npu_demo.default`
    - `expectation.tools.dsl_run`
- 目标 `功能实现`：
  - [`main.py`](../../main.py)
  - [`kernel_gen/operation/arch.py`](../../kernel_gen/operation/arch.py)
  - [`kernel_gen/dialect/arch.py`](../../kernel_gen/dialect/arch.py)
  - [`kernel_gen/dsl/ast/nodes.py`](../../kernel_gen/dsl/ast/nodes.py)
  - [`kernel_gen/dsl/ast/parser.py`](../../kernel_gen/dsl/ast/parser.py)
  - [`kernel_gen/dsl/mlir_gen/emit/core.py`](../../kernel_gen/dsl/mlir_gen/emit/core.py)
  - [`kernel_gen/passes/attach_arch_information.py`](../../kernel_gen/passes/attach_arch_information.py)
  - [`kernel_gen/passes/outline_device_kernel.py`](../../kernel_gen/passes/outline_device_kernel.py)
  - [`kernel_gen/passes/pipeline/npu_demo_lowering.py`](../../kernel_gen/passes/pipeline/npu_demo_lowering.py)
  - [`kernel_gen/dsl/gen_kernel.py`](../../kernel_gen/dsl/gen_kernel.py)
  - [`kernel_gen/tools/dsl_run.py`](../../kernel_gen/tools/dsl_run.py)
  - [`kernel_gen/target/registry.py`](../../kernel_gen/target/registry.py)
  - [`kernel_gen/target/targets/npu_demo.txt`](../../kernel_gen/target/targets/npu_demo.txt)
  - [`include/api/Arch.h`](../../include/api/Arch.h)
  - [`include/npu_demo/Arch.h`](../../include/npu_demo/Arch.h)

## 任务清单

| 任务 | 前置任务 | worktree | 记录文件 |
| --- | --- | --- | --- |
| `S1：launch shared memory ABI 与 IR/operation 收口` | 无 | `wt-20260422-main-npu-demo-launch-s1` | `agents/codex-multi-agents/log/task_records/2026/17/20260422-main-npu-demo-launch-s1.md` |
| `S2：pattern folding 接入现有 xdsl rewrite pass` | `S1` | `wt-20260422-main-npu-demo-launch-s2` | `agents/codex-multi-agents/log/task_records/2026/17/20260422-main-npu-demo-launch-s2.md` |
| `S3：main.py host/kernel 输出与 npu_demo 运行链路收口` | `S1,S2` | `wt-20260422-main-npu-demo-launch-s3` | `agents/codex-multi-agents/log/task_records/2026/17/20260422-main-npu-demo-launch-s3.md` |

## 任务创建记录

- `2026-04-22`：已创建 `S1` 任务 `T-20260422-e5e78096`，类型 `spec`，依赖 `None`。
- `2026-04-22`：已创建 `S2` 任务 `T-20260422-f94ed233`，类型 `build`，依赖 `T-20260422-e5e78096`。
- `2026-04-22`：已创建 `S3` 任务 `T-20260422-fdaf38a1`，类型 `build`，依赖 `T-20260422-e5e78096,T-20260422-f94ed233`。
- 下一步：由管理员按当前并发资源先分发 `T-20260422-e5e78096`；`S2/S3` 等依赖完成后再进入分发。

## 评审摘要

- 评审结论：`通过`
- 评审人：`大闸蟹、守护最好的爱莉希雅、睡觉小分队；提莫炖蘑菇、不要啊教练已询问但截至本次推进未回复`
- 结论摘要：`大闸蟹、守护最好的爱莉希雅、睡觉小分队复评均为通过。当前计划已补 include/runtime shared_memory_size 失败边界、spec/tools/dsl_run.md、本轮相关 expectation 口径、旧三字段 launch 残留扫描，并将 test/include/npu_demo/test_public_namespace.py 与 test/tools/test_ircheck_runner.py 纳入 S1/S3 和验收设计。S1/S2/S3 拆分与依赖可执行：S1 收四字段 ABI 链，S2 收现有 xdsl rewrite folding，S3 收 main.py/gen_kernel/dsl_run 真实执行链路。`
- 协同询问记录：
  - `2026-04-22`：`榕 -> 大闸蟹`，询问 S1 是否过大、S2 folding 边界、S3 main.py 链路依赖与旧三字段消费者遗漏。
  - `2026-04-22`：`榕 -> 守护最好的爱莉希雅`，询问四字段 ABI 全链路收口、S1/S2/S3 拆分、target registry 真源与 standalone cleanup pass 排除。
  - `2026-04-22`：`榕 -> 睡觉小分队`，询问 spec 参数顺序、失败边界、`!symbol.int` 类型约束、folding 合同与合同真源完整性。
  - `2026-04-22`：`榕 -> 提莫炖蘑菇`，询问旧三字段残留、红转绿 expectation 边界、main.py 真实链路与动态 symbol 误折叠风险。
  - `2026-04-22`：`睡觉小分队 -> 榕`，结论 `最小需改项`：include/runtime 段缺 shared memory size 非负与失败边界；目标 spec 缺 `spec/tools/dsl_run.md`。
  - `2026-04-22`：`大闸蟹 -> 榕`，结论 `最小需改项`：终验 expectation 口径应改为本轮相关；S1/S3 补旧三字段残留扫描并点名 `test/include/npu_demo/test_public_namespace.py`、`test/tools/test_ircheck_runner.py`。
  - `2026-04-22`：`守护最好的爱莉希雅 -> 榕`，结论 `最小需改项`：任务拆分可推进；同意补本轮相关 expectation 口径和旧三字段残留扫描。
  - `2026-04-22`：`守护最好的爱莉希雅 -> 榕`，复评结论 `通过`：本轮相关 expectation 口径、旧三字段残留扫描、`test/include/npu_demo/test_public_namespace.py` 与 `test/tools/test_ircheck_runner.py` 验收入口已写入正文；S1/S2/S3 拆分和依赖可推进。
  - `2026-04-22`：`大闸蟹 -> 榕`，复评结论 `通过`：最小需改项均已写入正文，S1/S2/S3 拆分和依赖顺序可执行。
  - `2026-04-22`：`睡觉小分队 -> 榕`，复评结论 `通过`：`spec/tools/dsl_run.md`、include/runtime 四模板与 shared memory size 失败边界、`test/tools/test_ircheck_runner.py` 验收均已补齐。
  - `2026-04-22`：`榕 -> 不要啊教练`，补充 review 风险询问，聚焦旧三字段扫描、runtime 失败边界、本轮相关 expectation 与 main.py 真实链路；截至本次推进未收到回复，且已有三方通过、无冲突观点。

## 终验 / 复验 / 修复复核记录

- 说明：本节保留各轮终验 / 复验当时实际执行的命令原文。用户已在 `2026-04-24` 明确确认 `expectation.operation.arch`、`expectation.dsl.mlir_gen.dialect.arch`、`expectation.pass.outline_device_kernel`、`expectation.execute_engine.npu_demo.default`、`expectation.tools.dsl_run` 为主动删除；当前正文里的现行 expectation 清单以上文“目标 `验收资产`”、下文“当前基线”“合同真源顺序”和各阶段“验收必过项目”为准。

- 结论人：`大闸蟹`
- 结论：`不通过`
- 验证基线：`主目录 /home/lfr/kernelcode_generate 已先执行 git fetch；当前主目录 main 与 origin/main 一致，基线 commit 为 e143d1ef6d5f64e37f32c91f90a4a87203172131。`
- 执行目录：`/home/lfr/kernelcode_generate`
- 合同验收摘要：`本轮按当前规则只执行与本计划相关的 expectation 合同验收：1）PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 -m expectation.operation.arch，exit 0；2）PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 -m expectation.dsl.mlir_gen.dialect.arch，exit 0；3）PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 -m expectation.pass.outline_device_kernel，exit 0；4）PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 -m expectation.pass.tuning.launch_kernel_cost_func，exit 0；5）PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 -m expectation.execute_engine.npu_demo.default，exit 0；6）PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 -m expectation.tools.dsl_run，exit 0。`
- 最小阻断项或通过摘要：`相关 expectation 已全部通过，但当前仓库仍存在可执行收口点，本轮不能给通过。最小阻断项有两处：1）spec/dsl/gen_kernel.md 仍保留三字段 arch.launch<%b, %t, %s>(@missing_body, ...) 示例，和本计划四字段 shared_memory_size 合同不一致；2）spec/dsl/ast.md、spec/dsl/mlir_gen.md、spec/operation/arch.md 以及 kernel_gen/dsl/ast/parser.py 仍把 launch_kernel(callee, block, thread, subthread, shared_memory_size, *args) 作为公开或兼容入口写在正文里，和本计划把 launch_kernel[...] 作为公开 DSL 入口的收口目标不一致。`
- 是否已创建修复任务：`否`
- 修复任务创建人：`不适用`
- 另一位架构师补充重点：`本次复验仅据最新主线现场与相关 expectation 结果给出；若后续要推进修复任务，应先把上述两类旧口径统一收到四字段下标式公开入口。`

- 结论人：`守护最好的爱莉希雅`
- 结论：`不通过`
- 验证基线：`已先在主目录 /home/lfr/kernelcode_generate 执行 git fetch；复验现场使用最新远端干净 worktree /home/lfr/kernelcode_generate-wt-20260424-main-npu-demo-final（detached HEAD e143d1e，对应 origin/main@e143d1e6fd52fa80c28e5af13d0e44cc8834e227）。该远端现场不含 expectation 目录，本轮合同验收使用 PYTHONPATH=/home/lfr/kernelcode_generate-wt-20260424-main-npu-demo-final:/home/lfr/kernelcode_generate 组合现场执行。`
- 执行目录：`/home/lfr/kernelcode_generate-wt-20260424-main-npu-demo-final`
- 合同验收摘要：`本轮按当前规则只执行与本计划相关的 expectation 合同验收：1）PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/home/lfr/kernelcode_generate-wt-20260424-main-npu-demo-final:/home/lfr/kernelcode_generate python3 -m expectation.operation.arch，exit 0；2）... python3 -m expectation.dsl.mlir_gen.dialect.arch，exit 0；3）... python3 -m expectation.pass.outline_device_kernel，exit 0；4）... python3 -m expectation.pass.tuning.launch_kernel_cost_func，exit 0；5）... python3 -m expectation.tools.dsl_run，exit 0；6）... python3 -m expectation.execute_engine.npu_demo.default，exit 1。`
- 最小阻断项或通过摘要：`本轮唯一明确阻断项是 expectation.execute_engine.npu_demo.default 目录入口自身不一致：__main__.py 仍导入 expectation.execute_engine.npu_demo.default.fa_online_softmax，但当前仓库已不存在该源文件，导致目录级合同验收直接以 ModuleNotFoundError 失败。在该入口恢复为可执行前，本计划不能给通过。其余本轮相关 expectation 入口 operation.arch、dsl.mlir_gen.dialect.arch、pass.outline_device_kernel、pass.tuning.launch_kernel_cost_func、tools.dsl_run 均已通过。`
- 是否已创建修复任务：`不适用`
- 修复任务创建人：`不适用`
- 另一位架构师补充重点：`守护最好的爱莉希雅已复评通过；大闸蟹已复评通过；睡觉小分队 spec 复评通过；当前无冲突观点。`

- 结论人：`守护最好的爱莉希雅`
- 结论：`已按当前双架构不通过口径创建唯一修复任务`
- 验证基线：`修复任务依据当前双架构最新不通过结论创建；阻断以 spec / parser 旧公开口径收口为准。`
- 最小阻断项或通过摘要：`已创建唯一修复任务 T-20260424-2e64ba19，worktree=/home/lfr/kernelcode_generate/wt-20260424-main-npu-demo-final-repair-s2，记录文件=agents/codex-multi-agents/log/task_records/2026/17/20260424-main-npu-demo-final-repair-s2.md。最小修复目标只收两项：1）把 spec/dsl/gen_kernel.md 中仍保留的三字段 arch.launch<%b, %t, %s>(@missing_body, ...) 示例统一改成四字段 shared_memory_size 合同；2）把 spec/dsl/ast.md、spec/dsl/mlir_gen.md、spec/operation/arch.md 与 kernel_gen/dsl/ast/parser.py 中仍写作公开或兼容入口的 launch_kernel(callee, block, thread, subthread, shared_memory_size, *args) 口径统一收到 launch_kernel[...] 下标式公开 DSL 入口。`
- 是否已创建修复任务：`是`
- 修复任务创建人：`守护最好的爱莉希雅`
- 另一位架构师补充重点：`本轮修复任务不扩到无关 expectation 或 runtime 链，只收 spec 示例与 parser / 公开 DSL 入口口径统一。`

### 2026-04-24 守护最好的爱莉希雅 终验复核

- 结论：`不通过`
- 执行目录：`主目录先执行 git fetch --prune；因 /home/lfr/kernelcode_generate 存在本地改动与未跟踪 worktree，本轮终验改用最新远端干净 worktree /home/lfr/kernelcode_generate-wt-20260424-main-npu-demo-final-2。`
- 验证基线：`origin/main@e7cde08e869bb3eef9f5de658fb451591b4f92c3；新 worktree detached HEAD 同步到 e7cde08。`
- 合同验收摘要：`本轮只执行与本计划相关的 expectation 合同验收，且全部通过：1）PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/home/lfr/kernelcode_generate-wt-20260424-main-npu-demo-final-2:/home/lfr/kernelcode_generate python3 -m expectation.operation.arch，exit 0；2）... python3 -m expectation.dsl.mlir_gen.dialect.arch，exit 0；3）... python3 -m expectation.pass.outline_device_kernel，exit 0；4）... python3 -m expectation.pass.tuning.launch_kernel_cost_func，exit 0；5）... python3 -m expectation.tools.dsl_run，exit 0；6）... python3 -m expectation.execute_engine.npu_demo.default，exit 0。`
- 最小阻断项或通过摘要：`尽管本轮相关 expectation 已全部通过，但当前仍有一线可执行收口点，因此不能给通过。最小阻断项是旧 launch_kernel 直调用兼容口径仍留在公开文档与实现说明里：spec/operation/arch.md、spec/dsl/ast.md、spec/dsl/mlir_gen.md 仍写“实现当前仍可接受旧直调用 launch_kernel(callee, block, thread, subthread, shared_memory_size, *args) 作为兼容路径”，kernel_gen/dsl/ast/parser.py 的说明也仍保留同样表述。该计划目标既然已收口到 launch_kernel[...] 作为公开 DSL 入口，这组旧兼容表述仍应继续清理。`
- 是否已创建修复任务：`是`
- 修复任务创建人：`守护最好的爱莉希雅`
- 修复任务信息：`已按当前终验阻断项补建唯一修复任务 T-20260424-78a40d80，worktree=/home/lfr/kernelcode_generate/wt-20260424-main-npu-demo-final-repair-s3，记录文件=agents/codex-multi-agents/log/task_records/2026/17/20260424-main-npu-demo-final-repair-s3.md。最小修复目标只收 4 个文件中的旧兼容表述：spec/operation/arch.md、spec/dsl/ast.md、spec/dsl/mlir_gen.md 与 kernel_gen/dsl/ast/parser.py 中仍保留的 launch_kernel(callee, block, thread, subthread, shared_memory_size, *args) 文本，需要统一到 launch_kernel[...] 公开入口；不扩到无关 expectation 或 runtime 链。`

### 2026-04-24 守护最好的爱莉希雅 复验

- 结论：`不通过`
- 执行目录：`/home/lfr/kernelcode_generate-wt-20260424-main-npu-demo-recheck`
- 验证基线：`origin/main@a45d798fa38e69f323f1f55ee4e994fa1f946bee`（主目录已先执行 git fetch --prune，但主目录存在本地删改与未跟踪 worktree，因此本轮改用最新远端干净 worktree）`
- 合同验收摘要：`本轮只执行与本计划相关的 expectation 合同验收，并按最新同步现场复跑重点入口：1）PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/home/lfr/kernelcode_generate-wt-20260424-main-npu-demo-recheck python3 -m expectation.pass.tuning.launch_kernel_cost_func，exit 0；2）... python3 -m expectation.pass.tuning.launch_kernel_cost_func_compute_memory，exit 0；3）... python3 -m expectation.operation.arch，exit 1，报 No module named expectation.operation；4）... python3 -m expectation.dsl.mlir_gen.dialect.arch，exit 1，报 No module named expectation.dsl.mlir_gen；5）... python3 -m expectation.pass.outline_device_kernel，exit 1，报 No module named expectation.pass.outline_device_kernel；6）... python3 -m expectation.execute_engine.npu_demo.default，exit 1，报 No module named expectation.execute_engine；7）... python3 -m expectation.tools.dsl_run，exit 1，报 No module named expectation.tools。`
- 最小阻断项或通过摘要：`当前最小阻断项是：本计划正文点名的相关验收资产在最新同步现场并不齐。虽然 expectation.pass.tuning.launch_kernel_cost_func 及其直接相关入口 expectation.pass.tuning.launch_kernel_cost_func_compute_memory 当前都通过，但 operation.arch、dsl.mlir_gen.dialect.arch、pass.outline_device_kernel、execute_engine.npu_demo.default、tools.dsl_run 这 5 个计划点名入口在最新远端干净 worktree 中均不存在，导致合同验收无法按计划正文落地执行。只要这组点名入口与最新同步现场还未对齐，本轮复验就不能给通过。`
- 是否已创建修复任务：`是`
- 修复任务创建人：`守护最好的爱莉希雅`
- 修复任务信息：`已存在唯一修复任务 T-20260424-4781572d，worktree=/home/lfr/kernelcode_generate/wt-20260424-main-npu-demo-final-repair-s4，记录文件=agents/codex-multi-agents/log/task_records/2026/17/20260424-main-npu-demo-final-repair-s4.md。按本轮最新现场看，后续若继续推进，需要先把计划正文点名的相关验收资产与最新同步现场对齐。`

### 2026-04-24 守护最好的爱莉希雅 复验补充（按用户确认删除口径修正）

- 结论：`不通过`
- 执行目录：`沿用上一轮复验目录 /home/lfr/kernelcode_generate-wt-20260424-main-npu-demo-recheck；本轮补充只修正阻断解释与后续任务边界，不重复扩展无关 expectation。`
- 验证基线：`沿用上一轮复验基线 origin/main@a45d798fa38e69f323f1f55ee4e994fa1f946bee。`
- 合同验收摘要：`上一轮复验中 expectation.pass.tuning.launch_kernel_cost_func 与 expectation.pass.tuning.launch_kernel_cost_func_compute_memory 已通过；operation.arch、dsl.mlir_gen.dialect.arch、pass.outline_device_kernel、execute_engine.npu_demo.default、tools.dsl_run 在最新远端干净 worktree 中不存在。用户已明确确认这组 expectation 资产为主动删除，不再作为产品阻断。`
- 最小阻断项或通过摘要：`当前最小阻断项改为：计划正文中的相关 expectation 清单仍包含用户已主动删除的资产，导致计划正文、复验范围与当前真实保留合同集合不一致。后续应只收计划正文中的相关 expectation 清单与直接关联的实现 / spec / test 说明，使计划完成态、复验范围和当前真实保留合同集合一致；不把用户主动删除的 expectation 继续当作产品失败。`
- 是否已创建修复任务：`是`
- 修复任务创建人：`守护最好的爱莉希雅`
- 修复任务信息：`已按当前修正后的最小阻断项补建唯一修复任务 T-20260424-33224722，worktree=/home/lfr/kernelcode_generate/wt-20260424-main-npu-demo-final-repair-s5，记录文件=agents/codex-multi-agents/log/task_records/2026/17/20260424-main-npu-demo-final-repair-s5.md。该任务只处理计划正文中相关 expectation 资产清单与当前真实保留合同集合不一致的问题，以及直接关联的实现 / spec / test 说明收口；不得改动任何 [immutable-file]，执行记录必须补真实自检与 Diff 反推自测，expectation 只单列为合同验收资产。`

### 2026-04-24 守护最好的爱莉希雅 复验（7c63c3b）

- 结论：`通过`
- 执行目录：`主目录先执行 git fetch --prune；因 /home/lfr/kernelcode_generate 存在本地删改与未跟踪文件，本轮改用最新远端干净 worktree /home/lfr/kernelcode_generate-wt-20260424-main-npu-demo-recheck-2。`
- 验证基线：`origin/main@7c63c3bc18b4d0d69dedc336e2cacdcfcb8bae99；主目录 HEAD 与 origin/main 一致，TODO.md 当前显示本计划为 8/8/0、完成待检查。`
- 合同验收摘要：`本轮按当前正文中“目标 验收资产”与“当前测试与验收资产”只执行当前保留合同集合的 expectation：1）PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/home/lfr/kernelcode_generate-wt-20260424-main-npu-demo-recheck-2 python3 -m expectation.pass.tuning.launch_kernel_cost_func，exit 0，输出 [OK] launch-kernel-cost-func expectation passed；2）PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/home/lfr/kernelcode_generate-wt-20260424-main-npu-demo-recheck-2 python3 -m expectation.pass.tuning.launch_kernel_cost_func_compute_memory，exit 0，输出 [OK] launch-kernel-cost-func compute/memory expectation passed。`
- 最小阻断项或通过摘要：`无。当前保留合同集合只剩 expectation.pass.tuning.launch_kernel_cost_func 与 expectation.pass.tuning.launch_kernel_cost_func_compute_memory，两者在最新干净现场均通过；TODO.md 与 DONE.md 也已对齐到本计划 8/8/0、修复任务 T-20260424-33224722 已完成的状态。按用户确认后的当前保留合同范围，本轮未再发现新的可直接执行改进点。`

### 2026-04-24 大闸蟹 复验（7c63c3b）

- 结论：`不通过`
- 执行目录：`主目录先执行 git fetch --prune；因 /home/lfr/kernelcode_generate 存在本地改动，本轮改用最新远端干净 worktree /home/lfr/kernelcode_generate-wt-20260424-main-npu-demo-recheck-3。`
- 验证基线：`origin/main@7c63c3bc18b4d0d69dedc336e2cacdcfcb8bae99；本轮复验 worktree detached HEAD 同步到 7c63c3b。`
- 合同验收摘要：`本轮只执行正文当前保留的相关 expectation：1）PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/home/lfr/kernelcode_generate-wt-20260424-main-npu-demo-recheck-3 python3 -m expectation.pass.tuning.launch_kernel_cost_func，exit 0；2）PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/home/lfr/kernelcode_generate-wt-20260424-main-npu-demo-recheck-3 python3 -m expectation.pass.tuning.launch_kernel_cost_func_compute_memory，exit 0。`
- 最小阻断项或通过摘要：`当前仍有可直接执行改进点，因此不能给通过。最小阻断项有两处：1）spec/dialect/arch.md 第 56 行的 operation API 映射仍把公开入口写成 launch_kernel(callee, block, thread, subthread, shared_memory_size)，与本计划收口到 launch_kernel[block, thread, subthread, shared_memory_size](callee, *args) 不一致；2）kernel_gen/operation/arch.py 第 927-948 行仍把直调用 launch_kernel(callee, block, thread, subthread, shared_memory_size, *args) 写成 builder 的兼容入口，且第 263 行、第 640 行的功能说明还在用 launch_kernel(...) 描述当前公开语义。既然本计划当前公开 DSL 入口已收成下标式 launch_kernel[...]，这组旧直调用口径仍应继续清理。`
- 是否已创建修复任务：`是`
- 修复任务创建人：`守护最好的爱莉希雅`
- 修复任务信息：`已按本轮最新最小阻断项补建唯一修复任务 T-20260424-3c0b1a41，worktree=/home/lfr/kernelcode_generate/wt-20260424-main-npu-demo-final-repair-s6，记录文件=agents/codex-multi-agents/log/task_records/2026/17/20260424-main-npu-demo-final-repair-s6.md。任务边界只收 spec/dialect/arch.md 与 kernel_gen/operation/arch.py 中剩余的旧直调用 launch_kernel 公开口径，以及它们直接关联的实现 / spec / test 收口；不得改动任何 [immutable-file]；执行记录必须补真实自检与 Diff 反推自测。`

### 2026-04-24 守护最好的爱莉希雅 复验（4983279）

- 结论：`通过`
- 执行目录：`主目录先执行 git fetch --prune；因 /home/lfr/kernelcode_generate 存在本地删改与未跟踪文件，本轮改用最新远端干净 worktree /home/lfr/kernelcode_generate-wt-20260424-main-npu-demo-recheck-4。`
- 验证基线：`origin/main@4983279c54631dcb42fceeca75b0233815621948；主目录 HEAD 与 origin/main 一致，TODO.md 当前显示本计划为 9/9/0、完成待检查，DONE.md 已记录修复任务 T-20260424-3c0b1a41 完成。`
- 合同验收摘要：`本轮只执行正文当前保留的相关 expectation：1）PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/home/lfr/kernelcode_generate-wt-20260424-main-npu-demo-recheck-4 python3 -m expectation.pass.tuning.launch_kernel_cost_func，exit 0，输出 [OK] launch-kernel-cost-func expectation passed；2）PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/home/lfr/kernelcode_generate-wt-20260424-main-npu-demo-recheck-4 python3 -m expectation.pass.tuning.launch_kernel_cost_func_compute_memory，exit 0，输出 [OK] launch-kernel-cost-func compute/memory expectation passed。`
- 最小阻断项或通过摘要：`无。上一轮阻断中的两处旧直调用公开口径已收口：spec/dialect/arch.md 当前 operation API 映射已改为 launch_kernel[block, thread, subthread, shared_memory_size](callee, *args)；kernel_gen/operation/arch.py 当前把直调用 launch_kernel(...) 明确写成失败路径，并在功能说明中收口到下标式公开入口。当前保留合同集合的 expectation 全部通过，TODO/DONE 与计划状态也已对齐，本轮未再发现新的可直接执行改进点。`

### 2026-04-24 大闸蟹 复验（4983279）

- 结论：`通过`
- 执行目录：`主目录先执行 git fetch --prune；因 /home/lfr/kernelcode_generate 存在本地改动，本轮复用最新远端干净 worktree /home/lfr/kernelcode_generate-wt-20260424-main-npu-demo-recheck-4。`
- 验证基线：`origin/main@4983279c54631dcb42fceeca75b0233815621948。`
- 合同验收摘要：`本轮只执行正文当前保留的相关 expectation：1）PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/home/lfr/kernelcode_generate-wt-20260424-main-npu-demo-recheck-4 python3 -m expectation.pass.tuning.launch_kernel_cost_func，exit 0，输出 [OK] launch-kernel-cost-func expectation passed；2）PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/home/lfr/kernelcode_generate-wt-20260424-main-npu-demo-recheck-4 python3 -m expectation.pass.tuning.launch_kernel_cost_func_compute_memory，exit 0，输出 [OK] launch-kernel-cost-func compute/memory expectation passed。`
- 最小阻断项或通过摘要：`无。上一轮复验中点到的旧直调用公开口径已在当前主线收口：spec/dialect/arch.md 的 operation API 映射已统一到 launch_kernel[block, thread, subthread, shared_memory_size](callee, *args)；kernel_gen/operation/arch.py 已把旧直调用 launch_kernel(...) 改成调用边界失败路径，并同步把相关功能说明改成下标式公开入口。当前正文保留的相关 expectation 全部通过，本轮未再发现新的可直接执行改进点。`

## 输入摘要

- 目标：`python3 main.py` 必须走 `npu-demo-lowering`，生成并展示 host 代码和 kernel 代码；host 代码以 CUDA launch 风格调用 `npu_demo::launch<1, 1, 1, 0>(...)`，第四模板参数是 shared memory size。
- 不做什么：不恢复 `only-kernel=true`；不新增 `canonicalize` / `cse` / `fold-canonicalize` pass；不在 main.py 或 gen_kernel 里写 npu_demo 特化旁路；不把折叠能力做成全仓隐式 pass manager 行为。
- 当前痛点：`launch_kernel` DSL / operation / dialect / include runtime 仍以函数调用三元 launch extent 为主，无法表达 `launch_kernel[...]` 与 shared memory size；main.py 输出不是用户期望的 host launch + device kernel 形态；现有 pattern pass 没有统一启用 xdsl folding，重复 symbol/int 值可能残留。
- 完成后用户最想看到的例子：`python3 main.py` 输出 `[HOST SOURCE]` 与 `[KERNEL SOURCE]`，host 中有 `npu_demo::launch<1, 1, 1, 0>(kernel_device, ...)`，device kernel 首参是 `npu_demo::KernelContext& ctx`，并真实编译执行得到与 torch 一致的结果。

## 计划目标

- 将 `launch_kernel` 公开 DSL/operation 入口收口为 `launch_kernel[block, thread, subthread, shared_memory_size](callee, *args)`，并让 `arch.launch` IR 固定携带第四个 shared memory size operand。
- 将 include/API 与 npu_demo runtime launch 源码形态统一为 `launch<block, thread, subthread, shared_memory_size>(callee, args...)`，当前 `npu_demo.txt` 默认 `shared_memory_size=0`。
- 让 `outline-device-kernel` / `attach-arch-information` / `npu-demo-lowering` 默认产生 host wrapper + device kernel，wrapper 内 `arch.launch` 通过 target registry 查询得到当前默认 `1,1,1,0`。
- 让相关 xdsl pattern pass 在自身 rewrite driver 中启用 `GreedyRewritePatternApplier(..., folding_enabled=True, ctx=ctx)`；若某 op 缺少 fold，则在对应 op 或 pass 的 pattern 中补最小折叠逻辑。
- 让 `main.py` 成为最小端到端示例：走 `dsl_run(..., "npu-demo-lowering", EmitCContext(target="npu_demo"))`，展示 lowered IR、host source、kernel source、完整 source、执行结果和 torch 校验。

## 当前基线

- 当前公开合同：`spec/operation/arch.md`、`spec/dsl/ast.md`、`spec/dsl/mlir_gen.md`、`spec/dialect/arch.md` 仍描述函数调用式三元 `launch_kernel(callee, block, thread, subthread, *args)`；`spec/dsl/gen_kernel.md`、`spec/include/api/Arch.md`、`spec/include/npu_demo/npu_demo.md` 仍锁定 `launch<block, thread, subthread>(...)`。
- 当前公开 API：`launch_kernel(callee, block, thread, subthread, *args)`；`ArchLaunchOp(callee, block, thread, subthread, args)`；`npu_demo::launch<block, thread, subthread>(callee, args...)`。
- 当前实现入口：[`kernel_gen/dialect/arch.py`](../../kernel_gen/dialect/arch.py) 的 `ArchLaunchOp` 只有 `block/thread/subthread` operands；[`kernel_gen/operation/arch.py`](../../kernel_gen/operation/arch.py) 的 `_launch_context` 与 `launch_kernel` 只处理三元 extent；[`kernel_gen/passes/outline_device_kernel.py`](../../kernel_gen/passes/outline_device_kernel.py) 只构造三元 `arch.launch`；[`kernel_gen/dsl/gen_kernel.py`](../../kernel_gen/dsl/gen_kernel.py) 发射 `npu_demo::launch<1, 1, 1>(...)`。
- 当前 target 基线：[`spec/target/registry.md`](../../spec/target/registry.md) 已记录 npu_demo 硬件信息里 `block_num=1`、`thread_num=1`、`subthread_num=1`、`sm_memory_size=0`；需要把 launch shared memory size 的默认来源写成 target registry / [`kernel_gen/target/targets/npu_demo.txt`](../../kernel_gen/target/targets/npu_demo.txt)，不得硬编码散落在 pass 或 codegen。
- 当前 xdsl 基础设施：本地 xdsl `GreedyRewritePatternApplier` 已提供 `folding_enabled`，启用后会调用 `Folder(ctx).try_fold(op)`；本轮只使用该能力，不把 xdsl `CanonicalizePass` / `CommonSubexpressionElimination` 加入 pipeline。
- 当前测试与验收资产：当前保留的 expectation 合同资产只剩 [`expectation/pass/tuning/launch_kernel_cost_func`](../../expectation/pass/tuning/launch_kernel_cost_func) 与其直接目录入口 [`expectation/pass/tuning/launch_kernel_cost_func_compute_memory`](../../expectation/pass/tuning/launch_kernel_cost_func_compute_memory)；`operation.arch`、`dsl.mlir_gen.dialect.arch`、`pass.outline_device_kernel`、`execute_engine.npu_demo.default`、`tools.dsl_run` 已按用户确认主动删除，不再作为本计划当前产品阻断。arch operation/dialect、AST、mlir_gen、gen_kernel、outline_device_kernel、dsl_run、include runtime、target registry 与 `main.py` 端到端合同改由对应 spec 与 pytest 维持。

## 合同真源顺序

- `spec/tools/dsl_run.md + spec/pass/pipeline/npu_demo_lowering.md + spec/dsl/gen_kernel.md > test/tools/test_dsl_run.py + test/tools/test_ircheck_runner.py + test/pass/test_pipeline_npu_demo_lowering.py + test/dsl/test_gen_kernel.py > 当前实现`
- `spec/operation/arch.md + spec/dialect/arch.md + spec/dsl/ast.md + spec/dsl/mlir_gen.md + spec/dsl/emit_mlir.md > test/operation/test_operation_arch.py + test/dialect/test_arch_dialect.py + test/dsl/test_ast.py + test/dsl/test_ast_visitor.py + test/dsl/test_mlir_gen.py > 当前实现`
- `expectation/pass/tuning/launch_kernel_cost_func + expectation/pass/tuning/launch_kernel_cost_func_compute_memory > spec/pass/outline_device_kernel.md + spec/pass/tuning/launch_kernel_cost_func.md > test/pass/outline_device_kernel/test_outline_device_kernel.py + test/pass/test_launch_kernel_cost_func.py > 当前实现`
- `spec/include/api/Arch.md + spec/include/npu_demo/npu_demo.md > test/include/api/test_arch.py + test/include/npu_demo/test_public_namespace.py + test/include/npu_demo/test_runtime_launch.py + test/include/npu_demo/test_kernel_context.py > include/api/Arch.h + include/npu_demo/Arch.h`
- `spec/target/registry.md > test/target/test_target_registry.py > kernel_gen/target/targets/npu_demo.txt + kernel_gen/target/registry.py`
- `test/test_main_npu_demo_pipeline.py > main.py > 当前手工运行输出`

## 方案比较与选型

- 不采用方案：保留三元 `arch.launch`，只在 C++ 发射阶段追加 `, 0`。
- 不采用原因：这会让 IR、operation、spec 与 include ABI 分叉；后续成本建模、outline pass、dsl_run 入口选择都无法机械判断 shared memory size。
- 采用方案：把 shared memory size 作为 `launch_kernel[...]` / `arch.launch` / include launch 的正式第四维字段，当前值从 target registry 读取，npu_demo 默认 `0`。
- 维护收益：IR 与源码 ABI 一一对应，后续把 `0` 改成真实 shared memory size 时只需改 target / attach pass，而不是补 codegen 特判。

- 不采用方案：新增 `canonicalize`、`cse` 或本仓 `fold-canonicalize` pass，并插入 `npu-demo-lowering`。
- 不采用原因：用户已确认本轮暂不加 canonicalize/CSE；独立 cleanup pass 会扩大 pipeline 行为面，也容易影响不属于本计划的 pass family。
- 采用方案：只在本轮触达的 xdsl pattern-driven pass 内启用 `GreedyRewritePatternApplier(..., folding_enabled=True, ctx=ctx)`；缺 fold 的 op 补 `fold` hook 或局部 rewrite pattern。
- 维护收益：折叠能力跟随具体 pass 的 pattern 运行，改动影响小；后续需要全局 canonicalize/CSE 时可另立计划。

- 不采用方案：main.py 自己拼接 host/kernel 字符串。
- 不采用原因：会绕开 `gen_kernel` 真实输出，示例可能假通过。
- 采用方案：main.py 只调用正式 `dsl_run + npu-demo-lowering + gen_kernel + execute_engine` 链路，并从真实 source 中展示 host/kernel 区段。
- 维护收益：main.py 与 execute_engine/default 共享同一条正向合同，减少示例与真实运行分叉。

## 公开 API 设计

### DSL / Operation

- 公开入口：`launch_kernel[block, thread, subthread, shared_memory_size](callee, *args)`
- 参数顺序：下标参数为 `block -> thread -> subthread -> shared_memory_size`；调用参数为 `callee -> *args`
- 参数类型：`callee` 为 Python 函数对象或 DSL symbol reference；四个下标 launch 数值为 `int | SymbolDim`，其中 `block/thread/subthread` 静态值必须 `> 0`，`shared_memory_size` 静态值必须 `>= 0`。
- 返回值：`None`

```python
def host(lhs, rhs, out):
    launch_kernel[1, 1, 1, 0](add_body, lhs, rhs, out)
```

### IR

- 公开入口：`arch.launch`
- 文本形态：`arch.launch<%block, %thread, %subthread, %shared_memory_size>(@callee, %arg0, ...) : (...) -> ()`
- 验证规则：`block/thread/subthread/shared_memory_size` 均必须是 `!symbol.int`；前三者静态值必须 `> 0`；第四者静态值必须 `>= 0`。

```mlir
%b = symbol.const 1 : !symbol.int<"1">
%t = symbol.const 1 : !symbol.int<"1">
%s = symbol.const 1 : !symbol.int<"1">
%smem = symbol.const 0 : !symbol.int<"0">
arch.launch<%b, %t, %s, %smem>(@add_body, %lhs, %rhs, %out) : (...) -> ()
```

### Include / Runtime

- 公开入口：`launch<block, thread, subthread, shared_memory_size>(callee, args...)`
- 参数顺序：四个模板参数后接 `callee, args...`
- 返回值：`Status`
- 当前 npu_demo 默认：`block=1, thread=1, subthread=1, shared_memory_size=0`
- 失败边界：模板参数数量必须为四个；`block/thread/subthread` 静态值必须 `> 0`；`shared_memory_size` 静态值必须 `>= 0`；`callee` 必须是可调用 kernel 入口；target 不支持的 launch extent 返回 `StatusCode::kError` 或等价稳定错误，不得静默降级为三字段 launch。

```cpp
Status status = npu_demo::launch<1, 1, 1, 0>(add_body, lhs, rhs, out);
```

### Pattern Folding

- 公开入口：现有 `ModulePass.apply(ctx, module)` 中使用的 xdsl rewrite driver。
- 约束：本轮不注册新 pass 名；不在 pipeline 中加入 `canonicalize`、`cse`、`fold-canonicalize`。
- 实现要求：需要折叠的 pattern pass 使用 `GreedyRewritePatternApplier(patterns, folding_enabled=True, ctx=ctx)` 或等价 xdsl 标准写法；没有 folder 的 op 在对应 dialect 或 pass 内补 `fold` hook / 局部 fold pattern。

```python
applier = GreedyRewritePatternApplier(
    patterns,
    folding_enabled=True,
    ctx=ctx,
)
PatternRewriteWalker(applier, apply_recursively=True).rewrite_module(module)
```

### main.py

- 公开入口：`python3 main.py`
- 参数顺序：无 CLI 参数
- 返回值：成功退出码 `0`
- 输出区段：`[LOWERED IR]`、`[HOST SOURCE]`、`[KERNEL SOURCE]`、`[SOURCE]`、`[EXECUTE]`、`[CHECK]`

```text
[HOST SOURCE]
void add_kernel(...) {
    npu_demo::launch<1, 1, 1, 0>(add_kernel_device, ...);
}

[KERNEL SOURCE]
static void add_kernel_device(npu_demo::KernelContext& ctx, ...) {
    ...
}
```

## 完成态定义

- `launch_kernel[...]`、`ArchLaunchKernelAST`、`ArchLaunchOp`、`mlir_gen`、`outline-device-kernel`、`gen_kernel`、include/api、include/npu_demo 全部使用四字段 launch 合同，第四字段命名为 shared memory size。
- `attach-arch-information` 通过 target registry / `npu_demo.txt` 获取 npu_demo 默认 launch 信息；当前生成 `1,1,1,0`，不得在多个实现点散落硬编码。
- `npu-demo-lowering` 默认仍生成 host wrapper + device kernel；wrapper 中唯一 `arch.launch` 发射为 `npu_demo::launch<1, 1, 1, 0>(...)`。
- 现有 xdsl pattern-driven pass 在必要位置启用 `folding_enabled=True`；重复 `symbol.const` 或可静态折叠的 symbol/int 表达式由 op fold hook 或局部 pattern 收口。
- `npu-demo-lowering` pipeline 不出现新 standalone `canonicalize`、`cse` 或 `fold-canonicalize` pass。
- `main.py` 运行真实编译执行链路，输出 host/kernel 源码区段，并给出与 torch 一致的校验结果。

## 验收设计

- 验收资产：`test/operation/test_operation_arch.py`、`test/dialect/test_arch_dialect.py`
- 覆盖目标：`launch_kernel[...]` 与 `arch.launch` 的 shared memory size 参数、文本打印、解析、非法输入诊断。
- 必过命令：`PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/operation/test_operation_arch.py test/dialect/test_arch_dialect.py`

- 验收资产：`test/dsl/test_ast.py`、`test/dsl/test_ast_visitor.py`、`test/dsl/test_mlir_gen.py`
- 覆盖目标：DSL `launch_kernel[block, thread, subthread, shared_memory_size](callee, *args)` 解析与 lowering 为四字段 `arch.launch`。
- 必过命令：`PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/dsl/test_ast.py test/dsl/test_ast_visitor.py test/dsl/test_mlir_gen.py`

- 验收资产：`test/pass/test_attach_arch_information.py`、`test/pass/outline_device_kernel/test_outline_device_kernel.py`、`test/pass/test_pipeline_npu_demo_lowering.py`
- 覆盖目标：target registry 提供默认 shared memory size，outline pass 生成四字段 `arch.launch`，pipeline 不新增 standalone cleanup pass。
- 必过命令：`PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/pass/test_attach_arch_information.py test/pass/outline_device_kernel/test_outline_device_kernel.py test/pass/test_pipeline_npu_demo_lowering.py`

- 验收资产：`test/dsl/test_gen_kernel.py`、`test/tools/test_dsl_run.py`、`test/tools/test_ircheck_runner.py`
- 覆盖目标：`gen_kernel` 发射 `npu_demo::launch<1, 1, 1, 0>(...)`，`dsl_run` 仍选择唯一 wrapper 并真实执行。
- 必过命令：`PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/dsl/test_gen_kernel.py test/tools/test_dsl_run.py test/tools/test_ircheck_runner.py`

- 验收资产：`test/include/api/test_arch.py`、`test/include/npu_demo/test_public_namespace.py`、`test/include/npu_demo/test_runtime_launch.py`、`test/include/npu_demo/test_kernel_context.py`
- 覆盖目标：include runtime 四模板参数 ABI、KernelContext 注入、shared memory size 非负约束与现有 thread id/thread num 行为。
- 必过命令：`PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/include/api/test_arch.py test/include/npu_demo/test_public_namespace.py test/include/npu_demo/test_runtime_launch.py test/include/npu_demo/test_kernel_context.py`

- 验收资产：`test/target/test_target_registry.py`
- 覆盖目标：`npu_demo.txt` 是默认 launch 信息真源，包含 `block_num=1/thread_num=1/subthread_num=1/sm_memory_size=0` 或等价字段。
- 必过命令：`PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/target/test_target_registry.py`

- 验收资产：`test/test_main_npu_demo_pipeline.py`
- 覆盖目标：`main.py` 输出 host/kernel/source 区段、包含 `npu_demo::launch<1, 1, 1, 0>`、真实执行并通过 torch 校验。
- 必过命令：`PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/test_main_npu_demo_pipeline.py`

- 合同验收：
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 -m expectation.pass.tuning.launch_kernel_cost_func`
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 -m expectation.pass.tuning.launch_kernel_cost_func_compute_memory`
- 终验 expectation：架构师终验、复验或终验修复复核时必须在最新同步现场运行与本轮改动有关的 `expectation` 合同验收；未运行或失败时不得给通过结论。只有用户明确要求全量 `expectation` 时，才按全量执行；环境依赖例外也必须由用户明确确认。
- 旧三字段残留扫描：S1/S3 必须运行并记录 `rg 'launch_kernel\\(|arch\\.launch<%[^>]*, %[^>]*, %[^>]*>|launch<[^,>]+, [^,>]+, [^,>]+>' kernel_gen spec test include expectation -g '*.py' -g '*.md' -g '*.h' -g '*.cpp'`；命中项必须分类为“改写 / 负例保留 / 旧基线说明”，不得留下未解释的正向三字段合同。
- Diff 反推验证：执行人与审查人必须按实际 diff 补跑对应 pytest 或可执行脚本，并在任务日志写明 `Diff 反推自测` / `Diff 反推审查`；`expectation` 合同验收单列，不算 diff 反推测试。

## 阶段拆分

### S1：launch shared memory ABI 与 IR/operation 收口

#### 上下文摘要

- 当前 DSL、operation、arch dialect、include runtime 与 gen_kernel 仍是函数调用式三字段 launch；用户已确认 DSL 入口改为 `launch_kernel[...]`，第四模板参数是 shared memory size，参考 CUDA launch 风格。

#### 阶段目标

- 将 shared memory size 纳入 `launch_kernel[...]`、AST、MLIR lowering、`ArchLaunchOp`、include/API、target 默认信息和相关 spec/test，使仓库内部不再存在函数调用式三字段 launch 正向合同。

#### 非目标

- 不实现动态 shared memory 分配行为。
- 不改变 `KernelContext` 的 thread id/thread num 运行时语义。
- 不处理 canonicalize/CSE/pattern folding。

#### 禁止修改面 / 合同真源

- 禁止修改 `.skills`。
- 禁止修改 `[immutable]` / `[immutable-file]` 内容。
- 合同真源以本计划“合同真源顺序”中 arch operation/dialect/include/target 链路为准。

#### 最小功能闭环

- `launch_kernel[1, 1, 1, 0](add_body, lhs, rhs, out)` 可解析、lowering、打印为四字段 `arch.launch`。
- `ArchLaunchOp` 的 custom syntax、parse、print、verify 全部覆盖 shared memory size。
- include/API 和 include/npu_demo runtime 支持 `launch<1, 1, 1, 0>(callee, args...)`，旧三模板参数正向测试改为四模板参数。
- `npu_demo.txt` 或 target registry 等价配置成为默认 `shared_memory_size=0` 的真源。

#### 执行步骤

1. 先读本计划 S1、全局完成态、相关 arch/include/target spec 与测试。
2. 更新 spec，明确 shared memory size 是 launch 第四字段，静态值必须 `>= 0`。
3. 更新 operation 与 AST/parser/nodes，使 `launch_kernel[...]` 下标调用可解析；operation 层 `launch_kernel` 应变为可下标化 launch builder，`launch_kernel[...]` 返回可调用对象。
4. 更新 `ArchLaunchOp` operand 定义、构造函数、parse/print/verify 和别名 `ArchLaunchKernelOp`。
5. 更新 include/api 与 include/npu_demo 的 `launch` 模板签名，确保 shared memory size 当前传入但不破坏 KernelContext 注入，并写死四模板参数、前三者正数、shared memory size 非负、callee 可调用、target 不支持 extent 的失败边界。
6. 更新 target registry / `npu_demo.txt`，让 attach pass 后续可查询默认 shared memory size。
7. 更新对应 pytest，删除函数调用式三字段正向合同，保留非法下标 arity、非法 callee、负 shared memory size 失败路径。

#### 预期输出

```mlir
arch.launch<%b, %t, %s, %smem>(@add_body, %lhs, %rhs, %out) : (...) -> ()
```

```cpp
Status status = npu_demo::launch<1, 1, 1, 0>(add_body, lhs, rhs, out);
```

#### 验收必过项目

- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/operation/test_operation_arch.py test/dialect/test_arch_dialect.py`
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/dsl/test_ast.py test/dsl/test_ast_visitor.py test/dsl/test_mlir_gen.py`
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/include/api/test_arch.py test/include/npu_demo/test_public_namespace.py test/include/npu_demo/test_runtime_launch.py test/include/npu_demo/test_kernel_context.py`
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/tools/test_ircheck_runner.py`
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/target/test_target_registry.py`
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 -m expectation.pass.tuning.launch_kernel_cost_func`
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 -m expectation.pass.tuning.launch_kernel_cost_func_compute_memory`
- `rg 'launch_kernel\\(|arch\\.launch<%[^>]*, %[^>]*, %[^>]*>|launch<[^,>]+, [^,>]+, [^,>]+>' kernel_gen spec test include expectation -g '*.py' -g '*.md' -g '*.h' -g '*.cpp'`

#### Diff 反推要求

- 若修改 AST/parser，还必须按 diff 反推补跑 `test/dsl/test_ast_nodes.py`、`test/dsl/test_ast_parser.py`、`test/dsl/test_ast_visitor.py` 或相关子集。
- 若修改 include runtime，还必须按 diff 反推补跑对应 C++ 编译运行 pytest。
- 若残留扫描命中旧三字段正向合同，必须在 S1 或 S3 归属范围内同步改写；仅允许旧基线说明或负例中保留，并必须在任务记录说明原因。

#### 记录要求

- `执行前阅读记录：TODO 任务行、计划书 S1、全局完成态/验收设计、相关 spec/test/实现`
- `自检：spec/API 是否仍残留函数调用式三字段 launch；shared memory size 是否全链路命名一致；负值/缺参错误是否覆盖`
- `Diff 反推自测：列出除本阶段必过命令外，按 diff 追加的 pytest 或脚本`

### S2：pattern folding 接入现有 xdsl rewrite pass

#### 上下文摘要

- 用户确认不加 standalone canonicalize/CSE/fold pass；需要利用 xdsl `GreedyRewritePatternApplier` 的 folding 能力。如果缺 fold，则在对应 op 或 pass 内补 pattern。

#### 阶段目标

- 在本轮相关 pattern-driven pass 中启用 xdsl folding，并补齐必要的 op fold hook / 局部 rewrite pattern，减少重复 symbol/int 常量和值。

#### 非目标

- 不注册 `canonicalize`、`cse`、`fold-canonicalize` pass。
- 不把 cleanup 自动加入全局 `PassManager.run()`。
- 不重构未触达的 pass family。

#### 禁止修改面 / 合同真源

- 禁止修改 `.skills`。
- 禁止修改 `[immutable]` / `[immutable-file]` 内容。
- 合同真源：本计划 Pattern Folding 公开 API 设计、`test/pass/test_pipeline_npu_demo_lowering.py`、具体被改 pass 的 pytest。

#### 最小功能闭环

- 相关 pass 的 rewrite driver 明确使用 `folding_enabled=True` 与当前 `ctx`。
- 可静态折叠的 symbol 整数表达式不再无故保留。
- `npu-demo-lowering` 的公开 pass 列表不出现 standalone cleanup pass 名。

#### 执行步骤

1. 先读本计划 S2、S1 记录、xdsl `pattern_rewriter.py` 中 `GreedyRewritePatternApplier` 与 `Folder` 行为。
2. 盘点当前 npu-demo-lowering 直接运行的 pattern-driven pass，优先只改本链路需要的 pass。
3. 对已使用 `GreedyRewritePatternApplier` 的 pass，改为传入 `folding_enabled=True, ctx=ctx`。
4. 对仍手写遍历但本计划必须折叠的局部重写，优先改成单 op pattern；确实不适合时仅补局部 fold pattern，不扩大架构重构。
5. 给 symbol/int 常量与简单符号算术补最小 fold hook 或 pattern，禁止改变动态 SymbolDim 语义。
6. 更新 pytest，锁定“不新增 cleanup pass”和“可折叠表达式经 pass 后被折叠”。

#### 预期输出

```python
applier = GreedyRewritePatternApplier(
    patterns,
    folding_enabled=True,
    ctx=ctx,
)
```

```mlir
%0 = symbol.const 1 : !symbol.int<"1">
%1 = symbol.const 2 : !symbol.int<"2">
%2 = symbol.add %0, %1 : !symbol.int<"1">, !symbol.int<"2"> -> !symbol.int<"3">
```

经相关 pass 后可折叠为等价 `symbol.const 3` 或直接复用已折叠 value。

#### 验收必过项目

- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/pass/test_pipeline_npu_demo_lowering.py`
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/dialect/test_symbol_dialect.py`
- 由执行人按实际改动补跑对应 pass pytest，例如 `test/pass/test_symbol_loop_hoist.py`、`test/pass/outline_device_kernel/test_outline_device_kernel.py`、nn lowering family 相关测试。

#### Diff 反推要求

- 修改哪个 pass，就必须补跑该 pass 的 pytest 或最小可执行脚本。
- 修改哪个 dialect fold hook，就必须补跑对应 dialect pytest。

#### 记录要求

- `执行前阅读记录：TODO 任务行、计划书 S2、S1 记录、xdsl folding 源码、相关 pass/dialect 测试`
- `自检：是否误加 standalone cleanup pass；是否误折叠动态符号；是否所有 GreedyRewritePatternApplier 都传入 ctx`
- `Diff 反推自测：列出按 diff 补跑的 pass/dialect 测试`

### S3：main.py host/kernel 输出与 npu_demo 运行链路收口

#### 上下文摘要

- S1 提供四字段 launch ABI，S2 提供 pattern folding；本阶段收口用户可见的 `python3 main.py` 行为和 dsl_run/gen_kernel 正向链路。

#### 阶段目标

- 让 `main.py` 默认使用 `npu-demo-lowering`，展示 host source 与 kernel source，并通过真实 compile/execute 路径运行；`gen_kernel` 与 `dsl_run` 统一消费四字段 `arch.launch`。

#### 非目标

- 不在 main.py 里实现独立 emitter。
- 不恢复 kernel-only 目录语义或 `only-kernel=true`。
- 不把 shared memory size 从 `0` 扩展成动态运行时参数。

#### 禁止修改面 / 合同真源

- 禁止修改 `.skills`。
- 禁止修改 `[immutable]` / `[immutable-file]` 内容。
- 合同真源：`spec/dsl/gen_kernel.md`、`spec/tools/dsl_run.md`、`test/tools/test_dsl_run.py`、`test/tools/test_ircheck_runner.py`、`test/pass/test_pipeline_npu_demo_lowering.py`、`test/dsl/test_gen_kernel.py`、`test/test_main_npu_demo_pipeline.py`。

#### 最小功能闭环

- `gen_kernel` 对唯一 wrapper + device body module 发射 `npu_demo::launch<1, 1, 1, 0>(body, args...)`。
- `dsl_run` 仍按唯一 `arch.launch` wrapper 选择入口，禁止回退到首个普通函数、只 lower、只出源码或 dry-run。
- `main.py` 打印 `[HOST SOURCE]`、`[KERNEL SOURCE]`、`[SOURCE]`、`[EXECUTE]`、`[CHECK]`，并给出成功校验。
- S3 必须复查旧三字段 C++ launch 文本残留，重点包含 `test/dsl/test_gen_kernel.py`、`test/include/npu_demo/test_public_namespace.py`、`test/tools/test_ircheck_runner.py`、`test/tools/test_dsl_run.py`。

#### 执行步骤

1. 先读本计划 S3、S1/S2 记录、`main.py`、`gen_kernel`、`dsl_run` 与当前保留的 tuning expectation 入口。
2. 更新 `gen_kernel` 对 `ArchLaunchOp` 的 extent 读取和错误文本，要求四字段 launch。
3. 更新 `dsl_run` 中 wrapper/device 识别逻辑，只消费新的四字段 `arch.launch`，不新增旧桥。
4. 更新 `main.py` 示例，固定使用 `dsl_run(..., "npu-demo-lowering", EmitCContext(target="npu_demo"))`。
5. 给 `main.py` 添加 pytest，使用 subprocess 运行，断言 host/kernel 区段、`launch<1, 1, 1, 0>`、真实执行与校验成功。
6. 按用户要求继续用 npu_demo pipeline，不允许 main.py 绕过 pass 或直接调用 kernel-only 形式。

#### 预期输出

```text
[HOST SOURCE]
void add_kernel(...) {
    npu_demo::launch<1, 1, 1, 0>(add_kernel_device, ...);
}
```

```text
[KERNEL SOURCE]
static void add_kernel_device(npu_demo::KernelContext& ctx, ...) {
    ...
}
```

#### 验收必过项目

- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/dsl/test_gen_kernel.py test/tools/test_dsl_run.py`
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/include/npu_demo/test_public_namespace.py test/tools/test_ircheck_runner.py`
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/test_main_npu_demo_pipeline.py`
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 main.py`
- `rg 'npu_demo::launch<[^,>]+, [^,>]+, [^,>]+>|launch<[^,>]+, [^,>]+, [^,>]+>\\(' kernel_gen test include spec expectation -g '*.py' -g '*.md' -g '*.h' -g '*.cpp'`

#### Diff 反推要求

- 修改 `gen_kernel` 必须补跑相关 gen_kernel pytest。
- 修改 `dsl_run` 必须补跑 tools pytest 与至少一条 execute_engine expectation。
- 修改 `main.py` 必须补跑 subprocess pytest 和手工 `python3 main.py`。
- 修改 C++ launch 发射或相关测试时，必须补跑旧三字段残留扫描并在记录中解释所有命中项。

#### 记录要求

- `执行前阅读记录：TODO 任务行、计划书 S3、S1/S2 记录、相关 spec/test/实现、expectation 入口`
- `自检：main.py 是否走正式 pipeline；是否还有三字段 launch 文本；是否真实 compile/execute`
- `Diff 反推自测：列出除阶段必过命令外追加的 pytest 或脚本`

## 待确认项

- 当前无待确认项。用户已确认：第四模板参数是 shared memory size；本轮不新增 standalone fold/canonicalize/CSE pass；折叠走 xdsl `GreedyRewritePatternApplier`，缺 fold 时补对应 op/pass pattern；canonicalize 和 CSE 暂不加入。

## 用户确认与协同约束

- 用户确认状态：`已确认`
- 已确认事项：
  - `npu_demo::launch<1, 1, 1, 0>` 的第四模板参数是 shared memory size，参考 CUDA launch 风格。
  - DSL/operation 入口是 `launch_kernel[block, thread, subthread, shared_memory_size](callee, *args)`，不是新增 `launch` helper，也不是 `launch_kernel(callee, block, ...)` 函数调用。
  - 需要修改 launch kernel 的 IR 与 operation，不接受只在 C++ 发射阶段追加 `0`。
  - 不是加 pass，而是使用 xdsl `GreedyRewritePatternApplier` 自动触发 fold。
  - 如果没有 fold，则在对应 pass/op 中实现 fold pattern。
  - `canonicalize` 和 `cse` 暂时不加。
  - `main.py` 需要生成 host 代码和 kernel 代码，并按 launch kernel 形式运行。
- 协同约束：用户已要求通过 `codex-multi-agents-tmux.sh -talk` 询问其他角色，并让对方用脚本回复；进入任务创建前必须整合已收到的 `-talk` 回复。若出现冲突观点，必须先向用户确认，不得擅自裁决。

## 风险与回滚

- 风险：`launch_kernel[...]` 与四字段 `arch.launch` 会触发大量旧三字段测试失败。
- 控制：S1 明确把旧函数调用式三字段正向合同改完，禁止只修局部测试；失败文本必须统一指向下标 arity、shared memory size 缺失或非法。

- 风险：启用 xdsl folding 后误折叠动态 SymbolDim。
- 控制：S2 只折叠静态整数语义确定的表达式；动态 symbol 名称或 runtime 形状不做数值化。

- 风险：main.py host/kernel 区段切分依赖源码文本。
- 控制：优先从 gen_kernel 已知 wrapper/body 函数名与 `arch.launch` 关系识别；不得手写假源码。

## 自检

- `spec/API` 自检：计划已把 launch 公开 API 固定为 `launch_kernel[...]` 与四字段 `arch.launch`，第四字段 shared memory size；函数调用式三字段 launch 只作为旧基线出现。
- `任务边界` 自检：S1 收 ABI/IR/operation，S2 收 pattern folding，S3 收 main.py/codegen/runtime 展示；没有纯 spec 空任务。
- `风险` 自检：最大风险为旧三字段测试残留与动态 symbol 误折叠，均已写入阶段验证。
- `方案取舍` 自检：明确排除 standalone canonicalize/CSE/fold pass、C++ 发射阶段特判、main.py 手写源码。
- `待确认` 自检：用户本轮已补齐关键决策，当前无阻塞待确认项。
