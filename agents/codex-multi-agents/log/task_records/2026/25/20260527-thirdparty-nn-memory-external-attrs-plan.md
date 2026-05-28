时间：2026-05-28 00:09 +0800
经办人：小李飞刀
任务：T-20260528-8ad7e551 / plan/1.md / execute
任务目标：按 `plan/1.md` 完成 `NnMemoryType` `external_attrs`、`template_name` 迁移、copy helper、parser/printer/verifier、template-name infer、gen_kernel/EmitC ABI、spec、测试与验收闭环。
执行目录：`/home/lfr/kernelcode_generate`
同步现场：`HEAD=479ef47e2cd93f3810b891ce6cf3b053ca360b41`，`origin/main=479ef47e2cd93f3810b891ce6cf3b053ca360b41`，`merge-base=479ef47e2cd93f3810b891ce6cf3b053ca360b41`；当前主仓 latest main 已对齐。
执行前阅读记录：已读取 `agents/codex-multi-agents/agents/小李飞刀/小李飞刀.prompt.md`、根 `AGENTS.md`、`agents/standard/实现文件规范.md`、`agents/standard/任务记录约定.md`、`plan/1.md`、本任务记录、`TODO.md` 任务行、`kernel_gen/dialect/nn/type/memory_type.py`、`kernel_gen/dialect/nn/__init__.py`、`kernel_gen/dialect/__init__.py`、`kernel_gen/passes/template_name/infer.py`、`kernel_gen/dsl/gen_kernel/kernel_emitter.py`、`spec/dialect/nn.md`、`spec/pass/template_name_infer.md`、`spec/dsl/gen_kernel/kernel_emitter.md`、`test/dialect/nn/test_type.py`、`test/dialect/nn/test_package.py`、`test/passes/test_template_name_infer.py`、`test/dsl/gen_kernel/test_gen_kernel.py`、`test/dsl/gen_kernel/emit/test_package.py`。
计划内小任务卡核对：
- S1：修改 `NnMemoryType` 数据结构，真实参数迁移为 `external_attrs`，保留旧 `template_name=` 构造和 `.template_name.data` 访问兼容。
- S2：修改 parser/printer/verifier，canonical print 使用 `external_attrs = {...}`，兼容 legacy `template = T0` 输入，稳定失败语义与计划一致。
- S3：修改 copy helper 与公开导出，新增 `copy_memory_type_with_external_attr(...)`，`copy_memory_type(...)` 只清除 `template_name` 且保留其它 `external_attrs`。
- S4：适配 template-name infer 与 emitter ABI 比较，确保 infer 继续通过公开 helper 写 `template_name`，ABI 比较只忽略 `template_name` 不忽略其它 `external_attrs`。
- S5：同步 `spec`、测试和迁移记录，运行计划列 pytest、py_compile、`git diff --check`、敏感目录门禁。
最小功能闭环：先以 `kernel_gen/dialect/nn/type/memory_type.py` 为真源完成构造、property、parse/print、verify、copy helper 和导出；随后用 `test/dialect/nn/test_type.py` 与 `test/dialect/nn/test_package.py` 锁定公开 API；再跑 `test/passes/test_template_name_infer.py` 与 `test/dsl/gen_kernel` 锁定 template infer 和 gen_kernel/EmitC ABI 行为。
禁止修改面：不得修改 `expectation/`、`.skills/`、`agents/standard/`、`AGENTS.md`、`TODO.md`、`DONE.md`；本计划无必过 `expectation`，不以 expectation 作为通过依据。
验证：本段为开工记录，尚未运行实现测试；后续按实际 diff 补 `Diff 反推自测` 和计划验收命令。
自检：开工前已确认任务状态为进行中、记录落点存在、计划公开 API 已有用户确认来源；当前工作区开工前 `git status --short --untracked-files=all` 为空，未发现需保留的他人改动。
结论：执行前记录已补齐，继续进入 S1/S2 实现。

时间：2026-05-28 00:42 +0800
经办人：小李飞刀
阶段：execute 完成

改动摘要：
- `kernel_gen/dialect/nn/type/memory_type.py`：将 `NnMemoryType` 真实参数迁移为 `external_attrs: DictionaryAttr`；保留 `template_name=` 构造兼容与 `.template_name` property；新增 canonical `external_attrs = {...}` parser/printer/verifier；legacy `template = T1` 只作为输入兼容并 canonical print 到 `external_attrs = {template_name = "T1"}`；新增 `copy_memory_type_with_external_attr(...)`；`copy_memory_type(...)` 仅清除 `template_name` 并保留其它 external attrs；`copy_memory_type_with_template_name(...)` 保留其它 external attrs 后覆盖 `template_name`。
- `kernel_gen/dialect/nn/type/__init__.py`、`kernel_gen/dialect/nn/__init__.py`、`kernel_gen/dialect/__init__.py`：同步文件级 API 列表、导入、`__all__` 与懒加载导出，纳入 `copy_memory_type_with_external_attr(...)`。
- `spec/dialect/nn.md`：同步 `NnMemoryType.external_attrs`、legacy template 输入兼容、canonical print、稳定失败语义、copy helper 语义与新增测试用例矩阵。
- `spec/pass/template_name_infer.md`：明确 template-name infer 写回 `external_attrs["template_name"]`，不得改变其它 external attrs。
- `spec/dsl/gen_kernel/kernel_emitter.md`：明确 launch wrapper/body ABI 比较只忽略 `external_attrs["template_name"]`，不得忽略其它 external attrs。
- `test/dialect/nn/test_type.py`、`test/dialect/nn/test_package.py`、`test/dialect/test_package.py`：补 external attrs parse/print/copy/错误语义、package root/API 导出回归。
- `test/passes/test_template_name_infer.py`：补 template-name infer 写回 template name 时保留其它 external attrs 的回归。
- `test/dsl/gen_kernel/test_gen_kernel.py`：补 npu_demo launch wrapper/body 非 template external attr 差异必须失败的 ABI 回归。

最小功能闭环：
- 构造：`NnMemoryType(..., template_name="T1")` 与 `NnMemoryType(..., external_attrs={"template_name": StringAttr("T1")})` 统一落到 `external_attrs` 真源。
- 文本：`template = T1` 可读，输出变为 `external_attrs = {template_name = "T1"}`；非 template external attr 按 key 排序输出。
- clone：`copy_memory_type(...)` 清除 template name 但保留其它 external attrs；`copy_memory_type_with_template_name(...)` 只覆盖 template；`copy_memory_type_with_external_attr(...)` clone 写单 key。
- 下游：template-name infer 通过公开 helper 写入 template name 且保留其它 external attrs；gen_kernel ABI 比较只忽略 template name。

Diff 反推自测：
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/dialect/nn/test_type.py test/dialect/nn/test_package.py test/dialect/test_package.py`：exit=0，`23 passed, 1 warning`。覆盖 `NnMemoryType` 新 parser/printer/verifier/copy helper 与 dialect 包根导出。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/passes/test_template_name_infer.py`：exit=0，`11 passed, 2 warnings`。覆盖 template-name infer 写回保留其它 external attrs。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/dsl/gen_kernel/test_gen_kernel.py -k "template_header or wrapper-external-attr-mismatch or rejects_npu_demo_barrier_fail_fast_boundaries"`：exit=0，`22 passed, 77 deselected, 2 warnings`。覆盖 gen_kernel 模板头与 launch ABI mismatch。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 -m py_compile kernel_gen/dialect/__init__.py kernel_gen/dialect/nn/__init__.py kernel_gen/dialect/nn/type/__init__.py kernel_gen/dialect/nn/type/memory_type.py test/dialect/nn/test_package.py test/dialect/nn/test_type.py test/dialect/test_package.py test/dsl/gen_kernel/test_gen_kernel.py test/passes/test_template_name_infer.py`：exit=0。覆盖本轮 Python diff 语法。

计划验收命令：
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/dialect/nn test/dialect/test_package.py test/passes/test_template_name_infer.py`：exit=0，`120 passed, 2 warnings`。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/dsl/gen_kernel`：exit=0，`186 passed, 2 warnings`。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/dsl/gen_kernel/emit/test_package.py test/dsl/gen_kernel/test_gen_kernel.py`：exit=0，`172 passed, 2 warnings`。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 -m py_compile kernel_gen/dialect/nn/type/memory_type.py`：exit=0。
- `git diff --check`：exit=0，无输出。
- `git diff --name-only -- expectation .skills agents/standard AGENTS.md TODO.md DONE.md`：exit=0，无输出。

合同验收说明：
- 本计划明确不新增、不修改、不要求运行 `expectation`；本轮未运行 expectation 作为通过依据。

减法检查：
- 新增 / 改动 private callable：
  - `kernel_gen/dialect/nn/type/memory_type.py::_normalize_template_name_attr(...)`：既有 helper 改为 external_attrs 合并真源使用；有效代码不少于 5 行；不调用其它 private callable；保留原因是构造与 clone helper 都需要统一规范化 `str | StringAttr | None` 并复用稳定失败语义。
  - `_NnMemoryTypeRules.verify_external_attr_key(...)`、`dictionary_from_external_attrs(...)`、`merge_template_name_into_external_attrs(...)`、`external_attrs_without_template_name(...)`、`external_attrs_with_attr(...)`：当前文件局部规则容器方法，不导出、不跨文件调用；用于集中 verifier/copy 规则，避免散落重复逻辑。
  - `test/passes/test_template_name_infer.py::_memory_type(...)`：仅扩展测试 helper 参数以构造公开 `external_attrs` 输入；未引入跨文件非公开 API。
  - `test/dsl/gen_kernel/test_gen_kernel.py::_make_memory_type(...)`：仅扩展测试 helper 参数以构造公开 `external_attrs` 输入；未引入跨文件非公开 API。
