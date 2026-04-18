# symbol_dim_expectation_green_plan.md

## 文档信息

- 创建者：`榕`
- 最后一次更改：`大闸蟹`
- 目标 `spec`：[`spec/symbol_variable/symbol_dim.md`](../../spec/symbol_variable/symbol_dim.md)
- 目标 `API`：[`kernel_gen/symbol_variable/symbol_dim.py`](../../kernel_gen/symbol_variable/symbol_dim.py)
- 目标 `test`：[`test/symbol_variable/test_symbol_dim.py`](../../test/symbol_variable/test_symbol_dim.py)
- 目标 `验收资产`：[`expectation/symbol_variable/symbol_dim.py`](../../expectation/symbol_variable/symbol_dim.py)、[`expectation/symbol_variable/memory.py`](../../expectation/symbol_variable/memory.py)
- 目标 `功能实现`：[`kernel_gen/symbol_variable/symbol_dim.py`](../../kernel_gen/symbol_variable/symbol_dim.py)

## 任务清单

| 任务 | 前置任务 | worktree | 记录文件 |
| --- | --- | --- | --- |
| S1 | 无 | `wt-20260418-symbol-dim-s1` | `20260418-symbol-dim-refactor.md` |
| S2 | S1 | `wt-20260418-symbol-dim-s2` | `20260418-symbol-dim-refactor.md` |
| S3 | S2 | `wt-20260418-symbol-dim-s3` | `20260418-symbol-dim-refactor.md` |

- 推进前提：按计划书规则先完成互评；互评结论满足推进条件后，才允许进入任务新建与分发。
- 新建任务时，每个“小任务”只先创建首个 `spec` 任务；后续 `build/review` 默认由执行链按 `-next -auto -type` 继续推进，不在计划通过后一次性全建出来。
- 小任务之间必须严格遵守前置依赖关系：`S1 -> S2 -> S3` 不可跳过，后续小任务不得越过未完成的前置小任务直接创建或推进。

## 评审摘要

- 评审结论：`通过`
- 评审人：`榕`、`守护最好的爱莉希雅`、`大闸蟹`
- 结论摘要：`用户已明确确认：spec/test 属于本轮计划收口范围，但 expectation 不改、继续作为合同真源。当前计划按“小任务先建 spec、后续由执行链默认推进 build/review”的依赖链推进，目标是在实现、spec、test 三侧同步对齐 expectation 合同；未见阻断推进的剩余歧义。`
- 终验结论（2026-04-19 00:19 +0800，终验人：`大闸蟹`）：`通过`
- 最新同步现场与验证基线：`/home/lfr/kernelcode_generate` 主仓工作区，`HEAD=2f7aea5cf24221e0fd90e3b97127d31513dc23df`；执行目录为仓库根目录，且 `DONE.md` 已记录 `T-20260418-a1838667`、`T-20260418-0f402082`、`T-20260418-a46b4404` 三个 merge 任务完成，按该主仓基线复核本计划必过命令。
- 终验命令：
  - `python3 expectation/symbol_variable/symbol_dim.py` -> `exit 0`
  - `python3 expectation/symbol_variable/memory.py` -> `exit 0`
  - `python3 -m pytest -q test/symbol_variable/test_symbol_dim.py` -> `16 passed`
  - `python3 -m pytest -q test/symbol_variable/test_memory.py test/symbol_variable/test_memory_operation.py test/symbol_variable/test_symbol_shape.py` -> `42 passed`
- 终验摘要：`当前主仓现场已满足本计划完成态与验收设计：SymbolDim 输入域、get_symbol/get_value 的公开口径，以及与 Memory 的联动回归均已收口；symbol_dim/memory 两条 expectation 与相关 pytest 未见剩余阻断项。`

## 计划目标

