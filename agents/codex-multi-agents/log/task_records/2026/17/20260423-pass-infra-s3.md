时间：2026-04-24 01:34 +0800
经办人：睡觉小分队
任务：T-20260423-5b62c1a4
任务目标：按计划书 S3 收口 `dma_memory_hierarchy` 与 `memory_pool` 的 rehome spec，明确 surviving public path、旧 lowering 路径失败边界与 registry / pass_manager 迁移矩阵。
执行前阅读记录：
- 已读 [`TODO.md`](/home/lfr/kernelcode_generate/TODO.md:5) 当前任务行，确认 `worktree`、计划书、任务类型与记录文件一致。
- 已读 [`ARCHITECTURE/plan/pass_infrastructure_refactor_green_plan.md`](/home/lfr/kernelcode_generate/ARCHITECTURE/plan/pass_infrastructure_refactor_green_plan.md:426) 的 `S3` 正文、全局完成态、合同真源顺序、消费者迁移矩阵与验收设计。
- 已读前序记录 [`agents/codex-multi-agents/log/task_records/2026/17/20260423-pass-infra-s1.md`](/home/lfr/kernelcode_generate/wt-20260423-pass-infra-s3/agents/codex-multi-agents/log/task_records/2026/17/20260423-pass-infra-s1.md) 与 [`agents/codex-multi-agents/log/task_records/2026/17/20260423-pass-infra-s2.md`](/home/lfr/kernelcode_generate/wt-20260423-pass-infra-s2/agents/codex-multi-agents/log/task_records/2026/17/20260423-pass-infra-s2.md)。
- 已读当前 `spec`、相关 pytest 与实现入口：[`spec/pass/lowering/dma_memory_hierarchy.md`](/home/lfr/kernelcode_generate/wt-20260423-pass-infra-s3/spec/pass/lowering/dma_memory_hierarchy.md)、[`spec/pass/lowering/memory_pool.md`](/home/lfr/kernelcode_generate/wt-20260423-pass-infra-s3/spec/pass/lowering/memory_pool.md)、[`spec/pass/registry.md`](/home/lfr/kernelcode_generate/wt-20260423-pass-infra-s3/spec/pass/registry.md)、[`spec/pass/pass_manager.md`](/home/lfr/kernelcode_generate/wt-20260423-pass-infra-s3/spec/pass/pass_manager.md)、[`test/pass/test_dma_memory_hierarchy.py`](/home/lfr/kernelcode_generate/wt-20260423-pass-infra-s3/test/pass/test_dma_memory_hierarchy.py)、[`test/pass/test_memory_pool.py`](/home/lfr/kernelcode_generate/wt-20260423-pass-infra-s3/test/pass/test_memory_pool.py)、[`test/pass/test_pass_registry.py`](/home/lfr/kernelcode_generate/wt-20260423-pass-infra-s3/test/pass/test_pass_registry.py)、[`test/pass/test_pass_manager.py`](/home/lfr/kernelcode_generate/wt-20260423-pass-infra-s3/test/pass/test_pass_manager.py)、[`kernel_gen/passes/registry.py`](/home/lfr/kernelcode_generate/wt-20260423-pass-infra-s3/kernel_gen/passes/registry.py)、[`kernel_gen/passes/lowering/__init__.py`](/home/lfr/kernelcode_generate/wt-20260423-pass-infra-s3/kernel_gen/passes/lowering/__init__.py)、[`kernel_gen/passes/lowering/dma_memory_hierarchy.py`](/home/lfr/kernelcode_generate/wt-20260423-pass-infra-s3/kernel_gen/passes/lowering/dma_memory_hierarchy.py)、[`kernel_gen/passes/lowering/memory_pool.py`](/home/lfr/kernelcode_generate/wt-20260423-pass-infra-s3/kernel_gen/passes/lowering/memory_pool.py)。
最小功能闭环：
- 把 `LowerDmaMemoryHierarchyPass` 与 `MemoryPoolPass` 的公开导入口径统一收口到 `kernel_gen.passes.dma_memory_hierarchy` / `kernel_gen.passes.memory_pool`。
- 把 `kernel_gen.passes.lowering.dma_memory_hierarchy` 与 `kernel_gen.passes.lowering.memory_pool` 明确写成旧路径失败边界。
- 让 [`spec/pass/registry.md`](/home/lfr/kernelcode_generate/wt-20260423-pass-infra-s3/spec/pass/registry.md) 与 [`spec/pass/pass_manager.md`](/home/lfr/kernelcode_generate/wt-20260423-pass-infra-s3/spec/pass/pass_manager.md) 的当前迁移矩阵与上述口径一致，便于下游 build 继续补实现与 pytest。
改动：
- 当前任务给定的 `worktree` 初始不存在；已在本轮创建 `/home/lfr/kernelcode_generate/wt-20260423-pass-infra-s3`，随后仅在该 `worktree` 内继续处理。
- 更新 [`spec/pass/lowering/dma_memory_hierarchy.md`](/home/lfr/kernelcode_generate/wt-20260423-pass-infra-s3/spec/pass/lowering/dma_memory_hierarchy.md)，把 `功能实现` 与使用示例改成上级模块导入，新增公开导入与旧路径失败边界，并把 registry / pass_manager 对应的验证职责写进测试目标。
- 更新 [`spec/pass/lowering/memory_pool.md`](/home/lfr/kernelcode_generate/wt-20260423-pass-infra-s3/spec/pass/lowering/memory_pool.md)，把 `功能实现` 与使用示例改成上级模块导入，新增公开导入与旧路径失败边界，并补充由 registry pytest 承接的迁移验证要求。
- 更新 [`spec/pass/registry.md`](/home/lfr/kernelcode_generate/wt-20260423-pass-infra-s3/spec/pass/registry.md)，把章节名改为“当前公开路径与迁移矩阵”，新增 `kernel_gen.passes.dma_memory_hierarchy` / `kernel_gen.passes.memory_pool` 为 canonical public path，并把两个旧 lowering 路径移入失败边界列表。
- 更新 [`spec/pass/pass_manager.md`](/home/lfr/kernelcode_generate/wt-20260423-pass-infra-s3/spec/pass/pass_manager.md)，把章节名改为“当前调用边界”，补写 `LowerDmaMemoryHierarchyPass` / `MemoryPoolPass` 的上级模块导入口径，并明确旧 lowering 路径不再作为主入口。
验证：
- `git -C /home/lfr/kernelcode_generate/wt-20260423-pass-infra-s3 diff --check -- spec/pass/lowering/dma_memory_hierarchy.md spec/pass/lowering/memory_pool.md spec/pass/pass_manager.md spec/pass/registry.md`
  - 结果：通过。
