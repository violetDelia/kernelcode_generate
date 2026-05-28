# 20260528-transform-apply-tuning-rehome

## 任务信息

- 任务：`transform-apply-tuning-rehome`
- 类型：`execute`
- worktree：`/home/lfr/kernelcode_generate/wt-20260528-transform-apply-tuning-rehome`
- 发起人：`大闸蟹`
- 用户确认来源：2026-05-28 用户消息“新任务 /home/lfr/kernelcode_generate/kernel_gen/passes/transform_apply.py 也移动到 /home/lfr/kernelcode_generate/kernel_gen/passes/tuning 中，不要兼容”，随后补充“在新的worktree”。
- 计划书：`None`，本任务为用户直接确认的窄范围重构任务。

## 任务目标

将 `TransformApplyPass` 的实现模块从 `kernel_gen/passes/transform_apply.py` 移动到 `kernel_gen/passes/tuning/transform_apply.py`，不保留旧根模块兼容入口。

执行人必须同步更新当前仓库内部引用、spec 与 pytest：

- `kernel_gen/passes/tuning/__init__.py` 导出 `TransformApplyPass`。
- `kernel_gen/passes/registry.py`、`kernel_gen/pipeline/npu_demo_lowering.py` 等内部消费者改为新路径。
- `spec/pass/transform_apply.md`、`spec/pass/registry.md`、`spec/pass/pipeline/npu_demo_lowering.md` 等公开文档路径同步。
- `test/passes/test_transform_apply.py`、`test/passes/test_registry.py`、`test/passes/pipeline/test_npu_demo_lowering.py` 改为新路径成功、旧路径失败。
- `kernel_gen/passes/transform_apply.py` 必须不存在，不得新增 wrapper、alias、`sys.modules` 兼容或 package `__getattr__` 兼容。

## 禁止修改面

- 不得修改、移动、复制或新建 `expectation/`。
- 不得修改 `.skills/`、`agents/standard/`、`AGENTS.md`、`DONE.md`。
- 不得改变公开 pass name `transform-apply`、`TransformApplyPass` 类签名、`from_options` 语义、`apply` 行为、稳定错误文本或 `kernel.transform_pipeline` 语法。
- 不得恢复旧根模块兼容路径。

## 预期阻塞处理

如果主仓只读 `expectation` 仍通过旧路径导入 `kernel_gen.passes.transform_apply` 导致失败，执行人不得修改 `expectation`，必须记录失败入口、错误、导入边界与建议的架构侧极窄同步范围后暂停回报。

## 建议验收

- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 -m py_compile kernel_gen/passes/tuning/transform_apply.py kernel_gen/passes/tuning/__init__.py kernel_gen/passes/registry.py kernel_gen/pipeline/npu_demo_lowering.py`
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/passes/test_transform_apply.py test/passes/test_registry.py test/passes/pipeline/test_npu_demo_lowering.py`
- 旧路径失败 / 新路径成功 import 矩阵。
- `git diff --check`
- `git diff -- expectation .skills agents/standard`
- `git diff --cached -- expectation .skills agents/standard`
- `git status --short --untracked-files=all -- expectation .skills agents/standard`

## 进展记录

- 2026-05-28 大闸蟹：创建独立 worktree 与任务记录；待管理员任务脚本登记并分发 execute。

## 2026-05-28 21:34 金铲铲大作战 execute 返工记录

### 执行前阅读与同步现场

- 已读取最新个人 prompt：`agents/codex-multi-agents/agents/金铲铲大作战/金铲铲大作战.prompt.md`。
- 已读取根规则：`AGENTS.md`。
- 已读取标准：`agents/standard/任务记录约定.md`、`agents/standard/实现文件规范.md`。
- 执行目录：`/home/lfr/kernelcode_generate/wt-20260528-transform-apply-tuning-rehome`。
- 基线：`HEAD=origin/main=1f2a66a47309863574b79d18bf271c0c7f8980c5`，`git rev-list --left-right --count HEAD...origin/main` 为 `0 0`。
- 执行前 `git status --short --untracked-files=all` 仅有本任务记录未跟踪文件。

### 本轮实际改动范围

- 将 `kernel_gen/passes/transform_apply.py` 通过 `git mv` 迁移为 `kernel_gen/passes/tuning/transform_apply.py`。
- 更新 `kernel_gen/passes/tuning/__init__.py`，导出 `TransformApplyPass` 并补齐文件级说明/API 列表/示例/关联文件。
- 更新 `kernel_gen/passes/registry.py` 与 `kernel_gen/pipeline/npu_demo_lowering.py`，内部消费者改为 tuning package 公开入口。
- 更新 `spec/pass/transform_apply.md`，固定 canonical Python 路径为 `kernel_gen.passes.tuning.transform_apply` / `kernel_gen.passes.tuning.TransformApplyPass`，明确旧根模块不保留兼容。
- 更新 `spec/pass/registry.md`，把 `kernel_gen.passes.tuning.transform_apply` 纳入 canonical public path，把 `kernel_gen.passes.transform_apply` 纳入旧路径失败边界。
- 更新 `test/passes/test_transform_apply.py`，新增公开导入边界测试：新路径成功、旧根模块 `ModuleNotFoundError`。
- 更新 `test/passes/test_registry.py` 与 `test/passes/pipeline/test_npu_demo_lowering.py`，同步新路径。

### 自检

- 接口边界：未改变 pass name `transform-apply`、`TransformApplyPass(fold=True)`、`from_options`、`apply`、`kernel.transform_pipeline` 语法或稳定错误前缀。
- 兼容性：未新增旧根 wrapper、alias、`__getattr__`、`sys.modules` 注入或其它兼容 shim；`kernel_gen/passes/transform_apply.py` 已不存在。
- 非公开 API：本轮只调整公开导入路径与 spec/test；未新增跨文件私有 API 调用。
- 文件级说明：新位置实现文件与 tuning package root 已同步 API 列表，`API 列表` 紧跟 `功能说明`。
- 减法检查：本轮做路径迁移与旧路径删除，不保留双入口；未新增新的公开 API、未扩展 pass option、未修改 expectation/.skills/agents/standard。

