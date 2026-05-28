# reference project research docs task record

时间：2026-05-29 02:09 +0800
经办人：榕
任务：T-20260529-8f034aee / execute / reference-project-research-docs
任务目标：创建独立 execute 任务，交由执行人审查并收口 Triton 与 nncase 两份 `ARCHITECTURE/reference` 调研文档；完成后按标准流转进入 review，review 通过后进入 merge。
改动：
- 新建 worktree：`/home/lfr/kernelcode_generate/wt-20260529-reference-project-research-docs`，分支：`task/reference-project-research-docs`。
- 将待审调研文档放入任务 worktree：
  - `ARCHITECTURE/reference/reference_project_triton_research.md`
  - `ARCHITECTURE/reference/reference_project_nncase_research.md`
- 通过任务脚本创建 execute 任务：`T-20260529-8f034aee`。
验证：
- `git worktree add -b task/reference-project-research-docs /home/lfr/kernelcode_generate/wt-20260529-reference-project-research-docs main`：退出码 0。
- `git status --short --untracked-files=all -- ARCHITECTURE/reference/reference_project_triton_research.md ARCHITECTURE/reference/reference_project_nncase_research.md`：主仓对应调研文档无未跟踪残留。
- `git status --short --untracked-files=all -- ARCHITECTURE/reference/reference_project_triton_research.md ARCHITECTURE/reference/reference_project_nncase_research.md`（任务 worktree）：两份调研文档为新增待审文件。
- `bash skills/codex-multi-agents/scripts/codex-multi-agents-task.sh -file TODO.md -new ...`：退出码 0，返回 `OK: new T-20260529-8f034aee`。
自检：
- 本轮只创建任务、任务 worktree 和任务初始记录，不修改 `expectation/`、`.skills/`、`agents/standard/`、`AGENTS.md`。
- 调研文档为文档类 diff，不涉及公开 API、实现文件、测试文件或合同资产。
- 后续执行人必须在任务 worktree 内补齐执行记录、自检、Diff 反推自测，并核对敏感目录空 diff。
结论：任务已创建，待分发给执行人。

时间：2026-05-29 02:12 +0800
经办人：榕
任务：T-20260529-8f034aee / execute / reference-project-research-docs
任务目标：确认任务运行态与实际指派，并补发执行口径。
改动：
- 核对 `TODO.md` 后确认任务已进入 `正在执行的任务`，实际指派为 `咯咯咯`。
- 通过 `codex-multi-agents-tmux.sh -talk` 向 `咯咯咯` 补发执行说明：仅处理两份 reference 调研文档，核对来源、证据边界、本仓映射、路径引用、敏感目录空 diff，完成后回报管理员进入 review，不直接 merge。
- 说明：尝试再次 `-dispatch` 到 `小李飞刀` 时脚本返回 `ERROR(3): task already exists in running list: T-20260529-8f034aee`；随后按 TODO 现场确认实际运行任务，无需重复分发。
验证：
- `bash skills/codex-multi-agents/scripts/codex-multi-agents-task.sh -file TODO.md -status -doing`：退出码 0，显示 `T-20260529-8f034aee` 为 `execute / 进行中 / 指派=咯咯咯`。
- `bash skills/codex-multi-agents/scripts/codex-multi-agents-tmux.sh -talk ... -to 咯咯咯 ...`：退出码 0，返回 `OK: talk 神秘人 -> 咯咯咯 (咯咯咯)`。
自检：
- 当前实际执行人是 `咯咯咯`，属于计划级 execute 职责角色；任务类型为 `execute`，职责匹配。
- `小李飞刀` 当前已有另一个 `execute` 任务，不再重复占用。
结论：任务已处于 execute 进行中，执行口径已补发给 `咯咯咯`；后续应由执行人完成记录与文档收口，再进入 review。