- `python3` 断言脚本核对 4 份 `spec` 中的新路径、旧路径失败边界与章节名。
  - 结果：`spec assertions passed`。
- `rg -n "lowering\\.dma_memory_hierarchy|lowering\\.memory_pool|passes\\.dma_memory_hierarchy|passes\\.memory_pool|当前公开路径与迁移矩阵|当前调用边界" spec/pass/lowering/dma_memory_hierarchy.md spec/pass/lowering/memory_pool.md spec/pass/pass_manager.md spec/pass/registry.md`
  - 结果：命中新旧路径与迁移矩阵文案，未发现漏改点。
Diff 反推自测：
- 本轮实际 diff 只落在 [`spec/pass/lowering/dma_memory_hierarchy.md`](/home/lfr/kernelcode_generate/wt-20260423-pass-infra-s3/spec/pass/lowering/dma_memory_hierarchy.md)、[`spec/pass/lowering/memory_pool.md`](/home/lfr/kernelcode_generate/wt-20260423-pass-infra-s3/spec/pass/lowering/memory_pool.md)、[`spec/pass/pass_manager.md`](/home/lfr/kernelcode_generate/wt-20260423-pass-infra-s3/spec/pass/pass_manager.md)、[`spec/pass/registry.md`](/home/lfr/kernelcode_generate/wt-20260423-pass-infra-s3/spec/pass/registry.md) 与本记录文件，因此反推自测只做文本核对、断言脚本与 `git diff --check`。
- 计划书列出的 `pytest -q test/pass/test_dma_memory_hierarchy.py test/pass/test_memory_pool.py` 与 `registry/pass_manager` 相关 pytest 由下游 build 按实现与测试 diff 继续兑现；本轮未运行，因为当前角色只改 `spec`。
合同验收（如适用）：
- `expectation/pass/pipeline/default_lowering.py` 仍只作合同验收资产单列。
- 本轮未执行 `expectation`，也未把 `expectation` 计入 Diff 反推自测。
自检：
- 已按任务要求先读完整 `S3`、全局完成态、验收设计、前序记录与相关 `spec/test/实现`，没有只看任务标题开工。
- 本轮只改点名 `spec` 与任务记录，没有顺手改实现、pytest 或仓库中的 `expectation`。
- `dma_memory_hierarchy` / `memory_pool` 的公开导入、旧路径失败边界、registry / pass_manager 迁移矩阵、示例代码与后续 pytest 承接关系都已写清，没有重复入口或双口径。
- `功能实现` 链接、使用示例、边界与失败模型已同步到最新目标路径；下游 build 可以直接按这份 `spec` 做 rehome。
结论：
- 当前 `spec` 任务已完成，记录已写入对应 `worktree`。
- 下一步按 `TODO.md` 创建 `build` 续流任务，继续完成 `dma_memory_hierarchy` / `memory_pool` 的实现迁移、旧路径退场与对应 pytest。