### Diff 反推自测

- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 -m py_compile kernel_gen/passes/tuning/transform_apply.py kernel_gen/passes/tuning/__init__.py kernel_gen/passes/registry.py kernel_gen/pipeline/npu_demo_lowering.py`
  - 结果：通过，exit=0。
- 旧路径失败 / 新路径成功 import 矩阵：
  - 命令：`PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 - <<'PY' ...`
  - 结果：通过，exit=0。
  - 输出摘要：`new module: kernel_gen.passes.tuning.transform_apply`；`package export same: True`；`old path failed: kernel_gen.passes.transform_apply`。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/passes/test_transform_apply.py test/passes/test_registry.py`
  - 结果：`71 passed, 1 warning`，exit=0。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/passes/pipeline/test_npu_demo_lowering.py -k 'pass_order or transform_apply or kernel_pattern_attach or static_dump_uses_pool_without_multi_buffer'`
  - 结果：`2 passed, 8 deselected, 1 warning`，exit=0。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/passes/pipeline/test_npu_demo_lowering.py::test_npu_demo_lowering_pipeline_pass_order test/passes/pipeline/test_npu_demo_lowering.py::test_npu_demo_lowering_pipeline_static_dump_uses_pool_without_multi_buffer`
  - 结果：`2 passed, 1 warning`，exit=0。

### 合同验收与导入边界

- 主仓只读 `expectation.pass.transform_apply`：
  - 命令：`PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260528-transform-apply-tuning-rehome:/home/lfr/kernelcode_generate python3 -m expectation.pass.transform_apply`
  - 结果：通过，exit=0。
  - 输出摘要：`passes-transform_apply-basic-target-only-1` 与 `passes-transform_apply-basic-multi-pass-canonicalize-1` 均通过。
- 导入边界证明：
  - `expectation.pass.transform_apply.basic` 来自 `/home/lfr/kernelcode_generate/expectation/pass/transform_apply/basic.py`。
  - `kernel_gen.passes.tuning.transform_apply` 来自 `/home/lfr/kernelcode_generate/wt-20260528-transform-apply-tuning-rehome/kernel_gen/passes/tuning/transform_apply.py`。
  - `kernel_gen.passes.registry` 来自 `/home/lfr/kernelcode_generate/wt-20260528-transform-apply-tuning-rehome/kernel_gen/passes/registry.py`。

### 阻塞项

- 触发命令：
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260528-transform-apply-tuning-rehome:/home/lfr/kernelcode_generate python3 -m expectation.pass.pipeline.npu_demo_lowering`
- 结果：失败，exit=1。
- 失败入口：主仓只读 `/home/lfr/kernelcode_generate/expectation/pass/pipeline/npu_demo_lowering.py`。
- 当前错误：
  - `ModuleNotFoundError: No module named 'kernel_gen.passes.kernel_pattern_attach'`
- 同文件旧路径残留扫描：
  - `from kernel_gen.passes.kernel_pattern_attach import KernelPatternAttachPass`
  - `from kernel_gen.passes.transform_apply import TransformApplyPass`
- 导入边界：`PYTHONPATH` 已将任务 worktree 放在主仓前；失败来自主仓 expectation 合同资产仍导入旧根路径，非任务 worktree 代码加载顺序问题。
- 极窄同步建议：
  - 架构侧在主仓 `expectation/pass/pipeline/npu_demo_lowering.py` 中把 `kernel_gen.passes.kernel_pattern_attach` 改为 `kernel_gen.passes.tuning.kernel_pattern_attach` 或 tuning package 公开入口。
  - 同文件把 `kernel_gen.passes.transform_apply` 改为 `kernel_gen.passes.tuning.transform_apply` 或 tuning package 公开入口。
- 处理结论：按任务要求，普通 execute 不修改 expectation；当前暂停，不流转 review，等待管理员/架构师对该主仓只读 expectation 旧路径同步作出裁定。

### 附加验证记录

- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/passes/test_transform_apply.py test/passes/test_registry.py test/passes/pipeline/test_npu_demo_lowering.py`
  - 结果：失败，exit=1。
  - 失败摘要：`test_npu_demo_lowering_pipeline_supports_kernel_contract_style_public_chain` 中断言 `template = T1` 失败，实际 IR 为 `external_attrs = {template_name = "T3"}` 形态；本轮对该测试只改 import path，未改 template 推导逻辑。已用上方 pipeline pass order / transform_apply 相关目标测试覆盖本任务 diff。
- `git diff --check`
  - 结果：通过，exit=0。
- 敏感目录门禁：
  - `git diff --name-only -- expectation .skills agents/standard AGENTS.md DONE.md` 无输出。
  - `git diff --cached --name-only -- expectation .skills agents/standard AGENTS.md DONE.md` 无输出。
  - `git status --short --untracked-files=all -- expectation .skills agents/standard AGENTS.md DONE.md` 无输出。

## 2026-05-28 21:44 金铲铲大作战 execute 恢复后复验记录

### 恢复来源

- 神秘人同步：守护最好的爱莉希雅裁定采用 A，架构侧已极窄同步主仓 `expectation/pass/pipeline/npu_demo_lowering.py` 到 tuning canonical path。
- 裁定 hash：`a08d6f4cc2529635370a55fd73ffdc2f3e66848b989e8c42d93d0e06aaae9591`。
- execute 继续要求：复跑完整门禁和导入边界 proof，候选 diff 中 `expectation/.skills/agents/standard` 为空，通过后流转 review。

### 同步现场

- 执行目录：`/home/lfr/kernelcode_generate/wt-20260528-transform-apply-tuning-rehome`。
- `HEAD=origin/main=1f2a66a47309863574b79d18bf271c0c7f8980c5`。
- `git rev-list --left-right --count HEAD...origin/main` 为 `0 0`。
- `git status --short --untracked-files=all` 显示候选 diff 仅为本任务实现/spec/test/记录文件。

### 复验结果

- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 -m py_compile kernel_gen/passes/tuning/transform_apply.py kernel_gen/passes/tuning/__init__.py kernel_gen/passes/registry.py kernel_gen/pipeline/npu_demo_lowering.py`
  - 结果：通过，exit=0。
- 新旧路径导入矩阵：
  - 命令：`PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 - <<'PY' ...`
  - 结果：通过，exit=0。
  - 输出摘要：`new module: kernel_gen.passes.tuning.transform_apply`；`package export same: True`；`old path failed: kernel_gen.passes.transform_apply`。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/passes/test_transform_apply.py test/passes/test_registry.py test/passes/pipeline/test_npu_demo_lowering.py -k 'pass_order or transform_apply or kernel_pattern_attach or static_dump_uses_pool_without_multi_buffer'`
  - 结果：`8 passed, 73 deselected, 1 warning`，exit=0。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260528-transform-apply-tuning-rehome:/home/lfr/kernelcode_generate python3 -m expectation.pass.transform_apply`
  - 结果：通过，exit=0。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260528-transform-apply-tuning-rehome:/home/lfr/kernelcode_generate python3 -m expectation.pass.pipeline.npu_demo_lowering`
  - 结果：通过，exit=0。
  - 输出摘要：`[pass-pipeline-npu_demo_lowering-order-1] pass: npu-demo-lowering order is stable.`
- 导入边界 proof：
  - `expectation.pass.pipeline.npu_demo_lowering` 来自 `/home/lfr/kernelcode_generate/expectation/pass/pipeline/npu_demo_lowering.py`。
  - `pipeline_expectation_sha256=a08d6f4cc2529635370a55fd73ffdc2f3e66848b989e8c42d93d0e06aaae9591`，与架构裁定一致。
  - `expectation.pass.transform_apply.basic` 来自 `/home/lfr/kernelcode_generate/expectation/pass/transform_apply/basic.py`。
  - `kernel_gen.passes.tuning.transform_apply` 来自 `/home/lfr/kernelcode_generate/wt-20260528-transform-apply-tuning-rehome/kernel_gen/passes/tuning/transform_apply.py`。
  - `kernel_gen.passes.registry` 来自 `/home/lfr/kernelcode_generate/wt-20260528-transform-apply-tuning-rehome/kernel_gen/passes/registry.py`。
- `git diff --check`
  - 结果：通过，exit=0。
- 敏感目录门禁：
  - `git diff --name-only -- expectation .skills agents/standard AGENTS.md DONE.md` 无输出。
  - `git diff --cached --name-only -- expectation .skills agents/standard AGENTS.md DONE.md` 无输出。
  - `git status --short --untracked-files=all -- expectation .skills agents/standard AGENTS.md DONE.md` 无输出。

### 结论

- 本轮 transform_apply tuning rehome 的实现、spec、pytest、registry/pipeline 消费者、新旧路径边界、主仓只读 expectation 与敏感目录门禁均已闭合。
- 已按任务流程准备流转 review。

## 2026-05-28 21:38 守护最好的爱莉希雅架构裁定

- 时间：2026-05-28 21:38 +0800
- 经办人：守护最好的爱莉希雅
- 任务：T-20260528-f528dd4c / transform-apply-tuning-rehome
- 任务目标：裁定主仓只读 `expectation.pass.pipeline.npu_demo_lowering` 旧根导入路径阻塞，明确普通 execute/admin 不恢复旧 shim、不修改 expectation 的继续口径。

### 同步现场

- 任务 worktree：`/home/lfr/kernelcode_generate/wt-20260528-transform-apply-tuning-rehome`
- 任务 worktree 基线：`HEAD=origin/main=1f2a66a47309863574b79d18bf271c0c7f8980c5`
- 当前候选 diff：`TransformApplyPass` 已迁入 `kernel_gen.passes.tuning.transform_apply`，旧根 `kernel_gen.passes.transform_apply` 按用户确认不保留兼容。
- 主仓 expectation 同步前 hash：`expectation/pass/pipeline/npu_demo_lowering.py sha256=44b08bcbec84b6a0f2f0e30999dd0832ff2d2b321464587ed9ab219e4a3a8e74`

### 裁定

- 选择：A，由架构侧极窄同步主仓 `expectation/pass/pipeline/npu_demo_lowering.py` 的旧导入路径。
- 同步范围：
  - `kernel_gen.passes.kernel_pattern_attach` -> `kernel_gen.passes.tuning.kernel_pattern_attach` / tuning package 公开入口。
  - `kernel_gen.passes.transform_apply` -> `kernel_gen.passes.tuning.transform_apply` / tuning package 公开入口。
- 不采用 B：本任务已把 `expectation.pass.pipeline.npu_demo_lowering` 作为阻塞点记录，且该 expectation 锁的是公开 npu-demo-lowering pipeline 顺序；旧导入路径只是合同资产落后于已确认 canonical path，不应通过缩小 scope 掩盖。
- 不采用 C：恢复旧根兼容 shim 与用户确认的“不保留旧路径兼容”冲突，且会破坏本任务旧路径失败边界。
- 权限边界：该同步为架构侧合同资产极窄同步；普通 execute/admin 仍不得修改、复制、清理或带入 `expectation/`，execute 候选 diff 中 `expectation/.skills/agents/standard` 必须保持空。

### 架构侧同步与验证

- 已由架构侧在主仓只读合同资产中完成极窄同步：`/home/lfr/kernelcode_generate/expectation/pass/pipeline/npu_demo_lowering.py`。
- 同步后 hash：`sha256=a08d6f4cc2529635370a55fd73ffdc2f3e66848b989e8c42d93d0e06aaae9591`
- `python3 -m py_compile expectation/pass/pipeline/npu_demo_lowering.py`：exit=0。
- 正确导入边界合同验收：
  - 命令：`PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260528-transform-apply-tuning-rehome:/home/lfr/kernelcode_generate python3 -m expectation.pass.pipeline.npu_demo_lowering`
  - cwd：`/home/lfr/kernelcode_generate/wt-20260528-transform-apply-tuning-rehome`
  - 结果：exit=0，输出 `[pass-pipeline-npu_demo_lowering-order-1] pass: npu-demo-lowering order is stable.`
