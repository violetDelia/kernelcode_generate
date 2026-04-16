# operation_layer_refactor_green_plan.md

## 文档信息

- 创建者：`大闸蟹`
- 最后一次更改：`大闸蟹`
- 目标 `spec`：
  - [`spec/operation/arch.md`](../../spec/operation/arch.md)
  - [`spec/operation/dma.md`](../../spec/operation/dma.md)
  - [`spec/operation/nn.md`](../../spec/operation/nn.md)
  - [`spec/operation/scf.md`](../../spec/operation/scf.md)
- 目标 `API`：
  - `kernel_gen.operation` 顶层稳定导出集合
  - `kernel_gen.operation.arch` 的查询 / 动态内存 / barrier / launch helper
  - `kernel_gen.operation.dma` 的 alloc / movement / view helper
  - `kernel_gen.operation.nn` 的 elementwise / broadcast / structured / reduction family
  - `kernel_gen.operation.scf.loop(start, end, step, trip_count=1)`
- 目标 `test`：
  - [`test/operation/test_operation_arch.py`](../../test/operation/test_operation_arch.py)
  - [`test/operation/test_operation_dma.py`](../../test/operation/test_operation_dma.py)
  - [`test/operation/test_operation_nn.py`](../../test/operation/test_operation_nn.py)
  - [`test/operation/test_operation_scf.py`](../../test/operation/test_operation_scf.py)
  - `test/operation/test_operation_package_api.py`
  - `test/operation/test_operation_dma_alloc_lifecycle.py`
  - `test/operation/test_operation_dma_transfer_view.py`
  - `test/operation/test_operation_nn_elementwise.py`
  - `test/operation/test_operation_nn_broadcast.py`
  - `test/operation/test_operation_nn_structured.py`
  - `test/operation/test_operation_nn_reduction.py`
- 目标 `验收资产`：
  - `rg -n "静态设备值|动态回退|BarrierVisibility|launch_kernel\\(callee" spec/operation/arch.md`
  - `rg -n "关系图|越界规则索引|alloc|view|slice|reshape|copy" spec/operation/dma.md`
  - `rg -n "逐元素|broadcast|structured|reduction" spec/operation/nn.md`
  - `rg -n "最小 loop helper|未来扩展|trip_count" spec/operation/scf.md`
  - `pytest -q test/operation`
- 目标 `功能实现`：
  - [`kernel_gen/operation/__init__.py`](../../kernel_gen/operation/__init__.py)
  - [`kernel_gen/operation/arch.py`](../../kernel_gen/operation/arch.py)
  - [`kernel_gen/operation/dma.py`](../../kernel_gen/operation/dma.py)
  - [`kernel_gen/operation/nn.py`](../../kernel_gen/operation/nn.py)
  - [`kernel_gen/operation/scf.py`](../../kernel_gen/operation/scf.py)
  - `kernel_gen/operation/_nn_common.py`
  - `kernel_gen/operation/_nn_elementwise.py`
  - `kernel_gen/operation/_nn_broadcast.py`
  - `kernel_gen/operation/_nn_structured.py`
  - `kernel_gen/operation/_nn_reduction.py`

## 任务清单

| 任务 | 前置任务 | worktree | 记录文件 |
| --- | --- | --- | --- |
| S1 | 无 | `wt-20260415-operation-layer-s1` | `agents/codex-multi-agents/log/task_records/2026/16/20260415-operation-layer-s1.md` |
| S2 | S1 | `wt-20260415-operation-layer-s2` | `agents/codex-multi-agents/log/task_records/2026/16/20260415-operation-layer-s2.md` |
| S3 | S2 | `wt-20260415-operation-layer-s3` | `agents/codex-multi-agents/log/task_records/2026/16/20260415-operation-layer-s3.md` |
| S4 | S3 | `wt-20260415-operation-layer-s4` | `agents/codex-multi-agents/log/task_records/2026/16/20260415-operation-layer-s4.md` |
| S5 | S4 | `wt-20260415-operation-layer-s5` | `agents/codex-multi-agents/log/task_records/2026/16/20260415-operation-layer-s5.md` |
| S6 | S5 | `wt-20260415-operation-layer-s6` | `agents/codex-multi-agents/log/task_records/2026/16/20260415-operation-layer-s6.md` |
| S7 | S6 | `wt-20260415-operation-layer-s7` | `agents/codex-multi-agents/log/task_records/2026/16/20260415-operation-layer-s7.md` |

## 评审摘要

- 评审结论：`通过`
- 评审人：`守护最好的爱莉希雅`、`大闸蟹`
- 结论摘要：`已按 2026-04-15 13:51 +0800 互评的两条最小阻断项完成修订，并经复核通过：S2 已明确为 nn family 文本合同与顶层导出边界收口，不再混入实现拆分表述；S3 已把 dma 同阶段测试与验收补齐，使“统一校验入口”可以在本阶段机械验证。当前计划可以按现版本建任务推进。`

## 互评结论（2026-04-15 13:51 +0800）

- 互评人：`守护最好的爱莉希雅`
- 互评结论：`暂不通过`
- 已确认可保留项：
  - 计划总边界是对的：当前版本明确把范围收在 `spec/operation`、`kernel_gen/operation`、`test/operation`，没有把任务扩到 `dialect / pass / dsl / emit_c / gen_kernel / expectation`，符合“operation 继续作为纯高层语义层”的定位。
  - `nn` 采用“保留 `kernel_gen.operation.nn` 聚合入口，同时拆出 `_nn_common / _nn_elementwise / _nn_broadcast / _nn_structured / _nn_reduction` 私有模块”的主方案可以保留；这条路线兼顾了维护性与对外导入路径稳定。
  - 顶层 `kernel_gen.operation` 导出锁定、`scf.loop` 的 `bool / 非法 step / trip_count` 负例、以及 `arch` 当前 spec 与实现脱节需要先收口，这些计划目标都成立。
