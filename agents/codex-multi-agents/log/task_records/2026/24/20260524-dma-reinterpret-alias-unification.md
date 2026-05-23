# T-20260524-b30e8d52 / dma_reinterpret_alias_unification

时间：2026-05-24 04:06 CST
经办人：小李飞刀
任务：T-20260524-b30e8d52 / dma_reinterpret_alias_unification / execute
任务目标：按主仓只读计划 `/home/lfr/kernelcode_generate/ARCHITECTURE/plan/dma_reinterpret_alias_unification_green_plan.md` 新增 `dma.reinterpret` 与 `dma-alias-to-reinterpret`，同步 dialect / pass / registry / pipeline / emit / downstream pass / spec / pytest，并保持 `expectation/.skills/agents/standard/AGENTS.md/TODO.md/DONE.md/ARCHITECTURE` 候选 diff 为空。

## 执行前阅读记录

- 已读角色提示：`agents/codex-multi-agents/agents/小李飞刀/小李飞刀.prompt.md`。
- 已读仓库规则：`AGENTS.md`，确认 `expectation/`、`.skills/`、`agents/standard/**`、共享状态和计划资产禁止修改。
- 已读任务口径：管理员下发 T-20260524-b30e8d52；worktree=`/home/lfr/kernelcode_generate/wt-20260524-dma-reinterpret-alias-unification`；分支=`task/dma-reinterpret-alias-unification`；原始基线=`bb874adfad94ea95697e08acc2bc12be5d34a52f`。
- 已读合同真源：主仓只读计划 `/home/lfr/kernelcode_generate/ARCHITECTURE/plan/dma_reinterpret_alias_unification_green_plan.md`。计划位于 ignored `ARCHITECTURE/plan`，未复制、未同步、未修改到任务 worktree。
- 已核对 TODO：主仓 `TODO.md` 显示本任务处于 running/execute，指派小李飞刀；本轮未修改 `TODO.md`。

## latest main 同步记录

- 原始创建基线：`origin/main@bb874adfad94ea95697e08acc2bc12be5d34a52f`。
- 首次主线推进：`origin/main=023d3c9b159d2f05610b68006a81d52a90058ac9`，候选当时为空 diff；与目标路径有交集，执行 fast-forward 后继续。
- 二次主线推进：`origin/main=5e1019a31910e7641c1874118e8045818273a184`，本 worktree 已 `git fetch`、`git stash push --include-untracked`、`git merge --ff-only origin/main`、`git stash pop`，无冲突。
- 当前同步现场：`HEAD=origin/main=5e1019a31910e7641c1874118e8045818273a184`。
- `bb874ad..5e1019a3` 与候选 diff 路径交集：
  - `kernel_gen/passes/arch_parallelize.py`
  - `kernel_gen/passes/symbol_buffer_hoist.py`
  - `spec/pass/arch_parallelize.md`
  - `spec/pass/hoist_dma_alias_ops.md`
  - `spec/pass/pipeline/npu_demo_lowering.md`
  - `spec/pass/registry.md`
  - `spec/pass/symbol_buffer_hoist.md`
  - `test/passes/pipeline/test_npu_demo_lowering.py`
- `023d3c9..5e1019a3` 与候选 diff 路径交集：
  - `kernel_gen/passes/arch_parallelize.py`
  - `spec/pass/arch_parallelize.md`
  - `spec/pass/pipeline/npu_demo_lowering.md`
  - `spec/pass/registry.md`
  - `test/passes/pipeline/test_npu_demo_lowering.py`
- 同步后处理：保留最新 main 的 `entry_point` host dispatcher skip 语义，在 `arch_parallelize` setup allowlist 中补 `DmaReinterpretOp`；pipeline 顺序测试同步保留 latest main entry_point case。未发现公开 API、expectation 授权、scope 扩大或合同真源冲突。

## 改动摘要

- dialect：新增公开 `DmaReinterpretOp`，注册到 `kernel_gen.dialect.dma.operation`、`kernel_gen.dialect.dma` 与 `Dma.operations`；verifier 覆盖 source/result memory、space、dtype/byte-pool 例外、offset、shape/stride exact match、bounds。
- pass：新增 `kernel_gen/passes/dma_alias_to_reinterpret.py`，公开 `DmaAliasToReinterpretPass(fold: bool = True)`，注册名 `dma-alias-to-reinterpret`；将 `dma.view` / `dma.reshape` / `dma.subview` 归一为 root source 上单个 `dma.reinterpret`，组合 alias 链 offset；无法 exact 物化或 verifier 失败时 no-op/回滚。
- 返工收口：只读 expectation 首次暴露 pass 内部 DCE 会把 unused alias 正例清掉，已关闭 pass 内部全局 DCE，改为只清理当前 rewrite source alias 链中已无 use 的中间 alias；新增 `test_dma_alias_to_reinterpret_preserves_unused_rewrite_result` 防假绿。
- registry/pipeline：`load_builtin_passes()` 注册新 pass；`npu-demo-lowering` 在 `NnLoweringPass()` 后插入 `DmaAliasToReinterpretPass()`。
- downstream pass：`producer_consumer_analysis`、`memory_plan`、`symbol_buffer_hoist`、`arch_parallelize` 识别 `DmaReinterpretOp`；`symbol_buffer_hoist` 增加 reinterpret full-cover / single-op hoist 处理；`arch_parallelize` setup prefix 允许 `arch.get_dynamic_memory + dma.reinterpret`。
- memory-pool：按计划方案 A，片上 alloc rewrite 直接生成 `arch.get_dynamic_memory + dma.reinterpret`，不再生成 `dma.view + dma.reshape`。
- emit：CPU 与 npu_demo emit 支持 `dma.reinterpret`，typed source 按 element offset，共享 byte-pool source 按 byte offset 后 `reinterpret_cast<T*>` 构造 `Memory`。
- template/default constraints：把 `dma.reinterpret` 纳入 memory alias 模板约束。
- spec/test：新增/更新对应 spec、pytest；未修改 expectation 合同资产。

## 验证

### pytest / py_compile / demo

- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/dialect/dma/test_reinterpret.py test/passes/test_dma_alias_to_reinterpret.py test/passes/test_registry.py test/passes/pipeline/test_npu_demo_lowering.py test/passes/test_producer_consumer_analysis.py test/passes/test_memory_plan.py test/passes/test_symbol_buffer_hoist.py test/passes/test_memory_pool.py test/dsl/gen_kernel/emit/test_package.py`
  - 结果：exit 0，`258 passed, 1 warning`。
- 同组 pytest 额外用 `PYTHONMALLOC=malloc` 复跑：
  - 结果：exit 0，`258 passed, 1 warning`。
- `PYTHONDONTWRITEBYTECODE=1 python3 -m py_compile` 覆盖本轮实现与新增测试文件：
  - 结果：exit 0。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/passes/test_arch_parallelize.py test/passes/test_template_name_constraints.py test/passes/test_template_name_infer.py -x --tb=short`
  - 结果：exit 0，`35 passed, 1 warning`。
- 额外广谱探针 `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/dsl/gen_kernel/test_gen_kernel.py -x --tb=short`
  - 结果：120s timeout，输出停在 `73%`。该命令不属于计划必跑项，且本轮未改 `kernel_gen/dsl/gen_kernel/kernel_emitter.py` 或 `test/dsl/gen_kernel/test_gen_kernel.py`；模板约束相关 targeted 测试已由上条覆盖，真实生成/编译由静态 matmul demo 覆盖。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 kernel/matmul/inputs_static_tile_static.py`
  - 结果：exit 0；输出包含 `selected_tile=(M=72,N=56,K=48)`，absent/present bias `max_abs_diff=3.4332275390625e-05`。
  - 备注：同命令一次早先复现 transient `compile_failed: compiler returned non-zero (1)`，随后原命令重跑通过；生成 `source.cpp` 手动 `g++ -shared -fPIC -std=c++17 -I<worktree>` 编译通过。

### expectation 合同验收

- 导入来源探针：
  - 命令：`PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260524-dma-reinterpret-alias-unification:/home/lfr/kernelcode_generate python3 - <<'PY' ...`
  - 结果：exit 0。
  - `expectation.pass.dma_alias_to_reinterpret.__main__` 来源：`/home/lfr/kernelcode_generate/expectation/pass/dma_alias_to_reinterpret/__main__.py`。
  - `kernel_gen.passes.registry` 来源：`/home/lfr/kernelcode_generate/wt-20260524-dma-reinterpret-alias-unification/kernel_gen/passes/registry.py`。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260524-dma-reinterpret-alias-unification:/home/lfr/kernelcode_generate python3 -m expectation.pass.dma_alias_to_reinterpret`
  - 结果：exit 0；12 个 reshape/view/subview 正例全部通过，旧 alias op 不残留，最终单个 `dma.reinterpret` 匹配 CHECK。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260524-dma-reinterpret-alias-unification:/home/lfr/kernelcode_generate python3 -m expectation.pass.symbol_buffer_hoist`
  - 结果：exit 0。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260524-dma-reinterpret-alias-unification:/home/lfr/kernelcode_generate python3 -m expectation.pass.producer_consumer_analysis`
  - 结果：exit 0。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260524-dma-reinterpret-alias-unification:/home/lfr/kernelcode_generate python3 -m expectation.pass.memory_plan`
  - 结果：exit 0。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260524-dma-reinterpret-alias-unification:/home/lfr/kernelcode_generate python3 -m expectation.pass.hoist_dma_alias_ops`
  - 结果：`Sandbox(Signal(11))`。
