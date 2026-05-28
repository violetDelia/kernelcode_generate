# T-20260528-pass-tuning-rehome-no-compat

## execute 开工记录

- 时间：2026-05-28 01:31:46 +0800
- 执行人：小李飞刀
- worktree：`/home/lfr/kernelcode_generate/wt-20260528-pass-tuning-rehome-no-compat`
- 分支：`task/pass-tuning-rehome-no-compat`
- 基线：`HEAD=origin/main=479ef47e2cd93f3810b891ce6cf3b053ca360b41`
- 计划书：`/home/lfr/kernelcode_generate/ARCHITECTURE/plan/pass_tuning_rehome_no_compat_green_plan.md`
- 禁止修改面：`expectation/`、`.skills/`、`agents/standard/`、`AGENTS.md`、`TODO.md`、`DONE.md`
- expectation 口径：本计划无必过 expectation；`expectation/pass/dma_memory_hierarchy/` 与 `expectation/pass/kernel_pattern_attach/` 只作为历史 / 本地只读来源，不作为当前 gate。

## 执行前阅读

- 已读根 `AGENTS.md` 用户粘贴版。
- 已读个人提示词：`agents/codex-multi-agents/agents/小李飞刀/小李飞刀.prompt.md`。
- 已读标准：`agents/standard/任务记录约定.md`、`agents/standard/实现文件规范.md`、`agents/standard/测试文件约定.md`。
- 已读计划书全文：`pass_tuning_rehome_no_compat_green_plan.md`。

## 计划内小任务卡核对

- S1：移动 `kernel_gen/passes/dma_memory_hierarchy.py` 与 `kernel_gen/passes/kernel_pattern_attach.py` 到 `kernel_gen/passes/tuning/`，不保留旧路径兼容。
- S2：更新 `kernel_gen.passes.tuning` export、registry、default/npu-demo pipeline 导入，并删除 `kernel_gen.passes.lowering.LowerDmaMemoryHierarchyPass` 聚合导出。
- S3：同步 spec 与 pytest，锁定新路径成功、旧路径失败；相关 expectation 只作为历史说明，不作为当前必跑入口。

## 最小功能闭环

- 新 canonical path：
  - `kernel_gen.passes.tuning.dma_memory_hierarchy.LowerDmaMemoryHierarchyPass`
  - `kernel_gen.passes.tuning.kernel_pattern_attach.KernelPatternAttachPass`
- 旧路径必须失败：
  - `kernel_gen.passes.dma_memory_hierarchy`
  - `kernel_gen.passes.kernel_pattern_attach`
- registry pass name 不变：
  - `lower-dma-memory-hierarchy`
  - `kernel-pattern-attach`
- pipeline pass 顺序与 pass 行为不变。

## 初始扫描

- `git status --short --untracked-files=all`：clean。
- 旧路径残留命中范围：
  - 实现：`kernel_gen/passes/registry.py`、`kernel_gen/pipeline/default_lowering.py`、`kernel_gen/pipeline/npu_demo_lowering.py`、`kernel_gen/passes/lowering/__init__.py`
  - spec：`spec/pass/lowering/dma_memory_hierarchy/spec.md`、`spec/pass/kernel_pattern_attach.md`、`spec/pass/pass_manager.md`、`spec/pass/registry.md`、pipeline spec
  - pytest：`test/passes/test_dma_memory_hierarchy.py`、`test/passes/test_kernel_pattern_attach.py`、`test/passes/test_pass_manager.py`、`test/passes/test_registry.py`、pipeline pytest

## execute 改动摘要

- 将 `kernel_gen/passes/dma_memory_hierarchy.py` 移动为 `kernel_gen/passes/tuning/dma_memory_hierarchy.py`。
- 将 `kernel_gen/passes/kernel_pattern_attach.py` 移动为 `kernel_gen/passes/tuning/kernel_pattern_attach.py`。
- 更新 `kernel_gen/passes/tuning/__init__.py`，导出 `LowerDmaMemoryHierarchyPass`、`KernelPatternAttachPass`、`LaunchKernelCostFuncPass`。
- 更新 registry 与 pipeline 导入：
  - `kernel_gen/passes/registry.py`
  - `kernel_gen/pipeline/default_lowering.py`
  - `kernel_gen/pipeline/npu_demo_lowering.py`
- 删除 `kernel_gen.passes.lowering.LowerDmaMemoryHierarchyPass` 聚合导出。
- 更新 spec：
  - `spec/pass/lowering/dma_memory_hierarchy/spec.md`
  - `spec/pass/kernel_pattern_attach.md`
  - `spec/pass/pass_manager.md`
  - `spec/pass/registry.md`
- 更新 pytest：
  - 新路径正例：`kernel_gen.passes.tuning.dma_memory_hierarchy`、`kernel_gen.passes.tuning.kernel_pattern_attach`、`kernel_gen.passes.tuning`
  - 旧路径负例：`kernel_gen.passes.dma_memory_hierarchy`、`kernel_gen.passes.kernel_pattern_attach`
  - lowering 聚合负例：`kernel_gen.passes.lowering.LowerDmaMemoryHierarchyPass`

## 最小功能闭环结果

- 新路径 import 成功：
  - `kernel_gen.passes.tuning.dma_memory_hierarchy`
  - `kernel_gen.passes.tuning.kernel_pattern_attach`
  - `kernel_gen.passes.tuning`
- 旧路径 import 失败：
  - `kernel_gen.passes.dma_memory_hierarchy`
  - `kernel_gen.passes.kernel_pattern_attach`
- `kernel_gen.passes.lowering` 不再暴露 `LowerDmaMemoryHierarchyPass`。
- `build_registered_pass("lower-dma-memory-hierarchy").__class__.__module__ == "kernel_gen.passes.tuning.dma_memory_hierarchy"`。
- `build_registered_pass("kernel-pattern-attach").__class__.__module__ == "kernel_gen.passes.tuning.kernel_pattern_attach"`。

