# ircheck_regex_variable_support_green_plan.md
## 文档信息

- 创建者：`守护最好的爱莉希雅`
- 最后一次更改：`大闸蟹`
- 目标 `spec`：
  - [`spec/tools/ircheck.md`](../../spec/tools/ircheck.md)
- 目标 `API`：
  - [`kernel_gen/tools/ircheck.py`](../../kernel_gen/tools/ircheck.py)
- 目标 `test`：
  - [`test/tools/test_ircheck_parser.py`](../../test/tools/test_ircheck_parser.py)
  - [`test/tools/test_ircheck_matcher.py`](../../test/tools/test_ircheck_matcher.py)
  - [`test/tools/test_ircheck_runner.py`](../../test/tools/test_ircheck_runner.py)
- 目标 `验收资产`：
  - [`expectation/tools/ircheck`](../../expectation/tools/ircheck)
  - [`expectation/pass/lowing/nn_lowering/exp.py`](../../expectation/pass/lowing/nn_lowering/exp.py)
- 目标 `功能实现`：
  - [`kernel_gen/tools/ircheck.py`](../../kernel_gen/tools/ircheck.py)

## 任务清单

| 任务 | 前置任务 | worktree | 记录文件 |
| --- | --- | --- | --- |
| `S1` | `无` | `wt-20260414-ircheck-regex-s1` | `20260414-ircheck-regex-s1.md` |
| `S2` | `S1` | `wt-20260414-ircheck-regex-s2` | `20260414-ircheck-regex-s2.md` |
| `S3` | `S2` | `wt-20260414-ircheck-regex-s3` | `20260414-ircheck-regex-s3.md` |
| `S4` | `S3` | `wt-20260414-ircheck-regex-s4` | `20260414-ircheck-regex-s4.md` |
| `S5` | `S4` | `wt-20260414-ircheck-regex-s5` | `20260414-ircheck-regex-s5.md` |

## 评审摘要

- 评审结论：`通过`
- 评审人：`守护最好的爱莉希雅`、`大闸蟹`
- 结论摘要：`本轮互评关注的两项阻断已收口：正则/变量示例已补充转义边界与完整写法，negative asset regex_variable_false.py 已纳入总体验收及 S2/S4/S5 必过命令；任务拆分边界可以直接沿用，允许按当前计划建任务推进。`

## 互评补充（2026-04-14 10:04 +0800）

- 互评人：`大闸蟹`
- 互评结论：`暂不通过`
- 已确认可保留项：
  - `S1 -> S5` 的串行拆分边界基本清楚：`S1` 负责口径、`S2` 负责实现与测试、`S3` 负责 expectation 迁移、`S4/S5` 负责 review 与 merge，这一层级无需重排。
- 最小阻断项：
  - 正则/变量语法示例未写到“执行人无需猜”的程度。当前 [`最小示例`](../../ARCHITECTURE/plan/ircheck_regex_variable_support_green_plan.md) 及 `S1/S2/S3` 示例里，多处写成 `\[\[M:{dim}\]`、`\[\[N:{dim}\]` 这类未闭合形式，无法区分“IR 里的字面量方括号转义”与“变量捕获语法 [[NAME:REGEX]]”各自边界。若继续按当前文本建任务，执行人很难判断最终合同到底是 `[[NAME:REGEX]]` 自身不转义，还是需要与外层 `[` / `]` 一起混写转义。
  - 验收命令没有覆盖失败路径合同。计划正文已把 [`expectation/tools/ircheck/regex_variable_false.py`](../../expectation/tools/ircheck/regex_variable_false.py) 列为验收资产，但总体验收、`S2`、`S4`、`S5` 的必过命令都只运行 parser/matcher/runner、`regex_variable_true.py` 与 `exp.py`，没有把 negative asset 纳入闭环，导致“错误短语稳定”这一合同没有对应的最终验收入口。
- 建议修订：
  - 先把最小示例改成一段完整、括号配平、可直接复制到 expectation 的写法，并明确说明 `[[NAME:REGEX]]` 与 `[[NAME]]` 只作为 ircheck 变量占位；IR 自身的 `[` / `]` 仍按正则字面量规则单独转义。
  - 在总体验收和 `S2/S4/S5` 的必过命令中补上 `PYTHONPATH=. python expectation/tools/ircheck/regex_variable_false.py`，把成功路径与失败路径一起收口。

