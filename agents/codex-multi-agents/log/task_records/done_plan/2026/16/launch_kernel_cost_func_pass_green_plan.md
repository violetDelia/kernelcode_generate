# launch_kernel_cost_func_pass_green_plan.md

## 文档信息

- 创建者：`守护最好的爱莉希雅`
- 最后一次更改：`守护最好的爱莉希雅`
- 目标 `spec`：
  - [`spec/dialect/symbol.md`](../../spec/dialect/symbol.md)
  - [`spec/dialect/tuner.md`](../../spec/dialect/tuner.md)
  - `spec/pass/tuning/launch_kernel_cost_func.md`
  - [`spec/pass/registry.md`](../../spec/pass/registry.md)
- 目标 `API`：
  - [`kernel_gen/dialect/symbol.py`](../../kernel_gen/dialect/symbol.py)
  - [`kernel_gen/dialect/tuner.py`](../../kernel_gen/dialect/tuner.py)
  - `kernel_gen/passes/tuning/launch_kernel_cost_func.py`
  - [`kernel_gen/passes/registry.py`](../../kernel_gen/passes/registry.py)
- 目标 `test`：
  - [`test/dialect/test_symbol_dialect.py`](../../test/dialect/test_symbol_dialect.py)
  - [`test/dialect/test_tuner_dialect.py`](../../test/dialect/test_tuner_dialect.py)
  - `test/pass/test_launch_kernel_cost_func.py`
  - [`test/pass/test_pass_registry.py`](../../test/pass/test_pass_registry.py)
- 目标 `验收资产`：
  - `expectation/pass/tuning/launch_kernel_cost_func`
  - `pytest -q test/dialect/test_symbol_dialect.py`
  - `pytest -q test/dialect/test_tuner_dialect.py`
  - `pytest -q test/pass/test_launch_kernel_cost_func.py`
  - `pytest -q test/pass/test_pass_registry.py -k launch_kernel_cost_func`
- 目标 `功能实现`：
  - [`kernel_gen/dialect/symbol.py`](../../kernel_gen/dialect/symbol.py)
  - [`kernel_gen/dialect/tuner.py`](../../kernel_gen/dialect/tuner.py)
  - `kernel_gen/passes/tuning/launch_kernel_cost_func.py`
  - `kernel_gen/passes/tuning/__init__.py`
  - [`kernel_gen/passes/registry.py`](../../kernel_gen/passes/registry.py)

## 任务清单

| 任务 | 前置任务 | worktree | 记录文件 |
| --- | --- | --- | --- |
| `S1` | `无` | `wt-20260416-launch-kernel-cost-s1` | `agents/codex-multi-agents/log/task_records/2026/16/20260416-launch-kernel-cost-s1.md` |
| `S2` | `S1` | `wt-20260416-launch-kernel-cost-s2` | `agents/codex-multi-agents/log/task_records/2026/16/20260416-launch-kernel-cost-s2.md` |
| `S3` | `S2` | `wt-20260416-launch-kernel-cost-s3` | `agents/codex-multi-agents/log/task_records/2026/16/20260416-launch-kernel-cost-s3.md` |
| `S4` | `S3` | `wt-20260416-launch-kernel-cost-s4` | `agents/codex-multi-agents/log/task_records/2026/16/20260416-launch-kernel-cost-s4.md` |

## 小任务链说明

- 本计划的小任务默认只预建 `spec/build` 起点任务，不单独预建 `review/merge` 任务。
- 每个 `S*` 小任务都按默认 `spec/build/review/merge` 路线在执行链内自动续接。
- 因此管理员在分发时，只需要按本计划当前预建的 `spec/build` 起点任务顺序推进，不应额外把 `review/merge` 视为计划书中的独立预建小任务。
- `S2/S3` 的 `build` 执行阶段允许对本阶段直接相关 `spec` 做最小同步校正，用于补齐执行中发现的漏项、错误示例或实现约束描述；这类校正不需要暂停回架构师。
- `S2/S3` 不得自行推翻 `S1` 已冻结的核心公开合同，包括 `tuner.cost -> f64`、只透传原 op operands、原 attrs 平铺保留、cost func 汇总返回、`symbol.for` 只支持单个 loop-carried `f64`、原 wrapper/device func 不改。若必须改变这些核心合同，必须回到架构侧重新裁定。
- 执行阶段发生最小 `spec` 校正时，任务记录必须写清校正原因、涉及路径、对应实现/测试或 expectation 验证结果。
- 若口头消息中的旧任务号与当前 [`TODO.md`](../../TODO.md) 落表不一致，以当前 `TODO.md` 中同阶段、同记录文件、同依赖链的任务号为唯一有效口径；不为这种口径修正重复补建平行任务。

## 评审摘要

