# alloc_producer_init_edge.md

## 文档信息

- 状态：Draft 6 已按用户最新口径将 `dma.alloc -> dma.make_ring` ring 场景改为由 `dma.make_ring` 承接 init producer event；Round 7 strict review、守护复验与用户最终确认下发均已闭合，管理员已创建唯一计划级 execute `T-20260620-e3ed07d4`，当前进入计划级 `archive_acceptance` 入档验收。
- 用户原始诉求：`参考 /home/lfr/kernelcode_generate/plan/2 按照计划书流程推进`
- 临时草稿来源：`plan/2`
- 当前核对结论：
  - `plan/2` 中的 `sdnn_kenrel_gen_dsl/...` 路径在当前 `/home/lfr/kernelcode_generate` 工作区不存在。
  - 已扩展到 `/home/lfr` 下 `maxdepth=4/5` 只读搜索，仍未找到 `sdnn_kenrel_gen_dsl` / `sdnn_kernel_gen_dsl` 目录，也未找到 `core_assign.py`、`event_schedule.py`、`sdnn4_lowering.py`、`dma1d.py`。
  - 当前工作区存在根目录版 `ProducerConsumerAnalysisPass`：`spec/pass/producer_consumer_analysis.md`、`kernel_gen/passes/producer_consumer_analysis.py`、`test/passes/test_producer_consumer_analysis.py`。
  - 当前工作区没有 `SdnnCoreAssignPass`、`SdnnEventSchedulePass`、`sdnn4_lowering.py` 或 `kernel/basic/dma1d.py` 对应路径。
- 目标 `spec`：
  - 已确认：当前仓库根目录 `spec/pass/producer_consumer_analysis.md`。
  - 已确认：当前仓库根目录 `spec/pass/pipeline/npu_demo_lowering.md` 只需核对 `producer-consumer-analysis` 位置不退化；不新增 pipeline API。
- 目标 `API`：
  - `ProducerConsumerAnalysisPass(fold: bool = True)`、`ProducerConsumerAnalysisPass.from_options(options: dict[str, str]) -> ProducerConsumerAnalysisPass`、`ProducerConsumerAnalysisPass.apply(ctx: Context, module: ModuleOp) -> None` 公开签名不变。
  - registry pass name `producer-consumer-analysis` 不变。
- 目标 `test`：
  - 已确认：`test/passes/test_producer_consumer_analysis.py`。
  - 已确认：必要时补 `test/passes/pipeline/test_npu_demo_lowering.py` 中 producer-consumer / ring / multi-buffer 不退化覆盖。
- 目标 `验收资产`：
  - 当前主仓本地 ignored / untracked 合同来源：`expectation/pass/producer_consumer_analysis/**`；`expectation/` 默认不进入远程仓库，不作为 normal git diff 资产。
  - 用户于 2026-06-16 明确授权“添加对应的 expectation，作为验证”；本轮架构侧仅在本地 `expectation/pass/producer_consumer_analysis` 下新增 / 更新合同资产。
  - Draft 6 授权范围：
    - 更新 `expectation/pass/producer_consumer_analysis/__main__.py` 聚合说明。
    - 新增 `expectation/pass/producer_consumer_analysis/alloc_first_touch.py`。
    - 新增并按用户最新口径修订 `expectation/pass/producer_consumer_analysis/ring_backing_init_alias.py`，ring 场景由 `dma.make_ring` 写 `productor`，backing `dma.alloc` 不写 event attr。
  - Draft 6 当前 hash：
    - `__main__.py` sha256 `4399778cd2731c8f07121a0fee8a9a87870b68b89896d0449753704c65fc6f09`
    - `alloc_first_touch.py` sha256 `0a69d4ba92573355eb55cf11fc5e3c93aeab671271cdf5f6ced72fe0a6086802`
    - `ring_backing_init_alias.py` sha256 `3c0a557d1ae1d9c70a290c923641a17ce629cf1cd5d126642608bd12a8c1469f`
  - 架构侧物化自检：`PYTHONDONTWRITEBYTECODE=1 python3 -m py_compile expectation/pass/producer_consumer_analysis/__main__.py expectation/pass/producer_consumer_analysis/alloc_first_touch.py expectation/pass/producer_consumer_analysis/ring_backing_init_alias.py` 通过。
  - 当前未实现基线运行新增 leaf 会失败，失败点正是本计划要由 execute 收口的合同门禁：`alloc_first_touch` 当前找不到 `dma.slice {consumer=[0], productor=[1]}`；`ring_backing_init_alias` 当前找不到 `dma.make_ring {productor=[0]}`。
  - Draft 6 后 execute / review / archive_acceptance / merge / 管理员仍不得修改、新建、移动、删除或重命名 `expectation/`；只能读取、运行、引用和记录。
  - 任务记录必须写清 expectation import 来源、关键 leaf 名称、hash / manifest、scope 外空 diff 与合同验收结果；若发现本体疑似缺口，暂停回架构裁定，不得由执行链直接修 expectation。
- 目标 `功能实现`：
  - `kernel_gen/passes/producer_consumer_analysis.py`。

## 计划级任务

- 流转：`execute -> review -> archive_acceptance -> merge/归档`
- 失败接续：`review` 不通过回 `execute`；`archive_acceptance` 不通过也回 `execute`。
- 当前 Draft 6 已按用户确认收窄到当前仓库根目录方案，并按用户授权补充 / 修订本地 expectation 合同；Round 7 strict review、守护复验与用户最终确认下发均已闭合，管理员已创建唯一计划级 execute。
- 计划归档目标：`agents/codex-multi-agents/log/task_records/done_plan/2026/25/alloc_producer_init_edge.md`

| 计划任务 | 任务类型 | worktree | 记录文件 |
| --- | --- | --- | --- |
| `alloc-producer-init-edge` | `execute` | `/home/lfr/kernelcode_generate/wt-20260620-alloc-producer-init-edge` | `agents/codex-multi-agents/log/task_records/2026/25/20260620-alloc-producer-init-edge.md` |

## 迭代审阅记录

### Draft 0：草案迁移与现场核对

- 审阅对象：大闸蟹主线自查；尚未发起 subagent strict review。
- 输入标准包：根 `AGENTS.md`、大闸蟹 prompt、`agents/standard/计划书标准.md`、`agents/standard/计划书模板.md`、`agents/standard/expectation任务规则.md`、`plan/2`、当前仓库 `spec/pass/producer_consumer_analysis.md`、`kernel_gen/passes/producer_consumer_analysis.py`、`test/passes/test_producer_consumer_analysis.py`。
- 严格通过口径：路径不存在、目标工作区不清、公开 API / expectation 授权未确认时不得进入 subagent strict review 或下发。
- 发现问题：
  - `plan/2` 的核心 SDNN 路径 `sdnn_kenrel_gen_dsl/...` 在当前工作区不存在。
  - `/home/lfr` 下扩展只读搜索也未找到 `sdnn_kenrel_gen_dsl` 或 `sdnn_kernel_gen_dsl` 目录，也未找到 `core_assign.py`、`event_schedule.py`、`sdnn4_lowering.py`、`dma1d.py`。
  - `plan/2` 同时描述 third_party `ProducerConsumerAnalysisPass` 与 first-party SDNN `core_assign/event_schedule/dma1d`，但当前仓库只能核对到前者。
  - `plan/2` 中 Q2 / Q3 仍是待确认项：if 分支 first touch 是否共享 event、`driver.inline INIT_EVENT` 是否仅保留手写/未来后端能力。
- 主线处理：先生成正式 Draft 0，列出目标工作区与方案范围待确认；不请求守护最终检验，不通知管理员创建 execute。
- 状态：已由 Draft 1 按用户确认收口。

### Draft 1：用户确认当前仓库根目录方案

- 审阅对象：大闸蟹主线修订；尚未发起 subagent strict review。
- 输入标准包：Draft 0 全文、用户确认消息、当前仓库 `ProducerConsumerAnalysisPass` spec / implementation / pytest、`agents/standard/计划书标准.md`、`agents/standard/expectation任务规则.md`。
- 用户确认：
  - C0=A：目标工作区选择当前仓库根目录，只做公共 `ProducerConsumerAnalysisPass` / npu-demo 相关合同。
  - `if_branch_*` first-touch 新策略不属于本项目考虑事项；若 ALLOC first-touch 被现有控制流分类命中，只复用现有 `if_branch_*` 规则。
  - `driver.inline INIT_EVENT` 与 SDNN event schedule 不属于本项目考虑事项；本计划不修改 SDNN、driver inline、EmitC 或外部 `sdnn_kenrel_gen_dsl` 路径。
- 主线处理：
  - 删除外部 SDNN 工作区作为当前目标范围。
  - 删除 `driver.inline INIT_EVENT` 相关待确认项和任务范围。
  - 将计划内任务收口为当前仓库 `ProducerConsumerAnalysisPass` 的 alloc first-touch、ring backing init-only alias、spec / pytest / expectation 只读验收。
- 状态：已发起 Round 1 subagent strict review；Round 1-A / Round 1-B 均不通过，已由 Draft 2 主线修订处理。

### Round 1：Codex subagent strict review（Draft 1）

