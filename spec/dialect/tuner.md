# tuner.md

## 功能简介

- 定义 `tuner` dialect 的超参数声明接口。
- 本方言只提供“声明超参数并生成符号标量”的 IR 表达，不负责运行期求值、调度策略或搜索空间算法。
- 超参数标量统一返回 `!symbol.int<"name">`，与 `SymbolDim` 的符号整数语义保持一致。

## 文档信息

- 创建者：`咯咯咯`
- 最后一次更改：`金铲铲大作战`
- `spec`：[`spec/dialect/tuner.md`](../../spec/dialect/tuner.md)
- `功能实现`：[`kernel_gen/dialect/tuner.py`](../../kernel_gen/dialect/tuner.py)
- `test`：[`test/dialect/test_tuner_dialect.py`](../../test/dialect/test_tuner_dialect.py)

## 依赖

- [`spec/dialect/symbol.md`](../../spec/dialect/symbol.md)：提供符号整数标量语义；`!symbol.int<"name">` 作为超参数标量类型由 `symbol dialect` 维护。
- [`spec/symbol_variable/symbol_dim.md`](../../spec/symbol_variable/symbol_dim.md)：定义 `SymbolDim` 的运行时语义边界，供超参数标量语义对齐。

## 目标

- 在 IR 中提供统一的超参数声明入口。
- 保持 `parse/print` 与 verifier 约束清晰，保证超参数名可稳定打印与校验。
- 为后续实现与测试提供最小闭环的测试清单。

## 限制与边界

- `tuner` dialect 仅包含一个公开 op：`tuner.param`。
- `tuner.param` 无 operand、无 region、单结果。
- 结果类型必须为 `!symbol.int<"name">`；不得使用 builtin `index`、普通整数或其他类型替代。
- `name` 必须为非空标识符，且只能包含字母、数字与下划线，并以字母或下划线开头。
- 本方言不定义任何超参数值求解、范围约束、搜索策略或默认值逻辑；仅声明符号标量。

## 公开接口

### `tuner.param`

功能说明：

- 声明一个超参数并返回对应的符号维度标量。

参数说明：

- 无参数。

使用示例：

```text
%tile_m = tuner.param : !symbol.int<"BLOCK_M">
```

注意事项：

- `parse/print` 必须保持无 operand、单结果形式。
- verifier 必须拒绝任何非 `!symbol.int<"name">` 的结果类型。
- `name` 为空或包含非法字符必须报错。

返回与限制：

- 返回类型：`!symbol.int<"name">`
- 限制：不接受 builtin `index` 或普通整数结果类型。

## 测试

- 测试文件：[`test/dialect/test_tuner_dialect.py`](../../test/dialect/test_tuner_dialect.py)
- 执行命令：`pytest -q test/dialect/test_tuner_dialect.py`

### 测试目标

- 验证 `tuner.param` 的 parse/print round-trip 以及返回类型稳定性。
- 验证 `tuner.param` 对非法类型与非法 `name` 的错误路径。

### 功能与用例清单

| 用例 ID | 约束点 | 对应测试 |
| --- | --- | --- |
| TC-TUNER-001 | `tuner.param` parse/print 与返回类型稳定 | `test_tuner_param_round_trip` |
| TC-TUNER-002 | `tuner.param` 结果类型必须为 `!symbol.int<"name">` | `test_tuner_param_rejects_invalid_result_type` |
| TC-TUNER-003 | `tuner.param` 的 `name` 非法时报错 | `test_tuner_param_rejects_invalid_name` |
