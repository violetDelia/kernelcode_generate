# analysis_engine_refactor_green_plan.md

## 进度

| 编号 | 依赖 | worktree | 记录文件 | 进度 |
| --- | --- | --- | --- | --- |
| `S1` | `无` | `.` | `20260404-analysis-engine-refactor-s1.md` | `实现完成（T-20260404-44d4afcf，金铲铲大作战）；复审完成（需修改，T-20260404-b67dba97，提莫炖蘑菇）；修复完成（T-20260404-80b85158，金铲铲大作战）；复审通过（T-20260404-25e76f7a，提莫炖蘑菇）；已合并（commit a12265b，T-20260404-a8be0498，李白）。` |
| `S2` | `S1` | `wt-20260404-analysis-engine-refactor-s2` | `20260404-analysis-engine-refactor-s2.md` | `实现完成（T-20260404-07caa57b，朽木露琪亚）；复审通过（T-20260404-75397a22，提莫炖蘑菇）；已合并（commit d58bc19，T-20260404-e3a776b3，李白）。` |
| `S3` | `S1、S2` | `wt-20260405-analysis-engine-refactor-s3` | `20260405-analysis-engine-refactor-s3.md` | `实现完成（T-20260405-e3ff6a4b，朽木露琪亚）；复审通过（T-20260405-20803047，提莫炖蘑菇）；已合并（commit aa7055e，T-20260405-70830a39，李白）。` |
| `S4` | `S3` | `wt-20260405-analysis-engine-refactor-s4` | `20260405-analysis-engine-refactor-s4.md` | `实现+补测完成（T-20260405-b12c6530，金铲铲大作战；pytest gate exit=0，84 passed）；复审不通过（T-20260405-5653dd9a，提莫炖蘑菇：发现未追踪文件合并风险）；修复完成（T-20260405-bd8250cd，jcc你莫辜负；gate exit=0，84 passed）；复审通过（T-20260405-15344c9c，提莫炖蘑菇）；已合并（commit b530c6d，T-20260405-ab62bd23，李白；gate exit=0）。` |
| `S5` | `S4` | `wt-20260405-analysis-engine-refactor-s5` | `20260405-analysis-engine-refactor-s5.md` | `实现完成（T-20260405-a11cfab8，金铲铲大作战；gate exit=0）；复审通过（T-20260405-e71a9ff7，不要啊教练；gate exit=0）；已合并（commit e69d456，T-20260405-48bb68d6，李白；gate exit=0）。` |
| `S6` | `S5` |  |  | `未开始` |
| `S7` | `S6` |  |  | `未开始` |

## 功能说明

- 本计划用于指导 `kernel_gen/analysis/**` 的重构与补齐，不直接依赖当前实现是否“刚好能跑”。
- 目标是按 `analysis(op, config, otherargs=None)` 单一主入口，完成 `analysis .plan.md` 要求的目录拆分、装饰器分发、计算量/访存统一口径，并把当前仓库内已公开 op 纳入“有分析结果或显式零成本/忽略”的稳定合同。
- 本计划只定义任务拆解、目标公式、代码示例、验收口径与当前实现状态；本文件不是实现提交。
- 本计划优先保证 `analysis` 主线、`analyze_kernel(...)` facade、`AnalyzeFuncCostPass` 三者口径一致；不允许维护第二套独立公式主线。

## 范围与非目标

### 范围

- `kernel_gen/analysis/**`
- 直接消费方：
  - `kernel_gen/passes/analysis/func_cost.py`
  - `kernel_gen/target/registry.py` 中 analysis 默认参数读取
- 当前需要纳入覆盖的 op 家族：
  - `kernel.*`
  - `nn.*`
  - `dma.*`
  - `symbol.*`
  - `arch.*`
  - `tuner.param`
  - `arith.constant` / `func.return` / `scf.for` / `scf.yield` / `symbol.for` 等控制或元信息 op
- 相关规格与测试：
  - `spec/analysis/**`
  - `spec/dialect/{kernel,nn,dma,symbol,arch}.md`
  - `test/analysis/**`
  - `test/pass/test_analysis_func_cost.py`

### 非目标

