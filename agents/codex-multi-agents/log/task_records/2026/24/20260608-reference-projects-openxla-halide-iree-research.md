# T-20260608-9e23420f reference projects OpenXLA / Halide / IREE research

时间：2026-06-08 02:38 +0800
经办人：小李飞刀
任务：T-20260608-9e23420f / plan-level execute
任务目标：按 `ARCHITECTURE/plan/reference_projects_openxla_halide_iree_research.md` Draft 1-R2，在 `ARCHITECTURE/reference/` 新增 OpenXLA、Halide、IREE 三份长期参考文档，只读参考官方文档和官方源码，聚焦 pass / 优化方法、可借鉴方法和本仓迁移口径。

## 执行前阅读记录

- 已读根 `AGENTS.md`：确认 `expectation/`、`.skills/`、`agents/standard/`、公开 API、`TODO.md`、`DONE.md` 等禁止修改面；execute 需记录自检、Diff 反推自测和减法检查。
- 已读 `agents/codex-multi-agents/agents/小李飞刀/小李飞刀.prompt.md`：确认当前角色只做 execute，不做 review / merge / 归档；完成后通过 `-next review` 流转。
- 已读 `agents/standard/任务记录约定.md`：确认常规任务记录落在当前 worktree 指定路径；记录需包含执行前阅读、最小功能闭环、验证、自检、Diff 反推自测和减法检查。
- 已读 `/home/lfr/kernelcode_generate/TODO.md`：当前任务 `T-20260608-9e23420f` 为 `execute / 小李飞刀 / 进行中`，worktree 为 `/home/lfr/kernelcode_generate/wt-20260608-reference-projects-openxla-halide-iree-research`。
- 已读计划书 `ARCHITECTURE/plan/reference_projects_openxla_halide_iree_research.md`：Draft 1-R2 已由 `守护最好的爱莉希雅` 守护最终检验通过；计划级固定流转为 `execute -> review -> archive_acceptance/计划书入档验收 -> merge/归档`。
- 已核对管理员补建 worktree 回执：分支 `task/reference-projects-openxla-halide-iree-research`，基线 `origin/main` / `HEAD` 为 `7cddf72301dcba958fcc0f0cedd34e09b0f24aa0`。
- 已核对计划文件 index 证据：`git ls-files --stage ARCHITECTURE/plan/reference_projects_openxla_halide_iree_research.md` 为 `100644 051485fa8e9dd790753acae1bd8b3ade0f67e018 0`；`sha256sum` 为 `e654a7973c83eba58dc7acd4e33531833db9d11ae51172440edb6a1c46b99807`。
- 官方证据源只读查看范围：
  - OpenXLA / XLA：`openxla.org/xla/*` 官方文档、`github.com/openxla/xla` 官方源码中的 HLO pass pipeline、HloPassFix、HLO verifier、GPU compiler / thunk / emitter 相关文件。
  - Halide：`halide-lang.org/docs/*` 官方文档、`github.com/halide/Halide` 官方源码中的 schedule、bounds、simplify、storage folding / flattening、lowering 相关文件。
  - IREE：`iree.dev/*` 官方文档、`github.com/iree-org/iree` 官方源码中的 Flow、HAL、Codegen、GlobalOptimization pass 相关文件。
- 未下载、未 clone、未编译外部项目，未引入外部依赖。

## 计划内小任务卡核对

- S1 新增 OpenXLA reference 文档：已完成 `ARCHITECTURE/reference/reference_project_openxla_research.md`。
- S2 新增 Halide reference 文档：已完成 `ARCHITECTURE/reference/reference_project_halide_research.md`。
- S3 新增 IREE reference 文档：已完成 `ARCHITECTURE/reference/reference_project_iree_research.md`。
- S4 整体一致性、禁止修改面和任务记录收口：已完成文档结构、关键词、负向排除词、reference 目录状态、禁止修改面和 diff check 验收；本记录写入指定路径。

## 最小功能闭环

- 新增三份长期参考文档，均包含计划要求的 `功能简介 / 执行摘要 / 文档信息 / 使用示例 / 调研对象与证据边界 / 外部证据源 / 本仓对照点 / 证据核对矩阵 / 项目是什么 / 不是什么 / 可借鉴方法 / 对本仓的迁移口径 / 最不该直接照搬的点 / 自检清单`。
- OpenXLA 文档聚焦 HLO pass pipeline、`HloPassPipeline`、`HloPassFix`、invariant checker、cleanup placement、target late lowering 和本仓迁移口径。
- Halide 文档聚焦 algorithm / schedule 分离、bounds inference、simplify placement、storage folding / flattening、target codegen 边界和本仓迁移口径。
- IREE 文档聚焦 Flow / Codegen / HAL / VM 分层、dispatch / executable 边界、cleanup / legality gate、target backend 分层和本仓迁移口径。
- 三份文档均明确外部项目 `main` / 在线文档会变化，只沉淀能力类别和设计边界，不把外部 pass 顺序、runtime、debug tooling 或内部 flag 写成本仓稳定合同。
- 本轮不修改公开 API，不修改实现、`spec`、`test`、`kernel_gen` 或 `expectation/`，不回到用户排除方向。

## 改动摘要

