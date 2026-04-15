# agents_standard_rules_governance_green_plan.md

## 文档信息

- 创建者：`大闸蟹`
- 最后一次更改：`大闸蟹`
- 目标 `spec`：
  - [`agents/standard/agents目录规则.md`](../../agents/standard/agents目录规则.md)
  - [`agents/standard/spec文件规范.md`](../../agents/standard/spec文件规范.md)
  - [`agents/standard/任务新建模板.md`](../../agents/standard/任务新建模板.md)
  - [`agents/standard/任务记录约定.md`](../../agents/standard/任务记录约定.md)
  - [`agents/standard/协作执行通用规则.md`](../../agents/standard/协作执行通用规则.md)
  - [`agents/standard/合并规范.md`](../../agents/standard/合并规范.md)
  - [`agents/standard/审查规范.md`](../../agents/standard/审查规范.md)
  - [`agents/standard/异常处理规范.md`](../../agents/standard/异常处理规范.md)
  - [`agents/standard/角色权限矩阵.md`](../../agents/standard/角色权限矩阵.md)
  - [`agents/standard/计划书标准.md`](../../agents/standard/计划书标准.md)
  - [`agents/standard/计划书模板.md`](../../agents/standard/计划书模板.md)
  - [`agents/standard/规则索引.md`](../../agents/standard/规则索引.md)
  - [`agents/standard/术语统一页.md`](../../agents/standard/术语统一页.md)
  - [`agents/standard/计划书完成样板.md`](../../agents/standard/计划书完成样板.md)
- 目标 `API`：
  - `agents/standard` 标准文档入口
  - `规则索引`
  - `术语统一页`
  - `命令 × 文件范围交叉矩阵`
  - `计划书必备字段 checklist`
  - `已完成计划书样板`
- 目标 `test`：
  - 无现成 `pytest`；本计划以文档文本核对命令为主
  - `rg -n` / `test -f` / `sed -n` 文本验收
- 目标 `验收资产`：
  - [`agents/standard/规则索引.md`](../../agents/standard/规则索引.md)
  - [`agents/standard/术语统一页.md`](../../agents/standard/术语统一页.md)
  - [`agents/standard/计划书完成样板.md`](../../agents/standard/计划书完成样板.md)
  - `rg -n "目录树示例|主仓更新|worktree 更新" agents/standard/agents目录规则.md`
  - `rg -n "一对多实现|多测试文件" agents/standard/spec文件规范.md`
  - `rg -n "失败示例" agents/standard/任务新建模板.md`
  - `rg -n "最小合格记录|阻塞记录" agents/standard/任务记录约定.md`
  - `rg -n "状态流转图" agents/standard/协作执行通用规则.md`
  - `rg -n "白名单" agents/standard/合并规范.md`
  - `rg -n "结构性问题|转成任务" agents/standard/审查规范.md`
  - `rg -n "脚本|任务表|worktree|权限" agents/standard/异常处理规范.md`
  - `rg -n "交叉矩阵|命令|文件范围" agents/standard/角色权限矩阵.md`
  - `rg -n "checklist|必备字段" agents/standard/计划书标准.md`
  - `rg -n "已完成计划书|样板" agents/standard/计划书模板.md`
- 目标 `功能实现`：
  - [`agents/standard/agents目录规则.md`](../../agents/standard/agents目录规则.md)
  - [`agents/standard/spec文件规范.md`](../../agents/standard/spec文件规范.md)
  - [`agents/standard/任务新建模板.md`](../../agents/standard/任务新建模板.md)
  - [`agents/standard/任务记录约定.md`](../../agents/standard/任务记录约定.md)
  - [`agents/standard/协作执行通用规则.md`](../../agents/standard/协作执行通用规则.md)
  - [`agents/standard/合并规范.md`](../../agents/standard/合并规范.md)
  - [`agents/standard/审查规范.md`](../../agents/standard/审查规范.md)
  - [`agents/standard/异常处理规范.md`](../../agents/standard/异常处理规范.md)
  - [`agents/standard/角色权限矩阵.md`](../../agents/standard/角色权限矩阵.md)
  - [`agents/standard/计划书标准.md`](../../agents/standard/计划书标准.md)
  - [`agents/standard/计划书模板.md`](../../agents/standard/计划书模板.md)
  - [`agents/standard/规则索引.md`](../../agents/standard/规则索引.md)
  - [`agents/standard/术语统一页.md`](../../agents/standard/术语统一页.md)
  - [`agents/standard/计划书完成样板.md`](../../agents/standard/计划书完成样板.md)

## 任务清单

| 任务 | 前置任务 | worktree | 记录文件 |
| --- | --- | --- | --- |
| S1 | 无 | `wt-20260415-standard-rules-s1` | `agents/codex-multi-agents/log/task_records/2026/16/20260415-standard-rules-s1.md` |
| S2 | S1 | `wt-20260415-standard-rules-s2` | `agents/codex-multi-agents/log/task_records/2026/16/20260415-standard-rules-s2.md` |
| S3 | S2 | `wt-20260415-standard-rules-s3` | `agents/codex-multi-agents/log/task_records/2026/16/20260415-standard-rules-s3.md` |
| S4 | S3 | `wt-20260415-standard-rules-s4` | `agents/codex-multi-agents/log/task_records/2026/16/20260415-standard-rules-s4.md` |
| S5 | S4 | `wt-20260415-standard-rules-s5` | `agents/codex-multi-agents/log/task_records/2026/16/20260415-standard-rules-s5.md` |
| S6 | S5 | `wt-20260415-standard-rules-s6` | `agents/codex-multi-agents/log/task_records/2026/16/20260415-standard-rules-s6.md` |

