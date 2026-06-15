# OpenXLA / Halide / IREE reference research 计划书 Draft 1-R2

## 文档信息

- 计划用途：让唯一计划级 `execute` 在 `ARCHITECTURE/reference/` 新增 OpenXLA、Halide 与 IREE 三个外部项目的长期参考文档，沉淀这些项目在 pass 优化组织、cleanup barrier、fixed-point / invariant、bounds / storage rewrite、target late lowering、dispatch / executable 边界等方面的可借鉴方法，供后续计划学习吸收。
- 当前状态：Draft 1-R2；已吸收 Poincare / Noether Draft 1 strict review 对逐文件章节门禁、reference 目录只允许三份新增文件门禁、排除词负向门禁可执行性的最小需改项，并吸收 Poincare Draft 1-R1 复审对 `## 可借鉴方法` 章节未纳入逐文件门禁的最小需改项；Poincare / Noether Draft 1-R2 strict review 已收敛到无阻断、无最小需改项、无待确认项；可进入守护最终检验，守护通过前不得下发 execute。
- 用户确认来源：
  - 2026-06-08 用户要求继续查看可重构点，并允许网上查找相关项目。
  - 2026-06-08 用户要求“可以出一个计划书，OpenXLA Halide iree 这三个项目的调研参考。按照计划书推进”。
  - 2026-06-08 用户纠正参考方向：不是调试产物、生成参数和编译会话模型，而是这些项目的 pass 优化方法；只看项目代码，不需要下载编译。
  - 2026-06-08 用户进一步澄清：希望在 `/home/lfr/kernelcode_generate/ARCHITECTURE/reference` 增加这几个项目的参考，方便以后学习吸收这些项目的精华。
  - 2026-06-08 用户再次澄清：当前要“出一个计划书，让执行人做这些事情”。
- 计划文件位置：`ARCHITECTURE/plan/reference_projects_openxla_halide_iree_research.md`。
- 目标 `spec`：不适用；本文计划交付架构参考文档，不修改本仓公开 `spec`。
- 目标 `API`：
  - 不新增、不删除、不重命名、不改签名公开 API。
  - 不新增工具入口、脚本参数、pipeline option、include API、稳定错误文本或公开输出合同。