- 审阅对象：`ARCHITECTURE/plan/alloc_producer_init_edge.md` Draft 1。
- 输入标准包：根 `AGENTS.md`、大闸蟹 prompt、`agents/standard/计划书标准.md`、`agents/standard/计划书模板.md`、`agents/standard/expectation任务规则.md`、`agents/standard/实现文件规范.md`、`agents/standard/审查规范.md`、Draft 1 全文、用户 C0=A 与“if 分支 / driver.inline 不属于本项目考虑事项”确认、禁止修改面、必过验收命令、当前 staged 证据、unrelated staged / unstaged 文件隔离说明。
- 严格通过口径：仍存在技术边界不清、可执行任务卡不精确、验收命令或 expectation 口径不足以直接下发时，不通过；不得以“执行时再判断”替代计划收口。
- Round 1-A：Beauvoir，流程 / expectation / 计划可执行性审阅。
  - 结论：不通过。
  - 发现问题：
    1. Draft 1 将 `expectation/pass/producer_consumer_analysis/**` 写成“主仓只读合同资产”，但现场 `git ls-files --stage -- expectation/pass/producer_consumer_analysis` 无输出，且 `git check-ignore` 命中 `.gitignore:21:expectation`；应改为主仓本地 ignored / untracked 只读合同来源。
    2. S1-S3 未明确要求修改 `kernel_gen/passes/producer_consumer_analysis.py` 时同步文件级说明 / `API 列表` 和改动函数注释。
    3. S1 示例中 `%slot` 未定义，示例不能作为执行人可验证输入。
  - 影响：管理员和执行链可能误判 expectation 授权状态；实现文件规范可能遗漏；示例无法直接推导预期。
  - Draft 2 主线处理：改写 expectation 来源与权限口径；新增通用实现文件说明同步规则；修正 S1 示例为定义完整的 alloc first WRITE touch 片段。
  - 遗留项：无用户待确认项；需进入 Round 2 复审。
- Round 1-B：Lovelace，技术 / 验收 / 回归审阅。
  - 结论：不通过。
  - 发现问题：
    1. ALLOC first-touch 实现边界不够精确；若直接把 `_collect_consumer_edges` 从 READ 扩为 READ / WRITE，可能把普通 WRITE candidate 也误扩成 WRITE consumer。
    2. ring backing init-only alias 缺少防污染负断言；`kernel.matmul` 不得消费 backing alloc init event，ring-aware 分类 attr 不得被主 `productor` / `consumer` 替代，`make_ring/current_ring/advance_ring/reinterpret` 不得写 event。
    3. 验收矩阵不够自包含；S1/S2 没有具体测试名，pipeline `-k "producer_consumer or ring or multi_buffer"` 过宽，expectation 未写预期输出和关键 leaf 合同。
  - 影响：execute 可能扩大普通 WRITE 语义或误污染 ring dataflow，review 难以用机械断言发现。
  - Draft 2 主线处理：明确 candidate kind 保留、仅 ALLOC 使用 READ ∪ WRITE touch roots、普通 WRITE 仍只连 READ consumer、按 `op_order` 每个 init root 只取第一条 touch、alias-only op 不算 touch；补 S2/S3 负断言、精确测试名和 expectation leaf 预期。
  - 遗留项：无用户待确认项；需进入 Round 2 复审。

### Round 2：Codex subagent strict review（Draft 2）

- 审阅对象：`ARCHITECTURE/plan/alloc_producer_init_edge.md` Draft 2。
- 输入标准包：根 `AGENTS.md`、大闸蟹 prompt、`agents/standard/计划书标准.md`、`agents/standard/计划书模板.md`、`agents/standard/expectation任务规则.md`、`agents/standard/实现文件规范.md`、`agents/standard/审查规范.md`、staged Draft 2 全文 / indexed diff、Round 1-A/B 问题与 Draft 2 主线处理、用户确认来源、禁止修改面、必过验收命令、unrelated staged / unstaged 文件隔离说明。
- 严格通过口径：Round 1 问题必须闭合；若精确验收命令、建议测试名或任务卡仍不自洽，则不通过。
- Round 2-A：Beauvoir，流程 / expectation / 任务卡可执行性复审。
  - 结论：不通过。
  - 发现问题：S1 `-k "alloc_first_touch"` 与建议测试名不完全匹配，S2 `-k "ring_backing_init_alias"` 与建议测试名不完全匹配；落地时 focused 命令可能只覆盖部分新增测试。
  - 影响：execute / review 可能误以为 focused 验收已覆盖完整新增行为。
  - Draft 3 主线处理：统一建议新增测试名，使 S1 所有新增测试名包含 `alloc_first_touch`，S2 所有新增测试名包含 `ring_backing_init_alias`。
  - 遗留项：无用户待确认项；需进入 Round 3 复审。
- Round 2-B：Lovelace，技术 / 验收 / 回归复审。
  - 结论：不通过。
  - 发现问题：与 Round 2-A 一致，focused `-k` token 与建议新增测试名不自洽；`alloc_first_write`、`alloc_first_read`、`write_candidate_still` 不会被 `alloc_first_touch` 覆盖，`ring_backing_alloc_first_slot_write`、`ring_backing_current_advance` 不会被 `ring_backing_init_alias` 覆盖。
  - 影响：计划强调精确 pytest，但当前 focused 命令不能机械选择完整新增用例。
  - Draft 3 主线处理：统一建议新增测试名 token，不改变技术方案、公开 API、expectation 授权、禁止修改面或验收资产。
  - 遗留项：无用户待确认项；需进入 Round 3 复审。

### Round 3：Codex subagent strict review（Draft 3）

- 审阅对象：`ARCHITECTURE/plan/alloc_producer_init_edge.md` Draft 3。
- 输入标准包：根 `AGENTS.md`、大闸蟹 prompt、`agents/standard/计划书标准.md`、`agents/standard/计划书模板.md`、`agents/standard/expectation任务规则.md`、`agents/standard/实现文件规范.md`、`agents/standard/审查规范.md`、staged Draft 3 全文 / indexed diff、Round 1/2 问题与 Draft 3 主线处理、用户确认来源、禁止修改面、必过验收命令、unrelated staged / unstaged 文件隔离说明。
- 严格通过口径：Round 1/2 问题必须闭合；若仍存在 focused pytest token 与建议测试名不自洽、公开 API / expectation 授权风险、任务卡不可执行或验收不自包含问题，则不通过。
- Round 3-A：Beauvoir，流程 / expectation / 任务卡可执行性复审。
  - 结论：通过。
  - 阻断项：无。
  - 最小需改项：无。
  - 待确认项：无。
  - 关键证据：staged blob `4cfd1e8e4a294c0d6f9d4c0307d5f43680bb0c74`，staged sha256 `f1c57894e7adf031529f9c1f9b7b5752ebad3c1b6b967717dd6b511cf6ba0f1e`；Round 1-A/B 与 Round 2-A/B 已闭合；`expectation/pass/producer_consumer_analysis/**` 仍为主仓本地 ignored / untracked 只读来源；unrelated staged / unstaged 现场已隔离。
- Round 3-B：Lovelace，技术 / 验收 / 回归复审。
  - 结论：通过。
  - 阻断项：无。
  - 最小需改项：无。
  - 待确认项：无。
  - 关键证据：staged blob `4cfd1e8e4a294c0d6f9d4c0307d5f43680bb0c74`，staged sha256 `f1c57894e7adf031529f9c1f9b7b5752ebad3c1b6b967717dd6b511cf6ba0f1e`；S1 建议测试名均包含 `alloc_first_touch`，S2 建议测试名均包含 `ring_backing_init_alias`，focused `-k` token 与建议测试名自洽；无新增公开 API 或 expectation 授权待确认。

### Draft 4：用户反馈预期改用 IR 表示

- 触发来源：2026-06-16 用户反馈“预期也用 ir 表示比较好”。
- 主线处理：
  - S1 `示例 / 预期` 增加最小预期 IR attr 形态，用 `dma.alloc {productor = [0]}`、首个 WRITE touch `dma.slice {consumer = [0], productor = [1]}`、后续 `dma.copy {consumer = [1]}` 表达 init edge 与普通 data edge 的区别。
  - S2 `示例 / 预期` 增加 ring backing init-only alias 的预期 IR attr 形态，用 backing alloc 上的 `productor`、首个 slot WRITE 上的 `consumer/productor`、后续 reader 上的普通 `consumer`，并明确 `dma.make_ring` / `dma.current_ring` / `dma.reinterpret` 不带 event attr。
  - 保留文字说明，补充“event id 仅以最小函数遍历顺序为例，测试应断言关系和禁止项”。
- 范围声明：本轮只改计划预期表达和流程状态，不改技术方案、公开 API、expectation 授权、禁止修改面、任务卡范围、验收命令或计划级 execute 草案。
- 状态：writeback-only subagent strict review 已通过；旧 staged blob `2ed198fe6bf54d33b8385dbcefe371c3d88d1049` 的守护请求已由守护确认暂停并作废；最新 staged 候选已重新通过守护最终检验。

### Round 4：Codex subagent writeback-only strict review（Draft 4）

