# 主动巡检 2026-03-16

## PR-001 旧路径删除回归覆盖不足

- 背景：`spec/symbol_variable/package_api.md` 已明确 `python.symbol_variable` 为唯一有效入口，旧路径 `symbol_variable.*` 不再兼容；但 `test/symbol_variable/test_package_api.py` 目前仅验证 `importlib.import_module("symbol_variable")` 失败，未锁定代表性的旧子模块路径。
- 涉及文件：
  - `spec/symbol_variable/package_api.md`
  - `test/symbol_variable/test_package_api.py`
- 影响范围：若后续误恢复 `symbol_variable/symbol_dim.py` 或 `symbol_variable/memory.py` 一类旧子模块，即便顶层包仍不可导入，局部旧路径回归风险也缺少直接测试约束。
- 建议改法：在 `test/symbol_variable/test_package_api.py` 中补充对 `symbol_variable.symbol_dim`、`symbol_variable.symbol_shape`、`symbol_variable.memory` 至少一到两个代表性旧子模块路径的失败断言，并在 `spec/symbol_variable/package_api.md` 的测试目标中同步写明旧路径子模块不可导入。
- 优先级：中

## PR-002 type 模块缺少旧路径移除回归锁定

- 背景：`spec/symbol_variable/type.md:22` 已明确 `symbol_variable.type` 不再兼容，但 `test/symbol_variable/test_type.py` 当前只验证新路径枚举值、别名和 `__all__`，没有直接锁定旧路径删除行为。
- 涉及文件：
  - `spec/symbol_variable/type.md`
  - `test/symbol_variable/test_type.py`
- 影响范围：如果后续误恢复 `symbol_variable/type.py`，现有 type 测试不会直接报警，type 模块的迁移边界将退化为“文档声明删除，但测试未锁定”。
- 建议改法：在 `test/symbol_variable/test_type.py` 中新增 `importlib.import_module("symbol_variable.type")` 失败断言，并在 `spec/symbol_variable/type.md` 的测试目标中补充“旧路径 type 不可导入”的回归要求。
- 优先级：中

## PR-003 文件元数据与文档结构仍有一致性问题

- 背景：`python/symbol_variable/__init__.py` 作为包入口实现文件，其头部 `关联文件` 中的 `功能实现` 当前全部指向子模块文件而不是自身；同时 `spec/symbol_variable/type.md` 出现重复的 `## 返回与错误` 标题，文档结构有明显重复。
- 涉及文件：
  - `python/symbol_variable/__init__.py`
  - `spec/symbol_variable/type.md`
- 影响范围：会削弱文件元数据的可追溯性，增加维护者定位“该文件对应哪个实现对象”的成本；重复标题也会影响 spec 可读性和后续审查判断。
- 建议改法：将 `python/symbol_variable/__init__.py` 头部的 `功能实现` 至少补回自身文件链接，并视需要将子模块链接降级为“关联实现”；同时清理 `spec/symbol_variable/type.md` 中重复的 `## 返回与错误` 标题，保持单一结构。
- 优先级：低

- 本轮说明：主动静态巡检，未执行测试。

## 已申请改进任务

- 2026-03-16 04:08 +0800：已向管理员提交 PR-001 改进申请，请求围绕 `spec/symbol_variable/package_api.md` 与 `test/symbol_variable/test_package_api.py` 新建任务，补齐旧子模块删除回归与 API 示例。
- 2026-03-16 04:08 +0800：已向管理员提交 PR-002 改进申请，请求围绕 `spec/symbol_variable/type.md` 与 `test/symbol_variable/test_type.py` 新建任务，补齐旧路径删除回归与 API 示例。
- 2026-03-16 04:08 +0800：已向管理员提交 PR-003 改进申请，请求围绕 `python/symbol_variable/__init__.py` 与 `spec/symbol_variable/type.md` 新建任务，修复文件头元数据、重复标题与 API 示例不足问题。
