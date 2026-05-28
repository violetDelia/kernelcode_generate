# Triton 调研与本仓可借鉴点

## 功能简介

- 调研外部参考项目 `triton-lang/triton` 的块程序模型、JIT 编译合同、matmul tail、autotune/config、stage dump 与 backend lowering 边界。
- 区分 Triton 的 GPU JIT/runtime 生态和本仓自有 DSL / IR / `npu_demo` 源码生成链路，避免把外部 GPU runtime 能力误写成本仓当前目标。
- 为后续讨论 effective tile view、dynamic acc matmul、tuner config、stage artifact 和 transform pipeline 结构化提供外部样本。

## 执行摘要

Triton 最值得当前仓库借鉴的不是“Python 写 GPU kernel”这层表象，而是它把高性能 kernel 拆成了几个边界清楚的合同：

1. 用户写的是“一个 program instance 处理一个 block”的块程序，而不是逐线程程序。
2. tile / block size / warps / stages 等作为 meta-parameter 进入编译与调优空间，而不是混在普通运行时参数里。
3. 前端先生成 Triton IR，后端再按 target 分阶段 lower 到 GPU IR、LLVM IR、汇编和二进制。
4. 每个编译 stage 都能缓存、dump、override 或复现，方便定位 pass 语义漂移。
5. matmul tail 不是靠整块临时 buffer 填零后再算，而是用 block pointer / mask / `other=0` / output mask 把“有效区域”显式写进访存语义。
6. autotune 是一套显式配置合同：config 负责 meta-parameter 和执行资源，key 负责什么时候重测，hook 负责多次 benchmark 前后的状态恢复。

对本仓最直接的启发是：后续不要把 tuning、tile、dynamic acc、DMA view、memory pool 和 backend lowering 混成一个大 pass；更稳的方式是把“块程序语义”“候选 config”“有效 tile 视图”“target stage”和“调试产物”分别做成可验证的中间合同。

## 文档信息

- `文档`：[`ARCHITECTURE/reference/reference_project_triton_research.md`](reference_project_triton_research.md)
- `spec`：不适用；本文为外部参考项目调研文档，不对应本仓 `spec` 文件。
- `外部参考`：见下文“外部证据源”，只使用 Triton 官方文档、官方 GitHub 仓库源码和本仓本地文件。

## 使用示例

- 当要判断本仓 tile/pattern 语义是否可借鉴 Triton blocked program 时，先读本文档“用户编程模型”与“块程序合同”。
- 当要讨论 matmul tail、dynamic acc、fill 消除或 masked/effective view 合同时，先读本文档“Matmul tail 与 fill 处理”。
- 当要设计 tuner config、stage dump 或 backend stage 边界时，先读本文档“Autotune / Config 的借鉴点”和“编译 pipeline 分层”。

## 调研对象与证据边界

本文只使用官方文档、官方 GitHub 仓库源码和本仓本地文件做调研。本文不是性能结论，也不主张直接引入 Triton 作为依赖。

### 外部证据源

- Triton 官方仓库 README：<https://github.com/triton-lang/triton>
- Triton 编程模型介绍：<https://triton-lang.org/main/programming-guide/chapter-1/introduction.html>
- Triton vector add tutorial：<https://triton-lang.org/main/getting-started/tutorials/01-vector-add.html>
- Triton matmul tutorial：<https://triton-lang.org/main/getting-started/tutorials/03-matrix-multiplication.html>
- Triton Python API `triton.jit`：<https://triton-lang.org/main/python-api/generated/triton.jit.html>
- Triton Python API `triton.autotune`：<https://triton-lang.org/main/python-api/generated/triton.autotune.html>
- Triton Python API `triton.Config`：<https://triton-lang.org/main/python-api/generated/triton.Config.html>
- Triton language API：<https://triton-lang.org/main/python-api/triton.language.html>
- Triton MLIR dialect docs：<https://triton-lang.org/main/dialects/dialects.html>
- Triton compiler driver：<https://github.com/triton-lang/triton/blob/main/python/triton/compiler/compiler.py>
- Triton NVIDIA backend compiler：<https://github.com/triton-lang/triton/blob/main/third_party/nvidia/backend/compiler.py>
- Triton AMD backend compiler：<https://github.com/triton-lang/triton/blob/main/third_party/amd/backend/compiler.py>
- Triton autotuner implementation：<https://github.com/triton-lang/triton/blob/main/python/triton/runtime/autotuner.py>