- 目标 `test`：不适用；本计划不修改实现或测试。验收以 markdown 文本核对、链接边界核对、禁止修改面核对和 diff check 为主。
- 目标 `验收资产`：
  - `git diff --check -- ARCHITECTURE/reference ARCHITECTURE/plan/reference_projects_openxla_halide_iree_research.md`
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 -m compileall ARCHITECTURE/reference`
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 -c 'from pathlib import Path; files = [Path("ARCHITECTURE/reference/reference_project_openxla_research.md"), Path("ARCHITECTURE/reference/reference_project_halide_research.md"), Path("ARCHITECTURE/reference/reference_project_iree_research.md")]; required = ["## 功能简介", "## 执行摘要", "## 文档信息", "## 使用示例", "## 调研对象与证据边界", "### 外部证据源", "### 本仓对照点", "### 证据核对矩阵", "## 项目是什么 / 不是什么", "## 可借鉴方法", "## 对本仓的迁移口径", "## 最不该直接照搬的点", "## 自检清单"]; missing = {str(path): [item for item in required if item not in path.read_text(encoding="utf-8")] for path in files}; missing = {path: items for path, items in missing.items() if items}; assert not missing, missing'`
  - `! rg -n "调试产物|生成参数|编译会话模型" ARCHITECTURE/reference/reference_project_openxla_research.md ARCHITECTURE/reference/reference_project_halide_research.md ARCHITECTURE/reference/reference_project_iree_research.md`
  - `git diff --name-only -- expectation .skills agents/standard AGENTS.md TODO.md DONE.md plan/1.md kernel_gen spec test`
  - `git diff --cached --name-only -- expectation .skills agents/standard AGENTS.md TODO.md DONE.md plan/1.md kernel_gen spec test`
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 -c 'import subprocess; allowed = {"ARCHITECTURE/reference/reference_project_openxla_research.md", "ARCHITECTURE/reference/reference_project_halide_research.md", "ARCHITECTURE/reference/reference_project_iree_research.md"}; out = subprocess.check_output(["git", "status", "--porcelain", "--", "ARCHITECTURE/reference"], text=True); seen = set(); bad = [];  [seen.add(line[3:]) if (line[:2] == "??" or line[:2].strip() == "A") and line[3:] in allowed else bad.append(line) for line in out.splitlines()]; assert not bad, bad; assert seen == allowed, seen'`
- 目标 `功能实现`：不适用；目标交付文档为：
  - `ARCHITECTURE/reference/reference_project_openxla_research.md`
  - `ARCHITECTURE/reference/reference_project_halide_research.md`
  - `ARCHITECTURE/reference/reference_project_iree_research.md`
- `expectation/` 授权：本计划不新增、不删除、不移动、不重命名、不修改 `expectation/`；当前无必过 `expectation` 合同验收。
- 外部项目边界：只读查看官方文档和官方 GitHub 源码；不下载、不 clone、不编译外部项目；不引入外部依赖。
- 计划书边界：subagent 收敛、守护最终检验和计划书入档验收角色可按流程回填本计划记录；计划级 `execute` 不得修改本计划书正文。

## 计划级任务

- 计划级任务目标：在不修改公开 API、实现、spec、测试、`expectation/` 和任务状态文件的前提下，只读参考 OpenXLA、Halide 与 IREE 官方源码 / 官方文档，在 `ARCHITECTURE/reference/` 新增三份 reference 调研文档，分别写清项目定位、证据来源、可借鉴的 pass 优化方法、对本仓的迁移口径、禁止直接照搬项、自检清单，并完成 markdown / diff / 禁止修改面验收。
- 任务类型：`execute`。
- 固定流转：`execute -> review -> archive_acceptance/计划书入档验收 -> merge/归档`。
- 失败接续：`review` 不通过回 `execute`；`archive_acceptance` 不通过也回 `execute`；不得另建独立 `refactor` 阶段绕过计划级任务。
- 当前下发前置：
  - 本计划 subagent strict review 收敛到无阻断、无最小需改项、无待确认项。
  - `守护最好的爱莉希雅` 守护最终检验通过。
  - 管理员创建唯一计划级 `execute`；不得拆成三个独立 TODO 任务。

| 计划任务 | 任务类型 | worktree | 记录文件 |
| --- | --- | --- | --- |
| `reference-projects-openxla-halide-iree-research` | `execute` | 管理员下发的新独立 worktree | `agents/codex-multi-agents/log/task_records/2026/24/20260608-reference-projects-openxla-halide-iree-research.md` |

## 迭代审阅记录

### 收敛轮次 1：subagent strict review

- 审阅对象：Draft 1 全文。
- 输入标准包：根 `AGENTS.md`、当前角色 prompt、`agents/standard/计划书标准.md`、`agents/standard/审查规范.md`、`agents/standard/任务记录约定.md`、`agents/standard/协作执行通用规则.md`、Draft 1 全文、用户确认来源、外部证据边界、禁止修改面、验收命令和本轮严格通过口径。
- 严格通过口径：计划必须只要求在 `ARCHITECTURE/reference/` 新增 OpenXLA / Halide / IREE 三份外部参考文档；必须聚焦 pass 优化方法和项目精华；不得把调试产物、生成参数、编译会话模型作为本计划目标；不得修改实现、spec、test、公开 API、`expectation/`、任务状态文件或已有 reference 文档；小任务卡必须可执行；验收必须能证明三份文档存在、证据边界清楚、禁止照搬项明确、敏感目录无 diff；若仍有可执行的边界、可维护性、可读性或验收可信度返工项，则不得通过。
- 审阅任务：
  - Poincare / `019ea31e-c5f1-7cd3-b5d9-bde3c53be95e`：不通过。
  - Noether / `019ea31e-f68a-7c61-8b4f-8383dba450a8`：不通过。
- 发现问题：
  - Poincare / Noether 均指出三份 reference 文档必需章节只用合并 `rg` OR 扫描验证，不能证明每份文档都包含 `外部证据源`、`本仓对照点`、`证据核对矩阵`、`最不该直接照搬`、`自检清单` 等章节。
  - Poincare 指出计划要求不得修改已有 reference 文档，但验收没有证明 `ARCHITECTURE/reference/` diff 只包含三份新增目标文件，误改既有 `nncase` / `rvv_xdsl` / `triton` reference 可能逃过门禁。
  - Poincare / Noether 均指出排除词 `rg -n "调试产物|生成参数|编译会话模型"` 的预期“无命中”与命令退出码冲突；同时 S4 原口径又允许人工判断命中，导致验收不可执行且判定不稳定。
  - Noether 指出敏感目录核对只用 `git diff` / `git diff --cached`，不能发现禁止修改面下的未跟踪新增文件。
- 主线处理：
  - Draft 1-R1 删除合并结构 `rg` 作为必需章节门禁，改为逐文件 `python3 -c` 脚本，分别断言三份 reference 都包含必需章节。
  - Draft 1-R1 增加 `ARCHITECTURE/reference/` 状态门禁，断言该目录只出现三份目标新增文件，允许 untracked 或 staged 新增，不允许 `M/D/R` 既有 reference 文件。
  - Draft 1-R1 将排除词门禁改为 `! rg -n ...`，并删除 S4 中“命中后人工允许”的不稳定口径；三份 reference 不得出现用户明确排除方向词。
  - Draft 1-R1 保留敏感目录 `git diff` / `git diff --cached` 门禁，并补充 `ARCHITECTURE/reference/` 状态门禁覆盖本计划目标目录误改；禁止修改面下的未跟踪文件由敏感目录 status 门禁覆盖。
- 状态：不通过；已形成 Draft 1-R1，需基于最新计划文本发起第二轮 subagent strict review。

### 收敛轮次 2：subagent strict review

- 审阅对象：Draft 1-R1 全文。
- 输入标准包：根 `AGENTS.md`、当前角色 prompt、`agents/standard/计划书标准.md`、`agents/standard/审查规范.md`、`agents/standard/任务记录约定.md`、`agents/standard/协作执行通用规则.md`、Draft 1-R1 全文、收敛轮次 1 问题和主线处理、用户确认来源、外部证据边界、禁止修改面、验收命令和本轮严格通过口径。
- 严格通过口径：确认 Draft 1-R1 已收口逐文件章节门禁、reference 目录只允许三份新增文件门禁、排除词负向门禁和禁止修改面 untracked 覆盖；计划仍只要求唯一计划级 execute 新增三份 `ARCHITECTURE/reference/` 文档；不得修改实现、spec、test、公开 API、`expectation/` 或任务状态文件；若仍有阻断、最小需改项或待用户确认项，则不得通过。
- 审阅任务：
  - Poincare / `019ea31e-c5f1-7cd3-b5d9-bde3c53be95e`：不通过。
  - Noether / `019ea31e-f68a-7c61-8b4f-8383dba450a8`：通过；无阻断、无最小需改项、无待确认项。
- 发现问题：
  - Poincare 指出计划目标要求三份 reference 都包含“可借鉴方法”，但 Draft 1-R1 的逐文件章节门禁未断言 `## 可借鉴方法`，执行人可能提交缺少核心 pass 优化方法 / 项目精华章节的文档仍通过验收。
