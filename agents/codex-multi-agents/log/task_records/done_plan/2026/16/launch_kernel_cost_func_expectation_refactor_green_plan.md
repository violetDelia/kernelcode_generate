# launch_kernel_cost_func_expectation_refactor_green_plan.md

## 文档信息

- 创建者：`榕`
- 最后一次更改：`榕`
- 目标 `spec`：
  - [`spec/dialect/tuner.md`](../../spec/dialect/tuner.md)
  - [`spec/dialect/symbol.md`](../../spec/dialect/symbol.md)
  - [`spec/pass/tuning/launch_kernel_cost_func.md`](../../spec/pass/tuning/launch_kernel_cost_func.md)
- 目标 `API`：
  - `LaunchKernelCostFuncPass(cost_kind="compute" | "memory")`
  - `build_registered_pass("launch-kernel-cost-func", {"cost_kind": ...})`
  - `tuner.cost(...){cost_kind=..., op_name=..., ...} -> !symbol.int<...>`
- 目标 `test`：
  - [`test/dialect/test_tuner_dialect.py`](../../test/dialect/test_tuner_dialect.py)
  - [`test/dialect/test_symbol_dialect.py`](../../test/dialect/test_symbol_dialect.py)
  - [`test/pass/test_launch_kernel_cost_func.py`](../../test/pass/test_launch_kernel_cost_func.py)
