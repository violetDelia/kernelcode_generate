# symbol_loop_hoist_green_plan.md

## 验收结论（归档）

- 结论：通过
- 验收日期：2026-04-07
- 评审人：大闸蟹、守护最好的爱莉希雅
- S1 合并提交：`ae438cf`
- 链路记录（含收口/审查/复审与 gate 证据）：`agents/codex-multi-agents/log/task_records/2026/15/20260407-symbol-loop-hoist-s1.md`

## 关键验证命令（证据引用见链路记录）

- `PYTHONPATH=. pytest -q test/pass/test_symbol_loop_hoist.py`
- `PYTHONPATH=. pytest -q test/pass/test_pass_manager.py -k symbol_loop_hoist`
- `PYTHONPATH=. pytest -q --cov=kernel_gen.passes.lowering.symbol_loop_hoist --cov-branch --cov-report=term-missing test/pass/test_symbol_loop_hoist.py`

## 进度

| 编号 | 依赖 | worktree | 记录文件 | 进度 |
| --- | --- | --- | --- | --- |
| `S1` | `无` | `wt-20260407-symbol-loop-hoist-s1` | `agents/codex-multi-agents/log/task_records/2026/15/20260407-symbol-loop-hoist-s1.md` | `已合并收口（merge_commit=ae438cf）` |

## 计划目标

- 新增 `symbol-loop-hoist` pass，只处理 `symbol.for`。
- 目标是把循环内仅依赖外层 symbol、常量、`tuner.param` 的值提前到循环外，优先覆盖：
  - `tuner.param`
  - `symbol.get_dim / symbol.get_shape / symbol.get_stride`
  - 纯 `arith/index` 计算
  - 可跨迭代复用的 `dma.alloc / kernel.alloc`
  - 只改元信息、不搬数据的 `dma.view / dma.reshape`
  - 固定窗口、只读来源的 `dma.slice / dma.load`
- 本计划重点不是“做一个通用 LICM”，而是给 split 后的 `symbol.for` 提供稳定、可复现的 hoist 合同。
- 目标完成态：
  - `kernel_split` 之后出现的循环内 invariant `alloc` / 纯计算能被移到 `symbol.for` 外；
  - 仍依赖 loop iv、每轮必须独立分配、或会真正搬数据的 op 必须保留在循环内；
  - 前后 IR 变化可以通过 expectation 与 pytest 直接看到。

## 当前基线（2026-04-06）

- 项目内已经有：
  - `KernelSplitPass`：把 tile 结构表达成 `symbol.for`
  - `LowerDmaMemoryHierarchyPass`：负责后续 `GM -> SM -> LM` / `LM -> SM -> GM`
- 当前仓库没有专门针对 `symbol.for` 的 hoist pass。
- 官方现成方案不能直接覆盖本需求：
  - xDSL 的 `loop_invariant_code_motion` 主要面向“无副作用 + 可安全提前”的 op；
  - xDSL 的 `loop_hoist_memref` 只覆盖受限的 memref 访问模式；
  - 二者都不等于“把 split 后 kernel/dma 场景里的 alloc 与 symbol 计算稳定外提”。

## 讨论结论

### 计划目标

- 这份计划只做一件事：把 `symbol.for` 内可安全提前的对象移到外层 block。
- 优先解决 split 之后循环体里出现 `alloc`、shape 公式、symbol 查询重复构造的问题。
- pass 输出仍保持单函数、单 region 结构，不新建 helper 函数。

### 是否有更合理的方案

- 不采用“直接复用 xDSL LICM”的方案。
  - 原因：本项目要处理的是 `symbol.for + tuner.param + kernel/dma alloc` 的组合，不是纯 SSA 计算的最小 LICM 场景。
  - `alloc` 一类 op 还涉及生命周期与跨迭代复用判定，通用 LICM 很难直接给出项目所需合同。
- 不采用“把所有 dma op 都当成可提前对象”的方案。
  - 原因：`dma.slice / dma.deslice / dma.broadcast / dma.transpose` 这类 op 代表真实搬运或语义改写，提前后很容易改变每轮执行语义。
- 采用单独的 `symbol-loop-hoist` pass，白名单推进。
- 第一版除了 `alloc` 与符号计算，还直接覆盖“固定窗口读入”场景，避免 split 后每轮重复读取同一块只读数据。

### 依赖

- 输入前提：
  - `LowerNnToKernelPass`
  - `BufferResultsToOutParamsPass`
  - `KernelSplitPass`
- 推荐顺序：
  - `LowerNnToKernelPass -> BufferResultsToOutParamsPass -> KernelSplitPass -> SymbolLoopHoistPass -> LowerDmaMemoryHierarchyPass`
