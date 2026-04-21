时间：2026-04-21 20:38 +0800
经办人：小李飞刀
任务：T-20260421-df8cc06e
任务目标：收口 nn_lowering pattern driver 与 registry/pass_manager 兼容，不改变现有 lowering 行为
改动：更新 kernel_gen/passes/lowering/nn_lowering/nn_lowering.py，新增 nn_lowering_patterns() 作为 pattern 集合入口，NnLoweringPass.apply(...) 直接通过 PatternRewriteWalker(GreedyRewritePatternApplier(nn_lowering_patterns(), dce_enabled=False)).rewrite_module(op) 执行；删除旧 _LowerNnSupportedOpPattern、_lower_op、_lower_block、_lower_func 与旧 _lower_module 手写遍历入口。更新 element_binary_lowering.py、dma_structured_lowering.py、matmul_img2col_lowering.py、reduce_softmax_lowering.py，补齐 family patterns() 注册函数，并保留当前 family helper 以维持行为；reduce_softmax 继续保留 direct nn.softmax 显式拒绝错误短语。更新 test/pass/nn_lowering/public_name.py，锁定 pattern 注册顺序与 apply driver 调用；更新 test/pass/test_pass_manager.py，锁定 registry 构造出的 lower-nn 仍可由 PassManager 执行。
验证：PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260421-nn-lowering-pattern-driver-s1 python3 -m py_compile kernel_gen/passes/lowering/nn_lowering/nn_lowering.py kernel_gen/passes/lowering/nn_lowering/element_binary_lowering.py kernel_gen/passes/lowering/nn_lowering/dma_structured_lowering.py kernel_gen/passes/lowering/nn_lowering/matmul_img2col_lowering.py kernel_gen/passes/lowering/nn_lowering/reduce_softmax_lowering.py test/pass/nn_lowering/public_name.py test/pass/test_pass_manager.py -> 通过；PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260421-nn-lowering-pattern-driver-s1 pytest -q test/pass/nn_lowering/public_name.py -> 4 passed；PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260421-nn-lowering-pattern-driver-s1 pytest -q test/pass/test_pass_manager.py -> 25 passed；PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260421-nn-lowering-pattern-driver-s1 pytest -q test/pass/test_pipeline_default_lowering.py test/pass/test_pipeline_npu_demo_lowering.py -> 4 passed；PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260421-nn-lowering-pattern-driver-s1 pytest -q test/pass/test_pass_registry.py -> 27 passed；PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260421-nn-lowering-pattern-driver-s1 pytest -q test/pass/nn_lowering -> 42 passed；当前 worktree 缺少 expectation/ 目录，单独使用 worktree PYTHONPATH 运行 python3 -m expectation.pass.lowing.nn_lowering 返回 ModuleNotFoundError；随后使用 PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260421-nn-lowering-pattern-driver-s1:/home/lfr/kernelcode_generate python3 -m expectation.pass.lowing.nn_lowering，验收资产来自主仓 expectation，kernel_gen 优先来自当前 worktree，命令通过并输出全部 CASE。
结论：当前 build 已完成，driver/registry/pass_manager 兼容面已收口，行为验证通过；下一步按流程创建 review 任务并通知管理员推进。