- 主线处理：
  - Draft 1-R2 将 `## 可借鉴方法` 加入两处逐文件 `python3 -c` 章节门禁的 `required` 列表，确保三份 reference 都必须包含该核心章节。
- 状态：不通过；已形成 Draft 1-R2，需基于最新计划文本发起第三轮 subagent strict review。

### 收敛轮次 3：subagent strict review

- 审阅对象：Draft 1-R2 全文。
- 输入标准包：根 `AGENTS.md`、当前角色 prompt、`agents/standard/计划书标准.md`、`agents/standard/审查规范.md`、`agents/standard/任务记录约定.md`、`agents/standard/协作执行通用规则.md`、Draft 1-R2 全文、收敛轮次 2 问题和主线处理、用户确认来源、外部证据边界、禁止修改面、验收命令和本轮严格通过口径。
- 严格通过口径：确认 Draft 1-R2 已把 `## 可借鉴方法` 纳入逐文件章节门禁；R1 / R2 问题必须完全收口；计划仍只要求唯一计划级 execute 新增三份 `ARCHITECTURE/reference/` 文档；不得修改实现、spec、test、公开 API、`expectation/` 或任务状态文件；若仍有阻断、最小需改项或待用户确认项，则不得通过。
- 审阅任务：
  - Poincare / `019ea31e-c5f1-7cd3-b5d9-bde3c53be95e`：通过；无阻断、无最小需改项、无待确认项。
  - Noether / `019ea31e-f68a-7c61-8b4f-8383dba450a8`：通过；无阻断、无最小需改项、无待确认项。
- 发现问题：无。
- 主线处理：无需继续修订；Poincare / Noether 均确认 Draft 1-R2 已把 `## 可借鉴方法` 加入两处逐文件章节门禁，R1 / R2 验收可信度问题已收口，计划仍只要求唯一计划级 `execute` 在 `ARCHITECTURE/reference/` 新增三份 reference 文档，未要求修改实现、`spec`、`test`、公开 API、`expectation/` 或任务状态文件。
- 状态：通过；所有已发起 subagent strict review 均收敛为无阻断、无最小需改项、无待确认项，可进入守护最终检验。

### subagent 收敛结论

- 已发起或计划要求的审阅任务：
  - 收敛轮次 1：Poincare / `019ea31e-c5f1-7cd3-b5d9-bde3c53be95e`；状态不通过，最小需改项已并入 Draft 1-R1。
  - 收敛轮次 1：Noether / `019ea31e-f68a-7c61-8b4f-8383dba450a8`；状态不通过，最小需改项已并入 Draft 1-R1。
  - 收敛轮次 2：Poincare / `019ea31e-c5f1-7cd3-b5d9-bde3c53be95e`；状态不通过，最小需改项已并入 Draft 1-R2。
  - 收敛轮次 2：Noether / `019ea31e-f68a-7c61-8b4f-8383dba450a8`；状态通过，无阻断、无最小需改项、无待确认项。
  - 收敛轮次 3：Poincare / `019ea31e-c5f1-7cd3-b5d9-bde3c53be95e`；状态通过，无阻断、无最小需改项、无待确认项。
  - 收敛轮次 3：Noether / `019ea31e-f68a-7c61-8b4f-8383dba450a8`；状态通过，无阻断、无最小需改项、无待确认项。
