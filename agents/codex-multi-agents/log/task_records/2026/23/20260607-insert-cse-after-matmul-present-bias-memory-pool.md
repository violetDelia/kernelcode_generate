时间：2026-06-07 16:55 CST
经办人：小李飞刀
任务：T-20260607-eb659882 / insert-cse-after-matmul-present-bias-memory-pool / execute 阻塞记录
任务目标：在 `npu-demo-lowering` 的 `memory-pool` 后插入一轮 CSE，重新生成 matmul static/static present-bias dump，并同步必要 spec/test。
执行前阅读记录：
- 已读取根 `AGENTS.md`、`agents/codex-multi-agents/agents/小李飞刀/小李飞刀.prompt.md`、`agents/standard/任务记录约定.md`、当前 TODO 任务、管理员下发消息、`kernel_gen/pipeline/npu_demo_lowering.py`、`spec/pass/pipeline/npu_demo_lowering.md`、`test/passes/pipeline/test_npu_demo_lowering.py`、matmul demo 脚本与相关测试。
- 依赖核对：执行前 `git fetch --prune origin`，`origin/main=cf89a43112e3368bbefdd8df4e97c98758a6525c`，为 `Merge pass directory layout refactor`；已 `git merge --ff-only origin/main`，当前 `HEAD=origin/main=merge-base=cf89a43112e3368bbefdd8df4e97c98758a6525c`。
- 禁止面核对：本轮不得修改 `expectation/`、`.skills/`、`agents/standard/`、`AGENTS.md`；如需调整公开 API 或 expectation 本体，停止并回报管理员转用户 / 架构确认。
改动：
- `kernel_gen/pipeline/npu_demo_lowering.py`：在 `MemoryPoolPass(rewrite=True, alignment=1024)` 后、既有 `CanonicalizePass()` 前插入 `CommonSubexpressionElimination()`；同步文件级说明和 builder 函数说明的公开顺序。
- `spec/pass/pipeline/npu_demo_lowering.md`：同步公开 pipeline 顺序为 `memory-pool -> cse -> canonicalize -> arch-parallelize -> attach-arch-information -> outline-device-kernel -> template-name-infer`；CSE 次数从 4 次更新为 5 次，后续公开顺序编号顺延。
- `test/passes/pipeline/test_npu_demo_lowering.py`：同步 pass order、真实 dump marker、`26-memory-pool -> 27-cse -> 28-canonicalize` 与后续序号断言。
- `kernel/matmul/inputs_dynamic_tile_dynamic.py`、`kernel/matmul/inputs_static_tile_dynamic.py`、`test/kernel/test_matmul_symbolic_memory_genkernel.py`：demo/source 自检兼容 latest main context-first 生成源码中的 `deslice(ctx, arg0, ...)`，否则相关 matmul demo 脚本会在当前主线上因旧 `deslice(arg0` 文本断言失败；未改变生成逻辑或公开 API。
最小功能闭环：
- 实现入口：公开 `build_npu_demo_lowering_pipeline(...)` 返回的 `PassManager` 中，`memory-pool` 后新增一轮 xDSL `CommonSubexpressionElimination`，保留后续 `CanonicalizePass`。
- spec/test 入口：公开 pipeline spec、pass order pytest 和真实 dump pytest 均锁定新顺序。
- dump 入口：已重新运行 `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 kernel/matmul/inputs_static_tile_static.py` 生成 ignored dump；`kernel/dump/matmul/inputs_static_tile_static_present_bias/matmul_inputs_static_tile_static_kernel` 共 32 个 `.mlir`，关键序列为 `26-memory-pool.mlir: memory-pool`、`27-cse.mlir: cse`、`28-canonicalize.mlir: canonicalize`、`29-arch-parallelize.mlir: arch-parallelize`、`32-template-name-infer.mlir: template-name-infer`。
- 当前失败边界：只读共享 expectation `expectation.pass.pipeline.npu_demo_lowering` 仍期望旧顺序 `memory-pool -> canonicalize`，需要修改 expectation 本体或由架构明确本任务不以该 ignored expectation 为阻断；execute 无权修改 expectation，故暂停。
验证：
- 同步基线：`git rev-parse HEAD && git rev-parse origin/main && git merge-base HEAD origin/main` 均为 `cf89a43112e3368bbefdd8df4e97c98758a6525c`。
- 目标 pipeline pytest：`PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/passes/pipeline/test_npu_demo_lowering.py -k 'pass_order or dynamic_acc_kernel_decompose_dump or static_dump_runs_multi_buffer_before_pool'`，`3 passed, 8 deselected, 1 warning`。
- 重新生成 present-bias dump：`PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 kernel/matmul/inputs_static_tile_static.py`，exit 0，stdout 含 `matmul/inputs_static_tile_static_absent_bias max_abs_diff=2.6702880859375e-05` 与 `matmul/inputs_static_tile_static_present_bias max_abs_diff=2.6702880859375e-05`。
- dump 序列核对：`27-cse.mlir` 被 `.gitignore:25:dump` 忽略；`dump_file_count=32`；`26-memory-pool.mlir` 首行为 `memory-pool`、`27-cse.mlir` 首行为 `cse`、`28-canonicalize.mlir` 首行为 `canonicalize`、`29-arch-parallelize.mlir` 首行为 `arch-parallelize`、`32-template-name-infer.mlir` 首行为 `template-name-infer`。
- 完整 pipeline pytest：`PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/passes/pipeline/test_npu_demo_lowering.py`，`11 passed, 1 warning`。
- matmul demo pytest：`PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/kernel/test_matmul_symbolic_memory_genkernel.py`，`4 passed, 1 warning`。
- 相关 pipeline / registry / tool 组合：`PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/passes/pipeline/test_npu_demo_lowering.py test/passes/test_registry.py test/tools/test_dsl_cost_run.py`，`80 passed, 1 warning`。
- main pipeline 测试：`PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/test_main_npu_demo_pipeline.py`，`2 passed, 2 warnings`。
- 全量 pass 测试：`PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/passes`，`589 passed, 1 warning`。
- KCE / private API 门禁：`PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/tools/test_kernel_code_error_static_gate.py test/repo_conformance/test_private_api_boundaries.py`，`7 passed`。
- py_compile：`PYTHONDONTWRITEBYTECODE=1 python3 -m py_compile kernel_gen/pipeline/npu_demo_lowering.py test/passes/pipeline/test_npu_demo_lowering.py` 与 `PYTHONDONTWRITEBYTECODE=1 python3 -m py_compile kernel/matmul/inputs_dynamic_tile_dynamic.py kernel/matmul/inputs_static_tile_dynamic.py test/kernel/test_matmul_symbolic_memory_genkernel.py` 均 exit 0。
- 格式门禁：`git diff --check && git diff --cached --check`，exit 0。
- 敏感目录门禁：`git status --short --untracked-files=all -- .skills expectation agents/standard AGENTS.md TODO.md DONE.md plan/1.md`、`git diff -- .skills expectation agents/standard AGENTS.md TODO.md DONE.md plan/1.md`、`git diff --cached -- .skills expectation agents/standard AGENTS.md TODO.md DONE.md plan/1.md` 均无输出。
- 只读合同验收阻塞：`PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260607-insert-cse-after-matmul-present-bias-memory-pool:/home/lfr/kernelcode_generate python3 -m expectation.pass.pipeline.npu_demo_lowering`，exit 1；失败摘要为 actual order 在 `memory-pool:True:1024` 后包含新增 `cse`，expected 仍为 `memory-pool:True:1024 -> canonicalize -> arch-parallelize...`。
Diff 反推自测：
- `kernel_gen/pipeline/npu_demo_lowering.py`、`spec/pass/pipeline/npu_demo_lowering.md`、`test/passes/pipeline/test_npu_demo_lowering.py` 反推：pipeline 目标 pytest、完整 pipeline pytest、相关 registry/tool 组合、全量 `test/passes`、dump marker 核对。
- `kernel/matmul/inputs_dynamic_tile_dynamic.py`、`kernel/matmul/inputs_static_tile_dynamic.py`、`test/kernel/test_matmul_symbolic_memory_genkernel.py` 反推：完整 matmul demo pytest、目标脚本执行测试、py_compile。
- `kernel/dump/**` 是 ignored 诊断产物，不纳入 git diff；本轮按任务要求已在工作区重新生成并核对 present-bias 关键序列。
- expectation 是合同验收资产，不计入 diff 反推；只读运行发现需调整 expected order，已单列为阻塞。
减法检查：
- 新增 private callable：无。
- 改动 private callable：`kernel/matmul/inputs_dynamic_tile_dynamic.py::_assert_accumulator_source`、`kernel/matmul/inputs_static_tile_dynamic.py::_assert_accumulator_source`、`test/kernel/test_matmul_symbolic_memory_genkernel.py::_assert_source_uses_accumulator` 仅扩展公开生成源码文本匹配，支持 `deslice(ctx, arg0, ...)`；没有调用跨文件 private helper。
- 被替代旧逻辑：未删除旧 `deslice(arg0, ...)` 兼容匹配，新增 context-first fallback，避免旧源码格式仍可测试时被误拒绝。
- 保留旧逻辑依据：生成源码格式在不同合入阶段存在旧 direct 调用与 context-first 调用两种文本；自检只锁定 accumulator 顺序，不应绑定单一参数前缀。
自检：
- 接口：未新增 pipeline option，未修改 builder 签名，未改 registry 名称，未新增 / 删除公开 API；本轮改变的是任务授权的公开 pipeline 固定顺序。
- 边界 / 异常：unknown option、target 等公开错误语义未改；新增 CSE 使用已有 xDSL pass，不引入 context 能力探测。
- 兼容：post-pool CSE 后仍保留 canonicalize、arch-parallelize、attach、outline、template-name-infer 顺序；demo/source 自检兼容旧与 context-first 两种公开源码文本。
- 实现遗漏 / 冗余：spec、实现、pipeline pytest、dump 产物和 demo 自检均已同步；未新增无关 helper。
- 资源 / 并发 / 性能：只增加一轮 CSE，未改变 memory-pool rewrite、multi-buffer、producer-consumer-analysis 或 runtime launch 参数。
- 测试有效性：pytest 与 dump marker 能在新 CSE 缺失、位置错误或后续序号未顺延时失败；只读 expectation 失败明确暴露合同资产未同步。
结论：代码 / spec / pytest / dump 已按任务目标收口，但共享 `expectation.pass.pipeline.npu_demo_lowering` 需要同步 expected order 或由架构明确本任务不以该 expectation 为阻断。因任务明确禁止修改 `expectation/` 且要求发现需调整 expectation 本体时停止回报，当前不 `-next review`，等待管理员 / 架构确认。