## 评审摘要

- 评审结论：`通过`
- 评审人：`守护最好的爱莉希雅`、`大闸蟹`
- 结论摘要：`按用户新范围复核后通过。当前版本已把 expectation 从计划主体中移除，S1-S6 改为纯 agents/standard 文档治理：S1 收索引与术语入口，S2 收高频执行示例，S3 收白名单与命令×文件范围交叉矩阵，S4 收 spec/审查/计划写作规范与完成样板，S5 统一复核互引与口径，S6 统一交付；任务边界清楚，规则索引、术语统一页、合并白名单、权限快查矩阵与计划书完成样板足以形成独立治理闭环，可直接按当前计划建任务推进。`

## 互评结论（2026-04-15 08:46 +0800）

- 互评人：`守护最好的爱莉希雅`
- 互评结论：`通过`
- 互评要点：
  - 新范围已经收干净：计划正文只把 `expectation` 保留在“范围变更说明 / 不做什么”中的排除项说明，不再把 `expectation` 作为交付对象、合同项或阶段验收内容；上一轮围绕 `expectation` 例外交付的阻断在本版确实已失效。
  - 任务拆分仍然合理，且比旧版更干净：`S1` 先建立索引与术语入口，`S2` 再补目录树/失败示例/阻塞记录/状态流转图这些高频执行样板，`S3` 再把白名单与命令×文件范围交叉矩阵收成快查表，`S4` 收 spec/审查/计划写作规范与完成样板，`S5` 统一做全文互引与口径复核，`S6` 再统一交付，前后依赖顺序成立，不需要再重排。
  - 三个治理抓手已经能独立闭环：
    - `规则索引.md` + `术语统一页.md` 解决“先看哪篇、词是什么意思”；
    - `合并规范.md` 白名单 + `角色权限矩阵.md` 交叉矩阵解决“能不能做、能带哪些文件”；
    - `计划书标准.md` checklist + `计划书模板.md` + `计划书完成样板.md` 解决“怎么写、写成什么样算完成”。
  - `计划书完成样板.md` 继续独立成文件是合适的。当前计划已把它和 `计划书模板.md` 做成“空模板 + 终态样板”的双入口，这比把大段完成态正文直接嵌回模板更利于维护，也更符合本轮“文档治理而非流程改造”的目标。

## 范围变更说明

- 用户已明确：`这个计划应该没有 expectation`。
- 因此本计划从“标准规则组治理 + expectation 例外交付口径”收缩为“纯 `agents/standard` 文档治理”。
- 上一轮互评中围绕 `expectation` 例外交付必要条件的阻断项，不再属于本计划范围；该阻断不沿用到本版。
- 本计划不负责：
  - `expectation` 资产交付方式
  - `.gitignore` 相关口径
  - 任何计划书中的 ignored asset 例外说明

## 输入摘要

- 目标：把 `agents/standard` 这组标准文档整理成一套更容易检索、互相引用稳定、执行人和管理员都能快速判定的规则系统。
- 不做什么：本轮不重写任务脚本，不改 `.skills`，不调整 `TODO.md / DONE.md` 数据结构，不把整套流程重新设计一遍，也不处理 `expectation` 资产规则。
- 当前痛点：文档阅读需要频繁来回跳转，部分高频问题只能靠口头规则补齐，且缺少统一入口、术语页、快查表与终态样板。
- 完成后最想看到的例子：执行人只靠 `规则索引 + 术语统一页 + 目标文档`，就能判断“该看哪篇、能改什么、怎么记日志、怎么判定是否越界”。

## 计划目标

- 为 `agents/standard` 建立稳定入口：新增 `规则索引` 与 `术语统一页`，先解决“找不到规则”和“同词多义”的问题。
- 为高频执行场景补齐最小样板：目录树、失败示例、最小合格记录、阻塞记录、状态流转图、白名单、checklist、完成样板。
- 把权限与边界做成快查表，而不是继续把角色权限、命令权限、文件范围分散在多篇纯文本里。
- 把“结构性建议如何变成修复任务”“计划书怎么自查”“任务字段怎么不填错”都写成可以直接照抄的模板。
- 保持本计划为纯文档治理，不扩到脚本实现、角色提示词、`expectation` 资产规则或仓库流程重构。

## 当前基线

- 当前公开合同：
  - `agents/standard` 已覆盖 `agents` 目录、`spec`、任务新建、任务记录、协作执行、合并、审查、异常、权限矩阵、计划书标准与模板。
  - 但这组文档目前没有统一入口页，也没有统一术语页；使用者通常需要先靠经验判断“去看哪一篇”。
