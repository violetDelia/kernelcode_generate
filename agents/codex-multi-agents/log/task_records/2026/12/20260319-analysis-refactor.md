# 20260319-analysis-refactor

- 任务: T-20260319-fa47e9e0
- 执行人: 我不是牛马
- worktree: /home/lfr/kernelcode_generate
- 时间: 2026-03-19 04:16:33 +0800

## 结论
- 不通过。

## 再次审查要点（spec 新增公开 API 约束）
- `spec/analysis/分析.md` 已新增“公开接口”章节，覆盖 `MemoryRef/Operation/OpStats/AnalysisSummary` 以及 `analyze_elementwise/analyze_broadcast/analyze_matmul/analyze_function` 的参数约束与行为约束；与本轮审查目标一致。
- AN-001..006 与 `test/analysis/test_analysis.py` 仍保持一一对应，统计公式、物化/融合聚合口径与实现一致。

## 不通过原因与改进建议

### 1) spec 已将 `read_mask` “长度必须为固定值”写为硬约束，但实现未做校验（spec/实现不一致）

需改位置：
- `python/analysis/analysis.py: analyze_elementwise`
- `python/analysis/analysis.py: analyze_broadcast`
- `python/analysis/analysis.py: analyze_matmul`

为什么要改：
- spec 明确约束：
  - `analyze_elementwise`：`rhs` 为 `Memory` 时 `read_mask` 长度必须为 2；`rhs` 为标量时长度必须为 1 或 2。
  - `analyze_broadcast`：`read_mask` 长度必须为 1。
  - `analyze_matmul`：`read_mask` 长度必须为 2。
- 当前实现对 `read_mask` 不做长度校验：例如 `analyze_broadcast` 直接访问 `read_mask[0]`，短列表可能抛 `IndexError`；`analyze_elementwise` 用迭代器+默认 `False` 的方式“吞掉缺失项”，会把违反 spec 的输入静默当作不读而继续计算。

建议改法：
- 在上述三个入口显式校验 `read_mask` 长度，不满足时抛 `AnalysisError`，并在错误信息中包含 op 名称与期望长度，避免调用方定位困难。
- 补充单元测试覆盖该错误边界（建议新增 AN-007/AN-008 或在现有文件中新增测试但同步 spec 测试清单）。

是否需要新建改进任务：
- 需要：派发“改进实现/测试”任务，收敛 `read_mask` 的错误边界与异常类型；改完后再次审查。

### 2) `analyze_function` 仍未校验 `Operation.inputs` 数量，异常类型仍可能泄露为 IndexError（未收敛）

需改位置：
- `python/analysis/analysis.py: analyze_function`

为什么要改：
- spec 在 `Operation` 字段约束中已经明确不同算子的 `inputs` 数量要求（elementwise/matmul=2，broadcast=1）。
- 当前实现仍直接访问 `op.inputs[0]`/`op.inputs[1]`，若传入非法 `Operation` 会抛 `IndexError` 而非统一的 `AnalysisError`，不利于调用方稳定处理错误边界。

建议改法：
- 在分发到各 analyze_* 前先校验 `len(op.inputs)` 是否满足算子要求，不满足则抛 `AnalysisError`。
- 增加负例测试用例，锁定异常类型为 `AnalysisError`（并同步到 spec 测试清单）。

是否需要新建改进任务：
- 需要：继续派发“改进实现/测试”任务；改完后再次审查。

### 3) spec 的“公开接口”未声明 `AnalysisError`，但实现已作为对外错误类型存在（API 口径待收敛）

需改位置：
- `spec/analysis/分析.md`

为什么要改：
- 实现对外导出了 `AnalysisError`，且错误边界主要通过该类型表达；但 spec 的“公开接口”未列出 `AnalysisError`，导致调用方无法按 spec 依赖稳定错误类型。

