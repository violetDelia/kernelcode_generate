时间：2026-04-24 04:00 +0800
经办人：咯咯咯
任务：T-20260423-432a6289
任务目标：按计划书 S5 收口 `nn_lowering family` 的 spec 口径，把 surviving 模块级接口统一到 `NnLoweringPass.apply(...)`、`nn_lowering_patterns()` 与各 child 模块 `*_patterns()`，并把旧 family helper 的退场范围写清。
执行前阅读记录：
- 已读 [`TODO.md`](/home/lfr/kernelcode_generate/TODO.md:7) 当前任务行，确认 `worktree`、计划书、记录文件与任务指派一致；任务点名的 `worktree` 缺失，已按配置 `BRANCH=main` 创建 [`wt-20260423-pass-infra-s5`](/home/lfr/kernelcode_generate/wt-20260423-pass-infra-s5)。
- 已读 [`ARCHITECTURE/plan/pass_infrastructure_refactor_green_plan.md`](/home/lfr/kernelcode_generate/ARCHITECTURE/plan/pass_infrastructure_refactor_green_plan.md:580) 的 `S5` 正文、全局完成态、合同真源顺序与验收设计。
- 已读前序记录 [`20260423-pass-infra-s1.md`](/home/lfr/kernelcode_generate/agents/codex-multi-agents/log/task_records/2026/17/20260423-pass-infra-s1.md) 与 [`20260423-pass-infra-s2.md`](/home/lfr/kernelcode_generate/agents/codex-multi-agents/log/task_records/2026/17/20260423-pass-infra-s2.md)，确认 `lower-nn` canonical import、`nn_to_kernel` 旧模块失败边界与 `expectation` 单列口径仍需保留。
- 已读当前 worktree 的 [`spec/pass/lowering/nn_lowering/spec.md`](/home/lfr/kernelcode_generate/wt-20260423-pass-infra-s5/spec/pass/lowering/nn_lowering/spec.md)、[`spec/pass/lowering/nn_lowering/element_binary_lowering.md`](/home/lfr/kernelcode_generate/wt-20260423-pass-infra-s5/spec/pass/lowering/nn_lowering/element_binary_lowering.md)、[`spec/pass/lowering/nn_lowering/dma_structured_lowering.md`](/home/lfr/kernelcode_generate/wt-20260423-pass-infra-s5/spec/pass/lowering/nn_lowering/dma_structured_lowering.md)、[`spec/pass/lowering/nn_lowering/select_cast_lowering.md`](/home/lfr/kernelcode_generate/wt-20260423-pass-infra-s5/spec/pass/lowering/nn_lowering/select_cast_lowering.md)、[`spec/pass/lowering/nn_lowering/reduce_softmax_lowering.md`](/home/lfr/kernelcode_generate/wt-20260423-pass-infra-s5/spec/pass/lowering/nn_lowering/reduce_softmax_lowering.md)、[`spec/pass/lowering/nn_lowering/matmul_img2col_lowering.md`](/home/lfr/kernelcode_generate/wt-20260423-pass-infra-s5/spec/pass/lowering/nn_lowering/matmul_img2col_lowering.md)。
- 已读相关 pytest 与实现现场：[`test/pass/nn_lowering/public_name.py`](/home/lfr/kernelcode_generate/wt-20260423-pass-infra-s5/test/pass/nn_lowering/public_name.py)、[`test/pass/nn_lowering/test_lowering_nn_lowering.py`](/home/lfr/kernelcode_generate/wt-20260423-pass-infra-s5/test/pass/nn_lowering/test_lowering_nn_lowering.py)、[`test/pass/nn_lowering/test_nn_lowering_private_helpers.py`](/home/lfr/kernelcode_generate/wt-20260423-pass-infra-s5/test/pass/nn_lowering/test_nn_lowering_private_helpers.py)、[`kernel_gen/passes/lowering/nn_lowering/nn_lowering.py`](/home/lfr/kernelcode_generate/wt-20260423-pass-infra-s5/kernel_gen/passes/lowering/nn_lowering/nn_lowering.py) 及各 child 实现文件。
最小功能闭环：
- 总 spec 需要把 `lower-nn` 的稳定形态写成“`NnLoweringPass.apply(...)` + `nn_lowering_patterns()` + 单 op `RewritePattern` 顺序化 driver”，而不是 family dispatcher。
- child spec 需要把 `element_binary`、`dma_structured`、`select_cast`、`reduce_softmax`、`matmul_img2col` 的 surviving 模块级接口统一成 `*_patterns()`，并明确 `lower_*_family` 不再属于公开接口。
- 下游 build 需要同时处理实现导出与测试导入：当前 [`kernel_gen/passes/lowering/nn_lowering/element_binary_lowering.py`](/home/lfr/kernelcode_generate/wt-20260423-pass-infra-s5/kernel_gen/passes/lowering/nn_lowering/element_binary_lowering.py)、[`dma_structured_lowering.py`](/home/lfr/kernelcode_generate/wt-20260423-pass-infra-s5/kernel_gen/passes/lowering/nn_lowering/dma_structured_lowering.py)、[`select_cast_lowering.py`](/home/lfr/kernelcode_generate/wt-20260423-pass-infra-s5/kernel_gen/passes/lowering/nn_lowering/select_cast_lowering.py)、[`reduce_softmax_lowering.py`](/home/lfr/kernelcode_generate/wt-20260423-pass-infra-s5/kernel_gen/passes/lowering/nn_lowering/reduce_softmax_lowering.py)、[`matmul_img2col_lowering.py`](/home/lfr/kernelcode_generate/wt-20260423-pass-infra-s5/kernel_gen/passes/lowering/nn_lowering/matmul_img2col_lowering.py) 仍导出 `lower_*_family`，且多份 pytest 仍直接导入这些 helper。
改动：
- 更新 [`spec/pass/lowering/nn_lowering/spec.md`](/home/lfr/kernelcode_generate/wt-20260423-pass-infra-s5/spec/pass/lowering/nn_lowering/spec.md)：
  - 把主 pass 的成功口径收口为 `PatternRewriteWalker(GreedyRewritePatternApplier(nn_lowering_patterns()))`。
  - 保留 `kernel_gen.passes.lowering.nn_lowering` canonical import 与 `kernel_gen.passes.lowering.nn_to_kernel` 旧模块失败边界，不让 S5 覆盖 S2 既有合同。
  - 新增 `nn_lowering_patterns() -> list[RewritePattern]` 公开接口，明确注册顺序、reject-last 规则和不再允许出现 family dispatcher 占位 pattern。
  - 扩写 child 模块职责与 surviving 模块级接口，只承认各 child 的 `*_patterns()`。
- 更新 [`spec/pass/lowering/nn_lowering/element_binary_lowering.md`](/home/lfr/kernelcode_generate/wt-20260423-pass-infra-s5/spec/pass/lowering/nn_lowering/element_binary_lowering.md)，把公开接口改为 `element_binary_patterns()`，明确 `lower_element_binary_family` 不再属于公开入口，并补齐 `public_name.py` / `test_nn_lowering_private_helpers.py` 的测试映射。
- 更新 [`spec/pass/lowering/nn_lowering/dma_structured_lowering.md`](/home/lfr/kernelcode_generate/wt-20260423-pass-infra-s5/spec/pass/lowering/nn_lowering/dma_structured_lowering.md)，把公开接口改为 `dma_structured_patterns()`，明确 `nn.broadcast` / `nn.transpose` 各自独立 pattern，`lower_dma_structured_family` 不再属于公开入口。
- 更新 [`spec/pass/lowering/nn_lowering/select_cast_lowering.md`](/home/lfr/kernelcode_generate/wt-20260423-pass-infra-s5/spec/pass/lowering/nn_lowering/select_cast_lowering.md)，把模块职责扩成 `nn.select` / `nn.cast` / `nn.exp`，公开接口改为 `select_cast_patterns()`，并写清 `nn.exp` 已转入本模块。
- 更新 [`spec/pass/lowering/nn_lowering/reduce_softmax_lowering.md`](/home/lfr/kernelcode_generate/wt-20260423-pass-infra-s5/spec/pass/lowering/nn_lowering/reduce_softmax_lowering.md)，把公开接口改为 `reduce_softmax_patterns()`，移除旧 `reduce_sum.py/reduce_min.py/reduce_max.py` 测试路径口径，改写为 [`test/pass/nn_lowering/test_reduce_lowering.py`](/home/lfr/kernelcode_generate/wt-20260423-pass-infra-s5/test/pass/nn_lowering/test_reduce_lowering.py) 与 direct `nn.softmax` 拒绝口径。
- 更新 [`spec/pass/lowering/nn_lowering/matmul_img2col_lowering.md`](/home/lfr/kernelcode_generate/wt-20260423-pass-infra-s5/spec/pass/lowering/nn_lowering/matmul_img2col_lowering.md)，把公开接口改为 `matmul_img2col_patterns()`，明确 `matmul/img2col` 只保留单 op pattern 注册面。
- 当前 spec 同时明确了 build 必须回收的旧接口与测试调用点：
  - 实现侧：child 模块中的 `lower_*_family` 定义、示例、`__all__` 导出与依赖 `parent_block()` / `rewriter.has_done_action` 的旧 dispatcher 路径。
  - 测试侧：[`test/pass/nn_lowering/test_nn_lowering_private_helpers.py`](/home/lfr/kernelcode_generate/wt-20260423-pass-infra-s5/test/pass/nn_lowering/test_nn_lowering_private_helpers.py)、[`test/pass/nn_lowering/select.py`](/home/lfr/kernelcode_generate/wt-20260423-pass-infra-s5/test/pass/nn_lowering/select.py)、[`test/pass/nn_lowering/cast.py`](/home/lfr/kernelcode_generate/wt-20260423-pass-infra-s5/test/pass/nn_lowering/cast.py)、[`test/pass/nn_lowering/element_binary_add.py`](/home/lfr/kernelcode_generate/wt-20260423-pass-infra-s5/test/pass/nn_lowering/element_binary_add.py) 及其同类文件里对 `lower_*_family` 的直接导入与调用。
