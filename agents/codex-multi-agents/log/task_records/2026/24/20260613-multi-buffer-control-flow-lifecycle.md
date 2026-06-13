时间：2026-06-13 18:16 +0800
经办人：金铲铲大作战
任务：T-20260613-6ccd1b8f / multi-buffer-control-flow-lifecycle / execute
任务目标：按 ARCHITECTURE/plan/multi_buffer_control_flow_lifecycle.md 完成 multi-buffer 控制流生命周期分析闭环，更新 spec、实现、pytest、dump 验收与任务记录，完成后流转 review。

执行前阅读记录：
- 已读根 AGENTS.md、agents/codex-multi-agents/agents/金铲铲大作战/金铲铲大作战.prompt.md、agents/standard/任务记录约定.md。
- 已复查主仓 TODO.md：T-20260613-6ccd1b8f 为 execute / 金铲铲大作战 / 进行中；任务 worktree 内无 TODO.md，按标准文档使用主仓 TODO.md 为状态源。
- 已读计划书 ARCHITECTURE/plan/multi_buffer_control_flow_lifecycle.md、正式候选 dump expected、现有 spec/pass/memory/multi_buffer.md、spec/dialect/symbol.md、kernel_gen/passes/memory/multi_buffer.py、kernel_gen/dialect/symbol/operation/control_flow.py、test/passes/memory/test_multi_buffer.py、test/dialect/symbol/test_symbol.py、test/passes/pipeline/test_npu_demo_lowering.py。
- 执行前 worktree staged name-status 仅 A ARCHITECTURE/plan/multi_buffer_control_flow_lifecycle.md 与 A kernel/dump/matmul/inputs_static_tile_static_present_bias/matmul_inputs_static_tile_static_kernel/24-multi-buffer-analysis-if-path-expected.mlir；无 expectation diff。

计划内小任务卡核对：
- S1 spec：已更新 multi_buffer 列表属性、control-flow id、main / 最大 depth auto / 非最大 depth fixed=2 合同；已更新 symbol.for 额外 attrs round-trip 合同。
- S2 analysis：已实现 symbol.for / scf.if analysis id、共同外层 loop lifecycle、if path candidate discovery、列表 update/use points。
- S3 apply：已按列表属性重新校验并复用原 ring 物化逻辑；main 写 num=1，最大 depth auto 保留 target capacity/reserved 闭合，非最大 depth fixed=2。
- S4 测试与 dump：已补 multi-buffer if path analysis/apply pytest、SymbolForOp extra attrs round-trip、pipeline dump 断言。
- S5 expectation：本 worktree 不存在 expectation 目录；执行前后 expectation status/content 指纹均为 e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855；未修改、未新增、未移动、未删除 expectation。

改动：
- kernel_gen/passes/memory/multi_buffer.py
  - 将旧 multi_buffer.update_point / use_point 单值属性迁移为 multi_buffer.update_points / use_points 列表属性。
  - 新增 analysis.loop_id / analysis.if_id 分配与保留逻辑，id 形如 loopN-D / ifN-D。
  - loop staging 候选从“同一最近 symbol.for 直接 body”扩展为“所有 access 可收口到最深共同 symbol.for”，支持 nested loop 与 scf.if branch。
  - use_points 按目标 loop body 控制流锚点顺序去重；dma.broadcast 与 kernel.binary_elewise 纳入 progress use，覆盖 present-bias bias_full scratch。
  - analysis_num 按 main、区域最大 depth、非最大 depth 规则写 1 / auto / memory_stage / 2。
- kernel_gen/dialect/symbol/operation/control_flow.py
  - SymbolForOp 自定义语法打印完整 attr dict，parse attr dict 并保留 iter 之外额外 attrs。
- spec/pass/memory/multi_buffer.md、spec/dialect/symbol.md
  - 同步新合同与测试矩阵。
- test/passes/memory/test_multi_buffer.py
  - 旧断言迁移为 update_points/use_points。
  - 新增 if path direct slice analysis/apply 测试，覆盖 analysis.loop_id / analysis.if_id、非最大 depth fixed=2、branch 内 use 替换。
- test/dialect/symbol/test_symbol.py
  - 新增 SymbolForOp extra attrs round-trip 测试。
- test/passes/pipeline/test_npu_demo_lowering.py
  - pipeline dump 断言迁移到 analysis.loop_id 与列表属性名。

最小功能闭环：
- analysis 阶段先补 control-flow id，再在 alloc 上写列表 points 与 num；不物化 ring。
- apply 阶段重新发现同一 lifecycle candidate，要求列表 points 与 num 属性匹配后才物化 ring 并删除原 alloc/free。
- if path、nested loop 和 present-bias 场景均通过公开 pass API / pipeline / dump 脚本验证；unsupported 或无法证明共同 loop 的生命周期继续 no-op。
- 未新增 pass class、registry 名、构造参数、package re-export、LoopSoftPipelinePassError 或共享 ring_cursor_analysis API。

Diff 反推自测：
- multi_buffer.py / spec/pass/memory/multi_buffer.md / test/passes/memory/test_multi_buffer.py：
  - PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/passes/memory/test_multi_buffer.py test/passes/test_registry.py
  - 结果：89 passed，退出码 0。
- control_flow.py / spec/dialect/symbol.md / test/dialect/symbol/test_symbol.py：
  - PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/dialect/symbol/test_symbol.py
  - 结果：118 passed，退出码 0。
- 私有 API / 错误静态门禁：
  - PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/repo_conformance/test_private_api_boundaries.py test/tools/test_kernel_code_error_static_gate.py
  - 结果：8 passed，退出码 0。
- pipeline 顺序与 dump 断言：
  - PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/passes/pipeline/test_npu_demo_lowering.py -k 'dump or multi_buffer'
  - 结果：3 passed，退出码 0。
  - PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/passes/pipeline/test_npu_demo_lowering.py -k 'builds_pass_manager or pass_order or rejects_unknown_option or propagates_unsupported_structure or wraps_no_loop_body or skips_entry_point_dispatcher'
  - 结果：6 passed，退出码 0。
  - PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/passes/pipeline/test_npu_demo_lowering.py -k 'matmul_demo_allocs_hoist or symbol_hoist_pipeline_pattern_dump or supports_kernel_contract_style_public_chain'
  - 结果：3 passed，退出码 0。
  - 说明：完整单进程 PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/passes/pipeline/test_npu_demo_lowering.py 连续两次为 Signal 11；拆分后 11 个用例均已覆盖通过，判断为该文件重型 demo 累积运行的环境/native 崩溃风险，不作为本 diff 功能失败隐藏。
- dump 脚本：
  - PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 kernel/matmul/inputs_static_tile_static.py
  - 结果：退出码 0；最终 run shape_seed=848249242，tile_seed=1480206739；absent/present max_abs_diff=2.09808349609375e-05。
  - PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 kernel/matmul/inputs_static_tile_dynamic.py
  - 结果：退出码 0；最终 run shape_seed=546988862，tile_seed=1376508960；absent/present max_abs_diff=3.4332275390625e-05。
  - PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 kernel/matmul/inputs_dynamic_tile_dynamic.py
  - 结果：退出码 0；最终 run shape_seed=2146946374，tile_seed=1521716793；absent/present max_abs_diff=4.9591064453125e-05。
- present-bias dump 结构合同：
  - 脚本核对 kernel/dump/matmul/inputs_static_tile_static_present_bias/matmul_inputs_static_tile_static_kernel/24-multi-buffer-analysis.mlir。
  - 断言均为 True：top if id、pattern0 loop1/2/3 ids、pattern0 acc fixed、pattern0 bias fixed、pattern0 K auto、pattern1 acc fixed、pattern1 bias fixed、pattern1 K auto。
  - 说明：inputs_static_tile_static.py 默认入口每次用 SystemRandom 选择 shape/tile，因此 24-multi-buffer-analysis-if-path-expected.mlir 与当前 actual 不能做 byte-level cmp；本轮按结构字段验收正式 expected 表达的合同，且未修改 expected 本体。
- 格式检查：
  - git diff --check && git diff --cached --check
  - 结果：退出码 0。

减法检查：
- 替代旧逻辑：
  - 删除旧 multi_buffer.update_point / use_point 单值属性路径，替换为列表属性读写与 apply 校验。
  - 删除 loop staging “所有 access 必须在目标 loop 直接 body”限制，替换为最深共同 symbol.for + 控制流锚点定位。
  - 删除 binary_elewise access 直接跳过限制，改为可证明 if/binary/broadcast 生命周期候选。
- 保留旧逻辑：
  - 保留旧 matmul lhs/rhs direct pair 专用路径，防止 loop staging 抢占成对合同。
  - 保留 current block 已有 ring no-op、dynamic shape 可支配性、target capacity/reserved、fixed/auto 分组逻辑。
- 新增 / 改动 private callable：
  - kernel_gen/passes/memory/multi_buffer.py 主要新增为 _MultiBufferRewriteRules 内公开命名 static methods，服务当前文件公开 pass，不是跨文件 API；现有 _rewrite_matmul_if_pair 与 _rewrite_loop_staging_candidates 仅调用当前文件内公开命名 static methods。
  - test/passes/memory/test_multi_buffer.py 新增 _string_attr_array、_string_array_values、_build_if_path_direct_slice_module；均不少于 5 行有效代码，且不调用同文件 private callable。
  - 静态门禁 test/repo_conformance/test_private_api_boundaries.py 已通过，确认无 under-5 或 private-callable chaining 违规。

敏感范围：
- git diff --name-status -- expectation .skills agents/standard AGENTS.md TODO.md DONE.md agents/codex-multi-agents/agents-lists.md：空。
- git diff --cached --name-status -- expectation .skills agents/standard AGENTS.md TODO.md DONE.md agents/codex-multi-agents/agents-lists.md：空。
- expectation status 指纹：e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855。
- expectation content 指纹：e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855。
- expectation 目录在该 worktree 不存在；未读取到可运行 expectation 包，未把 expectation 纳入 staged/unstaged diff。

自检：
- 接口：未改 MultiBufferAnalysisPass / MultiBufferApplyPass / MultiBufferPass 构造签名、registry 名、pipeline 公开参数或 package re-export；SymbolForOp 签名不变，仅保留额外 attrs round-trip。
- 边界：unsupported、无共同 loop、跨 sibling/loop 外 escape、已有 current、缺属性、属性类型不匹配均保持 no-op。
- 异常/兼容：未新增公开错误文本；旧单值临时属性不再作为本合同路径支持，符合本计划列表属性迁移。
- 实现遗漏：present-bias 中 acc/bias_full/bias_tile/K-loop candidate 已覆盖；main / 非最大 fixed / 最大 auto 三类 num 已覆盖。
- 冗余/复用：新增逻辑集中在 _MultiBufferRewriteRules，未新增跨文件公共 API；测试只调用公开 pass 与公开 dialect API。
- 函数粒度：control id、domain、depth、列表 attr、num 计算拆分为当前文件内复用点；没有函数体内嵌套函数。
- 输入输出：StringAttr / ArrayAttr 类型均校验；num 正整数 / auto 保持原解析规则。
- 资源/性能：analysis 只按 module walk 与候选 access 线性扫描；未新增全局求解或跨模块状态。
- 测试有效性：新增测试在 if_id、列表 points、fixed=2、branch use replacement 任一失效时会失败；dump 结构验收覆盖计划 present-bias 关键字段。

结论：execute 主体完成；实现、spec、pytest、dump 验收、敏感范围和记录已收口。下一步按计划级链路流转 review，不进入 archive_acceptance 或 merge。

时间：2026-06-13 18:21 +0800
经办人：金铲铲大作战
任务：T-20260613-6ccd1b8f / execute -> review 标准流转补记
任务目标：记录本次实际 -next -type review -auto 流转、脚本输出、流转后状态复查和敏感范围复查。

实际命令：
```bash
bash skills/codex-multi-agents/scripts/codex-multi-agents-task.sh \
  -file /home/lfr/kernelcode_generate/TODO.md \
  -next \
  -task_id T-20260613-6ccd1b8f \
  -from "金铲铲大作战" \
  -type review \
  -message "review；任务目标：审查 T-20260613-6ccd1b8f multi-buffer 控制流生命周期分析闭环的 spec、实现、pytest、dump 验收、Diff 反推自测、敏感范围和任务记录；计划级链路 execute -> review -> archive_acceptance -> merge/归档；任务链记录：agents/codex-multi-agents/log/task_records/2026/24/20260613-multi-buffer-control-flow-lifecycle.md。" \
  -agents-list /home/lfr/kernelcode_generate/agents/codex-multi-agents/agents-lists.md \
  -auto
```

