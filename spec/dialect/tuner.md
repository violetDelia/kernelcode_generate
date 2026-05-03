# tuner.md

## 功能简介

- 定义 `tuner` dialect 的超参数声明与成本节点接口。
- 本方言提供“声明超参数并生成符号标量”的 IR 表达，也提供 `tuner.cost` 作为 cost function 内的单 op 局部成本节点；不负责运行期求值、调度策略、搜索空间算法或真实 cost table。
- 超参数标量统一返回 `!symbol.dim<"name">`，与 `SymbolDim` 的符号维度语义保持一致；`tuner.cost` 固定返回 `!symbol.int<"expr">`。

## API 列表

- `class Tuner(Dialect)`
- `class TunerParamOp(result_type: Attribute)`
- `class TunerCostOp(operands: list[SSAValue | Operation], *, cost_kind: Attribute, op_name: Attribute, extra_attrs: dict[str, Attribute] | None = None, result_type: Attribute = SymbolValueType.from_expr("COST"))`

## 文档信息

- 创建者：`未记录`
- 最后一次更改：`小李飞刀`
- `spec`：[`spec/dialect/tuner.md`](../../spec/dialect/tuner.md)
- `功能实现`：[`kernel_gen/dialect/tuner.py`](../../kernel_gen/dialect/tuner.py)
- `test`：
  - [`test/dialect/test_tuner.py`](../../test/dialect/test_tuner.py)
  - [`test/passes/tuning/test_launch_kernel_cost_func.py`](../../test/passes/tuning/test_launch_kernel_cost_func.py)

## 依赖

- [`spec/dialect/symbol.md`](../../spec/dialect/symbol.md)：提供符号整数/维度标量语义；`!symbol.dim<"name">` 作为超参数标量类型由 `symbol dialect` 维护。
- [`spec/symbol_variable/symbol_dim.md`](../../spec/symbol_variable/symbol_dim.md)：定义 `SymbolDim` 的运行时语义边界，供超参数标量语义对齐。
- [`spec/pass/tuning/launch_kernel_cost_func.md`](../pass/tuning/launch_kernel_cost_func.md)：消费 `tuner.cost` 作为 launch kernel cost function 的局部成本节点。

## 目标

- 在 IR 中提供统一的超参数声明入口。
- 在 IR 中提供统一的局部成本节点入口，使 pass 可把原 op 的 operands 与 attrs 映射为 `tuner.cost(...)->!symbol.int<"expr">`。
- 保持 `parse/print` 与 verifier 约束清晰，保证超参数名可稳定打印与校验。
- 当前 `tuner.cost.cost_kind` 的公开方向为任意非空字符串 attr。

## 额外补充

### 模块级补充

- 本小节只记录模块级非接口补充；接口级参数限制、错误语义、兼容要求与非目标必须维护在对应 API 的 `注意事项`。
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

## API详细说明

### `class Tuner(Dialect)`

- api：`class Tuner(Dialect)`
- 参数：无。
- 返回值：`Tuner` 实例。
- 使用示例：

  ```python
  from kernel_gen.dialect.tuner import Tuner

  tuner = Tuner()
  ```
- 功能说明：定义 `Tuner` 公开类型。
- 注意事项：`Tuner` 只注册 `tuner.param` 与 `tuner.cost` 两类公开 op；不定义运行期求值、调度策略、搜索空间算法或真实 cost table。

### `class TunerParamOp(result_type: Attribute)`

- api：`class TunerParamOp(result_type: Attribute)`
- 参数：
  - `result_type`：类型对象或类型名称；类型 `Attribute`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
- 返回值：`TunerParamOp` 实例。
- 使用示例：

  ```python
  from kernel_gen.dialect.symbol import SymbolDimType
  from kernel_gen.dialect.tuner import TunerParamOp

  tuner_param_op = TunerParamOp(SymbolDimType.from_name("BLOCK_M"))
  ```
- 功能说明：声明一个超参数并返回对应的符号维度标量。
- 注意事项：`tuner.param` 无 operand、无 region、单结果；`result_type` 必须为 `!symbol.dim<"name">`；`name` 必须为非空标识符，只能包含字母、数字与下划线，并以字母或下划线开头；不得使用 `!symbol.int<"...">`、builtin `index`、普通整数或其他类型替代。

### `class TunerCostOp(operands: list[SSAValue | Operation], *, cost_kind: Attribute, op_name: Attribute, extra_attrs: dict[str, Attribute] | None = None, result_type: Attribute = SymbolValueType.from_expr("COST"))`

- api：`class TunerCostOp(operands: list[SSAValue | Operation], *, cost_kind: Attribute, op_name: Attribute, extra_attrs: dict[str, Attribute] | None = None, result_type: Attribute = SymbolValueType.from_expr("COST"))`
- 参数：
  - `operands`：输入操作数序列；类型 `list[SSAValue | Operation]`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按可变容器传入时，是否修改输入必须以本接口功能说明和注意事项为准；非法值按该 API 的公开错误语义处理。
  - `cost_kind`：`cost_kind` 输入值，参与 `TunerCostOp` 的公开处理流程；类型 `Attribute`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
  - `op_name`：公开名称或符号名；类型 `Attribute`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
  - `extra_attrs`：`extra_attrs` 输入值，参与 `TunerCostOp` 的公开处理流程；类型 `dict[str, Attribute] | None`；默认值 `None`；允许 `None`/空值仅用于签名或默认值显式声明的可选场景；按可变容器传入时，是否修改输入必须以本接口功能说明和注意事项为准；非法值按该 API 的公开错误语义处理。
  - `result_type`：类型对象或类型名称；类型 `Attribute`；默认值 `SymbolValueType.from_expr("COST")`；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
