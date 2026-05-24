# T-20260524-96cea72d private-helper-subtraction-review

## 2026-05-24 17:03 +0800 execute / 金铲铲大作战

### 任务目标

- 按主仓只读计划书 `/home/lfr/kernelcode_generate/ARCHITECTURE/plan/private_helper_subtraction_review_green_plan.md` 更新协作标准和点名角色提示词。
- 写入 `private callable` 准入、5 行有效代码规则、私有函数不得调用私有函数、减法检查 / 减法审查、旧逻辑保留依据。
- 不修改架构师提示词，不修改 `expectation/`、`.skills`、业务代码、业务测试或业务公开 API。

### 执行前阅读记录

- 已读取个人提示词：`agents/codex-multi-agents/agents/金铲铲大作战/金铲铲大作战.prompt.md`。
- 已读取根规则：`AGENTS.md`。
- 已读取相关标准：`agents/standard/实现文件规范.md`、`agents/standard/审查规范.md`、`agents/standard/任务记录约定.md`。
- 已读取主仓只读计划书：`/home/lfr/kernelcode_generate/ARCHITECTURE/plan/private_helper_subtraction_review_green_plan.md`，核对 S1-S4、小任务卡、验收设计、禁止修改面和用户 / 架构确认记录。
- 当前任务记录原文件不存在，本轮新建在指定 worktree 路径。

### 基线与并行任务核对

- 执行目录：`/home/lfr/kernelcode_generate/wt-20260524-private-helper-subtraction-review`。
- `git fetch --prune` 后基线：
  - `HEAD=d5ddd875218bb7701cb7722d4b561d1f83f7df9e`
  - `origin/main=d5ddd875218bb7701cb7722d4b561d1f83f7df9e`
  - `merge-base=d5ddd875218bb7701cb7722d4b561d1f83f7df9e`
- 并行任务路径交集核对：
  - `T-20260524-572f35ec` worktree 为 `/home/lfr/kernelcode_generate/wt-20260524-private-api-boundary-static-gate`，当前候选为 `test/repo_conformance/` 未跟踪目录，不触碰本任务 `agents/standard` 或角色提示词范围。
  - `T-20260524-99183dda` worktree 为 `/home/lfr/kernelcode_generate/wt-20260524-symbol-loop-hoist-dma-broadcast`，当前 `git status --short` 无候选 diff。
  - 本任务候选 diff 仅限计划点名标准文件和角色提示词，未发现与并行任务候选路径交叠。

### 改动

- `agents/standard/实现文件规范.md`
  - 新增 `private callable 准入` 章节，定义 module-level `_helper`、class `_method`、私有 `staticmethod`、私有 `classmethod` 的规则。
  - 明确 `__dunder__` 协议方法不按 `private callable` 处理。
  - 明确有效代码行计数口径：不计空行、注释、docstring、函数签名、装饰器行、单独括号行、单独逗号行。
  - 明确新建或改动 `private callable` 小于 5 行有效代码不得保留。
  - 明确 `private callable` 不得调用其它 `private callable`，即私有函数不得调用私有函数。
  - 明确不能内联时只能提升为已确认公开 API 或重构调用点。
  - 在实现质量与自检中加入减法检查：替代了什么旧逻辑、删了什么、保留什么、为什么保留。
- `agents/standard/审查规范.md`
  - 新增 `减法审查` 与 `私有函数审查`。
  - 明确 review 必须检查旧 helper / 旧入口 / 旧测试 / 旧文案是否删除或有保留依据。
  - 明确审查范围限定为本轮 diff、diff 直接触达模块、执行记录声称替代的旧路径；全仓扫描只作线索。
  - 将无依据旧逻辑残留、小于 5 行有效代码的 `private callable`、`private callable` 调用 `private callable` 写入不得放行项。
- `agents/standard/任务记录约定.md`
  - 在执行记录要求中新增 `减法检查` 字段。
  - 在审查记录要求中新增 `减法审查` 字段。
  - 明确无代码 diff、纯状态流转或纯只读评估场景可写不适用，但必须说明原因。
