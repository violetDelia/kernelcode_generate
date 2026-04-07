时间：2026-04-07 23:59:40 +0800
经办人：小李飞刀
任务：T-20260407-22566392
任务目标：在 symbol dialect 增加 symbol.const 的规格、实现与测试，并给出可复现验证命令。
改动：新增 SymbolConstOp 与 parse/print/verifier，补齐 spec 说明与测试用例，并更新测试清单。
结论：已完成，验证通过。
改动文件：
- kernel_gen/dialect/symbol.py
- spec/dialect/symbol.md
- test/dialect/test_symbol_dialect.py
验证命令：
- PYTHONPATH=. pytest -q test/dialect/test_symbol_dialect.py -k "symbol_const"
退出码：
- 0
关键输出：
- 3 passed, 46 deselected in 0.22s
已知风险：
- 未发现。
下一步建议：
- 进入审查，核对 spec/实现/测试一致性与错误信息覆盖。

---

时间：2026-04-08 00:08:00 +0800
经办人：不要啊教练
任务：T-20260407-32a82514（审查：symbol.const spec/实现/测试一致性）
worktree：wt-20260407-symbol-const-s1
任务目标：核对 symbol.const 的 spec/实现/测试一致性与验证记录是否可复现

结论：通过。

核对要点：
- spec（spec/dialect/symbol.md）对 symbol.const 的公开文本形式要求为：symbol.const <value> : !symbol.int<"...">；实现 print/parse 与测试 round-trip 均覆盖该形式。
- spec 要求 value 为整数；实现 parse 使用 parse_integer 且 allow_boolean=False、allow_negative=True，符合“仅整数、允许负数”的合同。
- spec 要求结果类型必须为 !symbol.int 且表达式与常量值一致；实现 verify_ 校验 result.type 为 SymbolValueType 且与 value 一致，并覆盖“结果类型不匹配”错误路径；测试覆盖匹配常量与不匹配场景。

验证（复跑，与记录一致）：
- PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/dialect/test_symbol_dialect.py -k "symbol_const"
  - 退出码：0
  - 关键输出：3 passed, 46 deselected in 0.19s

风险与备注：
- 未发现明显的越界、未校验输入或状态污染风险；当前实现仅引入整数常量 op，作用域清晰。

下一步建议：
- 进入合并阶段；合并时请确保包含记录中列出的 3 个改动文件与本记录文件。
