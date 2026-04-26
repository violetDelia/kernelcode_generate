# nn_lowering_pass_refactor_green_plan.md

## 文档信息

- 创建者：`大闸蟹`
- 最后一次更改：`守护最好的爱莉希雅`
- 目标 `spec`：
  - [`spec/pass/lowering/nn_lowering/spec.md`](../../spec/pass/lowering/nn_lowering/spec.md)
  - [`spec/pass/lowering/nn_lowering/nn_lowering_utility.md`](../../spec/pass/lowering/nn_lowering/nn_lowering_utility.md)
  - [`spec/pass/lowering/nn_lowering/element_binary_lowering.md`](../../spec/pass/lowering/nn_lowering/element_binary_lowering.md)
  - [`spec/pass/lowering/nn_lowering/select_cast_lowering.md`](../../spec/pass/lowering/nn_lowering/select_cast_lowering.md)
- 目标 `API`：
  - [`kernel_gen/passes/lowering/nn_lowering/__init__.py`](../../kernel_gen/passes/lowering/nn_lowering/__init__.py)
  - [`kernel_gen/passes/lowering/nn_lowering/nn_lowering.py`](../../kernel_gen/passes/lowering/nn_lowering/nn_lowering.py)
- 目标 `test`：
  - [`test/pass/nn_lowering`](../../test/pass/nn_lowering)
  - [`test/pass/test_pass_manager.py`](../../test/pass/test_pass_manager.py)
  - [`test/pass/test_pipeline_default_lowering.py`](../../test/pass/test_pipeline_default_lowering.py)
- 目标 `验收资产`：
  - [`expectation/pass/lowing/nn_lowering`](../../expectation/pass/lowing/nn_lowering)
- 目标 `功能实现`：
  - [`kernel_gen/passes/lowering/nn_lowering`](../../kernel_gen/passes/lowering/nn_lowering)

## 任务清单

> 本计划按严格串行推进：`S1 -> S2 -> S3 -> S4 -> S5 -> S6 -> S7`。每一段都先把对应 `spec` 与文件职责写清，再做实现与测试收口；不允许先写实现、后补职责说明。唯一公开 pass 始终只有 `NnLoweringPass` / `lower-nn`。

| 任务 | 前置任务 | worktree | 记录文件 | 任务形态 |
| --- | --- | --- | --- | --- |
| `S1` | `无` | `wt-20260412-nn-lowering-s1` | `20260412-nn-lowering-s1.md` | `收口任务（规格+实现+测试）` |
| `S2` | `S1` | `wt-20260412-nn-lowering-s2` | `20260412-nn-lowering-s2.md` | `收口任务（规格+实现+测试）` |
| `S3` | `S2` | `wt-20260412-nn-lowering-s3` | `20260412-nn-lowering-s3.md` | `收口任务（规格+实现+测试）` |
| `S4` | `S3` | `wt-20260412-nn-lowering-s4` | `20260412-nn-lowering-s4.md` | `收口任务（规格+实现+测试）` |
| `S5` | `S4` | `wt-20260412-nn-lowering-s5` | `20260412-nn-lowering-s5.md` | `收口任务（规格+实现+测试）` |
| `S6` | `S5` | `wt-20260412-nn-lowering-s6` | `20260412-nn-lowering-s6.md` | `收口任务（规格+实现+测试）` |
| `S7` | `S6` | `wt-20260412-nn-lowering-s7` | `20260412-nn-lowering-s7.md` | `收口任务（规格+实现+测试）` |

> `2026-04-14 09:19 +0800` 起，本计划按用户最新口径重开；`S1~S7` 仅保留历史过程，不再等同于当前有效完成态。重开后的执行链路改为 `R1 -> R2 -> R3`，且明确取消 element_binary mixed scalar 对旧 `dma.broadcast` 接口的兼容。

| 重开任务 | 前置任务 | worktree | 记录文件 | 任务形态 |
| --- | --- | --- | --- | --- |
| `R1` | `无` | `wt-20260414-nn-lowering-reopen-r1` | `20260414-nn-lowering-reopen-r1.md` | `build（实现+测试收口）` |
| `R2` | `R1` | `wt-20260414-nn-lowering-reopen-r1` | `20260414-nn-lowering-reopen-r1.md` | `review` |
| `R3` | `R2` | `wt-20260414-nn-lowering-reopen-r1` | `20260414-nn-lowering-reopen-r1.md` | `merge` |

## 评审摘要

- 评审结论：`通过`
- 评审人：`守护最好的爱莉希雅`
- 结论摘要：`本次重写后的计划以当前仓库实现为基线：先收口现有 nn_lowering 目录与唯一公开 pass，再按 family 增量拆出对应文件；稳定清单只保留当前四份现有文件及对应 spec，S4~S6 到阶段时再新增 family 文件与同名 spec。`
- 补充说明：`2026-04-13 已由架构侧补齐 expectation/pass/lowing/nn_lowering/softmax.py，并同步修正 exp / reduce 系列 expectation 的测试映射说明；S5 后续执行继续只处理实现与测试收口。`
- 补充说明：`2026-04-13 已由架构侧同步 element_binary/{add,sub,mul,div,truediv} 的 mixed scalar expectation，统一收口为 dma.alloc + dma.broadcast + kernel.binary_elewise，并去掉 dma.fill；按 PYTHONPATH=worktree:root 且 cwd=worktree 复跑 python -m expectation.pass.lowing.nn_lowering 已通过。`
- `2026-04-14 用户补充口径`：
  - [`expectation/pass/lowing/nn_lowering/element_binary`](../../expectation/pass/lowing/nn_lowering/element_binary) 中，标量源统一视为 `scalar -> memory` 物化链，使用 `dma.alloc + dma.fill + kernel.binary_elewise`
  - `dma.broadcast` 仅用于 memory 源的显式广播；不再用于 `symbol.int / const-symbol` 这类标量源
- `2026-04-14 架构口径`：
  - [`expectation/pass/lowing/nn_lowering/element_binary/add.py`](../../expectation/pass/lowing/nn_lowering/element_binary/add.py) 与 [`expectation/pass/lowing/nn_lowering/element_binary/sub.py`](../../expectation/pass/lowing/nn_lowering/element_binary/sub.py) 的 tracked expectation 由架构侧直接维护；本轮不再授权 `build` 执行人继续修改这两个 tracked 文件。
  - 本轮收口范围按 `add.py` / `sub.py` 的 `static#1 + static#2` 一并执行，并同步收口对应的动态 `const-symbol` alloc / fill 顺序口径。
  - 若任务 worktree 缺 expectation 资产，可从主仓镜像到临时位置做本地验证；镜像内容不作为正常提交物。
  - `T-20260413-a8b05b61` 后续只保留复跑验证、补记录与续推，不再以“等待 expectation 授权”阻塞。