- 点名角色提示词
  - execute：`小李飞刀`、`金铲铲大作战`、`睡觉小分队`、`咯咯咯` 加入减法检查、5 行有效代码与不得调用其它 `private callable` 自检。
  - review：`提莫炖蘑菇`、`不要啊教练` 加入减法审查、私有函数审查和不得放行边界。
  - 替补：`朽木露琪亚`、`jcc你莫辜负` 按承担 `execute` / `review` 阶段核对减法检查 / 减法审查。
  - merge / admin：`李白`、`神秘人` 加入记录字段核对，缺减法检查 / 减法审查或旧逻辑保留依据时不得继续流转或合并。
- 未修改架构师提示词：`大闸蟹`、`守护最好的爱莉希雅` 无候选 diff。

### 最小功能闭环

- 标准侧：实现、审查、任务记录三个落点均能回答 `private callable` 是否准入、旧逻辑是否删除、为什么保留。
- 角色侧：execute 能在提交前写 `减法检查`，review 能在审查中写 `减法审查`，替补按承担阶段执行同口径，merge/admin 能核对记录是否齐全。
- 验收侧：文本扫描可直接命中计划关键词；结构扫描和引用路径检查可证明提示词仍保持可用结构；敏感目录空 diff 证明未越权。

### 减法检查

- 本轮为标准文档与角色提示词文本整改，无业务代码 diff，无新增 / 改动业务 `private callable`。
- 被替代旧逻辑：原标准只泛化要求“避免浅 helper / 无意义小函数 / 冗余”，未形成可执行的减法检查字段和私有函数审查字段。
- 处理结果：通过新增标准章节和角色自检，把泛化口径替换为可审查的字段、扫描关键词和不得放行项。
- 保留依据：保留原公开 API、跨文件非公开 API、测试边界、ctx 探测、嵌套函数等规则，因为它们仍是当前全仓基础约束，且与本轮新规则互补。
- 删除 / 未删除验证：本轮不删除业务旧逻辑；通过文本扫描证明新规则已落地，通过敏感目录空 diff证明未误动禁止面。

### Diff 反推自测

- 改动标准文件和提示词，所以 Diff 反推测试采用计划定义的文本验收与结构验收，不运行业务 pytest。
- 文本扫描 1：
  - `rg -n "减法检查|减法审查|私有函数审查|private callable|小于.*5 行|私有函数不得调用|有效代码行" agents/standard agents/codex-multi-agents/agents`
  - 结果：退出码 0；命中标准文件和 10 个点名角色提示词，包含 `private callable`、小于 5 行有效代码、私有函数不得调用私有函数、减法检查 / 减法审查。
- 文本扫描 2：
  - `rg -n "为什么不能内联|替代了什么旧逻辑|旧逻辑是否删除|保留依据|删了什么|保留什么|为什么保留" agents/standard agents/codex-multi-agents/agents`
  - 结果：退出码 0；命中实现规范、审查规范、任务记录约定和点名角色提示词。
- 文本扫描 3：
  - `rg -n "expectation/|\\.skills|公开 API" agents/standard agents/codex-multi-agents/agents`
  - 结果：退出码 0；命中既有权限和公开 API 规则，未引入授权放宽。
- 结构扫描：
  - 对 10 个点名 prompt 逐一检查 `## 身份与职责`、`## 权限边界`、`## 当前流程`、`## 脚本动作`、`## 交接块`、`## 正例 / 反例`、`## 升级到用户`、`## 恢复锚点`。
  - 结果：退出码 0。
- 引用路径核对：
  - 对 10 个点名 prompt 中的相对 Markdown 链接逐一按文件目录解析并检查存在。
  - 结果：退出码 0。
- 静态门禁：
  - `git diff --check`
  - 结果：退出码 0。
