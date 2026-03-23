# scf.md

## 功能简介

- 定义 operation 层控制流能力，提供 `loop` 的高层语义。
- 面向上层 DSL 的范围迭代表达，支持 `for i in loop(start, end, step)`。
- 允许 `SymbolDim` 参与范围描述，保持符号表达语义。

## 文档信息

- 创建者：`摸鱼小分队`
- 最后一次更改：`摸鱼小分队`
- `spec`：[`spec/operation/scf.md`](../../spec/operation/scf.md)
- `功能实现`：[`kernel_gen/operation/scf.py`](../../kernel_gen/operation/scf.py)
- `test`：[`test/operation/test_operation_scf.py`](../../test/operation/test_operation_scf.py)

## 依赖

- [`spec/symbol_variable/symbol_dim.md`](../../spec/symbol_variable/symbol_dim.md)：`SymbolDim` 的符号维度语义。
- [`expectation/operation/scf/loop.py`](../../expectation/operation/scf/loop.py)：`scf.loop` 的只读 acceptance gate。

## 目标

- 提供统一的高层 `loop` 语义入口，使 DSL 可表达确定或符号范围迭代。
- 允许 `start/end/step` 使用 `int` 与 `SymbolDim` 组合，保留符号表达而不强制求值。
- 保持与 operation 层其他接口一致的错误处理与边界约束。

## 限制与边界

- 仅定义高层范围迭代语义，不提供 IR/lowering 规则。
- 不负责实际执行优化、自动并行或向后端映射。
- 仅支持 `for i in loop(start, end, step)` 形式，当前不定义 `loop(end)` 或 `loop(start, end)` 的简写。
- 不允许 `step == 0`；`step` 为 0 必须抛出错误。
- 当 `start/end/step` 中存在 `SymbolDim` 时，不要求在 Python 运行期求值或展开，只保留符号表达语义。

## 公开接口

### `loop(start, end, step)`

功能说明：

- 创建范围迭代对象，支持在 `for` 语句中迭代。
- 当输入为纯整数时，行为等价于 Python `range(start, end, step)` 的半开区间迭代。
- 当输入包含 `SymbolDim` 时，返回符号范围迭代对象，迭代变量表示符号索引。

参数说明：

- `start (int | SymbolDim)`：起始索引。
- `end (int | SymbolDim)`：结束索引（半开区间终止）。
- `step (int | SymbolDim)`：步长，禁止为 `0`。

使用示例：

```python
from kernel_gen.symbol_variable.symbol_dim import SymbolDim
from kernel_gen.operation.scf import loop

# 纯整数范围
for i in loop(0, 4, 1):
    pass

# 符号范围
M = SymbolDim("M")
K = SymbolDim("K")
for i in loop(0, M, 1):
    pass

for j in loop(K, M, SymbolDim("S")):
    pass
```

注意事项：

- 任意输入不是 `int` 或 `SymbolDim` 时必须抛出 `TypeError`。
- `step == 0` 必须抛出 `ValueError`。
- 当输入包含 `SymbolDim` 时，迭代变量代表符号索引，不要求在运行期展开为具体序列。

返回与限制：

- 返回可迭代对象 `LoopRange`（实现名可自定义，但语义需一致）。
- 对纯整数输入，迭代行为与 `range(start, end, step)` 等价。
- 对含 `SymbolDim` 输入，迭代变量的符号表达遵循 `start + k * step` 的语义约束，其中 `k` 为非负整数索引。
- 返回对象需公开只读的 `start/end/step` 属性（或等价访问接口），以便上层 DSL 保留范围表达并用于测试校验。

## 测试

- 测试文件：[`test/operation/test_operation_scf.py`](../../test/operation/test_operation_scf.py)
- 执行命令：`pytest -q test/operation/test_operation_scf.py`
- Acceptance Gate：[`expectation/operation/scf/loop.py`](../../expectation/operation/scf/loop.py)（只读，用于确认整数与符号输入的核心语义）。
- 测试目标：
  - 纯整数 `loop` 与 `range(start, end, step)` 的半开区间语义一致。
  - `SymbolDim` 输入可构建 `LoopRange` 并保留 `start/end/step` 语义。
  - `step == 0` 触发 `ValueError`。
  - 非法类型输入触发 `TypeError`。
  - 边界/半开区间语义与正负步长的停止条件一致。
- 功能与用例清单：
  - TC-OP-SCF-001：纯整数 `loop(0, 4, 1)` 产生 `[0, 1, 2, 3]`。
  - TC-OP-SCF-002：纯整数 `loop(4, 0, -1)` 产生 `[4, 3, 2, 1]`。
  - TC-OP-SCF-003：`SymbolDim` 输入可返回 `LoopRange`，且 `start/end/step` 保留原值。
  - TC-OP-SCF-004：`step == 0` 抛出 `ValueError`。
  - TC-OP-SCF-005：`start/end/step` 存在非法类型时抛出 `TypeError`。
