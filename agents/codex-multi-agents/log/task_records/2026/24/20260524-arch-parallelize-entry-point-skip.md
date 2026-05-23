# T-20260524-83a48dea / arch-parallelize-entry-point-skip

时间：2026-05-24 01:57 +0800
经办人：守护最好的爱莉希雅
任务：T-20260524-83a48dea / arch-parallelize-entry-point-skip / 执行中 scope 架构裁定
任务目标：确认 `entry_point` skip execute 是否允许追加最小 `KernelEmitter` 修复，以收口最低 pipeline -> gen_kernel pytest 暴露的 `builtin.unregistered` generic symbol op 发射失败。
改动：裁定选 A。授权本 execute 内追加最小修改 `kernel_gen/dsl/gen_kernel/kernel_emitter.py`，并同步必要 `spec/dsl/gen_kernel/kernel_emitter.md` 与公开 `gen_kernel(...)` 测试；范围仅限 `builtin.unregistered` + `op_name__` 为 `"symbol.const"` / `"symbol.eq"` 的 npu_demo final host 发射支持。不得扩大为通用 `builtin.unregistered` 支持，不改公开 API、registry、工具参数、稳定错误文本、`expectation/`、`.skills/` 或 `agents/standard/**`。
验证：只读核对 `/home/lfr/kernelcode_generate/ARCHITECTURE/plan/arch_parallelize_entry_point_skip_green_plan.md` 当前任务边界、`TODO.md` 中 T-20260524-83a48dea 暂停状态、任务 worktree diff、`kernel_gen/dsl/gen_kernel/kernel_emitter.py` 现有 generic helper 与失败回报；未运行 pytest，本记录是架构裁定，不替代 execute 自测。
自检：该裁定不新增公开 API，不变更 expectation 授权或 tracked 合同落地；范围扩大是完成既有计划最低 pipeline gate 的直接依赖修复。若后续需要支持 `"symbol.const"` / `"symbol.eq"` 之外的 generic op、调整公开错误文本、改 target registry 或改 expectation，必须再次暂停并转用户确认。
结论：A。计划书已回写执行中架构裁定；execute 可在管理员恢复后按该范围继续，并必须把新增文件范围、失败复现、修复动作、Diff 反推自测、合同验收和敏感目录门禁写入本记录。

## Execute 完成记录 - 睡觉小分队 - 2026-05-24 02:09 +0800

时间：2026-05-24 02:09 +0800
经办人：睡觉小分队
任务：T-20260524-83a48dea / arch-parallelize-entry-point-skip
任务目标：完成 `ArchParallelizePass` 跳过 `entry_point` host dispatcher；保持 pattern/device 函数 block 级并行化；按架构裁定 A 补齐最小 `KernelEmitter` generic `"symbol.const"` / `"symbol.eq"` 发射支持；同步 spec、pytest、pipeline dump 与只读 expectation 合同闭环。

### 执行前阅读记录

- 已读睡觉小分队 prompt、`AGENTS.md`、`agents/standard/任务记录约定.md`、`agents/standard/实现文件规范.md`。
- 已读主仓只读计划 `/home/lfr/kernelcode_generate/ARCHITECTURE/plan/arch_parallelize_entry_point_skip_green_plan.md` 最新版，确认 S1-S6 小任务卡、用户确认、expectation 只读 scope、架构裁定 A。
- 已读本记录中守护最好的爱莉希雅 01:57 架构裁定：允许本 execute 内追加最小修改 `kernel_gen/dsl/gen_kernel/kernel_emitter.py`、`spec/dsl/gen_kernel/kernel_emitter.md`、公开 `gen_kernel(...)` 测试；只支持 `builtin.unregistered` + `op_name__` 为 `"symbol.const"` / `"symbol.eq"`；不得扩大到其它 generic op。
- 已按榕的要求重新查看 `/home/lfr/kernelcode_generate/TODO.md`：`T-20260524-83a48dea` 当前指派睡觉小分队，状态 `进行中`，记录文件为本文件。

### 计划内小任务卡核对

- S1 spec：已更新 `spec/pass/arch_parallelize.md`、`spec/pass/pipeline/npu_demo_lowering.md`、`spec/pass/registry.md`，写清 entry host no-op、非入口函数旧行为不变、registry 说明不再无条件描述 no-loop block0。
- S2 实现：已更新 `kernel_gen/passes/arch_parallelize.py`，在当前文件内新增私有 `_is_entry_point_func(...)`，`apply(...)` 在 `_rewrite_func(...)` 前跳过入口 host；未新增公开 API。
- S3 pytest / pipeline gate：已补 `test_arch_parallelize_skips_entry_point_host_dispatcher` 与 `test_npu_demo_lowering_pipeline_arch_parallelize_skips_entry_point_dispatcher`；matmul dump 使用任务 worktree 现有 `kernel/matmul/inputs_static_tile_static.py` 生成现场后核对。
- S4 expectation：未修改 `expectation/`；从任务 worktree 启动 `expectation.pass.arch_parallelize`，并记录 `__file__` 探针、exact file-list 与 sha256 manifest。
- S5 回归 / 门禁：pytest、expectation、dump、compileall / AST parse、静态扫描、diff check、敏感目录门禁均已执行。
- S6 emitter：按架构裁定 A 更新 `kernel_gen/dsl/gen_kernel/kernel_emitter.py`、`spec/dsl/gen_kernel/kernel_emitter.md` 与 `test/dsl/gen_kernel/test_gen_kernel.py`，只支持 generic `"symbol.const"` / `"symbol.eq"`。

### 失败复现与修复动作

- 失败复现：在只完成 entry skip 后运行
  `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/passes/test_arch_parallelize.py test/passes/pipeline/test_npu_demo_lowering.py test/passes/test_registry.py`
  结果 `85 passed, 1 failed, 1 warning`；失败为 `test_npu_demo_lowering_pipeline_supports_kernel_contract_style_public_chain`，`gen_kernel(...)` 报 `KernelCodeError: target=npu_demo: builtin.unregistered: unsupported op`。
- 根因：entry host no-op 后 final dispatcher 保留 kernel-pattern / outline 产生的 generic `"symbol.const"` / `"symbol.eq"`，xDSL 形态为 `builtin.unregistered` + `op_name__`；`KernelEmitter` 已有 generic helper 只识别 op 名称等于 `symbol.const` / `symbol.eq`。
- 修复：`KernelEmitter._generic_symbol_op_name(...)` 只在 `target="npu_demo"` 且 `op.name == "builtin.unregistered"` 时读取 `op_name__`，且仅允许 `"symbol.const"` / `"symbol.eq"`；其它 `builtin.unregistered` 继续走 unsupported。
- 防扩散测试：新增 `test_gen_kernel_rejects_other_builtin_unregistered_symbol_ops`，构造 `builtin.UnregisteredOp.with_name("symbol.fake")`，断言仍失败为 `builtin.unregistered: unsupported op`。

### 改动摘要