- 最小阻断项：
  - `S2` 的阶段边界还不够自洽。当前 `S2` 的阶段目标写成“将 nn 组重排为 family 目录结构，并把 kernel_gen.operation 顶层导出收成稳定集合”，但该阶段的可改文件只有 [`spec/operation/nn.md`](../../spec/operation/nn.md) 与计划书本身，不包含 [`kernel_gen/operation/nn.py`](../../kernel_gen/operation/nn.py)、[`kernel_gen/operation/__init__.py`](../../kernel_gen/operation/__init__.py) 或任何测试文件。也就是说，`S2` 现在名义上在做实现重排，实际却只能写 spec，执行人与管理员很难判断“nn family 目录结构”到底是在本阶段定义合同，还是已经要求进入实现。这里需要把 `S2` 改成纯 spec/边界收口，真正的实现拆分继续留在 `S4`，否则阶段目标与可改文件不一致。
  - `S3` 的 dma 收口缺少同阶段可验证资产。当前 `S3` 的预期输出明确写了“`dma` 访问区域校验走统一入口”，可改文件也包含 [`kernel_gen/operation/dma.py`](../../kernel_gen/operation/dma.py)，但该阶段的可改测试与验收必过项目只覆盖 `test_operation_package_api.py`、[`test/operation/test_operation_arch.py`](../../test/operation/test_operation_arch.py)、[`test/operation/test_operation_scf.py`](../../test/operation/test_operation_scf.py)，没有 [`test/operation/test_operation_dma.py`](../../test/operation/test_operation_dma.py) 或任何 dma 定向回归。这样即使执行人改了 dma，实现结果也只能等到 `S5` 才被顺带验证，`S3` 本身无法机械证明“统一入口”已经成立。这里需要二选一：要么把 dma 实现收口从 `S3` 移出，留到有 dma 测试的阶段；要么把 dma 定向测试与验收一并补进 `S3`。
- 修订建议：
  - 将 `S2` 的阶段目标收窄为“`nn` family 合同重排 + 顶层导出稳定集合文本收口”，不要在该阶段直接写“重排为 family 目录结构”这类实现表述；实现拆分统一留在 `S4`。
  - 将 `S3` 重新收成“arch / scf / 顶层导出实现收口”，或者显式把 [`test/operation/test_operation_dma.py`](../../test/operation/test_operation_dma.py) / dma 新拆分测试纳入 `S3` 的可改文件与验收必过项目，使 dma 统一校验入口在本阶段即可被验证。

## 复核结论（2026-04-15 13:55 +0800）

- 复核人：`守护最好的爱莉希雅`
- 复核结论：`通过`
- 复核摘要：
  - `S2` 已明确收窄为 `nn` family 文本合同重排与 `kernel_gen.operation` 顶层导出边界收口，预期输出里也已写清“`nn` 实现拆分只在 `S4` 执行”，阶段目标与可改文件已一致。
  - `S3` 已把 [`test/operation/test_operation_dma.py`](../../test/operation/test_operation_dma.py) 纳入可改文件、目标验收资产与必过命令；因此 `dma` 统一校验入口不再只是实现目标，而是能在同阶段被机械验证。
  - 当前计划继续保持 `operation` 纯高层语义边界，不扩到 `dialect / pass / dsl / emit_c / gen_kernel / expectation`；`arch / dma / nn / scf` 的拆分与 `S1 -> S7` 依赖也已可直接执行。

## 终验结论（2026-04-17 00:56 +0800）

- 终验人：`守护最好的爱莉希雅`
- 当前结论：`通过`
- 归档结论：`当前可进入归档链；待双架构师都明确“通过”后，由管理员补建唯一归档任务`
- 验证基线：
  - 以同步现场 ` /home/lfr/kernelcode_generate/wt-20260415-operation-layer-s1 ` 为准；本次核对时间为 `2026-04-17 00:56 +0800`。
  - 该现场 `HEAD` 为 `bb5139006c900cfafb9d53f0214002379218751b`。
- 依据：
  - `rg -n "静态设备值|动态回退|BarrierVisibility|launch_kernel\\(callee" spec/operation/arch.md` 可命中 `arch` 当前合同中的静态设备值、动态回退、`BarrierVisibility` 与 `launch_kernel(callee, ...)` 口径。
  - `rg -n "关系图|越界规则索引|alloc|view|slice|reshape|copy" spec/operation/dma.md`、`rg -n "逐元素|broadcast|structured|reduction" spec/operation/nn.md`、`rg -n "最小 loop helper|未来扩展|trip_count" spec/operation/scf.md` 均可命中计划书要求的文本验收资产。
  - `PYTHONDONTWRITEBYTECODE=1 pytest -q test/operation` 在上述同步现场结果为 `139 passed in 0.37s`。
- 终验摘要：
  - [`spec/operation/arch.md`](../../spec/operation/arch.md)、[`spec/operation/dma.md`](../../spec/operation/dma.md)、[`spec/operation/nn.md`](../../spec/operation/nn.md)、[`spec/operation/scf.md`](../../spec/operation/scf.md) 已按计划收口到当前公开语义。
  - `test/operation` 当前整组回归通过，且验收结果支持 `arch / dma / nn / scf` 与顶层导出边界已形成闭环。
  - 本次终验按“最新同步现场优先”执行；根目录主仓工作目录若仍停在更早现场，只记为现场差异，不单独构成本计划阻塞。
- 当前状态：
  - 我侧终验已明确为 `通过`。
  - 待 `大闸蟹` 在计划正文写入同口径终验后，可由管理员补建唯一归档任务继续推进。

## 输入摘要

- 目标：为 `Operation` 组补一份可直接推进的重构计划，让 `arch / dma / nn / scf` 的 spec、实现结构和测试边界同步收口。
- 不做什么：不把本轮改动扩到 `dialect / pass / dsl / emit_c / gen_kernel / expectation`，也不把 operation 组改成新的 lowering 或 codegen 层。
- 当前痛点：`nn.py` 与对应测试文件已经明显过大，`arch` 的 spec 已落后于实现，`dma` / `scf` 仍缺结构化边界说明与若干负例。
- 完成后最想看到的例子：执行人只看 `spec/operation/*.md` 与 `test/operation/*`，就能判断哪些 helper 属于稳定高层语义、哪些只允许子模块使用、哪些错误路径必须报错，而不需要再去猜 dialect/codegen 细节。