- 删除 / 替代旧逻辑：
  - 删除了类内重复 `_normalize_template_name_attr(...)` 死代码，只保留模块级实际 helper。
  - 旧 `NnMemoryType.template_name` param 真源被 `external_attrs` 替代；保留 property 作为公开兼容读取入口。
- 保留旧逻辑依据：
  - legacy `template = T1` parse 路径按计划保留为输入兼容；canonical print 不再保留旧文本。
  - 下游 `.template_name.data` 调用点不批量改写，因计划要求 Python 侧访问兼容。
- 静态边界扫描：
  - `rg -n "hasattr\\(ctx|getattr\\(ctx|callable\\(getattr\\(ctx|def [A-Za-z_][A-Za-z0-9_]*\\([^)]*object" kernel_gen/dialect/nn/type/memory_type.py kernel_gen/dialect/nn/__init__.py kernel_gen/dialect/__init__.py test/dialect/nn/test_type.py test/passes/test_template_name_infer.py test/dsl/gen_kernel/test_gen_kernel.py`：exit=1，无输出；未引入 ctx 能力探测或 object 签名。

候选文件列表：
- `kernel_gen/dialect/__init__.py`
- `kernel_gen/dialect/nn/__init__.py`
- `kernel_gen/dialect/nn/type/__init__.py`
- `kernel_gen/dialect/nn/type/memory_type.py`
- `spec/dialect/nn.md`
- `spec/dsl/gen_kernel/kernel_emitter.md`
- `spec/pass/template_name_infer.md`
- `test/dialect/nn/test_package.py`
- `test/dialect/nn/test_type.py`
- `test/dialect/test_package.py`
- `test/dsl/gen_kernel/test_gen_kernel.py`
- `test/passes/test_template_name_infer.py`
- `agents/codex-multi-agents/log/task_records/2026/25/20260527-thirdparty-nn-memory-external-attrs-plan.md`

自检：
- 公开 API 变更已有计划书用户确认来源，新增 `copy_memory_type_with_external_attr(...)` 已同步 spec/API 列表、导出面和公开 pytest。
- 未修改 `expectation/`、`.skills/`、`agents/standard/`、`AGENTS.md`、`TODO.md`、`DONE.md`。
- 未跨文件调用非公开 helper；测试只通过公开 API、公开 parser/printer、公开 pass 与 gen_kernel 行为观测。
- wrapper/body ABI 只忽略 template name 的要求已通过公开 gen_kernel 负例锁定。
- 当前无阻塞项；可进入 review。

流转记录：
- `bash skills/codex-multi-agents/scripts/codex-multi-agents-task.sh -file TODO.md -next -task_id T-20260528-8ad7e551 -from 小李飞刀 -type review -message 'review；任务目标：审查 plan/1.md 的 NnMemoryType external_attrs/template_name 迁移、copy helper、parser/printer/verifier、template_name infer、gen_kernel ABI、spec/test、Diff 反推自测和禁止修改面记录；任务链记录：agents/codex-multi-agents/log/task_records/2026/25/20260527-thirdparty-nn-memory-external-attrs-plan.md' -agents-list agents/codex-multi-agents/agents-lists.md -auto`：exit=0，已自动分发 review 给 `提莫炖蘑菇`，脚本已通知 `神秘人`。

时间：2026-05-28 01:12 +0800
经办人：提莫炖蘑菇
阶段：review

审查前同步：
- 执行目录：`/home/lfr/kernelcode_generate`
- `git fetch origin`：exit=0。
- `HEAD=479ef47e2cd93f3810b891ce6cf3b053ca360b41`
- `origin/main=479ef47e2cd93f3810b891ce6cf3b053ca360b41`
- `merge-base=479ef47e2cd93f3810b891ce6cf3b053ca360b41`
- `git rev-list --left-right --count HEAD...origin/main`：`0 0`。
- 同步结论：当前主仓 worktree 已在 latest `origin/main` 基线上；候选 diff 为当前主仓未提交工作区改动，无需 merge。

审查范围：
- 计划书：`plan/1.md`
- 候选实现 / spec / test：`kernel_gen/dialect/__init__.py`、`kernel_gen/dialect/nn/__init__.py`、`kernel_gen/dialect/nn/type/__init__.py`、`kernel_gen/dialect/nn/type/memory_type.py`、`spec/dialect/nn.md`、`spec/dsl/gen_kernel/kernel_emitter.md`、`spec/pass/template_name_infer.md`、`test/dialect/nn/test_package.py`、`test/dialect/nn/test_type.py`、`test/dialect/test_package.py`、`test/dsl/gen_kernel/test_gen_kernel.py`、`test/passes/test_template_name_infer.py`。
- 敏感目录：`expectation/`、`.skills/`、`agents/standard/`。

审查发现：
- 阻断：`test/passes/test_template_name_infer.py:49` 本轮改动了 private callable `_memory_type(...)`，但该 helper 仍在 `test/passes/test_template_name_infer.py:53` 与 `test/passes/test_template_name_infer.py:54` 调用同文件 private callable `_symbol_array(...)`。这命中 `agents/standard/审查规范.md` 的私有函数审查硬规则：本轮新增或改动的 `private callable` 不得调用其它 `private callable`，测试也不得以 private helper 链路绕过公开 API。最小返工：将 `_memory_type(...)` 内的 `_symbol_array(("M",))` / `_symbol_array(("1",))` 调用内联为公开 `ArrayAttr([SymbolExprAttr.from_expr(...)])` 构造，或合并 helper，确保改动后的 private callable 不再调用 private callable。

Diff 反推审查：
- `NnMemoryType` 真实参数迁移到 `external_attrs`、`template_name` property、legacy `template = T1` parse、canonical `external_attrs = {...}` print、copy helper 语义、template-name infer 保留其它 external attrs、gen_kernel wrapper/body ABI 只忽略 template_name 的测试覆盖与计划目标基本对齐。
- `kernel_gen/dsl/gen_kernel/kernel_emitter.py` 既有 `_same_launch_signature_without_template_names(...)` 继续通过公开 `copy_memory_type(...)` 清除 template name；由于本轮 `copy_memory_type(...)` 保留非 template external attrs，wrapper/body 非 template external attr 差异会参与比较，方向符合计划。
- 公开 API 新增 `copy_memory_type_with_external_attr(...)` 已有计划书用户确认来源，并同步到 spec、文件级 API 列表、包根导出和公开 pytest。
- 静态扫描命中 `importlib` 仅出现在既有公开模块存在性 / 旧路径负例测试中，不是本轮新增能力探测或私有 API 绕过；本轮阻断项仍以上述 private-to-private 调用为准。

复跑验证：
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/dialect/nn test/dialect/test_package.py test/passes/test_template_name_infer.py`：exit=0，`120 passed, 2 warnings`。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/dsl/gen_kernel`：exit=0，`186 passed, 2 warnings`。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/dsl/gen_kernel/emit/test_package.py test/dsl/gen_kernel/test_gen_kernel.py`：exit=0，`172 passed, 2 warnings`。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 -m py_compile kernel_gen/dialect/nn/type/memory_type.py`：exit=0。
- `git diff --check`：exit=0。
- `git diff --name-only -- expectation .skills agents/standard`：exit=0，无输出。
- `git diff --cached --name-only -- expectation .skills agents/standard`：exit=0，无输出。
- `git status --short --untracked-files=all -- expectation .skills agents/standard`：exit=0，无输出。

减法审查：
- 本轮实现侧删除了旧 `NnMemoryType.template_name` 真实 param，改由 `external_attrs` 承载；legacy parse 只作为输入兼容保留，canonical print 已迁移为 `external_attrs`，保留依据与计划一致。
- 本轮新增公开 helper `copy_memory_type_with_external_attr(...)` 有用户确认来源和 spec/API 列表支撑，不按 private callable 处理。
- 本轮改动 private callable 中，`test/passes/test_template_name_infer.py::_memory_type(...)` 未满足“private callable 不得调用 private callable”，需退回修复。

结论：
- `review` 不通过，退回 `execute`。
- 最小需改项：收口 `test/passes/test_template_name_infer.py::_memory_type(...)` 的 private-to-private 调用链，并复跑本记录中的 Diff 反推 pytest、计划 pytest、`py_compile`、`git diff --check` 与敏感目录门禁。

时间：2026-05-28 00:49 +0800
经办人：金铲铲大作战
阶段：execute 返工

返工目标：
- 仅按 review 最小项收口 `test/passes/test_template_name_infer.py` 中本轮改动 private callable 的 private-to-private 调用链。
- 禁止扩大到 `plan/2.md`；禁止修改 `expectation/`、`.skills/`、`agents/standard/`、`AGENTS.md`、`TODO.md`、`DONE.md`。