---
时间：2026-04-24 02:10 +0800
经办人：jcc你莫辜负
任务：T-20260423-5b62c1a4（build）
任务目标：按计划书 `S3` 完成 `dma_memory_hierarchy` / `memory_pool` 的实现 rehome、旧路径退场、registry / default pipeline / pytest / importlib 同步更新，并补齐真实自检与 `Diff 反推自测`。
执行前阅读记录：
- 已重读 [`TODO.md`](/home/lfr/kernelcode_generate/TODO.md:5) 当前任务行，确认当前任务类型为 `build`。
- 已重读 [`ARCHITECTURE/plan/pass_infrastructure_refactor_green_plan.md`](/home/lfr/kernelcode_generate/ARCHITECTURE/plan/pass_infrastructure_refactor_green_plan.md:426) 的 `S3` 正文、全局完成态 / 验收设计与 `S1` 记录。
- 已重读本记录上一条 `spec` 条目，以及当前 diff 对应的 [`kernel_gen/passes/lowering/__init__.py`](/home/lfr/kernelcode_generate/wt-20260423-pass-infra-s3/kernel_gen/passes/lowering/__init__.py)、[`kernel_gen/passes/registry.py`](/home/lfr/kernelcode_generate/wt-20260423-pass-infra-s3/kernel_gen/passes/registry.py)、[`kernel_gen/passes/pipeline/default_lowering.py`](/home/lfr/kernelcode_generate/wt-20260423-pass-infra-s3/kernel_gen/passes/pipeline/default_lowering.py)、[`test/pass/test_dma_memory_hierarchy.py`](/home/lfr/kernelcode_generate/wt-20260423-pass-infra-s3/test/pass/test_dma_memory_hierarchy.py)、[`test/pass/test_memory_pool.py`](/home/lfr/kernelcode_generate/wt-20260423-pass-infra-s3/test/pass/test_memory_pool.py)、[`test/pass/test_pass_registry.py`](/home/lfr/kernelcode_generate/wt-20260423-pass-infra-s3/test/pass/test_pass_registry.py)、[`test/pass/test_pass_manager.py`](/home/lfr/kernelcode_generate/wt-20260423-pass-infra-s3/test/pass/test_pass_manager.py) 与 [`test/pass/test_pipeline_default_lowering.py`](/home/lfr/kernelcode_generate/wt-20260423-pass-infra-s3/test/pass/test_pipeline_default_lowering.py)。
最小功能闭环：
- 把实现文件从 `kernel_gen/passes/lowering/` 上移到 [`kernel_gen/passes/dma_memory_hierarchy.py`](/home/lfr/kernelcode_generate/wt-20260423-pass-infra-s3/kernel_gen/passes/dma_memory_hierarchy.py) 与 [`kernel_gen/passes/memory_pool.py`](/home/lfr/kernelcode_generate/wt-20260423-pass-infra-s3/kernel_gen/passes/memory_pool.py)。
- 让 `kernel_gen.passes.lowering.dma_memory_hierarchy` 与 `kernel_gen.passes.lowering.memory_pool` 在当前现场稳定以 `ModuleNotFoundError` 失败。
- 让 `registry`、默认 pipeline、相关 pytest 与字符串导入同步改到新路径，并保持 pass 行为与顺序约束不变。
改动：
- 新增 [`kernel_gen/passes/dma_memory_hierarchy.py`](/home/lfr/kernelcode_generate/wt-20260423-pass-infra-s3/kernel_gen/passes/dma_memory_hierarchy.py) 与 [`kernel_gen/passes/memory_pool.py`](/home/lfr/kernelcode_generate/wt-20260423-pass-infra-s3/kernel_gen/passes/memory_pool.py)，承接原 `lowering/` 下的实现与文档说明。
- 删除旧文件 [`kernel_gen/passes/lowering/dma_memory_hierarchy.py`](/home/lfr/kernelcode_generate/wt-20260423-pass-infra-s3/kernel_gen/passes/lowering/dma_memory_hierarchy.py) 与 [`kernel_gen/passes/lowering/memory_pool.py`](/home/lfr/kernelcode_generate/wt-20260423-pass-infra-s3/kernel_gen/passes/lowering/memory_pool.py)，使旧 lowering 子模块真正退出现场。
- 更新 [`kernel_gen/passes/lowering/__init__.py`](/home/lfr/kernelcode_generate/wt-20260423-pass-infra-s3/kernel_gen/passes/lowering/__init__.py)：`LowerDmaMemoryHierarchyPass` 改为从上级模块聚合导出，不再依赖已退场的 lowering 子模块。
- 更新 [`kernel_gen/passes/registry.py`](/home/lfr/kernelcode_generate/wt-20260423-pass-infra-s3/kernel_gen/passes/registry.py) 与 [`kernel_gen/passes/pipeline/default_lowering.py`](/home/lfr/kernelcode_generate/wt-20260423-pass-infra-s3/kernel_gen/passes/pipeline/default_lowering.py)：统一改用上级模块路径加载 `LowerDmaMemoryHierarchyPass` / `MemoryPoolPass`。
- 更新 [`test/pass/test_dma_memory_hierarchy.py`](/home/lfr/kernelcode_generate/wt-20260423-pass-infra-s3/test/pass/test_dma_memory_hierarchy.py)、[`test/pass/test_memory_pool.py`](/home/lfr/kernelcode_generate/wt-20260423-pass-infra-s3/test/pass/test_memory_pool.py)、[`test/pass/test_pass_registry.py`](/home/lfr/kernelcode_generate/wt-20260423-pass-infra-s3/test/pass/test_pass_registry.py)、[`test/pass/test_pass_manager.py`](/home/lfr/kernelcode_generate/wt-20260423-pass-infra-s3/test/pass/test_pass_manager.py)、[`test/pass/test_pipeline_default_lowering.py`](/home/lfr/kernelcode_generate/wt-20260423-pass-infra-s3/test/pass/test_pipeline_default_lowering.py) 的导入路径、实现链接、coverage 文案和旧路径失败断言。
验证：
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260423-pass-infra-s3:/home/lfr/kernelcode_generate pytest -q /home/lfr/kernelcode_generate/wt-20260423-pass-infra-s3/test/pass/test_dma_memory_hierarchy.py /home/lfr/kernelcode_generate/wt-20260423-pass-infra-s3/test/pass/test_memory_pool.py /home/lfr/kernelcode_generate/wt-20260423-pass-infra-s3/test/pass/test_pass_registry.py /home/lfr/kernelcode_generate/wt-20260423-pass-infra-s3/test/pass/test_pass_manager.py /home/lfr/kernelcode_generate/wt-20260423-pass-infra-s3/test/pass/test_pipeline_default_lowering.py` -> `85 passed, 4 warnings`
- `python3 -m py_compile /home/lfr/kernelcode_generate/wt-20260423-pass-infra-s3/kernel_gen/passes/dma_memory_hierarchy.py /home/lfr/kernelcode_generate/wt-20260423-pass-infra-s3/kernel_gen/passes/memory_pool.py /home/lfr/kernelcode_generate/wt-20260423-pass-infra-s3/kernel_gen/passes/lowering/__init__.py /home/lfr/kernelcode_generate/wt-20260423-pass-infra-s3/kernel_gen/passes/registry.py /home/lfr/kernelcode_generate/wt-20260423-pass-infra-s3/kernel_gen/passes/pipeline/default_lowering.py /home/lfr/kernelcode_generate/wt-20260423-pass-infra-s3/test/pass/test_dma_memory_hierarchy.py /home/lfr/kernelcode_generate/wt-20260423-pass-infra-s3/test/pass/test_memory_pool.py /home/lfr/kernelcode_generate/wt-20260423-pass-infra-s3/test/pass/test_pass_registry.py /home/lfr/kernelcode_generate/wt-20260423-pass-infra-s3/test/pass/test_pass_manager.py /home/lfr/kernelcode_generate/wt-20260423-pass-infra-s3/test/pass/test_pipeline_default_lowering.py` -> 通过
- `git -C /home/lfr/kernelcode_generate/wt-20260423-pass-infra-s3 diff --check` -> 通过
- 本地核对：
  - `kernel_gen/passes/dma_memory_hierarchy.py`、`kernel_gen/passes/memory_pool.py` 已存在
  - `kernel_gen/passes/lowering/dma_memory_hierarchy.py`、`kernel_gen/passes/lowering/memory_pool.py` 已不存在
Diff 反推自测：
- 实际 diff 覆盖了 `kernel_gen/passes/{dma_memory_hierarchy.py,memory_pool.py,registry.py,pipeline/default_lowering.py,lowering/__init__.py}` 与 5 份 pass pytest，因此自测按真实改动反推为：
  - `test/pass/test_dma_memory_hierarchy.py`
  - `test/pass/test_memory_pool.py`
  - `test/pass/test_pass_registry.py`
  - `test/pass/test_pass_manager.py`
  - `test/pass/test_pipeline_default_lowering.py`
- 这组测试同时覆盖了新路径可导入、旧 lowering 子模块失败、registry 构造、default lowering pipeline 顺序与 pass 行为不回退。
合同验收资产（单列）：
- 本轮未执行 `expectation`。按当前任务边界，`expectation` 继续只作合同验收资产单列，不替代对应 pytest。
自检：
- API / 边界：`dma_memory_hierarchy` / `memory_pool` 的实现文件已经上移，新旧路径边界与 `S3 spec` 一致；旧 lowering 子模块不再残留为可导入实现文件。
- 复用 / 粒度：`lowering/__init__.py` 仅保留需要的聚合导出，没有额外引入新的 compat 子模块。
- 测试有效性：这轮 pytest 同时覆盖实现行为、导入矩阵、旧路径失败与 pipeline 顺序；不是只跑计划书最低命令。
- 可改进点：`test_memory_pool.py` 运行时仍出现来自 `replace_by` 的上游 deprecation warning，但不影响当前 `S3` rehome 结论；如要处理，应单列到后续行为维护任务。
结论：当前 build 已完成，rehome 与旧路径退场已收口，真实自检和 `Diff 反推自测` 已补齐；下一步执行 `-next -auto -type review` 并同步管理员。

---
时间：2026-04-24 02:13 +0800
经办人：朽木露琪亚
任务：T-20260423-5b62c1a4（review）
任务目标：复核 `S3 dma_memory_hierarchy / memory_pool rehome` 是否已按 spec 收口到 `kernel_gen.passes.{dma_memory_hierarchy,memory_pool}`，重点检查实现上移、旧 lowering 子模块失败、registry/default_lowering/pytest/importlib 更新、真实自检与 `Diff 反推自测`。
执行前阅读记录：
- 已重读 [`TODO.md`](/home/lfr/kernelcode_generate/TODO.md) 中 `T-20260423-5b62c1a4` 当前任务行，确认当前任务类型为 `review`，指派为 `朽木露琪亚`。
- 已重读 [`ARCHITECTURE/plan/pass_infrastructure_refactor_green_plan.md`](/home/lfr/kernelcode_generate/ARCHITECTURE/plan/pass_infrastructure_refactor_green_plan.md) 的 `S3` 正文、全局完成态 / 验收设计、消费者迁移矩阵与 `S1` 记录。
- 已重读本记录中的 `spec/build` 条目，并现场核对 [`kernel_gen/passes/dma_memory_hierarchy.py`](/home/lfr/kernelcode_generate/wt-20260423-pass-infra-s3/kernel_gen/passes/dma_memory_hierarchy.py)、[`kernel_gen/passes/memory_pool.py`](/home/lfr/kernelcode_generate/wt-20260423-pass-infra-s3/kernel_gen/passes/memory_pool.py)、[`kernel_gen/passes/lowering/__init__.py`](/home/lfr/kernelcode_generate/wt-20260423-pass-infra-s3/kernel_gen/passes/lowering/__init__.py)、[`kernel_gen/passes/registry.py`](/home/lfr/kernelcode_generate/wt-20260423-pass-infra-s3/kernel_gen/passes/registry.py)、[`kernel_gen/passes/pipeline/default_lowering.py`](/home/lfr/kernelcode_generate/wt-20260423-pass-infra-s3/kernel_gen/passes/pipeline/default_lowering.py)、[`test/pass/test_dma_memory_hierarchy.py`](/home/lfr/kernelcode_generate/wt-20260423-pass-infra-s3/test/pass/test_dma_memory_hierarchy.py)、[`test/pass/test_memory_pool.py`](/home/lfr/kernelcode_generate/wt-20260423-pass-infra-s3/test/pass/test_memory_pool.py)、[`test/pass/test_pass_registry.py`](/home/lfr/kernelcode_generate/wt-20260423-pass-infra-s3/test/pass/test_pass_registry.py)、[`test/pass/test_pass_manager.py`](/home/lfr/kernelcode_generate/wt-20260423-pass-infra-s3/test/pass/test_pass_manager.py) 与 [`spec/pass/lowering/dma_memory_hierarchy.md`](/home/lfr/kernelcode_generate/wt-20260423-pass-infra-s3/spec/pass/lowering/dma_memory_hierarchy.md)、[`spec/pass/lowering/memory_pool.md`](/home/lfr/kernelcode_generate/wt-20260423-pass-infra-s3/spec/pass/lowering/memory_pool.md)。
真实审查：
- 当前 diff 已按 `S3` 边界把实现上移到 [`kernel_gen/passes/dma_memory_hierarchy.py`](/home/lfr/kernelcode_generate/wt-20260423-pass-infra-s3/kernel_gen/passes/dma_memory_hierarchy.py) 与 [`kernel_gen/passes/memory_pool.py`](/home/lfr/kernelcode_generate/wt-20260423-pass-infra-s3/kernel_gen/passes/memory_pool.py)，旧 lowering 子模块文件已真实删除。
- `kernel_gen.passes.lowering` 只保留 `LowerDmaMemoryHierarchyPass` 的聚合导出；`kernel_gen.passes.lowering.dma_memory_hierarchy` 与 `kernel_gen.passes.lowering.memory_pool` 已稳定以 `ModuleNotFoundError` 失败，和 `S3` spec 一致。
- `registry`、`default_lowering`、`pytest` 与 importlib 矩阵均已切到上级模块路径，现场复跑没有回退。
- build 记录里的 `真实自检` 与 `Diff 反推自测` 口径完整，执行前阅读、最小功能闭环、自测命令、expectation 单列边界都写清，没有把 `expectation` 冒充 diff 证明。
问题清单：
- 未发现需要退回 `build` 的实现、测试或记录问题。
可改进点：
- [`kernel_gen/passes/memory_pool.py`](/home/lfr/kernelcode_generate/wt-20260423-pass-infra-s3/kernel_gen/passes/memory_pool.py) 运行时仍有 `replace_by` 的上游 deprecation warning；当前不构成功能阻断，但后续若要消除 warning，建议拆到独立维护任务。
Diff 反推审查：
- 被审 diff 主要覆盖 [`kernel_gen/passes/dma_memory_hierarchy.py`](/home/lfr/kernelcode_generate/wt-20260423-pass-infra-s3/kernel_gen/passes/dma_memory_hierarchy.py)、[`kernel_gen/passes/memory_pool.py`](/home/lfr/kernelcode_generate/wt-20260423-pass-infra-s3/kernel_gen/passes/memory_pool.py)、[`kernel_gen/passes/lowering/__init__.py`](/home/lfr/kernelcode_generate/wt-20260423-pass-infra-s3/kernel_gen/passes/lowering/__init__.py)、[`kernel_gen/passes/registry.py`](/home/lfr/kernelcode_generate/wt-20260423-pass-infra-s3/kernel_gen/passes/registry.py)、[`kernel_gen/passes/pipeline/default_lowering.py`](/home/lfr/kernelcode_generate/wt-20260423-pass-infra-s3/kernel_gen/passes/pipeline/default_lowering.py) 与对应 pytest。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260423-pass-infra-s3:/home/lfr/kernelcode_generate pytest -q /home/lfr/kernelcode_generate/wt-20260423-pass-infra-s3/test/pass/test_dma_memory_hierarchy.py /home/lfr/kernelcode_generate/wt-20260423-pass-infra-s3/test/pass/test_memory_pool.py /home/lfr/kernelcode_generate/wt-20260423-pass-infra-s3/test/pass/test_pass_registry.py /home/lfr/kernelcode_generate/wt-20260423-pass-infra-s3/test/pass/test_pass_manager.py /home/lfr/kernelcode_generate/wt-20260423-pass-infra-s3/test/pass/test_pipeline_default_lowering.py -ra`
  - 结果：`85 passed, 4 warnings`