首次输出：
```text
ERROR(1): cannot resolve canonical agents list; set CODEX_MULTI_AGENTS_AGENTS_FILE or AGENTS_FILE
```

处理说明：任务 worktree 内脚本将当前 worktree 作为 REPO_ROOT，未从配置解析到主仓 canonical agents-list；未改变任务状态。随后显式设置 CODEX_MULTI_AGENTS_AGENTS_FILE 为主仓 agents-lists.md 后重试。

实际成功命令：
```bash
CODEX_MULTI_AGENTS_AGENTS_FILE=/home/lfr/kernelcode_generate/agents/codex-multi-agents/agents-lists.md \
bash skills/codex-multi-agents/scripts/codex-multi-agents-task.sh \
  -file /home/lfr/kernelcode_generate/TODO.md \
  -next \
  -task_id T-20260613-6ccd1b8f \
  -from "金铲铲大作战" \
  -type review \
  -message "review；任务目标：审查 T-20260613-6ccd1b8f multi-buffer 控制流生命周期分析闭环的 spec、实现、pytest、dump 验收、Diff 反推自测、敏感范围和任务记录；计划级链路 execute -> review -> archive_acceptance -> merge/归档；任务链记录：agents/codex-multi-agents/log/task_records/2026/24/20260613-multi-buffer-control-flow-lifecycle.md。" \
  -agents-list /home/lfr/kernelcode_generate/agents/codex-multi-agents/agents-lists.md \
  -auto
```

完整脚本输出：
```text
OK: next T-20260613-6ccd1b8f
OK: replace 金铲铲大作战 状态
OK: auto-dispatch T-20260613-6ccd1b8f -> 不要啊教练
OK: replace 不要啊教练 状态
OK: talk 金铲铲大作战 -> 不要啊教练 (不要啊教练)
OK: talk 金铲铲大作战 -> 神秘人 (神秘人)
```

流转后复查：
- TODO.md：/home/lfr/kernelcode_generate/TODO.md 显示 T-20260613-6ccd1b8f 为 review / 不要啊教练 / 进行中；计划书 ARCHITECTURE/plan/multi_buffer_control_flow_lifecycle.md 仍为 1 个待完成任务进行中。
- agents-list：/home/lfr/kernelcode_generate/agents/codex-multi-agents/agents-lists.md 显示 金铲铲大作战 free、不要啊教练 busy。
- talk.log：/home/lfr/kernelcode_generate/agents/codex-multi-agents/log/talk.log 尾部包含：
  - @金铲铲大作战向@不要啊教练发起会话：请处理任务 T-20260613-6ccd1b8f（review；任务目标：审查 T-20260613-6ccd1b8f multi-buffer 控制流生命周期分析闭环...）
  - @金铲铲大作战向@神秘人发起会话：任务 T-20260613-6ccd1b8f 已完成当前阶段，已回到任务列表；新任务类型=review，已经指派给-> 不要啊教练。

验证：
- git diff --check && git diff --cached --check：退出码 0，无输出。
- git diff --name-status -- expectation .skills agents/standard AGENTS.md TODO.md DONE.md agents/codex-multi-agents/agents-lists.md：空。
- git diff --cached --name-status -- expectation .skills agents/standard AGENTS.md TODO.md DONE.md agents/codex-multi-agents/agents-lists.md：空。
- staged name-status 仍为本任务候选：A ARCHITECTURE/plan/multi_buffer_control_flow_lifecycle.md；A agents/codex-multi-agents/log/task_records/2026/24/20260613-multi-buffer-control-flow-lifecycle.md；A kernel/dump/matmul/inputs_static_tile_static_present_bias/matmul_inputs_static_tile_static_kernel/24-multi-buffer-analysis-if-path-expected.mlir；M kernel_gen/dialect/symbol/operation/control_flow.py；M kernel_gen/passes/memory/multi_buffer.py；M spec/dialect/symbol.md；M spec/pass/memory/multi_buffer.md；M test/dialect/symbol/test_symbol.py；M test/passes/memory/test_multi_buffer.py；M test/passes/pipeline/test_npu_demo_lowering.py。

自检：
- 本段仅补 execute -> review 流转记录并暂存；未改实现、spec、测试或计划验收结论。
- 未进入 archive_acceptance 或 merge。
- 未修改、新建、移动、删除或重命名 expectation；expectation/.skills/agents/standard/AGENTS.md/TODO.md/DONE.md/agents-lists 敏感范围空 diff。

结论：T-20260613-6ccd1b8f 已成功流转到 review / 不要啊教练 / 进行中；金铲铲大作战已释放为 free，等待 review 结论。

时间：2026-06-13 18:37 +0800
经办人：不要啊教练
任务：T-20260613-6ccd1b8f / multi-buffer-control-flow-lifecycle / review
任务目标：审查 multi-buffer 控制流生命周期分析闭环的 spec、实现、pytest、dump 验收、Diff 反推自测、减法检查、敏感范围和任务记录；若通过只流转 archive_acceptance，不进入 merge。

最新同步现场：
- 执行目录：/home/lfr/kernelcode_generate/wt-20260613-multi-buffer-control-flow-lifecycle。
- 分支：task/multi-buffer-control-flow-lifecycle。
- `git fetch --prune origin main`：退出码 0。
- `git rev-parse HEAD`：ed33fcf8a0a031b9c3753e3d2339d5058f875169。
- `git rev-parse origin/main`：ed33fcf8a0a031b9c3753e3d2339d5058f875169。
- `git merge-base HEAD origin/main`：ed33fcf8a0a031b9c3753e3d2339d5058f875169。
- `git rev-list --left-right --count HEAD...origin/main`：`0 0`。
- 判断：当前 worktree 与 latest main 基线一致，无主线覆盖风险。

审查范围：
- 已读根 AGENTS.md、agents/codex-multi-agents/agents/不要啊教练/不要啊教练.prompt.md、agents/standard/任务记录约定.md、agents/standard/审查规范.md。
- 已核对计划书 ARCHITECTURE/plan/multi_buffer_control_flow_lifecycle.md、任务记录尾部 execute 主体记录与 execute -> review 标准流转补记；管理员已解除只读预检限制。
- 被审 staged diff：
  - A ARCHITECTURE/plan/multi_buffer_control_flow_lifecycle.md
  - A agents/codex-multi-agents/log/task_records/2026/24/20260613-multi-buffer-control-flow-lifecycle.md
  - A kernel/dump/matmul/inputs_static_tile_static_present_bias/matmul_inputs_static_tile_static_kernel/24-multi-buffer-analysis-if-path-expected.mlir
  - M kernel_gen/dialect/symbol/operation/control_flow.py
  - M kernel_gen/passes/memory/multi_buffer.py
  - M spec/dialect/symbol.md
  - M spec/pass/memory/multi_buffer.md
  - M test/dialect/symbol/test_symbol.py
  - M test/passes/memory/test_multi_buffer.py
  - M test/passes/pipeline/test_npu_demo_lowering.py

发现：
- 阻断 / 新增审查发现：kernel_gen/passes/memory/multi_buffer.py:2225 在 `MultiBufferApplyPass.apply` 中调用 `_MultiBufferRewriteRules.region_labels(module)`；而 region_labels 在 kernel_gen/passes/memory/multi_buffer.py:682-694 委托 ensure_control_flow_ids，ensure_control_flow_ids 会在 kernel_gen/passes/memory/multi_buffer.py:620-680 写入 `analysis.loop_id` / `analysis.if_id`。这导致 apply-only 即使没有任何 `multi_buffer.*` 候选，也会修改控制流 op。计划用户确认 ARCHITECTURE/plan/multi_buffer_control_flow_lifecycle.md:23 明确“`multi-buffer-analysis` 第一件事是给控制流编号”，spec/pass/memory/multi_buffer.md:65-84 把控制流 id 写入归在 Analysis 合同，spec/pass/memory/multi_buffer.md:86-95 则规定 apply 只处理带三项 `multi_buffer.*` 属性的候选。影响：公开 `MultiBufferApplyPass` 的 no-op/只消费属性阶段边界被放宽，apply-only 在无候选 IR 上产生额外 `analysis.*` 输出，后续 dump 或下游 pass 会误以为 analysis 已执行；同时测试未覆盖该边界。最小返工动作：让 `MultiBufferApplyPass` 使用非写入式 label 读取/校验路径，或只在 analysis/facade 的 analysis 阶段补 id；apply-only 缺失必要 id 时应 no-op 或按 spec 明确失败，不得静默补 id。同步补 pytest：构造无 `multi_buffer.*` 的 `symbol.for` / `scf.if`，运行 `MultiBufferApplyPass` 后断言不新增 `analysis.loop_id` / `analysis.if_id`；构造 apply-only 带三项属性的合法输入时，应显式带上 analysis id 后再验证消费行为。验收方式：新增/调整测试失败后修复通过，并复跑 `pytest -q test/passes/memory/test_multi_buffer.py test/passes/test_registry.py`、`pytest -q test/dialect/symbol/test_symbol.py`、private/KCE、pipeline 分组、dump 结构检查、diff check 与敏感范围。

复现证据：
```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 - <<'PY'
from io import StringIO
from xdsl.context import Context
from xdsl.parser import Parser
from xdsl.printer import Printer
from xdsl.dialects.builtin import Builtin
from xdsl.dialects import func, scf
from kernel_gen.dialect.symbol import Symbol
from kernel_gen.dialect.dma import Dma
from kernel_gen.dialect.nn import Nn
from kernel_gen.dialect.kernel import Kernel
from kernel_gen.passes.memory.multi_buffer import MultiBufferApplyPass
ctx=Context()
for d in (Builtin, func.Func, scf.Scf, Symbol, Dma, Nn, Kernel):
    ctx.load_dialect(d)
module=Parser(ctx, '''
builtin.module {
  %c0 = symbol.const 0 : !symbol.int<#symbol.expr<0>>
  %c4 = symbol.const 4 : !symbol.int<#symbol.expr<4>>
  %c1 = symbol.const 1 : !symbol.int<#symbol.expr<1>>
  symbol.for %i = %c0 to %c4 step %c1 {iter = #symbol.iter<start = #symbol.expr<0>, end = #symbol.expr<4>, step = #symbol.expr<1>>} {
  }
}
''').parse_module()
MultiBufferApplyPass().apply(ctx, module)
stream=StringIO()
Printer(stream=stream).print_op(module)
print(stream.getvalue())
PY
```
输出关键行：
```text
symbol.for %i = %c0 to %c4 step %c1 {iter = #symbol.iter<start = #symbol.expr<0>, end = #symbol.expr<4>, step = #symbol.expr<1>>, analysis.loop_id = "loop1-1"} {
```
结论：输入中没有 `multi_buffer.*`，apply-only 仍新增了 `analysis.loop_id`，问题可稳定复现。

验证：
- `PYTHONDONTWRITEBYTECODE=1 python3 -m py_compile kernel_gen/passes/memory/multi_buffer.py kernel_gen/dialect/symbol/operation/control_flow.py test/passes/memory/test_multi_buffer.py test/dialect/symbol/test_symbol.py test/passes/pipeline/test_npu_demo_lowering.py`：退出码 0。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/passes/memory/test_multi_buffer.py test/passes/test_registry.py`：89 passed，退出码 0。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/dialect/symbol/test_symbol.py`：118 passed，退出码 0。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/repo_conformance/test_private_api_boundaries.py test/tools/test_kernel_code_error_static_gate.py`：8 passed，退出码 0。
- pipeline 分组覆盖：
  - `pytest -q test/passes/pipeline/test_npu_demo_lowering.py -k 'dump or multi_buffer'`：3 passed / 8 deselected，退出码 0。
  - `pytest -q test/passes/pipeline/test_npu_demo_lowering.py -k 'builds_pass_manager or pass_order or rejects_unknown_option or propagates_unsupported_structure or wraps_no_loop_body or skips_entry_point_dispatcher'`：6 passed / 5 deselected，退出码 0。
  - `pytest -q test/passes/pipeline/test_npu_demo_lowering.py -k 'matmul_demo_allocs_hoist or symbol_hoist_pipeline_pattern_dump or supports_kernel_contract_style_public_chain'`：3 passed / 8 deselected，退出码 0。
  - `pytest --collect-only -q test/passes/pipeline/test_npu_demo_lowering.py`：11 tests collected；三个分组 union 覆盖 11 个用例，其中 `symbol_hoist_pipeline_pattern_dump` 被第一组和第三组重复覆盖。执行人记录的完整单进程该文件 Signal 11 未作为本轮通过依据；本 review 采用拆分覆盖所有用例。
- dump 脚本：
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 kernel/matmul/inputs_static_tile_static.py`：退出码 0；本轮 shape_seed=1319592796，tile_seed=1251827331，absent/present max_abs_diff=2.6702880859375e-05。
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 kernel/matmul/inputs_static_tile_dynamic.py`：退出码 0；本轮 shape_seed=1330178048，tile_seed=406008204，absent/present max_abs_diff=3.814697265625e-05。
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 kernel/matmul/inputs_dynamic_tile_dynamic.py`：退出码 0；本轮 shape_seed=1006083070，tile_seed=726997430，absent/present max_abs_diff=3.4332275390625e-05。
- present-bias dump 结构检查：
  - 路径：kernel/dump/matmul/inputs_static_tile_static_present_bias/matmul_inputs_static_tile_static_kernel/24-multi-buffer-analysis.mlir。
  - 核对结果均为 True：top_if_id、pattern0 loop1/2/3 id、pattern0 `%11` fixed `loop2-2/loop3-3/if2-2`、pattern0 `%12/%13` fixed `loop2-2/if2-2`、pattern0 K auto、pattern1 loop4/5/6 id、pattern1 `%11` fixed `loop5-2/loop6-3/if3-2`、pattern1 `%12/%13` fixed `loop5-2/if3-2`、pattern1 K auto。
  - `25-multi-buffer-apply.mlir` 含 `dma.make_ring/current_ring/advance_ring`，未命中 `multi_buffer.*` 残留。