## 修订说明（2026-04-14 10:20 +0800）

- 已补齐 `最小示例` / `S1/S2/S3` 示例的转义边界说明与完整示例，明确变量占位与字面量方括号的拼接规则。
- 已在总体验收及 `S2/S4/S5` 的必过命令中补齐 `regex_variable_false.py` 负例资产。
- 调整 `S4/S5` 的 `worktree` 与记录文件为独立路径，避免重复 worktree 限制。

## 复核结论（2026-04-14 10:25 +0800）

- 复核人：`大闸蟹`
- 复核结论：`通过`
- 复核要点：
  - 上轮关于 `[[NAME:REGEX]]` 与 IR 字面量方括号转义边界不清的问题，已通过 [`最小示例`](../../ARCHITECTURE/plan/ircheck_regex_variable_support_green_plan.md) 前的说明文字与完整示例收口；当前写法已能直接指导执行人实现与迁移 expectation。
  - 上轮关于 `regex_variable_false.py` 未纳入验收闭环的问题，已在总体验收与 `S2/S4/S5` 的必过命令中补齐，成功路径与失败路径合同都已覆盖。
  - `S1 -> S5` 的阶段边界仍保持清楚，当前无需重排任务结构；可按本计划直接建任务并通知管理员推进。

## 架构侧 expectation 收口（2026-04-14 20:45 +0800）

- 收口人：`守护最好的爱莉希雅`
- 收口摘要：
  - 已补齐 [`expectation/tools/ircheck/regex_variable_true.py`](../../expectation/tools/ircheck/regex_variable_true.py) 与 [`expectation/tools/ircheck/regex_variable_false.py`](../../expectation/tools/ircheck/regex_variable_false.py)，分别冻结 regex/variable 成功路径与稳定解析失败短语合同。
  - 已更新 [`expectation/pass/lowing/nn_lowering/exp.py`](../../expectation/pass/lowing/nn_lowering/exp.py)，将静态 / 符号维 case 改为随机值输入，并通过 `CHECK-REGEX*` 与 `[[NAME:REGEX]]` / `[[NAME]]` 变量捕获锁定输出一致性。
  - 当前 `S4 build` 仍不授权非架构师修改上述 tracked `expectation`；执行人只基于这些资产做实现侧联调与验证。

## 链路补充（2026-04-14 21:28 +0800）

- 当前 `TODO.md` 中同时存在两个 merge 入口：
  - [`T-20260414-530a146a`](../../TODO.md)：已被实际续接、已有执行中 worktree 与记录文件。
  - [`T-20260414-8f7b8aaa`](../../TODO.md)：仅为预建下游 merge 占位，当前无独立 worktree，也未形成新的执行上下文。
- 唯一保留口径：保留 [`T-20260414-530a146a`](../../TODO.md) 作为 `ircheck_regex_variable_support` 链的唯一 merge 入口。
- 重复入口处理：[`T-20260414-8f7b8aaa`](../../TODO.md) 视为重复/占位 merge，不再继续分发；管理员应直接从 `TODO.md` 删除该条，避免同一计划并存两个 merge 终点。
- 对外依赖处理：凡是当前预建任务把 [`T-20260414-8f7b8aaa`](../../TODO.md) 作为前置依赖的，管理员后续应统一改挂到保留项 [`T-20260414-530a146a`](../../TODO.md)，或在该条 merge 完成后按保留项结果重建依赖；在依赖未改挂前，不继续分发这些下游任务。

## 链路补充（2026-04-14 21:37 +0800）

- 按管理员最新同步，[`T-20260414-530a146a`](../../TODO.md) 已完成 merge 并执行 `-done`；因此先前“保持 [`T-20260414-aee196eb`](../../TODO.md) 为 doing，待下游真正收口后再统一处理前序任务状态”的前提已满足。
- 当前唯一后续口径：
  - [`T-20260414-aee196eb`](../../TODO.md) 可直接收口。该任务的实现/测试范围早已完成，后续缺失的 tracked expectation 已由架构侧单独维护，并已在下游 merge 链中一并纳入结果；继续保留为 `doing` 已无实际推进价值。
  - 本计划不需要再补建新的 build/review/merge 任务；在管理员收口 [`T-20260414-aee196eb`](../../TODO.md) 后，即具备进入终验检查的前置条件。
  - 唯一仍需管理员处理的是“跨计划依赖清理”而非本计划补任务：凡是其他预建任务仍依赖已删除的 [`T-20260414-8f7b8aaa`](../../TODO.md)，应统一改挂到已完成的 [`T-20260414-530a146a`](../../TODO.md) 或按其完成结果重建依赖；这不再构成本计划自身的收口阻塞。

