# memory_pool_pass_green_plan.md

## 进度

| 编号 | 依赖 | worktree | 记录文件 | 进度 |
| --- | --- | --- | --- | --- |
| `S1` | `无` | `wt-20260407-memory-pool-s1` | `agents/codex-multi-agents/log/task_records/2026/15/20260407-memory-pool-s1.md` | `已合并收口（merge_commit=d0bdd9d；T-20260407-c857fff4，李白；push(main)=exit=0）` |
| `S2` | `S1` | `wt-20260407-memory-pool-s1` | `agents/codex-multi-agents/log/task_records/2026/15/20260407-memory-pool-s1.md` | `已合并收口（merge_commit=3426135；T-20260407-ad8346ab，李白；push(main)=exit=0）` |
| `S3` | `S1,S2` | `wt-20260408-memory-pool` | `agents/codex-multi-agents/log/task_records/2026/15/20260408-memory-pool-s3.md` | `已合并收口（T-20260408-47071895；详见记录文件）` |
| `S4` | `S1,S2,S3` | `wt-20260408-memory-pool` | `agents/codex-multi-agents/log/task_records/2026/15/20260408-memory-pool-s4.md` | `已合并收口（T-20260408-966f04e0；详见记录文件）` |

## 计划目标

- 新增一个公开 pass：`memory-pool`，用于在单个 `func.func` 内分析 `dma.alloc / dma.free / use` 的生命周期，并把可复用的 allocation 收口为更少的 pool allocation。
- pass 既要给出稳定的生命周期摘要，也要在满足条件时改写 IR；不拆成两个公开 pass。
- 第一版重点覆盖：
  - 直线代码中的同 bucket `dma.alloc` 复用；
  - `symbol.for` 内外的词法生命周期分析；
  - 基于 `i8` pool + `dma.view` 的 typed subview 重建；
  - 显式失败的拒绝路径，而不是静默跳过后让结果看起来“像是支持”。
- 第一版不追求“任意 layout / 任意 alias / 任意副作用路径”的全覆盖，只先把合同写清并跑通最小稳定子集。

## 当前基线（2026-04-07）

- 需求来源是 [`analysis .plan.md`](../../analysis%20.plan.md)；当前仓库还没有单独的 `memory-pool` pass。
- 当前公开 IR 已有：
  - [`spec/dialect/dma.md`](../../spec/dialect/dma.md) 中的 `dma.alloc / dma.free / dma.view / dma.reshape`
  - [`spec/pass/lowering/symbol_loop_hoist.md`](../../spec/pass/lowering/symbol_loop_hoist.md)
  - [`spec/pass/lowering/dma_memory_hierarchy/spec.md`](../../spec/pass/lowering/dma_memory_hierarchy/spec.md)
- `analysis .plan.md` 里的 `alloc [2*A*B, i8] + with type` 思路保留为本计划第一版主路径。
- 本计划不再把 `#layout.contiguous` 作为第一版公开合同前提，也不要求 pool bucket 绑定具体 layout 文本。
- 第一版明确采用：
  - 按 `space` 维度分 bucket；
  - 每个 bucket 统一生成 `i8` 类型的一维 byte pool；
  - `dma.view` 允许从 byte pool 上直接构造目标 typed memory；
  - pool 重写按字节数而不是按 `numel + 原 dtype` 计算 offset / peak。

## 讨论结论

### 计划目标

- 公开名确定为 `memory-pool`，Python 入口为 `MemoryPoolPass`。
- 这次计划同时覆盖：
  - 生命周期分析；
  - peak size 计算；
  - offset 复用分配；
  - IR 重写；
  - expectation 与 pytest。
- pass 输出除了改写后的 module，还应提供稳定可查询的摘要，便于测试与 expectation 对照生命周期表。

### 是否有更合理的方案

- 不采用“两个公开 pass：先 analysis，再 rewrite”的方案。
  - 原因：对外暴露两套入口会让顺序、摘要来源、失败路径分散；当前更适合一个公开 pass、内部拆 analysis helper。
- 采用 `i8` byte pool + `dma.view` typed subview 的第一版方案。
  - 原因：这和用户给出的 memory pool 目标一致，也更适合跨 dtype 复用同一块 pool memory。
