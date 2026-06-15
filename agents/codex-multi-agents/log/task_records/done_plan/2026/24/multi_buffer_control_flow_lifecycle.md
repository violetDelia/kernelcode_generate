# multi_buffer_control_flow_lifecycle 正式候选 Candidate 1

## 文档信息

- 状态：正式候选；已完成两轮 `subagent` strict review、用户待确认项收口和 `守护最好的爱莉希雅` 本人守护最终检验；唯一计划级任务 `T-20260613-6ccd1b8f` 已完成 execute / review，本次回写 archive_acceptance 计划书入档验收结论。
- 用户需求来源：2026-06-13 用户指出 `24-multi-buffer-analysis.mlir` 中 `scf.if` 内使用的 alloc 没有被 `multi-buffer-analysis` 标出，且 loop / if 没有可反查编号；用户确认控制流编号不使用 `multi_buffer.*` 前缀，不需要 `analysis.control_path`，需要 pass 内部分析 if 路径，并要求 analysis + apply 让所有满足规则的 alloc 都能被标注和变换。
- 计划目标文件：`ARCHITECTURE/plan/multi_buffer_control_flow_lifecycle.md`
- 目标 `spec`：[`spec/pass/memory/multi_buffer.md`](../../spec/pass/memory/multi_buffer.md)、[`spec/dialect/symbol.md`](../../spec/dialect/symbol.md)
- 目标公开 API：现有 `MultiBufferAnalysisPass` / `MultiBufferApplyPass` / `MultiBufferPass` class 与 registry 名称保持不变；新增公开 IR attrs `analysis.loop_id` 与 `analysis.if_id`，其值直接采用 `name-depth` 形式，例如 `"loop5-2"`、`"if3-2"`。
- 目标功能实现：[`kernel_gen/passes/memory/multi_buffer.py`](../../kernel_gen/passes/memory/multi_buffer.py)、[`kernel_gen/dialect/symbol/operation/control_flow.py`](../../kernel_gen/dialect/symbol/operation/control_flow.py)
- 目标测试：[`test/passes/memory/test_multi_buffer.py`](../../test/passes/memory/test_multi_buffer.py)、[`test/dialect/symbol/test_symbol.py`](../../test/dialect/symbol/test_symbol.py)、[`test/passes/test_registry.py`](../../test/passes/test_registry.py)
- 目标 dump 验收来源：
  - `/home/lfr/kernelcode_generate/kernel/dump/matmul/inputs_static_tile_static_present_bias/matmul_inputs_static_tile_static_kernel/23-canonicalize.mlir`
  - `/home/lfr/kernelcode_generate/kernel/dump/matmul/inputs_static_tile_static_present_bias/matmul_inputs_static_tile_static_kernel/24-multi-buffer-analysis-if-path-expected.mlir`
  - `/home/lfr/kernelcode_generate/kernel/dump/matmul/inputs_static_tile_static_present_bias/matmul_inputs_static_tile_static_kernel/24-multi-buffer-analysis.mlir`
  - `/home/lfr/kernelcode_generate/kernel/dump/matmul/inputs_static_tile_static_present_bias/matmul_inputs_static_tile_static_kernel/25-multi-buffer-apply.mlir`
- 目标 `expectation`：本轮按用户推进口径选择不预置新 expectation；计划级 execute 不得修改 `expectation/` 本体。

### 用户确认记录

- Q1 已确认：控制流编号使用通用 `analysis.loop_id` / `analysis.if_id`，不使用 `multi_buffer.loop_id`。
- Q2 已确认：不新增 `analysis.control_path`。
- Q3 已确认：`multi-buffer-analysis` 第一件事是给控制流编号，只给没有编号的控制流 op 补编号；后续其它 pass 已经编号的值必须保留。
- Q4 已确认：`multi-buffer-analysis` 第二件事是分析每个 alloc memory 的使用点和更新点，按规则在 `dma.alloc` 上写 `multi_buffer.update_points/use_points/num`；更新点和使用点都是列表，不是单值。
- Q5 已确认：需要分析 if 路径；if 参与候选推导，但不把路径复制成 alloc 上的 `control_path`。
- Q6 已确认：buffer 个数按更新点列表和使用点列表的关系判断；`update_points` 与 `use_points` 表达完整分析关系，`multi_buffer.num` 表达 apply 使用的 stage 数。
- Q7 已确认：一个 alloc 可能有多个 raw 使用点；例如 `%12` 的 `%30 = dma.reinterpret(%12, ...)` 就是 raw use point，后续 `scf.if` 内 `%45 = dma.reinterpret(%12, ...)` 也是 raw use point。analysis 必须收集所有 raw use/update points，并把控制流 domain 写入 `multi_buffer.update_points/use_points`。
- Q8 已确认：控制流 id 本身编码深度，不再新增 `analysis.loop_depth` 或 `analysis.if_depth`；格式为 `name-depth`，例如 pattern1 外层 M loop 是 `"loop4-1"`、N loop 是 `"loop5-2"`、K loop 是 `"loop6-3"`，bias if 位于 N loop body，深度取所在 block / enclosing loop 深度，因此是 `"if3-2"`。
- Q9 已确认：`multi_buffer.num` 按优先级判断。第一优先级是 `update_points = ["main"]` 的可证明候选写 `"1"`，即使最大使用深度大于 2 也不写 `"2"`；第二优先级是非 main 候选只有 `update_points + use_points` 中所有点都位于当前可分析区域的最大控制流 depth 时才写 `"auto"` / `memory_stage`；其它非 main 场景写固定 `"2"`。多深度使用点不各自推进 ring；例如 `%11` 的 current/advance 在 `loop5-2` 生命周期，`if3-2` 和 `loop6-3` 使用 `loop5-2` 的 current slot。
- Q10 已确认：本轮不预置新 `expectation/pass/multi_buffer/**` 合同资产，只用 spec + pytest + dump 验收；execute/review/merge/管理员仍不得修改 expectation。

### 本计划待用户确认项

- 无。

## 计划级任务

- 当前状态：唯一计划级任务 `T-20260613-6ccd1b8f` 已完成 execute 与 review，通过 archive_acceptance 后进入 merge/归档。
- 正式计划只允许一个计划级 `execute` 大任务。
- 固定流转：`execute -> review -> archive_acceptance -> merge/归档`。
- 若 `review` 或 `archive_acceptance` 不通过，回到同一个 `execute`，不得另设 `refactor` 阶段。

| 计划任务 | 任务类型 | worktree | 记录文件 |
| --- | --- | --- | --- |
| `multi-buffer-control-flow-lifecycle` | `execute` | 待管理员创建 | `agents/codex-multi-agents/log/task_records/2026/24/20260613-multi-buffer-control-flow-lifecycle.md` |

## 迭代审阅记录

### 收敛轮次 1：subagent strict review

