# T-20260523-1aed88f5 execute-engine-strategy-registry-rehome

## 任务信息

- 任务：`T-20260523-1aed88f5`
- 阶段：`execute`
- worktree：`/home/lfr/kernelcode_generate/wt-20260523-execute-engine-strategy-registry-rehome`
- 分支基线：`HEAD=origin/main=5a9d524c733cc3838046319adf44015cb23ae49b`
- 计划书：主仓只读 `ARCHITECTURE/plan/execute_engine_strategy_registry_rehome_green_plan.md`
- 计划书 sha256：`1a41724f0996a0fede940f324b7e5c4b3ddca0b37f21c8bcfa77951dd24feaff`
- 记录时间：`2026-05-23 18:14:27 +0800`

## 执行前阅读

- 已重新读取 `agents/codex-multi-agents/agents/小李飞刀/小李飞刀.prompt.md`。
- 已读取 `AGENTS.md` 与 `agents/standard/任务记录约定.md`、`agents/standard/实现文件规范.md`、`agents/standard/测试文件约定.md`。
- 已只读读取主仓计划书；任务 worktree 内无该计划文件，按派发口径使用主仓协调资产，不在主仓写任务 diff。

## 实现结果

- 新增 `kernel_gen/execute_engine/strategy.py` 作为 compile strategy registry 真源：
  - `CompileStrategy`
  - `register_compile_strategy(...)`
  - `get_compile_strategy(...)`
- 新增 `kernel_gen/execute_engine/builtin_strategy.py`：
  - 仅保留包内 `install_builtin_compile_strategies(strategy_factory) -> None`
  - 不进入 `kernel_gen.execute_engine.__all__`
  - 不导入 `compiler.py`，不触碰 `CompileRequest` / `CompiledKernel` / 运行期 ABI。
- `kernel_gen/execute_engine/compiler.py`：
  - 删除本文件内 strategy registry 实现体，改为从 `strategy.py` re-export。
  - 保留 `_BuiltinCompileStrategy`、内置 target include / entry shim / compile unit / real compile helper、`_AllowAbsentMemoryArg` 与 `CompiledKernel` 装配。
  - late import `install_builtin_compile_strategies` 并唯一调用 `install_builtin_compile_strategies(_BuiltinCompileStrategy)`。
  - 删除旧 `target_support.py` 依赖。
- 删除 `kernel_gen/execute_engine/target_support.py`。
- 将 `test/execute_engine/test_target_support.py` 迁移为 `test/execute_engine/test_builtin_strategy.py`，测试仍只通过公开 `ExecutionEngine.compile(...)` / `CompiledKernel.execute(...)` 观察行为。
- 同步 `spec/execute_engine/*.md` 与 execute_engine 测试文件说明。

## 用户补充指导处理

- 用户补充指导：去掉 worktree 中多余函数，只保留计划/spec/API/调用链必要函数，删除多余 wrapper、转发、重复 helper。
- 已删除/避免保留：
  - `_compiled_kernel_from_builtin_artifacts(...)`：纯转发装配层，已内联到 `_BuiltinCompileStrategy.compile(...)`。
  - `_compile_with_builtin_strategy(...)`：纯转发层，已删除。
  - 迁移过程中重复生成的第二个 `_execution_engine_error(...)`：已删除，统一使用原 `compiler.py` 错误 helper。
  - 迁移过程中与运行期同名的 `_allow_absent_memory_arg_map(...)`：已改为 `_allow_absent_memory_arg_specs_map(...)`，避免覆盖运行期 metadata map。
- 保留且必要：
  - `_BuiltinCompileArtifacts`：替代已删除公开 artifact API 的私有编译产物结构，只在 `compiler.py` 内部使用。
  - `_build_builtin_compile_artifacts(...)`：承载从旧 `target_support.py` 合并回 `compiler.py` 的内置编译主路径。
  - `install_builtin_compile_strategies(...)`：计划明确要求的包内安装函数，唯一调用点在 `compiler.py`。
- 当前无不确定函数需要升级确认。

## 候选 diff

- `kernel_gen/execute_engine/compiler.py`
- `kernel_gen/execute_engine/strategy.py`
- `kernel_gen/execute_engine/builtin_strategy.py`
- `kernel_gen/execute_engine/target_support.py`
- `spec/execute_engine/execute_engine.md`
- `spec/execute_engine/execute_engine_api.md`
- `spec/execute_engine/execute_engine_target.md`
- `spec/execute_engine/strategy.md`
- `test/execute_engine/test_builtin_strategy.py`
- `test/execute_engine/test_compile.py`
- `test/execute_engine/test_compile_strategy.py`
- `test/execute_engine/test_contract.py`

## 自检

- 接口：`kernel_gen.execute_engine.__all__` 保持 8 项不变；`compiler.py` 旧公开导入路径仍与 `strategy.py` 真源对象同一身份。
- 边界：`strategy.py` 不 import `compiler.py`；`builtin_strategy.py` 不 import `compiler.py`，不引用 `CompileRequest` / `CompiledKernel` / `_AllowAbsentMemoryArg`。
- 异常：duplicate strategy、missing strategy、unknown target、request/source 混用等公开失败短语由既有 pytest 覆盖。
- 兼容性：`ExecutionEngine.compile(...)`、内置 `cpu` / `npu_demo` 编译、allow-absent memory `None` runtime 行为均保持通过。
- 冗余：已按用户补充指导删除纯转发 wrapper 与重复 helper。
- 测试有效性：新增 import identity、import order、builtin installer AST gate、旧文件退场断言；迁移后的 target include / entry shim 测试仍走公开 API。

## Diff 反推自测

- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/execute_engine/test_compile.py test/execute_engine/test_builtin_strategy.py test/execute_engine/test_compile_strategy.py test/execute_engine/test_contract.py -ra`
  - 结果：`44 passed, 1 warning`
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/execute_engine/test_invoke.py -ra`
  - 结果：`19 passed`
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/execute_engine/test_compile.py test/execute_engine/test_builtin_strategy.py test/execute_engine/test_compile_strategy.py test/execute_engine/test_contract.py test/execute_engine/test_invoke.py -ra`
  - 结果：`63 passed, 1 warning`
- `PYTHONDONTWRITEBYTECODE=1 python3 -m compileall -q kernel_gen/execute_engine test/execute_engine`
  - 结果：`exit=0`
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest --collect-only -q test/execute_engine/test_compile.py test/execute_engine/test_builtin_strategy.py test/execute_engine/test_compile_strategy.py test/execute_engine/test_contract.py test/execute_engine/test_invoke.py`
  - 结果：`63 tests collected`

## 计划门禁

- import/API matrix：
  - 命令：计划书内 `kernel_gen.execute_engine.strategy` / `builtin_strategy` / `compiler` / package root 全排列导入脚本。
  - 结果：`import api matrix ok`
- 旧文件退场：
  - `test ! -f kernel_gen/execute_engine/target_support.py`
  - `test ! -f test/execute_engine/test_target_support.py`
  - 结果：`old-files-absent`
