# matmul dynamic acc fill canonicalization 计划书 Draft 2-R5

## 文档信息

- 计划用途：收口 matmul dynamic tile 场景中可证明无效的 `dma.fill`；`kernel-decompose` 只负责把 `kernel.matmul_fusion` 分解为 dynamic acc `kernel.matmul`，所有 fill 删除统一放到后续 `dma.fill` canonicalization 中判断。
- 当前状态：Draft 2-R5，用户已确认 DU1-A、DU2-A、DU3-B；两路最终 subagent strict review 均通过，无阻断、无最小需改项、无待确认项；`守护最好的爱莉希雅` 守护最终检验通过，允许通知管理员创建唯一计划级 execute。
- 用户确认来源：
  - 2026-06-07 用户指出动态 matmul dump 中若干 `fill` 看起来可以被规范化消除，并提到 matmul 合并与 fill 规范化相关。
  - 2026-06-07 用户确认 `bias_tile fill` 应优先扩建现有 `dma.fill` canonicalization，而不是新建 host pass 或塞进 `kernel-decompose`。
  - 2026-06-07 用户指出 `kernel.matmul_fusion` 合并不需要判断 fill。
  - 2026-06-07 用户裁定：“`kernel-decompose` 不做 fill 是否删除”“fill 就在规范化中看”。
  - 2026-06-07 用户确认 DU1-A：runtime tile 参数必须为正数，static/dynamic 的 acc fill 可以删。
  - 2026-06-07 用户确认 DU2-A：不假设 dynamic shape `K > 0`，dynamic/dynamic 的 acc fill 暂不要求删除。
  - 2026-06-07 用户确认 DU3-B：旧 `expectation.pass.kernel_decompose` initial fill 删除 case 作为历史只读来源，不列为本计划必过；execute 不修改 `expectation/`。
- 计划文件位置：`ARCHITECTURE/plan/matmul_dynamic_acc_fill_canonicalization.md`。

## 功能简介

- 收窄 `kernel-decompose`：只做 `kernel.matmul_fusion -> kernel.matmul(..., dynamic_acc)`，不删除 `dma.fill`。
- 扩展 `dma.fill` canonicalization：在 dynamic acc matmul 已显式化后，删除可证明无效的 acc initial fill。
- 扩展 `dma.fill` canonicalization：删除受控 `scf.if` 分支内 full overwrite before read 的 bias staging fill。
- 补齐 static/dynamic 与 dynamic/dynamic matmul pipeline dump 测试，避免只在 static/static case 覆盖 fill 消除事实。

## API 列表

- 不新增公开 API。
- 不修改 `KernelDecomposePass(fold: bool = True)` 构造签名、`from_options(options: dict[str, str]) -> KernelDecomposePass`、`apply(ctx: Context, module: ModuleOp) -> None`。
- 不修改 `DmaFillOp(target: SSAValue | Operation, value: SSAValue | Operation)` 签名。
- 不新增 pipeline option，不修改 `build_npu_demo_lowering_pipeline(options: dict[str, str] | None = None) -> PassManager` 签名。

## 目标 spec

- `spec/pass/kernel/kernel_decompose.md`
- `spec/dialect/dma.md`
- `spec/pass/pipeline/npu_demo_lowering.md`

## 目标功能实现

- `kernel_gen/passes/kernel/kernel_decompose.py`
- `kernel_gen/dialect/dma/canonicalization.py`
- 默认不修改 `kernel_gen/pipeline/npu_demo_lowering.py` 的 pass 顺序。

## 目标测试

- `test/passes/kernel/test_kernel_decompose.py`
- `test/dialect/dma/test_canonicalization.py`
- `test/passes/pipeline/test_npu_demo_lowering.py`
- `test/kernel/test_matmul_symbolic_memory_genkernel.py`

## 禁止修改面

- 本计划 execute 不修改、新建、删除或移动 `expectation/`；旧 `expectation.pass.kernel_decompose` initial fill 删除 case 仅作为历史只读来源，不列为本计划必过合同验收。
- 不修改 `.skills/`。
- 不修改 `TODO.md`、`DONE.md`、`agents-lists.md` 或无关 worktree 状态；允许按本计划指定记录文件写执行、review、入档验收与复验记录。
- 不改公开 API、registry pass name、pipeline name、pipeline option 或稳定错误文本；若执行发现必须改变，暂停并交用户确认。
- 不把本计划扩展为通用 CFG DSE、通用 alias analysis 或 matmul demo 重写计划。

## 当前基线

- `DmaFillOp` 已挂 `DmaFillCanonicalizationTrait`，由 xDSL `CanonicalizePass` 调用 `DmaDeadFillCanonicalizationPattern`。
- 当前 `dma.fill` dead-fill 规则只线性扫描同 block 后续 sibling：
  - 遇到 `dma.fill`、安全 `dma.copy`、标量 `dma.broadcast`、full `dma.deslice` 等完整覆盖 writer 时删除前序 fill。
  - 遇到 region op 直接保守阻断。
- 因此 input tile 的 `fill -> full deslice` 已能在 `CanonicalizePass` 消除；但 `fill -> scf.if { full deslice -> broadcast(alias) }` 的 bias staging 形态会被 region op 阻断。
- `KernelDecomposePass` 当前已有 `initial_zero_fill_for_fusion(...)`，会在 `kernel.matmul_fusion` 分解为 dynamic acc `kernel.matmul` 时尝试删除 loop 前 initial zero fill。
- 用户已裁定 `kernel-decompose` 不做 fill 删除；因此该删除行为需要迁出到 `dma.fill` canonicalization。
- 当前 `spec/pass/kernel/kernel_decompose.md` 和 `expectation.pass.kernel_decompose` 仍包含旧合同：`kernel-decompose` 可删除 / 应删除可证明安全的 initial `dma.fill(out, 0)`；用户已确认 DU3-B，本计划将该旧 `expectation` case 作为历史只读来源，不列为当前必过合同验收，并要求 `spec/pass/kernel/kernel_decompose.md` 在执行中更新为 `kernel-decompose` 只分解不删 fill。
- pipeline 中 `KernelDecomposePass` 后仍有 `MemoryPlanPass -> SymbolHoistPipelinePass -> CSE -> CanonicalizePass`，具备在 dynamic acc matmul 显式化后由 canonicalization 删除 acc fill 的阶段。
- pipeline 测试目前覆盖 static/static final hoist 不残留 `dma.fill`；static/dynamic 与 dynamic/dynamic 主要覆盖 alloc/free 外提和 logical reinterpret 消费，对 fill 消除缺少精确断言。

