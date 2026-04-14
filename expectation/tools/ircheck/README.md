# ircheck expectation README

## 文档信息

- 创建者：`睡觉小分队`
- 最后一次更改：`睡觉小分队`
- `spec`：[`spec/tools/ircheck.md`](../../../spec/tools/ircheck.md)
- `test`：
  - [`test/tools/test_ircheck_parser.py`](../../../test/tools/test_ircheck_parser.py)
  - [`test/tools/test_ircheck_matcher.py`](../../../test/tools/test_ircheck_matcher.py)
  - [`test/tools/test_ircheck_runner.py`](../../../test/tools/test_ircheck_runner.py)
- `功能实现`：[`kernel_gen/tools/ircheck.py`](../../../kernel_gen/tools/ircheck.py)

## 功能说明

- 汇总 `expectation/tools/ircheck` 目录下的样例入口，说明哪些样例验证基础 `CHECK*` 子串合同，哪些样例验证 `CHECK-REGEX*` 与变量捕获合同。
- 统一 expectation 侧的写法口径：稳定公开 API 只有 `parse_ircheck_file`、`run_ircheck_file`、`run_ircheck_text`。
- 给出一段可直接迁移到 expectation 的 regex/variable 最小示例，避免执行人猜测方括号转义与 `[[NAME:REGEX]]` 的边界。

## 使用示例

- `PYTHONPATH=. python expectation/tools/ircheck/basic_true.py`
- `PYTHONPATH=. python expectation/tools/ircheck/basic_false.py`
- `PYTHONPATH=. python expectation/tools/ircheck/check_next_false.py`
- `PYTHONPATH=. python expectation/tools/ircheck/regex_variable_true.py`（`S2` 预期新增）
- `PYTHONPATH=. python expectation/tools/ircheck/regex_variable_false.py`（`S2` 预期新增）

## 样例清单

- [`expectation/tools/ircheck/basic_true.py`](../../../expectation/tools/ircheck/basic_true.py)：基础成功路径，验证 `CHECK:` / `CHECK-NOT:` / `CHECK-NEXT:` 组合语义。
- [`expectation/tools/ircheck/basic_false.py`](../../../expectation/tools/ircheck/basic_false.py)：基础失败路径，验证 `IrcheckMatchError: CHECK not found`。
- [`expectation/tools/ircheck/check_next_false.py`](../../../expectation/tools/ircheck/check_next_false.py)：相邻行失败路径，验证 `IrcheckMatchError: CHECK-NEXT not found on next line`。
- [`expectation/tools/ircheck/multi_pass_true.py`](../../../expectation/tools/ircheck/multi_pass_true.py)：多 step 成功路径。
- [`expectation/tools/ircheck/multi_pass_fail.py`](../../../expectation/tools/ircheck/multi_pass_fail.py)：step 失败定位与 `actual_ir` 合同。
- [`expectation/tools/ircheck/ir_dump_true.py`](../../../expectation/tools/ircheck/ir_dump_true.py)：`-irdump` 目录与文件命名合同。
- `expectation/tools/ircheck/regex_variable_true.py`（`S2` 预期新增）：正则 + 变量捕获/复用成功路径。
- `expectation/tools/ircheck/regex_variable_false.py`（`S2` 预期新增）：正则 + 变量写法失败路径与稳定错误短语。

## regex / variable 写法

- `CHECK:` / `CHECK-NEXT:` / `CHECK-NOT:` 继续用于固定文本的逐行子串匹配。
- `CHECK-REGEX:` / `CHECK-NEXT-REGEX:` / `CHECK-NOT-REGEX:` 用于需要正则匹配或变量复用的场景。
- `[[NAME:REGEX]]` 表示“在本条 positive regex check 中定义变量 `NAME` 并捕获该段文本”。
- `[[NAME]]` 表示“引用先前已捕获的变量 `NAME`，按字面量匹配”。
- `CHECK-NOT-REGEX:` 只允许引用已有变量，不允许定义新变量。
- `[[NAME:REGEX]]` / `[[NAME]]` 仅表示 ircheck 变量占位；IR 自身的字面量 `[` / `]` 仍需单独写作 `\[` / `\]`。
- 内置别名只在 `[[NAME:REGEX]]` 的 `REGEX` 段内展开：
  - `{reg}`：`[A-Za-z_][A-Za-z0-9_]*`
  - `{dim}`：`[1-9][0-9]*`
  - `{int}`：`-?[0-9]+`

## 最小示例

```text
// COMPILE_ARGS: --pass lower-nn
// CHECK-REGEX: func.func @exp_kernel\(%arg0 : !nn.memory<\[[[M:{dim}]], [[N:{dim}]]\], \[[[N]], 1\], f32, #nn.space<global>>\) -> !nn.memory<\[[[M]], [[N]]\], \[[[N]], 1\], f32, #nn.space<global>>
// CHECK-NEXT-REGEX: "dma.alloc"() .* -> !nn.memory<\[[[M]], [[N]]\], \[[[N]], 1\], f32, #nn.space<global>>
// CHECK-NOT-REGEX: nn\.exp

builtin.module {
  func.func @exp_kernel(%arg0 : !nn.memory<[8, 16], [16, 1], f32, #nn.space<global>>) -> !nn.memory<[8, 16], [16, 1], f32, #nn.space<global>> {
    %0 = "dma.alloc"() : () -> !nn.memory<[8, 16], [16, 1], f32, #nn.space<global>>
    func.return %0 : !nn.memory<[8, 16], [16, 1], f32, #nn.space<global>>
  }
}
```

## 迁移建议

- 旧 expectation 若只断言固定字符串，直接保留或迁移为 `CHECK*` 子串指令即可，不需要强行改成 regex。
- 当维度、符号名或 SSA 名由随机值生成时，再引入 `CHECK-REGEX*` 与 `[[NAME:REGEX]]` / `[[NAME]]`。
- expectation 文档、脚本和测试都应只把 `parse_ircheck_file`、`run_ircheck_file`、`run_ircheck_text` 当作稳定合同；不要依赖 `kernel_gen.tools.ircheck` 的内部辅助函数。