- 收敛结论：已收敛；所有已发起或计划要求的 subagent strict review 均无阻断、无最小需改项、无待确认项。
- 遗留项：无；可请求 `守护最好的爱莉希雅` 守护最终检验。

### 守护最终检验

- 检验对象：`守护最好的爱莉希雅`。
- 检验范围：subagent 收敛结论、公开 API 状态、`expectation/` 授权、禁止修改面、验收命令、小任务卡、待确认项和计划索引状态。
- 必过门禁：所有已发起或计划要求的 subagent strict review 均无阻断、无最小需改项、无待确认项；用户待决策项为无；计划不越权修改 `expectation/`、实现、spec、test 或任务状态文件；计划文件进入 tracked / index diff。
- 当前状态：已执行。
- 结论：通过。
- 阻断项：无。
- 最小需改项：无。
- 待确认项：无。
- 关键证据：
  - Poincare / `019ea31e-c5f1-7cd3-b5d9-bde3c53be95e` 与 Noether / `019ea31e-f68a-7c61-8b4f-8383dba450a8` 三轮 subagent strict review 已收敛，R3 均通过且无阻断、无最小需改项、无待确认项。
  - 用户确认来源已写入正文：本计划只在 `ARCHITECTURE/reference/` 新增 OpenXLA、Halide、IREE 三份 reference 文档；只参考项目代码 / 官方文档，不下载、不编译，不回到调试产物、生成参数或编译会话模型方向。
  - 公开 API 状态明确为不新增、不删除、不重命名、不改签名；不新增工具入口、脚本参数、pipeline option、include API、稳定错误文本或公开输出合同。
  - `expectation/` 授权明确为不新增、不删除、不移动、不重命名、不修改；当前无必过 `expectation` 合同验收。
  - 验收设计覆盖三份 reference 文件存在性、逐文件章节门禁、排除词负向门禁、`ARCHITECTURE/reference/` 只允许三份目标新增文件、敏感禁止修改面 unstaged / staged / untracked 核对和 diff check。
  - 计划文件已进入 tracked / index diff；cached name-status 为 `A`，status 为 `A`，不是 ignored-only。
- 是否允许通知管理员创建唯一计划级 execute：允许。

## 计划书入档验收 / 复验 / 修复复核记录

- 结论人：不要啊教练 / 2026-06-08 archive_acceptance。
- 结论：通过；无阻断项、无最小需改项。
- 验证基线：`HEAD=7cddf72301dcba958fcc0f0cedd34e09b0f24aa0`，`origin/main=7cddf72301dcba958fcc0f0cedd34e09b0f24aa0`，`merge-base=7cddf72301dcba958fcc0f0cedd34e09b0f24aa0`，ahead / behind 为 `0 0`。
- 执行目录：`/home/lfr/kernelcode_generate/wt-20260608-reference-projects-openxla-halide-iree-research`。
- 同步结果：latest main 已对齐；staged candidate 只包含本计划文件、三份 `ARCHITECTURE/reference/reference_project_*_research.md` 和任务记录，unstaged diff 为空。
- 合同验收摘要：当前计划无必过 `expectation`；`expectation/` 无 unstaged / staged / status diff，本次不运行 expectation 作为通过依据。
- 最小阻断项或通过摘要：三份 reference 文档存在且均含计划要求章节；官方证据源限定在 `openxla.org` / `github.com/openxla/xla`、`halide-lang.org` / `github.com/halide/Halide`、`iree.dev` / `github.com/iree-org/iree`；用户排除方向负向门禁无命中；内部 markdown link、文本门禁、`git diff --check` / `--cached --check`、敏感目录空 diff、`ARCHITECTURE/reference/` 只允许三份目标新增文件门禁均通过；可按计划级链路进入 `merge`，不得由入档验收角色直接合并。

## 计划目标

- 新增 `ARCHITECTURE/reference/reference_project_openxla_research.md`，沉淀 OpenXLA / XLA 的 HLO pass pipeline、fixed-point、invariant checker、cleanup placement 与 target late lowering 方法。
- 新增 `ARCHITECTURE/reference/reference_project_halide_research.md`，沉淀 Halide 的 algorithm / schedule 分离、bounds inference、simplify placement、storage folding / flattening 与 target codegen 边界。
- 新增 `ARCHITECTURE/reference/reference_project_iree_research.md`，沉淀 IREE 的 Flow / Codegen 分层 pipeline、cleanup / legality gate、dispatch / executable 边界和 target backend 分层。
- 三份文档都必须写清：
  - 功能简介。
  - 执行摘要。
  - 文档信息。
  - 使用示例。
  - 调研对象与证据边界。
  - 外部证据源。
  - 本仓对照点。
  - 证据核对矩阵。
  - 项目是什么 / 不是什么。
  - 可借鉴方法。
  - 对本仓的迁移口径。
  - 最不该直接照搬的点。
  - 后续计划引用本文时的自检清单。