- 审阅对象：Descartes。
- 输入标准包：根 `AGENTS.md`、`agents/codex-multi-agents/agents/榕/榕.prompt.md`、`agents/standard/计划书标准.md`、`agents/standard/expectation任务规则.md`、`agents/standard/实现文件规范.md`、当前计划全文、当前待确认项为无、禁止修改面和必过验收命令。
- 严格通过口径：仍有公开 API 未确认、expectation 授权不清、buffer num 规则不闭合、analysis/apply 候选不一致、小任务卡不可执行、验收不可复现或可读性/维护性可执行返工项时，不得通过。
- 发现问题：结论不通过；问题为讨论稿尚非正式候选、ignored/untracked 文件未进入 tracked/index、S5 曾被写成不可执行说明、expectation ignored/untracked 不能只用 `git diff` 证明未改、S3 的目标 dump 名称与 present-bias 验收对象不一致。
- 主线处理：保持讨论稿状态，不提前请求守护；S3 已修正为 present-bias；S5 改为可执行禁止修改面核对任务；静态门禁补 expectation status/content 指纹前后比对；formal candidate tracked/index 证据留到两轮收敛后处理。
- 状态：不通过，已按最小需改项修订，等待 Round 2 复审。

### 收敛轮次 2：subagent strict review

- 审阅对象：Descartes。
- 输入标准包：基于 Round 1 修订后的最新计划全文或 diff、上一轮问题、本轮收口摘要、其它标准包、用户确认记录。
- 严格通过口径：所有已发起或计划要求的 subagent 审阅任务均无阻断、无最小需改项、无待确认项，才允许进入守护最终检验。
- 发现问题：结论通过；无阻断项、无最小需改项、无待确认项。Round 1 的 S5 可执行性、expectation ignored/untracked 指纹、present-bias 目标、`analysis.loop_id/if_id`、`name-depth`、if depth、`%11/%12/%13 num="2"`、`%15/%16/%20/%21 auto`、`SymbolForOp` extra attrs round-trip 均已核对通过。
- 主线处理：内容不再返工；进入正式候选 tracked/index 证据补齐与守护最终检验阶段。
- 状态：通过。

### subagent 收敛结论

- 已发起或计划要求的审阅任务：Round 1 Descartes strict review 已完成且不通过；Round 2 Descartes strict review 已完成且通过。
- 收敛结论：已收敛；当前无阻断项、无最小需改项、无待确认项。
- 遗留项：无内容遗留项；正式候选路径级 tracked/index 证据已补齐，守护最终检验已通过。

### 正式候选 tracked/index 证据

- 正式候选范围仅包含：
  - `ARCHITECTURE/plan/multi_buffer_control_flow_lifecycle.md`
  - `kernel/dump/matmul/inputs_static_tile_static_present_bias/matmul_inputs_static_tile_static_kernel/24-multi-buffer-analysis-if-path-expected.mlir`
- 必须用路径级命令核对：
  - `git ls-files --stage -- ARCHITECTURE/plan/multi_buffer_control_flow_lifecycle.md kernel/dump/matmul/inputs_static_tile_static_present_bias/matmul_inputs_static_tile_static_kernel/24-multi-buffer-analysis-if-path-expected.mlir`
  - `git diff --cached --name-status -- ARCHITECTURE/plan/multi_buffer_control_flow_lifecycle.md kernel/dump/matmul/inputs_static_tile_static_present_bias/matmul_inputs_static_tile_static_kernel/24-multi-buffer-analysis-if-path-expected.mlir`
  - `git status --short --ignored --untracked-files=all -- ARCHITECTURE/plan/multi_buffer_control_flow_lifecycle.md kernel/dump/matmul/inputs_static_tile_static_present_bias/matmul_inputs_static_tile_static_kernel/24-multi-buffer-analysis-if-path-expected.mlir`
  - `git diff --cached --check -- ARCHITECTURE/plan/multi_buffer_control_flow_lifecycle.md kernel/dump/matmul/inputs_static_tile_static_present_bias/matmul_inputs_static_tile_static_kernel/24-multi-buffer-analysis-if-path-expected.mlir`
- 当前 index 中如存在其它既有 staged 文件，不属于本计划候选范围；守护核对时必须按上述路径级命令区分，不得把其它计划候选混入本任务下发。

### 守护最终检验

- 检验对象：`守护最好的爱莉希雅` 本人。
- 检验范围：标准包、公开 API、expectation 权限、禁止修改面、验收命令、小任务卡、正式候选 tracked/index 证据。
- 必过门禁：两轮 subagent strict review 收敛；用户待确认项收口；计划文件进入正式 tracked/index 候选；无越权 diff。
- 结论：通过；`守护最好的爱莉希雅` 本人回执 Candidate 1 守护最终检验通过。
- 阻断项：无。
- 最小需改项：无。
- 待确认项：无。
- 允许事项：允许通知管理员创建唯一计划级 `execute` `multi-buffer-control-flow-lifecycle`；管理员不得创建第二个 execute；execute、review、merge、管理员和替补仍不得修改 expectation 本体，只能读取、运行、引用与记录。
- 守护证据摘要：守护只核对两条正式候选路径 `ARCHITECTURE/plan/multi_buffer_control_flow_lifecycle.md` 与 `kernel/dump/matmul/inputs_static_tile_static_present_bias/matmul_inputs_static_tile_static_kernel/24-multi-buffer-analysis-if-path-expected.mlir`；`git ls-files --stage`、cached name-status、status、`git diff --cached --check`、敏感范围空 diff 均通过；全 index 另有 unrelated `ARCHITECTURE/plan/tuner_select_runtime_cost_choice.md`，未作为本计划证据。

## 当前基线

- `spec/pass/memory/multi_buffer.md` 当前公开合同写明：
  - `multi-buffer-analysis` 只在候选 `dma.alloc` 上写三项临时属性。
  - `multi_buffer.update_point = "loopN"`、`multi_buffer.use_point = "loopN"`、`multi_buffer.num = "auto" | "<positive-int>"`。
  - 以上是旧基线；本计划要把单值 `update_point/use_point` 迁移为列表 `update_points/use_points`。
  - `same-loop staging` 在 `target` 非空时写 `"auto"`，`target is None` 时写固定 `memory_stage`。
  - `loop-local direct use` 写 `"1"`。
  - 不满足条件的 alloc 保持 no-op。
- 当前实现的控制流标签由 `_MultiBufferRewriteRules.region_labels(module)` 内部生成，只给 `SymbolForOp` 分配 `loop1/loop2/...`，且只把标签写到候选 `dma.alloc` 的 `multi_buffer.update_point/use_point`，没有落到 loop op 本体。
- 当前 `SymbolForOp` 使用自定义文本语法，printer/parser 只显式处理 `{iter = ...}`。若直接把 `analysis.loop_id` 写到 `symbol.for`，必须同步保证非 `iter` 属性可打印、可解析、可 round-trip，否则 dump 验收与后续文本测试会失真。
- 当前实现没有 `analysis.if_id`，`scf.if` 没有可反查编号。
- 当前 direct alias / direct use 候选有硬门槛：所有 `access_op.parent_block()` 必须是目标 `symbol.for` 的直接 body。`scf.if` branch block 和 nested `symbol.for` body 会被跳过。
- 当前 `24-multi-buffer-analysis.mlir` 中 pattern0：
  - `%11/%12/%13` 未标 `multi_buffer.*`。
  - `%15/%16/%20/%21` 标为 `loop3` / `auto`。
  - `%12/%13` 在 `scf.if %19` 内通过 `%45`、`dma.broadcast`、`kernel.binary_elewise` 使用。
- 当前 `24-multi-buffer-analysis.mlir` 中 pattern1 同构：
  - `%11/%12/%13` 未标 `multi_buffer.*`。
  - `%15/%16/%20/%21` 标为 `loop6` / `auto`。