- 敏感目录空 diff：
  - `git diff --name-only -- agents/codex-multi-agents/agents/大闸蟹 agents/codex-multi-agents/agents/守护最好的爱莉希雅 expectation .skills`
  - 结果：无输出。

### 自检

- 允许范围：只修改计划点名的 3 个标准文件和 10 个角色提示词，并新建当前任务记录。
- 禁止面：未修改 `expectation/`、`.skills`、业务代码、业务测试、业务公开 API、架构师提示词。
- 公开 API：本轮不涉及业务公开 API 新增、删除、重命名或稳定错误语义变化。
- 规则完整性：private callable 定义、5 行有效代码计数、私有函数不得调用私有函数、不能内联处理、减法检查 / 减法审查和旧逻辑保留依据均已写入。
- 测试有效性：本轮无业务行为变化，按实际 diff 反推文本扫描、结构扫描、引用路径和敏感目录空 diff；这些命令能在关键词缺失、结构缺失、链接失效或越权改动时失败。
- 并行风险：已重核并行 running 任务路径；当前无候选路径交集。

### 结论

- execute 已完成计划 S1-S4 与验收设计。
- 无已知阻断，下一步按计划级流程续接 `review`。

## Review 记录 - 提莫炖蘑菇 - 2026-05-24 18:22 +0800

### 任务

- 任务 ID：`T-20260524-96cea72d`
- 阶段：`review`
- 经办人：`提莫炖蘑菇`
- 任务目标：审查 `private-helper-subtraction-review` 标准文档与点名角色提示词 diff，核对 `private callable` 准入、5 行有效代码、私有函数不得调用私有函数、减法检查 / 减法审查、旧逻辑保留依据、文本扫描、结构扫描、引用路径核对、`git diff --check` 与 `expectation/.skills` 空 diff。

### 最新同步现场

- 执行目录：`/home/lfr/kernelcode_generate/wt-20260524-private-helper-subtraction-review`
- `git fetch --prune origin`：退出码 0。
- `HEAD`：`d5ddd875218bb7701cb7722d4b561d1f83f7df9e`
- `origin/main`：`d5ddd875218bb7701cb7722d4b561d1f83f7df9e`
- `merge-base HEAD origin/main`：`d5ddd875218bb7701cb7722d4b561d1f83f7df9e`
- `git rev-list --left-right --count HEAD...origin/main`：`0 0`
- 同步结论：待审 worktree 已在最新 `origin/main` 基线上；本轮候选为未提交 diff，无 merge/覆盖风险。

### 审查范围

- 已读计划书：`/home/lfr/kernelcode_generate/ARCHITECTURE/plan/private_helper_subtraction_review_green_plan.md`
- 已读执行记录：本文件 execute 段。
- 被审 diff：
  - `agents/standard/实现文件规范.md`
  - `agents/standard/审查规范.md`
  - `agents/standard/任务记录约定.md`
  - `agents/codex-multi-agents/agents/小李飞刀/小李飞刀.prompt.md`
  - `agents/codex-multi-agents/agents/金铲铲大作战/金铲铲大作战.prompt.md`
  - `agents/codex-multi-agents/agents/睡觉小分队/睡觉小分队.prompt.md`
  - `agents/codex-multi-agents/agents/咯咯咯/咯咯咯.prompt.md`
  - `agents/codex-multi-agents/agents/提莫炖蘑菇/提莫炖蘑菇.prompt.md`
  - `agents/codex-multi-agents/agents/不要啊教练/不要啊教练.prompt.md`
  - `agents/codex-multi-agents/agents/朽木露琪亚/朽木露琪亚.prompt.md`
  - `agents/codex-multi-agents/agents/jcc你莫辜负/jcc你莫辜负.prompt.md`
  - `agents/codex-multi-agents/agents/李白/李白.prompt.md`
  - `agents/codex-multi-agents/agents/神秘人/神秘人.prompt.md`
- 任务记录文件为本轮新增记录文件，属于候选范围。

### Findings

- 无阻断项。
- 未发现需退回 execute 的可执行改进点。