- `git diff --check && git diff --cached --check`：退出码 0，无输出。
- `git diff --name-status`：空；除 staged 候选和 ignored dump/cache 外，无 tracked unstaged diff。

Diff 反推审查：
- multi_buffer.py / spec/pass/memory/multi_buffer.md / test/passes/memory/test_multi_buffer.py：已复跑 multi-buffer + registry，且人工核对列表属性、control id、candidate discovery、analysis/apply 同源校验；新增阻断项来自 apply-only 无候选副作用。
- control_flow.py / spec/dialect/symbol.md / test/dialect/symbol/test_symbol.py：已复跑 symbol 测试；`symbol.for` extra attrs round-trip 覆盖新增 `analysis.loop_id` 保留。
- test/passes/pipeline/test_npu_demo_lowering.py 与 dump expected：已复跑 pipeline 分组和三个 dump 入口，并用结构检查核对用户点名 `%11/%12/%13/%15/%16/%20/%21`。
- expectation：本轮计划明确不新增必过 expectation；review 只核对禁止修改面和指纹，不把 expectation 当作 Diff 反推测试。

减法审查：
- 已核对执行人记录的旧逻辑替代：旧 `multi_buffer.update_point/use_point` 单值路径被列表属性替代；旧 direct body 限制被最深共同 `symbol.for` + control domain 分析替代；旧 binary_elewise access 直接跳过被支持 if/broadcast 生命周期候选替代。
- 保留旧逻辑依据充分：matmul lhs/rhs direct pair 兼容路径仍独立处理，现有 ring/current block no-op、dynamic shape 可支配性、capacity/reserved 与 no-op 边界仍保留。
- private callable / private API：新增测试 helper `_string_attr_array`、`_string_array_values`、`_build_if_path_direct_slice_module` 均不少于 5 行有效代码；未见测试跨文件直连 `_MultiBufferRewriteRules` 或 `_rewrite_*`；private/KCE gate 8 passed。
- 能力探测：本轮 staged diff 未在改动实现/spec/test 中新增 `analysis.control_path`、`multi_buffer.loop_id`、`multi_buffer.if_id` 或 ctx 能力探测；旧名 `multi_buffer.update_point/use_point` 只出现在计划书“当前基线”说明。

敏感范围：
- `git diff --name-status -- expectation .skills agents/standard AGENTS.md TODO.md DONE.md agents/codex-multi-agents/agents-lists.md`：空。
- `git diff --cached --name-status -- expectation .skills agents/standard AGENTS.md TODO.md DONE.md agents/codex-multi-agents/agents-lists.md`：空。
- `git diff --cached --name-status -- expectation/pass/multi_buffer expectation/pass/pipeline/npu_demo_lowering.py`：空。
- `git status --short --ignored --untracked-files=all -- expectation | LC_ALL=C sort | sha256sum`：e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855。
- expectation 目录在该 worktree 不存在；按空目录内容指纹核对为 e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855。

自检：
- 已逐项读取实际 diff，而不是只看执行摘要；已核对 execute 主体记录和 execute -> review 流转补记。
- 已先对齐 latest main，再审查 staged diff。
- 已完成 Diff 反推审查、减法审查、private callable / private API / KCE gate、sensitive diff 和 expectation 指纹核对。
- 已复跑计划与实际 diff 相关 pytest、pipeline 分组、dump 脚本和结构检查。
- 未修改实现、spec、测试、计划书、expectation、TODO/DONE、agents-list 或标准文档；本段仅写 review 记录。
- 结论严格按仍有可执行返工项处理，不进入 archive_acceptance 或 merge。

结论：review 不通过。最小阻断项为 `MultiBufferApplyPass` apply-only 无候选时仍写入 `analysis.loop_id/if_id` 的阶段边界问题；需回 execute 收口后重新 review。

时间：2026-06-13 18:40 +0800
经办人：不要啊教练
任务：T-20260613-6ccd1b8f / review -> execute 标准流转补记
任务目标：记录本次 review 不通过后实际 -next -type execute -auto 流转、完整脚本输出、流转后复查和自检；不进入 archive_acceptance 或 merge。

实际命令：
```bash
CODEX_MULTI_AGENTS_AGENTS_FILE=/home/lfr/kernelcode_generate/agents/codex-multi-agents/agents-lists.md \
bash skills/codex-multi-agents/scripts/codex-multi-agents-task.sh \
  -file /home/lfr/kernelcode_generate/TODO.md \
  -next \
  -task_id T-20260613-6ccd1b8f \
  -from "不要啊教练" \
  -type execute \
  -message "execute；任务目标：修复 T-20260613-6ccd1b8f review 指出的最小阻断项：MultiBufferApplyPass apply-only 在无 multi_buffer.* 候选时不得写入 analysis.loop_id/analysis.if_id；让 apply 使用非写入式 label 校验或要求 analysis 阶段已产出 id，并补对应 pytest，复跑 multi-buffer、symbol、private/KCE、pipeline 分组、dump 结构、diff check 与敏感范围；任务链记录：agents/codex-multi-agents/log/task_records/2026/24/20260613-multi-buffer-control-flow-lifecycle.md。" \
  -agents-list /home/lfr/kernelcode_generate/agents/codex-multi-agents/agents-lists.md \
  -auto
```

完整脚本输出：
```text
OK: next T-20260613-6ccd1b8f
OK: replace 不要啊教练 状态
OK: auto-dispatch T-20260613-6ccd1b8f -> 咯咯咯
OK: replace 咯咯咯 状态
OK: talk 不要啊教练 -> 咯咯咯 (咯咯咯)
OK: talk 不要啊教练 -> 神秘人 (神秘人)
```

流转后复查：
- TODO.md：/home/lfr/kernelcode_generate/TODO.md 显示 T-20260613-6ccd1b8f 为 execute / 咯咯咯 / 进行中；任务目标为修复 review 指出的 MultiBufferApplyPass apply-only 阶段边界阻断项。
- agents-list：/home/lfr/kernelcode_generate/agents/codex-multi-agents/agents-lists.md 显示 不要啊教练 free、咯咯咯 busy。
- talk.log：/home/lfr/kernelcode_generate/agents/codex-multi-agents/log/talk.log 尾部包含：
  - @不要啊教练向@咯咯咯发起会话：请处理任务 T-20260613-6ccd1b8f（execute；任务目标：修复 T-20260613-6ccd1b8f review 指出的最小阻断项...）
  - @不要啊教练向@神秘人发起会话：任务 T-20260613-6ccd1b8f 已完成当前阶段，已回到任务列表；新任务类型=execute，已经指派给-> 咯咯咯。

验证：
- `git diff --check && git diff --cached --check`：退出码 0，无输出。
- `git diff --name-status -- expectation .skills agents/standard AGENTS.md TODO.md DONE.md agents/codex-multi-agents/agents-lists.md`：空。
- `git diff --cached --name-status -- expectation .skills agents/standard AGENTS.md TODO.md DONE.md agents/codex-multi-agents/agents-lists.md`：空。
- `git diff --cached --name-status -- expectation/pass/multi_buffer expectation/pass/pipeline/npu_demo_lowering.py`：空。

自检：
- 本段仅补 review -> execute 流转记录并暂存；review 正文已在上一段写明不通过结论、阻断项、验证和自检。
- 未修改实现、spec、测试、计划书或 expectation；未改任务状态文件或 agents-list，只通过标准脚本流转。
- 未进入 archive_acceptance 或 merge。
- 敏感范围 expectation/.skills/agents/standard/AGENTS.md/TODO.md/DONE.md/agents-lists staged/unstaged diff 为空。

结论：T-20260613-6ccd1b8f 已按 review 不通过结论流转回 execute / 咯咯咯 / 进行中；不要啊教练已释放为 free，等待 execute 返工后重新 review。

时间：2026-06-13 18:50 +0800
经办人：咯咯咯
任务：T-20260613-6ccd1b8f / execute 返工收口
任务目标：修复 review 最小阻断项：`MultiBufferApplyPass` apply-only 在无 `multi_buffer.*` 候选时不得写入 `analysis.loop_id/analysis.if_id`；让 apply 使用非写入式 label 校验或要求 analysis 阶段已产出 id，并补对应 pytest，复跑 multi-buffer、symbol、private/KCE、pipeline 分组、dump 结构、diff check 与敏感范围；完成后只流转 review，不进入 archive_acceptance 或 merge。

执行前阅读记录：
- 已读根 `AGENTS.md`、`agents/codex-multi-agents/agents/咯咯咯/咯咯咯.prompt.md`、`agents/standard/任务记录约定.md`。
- 已核对 `TODO.md`：`T-20260613-6ccd1b8f` 当前为 `execute / 咯咯咯 / 进行中`。
- 已核对 agents-list：`咯咯咯=busy`。
- 已读本记录尾部：不要啊教练 review 不通过正文和 `review -> execute` 标准流转补记均可见，管理员已解除只读等待限制。
- 已读计划书 `ARCHITECTURE/plan/multi_buffer_control_flow_lifecycle.md`、`spec/pass/memory/multi_buffer.md`、`kernel_gen/passes/memory/multi_buffer.py`、`test/passes/memory/test_multi_buffer.py`，确认本轮唯一最小阻断为 apply-only 阶段边界。

返工收口：
- 审查问题：`MultiBufferApplyPass.apply` 调用 `_MultiBufferRewriteRules.region_labels(module)`，该入口委托 `ensure_control_flow_ids` 并会写入 `analysis.loop_id/analysis.if_id`，导致 apply-only 即使没有任何 `multi_buffer.*` 属性也会修改控制流。
- 修复动作：
  - `kernel_gen/passes/memory/multi_buffer.py` 新增 `_MultiBufferRewriteRules.existing_region_labels(module)`，只读取已有 `analysis.loop_id`，不写 `analysis.loop_id/analysis.if_id`。
  - `MultiBufferApplyPass.apply` 改用 `existing_region_labels`；matmul pair apply 缺少既有 loop label 时直接 no-op，不再使用 `"loop1"` fallback。
  - `_rewrite_loop_staging_candidates(..., mode="apply")` 继续接收只读 labels；缺失 target loop / if analysis id 时按现有校验 no-op。
  - `test/passes/memory/test_multi_buffer.py` 中合法 apply-only 手工属性输入显式设置 `analysis.loop_id`，防止测试靠隐式补 id 误通过。
  - 新增 `test_multi_buffer_apply_without_attrs_does_not_write_analysis_ids`：构造含 `symbol.for` / `scf.if` / inner `symbol.for` 的无三项属性输入，运行 `MultiBufferApplyPass` 后断言不新增 `analysis.loop_id/analysis.if_id`，不生成 ring，不残留 `multi_buffer.*`。
  - `spec/pass/memory/multi_buffer.md` 明确 Apply 合同：apply 不生成或补写 `analysis.loop_id/analysis.if_id`；apply-only 输入缺少 analysis 阶段已产出的控制流 id 时保持 no-op，并补 `TC-MULTI-BUFFER-002C`。