实际改动：
- 删除同文件浅 helper `_symbol_array(...)`。
- 将 `_memory_type(...)`、`_byte_pool_type(...)`、`_typed_tsm_type(...)` 内部的 `_symbol_array(...)` 调用改为直接使用公开 `ArrayAttr([SymbolExprAttr.from_expr(...)])` 构造。
- `_memory_type(...)` 继续保留本计划已有 `external_attrs` 参数并传入 `NnMemoryType(...)`；未新增公开 API，未修改业务实现行为。

减法检查：
- 删除 `_symbol_array(...)` 后，本文件不再保留只为转发公开构造的浅 private callable。
- 未新增 private callable；未引入 private callable 调用 private callable。
- 未恢复旧兼容入口，未修改 expectation 或标准文件，未扩大计划边界。

静态边界扫描：
- `python3 - <<'PY' ...` 扫描 `test/passes/test_template_name_infer.py` 中 private callable 对同文件 private callable 的直接调用：exit=0，输出 `private_to_private_calls: []`。

Diff 反推自测：
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/passes/test_template_name_infer.py`：exit=0，`11 passed, 2 warnings`。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 -m py_compile test/passes/test_template_name_infer.py`：exit=0。

计划 pytest / 记录要求复跑：
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/dialect/nn test/dialect/test_package.py test/passes/test_template_name_infer.py`：exit=0，`120 passed, 2 warnings`。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/dsl/gen_kernel`：第一次 120s 超时，仅输出部分进度；使用 300s 超时复跑 exit=0，`186 passed, 2 warnings`。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/dsl/gen_kernel/emit/test_package.py test/dsl/gen_kernel/test_gen_kernel.py`：exit=0，`172 passed, 2 warnings`。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 -m py_compile kernel_gen/dialect/nn/type/memory_type.py test/passes/test_template_name_infer.py test/dsl/gen_kernel/test_gen_kernel.py`：exit=0。

格式与敏感目录门禁：
- `git diff --check`：exit=0。
- `git diff --name-only -- expectation .skills agents/standard AGENTS.md TODO.md DONE.md`：exit=0，无输出。
- `git diff --cached --name-only -- expectation .skills agents/standard AGENTS.md TODO.md DONE.md`：exit=0，无输出。
- `git status --short --untracked-files=all -- expectation .skills agents/standard AGENTS.md TODO.md DONE.md`：exit=0，无输出。

自检：
- 本轮只触达 `test/passes/test_template_name_infer.py` 与本任务记录。
- `_memory_type(...)` private-to-private 阻断已消除；同文件其它 sibling helper 也同步消除同类浅 helper 调用，避免复审同规则再次命中。
- 测试仍通过公开 `NnMemoryType` / `ArrayAttr` / `SymbolExprAttr` 行为构造输入，未直连跨文件非公开 API。
- 当前 `git status --short` 仍显示一个非本轮触达的未跟踪 `spec/pass/symbol_iter_eliminate.md`；本轮未修改、未清理、未纳入本任务候选说明。

结论：
- `execute` 返工完成，可回流 `review`。

时间：2026-05-28 00:53 +0800
经办人：提莫炖蘑菇
阶段：review 复审

审查前同步：
- 执行目录：`/home/lfr/kernelcode_generate`
- `git fetch origin`：exit=0。
- `HEAD=479ef47e2cd93f3810b891ce6cf3b053ca360b41`
- `origin/main=479ef47e2cd93f3810b891ce6cf3b053ca360b41`
- `merge-base=479ef47e2cd93f3810b891ce6cf3b053ca360b41`
- `git rev-list --left-right --count HEAD...origin/main`：`0 0`。
- 同步结论：当前主仓 worktree 已在 latest `origin/main` 基线上；候选 diff 为当前未提交工作区改动，无需 merge。

复审范围：
- 计划书：`plan/1.md`
- 重点返工文件：`test/passes/test_template_name_infer.py`
- 候选 diff：`kernel_gen/dialect/__init__.py`、`kernel_gen/dialect/nn/__init__.py`、`kernel_gen/dialect/nn/type/__init__.py`、`kernel_gen/dialect/nn/type/memory_type.py`、`spec/dialect/nn.md`、`spec/dsl/gen_kernel/kernel_emitter.md`、`spec/pass/template_name_infer.md`、`test/dialect/nn/test_package.py`、`test/dialect/nn/test_type.py`、`test/dialect/test_package.py`、`test/dsl/gen_kernel/test_gen_kernel.py`、`test/passes/test_template_name_infer.py`、本任务记录。
- 范围隔离：当前工作区仍存在非本任务未跟踪文件 `spec/pass/symbol_iter_eliminate.md`；本轮未读取为候选 diff、未修改、未纳入通过范围，后续 merge 不应合入该文件。

复审发现：
- 阻断项：无。
- 重复问题复核：上一轮阻断的 `test/passes/test_template_name_infer.py::_memory_type(...)` private callable 调用 `_symbol_array(...)` private callable 已修复；`_symbol_array(...)` 已删除，`_memory_type(...)`、`_byte_pool_type(...)`、`_typed_tsm_type(...)` 均直接使用公开 `ArrayAttr([SymbolExprAttr.from_expr(...)])` 构造。
- 新增问题：无。
- 范围扩大：无；返工仅触达 `test/passes/test_template_name_infer.py` 和任务记录。

Diff 反推审查：
- `test/passes/test_template_name_infer.py` 的返工直接对应上一轮阻断，去掉浅 private helper 并消除 private-to-private 调用链。
- `NnMemoryType.external_attrs`、`copy_memory_type_with_external_attr(...)`、legacy `template = T1` parse、canonical print、template-name infer 保留其它 external attrs、gen_kernel ABI 只忽略 `template_name` 的前序审查结论未回退。
- 公开 API 变更仍有 `plan/1.md` 用户确认来源；spec/API 列表、文件级 API 列表、包根导出和公开 pytest 保持同步。
- 本计划无必过 `expectation`；本轮未把 expectation 作为通过依据。

