# npu-demo memory-plan auto_pad matmul alloc hoist 计划书 Final

## 文档信息

- 计划用途：规划在 `npu-demo-lowering` 的三段 `memory-plan` 阶段启用既有 `auto_pad` 能力，并保证 matmul kernel 中静态 tile 与动态 effective tile 产生的 `dma.alloc` / `dma.free` 都能在可证明安全时提出到最外层 supported `symbol.for` 之外。
- 当前状态：Feynman / Gibbs 两路 subagent strict review R2 通过，`守护最好的爱莉希雅` 守护最终检验通过；无阻断、无最小需改项、无待用户确认项；允许进入管理员下发唯一计划级 `execute`；尚未创建计划级 `execute`。
- 用户确认来源：2026-06-06 用户原始需求：“出一个新计划书。就是 memory plan 使能 auto pad，目的是 matmul 的 kernel，动态静态的 alloc 都能提出到最外面。”
- 目标 `spec`：
  - [`spec/pass/pipeline/npu_demo_lowering.md`](../../spec/pass/pipeline/npu_demo_lowering.md)
  - [`spec/pass/memory_plan.md`](../../spec/pass/memory_plan.md)
  - [`spec/pass/symbol_buffer_hoist.md`](../../spec/pass/symbol_buffer_hoist.md)（仅当 execute 为 matmul 外提补齐既有公开能力边界时同步）
- 目标 `API`：
  - 不新增、不删除、不重命名公开 API。
  - 既有 `MemoryPlanPass(insert_free: bool = False, fold: bool = True, reuse: bool = False, auto_pad: bool = False)` 保持签名与 registry option 不变。
  - 既有 `build_npu_demo_lowering_pipeline(options: dict[str, str] | None = None) -> PassManager` 保持签名、pipeline 名称与 options 入口不变。
  - 公开行为变更：`npu-demo-lowering` 固定构造的三段 `MemoryPlanPass` 从 `auto_pad=False` 改为 `auto_pad=True`；用户原始需求即为确认来源。
- 目标 `test`：
  - [`test/passes/test_memory_plan.py`](../../test/passes/test_memory_plan.py)
  - [`test/passes/test_symbol_buffer_hoist.py`](../../test/passes/test_symbol_buffer_hoist.py)
  - [`test/passes/test_symbol_hoist_pipeline.py`](../../test/passes/test_symbol_hoist_pipeline.py)
  - [`test/passes/pipeline/test_npu_demo_lowering.py`](../../test/passes/pipeline/test_npu_demo_lowering.py)
  - [`test/kernel/test_matmul_symbolic_memory_genkernel.py`](../../test/kernel/test_matmul_symbolic_memory_genkernel.py)