- 返回值：`TunerCostOp` 实例。
- 使用示例：

  ```python
  from xdsl.dialects.builtin import StringAttr

  from kernel_gen.dialect.symbol import SymbolDimType
  from kernel_gen.dialect.tuner import TunerCostOp, TunerParamOp

  value = TunerParamOp(SymbolDimType.from_name("BLOCK_M")).result
  tuner_cost_op = TunerCostOp(
      [value],
      cost_kind=StringAttr("memory"),
      op_name=StringAttr("dma.copy"),
  )
  ```
- 功能说明：表示 cost function 内某个原 op 的局部成本，记录原 op operands、原 attrs 与 pass-owned metadata，并返回 `!symbol.int<"expr">` 局部成本值。
- 注意事项：`operands` 按原 op operands 原顺序透传，原 op 无 operands 时传空列表；`cost_kind` 表示当前 cost function 的统计视角，允许任意非空字符串 attr；`op_name` 必须为非空字符串 attr；`extra_attrs` 用于平铺保留原 op attributes；若原 op 存在业务字段 `kind`，生成方必须先改名为领域字段，例如 `kernel_kind`；`tuner.cost` 自身不公开旧 metadata attr `kind` 或 `device_func`，verifier 必须拒绝这两个字段；结果类型固定为单结果 `!symbol.int<"expr">`；本 op 无 region、不支持多结果、不负责把局部成本汇总成函数返回值。

## 测试

- 测试文件：
  - `test/dialect/test_tuner.py`
  - `test/passes/tuning/test_launch_kernel_cost_func.py`
- 执行命令：
  - `pytest -q test/dialect/test_tuner.py -k "tuner_cost"`
  - `pytest -q test/passes/tuning/test_launch_kernel_cost_func.py -k "launch_kernel_cost_func"`

### 测试目标

- 验证 `tuner.cost` 的 parse/print、operand 透传、`!symbol.int<"...">` 结果类型、open-kind verifier 与错误路径。
- 验证 `launch-kernel-cost-func` 消费 `tuner.cost` 时的 kind 口径与错误路径一致。

### 功能与用例清单

| 用例 ID | 功能 | 场景 | 前置条件 | 操作 | 预期结果 | 建议测试 |
| --- | --- | --- | --- | --- | --- | --- |
| TC-TUNER-001 | 解析/打印 | `tuner.param` parse/print 与返回类型稳定 | 准备可 parse/print、round-trip 或文本比对的公开输入。 | 运行 `test_tuner_param_round_trip`。 | parse/print、round-trip 或文本比对结果稳定。 | `test_tuner_param_round_trip` |
| TC-TUNER-002 | 边界/异常 | `tuner.param` 结果类型必须为 `!symbol.dim<"name">` | 准备触发该错误路径的公开输入或非法参数组合。 | 运行 `test_tuner_param_rejects_invalid_result_type`。 | “`tuner.param` 结果类型必须为 `!symbol.dim<"name">`”场景按公开错误语义失败或被拒绝。 | `test_tuner_param_rejects_invalid_result_type` |
| TC-TUNER-003 | 边界/异常 | `tuner.param` 的 `name` 非法时报错 | 准备触发该错误路径的公开输入或非法参数组合。 | 运行 `test_tuner_param_rejects_invalid_name`。 | “`tuner.param` 的 `name` 非法时报错”场景按公开错误语义失败或被拒绝。 | `test_tuner_param_rejects_invalid_name` |
| TC-TUNER-004 | 解析/打印 | `tuner.cost` parse/print 与 operand 透传稳定，结果类型固定为 `!symbol.int<"...">` | 准备可 parse/print、round-trip 或文本比对的公开输入。 | 运行 `test_tuner_cost_round_trip`。 | parse/print、round-trip 或文本比对结果稳定。 | `test_tuner_cost_round_trip` |
| TC-TUNER-005 | 边界/异常 | `tuner.cost.cost_kind` 必须是非空字符串，并拒绝旧 `kind / device_func` attrs | 准备触发该错误路径的公开输入或非法参数组合。 | 运行 `test_tuner_cost_rejects_invalid_kind_attrs`。 | “`tuner.cost.cost_kind` 必须是非空字符串，并拒绝旧 `kind / device_func` attrs”场景按公开错误语义失败或被拒绝。 | `test_tuner_cost_rejects_invalid_kind_attrs` |
| TC-TUNER-006 | 边界/异常 | `tuner.cost` 必须包含 `cost_kind / op_name`，且结果类型必须为 `!symbol.int<"...">` | 准备触发该错误路径的公开输入或非法参数组合。 | 运行 `test_tuner_cost_rejects_missing_attrs_or_invalid_result_type`。 | “`tuner.cost` 必须包含 `cost_kind / op_name`，且结果类型必须为 `!symbol.int<"...">`”场景按公开错误语义失败或被拒绝。 | `test_tuner_cost_rejects_missing_attrs_or_invalid_result_type` |