- 当前缺口：
  - 用户无法从 IR 里反查 `loop3` 对应哪个 `symbol.for`。
  - 用户无法从 IR 里反查某个 `scf.if` 的编号。
  - `if` 内使用的 alloc 不进入 analysis 候选，apply 也不会变换。
  - analysis 与 apply 都依赖同一直接 body 限制，无法做到“分析到的都能变、需要变的都能分析”。

## 计划目标

- `multi-buffer-analysis` 在执行候选分析前，为所有缺少编号的 `symbol.for` 与 `scf.if` 补通用控制流编号；编号值直接编码深度：

```mlir
symbol.for ... attributes {analysis.loop_id = "loop3-3"} {
  scf.if %cond attributes {analysis.if_id = "if2-2"} {
    ...
  }
}
```

- 已有 `analysis.loop_id` / `analysis.if_id` 必须保留；新增编号必须避开已有编号，不能生成重复 id。
- `symbol.for` 自定义 printer/parser 必须保留 `iter` 之外的普通属性，至少保证 `{iter = #It1, analysis.loop_id = "loop5-2"}` 这类文本可解析、可打印、可 round-trip。
- `multi_buffer.update_points/use_points` 引用同一套 `analysis.loop_id` / `analysis.if_id` 字符串；列表中允许同时出现 loop 和 if：

```mlir
%buf = "dma.alloc"(...)
  {
    multi_buffer.update_points = ["loop2-2"],
    multi_buffer.use_points = ["loop2-2", "loop3-3", "if2-2"],
    multi_buffer.num = "2"
  }
```

- `multi-buffer-analysis` 内部必须能沿 parent chain 分析 if 路径：

```text
use op -> branch block -> scf.if(ifN) -> loop body -> symbol.for(loopN)
```

- 不新增 `analysis.control_path`，不在 alloc 上复制 if 路径。
- analysis 与 apply 使用同一套 candidate discovery。凡 analysis 能写三项属性的候选，apply 必须能重新识别并按同一规则消费；凡 apply 需要变换的合法候选，analysis 必须能提前标出。
- 对用户点名 dump 的完成态：
  - pattern0 `%11` 应标为 `update_points = ["loop2-2"]`、`use_points = ["loop2-2", "loop3-3", "if2-2"]`、`num = "2"`，并在 `loop2-2` 生命周期 current/advance。
  - pattern0 `%12/%13` 应标为 `update_points = ["loop2-2"]`、`use_points` 覆盖 `loop2-2` 与对应 `if2-2`、`num = "2"`，并在 apply 后变成 ring。
  - pattern0 `%15/%16/%20/%21` 继续标为 `update_points/use_points = ["loop3-3"]`、`num = "auto"` 并在 apply 后变成 ring。
  - pattern1 `%11` 应标为 `update_points = ["loop5-2"]`、`use_points = ["loop5-2", "loop6-3", "if3-2"]`、`num = "2"`，并在 `loop5-2` 生命周期 current/advance。
  - pattern1 `%12/%13` 应标为 `update_points = ["loop5-2"]`、`use_points` 覆盖 `loop5-2` 与对应 `if3-2`、`num = "2"`，并在 apply 后变成 ring。
  - pattern1 `%15/%16/%20/%21` 继续标为 `update_points/use_points = ["loop6-3"]`、`num = "auto"` 并在 apply 后变成 ring。

## 非目标

- 不新增 `analysis.control_path`。
- 不新增 `multi_buffer.loop_id` 或 `multi_buffer.if_id`。
- 不修改 `MultiBufferAnalysisPass`、`MultiBufferApplyPass`、`MultiBufferPass` 构造签名、registry 名称或公开 option。
- 不修改 `SymbolForOp` 构造签名；只扩展其现有自定义文本语法对额外 attrs 的保留能力。
- 不新增 package re-export。
- 不在本计划中引入 `loop-soft-pipeline`、producer-consumer event attr、async token、barrier、`arch.sign` 或 `arch.wait`。
- 不把任意不可证明 alias、跨 sibling region escape、多 free、missing free、已有 ring current block 等既有 no-op 边界放宽成强行改写。
- 不要求 execute 修改 `expectation/`；本轮不预置新 expectation，execute 只读/运行/记录既有 expectation（如有）。
- 不修改 `.skills/`、`agents/standard/`、`AGENTS.md`、`TODO.md`、`DONE.md`。

## 方案比较与选型

### 方案 A：只给 loop op 落编号，不改 if 分析

- 内容：新增 `analysis.loop_id`，让 `loop3-3` 可反查；保持 if branch use no-op。
- 优点：改动最小。
- 缺点：不能解决用户点名的 if 内 alloc 不分析、不变换；analysis/apply 仍无法覆盖 `%12/%13`。
- 结论：不采用。

### 方案 B：给 loop / if 都编号，并允许候选穿过 `scf.if`

- 内容：补 `analysis.loop_id` / `analysis.if_id`，id 值直接编码 `name-depth`；candidate discovery 允许 access op 位于目标 loop body 直接 op、目标 loop 内 `scf.if` branch、以及目标 loop 内可证明嵌套 loop；先收集 raw update/use points，再在 alloc 上写完整 `update_points/use_points` 列表。
- 优点：解决当前 dump 缺口；不新增 control path；analysis/apply 共享候选能力；输出 IR 可反查控制流编号。
- 缺点：需要重写候选发现和 insertion/advance 定位；capacity/reserved 规则必须重新验收。
- 结论：推荐。

### 方案 C：新增 `analysis.control_path`，alloc 上直接记录路径

- 内容：在 alloc 上额外写 `analysis.control_path = ["loop2", "if1"]`。
- 优点：调试直观。
- 缺点：用户已明确不需要；会增加公开 IR 合同和维护成本。
- 结论：不采用。

## 公开 API 设计

### 功能简介

- `multi-buffer-analysis` 补充通用控制流编号，并在可证明 alloc lifecycle 上写 multi-buffer 三项属性。
- `multi-buffer-apply` 消费三项属性，把同一候选改写为 ring。
- `multi-buffer` facade 行为仍等价于 analysis 后接 apply。

### API 列表

- `class MultiBufferAnalysisPass(memory_stage: int = 2, fold: bool = True, target: str | None = None)`
- `MultiBufferAnalysisPass.from_options(options: dict[str, str]) -> MultiBufferAnalysisPass`
- `MultiBufferAnalysisPass.apply(ctx: Context, module: ModuleOp) -> None`
- `class MultiBufferApplyPass(fold: bool = True, target: str | None = None, alignment: int = 1024)`
- `MultiBufferApplyPass.from_options(options: dict[str, str]) -> MultiBufferApplyPass`
- `MultiBufferApplyPass.apply(ctx: Context, module: ModuleOp) -> None`
- `class MultiBufferPass(memory_stage: int = 2, fold: bool = True, target: str | None = None, alignment: int = 1024)`
- `MultiBufferPass.from_options(options: dict[str, str]) -> MultiBufferPass`
- `MultiBufferPass.apply(ctx: Context, module: ModuleOp) -> None`

### 新增公开 IR attr

| attr | 写入对象 | 值 | 语义 |
| --- | --- | --- | --- |
| `analysis.loop_id` | `symbol.for` | `"loopN-D"` | 通用 loop 编号，`N` 是 module walk 序号，`D` 是控制流深度；供 multi-buffer 与后续分析反查控制流。 |
| `analysis.if_id` | `scf.if` | `"ifN-D"` | 通用 if 编号，`N` 是 module walk 序号，`D` 是控制流深度；供分析内部和调试反查 if。 |

