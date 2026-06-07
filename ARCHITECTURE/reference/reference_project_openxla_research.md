# OpenXLA / XLA 调研与本仓可借鉴点

## 功能简介

- 调研 OpenXLA / XLA 的 HLO pass 组织、HloPassPipeline、HloPassFix、invariant checker、cleanup 放置和 target late lowering。
- 区分 OpenXLA 的整套 ML compiler 栈和本仓当前 DSL / IR / backend demo 边界，避免把外部系统能力写成本仓当前完成态。
- 为后续 pass manager、pipeline、canonicalize、memory 和 target lowering 计划提供长期参考。

## 执行摘要

1. OpenXLA / XLA 的核心参考价值是 pass pipeline 的治理方式：pass、pipeline、invariant checker、metadata、dump 和 target backend 边界各自有明确职责。
2. HLO pass 先在硬件无关层面做代数化简、constant folding、DCE、reshape mover、rematerialization 等优化，再在 GPU / CPU / TPU 等 backend 中加入 target-specific pass。
3. `HloPassPipeline` 的 invariant checker 在 pipeline start 和 pass changed 后运行，能把“每个 pass 后 IR 仍合法”做成流程约束。
4. `HloPassFix` 表达 fixed-point 迭代，带迭代上限和 cycle / hash 观察，适合本仓后续处理 canonicalize / cleanup 重复收敛问题。
5. GPU 文档和源码显示 target late lowering 不应混进高层语义 pass：layout、fusion、library call rewrite、emitter / thunk packaging 属于后端阶段。
6. 对本仓最直接的迁移口径是：先把 pipeline 分层、cleanup barrier、合法性检查和阶段记录做实，再考虑具体优化规则，不反过来堆单个大 pass。

## 文档信息

- `文档`：[`ARCHITECTURE/reference/reference_project_openxla_research.md`](reference_project_openxla_research.md)
- `spec`：不适用；本文为外部参考项目调研文档，不对应本仓 `spec` 文件。
- `外部参考`：见下文“外部证据源”，只使用 OpenXLA 官方文档和官方 GitHub 源码。
- `本仓影响`：不修改公开 API、`kernel_gen/`、`spec/`、`test/` 或 `expectation/`。

## 使用示例

- 讨论本仓 pass pipeline 是否需要阶段合法性检查时，先读“可借鉴方法 / invariant checker”。
- 讨论 repeated canonicalize、DCE 或 cleanup 放置时，先读“HloPassFix 与 fixed-point 收敛”。
- 讨论 npu_demo / cuda_sm86 后端 pass 是否应该提前侵入高层 IR 时，先读“target late lowering”。

## 调研对象与证据边界

本文只读查看官方文档和官方 GitHub 源码，不下载、不 clone、不编译外部项目。OpenXLA `main` 会持续变化，本文只沉淀能力类别和设计边界，不固定 pass 顺序、性能数字或某个 backend 的内部实现为本仓合同。

### 外部证据源

- OpenXLA XLA architecture：<https://openxla.org/xla/architecture>
- OpenXLA HLO passes：<https://openxla.org/xla/hlo_passes>
- OpenXLA XLA GPU architecture：<https://openxla.org/xla/gpu_architecture>
- OpenXLA HLO to thunks：<https://openxla.org/xla/hlo_to_thunks>
- OpenXLA XLA GPU emitters：<https://openxla.org/xla/emitters>
- OpenXLA 官方仓库 README：<https://github.com/openxla/xla>
- `HloPassPipeline` 接口：<https://github.com/openxla/xla/blob/main/xla/hlo/pass/hlo_pass_pipeline.h>
- `HloPassPipeline` 实现：<https://github.com/openxla/xla/blob/main/xla/hlo/pass/hlo_pass_pipeline.cc>
- `HloPassFix` fixed-point 模板：<https://github.com/openxla/xla/blob/main/xla/hlo/pass/hlo_pass_fix.h>
- `HloVerifier`：<https://github.com/openxla/xla/blob/main/xla/service/hlo_verifier.h>
- GPU compiler pipeline 源码：<https://github.com/openxla/xla/blob/main/xla/service/gpu/gpu_compiler.cc>