最小功能闭环：
- analysis / facade 的 analysis 阶段仍通过 `region_labels -> ensure_control_flow_ids` 写稳定 id。
- apply-only 阶段只消费已有 `multi_buffer.update_points/use_points/num` 和 analysis id；没有 `multi_buffer.*` 或缺少 analysis id 时 no-op，不产生额外 `analysis.*` 输出。
- 合法 apply-only 测试显式带上 analysis id 后仍能消费三项属性并物化 ring。

验证：
- 聚焦回归：`PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/passes/memory/test_multi_buffer.py -k 'apply_without_attrs_does_not_write_analysis_ids or apply_consumes_attrs_with_alignment_zero or apply_keeps_existing_current_pair_noop or apply_keeps_existing_current_direct_use_noop'`：退出码 `0`，`4 passed, 21 deselected, 1 warning in 1.71s`。
- py_compile：`PYTHONDONTWRITEBYTECODE=1 python3 -m py_compile kernel_gen/passes/memory/multi_buffer.py kernel_gen/dialect/symbol/operation/control_flow.py test/passes/memory/test_multi_buffer.py test/dialect/symbol/test_symbol.py test/passes/pipeline/test_npu_demo_lowering.py`：退出码 `0`，无输出。
- multi-buffer / registry：`PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/passes/memory/test_multi_buffer.py test/passes/test_registry.py`：退出码 `0`，`90 passed, 1 warning in 2.73s`。
- symbol：`PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/dialect/symbol/test_symbol.py`：退出码 `0`，`118 passed, 1 warning in 2.32s`。
- private / KCE：`PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/repo_conformance/test_private_api_boundaries.py test/tools/test_kernel_code_error_static_gate.py`：退出码 `0`，`8 passed in 3.65s`。
- review 复现脚本反证：用不要啊教练记录中的无 `multi_buffer.*` parser 输入运行 `MultiBufferApplyPass`，断言输出不含 `analysis.loop_id/analysis.if_id`：退出码 `0`，输出 `no analysis ids written`。
- pipeline collect：`PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest --collect-only -q test/passes/pipeline/test_npu_demo_lowering.py`：退出码 `0`，`11 tests collected in 2.36s`。
- pipeline 分组：
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/passes/pipeline/test_npu_demo_lowering.py -k 'dump or multi_buffer'`：退出码 `0`，`3 passed, 8 deselected, 1 warning in 6.75s`。
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/passes/pipeline/test_npu_demo_lowering.py -k 'builds_pass_manager or pass_order or rejects_unknown_option or propagates_unsupported_structure or wraps_no_loop_body or skips_entry_point_dispatcher'`：退出码 `0`，`6 passed, 5 deselected, 1 warning in 2.37s`。
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/passes/pipeline/test_npu_demo_lowering.py -k 'matmul_demo_allocs_hoist or symbol_hoist_pipeline_pattern_dump or supports_kernel_contract_style_public_chain'`：退出码 `0`，`3 passed, 8 deselected, 1 warning in 30.23s`。
- dump 脚本：
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 kernel/matmul/inputs_static_tile_static.py`：退出码 `0`；`shape_seed=1047643086`，`tile_seed=1714272074`，absent/present `max_abs_diff=2.288818359375e-05`。
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 kernel/matmul/inputs_static_tile_dynamic.py`：退出码 `0`；`shape_seed=898663388`，`tile_seed=316225356`，absent/present `max_abs_diff=3.0517578125e-05`。
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 kernel/matmul/inputs_dynamic_tile_dynamic.py`：退出码 `0`；`shape_seed=450119184`，`tile_seed=1227615714`，absent/present `max_abs_diff=3.0517578125e-05`。
- present-bias dump 结构：
  - 首次结构脚本按旧记录里的窄字符串检查 fixed 分组，退出码 `1`；原因是检查脚本误把当前 actual 的 `update_points=["loop2-2"]` / `use_points=["loop2-2","loop3-3","if2-2"]` 当成失败，不是 product diff 失败。
  - 随后读取实际 `24-multi-buffer-analysis.mlir` 与 `25-multi-buffer-apply.mlir`，按结构字段复查：`top_if_id`、pattern0 loop1/2/3 ids、pattern0 acc fixed、pattern0 bias fixed、pattern0 K auto、pattern1 loop4/5/6 ids、pattern1 acc fixed、pattern1 bias fixed、pattern1 K auto、apply has rings、apply no temp attrs 均为 `True`；退出码 `0`。
- 静态核对：`rg -n "region_labels\\(|existing_region_labels\\(|ensure_control_flow_ids\\(" kernel_gen/passes/memory/multi_buffer.py`：确认 `MultiBufferAnalysisPass` 仍调用写入式 `region_labels`，`MultiBufferApplyPass.apply` 调用只读 `existing_region_labels`。
- `git diff --check && git diff --cached --check`：退出码 `0`，无输出。
- 敏感范围：
  - `git diff --name-status -- expectation .skills agents/standard AGENTS.md TODO.md DONE.md agents/codex-multi-agents/agents-lists.md`：无输出。
  - `git diff --cached --name-status -- expectation .skills agents/standard AGENTS.md TODO.md DONE.md agents/codex-multi-agents/agents-lists.md`：无输出。
  - `git diff --cached --name-status -- expectation/pass/multi_buffer expectation/pass/pipeline/npu_demo_lowering.py`：无输出。
  - `git status --short --ignored --untracked-files=all -- expectation | LC_ALL=C sort | sha256sum`：`e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855`；该 worktree 无 expectation 目录内容变更。

Diff 反推自测：
- `kernel_gen/passes/memory/multi_buffer.py`：用聚焦回归、复现脚本、完整 multi-buffer/registry、pipeline 分组和 dump 结构覆盖 apply-only 不写 analysis id、合法 apply-only 消费属性、facade analysis+apply 仍生成 ring。
- `test/passes/memory/test_multi_buffer.py`：完整 multi-buffer/registry 90 passed 覆盖新增 TC 和既有 no-op / apply-only 路径。
- `spec/pass/memory/multi_buffer.md`：multi-buffer/registry、pipeline 分组和静态 `rg` 核对共同覆盖新增 Apply 合同；未修改公开 class 签名或 registry 参数。
- 未执行 full repo pytest；本轮 diff 仅三处文件，已按 review 要求和实际 diff 覆盖 multi-buffer、symbol、private/KCE、pipeline、dump、diff check 与敏感范围。

减法检查：
- 新增 / 改动 private callable：
  - 新增 `_MultiBufferRewriteRules.existing_region_labels(module)`，有效代码不少于 5 行，不调用其它 private callable，只读取 `SymbolForOp` 上已有 `analysis.loop_id`。
  - 改动 `MultiBufferApplyPass.apply`：从写入式 `region_labels` 改为只读 `existing_region_labels`，并删除 matmul apply 的 `"loop1"` fallback。
- 被替代旧逻辑：
  - 替代旧 apply-only 隐式调用 `ensure_control_flow_ids` 的副作用路径；apply 不再生成 `analysis.loop_id/analysis.if_id`。
  - 替代旧测试中手工三项属性但无 analysis id 仍可通过的隐式依赖；合法 apply-only 测试现在显式带 analysis id。
- 保留旧逻辑依据：
  - 保留 `region_labels -> ensure_control_flow_ids` 给 analysis / facade analysis 阶段使用，符合 Analysis 合同。
  - 保留 `_rewrite_loop_staging_candidates` 缺 label no-op 的现有校验方式，避免新增公开错误语义。
- 删除 / 未删除验证证据：
  - `rg` 显示 `MultiBufferApplyPass.apply` 只调用 `existing_region_labels`；写入式入口仍仅供 analysis 路径使用。
  - 聚焦回归和复现脚本证明无三项属性 apply-only 不再写 id。

自检：
- 接口：未新增、删除、重命名或修改公开 pass class、构造参数、registry 名、脚本参数或公开错误文本。
- 边界：apply-only 无 `multi_buffer.*` 候选不写 analysis id；apply-only 缺 analysis id no-op；analysis / facade 仍可写 id 并继续完成 ring 物化。
- 异常 / 兼容：没有新增抛错语义；缺 label 走 no-op，符合 apply 只消费 analysis 输出的阶段边界。
- 实现遗漏：matmul pair apply 和 loop staging apply 均使用只读 labels；测试覆盖无 attrs 的 `symbol.for`、`scf.if`、inner `symbol.for`。
- 冗余 / 复用 / 函数粒度：新增读取函数集中表达只读 label 语义，避免在 apply 中重复遍历逻辑；未新增跨文件 helper。
- 注释准确性：spec Apply 合同与测试矩阵已同步；`region_labels` doc 已不再宣称 apply 使用写入规则。
- 输入输出校验：existing labels 只接受非空 `StringAttr`；类型不匹配不进入 labels，apply no-op。
- 资源 / 性能：只读遍历 module 一次，与原写入式遍历同阶；没有新增全局状态或并发共享状态。
- 测试有效性：新增回归会在 apply 再次写 `analysis.loop_id/analysis.if_id` 时失败；合法 apply-only 测试会在缺少显式 analysis id 或消费属性失败时失败。
- 敏感范围：`expectation/`、`.skills/`、`agents/standard/`、根 `AGENTS.md`、`TODO.md`、`DONE.md`、agents-list 均无 staged/unstaged diff。

结论：
- review 最小阻断项已收口；验证通过，敏感范围为空。
- 下一步暂存本轮修复和记录后，按标准链路执行 `-next -type review -auto`；不进入 archive_acceptance 或 merge。

时间：2026-06-13 18:54 +0800
经办人：咯咯咯
任务：T-20260613-6ccd1b8f / execute -> review 标准流转补记
任务目标：记录本次 execute 返工完成后实际 `-next -type review -auto` 流转、完整脚本输出、TODO / agents-list / talk 复查、diff check、敏感范围空 diff和自检；不进入 archive_acceptance 或 merge。

实际命令：

```bash
CODEX_MULTI_AGENTS_AGENTS_FILE=/home/lfr/kernelcode_generate/agents/codex-multi-agents/agents-lists.md \
bash /home/lfr/kernelcode_generate/skills/codex-multi-agents/scripts/codex-multi-agents-task.sh \
  -file /home/lfr/kernelcode_generate/TODO.md \
  -next \
  -task_id T-20260613-6ccd1b8f \
  -from "咯咯咯" \
  -type review \
  -message "review；任务目标：复审 T-20260613-6ccd1b8f MultiBufferApplyPass apply-only 阶段边界返工：无 multi_buffer.* 候选时不得写入 analysis.loop_id/analysis.if_id，apply 只读取 analysis 阶段已产出 id；核对新增 pytest、multi-buffer/symbol/private-KCE/pipeline 分组/dump 结构/diff check/敏感范围、Diff 反推自测、减法检查和自检；任务链记录：agents/codex-multi-agents/log/task_records/2026/24/20260613-multi-buffer-control-flow-lifecycle.md。计划级链路 execute -> review -> archive_acceptance -> merge/归档；本次只流转 review，不进入 archive_acceptance 或 merge。" \
  -agents-list /home/lfr/kernelcode_generate/agents/codex-multi-agents/agents-lists.md \
  -auto
```

完整脚本输出：

```text
OK: next T-20260613-6ccd1b8f
OK: replace 咯咯咯 状态
OK: auto-dispatch T-20260613-6ccd1b8f -> 提莫炖蘑菇
OK: replace 提莫炖蘑菇 状态
OK: talk 咯咯咯 -> 提莫炖蘑菇 (提莫炖蘑菇)
OK: talk 咯咯咯 -> 神秘人 (神秘人)
```

TODO 复查：
- `bash /home/lfr/kernelcode_generate/skills/codex-multi-agents/scripts/codex-multi-agents-task.sh -file /home/lfr/kernelcode_generate/TODO.md -status -doing`：`T-20260613-6ccd1b8f` 当前为 `review / 提莫炖蘑菇 / 进行中`。
- worktree 仍为 `/home/lfr/kernelcode_generate/wt-20260613-multi-buffer-control-flow-lifecycle`。
- 计划书仍为 `ARCHITECTURE/plan/multi_buffer_control_flow_lifecycle.md`。
- 记录文件仍为 `agents/codex-multi-agents/log/task_records/2026/24/20260613-multi-buffer-control-flow-lifecycle.md`。

agents-list 复查：
- `bash /home/lfr/kernelcode_generate/skills/codex-multi-agents/scripts/codex-multi-agents-list.sh -file /home/lfr/kernelcode_generate/agents/codex-multi-agents/agents-lists.md -status`：`提莫炖蘑菇=busy`，`咯咯咯=free`，`不要啊教练=free`。

