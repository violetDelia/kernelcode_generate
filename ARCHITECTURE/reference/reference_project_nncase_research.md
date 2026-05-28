# nncase 调研与本仓可借鉴点

## 功能简介

- 调研外部参考项目 `kendryte/nncase` 的模型编译、量化、动态 shape、pass 分层、dump 与运行验证闭环。
- 区分 nncase 的“整模型编译器”定位和本仓当前“DSL / 高层语义 / 局部 kernel demo”定位，避免把外部项目能力误写成本仓已具备能力。
- 为后续讨论 `nn` 算子覆盖矩阵、lowerability 合同、runtime symbolic profile、stage dump 和输入预处理合同提供外部样本。

## 执行摘要

1. nncase 的本质是面向 AI accelerator 的神经网络模型编译器，不是单 kernel/tile DSL。
2. 它把模型导入、预处理、PTQ/混合量化、动态 shape bucket、target-independent pass、target-dependent pass、codegen 和 simulator 验证放进一条可配置链路。
3. 最值得本仓借鉴的是“显式编译合同”：`CompileOptions`、`PTQTensorOptions`、ShapeBucket 配置、dump 目录、target 名称、输入预处理和运行验证都作为可审计配置出现。
4. nncase 的 pass 边界很清楚：先做 target-independent 规范化和优化，再进入 target-dependent 优化、量化、后量化目标优化、codegen 前收口。
5. 它把 stage dump 做成编译流程的一等能力，公开源码中 `RunPassAsync` 会按阶段序号和阶段名组织 pass manager，并在 dump 开启时写出 IR / dot 产物。
6. 对本仓最直接的启发是：`nn` 高层语义、可 lower 算子矩阵、shape profile、target pass、预处理/layout 合同和 demo 验证记录应分开建模，不要混成隐式 runner 行为。
7. 不应照搬的是：引入 dotnet/nncase runtime/kmodel 包装、复制闭源 KPU 插件能力、或把整模型编译器边界强行套到当前单 kernel 生成链路上。

## 文档信息