- `ARCHITECTURE/plan/reference_projects_openxla_halide_iree_research.md`：管理员已物化并暂存守护通过的计划文件，execute 未修改计划正文。
- `ARCHITECTURE/reference/reference_project_openxla_research.md`：新增 OpenXLA / XLA reference 文档。
- `ARCHITECTURE/reference/reference_project_halide_research.md`：新增 Halide reference 文档。
- `ARCHITECTURE/reference/reference_project_iree_research.md`：新增 IREE reference 文档。
- `agents/codex-multi-agents/log/task_records/2026/24/20260608-reference-projects-openxla-halide-iree-research.md`：新增本执行记录。

## 验证

- `git status --short`：退出码 0；显示计划文件 staged，三份 reference 文档待暂存；无禁止修改面文件改动。
- `git ls-files --stage ARCHITECTURE/plan/reference_projects_openxla_halide_iree_research.md && sha256sum ARCHITECTURE/plan/reference_projects_openxla_halide_iree_research.md`：退出码 0；blob `051485fa8e9dd790753acae1bd8b3ade0f67e018`、sha256 `e654a7973c83eba58dc7acd4e33531833db9d11ae51172440edb6a1c46b99807`，与管理员证据一致。
- `git diff --check -- ARCHITECTURE/reference ARCHITECTURE/plan/reference_projects_openxla_halide_iree_research.md`：退出码 0；无 whitespace 错误。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 -m compileall ARCHITECTURE/reference`：退出码 0；输出 `Listing 'ARCHITECTURE/reference'...`，无错误。
- `test -f ARCHITECTURE/reference/reference_project_openxla_research.md`：退出码 0。
- `test -f ARCHITECTURE/reference/reference_project_halide_research.md`：退出码 0。
- `test -f ARCHITECTURE/reference/reference_project_iree_research.md`：退出码 0。
- `rg -n "OpenXLA|HloPassPipeline|HloPassFix|invariant|target late" ARCHITECTURE/reference/reference_project_openxla_research.md`：退出码 0；命中 OpenXLA / HloPassPipeline / HloPassFix / invariant / target late 关键内容。
- `rg -n "Halide|schedule|bounds|simplify|storage" ARCHITECTURE/reference/reference_project_halide_research.md`：退出码 0；命中 Halide / schedule / bounds / simplify / storage 关键内容。
- `rg -n "IREE|Flow|Codegen|dispatch|executable|HAL" ARCHITECTURE/reference/reference_project_iree_research.md`：退出码 0；命中 IREE / Flow / Codegen / dispatch / executable / HAL 关键内容。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 -c 'from pathlib import Path; files = [Path("ARCHITECTURE/reference/reference_project_openxla_research.md"), Path("ARCHITECTURE/reference/reference_project_halide_research.md"), Path("ARCHITECTURE/reference/reference_project_iree_research.md")]; required = ["## 功能简介", "## 执行摘要", "## 文档信息", "## 使用示例", "## 调研对象与证据边界", "### 外部证据源", "### 本仓对照点", "### 证据核对矩阵", "## 项目是什么 / 不是什么", "## 可借鉴方法", "## 对本仓的迁移口径", "## 最不该直接照搬的点", "## 自检清单"]; missing = {str(path): [item for item in required if item not in path.read_text(encoding="utf-8")] for path in files}; missing = {path: items for path, items in missing.items() if items}; assert not missing, missing'`：退出码 0；三份文档均包含必需章节。
- `! rg -n "调试产物|生成参数|编译会话模型" ARCHITECTURE/reference/reference_project_openxla_research.md ARCHITECTURE/reference/reference_project_halide_research.md ARCHITECTURE/reference/reference_project_iree_research.md`：退出码 0；无命中。
- `git diff --name-only -- expectation .skills agents/standard AGENTS.md TODO.md DONE.md plan/1.md kernel_gen spec test`：退出码 0；无输出。
- `git diff --cached --name-only -- expectation .skills agents/standard AGENTS.md TODO.md DONE.md plan/1.md kernel_gen spec test`：退出码 0；无输出。
- `git status --porcelain -- expectation .skills agents/standard AGENTS.md TODO.md DONE.md plan/1.md kernel_gen spec test`：退出码 0；无输出。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 -c 'import subprocess; allowed = {"ARCHITECTURE/reference/reference_project_openxla_research.md", "ARCHITECTURE/reference/reference_project_halide_research.md", "ARCHITECTURE/reference/reference_project_iree_research.md"}; out = subprocess.check_output(["git", "status", "--porcelain", "--", "ARCHITECTURE/reference"], text=True); seen = set(); bad = [];  [seen.add(line[3:]) if (line[:2] == "??" or line[:2].strip() == "A") and line[3:] in allowed else bad.append(line) for line in out.splitlines()]; assert not bad, bad; assert seen == allowed, seen'`：退出码 0；`ARCHITECTURE/reference/` 只出现三份目标新增文档。

## Diff 反推自测

- 实际改动为 markdown 文档与任务记录，无 Python / C++ / shell 实现改动；无对应 pytest 入口。
- 反推测试覆盖：
  - markdown / diff 基础：`git diff --check -- ARCHITECTURE/reference ARCHITECTURE/plan/reference_projects_openxla_halide_iree_research.md`，退出码 0。
  - 文档目录可遍历：`PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 -m compileall ARCHITECTURE/reference`，退出码 0。
  - 目标文档存在性：三条 `test -f` 均退出码 0。
  - 内容主题：三条项目关键词 `rg` 均退出码 0。
  - 逐文件结构：计划给定 `python3 -c` 章节核对退出码 0。
  - 用户排除方向：负向 `rg` 退出码 0，无命中。
  - 禁止修改面：unstaged / staged / status 三类命令均退出码 0 且无输出。
  - reference 目录误改防线：计划给定 status 脚本退出码 0。
- 未运行 pytest：本轮不改实现、`spec` 或 `test`，计划正文明确验收以 markdown 文本核对、链接边界核对、禁止修改面核对和 diff check 为主；风险为 review 需继续人工核对文档质量和官方证据边界。

## 减法检查

- 新增 / 改动 private callable：无。
- 被替代旧逻辑：无；本轮仅新增 reference 文档，不替换实现逻辑。
- 保留旧逻辑依据：不适用；无代码 diff。
- 删除 / 未删除验证：`git status --short` 与 reference 目录状态脚本显示未修改既有 reference 文档，禁止修改面三类核对均无输出。
- 旧方向收口：三份文档未出现计划负向门禁中的用户排除词，未把外部 debug / runtime / 完整 compiler stack 写成本仓当前完成态。

## 自检

- 接口：不新增、不删除、不重命名、不修改公开 API；未新增工具入口、脚本参数、pipeline option、include API、稳定错误文本或公开输出合同。
- 边界：只改计划交付的三份 reference 文档、管理员已暂存的计划文件和指定任务记录；未触碰 `expectation/`、`.skills/`、`agents/standard/`、`AGENTS.md`、`TODO.md`、`DONE.md`、`plan/1.md`、`kernel_gen`、`spec`、`test`。
- 异常与兼容：无运行时代码改动，无兼容分支或能力探测写法。
- 实现遗漏：S1 / S2 / S3 / S4 均有对应产物和验收证据。
- 冗余与复用：三份文档结构一致，分别覆盖项目差异；没有新增总览文档或修改既有 reference 文档。
- 注释准确性：文档均标注外部 `main` / 在线 docs 会变化，避免把外部源码当前状态写成本仓稳定合同。
- 函数粒度、输入输出、资源、并发、性能：不适用，原因是纯 markdown 文档任务。
- 测试有效性：章节脚本逐文件检查所有必需章节；关键词 `rg` 覆盖每个项目核心主题；负向 `rg` 覆盖用户排除方向；敏感目录命令覆盖禁止修改面。
- 质量风险：仍需 review 人工核对三份文档的证据解释是否充分、是否真正聚焦 pass / 优化方法、是否存在过度迁移表述。

## 结论

execute 已完成。候选可进入 review；计划级后续流转应为 `review -> archive_acceptance/计划书入档验收 -> merge/归档`，不得在 review 通过后直接 merge。

---

时间：2026-06-08 02:40 +0800
经办人：小李飞刀
任务：T-20260608-9e23420f / staged 候选复核
任务目标：记录暂存后三份 reference 文档、计划文件和任务记录的最终核验结果。

## 改动

- 已暂存：
  - `ARCHITECTURE/plan/reference_projects_openxla_halide_iree_research.md`
  - `ARCHITECTURE/reference/reference_project_halide_research.md`
  - `ARCHITECTURE/reference/reference_project_iree_research.md`
  - `ARCHITECTURE/reference/reference_project_openxla_research.md`
  - `agents/codex-multi-agents/log/task_records/2026/24/20260608-reference-projects-openxla-halide-iree-research.md`
- `git status --short`：退出码 0；仅显示以上 5 个 staged 新增文件，无 unstaged / untracked 额外文件。

## 验证

- `git diff --check -- ARCHITECTURE/reference ARCHITECTURE/plan/reference_projects_openxla_halide_iree_research.md agents/codex-multi-agents/log/task_records/2026/24/20260608-reference-projects-openxla-halide-iree-research.md`：退出码 0；无输出。
- `git diff --cached --check -- ARCHITECTURE/reference ARCHITECTURE/plan/reference_projects_openxla_halide_iree_research.md agents/codex-multi-agents/log/task_records/2026/24/20260608-reference-projects-openxla-halide-iree-research.md`：退出码 0；无输出。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 -m compileall ARCHITECTURE/reference`：退出码 0；输出 `Listing 'ARCHITECTURE/reference'...`，无错误。
- 逐文件章节核对脚本：退出码 0；三份文档均包含计划要求章节。
- 负向排除词 `! rg -n "调试产物|生成参数|编译会话模型" ...`：退出码 0；无命中。
- `git diff --name-only -- expectation .skills agents/standard AGENTS.md TODO.md DONE.md plan/1.md kernel_gen spec test`：退出码 0；无输出。
- `git diff --cached --name-only -- expectation .skills agents/standard AGENTS.md TODO.md DONE.md plan/1.md kernel_gen spec test`：退出码 0；无输出。
- `git status --porcelain -- expectation .skills agents/standard AGENTS.md TODO.md DONE.md plan/1.md kernel_gen spec test`：退出码 0；无输出。
- `ARCHITECTURE/reference/` 只允许三份目标新增文件的状态脚本：退出码 0。
- `git diff --cached --name-status`：退出码 0；输出只包含计划文件、三份 reference 文档和本任务记录 5 个新增文件。