时间：2026-05-29 02:26 +0800
经办人：咯咯咯
任务：T-20260529-8f034aee / execute / reference-project-research-docs
任务目标：只处理两份 reference 调研文档，审查并必要收口官方来源链接、证据边界、本仓映射、可维护性、路径引用和敏感目录空 diff；完成后进入 review，不合并。
执行前阅读记录：
- 已读个人提示词：`agents/codex-multi-agents/agents/咯咯咯/咯咯咯.prompt.md`。
- 已读根规则：`AGENTS.md`。
- 已读标准规则：`agents/standard/任务记录约定.md`、`agents/standard/协作执行通用规则.md`。
- 已读任务记录：`agents/codex-multi-agents/log/task_records/2026/22/20260529-reference-project-research-docs.md`。
- 已读并核对目标文档：`ARCHITECTURE/reference/reference_project_triton_research.md`、`ARCHITECTURE/reference/reference_project_nncase_research.md`。
- 本任务未下发独立计划书；以管理员任务目标、任务记录和当前两份 reference 文档为执行边界。
最新同步现场：
- 执行目录：`/home/lfr/kernelcode_generate/wt-20260529-reference-project-research-docs`。
- `git fetch origin --prune` 后：`HEAD=f1241d90456408d6fd033937dd2e8ce9db1b9041`，`origin/main=f1241d90456408d6fd033937dd2e8ce9db1b9041`，`merge-base=f1241d90456408d6fd033937dd2e8ce9db1b9041`，ahead/behind=`0/0`。
- 初始候选状态仅包含两份 reference 文档和本任务记录，未发现 `expectation/`、`.skills/`、`agents/standard/`、`AGENTS.md`、`TODO.md`、`DONE.md` 候选 diff。
最小功能闭环：
- `ARCHITECTURE/reference/reference_project_triton_research.md`：补齐 `功能简介 / 执行摘要 / 文档信息 / 使用示例 / 调研对象与证据边界` 结构；新增“证据核对矩阵”，把 block program、`tl.constexpr`、matmul tail、autotune/config、backend stage、debug dump/reproducer 等结论逐项绑定官方来源和证据边界；补充上游 `main` 移动源边界与本仓公开 API / `expectation/` 转化必须另走确认流程。
- `ARCHITECTURE/reference/reference_project_nncase_research.md`：新增“证据核对矩阵”，把模型编译器定位、Python wrapper 编译闭环、`CompileOptions` / PTQ / dump / preprocess、ShapeBucket、stage dump、KPU 源码边界逐项绑定官方来源和证据边界；补充上游 `master` 移动源边界。
- 路径引用收口：确认两份文档内本仓相对链接均存在；将 `kernel/dump/` 从不存在的 tracked 链接改为“运行 demo 后生成”的产物目录说明。
- 证据边界收口：明确 Triton / nncase 调研只作为设计样本，不主张直接依赖外部项目，不把未来能力写成本仓当前已具备能力。
改动：
- 修改 `ARCHITECTURE/reference/reference_project_triton_research.md`。
- 修改 `ARCHITECTURE/reference/reference_project_nncase_research.md`。
- 追加本执行记录。
验证：
- `python3` 官方来源核对脚本访问 Triton 官方文档 8 个入口：全部 `OK 200`，覆盖编程模型、vector add、matmul、`triton.jit`、`triton.autotune`、`triton.Config`、language API、dialect docs。
- `curl -L --connect-timeout 10 --max-time 30` 核对 GitHub 仓库根入口：`https://github.com/triton-lang/triton`、`https://github.com/kendryte/nncase` 均 `OK 200`。
- `curl -L --connect-timeout 10 --max-time 25` 核对 GitHub blob 来源 12 个入口：Triton compiler/autotuner/NVIDIA backend/AMD backend 与 nncase USAGE_v2/shape_bucket/MixQuant/FAQ/Python wrapper/Compiler/CompileOptions/CompileSession 均 `OK 200`。
- `python3` 本仓相对链接核对脚本：两份文档内所有 markdown 相对链接均 `OK`；`kernel/dump/` 已不再作为 tracked 链接。
- `rg -n '^(## 功能简介|## 执行摘要|## 文档信息|## 使用示例|## 调研对象与证据边界|### 证据核对矩阵)|GitHub `main`|GitHub `master`|生成产物目录 `kernel/dump/`' ARCHITECTURE/reference/reference_project_triton_research.md ARCHITECTURE/reference/reference_project_nncase_research.md`：退出码 0，确认结构、证据矩阵和移动源边界已落位。
- `rg -n '直接引入 Triton|直接依赖 nncase|当前已有 PTQ|当前已支持混合量化|Caffe 当作 v2 Python wrapper' ARCHITECTURE/reference/reference_project_triton_research.md ARCHITECTURE/reference/reference_project_nncase_research.md`：退出码 0，确认风险边界表述仍存在且未把外部能力写成本仓当前能力。
- `git diff --check`：退出码 0。
- `git status --short --untracked-files=all`：退出码 0，仅显示 `ARCHITECTURE/reference/reference_project_nncase_research.md`、`ARCHITECTURE/reference/reference_project_triton_research.md`、本任务记录 3 个候选文件。
- `git diff --name-only -- AGENTS.md TODO.md DONE.md agents/standard expectation .skills && git diff --cached --name-only -- AGENTS.md TODO.md DONE.md agents/standard expectation .skills && git status --short --untracked-files=all -- AGENTS.md TODO.md DONE.md agents/standard expectation .skills`：退出码 0，无输出，敏感目录和状态文件空 diff。
- `rg -n '[[:blank:]]$' ARCHITECTURE/reference/reference_project_triton_research.md ARCHITECTURE/reference/reference_project_nncase_research.md agents/codex-multi-agents/log/task_records/2026/22/20260529-reference-project-research-docs.md` 反向检查：退出码 1 后脚本转为 `OK no trailing whitespace in target docs/record`，无尾随空白。
Diff 反推自测：
- 实际 diff 是纯文档与任务记录；不涉及 Python/C++ 实现、测试文件、公开 API 或工具入口，因此不运行 pytest。
- 反推验证覆盖文档类改动的真实风险：官方来源链接可达性、事实-来源-边界矩阵落位、上游移动源边界、本仓路径引用存在性、外部能力不误写成本仓当前能力、markdown 尾随空白、`git diff --check` 和敏感目录空 diff。
- `expectation` 不属于 Diff 反推测试；本任务没有计划正文列为必过的 `expectation` 合同资产，且未读取或修改 `expectation/`。
减法检查：
- 不适用代码类 private callable；本轮未新增或修改任何函数、类、helper、公开 API、测试 helper 或实现文件。
- 文档减法项：把不存在的 tracked 链接 `kernel/dump/` 收敛为生成产物目录说明，避免后续审查误判为常驻仓库路径；未删除外部能力讨论，但全部加证据边界和“不可直接转化为本仓当前能力”约束。
- 未保留旧风险：Triton 文档原先缺少标准结构和事实-来源-边界矩阵，已补齐；nncase 文档原先缺少事实-来源-边界矩阵，已补齐。
自检：
- 仅改两份 reference 文档和任务记录，符合管理员下发范围；未修改 `expectation/`、`.skills/`、`agents/standard/`、`AGENTS.md`、`TODO.md`、`DONE.md`、`spec/`、`kernel_gen/`、`kernel/`、`include/`、`test/`。
- 不涉及公开 API 新增、删除、重命名、签名、工具参数或公开错误语义变化。
- 证据矩阵已把每条核心结论绑定官方来源和边界，避免把上游项目能力、闭源 KPU 插件能力、GPU runtime、PTQ/混合量化或 masked DMA 写成本仓当前完成态。
- 本仓相对链接已核对，缺失的 `kernel/dump/` 已改为生成产物口径。
- 可维护性检查：两份文档现在都有稳定入口、使用示例、证据边界和后续转化约束；后续 review 可直接按矩阵逐条复核。
结论：execute 已完成，建议进入 review；review 通过后再交合并专职 merge，本人不执行合并。