### 本仓对照点

- [`ARCHITECTURE/project_architecture.md`](../project_architecture.md)
- [`kernel_gen/pipeline/npu_demo_lowering.py`](../../kernel_gen/pipeline/npu_demo_lowering.py)
- [`kernel_gen/passes/pass_manager.py`](../../kernel_gen/passes/pass_manager.py)
- [`kernel_gen/passes/tuning/kernel_pattern_attach.py`](../../kernel_gen/passes/tuning/kernel_pattern_attach.py)
- [`kernel_gen/passes/tuning/transform_apply.py`](../../kernel_gen/passes/tuning/transform_apply.py)
- [`kernel_gen/dialect/tuner/`](../../kernel_gen/dialect/tuner)
- [`spec/dialect/tuner.md`](../../spec/dialect/tuner.md)
- [`spec/pass/transform_apply.md`](../../spec/pass/transform_apply.md)
- [`kernel/matmul/`](../../kernel/matmul)

### 证据核对矩阵

| 文档结论 | 官方来源 | 证据边界 |
| --- | --- | --- |
| Triton 是 block/program instance 编程模型，不是逐线程标量程序 | 编程模型介绍、vector add tutorial、matmul tutorial | 只证明 Triton 的公开编程模型；本仓映射仅作为 tile/pattern body 设计参考，不说明本仓已有等价 GPU runtime |
| `tl.constexpr` / meta-parameter 与普通运行时参数分层 | vector add tutorial、matmul tutorial、`triton.jit` API | 只借鉴参数分层；本文不新增或修改本仓公开 API |
| Matmul tail 通过 masked load、`other=0.0`、output mask 和 accumulator 表达 | matmul tutorial | 用于说明 tail/effective view 语义参考；不推断本仓当前 DMA 已支持 mask/default load |
| Autotune 由 `Config`、`key`、reset/restore/hook/cache 等显式配置组成 | `triton.autotune` API、`triton.Config` API、autotuner source | 只作为 tuning config 合同样本；不把 benchmark/autotune 放入本仓普通 pytest 默认要求 |
| 编译链路按 source、IR、backend stage 和 artifact 分层 | compiler driver、NVIDIA backend compiler、AMD backend compiler、MLIR dialect docs | Triton `main` 源码是移动目标，stage 名称与顺序只作为当前源码事实和架构参考，不写成本仓稳定验收 |
| Debug/dump/reproducer 是编译器可维护性能力 | Triton README | 只借鉴 artifact 可追溯原则；本仓公开行为仍应落在 `spec`、任务记录和验收命令中 |

补充边界：

- 官方 `main` 文档和 GitHub `main` 源码会随上游演进，本文记录的是能力类别和设计边界，不固定 Triton 某个 commit 的性能或 stage 细节。
- 本文任何后续转化若涉及本仓公开 API、dialect 语义、工具参数或 `expectation/` 合同资产，必须另走 `spec`、计划书和用户确认流程。

## Triton 是什么

Triton 是一个面向高性能自定义 deep-learning primitive 的语言和编译器。它的目标不是取代所有图编译器，也不是让用户完全不理解硬件；它的核心取舍是让用户用 Python 风格写 block-level program，由编译器负责把块级数据流、layout、访存、tensor core、pipeline 等硬件细节 lower 下去。

官方编程指南把 Triton 与 CUDA 的差别归纳为：CUDA 常见思路是“标量程序 + blocked threads”，Triton 是“blocked program + scalar threads”。换成当前仓库语言，就是 Triton 的用户函数天然像一个 tile/pattern body：一个 program instance 处理一个输出 tile，launch grid 决定有多少个 tile 并行。

## Triton 不是什么

