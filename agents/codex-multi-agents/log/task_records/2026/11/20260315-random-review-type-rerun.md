# random-review-type-rerun-20260315 记录

## 巡检记录 T-20260315-63c0956b

- 时间: 2026-03-15 23:05:00 +0800
- 角色: 巡检小队
- worktree: `main`
- 工作区路径: `/home/lfr/kernelcode_generate`
- 巡检范围:
  - `symbol_variable/type.py`
  - `symbol_variable/__init__.py`
- 验证:
  - `pytest -q test/symbol_variable/test_memory.py` -> `7 passed in 0.14s`
  - `from symbol_variable.type import *` -> 暴露 `Enum`、`Farmat`、`NumericType`、`annotations`
  - `import symbol_variable` -> 顶层未导出 `NumericType`、`Farmat`

巡检结论:
- 当前实现与现有 `memory` 相关测试一致，未发现会直接导致现有测试失败的显性错误。
- 发现两类可维护性风险，建议后续发起收敛型重构。

风险清单:
- 中: `symbol_variable/__init__.py` 将自己描述为“符号维度、形状与内存相关类型的统一导入入口”，并导出 `Memory` / `MemorySpace`，但没有同时导出构造 `Memory` 时高频配套使用的 `NumericType` / `Farmat`。这会让调用方必须在包根入口与 `symbol_variable.type` 子模块之间来回切换，形成分裂的导入习惯。
- 低: `symbol_variable/type.py` 没有显式定义公共导出列表，`from symbol_variable.type import *` 会额外泄露 `Enum` 和 `annotations`。这会让模块公共接口边界依赖实现细节，不利于后续收敛。
- 低: `type.py` 中的公开类型名 `Farmat` 带有拼写债务。当前 spec、测试和调用方都已围绕这个名字建立约定，因此它不是立即缺陷，但会持续抬高理解和沟通成本。

改进建议:
- 明确 `symbol_variable` 包根是否承担统一导入入口职责；如果承担，应把 `NumericType` / `Farmat` 一并纳入包根导出，并补充相应回归测试。
- 为 `symbol_variable/type.py` 增加显式公共接口边界，例如补 `__all__ = ["NumericType", "Farmat"]`，避免无关名字进入通配导入结果。
- 针对 `Farmat` 的命名债务，单独规划兼容性重构：优先引入正确拼写别名和迁移文档，再决定是否逐步废弃旧名，避免直接硬改破坏现有调用方。

重构申请: 收敛 symbol_variable 类型模块公开接口
范围: symbol_variable/type.py, symbol_variable/__init__.py, test/symbol_variable/test_memory.py
原因: 包根导出面与子模块公开接口边界不清晰，增加调用方心智负担并放大后续演进成本
建议方式: 明确包根导出策略；若保留统一入口则补充 NumericType/Farmat 导出与测试；为 type.py 增加显式 __all__；评估 Farmat 命名债务的兼容迁移方案
优先级: 中