- 审阅对象：`ARCHITECTURE/plan/alloc_producer_init_edge.md` Draft 4。
- 输入标准包：根 `AGENTS.md`、大闸蟹 prompt、`agents/standard/计划书标准.md`、`agents/standard/计划书模板.md`、`agents/standard/expectation任务规则.md`、`agents/standard/实现文件规范.md`、`agents/standard/审查规范.md`、staged Draft 4 全文、用户“预期也用 IR 表示”反馈、旧候选作废回执、新候选 blob / sha256、禁止修改面、必过验收命令、unrelated staged / unstaged 文件隔离说明。
- 严格通过口径：本轮只复核 S1 / S2 `示例 / 预期` 改为 IR attr 表达和流程状态 writeback；若仍存在 IR 预期不自洽、旧候选状态混用、公开 API / expectation 授权风险、任务卡不可执行或需要用户确认的事项，则不通过。
- Round 4-A：Popper，流程 / API / expectation / 任务卡可执行性 writeback-only 复核。
  - 结论：通过。
  - 阻断项：无。
  - 最小需改项：无。
  - 待确认项：无。
  - 关键证据：复核候选 blob `456954e2c6195edd00f7923fe22ae18a6dfc171c`，sha256 `e70b75dd1f51ef9d3514b6a8925d4f611de1b1a887d35fc90e3def734ae6bf8c`；Draft 4 相对 Draft 3 只涉及流程状态、Round 3 记录、Draft 4 writeback 状态和 S1 / S2 `示例 / 预期` IR attr 表达；未改变公开 API、expectation 授权、禁止修改面、任务范围、验收命令或 execute 草案。
  - IR 预期核对：S1 明确 `dma.alloc {productor = [0]}`、首个 WRITE touch `{consumer = [0], productor = [1]}`、后续 reader `{consumer = [1]}`，并说明测试断言关系和只消费一次 init event；S2 明确 backing alloc init producer、首个 slot WRITE init consumer / data producer、后续 reader 只消费 data event，并要求 alias-only / cursor-only op 无 event attr。
- Round 4-B：Averroes，技术 / IR 预期 / 验收闭环 writeback-only 复核。
  - 结论：通过。
  - 阻断项：无。
  - 最小需改项：无。
  - 待确认项：无。
  - 关键证据：只读复核候选 blob `456954e2c6195edd00f7923fe22ae18a6dfc171c`，sha256 与 `e70b75dd1f51ef9d3514b6a8925d4f611de1b1a887d35fc90e3def734ae6bf8c` 一致；S1 / S2 预期 IR 表达技术关系正确；测试名、验收命令、API、expectation 授权、任务范围、`if_branch_*` 复用现有规则和 `driver.inline` / SDNN / EmitC 非目标边界均未改变。
  - 过程备注：Averroes 隔离环境提示该路径 index 可见性与主线不一致；主线据此在写回 Round 4 记录后重新 `git add -f` 该计划，并以最新 staged blob / sha256 作为守护最终检验证据，不沿用旧候选。
- 主线处理：Round 4-A / Round 4-B 均通过，无阻断、无最小需改项、无待确认项；本轮仅写回 subagent 结果和流程状态，不改变技术方案、公开 API、expectation 授权、禁止修改面、任务范围、验收命令或 execute 草案。

### Draft 5：用户授权补充本地 expectation 合同资产

- 触发来源：2026-06-16 用户反馈“应该 添加对应的 expatation，作为验证”，并确认 expectation 默认不会进入远程仓库。
- 授权范围：仅限本地 ignored `expectation/pass/producer_consumer_analysis` family；新增 / 更新的合同资产用于验证本计划的 alloc first-touch 与 ring backing init-only alias 行为。
- 主线处理：
  - 更新 `expectation/pass/producer_consumer_analysis/__main__.py` 聚合说明，补充 alloc first-touch 与 ring backing init-only alias 合同描述。
  - 新增 `expectation/pass/producer_consumer_analysis/alloc_first_touch.py`，覆盖 `dma.alloc -> dma.slice WRITE -> dma.copy READ` 与 alias-only no-op before touch。
  - 新增 `expectation/pass/producer_consumer_analysis/ring_backing_init_alias.py`，覆盖 backing alloc init producer、`dma.make_ring` / `dma.current_ring` / `dma.reinterpret` 无 event attr、slot first WRITE 消费 init 并生产普通 data event、后续 `kernel.matmul` 只消费 data event。
  - 更新验收设计、S1 / S2 禁止修改面、S3 任务卡、计划自检和用户确认记录，使 expectation 从 Draft 4 的只读旧合同来源升级为“架构侧按用户授权本地补齐，execute 链只读运行”的合同门禁。
- 本地 manifest / hash：
  - `expectation/pass/producer_consumer_analysis/__main__.py`：sha256 `cf26e510ddc28fc5078f399970377e2b9377c3392f137564b80c9fca0dd49ac3`
  - `expectation/pass/producer_consumer_analysis/alloc_first_touch.py`：sha256 `0a69d4ba92573355eb55cf11fc5e3c93aeab671271cdf5f6ced72fe0a6086802`
  - `expectation/pass/producer_consumer_analysis/ring_backing_init_alias.py`：sha256 `ccfe2a16db7bbef9df4fbaaf0157f5b350d01c5ad03e9ac650bdd76d5c77e4d7`
- 架构侧自检：
  - `PYTHONDONTWRITEBYTECODE=1 python3 -m py_compile expectation/pass/producer_consumer_analysis/__main__.py expectation/pass/producer_consumer_analysis/alloc_first_touch.py expectation/pass/producer_consumer_analysis/ring_backing_init_alias.py`：通过。
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 -m expectation.pass.producer_consumer_analysis.alloc_first_touch`：当前未实现基线失败，失败点为缺少 `dma.slice {consumer=[0], productor=[1]}`；这是 execute 必须修复的合同门禁。
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 -m expectation.pass.producer_consumer_analysis.ring_backing_init_alias`：当前未实现基线失败，失败点为缺少 backing `dma.alloc {productor=[0]}`；这是 execute 必须修复的合同门禁。
- 流程影响：Draft 4 守护最终检验通过结论不再足以支持下发；Draft 5 已完成 subagent strict review 收敛但未形成可用下发依据。用户于 2026-06-17 改变 ring backing 语义后，Draft 5 守护请求已由守护确认暂停并作废，Draft 5 staged blob `6a24d05065c5be3bb3c3cfff14c67ab0d03de773` / sha256 `fb36f55f05c37d4f6044d3e775f857bd774992c5e4309cabe2d4a6831e232735` 不得再作为守护通过、通知管理员或创建 execute 的依据。

### Round 5：Codex subagent strict review（Draft 5）

- 历史状态：以下 Round 5 记录仅解释 Draft 5 曾如何收敛；Draft 5 已因用户最新 ring 语义变更和守护暂停回执作废，不得作为 Draft 6 下发、守护或通知管理员依据。
- 审阅对象：`ARCHITECTURE/plan/alloc_producer_init_edge.md` Draft 5。
- 输入标准包：根 `AGENTS.md`、大闸蟹 prompt、`agents/standard/计划书标准.md`、`agents/standard/计划书模板.md`、`agents/standard/expectation任务规则.md`、`agents/standard/实现文件规范.md`、`agents/standard/审查规范.md`、staged Draft 5 全文、用户授权 expectation 来源、local-only expectation manifest / hash、禁止修改面、必过验收命令、unrelated staged / unstaged 文件隔离说明。
- 严格通过口径：用户授权链、local-only expectation 说明、manifest / hash、运行入口、预期输出、禁止修改面和下发门禁必须自洽；新增 expectation IR 合同必须可解析、可运行，当前基线失败必须是实现缺口而非 expectation 本体错误；若仍有旧现场冲突、公开 API / expectation 授权风险、任务卡不可执行或待用户确认项，则不通过。
- Round 5-A：Mill，流程 / expectation 授权 / 门禁 / 任务可执行性复核。
  - 结论：不通过。
  - 阻断项：`当前基线` 章节仍保留旧 unrelated staged / unstaged 列表，与当前事实冲突；现场实际为全量 cached diff 仅本计划 A 项，unstaged diff 为空，expectation family 为 ignored local-only，不进入 normal git status。
  - 最小需改项：将旧 unrelated staged / unstaged 列表替换为当前事实，避免执行 / 审查误按旧隔离现场推进。
  - 待确认项：无。
  - 关键证据：expectation 授权链、local-only 说明、hash、入口、预期输出和只读边界已写清；`git check-ignore -v` 命中 `.gitignore:21:expectation`，`git ls-files --stage -- expectation/pass/producer_consumer_analysis` 无输出；新增 expectation leaf 当前基线失败已正确表述为 execute 后必须转为通过的合同门禁。
  - 主线处理：已按最小需改项更新 `当前基线` 章节，改为当前事实：全量 cached diff 仅有 `A ARCHITECTURE/plan/alloc_producer_init_edge.md`，unstaged diff 为空，`expectation/pass/producer_consumer_analysis/**` 为 ignored local-only 合同资产，通过 manifest / hash、`git check-ignore` 与 `git ls-files --stage` 无输出记录状态。