- `kernel_gen/passes/arch_parallelize.py`：入口 host 跳过逻辑、文件级说明与函数注释。
- `kernel_gen/dsl/gen_kernel/kernel_emitter.py`：最小 npu_demo generic symbol op 识别，仅限 `"symbol.const"` / `"symbol.eq"`。
- `spec/pass/arch_parallelize.md`、`spec/pass/pipeline/npu_demo_lowering.md`、`spec/pass/registry.md`：同步 entry host no-op 与非入口旧行为。
- `spec/dsl/gen_kernel/kernel_emitter.md`：同步架构裁定 A 的 generic symbol 发射边界与测试矩阵。
- `test/passes/test_arch_parallelize.py`、`test/passes/pipeline/test_npu_demo_lowering.py`、`test/dsl/gen_kernel/test_gen_kernel.py`：补 pass / pipeline / gen_kernel 公开入口测试。

### 验证

- pytest 最低集合 + emitter 公开测试：
  - 命令：`PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/passes/test_arch_parallelize.py test/passes/pipeline/test_npu_demo_lowering.py test/passes/test_registry.py test/dsl/gen_kernel/test_gen_kernel.py`
  - 结果：exit 0，`184 passed, 1 warning`。
- 裁定 A 新增测试：
  - 命令：`PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/dsl/gen_kernel/test_gen_kernel.py -k 'generic_symbol_guard or rejects_other_builtin_unregistered'`
  - 结果：exit 0，`2 passed, 96 deselected, 2 warnings`。
- 原失败项复测：
  - 命令：`PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/passes/pipeline/test_npu_demo_lowering.py -k supports_kernel_contract_style_public_chain`
  - 结果：exit 0，`1 passed, 8 deselected, 1 warning`。
- 只读 expectation 导入来源探针：
  - 命令：从任务 worktree 启动 `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260524-arch-parallelize-entry-point-skip:/home/lfr/kernelcode_generate python3 - <<'PY' ...`
  - 结果：exit 0。
  - 摘要：`expectation.pass.arch_parallelize.entry_point_skip` 来自主仓 `/home/lfr/kernelcode_generate/expectation/pass/arch_parallelize/entry_point_skip.py`；`kernel_gen.passes.arch_parallelize` 来自任务 worktree `/home/lfr/kernelcode_generate/wt-20260524-arch-parallelize-entry-point-skip/kernel_gen/passes/arch_parallelize.py`。
- 只读 expectation：
  - 命令：`PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260524-arch-parallelize-entry-point-skip:/home/lfr/kernelcode_generate python3 -m expectation.pass.arch_parallelize`
  - 结果：exit 0；`block0_guard`、`block_loop`、`dynamic_nested_loop`、`entry_point_skip` 均通过。
- expectation exact file-list / manifest：
  - 命令：在主仓 `/home/lfr/kernelcode_generate` 运行 `git ls-files expectation/pass/arch_parallelize`、exact file-list `diff -u ... <(find ...)`、`find ... -name '*.py' | xargs sha256sum`。
  - 结果：exit 0；`git ls-files expectation/pass/arch_parallelize` 为空；file-list 与计划一致；`entry_point_skip.py` hash 为 `83b84e541298c4b6e6ab7d1a8595dbad95f43d69350ea1cf064b25f286eab849`。
- matmul dump 生成与核对：
  - 生成命令：`PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 kernel/matmul/inputs_static_tile_static.py`
  - 结果：exit 0；absent / present bias `max_abs_diff=3.4332275390625e-05`。
  - 核对命令：读取 `kernel/dump/matmul/inputs_static_tile_static_present_bias/matmul_inputs_static_tile_static_kernel/23-canonicalize.mlir` 与 `24-arch-parallelize.mlir`，比较 host 切片并检查 pattern。
  - 结果：exit 0；`host_unchanged_from_23=True`、`host_no_arch_block=True`、`pattern0_rewrite=True`、`pattern1_rewrite=True`。
  - 说明：计划书原示例中的 `assert "scf.if" not in host` 对当前 pipeline 过宽；host 在 `23-canonicalize` 前已有 pattern selector `scf.if`，本轮核对改为证明 `arch-parallelize` 阶段前后 host 完全不变，且 host 不含 `arch.get_block_id` / `symbol.ne`。
- compileall / AST parse：
  - 命令：`PYTHONDONTWRITEBYTECODE=1 python3 -m compileall -q kernel_gen/passes kernel_gen/dsl/gen_kernel test/passes test/dsl/gen_kernel`，并对主仓 expectation case、`kernel_emitter.py`、`arch_parallelize.py` 执行 `ast.parse(...)`。
  - 结果：exit 0，输出 `compileall_ast_ok`。
- 静态扫描：
  - 旧口径扫描：`! rg -n "entry_point.*block0|entry_point.*arch.get_block_id|entry_point.*scf.if|所有非声明.*无条件|all non-declaration.*unconditional" ...`，exit 0。
  - runtime 能力探测扫描：`! rg -n "hasattr\\(|getattr\\(|callable\\(getattr" kernel_gen/passes/arch_parallelize.py test/passes/test_arch_parallelize.py test/passes/pipeline/test_npu_demo_lowering.py`，exit 0。
  - 跨文件私有 helper 扫描：`! rg -n "from kernel_gen\\.passes\\.arch_parallelize import _|kernel_gen\\.passes\\.arch_parallelize\\._" test/passes`，exit 0。
  - generic allowset AST 扫描：`_generic_symbol_op_name(...)` 中含 `npu_demo`、`builtin.unregistered`、`op_name__`、`symbol.const`、`symbol.eq`，不含 `symbol.ne`、`symbol.fake`、`kernel.add`，exit 0，输出 `generic_allowset_ok`。
- diff check：`git diff --check && git diff --cached --check`，exit 0。
- 敏感目录门禁：
  - `git diff --name-only -- .skills agents/standard expectation AGENTS.md | sort`：空。
  - `git diff --cached --name-only -- .skills agents/standard expectation AGENTS.md | sort`：空。
  - `git status --short --untracked-files=all -- .skills agents/standard`：空。
  - `git status --short --ignored --untracked-files=all -- .skills agents/standard`：空。

### Diff 反推自测

- `kernel_gen/passes/arch_parallelize.py` -> `test/passes/test_arch_parallelize.py`，锁定单 pass host no-op、pattern rewrite、旧 block0 / loop rewrite / unsupported 失败边界。
- `test/passes/pipeline/test_npu_demo_lowering.py` 与 pipeline spec -> `test/passes/pipeline/test_npu_demo_lowering.py`，锁定 pipeline 真实 arch 阶段跳过入口 host，并复测公开 pipeline -> gen_kernel 链路。
- `kernel_gen/dsl/gen_kernel/kernel_emitter.py` 与 `spec/dsl/gen_kernel/kernel_emitter.md` -> `test/dsl/gen_kernel/test_gen_kernel.py -k 'generic_symbol_guard or rejects_other_builtin_unregistered'`，锁定仅放行 generic `"symbol.const"` / `"symbol.eq"`，其它 `builtin.unregistered` 仍失败。
- `spec/pass/registry.md` -> `test/passes/test_registry.py`，确认 registry 公开入口未回退。
- dump 文件为生成现场，不纳入候选 diff；expectation 单列合同验收，不替代 pytest。