## Diff 反推自测

- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/passes/test_dma_memory_hierarchy.py test/passes/test_kernel_pattern_attach.py`
  - 退出码：0
  - 结果：19 passed，1 warning
  - 锁定：两个 moved pass 的公开构造、公开 `apply` 行为、registry option 和 kernel-pattern attach 行为未回退。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/passes/test_registry.py test/passes/test_pass_manager.py`
  - 退出码：0
  - 结果：80 passed，1 warning
  - 锁定：registry 构造路径、新旧 import 正反例、lowering 聚合退场、pass manager 调用矩阵。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/passes/pipeline/test_default_lowering.py test/passes/pipeline/test_npu_demo_lowering.py`
  - 退出码：0
  - 结果：13 passed，1 warning
  - 锁定：default-lowering 与 npu-demo-lowering 使用新 tuning path，pipeline 顺序未改变。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/passes/tuning/test_launch_kernel_cost_func.py`
  - 退出码：0
  - 结果：18 passed，2 warnings
  - 锁定：扩展 `kernel_gen.passes.tuning` package export 未破坏既有 tuning pass。

## 计划验收与静态门禁

- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 -m py_compile kernel_gen/passes/tuning/dma_memory_hierarchy.py kernel_gen/passes/tuning/kernel_pattern_attach.py kernel_gen/passes/tuning/__init__.py kernel_gen/passes/registry.py kernel_gen/passes/lowering/__init__.py kernel_gen/pipeline/default_lowering.py kernel_gen/pipeline/npu_demo_lowering.py`
  - 退出码：0
- `test ! -e kernel_gen/passes/dma_memory_hierarchy.py && test ! -e kernel_gen/passes/kernel_pattern_attach.py`
  - 退出码：0
- 计划旧路径退场 Python AST/import 扫描
  - 退出码：0
  - 输出：`old-path-scan-ok`
- `rg -n "expectation\.pass\.(dma_memory_hierarchy|kernel_pattern_attach)" spec/pass/lowering/dma_memory_hierarchy/spec.md spec/pass/kernel_pattern_attach.md`
  - 退出码：1，无输出
  - 结论：目标 spec 未把历史 expectation 入口列为当前必跑命令。
- `git diff --check`
  - 退出码：0
- 敏感目录门禁：
  - `git diff --name-only -- expectation .skills agents/standard AGENTS.md TODO.md DONE.md`
  - `git diff --cached --name-only -- expectation .skills agents/standard AGENTS.md TODO.md DONE.md`
  - `git status --short --untracked-files=all -- expectation .skills agents/standard AGENTS.md TODO.md DONE.md`
  - 退出码：0，均无输出

## expectation 记录

- 本计划无必过 expectation。
- 未运行 `expectation.pass.dma_memory_hierarchy` / `expectation.pass.kernel_pattern_attach`。
- 原因：计划明确将相关 expectation 收为历史 / 本地只读合同来源；本任务只做 import-path rehome/no-compat，不修改 expectation。

## 减法检查

- 新增公开 API：无；仅迁移既有公开 API 到计划确认的新 canonical path。
- 删除旧入口：
  - `kernel_gen/passes/dma_memory_hierarchy.py`
  - `kernel_gen/passes/kernel_pattern_attach.py`
  - `kernel_gen.passes.lowering.LowerDmaMemoryHierarchyPass`
- 未保留 wrapper / alias / sys.modules 兼容层；旧路径扫描已通过。
- 新增 private callable：无。
- 逻辑改动 private callable：无。
- 说明：两个 pass 文件为 rehome，内部 private helper 仅随文件迁移并更新关联文件路径说明；未新增新的 helper 层，未新增 private-to-private 调用链。

## 自检

- 接口：`LowerDmaMemoryHierarchyPass` 与 `KernelPatternAttachPass` 的 class 签名、`from_options`、`apply`、pass name、registry option 语义均未改变。
- 边界：旧顶层 module path 和 lowering 聚合导出均按计划失败；新 tuning path 和 tuning package root 正常可达。
- 异常：旧路径 import 失败由 pytest 与扫描锁定；registry unknown option 行为未改。
- 兼容性：本轮是用户确认的 no-compat rehome；未保留旧 import shim。
- 冗余：未新增 wrapper/转发 helper；registry 只改导入来源。
- 测试有效性：Diff 反推 pytest 同时覆盖 pass 行为、registry、pass manager、pipeline 与 tuning package 既有 pass。
- 禁止修改面：`expectation/`、`.skills/`、`agents/standard/`、`AGENTS.md`、`TODO.md`、`DONE.md` 均为空 diff。

## 当前候选 diff

- `git status --short --untracked-files=all`：
  - `A agents/codex-multi-agents/log/task_records/2026/25/20260528-pass-tuning-rehome-no-compat-plan.md`
  - `M kernel_gen/passes/lowering/__init__.py`
  - `M kernel_gen/passes/registry.py`
  - `M kernel_gen/passes/tuning/__init__.py`
  - `R kernel_gen/passes/dma_memory_hierarchy.py -> kernel_gen/passes/tuning/dma_memory_hierarchy.py`
  - `R kernel_gen/passes/kernel_pattern_attach.py -> kernel_gen/passes/tuning/kernel_pattern_attach.py`
  - `M kernel_gen/pipeline/default_lowering.py`
  - `M kernel_gen/pipeline/npu_demo_lowering.py`
  - `M spec/pass/kernel_pattern_attach.md`
  - `M spec/pass/lowering/dma_memory_hierarchy/spec.md`
  - `M spec/pass/pass_manager.md`
  - `M spec/pass/registry.md`
  - `M test/passes/pipeline/test_default_lowering.py`
  - `M test/passes/pipeline/test_npu_demo_lowering.py`
  - `M test/passes/test_dma_memory_hierarchy.py`
  - `M test/passes/test_kernel_pattern_attach.py`
  - `M test/passes/test_pass_manager.py`
  - `M test/passes/test_registry.py`

## execute 结论

- 计划目标已完成。
- 无公开 API 未确认扩展。
- 无 expectation / `.skills` / `agents/standard` / 共享状态文件越权 diff。
- 建议按计划级流程进入 `review`。

## 流转记录

- `bash skills/codex-multi-agents/scripts/codex-multi-agents-task.sh ... -next ...`
  - 首次退出码：1
  - 原因：脚本无法解析 canonical agents list，提示需设置 `CODEX_MULTI_AGENTS_AGENTS_FILE` 或 `AGENTS_FILE`。
- `CODEX_MULTI_AGENTS_AGENTS_FILE=/home/lfr/kernelcode_generate/agents/codex-multi-agents/agents-lists.md bash skills/codex-multi-agents/scripts/codex-multi-agents-task.sh -file /home/lfr/kernelcode_generate/TODO.md -next -task_id T-20260528-7548d1c6 -from 小李飞刀 -type review ... -auto`
  - 退出码：0
  - 输出摘要：`OK: next T-20260528-7548d1c6`，已自动分发给 `不要啊教练`，并通知 `不要啊教练` 与 `神秘人`。

### 流转后收尾门禁

- `git diff --check`：exit=0，无输出。
- `git diff --name-only -- expectation .skills agents/standard AGENTS.md TODO.md DONE.md`：exit=0，无输出。
- `git diff --cached --name-only -- expectation .skills agents/standard AGENTS.md TODO.md DONE.md`：exit=0，无输出。
- `git status --short --untracked-files=all -- expectation .skills agents/standard AGENTS.md TODO.md DONE.md`：exit=0，无输出。

## review 记录

- 时间：2026-05-28 01:50 +0800
- 经办人：不要啊教练
- 阶段：review
- 任务：T-20260528-7548d1c6 / pass-tuning-rehome-no-compat
- 任务目标：审查 `dma_memory_hierarchy` / `kernel_pattern_attach` 迁入 `kernel_gen.passes.tuning` 且旧路径不兼容的候选 diff、Diff 反推自测、计划 pytest、py_compile、git diff check、敏感目录空 diff和任务记录。

### 审查前同步

- 执行目录：`/home/lfr/kernelcode_generate/wt-20260528-pass-tuning-rehome-no-compat`
- `git fetch origin`：exit=0。
- `HEAD=479ef47e2cd93f3810b891ce6cf3b053ca360b41`
- `origin/main=479ef47e2cd93f3810b891ce6cf3b053ca360b41`
- `merge-base=479ef47e2cd93f3810b891ce6cf3b053ca360b41`
- `git rev-list --left-right --count HEAD...origin/main`：`0 0`。
- 同步结论：任务 worktree 已对齐 latest `origin/main`，当前 diff 为待审候选改动；未发现需要合并主线或覆盖本地 diff 的场景。

### 审查范围

- 计划书：`/home/lfr/kernelcode_generate/ARCHITECTURE/plan/pass_tuning_rehome_no_compat_green_plan.md`
- 任务记录：`agents/codex-multi-agents/log/task_records/2026/25/20260528-pass-tuning-rehome-no-compat-plan.md`
- 候选 diff：
  - `kernel_gen/passes/lowering/__init__.py`
  - `kernel_gen/passes/registry.py`
  - `kernel_gen/passes/tuning/__init__.py`
  - `kernel_gen/passes/dma_memory_hierarchy.py -> kernel_gen/passes/tuning/dma_memory_hierarchy.py`
  - `kernel_gen/passes/kernel_pattern_attach.py -> kernel_gen/passes/tuning/kernel_pattern_attach.py`
  - `kernel_gen/pipeline/default_lowering.py`
  - `kernel_gen/pipeline/npu_demo_lowering.py`
  - `spec/pass/kernel_pattern_attach.md`
  - `spec/pass/lowering/dma_memory_hierarchy/spec.md`
  - `spec/pass/pass_manager.md`
  - `spec/pass/registry.md`
  - `test/passes/pipeline/test_default_lowering.py`
  - `test/passes/pipeline/test_npu_demo_lowering.py`
  - `test/passes/test_dma_memory_hierarchy.py`
  - `test/passes/test_kernel_pattern_attach.py`
  - `test/passes/test_pass_manager.py`
  - `test/passes/test_registry.py`
  - 本任务记录。

### findings

1. 阻断：`spec/pass/kernel_pattern_attach.md:44` 的 `API 详细说明` 仍是旧式简写，未按 `agents/standard/spec文件规范.md` 为每个公开 API 条目补齐 `api`、`参数`、`返回值`、`使用示例`、`功能说明`、`注意事项`。
   - 影响：本轮已经修改该 spec 的实现路径和 expectation 口径，属于当前候选范围；若放行，`KernelPatternAttachPass` 的公开构造、`from_options`、`apply` 的参数/返回/示例/注意事项仍不能被机械审查，后续 execute/review 无法按当前 spec 标准判断公开 API 是否闭合。
   - 最小返工动作：在 `spec/pass/kernel_pattern_attach.md` 的三个公开 API 条目下分别补齐标准字段，并确保 `api` 字段与顶部 `API 列表` 完全一致；`参数` 逐项说明 `fold`、`options`、`ctx`、`module` 的类型、默认值、是否允许 `None` 与错误语义；`返回值` 写清实例或 `None`；`使用示例` 只通过公开 import 路径 `kernel_gen.passes.tuning.kernel_pattern_attach` 调用。
   - 验收方式：复跑 `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/passes/test_kernel_pattern_attach.py test/passes/test_registry.py test/passes/test_pass_manager.py`、计划 pytest、`py_compile`、`git diff --check` 和敏感目录门禁。

### Diff 反推审查

- `kernel_gen/passes/dma_memory_hierarchy.py` 与 `kernel_gen/passes/kernel_pattern_attach.py` 已以 rename 形式迁入 `kernel_gen/passes/tuning/`，旧顶层文件不存在。
- `kernel_gen/passes/tuning/__init__.py` 已导出 `LowerDmaMemoryHierarchyPass`、`KernelPatternAttachPass`、`LaunchKernelCostFuncPass`，registry 与 default/npu-demo pipeline 均改为新 tuning path。
- `test/passes/test_registry.py`、`test/passes/test_pass_manager.py`、pipeline pytest 已覆盖新路径正例、旧路径失败、旧 lowering aggregate 退场与 registry class `__module__` 指向。
- `spec/pass/lowering/dma_memory_hierarchy/spec.md` 的 API 列表紧跟功能简介，API 详细说明已包含参数、返回值、示例、功能说明与注意事项；该文件当前无同类阻断。
- `spec/pass/kernel_pattern_attach.md` 的 API 列表位置正确，但 API 详细说明未达当前 spec 标准，形成本轮唯一阻断。
- 本计划无必过 expectation；`expectation/pass/dma_memory_hierarchy/` 与 `expectation/pass/kernel_pattern_attach/` 只作为历史 / 本地只读来源，本轮未运行 expectation 作为通过依据。

### 复跑验证

- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/passes/test_dma_memory_hierarchy.py test/passes/test_kernel_pattern_attach.py`：exit=0，`19 passed, 1 warning`。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/passes/test_registry.py test/passes/test_pass_manager.py`：exit=0，`80 passed, 1 warning`。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/passes/pipeline/test_default_lowering.py test/passes/pipeline/test_npu_demo_lowering.py`：exit=0，`13 passed, 1 warning`。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/passes/tuning/test_launch_kernel_cost_func.py`：exit=0，`18 passed, 2 warnings`。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 -m py_compile kernel_gen/passes/tuning/dma_memory_hierarchy.py kernel_gen/passes/tuning/kernel_pattern_attach.py kernel_gen/passes/tuning/__init__.py kernel_gen/passes/registry.py kernel_gen/passes/lowering/__init__.py kernel_gen/pipeline/default_lowering.py kernel_gen/pipeline/npu_demo_lowering.py`：exit=0。
- `test ! -e kernel_gen/passes/dma_memory_hierarchy.py && test ! -e kernel_gen/passes/kernel_pattern_attach.py`：exit=0，输出 `old-files-absent`。
- 计划旧路径退场 Python AST/import 扫描：exit=0，输出 `old-path-scan-ok`。
- `rg -n "python3 -m expectation\.pass\.(dma_memory_hierarchy|kernel_pattern_attach)" spec/pass/lowering/dma_memory_hierarchy/spec.md spec/pass/kernel_pattern_attach.md`：exit=1，无输出；目标 spec 未把历史 expectation 写成当前必跑入口。
- `git diff --check`：exit=0，输出 `diff-check-ok`。
- 敏感目录门禁：
  - `git diff --name-only -- expectation .skills agents/standard AGENTS.md TODO.md DONE.md`：exit=0，无输出。
  - `git diff --cached --name-only -- expectation .skills agents/standard AGENTS.md TODO.md DONE.md`：exit=0，无输出。
  - `git status --short --untracked-files=all -- expectation .skills agents/standard AGENTS.md TODO.md DONE.md`：exit=0，无输出。