- 目标 `验收资产`：
  - [`expectation/pass/tuning/launch_kernel_cost_func/basic_all.py`](../../expectation/pass/tuning/launch_kernel_cost_func/basic_all.py)
  - [`expectation/pass/tuning/launch_kernel_cost_func/shared_callee_once.py`](../../expectation/pass/tuning/launch_kernel_cost_func/shared_callee_once.py)
  - [`expectation/pass/tuning/launch_kernel_cost_func/invalid_kind.py`](../../expectation/pass/tuning/launch_kernel_cost_func/invalid_kind.py)
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python expectation/pass/tuning/launch_kernel_cost_func`
  - `pytest -q test/dialect/test_tuner_dialect.py test/dialect/test_symbol_dialect.py test/pass/test_launch_kernel_cost_func.py`
- 目标 `功能实现`：
  - [`kernel_gen/dialect/tuner.py`](../../kernel_gen/dialect/tuner.py)
  - [`kernel_gen/dialect/symbol.py`](../../kernel_gen/dialect/symbol.py)
  - [`kernel_gen/passes/tuning/launch_kernel_cost_func.py`](../../kernel_gen/passes/tuning/launch_kernel_cost_func.py)
  - [`kernel_gen/passes/registry.py`](../../kernel_gen/passes/registry.py)

## 任务清单

| 任务 | 任务号 | 前置任务 | worktree | 记录文件 | 当前状态 |
| --- | --- | --- | --- | --- | --- |
| S1 | `T-20260420-2b0cd9c2` | 无 | `wt-20260420-launch-kernel-cost-s1` | `agents/codex-multi-agents/log/task_records/2026/16/20260420-launch-kernel-cost-s1.md` | `已分发，build/金铲铲大作战，执行中` |
| S2 | `T-20260420-e22d6a1d` | S1 | `wt-20260420-launch-kernel-cost-s2` | `agents/codex-multi-agents/log/task_records/2026/16/20260420-launch-kernel-cost-s2.md` | `已创建，等待 S1` |

## 评审摘要

- 评审结论：`通过`
- 评审人：`守护最好的爱莉希雅`、`大闸蟹`
- 结论摘要：`两位架构师均已通过。当前任务链符合“不拆纯 spec 任务”：S1 收 tuner/symbol/spec/pytest，S2 收 pass/registry/expectation/pass pytest；粒度与依赖合理。合同真源顺序已显式写清，cost_kind=compute|memory、tuner.cost 整数合同，以及 symbol.for / symbol.yield “本轮只要求 !symbol.int 成本链闭环”的边界均已收口，可按当前版本建任务推进。`

## 终验 / 复验 / 修复复核记录

- 结论人：`不适用`
- 结论：`不适用`
- 验证基线：`计划书编写阶段；当前仅完成基线核对与意见整合，未进入执行终验`
- 最小阻断项或通过摘要：`尚未开始执行，不适用`
- 是否已创建修复任务：`不适用`
- 修复任务创建人：`不适用`
- 另一位架构师补充重点：`无`

## 计划目标

- 以 [`expectation/pass/tuning/launch_kernel_cost_func`](../../expectation/pass/tuning/launch_kernel_cost_func) 为唯一行为准，重构 `launch-kernel-cost-func` 与 `tuner.cost`。
- 把旧公开合同 `kind=compute|move|all`、`tuner.cost -> f64`、`kind/device_func` metadata 收口为新合同：`cost_kind=compute|memory`、整数成本链、helper 保留、成本节点不裁剪。
- 同步收口 `symbol.for` / `symbol.yield` 的 carried-value 合同，但本轮只要求 `!symbol.int<...>` 成本链闭环，不顺手泛化到任意 carried 类型。
- 让 `spec`、实现、expectation、pytest 一次性同口径，不再出现“expectation 锁新合同、实现与测试仍按旧合同”的分叉。

## 合同真源顺序

- [`expectation/pass/tuning/launch_kernel_cost_func`](../../expectation/pass/tuning/launch_kernel_cost_func)
- [`spec/dialect/tuner.md`](../../spec/dialect/tuner.md) + [`spec/dialect/symbol.md`](../../spec/dialect/symbol.md) + [`spec/pass/tuning/launch_kernel_cost_func.md`](../../spec/pass/tuning/launch_kernel_cost_func.md)
- [`test/dialect/test_tuner_dialect.py`](../../test/dialect/test_tuner_dialect.py) + [`test/dialect/test_symbol_dialect.py`](../../test/dialect/test_symbol_dialect.py) + [`test/pass/test_launch_kernel_cost_func.py`](../../test/pass/test_launch_kernel_cost_func.py)
- 当前实现

## 当前基线

- 当前公开合同：
  - [`spec/pass/tuning/launch_kernel_cost_func.md`](../../spec/pass/tuning/launch_kernel_cost_func.md) 仍公开 `kind=compute|move|all`、`tuner.cost -> f64`、`kind/device_func` metadata。
  - [`spec/dialect/tuner.md`](../../spec/dialect/tuner.md) 仍要求 `tuner.cost` 包含 `kind/device_func` 且结果固定 `f64`。
  - [`spec/dialect/symbol.md`](../../spec/dialect/symbol.md) 仍把 `symbol.for` carried-value 语义限定为 `f64`。
- 当前公开 API：
  - [`kernel_gen/passes/tuning/launch_kernel_cost_func.py`](../../kernel_gen/passes/tuning/launch_kernel_cost_func.py) 入口仍是 `LaunchKernelCostFuncPass(kind="all")`，registry 只认 `kind`。
  - [`kernel_gen/dialect/tuner.py`](../../kernel_gen/dialect/tuner.py) 的 `TunerCostOp` 仍公开 `kind/cost_kind/op_name/device_func`，结果类型固定 `f64`。
  - [`kernel_gen/dialect/symbol.py`](../../kernel_gen/dialect/symbol.py) 的 `SymbolForOp` / `SymbolYieldOp` carried-value 仍只接受 `f64`。
- 当前实现入口：
  - pass 仍把 `dma.* -> move`、`kernel.* -> compute`，并通过 `arith.constant + arith.addf` 形成 `f64` 成本链。
  - pass 仍为 `tuner.cost` 平铺补齐 `kind/cost_kind/op_name/device_func`。
- 当前测试与验收资产：
  - [`expectation/pass/tuning/launch_kernel_cost_func/basic_all.py`](../../expectation/pass/tuning/launch_kernel_cost_func/basic_all.py) 已经在锁新合同：`cost_kind=compute|memory`、`tuner.cost` 无 `kind/device_func`、整数成本链、`dma.copy` / `kernel.add` 双保留、`dma.view/reshape` helper 保留。
  - [`shared_callee_once.py`](../../expectation/pass/tuning/launch_kernel_cost_func/shared_callee_once.py) 与 [`invalid_kind.py`](../../expectation/pass/tuning/launch_kernel_cost_func/invalid_kind.py) 也已按新合同书写。
  - [`test/pass/test_launch_kernel_cost_func.py`](../../test/pass/test_launch_kernel_cost_func.py) 与 [`test/dialect/test_tuner_dialect.py`](../../test/dialect/test_tuner_dialect.py) 仍锁旧合同。
- 当前缺口或失败点：
  - `ircheck` 现已能接受 `--pass "launch-kernel-cost-func={cost_kind=...}"` 语法，但 pass 本体会把 `cost_kind` 视为未知参数。
  - `expectation` 当前要求整数累计链，而实现与 `symbol dialect` 仍只支持 `f64` carried-value。
  - 旧 `kind/device_func/f64/compute|move|all` 合同散落在 spec、实现与 pytest 中，若不一次性清理，review 会持续卡在合同分叉。

## 方案比较与选型

- 不采用方案：只修改 pass 参数名，从 `kind` 改为 `cost_kind`，其他 `tuner.cost` attrs 与 `f64` 逻辑暂时保留。
- 不采用原因：
  - expectation 已经锁定 `tuner.cost` 无 `kind/device_func`，仅改参数名无法消除公开合同分叉。
  - 仅改参数名会导致 `tuner.cost`、`symbol.for`、pytest、spec 四层继续混用旧 `f64` 语义，后续 review 成本更高。
- 不采用方案：只调整 expectation，让其迁就当前实现。
- 不采用原因：
  - 用户已明确要求“按照这个 expectation 重构改 pass”，expectation 是这次专题的真源，不应回退迁就旧实现。
- 采用方案：
  - 以 expectation 为真源，同时修改 `spec + dialect + pass + registry + pytest`。
  - 同步把 `symbol.for / symbol.yield` 的 carried-value 合同从“固定 `f64`”收口到“本专题仅支持 `!symbol.int<...>` 成本链闭环”，不在本轮顺手泛化到任意 carried 类型。
- 最小公开接口：
  - `LaunchKernelCostFuncPass(cost_kind="compute" | "memory")`
  - `build_registered_pass("launch-kernel-cost-func", {"cost_kind": ...})`
  - `tuner.cost(...){cost_kind=..., op_name=..., ...} -> !symbol.int<...>`

## 公开 API 设计

- 公开入口：`LaunchKernelCostFuncPass`
- 参数顺序：`cost_kind`
- 参数类型：`str`
- 返回值：`ModuleOp`

```python
from kernel_gen.passes.tuning.launch_kernel_cost_func import LaunchKernelCostFuncPass