talk 复查：
- `tail -n 30 /home/lfr/kernelcode_generate/agents/codex-multi-agents/log/talk.log`：尾部包含 `@咯咯咯向@提莫炖蘑菇发起会话`，交接任务 `T-20260613-6ccd1b8f` review，写明 worktree、计划书、记录文件和计划级链路；尾部也包含 `@咯咯咯向@神秘人发起会话`，说明任务已完成当前阶段、已回到任务列表、新任务类型为 review、已指派给 `提莫炖蘑菇`。

验证：
- `git diff --check && git diff --cached --check`：退出码 `0`，无输出。
- 敏感范围：
  - `git diff --name-status -- expectation .skills agents/standard AGENTS.md TODO.md DONE.md agents/codex-multi-agents/agents-lists.md`：无输出。
  - `git diff --cached --name-status -- expectation .skills agents/standard AGENTS.md TODO.md DONE.md agents/codex-multi-agents/agents-lists.md`：无输出。
  - `git diff --cached --name-status -- expectation/pass/multi_buffer expectation/pass/pipeline/npu_demo_lowering.py`：无输出。
  - `git status --short --untracked-files=all -- expectation .skills agents/standard AGENTS.md TODO.md DONE.md agents/codex-multi-agents/agents-lists.md`：无输出。

自检：
- 本段只补 execute -> review 标准流转记录；未修改实现、spec、测试或计划验收结论。
- `TODO.md` 与 agents-list 状态变化来自标准 `-next` 脚本；未手工修改状态文件。
- 当前任务已为 `review / 提莫炖蘑菇 / 进行中`，`咯咯咯=free`。
- 未进入 archive_acceptance，未进入 merge，未执行提交、推送或归档。
- 敏感范围空 diff，`expectation/pass/multi_buffer` 与 `expectation/pass/pipeline/npu_demo_lowering.py` 未进入 staged / unstaged diff。

结论：
- T-20260613-6ccd1b8f 已按标准链路从 execute 流转到 review，当前审查责任人为 `提莫炖蘑菇`。
- 等待 review 结论；咯咯咯不再继续处理本轮 execute。

时间：2026-06-13 19:05 +0800
经办人：提莫炖蘑菇
任务：T-20260613-6ccd1b8f / review 复审
任务目标：复审 `MultiBufferApplyPass` apply-only 阶段边界返工，核对无 `multi_buffer.*` 候选时不写入 `analysis.loop_id/analysis.if_id`、apply 只读取 analysis 阶段已产出 id、pytest / pipeline / dump / private-KCE / diff check / 敏感范围 / 任务记录完整性；计划级链路通过后进入 `archive_acceptance`，不得直接 merge。

最新同步现场：
- 执行目录：`/home/lfr/kernelcode_generate/wt-20260613-multi-buffer-control-flow-lifecycle`。
- `git fetch origin main --prune && git rev-parse HEAD && git rev-parse origin/main && git merge-base HEAD origin/main && git rev-list --left-right --count HEAD...origin/main`：退出码 `0`。
- HEAD：`ed33fcf8a0a031b9c3753e3d2339d5058f875169`。
- `origin/main`：`ed33fcf8a0a031b9c3753e3d2339d5058f875169`。
- merge-base：`ed33fcf8a0a031b9c3753e3d2339d5058f875169`。
- ahead / behind：`0 0`。
- 当前待审 diff 为 staged diff；不存在 main 同步冲突或覆盖风险。

执行记录与流转核对：
- 已核对本记录第 440 行起存在本轮 `2026-06-13 18:54 +0800` execute -> review 标准流转补记，标题为 `T-20260613-6ccd1b8f / execute -> review 标准流转补记`，包含实际 `-next -type review -auto` 命令、完整脚本输出、TODO / agents-list / talk 复查、diff check、敏感范围和自检。
- 已核对当前 `TODO.md`：`T-20260613-6ccd1b8f` 为 `review / 提莫炖蘑菇 / 进行中`；管理员已确认无需再要求咯咯咯补同一段流转记录。
- 已核对咯咯咯 execute 返工记录包含执行前阅读、最小功能闭环、验证、Diff 反推自测、减法检查和自检。

被审 diff：
- 新增计划书：`ARCHITECTURE/plan/multi_buffer_control_flow_lifecycle.md`。
- 新增任务记录：`agents/codex-multi-agents/log/task_records/2026/24/20260613-multi-buffer-control-flow-lifecycle.md`。
- 新增 dump expectation 旁路产物：`kernel/dump/matmul/inputs_static_tile_static_present_bias/matmul_inputs_static_tile_static_kernel/24-multi-buffer-analysis-if-path-expected.mlir`。
- 修改实现：`kernel_gen/passes/memory/multi_buffer.py`、`kernel_gen/dialect/symbol/operation/control_flow.py`。
- 修改 spec：`spec/pass/memory/multi_buffer.md`、`spec/dialect/symbol.md`。
- 修改测试：`test/passes/memory/test_multi_buffer.py`、`test/dialect/symbol/test_symbol.py`、`test/passes/pipeline/test_npu_demo_lowering.py`。

发现：
- 无阻断项。
- 无最小需改项。
- 本轮为 execute 返工复审；上一轮阻断项“apply-only 调写入式 `region_labels` 并在无候选时写 `analysis.loop_id/analysis.if_id`”已收口；未发现新增问题、重复问题或范围扩大。

关键审查结论：
- `MultiBufferApplyPass.apply` 已改为调用 `_MultiBufferRewriteRules.existing_region_labels(module)`，只读取已有 `analysis.loop_id`，不再触发 `ensure_control_flow_ids` 写入控制流 id。
- `MultiBufferAnalysisPass.apply` 仍使用写入式 `region_labels(module)`，analysis / facade 阶段继续负责生成稳定 `analysis.*_id`，职责边界清楚。
- matmul apply 路径缺少 analysis loop label 时直接 no-op，已删除 `"loop1"` fallback，避免 apply-only 隐式推断。
- loop-local/direct-use apply 路径继续只消费入参 labels；缺 target loop label 或 if path label 时按现有校验 no-op，不产生额外 analysis id。
- 合法 apply-only pytest 已显式设置 `analysis.loop_id`，不会再靠 apply 隐式补 id 误通过。
- 新增 `test_multi_buffer_apply_without_attrs_does_not_write_analysis_ids` 覆盖无 `multi_buffer.*` 候选时不写 `analysis.loop_id/analysis.if_id`、不生成 ring、不残留三项临时属性。

验证：
- 聚焦回归：`PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/passes/memory/test_multi_buffer.py -k 'apply_without_attrs_does_not_write_analysis_ids or apply_consumes_attrs_with_alignment_zero or apply_keeps_existing_current_pair_noop or apply_keeps_existing_current_direct_use_noop'`：退出码 `0`，`4 passed, 21 deselected, 1 warning in 2.04s`。
- py_compile：`PYTHONDONTWRITEBYTECODE=1 python3 -m py_compile kernel_gen/passes/memory/multi_buffer.py kernel_gen/dialect/symbol/operation/control_flow.py test/passes/memory/test_multi_buffer.py test/dialect/symbol/test_symbol.py test/passes/pipeline/test_npu_demo_lowering.py`：退出码 `0`，无输出。
- private / KCE：`PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/repo_conformance/test_private_api_boundaries.py test/tools/test_kernel_code_error_static_gate.py`：退出码 `0`，`8 passed in 3.50s`。
- multi-buffer / registry：`PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/passes/memory/test_multi_buffer.py test/passes/test_registry.py`：退出码 `0`，`90 passed, 1 warning in 2.61s`。
- symbol：`PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/dialect/symbol/test_symbol.py`：退出码 `0`，`118 passed, 1 warning in 2.20s`。
- pipeline collect：`PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest --collect-only -q test/passes/pipeline/test_npu_demo_lowering.py`：退出码 `0`，`11 tests collected`。
- pipeline 分组一：`PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/passes/pipeline/test_npu_demo_lowering.py -k 'dump or multi_buffer'`：退出码 `0`，`3 passed, 8 deselected, 1 warning in 7.15s`。
- pipeline 分组二：`PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/passes/pipeline/test_npu_demo_lowering.py -k 'builds_pass_manager or pass_order or rejects_unknown_option or propagates_unsupported_structure or wraps_no_loop_body or skips_entry_point_dispatcher'`：退出码 `0`，`6 passed, 5 deselected, 1 warning in 2.59s`。
- pipeline 分组三：`PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/passes/pipeline/test_npu_demo_lowering.py -k 'matmul_demo_allocs_hoist or symbol_hoist_pipeline_pattern_dump or supports_kernel_contract_style_public_chain'`：退出码 `0`，`3 passed, 8 deselected, 1 warning in 29.83s`。
- dump 脚本一：`PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 kernel/matmul/inputs_static_tile_static.py`：退出码 `0`，`shape_seed=727074224`，`tile_seed=551854418`，absent / present `max_abs_diff=3.4332275390625e-05`。
- dump 脚本二：`PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 kernel/matmul/inputs_static_tile_dynamic.py`：退出码 `0`，`shape_seed=95077400`，`tile_seed=1315344892`，absent / present `max_abs_diff=3.814697265625e-05`。
- dump 脚本三：`PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 kernel/matmul/inputs_dynamic_tile_dynamic.py`：退出码 `0`，`shape_seed=1835387404`，`tile_seed=1157924699`，absent / present `max_abs_diff=1.9073486328125e-05`。
- 审查补充脚本：构造含 `multi_buffer.update_points/use_points/num` 但缺 `analysis.loop_id` 的 loop-local direct slice 输入，运行 `MultiBufferApplyPass()` 后输出 `attrs-present missing analysis.loop_id kept no-op`；证明 apply-only 缺 analysis id 时不会隐式补 id 或物化 ring。
- dump 结构复核：当前 `24-multi-buffer-analysis.mlir` 与 `25-multi-buffer-apply.mlir` 中 `if_ids_present`、pattern0 / pattern1 loop id、fixed / auto update-use points、apply ring 物化、apply 无临时属性均为 `True`。首次结构脚本因沿用旧窄字符串检查失败，已判定为审查脚本口径错误，不是 product diff 失败；已用当前结构字段复查通过。
- `git diff --check && git diff --cached --check`：退出码 `0`，无输出。
- 敏感范围：`git diff --name-status -- expectation .skills agents/standard AGENTS.md TODO.md DONE.md agents/codex-multi-agents/agents-lists.md`、`git diff --cached --name-status -- expectation .skills agents/standard AGENTS.md TODO.md DONE.md agents/codex-multi-agents/agents-lists.md`、`git status --short --untracked-files=all -- expectation .skills agents/standard AGENTS.md TODO.md DONE.md agents/codex-multi-agents/agents-lists.md` 均无输出。
- `expectation/pass/multi_buffer` 与 `expectation/pass/pipeline/npu_demo_lowering.py`：staged / unstaged diff 均为空。

Diff 反推审查：
- `kernel_gen/passes/memory/multi_buffer.py`：由聚焦回归、完整 multi-buffer / registry、pipeline 分组、dump 结构和补充脚本覆盖只读 label、缺 label no-op、合法 apply-only 物化 ring、analysis / facade 写 id 的行为边界。
- `kernel_gen/dialect/symbol/operation/control_flow.py`、`spec/dialect/symbol.md`、`test/dialect/symbol/test_symbol.py`：由 symbol pytest 118 passed 和 private/KCE 覆盖新增 / 调整的 symbol 控制流结构语义。
- `spec/pass/memory/multi_buffer.md`：已与 implementation/test 对齐，明确 apply 不生成或补写 `analysis.loop_id/analysis.if_id`，缺 analysis id 的 apply-only 输入 no-op。
- `test/passes/memory/test_multi_buffer.py`：新增 no-attrs 回归和合法 apply-only 显式 id 测试会在 apply 再次写 id、缺 id 仍物化 ring 或属性消费失败时失败。
- `test/passes/pipeline/test_npu_demo_lowering.py` 与 dump 文件：pipeline collect / 分组 / dump 脚本 / dump 结构复查覆盖 pipeline 集成与 dump 结构。
- `ARCHITECTURE/plan/multi_buffer_control_flow_lifecycle.md` 和任务记录：本轮 review 已核对计划级链路、execute 返工记录和标准流转补记；计划书入档验收由下一阶段 `archive_acceptance` 继续负责。
- 未执行 full repo pytest；本轮 diff 已按 touched modules 反推覆盖 multi-buffer、symbol、private/KCE、pipeline、dump、diff check 和敏感范围，残余风险可接受。

