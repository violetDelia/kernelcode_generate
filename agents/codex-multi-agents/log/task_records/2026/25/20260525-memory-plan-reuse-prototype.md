# T-20260525-a814d111 memory-plan-reuse-prototype

## 2026-05-25 管理员建档 / 经办人：神秘人

- 任务类型：普通小任务 execute，无计划书。
- worktree：`/home/lfr/kernelcode_generate/wt-20260525-memory-plan-reuse-prototype`
- 记录文件：`agents/codex-multi-agents/log/task_records/2026/25/20260525-memory-plan-reuse-prototype.md`
- 基线：`origin/main` = `758b5c62b6ef25f591d35a610484bd23afe44477`
- 任务目标：为 `kernel_gen/passes/memory_plan.py` 增加第一版可选 memory reuse 能力，并同步 `spec/pass/memory_plan.md` 与相关文件级 API 列表。
- 公开 API 精确口径：`MemoryPlanPass(insert_free: bool = False, fold: bool = True, reuse: bool = False)`；`from_options` 支持 `reuse=true|false|1|0|yes|no|on|off`；registry 使用 `memory-plan={reuse=true}`；默认 `reuse=False` 保持现有行为；未知 option / 非法 bool 沿用 `MemoryPlanOptionError` 稳定前缀。
- 实现口径：参考 MLIR ownership/liveness、XLA BufferAssignment/lifetime、IREE stream reuse allocations、TVM USMP 的基本思想，第一版采用保守 linear-scan live interval reuse；在 `insert_free` 与 `reuse` 同时开启时，对同一 supported owner block 内的 `dma.alloc` 建 alias closure 与 live interval，按 exact memory type 或可证明兼容 bucket 分组，生命周期不重叠才复用；优先只支持同 block、同 space、dtype、rank、shape、stride 的安全复用。
- 边界：遇 return/yield/call escape、unsupported CFG、未知 memory-producing op、free-before-use、重复 free、跨 region 不可证明 use 时保持既有错误或 no-op，不扩大控制流支持。
- 物化口径：第一版可以直接把后续可复用 alloc 的 data uses 替换为 slot base alloc，删除被复用 alloc/free，并把 slot 的最终 free 放到最后一个 interval 之后；若实现者发现 xDSL op 移动风险高，可退化为给 alloc 标注 memory-plan reuse slot 并记录未物化原因。
- 非目标：不修改 memory-pool，不接入 npu-demo-lowering，不新增 pipeline option，不新增/修改 expectation，不新增测试文件。
- 验收：`python3 -m py_compile kernel_gen/passes/memory_plan.py`；用本地一次性脚本构造最小 IR/Operation 运行 `MemoryPlanPass(insert_free=True, reuse=True)`，证明两个不重叠同类型 alloc 被复用或明确记录保守 no-op 原因；`git diff --check`；`expectation/.skills/agents/standard` 空 diff。
- 参考资料：MLIR Ownership-based Buffer Deallocation `https://mlir.llvm.org/docs/OwnershipBasedBufferDeallocation/`；OpenXLA buffer assignment `https://openxla.org/xla/hlo_to_thunks`；IREE stream passes reuse allocations `https://iree.dev/reference/mlir-passes/Stream/`；TVM USMP RFC `https://discuss.tvm.apache.org/t/rfc-unified-static-memory-planning/10099`。
- 禁止修改面：`expectation/`、`.skills/`、`agents/standard/`。

## 2026-05-25 04:16 execute 进展与完成 / 经办人：金铲铲大作战

时间：2026-05-25 04:16 CST
经办人：金铲铲大作战
任务：T-20260525-a814d111 / memory-plan-reuse-prototype
任务目标：为 `kernel_gen/passes/memory_plan.py` 增加第一版可选 memory reuse，并同步 `spec/pass/memory_plan.md`、registry spec、相关文件级 API 列表和现有测试文件；候选 diff 不包含 `expectation/.skills/agents/standard`。