- Round 5-B：Mendel，技术 / IR 合同 / 验收闭环复核。
  - 结论：通过。
  - 阻断项：无。
  - 最小需改项：无。
  - 待确认项：无。
  - 关键证据：三个 expectation sha256 与 Draft 5 记录一致；`alloc_first_touch.py` 两个 case 表达 alloc init producer、alias-only no event、首个真实 WRITE touch 消费 init 并生产 data、后续 reader 只消费 data event；`ring_backing_init_alias.py` 表达 backing `dma.alloc` init、`make_ring/current_ring/reinterpret` 无 event attr、slot first WRITE 消费 init 并生产 data、`kernel.matmul` 只消费 data。新增 leaf 可解析、可运行；当前基线失败为实现缺口，不是 IR 写错；当前两 leaf 已覆盖本轮最小必要合同范围。
- 主线处理：Round 5-A 的流程状态阻断已修正；由于修正后 staged 候选已变化，需要对最新 Draft 5 再做 writeback-only subagent strict review，确认 Round 5-A 最小修订未引入新冲突后才可进入守护最终检验。

### Round 6：Codex subagent writeback-only strict review（Draft 5）

- 历史状态：以下 Round 6 记录仅解释 Draft 5 writeback 曾如何收敛；Draft 5 已因用户最新 ring 语义变更和守护暂停回执作废，不得作为 Draft 6 下发、守护或通知管理员依据。
- 审阅对象：Round 5-A 最小修订后的 `ARCHITECTURE/plan/alloc_producer_init_edge.md` Draft 5。
- 输入标准包：根 `AGENTS.md`、大闸蟹 prompt、相关 `agents/standard/**`、最新 staged Draft 5 全文、Round 5-A 不通过项与主线处理、Round 5-B 通过结论、用户 expectation 授权来源、local-only expectation manifest / hash、禁止修改面、必过验收命令。
- 严格通过口径：只复核 Round 5-A 最小需改项是否闭合、Round 5 记录是否自洽、Draft 5 门禁是否仍为“需重新守护，未通过前不得通知管理员创建 execute”；不得扩大技术方案。
- Round 6-A：Mill 原会话。
  - 状态：未形成有效复核结论；工具返回 `Selected model is at capacity. Please try a different model.`
  - 主线处理：不降级、不绕过；改由替补 Codex subagent Godel 执行同一 writeback-only strict review。
- Round 6-A replacement：Godel，流程 / expectation 授权 / 门禁 writeback-only 复核。
  - 结论：通过。
  - 阻断项：无。
  - 最小需改项：无。
  - 待确认项：无。
  - 关键证据：staged blob `b4fe4b8a57adf7a1d4f23b504b01527713a8afc7`、staged sha256 `d402fb7449c79ffdf56b7b33f79be128e3bbe8ec2b094ccaad55c01869e91db1`；cached name-status 仅 `A ARCHITECTURE/plan/alloc_producer_init_edge.md`；unstaged diff 为空；`git diff --cached --check` / `git diff --check` clean。Round 5-A 最小需改项已闭合，`当前基线` 已替换为当前事实；Draft 5 门禁清楚；expectation local-only 边界和 execute 链只读权限清楚。
- Round 6-B：Mendel，技术 / IR 合同 / 验收闭环 writeback-only 复核。
  - 结论：通过。
  - 阻断项：无。
  - 最小需改项：无。
  - 待确认项：无。
  - 关键证据：staged blob `b4fe4b8a57adf7a1d4f23b504b01527713a8afc7`、staged sha256 `d402fb7449c79ffdf56b7b33f79be128e3bbe8ec2b094ccaad55c01869e91db1`；相对 Round 5-B 基线只新增 Round 5-A/B 记录并修正旧 unrelated 现场列表，未改技术方案、API、验收命令或 S1-S3 任务卡。三个 expectation sha256 与记录一致，仍为 ignored local-only；新增 expectation 仍作为 execute 后必须通过的合同门禁。
- 主线处理：Round 6-A replacement / Round 6-B 均通过，无阻断、无最小需改项、无待确认项；Draft 5 subagent strict review 曾重新收敛并可进入守护最终检验。该 Draft 5 口径已被 Draft 6 supersede，当前不得沿用 Draft 5 结论请求守护或通知管理员创建 execute。

### Draft 6：用户调整 ring 场景为 make_ring 承接 init producer

- 触发来源：2026-06-17 用户确认“现在改了，如果是 alloc make ring，再 make ring 添加属性”。
- 守护暂停回执：`守护最好的爱莉希雅` 已确认暂停并作废 Draft 5 下发口径；Draft 5 staged blob `6a24d05065c5be3bb3c3cfff14c67ab0d03de773` / sha256 `fb36f55f05c37d4f6044d3e775f857bd774992c5e4309cabe2d4a6831e232735` 不得再作为守护通过、通知管理员或创建 execute 的依据。
- 主线处理：
  - 将 S2 ring 场景从“backing `dma.alloc` 写 `productor`、`dma.make_ring` 无 event attr”改为“backing `dma.alloc` 无 event attr、`dma.make_ring` 写 `productor` 并作为 ring init producer”。
  - 修订 `expectation/pass/producer_consumer_analysis/__main__.py` 聚合说明。
  - 修订 `expectation/pass/producer_consumer_analysis/ring_backing_init_alias.py`，预期 IR 断言为 `dma.alloc` 无 `productor` / `consumer`，`dma.make_ring {productor = [0]}`，slot first WRITE `dma.slice {consumer = [0], productor = [1]}`，后续 `kernel.matmul {consumer = [1]}`。
  - 更新完成态、验收设计、S2 / S3 任务卡、计划自检、用户确认与下发门禁。
- 本地 manifest / hash：
  - `expectation/pass/producer_consumer_analysis/__main__.py`：sha256 `4399778cd2731c8f07121a0fee8a9a87870b68b89896d0449753704c65fc6f09`
  - `expectation/pass/producer_consumer_analysis/alloc_first_touch.py`：sha256 `0a69d4ba92573355eb55cf11fc5e3c93aeab671271cdf5f6ced72fe0a6086802`
  - `expectation/pass/producer_consumer_analysis/ring_backing_init_alias.py`：sha256 `3c0a557d1ae1d9c70a290c923641a17ce629cf1cd5d126642608bd12a8c1469f`
- 架构侧自检：
  - `PYTHONDONTWRITEBYTECODE=1 python3 -m py_compile expectation/pass/producer_consumer_analysis/__main__.py expectation/pass/producer_consumer_analysis/alloc_first_touch.py expectation/pass/producer_consumer_analysis/ring_backing_init_alias.py`：通过。
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 -m expectation.pass.producer_consumer_analysis.alloc_first_touch`：当前未实现基线失败，失败点为缺少 `dma.slice {consumer=[0], productor=[1]}`。
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 -m expectation.pass.producer_consumer_analysis.ring_backing_init_alias`：当前未实现基线失败，失败点为缺少 `dma.make_ring {productor=[0]}`。
- 流程影响：Draft 6 改变了 S2 预期 IR 与本地 expectation 合同，必须重新进行两路 Codex subagent strict review 收敛；收敛通过后再请求 `守护最好的爱莉希雅` 本人守护最终检验。守护通过前不得通知管理员创建 execute。

### Round 7：Codex subagent strict review（Draft 6）

- 审阅对象：`ARCHITECTURE/plan/alloc_producer_init_edge.md` Draft 6。
- 输入标准包：根 `AGENTS.md`、大闸蟹 prompt、`agents/standard/计划书标准.md`、`agents/standard/计划书模板.md`、`agents/standard/expectation任务规则.md`、`agents/standard/实现文件规范.md`、`agents/standard/审查规范.md`、最新 staged Draft 6 全文、用户 2026-06-17 make_ring 语义确认、Draft 5 守护暂停 / 作废回执、local-only expectation manifest / hash、禁止修改面、必过验收命令和 staged / ignored / sensitive 范围证据。
- 严格通过口径：Draft 5 旧下发口径、backing alloc producer 旧语义、expectation 权限、公开 API、任务卡、验收命令、守护 / 下发门禁任一处仍不自洽则不通过；不得以历史记录替代 Draft 6 当前收敛。
- Round 7-A：Beauvoir，流程 / API / expectation 授权 / 门禁 / 任务可执行性 strict review。
  - 结论：通过。
  - 阻断项：无。
  - 最小需改项：无。
  - 待确认项：无。
  - 关键证据：最新 staged 候选 blob `6fef6c227f40c7699888b2f9622b63ed33037c27`、sha256 `097e9609bba20169f47252235f0778e3e7fc7d7f3b844dca446497af8f777a39`；cached name-status 仅 `A ARCHITECTURE/plan/alloc_producer_init_edge.md`；本路径 `git diff --cached --check` clean。Draft 6 明确 Draft 5 守护请求已暂停作废，Round 5 / 6 仅为历史记录，不得作为 Draft 6 下发、守护或通知管理员依据。三份 expectation sha256 与计划记录一致，`git check-ignore` 命中 `.gitignore:21:expectation`，`git ls-files --stage -- expectation/pass/producer_consumer_analysis` 无输出。下发门禁自洽：Draft 6 仍需 Round 7-A / 7-B 收敛后再请求守护最终检验，守护通过前不得通知管理员创建 execute。