- 当前公开 API：
  - 现有文档更像“分散的规则正文”，缺少两类高频入口：
    - `按问题找规则` 的入口
    - `按术语找定义` 的入口
  - `角色权限矩阵` 已有角色级权限表，但没有把“命令”和“文件范围”做成交叉快查表。
- 当前实现入口：
  - 多数文档已经可用，但样例层面不足：缺目录树示例、失败示例、阻塞记录对照、状态流转图、已完成计划书样板。
  - `计划书模板` 只有空模板，没有终态样板；`计划书标准` 有自检清单，但未收成一眼可扫的必备字段 checklist。
- 当前测试与验收资产：
  - 当前没有针对 `agents/standard` 的自动化测试；验收主要靠文本核对与执行链实践。
  - 多数文档缺少能够直接 `rg` 命中的稳定章节标题，导致“有没有补齐指定内容”很难快速核验。
- 当前缺口或失败点：
  - 文档检索成本高：没有 `规则索引`，没有 `术语统一页`。
  - 示例不足：用户列出的目录树、失败示例、阻塞记录样例、状态流转图、白名单、完成样板，目前都不存在。
  - 快速判定能力不足：权限矩阵、异常分类、计划自检仍以长文本为主，不利于执行时快速查阅。
  - 当前 [`agents/standard/合并规范.md`](../../agents/standard/合并规范.md) 缺少“允许合并的文件类型白名单”快查结构；即使不讨论 `expectation`，也仍不利于审查时快速判断是否越界。

## 方案比较与选型

- 不采用方案：继续只在原有 11 篇文档里零散补段落，不新增入口页。
- 不采用原因：
  - 这样能补内容，但不能解决“先看哪篇”和“同一个词在不同文档里怎么解释”的问题。
  - 每次新增规则仍会继续分散，检索成本不会下降。
- 不采用方案：把本轮直接扩成脚本治理或流程重构专题。
- 不采用原因：
  - 用户当前提出的是标准规则组整理，不是脚本系统改造。
  - 现阶段最大问题是检索困难和示例缺失，先改脚本会让范围失控。
- 不采用方案：把“已完成计划书样板”直接整篇内嵌到 [`agents/standard/计划书模板.md`](../../agents/standard/计划书模板.md) 里。
- 不采用原因：
  - 模板文件本身已经偏长；若整篇嵌入完成样板，后续维护会变成同时维护两份大块正文。
  - 更适合让模板保留“最小模板 + 跳转入口”，完成样板独立成单独文档。
- 采用方案：
  - 新增两份基础入口文档：`规则索引.md`、`术语统一页.md`。
  - 不处理 `expectation` 规则，只按主题对现有文档补示例、图示、白名单、矩阵与 checklist。
  - 将 `已完成计划书样板` 拆为独立文件，并在模板中链接引用。
- 最小公开接口：
  - `agents/standard/规则索引.md`
  - `agents/standard/术语统一页.md`
  - `agents/standard/角色权限矩阵.md` 中的命令 × 文件范围交叉矩阵
  - `agents/standard/计划书标准.md` 中的必备字段 checklist
  - `agents/standard/计划书模板.md` 到 `agents/standard/计划书完成样板.md` 的入口

## 公开 API 设计

### 1. 规则索引

- 公开入口：`agents/standard/规则索引.md`
- 用途：作为 `agents/standard` 的第一入口，按“主题 / 文档 / 什么时候看 / 常见问题”组织。
- 最小字段顺序：`主题`、`主文档`、`配套文档`、`什么时候看`、`常见误区`
- 返回值：`无`

```markdown
| 主题 | 主文档 | 配套文档 | 什么时候看 | 常见误区 |
| --- | --- | --- | --- | --- |
| 任务记录 | 任务记录约定.md | 异常处理规范.md | 写日志前 | 把常规记录写回主仓 |
| 合并 | 合并规范.md | 角色权限矩阵.md | merge 前 | 只看文字结论，不核对白名单与禁带目录 |
```

### 2. 术语统一页

- 公开入口：`agents/standard/术语统一页.md`
- 用途：统一 `任务`、`阶段`、`任务链`、`主仓`、`worktree`、`阻塞记录`、`归档任务` 等常用词。
- 最小字段顺序：`术语`、`定义`、`不等于什么`、`首次出现文档`
- 返回值：`无`

```markdown
| 术语 | 定义 | 不等于什么 | 首次出现文档 |
| --- | --- | --- | --- |
| worktree | 当前任务独立工作目录 | 主仓根目录 | agents目录规则.md |
| 阻塞记录 | 因异常无法继续时的强制日志 | 审查结论 | 任务记录约定.md |
```

### 3. 命令 × 文件范围交叉矩阵

- 公开入口：`agents/standard/角色权限矩阵.md`
- 用途：让执行人快速判断“我能不能执行这个命令、能改哪类文件”。
- 最小字段顺序：`命令/动作`、`架构师`、`管理员`、`spec/build/review/替补`、`merge`、`允许文件范围`
- 返回值：`无`

```markdown
| 命令/动作 | 架构师 | build | merge | 允许文件范围 |
| --- | --- | --- | --- | --- |
| -new | 可 | 不可 | 不可 | 计划书 / 专题 spec / 任务记录 |
| -next -auto -type | 不可 | 可 | 不可 | 当前任务记录 + 下游任务续接 |
```