- 不在本轮引入硬件级缓存命中、双缓冲、流水重叠、bank conflict 等微架构级建模。
- 不在本轮把 `theoretical_compute` 扩展成正式 `compute_time_ns` 结果字段；当前只要求配置收口与后续扩展点保留。
- 不改 `emit_c` / `gen_kernel` / codegen 合同。
- 不把 `fc`、`conv` 这类高层 helper 再定义成 analysis 主线独立 op；它们应通过 lower 后的 `nn.img2col*` / `nn.matmul` / `dma.*` 链路反映成本。

## 文档信息

- 创建者：`大闸蟹`
- 最后一次更改：`大闸蟹`
- `文档`：[`ARCHITECTURE/plan/analysis_engine_refactor_green_plan.md`](/home/lfr/kernelcode_generate/ARCHITECTURE/plan/analysis_engine_refactor_green_plan.md)
- `spec`：
  - [`analysis .plan.md`](/home/lfr/kernelcode_generate/analysis%20.plan.md)
  - [`spec/analysis/analysis_engine.md`](/home/lfr/kernelcode_generate/spec/analysis/analysis_engine.md)
  - [`spec/analysis/analysis_kernel.md`](/home/lfr/kernelcode_generate/spec/analysis/analysis_kernel.md)
  - [`spec/dialect/kernel.md`](/home/lfr/kernelcode_generate/spec/dialect/kernel.md)
  - [`spec/dialect/nn.md`](/home/lfr/kernelcode_generate/spec/dialect/nn.md)
  - [`spec/dialect/dma.md`](/home/lfr/kernelcode_generate/spec/dialect/dma.md)
  - [`spec/dialect/symbol.md`](/home/lfr/kernelcode_generate/spec/dialect/symbol.md)
  - [`spec/dialect/arch.md`](/home/lfr/kernelcode_generate/spec/dialect/arch.md)
  - [`spec/pass/analysis/func_cost.md`](/home/lfr/kernelcode_generate/spec/pass/analysis/func_cost.md)
- `功能实现`：
  - [`kernel_gen/analysis/analysis.py`](/home/lfr/kernelcode_generate/kernel_gen/analysis/analysis.py)
  - [`kernel_gen/analysis/compute/__init__.py`](/home/lfr/kernelcode_generate/kernel_gen/analysis/compute/__init__.py)
  - [`kernel_gen/analysis/compute/kernel.py`](/home/lfr/kernelcode_generate/kernel_gen/analysis/compute/kernel.py)
  - [`kernel_gen/analysis/compute/nn.py`](/home/lfr/kernelcode_generate/kernel_gen/analysis/compute/nn.py)
  - [`kernel_gen/analysis/memory/__init__.py`](/home/lfr/kernelcode_generate/kernel_gen/analysis/memory/__init__.py)
  - [`kernel_gen/analysis/memory/dma.py`](/home/lfr/kernelcode_generate/kernel_gen/analysis/memory/dma.py)
  - [`kernel_gen/passes/analysis/func_cost.py`](/home/lfr/kernelcode_generate/kernel_gen/passes/analysis/func_cost.py)
  - [`kernel_gen/target/registry.py`](/home/lfr/kernelcode_generate/kernel_gen/target/registry.py)
- `test`：
  - [`test/analysis/test_analysis.py`](/home/lfr/kernelcode_generate/test/analysis/test_analysis.py)
  - [`test/pass/test_analysis_func_cost.py`](/home/lfr/kernelcode_generate/test/pass/test_analysis_func_cost.py)
  - [`test/pass/test_pass_manager.py`](/home/lfr/kernelcode_generate/test/pass/test_pass_manager.py)
  - [`test/dialect/test_nn_dialect.py`](/home/lfr/kernelcode_generate/test/dialect/test_nn_dialect.py)
  - [`test/dialect/test_dma_dialect.py`](/home/lfr/kernelcode_generate/test/dialect/test_dma_dialect.py)
  - [`test/dialect/test_symbol_dialect.py`](/home/lfr/kernelcode_generate/test/dialect/test_symbol_dialect.py)
  - [`test/dialect/test_arch_dialect.py`](/home/lfr/kernelcode_generate/test/dialect/test_arch_dialect.py)

## 当前实测状态

### 基线命令

```bash
pytest -q test/analysis/test_analysis.py test/pass/test_analysis_func_cost.py test/pass/test_pass_manager.py
```