### 本仓对照点

- [`kernel_gen/passes/pass_manager.py`](../../kernel_gen/passes/pass_manager.py)
- [`kernel_gen/pipeline/npu_demo_lowering.py`](../../kernel_gen/pipeline/npu_demo_lowering.py)
- [`spec/pass/pipeline/npu_demo_lowering.md`](../../spec/pass/pipeline/npu_demo_lowering.md)
- [`spec/pass/pass_manager.md`](../../spec/pass/pass_manager.md)
- [`kernel_gen/passes/memory/`](../../kernel_gen/passes/memory)
- [`kernel_gen/passes/kernel/`](../../kernel_gen/passes/kernel)
- [`kernel_gen/dsl/gen_kernel/`](../../kernel_gen/dsl/gen_kernel)

### 证据核对矩阵

| 文档结论 | 官方来源 | 证据边界 |
| --- | --- | --- |
| XLA 是面向 GPUs / CPUs / ML accelerators 的 ML compiler | XLA architecture、官方 README | 只说明外部项目定位；本仓仍是自有 DSL / IR / backend demo |
| HLO pass 包括硬件无关优化和 backend-specific pass | HLO passes 文档 | pass 名称只作能力类别参考，不写成本仓验收顺序 |
| HloPassPipeline 支持 pass 序列、invariant checker、pass metadata 和 dump 条件 | `hlo_pass_pipeline.h` / `.cc` | 可借鉴 pipeline 结构；不引入 XLA API |
| HloPassFix 以 fixed-point 方式重复运行 pass 并带迭代上限 | `hlo_pass_fix.h` | 只作为 cleanup 收敛样本；本仓若采用需另写计划 |
| HloVerifier 是 HLO graph invariant 检查器 | `hlo_verifier.h`、HLO passes 文档 | 只借鉴 pass 后合法性检查概念 |
| GPU lowering 有 layout、emitter、thunk / executable packaging 等后端阶段 | GPU architecture、HLO to thunks、GPU emitters、`gpu_compiler.cc` | 只借鉴 target late lowering 边界，不引入 OpenXLA runtime |

## 项目是什么 / 不是什么

| 问题 | 结论 | 本仓解释 |
| --- | --- | --- |
| OpenXLA / XLA 是不是整套 ML compiler？ | 是 | 它从 StableHLO / HLO 编译到多类硬件后端，不是单 kernel demo |
| HLO pass 是不是单个统一优化器？ | 不是 | 官方文档列出多个硬件无关和 backend-specific pass 类别 |
| invariant checker 是不是普通优化 pass？ | 不是 | 它用于验证 pass 前后合法性，必须不改变图 |
| fixed-point 是不是所有 pass 默认行为？ | 不是 | `HloPassFix` 是显式模板，适合特定需要重复收敛的 pass |
| 是否适合本仓直接接入 XLA？ | 当前不适合 | 会改变依赖、IR、runtime 和后端边界；本文只提炼方法 |

## 可借鉴方法

### 1. Pipeline 不是 pass list，而是治理边界

`HloPassPipeline` 不只保存 pass 列表。源码里可以看到：

- `AddPass(...)` 只在 Run 前允许加入 pass。
- `AddInvariantChecker(...)` 把合法性检查挂到 pipeline。
- `RunPassesInternal(...)` 在 pipeline start、每个 pass、pipeline end 记录 metadata。
- pass changed 时再跑 invariant checker。
- pass dump 受 debug option 控制，并与 pass changed 绑定。

本仓后续 pass manager 不宜只维护“字符串 -> pass”的调用表。更稳的方向是把阶段名、pass marker、合法性检查、changed 结果、dump 文件和 error mapping 作为同一个 pipeline 运行记录来维护。