- `python3 -m py_compile /home/lfr/kernelcode_generate/wt-20260423-pass-infra-s3/kernel_gen/passes/dma_memory_hierarchy.py /home/lfr/kernelcode_generate/wt-20260423-pass-infra-s3/kernel_gen/passes/memory_pool.py /home/lfr/kernelcode_generate/wt-20260423-pass-infra-s3/kernel_gen/passes/lowering/__init__.py /home/lfr/kernelcode_generate/wt-20260423-pass-infra-s3/kernel_gen/passes/registry.py /home/lfr/kernelcode_generate/wt-20260423-pass-infra-s3/kernel_gen/passes/pipeline/default_lowering.py /home/lfr/kernelcode_generate/wt-20260423-pass-infra-s3/test/pass/test_dma_memory_hierarchy.py /home/lfr/kernelcode_generate/wt-20260423-pass-infra-s3/test/pass/test_memory_pool.py /home/lfr/kernelcode_generate/wt-20260423-pass-infra-s3/test/pass/test_pass_registry.py /home/lfr/kernelcode_generate/wt-20260423-pass-infra-s3/test/pass/test_pass_manager.py /home/lfr/kernelcode_generate/wt-20260423-pass-infra-s3/test/pass/test_pipeline_default_lowering.py`
  - 结果：通过