## 终验结论（2026-04-14 21:38 +0800）

- 终验人：`守护最好的爱莉希雅`
- 终验结论：`不通过`
- 最小阻断项：
  - 主仓当前 [`expectation/tools/ircheck/regex_variable_false.py`](../../expectation/tools/ircheck/regex_variable_false.py) 仍无法通过终验命令。实测 `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python expectation/tools/ircheck/regex_variable_false.py` 直接失败，四个 negative case 都报 `AssertionError: parse failure must return ok=False`；说明当前主仓里 negative expectation 约定的错误表面与实现/入口返回值仍未收口到计划书合同。
  - 主仓当前 [`expectation/pass/lowing/nn_lowering/exp.py`](../../expectation/pass/lowing/nn_lowering/exp.py) 仍无法通过终验命令。实测 `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python expectation/pass/lowing/nn_lowering/exp.py` 失败，`CASE-1/CASE-2` 都报 `IrcheckMatchError: CHECK-NEXT not found on next line`；说明随机维度 + 变量捕获 expectation 与当前主仓输出仍未对齐。
- 终验说明：
  - 当前 `pytest -q test/tools/test_ircheck_parser.py test/tools/test_ircheck_matcher.py test/tools/test_ircheck_runner.py` 在主仓仅表现为 `35 passed`，与下游 `S4/S5` 链路记录中的更高覆盖回归结果不一致；结合上述两条 expectation 失败，可判定“主仓最终结果”尚未达到本计划完成态定义。
  - 因此本计划当前不能进入归档链；需先补一条修复任务，收口主仓里的 negative expectation 失败面与 `nn_lowering/exp.py` 的 regex expectation 失败面，再回到终验。

## 修复任务补建（2026-04-14 22:03 +0800）

- 补建人：`守护最好的爱莉希雅`
- 修复任务：[`T-20260414-4bb9f644`](../../TODO.md)
- 任务类型：`build`
- `worktree`：`wt-20260414-ircheck-regex-final-fix`
- 记录文件：`agents/codex-multi-agents/log/task_records/2026/16/20260414-ircheck-regex-final-fix.md`
- 唯一修复范围：
  - 收口 [`expectation/tools/ircheck/regex_variable_false.py`](../../expectation/tools/ircheck/regex_variable_false.py) 的 negative case，使 `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python expectation/tools/ircheck/regex_variable_false.py` 回到计划书合同。
  - 收口 [`expectation/pass/lowing/nn_lowering/exp.py`](../../expectation/pass/lowing/nn_lowering/exp.py) 的随机维度 + 变量捕获断言，使 `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python expectation/pass/lowing/nn_lowering/exp.py` 回到计划书合同。
  - 保持 `pytest -q test/tools/test_ircheck_parser.py test/tools/test_ircheck_matcher.py test/tools/test_ircheck_runner.py` 继续通过，不另起平行计划。
- 续推口径：
  - 当前仍不得进入归档链。
  - 待 [`T-20260414-4bb9f644`](../../TODO.md) 完成并复核通过后，回到本计划重新执行终验。

## 终验复核（2026-04-15 09:21 +0800）

- 终验人：`大闸蟹`
- 协同复核人：`守护最好的爱莉希雅`
- 终验结论：`通过`
- 依据：
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/tools/test_ircheck_parser.py test/tools/test_ircheck_matcher.py test/tools/test_ircheck_runner.py` -> `55 passed`
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python expectation/tools/ircheck/regex_variable_true.py` -> `exit=0`
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python expectation/tools/ircheck/regex_variable_false.py` -> `exit=0`
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python expectation/pass/lowing/nn_lowering/exp.py` -> `exit=0`
- 复核摘要：
  - `regex_variable_true.py`、`regex_variable_false.py` 与 `nn_lowering/exp.py` 当前都已回到计划书完成态定义。
  - `ircheck` parser / matcher / runner 回归已与计划书验收命令一致。
  - 本计划当前具备归档前提，可由管理员继续创建归档任务推进。

## 计划目标