时间：2026-05-29 02:29 +0800
经办人：咯咯咯
任务：T-20260529-8f034aee / execute -> review 流转
任务目标：按任务记录约定在执行记录完成后续接 review，并回报管理员。
改动：
- 执行 `codex-multi-agents-task.sh -next -auto` 将任务从 `execute` 续接到 `review`。
- 自动分配 review 给 `不要啊教练`，脚本已向 `不要啊教练` 与管理员 `神秘人` 发送 talk。
验证：
- 首次 `-next` 因缺少 canonical agents list 环境变量失败：`ERROR(1): cannot resolve canonical agents list; set CODEX_MULTI_AGENTS_AGENTS_FILE or AGENTS_FILE`，未改变任务状态。
- 设置 `CODEX_MULTI_AGENTS_AGENTS_FILE=/home/lfr/kernelcode_generate/agents/codex-multi-agents/agents-lists.md` 与 `AGENTS_FILE=/home/lfr/kernelcode_generate/agents/codex-multi-agents/agents-lists.md` 后重跑：退出码 0，输出 `OK: next T-20260529-8f034aee`、`OK: auto-dispatch T-20260529-8f034aee -> 不要啊教练`、`OK: talk 咯咯咯 -> 不要啊教练`、`OK: talk 咯咯咯 -> 神秘人`。
自检：
- 流转前已写完整 execute 记录、验证、Diff 反推自测、减法检查和自检。
- 本人未执行 review 或 merge。
结论：任务已续接 review，等待 reviewer 审查。

