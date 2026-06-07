# IREE 调研与本仓可借鉴点

## 功能简介

- 调研 IREE 的 Flow / Stream / HAL / VM 分层、Codegen pipeline、dispatch / executable 边界、cleanup / legality gate 和 target backend 分层。
- 为本仓 host/device 边界、source bundle、target late lowering、pipeline cleanup 与 backend artifact 管理提供长期参考。
- 区分 IREE 的 end-to-end compiler / runtime toolkit 和本仓当前 DSL / IR / kernel demo，不把外部 runtime 体系写成本仓目标。

## 执行摘要

1. IREE 最值得借鉴的是阶段分层：Input / ABI / Flow / Stream / HAL / VM 等 phase 把高层数据流、dispatch、executable、target backend 与 runtime packaging 分开。
2. Flow 层负责 data flow、dispatch region、executable outline、dynamic dim capture 和 shape cleanup，是 high-level tensor program 到 executable unit 的关键边界。
3. HAL 层把 target device、hal.executable、executable variant、translation pipeline 和 host/device command 边界下沉到后段。
4. Codegen 使用 lowering config / dispatch config 记录 tile、workgroup、thread、subgroup 等决策，后续 lowering 读取属性，而不是处处重新做 heuristic。
5. IREE 的 pass 文档和源码都显示 cleanup、canonicalize、legality verification、fixed-point cleanup 应穿插在明确阶段中，而不是靠最终失败回推。
6. 对本仓最直接的迁移口径是：把 source bundle / backend codegen / runtime launcher 的边界保持靠后，用可审 IR 和任务记录证明每一层输入输出。

## 文档信息

- `文档`：[`ARCHITECTURE/reference/reference_project_iree_research.md`](reference_project_iree_research.md)
- `spec`：不适用；本文为外部参考项目调研文档，不对应本仓 `spec` 文件。
- `外部参考`：见下文“外部证据源”，只使用 IREE 官方文档和官方 GitHub 源码。
- `本仓影响`：不修改公开 API、`kernel_gen/`、`spec`、`test` 或 `expectation/`。

## 使用示例

- 讨论本仓 backend 是否应拆 host / device / source bundle 边界时，先读“Flow / HAL / VM 分层”。
- 讨论 dispatch / executable 是否要成为 IR 边界时，先读“dispatch / executable 边界”。
- 讨论 target tile / workgroup 参数是否应写入 IR 属性时，先读“Codegen lowering config”。

## 调研对象与证据边界

本文只读查看官方文档和官方 GitHub 源码，不下载、不 clone、不编译外部项目。IREE `main` 与 iree.dev 文档会持续变化，本文只记录能力类别和设计边界，不固定 pass 顺序、性能数字或 target backend 内部实现为本仓合同。

### 外部证据源

- IREE 官方网站：<https://iree.dev/>
- IREE 官方仓库 README：<https://github.com/iree-org/iree>
- IREE developer overview：<https://iree.dev/developers/general/developer-overview/>
- IREE developer tips / phase-by-phase compilation：<https://iree.dev/developers/general/developer-tips/>
- Flow MLIR passes：<https://iree.dev/reference/mlir-passes/Flow/>
- HAL MLIR passes：<https://iree.dev/reference/mlir-passes/HAL/>
- IREE lowering configs：<https://iree.dev/developers/lowering-config/>
- IREE Codegen dialect：<https://iree.dev/reference/mlir-dialects/IREECodegen/>
- VM design：<https://iree.dev/developers/design-docs/vm/>
- Flow transform pipeline source：<https://github.com/iree-org/iree/blob/main/compiler/src/iree/compiler/Dialect/Flow/Transforms/Passes.cpp>
- HAL transform pipeline source：<https://github.com/iree-org/iree/blob/main/compiler/src/iree/compiler/Dialect/HAL/Transforms/Passes.cpp>
- Codegen common passes source：<https://github.com/iree-org/iree/blob/main/compiler/src/iree/compiler/Codegen/Common/Passes.cpp>
- Global optimization passes source：<https://github.com/iree-org/iree/blob/main/compiler/src/iree/compiler/GlobalOptimization/Passes.cpp>

### 本仓对照点

- [`kernel_gen/pipeline/npu_demo_lowering.py`](../../kernel_gen/pipeline/npu_demo_lowering.py)
- [`kernel_gen/dsl/gen_kernel/`](../../kernel_gen/dsl/gen_kernel)
- [`kernel_gen/execute_engine/`](../../kernel_gen/execute_engine)
- [`kernel_gen/execute_engine/builtin_strategy/`](../../kernel_gen/execute_engine/builtin_strategy)
- [`spec/dsl/gen_kernel/source_bundle.md`](../../spec/dsl/gen_kernel/source_bundle.md)
- [`spec/execute_engine/strategy.md`](../../spec/execute_engine/strategy.md)
- [`kernel/matmul/`](../../kernel/matmul)
- [`kernel/conv2d/`](../../kernel/conv2d)

### 证据核对矩阵

| 文档结论 | 官方来源 | 证据边界 |
| --- | --- | --- |
| IREE 是 MLIR-based end-to-end compiler and runtime toolkit | 官方网站、官方 README | 只说明外部项目定位；本仓不接入 IREE runtime |
| 编译 phase 包括 Input / ABI / Flow / Stream / HAL / VM | developer tips | phase 名只作分层参考，不写成本仓 pipeline 名 |
| Flow pass 包含 dispatch annotation、dynamic dim capture、shape cleanup、dispatch region outline、executable dedup | Flow pass docs、Flow Passes.cpp | 只借鉴 dispatch / executable 分层 |
| HAL pass 处理 device assignment、target executable、executable translation、host/device command 边界 | HAL pass docs、HAL Passes.cpp | 不引入 HAL dialect 或 runtime |
| Codegen lowering config 用属性携带 workgroup / thread / subgroup / reduction 等决策 | lowering configs、IREECodegen dialect docs | 只借鉴“决策写入 IR 属性”思想 |
| VM / VMFB 是后段 packaging 和 runtime 调用模型 | VM design、developer tips | 不把 VM bytecode 或 module system 作为本仓目标 |