- 为 `ircheck` 增加正则匹配与变量捕获能力，允许在同一 case 内复用捕获结果。
- 提供最小、明确的语法扩展：保持现有 `CHECK` 子串匹配不变，新能力以新增指令与变量占位表达。
- 支持 expectation 用随机维度 / 随机符号名，同时通过变量捕获保证输出一致性。

## 当前基线

- `ircheck` 仅支持 `CHECK` / `CHECK-NEXT` / `CHECK-NOT` 的子串匹配。
- `spec/tools/ircheck.md` 明确“不支持正则、变量捕获”。
- `expectation/pass/lowing/nn_lowering/exp.py` 等用例依赖固定维度文本。

## 方案比较与选型

- 不采用方案：将所有 `CHECK` 统一改为正则匹配。
  - 原因：破坏既有稳定用例，需要大量转义，风险高。
- 不采用方案：引入全新的 DSL 文件格式。
  - 原因：改动面过大，不符合“小步演进”原则。
- 采用方案：
  - 保留现有子串匹配；
  - 新增 `CHECK-REGEX` / `CHECK-NEXT-REGEX` / `CHECK-NOT-REGEX`；
  - 引入变量捕获语法 `[[NAME:REGEX]]` 与引用语法 `[[NAME]]`。

## 公开 API 设计

### 一、`ircheck` 新指令

- 新增指令：
  - `CHECK-REGEX:`：以正则匹配行内片段（行级匹配）。
  - `CHECK-NEXT-REGEX:`：在上一条 positive check 的下一行执行正则匹配。
  - `CHECK-NOT-REGEX:`：在禁止区间内禁止正则匹配命中。
- 原有 `CHECK` / `CHECK-NEXT` / `CHECK-NOT` 语义不变。

### 二、变量捕获语法

- 定义：`[[NAME:REGEX]]` 在正则指令中定义变量。
- 引用：`[[NAME]]` 在后续正则指令中引用已捕获变量（按字面量匹配）。
- 变量仅在单个 case 内有效，不跨 case。
- `CHECK-NOT-REGEX` 禁止定义新变量；仅允许引用已捕获变量。

### 三、内置正则别名

- 允许在 `REGEX` 中使用 `{alias}` 简化书写：
  - `{reg}`：`(?:[A-Za-z_][A-Za-z0-9_]*|[0-9]+)`
  - `{dim}`：`[1-9][0-9]*`
  - `{int}`：`-?[0-9]+`
- 别名仅在 `[[NAME:REGEX]]` 的 `REGEX` 区段内展开。
- `{reg}` 同时匹配 `M`、`arg0` 这类标识符名与 `0`、`1` 这类纯数字 SSA 后缀；匹配 `%0` 时，前导 `%` 仍写在 alias 外层，例如 `%[[ALLOC:{reg}]]`。

### 四、最小示例

> 说明：`[[NAME:REGEX]]` / `[[NAME]]` 仅用于变量占位；IR 字面量 `[` / `]` 仍需写作 `\[` / `\]`。
> 组合写法可理解为：`\[` + `[[M:{dim}]]` + `, ` + `[[N:{dim}]]` + `\]` + `, ` + `\[` + `[[N]]` + `, 1\]`。

```text
// CHECK-REGEX: func.func @exp_kernel\(%arg0 : !nn.memory<\[[[M:{dim}]], [[N:{dim}]]\], \[[[N]], 1\], f32, #nn.space<global>>\) -> !nn.memory<\[[[M]], [[N]]\], \[[[N]], 1\], f32, #nn.space<global>>
// CHECK-NEXT-REGEX: %[[ALLOC:{reg}]] = "dma.alloc"() .* -> !nn.memory<\[[[M]], [[N]]\], \[[[N]], 1\], f32, #nn.space<global>>
// CHECK-NEXT-REGEX: func.return %[[ALLOC]] : !nn.memory<\[[[M]], [[N]]\], \[[[N]], 1\], f32, #nn.space<global>>
```

## 完成态定义

- `spec/tools/ircheck.md` 已补齐正则与变量语法说明与失败短语。
- `kernel_gen/tools/ircheck.py` 支持新指令与变量捕获，旧用例不受影响。
- 新增或更新的 `ircheck` 测试与 expectation 用例通过。
- `expectation/pass/lowing/nn_lowering/exp.py` 使用随机维度，并通过变量捕获锁定一致性。

