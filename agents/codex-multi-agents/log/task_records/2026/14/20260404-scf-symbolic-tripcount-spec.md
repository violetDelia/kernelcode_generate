记录因 worktree 丢失重建（2026-04-04 19:47:56 +0800，重建人：神秘人，worktree=/home/lfr/kernelcode_generate/wt-20260404-scf-symbolic-tripcount-spec），本次续写。

## T-20260404-da0ff154 复审结论（隐式 trip_count spec：仅 operation 层）

- 审查时间：2026-04-04 20:05:00 +0800
- worktree：`/home/lfr/kernelcode_generate/wt-20260404-scf-symbolic-tripcount-spec`
- 记录文件：`agents/codex-multi-agents/log/task_records/2026/14/20260404-scf-symbolic-tripcount-spec.md`

### 范围与硬断点核对（证据）

- `git diff --name-only`：仅
  - `spec/dsl/mlir_gen.md`
  - `spec/dsl/emit_mlir.md`
- 硬断点 1（不得触碰 `spec/dialect/*`）：满足（diff 不包含 `spec/dialect/*`）。
- 硬断点 2（不新增 AST 字段、不改 `spec/dsl/ast.md`）：满足（diff 不包含 `spec/dsl/ast.md`）。
- 硬断点 3（不引入 pipeline/lowered IR/gen_kernel/codegen 口径）：满足（新增内容未引入该口径；原文已有“不得把 pipeline/lowered IR/gen_kernel 当成完成条件”的负向表述不构成口径混入）。
- 硬断点 4（锚点清晰且不自相矛盾）：部分满足（新增锚点齐全，但存在语义/示例表述易误读点，见“问题列表”）。

复核到的新增锚点：
- `spec/dsl/mlir_gen.md:292`：`MGEN-015A`
- `spec/dsl/emit_mlir.md:245`：`EMIT-010A`

### 问题列表（需修改）

- P1｜`spec/dsl/mlir_gen.md:90-95` “隐式 trip_count 最小示例”注释存在自相矛盾/易误读：
  - 现象：示例注释写“含 symbol 且无法静态推导次数：隐式 trip_count = 2”，但同页上文已规定“无法在 spec 层静态推导迭代次数时默认 `trip_count = 1`”（`spec/dsl/mlir_gen.md:50`）。
  - 风险：读者无法判断 `trip_count>1` 的来源到底是“默认值之外的显式合同/规范化 end 形式”，还是“实现应在含 symbol 时自动推导为 2”；容易导致实现/测试口径分叉。
  - 建议：要么将该示例的文字改为“end 已按 `end = start + step * trip_count` 形式显式承载（此处 trip_count=2）”，强调这不是“无法推导”的场景；要么改成与“默认 1”一致的动态示例（并明确 end 规范化由哪一层负责、如何触发）。

- P1｜`spec/dsl/mlir_gen.md:50-51` 与 `spec/dsl/emit_mlir.md:43` 对“上游决定 trip_count / end 规范化承载”的边界仍偏松：
  - 现象：文档写“未遵循规范化约束的情形不在本 spec 覆盖范围内”，但未明确这类情形在实现侧应“必须报错/统一 unsupported/禁止静默回退”。
  - 风险：边界不清会导致实现侧出现静默 fallback（例如继续用原 end 发射、或改走其他 lowering 分支），削弱该 spec 的可验收性与安全性（尤其影响 DMA offset 的边界正确性）。
  - 建议：补一条“实现合同”：对不满足规范化或无法保证合法循环（例如 `step==0`、`trip_count<=0`、或无法构造 `end = start + step * trip_count`）必须报错（建议统一到 `Unsupported`/`AstVisitorError` 的既有口径），不得静默回退。

### 漏洞/风险排查（6 类，结论：存在风险点，需在 spec 收口）