阻塞回报同步：
- 2026-06-07 16:59 CST，已通过 `codex-multi-agents-tmux.sh -talk` 向管理员 `神秘人` 回报阻塞，并给出 A=安排 / 授权同步 expectation、B=裁定 expectation 不作为阻断并允许 `-next review`、C=其它处理三种决策选项。
- 2026-06-07 16:59 CST，已通过 `codex-multi-agents-tmux.sh -talk` 向架构师 `大闸蟹` 请求公开 pipeline 合同 / expectation 口径确认。
- 管理员已转发给架构并明确：`T-20260607-eb659882` 当前因 expectation 合同口径暂停，不允许 execute 继续或 `-next`；等待架构裁定。

时间：2026-06-07 17:04 CST
经办人：小李飞刀
任务：T-20260607-eb659882 / insert-cse-after-matmul-present-bias-memory-pool / execute 恢复收口
任务目标：按架构裁定 A 极窄同步 `expectation.pass.pipeline.npu_demo_lowering` leaf 合同到 `memory-pool -> cse -> canonicalize`，复跑合同验收后流转 review。
执行前阅读记录：
- 已读取管理员恢复 execute 消息：大闸蟹裁定 A；授权范围仅 `expectation/pass/pipeline/npu_demo_lowering.py`，把 expected order 中 `memory-pool:True:1024 -> canonicalize` 更新为 `memory-pool:True:1024 -> cse -> canonicalize`，并按需要补 / 改该 leaf 内相邻顺序断言或说明。
- 授权禁止面：不得新增 / 修改 / 删除 `expectation/pass/pipeline/__main__.py`、其它 pipeline leaf、其它 expectation 文件或目录级聚合；不得扩大到其它合同资产；若需修改其它 expectation、改变额外公开 API、调整 pipeline 其它阶段或扩大任务目标，必须再次暂停回报。
- 用户确认口径：管理员明确“无需新增用户确认，因为用户已明确要求在 `26-memory-pool.mlir` 后加 `cse`，本次只是同步既有 leaf 合同到该公开 pipeline 顺序”。
改动：
- 主仓 ignored 合同资产 `/home/lfr/kernelcode_generate/expectation/pass/pipeline/npu_demo_lowering.py`：在 expected order 中于 `memory-pool:True:1024` 后加入 `cse`，保留后续 `canonicalize`；补充文件说明与 `main()` 说明；新增相邻顺序断言，锁定 `memory-pool:True:1024 -> cse -> canonicalize`。
- 该 `expectation/` leaf 是主仓 ignored 合同资产，任务 worktree 内无 `expectation/pass/pipeline`；本轮不把 `expectation/` 写入普通 candidate diff，不 force-add ignored 合同资产。
最小功能闭环：
- 实现 / spec / test / dump 闭环沿用前一段执行记录：代码、spec、pytest、matmul present-bias dump 均已体现 `26-memory-pool -> 27-cse -> 28-canonicalize`。
- 合同闭环：`expectation.pass.pipeline.npu_demo_lowering` 现在在 worktree-first `PYTHONPATH` 下通过，实际导入任务 worktree 中的 `kernel_gen.pipeline` 并使用主仓 leaf 合同校验公开 pipeline 顺序。
验证：
- expectation 修改前 hash：`5984d4f8525a4fc2d0e420127336cd4b1aea45abd689708ee5a6421eed0c88c7  expectation/pass/pipeline/npu_demo_lowering.py`。
- expectation 修改后 hash：`a61596ae6abf0c84a12e822c84f44a52530548a3a8fc387cea724bd10b3b632c  /home/lfr/kernelcode_generate/expectation/pass/pipeline/npu_demo_lowering.py`。
- 合同验收：`PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260607-insert-cse-after-matmul-present-bias-memory-pool:/home/lfr/kernelcode_generate python3 -m expectation.pass.pipeline.npu_demo_lowering`，exit 0，输出 `[pass-pipeline-npu_demo_lowering-order-1] pass: npu-demo-lowering order is stable.`。
- expectation py_compile：`PYTHONDONTWRITEBYTECODE=1 python3 -m py_compile /home/lfr/kernelcode_generate/expectation/pass/pipeline/npu_demo_lowering.py`，exit 0。
- expectation leaf 范围核对：`find /home/lfr/kernelcode_generate/expectation/pass/pipeline -maxdepth 1 -type f -printf ...` 仅显示 `npu_demo_lowering.py`；`test ! -e /home/lfr/kernelcode_generate/expectation/pass/pipeline/__main__.py` 输出 `__main__.py absent`；`rg` 核对 leaf 中存在 `memory-pool:True:1024` 后的 `cse` 与相邻断言。
- worktree 敏感目录门禁：`git status --short --untracked-files=all -- .skills expectation agents/standard AGENTS.md TODO.md DONE.md plan/1.md` 无输出。
- 保留前序已通过验证：pipeline pytest `11 passed`；matmul demo pytest `4 passed`；相关 pipeline / registry / tool 组合 `80 passed`；`test/passes` `589 passed`；KCE / private API `7 passed`；实现与测试 `py_compile` 通过；`git diff --check && git diff --cached --check` 通过；present-bias dump 序列为 `26-memory-pool.mlir -> 27-cse.mlir -> 28-canonicalize.mlir`。
Diff 反推自测：
- 普通 candidate diff 的反推自测仍是前序记录中的 pipeline pytest、matmul demo pytest、相关组合测试、全量 `test/passes`、KCE / private API、py_compile 与 dump marker 核对。
- `expectation/pass/pipeline/npu_demo_lowering.py` 是合同验收资产，本轮只在架构裁定 A 授权范围内同步 leaf 合同；其验收单列为“合同验收”，不计入 Diff 反推自测。
减法检查：
- 新增 / 改动 private callable：无。
- expectation leaf 中仅补 expected order 元素、说明和相邻顺序断言；未新增公开 API，未新增目录级聚合，未修改 `__main__.py`。
- 未删除旧 `canonicalize` 期望；只是把旧相邻顺序从 `memory-pool -> canonicalize` 收口为 `memory-pool -> cse -> canonicalize`。
自检：
- 接口：未修改 builder 签名、工具入口、registry option、pass 名称或错误语义；本轮只同步已授权的公开 pipeline 顺序合同。
- 边界：未修改其它 expectation leaf、目录级聚合、`expectation/pass/pipeline/__main__.py` 或其它合同资产；若 review 发现额外 expectation 变更，应退回。
- 测试有效性：合同验收会在 post-memory-pool CSE 缺失或位置错误时失败；pytest / dump marker 会在 dump 序号或 marker 错误时失败。
结论：架构裁定 A 已收口；实现 / spec / test / dump / expectation leaf 合同均体现 `memory-pool -> cse -> canonicalize`。准备执行最终门禁并按流程 `-next review`。