### 2. invariant checker 应成为阶段门，而不是 review 口头约定

OpenXLA 的 invariant checker 规则很硬：checker 不应改变图，失败要附带 pass 名上下文。对本仓有两个迁移点：

- `npu-demo-lowering` 关键阶段后可以逐步加入结构检查，例如 launch/body/alloc/dma/memory op 的阶段合法性。
- review 不能只看最终 IR 是否能跑；需要知道哪个阶段首次破坏了合法性。

### 3. HloPassFix 提供 cleanup / canonicalize 的固定点模型

本仓已有 canonicalize、CSE、memory cleanup、kernel decompose 等重复收敛需求。OpenXLA 的 fixed-point 模型启发：

- 只对需要重复收敛的 pass 使用 fixed-point，不让所有 pass 默默循环。
- 设定 iteration limit，并在达到上限时形成可诊断记录。
- 记录 changed computation 或 changed flag，避免无法解释的静默变化。

### 4. Cleanup placement 要和 target late lowering 分开

OpenXLA HLO passes 文档把硬件无关优化、legalization、backend-specific pass 分层。GPU 文档又把 layout、library rewrite、emitter 和 thunk 包装放到更靠后的 backend 阶段。

本仓后续应避免：

- 在高层 `npu_demo_lowering` 早期就塞入后端源码策略。
- 让 memory pass 知道最终 C++ wrapper 细节。
- 把 target-specific rule 写进共享 canonicalize。

### 5. Pass metadata 和 dump 是审查材料，不是业务语义

OpenXLA pipeline 会记录 pass 名、pipeline 名、changed 等 metadata。本仓可以借鉴“每个阶段可审”的思想，但不能把某个上游 dump flag 或文件命名照搬成本仓公开合同。对于本仓，任务记录、spec、expectation 和 tracked dump 才是合同来源。

## 对本仓的迁移口径

| OpenXLA 方法 | 本仓可迁移口径 | 不改变的边界 |
| --- | --- | --- |
| HloPassPipeline | 强化 `PassManager` 的阶段名、marker、changed、dump 记录 | 不新增公开 API，除非用户确认 |
| invariant checker | 为 npu_demo / memory / kernel 阶段加只读合法性检查 | checker 不做 rewrite |
| HloPassFix | 对 canonicalize / cleanup 设计显式 fixed-point 包装 | 不让普通 pass 隐式循环 |
| 硬件无关 HLO pass | 把 algebraic / DCE / CSE / reshape 类 cleanup 留在共享层 | 不混入 target codegen 语义 |
| target late lowering | 后端源码生成、layout 和 runtime packaging 靠后收口 | 不提前污染 DSL / 高层 IR |

落地顺序建议：

1. 先补 pipeline 记录和阶段合法性检查。
2. 再把 cleanup barrier 写进 pipeline spec。
3. 最后才设计 fixed-point wrapper 或 target-specific lowering。

## 最不该直接照搬的点

- 不直接引入 OpenXLA / XLA 依赖或 StableHLO 入口。
- 不把 HLO pass 名称、debug flag、dump 文件命名写成本仓稳定合同。
- 不复制 GPU thunk / emitter / runtime packaging 到 `npu_demo`。
- 不把 XLA 的整图 compiler 假设套到本仓单 kernel / demo runner。
- 不把 backend-specific legalization 提前放进共享 DSL lowering。

## 自检清单

- 后续计划引用本文时，是否仍保持本仓公开 API 不变？
- 是否把 invariant checker 写成只读检查，而不是隐藏 rewrite？
- 是否明确 fixed-point 的 pass scope、iteration limit 和失败记录？
- 是否区分硬件无关 cleanup 与 target late lowering？
- 是否只把 OpenXLA 作为方法参考，而不是依赖、runtime 或 IR 替换方案？
- 是否避免把 OpenXLA `main` 当前 pass 顺序写成本仓稳定验收？