- 输入校验绕过：当前新增条款未明确 `step==0`、`trip_count<=0` 的处理口径，容易被上游/调用方绕过并落入未定义行为区间。
- 类型/形状绕过：`trip_count`/`start/end/step` 参与边界规范化后，会影响 `it` 的类型与 DMA 标量 operand 传递；若缺少明确的类型合同，可能引入隐式 cast 或错误类型落地。
- 边界越界：`it` 常用于 `dma.slice/dma.deslice` 的 offsets；对“非规范化 end”或不受控 `trip_count` 的行为未收口时，存在窗口越界与 out 写回错误风险。
- 错误处理缺失：当前以“不在 spec 覆盖范围”表述边界，但未明确“必须报错且不得 fallback”的合同，存在错误处理缺失风险。
- 状态污染：`EmitContext(symbols/types)` 依赖一致性；边界不清可能导致符号表/循环变量在异常路径下部分更新，产生后续 emit 污染风险（需通过“必须报错且不继续发射”口径间接规避）。
- 资源释放问题：`trip_count` 若被误解为可由实现推导/放大，可能导致循环内临时分配规模扩大，引入资源耗尽或未释放风险；spec 应通过“默认值/合法性/报错边界”降低该风险。

### 最终结论

- 结论：**需修改**
- 唯一下一步：创建修复任务，要求在 operation 层文档内澄清 `trip_count` 的来源/默认值与示例表述，并补齐“非规范化/非法边界必须报错且不得 fallback”的合同口径；修复后再进入复审。
时间：2026-04-04 19:49:28 +0800
经办人：睡觉小分队
任务：T-20260404-ac20d7e3
任务目标：按最新口径仅在 operation 层 spec 收口隐式 `trip_count` 语义（`spec/dsl/mlir_gen.md`、`spec/dsl/emit_mlir.md`），严禁改动 `spec/dialect/*`，不改 `spec/dsl/ast.md`，不引入 pipeline/lowered IR/gen_kernel/codegen 口径。
改动：
- `spec/dsl/mlir_gen.md`：
  - 增补隐式 `trip_count` 语义与半开区间边界说明：默认 `trip_count = 1`（`scf.for/index` 用 `index` 常量 `1`，`symbol.for` 用 `!symbol.int<"1">`），迭代序列 `it = start + step * i`、`i = 0..trip_count-1`，`end` 规范化承载；不要求证明 `step` 符号/真实迭代次数。
  - 补充最小示例（静态/含 symbol 各 1）与测试映射建议（MGEN-015A）。
- `spec/dsl/emit_mlir.md`：
  - 增补 emit 约束：隐式 `trip_count` 由上游规范化承载，emit 仅消费规范化后的边界；补充最小示例与测试映射建议（EMIT-010A）。
结论：完成本轮 operation 层 spec 修复；`git diff --name-only` 仅包含 `spec/dsl/mlir_gen.md` 与 `spec/dsl/emit_mlir.md`；未运行测试（spec-only 变更）。
时间：2026-04-04 19:58:48 +0800
经办人：睡觉小分队
任务：T-20260404-44bb13f3
任务目标：修复 operation 层隐式 `trip_count` 口径冲突与非法边界误读，仅修改 `spec/dsl/mlir_gen.md` 与 `spec/dsl/emit_mlir.md`，严禁改动 `spec/dialect/*`，不改 `spec/dsl/ast.md`。
改动：
- `spec/dsl/mlir_gen.md`：
  - 最小示例改为“上游显式提供 `trip_count = 2`”，避免与默认 `trip_count = 1` 口径冲突。
  - 明确 `step==0` 或 `trip_count<=0` 必须报错，不得 silent fallback；补充测试目标与 MGEN-015B 映射建议。
- `spec/dsl/emit_mlir.md`：
  - 补充 `step==0` 或 `trip_count<=0` 的报错/unsupported 约束，避免非法边界误读；补充测试目标与 EMIT-010B 映射建议。
结论：完成修复；`git diff --name-only` 仅包含 `spec/dsl/mlir_gen.md` 与 `spec/dsl/emit_mlir.md`；未运行测试（spec-only 变更）。

## T-20260404-eba15982 复审结论（trip_count operation 层 spec 修复复审）

- 审查时间：2026-04-04 20:25:00 +0800
- worktree：`/home/lfr/kernelcode_generate/wt-20260404-scf-symbolic-tripcount-spec`
- 记录文件：`agents/codex-multi-agents/log/task_records/2026/14/20260404-scf-symbolic-tripcount-spec.md`

### 复审点逐条核对（证据）

1) diff 范围硬断点
- `git diff --name-only` 仅包含：
  - `spec/dsl/mlir_gen.md`
  - `spec/dsl/emit_mlir.md`
