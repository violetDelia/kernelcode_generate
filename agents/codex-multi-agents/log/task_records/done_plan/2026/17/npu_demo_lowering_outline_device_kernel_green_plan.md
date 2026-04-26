# npu_demo_lowering_outline_device_kernel_green_plan.md

> 说明：该文件为 `npu_pipeline_outline_device_kernel_contract` / `npu_demo_lowering_outline_device_kernel` 主题的归档承接快照。自 `origin/main@9a0a52a0730581787bcf4c767167253c4c5b936e` 起的后续主线现场，均不再包含 `ARCHITECTURE/plan/npu_pipeline_outline_device_kernel_contract_green_plan.md`、`TODO.md` 与 `expectation` 包；当前主题只由 `agents/codex-multi-agents/log/task_records/done_plan/2026/17/npu_demo_lowering_outline_device_kernel_green_plan.md` 承接。后续计划状态、结论和续接依据统一收口到本归档文件与对应任务记录；若需核对某一轮复验基线，以对应复验段和修复任务记录为准。

## 文档信息

- 创建者：`Codex`
- 最后一次更改：`睡觉小分队`
- 目标 `spec`：
  - [`spec/pass/pipeline/npu_demo_lowering.md`](../../../../../../../spec/pass/pipeline/npu_demo_lowering.md)
  - [`spec/pass/outline_device_kernel.md`](../../../../../../../spec/pass/outline_device_kernel.md)
  - [`spec/pass/attach_arch_information.md`](../../../../../../../spec/pass/attach_arch_information.md)
  - [`spec/dsl/gen_kernel/gen_kernel.md`](../../../../../../../spec/dsl/gen_kernel/gen_kernel.md)
  - [`spec/dsl/gen_kernel/emit.md`](../../../../../../../spec/dsl/gen_kernel/emit.md)
- 目标 `API`：
  - `build_npu_demo_lowering_pipeline(options: dict[str, str] | None = None) -> PassManager`
  - `build_registered_pipeline("npu-demo-lowering", {"target": "npu_demo"}) -> PassManager`
  - `OutlineDeviceKernelPass`
  - `gen_kernel(op_or_func, ctx: EmitCContext) -> str`
  - `emit_c(obj, ctx: EmitCContext) -> str`
- 目标 `test`：
  - [`test/pass/test_pipeline_npu_demo_lowering.py`](../../../../../../../test/pass/test_pipeline_npu_demo_lowering.py)
  - [`test/pass/outline_device_kernel/test_outline_device_kernel.py`](../../../../../../../test/pass/outline_device_kernel/test_outline_device_kernel.py)
  - [`test/pass/test_attach_arch_information.py`](../../../../../../../test/pass/test_attach_arch_information.py)
  - [`test/pass/test_pass_registry.py`](../../../../../../../test/pass/test_pass_registry.py)
  - [`test/dsl/gen_kernel/test_gen_kernel.py`](../../../../../../../test/dsl/gen_kernel/test_gen_kernel.py)
  - [`test/dsl/gen_kernel/emit/test_emit.py`](../../../../../../../test/dsl/gen_kernel/emit/test_emit.py)
- 目标 `验收资产`：
  - `expectation/pass/outline_device_kernel`
  - `expectation/pass/outline_device_kernel/__main__.py`
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 -m expectation.pass.outline_device_kernel`
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/pass/test_pipeline_npu_demo_lowering.py test/pass/test_attach_arch_information.py test/pass/outline_device_kernel/test_outline_device_kernel.py test/dsl/gen_kernel/test_gen_kernel.py test/dsl/gen_kernel/emit/test_emit.py`
- 目标 `功能实现`：
  - [`kernel_gen/passes/pipeline/npu_demo_lowering.py`](../../../../../../../kernel_gen/passes/pipeline/npu_demo_lowering.py)
  - [`kernel_gen/passes/outline_device_kernel.py`](../../../../../../../kernel_gen/passes/outline_device_kernel.py)
  - [`kernel_gen/passes/attach_arch_information.py`](../../../../../../../kernel_gen/passes/attach_arch_information.py)
  - [`kernel_gen/passes/registry.py`](../../../../../../../kernel_gen/passes/registry.py)
  - [`kernel_gen/dsl/gen_kernel/gen_kernel.py`](../../../../../../../kernel_gen/dsl/gen_kernel/gen_kernel.py)
  - [`kernel_gen/dsl/gen_kernel/kernel_emitter.py`](../../../../../../../kernel_gen/dsl/gen_kernel/kernel_emitter.py)
  - [`kernel_gen/dsl/gen_kernel/emit/__init__.py`](../../../../../../../kernel_gen/dsl/gen_kernel/emit/__init__.py)
  - [`kernel_gen/dsl/gen_kernel/emit_context.py`](../../../../../../../kernel_gen/dsl/gen_kernel/emit_context.py)
  - [`kernel_gen/dsl/gen_kernel/emit/npu_demo/__init__.py`](../../../../../../../kernel_gen/dsl/gen_kernel/emit/npu_demo/__init__.py)

## 任务清单