- 旧接口残留：
  - `rg -n "target_support|BuiltinTargetSupportArtifacts|build_builtin_target_support_artifacts" kernel_gen spec test`
  - 结果：无输出。
- 静态 rg：
  - 覆盖 `strategy.py` / `builtin_strategy.py` 非公开导入、`compiler.py` 私有导入、ctx/context 能力探测、`install_builtin_compile_strategies(` 测试直连、skip/xfail。
  - 结果：`static-rg-ok`
- 静态 AST：
  - 覆盖非装饰器嵌套定义、`compiler.py` import allowlist、`strategy.py` / `builtin_strategy.py` 不 import compiler、`builtin_strategy.py` 无顶层 install/register call、`compiler.py` 唯一安装调用。
  - 结果：`static-ast-ok`
- `git diff --check && git diff --cached --check`
  - 结果：`exit=0`
- 敏感目录门禁：
  - `git diff --name-only -- expectation .skills agents/standard`
  - `git diff --cached --name-only -- expectation .skills agents/standard`
  - `git status --short --ignored --untracked-files=all -- expectation .skills agents/standard`
  - 结果：三条均无输出。

## expectation

- 本计划明确不修改、不运行 `expectation` 作为通过依据。
- 候选 diff 中 `expectation/`、`.skills/`、`agents/standard/` 均为空。

## 结论

- execute 已完成。
- 待按流程流转 `review`。

## TODO 复核与流转准备

- `2026-05-23 18:14 +0800` 复核 `/home/lfr/kernelcode_generate/TODO.md`：
  - 当前 `T-20260523-1aed88f5` 仍在“正在执行的任务”，指派 `小李飞刀`，状态 `进行中`。
  - worktree 内无 `TODO.md`，按个人提示词使用主仓状态文件。
  - 任务列表无新的同任务返工项。
- 流转目标：`review`。

## review 记录（提莫炖蘑菇，2026-05-23）

### 审查前置

- 已重新读取：
  - `agents/codex-multi-agents/agents/提莫炖蘑菇/提莫炖蘑菇.prompt.md`
  - `/home/lfr/kernelcode_generate/AGENTS.md`
  - `agents/standard/审查规范.md`
  - `agents/standard/expectation任务规则.md`
- 执行目录：`/home/lfr/kernelcode_generate/wt-20260523-execute-engine-strategy-registry-rehome`
- latest main 核对：
  - `git fetch origin`：通过。
  - `HEAD=5a9d524c733cc3838046319adf44015cb23ae49b`
  - `origin/main=5a9d524c733cc3838046319adf44015cb23ae49b`
  - `merge-base HEAD origin/main=5a9d524c733cc3838046319adf44015cb23ae49b`
  - 结论：待审 worktree 已在 latest main 基线上，未发现需要 merge 的新主线提交。
- 计划书来源：目标 worktree 内无 `ARCHITECTURE/plan/execute_engine_strategy_registry_rehome_green_plan.md`，按执行记录读取主仓只读计划资产 `/home/lfr/kernelcode_generate/ARCHITECTURE/plan/execute_engine_strategy_registry_rehome_green_plan.md`。

### 审查范围

- 实际候选 diff：
  - `kernel_gen/execute_engine/compiler.py`
  - `kernel_gen/execute_engine/strategy.py`
  - `kernel_gen/execute_engine/builtin_strategy.py`
  - `kernel_gen/execute_engine/target_support.py`
  - `spec/execute_engine/execute_engine.md`
  - `spec/execute_engine/execute_engine_api.md`
  - `spec/execute_engine/execute_engine_target.md`
  - `spec/execute_engine/strategy.md`
  - `test/execute_engine/test_builtin_strategy.py`
  - `test/execute_engine/test_compile.py`
  - `test/execute_engine/test_compile_strategy.py`
  - `test/execute_engine/test_contract.py`
- 重点核对：
  - `strategy.py` 是否成为 compile strategy registry 真源。
  - `builtin_strategy.py` 是否只承接包内安装逻辑，不进入包根公开 API。
  - `compiler.py` 是否保留 `_BuiltinCompileStrategy` / `_AllowAbsentMemoryArg` / `CompiledKernel` 装配和旧公开导入路径。
  - `target_support.py` 与旧 artifact API 是否退场。
  - spec/test 是否同步且测试只走公开入口。
  - `expectation/`、`.skills/`、`agents/standard/**` 是否无候选 diff。

### Findings

- `最小需改项`：`kernel_gen/execute_engine/compiler.py:94` 与 `kernel_gen/execute_engine/compiler.py:1428` 重复定义 `_dtype_code_from_name(dtype: str | None) -> int`。
  - 问题：本轮把 `target_support.py` 合回 `compiler.py` 后保留了两个同名顶层 helper。第二个定义会覆盖第一个定义，当前函数体虽然相同，但同一 dtype-code 规则已经形成双真源。
  - 影响：违反本轮“删除多余 wrapper、转发、重复 helper”的执行记录口径，也违反审查规范中同一规则不得多处散落的维护性要求；后续若只改其中一处 docstring 或逻辑，容易产生误导或回归。
  - 最小返工动作：只保留一个 `_dtype_code_from_name(...)` 定义，建议保留一份同时覆盖 runtime template shim 与 allow-absent metadata 校验的说明；删除另一份重复定义。
  - 验收方式：重跑本轮 Diff 反推 pytest、compileall、import/API matrix、静态 AST gate，并补一条重复顶层定义检查或在记录中写明已用 AST 核对 `compiler.py` 无重复顶层函数定义。

### Diff 反推审查

- `strategy.py`：
  - `CompileStrategy`、`register_compile_strategy(...)`、`get_compile_strategy(...)` 已从 `compiler.py` 拆出为真源。
  - 未运行期 import `compiler.py`；签名使用字符串注解保留 `CompileRequest` / `CompiledKernel` 文本。
  - 公开包根与 `compiler.py` re-export 对象身份由 import/API matrix 覆盖。
- `builtin_strategy.py`：
  - 仅定义 `install_builtin_compile_strategies(strategy_factory) -> None`。
  - 未导入 `compiler.py`，未引用 `CompileRequest`、`CompiledKernel`、`_BuiltinCompileStrategy`、`_AllowAbsentMemoryArg`。
  - 未进入 `kernel_gen.execute_engine.__all__`。
- `compiler.py`：
  - 已删除 strategy registry 实现体，保留旧公开导入路径。
  - 内置 target include / entry shim / 编译单元 / allow-absent ABI / `CompiledKernel` 装配留在本文件。
  - `install_builtin_compile_strategies(_BuiltinCompileStrategy)` 为唯一安装调用点。
  - 存在上述重复 helper 阻断。