## 计划目标

- 保持 `operation` 组作为仓库里的高层语义真源，不把本轮重构变成对 `dialect / codegen` 的越层改造。
- 收口 [`spec/operation/arch.md`](../../spec/operation/arch.md) 与 [`kernel_gen/operation/arch.py`](../../kernel_gen/operation/arch.py) 的真实公开合同，明确静态设备值与动态回退、barrier 聚合域、launch 上下文和动态片上内存语义。
- 在 [`spec/operation/dma.md`](../../spec/operation/dma.md) 与 [`kernel_gen/operation/dma.py`](../../kernel_gen/operation/dma.py) 中把 `alloc / view / slice / reshape / copy` 的关系图、越界规则索引与统一参数校验入口收成单一口径。
- 按 `逐元素 / broadcast / structured / reduction` 重整 [`spec/operation/nn.md`](../../spec/operation/nn.md) 与 `nn` 实现结构，把当前 2653 行 [`kernel_gen/operation/nn.py`](../../kernel_gen/operation/nn.py) 拆成可维护的 family 模块，同时保持 `kernel_gen.operation.nn` 作为对外聚合入口。
- 把 [`kernel_gen/operation/__init__.py`](../../kernel_gen/operation/__init__.py) 的顶层导出收敛为“现有稳定 helper 集合”，防止名字空间继续膨胀。
- 保持 [`spec/operation/scf.md`](../../spec/operation/scf.md) 与 [`kernel_gen/operation/scf.py`](../../kernel_gen/operation/scf.py) 的“最小 loop helper”定位，不顺手扩成更完整控制流体系；未来如要补 `if / while / yield`，必须另开计划。
- 将 `test/operation` 从大文件拆成 family 测试，并补齐 `target registry` 缺字段、`stride/offset` 组合边界、非法 `bound/step` 与符号步长等真实负例。

## 当前基线

- 当前公开合同：
  - [`spec/operation/arch.md`](../../spec/operation/arch.md)、[`spec/operation/dma.md`](../../spec/operation/dma.md)、[`spec/operation/nn.md`](../../spec/operation/nn.md)、[`spec/operation/scf.md`](../../spec/operation/scf.md) 已存在，`operation` 组不是“无 spec 起步”。
  - `operation` 组当前测试全绿：`pytest -q test/operation/test_operation_arch.py test/operation/test_operation_dma.py test/operation/test_operation_nn.py test/operation/test_operation_scf.py` 已通过，结果为 `128 passed in 0.24s`。
- 当前公开 API：
  - [`kernel_gen/operation/__init__.py`](../../kernel_gen/operation/__init__.py) 当前顶层导出集合为：`add / sub / mul / truediv / eq / ne / lt / le / gt / ge / matmul / alloc / free / copy / load / store / slice / deslice / view / reshape / flatten / cast / loop`。
  - 当前顶层未导出 `arch` helper、激活 / reduction / broadcast / fc / conv / transpose / img2col；但这份“哪些留在子模块、哪些出现在顶层”的边界还没有被单独写成稳定合同。
- 当前实现入口：
  - [`kernel_gen/operation/nn.py`](../../kernel_gen/operation/nn.py) 当前为单文件 `2653` 行，包含公共 helper、内部推导、family 逻辑与 `__all__`；[`test/operation/test_operation_nn.py`](../../test/operation/test_operation_nn.py) 也已达 `1579` 行。
  - [`kernel_gen/operation/dma.py`](../../kernel_gen/operation/dma.py) 已拆出 `_ensure_*` 系列校验函数，但参数规范化、rank 校验、越界校验仍散在多个入口里，缺少单一“访问区域校验入口”。
  - [`kernel_gen/operation/arch.py`](../../kernel_gen/operation/arch.py) 已具备 `BarrierVisibility`、`BarrierScope`、`barrier(...)`、`launch_kernel(callee, block, thread, subthread, *args)`、launch 上下文优先级与 `TLM1/TLM2/TLM3` 动态内存支持。
  - [`kernel_gen/operation/scf.py`](../../kernel_gen/operation/scf.py) 当前实现了 `loop(start, end, step, trip_count=1)`，但其 `int` 校验实际会把 `bool` 一并接受，测试侧尚未锁定这一负例。
- 当前测试与验收资产：
  - [`test/operation/test_operation_arch.py`](../../test/operation/test_operation_arch.py) 已覆盖 barrier、launch 上下文与设备值 fallback，但仍缺 `target registry` 缺关键字段时的显式错误路径。
  - [`test/operation/test_operation_dma.py`](../../test/operation/test_operation_dma.py) 已有较高覆盖，但仍以单文件堆叠多家族 case 的方式存在，边界组合不利于快速判定。
  - [`test/operation/test_operation_nn.py`](../../test/operation/test_operation_nn.py) 已覆盖 elementwise、broadcast、fc/matmul/conv/img2col、softmax/reduction/transpose，但目前所有 family 混在同一文件中。
  - [`test/operation/test_operation_scf.py`](../../test/operation/test_operation_scf.py) 已覆盖 `trip_count` 与符号范围，但还缺 `bool`、非法 `bound`、符号步长的明确负例说明。
- 当前缺口或失败点：
  - [`spec/operation/arch.md`](../../spec/operation/arch.md) 仍按旧口径描述 `launch_kernel(name, block, thread, subthread)` 与 `MemorySpace.TLM`，而当前实现 / 测试已使用 `callee` 函数对象、`barrier(...)` 与 `TLM1/TLM2/TLM3`；spec 与实现已出现明显偏差。
  - [`spec/operation/nn.md`](../../spec/operation/nn.md) 虽已覆盖多数 helper，但目录与叙述仍以“按 helper 顺序长文罗列”为主，没有把 `逐元素 / broadcast / structured / reduction` 作为维护主轴。
  - [`kernel_gen/operation/__init__.py`](../../kernel_gen/operation/__init__.py) 的顶层导出仍是隐式边界，缺少专门测试来锁定“当前哪些名字是稳定顶层 API”。
  - `scf.loop` 当前默认把 `bool` 当作 `int` 接受，这与“只接受 `int | SymbolDim`”的语义描述并不一致。
  - 当前 operation 组没有 expectation 资产，本轮验收应继续以 `spec` 文本核对与 `pytest -q test/operation` 为主，不宜引入新的 expectation 路径。