- 不采用“pool 仍按原始 dtype 分 bucket”的方案。
  - 原因：这会直接放弃 mixed dtype alloc 复用，和 byte pool 目标冲突。
- 不采用“先只做 summary，不做 IR 改写”的方案。
  - 原因：用户给出的目标明确包含“根据生命周期表复用 alloc 内存”；只有 summary 还不够。
- 不采用“所有 `dma.alloc` 都自动进 pool”的方案。
  - 原因：loop 私有 buffer、escaping alloc、非连续布局、未知 alias 这些场景都需要明确拒绝。

### 依赖

- 输入前提：
  - [`spec/dialect/dma.md`](../../spec/dialect/dma.md)
  - [`spec/dialect/symbol.md`](../../spec/dialect/symbol.md)
  - [`spec/pass/pass_manager.md`](../../spec/pass/pass_manager.md)
  - [`spec/pass/lowering/symbol_loop_hoist.md`](../../spec/pass/lowering/symbol_loop_hoist.md)
  - [`spec/pass/lowering/dma_memory_hierarchy/spec.md`](../../spec/pass/lowering/dma_memory_hierarchy/spec.md)
- 推荐顺序：
  - `LowerNnToKernelPass -> BufferResultsToOutParamsPass -> TilePass -> SymbolLoopHoistPass -> MemoryPoolPass -> LowerDmaMemoryHierarchyPass`
- 这样安排的原因：
  - `TilePass` 与 `SymbolLoopHoistPass` 先把循环结构和 invariant alloc 形态稳定下来；
  - `MemoryPoolPass` 再做生命周期复用；
  - `LowerDmaMemoryHierarchyPass` 最后再把空间路径细化成 `GM/SM/LM` staging。

### 验证合理性

- 只看“pass 不报错”不够，必须同时看到：
  - 生命周期摘要是否和预期一致；
  - peak size 是否和预期一致；
  - after IR 是否真的把多个 `dma.alloc` 收口成一个 pool alloc；
  - 原本可复用的 allocation 是否共享 offset；
  - 不支持场景是否给出明确错误短语。
- expectation 需要直接打印：
  - before IR
  - summary table
  - after IR
- pytest 需要覆盖：
  - 直线路径；
  - `symbol.for` 词法生命周期；
  - bucket 分组；
  - escaping / custom stride / alias 拒绝路径。

### 可维护性

- 生命周期摘要 schema 要固定，不允许每个测试各自拼字符串。
- bucket 规则要固定；第一版只按 `space` 分 bucket，offset/peak 统一按字节数统计。
- 失败短语要统一前缀 `MemoryPool*`，便于 expectation 和审查直接比对。
- 第一版不依赖 `#layout.contiguous` 文本；若某个 alloc 需要显式 custom stride / 非线性布局解释，则单独拒绝，不在本轮混入模糊行为。

## 固定合同（草案）

- pass 名称：`memory-pool`
- Python 入口：`MemoryPoolPass`
- 目标对象：单个 `func.func` 内的 `dma.alloc / dma.free / use`
- 第一版只处理：
  - `dma.alloc` 结果类型为 `!nn.memory<...>`
  - 默认线性字节池可覆盖的 alloc
  - 不逃逸当前函数
  - 不穿越未知 region / 未知 side-effect op 的明确子集
- pool bucket 的最小划分维度：
  - `space`
- 每个 bucket 只生成同 space 的 `i8` pool allocation；允许在同一 bucket 内复用不同 `element_type` 的 alloc。
- pool memory 采用一维 `!nn.memory<[peak_bytes], i8, ...>` 表达。
- 原始 alloc 重写后，统一变为：
  - `pool alloc`
  - `dma.view` 从 byte pool 直接构造目标 typed memory
- 原本参与 pool 的独立 `dma.alloc / dma.free` 在 after IR 中不再保留。
- 若函数里没有符合条件的 alloc，pass 允许 no-op，不报错。

### byte pool typed view 合同

- 第一版新增的公开口径是：`dma.view` 可从 `i8` pool memory 上直接得到目标 typed memory。
- `dma.view` 选取的底层区间按字节解释；目标 memory 的合法性按 `result.numel * sizeof(result.element_type)` 校验。
- `dma.view` 的 `space` 必须与 byte pool 相同；不允许跨 `space` 重解释。
- 对 memory pool 场景，typed view 的 `offset` 可按目标 `element_type` 的元素单位表达；例如：
  - `memory<12, i8>.subview(1, 2, f32)`
  - 语义上选取字节区间 `[4, 12)`，结果解释为 `2` 个 `f32`
