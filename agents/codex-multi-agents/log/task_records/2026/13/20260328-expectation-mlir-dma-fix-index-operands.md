时间：2026-03-28 06:25:39 +0800
经手人：小李飞刀
任务：T-20260328-48b9825d
任务目标：按审查意见修复 _resolve_index_operand/_cast_to_symbol_int 类型校验并补负例测试。
改动：
- kernel_gen/dsl/emit_mlir.py：_cast_to_symbol_int 仅允许 IndexType/IntegerType 或 SymbolValueType，非法类型直接报错。
- test/dsl/test_ast_visitor.py：新增 index operand 非整数 SSA value 的负例覆盖。
测试：
- pytest -q test/dsl/test_ast_visitor.py -k test_emit_mlir_index_operand_rejects_non_integer_symbol
  - 结果：1 passed, 178 deselected
结论：实现与补测完成；等待 -done 与新建审查任务。

时间：2026-03-28 06:28:54 +0800
经手人：我不是牛马
任务：T-20260328-35edd44c
任务目标：审查 index operand 类型校验修复与负例覆盖，覆盖功能正确性、边界条件、异常路径、潜在漏洞与可维护性。
改动：
- 代码未修改。
- 复核 kernel_gen/dsl/emit_mlir.py 中 `_cast_to_symbol_int` 的类型校验与 `_resolve_index_operand` 调用链，确认对非整数 SSA value（含 memory/float）拒绝。
- 复核 test/dsl/test_ast_visitor.py 新增负例覆盖，验证非整数 SSA value 触发 `_LoweringError`。
- 复测 `pytest -q test/dsl/test_ast_visitor.py -k test_emit_mlir_index_operand_rejects_non_integer_symbol`，退出码 0（1 passed, 178 deselected）。
结论：通过。功能正确性、边界条件、异常路径、潜在漏洞与可维护性已审查，未发现问题或改进项。
