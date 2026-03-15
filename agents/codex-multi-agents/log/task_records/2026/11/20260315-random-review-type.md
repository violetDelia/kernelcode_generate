# random-review-type-20260315 记录

## 审查记录 T-20260315-5ee8d9ee

- 时间: 2026-03-15 23:00:00 +0800
- 角色: 巡检小队
- worktree: `wt-20260315-random-review-type`
- 审查范围:
  - `symbol_variable/type.py`
  - `symbol_variable/__init__.py`
- 审查限制:
  - 任务单登记的 `wt-20260315-random-review-type` 未出现在 `git worktree list`，实际目录也不存在。
  - 本次仅能基于主工作区对应文件做只读静态检查，无法确认是否与任务预期副本完全一致。
- 验证:
  - `git worktree list`
  - `pytest -q test/symbol_variable/test_memory.py` -> `7 passed in 0.16s`

结论: 不通过

问题清单:
- 高: 任务指定的 `worktree` 缺失，当前无法在目标副本上完成确定性审查。这会导致审查对象与任务登记对象不一致，后续即使给出结论，也不能保证覆盖到管理员实际想检查的那份代码。
- 中: [`symbol_variable/__init__.py`](/home/lfr/kernelcode_generate/symbol_variable/__init__.py#L26) 作为包级“统一导入入口”，导出了 `Memory` / `MemorySpace`，却没有同时导出构造 `Memory` 必需的 `NumericType` / `Farmat`。这使顶层 API 面不完整，调用方必须额外记住 `symbol_variable.type` 这一特例，容易造成导入方式分裂。
- 低: [`symbol_variable/__init__.py`](/home/lfr/kernelcode_generate/symbol_variable/__init__.py#L6) 的模块说明宣称提供“内存相关类型的统一导入入口”，但关联文件和示例没有覆盖 [`symbol_variable/type.py`](/home/lfr/kernelcode_generate/symbol_variable/type.py#L1)，文档表达与实际暴露面不完全一致，后续继续扩展时容易加重认知成本。

风险说明:
- 最大风险不是当前测试失败，而是任务流程与审查对象脱节：缺失 worktree 会让结论失去可追踪性。
- 其次是包根导出不完整会放大调用习惯分叉，后续如果继续增加 `type.py` 中的枚举或类型，外部接口会越来越碎片化。

建议修复项:
- 先补齐或更正任务所指向的 `worktree`，再基于目标副本重新执行一次随机审查。
- 明确 `symbol_variable` 包根是否承担统一导出职责；如果承担，应把 `NumericType` / `Farmat` 一并导出并补测试。
- 若不打算在包根导出 `type.py` 中的枚举，则应收敛 [`symbol_variable/__init__.py`](/home/lfr/kernelcode_generate/symbol_variable/__init__.py#L6) 文案，避免“统一导入入口”的表述误导调用方。

重构申请: 收敛 symbol_variable 顶层导出面
范围: symbol_variable/__init__.py, symbol_variable/type.py, test/symbol_variable/test_memory.py
原因: 包级导出面不完整，文档与实际使用路径分裂，增加调用方心智负担
建议方式: 明确包根导出策略；若保留统一入口，则补充 NumericType/Farmat 导出与回归测试；否则调整包文档与示例
优先级: 中