### 静态边界与减法审查

- `git diff -U0 -- '*.py'` 新增可疑命中仅包含公开 import matrix、旧路径负例 `importlib.import_module/find_spec` 和既有测试 monkeypatch 场景；未见新增 `ctx` 能力探测、`object` 签名或新增嵌套函数。
- AST 嵌套函数扫描命中均为既有 registry decorator / 既有 pytest 局部 stub；本轮未新增非装饰器嵌套函数。
- moved pass 文件内存在既有 private helper 与既有 private helper 调用图谱；本轮为 rename/rehome 与文档路径同步，未新增新的 private callable、未新增新的 private-to-private 调用链，且计划明确不顺手重构 pass 内部 helper。
- 减法结论：旧顶层 module path、旧 lowering aggregate export、旧 expectation 当前必跑 spec 口径均已按计划删除或退场；未保留 wrapper、alias 或 `sys.modules` 兼容层。

### 自检

- 已逐项读取计划书、任务记录和实际 diff；未只依赖 execute 摘要。
- 已复跑计划 pytest、Diff 反推 pytest、py_compile、旧路径退场扫描、git diff check 和敏感目录门禁。
- 已核对公开 API 用户确认来源、旧路径不兼容口径、无 expectation 必过口径和敏感目录空 diff。
- 当前仍存在一个可执行 spec 标准返工项，因此不得给出通过。

