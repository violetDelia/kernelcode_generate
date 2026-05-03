# scf.md

## 功能简介

- 定义 operation 层控制流能力，提供 `loop` 的高层语义。
- 面向上层 DSL 的范围迭代表达，支持 `for i in loop(start, end, step)`。
- 允许 `SymbolDim` 参与范围描述，保持符号表达语义。
- 当前只覆盖最小 loop helper；未来若要扩展 `if / while / yield / region builder`，必须另开计划，不在本文件顺手扩展。

## API 列表

- `class LoopRange(start: int | SymbolDim, end: int | SymbolDim, step: int | SymbolDim, trip_count: int | SymbolDim | None = 1)`
- `LoopRange.start -> int | SymbolDim`
- `LoopRange.end -> int | SymbolDim`
- `LoopRange.step -> int | SymbolDim`
- `LoopRange.trip_count -> int | SymbolDim`
- `loop(start: int | SymbolDim, end: int | SymbolDim, step: int | SymbolDim, trip_count: int | SymbolDim | None = 1) -> range | LoopRange`
- `kernel_gen.operation.loop(start: int | SymbolDim, end: int | SymbolDim, step: int | SymbolDim, trip_count: int | SymbolDim | None = 1) -> range | LoopRange`

## 文档信息

- 创建者：`未记录`
- 最后一次更改：`小李飞刀`
- `spec`：[`spec/operation/scf.md`](../../spec/operation/scf.md)
- `功能实现`：[`kernel_gen/operation/scf.py`](../../kernel_gen/operation/scf.py)
- `test`：[`test/operation/test_scf.py`](../../test/operation/test_scf.py)

## 依赖

- [`spec/symbol_variable/symbol_dim.md`](../../spec/symbol_variable/symbol_dim.md)：`SymbolDim` 的符号维度语义。
- [`kernel_gen/operation/__init__.py`](../../kernel_gen/operation/__init__.py)：定义 `kernel_gen.operation` 包级稳定导出集合，供本文件锁定顶层导出边界复用。

## 目标

- 提供统一的高层 `loop` 语义入口，使 DSL 可表达确定或符号范围迭代。
- 允许 `start/end/step` 使用 `int` 与 `SymbolDim` 组合，保留符号表达而不强制求值。
- 保持与 operation 层其他接口一致的错误处理与边界约束。
- 保持 `loop` 作为 operation 层最小范围迭代 helper，不把本轮文本合同扩成完整控制流体系。

## 额外补充

### 模块级补充

- 本小节只记录模块级非接口补充；接口级参数限制、错误语义、兼容要求与非目标必须维护在对应 API 的 `注意事项`。
- 仅定义高层范围迭代语义，不提供 IR/lowering 规则。
- 不负责实际执行优化、自动并行或向后端映射。
- 仅支持 `for i in loop(start, end, step)` 形式，当前不定义 `loop(end)` 或 `loop(start, end)` 的简写。
- 当前只覆盖最小 loop helper，不定义 `if / while / yield / region builder` 或其他控制流族。
- `kernel_gen.operation.scf` 是 scf family 的完整稳定入口；`kernel_gen.operation` 顶层只稳定重导出 `loop`，且对象身份必须与 `kernel_gen.operation.scf.loop` 一致。

### package-root 导出说明

| 入口 | 稳定公开 API | 说明 |
| --- | --- | --- |
| `kernel_gen.operation.scf` | `loop` | scf family 的完整稳定入口 |
| `kernel_gen.operation` | `loop` | 包根稳定重导出同一 `loop` helper；对象身份与 `kernel_gen.operation.scf` 保持一致 |
## API详细说明

### `class LoopRange(start: int | SymbolDim, end: int | SymbolDim, step: int | SymbolDim, trip_count: int | SymbolDim | None = 1)`

- api：`class LoopRange(start: int | SymbolDim, end: int | SymbolDim, step: int | SymbolDim, trip_count: int | SymbolDim | None = 1)`
- 参数：
  - `start`：范围起始值；类型 `int | SymbolDim`；无默认值；纯整数路径表示半开区间首项，符号路径保留为 `LoopRange.start`。
  - `end`：范围结束值；类型 `int | SymbolDim`；无默认值；纯整数路径表示半开区间终止边界，符号路径保留为 `LoopRange.end`。
  - `step`：范围步长；类型 `int | SymbolDim`；无默认值；纯整数路径按 Python `range` 步长推进，符号路径保留为 `LoopRange.step`。
  - `trip_count`：符号路径的有限展开次数约束；类型 `int | SymbolDim | None`；默认值 `1`；`None` 归一化为 `1`。
