# 2026-03-22 T-20260322-227b97e4

- 任务目标：修正文档中默认连续 stride 的符号维度表达规则，并在测试目标/用例中标注覆盖。
- worktree：`/home/lfr/kernelcode_generate/wt-20260322-dialect-dma-spec-fix`
- 实际变更：
  - `spec/dialect/dma.md`
- 关键调整：
  - 补充默认连续 stride 在 `StringAttr` 符号维度（如 `N`/`M*N`/`?`）下的推导与退化语义，并强调仅用于默认连续 stride 推导，不替代显式 index operand 建模。
  - 在测试目标与用例表中标注默认连续 stride 规则已覆盖。
  - 更新文档信息“最后一次更改”。
- 测试：未执行（仅 spec 文档调整）。
- 结论：已完成，等待复审。