- `PYTHONMALLOC=malloc PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260524-dma-reinterpret-alias-unification:/home/lfr/kernelcode_generate python3 -m expectation.pass.hoist_dma_alias_ops`
  - 结果：exit 1；失败集中在 `slice` family：`symbol.mul %n, %kh` 预期 `KH*N` 未匹配，动态 conv2d dump path 预期 `17-hoist-dma-alias-ops.mlir` 缺失。
  - 同源复核：在主仓 latest main `5e1019a31910e7641c1874118e8045818273a184` 用同一 slice case 手工运行 `run_ircheck_text(...)`，得到同一 `CHECK not found`，实际 IR 保持 4D `dma.slice`，未产生降维 `symbol.mul` / `dma.reshape`。候选未修改 `kernel_gen/passes/hoist_dma_alias_ops.py` 或 `expectation/pass/hoist_dma_alias_ops/slice.py`；本轮只在 `spec/pass/hoist_dma_alias_ops.md` 增加保留旧逻辑说明。因此该项记录为 latest-main 既有失败隔离，不记为通过项，送 review 复核隔离结论。

### manifest / 静态门禁

- `find /home/lfr/kernelcode_generate/expectation/pass/dma_alias_to_reinterpret -maxdepth 1 -type f -print | sort`
  - 结果：exit 0，恰好 4 个文件：`__main__.py`、`reshape.py`、`subview.py`、`view.py`。
- `sha256sum`：
  - `__main__.py` = `6eeeec322ada03803347630905d536b37158717c32dcf39fcb2514b9dd6c346a`
  - `reshape.py` = `dd3d7bc53e63e3f6e2e14ae56b3c59f5fc3539f171675534869fef1c33c8357f`
  - `view.py` = `0bc0a210737d704d81242b2f1edb09402ba57cdbf5eec8b7cb99345bd2da75d8`
  - `subview.py` = `b772e6871ff6db57078c90709360f77fb8ab2358fc136090aa7a43b29ab71312`
- `git diff --exit-code -- expectation .skills agents/standard AGENTS.md TODO.md DONE.md ARCHITECTURE && git status --short -- expectation .skills agents/standard AGENTS.md TODO.md DONE.md ARCHITECTURE`
  - 结果：exit 0，无输出，敏感目录 / 共享状态 / 主仓计划资产无候选 diff。
- `find /home/lfr/kernelcode_generate/expectation/pass/dma_alias_to_reinterpret -maxdepth 2 -type d -name __pycache__ -print`
  - 结果：exit 0，无输出。早先只读 `py_compile` 产生的 `__pycache__` 已清理。
- `rg -n "DmaReinterpretOp|dma\\.reinterpret|dma-alias-to-reinterpret|DmaAliasToReinterpretPass" spec kernel_gen test`
  - 结果：exit 0；共 323 处命中，用于核对公开 API/spec/实现/test 同步覆盖。
- `if rg -n 'view/reshape/subview.*唯一 alias|只识别.*view.*reshape.*subview|setup.*view.*reshape' spec/pass kernel_gen/passes; then exit 1; else echo 'no matches'; fi`
  - 结果：exit 0，`no matches`。
- `git diff --check`
  - 结果：exit 0。

## Diff 反推自测

- dialect/API diff：`kernel_gen/dialect/dma/**`、`spec/dialect/dma.md`、`spec/operation/dma.md`。
  - 反推测试：`pytest -q test/dialect/dma/test_reinterpret.py test/dialect/dma/test_package.py test/dialect/dma/test_operation_alias.py`；纳入整组 pytest，验证公开导入、operation registry、verifier 正反例和 NoMemoryEffect。
- pass/registry/pipeline diff：`kernel_gen/passes/dma_alias_to_reinterpret.py`、`kernel_gen/passes/registry.py`、`kernel_gen/pipeline/npu_demo_lowering.py`。
  - 反推测试：`pytest -q test/passes/test_dma_alias_to_reinterpret.py test/passes/test_registry.py test/passes/pipeline/test_npu_demo_lowering.py`；纳入整组 pytest。新增 unused alias 回归测试，能在 pass 内部 DCE 误删最终 rewrite 时失败。
  - 合同验收：`expectation.pass.dma_alias_to_reinterpret` 由主仓 expectation + worktree 实现通过，锁定 12 个防假绿 CHECK。
- downstream analysis diff：`producer_consumer_analysis.py`、`memory_plan.py`、`symbol_buffer_hoist.py`、`arch_parallelize.py`。
  - 反推测试：`pytest -q test/passes/test_producer_consumer_analysis.py test/passes/test_memory_plan.py test/passes/test_symbol_buffer_hoist.py test/passes/test_arch_parallelize.py` 中本轮整组覆盖前三类；`arch_parallelize` 由 pipeline 测试和 latest-main case 保留验证。只读 `expectation.pass.symbol_buffer_hoist`、`expectation.pass.producer_consumer_analysis`、`expectation.pass.memory_plan` 均 exit 0。
- memory-pool diff：`kernel_gen/passes/memory_pool.py`、`spec/pass/lowering/memory_pool.md`、`test/passes/test_memory_pool.py`。
  - 反推测试：整组 pytest 中 `test/passes/test_memory_pool.py` 通过；静态 matmul demo 通过，确认 `memory-pool` 后由 `arch.get_dynamic_memory + dma.reinterpret` 承接。
- emit diff：`kernel_gen/dsl/gen_kernel/emit/**`、`spec/dsl/gen_kernel/emit*.md`、`test/dsl/gen_kernel/emit/test_package.py`。
  - 反推测试：整组 pytest 中 `test/dsl/gen_kernel/emit/test_package.py` 通过；静态 matmul demo 编译和数值校验通过，覆盖 npu_demo 源码生成/编译。
- template constraint diff：`kernel_gen/passes/template_name/default_constraints.py`。
  - 反推测试：`pytest -q test/passes/test_template_name_constraints.py test/passes/test_template_name_infer.py` 随 arch_parallelize 组通过，覆盖默认约束注册与 byte-pool alias family；整组 pytest 与静态 matmul demo 覆盖模板 dtype seed / npu_demo pipeline 生成路径。

## 自检

- 接口：公开 API 仅限计划已获用户确认的 `dma.reinterpret`、`DmaReinterpretOp`、`dma-alias-to-reinterpret`、`DmaAliasToReinterpretPass(fold: bool = True)`；未新增未确认公开入口。
- 边界：`dma_alias_to_reinterpret` 对无法 exact materialize、verifier 失败、非 byte-pool subview、unsupported type 保持 no-op；alias 链只清理当前 source chain 中已无 use 的中间 alias，不做全局 DCE。
- 异常：`DmaAliasToReinterpretVerifierError:` 作为 pass verifier 失败稳定前缀；dialect verifier 错误文本已写入 spec/test。
- 兼容：保留 `dma.view` / `dma.reshape` / `dma.subview` 定义和旧 hoist 专项逻辑；主 pipeline lower-nn 后先归一化，memory-pool 直接产出 reinterpret。
- 非公开 API：实现未跨文件调用 `kernel_gen.dialect.dma.common` 等非公开 helper；测试通过公开 pass / registry / operation API 观察行为。
- 运行时兼容探测：未新增 `hasattr(ctx, ...)`、`getattr(ctx, ...)` 或同类上下文能力探测分支。
- 函数粒度/复用：新增逻辑收口到当前文件内顶层 helper，无函数体内嵌套函数；注释集中在复杂 alias/materialize/emit 分支。
- 输入输出/资源：byte-pool offset 单位按 byte，typed source offset 按 element；shape/stride exact 匹配 result type；pass 在 clone 上 rewrite 后验证再替换，避免半替换。
- 并发/性能：新增 pass 使用 greedy rewrite；只物化必要 symbol op，不做跨 region 移动和复杂代数化简；pipeline DCE 仍由 PassManager fold 控制。
- 测试有效性：pytest 覆盖 dialect、pass、pipeline、downstream、memory-pool、emit；只读 expectation 锁定 root source、offset、shape/stride、result type、旧 alias 删除和单 reinterpret 数量；静态 matmul demo覆盖真实 dump/source/compile/execute。
- 敏感面：候选 diff 中 `expectation/.skills/agents/standard/AGENTS.md/TODO.md/DONE.md/ARCHITECTURE` 为空。

## 结论

- 本轮 execute 计划内实现、spec、pytest、只读 `dma_alias_to_reinterpret` expectation、manifest/file-list/import 探针、diff check、敏感目录空 diff已完成。
- `expectation.pass.hoist_dma_alias_ops` 不作为通过项：候选与 latest main 同源失败，且本轮未改该 pass 实现或 expectation；需 review 复核隔离结论、确认候选未扩大失败面。
- execute 候选可进入 review。

## Review 记录 - 不要啊教练 - 2026-05-24 04:21 +0800

时间：2026-05-24 04:21 +0800
经办人：不要啊教练
任务：T-20260524-b30e8d52 / dma_reinterpret_alias_unification / review
任务目标：审查计划级 execute 产物的公开 API、实现、spec、测试、Diff 反推自测、只读 expectation 合同验收、latest main 同步、敏感目录空 diff，并复核 `expectation.pass.hoist_dma_alias_ops` latest-main 既有失败隔离。

### 最新同步现场