## 方案比较与选型

### 方案 A：在 demo 里手动删除 fill

- 优点：局部改动少。
- 问题：把语义证明留给调用方，不能覆盖其它 lowering 产物；容易让 correctness 依赖隐式约定。
- 结论：不采用。

### 方案 B：继续在 kernel-decompose 删除 acc fill

- 优点：当前已有实现雏形，知道 `kernel.matmul_fusion` 的 acc 语义。
- 问题：`kernel-decompose` 会混入 fill DSE 职责；用户已裁定 fill 应在规范化中看。
- 结论：不采用。

### 方案 C：所有 fill 删除统一放到 dma.fill canonicalization

- 做法：
  - `kernel-decompose` 只产出 dynamic acc `kernel.matmul`，不删除 fill。
  - input staging、bias staging 和 acc initial fill 均由 `DmaDeadFillCanonicalizationPattern` 判定删除。
  - acc fill 删除只识别分解后的 `kernel.matmul(..., dynamic_acc)`，不识别 `kernel.matmul_fusion`。
- 优点：fill 删除只有一个规范化落点；fusion 分解职责单一；复用既有 `CanonicalizePass`。
- 风险：`dma.fill` canonicalization 需要识别受控 `symbol.for + kernel.matmul(dynamic_acc)` 跨 dialect 形态，因此匹配边界必须写窄。
- 结论：采用。

## 公开行为设计

### kernel-decompose 行为

`kernel-decompose` 只做：

```mlir
"kernel.matmul_fusion"(%out, %lhs, %rhs, %acc) : (...) -> ()
```

变为：

```mlir
"kernel.matmul"(%out, %lhs, %rhs, %acc) : (...) -> ()
```

它不得删除：

```mlir
"dma.fill"(%out, %zero) : (...) -> ()
```

因此单独运行 `KernelDecomposePass` 后，合法结果是：

- `kernel.matmul_fusion` 不残留。
- dynamic acc `kernel.matmul` 出现。
- 原有 initial `dma.fill` 保留，等待后续 `CanonicalizePass` 判断。

### acc fill canonicalization

`dma.fill` canonicalization 可删除以下形态中的 `dma.fill(%acc, 0)`：

```mlir
"dma.fill"(%acc, %zero) : (...) -> ()
symbol.for %k = %start to %end step %tile_k {
  %is_acc = "symbol.ne"(%k, %start) : (...) -> i1
  "kernel.matmul"(%acc, %lhs, %rhs, %is_acc) : (...) -> ()
}
```

必须同时满足：

- `kernel.matmul` 已经是 dynamic acc 形态；不识别 `kernel.matmul_fusion`。
- `%is_acc` 为 `symbol.ne(iter, start)`，按 SSA 身份确认。
- fill 位于 loop 前同一 block，target 与 matmul out 是同一 SSA 或可追踪一跳 alias。
- fill value 是精确 0。
- fill 到 loop 之间、loop body 起点到 matmul 之间，不存在 target 或可追踪 alias 的读、写、逃逸或未知 region capture。
- loop 至少执行一次可证明。

第一阶段支持：

- `start/end/step` 全部静态整数，且 `end > start`、`step > 0`。
- DU1-A 已由用户确认，额外支持 `start/end` 是静态整数且 `end > start`，`step` 是 runtime tile 参数符号，且该符号按用户确认合同必须为正数。
- DU2-A 已由用户确认，本计划不假设 dynamic shape `K > 0`，因此不支持 dynamic end 的 acc fill 删除完成态。

### bias / staging fill canonicalization

扩展 `DmaDeadFillCanonicalizationPattern`，新增受控 `scf.if` 支持：

```mlir
"dma.fill"(%bias_tile, %zero) : (...) -> ()
%bias_row = "dma.reshape"(%bias_tile) : (...) -> (...)
scf.if %bias_present {
  "dma.deslice"(%bias_tile, %bias_region, %zero, %cur_w, %one) : (...) -> ()
  "dma.broadcast"(%bias_full, %bias_row) : (...) -> ()
}
```

允许删除 fill 的条件：

- fill target 的 root owner 是本地 `dma.alloc`。
- 后续 `scf.if` 无 results，且 then/else region 均为单 block；无 else 时按空分支处理。
- 每个分支内对 target 或一跳 alias 的所有读，必须被同分支内先出现的 full `dma.deslice` 覆盖支配。
- 没有 full overwrite 的分支不得读取 target 或 alias。
- 分支内遇到 partial write、未知 effect、nested region、target/alias 逃逸或无法识别 consumer 时保守失败。
- if 后继续按现有同 block scan 规则检查后续 op；不能因为 if 内某一分支覆盖就直接把 if 当作全路径 full overwrite。

## 用户确认项

### DU1：runtime tile 参数正数合同

- 用户确认：选择 A，`TILE_H/TILE_W/TILE_K` 等 runtime tile 参数必须为正数。
- 完成态影响：执行必须支持 `symbol.for k = 0 to static_positive_K step TILE_K` 的 acc fill 删除；`kernel-decompose` 仍不得自行删除该 fill。

### DU2：dynamic shape 正数合同

- 用户确认：选择 A，本计划不假设动态 input shape `K > 0`。
- 完成态影响：dynamic/dynamic matmul 暂不要求删除 acc fill；dynamic/dynamic pipeline 测试不得使用全局 `'"dma.fill"' not in final_hoist_text` 作为完成态，只能精确断言 input/bias staging fill 消除与 acc fill 保留口径。

### DU3：`expectation.pass.kernel_decompose` 旧合同处理