| 任务 | 前置任务 | worktree | 记录文件 |
| --- | --- | --- | --- |
| `S1：npu-demo-lowering / attach-arch-information / outline-device-kernel / gen_kernel-emit 合同分层收口` | 无 | `wt-20260426-npu-pipeline-outline-s1` | `agents/codex-multi-agents/log/task_records/2026/17/20260426-npu-pipeline-outline-s1.md` |
| `R1：计划资产与 latest main 现场对齐 / 归档记录收口` | `T-20260426-dbabb1e3` | `wt-20260427-npu-pipeline-outline-plan-align-s2` | `agents/codex-multi-agents/log/task_records/2026/17/20260427-npu-pipeline-outline-plan-align-s2.md` |

## 任务创建记录

- `S1=T-20260426-dbabb1e3，任务类型 spec，worktree=wt-20260426-npu-pipeline-outline-s1，记录文件=agents/codex-multi-agents/log/task_records/2026/17/20260426-npu-pipeline-outline-s1.md`
- `R1=T-20260427-edf6681e，任务类型 spec，依赖 T-20260426-dbabb1e3，worktree=wt-20260427-npu-pipeline-outline-plan-align-s2，记录文件=agents/codex-multi-agents/log/task_records/2026/17/20260427-npu-pipeline-outline-plan-align-s2.md`
- `归档前最后一次共享计划快照状态：TODO.md 计划状态曾为 2/1/1 进行中；自 9a0a52a0730581787bcf4c767167253c4c5b936e 起的后续主线现场已无活动计划路径、TODO.md 与 expectation 包，后续状态以本归档文件与任务记录为准`

## 评审摘要

- 评审结论：`通过`
- 评审人：`Avicenna / Anscombe / Sartre`
- 结论摘要：`三方复评均已通过。最终口径已收口为：S1 保持单阶段；范围为 pass/pipeline + gen_kernel/emit，不扩到 dsl_run / execute_engine；standalone expectation 仅作为 standalone pass 终端语义见证，不冒充 pipeline 第一真源；registry 回归为本轮常驻验收；attach->outline 与 emit_c(outlined module) 若现有资产无法直接证明，则在 S1 内补最小 bridge / direct case，或将正文表述降级为分层推断。`

## 终验 / 复验 / 修复复核记录

- 结论人：`守护最好的爱莉希雅`
- 结论：`不通过`
- 验证基线：`origin/main@9a0a52a0730581787bcf4c767167253c4c5b936e`
- 执行目录：`/home/lfr/kernelcode_generate-wt-20260427-npu-pipeline-outline-recheck`
- 相关 expectation 摘要：`按正文当前保留入口尝试执行 PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 -m expectation.pass.outline_device_kernel，但最新远端干净现场不存在 expectation 包，无法装载该入口。`
- 最小阻断项或通过摘要：`最新同步现场本身未携带这份计划资产：origin/main@9a0a52a0730581787bcf4c767167253c4c5b936e 的干净 worktree 中没有 ARCHITECTURE/plan/npu_pipeline_outline_device_kernel_contract_green_plan.md，也不存在 expectation/pass/outline_device_kernel 或 expectation 包；当前只剩另一份 done_plan 归档名为 npu_demo_lowering_outline_device_kernel_green_plan.md。由于无法在最新主线现场对你指定计划执行正文保留的 expectation 合同验收，当前不能把这份计划当作已与最新主线对齐的有效归档对象。`
- 是否已创建修复任务：`是；T-20260427-edf6681e`

### 当前唯一修复任务（2026-04-27）

- 任务号：`T-20260427-edf6681e`
- worktree：`/home/lfr/kernelcode_generate/wt-20260427-npu-pipeline-outline-plan-align-s2`
- 记录文件：`/home/lfr/kernelcode_generate/wt-20260427-npu-pipeline-outline-plan-align-s2/agents/codex-multi-agents/log/task_records/2026/17/20260427-npu-pipeline-outline-plan-align-s2.md`
- 任务类型：`spec`
- 任务目标：`对齐计划资产与 latest main 现场，收口 done_plan / 任务记录承接位置，并让计划正文、TODO.md 与直接关联归档记录和最新主线一致；不得改动任何 expectation。`
- 任务边界：`只处理计划资产与 latest main 现场的对齐，以及直接关联的归档 / 记录收口；不改动 expectation，不扩到实现、测试或其他专题资产。`
- 记录要求：`执行记录必须包含真实自检与 Diff 反推自测；若最新主线现场仍缺失计划资产或归档承接位置不一致，必须如实记录，不得擅自补写未确认结论。`

## 归档对齐记录

