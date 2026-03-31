# 20260319-symbol-variable-spec-normalize

- 任务: T-20260319-68ec7a96
- 执行人: 朽木露琪亚
- worktree: /home/lfr/kernelcode_generate
- 时间: 2026-03-19 07:35:16 +0800

## 本次改动
- 收敛 `spec/symbol_variable/type.md` 中 `Farmat` 的可改段落，删除“别名语义/别名验证/别名规则一致”等与当前实现测试不一致的表述。
- 统一 `Farmat` 口径为“仅公开 `Norm` / `CLast` 两成员”，兼容性与测试目标均以成员可见性、成员名称和导出边界为准。
- 在测试用例清单中补回 `TY-002 -> test_farmat_public_members` 的正式映射，和当前测试函数名保持一致。

## 修改文件
- `spec/symbol_variable/type.md`

## 说明
- 未修改 `[immutable]` 段。
- 未修改 `python` / `test`。
- 建议进入复审，重点核对 `Farmat` 在 spec 中是否还残留 `.value` / 别名 / `repr` 等超出当前公开口径的约束。

# 20260319-symbol-variable-spec-normalize

- 任务: T-20260319-27df6f10
- 执行人: 提莫炖蘑菇
- worktree: /home/lfr/kernelcode_generate
- 时间: 2026-03-19 03:43:37 +0800

## 结论
- 不通过。

## 核对范围
- `spec/symbol_variable/memory.md` ↔ `python/symbol_variable/memory.py` ↔ `test/symbol_variable/test_memory.py`
- `spec/symbol_variable/package_api.md` ↔ `python/symbol_variable/__init__.py` ↔ `test/symbol_variable/test_package_api.py`
- `spec/symbol_variable/symbol_dim.md` ↔ `python/symbol_variable/symbol_dim.py` ↔ `test/symbol_variable/test_symbol_dim.py`
- `spec/symbol_variable/symbol_shape.md` ↔ `python/symbol_variable/symbol_shape.py` ↔ `test/symbol_variable/test_symbol_shape.py`
- `spec/symbol_variable/type.md` ↔ `python/symbol_variable/type.py` ↔ `test/symbol_variable/test_type.py`

## 不通过原因与改进建议

### 1) `Farmat`（layout 枚举）spec/实现/测试不一致，且 spec 内部表述冲突

需改位置：
- `spec/symbol_variable/type.md`：`Farmat` 段落内的“公开成员/示例”与“别名/兼容性/测试目标”表述。
- `python/symbol_variable/type.py`：`class Farmat` 当前定义包含 `NHWC/NCHW` 并用 `Norm/CLast` 作为 `Enum` 别名。
- `test/symbol_variable/test_type.py`：`test_farmat_aliases` 当前断言 `Farmat.Norm is Farmat.NCHW`、`Farmat.Norm.name == "NCHW"` 等别名行为。

为什么要改：
- `spec/symbol_variable/type.md` 中（含不可更改片段）明确“当前公开成员包括 `Norm` / `CLast`”，且示例期望 `Farmat.Norm.name == "Norm"`；但当前实现/测试把 `Norm/CLast` 做成 `NCHW/NHWC` 的别名，导致 `.name`/`repr` 呈现为 `NCHW/NHWC`，公开接口语义发生漂移，调用方按 spec 编码会遇到不一致。
- 同一份 spec 中又出现“`Farmat` 的 `name` 与 `repr` 行为保持与 Python `Enum` 别名规则一致”“验证 `Farmat` 的别名关系”等描述，与“仅公开 `Norm/CLast`”的口径相互冲突，导致“latest spec 唯一”目标无法成立。

建议改法（推荐向 spec 的不可更改约束收敛）：
- 改进实现/测试：在 `python/symbol_variable/type.py` 中移除 `Farmat.NHWC` / `Farmat.NCHW` 等超出当前 spec“公开成员”范围的成员；将 `Farmat` 收敛为仅包含 `Norm` / `CLast` 两个稳定成员（建议其 `.value` 分别为 `"NCHW"` / `"NHWC"`，用值表达布局映射，而不是用 `Enum` 别名偷渡等价语义）；同步更新 `test/symbol_variable/test_type.py`，删去别名断言，改为断言 `.name` 与 `.value` 的稳定性。
- 改进 spec（仅限可改片段）：清理 `spec/symbol_variable/type.md` 中“别名关系/别名规则一致”的矛盾表述与测试目标描述，使其与“仅公开 `Norm/CLast` 且 `.name` 稳定”为同一口径；避免在 spec 中将“语义别名”（Norm/CLast 表示类别）与“Python Enum 别名”（两个名字指向同一成员）混用。

影响范围：
- `python.symbol_variable.type.Farmat` 的公开 API、示例与调试输出（例如 `repr()`）；
- 依赖 `Farmat` 的 `Memory(format=...)` 相关示例与用例（`spec/symbol_variable/memory.md`、`spec/symbol_variable/package_api.md` 等会被连带影响，但其本身目前未强约束 `.name` 表现）。