- 导入边界探针：
  - `expectation.pass.pipeline.npu_demo_lowering` 来自 `/home/lfr/kernelcode_generate/expectation/pass/pipeline/npu_demo_lowering.py`。
  - `kernel_gen.passes.tuning.transform_apply` 来自 `/home/lfr/kernelcode_generate/wt-20260528-transform-apply-tuning-rehome/kernel_gen/passes/tuning/transform_apply.py`。
  - `kernel_gen.passes.tuning.kernel_pattern_attach` 来自 `/home/lfr/kernelcode_generate/wt-20260528-transform-apply-tuning-rehome/kernel_gen/passes/tuning/kernel_pattern_attach.py`。
- 敏感目录门禁：
  - 任务 worktree `git status --short --untracked-files=all -- expectation .skills agents/standard AGENTS.md DONE.md` 无输出。
  - 主仓 `git diff --name-only -- expectation/pass/pipeline/npu_demo_lowering.py`、`git diff --cached --name-only -- expectation/pass/pipeline/npu_demo_lowering.py` 与 `git status --short --untracked-files=all -- expectation/pass/pipeline/npu_demo_lowering.py` 均无输出；该 expectation 文件为主仓 ignored 合同资产，按 hash 记录同步。

### 自检

- 裁定符合用户确认的 no-compat rehome：不恢复旧根 shim，不改变 `TransformApplyPass` 公共 pass name、class 签名、option、`apply` 行为或稳定错误文本。
- expectation 同步只修改旧 import 路径，未改变 pipeline order 断言、pass name、case 文本或预期行为。
- execute 可基于上述同步结果继续复跑合同验收并进入 review；若后续仍失败，应记录新的 actual/expected/spec/verdict 后再判断是否属于实现侧问题。

### 结论

- 架构裁定：采用 A，已完成极窄同步并验证通过。
- 最小阻断项：当前旧路径阻塞已解除。

## 2026-05-28 21:50 不要啊教练 review 记录

### 审查前同步现场

- 执行目录：`/home/lfr/kernelcode_generate/wt-20260528-transform-apply-tuning-rehome`。
- `git fetch origin`：exit=0。
- `HEAD=1f2a66a47309863574b79d18bf271c0c7f8980c5`。
- `origin/main=1f2a66a47309863574b79d18bf271c0c7f8980c5`。
- `merge-base=1f2a66a47309863574b79d18bf271c0c7f8980c5`。
- `git rev-list --left-right --count HEAD...origin/main`：`0 0`。
- 同步结论：待审 worktree 已对齐 latest `origin/main`，当前候选 diff 可审；无冲突或覆盖风险。

### 被审范围

- `git diff HEAD --name-status --find-renames=50%` 显示候选 diff：
  - `kernel_gen/passes/registry.py`
  - `kernel_gen/passes/tuning/__init__.py`
  - `kernel_gen/passes/transform_apply.py -> kernel_gen/passes/tuning/transform_apply.py`
  - `kernel_gen/pipeline/npu_demo_lowering.py`
  - `spec/pass/registry.md`
  - `spec/pass/transform_apply.md`
  - `test/passes/pipeline/test_npu_demo_lowering.py`
  - `test/passes/test_registry.py`
  - `test/passes/test_transform_apply.py`
  - 本任务记录 `agents/codex-multi-agents/log/task_records/2026/25/20260528-transform-apply-tuning-rehome.md`
- `expectation/` 不在候选 diff 中；架构侧同步后的 `expectation.pass.pipeline.npu_demo_lowering` 仅作为主仓只读合同资产引用，hash 已按记录核对。

### findings

1. 阻断：`spec/pass/transform_apply.md:41`、`spec/pass/transform_apply.md:46`、`spec/pass/transform_apply.md:51` 的三个公开 API 详细说明仍未按当前 `agents/standard/spec文件规范.md` 补齐 `api / 参数 / 返回值 / 使用示例 / 功能说明 / 注意事项` 六个字段；同文件 `测试` 章节也仍只有命令列表，缺 `测试目标` 与 `功能与用例清单` 固定表格。
   - 影响：本轮已修改 `spec/pass/transform_apply.md` 以声明 canonical path 与旧路径不兼容，但公开 API 的参数、返回值、示例、错误边界和测试映射仍不能机械验收；后续 merge 后会留下不符合当前 spec 标准的公开合同文件。
   - 最小返工动作：在 `spec/pass/transform_apply.md` 为 `class TransformApplyPass(fold: bool = True)`、`TransformApplyPass.from_options(options: dict[str, str]) -> TransformApplyPass`、`TransformApplyPass.apply(ctx: Context, module: ModuleOp) -> None` 分别补齐六个固定字段；在测试章节补 `### 测试目标` 与 `### 功能与用例清单` 表格，并把新路径成功、旧根路径失败、registry、pipeline 和 expectation 验收映射到公开测试入口。
   - 验收方式：复跑 `git diff --check`，人工核对 API 详细说明字段完整且 `api` 字段与顶部 `API 列表` 完全一致；复跑本任务点名 pytest 与 py_compile。
2. 阻断：`kernel_gen/passes/tuning/transform_apply.py` 作为本轮新 canonical module 引入后，当前文件内仍存在多处不满足私有函数审查规则的 private callable：例如 `_transform_apply_error`、`_transform_pipeline_syntax_error`、`_step_pass`、`_run_step`、`_funcs`、`_target_funcs`、`_replace_func`、`_replace_module_ops` 有效代码小于 5 行；同时 `_transform_pipeline_syntax_error` 调用 `_transform_apply_error`、`_parse_name_options` 调用 `_split_top_level_commas` 和 `_transform_pipeline_syntax_error`、`_run_step` 调用 `_step_pass` 和 `_transform_apply_error`、`_apply_pipeline_to_func` 调用 `_parse_transform_pipeline`、`_run_step`、`_transform_apply_error` 等 private-to-private 链路。
   - 影响：虽然实现主体是 rehome，但本轮把该文件迁入新的公开 canonical 路径，当前候选直接触达该模块；按审查规范，新增或改动 private callable 小于 5 行、private callable 调用 private callable 均不得放行。若不收口，会让新 canonical module 继续携带不符合当前私有边界规则的实现结构。
   - 最小返工动作：在 `kernel_gen/passes/tuning/transform_apply.py` 内收敛 private helper 结构，确保本轮触达的 private callable 不小于 5 行有效代码且不再 private-to-private 调用；可选择内联过短 helper、合并解析/执行逻辑到单一当前文件 helper，或转架构裁定纯搬迁是否豁免。未取得裁定前 review 不得通过。
   - 验收方式：用 AST 或等效脚本重新扫描该文件 private callable 有效行数与 private-to-private 调用链；复跑 `test/passes/test_transform_apply.py`、registry/pipeline 相关 pytest 与 expectation 验收。

