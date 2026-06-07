# dsl_run runtime args alignment 计划书 Draft 4

## 文档信息

- 计划用途：把 `dsl_run(...)` 的真实运行参数基础分类收敛到 `kernel_gen.execute_engine.runtime_args`，使 `dsl_run(...)` 与 `CompiledKernel.execute(...)` 对 `torch.Tensor`、`numpy.ndarray`、`int`、`float`、numpy scalar、`bool` 与 `None` 的基础处理口径一致，并移除 `dsl_run.py` 中重复维护的 tensor / dtype / shape / stride / scalar 判定逻辑。
- 当前状态：Draft 4；已吸收 Aristotle / Averroes 对 Draft 1 的 strict review 最小需改项，补齐 numpy scalar 的 `RuntimeInput` 口径、`RuntimeArgInfo` 精确别名、dtype alias 表、`tile_*` bool 唯一错误语义、`dsl_cost_run` / 包根验收、memory value-driven 边界、通用 `[immutable]` / `[immutable-file]` 禁止修改面和历史只读 expectation 说明；第二轮 strict review 复审与第三轮轻量复核均通过，守护最终检验复检通过；无阻断、无最小需改项、无待确认项；可由管理员按下发依赖创建 / 下发唯一计划级 `execute`。
- 计划文件位置：`ARCHITECTURE/plan/dsl_run_runtime_args_alignment.md`。
- 计划任务名建议：`dsl-run-runtime-args-alignment`。
- 计划级任务类型：唯一计划级 `execute`。
- 建议 worktree：`/home/lfr/kernelcode_generate/wt-20260608-dsl-run-runtime-args-alignment`。
- 建议记录文件：`agents/codex-multi-agents/log/task_records/2026/24/20260608-dsl-run-runtime-args-alignment.md`。
- 固定流转：`execute -> review -> archive_acceptance / 计划书入档验收 -> merge / 归档`。
- 下发依赖：
  - 默认等待 `T-20260608-cdc4c6f4 / dump_diagnostics_writer_refactor` 完成入档验收、合并并同步到 latest main 后再下发，避免与 `kernel_gen/tools/dsl_run.py` 的 dump 写出链路产生并行覆盖。
  - 本计划不依赖 `T-20260608-bfe97ae7 / cuda_sm86_api_aligned_kernel_codegen`，也不得混入 CUDA SM86 execute。
  - 若下发时 `T-20260607-0c4db1f1 / multi_buffer_loop_staging_ring` 尚未合并，管理员应再次核对该任务是否触碰 `dsl_run.py`、`runtime_args.py`、`test/tools/test_dsl_run.py` 或 execute_engine 测试；存在同文件并行覆盖风险时，必须等其合并并同步后再分发。
- 目标 `spec`：
  - `spec/execute_engine/execute_engine.md`
  - `spec/execute_engine/execute_engine_api.md`
  - `spec/execute_engine/strategy.md`
  - `spec/tools/dsl_run.md`
  - `spec/tools/dsl_cost_run.md`
- 目标公开 `API`：
  - `kernel_gen.execute_engine.runtime_args.RuntimeScalarArgInfo`
  - `kernel_gen.execute_engine.runtime_args.RuntimeMemoryArgInfo`
  - `kernel_gen.execute_engine.runtime_args.RuntimeArgInfo`
  - `kernel_gen.execute_engine.runtime_args.describe_runtime_arg(value: object) -> RuntimeArgInfo | None`
  - 修订 `kernel_gen.execute_engine.runtime_args.RuntimeInput` 文档类型定义，使 execute 公开 runtime scalar 覆盖 Python / numpy integer scalar 与 Python / numpy floating scalar；执行前规整为 Python `int` / `float`。
  - 保持 `kernel_gen.execute_engine` 包根 `__all__` 不新增这些文件级 API。
- 目标 `test`：
  - `test/execute_engine/test_contract.py`
  - `test/execute_engine/test_invoke.py`
  - `test/tools/test_dsl_run.py`
  - `test/tools/test_dsl_cost_run.py`
  - `test/tools/test_package.py`
  - `test/repo_conformance/test_private_api_boundaries.py`
  - `test/tools/test_kernel_code_error_static_gate.py`
- 目标 `功能实现`：
  - `kernel_gen/execute_engine/runtime_args.py`
  - `kernel_gen/tools/dsl_run.py`
  - `kernel_gen/tools/__init__.py`