验证：
- `rg -n '### \`.*patterns\\(|lower_.*family|nn_to_kernel|PatternRewriteWalker|GreedyRewritePatternApplier' spec/pass/lowering/nn_lowering/spec.md spec/pass/lowering/nn_lowering/*.md`
  - 结果：命中总 spec 的 pattern driver、`nn_to_kernel` 旧模块失败边界，以及 5 份 child spec 的 `*_patterns()` 公开接口与 `lower_*_family` 退场口径。
- `rg -n 'test/pass/nn_lowering/reduce_(sum|min|max)\\.py|test/pass/nn_lowering/reduce_sum\\.py|test/pass/nn_lowering/reduce_min\\.py|test/pass/nn_lowering/reduce_max\\.py' spec/pass/lowering/nn_lowering/spec.md spec/pass/lowering/nn_lowering/*.md`
  - 结果：无命中；旧 reduce 测试路径已从 spec 中移除。
- `git -C /home/lfr/kernelcode_generate/wt-20260423-pass-infra-s5 diff --stat -- spec/pass/lowering/nn_lowering/spec.md spec/pass/lowering/nn_lowering/dma_structured_lowering.md spec/pass/lowering/nn_lowering/element_binary_lowering.md spec/pass/lowering/nn_lowering/matmul_img2col_lowering.md spec/pass/lowering/nn_lowering/reduce_softmax_lowering.md spec/pass/lowering/nn_lowering/select_cast_lowering.md`
  - 结果：6 个 spec 文件，`337 insertions(+), 150 deletions(-)`。
- `git -C /home/lfr/kernelcode_generate/wt-20260423-pass-infra-s5 diff --check -- spec/pass/lowering/nn_lowering/spec.md spec/pass/lowering/nn_lowering/dma_structured_lowering.md spec/pass/lowering/nn_lowering/element_binary_lowering.md spec/pass/lowering/nn_lowering/matmul_img2col_lowering.md spec/pass/lowering/nn_lowering/reduce_softmax_lowering.md spec/pass/lowering/nn_lowering/select_cast_lowering.md`
  - 结果：通过。
- `rg -n '[[:blank:]]$' spec/pass/lowering/nn_lowering/spec.md spec/pass/lowering/nn_lowering/*.md`
  - 结果：无命中。
Diff 反推自测：
- 本轮实际 diff 只落在 6 份 `spec/pass/lowering/nn_lowering*.md` 文档与当前任务记录，因此反推自测只做文本核对、旧路径清点、空白检查与 `git diff --check`。
- 结合 spec 当前口径与实现现场，下一步 build 的 diff 反推自测至少应覆盖：
  - `pytest -q test/pass/nn_lowering/public_name.py test/pass/nn_lowering/test_lowering_nn_lowering.py test/pass/nn_lowering/test_nn_lowering_private_helpers.py`
  - 若 build 同时改动 element/select/cast/exp/reduce/matmul/img2col 的对应实现或测试文件，还应补跑 `test/pass/nn_lowering/element_binary_*.py`、`test/pass/nn_lowering/element_compare_*.py`、`test/pass/nn_lowering/select.py`、`test/pass/nn_lowering/cast.py`、`test/pass/nn_lowering/exp.py`、`test/pass/nn_lowering/test_reduce_lowering.py`、`test/pass/nn_lowering/matmul.py`、`test/pass/nn_lowering/img2col1d.py`、`test/pass/nn_lowering/img2col2d.py` 中与实际 diff 对应的最小集合。
- `expectation` 不计入上述 diff 反推测试；如需执行，只能在“合同验收”单列。
合同验收（如适用）：
- `expectation/pass/lowing/nn_lowering/**` 继续只作合同验收资产单列。
- 本轮未执行 `expectation`，也未把 `expectation` 当作当前 diff 的对应测试替代。
自检：
- 已读完整 `S5` 阶段、全局验收设计、S1/S2 前序记录以及相关 spec/test/实现；未越权改实现、测试或仓库中的 `expectation`。
- 本轮 spec 已把 API、边界、异常、兼容与文字歧义收口到可机械判断的状态：主链只承认 `NnLoweringPass.apply(...)` / `nn_lowering_patterns()` / `*_patterns()`，并保留了 `nn_to_kernel` 旧模块失败边界，没有覆盖前序合同。
- 文档已把下游必须改的实现导出和测试导入写具体，build 不需要再自己猜哪些 `lower_*_family` 仍算公开面。
- 本轮按 diff 反推完成了文本核对与格式检查；当前未发现同级别的 spec 缺口。后续剩余工作在 build：删旧 helper 出口、改 pytest、再用真实代码/测试证明这套口径落地。
结论：
- `T-20260423-432a6289` 的 spec 收口已完成；当前 worktree 已把 `nn_lowering family` 的公开接口、旧 helper 退场范围与下游 build 测试面写清。
- 下一步应回到 `build`：按最新 spec 清理 child 模块里的 `lower_*_family` 与旧导出，同步改写直接依赖这些 helper 的 pytest，并执行与实际 diff 对应的 `pytest`；`expectation` 继续单列处理。

