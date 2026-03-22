# T-20260322-dd037de5

- 时间：2026-03-22 18:50:40 +0800
- 执行人：金铲铲大作战
- worktree：`/home/lfr/kernelcode_generate/wt-20260322-dialect-symbol-integer-only`

## 任务目标
- 基于 worktree 内 `spec/dialect/symbol.md`，新增/重构 `kernel_gen/dialect/symbol.py` 与 `test/dialect/test_symbol_dialect.py`。
- 收敛为只表示整数类型的 symbol type，不区分 `int8/int64` 等整型宽度。
- 补齐 verifier、parse/print、相等性与错误路径测试，确保测试映射闭环。

## 改动文件
- `wt-20260322-dialect-symbol-integer-only/kernel_gen/dialect/symbol.py`
- `wt-20260322-dialect-symbol-integer-only/test/dialect/test_symbol_dialect.py`

## 实现结果
- 新增 `SymbolExprAttr`，语法为 `#symbol.expr<"expr">`，支持非空、可打印、可比较的整数符号表达。
- 新增 `SymbolValueType`，语法为 `!symbol.int<"expr">`，只表示整数符号值语义，不再暴露宽度区分。
- verifier 收敛为：表达式不能为空，且只允许标识符、整数、空白与 `+/-/*`。
- parse/print round-trip 已补齐；legacy 宽度整型文本如 `!symbol.int64<...>` 会被拒绝。
- 相等性仅比较整数 symbol type 中的表达式内容。

## 测试闭环
- `TC-SYM-001/002/009`：`SymbolExprAttr` 基础/复合表达与 round-trip。
- `TC-SYM-003`：空表达式 verifier 错误。
- `TC-SYM-004/005/006/009`：整数 symbol type 的具名表达、复合表达、常量表达与 round-trip。
- `TC-SYM-007/008`：legacy 宽度整型文本与缺少表达式的错误路径。
- `TC-SYM-010/011/012`：相等性仅由表达式决定。
- 非法字符错误路径：补齐 attr/type 两条 verifier 路径。

## 说明
- worktree 中给定的 `spec/dialect/symbol.md` 仍保留了 `index/f32` 等更宽泛表述；本轮按任务明确要求，先将实现与测试收敛到“整数-only symbol type”口径。
- 建议下一阶段发起 spec 复审/修订任务，清理 `index/f32` 与旧用例描述，避免文档与实现继续分叉。

## 测试结果
- `cd /home/lfr/kernelcode_generate/wt-20260322-dialect-symbol-integer-only && pytest -q test/dialect/test_symbol_dialect.py`
- 结果：`6 passed`
- `cd /home/lfr/kernelcode_generate/wt-20260322-dialect-symbol-integer-only && pytest -q --cov=kernel_gen.dialect.symbol --cov-report=term-missing test/dialect/test_symbol_dialect.py`
- 结果：`6 passed`，`kernel_gen.dialect.symbol` 覆盖率 `100%`

## 下一步建议
- 先发起 spec 复审/改进任务，收敛 `spec/dialect/symbol.md` 到整数-only 口径。
- 随后再做实现复审，确认 dialect package 导出与上游调用链是否需要纳入同一链路。