### Diff 反推审查

- 文本扫描 1：
  - 命令：`rg -n "减法检查|减法审查|私有函数审查|private callable|小于.*5 行|私有函数不得调用|有效代码行" agents/standard agents/codex-multi-agents/agents | wc -l`
  - 结果：退出码 0，`67` 条命中。
- 文本扫描 2：
  - 命令：`rg -n "为什么不能内联|替代了什么旧逻辑|旧逻辑是否删除|保留依据|删了什么|保留什么|为什么保留" agents/standard agents/codex-multi-agents/agents | wc -l`
  - 结果：退出码 0，`33` 条命中。
- 文本扫描 3：
  - 命令：`rg -n "expectation/|\\.skills|公开 API" agents/standard agents/codex-multi-agents/agents | wc -l`
  - 结果：退出码 0，`222` 条命中；命中为既有权限与公开 API 规则及本轮补充说明，未发现授权放宽。
- 角色提示词结构扫描：
  - 命令：Python 脚本检查 10 个点名 prompt 均包含 `## 身份与职责`、`## 权限边界`、`## 当前流程`、`## 脚本动作`、`## 交接块`、`## 正例 / 反例`、`## 升级到用户`、`## 恢复锚点`。
  - 结果：退出码 0，`OK prompt structure: 10 prompts x 8 headings`。
- 引用路径核对：
  - 命令：Python 脚本检查 3 个标准文档和 10 个点名 prompt 路径存在。
  - 结果：退出码 0，`OK path check: 13 files exist`。
- 角色语义矩阵：
  - 命令：Python 脚本核对 execute / review / 替补 / merge-admin 角色提示词分别包含对应 `减法检查`、`减法审查`、`private callable`、5 行有效代码、不得调用其它 `private callable`、测试直连检查等语义。
  - 结果：退出码 0，`OK role prompt semantic term matrix`。
- 标准文档语义矩阵：
  - 命令：Python 脚本核对 `任务记录约定.md`、`实现文件规范.md`、`审查规范.md` 中对应字段和不得放行规则。
  - 结果：退出码 0，`OK standard docs semantic term matrix`。
- Diff 格式：
  - 命令：`git diff --check`
  - 结果：退出码 0。
- 敏感目录：
  - 命令：`git diff --name-only -- expectation .skills`
  - 结果：退出码 0，无输出。
  - 命令：`git diff --cached --name-only -- expectation .skills`
  - 结果：退出码 0，无输出。
  - 命令：`git status --short --ignored --untracked-files=all -- expectation .skills`
  - 结果：退出码 0，无输出。
  - 命令：`git diff --name-only -- agents/codex-multi-agents/agents/大闸蟹 agents/codex-multi-agents/agents/守护最好的爱莉希雅 expectation .skills`
  - 结果：退出码 0，无输出；架构师提示词与 `expectation/.skills` 未被修改。

### 减法审查

- 本轮为标准文档与角色提示词文本整改，无业务代码 diff，无新增或改动业务 `private callable`。
- 执行记录已写 `减法检查`，说明被替代旧逻辑为原标准中泛化的“避免浅 helper / 无意义小函数 / 冗余”口径，现收敛为可记录、可审查、可退回的字段和不得放行项。
- 被替代旧逻辑未要求删除业务代码；保留原公开 API、跨文件非公开 API、测试边界、`ctx` 探测、嵌套函数等规则有明确依据：这些仍是全仓基础约束，并与本轮新增减法规则互补。
- `实现文件规范.md` 已明确 `private callable` 准入、有效代码行计数、小于 5 行不得保留、`private callable` 不得调用其它 `private callable`、不能内联时必须提升为已确认公开 API 或重构调用点。
- `审查规范.md` 已明确 `减法审查` 和 `私有函数审查`，并将无依据旧逻辑残留、不合格 `private callable`、测试直连或跨文件直连 `private callable` 写入不得放行项。
- 未发现无依据保留的旧口径、旧字段或与本轮规则冲突的提示词残留。