- `文档`：[`ARCHITECTURE/reference/reference_project_nncase_research.md`](reference_project_nncase_research.md)
- `spec`：不适用；本文为外部参考项目调研文档，不对应本仓 `spec` 文件
- `外部参考`：
  - [kendryte/nncase README](https://github.com/kendryte/nncase)
  - [nncase v2 使用说明](https://github.com/kendryte/nncase/blob/master/docs/USAGE_v2_EN.md)
  - [nncase ShapeBucket](https://github.com/kendryte/nncase/blob/master/docs/shape_bucket.md)
  - [nncase MixQuant](https://github.com/kendryte/nncase/blob/master/docs/MixQuant.md)
  - [nncase FAQ](https://github.com/kendryte/nncase/blob/master/docs/FAQ_EN.md)
  - [python/nncase/__init__.py](https://github.com/kendryte/nncase/blob/master/python/nncase/__init__.py)
  - [src/Nncase.Compiler/Compiler.cs](https://github.com/kendryte/nncase/blob/master/src/Nncase.Compiler/Compiler.cs)
  - [src/Nncase.Core/CompileOptions.cs](https://github.com/kendryte/nncase/blob/master/src/Nncase.Core/CompileOptions.cs)
  - [src/Nncase.Core/CompileSession.cs](https://github.com/kendryte/nncase/blob/master/src/Nncase.Core/CompileSession.cs)

## 使用示例

- 当要判断本仓 `nn` API 是否已经等价于“模型编译器”时，先读本文档“项目是什么 / 不是什么”。
- 当要设计 `nn` lowerability 矩阵、unsupported op 错误、动态 shape profile 或 stage dump 合同时，参考本文档“可借鉴点”。
- 当要讨论量化、输入预处理或模型级 runtime 包装时，先读本文档“不要直接照搬的点”，避免把未来能力写成当前计划默认前提。

## 调研对象与证据边界

### 外部证据源

- nncase 官方仓库 README：<https://github.com/kendryte/nncase>
- nncase v2 使用说明：<https://github.com/kendryte/nncase/blob/master/docs/USAGE_v2_EN.md>
- nncase ShapeBucket 文档：<https://github.com/kendryte/nncase/blob/master/docs/shape_bucket.md>
- nncase 混合量化文档：<https://github.com/kendryte/nncase/blob/master/docs/MixQuant.md>
- nncase FAQ：<https://github.com/kendryte/nncase/blob/master/docs/FAQ_EN.md>
- nncase Python wrapper：<https://github.com/kendryte/nncase/blob/master/python/nncase/__init__.py>
- nncase 编译器主流程：<https://github.com/kendryte/nncase/blob/master/src/Nncase.Compiler/Compiler.cs>
- nncase 编译选项：<https://github.com/kendryte/nncase/blob/master/src/Nncase.Core/CompileOptions.cs>
- nncase CompileSession：<https://github.com/kendryte/nncase/blob/master/src/Nncase.Core/CompileSession.cs>

### 本仓对照点

- [`ARCHITECTURE/project_architecture.md`](../project_architecture.md)
- [`spec/operation/nn.md`](../../spec/operation/nn.md)
- [`kernel_gen/operation/nn/`](../../kernel_gen/operation/nn)
- [`kernel/runner.py`](../../kernel/runner.py)
- [`kernel/matmul/`](../../kernel/matmul)
- [`kernel/conv2d/`](../../kernel/conv2d)
- [`kernel/flash_attention/`](../../kernel/flash_attention)
- 生成产物目录 `kernel/dump/`：运行 demo 后生成，不作为当前 tracked 常驻路径引用。

### 证据边界

- 本文只使用官方公开仓库、官方文档和本仓本地文件。
- README 明确提示 K510/K230 相关芯片源码并非全部开源；因此本文不推断闭源 `nncase-kpu` / KPU 插件内部实现。
- nncase v2 Python wrapper 中可直接确认的导入入口是 ONNX、TFLite 和 NCNN；仓库保留 Caffe ops 文档，但不能据此把 Caffe 当作 v2 Python wrapper 的已确认导入主路径。
- 本文不是性能结论，不主张本仓直接依赖 nncase，也不把 nncase 的模型级 runtime 产物等同于本仓当前 `npu_demo` 源码生成。
- GitHub `master` 文档和源码会随上游演进，本文记录能力类别、证据边界和可借鉴设计，不固定某个 commit 的性能、pass 顺序或 target 插件行为。

### 证据核对矩阵

| 文档结论 | 官方来源 | 证据边界 |
| --- | --- | --- |
| nncase 是面向 AI accelerator 的模型编译器，不是单 kernel DSL | README、v2 使用说明 | 只说明外部项目定位；本仓仍按自有 DSL / IR / kernel demo 链路理解 |
| Python wrapper 暴露模型导入、PTQ、编译、gencode 和 simulator 闭环 | v2 使用说明、`python/nncase/__init__.py` | 直接确认的 v2 wrapper 导入主路径限 ONNX、TFLite、NCNN；Caffe 只作为仓库文档事实 |
| `CompileOptions` / PTQ / dump / preprocess 是显式编译合同 | v2 使用说明、`CompileOptions.cs`、MixQuant 文档 | 只作为配置设计样本；不说明本仓当前已有 PTQ、混合量化或模型预处理主链路 |
| ShapeBucket 把动态 shape 范围、segment 和固定变量显式化 | ShapeBucket 文档 | 只作为 runtime symbolic profile/bucket 参考；不把 `SymbolDim` 扩展成 profile 合同 |
| 编译流程分 target-independent、target-dependent、quant、before-codegen 等 stage，并支持阶段 dump | `Compiler.cs`、`CompileSession.cs` | stage 名称和源码顺序是上游当前实现事实；本仓只借鉴 stage artifact 与维护边界 |
| KPU / K230/K510 相关能力存在公开源码边界 | README、FAQ | 不推断闭源插件内部实现，不把闭源 target 能力写成本仓可复制能力 |

补充边界：本文任何后续转化若涉及本仓公开 API、工具参数、dialect 语义、量化合同或 `expectation/` 合同资产，必须另走 `spec`、计划书和用户确认流程。

## 项目是什么 / 不是什么

| 问题 | 结论 | 说明 |
| --- | --- | --- |
| nncase 是不是模型编译器？ | 是 | README 与 v2 使用文档都围绕模型导入、编译、量化、生成 kmodel、模拟执行展开 |
| 它是不是单 kernel DSL？ | 不是 | 用户 API 面向模型文件、编译选项、PTQ 选项和 simulator，不是让用户写 tile program |
| 它是不是只做语义检查？ | 不是 | 公开源码包含 Importer、Core、Graph、EGraph、Passes、Quantization、CodeGen、Runtime 等层 |
| 它是不是完全开源可复刻 K230/KPU 后端？ | 不是 | K230/K510 芯片相关插件源码存在公开边界，不能把闭源 target 能力当作可复制事实 |
| 它是不是适合本仓直接接入？ | 当前不适合 | 本仓当前主线是自有 DSL/IR/kernel demo，直接引入 nncase 会改变产品边界和依赖栈 |

## 实现分层

| 层级 | nncase 对象 / 模块 | 职责 | 本仓对照 |
| --- | --- | --- | --- |
| 用户配置层 | `CompileOptions`、`ImportOptions`、`PTQTensorOptions` | 描述 target、dump、输入预处理、动态 shape、量化与校准数据 | `core.config`、demo runner、未来 shape profile / dtype config |
| 模型导入层 | `ImportOnnx`、`ImportTFLite`、`ImportNcnn` | 把外部模型导入 IR module | 本仓当前没有整模型导入层 |
| IR / Graph 层 | `Nncase.Core`、`Nncase.Graph`、`Nncase.EGraph` | 表达模型图、类型、shape、等价改写和优化 | 本仓 `operation/nn` 仅是高层算子语义，不能等同整图 IR |
| Pass 层 | `Nncase.Passes` | 分阶段做规范化、融合、shape 推导、目标相关优化 | 本仓 `passes` 与 `npu_demo_lowering` 有局部对应 |
| Quantization 层 | `Nncase.Quantization`、PTQ options | 用校准数据和量化方案决定张量范围、类型和混合量化 | 本仓当前没有量化主链路 |
| CodeGen / Runtime 层 | `Nncase.CodeGen`、`Nncase.Runtime` | 生成并序列化 runtime 模型产物 | 本仓当前生成 C/C++ 源码和 demo 执行，不生成 kmodel |
| 验证层 | `Simulator` | 加载 kmodel，设置输入输出，执行并比对结果 | 本仓 `kernel.runner.run_numpy_demo` 是局部 kernel 级对应物 |

## 用户 API 与编译合同

nncase 的 Python API 把编译流程拆成几个显式对象：

```text
CompileOptions
ImportOptions
PTQTensorOptions
Compiler
Simulator
```

公开 wrapper 中的典型流程可以概括为：

```text
Compiler(compile_options)
  -> import_onnx / import_tflite / import_ncnn
  -> use_ptq(ptq_options)
  -> compile()
  -> gencode_tobytes()
  -> Simulator.load_model(...)
  -> set inputs / run / read outputs
```

这套结构对本仓的价值在于：编译输入、编译策略、量化输入、生成产物和运行验证不是隐式散落在脚本里，而是有稳定对象承载。后续本仓如果继续扩大 `kernel/` demo，不宜只靠 case 名和临时 Python 变量表达合同；更稳的方式是引入 case manifest 或 profile 记录，明确：

- 输入张量 shape、dtype、layout、stride 和 runtime symbol。
- 期望结果来源，例如 NumPy reference。
- 编译 target、dump 目录、pass pipeline 名称。
- 运行时 profile，例如随机种子、tile 候选、dynamic dim 范围。
- 产物位置和可复现命令。

## 编译流程

公开 `Compiler.cs` 中的主流程可概括为：

```text
import model
  -> InitializeModuleAsync
       -> dump IRImport
       -> BroadcastOutputNamesAfterImport
       -> ShapeInferAfterImport
       -> AddPreAndPostProcessAfterImport
       -> InferenceType
  -> CompileAsync
       -> TargetIndependentPass
       -> TargetIndependentQuantPass
       -> ShapeBucket / TargetIndependentPass again when enabled
       -> TargetDependentPass
       -> QuantizePass
       -> TargetDependentAfterQuantPass
       -> ClearFixShape
       -> TargetDependentBeforeCodeGen
       -> dump ModuleAfterCompile
  -> Gencode
```

这个顺序说明了几个设计原则：

1. 导入后的 shape/type/preprocess 会先收敛，再进入主要优化。
2. 目标无关优化和目标相关优化分层，不把所有逻辑塞进一个 pass。
3. 动态 shape bucket 不是普通常量折叠，而是会影响优化阶段重跑。
4. 量化前后都有独立阶段，量化不是某个算子 lowering 中顺手做掉的副作用。
5. codegen 前还有目标侧收口阶段，便于把最后的 layout、buffer 和 runtime 约束归一。

对本仓来说，后续如果 `npu_demo_lowering` 继续增长，应优先建立 stage 级合同，而不是只追加 pass 名称。一个更清楚的方向是：

```text
high-level nn / DSL IR
  -> semantic normalization
  -> shape/profile specialization
  -> target-independent kernel lowering
  -> target-dependent memory / dma / parallel lowering
  -> codegen preparation
  -> source bundle / runner metadata
```

## Stage Dump 与可复现性

nncase 的 `RunPassAsync` 会为每次阶段运行创建带序号和名称的 pass manager，并在 dump 开启时写出该阶段的 module 和 dot IR。这个设计很适合参考。

本仓已经有 `kernel/dump/<case_name>/` 和 pass manager dump，但当前更多是“逐 pass 文件”。如果后续要支持复杂 `nn` case、runtime symbolic profile 和多 target，建议把 dump 分成两层：

| 层级 | 内容 | 目的 |
| --- | --- | --- |
| stage dump | 例如 `01-imported`, `02-normalized`, `03-profiled`, `04-target-lowered`, `05-codegen-ready` | 让人先看清大阶段语义是否正确 |
| pass dump | 每个具体 pass 后的 IR | 定位具体 pass 的改写问题 |

这能避免调试时只能在几十个 pass dump 中人工猜测“哪一个文件代表语义边界”。

## 输入预处理是模型合同

nncase 的 `CompileOptions` 不只包含 target 和 dump，也包含输入预处理相关字段，例如 input type、shape、range、layout、swapRB、mean、std、letterbox、output layout 等。v2 使用文档还明确给出预处理流水线顺序，并提醒如果把预处理写进模型产物，验证时必须按等价预处理比对。

这点对本仓非常重要。本仓当前 `nn` 语义和 kernel demo 主要处理已经准备好的数组。如果未来要在 case 层加入 layout 转换、dtype cast、padding、letterbox 或类似 view/copy 策略，不应隐藏在 runner 内部；它必须成为 case 合同的一部分。

建议口径：

- `operation/nn` 继续只定义算子语义，不夹带模型输入预处理。
- demo/case manifest 可以记录输入预处理，但必须在 dump 和验证摘要里可见。
- layout/cast/pad 如果进入 IR，应有显式 op 或显式 view，不要靠 runner 侧默默改数组。
- 任何预处理变化都必须同步更新 NumPy reference 构造方式，否则结果比对没有意义。

## 量化与混合精度

nncase 的 PTQ 流程把校准数据、校准方法、量化类型、权重量化类型、误差 dump、量化 scheme 导入/导出等作为显式配置。混合量化文档还支持按层指定范围和数据类型，导出量化 scheme 时需要打开 IR dump。

本仓当前还没有量化主链路，因此不应提前写“支持 PTQ”或“支持混合量化”。但 nncase 的设计给出一个很好的边界样本：

| nncase 做法 | 本仓未来可借鉴口径 |
| --- | --- |
| 量化配置独立于普通编译选项 | dtype/quant profile 不要混进 tile 或 shape 参数 |
| 校准数据通过 PTQ options 进入编译 | 如果未来做量化，校准样本必须是计划/manifest 显式输入 |
| 量化 scheme 可导出和导入 | dtype/range 决策应能复现，不能只存在于一次运行的内存状态 |
| 量化前后有独立 pass 阶段 | 不要在单个 lowering pass 中夹带全局量化决策 |

## 动态 Shape 与 ShapeBucket

nncase 的 ShapeBucket 是一个动态 shape 解决方案。配置中会显式写：

- 是否启用 shape bucket。
- shape 变量的取值范围。
- 每个范围切分的 segment 数。
- 固定 shape 变量映射。

这个设计与本仓近期的 runtime symbolic / random profile 讨论相关。关键启发是：动态 shape 不是“运行时有符号变量”这么简单，还需要区分：

| 概念 | 含义 |
| --- | --- |
| 用户运行时维度 | 实际调用时传入的 shape 或 tile 大小 |
| 编译 profile 范围 | 编译时愿意覆盖的动态维度范围 |
| bucket / segment | 为了优化或生成多个路径而划分的子区间 |
| 固定变量 | 虽然模型维度是 symbol，但某次编译固定为常量 |
| 验证样本 | 每个 bucket 或边界点需要怎样测试 |

对本仓来说，`SymbolDim` 和 runtime tile 只能表达第一类含义；后续如果要做优化选择、kernel variant 或 fill elimination 的 profile 化判断，应另设 profile/bucket 合同，不要把 profile 范围偷偷塞进 `SymbolDim` 名字或 pass 内部默认值。

## Target 边界

nncase 源码中能看到 `TargetIndependentPass`、`TargetDependentPass`、`TargetDependentAfterQuantPass`、`TargetDependentBeforeCodeGen` 等阶段。`CompileSession` 会持有 target 和 compile options，并通过服务体系创建 pass manager。

本仓可以借鉴这个边界，但不必照搬命名。建议未来对 `npu_demo` 形成类似分层：

| 阶段 | 本仓建议职责 |
| --- | --- |
| target-independent semantic stage | 只做不依赖具体硬件的 nn/kernel 语义规整、shape 推导、公共 DCE |
| profile / tuning stage | 处理 tile、runtime symbol、candidate config、shape bucket |
| target-dependent lowering stage | 处理具体 target 的 DMA、memory hierarchy、arch parallel 和 barrier |
| codegen preparation stage | 把 IR 收到源码生成可接受的稳定子集 |
| source/runtime bundle stage | 生成源码、运行命令、验证摘要和 dump manifest |

这能避免“某个 pass 既做语义修复、又做 target lowering、又改 runner 行为”的维护问题。

## Supported Ops 与错误合同

nncase 仓库文档提供 TFLite、ONNX、Caffe 等 supported ops 列表，FAQ 也把 unsupported op 错误作为常见问题说明。这点对本仓 `nn` 层非常有价值。按上文证据边界，Caffe 只作为仓库保留文档事实，不写成 v2 Python wrapper 的已确认导入主路径。

本仓现在 [`spec/operation/nn.md`](../../spec/operation/nn.md) 定义的是高层可调用语义，不等于所有 op 都可 lower 到某个 target。后续建议明确拆两张表：

| 表 | 说明 |
| --- | --- |
| semantic API matrix | `operation/nn` 中哪些函数可调用、shape/dtype/error 如何定义 |
| lowerability matrix | 哪些 `nn` op 在哪个 target / pipeline / dtype / shape 条件下可 lower |

例如 `conv` 在高层语义存在，不应自动推出 `npu_demo` 已有完整 conv codegen。unsupported op 错误也应稳定表达“语义 API 存在但当前 target/pipeline 不支持 lowering”，而不是混成 Python `NotImplementedError` 或底层 pass 崩溃。

## Runtime 与 Simulator

nncase 的 `gencode_tobytes()` 会生成模型产物，`Simulator` 能加载模型、设置输入输出并执行。这提供了模型级闭环：

```text
compile -> model bytes -> simulator runtime -> output verification
```

本仓当前更接近 kernel 级闭环：

```text
dsl_run / lowering -> source.cpp -> local execute -> numpy reference verification
```

两者不是同一种产物，但有共同原则：

- 生成产物必须可定位。
- 运行输入必须可重建。
- 输出校验必须写清参考来源和容差。
- 编译版本、target、profile 和 dump 目录应随结果记录。
- 运行失败要优先报输入 shape/type/layout 或产物版本不匹配这类高层错误，而不是只暴露底层执行失败。

## 对本仓最值得借鉴的点

### 1. 用 manifest 固化 case 合同

当前 `kernel/` 下 demo 已经能 dump 和比对结果，但 case 信息散在脚本参数、随机种子、NumPy 构造和 dump 路径中。借鉴 nncase 的配置对象，后续可以为复杂 case 加 manifest，记录：

- case 名称和 target。
- 输入输出 shape、dtype、layout、stride。
- runtime symbol / shape profile。
- pass pipeline 或 stage 名。
- NumPy reference 和容差。
- dump 产物清单。

### 2. 明确 `nn` semantic 与 lowerability 分离

`operation/nn` 可以继续扩展高层语义，但每次计划都应说明它是否新增 target lowering。否则容易出现“spec 有 API，所以 codegen 应该能跑”的误判。

### 3. 把动态 shape profile 显式化

runtime symbolic demo 如果要继续走向优化，应记录 profile 范围、边界样本和 variant 选择。不要只靠随机 case 名表达覆盖范围。

### 4. 建立 stage 级 dump

复杂 pass 链路应该先看 stage 产物，再看 pass 细节。nncase 的阶段命名和 dump 方式说明，debuggability 是编译器架构的一部分，不是事后日志。

### 5. 把预处理 / layout / cast 作为合同

任何输入输出 layout 或 dtype 变化，都应在 IR 或 manifest 中显式出现，并同步进入 reference 计算。这个原则也适用于 matmul tail view、slice、effective tile 等讨论。

### 6. 目标相关逻辑后移

公共 `nn` 语义不要提前包含 NPU memory pool、DMA barrier 或 target-specific tile 细节。目标相关决策应在明确 target stage 里做，并由对应验收覆盖。

## 不要直接照搬的点

1. 不要把 nncase 的 dotnet / kmodel / simulator runtime 作为本仓当前依赖。
2. 不要把 K230/KPU 闭源插件能力写成可借鉴源码事实。
3. 不要为了参考 nncase 而把本仓从 kernel DSL 直接改成整模型导入器。
4. 不要把输入预处理隐藏进 runner；nncase 的价值恰恰是这些选项可见。
5. 不要把量化决策夹在普通 lowering pass 里；量化需要独立配置、数据和阶段。
6. 不要用 supported ops 文档替代真实验收；可支持矩阵必须绑定 target、dtype、shape 和测试。

## 与本仓模块的具体映射

| nncase 概念 | 本仓现状 | 可借鉴方向 |
| --- | --- | --- |
| `CompileOptions.target` | `set_target("npu_demo")` | target 进入 case manifest 和 dump 摘要 |
| `CompileOptions.dump_ir/dump_dir` | pass manager 与 `kernel/dump` | 增加 stage 级 dump index 和 manifest |
| preprocessing options | 当前主要由 demo 准备输入数组 | 未来 layout/cast/pad 必须显式记录 |
| `PTQTensorOptions` | 暂无量化主链路 | 未来 dtype/quant profile 单独建合同 |
| ShapeBucket | `SymbolDim` / runtime tile demo | 增加 profile range、bucket、边界样本概念 |
| `TargetIndependentPass` | 公共 lowering / canonicalize | 拆清公共语义规整阶段 |
| `TargetDependentPass` | `npu_demo_lowering` 中 target pass | target memory / DMA / arch 逻辑集中后移 |
| supported ops docs | `spec/operation/nn.md` | 补 lowerability matrix，而不是只列 semantic API |
| `Simulator` | `run_numpy_demo` / `dsl_run` | 记录可复现运行输入、产物和容差 |
| kmodel bytes | `source.cpp` / generated bundle | 当前不生成模型包；只借鉴产物记录原则 |

## 可转化为后续计划输入的事项

以下不是当前文档任务的执行范围，只是后续计划可选输入：

1. 为 `nn` 增加 lowerability matrix 文档，区分 semantic API、dialect op、target lowering 和 codegen 支持。
2. 为复杂 `kernel/` demo 增加 case manifest，记录输入、reference、profile、target、dump 和 source bundle。
3. 为 pass pipeline 增加 stage dump 命名合同，把大阶段产物和逐 pass 产物分开。
4. 为 runtime symbolic / random profile case 设计 shape profile 或 bucket 合同，明确范围、边界样本和 variant 选择。
5. 为 layout/cast/pad/view 类输入预处理建立显式合同，避免 runner 侧隐式修改数据。
6. 为未来量化或 mixed dtype 计划单独设计配置和验收，不与 tile tuning 或普通 lowering 混在一起。

## 结论

nncase 对本仓最有价值的参考点不是某个具体 pass 或 runtime，而是它把“模型编译需要的上下文”显式化：输入、target、dump、shape、量化、预处理、stage、产物和验证都有地方落。当前仓库如果继续推进 `nn` case、runtime symbolic 和 `npu_demo` lowering，优先应借鉴这种合同化方式，而不是复制 nncase 的整模型工具链。