时间：2026-04-21 20:42:24 CST
经办人：提莫炖蘑菇
任务：T-20260421-df8cc06e
任务目标：复核 NnLoweringPass.apply 收口到 nn_lowering_patterns + PatternRewriteWalker，确认 registry/pass_manager 与 nn_lowering 验证结果。
改动：仅审查与复测，未修改 spec、实现、测试或 expectation。问题列表：未发现必须修改项。漏洞排查结果：输入校验绕过未发现新增风险，仍沿用各 family helper 校验；类型/形状绕过未发现新增风险，`test/pass/nn_lowering` 覆盖动态维度、类型与 shape 错误；边界越界未发现新增风险，reduce/broadcast 等边界用例仍通过；错误处理缺失未发现新增风险，direct `nn.softmax` 与 unknown `nn.*` 仍有显式拒绝路径；状态污染未发现新增风险，registry reset 与 PassManager 子集通过；资源释放问题不涉及新资源生命周期。
验证：
- 核对计划书 `/home/lfr/kernelcode_generate/ARCHITECTURE/plan/nn_lowering_op_pattern_refactor_green_plan.md`：S1 要求 `NnLoweringPass.apply(...)` 使用 `PatternRewriteWalker(GreedyRewritePatternApplier(nn_lowering_patterns(), dce_enabled=False)).rewrite_module(...)`，公开 pass 名、registry/pass_manager 兼容不变，`_RejectUnsupportedNnOpPattern` 位于末尾。
- `git -C /home/lfr/kernelcode_generate/wt-20260421-nn-lowering-pattern-driver-s1 status --short` -> 仅包含 `kernel_gen/passes/lowering/nn_lowering/*.py`、`test/pass/nn_lowering/public_name.py`、`test/pass/test_pass_manager.py` 与本任务记录改动，未见 expectation 改动。
- `rg -n "def _lower_op|def _lower_block|def _lower_func|_LowerNnSupportedOpPattern|_SUPPORTED_NN_OP_NAMES|_lower_with_current_op" . -S` -> 仅命中测试 helper、任务记录或新增测试断言，未命中 `kernel_gen/passes/lowering/nn_lowering` 主实现残留。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260421-nn-lowering-pattern-driver-s1 python3 -m py_compile kernel_gen/passes/lowering/nn_lowering/nn_lowering.py kernel_gen/passes/lowering/nn_lowering/element_binary_lowering.py kernel_gen/passes/lowering/nn_lowering/dma_structured_lowering.py kernel_gen/passes/lowering/nn_lowering/matmul_img2col_lowering.py kernel_gen/passes/lowering/nn_lowering/reduce_softmax_lowering.py test/pass/nn_lowering/public_name.py test/pass/test_pass_manager.py` -> 通过
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260421-nn-lowering-pattern-driver-s1 python3 - <<'PY' ... PY` -> `pass_name= lower-nn`，patterns 为 `['_LowerElementBinaryFamilyPattern', '_LowerSelectPattern', '_LowerCastPattern', '_LowerExpPattern', '_LowerDmaStructuredFamilyPattern', '_LowerMatmulImg2colFamilyPattern', '_LowerReduceSoftmaxFamilyPattern', '_RejectSoftmaxPattern', '_RejectUnsupportedNnOpPattern']`，`reject_last= True`，`old_supported_pattern= False`
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260421-nn-lowering-pattern-driver-s1 python3 - <<'PY' ... PY` -> `build_registered_pass("lower-nn")` 返回 `NnLoweringPass lower-nn`，`PassManager.run(ModuleOp([])) is module` 为 `True`
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260421-nn-lowering-pattern-driver-s1 pytest -q test/pass/nn_lowering/public_name.py test/pass/test_pass_manager.py test/pass/test_pipeline_default_lowering.py test/pass/test_pipeline_npu_demo_lowering.py test/pass/test_pass_registry.py` -> `60 passed, 27 warnings`
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260421-nn-lowering-pattern-driver-s1 pytest -q test/pass/nn_lowering` -> `42 passed, 60 warnings`
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260421-nn-lowering-pattern-driver-s1:/home/lfr/kernelcode_generate python3 -m expectation.pass.lowing.nn_lowering` -> 通过，输出覆盖 broadcast、cast、element binary、compare、exp、img2col、matmul、reduce、select、transpose CASE
- `git diff --check` -> 通过
结论：通过。NnLoweringPass 公开名仍为 `lower-nn`，apply 已收口到 `nn_lowering_patterns()` + `PatternRewriteWalker`，旧统一受支持 op pattern 与手写遍历主路径未在实现中残留；family patterns、softmax/unsupported 拒绝顺序、registry/pass_manager 与 nn_lowering 行为资产均与计划书 S1 对齐。下一步续到 merge。

时间：2026-04-21 20:43 CST
经办人：李白
任务：T-20260421-df8cc06e
任务目标：合并已通过 review 的 nn_lowering pattern driver 与 registry/pass_manager 兼容收口结果。
改动：合并前核对 worktree `/home/lfr/kernelcode_generate/wt-20260421-nn-lowering-pattern-driver-s1`，待纳入文件为 `kernel_gen/passes/lowering/nn_lowering/dma_structured_lowering.py`、`kernel_gen/passes/lowering/nn_lowering/element_binary_lowering.py`、`kernel_gen/passes/lowering/nn_lowering/matmul_img2col_lowering.py`、`kernel_gen/passes/lowering/nn_lowering/nn_lowering.py`、`kernel_gen/passes/lowering/nn_lowering/reduce_softmax_lowering.py`、`test/pass/nn_lowering/public_name.py`、`test/pass/test_pass_manager.py` 与本任务记录文件；未见 `expectation/` 改动。
验证：`git diff --name-status` -> 仅命中上述 7 个跟踪文件；`rg -n "T-20260421-df8cc06e|wt-20260421-nn-lowering-pattern-driver-s1|nn-lowering-pattern-driver-s1" TODO.md` -> 当前任务为 merge 且指派李白；`git status --short --ignored -- expectation` -> 无 `expectation/` 改动。
结论：合并前记录已写入，下一步在任务 worktree 执行 `timeout 60 git fetch origin` 并基于最新 `origin/main` 收口。

时间：2026-04-21 20:45 CST
经办人：李白
任务：T-20260421-df8cc06e
任务目标：完成 nn_lowering pattern driver 与 registry/pass_manager 兼容收口结果的 merge 提交前确认。
改动：已在任务 worktree 取回远端，并将合并提交重放到最新 `origin/main`；无冲突，范围仍为 nn_lowering 实现、pass 测试与本任务记录。
验证：`timeout 60 git fetch origin` -> 通过；`git rebase origin/main` -> 通过；`git status --short --branch` -> 工作区干净；`git diff --check origin/main..HEAD` -> 通过；未执行 pytest，原因：review 已完成复测，本轮无冲突且仅做 merge 收口。
结论：本次 merge 提交前确认通过，下一步将完成记录并入同一提交后推送远端主分支，推送成功后执行 `-done` 并回报管理员。