时间：2026-06-07 17:13 CST
经办人：提莫炖蘑菇
任务：T-20260607-eb659882 / insert-cse-after-matmul-present-bias-memory-pool / review
任务目标：审查按架构裁定 A 收口后的候选，确认代码 / spec / test / dump / expectation 均体现 `memory-pool -> cse -> canonicalize`，且 expectation 变更只命中授权 leaf。
审查结论：通过。未发现阻断或最小需改项；该任务无计划书字段，按普通 review 通过后可续接 `merge`。
发现：
- 无阻断发现。
审查范围：
- worktree：`/home/lfr/kernelcode_generate/wt-20260607-insert-cse-after-matmul-present-bias-memory-pool`
- latest main：`HEAD=origin/main=merge-base=cf89a43112e3368bbefdd8df4e97c98758a6525c`，ahead / behind `0 0`。
- 普通 staged diff：7 个路径，包含任务记录、`kernel_gen/pipeline/npu_demo_lowering.py`、`spec/pass/pipeline/npu_demo_lowering.md`、`test/passes/pipeline/test_npu_demo_lowering.py`、两个 matmul demo 脚本和 `test/kernel/test_matmul_symbolic_memory_genkernel.py`。
- 合同资产：主仓 ignored leaf `/home/lfr/kernelcode_generate/expectation/pass/pipeline/npu_demo_lowering.py`，`sha256=a61596ae6abf0c84a12e822c84f44a52530548a3a8fc387cea724bd10b3b632c`；未把 `expectation/` 写入普通 staged diff。
执行记录核对：
- 已核对 16:55 阻塞记录与 17:04 架构裁定 A 恢复收口记录。执行记录写清执行前阅读、最小功能闭环、验证、`Diff 反推自测`、减法检查、自检、expectation 授权范围和禁止面。
- 管理员 / 架构口径为极窄授权：只允许同步 `expectation/pass/pipeline/npu_demo_lowering.py`，不得新增 / 修改 / 删除 `expectation/pass/pipeline/__main__.py`、其它 pipeline leaf 或目录聚合。复审确认源码 leaf hash 符合记录，`__main__.py` 不存在。
验证：
- 主线核对：`git fetch --prune origin && git rev-parse HEAD && git rev-parse origin/main && git merge-base HEAD origin/main && git rev-list --left-right --count HEAD...origin/main` -> `HEAD=origin/main=merge-base=cf89a43112e3368bbefdd8df4e97c98758a6525c`，ahead / behind `0 0`。
- 普通 diff 核对：`git diff --cached --name-status` 为 7 个 staged 路径；`git diff --name-status` 无输出；worktree 普通候选未包含 `expectation/`。
- expectation leaf 核对：`sha256sum /home/lfr/kernelcode_generate/expectation/pass/pipeline/npu_demo_lowering.py` -> `a61596ae6abf0c84a12e822c84f44a52530548a3a8fc387cea724bd10b3b632c`；`find /home/lfr/kernelcode_generate/expectation/pass/pipeline -maxdepth 1 -type f` 仅有 `npu_demo_lowering.py`；`test ! -e /home/lfr/kernelcode_generate/expectation/pass/pipeline/__main__.py` 通过。
- ignored 资产状态：`git -C /home/lfr/kernelcode_generate check-ignore -v expectation/pass/pipeline/npu_demo_lowering.py expectation/pass/pipeline/__pycache__/npu_demo_lowering.cpython-312.pyc` 显示二者均由 `.gitignore:21:expectation` 忽略；`__pycache__` 是验收 / py_compile 生成缓存，不是授权源码 leaf，merge 阶段必须排除。
- 合同验收：`PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260607-insert-cse-after-matmul-present-bias-memory-pool:/home/lfr/kernelcode_generate python3 -m expectation.pass.pipeline.npu_demo_lowering` -> exit 0，输出 `[pass-pipeline-npu_demo_lowering-order-1] pass: npu-demo-lowering order is stable.`。
- pipeline pytest：`PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/passes/pipeline/test_npu_demo_lowering.py` -> `11 passed, 1 warning`。
- matmul demo pytest：`PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/kernel/test_matmul_symbolic_memory_genkernel.py` -> `4 passed, 1 warning`。
- matmul demo 脚本：`PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 kernel/matmul/inputs_static_tile_static.py` -> exit 0，stdout 含 absent / present bias `max_abs_diff=2.6702880859375e-05`。
- dump marker 核对：`kernel/dump/matmul/inputs_static_tile_static_present_bias/matmul_inputs_static_tile_static_kernel` 下 `.mlir` 数量为 32，首行序列为 `26-memory-pool.mlir: memory-pool`、`27-cse.mlir: cse`、`28-canonicalize.mlir: canonicalize`、`29-arch-parallelize.mlir: arch-parallelize`、`32-template-name-infer.mlir: template-name-infer`。
- 组合 pytest：`PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/passes/test_registry.py test/tools/test_dsl_cost_run.py test/test_main_npu_demo_pipeline.py` -> `71 passed, 1 warning`。
- 全量 pass：`PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/passes` -> `589 passed, 1 warning`。
- KCE / private API：`PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/tools/test_kernel_code_error_static_gate.py test/repo_conformance/test_private_api_boundaries.py` -> `7 passed`。
- py_compile：`PYTHONDONTWRITEBYTECODE=1 python3 -m py_compile kernel_gen/pipeline/npu_demo_lowering.py test/passes/pipeline/test_npu_demo_lowering.py kernel/matmul/inputs_dynamic_tile_dynamic.py kernel/matmul/inputs_static_tile_dynamic.py test/kernel/test_matmul_symbolic_memory_genkernel.py` -> exit 0。
- 格式 / 敏感目录门禁：`git diff --check && git diff --cached --check` -> exit 0；worktree 内 `.skills`、`expectation`、`agents/standard`、`AGENTS.md`、`TODO.md`、`DONE.md`、`plan/1.md` 的 status / unstaged diff / staged diff 均无输出。
Diff 反推审查：
- `kernel_gen/pipeline/npu_demo_lowering.py`：实际 builder 在 `MemoryPoolPass(rewrite=True, alignment=1024)` 后新增 `CommonSubexpressionElimination()`，再运行 `CanonicalizePass()`；没有新增 pipeline option、builder 参数或 registry 名称。
- `spec/pass/pipeline/npu_demo_lowering.md` 与 `test/passes/pipeline/test_npu_demo_lowering.py`：公开顺序、CSE 次数、dump marker 和阶段序号均同步为 `memory-pool -> cse -> canonicalize`；pytest 和 `rg` 核对均覆盖该顺序。
- matmul demo / dump：两个 demo 脚本和 kernel 测试只扩展 generated source 自检，兼容 `deslice(ctx, arg0, ...)`；公开生成逻辑未变。脚本执行和 dump marker 复核覆盖 present-bias `26-memory-pool -> 27-cse -> 28-canonicalize`。
- expectation 合同验收单列：授权 leaf 通过 `expectation.pass.pipeline.npu_demo_lowering`，且只锁定公开 pipeline 顺序；不计入普通 diff 反推测试。
减法审查：
- 新增逻辑替代旧相邻顺序：旧公开顺序为 `memory-pool -> canonicalize`，本轮改为 `memory-pool -> cse -> canonicalize`；没有删除 `canonicalize`，而是在其前增加一轮 CSE。
- 保留旧逻辑依据：保留 memory-pool、canonicalize、arch-parallelize、attach、outline、template-name-infer 后续链路；保持 multi-buffer、producer-consumer-analysis、pipeline option、make-ring / `DmaMakeRingOp` 合同不变。
- private callable：本轮普通 diff 改动的 `_assert_accumulator_source` 与 `_assert_source_uses_accumulator` 均为同文件自检 helper，未跨文件调用 private API，未调用其它 private callable；`test/repo_conformance/test_private_api_boundaries.py` 通过。
- expectation leaf 中 `_record_pipeline_pass` 为该 leaf 内部记录 helper，服务合同顺序断言；本轮没有新增目录级聚合或其它 expectation leaf。
自检：
- 已按 review 口径核对任务目标、执行记录、实际 diff、latest main、授权 expectation scope、合同验收、diff 反推测试、敏感目录、公开 API / option 和 private callable。
- 未发现其它 `expectation/` source leaf、`__main__.py`、pipeline 阶段、公开 option/API 或敏感目录越界。
- 因无剩余可执行返工项，本轮结论为通过；普通任务下一阶段可续接 `merge`。merge 阶段需特别处理主仓 ignored 合同 leaf，并排除 `expectation/pass/pipeline/__pycache__/`。
结论：review 通过。可使用 `-next -type merge` 进入合并阶段。