- 当前冲突：`expectation.pass.kernel_decompose` 当前包含 `remove_initial_zero_fill` 等 case，要求 `kernel-decompose` 删除 initial `dma.fill`；本计划要求 `kernel-decompose` 保留 fill，交由后续 canonicalization 删除。
- 用户确认：选择 B，把当前 `expectation.pass.kernel_decompose` 中 initial fill 删除 case 降为历史只读合同来源，不列为本计划必过合同验收。
- 完成态影响：执行必须更新 `spec/pass/kernel/kernel_decompose.md`，使当前 `spec` 不再把旧 `expectation` case 当作必过入口；execute 不修改 `expectation/`。

## 完成态定义

- `kernel-decompose` 继续输出 dynamic acc `kernel.matmul`，不生成旧 `scf.if` 双分支，并且不删除任何 `dma.fill`。
- static input + dynamic tile matmul 的 `acc` initial zero fill 可由后续 `CanonicalizePass` 删除，依赖 DU1-A 已确认的 runtime tile 参数正数合同。
- dynamic input + dynamic tile matmul 的 acc fill 不作为必须删除项，原因是 DU2-A 已确认本计划不假设 dynamic shape `K > 0`。
- `dma.fill` canonicalization 可删除 bias staging 中“if 分支内 full overwrite before read、absent 路径不读”的 dead fill。
- input tile 的 `fill -> full deslice` 删除仍由现有 canonicalization 规则覆盖，并补 pipeline 测试锁定。
- `npu-demo-lowering` pass 顺序不改变；最终 typed pre-pool IR 中不因本计划新增 `dma.alloc/free`、`kernel.matmul_fusion` 或旧双分支。

## 计划级任务

- 计划级任务目标：收窄 `kernel-decompose` 为纯 `kernel.matmul_fusion -> dynamic acc kernel.matmul` 分解，并扩展 `dma.fill` canonicalization 的 dynamic acc matmul 与受控 `scf.if` dead-fill 规则；基于 DU1-A，使 static/dynamic matmul final typed IR 中可证明无效的 acc、bias 与 input staging fill 被后续 `CanonicalizePass` 消除；基于 DU2-A，dynamic/dynamic acc fill 暂不作为必须删除项；基于 DU3-B，旧 `expectation.pass.kernel_decompose` initial fill 删除 case 只作为历史只读来源，不作为当前必过合同验收；同时保持公开 API、pipeline option 和 pass 顺序不变。
- 任务类型：`execute`。
- 固定流转：`execute -> review -> archive_acceptance / 计划书入档验收 -> merge/归档`。
- 当前下发前置：本 Draft 2-R5 已收口 DU1/DU2/DU3，已完成最终 subagent strict review 收敛与守护最终检验；允许通知管理员创建唯一计划级 execute，具体创建与分发仍由管理员执行。

| 计划任务 | 任务类型 | worktree | 记录文件 |
| --- | --- | --- | --- |
| `matmul-dynamic-acc-fill-canonicalization` | `execute` | 管理员下发的新独立 worktree | `agents/codex-multi-agents/log/task_records/2026/<week>/YYYYMMDD-matmul-dynamic-acc-fill-canonicalization.md` |

## 计划内小任务

### 通用执行字段

- 合同真源：用户已确认裁定和本计划完成态 > 已更新 `spec` > pytest 回归；旧 `expectation.pass.kernel_decompose` initial fill 删除 case 仅作为历史只读来源，不是当前必过合同。当前实现不得反向覆盖用户裁定、计划完成态或 `spec`。
- 模块范围：S1 触达目标 `spec` 与目标测试，并按 DU3-B 记录旧 `expectation` 历史只读口径；S2 触达 `kernel_gen/passes/kernel/kernel_decompose.py` 与 `test/passes/kernel/test_kernel_decompose.py`；S3/S4 触达 `kernel_gen/dialect/dma/canonicalization.py` 与 `test/dialect/dma/test_canonicalization.py`；S5 触达 `test/passes/pipeline/test_npu_demo_lowering.py` 与 `test/kernel/test_matmul_symbolic_memory_genkernel.py`，默认不改 `kernel_gen/pipeline/npu_demo_lowering.py` pass 顺序。
- 最小功能闭环：spec 明确职责边界，`kernel-decompose` 只分解 fusion 并保留 fill，`dma.fill` canonicalization 删除静态可证明 acc dead-fill、positive runtime tile step acc dead-fill 与受控 `scf.if` bias dead-fill，pipeline/source 测试证明完成态和 DU 确认口径一致；旧 `expectation.pass.kernel_decompose` initial fill 删除 case 不作为当前必过合同验收。
- 记录要求：execute 必须在计划级任务记录写执行前阅读、最小功能闭环、自检、Diff 反推自测、减法检查、DU1/DU2/DU3 用户确认来源、`expectation` 历史只读口径；review / archive_acceptance 必须记录最新同步现场、Diff 反推审查、合同验收状态和剩余风险。

### S1：补齐 spec 与失败测试基线

- 为什么做：先把 `kernel-decompose` 与 `dma.fill` canonicalization 的职责边界写清，并用测试证明当前动态场景缺口。
- 做什么：更新 `kernel_decompose`、`dma`、`npu_demo_lowering` 相关 spec；新增或调整 pytest 覆盖 acc fill、bias if dead-fill 正反例和真实 pipeline dump。
- 不做什么：不修改实现；execute 不修改 `expectation/`，只记录旧 `expectation.pass.kernel_decompose` initial fill 删除 case 为历史只读来源。
- 怎么验收：新增测试在实现前可暴露当前缺口；spec 明确所有 fill 删除都在 canonicalization 中判断。
- 卡住问谁：若执行发现需要扩大 DU1-A / DU2-A / DU3-B 已确认范围，先问用户；spec 口径冲突问架构师。

详细执行：