1. 它不是“不写 tile 就自动生成最优 kernel”的系统。Triton matmul tutorial 中 `BLOCK_SIZE_M/N/K`、`GROUP_SIZE_M`、`num_warps`、`num_stages` 都是用户或 autotune config 显式给出的。
2. 它不是只有一个统一 lowering pass。源码中 CUDA 和 AMD backend 都各自注册多阶段 lowering。
3. 它不是把所有硬件信息塞进前端 Python。硬件相关优化主要沉到 TTGIR / backend stage。
4. 它不是适合直接拷贝到本仓的 runtime。Triton 强绑定 GPU driver、PyTorch tensor 入口、JIT cache 和二进制加载，本仓当前目标仍是自有 DSL / IR / npu_demo codegen 链路。

## 用户编程模型

### `@triton.jit` 的合同边界

`triton.jit` 把 Python 函数变成 JITFunction。官方 API 明确说明 jit 函数只应该访问 Python primitives、Triton package 内置项、函数参数和其它 jit 函数；调用时带 `.data_ptr()` 和 `.dtype` 的参数会隐式按 pointer 处理。

这点对应本仓的 DSL 前端边界：本仓已经强调 `mlir_gen` 只能接受函数形参和函数体内可达值，不能隐式捕获外部值。Triton 的经验说明，这类限制不是“功能少”，而是编译前端可验证和可缓存的必要条件。

### program instance 与 launch grid

Triton vector add tutorial 展示了最小模型：

- `tl.program_id(axis=0)` 读取当前 program instance id。
- `BLOCK_SIZE: tl.constexpr` 表示每个 program 处理多少元素。
- `tl.arange(0, BLOCK_SIZE)` 构造块内 offsets。
- launch grid 表示并行运行多少个 program instance，可以是 tuple，也可以是依赖 meta-parameter 的 callable。

对应到本仓：

- `arch.get_block_id` / `arch.get_thread_id` / `arch_parallelize` 已有并行化入口。
- `kernel-pattern-attach -> tuner.select -> tuner.launch` 已经有 host dispatcher 和 pattern body 分离雏形。
- 后续可把“一个 pattern body 对应一个 block/tile program”的语义写得更明确，而不是让 pattern 只表示“某个 pass 字符串的复制函数”。

### `tl.constexpr` 与普通参数分层

Triton tutorial 里 `BLOCK_SIZE`、`BLOCK_SIZE_M/N/K`、`GROUP_SIZE_M` 常用 `tl.constexpr`，用于形状、循环展开、编译期 specialize 和 autotune。`M/N/K`、stride、pointer 则是普通运行时参数。

这对当前仓库很关键：本仓有 `SymbolDim` runtime tile，也有 tuning 超参数 `tuner.param`。后续计划不要把“用户运行时传进来的 tile”和“调优器可改写的 compile-time meta 参数”混成一个概念。建议明确三类值：

| 类别 | Triton 对应 | 本仓建议 |
| --- | --- | --- |
| 真实运行时 shape / stride / pointer | 普通 kernel 参数 | 继续由 `Memory` / `SymbolDim` / wrapper 参数承载 |
| 编译期候选参数 | `tl.constexpr` / `triton.Config.kwargs` | 由 `tuner.param`、pattern attr 或后续 config dialect 承载 |
| 目标资源参数 | `num_warps` / `num_stages` / `num_ctas` | 不要塞进 `SymbolDim`；应进入 target/backend config |

## Matmul tail 与 fill 处理

Triton matmul tutorial 的核心结构是：

1. 每个 program instance 负责一个 `[BLOCK_SIZE_M, BLOCK_SIZE_N]` 输出块。
2. K 维按 `BLOCK_SIZE_K` 循环。
3. `accumulator = tl.zeros((BLOCK_SIZE_M, BLOCK_SIZE_N), dtype=tl.float32)`。
4. 每个 K tile 通过 `tl.load(..., mask=..., other=0.0)` 处理 K 尾块。
5. `accumulator = tl.dot(a, b, accumulator)` 显式表达累加。
6. 最终 `tl.store(..., mask=c_mask)` 只写真实输出区域。

这里有两个值得本仓直接吸收的点。

### 1. tail 是访存语义，不应该退化成整块 fill

Triton 不需要先把 full tile 临时 buffer 全部 `fill(0)`，再把真实 slice 拷进去，最后把 full tile 喂给 matmul。它把“越界读返回 0”和“越界输出不写”作为访存合同。

本仓当前 matmul demo 中常见模式是：