### 4. 计划书必备字段 checklist

- 公开入口：`agents/standard/计划书标准.md`
- 用途：把已有自检项整理成“写完后逐条打勾”的最小清单。
- 最小字段顺序：`是否写明目标 spec`、`是否写明目标 API`、`是否写明验收资产`、`是否有示例`、`是否有完成态`、`是否有待确认项`
- 返回值：`无`

```markdown
- [ ] 已写明目标 spec / API / test / 验收资产 / 功能实现
- [ ] 每个阶段只有一个直接产出中心
- [ ] 已写清不做什么
```

### 5. 已完成计划书样板

- 公开入口：`agents/standard/计划书完成样板.md`
- 用途：给架构师一个终态参考，而不是只有空模板。
- 结构：必须与 `计划书标准` 一致，但内容使用一个独立示例主题，不直接复用真实进行中计划。
- 返回值：`无`

```markdown
# demo_green_plan.md

## 文档信息
- 创建者：...
...
## 阶段拆分
### S1：...
```

## 完成态定义

- `agents/standard` 下存在可直接打开的 [`规则索引.md`](../../agents/standard/规则索引.md) 与 [`术语统一页.md`](../../agents/standard/术语统一页.md)，且能覆盖现有标准文档入口。
- 用户点名的 11 篇标准文档都补上本轮要求的关键示例或快查结构，不再只剩抽象条款。
- [`agents/standard/角色权限矩阵.md`](../../agents/standard/角色权限矩阵.md) 可直接回答“哪个角色能执行什么命令、可改哪类文件”。
- [`agents/standard/合并规范.md`](../../agents/standard/合并规范.md) 含有允许合并文件类型白名单，便于快速判定越界，而不涉及 `expectation` 资产规则。
- [`agents/standard/计划书模板.md`](../../agents/standard/计划书模板.md) 能直接跳转到 [`agents/standard/计划书完成样板.md`](../../agents/standard/计划书完成样板.md)，新手不需要自己猜终态长什么样。
- 本轮不改任务脚本、不改 `.skills`、不改角色提示词、不改 `expectation` 规则；收口对象仅限 `agents/standard` 文档及其必要的新建文档。

## 验收设计

- 验收资产：
  - [`agents/standard/规则索引.md`](../../agents/standard/规则索引.md)
  - [`agents/standard/术语统一页.md`](../../agents/standard/术语统一页.md)
  - [`agents/standard/计划书完成样板.md`](../../agents/standard/计划书完成样板.md)
  - 用户点名的 11 篇标准文档
- 输入样例：
  - 以“我要建任务，但不确定 `depends/worktree/log` 怎么写”为查询入口，应能从 `规则索引 -> 任务新建模板` 找到失败示例。
  - 以“当前任务阻塞，要不要 `-next`”为查询入口，应能从 `规则索引 -> 协作执行通用规则 / 任务记录约定 / 异常处理规范` 找到状态流转与阻塞记录样例。
  - 以“当前角色能不能执行这个命令、能改哪些文件”为查询入口，应能从 `规则索引 -> 角色权限矩阵` 找到交叉矩阵。
- 锁定输出：
  - 规则入口稳定存在，且每份目标文档都能被索引页指向。
  - 关键章节名稳定可 grep。
  - 本计划不再引入 `expectation` 资产规则。
- 必过命令：
  - `test -f agents/standard/规则索引.md`
  - `test -f agents/standard/术语统一页.md`
  - `test -f agents/standard/计划书完成样板.md`
  - `rg -n "目录树示例|主仓更新|worktree 更新" agents/standard/agents目录规则.md`
  - `rg -n "一对多实现|多测试文件" agents/standard/spec文件规范.md`
  - `rg -n "失败示例" agents/standard/任务新建模板.md`
  - `rg -n "最小合格记录|阻塞记录" agents/standard/任务记录约定.md`
  - `rg -n "状态流转图" agents/standard/协作执行通用规则.md`
  - `rg -n "白名单" agents/standard/合并规范.md`
  - `rg -n "结构性问题|转成任务" agents/standard/审查规范.md`
  - `rg -n "脚本|任务表|worktree|权限" agents/standard/异常处理规范.md`
  - `rg -n "交叉矩阵|命令|文件范围" agents/standard/角色权限矩阵.md`
  - `rg -n "checklist|必备字段" agents/standard/计划书标准.md`
  - `rg -n "已完成计划书|样板" agents/standard/计划书模板.md`

## 阶段拆分

### S1：索引与术语入口收口

#### 阶段目标

- 建立 `agents/standard` 第一入口，让执行人先能找到文档、看懂术语。

#### 目标 spec / API

- `agents/standard/规则索引.md`
- `agents/standard/术语统一页.md`
- `公开 API：规则入口 / 术语入口`

#### 可改文件

- `agents/standard/规则索引.md`
- `agents/standard/术语统一页.md`
- `agents/standard/agents目录规则.md`

#### 预期示例代码

