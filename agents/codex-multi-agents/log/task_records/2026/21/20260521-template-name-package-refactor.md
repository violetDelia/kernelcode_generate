时间：2026-05-22 01:56 CST
经办人：睡觉小分队
任务：T-20260522-705c8fcf / template-name-package-refactor / execute
任务目标：将 template-name 推导真实实现搬入 `kernel_gen/passes/template_name/` 内部目录，旧公开根模块保留兼容薄壳；同步 spec、文件级 API 列表、registry/pipeline 内部导入、pytest，并只读运行主仓 `expectation.pass.template_name_infer`。

执行前阅读记录：
- 已读取最新个人提示词 `agents/codex-multi-agents/agents/睡觉小分队/睡觉小分队.prompt.md`、根 `AGENTS.md`、`agents/standard/任务记录约定.md`、`agents/standard/实现文件规范.md`、`agents/standard/测试文件约定.md`。
- 已读取主仓计划书 `/home/lfr/kernelcode_generate/ARCHITECTURE/plan/template_name_package_refactor_green_plan.md`。目标 worktree 不包含该计划资产，本轮仅只读引用主仓计划正文。
- 已核对计划 S1-S4：S1 spec 与公开兼容合同；S2 搬迁真实实现；S3 保留旧公开入口并补导入矩阵测试；S4 template-name pytest、registry/pipeline pytest、主仓只读 expectation、import proof、静态扫描与敏感目录门禁。
- 已核对同步基线：执行目录 `/home/lfr/kernelcode_generate/wt-20260521-template-name-package-refactor`；`HEAD=origin/main=merge-base=1b8e9629446ff78fc7d9216000c06dab9d0b52d8`；初始 worktree 干净。

改动：
- 新增内部真实实现目录 `kernel_gen/passes/template_name/`，包含 `__init__.py`、`graph.py`、`constraints.py`、`default_constraints.py`、`infer.py`。
- 四个旧公开根模块 `kernel_gen/passes/template_name_graph.py`、`template_name_constraints.py`、`template_name_default_constraints.py`、`template_name_infer.py` 改为薄兼容 re-export，保留原公开导入路径和 `__all__`。
- `kernel_gen/passes/registry.py` 与 `kernel_gen/passes/pipeline/npu_demo_lowering.py` 作为内部消费者改为导入 `kernel_gen.passes.template_name.infer.TemplateNameInferPass`；`kernel_gen.passes` 包根仍经旧兼容入口 re-export。
- 更新 `spec/pass/template_name_*.md` 与 `spec/pass/registry.md`：真实实现路径改为新目录，旧根模块写为兼容入口，明确 `kernel_gen/passes/template_name/` 不进入 public path matrix。
- 补 `test/passes/test_registry.py`：锁定四个旧公开模块、`kernel_gen.passes.TemplateNameInferPass` 包根 re-export、registry 构造和内部 package root 空 `__all__`。
- 补 `test/passes/test_template_name_infer.py`：锁定 `entry_point` host 参数 template-name 传播到 `<host>_pattern*` 函数同位置参数，并覆盖 pattern 参数数量不一致失败边界。
- 只读 expectation 首次暴露 latest main 同合同失败：`entry_point` pattern case 中 host 参数模板名未传播到 pattern 函数。该失败在 `PYTHONPATH=/home/lfr/kernelcode_generate` 下同样复现，说明不是本轮搬迁引入；本轮在 template-name infer 实现内补齐当前主仓 expectation 合同，未改公开签名、pass name、错误模块或 expectation。

最小功能闭环：
- 公开 caller 继续使用 `kernel_gen.passes.template_name_infer`、`kernel_gen.passes.template_name_graph`、`kernel_gen.passes.template_name_constraints`、`kernel_gen.passes.template_name_default_constraints` 和 `kernel_gen.passes.TemplateNameInferPass`。
- 内部真实实现集中在 `kernel_gen/passes/template_name/`；内部模块之间不经旧 shim 互相导入；`template_name/__init__.py` 不 re-export 公开对象。
- registry pass name 保持 `template-name-infer`，npu-demo-lowering pass 顺序不变。
- `entry_point` host 与携带 `kernel.transform_pipeline` 的 `<host>_pattern*` 函数按参数位置建立 memory template 等价约束；pattern 参数数量或 memory / non-memory 不一致稳定失败。
- `expectation/`、`.skills/`、`agents/standard/` 未修改、未复制、未新建、未删除。

Diff 反推自测：
- 改动文件：`kernel_gen/passes/template_name/**`、四个旧 `template_name_*.py` shim、`kernel_gen/passes/registry.py`、`kernel_gen/passes/pipeline/npu_demo_lowering.py`、`spec/pass/template_name_*.md`、`spec/pass/registry.md`、`test/passes/test_registry.py`、`test/passes/test_template_name_*.py`、本任务记录。
- 反推测试 1：`PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/passes/test_template_name_graph.py test/passes/test_template_name_constraints.py test/passes/test_template_name_infer.py`，exit=0，`19 passed, 1 warning`；锁定 graph/constraints/default/infer 公开行为、entry_point pattern 传播和失败边界。
- 反推测试 2：`PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/passes/test_registry.py test/passes/pipeline/test_npu_demo_lowering.py`，exit=0，`63 passed, 1 warning`；锁定旧公开路径、registry 构造、内部 package root 空导出与 pipeline 顺序。
- 反推测试 3：`python3 -m py_compile kernel_gen/passes/template_name/*.py kernel_gen/passes/template_name_*.py kernel_gen/passes/registry.py kernel_gen/passes/pipeline/npu_demo_lowering.py test/passes/test_registry.py test/passes/test_template_name_graph.py test/passes/test_template_name_constraints.py test/passes/test_template_name_infer.py`，exit=0；锁定新增内部 package 与 shim 导入语法。
- 未执行 full pytest；本轮 diff 集中在 template-name pass 组织、registry/pipeline import 和对应 pytest，计划未要求全量测试，风险由上述 diff 反推测试与合同验收覆盖。