### 自检

- 接口：未新增、删除、重命名或修改公开 API / registry option / 工具参数；`ArchParallelizePass` 与 `gen_kernel(...)` 签名不变。
- 公开行为：仅按用户确认跳过带 `entry_point` 属性的 host dispatcher；未扩大为所有无 kernel 标记函数 no-op。
- 架构裁定 A：只补 `builtin.unregistered` + `op_name__` 为 `"symbol.const"` / `"symbol.eq"` 的 npu_demo final host 发射支持；未支持其它 generic op，负例已覆盖。
- 异常 / 稳定错误：未改稳定错误文本；非授权 generic op 仍走既有 `builtin.unregistered: unsupported op`。
- expectation / 敏感目录：未修改、复制、同步、移动、删除或新建 `expectation/`；`.skills`、`agents/standard/**`、`AGENTS.md` 无 diff。
- 跨文件私有 API：测试未直连 `arch_parallelize` 私有 helper；实现未跨文件调用非公开 helper。
- 注释 / API 列表：触达功能实现文件的文件级说明、函数注释已同步当前真实行为；未把内部 helper 写成公开 API。
- 测试有效性：新增 pass / pipeline / gen_kernel 测试在旧实现或未授权扩展时会失败；dump gate 证明 host 在 arch-parallelize 阶段前后不变。
- 残余风险：计划示例 dump 断言中 `scf.if not in host` 与当前 pipeline 既有 selector `scf.if` 不匹配，已用更精确的 host 切片前后完全相等替代并记录；请 review 重点核对该验收口径。

### 结论

- 结论：execute 完成，可进入 review。
- 下一步：通过 `-next -auto` 续接 review，审查重点为 entry host no-op 边界、裁定 A generic allowset 未扩大、expectation 只读合同、dump gate 口径与敏感目录空 diff。

## Review 记录

时间：2026-05-24 02:21 +0800
经办人：提莫炖蘑菇
任务：T-20260524-83a48dea / arch-parallelize-entry-point-skip review
任务目标：审查 execute 完成态是否满足计划级任务：`ArchParallelizePass` 跳过 `entry_point` host dispatcher、pattern/device 函数继续 block rewrite、架构裁定 A 仅最小支持 `kernel_emitter` 的 `builtin.unregistered` + `op_name__` 为 `"symbol.const"` / `"symbol.eq"`，并核对 spec / pytest / dump / expectation / manifest / 门禁 / 任务记录。

### 最新同步现场

- 执行目录：`/home/lfr/kernelcode_generate/wt-20260524-arch-parallelize-entry-point-skip`
- `git fetch origin`：exit 0。
- 分支与基线：`task/arch-parallelize-entry-point-skip`；`HEAD=6369c235736e89499d6c1fc2b7b8bc19f2b564fe`，`origin/main=6369c235736e89499d6c1fc2b7b8bc19f2b564fe`，`merge-base=6369c235736e89499d6c1fc2b7b8bc19f2b564fe`，ahead / behind=`0 / 0`。
- 覆盖风险：候选改动均为 worktree 未提交 diff，基线与 latest main 对齐；未见主线交叉覆盖风险。

### 被审 diff 与记录核对

- 被审 diff：
  - `kernel_gen/passes/arch_parallelize.py`
  - `kernel_gen/dsl/gen_kernel/kernel_emitter.py`
  - `spec/pass/arch_parallelize.md`
  - `spec/pass/pipeline/npu_demo_lowering.md`
  - `spec/pass/registry.md`
  - `spec/dsl/gen_kernel/kernel_emitter.md`
  - `test/passes/test_arch_parallelize.py`
  - `test/passes/pipeline/test_npu_demo_lowering.py`
  - `test/dsl/gen_kernel/test_gen_kernel.py`
  - `agents/codex-multi-agents/log/task_records/2026/24/20260524-arch-parallelize-entry-point-skip.md`
- 执行记录核对：已记录执行前阅读、架构裁定 A、失败复现、最小功能闭环、Diff 反推自测、合同验收、dump gate、compileall / AST、静态扫描、diff check、敏感目录门禁与自检。
- 公开 API / 权限核对：未新增 pass 名称、registry option、公开 helper、工具参数、公开签名或稳定错误文本；未修改 `.skills/`、`agents/standard/**`、`AGENTS.md`、`expectation/`。

### 审查结论

发现：无阻断项。

核对要点：
- `arch_parallelize.py` 仅新增当前文件内私有 `_is_entry_point_func(...)`，在 `apply(...)` 调用 `_rewrite_func(...)` 前跳过带 `entry_point` 属性的 host；无 `entry_point` 的普通函数、pattern/device 函数仍按既有 loop rewrite / block0 guard / unsupported 失败路径处理。
- `kernel_emitter.py` 的裁定 A 实现仅在 `ctx.is_target("npu_demo")` 且 `op.name == "builtin.unregistered"` 时读取 `op_name__`，allowset 只有 `"symbol.const"` / `"symbol.eq"`；其它 `builtin.unregistered` 继续落入 unsupported 路径。
- 测试均通过公开入口验证：pass 测试用 `run_ircheck_text(...)`，pipeline 测试用公开 builder，gen_kernel 测试用公开 `gen_kernel(...)`；未直连 `arch_parallelize` 私有 helper。
- spec 与实现同步写清：只跳过 `entry_point`，不扩大为 kernel-only；非入口 no-loop 函数仍 block0 guard；`KernelEmitter` 的 generic 支持不扩展为通用 `builtin.unregistered`。
- dump gate 对计划示例中过宽的 `scf.if not in host` 作了更精确核对：比较 `23-canonicalize` 与 `24-arch-parallelize` 的 host 切片完全一致，同时确认 host 不含 `arch.get_block_id` / `symbol.ne`，pattern0 / pattern1 均含 `arch.get_block_id`。

### Diff 反推审查与验证

- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/passes/test_arch_parallelize.py test/passes/pipeline/test_npu_demo_lowering.py test/passes/test_registry.py test/dsl/gen_kernel/test_gen_kernel.py` -> exit 0，`184 passed, 1 warning`。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/dsl/gen_kernel/test_gen_kernel.py -k 'generic_symbol_guard or rejects_other_builtin_unregistered'` -> exit 0，`2 passed, 96 deselected, 2 warnings`。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/passes/pipeline/test_npu_demo_lowering.py -k 'supports_kernel_contract_style_public_chain or skips_entry_point_dispatcher'` -> exit 0，`2 passed, 7 deselected, 1 warning`。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/passes/test_arch_parallelize.py -k 'skips_entry_point_host_dispatcher or wraps_no_loop_body_with_block0_guard or rewrites_single_top_level_loop'` -> exit 0，`3 passed, 16 deselected, 1 warning`。
- 额外核验：从 pipeline 公开链路生成 module 后，entry host 内确认为 `UnregisteredOpWithNameOp builtin.unregistered {'op_name__': 'symbol.const'}` 与 `{'op_name__': 'symbol.eq'}`；手工公开 `gen_kernel(...)` 探针直接构造 `UnregisteredOp.with_name("symbol.const")` / `UnregisteredOp.with_name("symbol.eq")`，输出含 `S_INT` 与 `bool`，exit 0，确认裁定 A 正例不是只靠文本解析假绿。
- 合同验收导入探针：从任务 worktree 启动，`expectation.pass.arch_parallelize.entry_point_skip` 来自主仓 `/home/lfr/kernelcode_generate/expectation/pass/arch_parallelize/entry_point_skip.py`，`kernel_gen.passes.arch_parallelize` 与 `kernel_gen.dsl.gen_kernel.kernel_emitter` 来自任务 worktree。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260524-arch-parallelize-entry-point-skip:/home/lfr/kernelcode_generate python3 -m expectation.pass.arch_parallelize` -> exit 0，`block0_guard`、`block_loop`、`dynamic_nested_loop`、`entry_point_skip` 输出均通过。
- expectation exact file-list：`__main__.py`、`block0_guard.py`、`block_loop.py`、`dynamic_nested_loop.py`、`entry_point_skip.py`、`multiple_top_level_loops.py`、`parallel_level.py`，与计划清单一致；`entry_point_skip.py` hash=`83b84e541298c4b6e6ab7d1a8595dbad95f43d69350ea1cf064b25f286eab849`，manifest 与计划一致。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 kernel/matmul/inputs_static_tile_static.py` -> exit 0；dump 核对 -> `host_unchanged_from_23=True`、`host_no_arch_block=True`、`host_keeps_existing_selector_if=True`、`pattern0_rewrite=True`、`pattern1_rewrite=True`。
- `PYTHONDONTWRITEBYTECODE=1 python3 -m compileall -q kernel_gen/passes kernel_gen/dsl/gen_kernel test/passes test/dsl/gen_kernel` -> exit 0。
- AST parse：`kernel_gen/passes/arch_parallelize.py`、`kernel_gen/dsl/gen_kernel/kernel_emitter.py`、三份相关测试与主仓 `expectation/pass/arch_parallelize/entry_point_skip.py` -> exit 0。
- 静态门禁：
  - 旧口径扫描 `entry_point.*block0|entry_point.*arch.get_block_id|entry_point.*scf.if|所有非声明.*无条件|all non-declaration.*unconditional` -> exit 0，无命中。
  - `hasattr/getattr/callable(getattr)` 扫描 `arch_parallelize.py` 与相关测试 -> exit 0，无命中。
  - 测试直连 `arch_parallelize` 私有 helper 扫描 -> exit 0，无命中。
  - `_generic_symbol_op_name(...)` AST allowset -> `generic_allowset_ok`；文本扫描未命中其它 generic `symbol.*` / `dma.*` / `kernel.*` / `nn.*` / `tuner.*` 扩展。
- `git diff --check && git diff --cached --check` -> exit 0。
- 敏感目录门禁：
  - `git diff --name-only -- .skills agents/standard expectation AGENTS.md ARCHITECTURE TODO.md DONE.md spec/API.md` -> 空。
  - `git diff --cached --name-only -- .skills agents/standard expectation AGENTS.md ARCHITECTURE TODO.md DONE.md spec/API.md` -> 空。
  - `git status --short --untracked-files=all -- .skills agents/standard expectation AGENTS.md ARCHITECTURE TODO.md DONE.md` -> 空。
- `git status --short --untracked-files=all` 仅见本轮候选功能 / spec / test diff 与本任务记录文件；`kernel/dump/` 生成现场未进入候选 diff。

### 自检

- 已逐项读取实际 diff，并结合计划、架构裁定 A、执行记录、spec、测试和只读 expectation 核对。
- 已核对 latest main 基线、公开 API、expectation 权限、跨文件私有 API、上下文能力探测、测试有效性、文件级说明 / API 列表与注释同步。
- Diff 反推审查覆盖 `arch_parallelize.py`、`kernel_emitter.py`、相关 spec、pass / pipeline / gen_kernel 测试、dump 现场和任务记录；expectation 单列为合同验收，未替代 pytest。
- 未发现剩余可执行返工项；无公开 API、expectation 授权、tracked 合同落地或口径冲突待用户确认。

结论：review 通过。计划级 execute 已完成审查，建议管理员接架构复核 / 终验；不得直接 merge。

### 状态续接

- 先尝试显式 `-next -to 神秘人 -type other`，脚本返回 `ERROR(3): agent is busy, cannot next to: 神秘人`；未手工修改状态文件。
- 随后按脚本语义执行 `-next -type other`，exit 0：`OK: next T-20260524-83a48dea`、`OK: replace 提莫炖蘑菇 状态`、`OK: talk 提莫炖蘑菇 -> 神秘人 (神秘人)`。
- 状态核对：`T-20260524-83a48dea` 已回到任务列表，类型为 `other`，未指派；`提莫炖蘑菇` 状态为 `free`。请管理员接计划级架构复核 / 终验。

## 第一轮计划级架构复核 / 终验 - 大闸蟹 - 2026-05-24

时间：2026-05-24 当前会话
经办人：大闸蟹
任务：T-20260524-83a48dea / arch-parallelize-entry-point-skip
任务目标：基于 latest main 复核候选 diff、计划正文、任务记录、只读 expectation、pytest / dump / 静态门禁与敏感目录，判断是否可进入第二轮架构终验；不进入 merge。

### 最新同步现场

- 执行目录：`/home/lfr/kernelcode_generate/wt-20260524-arch-parallelize-entry-point-skip`
- `git fetch origin`：exit 0。
- 任务 worktree 当前分支：`task/arch-parallelize-entry-point-skip`。
- 任务 worktree 基线：`HEAD=6369c235736e89499d6c1fc2b7b8bc19f2b564fe`，`origin/main=bb874adfad94ea95697e08acc2bc12be5d34a52f`，`merge-base=6369c235736e89499d6c1fc2b7b8bc19f2b564fe`，ahead / behind=`0 / 1`。
- 候选 diff 是基于旧 base 的未提交 diff；latest main 已合入 `bb874adf Unify KernelCodeError public failures`。
- 候选 diff 与 `HEAD..origin/main` 路径交集：
  - `kernel_gen/passes/arch_parallelize.py`
  - `spec/pass/pipeline/npu_demo_lowering.md`
  - `test/passes/pipeline/test_npu_demo_lowering.py`
- 交集复核结论：主线新增 `KernelCodeError` 公开失败口径，候选新增 `entry_point` skip 与裁定 A 测试；使用临时 latest worktree 验证候选补丁可三方干净应用到 `origin/main=bb874adf`，无文本冲突。

### latest 临时 worktree 复验

- 复验方式：从任务 worktree 导出 `git diff --binary HEAD` 为候选补丁，在临时 worktree `origin/main=bb874adf` 上执行 `git apply --3way`，再运行 pytest、expectation、dump 与静态门禁；临时 worktree 复验后清理，不修改任务 worktree 分支。
- 补丁应用结果：`kernel_gen/dsl/gen_kernel/kernel_emitter.py`、`kernel_gen/passes/arch_parallelize.py`、相关 spec 与 test 均 clean apply。
- Diff 反推 pytest 最低集合：
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/passes/test_arch_parallelize.py test/passes/pipeline/test_npu_demo_lowering.py test/passes/test_registry.py test/dsl/gen_kernel/test_gen_kernel.py`
  - 结果：exit 0，`184 passed, 1 warning`。
- 裁定 A 聚焦测试：
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/dsl/gen_kernel/test_gen_kernel.py -k 'generic_symbol_guard or rejects_other_builtin_unregistered'`
  - 结果：exit 0，`2 passed, 96 deselected, 2 warnings`。