- 当前必过 `expectation` 合同验收：
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 -m expectation.pass.memory_plan.auto_pad`
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 -m expectation.pass.symbol_buffer_hoist.dynamic_matmul_alloc`
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 -m expectation.pass.pipeline.npu_demo_lowering`
- 目标 `功能实现`：
  - [`kernel_gen/pipeline/npu_demo_lowering.py`](../../kernel_gen/pipeline/npu_demo_lowering.py)
  - [`kernel_gen/passes/hoist/symbol_buffer_hoist.py`](../../kernel_gen/passes/hoist/symbol_buffer_hoist.py)（仅当既有 hoist 对 auto_pad logical alias 的 pipeline 组合不达标时）
  - [`kernel_gen/passes/memory_plan.py`](../../kernel_gen/passes/memory_plan.py)（仅当既有 `auto_pad` 在 pipeline 真实 matmul 输入上暴露已在 spec 中承诺的缺口时）
- `expectation/` 授权：本计划默认不新增、不修改 `expectation/`；只读取和运行上述现有合同资产。若 execute 发现必须新增或修改 `expectation/` 才能闭环，必须先回到用户 / 架构师确认，不得自行改动。
- 计划书边界：subagent 收敛、守护最终检验和计划书入档验收角色可按流程回填本计划记录；计划级 `execute` 不得修改本计划书正文。

## 计划级任务

- 计划级任务目标：在 `npu-demo-lowering` 固定启用 `MemoryPlanPass(auto_pad=True)`，同步 spec / 文件级说明 / pytest，并让 matmul static 与 dynamic tile 场景在 pre-pool typed IR 中只保留最外层 supported loop 外的 alloc/free，memory-pool 后不残留 `dma.alloc` / `dma.free`。
- 任务类型：`execute`。
- 固定流转：`execute -> review -> archive_acceptance/计划书入档验收 -> merge/归档`。
- 失败接续：`review` 不通过回 `execute`；`archive_acceptance` 不通过也回 `execute`；不得另建独立 `refactor` 阶段绕过计划级任务。
- 当前下发前置：已完成 subagent strict review 收敛与守护最终检验；用户待决策项为无；允许管理员下发唯一计划级 `execute`。

| 计划任务 | 任务类型 | worktree | 记录文件 |
| --- | --- | --- | --- |
| `npu-demo-memory-plan-auto-pad-matmul-hoist` | `execute` | 管理员下发的新独立 worktree | `agents/codex-multi-agents/log/task_records/2026/23/20260606-npu-demo-memory-plan-auto-pad-matmul-hoist.md` |

## 迭代审阅记录

### 收敛轮次 1：subagent strict review

- 审阅对象：Draft 1 全文。
- 输入标准包：根 `AGENTS.md`、当前角色 prompt、`agents/standard/计划书标准.md`、`agents/standard/审查规范.md`、`agents/standard/实现文件规范.md`、`agents/standard/测试文件约定.md`、`agents/standard/任务记录约定.md`、Draft 1 全文、当前用户确认来源、禁止修改面、必过验收命令和本轮严格通过口径。
- 严格通过口径：无未确认公开 API 变更；无未授权 `expectation/` 改动；任务目标可直接执行；matmul static / dynamic alloc 最外提完成态可验证；pytest 与 expectation 分开；小任务卡短口径与详细字段一致；仍有可执行可读性、可维护性、测试有效性或边界完整性返工项则不得通过。
- 审阅任务：
  - `Feynman / 019e9848-7e41-7da1-8d60-f3be334191e6`：最小需改项。
  - `Gibbs / 019e9848-ed7c-7a92-97d2-22dd946f4515`：最小需改项。
- 发现问题：
  1. S1-S4 小任务卡未在卡内逐卡单列三条 `expectation` 合同验收命令，容易把 expectation 混入 diff 反推测试或漏跑。
  2. S1-S4 禁止修改面未显式列出本计划书路径；execute 可能误把计划正文纳入任务 diff。
  3. S2 允许在既有 spec 范围内修复 `memory_plan.py` / `symbol_buffer_hoist.py`，但未明确触达实现文件时必须同步文件级说明、`API 列表`、函数注释、spec/test。
- 主线处理：
  - 采纳 1：S1-S4 均新增 `合同验收（单列，不计入 Diff 反推测试）`，逐条列出三条 exact expectation 命令；`验收必过项目` 只列 pytest / scripts / text gate。
  - 采纳 2：S1-S4 禁止修改面和完成态增加本计划书路径，注明仅计划阶段 / 入档验收角色可按流程回填记录。
  - 采纳 3：S2 完成态、执行步骤和记录要求增加实现文件规范同步要求。
- 状态：已按 Draft 1-R1 修订，并经收敛轮次 2 返工复核通过。

### 收敛轮次 2：subagent strict review 返工复核

- 审阅对象：Draft 1-R1 全文。
- 输入标准包：根 `AGENTS.md`、当前角色 prompt、相关 `agents/standard/**`、Draft 1-R1 全文、R1 问题与本轮收口摘要、当前用户确认来源、禁止修改面、必过验收命令和本轮严格通过口径。
- 严格通过口径：确认 R1 所有已发起审阅任务提出的问题均已收口；无新增阻断、无最小需改项、无待用户确认项；计划可进入守护最终检验。
- 审阅任务：
  - `Feynman / 019e9848-7e41-7da1-8d60-f3be334191e6`：R2 通过。
  - `Gibbs / 019e9848-ed7c-7a92-97d2-22dd946f4515`：R2 通过。
- 发现问题：无新增阻断；无新增最小需改项；无待用户确认项。
- 主线处理：R2 无需继续修订；保留 Draft 1-R1 的三项主线修订。
- 状态：已收口。

### subagent 收敛结论

- 已发起或计划要求的审阅任务：
  - Feynman R1：最小需改项；R2：通过。
  - Gibbs R1：最小需改项；R2：通过。
- 收敛结论：两路 R2 均确认 R1 问题已收口，且无新增阻断、无最小需改项、无待用户确认项；可进入守护最终检验。
- 遗留项：无。

### 守护最终检验

- 检验对象：`守护最好的爱莉希雅`。
- 检验范围：subagent 收敛结论、公开 API 用户确认、`expectation/` 授权、禁止修改面、验收命令、小任务卡和待确认项。
- 必过门禁：所有已发起或计划要求的 subagent strict review 均无阻断、无最小需改项、无待确认项；用户待决策项为无；计划不越权修改 `expectation/`。
- 守护验证：
  - 已读：`AGENTS.md`、本计划 Final、`agents/standard/计划书标准.md`、`agents/standard/审查规范.md`、`agents/standard/实现文件规范.md`、`agents/standard/测试文件约定.md`、`agents/standard/任务记录约定.md`。
  - 已核对：Feynman / Gibbs R2 均通过；公开 API 不新增 / 不删除 / 不重命名；固定启用既有 `auto_pad=True` 的公开行为有用户原始需求作为确认来源；`expectation/` 默认不新增 / 不修改；S1-S4 小任务卡自包含且单列合同验收；待确认项为无。
  - 合同验收：`python3 -B -m expectation.pass.memory_plan.auto_pad` 通过；`python3 -B -m expectation.pass.symbol_buffer_hoist.dynamic_matmul_alloc` 通过；`python3 -B -m expectation.pass.pipeline.npu_demo_lowering` 通过。
  - 敏感目录核对：`git diff` 与 `git status` 对 `.skills expectation agents/standard AGENTS.md TODO.md DONE.md` 及本计划书路径无输出。
  - 未执行项：pytest / demo scripts / text gate 属于计划级 `execute` 实施后验收，本次只读守护检验未执行。
- 结论：通过；允许进入管理员下发唯一计划级 `execute`。
- 最小阻断项：无。

## 计划书入档验收 / 复验 / 修复复核记录

- 结论人：待计划级 `execute` 完成后由计划书入档验收角色填写。
- 结论：待填写。
- 验证基线：待填写。
- 执行目录：待填写。
- 同步结果：待填写。
- 合同验收摘要：待填写。
- 最小阻断项或通过摘要：待填写。

## 计划目标

- 在 `npu-demo-lowering` 三段 fixed `memory-plan` 阶段启用既有 `auto_pad`，不新增 pipeline option。
- 保持 `memory-plan` 先生成 padded backing + logical `dma.reinterpret` alias，再由既有 `symbol-hoist-pipeline` / `symbol-buffer-hoist` fixed-point 外提安全 alloc/free。
- 对 matmul kernel 的三类关键场景建立 pipeline 级验收：
  - static input + static tile：静态常量 tail 产生的 logical alloc 能经 auto_pad / hoist 收口。
  - static input + dynamic tile：runtime tile 符号 alloc 可在 tile 参数支配时提出到最外层。
  - dynamic input + dynamic tile：`H/K/W` 与 `TILE_H/TILE_W/TILE_K` 共同存在时，padded backing alloc 提出到最外层，`kernel.matmul` 继续消费 logical alias。
- 保持 memory-pool 前的 typed IR 仍可供 `producer-consumer-analysis` 读取，memory-pool 后最终 IR 不残留 `dma.alloc` / `dma.free`。

## 当前基线

- 当前 `spec/pass/memory_plan.md` 已公开 `auto_pad`：`MemoryPlanPass(..., auto_pad: bool = False)` 与 registry `auto-pad=true` 均已存在，且 `auto_pad` 在 lifecycle 分析前执行。
- 当前 `spec/pass/memory_plan.md` 和 `spec/pass/pipeline/npu_demo_lowering.md` 均明确 `npu-demo-lowering` 固定使用 `auto_pad=False`，并把“不默认开启 auto_pad”写成目标 / 非目标口径。
- 当前 `kernel_gen/pipeline/npu_demo_lowering.py` 三处均为 `MemoryPlanPass(insert_free=True, reuse=True, fold=False)`，未传入 `auto_pad=True`。
- 当前 `spec/pass/symbol_buffer_hoist.md` 已写入 padded backing + logical alias 术语，并承诺 `dma.reinterpret` alias 可参与 fixed-point 外提，`kernel.*` consumer 不改写到 padded backing。
- 当前 `expectation/pass/memory_plan/auto_pad.py` 已覆盖 dynamic tail alloc、已有 free redirect、unknown no-op 与 dynamic matmul logical consumer。
- 当前 `expectation/pass/symbol_buffer_hoist/dynamic_matmul_alloc.py` 已覆盖 dynamic matmul acc/tmp/lhs/rhs loop-local scratch 外提，但它是 standalone `symbol-buffer-hoist` 合同，不是 `npu-demo-lowering` 全 pipeline 合同。
- 当前 `test/passes/pipeline/test_npu_demo_lowering.py` 只记录 `MemoryPlanPass` 的 `insert_free/reuse/fold`，未记录 `auto_pad`；dump 测试覆盖 static / dynamic matmul 与 memory-pool，但未要求 auto_pad backing / logical alias 在 pipeline 中最外提。
- 当前基线验证已执行：
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/passes/test_memory_plan.py test/passes/pipeline/test_npu_demo_lowering.py` -> `42 passed, 1 warning`
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 -m expectation.pass.memory_plan.auto_pad` -> 通过
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 -m expectation.pass.symbol_buffer_hoist.dynamic_matmul_alloc` -> 通过
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 -m expectation.pass.pipeline.npu_demo_lowering` -> 通过

## 方案比较与选型

### 方案 A：重写 memory_plan auto_pad 算法

- 内容：重新设计 padded backing 推导、matmul consumer alias、free redirect 与生命周期。
- 缺点：仓库已有公开 spec、pytest 与 expectation，当前目标只是接入 pipeline；重写会扩大风险并重复已有合同。
- 结论：不采用。

### 方案 B：给 `npu-demo-lowering` 新增 `auto-pad` pipeline option

- 内容：保持默认 false，新增 `build_npu_demo_lowering_pipeline({"auto-pad": "true"})`。
- 缺点：新增公开工具 / pipeline 参数，用户需求是“使能 auto pad”，不是新增可选开关；公开 API 变更会扩大确认与兼容边界。
- 结论：不采用；本计划不新增 pipeline option。

### 方案 C：固定启用既有 `MemoryPlanPass(auto_pad=True)` 并补 pipeline 级验收

- 内容：三段 `MemoryPlanPass(insert_free=True, reuse=True, fold=False)` 全部改为 `MemoryPlanPass(insert_free=True, reuse=True, fold=False, auto_pad=True)`，同步 pipeline / memory_plan spec 与文件级说明；用 pytest / dump / 现有 expectation 验收 matmul static 与 dynamic alloc 最外提。
- 优点：最小改动接入已有公开能力；不新增公开 API；与用户目标直接一致；三段都开启可覆盖 lower-nn、transform-apply、kernel-decompose 后不同来源的 alloc。
- 风险：auto_pad 生成的 `dma.reinterpret` logical alias 可能暴露既有 `symbol-buffer-hoist` 对 pipeline 真实 matmul IR 的边界缺口。
- 风险处理：若执行中发现缺口，只在现有 `spec/pass/symbol_buffer_hoist.md` 已承诺的 padded backing / logical alias / dynamic matmul 范围内修复，不新增公开 API；若需要扩大公开语义或改 expectation，暂停并回用户 / 架构师确认。
- 结论：采用。

## 公开 API 设计

- 用户确认来源：2026-06-06 用户要求 `memory plan` 使能 `auto pad`，用于 matmul kernel，并使动态 / 静态 alloc 提到最外面。
- 不新增 API：
  - `build_npu_demo_lowering_pipeline(options: dict[str, str] | None = None) -> PassManager` 保持不变。
  - `MemoryPlanPass(insert_free: bool = False, fold: bool = True, reuse: bool = False, auto_pad: bool = False)` 保持不变。
  - `MemoryPlanPass.from_options(options: dict[str, str]) -> MemoryPlanPass` 保持不变。
  - `SymbolBufferHoistPass(fold: bool = True)` 与 `SymbolHoistPipelinePass(fold: bool = True)` 保持不变。
- 公开行为变更：
  - `npu-demo-lowering` 的三处 `memory-plan` 固定参数变更为 `insert_free=True, reuse=True, fold=False, auto_pad=True`。
  - `npu-demo-lowering` 仍不接受 `auto-pad`、`auto_pad`、`only-kernel` 或其它新增 options。
  - 稳定错误文本不变；如果实现发现必须改变公开错误语义，必须先形成待确认项并取得用户确认。

## 完成态定义

- `spec/pass/pipeline/npu_demo_lowering.md` 与 `spec/pass/memory_plan.md` 不再残留 `npu-demo-lowering` 默认 `auto_pad=False` 或“不默认开启 auto_pad”的当前口径。
- `kernel_gen/pipeline/npu_demo_lowering.py` 文件级说明、函数注释和三处 pass 构造均明确 `auto_pad=True`。
- `test/passes/pipeline/test_npu_demo_lowering.py` 顺序测试记录并断言 `auto_pad=True`，且未知 option 测试仍证明没有新增 pipeline option。
- matmul pipeline dump 验收证明：
  - memory-pool 前 typed stage 中，matmul scratch backing alloc/free 位于对应 pattern/device 函数最外层 supported `symbol.for` 外。
  - `kernel.matmul` / `kernel.binary_elewise` / `dma.deslice` 的循环语义位置不被提前。
  - dynamic effective tile 场景中 `kernel.matmul` 继续消费 logical `dma.reinterpret` alias，不直接消费 padded backing。
  - memory-pool 后最终 module 不残留 `dma.alloc` / `dma.free`。
- 三个 matmul demo 脚本仍通过真实 lowering / source / execution 链路：
  - `kernel/matmul/inputs_static_tile_static.py`
  - `kernel/matmul/inputs_static_tile_dynamic.py`
  - `kernel/matmul/inputs_dynamic_tile_dynamic.py`
- 候选 diff 中 `expectation/`、`.skills/`、`agents/standard/`、`AGENTS.md`、`TODO.md`、`DONE.md` 无改动；计划级 `execute` 不修改 [`ARCHITECTURE/plan/npu_demo_memory_plan_auto_pad_matmul_hoist.md`](../../ARCHITECTURE/plan/npu_demo_memory_plan_auto_pad_matmul_hoist.md)。
- 若 execute 触达 `kernel_gen/passes/memory_plan.py` 或 `kernel_gen/passes/hoist/symbol_buffer_hoist.py`，对应文件级 `功能说明 / API 列表 / 使用示例 / 关联文件`、相关函数注释、spec 与 pytest 必须同步。

## 验收设计

- pytest / 脚本：
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/passes/test_memory_plan.py test/passes/test_symbol_buffer_hoist.py test/passes/test_symbol_hoist_pipeline.py test/passes/pipeline/test_npu_demo_lowering.py`
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/kernel/test_matmul_symbolic_memory_genkernel.py`
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 kernel/matmul/inputs_static_tile_static.py`
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 kernel/matmul/inputs_static_tile_dynamic.py`
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 kernel/matmul/inputs_dynamic_tile_dynamic.py`
- 当前必过 expectation 合同验收：
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 -m expectation.pass.memory_plan.auto_pad`
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 -m expectation.pass.symbol_buffer_hoist.dynamic_matmul_alloc`
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 -m expectation.pass.pipeline.npu_demo_lowering`
- 文本 / 敏感目录门禁：
  - `rg -n "auto_pad=False|auto-pad=false|不默认开启.*auto_pad|MemoryPlanPass\\(insert_free=True, reuse=True, fold=False\\)" spec/pass/memory_plan.md spec/pass/pipeline/npu_demo_lowering.md kernel_gen/pipeline/npu_demo_lowering.py test/passes/pipeline/test_npu_demo_lowering.py`
  - `git diff -- .skills expectation agents/standard AGENTS.md TODO.md DONE.md ARCHITECTURE/plan/npu_demo_memory_plan_auto_pad_matmul_hoist.md`
  - `git status --short --untracked-files=all -- .skills expectation agents/standard AGENTS.md TODO.md DONE.md ARCHITECTURE/plan/npu_demo_memory_plan_auto_pad_matmul_hoist.md`
  - execute 前后记录 `sha256sum ARCHITECTURE/plan/npu_demo_memory_plan_auto_pad_matmul_hoist.md`，确认计划级 `execute` 未改计划书正文。
- Diff 反推要求：执行人与审查人必须按实际 diff 补充测试；`expectation` 单列为合同验收，不计入 diff 反推测试。

## 计划内小任务

### S1. 同步 auto_pad pipeline 公开合同

- 为什么做：当前 spec 明确写 `npu-demo-lowering` 默认 `auto_pad=False`，与用户要求相反。
- 做什么：更新 `memory_plan` 与 `npu-demo-lowering` spec，把三段 fixed `MemoryPlanPass` 参数改成 `auto_pad=True`，并定义 matmul alloc 最外提完成态。
- 不做什么：不新增 pipeline option，不修改 `expectation/`，不改变 `MemoryPlanPass` 公开签名或错误语义。
- 怎么验收：运行文本扫描确认 `npu-demo-lowering` 默认 `auto_pad=False` 旧口径清零，并确认公开顺序仍是三段 `memory-plan -> symbol-hoist-pipeline -> cse -> canonicalize`。
- 卡住问谁：公开 API、pipeline option 或 expectation 授权需要变化时问用户；spec 与验收口径冲突时问架构师。
- 上下文摘要：`memory-plan` 的 auto_pad 已有公开 API 和 expectation，但 pipeline spec 把它显式关掉。
- 小任务目标：把 `npu-demo-lowering` 的公开合同改为三段固定启用 `auto_pad=True`，且不引入新公开入口。
- 非目标：不调整 `default-lowering`、`cuda_sm86-lowering`、`multi-buffer` 或 matmul DSL API。
- 模块范围：`spec/pass/memory_plan.md`、`spec/pass/pipeline/npu_demo_lowering.md`，必要时同步 `spec/pass/symbol_buffer_hoist.md` 中 matmul auto_pad 外提描述。
- 禁止修改面：`expectation/`、`.skills/`、`agents/standard/`、`AGENTS.md`、`TODO.md`、`DONE.md`、[`ARCHITECTURE/plan/npu_demo_memory_plan_auto_pad_matmul_hoist.md`](../../ARCHITECTURE/plan/npu_demo_memory_plan_auto_pad_matmul_hoist.md)（计划阶段 / 入档验收角色按流程回填记录除外）。
- 合同真源：用户需求 > 目标 spec > pytest > 当前必过 expectation > 当前实现。
- 最小功能闭环：公开文档说明三段 memory-plan 均为 `auto_pad=True`，并定义 matmul static / dynamic alloc 外提边界。
- 执行步骤：
  1. 将 `spec/pass/pipeline/npu_demo_lowering.md` 中三处 `MemoryPlanPass(... auto_pad=False)` 改为 `auto_pad=True`，同步术语、目标、注意事项和测试矩阵。
  2. 将 `spec/pass/memory_plan.md` 中关于 `npu-demo-lowering` 固定调用与非目标的 `auto_pad=False` 旧口径改为 `auto_pad=True`。
  3. 若实现实际修复触达 `symbol-buffer-hoist` 语义边界，同步 `spec/pass/symbol_buffer_hoist.md` 中 padded backing / logical alias / matmul alloc 外提描述。
- 验收必过项目：文本扫描旧口径；`PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/passes/test_memory_plan.py test/passes/pipeline/test_npu_demo_lowering.py`。
- 合同验收（单列，不计入 Diff 反推测试）：
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 -m expectation.pass.memory_plan.auto_pad`
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 -m expectation.pass.symbol_buffer_hoist.dynamic_matmul_alloc`
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 -m expectation.pass.pipeline.npu_demo_lowering`
- 记录要求：任务记录写清公开 API 未新增、旧口径清理结果和是否触达 `symbol-buffer-hoist` spec。

### S2. 接入 npu-demo pipeline auto_pad

- 为什么做：实现当前三段 `MemoryPlanPass` 未传入 `auto_pad=True`，即使 pass 本身支持也不会在 pipeline 中生效。
- 做什么：把 `kernel_gen/pipeline/npu_demo_lowering.py` 三处 `MemoryPlanPass` 固定构造改为 `auto_pad=True`，同步文件级说明和函数注释；如 pipeline 真实 matmul 仍不能外提，在既有公开语义范围内修复 `memory_plan` 或 `symbol-buffer-hoist`，并同步被触达实现文件的文件级说明、`API 列表`、函数注释、spec 与 pytest。
- 不做什么：不新增 wrapper helper，不新增 compatibility branch，不新增公开 option，不调用跨文件非公开 helper。
- 怎么验收：pipeline 顺序测试记录 `memory-plan:True:True:False:True` 或等价标签；未知 option 仍失败；matmul dump 中 pre-pool alloc/free 外提且 memory-pool 后无 alloc/free。
- 卡住问谁：需要扩大公开 API、错误文本或 expectation 合同时问用户；只属于既有 spec 内实现缺口时由 execute 收口。
- 上下文摘要：pipeline 有三段 memory-plan，分别服务 lower-nn 后、transform-apply 后、kernel-decompose 后的 alloc 生命周期；只开一段可能遗漏后续新生成 alloc。
- 小任务目标：让 `npu-demo-lowering` 三段 memory-plan 都实际执行 `auto_pad`，并保持后续 producer / memory-pool 顺序不变。
- 非目标：不改变 `MemoryPoolPass`、`ProducerConsumerAnalysisPass`、`KernelAggregatePass`、`KernelDecomposePass` 的公开顺序。
- 模块范围：`kernel_gen/pipeline/npu_demo_lowering.py`；必要时限于 `kernel_gen/passes/memory_plan.py` 与 `kernel_gen/passes/hoist/symbol_buffer_hoist.py` 的既有 spec 能力修复。
- 禁止修改面：`expectation/`、`.skills/`、`agents/standard/`、`AGENTS.md`、`TODO.md`、`DONE.md`、[`ARCHITECTURE/plan/npu_demo_memory_plan_auto_pad_matmul_hoist.md`](../../ARCHITECTURE/plan/npu_demo_memory_plan_auto_pad_matmul_hoist.md)（计划阶段 / 入档验收角色按流程回填记录除外）。
- 合同真源：用户需求 > `spec/pass/pipeline/npu_demo_lowering.md` > `spec/pass/memory_plan.md` > pytest > expectation。
- 最小功能闭环：构造 pipeline 时三段 `MemoryPlanPass` 的 `auto_pad` 属性为 `True`，且 pipeline 运行后 verifier 通过。
- 执行步骤：
  1. 修改三处 `MemoryPlanPass(insert_free=True, reuse=True, fold=False)` 为显式 `auto_pad=True`。
  2. 同步 `kernel_gen/pipeline/npu_demo_lowering.py` 文件级说明与 `build_npu_demo_lowering_pipeline(...)` 函数注释中的 pass 顺序文本。
  3. 运行并观察 `test_npu_demo_lowering_pipeline_pass_order`，更新记录 helper 与断言覆盖 `auto_pad`。
  4. 若真实 matmul dump 显示 alloc/free 仍滞留在内层 loop，先判断是否属于已写入 `spec/pass/symbol_buffer_hoist.md` 的 padded backing / logical alias / dynamic matmul 能力；属于则修复实现与对应 pytest，不属于则暂停并回用户 / 架构师确认。
  5. 若触达 `kernel_gen/passes/memory_plan.py` 或 `kernel_gen/passes/hoist/symbol_buffer_hoist.py`，同步对应文件级 `功能说明 / API 列表 / 使用示例 / 关联文件`、相关函数注释、spec 与 pytest。
- 验收必过项目：`PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/passes/test_memory_plan.py test/passes/test_symbol_buffer_hoist.py test/passes/test_symbol_hoist_pipeline.py test/passes/pipeline/test_npu_demo_lowering.py`；三条 matmul demo 脚本。
- 合同验收（单列，不计入 Diff 反推测试）：
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 -m expectation.pass.memory_plan.auto_pad`
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 -m expectation.pass.symbol_buffer_hoist.dynamic_matmul_alloc`
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 -m expectation.pass.pipeline.npu_demo_lowering`
- 记录要求：任务记录写清三段 memory-plan 位置、是否修改 hoist / memory_plan、被触达实现文件的文件级说明 / API 列表 / 函数注释同步情况、是否存在公开 API 或 expectation 授权变化。

### S3. 补齐 matmul static / dynamic 外提测试

- 为什么做：现有 pipeline 测试未证明 auto_pad 在 npu-demo matmul kernel 的组合链路中生效，也未断言 `kernel.matmul` 继续消费 logical alias。
- 做什么：更新 `test/passes/pipeline/test_npu_demo_lowering.py`，新增或强化 dump 断言，覆盖 static/static、static/dynamic、dynamic/dynamic matmul 的 pre-pool typed IR 与 post-pool final IR。
- 不做什么：不通过私有 helper 绕过公开 API，不直接调用 pass 内部 helper，不把 expectation 当成 diff 反推测试。
- 怎么验收：pytest 能在 `auto_pad=False` 或 alloc/free 留在内层 loop 时失败；能在 `kernel.matmul` 误读 padded backing 时失败；三个 matmul demo 脚本通过。
- 卡住问谁：测试需要新增或修改 `expectation/` 时问用户 / 架构师；测试输入形态与用户“动态静态”理解冲突时问用户。
- 上下文摘要：用户目标落在 matmul kernel，而不是单 pass leaf；必须在 pipeline 真实输入上锁住组合行为。
- 小任务目标：让 pipeline pytest 直接证明 matmul alloc 最外提与 logical alias consumer 语义。
- 非目标：不把所有 kernel family 或全量 expectation 纳入当前必过门禁。
- 模块范围：`test/passes/pipeline/test_npu_demo_lowering.py`、必要时 `test/passes/test_symbol_buffer_hoist.py` 或 `test/passes/test_memory_plan.py`。
- 禁止修改面：`expectation/`、`.skills/`、`agents/standard/`、`AGENTS.md`、`TODO.md`、`DONE.md`、[`ARCHITECTURE/plan/npu_demo_memory_plan_auto_pad_matmul_hoist.md`](../../ARCHITECTURE/plan/npu_demo_memory_plan_auto_pad_matmul_hoist.md)（计划阶段 / 入档验收角色按流程回填记录除外）。
- 合同真源：`spec/pass/pipeline/npu_demo_lowering.md` > pytest dump 断言 > 现有 expectation > 当前实现。
- 最小功能闭环：pipeline dump 测试能定位第三段 `symbol-hoist-pipeline` 或 `producer-consumer-analysis`，断言 backing alloc 位于 outermost supported loop 前、free 位于 loop 后、核心 compute / copy op 留在循环语义位置。
- 执行步骤：
  1. 扩展 `MemoryPlanPass` 记录 helper，断言每段 `auto_pad=True`。
  2. 在现有 static dump 测试中增加最外层 alloc/free 与 post-pool no alloc/free 断言。
  3. 新增或强化 dynamic dump 测试，检查 padded backing `dma.alloc`、logical `dma.reinterpret`、`kernel.matmul(%logical, %logical, %logical)` 与禁止 `kernel.matmul(%backing, ...)`。
  4. 运行三条 matmul demo 脚本，确认真实 lowering / source / execution 链路仍通过。
- 验收必过项目：`PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/passes/pipeline/test_npu_demo_lowering.py`、`PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/kernel/test_matmul_symbolic_memory_genkernel.py`、三条 matmul demo 脚本。
- 合同验收（单列，不计入 Diff 反推测试）：
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 -m expectation.pass.memory_plan.auto_pad`
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 -m expectation.pass.symbol_buffer_hoist.dynamic_matmul_alloc`
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 -m expectation.pass.pipeline.npu_demo_lowering`
- 记录要求：任务记录写清每个新增断言锁定的行为、错误实现会如何失败、未覆盖范围。

### S4. 执行验收与敏感边界自检

- 为什么做：本计划触达公开 pipeline 行为，必须确认 spec、实现、pytest、现有 expectation 和真实 matmul kernel 链路一致。
- 做什么：按验收设计运行 pytest、脚本、expectation 与文本门禁，补齐任务记录的执行前阅读、自检、Diff 反推自测、减法检查和敏感目录核对。
- 不做什么：不跳过失败项，不把 expectation 失败归因给“旧合同”而不记录证据，不修改主仓任务状态文件。
- 怎么验收：所有必过命令成功；敏感目录门禁无输出；任务记录包含 diff 反推测试与自检。
- 卡住问谁：命令失败且涉及合同冲突时问架构师；需要用户取舍或公开 API 变化时问用户；流程状态问管理员。
- 上下文摘要：开启 auto_pad 可能影响 memory-pool 前后的 IR 形态，必须用真实链路验证。
- 小任务目标：完成计划内实现、测试和验收闭环，形成可 review 的任务记录。
- 非目标：不运行全量 `expectation.pass` 或全量仓库测试，除非 review / 架构师追加要求。
- 模块范围：任务实际 diff 触达模块与本计划验收命令。
- 禁止修改面：`expectation/`、`.skills/`、`agents/standard/`、`AGENTS.md`、`TODO.md`、`DONE.md`、[`ARCHITECTURE/plan/npu_demo_memory_plan_auto_pad_matmul_hoist.md`](../../ARCHITECTURE/plan/npu_demo_memory_plan_auto_pad_matmul_hoist.md)（计划阶段 / 入档验收角色按流程回填记录除外）。
- 合同真源：计划正文 > spec > pytest / scripts > expectation > 当前实现。
- 最小功能闭环：执行记录证明 npu-demo pipeline auto_pad 已启用、matmul alloc 外提已验收、敏感目录未越权。
- 执行步骤：
  1. 运行本计划“验收设计”中的 pytest / script / expectation / 文本门禁。
  2. 用 `git diff --stat` 与 `git status --short --untracked-files=all` 核对实际改动范围。
  3. 在任务记录中写清执行前阅读、最小功能闭环、Diff 反推自测、合同验收、减法检查、自检和剩余风险。
- 验收必过项目：本计划“验收设计”的 pytest / 脚本与文本 / 敏感目录门禁；如因环境失败，记录复现命令、失败摘要、是否与本轮 diff 相关和残余风险。
- 合同验收（单列，不计入 Diff 反推测试）：
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 -m expectation.pass.memory_plan.auto_pad`
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 -m expectation.pass.symbol_buffer_hoist.dynamic_matmul_alloc`
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 -m expectation.pass.pipeline.npu_demo_lowering`
- 记录要求：记录文件为本计划级任务指定路径；不得只在会话中保留验证结论。

## 计划自检与返工口径

- 自检：
  - 公开 API：无新增 / 删除 / 重命名；固定 pipeline 行为变更有用户确认来源。
  - `expectation/`：默认不修改，只运行现有 leaf；若需要变更必须暂停确认。
  - 小任务卡：每张卡均包含为什么做、做什么、不做什么、怎么验收、卡住问谁。
  - 验收资产：pytest / scripts 与 expectation 分开，expectation 不计入 diff 反推测试。
  - 禁止修改面：显式列出 `expectation/`、`.skills/`、`agents/standard/`、`AGENTS.md`、`TODO.md`、`DONE.md`。
  - 可维护性：优先接入既有公开能力；仅在真实 matmul pipeline 暴露既有 spec 缺口时才修复 pass。
- 返工口径：只要仍有影响公开 API 确认、expectation 授权、matmul 外提可验证性、测试有效性、可读性或维护边界的可执行项，就回到计划修订或 execute 返工，不得下发 / 通过。

## 待确认项

- 无当前待确认项。
- 若 execute 或 review 发现以下任一情况，必须新增待确认项并暂停：
  - 需要新增、删除或修改公开 API / pipeline option / 稳定错误文本。
  - 需要新增或修改 `expectation/` 合同资产。
  - 用户“动态静态的 alloc”需扩展到本计划三类 matmul demo之外的 kernel 或 pass。

## 用户确认与协同约束

- 用户确认来源：2026-06-06 用户要求为 `memory plan` 使能 `auto pad` 出新计划书，目标是 matmul kernel 的动态 / 静态 alloc 能提出到最外面。
- 用户已确认事项：
  - 启用 `memory-plan` 的 `auto_pad`。
  - 目标聚焦 matmul kernel。
  - 完成态关注动态 / 静态 alloc 最外提。
- 待用户确认项：无。
- `迭代审阅记录`：见本计划“迭代审阅记录”；Feynman / Gibbs R2 均通过，收敛结论为无阻断、无最小需改项、无待确认项。
- 守护最终检验：`守护最好的爱莉希雅` 已通过，允许进入管理员下发唯一计划级 `execute`。