- 本 pass 只接受已经出现 `symbol.for` 的 IR；若没有 `symbol.for`，按 no-op 处理。

### 验证合理性

- 这类 pass 最关键的是“前后 IR 是否真的发生了外提”，因此必须同时有：
  - `pytest`：验证白名单、禁止项、错误短语
  - `expectation`：打印 before/after IR，直接看到 `symbol.for` 外是否新增了 hoisted op
- 完成判断不能只看 pass 不报错，必须看到：
  - before 在循环内
  - after 在循环外
  - after 仍满足 verifier

### 可维护性

- 采用“白名单 + 明确禁止项”而不是通配匹配。
- 第一版只覆盖少量确定安全的 op，后续若要扩 `dma.*`，再新增条目和用例，不在第一版里做模糊兜底。
- 失败短语固定，后续扩展时不用重写整套 expectation。

## 固定合同

- pass 名称：`symbol-loop-hoist`
- Python 入口：`SymbolLoopHoistPass`
- 作用对象：只处理 `symbol.for`
- 不新建函数，不改函数签名，不改 tile 参数来源
- `tuner.param` 仍然是 tile 大小与相关动态值的公开来源
- 只允许 hoist 下列对象：
  - 所有输入都定义在 loop 外的 `tuner.param`
  - 所有输入都定义在 loop 外的 `symbol.get_dim / symbol.get_shape / symbol.get_stride`
  - 所有输入都定义在 loop 外的 `arith` / `index` 纯计算
  - `shape/space/dtype` 不依赖 loop iv，且语义允许跨迭代复用的 `dma.alloc / kernel.alloc`
  - 只改 memory 元信息、不做真实搬运的 `dma.view / dma.reshape`
  - 固定窗口、只读来源、且结果可跨迭代复用的 `dma.slice / dma.load`
- 明确不允许 hoist：
  - 依赖 loop iv 或 loop-carried value 的任何 op
  - `dma.deslice / dma.broadcast / dma.transpose`
  - `dma.store`
  - 任何有写副作用的 op
  - 每轮必须独立生命周期的 `alloc`

### `alloc` 外提条件

- 只有同时满足以下条件，`alloc` 才能外提：
  - `shape`、`dynamic_shape`、`dtype`、`space` 都不依赖当前 `symbol.for` 的 iv
  - `alloc` 的所有输入都定义在 loop 外，或这些输入本身也会在本轮一起外提
  - 该 buffer 语义上允许跨迭代复用，不要求“每轮独立一份”
  - 外提后生命周期仍正确，不会引入写后读、读后写冲突
- 以下 `alloc` 不允许外提：
  - 大小依赖 iv 或当前 tile 路径
  - 每轮都必须重新初始化才能保证正确结果
  - 被下游视作“当前迭代私有对象”的临时 buffer

### 固定窗口 `view / slice / load` 外提条件

- `dma.view / dma.reshape` 可外提的前提：
  - `source` 定义在 loop 外
  - `offset/size/stride` 都不依赖 iv
  - 该 op 只承担窗口描述，不承担真实写入
- `dma.slice / dma.load` 进入第一版，但只允许最小子集：
  - `source` 定义在 loop 外
  - `offsets/sizes/strides` 全部与 iv 无关
  - `source` 在整个 `symbol.for` 期间是只读的，循环体内不存在别名写入
  - 读取结果只作为只读输入被后续消费，不在循环体内被改写
  - 若 `slice/load` 结果写入一个 temporary memory，该 temporary memory 也必须满足可跨迭代复用
- 以下 `slice / load` 不允许外提：
  - 窗口位置依赖 iv
  - `source` 在循环体内会被写回、更新或别名修改
  - 读取结果在循环内还会被覆盖、回填或作为 in-place 输出

## 前后 IR 示例

### 示例 1：`alloc + symbol 计算` 可以外提

输入 IR：

```text
%tile_m = tuner.param : !symbol.dim<"TILE_M">
symbol.for %i = %lb to %ub step %step : !symbol.int<"0">, !symbol.int<"M">, !symbol.int<"TILE_M"> {
  %m = symbol.get_dim %arg0, 0 : !nn.memory<[M, K], i32, #layout, #GM> -> !symbol.int<"M">
  %span = arith.muli %m, %c4 : !symbol.int<"M">, !symbol.int<"4"> -> !symbol.int<"M*4">
  %tmp = dma.alloc (%m, %c128) : !nn.memory<[M, 128], i32, #layout, #LM>
  %0 = kernel.matmul %a_tile, %b_tile outs(%tmp)
}
```

预期输出：