- Round 7-B：Lovelace，技术 / IR 合同 / 验收闭环 strict review。
  - 结论：通过。
  - 阻断项：无。
  - 最小需改项：无。
  - 待确认项：无。
  - 关键证据：最新 staged 候选 blob `6fef6c227f40c7699888b2f9622b63ed33037c27`、sha256 `097e9609bba20169f47252235f0778e3e7fc7d7f3b844dca446497af8f777a39`；cached name-status 为 `A ARCHITECTURE/plan/alloc_producer_init_edge.md`；本路径 `git diff --cached --check` clean。S2 当前口径统一为 `dma.make_ring {productor=[0]}`，backing `dma.alloc` 无 event attr；`ring_backing_init_alias.py` 断言 `dma.alloc` 无 `productor/consumer`，`dma.make_ring` 有 `productor=[0]`，`dma.slice` 有 `consumer=[0], productor=[1]`，`kernel.matmul` 只消费 `[1]`。普通 WRITE consumer 扩大风险已由“仅 ALLOC candidate 可用 READ ∪ WRITE first touch，普通 WRITE 仍只连 downstream READ”约束；ring data edge 污染风险已有 `ring_soft_pipeline_events`、`single_tile_prologue_epilogue` 回归和 `loop_first/loop_carried/after_loop` 不被主 `productor/consumer` 污染的记录要求。
- 主线处理：Round 7-A / Round 7-B 均通过，无阻断、无最小需改项、无待确认项；Draft 6 可进入 `守护最好的爱莉希雅` 守护最终检验。守护通过前仍不得通知管理员创建 execute。

### subagent 收敛结论

- 已发起或计划要求的审阅任务：
  - Round 1-A Beauvoir：不通过；Draft 2 已主线处理。
  - Round 1-B Lovelace：不通过；Draft 2 已主线处理。
  - Round 2-A Beauvoir：不通过；Draft 3 已主线处理。
  - Round 2-B Lovelace：不通过；Draft 3 已主线处理。
  - Round 3-A Beauvoir：通过；无阻断、无最小需改项、无待确认项。
  - Round 3-B Lovelace：通过；无阻断、无最小需改项、无待确认项。
  - Round 4-A Popper：通过；无阻断、无最小需改项、无待确认项。
  - Round 4-B Averroes：通过；无阻断、无最小需改项、无待确认项。
  - Round 5-A Mill：不通过；最小需改项已主线处理。
  - Round 5-B Mendel：通过；无阻断、无最小需改项、无待确认项。
  - Round 6-A Mill：工具容量错误，未形成有效结论；已由 Godel replacement 接续。
  - Round 6-A replacement Godel：通过；无阻断、无最小需改项、无待确认项。
  - Round 6-B Mendel：通过；无阻断、无最小需改项、无待确认项。
  - Round 7-A Beauvoir：通过；无阻断、无最小需改项、无待确认项。
  - Round 7-B Lovelace：通过；无阻断、无最小需改项、无待确认项。
- 收敛结论：Round 1 / 2 不通过项均已主线处理；Round 3 两路已通过；Draft 4 用户反馈后的 IR 预期 writeback 已由 Round 4-A / Round 4-B 通过复核；Draft 5 expectation 合同变更的 Round 5-A 不通过项已修正，并由 Round 6-A replacement / Round 6-B writeback-only 复核通过，但 Draft 5 已因用户最新 ring 语义变更和守护暂停回执作废，不能作为 Draft 6 下发依据。
- 收敛结论更新：Draft 6 已由 Round 7-A / Round 7-B 两路 Codex subagent strict review 通过，无阻断、无最小需改项、无待用户确认项；随后已由 `守护最好的爱莉希雅` 守护复验通过，并经用户最终确认下发。
- 遗留项：无。用户最终确认下发后，管理员已创建唯一计划级 execute `T-20260620-e3ed07d4`；后续固定按 `execute -> review -> archive_acceptance -> merge/归档` 流转。

### 守护最终检验

- 检验对象：`守护最好的爱莉希雅`
- 当前状态：Draft 4 已通过但已被后续 expectation 合同变更 supersede；Draft 5 守护请求已由守护确认暂停并作废；Draft 6 已完成 Round 7-A / Round 7-B subagent strict review 收敛，并已由 `守护最好的爱莉希雅` 守护复验通过。用户已最终确认下发，管理员已创建唯一计划级 execute `T-20260620-e3ed07d4`。
- 通过回执：
  - 结论：通过。
  - 阻断项：无。
  - 最小需改项：无。
  - 待确认项：无新的方案待确认项；用户最终确认下发已完成。
  - 正式候选：`ARCHITECTURE/plan/alloc_producer_init_edge.md`，下发时 staged blob `4493095e36d3212a3e6d5007346ad2252fc5ab8a`，staged sha256 `d1c67060840a2cb70e1f875258529127a663827fc586507199fa68a72fa6892a`，cached name-status `A`。
  - 检查摘要：本计划路径 `git diff --cached --check` / `git diff --check` clean；守护复验时全量 cached diff 仅本计划 A 项，unstaged diff 为空，敏感范围 `expectation`、`.skills`、`agents/standard`、`AGENTS.md`、`TODO.md`、`DONE.md`、`agents/codex-multi-agents/agents-lists.md` 无 diff。
  - 范围摘要：Draft 6 维持当前仓库根目录方案，不改变公开 API 签名、registry pass name、公开 attr 名称或 `if_branch_*` 策略；`dma.alloc -> dma.make_ring` ring 场景由 `dma.make_ring` 承接 init producer event。
  - 合同验收摘要：守护复验核对 local-only expectation manifest 与计划一致，`git check-ignore` 命中 `.gitignore:21:expectation`，`git ls-files --stage -- expectation/pass/producer_consumer_analysis` 无输出，三份关键 expectation 入口 py_compile 通过；完整 expectation family 是 execute 后必过合同门禁。
  - 允许事项：用户最终确认下发后，允许管理员创建唯一计划级 execute `alloc-producer-init-edge`；管理员已创建 `T-20260620-e3ed07d4`，不得创建第二个并行 execute。
- Draft 5 / Draft 6 更新：Draft 5 staged blob `6a24d05065c5be3bb3c3cfff14c67ab0d03de773` / sha256 `fb36f55f05c37d4f6044d3e775f857bd774992c5e4309cabe2d4a6831e232735` 已被守护确认暂停并作废，不得作为下发或归档依据；当前以 Draft 6 守护复验通过、用户最终确认下发和任务链 `T-20260620-e3ed07d4` 为准。

## 计划书入档验收 / 复验 / 修复复核记录

- 结论人：提莫炖蘑菇。
- 结论：通过。`T-20260620-e3ed07d4` 已完成 execute、review 复审和本轮 archive_acceptance 入档验收；可按计划级链路进入 `merge/归档`，不得由 archive_acceptance 直接提交或推送。
- 验证基线：任务 worktree 分支 `task/T-20260620-e3ed07d4`；`HEAD=origin/main=merge-base=7c3e9ac01ff778f56420e0fcc06fce655cec199f`。正式计划真源为主仓 staged `ARCHITECTURE/plan/alloc_producer_init_edge.md`，worktree 内不复制计划书。
- 执行目录：`/home/lfr/kernelcode_generate/wt-20260620-alloc-producer-init-edge`。
- 同步结果：archive_acceptance 阶段已 `git fetch origin main --prune` 并复核 latest main 一致；任务候选 diff 限于 `kernel_gen/passes/producer_consumer_analysis.py`、`spec/pass/producer_consumer_analysis.md`、`test/passes/test_producer_consumer_analysis.py`、任务记录与本计划书入档回写；`expectation/`、`.skills`、`agents/standard`、`AGENTS.md`、`TODO.md`、`DONE.md`、`agents/codex-multi-agents/agents-lists.md` 无任务 diff。
- 合同验收摘要：archive_acceptance 复跑 `py_compile` 通过；`test/passes/test_producer_consumer_analysis.py -k "alloc_first_touch or ring_backing_init_alias or ring_soft_pipeline_events or single_tile_prologue_epilogue"` 为 `10 passed, 10 deselected, 1 warning`；完整 producer-consumer pytest 为 `20 passed, 1 warning`；pipeline 回归 `test/passes/pipeline/test_npu_demo_lowering.py` 为 `11 passed, 1 warning`；只读合同验收 `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260620-alloc-producer-init-edge:/home/lfr/kernelcode_generate timeout 120 python3 -m expectation.pass.producer_consumer_analysis` exit 0，关键 leaf 覆盖 `alloc_first_touch`、`ring_backing_init_alias`、`memory_effect_alias`、`if_branch`、`after_if`、`loop_body`、`after_loop`、`ring_*`。
- 最小阻断项或通过摘要：无剩余阻断。前序 review 发现的 `dma.alloc` init first-touch 在 `scf.if` then/else 互斥分支共享 `if_branch` init event 缺口已由 execute 返工和 review 复审收口；Diff 反推审查、减法审查、公开 API 边界、private callable 边界、只读 expectation 边界、敏感范围和任务记录完整性均已核对通过。
- 计划归档目标：`agents/codex-multi-agents/log/task_records/done_plan/2026/25/alloc_producer_init_edge.md`

## 计划目标