复跑验证：
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/passes/test_template_name_infer.py`：exit=0，`11 passed, 2 warnings`。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/dialect/nn test/dialect/test_package.py test/passes/test_template_name_infer.py`：exit=0，`120 passed, 2 warnings`。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/dsl/gen_kernel`：exit=0，`186 passed, 2 warnings`。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/dsl/gen_kernel/emit/test_package.py test/dsl/gen_kernel/test_gen_kernel.py`：exit=0，`172 passed, 2 warnings`。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 -m py_compile test/passes/test_template_name_infer.py kernel_gen/dialect/nn/type/memory_type.py`：exit=0。
- `python3 - <<'PY' ...` AST 扫描 `test/passes/test_template_name_infer.py` private callable 对同文件 private callable 的直接调用：exit=0，`private_to_private_calls: []`。
- `rg -n "_symbol_array|_memory_type\\(|ArrayAttr\\(\\[SymbolExprAttr\\.from_expr" test/passes/test_template_name_infer.py`：exit=0，确认 `_symbol_array` 无命中，公开构造内联命中位于 `_memory_type`、`_byte_pool_type`、`_typed_tsm_type`。
- `git diff --check`：exit=0。
- `git diff --name-only -- expectation .skills agents/standard AGENTS.md TODO.md DONE.md`：exit=0，无输出。
- `git diff --cached --name-only -- expectation .skills agents/standard AGENTS.md TODO.md DONE.md`：exit=0，无输出。
- `git status --short --untracked-files=all -- expectation .skills agents/standard AGENTS.md TODO.md DONE.md`：exit=0，无输出。

减法审查：
- 本轮返工删除了 `_symbol_array(...)`，去掉只封装公开 `ArrayAttr` / `SymbolExprAttr` 构造的浅 private helper。
- 改动后的 `_memory_type(...)` 不再调用其它 private callable，AST 扫描为 `[]`。
- 其它候选实现仍维持上一轮已核对的迁移方向：旧 `NnMemoryType.template_name` 真实 param 被 `external_attrs` 替代；legacy parser 仅作输入兼容；`copy_memory_type(...)` 只清除 template_name 并保留其它 external attrs。

自检：
- 已逐项读取返工 diff、任务记录和计划重点；已复跑计划 pytest、Diff 反推 pytest、py_compile、diff check 与敏感目录门禁。
- 已完成 private callable 复审，上一轮阻断已收口。
- 已隔离非候选未跟踪文件 `spec/pass/symbol_iter_eliminate.md`，不作为本任务通过依据或合入范围。

结论：
- `review` 通过。
- 本任务为计划级 execute 落地任务，下一阶段应进入 `archive_acceptance / 计划书入档验收`，不得直接 merge。

时间：2026-05-28 01:20 +0800
经办人：神秘人
阶段：管理员迁移协调

迁移原因：
- 用户指出本任务常规执行与任务记录不应落在主仓 `/home/lfr/kernelcode_generate`，应位于独立 worktree。
- 原任务 `T-20260528-8ad7e551` 的 TODO worktree 字段误设为主仓，且任务已进入 `archive_acceptance`；标准任务脚本不支持直接修改运行中任务的 worktree 字段，也禁止直接创建 `archive_acceptance` 新任务。

管理员处置：
- 已暂停并删除误设主仓 worktree 的 `T-20260528-8ad7e551` 状态行。
- 已创建独立 worktree `/home/lfr/kernelcode_generate/wt-20260527-thirdparty-nn-memory-external-attrs`，分支 `task/thirdparty-nn-memory-external-attrs`。
- 已将原任务记录明确候选文件与本记录迁移到该独立 worktree。
- 已从主仓撤出同批候选 diff；主仓仍保留非本任务未归属的 `symbol` 相关本地改动和未跟踪 `spec/pass/symbol_iter_eliminate.md`，本任务不得纳入。
- 已新建替代任务 `T-20260528-2936d50e`，任务类型为 `review`，用于在独立 worktree 复核迁移后候选与原 review 通过记录一致，再按计划级流程进入 `archive_acceptance`。

迁移后的候选范围：
- `kernel_gen/dialect/__init__.py`
- `kernel_gen/dialect/nn/__init__.py`
- `kernel_gen/dialect/nn/type/__init__.py`
- `kernel_gen/dialect/nn/type/memory_type.py`
- `spec/dialect/nn.md`
- `spec/dsl/gen_kernel/kernel_emitter.md`
- `spec/pass/template_name_infer.md`
- `test/dialect/nn/test_package.py`
- `test/dialect/nn/test_type.py`
- `test/dialect/test_package.py`
- `test/dsl/gen_kernel/test_gen_kernel.py`
- `test/passes/test_template_name_infer.py`
- `agents/codex-multi-agents/log/task_records/2026/25/20260527-thirdparty-nn-memory-external-attrs-plan.md`

禁止纳入：
- `kernel_gen/dialect/symbol/operation/arith.py`
- `spec/dialect/symbol.md`
- `test/dialect/symbol/test_symbol.py`
- `spec/pass/symbol_iter_eliminate.md`

下一步：
- `T-20260528-2936d50e` 从独立 worktree 进入 `review`，review 通过后进入 `archive_acceptance`，不得直接 merge。

时间：2026-05-28 12:44 +0800
经办人：提莫炖蘑菇
任务：T-20260528-2936d50e / review
任务目标：在独立 worktree 复核迁移后 `thirdparty nn memory external_attrs` 候选 diff 与原 review 通过记录一致，隔离主仓 `symbol_iter` / `symbol fold` 非候选改动，并按计划级流程续接 `archive_acceptance`。

审查前同步：
- 执行目录：`/home/lfr/kernelcode_generate/wt-20260527-thirdparty-nn-memory-external-attrs`
- 分支：`task/thirdparty-nn-memory-external-attrs`
- `git fetch origin`：exit=0。
- `HEAD=479ef47e2cd93f3810b891ce6cf3b053ca360b41`
- `origin/main=479ef47e2cd93f3810b891ce6cf3b053ca360b41`
- `merge-base=479ef47e2cd93f3810b891ce6cf3b053ca360b41`
- `git rev-list --left-right --count HEAD...origin/main`：`0 0`。
- 同步结论：独立 worktree 已在 latest `origin/main` 基线上；候选 diff 为当前 worktree 未提交改动，无需合并，不存在覆盖任务 diff 风险。

计划与记录来源：
- 当前独立 worktree 内不存在 `plan/1.md`；本轮按管理员迁移记录和主仓只读计划 `/home/lfr/kernelcode_generate/plan/1.md` 核对计划合同真源，未复制、新建或修改计划资产。
- 已读取本任务记录中 execute、第一次 review、execute 返工、review 通过、管理员迁移协调和迁移候选范围。

候选范围核对：
- `git diff --name-only` 输出仅包含 12 个候选文件：`kernel_gen/dialect/__init__.py`、`kernel_gen/dialect/nn/__init__.py`、`kernel_gen/dialect/nn/type/__init__.py`、`kernel_gen/dialect/nn/type/memory_type.py`、`spec/dialect/nn.md`、`spec/dsl/gen_kernel/kernel_emitter.md`、`spec/pass/template_name_infer.md`、`test/dialect/nn/test_package.py`、`test/dialect/nn/test_type.py`、`test/dialect/test_package.py`、`test/dsl/gen_kernel/test_gen_kernel.py`、`test/passes/test_template_name_infer.py`。
- `git status --short --untracked-files=all` 额外仅显示本任务记录未跟踪文件 `agents/codex-multi-agents/log/task_records/2026/25/20260527-thirdparty-nn-memory-external-attrs-plan.md`。
- `git diff --name-only -- kernel_gen/dialect/symbol/operation/arith.py spec/dialect/symbol.md test/dialect/symbol/test_symbol.py spec/pass/symbol_iter_eliminate.md`：exit=0，无输出。
- `git status --short --untracked-files=all -- kernel_gen/dialect/symbol/operation/arith.py spec/dialect/symbol.md test/dialect/symbol/test_symbol.py spec/pass/symbol_iter_eliminate.md`：exit=0，无输出。
- 结论：迁移后候选范围与管理员记录一致；主仓 `symbol_iter` / `symbol fold` 非候选改动未进入独立 worktree 候选 diff。

审查发现：
- 阻断项：无。
- 重复问题复核：原 review 阻断的 `test/passes/test_template_name_infer.py::_memory_type(...)` 调用 `_symbol_array(...)` private callable 已收口；`_symbol_array(...)` 已删除，相关测试 helper 直接使用公开 `ArrayAttr([SymbolExprAttr.from_expr(...)])` 构造。
- 新增问题：无。
- 范围扩大：无；候选 diff 未混入禁止纳入的 symbol 相关文件。

Diff 反推审查：
- `kernel_gen/dialect/nn/type/memory_type.py` 将 `NnMemoryType` 真实参数迁移为 `external_attrs`，保留 `template_name=` 构造兼容和 `.template_name` property；`copy_memory_type(...)` 只清除 `template_name` 并保留其它 external attrs；新增 `copy_memory_type_with_external_attr(...)` 有计划书用户确认来源。
- `spec/dialect/nn.md`、`spec/pass/template_name_infer.md`、`spec/dsl/gen_kernel/kernel_emitter.md` 已同步 external attrs、template-name infer 写回和 gen_kernel ABI 只忽略 `external_attrs["template_name"]` 的公开合同。
- `test/dialect/nn/test_type.py`、`test/passes/test_template_name_infer.py`、`test/dsl/gen_kernel/test_gen_kernel.py` 覆盖 parser/printer/verifier/copy helper、template-name infer 保留其它 external attrs、wrapper/body 非 template external attr mismatch。
- 本计划无必过 `expectation`；本轮未把 `expectation` 作为通过依据。

复跑验证：
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/passes/test_template_name_infer.py`：exit=0，`11 passed, 2 warnings`。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/dialect/nn test/dialect/test_package.py test/passes/test_template_name_infer.py`：exit=0，`120 passed, 2 warnings`。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/dsl/gen_kernel`：exit=0，`186 passed, 2 warnings`。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/dsl/gen_kernel/emit/test_package.py test/dsl/gen_kernel/test_gen_kernel.py`：exit=0，`172 passed, 2 warnings`。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 -m py_compile test/passes/test_template_name_infer.py kernel_gen/dialect/nn/type/memory_type.py test/dsl/gen_kernel/test_gen_kernel.py`：exit=0。
- `python3 - <<'PY' ...` AST 扫描 `test/passes/test_template_name_infer.py` private callable 对同文件 private callable 的直接调用：exit=0，`private_to_private_calls: []`。
- `rg -n "_symbol_array|hasattr\\(ctx|getattr\\(ctx|callable\\(getattr\\(ctx|def [A-Za-z_][A-Za-z0-9_]*\\([^)]*object" test/passes/test_template_name_infer.py kernel_gen/dialect/nn/type/memory_type.py test/dsl/gen_kernel/test_gen_kernel.py || true`：exit=0，无输出。
- `git diff --check`：exit=0，无输出。
- `git diff --name-only -- expectation .skills agents/standard AGENTS.md TODO.md DONE.md`：exit=0，无输出。
- `git diff --cached --name-only -- expectation .skills agents/standard AGENTS.md TODO.md DONE.md`：exit=0，无输出。
- `git status --short --untracked-files=all -- expectation .skills agents/standard AGENTS.md TODO.md DONE.md`：exit=0，无输出。

减法审查：
- 旧 `NnMemoryType.template_name` 真实 param 已由 `external_attrs` 替代；legacy `template = T1` 仅保留为输入兼容并 canonical print 为 `external_attrs = {...}`，保留依据与计划一致。
- 返工已删除浅 helper `_symbol_array(...)`，消除 private callable 调用 private callable 的阻断链路。
- 未恢复旧 `memory_template_name(...)` / `has_memory_template_name(...)`；未混入 symbol_iter/symbol fold 非候选改动。

自检：
- 已逐项读取迁移后实际 diff、任务记录与主仓只读计划；已复核候选范围、禁止纳入文件、公开 API/spec/test 同步、private callable 边界、Diff 反推测试和敏感目录门禁。
- 独立 worktree 缺 `plan/1.md` 已记录为计划来源差异；本轮任务目标是迁移后候选 diff 复核，候选 diff 不含计划资产变更，未因此阻断。
- 未修改 `expectation/`、`.skills/`、`agents/standard/`、`AGENTS.md`、`TODO.md`、`DONE.md`。

结论：
- `review` 通过。
- 该任务为计划级任务，下一阶段应进入 `archive_acceptance / 计划书入档验收`，不得直接 merge。