```text
%tile_m = tuner.param : !symbol.dim<"TILE_M">
%m = symbol.get_dim %arg0, 0 : !nn.memory<[M, K], i32, #layout, #GM> -> !symbol.int<"M">
%span = arith.muli %m, %c4 : !symbol.int<"M">, !symbol.int<"4"> -> !symbol.int<"M*4">
%tmp = dma.alloc (%m, %c128) : !nn.memory<[M, 128], i32, #layout, #LM>
symbol.for %i = %lb to %ub step %step : !symbol.int<"0">, !symbol.int<"M">, !symbol.int<"TILE_M"> {
  %0 = kernel.matmul %a_tile, %b_tile outs(%tmp)
}
```

### 示例 2：依赖 loop iv 的对象不能外提

输入 IR：

```text
symbol.for %i = %lb to %ub step %step : !symbol.int<"0">, !symbol.int<"M">, !symbol.int<"TILE_M"> {
  %tile = dma.alloc (%step, %c128) : !nn.memory<[TILE_M, 128], i32, #layout, #LM>
  %lhs = dma.slice %arg0[%i, 0][%step, %c128][1, 1]
  %0 = kernel.add %lhs, %bias outs(%tile)
}
```

预期输出：

```text
symbol.for %i = %lb to %ub step %step : !symbol.int<"0">, !symbol.int<"M">, !symbol.int<"TILE_M"> {
  %tile = dma.alloc (%step, %c128) : !nn.memory<[TILE_M, 128], i32, #layout, #LM>
  %lhs = dma.slice %arg0[%i, 0][%step, %c128][1, 1]
  %0 = kernel.add %lhs, %bias outs(%tile)
}
```

说明：

- `%tile` 依赖当前 tile 大小与当前迭代路径，不能提前。
- `dma.slice` 属于真实窗口搬运，也不能提前。

### 示例 3：固定窗口、只读来源的 `dma.slice` 可以外提

输入 IR：

```text
%bias_win = dma.view %bias[%c0, %c0][%c1, %c128][%c1, %c1]
symbol.for %i = %lb to %ub step %step : !symbol.int<"0">, !symbol.int<"M">, !symbol.int<"TILE_M"> {
  %bias_tile = dma.alloc (%c1, %c128) : !nn.memory<[1, 128], i32, #layout, #LM>
  dma.slice(%bias_tile, %bias_win, %c0, %c0, %c1, %c128, %c1, %c1)
  %0 = kernel.add %lhs_tile, %bias_tile outs(%out_tile)
}
```

预期输出：

```text
%bias_win = dma.view %bias[%c0, %c0][%c1, %c128][%c1, %c1]
%bias_tile = dma.alloc (%c1, %c128) : !nn.memory<[1, 128], i32, #layout, #LM>
dma.slice(%bias_tile, %bias_win, %c0, %c0, %c1, %c128, %c1, %c1)
symbol.for %i = %lb to %ub step %step : !symbol.int<"0">, !symbol.int<"M">, !symbol.int<"TILE_M"> {
  %0 = kernel.add %lhs_tile, %bias_tile outs(%out_tile)
}
```

说明：

- `bias` 是 loop 期间只读数据。
- 窗口参数固定，不依赖 `%i`。
- `bias_tile` 只作为只读输入参与后续计算，因此可以在循环外准备一次。

## 计划任务

### `S1`

- `任务类型`：`收口任务（规格+实现+测试）`
- `任务目标`：
  - 新增 `spec/pass/lowering/symbol_loop_hoist.md`
  - 新增 `kernel_gen/passes/lowering/symbol_loop_hoist.py`
  - 新增 `test/pass/test_symbol_loop_hoist.py`
  - 新增 `expectation/pass/lowing/symbol_loop_hoist/basic.py`
  - 按推荐顺序补齐 `PassManager` 对 `symbol-loop-hoist` 的顺序约束
- `重点内容`：
  - 定义白名单、禁止项、错误短语
  - 完成 `symbol.for` 内 hoist 重写
  - 保证 `alloc` 生命周期与使用点支配关系正确
  - 固定窗口 `slice/load` 只在只读来源场景下外提
  - expectation 直接打印 before/after IR
- `不采用的做法`：
  - 不做通用 LICM 框架改造
  - 不把 pass 写成“无论什么 op 只要看起来没用 iv 就往外搬”
  - 不把 `dma.deslice / dma.broadcast / dma.transpose` 纳入第一版范围
- `示例代码`：

```python
from kernel_gen.passes.lowering.kernel_split import KernelSplitPass
from kernel_gen.passes.lowering.symbol_loop_hoist import SymbolLoopHoistPass

module = KernelSplitPass().run(module)
module = SymbolLoopHoistPass().run(module)
```

- `预期输出`：