时间：2026-05-29 02:37 +0800
经办人：不要啊教练
任务：T-20260529-8f034aee / review / reference-project-research-docs
任务目标：审查两份 `ARCHITECTURE/reference` 调研文档的官方来源证据、证据边界、本仓映射、可维护性、路径引用、Diff 反推自测与敏感目录空 diff；本任务为非计划级任务，通过后进入 merge。
最新同步现场：
- 执行目录：`/home/lfr/kernelcode_generate/wt-20260529-reference-project-research-docs`
- `git fetch origin main --prune`：退出码 0。
- `HEAD`：`f1241d90456408d6fd033937dd2e8ce9db1b9041`
- `origin/main`：`f1241d90456408d6fd033937dd2e8ce9db1b9041`
- `merge-base HEAD origin/main`：`f1241d90456408d6fd033937dd2e8ce9db1b9041`
- `git rev-list --left-right --count HEAD...origin/main`：`0 0`
- 同步结论：待审 worktree 与最新主线同基线，无 ahead/behind；`git diff --name-only HEAD..origin/main -- ARCHITECTURE/reference/reference_project_triton_research.md ARCHITECTURE/reference/reference_project_nncase_research.md agents/codex-multi-agents/log/task_records/2026/22/20260529-reference-project-research-docs.md` 无输出，主线未抢先改动候选路径，无覆盖风险。
被审 diff：
- `ARCHITECTURE/reference/reference_project_triton_research.md`：新增 Triton 调研文档。
- `ARCHITECTURE/reference/reference_project_nncase_research.md`：新增 nncase 调研文档。
- `agents/codex-multi-agents/log/task_records/2026/22/20260529-reference-project-research-docs.md`：新增任务记录。
发现：无阻断项。
官方来源证据审查：
- Triton 文档列出官方仓库、官方文档、API 页面、dialect 文档和官方 GitHub 源码；证据核对矩阵逐条把 block/program instance、`tl.constexpr`、matmul tail、autotune/config、compiler stage 和 debug dump/reproducer 绑定到官方来源与证据边界。
- nncase 文档列出官方仓库、v2 使用说明、ShapeBucket、MixQuant、FAQ、Python wrapper、Compiler、CompileOptions、CompileSession；证据核对矩阵逐条把模型编译器定位、Python wrapper 编译闭环、显式编译合同、ShapeBucket、stage dump 和 KPU 源码边界绑定到官方来源与证据边界。
- 本轮 shell 中 `curl` 对 Triton 官方文档页返回 200；GitHub 页面在当前复审环境出现连接超时，未形成内容不一致证据。execute 记录已记录 GitHub 链接访问 `OK 200`；本轮 review 额外核对了文档中的上游 `main/master` 移动源边界，确认没有把 GitHub moving source 写成固定 commit 事实。
证据边界与本仓映射审查：
- 两份文档均明确“只作为外部参考样本”，不把 Triton GPU runtime、nncase 整模型编译、PTQ、混合量化、KPU 闭源能力或 Caffe wrapper 写成本仓当前能力。
- Triton 文档明确后续涉及公开 API、dialect 语义、工具参数或 `expectation/` 合同资产时必须另走 `spec`、计划书和用户确认流程。
- nncase 文档明确后续涉及公开 API、工具参数、dialect 语义、量化合同或 `expectation/` 合同资产时必须另走 `spec`、计划书和用户确认流程。
- 本仓相对映射链接覆盖 `ARCHITECTURE/project_architecture.md`、`kernel_gen/pipeline/npu_demo_lowering.py`、tuning pass、tuner dialect/spec、`operation/nn`、`kernel/runner.py` 和 kernel demo 目录；`kernel/dump/` 已写成运行 demo 后生成产物，不作为 tracked 常驻路径引用。
可维护性与文档结构审查：
- 两份文档均包含 `功能简介 / 执行摘要 / 文档信息 / 使用示例 / 调研对象与证据边界 / 证据核对矩阵`，后续维护者可按矩阵更新来源、边界和本仓映射。
- 文档把“可直接借鉴 / 不建议照搬 / 后续可形成计划输入”分开，降低后续执行人把参考项目能力误读为当前任务目标的风险。
- 没有新增公开 API、实现、测试、spec 或合同资产改动。
验证：
- `python3` 本仓 markdown 相对链接核对脚本：退出码 0，输出 `OK local markdown relative links`。
- `python3` 候选文档与记录尾随空白检查脚本：退出码 0，输出 `OK no trailing whitespace in candidate docs/record`。
- `git diff --check`：退出码 0；注意候选文档当前为 untracked，普通 `git diff --check` 不覆盖 untracked 文件，因此本轮已用尾随空白脚本补充覆盖两份文档和任务记录。
- `rg -n '^(## 功能简介|## 执行摘要|## 文档信息|## 使用示例|## 调研对象与证据边界|### 证据核对矩阵)|GitHub `main`|GitHub `master`|生成产物目录 `kernel/dump/`' ARCHITECTURE/reference/reference_project_triton_research.md ARCHITECTURE/reference/reference_project_nncase_research.md`：退出码 0，确认结构、移动源边界和生成产物路径口径均落位。
- `rg -n '直接引入 Triton|直接依赖 nncase|当前已有 PTQ|当前已支持混合量化|Caffe 当作 v2 Python wrapper|公开 API|expectation' ARCHITECTURE/reference/reference_project_triton_research.md ARCHITECTURE/reference/reference_project_nncase_research.md`：退出码 0，确认关键风险边界与公开 API / expectation 转化约束存在。
- `git status --short --untracked-files=all`：仅显示两份 reference 文档和本任务记录。
- `git status --short --untracked-files=all -- expectation .skills agents/standard AGENTS.md TODO.md DONE.md kernel_gen kernel include test spec`：退出码 0，无输出；候选不得包含的敏感目录、状态文件和业务代码均为空 diff。
Diff 反推审查：
- 实际 diff 为纯文档新增和任务记录新增，不涉及 Python/C++ 实现、测试文件、spec、公开 API、工具入口或 expectation；因此不运行 pytest。
- 反推审查覆盖文档类风险：官方来源链接与来源清单、证据核对矩阵、上游 moving source 边界、本仓相对路径、本仓能力边界、公开 API / expectation 转化约束、markdown 尾随空白、`git diff --check` 和敏感目录空 diff。
- execute 记录中的 Diff 反推自测与本轮复审范围匹配；未发现用 expectation 替代 diff 测试的问题。
减法审查：
- 不适用代码类 private callable；本轮未新增或修改函数、类、helper、测试 helper 或实现文件。
- 文档减法已闭合：不存在的 tracked 链接 `kernel/dump/` 已改为“运行 demo 后生成”的产物目录说明；两份文档从无结构/无矩阵状态收口为带证据边界矩阵的 reference 文档。
- 未发现被替代旧文案无依据保留；未发现小于 5 行 private callable、private callable 调用 private callable、跨文件非公开 API、ctx 能力探测、非装饰器嵌套函数或 `object` 签名问题。
执行记录核对：
- execute 记录包含执行前阅读、最新同步现场、最小功能闭环、验证、Diff 反推自测、减法检查、自检和结论。
- 执行范围与管理员下发一致：只处理两份 reference 文档和任务记录，不修改 `expectation/`、`.skills/`、`agents/standard/`、`AGENTS.md`、`TODO.md`、`DONE.md`、业务代码或测试。
自检：
- 已读取实际文档全文、任务记录、角色 prompt、根 `AGENTS.md`、审查规范和任务记录约定。
- 已按最新主线现场审查，确认候选路径没有主线覆盖风险。
- 已检查官方来源证据、证据边界、本仓映射、路径引用、文档结构、Diff 反推自测和敏感目录门禁。
- 已确认本任务非计划级；review 通过后应按普通任务流程流转 merge，不进入 archive_acceptance。
结论：通过。可进入 merge；merge 候选只能包含两份 `ARCHITECTURE/reference` 调研文档和本任务记录，不得纳入 `expectation/.skills/agents/standard/AGENTS.md/TODO.md/DONE.md`、`spec/`、`kernel_gen/`、`kernel/`、`include/`、`test/` 或其它业务代码。