### 结论

- `review` 结论：最小需改项 / 不通过。
- 下一步：退回 `execute`，只需补齐 `spec/pass/kernel_pattern_attach.md` 的 `API 详细说明` 标准字段，并复跑上述相关验证。

## execute 返工记录

- 时间：2026-05-28 01:56 +0800
- 经办人：小李飞刀
- 阶段：execute
- 任务：T-20260528-7548d1c6 / pass-tuning-rehome-no-compat
- 返工目标：修复 review 指出的最小阻断项，补齐 `spec/pass/kernel_pattern_attach.md` 中 `KernelPatternAttachPass`、`from_options`、`apply` 的 `API 详细说明` 标准字段。

### 返工范围

- 修改文件：`spec/pass/kernel_pattern_attach.md`
- 修改内容：
  - `class KernelPatternAttachPass(fold: bool = True)` 补齐 `api`、`参数`、`返回值`、`使用示例`、`功能说明`、`注意事项`。
  - `KernelPatternAttachPass.from_options(options: dict[str, str]) -> KernelPatternAttachPass` 补齐 `api`、`参数`、`返回值`、`使用示例`、`功能说明`、`注意事项`。
  - `KernelPatternAttachPass.apply(ctx: Context, module: ModuleOp) -> None` 补齐 `api`、`参数`、`返回值`、`使用示例`、`功能说明`、`注意事项`。