时间：2026-05-28 12:50 +0800
经办人：不要啊教练
阶段：archive_acceptance / 计划书入档验收
任务：T-20260528-2936d50e / thirdparty-nn-memory-external-attrs-template-name
任务目标：核对独立 worktree 迁移候选、review 通过记录、Diff 反推审查、计划 pytest、py_compile、git diff check、敏感目录空 diff、主仓 symbol_iter / symbol fold 非候选隔离与可入档性。

入档前同步现场：
- 执行目录：`/home/lfr/kernelcode_generate/wt-20260527-thirdparty-nn-memory-external-attrs`
- 分支：`task/thirdparty-nn-memory-external-attrs`
- `git fetch origin`：exit=0。
- `HEAD=479ef47e2cd93f3810b891ce6cf3b053ca360b41`
- `origin/main=479ef47e2cd93f3810b891ce6cf3b053ca360b41`
- `merge-base=479ef47e2cd93f3810b891ce6cf3b053ca360b41`
- `git rev-list --left-right --count HEAD...origin/main`：`0 0`。
- 同步结论：独立 worktree 与 latest `origin/main` 对齐，当前候选 diff 可审；未发现冲突或覆盖风险。

计划与迁移口径：
- 当前独立 worktree 内 `plan/1.md` 缺失；按管理员迁移协调记录，本轮只读引用主仓 `/home/lfr/kernelcode_generate/plan/1.md` 作为计划合同真源，未复制、新建或修改计划资产。
- 主仓 `plan/1.md` 本身未被 git 跟踪；本轮不把计划书纳入候选 diff。
- 管理员迁移记录已明确禁止纳入主仓 `symbol_iter` / `symbol fold` 非候选文件：`kernel_gen/dialect/symbol/operation/arith.py`、`spec/dialect/symbol.md`、`test/dialect/symbol/test_symbol.py`、`spec/pass/symbol_iter_eliminate.md`。

候选范围核对：
- `git diff --name-status --find-renames` 候选 tracked diff：
  - `kernel_gen/dialect/__init__.py`
  - `kernel_gen/dialect/nn/__init__.py`
  - `kernel_gen/dialect/nn/type/__init__.py`
  - `kernel_gen/dialect/nn/type/memory_type.py`
  - `spec/dialect/nn.md`
  - `spec/dsl/gen_kernel/kernel_emitter.md`
  - `spec/pass/template_name_infer.md`
  - `test/dialect/nn/test_package.py`
  - `test/dialect/nn/test_type.py`
  - `test/dialect/test_package.py`
  - `test/dsl/gen_kernel/test_gen_kernel.py`
  - `test/passes/test_template_name_infer.py`
- `git status --short --untracked-files=all` 额外仅显示本任务记录未跟踪文件：`agents/codex-multi-agents/log/task_records/2026/25/20260527-thirdparty-nn-memory-external-attrs-plan.md`。
- 主仓非候选现场仍存在：`kernel_gen/dialect/symbol/operation/arith.py`、`spec/dialect/symbol.md`、`test/dialect/symbol/test_symbol.py` 的本地修改，以及未跟踪 `spec/pass/symbol_iter_eliminate.md`。
- 独立 worktree 对上述四个 symbol 相关非候选路径执行 `git diff --name-only` 与 `git status --short --untracked-files=all` 均无输出；隔离成立。

findings：
1. 阻断：主仓计划 `/home/lfr/kernelcode_generate/plan/1.md:17-19` 已确认 `NnMemoryType.external_attrs -> DictionaryAttr` 与 `NnMemoryType.template_name -> StringAttr` 属于目标公开 API，但候选 `spec/dialect/nn.md:7-13` 的 `API 列表` 未列这两个 class public property，`kernel_gen/dialect/nn/type/memory_type.py:6-10` 的文件级 `API 列表` 也未列这两个公开 property。
   - 影响：`NnMemoryType` class 的公开 API 真源没有闭合，违反 class 场景需逐条列类公开 API 的规范；后续 review / merge 无法机械判断这两个 property 的签名、返回值、错误语义和兼容边界是否受合同保护。
   - 最小返工动作：在 `spec/dialect/nn.md` 顶部 `API 列表` 与 `API详细说明` 中补齐 `NnMemoryType.external_attrs -> DictionaryAttr`、`NnMemoryType.template_name -> StringAttr` 两个条目；在 `kernel_gen/dialect/nn/type/memory_type.py` 文件级 `API 列表` 中同步列出这两个 class public property。若 package root `__init__` 文件的 API 列表只作为导出对象清单而不展开 class property，需要在返工记录中写清不展开依据；否则也同步补齐。
   - 验收方式：复跑 `pytest -q test/dialect/nn test/dialect/test_package.py test/passes/test_template_name_infer.py`、`pytest -q test/dsl/gen_kernel`、`pytest -q test/dsl/gen_kernel/emit/test_package.py test/dsl/gen_kernel/test_gen_kernel.py`、`py_compile`、`git diff --check`、敏感目录门禁与非候选隔离检查。
2. 阻断：候选 `spec/dialect/nn.md:151-161` 中 `copy_memory_type(...)` 与 `copy_memory_type_with_template_name(...)` 两个公开 API 详细说明仍只有 `api / 功能说明 / 注意事项`，缺少当前 `spec` 标准要求的 `参数 / 返回值 / 使用示例` 字段。本轮 diff 已修改这两个条目的公开行为说明，不能按存量缺口放行。
   - 影响：两个 copy helper 的公开参数默认值、是否允许 `None`、返回值、示例和错误边界无法从 spec 机械核验，尤其本任务改变了 `template_name` 与其它 `external_attrs` 的保留/清除合同。
   - 最小返工动作：在 `spec/dialect/nn.md` 的这两个 API 详细说明条目中补齐 `参数`、`返回值`、`使用示例`，并把 `shape/stride/element_type/space` 可选替换、`template_name` 合法性、其它 `external_attrs` 保留语义写入对应字段。
   - 验收方式：同上，并额外人工核对 `api` 字段与顶部 `API 列表` 完全一致。

Diff 反推审查：
- `NnMemoryType` 真实参数迁移为 `external_attrs`、legacy `template = T1` parse、canonical `external_attrs = {...}` print、copy helper 保留非 template attrs、template-name infer 保留其它 attrs、gen_kernel ABI 只忽略 `template_name` 的测试方向与计划目标一致。
- `test/passes/test_template_name_infer.py` 前轮 private-to-private 阻断已修复：`_symbol_array(...)` 已删除，AST 扫描 `private_to_private_calls: []`。
- Review 通过记录中的候选范围和迁移隔离结论基本成立；本轮入档阻断只针对公开 API/spec 结构闭合，不是实现行为测试失败。
- 本计划无必过 `expectation`；未运行 expectation 作为通过依据，候选 diff 未包含 `expectation/`。

复跑验证：
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/dialect/nn test/dialect/test_package.py test/passes/test_template_name_infer.py`：exit=0，`120 passed, 2 warnings`。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/dsl/gen_kernel`：exit=0，`186 passed, 2 warnings`。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/dsl/gen_kernel/emit/test_package.py test/dsl/gen_kernel/test_gen_kernel.py`：exit=0，`172 passed, 2 warnings`。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 -m py_compile kernel_gen/dialect/nn/type/memory_type.py`：exit=0，输出 `py_compile-ok`。
- `python3 - <<'PY' ...` AST 扫描 `test/passes/test_template_name_infer.py` private callable 对同文件 private callable 的直接调用：exit=0，`private_to_private_calls: []`。
- `rg -n '_symbol_array|hasattr\(ctx|getattr\(ctx|callable\(getattr\(ctx|def [A-Za-z_][A-Za-z0-9_]*\([^)]*object' test/passes/test_template_name_infer.py kernel_gen/dialect/nn/type/memory_type.py test/dsl/gen_kernel/test_gen_kernel.py || true`：exit=0，无输出。
- `git diff --check`：exit=0，输出 `diff-check-ok`。
- 敏感目录门禁：
  - `git diff --name-only -- expectation .skills agents/standard AGENTS.md TODO.md DONE.md`：exit=0，无输出。
  - `git diff --cached --name-only -- expectation .skills agents/standard AGENTS.md TODO.md DONE.md`：exit=0，无输出。
  - `git status --short --untracked-files=all -- expectation .skills agents/standard AGENTS.md TODO.md DONE.md`：exit=0，无输出。
- 主仓非候选隔离：主仓仍有 symbol 相关本地改动；独立 worktree 对 `kernel_gen/dialect/symbol/operation/arith.py spec/dialect/symbol.md test/dialect/symbol/test_symbol.py spec/pass/symbol_iter_eliminate.md` 的 `git diff --name-only` 与 `git status --short --untracked-files=all` 均无输出。

减法审查：
- 旧 `NnMemoryType.template_name` 真实 param 已由 `external_attrs` 替代；legacy `template = T1` 仅作为输入兼容保留，canonical print 已迁移为 `external_attrs = {...}`。
- `_symbol_array(...)` 浅 private helper 已删除，private callable 链路阻断消除。
- 未恢复 `memory_template_name(...)` / `has_memory_template_name(...)`；未混入主仓 symbol_iter / symbol fold 非候选改动。