- 重构 [`kernel_gen/symbol_variable/symbol_dim.py`](../../kernel_gen/symbol_variable/symbol_dim.py)，并同步收口 [`spec/symbol_variable/symbol_dim.md`](../../spec/symbol_variable/symbol_dim.md) 与 [`test/symbol_variable/test_symbol_dim.py`](../../test/symbol_variable/test_symbol_dim.py)，使仓库合同与当前 expectation 一致。
- 明确并收口 `SymbolDim(value)` 的输入域：`SymbolDim(12)` 合法，但数值字面量字符串如 `"12"`、`"3.14"` 不再作为合法符号名。
- 明确并收口 `get_symbol()` 与 `get_value()` 的公开语义：符号计算结果应与约定的 SymPy 简化结果一致。
- 保持现有公开 API 名称和参数顺序不变，不新增新的对外入口。
- 以 [`expectation/symbol_variable/symbol_dim.py`](../../expectation/symbol_variable/symbol_dim.py) 为合同真源收口实现/spec/test，同时不回退 [`expectation/symbol_variable/memory.py`](../../expectation/symbol_variable/memory.py) 已通过的合同。

## 当前基线

- 当前公开合同：
  - 以 [`expectation/symbol_variable/symbol_dim.py`](../../expectation/symbol_variable/symbol_dim.py) 和用户补充口径为准。
  - 本轮合同真源顺序：`expectation/symbol_variable/symbol_dim.py + 用户确认 > spec/symbol_variable/symbol_dim.md > test/symbol_variable/test_symbol_dim.py > 当前实现`。
- 当前公开 API：
  - `SymbolDim(value)`
  - `get_symbol()`
  - `get_value()`
  - `is_dynamic()`
  - `__eq__()`
  - `+` / `-` / `*` / `/` / `//` 及对应反向运算
- 当前实现入口：
  - [`kernel_gen/symbol_variable/symbol_dim.py`](../../kernel_gen/symbol_variable/symbol_dim.py)
- 当前测试与验收资产：
  - 待同步收口测试：[`test/symbol_variable/test_symbol_dim.py`](../../test/symbol_variable/test_symbol_dim.py)
  - 当前验收入口（本轮不修改）：[`expectation/symbol_variable/symbol_dim.py`](../../expectation/symbol_variable/symbol_dim.py)
  - 关联回归入口：[`expectation/symbol_variable/memory.py`](../../expectation/symbol_variable/memory.py)
- 当前缺口或失败点：
  - `python expectation/symbol_variable/memory.py` 已通过。
  - `python expectation/symbol_variable/symbol_dim.py` 当前失败 `CASE-6` 与 `CASE-8`。
  - 当前实现仍接受 `"3.14"`、`".5"`、`"1e3"`、`"+1"`、`"-2"` 这类数值字面量字符串。
- 当前实现的 `get_symbol()/get_value()` 未完全对齐 SymPy 简化结果：
    - `(A / B / 3).get_value()` 当前为 `"(A/B)/3"`，目标合同要求按约定 SymPy 简化结果收口，例如 `A/(3*B)`。
    - `(A / A).get_value()` 当前为 `"A/A"`，目标合同要求 `1`。
    - `(A // A).get_value()` 当前为 `"floor(A/A)"`，目标合同要求 `1`。
  - 当前 `spec/test` 与用户已确认合同存在分叉：
    - `test/symbol_variable/test_symbol_dim.py` 仍接受 `"3.14"`、`"+1"` 等字符串输入。
    - `spec/symbol_variable/symbol_dim.md` 仍保留 `(A/B/3)` 等旧公开值口径。

## 方案比较与选型

- 不采用方案：`直接用 parse_expr/sympify 作为 SymbolDim 的字符串构造主路径`
- 不采用原因：
  - SymPy 官方 parsing 文档说明 `parse_expr(...)` 默认带 `auto_number`，会把数值字面量解析成 `Integer/Float`，这与“字符串输入只允许符号名、不允许数值字面量字符串”的合同相冲突。
  - `parse_expr(...)` 文档明确提示其内部使用 `eval`，不适合作为当前这个轻量维度对象的默认字符串入口。
  - SymPy best practices 也明确提醒字符串输入与 assumptions 容易产生“同名不同 assumptions 的符号不相等”的问题。
- 采用方案：`保留当前 SymbolDim 公开 API；字符串输入走显式词法校验；运算结果在内部表达与公开值两个口径上都按约定的 SymPy 简化结果收口`
- 最小公开接口：
  - `SymbolDim(value)`：继续是唯一构造入口。
  - `get_symbol()`：返回与约定 SymPy 简化结果一致的 `sympy.Basic`。
  - `get_value()`：静态结果返回 `int | float`，动态结果返回与约定 SymPy 简化结果一致的稳定公开值。