1. 在 `spec/pass/kernel/kernel_decompose.md` 中明确 `kernel-decompose` 不负责删除 `dma.fill`，只分解 `kernel.matmul_fusion`。
2. 在 `spec/dialect/dma.md` 中补 `dma.fill` canonicalization 的 dynamic acc matmul dead-fill 与受控 `scf.if` dead-fill 规则和反例边界。
3. 在 `spec/pass/pipeline/npu_demo_lowering.md` 中说明 pipeline 依赖 `kernel-decompose` 显式化 dynamic acc matmul，再由后续 `CanonicalizePass` 删除可证明 dead fill。
4. 按 DU3-B 处理 `expectation.pass.kernel_decompose`：在计划与 spec 中明确旧 initial fill 删除 case 为历史只读非必过，不修改、不运行该旧 case 作为本计划通过依据。
5. 在 `test/passes/kernel/test_kernel_decompose.py` 调整既有 fill 删除断言：`kernel-decompose` 后应保留 fill，但 fusion 已变为 dynamic acc matmul。
6. 在 `test/dialect/dma/test_canonicalization.py` 增加 acc dynamic matmul loop、bias if 正反例。
7. 在 `test/passes/pipeline/test_npu_demo_lowering.py` 增加 static/dynamic matmul final hoist 精确 fill 断言，并覆盖 DU1-A positive runtime tile step acc fill 删除正例。

验收：

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/passes/kernel/test_kernel_decompose.py -k "fill or dynamic"
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/dialect/dma/test_canonicalization.py -k "fill"
```

合同验收：

- `expectation.pass.kernel_decompose` 的 initial fill 删除 case 只作为历史只读来源记录，不列为本计划必过合同验收。

### S2：收窄 kernel-decompose fill 职责

- 为什么做：用户裁定 `kernel-decompose` 不做 fill 删除；该 pass 应只负责 matmul fusion 分解。
- 做什么：移除或停用 `KernelDecomposePass` 中 initial zero fill 删除路径，保留 fusion -> dynamic acc matmul 结果。
- 不做什么：不在 `kernel-decompose` 中判断 trip count、zero fill 或 out alias live-read；不删除任何 `dma.fill`。
- 怎么验收：`kernel_decompose` 单测证明 fill 保留、fusion 消失、dynamic acc matmul 生成；旧 fill 删除用例迁到 DMA canonicalization 测试。
- 卡住问谁：若旧 `expectation` 与当前 `spec` 口径冲突仍阻断流程，按 DU3-B 记录为历史只读来源并回用户或架构师确认是否需要另开合同资产处理；不修改 `expectation/`。

详细执行：

1. 删除 `match_and_rewrite(...)` 中 `initial_zero_fill_for_fusion(...)` 调用，或使其不再参与 rewrite。
2. 清理 `initial_zero_fill_for_fusion(...)`、`erase_fill_with_verify_rollback(...)`、trip count 与 zero-fill 专属 helper；不保留无调用死代码。
3. 更新文件级说明与函数注释，删除“删除 initial dma.fill”描述。
4. 更新 `test/passes/kernel/test_kernel_decompose.py`：
   - 原“删除 fill”正例改为“保留 fill + 生成 dynamic acc matmul”。
   - rollback 相关用例若只服务 fill 删除，应删除或迁移到 canonicalization。
   - 保留“不生成 scf.if、不残留 fusion”的断言。

验收：

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/passes/kernel/test_kernel_decompose.py
```

合同验收：

- 本小任务不修改 `expectation/`。

### S3：扩展 dma.fill canonicalization 的 dynamic acc matmul dead-fill

- 为什么做：acc fill 删除应作为 fill 规范化发生在 dynamic acc matmul 已显式化之后。
- 做什么：在 `DmaDeadFillCanonicalizationPattern` 中识别受控 `symbol.for + kernel.matmul(dynamic_acc)`，删除 loop 前 initial zero fill。
- 不做什么：不识别 `kernel.matmul_fusion`；不做通用 kernel DSE；不支持 dynamic `K > 0` 推理，原因是 DU2-A 已确认本计划不假设 dynamic shape 正数。
- 怎么验收：DMA canonicalization 单测证明静态 positive trip count 的 acc fill 可删，并证明 static end + positive runtime tile symbol step 的 acc fill 可删；反例必须保留 fill。
- 卡住问谁：若要扩大到 DU2-A 之外的 dynamic shape 正数合同，先问用户；跨 dialect canonicalization 边界问架构师。

详细执行：

1. 在 `_DmaCanonicalizationRules` 中新增当前文件内 helper，识别 `symbol.for` 单 block body。
2. 识别 loop body 中首个 target/alias 数据事件必须是 dynamic acc `kernel.matmul`，且 out 为 fill target 或可追踪一跳 alias。
3. 识别 dynamic acc operand owner 为 `symbol.ne`，operands 为 `(iter_arg, loop.start)`；只接受当前 lowering 生成的顺序。
4. 复用或迁入 start/end/step 证明：
   - 允许 start/end/step 全部静态，且 `end > start`、`step > 0`。
   - 基于 DU1-A，允许 start/end 静态且 `end > start`，step 为 positive runtime tile symbol。
   - 基于 DU2-A，不支持 dynamic end。
5. 扫描 fill 到 loop 之间、loop body 到 matmul 之间的 target/alias 使用；发现读、写、逃逸、unknown effect 或 nested region 则失败。
6. 在 `DmaDeadFillCanonicalizationPattern.match_and_rewrite(...)` 中，把该规则作为 `has_later_full_overwrite(...)` 的补充删除条件。

必须新增或调整的测试用例：

- `test_dma_fill_canonicalization_removes_zero_fill_before_static_trip_dynamic_acc_matmul`：`start/end/step` 全静态正 trip count，`symbol.ne(iter,start)`，`kernel.matmul(dynamic_acc)` 首个读取事件；删除 zero fill。
- `test_dma_fill_canonicalization_keeps_fill_before_matmul_fusion`：后续仍是 `kernel.matmul_fusion`，canonicalization 不识别 fusion；保留 fill。
- `test_dma_fill_canonicalization_keeps_nonzero_fill_before_dynamic_acc_matmul`：fill value 非零；保留 fill。
- `test_dma_fill_canonicalization_keeps_fill_for_noncanonical_acc_operand`：dynamic acc 不是 `symbol.ne(iter,start)` 或 operand 顺序不符合当前 lowering 合同；保留 fill。
- `test_dma_fill_canonicalization_keeps_fill_for_zero_or_unknown_trip_count`：`end <= start`、`step <= 0` 或 dynamic end；保留 fill。
- `test_dma_fill_canonicalization_keeps_fill_when_target_read_before_loop`：fill 到 loop 之间读 target 或一跳 alias；保留 fill。
- `test_dma_fill_canonicalization_keeps_fill_when_body_reads_before_matmul`：loop body 起点到 matmul 前读 target 或一跳 alias；保留 fill。
- `test_dma_fill_canonicalization_keeps_fill_when_target_escapes_before_matmul`：target/alias 传入未知 effect op、nested region 或 func.call；保留 fill。
- 增加 `test_dma_fill_canonicalization_removes_zero_fill_with_positive_symbol_step`，证明 DU1-A 下 positive runtime tile symbol step 可删。