- 返回值：`LoopRange` 实例。
- 使用示例：

  ```python
  from kernel_gen.operation.scf import LoopRange
  from kernel_gen.symbol_variable.symbol_dim import SymbolDim

  n = SymbolDim("N")
  s = SymbolDim("S")
  loop_range = LoopRange(0, n, s, trip_count=3)

  assert loop_range.start == 0
  assert loop_range.end is n
  assert loop_range.step is s
  assert loop_range.trip_count == 3
  assert [item if isinstance(item, int) else item.get_value() for item in loop_range] == [
      0,
      "S",
      "2*S",
  ]
  ```
- 功能说明：保存符号范围表达，并在 Python helper 层按 `trip_count` 提供有限迭代序列。
- 注意事项：
  - `start`、`end`、`step` 只接受 `int | SymbolDim`；传入 `bool`、`str` 或其他类型必须抛出 `KernelCodeError`。
  - `step == 0` 必须抛出 `KernelCodeError`。
  - `trip_count` 只接受 `int | SymbolDim | None`；传入 `bool`、`str` 或其他类型必须抛出 `KernelCodeError`。
  - `trip_count=None` 必须归一化为 `1`；`trip_count <= 0` 必须抛出 `KernelCodeError`。
  - `trip_count` 为 `int` 时，迭代序列为 `start + step * i`，`i = 0..trip_count-1`。
  - `trip_count` 为 `SymbolDim` 时，当前 Python helper 层只保守产出首项 `start`，不承诺按符号次数展开。
  - 本类只提供 operation/Python helper 层的有限展开；lowering 不消费该有限展开结果。

### `LoopRange.start -> int | SymbolDim`

- api：`LoopRange.start -> int | SymbolDim`
- 参数：无。
- 返回值：构造 `LoopRange` 时传入并校验后的 `start`。
- 使用示例：

  ```python
  from kernel_gen.operation.scf import LoopRange
  from kernel_gen.symbol_variable.symbol_dim import SymbolDim

  loop_range = LoopRange(SymbolDim("M"), SymbolDim("N"), 1)
  assert loop_range.start.get_value() == "M"
  ```
- 功能说明：只读返回符号范围起始值。
- 注意事项：属性返回值不得在访问时重新求值；调用方应按只读语义消费。

### `LoopRange.end -> int | SymbolDim`

- api：`LoopRange.end -> int | SymbolDim`
- 参数：无。
- 返回值：构造 `LoopRange` 时传入并校验后的 `end`。
- 使用示例：

  ```python
  from kernel_gen.operation.scf import LoopRange
  from kernel_gen.symbol_variable.symbol_dim import SymbolDim

  loop_range = LoopRange(0, SymbolDim("N"), 1)
  assert loop_range.end.get_value() == "N"
  ```
- 功能说明：只读返回符号范围结束值。
- 注意事项：属性返回值不得在访问时重新求值；调用方应按只读语义消费。

### `LoopRange.step -> int | SymbolDim`

- api：`LoopRange.step -> int | SymbolDim`
- 参数：无。
- 返回值：构造 `LoopRange` 时传入并校验后的 `step`。
- 使用示例：

  ```python
  from kernel_gen.operation.scf import LoopRange
  from kernel_gen.symbol_variable.symbol_dim import SymbolDim

  loop_range = LoopRange(0, SymbolDim("N"), SymbolDim("S"))
  assert loop_range.step.get_value() == "S"
  ```
- 功能说明：只读返回符号范围步长。
- 注意事项：属性返回值不得在访问时重新求值；调用方应按只读语义消费。

### `LoopRange.trip_count -> int | SymbolDim`

- api：`LoopRange.trip_count -> int | SymbolDim`
- 参数：无。
- 返回值：构造 `LoopRange` 时传入并校验后的 `trip_count`；若构造时传入 `None`，返回 `1`。
- 使用示例：

  ```python
  from kernel_gen.operation.scf import LoopRange
  from kernel_gen.symbol_variable.symbol_dim import SymbolDim

  loop_range = LoopRange(0, SymbolDim("N"), 1, trip_count=None)
  assert loop_range.trip_count == 1
  ```
- 功能说明：只读返回符号范围有限展开次数约束。
- 注意事项：属性返回值不得在访问时重新求值；调用方应按只读语义消费。

### `loop(start: int | SymbolDim, end: int | SymbolDim, step: int | SymbolDim, trip_count: int | SymbolDim | None = 1) -> range | LoopRange`