## 公开 API 设计

- 公开入口：`SymbolDim(value)`
- 参数顺序：`value`
- 参数类型：`int | str | sympy.Basic`
- 返回值：`SymbolDim`

```python
from kernel_gen.symbol_variable.symbol_dim import SymbolDim

assert SymbolDim(1).get_symbol() == 1
assert SymbolDim(1).get_value() == 1
assert SymbolDim(12).get_value() == 12
assert SymbolDim(" N ").get_value() == "N"
assert str((SymbolDim("A") + SymbolDim("A")).get_symbol()) == "2*A"
assert (SymbolDim("A") + SymbolDim("A")).get_value() == "2*A"
assert (SymbolDim("A") + 0).get_value() == "A"
assert (SymbolDim("A") - SymbolDim("A")).get_symbol() == 0
assert (SymbolDim("A") - SymbolDim("A")).get_value() == 0
assert (SymbolDim("A") / SymbolDim("A")).get_symbol() == 1
assert (SymbolDim("A") / SymbolDim("A")).get_value() == 1
assert (SymbolDim("A") // SymbolDim("A")).get_symbol() == 1
assert (SymbolDim("A") // SymbolDim("A")).get_value() == 1
```

### 本轮行为收口

- `int` 输入继续合法：`SymbolDim(12)` 合法。
- `str` 输入只接受“符号名”语义，不接受数值字面量字符串。
- `SymbolDim(1)` 合法，但 `SymbolDim("1")` 非法。
- `spec/`、`test/` 也属于本轮收口对象，必须和新合同同步，不允许继续保留旧口径分叉。
- `expectation/` 不属于本轮修改对象，继续作为合同真源与验收资产。
- `get_symbol()` 也属于本轮严格收口范围：
  - 返回值应与约定的 SymPy 简化结果一致。
  - 静态整数结果直接返回 `sympy.Integer/int` 等价值，不再保留未简化表达式。
- `get_value()` 的公开结果口径为：
  - 静态表达式返回 `int | float`
  - 动态表达式返回与约定 SymPy 简化结果一致的稳定公开值
  - 若结果已经是静态整数，不使用字符串承载该结果

## 完成态定义

- [`kernel_gen/symbol_variable/symbol_dim.py`](../../kernel_gen/symbol_variable/symbol_dim.py)、[`spec/symbol_variable/symbol_dim.md`](../../spec/symbol_variable/symbol_dim.md)、[`test/symbol_variable/test_symbol_dim.py`](../../test/symbol_variable/test_symbol_dim.py) 三侧与当前 [`expectation/symbol_variable/symbol_dim.py`](../../expectation/symbol_variable/symbol_dim.py) 保持一致，不再分叉。
- `SymbolDim(12)` 继续合法。
- `SymbolDim(1)` 合法，但 `SymbolDim("1")` 非法。
- 数值字面量字符串如 `"12"`、`"3.14"`、`".5"`、`"1e3"`、`"+1"`、`"-2"` 在构造、运算操作数、比较操作数路径上都按 `ValueError` 收口。
- `get_symbol()` 与 `get_value()` 都与约定 SymPy 简化结果一致，至少覆盖：
  - `A + A -> 2*A`
  - `A + 0 -> A`
  - `A * 1 -> A`
  - `A - A -> 0`
  - `A / A -> 1`
  - `A // A -> 1`
  - `A / B / 3 -> A/(3*B)` 或与约定等价的 SymPy 简化公开值
- [`expectation/symbol_variable/memory.py`](../../expectation/symbol_variable/memory.py) 不因 `SymbolDim` 改造回退。

## 验收设计

- 验收资产：
  - [`expectation/symbol_variable/symbol_dim.py`](../../expectation/symbol_variable/symbol_dim.py)
  - [`expectation/symbol_variable/memory.py`](../../expectation/symbol_variable/memory.py)
