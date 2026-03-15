# convert-from-cleanup-20260315 记录

## T-20260315-3635b7a3

- 时间：2026-03-15 20:20:54 +0800
- 角色：规格小队
- 任务描述：完成 convert_from_* 清理的 spec 阶段，更新相关 spec，明确移除 `symbol_dim` / `symbol_shape` / `memory` 中 `convert_from_*` 系列函数后的统一接口与命名。
- worktree：`wt-20260315-convert-from-cleanup`
- 产出文件：
  - `spec/symbol_variable/symbol_dim.md`
  - `spec/symbol_variable/symbol_shape.md`
  - `spec/symbol_variable/memory.md`
- 变更摘要：
  - 明确 `SymbolDim(value)` 取代 `SymbolDim.convert_from_int(value)`，并限定公开 API 不再暴露新的 `convert_from_*` 命名。
  - 明确 `SymbolShape(shapes)` 作为唯一公开形状归一化入口，移除 `SymbolList.convert_from_list` 的 spec 承诺。
  - 明确 `Memory(shape, dtype, ...)` 作为唯一公开构造入口，替代 `Memory.convert_from_tensor(tensor)`。
  - 为三处模块统一补充“构造器直入、私有 `_normalize_*` 负责内部规整”的命名规则。
  - 更新测试目标与用例清单，改为验证构造器入口和迁移路径，不再要求 `convert_from_*` 行为继续保留。
@规格小队向@神秘人发起会话: 已完成任务 T-20260315-3635b7a3，描述：完成 convert_from_* 清理 spec 收敛，统一 SymbolDim/SymbolShape/Memory 的公开输入入口改为构造器直入，worktree=wt-20260315-convert-from-cleanup，产出文件=spec/symbol_variable/symbol_dim.md,spec/symbol_variable/symbol_shape.md,spec/symbol_variable/memory.md，记录：agents/codex-multi-agents/log/task_records/2026/11/20260315-convert-from-cleanup.md。

## T-20260315-61a24d0d

- 时间：2026-03-15
- 角色：小李飞刀
- 任务描述：清理 convert_from_* 公开入口，统一构造器与内部规范化。
- worktree：`wt-20260315-convert-from-cleanup`
- 产出文件：
  - `symbol_variable/symbol_dim.py`
  - `symbol_variable/symbol_shape.py`
  - `symbol_variable/memory.py`
  - `test/symbol_variable/test_symbol_dim.py`
  - `test/symbol_variable/test_symbol_shape.py`
  - `test/symbol_variable/test_memory.py`
- 变更摘要：
  - 移除 `SymbolDim.convert_from_int`、`SymbolList.convert_from_list`、`Memory.convert_from_tensor` 公开入口。
  - `Memory` 内部新增 `_normalize_shape` 统一 shape/stride 规范化。
  - 测试改为构造器直入，补充 `SymbolShape(existing)` 与 `SymbolShape` 直入 `Memory` 用例。
- 测试：
  - `pytest -q test/symbol_variable/test_symbol_dim.py test/symbol_variable/test_symbol_shape.py test/symbol_variable/test_memory.py`（37 passed）
@小李飞刀向@神秘人发起会话: 已完成任务 T-20260315-61a24d0d：清理 convert_from_* 入口并更新实现/测试；worktree=wt-20260315-convert-from-cleanup；测试：pytest -q test/symbol_variable/test_symbol_dim.py test/symbol_variable/test_symbol_shape.py test/symbol_variable/test_memory.py（37 passed）；记录：agents/codex-multi-agents/log/task_records/2026/11/20260315-convert-from-cleanup.md。
@小李飞刀向@神秘人发起会话: 申请创建审查任务：实现文件在 symbol_variable/symbol_dim.py、symbol_variable/symbol_shape.py、symbol_variable/memory.py 与对应测试 test/symbol_variable/test_symbol_dim.py、test/symbol_variable/test_symbol_shape.py、test/symbol_variable/test_memory.py，请审查并记录到 agents/codex-multi-agents/log/task_records/2026/11/20260315-convert-from-cleanup.md；worktree=wt-20260315-convert-from-cleanup。