时间：2026-06-07 17:23 +0800
经办人：李白
任务：T-20260607-eb659882 / insert-cse-after-matmul-present-bias-memory-pool / merge
任务目标：合入已 review 通过的 `memory-pool -> cse -> canonicalize` pipeline 候选、任务记录和架构裁定 A 授权的唯一 ignored expectation leaf；排除 `expectation/pass/pipeline/__pycache__`、`__main__.py` 和其它 expectation leaf。
合入来源与范围：
- worktree：`/home/lfr/kernelcode_generate/wt-20260607-insert-cse-after-matmul-present-bias-memory-pool`。
- latest main：`HEAD=origin/main=merge-base=cf89a43112e3368bbefdd8df4e97c98758a6525c`，ahead / behind `0 0`。
- 普通 staged diff 初始 7 个路径：任务记录、`kernel_gen/pipeline/npu_demo_lowering.py`、`spec/pass/pipeline/npu_demo_lowering.md`、`test/passes/pipeline/test_npu_demo_lowering.py`、`kernel/matmul/inputs_dynamic_tile_dynamic.py`、`kernel/matmul/inputs_static_tile_dynamic.py`、`test/kernel/test_matmul_symbolic_memory_genkernel.py`。
- expectation 合同资产：按架构裁定 A，只纳入 `expectation/pass/pipeline/npu_demo_lowering.py`，`sha256=a61596ae6abf0c84a12e822c84f44a52530548a3a8fc387cea724bd10b3b632c`。
- 已从主仓 ignored leaf 同步到任务 worktree 同路径，并执行 `git add -f expectation/pass/pipeline/npu_demo_lowering.py`；未纳入 `expectation/pass/pipeline/__pycache__`、`expectation/pass/pipeline/__main__.py` 或其它 expectation leaf。
- 本任务不是计划级 merge，计划归档 / done_plan：不适用。
验证：
- `git fetch --prune origin`：退出码 0。
- `git diff --check && git diff --cached --check`：退出码 0。
- 合同验收：`PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260607-insert-cse-after-matmul-present-bias-memory-pool:/home/lfr/kernelcode_generate python3 -m expectation.pass.pipeline.npu_demo_lowering`：退出码 0，输出 `[pass-pipeline-npu_demo_lowering-order-1] pass: npu-demo-lowering order is stable.`。
- pipeline / matmul pytest：`PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/passes/pipeline/test_npu_demo_lowering.py test/kernel/test_matmul_symbolic_memory_genkernel.py -x`：`15 passed, 1 warning`。
- 组合 pytest：`PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/passes/test_registry.py test/tools/test_dsl_cost_run.py test/test_main_npu_demo_pipeline.py -x`：`71 passed, 1 warning`。
- 全量 pass：`PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/passes -x`：`589 passed, 1 warning`。
- KCE / private API：`PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/tools/test_kernel_code_error_static_gate.py test/repo_conformance/test_private_api_boundaries.py -x`：`7 passed`。
- py_compile：`PYTHONDONTWRITEBYTECODE=1 python3 -m py_compile kernel_gen/pipeline/npu_demo_lowering.py test/passes/pipeline/test_npu_demo_lowering.py kernel/matmul/inputs_dynamic_tile_dynamic.py kernel/matmul/inputs_static_tile_dynamic.py test/kernel/test_matmul_symbolic_memory_genkernel.py expectation/pass/pipeline/npu_demo_lowering.py`：退出码 0。
敏感目录与 expectation 范围核对：
- `git diff --cached --name-status -- expectation`：仅 `A expectation/pass/pipeline/npu_demo_lowering.py`。
- `sha256sum expectation/pass/pipeline/npu_demo_lowering.py`：`a61596ae6abf0c84a12e822c84f44a52530548a3a8fc387cea724bd10b3b632c`。
- `py_compile` 生成的 ignored `expectation/pass/pipeline/__pycache__` 已删除；`git status --short --ignored --untracked-files=all -- expectation/pass/pipeline` 只显示 staged leaf。
- `.skills`、`agents/standard`、根 `AGENTS.md`、`TODO.md`、`DONE.md`、`plan/1.md` 无 unstaged / cached diff。
冲突处理：
- 本轮 `HEAD=origin/main`，候选已在 latest main 上完成 review；未发生同步冲突。
剩余风险：
- 无剩余阻断。最终提交号在合并完成回报中说明，不再为提交号追加记录提交。
结论：merge 前 gate 通过，可提交并推送 `main`，随后执行 `-done`，并按最新流程清理已完成任务 worktree / branch；若清理条件不满足，在回报中列明原因。