## 方案比较与选型

- 不采用方案：继续把 [`kernel_gen/operation/nn.py`](../../kernel_gen/operation/nn.py) 保持为单文件，只靠注释标题区分 family。
  - 原因：这不会减少写集冲突，也不会降低 review 成本；`2653` 行单文件已经超过“靠段落标题维持可维护”的阈值。
- 不采用方案：把 `nn.py` 直接重命名成 `kernel_gen/operation/nn/` 包，并要求上层改用新的子模块导入路径。
  - 原因：这会扩大公开导入路径变动面；本轮更适合采用“保留 `kernel_gen.operation.nn` 聚合入口 + 拆出私有 family 模块”的最短路径。
- 不采用方案：顺手把 `operation` 的问题一路修到 `dialect / dsl / codegen`。
  - 原因：用户已明确要求这组继续保持“纯语义边界”；operation 组的职责是高层语义真源，不是下游 IR 或发码层的替代入口。
- 不采用方案：继续放任 `kernel_gen.operation` 顶层导出随实现自然增长。
  - 原因：这会让顶层命名空间进一步膨胀，执行人和调用方更难判断“哪些是稳定 helper、哪些只是子模块入口”。
- 采用方案：
  - 先用 `spec` 收口真实边界，再按边界拆实现与测试。
  - `nn` 采用“保留 `nn.py` 聚合入口 + 拆出 `_nn_common / _nn_elementwise / _nn_broadcast / _nn_structured / _nn_reduction` 私有模块”的方案。
  - `arch / dma / scf` 不做目录级拆分，保持模块路径稳定，只做边界收口与内部组织优化。
  - 顶层 `kernel_gen.operation` 不新增导出；本轮只锁定现有稳定集合，并通过专门测试锁定。
- 最小公开接口：
  - `kernel_gen.operation` 顶层稳定导出集合保持现状，不新增、不扩散。
  - `kernel_gen.operation.arch` 以 `get_* / get_dynamic_memory / barrier / launch_kernel` 为公开口径。
  - `kernel_gen.operation.dma` 以 alloc / movement / view helper 为公开口径。
  - `kernel_gen.operation.nn` 继续作为对外聚合入口；内部 family 模块不承诺为对外稳定 API。
  - `kernel_gen.operation.scf.loop` 继续作为唯一公开控制流 helper。

## 公开 API 设计

### 1. `kernel_gen.operation` 顶层稳定导出

- 公开入口：`kernel_gen.operation`
- 稳定导出集合：`add / sub / mul / truediv / eq / ne / lt / le / gt / ge / matmul / alloc / free / copy / load / store / slice / deslice / view / reshape / flatten / cast / loop`
- 本轮规则：不新增顶层导出，不把 `arch` helper、activation、broadcast、structured helper 顺手挂到顶层。
- 返回值：`无`

```python
from kernel_gen.operation import add, alloc, copy, loop, matmul
```

### 2. `kernel_gen.operation.arch`

- 公开入口：
  - `get_block_id / get_block_num / get_thread_id / get_thread_num / get_subthread_id / get_subthread_num`
  - `get_dynamic_memory(space)`
  - `barrier(visibility=[BarrierVisibility.TSM, BarrierVisibility.TLM], scope=...)`
  - `launch_kernel(callee, block, thread, subthread, *args)`
- 参数顺序：
  - `launch_kernel(callee, block, thread, subthread, *args)`，`callee` 为函数对象，不再沿用旧的 `name: str` 口径
  - `get_dynamic_memory(space)` 只接受片上空间 `SM / LM / TSM / TLM1 / TLM2 / TLM3`
- 返回值：
  - 查询 helper 返回 `SymbolDim`
  - `get_dynamic_memory` 返回一维字节 `Memory`
  - `barrier` / `launch_kernel` 返回 `None`

```python
from kernel_gen.operation.arch import BarrierScope, BarrierVisibility, barrier, get_dynamic_memory, launch_kernel
from kernel_gen.symbol_variable.memory import MemorySpace
from kernel_gen.symbol_variable.symbol_dim import SymbolDim

smem = get_dynamic_memory(MemorySpace.TSM)
barrier(visibility=[BarrierVisibility.TSM, BarrierVisibility.TLM], scope=BarrierScope.THREAD)
launch_kernel(lambda lhs, rhs, out: None, SymbolDim("GRID_X"), 128, 4, "lhs", "rhs", "out")
```

### 3. `kernel_gen.operation.dma`

- 公开入口：`alloc / free / copy / cast / load / store / slice / deslice / view / reshape / flatten`
- 规则：
  - `alloc / view / slice / reshape / copy` 的关系图与越界规则索引在 spec 中集中说明
  - `offset / size / stride` 的规范化、rank 校验、越界检查通过统一入口复用，不再由每个 helper 各自散写一轮
- 返回值：`Memory | None`

```python
from kernel_gen.operation.dma import alloc, copy, reshape, slice, view
from kernel_gen.symbol_variable.memory import MemorySpace
from kernel_gen.symbol_variable.type import NumericType

src = alloc([64, 64], NumericType.Float32, space=MemorySpace.GM)
tile = slice(src, offsets=[0, 0], sizes=[16, 16], strides=[1, 1], space=MemorySpace.SM)
sub = view(tile, offsets=[0, 0], sizes=[8, 8], strides=[1, 1])
dst = copy(reshape(sub, [64]), MemorySpace.LM)
```

### 4. `kernel_gen.operation.nn`

- 公开入口：`kernel_gen.operation.nn`
- family 划分：
  - `逐元素`：`add / sub / mul / truediv / floordiv / eq / ne / lt / le / gt / ge / relu / leaky_relu / sigmoid / tanh / hard_sigmoid / exp`
  - `broadcast`：`broadcast / broadcast_to` 与对应 shape 推导 helper
  - `structured`：`softmax / fc / matmul / conv / img2col1d / img2col2d / transpose`
  - `reduction`：`reduce_sum / reduce_min / reduce_max`