## 自检

- 暂存后仍未触碰禁止修改面；`expectation/` 无 diff。
- 三份文档仍通过章节、关键词和负向排除词门禁。
- 任务记录已包含执行前阅读、最小功能闭环、Diff 反推自测、减法检查、自检和结论。

## 结论

staged 候选满足计划验收，可执行 `-next review` 并回报管理员。

---

时间：2026-06-08 02:48 +0800
经办人：提莫炖蘑菇
任务：T-20260608-9e23420f / reference-projects-openxla-halide-iree-research / review
任务目标：审查计划级 execute 候选是否按 `ARCHITECTURE/plan/reference_projects_openxla_halide_iree_research.md` 新增 OpenXLA / Halide / IREE 三份长期 reference 文档，并核对官方文档 / 官方源码证据边界、pass / 优化方法聚焦、可借鉴方法、迁移口径、用户排除方向负向门禁、禁止修改面、Diff 反推自测、减法检查和 staged diff；计划级 review 通过后续接 `archive_acceptance`，不得直接 `merge`。

## 最新同步现场

- 执行目录：`/home/lfr/kernelcode_generate/wt-20260608-reference-projects-openxla-halide-iree-research`。
- `git fetch origin` 后核对：`HEAD=7cddf72301dcba958fcc0f0cedd34e09b0f24aa0`，`origin/main=7cddf72301dcba958fcc0f0cedd34e09b0f24aa0`，`merge-base=7cddf72301dcba958fcc0f0cedd34e09b0f24aa0`，`git rev-list --left-right --count HEAD...origin/main` 为 `0 0`。
- 主仓 `TODO.md` 当前任务状态：`T-20260608-9e23420f` 为 `review / 提莫炖蘑菇 / 进行中`。
- 被审 staged diff：5 个新增文件，`987 insertions(+)`；包含计划书、三份 `ARCHITECTURE/reference/reference_project_*_research.md` 和本任务记录。