## 审查记录 T-20260315-857a79fe

任务 ID: T-20260315-857a79fe
审查时间: 2026-03-15 20:41:00 +0800
工作树: wt-20260315-convert-from-cleanup
审查范围:
- spec/symbol_variable/symbol_dim.md
- spec/symbol_variable/symbol_shape.md
- spec/symbol_variable/memory.md
- symbol_variable/symbol_dim.py
- symbol_variable/symbol_shape.py
- symbol_variable/memory.py
- test/symbol_variable/test_symbol_dim.py
- test/symbol_variable/test_symbol_shape.py
- test/symbol_variable/test_memory.py

结论: 通过

审查结论:
- `spec/symbol_variable/symbol_dim.md:31`、`spec/symbol_variable/symbol_shape.md:41`、`spec/symbol_variable/memory.md:38` 已统一要求公开构造入口分别收敛为 `SymbolDim(value)`、`SymbolShape(shapes)`、`Memory(...)`。当前实现中对应的公开 `convert_from_*` 已清理：`SymbolDim` 不再暴露 `convert_from_int`，`SymbolShape` / `SymbolList` 不再暴露 `convert_from_list`，`Memory` 不再暴露 `convert_from_tensor`。
- 当前实现保留的输入规整逻辑均已收敛到内部 `_normalize_*` 命名：`symbol_variable/symbol_dim.py` 使用 `_normalize_str` / `_normalize_operand` / `_normalize_symbol`，`symbol_variable/symbol_shape.py` 使用 `_normalize_value`，`symbol_variable/memory.py` 使用 `_normalize_shape`，符合本轮“公开入口收敛、内部 normalize 复用”的目标。
- 目标测试文件已同步迁移到直接构造器入口：`test/symbol_variable/test_symbol_dim.py` 直接使用 `SymbolDim(32)`；`test/symbol_variable/test_symbol_shape.py` 直接使用 `SymbolShape(existing_shape)`；`test/symbol_variable/test_memory.py` 直接用 `Memory(t.shape, t.dtype, stride=t.stride, format=t.format)` 替代旧的 `convert_from_tensor` 路径。
- 运行时抽查确认：`hasattr(SymbolDim, "convert_from_int") == False`、`hasattr(SymbolShape, "convert_from_list") == False`、`hasattr(Memory, "convert_from_tensor") == False`；同时 `SymbolShape(existing_shape)` 可构造等价新对象，`Memory(existing_shape, dtype, stride=existing_stride)` 可直接接收已归一化输入。

验证记录:
- 执行 `pytest -q wt-20260315-convert-from-cleanup/test/symbol_variable/test_symbol_dim.py wt-20260315-convert-from-cleanup/test/symbol_variable/test_symbol_shape.py wt-20260315-convert-from-cleanup/test/symbol_variable/test_memory.py`，结果 `37 passed`。

## 合并记录 T-20260315-6e78d896

- 时间：2026-03-15 20:49:43 +0800
- 角色：合并小队
- 目标分支：main
- 源分支：wt-20260315-convert-from-cleanup
- 合并方式：fast-forward
- 合并提交：6439cab
- worktree：wt-20260315-convert-from-cleanup（已删除）
- 变更范围：
  - spec/symbol_variable/symbol_dim.md
  - spec/symbol_variable/symbol_shape.md
  - spec/symbol_variable/memory.md
  - symbol_variable/symbol_dim.py
  - symbol_variable/symbol_shape.py
  - symbol_variable/memory.py
  - test/symbol_variable/test_symbol_dim.py
  - test/symbol_variable/test_symbol_shape.py
  - test/symbol_variable/test_memory.py
- 清理前检查：已核对 TODO.md，仅存在当前合并任务，无其他进行中任务。
- 备注：合并前已暂存 main 分支的 spec/symbol_variable/memory.md 变更（stash: "tmp memory md for convert_from merge"）。