- api：`loop(start: int | SymbolDim, end: int | SymbolDim, step: int | SymbolDim, trip_count: int | SymbolDim | None = 1) -> range | LoopRange`
- 参数：
  - `start`：范围起始值；类型 `int | SymbolDim`；无默认值；纯整数路径表示半开区间首项，符号路径用于构造 `LoopRange.start`。
  - `end`：范围结束值；类型 `int | SymbolDim`；无默认值；纯整数路径表示半开区间终止边界，符号路径用于构造 `LoopRange.end`。
  - `step`：范围步长；类型 `int | SymbolDim`；无默认值；纯整数路径按 Python `range` 步长推进，符号路径用于构造 `LoopRange.step`。
  - `trip_count`：符号路径的有限展开次数约束；类型 `int | SymbolDim | None`；默认值 `1`；`None` 归一化为 `1`。
- 返回值：当 `start/end/step` 均为 `int` 时返回 `range`；任一参数为 `SymbolDim` 时返回 `LoopRange`。
- 使用示例：

  ```python
  from kernel_gen.operation.scf import loop
  from kernel_gen.symbol_variable.symbol_dim import SymbolDim

  assert list(loop(0, 4, 1)) == [0, 1, 2, 3]

  loop_range = loop(0, SymbolDim("N"), SymbolDim("S"), trip_count=3)
  assert [item if isinstance(item, int) else item.get_value() for item in loop_range] == [
      0,
      "S",
      "2*S",
  ]
  ```
- 功能说明：创建 operation 层范围迭代对象，供 DSL 表达确定或符号循环范围。
- 注意事项：
  - `start`、`end`、`step` 只接受 `int | SymbolDim`；传入 `bool`、`str` 或其他类型必须抛出 `KernelCodeError`。
  - `step == 0` 必须抛出 `KernelCodeError`。
  - `trip_count` 只接受 `int | SymbolDim | None`；传入 `bool`、`str` 或其他类型必须抛出 `KernelCodeError`。
  - `trip_count=None` 必须归一化为 `1`；`trip_count <= 0` 必须抛出 `KernelCodeError`。
  - 当输入全部为 `int` 时，返回值行为必须等价于 `range(start, end, step)`。
  - 当输入包含 `SymbolDim` 时，不要求在 Python 运行期求出真实迭代次数；若 `trip_count` 为 `int`，Python helper 层按 `start + step * i` 生成有限序列。
  - `trip_count` 为 `SymbolDim` 时，当前 Python helper 层只保守产出首项 `start`。

### `kernel_gen.operation.loop(start: int | SymbolDim, end: int | SymbolDim, step: int | SymbolDim, trip_count: int | SymbolDim | None = 1) -> range | LoopRange`

- api：`kernel_gen.operation.loop(start: int | SymbolDim, end: int | SymbolDim, step: int | SymbolDim, trip_count: int | SymbolDim | None = 1) -> range | LoopRange`
- 参数：
  - `start`：范围起始值；类型 `int | SymbolDim`；无默认值；转发给 `kernel_gen.operation.scf.loop`。
  - `end`：范围结束值；类型 `int | SymbolDim`；无默认值；转发给 `kernel_gen.operation.scf.loop`。
  - `step`：范围步长；类型 `int | SymbolDim`；无默认值；转发给 `kernel_gen.operation.scf.loop`。
  - `trip_count`：符号路径的有限展开次数约束；类型 `int | SymbolDim | None`；默认值 `1`；转发给 `kernel_gen.operation.scf.loop`。
- 返回值：与 `kernel_gen.operation.scf.loop` 相同，返回 `range | LoopRange`。
- 使用示例：

  ```python
  import kernel_gen.operation as operation

  assert list(operation.loop(0, 4, 1)) == [0, 1, 2, 3]
  ```
- 功能说明：通过 `kernel_gen.operation` 包根稳定重导出 `loop`。
- 注意事项：
  - 包根 `loop` 必须与 `kernel_gen.operation.scf.loop` 保持对象身份一致。
  - 参数、返回值与错误语义必须完全沿用 `kernel_gen.operation.scf.loop`。

## 测试

- 测试文件：
  - `test/operation/test_package.py`
  - `test/operation/test_scf.py`
- 执行命令：`pytest -q test/operation/test_scf.py`

### 测试目标

- 验证 `spec/operation/scf.md` 对应公开 API 的正常路径、边界条件与错误语义。
- 验证公开执行入口的返回值、输出或状态变化符合预期。
- 验证非法输入、边界条件和错误语义按公开合同失败。


### 功能与用例清单