- `git -C /home/lfr/kernelcode_generate/wt-20260423-pass-infra-s3 diff --check`
  - 结果：通过
- `python3` import matrix 核对：
  - `kernel_gen.passes.dma_memory_hierarchy.LowerDmaMemoryHierarchyPass` 可导入
  - `kernel_gen.passes.memory_pool.MemoryPoolPass` 可导入
  - `kernel_gen.passes.lowering.LowerDmaMemoryHierarchyPass` 聚合导出可导入
  - `kernel_gen.passes.lowering.dma_memory_hierarchy`、`kernel_gen.passes.lowering.memory_pool` 均以 `ModuleNotFoundError` 失败
  - 结果：通过
合同验收（单列，不计入 Diff 反推审查）：
- 本轮未执行 `expectation`；其仍只作为合同验收资产单列，不替代对应 pytest。
自检：
- 已按要求先读 `TODO`、计划书 `S3`、全局完成态 / 验收设计和前序记录，再按被审 diff 复跑对应 pytest 与本地检查。
- 审查范围只覆盖当前 `review` 指定的 `dma_memory_hierarchy / memory_pool rehome` 切片，没有越界扩大到 `S4+`。
- 当前可改进点只有 warning 级维护项，不影响本轮 `S3` rehome 收口结论。
结论：
- `review pass`
- `Diff 反推审查 completed`
- 当前 `S3 dma_memory_hierarchy / memory_pool rehome` 已按 spec 收口，可续到下游 `merge`。