时间：2026-05-29 02:42 +0800
经办人：李白
任务：T-20260529-8f034aee / merge / reference-project-research-docs
任务目标：同批合入两份 `ARCHITECTURE/reference` 调研文档与本任务记录，排除 `expectation/.skills/agents/standard/AGENTS.md/TODO.md/DONE.md`、`spec/`、`kernel_gen/`、`kernel/`、`include/`、`test/` 和其它业务代码。
改动：
- 来源 worktree：`/home/lfr/kernelcode_generate/wt-20260529-reference-project-research-docs`。
- 合并前同步：`git fetch --prune origin` 后发现任务分支 `HEAD=f1241d90456408d6fd033937dd2e8ce9db1b9041`、`origin/main=e8a08b619053780ae4b80d56dbe700d5323530cd`，ahead/behind=`0/1`；执行 `git merge --ff-only origin/main` 成功，更新后 `HEAD=origin/main=merge-base=e8a08b619053780ae4b80d56dbe700d5323530cd`，ahead/behind=`0/0`。
- 实际候选文件仅 3 个：
  - `ARCHITECTURE/reference/reference_project_triton_research.md`
  - `ARCHITECTURE/reference/reference_project_nncase_research.md`
  - `agents/codex-multi-agents/log/task_records/2026/22/20260529-reference-project-research-docs.md`
