# 20260318-code-inspection-two-improvements

- 任务: T-20260318-b0ae0a24
- 执行人: 不要啊教练
- worktree: /home/lfr/kernelcode_generate
- 时间: 2026-03-18 01:40:10 +0800

## 巡检范围
- 仅检查 spec/、python/、test/ 下的在途改动（不审查 skills 目录）。
- 聚焦 spec、实现、测试之间的收敛缺口与一致性风险。

## 发现问题与改进建议

### 1) spec 冲突标记残留（阻塞）
- 问题: `spec/dsl/ast_visitor.md` 出现未解决的 merge conflict 标记（`<<<<<<<`/`=======`/`>>>>>>>`）。
- 影响: 文档语义断裂，示例与约束不可判读，后续实现/测试对齐将被误导；同时阻塞任何依赖 spec 的审查或生成流程。
- 涉及文件:
  - spec: `spec/dsl/ast_visitor.md`
  - 实现: `python/dsl/ast_visitor.py`
  - 测试: `test/dsl/test_ast_visitor.py`
- 建议: 创建“修复 spec 冲突”任务，清理冲突标记并确认示例文本与现有实现/测试保持一致；必要时补充/调整 spec 的示例与测试清单映射。
- 优先级: 阻塞问题
- 建议角色: 管理员
- 建议阶段: spec

### 2) SymbolShape 规约过度简化导致 spec/实现/测试语义漂移（普通缺陷）
- 问题: `spec/symbol_variable/symbol_shape.md` 的描述被简化为泛化语句，缺少 `SymbolShape` 的公开行为约束（如索引/切片、越界错误、repr/序列化语义），与 `python/symbol_variable/symbol_shape.py` 的实际行为及 `test/symbol_variable/test_symbol_shape.py` 的断言覆盖不匹配。
- 影响: spec 无法作为实现与测试的稳定契约，后续重构容易破坏既有行为而不自知；测试与 spec 也难以一一映射。
- 涉及文件:
  - spec: `spec/symbol_variable/symbol_shape.md`
  - 实现: `python/symbol_variable/symbol_shape.py`
  - 测试: `test/symbol_variable/test_symbol_shape.py`
- 建议: 创建“补齐 SymbolShape 规范”任务，补充 API 行为边界（索引/切片/错误语义/表示形式）与测试映射清单，确保与当前实现与测试一致。
- 优先级: 普通缺陷
- 建议角色: 管理员
- 建议阶段: spec

## 备注
- 已避开 `dialect nn`、`memory`、`symbol_dim`、`type` 等已有在途任务记录，避免重复提案。
