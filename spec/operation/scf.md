# scf.md

## 功能简介

- 定义 operation 层控制流能力，提供 `loop` 的高层语义。
- 面向上层 DSL 的范围迭代表达，支持 `for i in loop(start, end, step)`。
- 允许 `SymbolDim` 参与范围描述，保持符号表达语义。
- 当前只覆盖最小 loop helper；未来若要扩展 `if / while / yield / region builder`，必须另开计划，不在本文件顺手扩展。

## 文档信息

- 创建者：`摸鱼小分队`
- 最后一次更改：`金铲铲大作战`
- `spec`：[`spec/operation/scf.md`](../../spec/operation/scf.md)
- `功能实现`：[`kernel_gen/operation/scf.py`](../../kernel_gen/operation/scf.py)
- `test`：[`test/operation/test_operation_scf.py`](../../test/operation/test_operation_scf.py)

## 依赖

- [`spec/symbol_variable/symbol_dim.md`](../../spec/symbol_variable/symbol_dim.md)：`SymbolDim` 的符号维度语义。

## 目标

- 提供统一的高层 `loop` 语义入口，使 DSL 可表达确定或符号范围迭代。
- 允许 `start/end/step` 使用 `int` 与 `SymbolDim` 组合，保留符号表达而不强制求值。
- 保持与 operation 层其他接口一致的错误处理与边界约束。
- 保持 `loop` 作为 operation 层最小范围迭代 helper，不把本轮文本合同扩成完整控制流体系。

## 限制与边界

- 仅定义高层范围迭代语义，不提供 IR/lowering 规则。
- 不负责实际执行优化、自动并行或向后端映射。
- 仅支持 `for i in loop(start, end, step)` 形式，当前不定义 `loop(end)` 或 `loop(start, end)` 的简写。
- 当前只覆盖最小 loop helper，不定义 `if / while / yield / region builder` 或其他控制流族。
- `start/end/step` 只接受 `int | SymbolDim`，并显式拒绝 `bool`；不得依赖 Python `bool` 是 `int` 子类的行为绕过校验。
- 不允许 `step == 0`；`step` 为 0 必须抛出错误。
- 当 `start/end/step` 中存在 `SymbolDim` 时，不要求在 Python 运行期求值或展开，只保留符号表达语义。
- 当 `start/end/step` 含 `SymbolDim` 且无法推导真实迭代次数时，引入 `trip_count`（可选 keyword，默认 `1`，由上游决定）；若 `trip_count` 为整数，则 operation/Python helper 层的迭代序列为 `start + step * i`，`i = 0..trip_count-1`。
- 当 `trip_count` 本身也是 `SymbolDim` 时，当前 operation/Python helper 层只保守产出首项 `start`，不承诺在运行期按符号次数完整展开；lowering 仍只消费 `start/end/step` 的符号范围语义，不消费该有限展开结果。
- `trip_count` 只接受 `int | SymbolDim | None`，并显式拒绝 `bool`；`None` 仅表示按默认值 `1` 归一化。
- `trip_count <= 0` 必须抛出错误（建议 `ValueError`），不得 silent fallback 或默认当作 `1`。
- `LoopRange(...)` 作为公开可直接构造入口，必须与 `loop(...)` 共用同一组输入校验与 `trip_count=None -> 1` 的归一化规则。

## 公开接口

### `loop(start, end, step, trip_count=1)`

功能说明：

- 创建范围迭代对象，支持在 `for` 语句中迭代。
- 当输入为纯整数时，行为等价于 Python `range(start, end, step)` 的半开区间迭代。
- 当输入包含 `SymbolDim` 时，返回符号范围迭代对象，迭代变量表示符号索引；可通过 `trip_count` 指定迭代次数。

参数说明：

- `start (int | SymbolDim)`：起始索引。
- `end (int | SymbolDim)`：结束索引（半开区间终止）。
- `step (int | SymbolDim)`：步长，禁止为 `0`。
- `trip_count (int | SymbolDim | None)`：可选 keyword 迭代次数；当 `start/end/step` 含 `SymbolDim` 且无法推导真实次数时使用；默认 `1`。若 `trip_count` 为整数，则运行期 helper 有限展开 `trip_count` 项；若 `trip_count` 为 `SymbolDim`，当前只保守产出首项。

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