- 未修改实现语义、pytest 逻辑、registry/pipeline 逻辑或 expectation。

### Diff 反推自测计划

- `spec/pass/kernel_pattern_attach.md` 变更直接对应 `KernelPatternAttachPass` 公开构造、registry options 与 apply 行为，因此复跑：
  - `test/passes/test_kernel_pattern_attach.py`
  - `test/passes/test_registry.py`
  - `test/passes/test_pass_manager.py`
- 保持计划候选范围不回退，因此复跑：
  - `test/passes/test_dma_memory_hierarchy.py`
  - `test/passes/pipeline/test_default_lowering.py`
  - `test/passes/pipeline/test_npu_demo_lowering.py`
  - `test/passes/tuning/test_launch_kernel_cost_func.py`
- 本计划无必过 expectation；expectation 不作为 Diff 反推测试。

### 减法检查

- 本次返工只修改 spec 文本，未新增函数、类、helper、wrapper 或兼容层。
- 未新增 private callable；不存在本轮新增 private callable 小于 5 行、private callable 调用 private callable、非装饰器嵌套函数或 ctx 能力探测问题。
- 旧顶层 pass 路径仍保持删除状态，未恢复兼容 shim。

### 返工验证

- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/passes/test_kernel_pattern_attach.py test/passes/test_registry.py test/passes/test_pass_manager.py`：exit=0，`85 passed, 1 warning`。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/passes/test_dma_memory_hierarchy.py test/passes/test_kernel_pattern_attach.py`：exit=0，`19 passed, 1 warning`。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/passes/pipeline/test_default_lowering.py test/passes/pipeline/test_npu_demo_lowering.py`：exit=0，`13 passed, 1 warning`。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/passes/tuning/test_launch_kernel_cost_func.py`：exit=0，`18 passed, 2 warnings`。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 -m py_compile kernel_gen/passes/tuning/dma_memory_hierarchy.py kernel_gen/passes/tuning/kernel_pattern_attach.py kernel_gen/passes/tuning/__init__.py kernel_gen/passes/registry.py kernel_gen/passes/lowering/__init__.py kernel_gen/pipeline/default_lowering.py kernel_gen/pipeline/npu_demo_lowering.py`：exit=0。
- `git diff --check`：exit=0，无输出。
- 敏感目录门禁：
  - `git diff --name-only -- expectation .skills agents/standard AGENTS.md TODO.md DONE.md`：exit=0，无输出。
  - `git diff --cached --name-only -- expectation .skills agents/standard AGENTS.md TODO.md DONE.md`：exit=0，无输出。
  - `git status --short --untracked-files=all -- expectation .skills agents/standard AGENTS.md TODO.md DONE.md`：exit=0，无输出。

### 返工自检

- review 指出的三个公开 API 条目均已补齐标准字段，且 `api` 字段与顶部 `API 列表` 保持一致。
- 示例只使用公开 tuning import path：`kernel_gen.passes.tuning.kernel_pattern_attach`。
- 未把 expectation 作为 Diff 反推测试；本计划无必过 expectation。
- 候选 diff 仍保持 expectation / `.skills` / `agents/standard` / `AGENTS.md` / `TODO.md` / `DONE.md` 空 diff。

### execute 返工结论

- review 最小阻断项已闭合。
- 建议重新流转 `review`。

### 返工流转记录

- `CODEX_MULTI_AGENTS_AGENTS_FILE=/home/lfr/kernelcode_generate/agents/codex-multi-agents/agents-lists.md bash skills/codex-multi-agents/scripts/codex-multi-agents-task.sh -file /home/lfr/kernelcode_generate/TODO.md -next -task_id T-20260528-7548d1c6 -from 小李飞刀 -type review ... -auto`
  - 退出码：0
  - 输出摘要：`OK: next T-20260528-7548d1c6`，已自动分发给 `不要啊教练`，并通知 `不要啊教练` 与 `神秘人`。

## review 复审记录

- 时间：2026-05-28 02:05 +0800
- 经办人：不要啊教练
- 阶段：review 复审
- 任务：T-20260528-7548d1c6 / pass-tuning-rehome-no-compat
- 任务目标：复审 `spec/pass/kernel_pattern_attach.md` API 详细说明返工，并核对 pass rehome/no-compat 候选 diff、计划 pytest、py_compile、旧路径退场扫描、git diff check、敏感目录空 diff和任务记录。

### 审查前同步

- 执行目录：`/home/lfr/kernelcode_generate/wt-20260528-pass-tuning-rehome-no-compat`
- `git fetch origin`：exit=0。
- `HEAD=479ef47e2cd93f3810b891ce6cf3b053ca360b41`
- `origin/main=479ef47e2cd93f3810b891ce6cf3b053ca360b41`
- `merge-base=479ef47e2cd93f3810b891ce6cf3b053ca360b41`
- `git rev-list --left-right --count HEAD...origin/main`：`0 0`。
- 同步结论：任务 worktree 已对齐 latest `origin/main`，当前 diff 为待审候选改动；无冲突或覆盖风险。

### 复审范围

- 计划书：`/home/lfr/kernelcode_generate/ARCHITECTURE/plan/pass_tuning_rehome_no_compat_green_plan.md`
- 任务记录：`agents/codex-multi-agents/log/task_records/2026/25/20260528-pass-tuning-rehome-no-compat-plan.md`
- 重点返工文件：`spec/pass/kernel_pattern_attach.md`
- 候选 diff：
  - `kernel_gen/passes/lowering/__init__.py`
  - `kernel_gen/passes/registry.py`
  - `kernel_gen/passes/tuning/__init__.py`
  - `kernel_gen/passes/dma_memory_hierarchy.py -> kernel_gen/passes/tuning/dma_memory_hierarchy.py`
  - `kernel_gen/passes/kernel_pattern_attach.py -> kernel_gen/passes/tuning/kernel_pattern_attach.py`
  - `kernel_gen/pipeline/default_lowering.py`
  - `kernel_gen/pipeline/npu_demo_lowering.py`
  - `spec/pass/kernel_pattern_attach.md`
  - `spec/pass/lowering/dma_memory_hierarchy/spec.md`
  - `spec/pass/pass_manager.md`
  - `spec/pass/registry.md`
  - `test/passes/pipeline/test_default_lowering.py`
  - `test/passes/pipeline/test_npu_demo_lowering.py`
  - `test/passes/test_dma_memory_hierarchy.py`
  - `test/passes/test_kernel_pattern_attach.py`
  - `test/passes/test_pass_manager.py`
  - `test/passes/test_registry.py`
  - 本任务记录。

### findings

- 阻断项：无。
- 重复问题复核：上一轮 `spec/pass/kernel_pattern_attach.md:44` API 详细说明字段缺失已闭合；`KernelPatternAttachPass`、`KernelPatternAttachPass.from_options(...)`、`KernelPatternAttachPass.apply(...)` 三个公开 API 条目均包含 `api`、`参数`、`返回值`、`使用示例`、`功能说明`、`注意事项`，且 `api` 字段与顶部 API 列表一致。
- 新增问题：无。
- 范围扩大：无；返工只触达 `spec/pass/kernel_pattern_attach.md` 和任务记录，未修改实现、pytest 或 expectation。

### Diff 反推审查

- `spec/pass/kernel_pattern_attach.md` 的返工直接对应上一轮阻断：补齐 API 详细说明标准字段，示例只使用公开 tuning import path `kernel_gen.passes.tuning.kernel_pattern_attach`。
- 两个 pass 的 rehome/no-compat 主线未回退：旧顶层 module 文件不存在，新 tuning path 可 import，旧 path import 失败，`kernel_gen.passes.lowering` 不再导出 `LowerDmaMemoryHierarchyPass`，registry class `__module__` 指向 tuning 子模块。
- `spec/pass/lowering/dma_memory_hierarchy/spec.md`、`spec/pass/registry.md`、`spec/pass/pass_manager.md` 与 pytest 的新旧路径正反例继续对齐计划口径。
- 本计划无必过 expectation；目标 spec 已把相关 expectation 写为历史 / 本地只读合同来源，不作为当前 gate；本轮未运行 expectation 作为通过依据。

### 复跑验证

- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/passes/test_kernel_pattern_attach.py test/passes/test_registry.py test/passes/test_pass_manager.py`：exit=0，`85 passed, 1 warning`。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/passes/test_dma_memory_hierarchy.py test/passes/test_kernel_pattern_attach.py`：exit=0，`19 passed, 1 warning`。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/passes/pipeline/test_default_lowering.py test/passes/pipeline/test_npu_demo_lowering.py`：exit=0，`13 passed, 1 warning`。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/passes/tuning/test_launch_kernel_cost_func.py`：exit=0，`18 passed, 2 warnings`。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 -m py_compile kernel_gen/passes/tuning/dma_memory_hierarchy.py kernel_gen/passes/tuning/kernel_pattern_attach.py kernel_gen/passes/tuning/__init__.py kernel_gen/passes/registry.py kernel_gen/passes/lowering/__init__.py kernel_gen/pipeline/default_lowering.py kernel_gen/pipeline/npu_demo_lowering.py`：exit=0。
- `test ! -e kernel_gen/passes/dma_memory_hierarchy.py && test ! -e kernel_gen/passes/kernel_pattern_attach.py`：exit=0，输出 `old-files-absent`。
- 计划旧路径退场 Python AST/import 扫描：exit=0，输出 `old-path-scan-ok`。
- `rg -n "python3 -m expectation\.pass\.(dma_memory_hierarchy|kernel_pattern_attach)" spec/pass/lowering/dma_memory_hierarchy/spec.md spec/pass/kernel_pattern_attach.md`：exit=1，无输出；目标 spec 未把历史 expectation 写成当前必跑入口。
- `git diff --check`：exit=0，输出 `diff-check-ok`。
- 敏感目录门禁：
  - `git diff --name-only -- expectation .skills agents/standard AGENTS.md TODO.md DONE.md`：exit=0，无输出。
  - `git diff --cached --name-only -- expectation .skills agents/standard AGENTS.md TODO.md DONE.md`：exit=0，无输出。
  - `git status --short --untracked-files=all -- expectation .skills agents/standard AGENTS.md TODO.md DONE.md`：exit=0，无输出。