## 最终验收补充（2026-04-13 22:14）

- `最终验收结论`：`不通过`
- `验收人`：`守护最好的爱莉希雅`
- `验证结果`：
  - `pytest -q test/pass/nn_lowering test/pass/test_pass_manager.py test/pass/test_pipeline_default_lowering.py` => `60 passed`
  - `PYTHONPATH=. python -m expectation.pass.lowing.nn_lowering` => `失败`
- `最小阻断项`：
  - [`expectation/pass/lowing/nn_lowering/element_binary/add.py`](../../expectation/pass/lowing/nn_lowering/element_binary/add.py) 的 `CASE-add-memory-static`
  - [`expectation/pass/lowing/nn_lowering/element_binary/sub.py`](../../expectation/pass/lowing/nn_lowering/element_binary/sub.py) 的 `CASE-sub-memory-static`
  - 两处都把 `symbol.get_dim(%lhs)` 锁成 `func.func` 之后的连续 `CHECK-NEXT` 行；当前实现输出在该位置已不满足该相邻顺序，导致目录级 expectation 入口失败
- `修复范围`：
  - 仅复核并修复 `element_binary/add.py`、`element_binary/sub.py` 静态 case 的 ircheck 合同，使其与当前 `lower-nn` 公开行为一致
  - 不扩展到其它 family、新 pass、或与本次失败无关的实现重构
- `大闸蟹复核（2026-04-13 22:16）`：
  - 复跑 `pytest -q test/pass/nn_lowering` => `40 passed`
  - 复跑 `pytest -q test/pass/test_pass_manager.py -k "lower-nn or nn_lowering"` => `13 passed`
  - 复跑 `pytest -q test/pass/test_pipeline_default_lowering.py` => `2 passed`
  - 复跑 `PYTHONPATH=. python -m expectation.pass.lowing.nn_lowering` => `失败`
  - 复核结论与上述阻断项一致：当前只能判定 `不通过`
  - 架构侧修复任务已补建且不重复建单：[`TODO.md`](../../TODO.md) 中 `T-20260413-a8b05b61`

## 最终验收补充（2026-04-14 06:55）

- `最终验收结论`：`通过`
- `验收人`：`守护最好的爱莉希雅`
- `验证结果`：
  - `pytest -q test/pass/nn_lowering test/pass/test_pass_manager.py test/pass/test_pipeline_default_lowering.py` => `60 passed`
  - `PYTHONPATH=. python -m expectation.pass.lowing.nn_lowering` => `通过`
- `收口说明`：
  - [`expectation/pass/lowing/nn_lowering/element_binary/add.py`](../../expectation/pass/lowing/nn_lowering/element_binary/add.py) 与 [`expectation/pass/lowing/nn_lowering/element_binary/sub.py`](../../expectation/pass/lowing/nn_lowering/element_binary/sub.py) 的 `static#1 + static#2` 已按当前公开 lowering 行为收口。
  - 任务链 [`agents/codex-multi-agents/log/task_records/2026/15/20260413-nn-lowering-final-fix.md`](../../agents/codex-multi-agents/log/task_records/2026/15/20260413-nn-lowering-final-fix.md) 已记录 build / review / merge 收尾过程；tracked expectation 由架构侧直接维护，执行链仅做临时镜像验证，不混入额外 expectation 提交。
  - 本计划要求的两类终验资产已在主仓闭环：`test/pass/nn_lowering` 目录级 pytest 通过，`expectation/pass/lowing/nn_lowering` 目录级入口通过。
- `结论摘要`：
  - 当前主仓结果已满足本计划的最终完成态与验收设计，可按归档链路继续推进。

## 用户重开结论（2026-04-14 09:19）

- `当前结论`：`重开，原“通过”结论失效`
- `触发原因`：
  - 用户已明确新增合同：[`expectation/pass/lowing/nn_lowering/element_binary`](../../expectation/pass/lowing/nn_lowering/element_binary) 中，动态标量与其它标量源统一走 `dma.fill` 物化；只有 memory 源才允许走 `dma.broadcast`
  - 用户已明确要求：取消与旧接口的兼容，不再保留 element_binary mixed scalar 通过 `dma.broadcast` 的旧链路
- `当前最小阻断项`：
  - [`kernel_gen/passes/lowering/nn_lowering/element_binary_lowering.py`](../../kernel_gen/passes/lowering/nn_lowering/element_binary_lowering.py) 仍把 mixed element binary / compare 标量统一物化为 `dma.alloc + dma.broadcast`
  - [`test/pass/nn_lowering/test_lowering_nn_lowering.py`](../../test/pass/nn_lowering/test_lowering_nn_lowering.py) 仍以 `DmaBroadcastOp` 断言 mixed element binary scalar 的旧行为
  - 当前 `expectation + spec` 已改为 `dma.fill`，而 `实现 + 测试` 仍保留旧 `dma.broadcast`，计划书此前的“通过”已不再代表最新用户口径下的真实完成态
- `取消兼容边界`：
  - 不再接受 element binary mixed scalar 同时兼容 `dma.fill` 与 `dma.broadcast` 两套输出
  - `dma.broadcast` 仅保留给 mixed compare 与 memory-source 显式广播链路
  - 本轮不扩展到其它 family，也不重开 `lower-nn` 公开 API 名称兼容
- `新的修复目标`：
  - 让 element binary mixed scalar 在实现、测试、expectation、spec 四个载体上统一收口为 `dma.alloc + dma.fill + kernel.binary_elewise`
  - 保持 mixed compare 继续走 `dma.alloc + dma.broadcast + kernel.binary_elewise`
- 目录级验收重新回到：
    - `pytest -q test/pass/nn_lowering test/pass/test_pass_manager.py test/pass/test_pipeline_default_lowering.py`
    - `PYTHONPATH=. python -m expectation.pass.lowing.nn_lowering`

## 重开终验补充（2026-04-14 11:25）