自检：
- 已读取个人 prompt、根 `AGENTS.md`、审查规范、任务记录约定、主仓只读计划、迁移记录、review 通过记录和实际 diff。
- 已核对 latest 同步现场、候选范围、非候选隔离、计划 pytest、py_compile、git diff check、敏感目录空 diff和无必过 expectation 口径。
- 已发现并定位公开 API/spec 结构阻断；当前仍有可执行返工项，因此不得给出 archive_acceptance 通过。
- 本轮仅追加任务记录，未修改业务实现、spec、测试、计划书、`expectation/`、`.skills`、`agents/standard` 或任务状态文件。

结论：
- `archive_acceptance` 结论：最小需改项 / 不通过。
- 下一步：退回 `execute`，仅收口上述两个 spec/API 列表阻断项，并保持主仓 symbol_iter / symbol fold 非候选隔离；返工后重新 review，再进入 archive_acceptance。

时间：2026-05-28 12:57 +0800
经办人：金铲铲大作战
阶段：execute / archive_acceptance 返工
任务：T-20260528-2936d50e / thirdparty-nn-memory-external-attrs-template-name
任务目标：只收口 archive_acceptance 指出的两处 `spec/API 列表` 与公开 API 详细说明阻断，不修改实现主逻辑，不触碰 `expectation/`、`.skills/`、`agents/standard/`、`AGENTS.md`、`TODO.md`、`DONE.md`，并保持主仓 `symbol_iter` / `symbol fold` 非候选隔离。

执行前阅读记录：
- 已读取当前 worktree 内个人提示词 `agents/codex-multi-agents/agents/金铲铲大作战/金铲铲大作战.prompt.md`、根 `AGENTS.md`、`agents/standard/任务记录约定.md`、`agents/standard/spec文件规范.md`、`agents/standard/实现文件规范.md`。
- 已读取主仓只读计划真源 `/home/lfr/kernelcode_generate/plan/1.md`，确认用户已确认公开 API 包含 `NnMemoryType.external_attrs -> DictionaryAttr`、`NnMemoryType.template_name -> StringAttr`、`copy_memory_type(...)`、`copy_memory_type_with_template_name(...)`。
- 已读取本任务记录中 archive_acceptance 阻断：`spec/dialect/nn.md` 与 `kernel_gen/dialect/nn/type/memory_type.py` 文件级 `API 列表` 缺 property；`copy_memory_type(...)` 与 `copy_memory_type_with_template_name(...)` 详细条目缺 `参数 / 返回值 / 使用示例`。

实际改动：
- `spec/dialect/nn.md`
  - 在顶部 `API 列表` 补齐 `NnMemoryType.external_attrs -> DictionaryAttr` 与 `NnMemoryType.template_name -> StringAttr`。
  - 在 `API详细说明` 中新增 `NnMemoryType.external_attrs -> DictionaryAttr` 与 `NnMemoryType.template_name -> StringAttr` 两个条目，包含 `api / 参数 / 返回值 / 使用示例 / 功能说明 / 注意事项`。
  - 为 `copy_memory_type(...)` 补齐 `参数 / 返回值 / 使用示例`，明确基础字段可选替换、返回新 `NnMemoryType`、清除 `external_attrs["template_name"]` 且保留其它 `external_attrs`。
  - 为 `copy_memory_type_with_template_name(...)` 补齐 `参数 / 返回值 / 使用示例`，明确 `template_name` 合法性、基础字段可选替换、返回新 `NnMemoryType`、保留其它 `external_attrs` 并添加或覆盖 `external_attrs["template_name"]`。
- `kernel_gen/dialect/nn/type/memory_type.py`
  - 仅在文件级 `API 列表` 补齐 `NnMemoryType.external_attrs -> DictionaryAttr` 与 `NnMemoryType.template_name -> StringAttr`。
- 未修改实现主逻辑、测试逻辑、计划书、`expectation/`、`.skills/`、`agents/standard/`、`AGENTS.md`、`TODO.md`、`DONE.md`。

最小功能闭环：
- 本轮交付仅为公开 API 文档闭合：`spec` 顶部快速索引、`spec` 详细条目和实现文件级 `API 列表` 对齐主仓计划公开 API。
- `copy_memory_type(...)` / `copy_memory_type_with_template_name(...)` 的 `external_attrs` 保留与 `template_name` 清除 / 写入语义已在详细条目中可机械核对。
- 本轮无新增实现入口、无新增测试入口、无 expectation 合同资产要求。

Diff 反推自测：
- 改动文件：`spec/dialect/nn.md`、`kernel_gen/dialect/nn/type/memory_type.py`、本任务记录。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/dialect/nn test/dialect/test_package.py test/passes/test_template_name_infer.py`：exit=0，`120 passed, 2 warnings`。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/dsl/gen_kernel`：exit=0，`186 passed, 2 warnings`。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/dsl/gen_kernel/emit/test_package.py test/dsl/gen_kernel/test_gen_kernel.py`：exit=0，`172 passed, 2 warnings`。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 -m py_compile kernel_gen/dialect/nn/type/memory_type.py test/passes/test_template_name_infer.py test/dsl/gen_kernel/test_gen_kernel.py`：exit=0。
- `rg -n "NnMemoryType\\.external_attrs -> DictionaryAttr|NnMemoryType\\.template_name -> StringAttr|copy_memory_type\\(|copy_memory_type_with_template_name\\(" spec/dialect/nn.md kernel_gen/dialect/nn/type/memory_type.py`：exit=0，确认 API 列表与详细条目已出现。

格式与敏感目录门禁：
- `git diff --check`：exit=0。
- `git diff --name-only -- expectation .skills agents/standard AGENTS.md TODO.md DONE.md`：exit=0，无输出。
- `git diff --cached --name-only -- expectation .skills agents/standard AGENTS.md TODO.md DONE.md`：exit=0，无输出。
- `git status --short --untracked-files=all -- expectation .skills agents/standard AGENTS.md TODO.md DONE.md`：exit=0，无输出。

主仓 symbol_iter / symbol fold 非候选隔离：
- 在独立 worktree 执行 `git diff --name-only -- kernel_gen/dialect/symbol/operation/arith.py spec/dialect/symbol.md test/dialect/symbol/test_symbol.py spec/pass/symbol_iter_eliminate.md`：exit=0，无输出。
- 在独立 worktree 执行 `git status --short --untracked-files=all -- kernel_gen/dialect/symbol/operation/arith.py spec/dialect/symbol.md test/dialect/symbol/test_symbol.py spec/pass/symbol_iter_eliminate.md`：exit=0，无输出。

减法检查：
- 不适用新增 private callable；本轮未新增或改动 private callable。
- 本轮没有替换运行时旧逻辑；只补齐公开 API 文档缺口。
- 未删除或保留任何旧实现分支；未恢复 `memory_template_name(...)` / `has_memory_template_name(...)`，未修改 copy helper 实现。

自检：
- 只改 archive_acceptance 点名的 `spec/dialect/nn.md` 与 `kernel_gen/dialect/nn/type/memory_type.py` 文件级 API 列表 / 详细说明，以及本任务记录。
- 未新增公开 API；补齐项均来自主仓只读计划中已确认的公开 API。
- 未跨文件调用非公开 helper，未增加 ctx 能力探测，未修改实现行为。
- 测试覆盖了受文档约束的 `NnMemoryType`、copy helper、template-name infer 与 gen_kernel ABI 相关行为；本轮没有 expectation 必过资产。
- 当前仍有既有候选实现 / spec / test diff，均为本任务计划候选范围；本轮未混入主仓 symbol 相关非候选文件。

结论：
- `execute` 返工完成。
- 建议回流 `review`，重点复核 archive_acceptance 两项最小阻断是否已闭合，以及敏感目录和非候选隔离是否仍为空。

时间：2026-05-28 13:13 +0800
经办人：不要啊教练
阶段：review / archive_acceptance 返工复审
任务：T-20260528-2936d50e / thirdparty-nn-memory-external-attrs-template-name
任务目标：复审 archive_acceptance 两项返工是否闭合：`NnMemoryType.external_attrs/template_name` 进入 spec 与实现文件 API 列表，`copy_memory_type(...)` 与 `copy_memory_type_with_template_name(...)` 补齐参数、返回值、使用示例及 external_attrs/template_name 语义；同时核对计划 pytest、py_compile、git diff check、敏感目录空 diff 与 symbol 非候选隔离。

最新同步现场：
- 执行目录：`/home/lfr/kernelcode_generate/wt-20260527-thirdparty-nn-memory-external-attrs`
- `git fetch origin`：exit=0。
- 同步前：`HEAD=479ef47e2cd93f3810b891ce6cf3b053ca360b41`，`origin/main=2c7857354da6b94da70dc19346ab8274e27626fb`，`merge-base=479ef47e2cd93f3810b891ce6cf3b053ca360b41`，`git rev-list --left-right --count HEAD...origin/main` 为 `0 1`。
- `git diff --name-status HEAD..origin/main`：latest main 仅触达 pass/tuning rehome 相关文件与对应任务记录，未与当前候选的 dialect/nn、dsl/gen_kernel、template_name_infer 文件重叠。
- `git merge --no-edit origin/main`：exit=0，fast-forward 到 `2c7857354da6b94da70dc19346ab8274e27626fb`，无冲突、无覆盖候选 diff。
- 同步后：`HEAD=origin/main=merge-base=2c7857354da6b94da70dc19346ab8274e27626fb`，`git rev-list --left-right --count HEAD...origin/main` 为 `0 0`。
- 同步后 `git status --short --untracked-files=all` 仍仅显示本任务 12 个候选文件修改与本任务记录未跟踪文件；latest main 同步未混入非候选 symbol 文件。