- pipeline entry host 测试：
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/passes/pipeline/test_npu_demo_lowering.py -k 'supports_kernel_contract_style_public_chain or skips_entry_point_dispatcher'`
  - 结果：exit 0，`2 passed, 7 deselected, 1 warning`。
- pass 旧行为与 entry host 聚焦测试：
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/passes/test_arch_parallelize.py -k 'skips_entry_point_host_dispatcher or wraps_no_loop_body_with_block0_guard or rewrites_single_top_level_loop'`
  - 结果：exit 0，`3 passed, 16 deselected, 1 warning`。

### 合同验收与 dump

- `__file__` 探针：
  - `expectation.pass.arch_parallelize.entry_point_skip` 来自主仓 `/home/lfr/kernelcode_generate/expectation/pass/arch_parallelize/entry_point_skip.py`。
  - `kernel_gen.passes.arch_parallelize` 来自 latest 临时 worktree。
  - `kernel_gen.dsl.gen_kernel.kernel_emitter` 来自 latest 临时 worktree。
  - `expectation.pass.arch_parallelize` 是 namespace package，`__file__` 为 `None`，不影响子模块来源核对。
- 只读 expectation：
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=<latest临时worktree>:/home/lfr/kernelcode_generate python3 -m expectation.pass.arch_parallelize`
  - 结果：exit 0；`block0_guard`、`block_loop`、`dynamic_nested_loop`、`entry_point_skip` 均通过。
- 主仓 exact file-list：
  - `expectation/pass/arch_parallelize/__main__.py`
  - `expectation/pass/arch_parallelize/block0_guard.py`
  - `expectation/pass/arch_parallelize/block_loop.py`
  - `expectation/pass/arch_parallelize/dynamic_nested_loop.py`
  - `expectation/pass/arch_parallelize/entry_point_skip.py`
  - `expectation/pass/arch_parallelize/multiple_top_level_loops.py`
  - `expectation/pass/arch_parallelize/parallel_level.py`
- 主仓 manifest 与计划一致；`entry_point_skip.py` hash=`83b84e541298c4b6e6ab7d1a8595dbad95f43d69350ea1cf064b25f286eab849`。
- `git ls-files expectation/pass/arch_parallelize` 为空，符合当前 ignored 本地合同资产口径。
- matmul dump：
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 kernel/matmul/inputs_static_tile_static.py` exit 0。
  - dump 核对结果：`host_unchanged_from_23=True`、`host_no_arch_block=True`、`pattern0_rewrite=True`、`pattern1_rewrite=True`。
  - 计划正文中原示例的 `scf.if not in host` 对当前 pipeline 过宽；本轮已同步计划正文为 `23-canonicalize` 到 `24-arch-parallelize` 的 host 切片完全不变，同时检查 host 不含 `arch.get_block_id` / `symbol.ne`，pattern0 / pattern1 仍 rewrite。

### 静态门禁与敏感目录

- `PYTHONDONTWRITEBYTECODE=1 python3 -m compileall -q kernel_gen/passes kernel_gen/dsl/gen_kernel test/passes test/dsl/gen_kernel`：exit 0。
- AST parse：`kernel_gen/passes/arch_parallelize.py`、`kernel_gen/dsl/gen_kernel/kernel_emitter.py`、相关 test 与主仓 `expectation/pass/arch_parallelize/entry_point_skip.py` 均通过。
- `git diff --check && git diff --cached --check`：exit 0。
- 旧口径扫描 `entry_point.*block0|entry_point.*arch.get_block_id|entry_point.*scf.if|所有非声明.*无条件|all non-declaration.*unconditional`：exit 0，无命中。
- runtime 能力探测扫描 `hasattr/getattr/callable(getattr)`：exit 0，无命中。
- 测试直连 `arch_parallelize` 私有 helper 扫描：exit 0，无命中。
- generic 扩散扫描：未命中除 `"symbol.const"` / `"symbol.eq"` 之外的 generic `symbol.*`、`dma.*`、`kernel.*`、`nn.*`、`tuner.*` 扩展。
- 任务 worktree 敏感 / 禁止面：
  - `git diff --name-only -- .skills agents/standard expectation AGENTS.md ARCHITECTURE TODO.md DONE.md spec/API.md`：空。
  - `git diff --cached --name-only -- .skills agents/standard expectation AGENTS.md ARCHITECTURE TODO.md DONE.md spec/API.md`：空。
  - `git status --short --untracked-files=all -- .skills agents/standard expectation AGENTS.md ARCHITECTURE TODO.md DONE.md`：空。

### 架构复核结论

- `entry_point` host dispatcher no-op 严格限于带 `entry_point` 属性的函数；非入口普通函数和 pattern/device 函数旧行为保持。
- pattern/device 函数仍按既有 block-strided rewrite / block0 guard / unsupported 失败口径处理。
- 裁定 A 未扩大：`KernelEmitter` 只为 `npu_demo` final host 支持 `builtin.unregistered` + `op_name__` 为 `"symbol.const"` / `"symbol.eq"`；其它 generic op 仍走 unsupported。
- expectation 仅只读运行，未修改、移动、新建、删除或 tracked 落地。
- 计划正文与任务记录已闭环：计划状态、终验记录和 dump gate 口径已同步为最新复核结论。
- 未发现最小阻断项；无公开 API、expectation 授权、tracked 合同落地或口径冲突待用户确认。

### 自检

- 已按最新 `origin/main` 复核候选补丁应用性、路径交集、pytest、只读 expectation、dump、compileall / AST、静态扫描和敏感目录。
- expectation 作为合同验收单列执行，未替代 Diff 反推 pytest。
- 本轮未进入 merge，未修改候选功能实现；只补充主仓计划正文状态 / dump gate 口径与本任务记录。

结论：第一轮计划级架构复核 / 终验通过。可进入第二轮架构终验；当前不进入 merge。

## 第二轮计划级架构复核 / 终验 - 守护最好的爱莉希雅 - 2026-05-24

时间：2026-05-24 03:18:56 +0800
经办人：守护最好的爱莉希雅
任务：T-20260524-83a48dea / arch-parallelize-entry-point-skip
任务目标：基于 latest main 对候选 diff、计划正文、任务记录、只读 expectation、matmul dump gate、裁定 A generic allowset 与敏感目录做第二轮计划级架构复核 / 终验；不进入 merge。

### latest 同步与候选 diff