## Findings

- 未发现阻断项。
- 未发现最小需改项。
- 残余风险：OpenXLA 官方文档链接在本环境 `curl` 访问 `openxla.org` 超时；已用 URL 域名 / 仓库前缀检查确认 34 个外部 URL 均限定在官方域名或官方 GitHub 仓库，且 Halide / IREE 非 GitHub 官方文档链接均返回 200。本计划未把外部 live-link 全量检查列为必过，当前不作为阻断。

## 审查范围

- 已读取根 `AGENTS.md`、`agents/codex-multi-agents/agents/提莫炖蘑菇/提莫炖蘑菇.prompt.md`、计划书、任务记录、staged diff 和三份 reference 文档全文。
- 被审文件：
  - `ARCHITECTURE/plan/reference_projects_openxla_halide_iree_research.md`
  - `ARCHITECTURE/reference/reference_project_openxla_research.md`
  - `ARCHITECTURE/reference/reference_project_halide_research.md`
  - `ARCHITECTURE/reference/reference_project_iree_research.md`
  - `agents/codex-multi-agents/log/task_records/2026/24/20260608-reference-projects-openxla-halide-iree-research.md`

## 执行记录核对

- execute 记录包含执行前阅读、计划内小任务卡核对、最小功能闭环、改动摘要、验证、Diff 反推自测、减法检查、自检、staged 候选复核和结论。
- execute 记录中关于“不修改公开 API / 实现 / spec / test / expectation / 敏感目录”的结论，与本轮 staged diff、敏感目录门禁和 reference 目录门禁一致。
- execute 的减法检查适用：本轮为纯 markdown 文档任务，无新增 / 改动 private callable，无被替代实现逻辑。

## 验证