减法审查：
- 新增 `_MultiBufferRewriteRules.existing_region_labels(module)` 用只读读取替代 apply-only 阶段旧的写入式 `region_labels(module)` 调用；该 helper 有实质遍历和过滤逻辑，不属于小于 5 行有效代码的 shallow private callable。
- 旧的 `MultiBufferApplyPass.apply -> region_labels -> ensure_control_flow_ids` 写入副作用已从 apply 路径删除；`region_labels` 保留给 analysis / facade analysis 阶段，保留依据充分。
- matmul apply 旧 `"loop1"` fallback 已删除，缺 analysis id 时 no-op；保留的 no-op 校验避免新增公开错误语义。
- 新增 / 改动 private callable 静态核对未发现 private callable 调用 private callable 的违规链路；测试未跨文件直连 product private helper。
- `rg` 静态扫描未发现本轮实现引入 `hasattr/getattr/callable(getattr(...))` 上下文能力探测、非装饰器嵌套函数或公开 API 越权。

公开 API / 权限边界：
- 未新增、删除、重命名或修改公开 pass class、构造参数、registry 名、脚本参数、include 接口或公开错误文本。
- 未修改 `expectation/`、`.skills/`、`agents/standard/`、根 `AGENTS.md`、`TODO.md`、`DONE.md` 或 agents-list；`expectation/pass/multi_buffer` 与 `expectation/pass/pipeline/npu_demo_lowering.py` 未进入 staged / unstaged diff。
- review 期间未修改实现、spec、测试或计划书；本段仅写入任务记录。

自检：
- 已读取实际 diff，而不是只依据执行摘要。
- 已核对 latest main 基线、execute 正文、execute -> review 标准流转补记、TODO / agents-list 当前状态。
- 已完成特殊情况、完整性、维护性、扩展性、测试有效性、Diff 反推审查、减法审查和 private callable / 公开 API 边界审查。
- 已核对测试断言有效性：新增 no-attrs 回归会在 apply 写 id 时失败，合法 apply-only 测试会在缺少显式 analysis id 或属性消费失败时失败。
- 未发现可执行返工项；未进入 archive_acceptance 或 merge，下一步只按标准脚本流转到 `archive_acceptance`。

结论：
- 通过。
- T-20260613-6ccd1b8f execute 返工候选满足 review 目标；下一步按计划级链路执行 `review -> archive_acceptance`，不得直接 merge。

时间：2026-06-13 19:08 +0800
经办人：提莫炖蘑菇
任务：T-20260613-6ccd1b8f / review -> archive_acceptance 标准流转
任务目标：记录本次 review 通过后实际 `-next -type archive_acceptance -auto` 流转、完整脚本输出、TODO / agents-list / talk 复查、diff check、敏感范围空 diff 和自检；计划级链路进入 `archive_acceptance`，不进入 merge。

实际命令：

```bash
bash /home/lfr/kernelcode_generate/skills/codex-multi-agents/scripts/codex-multi-agents-task.sh \
  -file /home/lfr/kernelcode_generate/TODO.md \
  -next \
  -task_id T-20260613-6ccd1b8f \
  -from "提莫炖蘑菇" \
  -type "archive_acceptance" \
  -message "archive_acceptance；任务目标：核对 T-20260613-6ccd1b8f MultiBufferApplyPass apply-only 阶段边界返工 review 通过后的计划书入档验收与可归档性；重点复核 latest main 同步、计划书回写、无 multi_buffer.* 候选时 apply-only 不写 analysis.loop_id/analysis.if_id、apply 只读取 analysis 阶段已产出 id、multi-buffer/symbol/private-KCE/pipeline 分组/dump 验证、Diff 反推审查、减法审查、敏感范围和任务记录完整性。任务链记录：agents/codex-multi-agents/log/task_records/2026/24/20260613-multi-buffer-control-flow-lifecycle.md。计划级链路 execute -> review -> archive_acceptance -> merge/归档；archive_acceptance 完成前不得进入 merge。" \
  -agents-list /home/lfr/kernelcode_generate/agents/codex-multi-agents/agents-lists.md \
  -auto
```

完整脚本输出：

```text
OK: next T-20260613-6ccd1b8f
OK: replace 提莫炖蘑菇 状态
OK: auto-dispatch T-20260613-6ccd1b8f -> 不要啊教练
OK: replace 不要啊教练 状态
OK: talk 提莫炖蘑菇 -> 不要啊教练 (不要啊教练)
OK: talk 提莫炖蘑菇 -> 神秘人 (神秘人)
```

TODO 复查：
- `bash /home/lfr/kernelcode_generate/skills/codex-multi-agents/scripts/codex-multi-agents-task.sh -file /home/lfr/kernelcode_generate/TODO.md -status -doing | rg -n "T-20260613-6ccd1b8f|任务ID|archive_acceptance|不要啊教练|提莫炖蘑菇"`：`T-20260613-6ccd1b8f` 当前为 `archive_acceptance / 不要啊教练 / 进行中`。
- worktree 仍为 `/home/lfr/kernelcode_generate/wt-20260613-multi-buffer-control-flow-lifecycle`。
- 计划书仍为 `ARCHITECTURE/plan/multi_buffer_control_flow_lifecycle.md`。
- 记录文件仍为 `agents/codex-multi-agents/log/task_records/2026/24/20260613-multi-buffer-control-flow-lifecycle.md`。

agents-list 复查：
- `bash /home/lfr/kernelcode_generate/skills/codex-multi-agents/scripts/codex-multi-agents-list.sh -file /home/lfr/kernelcode_generate/agents/codex-multi-agents/agents-lists.md -status | rg -n "不要啊教练|提莫炖蘑菇|咯咯咯"`：`不要啊教练=busy`，`提莫炖蘑菇=free`，`咯咯咯=free`。

talk 复查：
- `tail -n 50 /home/lfr/kernelcode_generate/agents/codex-multi-agents/log/talk.log`：尾部包含 `@提莫炖蘑菇向@不要啊教练发起会话`，交接任务 `T-20260613-6ccd1b8f` 的 `archive_acceptance`，写明 worktree、计划书、记录文件和计划级链路；尾部也包含 `@提莫炖蘑菇向@神秘人发起会话`，说明任务已完成当前阶段、已进入计划书入档验收、已指派给 `不要啊教练`。

验证：
- `git diff --check && git diff --cached --check`：退出码 `0`，无输出。
- 敏感范围：
  - `git diff --name-status -- expectation .skills agents/standard AGENTS.md TODO.md DONE.md agents/codex-multi-agents/agents-lists.md`：无输出。
  - `git diff --cached --name-status -- expectation .skills agents/standard AGENTS.md TODO.md DONE.md agents/codex-multi-agents/agents-lists.md`：无输出。
  - `git status --short --untracked-files=all -- expectation .skills agents/standard AGENTS.md TODO.md DONE.md agents/codex-multi-agents/agents-lists.md`：无输出。
- expectation local-only 相关路径：
  - `git diff --name-status -- expectation/pass/multi_buffer expectation/pass/pipeline/npu_demo_lowering.py`：无输出。
  - `git diff --cached --name-status -- expectation/pass/multi_buffer expectation/pass/pipeline/npu_demo_lowering.py`：无输出。

自检：
- 本段只补 review -> archive_acceptance 标准流转记录；review 正文已在上一段写明通过结论、验证、Diff 反推审查、减法审查、敏感范围和自检。
- `TODO.md` 与 agents-list 状态变化来自标准 `-next` 脚本；未手工修改状态文件。
- 当前任务已为 `archive_acceptance / 不要啊教练 / 进行中`，`提莫炖蘑菇=free`。
- 未执行 merge，未提交，未推送，未归档，未清理 worktree。
- 未修改实现、spec、测试、计划书或 expectation；仅补任务记录并暂存。
- 敏感范围 `expectation/.skills/agents/standard/AGENTS.md/TODO.md/DONE.md/agents-lists` staged / unstaged diff 为空，`expectation/pass/multi_buffer` 与 `expectation/pass/pipeline/npu_demo_lowering.py` 未进入 staged / unstaged diff。

结论：
- T-20260613-6ccd1b8f 已按计划级标准链路从 review 流转到 archive_acceptance。
- 当前 archive_acceptance 责任人为 `不要啊教练`；提莫炖蘑菇已释放为 free。
- 未进入 merge，等待 archive_acceptance 计划书入档验收。

时间：2026-06-13 19:16 +0800
经办人：不要啊教练
任务：T-20260613-6ccd1b8f / multi-buffer-control-flow-lifecycle / archive_acceptance
任务目标：核对 T-20260613-6ccd1b8f MultiBufferApplyPass apply-only 阶段边界返工 review 通过后的计划书入档验收与可归档性；重点复核 latest main 同步、计划书回写、无 multi_buffer.* 候选时 apply-only 不写 analysis.loop_id/analysis.if_id、apply 只读取 analysis 阶段已产出 id、multi-buffer/symbol/private-KCE/pipeline 分组/dump 验证、Diff 反推审查、减法审查、敏感范围和任务记录完整性；通过后按标准链路续接 merge，不直接合并。

改动：
- 回写 `ARCHITECTURE/plan/multi_buffer_control_flow_lifecycle.md` 的状态与 `计划书入档验收 / 复验 / 修复复核记录`：结论人 `不要啊教练`，结论 `archive_acceptance` 通过，验证基线、执行目录、合同验收摘要、通过摘要和下一步 merge/归档口径均已写入。
- 清理计划书内旧状态文字：顶部状态、计划任务当前状态、subagent 收敛遗留项和用户确认协同约束已同步为守护最终检验已通过、唯一计划级任务 `T-20260613-6ccd1b8f` 已进入 archive_acceptance / merge 续接口径。
- 追加本任务记录；未修改实现、spec、测试、`expectation/`、`.skills/`、`agents/standard/`、`AGENTS.md`、`TODO.md`、`DONE.md` 或 agents-list。

最新同步现场：
- 执行目录：`/home/lfr/kernelcode_generate/wt-20260613-multi-buffer-control-flow-lifecycle`。
- `git fetch origin main --prune && git rev-parse HEAD && git rev-parse origin/main && git merge-base HEAD origin/main && git rev-list --left-right --count HEAD...origin/main && git diff --name-only HEAD..origin/main -- ARCHITECTURE/plan/multi_buffer_control_flow_lifecycle.md kernel_gen/passes/memory/multi_buffer.py kernel_gen/dialect/symbol/operation/control_flow.py spec/pass/memory/multi_buffer.md spec/dialect/symbol.md test/passes/memory/test_multi_buffer.py test/dialect/symbol/test_symbol.py test/passes/pipeline/test_npu_demo_lowering.py kernel/dump/matmul/inputs_static_tile_static_present_bias/matmul_inputs_static_tile_static_kernel/24-multi-buffer-analysis-if-path-expected.mlir`：退出码 `0`。
- HEAD：`ed33fcf8a0a031b9c3753e3d2339d5058f875169`。
- `origin/main`：`ed33fcf8a0a031b9c3753e3d2339d5058f875169`。
- merge-base：`ed33fcf8a0a031b9c3753e3d2339d5058f875169`。
- ahead / behind：`0 0`。
- 目标文件 `HEAD..origin/main` diff 为空；不存在 latest main 覆盖风险。

任务记录与流转核对：
- 已核对提莫炖蘑菇 review 通过记录：无阻断、无最小需改项，包含 latest main、验证、Diff 反推审查、减法审查、敏感范围和自检。
- 已核对任务记录尾部存在 `2026-06-13 19:08 +0800` 的 `review -> archive_acceptance` 标准流转补记，包含实际 `-next -type archive_acceptance -auto` 命令、完整脚本输出、TODO / agents-list / talk 复查、diff check、敏感范围和自检；管理员已核对通过。
- `bash /home/lfr/kernelcode_generate/skills/codex-multi-agents/scripts/codex-multi-agents-task.sh -file /home/lfr/kernelcode_generate/TODO.md -status -doing | rg -n "T-20260613-6ccd1b8f|任务ID|archive_acceptance|不要啊教练|提莫炖蘑菇"`：`T-20260613-6ccd1b8f` 当前为 `archive_acceptance / 不要啊教练 / 进行中`。
- `bash /home/lfr/kernelcode_generate/skills/codex-multi-agents/scripts/codex-multi-agents-list.sh -file /home/lfr/kernelcode_generate/agents/codex-multi-agents/agents-lists.md -status | rg -n "不要啊教练|提莫炖蘑菇|咯咯咯"`：`不要啊教练=busy`，`提莫炖蘑菇=free`，`咯咯咯=free`。
- `tail -n 80 /home/lfr/kernelcode_generate/agents/codex-multi-agents/log/talk.log`：尾部包含提莫炖蘑菇交接给不要啊教练、回报管理员，以及管理员确认 `review -> archive_acceptance` 补记通过并解除只读等待限制。