- 把 alloc 初始化同步边界从下游专用 pass 上移到 producer-consumer 分析语义：直接使用的 `dma.alloc` 作为 init producer，alloc 结果所属资源的第一个真实触碰 op 作为 init consumer。
- first touch 同时支持 READ 与 WRITE；例如 `dma.slice` 写入 ring slot 时也必须能等待 make_ring init event。
- `dma.alloc -> dma.make_ring` 场景由 `dma.make_ring` 承接 init producer event，再通过 `dma.current_ring / dma.advance_ring -> view/reinterpret` 链找到第一个真实 slot 使用者。
- 保持普通 ring slot data producer-consumer alias 不被 make_ring init alias 污染。

## 非目标

- 不恢复 synthetic `ring.free:*` event。
- 不改变 `ProducerConsumerAnalysisPass` 公开构造签名、registry pass name 或 `fold` option。
- 不新增公开 dialect attr；新增内部 alias/root 表只能是当前文件内实现细节。
- 除 Draft 6 已获用户授权并由架构侧物化的本地 `expectation/pass/producer_consumer_analysis` 合同资产外，执行链不修改 `expectation/`。
- 不提交 dump 作为资产；dump 只用于本地检查与任务记录证据。
- 不处理外部 `sdnn_kenrel_gen_dsl`、`SdnnCoreAssignPass`、`SdnnEventSchedulePass`、`sdnn4_lowering`、`dma1d`、`driver.inline INIT_EVENT` 或 EmitC。
- 不新增、不重定义 `if_branch_*` first-touch 策略；ALLOC first-touch 若经过现有 `_classify_edge` 命中 if 分支关系，只复用现有 `if_branch_*` attr 规则，既有控制流分类逻辑保持当前公开合同。

## 当前基线

- 当前根目录公开 `ProducerConsumerAnalysisPass` 已在 `spec/pass/producer_consumer_analysis.md` 中公开：
  - `class ProducerConsumerAnalysisPass(fold: bool = True)`
  - `ProducerConsumerAnalysisPass.from_options(options: dict[str, str]) -> ProducerConsumerAnalysisPass`
  - `ProducerConsumerAnalysisPass.apply(ctx: Context, module: ModuleOp) -> None`
  - registry pass name：`producer-consumer-analysis`
- 当前根目录 spec 明确 `ALLOC(value)` 是 producer value 候选，但现有公开测试语义主要覆盖 alloc fanout 与 READ consumer。
- 当前根目录 spec 已有 ring-aware current/advance 合同：
  - `dma.current_ring` result 是 ring cursor slot root。
  - `dma.advance_ring` 是 cursor boundary，op 本身不写 producer/consumer attr。
  - loop-first / loop-carried / after-loop 使用现有分类 attr。
- 当前根目录 pipeline `npu-demo-lowering` 中 `producer-consumer-analysis` 位于 `loop-soft-pipeline` 之后、`memory-pool` 之前。
- 当前不存在 `sdnn_kenrel_gen_dsl` 目录；用户已确认当前计划不考虑该外部工程相关事项。
- 当前候选隔离事实：
  - 全量 cached diff 仅有 `A ARCHITECTURE/plan/alloc_producer_init_edge.md`。
  - unstaged diff 为空。
  - `expectation/pass/producer_consumer_analysis/**` 是 ignored local-only 合同资产，不进入 normal git status / cached diff；本计划通过 manifest / hash、`git check-ignore` 和 `git ls-files --stage` 无输出记录其状态。

## 方案比较与选型

### C0：目标工作区

- 用户决策：选项 A，当前仓库根目录方案；确认来源为 2026-06-15 用户回复“A”。

- 选项 A：当前仓库根目录方案。
  - 内容：只修改根目录 `ProducerConsumerAnalysisPass`、spec、pytest 和必要 pipeline 测试。
  - 优点：路径存在，可立即做严格审阅和执行。
  - 风险：不覆盖 `plan/2` 中 SDNN `core_assign/event_schedule/dma1d` 目标，无法验收 `sdnn_*` event schedule。
  - 结论：采用。
- 选项 B：外部 `sdnn_kenrel_gen_dsl` 工作区方案。
  - 内容：按 `plan/2` 覆盖 third_party `kernelcode_generate` 与 first-party SDNN pass。
  - 优点：完整匹配 `plan/2` 的目标。
  - 风险：当前工作区缺目标路径，需要用户或管理员提供实际 worktree；未确认前不能下发。
  - 结论：不采用；用户已确认当前项目不考虑这些外部 SDNN 事项。
- 选项 C：把 `sdnn_kenrel_gen_dsl` 引入当前仓库。
  - 内容：新增或移动外部工程进入当前仓库。
  - 优点：单工作区执行。
  - 风险：范围巨大，容易混入仓库结构变更，不适合作为本计划前置动作。
  - 推荐：不推荐。

### C1：alloc first-touch edge 语义

- 推荐方案：在 `ProducerConsumerAnalysisPass` 内区分 ALLOC init edge 与普通 WRITE->READ data edge。
- 设计：
  - `ALLOC(value)` 只产生该 alloc root 的第一条 READ 或 WRITE first-touch edge。
  - 普通 `WRITE(value)` 保持当前 READ consumer 逻辑，不因本计划扩大为 WRITE consumer。
  - first-touch edge 使用现有 event attr 体系，不新增公开 attr。
- 影响：需要新增 init-only alias/root 表，避免影响普通 ring dataflow。

## 公开 API 设计

- 用户确认来源：2026-06-15 用户确认 C0=A，`if_branch_*` first-touch 只复用现有规则，当前项目不考虑 `driver.inline INIT_EVENT` 或 SDNN event schedule。
- 当前仓库公开 API 不改签名：
  - `class ProducerConsumerAnalysisPass(fold: bool = True)`
  - `ProducerConsumerAnalysisPass.from_options(options: dict[str, str]) -> ProducerConsumerAnalysisPass`
  - `ProducerConsumerAnalysisPass.apply(ctx: Context, module: ModuleOp) -> None`
  - registry pass name：`producer-consumer-analysis`
- 公开行为变化候选：
  - `ALLOC(value)` 新增 first-touch init edge 语义，consumer 可为 READ 或 WRITE。
  - `dma.alloc -> dma.make_ring` ring 场景由 `dma.make_ring` 承接 init producer event；backing `dma.alloc` 在该 ring 路径不写 event attr。
  - first-touch edge 使用既有 `productor` / `consumer`、`if_branch_*`、`after_if_*`、`loop_body_*`、`after_loop_*` 等公开 attr；不新增公开 attr，不新增 if 分支策略。

## 完成态定义

- `dma.alloc` 对同一 init root 只生成第一条 READ 或 WRITE first-touch edge。
- `dma.alloc -> dma.make_ring` ring 场景中，backing `dma.alloc` 不写 producer / consumer / init attr，`dma.make_ring` 写 init `productor` attr。
- `dma.current_ring` / `dma.advance_ring` 的 slot 结果只在 init-only alias 表中回到 `dma.make_ring` init root。
- 普通 ring data edge 继续按 current/advance ring-aware 规则输出，不被 make_ring init alias 合并。
- 公开 API 签名、registry pass name、event attr 名称均不变。
- 不触碰外部 SDNN、driver inline、EmitC 或不存在路径。

## 验收设计

- 当前仓库 focused pytest：
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 -m pytest -q test/passes/test_producer_consumer_analysis.py -k "alloc_first_touch or ring_backing_init_alias or ring_soft_pipeline_events or single_tile_prologue_epilogue"`
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 -m pytest -q test/passes/test_producer_consumer_analysis.py`
  - 若实际 diff 触碰 `kernel_gen/pipeline/npu_demo_lowering.py`、pipeline spec 或 pipeline test，则补跑：`PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 -m pytest -q test/passes/pipeline/test_npu_demo_lowering.py -k "test_npu_demo_lowering_pipeline_pass_order or test_npu_demo_lowering_pipeline_static_dump_runs_multi_buffer_before_pool"`