### 当前结果

- `70 passed in 0.71s`
- 当前 analysis 相关测试是绿的，但它们只覆盖现有已承接子集，不代表“analysis 按计划重构完成”。

### 当前实现状态判断

| 区域 | 当前状态 | 真实缺口 |
| --- | --- | --- |
| `analysis.py` | 已有统一入口、结果结构与 target 默认参数读取 | 仍承担分发、旧 helper、聚合、兼容 facade、多种公式，职责过重 |
| `compute/` | 只有 `kernel.py` 与 `nn.py` | 没有装饰器注册器；`nn.py` 混入访存逻辑；缺 `symbol`/`dma.cast` 等 compute 子模块 |
| `memory/` | 只有 `dma.py` | 缺 `nn` 访存分析；`dma` 只覆盖 `copy/load/store/slice` 四类 |
| `MemoryPath` | 已有正式枚举 | 缺 `SM/TSM/TLM <-> compute` 路径与若干同空间 direct path，导致合法 op 只能落到 `UNKNOWN` |
| `kernel.*` | 只覆盖 `add/sub/mul/div/eq/ne/lt/le/gt/ge` 的标量子集 | `kernel.select`、`kernel.cast` 未纳入 |
| `nn.*` | 只覆盖逐元素 binary/compare 与 `matmul` | `broadcast`、`transpose`、`exp`、`reduce_*`、`softmax`、`img2col1d/2d` 未纳入 |
| `dma.*` | 只覆盖四类公开 DMA path | `alloc/fill/free/deslice/view/reshape/cast` 未纳入；`cast` 同时缺 compute+memory |
| `symbol.*` / `arch.*` / `tuner.param` | 基本未纳入 | 现在只能 warning/skip，无法满足“当前所有 op 全覆盖”的计划要求 |
| region/control | 仅递归遍历 block | `symbol.for` / `scf.for` 体内成本不会乘 trip count |

### 当前结构性问题

- `kernel_gen/analysis/compute/nn.py` 现在直接构造 `MemoryItem`，实际混合了 compute 与 memory 两层职责。
- `kernel_gen/analysis/analysis.py` 仍保留大量 `analyze_add/analyze_broadcast/analyze_matmul/analyze_function/analyze_kernel` 兼容公式，未来极易与新主线发生重复维护。
- `MemoryPath` 当前对 `shared/tsm/tlm` 到 compute 的读取、以及从 compute 回写到这些空间的路径表达不完整，会把合法 `nn.*` op 的结果归到 `UNKNOWN`。
- `symbol.for` / `scf.for` 的 region 当前只被“展开遍历一次”，不是“按 trip count 放大体内成本”。

## 目标目录结构

```text
kernel_gen/analysis/
├── analysis.py
├── compute/
│   ├── __init__.py
│   ├── kernel.py
│   ├── nn.py
│   ├── dma.py
│   └── symbol.py
└── memory/
    ├── __init__.py
    ├── nn.py
    └── dma.py
```

### 目录职责

- `analysis.py`
  - 只做统一入口、配置归一、registry 分发、region 聚合、兼容 facade 适配。
  - 不再承载大段按 op 逐个写死的公式实现。
- `compute/*.py`
  - 只返回 `ComputeItem` 与必要的聚合辅助信息。
  - 不直接创建 `MemoryItem`。
- `memory/*.py`
  - 只返回 `MemoryItem` 与必要的流量辅助信息。
  - 不承担 `ComputeKind` 分类。
- `analyze_kernel(...)` / `AnalyzeFuncCostPass`
  - 只消费 `analysis(...)` 结果。
  - 不再保留第二套独立公式分支。

## 统一口径

### 分发模型

- `compute/__init__.py` 提供装饰器注册：
  - `@register_compute("nn.add")`
  - `@register_compute(("symbol.add", "symbol.sub"))`
- `memory/__init__.py` 提供装饰器注册：
  - `@register_memory("dma.copy")`
  - `@register_memory(("nn.broadcast", "nn.transpose"))`
- `analysis.py` 只做：
  - 查找 compute analyzer
  - 查找 memory analyzer
  - 合并 `AnalysisResult`
  - 对 `func.func` / loop region 做乘法聚合

### 零成本与忽略