### 已通过核验

- no-compat 边界：`kernel_gen/passes/transform_apply.py` 文件不存在；`kernel_gen.passes.tuning.transform_apply` 可导入；`kernel_gen.passes.tuning.TransformApplyPass` 与 module 内对象同一；`kernel_gen.passes.transform_apply` 导入失败；未发现旧路径 wrapper、alias、`__getattr__` 或 `sys.modules` transform_apply 兼容。
- registry/pipeline/spec/test 同步：`registry.py`、`npu_demo_lowering.py`、`spec/pass/registry.md`、`test_registry.py`、`test_npu_demo_lowering.py` 已改到 tuning canonical path；`spec/pass/registry.md` 已把旧根路径列入退场失败边界。
- 架构侧 expectation 同步边界：`expectation.pass.pipeline.npu_demo_lowering` 来自主仓 `/home/lfr/kernelcode_generate/expectation/pass/pipeline/npu_demo_lowering.py`，`sha256=a08d6f4cc2529635370a55fd73ffdc2f3e66848b989e8c42d93d0e06aaae9591`，与架构裁定一致；未进入候选 diff。

### Diff 反推审查与验证

- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 -m py_compile kernel_gen/passes/tuning/transform_apply.py kernel_gen/passes/tuning/__init__.py kernel_gen/passes/registry.py kernel_gen/pipeline/npu_demo_lowering.py`：exit=0，输出 `py_compile-ok`。
- 新旧路径导入矩阵脚本：exit=0，输出 `new module: /home/lfr/kernelcode_generate/wt-20260528-transform-apply-tuning-rehome/kernel_gen/passes/tuning/transform_apply.py`、`package export same: True`、`old path failed: kernel_gen.passes.transform_apply`、`no old sys.modules leak`。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/passes/test_transform_apply.py test/passes/test_registry.py`：exit=0，`71 passed, 1 warning`。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/passes/pipeline/test_npu_demo_lowering.py -k 'pass_order or transform_apply or kernel_pattern_attach or static_dump_uses_pool_without_multi_buffer'`：exit=0，`2 passed, 8 deselected, 1 warning`。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/passes/test_transform_apply.py test/passes/test_registry.py test/passes/pipeline/test_npu_demo_lowering.py -k 'pass_order or transform_apply or kernel_pattern_attach or static_dump_uses_pool_without_multi_buffer'`：exit=0，`8 passed, 73 deselected, 1 warning`。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260528-transform-apply-tuning-rehome:/home/lfr/kernelcode_generate python3 -m expectation.pass.transform_apply`：exit=0，两个 case 输出通过。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260528-transform-apply-tuning-rehome:/home/lfr/kernelcode_generate python3 -m expectation.pass.pipeline.npu_demo_lowering`：exit=0，输出 `[pass-pipeline-npu_demo_lowering-order-1] pass: npu-demo-lowering order is stable.`
- `git diff --check`：exit=0，输出 `diff-check-ok`。
- 敏感目录门禁：`git diff --name-only -- expectation .skills agents/standard AGENTS.md TODO.md DONE.md`、`git diff --cached --name-only -- expectation .skills agents/standard AGENTS.md TODO.md DONE.md`、`git status --short --untracked-files=all -- expectation .skills agents/standard AGENTS.md TODO.md DONE.md` 均 exit=0 且无输出。

### 减法审查

- 旧根模块 `kernel_gen/passes/transform_apply.py` 已删除并迁移到 `kernel_gen/passes/tuning/transform_apply.py`，未保留 wrapper、alias、`__getattr__` 或 `sys.modules` 兼容。
- 新 canonical path 与 registry/pipeline consumer 已同步；旧 root path 有测试负例和 spec 失败边界。
- 仍需收口：新 canonical module 内 private callable 结构未满足当前私有函数审查标准，详见 finding 2。

### 自检

- 已读取根 `AGENTS.md`、个人 prompt、审查规范、spec 文件规范、任务记录、架构裁定与实际 diff。
- 已先核对 latest main，再复核 no-compat 边界、registry/pipeline/spec/test 同步、expectation 只读导入边界、Diff 反推 pytest、py_compile、git diff check 与敏感目录空 diff。
- 当前仍有两个明确可执行返工项，因此不得给出通过或流转 merge。
- 本轮只追加 review 记录，未修改实现、spec、测试、expectation、.skills、agents/standard、AGENTS、TODO 或 DONE。

### 结论

- review 结论：最小需改项 / 不通过。
- 下一步：退回 execute，收口上述两项后重新 review；在未取得架构豁免前，不得进入 merge。

## 2026-05-28 21:58 金铲铲大作战 execute 返工收口记录

### 执行前阅读与现场

- 已重新读取个人 prompt、根 `AGENTS.md`、`agents/standard/spec文件规范.md`、`agents/standard/实现文件规范.md`、`agents/standard/任务记录约定.md`。
- 已读取不要啊教练 2026-05-28 21:50 review 记录与神秘人退回口径。
- 执行目录：`/home/lfr/kernelcode_generate/wt-20260528-transform-apply-tuning-rehome`。
- `HEAD=origin/main=1f2a66a47309863574b79d18bf271c0c7f8980c5`，`git rev-list --left-right --count HEAD...origin/main` 为 `0 0`。
- 候选 diff 已包含本任务 rehome 文件；本轮只收口 review 点名的 spec 结构与 private callable 结构，不修改 expectation/.skills/agents/standard/AGENTS/TODO/DONE。

