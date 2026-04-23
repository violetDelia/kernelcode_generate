时间：2026-04-23 23:16 CST
经办人：金铲铲大作战
任务：T-20260423-73440e31
任务目标：按最新 S1 计划正文冻结 canonical public path、旧路径失败边界与消费者迁移矩阵，并把当前 S1 收口结果写回任务记录

执行前阅读记录：
- 已读 `TODO.md` 当前任务行，确认 worktree、计划书、记录文件与任务指派一致。
- 已读 `ARCHITECTURE/plan/pass_infrastructure_refactor_green_plan.md` 的 S1 正文、全局完成态/验收设计、消费者迁移矩阵和 `expectation` 单列口径。
- 已读当前 worktree 记录、`spec/pass/registry.md`、`spec/pass/pass_manager.md`、`test/pass/test_pass_registry.py`、`test/pass/test_pass_manager.py`、`kernel_gen/passes/{__init__.py,lowering/__init__.py,registry.py,pass_manager.py}`。

最小功能闭环：
- 把 `S1` 当前 surviving public path、old path failure boundary 和 consumer migration matrix 直接写进 `spec/pass/registry.md`、`spec/pass/pass_manager.md`。
- 用 `pytest` 机械锁定当前 registry/pass_manager caller 的 `importlib` 消费者矩阵，而不是只靠任务记录口头说明。
- 清掉 `test/pass/test_pass_registry.py` 中重复定义的 `test_build_registered_tile_reduce_pass`，避免 S1 证据链被 Python 名称覆盖机制静默污染。

改动：
- `spec/pass/registry.md`
  - 新增 `S1 冻结的公开路径与迁移矩阵` 小节。
  - 明确当前 canonical public path、当前仍存活的 compat / family caller、以及 `kernel_gen.passes.lowering.{registry,pass_manager,inline,attach_arch_information,decompass}` 的失败边界。
- `spec/pass/pass_manager.md`
  - 新增 `S1 冻结的调用边界` 小节。
  - 明确 `kernel_gen.passes.pass_manager`、`kernel_gen.passes.pipeline` 与当前仍允许的 lowering family import baseline。
- `test/pass/test_pass_registry.py`
  - 把重复的 `tile-reduce` 测试入口改成 `test_registry_surviving_public_paths_match_consumer_matrix`，直接锁定当前 surviving import matrix。
  - 新增 `test_registry_old_lowering_paths_fail_fast`，锁定当前已退场旧路径必须报 `ModuleNotFoundError`。
- `test/pass/test_pass_manager.py`
  - 新增 `test_pass_manager_surviving_import_matrix`，锁定 `PassManager` / pipeline / lowering family caller 的当前公开导入矩阵。
  - 新增 `test_pass_manager_old_lowering_paths_fail_fast`，锁定 `kernel_gen.passes.lowering.{pass_manager,registry}` 的失败边界。