- 规则：
  - `kernel_gen.operation.nn` 继续作为对外聚合入口
  - 私有 family 模块只作为内部组织结构，不承诺为对外稳定导入路径

```python
from kernel_gen.operation.nn import add, broadcast, matmul, reduce_sum, transpose

acc = add(lhs, rhs)
expanded = broadcast(acc, rhs)
prod = matmul(a, b)
reduced = reduce_sum(prod, axis=1, keepdim=True)
transposed = transpose(reduced, perm=[1, 0])
```

### 5. `kernel_gen.operation.scf.loop`

- 公开入口：`loop(start, end, step, trip_count=1)`
- 规则：
  - 当前只覆盖最小范围迭代 helper
  - 不顺手扩到 `if / while / yield / region builder`
  - `bool` 不再按 `int` 被接受
- 返回值：`range | LoopRange`

## 归档记录

时间：2026-04-17 01:43 +0800
经办人：李白
任务：T-20260417-4331cd90
任务目标：将 `ARCHITECTURE/plan/operation_layer_refactor_green_plan.md` 归档到 `agents/codex-multi-agents/log/task_records/done_plan/2026/16/operation_layer_refactor_green_plan.md`，并完成归档 merge 收口。
改动：
- 管理员指定的 `worktree=/home/lfr/kernelcode_generate/wt-20260417-archive-operation-layer-refactor-green-plan` 与任务分支 `T-20260417-4331cd90` 原本不存在；已按当前远端主分支 `origin/main@ba6ce70` 补建归档 `worktree` 与对应分支。
- 核对发现源计划书 `ARCHITECTURE/plan/operation_layer_refactor_green_plan.md` 当前只存在于主仓本地文件系统，未被 `git ls-files` 跟踪，且 `origin/main` 中无目标 `done_plan` 文件；因此将主仓本地源计划书整体迁移到任务 `worktree` 内的归档目标路径 `agents/codex-multi-agents/log/task_records/done_plan/2026/16/operation_layer_refactor_green_plan.md`，并在文件尾部追加本次归档记录。
- 本次归档合并范围限定为新增 `agents/codex-multi-agents/log/task_records/done_plan/2026/16/operation_layer_refactor_green_plan.md`；按用户要求，主仓本地源计划书已删除，不修改 `.gitignore`、`TODO.md`、`DONE.md` 或其他共享状态文件。
验证：
- `rg -n "T-20260417-4331cd90" /home/lfr/kernelcode_generate/TODO.md` -> 确认任务为 `merge/进行中/指派=李白`
- `git -C /home/lfr/kernelcode_generate worktree add -b T-20260417-4331cd90 /home/lfr/kernelcode_generate/wt-20260417-archive-operation-layer-refactor-green-plan origin/main` -> 成功创建归档 `worktree`
- `git -C /home/lfr/kernelcode_generate rev-parse --verify origin/main` -> `ba6ce70aa19b6e1cb11240d9047affa4c493588d`
- `test -f /home/lfr/kernelcode_generate/ARCHITECTURE/plan/operation_layer_refactor_green_plan.md && echo ROOT_PLAN_EXISTS || echo ROOT_PLAN_MISSING` -> 迁移前为 `ROOT_PLAN_EXISTS`
- `test -f /home/lfr/kernelcode_generate/agents/codex-multi-agents/log/task_records/done_plan/2026/16/operation_layer_refactor_green_plan.md && echo DONE_PLAN_EXISTS || echo DONE_PLAN_MISSING` -> 迁移前为 `DONE_PLAN_MISSING`
- `test -f /home/lfr/kernelcode_generate/wt-20260417-archive-operation-layer-refactor-green-plan/agents/codex-multi-agents/log/task_records/done_plan/2026/16/operation_layer_refactor_green_plan.md && echo ARCHIVE_READY && test -e /home/lfr/kernelcode_generate/ARCHITECTURE/plan/operation_layer_refactor_green_plan.md || echo ROOT_REMOVED` -> `ARCHIVE_READY`、`ROOT_REMOVED`
结论：归档文件已在指定 `worktree` 内生成并写入归档记录；下一步提交并推送该归档文件，随后执行当前 merge 任务 `-done` 并回报管理员继续 `-done-plan`。

```python
from kernel_gen.operation.scf import loop
from kernel_gen.symbol_variable.symbol_dim import SymbolDim

for i in loop(0, 4, 1):
    pass

for j in loop(0, SymbolDim("N"), SymbolDim("S"), trip_count=3):
    pass
```

## 完成态定义

- [`spec/operation/arch.md`](../../spec/operation/arch.md) 已与当前实现口径一致，明确写清：
  - 静态设备值优先、缺失时动态回退；
  - `barrier` 的聚合可见域与 scope；
  - `launch_kernel(callee, ...)` 的函数对象与 launch 上下文语义；
  - `TLM1 / TLM2 / TLM3` 的动态内存入口。
- [`spec/operation/dma.md`](../../spec/operation/dma.md) 中存在可检索的“关系图”和“越界规则索引”，并能直接覆盖 `alloc / view / slice / reshape / copy` 的关系。
- [`spec/operation/nn.md`](../../spec/operation/nn.md) 已按 `逐元素 / broadcast / structured / reduction` 重整，阅读顺序不再跟随当前单文件实现顺序变化。
- [`spec/operation/scf.md`](../../spec/operation/scf.md) 已明确“当前只覆盖最小 loop helper；未来若要扩展控制流须另开计划”。
- [`kernel_gen/operation/__init__.py`](../../kernel_gen/operation/__init__.py) 顶层导出集合被显式锁定，本轮没有继续膨胀。
- [`kernel_gen/operation/nn.py`](../../kernel_gen/operation/nn.py) 已降为聚合入口或薄 facade，family 逻辑拆到私有模块中；但 `from kernel_gen.operation.nn import ...` 继续有效。
- `test/operation` 已按 family 拆分，并新增：
  - `target registry` 缺字段错误路径；
  - `stride / offset` 组合边界；
  - 非法 `bound / step`；
  - 符号步长与 `bool` 负例。
- `pytest -q test/operation` 全绿，且本轮没有改动 `spec/operation`、`kernel_gen/operation`、`test/operation` 之外的实现目录。