```markdown
| 主题 | 主文档 | 配套文档 | 什么时候看 | 常见误区 |
| --- | --- | --- | --- | --- |
| 合并 | 合并规范.md | 角色权限矩阵.md | merge 前 | 只看角色名，不核对白名单与禁带目录 |
```

#### 预期输出

```text
规则索引可直接指向所有现有标准文档
术语统一页至少覆盖：任务 / 阶段 / worktree / 主仓 / 阻塞记录 / 归档任务
```

#### 目标验收资产

- `agents/standard/规则索引.md`：锁定入口表与文档映射。
- `agents/standard/术语统一页.md`：锁定高频术语统一定义。

#### 验收必过项目

- `test -f agents/standard/规则索引.md`
- `test -f agents/standard/术语统一页.md`
- `rg -n "主题|主文档|配套文档|什么时候看|常见误区" agents/standard/规则索引.md`
- `rg -n "任务|阶段|worktree|主仓|阻塞记录|归档任务" agents/standard/术语统一页.md`

#### 任务新建建议

- `任务类型：spec`
- `任务目标：建立标准文档索引与术语统一页`
- `记录文件：agents/codex-multi-agents/log/task_records/2026/16/20260415-standard-rules-s1.md`

### S2：高频执行文档示例补齐

#### 阶段目标

- 把执行链最容易填错、记错、跳错的文档补成“可直接照抄”的示例型正文。

#### 目标 spec / API

- `agents/standard/agents目录规则.md`
- `agents/standard/任务新建模板.md`
- `agents/standard/任务记录约定.md`
- `agents/standard/协作执行通用规则.md`
- `agents/standard/异常处理规范.md`
- `公开 API：目录树示例 / 失败示例 / 最小合格记录 / 阻塞记录 / 状态流转图 / 异常分类`

#### 可改文件

- `agents/standard/agents目录规则.md`
- `agents/standard/任务新建模板.md`
- `agents/standard/任务记录约定.md`
- `agents/standard/协作执行通用规则.md`
- `agents/standard/异常处理规范.md`
- `agents/standard/规则索引.md`

#### 预期示例代码

```markdown
主仓：
  agents/codex-multi-agents/agents-lists.md
worktree：
  wt-xxxx/agents/codex-multi-agents/log/task_records/...
```

#### 预期输出

```text
agents目录规则中有目录树示例
任务新建模板中有典型失败示例
任务记录约定中同时存在最小合格记录与阻塞记录样例
协作执行通用规则中存在状态流转图
异常处理规范按脚本 / 任务表 / worktree / 权限四类重组
```

#### 目标验收资产

- `agents/standard/agents目录规则.md`：锁定主仓 / worktree 路径示意。
- `agents/standard/任务新建模板.md`：锁定典型失败示例。
- `agents/standard/任务记录约定.md`：锁定最小合格记录与阻塞记录对照。
- `agents/standard/协作执行通用规则.md`：锁定状态流转图。
- `agents/standard/异常处理规范.md`：锁定四类异常索引。

#### 验收必过项目

- `rg -n "目录树示例|主仓更新|worktree 更新" agents/standard/agents目录规则.md`
- `rg -n "失败示例" agents/standard/任务新建模板.md`
- `rg -n "最小合格记录|阻塞记录" agents/standard/任务记录约定.md`
- `rg -n "状态流转图" agents/standard/协作执行通用规则.md`
- `rg -n "脚本|任务表|worktree|权限" agents/standard/异常处理规范.md`

#### 任务新建建议

- `任务类型：build`
- `任务目标：补齐标准规则组高频执行示例、状态流转图与异常分类`
- `记录文件：agents/codex-multi-agents/log/task_records/2026/16/20260415-standard-rules-s2.md`

### S3：权限快查表与合并白名单收口

#### 阶段目标

- 让“能不能做”“能改哪些文件”“合并能带哪些文件”变成可快速判定的表格。

#### 目标 spec / API

- `agents/standard/角色权限矩阵.md`
- `agents/standard/合并规范.md`
- `公开 API：命令 × 文件范围交叉矩阵 / 允许合并文件类型白名单`

#### 可改文件

- `agents/standard/角色权限矩阵.md`
- `agents/standard/合并规范.md`
- `agents/standard/规则索引.md`

#### 预期示例代码

```markdown
| 命令/动作 | build | review | merge | 允许文件范围 |
| --- | --- | --- | --- | --- |
| -next -auto -type | 可 | 可 | 不可 | 当前任务记录 + 下游任务续接 |
```

#### 预期输出

```text
角色权限矩阵内可直接判断命令权限与文件边界
合并规范内存在允许合并文件类型白名单
白名单仅覆盖标准文档当前已定义的常规可交付类型
```

#### 目标验收资产

- `agents/standard/角色权限矩阵.md`：锁定交叉矩阵。
- `agents/standard/合并规范.md`：锁定白名单。

#### 验收必过项目

- `rg -n "交叉矩阵|命令|文件范围" agents/standard/角色权限矩阵.md`
- `rg -n "白名单|task_records|skills/|TODO.md|DONE.md|AGENTS.md" agents/standard/合并规范.md`

#### 任务新建建议

- `任务类型：build`
- `任务目标：补齐权限快查表与允许合并文件类型白名单`
- `记录文件：agents/codex-multi-agents/log/task_records/2026/16/20260415-standard-rules-s3.md`