### 减法审查

- 旧顶层 module path、旧 lowering aggregate export、旧 expectation 当前必跑 spec 口径均保持退场。
- 未恢复 wrapper、alias、`sys.modules` 兼容层或旧根路径 shim。
- 本轮返工只改 spec 文本；未新增 private callable、未新增 private-to-private 调用链、未新增 ctx 能力探测或非装饰器嵌套函数。
- moved pass 文件内既有 private helper 仅随文件迁移和文档路径同步，计划明确不顺手重构 pass 内部 helper，本轮无新增 helper 层。

### 自检

- 已读取计划书、任务记录、返工 diff 与实际候选 diff，未只看执行摘要。
- 已按实际 diff 复跑相关 pytest、计划 pytest、py_compile、旧路径退场扫描、git diff check 和敏感目录门禁。
- 已核对公开 API 用户确认来源、spec/API 列表、文件级 API 列表、旧路径不兼容、无必过 expectation 和禁止修改面。
- 当前无剩余可执行返工项。

### 结论

- `review` 复审结论：通过。
- 本任务为计划级 execute 落地任务，下一阶段应进入 `archive_acceptance / 计划书入档验收`，不得直接 merge。

## archive_acceptance 计划书入档验收记录

- 时间：2026-05-28 12:44 +0800
- 经办人：不要啊教练
- 阶段：archive_acceptance / 计划书入档验收
- 任务：T-20260528-7548d1c6 / pass-tuning-rehome-no-compat
- 任务目标：核对计划级任务 review 通过记录、latest 同步现场、任务记录完整性、Diff 反推审查、计划 pytest、py_compile、旧路径退场扫描、git diff check、敏感目录空 diff 与可入档性。