- 执行目录：`/home/lfr/kernelcode_generate/wt-20260524-arch-parallelize-entry-point-skip`
- `git fetch origin --prune`：exit 0。
- 任务 worktree：`HEAD=6369c235736e89499d6c1fc2b7b8bc19f2b564fe`，`origin/main=023d3c9b159d2f05610b68006a81d52a90058ac9`，`merge-base=6369c235736e89499d6c1fc2b7b8bc19f2b564fe`，ahead / behind=`0 / 2`。
- 候选 diff 路径：
  - `kernel_gen/dsl/gen_kernel/kernel_emitter.py`
  - `kernel_gen/passes/arch_parallelize.py`
  - `spec/dsl/gen_kernel/kernel_emitter.md`
  - `spec/pass/arch_parallelize.md`
  - `spec/pass/pipeline/npu_demo_lowering.md`
  - `spec/pass/registry.md`
  - `test/dsl/gen_kernel/test_gen_kernel.py`
  - `test/passes/pipeline/test_npu_demo_lowering.py`
  - `test/passes/test_arch_parallelize.py`
- 候选 diff 与 `HEAD..origin/main` 路径交集：
  - `kernel_gen/passes/arch_parallelize.py`
  - `spec/pass/pipeline/npu_demo_lowering.md`
  - `spec/pass/registry.md`
  - `test/passes/pipeline/test_npu_demo_lowering.py`
- latest 临时 worktree：`/tmp/arch-entry-second.1nEXwL/worktree`，基线 `origin/main=023d3c9b159d2f05610b68006a81d52a90058ac9`。
- 三方应用：从任务 worktree 导出 `git diff --binary` 后在 latest 临时 worktree 执行 `git apply --3way`，9 个候选文件均 clean apply。

### 架构核对

- `ArchParallelizePass` 的行为边界符合计划：只跳过带 `entry_point` 属性的 host dispatcher；无 `entry_point` 的普通函数、pattern/device 函数仍保留既有 loop rewrite / block0 guard / unsupported 失败语义。
- `arch_parallelize.py` 仅新增当前文件内私有 `_is_entry_point_func(...)`，无新增公开 pass 名称、registry option、公开 helper、函数签名或稳定错误文本。
- 裁定 A 未扩大：`KernelEmitter` 只在 `target="npu_demo"` 且 `op.name == "builtin.unregistered"` 时承接 `op_name__` 为 `"symbol.const"` / `"symbol.eq"` 的 final host generic 形态；其它 `builtin.unregistered` 继续按 unsupported 失败。
- spec 与测试同步覆盖 `entry_point` no-op、非入口 no-loop block0 guard、pattern rewrite、pipeline 公开 builder 链路和 `gen_kernel(...)` final host generic guard。

### Diff 反推 pytest

- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/passes/test_arch_parallelize.py test/passes/pipeline/test_npu_demo_lowering.py test/passes/test_registry.py test/dsl/gen_kernel/test_gen_kernel.py`
  - 结果：exit 0，`184 passed, 1 warning`。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/dsl/gen_kernel/test_gen_kernel.py -k 'generic_symbol_guard or rejects_other_builtin_unregistered'`
  - 结果：exit 0，`2 passed, 96 deselected, 2 warnings`。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/passes/pipeline/test_npu_demo_lowering.py -k 'supports_kernel_contract_style_public_chain or skips_entry_point_dispatcher'`
  - 结果：exit 0，`2 passed, 7 deselected, 1 warning`。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/passes/test_arch_parallelize.py -k 'skips_entry_point_host_dispatcher or wraps_no_loop_body_with_block0_guard or rewrites_single_top_level_loop'`
  - 结果：exit 0，`3 passed, 16 deselected, 1 warning`。

### 只读 expectation 与 dump gate

- `__file__` 探针：
  - `expectation.pass.arch_parallelize` 为 namespace package，`__file__=None`。
  - `expectation.pass.arch_parallelize.entry_point_skip` 来自主仓 `/home/lfr/kernelcode_generate/expectation/pass/arch_parallelize/entry_point_skip.py`。
  - `kernel_gen.passes.arch_parallelize` 来自 latest 临时 worktree。
  - `kernel_gen.dsl.gen_kernel.kernel_emitter` 来自 latest 临时 worktree。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/tmp/arch-entry-second.1nEXwL/worktree:/home/lfr/kernelcode_generate python3 -m expectation.pass.arch_parallelize`
  - 结果：exit 0；`block0_guard`、`block_loop`、`dynamic_nested_loop`、`entry_point_skip` 均通过。
- 主仓 `expectation/pass/arch_parallelize`：`git ls-files expectation/pass/arch_parallelize` 为空，符合 ignored 本地合同资产口径；exact file-list 与计划一致；`entry_point_skip.py` hash=`83b84e541298c4b6e6ab7d1a8595dbad95f43d69350ea1cf064b25f286eab849`；完整 `*.py` manifest 与计划一致。
- matmul dump：按仓库实际入口运行 `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 kernel/matmul/inputs_static_tile_static.py`，exit 0。
- dump 核对路径：`kernel/dump/matmul/inputs_static_tile_static_present_bias/matmul_inputs_static_tile_static_kernel`。
- dump gate 结果：`host_unchanged_from_23=True`、`host_has_entry_point=True`、`host_no_arch_block=True`、`pattern0_rewrite=True`、`pattern1_rewrite=True`。

### 静态门禁与敏感目录

- `PYTHONDONTWRITEBYTECODE=1 python3 -m compileall -q kernel_gen/passes kernel_gen/dsl/gen_kernel test/passes test/dsl/gen_kernel`：exit 0。
- AST parse：`kernel_gen/passes/arch_parallelize.py`、`kernel_gen/dsl/gen_kernel/kernel_emitter.py`、三份相关测试与主仓 `expectation/pass/arch_parallelize/entry_point_skip.py` 均通过。
- 旧口径扫描 `entry_point.*block0|entry_point.*arch.get_block_id|entry_point.*scf.if|所有非声明.*无条件|all non-declaration.*unconditional`：exit 0，无命中。
- runtime 能力探测扫描 `hasattr/getattr/callable(getattr)`：exit 0，无命中。
- 测试直连 `arch_parallelize` 私有 helper 扫描：exit 0，无命中。
- generic allowset AST 核对：`generic_symbol_constants=builtin.unregistered,npu_demo,symbol.const,symbol.eq`，`generic_allowset_ok`。
- generic 扩散文本扫描：未发现除 `"symbol.const"` / `"symbol.eq"` 外的 generic `symbol.*`、`dma.*`、`kernel.*`、`nn.*`、`tuner.*` 扩展。
- `git diff --check && git diff --cached --check`：exit 0。
- 敏感目录 / 禁止面：
  - `git diff --name-only -- .skills agents/standard expectation AGENTS.md ARCHITECTURE TODO.md DONE.md spec/API.md`：空。
  - `git diff --cached --name-only -- .skills agents/standard expectation AGENTS.md ARCHITECTURE TODO.md DONE.md spec/API.md`：空。
  - `git status --short --untracked-files=all -- .skills agents/standard expectation AGENTS.md ARCHITECTURE TODO.md DONE.md spec/API.md`：空。
- latest 临时 worktree `git status --short --untracked-files=all` 仅见 9 个候选功能 / spec / test 文件；未出现敏感目录候选 diff。

### 自检

- 已按 latest main 重新复核候选补丁应用性、路径交集、计划正文、任务记录、pytest、只读 expectation、dump、compileall / AST、静态扫描、generic allowset 和敏感目录。
- expectation 作为合同验收单列执行，未替代 Diff 反推 pytest。
- 未修改候选功能实现、spec、test 或 expectation；本轮只写入任务记录。
- 未发现公开 API、expectation 授权、tracked 合同落地、口径冲突或不确定项待用户确认。

结论：第二轮计划级架构复核 / 终验通过。无最小阻断项，无需用户确认；可进入 merge，本轮不直接 merge。

## 最新主线追加复核 - 大闸蟹 - 2026-05-24

时间：2026-05-24 当前会话
触发原因：管理员同步 `T-20260524-c906a59e` 已 merge，`origin/main` 推进到 `023d3c9b159d2f05610b68006a81d52a90058ac9`，要求第一轮架构复核 / 终验改以该 latest 为同步基线。

### 最新同步现场

- 执行目录：`/home/lfr/kernelcode_generate/wt-20260524-arch-parallelize-entry-point-skip`
- `git fetch origin`：exit 0。
- 任务 worktree 基线：`HEAD=6369c235736e89499d6c1fc2b7b8bc19f2b564fe`，`origin/main=023d3c9b159d2f05610b68006a81d52a90058ac9`，`merge-base=6369c235736e89499d6c1fc2b7b8bc19f2b564fe`，ahead / behind=`0 / 2`。
- `origin/main` 新增提交：
  - `bb874adf Unify KernelCodeError public failures`
  - `023d3c9b Publish pass pattern public APIs`
- 候选 diff 与 `HEAD..origin/main` 路径交集：
  - `kernel_gen/passes/arch_parallelize.py`
  - `spec/pass/pipeline/npu_demo_lowering.md`
  - `spec/pass/registry.md`
  - `test/passes/pipeline/test_npu_demo_lowering.py`

### latest 应用与复验

- 复验方式：导出任务 worktree 候选 diff，在临时 latest worktree `origin/main=023d3c9b159d2f05610b68006a81d52a90058ac9` 上执行 `git apply --3way` 并复跑门禁；临时 worktree 清理，不修改任务 worktree 分支。
- 三方 apply：`kernel_gen/dsl/gen_kernel/kernel_emitter.py`、`kernel_gen/passes/arch_parallelize.py`、相关 spec 与 test 均 clean apply。
- Diff 反推 pytest 最低集合：
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/passes/test_arch_parallelize.py test/passes/pipeline/test_npu_demo_lowering.py test/passes/test_registry.py test/dsl/gen_kernel/test_gen_kernel.py`
  - 结果：exit 0，`184 passed, 1 warning`。