- `终验结论`：`不通过`
- `验收人`：`守护最好的爱莉希雅`
- `验证结果`：
  - `pytest -q test/pass/nn_lowering test/pass/test_pass_manager.py test/pass/test_pipeline_default_lowering.py` => `60 passed`（含 nn_lowering mark 警告）
  - `PYTHONPATH=. python -m expectation.pass.lowing.nn_lowering` => `失败`
- `最小阻断项`：
  - [`expectation/pass/lowing/nn_lowering/element_binary/add.py`](../../expectation/pass/lowing/nn_lowering/element_binary/add.py) `CASE-add` 的 `static#2`：`CHECK-NEXT` 未命中 `dma.fill`。
  - [`expectation/pass/lowing/nn_lowering/element_binary/sub.py`](../../expectation/pass/lowing/nn_lowering/element_binary/sub.py) `CASE-sub` 的 `static#2`：`CHECK-NEXT` 未命中 `dma.fill`。
  - [`expectation/pass/lowing/nn_lowering/element_binary/mul.py`](../../expectation/pass/lowing/nn_lowering/element_binary/mul.py) `CASE-mul` 的 `static#2`：`CHECK-NEXT` 未命中 `dma.fill`。
  - [`expectation/pass/lowing/nn_lowering/element_binary/div.py`](../../expectation/pass/lowing/nn_lowering/element_binary/div.py) `CASE-div` 的 `static#2`：`CHECK-NEXT` 未命中 `dma.fill`。
  - [`expectation/pass/lowing/nn_lowering/element_binary/truediv.py`](../../expectation/pass/lowing/nn_lowering/element_binary/truediv.py) `CASE-truediv` 的 `static#2`：`CHECK-NEXT` 未命中 `dma.fill`。
- `修复范围`：
  - 仅修复 mixed scalar（const / symbol）路径在 `element_binary` lowering 中的 `dma.fill` 输出与顺序，使其与 expectation 约束一致。
  - 不恢复旧 `dma.broadcast` 对 scalar 的兼容；mixed compare 仍保持 `dma.broadcast`。

## 修复任务（2026-04-14 11:25）

- `build`：`T-20260414-e056a6e4`，任务目标：`修复：element_binary mixed scalar static#2 的 dma.fill 顺序/缺失导致 expectation 失败`。
- `review`：`T-20260414-d28823bc`
- `merge`：`T-20260414-c5719e1b`

## 重开终验补充（2026-04-14 13:30）

- `终验结论`：`通过`
- `验收人`：`守护最好的爱莉希雅`
- `验收依据`：
  - 任务记录 [`agents/codex-multi-agents/log/task_records/2026/16/20260414-nn_lowering-reopen-fix.md`](../../agents/codex-multi-agents/log/task_records/2026/16/20260414-nn-lowering-reopen-fix.md) 已给出以下通过结果：
    - `pytest -q test/pass/nn_lowering` => `40 passed`
    - `pytest -q test/pass/test_pass_manager.py test/pass/test_pipeline_default_lowering.py` => `20 passed`
    - `PYTHONPATH=<worktree>:<repo> python -m expectation.pass.lowing.nn_lowering` => 通过
    - `PYTHONPATH=<worktree>:<repo> python -m expectation.pass.lowing.nn_lowering.element_binary` => 通过
    - `PYTHONPATH=<worktree>:<repo> python -m expectation.pass.lowing.nn_lowering.element_compare` => 通过
- `结论摘要`：
  - mixed scalar element binary 已统一为 `dma.fill` 路径，mixed compare 继续走 `dma.broadcast`，实现/测试/spec 已对齐。
  - 修复链最终以 `T-20260414-e056a6e4` 完成；`T-20260414-d28823bc` 与 `T-20260414-c5719e1b` 判定为重复任务并已收口。

## 计划目标

- 将 [`kernel_gen/passes/lowering/nn_lowering`](../../kernel_gen/passes/lowering/nn_lowering) 收口为**一个公开 pass + 多个内部 family lowering 文件**的结构。
- 公开口径只有：
  - `from kernel_gen.passes.lowering.nn_lowering import NnLoweringPass, NnLoweringError`
  - pass 名 `lower-nn`
- 任何 family 文件都**不得再定义额外 pass**；它们只承载该 family 的 lowering 逻辑与局部 helper。
- 每个稳定 lowering 文件都必须有对应 spec；没有对应 spec 的文件与接口，不写入本计划完成态。
- 本计划不把“实现现状”当作最终合同；实现可分阶段调整，但计划里定义的最终结构必须清楚、唯一、可验收。
- 最终验收不是“部分 leaf 通过”，而是 [`expectation/pass/lowing/nn_lowering`](../../expectation/pass/lowing/nn_lowering) 目录级可运行，且 [`test/pass/nn_lowering`](../../test/pass/nn_lowering) 目录级通过。

## 当前基线（按主仓现状）

- 当前已经存在的 `nn_lowering` 文件只有：
  - [`kernel_gen/passes/lowering/nn_lowering/nn_lowering.py`](../../kernel_gen/passes/lowering/nn_lowering/nn_lowering.py)
  - [`kernel_gen/passes/lowering/nn_lowering/nn_lowering_utility.py`](../../kernel_gen/passes/lowering/nn_lowering/nn_lowering_utility.py)
  - [`kernel_gen/passes/lowering/nn_lowering/element_binary_lowering.py`](../../kernel_gen/passes/lowering/nn_lowering/element_binary_lowering.py)
  - [`kernel_gen/passes/lowering/nn_lowering/select_cast_lowering.py`](../../kernel_gen/passes/lowering/nn_lowering/select_cast_lowering.py)
- 当前还不存在对应 child spec；只有总 spec [`spec/pass/lowering/nn_lowering/spec.md`](../../spec/pass/lowering/nn_lowering/spec.md)。
- 当前实现结构与目标不一致：
  - [`element_binary_lowering.py`](../../kernel_gen/passes/lowering/nn_lowering/element_binary_lowering.py) 里仍有 `LowerNnElementBinaryPass`
  - [`select_cast_lowering.py`](../../kernel_gen/passes/lowering/nn_lowering/select_cast_lowering.py) 里仍有 `LowerNnSelectCastPass`
  - [`nn_lowering.py`](../../kernel_gen/passes/lowering/nn_lowering/nn_lowering.py) 仍直接承载 `exp / reduce / softmax / matmul / img2col / broadcast / transpose / broadcast_to / fill / copy` 的 lowering