### S4：spec、审查与计划写作规范收口

#### 阶段目标

- 收口架构师、审查人和 `spec` 作者最常用的写作型标准，使其具备更稳定的模板和样板。

#### 目标 spec / API

- `agents/standard/spec文件规范.md`
- `agents/standard/审查规范.md`
- `agents/standard/计划书标准.md`
- `agents/standard/计划书模板.md`
- `agents/standard/计划书完成样板.md`
- `公开 API：一对多例外写法 / 结构性问题转任务模板 / 计划书必备字段 checklist / 已完成计划书样板`

#### 可改文件

- `agents/standard/spec文件规范.md`
- `agents/standard/审查规范.md`
- `agents/standard/计划书标准.md`
- `agents/standard/计划书模板.md`
- `agents/standard/计划书完成样板.md`
- `agents/standard/规则索引.md`

#### 预期示例代码

```markdown
- [ ] 已写明目标 spec / API / test / 验收资产 / 功能实现
- [ ] 已写明完成态
- [ ] 已写明待确认项
```

#### 预期输出

```text
spec文件规范支持一对多实现 / 多测试文件的合法例外写法
审查规范中存在“结构性问题如何转成任务”的模板
计划书标准中存在必备字段 checklist
计划书模板可跳转到独立完成样板
```

#### 目标验收资产

- `agents/standard/spec文件规范.md`：锁定合法例外写法。
- `agents/standard/审查规范.md`：锁定结构性问题转任务模板。
- `agents/standard/计划书标准.md`：锁定 checklist。
- `agents/standard/计划书模板.md` 与 `agents/standard/计划书完成样板.md`：锁定空模板 + 完成样板双入口。

#### 验收必过项目

- `rg -n "一对多实现|多测试文件" agents/standard/spec文件规范.md`
- `rg -n "结构性问题|转成任务" agents/standard/审查规范.md`
- `rg -n "checklist|必备字段" agents/standard/计划书标准.md`
- `rg -n "已完成计划书|样板" agents/standard/计划书模板.md`
- `test -f agents/standard/计划书完成样板.md`

#### 任务新建建议

- `任务类型：build`
- `任务目标：补齐 spec、审查与计划写作规范的例外写法、模板与样板`
- `记录文件：agents/codex-multi-agents/log/task_records/2026/16/20260415-standard-rules-s4.md`

### S5：全文互引与口径复核

#### 阶段目标

- 统一检查整组标准文档的相互引用、章节命名和口径一致性，不再只做单篇补丁。

#### 目标 spec / API

- `agents/standard/*.md`
- `公开 API：规则索引可回跳、术语定义唯一、跨文档口径一致`

#### 可改文件

- `agents/standard/agents目录规则.md`
- `agents/standard/spec文件规范.md`
- `agents/standard/任务新建模板.md`
- `agents/standard/任务记录约定.md`
- `agents/standard/协作执行通用规则.md`
- `agents/standard/合并规范.md`
- `agents/standard/审查规范.md`
- `agents/standard/异常处理规范.md`
- `agents/standard/角色权限矩阵.md`
- `agents/standard/计划书标准.md`
- `agents/standard/计划书模板.md`
- `agents/standard/规则索引.md`
- `agents/standard/术语统一页.md`
- `agents/standard/计划书完成样板.md`

#### 预期示例代码

```markdown
参见：
- 规则索引.md
- 术语统一页.md
```

#### 预期输出

```text
各文档都能被规则索引覆盖
关键术语优先回链到术语统一页
不存在明显互相打架的文字口径
```

#### 目标验收资产

- `agents/standard/*.md`：锁定互引关系与冲突清单已关闭。

#### 验收必过项目

- `rg -n "规则索引.md|术语统一页.md" agents/standard/*.md`
- `sed -n '1,220p' agents/standard/规则索引.md`

#### 任务新建建议

- `任务类型：review`
- `任务目标：复核标准规则组互引关系、术语回链与口径是否闭环`
- `记录文件：agents/codex-multi-agents/log/task_records/2026/16/20260415-standard-rules-s5.md`

### S6：最终交付与归并

#### 阶段目标

- 将已通过复核的标准文档统一交付，避免只合入局部更新后留下半套口径。

#### 目标 spec / API

- `agents/standard/*.md`
- `公开交付：索引 / 术语 / 示例 / 矩阵 / 样板`

#### 可改文件

- `agents/standard/*.md`

#### 预期示例代码

```text
交付后，新进入仓库的角色可按：
规则索引 -> 术语统一页 -> 目标标准文档
完成自查与执行判定
```

#### 预期输出

```text
标准规则组形成一套可检索、可回链、无明显歧义的文档系统
```

#### 目标验收资产

- `agents/standard/*.md`
- `S1-S5` 的所有验收命令

#### 验收必过项目

- `test -f agents/standard/规则索引.md`
- `test -f agents/standard/术语统一页.md`
- `test -f agents/standard/计划书完成样板.md`
- `rg -n "目录树示例|失败示例|最小合格记录|状态流转图|白名单|交叉矩阵|checklist|样板" agents/standard/*.md`

#### 任务新建建议