### 执行记录核对

- 执行记录包含执行前阅读、最新同步现场、并行路径核对、改动摘要、最小功能闭环、`减法检查`、`Diff 反推自测`、自检和结论。
- 执行记录列出的验证与本轮 review 复核命令一致；未发现以 `expectation` 替代 diff 反推测试的问题。
- 本计划不涉及业务 pytest 或必过 `expectation` 合同验收，`expectation/` 仅作为禁止修改面核对，符合计划和 AGENTS 规则。

### 自检

- 已读取当前个人提示词、`AGENTS.md`、计划书、执行记录、被审 diff 和标准文件。
- 已逐项核对实际 diff，未只依赖执行摘要。
- 已按文本 diff 反推审查命令，验证规则落点、角色提示词结构、路径和敏感目录。
- 已核对公开 API：本轮不新增、删除、重命名或修改业务公开 API。
- 已核对禁止修改面：未修改 `expectation/`、`.skills`、业务代码、业务测试、架构师提示词。
- 已完成减法审查和私有函数审查；本轮无业务 `private callable` diff，标准与 prompt 规则已能约束后续任务。
- 当前无可执行返工项。

### 结论

- 结论：通过。
- 下一阶段：本任务是计划级 execute 落地后的 review，通过后应进入 `archive_acceptance / 计划书入档验收`，不得直接进入 merge。

## Archive Acceptance - 不要啊教练 - 2026-05-24 18:31 +0800

### 任务

- 任务 ID：`T-20260524-96cea72d`
- 阶段：`archive_acceptance / 计划书入档验收`
- 经办人：`不要啊教练`
- 任务目标：核对 `private-helper-subtraction-review` 计划级任务记录、标准文档与角色提示词 diff、文本 / 结构扫描、`git diff --check`、`expectation/.skills` 空 diff 与可归档性。

### 最新同步现场

- 执行目录：`/home/lfr/kernelcode_generate/wt-20260524-private-helper-subtraction-review`
- `git fetch origin --prune`：exit=0。
- `HEAD=d5ddd875218bb7701cb7722d4b561d1f83f7df9e`
- `origin/main=d5ddd875218bb7701cb7722d4b561d1f83f7df9e`
- `merge-base=d5ddd875218bb7701cb7722d4b561d1f83f7df9e`
- `HEAD...origin/main=0/0`
- 任务 worktree 内计划书缺失；本轮只读引用主仓计划书 `/home/lfr/kernelcode_generate/ARCHITECTURE/plan/private_helper_subtraction_review_green_plan.md`，`sha256=fce344919ca4aba4a9a8eb9a91983ce3e26284bded519c440c658cc7430c987e`。
- 同步结论：当前 worktree 位于最新 `origin/main`；候选为未提交 diff，无 merge/覆盖风险。

### 候选范围

- tracked diff：
  - `agents/standard/实现文件规范.md`
  - `agents/standard/审查规范.md`
  - `agents/standard/任务记录约定.md`
  - `agents/codex-multi-agents/agents/小李飞刀/小李飞刀.prompt.md`
  - `agents/codex-multi-agents/agents/金铲铲大作战/金铲铲大作战.prompt.md`
  - `agents/codex-multi-agents/agents/睡觉小分队/睡觉小分队.prompt.md`
  - `agents/codex-multi-agents/agents/咯咯咯/咯咯咯.prompt.md`
  - `agents/codex-multi-agents/agents/提莫炖蘑菇/提莫炖蘑菇.prompt.md`
  - `agents/codex-multi-agents/agents/不要啊教练/不要啊教练.prompt.md`
  - `agents/codex-multi-agents/agents/朽木露琪亚/朽木露琪亚.prompt.md`
  - `agents/codex-multi-agents/agents/jcc你莫辜负/jcc你莫辜负.prompt.md`
  - `agents/codex-multi-agents/agents/李白/李白.prompt.md`
  - `agents/codex-multi-agents/agents/神秘人/神秘人.prompt.md`