时间：2026-04-27 00:12 +0800
经办人：睡觉小分队
任务：T-20260427-edf6681e
任务目标：把 `npu_pipeline_outline_device_kernel_contract` 主题的计划资产对齐到 latest main 仍存在的承接位置，只处理 surviving done_plan 与直接关联记录。
改动：在本归档文件顶部新增稳定承接说明；把 `最后一次更改` 收到本轮执行人；保留当前专题任务清单和 `2026-04-27` 复验 / 修复任务信息；将 `任务创建记录` 改成归档前快照语义；新增当前 `归档对齐记录`；并把原根目录层级的 Markdown 相对链接统一改到当前 done_plan 层级。
验证：latest main 现场缺失检查、`ls-tree` 基线核对、Markdown 相对链接校验和当前任务记录引用，详见 [`20260427-npu-pipeline-outline-plan-align-s2.md`](../../../2026/17/20260427-npu-pipeline-outline-plan-align-s2.md)。
结论：`npu_pipeline_outline_device_kernel_contract` 主题在 latest main 干净现场中不再通过活动计划路径、TODO.md 或 expectation 包承接，后续应以本归档文件和对应任务记录作为唯一续接依据；不需要在该现场重新补回活动计划路径、TODO.md 或 expectation 包。`

## 输入摘要

- 目标：把 `expectation/pass/outline_device_kernel` 这组 standalone pass 合同，正式纳入 `npu-demo-lowering` 的分层验收链，并把 `gen_kernel/emit` 对 outlined 结果的消费合同一并收口。
- 不做什么：不改 `expectation`；不改 `dsl_run`、`execute_engine`；不扩展到 `default-lowering`；不新增第二套 outline 实现。
- 当前痛点：仓库里 `outline-device-kernel` 已经在 `npu-demo-lowering` 中，但当前 `expectation` 只锁 standalone pass，pipeline 层没有独立黑盒 expectation；同时若 pipeline 输出与 `gen_kernel/emit` 的消费约定不一致，问题会落在 `kernel_gen/dsl/gen_kernel/**`，不能只盯 pass 顺序层。
- 完成后用户最想看到的例子：执行人只看计划书就能知道，`npu-demo-lowering` 的末段固定是 `outline-device-kernel`；验收时要分层看 pipeline 顺序、attach->outline 桥接、standalone outline 终态，以及 `gen_kernel/emit` 如何直接消费 outlined 结果，而不是把多层合同混成一条。

## 计划目标

- 明确 `outline-device-kernel` 已是 `npu-demo-lowering` 的固定最后一段，本计划不再把主题写成“新增 pass 接入”。
- 把 `npu-demo-lowering`、`attach-arch-information`、`outline-device-kernel` 三层合同关系写清，避免把 standalone pass 输入域误写成 pipeline 输入域。
- 在不改 `expectation` 的前提下，收出一条可执行的分层验收链：pipeline 顺序 + attach/outline 桥接 + standalone outline expectation + `gen_kernel/emit` 对 outlined 结果的直接消费。
- 保持 `build_npu_demo_lowering_pipeline(...)`、`build_registered_pipeline("npu-demo-lowering", ...)` 与 `OutlineDeviceKernelPass` 的公开 API 不变。
- 把 `gen_kernel(op_or_func, ctx)` 与 `emit_c(obj, ctx)` 一并纳入范围，但只收 `kernel_gen/dsl/gen_kernel/**` 这一层，不扩到 `dsl_run / execute_engine`。

## 当前基线

- 当前公开合同：
  - [`spec/pass/pipeline/npu_demo_lowering.md`](../../../../../../../spec/pass/pipeline/npu_demo_lowering.md) 已把 `OutlineDeviceKernelPass` 写进 `npu-demo-lowering` 固定顺序。
  - [`spec/pass/outline_device_kernel.md`](../../../../../../../spec/pass/outline_device_kernel.md) 已定义 standalone `outline-device-kernel` 合同。
  - [`spec/pass/attach_arch_information.md`](../../../../../../../spec/pass/attach_arch_information.md) 已定义 pipeline 进入 outline 前的 launch / shared-memory 元信息注入合同。
  - [`spec/dsl/gen_kernel/gen_kernel.md`](../../../../../../../spec/dsl/gen_kernel/gen_kernel.md) 已定义 `gen_kernel(...)` 的公开包装合同。
  - [`spec/dsl/gen_kernel/emit.md`](../../../../../../../spec/dsl/gen_kernel/emit.md) 已定义 `emit_c(...) / emit_c_op(...) / emit_c_value(...)` 的公开消费合同。
- 当前公开 API：
  - `build_npu_demo_lowering_pipeline(options: dict[str, str] | None = None) -> PassManager`
  - `build_registered_pipeline("npu-demo-lowering", {"target": "npu_demo"}) -> PassManager`
  - `OutlineDeviceKernelPass`
  - `gen_kernel(op_or_func, ctx: EmitCContext) -> str`
  - `emit_c(obj, ctx: EmitCContext) -> str`
- 当前实现入口：
  - [`kernel_gen/passes/pipeline/npu_demo_lowering.py`](../../../../../../../kernel_gen/passes/pipeline/npu_demo_lowering.py) 当前固定顺序已经包含 `outline-device-kernel`。
  - [`kernel_gen/passes/outline_device_kernel.py`](../../../../../../../kernel_gen/passes/outline_device_kernel.py) 当前已能输出 `host wrapper + device body`。
  - [`kernel_gen/passes/attach_arch_information.py`](../../../../../../../kernel_gen/passes/attach_arch_information.py) 当前承担进入 outline 前的 arch 元信息注入。
  - [`kernel_gen/dsl/gen_kernel/gen_kernel.py`](../../../../../../../kernel_gen/dsl/gen_kernel/gen_kernel.py) 当前承担 `func.func / builtin.module` 级源码发射入口。
  - [`kernel_gen/dsl/gen_kernel/kernel_emitter.py`](../../../../../../../kernel_gen/dsl/gen_kernel/kernel_emitter.py) 当前承担 outlined 结果的函数级/模块级发射骨架。
  - [`kernel_gen/dsl/gen_kernel/emit/__init__.py`](../../../../../../../kernel_gen/dsl/gen_kernel/emit/__init__.py) 与 [`kernel_gen/dsl/gen_kernel/emit/npu_demo/__init__.py`](../../../../../../../kernel_gen/dsl/gen_kernel/emit/npu_demo/__init__.py) 当前承担节点级 emit 分发与 `target="npu_demo"` 实现接入。
- 当前测试与验收资产：
  - [`test/pass/test_pipeline_npu_demo_lowering.py`](../../../../../../../test/pass/test_pipeline_npu_demo_lowering.py) 当前只锁 builder、固定顺序和非法 option。
  - [`test/pass/test_attach_arch_information.py`](../../../../../../../test/pass/test_attach_arch_information.py) 锁 attach 阶段自身合同。
  - [`test/pass/outline_device_kernel/test_outline_device_kernel.py`](../../../../../../../test/pass/outline_device_kernel/test_outline_device_kernel.py) 锁 standalone outline 语义与失败边界。
  - [`test/dsl/gen_kernel/test_gen_kernel.py`](../../../../../../../test/dsl/gen_kernel/test_gen_kernel.py) 当前锁 `npu_demo` wrapper/body、launch module 与 module 级源码发射。
  - [`test/dsl/gen_kernel/emit/test_emit.py`](../../../../../../../test/dsl/gen_kernel/emit/test_emit.py) 当前锁 `emit_c(...)`、`emit_c_op(...)`、`emit_c_value(...)` 和 `npu_demo` 节点级 emit。
  - `expectation/pass/outline_device_kernel` 当前是 standalone pass expectation，不是 pipeline expectation。
- 当前缺口：
  - 缺少一份明确计划告诉执行链：本专题不需要新增实现，重点是把 pipeline 顺序、attach->outline 桥接、standalone expectation，以及 `gen_kernel/emit` 消费 outlined 结果这四层合同正式串起来。
  - `npu-demo-lowering` 目前没有独立 pipeline 黑盒 expectation，而本轮又已确认不改 `expectation`，因此计划书必须显式采用“分层验收”，不能假装已有 pipeline expectation。
  - 用户已明确，真实修复可能落在 `emitc/gen_kernel`；因此计划不能只写 pass/pipeline，否则执行人会在 pass 已正确时错误停手。

## 合同真源顺序

- `npu-demo-lowering` builder / 顺序 / options 真源顺序：
  - [`spec/pass/pipeline/npu_demo_lowering.md`](../../../../../../../spec/pass/pipeline/npu_demo_lowering.md)
  - > [`test/pass/test_pipeline_npu_demo_lowering.py`](../../../../../../../test/pass/test_pipeline_npu_demo_lowering.py)
  - > 当前实现
- `attach -> outline` 桥接真源顺序：
  - [`spec/pass/attach_arch_information.md`](../../../../../../../spec/pass/attach_arch_information.md)
  - > [`spec/pass/outline_device_kernel.md`](../../../../../../../spec/pass/outline_device_kernel.md)
  - > [`test/pass/test_attach_arch_information.py`](../../../../../../../test/pass/test_attach_arch_information.py)
  - > [`test/pass/outline_device_kernel/test_outline_device_kernel.py`](../../../../../../../test/pass/outline_device_kernel/test_outline_device_kernel.py)
  - > 当前实现
- standalone `outline-device-kernel` 终端 expectation 见证顺序：
  - `expectation/pass/outline_device_kernel`
  - > [`spec/pass/outline_device_kernel.md`](../../../../../../../spec/pass/outline_device_kernel.md)
  - > [`test/pass/outline_device_kernel/test_outline_device_kernel.py`](../../../../../../../test/pass/outline_device_kernel/test_outline_device_kernel.py)
  - > 当前实现
- `gen_kernel / emit` 消费 outlined 结果真源顺序：
  - [`spec/dsl/gen_kernel/gen_kernel.md`](../../../../../../../spec/dsl/gen_kernel/gen_kernel.md)
  - > [`spec/dsl/gen_kernel/emit.md`](../../../../../../../spec/dsl/gen_kernel/emit.md)
  - > [`test/dsl/gen_kernel/test_gen_kernel.py`](../../../../../../../test/dsl/gen_kernel/test_gen_kernel.py)
  - > [`test/dsl/gen_kernel/emit/test_emit.py`](../../../../../../../test/dsl/gen_kernel/emit/test_emit.py)
  - > 当前实现
- 本计划约束：
  - 当前“pipeline 黑盒终态 IR expectation”不存在，因此本轮采用分层验收；
  - 不得把 standalone `outline_device_kernel` expectation 写成 `npu-demo-lowering` 的现成黑盒 expectation；
  - standalone `outline_device_kernel` expectation 只作为 standalone pass 终端语义见证，不上提成 pipeline 层第一真源；
  - 若 pass 输出与 `gen_kernel/emit` 消费不一致，允许在 `kernel_gen/dsl/gen_kernel/**` 范围内收口，但不因此扩到 `dsl_run / execute_engine`；
  - [`test/tools/test_dsl_run.py`](../../../../../../../test/tools/test_dsl_run.py) 与 [`test/test_main_npu_demo_pipeline.py`](../../../../../../../test/test_main_npu_demo_pipeline.py) 当前只作下游见证，不列为本轮必过资产。

## 方案比较与选型

- 不采用方案：把本专题写成“把 `outline-device-kernel` 新增进 npu pipeline”。
- 不采用原因：这件事已经是既成事实；继续这样写会误导执行人去重复做实现改动。
- 不采用方案：默认新增或改写 `expectation/pass/pipeline/npu_demo_lowering.py`。
- 不采用原因：用户已明确本轮不改 `expectation`；仓库规则也禁止未授权改动 `expectation/**`。
- 不采用方案：把 `gen_kernel/emit` 排除在外，只收 pass/pipeline。
- 不采用原因：用户已确认真实修复可能落在 `emitc/gen_kernel`；若计划不纳入这层，执行链会在消费合同失配时没有合法落点。
- 采用方案：收口 `pass/pipeline + gen_kernel/emit` 两层合同，采用“pipeline 顺序 + attach/outline 桥接 + standalone outline expectation + gen_kernel/emit 消费 outlined 结果”的分层验收链，不扩到 `dsl_run / execute_engine`。
- 最小公开接口：
  - `build_npu_demo_lowering_pipeline(options: dict[str, str] | None = None) -> PassManager`
  - `build_registered_pipeline("npu-demo-lowering", {"target": "npu_demo"}) -> PassManager`
  - `OutlineDeviceKernelPass`
  - `gen_kernel(op_or_func, ctx: EmitCContext) -> str`
  - `emit_c(obj, ctx: EmitCContext) -> str`

## 公开 API 设计

### `build_npu_demo_lowering_pipeline(options: dict[str, str] | None = None) -> PassManager`

- 公开入口：`kernel_gen.passes.pipeline.build_npu_demo_lowering_pipeline`
- 参数顺序：`options`
- 参数类型：`dict[str, str] | None`
- 返回值：`PassManager`
- 合同要点：
  - `target="npu_demo"` 时固定构造：
    - `inline`
    - `decompass`
    - `lower-nn`
    - `symbol-loop-hoist`
    - `attach-arch-information`
    - `outline-device-kernel`
  - 本计划不改该 API 的参数面和 pass 顺序。

```python
from kernel_gen.passes.pipeline import build_npu_demo_lowering_pipeline

pm = build_npu_demo_lowering_pipeline({"target": "npu_demo"})
module = pm.run(module)
```

### `build_registered_pipeline("npu-demo-lowering", {"target": "npu_demo"}) -> PassManager`

- 公开入口：`kernel_gen.passes.registry.build_registered_pipeline`
- 参数顺序：`name`、`options`
- 参数类型：`str`、`dict[str, str]`
- 返回值：`PassManager`
- 合同要点：
  - registry 名称固定为 `npu-demo-lowering`
  - registry 构造得到的顺序必须与 builder 一致

```python
from kernel_gen.passes.registry import build_registered_pipeline

pm = build_registered_pipeline("npu-demo-lowering", {"target": "npu_demo"})
module = pm.run(module)
```

### `OutlineDeviceKernelPass`

- 公开入口：`kernel_gen.passes.outline_device_kernel.OutlineDeviceKernelPass`
- 合同要点：
  - standalone 用法保持不变
  - `npu-demo-lowering` 的最后一段直接复用该 pass 的公开语义，不新增 pipeline 私有 outline 变体

```python
from kernel_gen.passes.outline_device_kernel import OutlineDeviceKernelPass

module = OutlineDeviceKernelPass().run(module)
```

### `gen_kernel(op_or_func, ctx: EmitCContext) -> str`

- 公开入口：`kernel_gen.dsl.gen_kernel.gen_kernel`
- 参数顺序：`op_or_func`、`ctx`
- 参数类型：`object`、`EmitCContext`
- 返回值：`str`
- 合同要点：
  - 当前公开输入域保持不变；本专题只收 `outlined-output compatibility`，不收窄既有 plain module / 受控 launch module 输入合同。
  - 若输入为 `outline-device-kernel` 产出的 wrapper/body 结果，必须能直接消费。
  - 本计划不改该 API 的参数面，只收其与 outlined 结果的兼容合同。

```python
from kernel_gen.dsl.gen_kernel import EmitCContext, gen_kernel

source = gen_kernel(module, EmitCContext(target="npu_demo"))
```

### `emit_c(obj, ctx: EmitCContext) -> str`

- 公开入口：`kernel_gen.dsl.gen_kernel.emit.emit_c`
- 参数顺序：`obj`、`ctx`
- 参数类型：`object`、`EmitCContext`
- 返回值：`str`
- 合同要点：
  - 当前公开输入域保持不变；本专题只收 `outlined-output compatibility`，不收窄既有 plain module / node-level emit 输入合同。
  - `target="npu_demo"` 时，若输入为 outlined wrapper/body 结果，节点级 / 模块级 emit 与 `gen_kernel(...)` 的消费合同必须一致。
  - 本计划不改该 API 的参数面，只收其对 outlined 结果和 `npu_demo` target-specific emit 的兼容边界。

```python
from kernel_gen.dsl.gen_kernel import EmitCContext
from kernel_gen.dsl.gen_kernel.emit import emit_c

source = emit_c(module, EmitCContext(target="npu_demo"))
```

## 完成态定义

- [`spec/pass/pipeline/npu_demo_lowering.md`](../../../../../../../spec/pass/pipeline/npu_demo_lowering.md) 明确写清：`outline-device-kernel` 已是 `npu-demo-lowering` 的固定最后一段。
- [`spec/pass/attach_arch_information.md`](../../../../../../../spec/pass/attach_arch_information.md) 与 [`spec/pass/outline_device_kernel.md`](../../../../../../../spec/pass/outline_device_kernel.md) 明确写清：pipeline 输入域与 standalone outline 输入域不是同一层合同。
- [`spec/dsl/gen_kernel/gen_kernel.md`](../../../../../../../spec/dsl/gen_kernel/gen_kernel.md) 与 [`spec/dsl/gen_kernel/emit.md`](../../../../../../../spec/dsl/gen_kernel/emit.md) 明确写清：本专题只收 `outlined-output compatibility`，不收窄 `gen_kernel/emit` 既有公开输入域，也不让其承担重新定义 pipeline 顺序的职责。
- [`test/pass/test_pipeline_npu_demo_lowering.py`](../../../../../../../test/pass/test_pipeline_npu_demo_lowering.py)、[`test/pass/test_attach_arch_information.py`](../../../../../../../test/pass/test_attach_arch_information.py) 与 [`test/pass/outline_device_kernel/test_outline_device_kernel.py`](../../../../../../../test/pass/outline_device_kernel/test_outline_device_kernel.py) 一起收出 bridge 证明点或分层推断说明：
  - pipeline 固定顺序
  - attach -> outline 桥接边界
  - standalone outline 终态与失败路径
- [`test/dsl/gen_kernel/test_gen_kernel.py`](../../../../../../../test/dsl/gen_kernel/test_gen_kernel.py) 机械锁定 outlined module 可被 `gen_kernel(...)` 直接消费。
- [`test/dsl/gen_kernel/emit/test_emit.py`](../../../../../../../test/dsl/gen_kernel/emit/test_emit.py) 保持 plain module / node-level emit 合同；若正文宣称 `emit_c(...)` 直接兼容 outlined module，则本轮必须补一条对应 case。
- 终验时运行 `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 -m expectation.pass.outline_device_kernel`，并明确记录：这是 standalone outline 终端语义验收，不是 pipeline 黑盒 expectation。

## 验收设计

- 验收资产：
  - [`test/pass/test_pipeline_npu_demo_lowering.py`](../../../../../../../test/pass/test_pipeline_npu_demo_lowering.py)
  - [`test/pass/test_attach_arch_information.py`](../../../../../../../test/pass/test_attach_arch_information.py)
  - [`test/pass/outline_device_kernel/test_outline_device_kernel.py`](../../../../../../../test/pass/outline_device_kernel/test_outline_device_kernel.py)
  - [`test/dsl/gen_kernel/test_gen_kernel.py`](../../../../../../../test/dsl/gen_kernel/test_gen_kernel.py)
  - [`test/dsl/gen_kernel/emit/test_emit.py`](../../../../../../../test/dsl/gen_kernel/emit/test_emit.py)
  - `expectation/pass/outline_device_kernel`
- 输入样例：
  - 通过 `build_npu_demo_lowering_pipeline({"target": "npu_demo"})` 构造并运行 pipeline
  - 通过 standalone `OutlineDeviceKernelPass()` 运行 pass
  - 通过 `gen_kernel(module, EmitCContext(target="npu_demo"))` 与 `emit_c(module, EmitCContext(target="npu_demo"))` 直接消费 outlined 结果
- 锁定输出：
  - pipeline 顺序中最后一段必须是 `outline-device-kernel`
  - attach 阶段负责把 pipeline 输入收成可进入 outline 的函数形状；本轮需在 pytest 中补一个明确 bridge case，或在 spec 中明确该层仅作分层推断
  - standalone outline expectation 继续只锁 pass 自身语义
  - `gen_kernel(...)` 必须能直接消费 outlined wrapper/body 结果
  - 若正文继续把 `emit_c(...)` 纳入这条兼容链，则本轮必须补一条 outlined-module `emit_c(...)` 直接验证
- 必过命令：
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/pass/test_pipeline_npu_demo_lowering.py test/pass/test_attach_arch_information.py test/pass/outline_device_kernel/test_outline_device_kernel.py test/dsl/gen_kernel/test_gen_kernel.py test/dsl/gen_kernel/emit/test_emit.py`
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 -m expectation.pass.outline_device_kernel`
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/pass/test_pass_registry.py`
- 补充要求：
  - `Diff 反推测试` 必须单列，不能拿 expectation 代替相关 pytest。
  - 本计划不修改 `expectation`；若执行中判断必须新增 pipeline expectation，必须停下并重新向用户确认。
  - [`test/tools/test_dsl_run.py`](../../../../../../../test/tools/test_dsl_run.py) 与 [`test/test_main_npu_demo_pipeline.py`](../../../../../../../test/test_main_npu_demo_pipeline.py) 只作下游见证，不列为本轮必过。

## 阶段拆分

### S1：npu-demo-lowering / attach-arch-information / outline-device-kernel / gen_kernel-emit 合同分层收口

#### 阶段目标

- 收口 `npu-demo-lowering`、`attach-arch-information`、`outline-device-kernel`、`gen_kernel/emit` 四层公开合同、相关 pytest 与 standalone expectation 验收说明，并在发现真实代码口径不一致时，只在 pass/pipeline 与 `kernel_gen/dsl/gen_kernel/**` 直接关联模块内做最小必要修正，最终跑通相关 pytest 与 expectation。

#### 非目标

- 不改 `expectation/**`
- 不改 `dsl_run`、`execute_engine`
- 不扩到 `default-lowering`
- 不新增第二套 outline 语义

#### 目标 spec / API

- [`spec/pass/pipeline/npu_demo_lowering.md`](../../../../../../../spec/pass/pipeline/npu_demo_lowering.md)
- [`spec/pass/attach_arch_information.md`](../../../../../../../spec/pass/attach_arch_information.md)
- [`spec/pass/outline_device_kernel.md`](../../../../../../../spec/pass/outline_device_kernel.md)
- [`spec/dsl/gen_kernel/gen_kernel.md`](../../../../../../../spec/dsl/gen_kernel/gen_kernel.md)
- [`spec/dsl/gen_kernel/emit.md`](../../../../../../../spec/dsl/gen_kernel/emit.md)
- `公开 API：build_npu_demo_lowering_pipeline(options: dict[str, str] | None = None) -> PassManager`
- `公开 API：build_registered_pipeline("npu-demo-lowering", {"target": "npu_demo"}) -> PassManager`
- `公开 API：OutlineDeviceKernelPass`
- `公开 API：gen_kernel(op_or_func, ctx: EmitCContext) -> str`
- `公开 API：emit_c(obj, ctx: EmitCContext) -> str`

#### 目标模块范围

- `kernel_gen/passes/pipeline/**`
- `kernel_gen/passes/attach_arch_information.py`
- `kernel_gen/passes/outline_device_kernel.py`
- `kernel_gen/passes/registry.py`
- `kernel_gen/dsl/gen_kernel/**`
- `spec/pass/pipeline/npu_demo_lowering.md`
- `spec/pass/attach_arch_information.md`
- `spec/pass/outline_device_kernel.md`
- `spec/dsl/gen_kernel/**`
- `test/pass/test_pipeline_npu_demo_lowering.py`
- `test/pass/test_attach_arch_information.py`
- `test/pass/outline_device_kernel/test_outline_device_kernel.py`
- `test/dsl/gen_kernel/**`

#### 禁止修改面 / 合同真源

- `禁止修改面：expectation/**；dsl_run/**；execute_engine/**；default-lowering 相关实现与 spec`
- `合同真源：spec/pass/pipeline/npu_demo_lowering.md > test/pass/test_pipeline_npu_demo_lowering.py；spec/pass/attach_arch_information.md + spec/pass/outline_device_kernel.md > test/pass/test_attach_arch_information.py + test/pass/outline_device_kernel/test_outline_device_kernel.py；spec/dsl/gen_kernel/gen_kernel.md + spec/dsl/gen_kernel/emit.md > test/dsl/gen_kernel/test_gen_kernel.py + test/dsl/gen_kernel/emit/test_emit.py；expectation/pass/outline_device_kernel 只作为 standalone pass 终端语义见证`

#### 最小功能闭环

- `npu-demo-lowering` 已包含 `outline-device-kernel` 的事实在 spec 中写实。
- `attach` 与 `outline` 的职责边界在 spec 和 pytest 中写清。
- `attach -> outline` 若当前资产不能直接证明，必须在 pytest 中补一条最小 bridge case，或把正文表述降级成分层推断，不能继续写成机械锁定。
- `gen_kernel(...)` 消费 outlined 结果的边界在 spec 和 pytest 中写清。
- 若正文宣称 `emit_c(...)` 直接兼容 outlined module，本轮必须在 `test/dsl/gen_kernel/emit/test_emit.py` 补对应直接验证。
- 终验 expectation 采用现有 standalone `outline_device_kernel` 目录入口，不新增 pipeline expectation。
- 若实现与上述合同存在差异，只允许在 `pipeline / attach / outline / registry / kernel_gen.dsl.gen_kernel` 直接关联模块内做最小必要修正。

#### 执行步骤

1. 先核对并收口 `npu-demo-lowering` 的 pass 顺序、公开 builder / registry 合同和相关 spec / pytest。
2. 再收 `attach-arch-information -> outline-device-kernel` 的桥接边界；若当前 pytest 只能分层证明，补一条最小 bridge case 或把正文降级成分层推断。
3. 在上游输出稳定后，再收 `gen_kernel / emit` 对 outlined 结果的兼容合同；保持既有 plain module / 受控 launch module 输入域不收窄。
4. 最后统一跑 `test_pass_registry.py`、相关 pass / dsl pytest 与 standalone expectation，确认注册入口、源码发射和终端语义一起闭环。

#### 预期示例代码

```python
from kernel_gen.passes.pipeline import build_npu_demo_lowering_pipeline

pm = build_npu_demo_lowering_pipeline({"target": "npu_demo"})
module = pm.run(module)
```

#### 预期输出

```text
pass order = inline -> decompass -> lower-nn -> symbol-loop-hoist -> attach-arch-information -> outline-device-kernel
gen_kernel / emit consume the outlined wrapper+body result directly
outline expectation remains standalone and passes as terminal semantic witness
```

#### 目标验收资产

- [`spec/pass/pipeline/npu_demo_lowering.md`](../../../../../../../spec/pass/pipeline/npu_demo_lowering.md)
- [`spec/pass/attach_arch_information.md`](../../../../../../../spec/pass/attach_arch_information.md)
- [`spec/pass/outline_device_kernel.md`](../../../../../../../spec/pass/outline_device_kernel.md)
- [`spec/dsl/gen_kernel/gen_kernel.md`](../../../../../../../spec/dsl/gen_kernel/gen_kernel.md)
- [`spec/dsl/gen_kernel/emit.md`](../../../../../../../spec/dsl/gen_kernel/emit.md)
- [`test/pass/test_pipeline_npu_demo_lowering.py`](../../../../../../../test/pass/test_pipeline_npu_demo_lowering.py)
- [`test/pass/test_attach_arch_information.py`](../../../../../../../test/pass/test_attach_arch_information.py)
- [`test/pass/outline_device_kernel/test_outline_device_kernel.py`](../../../../../../../test/pass/outline_device_kernel/test_outline_device_kernel.py)
- [`test/dsl/gen_kernel/test_gen_kernel.py`](../../../../../../../test/dsl/gen_kernel/test_gen_kernel.py)
- [`test/dsl/gen_kernel/emit/test_emit.py`](../../../../../../../test/dsl/gen_kernel/emit/test_emit.py)
- `expectation/pass/outline_device_kernel`

#### 验收必过项目

- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/pass/test_pipeline_npu_demo_lowering.py test/pass/test_attach_arch_information.py test/pass/outline_device_kernel/test_outline_device_kernel.py test/dsl/gen_kernel/test_gen_kernel.py test/dsl/gen_kernel/emit/test_emit.py`
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 -m expectation.pass.outline_device_kernel`
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/pass/test_pass_registry.py`
- `补充要求：执行人与审查人必须按实际 diff 反推补跑相关 pytest；expectation 只算合同验收，不替代 diff 反推测试。`

#### 任务新建建议

- `任务类型：spec`
- `默认链路：spec -> build -> review -> merge`
- `任务目标：收口 npu-demo-lowering / attach-arch-information / outline-device-kernel / gen_kernel-emit 的分层合同、pytest 与 standalone expectation 验收链，并跑通相关 pytest 与 expectation。`
- `记录文件：agents/codex-multi-agents/log/task_records/2026/17/20260426-npu-pipeline-outline-s1.md`

## 待确认项

- 当前无额外待确认项。
- 若后续要新增 `expectation/pass/pipeline/npu_demo_lowering.py` 这类 pipeline expectation，必须重新向用户确认。

## 用户确认与协同约束

- 用户确认状态：`已确认`
- 已确认事项：
  - `本轮不改 expectation`
  - `本轮不扩到 dsl_run / execute_engine`
  - `计划主题应按 pass/pipeline + gen_kernel/emit 合同层收口`
- 未确认事项：`无`
- 留痕方式：`本轮通过当前线程内 3 条 sub-agent 复评回执留痕；对应 agent id 为 019dc9b3-9a4f-7fe3-ba8f-d59db0f0a276、019dc9b3-9a85-7170-ab90-ad136dfb3243、019dc9b3-9ab3-7d52-8f6b-948b3864781f。`
- 讨论对象 1：`Avicenna / 实现关系审阅 / 结论：outline-device-kernel 已在 npu-demo-lowering 中，本题应定义为“合同/验收链收口”，不是新增实现；S1 单阶段可行，但 attach->outline 与 emit->outlined 兼容需补桥接证明或降级为分层推断。`
- 讨论对象 2：`Anscombe / expectation 风险审阅 / 结论：standalone expectation 不应冒充 pipeline 第一真源；test/tools/test_dsl_run.py 与 test/test_main_npu_demo_pipeline.py 只作下游见证、非本轮必过。`
- 讨论对象 3：`Sartre / 依赖与任务拆分审阅 / 结论：S1 保持单阶段合理，但必须写清执行步骤顺序，并把 test_pass_registry.py 升为本轮常驻验收。`
- 处理要求：`凡是争议、冲突或不确定事项，一律待用户确认；在架构复评完成前，不创建任务、不通知管理员推进。`

## 参考资料

- [`agents/standard/计划书标准.md`](../../../../../../../agents/standard/计划书标准.md)
- [`spec/pass/pipeline/npu_demo_lowering.md`](../../../../../../../spec/pass/pipeline/npu_demo_lowering.md)
- [`spec/pass/attach_arch_information.md`](../../../../../../../spec/pass/attach_arch_information.md)
- [`spec/pass/outline_device_kernel.md`](../../../../../../../spec/pass/outline_device_kernel.md)
- [`spec/dsl/gen_kernel/gen_kernel.md`](../../../../../../../spec/dsl/gen_kernel/gen_kernel.md)
- [`spec/dsl/gen_kernel/emit.md`](../../../../../../../spec/dsl/gen_kernel/emit.md)
- [`test/pass/test_pipeline_npu_demo_lowering.py`](../../../../../../../test/pass/test_pipeline_npu_demo_lowering.py)
- [`test/pass/test_attach_arch_information.py`](../../../../../../../test/pass/test_attach_arch_information.py)
- [`test/pass/outline_device_kernel/test_outline_device_kernel.py`](../../../../../../../test/pass/outline_device_kernel/test_outline_device_kernel.py)
- [`test/dsl/gen_kernel/test_gen_kernel.py`](../../../../../../../test/dsl/gen_kernel/test_gen_kernel.py)
- [`test/dsl/gen_kernel/emit/test_emit.py`](../../../../../../../test/dsl/gen_kernel/emit/test_emit.py)
- `expectation/pass/outline_device_kernel`