- `git fetch origin && git rev-parse HEAD origin/main && git merge-base HEAD origin/main && git rev-list --left-right --count HEAD...origin/main`：退出码 0；HEAD / origin/main / merge-base 均为 `7cddf72301dcba958fcc0f0cedd34e09b0f24aa0`，ahead / behind 为 `0 0`。
- `git diff --cached --name-status && git diff --cached --stat`：退出码 0；仅 5 个 staged 新增文件。
- `git diff --check -- ARCHITECTURE/reference ARCHITECTURE/plan/reference_projects_openxla_halide_iree_research.md agents/codex-multi-agents/log/task_records/2026/24/20260608-reference-projects-openxla-halide-iree-research.md && git diff --cached --check -- ...`：退出码 0；无 whitespace 错误。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 -m compileall ARCHITECTURE/reference`：退出码 0；输出 `Listing 'ARCHITECTURE/reference'...`，无错误。
- 逐文件章节核对脚本：退出码 0；三份 reference 文档均包含 `功能简介 / 执行摘要 / 文档信息 / 使用示例 / 调研对象与证据边界 / 外部证据源 / 本仓对照点 / 证据核对矩阵 / 项目是什么 / 不是什么 / 可借鉴方法 / 对本仓的迁移口径 / 最不该直接照搬的点 / 自检清单`。
- 三条关键词门禁：OpenXLA / HloPassPipeline / HloPassFix / invariant / target late，Halide / schedule / bounds / simplify / storage，IREE / Flow / Codegen / dispatch / executable / HAL 均命中对应文档。
- `! rg -n "调试产物|生成参数|编译会话模型" ARCHITECTURE/reference/reference_project_openxla_research.md ARCHITECTURE/reference/reference_project_halide_research.md ARCHITECTURE/reference/reference_project_iree_research.md`：退出码 0；无命中，用户排除方向负向门禁通过。
- `git diff --name-only -- expectation .skills agents/standard AGENTS.md TODO.md DONE.md plan/1.md kernel_gen spec test && git diff --cached --name-only -- ... && git status --porcelain -- ...`：退出码 0；无输出，禁止修改面和敏感目录空 diff。
- reference 目录状态脚本：退出码 0；`ARCHITECTURE/reference/` 只出现三份目标新增文件，无既有 reference 文档修改 / 删除 / 重命名。
- 内部 markdown link 检查脚本：退出码 0；三份文档中的本仓相对链接均解析到存在路径。
- 官方 URL 域名 / 仓库前缀检查脚本：退出码 0；共 34 个外部 URL，均限定在 `openxla.org`、`github.com/openxla/xla`、`halide-lang.org`、`github.com/halide/Halide`、`iree.dev`、`github.com/iree-org/iree`。
- 非 GitHub 官方文档 live check：`iree.dev` 8 个链接均返回 200，`halide-lang.org` 4 个链接均返回 200；`openxla.org` 5 个链接在本环境 `curl` 连接超时，未作为通过 / 失败门禁。

## Diff 反推审查

- 实际 diff 为纯 markdown 文档和任务记录新增，无 Python / C++ / shell 实现改动，因此不运行实现 pytest。
- 反推审查覆盖：
  - 文档结构：逐文件章节脚本确认三份文档都有计划必需章节，含 `## 可借鉴方法`。
  - 主题聚焦：项目关键词门禁与人工阅读全文确认内容聚焦 pass / 优化方法、cleanup、bounds / storage、dispatch / executable、target late lowering，而不是用户排除方向。
  - 证据边界：三份文档均列官方文档 / 官方源码，声明上游 `main` 和在线 docs 会变化，不把外部 pass 顺序、性能数字、runtime 或内部 flag 写成本仓合同。
  - 迁移口径：三份文档均把外部方法落到“可借鉴 / 不改变边界 / 最不该照搬”，未要求本任务新增公开 API、引入外部依赖、修改实现或改变 pipeline。
  - 保护面：staged diff、unstaged diff、status 和 reference 目录脚本均证明没有越界文件。

## 减法审查

- 新增 / 改动 private callable：无。
- private callable 小于 5 行或 private callable 调 private callable：不适用，原因是无代码 diff。
- 测试直连 / 跨文件直连非公开 API：不适用，原因是未改测试或实现。
- 被替代旧逻辑：无；本轮只新增 reference 文档，不替换现有架构文档或实现逻辑。
- 旧逻辑保留依据：既有 `ARCHITECTURE/reference/` 文档未改，本计划只补齐 OpenXLA / Halide / IREE 三份缺口；reference 目录状态脚本已证明无既有 reference 误改。

## 保护面与公开 API

- 未修改 `kernel_gen/`、`spec/`、`test/`、`expectation/`、`.skills/`、`agents/standard/`、`AGENTS.md`、`TODO.md`、`DONE.md`、`plan/1.md`。
- 未新增、删除、重命名或修改公开 API；未新增工具入口、脚本参数、pipeline option、include API、稳定错误文本或公开输出合同。
- 三份文档中的迁移建议均保留“后续另写计划 / 不新增公开 API，除非用户确认”的边界，不构成本轮实现授权。

## 自检

- 已先同步 / 核对 latest main，并基于当前 staged candidate 审查。
- 已读取实际 diff 和三份文档全文，未只依赖 execute 摘要。
- 已核对执行记录、Diff 反推自测、减法检查、staged diff、官方证据边界、用户排除方向、禁止修改面和计划级流转。
- 未修改业务实现、测试、spec、计划书或 `expectation/`；仅将本 review 记录追加到任务记录。
- 当前没有剩余可执行返工项；计划级 review 通过后下一阶段应为 `archive_acceptance / 计划书入档验收`，不得直接 `merge`。

## 结论

review 通过。候选可按计划级链路续接 `archive_acceptance / 计划书入档验收`；不得直接 `merge`。

---