- 明确零成本、不再 warning 的 op：
  - `arith.constant`
  - `func.return`
  - `scf.yield`
  - `tuner.param`
  - `arch.get_*`
  - `arch.get_dynamic_memory`
  - `arch.launch_kernel`
  - `symbol.get_dim`
  - `symbol.get_stride`
- 这些 op 应返回空 `compute_items` 与空 `memory_items`，而不是塞入 `0-byte item`。

### loop 聚合

- `symbol.for` / `scf.for` 不直接产生自身 compute/memory 成本。
- 函数级分析时，body 内所有成本统一乘以 trip count。
- 推荐 trip count 公式：

```python
trip_count = Max(0, ceiling((end - start) / step))
```

- 若 `step == 0`，必须显式失败。
- 若 `step` 不能证明为正且无法安全化简，不允许静默当作 `1`；应保留符号表达式，必要时显式报 unsupported。

### MemoryPath 规则

- `MemoryPath` 继续使用枚举，不回退到自由字符串。
- 本轮至少补齐：
  - `SM->compute`
  - `TSM->compute`
  - `TLM->compute`
  - `compute->SM`
  - `compute->TSM`
  - `compute->TLM`
  - `SM->SM`
  - `LM->LM`
  - `TSM->TSM`
  - `TLM->TLM`
- 对 target 默认参数未给出的 path：
  - `bytes` 仍然必须统计
  - `latency_ns/bandwidth/time_ns` 允许为 `None`
  - 不允许因为缺时间参数就丢掉整条 memory item

### 兼容 facade

- `analyze_kernel(...)`
  - 继续存在，但只能是 `analysis(func_op, config, otherargs)` 的 adapter。
- `analyze_function(...)` / `analyze_add(...)` / `analyze_broadcast(...)` / `analyze_matmul(...)`
  - 只保留兼容层。
  - 公式来源必须委托到新的 per-op analyzer 或公共 helper。

## 目标公式矩阵

### `kernel` / `symbol` / `arch` / meta

| op 家族 | 计算分类 | 计算量 | 访存 |
| --- | --- | --- | --- |
| `kernel.add/sub/mul/div/eq/ne/lt/le/gt/ge` | `SCALAR` | `1` | `0` |
| `kernel.select` | `SCALAR` | `1` | `0` |
| `kernel.cast` | `SCALAR` | `1` | `0` |
| `symbol.add/sub/mul/div/floordiv/eq/ne/lt/le/gt/ge` | `SCALAR` | `1` | `0` |
| `symbol.to_int/to_float` | `0` | `0` | `1`（按 symbol scalar 单位记） |
| `symbol.get_dim/get_stride` | `0` | `0` | `0` |
| `arch.get_block_id/get_thread_id/...` | `0` | `0` | `0` |
| `arch.get_dynamic_memory` | `0` | `0` | `0` |
| `arch.launch_kernel` | `0` | `0` | `0` |
| `tuner.param` | `0` | `0` | `0` |

### `nn`

| op 家族 | 计算分类 | 计算量 | 访存 |
| --- | --- | --- | --- |
| `nn.add/sub/mul/truediv` | `VECTOR` | `numel(result)` | 读各 memory operand，写 result |
| `nn.eq/ne/lt/le/gt/ge` | `VECTOR` | `numel(result)` | 写回使用 `predicate_size` |
| `nn.exp` | `MATH` | `numel(result)` | 读 input，写 result |
| `nn.reduce_sum/min/max` | `VECTOR` | `numel(input) - numel(result)` | 读 input，写 result |
| `nn.softmax` | `VECTOR + MATH` | `VECTOR = 4*N - 2*G`，`MATH = N`；其中 `N=numel(input)`、`G=沿 axis 归约后的 group 数` | 读 input，写 result，不计中间 buffer |
| `nn.matmul` | `TENSOR` | `2*M*N*K` | 读 lhs/rhs，写 result |
| `nn.broadcast` | `0` | `0` | direct path：读 `numel(input)`，写 `numel(result)` |
| `nn.transpose` | `0` | `0` | direct path：读 `numel(result)`，写 `numel(result)` |
| `nn.img2col1d/2d` | `0` | `0` | direct path：读 `numel(result)`，写 `numel(result)` |

### `dma`