- 用户确认来源：2026-06-13 用户明确确认不用 `multi_buffer.loop_id`，采用通用 `analysis.*`；用户明确确认不需要 `analysis.control_path`。
- 编号规则：
  - 只给缺少编号的控制流 op 补编号。
  - 已有 `analysis.loop_id` / `analysis.if_id` 保留原值。
  - 新编号 name 部分按 module walk 顺序分配。
  - 新编号 depth 部分按控制流分析深度写入 id：外层 pattern loop 深度为 1，下一层为 2，K loop 深度为 3；`scf.if` 深度取其所在 block / enclosing loop 深度，不因为 if 自身再加一，因此 bias if 位于 N loop body 时深度为 2。
  - 新编号必须避开 module 内已有同类编号，不能重复。
  - `analysis.loop_id` 和 `analysis.if_id` 分属不同命名空间；`loop1` 与 `if1` 不冲突。
  - 不新增 `analysis.loop_depth` / `analysis.if_depth`，深度必须从 id 文本中直接读出。
- `SymbolForOp` 文本规则：
  - `iter` 仍是必需属性。
  - `iter` 之外的普通属性必须保留在同一个属性字典中打印和解析。
  - round-trip 后 `analysis.loop_id` 不得丢失，也不得改变已有 id。

### multi-buffer attr 语义保持

| attr | 写入对象 | 语义 |
| --- | --- | --- |
| `multi_buffer.update_points` | `dma.alloc` | 候选 memory 更新点列表；每项为 `"main"` 或某个 `analysis.loop_id` / `analysis.if_id`。 |
| `multi_buffer.use_points` | `dma.alloc` | 候选 memory 使用点列表；每项为某个 `analysis.loop_id` / `analysis.if_id`，保留完整 raw domain 列表。 |
| `multi_buffer.num` | `dma.alloc` | `"1"`、固定正整数或 `"auto"`。 |

## Buffer 个数规则

本计划先为每个 alloc 收集 raw update/use points，再把控制流 domain 列表写到 IR，最后按列表关系确定 `multi_buffer.num`。

- `raw_use_points`：所有直接使用 alloc 或 alias 的原始 op 点，例如 `%30 = dma.reinterpret(%12, ...)`、`%45 = dma.reinterpret(%12, ...)`、`dma.deslice(%30, ...)`。raw points 是 pass 内部分析数据，不写成 `analysis.control_path`。
- `raw_update_points`：所有可证明更新 alloc 或 alias memory 的原始 op 点；例如 matmul / binary / deslice 这类会写目标 memory 的 op。
- `raw_use_domain` / `raw_update_domain`：每个 raw point 所属的控制流 domain，例如 `main`、`loop2-2`、`if2-2`。
- `multi_buffer.update_points` / `multi_buffer.use_points`：写入 IR 的完整 domain 列表，按出现顺序去重；不写 `effective_update_point` / `effective_use_point`。
- apply 若需要调度点，必须从列表和控制流结构内部推导，不能依赖额外公开 effective attr。
- 若多个 raw use points 不能归约到一个安全生命周期，且也不能按多个 disjoint lifecycle 保守变换，则该 alloc no-op。

### 1. `num = "1"`

优先用于 update points 只包含 `main` 且使用点可在单 slot 生命周期内证明的候选：

- `multi_buffer.update_points = ["main"]`。
- `multi_buffer.use_points` 可以包含一个或多个可证明 use domain。
- 该类候选只需要单 slot，因为 update point 不在 loop 内重复推进。
- 即使 `use_points` 的最大深度大于 2，只要 update 仍是 `main` 且生命周期可证明，也写 `multi_buffer.num = "1"`。
- 用户点名 present-bias dump 的 `%11/%12/%13` 当前不属于本类；它们的更新点落在 N loop 相关控制域，按非 main depth 规则处理。

### 2. `num = "auto"` 或固定 `memory_stage`

用于非 main 候选中 update/use 点全部位于当前可分析区域最大 depth 的 loop-local / deepest-point staging：

- `target != None` 时写 `"auto"`。
- `target is None` 时写固定 `memory_stage`。
- 同一个 target loop、同一个 insertion scope、同一个 memory space 的 auto 候选共享同一个 runtime `num`。
- 用户点名 dump 中：
  - pattern0 `%12/%13` 的 update/use points 都在 depth 2，不是当前 pattern 最大 depth 3，写 `2`。
  - pattern0 `%15/%16` 是 `loop3-3` 的 tsm A/B staging，同 space 共享 `auto`。
  - pattern0 `%20` 是 `loop3-3` 的 tlm1 staging，独立按 tlm1 capacity 算 `auto`。
  - pattern0 `%21` 是 `loop3-3` 的 tlm2 staging，独立按 tlm2 capacity 算 `auto`。
  - pattern1 `%12/%13` 的 update/use points 都在 depth 2，不是当前 pattern 最大 depth 3，写 `2`。
  - pattern1 `%15/%16/%20/%21` 同理是 `loop6-3`，但 tlm1/tlm2 分配按实际 memory space。

### 3. `num = "2"`

用于剩余不同点场景：

- `update_points` 不只包含 `main`，且存在 update/use point 没有位于当前可分析区域最大 depth，但能证明固定双 buffer 足够覆盖跨点传递。
- 典型例子是 `update_points = ["loop5-2"]`、`use_points = ["loop5-2", "loop6-3", "if3-2"]`；最大 depth 为 3，但 update point 在 depth 2，所以写 `"2"`。
- 第一版按固定双 buffer 处理，写 `multi_buffer.num = "2"`。

### 4. apply 的 capacity / reserved 规则

- `slot_bytes(candidate) = element_bytes * product(slot_shape_dims_from_alloc)`。
- `aligned_slot_bytes = align_unit(slot_bytes, alignment)`。
- 固定 num 候选的 reserved bytes 为 `fixed_num * aligned_slot_bytes`；`num = "1"` 与 `num = "2"` 都按固定 num 参与 reserved。
- auto group 的 `available` 必须扣除同 memory space、同 insertion scope 内与本 auto group 生命周期重叠的固定候选、已证明会共存的非候选 alloc，以及已物化 ring backing。
- `group_unit = sum(aligned_slot_bytes(candidate) for candidate in same auto group)`。
- `auto_num = available floordiv group_unit`。
- `auto_num <= 0` 或 footprint 无法证明时，该 auto group no-op；固定 `num = "1"` / `"2"` 候选不因某个 auto group no-op 自动取消。
- 不同 memory space 独立计算；同 memory space 但生命周期不重叠的 group 可独立计算，但第一版只在可证明时放宽，否则按重叠保守扣除。

## 候选分析规则

### 控制流编号阶段

1. 遍历 module。
2. 收集已有 `analysis.loop_id` 与 `analysis.if_id`。
3. 对缺少 `analysis.loop_id` 的 `SymbolForOp` 补 `loopN-D`。
4. 对缺少 `analysis.if_id` 的 `scf.IfOp` 补 `ifN-D`。
5. 不写 `analysis.control_path`。
6. 不写 `analysis.loop_depth` / `analysis.if_depth`；深度必须编码在 id 字符串里。
7. `symbol.for` 的 `analysis.loop_id` 必须能通过自定义文本语法打印和解析；parser 不得因为属性字典中有 `analysis.loop_id` 而失败。