- 裁定 A 聚焦测试：
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/dsl/gen_kernel/test_gen_kernel.py -k 'generic_symbol_guard or rejects_other_builtin_unregistered'`
  - 结果：exit 0，`2 passed, 96 deselected, 2 warnings`。
- pipeline entry host 聚焦测试：
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/passes/pipeline/test_npu_demo_lowering.py -k 'supports_kernel_contract_style_public_chain or skips_entry_point_dispatcher'`
  - 结果：exit 0，`2 passed, 7 deselected, 1 warning`。
- pass 旧行为与 entry host 聚焦测试：
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/passes/test_arch_parallelize.py -k 'skips_entry_point_host_dispatcher or wraps_no_loop_body_with_block0_guard or rewrites_single_top_level_loop'`
  - 结果：exit 0，`3 passed, 16 deselected, 1 warning`。
- 只读 expectation：
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=<latest临时worktree>:/home/lfr/kernelcode_generate python3 -m expectation.pass.arch_parallelize`
  - 结果：exit 0；导入来源仍为 expectation 子模块来自主仓，候选实现来自 latest 临时 worktree。
- matmul dump：
  - `timeout 180s env PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 kernel/matmul/inputs_static_tile_static.py` exit 0。
  - dump 核对：`host_unchanged_from_23=True`、`host_no_arch_block=True`、`pattern0_rewrite=True`、`pattern1_rewrite=True`。
- `PYTHONDONTWRITEBYTECODE=1 python3 -m compileall -q kernel_gen/passes kernel_gen/dsl/gen_kernel test/passes test/dsl/gen_kernel`：exit 0。
- `git diff --check && git diff --cached --check`：exit 0。
- 静态扫描：旧口径、runtime 能力探测、测试直连私有 helper、generic 扩散扫描均 exit 0。
- 敏感目录：`.skills`、`agents/standard`、`expectation`、`AGENTS.md`、`ARCHITECTURE`、`TODO.md`、`DONE.md`、`spec/API.md` 的 diff / cached diff / untracked status 均为空。

### 追加复核结论

- 新主线 `023d3c9b` 与候选存在路径交集，但候选补丁可 clean apply 且所有复验门禁通过。
- `pass-pattern-public-api-refactor` 的最新合入未改变本任务公开 API 边界，也未破坏 `entry_point` host no-op、pattern/device 旧行为或裁定 A generic allowset。
- 前一段基于 `bb874adf` 的第一轮结论被本段 latest `023d3c9b` 复核覆盖。
- 未发现新的最小阻断项或需用户确认项；第一轮计划级架构复核 / 终验仍为通过。可进入第二轮架构终验；当前不进入 merge。

## 第二轮最终回报补充 - 守护最好的爱莉希雅 - 2026-05-24

- 第二轮计划级架构复核 / 终验详见上文“第二轮计划级架构复核 / 终验 - 守护最好的爱莉希雅 - 2026-05-24”。
- 该第二轮已基于 latest `origin/main=023d3c9b159d2f05610b68006a81d52a90058ac9` 临时 worktree clean apply 候选 diff，并复跑 pytest、只读 expectation、matmul dump、compileall / AST、静态扫描、generic allowset 与敏感目录门禁。
- 最终结论：第二轮计划级架构复核 / 终验通过；无最小阻断项，无需用户确认；可进入 merge，本轮不直接 merge。

---

## 2026-05-24 03:32 +0800 李白 merge 记录

时间：2026-05-24 03:32 +0800

经办人：李白

任务：`T-20260524-83a48dea / arch-parallelize-entry-point-skip`

任务目标：按合并规范合入已通过 review 与双架构终验的 `arch-parallelize` entry_point host no-op 候选，确保代码 / spec / test 与任务记录同批提交并推送 `origin/main`。

合入来源：