- 当前仓库合同验收：
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=<任务worktree>:/home/lfr/kernelcode_generate python3 -m expectation.pass.producer_consumer_analysis`
  - execute 完成后预期：exit 0；leaf 至少覆盖 `memory_effect_alias`、`if_branch`、`after_if`、`loop_body`、`after_loop`、`ring_loop_first`、`ring_loop_carried`、`ring_after_loop`、`ring_cursor_current_advance`、`alloc_first_touch`、`ring_backing_init_alias`。
  - `expectation` 是主仓本地 ignored / untracked 合同来源，默认不进入远程仓库；Draft 6 已由架构侧按用户授权本地补齐并按用户最新 ring 语义修订，execute / review / archive_acceptance / merge / 管理员只读运行，不得修改。
  - 当前未实现基线运行新增 leaf 失败属于预期：`alloc_first_touch` 与 `ring_backing_init_alias` 是本计划 execute 后必须转为通过的合同门禁。
- 静态检查：
  - `git diff --check`
- Diff 反推要求：execute / review / archive_acceptance 必须按实际 diff 补测试；`expectation` 单列为合同验收，不计入 diff 反推测试。

## 通用执行规则

- 修改 `kernel_gen/passes/producer_consumer_analysis.py` 时，必须同步该文件文件级说明中的 `功能说明 / API 列表 / 使用示例 / 关联文件`；`API 列表` 必须紧跟在 `功能说明` 后，公开签名仍保持 `ProducerConsumerAnalysisPass(fold: bool = True)`、`from_options(options: dict[str, str])`、`apply(ctx: Context, module: ModuleOp)` 不变。
- 新增或修改函数时，函数注释必须至少包含 `功能说明 / 使用示例`；不得新增跨文件非公开 API 调用，不得在测试中直连跨文件私有 helper。
- Producer candidate 必须保留 kind：`ALLOC` 与 `WRITE` 不能在后续 consumer 收集中混成同一种普通 producer。
- 只有 `ALLOC` candidate 的 init first-touch consumer 集合允许使用 `READ ∪ WRITE` roots；普通 `WRITE` candidate 仍只允许连接 downstream meaningful `READ` consumer。
- 每个 alloc init root 按 `op_order` 只取第一条 READ 或 WRITE touch；后续 touch 不再消费 alloc init event。
- `dma.view`、`dma.reshape`、`dma.subview`、`dma.reinterpret`、`dma.current_ring`、`dma.advance_ring` 等 alias-only / cursor-only op 不算真实 first touch，不得因 init alias 被写 event attr。
- if 分支 first-touch 不新增策略；若现有 `_classify_edge` 将 edge 分类为 `if_branch` / `after_if`，继续使用既有 attr 规则。

## 计划内小任务

### S1. 设计 alloc first-touch init edge

- 为什么做：alloc init 同步应由 producer-consumer analysis 统一建模，避免下游 pass 重新分析内存别名。
- 做什么：为 `ProducerConsumerAnalysisPass` 增加 ALLOC first-touch edge 语义，first touch 支持 READ / WRITE。
- 不做什么：不改变普通 WRITE candidate 的 READ consumer 逻辑，不新增公开 attr。
- 怎么验收：producer-consumer pytest 必须点名覆盖 `alloc_first_touch_write`、`alloc_first_touch_read`、`alloc_first_touch_only_first_op`、`alloc_first_touch_write_candidate_still_read_only` 四类断言。
- 卡住问谁：公开 API / attr 变化问用户；实现边界问大闸蟹。
- 上下文摘要：当前 spec 已把 ALLOC 列为 producer candidate，但 `plan/2` 指出第一个真实使用者可能是 WRITE。
- 小任务目标：alloc init edge 能稳定输出到现有 event attr 体系。
- 非目标：不生成 wait / signal runtime op；不新增 if 分支策略。
- 模块范围：`kernel_gen/passes/producer_consumer_analysis.py`、`spec/pass/producer_consumer_analysis.md`、`test/passes/test_producer_consumer_analysis.py`。
- 禁止修改面：除 Draft 6 已授权并由架构侧物化的本地 expectation 合同资产外，执行链不得修改 `expectation/`；不得改无关 pipeline、无关 SDNN pass。
- 合同真源：spec > pytest > expectation 本地合同 > 当前实现。
- 最小功能闭环：单个 `dma.alloc` 后第一条 READ 或 WRITE op 得到 init event，后续 op 不重复消费该 init event。
- 示例 / 预期：
  输入 IR：
  ```mlir
  func.func @alloc_first_write(%src : !nn.memory<...>, %dst : !nn.memory<...>) {
    %buf = "dma.alloc"() : () -> !nn.memory<...>
    "dma.slice"(%buf, %src, ...) : (...) -> ()
    "dma.copy"(%dst, %buf) : (...) -> ()
    func.return
  }
  ```
  预期 IR attr 形态：
  ```mlir
  func.func @alloc_first_write(%src : !nn.memory<...>, %dst : !nn.memory<...>) {
    %buf = "dma.alloc"() {productor = [0]} : () -> !nn.memory<...>
    "dma.slice"(%buf, %src, ...) {consumer = [0], productor = [1]} : (...) -> ()
    "dma.copy"(%dst, %buf) {consumer = [1]} : (...) -> ()
    func.return
  }
  ```
  预期说明：`dma.alloc` 写一个 init producer event；第一条真实 touch `dma.slice` 因 WRITE `%buf` 作为 init consumer，同时可作为普通 WRITE candidate 生产 `%buf` 后续 data event；后续 `dma.copy` 不再消费 alloc init event，只按普通 data edge 消费 `dma.slice` / WRITE producer。示例 event id 以该最小函数遍历顺序为例，实际测试应断言 edge 关系和“只消费一次 init event”，不要依赖无关 op 插入后的固定编号。
- 执行步骤：
  1. 为 producer candidate 保留 kind，明确 `ALLOC` / `WRITE` 后续 consumer 收集路径。
  2. 只对 `ALLOC` candidate 收集 `READ ∪ WRITE` first-touch roots；普通 `WRITE` candidate 仍只收集 downstream meaningful `READ` roots。
  3. 按 `op_order` 为每个 alloc init root 仅选择第一条真实 READ 或 WRITE touch；alias-only / cursor-only op 不算 touch。
  4. 补 spec 与 pytest；实现文件如有修改，同步文件级说明、`API 列表` 和改动函数注释。
- 验收必过项目：
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 -m pytest -q test/passes/test_producer_consumer_analysis.py -k "alloc_first_touch"`
  - 建议新增测试名：`test_producer_consumer_analysis_alloc_first_touch_write_uses_init_event_once`、`test_producer_consumer_analysis_alloc_first_touch_read_uses_init_event_once`、`test_producer_consumer_analysis_alloc_first_touch_ignores_alias_only_ops`、`test_producer_consumer_analysis_alloc_first_touch_write_candidate_still_has_read_only_consumers`。
- 记录要求：记录新增用例、first-touch 分类、普通 WRITE 未扩成 WRITE consumer 的负断言和是否影响旧 fanout 测试。

### S2. 增加 make_ring init producer edge

- 为什么做：`dma.alloc -> dma.make_ring` 场景需要由 ring 对象承接 init event，再通过 current / advance slot 找到 first touch，同时不能污染普通 ring dataflow。
- 做什么：新增 init-only alias/root 表，将 `dma.make_ring` init root 与 ring slot first touch 关联；backing `dma.alloc` 在该 ring 路径不写 event attr。
- 不做什么：不把 `dma.current_ring` / `dma.advance_ring` 全局 alias 到 backing alloc；不让 backing `dma.alloc` 和 `dma.make_ring` 同时生产同一个 init event。
- 怎么验收：pytest 覆盖 make_ring/current_ring/reinterpret/first WRITE、advance_ring first touch、普通 ring data edge 不被 make_ring init alias 污染，并包含明确负断言。
- 卡住问谁：ring alias 边界问大闸蟹；公开 attr 变化问用户。
- 上下文摘要：用户于 2026-06-17 明确改为 `alloc -> make_ring` 后在 `make_ring` 添加属性。
- 小任务目标：`dma.make_ring` 作为 ring init producer，slot first touch 作为 init consumer，普通 data producer-consumer 仍按现有 ring-aware 规则。
- 非目标：不实现 ring free-slot 生命周期。
- 模块范围：producer-consumer analysis 实现 / spec / pytest。
- 禁止修改面：除 Draft 6 已授权并由架构侧物化的本地 expectation 合同资产外，执行链不得修改 `expectation/`；不得改无关 memory-plan / multi-buffer 实现。
- 合同真源：spec > pytest > expectation 本地合同 > 当前实现。
- 最小功能闭环：`dma.alloc -> dma.make_ring -> dma.current_ring -> dma.reinterpret -> dma.slice` 时 producer attr 写在 `dma.make_ring`，backing `dma.alloc` 无 event attr。
- 示例 / 预期：
  输入 IR：
  ```mlir
  func.func @ring_backing_init_alias(
      %src : !nn.memory<...>, %rhs : !nn.memory<...>, %out : !nn.memory<...>,
      %num : !symbol.int<...>, %bytes : !symbol.int<...>) {
    %pool = "dma.alloc"() : () -> !nn.memory<...>
    %ring = "dma.make_ring"(%pool, %num, %bytes) : (...) -> !dma.ring<...>
    %slot = "dma.current_ring"(%ring) : (...) -> !nn.memory<...>
    %view = "dma.reinterpret"(%slot, ...) : (...) -> !nn.memory<...>
    "dma.slice"(%view, %src, ...) : (...) -> ()
    "kernel.matmul"(%out, %view, %rhs) : (...) -> ()
    func.return
  }
  ```
  预期 IR attr 形态：
  ```mlir
  func.func @ring_backing_init_alias(
      %src : !nn.memory<...>, %rhs : !nn.memory<...>, %out : !nn.memory<...>,
      %num : !symbol.int<...>, %bytes : !symbol.int<...>) {
    %pool = "dma.alloc"() : () -> !nn.memory<...>
    %ring = "dma.make_ring"(%pool, %num, %bytes) {productor = [0]} : (...) -> !dma.ring<...>
    %slot = "dma.current_ring"(%ring) : (...) -> !nn.memory<...>
    %view = "dma.reinterpret"(%slot, ...) : (...) -> !nn.memory<...>
    "dma.slice"(%view, %src, ...) {consumer = [0], productor = [1]} : (...) -> ()
    "kernel.matmul"(%out, %view, %rhs) {consumer = [1]} : (...) -> ()
    func.return
  }
  ```
  预期说明：init edge producer 写在 `%ring` 的 `dma.make_ring`；backing `%pool` 的 `dma.alloc` 不写 event attr；consumer 写在第一条真实 touch `dma.slice`；`dma.current_ring`、`dma.reinterpret` 不写 init event attr；后续读取 `%view` 的 `kernel.matmul` / `dma.copy` 不再消费 make_ring init event，只消费 first WRITE 产生的普通 data event；普通 ring-aware data edge 仍按现有 current/advance 规则输出。示例 event id 以最小片段为例；测试必须断言 alias-only / cursor-only op 无 event attr，以及后续 reader 不消费 make_ring init event。