### lifecycle 分析阶段

对每个 `dma.alloc`：

1. 收集唯一 `dma.free`；missing free、多 free、free 早于可证明生命周期仍 no-op。
2. 收集 direct alias：`dma.reinterpret`、`dma.view`、`dma.reshape`、`dma.subview`。
3. 收集 direct memory access：`dma.broadcast/copy/deslice/fill/load/slice/store/transpose`、`kernel.binary_elewise/img2col1d/img2col2d/matmul`。
4. 对 alias result 的 memory access 同样收集；第一版仍只支持一层 direct alias，不把多层 alias 作为本计划目标。
5. 对每个 access op 计算控制流父链：

```text
access op
  -> parent block
  -> optional scf.if branch
  -> optional nested symbol.for
  -> target symbol.for
```

6. 为每个 access 记录 raw use point；raw point 是具体 alias/use op，而不是只记录 enclosing loop。
7. 为每个 raw use point 记录 raw use domain；domain 可为直接 enclosing loop、enclosing if，或 after-if / after-loop 所在 enclosing point，格式统一为 `name-depth`。
8. 为每个 raw update point 记录 raw update domain，并按出现顺序去重写入 `multi_buffer.update_points`。
9. 将 raw use domains 按出现顺序去重写入 `multi_buffer.use_points`。
10. apply 内部根据 update/use 列表和控制流结构推导 current/advance 调度点；调度点不写成公开 `effective_*` attr。
11. 若 raw use points 分散到 sibling loop / sibling if 且无法归约出安全生命周期，no-op。
12. 若 access 在目标生命周期外 escape，no-op。
13. 若候选命中已有 ring current block，保持 no-op，避免重复 ring。

### insertion / advance 定位

- `current_ring` 插入目标 loop body 内、第一条需要该 alloc slot 的 alias/use 之前。
- 对 alias 在 loop body、真实 use 在 `scf.if` branch 内的情况，`current_ring` 插在 alias 之前。
- 对真实 first use 在 `scf.if` branch 内且 loop body 没有 alias 的情况，第一版允许把 `current_ring` 插在 `scf.if` 之前，保证 then/else branch 都被支配；若无法证明支配，no-op。
- `advance_ring` 插在目标 loop body 中最后一个 access 之后；若最后 access 位于 `scf.if` branch 内，则插在 enclosing `scf.if` 之后。
- 若目标 block 有 terminator，则 `advance_ring` 插在 terminator 前。
- nested K loop 内的 staging 仍在 K loop body 内 current/advance；outer scratch 在 outer N loop body 内 current/advance，不在 K loop 每轮 advance。

## 用户点名 dump 的预期分析结果

以 `/home/lfr/kernelcode_generate/kernel/dump/matmul/inputs_static_tile_static_present_bias/matmul_inputs_static_tile_static_kernel/23-canonicalize.mlir` 为 before 基线，并以同目录 `24-multi-buffer-analysis-if-path-expected.mlir` 为本轮讨论期预期 analysis 结果。

### 控制流编号预期

```text
entry dispatcher scf.if %6 -> analysis.if_id = "if1-1"

pattern0:
  symbol.for %22 -> analysis.loop_id = "loop1-1"
  symbol.for %26 -> analysis.loop_id = "loop2-2"
  symbol.for %32 -> analysis.loop_id = "loop3-3"
  scf.if %19     -> analysis.if_id = "if2-2"

pattern1:
  symbol.for %22 -> analysis.loop_id = "loop4-1"
  symbol.for %26 -> analysis.loop_id = "loop5-2"
  symbol.for %32 -> analysis.loop_id = "loop6-3"
  scf.if %19     -> analysis.if_id = "if3-2"
```

### pattern0 alloc 标注预期

raw update/use 说明：

- `%11` update points 为 `["loop2-2"]`；use points 覆盖 `loop2-2` 的 `%29` alias / output deslice、`loop3-3` 的 `kernel.matmul`、`if2-2` 的 `kernel.binary_elewise`；最大 depth 为 3 但 update depth 为 2，因此 `num = "2"`，advance 仍放在 `loop2-2` 生命周期。
- `%12` update points 为 `["loop2-2"]`；use points 至少包含 `%30 = dma.reinterpret(%12, ...)` 所在 `loop2-2` 和 `%45 = dma.reinterpret(%12, ...)` 所在 `if2-2`；二者都不是当前 pattern 最大 depth 3，因此 `num = "2"`。
- `%13` update points 为 `["loop2-2"]`；use points 至少包含 `%31 = dma.reinterpret(%13, ...)` 所在 `loop2-2` 和 if 内 `dma.broadcast` / `kernel.binary_elewise` 所在 `if2-2`；二者都不是当前 pattern 最大 depth 3，因此 `num = "2"`。
- `%15/%16/%20/%21` update/use points 均为 `["loop3-3"]`。

```mlir
%11 = "dma.alloc"(...)
  {multi_buffer.update_points = ["loop2-2"],
   multi_buffer.use_points = ["loop2-2", "loop3-3", "if2-2"],
   multi_buffer.num = "2"}

%12 = "dma.alloc"(...)
  {multi_buffer.update_points = ["loop2-2"],
   multi_buffer.use_points = ["loop2-2", "if2-2"],
   multi_buffer.num = "2"}

%13 = "dma.alloc"(...)
  {multi_buffer.update_points = ["loop2-2"],
   multi_buffer.use_points = ["loop2-2", "if2-2"],
   multi_buffer.num = "2"}

%15 = "dma.alloc"(...)
  {multi_buffer.update_points = ["loop3-3"],
   multi_buffer.use_points = ["loop3-3"],
   multi_buffer.num = "auto"}

%16 = "dma.alloc"(...)
  {multi_buffer.update_points = ["loop3-3"],
   multi_buffer.use_points = ["loop3-3"],
   multi_buffer.num = "auto"}

%20 = "dma.alloc"(...)
  {multi_buffer.update_points = ["loop3-3"],
   multi_buffer.use_points = ["loop3-3"],
   multi_buffer.num = "auto"}

%21 = "dma.alloc"(...)
  {multi_buffer.update_points = ["loop3-3"],
   multi_buffer.use_points = ["loop3-3"],
   multi_buffer.num = "auto"}
```

### pattern1 alloc 标注预期

raw update/use 说明：

- pattern1 与 pattern0 同构，`%11/%12/%13` 的 update points 为 `["loop5-2"]`。
- `%11` use points 为 `["loop5-2", "loop6-3", "if3-2"]`，最大 depth 为 3 但 update depth 为 2，因此 `num = "2"`，advance 仍放在 `loop5-2` 生命周期；`%12/%13` use points 为 `["loop5-2", "if3-2"]`，不在当前 pattern 最大 depth 3，因此同样 `num = "2"`。
- `%15/%16/%20/%21` 的 update/use points 均为 `["loop6-3"]`。