是否需要新建改进任务：
- 需要，且至少 2 个：
  1) 改进实现/测试任务：`python/symbol_variable/type.py`、`test/symbol_variable/test_type.py`（必要时连带 `test/symbol_variable/test_memory.py`/`test/symbol_variable/test_package_api.py` 中对 `Farmat` 的断言）收敛到 spec 的“仅 `Norm/CLast`”口径；改完后再派发“再次审查”任务。
  2) 改进 spec 任务：清理 `spec/symbol_variable/type.md` 中可修改段落的矛盾表述，确保 spec 内部自洽且与实现/测试一致；改完后再派发“再次审查”任务。

### 2) 其他文件核对结论（本轮未发现新增冲突）
- `memory`：`LocalSpaceMeta.max_size=None`、`GM/SM/LM/TSM/TLM align=1024/max_size=None`、`Memory(stride=None)` 语义与 `test/symbol_variable/test_memory.py` 一致；逐元素算术/比较在实现与 `test/operation/test_memory_operation.py` 中有覆盖，与 `spec/symbol_variable/memory.md` 当前边界描述不冲突。
- `symbol_dim` / `symbol_shape` / `package_api`：spec/实现/测试表述与行为基本一致；包含 `[immutable]` 的内容仅核对未修改。

- 任务: T-20260319-d43cbfa4
- 执行人: 咯咯咯
- worktree: /home/lfr/kernelcode_generate
- 时间: 2026-03-19 03:20:23 +0800

## 范围
- `spec/symbol_variable/memory.md`
- `spec/symbol_variable/package_api.md`
- `spec/symbol_variable/symbol_dim.md`
- `spec/symbol_variable/symbol_shape.md`
- `spec/symbol_variable/type.md`

## 已完成
- 按 AGENTS.md 的 spec 结构补齐 `功能简介`/`依赖`/`限制与边界`/`公开接口` 等章节命名，统一结构与表述。
- 补齐 `symbol_shape` 中缺失的使用示例，覆盖列表行为、`get_shape`、`get_values`、`to_symbols`、`__repr__` 等接口。
- 补齐 `memory` 中 tensor-like 示例缺失的 `NumericType`/`Farmat` 导入，确保示例可直接运行。
- 统一 `type.md` 的章节命名为“限制与边界”，与当前 spec 规范一致。
- 规避所有 `[immutable]` 段落，未修改含 `[immutable]` 的原有内容。

## 修改文件
- `spec/symbol_variable/memory.md`
- `spec/symbol_variable/package_api.md`
- `spec/symbol_variable/symbol_dim.md`
- `spec/symbol_variable/symbol_shape.md`
- `spec/symbol_variable/type.md`

## 规范缺口与风险
- 仅收敛 spec，未触及实现与测试，需后续审查确认 spec 与现有实现/测试的一致性。

## 是否需要派发实现/测试收敛任务
- 需要。建议创建后续审查任务，核对 spec 与 `python/symbol_variable/*`、`test/symbol_variable/*` 是否一致，尤其是补充的示例与接口描述是否匹配现有实现行为。

## T-20260319-65160ba3

- 执行人: 小李飞刀
- worktree: /home/lfr/kernelcode_generate
- 时间: 2026-03-19 06:33:41 +0800

## 本次改动
- 收敛 Farmat 仅公开 Norm/CLast 两成员，移除 NHWC/NCHW 别名公开语义。
- 更新 type 测试断言，确保无 NHWC/NCHW 成员暴露。

## 变更文件
- /home/lfr/kernelcode_generate/python/symbol_variable/type.py
- /home/lfr/kernelcode_generate/test/symbol_variable/test_type.py

## 测试
- pytest -q test/symbol_variable/test_type.py
- pytest -q test/symbol_variable/test_memory.py

---

## T-20260319-9f78f79c（再次审查）

- 执行人: 提莫炖蘑菇
- worktree: /home/lfr/kernelcode_generate
- 时间: 2026-03-19 07:40:30 +0800
- 结论: 通过

### 复核结论（闭环确认）
- `Farmat` 在 `python/symbol_variable/type.py` 仅公开 `Norm/CLast` 两成员；`test/symbol_variable/test_type.py::test_farmat_public_members` 覆盖并断言不暴露 `NCHW/NHWC` 成员。
- `spec/symbol_variable/type.md` 已收敛为仅以 `Norm/CLast` 作为公开成员口径，不再要求/验证别名关系、别名验证或 `.value` 字符串等价规则（`Farmat` 示例仅使用 `.name`）。
- `TY-002 -> test_farmat_public_members` 映射已在 `spec/symbol_variable/type.md` 的测试清单中闭环。
- `test/symbol_variable/test_memory.py` 对 `Memory(format=Farmat.*)` 的用法与当前 `Farmat` 公开口径一致，未引入别名语义验证。

### 后续任务建议
- 建议进入合并提交整理/合并到 main 阶段（由管理员下发合并任务）。

## T-20260319-4fbc2952

- 时间：2026-03-19 07:42:46 +0800
- 角色：李白
- 任务描述：提交整理并合入 symbol_variable Farmat 链路。
- worktree：`/home/lfr/kernelcode_generate`
- 合并结果：
  - 已在 main 合入提交 `9d64328`。
- 变更文件：
  - `spec/symbol_variable/type.md`
  - `python/symbol_variable/type.py`
  - `test/symbol_variable/test_type.py`
- 测试说明：未复测（按任务要求默认不额外复测）。