验证：
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260423-pass-infra-s1:/home/lfr/kernelcode_generate pytest -q /home/lfr/kernelcode_generate/wt-20260423-pass-infra-s1/test/pass/test_pass_registry.py /home/lfr/kernelcode_generate/wt-20260423-pass-infra-s1/test/pass/test_pass_manager.py`
  - 结果：`59 passed, 1 warning`
- `python3 -m py_compile /home/lfr/kernelcode_generate/wt-20260423-pass-infra-s1/test/pass/test_pass_registry.py /home/lfr/kernelcode_generate/wt-20260423-pass-infra-s1/test/pass/test_pass_manager.py`
  - 结果：通过
- `git -C /home/lfr/kernelcode_generate/wt-20260423-pass-infra-s1 diff --check`
  - 结果：通过

Diff 反推自测：
- 本轮实际 diff 只落在 `spec/pass/{registry,pass_manager}.md` 与 `test/pass/{test_pass_registry.py,test_pass_manager.py}`，因此反推自测只跑这两份 pytest 资产，而没有扩跑其他 pass family。
- 反推依据：
  - `registry.md` / `test_pass_registry.py` 负责冻结 registry caller 的 canonical public path、old path failure boundary 与 compat consumer matrix。
  - `pass_manager.md` / `test_pass_manager.py` 负责冻结 pass manager / pipeline caller 的 canonical public path 与旧路径失败边界。

合同验收（如适用）：
- `expectation` 仅作为只读合同验收资产单列。
- 本轮未执行 `expectation`，也未把 `expectation` 当作对应测试替代。

真实自检：
- 接口边界：本轮没有提前推进 `S2+` 的 compat 退场，只冻结 `S1` 当前真实存活/失败基线，避免 spec/test 抢跑实现阶段。
- 兼容性：对当前仍存活的 compat 路径明确标成“继续可导入但不承诺永久保留”，和计划正文一致，没有把未来失败边界误写成当前事实。
- 可维护性：清掉重复的 `test_build_registered_tile_reduce_pass` 后，registry 证据链不再依赖 Python 后定义覆盖前定义的隐式行为。
- 测试有效性：新增断言直接走 `importlib.import_module(...)`，能机械判断“哪个路径继续活、哪个路径该失败”，比仅看 `__all__` 或口头记录更稳。
- 一线可改进点：当前 pytest 仍有 `xdsl` 上游 `irdl_options list` 的 `DeprecationWarning`，但它不来自本轮仓内 diff，不在本切片处理边界内。

结论：
- `S1` 当前目标已按计划正文收口：canonical public path、旧路径失败边界、消费者迁移矩阵都已在 spec/test 中机械可判。
- 当前 diff 已具备回流 review 的条件。

时间：2026-04-23 23:47 CST
经办人：不要啊教练
任务：T-20260423-73440e31
任务目标：复核 S1 canonical public path、旧路径失败边界与消费者迁移矩阵冻结结果，并按实际 diff 给出审查结论
执行前阅读记录：已读 `TODO.md` 当前任务行、`ARCHITECTURE/plan/pass_infrastructure_refactor_green_plan.md` 的 S1 正文与全局完成态/验收设计、当前 worktree 任务记录、`spec/pass/{registry,pass_manager}.md`、`test/pass/{test_pass_registry.py,test_pass_manager.py}` 与相关实现入口 `kernel_gen/passes/{registry.py,pass_manager.py,pipeline/__init__.py}`。
改动：
- 真实审查：逐项核对 `spec/pass/registry.md`、`spec/pass/pass_manager.md` 新增 S1 文字与 `test/pass/test_pass_registry.py`、`test/pass/test_pass_manager.py` 的新增断言，确认 build 记录已写清 `执行前阅读记录`、`最小功能闭环`、`Diff 反推自测` 与 `真实自检`。
- 问题 1：`test/pass/test_pass_registry.py:550` 与 `test/pass/test_pass_registry.py:572` 复用了同一个测试编号 `TC-REGISTRY-007J`。这会让 S1 迁移矩阵证据链在任务记录、失败截图与后续引用里出现歧义，和本阶段“冻结矩阵、机械可判”的目标冲突。
- 问题 2：`test/pass/test_pass_registry.py:312-348` 的 `test_registry_surviving_public_paths_match_consumer_matrix` 只做 `hasattr(...)` 检查，没有把 canonical public path 的导出对象身份锁死。当前断言即使导出被错误 alias、错误 re-export 或对象来源漂移，只要属性名还在就会继续通过，无法机械证明消费者迁移矩阵真的保持不变。
- 问题 3：`spec/pass/pass_manager.md:48` 明确写了 `default / npu-demo pipeline builder` 的 canonical public path 都固定为 `kernel_gen.passes.pipeline`，但 `test/pass/test_pass_manager.py:243-258` 只显式锁定了 `build_default_lowering_pipeline`，没有覆盖同一公开入口上的 `build_npu_demo_lowering_pipeline`。当前 S1 针对 pipeline builder 的公开路径冻结仍缺一条直接断言。
- 可改进点：先把重复测试编号去重，再把 surviving matrix 断言从“属性存在”收紧到“导出对象身份/来源一致”，并为 `build_npu_demo_lowering_pipeline` 补一条与 `build_default_lowering_pipeline` 同等级的 canonical path 断言。
验证：
- `python3 -m pytest -q /home/lfr/kernelcode_generate/wt-20260423-pass-infra-s1/test/pass/test_pass_registry.py /home/lfr/kernelcode_generate/wt-20260423-pass-infra-s1/test/pass/test_pass_manager.py`
  - 结果：`59 passed, 1 warning`
- `python3 -m py_compile /home/lfr/kernelcode_generate/wt-20260423-pass-infra-s1/test/pass/test_pass_registry.py /home/lfr/kernelcode_generate/wt-20260423-pass-infra-s1/test/pass/test_pass_manager.py`
  - 结果：通过
- `git -C /home/lfr/kernelcode_generate/wt-20260423-pass-infra-s1 diff --check`
  - 结果：通过
Diff 反推审查：
- 被审 diff 文件：`spec/pass/registry.md`、`spec/pass/pass_manager.md`、`test/pass/test_pass_registry.py`、`test/pass/test_pass_manager.py`。
- 反推依据：S1 计划正文把验收资产限定为 `test/pass/test_pass_registry.py` 与 `test/pass/test_pass_manager.py`，目标是冻结 surviving public path、old path failure boundary 与 `importlib` 消费者矩阵；因此审查复跑上述两份 pytest，并额外核对公开符号 `build_npu_demo_lowering_pipeline` 的现状是否被 S1 用例覆盖。
- 复核证据：`test/pass/test_pass_registry.py:312-348` 当前仅以 `hasattr` 锁定 surviving path；`test/pass/test_pass_registry.py:550` 与 `:572` 的测试编号重复；`test/pass/test_pass_manager.py:252` 只锁定 `build_default_lowering_pipeline`，未覆盖 `build_npu_demo_lowering_pipeline`。
- 未覆盖项：本轮未另跑其他 pass family pytest，因为实际 diff 未触及对应测试资产。
合同验收（如适用）：
- `expectation` 只作为合同验收资产单列。
- 本轮未执行 `expectation`，也未把 `expectation` 计入 diff 反推测试。
自检：已逐行审查本轮改动文件并结合 S1 计划正文核对；执行前提、特殊情况、兼容边界、测试有效性、可维护性和可追踪性已检查；输入校验绕过、类型/形状绕过、边界越界、错误处理缺失、状态污染、资源释放六类风险在本次 spec/test 冻结切片内未发现新增实现问题，但发现 3 个可执行改进点，按当前审查口径不能给通过。
结论：需修改。当前 S1 文本方向正确、复测也通过，但 canonical public path 与迁移矩阵的机械证据还不够严，且测试编号存在冲突；建议回退 `build`，修正上述问题后再复审。

时间：2026-04-24 00:02 CST
经办人：金铲铲大作战
任务：T-20260423-73440e31
任务目标：修复 S1 审查问题，去重重复测试编号，收紧 canonical public path / consumer matrix 断言，并补齐 npu-demo pipeline builder 的公开路径覆盖

执行前阅读记录：
- 已重新读取 `TODO.md` 当前任务行，确认本轮已从 `review` 回退到 `build`，目标聚焦在审查指出的 3 个问题。
- 已重读 `ARCHITECTURE/plan/pass_infrastructure_refactor_green_plan.md` 的 S1 正文、全局完成态/验收设计、消费者迁移矩阵和 `expectation` 单列边界。
- 已复核前序 build 记录与 review 记录，确认本轮只需要修正 `test/pass/{test_pass_registry.py,test_pass_manager.py}` 的证据链，不扩大到其他 pass family。

最小功能闭环：
- 去掉 `test/pass/test_pass_registry.py` 里重复的测试编号，保证 S1 证据链引用稳定。
- 把 registry / pass_manager 的 surviving public path 断言从“属性存在”收紧为“导出对象身份与来源一致”。
- 给 `build_npu_demo_lowering_pipeline` 增加与 `build_default_lowering_pipeline` 同等级的 canonical public path 覆盖。

改动：
- `test/pass/test_pass_registry.py`
  - `test_registry_surviving_public_paths_match_consumer_matrix` 由 `hasattr(...)` 改为 `getattr(...) is expected_obj`，直接锁定对象身份。
  - 把 `npu-demo-lowering` registry pipeline 用例的编号从重复的 `TC-REGISTRY-007J` 去重为 `TC-REGISTRY-007K`。
- `test/pass/test_pass_manager.py`
  - `test_pass_manager_surviving_import_matrix` 新增 `kernel_gen.passes.pipeline.build_npu_demo_lowering_pipeline` 与 `kernel_gen.passes.pipeline.npu_demo_lowering.build_npu_demo_lowering_pipeline` 的对象身份断言。
  - lowering family 断言也同步改为对象身份一致，而不再只看 `__name__` / `__module__` 文本。

验证：
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260423-pass-infra-s1:/home/lfr/kernelcode_generate pytest -q /home/lfr/kernelcode_generate/wt-20260423-pass-infra-s1/test/pass/test_pass_registry.py /home/lfr/kernelcode_generate/wt-20260423-pass-infra-s1/test/pass/test_pass_manager.py`
  - 结果：`59 passed, 1 warning`
