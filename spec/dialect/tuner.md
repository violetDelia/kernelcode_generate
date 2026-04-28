# tuner.md

## 功能简介

- 定义 `tuner` dialect 的超参数声明与成本节点接口。
- 本方言提供“声明超参数并生成符号标量”的 IR 表达，也提供 `tuner.cost` 作为 cost function 内的单 op 局部成本节点；不负责运行期求值、调度策略、搜索空间算法或真实 cost table。
- 超参数标量统一返回 `!symbol.dim<"name">`，与 `SymbolDim` 的符号维度语义保持一致；`tuner.cost` 固定返回 `!symbol.int<"expr">`。

## API 列表

- `tuner.param`
- `tuner.cost`

## 文档信息

- 创建者：`咯咯咯`
- 最后一次更改：`小李飞刀`
- `spec`：[`spec/dialect/tuner.md`](../../spec/dialect/tuner.md)
- `功能实现`：[`kernel_gen/dialect/tuner.py`](../../kernel_gen/dialect/tuner.py)
- `test`：
  - [`test/dialect/test_tuner_dialect.py`](../../test/dialect/test_tuner_dialect.py)
  - [`test/pass/test_launch_kernel_cost_func.py`](../../test/pass/test_launch_kernel_cost_func.py)

## 依赖

- [`spec/dialect/symbol.md`](../../spec/dialect/symbol.md)：提供符号整数/维度标量语义；`!symbol.dim<"name">` 作为超参数标量类型由 `symbol dialect` 维护。
- [`spec/symbol_variable/symbol_dim.md`](../../spec/symbol_variable/symbol_dim.md)：定义 `SymbolDim` 的运行时语义边界，供超参数标量语义对齐。
- [`spec/pass/tuning/launch_kernel_cost_func.md`](../pass/tuning/launch_kernel_cost_func.md)：消费 `tuner.cost` 作为 launch kernel cost function 的局部成本节点。

## 目标

- 在 IR 中提供统一的超参数声明入口。
- 在 IR 中提供统一的局部成本节点入口，使 pass 可把原 op 的 operands 与 attrs 映射为 `tuner.cost(...)->!symbol.int<"expr">`。
- 保持 `parse/print` 与 verifier 约束清晰，保证超参数名可稳定打印与校验。
- 当前 `tuner.cost.cost_kind` 的公开方向为任意非空字符串 attr。

## 限制与边界

- `tuner` dialect 当前公开 op 包含：
  - `tuner.param`
  - `tuner.cost`
- `tuner.param` 无 operand、无 region、单结果。
- `tuner.param` 结果类型必须为 `!symbol.dim<"name">`；不得使用 `!symbol.int<"...">`、builtin `index`、普通整数或其他类型替代。
- `name` 必须为非空标识符，且只能包含字母、数字与下划线，并以字母或下划线开头。
- `tuner.cost` 无 region，operand 列表按原 op operands 原顺序透传，结果类型固定为 `!symbol.int<"expr">`。
- `tuner.cost` 的 `cost_kind` 必须为非空字符串 attr，`op_name` 必须为非空字符串。
- `tuner.cost` 不再公开 `kind`、`device_func` 两个 attrs；若实现仍生成这两个字段，verifier 必须显式拒绝。
- `tuner.cost` 不求值、不查表、不裁剪节点；“不同 `cost_kind` 下某类 op 是否为 0”属于后续 evaluator 语义。
- 本方言不定义任何超参数值求解、范围约束、搜索策略、默认值逻辑或真实 cost evaluator。

## 公开接口

### `tuner.param`

功能说明：

- 声明一个超参数并返回对应的符号维度标量。

参数说明：

- 无参数。

使用示例：

```text
%tile_m = tuner.param : !symbol.dim<"BLOCK_M">
```

注意事项：

- `parse/print` 必须保持无 operand、单结果形式。
- verifier 必须拒绝任何非 `!symbol.dim<"name">` 的结果类型。
- `name` 为空或包含非法字符必须报错。

返回与限制：

- 返回类型：`!symbol.dim<"name">`
- 限制：不接受 `!symbol.int<"...">`、builtin `index` 或普通整数结果类型。