时间：2026-06-08 02:50 +0800
经办人：提莫炖蘑菇
任务：T-20260608-9e23420f / reference-projects-openxla-halide-iree-research / review -> archive_acceptance 流转记录
任务目标：将 review 通过结论按计划级链路续接 `archive_acceptance / 计划书入档验收`，并回报管理员。
改动：无业务实现 / spec / test / expectation 改动；仅通过标准脚本推进主仓 `TODO.md` 状态并发送会话消息。
验证：
- `CODEX_MULTI_AGENTS_AGENTS_FILE=/home/lfr/kernelcode_generate/agents/codex-multi-agents/agents-lists.md CODEX_MULTI_AGENTS_PERMISSION_AGENTS_FILE=/home/lfr/kernelcode_generate/agents/codex-multi-agents/agents-lists.md bash /home/lfr/kernelcode_generate/skills/codex-multi-agents/scripts/codex-multi-agents-task.sh -file /home/lfr/kernelcode_generate/TODO.md -next -auto -task_id T-20260608-9e23420f -from "提莫炖蘑菇" -type archive_acceptance -message "<archive_acceptance message>" -agents-list /home/lfr/kernelcode_generate/agents/codex-multi-agents/agents-lists.md`：退出码 0，输出 `OK: next T-20260608-9e23420f`、`OK: replace 提莫炖蘑菇 状态`、`OK: auto-dispatch T-20260608-9e23420f -> 不要啊教练`、`OK: replace 不要啊教练 状态`、`OK: talk 提莫炖蘑菇 -> 不要啊教练 (不要啊教练)`、`OK: talk 提莫炖蘑菇 -> 神秘人 (神秘人)`。
- 复查 `/home/lfr/kernelcode_generate/TODO.md`：`T-20260608-9e23420f` 当前为 `archive_acceptance / 不要啊教练 / 进行中`。
- 复查 `/home/lfr/kernelcode_generate/agents/codex-multi-agents/agents-lists.md`：`提莫炖蘑菇` 为 `free`，`不要啊教练` 为 `busy`。
- 复查 `/home/lfr/kernelcode_generate/agents/codex-multi-agents/log/talk.log`：可见给 `不要啊教练` 的 `archive_acceptance` 分发消息和给 `神秘人` 的阶段完成回报。
自检：未手工编辑 `TODO.md` 或 `agents-lists.md`；未直接进入 `merge`；review 记录已写入并暂存；计划级下一阶段已按 `archive_acceptance` 流转。
结论：review 阶段已完成并释放，当前接手人为 `不要啊教练`；管理员 `神秘人` 已收到回报。

---

时间：2026-06-08 02:53 +0800
经办人：不要啊教练
任务：T-20260608-9e23420f / reference-projects-openxla-halide-iree-research / archive_acceptance
任务目标：核对计划级 review 通过后的计划书入档验收、任务记录、latest main 同步现场、三份 `ARCHITECTURE/reference` 文档、官方证据边界、文本门禁、用户排除方向负向门禁、`expectation` 无 diff、敏感目录空 diff、`git diff --check` / `--cached --check` 与可归档性；不得直接 merge。

## 最新同步现场

- 执行目录：`/home/lfr/kernelcode_generate/wt-20260608-reference-projects-openxla-halide-iree-research`。
- `git fetch origin --prune` 后核对：`HEAD=7cddf72301dcba958fcc0f0cedd34e09b0f24aa0`，`origin/main=7cddf72301dcba958fcc0f0cedd34e09b0f24aa0`，`merge-base=7cddf72301dcba958fcc0f0cedd34e09b0f24aa0`，`git rev-list --left-right --count HEAD...origin/main` 为 `0 0`。
- 主仓 `TODO.md` 当前任务状态：`T-20260608-9e23420f` 为 `archive_acceptance / 不要啊教练 / 进行中`。
- 候选范围：5 个 staged 新增文件，unstaged diff 为空；包含计划书、OpenXLA / Halide / IREE 三份 reference 文档和本任务记录。

## Findings

- 未发现阻断项。
- 未发现最小需改项。
- 残余风险：外部官方文档和官方源码会持续变化，本次入档只验收证据边界、官方 URL 范围和当前文档质量；不把外部 `main` 当前 pass 顺序、性能数字、runtime 或内部 flag 写成本仓稳定合同。

## 计划正文回写

- 已按计划书 `计划书入档验收 / 复验 / 修复复核记录` 占位段回写本次入档验收结论。
- 回写内容仅包含结论人、结论、验证基线、执行目录、同步结果、合同验收摘要和通过摘要；未修改计划目标、用户确认来源、公开 API 边界、验收资产、计划内小任务卡或技术方案。

## 入档验收核对

- 任务记录完整：已包含 execute 记录、staged 候选复核、review 通过记录、review -> archive_acceptance 流转记录和本次 archive_acceptance 记录。
- review 结论：通过，无阻断项、无最小需改项；review 已核对官方 URL 范围、三份文档全文、负向门禁、保护面和 staged diff。
- 三份 reference 文档：
  - `ARCHITECTURE/reference/reference_project_openxla_research.md`：存在，聚焦 HLO pass pipeline、`HloPassPipeline`、`HloPassFix`、invariant checker、cleanup placement 与 target late lowering。
  - `ARCHITECTURE/reference/reference_project_halide_research.md`：存在，聚焦 algorithm / schedule 分离、bounds inference、simplify placement、storage folding / flattening 和 target codegen 边界。
  - `ARCHITECTURE/reference/reference_project_iree_research.md`：存在，聚焦 Flow / HAL / VM 分层、dispatch / executable 边界、Codegen lowering config、cleanup / legality gate 与 target backend 分层。
- 官方证据边界：三份文档均写明只读查看官方文档和官方 GitHub 源码，不下载、不 clone、不编译外部项目；34 个外部 URL 均限定在 `openxla.org` / `github.com/openxla/xla`、`halide-lang.org` / `github.com/halide/Halide`、`iree.dev` / `github.com/iree-org/iree`。
- 用户排除方向：负向门禁 `调试产物|生成参数|编译会话模型` 无命中；三份文档没有把这些方向写成本计划主题。
- 当前无必过 `expectation`；`expectation/` 只做无 diff / status 核对，不作为通过依据。