- 若某个 typed view 的字节区间越界、无法整除目标 dtype 字节宽度，或需要显式 custom stride 才能成立，则必须报错。

### 生命周期摘要 schema

- `MemoryPoolInterval`
  - `name`
  - `bucket_key`
  - `size_bytes_expr`
  - `begin_index`
  - `end_index`
  - `offset_bytes_expr`
- `MemoryPoolSummary`
  - `func_name`
  - `intervals`
  - `peak_bytes_by_bucket`
  - `pool_count`

### 生命周期规则

- `begin_index / end_index` 使用单函数词法顺序索引。
- 对 `symbol.for`：
  - loop 内 alloc 的生命周期按“region 进入 -> region 退出”的词法范围统计；
  - 第一版不把 trip count 乘进并发占用，只按同一时刻的最大词法重叠量计算。
- 两个 allocation 只有在以下条件同时成立时才允许复用同一 offset：
  - bucket 相同；
  - 生命周期不重叠；
  - 中间不存在未知 alias 写入或 escaping 使用；
  - 重写后 typed `dma.view` 仍满足字节区间与 dtype 校验。

### 拒绝路径

- `MemoryPoolEscapingAlloc`
  - alloc 结果被返回、写入未知容器、传给未知 call，或进入当前计划未覆盖的逃逸路径。
- `MemoryPoolUnsupportedNonLinearAlloc`
  - alloc 需要显式 custom stride / 非线性布局解释，当前 byte pool v1 不承接。
- `MemoryPoolUnsupportedRegionEscape`
  - alloc 生命周期跨越当前计划未承接的 region/control-flow 结构。
- `MemoryPoolInvalidLifetime`
  - free/use 顺序异常，无法构造稳定区间。
- `MemoryPoolUnsupportedPoolBucket`
  - 该 alloc 无法归入当前按 `space` 划分的 byte pool bucket。
- `MemoryPoolTypedViewOutOfBounds`
  - typed `dma.view` 的字节区间越界，或与目标 dtype 字节宽度不匹配。

## 前后 IR 与摘要示例

### 示例 1：直线路径复用

输入 IR：

```text
func.func @pool_demo(%A: !symbol.int<"A">,
                     %B: !symbol.int<"B">) {
  %alloc1 = dma.alloc (%A, %B) : !nn.memory<[A, B], f32, #layout, #GM>
  kernel.use %alloc1
  dma.free %alloc1

  %alloc3 = dma.alloc (%A, %B) : !nn.memory<[A, B], f32, #layout, #GM>
  kernel.use %alloc3
  dma.free %alloc3
  func.return
}
```

预期摘要：

```text
func_name = pool_demo
bucket = (#GM)
intervals:
  - alloc1 | size_bytes=4*A*B | begin=0 | end=2 | offset_bytes=0
  - alloc3 | size_bytes=4*A*B | begin=3 | end=5 | offset_bytes=0
peak_bytes_by_bucket:
  - (#GM) -> 4*A*B
```

预期输出 IR：

```text
func.func @pool_demo(%A: !symbol.int<"A">,
                     %B: !symbol.int<"B">) {
  %pool = dma.alloc (%four_A_mul_B) : !nn.memory<[4*A*B], i8, #layout, #GM>

  %alloc1 = dma.view %pool[offset=0, size=(%A, %B), dtype=f32] -> !nn.memory<[A, B], f32, #layout, #GM>
  kernel.use %alloc1

  %alloc3 = dma.view %pool[offset=0, size=(%A, %B), dtype=f32] -> !nn.memory<[A, B], f32, #layout, #GM>
  kernel.use %alloc3
  dma.free %pool
  func.return
}
```

说明：

- `alloc1` 与 `alloc3` 生命周期不重叠，因此 byte offset 相同。
- after IR 不再保留原始两次 `dma.alloc / dma.free`。

### 示例 2：`symbol.for` 内外重叠

输入 IR：