- 目标验收资产：
  - `pytest -q test/execute_engine/test_contract.py test/execute_engine/test_invoke.py test/tools/test_dsl_run.py test/tools/test_dsl_cost_run.py test/tools/test_package.py`
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/repo_conformance/test_private_api_boundaries.py test/tools/test_kernel_code_error_static_gate.py`
  - 当前无必过 `expectation`；`expectation/tools/dsl_run/**` 与 `expectation/tools/dsl_cost_run/**` 是 immutable 历史 / 本地只读合同来源，不作为当前必过验收入口；本计划不授权修改、移动、重命名、新建或删除 `expectation/`。
- 用户确认来源：
  - 2026-06-08 用户指出 `dsl_run(...)` 内部调用 execute_engine，因此两者 runtime args 基础处理应一致。
  - 2026-06-08 用户确认 `dsl_run(...)` 应支持普通 `float` scalar，当前拒绝 `float` 是长期偏移。
  - 2026-06-08 用户确认 `runtime_args.py` 就是处理 runtime args 逻辑的真源。
  - 2026-06-08 用户确认公开 API 收口为 `describe_runtime_arg(...)` 主入口，调用方不应再自行判断原始 `value` 类型。
  - 2026-06-08 用户确认 `RuntimeMemoryArgInfo.dtype` 可以统一使用 `NumericType`。
  - 2026-06-08 用户确认“加了类型支持就加”，本计划据此把 numpy integer / floating scalar 纳入 execute 公开 `RuntimeInput` 的 runtime scalar 范围，并由 `describe_runtime_arg(...)` 规整为 Python `int` / `float`。

## 计划级任务

| 计划任务 | 任务类型 | worktree | 记录文件 | 流转 |
| --- | --- | --- | --- | --- |
| `dsl-run-runtime-args-alignment` | 唯一计划级 `execute` | `/home/lfr/kernelcode_generate/wt-20260608-dsl-run-runtime-args-alignment` | `agents/codex-multi-agents/log/task_records/2026/24/20260608-dsl-run-runtime-args-alignment.md` | `execute -> review -> archive_acceptance -> merge/归档` |

任务目标：为 `kernel_gen.execute_engine.runtime_args` 新增文件级公开 `describe_runtime_arg(value: object) -> RuntimeArgInfo | None` 及配套 info 类型，把 runtime 参数基础分类、dtype/shape/stride/contiguous 元数据提取收敛为单一真源；同步 `dsl_run(...)` 的公开合同，支持普通 `float` runtime scalar，保持 `bool` 拒绝与 `tile_*` 仅接受正整数，并用 pytest 和静态门禁证明 `dsl_run.py` 与 execute ABI 不再重复维护基础 runtime arg 分类逻辑。

计划级边界：
- 一个计划书只创建一个计划级 `execute`；S1-S5 是计划内小任务卡，不创建独立 TODO。
- `execute` 必须一次完成本计划内 spec、实现、测试、验收和记录闭环。
- 本计划涉及公开 API 新增和 `dsl_run(...)` 公开错误语义修正，必须保留用户确认来源；若 execute 发现仍需新增其它公开 API、修改包根导出、变更工具入口参数或新增稳定错误短语，必须暂停并回用户确认。
- 本计划不修改 `.skills/`、`agents/standard/`、`AGENTS.md`、`TODO.md`、`DONE.md`。
- 本计划不得修改带 `[immutable]` / `[immutable-file]` 标记的文件或内容；无额外授权不得触碰。
- 本计划不修改 `expectation/`；相关 expectation 不列为当前必过验收。

## 迭代审阅记录

### 收敛轮次 1：subagent strict review

- 审阅对象：
  - `Aristotle` / agent `019ea343-1d6c-76a0-a37d-a53cd30f2ac7` / 公开 API 与 spec 边界 strict review。
  - `Averroes` / agent `019ea343-1da7-77d2-9c7b-1a46e8850765` / 执行可落地性、测试覆盖与私有 API 风险 strict review。
- 输入标准包：根 `AGENTS.md`、当前角色 prompt、`agents/standard/计划书标准.md`、`agents/standard/计划书模板.md`、`agents/standard/spec文件规范.md`、`agents/standard/实现文件规范.md`、`agents/standard/审查规范.md`、本 Draft 1 全文、用户确认来源、禁止修改面、必过验收命令。
- 严格通过口径：公开 API 变更必须有用户确认来源；`describe_runtime_arg(...)` API 必须足够小且不把 execute ABI 私有细节暴露给 `dsl_run`；小任务卡必须可执行；pytest / conformance / expectation 验收必须分层；仍有可执行可读性、可维护性或测试有效性改进项则不通过。
- 发现问题：
  - `Aristotle` 结论不通过：numpy scalar 是否进入 execute 公开 `RuntimeInput` 口径不清；`RuntimeArgInfo` 精确别名和 `value: object` 确认不足；`NumericType` dtype alias / ABI code 映射未列全；`tile_*` bool 错误语义冲突；`dsl_cost_run(...)` 验收缺 `test_tools/test_dsl_cost_run.py`；历史 `expectation/tools/dsl_run` 需写明只读口径。
  - `Averroes` 结论最小需改项：`dsl_cost_run(...)`、`spec/tools/dsl_cost_run.md`、`kernel_gen/tools/__init__.py`、`test/tools/test_dsl_cost_run.py`、`test/tools/test_package.py` 未纳入目标与验收；`tile_*` bool 错误语义冲突；`RuntimeArgInfo` 精确别名、`object` 宽入口和 `DslRunUnsupportedRealArg` 最终文本未钉死。
- 主线处理：采纳。Draft 2 明确 numpy scalar 纳入 execute 公开 `RuntimeInput` 的 runtime scalar 范围；补 `RuntimeArgInfo: TypeAlias = RuntimeScalarArgInfo | RuntimeMemoryArgInfo`；把 `value: object` 写成用户确认的唯一宽分类入口；新增 dtype alias / ABI code 表；固定 `tile_*` bool / numpy bool / float / 非正 int 均走 `DslRunInvalidTileValue`，非 `tile_*` bool 走 `DslRunUnsupportedRealArg`；固定 `DslRunUnsupportedRealArg: real_args only supports torch.Tensor, numpy.ndarray, integer scalar, float scalar and None for memory`；纳入 `spec/tools/dsl_cost_run.md`、`kernel_gen/tools/__init__.py`、`test/tools/test_dsl_cost_run.py`、`test/tools/test_package.py`；把 `expectation/tools/dsl_run/**` 与 `expectation/tools/dsl_cost_run/**` 写为 immutable 历史 / 本地只读来源，不列当前必过入口。
- 状态：已修订为 Draft 2；复审结论见收敛轮次 2。

### 收敛轮次 2：subagent strict review 复审

- 审阅对象：
  - `Aristotle` / agent `019ea343-1d6c-76a0-a37d-a53cd30f2ac7` / 公开 API 与 spec 边界 strict review 复审。
  - `Averroes` / agent `019ea343-1da7-77d2-9c7b-1a46e8850765` / 执行可落地性、测试覆盖与私有 API 风险 strict review 复审。
- 输入标准包：根 `AGENTS.md`、当前角色 prompt、相关 `agents/standard/**`、Draft 2 / 当时最新正文、上一轮 Aristotle / Averroes 问题、本轮收口摘要、用户确认项、禁止修改面、必过验收命令、每张小任务卡的当前必过 `expectation` 单列口径。
- 严格通过口径：确认 Draft 1 所有问题已收口，且最新计划无阻断、无最小需改项、无待确认项；若公开 API、验收资产、任务范围或 expectation 只读口径仍不闭合，则不通过。
- 发现问题：
  - `Aristotle` 结论 PASS：无阻断、无最小需改项、无待用户确认项；确认公开 API 变更来源、`RuntimeInput` 的 numpy integer / floating scalar 口径、`RuntimeArgInfo` 精确别名、`value: object` 宽入口、`NumericType` dtype 映射、`tile_*` bool / float 错误优先级、包根导出边界和 `expectation` 只读口径均已写清。
  - `Averroes` 结论 PASS：无阻断、无最小需改项、无待用户确认项；确认 `dsl_cost_run`、`spec/tools/dsl_cost_run.md`、`kernel_gen/tools/__init__.py`、`test/tools/test_dsl_cost_run.py`、`test/tools/test_package.py` 已纳入，`DslRunUnsupportedRealArg` 文本、memory value-driven 规则和 `expectation` 只读口径已闭合。
- 主线处理：无必须修订项。采纳 Averroes 可选建议，把 `dsl_cost_run` float / numpy floating 测试写成必须证明 real_args 参数校验已通过，后续即使因 cost sibling 现有合同失败，也不得误判为仍被 `dsl_run` 绑定层拒绝。
- 状态：复审通过；无阻断、无最小需改项、无待确认项。

### 收敛轮次 3：subagent strict review 轻量复核

- 审阅对象：
  - `Aristotle` / agent `019ea343-1d6c-76a0-a37d-a53cd30f2ac7` / Draft 3 公开 API 与 spec 边界轻量复核。
  - `Averroes` / agent `019ea343-1da7-77d2-9c7b-1a46e8850765` / Draft 3 执行可落地性、测试覆盖与私有 API 风险轻量复核。
- 输入标准包：根 `AGENTS.md`、当前角色 prompt、最新 Draft 3 正文、第二轮 PASS 结果、Draft 3 变化摘要、用户确认项、禁止修改面、必过验收命令。
- 严格通过口径：确认 Draft 3 仅回填第二轮复审记录、吸收 `dsl_cost_run` 测试有效性建议并清理历史状态措辞，未扩大公开 API、任务范围、验收命令或 `expectation` 授权；最新计划仍无阻断、无最小需改项、无待确认项。
- 发现问题：
  - `Averroes` 结论 PASS：无阻断、无最小需改项、无待用户确认项；确认第二轮复审记录与 subagent 收敛结论已回填，`dsl_cost_run` float / numpy floating 测试已明确要求证明 real_args 绑定层放行，公开 API、任务范围、验收命令、禁止修改面和 `expectation` 只读授权未扩大。
  - `Aristotle` 结论 PASS：无阻断、无最小需改项、无待用户确认项；确认 Draft 3 已补齐第二轮复审记录、subagent 收敛结论和 S1-S5 的 `expectation` 只读 / 不适用口径，`dsl_cost_run` 测试要求属于测试有效性加强，未扩大公开 API、任务范围或 `expectation` 授权。
- 主线处理：无必须修订项；无新的可执行建议。
- 状态：轻量复核通过；无阻断、无最小需改项、无待确认项。

### subagent 收敛结论

- 已发起或计划要求的审阅任务：
  - `Aristotle` / `019ea343-1d6c-76a0-a37d-a53cd30f2ac7`：Round 1 不通过，Round 2 复审 PASS，Round 3 轻量复核 PASS。
  - `Averroes` / `019ea343-1da7-77d2-9c7b-1a46e8850765`：Round 1 有最小需改项，Round 2 复审 PASS，Round 3 轻量复核 PASS。
- 收敛结论：所有已发起或计划要求的 subagent strict review 均无阻断、无最小需改项、无待确认项；可进入守护最终检验。
- 遗留项：无阻断遗留项；Averroes 的测试表达建议已吸收到 S3 / 验收设计。

### 守护最终检验

- 检验对象：`守护最好的爱莉希雅`。
- 检验范围：标准包、公开 API、用户确认来源、`expectation` 权限、禁止修改面、验收命令、小任务卡、subagent 收敛结论。
- 必过门禁：所有 subagent strict review 无阻断、无最小需改项、无待确认项；用户待决策项已收口；敏感目录无越权；验收命令和任务目标可直接执行。
- 初检结论：FAIL；最小需改项为计划级边界、S1-S5 `禁止修改面` 和 S5 敏感目录门禁 / 记录要求缺少通用 `[immutable]` / `[immutable-file]` 保护口径。
- 主线处理：采纳并修订。计划级边界补入不得修改带 `[immutable]` / `[immutable-file]` 标记的文件或内容；S1-S5 禁止修改面全部补入该口径；S5 验收、执行步骤和记录要求补入无越权核对与记录要求。该修订未改变公开 API、任务范围、验收命令或 `expectation` 授权。
- 复检结论：PASS；公开 API 与用户确认来源闭合，`expectation/` 仍仅作为历史 / 本地只读来源且不列当前必过入口，验收命令覆盖 execute_engine、`dsl_run`、`dsl_cost_run`、包根导出、private API 与工具错误静态门禁，subagent 收敛结论无阻断、无最小需改项、无待确认项。
- 最小阻断项：无。
- 待用户确认项：无。

## 计划书入档验收 / 复验 / 修复复核记录

- 结论人：`提莫炖蘑菇`。
- 结论：`archive_acceptance` 通过；review 结论为通过，无阻断、无最小需改项；可按计划级链路续接 `merge / 归档`，不得跳过合并记录与计划归档同批合入要求。
- 验证基线：`HEAD=b10ded364fb5b4714964faa4ca0cfb9c7cce8f62`，`origin/main=1475a42c3eedd17c52153c7b4a58e1f41d44959f`，`merge-base=b10ded364fb5b4714964faa4ca0cfb9c7cce8f62`，`HEAD...origin/main=0 1`。
- 执行目录：`/home/lfr/kernelcode_generate/wt-20260608-dsl-run-runtime-args-alignment`。
- 同步结果：latest main 仅领先 1 个 multi-buffer 相关提交；`git diff --name-only HEAD..origin/main -- <本计划目标文件>` 无输出，未发现覆盖本计划候选 diff 的同步风险。
- 合同验收摘要：当前无必过 `expectation`；`expectation/tools/dsl_run/**` 与 `expectation/tools/dsl_cost_run/**` 只作为历史 / 本地只读来源，未运行为当前必过入口且未修改。已复跑 `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/execute_engine/test_contract.py test/execute_engine/test_invoke.py test/tools/test_dsl_run.py test/tools/test_dsl_cost_run.py test/tools/test_package.py`，结果 `109 passed, 1 warning in 208.31s`；已复跑 `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/repo_conformance/test_private_api_boundaries.py test/tools/test_kernel_code_error_static_gate.py`，结果 `7 passed in 3.32s`；`py_compile`、`git diff --check`、`git diff --cached --check`、敏感目录 diff/status 均通过。
- 最小阻断项或通过摘要：无阻断项；无最小需改项。计划书入档验收确认公开 API、spec、实现、测试、任务记录、Diff 反推审查、减法审查和禁止修改面记录齐全，可进入 merge。

## 计划目标

- 新增 `runtime_args.py` 文件级公开 runtime arg 描述 API，让调用方通过 `describe_runtime_arg(...)` 获得 `kind`、规整后的 scalar 值、`NumericType` dtype、shape、元素 stride 和 contiguous 事实。
- `dsl_run(...)` 与 `dsl_cost_run(...)` 的 runtime 参数基础类型域与 `CompiledKernel.execute(...)` 对齐：接受 `torch.Tensor`、`numpy.ndarray`、Python / numpy integer scalar、Python / numpy floating scalar 和合法 memory absent `None`；继续拒绝 `bool` 与 numpy bool scalar。
- `dsl_run(...)` 保留 DSL 专属绑定规则：`Tensor[...]` 形参只能绑定 memory 或合法 memory absent `None`；`tile_*` runtime scalar 必须是正整数；普通 float scalar 只能用于非 `tile_*`、非 Tensor 形参。
- 删除或收敛 `dsl_run.py` 中重复的 `_runtime_module_name(...)`、`_is_torch_tensor(...)`、`_is_numpy_array(...)`、`_runtime_arg_shape(...)`、`_runtime_arg_stride(...)`、`_runtime_arg_dtype(...)` 基础判定逻辑，避免与 execute ABI 侧继续漂移。
- 保持 `runtime_args.py` 的 `_ArgSlot`、`_CArgSlot`、ctypes marshal、data pointer、entry loading 和 allow-absent ABI 处理为当前文件内部细节，不暴露给 `dsl_run.py`。

## 当前基线

- `kernel_gen/execute_engine/runtime_args.py` 当前文件级 API 只有 `AllowAbsentMemoryArg`、`RuntimeInput`、`invoke_compiled_kernel(...)`；基础分类逻辑散落在 `_RuntimeArgSupport` 内部，不允许 `dsl_run.py` 跨文件调用。
- `kernel_gen/tools/dsl_run.py` 当前自己维护 torch/numpy 判断、shape/stride/dtype 提取、numpy integer 规整和 `float` 拒绝逻辑。
- `spec/tools/dsl_run.md` 当前明确写死 `float` 必须拒绝，`RuntimeRealArg` 只表示 `torch.Tensor | numpy.ndarray | int | None`。
- `spec/tools/dsl_cost_run.md` 当前把 `real_args` 校验规则指向 `dsl_run(...)`，因此 `dsl_run(...)` 的 runtime arg 合同修订必须同步覆盖 `dsl_cost_run(...)` 的 spec、实现、测试和包根转发类型。
- `test/tools/test_dsl_run.py` 当前包含 `test_dsl_run_rejects_float_runtime_scalar`，锁定了错误合同。
- `test/tools/test_dsl_cost_run.py` 当前只覆盖 `numpy.ndarray` 与 `torch.Tensor` 混用参数，未覆盖普通 float scalar 或 numpy floating scalar。
- `spec/execute_engine/execute_engine_api.md` 已说明 execute runtime args 允许 `int` / `float` 标量和 memory 参数，元素 `None` 仅用于 allow-absent memory。
- `kernel_gen/dsl/ast/mlir_gen.py` 的 `DslRuntimeArg` 已包含 `float`，`FunctionAST.input_from_runtime_arg(...)` 也支持 `float`，说明 DSL AST 层可以承接 float runtime scalar。
- `kernel_gen/tools/__init__.py` 当前 `RuntimeRealArg` 文档类型只写 `TensorRuntimeArg | int`，包根 `dsl_run(...)` / `dsl_cost_run(...)` 的类型说明已落后于本计划目标。
- `kernel_gen.symbol_variable.type.NumericType` 是仓库已有公开 dtype 枚举，包含 `Int8`、`Int16`、`Int32`、`Int64`、`Uint8`、`Uint16`、`Uint32`、`Uint64`、`Float16`、`BFloat16`、`Float32`、`Float64`、`Bool`。
- 当前 `test/execute_engine/test_contract.py` 明确锁定 `kernel_gen.execute_engine` 包根不导出 `AllowAbsentMemoryArg`、`RuntimeInput`、`invoke_compiled_kernel` 等 runtime_args 文件级 API；本计划不得破坏该包根边界。
- `expectation/tools/dsl_run/add.py`、`expectation/tools/dsl_run/invalid_contract.py`、`expectation/tools/dsl_cost_run/invalid_contract.py` 均带 `[immutable-file]` 标记或位于 `expectation/` 下；本计划无授权修改，只能作为历史 / 本地只读来源说明，不列当前必过验收入口。

## 方案比较与选型

### 不采用 A：让 `dsl_run.py` 直接导入 `_RuntimeArgSupport`

- 问题：`_RuntimeArgSupport` 不在文件级 API 列表和 `__all__` 中，跨文件导入会违反公开 API 边界。
- 问题：`_RuntimeArgSupport` 混合了 runtime arg 基础分类、C ABI slot、ctypes marshal、data pointer 和 entry loading；直接暴露会把 DSL 工具层耦合到 execute ABI 私有细节。
- 结论：不采用。

### 不采用 B：在 `dsl_run.py` 继续复制并补 float 支持

- 问题：短期能修 `float`，但 torch/numpy dtype、stride、contiguous、numpy scalar 和 bfloat16 规则仍会在两处漂移。
- 问题：后续新增 runtime arg 类型时仍需多处改动，测试难以证明一致。
- 结论：不采用。

### 不采用 C：新建独立 `kernel_gen/runtime/arg_metadata.py`

- 优点：可以让 metadata 层看起来更中立。
- 问题：用户已确认 `runtime_args.py` 就是 runtime args 真源；新增第三处 runtime 模块会增加命名和所有权成本。
- 问题：execute ABI 仍在 `runtime_args.py` 内，第三处模块会引入额外 import / spec 边界。
- 结论：不采用。

### 采用 D：扩展 `runtime_args.py` 文件级公开 API

- 在 `runtime_args.py` 内新增 `RuntimeScalarArgInfo`、`RuntimeMemoryArgInfo`、`RuntimeArgInfo` 和 `describe_runtime_arg(...)`。
- `describe_runtime_arg(...)` 只描述真实参数事实，不抛 `DslRun...` 或 `runtime_throw_or_abort`，失败返回 `None`。
- `dsl_run.py` 使用该公开 API 做基础分类，再应用 DSL 专属绑定规则。
- execute ABI 内部也使用该公开 API 生成 `_ArgSlot`，但 `_ArgSlot`、ctypes marshal、data pointer、entry loading 继续私有。
- `describe_runtime_arg(...)` 不为了识别 torch / numpy 对象而直接导入 torch 或 numpy；memory 参数继续使用模块名前缀、shape/dtype/stride/flags 等公开属性轻量识别，numpy scalar 可通过标准数值抽象或无硬依赖策略处理。
- 结论：采用。

## 公开 API 设计

### 功能简介

`kernel_gen.execute_engine.runtime_args` 提供 runtime arg 基础描述 API。该 API 是文件级公开 API，不进入 `kernel_gen.execute_engine` 包根导出；调用方通过 `describe_runtime_arg(...)` 获得明确的 scalar 或 memory 信息，避免跨文件依赖 execute ABI 私有 helper。

### API 列表

- `class RuntimeScalarArgInfo(kind: Literal["int", "float"], value: int | float)`
- `class RuntimeMemoryArgInfo(kind: Literal["memory"], dtype: NumericType, shape: tuple[int, ...], stride: tuple[int, ...] | None, is_contiguous: bool)`
- `RuntimeArgInfo: TypeAlias = RuntimeScalarArgInfo | RuntimeMemoryArgInfo`
- `describe_runtime_arg(value: object) -> RuntimeArgInfo | None`
- 保持不变：`class AllowAbsentMemoryArg(index: int, dtype: str, rank: int)`
- 修订定义：`RuntimeInput: TypeAlias` 表示 memory runtime input、Python / numpy integer scalar、Python / numpy floating scalar 或 `None`；实现可用标准数值抽象表达该范围，不因类型标注直接导入 numpy。
- 保持不变：`invoke_compiled_kernel(soname_path: str, entry_point: str, args: tuple[RuntimeInput, ...], allow_absent_memory_args: tuple[AllowAbsentMemoryArg, ...]) -> int`

### `RuntimeScalarArgInfo`

- `kind` 只允许 `"int"` 或 `"float"`。
- `value` 是规整后的 Python `int` 或 Python `float`。
- Python `bool` 和 numpy bool scalar 不产生 `RuntimeScalarArgInfo`。

### `RuntimeMemoryArgInfo`

- `kind` 固定为 `"memory"`。
- `dtype` 使用 `NumericType`，不使用字符串作为公开 dtype 真源。
- `shape` 是按维度规整后的 `tuple[int, ...]`。
- `stride` 是元素单位 stride；无法取得 stride 时为 `None`。
- `is_contiguous` 是运行时对象报告的连续性事实；该 API 不因 `False` 抛错，execute ABI 是否拒绝由 `invoke_compiled_kernel(...)` 内部规则处理。

### `describe_runtime_arg(value: object) -> RuntimeArgInfo | None`

- 用户确认来源：2026-06-08 用户确认调用方应只使用 `describe_runtime_arg(...)`，不再先自行判断 `value` 类型。
- `value: object` 是本计划唯一确认的宽类型公开入口，原因是该 API 的职责就是对未知 runtime object 做分类并以 `RuntimeArgInfo | None` 收口；其它新增 / 修改函数不得用 `object` 掩盖可枚举输入。
- 参数：
  - `value`：待描述的真实运行时参数；类型写作 `object` 是本 API 的公开分类入口语义，调用方可以传入未知对象并通过 `None` 判断不支持；有效输出范围仍由 `RuntimeArgInfo` 枚举收口。
- 返回值：
  - Python `int` 与 numpy integer scalar 返回 `RuntimeScalarArgInfo(kind="int", value=int(value))`。
  - Python `float` 与 numpy floating scalar 返回 `RuntimeScalarArgInfo(kind="float", value=float(value))`。
  - torch / numpy memory 参数返回 `RuntimeMemoryArgInfo(kind="memory", dtype=<NumericType>, shape=<tuple>, stride=<tuple | None>, is_contiguous=<bool>)`。
  - `bool`、numpy bool scalar、`None`、缺少 shape/dtype 的对象、dtype 不可映射到 `NumericType` 的 memory 对象、无法解析 shape 的对象和不支持对象返回 `None`。
- 注意事项：
  - `None` 合法性不由本 API 决定；`dsl_run(...)` 需要看 `Tensor[...]` 注解，execute ABI 需要看 `AllowAbsentMemoryArg`。
  - 本 API 不返回 data pointer，不分配 ctypes buffer，不读取或加载 entry symbol，不构造 `_ArgSlot`。
  - 本 API 不抛 tools 层稳定错误文本，也不直接抛 execute failure phrase；调用方负责把 `None` 或不满足上下文规则的 `RuntimeArgInfo` 转成自身公开错误语义。

### dtype normalization 与 ABI code

`RuntimeMemoryArgInfo.dtype` 使用 `NumericType`。`describe_runtime_arg(...)` 必须把 runtime dtype 文本规整为小写、去空格、去 `torch.` 前缀，再按下表映射；不在表中的 memory dtype 返回 `None`。execute ABI 的 dtype code 仍是内部 C ABI 细节，不进入 `RuntimeMemoryArgInfo`。

| runtime dtype 文本 | `RuntimeMemoryArgInfo.dtype` | execute ABI dtype code |
| --- | --- | --- |
| `int8`, `i8` | `NumericType.Int8` | `0` |
| `int16`, `i16` | `NumericType.Int16` | `0` |
| `int`, `int32`, `int32_t`, `i32` | `NumericType.Int32` | `3` |
| `longlong`, `longlongint`, `long long`, `int64`, `int64_t`, `i64` | `NumericType.Int64` | `4` |
| `uint8`, `ui8` | `NumericType.Uint8` | `0` |
| `uint16`, `ui16` | `NumericType.Uint16` | `0` |
| `uint32`, `uint32_t`, `ui32` | `NumericType.Uint32` | `0` |
| `uint64`, `uint64_t`, `ui64` | `NumericType.Uint64` | `0` |
| `float16`, `f16`, `half` | `NumericType.Float16` | `0` |
| `bfloat16`, `bf16` | `NumericType.BFloat16` | `0` |
| `float`, `float32`, `f32` | `NumericType.Float32` | `1` |
| `double`, `float64`, `f64` | `NumericType.Float64` | `2` |
| `bool` | `NumericType.Bool` | `0` |

补充规则：
- `AllowAbsentMemoryArg.dtype` 继续是源码 metadata 的字符串，仍由 execute ABI 内部按 `float`、`double`、`int32_t`、`int64_t`、`int`、`long long` 等当前公开源码类型名映射 dtype code；本计划不把 `AllowAbsentMemoryArg.dtype` 改成 `NumericType`。
- ABI dtype code 为 `0` 表示当前 C shim 不能据此选择模板实例；是否执行失败由现有 execute ABI / generated source 规则决定，不由 `describe_runtime_arg(...)` 直接抛错。

### 包根导出边界

- `kernel_gen.execute_engine.__all__` 保持不变。
- 新 API 只通过 `from kernel_gen.execute_engine.runtime_args import describe_runtime_arg, RuntimeArgInfo, RuntimeScalarArgInfo, RuntimeMemoryArgInfo` 使用。
- `test_execute_engine_public_api_exports_only_runtime_contract` 必须继续证明包根不暴露 runtime_args 文件级 API。

## dsl_run 绑定逻辑

`dsl_run(...)` 与 `dsl_cost_run(...)` 的参数处理分两层：

1. 容器规整：`real_args` 只接受 `tuple` 或 `list`，规整成 `tuple`。其它容器继续以 `DslRunInvalidRealArgs: real_args must be tuple or list` 失败。
2. 形参绑定：按 DSL 函数位置形参与 runtime arg 一一对应，使用 `describe_runtime_arg(...)` 获得基础信息，再应用 DSL 专属规则。

绑定规则：
- arity 不匹配继续以 `DslRunArityMismatch: real_args count does not match function signature` 失败。
- 非法真实参数的稳定错误文本固定为 `DslRunUnsupportedRealArg: real_args only supports torch.Tensor, numpy.ndarray, integer scalar, float scalar and None for memory`。
- Tensor 形参收到非 memory / 非合法 absent `None` 时，继续使用 tensor-only 文本 `DslRunUnsupportedRealArg: real_args only supports torch.Tensor and numpy.ndarray`。
- `arg is None` 时：
  - 只有 `Tensor[...]` 形参可接受。
  - `dsl_args` 使用 `Tensor[...]` 注解构造 nominal `Memory`。
  - `execute_args` 保留 `None`，由 execute ABI 的 allow-absent metadata 决定是否可执行。
- `RuntimeScalarArgInfo` 时：
  - `Tensor[...]` 形参必须失败，错误短语为 `DslRunUnsupportedRealArg` 的 tensor-only 版本。
  - `tile_*` 形参只接受 `kind == "int"` 且 `value > 0`；`float`、`0`、负数、Python bool 和 numpy bool scalar 必须以 `DslRunInvalidTileValue: tile runtime scalar must be positive int` 失败。
  - 非 `tile_*`、非 Tensor 形参接受 `int` 或 `float`，`dsl_args` 与 `execute_args` 都使用规整后的 Python scalar。
- `RuntimeMemoryArgInfo` 时：
  - 真实 torch / numpy memory 参数按 runtime value 构造 `Memory`；不得新增“memory 必须绑定 `Tensor[...]` 形参”的公开收紧。
  - `Tensor[...]` 注解用于约束 scalar 不得绑定 tensor 形参，并用于 `None` absent memory 的 nominal `Memory` 构造；真实 memory 参数是否还受 DSL 函数体 / AST 层约束，保持现有公开行为。
  - 若 execute 发现必须拒绝显式非 Tensor 标注的 memory 绑定，属于新增公开错误语义，必须暂停并回用户确认。
  - `dsl_args` 构造 `Memory(info.shape, info.dtype, stride=info.stride)`。
  - `execute_args` 保留原始 torch / numpy 对象。
- `describe_runtime_arg(...) is None` 时：
  - 对非 `tile_*` 形参上的 `bool`、numpy bool scalar、unsupported object、unsupported dtype 或非法 memory metadata 统一按 `DslRunUnsupportedRealArg` 失败。
  - 对 `tile_*` 形参上的 `bool` 或 numpy bool scalar 统一按 `DslRunInvalidTileValue` 失败；`float` 已在 `RuntimeScalarArgInfo(kind="float")` 路径按 `DslRunInvalidTileValue` 失败。

实现提示：
- `prepare_dsl_run_args` 是逻辑名称，不强制新增为私有 helper。执行时必须遵守 `agents/standard/实现文件规范.md` 的 private callable 规则，避免新增小于 5 行的私有 helper，避免新增或改动的 private callable 调用其它 private callable。
- 若 execute 判断把该逻辑做成 `dsl_run.py` 文件级公开 API 才能避免私有 helper 违规，必须暂停并回用户确认；默认不新增 `dsl_run.py` 公开 API。

## 非目标

- 不修改 `kernel_gen.execute_engine` 包根公开 API。
- 不公开 `_RuntimeArgSupport`、`_ArgSlot`、`_CArgSlot`、ctypes marshal、runtime data pointer、entry loading 或 allow-absent map helper。
- 不新增 `kernel_gen/runtime/` 或其它 runtime arg 平行真源。
- 不新增 `dsl_run(...)` 或 `dsl_cost_run(...)` 参数。
- 不新增稳定错误短语；只把 `DslRunUnsupportedRealArg` 文本固定修正为 `DslRunUnsupportedRealArg: real_args only supports torch.Tensor, numpy.ndarray, integer scalar, float scalar and None for memory`。
- 不改变 `mlir_gen(...)`、`CompiledKernel.execute(...)`、`ExecutionEngine.compile(...)` 的签名。
- 不修改 CUDA SM86、multi-buffer ring、dump writer 计划正文或任务状态。
- 不修改 `expectation/`。

## 完成态定义

- `runtime_args.py` 文件级说明和 `__all__` 列出新增 info 类型与 `describe_runtime_arg(...)`。
- `spec/execute_engine/execute_engine_api.md` 和 `spec/execute_engine/strategy.md` 写清 runtime_args 文件级 API，不把它们加入包根导出。
- `spec/tools/dsl_run.md` 改为 `RuntimeRealArg` 支持 `torch.Tensor | numpy.ndarray | int | float | None`，普通 `float` 合法，`bool` 非法，`tile_*` 仍仅接受正整数。
- `dsl_run.py` 不再重复维护 torch/numpy/dtype/shape/stride/scalar 基础分类；基础分类来自 `describe_runtime_arg(...)`。
- execute ABI 的 `_ArgSlot` 构造复用 `describe_runtime_arg(...)`，但 ABI 私有结构不外露。
- 原 `test_dsl_run_rejects_float_runtime_scalar` 被替换为普通 float scalar 正向测试；新增或更新 `tile_*` float 拒绝测试和 numpy floating scalar 规整测试。
- 新增或更新 `tile_* True`、`tile_* numpy bool scalar`、非 `tile_* bool` 测试，锁定 tile 错误与 unsupported 错误的唯一优先级。
- execute_engine 测试覆盖 `describe_runtime_arg(...)` 的 int/float/numpy scalar/bool/memory/unsupported dtype/None 矩阵。
- conformance 和 tools 静态门禁通过。

## 验收设计

- pytest：
  - `pytest -q test/execute_engine/test_contract.py test/execute_engine/test_invoke.py test/tools/test_dsl_run.py test/tools/test_dsl_cost_run.py test/tools/test_package.py`
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/repo_conformance/test_private_api_boundaries.py test/tools/test_kernel_code_error_static_gate.py`
- 当前必过 expectation 合同验收：不适用；本计划未获得修改 `expectation/` 授权，且 runtime args / dsl_run / dsl_cost_run 合同由 spec + pytest 锁定。
- 历史 / 本地只读 expectation 来源说明：`expectation/tools/dsl_run/**` 与 `expectation/tools/dsl_cost_run/**` 位于合同资产目录且含 immutable 文件，本计划只读核对，不作为当前必过入口；若执行中发现其仍锁定旧 `dsl_run` float 拒绝口径，只能记录为历史只读冲突并回架构 / 用户确认，不得修改 expectation 本体。
- 锁定结果：
  - `describe_runtime_arg(1).kind == "int"` 且 value 为 Python `int`。
  - `describe_runtime_arg(1.5).kind == "float"` 且 value 为 Python `float`。
  - numpy integer / floating scalar 分别规整到 Python `int` / `float`。
  - Python bool 与 numpy bool scalar 返回 `None`。
  - torch / numpy memory 返回 `NumericType` dtype、tuple shape、元素单位 stride 和 contiguous 事实。
  - `dsl_run(...)` 普通 float scalar 通过公开路径进入 `mlir_gen(...)` 与 execute args。
  - `dsl_cost_run(...)` 复用同一 real_args 绑定规则，普通 float scalar 和 numpy floating scalar 必须证明已通过 real_args 参数校验；后续按 cost sibling 现有合同继续成功或失败。
  - `dsl_run(...)` 的 `tile_*` float 仍按 `DslRunInvalidTileValue` 失败。
  - `kernel_gen.execute_engine.__all__` 保持不变。
- Diff 反推要求：执行与审查按实际 diff 补充 pytest 或本地脚本；`expectation` 单列为合同验收，不计入 diff 反推测试。

## 计划内小任务

### S1. 更新 runtime_args 公开合同

- 为什么做：`runtime_args.py` 当前只有 ABI 调用入口，无法让 `dsl_run.py` 合法复用基础 runtime arg 分类逻辑。
- 做什么：更新 `spec/execute_engine/execute_engine.md`、`spec/execute_engine/execute_engine_api.md`、`spec/execute_engine/strategy.md` 和 `kernel_gen/execute_engine/runtime_args.py` 文件级说明，定义 `RuntimeScalarArgInfo`、`RuntimeMemoryArgInfo`、`RuntimeArgInfo`、`describe_runtime_arg(...)`，并修订 `RuntimeInput` 文档类型覆盖 numpy integer / floating scalar。
- 不做什么：不改包根 `kernel_gen.execute_engine.__all__`，不公开 ABI slot 或 ctypes 细节。
- 怎么验收：`rg -n "RuntimeScalarArgInfo|RuntimeMemoryArgInfo|RuntimeArgInfo: TypeAlias = RuntimeScalarArgInfo \\| RuntimeMemoryArgInfo|describe_runtime_arg|numpy integer|numpy floating" spec/execute_engine kernel_gen/execute_engine/runtime_args.py` 命中 API 列表与详细说明；`pytest -q test/execute_engine/test_contract.py` 通过且包根导出测试仍锁定不外露。
- 卡住问谁：用户；触发条件是必须新增本计划外公开 API、进入包根导出或修改 `RuntimeInput` 签名。
- 上下文摘要：用户已确认 `runtime_args.py` 是真源，公开 API 收口为 `describe_runtime_arg(...)`。
- 小任务目标：补齐 execute_engine runtime args 文件级公开合同，使调用方可合法复用基础分类结果。
- 非目标：不改 `dsl_run.py` 行为。
- 模块范围：`spec/execute_engine/**`、`kernel_gen/execute_engine/runtime_args.py`、`test/execute_engine/**`。
- 禁止修改面：`expectation/`、带 `[immutable]` / `[immutable-file]` 标记的文件或内容、`.skills/`、`agents/standard/`、`AGENTS.md`、`TODO.md`、`DONE.md`、本计划书。
- 合同真源：`spec/execute_engine/execute_engine_api.md` > `spec/execute_engine/strategy.md` > `kernel_gen/execute_engine/runtime_args.py` 文件级 API 列表 > `test/execute_engine/**`。
- 最小功能闭环：公开 API 文档、实现文件 API 列表和包根导出边界一致。
- 执行步骤：
  1. 在 execute_engine spec 中新增 runtime arg info API 说明和包根不导出边界。
  2. 更新 `runtime_args.py` 文件级说明、`__all__` 和相关 import。
  3. 更新 execute_engine contract 测试，证明文件级 API 可导入且包根仍不导出。
- 验收必过项目：`pytest -q test/execute_engine/test_contract.py`。
- 当前必过 expectation 合同验收：不适用；本卡不列 `expectation/` 为必跑入口。
- 记录要求：写清新增公开 API、用户确认来源、包根不导出证明和未改 expectation 证明。

### S2. 实现 describe_runtime_arg 真源

- 为什么做：当前基础分类规则散落在 execute ABI 内部和 `dsl_run.py`，新增类型支持会继续漂移。
- 做什么：在 `runtime_args.py` 实现 `describe_runtime_arg(...)`，覆盖 Python / numpy scalar、memory、dtype 到 `NumericType`、shape、元素 stride、contiguous 事实和 unsupported 返回 `None`；让 ABI slot 构造复用该 API。
- 不做什么：不暴露 `_RuntimeArgSupport`、不返回 data pointer、不封送 ctypes、不加载 entry。
- 怎么验收：`pytest -q test/execute_engine/test_invoke.py` 覆盖 runtime arg info 矩阵和 execute ABI 复用路径；`PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/repo_conformance/test_private_api_boundaries.py` 通过。
- 卡住问谁：用户；触发条件是需要支持 `NumericType` 以外 dtype、改变 execute failure phrase 或让 unsupported dtype 继续进入 ABI slot。
- 上下文摘要：`NumericType` 是公开 dtype 真源，`describe_runtime_arg(...)` 失败只返回 `None`。
- 小任务目标：实现 `describe_runtime_arg(...)` 并让 execute ABI 使用同一分类结果构造 `_ArgSlot`，numpy scalar 进入 ABI 前必须规整为 Python `int` 或 `float`。
- 非目标：不处理 DSL 形参绑定和 `tile_*` 规则。
- 模块范围：`kernel_gen/execute_engine/runtime_args.py`、`test/execute_engine/test_invoke.py`。
- 禁止修改面：`expectation/`、带 `[immutable]` / `[immutable-file]` 标记的文件或内容、`.skills/`、`agents/standard/`、`AGENTS.md`、`TODO.md`、`DONE.md`、本计划书。
- 合同真源：`spec/execute_engine/execute_engine_api.md` > `runtime_args.py` 文件级 API 列表 > `test/execute_engine/test_invoke.py`。
- 最小功能闭环：一个公开函数能描述所有当前 execute runtime args 基础类型，ABI slot 构造不再独立重复分类。
- 执行步骤：
  1. 新增 info dataclass、TypeAlias 和 `describe_runtime_arg(...)`。
  2. 把 dtype 规整结果映射到 `NumericType`，包含 `torch.bfloat16` / `bfloat16 -> NumericType.BFloat16`。
  3. 修改 `_RuntimeArgSupport.build_arg_slots(...)` 使用 `describe_runtime_arg(...)`，保留 allow-absent `None`、contiguous 拒绝、dtype code、data pointer 和 marshal 私有逻辑。
  4. 补 execute_engine 测试矩阵，覆盖成功、unsupported、None、bool、numpy integer scalar、numpy floating scalar、numpy bool scalar、memory stride、contiguous、dtype alias 表和不直接导入 torch/numpy 的 import 边界。
- 验收必过项目：`pytest -q test/execute_engine/test_contract.py test/execute_engine/test_invoke.py`；`PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/repo_conformance/test_private_api_boundaries.py`。
- 当前必过 expectation 合同验收：不适用；本卡不列 `expectation/` 为必跑入口。
- 记录要求：写清旧分类逻辑删改点、保留 ABI 私有逻辑依据、Diff 反推自测和 unsupported dtype 行为。

### S3. 对齐 dsl_run runtime 参数合同

- 为什么做：`dsl_run(...)` 最终调用 execute_engine，却提前拒绝普通 `float` scalar，公开合同已与执行引擎偏移。
- 做什么：更新 `spec/tools/dsl_run.md`、`spec/tools/dsl_cost_run.md`、`kernel_gen/tools/dsl_run.py` 和 `kernel_gen/tools/__init__.py`，让 `dsl_run(...)` 和 `dsl_cost_run(...)` 使用 `describe_runtime_arg(...)` 做基础分类，支持普通 float scalar，保留 `bool` 拒绝、`tile_*` 正整数约束、Tensor 注解和 memory absent 规则。
- 不做什么：不新增 `dsl_run(...)` 参数，不新增 `dsl_run.py` 公开 API，不改变 dump、pipeline、target、return value 或 cost kind 行为。
- 怎么验收：`pytest -q test/tools/test_dsl_run.py test/tools/test_dsl_cost_run.py test/tools/test_package.py` 通过；`rg -n "_runtime_module_name|_is_torch_tensor|_is_numpy_array|_is_runtime_scalar|_normalize_runtime_scalars|_is_tensor_runtime_arg|_runtime_arg_shape|_runtime_arg_stride|_runtime_arg_dtype|Integral" kernel_gen/tools/dsl_run.py kernel_gen/tools/__init__.py` 不再命中已被替代的重复基础分类 helper 定义或旧整数-only 类型说明。
- 卡住问谁：用户；触发条件是必须新增 `dsl_run.py` 公开 helper、改变稳定错误文本或让 `tile_*` 接受 float。
- 上下文摘要：DSL AST 和 `mlir_gen(...)` 当前已经支持 float runtime arg，阻断点在 tools 层合同和实现。
- 小任务目标：修正 `dsl_run(...)` runtime scalar 合同，并复用 execute_engine runtime args 真源。
- 非目标：不改 `mlir_gen(...)`、AST 节点或 execute ABI 签名。
- 模块范围：`spec/tools/dsl_run.md`、`spec/tools/dsl_cost_run.md`、`kernel_gen/tools/dsl_run.py`、`kernel_gen/tools/__init__.py`、`test/tools/test_dsl_run.py`、`test/tools/test_dsl_cost_run.py`、`test/tools/test_package.py`。
- 禁止修改面：`expectation/`、带 `[immutable]` / `[immutable-file]` 标记的文件或内容、`.skills/`、`agents/standard/`、`AGENTS.md`、`TODO.md`、`DONE.md`、本计划书。
- 合同真源：`spec/tools/dsl_run.md` > `spec/execute_engine/execute_engine_api.md` > `test/tools/test_dsl_run.py`。
- 最小功能闭环：普通 float scalar 通过 `dsl_run(...)` 进入 `DslRunResult.runtime_args` 和 execute args；`dsl_cost_run(...)` 复用同一 real_args 绑定规则；`tile_*` float / bool / numpy bool 仍失败。
- 执行步骤：
  1. 修改 `spec/tools/dsl_run.md` 与 `spec/tools/dsl_cost_run.md` 中 `RuntimeRealArg`、注意事项、错误语义和测试清单，写明 `float` 支持与 `tile_*` 限制。
  2. 在 `dsl_run.py` 中导入 `describe_runtime_arg` 和 info 类型，移除被替代的基础分类 helper。
  3. 同步 `kernel_gen/tools/__init__.py` 的文件级说明和 `RuntimeRealArg` 文档类型，保证包根 `dsl_run(...)` / `dsl_cost_run(...)` 签名说明与子模块一致。
  4. 调整 `dsl_run(...)` 与 `dsl_cost_run(...)` 的 runtime args 规整逻辑，分别生成 `dsl_args` 与 `execute_args`。
  5. 保持 `DslRunInvalidRealArgs`、`DslRunArityMismatch`、`DslRunInvalidTileValue` 的公开错误语义稳定；把 unsupported 文案固定修正为 `DslRunUnsupportedRealArg: real_args only supports torch.Tensor, numpy.ndarray, integer scalar, float scalar and None for memory`。
  6. 为 `dsl_cost_run(...)` 补普通 float / numpy floating 测试时，必须断言 real_args 绑定层已经放行；若测试因缺少 cost sibling 或 cost 现有合同失败，断言错误不再是 `DslRunUnsupportedRealArg` 或 tile 绑定层错误。
- 验收必过项目：`pytest -q test/tools/test_dsl_run.py test/tools/test_dsl_cost_run.py test/tools/test_package.py`。
- 当前必过 expectation 合同验收：不适用；本卡不列 `expectation/` 为必跑入口；`expectation/tools/dsl_run/**` 与 `expectation/tools/dsl_cost_run/**` 仅作历史 / 本地只读来源说明。
- 记录要求：写清公开错误文本变化、用户确认来源、删除的重复 helper、float 正向与 tile float 失败测试结果。

### S4. 补齐跨模块一致性与静态门禁

- 为什么做：本计划触及公开 API、跨文件调用和私有 helper 边界，需要防止测试直连私有实现或把文件级 API 错误导入包根。
- 做什么：补或更新测试，验证 `runtime_args.py` 文件级公开 API 可直接导入、包根不导出、`dsl_run.py` 不导入 `_RuntimeArgSupport`，并运行 private API / KernelCodeError 静态门禁。
- 不做什么：不新增测试专用公开 helper，不放宽静态门禁 allowlist。
- 怎么验收：`PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/repo_conformance/test_private_api_boundaries.py test/tools/test_kernel_code_error_static_gate.py` 通过；`rg -n "_RuntimeArgSupport|_ArgSlot|_CArgSlot" kernel_gen/tools test/tools test/execute_engine` 不命中跨文件依赖或测试直连私有 ABI 结构；`test/execute_engine/test_contract.py` 继续证明 `kernel_gen.execute_engine.__all__` 不导出 runtime_args 文件级 API。
- 卡住问谁：架构师；触发条件是现有静态门禁与计划目标冲突且无法通过重构解决。
- 上下文摘要：项目规则禁止跨文件使用非公开 API，新增文件级 API 必须被 spec 和测试锁定。
- 小任务目标：证明本轮重构没有跨文件私有 API、测试直连私有 helper、包根导出泄漏或旧错误类型问题。
- 非目标：不调整 unrelated conformance 规则。
- 模块范围：`test/execute_engine/**`、`test/tools/**`、`test/repo_conformance/**` 只读或按必要测试更新。
- 禁止修改面：`expectation/`、带 `[immutable]` / `[immutable-file]` 标记的文件或内容、`.skills/`、`agents/standard/`、`AGENTS.md`、`TODO.md`、`DONE.md`、本计划书。
- 合同真源：根 `AGENTS.md`、`agents/standard/实现文件规范.md`、`agents/standard/审查规范.md`、相关 spec。
- 最小功能闭环：静态门禁证明新增 API 是公开路径，旧私有路径未被跨文件消费。
- 执行步骤：
  1. 更新或新增测试断言 `kernel_gen.execute_engine.runtime_args.__all__` 包含新增 API。
  2. 保持 `kernel_gen.execute_engine.__all__` 断言不变。
  3. 运行 private API 和 tools 错误静态门禁。
  4. 用 `rg` 记录 `_RuntimeArgSupport`、`_ArgSlot`、`_CArgSlot` 未被 `dsl_run.py`、tools 测试或 execute_engine 测试跨文件导入。
- 验收必过项目：`PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/repo_conformance/test_private_api_boundaries.py test/tools/test_kernel_code_error_static_gate.py`。
- 当前必过 expectation 合同验收：不适用；本卡不列 `expectation/` 为必跑入口。
- 记录要求：写清静态门禁结果、包根导出边界和私有 API 扫描结果。

### S5. 全量收口与记录

- 为什么做：本计划改变公开 API 和工具错误语义，执行记录必须能支撑 review、入档验收和 merge。
- 做什么：运行本计划验收命令，按实际 diff 反推补充测试，完成任务记录中的执行前阅读、自检、Diff 反推自测、敏感目录门禁、减法检查和剩余风险说明。
- 不做什么：不手工修改 `TODO.md` / `DONE.md`，不创建额外计划级任务。
- 怎么验收：本计划 `验收设计` 全部命令通过；`git diff --check` 通过；敏感目录 `expectation/ .skills agents/standard AGENTS.md TODO.md DONE.md` 无本任务越权 diff；带 `[immutable]` / `[immutable-file]` 标记的文件或内容无本任务越权改动；任务记录写清 `expectation/tools/dsl_run/**` 与 `expectation/tools/dsl_cost_run/**` 只读核对结论。
- 卡住问谁：管理员；触发条件是流程状态、依赖任务或 worktree 同步冲突。用户；触发条件是新增公开 API 或错误文本超出本计划确认范围。
- 上下文摘要：执行、审查、入档验收都需要可追溯证据。
- 小任务目标：完成规格、实现、测试、验收和任务记录闭环，进入 review。
- 非目标：不执行任务分发或合并。
- 模块范围：本计划触达的 spec / implementation / test / task record。
- 禁止修改面：`expectation/`、带 `[immutable]` / `[immutable-file]` 标记的文件或内容、`.skills/`、`agents/standard/`、`AGENTS.md`、`TODO.md`、`DONE.md`、本计划书。
- 合同真源：本计划书 > 相关 spec > pytest / 静态门禁 > 任务记录。
- 最小功能闭环：review 能从 diff、测试和记录确认公开 API、行为修正、重复逻辑删除和无越权。
- 执行步骤：
  1. 运行本计划全部 pytest / conformance 命令。
  2. 按实际 diff 反推补充必要测试，并记录为什么需要或不需要。
  3. 执行 `git diff --check`、敏感目录空 diff 核对与 `[immutable]` / `[immutable-file]` 标记文件无越权改动核对。
  4. 在任务记录中写清执行前阅读、实现摘要、减法检查、自检、Diff 反推自测和剩余风险。
- 验收必过项目：本计划 `验收设计` 全部命令；合同验收：无当前必过 expectation。
- 当前必过 expectation 合同验收：不适用；本卡只要求只读核对历史 / 本地来源，不运行或修改 `expectation/`。
- 记录要求：任务记录必须写明用户确认来源、公开 API 变更、`dsl_run` float 合同修正、`RuntimeMemoryArgInfo.dtype` 使用 `NumericType`、未修改 expectation、未触碰 `[immutable]` / `[immutable-file]` 标记内容、未混入 CUDA。

## 计划自检与返工口径

- 自检：
  - 公开 API 变更已有用户确认来源。
  - 新 API 只进入 `runtime_args.py` 文件级公开 API，不进入包根 `kernel_gen.execute_engine.__all__`。
  - `NumericType` 是 dtype 公开真源，字符串 dtype 映射只留在 `describe_runtime_arg(...)` 内部。
  - `RuntimeInput` 文档类型明确覆盖 numpy integer / floating scalar，进入 ABI slot 前规整为 Python `int` / `float`。
  - `None` 合法性不放进 `describe_runtime_arg(...)`，由 `dsl_run(...)` 或 execute ABI 上下文判断。
  - `dsl_run(...)` 普通 float 支持和 `tile_*` 正整数规则同时写入 spec / tests。
  - `dsl_cost_run(...)`、`spec/tools/dsl_cost_run.md`、`kernel_gen/tools/__init__.py` 和 tools 包根测试纳入范围。
  - `expectation/tools/dsl_run/**` 与 `expectation/tools/dsl_cost_run/**` 只作为历史 / 本地只读来源，不作为当前必过验收且无修改授权。
  - 计划内小任务卡都包含为什么做、做什么、不做什么、怎么验收、卡住问谁、执行步骤和验收必过项目。
- 返工口径：只要仍有能提升质量、可读性、可维护性、测试有效性或验收可信度的可执行项，就回到计划修订或 execute 返工；不得以“当前能跑”放行重复分类逻辑或跨文件私有 API。

## 待确认项

- 当前无待用户确认项。

## 用户确认与协同约束

- 用户确认来源：见 `文档信息 / 用户确认来源`。
- 用户已确认事项：
  - `dsl_run(...)` 与 execute_engine runtime args 基础处理应一致。
  - `dsl_run(...)` 支持普通 `float` scalar。
  - `runtime_args.py` 是 runtime arg 基础处理真源。
  - 公开 API 收口为 `describe_runtime_arg(...)` 主入口。
  - `RuntimeMemoryArgInfo.dtype` 使用 `NumericType`。
  - execute 公开 `RuntimeInput` 的 runtime scalar 范围同步覆盖 numpy integer / floating scalar，并由 `describe_runtime_arg(...)` 规整为 Python `int` / `float`。
- 待用户确认项：无。若 execute 发现必须新增本计划外公开 API、进入包根导出、改变 `tile_*` 语义、支持 `NumericType` 外 dtype、改变 `DslRunUnsupportedRealArg` / `DslRunInvalidTileValue` 最终文本或修改 `expectation/`，必须暂停并回用户确认。
- 迭代审阅记录：见本文件 `迭代审阅记录`；subagent strict review 已收敛通过，无阻断、无最小需改项、无待确认项。
- 守护最终检验：复检通过；可由管理员按下发依赖创建 / 下发唯一计划级 `execute`。