```text
alloc full tile
fill full tile
view real input slice
deslice real slice into tile
kernel.matmul full tile
```

这会让尾块 correctness 依赖 fill，而且让后续 pass 很难判断哪些 fill 真正影响结果。更接近 Triton 的建模方式是：

```text
view effective input tile
kernel.matmul effective output/view, effective lhs/view, effective rhs/view, acc=(k0 != 0)
store only effective output region
```

这正好支持当前 `matmul_effective_view_fill_elimination` 计划：不要靠 canonicalize 猜 fill 可删，而要把有效区域写成 IR 合同。

### 2. accum 语义应该在 matmul op 上显式出现

Triton 的 `tl.dot(a, b, accumulator)` 把“这次 dot 累加到已有 accumulator”写成 op 参数。当前本仓动态 acc `kernel.matmul(..., acc=<i1>)` 与这个方向一致。

后续应坚持：

- 第一段 K tile：`acc=false`，matmul 覆盖输出 effective view。
- 后续 K tile：`acc=true`，matmul 累加到同一 effective view。
- 不要再生成旧式 `partial + kernel.add` 或靠前置 `fill(acc, 0)` 暗示 first-K 初始化。

这比单独做 fill DCE 更稳，因为语义在 `kernel.matmul` 上，不依赖跨 op 数据流猜测。

## 编译 pipeline 分层

Triton compiler driver 中 `compile(...)` 的结构可以概括为：

```text
ASTSource / IRSource
  -> make_ir(...)
  -> backend.add_stages(...)
  -> 按 stage 顺序生成并缓存 artifact
  -> CompiledKernel
```

CUDA backend 的 stage 顺序在源码中是：

```text
ttir -> ttgir -> llir -> ptx -> cubin
```

AMD backend 的 stage 顺序是：

```text
ttir -> ttgir -> llir -> amdgcn -> hsaco
```

这对本仓的启发不是“照抄 TTIR/TTGIR”，而是后续应把 `npu_demo` 也拆成更清楚的 stage 概念：

```text
DSL / operation
  -> high-level kernel/dma/symbol IR
  -> tiled/pattern IR
  -> memory hierarchy IR
  -> parallelized device IR
  -> outlined host/device IR
  -> npu_demo source bundle
```

本仓现在 `build_npu_demo_lowering_pipeline(...)` 已经有固定顺序，但它是一个长 pass 列表。Triton 的结构提醒我们：当这个列表继续增长时，应优先引入“stage 级命名与 artifact 合同”，而不是继续只追加 pass。

## 后端专有优化的边界

Triton 官方 dialect docs 列出 `tt`、`ttg`、`ttng`、`amdg`、`nvg` 等 dialect。源码上也能看到 CUDA backend 和 AMD backend 各自有独立 pass 组合。

本仓对应建议：

1. `kernel/dma/symbol` 这类前段 IR 不应提前绑定具体 NPU backend 内存布局。
2. `lower-dma-memory-hierarchy`、`memory-pool`、`arch-parallelize`、`attach-arch-information` 更接近 target stage，应保留清楚的 target boundary。
3. `TransformApplyPass` 现在用 pattern 上的 `kernel.transform_pipeline` 字符串驱动局部 pass，这是一个可用起点，但后续如果 target 增多，应考虑从“字符串 pass pipeline”升级为“结构化 transform config”。

## Autotune / Config 的借鉴点

Triton 的 autotune API 有几类明确对象：

- `triton.Config(kwargs, num_warps, num_stages, num_ctas, maxnreg, pre_hook, ir_override)` 描述一个候选配置。
- `triton.autotune(configs=..., key=...)` 描述什么时候重新 benchmark 候选配置。
- `prune_configs_by` 支持 perf model、top-k 和 early prune。
- `reset_to_zero` / `restore_value` / hook 处理多次运行同一 kernel 时输出或输入状态污染。
- 实现中会按 tuning key 缓存最佳 config，并可选把 autotune timing 落盘。

本仓现状：

- `tuner.param` 能声明超参数。
- `tuner.cost` 能表达局部成本节点。
- `tuner.select` / `tuner.launch` 能表达 pattern dispatcher。
- `kernel-pattern-attach` 当前固定生成两个 pattern，`npu_demo` 源码发射目前固定选择 pattern0。