- 当前测试与 expectation 已经部分拆细：
  - [`test/pass/nn_lowering`](../../test/pass/nn_lowering) 已有按 op 拆分的测试文件
  - [`expectation/pass/lowing/nn_lowering`](../../expectation/pass/lowing/nn_lowering) 已有 `element_binary / element_compare / reduce / img2col` 等目录
- 当前主要问题不是“没有开始拆”，而是“拆了一半”：
  - 文件职责边界不统一
  - spec 没跟上文件拆分
  - expectation 目录级入口未收口
  - `nn_lowering.py` 仍承担过多 family 逻辑

## 方案比较与选型

- 不采用方案：继续把所有 lowering 维持在 [`nn_lowering.py`](../../kernel_gen/passes/lowering/nn_lowering/nn_lowering.py) 单文件中。
  - 原因：当前 `test` 与 `expectation` 已按 op family 拆分，单文件会继续放大改动面，职责也无法对齐 spec。
- 不采用方案：把每个 family 再做成一个独立 pass。
  - 原因：用户要求最终只有一个 pass；family 文件只是实现拆分，不是公开执行单元。
- 不采用方案：先写多个新文件，再回头补 spec。
  - 原因：这会继续制造“实现里有文件，计划/规范里没有定义”的混乱。
- 采用方案：按当前实现为基线，先收口现有 4 个文件与唯一公开 pass，再逐段把 `nn_lowering.py` 内剩余 family 拆到带 spec 的新文件中。
  - `nn_lowering.py`：唯一公开 pass 入口与顶层调度
  - `nn_lowering_utility.py`：共享 helper
  - `element_binary_lowering.py`：element binary / compare
  - `select_cast_lowering.py`：select / cast
  - 后续新增文件必须同步新增同名 spec，并在计划书中明确负责的 op 与必过 expectation

## 公开 API 设计

### 一、唯一公开接口

```python
from kernel_gen.passes.lowering.nn_lowering import NnLoweringPass, NnLoweringError

module = NnLoweringPass().run(module)
```

- 公开类：`NnLoweringPass`
- 公开错误：`NnLoweringError`
- 公开 pass 名：`lower-nn`
- 除上述三项外，本计划不新增其它公开接口。

### 二、文件职责与对应 spec

| 文件 | 对应 spec | 是否公开 | 负责内容 | 必过验收资产 |
| --- | --- | --- | --- | --- |
| [`kernel_gen/passes/lowering/nn_lowering/__init__.py`](../../kernel_gen/passes/lowering/nn_lowering/__init__.py) | [`spec/pass/lowering/nn_lowering/spec.md`](../../spec/pass/lowering/nn_lowering/spec.md) | `是` | 公开导出 `NnLoweringPass` / `NnLoweringError` | [`test/pass/nn_lowering/public_name.py`](../../test/pass/nn_lowering/public_name.py) |
| [`kernel_gen/passes/lowering/nn_lowering/nn_lowering.py`](../../kernel_gen/passes/lowering/nn_lowering/nn_lowering.py) | [`spec/pass/lowering/nn_lowering/spec.md`](../../spec/pass/lowering/nn_lowering/spec.md) | `是` | 唯一 pass、调度顺序、顶层遍历、错误汇总 | [`test/pass/test_pass_manager.py`](../../test/pass/test_pass_manager.py)、[`test/pass/test_pipeline_default_lowering.py`](../../test/pass/test_pipeline_default_lowering.py)、[`expectation/pass/lowing/nn_lowering`](../../expectation/pass/lowing/nn_lowering) |
| [`kernel_gen/passes/lowering/nn_lowering/nn_lowering_utility.py`](../../kernel_gen/passes/lowering/nn_lowering/nn_lowering_utility.py) | [`spec/pass/lowering/nn_lowering/nn_lowering_utility.md`](../../spec/pass/lowering/nn_lowering/nn_lowering_utility.md) | `否` | alloc / shape / symbol-int / broadcast bridge 等共享 helper | 被所有 family 测试与 expectation 间接覆盖 |
| [`kernel_gen/passes/lowering/nn_lowering/element_binary_lowering.py`](../../kernel_gen/passes/lowering/nn_lowering/element_binary_lowering.py) | [`spec/pass/lowering/nn_lowering/element_binary_lowering.md`](../../spec/pass/lowering/nn_lowering/element_binary_lowering.md) | `否` | `nn.add/sub/mul/div/truediv/eq/ne/lt/le/gt/ge` | [`test/pass/nn_lowering/element_binary_add.py`](../../test/pass/nn_lowering/element_binary_add.py)、[`test/pass/nn_lowering/element_compare_eq.py`](../../test/pass/nn_lowering/element_compare_eq.py)、[`expectation/pass/lowing/nn_lowering/element_binary`](../../expectation/pass/lowing/nn_lowering/element_binary)、[`expectation/pass/lowing/nn_lowering/element_compare`](../../expectation/pass/lowing/nn_lowering/element_compare) |
| [`kernel_gen/passes/lowering/nn_lowering/select_cast_lowering.py`](../../kernel_gen/passes/lowering/nn_lowering/select_cast_lowering.py) | [`spec/pass/lowering/nn_lowering/select_cast_lowering.md`](../../spec/pass/lowering/nn_lowering/select_cast_lowering.md) | `否` | `nn.select`、`nn.cast` | [`test/pass/nn_lowering/select.py`](../../test/pass/nn_lowering/select.py)、[`test/pass/nn_lowering/cast.py`](../../test/pass/nn_lowering/cast.py)、[`expectation/pass/lowing/nn_lowering/select.py`](../../expectation/pass/lowing/nn_lowering/select.py)、[`expectation/pass/lowing/nn_lowering/cast.py`](../../expectation/pass/lowing/nn_lowering/cast.py) |

### 三、每份 child spec 需要定义的重要 API

- [`spec/pass/lowering/nn_lowering/spec.md`](../../spec/pass/lowering/nn_lowering/spec.md)
  - `class NnLoweringPass(Pass)`
  - `NnLoweringPass.run(module: ModuleOp) -> ModuleOp`
- [`spec/pass/lowering/nn_lowering/nn_lowering_utility.md`](../../spec/pass/lowering/nn_lowering/nn_lowering_utility.md)
  - `ensure_module_op(module: Operation) -> ModuleOp`
  - `ensure_space_attr(op: Operation) -> NnMemorySpaceAttr`
  - `ensure_single_result(op: Operation) -> NnMemoryType`
  - `ensure_operand_count(op: Operation, expected: int) -> None`