## 验收设计

- 验收资产：
  - [`spec/operation/arch.md`](../../spec/operation/arch.md)
  - [`spec/operation/dma.md`](../../spec/operation/dma.md)
  - [`spec/operation/nn.md`](../../spec/operation/nn.md)
  - [`spec/operation/scf.md`](../../spec/operation/scf.md)
  - [`kernel_gen/operation/__init__.py`](../../kernel_gen/operation/__init__.py)
  - [`kernel_gen/operation/arch.py`](../../kernel_gen/operation/arch.py)
  - [`kernel_gen/operation/dma.py`](../../kernel_gen/operation/dma.py)
  - [`kernel_gen/operation/nn.py`](../../kernel_gen/operation/nn.py)
  - [`kernel_gen/operation/scf.py`](../../kernel_gen/operation/scf.py)
  - `kernel_gen/operation/_nn_common.py`
  - `kernel_gen/operation/_nn_elementwise.py`
  - `kernel_gen/operation/_nn_broadcast.py`
  - `kernel_gen/operation/_nn_structured.py`
  - `kernel_gen/operation/_nn_reduction.py`
  - `test/operation/*.py`
- 输入样例：
  - `launch_kernel(lambda lhs, rhs, out: None, SymbolDim("GRID_X"), 128, 4, "lhs", "rhs", "out")`
  - `slice(src, offsets=[0, 4], sizes=[8, 8], strides=[2, 1], space=MemorySpace.SM)`
  - `add(Memory(["M", "N"], NumericType.Float32), Memory([1, "N"], NumericType.Float32))`
  - `loop(0, SymbolDim("N"), SymbolDim("S"), trip_count=3)`
- 锁定输出：
  - `arch` 文本与实现不再存在“旧 `name: str` / 旧 `TLM` / 缺 barrier”的三口径
  - `dma` 的关系图与越界规则索引可直接命中
  - `nn` 文本与实现结构都以 family 为主轴
  - `kernel_gen.operation` 顶层不新增导出
  - `scf.loop` 对 `bool` 与非法 `trip_count / step` 路径有明确负例
- 必过命令：
  - `rg -n "静态设备值|动态回退|BarrierVisibility|launch_kernel\\(callee" spec/operation/arch.md`
  - `rg -n "关系图|越界规则索引|alloc|view|slice|reshape|copy" spec/operation/dma.md`
  - `rg -n "逐元素|broadcast|structured|reduction" spec/operation/nn.md`
  - `rg -n "最小 loop helper|未来扩展|trip_count" spec/operation/scf.md`
  - `pytest -q test/operation`

## 阶段拆分

### S1：arch / dma / scf spec 收口

#### 阶段目标

- 收口 `arch / dma / scf` 三组 spec，使其与当前实现 / 测试真实口径对齐，并补齐高层语义边界说明。

#### 目标 spec / API

- [`spec/operation/arch.md`](../../spec/operation/arch.md)
- [`spec/operation/dma.md`](../../spec/operation/dma.md)
- [`spec/operation/scf.md`](../../spec/operation/scf.md)
- `公开 API：kernel_gen.operation.arch / kernel_gen.operation.dma / kernel_gen.operation.scf.loop`

#### 可改文件

- `ARCHITECTURE/plan/operation_layer_refactor_green_plan.md`
- `spec/operation/arch.md`
- `spec/operation/dma.md`
- `spec/operation/scf.md`

#### 预期示例代码

```python
from kernel_gen.operation.arch import BarrierScope, BarrierVisibility, barrier, launch_kernel
from kernel_gen.operation.scf import loop
from kernel_gen.symbol_variable.symbol_dim import SymbolDim

barrier(visibility=[BarrierVisibility.TSM, BarrierVisibility.TLM], scope=BarrierScope.THREAD)
launch_kernel(lambda lhs, rhs, out: None, SymbolDim("GRID_X"), 128, 4, "lhs", "rhs", "out")

for i in loop(0, SymbolDim("N"), SymbolDim("S"), trip_count=3):
    pass
```

#### 预期输出

```text
arch.md:
- launch_kernel(callee, block, thread, subthread, *args)
- BarrierVisibility.TSM / BarrierVisibility.TLM
- TLM1 / TLM2 / TLM3

dma.md:
- alloc/view/slice/reshape/copy 关系图
- 越界规则索引

scf.md:
- 当前只覆盖最小 loop helper
```

#### 目标验收资产

- `spec/operation/arch.md`
- `spec/operation/dma.md`
- `spec/operation/scf.md`

#### 验收必过项目

- `rg -n "静态设备值|动态回退|BarrierVisibility|launch_kernel\\(callee" spec/operation/arch.md`
- `rg -n "关系图|越界规则索引|alloc|view|slice|reshape|copy" spec/operation/dma.md`
- `rg -n "最小 loop helper|未来扩展|trip_count" spec/operation/scf.md`

#### 任务新建建议

- `任务类型：spec`
- `任务目标：收口 arch / dma / scf 的 operation 高层语义合同`
- `记录文件：agents/codex-multi-agents/log/task_records/2026/16/20260415-operation-layer-s1.md`

### S2：nn spec 与顶层导出边界收口

#### 阶段目标

- 将 `nn` family 合同重排写进 [`spec/operation/nn.md`](../../spec/operation/nn.md)，并在计划正文中收口 `kernel_gen.operation` 顶层稳定导出集合；本阶段只定义文本合同与边界，不改实现、不拆测试。

#### 目标 spec / API

- [`spec/operation/nn.md`](../../spec/operation/nn.md)
- `公开 API：kernel_gen.operation 顶层稳定导出`
- `公开 API：kernel_gen.operation.nn`

#### 可改文件

- `spec/operation/nn.md`
- `ARCHITECTURE/plan/operation_layer_refactor_green_plan.md`

#### 预期示例代码

```python
from kernel_gen.operation import add, alloc, loop, matmul
from kernel_gen.operation.nn import broadcast, reduce_sum, transpose
```

#### 预期输出