### 入档前同步现场

- 执行目录：`/home/lfr/kernelcode_generate/wt-20260528-pass-tuning-rehome-no-compat`
- `git fetch origin`：exit=0。
- `HEAD=479ef47e2cd93f3810b891ce6cf3b053ca360b41`
- `origin/main=479ef47e2cd93f3810b891ce6cf3b053ca360b41`
- `merge-base=479ef47e2cd93f3810b891ce6cf3b053ca360b41`
- `git rev-list --left-right --count HEAD...origin/main`：`0 0`。
- 同步结论：待入档 worktree 与 latest `origin/main` 对齐；当前候选 diff 与 review 复审范围一致；未发现冲突或覆盖风险。

### 候选范围核对

- 候选 diff：
  - `agents/codex-multi-agents/log/task_records/2026/25/20260528-pass-tuning-rehome-no-compat-plan.md`
  - `kernel_gen/passes/lowering/__init__.py`
  - `kernel_gen/passes/registry.py`
  - `kernel_gen/passes/tuning/__init__.py`
  - `kernel_gen/passes/dma_memory_hierarchy.py -> kernel_gen/passes/tuning/dma_memory_hierarchy.py`
  - `kernel_gen/passes/kernel_pattern_attach.py -> kernel_gen/passes/tuning/kernel_pattern_attach.py`
  - `kernel_gen/pipeline/default_lowering.py`
  - `kernel_gen/pipeline/npu_demo_lowering.py`
  - `spec/pass/kernel_pattern_attach.md`
  - `spec/pass/lowering/dma_memory_hierarchy/spec.md`
  - `spec/pass/pass_manager.md`
  - `spec/pass/registry.md`
  - `test/passes/pipeline/test_default_lowering.py`
  - `test/passes/pipeline/test_npu_demo_lowering.py`
  - `test/passes/test_dma_memory_hierarchy.py`
  - `test/passes/test_kernel_pattern_attach.py`
  - `test/passes/test_pass_manager.py`
  - `test/passes/test_registry.py`
- 计划书：`/home/lfr/kernelcode_generate/ARCHITECTURE/plan/pass_tuning_rehome_no_compat_green_plan.md`，本轮无计划书 diff；计划正文已记录用户确认来源、两轮 subagent strict review、后置限定复核和守护最终检验通过。
- review 复审结论：已记录 `通过`，并明确计划级任务下一阶段进入 `archive_acceptance`，不得直接 merge。
- 禁止修改面：`expectation/`、`.skills/`、`agents/standard/`、`AGENTS.md`、`TODO.md`、`DONE.md` 均未进入候选 diff。

### Diff 反推审查与入档验收

- 两个 pass 已迁入 `kernel_gen.passes.tuning`，旧顶层 module 文件不存在；未恢复 wrapper、alias、`sys.modules` 兼容层或旧 `kernel_gen.passes.lowering.LowerDmaMemoryHierarchyPass` aggregate export。
- Registry 与 default / npu-demo pipeline 均指向新 tuning path；pytest 已覆盖新路径正例、旧路径负例、registry class `__module__` 与 pipeline 顺序。
- `spec/pass/kernel_pattern_attach.md` 的上一轮阻断项已闭合：`KernelPatternAttachPass`、`from_options`、`apply` 均补齐 API 详细说明标准字段。
- 本计划无当前必过 `expectation`；相关 `expectation.pass.dma_memory_hierarchy` / `expectation.pass.kernel_pattern_attach` 仅作为历史 / 本地只读合同来源，本轮不运行、不修改、不纳入候选 diff。

### 复跑验证

- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/passes/test_dma_memory_hierarchy.py test/passes/test_kernel_pattern_attach.py`：exit=0，`19 passed, 1 warning`。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/passes/test_registry.py test/passes/test_pass_manager.py`：exit=0，`80 passed, 1 warning`。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/passes/pipeline/test_default_lowering.py test/passes/pipeline/test_npu_demo_lowering.py`：exit=0，`13 passed, 1 warning`。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/passes/tuning/test_launch_kernel_cost_func.py`：exit=0，`18 passed, 2 warnings`。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 -m py_compile kernel_gen/passes/tuning/dma_memory_hierarchy.py kernel_gen/passes/tuning/kernel_pattern_attach.py kernel_gen/passes/tuning/__init__.py kernel_gen/passes/registry.py kernel_gen/passes/lowering/__init__.py kernel_gen/pipeline/default_lowering.py kernel_gen/pipeline/npu_demo_lowering.py`：exit=0，输出 `py_compile-ok`。
- `test ! -e kernel_gen/passes/dma_memory_hierarchy.py && test ! -e kernel_gen/passes/kernel_pattern_attach.py`：exit=0，输出 `old-files-absent`。
- 计划旧路径退场 Python AST/import 扫描：exit=0，输出 `old-path-scan-ok`。
- `rg -n "python3 -m expectation\.pass\.(dma_memory_hierarchy|kernel_pattern_attach)" spec/pass/lowering/dma_memory_hierarchy/spec.md spec/pass/kernel_pattern_attach.md`：exit=1，包装命令输出 `expectation-current-gate-scan-ok`；目标 spec 未把历史 expectation 写成当前必跑入口。
- `git diff --check`：exit=0，输出 `diff-check-ok`。
- 敏感目录门禁：
  - `git diff --name-only -- expectation .skills agents/standard AGENTS.md TODO.md DONE.md`：exit=0，无输出。
  - `git diff --cached --name-only -- expectation .skills agents/standard AGENTS.md TODO.md DONE.md`：exit=0，无输出。
  - `git status --short --untracked-files=all -- expectation .skills agents/standard AGENTS.md TODO.md DONE.md`：exit=0，无输出。

### 减法审查

- 旧顶层 module path、旧 lowering aggregate export、旧 expectation 当前必跑 spec 口径均已退场。
- 未保留旧 shim、wrapper、alias、动态兼容或迁移层。
- 本轮候选 diff 未新增 private callable、private-to-private 调用链、非装饰器嵌套函数、ctx 能力探测或测试直连跨文件私有 API。

### 自检

- 已读取并核对最新 prompt、根 `AGENTS.md`、审查规范、任务记录约定、计划正文与任务记录。
- 已复核 review 通过结论、latest 同步现场、候选 diff、计划 pytest、py_compile、旧路径退场扫描、git diff check、敏感目录空 diff和无必过 expectation 口径。
- 未修改业务实现、spec、测试、计划书、`expectation/`、`.skills`、`agents/standard` 或任务状态文件。
- 当前无剩余可执行返工项。

### 入档验收结论

- `archive_acceptance` 结论：通过。
- 下一步：按计划级流程流转 `merge`；merge 前必须同批纳入代码、spec、测试与本任务记录，且继续排除 `expectation/`、`.skills/`、`agents/standard/`、`AGENTS.md`、`TODO.md`、`DONE.md`。

## merge 记录：李白

- 时间：2026-05-28 12:48 +0800
- 经办人：李白
- 阶段：merge
- 任务：T-20260528-7548d1c6 / pass-tuning-rehome-no-compat
- 任务目标：同批合入已通过 review 与 archive_acceptance 的 pass tuning rehome/no-compat 代码、spec、测试与任务记录，并继续排除 `expectation/`、`.skills/`、`agents/standard/`、`AGENTS.md`、`TODO.md`、`DONE.md`。

### 合并前核对

- 来源 worktree：`/home/lfr/kernelcode_generate/wt-20260528-pass-tuning-rehome-no-compat`
- 来源分支：`task/pass-tuning-rehome-no-compat`
- latest main：`HEAD=origin/main=479ef47e2cd93f3810b891ce6cf3b053ca360b41`
- 计划书：`/home/lfr/kernelcode_generate/ARCHITECTURE/plan/pass_tuning_rehome_no_compat_green_plan.md`
- review 复审结论：2026-05-28 02:05 +0800 通过。
- archive_acceptance 结论：2026-05-28 12:44 +0800 通过。
- 主仓保护：合并前主仓存在与本任务无关的本地 symbol 相关未提交改动；本轮只在任务 worktree 提交候选，不覆盖或带入主仓 dirty 文件。

### 实际合入文件

- `agents/codex-multi-agents/log/task_records/2026/25/20260528-pass-tuning-rehome-no-compat-plan.md`
- `kernel_gen/passes/lowering/__init__.py`
- `kernel_gen/passes/registry.py`
- `kernel_gen/passes/tuning/__init__.py`
- `kernel_gen/passes/dma_memory_hierarchy.py -> kernel_gen/passes/tuning/dma_memory_hierarchy.py`
- `kernel_gen/passes/kernel_pattern_attach.py -> kernel_gen/passes/tuning/kernel_pattern_attach.py`
- `kernel_gen/pipeline/default_lowering.py`
- `kernel_gen/pipeline/npu_demo_lowering.py`
- `spec/pass/kernel_pattern_attach.md`
- `spec/pass/lowering/dma_memory_hierarchy/spec.md`
- `spec/pass/pass_manager.md`
- `spec/pass/registry.md`
- `test/passes/pipeline/test_default_lowering.py`
- `test/passes/pipeline/test_npu_demo_lowering.py`
- `test/passes/test_dma_memory_hierarchy.py`
- `test/passes/test_kernel_pattern_attach.py`
- `test/passes/test_pass_manager.py`
- `test/passes/test_registry.py`

### 验证

- `git fetch --prune origin`：exit=0。
- `git diff --check`：exit=0。
- `git diff --name-only -- expectation .skills agents/standard AGENTS.md TODO.md DONE.md`：exit=0，无输出。
- `git status --short --ignored --untracked-files=all -- expectation .skills agents/standard AGENTS.md TODO.md DONE.md`：exit=0，无输出。
- archive_acceptance 已在同一 latest main 基线复跑并记录通过：`test_dma_memory_hierarchy.py + test_kernel_pattern_attach.py` 19 passed；`test_registry.py + test_pass_manager.py` 80 passed；`test_default_lowering.py + test_npu_demo_lowering.py` 13 passed；`test_launch_kernel_cost_func.py` 18 passed；`py_compile`、旧路径退场扫描、`git diff --check` 与敏感目录门禁均通过。

### 敏感目录与 expectation

- `expectation/`、`.skills/`、`agents/standard/`、`AGENTS.md`、`TODO.md`、`DONE.md` 未进入候选 diff。
- 本计划无当前必过 `expectation`；相关 `expectation.pass.dma_memory_hierarchy` / `expectation.pass.kernel_pattern_attach` 只作为历史 / 本地只读合同来源，merge 未运行或修改 expectation。

### 冲突处理

- 无冲突；任务 worktree 与 latest `origin/main` 对齐，候选为工作区 diff。

### 剩余风险

- 未发现 merge 阻断项。
- 最终合并提交号在 push 后回报，不再为补提交号追加任务记录提交。

### 结论

- `merge 可执行`；代码、spec、测试与本任务记录将同批暂存、提交、推送到 `origin/main`，随后执行 `-done` 并回报管理员。