- `任务类型：merge`
- `任务目标：交付标准规则组文档整理结果并完成最终合并`
- `记录文件：agents/codex-multi-agents/log/task_records/2026/16/20260415-standard-rules-s6.md`

## 待确认项

- 问题：`已完成计划书样板` 是否独立成单独文件，还是直接嵌进 [`agents/standard/计划书模板.md`](../../agents/standard/计划书模板.md)。
  - 可选项：`A. 独立文件 + 模板跳转`；`B. 全量内嵌到模板`
  - 差异：`A` 更利于维护与复用；`B` 打开模板即见终态，但模板会明显变长。
  - 推荐项：`A. 独立文件 + 模板跳转`
- 问题：状态流转图采用什么表达方式。
  - 可选项：`A. Mermaid 图 + 短文字说明`；`B. 纯 ASCII 文本箭头`
  - 差异：`A` 更直观，但要求阅读端支持 Mermaid；`B` 兼容性最好，但可读性较差。
  - 推荐项：`A. Mermaid 图 + 短文字说明`

## 参考资料

- 用户给出的“标准规则组”点评与补充项：作为本计划的输入清单。
- [`agents/standard/计划书标准.md`](../../agents/standard/计划书标准.md)：本计划书结构与自检口径来源。

## 终验结论（2026-04-15 22:20 +0800）

- 终验人：`大闸蟹`
- 当前主仓：`HEAD=bb51390`
- 终验结论：`通过`
- 终验依据：
  - [`TODO.md`](../../TODO.md) 当前将本计划记为 `3/3/0 / 完成待检查`；已完成链为 [`T-20260415-785e88a8`](../../DONE.md)、[`T-20260415-6c99cb23`](../../DONE.md)、[`T-20260415-b494814e`](../../DONE.md)，旧占位 `T-20260415-2fe92aca / T-20260415-b8047205 / T-20260415-00599018 / T-20260415-ae63b008` 已不再保留于任务表。
  - 新增入口文档存在且可直接打开：
    - `test -f agents/standard/规则索引.md` -> `OK`
    - `test -f agents/standard/术语统一页.md` -> `OK`
    - `test -f agents/standard/计划书完成样板.md` -> `OK`
  - 计划书点名的关键文本验收已在主仓复跑命中：
    - `rg -n "目录树示例|主仓更新|worktree 更新" agents/standard/agents目录规则.md` -> 命中 `目录树示例` 与 `主仓更新 / worktree 更新`
    - `rg -n "一对多实现|多测试文件" agents/standard/spec文件规范.md` -> 命中例外规则与示例章节
    - `rg -n "失败示例" agents/standard/任务新建模板.md` -> 命中
    - `rg -n "最小合格记录|阻塞记录" agents/standard/任务记录约定.md` -> 命中
    - `rg -n "状态流转图" agents/standard/协作执行通用规则.md` -> 命中
    - `rg -n "白名单" agents/standard/合并规范.md` -> 命中“允许合并文件类型白名单”
    - `rg -n "结构性问题|转成任务" agents/standard/审查规范.md` -> 命中“结构性问题如何转成任务”与模板章节
    - `rg -n "脚本|任务表|worktree|权限" agents/standard/异常处理规范.md` -> 命中四类异常索引
    - `rg -n "交叉矩阵|命令|文件范围" agents/standard/角色权限矩阵.md` -> 命中“命令 × 文件范围交叉矩阵”
    - `rg -n "checklist|必备字段" agents/standard/计划书标准.md` -> 命中“必备字段 checklist”
    - `rg -n "已完成计划书|样板" agents/standard/计划书模板.md` -> 命中到 [`agents/standard/计划书完成样板.md`](../../agents/standard/计划书完成样板.md) 的跳转入口
  - 新增三份治理入口已形成闭环：
    - [`agents/standard/规则索引.md`](../../agents/standard/规则索引.md) 已按主题组织“主文档 / 配套文档 / 什么时候看 / 常见误区”
    - [`agents/standard/术语统一页.md`](../../agents/standard/术语统一页.md) 已覆盖 `任务 / 阶段 / 任务链 / worktree / 主仓 / 阻塞记录 / 归档任务 / 验收资产`
    - [`agents/standard/计划书完成样板.md`](../../agents/standard/计划书完成样板.md) 已提供与 [`agents/standard/计划书模板.md`](../../agents/standard/计划书模板.md) 对应的终态样板
- 终验说明：
  - 当前完成态与计划目标一致：本计划已收口为纯 `agents/standard` 文档治理链，索引入口、术语页、白名单、交叉矩阵、checklist 与完成样板均已在主仓落地。
  - 当前未发现需要继续补建的最小阻断项；本计划具备进入归档链的条件。

## 终验复核（2026-04-15 22:25 +0800）