- [`spec/pass/lowering/nn_lowering/element_binary_lowering.md`](../../spec/pass/lowering/nn_lowering/element_binary_lowering.md)
  - `lower_element_binary_family(block: Block, op: Operation) -> bool`
  - 负责 `nn.add/sub/mul/div/truediv/eq/ne/lt/le/gt/ge`；其余 op 必须返回 `False`
- [`spec/pass/lowering/nn_lowering/select_cast_lowering.md`](../../spec/pass/lowering/nn_lowering/select_cast_lowering.md)
  - `lower_select_cast_family(block: Block, op: Operation) -> bool`
  - 负责 `nn.select`、`nn.cast`；其余 op 必须返回 `False`
- `S4~S6` 阶段新增的 child spec，统一沿用同一 API 设计规则：
  - family 文件只定义一个 `lower_*_family(block: Block, op: Operation) -> bool`
  - 该 API 只处理本 family 的 op；非本 family 的 op 必须返回 `False`
  - 如果新增跨 family 复用 helper，必须同步写入 `nn_lowering_utility.md`
- 除上述 API 外，其余 helper 默认视为文件私有实现细节；如果跨文件复用，必须先补进对应 child spec 或迁入 `nn_lowering_utility.py`。

### 四、内部结构约束

- family 文件只允许暴露 lowering helper / rewrite helper；不得再定义 `*Pass` 类。
- `nn_lowering.py` 只做三件事：
  - 组织 family lowering 的调用顺序
  - 统一 block / func / module 遍历
  - 汇总 `NnLoweringError`
- `nn_lowering_utility.py` 只放共享逻辑；任何 family 文件里的通用 helper 一旦被第二个 family 复用，就必须迁入该文件。
- 新增 family 文件时，必须同步新增同名 spec、test、expectation 责任说明；否则该文件不进入完成态。

### 五、边界判定规则

- **按 op family 判定归属**：某个改动如果只服务 `element binary / compare`，只能落在 `element_binary_lowering.py`；只服务 `select / cast`，只能落在 `select_cast_lowering.py`；其余 family 以各自 child spec 为准。
- **单 family 私有 helper 不上收**：一个 helper 若只被一个 family 使用，应留在该 family 文件，不提前放进 `nn_lowering_utility.py`。
- **第二次复用才上收 utility**：同一 helper 被第二个 family 实际调用时，才允许迁入 `nn_lowering_utility.py`，并同步更新 utility spec。
- **`nn_lowering.py` 不承载具体算法细节**：除顶层调度、遍历和错误汇总外，不允许继续把某个 op 的完整 lowering 逻辑长期塞回 `nn_lowering.py`。若暂时过渡，必须在对应阶段内搬出并删除过渡实现。
- **spec 先于文件稳定**：任何新文件若没有对应 spec，只能视为阶段内临时草稿；只有当同名 spec、test、expectation 一起落齐时，才算进入最终结构。
- **审查按“文件职责表”否决越界改动**：评审时凡是出现“本 family 之外的 op lowering 被顺手塞进该文件”“本应私有的 helper 被提前抽成 utility”“无 spec 对应的文件进入公开路径”，都直接判为未收口。

## 完成态定义

### 一、本轮稳定完成态

- 仓库内只保留一个公开 pass：`NnLoweringPass(name="lower-nn")`。
- 当前稳定结构只包含：
  - [`kernel_gen/passes/lowering/nn_lowering/nn_lowering.py`](../../kernel_gen/passes/lowering/nn_lowering/nn_lowering.py)
  - [`kernel_gen/passes/lowering/nn_lowering/nn_lowering_utility.py`](../../kernel_gen/passes/lowering/nn_lowering/nn_lowering_utility.py)
  - [`kernel_gen/passes/lowering/nn_lowering/element_binary_lowering.py`](../../kernel_gen/passes/lowering/nn_lowering/element_binary_lowering.py)
  - [`kernel_gen/passes/lowering/nn_lowering/select_cast_lowering.py`](../../kernel_gen/passes/lowering/nn_lowering/select_cast_lowering.py)
- [`element_binary_lowering.py`](../../kernel_gen/passes/lowering/nn_lowering/element_binary_lowering.py) 与 [`select_cast_lowering.py`](../../kernel_gen/passes/lowering/nn_lowering/select_cast_lowering.py) 不再包含 `Pass` 子类。
- `spec/pass/lowering/nn_lowering/` 下已落齐当前稳定结构对应的总 spec 与 child spec。
- [`test/pass/nn_lowering`](../../test/pass/nn_lowering) 目录级通过。
- [`expectation/pass/lowing/nn_lowering`](../../expectation/pass/lowing/nn_lowering) 目录级通过，并提供根入口 `__main__.py`。
- `pass_manager / pipeline / dsl / execute_engine` 中不再公开旧名 `lower-nn-to-kernel` / `LowerNnToKernelPass`。

### 二、后续增量完成态

- `S4~S6` 到阶段时，再分别新建：
  - `dma_structured_lowering.py` + 同名 spec
  - `reduce_softmax_lowering.py` + 同名 spec
  - `matmul_img2col_lowering.py` + 同名 spec
- 新增 family 文件只有在“文件 + 同名 spec + 对应 test + 对应 expectation”同时落齐后，才进入最终稳定结构。

## 验收设计

- 本计划验收分两层：
  - family 收口：每个 lowering 文件对应的 `test + expectation` 必须先绿
  - 目录收口：`test/pass/nn_lowering` 与 `expectation/pass/lowing/nn_lowering` 必须目录级全绿
- 统一验收命令：
  - `pytest -q test/pass/nn_lowering`
  - `PYTHONPATH=. python -m expectation.pass.lowing.nn_lowering`
  - `pytest -q test/pass/test_pass_manager.py -k "lower-nn or nn_lowering"`
  - `pytest -q test/pass/test_pipeline_default_lowering.py`
- 若某阶段新增 lowering 文件，但没有同步 child spec 或目录级入口，则该阶段视为未完成。

## 阶段拆分

### `S1` 总 spec 与现有 4 文件职责收口

