# scf.md

## 功能简介

- 定义 operation 层控制流能力，提供 `loop` 的高层语义。
- 面向上层 DSL 的范围迭代表达，支持 `for i in loop(start, end, step)`。
- 允许 `SymbolDim` 参与范围描述，保持符号表达语义。

## 文档信息

- 创建者：`摸鱼小分队`
- 最后一次更改：`摸鱼小分队`
- `spec`：[`spec/operation/scf.md`](../../spec/operation/scf.md)
- `功能实现`：无（当前未实现）
- `test`：无（当前未提供测试）

## 依赖

- [`spec/symbol_variable/symbol_dim.md`](../../spec/symbol_variable/symbol_dim.md)：`SymbolDim` 的符号维度语义。

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

## 测试

- 测试文件：无（当前未提供测试实现）
- 执行命令：无（当前未提供测试实现）
- 测试目标：无（当前未提供测试实现）
- 功能与用例清单：无（当前未提供测试实现）