执行前阅读记录：
- 已读取最新个人提示词 `agents/codex-multi-agents/agents/金铲铲大作战/金铲铲大作战.prompt.md`、根 `AGENTS.md`、`agents/standard/实现文件规范.md`、`agents/standard/任务记录约定.md`、`agents/standard/协作执行通用规则.md`。
- 已读取本任务建档段、`kernel_gen/passes/memory_plan.py`、`spec/pass/memory_plan.md`、`spec/pass/registry.md`、`kernel_gen/passes/__init__.py`、`kernel_gen/passes/registry.py`、`test/passes/test_memory_plan.py`、`test/passes/test_registry.py`。
- worktree 核对：执行目录 `/home/lfr/kernelcode_generate/wt-20260525-memory-plan-reuse-prototype`；`HEAD=origin/main=merge-base=758b5c62b6ef25f591d35a610484bd23afe44477`；初始候选 diff 仅有本记录目录未跟踪。

改动：
- `kernel_gen/passes/memory_plan.py`
  - 公开 API 更新为 `MemoryPlanPass(insert_free: bool = False, fold: bool = True, reuse: bool = False)`，默认 `reuse=False` 保持现有 no-op / insert-free 行为。
  - `MemoryPlanPass.from_options(...)` 支持 `reuse=true|false|1|0|yes|no|on|off`，未知 option 与非法 bool 继续走 `MemoryPlanOptionError` 稳定前缀；新增非法 reuse 文本 `MemoryPlanOptionError: reuse expects bool`。
  - `apply(...)` 保持先用既有生命周期分析补齐 `dma.free`，仅在 `insert_free=True` 且 `reuse=True` 后追加保守 linear-scan 复用：同一 supported owner block、`NnMemoryType` 完全一致、前一 interval free 早于后一 alloc 才复用；复用时删除前一旧 free 与后一 alloc，并把最终 free 延长到后一 interval 末尾。
- `spec/pass/memory_plan.md`
  - 同步 API、option、reuse 行为、非目标、错误语义、registry 示例与 TC-MPLAN-003A/003B 测试矩阵。
- `spec/pass/registry.md`、`kernel_gen/passes/__init__.py`、`kernel_gen/passes/registry.py`
  - 同步 memory-plan `reuse` option 与 API 列表 / 文件级说明。
- `test/passes/test_memory_plan.py`
  - 在现有测试文件内新增公开 API 测试，不新增测试文件：正例证明同 block、同类型、生命周期不重叠 alloc 被复用；负例证明 shape/stride 不一致时保守 no-op。
- `test/passes/test_registry.py`
  - 扩展 memory-plan registry option 正反例，覆盖 `reuse=on` 与非法 `reuse=maybe` 的 direct / registry 错误语义。

最小功能闭环：
- `reuse=False` 默认不触发复用，既有 insert-free 逻辑保持不变。
- `reuse=True` 单独开启但 `insert_free=False` 时仍按 `insert_free=False` 的公开 no-op 行为返回。
- `insert_free=True,reuse=True` 时只复用同 owner block、同完整 memory type、非重叠生命周期；遇 escape、unsupported CFG、free-before-use、重复 free 等继续沿用既有生命周期分析错误，不扩大控制流或 ownership 支持。
- 未修改 `memory-pool`，未接入 `npu-demo-lowering`，未新增 pipeline option，未新增测试文件，未修改 `expectation/`。