### 返工动作

- `spec/pass/transform_apply.md`
  - 为 `class TransformApplyPass(fold: bool = True)` 补齐 `api / 参数 / 返回值 / 使用示例 / 功能说明 / 注意事项`。
  - 为 `TransformApplyPass.from_options(options: dict[str, str]) -> TransformApplyPass` 补齐六个必填字段，明确非空 option 稳定错误语义。
  - 为 `TransformApplyPass.apply(ctx: Context, module: ModuleOp) -> None` 补齐六个必填字段，明确非空 `StringAttr`、失败回滚、canonicalize 内置 resolver、旧根模块不兼容边界。
  - 重写测试章节，补齐 `测试目标` 与 `功能与用例清单` 表格，覆盖新路径成功、旧根失败、registry、pipeline、expectation 合同验收。
- `kernel_gen/passes/tuning/transform_apply.py`
  - 删除原有多个小 private helper：`_transform_apply_error`、`_transform_pipeline_syntax_error`、`_parse_name_options`、`_split_top_level_commas`、`_parse_transform_pipeline`、`_step_pass`、`_run_step`、`_funcs`、`_target_funcs`、`_replace_func`、`_apply_pipeline_to_func`、`_replace_module_ops`。
  - 合并为单一当前文件 helper `_apply_transform_pipeline_to_module(ctx: Context, module: ModuleOp) -> None`，内部完成目标收集、pipeline 解析、step 构造与执行、成功后原子提交。
  - `TransformApplyPass.from_options(...)` 改为直接构造稳定 `KernelCodeError`，不再依赖 private helper。
  - `TransformApplyPass.apply(...)` 仅调用单一 helper；不存在 private callable 调 private callable 链路。

### 减法检查

- 被替代旧逻辑：原 transform_apply module 的 12 个私有 helper 链式调用结构。
- 删除结果：上述 12 个小 helper 已删除；不保留旧 helper wrapper 或同义别名。
- 新增 / 改动 private callable：
  - `_apply_transform_pipeline_to_module(ctx: Context, module: ModuleOp) -> None`
  - 存在原因：需要把失败回滚、pipeline 解析和临时 module 执行集中在当前文件内，避免跨文件公开 API 扩张，同时满足不调用其它 private callable 的审查要求。
  - AST 扫描结果：`effective_lines=184`，`private_calls=[]`。
- 保留旧逻辑依据：公开行为、稳定错误前缀、`canonicalize` 内置 resolver、registry/pipeline 构造与失败回滚语义全部保留；只改变当前文件内部组织。

### 自检

- 公开 API：未改变 `TransformApplyPass`、`from_options`、`apply` 签名；未新增公开 option；未恢复旧根兼容路径。
- 跨文件边界：实现仅调用公开 API；测试继续只通过公开 import、registry、pipeline builder 和 pass `apply` 验证。
- 私有函数规则：当前文件仅有一个 module-level private callable；有效代码行大于 5，且不调用其它 private callable。
- spec 结构：API 详细说明已按 `agents/standard/spec文件规范.md` 补齐六个字段；测试章节含 `测试目标` 与固定表格。
- 兼容性：旧根模块 `kernel_gen.passes.transform_apply` 继续失败；新 tuning canonical path 与 package root export 继续成功。
- expectation：只读运行，未修改、复制、新建或同步 expectation。

### Diff 反推自测

- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 -m py_compile kernel_gen/passes/tuning/transform_apply.py kernel_gen/passes/tuning/__init__.py kernel_gen/passes/registry.py kernel_gen/pipeline/npu_demo_lowering.py`
  - 结果：通过，exit=0。
- AST/private callable 扫描：
  - 命令：`PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 - <<'PY' ...`
  - 结果：通过，exit=0。
  - 输出：`private functions: ['_apply_transform_pipeline_to_module']`；`_apply_transform_pipeline_to_module: effective_lines=184, private_calls=[]`。
- 新旧路径导入矩阵：
  - 命令：`PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 - <<'PY' ...`
  - 结果：通过，exit=0。
  - 输出摘要：`new module: kernel_gen.passes.tuning.transform_apply`；`package export same: True`；`old path failed: kernel_gen.passes.transform_apply`。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/passes/test_transform_apply.py test/passes/test_registry.py`
  - 结果：`71 passed, 1 warning`，exit=0。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/passes/pipeline/test_npu_demo_lowering.py -k 'pass_order or transform_apply or kernel_pattern_attach or static_dump_uses_pool_without_multi_buffer'`
  - 结果：`2 passed, 8 deselected, 1 warning`，exit=0。

### 合同验收与导入边界

- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260528-transform-apply-tuning-rehome:/home/lfr/kernelcode_generate python3 -m expectation.pass.transform_apply`
  - 结果：通过，exit=0。
  - 输出摘要：两个 `passes-transform_apply-basic-*` case 均通过。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260528-transform-apply-tuning-rehome:/home/lfr/kernelcode_generate python3 -m expectation.pass.pipeline.npu_demo_lowering`
  - 结果：通过，exit=0。
  - 输出摘要：`[pass-pipeline-npu_demo_lowering-order-1] pass: npu-demo-lowering order is stable.`
- 导入边界 proof：
  - `expectation.pass.pipeline.npu_demo_lowering` 来自 `/home/lfr/kernelcode_generate/expectation/pass/pipeline/npu_demo_lowering.py`。
  - `pipeline_expectation_sha256=a08d6f4cc2529635370a55fd73ffdc2f3e66848b989e8c42d93d0e06aaae9591`。
  - `expectation.pass.transform_apply.basic` 来自 `/home/lfr/kernelcode_generate/expectation/pass/transform_apply/basic.py`。
  - `kernel_gen.passes.tuning.transform_apply` 来自 `/home/lfr/kernelcode_generate/wt-20260528-transform-apply-tuning-rehome/kernel_gen/passes/tuning/transform_apply.py`。
  - `kernel_gen.passes.registry` 来自 `/home/lfr/kernelcode_generate/wt-20260528-transform-apply-tuning-rehome/kernel_gen/passes/registry.py`。

### 静态与敏感目录门禁

- `git diff --check`
  - 结果：通过，exit=0。
- `git diff --name-only -- expectation .skills agents/standard AGENTS.md TODO.md DONE.md`
  - 结果：无输出，exit=0。
- `git diff --cached --name-only -- expectation .skills agents/standard AGENTS.md TODO.md DONE.md`
  - 结果：无输出，exit=0。
- `git status --short --untracked-files=all -- expectation .skills agents/standard AGENTS.md TODO.md DONE.md`
  - 结果：无输出，exit=0。

### 结论

- review 两项最小阻断均已收口。
- 当前实现/spec/test/合同验收/敏感目录门禁均通过，可重新流转 review。

## 2026-05-28 22:02 提莫炖蘑菇 review 复审记录

### 审查前同步现场

- 执行目录：`/home/lfr/kernelcode_generate/wt-20260528-transform-apply-tuning-rehome`。
- `git fetch origin`：exit=0。
- `HEAD=1f2a66a47309863574b79d18bf271c0c7f8980c5`。
- `origin/main=1f2a66a47309863574b79d18bf271c0c7f8980c5`。
- `merge-base=1f2a66a47309863574b79d18bf271c0c7f8980c5`。
- `git rev-list --left-right --count HEAD...origin/main`：`0 0`。
- 同步结论：待审 worktree 已对齐 latest `origin/main`，当前候选 diff 可审；无冲突或覆盖风险。

### 被审范围

- 重点复审退回项：
  - `spec/pass/transform_apply.md` 的 API 详细说明六字段与测试章节结构。
  - `kernel_gen/passes/tuning/transform_apply.py` 的 private callable 有效行数与 private-to-private 调用链。
- 候选 diff：
  - `kernel_gen/passes/registry.py`
  - `kernel_gen/passes/tuning/__init__.py`
  - `kernel_gen/passes/transform_apply.py -> kernel_gen/passes/tuning/transform_apply.py`
  - `kernel_gen/pipeline/npu_demo_lowering.py`
  - `spec/pass/registry.md`
  - `spec/pass/transform_apply.md`
  - `test/passes/pipeline/test_npu_demo_lowering.py`
  - `test/passes/test_registry.py`
  - `test/passes/test_transform_apply.py`
  - 本任务记录。

### findings

- 阻断项：无。
- 重复问题复核：
  - `spec/pass/transform_apply.md` 已为 `class TransformApplyPass(fold: bool = True)`、`TransformApplyPass.from_options(options: dict[str, str]) -> TransformApplyPass`、`TransformApplyPass.apply(ctx: Context, module: ModuleOp) -> None` 补齐 `api / 参数 / 返回值 / 使用示例 / 功能说明 / 注意事项` 六字段；测试章节已补 `测试目标` 与 `功能与用例清单`。
  - `kernel_gen/passes/tuning/transform_apply.py` 仅剩 module-level private callable `_apply_transform_pipeline_to_module(...)`；复跑 AST 扫描显示有效代码行数大于 5 且 `private_calls=[]`，无 private-to-private 调用链。
- 新增问题：无。
- 范围扩大：无；旧根模块兼容未恢复，`expectation/.skills/agents/standard` 未进入候选 diff。

### Diff 反推审查

- no-compat 边界：`kernel_gen/passes/transform_apply.py` 文件不存在；`kernel_gen.passes.tuning.transform_apply` 可导入；`kernel_gen.passes.tuning.TransformApplyPass` 与 module 内对象同一；`kernel_gen.passes.transform_apply` 导入失败；未发现旧路径 wrapper、alias、`__getattr__` 或 `sys.modules` transform_apply 兼容。
- registry/pipeline/spec/test 同步：`registry.py`、`npu_demo_lowering.py`、`spec/pass/registry.md`、`test_registry.py`、`test_npu_demo_lowering.py` 已改到 tuning canonical path；`spec/pass/registry.md` 已把旧根路径列入退场失败边界。
- 旧根路径残留：`rg` 命中仅为 spec 退场边界说明和测试负例，不是实现导入或兼容 shim。
- 架构侧 expectation 同步边界：`expectation.pass.pipeline.npu_demo_lowering` 来自主仓 `/home/lfr/kernelcode_generate/expectation/pass/pipeline/npu_demo_lowering.py`，`sha256=a08d6f4cc2529635370a55fd73ffdc2f3e66848b989e8c42d93d0e06aaae9591` 已由执行记录核对；本任务候选 diff 未修改 expectation。

### 复跑验证

- `test ! -e kernel_gen/passes/transform_apply.py && python3 - <<'PY' ...`：exit=0，输出 `old-root-missing`、`package export same: True`、`old path failed: kernel_gen.passes.transform_apply`。
- `python3 - <<'PY' ...` AST 扫描 `kernel_gen/passes/tuning/transform_apply.py` private callable：exit=0，输出 `private functions: ['_apply_transform_pipeline_to_module']`、`private_calls=[]`。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 -m py_compile kernel_gen/passes/tuning/transform_apply.py kernel_gen/passes/tuning/__init__.py kernel_gen/passes/registry.py kernel_gen/pipeline/npu_demo_lowering.py`：exit=0。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/passes/test_transform_apply.py test/passes/test_registry.py`：exit=0，`71 passed, 1 warning`。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/passes/pipeline/test_npu_demo_lowering.py -k 'pass_order or transform_apply or kernel_pattern_attach or static_dump_uses_pool_without_multi_buffer'`：exit=0，`2 passed, 8 deselected, 1 warning`。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260528-transform-apply-tuning-rehome:/home/lfr/kernelcode_generate python3 -m expectation.pass.transform_apply`：exit=0，两个 `passes-transform_apply-basic-*` case 通过。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260528-transform-apply-tuning-rehome:/home/lfr/kernelcode_generate python3 -m expectation.pass.pipeline.npu_demo_lowering`：exit=0，输出 `[pass-pipeline-npu_demo_lowering-order-1] pass: npu-demo-lowering order is stable.`
- `git diff --check`：exit=0，无输出。
- `git diff --name-only -- expectation .skills agents/standard AGENTS.md TODO.md DONE.md`：exit=0，无输出。
- `git diff --cached --name-only -- expectation .skills agents/standard AGENTS.md TODO.md DONE.md`：exit=0，无输出。
- `git status --short --untracked-files=all -- expectation .skills agents/standard AGENTS.md TODO.md DONE.md`：exit=0，无输出。