- 执行步骤：
  1. 建立 init-only make_ring root 映射。
  2. 让 current/advance slot result 在 init-only 表中归属 make_ring init root。
  3. 保持普通 alias_roots / ring-aware dataflow 不变。
  4. 补正反向 pytest；实现文件如有修改，同步文件级说明、`API 列表` 和改动函数注释。
- 验收必过项目：
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 -m pytest -q test/passes/test_producer_consumer_analysis.py -k "ring_backing_init_alias or ring_soft_pipeline_events or single_tile_prologue_epilogue"`
  - 建议新增测试名：`test_producer_consumer_analysis_ring_backing_init_alias_first_slot_write_uses_init_event_once`、`test_producer_consumer_analysis_ring_backing_init_alias_does_not_pollute_ring_data_events`、`test_producer_consumer_analysis_ring_backing_init_alias_current_advance_reinterpret_have_no_event_attrs`。
- 记录要求：记录 init-only alias 与普通 data alias 的隔离证据；必须列出 `kernel.matmul` 不消费 make_ring init event、backing `dma.alloc` 不写 event attr、`loop_first/loop_carried/after_loop` 仍使用分类 attr 且未被主 `productor/consumer` 污染、`current_ring/advance_ring/reinterpret` 无 event attr 的断言证据。

### S3. 更新 spec / pytest / expectation 验收

- 为什么做：公开行为变化必须同步 spec 与公开 pytest，并用用户授权新增的本地 expectation 锁定 alloc first-touch / make_ring init producer 合同。
- 做什么：更新 producer-consumer spec 的 ALLOC first-touch / make_ring init producer 合同，补齐 focused pytest，按实际 diff 补 pipeline 不退化测试；execute 只读运行架构侧已物化的 expectation 合同。
- 不做什么：execute / review / archive_acceptance / merge / 管理员不修改、新建、移动、删除或重命名 `expectation/`。
- 怎么验收：运行 producer-consumer 精确 pytest、必要 pipeline 精确 pytest、`expectation.pass.producer_consumer_analysis`，并记录 import 来源、leaf 名称、hash / manifest 和 scope 外空 diff。
- 卡住问谁：expectation 本体疑似缺口问大闸蟹；公开合同新增问用户。
- 上下文摘要：当前 `expectation/pass/producer_consumer_analysis/**` 是主仓本地 ignored / untracked 合同来源，Draft 6 已由架构侧按用户授权新增 `alloc_first_touch.py` 并按 make_ring 最新语义修订 `ring_backing_init_alias.py`；执行链只能读取、运行、引用和记录。
- 小任务目标：spec、pytest、expectation 三者对 alloc first-touch / make_ring init producer 行为不冲突。
- 非目标：不以 expectation 替代 diff 反推 pytest。
- 模块范围：`spec/pass/producer_consumer_analysis.md`、`test/passes/test_producer_consumer_analysis.py`、必要时 `test/passes/pipeline/test_npu_demo_lowering.py`、架构侧本地 expectation 合同 `expectation/pass/producer_consumer_analysis/{__main__.py,alloc_first_touch.py,ring_backing_init_alias.py}`。
- 禁止修改面：execute / review / archive_acceptance / merge / 管理员不得修改 `expectation/`、外部 SDNN、driver inline、EmitC、无关 staged 计划和无关 dump。
- 合同真源：spec > pytest > expectation 本地合同 > 当前实现。
- 最小功能闭环：新增行为在 spec 中可读、在 pytest 中可机械验证、在 expectation 中不回退既有合同。
- 示例 / 预期：
  ```bash
  PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 -m pytest -q \
    test/passes/test_producer_consumer_analysis.py
  ```
  预期：新增 alloc first-touch / make_ring init producer 正反断言通过；旧 ring-aware `loop_first` / `loop_carried` / `after_loop` 用例仍通过；`expectation.pass.producer_consumer_analysis` exit 0。
- 执行步骤：
  1. 更新 `spec/pass/producer_consumer_analysis.md` 的 ALLOC 与 make_ring init producer 合同。
  2. 补 producer-consumer pytest 的正反断言。
  3. 按实际 diff 判断是否补 pipeline 不退化测试；若补 pipeline 测试，使用精确测试名，不使用过宽 `-k`。
  4. 只读运行 expectation 并记录 import 来源、关键 leaf 名称、`git ls-files --stage` 无输出、`git check-ignore` 命中、必要 hash / manifest 和 scope 外空 diff。
- 验收必过项目：
  - 见 `验收设计`。
  - expectation 预期：`PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=<任务worktree>:/home/lfr/kernelcode_generate python3 -m expectation.pass.producer_consumer_analysis` exit 0；关键 leaf 合同包括 `memory_effect_alias`、`if_branch`、`after_if`、`loop_body`、`after_loop`、`ring_loop_first`、`ring_loop_carried`、`ring_after_loop`、`ring_cursor_current_advance`、`alloc_first_touch`、`ring_backing_init_alias`。
- 记录要求：任务记录写清 pytest、expectation 验收、diff 反推测试、实现文件说明同步、expectation manifest / hash、scope 外空 diff、敏感范围空 diff和 unrelated staged / unstaged 文件隔离。

## 计划自检与返工口径

- 自检：
  - 当前 Draft 0 已指出 `plan/2` 目标路径在当前工作区不存在。
  - 当前 Draft 6 已按用户确认收窄为当前仓库根目录方案，不再把不存在的 SDNN 路径写成可下发任务。
  - 当前 Draft 6 已按用户授权在本地 ignored `expectation/pass/producer_consumer_analysis` 下补充 / 修订合同资产；这些 expectation 默认不会进入远程仓库，但必须作为 execute 合同验收来源记录 manifest / hash。
  - 当前 Draft 6 已移除 C0 / C2 / C3 待确认项；用户已确认 C0=A，`if_branch_*` 只复用现有规则，`driver.inline INIT_EVENT` 不属于本项目考虑事项。
  - 当前 Draft 6 已按用户最新口径把 ring 场景改为 `dma.make_ring {productor=[0]}`，Draft 5 守护请求已由守护确认暂停并作废。
- 返工口径：Draft 6 必须重新完成 subagent strict review 收敛并重新通过 `守护最好的爱莉希雅` 守护最终检验后，才可进入用户最终确认 / 下发流程。

## 待确认项

- 无。用户已确认当前计划只做当前仓库根目录方案；`if_branch_*` first-touch 只复用现有规则，`driver.inline INIT_EVENT` 不属于本项目考虑事项。

## 用户确认与协同约束

- 用户确认来源：
  - 2026-06-15 用户要求参考 `/home/lfr/kernelcode_generate/plan/2` 并按计划书流程推进。
  - 2026-06-15 用户确认选择 A：当前仓库根目录方案。
  - 2026-06-15 用户确认 `if_branch_*` first-touch 只复用现有规则，`driver.inline INIT_EVENT` 不属于本项目考虑事项。
  - 2026-06-16 用户明确要求“应该 添加对应的 expatation，作为验证”，并说明 expectation 默认不会进入远程仓库；据此授权架构侧在本地 ignored `expectation/pass/producer_consumer_analysis` 下补充最小合同资产。
  - 2026-06-17 用户确认 ring 场景新口径：“如果是 alloc make ring，再 make ring 添加属性”。
- 用户已确认事项：
  - 允许进入计划书流程。
  - C0=A：目标工作区选择当前仓库根目录，只做公共 `ProducerConsumerAnalysisPass` / npu-demo 相关合同。
  - 允许架构侧本地补充 / 修订对应 expectation 作为验证；execute 链只能读取、运行、引用和记录，不得修改。
  - `dma.alloc -> dma.make_ring` 场景由 `dma.make_ring` 承接 init producer event；backing `dma.alloc` 不写 event attr。
- 待用户确认项：无。
- 迭代审阅记录：Round 1-A / Round 1-B、Round 2-A / Round 2-B 均不通过，Draft 3 已处理；Round 3-A / Round 3-B 均通过；Draft 4 用户反馈 writeback 已由 Round 4-A / Round 4-B 通过复核；Draft 5 expectation 合同变更的 Round 5/6 已作为历史记录保留，但因用户最新 ring 语义变更不得作为 Draft 6 下发依据；Draft 6 Round 7-A / Round 7-B 已通过，无阻断、无最小需改项、无待确认项。
- 守护最终检验：旧候选请求已暂停并作废；Draft 4 staged 候选已通过但被后续 expectation 合同变更 supersede；Draft 5 守护请求已由守护确认暂停并作废；Draft 6 守护复验已通过。
- 下发门禁：用户已最终确认下发，管理员已创建唯一计划级 execute `T-20260620-e3ed07d4 / alloc-producer-init-edge`；当前计划级链路已推进到 archive_acceptance，下一步为 `merge/归档`。