- 来源 worktree：`/home/lfr/kernelcode_generate/wt-20260524-arch-parallelize-entry-point-skip`。
- 来源分支：`task/arch-parallelize-entry-point-skip`。
- 合并前同步：任务 worktree 原 `HEAD=6369c235736e89499d6c1fc2b7b8bc19f2b564fe`，`origin/main=023d3c9b159d2f05610b68006a81d52a90058ac9`，`merge-base=6369c235736e89499d6c1fc2b7b8bc19f2b564fe`，`ahead/behind=0/2`。
- 同步动作：先用 `git stash push -u -m T-20260524-83a48dea-pre-latest-sync` 保存候选 diff 与未跟踪任务记录，再 `git merge --ff-only origin/main` 快进到 latest main，最后 `git stash pop` 恢复候选。
- 路径交集：`kernel_gen/passes/arch_parallelize.py`、`spec/pass/pipeline/npu_demo_lowering.md`、`spec/pass/registry.md`、`test/passes/pipeline/test_npu_demo_lowering.py`。
- 冲突处理：上述交集文件自动合并，无冲突标记；`rg -n '<<<<<<<|=======|>>>>>>>' kernel_gen/dsl/gen_kernel kernel_gen/passes spec/pass spec/dsl test/dsl test/passes agents/codex-multi-agents/log/task_records/2026/24/20260524-arch-parallelize-entry-point-skip.md` 无命中。
- 同步后基线：`HEAD=origin/main=merge-base=023d3c9b159d2f05610b68006a81d52a90058ac9`，`ahead/behind=0/0`。

实际合入文件：

- 实现：`kernel_gen/passes/arch_parallelize.py`、`kernel_gen/dsl/gen_kernel/kernel_emitter.py`。
- spec：`spec/pass/arch_parallelize.md`、`spec/pass/pipeline/npu_demo_lowering.md`、`spec/pass/registry.md`、`spec/dsl/gen_kernel/kernel_emitter.md`。
- test：`test/passes/test_arch_parallelize.py`、`test/passes/pipeline/test_npu_demo_lowering.py`、`test/dsl/gen_kernel/test_gen_kernel.py`。
- 任务记录：`agents/codex-multi-agents/log/task_records/2026/24/20260524-arch-parallelize-entry-point-skip.md`。

验证：

- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/passes/test_arch_parallelize.py test/passes/pipeline/test_npu_demo_lowering.py test/passes/test_registry.py test/dsl/gen_kernel/test_gen_kernel.py`：exit 0，`184 passed, 1 warning`。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/dsl/gen_kernel/test_gen_kernel.py -k 'generic_symbol_guard or rejects_other_builtin_unregistered'`：exit 0，`2 passed, 96 deselected, 2 warnings`。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/passes/pipeline/test_npu_demo_lowering.py -k 'supports_kernel_contract_style_public_chain or skips_entry_point_dispatcher'`：exit 0，`2 passed, 7 deselected, 1 warning`。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/passes/test_arch_parallelize.py -k 'skips_entry_point_host_dispatcher or wraps_no_loop_body_with_block0_guard or rewrites_single_top_level_loop'`：首次并行执行超时；单独重跑 exit 0，`3 passed, 16 deselected, 1 warning`。该 3 项也已包含在最低集合 `184 passed` 中。
- 只读 expectation 导入探针：从任务 worktree 启动，`expectation.pass.arch_parallelize.entry_point_skip` 来自主仓 `/home/lfr/kernelcode_generate/expectation/pass/arch_parallelize/entry_point_skip.py`；`kernel_gen.passes.arch_parallelize` 和 `kernel_gen.dsl.gen_kernel.kernel_emitter` 来自任务 worktree；`expectation.pass.arch_parallelize` 为 namespace package，`__file__=None`。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260524-arch-parallelize-entry-point-skip:/home/lfr/kernelcode_generate python3 -m expectation.pass.arch_parallelize`：exit 0；`block0_guard`、`block_loop`、`dynamic_nested_loop`、`entry_point_skip` 均通过。
- matmul dump：`PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 kernel/matmul/inputs_static_tile_static.py` exit 0；dump gate 输出 `host_unchanged_from_23=True`、`host_has_entry_point=True`、`host_no_arch_block=True`、`pattern0_rewrite=True`、`pattern1_rewrite=True`。
- `PYTHONDONTWRITEBYTECODE=1 python3 -m compileall -q kernel_gen/passes kernel_gen/dsl/gen_kernel test/passes test/dsl/gen_kernel` 与 AST parse：exit 0，`compileall_ast_ok`。
- 静态扫描：旧口径扫描、runtime 能力探测扫描、测试直连 `arch_parallelize` 私有 helper 扫描、generic 扩散扫描均无命中，输出 `static_rg_ok`。
- generic allowset AST 核对：`_generic_symbol_op_name(...)` 常量仅含目标相关 `builtin.unregistered`、`npu_demo`、`op_name__`、`symbol.const`、`symbol.eq` 及 docstring 文本；未出现 `symbol.ne`、`symbol.fake`、`dma.*`、`kernel.*`、`nn.*`、`tuner.*` 等扩散常量，输出 `generic_allowset_ok`。
- `git diff --check && git diff --cached --check`：exit 0。

只读 expectation manifest / scope：

- 主仓 `git ls-files expectation/pass/arch_parallelize`：空，符合 ignored 本地合同资产口径。
- 主仓 exact file-list 与计划一致：
  - `expectation/pass/arch_parallelize/__main__.py`
  - `expectation/pass/arch_parallelize/block0_guard.py`
  - `expectation/pass/arch_parallelize/block_loop.py`
  - `expectation/pass/arch_parallelize/dynamic_nested_loop.py`
  - `expectation/pass/arch_parallelize/entry_point_skip.py`
  - `expectation/pass/arch_parallelize/multiple_top_level_loops.py`
  - `expectation/pass/arch_parallelize/parallel_level.py`
- `entry_point_skip.py` hash=`83b84e541298c4b6e6ab7d1a8595dbad95f43d69350ea1cf064b25f286eab849`，完整 `*.py` manifest 与计划一致。
- 本轮未执行 `git add -f expectation/...`，未修改、复制、同步、移动、删除或新建 `expectation/`。

敏感目录与禁止面核对：

- `git diff --name-only -- kernel/dump .skills agents/standard expectation AGENTS.md TODO.md DONE.md ARCHITECTURE plan spec/API.md`：空。
- `git diff --cached --name-only -- kernel/dump .skills agents/standard expectation AGENTS.md TODO.md DONE.md ARCHITECTURE plan spec/API.md`：空。
- `git status --short --untracked-files=all -- kernel/dump .skills agents/standard expectation AGENTS.md TODO.md DONE.md ARCHITECTURE plan spec/API.md`：空。
- `kernel/dump` 仅有 ignored 生成现场，不属于候选 diff；按计划不使用 `git status --ignored -- expectation` 是否为空作为 expectation 通过 / 失败依据。

剩余风险：

- 任务记录中已说明计划示例中过宽的 `scf.if not in host` 已收口为更精确的 `23-canonicalize` 到 `24-arch-parallelize` host 切片完全不变，并额外检查 host 不含 `arch.get_block_id` / `symbol.ne`；本轮 merge gate 复核通过。
- 当前未清理任务 worktree / 分支；原因是本轮仅授权 merge，且管理员此前要求 worktree / 分支清理范围确认后再处理。merge 完成回报中继续明确该状态。

结论：

- 候选 diff、任务记录、review 与双架构终验记录闭环；merge gate 已复跑通过，敏感目录与禁止面为空。
- 可将上述代码 / spec / test 与本任务记录同批提交并推送 `origin/main`，随后执行 `-done`。