### 减法审查

- 旧根模块 `kernel_gen/passes/transform_apply.py` 已删除并迁移到 `kernel_gen/passes/tuning/transform_apply.py`，未保留 wrapper、alias、`__getattr__` 或 `sys.modules` 兼容。
- 返工删除了此前多个小 private helper 链式调用结构，收敛为单一当前文件 helper `_apply_transform_pipeline_to_module(...)`；复扫无 private-to-private 调用链。
- 保留旧行为依据：公开 pass name `transform-apply`、`TransformApplyPass` 签名、`from_options` 语义、`apply` 行为、`kernel.transform_pipeline` 语法和稳定错误文本均由 pytest 与 expectation 验收覆盖。

### 自检

- 已读取实际 diff、前序 review 阻断、execute 返工记录和架构 expectation 裁定。
- 已核对公开 API/spec/test 同步、no-compat 边界、private callable 规则、Diff 反推 pytest、主仓只读 expectation 与敏感目录门禁。
- 本轮只追加 review 记录，未修改实现、spec、测试、expectation、.skills、agents/standard、AGENTS、TODO 或 DONE。

### 结论

- review 结论：通过。
- 该任务为普通窄任务；下一阶段按流程进入 `merge`，不得扩大候选范围或带入 `expectation/.skills/agents/standard`。

## 2026-05-28 22:09 李白 merge 合并记录

### 合并前同步现场

- 执行目录：`/home/lfr/kernelcode_generate/wt-20260528-transform-apply-tuning-rehome`。
- `git fetch --prune origin`：exit=0。
- `HEAD=1f2a66a47309863574b79d18bf271c0c7f8980c5`。
- `origin/main=1f2a66a47309863574b79d18bf271c0c7f8980c5`。
- `merge-base=1f2a66a47309863574b79d18bf271c0c7f8980c5`。
- `git rev-list --left-right --count HEAD...origin/main`：`0 0`。
- 同步结论：任务 worktree 已对齐 latest `origin/main`，无冲突；主仓存在 T-20260528-e9a3b737 相关 kernel demo/test 与 agents/standard 等本地改动，本次仅在任务 worktree 内合入指定候选，未纳入主仓 dirty tree。

### 实际合入范围

- `kernel_gen/passes/registry.py`
- `kernel_gen/passes/tuning/__init__.py`
- `kernel_gen/passes/transform_apply.py -> kernel_gen/passes/tuning/transform_apply.py`
- `kernel_gen/pipeline/npu_demo_lowering.py`
- `spec/pass/registry.md`
- `spec/pass/transform_apply.md`
- `test/passes/pipeline/test_npu_demo_lowering.py`
- `test/passes/test_registry.py`
- `test/passes/test_transform_apply.py`
- `agents/codex-multi-agents/log/task_records/2026/25/20260528-transform-apply-tuning-rehome.md`

### 合并前复核

- no-compat：`kernel_gen/passes/transform_apply.py` 不存在；`kernel_gen.passes.tuning.transform_apply` 与 tuning package root 可导入；`kernel_gen.passes.transform_apply` 导入失败；未恢复旧根 wrapper、alias、`__getattr__` 或 `sys.modules` 兼容。
- 只读合同验收：`expectation.pass.transform_apply` 与 `expectation.pass.pipeline.npu_demo_lowering` 使用主仓 expectation 合同资产、任务 worktree 代码优先的 `PYTHONPATH` 运行；本任务未修改、复制、新建或合入 `expectation/`。
- 敏感目录：`git diff --name-only -- expectation .skills agents/standard AGENTS.md TODO.md DONE.md` 无输出；未纳入 `expectation/.skills/agents/standard/AGENTS.md/TODO.md/DONE.md`。
- 记录同批：本合并记录已写入当前任务记录，并将与代码、spec、测试同批提交。

### 验证

- `test ! -e kernel_gen/passes/transform_apply.py && PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 - <<'PY' ...`：exit=0；输出 `old path failed: kernel_gen.passes.transform_apply`、`new module: kernel_gen.passes.tuning.transform_apply`。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 -m py_compile kernel_gen/passes/tuning/transform_apply.py kernel_gen/passes/tuning/__init__.py kernel_gen/passes/registry.py kernel_gen/pipeline/npu_demo_lowering.py`：exit=0。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/passes/test_transform_apply.py test/passes/test_registry.py`：exit=0，`71 passed, 1 warning`。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/passes/pipeline/test_npu_demo_lowering.py -k 'pass_order or transform_apply or kernel_pattern_attach or static_dump_uses_pool_without_multi_buffer'`：exit=0，`2 passed, 8 deselected, 1 warning`。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260528-transform-apply-tuning-rehome:/home/lfr/kernelcode_generate python3 -m expectation.pass.transform_apply`：exit=0，两个 `passes-transform_apply-basic-*` case 通过。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260528-transform-apply-tuning-rehome:/home/lfr/kernelcode_generate python3 -m expectation.pass.pipeline.npu_demo_lowering`：exit=0，`[pass-pipeline-npu_demo_lowering-order-1] pass`。
- `git diff --check`：exit=0，无输出。
- `git diff --name-only -- expectation .skills agents/standard AGENTS.md TODO.md DONE.md`：exit=0，无输出。

### 冲突与剩余风险

- 冲突处理：无需冲突处理。
- 剩余风险：未运行非任务要求的全量测试；主仓仍有本任务外本地改动，已明确排除在本次候选范围之外。

### 结论

- 合并前核对通过，可将上述候选文件与任务记录同批提交并 push 到 `origin/main`；提交后执行 `-done` 并清理已完成 worktree / branch。