- 阶段目标：
  - 重写总 spec，明确唯一公开 pass。
  - 为现有 `nn_lowering_utility.py`、`element_binary_lowering.py`、`select_cast_lowering.py` 建立对应 child spec。
  - 删除计划里与当前实现不对应的旧任务描述。
- 目标 `spec / API`：
  - [`spec/pass/lowering/nn_lowering/spec.md`](../../spec/pass/lowering/nn_lowering/spec.md)
  - [`spec/pass/lowering/nn_lowering/nn_lowering_utility.md`](../../spec/pass/lowering/nn_lowering/nn_lowering_utility.md)
  - [`spec/pass/lowering/nn_lowering/element_binary_lowering.md`](../../spec/pass/lowering/nn_lowering/element_binary_lowering.md)
  - [`spec/pass/lowering/nn_lowering/select_cast_lowering.md`](../../spec/pass/lowering/nn_lowering/select_cast_lowering.md)
- 可改文件：
  - `ARCHITECTURE/plan/nn_lowering_pass_refactor_green_plan.md`
  - `spec/pass/lowering/nn_lowering/spec.md`
  - `spec/pass/lowering/nn_lowering/*.md`
- 预期示例代码：
  ```python
  from kernel_gen.passes.lowering.nn_lowering import NnLoweringPass
  module = NnLoweringPass().run(module)
  ```
- 预期输出：
  - `nn_lowering` 目录的每个稳定实现文件都有对应 spec。
  - 总 spec 不再声称存在当前仓库还没有的公开 pass 或公开接口。
- 目标验收资产：
  - [`test/pass/nn_lowering/public_name.py`](../../test/pass/nn_lowering/public_name.py)
- 验收必过项目：
  - `pytest -q test/pass/nn_lowering/public_name.py`
- 任务新建建议：
  - `spec -> review -> merge`

### `S2` element_binary / compare 收口

- 阶段目标：
  - 让 `element_binary_lowering.py` 只保留 family lowering helper。
  - 移除该文件中的 `Pass` 子类。
  - 收口 `nn.add/sub/mul/div/truediv/eq/ne/lt/le/gt/ge` 的 expectation 与测试。
- 目标 `spec / API`：
  - [`spec/pass/lowering/nn_lowering/element_binary_lowering.md`](../../spec/pass/lowering/nn_lowering/element_binary_lowering.md)
  - [`kernel_gen/passes/lowering/nn_lowering/element_binary_lowering.py`](../../kernel_gen/passes/lowering/nn_lowering/element_binary_lowering.py)
- 可改文件：
  - `kernel_gen/passes/lowering/nn_lowering/element_binary_lowering.py`
  - `kernel_gen/passes/lowering/nn_lowering/nn_lowering.py`
  - `test/pass/nn_lowering/element_binary_*.py`
  - `test/pass/nn_lowering/element_compare_*.py`
  - `expectation/pass/lowing/nn_lowering/element_binary/*`
  - `expectation/pass/lowing/nn_lowering/element_compare/*`
- 预期示例代码：
  ```mlir
  %out = "nn.mul"(%lhs, %rhs) {space = #nn.space<global>} : (...) -> !nn.memory<[4, 8], [8, 1], f32, #nn.space<global>>
  ```
- 预期输出：
  - `nn.mul` lower 为 `dma.alloc + kernel.binary_elewise(kind="mul")`
  - mixed compare 先物化 `dma.broadcast` 再进入 `kernel.binary_elewise`
  - mixed element_binary scalar 先物化 `dma.fill` 再进入 `kernel.binary_elewise`
- 目标验收资产：
  - [`expectation/pass/lowing/nn_lowering/element_binary`](../../expectation/pass/lowing/nn_lowering/element_binary)
  - [`expectation/pass/lowing/nn_lowering/element_compare`](../../expectation/pass/lowing/nn_lowering/element_compare)
- 验收必过项目：
  - `pytest -q test/pass/nn_lowering/element_binary_add.py test/pass/nn_lowering/element_binary_mul.py test/pass/nn_lowering/element_compare_eq.py`
  - `PYTHONPATH=. python -m expectation.pass.lowing.nn_lowering.element_binary`
  - `PYTHONPATH=. python -m expectation.pass.lowing.nn_lowering.element_compare`
- 任务新建建议：
  - `spec -> build -> review -> merge`

### `S3` select / cast 收口

- 阶段目标：
  - 让 `select_cast_lowering.py` 只保留 family lowering helper。
  - 移除该文件中的 `Pass` 子类。
  - 收口 `nn.select` 与 `nn.cast` 的 expectation 与测试。
- 目标 `spec / API`：
  - [`spec/pass/lowering/nn_lowering/select_cast_lowering.md`](../../spec/pass/lowering/nn_lowering/select_cast_lowering.md)
  - [`kernel_gen/passes/lowering/nn_lowering/select_cast_lowering.py`](../../kernel_gen/passes/lowering/nn_lowering/select_cast_lowering.py)
- 可改文件：
  - `kernel_gen/passes/lowering/nn_lowering/select_cast_lowering.py`
  - `kernel_gen/passes/lowering/nn_lowering/nn_lowering.py`
  - `test/pass/nn_lowering/select.py`
  - `test/pass/nn_lowering/cast.py`
  - `expectation/pass/lowing/nn_lowering/select.py`
  - `expectation/pass/lowing/nn_lowering/cast.py`
- 预期示例代码：
  ```mlir
  %out = "nn.cast"(%arg0) {space = #nn.space<global>} : (...) -> !nn.memory<[4, 8], [8, 1], f32, #nn.space<global>>
  ```
- 预期输出：
  - `nn.select` lower 为 `dma.alloc + kernel.select`
  - `nn.cast` lower 为 `dma.alloc + dma.cast`
- 目标验收资产：
  - [`expectation/pass/lowing/nn_lowering/select.py`](../../expectation/pass/lowing/nn_lowering/select.py)
  - [`expectation/pass/lowing/nn_lowering/cast.py`](../../expectation/pass/lowing/nn_lowering/cast.py)
- 验收必过项目：
  - `pytest -q test/pass/nn_lowering/select.py test/pass/nn_lowering/cast.py`
  - `PYTHONPATH=. python expectation/pass/lowing/nn_lowering/select.py`
  - `PYTHONPATH=. python expectation/pass/lowing/nn_lowering/cast.py`
- 任务新建建议：
  - `spec -> build -> review -> merge`

### `S4` dma_structured family 增量拆出