合同验收：
- 命令：`EXPECTATION_WORKTREE_ROOT=/home/lfr/kernelcode_generate/wt-20260521-template-name-package-refactor PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260521-template-name-package-refactor:/home/lfr/kernelcode_generate python3 -m expectation.pass.template_name_infer`，exit=0。
- 输出覆盖 5 个正例，包括 `passes-template_name_infer-entry_point-pattern_propagation-1`。
- import proof：`expectation.pass.template_name_infer.__main__` 来自 `/home/lfr/kernelcode_generate/expectation/pass/template_name_infer/__main__.py`；`kernel_gen.passes.template_name_infer`、`template_name_graph`、`template_name_constraints`、`template_name_default_constraints`、`kernel_gen.passes`、`registry`、`pipeline.npu_demo_lowering` 均来自任务 worktree。
- registry proof：`build_registered_pass("template-name-infer")` 返回 `kernel_gen.passes.template_name.infer.TemplateNameInferPass`，`name="template-name-infer"`。

静态扫描与敏感目录门禁：
- `rg -n "kernel_gen\\.passes\\.template_name_(constraints|default_constraints|graph|infer)" kernel_gen/passes`，exit=0；命中仅为四个旧公开 shim 的文档/示例，已归类为兼容入口说明；`registry.py`、`pipeline/npu_demo_lowering.py` 与新目录内部实现未经旧 shim 导入。
- `! rg -n "kernel_gen\\.passes\\.template_name\\." test spec/pass/registry.md`，exit=0；公开 pytest 与 registry spec 未把新内部 dotted path 写成外部 caller 合同。
- `rg -n "kernel_gen\\.passes\\.template_name\\.infer" kernel_gen/passes/registry.py kernel_gen/passes/pipeline/npu_demo_lowering.py && ! rg -n "kernel_gen\\.passes\\.template_name_infer" kernel_gen/passes/registry.py kernel_gen/passes/pipeline/npu_demo_lowering.py`，exit=0；内部消费者导入新实现路径且不经旧根 shim。
- `! rg -n "from kernel_gen\\.passes\\.[^.]+ import _|kernel_gen\\.passes\\.[A-Za-z0-9_]+\\._" kernel_gen/passes/template_name kernel_gen/passes/template_name_*.py test/passes`，exit=0。
- `! rg -n "hasattr\\(|getattr\\(|callable\\(getattr" kernel_gen/passes/template_name kernel_gen/passes/template_name_*.py`，exit=0。
- `! rg -n "object\\.__setattr__|\\bobject\\b.*signature|inspect\\.signature\\(object" kernel_gen/passes/template_name kernel_gen/passes/template_name_*.py`，exit=0。
- AST nested function scan over `kernel_gen/passes/template_name/*.py` and old shim files，exit=0，输出 `nested function scan ok`。
- `git diff --check`，exit=0。
- `git diff --name-only -- expectation .skills agents/standard`，exit=0，无输出；`git diff --cached --name-only -- expectation .skills agents/standard`，exit=0，无输出；`git status --short --ignored --untracked-files=all -- expectation .skills agents/standard`，exit=0，无输出。

自检：
- 接口：未新增公开 API，旧公开路径和 `kernel_gen.passes.TemplateNameInferPass` 均保留；新目录只作为内部实现路径，`template_name/__init__.py` 空 `__all__`。
- 边界：未删除旧公开模块；未改 pass name、pipeline 顺序、class / function 签名或工具参数；`entry_point` pattern 传播是当前主仓 expectation 合同补齐，不改变 API 表面。
- 异常：新增 pattern 参数数量不一致与 memory / non-memory 不一致稳定失败；未知 memory op、template 冲突等既有失败语义保留。
- 兼容性：公开 pytest 覆盖旧根模块、包根 re-export 与 registry 构造；内部消费者导入新实现路径。
- 实现遗漏：已迁移 graph、constraints、default constraints、infer 四个真实模块；旧根 shim 不承载算法逻辑。
- 冗余与复用：`entry_point` pattern 约束复用同位置 memory arg helper；未新增跨文件非公开 helper 依赖。
- 注释准确性：新增/移动实现文件保留文件级说明、API 列表、使用示例和关联文件；新增 helper 均含功能说明与使用示例。
- 函数粒度：新增 helper 按 entry_point 判断、pattern 判断、同位置约束构造、整体约束收集拆分，职责可读。
- 输入/输出校验：pattern 参数数量和类型不匹配会失败；只写回 memory template_name，不改 shape/stride/element_type/space。
- 资源、并发、性能：本轮为 IR 图约束收集，无外部资源；新增约束遍历为函数数平方级，仅在 module 内函数集合上运行，符合当前 pass 规模。
- 测试有效性：新增 pytest 会在旧路径断裂、内部 package root re-export、registry 构造失败、entry_point pattern 不传播或参数不匹配未失败时失败；expectation 覆盖当前主仓合同。