Diff 反推自测：
- 实现与 spec 改动反推：
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 -m py_compile kernel_gen/passes/memory_plan.py`，exit=0。
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/passes/test_memory_plan.py test/passes/test_registry.py`，exit=0，`81 passed, 1 warning`；覆盖 memory-plan insert-free 既有行为、reuse 正反例和 registry option 正反例。
- 本地一次性脚本：
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 - <<'PY' ...` 构造两个同类型、不重叠 `dma.alloc`，执行 `MemoryPlanPass(insert_free=True, fold=False, reuse=True)` 后断言 `allocs=1`、`frees=1`、第二个 `dma.broadcast.target` 已改用第一个 alloc，exit=0，输出 `reuse_proved allocs=1 frees=1 second_write_uses_first_alloc=1`。
- 静态边界扫描：
  - `git diff -U0 -- kernel_gen/passes/memory_plan.py test/passes/test_memory_plan.py test/passes/test_registry.py | rg -n "hasattr\\(|getattr\\(|callable\\(getattr|def .+def " || true`，exit=0，无命中；本轮 diff 未新增 ctx 能力探测或嵌套函数。
- 敏感目录门禁：
  - `git diff --name-only -- expectation .skills agents/standard`，exit=0，无输出。
- 格式门禁：
  - `git diff --check`，exit=0。

验证：
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 -m py_compile kernel_gen/passes/memory_plan.py`：exit=0。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/passes/test_memory_plan.py -k 'reuse or memory_plan_ircheck_inserts_free_for_static_alloc or memory_plan_keeps_existing_free_noop'`：exit=0，`4 passed, 19 deselected, 1 warning`。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/passes/test_registry.py -k 'memory_plan'`：exit=0，`2 passed, 56 deselected, 1 warning`。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/passes/test_memory_plan.py test/passes/test_registry.py`：exit=0，`81 passed, 1 warning`。
- 本地一次性 reuse 证明脚本：exit=0，输出 `reuse_proved allocs=1 frees=1 second_write_uses_first_alloc=1`。
- `git diff --check`：exit=0。
- `git diff --name-only -- expectation .skills agents/standard`：exit=0，无输出。

减法检查：
- 新增 callable：无。
- 新增 private callable：无；新增 `_ReuseInterval` 为当前文件内私有 dataclass，不是 callable。
- 改动 private callable：`_parse_bool_option(name, value)` 从仅解析 `insert-free` 扩展为按 option name 生成稳定 bool 错误文本。该 helper 原本已由 `from_options` 使用，本轮未新增新的跨文件私有 API 调用，也未新增私有 helper 链。
- 被替代旧逻辑：`from_options` 旧的单 option 分支被替换为 `insert-free` / `reuse` 双 option 分支；旧的 `insert-free` 解析与未知 option 错误语义保留。
- 保留旧逻辑依据：既有 alias closure、owner block 校验、use/free 顺序校验和 insert-free 插入逻辑是 reuse 安全性的前置证明，继续复用，避免另建重复生命周期分析。

自检：
- 接口：公开 API 变更与用户任务目标一致；未新增未确认公开 API；`reuse` 默认关闭，兼容既有 direct API、registry 与 pipeline 调用。
- 边界：reuse 只在 `insert_free=True` 后执行；仅同 owner block、同完整 `NnMemoryType`、非重叠 interval 复用；跨 region、unsupported CFG、未知 memory-producing、escape、free-before-use、重复 free 继续由既有分析失败或 no-op。
- 异常：新增 `reuse expects bool` 与 `insert-free expects bool` 同属 `MemoryPlanOptionError` 前缀；registry 包装错误已补测试。
- 测试有效性：正例会在未删除后续 alloc / 未替换第二次 use / 未延长最终 free 时失败；负例会在错误复用 shape/stride 不一致 alloc 时失败；registry 测试锁定 option 解析和稳定错误短语。
- 复杂度与复用：没有复制生命周期分析；reuse 逻辑直接复用现有 alias closure 和 free 校验结果；未引入 memory-pool、pipeline 或 expectation 依赖。
- 注释与文档：功能实现文件 API 列表、类 / 方法注释、spec 与 registry 文档已同步；人员元信息未纳入。
- 敏感目录：`expectation/.skills/agents/standard` 无 diff。

结论：execute 已完成，候选 diff 位于任务允许范围，验证通过；下一步按普通任务流程续接 review。

## 2026-05-25 04:20 review 结论 / 经办人：提莫炖蘑菇

时间：2026-05-25 04:20 CST
经办人：提莫炖蘑菇
任务：T-20260525-a814d111 / memory-plan-reuse-prototype
任务目标：审查 memory-plan reuse prototype 的公开 API、from_options/registry 语义、保守 linear-scan 复用实现、spec/API 列表、现有测试文件内 pytest、Diff 反推自测与敏感目录门禁记录。

最新同步现场：
- 执行目录：`/home/lfr/kernelcode_generate/wt-20260525-memory-plan-reuse-prototype`
- 已执行：`git fetch origin`，exit=0。
- 基线核对：`HEAD=758b5c62b6ef25f591d35a610484bd23afe44477`，`origin/main=758b5c62b6ef25f591d35a610484bd23afe44477`，`merge-base=758b5c62b6ef25f591d35a610484bd23afe44477`。
- 工作树：任务候选 diff 为未提交工作树改动，含 `kernel_gen/passes/__init__.py`、`kernel_gen/passes/memory_plan.py`、`kernel_gen/passes/registry.py`、`spec/pass/memory_plan.md`、`spec/pass/registry.md`、`test/passes/test_memory_plan.py`、`test/passes/test_registry.py` 和本任务记录目录；未发现主线落后或合并冲突风险。

被审 diff：
- `kernel_gen/passes/memory_plan.py`：新增 `reuse` constructor 参数、`from_options` reuse bool、`apply` 中保守 linear-scan reuse、`_ReuseInterval`。
- `kernel_gen/passes/__init__.py`、`kernel_gen/passes/registry.py`：同步文件级 API / registry 文案。
- `spec/pass/memory_plan.md`、`spec/pass/registry.md`：同步公开 API、option、reuse 行为、错误语义和测试矩阵。
- `test/passes/test_memory_plan.py`、`test/passes/test_registry.py`：新增现有测试文件内 reuse 正反例和 registry option 正反例。

Diff 反推审查：
- 已复跑 `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/passes/test_memory_plan.py test/passes/test_registry.py`，exit=0，`81 passed, 1 warning`。
- 已复跑 `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 -m py_compile kernel_gen/passes/memory_plan.py`，exit=0。
- 已复跑 `git diff --check`，exit=0。
- 已复跑敏感目录门禁：
  - `git diff --name-only -- expectation .skills agents/standard`，exit=0，无输出。
  - `git diff --cached --name-only -- expectation .skills agents/standard`，exit=0，无输出。
  - `git status --short --ignored --untracked-files=all -- expectation .skills agents/standard`，exit=0，无输出。
- 静态扫描：`rg -n "hasattr\\(|getattr\\(|callable\\(getattr|def .+def |object" kernel_gen/passes/memory_plan.py test/passes/test_memory_plan.py test/passes/test_registry.py` 命中均为既有 registry 测试中的通用公开对象断言 / attr 断言；未发现本轮新增 ctx 能力探测、嵌套函数或 `object` 签名。

发现：
- 最小需改项：`kernel_gen/passes/memory_plan.py:249` 本轮改动了私有 callable `_parse_bool_option(name, value)`，该函数仍在 `kernel_gen/passes/memory_plan.py:265` 调用同文件私有 callable `_raise_memory_plan_error(...)`。影响：违反当前审查规范“改动的 private callable 不得调用其它 private callable”的硬门禁；执行记录已把它列入改动 private callable，但以“既有 helper 链”作为保留依据，不满足本轮减法审查要求。最小返工动作：将 `_parse_bool_option(...)` 的错误路径改为不调用其它 private callable，例如直接构造并抛出同等 `KernelCodeError(ErrorKind.CONTRACT, ErrorModule.PASS, f"MemoryPlanOptionError: {name} expects bool")`，或把 bool 解析逻辑内联到公开 `from_options(...)`，并更新减法检查。验收方式：复跑 `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/passes/test_memory_plan.py test/passes/test_registry.py`、`PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 -m py_compile kernel_gen/passes/memory_plan.py`、`git diff --check`，并用 `rg -n "def _parse_bool_option|_parse_bool_option\\(|_raise_memory_plan_error\\(" kernel_gen/passes/memory_plan.py` 核对改动后的 private callable 不再调用 private callable。

减法审查：
- 已核对执行记录中的减法检查。本轮无新增 private function；新增 `_ReuseInterval` 为私有 dataclass，不按 private function 处理。
- 本轮改动 private callable：`_parse_bool_option(name, value)`，有效代码行数不少于 5 行，但仍调用 `_raise_memory_plan_error(...)`，不满足当前私有函数审查门禁。
- 旧逻辑替代关系：`from_options` 从单 `insert-free` option 分支扩展为 `insert-free` / `reuse` 双 option 分支；旧 `insert-free` 错误语义由测试覆盖。保留 `_raise_memory_plan_error` 作为公开方法和其它存量 helper 的错误出口不在本轮直接阻断范围，但本轮改动的 `_parse_bool_option` 不能继续调用它。

执行记录核对：
- 执行前阅读、最小功能闭环、自检、Diff 反推自测、敏感目录门禁记录完整。
- 测试与 diff 基本匹配，reuse 正例可证明后续 alloc 被删除并复用前一 alloc，负例可证明类型不一致 no-op，registry 测试覆盖 `reuse=on` 与 `reuse=maybe`。
- 阻断项集中在私有 callable 减法审查门禁，不是行为测试失败。

自检：
- 已读取实际 diff、任务记录、相关实现/spec/test。
- 已核对公开 API 变更来源、文件级 API 列表、registry option、测试是否只走公开 API、expectation/.skills/agents/standard 禁止修改面。
- 已完成减法审查和私有函数审查；发现 1 个可执行返工项，结论不得通过。

结论：最小需改项。请退回 execute 按上述 private callable 门禁收口后复审。

## 2026-05-25 04:22 execute 返工完成 / 经办人：睡觉小分队

时间：2026-05-25 04:22 CST
经办人：睡觉小分队
任务：T-20260525-a814d111 / memory-plan-reuse-prototype
任务目标：修复 review 指出的最小阻断项：本轮改动的 `_parse_bool_option(...)` 不得继续调用私有 `_raise_memory_plan_error(...)`，补齐减法检查并复跑 memory_plan / registry pytest、py_compile、git diff check 与敏感目录门禁。

执行前阅读记录：
- 已重新读取个人提示词 `agents/codex-multi-agents/agents/睡觉小分队/睡觉小分队.prompt.md`、根 `AGENTS.md`、`agents/standard/协作执行通用规则.md`、`agents/standard/任务记录约定.md`、`agents/standard/实现文件规范.md`、`agents/standard/测试文件约定.md`、`agents/standard/expectation任务规则.md`。
- 已读取本任务建档、前序 execute 记录和 2026-05-25 04:20 review 结论；本轮仅处理 `_parse_bool_option(...)` 私有 callable 门禁问题。
- 执行目录：`/home/lfr/kernelcode_generate/wt-20260525-memory-plan-reuse-prototype`。

返工改动：
- `kernel_gen/passes/memory_plan.py`：将 `_parse_bool_option(name, value)` 的非法 bool 错误路径改为直接抛出 `KernelCodeError(ErrorKind.CONTRACT, ErrorModule.PASS, f"MemoryPlanOptionError: {name} expects bool")`，不再调用同文件私有 `_raise_memory_plan_error(...)`。
- 未改公开 API、spec、测试语义或 `expectation/.skills/agents/standard`。

最小功能闭环：
- `MemoryPlanPass.from_options(...)` 对 `insert-free` / `reuse` 的合法 bool 解析保持不变。
- 非法 bool 仍保持公开稳定文本：`MemoryPlanOptionError: <name> expects bool`，registry 包装语义保持不变。
- `_raise_memory_plan_error(...)` 仍供其它 memory-plan 生命周期错误路径使用；本轮阻断的 private callable 调用 private callable 已消除。

Diff 反推自测：
- 实际改动文件：`kernel_gen/passes/memory_plan.py` 与本任务记录。
- 反推测试：
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 -m py_compile kernel_gen/passes/memory_plan.py`，exit=0。
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/passes/test_memory_plan.py test/passes/test_registry.py`，exit=0，`81 passed, 1 warning`；覆盖 memory-plan reuse 行为、from_options bool 错误和 registry 包装错误。
  - `rg -n "def _parse_bool_option|_parse_bool_option\\(|_raise_memory_plan_error\\(" kernel_gen/passes/memory_plan.py`，exit=0；显示 `_parse_bool_option` 调用点和 `_raise_memory_plan_error` 存量调用点，确认 `_parse_bool_option` 函数体内不再调用 `_raise_memory_plan_error`。
  - `git diff --check`，exit=0。
- 敏感目录门禁：
  - `git diff --name-only -- expectation .skills agents/standard`，exit=0，无输出。
  - `git diff --cached --name-only -- expectation .skills agents/standard`，exit=0，无输出。
  - `git status --short --ignored --untracked-files=all -- expectation .skills agents/standard`，exit=0，无输出。

验证：
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 -m py_compile kernel_gen/passes/memory_plan.py`：exit=0。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/passes/test_memory_plan.py test/passes/test_registry.py`：exit=0，`81 passed, 1 warning`。
- `git diff --check`：exit=0。
- 敏感目录三条门禁：exit=0，均无输出。

减法检查：
- 新增 private callable：无。
- 改动 private callable：`_parse_bool_option(name, value)`。
- 被替代旧逻辑：`_parse_bool_option(...)` 非法 bool 分支原先复用 `_raise_memory_plan_error(...)`，现改为直接构造并抛出同等 `KernelCodeError`，删除本轮 private callable 调用 private callable 的依赖。
- 保留旧逻辑依据：`_raise_memory_plan_error(...)` 仍是其它生命周期分析错误路径的统一出口，未被本轮 review 点名，且不是 `_parse_bool_option(...)` 的被调用路径；保留可避免扩大返工范围。
- 私有函数门禁：`_parse_bool_option(...)` 有效代码不少于 5 行，且不再调用其它 private callable。

自检：
- 接口：未新增或修改公开 API；`MemoryPlanPass`、`from_options`、registry option 公开语义保持前序 execute 口径。
- 边界：只收口 review 点名的 private callable 调用边界，不扩大 memory-plan reuse 行为、不触碰 pipeline / memory-pool / expectation。
- 异常：非法 bool 错误类型仍为 `KernelCodeError(ErrorKind.CONTRACT, ErrorModule.PASS, ...)`，错误文本保持 `MemoryPlanOptionError: <name> expects bool`。
- 兼容：合法 bool、未知 option、registry 包装错误均由现有 pytest 覆盖。
- 实现质量：本轮未新增 helper；消除了 private callable 链式调用，复杂度未上升。
- 测试有效性：`test_registry.py` 中非法 bool 正则会在错误文本或包装语义变化时失败；`test_memory_plan.py` 继续锁定 reuse 正反例。
- 禁止修改面：未修改 `expectation/`、`.skills`、`agents/standard`。

结论：execute 返工已完成，review 阻断项已收口；下一步按流程续接 review。

## 2026-05-25 04:25 review 复审结论 / 经办人：提莫炖蘑菇

时间：2026-05-25 04:25 CST
经办人：提莫炖蘑菇
任务：T-20260525-a814d111 / memory-plan-reuse-prototype
任务目标：复审 `_parse_bool_option(...)` 不再调用私有 `_raise_memory_plan_error(...)`，以及 memory_plan / registry pytest、py_compile、git diff check、敏感目录门禁和任务记录。

最新同步现场：
- 执行目录：`/home/lfr/kernelcode_generate/wt-20260525-memory-plan-reuse-prototype`
- 已执行：`git fetch origin`，exit=0。
- 基线核对：`HEAD=758b5c62b6ef25f591d35a610484bd23afe44477`，`origin/main=758b5c62b6ef25f591d35a610484bd23afe44477`，`merge-base=758b5c62b6ef25f591d35a610484bd23afe44477`。
- 工作树：任务候选 diff 仍为未提交工作树改动；未发现主线落后、合并冲突或覆盖风险。

被审 diff：
- `kernel_gen/passes/memory_plan.py`：`_parse_bool_option(name, value)` 非法 bool 分支改为直接抛 `KernelCodeError(ErrorKind.CONTRACT, ErrorModule.PASS, f"MemoryPlanOptionError: {name} expects bool")`，不再调用 `_raise_memory_plan_error(...)`。
- 前序候选 diff 仍包括 `MemoryPlanPass(reuse=...)`、registry/spec/test 同步和本任务记录。

Diff 反推审查：
- 已复跑 `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/passes/test_memory_plan.py test/passes/test_registry.py`，exit=0，`81 passed, 1 warning`。
- 已复跑 `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 -m py_compile kernel_gen/passes/memory_plan.py`，exit=0。
- 已复跑 `git diff --check`，exit=0。
- 已复跑敏感目录门禁：
  - `git diff --name-only -- expectation .skills agents/standard`，exit=0，无输出。
  - `git diff --cached --name-only -- expectation .skills agents/standard`，exit=0，无输出。
  - `git status --short --ignored --untracked-files=all -- expectation .skills agents/standard`，exit=0，无输出。
- 已核对 `def _parse_bool_option` 函数体：只读取 `_TRUE_VALUES` / `_FALSE_VALUES`，非法 bool 直接抛 `KernelCodeError`，不再调用 `_raise_memory_plan_error(...)`。
- 已执行 diff 级静态扫描：`git diff -U0 -- kernel_gen/passes/memory_plan.py test/passes/test_memory_plan.py test/passes/test_registry.py | rg -n "hasattr\\(|getattr\\(|callable\\(getattr|def .+def |object|_raise_memory_plan_error\\(" || true`；未发现本轮新增 ctx 能力探测、嵌套函数、`object` 签名或 `_parse_bool_option(...)` 调 `_raise_memory_plan_error(...)`。命中仅为保留的 `from_options(...)` 未知 option 错误出口和删除旧调用的 diff 上下文，不构成本轮阻断。

发现：
- 无阻断项。

减法审查：
- 复审前次阻断项：`_parse_bool_option(name, value)` 已删除对 `_raise_memory_plan_error(...)` 的私有 callable 调用，改为直接抛同等 `KernelCodeError`；错误文本与 registry 包装测试保持通过。
- 本轮未新增 private callable；`_parse_bool_option(...)` 有效代码不少于 5 行，且不再调用其它 private callable。
- 保留 `_raise_memory_plan_error(...)` 作为其它生命周期错误路径统一出口，属于前序存量及其它调用点，不是本轮返工阻断范围。

执行记录核对：
- execute 返工记录包含执行前阅读、返工改动、最小功能闭环、Diff 反推自测、验证、减法检查、自检和结论。
- 测试与 diff 匹配：pytest 覆盖 memory-plan reuse 正反例、`from_options` bool 错误和 registry 包装错误；py_compile / diff check / 敏感目录门禁均已复核。

自检：
- 已读取实际 diff、前序 review 阻断和 execute 返工记录。
- 已核对公开 API、spec/API 列表、测试公开入口、禁止修改面、Diff 反推测试、私有函数审查与敏感目录门禁。
- 当前无剩余可执行返工项。

结论：通过。该任务为普通小任务，可进入 merge。

## 2026-05-25 04:28 merge 收口 / 经办人：李白

时间：2026-05-25 04:28 +0800
经办人：李白
任务：T-20260525-a814d111 / memory-plan-reuse-prototype / merge
任务目标：合入已复审通过的 memory-plan reuse prototype 改动与任务记录。
改动：
- 已重新读取个人提示词、根 `AGENTS.md`、`agents/standard/合并规范.md`、`agents/standard/任务记录约定.md`。
- 已确认本任务为普通小任务，记录链路包含 execute、review、execute 返工与 review 复审通过结论；无计划书与 `archive_acceptance` 要求。
- 最新同步现场：执行目录 `/home/lfr/kernelcode_generate/wt-20260525-memory-plan-reuse-prototype`，`HEAD=origin/main=merge-base=758b5c62b6ef25f591d35a610484bd23afe44477`；主仓 `/home/lfr/kernelcode_generate` 为 `HEAD=origin/main=758b5c62b6ef25f591d35a610484bd23afe44477` 且无 tracked dirty。
- 候选范围复核：`git diff --name-status` 仅包含 `kernel_gen/passes/__init__.py`、`kernel_gen/passes/memory_plan.py`、`kernel_gen/passes/registry.py`、`spec/pass/memory_plan.md`、`spec/pass/registry.md`、`test/passes/test_memory_plan.py`、`test/passes/test_registry.py`；`git ls-files --others --exclude-standard` 仅包含本任务记录。
- 实际合入内容：新增 `MemoryPlanPass(..., reuse: bool = False)` 公开参数与 `from_options`/registry `reuse` bool option；在 `insert_free=True,reuse=True` 下对同 owner block、类型完全一致、生命周期不重叠的 `dma.alloc` 做保守复用；同步 spec、registry 文档、API 列表和现有测试文件。
验证：
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 -m py_compile kernel_gen/passes/memory_plan.py`：exit=0。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q -p no:cacheprovider test/passes/test_memory_plan.py test/passes/test_registry.py`：exit=0，`81 passed, 1 warning`。
- `git diff --check && git diff --cached --check`：exit=0。
- `git diff --name-only -- expectation .skills agents/standard AGENTS.md TODO.md DONE.md ARCHITECTURE/plan`：无输出；`git diff --cached --name-only -- expectation .skills agents/standard AGENTS.md TODO.md DONE.md ARCHITECTURE/plan`：无输出。
- diff 级静态扫描 `git diff -U0 -- kernel_gen/passes/memory_plan.py test/passes/test_memory_plan.py test/passes/test_registry.py | rg ...`：仅命中 `from_options(...)` 未知 option 分支新增 `_raise_memory_plan_error(...)` 调用；该路径位于公开 `from_options` 内，不是 `_parse_bool_option` 私有 callable 调私有 callable。
- `_parse_bool_option(name, value)` 函数体核对：不再调用 `_raise_memory_plan_error(...)`，非法 bool 直接抛同等 `KernelCodeError(ErrorKind.CONTRACT, ErrorModule.PASS, f"MemoryPlanOptionError: {name} expects bool")`。
- AST 扫描：`kernel_gen/passes/memory_plan.py`、`test/passes/test_memory_plan.py` 无嵌套函数；`test/passes/test_registry.py` 存量测试内嵌类/函数存在，非本轮新增阻断。
结论：
- 复审阻断项已收口，候选范围与任务记录对应，敏感目录无未授权 diff；可提交、推送、执行 `-done` 并清理完成 worktree/branch。