```text
nn.md:
- 逐元素
- broadcast
- structured
- reduction

plan:
- 顶层稳定导出集合
- 不新增 kernel_gen.operation 顶层名字
- nn 实现拆分只在 S4 执行
```

#### 目标验收资产

- `spec/operation/nn.md`
- `ARCHITECTURE/plan/operation_layer_refactor_green_plan.md`

#### 验收必过项目

- `rg -n "逐元素|broadcast|structured|reduction" spec/operation/nn.md`
- `rg -n "顶层稳定导出|不新增顶层导出|kernel_gen.operation" ARCHITECTURE/plan/operation_layer_refactor_green_plan.md`

#### 任务新建建议

- `任务类型：spec`
- `任务目标：重排 nn spec 并锁定 operation 顶层导出边界`
- `记录文件：agents/codex-multi-agents/log/task_records/2026/16/20260415-operation-layer-s2.md`

### S3：arch / dma / scf 与顶层导出实现收口

#### 阶段目标

- 在不改动下游 dialect/codegen 的前提下，完成 `arch / dma / scf` 实现侧边界收口，并为顶层导出与 `dma` 统一校验入口补同阶段测试。

#### 目标 spec / API

- [`kernel_gen/operation/__init__.py`](../../kernel_gen/operation/__init__.py)
- [`kernel_gen/operation/arch.py`](../../kernel_gen/operation/arch.py)
- [`kernel_gen/operation/dma.py`](../../kernel_gen/operation/dma.py)
- [`kernel_gen/operation/scf.py`](../../kernel_gen/operation/scf.py)
- `公开 API：kernel_gen.operation / kernel_gen.operation.arch / kernel_gen.operation.dma / kernel_gen.operation.scf.loop`

#### 可改文件

- `kernel_gen/operation/__init__.py`
- `kernel_gen/operation/arch.py`
- `kernel_gen/operation/dma.py`
- `kernel_gen/operation/scf.py`
- `test/operation/test_operation_arch.py`
- `test/operation/test_operation_dma.py`
- `test/operation/test_operation_scf.py`
- `test/operation/test_operation_package_api.py`

#### 预期示例代码

```python
from kernel_gen.operation import add, alloc, loop, matmul
from kernel_gen.operation.arch import get_dynamic_memory
from kernel_gen.symbol_variable.memory import MemorySpace

assert get_dynamic_memory(MemorySpace.TLM1).space is MemorySpace.TLM1
```

#### 预期输出

```text
- kernel_gen.operation.__all__ 显式锁定
- dma 访问区域校验走统一入口
- scf.loop 拒绝 bool / 非法 step / 非法 trip_count
- arch 新增 target registry 缺字段错误路径
```

#### 目标验收资产

- `test/operation/test_operation_package_api.py`
- `test/operation/test_operation_arch.py`
- `test/operation/test_operation_dma.py`
- `test/operation/test_operation_scf.py`

#### 验收必过项目

- `pytest -q test/operation/test_operation_package_api.py test/operation/test_operation_arch.py test/operation/test_operation_dma.py test/operation/test_operation_scf.py`

#### 任务新建建议

- `任务类型：build`
- `任务目标：收口 arch / dma / scf 实现与 operation 顶层导出边界`
- `记录文件：agents/codex-multi-agents/log/task_records/2026/16/20260415-operation-layer-s3.md`

### S4：nn family 实现拆分

#### 阶段目标

- 将 `nn` 单文件实现拆成 family 模块，保留 `kernel_gen.operation.nn` 作为对外聚合入口，不改变公开导入方式。

#### 目标 spec / API

- [`kernel_gen/operation/nn.py`](../../kernel_gen/operation/nn.py)
- `kernel_gen/operation/_nn_common.py`
- `kernel_gen/operation/_nn_elementwise.py`
- `kernel_gen/operation/_nn_broadcast.py`
- `kernel_gen/operation/_nn_structured.py`
- `kernel_gen/operation/_nn_reduction.py`
- `公开 API：kernel_gen.operation.nn`

#### 可改文件

- `kernel_gen/operation/nn.py`
- `kernel_gen/operation/_nn_common.py`
- `kernel_gen/operation/_nn_elementwise.py`
- `kernel_gen/operation/_nn_broadcast.py`
- `kernel_gen/operation/_nn_structured.py`
- `kernel_gen/operation/_nn_reduction.py`

#### 预期示例代码

```python
from kernel_gen.operation.nn import add, broadcast, img2col2d, reduce_sum, softmax
```

#### 预期输出

```text
kernel_gen.operation.nn:
- 保留公开导入入口
- 仅负责 re-export / facade

私有模块:
- _nn_common
- _nn_elementwise
- _nn_broadcast
- _nn_structured
- _nn_reduction
```

#### 目标验收资产

- `kernel_gen/operation/nn.py`
- `kernel_gen/operation/_nn_common.py`
- `kernel_gen/operation/_nn_elementwise.py`
- `kernel_gen/operation/_nn_broadcast.py`
- `kernel_gen/operation/_nn_structured.py`
- `kernel_gen/operation/_nn_reduction.py`

#### 验收必过项目

- `pytest -q test/operation/test_operation_nn.py`

#### 任务新建建议

- `任务类型：build`
- `任务目标：拆分 nn family 实现并保持 kernel_gen.operation.nn 聚合入口稳定`
- `记录文件：agents/codex-multi-agents/log/task_records/2026/16/20260415-operation-layer-s4.md`

### S5：operation 测试拆分与负例补齐

#### 阶段目标

- 按 helper family 拆小测试文件，并补齐 prompt 中点名的负例与组合边界。

#### 目标 spec / API

- `公开 API：test/operation family 测试布局`

#### 可改文件

- `test/operation/test_operation_dma.py`
- `test/operation/test_operation_nn.py`
- `test/operation/test_operation_arch.py`
- `test/operation/test_operation_scf.py`
- `test/operation/test_operation_dma_alloc_lifecycle.py`
- `test/operation/test_operation_dma_transfer_view.py`
- `test/operation/test_operation_nn_elementwise.py`
- `test/operation/test_operation_nn_broadcast.py`
- `test/operation/test_operation_nn_structured.py`
- `test/operation/test_operation_nn_reduction.py`

#### 预期示例代码