结论：execute 已完成，计划内 spec / 实现 / pytest / 只读 expectation / 静态扫描 / 敏感目录门禁闭环通过；下一步按流程流转 review。

---

时间：2026-05-22 02:06 CST
经办人：不要啊教练
任务：T-20260522-705c8fcf / template-name-package-refactor / review
任务目标：审查 template-name package refactor 的旧公开路径兼容、`kernel_gen/passes/template_name/` 内部实现目录、registry / pipeline 内部导入、spec / API 列表、公开 pytest、Diff 反推自测、主仓只读 `expectation.pass.template_name_infer` 合同验收与 `expectation/.skills/agents/standard` 空 diff。

审查前读取与同步：
- 已重新读取个人提示词 `agents/codex-multi-agents/agents/不要啊教练/不要啊教练.prompt.md`、根 `AGENTS.md`、`agents/standard/审查规范.md`、`agents/standard/任务记录约定.md`、`agents/standard/expectation任务规则.md`。
- 已核对 `TODO.md`：`T-20260522-705c8fcf` 为 `review / 不要啊教练 / 进行中`；当前任务依赖的上一条 `T-20260522-f6be549d` 未在当前活动表中继续阻塞。
- 执行目录：`/home/lfr/kernelcode_generate/wt-20260521-template-name-package-refactor`。
- 已执行 `git fetch origin --prune`；同步结果：`HEAD=1b8e9629446ff78fc7d9216000c06dab9d0b52d8`，`origin/main=1b8e9629446ff78fc7d9216000c06dab9d0b52d8`，`merge-base=1b8e9629446ff78fc7d9216000c06dab9d0b52d8`，ahead / behind 为 `0 / 0`。
- 目标 worktree 缺少计划资产 `ARCHITECTURE/plan/template_name_package_refactor_green_plan.md`；本轮按主仓共享计划 `/home/lfr/kernelcode_generate/ARCHITECTURE/plan/template_name_package_refactor_green_plan.md` 只读作为合同真源，未复制、修改或新建计划资产。
- 同步未产生冲突，未覆盖任务 diff，未发现会丢失他人改动的风险。

被审 diff：
- 实现与兼容入口：`kernel_gen/passes/template_name/__init__.py`、`kernel_gen/passes/template_name/constraints.py`、`kernel_gen/passes/template_name/default_constraints.py`、`kernel_gen/passes/template_name/graph.py`、`kernel_gen/passes/template_name/infer.py`、`kernel_gen/passes/template_name_constraints.py`、`kernel_gen/passes/template_name_default_constraints.py`、`kernel_gen/passes/template_name_graph.py`、`kernel_gen/passes/template_name_infer.py`。
- 内部消费者：`kernel_gen/passes/registry.py`、`kernel_gen/passes/pipeline/npu_demo_lowering.py`。
- spec：`spec/pass/registry.md`、`spec/pass/template_name_constraints.md`、`spec/pass/template_name_default_constraints.md`、`spec/pass/template_name_graph.md`、`spec/pass/template_name_infer.md`。
- pytest：`test/passes/test_registry.py`、`test/passes/test_template_name_constraints.py`、`test/passes/test_template_name_graph.py`、`test/passes/test_template_name_infer.py`。
- 记录：`agents/codex-multi-agents/log/task_records/2026/21/20260521-template-name-package-refactor.md`。
- 工作树存在 `.pytest_cache/**` 与若干 `__pycache__/*.pyc` ignored 产物；不属于候选 diff，且不在 `expectation/.skills/agents/standard` 敏感目录内。

真实审查：
- 旧公开路径兼容：四个旧根模块 `kernel_gen.passes.template_name_graph`、`template_name_constraints`、`template_name_default_constraints`、`template_name_infer` 均保留薄 re-export，`__all__` 覆盖原公开对象；`kernel_gen.passes.TemplateNameInferPass` 仍经旧兼容入口导出，公开 caller 路径未断。
- 新内部目录边界：`kernel_gen/passes/template_name/__init__.py` 仅保留文件说明与空 `__all__`，未把内部实现目录提升为新的公开 package-root API；计划要求的“内部实现目录，不进入 public path matrix”成立。
- registry / pipeline 内部导入：`kernel_gen/passes/registry.py` 与 `kernel_gen/passes/pipeline/npu_demo_lowering.py` 均直接导入 `kernel_gen.passes.template_name.infer.TemplateNameInferPass`，内部消费者不再经旧公开 shim 间接取实现。
- spec / API 列表：`spec/pass/template_name_*.md` 顶部 API 简表与文件级 API 列表同步到新实现路径和旧兼容路径；`spec/pass/registry.md` 明确新目录为内部实现目录，未把 `kernel_gen.passes.template_name.*` 写成外部公开入口。
- 实现行为：搬迁后 graph / constraints / default constraints / infer 的公开签名、pass name、错误语义和 registry 名称保持不变；`entry_point` pattern 参数模板传播补齐当前只读 expectation 合同，未引入新的公开 API。
- 公开 API / 非公开 API 边界：未发现跨文件调用当前文件之外的非公开 helper；未发现测试正向直连 `kernel_gen.passes.template_name.*` 内部实现路径；未发现新增未在 spec 明确定义的公开 API。
- 禁止模式扫描：未发现 `hasattr/getattr/callable(getattr)` ctx 能力探测、`object` 签名绕行、非装饰器嵌套函数。

findings：
- 无阻断项。
- 未发现仍需退回 execute 的一线可执行返工项；旧公开路径、内部实现目录边界、registry / pipeline 内部导入、spec / pytest 与只读 expectation 证据链闭合。