验收：

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/dialect/dma/test_canonicalization.py -k "fill or matmul"
```

合同验收：

- 本小任务不修改 `expectation/`。
- 该验收必须覆盖 positive runtime tile symbol step 正例；dynamic end 仍按 DU2-A 作为反例保留 fill。

### S4：扩展 dma.fill canonicalization 的受控 scf.if dead-fill

- 为什么做：bias staging fill 是普通 DMA dead-fill 问题，应该复用 `DmaDeadFillCanonicalizationPattern`。
- 做什么：在 `kernel_gen/dialect/dma/canonicalization.py` 内扩展 private alloc fill live-read 判定，允许 `scf.if` 分支内 full overwrite before read。
- 不做什么：不做通用 CFG DSE；不跨 block、跨 loop 或跨未知 region 推理；不处理 target 非本地 alloc 的函数参数 fill。
- 怎么验收：DMA canonicalization 正例删 fill，反例保留 fill。
- 卡住问谁：如果 bias 形态需要支持多级 alias 或复杂 control-flow，先问用户是否扩大计划。

详细执行：

1. 在 `_DmaCanonicalizationRules` 中新增当前文件内 helper，判断 fill target 是否来自本地 `dma.alloc`。
2. 新增 branch scan helper：
   - 单 block region。
   - 初始 `covered=False`。
   - full `dma.deslice(target, ...)` 后置 `covered=True`。
   - target 或一跳 alias read 仅在 `covered=True` 后允许。
   - partial write、unknown effect、nested region、target escape 失败。
3. 新增 `is_safe_scf_if_for_dead_fill(...)`，只接受 `scf.if` 无 results、单块分支、无 else 或空 else 可按不读处理。
4. 修改 `DmaDeadFillCanonicalizationPattern.match_and_rewrite(...)`：
   - 先保留现有 `has_later_full_overwrite(...)`。
   - 再尝试 private alloc no-live-read / safe-if 规则。
5. 保留现有同 block sibling full overwrite 规则，不改变 `dma.deslice_covers_target(...)` 的判断口径。

必须新增或调整的测试用例：

- `test_dma_fill_canonicalization_removes_fill_for_if_full_deslice_before_alias_read`：then 分支 full `dma.deslice(target, ...)` 后读 reshape/view alias，else 为空或不存在；删除 fill。
- `test_dma_fill_canonicalization_keeps_fill_when_else_reads_alias_without_overwrite`：else 分支读 target/alias 但没有 full overwrite；保留 fill。
- `test_dma_fill_canonicalization_keeps_fill_for_partial_deslice_in_if`：分支内 `dma.deslice` offsets/sizes/strides 不能证明完整覆盖；保留 fill。
- `test_dma_fill_canonicalization_keeps_fill_for_nested_region_in_if_branch`：分支内出现 nested region 或未知控制流；保留 fill。
- `test_dma_fill_canonicalization_keeps_fill_when_target_is_function_argument`：fill target 不是本地 `dma.alloc` root；保留 fill。
- `test_dma_fill_canonicalization_keeps_fill_when_branch_escapes_target`：target/alias 传入未知 effect op 或 func.call；保留 fill。

验收：

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/dialect/dma/test_canonicalization.py
```

合同验收：

- 本小任务不修改 `expectation/`。

### S5：补 pipeline 与 matmul demo 回归

- 为什么做：单 pass 测试不足以证明真实 `npu-demo-lowering` 链路中 fill 被消除。
- 做什么：补 static/dynamic 与 dynamic/dynamic matmul pipeline dump 断言，精确区分 acc fill、bias fill、input tile fill。
- 不做什么：不把 dynamic/dynamic acc fill 删除写成完成态；不修改 demo kernel 以绕过 pass 证明。
- 怎么验收：pipeline pytest 能证明 final typed IR 满足本计划完成态，demo 相关测试仍通过。
- 卡住问谁：若真实 dump 里 fill 残留来自其它合法初始化，先回计划修订，不直接扩大删除规则。

详细执行：

1. 在 `test/passes/pipeline/test_npu_demo_lowering.py` 中复用公开 matmul demo kernel 与 `set_dump_dir(...)`。
2. static/dynamic case：
   - final third `symbol-hoist-pipeline` 后不残留可证明 dead acc/input/bias fill，其中 acc fill 删除依赖 DU1-A 的 positive runtime tile step 合同。
   - `kernel.matmul` 继续消费 logical `dma.reinterpret` alias。
   - memory-pool 后不残留 typed alloc/free。
3. dynamic/dynamic case：
   - 不做全局 no-fill 断言。
   - 精确断言 input staging full-deslice fill 与 bias safe-if fill 不残留；acc fill 因 DU2-A 不假设 dynamic `K > 0` 可保留，并写明原因。
4. 运行 matmul symbolic demo pytest，确认源码生成和运行链路不回退。

必须同步的 source 断言：

- `test_dynamic_matmul_demo_uses_symbolic_memory_and_tile_reduce_accumulator`：继续调用 `_assert_source_uses_accumulator(source)`，保留 dynamic/dynamic acc fill 预期。
- `test_static_dynamic_matmul_demo_keeps_static_memory_and_symbolic_tile_reduce`：改为 `_assert_source_uses_accumulator(source, expect_initial_fill=False)`，锁定 static/dynamic acc initial fill 删除。
- `test_static_static_matmul_demo_keeps_static_memory_and_static_tile_reduce`：继续使用 `expect_initial_fill=False`，作为静态 step acc fill 规范化基线。
- pipeline dump 测试必须与 source 断言一致：static/dynamic source 期望无 initial acc `fill<`；dynamic/dynamic 不得让 final hoist 全局 no-fill 断言覆盖合法保留的 acc fill。