```python
pytest -q test/operation/test_operation_nn_elementwise.py
pytest -q test/operation/test_operation_nn_structured.py
pytest -q test/operation/test_operation_dma_transfer_view.py
```

#### 预期输出

```text
- arch: target registry 缺字段错误路径
- dma: stride / offset 组合边界
- nn: family 文件拆分
- scf: 非法 bound / step / bool / 符号步长
```

#### 目标验收资产

- `test/operation/*.py`

#### 验收必过项目

- `pytest -q test/operation`

#### 任务新建建议

- `任务类型：build`
- `任务目标：拆分 operation 测试并补齐 arch / dma / nn / scf 负例`
- `记录文件：agents/codex-multi-agents/log/task_records/2026/16/20260415-operation-layer-s5.md`

### S6：operation 组审查

#### 阶段目标

- 复核 `spec / 实现 / 测试` 是否按“纯高层语义层”闭环，没有误改到 `dialect / codegen`。

#### 目标 spec / API

- `公开 API：operation 组整体公开边界`

#### 可改文件

- `agents/codex-multi-agents/log/task_records/2026/16/20260415-operation-layer-s6.md`

#### 预期示例代码

```text
review 只检查：
1. 顶层导出是否膨胀
2. spec 与实现是否同口径
3. 是否误改到 dialect / codegen
```

#### 预期输出

```text
审查结论：
- 通过，或
- 最小阻断项：...
```

#### 目标验收资产

- `agents/codex-multi-agents/log/task_records/2026/16/20260415-operation-layer-s6.md`

#### 验收必过项目

- `pytest -q test/operation`

#### 任务新建建议

- `任务类型：review`
- `任务目标：复核 operation 组重构未越过高层语义边界`
- `记录文件：agents/codex-multi-agents/log/task_records/2026/16/20260415-operation-layer-s6.md`

### S7：operation 组合并

#### 阶段目标

- 交付 `operation` 组文档、实现与测试重构结果，不扩大到其他层。

#### 目标 spec / API

- `公开 API：operation 组稳定交付面`

#### 可改文件

- `agents/codex-multi-agents/log/task_records/2026/16/20260415-operation-layer-s7.md`

#### 预期示例代码

```text
merge 范围仅限：
- spec/operation
- kernel_gen/operation
- test/operation
- 同链记录文件
```

#### 预期输出

```text
operation 组重构已交付：
- spec 对齐
- nn family 拆分
- 测试拆分
- 顶层导出锁定
```

#### 目标验收资产

- `pytest -q test/operation`

#### 验收必过项目

- `pytest -q test/operation`

#### 任务新建建议

- `任务类型：merge`
- `任务目标：合并 operation 组文档与实现重构结果`
- `记录文件：agents/codex-multi-agents/log/task_records/2026/16/20260415-operation-layer-s7.md`

## 待确认项

- 无阻塞性待确认项。
- 当前互评重点只剩两项：
  - `nn` 的拆分是否采用本计划给出的“私有 family 模块 + facade”路径；
  - `test/operation/test_operation_dma.py` 与 `test/operation/test_operation_nn.py` 的拆分粒度是否需要再细于当前计划。

## 参考资料

- [`spec/operation/arch.md`](../../spec/operation/arch.md)
- [`spec/operation/dma.md`](../../spec/operation/dma.md)
- [`spec/operation/nn.md`](../../spec/operation/nn.md)
- [`spec/operation/scf.md`](../../spec/operation/scf.md)
- [`kernel_gen/operation/__init__.py`](../../kernel_gen/operation/__init__.py)
- [`kernel_gen/operation/arch.py`](../../kernel_gen/operation/arch.py)
- [`kernel_gen/operation/dma.py`](../../kernel_gen/operation/dma.py)
- [`kernel_gen/operation/nn.py`](../../kernel_gen/operation/nn.py)
- [`kernel_gen/operation/scf.py`](../../kernel_gen/operation/scf.py)
- [`test/operation/test_operation_arch.py`](../../test/operation/test_operation_arch.py)
- [`test/operation/test_operation_dma.py`](../../test/operation/test_operation_dma.py)
- [`test/operation/test_operation_nn.py`](../../test/operation/test_operation_nn.py)
- [`test/operation/test_operation_scf.py`](../../test/operation/test_operation_scf.py)

## 当前同步现场终验复核（2026-04-17 01:01 +0800）

- 终验人：`大闸蟹`
- 终验结论：`通过`
- 归档结论：`可进入归档链`
- 验证基线：
  - 以同步现场 `/home/lfr/kernelcode_generate/wt-20260415-operation-layer-s1` 为准；本次复核时间为 `2026-04-17 01:01 +0800`。
  - 该现场 `HEAD` 为 `bb5139006c900cfafb9d53f0214002379218751b`。
  - 在该同步现场复跑本计划终验资产：
    - `rg -n "静态设备值|动态回退|BarrierVisibility|launch_kernel\\(callee" spec/operation/arch.md`：命中通过。
    - `rg -n "关系图|越界规则索引|alloc|view|slice|reshape|copy" spec/operation/dma.md`：命中通过。
    - `rg -n "逐元素|broadcast|structured|reduction" spec/operation/nn.md`：命中通过。
    - `rg -n "最小 loop helper|未来扩展|trip_count" spec/operation/scf.md`：命中通过。
    - `PYTHONDONTWRITEBYTECODE=1 pytest -q test/operation`：`139 passed in 0.33s`。
- 终验说明：
  - 本轮按“最新同步现场优先”执行，与守护最好的爱莉希雅在同一 worktree 基线上的终验口径一致；根目录主仓若仍停在其他现场，只记为环境差异，不单独构成功能阻断。
  - `spec/operation/arch.md`、`spec/operation/dma.md`、`spec/operation/nn.md`、`spec/operation/scf.md` 的计划命中文本均已存在，说明 `arch / dma / nn / scf` 的公开边界、family 主轴与禁止扩展范围已按计划落到文本真源。
  - `test/operation` 在该同步现场整组回归通过，支持本计划交付范围已闭环进入最新同步现场；就我侧终验复核结论，本计划已满足完成态，可进入归档链。