- 不把这三份 reference 文档写成当前实现完成状态，不要求执行人改 `npu-demo-lowering` 或其它实现。

## 当前基线

- 当前 `ARCHITECTURE/reference/` 已有外部项目参考文档：
  - `ARCHITECTURE/reference/reference_project_nncase_research.md`
  - `ARCHITECTURE/reference/reference_project_rvv_xdsl_research.md`
  - `ARCHITECTURE/reference/reference_project_triton_research.md`
- 当前缺口：没有 OpenXLA、Halide、IREE 的独立长期 reference 文档；相关参考只散落在 `ARCHITECTURE/plan/npu_demo_pass_optimization_method_refactor.md` 的具体计划上下文中，不适合作为后续所有计划的通用知识库。
- 当前公开 API：本计划不涉及公开 API。
- 当前实现入口：不涉及实现。
- 当前测试与验收资产：无实现测试；采用 markdown 文本核对、diff check 和禁止修改面核对。
- 当前已知风险：
  - 外部项目 `main` 分支持续变化，文档不得固定性能、pass 顺序或内部 flag 为本仓稳定事实。
  - reference 文档容易写成“照搬外部系统”或“当前本仓已经具备能力”，执行时必须明确证据边界和不可照搬项。
  - 本计划与 `npu-demo-pass-optimization-method-refactor` 计划有关联，但本计划只建设 reference 知识库，不下发或替代 npu-demo 实现重构计划。

## 方案比较与选型

### 方案 A：继续把 OpenXLA / Halide / IREE 参考写在 npu-demo 重构计划里

- 内容：只在 `ARCHITECTURE/plan/npu_demo_pass_optimization_method_refactor.md` 保留外部项目参考。
- 缺点：参考资料绑定单个计划，后续 CUDA、memory、pass manager、source bundle 等计划复用成本高；也容易把通用外部精华误解为 npu-demo 专属前置。
- 结论：不采用。

### 方案 B：一次性在 `ARCHITECTURE/reference/` 新增三份独立项目参考文档

- 内容：每个项目一份 reference 文档，沿用现有 `reference_project_*_research.md` 风格，写清证据、边界、可借鉴点和不可照搬项。
- 优点：可被后续计划复用；不触碰公开 API 和实现；边界清晰。
- 风险：三份文档质量不均，或混入调试产物 / 编译会话方向。
- 风险处理：计划验收要求三份文档结构一致，聚焦 pass 优化方法和项目精华，并用文本门禁检查用户明确排除方向。
- 结论：采用。

### 方案 C：新增一个总览文档，不拆三份项目文档

- 内容：只创建一个 `reference_projects_pass_optimization_research.md` 总览。
- 缺点：三个项目定位差异大，证据源和不可照搬项不同，单文档会变长且不利于后续按项目引用。
- 结论：不采用；可在未来 reference 索引计划中另做总览。

## 公开 API 设计

### 功能简介

- 本计划只新增架构参考文档，不新增公开 API。

### API 列表

- 无。

### API 变更

- 不新增 API。
- 不删除 API。
- 不重命名 API。
- 不修改参数顺序、默认值、返回值、工具参数、pipeline registry 名称、公开错误文本或稳定输出格式。

## 完成态定义

- `ARCHITECTURE/reference/reference_project_openxla_research.md` 存在，内容聚焦 OpenXLA / XLA 的 HLO pass pipeline、fixed-point、invariant checker、cleanup placement、target late lowering 和本仓可迁移口径。
- `ARCHITECTURE/reference/reference_project_halide_research.md` 存在，内容聚焦 Halide 的 algorithm / schedule 分离、bounds inference、simplify placement、storage rewrite 和本仓可迁移口径。
- `ARCHITECTURE/reference/reference_project_iree_research.md` 存在，内容聚焦 IREE 的 Flow / Codegen 分层 pipeline、cleanup / legality gate、dispatch / executable 边界和本仓可迁移口径。
- 三份文档都使用官方文档 / 官方 GitHub 源码作为外部证据源，并明确上游 `main` 会变化，本文只记录能力类别和设计边界。
- 三份文档都明确“不直接照搬”的内容，避免后续计划把外部 runtime、完整 compiler stack、debug tooling 或 schedule language 写成本仓默认目标。
- 不修改 `kernel_gen/`、`spec/`、`test/`、`expectation/`、`.skills/`、`agents/standard/`、`AGENTS.md`、`TODO.md`、`DONE.md`、`plan/1.md`。

## 验收设计

### Diff 反推测试 / 文本核对