- untracked：`agents/codex-multi-agents/log/task_records/2026/24/20260524-private-helper-subtraction-review.md`
- 禁止纳入 merge：`expectation/`、`.skills`、业务代码、业务测试、业务公开 API、架构师提示词、主仓计划书、`AGENTS.md`、`TODO.md`、`DONE.md`、缓存和其它 worktree。
- 候选范围脚本使用 `git -c core.quotePath=false diff --name-only` 与 `git -c core.quotePath=false ls-files --others --exclude-standard` 核对，tracked / untracked 与上述清单完全一致。

### 任务记录闭环核对

- execute 记录包含执行前阅读、基线与并行任务核对、改动摘要、最小功能闭环、`减法检查`、`Diff 反推自测`、自检和结论。
- review 记录包含最新同步现场、审查范围、findings、`Diff 反推审查`、`减法审查`、执行记录核对、自检和结论。
- review 结论为通过，并明确计划级 execute 落地后进入 `archive_acceptance / 计划书入档验收`，未直接进入 merge。

### 真实入档验收

- 标准文档：`实现文件规范.md` 已新增 `private callable 准入`、有效代码行计数、小于 5 行有效代码不得保留、`private callable` 不得调用其它 `private callable`、不能内联时必须提升为已确认公开 API 或重构调用点。
- 审查规范：已新增 `减法审查` 与 `私有函数审查`，并将无依据旧逻辑残留、不合格 `private callable`、测试直连或跨文件直连 `private callable` 写入不得放行项。
- 任务记录约定：已要求 execute 写 `减法检查`、review 写 `减法审查`，并说明无代码 diff / 纯状态流转 / 纯只读评估时的不适用写法。
- 点名角色提示词：execute、review、替补、merge/admin 角色均按计划新增对应自检或记录核对；架构师提示词无 diff。
- 公开 API / expectation：本轮不涉及业务公开 API；`expectation/` 仅作为禁止修改面核对，未修改。

### Diff 反推审查

- `agents/standard/实现文件规范.md`：文本扫描与语义矩阵覆盖 `private callable` 定义、5 行有效代码规则、私有函数不得调用私有函数、为什么不能内联和减法检查。
- `agents/standard/审查规范.md`：文本扫描与语义矩阵覆盖 `减法审查`、`私有函数审查`、不得放行项和审查自检。
- `agents/standard/任务记录约定.md`：文本扫描与语义矩阵覆盖 `减法检查`、`减法审查`、旧逻辑保留依据、删除 / 未删除验证命令或 `rg` 证据。
- 10 个点名角色提示词：结构扫描、路径核对和角色语义矩阵覆盖 execute / review / 替补 / merge-admin 差异化职责。
- 本轮为标准和提示词文本 diff，无业务代码 diff，不运行 `pytest` 或 `expectation` 作为 Diff 反推测试；`expectation/` 单列为敏感目录空 diff。

### 验证

- `rg -n "减法检查|减法审查|私有函数审查|private callable|小于.*5 行|私有函数不得调用|有效代码行" agents/standard agents/codex-multi-agents/agents | wc -l`：exit=0，`67`。
- `rg -n "为什么不能内联|替代了什么旧逻辑|旧逻辑是否删除|保留依据|删了什么|保留什么|为什么保留" agents/standard agents/codex-multi-agents/agents | wc -l`：exit=0，`33`。
- `rg -n "expectation/|\.skills|公开 API" agents/standard agents/codex-multi-agents/agents | wc -l`：exit=0，`222`；命中为既有权限与公开 API 规则及本轮补充说明，未发现授权放宽。
- 角色提示词结构扫描：exit=0，`OK prompt structure: 10 prompts x 8 headings`。
- 引用路径核对：exit=0，`OK path check: 13 files exist`。
- 角色语义矩阵：exit=0，`OK role prompt semantic term matrix`。
- 标准文档语义矩阵：exit=0，`OK standard docs semantic term matrix`。
- 候选范围脚本：exit=0，`candidate scope ok`。
- `git diff --check`：exit=0。
- `git diff --cached --check`：exit=0。
- `git diff --name-only -- expectation .skills`：exit=0，空输出。
- `git diff --cached --name-only -- expectation .skills`：exit=0，空输出。
- `git status --short --ignored --untracked-files=all -- expectation .skills`：exit=0，空输出。
- `git diff --name-only -- agents/codex-multi-agents/agents/大闸蟹 agents/codex-multi-agents/agents/守护最好的爱莉希雅 expectation .skills`：exit=0，空输出。