| 用例 ID | 功能 | 场景 | 前置条件 | 操作 | 预期结果 | 建议测试 |
| --- | --- | --- | --- | --- | --- | --- |
| TC-OPERATION-SCF-001 | 执行结果 | TC-OP-SCF-001：纯整数 `loop(0, 4, 1)` 产生 `[0, 1, 2, 3]`。 | 准备公开输入数据、执行入口或 CLI 状态文件。 | 运行覆盖 `TC-OP-SCF-001` 的公开测试用例。 | 命令返回码、输出、执行结果或状态变更体现“TC-OP-SCF-001：纯整数 `loop(0, 4, 1)` 产生 `[0, 1, 2, 3]`。”场景。 | `TC-OP-SCF-001` |
| TC-OPERATION-SCF-002 | 执行结果 | TC-OP-SCF-002：纯整数 `loop(4, 0, -1)` 产生 `[4, 3, 2, 1]`。 | 准备公开输入数据、执行入口或 CLI 状态文件。 | 运行覆盖 `TC-OP-SCF-002` 的公开测试用例。 | 命令返回码、输出、执行结果或状态变更体现“TC-OP-SCF-002：纯整数 `loop(4, 0, -1)` 产生 `[4, 3, 2, 1]`。”场景。 | `TC-OP-SCF-002` |
| TC-OPERATION-SCF-003 | 执行结果 | TC-OP-SCF-003：`SymbolDim` 输入可返回 `LoopRange`，且 `start/end/step` 保留原值。 | 准备公开输入数据、执行入口或 CLI 状态文件。 | 运行覆盖 `TC-OP-SCF-003` 的公开测试用例。 | 命令返回码、输出、执行结果或状态变更体现“TC-OP-SCF-003：`SymbolDim` 输入可返回 `LoopRange`，且 `start/end/step` 保留原值。”场景。 | `TC-OP-SCF-003` |
| TC-OPERATION-SCF-004 | 边界/异常 | TC-OP-SCF-004：`step == 0` 抛出 `KernelCodeError`。 | 准备触发该错误路径的公开输入或非法参数组合。 | 运行覆盖 `TC-OP-SCF-004` 的公开测试用例。 | “TC-OP-SCF-004：`step == 0` 抛出 `KernelCodeError`。”场景按公开错误语义失败或被拒绝。 | `TC-OP-SCF-004` |
| TC-OPERATION-SCF-005 | 边界/异常 | TC-OP-SCF-005：`start/end/step` 存在非法类型时抛出 `KernelCodeError`。 | 准备触发该错误路径的公开输入或非法参数组合。 | 运行覆盖 `TC-OP-SCF-005` 的公开测试用例。 | “TC-OP-SCF-005：`start/end/step` 存在非法类型时抛出 `KernelCodeError`。”场景按公开错误语义失败或被拒绝。 | `TC-OP-SCF-005` |
| TC-OPERATION-SCF-006 | 边界/异常 | TC-OP-SCF-006：隐式 `trip_count <= 0` 必须报错，不得 fallback。 | 准备触发该错误路径的公开输入或非法参数组合。 | 运行覆盖 `TC-OP-SCF-006` 的公开测试用例。 | “TC-OP-SCF-006：隐式 `trip_count <= 0` 必须报错，不得 fallback。”场景按公开错误语义失败或被拒绝。 | `TC-OP-SCF-006` |
| TC-OPERATION-SCF-007 | 执行结果 | TC-OP-SCF-007：显式 `trip_count = 3` 时迭代语义为 `start`、`start + step`、`start + step * 2`。 | 准备公开输入数据、执行入口或 CLI 状态文件。 | 运行覆盖 `TC-OP-SCF-007` 的公开测试用例。 | 命令返回码、输出、执行结果或状态变更体现“TC-OP-SCF-007：显式 `trip_count = 3` 时迭代语义为 `start`、`start + step`、`start + step * 2`。”场景。 | `TC-OP-SCF-007` |
| TC-OPERATION-SCF-008 | 执行结果 | TC-OP-SCF-013：`trip_count = SymbolDim("T")` 时，当前运行期 helper 只保守返回首项 `start`，并保留 `trip_count` 本身供上层读取。 | 准备公开输入数据、执行入口或 CLI 状态文件。 | 运行覆盖 `TC-OP-SCF-013` 的公开测试用例。 | 命令返回码、输出、执行结果或状态变更体现“TC-OP-SCF-013：`trip_count = SymbolDim("T")` 时，当前运行期 helper 只保守返回首项 `start`，并保留 `trip_count` 本身供上层读取。”场景。 | `TC-OP-SCF-013` |