- `python3 -m py_compile /home/lfr/kernelcode_generate/wt-20260423-pass-infra-s1/test/pass/test_pass_registry.py /home/lfr/kernelcode_generate/wt-20260423-pass-infra-s1/test/pass/test_pass_manager.py`
  - 结果：通过
- `git -C /home/lfr/kernelcode_generate/wt-20260423-pass-infra-s1 diff --check`
  - 结果：通过

Diff 反推自测：
- 本轮实际 diff 只新增修改了 `test/pass/test_pass_registry.py` 与 `test/pass/test_pass_manager.py`，因此反推自测仍只跑这两份 pytest。
- 反推依据：
  - `test_pass_registry.py` 承接 review 指到的“重复测试编号”和“consumer matrix 断言过宽”两项修复。
  - `test_pass_manager.py` 承接 review 指到的 “`build_npu_demo_lowering_pipeline` 公开路径覆盖缺失” 修复。

合同验收（如适用）：
- `expectation` 仅作为只读合同验收资产单列。
- 本轮未执行 `expectation`，也未把 `expectation` 当作对应测试替代。

真实自检：
- 接口边界：本轮没有继续改 `spec` 或产品实现，只收 review 明确指出的 S1 证据链问题。
- 兼容性：对象身份断言比 `hasattr` / `__name__` / `__module__` 更严格，能直接发现错误 alias、错误 re-export 或 builder 来源漂移。
- 可维护性：测试编号去重后，S1 任务记录、失败截图和后续引用不会再出现同编号歧义。
- 测试有效性：`build_npu_demo_lowering_pipeline` 现在和 `build_default_lowering_pipeline` 一样被纳入 public path 冻结断言，pipeline builder 证据链闭合。
- 一线可改进点：当前只剩 `xdsl` 上游 `irdl_options list` 的 `DeprecationWarning`，不是本轮仓内 diff 引入的问题。

结论：
- review 指出的 3 个问题已全部修复。
- 当前 diff 已具备再次回流 `review` 的条件。