可借鉴但要分阶段落地：

| Triton 能力 | 本仓可落点 | 建议 |
| --- | --- | --- |
| `Config.kwargs` | `tuner.param` / 后续 config spec | 增加结构化 config，而不是继续把候选塞进字符串 |
| `num_warps/num_stages/num_ctas` | target/backend config | 作为 target resource，不要混进普通 symbol 参数 |
| `autotune key` | shape/tile/runtime profile key | 后续 runner 可按 shape/tile seed 或实际 shape 记录选择 |
| `reset_to_zero/restore_value` | benchmark runner | 任何会多次运行候选的测试必须恢复输出 buffer |
| disk cache | `kernel/dump` 或独立 cache | 先做可审计记录，不急于长期缓存 |
| `ir_override` | transform debug / reproducer | 只可做调试入口，不能成为正常计划必需路径 |

## Debug / dump / reproducer 的借鉴点

Triton README 记录了多类调试入口：

- `MLIR_ENABLE_DUMP` dump 每个 MLIR pass 前后的 IR。
- `MLIR_DUMP_PATH` 控制 dump 位置。
- `TRITON_REPRODUCER_PATH` 在 stage 失败前生成 reproducer。
- `TRITON_INTERPRET=1` 可用解释器调试 kernel。
- `USE_IR_LOC={ttir,ttgir}` 让 IR location 更适合关联后续产物。

本仓已有 `PassManager` 的 dump 机制和 `kernel/dump/...` demo 产物。建议继续强化：

1. dump 文件名固定包含 stage index、stage name、pass name。
2. `transform-apply` 对 pattern 内局部 pipeline 的 dump 要能区分 pattern0/pattern1。
3. 每个 demo 的 `canonicalize.mlir`、`source.cpp`、运行 profile、seed、selected tile 应形成稳定目录结构。
4. 失败时优先保存最小 reproducer IR，而不是只保存最后一份 source。

这能直接帮助当前 matmul fill / effective view / dynamic acc 类问题定位。

## 可直接借鉴的设计清单

### A. 块程序合同

把“一个 pattern/device body 处理一个 tile/block”写成明确合同。当前 `kernel-pattern-attach` 生成 pattern 函数，但 pattern 还更像 pass 容器。后续可以补充：

- pattern 的 grid 维度来源。
- pattern 的 program id / block id 语义。
- pattern 允许读取哪些 runtime shape/tile 参数。
- pattern 是否允许内部再 launch 或 call。

### B. 有效 tile view / masked DMA

为 tail 建模优先使用 effective view 或 masked load/store，而不是 full tile fill。当前计划中的 `view(acc, [0,0], [cur_m,cur_n], [1,1])` 是一个正确方向。

后续如果要更接近 Triton，可以考虑新增或扩展 DMA 合同：

- `dma.view` 表达有效区域。
- `dma.load` / `dma.store` 支持 mask / default value。
- `dma.deslice` 对 tail 的语义要能区分“未写区域无关”和“未写区域后续会被读取”。

注意：这涉及公开 API 或 dialect 语义时必须先走 spec 与用户确认。

### C. dynamic acc matmul

保持 `kernel.matmul` 的 acc 参数作为 first-K / later-K 的唯一语义入口。后续所有 fill 消除、partial 删除、matmul fusion / decompose 都应围绕这个合同，而不是另写跨 op 猜测。

### D. tuning config 结构化

现在 pattern pipeline 是字符串：

```text
--pass "lower-dma-memory-hierarchy={...}" --pass canonicalize
```

短期能用，但长期不适合承载完整 tuning config。建议参考 Triton `Config` 的分层，把候选配置拆成：

- transform 参数：如 memory hierarchy、layout、pipeline stage。
- resource 参数：如 block/warp/thread/group 配置。
- search key：哪些 runtime shape 变化会触发重选。
- benchmark hook：运行前后如何清理输出。

### E. stage artifact 合同

Triton 每个 stage 都可成为 cache/dump artifact。本仓也应把 `npu-demo-lowering` 长 pipeline 归并成阶段名，用于测试和调试：