module = LaunchKernelCostFuncPass(cost_kind="compute").run(module)
```

- 公开入口：`build_registered_pass`
- 参数顺序：`name, options`
- 参数类型：`str, dict[str, str]`
- 返回值：`Pass`

```python
from kernel_gen.passes.registry import build_registered_pass

pass_obj = build_registered_pass(
    "launch-kernel-cost-func",
    {"cost_kind": "memory"},
)
```

- 公开入口：`tuner.cost`
- 参数顺序：`operands..., attrs`
- 参数类型：`SSAValue..., {cost_kind, op_name, ...原 op attrs...}`
- 返回值：`!symbol.int<"...">`

```mlir
%cost = tuner.cost(%dst, %src) {cost_kind = "compute", op_name = "dma.copy"} : (!nn.memory<[M], [1], f32, #nn.space<global>>, !nn.memory<[M], [1], f32, #nn.space<global>>) -> !symbol.int<"COST">
```

- 公开入口：`symbol.for / symbol.yield`
- 参数顺序：`start, end, step, iter_args(%acc = %zero), yield`
- 参数类型：`!symbol.int<...>`
- 返回值：`!symbol.int<...>`

```mlir
%zero = symbol.const 0 : !symbol.int<"0">
%total = symbol.for %i = %start to %end step %step iter_args(%acc = %zero) {iter = #symbol.iter<start = "0", end = "M", step = "1">} -> !symbol.int<"TOTAL"> {
  %next = symbol.add %acc, %local : !symbol.int<"ACC">, !symbol.int<"LOCAL"> -> !symbol.int<"NEXT">
  symbol.yield %next : !symbol.int<"NEXT">
}
```

## 完成态定义

- `launch-kernel-cost-func` 的公开参数只保留 `cost_kind=compute|memory`，旧 `kind` 不再是公开输入。
- `tuner.cost` 的公开 attrs 只保留 `cost_kind`、`op_name` 与 expectation 要求保留的原 op 公开 attrs；`kind/device_func` 全部移除。
- `tuner.cost`、`symbol.for` carried value、`symbol.yield`、cost function 返回值形成完整的 `!symbol.int<...>` 成本链，不再混入 `f64` / `arith.addf`。
- `dma.copy` 与 `kernel.add` 在 `cost_kind=compute` 和 `cost_kind=memory` 两种视角下都继续生成 `tuner.cost`；`dma.view/dma.reshape` 只保留 helper，不生成 `tuner.cost`。
- `basic_all.py`、`shared_callee_once.py`、`invalid_kind.py` 与实现、spec、pytest 同口径，不再存在黑盒 expectation 与实现相互打架的情况。

## 验收设计

- 验收资产：
  - [`expectation/pass/tuning/launch_kernel_cost_func/basic_all.py`](../../expectation/pass/tuning/launch_kernel_cost_func/basic_all.py)
  - [`expectation/pass/tuning/launch_kernel_cost_func/shared_callee_once.py`](../../expectation/pass/tuning/launch_kernel_cost_func/shared_callee_once.py)
  - [`expectation/pass/tuning/launch_kernel_cost_func/invalid_kind.py`](../../expectation/pass/tuning/launch_kernel_cost_func/invalid_kind.py)
  - [`test/dialect/test_tuner_dialect.py`](../../test/dialect/test_tuner_dialect.py)
  - [`test/dialect/test_symbol_dialect.py`](../../test/dialect/test_symbol_dialect.py)
  - [`test/pass/test_launch_kernel_cost_func.py`](../../test/pass/test_launch_kernel_cost_func.py)
- 输入样例：
  - `--pass "launch-kernel-cost-func={cost_kind=compute}"`
  - `--pass "launch-kernel-cost-func={cost_kind=memory}"`
  - `--pass "launch-kernel-cost-func={cost_kind=invalid}"`
- 锁定输出：
  - `tuner.cost` 无 `kind/device_func`
  - `cost_kind=compute|memory`
  - `tuner.cost` 与累计链返回 `!symbol.int<...>`
  - `dma.copy` / `kernel.add` 不裁剪
  - `dma.view/dma.reshape` helper 保留
- 必过命令：
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python expectation/pass/tuning/launch_kernel_cost_func`
  - `pytest -q test/dialect/test_tuner_dialect.py test/dialect/test_symbol_dialect.py test/pass/test_launch_kernel_cost_func.py`

## 阶段拆分

### S1：方言合同与整数 carried-value 收口

#### 阶段目标

- 一次收口 `tuner.cost` 与 `symbol.for / symbol.yield` 的新公开合同，并让 dialect 层与对应 pytest 同口径。

#### 目标 spec / API

- [`spec/dialect/tuner.md`](../../spec/dialect/tuner.md)
- [`spec/dialect/symbol.md`](../../spec/dialect/symbol.md)
- 公开 API：
  - `tuner.cost(...){cost_kind=..., op_name=..., ...} -> !symbol.int<...>`
  - `symbol.for ... iter_args(%acc = %zero) ... -> !symbol.int<...>`
  - `symbol.yield %next : !symbol.int<...>`

#### 禁止修改面 / 合同真源

- 禁止修改面：`无额外禁止面`
- 合同真源：[`expectation/pass/tuning/launch_kernel_cost_func`](../../expectation/pass/tuning/launch_kernel_cost_func)

#### 预期示例代码

```mlir
%zero = symbol.const 0 : !symbol.int<"0">
%total = symbol.for %i = %start to %end step %step iter_args(%acc = %zero) {iter = #symbol.iter<start = "0", end = "M", step = "1">} -> !symbol.int<"TOTAL"> {
  %local = tuner.cost(%dst, %src) {cost_kind = "compute", op_name = "dma.copy"} : (!nn.memory<[M], [1], f32, #nn.space<global>>, !nn.memory<[M], [1], f32, #nn.space<global>>) -> !symbol.int<"LOCAL">
  %next = symbol.add %acc, %local : !symbol.int<"ACC">, !symbol.int<"LOCAL"> -> !symbol.int<"NEXT">
  symbol.yield %next : !symbol.int<"NEXT">
}
```

#### 预期输出

```text
tuner.cost 无 kind/device_func，结果类型为 !symbol.int<...>
symbol.for / symbol.yield carried-value 本轮只要求支持 !symbol.int<...>
```

#### 目标验收资产

- [`test/dialect/test_tuner_dialect.py`](../../test/dialect/test_tuner_dialect.py)
- [`test/dialect/test_symbol_dialect.py`](../../test/dialect/test_symbol_dialect.py)
- 该阶段要锁定：
  - `tuner.cost` 新 attrs 与整数结果
  - `symbol.for / symbol.yield` 仅面向 `!symbol.int<...>` 的 carried-value 合同

#### 验收必过项目

- `pytest -q test/dialect/test_tuner_dialect.py test/dialect/test_symbol_dialect.py`

#### 任务新建建议

- `任务类型：build`
- `任务目标：收口 tuner.cost 与 symbol.for/yield 的整数合同，并同步 spec 与 dialect pytest`
- `记录文件：agents/codex-multi-agents/log/task_records/2026/16/20260420-launch-kernel-cost-s1.md`

### S2：pass、registry、expectation 与 pytest 收口

#### 阶段目标

- 让 `launch-kernel-cost-func`、registry、expectation 与 pass pytest 全部对齐到新合同，不再保留旧入口和旧行为。

#### 目标 spec / API

- [`spec/pass/tuning/launch_kernel_cost_func.md`](../../spec/pass/tuning/launch_kernel_cost_func.md)
- 公开 API：
  - `LaunchKernelCostFuncPass(cost_kind="compute" | "memory")`
  - `build_registered_pass("launch-kernel-cost-func", {"cost_kind": ...})`

#### 禁止修改面 / 合同真源

- 禁止修改面：`无额外禁止面`
- 合同真源：
  - [`expectation/pass/tuning/launch_kernel_cost_func/basic_all.py`](../../expectation/pass/tuning/launch_kernel_cost_func/basic_all.py)
  - [`expectation/pass/tuning/launch_kernel_cost_func/shared_callee_once.py`](../../expectation/pass/tuning/launch_kernel_cost_func/shared_callee_once.py)
  - [`expectation/pass/tuning/launch_kernel_cost_func/invalid_kind.py`](../../expectation/pass/tuning/launch_kernel_cost_func/invalid_kind.py)

#### 预期示例代码

```python
from kernel_gen.passes.registry import build_registered_pass

pass_obj = build_registered_pass(
    "launch-kernel-cost-func",
    {"cost_kind": "compute"},
)
module = pass_obj.run(module)
```

```text
func.func @_cost_compute__device_kernel(...) -> !symbol.int<...>
```

#### 预期输出

```text
pass 只认 cost_kind=compute|memory
invalid cost_kind 报固定错误短语
dma.copy 与 kernel.add 两种视角下都保留 tuner.cost
dma.view/dma.reshape 仅 helper 保留
```

#### 目标验收资产

- [`expectation/pass/tuning/launch_kernel_cost_func`](../../expectation/pass/tuning/launch_kernel_cost_func)
- [`test/pass/test_launch_kernel_cost_func.py`](../../test/pass/test_launch_kernel_cost_func.py)
- 该阶段要锁定：
  - `cost_kind` 新入口
  - shared callee dedup
  - helper 保留、成本节点不裁剪
  - 旧 `kind/device_func/f64/compute|move|all` 全部清理

#### 验收必过项目

- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python expectation/pass/tuning/launch_kernel_cost_func`
- `pytest -q test/pass/test_launch_kernel_cost_func.py`

#### 任务新建建议

- `任务类型：build`
- `任务目标：收口 launch-kernel-cost-func pass、registry、expectation 与 pass pytest 到新合同`
- `记录文件：agents/codex-multi-agents/log/task_records/2026/16/20260420-launch-kernel-cost-s2.md`

## 待确认项

- 当前无额外待确认项。

## 用户确认与协同约束

- 用户确认状态：`已确认`
- 未确认事项：`无`
- 用户确认结论：
  - 用户已确认按当前 expectation 重构 pass。
  - 用户已确认任务不要拆得过碎。
  - 用户已确认不单独拆“纯 spec 任务”。
  - 用户已确认不单独设“刻意验收”任务。
- 未确认前处理要求：`不得自行补假设`
- 若用户要求至少询问 3 人：`已执行；本计划已整合不少于 3 个对象意见。`
- 询问记录 1：`睡觉小分队 / agents/codex-multi-agents/log/talk.log / 明确了 spec 最小必须写死的真源顺序、cost_kind 参数、整数成本链、helper 保留与 shared callee dedup 边界`
- 询问记录 2：`小李飞刀 / agents/codex-multi-agents/log/talk.log / 明确了实现最小闭环是 pass 参数解析 + registry + tuner.cost 构造/验证 + pytest/expectation 一次收口，并点名旧 kind/device_func/f64 调用点最易炸`
- 询问记录 3：`提莫炖蘑菇 / agents/codex-multi-agents/log/talk.log / 明确了最小阻断项是 expectation 真源、计划书命令、task-site 入口必须一致，以及旧 kind/device_func 文本必须一次性清理`

## 参考资料

- [`agents/standard/计划书标准.md`](../../agents/standard/计划书标准.md)：计划书结构与必填项。
- [`agents/standard/计划书模板.md`](../../agents/standard/计划书模板.md)：本计划书写作模板。
- [`expectation/pass/tuning/launch_kernel_cost_func`](../../expectation/pass/tuning/launch_kernel_cost_func)：本次重构的黑盒合同真源。
- [`spec/tools/ircheck.md`](../../spec/tools/ircheck.md)：expectation 使用的 `COMPILE_ARGS` 与 `CHECK*` 语法边界。