计划与合同真源：
- 当前独立 worktree 内仍无 `plan/1.md`；按管理员迁移记录，本轮只读引用主仓 `/home/lfr/kernelcode_generate/plan/1.md` 作为计划合同真源，未复制、新建或修改计划资产。
- 主仓计划明确本计划无必过 `expectation`；本轮未运行或引用 expectation 作为通过依据。

返工项复核：
- `spec/dialect/nn.md:7-15` 的顶部 `API 列表` 已列出 `NnMemoryType.external_attrs -> DictionaryAttr` 与 `NnMemoryType.template_name -> StringAttr`，并保留 `NnMemoryType(...)`、`copy_memory_type(...)`、`copy_memory_type_with_template_name(...)`、`copy_memory_type_with_external_attr(...)` 的公开签名。
- `spec/dialect/nn.md:153-182` 已新增 `NnMemoryType.external_attrs -> DictionaryAttr` 与 `NnMemoryType.template_name -> StringAttr` 的 API 详细说明，包含 `api / 参数 / 返回值 / 使用示例 / 功能说明 / 注意事项`。
- `spec/dialect/nn.md:184-221` 中 `copy_memory_type(...)` 与 `copy_memory_type_with_template_name(...)` 均已补齐 `参数 / 返回值 / 使用示例`，并写清 `copy_memory_type(...)` 清除 `external_attrs["template_name"]`、保留其它 `external_attrs`，`copy_memory_type_with_template_name(...)` 添加或覆盖 `external_attrs["template_name"]`、保留其它 `external_attrs`。
- `kernel_gen/dialect/nn/type/memory_type.py:6-12` 的文件级 `API 列表` 已同步列出 `NnMemoryType.external_attrs -> DictionaryAttr` 与 `NnMemoryType.template_name -> StringAttr`。
- `kernel_gen/dialect/__init__.py`、`kernel_gen/dialect/nn/__init__.py`、`kernel_gen/dialect/nn/type/__init__.py` 的 API 列表仍按 package root / package export 清单列导出对象，不展开 class property；当前 archive_acceptance 返工点针对 `spec/dialect/nn.md` 与承载 class 实现的 `memory_type.py`，该处理与计划中 package root exact subset 口径一致，不构成本轮阻断。

findings：
- 阻断项：无。
- 重复问题复核：archive_acceptance 两项最小阻断均已闭合。
- 新增问题：无。
- 范围扩大：无。

Diff 反推审查：
- 被审 diff 文件：`kernel_gen/dialect/__init__.py`、`kernel_gen/dialect/nn/__init__.py`、`kernel_gen/dialect/nn/type/__init__.py`、`kernel_gen/dialect/nn/type/memory_type.py`、`spec/dialect/nn.md`、`spec/dsl/gen_kernel/kernel_emitter.md`、`spec/pass/template_name_infer.md`、`test/dialect/nn/test_package.py`、`test/dialect/nn/test_type.py`、`test/dialect/test_package.py`、`test/dsl/gen_kernel/test_gen_kernel.py`、`test/passes/test_template_name_infer.py`。
- 返工 diff 直接对应公开 API 文档闭合；测试覆盖 `NnMemoryType.external_attrs` parse/print/copy、legacy template 兼容、template-name infer 保留其它 external attrs、gen_kernel wrapper/body 非 template external attr mismatch。
- `rg` 核对旧 `memory_template_name(...)` / `has_memory_template_name(...)` 仅剩 spec 中“已删除”说明，未恢复旧公开入口。
- 静态扫描未发现当前返工新增跨文件非公开 API、`ctx` 能力探测、`object` 签名或未授权 expectation 修改；`test/dsl/gen_kernel/test_gen_kernel.py` 中既有测试局部 helper / 嵌套函数属于存量测试结构，本轮仅新增 `external_attrs` 参数和用例，不作为当前返工阻断。

复跑验证：
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/dialect/nn test/dialect/test_package.py test/passes/test_template_name_infer.py`：exit=0，`120 passed, 2 warnings`。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/dsl/gen_kernel`：exit=0，`186 passed, 2 warnings`。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/dsl/gen_kernel/emit/test_package.py test/dsl/gen_kernel/test_gen_kernel.py`：exit=0，`172 passed, 2 warnings`。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 -m py_compile kernel_gen/dialect/nn/type/memory_type.py test/passes/test_template_name_infer.py test/dsl/gen_kernel/test_gen_kernel.py`：exit=0，输出 `py_compile-ok`。
- `git diff --check`：exit=0，输出 `diff-check-ok`。
- 敏感目录门禁：`git diff --name-only -- expectation .skills agents/standard AGENTS.md TODO.md DONE.md`、`git diff --cached --name-only -- expectation .skills agents/standard AGENTS.md TODO.md DONE.md`、`git status --short --untracked-files=all -- expectation .skills agents/standard AGENTS.md TODO.md DONE.md` 均 exit=0 且无输出。
- symbol 非候选隔离：独立 worktree 对 `kernel_gen/dialect/symbol/operation/arith.py spec/dialect/symbol.md test/dialect/symbol/test_symbol.py spec/pass/symbol_iter_eliminate.md` 执行 `git diff --name-only` 与 `git status --short --untracked-files=all` 均无输出；主仓同路径当前也无输出。
- 静态边界扫描：AST 扫描 `kernel_gen/dialect/nn/type/memory_type.py`、`test/passes/test_template_name_infer.py`、`test/dsl/gen_kernel/test_gen_kernel.py` 未发现 `object` 参数；`kernel_gen/dialect/nn/type/memory_type.py` 与 `test/passes/test_template_name_infer.py` 未发现嵌套函数；`rg` 扫描 `hasattr(ctx`、`getattr(ctx`、`callable(getattr(ctx`、`object` 签名无命中。

减法审查：
- 本轮返工不改运行时实现逻辑，仅补齐公开 API 文档和文件级 API 列表；无新增或改动 private callable。
- 原计划中旧 `NnMemoryType.template_name` 独立 type parameter 已由 `external_attrs` 真实承载替代；legacy `template = T1` 仅作为输入兼容保留，canonical print 走 `external_attrs = {...}`。
- 旧 `memory_template_name(...)` / `has_memory_template_name(...)` 未恢复；主仓 `symbol_iter` / `symbol fold` 非候选文件未进入独立 worktree 候选 diff。

自检：
- 已按最新 prompt、根 `AGENTS.md` 与审查规范执行，先同步 latest main，再基于同步后现场读取计划、任务记录和实际 diff。
- 已复核 archive_acceptance 两项返工、公开 API/spec/test 边界、Diff 反推审查、计划 pytest、py_compile、git diff check、敏感目录空 diff和 symbol 非候选隔离。
- 未修改业务实现、测试、spec、计划书、`expectation/`、`.skills/`、`agents/standard`、`AGENTS.md`、`TODO.md`、`DONE.md`；本轮只追加审查记录。

结论：
- `review` 复审通过。
- 该任务为计划级任务，下一阶段应进入 `archive_acceptance / 计划书入档验收`，不得直接 merge。

时间：2026-05-28 13:20 +0800
经办人：不要啊教练
阶段：archive_acceptance / 计划书入档验收
任务：T-20260528-2936d50e / thirdparty-nn-memory-external-attrs-template-name
任务目标：核对计划级任务 review 通过后的 latest 同步现场、任务记录完整性、Diff 反推审查、计划 pytest、py_compile、git diff check、敏感目录空 diff、symbol 非候选隔离与可入档性。

最新同步现场：
- 执行目录：`/home/lfr/kernelcode_generate/wt-20260527-thirdparty-nn-memory-external-attrs`
- 已在 2026-05-28 13:13 review 复审前执行 `git fetch origin`，并将 worktree 从 `479ef47e2cd93f3810b891ce6cf3b053ca360b41` fast-forward 到 `origin/main=2c7857354da6b94da70dc19346ab8274e27626fb`。
- archive_acceptance 复核时再次执行 `git fetch origin`：exit=0。
- 当前 `HEAD=origin/main=merge-base=2c7857354da6b94da70dc19346ab8274e27626fb`，`git rev-list --left-right --count HEAD...origin/main` 为 `0 0`。
- 当前 `git diff --name-status --find-renames` 仅包含本计划候选 12 个 tracked 文件，另有本任务记录未跟踪文件；无冲突、无覆盖风险。

任务记录与计划口径：
- 已核对执行记录、第一次 review、archive_acceptance 退回项、execute 返工记录与 13:13 review 复审通过记录，记录链路完整。
- 当前独立 worktree 内仍无 `plan/1.md`；本链按管理员迁移记录只读引用主仓 `/home/lfr/kernelcode_generate/plan/1.md` 作为计划合同真源，未复制、新建或修改计划资产。
- 主仓计划声明本计划无必过 `expectation`；本轮不运行 expectation 作为通过依据，候选 diff 不含 `expectation/`。