| op 家族 | 计算分类 | 计算量 | 访存 |
| --- | --- | --- | --- |
| `dma.alloc` | `0` | `0` | `0` |
| `dma.free` | `0` | `0` | `0` |
| `dma.fill` | `0` | `0` | 写 target；标量 operand 不算 memory item |
| `dma.copy` | `0` | `0` | direct path：读/写 `numel * elem_size` |
| `dma.load` | `0` | `0` | direct path：读/写 slice bytes |
| `dma.store` | `0` | `0` | direct path：读/写 slice bytes |
| `dma.slice` | `0` | `0` | direct path：读/写 slice bytes |
| `dma.deslice` | `0` | `0` | direct path：读/写 slice bytes |
| `dma.view` | `0` | `0` | `0`，metadata-only |
| `dma.reshape` | `0` | `0` | `0`，metadata-only |
| `dma.cast` | `VECTOR` | `numel(result)` | 读 `src_numel * src_elem_size`，写 `dst_numel * dst_elem_size` |

## 计划任务

### `S1`

- `任务类型`：`重构任务`
- `目标`：建立装饰器注册与统一 orchestrator，清理 `analysis.py` 的硬编码分发。
- `边界`：
  - 不改 `analysis(op, config, otherargs=None)` 主入口签名。
  - 不在本任务里补公式，只完成“公式实现可迁移”的骨架。
- `注意事项`：
  - `compute` 与 `memory` analyzer 必须独立注册。
  - 允许一个 op 同时命中 compute 与 memory analyzer。
  - 兼容 facade 仍通过 `analysis(...)`。
- `代码示例`：

```python
@register_compute(("nn.add", "nn.sub", "nn.mul", "nn.truediv"))
def analyze_nn_elementwise_compute(op, config):
    ...


@register_memory(("nn.add", "nn.sub", "nn.mul", "nn.truediv"))
def analyze_nn_elementwise_memory(op, config):
    ...
```

```python
config = AnalysisConfig(enable_compute=True, enable_memory=True, target="npu_demo")
result = analysis(op, config)
```

- `可改文件`：
  - [`kernel_gen/analysis/analysis.py`](/home/lfr/kernelcode_generate/kernel_gen/analysis/analysis.py)
  - [`kernel_gen/analysis/compute/__init__.py`](/home/lfr/kernelcode_generate/kernel_gen/analysis/compute/__init__.py)
  - [`kernel_gen/analysis/memory/__init__.py`](/home/lfr/kernelcode_generate/kernel_gen/analysis/memory/__init__.py)
- `验收标准`：
  - `analysis.py` 不再维护 tuple 顺序写死的 `_analyze_ir_op(...)` 分发列表。
  - `compute`/`memory` 分发可独立注册与查询。
  - 未命中的 op 仍保留 `skip + warning`，但只允许用于“未纳入本轮合同的 op”。

### `S2`

- `任务类型`：`重构任务`
- `目标`：补齐 loop / region 乘法聚合与显式零成本元信息 op 口径。
- `边界`：
  - `symbol.for` / `scf.for` 自身不计成本，只放大 body。
  - `arith.constant` / `func.return` / `scf.yield` 不得再 warning。
- `注意事项`：
  - trip count 必须保留符号表达式，不允许默认当 `1`。
  - `step == 0` 必须报错。
- `代码示例`：

```mlir
symbol.for %i = %start to %end step %step : !symbol.int<"0">, !symbol.int<"N">, !symbol.int<"1"> {
  %0 = kernel.add %a, %b : i32
}
```

```python
# 目标合同
trip_count = Max(0, ceiling((N - 0) / 1))
total_scalar = trip_count
```

- `可改文件`：
  - [`kernel_gen/analysis/analysis.py`](/home/lfr/kernelcode_generate/kernel_gen/analysis/analysis.py)
  - [`test/analysis/test_analysis.py`](/home/lfr/kernelcode_generate/test/analysis/test_analysis.py)
- `验收标准`：
  - `symbol.for` / `scf.for` 体内 compute/memory 会被 trip count 放大。
  - `arith.constant` / `func.return` / `scf.yield` 不再产生 warning。
  - `arch.get_*` / `arch.get_dynamic_memory` / `tuner.param` 显式零成本，不再走 unsupported。

### `S3`