---
时间：2026-04-24 18:50 +0800
经办人：李白
任务：T-20260423-5b62c1a4（merge）
任务目标：在最新 `origin/main` 上收口 `S3 dma_memory_hierarchy / memory_pool rehome` 的实现上移、旧 lowering 子模块失败边界、registry/default_lowering/pytest/importlib 同步结果，并完成提交、推送与 `-done`。
执行前阅读记录：
- 已重读 [`TODO.md`](/home/lfr/kernelcode_generate/TODO.md) 中 `T-20260423-5b62c1a4` 当前任务行，确认任务类型为 `merge`，当前 `worktree` 与计划书、记录文件一致。
- 已重读 [`ARCHITECTURE/plan/pass_infrastructure_refactor_green_plan.md`](../../../../../../../ARCHITECTURE/plan/pass_infrastructure_refactor_green_plan.md) 的 `S3` 正文、全局完成态 / 验收设计、消费者迁移矩阵，以及本记录中的 `spec/build/review` 条目。
- 已核对 review 结论：当前 residual diff 允许收口 `dma_memory_hierarchy` / `memory_pool` 上移后的 13 个文件，`expectation` 不涉及本轮 merge。
合并前同步：
- `timeout 60 git -C /home/lfr/kernelcode_generate/wt-20260423-pass-infra-s3 fetch origin` -> `origin/main` 已更新到 `121f1a9`。
- `git -C /home/lfr/kernelcode_generate/wt-20260423-pass-infra-s3 rebase --autostash origin/main` -> 通过；当前现场已重放到最新主线之上。
真实收口过程：
- 已确认当前 diff 仍围绕 `S3` 目标展开：新增 [`kernel_gen/passes/dma_memory_hierarchy.py`](../../../../../../../kernel_gen/passes/dma_memory_hierarchy.py) / [`kernel_gen/passes/memory_pool.py`](../../../../../../../kernel_gen/passes/memory_pool.py)，删除旧 lowering 子模块 [`kernel_gen/passes/lowering/dma_memory_hierarchy.py`](../../../../../../../kernel_gen/passes/lowering/dma_memory_hierarchy.py) / [`kernel_gen/passes/lowering/memory_pool.py`](../../../../../../../kernel_gen/passes/lowering/memory_pool.py)，并同步 `registry`、`default_lowering`、`spec` 与 4 组 pytest。
- 已确认旧路径失败边界与 surviving public path 一致：`kernel_gen.passes.lowering.dma_memory_hierarchy`、`kernel_gen.passes.lowering.memory_pool` 继续以 `ModuleNotFoundError` 失败；`kernel_gen.passes.lowering.LowerDmaMemoryHierarchyPass` 只保留聚合导出。
验证：
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260423-pass-infra-s3:/home/lfr/kernelcode_generate pytest -q /home/lfr/kernelcode_generate/wt-20260423-pass-infra-s3/test/pass/test_dma_memory_hierarchy.py /home/lfr/kernelcode_generate/wt-20260423-pass-infra-s3/test/pass/test_memory_pool.py /home/lfr/kernelcode_generate/wt-20260423-pass-infra-s3/test/pass/test_pass_registry.py /home/lfr/kernelcode_generate/wt-20260423-pass-infra-s3/test/pass/test_pass_manager.py /home/lfr/kernelcode_generate/wt-20260423-pass-infra-s3/test/pass/test_pipeline_default_lowering.py -ra` -> `85 passed, 4 warnings`
- `python3 -m py_compile /home/lfr/kernelcode_generate/wt-20260423-pass-infra-s3/kernel_gen/passes/dma_memory_hierarchy.py /home/lfr/kernelcode_generate/wt-20260423-pass-infra-s3/kernel_gen/passes/memory_pool.py /home/lfr/kernelcode_generate/wt-20260423-pass-infra-s3/kernel_gen/passes/lowering/__init__.py /home/lfr/kernelcode_generate/wt-20260423-pass-infra-s3/kernel_gen/passes/registry.py /home/lfr/kernelcode_generate/wt-20260423-pass-infra-s3/kernel_gen/passes/pipeline/default_lowering.py /home/lfr/kernelcode_generate/wt-20260423-pass-infra-s3/test/pass/test_dma_memory_hierarchy.py /home/lfr/kernelcode_generate/wt-20260423-pass-infra-s3/test/pass/test_memory_pool.py /home/lfr/kernelcode_generate/wt-20260423-pass-infra-s3/test/pass/test_pass_registry.py /home/lfr/kernelcode_generate/wt-20260423-pass-infra-s3/test/pass/test_pass_manager.py /home/lfr/kernelcode_generate/wt-20260423-pass-infra-s3/test/pass/test_pipeline_default_lowering.py` -> 通过
- import 边界核对脚本 -> `import matrix ok`
- `git -C /home/lfr/kernelcode_generate/wt-20260423-pass-infra-s3 diff --check` -> 通过
合同验收（单列，不计入 Diff 反推自测）：
- 本轮未执行 `expectation`；按 `S3` 边界，`expectation` 继续只作合同验收资产单列。
结论：
- 当前现场已满足 merge 收口条件，下一步执行提交、推送、主仓同步与 `-done`。