## 项目是什么 / 不是什么

| 问题 | 结论 | 本仓解释 |
| --- | --- | --- |
| IREE 是不是 end-to-end compiler / runtime toolkit？ | 是 | 官方 README 和网站都围绕 compiler + runtime 展开 |
| Flow 是不是普通 cleanup pass？ | 不是 | Flow 表达 data flow、dispatch region、executable outline 等核心中间边界 |
| HAL 是不是只表示硬件名称？ | 不是 | HAL 管 device、executable、target backend、command 和 host/device 交互 |
| Codegen config 是不是普通注释？ | 不是 | 它承载 lowering 决策，后续 lowering 读取这些属性 |
| 是否适合本仓直接引入 IREE？ | 当前不适合 | 会改变 dialect、runtime、module packaging 和 deployment 边界 |

## 可借鉴方法

### 1. Flow / HAL / VM 分层把职责拆开

IREE developer tips 给出 phase-by-phase 编译视图：从 input 到 ABI，再到 Flow、Stream、HAL、VM。这个分层对本仓的启发是：

- 高层 DSL / IR 不应该提前知道最终 runtime packaging。
- dispatch / executable 边界应在中后段形成。
- target backend 的 layout、workgroup、source bundle 和 launcher 逻辑应靠后处理。

### 2. dispatch / executable 是明确中间合同

Flow pass 文档列出 outline dispatch regions、deduplicate executables、annotate dispatches、dump dispatch graph 等能力。对本仓来说，可以借鉴“把可执行单元从高层图中 outline 出来”的思路：

- 一个 kernel / tile body 是否已经成为可后端 lowering 的 unit，需要有明确 IR 或记录。
- host 侧 dispatcher 与 device 侧 executable 不应互相偷用内部 helper。
- source bundle 应表达 artifact 边界，而不是把后端所有文件拼成普通字符串。

### 3. HAL 层承接 target backend，而不是污染 Flow

HAL pass 文档和 `HAL/Transforms/Passes.cpp` 展示了 device assignment、target configuration、executable linking / translation 等后段职责。对本仓迁移口径：

- `npu_demo` / `cuda_sm86` target 信息应从显式 target / pipeline 进入。
- backend-specific source / header / shared library 路径应在 execute engine / strategy 层管理。
- 高层 pass 不应直接决定编译器二进制或 runtime module 包装。

### 4. Codegen lowering config 把 heuristic 变成 IR 属性

IREE Codegen dialect 文档说明 backend 先分析 entry point / target，再把 tile sizes 等决策写入属性，后续 flow 读取属性而不是反复做 heuristic。

本仓可以借鉴：

- tuning / tile / workgroup / memory_stage 决策应有显式 IR attr 或任务记录。
- 后端 lowering 不要重新猜高层含义。
- 若未来有 search / tuner，输出应是可审 config，不是隐式 Python 状态。

### 5. Cleanup 与 legality gate 要在阶段内显式存在

Flow pass 文档中有 canonicalize、cleanup tensor shapes、verify input legality。HAL 源码中也能看到 cleanup patterns 和 fixed-point iterator 的使用。对本仓：

- pipeline 阶段之间要有 legality check。
- cleanup barrier 应写在 pipeline spec。
- 后段 rewrite 产生的新冗余应在本阶段内清掉，不把负担留给最终 codegen。

## 对本仓的迁移口径

| IREE 方法 | 本仓可迁移口径 | 不改变的边界 |
| --- | --- | --- |
| phase-by-phase compilation | 明确 DSL / pipeline / backend strategy 分层 | 不引入 IREE dialect |
| Flow dispatch / executable | 为 kernel executable unit 建立可审边界 | 不新增 runtime module |
| HAL target backend | target late lowering 只在后段 strategy 执行 | 不让高层 pass 依赖 backend internals |
| Codegen lowering config | tile / workgroup / tuning 决策显式化 | 不新增公开 API，除非另有用户确认 |
| legality + cleanup | 阶段内校验与 cleanup barrier | 不靠最终失败反推 |

建议本仓按以下顺序吸收：

1. 先明确 host/device/source bundle 的文档边界。
2. 再让 pipeline 阶段记录 dispatch / executable unit。
3. 最后才把 target backend 的 lowering config 显式化。

## 最不该直接照搬的点

- 不引入 Flow / Stream / HAL / VM dialect 作为本仓 IR。
- 不引入 IREE runtime、VMFB、HAL executable 或 target plugin 体系。
- 不把 IREE phase 名称写成本仓公开 pipeline 合同。
- 不把 full model deployment 假设套到当前 kernel demo。
- 不把 backend workgroup / tile heuristic 藏进普通运行时参数。

## 自检清单

- 后续计划引用本文时，是否明确 high-level IR、dispatch / executable、backend strategy 的边界？
- 是否避免把 target backend 细节提前放入共享 pass？
- 是否把 tile / workgroup / tuning 决策写成可审事实？
- 是否保留阶段 legality check 和 cleanup barrier？
- 是否未新增公开 API、工具参数、`expectation/` 或 runtime 依赖？
- 是否只把 IREE 作为方法参考，而不是依赖接入或部署方案？