- 未触碰：
  - `spec/dialect/*`
  - `spec/dsl/ast.md`

2) 锚点一致性（MGEN-015A/015B 与 EMIT-010A/010B）
- `spec/dsl/mlir_gen.md:294`：`MGEN-015A`
- `spec/dsl/mlir_gen.md:295`：`MGEN-015B`
- `spec/dsl/emit_mlir.md:247`：`EMIT-010A`
- `spec/dsl/emit_mlir.md:248`：`EMIT-010B`
- 结论：编号无冲突，A/B 语义表述对齐（均强调默认 `trip_count=1` 合同、end 规范化承载、非法边界必须失败、禁止 silent fallback）。

3) 示例口径修复（“上游显式提供 trip_count=2”，默认=1 清晰）
- `spec/dsl/mlir_gen.md:92-95` 示例已明确“上游显式提供 `trip_count = 2`”，并以 `end = start + step * trip_count`（`s + 2*k`）形式显式承载，避免被误读为“实现侧自动推导 trip_count=2”。
- `spec/dsl/mlir_gen.md:50` 明确默认 `trip_count = 1`（scf/index 用 `index` 常量 `1`，symbol.for 用 `!symbol.int<"1">`）。

4) 非法边界口径（`step==0`、`trip_count<=0` 必须报错且不得 fallback）
- `spec/dsl/mlir_gen.md:52`：若可静态判定 `step==0` 或 `trip_count<=0` 必须报错，且不得 silent fallback/不得默认当作 `1`。
- `spec/dsl/emit_mlir.md:44`：同样要求 emit 阶段在可静态判定时必须报错/unsupported，禁止 silent fallback/禁止默认当作 `1`。

5) 口径隔离（无 pipeline/lowered IR/gen_kernel/codegen 混入）
- 复核：本次改动未新增 pipeline/lowered IR/gen_kernel/codegen 作为“完成标志”；仅保留既有负向约束“不得把 pipeline/lowered IR/gen_kernel 当成完成条件”。

### 漏洞/风险排查（6 类）

- 输入校验绕过：新增非法边界失败合同，降低绕过为“静默执行/默认=1”的风险。
- 类型/形状绕过：默认=1 与 end 规范化承载写清，降低实现侧私自推导导致类型漂移的风险。
- 边界越界：对非法步长/非法次数直接失败，降低 `it` 用于 DMA offsets 时的越界风险。
- 错误处理缺失：明确“必须报错/unsupported”与“不得 silent fallback”，避免错误被吞。
- 状态污染：失败合同减少 emit/符号表部分更新后继续发射导致的污染风险。
- 资源释放问题：非法边界直接失败，避免无限/超大循环触发资源耗尽风险。

### 最终结论

- 结论：**通过**
- 备注：纯 spec 复审任务，无需 pytest；证据以 diff/锚点定位为准。

时间：2026-04-04 20:04:01 +0800
经办人：李白
任务：T-20260404-02ae1778
任务目标：合并 `wt-20260404-scf-symbolic-tripcount-spec` 的 operation 层隐式 `trip_count` spec 收口；合入范围仅限 `spec/dsl/mlir_gen.md`、`spec/dsl/emit_mlir.md` 与当前记录文件；严禁带入 `spec/dialect/*`、`spec/dsl/ast.md` 或实现/测试文件；合并后清理 worktree。
改动：
- 合并范围确认：
  - `git -C wt-20260404-scf-symbolic-tripcount-spec status --short` 仅包含 `spec/dsl/mlir_gen.md`、`spec/dsl/emit_mlir.md` 与当前记录文件。
- 合入主仓内容：
  - `spec/dsl/mlir_gen.md`：明确默认 `trip_count=1`、示例改为上游显式提供 `trip_count=2`，并补充 `step==0`/`trip_count<=0` 必须报错、不得 silent fallback。
  - `spec/dsl/emit_mlir.md`：补充非法边界必须报错/unsupported 的合同口径与测试映射建议。
- 验证：
  - 未新增测试；纯 spec 变更沿用链路复审结论。
  - `git diff --check -- spec/dsl/mlir_gen.md spec/dsl/emit_mlir.md`（exit 0）。
结论：
- 已完成合并收口；合并范围仅限上述 2 个 spec 文件与当前记录文件。
- 阻塞点：无。
- 下一步建议：无。