- `git diff --check -- ARCHITECTURE/reference ARCHITECTURE/plan/reference_projects_openxla_halide_iree_research.md`
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 -m compileall ARCHITECTURE/reference`
- `test -f ARCHITECTURE/reference/reference_project_openxla_research.md`
- `test -f ARCHITECTURE/reference/reference_project_halide_research.md`
- `test -f ARCHITECTURE/reference/reference_project_iree_research.md`
- `rg -n "OpenXLA|HloPassPipeline|HloPassFix|invariant|target late" ARCHITECTURE/reference/reference_project_openxla_research.md`
- `rg -n "Halide|schedule|bounds|simplify|storage" ARCHITECTURE/reference/reference_project_halide_research.md`
- `rg -n "IREE|Flow|Codegen|dispatch|executable|HAL" ARCHITECTURE/reference/reference_project_iree_research.md`
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 -c 'from pathlib import Path; files = [Path("ARCHITECTURE/reference/reference_project_openxla_research.md"), Path("ARCHITECTURE/reference/reference_project_halide_research.md"), Path("ARCHITECTURE/reference/reference_project_iree_research.md")]; required = ["## 功能简介", "## 执行摘要", "## 文档信息", "## 使用示例", "## 调研对象与证据边界", "### 外部证据源", "### 本仓对照点", "### 证据核对矩阵", "## 项目是什么 / 不是什么", "## 可借鉴方法", "## 对本仓的迁移口径", "## 最不该直接照搬的点", "## 自检清单"]; missing = {str(path): [item for item in required if item not in path.read_text(encoding="utf-8")] for path in files}; missing = {path: items for path, items in missing.items() if items}; assert not missing, missing'`
  - 预期：三份 reference 文档分别包含全部必需章节。
- `! rg -n "调试产物|生成参数|编译会话模型" ARCHITECTURE/reference/reference_project_openxla_research.md ARCHITECTURE/reference/reference_project_halide_research.md ARCHITECTURE/reference/reference_project_iree_research.md`
  - 预期：无命中；不得把用户明确排除方向写入 reference 主题、非目标或边界说明。
- `git diff --name-only -- expectation .skills agents/standard AGENTS.md TODO.md DONE.md plan/1.md kernel_gen spec test`
  - 预期：无输出。
- `git diff --cached --name-only -- expectation .skills agents/standard AGENTS.md TODO.md DONE.md plan/1.md kernel_gen spec test`
  - 预期：无输出。