时间：2026-04-24 00:37 +0800
经办人：提莫炖蘑菇
任务：T-20260423-73440e31（review）
任务目标：复核 S1 修复后的 canonical public path、旧路径失败边界、消费者迁移矩阵与 npu-demo pipeline builder 公开路径覆盖是否已经按计划书收口。
执行前阅读记录：
- 已重读 [`TODO.md`](../../../../../../../TODO.md) 中 `T-20260423-73440e31` 当前 `review` 任务行。
- 已重读 [`ARCHITECTURE/plan/pass_infrastructure_refactor_green_plan.md`](../../../../../../../ARCHITECTURE/plan/pass_infrastructure_refactor_green_plan.md) 的 S1 正文、全局完成态 / 验收设计和消费者迁移矩阵。
- 已重读本记录中 23:16 的 build 记录、23:47 的上轮 review 退回项和 00:02 的 build 修复记录，确认本轮只复核该 3 个问题是否全部闭合。
真实审查：
- 已核对 `spec/pass/registry.md`、`spec/pass/pass_manager.md`、`test/pass/test_pass_registry.py`、`test/pass/test_pass_manager.py` 的当前 diff，确认重复测试编号问题已修正，`build_npu_demo_lowering_pipeline` 也已经补进 surviving import matrix 断言。
- 已核对 build 记录包含 `执行前阅读记录`、`最小功能闭环`、`Diff 反推自测` 和 `真实自检`，记录完整性满足 review 要求。
- 但当前 `build_default_lowering_pipeline` 的 canonical public path 证据仍不够严：[`test/pass/test_pass_manager.py`](../../../../../../../test/pass/test_pass_manager.py:253) 只比较 `pipeline_module.build_default_lowering_pipeline is build_default_lowering_pipeline`，两边都来自同一个 `kernel_gen.passes.pipeline` 包导入，属于自证式断言，不能机械证明 package export 与 `kernel_gen.passes.pipeline.default_lowering.build_default_lowering_pipeline` 的对象身份一致。
Diff 反推审查：
- 被审 diff 文件：[`spec/pass/registry.md`](../../../../../../../spec/pass/registry.md)、[`spec/pass/pass_manager.md`](../../../../../../../spec/pass/pass_manager.md)、[`test/pass/test_pass_registry.py`](../../../../../../../test/pass/test_pass_registry.py)、[`test/pass/test_pass_manager.py`](../../../../../../../test/pass/test_pass_manager.py)。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260423-pass-infra-s1:/home/lfr/kernelcode_generate pytest -q /home/lfr/kernelcode_generate/wt-20260423-pass-infra-s1/test/pass/test_pass_registry.py /home/lfr/kernelcode_generate/wt-20260423-pass-infra-s1/test/pass/test_pass_manager.py -ra` -> `59 passed, 1 warning`
- `python3 -m py_compile /home/lfr/kernelcode_generate/wt-20260423-pass-infra-s1/test/pass/test_pass_registry.py /home/lfr/kernelcode_generate/wt-20260423-pass-infra-s1/test/pass/test_pass_manager.py && git -C /home/lfr/kernelcode_generate/wt-20260423-pass-infra-s1 diff --check` -> 通过
- 额外核对：
  - [`spec/pass/pass_manager.md`](../../../../../../../spec/pass/pass_manager.md:48) 明确写的是 “default / npu-demo pipeline builder 的 canonical public path 固定为 `kernel_gen.passes.pipeline`”
  - [`test/pass/test_pass_manager.py`](../../../../../../../test/pass/test_pass_manager.py:253) 目前只对 `build_default_lowering_pipeline` 做同模块变量比较
  - `python3 - <<'PY' ...` 已确认 `kernel_gen.passes.pipeline.build_default_lowering_pipeline is kernel_gen.passes.pipeline.default_lowering.build_default_lowering_pipeline` 当前为 `True`，但这条事实尚未写进 pytest 断言
- 未覆盖项：本轮未另跑其他 pass family pytest，因为实际 diff 只落在 `spec/pass/{registry,pass_manager}.md` 与 `test/pass/{test_pass_registry.py,test_pass_manager.py}`。
合同验收：
- `expectation` 只作为合同验收资产单列。
- 本轮未执行 `expectation`，也未把 `expectation` 计入 diff 反推测试。
可改进点：
- `P2` 文件/接口：[`test/pass/test_pass_manager.py`](../../../../../../../test/pass/test_pass_manager.py:253)
  现象：`build_default_lowering_pipeline` 的 surviving import matrix 断言仍是同模块变量自比较，没有像 `build_npu_demo_lowering_pipeline` 一样直接对比 package export 与 submodule export。
  风险：S1 的目标是把 canonical public path 写成机械可判证据；当前默认 builder 仍缺一条与 `kernel_gen.passes.pipeline.default_lowering.build_default_lowering_pipeline` 的直接对象身份断言，后续若 package export 意外换成别名或错误 re-export，现有测试未必能第一时间报错。
  建议：在 [`test/pass/test_pass_manager.py`](../../../../../../../test/pass/test_pass_manager.py) 中补一条与 `npu_demo` builder 同等级的断言，直接比较 `kernel_gen.passes.pipeline.build_default_lowering_pipeline` 和 `kernel_gen.passes.pipeline.default_lowering.build_default_lowering_pipeline` 的对象身份。
自检：
- 已逐项对照上轮 review 的 3 个问题复核，而不是只看本轮 build 摘要。
- 已复跑本轮 diff 对应 pytest 与本地检查命令，并补做 `pipeline` 包 / 子模块对象身份现状核对。
- 当前仍能明确指出一线可执行问题；按审查口径，本轮不能给 `通过`。
结论：
- 结论：`需修改`
- 下一步：退回 `build`。给 `build_default_lowering_pipeline` 补一条 package export 对 submodule export 的直接对象身份断言后，再回到 `review`。

时间：2026-04-24 00:14 +0800
经办人：jcc你莫辜负
任务：T-20260423-73440e31（build）
任务目标：按最新 review 退回口径，为 `build_default_lowering_pipeline` 补 package export 对 submodule export 的直接对象身份断言，并把本轮真实自检与 Diff 反推自测写回记录。
执行前阅读记录：
- 已重读 [`TODO.md`](/home/lfr/kernelcode_generate/TODO.md:5) 中 `T-20260423-73440e31` 当前任务行，确认 worktree、计划书和记录文件与当前指派一致。
- 已重读 [`ARCHITECTURE/plan/pass_infrastructure_refactor_green_plan.md`](/home/lfr/kernelcode_generate/ARCHITECTURE/plan/pass_infrastructure_refactor_green_plan.md) 的 S1 正文、全局完成态 / 验收设计与消费者迁移矩阵，确认本轮目标仍是冻结 canonical public path 的机械证据。
- 已重读本记录中 00:02 的 build 修复记录和 00:37 的 review 退回记录，确认本轮只收一个问题：`build_default_lowering_pipeline` 仍缺 package export 对 `kernel_gen.passes.pipeline.default_lowering` submodule export 的直接对象身份断言。
最小功能闭环：
- 让 `test_pass_manager_surviving_import_matrix` 同时对默认 builder 和 `npu_demo` builder 使用同等级的“package export is submodule export”对象身份断言。
- 保持本轮只改 `test/pass/test_pass_manager.py`，不再扩到 `spec`、实现或其他 pass family。
改动：
- [`test/pass/test_pass_manager.py`](/home/lfr/kernelcode_generate/wt-20260423-pass-infra-s1/test/pass/test_pass_manager.py)
  - 在 `test_pass_manager_surviving_import_matrix` 中新增 `default_lowering_pipeline_module = importlib.import_module("kernel_gen.passes.pipeline.default_lowering")`。
  - 把默认 builder 断言从 `pipeline_module.build_default_lowering_pipeline is build_default_lowering_pipeline` 改成 `pipeline_module.build_default_lowering_pipeline is default_lowering_pipeline_module.build_default_lowering_pipeline`，使默认 builder 和 `build_npu_demo_lowering_pipeline` 一样直接锁定 package export 对 submodule export 的对象身份。
验证：
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260423-pass-infra-s1:/home/lfr/kernelcode_generate pytest -q /home/lfr/kernelcode_generate/wt-20260423-pass-infra-s1/test/pass/test_pass_registry.py /home/lfr/kernelcode_generate/wt-20260423-pass-infra-s1/test/pass/test_pass_manager.py` -> `59 passed, 1 warning`
- `python3 -m py_compile /home/lfr/kernelcode_generate/wt-20260423-pass-infra-s1/test/pass/test_pass_registry.py /home/lfr/kernelcode_generate/wt-20260423-pass-infra-s1/test/pass/test_pass_manager.py` -> 通过
- `git -C /home/lfr/kernelcode_generate/wt-20260423-pass-infra-s1 diff --check` -> 通过
Diff 反推自测：
- 本轮新增 diff 只落在 [`test/pass/test_pass_manager.py`](/home/lfr/kernelcode_generate/wt-20260423-pass-infra-s1/test/pass/test_pass_manager.py)，但当前任务工作树的 S1 证据链仍由 `test_pass_registry.py` 与 `test_pass_manager.py` 共同承接，所以按实际 diff 反推继续复跑这两份 pytest 资产，不扩跑其他 pass family。
- 反推依据：
  - `test_pass_manager.py` 直接承接 review 指到的默认 builder direct identity 断言缺失。
  - `test_pass_registry.py` 仍是同一 S1 canonical public path / consumer matrix 证据链的并行资产，和本轮 `test_pass_manager.py` 一起构成当前任务 diff 的最小回归面。