- `spec/test`：
  - `target_support.py` 文档与测试引用已迁移为 `compiler.py` / `strategy.py` / `builtin_strategy.py`。
  - `test_target_support.py` 已迁移为 `test_builtin_strategy.py`。
  - 测试主要通过 `ExecutionEngine.compile(...)`、`CompiledKernel.execute(...)`、包根 API 与 AST/static gate 观察行为；未发现 direct call `install_builtin_compile_strategies(...)`。
- `expectation`：
  - 计划正文明确本轮不运行、不修改 `expectation` 作为必过合同；审查中未发现候选 diff 涉及 `expectation/`。

### 复跑验证

- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/execute_engine/test_compile.py test/execute_engine/test_builtin_strategy.py test/execute_engine/test_compile_strategy.py test/execute_engine/test_contract.py -ra`
  - 结果：`44 passed, 1 warning`
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/execute_engine/test_invoke.py -ra`
  - 结果：`19 passed`
- `PYTHONDONTWRITEBYTECODE=1 python3 -m compileall -q kernel_gen/execute_engine test/execute_engine`
  - 结果：`exit=0`
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest --collect-only -q test/execute_engine/test_compile.py test/execute_engine/test_builtin_strategy.py test/execute_engine/test_compile_strategy.py test/execute_engine/test_contract.py test/execute_engine/test_invoke.py`
  - 结果：`63 tests collected`
- import/API matrix：
  - 结果：`import api matrix ok`
- 旧文件与旧接口退场：
  - `test ! -f kernel_gen/execute_engine/target_support.py`
  - `test ! -f test/execute_engine/test_target_support.py`
  - `! rg -n "target_support|BuiltinTargetSupportArtifacts|build_builtin_target_support_artifacts" kernel_gen spec test`
  - 结果：通过，无输出。
- 静态 rg：
  - 覆盖 `strategy.py` / `builtin_strategy.py` 非公开导入、`compiler.py` 私有导入、ctx/context 能力探测、`install_builtin_compile_strategies(` 测试直连、skip/xfail。
  - 结果：通过，无输出。
- 静态 AST：
  - 非装饰器嵌套定义：通过。
  - `compiler.py` import allowlist：通过。
  - `strategy.py` / `builtin_strategy.py` 不 import compiler：通过。
  - `builtin_strategy.py` 无顶层 install/register call，`compiler.py` 唯一安装调用：通过。
- 重复顶层定义检查：
  - 命中：`kernel_gen/execute_engine/compiler.py:_dtype_code_from_name:[94, 1428]`
- `git diff --check && git diff --cached --check`
  - 结果：`exit=0`
- 敏感目录门禁：
  - `git diff --name-only -- expectation .skills agents/standard`
  - `git diff --cached --name-only -- expectation .skills agents/standard`
  - `git status --short --ignored --untracked-files=all -- expectation .skills agents/standard`
  - 结果：三条均无输出。

### 自检

- 已按实际 diff 反推审查，未只依赖执行摘要。
- 已核对公开 API 用户确认来源、包根 `__all__`、旧公开路径兼容、新实现真源、测试公开入口边界。
- 已核对 `expectation/`、`.skills/`、`agents/standard/**` 未进入候选 diff。
- 已复跑计划 pytest、collect、compileall、import/API matrix、静态扫描、diff check 与敏感目录门禁。
- 由于存在可执行返工项，结论不得写通过。

### 结论

- 结论：`最小需改项`。
- 本轮 review 不通过，需退回 `execute` 删除 `compiler.py` 中重复 `_dtype_code_from_name(...)` 定义，并重跑上述验收。

## 流转结果

- 命令：`bash skills/codex-multi-agents/scripts/codex-multi-agents-task.sh -file TODO.md -next -task_id T-20260523-1aed88f5 -from 小李飞刀 -type review ... -auto`
- 结果：
  - `OK: next T-20260523-1aed88f5`
  - `OK: auto-dispatch T-20260523-1aed88f5 -> 提莫炖蘑菇`
  - `OK: talk 小李飞刀 -> 神秘人`
- 管理员回报：已通过 `codex-multi-agents-tmux.sh -talk` 回报神秘人。

## review 返工收口：删除重复 `_dtype_code_from_name`

时间：`2026-05-23 18:28 +0800`
经办人：`小李飞刀`
任务：`T-20260523-1aed88f5`
任务目标：删除 `kernel_gen/execute_engine/compiler.py` 中重复的 `_dtype_code_from_name(dtype: str | None) -> int` 顶层定义，只保留单一真源。

### 改动

- 删除 `compiler.py` 后部由旧内置编译实现迁移带入的重复 `_dtype_code_from_name(...)`。
- 保留文件前部 `_dtype_code_from_name(...)` 作为单一真源。
- 未改公开 API、spec、测试、expectation、`.skills` 或 `agents/standard`。

### Diff 反推自测

- `PYTHONDONTWRITEBYTECODE=1 python3 - <<'PY' ...`
  - 覆盖点：AST 检查 `compiler.py` 顶层函数名无重复，且 `_dtype_code_from_name` 仅位于第 94 行。
  - 结果：`compiler top-level functions unique`
- `PYTHONDONTWRITEBYTECODE=1 python3 -m py_compile kernel_gen/execute_engine/compiler.py`
  - 结果：`exit=0`
- `rg -n "def _dtype_code_from_name|_dtype_code_from_name\(" kernel_gen/execute_engine/compiler.py`
  - 结果：仅 1 个定义；调用点均指向单一真源。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/execute_engine/test_compile.py test/execute_engine/test_builtin_strategy.py test/execute_engine/test_compile_strategy.py test/execute_engine/test_contract.py test/execute_engine/test_invoke.py -ra`
  - 结果：`63 passed, 1 warning`
- `PYTHONDONTWRITEBYTECODE=1 python3 -m compileall -q kernel_gen/execute_engine test/execute_engine`
  - 结果：`exit=0`
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest --collect-only -q test/execute_engine/test_compile.py test/execute_engine/test_builtin_strategy.py test/execute_engine/test_compile_strategy.py test/execute_engine/test_contract.py test/execute_engine/test_invoke.py`
  - 结果：`63 tests collected`
- import/API matrix：
  - 结果：`import api matrix ok`
- 静态扫描：
  - `static-rg-ok`
  - `static-ast-ok`
- `git diff --check && git diff --cached --check`
  - 结果：`exit=0`
- 敏感目录门禁：
  - `git diff --name-only -- expectation .skills agents/standard`
  - `git diff --cached --name-only -- expectation .skills agents/standard`
  - `git status --short --ignored --untracked-files=all -- expectation .skills agents/standard`
  - 结果：三条均无输出。

### 自检

- 接口：未改公开 API，`strategy.py` / `builtin_strategy.py` 拆分边界不变。
- 边界：删除的是同文件重复 helper，不涉及跨文件非公开 API。
- 异常与兼容：`allow-absent` metadata、template dtype seed、entry shim 等调用点均继续使用保留的单一 `_dtype_code_from_name(...)`。
- 冗余：review 指出的重复定义已删除，顶层函数重复 AST 检查通过。
- 测试有效性：execute_engine 全量相关 pytest 与静态门禁均复跑通过。

### 结论

- review 最小需改项已收口。
- 可重新流转 `review`。

### 流转阻塞

- 已执行：
  - `bash skills/codex-multi-agents/scripts/codex-multi-agents-task.sh -file TODO.md -next -task_id T-20260523-1aed88f5 -from 小李飞刀 -type review ... -auto`
- 结果：
  - `ERROR(2): invalid table format: row column count mismatch in section ## 正在执行的任务`
- 定位：
  - `/home/lfr/kernelcode_generate/TODO.md` 第 6 行任务描述包含未转义 `|`：`_dtype_code_from_name(dtype: str | None) -> int`，导致状态脚本解析表格列数失败。
- 处理：
  - 未手工修改共享 `TODO.md`。
  - 已回报管理员请求修复状态文件或代执行流转。

## 架构侧接续核对（大闸蟹，2026-05-23 18:54 +0800）

### 当前现场

- 接续来源：`神秘人 -> 大闸蟹`：继续。
- 执行目录核对：
  - 主仓：`/home/lfr/kernelcode_generate`
  - 任务 worktree：`/home/lfr/kernelcode_generate/wt-20260523-execute-engine-strategy-registry-rehome`
- 当前状态文件：主仓 `TODO.md` 已将 `T-20260523-1aed88f5` 写为 `review` 阶段，指派 `不要啊教练`，描述为“execute 返工已完成并写入任务记录；重复 _dtype_code_from_name 已删除；请按 review 复审，不直接进入 merge。”
- 当前任务记录显示：
  - 第一轮 review 阻断项为 `compiler.py` 重复 `_dtype_code_from_name(...)`。
  - execute 返工已删除重复定义，并复跑相关 pytest、compileall、collect-only、import/API matrix、静态扫描、diff check 与敏感目录门禁。

### 架构裁定

- `大闸蟹` 为架构师角色，按角色提示词不承接管理员分发的实现、测试、审查、合并任务，也不替管理员分发或关闭任务。
- 当前任务尚未完成 `review` 复审，不具备进入架构复核 / 终验条件。
- 架构侧本轮不越权执行 review，不手工修改 `TODO.md` / `DONE.md`，不推进 merge。

### 下一步

- 由当前 `TODO.md` 指派的 `不要啊教练` 按 review / 复审规则完成复审。
- 若 review 通过，再由管理员接续到架构复核 / 终验；届时大闸蟹可按计划正文和最新同步现场执行终验。
- 若 review 再次不通过，按原计划级任务链回到 execute 收口最小需改项。

### 验证

- 本轮为架构侧流程核对，只读取 `TODO.md`、任务记录、角色提示词、计划书与候选 worktree 状态；未运行代码测试。
- 未修改 `expectation/`、`.skills/`、`agents/standard/**`。

### 自检

- 已核对当前阶段仍为 `review`，且已有明确指派审查角色。
- 已核对架构角色权限边界，未替代审查、合并或管理员状态推进。
- 已把接续裁定写入任务记录，避免仅保留口头结论。

### 结论

- 当前不执行架构终验；等待 `不要啊教练` 完成 review 复审。

## review 复审记录（不要啊教练，2026-05-23 19:04 +0800）

### Findings

- 结论：无阻断 findings。
- 第一轮 review 指出的 `kernel_gen/execute_engine/compiler.py` 重复 `_dtype_code_from_name(...)` 已收口；本轮 AST 复查未发现重复顶层函数/类定义。
- 未发现新增跨文件非公开 API 调用、测试直连包内安装 helper、公开 API 漂移或敏感目录候选 diff。

### 审查前置

- 已读取：
  - `agents/codex-multi-agents/agents/不要啊教练/不要啊教练.prompt.md`
  - `AGENTS.md`
  - `agents/standard/审查规范.md`
  - `agents/standard/任务记录约定.md`
  - `agents/standard/实现文件规范.md`
  - 主仓只读计划书 `/home/lfr/kernelcode_generate/ARCHITECTURE/plan/execute_engine_strategy_registry_rehome_green_plan.md`
- 执行目录：`/home/lfr/kernelcode_generate/wt-20260523-execute-engine-strategy-registry-rehome`
- latest main 核对：
  - `git fetch origin`：通过。
  - `HEAD=5a9d524c733cc3838046319adf44015cb23ae49b`
  - `origin/main=1381f0b687c7914c2eda95d31be55bf962502d53`
  - `merge-base HEAD origin/main=5a9d524c733cc3838046319adf44015cb23ae49b`
  - 当前任务分支落后 `origin/main` 1 个提交；最新主线变更为另一条 `dsl-scratch-alloc-view-normalization` 合并，`latest-main-changed=9`、`candidate-all-changed=13`、路径交集为 `[]`。
  - 结论：未发现 latest main 对本任务候选 diff 的覆盖或冲突风险；终验/merge 前仍需按最新主线同步并重跑相应 gate。

### 审查范围

- 实际候选 diff：
  - `kernel_gen/execute_engine/compiler.py`
  - `kernel_gen/execute_engine/strategy.py`
  - `kernel_gen/execute_engine/builtin_strategy.py`
  - `kernel_gen/execute_engine/target_support.py`
  - `spec/execute_engine/execute_engine.md`
  - `spec/execute_engine/execute_engine_api.md`
  - `spec/execute_engine/execute_engine_target.md`
  - `spec/execute_engine/strategy.md`
  - `test/execute_engine/test_builtin_strategy.py`
  - `test/execute_engine/test_compile.py`
  - `test/execute_engine/test_compile_strategy.py`
  - `test/execute_engine/test_contract.py`
  - `agents/codex-multi-agents/log/task_records/2026/23/20260523-execute-engine-strategy-registry-rehome.md`

### Diff 反推审查

- `strategy.py`：
  - `CompileStrategy` / `register_compile_strategy(...)` / `get_compile_strategy(...)` 已成为 registry 真源。
  - 使用纯字符串注解保留 `CompileRequest` / `CompiledKernel` 签名文本；未 import `compiler.py`。
  - registry 错误 helper 与稳定 failure phrase 留在本文件内，未跨文件调用 `compiler.py` 私有 helper。
- `builtin_strategy.py`：
  - 只定义包内 `install_builtin_compile_strategies(strategy_factory)`。
  - 未进入包根 `__all__`，未导入 `compiler.py`，未引用 `CompileRequest`、`CompiledKernel`、`_BuiltinCompileStrategy` 或 `_AllowAbsentMemoryArg`。
  - 测试未 direct call 该安装函数，只通过公开 compile/get strategy 行为和 AST/static gate 观察边界。
- `compiler.py`：
  - 保留旧公开导入路径 re-export，实际对象身份指向 `strategy.py`。
  - `_BuiltinCompileStrategy`、target include / entry shim / compile unit、allow-absent ABI 与 `CompiledKernel` 装配仍留在本文件。
  - `install_builtin_compile_strategies(_BuiltinCompileStrategy)` 为唯一安装调用点。
  - 第一轮重复 `_dtype_code_from_name(...)` 已删除；AST 重复定义检查通过。
- `target_support.py`：
  - 文件已删除；旧 `BuiltinTargetSupportArtifacts` / `build_builtin_target_support_artifacts(...)` 未在 `kernel_gen/spec/test` 中残留。
- `spec/test`：
  - spec 已把 `target_support.py` 口径迁移为 `strategy.py` / `builtin_strategy.py` / `compiler.py` 私有实现边界。
  - `test_target_support.py` 已迁移为 `test_builtin_strategy.py`，target include、entry shim、template shim、trance 与 allow-absent 行为仍通过公开 `ExecutionEngine.compile(...)` / `CompiledKernel.execute(...)` 验证。
- `expectation`：
  - 计划正文明确本轮不运行、不修改 `expectation` 作为必过合同；本轮未运行 expectation，也未作为通过依据。

### 复跑验证

- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/execute_engine/test_compile.py test/execute_engine/test_builtin_strategy.py test/execute_engine/test_compile_strategy.py test/execute_engine/test_contract.py -ra`
  - 结果：`44 passed, 1 warning`
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/execute_engine/test_invoke.py -ra`
  - 结果：`19 passed`
- `PYTHONDONTWRITEBYTECODE=1 python3 -m compileall -q kernel_gen/execute_engine test/execute_engine`
  - 结果：`exit=0`
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest --collect-only -q test/execute_engine/test_compile.py test/execute_engine/test_builtin_strategy.py test/execute_engine/test_compile_strategy.py test/execute_engine/test_contract.py test/execute_engine/test_invoke.py`
  - 结果：`63 tests collected`
- import/API matrix：
  - 结果：`import api matrix ok`
- 旧文件与旧接口退场：
  - `test ! -f kernel_gen/execute_engine/target_support.py`
  - `test ! -f test/execute_engine/test_target_support.py`
  - `! rg -n "target_support|BuiltinTargetSupportArtifacts|build_builtin_target_support_artifacts" kernel_gen spec test`
  - 结果：通过，无输出。
- 静态 rg：
  - 覆盖 `strategy.py` / `builtin_strategy.py` 非公开导入、`compiler.py` 私有导入、ctx/context 能力探测、测试 direct call 安装函数、skip/xfail。
  - 结果：通过，无输出。
- 静态 AST：
  - 顶层重复函数/类定义：通过。
  - 非装饰器嵌套定义：通过。
  - `compiler.py` import allowlist：通过。
  - `strategy.py` / `builtin_strategy.py` 不 import `compiler.py`：通过。
  - `builtin_strategy.py` 无顶层 install/register call；`compiler.py` 唯一安装调用：通过。
- `git diff --check`
  - 结果：`exit=0`
- `git diff --cached --check`
  - 结果：`exit=0`
- 敏感目录门禁：
  - `git diff --name-only -- expectation .skills agents/standard`
  - `git diff --cached --name-only -- expectation .skills agents/standard`
  - `git status --short --ignored --untracked-files=all -- expectation .skills agents/standard`
  - 结果：三条均无输出。

### 自检

- 已按实际 diff 审查，不只依赖 execute 摘要。
- 已核对公开 API 用户确认来源：删除 `target_support.py` 与接口、strategy registry 拆出、builtin installer 独立文件但不暴露，均记录在计划书用户确认口径中。
- 已核对实现跨文件调用：`strategy.py` / `builtin_strategy.py` 不跨文件调用 `compiler.py` 私有 API；`compiler.py` 仅导入 `strategy.py` 公开 registry API 与 `builtin_strategy.py` 包内安装函数。
- 已核对测试边界：公开测试不 direct call `install_builtin_compile_strategies(...)`，target 行为经公开 compile/execute 入口验证。
- 已核对执行记录包含执行前阅读、用户补充指导处理、自检、Diff 反推自测、返工收口与门禁结果。
- 已核对 `expectation/`、`.skills/`、`agents/standard/**` 未进入候选 diff。

### 结论

- 结论：`通过`。
- 本任务为计划级任务，review 通过后应由管理员协调架构复核 / 终验；不得直接进入 merge。

## 架构复核 / 终验第一轮（大闸蟹，2026-05-23 19:19 +0800）

### 结论

- 结论：`通过`。
- 本轮未发现计划完成态、公开 API、导入边界、旧接口退场、测试有效性或敏感目录方面的可执行返工项。
- 本计划正文明确 `expectation` 不作为必过合同，本轮未运行 `expectation`，也不以 `expectation` 作为通过依据。
- 当前只完成计划级架构复核 / 终验第一轮，不进入 merge。

### 验证基线与同步现场

- 计划：`ARCHITECTURE/plan/execute_engine_strategy_registry_rehome_green_plan.md`
- 任务：`T-20260523-1aed88f5`
- 任务 worktree：`/home/lfr/kernelcode_generate/wt-20260523-execute-engine-strategy-registry-rehome`
- 原任务分支 HEAD：`5a9d524c733cc3838046319adf44015cb23ae49b`
- `origin/main`：`1381f0b687c7914c2eda95d31be55bf962502d53`
- `merge-base HEAD origin/main`：`5a9d524c733cc3838046319adf44015cb23ae49b`
- latest main 变化与候选 diff 路径交集：空。
- latest 同步验证现场：`/tmp/kg-final-sync-20260523-1aed88f5-52281`
  - 该临时 worktree 基于 `origin/main@1381f0b687c7914c2eda95d31be55bf962502d53`。
  - 已叠加任务候选 diff 与任务记录文件。
  - 未在原任务 worktree 中执行 merge 或进入合并阶段。

### 复核范围

- 候选 diff：
  - `agents/codex-multi-agents/log/task_records/2026/23/20260523-execute-engine-strategy-registry-rehome.md`
  - `kernel_gen/execute_engine/compiler.py`
  - `kernel_gen/execute_engine/strategy.py`
  - `kernel_gen/execute_engine/builtin_strategy.py`
  - `kernel_gen/execute_engine/target_support.py`
  - `spec/execute_engine/execute_engine.md`
  - `spec/execute_engine/execute_engine_api.md`
  - `spec/execute_engine/execute_engine_target.md`
  - `spec/execute_engine/strategy.md`
  - `test/execute_engine/test_builtin_strategy.py`
  - `test/execute_engine/test_compile.py`
  - `test/execute_engine/test_compile_strategy.py`
  - `test/execute_engine/test_contract.py`
- 人工核对：
  - `strategy.py` 承载 `CompileStrategy` / `register_compile_strategy(...)` / `get_compile_strategy(...)` 真源，未 import `compiler.py`。
  - `builtin_strategy.py` 只承载包内安装函数，未进入包根 `__all__`，未引用 `CompileRequest` / `CompiledKernel` / `_BuiltinCompileStrategy` / `_AllowAbsentMemoryArg`。
  - `compiler.py` 保留旧公开导入路径、内置 target 私有编译实现、allow-absent ABI 与 `CompiledKernel` 装配；`install_builtin_compile_strategies(_BuiltinCompileStrategy)` 为唯一安装调用点。
  - `target_support.py` 与 `test_target_support.py` 已退场；spec / test 不再把旧文件写作实现边界。
  - `_dtype_code_from_name(...)` 只剩一个顶层定义，第一轮 review 返工项已收口。

### 验证

- `git fetch origin`
  - 结果：通过。
- `git rev-parse HEAD && git rev-parse origin/main && git merge-base HEAD origin/main`
  - 结果：`HEAD=5a9d524c733cc3838046319adf44015cb23ae49b`；`origin/main=1381f0b687c7914c2eda95d31be55bf962502d53`；`merge-base=5a9d524c733cc3838046319adf44015cb23ae49b`。
- `comm -12 <(git diff --name-only HEAD..origin/main | sort) <(git diff --name-only | sort)`
  - 结果：无输出，路径交集为空。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/execute_engine/test_compile.py test/execute_engine/test_builtin_strategy.py test/execute_engine/test_compile_strategy.py test/execute_engine/test_contract.py -ra`
  - 结果：`44 passed, 1 warning`。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/execute_engine/test_invoke.py -ra`
  - 结果：`19 passed`。
- `PYTHONDONTWRITEBYTECODE=1 python3 -m compileall -q kernel_gen/execute_engine test/execute_engine`
  - 结果：`exit=0`。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest --collect-only -q test/execute_engine/test_compile.py test/execute_engine/test_builtin_strategy.py test/execute_engine/test_compile_strategy.py test/execute_engine/test_contract.py test/execute_engine/test_invoke.py`
  - 结果：`63 tests collected`。
- import / API matrix：
  - 结果：`import api matrix ok`。
  - 覆盖：四个模块全排列导入、包根 `__all__` 仍为 8 项、包根与 `compiler.py` 旧路径对象身份指向 `strategy.py`、`builtin_strategy.py` 文件存在但不进入包根公开 API。
- 旧文件与旧接口退场：
  - `test ! -f kernel_gen/execute_engine/target_support.py`
  - `test ! -f test/execute_engine/test_target_support.py`
  - `! rg -n "target_support|BuiltinTargetSupportArtifacts|build_builtin_target_support_artifacts" kernel_gen spec test`
  - 结果：通过，无输出。
- 静态 rg：
  - 覆盖 `strategy.py` / `builtin_strategy.py` 非公开导入、`compiler.py` 私有导入、ctx/context 能力探测、测试 direct call 安装函数、skip/xfail。
  - 结果：通过，无输出。
- 静态 AST：
  - 覆盖顶层重复函数/类定义、非装饰器嵌套定义、`compiler.py` import allowlist、`strategy.py` / `builtin_strategy.py` 不 import `compiler.py`、`builtin_strategy.py` 无顶层 install/register call、`compiler.py` 唯一安装调用。
  - 结果：通过，输出 `static rg ast ok`。
- `rg -n "def _dtype_code_from_name|_dtype_code_from_name\(" kernel_gen/execute_engine/compiler.py`
  - 结果：仅 `94` 行为定义，其余为调用点。
- `git diff --check && git diff --cached --check`
  - 结果：`exit=0`。
- 敏感目录门禁：
  - `git diff --name-only -- expectation .skills agents/standard`
  - `git diff --cached --name-only -- expectation .skills agents/standard`
  - `git status --short --ignored --untracked-files=all -- expectation .skills agents/standard`
  - 结果：三条均无输出。

### 自检

- 已按计划正文、review 复审记录和 latest 同步现场复核；未基于落后任务分支直接放行。
- 已核对公开 API 变更均有计划书中的用户确认来源；包根公开 API 不新增 `strategy`、`builtin_strategy`、`target_support` 或包内安装函数。
- 已核对实现没有跨文件调用 `compiler.py` 私有 API，测试没有 direct call `install_builtin_compile_strategies(...)`。
- 已核对文件级说明、API 列表、spec 关联和测试边界与计划完成态一致。
- 已将 `expectation` 与 diff 反推测试分开记录；本计划不运行 expectation 作为通过依据。
- 未修改 `expectation/`、`.skills/`、`agents/standard/**`，未手工修改 `TODO.md` / `DONE.md`。

### 下一步

- 请管理员按流程接续，不要由本轮终验直接进入 merge。

## 第二架构复核 / 终验（守护最好的爱莉希雅，2026-05-23 19:28 +0800）

### 结论

- 结论：`通过`。
- 本轮未发现计划完成态、公开 API、导入边界、旧接口退场、测试有效性、任务记录同批候选或敏感目录方面的可执行返工项。
- 本计划正文明确 `expectation` 不作为必过合同；本轮未运行 `expectation`，也不把 `expectation` 写作通过依据。
- 当前只完成第二架构计划级复核 / 终验，不直接进入 merge。

### 验证基线与同步现场

- 计划：`ARCHITECTURE/plan/execute_engine_strategy_registry_rehome_green_plan.md`
- 任务：`T-20260523-1aed88f5`
- 原任务 worktree：`/home/lfr/kernelcode_generate/wt-20260523-execute-engine-strategy-registry-rehome`
- 原任务分支 HEAD：`5a9d524c733cc3838046319adf44015cb23ae49b`
- `origin/main`：`1381f0b687c7914c2eda95d31be55bf962502d53`
- `merge-base HEAD origin/main`：`5a9d524c733cc3838046319adf44015cb23ae49b`
- 原任务分支落后 `origin/main` 1 个提交；`HEAD..origin/main` 与候选 diff 路径交集为空。
- latest 同步验证现场：`/tmp/kg-elysia-final-sync-20260523-1aed88f5-63334`
  - 临时 worktree 基于 `origin/main@1381f0b687c7914c2eda95d31be55bf962502d53`。
  - 已叠加任务候选 diff，并将新增 `strategy.py`、`builtin_strategy.py` 与本任务记录纳入 staged 候选，确保 `git diff --cached --check` 覆盖 untracked 新文件。
  - 未在原任务 worktree 中执行 merge，也未进入合并阶段。
  - 验证完成后已清理该临时 worktree；原任务 worktree 保持候选 diff 状态。

### 复核范围

- 候选 diff：
  - `agents/codex-multi-agents/log/task_records/2026/23/20260523-execute-engine-strategy-registry-rehome.md`
  - `kernel_gen/execute_engine/builtin_strategy.py`
  - `kernel_gen/execute_engine/compiler.py`
  - `kernel_gen/execute_engine/strategy.py`
  - `kernel_gen/execute_engine/target_support.py`
  - `spec/execute_engine/execute_engine.md`
  - `spec/execute_engine/execute_engine_api.md`
  - `spec/execute_engine/execute_engine_target.md`
  - `spec/execute_engine/strategy.md`
  - `test/execute_engine/test_builtin_strategy.py`
  - `test/execute_engine/test_compile.py`
  - `test/execute_engine/test_compile_strategy.py`
  - `test/execute_engine/test_contract.py`
- 人工核对：
  - `strategy.py` 承载 `CompileStrategy` / `register_compile_strategy(...)` / `get_compile_strategy(...)` 真源，使用纯字符串注解维持 `CompileRequest` / `CompiledKernel` 签名文本，未 import `compiler.py`。
  - `builtin_strategy.py` 只承载包内 `install_builtin_compile_strategies(strategy_factory)`，未进入包根 `__all__`，未引用 `CompileRequest`、`CompiledKernel`、`_BuiltinCompileStrategy` 或 `_AllowAbsentMemoryArg`。
  - `compiler.py` 保留旧公开导入路径、内置 target 私有编译实现、allow-absent ABI 与 `CompiledKernel` 装配；`install_builtin_compile_strategies(_BuiltinCompileStrategy)` 为唯一安装调用点。
  - `target_support.py` 与 `test_target_support.py` 已退场；spec / test 不再把旧文件写作实现边界。
  - 第一轮 review 指出的重复 `_dtype_code_from_name(...)` 已收口；AST 与 `rg` 均显示仅剩一个顶层定义。

### 验证

- `git fetch origin --prune`
  - 结果：通过。
- 原任务 worktree 基线：
  - `HEAD=5a9d524c733cc3838046319adf44015cb23ae49b`
  - `origin/main=1381f0b687c7914c2eda95d31be55bf962502d53`
  - `merge-base=5a9d524c733cc3838046319adf44015cb23ae49b`
  - `ahead/behind=0/1`
- latest 同步临时 worktree 基线：
  - `HEAD=origin/main=merge-base=1381f0b687c7914c2eda95d31be55bf962502d53`
- `comm -12 <(git diff --name-only HEAD..origin/main | sort) <(git diff --name-only HEAD | sort)`
  - 结果：无输出，latest main 变化与候选 tracked diff 路径交集为空。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/execute_engine/test_compile.py test/execute_engine/test_builtin_strategy.py test/execute_engine/test_compile_strategy.py test/execute_engine/test_contract.py -ra`
  - 结果：`44 passed, 1 warning in 9.18s`。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/execute_engine/test_invoke.py -ra`
  - 结果：`19 passed in 2.30s`。
- `PYTHONDONTWRITEBYTECODE=1 python3 -m compileall -q kernel_gen/execute_engine test/execute_engine`
  - 结果：`exit=0`。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest --collect-only -q test/execute_engine/test_compile.py test/execute_engine/test_builtin_strategy.py test/execute_engine/test_compile_strategy.py test/execute_engine/test_contract.py test/execute_engine/test_invoke.py`
  - 结果：`63 tests collected`。
- import / API matrix：
  - 结果：`import api matrix ok`。
  - 覆盖四个模块全排列导入、包根 `__all__` 仍为 8 项、包根与 `compiler.py` 旧路径对象身份指向 `strategy.py`、`builtin_strategy.py` 文件存在但不进入包根公开 API。
- 旧文件与旧接口退场：
  - `test ! -f kernel_gen/execute_engine/target_support.py`
  - `test ! -f test/execute_engine/test_target_support.py`
  - `! rg -n "target_support|BuiltinTargetSupportArtifacts|build_builtin_target_support_artifacts" kernel_gen spec test`
  - 结果：通过，输出 `old-files-absent`。
- 静态 rg：
  - 覆盖 `strategy.py` / `builtin_strategy.py` 非公开导入、`compiler.py` 私有导入、ctx/context 能力探测、测试 direct call 安装函数、`importlib` / `__import__` / `eval` 与 skip/xfail。
  - 结果：`static-rg-ok`。
- 静态 AST：
  - 非装饰器嵌套定义：`nested-definition-ok`。
  - `compiler.py` import allowlist：`compiler-import-allowlist-ok`。
  - `strategy.py` / `builtin_strategy.py` 不 import `compiler.py`：`strategy-builtin-no-compiler-import-ok`。
  - `builtin_strategy.py` 无顶层 install/register call，`compiler.py` 唯一安装调用：`install-boundary-ok`。
  - `compiler.py` 顶层函数 / 类无重复：`compiler-top-level-definitions-unique`。
- `rg -n "def _dtype_code_from_name|_dtype_code_from_name\(" kernel_gen/execute_engine/compiler.py`
  - 结果：仅第 `94` 行为定义，其余为调用点。
- `git diff --check`
  - 结果：`exit=0`。
- `git diff --cached --check`
  - 结果：`exit=0`。
- 敏感目录门禁：
  - `git diff --name-only -- expectation .skills agents/standard`
  - `git diff --cached --name-only -- expectation .skills agents/standard`
  - `git status --short --ignored --untracked-files=all -- expectation .skills agents/standard`
  - 结果：三条均无输出。

### 合同验收

- 当前计划明确：不新增、不修改、不运行 `expectation` 作为必过合同。
- 本轮未运行 `python3 -m expectation...`，也未将 `expectation` 作为通过依据。
- 已按计划核对 `expectation/`、`.skills/`、`agents/standard/**` 候选 diff / staged diff / ignored-untracked 状态均为空。

### 自检

- 已基于 latest `origin/main` 临时现场复核，不在落后任务分支上直接放行。
- 已核对公开 API：包根 `__all__` 不变；`strategy.py` 为 registry 真源；`compiler.py` 旧公开导入路径保留；`builtin_strategy.py` 不作为包根公开 API。
- 已核对用户确认来源：删除 `target_support.py` 与接口、拆出 strategy registry、内置注册独立文件但不暴露均在计划书记录。
- 已核对实现边界：`strategy.py` / `builtin_strategy.py` 不跨文件调用 `compiler.py` 私有 API，`compiler.py` 只 late import 包内安装函数。
- 已核对测试边界：公开测试不 direct call `install_builtin_compile_strategies(...)`，内置 target 行为通过公开 compile / execute 入口验证。
- 已核对任务记录已纳入 latest 临时现场 staged 候选；merge 时仍必须与代码 / spec / test 同批合入。
- 已将 `expectation` 合同验收与 Diff 反推测试分开记录；本计划没有必过 `expectation`。
- 未修改 `expectation/`、`.skills/`、`agents/standard/**`，未手工修改 `TODO.md` / `DONE.md`，未执行 merge。

### 下一步

- 请管理员按流程接续；双架构终验已通过后，可由合并角色按合并规范核对 latest main、候选 diff、任务记录同批、计划门禁摘要与敏感目录空 diff后进入 merge。

## Merge 收口（李白，2026-05-23 19:38 CST）

时间：2026-05-23 19:38 CST
经办人：李白
任务：T-20260523-1aed88f5 / execute-engine-strategy-registry-rehome / merge
任务目标：按合并规范合入已通过 review 与双架构计划级复核 / 终验的 execute-engine strategy registry rehome 候选 diff；核对 latest main、候选范围、任务记录同批、计划门禁摘要、git diff check 与敏感目录空 diff。

合并前同步与来源：
- 已重新读取 `agents/codex-multi-agents/agents/李白/李白.prompt.md`、根 `AGENTS.md`、`agents/standard/合并规范.md`、`agents/standard/任务记录约定.md`、`agents/standard/expectation任务规则.md`。
- 主仓集成目录：`/home/lfr/kernelcode_generate`。
- 任务 worktree：`/home/lfr/kernelcode_generate/wt-20260523-execute-engine-strategy-registry-rehome`。
- 计划真源：主仓只读 `ARCHITECTURE/plan/execute_engine_strategy_registry_rehome_green_plan.md`。
- 已执行 `git fetch --prune origin`；任务 worktree 原始 `HEAD=5a9d524c733cc3838046319adf44015cb23ae49b`，`origin/main=1381f0b687c7914c2eda95d31be55bf962502d53`，落后 1 个提交。
- 合并前核对 `HEAD..origin/main` 与候选 diff 路径交集为空；随后在任务 worktree 执行 `git merge --ff-only origin/main`，同步后 `HEAD=origin/main=merge-base=1381f0b687c7914c2eda95d31be55bf962502d53`，ahead/behind=`0 0`。
- 主仓 `main` 当前 clean，且与 `origin/main` 对齐。
- `TODO.md` 中任务为 `merge / 李白 / 进行中`；管理员 / 架构消息要求执行 merge，且明确本计划不运行 `expectation` 作为通过依据。

实际合入范围：
- 实现：`kernel_gen/execute_engine/compiler.py`、新增 `kernel_gen/execute_engine/strategy.py`、新增 `kernel_gen/execute_engine/builtin_strategy.py`、删除 `kernel_gen/execute_engine/target_support.py`。
- spec：`spec/execute_engine/execute_engine.md`、`spec/execute_engine/execute_engine_api.md`、`spec/execute_engine/execute_engine_target.md`、`spec/execute_engine/strategy.md`。
- test：`test/execute_engine/test_builtin_strategy.py`、`test/execute_engine/test_compile.py`、`test/execute_engine/test_compile_strategy.py`、`test/execute_engine/test_contract.py`；旧 `test/execute_engine/test_target_support.py` 退场。
- 同批任务记录：`agents/codex-multi-agents/log/task_records/2026/23/20260523-execute-engine-strategy-registry-rehome.md`。
- 不纳入 `expectation/`、`.skills/`、`agents/standard/**`，不纳入状态文件 `TODO.md` / `DONE.md` 手工改动。

验证：
- 候选范围：
  - `git diff --name-status`：仅 execute_engine 实现、spec、test 及旧 `target_support.py` 删除。
  - `git ls-files --others --exclude-standard`：仅 `strategy.py`、`builtin_strategy.py` 与本任务记录。
  - `git diff --name-only -- expectation .skills agents/standard`：无输出。
  - `git diff --cached --name-only -- expectation .skills agents/standard`：无输出。
  - `git status --short --untracked-files=all -- expectation .skills agents/standard`：无输出。
  - `git status --short --ignored --untracked-files=all -- expectation .skills agents/standard`：无输出。
- Diff 反推 pytest：
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/execute_engine/test_compile.py test/execute_engine/test_builtin_strategy.py test/execute_engine/test_compile_strategy.py test/execute_engine/test_contract.py -ra`：exit=0，`44 passed, 1 warning`。
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/execute_engine/test_invoke.py -ra`：exit=0，`19 passed`。
- collect 与语法：
  - `PYTHONDONTWRITEBYTECODE=1 python3 -m compileall -q kernel_gen/execute_engine test/execute_engine`：exit=0。
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest --collect-only -q test/execute_engine/test_compile.py test/execute_engine/test_builtin_strategy.py test/execute_engine/test_compile_strategy.py test/execute_engine/test_contract.py test/execute_engine/test_invoke.py`：exit=0，`63 tests collected`。
- import / API matrix：
  - 计划脚本覆盖 `kernel_gen.execute_engine.strategy` / `builtin_strategy` / `compiler` / package root 全排列导入、包根 `__all__` 8 项、旧路径对象身份与 `strategy.py` 真源一致、`builtin_strategy.py` 文件存在但不进入包根公开 API。
  - 结果：exit=0，`import api matrix ok`。
- 旧文件与旧接口退场：
  - `test ! -f kernel_gen/execute_engine/target_support.py && test ! -f test/execute_engine/test_target_support.py && ! rg -n "target_support|BuiltinTargetSupportArtifacts|build_builtin_target_support_artifacts" kernel_gen spec test`：exit=0。
- 静态 rg：
  - 覆盖 `strategy.py` / `builtin_strategy.py` 非公开导入、`compiler.py` 私有导入、ctx/context 能力探测、测试 direct call 安装函数、`importlib` / `__import__` / `eval` 与 skip/xfail。
  - 结果：exit=0，无输出。
- 静态 AST：
  - 覆盖函数体内非装饰器嵌套定义、`compiler.py` import allowlist、`strategy.py` / `builtin_strategy.py` 不 import `compiler.py`、`builtin_strategy.py` 无顶层 install/register call、`compiler.py` 唯一安装调用、`compiler.py` 顶层函数 / 类无重复。
  - 结果：exit=0，输出 `nested-definition-ok`、`compiler-import-allowlist-ok`、`strategy-builtin-no-compiler-import-ok`、`install-boundary-ok`、`compiler-top-level-definitions-unique`。
- `_dtype_code_from_name` 单定义：
  - `rg -n "def _dtype_code_from_name|_dtype_code_from_name\\(" kernel_gen/execute_engine/compiler.py`：仅第 `94` 行为定义，其余为调用点。
- 格式：
  - `git diff --check && git diff --cached --check`：exit=0。
- 合同验收：
  - 本计划明确不新增、不修改、不运行 `expectation` 作为必过合同；merge 本轮未运行 `expectation`，也不将 `expectation` 写作通过依据。

冲突处理：
- 任务 worktree 落后 latest main 的 1 个提交仅涉及上一任务 DSL scratch alloc 文件与记录；候选 diff 路径交集为空。
- `git merge --ff-only origin/main` 在任务 worktree 中无冲突完成；未覆盖主仓或其他任务本地改动。
- 合并方式计划为任务分支提交候选 diff 后，主仓 `main` 进行 fast-forward 合入，避免手工复制遗漏。

剩余风险：
- 仅保留既有 xDSL deprecation warning；review 与双架构终验已记录同类 warning，不构成本轮阻断。
- 本轮不修改或运行 `expectation`；若后续计划需要 expectation 合同，应另行确认。

结论：merge gate 通过，可将上述实现 / spec / test 与本任务记录同批提交、推送并执行 `-done`。