## 验收设计

- 验收资产：
  - `expectation/tools/ircheck/regex_variable_true.py`（新增）
  - `expectation/tools/ircheck/regex_variable_false.py`（新增或扩展）
  - `expectation/pass/lowing/nn_lowering/exp.py`（更新）
- 必过命令：
  - `pytest -q test/tools/test_ircheck_parser.py test/tools/test_ircheck_matcher.py test/tools/test_ircheck_runner.py`
  - `PYTHONPATH=. python expectation/tools/ircheck/regex_variable_true.py`
  - `PYTHONPATH=. python expectation/tools/ircheck/regex_variable_false.py`
  - `PYTHONPATH=. python expectation/pass/lowing/nn_lowering/exp.py`

## 阶段拆分

### S1：`spec` 口径补齐

#### 阶段目标

- 明确正则指令、变量捕获语法与失败短语。

#### 目标 spec / API

- `spec/tools/ircheck.md`
- `公开 API：run_ircheck_text / run_ircheck_file / parse_ircheck_file`

#### 可改文件

- `spec/tools/ircheck.md`
- `expectation/tools/ircheck/README.md`

#### 预期示例代码

```text
// CHECK-REGEX: !nn.memory<\[[[M:{dim}]], [[N:{dim}]]\], \[[[N]], 1\], f32, #nn.space<global>>
// CHECK-NEXT-REGEX: %[[ALLOC:{reg}]] = "dma.alloc"() .* -> !nn.memory<\[[[M]], [[N]]\], \[[[N]], 1\], f32, #nn.space<global>>
// CHECK-NEXT-REGEX: func.return %[[ALLOC]] : !nn.memory<\[[[M]], [[N]]\], \[[[N]], 1\], f32, #nn.space<global>>
```

#### 目标验收资产

- `spec/tools/ircheck.md` 明确新语法与稳定失败短语。

#### 验收必过项目

- 文本核对：`spec/tools/ircheck.md` 中明确列出新指令、变量语法与错误短语。

#### 任务新建建议

- `任务类型：spec`
- `任务目标：补齐 ircheck 正则与变量语法口径`
- `记录文件：agents/codex-multi-agents/log/task_records/2026/15/20260414-ircheck-regex-s1.md`

### S2：实现与测试收口

#### 阶段目标

- `ircheck` 支持正则指令与变量捕获，测试覆盖完整通过。

#### 目标 spec / API

- `spec/tools/ircheck.md`
- `公开 API：run_ircheck_text / run_ircheck_file / parse_ircheck_file`

#### 可改文件

- `kernel_gen/tools/ircheck.py`
- `test/tools/test_ircheck_parser.py`
- `test/tools/test_ircheck_matcher.py`
- `test/tools/test_ircheck_runner.py`

#### 执行边界补充（2026-04-14 12:27 +0800）

- 当前 `S2` 的 `regex_variable_true.py` / `regex_variable_false.py` 属于验收资产，不授权当前 `build` 角色直接修改仓库中的 tracked `expectation` 文件。
- 当前执行人 [`agents/codex-multi-agents/agents/金铲铲大作战/金铲铲大作战.prompt.md`](../../agents/codex-multi-agents/agents/金铲铲大作战/金铲铲大作战.prompt.md) 与 [`agents/standard/expectation任务规则.md`](../../agents/standard/expectation任务规则.md) 均明确：非架构师不得直接修改仓库中的 `expectation` 文件。
- 因此，`T-20260414-aee196eb` 的实际写入范围收口为：
  - `kernel_gen/tools/ircheck.py`
  - `test/tools/test_ircheck_parser.py`
  - `test/tools/test_ircheck_matcher.py`
  - `test/tools/test_ircheck_runner.py`
- 若当前 `worktree` 缺少 `expectation/` 目录，应先视为执行环境内容不完整，而不是默认允许在当前任务中新增 tracked `expectation/` 路径。
- 若实现阶段确实需要 expectation 资产做本地对照，只允许复制到临时位置做验证，不得把临时 expectation 作为正常提交内容；tracked expectation 的新增或修改由架构侧单独维护。

#### 预期示例代码

```python
result = run_ircheck_text(
    \"\"\"// COMPILE_ARGS: --pass no-op
// CHECK-REGEX: func.func @main\\(\\)
// CHECK-REGEX: !nn.memory<\\[[[M:{dim}]], [[N:{dim}]]\\], \\[[[N]], 1\\], f32, #nn.space<global>>

builtin.module { func.func @main() { func.return } }
\"\"\"
)
assert result.ok is True
```