- 输入样例：
  - `SymbolDim(1)`
  - `SymbolDim(12)`
  - `SymbolDim(" N ")`
  - `SymbolDim("A") + SymbolDim("A")`
  - `SymbolDim("A") / SymbolDim("A")`
  - 非法输入 `"1"`、`"3.14"`、`".5"`、`"1e3"`、`"+1"`、`"-2"`
- 锁定输出：
  - 合法输入的 `get_symbol()/get_value()` 与约定 SymPy 简化结果一致
  - 非法字符串输入抛 `ValueError`
  - `spec/symbol_variable/symbol_dim.md` 与 `test/symbol_variable/test_symbol_dim.py` 同步到新合同
  - `memory` expectation 对 `SymbolDim` 驱动的 stride 公开值不回退
- 必过命令：
  - `python expectation/symbol_variable/symbol_dim.py`
  - `python expectation/symbol_variable/memory.py`
  - `pytest -q test/symbol_variable/test_symbol_dim.py`

## 阶段拆分

### S1：输入域收口

#### 阶段目标

- 让 `SymbolDim(value)` 的字符串输入域与当前 expectation 对齐：`int` 合法，数值字面量字符串非法。

#### 小任务路线

- 当前小任务编号：`S1`
- 任务新建时只创建 `S1` 的首个 `spec` 任务。
- 后续默认链路为：`S1-spec -> S1-build -> S1-review`。
- `S1` 的收口内容是：冻结输入域合同，随后修改实现/spec/test，最后复核 expectation 与 pytest 中输入域相关 case。

#### 目标 spec / API

- `spec/symbol_variable/symbol_dim.md`
- `公开 API：SymbolDim(value)`

#### 可改文件

- 以 [`kernel_gen/symbol_variable/symbol_dim.py`](../../kernel_gen/symbol_variable/symbol_dim.py) 为主。
- 允许修改与 `SymbolDim` 收口目标直接相关的实现、`spec`、`test` 与辅助模块。
- 不修改 `expectation/`、`agents/standard/` 与其他无关模块。

#### 预期示例代码

```python
from kernel_gen.symbol_variable.symbol_dim import SymbolDim

SymbolDim(1)
SymbolDim(12)
SymbolDim(" N ")
```

#### 预期输出

```text
SymbolDim(1) 合法
SymbolDim(12) 合法
SymbolDim(" N ").get_value() == "N"
SymbolDim("1") -> ValueError
SymbolDim("3.14") -> ValueError
SymbolDim("+1") -> ValueError
```

#### 目标验收资产

- [`expectation/symbol_variable/symbol_dim.py`](../../expectation/symbol_variable/symbol_dim.py)
- [`test/symbol_variable/test_symbol_dim.py`](../../test/symbol_variable/test_symbol_dim.py)
- 锁定构造、操作数、比较三条路径上的非法字符串输入

#### 验收必过项目

- `python expectation/symbol_variable/symbol_dim.py`
- `pytest -q test/symbol_variable/test_symbol_dim.py`

### S2：符号结果简化收口

#### 阶段目标

- 让 `get_symbol()` 与 `get_value()` 都对齐约定的 SymPy 简化结果。

#### 小任务路线

- 当前小任务编号：`S2`
- 任务新建时只创建 `S2` 的首个 `spec` 任务，且必须依赖 `S1` 完成。
- 后续默认链路为：`S2-spec -> S2-build -> S2-review`。
- `S2` 的收口内容是：冻结 `get_symbol()/get_value()` 简化合同，随后修改实现/spec/test，最后复核 expectation 与 pytest 中符号简化相关 case。

#### 目标 spec / API

- `spec/symbol_variable/symbol_dim.md`
- `公开 API：get_symbol()`、`get_value()`

#### 可改文件

- 以 [`kernel_gen/symbol_variable/symbol_dim.py`](../../kernel_gen/symbol_variable/symbol_dim.py) 为主。
- 允许修改与符号结果简化直接相关的实现、`spec`、`test` 与表达式构造辅助逻辑。
- 若当前实现需要拆 helper、调整归一化路径或重构表达式公开值生成流程，允许在相关实现文件内联动修改。
- 不修改 `expectation/`、`agents/standard/` 与其他无关模块。