```text
func.func @pool_loop(%A: !symbol.int<"A">,
                     %B: !symbol.int<"B">,
                     %lb: !symbol.int<"0">,
                     %ub: !symbol.int<"N">,
                     %step: !symbol.int<"TILE">) {
  %alloc1 = dma.alloc (%A, %B) : !nn.memory<[A, B], f32, #layout, #GM>
  kernel.use %alloc1

  symbol.for %i = %lb to %ub step %step : !symbol.int<"0">, !symbol.int<"N">, !symbol.int<"TILE"> {
    %alloc2 = dma.alloc (%A, %B) : !nn.memory<[A, B], f32, #layout, #GM>
    kernel.use %alloc2
    dma.free %alloc2
  }

  %alloc3 = dma.alloc (%A, %B) : !nn.memory<[A, B], f32, #layout, #GM>
  kernel.use %alloc3
  dma.free %alloc1
  dma.free %alloc3
  func.return
}
```

预期摘要：

```text
func_name = pool_loop
bucket = (#GM)
intervals:
  - alloc1 | size_bytes=4*A*B | begin=0 | end=7 | offset_bytes=0
  - alloc2 | size_bytes=4*A*B | begin=2 | end=5 | offset_bytes=4*A*B
  - alloc3 | size_bytes=4*A*B | begin=6 | end=8 | offset_bytes=4*A*B
peak_bytes_by_bucket:
  - (#GM) -> 8*A*B
```

预期输出 IR：

```text
func.func @pool_loop(...) {
  %pool = dma.alloc (%eight_A_mul_B) : !nn.memory<[8*A*B], i8, #layout, #GM>

  %alloc1 = dma.view %pool[offset=0, size=(%A, %B), dtype=f32] -> !nn.memory<[A, B], f32, #layout, #GM>
  kernel.use %alloc1

  symbol.for %i = %lb to %ub step %step : ... {
    %alloc2 = dma.view %pool[offset=%A*%B, size=(%A, %B), dtype=f32] -> !nn.memory<[A, B], f32, #layout, #GM>
    kernel.use %alloc2
  }

  %alloc3 = dma.view %pool[offset=%A*%B, size=(%A, %B), dtype=f32] -> !nn.memory<[A, B], f32, #layout, #GM>
  kernel.use %alloc3
  dma.free %pool
  func.return
}
```

说明：

- `alloc1` 在 loop 外仍然活着，因此 `alloc2` 不能复用 offset `0`。
- `alloc2` 与 `alloc3` 生命周期不重叠，因此两者共享同一段 byte offset；对 `f32` view 来说，该 offset 可写成 `A*B` 个 `f32` 元素。

### 示例 3：拒绝路径（escaping alloc）

输入 IR：

```text
func.func @pool_escape(%A: !symbol.int<"A">,
                       %B: !symbol.int<"B">) -> !nn.memory<[A, B], f32, #layout, #GM> {
  %alloc = dma.alloc (%A, %B) : !nn.memory<[A, B], f32, #layout, #GM>
  func.return %alloc : !nn.memory<[A, B], f32, #layout, #GM>
}
```

预期输出：

```text
MemoryPoolEscapingAlloc: function pool_escape returns pooled candidate alloc
```

### 示例 4：拒绝路径（非线性 / custom stride alloc）

输入 IR：

```text
func.func @pool_strided(%A: !symbol.int<"A">,
                        %B: !symbol.int<"B">) {
  %alloc = dma.alloc (%A, %B) : !nn.memory<[A, B], f32, #layout.custom_stride, #GM>
  kernel.use %alloc
  dma.free %alloc
  func.return
}
```

预期输出：

```text
MemoryPoolUnsupportedNonLinearAlloc: function pool_strided requires custom-stride interpretation outside byte-pool v1
```

## 计划任务

### `S1`

- `任务类型`：`收口任务（规格+实现+测试）`
- `任务目标`：
  - 新增 `spec/pass/lowering/memory_pool.md`
  - 新增 `kernel_gen/passes/lowering/memory_pool.py`
  - 新增 `test/pass/test_memory_pool.py`
  - 新增 `expectation/pass/lowing/memory_pool/summary.py`
  - 新增/对齐 `spec/dialect/dma.md`、`kernel_gen/dialect/dma.py`、`test/dialect/test_dma_dialect.py` 中 byte pool typed `dma.view` 合同
  - 建立 `MemoryPoolSummary` 与 `MemoryPoolInterval` 的统一摘要结构
