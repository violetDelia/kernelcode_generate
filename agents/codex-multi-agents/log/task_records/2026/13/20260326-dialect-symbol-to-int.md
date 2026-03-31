- 时间：`2026-03-26 00:29:35 +0800`
- 经手人：`睡觉小分队`
- 任务：`T-20260326-b46b0d8c`
- 任务目标：为 `symbol dialect` 新增 `symbol.to_int`（`!symbol.int<"expr"> -> 整型`，覆盖各整型变体），并补齐 `spec/实现/测试` 闭环；不修改 expectation。
- 改动：
  - 实现：更新 `kernel_gen/dialect/symbol.py`，新增 `SymbolToIntOp`（`name = "symbol.to_int"`），支持自定义 parse/print，verifier 约束 `source` 必须为 `!symbol.int<"expr">`、`result` 必须为 builtin `IntegerType`，并将该 op 注册到 `Symbol` dialect 与 `__all__`。
  - 规范：更新 `spec/dialect/symbol.md`，补充 `symbol.to_int` 的公开接口、参数/返回、边界约束、错误路径，以及测试目标与用例映射；同步收敛方言简介与转换能力边界描述。
  - 测试：更新 `test/dialect/test_symbol_dialect.py`，新增 3 个用例：
    - `test_symbol_to_int_verify_success_for_integer_variants`（`TC-SYM-042`）
    - `test_symbol_to_int_round_trip`（`TC-SYM-043`）
    - `test_symbol_to_int_rejects_invalid_types`（`TC-SYM-044`）
  - 未改动 `expectation/`。
  - 测试执行：`pytest -q test/dialect/test_symbol_dialect.py`，结果 `42 passed in 0.47s`。
- 结论：`symbol.to_int` 的 spec/实现/测试已完成最小闭环并通过现有 symbol dialect 测试，建议进入下一阶段复审。

时间: 2026-03-26 01:33:20 +0800
执行人: 小李飞刀
经办人: 小李飞刀
任务: T-20260326-ec24bcf3
任务目标: 复审 symbol.to_int 变更，只读核对 kernel_gen/dialect/symbol.py、spec/dialect/symbol.md、test/dialect/test_symbol_dialect.py；检查 TC-SYM-042/043/044 映射、整型变体验证与错误路径。
改动: 只读复审，无代码改动，无复测。
结论: 通过。
核对要点:
- spec/dialect/symbol.md 中 symbol.to_int 语义、parse/print 口径与实现一致；未出现 expectation 内容。
- SymbolToIntOp verifier 约束 source 为 !symbol.int<"expr"> 且 result 为 IntegerType；错误信息包含 op 名称与原因。
- TC-SYM-042/043/044 与测试用例一一对应：整型变体验证、parse/print round-trip、非法类型拒绝路径完整覆盖。
- kernel_gen/dialect/symbol.py 与 test/dialect/test_symbol_dialect.py 参数类型提示完备。