#### 预期示例代码

```python
from kernel_gen.symbol_variable.symbol_dim import SymbolDim

assert str((SymbolDim("A") + SymbolDim("A")).get_symbol()) == "2*A"
assert (SymbolDim("A") + SymbolDim("A")).get_value() == "2*A"
assert (SymbolDim("A") + 0).get_value() == "A"
assert (SymbolDim("A") - SymbolDim("A")).get_symbol() == 0
assert (SymbolDim("A") / SymbolDim("A")).get_value() == 1
assert (SymbolDim("A") / SymbolDim("A")).get_symbol() == 1
assert (SymbolDim("A") // SymbolDim("A")).get_value() == 1
assert (SymbolDim("A") // SymbolDim("A")).get_symbol() == 1
```

#### 预期输出

```text
内部符号表达与公开值都按约定 SymPy 简化结果收口
同符号约分和常量消除在 get_symbol()/get_value() 两个口径上都可见
```

#### 目标验收资产

- [`expectation/symbol_variable/symbol_dim.py`](../../expectation/symbol_variable/symbol_dim.py)
- [`test/symbol_variable/test_symbol_dim.py`](../../test/symbol_variable/test_symbol_dim.py)
- 锁定 `CASE-5`、`CASE-6` 的内部表达与公开结果

#### 验收必过项目

- `python expectation/symbol_variable/symbol_dim.py`
- `pytest -q test/symbol_variable/test_symbol_dim.py`

### S3：联动回归与边界复核

#### 阶段目标

- 确认 `SymbolDim` 改造不会破坏 `Memory` 侧已通过的 acceptance 合同。

#### 小任务路线

- 当前小任务编号：`S3`
- 任务新建时只创建 `S3` 的首个 `spec` 任务，且必须依赖 `S2` 完成。
- 后续默认链路为：`S3-spec -> S3-build -> S3-review`。
- `S3` 的收口内容是：冻结 SymbolDim 与 Memory 联动回归口径，随后做最小一致性修正，最后复核 `symbol_dim` 与 `memory` 的 expectation 及相关 pytest 闭环。

#### 目标 spec / API

- `spec/symbol_variable/memory.md`
- `公开 API：Memory(...), get_stride()`

#### 可改文件

- 以 [`kernel_gen/symbol_variable/symbol_dim.py`](../../kernel_gen/symbol_variable/symbol_dim.py) 为主。
- 允许修改联动回归中直接暴露问题的相关实现、`spec`、`test` 与最小必要辅助文件。
- 若为保证 [`expectation/symbol_variable/memory.py`](../../expectation/symbol_variable/memory.py) 不回退，需要同步调整 `SymbolDim` 关联实现路径，可一并修改。
- 不修改 `expectation/`、`agents/standard/` 与其他无关模块。

#### 预期示例代码

```python
from kernel_gen.symbol_variable.memory import Memory
from kernel_gen.symbol_variable.type import NumericType

mem = Memory(["M", "K", "N"], NumericType.Float32)
assert mem.get_stride() == ["K*N", "N", 1]
```

#### 预期输出

```text
symbol_dim expectation 通过
memory expectation 继续通过
```

#### 目标验收资产

- [`expectation/symbol_variable/symbol_dim.py`](../../expectation/symbol_variable/symbol_dim.py)
- [`expectation/symbol_variable/memory.py`](../../expectation/symbol_variable/memory.py)
- [`test/symbol_variable/test_symbol_dim.py`](../../test/symbol_variable/test_symbol_dim.py)

#### 验收必过项目

- `python expectation/symbol_variable/symbol_dim.py`
- `python expectation/symbol_variable/memory.py`
- `pytest -q test/symbol_variable/test_symbol_dim.py`

## 已确认项

- `get_symbol()` 也在本轮收口范围内，必须与约定 SymPy 简化结果一致。
- `SymbolDim(1)` 合法，但 `SymbolDim("1")` 非法。
- 只要结果已经是静态整数或静态数值，公开口径直接返回 `int | float`，不要再用字符串承载静态结果。
- 数值字面量字符串按“所有形式一律非法”处理，至少覆盖：
  - `"1"`
  - `"12"`
  - `"+1"`
  - `"-2"`
  - `"3.14"`
  - `".5"`
  - `"1e3"`