- 评审结论：`通过`
- 评审人：`守护最好的爱莉希雅`、`大闸蟹`
- 结论摘要：`kind 与 cost_kind 的职责切分、expectation 与 pytest 的分层，以及 dma/kernel/arch 承接与其余非 symbol dialect op 显式失败口径已收口，可按当前版本建任务推进。`
- 终验结论（2026-04-18 08:58 +0800，终验人：`大闸蟹`）：`通过`
- 最新同步现场与验证基线：`wt-20260416-launch-kernel-cost-s4`，`HEAD=origin/main=edff36ae05689a6eec1c992f8c48353a4c63b241`
- 终验命令：
  - `PYTHONDONTWRITEBYTECODE=1 pytest -q test/dialect/test_symbol_dialect.py` -> `52 passed`
  - `PYTHONDONTWRITEBYTECODE=1 pytest -q test/dialect/test_tuner_dialect.py` -> `6 passed`
  - `PYTHONDONTWRITEBYTECODE=1 pytest -q test/pass/test_launch_kernel_cost_func.py` -> `11 passed`
  - `PYTHONDONTWRITEBYTECODE=1 pytest -q test/pass/test_pass_registry.py -k launch_kernel_cost_func` -> `2 passed, 16 deselected`
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python expectation/pass/tuning/launch_kernel_cost_func` -> 输出包含 `[OK] launch-kernel-cost-func expectation passed`
- 终验摘要：`S2` 的 `symbol.for` loop-carried `f64` 与 `tuner.cost` 方言测试、`S3` 的 pass/registry 回归、`S4` 的目录级 expectation 合同资产均已在最新同步现场通过；当前未见阻断本计划归档的剩余缺口。

## 输入摘要

- 目标：新增一个 standalone pass，从已存在的 `arch.launch -> device func` 关系生成一个 sibling cost host function，用于表达 device kernel 的 cost 计算逻辑。
- 不做什么：不改原 host wrapper，不改原 device func，不把本轮目标扩成 target runtime 求值或真实 cost evaluator。
- 当前痛点：仓库里已有 `analysis/func_cost` 与 `analyze_kernel(...)`，但它们只做分析摘要，不产出新的 IR function，也没有对应的 `tuner.cost` IR 节点。
- 完成后最想看到的例子：给定一个带 `arch.launch` 的 wrapper 与其 device callee，pass 能新增 `@_cost_<kind>_<device_func_name>`，保留 `symbol.for` 结构，在 loop/body 中为 `dma/kernel/arch` op 生成 `tuner.cost`，并把所有 `tuner.cost` 的 `f64` 结果累计后作为 cost func 返回值。

## 计划目标

- 新增一个 standalone tuning pass，为被 `arch.launch` 调用的 device callee 生成 cost host function。
- 扩展 `symbol dialect` 的 `symbol.for`，使其可承载单个 loop-carried `f64`，为 cost func 的循环累计提供公开 IR 语义。
- 扩展 `tuner dialect`，新增 `tuner.cost` op，作为 cost function 内的单 op cost 节点。
- 冻结 cost function 命名、参数、返回值、skip 规则与 `cost_kind=compute/move/all` 的公开合同。
- 冻结“cost func 不只是生成 `tuner.cost`，还必须把所有 cost 累计并返回单个 `f64` 总值”的公开合同。
- 保持原 wrapper 与原 device func 不变；若多个 wrapper 指向同一 device func，只生成一份 cost function。
- 本 pass 的专题 `spec / expectation / test` 归属统一落在 `tuning`，不落在 `lowing/lowering` 目录；为支撑该专题新增的循环累计能力，`symbol.for` 的前置公开合同与测试同步落在 `symbol` dialect 自身目录。
- 将本轮公开行为锁定在 `spec + pytest + expectation`，让执行人不必再猜“这是 analysis pass 还是 IR-generating pass”。

## 当前基线

- 当前公开合同：
  - [`spec/dialect/symbol.md`](../../spec/dialect/symbol.md) 当前已定义 `symbol.for` 的单迭代变量、单块 region 与 `!symbol.iter<...>` 语义，但仍明确“不定义循环携带值、多结果循环”；这正是本轮需要扩展的前置合同。
  - [`spec/dialect/tuner.md`](../../spec/dialect/tuner.md) 目前只定义 `tuner.param`，没有 `tuner.cost`。
  - [`spec/pass/analysis/func_cost.md`](../../spec/pass/analysis/func_cost.md) 与 [`spec/analysis/analysis_engine.md`](../../spec/analysis/analysis_engine.md) 当前都是 analysis 主线或 facade，明确“不生成 sibling function”。
  - [`spec/pass/lowering/outline_device_kernel.md`](../../spec/pass/lowering/outline_device_kernel.md) 已冻结 `wrapper + device func + arch.launch` 的前置形状，可作为本 pass 的输入基线。
  - 上述 `lowering` 引用仅表示输入前置依赖，不表示本 pass 自身归属；本 pass 自身仍归属 `tuning`。
- 当前公开 API：
  - [`kernel_gen/dialect/symbol.py`](../../kernel_gen/dialect/symbol.py) 当前 `SymbolForOp` 只有 `start/end/step + iter_attr + 单 block arg`，`traits` 为 `NoTerminator()`，还不能承载 loop-carried `f64` 结果。
  - [`kernel_gen/dialect/tuner.py`](../../kernel_gen/dialect/tuner.py) 当前只有 `TunerParamOp`。
  - [`kernel_gen/passes/registry.py`](../../kernel_gen/passes/registry.py) 已支持新 pass 注册与 `from_options(...)` 选项构造。
  - `kernel_gen/passes/tuning/__init__.py` 与 `kernel_gen/passes/tuning/launch_kernel_cost_func.py` 当前都不存在，本轮需新增 `tuning` 包与 pass 入口。
- 当前实现入口：
  - [`kernel_gen/passes/analysis/func_cost.py`](../../kernel_gen/passes/analysis/func_cost.py) 是 analysis pass，不改写 IR。
  - [`kernel_gen/passes/lowering/outline_device_kernel.py`](../../kernel_gen/passes/lowering/outline_device_kernel.py) 已能稳定识别/生成 `arch.launch` wrapper 形态。
  - [`kernel_gen/dialect/arch.py`](../../kernel_gen/dialect/arch.py) 当前已使用 `arch.launch`（不是旧 `arch.launch_kernel`），callee 为 `@symbol`。
- 当前测试与验收资产：
  - [`test/dialect/test_symbol_dialect.py`](../../test/dialect/test_symbol_dialect.py) 当前只覆盖 `symbol.for` 的单块参数、parse/print、错误路径，还没有 loop-carried `f64` 的 round-trip / verifier / 结果传递回归。
  - [`test/dialect/test_tuner_dialect.py`](../../test/dialect/test_tuner_dialect.py) 当前只覆盖 `tuner.param`。
  - [`test/pass/test_pass_registry.py`](../../test/pass/test_pass_registry.py) 已有 `outline-device-kernel` 等 standalone pass 注册路径，可复用测试风格。
  - 当前主仓已存在 `expectation/pass/tuning/launch_kernel_cost_func/` 目录级 expectation 草案：
    - `basic_all.py`
    - `shared_callee_once.py`
    - `invalid_kind.py`
    - `__main__.py`
  - 但当前仍没有 `launch kernel cost func` 对应的 pass pytest 资产，也还没有 `spec/pass/tuning/launch_kernel_cost_func.md` 与 `kernel_gen/passes/tuning/launch_kernel_cost_func.py` 的实现落点。
- 当前缺口或失败点：
  - `symbol.for` 当前不能承载 loop-carried `f64`，因此无法在保留循环结构的前提下把 loop 内 cost 通过纯 SSA 返回到 cost func。
  - `tuner` 没有“单 op cost 节点”。
  - pass 层没有“从 `arch.launch` / device callee 生成 cost host func”的稳定入口。
  - `spec/pass/tuning/` 与 `kernel_gen/passes/tuning/` 目录当前都还没有公开资产，本轮需要一并补齐。
- 当前 expectation 草案已先行存在，但与之对应的 pass/spec/test 仍未闭环，因此 expectation 还不能单独作为“功能已存在”的证据。
- 当前没有冻结 `arith.constant` / `symbol.*` / `func.return` 在 cost IR 中的 skip 规则。

## 归档记录

时间：2026-04-18 23:59 +0800
经办人：李白
任务：T-20260418-9a8832fb
任务目标：将 `ARCHITECTURE/plan/launch_kernel_cost_func_pass_green_plan.md` 归档到 `agents/codex-multi-agents/log/task_records/done_plan/2026/16/launch_kernel_cost_func_pass_green_plan.md`，并完成归档 merge 收口
改动：已在指定 `worktree=/home/lfr/kernelcode_generate/wt-20260418-archive-launch-kernel-cost-func-pass-plan` 内将主仓当前计划书快照复制到归档目标路径 `agents/codex-multi-agents/log/task_records/done_plan/2026/16/launch_kernel_cost_func_pass_green_plan.md`，并在文件尾部追加本次归档记录；本次归档范围限定为新增该 `done_plan` 文件，不修改 `TODO.md`、`DONE.md`、`AGENTS.md`、`skills/`、`expectation/` 或其他共享状态文件
验证：`git -C /home/lfr/kernelcode_generate/wt-20260418-archive-launch-kernel-cost-func-pass-plan merge --ff-only origin/main` -> 已将归档 `worktree` 从 `2f7aea5cf24221e0fd90e3b97127d31513dc23df` 快进到 `0731a027c628be0e621d5bfdf3cab91eaacf7988`；`test -f /home/lfr/kernelcode_generate/ARCHITECTURE/plan/launch_kernel_cost_func_pass_green_plan.md` -> `ROOT_SRC_OK`；`test -e /home/lfr/kernelcode_generate/wt-20260418-archive-launch-kernel-cost-func-pass-plan/agents/codex-multi-agents/log/task_records/done_plan/2026/16/launch_kernel_cost_func_pass_green_plan.md` -> 归档目标已创建；`git -C /home/lfr/kernelcode_generate/wt-20260418-archive-launch-kernel-cost-func-pass-plan status --short -- agents/codex-multi-agents/log/task_records/done_plan/2026/16/launch_kernel_cost_func_pass_green_plan.md` -> `?? agents/codex-multi-agents/log/task_records/done_plan/2026/16/launch_kernel_cost_func_pass_green_plan.md`
结论：归档文件已在指定 `worktree` 内生成并写入归档记录；下一步提交并推送该归档文件，随后执行当前 merge 任务 `-done` 并回报管理员继续 `-done-plan`

## 合同真源顺序

- `expectation > spec > test 文字说明 > 当前实现`

## 方案比较与选型

- 不采用方案：扩展 [`kernel_gen/passes/analysis/func_cost.py`](../../kernel_gen/passes/analysis/func_cost.py)，让它顺手生成 cost function。
  - 原因：这会把 analysis 与 IR 改写耦在一起，破坏 [`spec/pass/analysis/func_cost.md`](../../spec/pass/analysis/func_cost.md) 现有“只做分析”的公开定位。
- 不采用方案：直接在现有 device func 内内联 `tuner.cost` 与累计逻辑。
  - 原因：用户已明确原 device func 不改；把 cost 逻辑混入 device body 会污染原 lowering/codegen 输入。
- 不采用方案：把 `tuner.cost` 做成“只记录 op_name、没有 operands/attrs”的摘要节点。
  - 原因：用户已明确 `tuner.cost` 只传原 op operands，且要保留原 attributes；不能退化成无输入摘要。
- 采用方案：
  - 新增 standalone pass `launch-kernel-cost-func`；
  - 输入是已存在 `arch.launch -> device func` 关系的 module；
- 输出是在 module 内新增 `@_cost_<cost_kind>_<device_func_name>`，参数列表与 device func 完全一致，返回 `f64`；
- `tuner.cost` 只承接原 op operands，平铺保留原 op attributes，并新增 pass 自己的 `kind / cost_kind / op_name / device_func` 元数据。
- cost func 内必须把所有 `tuner.cost(...)->f64` 的结果累计为单个 `f64`，并以该总值作为最终 `func.return`；不能停在“只生成若干 `tuner.cost` op”而不汇总返回。
- 为满足“保留 `symbol.for` 结构且最终返回单个 `f64` 总值”的公开合同，本轮一并扩展 [`kernel_gen/dialect/symbol.py`](../../kernel_gen/dialect/symbol.py) 对应的 `symbol.for`，支持 loop-carried `f64` 累计值；cost func 的循环累计承载统一复用该公开能力，不另造私有循环累计节点。
- 最小公开接口：
  - `LaunchKernelCostFuncPass(kind="all")`
  - registry name: `launch-kernel-cost-func`
  - `tuner.cost(...) -> f64`

## 公开 API 设计

### 1. `class LaunchKernelCostFuncPass(Pass)`

- 公开入口：`kernel_gen.passes.tuning.launch_kernel_cost_func.LaunchKernelCostFuncPass`
- 参数顺序：
  - `kind: str = "all"`
- 允许值：
  - `"compute"`
  - `"move"`
  - `"all"`
- 返回值：
  - `run(module) -> module`
- 规则：
  - pass 为 standalone tuning，不加入默认 pipeline。
  - 输入必须已经具备 `arch.launch` 与可解析的 device callee。
  - 原 wrapper 与原 device func 不改。
  - 若 module 中多个 `arch.launch` 指向同一 device func，仅生成一份 cost function。
  - 生成的 cost function 必须返回单个 `f64` 总 cost；该总 cost 来自函数体内全部 `tuner.cost` 结果的累计。
  - `kind` 非法时必须显式抛出 `ValueError`，且错误消息至少包含 `compute / move / all` 三个允许值。

```python
from kernel_gen.passes.tuning.launch_kernel_cost_func import LaunchKernelCostFuncPass