合同验收（如适用）：
- `expectation` 只作为合同验收资产单列。
- 本轮未执行 `expectation`，也未把 `expectation` 计入 Diff 反推自测。
自检：
- 范围控制：本轮只修 review 明确指出的最后一条缺口，没有越界改 `spec`、实现或其他角色文件。
- 测试有效性：新的默认 builder 断言不再是包内自比较，而是直接比较 `kernel_gen.passes.pipeline` 与 `kernel_gen.passes.pipeline.default_lowering` 的导出对象身份，能机械捕获错误 alias / 错误 re-export。
- 完整性：默认 builder 与 `npu_demo` builder 现在都采用同等级 direct identity 断言，S1 对 pipeline builder canonical public path 的证据链已对齐。
- 可改进点复核：我重新核对了本轮修改点周边，没有再看到同级别的一线缺口；当前剩余 `xdsl` `DeprecationWarning` 不是本轮仓内 diff 引入，不在本切片处理边界内。
结论：
- 最新 review 指出的缺口已补齐，当前 S1 diff 已具备再次回流 `review` 的条件。

---
任务：T-20260423-73440e31（review）
任务目标：复核 `build_default_lowering_pipeline` 已补 package export 对 `kernel_gen.passes.pipeline.default_lowering` submodule export 的直接对象身份断言，并确认 S1 canonical public path 证据链是否已经闭合。
执行前阅读记录：
- 已重读 [`TODO.md`](/home/lfr/kernelcode_generate/TODO.md:5) 中 `T-20260423-73440e31` 当前任务行。
- 已重读 [`ARCHITECTURE/plan/pass_infrastructure_refactor_green_plan.md`](/home/lfr/kernelcode_generate/ARCHITECTURE/plan/pass_infrastructure_refactor_green_plan.md) 的 S1 正文、全局完成态 / 验收设计与消费者迁移矩阵要求。
- 已重读本 worktree 任务记录最新 build / review 条目，以及 [`spec/pass/pass_manager.md`](/home/lfr/kernelcode_generate/wt-20260423-pass-infra-s1/spec/pass/pass_manager.md)、[`spec/pass/registry.md`](/home/lfr/kernelcode_generate/wt-20260423-pass-infra-s1/spec/pass/registry.md)、[`test/pass/test_pass_manager.py`](/home/lfr/kernelcode_generate/wt-20260423-pass-infra-s1/test/pass/test_pass_manager.py)、[`test/pass/test_pass_registry.py`](/home/lfr/kernelcode_generate/wt-20260423-pass-infra-s1/test/pass/test_pass_registry.py)。
真实审查：
- 这轮 build 已把 [`test/pass/test_pass_manager.py:256`](/home/lfr/kernelcode_generate/wt-20260423-pass-infra-s1/test/pass/test_pass_manager.py:256) 到 [`:263`](/home/lfr/kernelcode_generate/wt-20260423-pass-infra-s1/test/pass/test_pass_manager.py:263) 的默认 / `npu_demo` builder 都收成 package export 对 submodule export 的直接对象身份断言，这一条比上一轮更准确。
- 但同一个 `test_pass_manager_surviving_import_matrix` 里，[`test/pass/test_pass_manager.py:270`](/home/lfr/kernelcode_generate/wt-20260423-pass-infra-s1/test/pass/test_pass_manager.py:270) 到 [`:281`](/home/lfr/kernelcode_generate/wt-20260423-pass-infra-s1/test/pass/test_pass_manager.py:281) 的 `dma_memory_hierarchy`、`tile_analysis`、`tile_elewise`、`tile_reduce` 断言仍是“同一个 submodule 再 `import_module(...)` 一次后做对象自比较”。
- 这些断言不会比单纯 `importlib.import_module(...)` 成功多提供任何新证据；若要证明 S1 当前消费者矩阵可机械判断，要么只把这些路径作为“导入成功”基线写清，要么改成和上面的 builder / `lowering_module` 一样，直接比较两个不同公开入口之间的对象身份。
问题清单：
- 问题 1：[`test/pass/test_pass_manager.py:270`](/home/lfr/kernelcode_generate/wt-20260423-pass-infra-s1/test/pass/test_pass_manager.py:270) 到 [`:281`](/home/lfr/kernelcode_generate/wt-20260423-pass-infra-s1/test/pass/test_pass_manager.py:281)
  - 现象：`dma_memory_hierarchy`、`tile_analysis`、`tile_elewise`、`tile_reduce` 四条 surviving import matrix 断言仍是 submodule 对同一 submodule 的重复导入自比较。
  - 风险：这几条断言不能新增 S1 消费者矩阵证据，后续即使断言语义被误解为“验证不同入口一致”，实际也只是在验证 Python 模块缓存。
  - 建议：把这四条改成更直接的“导入成功 + 目标符号存在”基线，或者改成两个不同入口之间的对象身份比较；不要继续保留同模块自比较。