- `重点内容`：
  - 明确 bucket 规则
  - 明确按字节数统计的生命周期索引与 size/offset 规则
  - 明确 `dma.view` 从 `i8` pool 到 typed memory 的公开合同
  - 完成 summary 查询接口
  - 先不改写 IR，只确保分析结果稳定可测
- `不采用的做法`：
  - 不输出临时的 ad-hoc dict/string 作为最终摘要接口
  - 不把 `symbol.for` 直接按 trip count 展开成 N 份区间
- `示例代码`：

```python
from kernel_gen.passes.lowering.memory_pool import MemoryPoolPass

pass_obj = MemoryPoolPass(rewrite=False)
module = pass_obj.run(module)
summary = pass_obj.get_summary("pool_loop")
```

- `预期输出`：

```text
summary.func_name == "pool_loop"
summary.intervals 包含 alloc1 / alloc2 / alloc3
summary.peak_bytes_by_bucket[(GM)] == 8*A*B
```

- `必须测试通过项目`：
  - `pytest -q test/pass/test_memory_pool.py -k "summary or interval or peak"`

### `S2`

- `任务类型`：`收口任务（规格+实现+测试）`
- `任务目标`：
  - 在 `S1` 摘要基础上完成直线路径 IR 重写
  - 将同 bucket、非重叠生命周期的 `dma.alloc` 改写为 `i8` byte pool + typed `dma.view`
  - 去掉被 pool 接管的原始 `dma.alloc / dma.free`
- `重点内容`：
  - 同 space、一维 `i8` pool 生成
  - byte offset 分配
  - pool free 安全插入
  - before/after IR expectation
- `不采用的做法`：
  - 不把原始 alloc 仍保留为按 dtype 分 bucket
  - 不在第一版支持跨 `space` 复用
- `示例代码`：

```python
from kernel_gen.passes.lowering.memory_pool import MemoryPoolPass

module = MemoryPoolPass(rewrite=True).run(module)
```

- `预期输出`：

```text
before: 两个同 bucket 的 dma.alloc / dma.free
after:  一个 i8 pool dma.alloc
after:  两个 typed dma.view
after:  原始独立 dma.alloc / dma.free 消失
```

- `必须测试通过项目`：
  - `pytest -q test/pass/test_memory_pool.py -k "rewrite and straight_line"`
  - `PYTHONPATH=. python expectation/pass/lowing/memory_pool/summary.py`

### `S3`

- `任务类型`：`收口任务（规格+实现+测试）`
- `任务目标`：
  - 把 `symbol.for` 词法生命周期加入可重写范围
  - 补齐 escaping / unsupported non-linear alloc / invalid lifetime / unsupported region 的拒绝路径
  - 明确 loop-local alloc 与 loop 外 alloc 的 offset 竞争规则
- `重点内容`：
  - `symbol.for` region 进入/退出索引
  - loop-local pool reuse
  - 明确错误短语
- `不采用的做法`：
  - 不把未知 region/control-flow 一律当可重写
  - 不因为“看起来没冲突”就静默跳过 escaping alloc
- `示例代码`：

```python
pass_obj = MemoryPoolPass(rewrite=True)
module = pass_obj.run(module)
summary = pass_obj.get_summary("pool_loop")
```

- `预期输出`：

```text
alloc1.offset_bytes == 0
alloc2.offset_bytes == 4*A*B
alloc3.offset_bytes == 4*A*B
escaping alloc -> MemoryPoolEscapingAlloc
custom-stride alloc -> MemoryPoolUnsupportedNonLinearAlloc
```

- `必须测试通过项目`：
  - `pytest -q test/pass/test_memory_pool.py -k "symbol_for or escape or layout or invalid_lifetime"`
  - `PYTHONPATH=. python expectation/pass/lowing/memory_pool/loop_reuse.py`

### `S4`

- `任务类型`：`收口任务（规格+实现+测试）`
- `任务目标`：
  - 对齐 pass 顺序说明、expectation、文档与最终回归测试
  - 补一个目录级 expectation，打印 before IR / summary / after IR
  - 确认和 `SymbolLoopHoistPass`、`LowerDmaMemoryHierarchyPass` 的顺序说明一致
- `重点内容`：
  - pass manager 顺序说明
  - 目录级 expectation 入口
  - 完整验证命令