- `git status --porcelain -- expectation .skills agents/standard AGENTS.md TODO.md DONE.md plan/1.md kernel_gen spec test`
  - 预期：无输出；覆盖禁止修改面下的未跟踪文件。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 -c 'import subprocess; allowed = {"ARCHITECTURE/reference/reference_project_openxla_research.md", "ARCHITECTURE/reference/reference_project_halide_research.md", "ARCHITECTURE/reference/reference_project_iree_research.md"}; out = subprocess.check_output(["git", "status", "--porcelain", "--", "ARCHITECTURE/reference"], text=True); seen = set(); bad = [];  [seen.add(line[3:]) if (line[:2] == "??" or line[:2].strip() == "A") and line[3:] in allowed else bad.append(line) for line in out.splitlines()]; assert not bad, bad; assert seen == allowed, seen'`
  - 预期：`ARCHITECTURE/reference/` 只出现三份目标新增文件；不得修改、删除、重命名既有 reference 文档。

### 合同验收

- 当前无必过 `expectation`。
- `expectation/` 只读核对，不计入 Diff 反推测试。

## 计划内小任务

### S1：新增 OpenXLA reference 文档

- 为什么做：OpenXLA 的 HLO pass pipeline、fixed-point、invariant checker 与 target compiler pipeline 是后续 pass 组织和校验方法的重要参考。
- 做什么：创建 `ARCHITECTURE/reference/reference_project_openxla_research.md`，写清 OpenXLA / XLA 的项目定位、证据来源、可借鉴方法、迁移口径和不可照搬项。
- 不做什么：不引入 OpenXLA 依赖；不新增 PassManager API；不把 XLA pass 名或 debug tooling 写成本仓稳定合同。
- 怎么验收：运行 OpenXLA 文档 `test -f`、关键词 `rg`、结构章节核对和 diff check。
- 卡住问谁：外部证据不足或项目定位不清问架构师；需要新增本仓 API 或工具参数时问用户。
- 上下文摘要：当前 npu-demo 重构计划引用了 OpenXLA 方法，但缺少独立 reference 文档供后续计划复用。
- 小任务目标：新增 OpenXLA reference 文档并通过文本验收。
- 非目标：不修改 `npu-demo-lowering`、`PassManager`、spec、test 或 `expectation/`。
- 模块范围：`ARCHITECTURE/reference/`。
- 禁止修改面：`expectation/`、`.skills/`、`agents/standard/`、`AGENTS.md`、`TODO.md`、`DONE.md`、`plan/1.md`、`kernel_gen/`、`spec/`、`test/`、本计划书。
- 合同真源：用户确认 > 本计划 > 官方 OpenXLA 文档 / 官方 GitHub 源码 > 本仓现有 reference 风格。
- 最小功能闭环：文档能回答 OpenXLA 借鉴什么、不能照搬什么、后续计划引用时要检查什么。
- 执行步骤：
  1. 只读核对 OpenXLA 官方文档和官方源码链接。
  2. 新增 `reference_project_openxla_research.md`。
  3. 写清 HLO pass pipeline、fixed-point、invariant checker、cleanup placement、target late lowering。
  4. 写清不引入 OpenXLA 依赖、不新增 pass manager API、不复制 debug tooling。
  5. 运行验收文本命令并记录结果。
- 验收必过项目：本计划“验收设计”中 OpenXLA 相关 `test -f`、`rg`、diff check 和禁止修改面命令。
- 记录要求：写清外部证据源、未下载/未编译、未改公开 API、未改 `expectation/`。

### S2：新增 Halide reference 文档

- 为什么做：Halide 的 algorithm / schedule 分离、bounds inference、simplify placement 和 storage rewrite 能为本仓 tile、memory、canonicalize 放置提供长期参考。
- 做什么：创建 `ARCHITECTURE/reference/reference_project_halide_research.md`，写清 Halide 项目定位、证据来源、可借鉴方法、迁移口径和不可照搬项。
- 不做什么：不引入 Halide schedule language、autoscheduler、runtime、bounds solver 或 codegen backend。
- 怎么验收：运行 Halide 文档 `test -f`、关键词 `rg`、结构章节核对和 diff check。
- 卡住问谁：bounds / schedule 迁移边界不清问架构师；需要新增公开 API、dialect 语义或 tool option 时问用户。
- 上下文摘要：当前本仓 memory / tile / pipeline 任务需要长期区分算法语义、调度策略、运行时 shape 和 target 资源。
- 小任务目标：新增 Halide reference 文档并通过文本验收。
- 非目标：不修改 `SymbolDim`、memory pass、pipeline、spec、test 或 `expectation/`。
- 模块范围：`ARCHITECTURE/reference/`。
- 禁止修改面：`expectation/`、`.skills/`、`agents/standard/`、`AGENTS.md`、`TODO.md`、`DONE.md`、`plan/1.md`、`kernel_gen/`、`spec/`、`test/`、本计划书。
- 合同真源：用户确认 > 本计划 > 官方 Halide 文档 / 官方 GitHub 源码 > 本仓现有 reference 风格。
- 最小功能闭环：文档能回答 Halide 借鉴什么、不能照搬什么、后续计划引用时要检查什么。
- 执行步骤：
  1. 只读核对 Halide 官方文档和官方源码链接。
  2. 新增 `reference_project_halide_research.md`。
  3. 写清 algorithm / schedule 分离、bounds inference、simplify placement、storage folding / flattening。
  4. 写清不新增 schedule language、autoscheduler、bounds solver 或 runtime。
  5. 运行验收文本命令并记录结果。
- 验收必过项目：本计划“验收设计”中 Halide 相关 `test -f`、`rg`、diff check 和禁止修改面命令。
- 记录要求：写清外部证据源、未下载/未编译、未改公开 API、未改 `expectation/`。

### S3：新增 IREE reference 文档

- 为什么做：IREE 的 Flow / Codegen 分层 pipeline、cleanup / legality gate、dispatch / executable 边界和 target backend 分层能为本仓 host/device/source bundle 边界提供长期参考。
- 做什么：创建 `ARCHITECTURE/reference/reference_project_iree_research.md`，写清 IREE 项目定位、证据来源、可借鉴方法、迁移口径和不可照搬项。
- 不做什么：不引入 Flow / Stream / HAL / VM dialect，不引入 IREE runtime、HAL executable 或 target plugin 体系。
- 怎么验收：运行 IREE 文档 `test -f`、关键词 `rg`、结构章节核对和 diff check。
- 卡住问谁：dispatch / executable 与本仓 host/device 边界映射不清问架构师；需要新增 runtime、source bundle 格式或公开 API 时问用户。
- 上下文摘要：当前本仓已有 `npu_demo` / `cuda_sm86` 后端与 source bundle，需要长期保持 high-level IR、target lowering 和 emitter 边界清楚。
- 小任务目标：新增 IREE reference 文档并通过文本验收。
- 非目标：不修改 CUDA / npu_demo 实现、source bundle、pipeline、spec、test 或 `expectation/`。
- 模块范围：`ARCHITECTURE/reference/`。
- 禁止修改面：`expectation/`、`.skills/`、`agents/standard/`、`AGENTS.md`、`TODO.md`、`DONE.md`、`plan/1.md`、`kernel_gen/`、`spec/`、`test/`、本计划书。
- 合同真源：用户确认 > 本计划 > 官方 IREE 文档 / 官方 GitHub 源码 > 本仓现有 reference 风格。
- 最小功能闭环：文档能回答 IREE 借鉴什么、不能照搬什么、后续计划引用时要检查什么。
- 执行步骤：
  1. 只读核对 IREE 官方文档和官方源码链接。
  2. 新增 `reference_project_iree_research.md`。
  3. 写清 Flow / Codegen pipeline、cleanup / legality gate、dispatch / executable、target backend 分层。
  4. 写清不引入 IREE runtime、HAL executable、Flow / Stream / HAL / VM dialect。
  5. 运行验收文本命令并记录结果。
- 验收必过项目：本计划“验收设计”中 IREE 相关 `test -f`、`rg`、diff check 和禁止修改面命令。
- 记录要求：写清外部证据源、未下载/未编译、未改公开 API、未改 `expectation/`。

### S4：整体一致性、禁止修改面和任务记录收口

- 为什么做：本计划是 reference 知识库建设，必须证明没有混入实现、spec、test、API 或合同资产改动。
- 做什么：统一三份文档结构和口径，执行验收设计全部命令，写完整任务记录。
- 不做什么：不运行全量 `expectation`；不修改本计划书正文；不下发 npu-demo 重构任务。
- 怎么验收：全部 diff check、compileall、`rg`、敏感目录核对命令通过。
- 卡住问谁：流程状态和 worktree 问管理员；验收口径问架构师；公开 API 或 `expectation/` 授权问用户。
- 上下文摘要：reference 文档会被后续计划引用，必须避免证据边界含糊或把外部能力写成本仓当前能力。
- 小任务目标：完成三份 reference 文档的一致性验收和任务记录闭环。
- 非目标：不修改三份 reference 之外的业务文件；不改计划书；不创建额外 TODO。
- 模块范围：`ARCHITECTURE/reference/` 与任务记录文件。
- 禁止修改面：`expectation/`、`.skills/`、`agents/standard/`、`AGENTS.md`、`TODO.md`、`DONE.md`、`plan/1.md`、`kernel_gen/`、`spec/`、`test/`、本计划书。
- 合同真源：本计划 > 三份 reference 文档 > 验收命令 > 任务记录。
- 最小功能闭环：三份文档存在、结构一致、主题聚焦、敏感目录无 diff、记录完整。
- 执行步骤：
  1. 核对三份文档都包含必需章节。
  2. 运行本计划验收设计全部命令。
  3. 运行排除词负向门禁；若命中则修正文档，不做人工放行。
  4. 核对禁止修改面 unstaged / staged / untracked 状态均为空，并核对 `ARCHITECTURE/reference/` 只包含三份目标新增文件。
  5. 在任务记录写 `执行前阅读`、`最小功能闭环`、`Diff 反推自测`、`减法检查`、`自检`。
- 验收必过项目：本计划“验收设计”全部命令；当前无必过 `expectation`。
- 记录要求：写清新增文件清单、外部证据源、未下载/未编译、未改公开 API、未改实现/spec/test/expectation、未修改任务状态文件。

## 计划自检与返工口径

- 自检：
  - 公开 API：不新增、不删除、不重命名、不改签名。
  - `expectation/`：无授权改动，当前无必过合同验收。
  - 计划级任务：唯一 execute，三份 reference 文档作为计划内小任务卡，不创建三个独立 TODO。
  - 验收：以 markdown / 文本 / diff / 禁止修改面核对为主，符合纯文档任务边界。
  - 禁止修改面：已显式列出 `expectation/`、`.skills/`、`agents/standard/`、`AGENTS.md`、`TODO.md`、`DONE.md`、`plan/1.md`、`kernel_gen/`、`spec/`、`test/`、本计划书。
  - 待确认项：当前无。
- 返工口径：只要 subagent、守护、review 或 archive_acceptance 指出仍有可执行的边界、证据、可读性、可维护性、测试有效性或验收可信度问题，就回计划修订或 execute 返工，不得下发或归档。

## 待确认项

- 当前无用户待确认项。
- 若 execute 或 review 发现必须新增公开 API、修改 `kernel_gen/`、修改 `spec/`、修改 `test/`、修改 `expectation/`、新增工具参数、改变 dump / source bundle 格式，必须暂停并形成待确认项交用户确认。

## 用户确认与协同约束

- 本计划只建设 `ARCHITECTURE/reference/` 知识库，不执行 npu-demo pass 重构。
- 本计划只参考 OpenXLA、Halide、IREE 的项目精华和 pass 优化方法；不得把调试产物、生成参数或编译会话模型作为本计划目标。
- 本计划只要求只读查看外部项目代码和官方文档，不下载、不编译外部项目。
- subagent strict review 收敛前：不得请求守护最终检验，不得创建 execute。
- 下发前：必须由 `守护最好的爱莉希雅` 执行守护最终检验，管理员才允许创建唯一计划级 `execute`。
- 管理员不得向计划负责人或无关角色推送无行动要求的计划进度；只在需要确认、执行、审查、验收或合并动作时点名当前责任人。
