# T-20260322-45c4c0c4

## 基本信息

- 任务 ID：`T-20260322-45c4c0c4`
- 任务类型：`spec 改进`
- worktree：`/home/lfr/kernelcode_generate/wt-20260322-dialect-symbol-integer-only`
- 记录人：`睡觉小分队`

## 任务目标

- 先修订 `spec/dialect/symbol.md`
- 将 `symbol dialect` 收敛为整数-only 口径
- 不再区分 `int/int8/int16/int32/int64` 等具体宽度
- 移除 `index/f16/bf16/f32/f64` 等非整形表述
- 本轮只改 spec，不改实现/测试

## 审查基线

- 已对照：
  - `wt-20260322-dialect-symbol-integer-only/spec/dialect/symbol.md`
  - `wt-20260322-dialect-symbol-integer-only/kernel_gen/dialect/symbol.py`
  - `wt-20260322-dialect-symbol-integer-only/test/dialect/test_symbol_dialect.py`
- 当前实现/测试基线已经收敛到：
  - `#symbol.expr<"expr">`
  - `!symbol.int<"expr">`
  - 整数-only 语义

## 本次修改

### `wt-20260322-dialect-symbol-integer-only/spec/dialect/symbol.md`

- 将功能简介收敛为“带符号值语义的整型标量”
- 移除 `index/f16/bf16/f32/f64` 等非整形能力表述
- 移除“基础类型 + 符号值语义”的旧口径，改为固定整数语义
- 将正式文本语法收敛为：
  - `#symbol.expr<"expr">`
  - `!symbol.int<"expr">`
- 将类型校验规则收敛为：
  - 仅校验整数-only `SymbolValueType`
  - 不再区分整型宽度
  - 非法表达式、空表达式必须报错
- 将额外补充收敛为整数-only 基线，不再保留非整型扩张描述
- 将测试目标与功能用例清单映射到真实测试名：
  - `test_symbol_expr_attr_round_trip`
  - `test_symbol_expr_attr_rejects_empty_expr`
  - `test_symbol_value_type_round_trip_for_integer_only_semantics`
  - `test_symbol_value_type_rejects_unsupported_legacy_text_forms`
  - `test_symbol_value_type_equality_depends_on_expr_only`
  - `test_symbol_verifier_rejects_illegal_expression_characters`

### 补充修订：常量整数值语义

- 根据用户补充确认，已进一步在 `spec/dialect/symbol.md` 中明确：
  - `!symbol.int<"1">`
  - `!symbol.int<"2">`
  - `!symbol.int<"3">`
  均为合法的整数值语义表达
- 已在以下章节补充这一口径：
  - `术语`
  - `限制与边界`
  - `公开接口 -> SymbolExprAttr`
  - `公开接口 -> SymbolValueType`
  - `公开接口 -> 类型校验规则`
  - `额外补充`
- 当前 spec 明确：`symbol` 不仅表示具名符号，也表示已知的整型常量值

## 未修改内容

- 未修改 `kernel_gen/dialect/symbol.py`
- 未修改 `test/dialect/test_symbol_dialect.py`

## 结果

- `spec/dialect/symbol.md` 已收敛到当前用户要求的整数-only 口径
- 当前 spec 与现有实现/测试在文本语法与测试映射上已对齐
- 本轮无实现/测试改动

## 测试情况

- 未运行测试
- 原因：任务明确要求本轮只改 spec 与记录，不改实现/测试

## 下一步建议

- 当前按管理员补充要求继续停留在 spec 修订阶段
- 暂不进入复审，等待下一条分发指令