```text
before: symbol.for 内存在 dma.alloc / symbol.get_dim / arith.muli
after:  symbol.for 外出现可复用的 dma.alloc / symbol.get_dim / arith.muli / 固定窗口 dma.slice
after:  symbol.for 内只保留真正依赖 %i 的 op
禁止: SymbolLoopHoistPass 静默搬出依赖 %i 的 dma.slice
禁止: SymbolLoopHoistPass 静默搬出 dma.deslice
```

- `必须测试通过项目`：
  - `pytest -q test/pass/test_symbol_loop_hoist.py`
  - `pytest -q test/pass/test_pass_manager.py -k "symbol_loop_hoist or split or dma"`
  - `PYTHONPATH=. python expectation/pass/lowing/symbol_loop_hoist/basic.py`
- `完成标准`：
  - expectation 能清楚打印 before/after IR
  - 可外提对象全部移到 `symbol.for` 外
  - 不可外提对象保持在 `symbol.for` 内
  - 顺序错误、生命周期错误、非法 hoist 都有明确失败短语

## 失败短语

- `SymbolLoopHoistRequiresSymbolFor`
- `SymbolLoopHoistDependsOnLoopIV`
- `SymbolLoopHoistSideEffectOp`
- `SymbolLoopHoistAllocLifetimeUnsafe`
- `SymbolLoopHoistAllocReuseUnsafe`
- `SymbolLoopHoistAllocDependsOnLoopIV`
- `SymbolLoopHoistFixedReadSourceMutated`
- `SymbolLoopHoistFixedReadResultRewritten`
- `SymbolLoopHoistDominanceError`
- `SymbolLoopHoistVerifierError`

## 评审摘要

- 评审结论：`已评审通过`
- 评审人：`大闸蟹`、`守护最好的爱莉希雅`
- 评审时间：`2026-04-07`
- 六项摘要：
  - `目标`：通过；新增 `symbol-loop-hoist`，只处理 `symbol.for`，第一版范围清晰。
  - `边界`：通过；不新建函数，不改函数签名，不改 tile 参数来源，不包含 `dma.deslice / dma.broadcast / dma.transpose / dma.store`。
  - `依赖顺序`：通过；`LowerNnToKernelPass -> BufferResultsToOutParamsPass -> KernelSplitPass -> SymbolLoopHoistPass -> LowerDmaMemoryHierarchyPass` 自洽。
  - `验证命令`：通过；`pytest` 与 `expectation` 命令完整，能够直接判断前后 IR 变化。
  - `失败短语`：通过；`alloc` 生命周期、循环变量依赖、只读窗口被改写等失败口径已列清楚。
  - `不可改文件`：通过；遵循仓库默认 `immutable` 约束。

## 最终验收摘要

- 最终验收结论：`通过`
- 评审人：`大闸蟹`、`守护最好的爱莉希雅`
- 验收时间：`2026-04-07`
- 摘要：
  - `S1` 已合并收口：`merge_commit=ae438cf`
  - 任务记录：[`agents/codex-multi-agents/log/task_records/2026/15/20260407-symbol-loop-hoist-s1.md`](agents/codex-multi-agents/log/task_records/2026/15/20260407-symbol-loop-hoist-s1.md)
  - 必须测试通过项目已具备稳定证据：
    - `pytest -q test/pass/test_symbol_loop_hoist.py`
    - `pytest -q test/pass/test_pass_manager.py -k "symbol_loop_hoist or split or dma"`
    - `PYTHONPATH=. python expectation/pass/lowing/symbol_loop_hoist/basic.py`
  - 收口修复与复审已完成，当前无阻断项。

## 外部资料参考

- xDSL Loop Invariant Code Motion：<https://docs.xdsl.dev/reference/transforms/loop_invariant_code_motion/>
- xDSL Loop Hoist MemRef：<https://docs.xdsl.dev/reference/transforms/loop_hoist_memref/>
- MLIR Passes：<https://mlir.llvm.org/docs/Passes/>

## 文档信息

- 创建者：`大闸蟹`
- 最后修改人：`大闸蟹`
- `文档`：[`ARCHITECTURE/plan/symbol_loop_hoist_green_plan.md`](ARCHITECTURE/plan/symbol_loop_hoist_green_plan.md)
- `spec`：[`spec/pass/lowering/symbol_loop_hoist.md`](spec/pass/lowering/symbol_loop_hoist.md)
- `test`：
  - [`test/pass/test_symbol_loop_hoist.py`](test/pass/test_symbol_loop_hoist.py)
  - [`test/pass/test_pass_manager.py`](test/pass/test_pass_manager.py)
- `功能实现`：
  - [`kernel_gen/passes/lowering/symbol_loop_hoist.py`](kernel_gen/passes/lowering/symbol_loop_hoist.py)
  - [`kernel_gen/passes/pass_manager.py`](kernel_gen/passes/pass_manager.py)