### Findings

- 无阻断项。

### Merge 前交接

- merge 必须把本任务记录与 3 个标准文件、10 个点名角色提示词同批纳入。
- merge 不得纳入 `expectation/`、`.skills`、业务代码、业务测试、业务公开 API、架构师提示词、主仓计划书、`AGENTS.md`、`TODO.md`、`DONE.md`、缓存或其它 worktree。
- 本计划无必过 `expectation` 合同验收；`expectation/` 只作为禁止修改面空 diff 核对。

### 自检

- 已重新读取当前个人提示词、根 `AGENTS.md`、`agents/standard/任务记录约定.md` 和 `agents/standard/审查规范.md`。
- 已读取主仓只读计划书、执行记录、review 记录和实际 diff；未只依赖任务描述或执行摘要。
- 已按实际文本 diff 复跑扫描、结构、路径、语义、diff check、敏感目录和候选范围核对。
- 已核对本轮无业务公开 API、业务代码、业务测试、`expectation/`、`.skills` 或架构师提示词 diff。
- 已确认无剩余可执行返工项。

### 结论

- 结论：通过。
- `T-20260524-96cea72d` 的 `archive_acceptance / 计划书入档验收` 已闭合，可按 `execute -> review -> archive_acceptance -> merge` 流转到 merge；不直接合并。

## Merge 记录 - 李白 - 2026-05-24 18:37 CST

### 任务

- 任务 ID：`T-20260524-96cea72d`
- 阶段：`merge`
- 经办人：`李白`
- 任务目标：合入已通过 `archive_acceptance / 计划书入档验收` 的 `private-helper-subtraction-review` 标准文档、点名角色提示词和本任务记录；不得纳入 `expectation/`、`.skills`、业务代码、业务测试、业务公开 API、架构师提示词、主仓计划书、`AGENTS.md`、`TODO.md`、`DONE.md`、cache 或其它 worktree。

### 合并前阅读与同步

- 已重新读取 `agents/codex-multi-agents/agents/李白/李白.prompt.md`、主仓 `AGENTS.md`、`agents/standard/合并规范.md` 与 `agents/standard/任务记录约定.md`。
- 已读取 execute、review、archive_acceptance 全部记录；archive_acceptance 结论为通过，最小阻断项无。
- `git fetch --prune origin` 后主仓 `/home/lfr/kernelcode_generate` 为 `HEAD=origin/main=merge-base=d5ddd875218bb7701cb7722d4b561d1f83f7df9e`，任务 worktree `/home/lfr/kernelcode_generate/wt-20260524-private-helper-subtraction-review` 为 `HEAD=origin/main=merge-base=d5ddd875218bb7701cb7722d4b561d1f83f7df9e`，`HEAD...origin/main=0/0`。
- 主仓只读计划书：`ARCHITECTURE/plan/private_helper_subtraction_review_green_plan.md`，sha256=`fce344919ca4aba4a9a8eb9a91983ce3e26284bded519c440c658cc7430c987e`；本轮不合入计划书。

### 候选范围核对