入档验收 findings：
- 阻断项：无。
- archive_acceptance 退回的两项公开 API/spec 阻断已由 execute 返工并由 review 复审确认闭合。
- 未发现新的可执行返工项。

候选范围与可入档性：
- 候选 tracked diff：`kernel_gen/dialect/__init__.py`、`kernel_gen/dialect/nn/__init__.py`、`kernel_gen/dialect/nn/type/__init__.py`、`kernel_gen/dialect/nn/type/memory_type.py`、`spec/dialect/nn.md`、`spec/dsl/gen_kernel/kernel_emitter.md`、`spec/pass/template_name_infer.md`、`test/dialect/nn/test_package.py`、`test/dialect/nn/test_type.py`、`test/dialect/test_package.py`、`test/dsl/gen_kernel/test_gen_kernel.py`、`test/passes/test_template_name_infer.py`。
- 必须同批纳入 merge 的记录文件：`agents/codex-multi-agents/log/task_records/2026/25/20260527-thirdparty-nn-memory-external-attrs-plan.md`。
- 禁止纳入本任务候选：`expectation/`、`.skills/`、`agents/standard/`、`AGENTS.md`、`TODO.md`、`DONE.md`、主仓或其它 worktree 中的 `kernel_gen/dialect/symbol/operation/arith.py`、`spec/dialect/symbol.md`、`test/dialect/symbol/test_symbol.py`、`spec/pass/symbol_iter_eliminate.md`。
- `plan/1.md` 不是当前独立 worktree 候选资产；merge 前不得擅自复制、新建或把主仓未跟踪计划文件纳入本任务提交，除非管理员/用户另行明确授权。

Diff 反推审查复核：
- `spec/dialect/nn.md` 与 `kernel_gen/dialect/nn/type/memory_type.py` 已补齐 `NnMemoryType.external_attrs -> DictionaryAttr`、`NnMemoryType.template_name -> StringAttr` 的 API 列表与详细说明。
- `copy_memory_type(...)` 与 `copy_memory_type_with_template_name(...)` 的详细条目已补齐 `参数 / 返回值 / 使用示例`，并明确 `external_attrs` 保留、`template_name` 清除 / 写入语义。
- `test/dialect/nn/test_type.py`、`test/passes/test_template_name_infer.py`、`test/dsl/gen_kernel/test_gen_kernel.py` 覆盖 external attrs canonical print/copy、template-name infer 保留其它 attrs、wrapper/body ABI mismatch。
- 旧 `memory_template_name(...)` / `has_memory_template_name(...)` 未恢复；symbol 非候选路径在独立 worktree diff/status 为空。

入档验收复跑验证：
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/dialect/nn test/dialect/test_package.py test/passes/test_template_name_infer.py`：exit=0，`120 passed, 2 warnings`。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/dsl/gen_kernel`：exit=0，`186 passed, 2 warnings`。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/dsl/gen_kernel/emit/test_package.py test/dsl/gen_kernel/test_gen_kernel.py`：exit=0，`172 passed, 2 warnings`。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 -m py_compile kernel_gen/dialect/nn/type/memory_type.py test/passes/test_template_name_infer.py test/dsl/gen_kernel/test_gen_kernel.py`：exit=0，输出 `py_compile-ok`。
- `git diff --check`：exit=0，输出 `diff-check-ok`。
- 敏感目录门禁：`git diff --name-only -- expectation .skills agents/standard AGENTS.md TODO.md DONE.md`、`git diff --cached --name-only -- expectation .skills agents/standard AGENTS.md TODO.md DONE.md`、`git status --short --untracked-files=all -- expectation .skills agents/standard AGENTS.md TODO.md DONE.md` 均 exit=0 且无输出。
- symbol 非候选隔离：`git diff --name-only -- kernel_gen/dialect/symbol/operation/arith.py spec/dialect/symbol.md test/dialect/symbol/test_symbol.py spec/pass/symbol_iter_eliminate.md` 与对应 `git status --short --untracked-files=all` 均 exit=0 且无输出。

减法审查：
- 入档阶段不改代码；复核旧 `template_name` 独立字段已迁移为 `external_attrs` 真实承载，legacy `template = ...` 仅保留输入兼容，canonical print 走 `external_attrs`。
- 旧 `memory_template_name(...)` / `has_memory_template_name(...)` 未恢复。
- 本链前序阻断的浅 `_symbol_array(...)` helper 已删除；本轮 archive_acceptance 未新增或改动 private callable。

自检：
- 已基于最新 `origin/main` 现场核对 review 通过记录、任务记录完整性、候选范围、计划 pytest、py_compile、git diff check、敏感目录空 diff与 symbol 非候选隔离。
- 已确认仍无可执行返工项；本轮未修改业务实现、spec、测试、计划书、`expectation/`、`.skills/`、`agents/standard`、`AGENTS.md`、`TODO.md`、`DONE.md`，仅追加入档验收记录。

结论：
- `archive_acceptance` 通过。
- 下一阶段可按计划级流程流转 `merge`；merge 前必须同批纳入候选代码/spec/test 与本任务记录，且不得纳入上述敏感目录、symbol 非候选文件或未授权计划资产。

时间：2026-05-28 13:09 +0800
经办人：李白
阶段：merge
任务：T-20260528-2936d50e / thirdparty-nn-memory-external-attrs-template-name
任务目标：按 archive_acceptance 通过口径同批合入 12 个候选代码/spec/test 文件与本任务记录，排除 `expectation/`、`.skills/`、`agents/standard/`、`AGENTS.md`、`TODO.md`、`DONE.md`、`plan/1.md`、主仓 symbol 非候选文件和其它未授权资产。

合并前核对：
- 来源 worktree：`/home/lfr/kernelcode_generate/wt-20260527-thirdparty-nn-memory-external-attrs`
- 来源分支：`task/thirdparty-nn-memory-external-attrs`
- latest main：`HEAD=origin/main=2c7857354da6b94da70dc19346ab8274e27626fb`
- `git rev-list --left-right --count HEAD...origin/main`：`0 0`
- 计划书：独立 worktree 内无 `plan/1.md`，按管理员迁移记录只读引用主仓 `/home/lfr/kernelcode_generate/plan/1.md`；本轮不复制、不新建、不纳入计划资产。
- review 复审结论：通过。
- archive_acceptance 结论：通过。

实际合入文件：
- `kernel_gen/dialect/__init__.py`
- `kernel_gen/dialect/nn/__init__.py`
- `kernel_gen/dialect/nn/type/__init__.py`
- `kernel_gen/dialect/nn/type/memory_type.py`
- `spec/dialect/nn.md`
- `spec/dsl/gen_kernel/kernel_emitter.md`
- `spec/pass/template_name_infer.md`
- `test/dialect/nn/test_package.py`
- `test/dialect/nn/test_type.py`
- `test/dialect/test_package.py`
- `test/dsl/gen_kernel/test_gen_kernel.py`
- `test/passes/test_template_name_infer.py`
- `agents/codex-multi-agents/log/task_records/2026/25/20260527-thirdparty-nn-memory-external-attrs-plan.md`

验证：
- `git fetch --prune origin`：exit=0。
- `git diff --check`：exit=0。
- `git diff --name-only -- expectation .skills agents/standard AGENTS.md TODO.md DONE.md plan/1.md kernel_gen/dialect/symbol/operation/arith.py spec/dialect/symbol.md test/dialect/symbol/test_symbol.py spec/pass/symbol_iter_eliminate.md`：exit=0，无输出。
- `git status --short --ignored --untracked-files=all -- expectation .skills agents/standard AGENTS.md TODO.md DONE.md plan/1.md kernel_gen/dialect/symbol/operation/arith.py spec/dialect/symbol.md test/dialect/symbol/test_symbol.py spec/pass/symbol_iter_eliminate.md`：exit=0，无输出。
- archive_acceptance 已在 latest main 基线复跑并记录通过：`test/dialect/nn test/dialect/test_package.py test/passes/test_template_name_infer.py` 120 passed；`test/dsl/gen_kernel` 186 passed；`test/dsl/gen_kernel/emit/test_package.py test/dsl/gen_kernel/test_gen_kernel.py` 172 passed；`py_compile`、`git diff --check`、敏感目录门禁与 symbol 非候选隔离均通过。

敏感目录与禁止资产核对：
- `expectation/`、`.skills/`、`agents/standard/`、`AGENTS.md`、`TODO.md`、`DONE.md` 未进入候选 diff。
- `plan/1.md` 未进入候选 diff。
- 主仓 symbol 非候选文件 `kernel_gen/dialect/symbol/operation/arith.py`、`spec/dialect/symbol.md`、`test/dialect/symbol/test_symbol.py`、`spec/pass/symbol_iter_eliminate.md` 未进入独立 worktree候选 diff。
- 本计划无必过 `expectation`，merge 未运行或修改 expectation。

冲突处理：
- 无冲突；任务 worktree 与 latest `origin/main` 对齐，候选为工作区 diff。

剩余风险：
- 未发现 merge 阻断项。
- 最终合并提交号在 push 后回报，不再为补提交号追加任务记录提交。

结论：
- `merge 可执行`；将显式暂存 12 个候选代码/spec/test 文件与本任务记录，同批提交并推送到 `origin/main`，随后执行 `-done`。