建议改法（二选一）：
- 方案 A（推荐）：将 `AnalysisError` 纳入 spec 的“公开接口”并说明其继承关系（例如 `ValueError`）与使用方式；
- 方案 B：在实现中将 `AnalysisError` 视为内部实现细节（但这会要求对外统一用 `ValueError`/`TypeError` 等，并同步更新测试与文档）。

是否需要新建改进任务：
- 需要：派发“改进 spec”任务明确错误类型口径；改完后再次审查。

- 任务: T-20260319-38f9470a / T-20260319-ed907e9f
- 执行人: 咯咯咯
- worktree: /home/lfr/kernelcode_generate
- 时间: 2026-03-19 07:42:15 +0800

## 范围
- `spec/analysis/分析.md`

## 已完成
- 补齐 `analysis` 模块公开 API 与数据结构约束，明确 `Operation.materialize`、`dtype_size`、`predicate_size`、`read_mask`、`write_output` 的含义与约束。
- 明确公开错误类型 `AnalysisError`，补充 `read_mask` 长度校验与 `Operation.inputs` 数量校验的 spec 约束与测试映射（AN-007/AN-008 待补测试）。
- 将 AN-007/AN-008 更新为正式测试映射，调整 `analyze_elementwise` 在标量 rhs 的 `read_mask` 约束描述以匹配实现。
- 新增 `依赖`、`限制与边界`、`公开接口` 章节，补齐数据结构与统计入口说明，保留既有统计公式与 AN-001..AN-006 口径不变。

## 修改文件
- `spec/analysis/分析.md`

## 规范缺口与风险
- 仅更新 spec，未校验与当前实现/测试的一致性；需后续审查确认接口约束是否完全匹配实现与测试覆盖。

## 是否需要派发实现/测试收敛任务
- 需要。建议后续发起审查任务，核对 `python/analysis/analysis.py` 与 `test/analysis/test_analysis.py` 是否与新增约束一致。

---

## T-20260319-eeed1c3f

- 时间：2026-03-19 06:34:36 +0800
- 角色：`金铲铲大作战`
- 任务描述：补齐 read_mask/inputs 校验并新增 AN-007/AN-008 负例测试。
- worktree：`/home/lfr/kernelcode_generate`
- 变更文件：
  - `python/analysis/analysis.py`
  - `test/analysis/test_analysis.py`
- 变更摘要：
  - 对 elementwise/broadcast/matmul 增加 read_mask 长度校验并统一抛 AnalysisError。
  - 对 analyze_function 增加 Operation.inputs 数量校验。
  - 新增 AN-007/AN-008 负例测试。
- 测试结果：
  - `pytest -q test/analysis/test_analysis.py`
  - 结果：`8 passed in 0.31s`

---

## T-20260319-014b751f（审查）

- 执行人: 我不是牛马
- worktree: /home/lfr/kernelcode_generate
- 时间: 2026-03-19 07:36:54 +0800
- 结论: 不通过

### 已核对一致（无建议项）
- `AnalysisError` 已在 `spec/analysis/分析.md` 的公开接口中声明，`python/analysis/analysis.py` 也以 `ValueError` 子类对外暴露，且测试显式使用该类型断言。
- `analyze_broadcast/analyze_matmul/analyze_function` 的形状校验、读写/计算统计公式、以及函数级“物化/融合”聚合口径与 `AN-001..006` 测试一致，未出现口径漂移。
- `Operation.inputs` 数量校验已在 `analyze_function` 实现中落地，且 `AN-008` 负例测试覆盖并断言抛 `AnalysisError`。
- `read_mask` 长度校验已在逐元素/broadcast/matmul 入口落地，且 `AN-007` 负例测试覆盖并断言抛 `AnalysisError`。

### 不通过原因与改进建议（存在建议 => 必须不通过）