- `不采用的做法`：
  - 不只改 spec，不补 expectation
  - 不只改 expectation，不补 pytest
- `示例代码`：

```python
from kernel_gen.passes.pass_manager import PassManager
from kernel_gen.passes.lowering.memory_pool import MemoryPoolPass
from kernel_gen.passes.lowering.tile import TilePass
from kernel_gen.passes.lowering.symbol_loop_hoist import SymbolLoopHoistPass
from kernel_gen.passes.lowering.dma_memory_hierarchy import LowerDmaMemoryHierarchyPass

pm = PassManager(name="lowering")
pm.add_pass(TilePass())
pm.add_pass(SymbolLoopHoistPass())
pm.add_pass(MemoryPoolPass())
pm.add_pass(LowerDmaMemoryHierarchyPass())
module = pm.run(module)
```

- `预期输出`：

```text
目录级 expectation 运行后能看到 before IR / summary / after IR
pytest 与 expectation 都通过
顺序说明与实际公开入口一致
```

- `必须测试通过项目`：
  - `pytest -q test/pass/test_memory_pool.py`
  - `pytest -q test/pass/test_pass_manager.py -k "memory_pool or symbol_loop_hoist or dma_memory_hierarchy"`
  - `PYTHONPATH=. python expectation/pass/lowing/memory_pool/__main__.py`

## 最终验收摘要（2026-04-09）

- `验收结论`：通过
- `评审人`：`大闸蟹`、`守护最好的爱莉希雅`
- `结论摘要`：
  - `进度`：`S1~S4` 均已合并收口，当前计划链路完整。
  - `证据`：`agents/codex-multi-agents/log/task_records/2026/15/20260407-memory-pool-s1.md`、`agents/codex-multi-agents/log/task_records/2026/15/20260408-memory-pool-s3.md`、`agents/codex-multi-agents/log/task_records/2026/15/20260408-memory-pool-s4.md` 的实现、审查、复核记录均已通过。
  - `复核`：当前主仓执行 `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/pass/test_memory_pool.py`，结果为 `17 passed`，与计划目标一致。
  - `阻断项`：无。

## 历史评审摘要

- 评审结论：`已评审通过`
- 评审人：`大闸蟹`、`守护最好的爱莉希雅`
- 评审时间：`2026-04-07`
- 六项摘要：
  - `目标`：通过；`memory-pool / MemoryPoolPass` 的分析与重写范围明确，和 `analysis .plan.md` 的目标一致。
  - `边界`：本摘要基于旧版“按 dtype 分 bucket”草案；本次已改为 `i8` byte pool + typed `dma.view` 口径，交付管理员前需按新版合同重新互评。
  - `依赖顺序`：通过；`LowerNnToKernelPass -> BufferResultsToOutParamsPass -> TilePass -> SymbolLoopHoistPass -> MemoryPoolPass -> LowerDmaMemoryHierarchyPass` 自洽。
  - `验证命令`：通过；`S1~S4` 的 `pytest` 与 `expectation` 入口完整，目录级入口也已定义。
  - `失败短语`：需按新版合同更新为 `MemoryPoolEscapingAlloc / MemoryPoolUnsupportedNonLinearAlloc / MemoryPoolUnsupportedRegionEscape / MemoryPoolInvalidLifetime / MemoryPoolUnsupportedPoolBucket / MemoryPoolTypedViewOutOfBounds`。
  - `不可改文件`：通过；沿用仓库默认 `immutable` 规则，无额外豁免。

## 文档信息

- 创建者：`大闸蟹`
- 最后修改人：`大闸蟹`
- 需求来源：[`analysis .plan.md`](../../analysis%20.plan.md)
- 计划书：[`ARCHITECTURE/plan/memory_pool_pass_green_plan.md`](../../ARCHITECTURE/plan/memory_pool_pass_green_plan.md)
- 预期 `spec`：[`spec/pass/lowering/memory_pool.md`](../../spec/pass/lowering/memory_pool.md)
- 预期 `test`：[`test/pass/test_memory_pool.py`](../../test/pass/test_memory_pool.py)
- 预期 `功能实现`：[`kernel_gen/passes/lowering/memory_pool.py`](../../kernel_gen/passes/lowering/memory_pool.py)