Diff 反推审查：
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/passes/test_template_name_graph.py -ra`，exit=0，`5 passed, 1 warning`；锁定 graph 旧公开入口和 moved implementation 行为。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/passes/test_template_name_constraints.py -ra`，exit=0，`6 passed, 1 warning`；锁定 constraints 旧公开入口与约束构造。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/passes/test_template_name_infer.py -ra`，exit=0，`8 passed, 2 warnings`；锁定 `TemplateNameInferPass` 旧公开入口、entry_point pattern 传播和失败边界。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/passes/test_registry.py test/passes/pipeline/test_npu_demo_lowering.py -ra`，exit=0，`63 passed, 1 warning`；锁定旧公开 path、package-root re-export、registry 构造、pipeline 导入和顺序。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/passes/test_template_name_graph.py test/passes/test_template_name_constraints.py test/passes/test_template_name_infer.py -ra`，exit=0，`19 passed, 1 warning`；复跑计划级 template-name 相关公开 pytest。
- `PYTHONDONTWRITEBYTECODE=1 python3 -m py_compile kernel_gen/passes/template_name/*.py kernel_gen/passes/template_name_*.py kernel_gen/passes/registry.py kernel_gen/passes/pipeline/npu_demo_lowering.py test/passes/test_registry.py test/passes/test_template_name_graph.py test/passes/test_template_name_constraints.py test/passes/test_template_name_infer.py`，exit=0。
- 曾在并行 smoke 中命中环境层 SymPy import 异常 / pytest 进程 SIGSEGV；随后按逐条顺序复跑相同计划相关命令均通过，本 review 结论以上述顺序复跑结果为准。

合同验收：
- 主仓只读命令：`EXPECTATION_WORKTREE_ROOT=/home/lfr/kernelcode_generate/wt-20260521-template-name-package-refactor PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260521-template-name-package-refactor:/home/lfr/kernelcode_generate python3 -m expectation.pass.template_name_infer`，exit=0。
- 输出覆盖 `passes-template_name_infer-kernel_matmul_signature_seed-1`、`passes-template_name_infer-dma_view_same-1`、`passes-template_name_infer-dma_copy_same-1`、`passes-template_name_infer-kernel_exp_same-1`、`passes-template_name_infer-entry_point-pattern_propagation-1`。
- import proof：`expectation.pass.template_name_infer.__main__` 来自主仓 `/home/lfr/kernelcode_generate/expectation/pass/template_name_infer/__main__.py`；`kernel_gen.passes.template_name_infer`、`template_name_graph`、`template_name_constraints`、`template_name_default_constraints`、`kernel_gen.passes`、`registry`、`pipeline.npu_demo_lowering` 均来自任务 worktree。
- registry proof：`build_registered_pass("template-name-infer")` 返回 `kernel_gen.passes.template_name.infer.TemplateNameInferPass`，`name="template-name-infer"`。

静态扫描与敏感目录门禁：
- `git diff --check`，exit=0；`git diff --cached --check`，exit=0。
- `git diff --name-only -- expectation .skills agents/standard`，无输出；`git diff --cached --name-only -- expectation .skills agents/standard`，无输出；`git status --short --untracked-files=all -- expectation .skills agents/standard`，无输出；`git status --short --ignored --untracked-files=all -- expectation .skills agents/standard`，无输出。
- `rg -n "kernel_gen\.passes\.template_name_(constraints|default_constraints|graph|infer)" kernel_gen/passes` 仅命中旧 shim 文档 / 示例，不命中 registry / pipeline / 新内部实现绕旧 shim 导入。
- `! rg -n "kernel_gen\.passes\.template_name\." test spec/pass/registry.md`，exit=0；公开测试与 registry spec 未把内部 dotted path 写成外部 caller 合同。
- `rg -n "kernel_gen\.passes\.template_name\.infer" kernel_gen/passes/registry.py kernel_gen/passes/pipeline/npu_demo_lowering.py` 命中预期内部导入；`! rg -n "kernel_gen\.passes\.template_name_infer" kernel_gen/passes/registry.py kernel_gen/passes/pipeline/npu_demo_lowering.py`，exit=0。
- `! rg -n "from kernel_gen\.passes\.[^.]+ import _|kernel_gen\.passes\.[A-Za-z0-9_]+\._" kernel_gen/passes/template_name kernel_gen/passes/template_name_*.py test/passes`，exit=0。
- `! rg -n "hasattr\(|getattr\(|callable\(getattr" kernel_gen/passes/template_name kernel_gen/passes/template_name_*.py`，exit=0。
- `! rg -n "object\.__setattr__|\bobject\b.*signature|inspect\.signature\(object" kernel_gen/passes/template_name kernel_gen/passes/template_name_*.py`，exit=0。
- AST nested function scan over `kernel_gen/passes/template_name/*.py` and old shim files，exit=0，输出 `nested function scan ok`。

执行记录核对：
- 执行记录包含执行前阅读、同步基线、最小功能闭环、Diff 反推自测、合同验收、静态扫描、敏感目录门禁和自检。
- 执行记录将 `expectation.pass.template_name_infer` 单列为合同验收，未把 expectation 计入 Diff 反推测试；符合当前 expectation 只读合同真源规则。
- 执行记录对 worktree 缺计划资产已说明使用主仓共享计划只读，不存在复制或修改计划资产行为。

自检：
- 已逐项核对实际 diff，不只依赖执行摘要；重点覆盖旧公开路径、内部实现目录、registry / pipeline 内部导入、spec/API、pytest 与 expectation。
- 已先 fetch 并核对 latest main 现场，确认任务 worktree 与 origin/main 对齐且无冲突 / 覆盖风险。
- 已检查公开 API 未新增、未删除、未改签名；新目录未进入公开 API，旧公开路径兼容保留。
- 已检查跨文件非公开 API、测试直连非 API、ctx 能力探测、object 签名和非装饰器嵌套函数，未发现命中。
- 已复跑 diff 对应 pytest、py_compile、只读 expectation 和敏感目录门禁；未运行 full pytest，原因是计划和 diff 范围集中在 template-name package refactor，反推 pytest 与合同验收已覆盖本轮候选改动。
- 未修改业务实现、spec、测试、计划书、`expectation/`、`.skills/` 或 `agents/standard/`；仅追加本任务审查记录。

结论：通过。当前 review 未发现最小需改项；计划级任务不直接 merge，建议管理员接入架构复核 / 终验。

---

时间：2026-05-22 02:11:25 +0800
经办人：守护最好的爱莉希雅
任务：T-20260522-705c8fcf / template-name-package-refactor / 第二架构复核终验
任务目标：在 review 通过后复核最新同步现场、执行目录、旧公开路径兼容、新内部 `template_name/` 目录边界、registry / pipeline 内部导入、主仓只读 `expectation.pass.template_name_infer` 合同验收、Diff 反推测试、敏感目录空 diff 与最小阻断项。

最新同步现场：
- 执行目录：`/home/lfr/kernelcode_generate/wt-20260521-template-name-package-refactor`。
- 已执行 `git fetch origin --prune`。
- 基线：`HEAD=1b8e9629446ff78fc7d9216000c06dab9d0b52d8`，`origin/main=1b8e9629446ff78fc7d9216000c06dab9d0b52d8`，`merge-base=1b8e9629446ff78fc7d9216000c06dab9d0b52d8`，ahead/behind=`0/0`。
- 候选 diff 范围：
  - `kernel_gen/passes/template_name/{__init__.py,constraints.py,default_constraints.py,graph.py,infer.py}`
  - `kernel_gen/passes/template_name_constraints.py`
  - `kernel_gen/passes/template_name_default_constraints.py`
  - `kernel_gen/passes/template_name_graph.py`
  - `kernel_gen/passes/template_name_infer.py`
  - `kernel_gen/passes/registry.py`
  - `kernel_gen/passes/pipeline/npu_demo_lowering.py`
  - `spec/pass/{registry.md,template_name_constraints.md,template_name_default_constraints.md,template_name_graph.md,template_name_infer.md}`
  - `test/passes/{test_registry.py,test_template_name_constraints.py,test_template_name_graph.py,test_template_name_infer.py}`
  - 本任务记录

合同验收：
- 主仓只读命令：
  - `EXPECTATION_WORKTREE_ROOT=/home/lfr/kernelcode_generate/wt-20260521-template-name-package-refactor PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260521-template-name-package-refactor:/home/lfr/kernelcode_generate python3 -m expectation.pass.template_name_infer`
  - 结果：exit=0。
  - 输出覆盖 5 个合同正例：`kernel_matmul_signature_seed`、`dma_view_same`、`dma_copy_same`、`kernel_exp_same`、`entry_point-pattern_propagation`。
- expectation hash：
  - `8bf55e4d0a82521178243bbd46dae7165db05a42cb35d45cf2c920d536ca70dc  expectation/pass/template_name_infer/__main__.py`
  - `f68d6e6a54e9f126d529ae16c94d7efb4f5f386852840098fe1e8beece30e42f  expectation/pass/template_name_infer/basic.py`
  - `4096a2ab37bbfd79a3b7a8c2ded1dbc5aa988000421abae4ed886b1b62c4ec03  expectation/pass/template_name_infer/entry_point.py`
- import proof：
  - `expectation.pass.template_name_infer.__main__` 来自主仓 `/home/lfr/kernelcode_generate/expectation/pass/template_name_infer/__main__.py`。
  - `kernel_gen.passes.template_name_infer`、`kernel_gen.passes.template_name_graph`、`kernel_gen.passes.template_name_constraints`、`kernel_gen.passes.template_name_default_constraints`、`kernel_gen.passes`、`kernel_gen.passes.registry`、`kernel_gen.passes.pipeline.npu_demo_lowering` 均来自任务 worktree。
  - 先直接调用 `build_registered_pass("template-name-infer")` 会因 registry 未初始化返回 `PassRegistryError: unknown pass 'template-name-infer'`；这是验证命令口径问题，不是候选失败。按公开用法先执行 `load_builtin_passes()` 后重跑，`build_registered_pass("template-name-infer")` 返回 `kernel_gen.passes.template_name.infer.TemplateNameInferPass`，`name="template-name-infer"`。

Diff 反推终验：
- `PYTHONDONTWRITEBYTECODE=1 python3 -m py_compile kernel_gen/passes/template_name/*.py kernel_gen/passes/template_name_*.py kernel_gen/passes/registry.py kernel_gen/passes/pipeline/npu_demo_lowering.py test/passes/test_registry.py test/passes/test_template_name_graph.py test/passes/test_template_name_constraints.py test/passes/test_template_name_infer.py`：exit=0。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/passes/test_template_name_graph.py test/passes/test_template_name_constraints.py test/passes/test_template_name_infer.py -ra`：exit=0，`19 passed, 1 warning`。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/passes/test_registry.py test/passes/pipeline/test_npu_demo_lowering.py -ra`：exit=0，`63 passed, 1 warning`。
- `git diff --check` 与 `git diff --cached --check`：exit=0。
- 敏感目录门禁：
  - `git diff --name-only -- expectation .skills agents/standard`：空。
  - `git diff --cached --name-only -- expectation .skills agents/standard`：空。
  - `git status --short --untracked-files=all -- expectation .skills agents/standard`：空。
  - `git status --short --ignored --untracked-files=all -- expectation .skills agents/standard`：空。
- 静态边界扫描：
  - `rg -n "kernel_gen\\.passes\\.template_name_(constraints|default_constraints|graph|infer)" kernel_gen/passes` 仅命中四个旧 shim 的文档 / 示例，归类为旧公开兼容入口说明；`registry.py`、`pipeline/npu_demo_lowering.py` 和新内部实现未绕旧 shim 导入。
  - `! rg -n "kernel_gen\\.passes\\.template_name\\." test spec/pass/registry.md`：exit=0，公开 pytest 与 registry spec 未把内部 dotted path 写成外部 caller 合同。
  - `rg -n "kernel_gen\\.passes\\.template_name\\.infer" kernel_gen/passes/registry.py kernel_gen/passes/pipeline/npu_demo_lowering.py`：命中预期内部导入。
  - `! rg -n "kernel_gen\\.passes\\.template_name_infer" kernel_gen/passes/registry.py kernel_gen/passes/pipeline/npu_demo_lowering.py`：exit=0，内部消费者未经旧根 shim 导入。
  - 跨文件私有 helper、`hasattr/getattr/callable(getattr)`、`object.__setattr__` / `object` 签名探测扫描均 exit=0。
  - AST nested function scan over `kernel_gen/passes/template_name/*.py` and old shim files：exit=0，输出 `nested function scan ok`。

终验判断：
- 旧公开路径兼容：四个旧根模块和 `kernel_gen.passes.TemplateNameInferPass` 保留可用；旧模块为薄 shim，公开 `__all__` 由 pytest 锁定。
- 新内部目录边界：`kernel_gen/passes/template_name/__init__.py` 不 re-export 公开对象；公开 pytest 和 `spec/pass/registry.md` 未把 `kernel_gen.passes.template_name.*` 当作外部 caller path。
- registry / pipeline 边界：内部消费者直接导入 `kernel_gen.passes.template_name.infer.TemplateNameInferPass`；公开 registry pass name 仍为 `template-name-infer`，pipeline 顺序不变。
- 公开 API：未新增、删除、重命名或改签公开 API；未删除旧公开模块路径；未修改稳定错误文本或工具参数。
- 权限边界：本轮只读运行主仓 expectation；候选 diff 中 `expectation/`、`.skills/`、`agents/standard/**` 为空。
- 最小阻断项：无。

自检：
- 已按计划和 review 摘要核对旧公开路径兼容、内部实现目录、registry / pipeline 内部导入、spec/API 列表、公开 pytest、主仓只读 expectation 和敏感目录门禁。
- 已复跑计划列出的 Diff 反推 pytest 与合同 expectation；未运行 full pytest，原因是计划完成态和候选 diff 聚焦 template-name package refactor，当前反推测试与合同验收已覆盖本轮改动面。
- 已检查公开 API 边界、跨文件非公开 helper、测试直连内部 path、ctx 能力探测、`object` 签名和嵌套函数，未发现阻断命中。

结论：通过第二架构复核 / 终验，可进入 merge 流转；merge 前需保持本记录与代码 / spec / test 同批纳入，并继续确认 `expectation/`、`.skills/`、`agents/standard/**` 空 diff。

---

## 架构终验（大闸蟹）

时间：2026-05-22 02:13 CST
经办人：大闸蟹
任务：T-20260522-705c8fcf / template-name-package-refactor 计划级架构复核 / 终验
任务目标：复核 review 通过后的最新同步现场、执行目录、旧公开路径兼容、内部 template_name 目录边界、registry / pipeline 内部导入、主仓只读 `expectation.pass.template_name_infer` 合同验收和最小阻断项。

### 最新同步现场

- 执行目录：`/home/lfr/kernelcode_generate/wt-20260521-template-name-package-refactor`。
- 已在终验前执行 `git fetch --prune origin`。
- 基线：`HEAD=1b8e9629446ff78fc7d9216000c06dab9d0b52d8`，`origin/main=1b8e9629446ff78fc7d9216000c06dab9d0b52d8`，`merge-base=1b8e9629446ff78fc7d9216000c06dab9d0b52d8`，ahead/behind=`0/0`。
- 候选 diff 范围：`kernel_gen/passes/template_name/**`、四个旧 `kernel_gen/passes/template_name_*.py` 兼容入口、`kernel_gen/passes/registry.py`、`kernel_gen/passes/pipeline/npu_demo_lowering.py`、`spec/pass/template_name_*.md`、`spec/pass/registry.md`、`test/passes/test_template_name_*.py`、`test/passes/test_registry.py` 与本任务记录。

### 复核摘要

- 旧公开路径兼容：`kernel_gen.passes.template_name_infer`、`template_name_graph`、`template_name_constraints`、`template_name_default_constraints` 仍存在并作为薄 re-export；`kernel_gen.passes.TemplateNameInferPass` 继续可用。
- 新内部目录边界：`kernel_gen/passes/template_name/` 承载真实实现；`template_name/__init__.py` 不 re-export 公开对象，未把 `kernel_gen.passes.template_name.*` 写成新的外部 caller 合同。
- registry / pipeline 边界：`registry.py` 与 `npu_demo_lowering.py` 直接导入 `kernel_gen.passes.template_name.infer.TemplateNameInferPass`；公开 pass name 仍为 `template-name-infer`，pipeline 顺序不变。
- 公开 API 边界：未删除旧公开模块路径，未新增 / 重命名 / 改签公开 API，未修改稳定错误文本或工具参数。

### 终验命令与结果

- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/passes/test_template_name_graph.py test/passes/test_template_name_constraints.py test/passes/test_template_name_infer.py -ra`：exit=0，`19 passed, 1 warning`。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/passes/test_registry.py test/passes/pipeline/test_npu_demo_lowering.py -ra`：exit=0，`63 passed, 1 warning`。
- `PYTHONDONTWRITEBYTECODE=1 python3 -m py_compile kernel_gen/passes/template_name/*.py kernel_gen/passes/template_name_*.py kernel_gen/passes/registry.py kernel_gen/passes/pipeline/npu_demo_lowering.py test/passes/test_registry.py test/passes/test_template_name_graph.py test/passes/test_template_name_constraints.py test/passes/test_template_name_infer.py`：exit=0。
- 主仓只读 expectation：
  - 命令：`EXPECTATION_WORKTREE_ROOT=/home/lfr/kernelcode_generate/wt-20260521-template-name-package-refactor PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260521-template-name-package-refactor:/home/lfr/kernelcode_generate python3 -m expectation.pass.template_name_infer`
  - 结果：exit=0。
  - 输出覆盖 `kernel_matmul_signature_seed`、`dma_view_same`、`dma_copy_same`、`kernel_exp_same`、`entry_point-pattern_propagation` 五个合同正例。
- 导入边界 proof：
  - `expectation.pass.template_name_infer.__main__`、`basic.py`、`entry_point.py` 来自主仓 `/home/lfr/kernelcode_generate/expectation/pass/template_name_infer/`。
  - `kernel_gen.passes`、`registry`、`pipeline.npu_demo_lowering`、四个旧 `template_name_*` 兼容入口均来自任务 worktree。
  - `build_registered_pass("template-name-infer")` 在 `load_builtin_passes()` 后返回 `kernel_gen.passes.template_name.infer.TemplateNameInferPass`，`name="template-name-infer"`。
- `git diff --check` 与 `git diff --cached --check`：exit=0。
- 敏感目录门禁：
  - `git diff --name-only -- expectation .skills agents/standard`：空。
  - `git diff --cached --name-only -- expectation .skills agents/standard`：空。
  - `git status --short --untracked-files=all -- expectation .skills agents/standard`：空。
  - `git status --short --ignored --untracked-files=all -- expectation .skills agents/standard`：空。
- 静态边界扫描：
  - `rg -n "kernel_gen\\.passes\\.template_name_(constraints|default_constraints|graph|infer)" kernel_gen/passes` 仅命中四个旧 shim 的文档 / 示例，归类为公开兼容入口说明。
  - `! rg -n "kernel_gen\\.passes\\.template_name\\." test spec/pass/registry.md`：exit=0，公开 pytest 与 registry spec 未把内部 dotted path 写成外部 caller 合同。
  - `rg -n "kernel_gen\\.passes\\.template_name\\.infer" kernel_gen/passes/registry.py kernel_gen/passes/pipeline/npu_demo_lowering.py` 命中预期内部导入；`! rg -n "kernel_gen\\.passes\\.template_name_infer" kernel_gen/passes/registry.py kernel_gen/passes/pipeline/npu_demo_lowering.py`：exit=0。
  - 跨文件私有 helper、`hasattr/getattr/callable(getattr)`、`object.__setattr__` / `object` 签名探测扫描均 exit=0。
  - AST nested function scan over `kernel_gen/passes/template_name/*.py` and old shim files：exit=0，输出 `nested function scan ok`。

### 自检与结论

- 已按实际 diff 反推核对实现、spec、registry、pipeline、pytest 与任务记录；未发现跨文件非公开 API 使用、测试直连非公开 helper、ctx 能力探测、未授权公开 API 扩张或敏感目录差异。
- 本轮通过依据不包含 full expectation；仅以计划正文列出的 `expectation.pass.template_name_infer` 作为当前必过合同验收资产。
- 最小阻断项：无。

结论：通过计划级架构复核 / 终验。双架构终验已具备通过记录后，可进入 merge 流转；merge 前需保持代码、spec、test 与本任务记录同批纳入，并继续确认 `expectation/`、`.skills/`、`agents/standard/**` 空 diff。

---

## Merge 收口（李白）

时间：2026-05-22 02:18 CST
经办人：李白
任务：T-20260522-705c8fcf / merge
任务目标：合入 `template-name-package-refactor` 已通过 review 与双架构终验的候选 diff，并确保任务记录与实现 / spec / pytest 同批进入主线。

### 合并前同步与范围核对

- 执行目录：`/home/lfr/kernelcode_generate/wt-20260521-template-name-package-refactor`。
- 分支：`task/template-name-package-refactor`。
- 已重新读取：`agents/codex-multi-agents/agents/李白/李白.prompt.md`、根 `AGENTS.md`、`agents/standard/合并规范.md`、`agents/standard/任务记录约定.md`。
- 已执行：`git fetch --prune origin`。
- 同步基线：`HEAD=origin/main=merge-base=1b8e9629446ff78fc7d9216000c06dab9d0b52d8`，ahead/behind=`0/0`。
- 主仓 `/home/lfr/kernelcode_generate` 合并前状态 clean，无需要覆盖的本地改动。
- 共享计划只读核对：`/home/lfr/kernelcode_generate/ARCHITECTURE/plan/template_name_package_refactor_green_plan.md`；任务 worktree 未把计划书纳入候选。
- 候选文件核对为 21 个，任务记录必须与实现 / spec / pytest 同批纳入：
  - `kernel_gen/passes/template_name/__init__.py`
  - `kernel_gen/passes/template_name/constraints.py`
  - `kernel_gen/passes/template_name/default_constraints.py`
  - `kernel_gen/passes/template_name/graph.py`
  - `kernel_gen/passes/template_name/infer.py`
  - `kernel_gen/passes/template_name_constraints.py`
  - `kernel_gen/passes/template_name_default_constraints.py`
  - `kernel_gen/passes/template_name_graph.py`
  - `kernel_gen/passes/template_name_infer.py`
  - `kernel_gen/passes/registry.py`
  - `kernel_gen/passes/pipeline/npu_demo_lowering.py`
  - `spec/pass/registry.md`
  - `spec/pass/template_name_constraints.md`
  - `spec/pass/template_name_default_constraints.md`
  - `spec/pass/template_name_graph.md`
  - `spec/pass/template_name_infer.md`
  - `test/passes/test_registry.py`
  - `test/passes/test_template_name_constraints.py`
  - `test/passes/test_template_name_graph.py`
  - `test/passes/test_template_name_infer.py`
  - `agents/codex-multi-agents/log/task_records/2026/21/20260521-template-name-package-refactor.md`
- 公开 API 核对：旧公开路径 `kernel_gen.passes.template_name_*` 与 `kernel_gen.passes.TemplateNameInferPass` 保留；新增 `kernel_gen/passes/template_name/` 为内部实现目录，`__init__.py` 不 re-export 公开对象；未新增、删除、重命名或改签公开 API。

### merge 复核验证

- `PYTHONDONTWRITEBYTECODE=1 python3 -m py_compile kernel_gen/passes/template_name/*.py kernel_gen/passes/template_name_*.py kernel_gen/passes/registry.py kernel_gen/passes/pipeline/npu_demo_lowering.py test/passes/test_registry.py test/passes/test_template_name_graph.py test/passes/test_template_name_constraints.py test/passes/test_template_name_infer.py`：exit=0。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/passes/test_template_name_graph.py test/passes/test_template_name_constraints.py test/passes/test_template_name_infer.py -ra`：exit=0，`19 passed, 1 warning`。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/passes/test_registry.py test/passes/pipeline/test_npu_demo_lowering.py -ra`：首次与其它 gate 并行执行时进程收到 `SIGSEGV`；未修改代码，随后拆分顺序复跑：
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/passes/test_registry.py -ra`：exit=0，`55 passed, 1 warning`。
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/passes/pipeline/test_npu_demo_lowering.py -ra`：exit=0，`8 passed, 1 warning`。
  - 原组合命令再次顺序重跑：exit=0，`63 passed, 1 warning`。
- `EXPECTATION_WORKTREE_ROOT=/home/lfr/kernelcode_generate/wt-20260521-template-name-package-refactor PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260521-template-name-package-refactor:/home/lfr/kernelcode_generate python3 -m expectation.pass.template_name_infer`：exit=0，输出覆盖 `kernel_matmul_signature_seed`、`dma_view_same`、`dma_copy_same`、`kernel_exp_same`、`entry_point-pattern_propagation` 五个合同正例。
- 导入边界 proof：`expectation.pass.template_name_infer.__main__` 来自主仓 `/home/lfr/kernelcode_generate/expectation/pass/template_name_infer/__main__.py`；旧公开 shim、`registry`、`pipeline.npu_demo_lowering` 均来自任务 worktree；`load_builtin_passes()` 后 `build_registered_pass("template-name-infer")` 返回 `kernel_gen.passes.template_name.infer.TemplateNameInferPass`，`name="template-name-infer"`。
- `git diff --check` 与 `git diff --cached --check`：exit=0。
- `git diff --name-only -- expectation .skills agents/standard`：空。
- `git diff --cached --name-only -- expectation .skills agents/standard`：空。
- `git status --short --ignored --untracked-files=all -- expectation .skills agents/standard`：空。
- 静态边界扫描：`hasattr/getattr/callable(getattr)`、`object.__setattr__` / `object` 签名探测、跨文件私有 helper 与非装饰器嵌套函数均无阻断命中；AST 扫描输出 `nested function scan ok`。

### 冲突与风险

- 冲突处理：未发生冲突，latest main 已在合并前对齐。
- 敏感目录：`expectation/`、`.skills/`、`agents/standard/**` 无 tracked / staged / untracked / ignored 候选改动。
- 合同资产：本轮只读运行主仓 `expectation.pass.template_name_infer` 作为合同真源；候选 diff 不包含 `expectation/` 改动。
- 剩余风险：`test_registry.py test_npu_demo_lowering.py` 组合命令曾在并行 gate 中收到一次 SIGSEGV，随后单项和同命令顺序重跑均通过；本轮按真实过程记录，后续若复现需单列运行稳定性专项。

### 结论

- 结论：merge 前核对通过，可合入主线。
- 最小阻断项：无。