# 上游显式指定 trip_count
for t in loop(SymbolDim("S"), SymbolDim("S") + SymbolDim("K"), SymbolDim("K"), trip_count=3):
    pass
```

注意事项：

- 任意输入不是 `int` 或 `SymbolDim` 时必须抛出 `TypeError`。
- `bool` 不属于合法 `int` 输入，`start/end/step/trip_count` 传入 `True/False` 必须抛出 `TypeError`。
- `step == 0` 必须抛出 `ValueError`。
- `trip_count <= 0` 必须抛出 `ValueError`；不得 silent fallback 或默认当作 `1`。
- 当输入包含 `SymbolDim` 时，迭代变量代表符号索引，不要求在运行期展开为具体序列。
- 当无法推导真实迭代次数时，上游可显式提供 `trip_count`；未提供时默认 `1`，且 `trip_count <= 0` 必须报错。
- 当 `trip_count` 为整数时，operation/Python helper 层按 `start + step * i` 生成有限序列；当 `trip_count` 为 `SymbolDim` 时，当前只保守返回首项 `start`，避免在运行期伪造符号次数展开。
- `trip_count` 的运行期作用仅限 operation/Python helper 层的有限展开；lowering 不消费该字段。

返回与限制：

- 返回可迭代对象 `LoopRange`（实现名可自定义，但语义需一致）。
- 对纯整数输入，迭代行为与 `range(start, end, step)` 等价。
- 对含 `SymbolDim` 输入，迭代变量的符号表达遵循 `start + k * step` 的语义约束，其中 `k` 为非负整数索引；当 `trip_count` 为整数时，运行期 helper 生成 `k = 0..trip_count-1` 的有限序列。
- 当 `trip_count` 为 `SymbolDim` 时，当前运行期 helper 只保守返回首项 `start`，不承诺按符号次数完整展开。
- 返回对象需公开只读的 `start/end/step/trip_count` 属性（或等价访问接口），以便上层 DSL 保留范围表达并用于测试校验。
- `LoopRange(...)` 直接构造时，公开行为必须与 `loop(...)` 保持一致，不能绕过 `bool` / 非法类型 / 非法 `trip_count` 的显式校验。

## 测试

- 测试文件：[`test/operation/test_operation_scf.py`](../../test/operation/test_operation_scf.py)
- 执行命令：`pytest -q test/operation/test_operation_scf.py`
- 测试目标：
  - 纯整数 `loop` 与 `range(start, end, step)` 的半开区间语义一致。
  - `SymbolDim` 输入可构建 `LoopRange` 并保留 `start/end/step` 语义。
  - `bool` 输入不会因为 Python `bool` 是 `int` 子类而被接受。
  - `step == 0` 触发 `ValueError`。
  - `trip_count <= 0` 触发错误，且不得 silent fallback。
  - 当前只收口最小 loop helper，不扩到其他控制流构造。
  - 非法类型输入触发 `TypeError`。
  - 边界/半开区间语义与正负步长的停止条件一致。
- 功能与用例清单：
  - TC-OP-SCF-001：纯整数 `loop(0, 4, 1)` 产生 `[0, 1, 2, 3]`。
  - TC-OP-SCF-002：纯整数 `loop(4, 0, -1)` 产生 `[4, 3, 2, 1]`。
  - TC-OP-SCF-003：`SymbolDim` 输入可返回 `LoopRange`，且 `start/end/step` 保留原值。
  - TC-OP-SCF-004：`step == 0` 抛出 `ValueError`。
  - TC-OP-SCF-005：`start/end/step` 存在非法类型时抛出 `TypeError`。
  - TC-OP-SCF-006：隐式 `trip_count <= 0` 必须报错，不得 fallback。
  - TC-OP-SCF-007：显式 `trip_count = 3` 时迭代语义为 `start`、`start + step`、`start + step * 2`。
  - TC-OP-SCF-013：`trip_count = SymbolDim("T")` 时，当前运行期 helper 只保守返回首项 `start`，并保留 `trip_count` 本身供上层读取。