- 执行目录：`/home/lfr/kernelcode_generate/wt-20260524-dma-reinterpret-alias-unification`。
- `git fetch origin --prune`：exit 0。
- `git status --short --branch`：`task/dma-reinterpret-alias-unification...origin/main`，仅任务候选 diff 与任务记录 / 新增文件；未见冲突状态。
- `git rev-parse HEAD origin/main`：两者均为 `5e1019a31910e7641c1874118e8045818273a184`。
- `git merge-base HEAD origin/main`：`5e1019a31910e7641c1874118e8045818273a184`。
- 结论：候选基于 latest `origin/main`，当前 review 未发现同步冲突或覆盖风险。

### 被审 diff

- dialect/API：`kernel_gen/dialect/dma/**`、`spec/dialect/dma.md`、`spec/operation/dma.md`、`test/dialect/dma/**`。
- pass/registry/pipeline：`kernel_gen/passes/dma_alias_to_reinterpret.py`、`kernel_gen/passes/registry.py`、`kernel_gen/pipeline/npu_demo_lowering.py`、`spec/pass/dma_alias_to_reinterpret.md`、`spec/pass/registry.md`、`spec/pass/pipeline/npu_demo_lowering.md`、对应 pytest。
- downstream：`producer_consumer_analysis.py`、`memory_plan.py`、`symbol_buffer_hoist.py`、`arch_parallelize.py`、`template_name/default_constraints.py`、对应 spec/test。
- memory-pool/emit：`kernel_gen/passes/memory_pool.py`、`kernel_gen/dsl/gen_kernel/emit/**`、对应 spec/test。
- 敏感/合同：只读核对主仓 `expectation/pass/dma_alias_to_reinterpret/**` manifest 与候选 `expectation/.skills/agents/standard/AGENTS.md/TODO.md/DONE.md/ARCHITECTURE` 空 diff。

### Findings

- P1 / 阻断：`spec/dialect/dma.md:106` 与 `spec/dialect/dma.md:184` 把 `dma.reinterpret` 纳入旧的 “非 byte-pool source/result rank mismatch 只允许 byte pool、非 byte pool 可判定 numel mismatch 必须报错” 口径，但计划与实现/测试要求 typed source 可做 rank-changing reinterpret，并只按 `offset + max_index(shape, stride) < source_numel` 做 bounds 检查。
  - 证据：计划书 `ARCHITECTURE/plan/dma_reinterpret_alias_unification_green_plan.md:309-324` 的 verifier 规则未要求 typed source/result rank 或 numel 相等；`ARCHITECTURE/plan/dma_reinterpret_alias_unification_green_plan.md:328-348` 明确 `dma.reshape` 1D typed source -> 2D typed result 要归一为 `dma.reinterpret`。
  - 证据：实现 `kernel_gen/dialect/dma/operation/alias.py:435-465` 对非 byte-pool `DmaReinterpretOp` 只校验 same space、same element type 与静态 bounds，没有 rank/numel equality gate。
  - 证据：测试 `test/dialect/dma/test_reinterpret.py:30-37` 接受 source `[16]` 到 result `[2,3]`；`test/passes/test_dma_alias_to_reinterpret.py:226-244` 接受 `dma.reshape` source `[4,4]` 到 result `[2,8]` 归一为 `dma.reinterpret`。
  - 影响：公开 spec 与实际公开 API / pass 行为互相矛盾；按 spec 阅读会把计划核心产物判成非法 IR，后续架构终验和用户侧实现无法以 spec 作为稳定合同真源。
  - 最小返工动作：修订 `spec/dialect/dma.md` 中涉及 `dma.reinterpret` 的通用/Verifier 约束，把 `reinterpret` 从 `view/reshape` 的 rank/numel equality 旧口径中拆出；明确非 byte-pool `reinterpret` 允许 rank-changing / partial alias，只要求 same element type、same space、shape/stride exact match 与静态 bounds。
  - 验收方式：复跑 `rg -n "dma.view/reshape/reinterpret|rank 不一致|numel 不一致" spec/dialect/dma.md` 人工确认无冲突旧口径；复跑 `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q -p no:cacheprovider test/dialect/dma/test_reinterpret.py test/passes/test_dma_alias_to_reinterpret.py`；复跑 `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260524-dma-reinterpret-alias-unification:/home/lfr/kernelcode_generate python3 -m expectation.pass.dma_alias_to_reinterpret`。

### 执行记录核对

- 执行记录包含执行前阅读、latest-main 同步、最小功能闭环、pytest / expectation / manifest / 静态门禁、Diff 反推自测、自检与结论。
- 公开 API exact spelling 与计划一致，来源为用户已确认的 `dma.reinterpret`、`DmaReinterpretOp`、`dma-alias-to-reinterpret`、`DmaAliasToReinterpretPass(fold: bool = True)`。
- 记录中的 `expectation.pass.hoist_dma_alias_ops` 已标为 latest-main 既有失败隔离，未写作通过项。

### Diff 反推审查与验证

- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q -p no:cacheprovider test/dialect/dma/test_reinterpret.py test/dialect/dma/test_package.py test/dialect/dma/test_operation_alias.py test/passes/test_dma_alias_to_reinterpret.py test/passes/test_registry.py test/passes/pipeline/test_npu_demo_lowering.py test/passes/test_producer_consumer_analysis.py test/passes/test_memory_plan.py test/passes/test_symbol_buffer_hoist.py test/passes/test_memory_pool.py test/dsl/gen_kernel/emit/test_package.py`
  - 结果：exit 0，`279 passed, 1 warning`。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 kernel/matmul/inputs_static_tile_static.py`
  - 结果：exit 0，absent/present bias `max_abs_diff=3.4332275390625e-05`。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 - <<'PY' ...`
  - 结果：exit 0，公开 import/API matrix 通过；`DmaReinterpretOp.name == "dma.reinterpret"`，registry 可构造 `DmaAliasToReinterpretPass(fold=False)`。
- `git diff --check`
  - 结果：exit 0。
- `git diff --quiet -- expectation .skills agents/standard AGENTS.md TODO.md DONE.md ARCHITECTURE`
  - 结果：exit 0；敏感目录 / 共享状态 / 主仓计划候选 diff 为空。
- 静态非公开 API 扫描：
  - `rg -n "from kernel_gen\\.dialect\\.dma\\.(common|effect|canonicalization)|kernel_gen\\.dialect\\.dma\\.(common|effect|canonicalization)|from kernel_gen\\.passes\\.dma_alias_to_reinterpret import _|dma_alias_to_reinterpret\\._" kernel_gen test spec`
  - 结果：仅命中 `test/dialect/dma/test_package.py:320-322` 既有 package boundary 测试对 `common/effect/canonicalization` 的内部模块检查；未发现本轮实现或新增测试跨文件调用 `dma_alias_to_reinterpret` 私有 helper。
- 上下文能力探测 / `object` 签名扫描：
  - `rg -n "hasattr\\([^\\n]*ctx|getattr\\([^\\n]*ctx|callable\\(getattr\\([^\\n]*ctx|emit_barrier|def [A-Za-z0-9_]+\\([^)]*object|: object" ...`
  - 结果：exit 1，无命中。

### 合同验收与隔离

- 导入来源探针：
  - `expectation.pass.dma_alias_to_reinterpret.__main__` 来源：`/home/lfr/kernelcode_generate/expectation/pass/dma_alias_to_reinterpret/__main__.py`。
  - `kernel_gen.passes.registry` 来源：`/home/lfr/kernelcode_generate/wt-20260524-dma-reinterpret-alias-unification/kernel_gen/passes/registry.py`。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260524-dma-reinterpret-alias-unification:/home/lfr/kernelcode_generate python3 -m expectation.pass.dma_alias_to_reinterpret`
  - 结果：exit 0；12 个正例通过。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260524-dma-reinterpret-alias-unification:/home/lfr/kernelcode_generate python3 -m expectation.pass.symbol_buffer_hoist`
  - 结果：exit 0。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260524-dma-reinterpret-alias-unification:/home/lfr/kernelcode_generate python3 -m expectation.pass.producer_consumer_analysis`
  - 结果：exit 0。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260524-dma-reinterpret-alias-unification:/home/lfr/kernelcode_generate python3 -m expectation.pass.memory_plan`
  - 结果：exit 0。
- `PYTHONMALLOC=malloc PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260524-dma-reinterpret-alias-unification:/home/lfr/kernelcode_generate python3 -m expectation.pass.hoist_dma_alias_ops`
  - 结果：exit 1，`slice` family 失败；候选 raw 输出包含 `CHECK not found` 与旧硬编码 `17-hoist-dma-alias-ops.mlir` dump path missing。
- `PYTHONMALLOC=malloc PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/home/lfr/kernelcode_generate python3 -m expectation.pass.hoist_dma_alias_ops`
  - 结果：exit 1，latest main 同在 `slice` family 失败；主仓 `17-hoist-dma-alias-ops.mlir` 仍有高维 weight `dma.slice`。
- 隔离复核：候选新增 `07-dma-alias-to-reinterpret.mlir` 后，conv2d dump 编号从主仓 `17-hoist-dma-alias-ops.mlir` 后移到候选 `18-hoist-dma-alias-ops.mlir`。人工 `rg` 候选 `18-hoist-dma-alias-ops.mlir` 与主仓 `17-hoist-dma-alias-ops.mlir`，两边都保留同类 4D weight `dma.slice`；候选未修改 `kernel_gen/passes/hoist_dma_alias_ops.py` 或 `expectation/pass/hoist_dma_alias_ops/slice.py`。该项仍按 latest-main 既有失败隔离记录，不作为通过项；raw message 的 dump path 差异来自计划内 pipeline stage 后移。
- `find /home/lfr/kernelcode_generate/expectation/pass/dma_alias_to_reinterpret -maxdepth 1 -type f -print | sort`
  - 结果：恰好 4 个授权合同文件。
- `sha256sum /home/lfr/kernelcode_generate/expectation/pass/dma_alias_to_reinterpret/{__main__.py,reshape.py,view.py,subview.py}`
  - 结果与计划 manifest 一致：`6eeeec...346a`、`dd3d7...8357f`、`0bc0a...75d8`、`b772e...1312`。

### 自检

- 已逐项读取实际 diff，而不是只按 execute 摘要判断。
- 已核对 latest main 基线、公开 API 用户确认、root API/import/registry/pipeline、spec/实现/test 同步、敏感目录空 diff。
- 已核对实现未跨文件调用 `dma` package internal helper，新增测试通过公开 pass / registry / dialect op 观察行为。
- 已按 diff 反推复跑 pytest、静态 matmul demo、import matrix、只读 expectation 与静态门禁。
- 已复核 `hoist_dma_alias_ops` 失败隔离；该项不作为通过项。
- 因存在公开 spec 合同冲突，结论不能写通过。

### 结论

- 结论：`最小需改项 / 不通过`。
- 下一步：回 `execute` 修复上方 P1 spec 合同冲突；修复后补记返工收口与对应 pytest / expectation / 静态扫描，再续接 review。

## Execute 返工记录 - 咯咯咯 - 2026-05-24 04:25 +0800

时间：2026-05-24 04:25 CST
经办人：咯咯咯
任务：T-20260524-b30e8d52 / dma_reinterpret_alias_unification / execute 返工
任务目标：修复 review 指出的最小阻断项：`spec/dialect/dma.md` 中 `dma.reinterpret` 被纳入旧 rank/numel equality 口径，与计划 / 实现 / 测试允许 typed rank-changing / partial reinterpret 的合同冲突。

### 最新同步现场

- 执行目录：`/home/lfr/kernelcode_generate/wt-20260524-dma-reinterpret-alias-unification`。
- 已重新读取 `agents/codex-multi-agents/agents/咯咯咯/咯咯咯.prompt.md`、`AGENTS.md`、主仓只读计划 `/home/lfr/kernelcode_generate/ARCHITECTURE/plan/dma_reinterpret_alias_unification_green_plan.md` 与 review 记录。
- `git fetch origin --prune`：exit 0。
- `git rev-parse HEAD origin/main`：两者均为 `5e1019a31910e7641c1874118e8045818273a184`。
- `git merge-base HEAD origin/main`：`5e1019a31910e7641c1874118e8045818273a184`。
- `git rev-list --left-right --count HEAD...origin/main`：`0 0`。
- 主仓 `TODO.md` 核对：`T-20260524-b30e8d52` 当前为 `execute/进行中`，指派给 `咯咯咯`。

### 返工修改

- `spec/dialect/dma.md` 通用约束：将 `dma.reinterpret` 从 `dma.view/reshape` 的旧合并描述拆出，明确：
  - 非 byte-pool typed `dma.reinterpret` 要求 same element type、same space；
  - 一维 `i8` byte-pool source 允许 result 使用其它公开支持 dtype；
  - 非 byte-pool typed `dma.reinterpret` 允许 rank-changing 与 partial alias，不要求 `source/result` rank 或 `numel` 相等。
- `spec/dialect/dma.md` verifier 约束：拆分为 `dma.view`、`dma.reshape`、`dma.reinterpret` 三条，保留 `view` / `reshape` 自身的 numel 约束，同时明确 `reinterpret` 仅按 `shape/stride` exact match 与静态 bounds 判断合法性。
- `DmaReinterpretOp` 注意事项：补充 typed reinterpret 的 rank-changing / partial alias 合同，和 same element_type、same space、shape/stride exact match、静态 bounds 的约束组合。
- 本轮未修改实现、测试、expectation、`.skills`、`agents/standard`、`AGENTS.md`、`TODO.md`、`DONE.md` 或 `ARCHITECTURE`。

### 验证

- `rg -n "dma.view/reshape/reinterpret|rank 不一致|numel 不一致" spec/dialect/dma.md`
  - 结果：exit 0；命中仅剩通用 rank 校验、`view/reshape` 自身 operand 约束、transpose 边界和测试清单；未再出现把 `dma.reinterpret` 纳入旧 rank/numel equality 口径的句子。
- `! rg -n "reinterpret.*(rank 不一致|numel 不一致|numel.*必须报错|rank.*仅在 byte pool|source/result.*rank 不一致|source/result.*numel 不一致)|rank.*reinterpret|numel.*reinterpret" spec/dialect/dma.md`
  - 结果：exit 0；输出 `no reinterpret rank/numel equality conflict`。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q -p no:cacheprovider test/dialect/dma/test_reinterpret.py test/passes/test_dma_alias_to_reinterpret.py`
  - 结果：exit 0；`10 passed, 1 warning`。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260524-dma-reinterpret-alias-unification:/home/lfr/kernelcode_generate python3 -m expectation.pass.dma_alias_to_reinterpret`
  - 结果：exit 0；12 个正例输出均通过。
- `git diff --check && git diff --cached --check`
  - 结果：exit 0。
- `git diff --name-only -- expectation .skills agents/standard AGENTS.md TODO.md DONE.md ARCHITECTURE && git diff --cached --name-only -- expectation .skills agents/standard AGENTS.md TODO.md DONE.md ARCHITECTURE && git status --short --ignored --untracked-files=all -- expectation .skills agents/standard AGENTS.md TODO.md DONE.md ARCHITECTURE`
  - 结果：exit 0，空输出；敏感目录、共享状态和主仓计划资产无候选 diff。
- `! rg -n "hasattr\\([^\\n]*ctx|getattr\\([^\\n]*ctx|callable\\(getattr\\([^\\n]*ctx|emit_barrier|from kernel_gen\\.passes\\.dma_alias_to_reinterpret import _|dma_alias_to_reinterpret\\._" kernel_gen test spec`
  - 结果：exit 0；输出 `static forbidden patterns absent`。

### Diff 反推自测

- 反推范围：本轮实际 diff 仅追加 `spec/dialect/dma.md` 的公开合同表述，风险集中在 `dma.reinterpret` 与 `dma.view/reshape` 的 verifier 口径是否继续冲突。
- 反推测试：复跑 `test/dialect/dma/test_reinterpret.py` 锁定 typed / byte-pool `DmaReinterpretOp` verifier 正反例；复跑 `test/passes/test_dma_alias_to_reinterpret.py` 锁定 `dma.reshape`、`dma.view`、`dma.subview` 归一到 `dma.reinterpret` 的行为仍与 spec 一致。
- 合同验收：只读运行 `expectation.pass.dma_alias_to_reinterpret`，验证计划授权的 12 个 pass 正例仍通过；该 expectation 仅作为合同验收资产，不替代 pytest 反推测试。
- 静态扫描：补充 `spec/dialect/dma.md` 中 `reinterpret` + rank/numel 冲突口径扫描，确认旧 equality 口径已移除。

### 自检

- 接口：未新增、删除、重命名或修改公开 API；仅修正文档合同，使其与已确认计划、实现和测试一致。
- 边界：未修改 `expectation/`、`.skills/`、`agents/standard/**`、`AGENTS.md`、`TODO.md`、`DONE.md`、`ARCHITECTURE`；只读 expectation 仅执行。
- 异常/兼容：未修改实现错误文本或运行时行为；`dma.reinterpret` 的 verifier 行为仍由既有实现和测试覆盖。
- 实现遗漏：review 指出的 `reinterpret` 被旧 rank/numel equality 口径约束的问题已在通用约束、verifier 约束和 `DmaReinterpretOp` 专项说明中同步收口。
- 冗余：未增加无关 spec 段落、shim、helper 或测试跳过。
- 注释准确性：当前 spec 明确区分 `view`、`reshape`、`reinterpret` 的不同 alias 约束，避免再把 typed reinterpret 判成非法 IR。
- 复用/函数粒度：本轮无代码函数变更。
- 输入/输出校验：行为未变更；pytest 与只读 expectation 均通过。
- 并发/资源/性能：本轮为 spec 合同修订，无新增资源、后台进程、并发路径或性能敏感逻辑。
- 测试有效性：点名 pytest 能在 `DmaReinterpretOp` typed rank-changing / pass 归一化行为破坏时失败；静态 rg 能捕获本次 review 阻断类型的复发。

### 结论

- execute 返工完成；review P1 最小阻断项已修复。
- 候选 diff 可重新进入 `review`。

## Review 复审记录 - 不要啊教练 - 2026-05-24 04:30 +0800

时间：2026-05-24 04:30 +0800
经办人：不要啊教练
任务：T-20260524-b30e8d52 / dma_reinterpret_alias_unification / review 复审
任务目标：复核 execute 返工是否闭合上轮 P1：`spec/dialect/dma.md` 中 `dma.reinterpret` 从 `view/reshape` 旧 rank/numel equality 口径拆出，并明确非 byte-pool typed reinterpret 允许 rank-changing / partial alias。

### 最新同步现场

- 执行目录：`/home/lfr/kernelcode_generate/wt-20260524-dma-reinterpret-alias-unification`。
- `git fetch origin --prune`：exit 0。
- `git rev-parse HEAD origin/main`：两者均为 `5e1019a31910e7641c1874118e8045818273a184`。
- `git merge-base HEAD origin/main`：`5e1019a31910e7641c1874118e8045818273a184`。
- `git rev-list --left-right --count HEAD...origin/main`：`0 0`。
- 主仓 `TODO.md`：`T-20260524-b30e8d52` 为 `review/进行中`，指派 `不要啊教练`。

### 复审范围

- 本轮返工实际关注：`spec/dialect/dma.md` 的公开合同口径。
- 主仓只读计划：`ARCHITECTURE/plan/dma_reinterpret_alias_unification_green_plan.md`。
- 执行记录：已核对 `Execute 返工记录 - 咯咯咯 - 2026-05-24 04:25 +0800`。
- 敏感 / 合同资产：只读核对，未修改 `expectation/.skills/agents/standard/AGENTS.md/TODO.md/DONE.md/ARCHITECTURE`。

### Findings

- 未发现阻断项。
- 上轮 P1 已闭合：`spec/dialect/dma.md` 当前将 `dma.view`、`dma.reshape`、`dma.reinterpret` verifier 约束拆开；`dma.reinterpret` 明确非 byte-pool typed source 只要求 same element type、same space、shape/stride exact match 与静态 bounds，允许 rank-changing / partial alias，不要求 `source/result` rank 或 `numel` 相等。
- 未发现新的 spec 合同冲突：`view` 保留旧 numel 约束，`reshape` 保留 same element type 与静态 numel equality，`reinterpret` 独立按 bounds 判定。

### 公开 API / 计划口径核对

- 主仓计划记录公开 API exact spelling 已由用户确认：`dma.reinterpret`、`DmaReinterpretOp`、`dma-alias-to-reinterpret`、`DmaAliasToReinterpretPass(fold: bool = True)`。
- 返工没有新增、删除、重命名或修改公开 API；只是修正 `spec/dialect/dma.md` 与既有计划 / 实现 / 测试的一致性。
- `ARCHITECTURE/plan/dma_reinterpret_alias_unification_green_plan.md` 在候选 worktree 中无 diff。

### Diff 反推审查与验证

- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q -p no:cacheprovider test/dialect/dma/test_reinterpret.py test/passes/test_dma_alias_to_reinterpret.py`
  - 结果：exit 0，`10 passed, 1 warning`。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260524-dma-reinterpret-alias-unification:/home/lfr/kernelcode_generate python3 -m expectation.pass.dma_alias_to_reinterpret`
  - 结果：exit 0；12 个正例输出均通过。该项是只读合同验收，不计作 pytest 反推测试替代。
- 导入来源探针：
  - `expectation.pass.dma_alias_to_reinterpret.__main__` 来源：`/home/lfr/kernelcode_generate/expectation/pass/dma_alias_to_reinterpret/__main__.py`。
  - `kernel_gen.passes.registry` 来源：候选 worktree。
  - `kernel_gen.dialect.dma.operation.alias` 来源：候选 worktree。
- `git diff --check`
  - 结果：exit 0。
- `git diff --cached --check`
  - 结果：exit 0。
- `git diff --name-only -- expectation .skills agents/standard AGENTS.md TODO.md DONE.md ARCHITECTURE`
  - 结果：exit 0，空输出。
- `git diff --cached --name-only -- expectation .skills agents/standard AGENTS.md TODO.md DONE.md ARCHITECTURE`
  - 结果：exit 0，空输出。
- `git status --short --ignored --untracked-files=all -- expectation .skills agents/standard AGENTS.md TODO.md DONE.md ARCHITECTURE`
  - 结果：exit 0，空输出。
- `if rg -n "reinterpret.*(rank 不一致|numel 不一致|numel.*必须报错|rank.*仅在 byte pool|source/result.*rank 不一致|source/result.*numel 不一致)" spec/dialect/dma.md; then exit 1; else echo "no reinterpret rank/numel equality conflict"; fi`
  - 结果：exit 0，`no reinterpret rank/numel equality conflict`。
- `if rg -n "hasattr\\([^\\n]*ctx|getattr\\([^\\n]*ctx|callable\\(getattr\\([^\\n]*ctx|emit_barrier|from kernel_gen\\.passes\\.dma_alias_to_reinterpret import _|dma_alias_to_reinterpret\\._" kernel_gen test spec; then exit 1; else echo "static forbidden patterns absent"; fi`
  - 结果：exit 0，`static forbidden patterns absent`。

### latest-main 既有失败隔离复核

- 本轮返工仅修改 `spec/dialect/dma.md`，未改实现、测试、pipeline、expectation 或 `hoist_dma_alias_ops` 相关文件。
- 上轮 review 已确认 `expectation.pass.hoist_dma_alias_ops` 为候选与 latest main 同源失败，且不作为通过项。
- 本轮未发现会扩大该失败面的新增改动；该隔离结论保持有效。

### 自检

- 已按实际 diff 复核返工文本，而不是只采信 execute 摘要。
- 已核对公开 API 确认来源、spec 合同一致性、只读 expectation、pytest 反推测试、静态扫描与敏感目录空 diff。
- 已遵守 review 只读职责：未修改实现、测试、计划书、expectation、`.skills` 或 `agents/standard`。

### 结论

- 结论：`通过`。
- 下一步：按计划级流程 `-next` 到 `other`，交管理员接入架构复核 / 终验；不得直接 merge。

## Review 复审流转记录 - 不要啊教练 - 2026-05-24 04:32 +0800

- 已在主仓根目录执行标准流转：
  - `bash skills/codex-multi-agents/scripts/codex-multi-agents-task.sh -file TODO.md -next -task_id T-20260524-b30e8d52 -from 不要啊教练 -type other ... -agents-list agents/codex-multi-agents/agents-lists.md`
- 结果：
  - `OK: next T-20260524-b30e8d52`
  - `OK: replace 不要啊教练 状态`
  - `OK: talk 不要啊教练 -> 神秘人 (神秘人)`
- 状态核对：
  - 主仓 `TODO.md` 当前无正在执行任务。
  - `T-20260524-b30e8d52` 已回到任务列表，类型为 `other`，未指派，描述为 review 复审通过并请管理员接计划级架构复核 / 终验。
  - `agents-lists.md` 中 `不要啊教练` 状态为 `free`。
- 本轮未进入 merge。

## 第一轮计划级架构复核 / 终验 - 大闸蟹 - 2026-05-24

时间：2026-05-24 当前会话
经办人：大闸蟹
任务：T-20260524-b30e8d52 / dma_reinterpret_alias_unification
任务目标：基于 latest 同步现场复核候选 diff、公开 API、spec / 实现 / test 一致性、只读 expectation 合同验收、latest-main 既有失败隔离、Diff 反推测试和敏感目录；不进入 merge。

### 最新同步现场

- 执行目录：`/home/lfr/kernelcode_generate/wt-20260524-dma-reinterpret-alias-unification`。
- `git fetch origin`：exit 0。
- 分支：`task/dma-reinterpret-alias-unification`。
- 基线：`HEAD=5e1019a31910e7641c1874118e8045818273a184`，`origin/main=5e1019a31910e7641c1874118e8045818273a184`，`merge-base=5e1019a31910e7641c1874118e8045818273a184`，ahead / behind=`0 / 0`。
- 候选 diff 为 worktree 未提交改动；`HEAD..origin/main` 路径交集为空。
- 候选范围覆盖 dialect / pass / pipeline / downstream pass / memory-pool / emit / spec / pytest；未见 staged diff。

### 计划与公开 API 复核

- 主仓只读计划：`/home/lfr/kernelcode_generate/ARCHITECTURE/plan/dma_reinterpret_alias_unification_green_plan.md`。
- 公开 API exact spelling 已有用户确认，候选未新增未确认公开 API：
  - `dma.reinterpret`
  - `DmaReinterpretOp`
  - `dma-alias-to-reinterpret`
  - `DmaAliasToReinterpretPass(fold: bool = True)`
- API/import matrix：
  - 公开导入 `kernel_gen.dialect.dma.DmaReinterpretOp` 与 `kernel_gen.dialect.dma.operation.DmaReinterpretOp` 同源。
  - `Dma.operations` 包含 `dma.reinterpret`。
  - 按既有 registry 合同先 `load_builtin_passes()` 后，`build_registered_pass("dma-alias-to-reinterpret", {"fold": "false"})` 返回 `DmaAliasToReinterpretPass` 且 `fold=False`。
- P1 返工复核：
  - `spec/dialect/dma.md` 已将 `dma.reinterpret` 从 `view/reshape` 旧 rank / numel equality 口径拆出。
  - 非 byte-pool typed `dma.reinterpret` 允许 rank-changing / partial alias；合同收口为 same element type、same space、shape/stride exact match 与静态 bounds。
  - 静态扫描 `reinterpret.*rank/numel equality` 冲突口径无命中。

### Diff 反推测试

- 计划最低 pytest：
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q -p no:cacheprovider test/dialect/dma/test_reinterpret.py test/passes/test_dma_alias_to_reinterpret.py test/passes/test_registry.py test/passes/pipeline/test_npu_demo_lowering.py test/passes/test_producer_consumer_analysis.py test/passes/test_memory_plan.py test/passes/test_symbol_buffer_hoist.py test/passes/test_memory_pool.py test/dsl/gen_kernel/emit/test_package.py`
  - 结果：exit 0，`258 passed, 1 warning`。
- P1 返工聚焦 pytest：
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q -p no:cacheprovider test/dialect/dma/test_reinterpret.py test/passes/test_dma_alias_to_reinterpret.py`
  - 结果：exit 0，`10 passed, 1 warning`。
- arch / template 反推测试：
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q -p no:cacheprovider test/passes/test_arch_parallelize.py test/passes/test_template_name_constraints.py test/passes/test_template_name_infer.py -x --tb=short`
  - 结果：exit 0，`35 passed, 1 warning`。
- `PYTHONMALLOC=malloc` 复跑计划最低 pytest：
  - `PYTHONMALLOC=malloc PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/dialect/dma/test_reinterpret.py test/passes/test_dma_alias_to_reinterpret.py test/passes/test_registry.py test/passes/pipeline/test_npu_demo_lowering.py test/passes/test_producer_consumer_analysis.py test/passes/test_memory_plan.py test/passes/test_symbol_buffer_hoist.py test/passes/test_memory_pool.py test/dsl/gen_kernel/emit/test_package.py`
  - 结果：exit 0，`258 passed, 1 warning`。
- 静态 matmul demo：
  - `timeout 180s env PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 kernel/matmul/inputs_static_tile_static.py`
  - 结果：exit 0；absent / present bias `max_abs_diff=3.4332275390625e-05`。
- dump marker / memory-pool 复核：
  - `06-lower-nn.mlir` 后存在 `07-dma-alias-to-reinterpret.mlir`，随后 `08-symbol-loop-hoist.mlir`。
  - `07-dma-alias-to-reinterpret.mlir` 含 `dma.reinterpret`，不再残留 `dma.view` / `dma.reshape`。
  - `23-memory-pool.mlir` 含 `arch.get_dynamic_memory` + `dma.reinterpret`，不再生成 `dma.view + dma.reshape`。

### 合同 expectation

- 导入来源探针：
  - `expectation.pass.dma_alias_to_reinterpret.__main__` 来自主仓 `/home/lfr/kernelcode_generate/expectation/pass/dma_alias_to_reinterpret/__main__.py`。
  - `kernel_gen.passes.registry` 与 `kernel_gen.dialect.dma.operation.alias` 来自任务 worktree。
- `find /home/lfr/kernelcode_generate/expectation/pass/dma_alias_to_reinterpret -maxdepth 1 -type f -print | sort` 恰好返回 4 个授权文件：`__main__.py`、`reshape.py`、`subview.py`、`view.py`。
- `sha256sum` 与计划 manifest 一致：
  - `__main__.py` = `6eeeec322ada03803347630905d536b37158717c32dcf39fcb2514b9dd6c346a`
  - `reshape.py` = `dd3d7bc53e63e3f6e2e14ae56b3c59f5fc3539f171675534869fef1c33c8357f`
  - `view.py` = `0bc0a210737d704d81242b2f1edb09402ba57cdbf5eec8b7cb99345bd2da75d8`
  - `subview.py` = `b772e6871ff6db57078c90709360f77fb8ab2358fc136090aa7a43b29ab71312`
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260524-dma-reinterpret-alias-unification:/home/lfr/kernelcode_generate python3 -m expectation.pass.dma_alias_to_reinterpret`
  - 结果：exit 0；12 个 reshape / view / subview 正例全部通过。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260524-dma-reinterpret-alias-unification:/home/lfr/kernelcode_generate python3 -m expectation.pass.symbol_buffer_hoist`
  - 结果：exit 0。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260524-dma-reinterpret-alias-unification:/home/lfr/kernelcode_generate python3 -m expectation.pass.producer_consumer_analysis`
  - 结果：exit 0。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260524-dma-reinterpret-alias-unification:/home/lfr/kernelcode_generate python3 -m expectation.pass.memory_plan`
  - 结果：exit 0。

### latest-main 既有失败隔离

- `PYTHONMALLOC=malloc PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260524-dma-reinterpret-alias-unification:/home/lfr/kernelcode_generate python3 -m expectation.pass.hoist_dma_alias_ops`
  - 结果：exit 1；失败仍集中在 `slice` family，包含 `symbol.mul %n, %kh` CHECK not found 与动态 conv2d dump path 缺失。
- `PYTHONMALLOC=malloc PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/home/lfr/kernelcode_generate python3 -m expectation.pass.hoist_dma_alias_ops`
  - 结果：exit 1；latest main 同源失败，同在 `slice` family，保留高维 weight `dma.slice`。
- 隔离结论：该 expectation 本轮只作 latest-main 既有失败隔离，不作为通过项。候选未修改 `kernel_gen/passes/hoist_dma_alias_ops.py` 或 `expectation/pass/hoist_dma_alias_ops/slice.py`；计划内 pipeline 插入导致候选 dump 编号后移，不改变失败根因。

### 静态门禁与敏感目录

- `PYTHONDONTWRITEBYTECODE=1 python3 -m compileall -q kernel_gen/dialect/dma kernel_gen/passes kernel_gen/pipeline kernel_gen/dsl/gen_kernel/emit test/dialect/dma test/passes test/dsl/gen_kernel/emit`
  - 结果：exit 0。
- `git diff --check && git diff --cached --check`
  - 结果：exit 0。
- 公开 API 同步扫描：
  - `rg -n "DmaReinterpretOp|dma\\.reinterpret|dma-alias-to-reinterpret|DmaAliasToReinterpretPass" spec kernel_gen test`
  - 结果：exit 0，共 323 处命中；覆盖 spec / 实现 / test。
- 旧口径扫描：
  - `view/reshape/subview.*唯一 alias|只识别.*view.*reshape.*subview|setup.*view.*reshape`
  - 结果：exit 0，`old_alias_scan_ok`。
- runtime 能力探测扫描：
  - `hasattr(ctx, ...)` / `getattr(ctx, ...)` / `callable(getattr(ctx, ...))` / `emit_barrier`
  - 结果：exit 0，未命中。
- 跨文件私有 helper 扫描：
  - 排除既有 `test/dialect/dma/test_package.py` 对 package internal 模块的边界测试后，未发现本轮实现或新增测试跨文件调用 `dma_alias_to_reinterpret` 私有 helper / `dma.common` 等内部 API。
- 敏感目录 / 共享状态 / 计划资产：
  - `git diff --name-only -- expectation .skills agents/standard AGENTS.md TODO.md DONE.md ARCHITECTURE`：空。
  - `git diff --cached --name-only -- expectation .skills agents/standard AGENTS.md TODO.md DONE.md ARCHITECTURE`：空。
  - `git status --short --untracked-files=all -- expectation .skills agents/standard AGENTS.md TODO.md DONE.md ARCHITECTURE`：空。
  - `find /home/lfr/kernelcode_generate/expectation/pass/dma_alias_to_reinterpret -maxdepth 2 -type d -name __pycache__ -print`：空。
- `kernel/dump/` 无候选 diff。

### 架构复核结论

- `DmaReinterpretOp` verifier、pass 归一化、registry / pipeline 插入、memory-pool 方案 A、downstream alias 分析、emit CPU/npu_demo 与 template constraints 与计划目标一致。
- `spec/dialect/dma.md` 中 P1 合同冲突已闭合，当前 spec / 实现 / test 对 typed rank-changing / partial `dma.reinterpret` 口径一致。
- 只读 expectation 合同验收通过；`hoist_dma_alias_ops` latest-main 既有失败隔离成立，未作为通过项。
- 未发现公开 API、expectation 授权、敏感目录、跨文件私有 API、runtime 能力探测或计划边界阻断项。

### 自检

- 已基于 latest 同步现场复核 `HEAD` / `origin/main` / `merge-base` / ahead-behind。
- 已按实际 diff 反推测试，expectation 单列为合同验收，未替代 pytest。
- 已写回主仓计划正文状态：`execute 完成且 review 复审通过 / 第一轮架构终验通过 / 可进入第二轮架构终验`。
- 本轮未进入 merge，未修改候选功能实现；只补充计划正文状态与本终验记录。

结论：第一轮计划级架构复核 / 终验通过。可进入第二轮架构终验；当前不进入 merge。

## 第二轮计划级架构复核 / 终验 - 守护最好的爱莉希雅 - 2026-05-24

时间：2026-05-24 04:47:53 +0800
经办人：守护最好的爱莉希雅
任务：T-20260524-b30e8d52 / dma_reinterpret_alias_unification
任务目标：基于 latest 同步现场复核计划正文、候选 diff、公开 API、只读 expectation 合同、latest-main 既有失败隔离、敏感目录和任务记录；不进入 merge。

### 最新同步现场

- 执行目录：`/home/lfr/kernelcode_generate/wt-20260524-dma-reinterpret-alias-unification`。
- `git fetch origin --prune`：exit 0。
- 基线：`HEAD=5e1019a31910e7641c1874118e8045818273a184`，`origin/main=5e1019a31910e7641c1874118e8045818273a184`，`merge-base=5e1019a31910e7641c1874118e8045818273a184`，ahead / behind=`0 / 0`。
- 候选 diff 为 worktree 未提交改动；`HEAD..origin/main` 路径交集为空。
- 候选新增文件：
  - `kernel_gen/dsl/gen_kernel/emit/npu_demo/dma/reinterpret.py`
  - `kernel_gen/passes/dma_alias_to_reinterpret.py`
  - `spec/pass/dma_alias_to_reinterpret.md`
  - `test/dialect/dma/test_reinterpret.py`
  - `test/passes/test_dma_alias_to_reinterpret.py`
  - 本任务记录文件
- 候选修改范围：dma dialect / emit / pass registry / npu-demo pipeline / memory-plan / memory-pool / producer-consumer-analysis / symbol-buffer-hoist / arch-parallelize / template constraints / spec / pytest。

### 架构核对

- 主仓计划真源：`/home/lfr/kernelcode_generate/ARCHITECTURE/plan/dma_reinterpret_alias_unification_green_plan.md`，当前状态为 execute 完成、review 复审通过、第一轮架构终验通过、可进入第二轮架构终验。
- 公开 API exact spelling 已有用户确认，候选未新增未确认公开 API：
  - `dma.reinterpret`
  - `DmaReinterpretOp`
  - `dma-alias-to-reinterpret`
  - `DmaAliasToReinterpretPass(fold: bool = True)`
- API matrix：`kernel_gen.dialect.dma.DmaReinterpretOp`、`kernel_gen.dialect.dma.operation.DmaReinterpretOp`、`kernel_gen.dialect.dma.operation.alias.DmaReinterpretOp` 同源；`Dma.operations` 包含 `dma.reinterpret`；`load_builtin_passes()` 后 `build_registered_pass("dma-alias-to-reinterpret", {"fold": "false"})` 返回 `DmaAliasToReinterpretPass` 且 `fold=False`。
- `DmaReinterpretOp` verifier、`DmaAliasToReinterpretPass` root alias 归一化、`NnLoweringPass` 后插入点、memory-pool 方案 A、下游 alias 分析、CPU / npu_demo emit 与 template constraints 均与计划目标一致。
- P1 spec 冲突保持闭合：`spec/dialect/dma.md` 中 `dma.reinterpret` 已从 `view/reshape` 旧 rank / numel equality 口径拆出，非 byte-pool typed reinterpret 允许 rank-changing / partial alias，只按 same element type、same space、shape/stride exact match 与静态 bounds 判断。

### Diff 反推测试

- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q -p no:cacheprovider test/dialect/dma/test_reinterpret.py test/passes/test_dma_alias_to_reinterpret.py test/passes/test_registry.py test/passes/pipeline/test_npu_demo_lowering.py test/passes/test_producer_consumer_analysis.py test/passes/test_memory_plan.py test/passes/test_symbol_buffer_hoist.py test/passes/test_memory_pool.py test/dsl/gen_kernel/emit/test_package.py`
  - 结果：exit 0，`258 passed, 1 warning`。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q -p no:cacheprovider test/dialect/dma/test_reinterpret.py test/passes/test_dma_alias_to_reinterpret.py`
  - 结果：exit 0，`10 passed, 1 warning`。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q -p no:cacheprovider test/passes/test_arch_parallelize.py test/passes/test_template_name_constraints.py test/passes/test_template_name_infer.py -x --tb=short`
  - 结果：exit 0，`35 passed, 1 warning`。
- `PYTHONMALLOC=malloc PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/dialect/dma/test_reinterpret.py test/passes/test_dma_alias_to_reinterpret.py test/passes/test_registry.py test/passes/pipeline/test_npu_demo_lowering.py test/passes/test_producer_consumer_analysis.py test/passes/test_memory_plan.py test/passes/test_symbol_buffer_hoist.py test/passes/test_memory_pool.py test/dsl/gen_kernel/emit/test_package.py`
  - 结果：exit 0，`258 passed, 1 warning`。
- 静态 matmul demo：`timeout 180s env PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 kernel/matmul/inputs_static_tile_static.py`
  - 结果：exit 0；absent / present bias `max_abs_diff=3.4332275390625e-05`。
- dump marker / memory-pool gate：
  - `06-lower-nn.mlir` 后存在 `07-dma-alias-to-reinterpret.mlir`，随后是 `08-symbol-loop-hoist.mlir`。
  - `07-dma-alias-to-reinterpret.mlir` 含 `dma.reinterpret`，不含 `dma.view` / `dma.reshape`。
  - `23-memory-pool.mlir` 含 `arch.get_dynamic_memory` + `dma.reinterpret`，不含 `dma.view` / `dma.reshape`。

### 合同 expectation

- 导入来源探针：
  - `expectation.pass.dma_alias_to_reinterpret.__main__`、`reshape`、`view`、`subview` 均来自主仓 `/home/lfr/kernelcode_generate/expectation/pass/dma_alias_to_reinterpret/...`。
  - `kernel_gen.passes.registry`、`kernel_gen.passes.dma_alias_to_reinterpret`、`kernel_gen.dialect.dma.operation.alias` 均来自任务 worktree。
- `find /home/lfr/kernelcode_generate/expectation/pass/dma_alias_to_reinterpret -maxdepth 1 -type f -print | sort` 恰好返回授权 4 文件：`__main__.py`、`reshape.py`、`subview.py`、`view.py`。
- sha256 manifest 与计划一致：
  - `__main__.py` = `6eeeec322ada03803347630905d536b37158717c32dcf39fcb2514b9dd6c346a`
  - `reshape.py` = `dd3d7bc53e63e3f6e2e14ae56b3c59f5fc3539f171675534869fef1c33c8357f`
  - `view.py` = `0bc0a210737d704d81242b2f1edb09402ba57cdbf5eec8b7cb99345bd2da75d8`
  - `subview.py` = `b772e6871ff6db57078c90709360f77fb8ab2358fc136090aa7a43b29ab71312`
- `find /home/lfr/kernelcode_generate/expectation/pass/dma_alias_to_reinterpret -maxdepth 2 -type d -name __pycache__ -print`：空。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260524-dma-reinterpret-alias-unification:/home/lfr/kernelcode_generate python3 -m expectation.pass.dma_alias_to_reinterpret`
  - 结果：exit 0；12 个 reshape / view / subview 正例全部通过。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260524-dma-reinterpret-alias-unification:/home/lfr/kernelcode_generate python3 -m expectation.pass.symbol_buffer_hoist`
  - 结果：exit 0。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260524-dma-reinterpret-alias-unification:/home/lfr/kernelcode_generate python3 -m expectation.pass.producer_consumer_analysis`
  - 结果：exit 0。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260524-dma-reinterpret-alias-unification:/home/lfr/kernelcode_generate python3 -m expectation.pass.memory_plan`
  - 结果：exit 0。

### latest-main 既有失败隔离

- 候选：`PYTHONMALLOC=malloc PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260524-dma-reinterpret-alias-unification:/home/lfr/kernelcode_generate python3 -m expectation.pass.hoist_dma_alias_ops`
  - 结果：exit 1；仍失败在 `slice` family，包含 `symbol.mul %n, %kh` CHECK not found。动态 conv2d dump 子项因本计划插入 `07-dma-alias-to-reinterpret` 后编号后移，期望旧路径 `17-hoist-dma-alias-ops.mlir` 不存在；实际候选 dump 存在 `18-hoist-dma-alias-ops.mlir`。
- latest main：使用临时 pristine worktree `origin/main=5e1019a31910e7641c1874118e8045818273a184` 运行同一 expectation。
  - 结果：exit 1；同在 `slice` family，包含同一 `symbol.mul %n, %kh` CHECK not found，且 dynamic conv2d weight slice 仍为高维 `dma.slice`。
- 隔离结论：`expectation.pass.hoist_dma_alias_ops` 为 latest-main 既有失败隔离项；本轮未修改 `kernel_gen/passes/hoist_dma_alias_ops.py` 或 `expectation/pass/hoist_dma_alias_ops/**`，不作为通过依据。

### 静态门禁与敏感目录

- `PYTHONDONTWRITEBYTECODE=1 python3 -m compileall -q kernel_gen/dialect/dma kernel_gen/passes kernel_gen/pipeline kernel_gen/dsl/gen_kernel/emit test/dialect/dma test/passes test/dsl/gen_kernel/emit`：exit 0。
- AST parse：`kernel_gen/dialect/dma/operation/alias.py`、`kernel_gen/passes/dma_alias_to_reinterpret.py`、`kernel_gen/passes/memory_pool.py`、`kernel_gen/passes/symbol_buffer_hoist.py`、`kernel_gen/dsl/gen_kernel/emit/npu_demo/dma/reinterpret.py`、新增相关测试均通过。
- `rg -n "DmaReinterpretOp|dma\\.reinterpret|dma-alias-to-reinterpret|DmaAliasToReinterpretPass" spec kernel_gen test`：exit 0，共 323 处命中，覆盖 spec / 实现 / test。
- `reinterpret` rank / numel equality 冲突扫描：exit 0，`no reinterpret rank/numel equality conflict`。
- 旧 alias 口径扫描：exit 0，`old_alias_scan_ok`。
- runtime 能力探测扫描：exit 0，`ctx_probe_scan_ok`。
- 跨文件私有 helper / dma internal helper 扫描：exit 0，`private_api_scan_ok`。
- 嵌套函数扫描：exit 0，`nested_function_scan_ok_except_registry_decorator`；唯一例外是既有 `kernel_gen/passes/registry.py` decorator 闭包实现。
- `git diff --check && git diff --cached --check`：exit 0。
- 敏感目录 / 共享状态 / 计划资产：
  - `git diff --name-only -- expectation .skills agents/standard AGENTS.md TODO.md DONE.md ARCHITECTURE spec/API.md`：空。
  - `git diff --cached --name-only -- expectation .skills agents/standard AGENTS.md TODO.md DONE.md ARCHITECTURE spec/API.md`：空。
  - `git status --short --untracked-files=all -- expectation .skills agents/standard AGENTS.md TODO.md DONE.md ARCHITECTURE spec/API.md`：空。
  - `git status --short --untracked-files=all -- kernel/dump`：空。

### 自检

- 已基于 latest 同步现场复核 `HEAD` / `origin/main` / `merge-base` / ahead-behind 和候选相对主线交集。
- 已按实际 diff 反推 pytest，expectation 单列为合同验收，未替代 pytest。
- 已核对公开 API 用户确认来源、spec / 实现 / test 一致性、P1 spec 冲突闭合、memory-pool 方案 A、downstream alias 识别、emit 路径、跨文件私有 API、runtime 能力探测和敏感目录。
- 本轮未修改候选功能实现、spec、test、expectation 或计划书；只写入本任务记录。
- 未发现公开 API、expectation 授权、tracked 合同落地、口径冲突或不确定项待用户确认。

结论：第二轮计划级架构复核 / 终验通过。无最小阻断项，无需用户确认；可进入 merge，本轮不直接 merge。

## merge 合入记录 - 李白 - 2026-05-24

时间：2026-05-24 04:59 +0800
经办人：李白
任务：T-20260524-b30e8d52 / dma_reinterpret_alias_unification
任务目标：按合并规范核对 latest main、候选 diff、计划与任务记录、复跑关键 gate，并将代码 / spec / test 与任务记录同批合入。

### 最新同步现场

- 执行目录：`/home/lfr/kernelcode_generate/wt-20260524-dma-reinterpret-alias-unification`。
- `git fetch origin main`：exit 0。
- 基线：`HEAD=5e1019a31910e7641c1874118e8045818273a184`，`origin/main=5e1019a31910e7641c1874118e8045818273a184`，`merge-base=5e1019a31910e7641c1874118e8045818273a184`，ahead / behind=`0 / 0`。
- 候选 diff 为当前 worktree 未提交改动；`HEAD..origin/main` 路径交集为空，无文本冲突。
- 管理员更正已纳入：第二轮终验摘要中 `256` 为笔误；本轮 merge 复跑最低 pytest 实际结果为 `258 passed, 1 warning`，未写作 `256`。

### 实际合入范围

- 实现：`kernel_gen/dialect/dma/**`、`kernel_gen/dsl/gen_kernel/emit/**`、`kernel_gen/passes/{arch_parallelize,memory_plan,memory_pool,producer_consumer_analysis,registry,symbol_buffer_hoist,dma_alias_to_reinterpret}.py`、`kernel_gen/passes/template_name/default_constraints.py`、`kernel_gen/pipeline/npu_demo_lowering.py`。
- spec：`spec/dialect/dma.md`、`spec/operation/dma.md`、`spec/dsl/gen_kernel/emit*.md`、`spec/pass/{arch_parallelize,dma_alias_to_reinterpret,hoist_dma_alias_ops,lowering/memory_pool,memory_plan,pipeline/npu_demo_lowering,producer_consumer_analysis,registry,symbol_buffer_hoist,template_name_default_constraints}.md`。
- test：`test/dialect/dma/**`、`test/dsl/gen_kernel/emit/test_package.py`、`test/passes/**` 中本任务相关测试。
- 记录：`agents/codex-multi-agents/log/task_records/2026/24/20260524-dma-reinterpret-alias-unification.md`。
- 未带入 `expectation/`、`.skills/`、`agents/standard/`、`AGENTS.md`、`TODO.md`、`DONE.md`、`ARCHITECTURE/`、`spec/API.md`。

### 复跑验证

- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q -p no:cacheprovider test/dialect/dma/test_reinterpret.py test/passes/test_dma_alias_to_reinterpret.py test/passes/test_registry.py test/passes/pipeline/test_npu_demo_lowering.py test/passes/test_producer_consumer_analysis.py test/passes/test_memory_plan.py test/passes/test_symbol_buffer_hoist.py test/passes/test_memory_pool.py test/dsl/gen_kernel/emit/test_package.py`
  - 结果：exit 0，`258 passed, 1 warning`。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q -p no:cacheprovider test/dialect/dma/test_reinterpret.py test/passes/test_dma_alias_to_reinterpret.py`
  - 结果：exit 0，`10 passed, 1 warning`。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q -p no:cacheprovider test/passes/test_arch_parallelize.py test/passes/test_template_name_constraints.py test/passes/test_template_name_infer.py -x --tb=short`
  - 结果：exit 0，`35 passed, 1 warning`。
- `PYTHONDONTWRITEBYTECODE=1 python3 -m compileall -q kernel_gen/dialect/dma kernel_gen/passes kernel_gen/pipeline kernel_gen/dsl/gen_kernel/emit test/dialect/dma test/passes test/dsl/gen_kernel/emit`
  - 结果：exit 0。
- AST parse：`kernel_gen/dialect/dma/operation/alias.py`、`kernel_gen/passes/dma_alias_to_reinterpret.py`、`kernel_gen/passes/memory_pool.py`、`kernel_gen/passes/symbol_buffer_hoist.py`、`kernel_gen/dsl/gen_kernel/emit/npu_demo/dma/reinterpret.py`、`test/dialect/dma/test_reinterpret.py`、`test/passes/test_dma_alias_to_reinterpret.py` 全部通过。
- public API exact gate：`DmaReinterpretOp` 三个公开导入路径同源，`Dma.operations` 包含 `dma.reinterpret`，`build_registered_pass("dma-alias-to-reinterpret", {"fold": "false"})` 返回 `DmaAliasToReinterpretPass(fold=False)`，exit 0。
- 静态 matmul demo：`timeout 180s env PYTHONMALLOC=malloc PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 kernel/matmul/inputs_static_tile_static.py`
  - 结果：exit 0；absent / present bias `max_abs_diff=3.4332275390625e-05`。
- dump marker gate：`07-dma-alias-to-reinterpret.mlir` 含 `dma.reinterpret` 且不含 `dma.view` / `dma.reshape` / `dma.subview`；`23-memory-pool.mlir` 含 `arch.get_dynamic_memory` 与 `dma.reinterpret`，且不含 `dma.view` / `dma.reshape`。

### 只读 expectation 与 latest-main 既有失败隔离

- 导入来源探针：`expectation.pass.dma_alias_to_reinterpret.__main__`、`reshape`、`view`、`subview` 均来自主仓 `/home/lfr/kernelcode_generate/expectation/pass/dma_alias_to_reinterpret/...`；候选实现模块来自任务 worktree。
- 授权 expectation manifest 恰为 4 文件，sha256：
  - `__main__.py` = `6eeeec322ada03803347630905d536b37158717c32dcf39fcb2514b9dd6c346a`
  - `reshape.py` = `dd3d7bc53e63e3f6e2e14ae56b3c59f5fc3539f171675534869fef1c33c8357f`
  - `view.py` = `0bc0a210737d704d81242b2f1edb09402ba57cdbf5eec8b7cb99345bd2da75d8`
  - `subview.py` = `b772e6871ff6db57078c90709360f77fb8ab2358fc136090aa7a43b29ab71312`
- `PYTHONMALLOC=malloc PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260524-dma-reinterpret-alias-unification:/home/lfr/kernelcode_generate python3 -m expectation.pass.dma_alias_to_reinterpret`：exit 0。
- `PYTHONMALLOC=malloc PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260524-dma-reinterpret-alias-unification:/home/lfr/kernelcode_generate python3 -m expectation.pass.symbol_buffer_hoist`：exit 0。
- `PYTHONMALLOC=malloc PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260524-dma-reinterpret-alias-unification:/home/lfr/kernelcode_generate python3 -m expectation.pass.producer_consumer_analysis`：exit 0。
- `PYTHONMALLOC=malloc PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260524-dma-reinterpret-alias-unification:/home/lfr/kernelcode_generate python3 -m expectation.pass.memory_plan`：exit 0。
- `expectation.pass.hoist_dma_alias_ops`：候选与 latest main 均 exit 1，失败同在 `slice` family，包含 `symbol.mul %n, %kh` CHECK not found 与动态 conv2d weight slice 仍为高维 `dma.slice`；按终验结论隔离为 latest-main 既有失败，不作为通过项。

### 静态核对与敏感目录

- `rg -n "DmaReinterpretOp|dma\\.reinterpret|dma-alias-to-reinterpret|DmaAliasToReinterpretPass" spec kernel_gen test | wc -l`：`323`。
- reinterpret rank / numel equality 冲突扫描：exit 0，`no reinterpret rank/numel equality conflict`。
- 旧 alias 口径扫描：exit 0，`old_alias_scan_ok`。
- runtime 能力探测 / 跨文件私有 helper 扫描：exit 0，`static_forbidden_patterns_absent`。
- `git diff --check && git diff --cached --check`：exit 0。
- 敏感目录 / 共享状态 / 计划资产空 diff：
  - `git diff --name-only -- expectation .skills agents/standard AGENTS.md TODO.md DONE.md ARCHITECTURE spec/API.md`：空。
  - `git diff --cached --name-only -- expectation .skills agents/standard AGENTS.md TODO.md DONE.md ARCHITECTURE spec/API.md`：空。
  - `git status --short --untracked-files=all -- expectation .skills agents/standard AGENTS.md TODO.md DONE.md ARCHITECTURE spec/API.md`：空。
  - `git status --short --untracked-files=all -- kernel/dump`：空。

### 冲突处理、剩余风险与清理状态

- 冲突处理：latest main 未前进，未发生合并冲突；未手工改动候选实现 / spec / test，只追加本合并记录。
- 剩余风险：`expectation.pass.hoist_dma_alias_ops` 是 latest-main 既有失败隔离项，未作为通过依据；未运行 full expectation。
- worktree / 分支清理状态：本轮不清理 `/home/lfr/kernelcode_generate/wt-20260524-dma-reinterpret-alias-unification` 与 `task/dma-reinterpret-alias-unification` 分支，原因是当前只有 merge 授权，历史清理范围需管理员 / 用户另行确认，且已有流程要求未明确授权不得擅自删除 worktree / 分支。

结论：merge 前核对通过，可将候选代码 / spec / test 与本任务记录同批提交、ff 合入并推送 `origin/main`；合并后执行 `-done` 并回报最终提交号。