验收：

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/passes/pipeline/test_npu_demo_lowering.py -k "matmul or symbol_hoist_pipeline"
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/kernel/test_matmul_symbolic_memory_genkernel.py
```

合同验收：

- 不运行旧 `expectation.pass.kernel_decompose` initial fill 删除 case 作为当前必过合同验收；仅在记录中说明历史冲突和 DU3-B 用户确认来源。

## 总体验收命令

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/passes/kernel/test_kernel_decompose.py
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/dialect/dma/test_canonicalization.py
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/passes/pipeline/test_npu_demo_lowering.py -k "matmul or symbol_hoist_pipeline"
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/kernel/test_matmul_symbolic_memory_genkernel.py
```

合同验收：

- 基于 DU3-B，不把旧 `expectation.pass.kernel_decompose` initial fill 删除 case 列为当前必过；仅在记录中说明历史冲突和用户确认来源。

## Diff 反推测试要求

- execute 不能只运行上述最低命令；必须按实际 diff 追加相关 pass、dialect、pipeline 或 demo 测试。
- 若修改 `kernel_gen/dialect/dma/canonicalization.py`，至少运行 `test/dialect/dma/test_canonicalization.py`。
- 若修改 `kernel_gen/passes/kernel/kernel_decompose.py`，至少运行 `test/passes/kernel/test_kernel_decompose.py`。
- 若修改 pipeline 断言或影响 matmul dump，至少运行 `test/passes/pipeline/test_npu_demo_lowering.py` 的相关 case。
- `expectation` 只作为合同验收资产，不计入 diff 反推测试。

## 用户确认与协同约束

- DU1-A 已确认 runtime tile 参数为正数，execute 必须把 static/dynamic positive runtime tile step acc fill 删除写成必达完成态。
- DU2-A 已确认不假设 dynamic shape `K > 0`，execute 不得把 dynamic/dynamic acc fill 删除写成必达完成态。
- 本计划不授权 execute 修改 `expectation/`；若 execute 或 review 发现已有 expectation 与最新 spec 冲突，只能记录 actual / expected / spec / verdict 并请求用户或架构师裁定。
- 本计划下发前必须完成至少两路 subagent strict review 收敛，且所有审阅任务均无阻断、无最小需改项、无待确认项。
- subagent 收敛后必须由 `守护最好的爱莉希雅` 执行守护最终检验；守护最终检验通过前不得创建唯一计划级 execute 任务。
- 本计划只讨论 matmul dynamic acc / fill canonicalization；不得借计划执行 pass 目录迁移、dump marker 改造、runtime manifest 或其它专题重构。

## 计划书入档验收 / 复验 / 修复复核记录

- 当前状态：未执行。
- 计划书入档验收前置：
  - DU1-A / DU2-A / DU3-B 用户确认已写入计划正文。
  - subagent strict review 已按最新计划文本收敛到无阻断、无最小需改项、无待确认项。
  - 守护最终检验已通过。
- 入档验收必查：
  - `kernel-decompose` 是否只负责 fusion 分解并保留 fill。
  - `dma.fill` canonicalization 是否是所有 fill 删除的唯一实现落点。
  - `expectation/` 是否按 DU3-B 保持只读，旧 `expectation.pass.kernel_decompose` initial fill 删除 case 是否仅作为历史来源记录。
  - 总体验收命令是否与计划完成态一致，且 `expectation` 未混入 diff 反推测试。

## 迭代审阅记录

### Draft 1：主线起草

- 状态：未发起 subagent strict review。
- 问题：Draft 1 仍把 acc fill 删除放在 `kernel-decompose`，与用户后续裁定不一致。
- 结论：已由 Draft 2 替代。

### Draft 2 / Draft 2-R1：按用户裁定收窄 kernel-decompose

- 触发：2026-06-07 用户指出“`kernel-decompose` 不做 fill 是否删除”“fill 就在规范化中看”。
- 主线处理：
  - 将 acc fill 删除从 `kernel-decompose` 迁到 `dma.fill` canonicalization。
  - `kernel-decompose` 完成态改为只分解 fusion、保留 fill。
  - 新增 dynamic acc matmul dead-fill canonicalization 小任务。
  - Draft 2-R1 补齐计划书入档验收记录占位与用户确认 / 协同约束。
- 当前阻断：
  - DU1 runtime tile 参数正数合同未确认。
  - DU2 dynamic shape 正数合同未确认。
- 状态：未发起 subagent strict review；不得进入 execute 下发。

### Draft 2-R2：第一路 subagent strict review 最小需改项修订

- 审阅任务：
  - `Euclid / 019ea258-b579-7223-b542-5ec3d499abc6`：最小需改项。
- 输入标准包：
  - 根 `AGENTS.md`
  - `agents/standard/计划书标准.md`
  - `agents/standard/spec文件规范.md`
  - `agents/standard/测试文件约定.md`
  - `agents/standard/审查规范.md`
  - Draft 2-R1 全文
- 严格通过口径：计划目标、非目标、禁止修改面、合同真源、公开 API 边界无歧义；未确认语义合同只在待确认项中；计划流程完整；小任务卡可执行；验收命令和合同验收分开；仍有可执行返工项不得通过。
- 发现问题与主线处理：
  1. `expectation.pass.kernel_decompose` 当前旧合同要求 `kernel-decompose` 删除 initial fill，与新完成态冲突。主线处理：新增 DU3，并在当前基线、合同验收、入档验收中显式列为下发前阻断。
  2. DU1 未确认时，计划级目标、S3 与 S5 仍无条件要求 dynamic symbol step acc fill 删除。主线处理：把 dynamic-step acc fill 删除全部改为 DU1-A 条件完成态；DU1 未确认或 DU1-B 时只要求静态 step acc fill 与 bias/input fill 规范化。
  3. 禁止修改面误写“不修改任务记录”，与计划记录文件冲突。主线处理：改为不修改无关任务记录，允许写本计划执行/review/入档记录。