module = LaunchKernelCostFuncPass(kind="all").run(module)
```

```python
from kernel_gen.passes.registry import build_registered_pass, load_builtin_passes

load_builtin_passes()
pass_obj = build_registered_pass("launch-kernel-cost-func", {"kind": "move"})
module = pass_obj.run(module)
```

### 2. Cost function 命名与签名

- 命名规则：`@_cost_<cost_kind>_<device_func_name>`
- 命名规则按 raw callee 名直接拼接，不额外去除前导/尾随下划线。
- 参数列表：与 device func 参数列表完全一致，顺序不变。
- 返回值：固定单结果 `f64`。
- 函数体语义：必须把当前 cost function 中所有 `tuner.cost(...)->f64` 的结果累计为单个 `f64` 后返回。
- 每个 unique device callee 在同一 `cost_kind` 下只生成一份 cost function。

```text
func.func @_cost_all__device_matmul_kernel_(%lhs, %rhs, %out, %M, %K, %N, %TILE_M, %TILE_N) -> f64
```

### 3. `tuner.cost`

- 公开入口：`kernel_gen.dialect.tuner.TunerCostOp`
- operand 规则：
  - 只传原 op 的 operands。
  - 原 op 有几个 operands，就按原顺序透传几个 operands。
- attr 规则：
  - 原 op attributes 平铺保留。
  - 新增 pass-owned attrs：
    - `kind = "compute" | "move"`：表示该 op 在成本表中的自身类别；当前 V1 仅收 `compute / move`。
    - `cost_kind = "compute" | "move" | "all"`：表示当前 cost function 的统计视角，由 pass 参数决定。
    - `op_name = "<dialect.op>"`
    - `device_func = @callee`
  - 若原 op 已带有 `kind / cost_kind / op_name / device_func` 任一同名 attr，pass 必须显式失败，不做覆盖或静默改名。
- 结果类型：固定 `f64`
- 无 region
- 本 op 只表示“单个原 op 的局部 cost”；总 cost 由外层 cost function 负责累计并返回。
- `kind` / `cost_kind` 的分工必须写死：
  - `kind` 表示原 op 自身属于 `compute` 还是 `move`；
  - `cost_kind` 表示当前 cost function 的统计视角；
  - pass 不因为 `cost_kind=compute` 就跳过 `move` 类 op，也不因为 `cost_kind=move` 就跳过 `compute` 类 op。
- 当前 V1 的 pass 语义只负责“为所有受支持 op 产出 `tuner.cost` 节点并正确打上 `kind/cost_kind`”；“当 `kind` 与 `cost_kind` 不同时时该 cost 为 0”属于后续 cost table / evaluator 语义，不在本 pass 内做常量折叠或节点裁剪。

```text
%cost0 = tuner.cost(%tile_m, %k) {kind = "move", cost_kind = "all", op_name = "dma.alloc", device_func = @_device_matmul_kernel_, operandSegmentSizes = array<i32: 2>} : (!symbol.int<"TILE_M">, !symbol.int<"K">) -> f64
```

### 4. `symbol.for` 的 loop-carried `f64` 支撑合同

- 公开入口：[`kernel_gen.dialect.symbol.SymbolForOp`](../../kernel_gen/dialect/symbol.py)
- 保持不变的旧合同：
  - `start/end/step` 仍要求 `!symbol.int<"...">`
  - 主迭代变量 `it` 仍要求 `!symbol.iter<...>`
  - `symbol.for` 仍保持单 region、单块循环体
- 本轮新增能力：
  - `symbol.for` 允许可选承载一个 loop-carried `f64` 累计值，用于把循环内局部 cost 汇总回循环外。
  - V1 只支持“单个 carried 值、类型固定为 `f64`”；不顺手扩成任意类型、多 carried 值、并行循环或提前退出语义。
  - `launch-kernel-cost-func` 生成的 cost func 必须复用这条公开能力，不得私造隐藏状态或专题专用循环 op。
- 合同边界：
  - 旧的无 carried-value `symbol.for` 用法必须继续成立。
  - 新的 carried-value 文本语法、region/terminator 形状与 verifier 约束在 `S1` 的 `spec/dialect/symbol.md` 中冻结；在冻结前，不允许执行人自行扩成通用控制流体系。

### 5. Skip / clone 规则

- 保留 `symbol.for` 结构，不为 `symbol.for` 本身生成 `tuner.cost`。
- `symbol.for` 本轮允许承载 loop-carried `f64` 累计值；cost func 中的总 cost 必须通过该公开循环承载能力在 loop 内外传递。
- `arith.constant` 不生成 `tuner.cost`。
- 非循环结构的 `symbol.*` 不生成 `tuner.cost`。
- `func.return` 不生成 `tuner.cost`。
- 当前公开承接范围：
  - `dma.*`
  - `kernel.*`
  - `arch.*`
- 上述三族当前已有 op 全量纳入本轮承接范围；若遇到这三族之外的非 `symbol` dialect op，必须显式失败，不做 silent skip。

## 最小示例

### 输入示例

```text
builtin.module {
  func.func @matmul_kernel(%lhs : !nn.memory<[M, K], [K, 1], f32, #nn.space<global>>, %rhs : !nn.memory<[K, N], [N, 1], f32, #nn.space<global>>, %out : !nn.memory<[M, N], [N, 1], f32, #nn.space<global>>, %M : !symbol.int<"M">, %K : !symbol.int<"K">, %N : !symbol.int<"N">, %TILE_M : !symbol.int<"TILE_M">, %TILE_N : !symbol.int<"TILE_N">) {
    arch.launch<%c1, %c1, %c1>(@_device_matmul_kernel_, %lhs, %rhs, %out, %M, %K, %N, %TILE_M, %TILE_N) : (!nn.memory<[M, K], [K, 1], f32, #nn.space<global>>, !nn.memory<[K, N], [N, 1], f32, #nn.space<global>>, !nn.memory<[M, N], [N, 1], f32, #nn.space<global>>, !symbol.int<"M">, !symbol.int<"K">, !symbol.int<"N">, !symbol.int<"TILE_M">, !symbol.int<"TILE_N">) -> ()
    func.return
  }
  func.func @_device_matmul_kernel_(...) {
    %c0 = symbol.const 0 : !symbol.int<"0">
    symbol.for %it = %c0 to %M step %TILE_M {iter = #symbol.iter<start = "0", end = "M", step = "TILE_M">} {
      ...
      "dma.alloc"(...)
      "dma.slice"(...)
      "kernel.matmul"(...)
      func.return
    }
  }
}
```

### 预期输出摘要

```text
builtin.module {
  func.func @matmul_kernel(...) { ... }
  func.func @_device_matmul_kernel_(...) { ... }
  func.func @_cost_all__device_matmul_kernel_(...) -> f64 {
    %zero = arith.constant 0.0 : f64
    symbol.for %it = ... {
      ...
      %cost0 = tuner.cost(...) {kind = "move", cost_kind = "all", op_name = "dma.alloc", device_func = @_device_matmul_kernel_, ...} : (...) -> f64
      %cost1 = tuner.cost(...) {kind = "move", cost_kind = "all", op_name = "dma.slice", device_func = @_device_matmul_kernel_, ...} : (...) -> f64
      %cost2 = tuner.cost(...) {kind = "compute", cost_kind = "all", op_name = "kernel.matmul", device_func = @_device_matmul_kernel_, ...} : (...) -> f64
      %sum = ...  // 累计 %cost0/%cost1/%cost2/... 的 f64 总值
    }
    func.return %total : f64
  }
}
```

## 完成态定义

- [`spec/dialect/tuner.md`](../../spec/dialect/tuner.md) 已新增 `tuner.cost` 合同，且与 `tuner.param` 并存。
- `spec/pass/tuning/launch_kernel_cost_func.md` 已明确输入前置、命名规则、skip 规则、`kind` 选项与失败路径。
- `spec/pass/tuning/launch_kernel_cost_func.md` 已明确 `kind / cost_kind / op_name / device_func` 四个 pass-owned attrs 及其冲突失败语义。
- `spec/pass/tuning/launch_kernel_cost_func.md` 已明确 cost func 的唯一返回语义：汇总所有 `tuner.cost` 的 `f64` 结果并返回总值。
- `spec/dialect/symbol.md` 与 [`kernel_gen/dialect/symbol.py`](../../kernel_gen/dialect/symbol.py) 已补齐 `symbol.for` 的 loop-carried `f64` 公开合同、parse/print/verifier 与示例。
- `kernel_gen/passes/tuning/launch_kernel_cost_func.py` 已实现 `LaunchKernelCostFuncPass`，并通过 registry 公开为 `launch-kernel-cost-func`。
- `test/dialect/test_tuner_dialect.py` 已补齐 `tuner.cost` round-trip 与 verifier 路径。
- `test/dialect/test_symbol_dialect.py` 已补齐 `symbol.for` loop-carried `f64` 的 round-trip、verifier 与结果传递路径。
- `test/pass/test_launch_kernel_cost_func.py` 已机械锁定：
  - 单 wrapper / 单 device callee 成功路径
  - 同一 device callee 只生成一份 cost function
  - `arith.constant` / 非 loop `symbol.*` skip 路径
  - `kind=compute|move|all` 透传到 `tuner.cost.cost_kind`
  - cost func 会把全部 `tuner.cost` 返回的 `f64` 累计后再 `func.return`
  - 非法 `kind`、缺失 callee、重复生成冲突等失败路径
- `expectation/pass/tuning/launch_kernel_cost_func/` 已锁定公开输出形状。

## 验收设计

- 验收资产：
  - [`test/dialect/test_symbol_dialect.py`](../../test/dialect/test_symbol_dialect.py)
  - `expectation/pass/tuning/launch_kernel_cost_func/__main__.py`
  - `expectation/pass/tuning/launch_kernel_cost_func/basic_all.py`
  - `expectation/pass/tuning/launch_kernel_cost_func/shared_callee_once.py`
  - `expectation/pass/tuning/launch_kernel_cost_func/invalid_kind.py`
- 必过命令：
  - `pytest -q test/dialect/test_symbol_dialect.py`
  - `pytest -q test/dialect/test_tuner_dialect.py`
  - `pytest -q test/pass/test_launch_kernel_cost_func.py`
  - `pytest -q test/pass/test_pass_registry.py -k launch_kernel_cost_func`
  - `PYTHONPATH=. python expectation/pass/tuning/launch_kernel_cost_func`
- 验收重点：
  - `symbol.for` 的 loop-carried `f64` 是公开 dialect 能力，不是 pass 私有技巧；旧 `symbol.for` 文本仍可继续解析与校验。
  - `tuner.cost` 只承接原 op operands，attrs 平铺保留，并新增 `kind / cost_kind / op_name / device_func`。
  - 原 wrapper / device func 文本不变，只新增 cost func。
  - cost func 不是“只生成若干 `tuner.cost`”；它必须把所有局部 cost 汇总成单个 `f64` 返回值。
  - `arith.constant` 与非 `symbol.for` 的 `symbol.*` 不发 `tuner.cost`。
  - 原 op 若已含 `kind / cost_kind / op_name / device_func` 任一同名 attr，pass 必须显式失败。

### expectation case 矩阵

- `expectation/pass/tuning/launch_kernel_cost_func/basic_all.py`
  - `CASE-1: kind=all 基础成功路径`
  - 输入形状：单个 wrapper `@matmul_kernel` 指向单个 device callee `@_device_matmul_kernel_`；device body 内至少包含 `symbol.for`、三次 `dma.alloc`、一次 `kernel.matmul`、一次 `arch.barrier`，并保留 `symbol.const 0` 与 `symbol.get_dim`。
  - 必锁定合同：
    - 原 `@matmul_kernel` 与原 `@_device_matmul_kernel_` 文本仍存在，不被改写或重命名。
    - 新增且只新增一个 `func.func @_cost_all__device_matmul_kernel_(...) -> f64`。
    - cost func 内保留 `arith.constant 0.0 : f64` 作为累计零值，保留 `symbol.const 0` 作为 `symbol.for` 起始值。
    - cost func 内保留 `symbol.for`，不把循环打平。
    - `dma.alloc` / `kernel.matmul` / `arch.barrier` 会映射为 `tuner.cost`，且 `tuner.cost` 只传原 op operands。
    - 每个 `tuner.cost` 必须平铺保留原 op attributes，并新增 `kind / cost_kind / op_name / device_func`。
    - `tuner.cost.kind` 取单 op 语义分类：`dma.* -> "move"`、`kernel.matmul -> "compute"`、`arch.barrier -> "move"`。
    - `tuner.cost.cost_kind` 固定为 pass 参数 `"all"`。
    - `arith.constant`、`symbol.const`、`symbol.get_dim` 不生成 `tuner.cost`。
    - 每个 `tuner.cost(...)->f64` 结果都必须进入 `arith.addf` 累计链，最终 `func.return` 返回单个 `f64` 总 cost。
  - 补充计数断言：
    - `op_name = "dma.alloc"` 精确出现 3 次。
    - `op_name = "kernel.matmul"` 精确出现 1 次。
    - `op_name = "arch.barrier"` 精确出现 1 次。
    - `arith.addf` 至少出现 5 次，用于锁定“每个局部 cost 都并入总值”。

- `expectation/pass/tuning/launch_kernel_cost_func/shared_callee_once.py`
  - `CASE-1: 多 wrapper 共享同一 device callee`
  - 输入形状：两个 wrapper `@launch_a` / `@launch_b` 都通过 `arch.launch` 指向同一个 `@_device_shared_kernel_`，device body 内至少包含一次 `arch.barrier`。
  - 必锁定合同：
    - 原两个 wrapper 与共享的 device callee 文本仍存在。
    - 对同一个 device callee 只生成一份 `func.func @_cost_all__device_shared_kernel_(...) -> f64`。
    - 该唯一 cost func 内仍会为 `arch.barrier` 生成一条 `tuner.cost()`，并保留 `scope / visibility` 原 attrs。
    - 不允许因多个 `arch.launch` 重复生成重名 cost func。
  - 补充计数断言：
    - `func.func @_cost_all__device_shared_kernel_(` 精确出现 1 次。
    - `op_name = "arch.barrier"` 精确出现 1 次。

- `expectation/pass/tuning/launch_kernel_cost_func/invalid_kind.py`
  - `CASE-1: 非法 kind 失败路径`
  - 输入形状：最小 `arch.launch -> device callee` module，但 pass 参数显式给出非法 `kind=bad-kind`。
  - 必锁定合同：
    - 失败发生在 compile step 阶段，而不是 `CHECK` 匹配阶段。
    - `exit_code` 必须为 `2`。
    - `failed_check` 必须为 `None`。
    - `message` 前缀必须为 `IrcheckRunError: pass execution failed at step 1 (pass launch-kernel-cost-func):`。
    - `message` 中必须明确包含允许值集合 `compute` / `move` / `all`。

- `expectation/pass/tuning/launch_kernel_cost_func/__main__.py`
  - `CASE-ROOT: 目录级入口`
  - 输入形状：无独立 IR；负责串行运行 `basic_all.py`、`shared_callee_once.py`、`invalid_kind.py`。
  - 必锁定合同：
    - 目录级入口的运行顺序固定为 `basic_all -> shared_callee_once -> invalid_kind`。
    - 任一子 expectation 失败时直接向上抛错，不吞异常。
    - 全部通过时目录入口自身退出码为 `0`。

### case 与验收职责分层

- expectation 只锁定公开输出形状与失败前缀：
  - `basic_all.py` 锁定 `kind=all` 下的 IR 形状、skip 规则、attrs 透传与 `f64` 汇总返回。
  - `shared_callee_once.py` 锁定“同一 device callee 只生成一份 cost func”。
  - `invalid_kind.py` 锁定非法 `kind` 的公开失败语义。
  - `__main__.py` 锁定目录级入口合同。
- `kind=compute` 与 `kind=move` 不再额外拆成独立 expectation 文件；它们由 [`test/pass/test_launch_kernel_cost_func.py`](../../test/pass/test_launch_kernel_cost_func.py) 机械锁定，避免 expectation 资产无意义膨胀。
- `arith.constant` / 非 loop `symbol.*` skip 路径以双层方式锁定：
  - expectation 在 `basic_all.py` 中锁定“不发 `tuner.cost`”的公开形状；
  - pytest 负责补齐更细的 op 级计数与失败定位。

### pytest case 矩阵

- [`test/pass/test_launch_kernel_cost_func.py`](../../test/pass/test_launch_kernel_cost_func.py)
  - `CASE-PASS-1: kind=all 成功路径`
    - 锁定 `_cost_all_<device>` 命名、参数列表与 device func 完全一致、返回值固定为 `f64`。
    - 锁定 `dma.* / kernel.* / arch.*` 当前已有 op 都会生成 `tuner.cost`，且 `kind` 分类正确。
    - 锁定 `arith.constant` / 非 loop `symbol.*` / `func.return` 不生成 `tuner.cost`。
    - 锁定 cost func 会把所有局部 `f64` cost 通过 `arith.addf` 并入总值。
  - `CASE-PASS-2: kind=compute 成功路径`
    - 锁定新增函数名为 `_cost_compute_<device>`。
    - 锁定所有受支持 op 仍会生成 `tuner.cost`，但每条 `tuner.cost.cost_kind` 统一为 `"compute"`。
    - 锁定 `dma/arch` 这类 `kind="move"` 的 op 在 `cost_kind="compute"` 视角下不会被 pass 直接删掉。
  - `CASE-PASS-3: kind=move 成功路径`
    - 锁定新增函数名为 `_cost_move_<device>`。
    - 锁定所有受支持 op 仍会生成 `tuner.cost`，但每条 `tuner.cost.cost_kind` 统一为 `"move"`。
    - 锁定 `kernel.*` 这类 `kind="compute"` 的 op 在 `cost_kind="move"` 视角下不会被 pass 直接删掉。
  - `CASE-PASS-4: shared callee 去重`
    - 锁定两个 wrapper 指向同一 device callee 时，同一 `cost_kind` 下只生成一份 cost func。
  - `CASE-PASS-5: 非法 kind`
    - 锁定 `kind` 非法时抛 `ValueError`，错误消息至少包含 `compute / move / all`。
  - `CASE-PASS-6: 缺失 callee`
    - 锁定 `arch.launch` 指向的 symbol ref 无法解析到 device func 时显式失败，不做 silent skip。
  - `CASE-PASS-7: attr 冲突`
    - 锁定原 op 若已带 `kind / cost_kind / op_name / device_func` 任一同名 attr，pass 显式失败。
  - `CASE-PASS-8: 非支持 op 失败`
    - 锁定 device body 中若出现 `dma/kernel/arch` 之外、且不在 skip 白名单内的非 `symbol` dialect op，pass 显式失败。
  - `CASE-PASS-9: 预存重名 cost func`
    - 锁定输入 module 若已存在目标命名规则对应的 cost func，pass 显式失败，不做覆盖或静默复用。

- [`test/pass/test_pass_registry.py`](../../test/pass/test_pass_registry.py)
  - `CASE-REG-1: registry 注册`
    - 锁定 `launch-kernel-cost-func` 已注册到 pass registry。
  - `CASE-REG-2: from_options(kind=...)`
    - 锁定 `kind=compute|move|all` 能通过 registry 选项构造 pass。
  - `CASE-REG-3: 非法 kind 透传失败`
    - 锁定非法 `kind` 不会在 registry 层被吞掉，而是透传为明确失败。

### 白名单与失败矩阵

- 允许 pass 直接承接并生成 `tuner.cost` 的原 op 家族只有：
  - `dma.*`
  - `kernel.*`
  - `arch.*`
- 允许 pass 直接跳过、不生成 `tuner.cost` 的原 op 只有：
  - `arith.constant`
  - 非循环结构的 `symbol.*`
  - `func.return`
  - `symbol.for` 自身
- 因此 device body 中其他 op 的处理口径必须唯一：
  - 若属于 `symbol` dialect 但不是 `symbol.for`，按 skip 规则处理；
  - 若属于 `dma/kernel/arch`，必须产出 `tuner.cost`；
  - 若属于其他非 `symbol` dialect，一律显式失败，不做 silent skip。

## 阶段拆分

### S1：合同冻结

#### 阶段目标

- 冻结 `symbol.for` 的 loop-carried `f64` 前置合同，以及 `tuner.cost`、`launch-kernel-cost-func` pass、命名规则、`kind/cost_kind` 语义、skip 规则与 expectation 资产布局。

#### 目标 spec / API

- [`spec/dialect/symbol.md`](../../spec/dialect/symbol.md)
- [`spec/dialect/tuner.md`](../../spec/dialect/tuner.md)
- `spec/pass/tuning/launch_kernel_cost_func.md`
- [`spec/pass/registry.md`](../../spec/pass/registry.md)
- `公开 API：SymbolForOp(loop-carried f64) / LaunchKernelCostFuncPass(kind=\"all\") / TunerCostOp`

#### 可改文件

- [`spec/dialect/symbol.md`](../../spec/dialect/symbol.md)
- [`spec/dialect/tuner.md`](../../spec/dialect/tuner.md)
- `spec/pass/tuning/launch_kernel_cost_func.md`
- [`spec/pass/registry.md`](../../spec/pass/registry.md)
- [`ARCHITECTURE/plan/launch_kernel_cost_func_pass_green_plan.md`](../../ARCHITECTURE/plan/launch_kernel_cost_func_pass_green_plan.md)

#### 预期示例代码

```python
pass_obj = LaunchKernelCostFuncPass(kind="move")
module = pass_obj.run(module)
```

#### 预期输出

```text
func.func @_cost_move__device_matmul_kernel_(...) -> f64
%cost = tuner.cost(...) {kind = "move", cost_kind = "move", op_name = "dma.slice", device_func = @_device_matmul_kernel_, ...} : (...) -> f64
```

#### 目标验收资产

- `spec/dialect/symbol.md` 明确 `symbol.for` 的 loop-carried `f64` 合同边界
- `spec/dialect/tuner.md` 明确 `tuner.cost`
- `spec/pass/tuning/launch_kernel_cost_func.md` 明确输入输出与失败路径

#### 验收必过项目

- 文本核对：`symbol.for` 仅新增单个 loop-carried `f64`，不扩成通用多结果控制流
- 文本核对：`tuner.cost` 只透传原 op operands，attrs 平铺保留
- 文本核对：原 wrapper / device func 不改

#### 任务新建建议

- `推进方式：按默认 spec/build/review/merge 路线推进，本阶段只定义收口范围。`
- `阶段目标：冻结 symbol.for loop-carried f64、tuner.cost 与 launch-kernel-cost-func pass 的公开合同。`
- `记录文件：agents/codex-multi-agents/log/task_records/2026/16/20260416-launch-kernel-cost-s1.md`

### S2：symbol / tuner dialect 扩展

#### 阶段目标

- 在 `symbol dialect` 中补齐 `symbol.for` 的 loop-carried `f64`，并在 `tuner dialect` 中新增 `tuner.cost`；同步补齐 parse/print/verifier 与方言测试。

#### 目标 spec / API

- [`spec/dialect/symbol.md`](../../spec/dialect/symbol.md)
- [`kernel_gen/dialect/symbol.py`](../../kernel_gen/dialect/symbol.py)
- [`spec/dialect/tuner.md`](../../spec/dialect/tuner.md)
- [`kernel_gen/dialect/tuner.py`](../../kernel_gen/dialect/tuner.py)

#### 可改文件

- [`kernel_gen/dialect/symbol.py`](../../kernel_gen/dialect/symbol.py)
- [`test/dialect/test_symbol_dialect.py`](../../test/dialect/test_symbol_dialect.py)
- [`spec/dialect/symbol.md`](../../spec/dialect/symbol.md)
- [`kernel_gen/dialect/tuner.py`](../../kernel_gen/dialect/tuner.py)
- [`test/dialect/test_tuner_dialect.py`](../../test/dialect/test_tuner_dialect.py)
- [`spec/dialect/tuner.md`](../../spec/dialect/tuner.md)

#### spec 校正口径

- 允许在本阶段内最小同步校正 [`spec/dialect/symbol.md`](../../spec/dialect/symbol.md) 与 [`spec/dialect/tuner.md`](../../spec/dialect/tuner.md)，用于对齐 `SymbolForOp` 和 `TunerCostOp` 的真实 parse/print/verifier 约束。
- 不允许自行改变 `S1` 冻结的核心合同；若实现发现核心合同不可行，必须回到架构侧裁定后再继续。
- 发生 `spec` 校正时，任务记录必须写清校正原因、对应实现位置与测试命令。

#### 预期示例代码

```text
%cost = tuner.cost(%arg0, %arg1) {kind = "move", cost_kind = "all", op_name = "dma.copy", device_func = @_device_add} : (!nn.memory<[M], [1], f32, #nn.space<global>>, !nn.memory<[M], [1], f32, #nn.space<tsm>>) -> f64
```

#### 目标验收资产

- `test/dialect/test_symbol_dialect.py`
- `test/dialect/test_tuner_dialect.py`

#### 验收必过项目

- `pytest -q test/dialect/test_symbol_dialect.py`
- `pytest -q test/dialect/test_tuner_dialect.py`

#### 任务新建建议

- `推进方式：按默认 spec/build/review/merge 路线推进，本阶段只定义收口范围。`
- `阶段目标：补齐 symbol.for loop-carried f64、tuner.cost dialect op 与方言测试。`
- `记录文件：agents/codex-multi-agents/log/task_records/2026/16/20260416-launch-kernel-cost-s2.md`

### S3：pass 生成逻辑

#### 阶段目标

- 实现 `launch-kernel-cost-func` pass，生成一份 cost function，并锁定 skip/duplicate/failure 路径。

#### 目标 spec / API

- `spec/pass/tuning/launch_kernel_cost_func.md`
- `公开 API：LaunchKernelCostFuncPass / launch-kernel-cost-func`

#### 可改文件

- `kernel_gen/passes/tuning/launch_kernel_cost_func.py`
- `kernel_gen/passes/tuning/__init__.py`
- [`kernel_gen/passes/registry.py`](../../kernel_gen/passes/registry.py)
- `test/pass/test_launch_kernel_cost_func.py`
- [`test/pass/test_pass_registry.py`](../../test/pass/test_pass_registry.py)

#### spec 校正口径

- 允许在本阶段内最小同步校正 `spec/pass/tuning/launch_kernel_cost_func.md` 与 [`spec/pass/registry.md`](../../spec/pass/registry.md)，用于对齐 pass 选项、registry 接入、失败路径与实现中的必要约束。
- 不允许自行改变 `S1` 冻结的核心合同；若 pass 实现发现核心合同不可行，必须回到架构侧裁定后再继续。
- 发生 `spec` 校正时，任务记录必须写清校正原因、对应实现位置与测试命令。

#### 预期示例代码

```python
load_builtin_passes()
pass_obj = build_registered_pass("launch-kernel-cost-func", {"kind": "compute"})
module = pass_obj.run(module)
```

#### 预期输出

```text
func.func @_cost_compute__device_add(...) -> f64
```

#### 目标验收资产

- `test/pass/test_launch_kernel_cost_func.py`
- `test/pass/test_pass_registry.py -k launch_kernel_cost_func`

#### 验收必过项目

- `pytest -q test/pass/test_launch_kernel_cost_func.py`
- `pytest -q test/pass/test_pass_registry.py -k launch_kernel_cost_func`

#### 任务新建建议

- `推进方式：按默认 spec/build/review/merge 路线推进，本阶段只定义收口范围。`
- `阶段目标：实现 launch-kernel-cost-func pass 与 registry 接入。`
- `记录文件：agents/codex-multi-agents/log/task_records/2026/16/20260416-launch-kernel-cost-s3.md`

### S4：expectation 收口

#### 阶段目标

- 为公开输出形状补齐 expectation 资产，锁定 package root、成功路径与失败路径。
- 本阶段 expectation 必须锁定“cost func 会累计所有 `tuner.cost` 并返回 `f64` 总值”的公开合同；loop 内累计承载统一按 `symbol.for` 的 loop-carried `f64` 新合同写死。

#### 目标 spec / API

- `expectation/pass/tuning/launch_kernel_cost_func`

#### 可改文件

- `expectation/pass/tuning/launch_kernel_cost_func/__main__.py`
- `expectation/pass/tuning/launch_kernel_cost_func/basic_all.py`
- `expectation/pass/tuning/launch_kernel_cost_func/shared_callee_once.py`
- `expectation/pass/tuning/launch_kernel_cost_func/invalid_kind.py`
- `test/pass/test_launch_kernel_cost_func.py`

#### 预期示例代码

```text
// CHECK: func.func @_cost_all__device_matmul_kernel_
// CHECK: symbol.for
// CHECK: tuner.cost
// CHECK: func.return
```

#### 目标验收资产

- `expectation/pass/tuning/launch_kernel_cost_func`

#### 验收必过项目

- `PYTHONPATH=. python expectation/pass/tuning/launch_kernel_cost_func`
- `pytest -q test/pass/test_launch_kernel_cost_func.py`

#### 任务新建建议

- `推进方式：按默认 spec/build/review/merge 路线推进，本阶段只定义收口范围。`
- `阶段目标：补齐 launch-kernel-cost-func expectation 合同资产。`
- `记录文件：agents/codex-multi-agents/log/task_records/2026/16/20260416-launch-kernel-cost-s4.md`

## 已确认口径

- 用户已明确确认：本轮允许扩展 [`kernel_gen/dialect/symbol.py`](../../kernel_gen/dialect/symbol.py) 对应的 `symbol.for`，支持 loop-carried `f64`。
- 因此 `launch-kernel-cost-func` 的 cost func 不再额外引入私有“循环累计承载”方案；loop 内外累计值统一走 `symbol.for` 的公开 loop-carried 结果语义。
- `tuner.cost` 的返回值固定为 `f64`，且 cost func 必须把所有 `tuner.cost` 的结果相加后返回；这一点已冻结为硬合同。

## 参考资料

- 用户草稿：[`plan/tuner.const.pass.mlir`](../../plan/tuner.const.pass.mlir)
- tuner dialect 现状：[`spec/dialect/tuner.md`](../../spec/dialect/tuner.md)、[`kernel_gen/dialect/tuner.py`](../../kernel_gen/dialect/tuner.py)
- analysis 现状：[`spec/analysis/analysis_engine.md`](../../spec/analysis/analysis_engine.md)、[`spec/pass/analysis/func_cost.md`](../../spec/pass/analysis/func_cost.md)、[`kernel_gen/passes/analysis/func_cost.py`](../../kernel_gen/passes/analysis/func_cost.py)
- 前置 wrapper/device 形状：[`spec/pass/lowering/outline_device_kernel.md`](../../spec/pass/lowering/outline_device_kernel.md)、[`kernel_gen/passes/lowering/outline_device_kernel.py`](../../kernel_gen/passes/lowering/outline_device_kernel.py)
  - 这里只是读取现有 `arch.launch -> device func` 输入基线；本计划新增资产仍统一写入 `spec/pass/tuning/`、`kernel_gen/passes/tuning/` 与 `expectation/pass/tuning/`。
- registry 接入：[`spec/pass/registry.md`](../../spec/pass/registry.md)、[`kernel_gen/passes/registry.py`](../../kernel_gen/passes/registry.py)