- `任务类型`：`实现任务`
- `目标`：补齐 `kernel`、`symbol`、`arch`、`tuner` 家族的 compute/memory/zero-cost 覆盖。
- `边界`：
  - `kernel.*` 本轮只收口已公开 scalar 子集，不强行扩展 vector/tensor kernel 类型。
  - `symbol.get_dim/get_stride`、`arch.get_*`、`tuner.param` 不计入 compute。
- `注意事项`：
  - `kernel.select`、`kernel.cast` 需要纳入。
  - `symbol.to_int/to_float` 视为 symbol 标量访问，访存记 `1`，不计 compute。
- `代码示例`：

```mlir
%0 = kernel.cast %arg0 : i32 to f32
%1 = kernel.select %pred, %lhs, %rhs : i1, i32
```

```python
# 目标合同
analysis(kernel_cast_op, cfg).compute_totals_by_kind[ComputeKind.SCALAR] == 1
analysis(kernel_select_op, cfg).total_read_bytes == 0
```

- `可改文件`：
  - [`kernel_gen/analysis/compute/kernel.py`](/home/lfr/kernelcode_generate/kernel_gen/analysis/compute/kernel.py)
  - [`kernel_gen/analysis/compute/symbol.py`](/home/lfr/kernelcode_generate/kernel_gen/analysis/compute/symbol.py)
  - [`kernel_gen/analysis/analysis.py`](/home/lfr/kernelcode_generate/kernel_gen/analysis/analysis.py)
  - [`test/analysis/test_analysis.py`](/home/lfr/kernelcode_generate/test/analysis/test_analysis.py)
- `验收标准`：
  - `kernel.select`、`kernel.cast` 会返回 `SCALAR=1`。
  - `symbol.add/sub/...` 会返回 `SCALAR=1`。
  - `symbol.to_int/to_float` 不返回 compute item，访存记 `1`（按 symbol scalar 单位）。
  - `symbol.get_dim/get_stride`、`arch.*`、`tuner.param` 显式零成本、无 warning。

### `S4`

- `任务类型`：`实现任务`
- `目标`：补齐 `nn` 的 elementwise / unary / reduce / broadcast / transpose 分析，并把 `nn` 的访存实现迁入 `memory/nn.py`。
- `边界`：
  - `nn.broadcast` / `nn.transpose` 视为 direct memory/layout op，不记 compute。
  - `nn.reduce_*` 不统计中间 buffer，只统计输入读与结果写。
- `注意事项`：
  - `compare` 写回必须统一用 `predicate_size`。
  - `broadcast` 读字节口径固定为 `numel(input) * dtype_size`，与旧兼容 helper 保持一致。
  - `transpose` 写入/读取应按 `numel(result)` 统计。
- `代码示例`：

```mlir
%0 = nn.exp %arg0 : !nn.memory<[M, N], [N, 1], f32, #nn.space<global>> -> !nn.memory<[M, N], [N, 1], f32, #nn.space<global>>
%1 = nn.reduce_sum %0 {axes = [1], keepdim = true, space = #nn.space<global>} : (!nn.memory<[M, N], [N, 1], f32, #nn.space<global>>) -> !nn.memory<[M, 1], [1, 1], f32, #nn.space<global>>
```

```python
# 目标合同
exp_compute = M * N
reduce_compute = M * N - M
reduce_read_bytes = M * N * 4
reduce_write_bytes = M * 4
```

- `可改文件`：
  - [`kernel_gen/analysis/compute/nn.py`](/home/lfr/kernelcode_generate/kernel_gen/analysis/compute/nn.py)
  - [`kernel_gen/analysis/memory/nn.py`](/home/lfr/kernelcode_generate/kernel_gen/analysis/memory/nn.py)
  - [`kernel_gen/analysis/memory/__init__.py`](/home/lfr/kernelcode_generate/kernel_gen/analysis/memory/__init__.py)
  - [`test/analysis/test_analysis.py`](/home/lfr/kernelcode_generate/test/analysis/test_analysis.py)
- `验收标准`：
  - `nn.exp` 产出 `MATH=numel(result)`。
  - `nn.reduce_sum/min/max` 产出 `VECTOR=numel(input)-numel(result)`。
  - `nn.broadcast` / `nn.transpose` 不产出 compute item，但会产出 direct-path memory item。
  - `shared/local/tsm/tlm` 空间的 `nn.*` 结果不再全部落到 `MemoryPath.UNKNOWN`。