## 参考资料

- SymPy assumptions guide：<https://docs.sympy.org/latest/guides/assumptions.html>
  - 说明 assumptions 会直接影响是否能做安全简化，且建议在创建符号时尽可能精确声明 assumptions。
- SymPy best practices：<https://docs.sympy.org/dev/explanation/best-practices.html>
  - 明确提醒避免字符串输入与 assumptions 混用；如果必须解析字符串，应显式传入带 assumptions 的符号字典。
- SymPy parsing docs：<https://docs.sympy.org/latest/modules/parsing.html>
  - `parse_expr` 默认 `auto_number` 会把数字字面量转成 `Integer/Float`，且内部使用 `eval`，不适合直接拿来替代当前轻量构造入口。
- SymPy simplification tutorial：<https://docs.sympy.org/latest/tutorials/intro-tutorial/simplification.html>
  - 强调默认只做在当前 assumptions 下可成立的简化；这支持“把 assumptions 先收准，再定义对外简化口径”。
- SymbolicUtils.jl 文档：<https://symbolicutils.juliasymbolics.org/>
  - 其设计把“构造时的基础 canonicalization”和“显式 simplify”分开，适合作为本次 `get_symbol()` 与 `get_value()` 分层的参考。
- SymEngine simplification guidelines：<https://github.com/symengine/symengine/wiki/Simplifications-Guidelines>
  - 其经验是“只在构造时做快速且明显更简单的化简，其余交给显式 simplify 阶段”，可作为本次重构边界参考。
- Stack Overflow：<https://stackoverflow.com/questions/62821708/sympy-how-to-show-conditions-that-result-in-division-by-zero>
  - 社区对 `x/x -> 1` 的语义存在实际困惑，说明本仓库必须把该行为明确写成合同，而不能继续留在实现隐式行为里。

## 归档记录

时间：2026-04-19 00:29 +0800
经办人：李白
任务：T-20260419-c826852d
任务目标：将 `ARCHITECTURE/plan/symbol_dim_expectation_green_plan.md` 归档到 `agents/codex-multi-agents/log/task_records/done_plan/2026/16/symbol_dim_expectation_green_plan.md`，并完成归档 merge 收口
改动：已在指定 `worktree=/home/lfr/kernelcode_generate/wt-20260419-archive-symbol-dim-plan` 内将主仓当前计划书快照复制到归档目标路径 `agents/codex-multi-agents/log/task_records/done_plan/2026/16/symbol_dim_expectation_green_plan.md`，并在文件尾部追加本次归档记录；本次归档范围限定为新增该 `done_plan` 文件，不修改 `TODO.md`、`DONE.md`、`AGENTS.md`、`skills/`、`expectation/` 或其他共享状态文件
验证：`git -C /home/lfr/kernelcode_generate/wt-20260419-archive-symbol-dim-plan merge --ff-only origin/main` -> 已将归档 `worktree` 从 `2f7aea5cf24221e0fd90e3b97127d31513dc23df` 快进到 `78576ebda143f0ddbd86592a8a26b33212c87e60`；`test -f /home/lfr/kernelcode_generate/ARCHITECTURE/plan/symbol_dim_expectation_green_plan.md` -> `ROOT_SRC_OK`；`test -e /home/lfr/kernelcode_generate/wt-20260419-archive-symbol-dim-plan/agents/codex-multi-agents/log/task_records/done_plan/2026/16/symbol_dim_expectation_green_plan.md` -> 归档目标已创建；`git -C /home/lfr/kernelcode_generate/wt-20260419-archive-symbol-dim-plan status --short -- agents/codex-multi-agents/log/task_records/done_plan/2026/16/symbol_dim_expectation_green_plan.md` -> `?? agents/codex-multi-agents/log/task_records/done_plan/2026/16/symbol_dim_expectation_green_plan.md`
结论：归档文件已在指定 `worktree` 内生成并写入归档记录；下一步提交并推送该归档文件，随后执行当前 merge 任务 `-done` 并回报管理员继续 `-done-plan`