- 状态：已修订为 Draft 2-R2，等待第二路 subagent review 和必要复审。

### Draft 2-R3：第二路 subagent strict review 最小需改项修订

- 审阅任务：
  - `Dalton / 019ea258-b5d6-7c41-af38-7d01c924a4cd`：最小需改项。
- 输入标准包：
  - 根 `AGENTS.md`
  - `agents/standard/计划书标准.md`
  - `agents/standard/spec文件规范.md`
  - `agents/standard/测试文件约定.md`
  - `agents/standard/审查规范.md`
  - Draft 2-R1 全文
- 严格通过口径：计划实现方案必须落到现有代码结构；`kernel-decompose` 与 `dma.fill` canonicalization 边界一致；正反例、pipeline 回归、matmul source 回归足够；小任务步骤和验收可一次闭环；仍有可执行返工项不得通过。
- 发现问题与主线处理：
  1. DU1 未确认时仍存在 static/dynamic acc fill 必删口径。主线处理：Draft 2-R2 已把 dynamic-step acc fill 删除全部改为 DU1-A 条件完成态。
  2. `expectation.pass.kernel_decompose` 旧合同冲突。主线处理：Draft 2-R2 已新增 DU3，并列为下发前阻断。
  3. S3/S4/S5 测试设计过窄，未列必要反例，matmul source `expect_initial_fill` 预期未同步。主线处理：Draft 2-R3 补 S3 dynamic acc 反例矩阵、S4 `scf.if` 反例矩阵，以及 S5 三个 matmul source 测试的 `expect_initial_fill` 条件策略。
- 状态：已修订为 Draft 2-R3，并已在 Draft 2-R4 基于复审继续收口；DU1/DU2/DU3 未确认前不得下发。

### Draft 2-R4：Draft 2-R3 复审返工收口

- 审阅任务：
  - `Euclid / 019ea258-b579-7223-b542-5ec3d499abc6`：最小需改项。
  - `Dalton / 019ea258-b5d6-7c41-af38-7d01c924a4cd`：阻断。
- 输入标准包：
  - 根 `AGENTS.md`
  - 当前角色口径：计划负责人，只做计划书，不执行实现；争议、冲突、不确定事项进入用户待确认。
  - `agents/standard/计划书标准.md`
  - `agents/standard/spec文件规范.md`
  - `agents/standard/实现文件规范.md`
  - `agents/standard/测试文件约定.md`
  - `agents/standard/审查规范.md`
  - `agents/standard/任务记录约定.md`
  - Draft 2-R3 全文
  - 上轮问题、本轮收口摘要、DU1/DU2/DU3 待确认项、禁止修改面和验收命令
- 严格通过口径：上轮 expectation 冲突、DU1 条件完成态、任务记录边界和测试反例矩阵必须闭环；小任务卡必须自包含；`expectation/` 修改权限不得下发给 execute；仍有可执行返工项或待确认项不得进入守护最终检验。
- 发现问题与主线处理：
  1. S1 短口径写“不修改 expectation”，但详细步骤写 DU3-A 同步更新 expectation。主线处理：S1 改为 execute 不修改 `expectation/`；DU3-A 只消费用户 / 架构师已先行更新的 `expectation.pass.kernel_decompose`。
  2. DU3-A 把 `expectation/` 更新下发给 execute，违反合同资产权限。主线处理：DU3-A 改为用户 / 架构师先行更新，execute 只读取、执行、引用和记录；总体验收与 S5 合同验收同步改口径。
  3. S1-S5 小任务卡缺显式 `合同真源 / 模块范围 / 最小功能闭环 / 记录要求` 字段。主线处理：新增 `通用执行字段`，由 S1-S5 继承，明确 DU3-A/DU3-B/DU3-C 下的合同真源、模块范围、最小闭环和记录要求。
  4. DU1/DU2/DU3 仍未由用户收口。主线处理：保留为当前阻断，不擅自确认；待用户确认后再修订完成态、验收命令和审阅记录。
- 状态：已修订为 Draft 2-R4；仍需基于最新文本发起下一轮 subagent strict review。DU1/DU2/DU3 未确认前不得写 subagent 收敛结论、不得进入守护最终检验、不得下发 execute。

### Draft 2-R4：最新文本复审结果

- 审阅任务：
  - `Euclid / 019ea258-b579-7223-b542-5ec3d499abc6`：阻断，仅因 DU1/DU2/DU3 待用户确认；无新增文本返工项。
  - `Dalton / 019ea258-b5d6-7c41-af38-7d01c924a4cd`：阻断，仅因 DU1/DU2/DU3 待用户确认；无新增文本返工项。
- 输入标准包：
  - 根 `AGENTS.md`
  - 当前角色口径：计划负责人，只做计划书，不执行实现；争议、冲突、不确定事项进入用户待确认。
  - `agents/standard/计划书标准.md`
  - `agents/standard/spec文件规范.md`
  - `agents/standard/实现文件规范.md`
  - `agents/standard/测试文件约定.md`
  - `agents/standard/审查规范.md`
  - `agents/standard/任务记录约定.md`
  - Draft 2-R4 全文
  - R3/R4 上轮问题、本轮收口摘要、DU1/DU2/DU3 待确认项、禁止修改面和验收命令
- 严格通过口径：R3/R4 的可执行返工项必须闭环；`expectation/` 修改权限不得下发给 execute；S1-S5 必须继承明确的合同真源、模块范围、最小功能闭环和记录要求；除 DU1/DU2/DU3 待用户确认外不得有新的阻断或最小需改项。
- 发现问题与主线处理：
  1. R3 的 S1 expectation 短口径冲突已闭环，S1 与详细步骤均写为 execute 不修改 `expectation/`。
  2. R3 的 DU3-A execute 修改 expectation 权限问题已闭环，当前文本写为用户 / 架构师先行更新，execute 只读取、执行、引用和记录。
  3. R3 的小任务卡字段缺口已闭环，`通用执行字段` 可由 S1-S5 继承。
  4. DU1/DU2/DU3 仍未由用户收口。主线处理：保持待确认阻断；收到用户确认后更新计划完成态、验收命令和迭代审阅记录，再发起最终 subagent 收敛复审。