### `S5`

- `任务类型`：`实现任务`
- `目标`：补齐 `nn.matmul`、`nn.img2col1d`、`nn.img2col2d`、`nn.softmax` 的正式公式，并与当前结构化 shape 合同对齐。
- `边界`：
  - `matmul` 继续只支持二维收缩。
  - `img2col*` 不记 compute，只统计显式搬运。
  - `softmax` 不统计中间 buffer，只统计公开 op 级语义。
- `注意事项`：
  - `img2col1d/2d` 的输出 `numel(result)` 必须基于新结构化维度，而不是旧压扁形状。
  - `softmax` 需要同时返回 `VECTOR` 与 `MATH` 两类 compute item。
- `代码示例`：

```python
# img2col2d: NCHW -> [N, C, kh, kw, H_out, W_out]
write_bytes = N * C * kh * kw * H_out * W_out * dtype_size
read_bytes = write_bytes
```

```python
# softmax(axis=1)
N_total = numel(x)
G = product(non_axis_dims)
vector_compute = 4 * N_total - 2 * G
math_compute = N_total
```

- `可改文件`：
  - [`kernel_gen/analysis/compute/nn.py`](/home/lfr/kernelcode_generate/kernel_gen/analysis/compute/nn.py)
  - [`kernel_gen/analysis/memory/nn.py`](/home/lfr/kernelcode_generate/kernel_gen/analysis/memory/nn.py)
  - [`test/analysis/test_analysis.py`](/home/lfr/kernelcode_generate/test/analysis/test_analysis.py)
- `验收标准`：
  - `nn.matmul` 保持 `TENSOR = 2*M*N*K`，并与旧结果一致。
  - `nn.img2col1d/2d` 读写字节按结构化输出 `numel(result)` 统计。
  - `nn.softmax` 同时含 `ComputeKind.VECTOR` 与 `ComputeKind.MATH`，且 `total_compute` 等于两者和。

### `S6`

- `任务类型`：`实现任务`
- `目标`：把 `dma` 家族补齐为“全部公开 op 都有分析口径”，并把 `dma.cast` 拆成 compute+memory 双分析。
- `边界`：
  - `dma.alloc/free/view/reshape` 视为零成本元数据或生命周期 op，不产出 memory item。
  - `dma.fill` 只统计 target 写入；标量来源不记 memory item。
- `注意事项`：
  - `dma.view/reshape` 是 metadata-only，不允许误统计为整块 copy。
  - `dma.cast` 必须按源 dtype 与目标 dtype 分开统计读写字节。
  - `dma.deslice` 语义等价于切片回写，不能再走 unsupported。
- `代码示例`：

```mlir
%0 = dma.cast %arg0 : !nn.memory<[M, N], [N, 1], i32, #nn.space<global>> -> !nn.memory<[M, N], [N, 1], f32, #nn.space<global>>
```

```python
# 目标合同
compute = M * N
read_bytes = M * N * 4   # i32
write_bytes = M * N * 4  # f32
```

```python
# dma.reshape / dma.view
analysis(reshape_op, cfg).memory_items == ()
analysis(view_op, cfg).compute_items == ()
```

- `可改文件`：
  - [`kernel_gen/analysis/compute/dma.py`](/home/lfr/kernelcode_generate/kernel_gen/analysis/compute/dma.py)
  - [`kernel_gen/analysis/memory/dma.py`](/home/lfr/kernelcode_generate/kernel_gen/analysis/memory/dma.py)
  - [`kernel_gen/analysis/memory/__init__.py`](/home/lfr/kernelcode_generate/kernel_gen/analysis/memory/__init__.py)
  - [`test/analysis/test_analysis.py`](/home/lfr/kernelcode_generate/test/analysis/test_analysis.py)
- `验收标准`：
  - `dma.fill`、`dma.deslice`、`dma.view`、`dma.reshape`、`dma.cast` 全部不再走 unsupported。
  - `dma.view/reshape` 为零成本；`dma.cast` 为 `VECTOR=numel(result)`。
  - `dma.copy/load/store/slice/deslice` 继续保留 direct-path `bytes + latency + bandwidth -> time_ns` 口径。