1) `AN-007/AN-008` 的 spec↔test 映射仍未闭环（spec 标注“待补”，且测试名不一致）
   - 需改位置: `spec/analysis/分析.md` -> “测试清单”表格 `AN-007/AN-008` 行
   - 现状:
     - spec 写为“待补：`test_analysis_read_mask_length_validation` / `test_analysis_operation_input_count_validation`”
     - 实际测试已落地为 `test_analysis_read_mask_length_mismatch` 与 `test_analysis_function_inputs_mismatch`
   - 为什么要改: 当前任务要求核对 `AN-001..008` 映射闭环；spec 仍把已落地测试标为“待补”，会造成后续维护与审查判断漂移。
   - 建议改法:
     - 将 `AN-007` 的“建议测试”更新为 `test_analysis_read_mask_length_mismatch`，去掉“待补”前缀。
     - 将 `AN-008` 的“建议测试”更新为 `test_analysis_function_inputs_mismatch`，去掉“待补”前缀。
   - 是否需要新建改进任务: 需要（改进 spec）；改完后应创建再次审查任务。

2) `analyze_elementwise` 在 `rhs` 为标量时的 `read_mask` 长度约束与 spec 不一致
   - 需改位置:
     - spec: `spec/analysis/分析.md` -> `analyze_elementwise` 参数约束（标量 rhs 的 `read_mask` 长度描述）
     - 实现: `python/analysis/analysis.py` -> `analyze_elementwise`（`rhs` 非 `Memory` 分支的 `read_mask` 长度校验）
   - 现状:
     - spec 允许标量 rhs 的 `read_mask` 长度为 `1` 或 `2`
     - 实现仅接受长度 `1`，长度 `2` 会抛 `AnalysisError("read_mask length mismatch")`
   - 为什么要改: `analyze_elementwise` 是公开入口且签名接受 `rhs: Memory | int`，该不一致会导致调用方按 spec 传参时被实现拒绝，属于公开 API 约束漂移。
   - 建议改法（二选一，需管理员裁定取向）:
     - 方案 A（改实现，推荐最小改动）：允许标量 rhs 的 `read_mask` 长度为 `1` 或 `2`；长度为 `2` 时仅使用第 1 项控制 `lhs` 读（第 2 项忽略或在 spec 明确“当前不计标量读”）。
     - 方案 B（改 spec）：将标量 rhs 的 `read_mask` 约束收敛为“长度必须为 1”，同步移除“长度为 2 控制标量读”的描述。
   - 是否需要新建改进任务: 需要（改进 spec 或改进实现）；改完后应创建再次审查任务。

### 后续任务建议
- 建议管理员创建“改进 spec（analysis）”任务，优先补齐 `AN-007/AN-008` 在 `spec/analysis/分析.md` 的映射闭环。
- 同时创建“改进 spec 或改进实现（analysis）”任务，收敛 `analyze_elementwise` 标量 `rhs` 的 `read_mask` 长度约束；改完后需再次审查。

---

## T-20260319-51480c5f（再次审查）

- 执行人: 我不是牛马
- worktree: /home/lfr/kernelcode_generate
- 时间: 2026-03-19 07:44:48 +0800
- 结论: 不通过

### 已核对一致（无建议项）
- `AN-001..AN-008` 在 `spec/analysis/分析.md` 的“测试清单”中已与 `test/analysis/test_analysis.py` 真实测试名闭环（`AN-007=test_analysis_read_mask_length_mismatch`，`AN-008=test_analysis_function_inputs_mismatch`）。
- `AnalysisError` 为公开错误类型，`read_mask` 长度校验与 `Operation.inputs` 数量校验在实现与测试中已落地，且异常类型统一为 `AnalysisError`。
- 统计公式与函数级物化/融合聚合口径与既有 `AN-001..006` 断言一致，未观察到口径漂移。

### 不通过原因与改进建议（存在建议 => 必须不通过）

