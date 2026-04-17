# tuner.md

## 功能简介

- 定义 `tuner` dialect 的超参数声明与成本节点接口。
- 本方言提供“声明超参数并生成符号标量”的 IR 表达，也提供 `tuner.cost` 作为 cost function 内的单 op 局部成本节点；不负责运行期求值、调度策略、搜索空间算法或真实 cost table。
- 超参数标量统一返回 `!symbol.dim<"name">`，与 `SymbolDim` 的符号维度语义保持一致；`tuner.cost` 固定返回 `f64`。

## 文档信息

- 创建者：`咯咯咯`
- 最后一次更改：`睡觉小分队`
- `spec`：[`spec/dialect/tuner.md`](../../spec/dialect/tuner.md)
- `功能实现`：[`kernel_gen/dialect/tuner.py`](../../kernel_gen/dialect/tuner.py)
- `test`：[`test/dialect/test_tuner_dialect.py`](../../test/dialect/test_tuner_dialect.py)

## 依赖

- [`spec/dialect/symbol.md`](../../spec/dialect/symbol.md)：提供符号整数/维度标量语义；`!symbol.dim<"name">` 作为超参数标量类型由 `symbol dialect` 维护。
- [`spec/symbol_variable/symbol_dim.md`](../../spec/symbol_variable/symbol_dim.md)：定义 `SymbolDim` 的运行时语义边界，供超参数标量语义对齐。
- [`spec/pass/tuning/launch_kernel_cost_func.md`](../pass/tuning/launch_kernel_cost_func.md)：消费 `tuner.cost` 作为 launch kernel cost function 的局部成本节点。

## 目标

- 在 IR 中提供统一的超参数声明入口。
- 在 IR 中提供统一的局部成本节点入口，使 pass 可把原 op 的 operands 与 attrs 映射为 `tuner.cost(...)->f64`。
- 保持 `parse/print` 与 verifier 约束清晰，保证超参数名可稳定打印与校验。
- 为后续实现与测试提供最小闭环的测试清单。

## 限制与边界

- `tuner` dialect 当前公开 op 包含：
  - `tuner.param`
  - `tuner.cost`
- `tuner.param` 无 operand、无 region、单结果。
- `tuner.param` 结果类型必须为 `!symbol.dim<"name">`；不得使用 `!symbol.int<"...">`、builtin `index`、普通整数或其他类型替代。
- `name` 必须为非空标识符，且只能包含字母、数字与下划线，并以字母或下划线开头。
- `tuner.cost` 无 region，operand 列表按原 op operands 原顺序透传，结果类型固定为 `f64`。
- `tuner.cost` 的 `kind` 只接受 `compute` 或 `move`，`cost_kind` 只接受 `compute`、`move` 或 `all`，`op_name` 必须为非空字符串，`device_func` 必须为 `SymbolRefAttr`。
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
- 该 op 只记录原 op operands、原 attrs 与 pass-owned metadata，并返回一个 `f64` 局部成本值。

参数说明：

- `operands(SSA value...)`：原 op operands，数量与顺序必须与原 op 一致；原 op 无 operands 时本列表为空。
- `kind(str attr)`：原 op 自身的成本类别，当前只允许 `"compute"` 或 `"move"`。
- `cost_kind(str attr)`：当前 cost function 的统计视角，只允许 `"compute"`、`"move"` 或 `"all"`。
- `op_name(str attr)`：原 op 名称，例如 `"dma.alloc"`、`"kernel.matmul"`、`"arch.barrier"`。
- `device_func(symbol attr)`：当前 cost function 对应的 device callee symbol。

使用示例：

```text
%cost0 = tuner.cost(%tile_m, %k) {kind = "move", cost_kind = "all", op_name = "dma.alloc", device_func = @_device_matmul_kernel_} : (!symbol.int<"TILE_M">, !symbol.int<"K">) -> f64
%cost1 = tuner.cost() {kind = "move", cost_kind = "move", op_name = "arch.barrier", device_func = @_device_shared_kernel_, scope = #arch.scope<global>} : () -> f64
```

注意事项：

- `tuner.cost` 只传原 op operands，不额外插入摘要 operand。
- 原 op attributes 必须平铺保留；若原 op 已存在 `kind / cost_kind / op_name / device_func` 任一同名 attr，生成方必须显式失败，不得覆盖或静默改名。
- `kind` 与 `cost_kind` 分工固定：
  - `kind` 表示原 op 属于 `compute` 还是 `move`；
  - `cost_kind` 表示当前 cost function 的统计视角。
- `cost_kind="compute"` 时仍保留 `kind="move"` 的 `tuner.cost` 节点；`cost_kind="move"` 时仍保留 `kind="compute"` 的 `tuner.cost` 节点。
- 本 op 不负责把局部成本汇总成函数返回值；汇总由外层 cost function 通过 `arith.addf` 与 `symbol.for` carried `f64` 完成。

返回与限制：

- 返回类型：固定单结果 `f64`。
- 限制：无 region；不支持多结果；不支持 `kind="all"`，`all` 只能出现在 `cost_kind`。

## 测试

- 测试文件：[`test/dialect/test_tuner_dialect.py`](../../test/dialect/test_tuner_dialect.py)
- 执行命令：`pytest -q test/dialect/test_tuner_dialect.py`

### 测试目标

- 验证 `tuner.param` 的 parse/print round-trip 以及返回类型稳定性。
- 验证 `tuner.param` 对非法类型与非法 `name` 的错误路径。
- 验证 `tuner.cost` 的 parse/print round-trip、operand 透传、`f64` 结果类型、metadata attr 校验与错误路径。

### 功能与用例清单

| 用例 ID | 约束点 | 对应测试 |
| --- | --- | --- |
| TC-TUNER-001 | `tuner.param` parse/print 与返回类型稳定 | `test_tuner_param_round_trip` |
| TC-TUNER-002 | `tuner.param` 结果类型必须为 `!symbol.dim<"name">` | `test_tuner_param_rejects_invalid_result_type` |
| TC-TUNER-003 | `tuner.param` 的 `name` 非法时报错 | `test_tuner_param_rejects_invalid_name` |
| TC-TUNER-004 | `tuner.cost` parse/print 与 operand 透传稳定，结果类型固定为 `f64` | `test_tuner_cost_round_trip` |
| TC-TUNER-005 | `tuner.cost.kind` 仅允许 `compute / move`，`cost_kind` 仅允许 `compute / move / all` | `test_tuner_cost_rejects_invalid_kind_attrs` |
| TC-TUNER-006 | `tuner.cost` 必须包含 `kind / cost_kind / op_name / device_func`，且结果类型必须为 `f64` | `test_tuner_cost_rejects_missing_attrs_or_invalid_result_type` |