- 本任务为普通非计划任务；review 记录结论为通过，明确普通任务不进入 `archive_acceptance`。
验证：
- `git status --short --untracked-files=all`：仅显示两份 reference 文档和本任务记录。
- `git status --short --untracked-files=all -- expectation .skills agents/standard AGENTS.md TODO.md DONE.md kernel_gen kernel include test spec ARCHITECTURE/plan`：退出码 0，无输出，敏感目录、状态文件、业务代码、业务测试、`spec` 和计划书均未进入候选。
- `python3` 本仓 markdown 相对链接核对脚本：退出码 0，输出 `OK local markdown relative links`。
- `python3` 候选文档与记录尾随空白检查脚本：退出码 0，输出 `OK no trailing whitespace in candidate docs/record`。
- `git ls-tree -r --name-only origin/main -- <三条候选路径>`：无输出，确认 latest main 未已有同名 tracked 资产。
- 未运行 pytest：本轮实际 diff 是纯 reference 文档与任务记录，不涉及实现、`spec`、测试、公开 API 或工具入口；review 已按文档类风险完成 Diff 反推审查。
冲突处理：
- latest main 快进同步成功，无冲突。
- 候选路径在 `origin/main` 中不存在，未覆盖主仓已有 tracked 文件。
敏感文件核对：
- 未修改、未暂存、未合入 `expectation/`、`.skills/`、`agents/standard/`、`AGENTS.md`、`TODO.md`、`DONE.md`、`spec/`、`kernel_gen/`、`kernel/`、`include/`、`test/` 或 `ARCHITECTURE/plan`。
剩余风险：
- 两份文档引用的外部 GitHub `main/master` 与官网页面是移动源；文档已单列 moving source 边界，不把外部项目能力、性能或源码顺序写成本仓稳定验收。
结论：合并前核对通过；可以只暂存上述 3 个候选文件并执行同批提交、push、`-done`。
