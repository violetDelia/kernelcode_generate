时间：2026-04-06 15:10 +0800
经办人：睡觉小分队
任务：T-20260406-5c5fef52（nn_mlir_gen_lowering_expectation_green_plan-S1-spec）
任务目标：在 spec 中统一 broadcast/compare/transpose/exp/reduce/softmax/matmul/img2col/conv/fc 的原始语义、decomposition、lowering 目标面、输出合同、失败边界与职责矩阵；写死 nn 与 dma/kernel 职责边界；并明确 S2 只能在 S1 合并后启动。
改动：
- 新建任务记录文件，后续追加本次 spec 修改清单、关键条款与验证证据。
结论：进行中。

时间：2026-04-06 15:30 +0800
经办人：睡觉小分队
任务：T-20260406-5c5fef52（nn_mlir_gen_lowering_expectation_green_plan-S1-spec）
任务目标：在 spec 中统一 broadcast/compare/transpose/exp/reduce/softmax/matmul/img2col/conv/fc 的原始语义、decomposition、lowering 目标面、输出合同、失败边界与职责矩阵；写死 nn 与 dma/kernel 职责边界；并明确 S2 只能在 S1 合并后启动。
改动：
- 收口 lowering/decomposition 矩阵与职责矩阵（机械写死，禁止“由实现决定”）：
  - `spec/operation/nn.md`：补齐 compare 的“隐式 broadcast 语义 + 下游必须显式化”合同；写死 `conv -> nn.img2col2d + nn.matmul (+attrs)` 与 `fc -> nn.matmul (+bias add)` 的 decomposition；补齐职责矩阵与 mixed compare 显式化要求。
  - `spec/dialect/nn.md`：写死“方言层不支持逐元素隐式 broadcast”；明确 `operation.broadcast_to(...)` 进入方言必须归一化为 `nn.broadcast`（不新增 `nn.broadcast_to` dialect op）；明确 `conv/fc` 不作为方言独立 op 公开。
  - `spec/dialect/dma.md`：冻结 `dma.broadcast` 与 `dma.transpose` 作为 lowering 目标面；写明参数域、verifier 约束、标量/`!symbol.int` 输入语义与“禁止 silent fallback”的拒绝路径；将 analysis 覆盖口径引用统一指向 `spec/analysis/analysis_engine.md`，避免在 dialect 规范重复维护统计合同。
  - `spec/dialect/kernel.md`：明确 kernel 仅承载计算原语（无 broadcast/transpose 入口）；compare 仅接受 memory operand；structured op 以具名 `kernel.exp/reduce_*/softmax/matmul/img2col*` 冻结目标面。
  - `spec/pass/lowering/nn_to_kernel.md`：写死 pass 支持矩阵与 mixed compare 桥接（`memory+symbol/const -> dma.alloc + dma.broadcast -> kernel.compare family`）；补充职责矩阵与 lowering 表；补充阶段阻断条款（S2 仅允许在 S1 spec 合并后启动）。
- 计划书 S1 证据（rg 机械检查，exit=0）：
  - `cd wt-20260406-nn-mlir-lowering-s1 && rg -n "dma\\.broadcast|dma\\.transpose|kernel\\.(eq|reduce_|softmax|matmul|img2col|exp)|conv|fc" spec/operation/nn.md spec/dialect/nn.md spec/pass/lowering/nn_to_kernel.md spec/dialect/dma.md spec/dialect/kernel.md`（命中 116 行）
- 新建唯一后续任务：T-20260406-a9a00ca5（S1 复审；同计划书与同记录文件）
结论：S1 spec 收口完成；已新建复审任务 T-20260406-a9a00ca5。按计划书门禁，S2 必须在 S1 合并后方可启动。

时间：2026-04-06 15:38 +0800
经办人：提莫炖蘑菇
任务：T-20260406-a9a00ca5（nn_mlir_gen_lowering_expectation_green_plan-S1-复审）
任务目标：复审 S1 spec 是否完整写死 lowering/decomposition 矩阵、职责边界、失败边界，并检查“ S2 仅在 S1 合并后启动”条款。
改动：只读审查 spec 文件；未改代码/未改 spec。
结论：通过。
问题清单：未发现问题。
风险：
- 漏洞排查结果：已核对输入校验绕过/类型或形状绕过/边界越界/错误处理缺失/状态污染/资源释放问题六类风险；当前 spec 已明确禁止 silent fallback 并写死显式广播/transpose/结构化 lowering，未见新增风险。
验证命令：
- `cd /home/lfr/kernelcode_generate/wt-20260406-nn-mlir-lowering-s1 && git diff --name-only`
- `cd /home/lfr/kernelcode_generate/wt-20260406-nn-mlir-lowering-s1 && rg -n "S2" spec/pass/lowering/nn_to_kernel.md`
关键输出：
- diff 范围：`spec/dialect/dma.md`、`spec/dialect/kernel.md`、`spec/dialect/nn.md`、`spec/operation/nn.md`、`spec/pass/lowering/nn_to_kernel.md`
- `spec/pass/lowering/nn_to_kernel.md:48` 明确“`S2` 仅允许在 `S1` spec 合同合并后启动”
下一步建议：进入合并收口流程（派生合并任务给李白）。