- 阶段目标：
  - 到该阶段时，新建 `dma_structured_lowering.py` 与同名 child spec。
  - 将 `nn.broadcast`、`nn.broadcast_to`、`nn.transpose`、`nn.fill`、`nn.copy` 从 `nn_lowering.py` 迁入该新文件。
- 目标 `spec / API`：
  - [`spec/pass/lowering/nn_lowering/dma_structured_lowering.md`](../../spec/pass/lowering/nn_lowering/dma_structured_lowering.md)
  - `kernel_gen/passes/lowering/nn_lowering/dma_structured_lowering.py`
- 可改文件：
  - `kernel_gen/passes/lowering/nn_lowering/dma_structured_lowering.py`
  - `kernel_gen/passes/lowering/nn_lowering/nn_lowering.py`
  - `kernel_gen/passes/lowering/nn_lowering/nn_lowering_utility.py`
  - `expectation/pass/lowing/nn_lowering/broadcast.py`
  - `expectation/pass/lowing/nn_lowering/broadcast_to.py`
  - `expectation/pass/lowing/nn_lowering/transpose.py`
- 预期示例代码：
  ```mlir
  %out = "nn.broadcast_to"(%arg0, %m, %n) {space = #nn.space<global>} : (...) -> !nn.memory<[M, N], [N, 1], f32, #nn.space<global>>
  ```
- 预期输出：
  - `nn.broadcast` / `nn.broadcast_to` lower 为显式 `dma.alloc + dma.broadcast`
  - `nn.transpose` lower 为 `dma.alloc + dma.transpose`
- 目标验收资产：
  - [`expectation/pass/lowing/nn_lowering/broadcast.py`](../../expectation/pass/lowing/nn_lowering/broadcast.py)
  - [`expectation/pass/lowing/nn_lowering/broadcast_to.py`](../../expectation/pass/lowing/nn_lowering/broadcast_to.py)
  - [`expectation/pass/lowing/nn_lowering/transpose.py`](../../expectation/pass/lowing/nn_lowering/transpose.py)
- 验收必过项目：
  - `PYTHONPATH=. python expectation/pass/lowing/nn_lowering/broadcast.py`
  - `PYTHONPATH=. python expectation/pass/lowing/nn_lowering/broadcast_to.py`
  - `PYTHONPATH=. python expectation/pass/lowing/nn_lowering/transpose.py`
- 任务新建建议：
  - `spec -> build -> review -> merge`

### `S5` reduce / softmax family 增量拆出

- 阶段目标：
  - 到该阶段时，新建 `reduce_softmax_lowering.py` 与同名 child spec。
  - 将 `nn.exp`、`nn.reduce_sum`、`nn.reduce_min`、`nn.reduce_max`、`nn.softmax` 从 `nn_lowering.py` 迁入该新文件。
- 目标 `spec / API`：
  - [`spec/pass/lowering/nn_lowering/reduce_softmax_lowering.md`](../../spec/pass/lowering/nn_lowering/reduce_softmax_lowering.md)
  - `kernel_gen/passes/lowering/nn_lowering/reduce_softmax_lowering.py`
- 可改文件：
  - `kernel_gen/passes/lowering/nn_lowering/reduce_softmax_lowering.py`
  - `kernel_gen/passes/lowering/nn_lowering/nn_lowering.py`
  - `kernel_gen/passes/lowering/nn_lowering/nn_lowering_utility.py`
  - `test/pass/nn_lowering/exp.py`
  - `test/pass/nn_lowering/reduce_*.py`
  - `test/pass/nn_lowering/softmax.py`
  - `expectation/pass/lowing/nn_lowering/exp.py`
  - `expectation/pass/lowing/nn_lowering/reduce/*`
  - `expectation/pass/lowing/nn_lowering/softmax.py`
- 预期示例代码：
  ```mlir
  %out = "nn.reduce_sum"(%arg0) {axis = #builtin.int<1>, keepdim = #builtin.int<0>, space = #nn.space<global>} : (...) -> !nn.memory<[4], [1], f32, #nn.space<global>>
  ```
- 预期输出：
  - reduce 统一 lower 为 `kernel.reduce(kind=...)`
  - softmax lower 为稳定的 kernel / dma 链路
- 目标验收资产：
  - [`expectation/pass/lowing/nn_lowering/exp.py`](../../expectation/pass/lowing/nn_lowering/exp.py)
  - [`expectation/pass/lowing/nn_lowering/reduce`](../../expectation/pass/lowing/nn_lowering/reduce)
  - [`expectation/pass/lowing/nn_lowering/softmax.py`](../../expectation/pass/lowing/nn_lowering/softmax.py)
- 验收必过项目：
  - `pytest -q test/pass/nn_lowering/exp.py test/pass/nn_lowering/reduce_sum.py test/pass/nn_lowering/softmax.py`
  - `PYTHONPATH=. python expectation/pass/lowing/nn_lowering/exp.py`
  - `PYTHONPATH=. python -m expectation.pass.lowing.nn_lowering.reduce`
  - `PYTHONPATH=. python expectation/pass/lowing/nn_lowering/softmax.py`
- 任务新建建议：
  - `spec -> build -> review -> merge`

### `S6` matmul / img2col family 增量拆出

- 阶段目标：
  - 到该阶段时，新建 `matmul_img2col_lowering.py` 与同名 child spec。
  - 将 `nn.matmul`、`nn.img2col1d`、`nn.img2col2d` 从 `nn_lowering.py` 迁入该新文件。
- 目标 `spec / API`：
  - [`spec/pass/lowering/nn_lowering/matmul_img2col_lowering.md`](../../spec/pass/lowering/nn_lowering/matmul_img2col_lowering.md)
  - `kernel_gen/passes/lowering/nn_lowering/matmul_img2col_lowering.py`
- 可改文件：
  - `kernel_gen/passes/lowering/nn_lowering/matmul_img2col_lowering.py`
  - `kernel_gen/passes/lowering/nn_lowering/nn_lowering.py`
  - `kernel_gen/passes/lowering/nn_lowering/nn_lowering_utility.py`
  - `test/pass/nn_lowering/matmul.py`
  - `test/pass/nn_lowering/img2col1d.py`
  - `test/pass/nn_lowering/img2col2d.py`
  - `expectation/pass/lowing/nn_lowering/matmul.py`
  - `expectation/pass/lowing/nn_lowering/img2col/*`