- 终验人：`守护最好的爱莉希雅`
- 当前主仓：`HEAD=a4e2ed6`
- 终验结论：`通过`
- 复核依据：
  - 当前主仓文本验收直接复跑通过：
    - `test -f agents/standard/规则索引.md` -> `OK`
    - `test -f agents/standard/术语统一页.md` -> `OK`
    - `test -f agents/standard/计划书完成样板.md` -> `OK`
    - `rg -n "目录树示例|主仓更新|worktree 更新" agents/standard/agents目录规则.md` -> 命中
    - `rg -n "一对多实现|多测试文件" agents/standard/spec文件规范.md` -> 命中
    - `rg -n "失败示例" agents/standard/任务新建模板.md` -> 命中
    - `rg -n "最小合格记录|阻塞记录" agents/standard/任务记录约定.md` -> 命中
    - `rg -n "状态流转图" agents/standard/协作执行通用规则.md` -> 命中
    - `rg -n "白名单" agents/standard/合并规范.md` -> 命中
    - `rg -n "结构性问题|转成任务" agents/standard/审查规范.md` -> 命中
    - `rg -n "脚本|任务表|worktree|权限" agents/standard/异常处理规范.md` -> 命中
    - `rg -n "交叉矩阵|命令|文件范围" agents/standard/角色权限矩阵.md` -> 命中
    - `rg -n "checklist|必备字段" agents/standard/计划书标准.md` -> 命中
    - `rg -n "已完成计划书|样板" agents/standard/计划书模板.md` -> 命中
  - 大闸蟹已在本计划写回 `2026-04-15 22:20 +0800` 的终验通过结论；我本次复跑结果与其终验依据一致。
- 复核说明：
  - 当前未发现新的最小阻断项；本计划维持 `通过`，可由管理员按现行规则补建唯一归档任务推进。

## 归档记录

时间：2026-04-15 22:40 +0800
经办人：李白
任务：T-20260415-38c41a7e
任务目标：将 `ARCHITECTURE/plan/agents_standard_rules_governance_green_plan.md` 归档到 `agents/codex-multi-agents/log/task_records/done_plan/2026/16/agents_standard_rules_governance_green_plan.md`，并完成归档 merge 收口。
改动：
- 管理员指定的 `worktree=/home/lfr/kernelcode_generate/wt-20260415-archive-standard-rules-plan` 原本不存在，已按当前远端主分支 `origin/main@a4e2ed6` 新建任务分支 `T-20260415-38c41a7e` 与对应归档 `worktree`。
- 核对确认 `origin/main` 与当前索引中都不存在源计划书 `ARCHITECTURE/plan/agents_standard_rules_governance_green_plan.md` 及目标归档文件；源计划书当前仅以主仓本地 ignored 文件存在，已移动到指定归档 `worktree` 的目标路径，并在文件尾部追加本次归档记录。
- 本次归档合并范围限定为新增 `agents/codex-multi-agents/log/task_records/done_plan/2026/16/agents_standard_rules_governance_green_plan.md`；按任务口径同步移除主仓本地 `ARCHITECTURE/plan/agents_standard_rules_governance_green_plan.md`，不修改 `.gitignore`、`TODO.md`、`DONE.md` 或其它共享状态文件。
验证：
- `rg -n "T-20260415-38c41a7e|agents_standard_rules_governance_green_plan" /home/lfr/kernelcode_generate/TODO.md` -> 确认任务为 `merge/进行中/指派=李白`
- `git -C /home/lfr/kernelcode_generate worktree add -b T-20260415-38c41a7e /home/lfr/kernelcode_generate/wt-20260415-archive-standard-rules-plan origin/main` -> 成功创建归档 `worktree`
- `git -C /home/lfr/kernelcode_generate rev-parse --verify origin/main` -> `a4e2ed6d776e698055a0148a111531c5469b536e`
- `git -C /home/lfr/kernelcode_generate ls-tree --name-only origin/main -- ARCHITECTURE/plan/agents_standard_rules_governance_green_plan.md agents/codex-multi-agents/log/task_records/done_plan/2026/16/agents_standard_rules_governance_green_plan.md` -> 无输出，确认远端主分支当前无源计划书与目标归档文件
- `git -C /home/lfr/kernelcode_generate ls-files --stage -- ARCHITECTURE/plan/agents_standard_rules_governance_green_plan.md agents/codex-multi-agents/log/task_records/done_plan/2026/16/agents_standard_rules_governance_green_plan.md` -> 无输出，确认两者在当前索引均未跟踪
- `git -C /home/lfr/kernelcode_generate check-ignore -v ARCHITECTURE/plan/agents_standard_rules_governance_green_plan.md agents/codex-multi-agents/log/task_records/done_plan/2026/16/agents_standard_rules_governance_green_plan.md || true` -> 命中 `.gitignore:21:ARCHITECTURE/plan/`，确认源计划书为 ignored 本地文件，目标归档路径未被忽略
- `git -C /home/lfr/kernelcode_generate/wt-20260415-archive-standard-rules-plan status -sb` -> 仅新增 `agents/codex-multi-agents/log/task_records/done_plan/2026/16/agents_standard_rules_governance_green_plan.md`
- `test -e /home/lfr/kernelcode_generate/ARCHITECTURE/plan/agents_standard_rules_governance_green_plan.md; echo $?` -> `1`，确认主仓本地源计划书已移除
结论：归档文件已在指定 `worktree` 内生成并写入归档记录；下一步提交并推送归档文件，随后执行当前 merge 任务 `-done` 并回报管理员继续 `-done-plan`。