```mlir
%11 = "dma.alloc"(...)
  {multi_buffer.update_points = ["loop5-2"],
   multi_buffer.use_points = ["loop5-2", "loop6-3", "if3-2"],
   multi_buffer.num = "2"}

%12 = "dma.alloc"(...)
  {multi_buffer.update_points = ["loop5-2"],
   multi_buffer.use_points = ["loop5-2", "if3-2"],
   multi_buffer.num = "2"}

%13 = "dma.alloc"(...)
  {multi_buffer.update_points = ["loop5-2"],
   multi_buffer.use_points = ["loop5-2", "if3-2"],
   multi_buffer.num = "2"}

%15/%16/%20/%21 = "dma.alloc"(...)
  {multi_buffer.update_points = ["loop6-3"],
   multi_buffer.use_points = ["loop6-3"],
   multi_buffer.num = "auto"}
```

### apply 后结构预期

- pattern0 / pattern1 每个 pattern 原 7 个 typed `dma.alloc` 都应被 ring backing + `dma.make_ring` + `dma.current_ring` + `dma.advance_ring` 替代。
- 原 typed free 删除；新 i8 backing free 保留。
- `%11/%12/%13` 对应 ring 的 current 插在 N loop body 中对应 first alias/use 前，advance 插在 N loop body 最后一次使用后；多深度 use 只影响 `num`，不让 `loop3-3` / `loop6-3` 或 `if2-2` / `if3-2` 单独推进 `%11`。
- `%15/%16/%20/%21` 对应 ring 的 current/advance 保持在 K loop body。
- `scf.if` branch 内 `dma.deslice` / `dma.broadcast` / `kernel.binary_elewise` 继续使用由 current slot 派生的 view。
- `kernel.matmul` 的累加语义不变：acc/output scratch `%11` 对应 current slot 在整个 K loop、bias if 和 output deslice 期间保持同一 slot；不得在 K loop 内 advance `%11`。

## 完成态定义

- `multi-buffer-analysis` 输出中所有 `symbol.for` 带 `analysis.loop_id`，所有 `scf.if` 带 `analysis.if_id`。
- 已有 `analysis.loop_id` / `analysis.if_id` 不被覆盖。
- 用户点名 dump 中 `%11/%12/%13/%15/%16/%20/%21` 在两个 pattern 内全部获得正确 `multi_buffer.*` 属性。
- `multi-buffer-apply` 能消费同一批属性，两个 pattern 内 7 个 typed alloc 均被改写为 ring。
- `multi-buffer` facade 等价于 analysis + apply。
- target auto capacity 计算仍满足 existing contract，并在新增 fixed `num=1` / `"2"` ring 后避免同 space auto 过度占用。
- 既有 no-op 边界仍保持：missing free、free before loop、multi-free、alias escape、已有 ring、partial pair、不可证明 nested/sibling region escape。
- `spec/pass/memory/multi_buffer.md`、文件级 API 列表、pytest 和 dump 验收同步。

## 验收设计

### Diff 反推 pytest

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/passes/memory/test_multi_buffer.py test/passes/test_registry.py
```

### Dump 验收

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 kernel/matmul/inputs_static_tile_static.py
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 kernel/matmul/inputs_static_tile_dynamic.py
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 kernel/matmul/inputs_dynamic_tile_dynamic.py
```

验收核对：

- `inputs_static_tile_static_present_bias/.../24-multi-buffer-analysis.mlir` 包含 `analysis.loop_id` / `analysis.if_id`。
- 同文件 pattern0 / pattern1 各 7 个 typed alloc 均带预期 `multi_buffer.*`。
- `25-multi-buffer-apply.mlir` 不残留上述 typed alloc 的原生命周期，包含对应 ring/current/advance。
- if branch 内 bias / broadcast / binary add 使用 current slot 派生 view。

### 当前必过 expectation 合同验收

- 本轮不新增或修改 `expectation/pass/multi_buffer/**`，不列当前必过 expectation 合同验收。
- 若后续用户单独授权 expectation 预置，必须回到架构侧修订计划并重新审阅。