发现：
- 无阻断项。
- 无最小需改项。

计划书入档验收：
- 计划书已包含用户 Q1-Q10 确认来源、subagent Round 1 / Round 2 收敛记录、守护最终检验通过记录、固定链路 `execute -> review -> archive_acceptance -> merge/归档`、当前无必过 `expectation`、禁止修改面和 S1-S5 小任务卡。
- 本次已回写 `计划书入档验收 / 复验 / 修复复核记录`，并清理旧的“尚未请求 / 等待守护最终检验 / 不创建任务”状态残留；`rg -n "尚未请求|未请求|等待守护最终检验|不创建任务|待 execute" ARCHITECTURE/plan/multi_buffer_control_flow_lifecycle.md` 未再命中旧状态。
- 计划书与任务记录、实现、spec、pytest 和 dump 完成态一致；当前可归档性满足进入 merge 前置。

关键行为核对：
- `MultiBufferApplyPass.apply` 调用 `_MultiBufferRewriteRules.existing_region_labels(module)`，只读取已有 `analysis.loop_id`，缺失 loop id 时跳过；不会在 apply-only 阶段调用写入式 `region_labels(module)` 或 `ensure_control_flow_ids(module)`。
- `MultiBufferAnalysisPass.apply` 仍调用写入式 `region_labels(module)`，analysis / facade analysis 阶段继续负责生成 `analysis.loop_id/analysis.if_id`。
- 新增回归 `test_multi_buffer_apply_without_attrs_does_not_write_analysis_ids` 覆盖无 `multi_buffer.*` 候选时不写 `analysis.loop_id/analysis.if_id`、不生成 ring、不残留临时属性。
- 合法 apply-only 回归显式设置 `analysis.loop_id` 后再设置 `multi_buffer.update_points/use_points/num`，能防止 apply 靠隐式补 id 误通过。
- pipeline dump 断言 `multi-buffer-analysis` 中存在 `analysis.loop_id`、`multi_buffer.update_points/use_points` 与 `num="auto"`，并断言 `multi-buffer-apply` 不残留 `multi_buffer.*` 且包含 ring/current/advance。

验证：
- 聚焦回归：`PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/passes/memory/test_multi_buffer.py -k 'apply_without_attrs_does_not_write_analysis_ids or apply_consumes_attrs_with_alignment_zero or apply_keeps_existing_current_pair_noop or apply_keeps_existing_current_direct_use_noop'`：退出码 `0`，`4 passed, 21 deselected, 1 warning in 1.86s`。
- py_compile：`PYTHONDONTWRITEBYTECODE=1 python3 -m py_compile kernel_gen/passes/memory/multi_buffer.py kernel_gen/dialect/symbol/operation/control_flow.py test/passes/memory/test_multi_buffer.py test/dialect/symbol/test_symbol.py test/passes/pipeline/test_npu_demo_lowering.py`：退出码 `0`，无输出。
- multi-buffer / registry：`PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/passes/memory/test_multi_buffer.py test/passes/test_registry.py`：退出码 `0`，`90 passed, 1 warning in 2.68s`。
- symbol：`PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/dialect/symbol/test_symbol.py`：退出码 `0`，`118 passed, 1 warning in 2.25s`。
- private / KCE：`PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/repo_conformance/test_private_api_boundaries.py test/tools/test_kernel_code_error_static_gate.py`：退出码 `0`，`8 passed in 3.65s`。
- pipeline collect：`PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest --collect-only -q test/passes/pipeline/test_npu_demo_lowering.py`：退出码 `0`，`11 tests collected in 2.16s`。
- pipeline 分组一：`PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/passes/pipeline/test_npu_demo_lowering.py -k 'dump or multi_buffer'`：退出码 `0`，`3 passed, 8 deselected, 1 warning in 6.74s`。
- pipeline 分组二：`PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/passes/pipeline/test_npu_demo_lowering.py -k 'builds_pass_manager or pass_order or rejects_unknown_option or propagates_unsupported_structure or wraps_no_loop_body or skips_entry_point_dispatcher'`：退出码 `0`，`6 passed, 5 deselected, 1 warning in 2.32s`。
- pipeline 分组三：`PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/passes/pipeline/test_npu_demo_lowering.py -k 'matmul_demo_allocs_hoist or symbol_hoist_pipeline_pattern_dump or supports_kernel_contract_style_public_chain'`：退出码 `0`，`3 passed, 8 deselected, 1 warning in 29.41s`。
- dump 脚本一：`PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 kernel/matmul/inputs_static_tile_static.py`：退出码 `0`，`shape_seed=619867011`，`tile_seed=1782011768`，absent / present `max_abs_diff=2.6702880859375e-05`。
- dump 脚本二：`PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 kernel/matmul/inputs_static_tile_dynamic.py`：退出码 `0`，`shape_seed=1628978302`，`tile_seed=350851141`，absent / present `max_abs_diff=4.57763671875e-05`。
- dump 脚本三：`PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 kernel/matmul/inputs_dynamic_tile_dynamic.py`：退出码 `0`，`shape_seed=1258654840`，`tile_seed=1437736294`，absent / present `max_abs_diff=3.0517578125e-05`。
- dump 结构复核脚本：`24-multi-buffer-analysis.mlir` 的 `analysis.loop_id`、`analysis.if_id`、pattern0 `loop1-1/loop2-2/loop3-3/if2-2`、pattern1 `loop4-1/loop5-2/loop6-3/if3-2`、fixed `num="2"`、`num="auto"`、`multi_buffer.update_points/use_points` 均为 `True`；`25-multi-buffer-apply.mlir` 的无 `multi_buffer.*`、存在 `dma.make_ring/current_ring/advance_ring` 均为 `True`。
- `git diff --check && git diff --cached --check`：退出码 `0`，无输出。
- 敏感范围：
  - `git diff --name-status -- expectation .skills agents/standard AGENTS.md TODO.md DONE.md agents/codex-multi-agents/agents-lists.md`：无输出。
  - `git diff --cached --name-status -- expectation .skills agents/standard AGENTS.md TODO.md DONE.md agents/codex-multi-agents/agents-lists.md`：无输出。
  - `git status --short --ignored --untracked-files=all -- expectation .skills agents/standard AGENTS.md TODO.md DONE.md agents/codex-multi-agents/agents-lists.md`：无输出。
- expectation 专项：
  - `test -d expectation && echo expectation_dir_present || echo expectation_dir_absent`：`expectation_dir_absent`。
  - `git diff --name-status -- expectation/pass/multi_buffer expectation/pass/pipeline/npu_demo_lowering.py`：无输出。
  - `git diff --cached --name-status -- expectation/pass/multi_buffer expectation/pass/pipeline/npu_demo_lowering.py`：无输出。
  - `git status --short --ignored --untracked-files=all -- expectation | LC_ALL=C sort | sha256sum`：`e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855`。
  - `find expectation -type f -not -path '*/__pycache__/*' -print0 | sort -z | xargs -0 -r sha256sum | sha256sum`：因本 worktree 无 `expectation/` 目录，内容指纹按空输入记录为 `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855`，同时终端输出 `find: 'expectation': No such file or directory`。

Diff 反推审查：
- `kernel_gen/passes/memory/multi_buffer.py`：聚焦回归、multi-buffer / registry、pipeline 分组、dump 结构复核覆盖 apply-only 只读 id、analysis 写 id、if path lifecycle、fixed/auto ring、no-op 边界和临时属性清理。
- `kernel_gen/dialect/symbol/operation/control_flow.py`、`spec/dialect/symbol.md`、`test/dialect/symbol/test_symbol.py`：symbol pytest 118 passed 覆盖 `symbol.for` 额外 attrs parse / print round-trip，保证 `analysis.loop_id` 不被自定义文本语法丢弃。
- `spec/pass/memory/multi_buffer.md`：已写清 analysis id、`update_points/use_points` 列表、apply 不补写 `analysis.loop_id/analysis.if_id`、apply-only 缺 id no-op，与实现和测试一致。
- `test/passes/memory/test_multi_buffer.py`：新增 no-attrs apply-only 回归会在 apply 写 id 或生成 ring 时失败；if path analysis/apply 用例锁定 fixed `num=2` 和 outer-loop current/advance。
- `test/passes/pipeline/test_npu_demo_lowering.py` 与 dump 文件：pipeline 分组和 dump 脚本覆盖 multi-buffer-analysis 在 memory-pool 前运行、analysis dump 属性存在、apply dump ring 化且临时属性清理。
- `ARCHITECTURE/plan/multi_buffer_control_flow_lifecycle.md` 与任务记录：已按计划书入档验收要求回写验收结论，并纳入 staged diff；merge 阶段应同批合入计划书、任务记录、实现、spec、测试和 expected dump。
- 未运行 full repo pytest；本轮按实际 diff 覆盖 touched modules、pipeline 集成、dump 和静态门禁，残余风险可接受。

减法审查：
- 本轮返工删除了 apply-only 路径对写入式 `region_labels(module)` 的依赖，改为只读 `existing_region_labels(module)`；旧 `"loop1"` fallback 从 matmul apply 路径删除，缺 analysis id 时保持 no-op。
- `region_labels(module)` 保留给 analysis / facade analysis 阶段生成控制流 id，保留依据充分。
- 新增 / 改动 private callable 已由 `test/repo_conformance/test_private_api_boundaries.py` 覆盖；静态扫描未发现本轮实现引入 `hasattr/getattr/callable(getattr(...))` 上下文能力探测。
- 测试 helper 命中属于测试文件内部结构，private/KCE 门禁已通过；未发现测试跨文件直连 product private helper。

公开 API / 权限边界：
- 公开 pass class、constructor、from_options、apply、registry name、脚本参数和稳定错误文本未变更；公开 IR attrs `analysis.loop_id/analysis.if_id` 与 `multi_buffer.update_points/use_points` 已在计划书用户确认记录 Q1-Q10 中收口。
- 未修改 `expectation/`、`.skills/`、`agents/standard/`、根 `AGENTS.md`、`TODO.md`、`DONE.md` 或 agents-list。
- archive_acceptance 未执行 merge、提交、推送、归档或清理 worktree。

自检：
- 已读取根 `AGENTS.md`、不要啊教练 prompt、`agents/standard/任务记录约定.md`、`agents/standard/审查规范.md`、`agents/standard/合并规范.md` 与计划书正文。
- 已核对 latest main 基线、review 通过记录、`review -> archive_acceptance` 标准流转补记、TODO / agents-list / talk 当前状态。
- 已完成计划书回写、合同验收摘要、Diff 反推审查、减法审查、敏感范围和 expectation 只读边界核对。
- 已确认无剩余可执行返工项；下一步只能按标准脚本流转 merge，不由 archive_acceptance 角色直接合并。

结论：
- `archive_acceptance` 通过。
- 无阻断项，无最小需改项。
- 下一步按计划级链路续接 `merge / 归档`；merge 角色需同批合入计划书入档验收记录、任务记录、实现、spec、测试与 expected dump，并按合并规范再次同步 latest main、复核敏感范围和验证摘要。

时间：2026-06-13 19:17 +0800
经办人：不要啊教练
任务：T-20260613-6ccd1b8f / archive_acceptance -> merge 标准流转
任务目标：记录本次 archive_acceptance 通过后实际 `-next -type merge -auto` 流转、完整脚本输出、TODO / agents-list / talk 复查、diff check、敏感范围空 diff和自检；只续接 merge，不执行合并、提交、推送或归档。

实际命令：

```bash
CODEX_MULTI_AGENTS_AGENTS_FILE=/home/lfr/kernelcode_generate/agents/codex-multi-agents/agents-lists.md \
bash /home/lfr/kernelcode_generate/skills/codex-multi-agents/scripts/codex-multi-agents-task.sh \
  -file /home/lfr/kernelcode_generate/TODO.md \
  -next \
  -task_id T-20260613-6ccd1b8f \
  -from "不要啊教练" \
  -type merge \
  -message "merge；任务目标：合入已通过 execute、review 与 archive_acceptance 的 T-20260613-6ccd1b8f multi-buffer 控制流生命周期分析闭环 staged 改动、计划书入档验收记录和任务记录；合入前复核 latest main、计划书回写、无 multi_buffer.* 候选时 apply-only 不写 analysis.loop_id/analysis.if_id、apply 只读取 analysis 阶段已产出 id、multi-buffer/symbol/private-KCE/pipeline 分组/dump 验证摘要、Diff 反推审查、减法审查、敏感范围空 diff和任务记录完整性；不得修改 expectation 本体，不得顺手改实现；按合并规范同批提交/推送代码、spec、test、expected dump、计划书与任务记录，完成后执行 -done 与 done_plan 归档并清理对应 worktree/branch。任务链记录：agents/codex-multi-agents/log/task_records/2026/24/20260613-multi-buffer-control-flow-lifecycle.md。" \
  -agents-list /home/lfr/kernelcode_generate/agents/codex-multi-agents/agents-lists.md \
  -auto
```