## 验证

- `git diff --cached --name-status && git diff --name-status`：退出码 0；cached 只包含计划书、三份 reference 文档和任务记录，unstaged 无输出。
- `git diff --check -- ARCHITECTURE/reference ARCHITECTURE/plan/reference_projects_openxla_halide_iree_research.md agents/codex-multi-agents/log/task_records/2026/24/20260608-reference-projects-openxla-halide-iree-research.md && git diff --cached --check -- ... && git diff --check && git diff --cached --check`：退出码 0。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 -m compileall ARCHITECTURE/reference`：退出码 0，输出 `Listing 'ARCHITECTURE/reference'...`。
- 逐文件章节核对脚本：退出码 0；三份 reference 文档均包含计划要求的 13 个章节，含 `## 可借鉴方法`。
- 三条关键词门禁：OpenXLA / HloPassPipeline / HloPassFix / invariant / target late，Halide / schedule / bounds / simplify / storage，IREE / Flow / Codegen / dispatch / executable / HAL 均通过。
- `! rg -n "调试产物|生成参数|编译会话模型" ARCHITECTURE/reference/reference_project_openxla_research.md ARCHITECTURE/reference/reference_project_halide_research.md ARCHITECTURE/reference/reference_project_iree_research.md`：退出码 0，无命中。
- `git diff --name-only -- expectation .skills agents/standard AGENTS.md TODO.md DONE.md plan/1.md kernel_gen spec test && git diff --cached --name-only -- ... && git status --porcelain -- ...`：退出码 0，无输出。
- `ARCHITECTURE/reference/` 只允许三份目标新增文件状态脚本：退出码 0。
- 官方 URL 前缀脚本：退出码 0，输出 `official_url_prefixes_ok=34`。
- 内部 markdown link 检查脚本：退出码 0，输出 `internal_markdown_links_ok`。
- 证据边界文本脚本：退出码 0，输出 `evidence_boundary_text_ok`。

## Diff 反推审查

- 实际 diff 为计划书、三份 markdown reference 文档和任务记录；无 Python / C++ / shell 实现改动，无 `spec` / `test` 改动。
- 反推审查覆盖文档存在性、逐文件章节、项目关键词、官方证据 URL 范围、内部链接、用户排除方向、`ARCHITECTURE/reference/` 误改防线、禁止修改面、diff check 和任务记录完整性。
- 未运行 pytest：本轮不改实现、`spec` 或 `test`；计划正文也明确验收以 markdown 文本核对、链接边界核对、禁止修改面核对和 diff check 为主。

## 减法审查

- 新增 / 改动 private callable：无。
- private callable 小于 5 行或 private callable 调 private callable：不适用，原因是无代码 diff。
- 被替代旧逻辑：无；本轮只新增 reference 文档，不替换实现逻辑、旧 helper、旧入口或旧测试。
- 既有 `ARCHITECTURE/reference/` 文档未改；reference 目录状态脚本证明未修改、删除、重命名既有 reference 文档。

## 保护面与公开 API

- 未修改 `kernel_gen/`、`spec/`、`test/`、`expectation/`、`.skills/`、`agents/standard/`、`AGENTS.md`、`TODO.md`、`DONE.md`、`plan/1.md`。
- 未新增、删除、重命名或修改公开 API；未新增工具入口、脚本参数、pipeline option、include API、稳定错误文本或公开输出合同。
- 计划书回写只补入档验收记录，不改变计划目标、技术方案或授权范围。

## 自检

- 已先同步 / 核对 latest main，并确认 staged / unstaged 候选范围。
- 已读取计划书、任务记录、review 通过记录和三份 reference 文档。
- 已复跑计划门禁、官方 URL 范围检查、内部链接检查、证据边界文本检查、diff check 和敏感目录门禁。
- 已确认当前无必过 `expectation` 且 `expectation/` 无 diff。
- 本阶段未直接合并；archive_acceptance 通过后只按计划级链路续接 `merge`。

## 结论

archive_acceptance / 计划书入档验收通过；无阻断项、无最小需改项。可按计划级链路续接 `merge`，merge 阶段必须同批纳入计划书、三份 reference 文档和任务记录；不得纳入 `expectation/.skills/agents/standard/AGENTS.md/TODO.md/DONE.md/plan/1.md/kernel_gen/spec/test` 未授权改动。

---

时间：2026-06-08 02:59 +0800
经办人：李白
任务：T-20260608-9e23420f / reference-projects-openxla-halide-iree-research / merge
任务目标：按计划级合并规范核对 latest main、staged 5 文件范围、官方证据边界、用户排除方向负向门禁、`expectation/` 无 diff、敏感目录空 diff、`git diff --check` / `--cached --check`，并准备同批合入计划书、三份 `ARCHITECTURE/reference` 官方项目参考文档、任务记录和计划归档。

## 最新同步现场