### 静态门禁

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/repo_conformance/test_private_api_boundaries.py test/tools/test_kernel_code_error_static_gate.py
git diff --check
git diff --cached --check
git diff --name-status -- expectation .skills agents/standard AGENTS.md TODO.md DONE.md
git diff --cached --name-status -- expectation .skills agents/standard AGENTS.md TODO.md DONE.md
git status --short --ignored --untracked-files=all -- expectation | LC_ALL=C sort | sha256sum
find expectation -type f -not -path '*/__pycache__/*' -print0 | sort -z | xargs -0 -r sha256sum | sha256sum
```

说明：`expectation/` 在当前仓库是 ignored/untracked 合同资产，`git diff` 只能证明 tracked diff 为空，不能证明 ignored/untracked 文件未被改动。execute 必须在任务开始和结束分别记录上述两个 expectation 指纹；review / archive_acceptance 复核前后指纹一致，若不一致必须阻断并定位。

## 计划内小任务

### S1. 更新 multi-buffer spec 与公开 IR attr 合同

- 为什么做：当前 spec 没有 `analysis.loop_id` / `analysis.if_id`，也没有 if 路径候选和所有 eligible alloc 均 analysis/apply 闭合的规则。
- 做什么：更新 `spec/pass/memory/multi_buffer.md`，写清控制流编号、if path lifecycle、buffer num 分类和 apply capacity/reserved 规则。
- 不做什么：不新增 pass option，不改 class 签名，不新增 `analysis.control_path`。
- 怎么验收：文本核对 spec 包含 `analysis.loop_id`、`analysis.if_id`、`multi_buffer.update_points/use_points/num`、`main-only -> num=1`、非 main 当前区域最大深度全命中 -> `auto/memory_stage`、非 main 未命中当前区域最大深度 -> `num=2`、if branch insertion/advance 规则；pytest 仍通过。
- 卡住问谁：公开 API 或 buffer num 规则冲突问用户；计划验收口径问架构师。
- 上下文摘要：spec 是 execute/review 判断实现是否越界的合同真源。
- 小任务目标：把 multi-buffer 控制流编号与 if path lifecycle 写成可执行公开合同。
- 非目标：不写实现。
- 模块范围：`spec/pass/memory/multi_buffer.md`。
- 禁止修改面：`expectation/`、`.skills/`、`agents/standard/`、`AGENTS.md`、`TODO.md`、`DONE.md`。
- 合同真源：用户确认 > 本计划 > spec > pytest > 当前实现。
- 最小功能闭环：spec 能让执行人判断 `%11/%12/%13` 与 `%15/%16/%20/%21` 分别应打什么属性。
- 执行步骤：
  1. 在 Analysis 合同中加入控制流编号阶段。
  2. 在候选边界中加入 if path lifecycle 支持与 no-op 边界。
  3. 在 `spec/dialect/symbol.md` 中补充 `symbol.for` 自定义文本语法必须保留 `iter` 之外普通 attrs 的 round-trip 要求。
  4. 在 Apply 合同中加入 `main` update、最大深度 `auto/memory_stage`、非最大深度固定双 buffer 的 insertion/advance 与 capacity/reserved 规则。
- 验收必过项目：`pytest -q test/passes/memory/test_multi_buffer.py test/passes/test_registry.py`。
- 记录要求：任务记录写清公开 attr 新增的用户确认来源，不得写成未确认 API。

### S2. 实现控制流编号与共享 candidate discovery

- 为什么做：当前 loop label 只存在内部 dict，不落到 IR；analysis/apply 也没有同一套可穿过 if 的 candidate discovery。
- 做什么：在 `kernel_gen/dialect/symbol/operation/control_flow.py` 中保证 `symbol.for` 额外 attrs round-trip；在 `kernel_gen/passes/memory/multi_buffer.py` 内实现控制流编号 helper 和 lifecycle candidate builder，analysis/apply 共用同一候选结构。
- 不做什么：不把 helper 提升为跨文件公开 API，不跨文件调用非公开 helper。
- 怎么验收：pytest 覆盖已有编号不覆盖、缺失编号补齐、if branch use 可进入候选、sibling/escape no-op。
- 卡住问谁：如果需要新增公开 helper 或 package re-export，暂停问用户。
- 上下文摘要：AGENTS 禁止跨文件使用非公开 API；抽象能力应先保持当前文件内。
- 小任务目标：让 analysis/apply 在同一个文件内共享 lifecycle 抽象，避免分析和变换规则漂移。
- 非目标：不改 producer-consumer-analysis，不改 loop-soft-pipeline。
- 模块范围：`kernel_gen/passes/memory/multi_buffer.py`、`kernel_gen/dialect/symbol/operation/control_flow.py`。
- 禁止修改面：`expectation/`、`.skills/`、`agents/standard/`、计划书正文。
- 合同真源：spec > pytest > dump 验收 > 当前实现。
- 最小功能闭环：`MultiBufferAnalysisPass` 对用户点名 dump 能给 loop/if 编号并标出全部 7 个 alloc。
- 执行步骤：
  1. 新增当前文件内顶层 helper，收集和补齐 `analysis.loop_id` / `analysis.if_id`。
  2. 更新 `SymbolForOp` printer/parser，保留并 round-trip `iter` 之外的普通 attrs。
  3. 将现有 region label 读取改为优先读 op 上 `analysis.loop_id`。
  4. 把 direct body 检查替换为 lifecycle parent-chain 分析。
  5. 复用同一 `_LoopRingCandidate` 或等价结构服务 analysis/apply。
- 验收必过项目：`pytest -q test/dialect/symbol/test_symbol.py test/passes/memory/test_multi_buffer.py -k "analysis or control_flow or noop"`。
- 记录要求：写清没有新增公开 Python API，没有跨文件非公开 API 调用。

### S3. 实现 if path apply 与 buffer num/reserved 闭合

- 为什么做：analysis 能标出 if path alloc 后，apply 必须能按同一规则变换，否则 split pass 不闭合。
- 做什么：扩展 `MultiBufferApplyPass` 处理 `main` update `num=1`、if branch use、最大深度 `auto/memory_stage`、非最大深度 fixed `num=2`，并修正 auto group reserved 计算。
- 不做什么：不为了通过用例牺牲 no-op 安全边界；无法证明 capacity 或支配关系时按 group no-op 并记录。
- 怎么验收：pytest 验证 7 个 alloc 全部 ring 化；dump 验证 current/advance 位置；capacity 公式扣除 fixed `num=1` / `"2"` 候选。
- 卡住问谁：capacity 规则与现有 memory-pool 冲突时问架构师；若需改 target capacity 公开数据问用户。
- 上下文摘要：当前 apply 只消费三项 attr，必须保证 `analysis` 和 `apply` 对 update/use point 的解释一致。
- 小任务目标：让 `multi-buffer-apply` 对 analysis 标注的 if path / `main` update / 最大深度 auto / 非最大深度 fixed 候选全部正确改写。
- 非目标：不做 async pipeline，不改变 compute order。
- 模块范围：`kernel_gen/passes/memory/multi_buffer.py`。
- 禁止修改面：`expectation/`、`.skills/`、`agents/standard/`、计划书正文。
- 合同真源：spec > pytest > dump 验收 > 当前实现。
- 最小功能闭环：用户点名 present-bias static dump 两个 pattern 每个 pattern 7 个 typed alloc 都被 ring 化，matmul/bias/output 语义不变。
- 执行步骤：
  1. 对 `update_points/use_points` 列表可归约到同一生命周期的候选插入 current/advance 到目标 use loop。
  2. 对 if branch 中最后使用的候选，把 advance 插到 enclosing `scf.if` 后。
  3. 保持 K loop staging current/advance 在 K loop body。
  4. 在 auto capacity 中扣除同 space overlapping fixed candidates。
- 验收必过项目：`pytest -q test/passes/memory/test_multi_buffer.py`；dump 三个 matmul脚本。
- 记录要求：任务记录列出 `%11/%12/%13/%15/%16/%20/%21` 在 analysis 和 apply 后的结果摘要。

### S4. 补测试和 dump 断言

- 为什么做：当前测试只锁 direct body 和 nested no-op，缺少 if branch 正向用例和 all eligible alloc apply 用例。
- 做什么：新增或扩展 pytest，覆盖控制流编号、if path analysis、if path apply、buffer num/reserved、no-op 边界。
- 不做什么：不直接调用跨文件非公开 helper；测试只通过公开 pass API 和 IR 结果观察。
- 怎么验收：新增用例修复前失败、修复后通过；全量 multi-buffer 测试通过。
- 卡住问谁：测试需要访问非公开 helper 时改为构造 IR 后跑公开 pass；公开 API 不足时问用户。
- 上下文摘要：测试必须证明不是只改 dump 文本，而是 pass 行为真的闭合。
- 小任务目标：用 pytest 和 dump 锁定控制流编号、if path 和 all alloc ring 化行为。
- 非目标：不修改 expectation。
- 模块范围：`test/passes/memory/test_multi_buffer.py`、必要的 dump/text 验收脚本或现有 kernel demo。
- 禁止修改面：`expectation/`、`.skills/`、`agents/standard/`、计划书正文。
- 合同真源：spec > pytest > dump 验收。
- 最小功能闭环：`test_multi_buffer_analysis_marks_if_path_allocs`、`test_multi_buffer_apply_rewrites_if_path_allocs`、`test_multi_buffer_preserves_existing_analysis_ids` 等等价覆盖存在。
- 执行步骤：
  1. 构造含 `symbol.for + scf.if` 的 alloc/alias/use IR。
  2. 跑 `MultiBufferAnalysisPass` 断言 loop/if id 与 alloc attr。
  3. 跑 `MultiBufferApplyPass` 或 facade 断言 ring/current/advance 和 typed alloc/free 删除。
  4. 保留 sibling/escape/no-free/multi-free no-op 测试。
- 验收必过项目：`pytest -q test/passes/memory/test_multi_buffer.py test/passes/test_registry.py`。
- 记录要求：执行记录写清 Diff 反推测试，不得用 expectation 替代 pytest。

### S5. 核对 expectation 禁止修改面

- 为什么做：`expectation/` 是合同资产，且当前仓库把该目录 ignored/untracked，单靠 `git diff` 不能证明未被写入或改动。
- 做什么：execute 开始和结束各记录一次 expectation status/content 指纹，并确认 tracked diff、cached diff、ignored/untracked 指纹均未变化。
- 不做什么：不新增/移动/修改/删除 `expectation/**`，不把 expectation 作为本轮必过合同验收。
- 怎么验收：tracked/cached diff 为空；任务开始和结束的 expectation status/content 指纹完全一致；review / archive_acceptance 复核同一组证据。
- 卡住问谁：expectation 目标、输出或授权范围不清时问用户。
- 上下文摘要：`expectation/` 是合同资产，不是普通实现改动。
- 小任务目标：用可复核证据证明本轮没有触碰 ignored/untracked expectation 合同资产。
- 非目标：不把 expectation 当作 diff 反推测试。
- 模块范围：无 expectation 写入范围。
- 禁止修改面：scope 外全部 expectation、`.skills/`、`agents/standard/`、`AGENTS.md`。
- 合同真源：用户授权 > 本计划 > spec > pytest > dump。
- 最小功能闭环：任务记录包含开始/结束 expectation 指纹，且二者一致。
- 执行步骤：
  1. 在改动前记录 `git diff --name-status -- expectation`、`git diff --cached --name-status -- expectation`。
  2. 在改动前记录 `git status --short --ignored --untracked-files=all -- expectation | LC_ALL=C sort | sha256sum`。
  3. 在改动前记录 `find expectation -type f -not -path '*/__pycache__/*' -print0 | sort -z | xargs -0 -r sha256sum | sha256sum`。
  4. 完成实现、测试和 dump 验收后重新运行第 1-3 项，前后指纹必须一致。
- 验收必过项目：两组 `git diff` 无输出；两组 expectation status/content 指纹前后一致。
- 记录要求：任务记录写清本轮 expectation 非目标，不得以 expectation 替代 pytest / dump；若指纹变化，必须阻断并定位具体文件。

## 计划自检与返工口径

- 公开 API：新增 IR attrs `analysis.loop_id` / `analysis.if_id` 已有用户确认；无 class/option/registry 变更。
- expectation 权限：本轮已确认不预置新 expectation；execute 禁止修改。
- 小任务卡：S1-S5 均可由一个 execute 一次完成；S5 只做禁止修改面核对，不写 expectation。
- analysis/apply 闭合：计划要求同一 candidate discovery，避免 split pass 漂移。
- buffer num：已按 `main-only -> num=1`、非 main 当前区域最大深度全命中 -> `auto/memory_stage`、非 main 未命中当前区域最大深度 -> `num=2` 三类写清；用户点名 present-bias `%11/%12/%13` 是 `num=2`，`%15/%16/%20/%21` 是 `auto`。
- 返工口径：只要仍有能提升控制流编号稳定性、if path lifecycle 正确性、capacity 安全、测试有效性或计划可读性的可执行项，就不得进入守护最终检验。

## 计划书入档验收 / 复验 / 修复复核记录

时间：2026-06-13 19:16 +0800

结论人：不要啊教练。

任务：`T-20260613-6ccd1b8f / multi-buffer-control-flow-lifecycle / archive_acceptance`

验证基线：
- 执行目录：`/home/lfr/kernelcode_generate/wt-20260613-multi-buffer-control-flow-lifecycle`。
- `HEAD`：`ed33fcf8a0a031b9c3753e3d2339d5058f875169`。
- `origin/main`：`ed33fcf8a0a031b9c3753e3d2339d5058f875169`。
- merge-base：`ed33fcf8a0a031b9c3753e3d2339d5058f875169`。
- ahead / behind：`0 0`。

合同验收摘要：
- 当前计划正文不列必过 `expectation` 合同验收；本 worktree 无 `expectation/` 目录，`expectation` status / content 指纹均为 `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855`。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/passes/memory/test_multi_buffer.py -k 'apply_without_attrs_does_not_write_analysis_ids or apply_consumes_attrs_with_alignment_zero or apply_keeps_existing_current_pair_noop or apply_keeps_existing_current_direct_use_noop'`：`4 passed, 21 deselected, 1 warning`。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/passes/memory/test_multi_buffer.py test/passes/test_registry.py`：`90 passed, 1 warning`。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/dialect/symbol/test_symbol.py`：`118 passed, 1 warning`。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/repo_conformance/test_private_api_boundaries.py test/tools/test_kernel_code_error_static_gate.py`：`8 passed`。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest --collect-only -q test/passes/pipeline/test_npu_demo_lowering.py`：`11 tests collected`。
- pipeline 分组验收分别为 `3 passed, 8 deselected, 1 warning`、`6 passed, 5 deselected, 1 warning`、`3 passed, 8 deselected, 1 warning`。
- dump 脚本 `kernel/matmul/inputs_static_tile_static.py`、`kernel/matmul/inputs_static_tile_dynamic.py`、`kernel/matmul/inputs_dynamic_tile_dynamic.py` 均退出码 `0`，本轮最大误差分别为 `2.6702880859375e-05`、`4.57763671875e-05`、`3.0517578125e-05`。
- dump 结构复核通过：`24-multi-buffer-analysis.mlir` 包含 `analysis.loop_id`、`analysis.if_id`、`multi_buffer.update_points/use_points`、fixed `num = "2"` 和 `num = "auto"`；`25-multi-buffer-apply.mlir` 不残留 `multi_buffer.*`，并包含 `dma.make_ring`、`dma.current_ring`、`dma.advance_ring`。
- `PYTHONDONTWRITEBYTECODE=1 python3 -m py_compile kernel_gen/passes/memory/multi_buffer.py kernel_gen/dialect/symbol/operation/control_flow.py test/passes/memory/test_multi_buffer.py test/dialect/symbol/test_symbol.py test/passes/pipeline/test_npu_demo_lowering.py`：退出码 `0`。
- `git diff --check && git diff --cached --check`：退出码 `0`。
- 敏感范围 `expectation/.skills/agents/standard/AGENTS.md/TODO.md/DONE.md/agents-lists` staged / unstaged diff 为空；`expectation/pass/multi_buffer` 与 `expectation/pass/pipeline/npu_demo_lowering.py` staged / unstaged diff 为空。

通过摘要：
- execute / review / review -> archive_acceptance 标准流转记录齐全，review 通过结论无阻断、无最小需改项。
- `MultiBufferApplyPass.apply` 使用只读 `existing_region_labels(module)`；apply-only 在无 `multi_buffer.*` 候选时不写 `analysis.loop_id/analysis.if_id`。
- analysis 阶段仍通过写入式 `region_labels(module)` 负责生成控制流 id；apply 阶段只消费 analysis 阶段已产出 id。
- `spec/pass/memory/multi_buffer.md`、`kernel_gen/passes/memory/multi_buffer.py`、pytest、pipeline dump 与计划完成态一致。

最小阻断项或通过摘要：通过；无阻断项，无最小需改项。下一步按计划级链路续接 `merge / 归档`，archive_acceptance 本身不执行 merge、提交、推送或归档。

## 待确认项

### D1. expectation 授权（已收口）

- 结论：本轮不改 expectation，只用 spec + pytest + dump 验收。
- 影响：守护、execute、review、archive_acceptance 不把新增 expectation 当作当前必过资产；但必须核对 expectation diff 为空。

## 用户确认与协同约束

- 用户确认来源：2026-06-13 当前会话。
- 已确认事项：Q1-Q10 已写入本计划。
- 待用户确认项：无。
- 迭代审阅记录：Round 1 已完成并按不通过回执返工；Round 2 已通过，当前无阻断项、无最小需改项、无待确认项。
- 守护最终检验：已由 `守护最好的爱莉希雅` 本人回执通过，管理员已据此创建唯一计划级 execute。
- 管理员协同：当前唯一计划级任务为 `T-20260613-6ccd1b8f`；archive_acceptance 通过后按标准链路交给 merge/归档，不创建第二个 execute。