- 预期示例代码：
  ```mlir
  %out = "nn.img2col1d"(%arg0, %kw, %sw, %dw, %pl, %pr) {space = #nn.space<global>} : (...) -> !nn.memory<[N, C, KW, OW], [..], f32, #nn.space<global>>
  ```
- 预期输出：
  - `img2col` 参数统一走 symbol-int operand
  - `nn.matmul` lower 为稳定 `kernel.matmul + dma.alloc`
- 目标验收资产：
  - [`expectation/pass/lowing/nn_lowering/matmul.py`](../../expectation/pass/lowing/nn_lowering/matmul.py)
  - [`expectation/pass/lowing/nn_lowering/img2col`](../../expectation/pass/lowing/nn_lowering/img2col)
- 验收必过项目：
  - `pytest -q test/pass/nn_lowering/matmul.py test/pass/nn_lowering/img2col1d.py test/pass/nn_lowering/img2col2d.py`
  - `PYTHONPATH=. python expectation/pass/lowing/nn_lowering/matmul.py`
  - `PYTHONPATH=. python -m expectation.pass.lowing.nn_lowering.img2col`
- 任务新建建议：
  - `spec -> build -> review -> merge`

### `S7` 根入口与跨层公开引用收口

- 阶段目标：
  - 根入口只剩 `lower-nn` / `NnLoweringPass`
  - 目录级 expectation 与 test 全绿
  - `pass_manager / pipeline / dsl / execute_engine` 中旧名引用清理完成
- 目标 `spec / API`：
  - [`spec/pass/lowering/nn_lowering/spec.md`](../../spec/pass/lowering/nn_lowering/spec.md)
  - [`kernel_gen/passes/lowering/nn_lowering/__init__.py`](../../kernel_gen/passes/lowering/nn_lowering/__init__.py)
  - [`kernel_gen/passes/lowering/nn_lowering/nn_lowering.py`](../../kernel_gen/passes/lowering/nn_lowering/nn_lowering.py)
- 可改文件：
  - `kernel_gen/passes/pass_manager.py`
  - `kernel_gen/passes/pipeline/default_lowering.py`
  - `test/pass/test_pass_manager.py`
  - `test/pass/test_pipeline_default_lowering.py`
  - `test/dsl/test_emit_c.py`
  - `test/dsl/test_gen_kernel.py`
  - `expectation/execute_engine/add.py`
  - `expectation/pass/lowing/nn_lowering/__main__.py`
- 预期示例代码：
  ```python
  from kernel_gen.passes.lowering.nn_lowering import NnLoweringPass
  module = NnLoweringPass().run(module)
  ```
- 预期输出：
  - 目录级入口 `python -m expectation.pass.lowing.nn_lowering` 可运行
  - 旧公开名不再出现在主仓公开接口与主测试入口中
- 目标验收资产：
  - [`expectation/pass/lowing/nn_lowering`](../../expectation/pass/lowing/nn_lowering)
  - [`test/pass/nn_lowering`](../../test/pass/nn_lowering)
- 验收必过项目：
  - `pytest -q test/pass/nn_lowering`
  - `PYTHONPATH=. python -m expectation.pass.lowing.nn_lowering`
  - `pytest -q test/pass/test_pass_manager.py -k "lower-nn or nn_lowering"`
  - `pytest -q test/pass/test_pipeline_default_lowering.py`
- 任务新建建议：
  - `spec -> build -> review -> merge`

## 待确认项

- 无。当前计划的结构口径已固定：一个公开 pass，多份 child spec，对应多个 family lowering 文件；未来若新增 family 文件，必须作为新阶段显式加入计划与 spec。

## 参考资料

- [`analysis .plan.md`](../../analysis%20.plan.md)
- [`spec/pass/lowering/nn_lowering/spec.md`](../../spec/pass/lowering/nn_lowering/spec.md)
- [`kernel_gen/passes/lowering/nn_lowering`](../../kernel_gen/passes/lowering/nn_lowering)
- [`test/pass/nn_lowering`](../../test/pass/nn_lowering)
- [`expectation/pass/lowing/nn_lowering`](../../expectation/pass/lowing/nn_lowering)

## 归档记录

时间：2026-04-14 13:21 +0800
经办人：李白
任务：T-20260414-43298954
任务目标：将 `ARCHITECTURE/plan/nn_lowering_pass_refactor_green_plan.md` 归档到 `agents/codex-multi-agents/log/task_records/done_plan/2026/16/nn_lowering_pass_refactor_green_plan.md`，并为归档合并补齐记录
改动：
- 指定 `worktree` 不存在，已按当前协作口径补建 `/home/lfr/kernelcode_generate/wt-20260414-archive-nn-lowering-pass-refactor-plan` 并绑定任务分支 `T-20260414-43298954`。
- 核对发现 `ARCHITECTURE/plan/nn_lowering_pass_refactor_green_plan.md` 当前是主目录中的本地忽略文件，不在当前 Git 版本树中；因此在任务 `worktree` 内将该计划书内容复制到归档目标文件，作为本次归档记录文件与归档产物的统一载体。
- 本轮归档范围仅包含新建的归档文件；主目录本地 `ARCHITECTURE/plan/nn_lowering_pass_refactor_green_plan.md` 已同步移除。
验证：
- `git -C /home/lfr/kernelcode_generate worktree list`：确认原任务 `worktree` 缺失，补建后继续在专用 `worktree` 内执行。
- `git -C /home/lfr/kernelcode_generate check-ignore -v ARCHITECTURE/plan/nn_lowering_pass_refactor_green_plan.md` -> `.gitignore:21:ARCHITECTURE/plan/`，确认源计划书当前为本地忽略文件。
- `sed -n '1,80p' /home/lfr/kernelcode_generate/ARCHITECTURE/plan/nn_lowering_pass_refactor_green_plan.md`：确认归档源内容可读。
- `rm -f /home/lfr/kernelcode_generate/ARCHITECTURE/plan/nn_lowering_pass_refactor_green_plan.md && test ! -e /home/lfr/kernelcode_generate/ARCHITECTURE/plan/nn_lowering_pass_refactor_green_plan.md` -> `removed`
结论：归档前记录已补齐；下一步在当前 `worktree` 内提交归档文件并推送远端主分支，随后仅通过 `-talk` 回报管理员执行 `-done` 与后续 `-done-plan`。