### `tuner.cost`

功能说明：

- 表示 cost function 内某个原 op 的局部成本。
- 该 op 只记录原 op operands、原 attrs 与 pass-owned metadata，并返回一个 `!symbol.int<"expr">` 局部成本值。

参数说明：

- `operands(SSA value...)`：原 op operands，数量与顺序必须与原 op 一致；原 op 无 operands 时本列表为空。
- `cost_kind(str attr)`：当前 cost function 的统计视角；允许任意非空字符串。
- `op_name(str attr)`：原 op 名称，例如 `"dma.copy"`、`"kernel.matmul"`、`"arch.barrier"`。

使用示例：

```text
%cost0 = tuner.cost(%tile_m, %k) {cost_kind = "memory", op_name = "dma.copy"} : (!symbol.int<"TILE_M">, !symbol.int<"K">) -> !symbol.int<"LOCAL">
%cost1 = tuner.cost() {cost_kind = "latency", op_name = "arch.barrier", scope = #arch.scope<global>} : () -> !symbol.int<"BARRIER_COST">
```

注意事项：

- `tuner.cost` 只传原 op operands，不额外插入摘要 operand。
- 原 op attributes 必须平铺保留；若原 op 已存在 `cost_kind / op_name` 任一同名 attr，生成方必须显式失败，不得覆盖或静默改名。
- 原 op 若存在业务字段 `kind`，生成方必须先改名为领域字段，例如 `kernel_kind`；`tuner.cost` 自身仍不公开旧 metadata attr `kind`。
- `cost_kind` 表示当前 cost function 的统计视角；是否保留节点、如何累计属于外层 pass 语义。
- 空串、全空白字符串不属于当前公开输入域。
- 本 op 不负责把局部成本汇总成函数返回值；汇总由外层 cost function 通过 `symbol.add` 与 `symbol.for` carried `!symbol.int<"...">` 完成。

返回与限制：

- 返回类型：固定单结果 `!symbol.int<"expr">`。
- 限制：无 region；不支持多结果；不公开 `kind`、`device_func` attrs。

## 测试

- 测试文件：[`test/dialect/test_tuner_dialect.py`](../../test/dialect/test_tuner_dialect.py)
- 执行命令：`pytest -q test/dialect/test_tuner_dialect.py -k "tuner_cost"`
- 测试目标：验证 `tuner.cost` 的 parse/print、operand 透传、`!symbol.int<"...">` 结果类型、open-kind verifier 与错误路径。

- 测试文件：[`test/pass/test_launch_kernel_cost_func.py`](../../test/pass/test_launch_kernel_cost_func.py)
- 执行命令：`pytest -q test/pass/test_launch_kernel_cost_func.py -k "launch_kernel_cost_func"`
- 测试目标：验证 `launch-kernel-cost-func` 消费 `tuner.cost` 时的 kind 口径与错误路径一致。

### 功能与用例清单

| 用例 ID | 约束点 | 对应测试 |
| --- | --- | --- |
| TC-TUNER-001 | `tuner.param` parse/print 与返回类型稳定 | `test_tuner_param_round_trip` |
| TC-TUNER-002 | `tuner.param` 结果类型必须为 `!symbol.dim<"name">` | `test_tuner_param_rejects_invalid_result_type` |
| TC-TUNER-003 | `tuner.param` 的 `name` 非法时报错 | `test_tuner_param_rejects_invalid_name` |
| TC-TUNER-004 | `tuner.cost` parse/print 与 operand 透传稳定，结果类型固定为 `!symbol.int<"...">` | `test_tuner_cost_round_trip` |
| TC-TUNER-005 | `tuner.cost.cost_kind` 必须是非空字符串，并拒绝旧 `kind / device_func` attrs | `test_tuner_cost_rejects_invalid_kind_attrs` |
| TC-TUNER-006 | `tuner.cost` 必须包含 `cost_kind / op_name`，且结果类型必须为 `!symbol.int<"...">` | `test_tuner_cost_rejects_missing_attrs_or_invalid_result_type` |