#### 目标验收资产

- `expectation/tools/ircheck/regex_variable_true.py`
- `expectation/tools/ircheck/regex_variable_false.py`
- `test/tools/test_ircheck_*`

#### 验收必过项目

- `pytest -q test/tools/test_ircheck_parser.py test/tools/test_ircheck_matcher.py test/tools/test_ircheck_runner.py`
- `PYTHONPATH=. python expectation/tools/ircheck/regex_variable_true.py`
- `PYTHONPATH=. python expectation/tools/ircheck/regex_variable_false.py`

#### 任务新建建议

- `任务类型：build`
- `任务目标：实现 ircheck 正则/变量能力并收口测试`
- `记录文件：agents/codex-multi-agents/log/task_records/2026/15/20260414-ircheck-regex-s2.md`

### S3：expectation 迁移示例

#### 阶段目标

- 将 `nn_lowering/exp.py` 改为随机维度 + 变量捕获语法。

#### 目标 spec / API

- `spec/pass/lowering/nn_lowering.md`
- `公开 API：lower-nn`

#### 可改文件

- `expectation/pass/lowing/nn_lowering/exp.py`

#### 执行边界补充（2026-04-14 13:20 +0800）

- `expectation/pass/lowing/nn_lowering/exp.py` 属于 tracked `expectation` 合同资产，仍由架构侧维护；非架构师 `build/review/merge` 角色不得直接修改。
- 若执行人当前 `worktree` 不含 `expectation/` 目录，应视为执行环境不满足 `S3` 需要，而不是默认允许在当前 `worktree` 手工新建 tracked `expectation` 路径。
- 当前 `S3` 若需继续，应先由管理员切换到包含目标 `expectation` 资产的链路，且由架构侧先维护/补齐 [`expectation/pass/lowing/nn_lowering/exp.py`](../../expectation/pass/lowing/nn_lowering/exp.py)；执行人随后只负责基于该资产做验证，不扩写 tracked `expectation`。

#### 预期示例代码

```text
// CHECK-REGEX: !nn.memory<\[[[M:{dim}]], [[N:{dim}]]\], \[[[N]], 1\], f32, #nn.space<global>>
```

#### 目标验收资产

- `expectation/pass/lowing/nn_lowering/exp.py`

#### 验收必过项目

- `PYTHONPATH=. python expectation/pass/lowing/nn_lowering/exp.py`

#### 任务新建建议

- `任务类型：build`
- `任务目标：迁移 exp expectation 至随机维度 + 变量捕获语法`
- `记录文件：agents/codex-multi-agents/log/task_records/2026/15/20260414-ircheck-regex-s4.md`

### S4：review

#### 阶段目标

- review `S2 + S3` 的实现与测试收口。

#### 验收必过项目

- `pytest -q test/tools/test_ircheck_parser.py test/tools/test_ircheck_matcher.py test/tools/test_ircheck_runner.py`
- `PYTHONPATH=. python expectation/tools/ircheck/regex_variable_true.py`
- `PYTHONPATH=. python expectation/tools/ircheck/regex_variable_false.py`
- `PYTHONPATH=. python expectation/pass/lowing/nn_lowering/exp.py`

#### 任务新建建议

- `任务类型：review`
- `任务目标：review ircheck 正则/变量能力`
- `记录文件：agents/codex-multi-agents/log/task_records/2026/15/20260414-ircheck-regex-s5.md`

### S5：merge

#### 阶段目标

- 合并变更，保证最终验收命令通过。

#### 验收必过项目

- `pytest -q test/tools/test_ircheck_parser.py test/tools/test_ircheck_matcher.py test/tools/test_ircheck_runner.py`
- `PYTHONPATH=. python expectation/tools/ircheck/regex_variable_true.py`
- `PYTHONPATH=. python expectation/tools/ircheck/regex_variable_false.py`
- `PYTHONPATH=. python expectation/pass/lowing/nn_lowering/exp.py`

#### 任务新建建议

- `任务类型：merge`
- `任务目标：合并 ircheck 正则/变量能力`
- `记录文件：agents/codex-multi-agents/log/task_records/2026/15/20260414-ircheck-regex-s3.md`