- 执行目录：`/home/lfr/kernelcode_generate/wt-20260608-reference-projects-openxla-halide-iree-research`。
- `git fetch --prune origin`：exit=0。
- `git rev-parse HEAD origin/main`：`HEAD=7cddf72301dcba958fcc0f0cedd34e09b0f24aa0`，`origin/main=7cddf72301dcba958fcc0f0cedd34e09b0f24aa0`。
- `git merge-base HEAD origin/main`：`7cddf72301dcba958fcc0f0cedd34e09b0f24aa0`。
- `git rev-list --left-right --count HEAD...origin/main`：`0 0`。
- 当前候选位于 latest main，无冲突和覆盖风险。

## 链路与合入范围

- 计划级链路：`execute -> review -> archive_acceptance -> merge`；archive_acceptance 结论为通过，无阻断、无最小需改项。
- `git diff --cached --name-status`：当前只包含 5 个 staged 新增文件；`git diff --name-status` 无输出。
- 计划书原路径：`ARCHITECTURE/plan/reference_projects_openxla_halide_iree_research.md`。
- 计划 index blob：`100644 29dafa4d37f95933f39b78320f87a7cf0ca96fb9 0`。
- 计划 sha256：`67f17986ef05b1ab4be80af3472b3fd252c50a2af3ce7a4de77754e6dc83df40`。
- 计划归档目标：`agents/codex-multi-agents/log/task_records/done_plan/2026/reference_projects_openxla_halide_iree_research.md`；本记录写入后执行 `git mv`，提交前复核源路径已移出 `ARCHITECTURE/plan/` 且目标进入 staged diff。

## 同批合入文件

- `ARCHITECTURE/reference/reference_project_openxla_research.md`
- `ARCHITECTURE/reference/reference_project_halide_research.md`
- `ARCHITECTURE/reference/reference_project_iree_research.md`
- `agents/codex-multi-agents/log/task_records/2026/24/20260608-reference-projects-openxla-halide-iree-research.md`
- `agents/codex-multi-agents/log/task_records/done_plan/2026/reference_projects_openxla_halide_iree_research.md`

## 官方证据边界与文本门禁

- 三份 reference 文档均写明只读查看官方文档和官方 GitHub 源码，不下载、不 clone、不编译外部项目；外部 `main` / 在线 docs 会持续变化，不把外部当前 pass 顺序、性能数字、runtime 或内部 flag 写成本仓稳定合同。
- 官方 URL 前缀脚本：exit=0，`official_url_prefixes_ok=34`；URL 限定在 `openxla.org` / `github.com/openxla/xla`、`halide-lang.org` / `github.com/halide/Halide`、`iree.dev` / `github.com/iree-org/iree`。
- 内部 markdown link 检查脚本：exit=0，`internal_markdown_links_ok`。
- 证据边界文本脚本：exit=0，`evidence_boundary_text_ok`；上游 main / 本仓合同边界脚本：exit=0，`upstream_contract_boundary_ok`。
- 逐文件章节核对脚本：exit=0，`section_check_ok`；三份文档均包含计划要求章节，含 `## 项目是什么 / 不是什么` 与 `## 可借鉴方法`。
- 关键词门禁：OpenXLA / HloPassPipeline / HloPassFix / invariant / target late、Halide / schedule / bounds / simplify / storage、IREE / Flow / Codegen / dispatch / executable / HAL 均命中对应文档。
- 用户排除方向负向门禁：`! rg -n "调试产物|生成参数|编译会话模型" ...` exit=0，无命中。
- `ARCHITECTURE/reference/` 状态脚本：exit=0，`reference_status_ok`；只出现三份目标新增文件，无既有 reference 文档修改 / 删除 / 重命名。

## 验证

- `git diff --check && git diff --cached --check`：exit=0。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 -m compileall ARCHITECTURE/reference`：exit=0，输出 `Listing 'ARCHITECTURE/reference'...`。
- `git diff --name-only -- expectation .skills agents/standard AGENTS.md TODO.md DONE.md plan/1.md kernel_gen spec test && git diff --cached --name-only -- ... && git status --porcelain -- ...`：exit=0，无输出。
- `git ls-files --stage -- ARCHITECTURE/plan/reference_projects_openxla_halide_iree_research.md ...`：确认计划书、三份 reference 文档和任务记录均为 staged index 条目。

## 合同验收与敏感目录

- 本计划当前无必过 `expectation`；未运行 expectation，且未把 expectation 作为 diff 反推测试。
- `expectation/`、`.skills/`、`agents/standard/`、`AGENTS.md`、`TODO.md`、`DONE.md`、`plan/1.md`、`kernel_gen/`、`spec/`、`test/` 均无 staged / unstaged / status 输出。
- 未新增、删除、重命名或修改公开 API；本轮为纯 markdown reference 文档与任务记录合并。

## 冲突处理与剩余风险

- latest main 与候选基线一致，未发生冲突。
- 残余风险与 archive_acceptance 一致：外部官方文档和官方源码会持续变化，本次只验收证据边界、官方 URL 范围和当前文档质量，不把外部 `main` 当前状态写成本仓合同。
- 合并阶段不补做实现、审查或架构裁定；只合入已通过 archive_acceptance 的候选范围。
- 提交前将复核 staged diff、计划归档源 / 目标、敏感目录空 diff、`git diff --check` / `--cached --check` 和 worktree 无剩余 unstaged 候选。

## 结论

合并前记录已写入任务链记录；下一步执行计划归档、stage 任务记录与归档目标、复核 staged diff 后提交并推送。