时间：2026-04-24 04:17 +0800
经办人：jcc你莫辜负
任务：T-20260423-432a6289
任务目标：按最新 S5 spec 清理 `nn_lowering` child 模块的 `lower_*_family`、`__all__` 与旧示例，并把直接依赖这些 helper 的 pytest 收口到 `NnLoweringPass.apply(...)`、`nn_lowering_patterns()` 与各 child 模块 `*_patterns()`。
执行前阅读记录：
- 已读 [`TODO.md`](/home/lfr/kernelcode_generate/TODO.md:7) 当前任务行，确认任务类型为 `build`，`worktree`、计划书和记录文件一致。
- 已读 [`ARCHITECTURE/plan/pass_infrastructure_refactor_green_plan.md`](/home/lfr/kernelcode_generate/ARCHITECTURE/plan/pass_infrastructure_refactor_green_plan.md:580) 的 `S5` 正文、全局完成态/验收设计，以及同链路前序记录 [`20260423-pass-infra-s1.md`](/home/lfr/kernelcode_generate/agents/codex-multi-agents/log/task_records/2026/17/20260423-pass-infra-s1.md) 与 [`20260423-pass-infra-s2.md`](/home/lfr/kernelcode_generate/agents/codex-multi-agents/log/task_records/2026/17/20260423-pass-infra-s2.md)。
- 已读本 `worktree` 中的总 spec 与 child spec：[`spec/pass/lowering/nn_lowering/spec.md`](/home/lfr/kernelcode_generate/wt-20260423-pass-infra-s5/spec/pass/lowering/nn_lowering/spec.md)、[`element_binary_lowering.md`](/home/lfr/kernelcode_generate/wt-20260423-pass-infra-s5/spec/pass/lowering/nn_lowering/element_binary_lowering.md)、[`dma_structured_lowering.md`](/home/lfr/kernelcode_generate/wt-20260423-pass-infra-s5/spec/pass/lowering/nn_lowering/dma_structured_lowering.md)、[`select_cast_lowering.md`](/home/lfr/kernelcode_generate/wt-20260423-pass-infra-s5/spec/pass/lowering/nn_lowering/select_cast_lowering.md)、[`reduce_softmax_lowering.md`](/home/lfr/kernelcode_generate/wt-20260423-pass-infra-s5/spec/pass/lowering/nn_lowering/reduce_softmax_lowering.md)、[`matmul_img2col_lowering.md`](/home/lfr/kernelcode_generate/wt-20260423-pass-infra-s5/spec/pass/lowering/nn_lowering/matmul_img2col_lowering.md)。
- 已读实现与直接依赖旧 helper 的 pytest：[`kernel_gen/passes/lowering/nn_lowering/dma_structured_lowering.py`](/home/lfr/kernelcode_generate/wt-20260423-pass-infra-s5/kernel_gen/passes/lowering/nn_lowering/dma_structured_lowering.py)、[`element_binary_lowering.py`](/home/lfr/kernelcode_generate/wt-20260423-pass-infra-s5/kernel_gen/passes/lowering/nn_lowering/element_binary_lowering.py)、[`select_cast_lowering.py`](/home/lfr/kernelcode_generate/wt-20260423-pass-infra-s5/kernel_gen/passes/lowering/nn_lowering/select_cast_lowering.py)、[`reduce_softmax_lowering.py`](/home/lfr/kernelcode_generate/wt-20260423-pass-infra-s5/kernel_gen/passes/lowering/nn_lowering/reduce_softmax_lowering.py)、[`matmul_img2col_lowering.py`](/home/lfr/kernelcode_generate/wt-20260423-pass-infra-s5/kernel_gen/passes/lowering/nn_lowering/matmul_img2col_lowering.py)、[`test/pass/nn_lowering/public_name.py`](/home/lfr/kernelcode_generate/wt-20260423-pass-infra-s5/test/pass/nn_lowering/public_name.py)、[`test/pass/nn_lowering/test_lowering_nn_lowering.py`](/home/lfr/kernelcode_generate/wt-20260423-pass-infra-s5/test/pass/nn_lowering/test_lowering_nn_lowering.py)、[`test/pass/nn_lowering/test_nn_lowering_private_helpers.py`](/home/lfr/kernelcode_generate/wt-20260423-pass-infra-s5/test/pass/nn_lowering/test_nn_lowering_private_helpers.py) 以及 `element/select/cast` 相关单文件 pytest。
最小功能闭环：
- child 实现层不再暴露 `lower_*_family(block, op) -> bool` 兼容入口，模块级 surviving 接口只保留各自 `*_patterns()`。
- 直接依赖旧 helper 的 pytest 不再导入 child 模块的 `lower_*_family`，而是改走 `NnLoweringPass().run(module)` 或直接校验 `*_patterns()` / `__all__`。
- `public_name.py`、`test_lowering_nn_lowering.py` 与 `test_nn_lowering_private_helpers.py` 需要同时证明三件事：总 driver 仍走 `nn_lowering_patterns()`，child 模块只导出 `*_patterns()`，旧 helper 退场后 lowering 行为与错误边界不回退。
改动：
- 更新 [`kernel_gen/passes/lowering/nn_lowering/dma_structured_lowering.py`](/home/lfr/kernelcode_generate/wt-20260423-pass-infra-s5/kernel_gen/passes/lowering/nn_lowering/dma_structured_lowering.py)、[`element_binary_lowering.py`](/home/lfr/kernelcode_generate/wt-20260423-pass-infra-s5/kernel_gen/passes/lowering/nn_lowering/element_binary_lowering.py)、[`select_cast_lowering.py`](/home/lfr/kernelcode_generate/wt-20260423-pass-infra-s5/kernel_gen/passes/lowering/nn_lowering/select_cast_lowering.py)、[`reduce_softmax_lowering.py`](/home/lfr/kernelcode_generate/wt-20260423-pass-infra-s5/kernel_gen/passes/lowering/nn_lowering/reduce_softmax_lowering.py)、[`matmul_img2col_lowering.py`](/home/lfr/kernelcode_generate/wt-20260423-pass-infra-s5/kernel_gen/passes/lowering/nn_lowering/matmul_img2col_lowering.py)：删除 `lower_*_family` 兼容导出，`__all__` 收口到 `*_patterns()`，并把模块头部使用示例改成 surviving 接口；`reduce_softmax_lowering.py` 里顺手修正了失效的旧测试路径引用。
- 更新 [`test/pass/nn_lowering/public_name.py`](/home/lfr/kernelcode_generate/wt-20260423-pass-infra-s5/test/pass/nn_lowering/public_name.py)：新增 child 模块导出断言，要求 `element_binary`、`dma_structured`、`select_cast`、`reduce_softmax`、`matmul_img2col` 只保留 `*_patterns()`。
- 更新 [`test/pass/nn_lowering/test_nn_lowering_private_helpers.py`](/home/lfr/kernelcode_generate/wt-20260423-pass-infra-s5/test/pass/nn_lowering/test_nn_lowering_private_helpers.py)：移除对 `lower_*_family` 的直接调用，改成直接覆盖 `_lower_broadcast` / `_lower_transpose` / `_lower_matmul` / `_lower_img2col*` 等真实 helper，同时补 `__all__` 与 `*_patterns()` 名称断言，确保旧兼容出口退场后覆盖面不缩。
- 更新 [`test/pass/nn_lowering/select.py`](/home/lfr/kernelcode_generate/wt-20260423-pass-infra-s5/test/pass/nn_lowering/select.py)、[`cast.py`](/home/lfr/kernelcode_generate/wt-20260423-pass-infra-s5/test/pass/nn_lowering/cast.py)、[`element_binary_add.py`](/home/lfr/kernelcode_generate/wt-20260423-pass-infra-s5/test/pass/nn_lowering/element_binary_add.py)、[`element_binary_div.py`](/home/lfr/kernelcode_generate/wt-20260423-pass-infra-s5/test/pass/nn_lowering/element_binary_div.py)、[`element_binary_mul.py`](/home/lfr/kernelcode_generate/wt-20260423-pass-infra-s5/test/pass/nn_lowering/element_binary_mul.py)、[`element_binary_sub.py`](/home/lfr/kernelcode_generate/wt-20260423-pass-infra-s5/test/pass/nn_lowering/element_binary_sub.py)、[`element_binary_truediv.py`](/home/lfr/kernelcode_generate/wt-20260423-pass-infra-s5/test/pass/nn_lowering/element_binary_truediv.py)、[`element_compare_eq.py`](/home/lfr/kernelcode_generate/wt-20260423-pass-infra-s5/test/pass/nn_lowering/element_compare_eq.py)、[`element_compare_ge.py`](/home/lfr/kernelcode_generate/wt-20260423-pass-infra-s5/test/pass/nn_lowering/element_compare_ge.py)、[`element_compare_gt.py`](/home/lfr/kernelcode_generate/wt-20260423-pass-infra-s5/test/pass/nn_lowering/element_compare_gt.py)、[`element_compare_le.py`](/home/lfr/kernelcode_generate/wt-20260423-pass-infra-s5/test/pass/nn_lowering/element_compare_le.py)、[`element_compare_lt.py`](/home/lfr/kernelcode_generate/wt-20260423-pass-infra-s5/test/pass/nn_lowering/element_compare_lt.py)、[`element_compare_ne.py`](/home/lfr/kernelcode_generate/wt-20260423-pass-infra-s5/test/pass/nn_lowering/element_compare_ne.py)：去掉 child helper 导入，统一改用 `NnLoweringPass().run(module)` 驱动真实 pass。
验证：
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260423-pass-infra-s5:/home/lfr/kernelcode_generate pytest -q test/pass/nn_lowering/public_name.py test/pass/nn_lowering/test_lowering_nn_lowering.py test/pass/nn_lowering/test_nn_lowering_private_helpers.py test/pass/nn_lowering/select.py test/pass/nn_lowering/cast.py test/pass/nn_lowering/element_binary_add.py test/pass/nn_lowering/element_binary_div.py test/pass/nn_lowering/element_binary_mul.py test/pass/nn_lowering/element_binary_sub.py test/pass/nn_lowering/element_binary_truediv.py test/pass/nn_lowering/element_compare_eq.py test/pass/nn_lowering/element_compare_ge.py test/pass/nn_lowering/element_compare_gt.py test/pass/nn_lowering/element_compare_le.py test/pass/nn_lowering/element_compare_lt.py test/pass/nn_lowering/element_compare_ne.py`
  - 结果：`70 passed, 25 warnings in 0.36s`；warnings 均为既有 `xdsl` deprecation 提示，本轮 diff 未新增失败。
- `python3 -m py_compile kernel_gen/passes/lowering/nn_lowering/dma_structured_lowering.py kernel_gen/passes/lowering/nn_lowering/element_binary_lowering.py kernel_gen/passes/lowering/nn_lowering/matmul_img2col_lowering.py kernel_gen/passes/lowering/nn_lowering/reduce_softmax_lowering.py kernel_gen/passes/lowering/nn_lowering/select_cast_lowering.py test/pass/nn_lowering/public_name.py test/pass/nn_lowering/test_nn_lowering_private_helpers.py test/pass/nn_lowering/select.py test/pass/nn_lowering/cast.py test/pass/nn_lowering/element_binary_add.py test/pass/nn_lowering/element_binary_div.py test/pass/nn_lowering/element_binary_mul.py test/pass/nn_lowering/element_binary_sub.py test/pass/nn_lowering/element_binary_truediv.py test/pass/nn_lowering/element_compare_eq.py test/pass/nn_lowering/element_compare_ge.py test/pass/nn_lowering/element_compare_gt.py test/pass/nn_lowering/element_compare_le.py test/pass/nn_lowering/element_compare_lt.py test/pass/nn_lowering/element_compare_ne.py`
  - 结果：通过。
- `rg -n "lower_(element_binary|dma_structured|select_cast|reduce_softmax|matmul_img2col)_family" kernel_gen/passes/lowering/nn_lowering test/pass/nn_lowering`
  - 结果：无命中。
- `git -C /home/lfr/kernelcode_generate/wt-20260423-pass-infra-s5 diff --check`
  - 结果：通过。
Diff 反推自测：
- 本轮实际 diff 覆盖 5 个 child 实现文件、`public_name.py`、`test_nn_lowering_private_helpers.py`，以及 13 个直接依赖旧 helper 的 `nn_lowering` 单文件 pytest；因此反推自测选择了 `public_name.py`、`test_lowering_nn_lowering.py`、`test_nn_lowering_private_helpers.py` 和所有被改写的 `element/select/cast` 单测文件。
- 选择 `test_lowering_nn_lowering.py` 是因为 child 模块实现删除旧导出后，仍需证明 `NnLoweringPass.apply(...)` + `nn_lowering_patterns()` 的主路径行为未回退；单跑 child 私测不足以覆盖这条总链路。
- `py_compile`、旧 helper 残留扫描和 `git diff --check` 作为这批实现/测试文件的补充校验，结果均通过。
合同验收（如适用）：
- `expectation/pass/lowing/nn_lowering/**` 继续只作合同验收资产单列。
- 本轮未执行 `expectation`，也未把 `expectation` 计入 diff 反推自测。
自检：
- 已读完整 `S5` 阶段、全局验收设计和前序记录；仅修改实现与测试，未越权改 `spec` 外的其他阶段产物，也未修改任何 `expectation` 文件。
- 已检查 API 与导出边界：child 模块只剩 `*_patterns()`，`public_name.py` 和 `test_nn_lowering_private_helpers.py` 都会在 `__all__` 或 pattern 名称回退时失败；直接依赖旧 helper 的 pytest 也已全部切到新入口。
- 已检查函数粒度与复用：本轮没有额外引入新的兼容层，child 实现继续复用现有 `_lower_*` helper 和 typed pattern；没有为了测试再补一层中间包装。
- 已检查测试有效性：单文件 pytest 改用真实 `NnLoweringPass().run(module)` 后，如果 child pattern 注册、`nn_lowering_patterns()` 组装顺序或 `__all__` 回退，相关断言会直接失败；`test_lowering_nn_lowering.py` 也覆盖了总 driver 不回退。
- 已补齐本轮能直接修的文案问题：`reduce_softmax_lowering.py` 中已失效的 `reduce_sum.py` / `reduce_min.py` / `softmax.py` 引用已更新为当前现场测试文件；当前未再发现同级别的 diff 内可改进点。
结论：
- 当前 `build` 已完成；`nn_lowering` child 模块的旧 `lower_*_family` 导出、`__all__` 和直接依赖 pytest 已按 S5 收口，真实自检与 `Diff 反推自测` 已补齐。
- 下一步应进入 `review`：重点复核 child 模块是否只保留 `*_patterns()`、`public_name.py`/`test_nn_lowering_private_helpers.py` 的 surviving 接口断言是否完整，以及 `element/select/cast` 单测是否都已从旧 helper 切到 `NnLoweringPass().run(module)`。

时间：2026-04-24 11:33 +0800
经办人：不要啊教练
任务：T-20260423-432a6289
任务目标：复核 S5 nn_lowering child 模块是否已清理 lower_*_family、__all__ 与旧示例，重点检查 child 实现只保留 *_patterns()、public_name/test_nn_lowering_private_helpers 的 surviving 接口断言，以及直接依赖旧 helper 的 element/select/cast pytest 是否已切到 NnLoweringPass.apply(...) / run(...)
执行前阅读记录：
- 已读 [`TODO.md`](/home/lfr/kernelcode_generate/TODO.md:7) 当前任务行，确认当前任务处于 `review`，`worktree`、计划书与记录文件一致。
- 已读 [`ARCHITECTURE/plan/pass_infrastructure_refactor_green_plan.md`](/home/lfr/kernelcode_generate/ARCHITECTURE/plan/pass_infrastructure_refactor_green_plan.md:580) 的 `S5` 阶段正文、全局完成态/验收设计、`S1/S2` 前序记录要求，以及本任务当前 `spec/build` 记录。
- 已读当前 residual diff 涉及的实现、spec 与 pytest：[`kernel_gen/passes/lowering/nn_lowering/select_cast_lowering.py`](/home/lfr/kernelcode_generate/wt-20260423-pass-infra-s5/kernel_gen/passes/lowering/nn_lowering/select_cast_lowering.py)、[`test/pass/nn_lowering/public_name.py`](/home/lfr/kernelcode_generate/wt-20260423-pass-infra-s5/test/pass/nn_lowering/public_name.py)、[`test/pass/nn_lowering/test_nn_lowering_private_helpers.py`](/home/lfr/kernelcode_generate/wt-20260423-pass-infra-s5/test/pass/nn_lowering/test_nn_lowering_private_helpers.py)、[`test/pass/nn_lowering/select.py`](/home/lfr/kernelcode_generate/wt-20260423-pass-infra-s5/test/pass/nn_lowering/select.py)、[`test/pass/nn_lowering/cast.py`](/home/lfr/kernelcode_generate/wt-20260423-pass-infra-s5/test/pass/nn_lowering/exp.py) 及各 child lowering 模块。
真实审查：
- 已确认 child 实现侧的 `lower_*_family`、旧 `__all__` 和旧示例主线已经收住；[`public_name.py`](/home/lfr/kernelcode_generate/wt-20260423-pass-infra-s5/test/pass/nn_lowering/public_name.py) 与 [`test_nn_lowering_private_helpers.py`](/home/lfr/kernelcode_generate/wt-20260423-pass-infra-s5/test/pass/nn_lowering/test_nn_lowering_private_helpers.py) 也已经把 surviving 接口断言切到 `*_patterns()`。
- 已确认直接依赖旧 helper 的 `element/select/cast` 单测主线已改为通过 `NnLoweringPass().run(module)` 驱动真实 pass，不再直接导入 `lower_*_family`。
- 但当前 build 记录的 `Diff 反推自测` 仍缺一条和 residual diff 直接对应的 `exp.py`。[`select_cast_lowering.py`](/home/lfr/kernelcode_generate/wt-20260423-pass-infra-s5/kernel_gen/passes/lowering/nn_lowering/select_cast_lowering.py:1) 已把模块职责写成 `nn.select` / `nn.cast` / `nn.exp`，[`spec/pass/lowering/nn_lowering/select_cast_lowering.md`](/home/lfr/kernelcode_generate/wt-20260423-pass-infra-s5/spec/pass/lowering/nn_lowering/select_cast_lowering.md:98) 也把 [`test/pass/nn_lowering/exp.py`](/home/lfr/kernelcode_generate/wt-20260423-pass-infra-s5/test/pass/nn_lowering/exp.py) 列为本模块测试文件并写进必跑命令，但 build 记录中的 `pytest -q ...` 列表没有这条测试，证据链仍不完整。
问题清单：
- `P2` [`kernel_gen/passes/lowering/nn_lowering/select_cast_lowering.py`](/home/lfr/kernelcode_generate/wt-20260423-pass-infra-s5/kernel_gen/passes/lowering/nn_lowering/select_cast_lowering.py:1)、[`spec/pass/lowering/nn_lowering/select_cast_lowering.md`](/home/lfr/kernelcode_generate/wt-20260423-pass-infra-s5/spec/pass/lowering/nn_lowering/select_cast_lowering.md:98)、[`test/pass/nn_lowering/exp.py`](/home/lfr/kernelcode_generate/wt-20260423-pass-infra-s5/test/pass/nn_lowering/exp.py)
  - 现象：`select_cast_lowering` 本轮已把 `nn.exp` 收进 child 模块职责和 spec 测试矩阵，但 build 记录里的 `Diff 反推自测` 没把 `test/pass/nn_lowering/exp.py` 纳入。
  - 风险：当前 review 虽能现场证明 `exp.py` 通过，但 build 阶段的 residual diff 自测记录仍不完整；后续接手人无法机械确认 `nn.exp` 这一支是否被本轮 build 主动覆盖。
  - 建议：回到 `build`，把 `test/pass/nn_lowering/exp.py` 补进 `Diff 反推自测` 与记录，再回流 `review`。
可改进点：
- build 记录应把 `select_cast_lowering` 对应的 `nn.exp` 测试面补齐到 `Diff 反推自测`；当前这是本轮最直接、最小的收口项。
Diff 反推审查：
- 复核 build 已执行的 residual diff 自测：`PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260423-pass-infra-s5:/home/lfr/kernelcode_generate pytest -q test/pass/nn_lowering/public_name.py test/pass/nn_lowering/test_lowering_nn_lowering.py test/pass/nn_lowering/test_nn_lowering_private_helpers.py test/pass/nn_lowering/select.py test/pass/nn_lowering/cast.py test/pass/nn_lowering/element_binary_add.py test/pass/nn_lowering/element_binary_div.py test/pass/nn_lowering/element_binary_mul.py test/pass/nn_lowering/element_binary_sub.py test/pass/nn_lowering/element_binary_truediv.py test/pass/nn_lowering/element_compare_eq.py test/pass/nn_lowering/element_compare_ge.py test/pass/nn_lowering/element_compare_gt.py test/pass/nn_lowering/element_compare_le.py test/pass/nn_lowering/element_compare_lt.py test/pass/nn_lowering/element_compare_ne.py`
  - 记录结果：`70 passed, 25 warnings in 0.36s`。
- 针对当前遗漏点追加现场复核：`PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260423-pass-infra-s5:/home/lfr/kernelcode_generate pytest -q /home/lfr/kernelcode_generate/wt-20260423-pass-infra-s5/test/pass/nn_lowering/exp.py -ra`
  - 结果：`3 passed, 1 warning in 0.20s`。
- `git -C /home/lfr/kernelcode_generate/wt-20260423-pass-infra-s5 diff --check`
  - 结果：通过。
合同验收（单列）：
- 本轮未执行 `expectation`；按计划书与当前口径，`expectation/pass/lowing/nn_lowering/**` 继续只作合同验收资产单列，不计入 diff 反推测试。
自检：
- 已按任务要求先读 `TODO`、计划书 `S5`、全局完成态/验收设计和前序记录，再结合当前 residual diff 做真实审查。
- 已核对 API、边界、测试有效性与记录完整性：实现主线未见回退，当前唯一明确可改进点是 build 记录缺少 `exp.py` 这条与 residual diff 直接对应的自测。
- 本轮未改实现、spec、测试或 `expectation`，只补充审查记录并按流程回推。
结论：
- `需修改`。
- 当前 S5 child 模块的 surviving 接口与 `element/select/cast` 单测主线基本已收住，但 build 的 `Diff 反推自测` 仍漏掉 `select_cast_lowering` 对应的 [`test/pass/nn_lowering/exp.py`](/home/lfr/kernelcode_generate/wt-20260423-pass-infra-s5/test/pass/nn_lowering/exp.py)，需要先补齐记录再回流 `review`。

---

时间：2026-04-24 04:24 +0800
经办人：金铲铲大作战
任务：T-20260423-432a6289
任务目标：补齐 S5 `select_cast_lowering` 对应 [`test/pass/nn_lowering/exp.py`](test/pass/nn_lowering/exp.py) 的 `Diff 反推自测` 与记录，再回流 `review`。
执行前阅读记录：
- 已重读当前任务记录中的 `spec/build/review` 记录，确认 review 退回点只剩 `select_cast_lowering -> exp.py` 这条 diff 证据链缺口。
- 已重读 [`ARCHITECTURE/plan/pass_infrastructure_refactor_green_plan.md`](ARCHITECTURE/plan/pass_infrastructure_refactor_green_plan.md) 的 `S5` 正文、全局完成态/验收设计，以及 [`kernel_gen/passes/lowering/nn_lowering/select_cast_lowering.py`](kernel_gen/passes/lowering/nn_lowering/select_cast_lowering.py)、[`test/pass/nn_lowering/exp.py`](test/pass/nn_lowering/exp.py) 当前现场。
最小功能闭环：不改实现逻辑，只补 `select_cast_lowering` 当前 residual diff 对应的 [`test/pass/nn_lowering/exp.py`](test/pass/nn_lowering/exp.py) 运行证据，并把结果写回任务记录；已有大集合 pytest、`public_name.py`、`test_lowering_nn_lowering.py` 记录继续保留。
改动：
- 未改代码。
- 更新任务记录 [`20260423-pass-infra-s5.md`](agents/codex-multi-agents/log/task_records/2026/17/20260423-pass-infra-s5.md)，追加 `exp.py` 的 `Diff 反推自测`、真实自检与结论。
验证：
- `python3 -m py_compile kernel_gen/passes/lowering/nn_lowering/select_cast_lowering.py test/pass/nn_lowering/exp.py`：通过。
- `git -C /home/lfr/kernelcode_generate/wt-20260423-pass-infra-s5 diff --check`：通过。
Diff 反推自测：
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260423-pass-infra-s5:/home/lfr/kernelcode_generate pytest -q test/pass/nn_lowering/exp.py -ra`：`3 passed, 1 warning`。
- 说明：本轮 review 退回点明确点名 `select_cast_lowering` 对应的 `exp.py` 缺失，因此只补这条 residual diff 直接对应的 pytest 证据，不重复展开已在前序 build 记录中通过的大集合 child pytest。
合同验收（如适用）：
- 本轮未执行 `expectation`；`expectation/pass/lowing/nn_lowering/**` 仍只作合同验收资产单列，不计入 `Diff 反推自测`。
真实自检：
- 本轮没有扩大 diff 范围，也没有再改 `select_cast_lowering` 逻辑；只补 review 指出的证据缺口。
- 当前 `select_cast_lowering` 对应的 `select` / `cast` / `exp` 三支 pytest 证据链已经闭合：前序记录保留了 `select.py`、`cast.py`，本轮补齐了 `exp.py`。
- 当前一线可改进点已收口；这轮没有新的代码层问题需要继续改。
结论：
- `select_cast_lowering` 对应的 `exp.py` `Diff 反推自测` 已补齐。
- 当前任务可回流 `review`。

时间：2026-04-24 11:39 +0800
经办人：不要啊教练
任务：T-20260423-432a6289
任务目标：复核 build 已补齐 select_cast_lowering 对应 exp.py 的 Diff 反推自测后，S5 nn_lowering child 模块 surviving 接口与直接消费者是否已闭合。
执行前阅读记录：
- 已重读 [`TODO.md`](/home/lfr/kernelcode_generate/TODO.md:7) 当前任务行、[`ARCHITECTURE/plan/pass_infrastructure_refactor_green_plan.md`](/home/lfr/kernelcode_generate/ARCHITECTURE/plan/pass_infrastructure_refactor_green_plan.md:580) 的 `S5` 正文、全局完成态/验收设计，以及当前任务记录中的最新 `build/review` 条目。
- 已重点复核 [`kernel_gen/passes/lowering/nn_lowering/select_cast_lowering.py`](/home/lfr/kernelcode_generate/wt-20260423-pass-infra-s5/kernel_gen/passes/lowering/nn_lowering/select_cast_lowering.py)、[`test/pass/nn_lowering/public_name.py`](/home/lfr/kernelcode_generate/wt-20260423-pass-infra-s5/test/pass/nn_lowering/public_name.py)、[`test/pass/nn_lowering/select.py`](/home/lfr/kernelcode_generate/wt-20260423-pass-infra-s5/test/pass/nn_lowering/select.py)、[`test/pass/nn_lowering/cast.py`](/home/lfr/kernelcode_generate/wt-20260423-pass-infra-s5/test/pass/nn_lowering/cast.py)、[`test/pass/nn_lowering/exp.py`](/home/lfr/kernelcode_generate/wt-20260423-pass-infra-s5/test/pass/nn_lowering/exp.py)。
真实审查：
- 已确认 build 记录补上了 [`test/pass/nn_lowering/exp.py`](/home/lfr/kernelcode_generate/wt-20260423-pass-infra-s5/test/pass/nn_lowering/exp.py) 的 `Diff 反推自测`，`select_cast_lowering` 对应的 `select/cast/exp` 三支 pytest 运行证据现在都在记录里。
- 但 surviving public path 仍未完全闭合：[`test/pass/nn_lowering/select.py`](/home/lfr/kernelcode_generate/wt-20260423-pass-infra-s5/test/pass/nn_lowering/select.py:35) 与 [`cast.py`](/home/lfr/kernelcode_generate/wt-20260423-pass-infra-s5/test/pass/nn_lowering/cast.py:42) 都已经切到 canonical `from kernel_gen.passes.lowering.nn_lowering import NnLoweringPass`，而 [`exp.py`](/home/lfr/kernelcode_generate/wt-20260423-pass-infra-s5/test/pass/nn_lowering/exp.py:29) 仍然从旧包级入口 `kernel_gen.passes.lowering` 导入 `NnLoweringPass` / `NnLoweringError`。
- [`spec/pass/lowering/nn_lowering/spec.md`](/home/lfr/kernelcode_generate/wt-20260423-pass-infra-s5/spec/pass/lowering/nn_lowering/spec.md:36) 已把唯一 canonical import path 写死为 `kernel_gen.passes.lowering.nn_lowering.NnLoweringPass`。当前 `exp.py` 作为 `select_cast_lowering` 直接消费者仍保留旧导入，和 `public_name.py` 中的 surviving public path 断言不一致。
问题清单：
- `P2` [`test/pass/nn_lowering/exp.py`](/home/lfr/kernelcode_generate/wt-20260423-pass-infra-s5/test/pass/nn_lowering/exp.py:29)、[`spec/pass/lowering/nn_lowering/spec.md`](/home/lfr/kernelcode_generate/wt-20260423-pass-infra-s5/spec/pass/lowering/nn_lowering/spec.md:36)、[`test/pass/nn_lowering/public_name.py`](/home/lfr/kernelcode_generate/wt-20260423-pass-infra-s5/test/pass/nn_lowering/public_name.py:78)
  - 现象：`exp.py` 仍从旧包级入口 `kernel_gen.passes.lowering` 导入 `NnLoweringPass` / `NnLoweringError`，没有像 `select.py` / `cast.py` 一样切到 canonical `kernel_gen.passes.lowering.nn_lowering`。
  - 风险：S5 已冻结 surviving public path，但 `select_cast_lowering` 的直接消费者仍保留一条旧导入路径，consumer matrix 证据链不闭合。
  - 建议：把 [`test/pass/nn_lowering/exp.py`](/home/lfr/kernelcode_generate/wt-20260423-pass-infra-s5/test/pass/nn_lowering/exp.py) 的导入切到 canonical 子模块，再回流 `review`。
可改进点：
- `select/cast/exp` 作为同一 child 模块测试面，应统一使用 canonical `kernel_gen.passes.lowering.nn_lowering` 导入；当前只剩 `exp.py` 没对齐。
Diff 反推审查：
- 复核最新 build 补齐后的直接相关 pytest：`PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260423-pass-infra-s5:/home/lfr/kernelcode_generate pytest -q /home/lfr/kernelcode_generate/wt-20260423-pass-infra-s5/test/pass/nn_lowering/public_name.py /home/lfr/kernelcode_generate/wt-20260423-pass-infra-s5/test/pass/nn_lowering/select.py /home/lfr/kernelcode_generate/wt-20260423-pass-infra-s5/test/pass/nn_lowering/cast.py /home/lfr/kernelcode_generate/wt-20260423-pass-infra-s5/test/pass/nn_lowering/exp.py -ra`
  - 结果：`11 passed, 1 warning in 0.21s`。
- `git -C /home/lfr/kernelcode_generate/wt-20260423-pass-infra-s5 diff --check`
  - 结果：通过。
合同验收（单列）：
- 本轮未执行 `expectation`；`expectation/pass/lowing/nn_lowering/**` 继续只作合同验收资产单列，不计入 diff 反推测试。
自检：
- 已按当前口径重新完成真实审查与 `Diff 反推审查`，重点复核 build 最新补记后的 surviving public path 与直接消费者一致性。
- 当前唯一明确可改进点是 `exp.py` 仍使用旧包级导入；这是直接可执行且和 S5 canonical public path 目标直接相关的残留问题。
结论：
- `需修改`。
- build 已补齐 `exp.py` 的 `Diff 反推自测`，但 [`test/pass/nn_lowering/exp.py`](/home/lfr/kernelcode_generate/wt-20260423-pass-infra-s5/test/pass/nn_lowering/exp.py:29) 仍保留旧包级导入，尚未和 S5 冻结的 canonical `kernel_gen.passes.lowering.nn_lowering.NnLoweringPass` 完全对齐，需要先收口这条直接消费者路径再回流 `review`。

时间：2026-04-24 04:37 +0800
经办人：jcc你莫辜负
任务：T-20260423-432a6289
任务目标：补齐 S5 `select_cast_lowering` 对应 [`test/pass/nn_lowering/exp.py`](test/pass/nn_lowering/exp.py) 的 canonical import，统一收口到 `kernel_gen.passes.lowering.nn_lowering` 后回流 `review`。
执行前阅读记录：
- 已重读 [`TODO.md`](TODO.md) 当前任务行、[`ARCHITECTURE/plan/pass_infrastructure_refactor_green_plan.md`](ARCHITECTURE/plan/pass_infrastructure_refactor_green_plan.md) 的 `S5` 正文、全局完成态/验收设计，以及当前任务记录里的前序 `build/review` 条目。
- 已对照 review 退回点复核 [`test/pass/nn_lowering/exp.py`](test/pass/nn_lowering/exp.py)、[`test/pass/nn_lowering/select.py`](test/pass/nn_lowering/select.py)、[`test/pass/nn_lowering/cast.py`](test/pass/nn_lowering/cast.py)、[`test/pass/nn_lowering/public_name.py`](test/pass/nn_lowering/public_name.py) 与 [`spec/pass/lowering/nn_lowering/spec.md`](spec/pass/lowering/nn_lowering/spec.md) 当前口径。
最小功能闭环：
- 只把 [`test/pass/nn_lowering/exp.py`](test/pass/nn_lowering/exp.py) 的 `NnLoweringPass` / `NnLoweringError` 导入切到 canonical `kernel_gen.passes.lowering.nn_lowering`，让 `select` / `cast` / `exp` 三个直接消费者使用同一公开入口。
- 不改 `nn_lowering` 实现、不改 `expectation`，只收这条 review 指出的直接消费残留。
改动：
- 更新 [`test/pass/nn_lowering/exp.py`](test/pass/nn_lowering/exp.py)：
  - `from kernel_gen.passes.lowering import NnLoweringError, NnLoweringPass`
  - 调整为 `from kernel_gen.passes.lowering.nn_lowering import NnLoweringError, NnLoweringPass`
验证：
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260423-pass-infra-s5:/home/lfr/kernelcode_generate pytest -q test/pass/nn_lowering/public_name.py test/pass/nn_lowering/select.py test/pass/nn_lowering/cast.py test/pass/nn_lowering/exp.py -ra`：`11 passed, 1 warning in 0.20s`。
- `python3 -m py_compile test/pass/nn_lowering/exp.py`：通过。
- `rg -n "from kernel_gen\\.passes\\.lowering import NnLowering(Error|Pass)" test/pass/nn_lowering/exp.py`：无命中。
- `git -C /home/lfr/kernelcode_generate/wt-20260423-pass-infra-s5 diff --check`：通过。
Diff 反推自测：
- 当前实际 diff 只触到 [`test/pass/nn_lowering/exp.py`](test/pass/nn_lowering/exp.py)，所以直接运行 `exp.py` 所在的 `select/cast/exp/public_name` 消费者矩阵，确认 canonical import 已统一到 `kernel_gen.passes.lowering.nn_lowering`。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260423-pass-infra-s5:/home/lfr/kernelcode_generate pytest -q test/pass/nn_lowering/public_name.py test/pass/nn_lowering/select.py test/pass/nn_lowering/cast.py test/pass/nn_lowering/exp.py -ra`：`11 passed, 1 warning in 0.20s`。
合同验收（如适用）：
- 本轮未执行 `expectation`；`expectation/pass/lowering/nn_lowering/**` 继续只作合同验收资产单列，不计入 `Diff 反推自测`。
自检：
- 已按当前边界只处理 review 明确指出的 `exp.py` 旧导入残留，没有扩大到实现或其他测试面。
- 已核对 `spec`、`public_name.py`、`select.py`、`cast.py` 与 `exp.py` 的公开入口口径，现在这组三个直接消费者都统一走 `kernel_gen.passes.lowering.nn_lowering`。
- 这轮没有引入新的兼容层、重复导入或额外别名；当前一线可执行问题已收住。
结论：
- `build` 完成。
- `exp.py` 的 canonical import 已和 `select.py` / `cast.py`、`spec/pass/lowering/nn_lowering/spec.md` 收口一致，可回流 `review`。

时间：2026-04-24 04:40 +0800
经办人：jcc你莫辜负
任务：T-20260423-432a6289
任务目标：复核 S5 `select_cast_lowering` 对应 `exp.py` canonical import 修复后，`nn_lowering` 直接消费者矩阵是否已完全收口。
执行前阅读记录：
- 已重读 [`TODO.md`](TODO.md) 当前任务行、[`ARCHITECTURE/plan/pass_infrastructure_refactor_green_plan.md`](ARCHITECTURE/plan/pass_infrastructure_refactor_green_plan.md) 的 `S5` 正文、全局完成态/验收设计，以及当前任务记录中的前序 `build/review` 条目。
- 已复核 [`spec/pass/lowering/nn_lowering/spec.md`](spec/pass/lowering/nn_lowering/spec.md)、[`test/pass/nn_lowering/public_name.py`](test/pass/nn_lowering/public_name.py)、[`test/pass/nn_lowering/select.py`](test/pass/nn_lowering/select.py)、[`test/pass/nn_lowering/cast.py`](test/pass/nn_lowering/cast.py)、[`test/pass/nn_lowering/exp.py`](test/pass/nn_lowering/exp.py)、[`test/pass/nn_lowering/test_reduce_lowering.py`](test/pass/nn_lowering/test_reduce_lowering.py) 当前现场。
真实审查：
- 已确认最新 build 已把 [`test/pass/nn_lowering/exp.py`](test/pass/nn_lowering/exp.py) 切到 canonical `kernel_gen.passes.lowering.nn_lowering`，并且 `select.py` / `cast.py` / `exp.py` / `public_name.py` 这一组直接消费者运行通过。
- 但 `nn_lowering` 直接消费者矩阵仍未完全收口：[`test/pass/nn_lowering/test_reduce_lowering.py`](test/pass/nn_lowering/test_reduce_lowering.py) 第 41 行仍保留 `from kernel_gen.passes.lowering import NnLoweringError, NnLoweringPass`，与 [`spec/pass/lowering/nn_lowering/spec.md`](spec/pass/lowering/nn_lowering/spec.md) 已固定的唯一 canonical import path `kernel_gen.passes.lowering.nn_lowering.NnLoweringPass` 不一致。
问题清单：
- `P2` [`test/pass/nn_lowering/test_reduce_lowering.py`](test/pass/nn_lowering/test_reduce_lowering.py)
  - 现象：`reduce family` 的直接 pytest 消费者仍从旧包级入口 `kernel_gen.passes.lowering` 导入 `NnLoweringPass` / `NnLoweringError`。
  - 风险：S5 已把 `nn_lowering` 的公开入口收口到 canonical 子模块；当前 `reduce` 这支直接消费者仍保留旧导入，consumer matrix 还没有闭合。
  - 建议：把 [`test/pass/nn_lowering/test_reduce_lowering.py`](test/pass/nn_lowering/test_reduce_lowering.py) 同步切到 `from kernel_gen.passes.lowering.nn_lowering import NnLoweringError, NnLoweringPass`，再回流 `review`。
可改进点：
- 除 `select/cast/exp` 外，`reduce` 这支直接 pytest 消费者也应跟随 S5 canonical public path 统一导入口径；当前还有一条一线可执行的旧导入残留。
Diff 反推审查：
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260423-pass-infra-s5:/home/lfr/kernelcode_generate pytest -q /home/lfr/kernelcode_generate/wt-20260423-pass-infra-s5/test/pass/nn_lowering/public_name.py /home/lfr/kernelcode_generate/wt-20260423-pass-infra-s5/test/pass/nn_lowering/select.py /home/lfr/kernelcode_generate/wt-20260423-pass-infra-s5/test/pass/nn_lowering/cast.py /home/lfr/kernelcode_generate/wt-20260423-pass-infra-s5/test/pass/nn_lowering/exp.py -ra`
  - 结果：`11 passed, 1 warning in 0.21s`。
- `git -C /home/lfr/kernelcode_generate/wt-20260423-pass-infra-s5 diff --check`
  - 结果：通过。
合同验收（单列）：
- 本轮未执行 `expectation`；`expectation/pass/lowering/nn_lowering/**` 继续只作合同验收资产单列，不计入 diff 反推测试。
自检：
- 已按当前审查口径完成真实审查与 `Diff 反推审查`，并继续追到同一任务边界内的直接 pytest 消费者矩阵。
- 当前仍能明确指出一条直接、可执行的改进项：`test_reduce_lowering.py` 没有对齐 canonical import。
- 这条问题不在 `expectation`，也不涉及额外实现变更，仍属于本轮 S5 public import 收口范围。
结论：
- `需修改`。
- `exp.py` 已收口，但 [`test/pass/nn_lowering/test_reduce_lowering.py`](test/pass/nn_lowering/test_reduce_lowering.py) 仍保留旧包级导入，build 需补齐这条 `reduce` 直接消费者的 canonical import 后再回流 `review`。

时间：2026-04-24 04:41 +0800
经办人：jcc你莫辜负
任务：T-20260423-432a6289
任务目标：补齐 `reduce` 直接消费者 [`test/pass/nn_lowering/test_reduce_lowering.py`](test/pass/nn_lowering/test_reduce_lowering.py) 的 canonical import，统一收口到 `kernel_gen.passes.lowering.nn_lowering` 后回流 `review`。
执行前阅读记录：
- 已重读当前任务记录里最新 `review` 条目，确认本轮唯一待收口问题是 [`test/pass/nn_lowering/test_reduce_lowering.py`](test/pass/nn_lowering/test_reduce_lowering.py) 第 41 行仍走旧包级导入。
- 已对照 [`spec/pass/lowering/nn_lowering/spec.md`](spec/pass/lowering/nn_lowering/spec.md) 的 canonical import 口径与 [`test/pass/nn_lowering/public_name.py`](test/pass/nn_lowering/public_name.py) 当前断言，确认这条 `reduce` pytest 仍在同一 S5 public import 收口范围内。
最小功能闭环：
- 只更新 [`test/pass/nn_lowering/test_reduce_lowering.py`](test/pass/nn_lowering/test_reduce_lowering.py) 的 `NnLoweringPass` / `NnLoweringError` 导入，让 `reduce` 这支直接消费者与 `select` / `cast` / `exp` 一样统一走 `kernel_gen.passes.lowering.nn_lowering`。
- 不改 `nn_lowering` 实现、不改 `spec`、不改 `expectation`，只收 review 指出的这条旧导入残留。
改动：
- 更新 [`test/pass/nn_lowering/test_reduce_lowering.py`](test/pass/nn_lowering/test_reduce_lowering.py)：
  - `from kernel_gen.passes.lowering import NnLoweringError, NnLoweringPass`
  - 调整为 `from kernel_gen.passes.lowering.nn_lowering import NnLoweringError, NnLoweringPass`
验证：
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260423-pass-infra-s5:/home/lfr/kernelcode_generate pytest -q test/pass/nn_lowering/public_name.py test/pass/nn_lowering/test_reduce_lowering.py -ra`：`15 passed, 1 warning in 0.20s`。
- `python3 -m py_compile test/pass/nn_lowering/test_reduce_lowering.py`：通过。
- `rg -n "from kernel_gen\\.passes\\.lowering import NnLowering(Error|Pass)" test/pass/nn_lowering`：无命中。
- `git -C /home/lfr/kernelcode_generate/wt-20260423-pass-infra-s5 diff --check`：通过。
Diff 反推自测：
- 当前实际 diff 只触到 [`test/pass/nn_lowering/test_reduce_lowering.py`](test/pass/nn_lowering/test_reduce_lowering.py)，因此按直接消费者矩阵补跑 `public_name.py + test_reduce_lowering.py`，确认 canonical import 与公开断言保持一致。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260423-pass-infra-s5:/home/lfr/kernelcode_generate pytest -q test/pass/nn_lowering/public_name.py test/pass/nn_lowering/test_reduce_lowering.py -ra`：`15 passed, 1 warning in 0.20s`。
合同验收（如适用）：
- 本轮未执行 `expectation`；`expectation/pass/lowering/nn_lowering/**` 继续只作合同验收资产单列，不计入 `Diff 反推自测`。
自检：
- 已按当前边界只处理 `reduce` 直接消费者的旧导入，没有扩大到实现或无关测试面。
- 已核对 `spec`、`public_name.py` 与 `test_reduce_lowering.py` 的公开入口口径，现在 `select` / `cast` / `exp` / `reduce` 四支直接 pytest 消费者都统一走 `kernel_gen.passes.lowering.nn_lowering`。
- 这轮没有引入新的兼容层、重复导入或额外别名；当前能明确指出的直接消费者旧导入残留已经清掉。
结论：
- `build` 完成。
- `reduce` 这支直接消费者的 canonical import 已补齐，可回流 `review`。

---

时间：2026-04-24 04:57 +0800
经办人：提莫炖蘑菇
任务：T-20260423-432a6289
任务目标：复核 S5 `nn_lowering` 直接 pytest 消费者 `select/cast/exp/reduce` 是否都已统一到 canonical `kernel_gen.passes.lowering.nn_lowering`，并确认 consumer matrix 与记录口径收口
执行前阅读记录：
- 已重读 [`TODO.md`](/home/lfr/kernelcode_generate/TODO.md) 当前任务行，确认本轮为 `review`。
- 已重读计划书 [`ARCHITECTURE/plan/pass_infrastructure_refactor_green_plan.md`](/home/lfr/kernelcode_generate/ARCHITECTURE/plan/pass_infrastructure_refactor_green_plan.md) 的 `S5`、全局完成态与验收设计。
- 已重读当前任务记录中的前序 `spec/build/review/build/review/build` 条目，确认本轮唯一待验证点是 `select/cast/exp/reduce` 直接消费者与 consumer matrix 是否完全切到 canonical path。
真实审查：
- 现场 residual diff 覆盖了 `nn_lowering` child 实现、对应 spec 和直接 pytest 消费者；本轮 review 重点核对 `select/cast/exp/reduce` 与 `public_name.py` 的 import / export 行为。
- 当前 `select/cast/exp/reduce` 直接消费者都已统一到 canonical 子模块路径：
  - [`test/pass/nn_lowering/select.py`](/home/lfr/kernelcode_generate/wt-20260423-pass-infra-s5/test/pass/nn_lowering/select.py)
  - [`test/pass/nn_lowering/cast.py`](/home/lfr/kernelcode_generate/wt-20260423-pass-infra-s5/test/pass/nn_lowering/cast.py)
  - [`test/pass/nn_lowering/exp.py`](/home/lfr/kernelcode_generate/wt-20260423-pass-infra-s5/test/pass/nn_lowering/exp.py)
  - [`test/pass/nn_lowering/test_reduce_lowering.py`](/home/lfr/kernelcode_generate/wt-20260423-pass-infra-s5/test/pass/nn_lowering/test_reduce_lowering.py)
  都改为 `from kernel_gen.passes.lowering.nn_lowering import NnLoweringPass / NnLoweringError`。
- [`test/pass/nn_lowering/public_name.py`](/home/lfr/kernelcode_generate/wt-20260423-pass-infra-s5/test/pass/nn_lowering/public_name.py) 已把 child 模块 surviving export 明确收口为：
  - `element_binary_patterns()`
  - `dma_structured_patterns()`
  - `select_cast_patterns()`
  - `matmul_img2col_patterns()`
  - `reduce_softmax_patterns()`
- 现场 `rg` 复核未再发现：
  - `from kernel_gen.passes.lowering import NnLoweringPass/NnLoweringError`
  - `lower_select_cast_family / lower_reduce_softmax_family / lower_element_binary_family / lower_dma_structured_family / lower_matmul_img2col_family`
  出现在当前直接消费者或实现公开面。
Diff 反推审查：
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260423-pass-infra-s5:/home/lfr/kernelcode_generate pytest -q test/pass/nn_lowering/public_name.py test/pass/nn_lowering/select.py test/pass/nn_lowering/cast.py test/pass/nn_lowering/exp.py test/pass/nn_lowering/test_reduce_lowering.py test/pass/test_pass_registry.py -ra`
  - 结果：`54 passed, 1 warning`
- `python3 -m py_compile test/pass/nn_lowering/public_name.py test/pass/nn_lowering/select.py test/pass/nn_lowering/cast.py test/pass/nn_lowering/exp.py test/pass/nn_lowering/test_reduce_lowering.py kernel_gen/passes/lowering/nn_lowering/element_binary_lowering.py kernel_gen/passes/lowering/nn_lowering/select_cast_lowering.py kernel_gen/passes/lowering/nn_lowering/reduce_softmax_lowering.py kernel_gen/passes/lowering/nn_lowering/dma_structured_lowering.py kernel_gen/passes/lowering/nn_lowering/matmul_img2col_lowering.py`
  - 结果：通过
- `git -C /home/lfr/kernelcode_generate/wt-20260423-pass-infra-s5 diff --check`
  - 结果：通过
合同验收单列：
- 本轮未执行 `expectation`；`expectation/pass/lowing/nn_lowering/**` 继续只作为合同验收资产单列，不计入 `Diff 反推审查`。
自检：
- 已按要求先读计划阶段、全局完成态、验收设计和前序记录，再结合现场 diff、矩阵扫描与 pytest 结果做复审。
- 本轮没有把 `expectation` 混进 diff 反推测试，也没有把 review 扩大到 `nn_lowering` 行为重写之外的额外范围。
- 当前唯一 warning 仍是 xDSL 上游 `irdl_options list` 弃用告警，不属于本仓当前切片可处理问题。
可改进点：
- 当前切片内未再发现可直接执行的一线改进点；`select/cast/exp/reduce` 直接消费者与 consumer matrix 已按 S5 canonical public path 收口。
结论：
- 本轮结论为 `通过`。
- S5 当前 diff 中 `nn_lowering` 直接 pytest 消费者 `select/cast/exp/reduce` 已统一到 canonical `kernel_gen.passes.lowering.nn_lowering`，child 模块 surviving export 与 consumer matrix 证据链闭合，可按流程进入 `merge`。

---

时间：2026-04-24 13:45 +0800
经办人：李白
任务：T-20260423-432a6289
任务目标：按 `merge` 口径把 `pass_infra S5` 的 `nn_lowering` child 模块 surviving 接口、spec 与直接 pytest 消费者矩阵收口到主线，并同步确认主仓状态
执行前阅读记录：
- 已重读 [`TODO.md`](/home/lfr/kernelcode_generate/TODO.md) 当前任务行，确认本轮状态为 `merge`，`worktree` 为 [`wt-20260423-pass-infra-s5`](/home/lfr/kernelcode_generate/wt-20260423-pass-infra-s5)。
- 已重读 [`ARCHITECTURE/plan/pass_infrastructure_refactor_green_plan.md`](/home/lfr/kernelcode_generate/ARCHITECTURE/plan/pass_infrastructure_refactor_green_plan.md) 中 `S5` 正文、全局完成态、验收设计和消费者迁移矩阵。
- 已重读本任务前序 `spec/build/review` 记录，确认审查记录已包含 `Diff 反推审查`，执行记录已包含 `执行前阅读记录`、`最小功能闭环`、`自检` 与 `Diff 反推自测`。
- 已核对当前现场 diff：只包含 `nn_lowering` child 模块 surviving 接口、对应 spec 与 `select/cast/exp/reduce` / `element_*` 直接 pytest 消费者，不包含 `expectation` 改动。
真实收口过程：
- 在 [`wt-20260423-pass-infra-s5`](/home/lfr/kernelcode_generate/wt-20260423-pass-infra-s5) 内先执行 `git fetch origin`，再以 `git rebase --autostash origin/main` 重放到最新主线；重放成功，无冲突。
- 在最新主线现场复跑本轮 review 已锁定的 `nn_lowering` 直接消费者矩阵，确认 `public_name.py`、`test_lowering_nn_lowering.py`、`test_nn_lowering_private_helpers.py`、`select/cast/exp/reduce` 与 `element_*` 系列 pytest 没被主线近期变更冲掉。
- 本次纳入 merge 的文件为：
  - [`kernel_gen/passes/lowering/nn_lowering/dma_structured_lowering.py`](/home/lfr/kernelcode_generate/wt-20260423-pass-infra-s5/kernel_gen/passes/lowering/nn_lowering/dma_structured_lowering.py)
  - [`kernel_gen/passes/lowering/nn_lowering/element_binary_lowering.py`](/home/lfr/kernelcode_generate/wt-20260423-pass-infra-s5/kernel_gen/passes/lowering/nn_lowering/element_binary_lowering.py)
  - [`kernel_gen/passes/lowering/nn_lowering/matmul_img2col_lowering.py`](/home/lfr/kernelcode_generate/wt-20260423-pass-infra-s5/kernel_gen/passes/lowering/nn_lowering/matmul_img2col_lowering.py)
  - [`kernel_gen/passes/lowering/nn_lowering/reduce_softmax_lowering.py`](/home/lfr/kernelcode_generate/wt-20260423-pass-infra-s5/kernel_gen/passes/lowering/nn_lowering/reduce_softmax_lowering.py)
  - [`kernel_gen/passes/lowering/nn_lowering/select_cast_lowering.py`](/home/lfr/kernelcode_generate/wt-20260423-pass-infra-s5/kernel_gen/passes/lowering/nn_lowering/select_cast_lowering.py)
  - [`spec/pass/lowering/nn_lowering/spec.md`](/home/lfr/kernelcode_generate/wt-20260423-pass-infra-s5/spec/pass/lowering/nn_lowering/spec.md)
  - [`spec/pass/lowering/nn_lowering/dma_structured_lowering.md`](/home/lfr/kernelcode_generate/wt-20260423-pass-infra-s5/spec/pass/lowering/nn_lowering/dma_structured_lowering.md)
  - [`spec/pass/lowering/nn_lowering/element_binary_lowering.md`](/home/lfr/kernelcode_generate/wt-20260423-pass-infra-s5/spec/pass/lowering/nn_lowering/element_binary_lowering.md)
  - [`spec/pass/lowering/nn_lowering/matmul_img2col_lowering.md`](/home/lfr/kernelcode_generate/wt-20260423-pass-infra-s5/spec/pass/lowering/nn_lowering/matmul_img2col_lowering.md)
  - [`spec/pass/lowering/nn_lowering/reduce_softmax_lowering.md`](/home/lfr/kernelcode_generate/wt-20260423-pass-infra-s5/spec/pass/lowering/nn_lowering/reduce_softmax_lowering.md)
  - [`spec/pass/lowering/nn_lowering/select_cast_lowering.md`](/home/lfr/kernelcode_generate/wt-20260423-pass-infra-s5/spec/pass/lowering/nn_lowering/select_cast_lowering.md)
  - [`test/pass/nn_lowering/public_name.py`](/home/lfr/kernelcode_generate/wt-20260423-pass-infra-s5/test/pass/nn_lowering/public_name.py)
  - [`test/pass/nn_lowering/test_nn_lowering_private_helpers.py`](/home/lfr/kernelcode_generate/wt-20260423-pass-infra-s5/test/pass/nn_lowering/test_nn_lowering_private_helpers.py)
  - [`test/pass/nn_lowering/select.py`](/home/lfr/kernelcode_generate/wt-20260423-pass-infra-s5/test/pass/nn_lowering/select.py)
  - [`test/pass/nn_lowering/cast.py`](/home/lfr/kernelcode_generate/wt-20260423-pass-infra-s5/test/pass/nn_lowering/cast.py)
  - [`test/pass/nn_lowering/exp.py`](/home/lfr/kernelcode_generate/wt-20260423-pass-infra-s5/test/pass/nn_lowering/exp.py)
  - [`test/pass/nn_lowering/test_reduce_lowering.py`](/home/lfr/kernelcode_generate/wt-20260423-pass-infra-s5/test/pass/nn_lowering/test_reduce_lowering.py)
  - [`test/pass/nn_lowering/element_binary_add.py`](/home/lfr/kernelcode_generate/wt-20260423-pass-infra-s5/test/pass/nn_lowering/element_binary_add.py)
  - [`test/pass/nn_lowering/element_binary_div.py`](/home/lfr/kernelcode_generate/wt-20260423-pass-infra-s5/test/pass/nn_lowering/element_binary_div.py)
  - [`test/pass/nn_lowering/element_binary_mul.py`](/home/lfr/kernelcode_generate/wt-20260423-pass-infra-s5/test/pass/nn_lowering/element_binary_mul.py)
  - [`test/pass/nn_lowering/element_binary_sub.py`](/home/lfr/kernelcode_generate/wt-20260423-pass-infra-s5/test/pass/nn_lowering/element_binary_sub.py)
  - [`test/pass/nn_lowering/element_binary_truediv.py`](/home/lfr/kernelcode_generate/wt-20260423-pass-infra-s5/test/pass/nn_lowering/element_binary_truediv.py)
  - [`test/pass/nn_lowering/element_compare_eq.py`](/home/lfr/kernelcode_generate/wt-20260423-pass-infra-s5/test/pass/nn_lowering/element_compare_eq.py)
  - [`test/pass/nn_lowering/element_compare_ge.py`](/home/lfr/kernelcode_generate/wt-20260423-pass-infra-s5/test/pass/nn_lowering/element_compare_ge.py)
  - [`test/pass/nn_lowering/element_compare_gt.py`](/home/lfr/kernelcode_generate/wt-20260423-pass-infra-s5/test/pass/nn_lowering/element_compare_gt.py)
  - [`test/pass/nn_lowering/element_compare_le.py`](/home/lfr/kernelcode_generate/wt-20260423-pass-infra-s5/test/pass/nn_lowering/element_compare_le.py)
  - [`test/pass/nn_lowering/element_compare_lt.py`](/home/lfr/kernelcode_generate/wt-20260423-pass-infra-s5/test/pass/nn_lowering/element_compare_lt.py)
  - [`test/pass/nn_lowering/element_compare_ne.py`](/home/lfr/kernelcode_generate/wt-20260423-pass-infra-s5/test/pass/nn_lowering/element_compare_ne.py)
  - 当前任务记录
验证：
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260423-pass-infra-s5:/home/lfr/kernelcode_generate pytest -q /home/lfr/kernelcode_generate/wt-20260423-pass-infra-s5/test/pass/nn_lowering/public_name.py /home/lfr/kernelcode_generate/wt-20260423-pass-infra-s5/test/pass/nn_lowering/test_lowering_nn_lowering.py /home/lfr/kernelcode_generate/wt-20260423-pass-infra-s5/test/pass/nn_lowering/test_nn_lowering_private_helpers.py /home/lfr/kernelcode_generate/wt-20260423-pass-infra-s5/test/pass/nn_lowering/select.py /home/lfr/kernelcode_generate/wt-20260423-pass-infra-s5/test/pass/nn_lowering/cast.py /home/lfr/kernelcode_generate/wt-20260423-pass-infra-s5/test/pass/nn_lowering/exp.py /home/lfr/kernelcode_generate/wt-20260423-pass-infra-s5/test/pass/nn_lowering/test_reduce_lowering.py /home/lfr/kernelcode_generate/wt-20260423-pass-infra-s5/test/pass/nn_lowering/element_binary_add.py /home/lfr/kernelcode_generate/wt-20260423-pass-infra-s5/test/pass/nn_lowering/element_binary_div.py /home/lfr/kernelcode_generate/wt-20260423-pass-infra-s5/test/pass/nn_lowering/element_binary_mul.py /home/lfr/kernelcode_generate/wt-20260423-pass-infra-s5/test/pass/nn_lowering/element_binary_sub.py /home/lfr/kernelcode_generate/wt-20260423-pass-infra-s5/test/pass/nn_lowering/element_binary_truediv.py /home/lfr/kernelcode_generate/wt-20260423-pass-infra-s5/test/pass/nn_lowering/element_compare_eq.py /home/lfr/kernelcode_generate/wt-20260423-pass-infra-s5/test/pass/nn_lowering/element_compare_ge.py /home/lfr/kernelcode_generate/wt-20260423-pass-infra-s5/test/pass/nn_lowering/element_compare_gt.py /home/lfr/kernelcode_generate/wt-20260423-pass-infra-s5/test/pass/nn_lowering/element_compare_le.py /home/lfr/kernelcode_generate/wt-20260423-pass-infra-s5/test/pass/nn_lowering/element_compare_lt.py /home/lfr/kernelcode_generate/wt-20260423-pass-infra-s5/test/pass/nn_lowering/element_compare_ne.py -ra`
  - 结果：`83 passed, 25 warnings`
- `python3 -m py_compile /home/lfr/kernelcode_generate/wt-20260423-pass-infra-s5/kernel_gen/passes/lowering/nn_lowering/dma_structured_lowering.py /home/lfr/kernelcode_generate/wt-20260423-pass-infra-s5/kernel_gen/passes/lowering/nn_lowering/element_binary_lowering.py /home/lfr/kernelcode_generate/wt-20260423-pass-infra-s5/kernel_gen/passes/lowering/nn_lowering/matmul_img2col_lowering.py /home/lfr/kernelcode_generate/wt-20260423-pass-infra-s5/kernel_gen/passes/lowering/nn_lowering/reduce_softmax_lowering.py /home/lfr/kernelcode_generate/wt-20260423-pass-infra-s5/kernel_gen/passes/lowering/nn_lowering/select_cast_lowering.py /home/lfr/kernelcode_generate/wt-20260423-pass-infra-s5/test/pass/nn_lowering/public_name.py /home/lfr/kernelcode_generate/wt-20260423-pass-infra-s5/test/pass/nn_lowering/test_nn_lowering_private_helpers.py /home/lfr/kernelcode_generate/wt-20260423-pass-infra-s5/test/pass/nn_lowering/select.py /home/lfr/kernelcode_generate/wt-20260423-pass-infra-s5/test/pass/nn_lowering/cast.py /home/lfr/kernelcode_generate/wt-20260423-pass-infra-s5/test/pass/nn_lowering/exp.py /home/lfr/kernelcode_generate/wt-20260423-pass-infra-s5/test/pass/nn_lowering/test_reduce_lowering.py /home/lfr/kernelcode_generate/wt-20260423-pass-infra-s5/test/pass/nn_lowering/element_binary_add.py /home/lfr/kernelcode_generate/wt-20260423-pass-infra-s5/test/pass/nn_lowering/element_binary_div.py /home/lfr/kernelcode_generate/wt-20260423-pass-infra-s5/test/pass/nn_lowering/element_binary_mul.py /home/lfr/kernelcode_generate/wt-20260423-pass-infra-s5/test/pass/nn_lowering/element_binary_sub.py /home/lfr/kernelcode_generate/wt-20260423-pass-infra-s5/test/pass/nn_lowering/element_binary_truediv.py /home/lfr/kernelcode_generate/wt-20260423-pass-infra-s5/test/pass/nn_lowering/element_compare_eq.py /home/lfr/kernelcode_generate/wt-20260423-pass-infra-s5/test/pass/nn_lowering/element_compare_ge.py /home/lfr/kernelcode_generate/wt-20260423-pass-infra-s5/test/pass/nn_lowering/element_compare_gt.py /home/lfr/kernelcode_generate/wt-20260423-pass-infra-s5/test/pass/nn_lowering/element_compare_le.py /home/lfr/kernelcode_generate/wt-20260423-pass-infra-s5/test/pass/nn_lowering/element_compare_lt.py /home/lfr/kernelcode_generate/wt-20260423-pass-infra-s5/test/pass/nn_lowering/element_compare_ne.py`
  - 结果：通过
- `rg -n "from kernel_gen\\.passes\\.lowering import NnLowering(Error|Pass)" /home/lfr/kernelcode_generate/wt-20260423-pass-infra-s5/test/pass/nn_lowering /home/lfr/kernelcode_generate/wt-20260423-pass-infra-s5/kernel_gen/passes/lowering/nn_lowering`
  - 结果：无命中
- `git -C /home/lfr/kernelcode_generate/wt-20260423-pass-infra-s5 diff --check`
  - 结果：通过
自检：
- 已按 merge 角色要求先读计划阶段、全局完成态、前序记录，再在最新主线现场收口，不是直接照搬旧 review 结论。
- 本次合并没有把 `expectation/pass/lowing/nn_lowering/**` 当作 diff 反推测试；它仍只在前序记录中单列为合同资产。
- 当前切片内未发现新的阻断项；warnings 仍是 xDSL 上游 deprecation，不属于本轮 merge 可直接处理问题。
结论：
- `pass_infra S5` 的 `nn_lowering` child 模块 surviving 接口、spec 与直接 pytest 消费者矩阵已完成 merge 收口，可提交主线并执行 `-done`。