### `S7`

- `任务类型`：`重构任务`
- `目标`：把兼容 facade 与 pass 消费口径收口到新主线，避免重复公式。
- `边界`：
  - `analyze_kernel(...)`、`AnalyzeFuncCostPass` 的对外接口不改。
  - 旧 `compute/read_bytes/write_bytes` 只能是 derived alias。
- `注意事项`：
  - `func_cost` 不得再次重建自己的 unsupported/warning 逻辑。
  - `AnalysisConfig` 继续从 `target registry` 取 `path_bandwidth/path_latency_ns/theoretical_compute` 默认值。
- `代码示例`：

```python
summary = analyze_kernel(func_op, dtype_size_overrides={"f32": 4})
pass_summary = AnalyzeFuncCostPass().get_summary("main")
# 目标合同：两者 total_compute / total_read_bytes / total_write_bytes 一致
```

- `可改文件`：
  - [`kernel_gen/analysis/analysis.py`](/home/lfr/kernelcode_generate/kernel_gen/analysis/analysis.py)
  - [`kernel_gen/passes/analysis/func_cost.py`](/home/lfr/kernelcode_generate/kernel_gen/passes/analysis/func_cost.py)
  - [`test/analysis/test_analysis.py`](/home/lfr/kernelcode_generate/test/analysis/test_analysis.py)
  - [`test/pass/test_analysis_func_cost.py`](/home/lfr/kernelcode_generate/test/pass/test_analysis_func_cost.py)
- `验收标准`：
  - `analysis(...)`、`analyze_kernel(...)`、`AnalyzeFuncCostPass` 三路总量一致。
  - `func_cost` 不再依赖“旧 helper 公式偶然一致”。
  - target 默认参数缺字段时仍显式失败。

## 建议测试拆分

- 保留 [`test/analysis/test_analysis.py`](/home/lfr/kernelcode_generate/test/analysis/test_analysis.py) 作为兼容总入口。
- 新增或拆分为以下文件更易维护：
  - `test/analysis/test_analysis_kernel_symbol_meta.py`
  - `test/analysis/test_analysis_nn.py`
  - `test/analysis/test_analysis_dma.py`
  - `test/analysis/test_analysis_loop_region.py`
  - `test/analysis/test_analysis_compat.py`

## 推荐验证命令

```bash
pytest -q test/analysis
pytest -q test/pass/test_analysis_func_cost.py test/pass/test_pass_manager.py
```

## 阶段验收门禁

### Gate-A：骨架完成

- `S1`、`S2` 完成
- registry 已接管 dispatch
- loop trip count 已纳入
- 零成本 op 不再 warning

### Gate-B：op 覆盖完成

- `S3`、`S4`、`S5`、`S6` 完成
- 当前公开 op 全部满足以下三选一之一：
  - 有正式 compute 分析
  - 有正式 memory 分析
  - 有显式零成本/忽略口径

### Gate-C：兼容与下游一致

- `S7` 完成
- `analysis(...)` / `analyze_kernel(...)` / `AnalyzeFuncCostPass` 三路一致
- 现有 analysis/pass 测试保持全绿

## 当前建议分发顺序

1. `S1`：先把 registry 与 orchestrator 收口，否则后续每补一个 op 都会继续把 `analysis.py` 塞大。
2. `S2`：随后补 loop/zero-cost 基线，否则“全 op 覆盖”会被 region/control op 反复打断。
3. `S3 + S4`：先补 scalar/meta 与常见 `nn` 主线，尽快形成大面积覆盖。
4. `S5 + S6`：处理 `softmax/img2col/dma.cast/view/reshape` 等高差异公式。
5. `S7`：最后收口 facade 与 pass。

## 备注

- 本计划默认实现时允许同步补充 `spec/analysis/analysis_engine.md`、`spec/analysis/analysis_kernel.md` 的公式口径，但前提是“先补主线合同，再改兼容描述”，不能反过来用兼容 helper 约束主线。
- 若实现期发现某些 direct path 必须新增 `MemoryPath` 枚举项，优先补枚举与 target metric 归一逻辑；不要退回自由字符串。
- 若实现期发现 `fc/conv` 高层 helper 需要单独分析接口，应另起新计划，不挤入本轮主线。