可改进点：
- 当前 `build_default_lowering_pipeline` 的补强已经到位，但 `test_pass_manager_surviving_import_matrix` 还混有 4 条无增量证据的自比较断言，S1 证据链还不够整洁。
Diff 反推审查：
- 被审 diff 文件：[`spec/pass/pass_manager.md`](/home/lfr/kernelcode_generate/wt-20260423-pass-infra-s1/spec/pass/pass_manager.md)、[`spec/pass/registry.md`](/home/lfr/kernelcode_generate/wt-20260423-pass-infra-s1/spec/pass/registry.md)、[`test/pass/test_pass_manager.py`](/home/lfr/kernelcode_generate/wt-20260423-pass-infra-s1/test/pass/test_pass_manager.py)、[`test/pass/test_pass_registry.py`](/home/lfr/kernelcode_generate/wt-20260423-pass-infra-s1/test/pass/test_pass_registry.py)。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260423-pass-infra-s1:/home/lfr/kernelcode_generate pytest -q /home/lfr/kernelcode_generate/wt-20260423-pass-infra-s1/test/pass/test_pass_manager.py /home/lfr/kernelcode_generate/wt-20260423-pass-infra-s1/test/pass/test_pass_registry.py`
  结果：`59 passed, 1 warning`
- `git -C /home/lfr/kernelcode_generate/wt-20260423-pass-infra-s1 diff --check`
  结果：通过
- 复核证据：[`test/pass/test_pass_manager.py:256`](/home/lfr/kernelcode_generate/wt-20260423-pass-infra-s1/test/pass/test_pass_manager.py:256) 到 [`:263`](/home/lfr/kernelcode_generate/wt-20260423-pass-infra-s1/test/pass/test_pass_manager.py:263) 已补默认 builder 与 `npu_demo` builder 的 direct identity；[`test/pass/test_pass_manager.py:270`](/home/lfr/kernelcode_generate/wt-20260423-pass-infra-s1/test/pass/test_pass_manager.py:270) 到 [`:281`](/home/lfr/kernelcode_generate/wt-20260423-pass-infra-s1/test/pass/test_pass_manager.py:281) 仍是同模块自比较。
合同验收（单列，不计入 Diff 反推审查）：
- 本轮未执行 `expectation`；按计划书与仓库规则，`expectation` 继续只作合同验收资产单列。
自检：
- 已检查 build 记录包含 `执行前阅读记录`、`最小功能闭环`、`Diff 反推自测` 与 `自检`。
- 已复跑当前 diff 对应 pytest，并复核新增断言是否真的增强 S1 证据；发现 1 条新的可执行问题，因此不能给通过。
结论：
- 需修改。`build_default_lowering_pipeline` 的 direct identity 断言已补齐，但 `test_pass_manager_surviving_import_matrix` 仍保留 4 条无增量证据的同模块自比较；建议回到 `build`，把这些断言改成真正描述消费者矩阵的基线后再复审。

时间：2026-04-24 00:19 +0800
经办人：jcc你莫辜负
任务：T-20260423-73440e31（build）
任务目标：把 `test_pass_manager_surviving_import_matrix` 中剩余 4 条同模块自比较断言改成真正描述 S1 消费者矩阵的基线，再回流 `review`。
执行前阅读记录：
- 已重读 [`TODO.md`](/home/lfr/kernelcode_generate/TODO.md:5) 中 `T-20260423-73440e31` 当前任务行，确认本轮仍在 [`wt-20260423-pass-infra-s1`](/home/lfr/kernelcode_generate/wt-20260423-pass-infra-s1) 处理 `build`。
- 已重读 [`ARCHITECTURE/plan/pass_infrastructure_refactor_green_plan.md`](/home/lfr/kernelcode_generate/ARCHITECTURE/plan/pass_infrastructure_refactor_green_plan.md) 的 S1 正文、全局完成态 / 验收设计与 surviving import matrix 要求。
- 已重读本记录最新 `review` 退回项，确认本轮只收 `test_pass_manager_surviving_import_matrix` 中 `dma_memory_hierarchy`、`tile_analysis`、`tile_elewise`、`tile_reduce` 4 条同模块自比较断言，不扩到 `spec`、实现或其他 pass family。
最小功能闭环：
- 把这 4 条断言从“submodule 再 import 自己”的模块缓存式自比较，改成 `kernel_gen.passes.lowering` package export 对对应 submodule export 的对象身份断言。
- 保证 `test_pass_manager_surviving_import_matrix` 内默认 builder、`npu_demo` builder 和 lowering family 都用真正能描述消费者矩阵的基线。
改动：
- [`test/pass/test_pass_manager.py`](/home/lfr/kernelcode_generate/wt-20260423-pass-infra-s1/test/pass/test_pass_manager.py)
  - 将 `LowerDmaMemoryHierarchyPass`、`TileAnalysisPass`、`TileElewisePass`、`TileReducePass` 4 条断言改为 `lowering_module.<Pass> is <submodule>.<Pass>`。
  - 删除这 4 条通过重复 `importlib.import_module(...)` 对同一 submodule 做对象自比较的旧写法，使 surviving import matrix 真正表达“package export 与 submodule export 一致”。
验证：
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260423-pass-infra-s1:/home/lfr/kernelcode_generate pytest -q /home/lfr/kernelcode_generate/wt-20260423-pass-infra-s1/test/pass/test_pass_manager.py` -> `26 passed, 1 warning`
- `python3 -m py_compile /home/lfr/kernelcode_generate/wt-20260423-pass-infra-s1/test/pass/test_pass_manager.py` -> 通过
- `git -C /home/lfr/kernelcode_generate/wt-20260423-pass-infra-s1 diff --check` -> 通过
Diff 反推自测：
- 本轮实际 diff 只落在 [`test/pass/test_pass_manager.py`](/home/lfr/kernelcode_generate/wt-20260423-pass-infra-s1/test/pass/test_pass_manager.py)，因此按实际 diff 反推只跑该文件对应 pytest，不再把 `test_pass_registry.py` 作为本轮自测主体。
- 反推依据：最新 `review` 退回点只指向 `test_pass_manager_surviving_import_matrix` 中 4 条同模块自比较断言，当前风险面完全落在 `test_pass_manager.py`。
合同验收（如适用）：
- `expectation` 只作为合同验收资产单列。
- 本轮未执行 `expectation`，也未把 `expectation` 计入 Diff 反推自测。
自检：
- 范围控制：本轮只修改 `test_pass_manager.py` 里 review 明确指出的 4 条断言，没有越权改 `spec`、实现或其他角色文件。
- 测试有效性：4 条断言现已从“验证 Python 模块缓存”改成“验证 lowering package export 与 submodule export 的对象身份一致”，确实能为 S1 消费者矩阵提供新增证据。
- 完整性：`build_default_lowering_pipeline`、`build_npu_demo_lowering_pipeline`、`LowerDmaMemoryHierarchyPass`、`TileAnalysisPass`、`TileElewisePass`、`TileReducePass` 现在都采用统一的 package export / submodule export 基线，没有再留同级别的自比较断言。
- 可改进点复核：我重新检查了 `test_pass_manager_surviving_import_matrix` 当前断言组，没有再看到同类型的一线缺口；剩余 `xdsl` `DeprecationWarning` 不是本轮仓内 diff 引入的问题。
结论：
- 最新 `review` 指出的 4 条同模块自比较断言已全部收口，当前 S1 `pass_manager` surviving import matrix 已具备再次回流 `review` 的条件。