- subagent 收敛结论：尚未收敛。当前无新增可执行文本返工项，但仍有 DU1/DU2/DU3 待用户确认；不得进入守护最终检验。

### Draft 2-R5：用户确认 DU1/DU2/DU3 后修订

- 用户确认：
  - DU1-A：runtime tile 参数必须为正数，static/dynamic 的 acc fill 可以删。
  - DU2-A：不假设 dynamic shape `K > 0`，dynamic/dynamic 的 acc fill 暂不要求删除。
  - DU3-B：旧 `expectation.pass.kernel_decompose` initial fill 删除 case 作为历史只读来源，不列为本计划必过；execute 不修改 `expectation/`。
- 主线处理：
  1. 标题、当前状态和用户确认来源更新为 Draft 2-R5。
  2. 将 `待确认项` 改为 `用户确认项`，活跃正文不再保留 DU1/DU2/DU3 未确认分支。
  3. 完成态明确 static/dynamic positive runtime tile step acc fill 必须由 canonicalization 删除；dynamic/dynamic acc fill 不作为必须删除项。
  4. S3/S5 测试口径同步：positive runtime tile symbol step 正例成为必过；dynamic end / dynamic `K` 相关 acc fill 删除仍为非完成态。
  5. 合同验收同步 DU3-B：旧 `expectation.pass.kernel_decompose` initial fill 删除 case 只记录历史冲突，不列为当前必过命令。
- 状态：已基于 Draft 2-R5 完成最终 subagent strict review，Volta 与 Lorentz 均通过；允许请求守护最终检验。

### Draft 2-R5：最终 subagent strict review 收敛结论

- 审阅任务：
  - `Volta / 019ea28e-08b4-7232-a25a-393a02cc600d`：通过；无阻断、无最小需改项、无待确认项；允许进入守护最终检验。
  - `Lorentz / 019ea28e-0d94-7993-89c7-e6100aa3b4a2`：通过；无阻断、无最小需改项、无待确认项；允许进入守护最终检验。
- 输入标准包：
  - 根 `AGENTS.md`
  - 当前角色口径：计划负责人只做计划书，不执行实现；争议、冲突、不确定事项进入用户确认；本轮用户已确认 DU1-A / DU2-A / DU3-B。
  - `agents/standard/计划书标准.md`
  - `agents/standard/spec文件规范.md`
  - `agents/standard/实现文件规范.md`
  - `agents/standard/测试文件约定.md`
  - `agents/standard/审查规范.md`
  - `agents/standard/任务记录约定.md`
  - Draft 2-R5 全文
  - R4 复审结论、用户确认项、禁止修改面和验收命令
- 严格通过口径：
  1. R5 active 正文无 DU1/DU2/DU3 待确认项。
  2. static/dynamic positive runtime tile step acc fill 删除是必达完成态。
  3. dynamic/dynamic acc fill 不被写成必删。
  4. `expectation/` 修改权限没有下发给 execute；旧 `expectation.pass.kernel_decompose` initial fill 删除 case 没列入当前必过合同验收。
  5. S1-S5 自包含且可执行，验收命令与完成态一致。
  6. 无阻断、无最小需改项、无待确认项时，允许写 subagent 收敛结论并请求守护最终检验。
- 收敛结论：
  - 所有已发起或计划要求的 subagent strict review 均已收敛到无阻断、无最小需改项、无待确认项。
  - 用户待决策项 DU1/DU2/DU3 已全部收口并写入正文。
  - 正式计划索引门禁已通过：`git add -f ARCHITECTURE/plan/matmul_dynamic_acc_fill_canonicalization.md` 已执行；`git ls-files --stage -- ARCHITECTURE/plan/matmul_dynamic_acc_fill_canonicalization.md` 显示该文件已有 `100644` tracked 索引项；`git diff --cached --name-status -- ARCHITECTURE/plan/matmul_dynamic_acc_fill_canonicalization.md` 显示 `A`；`git status --short --ignored --untracked-files=all -- ARCHITECTURE/plan/matmul_dynamic_acc_fill_canonicalization.md` 显示 `A`，不再是仅 ignored 的 `!!`。
  - 遗留项：无。
  - 状态：允许进入守护最终检验；守护最终检验通过前不得下发 execute。

## 守护最终检验记录

- 状态：已执行。
- 检验对象：`守护最好的爱莉希雅`。
- 结论：通过。
- 阻断项：无。
- 最小需改项：无。
- 待确认项：无。
- 关键证据摘要：
  - 已只读核对 Draft 2-R5，未改文件、未创建任务、未通知管理员。
  - DU1-A / DU2-A / DU3-B 已写入正文：runtime tile 参数为正；不假设 dynamic `K > 0`；旧 `expectation.pass.kernel_decompose` initial fill 删除 case 仅作历史只读来源，execute 不改 `expectation/`。
  - 公开 API 列表明确不新增公开 API，且保留 `KernelDecomposePass`、`DmaFillOp`、`build_npu_demo_lowering_pipeline(...)` 等签名和公开行为边界。
  - Volta `019ea28e-08b4-7232-a25a-393a02cc600d` 与 Lorentz `019ea28e-0d94-7993-89c7-e6100aa3b4a2` 最终 strict review 均通过，无阻断、无最小需改项、无待确认项。
  - S1-S5 与总体验收命令已同步到 DU1/DU2/DU3 口径；旧 expectation case 未列为当前必过合同验收。
  - 索引门禁核对通过：计划文件已通过 `git add -f` 进入 index；`git ls-files --stage -- ARCHITECTURE/plan/matmul_dynamic_acc_fill_canonicalization.md` 显示 `100644` tracked 索引项；cached name-status 显示 `A`；status 显示 `A`，不是 ignored-only。具体 blob 以守护最终检验复核时当前 `git ls-files --stage` 输出为准。
- 是否允许通知管理员创建唯一计划级 execute：允许。