1) `analyze_elementwise` 在 `rhs` 为标量时的 `read_mask` 约束仍未与实现一致
   - 需改位置:
     - `spec/analysis/分析.md` -> `analyze_elementwise` 参数约束（标量 rhs 的 `read_mask` 描述）
     - `python/analysis/analysis.py` -> `analyze_elementwise`（`rhs` 非 `Memory` 分支的 `read_mask` 长度校验）
   - 现状:
     - spec：当 `rhs` 为标量，允许 `read_mask` 长度为 `1` 或 `2`，且长度为 `2` 的第 2 项“控制标量读”
     - 实现：当 `rhs` 为标量，仅接受长度 `1`；长度 `2` 会抛 `AnalysisError(\"read_mask length mismatch\")`
   - 为什么要改:
     - 该入口是公开 API（签名 `rhs: Memory | int`），spec/实现不一致会导致调用方按 spec 传参却被实现拒绝，属于公开参数约束漂移。
     - 另外，当前 spec 的逐元素“与标量”读字节基线公式为 `N * dtype_size`，并未体现“可选计入标量读”的额外项，和“第 2 项控制标量读”的描述也存在语义张力。
   - 建议改法（二选一，需管理员裁定取向）:
     - 方案 A（改 spec，推荐）：收敛为“当 `rhs` 为标量，`read_mask` 长度必须为 1，仅控制 `lhs` 读”，并删除“长度为 2 控制标量读”的描述。
     - 方案 B（改实现）：允许标量 rhs 的 `read_mask` 长度为 1 或 2；若长度为 2，则第 2 项要么明确忽略（并在 spec 写明“当前不计标量读”），要么将标量读以明确口径计入（需同步更新 spec 公式与测试覆盖）。
   - 是否需要新建改进任务: 需要（改进 spec 或改进实现）；改完后需再次审查。

### 后续任务建议
- 建议创建“改进 spec（analysis）”任务优先收敛标量 rhs 的 `read_mask` 约束到与实现一致；改完后继续创建“再次审查”任务，通过后再进入合并阶段。

---

## T-20260319-a5db007b（再次审查）

- 执行人: 我不是牛马
- worktree: /home/lfr/kernelcode_generate
- 时间: 2026-03-19 07:48:33 +0800
- 结论: 通过

### 复核结论（闭环确认）
- `AN-001..AN-008` 在 `spec/analysis/分析.md` 的测试清单与 `test/analysis/test_analysis.py` 真实测试函数名一一对应闭环，`AN-007/AN-008` 已使用真实测试名且 spec 内无“待补”残留。
- `analyze_elementwise` 在 `rhs` 为标量时的 `read_mask` 约束已按实现收敛为“长度必须为 1，仅控制 lhs 读”，与 `python/analysis/analysis.py` 的长度校验一致。
- `AnalysisError`、`read_mask` 长度校验、`Operation.inputs` 数量校验、统计公式与函数级物化/融合聚合口径与实现/测试一致，未发现口径漂移或新增风险点。

### 后续任务建议
- 建议进入合并提交整理/合并到 main 阶段（由管理员下发合并任务）。

---

## T-20260319-f3b286ba

- 执行人: 咯咯咯
- worktree: /home/lfr/kernelcode_generate
- 时间: 2026-03-19 07:46:39 +0800

## 范围
- `spec/analysis/分析.md`

## 已完成
- 将 `analyze_elementwise` 在 `rhs` 为标量时的 `read_mask` 约束收敛为“长度必须为 1，仅控制 `lhs`”，删除“第 2 项控制标量读”的描述，与当前实现一致。
- 保持 AN-001..008 映射、统计公式与其他公开 API 口径不变。

## 修改文件
- `spec/analysis/分析.md`

## 测试
- 未运行（按要求不复测）。

## T-20260319-28733452

- 时间：2026-03-19 07:50:12 +0800
- 角色：李白
- 任务描述：提交整理并合入 analysis 链路。
- worktree：`/home/lfr/kernelcode_generate`
- 合并结果：
  - 已在 main 合入提交 `b4d1798`。
- 变更文件：
  - `spec/analysis/分析.md`
  - `python/analysis/analysis.py`
  - `test/analysis/test_analysis.py`
- 测试说明：未复测（按任务要求默认不额外复测）。