时间：2026-04-24 15:20 +0800
经办人：提莫炖蘑菇
任务：T-20260423-73440e31（review）
任务目标：复核 `pass_manager` surviving import matrix 中 4 条 lowering package export 对 submodule export 的对象身份断言已补齐，并确认 S1 `canonical public path` 的当前证据已经闭合。
执行前阅读记录：
- 已重读 [`TODO.md`](/home/lfr/kernelcode_generate/TODO.md:5) 中 `T-20260423-73440e31` 当前任务行，确认本轮仍在 [`wt-20260423-pass-infra-s1`](/home/lfr/kernelcode_generate/wt-20260423-pass-infra-s1) 做 `review`。
- 已重读 [`ARCHITECTURE/plan/pass_infrastructure_refactor_green_plan.md`](/home/lfr/kernelcode_generate/ARCHITECTURE/plan/pass_infrastructure_refactor_green_plan.md) 的 S1 正文、全局完成态 / 验收设计与 surviving import matrix 相关说明。
- 已重读本记录前序 `build / review` 条目，确认本轮只收上一轮退回的最后一项：`test_pass_manager_surviving_import_matrix` 中 4 条 lowering family 断言是否已改成真正的 package export 对 submodule export 对比。
真实审查：
- 我复查了 [`test/pass/test_pass_manager.py`](/home/lfr/kernelcode_generate/wt-20260423-pass-infra-s1/test/pass/test_pass_manager.py) 当前 surviving import matrix 段落，`build_default_lowering_pipeline`、`build_npu_demo_lowering_pipeline`、`LowerDmaMemoryHierarchyPass`、`TileAnalysisPass`、`TileElewisePass`、`TileReducePass` 现在都使用 package export 对 submodule export 的对象身份断言，不再保留同模块重复导入自比较。
- 我同步核对了 [`spec/pass/pass_manager.md`](/home/lfr/kernelcode_generate/wt-20260423-pass-infra-s1/spec/pass/pass_manager.md) 与 [`spec/pass/registry.md`](/home/lfr/kernelcode_generate/wt-20260423-pass-infra-s1/spec/pass/registry.md)，当前公开路径说明与 pytest 断言口径一致，没有再出现一边写 `kernel_gen.passes.pipeline`、另一边只验证子模块导入成功的断裂。
- 我额外检查了当前 worktree residual diff，只包含 [`spec/pass/pass_manager.md`](/home/lfr/kernelcode_generate/wt-20260423-pass-infra-s1/spec/pass/pass_manager.md)、[`spec/pass/registry.md`](/home/lfr/kernelcode_generate/wt-20260423-pass-infra-s1/spec/pass/registry.md)、[`test/pass/test_pass_manager.py`](/home/lfr/kernelcode_generate/wt-20260423-pass-infra-s1/test/pass/test_pass_manager.py)、[`test/pass/test_pass_registry.py`](/home/lfr/kernelcode_generate/wt-20260423-pass-infra-s1/test/pass/test_pass_registry.py)，范围与 S1 当前说明一致。
Diff 反推审查：
- 按当前任务工作树的 residual diff，我复跑了：
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260423-pass-infra-s1:/home/lfr/kernelcode_generate pytest -q /home/lfr/kernelcode_generate/wt-20260423-pass-infra-s1/test/pass/test_pass_registry.py /home/lfr/kernelcode_generate/wt-20260423-pass-infra-s1/test/pass/test_pass_manager.py -ra` -> `59 passed, 1 warning`
  - `python3 -m py_compile /home/lfr/kernelcode_generate/wt-20260423-pass-infra-s1/test/pass/test_pass_registry.py /home/lfr/kernelcode_generate/wt-20260423-pass-infra-s1/test/pass/test_pass_manager.py` -> 通过
  - `git -C /home/lfr/kernelcode_generate/wt-20260423-pass-infra-s1 diff --check` -> 通过
- 额外现状核对：
  - `kernel_gen.passes.pipeline.build_default_lowering_pipeline is kernel_gen.passes.pipeline.default_lowering.build_default_lowering_pipeline` -> `True`
  - `kernel_gen.passes.pipeline.build_npu_demo_lowering_pipeline is kernel_gen.passes.pipeline.npu_demo_lowering.build_npu_demo_lowering_pipeline` -> `True`
  - `kernel_gen.passes.lowering.{LowerDmaMemoryHierarchyPass,TileAnalysisPass,TileElewisePass,TileReducePass}` 与各自 submodule export 的对象身份均为 `True`
合同验收：
- `expectation` 只作为合同验收资产单列。
- 本轮未执行 `expectation`，也未把 `expectation` 计入 Diff 反推审查。
可改进点：
- 本轮未发现当前切片内可直接执行、且仍未处理的问题。
自检：
- 已对照 S1 当前 review 口径，先核对计划正文、前序记录与当前 residual diff，再执行对应 pytest 与本地检查，没有只依赖 build 摘要下结论。
- 已确认上轮 review 指出的最后一项缺口确实被收齐，且本轮没有新增同级别问题。
结论：
- 结论：`通过`
- 下一步：进入 `merge`。

时间：2026-04-24 17:08 +0800
经办人：李白
任务：T-20260423-73440e31（merge）
任务目标：按最新通过的 review 结论合并 S1 canonical public path 与消费者迁移矩阵冻结改动，并把当前 worktree 同步到最新主线后完成收口。
执行前阅读记录：
- 已重读 [`TODO.md`](/home/lfr/kernelcode_generate/TODO.md) 当前任务行，确认本任务状态为 `merge`，worktree、计划书和记录文件一致。
- 已重读 [`ARCHITECTURE/plan/pass_infrastructure_refactor_green_plan.md`](/home/lfr/kernelcode_generate/ARCHITECTURE/plan/pass_infrastructure_refactor_green_plan.md) 的 S1 正文、全局完成态 / 验收设计与当前阶段验收资产。
- 已重读本记录前序 `build / review` 条目，确认最新 review 结论为 `通过`，且记录内已经写清 `Diff 反推自测`、`Diff 反推审查` 和 `expectation` 单列边界。
合并前同步：
- `git -C /home/lfr/kernelcode_generate/wt-20260423-pass-infra-s1 fetch origin` -> 已完成。
- `git -C /home/lfr/kernelcode_generate/wt-20260423-pass-infra-s1 rebase --autostash origin/main` -> 已完成，当前 worktree 已同步到 `origin/main@e143d1e`。
- 同步后 residual diff 仍只包含 [`spec/pass/pass_manager.md`](/home/lfr/kernelcode_generate/wt-20260423-pass-infra-s1/spec/pass/pass_manager.md)、[`spec/pass/registry.md`](/home/lfr/kernelcode_generate/wt-20260423-pass-infra-s1/spec/pass/registry.md)、[`test/pass/test_pass_manager.py`](/home/lfr/kernelcode_generate/wt-20260423-pass-infra-s1/test/pass/test_pass_manager.py)、[`test/pass/test_pass_registry.py`](/home/lfr/kernelcode_generate/wt-20260423-pass-infra-s1/test/pass/test_pass_registry.py)。
真实收口过程：
- 已核对当前 diff 与计划书 S1 目标一致：`spec` 固定 canonical public path / 调用边界，`pytest` 固定 surviving import matrix 与旧路径失败边界。
- 已核对前序记录中的 `Diff 反推自测` / `Diff 反推审查` 都围绕这 4 个 residual diff 文件展开，没有把 `expectation` 当作对应测试替代。
- 本轮 merge 不新增实现或测试口径，只把已通过 review 的 residual diff 收到主线。
验证：
- `git -C /home/lfr/kernelcode_generate/wt-20260423-pass-infra-s1 diff --check` -> 通过
合同验收：
- `expectation` 继续只作为合同验收资产单列；本轮 merge 未执行 `expectation`，也未把它计入 diff 反推测试。
结论：
- 当前 S1 residual diff 已按最新通过记录完成收口，可进入提交、推送和 `-done` 流程。