| 建议 stage | 可能覆盖的现有 pass |
| --- | --- |
| `frontend-cleanup` | inline / cse / canonicalize / decompass / nn lowering |
| `tile-pattern` | memory-plan / symbol-hoist / tile-analysis / kernel-pattern-attach |
| `pattern-transform` | transform-apply / lower-dma-memory-hierarchy |
| `kernel-matmul-normalize` | kernel-aggregate / kernel-decompose / dynamic acc |
| `memory-backend` | producer-consumer-analysis / memory-pool |
| `parallel-outline` | arch-parallelize / attach-arch-information / outline / template-name |

先作为文档和 dump 命名，不需要马上改公开 API。

## 不建议照搬的点

1. 不建议把 Triton 的 Python runtime/JIT/cache/driver 体系搬进本仓。本仓当前目标不是 GPU JIT runtime。
2. 不建议照抄 CUDA/AMD backend 的具体 pass 列表。那些 pass 与 TTGIR、LLVM、NVVM/ROCDL 强耦合。
3. 不建议用环境变量作为正常合同入口。本仓已有 spec / test / expectation / plan 规范，公开行为应先落 spec。
4. 不建议把 autotune benchmark 放进普通 pytest 的必跑路径。Triton autotune 会多次执行 kernel，成本和状态污染都需要独立 runner 设计。
5. 不建议把 `ir_override` 类能力做成用户正常工作流。它适合 debug 和 bisect，不适合成为生产链路。

## 对当前 matmul fill 问题的直接启发

当前讨论的 fill 问题可以用 Triton 的口径重新表述：

- 问题不在于某个 `fill` pass 没有“优化聪明”。
- 问题在于 IR 把 tail correctness 表达成了“full tile 临时 buffer 先清零”，而不是表达成“matmul 只消费 effective tile”或“越界 load 为 0”。
- 如果 `kernel.matmul` 已经有 dynamic acc，第一段 K tile 可以覆盖 accumulator，有效输出区域不需要前置 fill。
- 对输入 tail，如果输入 arg 是用户传入的真实 memory，不能改用户 buffer 本体；只能通过 view/mask/default-value 这类读语义描述有效区域。

因此，当前更好的方向仍是计划 A：

```text
acc_storage = alloc([tile_m, tile_n])
acc_eff = view(acc_storage, [0, 0], [cur_m, cur_n], [1, 1])
lhs_eff = view(lhs_tile_or_input, ..., [cur_m, cur_k], ...)
rhs_eff = view(rhs_tile_or_input, ..., [cur_k, cur_n], ...)
kernel.matmul(acc_eff, lhs_eff, rhs_eff, acc=(k0 != 0))
```

如果后续发现 `lhs_tile/rhs_tile` 仍必须经过 staging buffer，则需要把 staging buffer 的未写区域证明为不被读取，或引入 masked/default load 语义；不要再让 `fill(lhs_tile, 0)` 成为隐藏正确性条件。

## 后续可形成计划的方向

这些不是本文直接创建的任务，只是后续计划输入。

1. `tuner.Config` 类合同：定义候选配置、resource 参数、shape key 和 benchmark hook。
2. `effective tile view` 合同：明确 `dma.view` / `kernel.matmul` 对动态 shape slice 的合法输入语义。
3. `masked DMA` 合同：如果 effective view 不足以表达 input tail，新增 mask/default-value 读语义。
4. `npu-demo stage dump` 合同：把长 pipeline 的 dump 从 pass 列表提升到阶段化 artifact。
5. `transform_pipeline` 结构化替代：把字符串 pipeline 收口为可 parse/print/verify 的 IR attr 或 dialect op。
6. `autotune runner` 独立化：把 benchmark 多次运行、输出重置、结果缓存从普通 demo pytest 中剥离。

## 最小建议

短期不要动大架构。对当前仓库最划算的顺序是：

1. 先完成 matmul effective view + dynamic acc fill 消除，让 IR 语义从“靠 fill 保正确”改成“靠有效 tile 和 acc 合同保正确”。
2. 再把 `tuner.select` 从固定 pattern0 推进到最小 config/key 选择合同。
3. 最后再考虑 stage artifact 和 backend stage registry。

这样能沿着 Triton 的关键经验前进，但不会把当前仓库拖进一个过大的 GPU compiler 重写计划。