完整脚本输出：

```text
OK: next T-20260613-6ccd1b8f
OK: replace 不要啊教练 状态
OK: auto-dispatch T-20260613-6ccd1b8f -> 李白
OK: replace 李白 状态
OK: talk 不要啊教练 -> 李白 (李白)
OK: talk 不要啊教练 -> 神秘人 (神秘人)
```

TODO 复查：
- `bash /home/lfr/kernelcode_generate/skills/codex-multi-agents/scripts/codex-multi-agents-task.sh -file /home/lfr/kernelcode_generate/TODO.md -status -doing | rg -n "T-20260613-6ccd1b8f|任务ID|merge|李白|不要啊教练"`：`T-20260613-6ccd1b8f` 当前为 `merge / 李白 / 进行中`。
- worktree 仍为 `/home/lfr/kernelcode_generate/wt-20260613-multi-buffer-control-flow-lifecycle`。
- 计划书仍为 `ARCHITECTURE/plan/multi_buffer_control_flow_lifecycle.md`。
- 记录文件仍为 `agents/codex-multi-agents/log/task_records/2026/24/20260613-multi-buffer-control-flow-lifecycle.md`。

agents-list 复查：
- `bash /home/lfr/kernelcode_generate/skills/codex-multi-agents/scripts/codex-multi-agents-list.sh -file /home/lfr/kernelcode_generate/agents/codex-multi-agents/agents-lists.md -status | rg -n "李白|不要啊教练|提莫炖蘑菇"`：`李白=busy`，`不要啊教练=free`，`提莫炖蘑菇=free`。

talk 复查：
- `tail -n 50 /home/lfr/kernelcode_generate/agents/codex-multi-agents/log/talk.log`：尾部包含 `@不要啊教练向@李白发起会话`，交接任务 `T-20260613-6ccd1b8f` merge，写明 worktree、计划书、记录文件和合并目标；尾部也包含 `@不要啊教练向@神秘人发起会话`，说明任务已完成当前阶段、已回到任务列表、新任务类型为 merge、已指派给 `李白`。

验证：
- `git diff --check && git diff --cached --check`：退出码 `0`，无输出。
- 敏感范围：
  - `git diff --name-status -- expectation .skills agents/standard AGENTS.md TODO.md DONE.md agents/codex-multi-agents/agents-lists.md`：无输出。
  - `git diff --cached --name-status -- expectation .skills agents/standard AGENTS.md TODO.md DONE.md agents/codex-multi-agents/agents-lists.md`：无输出。
- expectation local-only 相关路径：
  - `git diff --name-status -- expectation/pass/multi_buffer expectation/pass/pipeline/npu_demo_lowering.py`：无输出。
  - `git diff --cached --name-status -- expectation/pass/multi_buffer expectation/pass/pipeline/npu_demo_lowering.py`：无输出。

自检：
- 本段只记录 `archive_acceptance -> merge` 标准流转；入档验收通过结论、计划书回写和验证摘要已在上一段写明。
- `TODO.md` 与 agents-list 状态变化来自标准 `-next` 脚本；未手工修改状态文件。
- 当前任务已为 `merge / 李白 / 进行中`，`不要啊教练=free`。
- 未执行 merge，未提交，未推送，未归档，未清理 worktree。
- 未修改实现、spec、测试或 expectation；本段只补任务记录并暂存。
- 敏感范围和 expectation local-only 相关路径 staged / unstaged diff 为空。

结论：
- T-20260613-6ccd1b8f 已按计划级标准链路从 archive_acceptance 流转到 merge。
- 当前 merge 责任人为 `李白`；不要啊教练已释放为 free。
- 等待 merge 角色按合并规范同批合入计划书、任务记录、实现、spec、测试与 expected dump，并完成提交 / 推送 / done_plan 归档。

时间：2026-06-13 19:30 +0800
经办人：李白
任务：T-20260613-6ccd1b8f / merge/归档
任务目标：在最新 `origin/main` 上合入已通过 execute、review 与 archive_acceptance 的 multi-buffer 控制流生命周期分析闭环候选；同批纳入计划书入档验收记录、任务记录、实现、spec、测试、expected dump 和 done_plan 计划归档；不修改 `expectation/` 本体，不顺手改实现。

合并前记录核对：
- 已核对 review 通过记录：无阻断、无最小需改项，包含 latest main、验证、Diff 反推审查、减法审查、敏感范围和自检。
- 已核对 `2026-06-13 19:16 +0800` archive_acceptance 通过记录：计划书已回写入档验收结论；无阻断项、无最小需改项；当前无必过 `expectation` 合同验收。
- 已核对 `2026-06-13 19:17 +0800` archive_acceptance -> merge 标准流转补记：包含实际 `-next -type merge -auto` 命令、完整脚本输出、TODO 复查 `merge / 李白 / 进行中`、agents-list 复查 `李白=busy`、talk 交接与回报、diff check、敏感范围、expectation 专项空 diff、自检和未执行 merge/提交/推送/归档说明。
- 已核对计划级链路为 `execute -> review -> archive_acceptance -> merge/归档`，满足计划级合并前置。

latest main 与同步现场：
- 执行目录：`/home/lfr/kernelcode_generate/wt-20260613-multi-buffer-control-flow-lifecycle`。
- `git fetch origin --prune`：通过。
- `HEAD=ed33fcf8a0a031b9c3753e3d2339d5058f875169`。
- `origin/main=ed33fcf8a0a031b9c3753e3d2339d5058f875169`。
- `git rev-list --left-right --count HEAD...origin/main`：`0 0`。
- latest main 无领先提交，无路径重放或冲突处理；未发生手工冲突合并。

实际合入范围：
- 最终 staged name-status 共 10 路径：
  - `A agents/codex-multi-agents/log/task_records/2026/24/20260613-multi-buffer-control-flow-lifecycle.md`
  - `A agents/codex-multi-agents/log/task_records/done_plan/2026/multi_buffer_control_flow_lifecycle.md`
  - `A kernel/dump/matmul/inputs_static_tile_static_present_bias/matmul_inputs_static_tile_static_kernel/24-multi-buffer-analysis-if-path-expected.mlir`
  - `M kernel_gen/dialect/symbol/operation/control_flow.py`
  - `M kernel_gen/passes/memory/multi_buffer.py`
  - `M spec/dialect/symbol.md`
  - `M spec/pass/memory/multi_buffer.md`
  - `M test/dialect/symbol/test_symbol.py`
  - `M test/passes/memory/test_multi_buffer.py`
  - `M test/passes/pipeline/test_npu_demo_lowering.py`
- 计划归档：原路径 `ARCHITECTURE/plan/multi_buffer_control_flow_lifecycle.md` 已进入 index，blob 为 `9310bcafe09920ec990b8a0392d95942b0078b07`；本轮通过 `git mv` 归档到 `agents/codex-multi-agents/log/task_records/done_plan/2026/multi_buffer_control_flow_lifecycle.md`，与代码/spec/test/dump/任务记录同批提交。最终提交中原计划路径不应存在。
- 未纳入 `expectation/`、`.skills/`、`agents/standard/`、`AGENTS.md`、`TODO.md`、`DONE.md` 或 `agents/codex-multi-agents/agents-lists.md`。

验证：
- `PYTHONDONTWRITEBYTECODE=1 python3 -m py_compile kernel_gen/passes/memory/multi_buffer.py kernel_gen/dialect/symbol/operation/control_flow.py test/passes/memory/test_multi_buffer.py test/dialect/symbol/test_symbol.py test/passes/pipeline/test_npu_demo_lowering.py`：退出码 `0`，无输出。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/passes/memory/test_multi_buffer.py -k 'apply_without_attrs_does_not_write_analysis_ids or apply_consumes_attrs_with_alignment_zero or apply_keeps_existing_current_pair_noop or apply_keeps_existing_current_direct_use_noop'`：`4 passed, 21 deselected, 1 warning in 2.28s`。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/passes/memory/test_multi_buffer.py test/passes/test_registry.py`：`90 passed, 1 warning in 2.90s`。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/dialect/symbol/test_symbol.py`：`118 passed, 1 warning in 2.45s`。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/repo_conformance/test_private_api_boundaries.py test/tools/test_kernel_code_error_static_gate.py`：`8 passed in 3.72s`。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest --collect-only -q test/passes/pipeline/test_npu_demo_lowering.py`：`11 tests collected in 2.43s`。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/passes/pipeline/test_npu_demo_lowering.py -k 'dump or multi_buffer'`：`3 passed, 8 deselected, 1 warning in 7.24s`。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/passes/pipeline/test_npu_demo_lowering.py -k 'builds_pass_manager or pass_order or rejects_unknown_option or propagates_unsupported_structure or wraps_no_loop_body or skips_entry_point_dispatcher'`：`6 passed, 5 deselected, 1 warning in 2.54s`。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/passes/pipeline/test_npu_demo_lowering.py -k 'matmul_demo_allocs_hoist or symbol_hoist_pipeline_pattern_dump or supports_kernel_contract_style_public_chain'`：`3 passed, 8 deselected, 1 warning in 30.39s`。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 kernel/matmul/inputs_static_tile_static.py`：通过，`shape_seed=333928315`、`tile_seed=771256693`，absent / present `max_abs_diff=4.1961669921875e-05`。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 kernel/matmul/inputs_static_tile_dynamic.py`：通过，`shape_seed=409013101`、`tile_seed=274061529`，absent / present `max_abs_diff=2.6702880859375e-05`。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 kernel/matmul/inputs_dynamic_tile_dynamic.py`：通过，`shape_seed=1712505810`、`tile_seed=1058609648`，absent / present `max_abs_diff=2.288818359375e-05`。
- dump 结构复核：`24-multi-buffer-analysis.mlir` 命中 `analysis.loop_id`、`analysis.if_id`、`multi_buffer.update_points`、`multi_buffer.use_points`、`multi_buffer.num`，包含 pattern0 `loop2-2/loop3-3/if2-2` 与 pattern1 `loop5-2/loop6-3/if3-2`；`25-multi-buffer-apply.mlir` 命中 `dma.make_ring`、`dma.current_ring`、`dma.advance_ring`，未命中 `multi_buffer.*` 残留。
- apply-only 边界复核：实现 diff 中 `MultiBufferApplyPass.apply` 使用 `_MultiBufferRewriteRules.existing_region_labels(module)`；spec/test 明确无 `multi_buffer.*` 候选时 apply-only 不写 `analysis.loop_id/analysis.if_id`，合法 apply-only 测试显式设置 `analysis.loop_id` 后消费 `multi_buffer.update_points/use_points/num`。
- `git diff --check`：通过，无输出。
- `git diff --cached --check`：通过，无输出。

敏感范围：
- `git diff --name-status -- expectation .skills agents/standard AGENTS.md TODO.md DONE.md agents/codex-multi-agents/agents-lists.md`：无输出。
- `git diff --cached --name-status -- expectation .skills agents/standard AGENTS.md TODO.md DONE.md agents/codex-multi-agents/agents-lists.md`：无输出。
- `git diff --name-status -- expectation/pass/multi_buffer expectation/pass/pipeline/npu_demo_lowering.py`：无输出。
- `git diff --cached --name-status -- expectation/pass/multi_buffer expectation/pass/pipeline/npu_demo_lowering.py`：无输出。
- `test -d expectation && echo expectation_dir_present || echo expectation_dir_absent`：`expectation_dir_absent`。
- `git status --short --ignored --untracked-files=all -- expectation | LC_ALL=C sort | sha256sum`：`e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855`。
- `find expectation -type f -not -path '*/__pycache__/*' -print0 2>/dev/null | sort -z | xargs -0 -r sha256sum | sha256sum`：`e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855`。

剩余风险：
- 未运行 full repo pytest；本轮按计划与 Diff 反推范围复跑 multi-buffer、symbol、pipeline 分组、private/KCE、py_compile、dump 脚本和静态门禁。
- `test/passes/pipeline/test_npu_demo_lowering.py` 仍按任务记录既有口径分组执行，未单进程全量执行；execute 记录已说明全量单进程历史 Signal 11，分组覆盖 11 个用例。

结论：
- 合并前复核通过。
- 可提交并推送当前 10 路径 staged diff；提交后执行 `-done` 与 `-done-plan`，再按清理规范删除已完成任务 worktree / branch。