- tracked diff：
  - `agents/standard/实现文件规范.md`
  - `agents/standard/审查规范.md`
  - `agents/standard/任务记录约定.md`
  - `agents/codex-multi-agents/agents/小李飞刀/小李飞刀.prompt.md`
  - `agents/codex-multi-agents/agents/金铲铲大作战/金铲铲大作战.prompt.md`
  - `agents/codex-multi-agents/agents/睡觉小分队/睡觉小分队.prompt.md`
  - `agents/codex-multi-agents/agents/咯咯咯/咯咯咯.prompt.md`
  - `agents/codex-multi-agents/agents/提莫炖蘑菇/提莫炖蘑菇.prompt.md`
  - `agents/codex-multi-agents/agents/不要啊教练/不要啊教练.prompt.md`
  - `agents/codex-multi-agents/agents/朽木露琪亚/朽木露琪亚.prompt.md`
  - `agents/codex-multi-agents/agents/jcc你莫辜负/jcc你莫辜负.prompt.md`
  - `agents/codex-multi-agents/agents/李白/李白.prompt.md`
  - `agents/codex-multi-agents/agents/神秘人/神秘人.prompt.md`
- untracked 同批纳入：`agents/codex-multi-agents/log/task_records/2026/24/20260524-private-helper-subtraction-review.md`。
- 候选范围脚本：exit=0，`candidate scope ok`，tracked / untracked 与预期完全一致。
- 禁止范围核对：`git diff --name-only -- expectation .skills kernel_gen spec test ARCHITECTURE/plan AGENTS.md TODO.md DONE.md agents/codex-multi-agents/agents/大闸蟹 agents/codex-multi-agents/agents/守护最好的爱莉希雅` 与 cached 同命令均为空；对应 `git status --short --ignored --untracked-files=all -- ...` 为空。

### Merge 前验证

- `rg -n "减法检查|减法审查|私有函数审查|private callable|小于.*5 行|私有函数不得调用|有效代码行" agents/standard agents/codex-multi-agents/agents | wc -l`：exit=0，`67`。
- `rg -n "为什么不能内联|替代了什么旧逻辑|旧逻辑是否删除|保留依据|删了什么|保留什么|为什么保留" agents/standard agents/codex-multi-agents/agents | wc -l`：exit=0，`33`。
- `rg -n "expectation/|\\.skills|公开 API" agents/standard agents/codex-multi-agents/agents | wc -l`：exit=0，`222`；命中为既有权限、公开 API 规则和本轮补充说明，未作为授权放宽依据。
- 角色提示词结构扫描：exit=0，`OK prompt structure: 10 prompts x 8 headings`。
- 引用路径核对：exit=0，`OK path check: 13 files exist`。
- 标准文档语义矩阵：exit=0，`OK standard docs semantic term matrix`。
- 角色语义矩阵：自写脚本第一次用固定短语 `5 行有效代码` / `不得调用其它` 检查时失败，第二次仍因提示词实际使用“没有调用其它 `private callable`”而失败；这两次为验证脚本固定词过窄，不是候选内容失败。改用实际等价表述 `有效代码` / `调用其它` 后复跑 exit=0，`OK role prompt semantic term matrix`。
- `git diff --check && git diff --cached --check`：exit=0。
- cache 检查：`find . \\( -name '__pycache__' -o -name '.pytest_cache' \\) -print` 无输出，未产生 cache 候选。
- 本轮为标准文档和提示词文本整改，无业务代码 diff，不运行业务 pytest；本计划无必过 `expectation` 合同验收，`expectation/` 只作为禁止修改面空 diff 核对。

### 冲突处理与敏感文件

- 无冲突；任务 worktree 与主仓同基线，未发生 rebase / merge 冲突处理。
- 未修改、未 stage、未合入 `expectation/`、`.skills`、业务代码、业务测试、业务公开 API、架构师提示词、主仓计划书、`AGENTS.md`、`TODO.md`、`DONE.md`、cache 或其它 worktree。
- 本任务记录为新增未跟踪文件，已确认必须与标准文档和点名角色提示词同批合入。

### 结论

- merge 前核对通过。
- 下一步按上述允许范围精确 stage、提交，快进合入主仓，push 后执行 `-done` 并清理完成 worktree/branch。
