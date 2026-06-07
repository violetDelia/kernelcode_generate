# Halide 调研与本仓可借鉴点

## 功能简介

- 调研 Halide 的 algorithm / schedule 分离、schedule 原语、bounds inference、simplify placement、storage folding / flattening 和 lowering 边界。
- 为本仓 tile、memory、canonicalize、dynamic shape 和 target lowering 计划提供长期参考。
- 区分 Halide 的图像 / tensor pipeline 语言和本仓当前 DSL / IR / backend demo，避免把外部 schedule language 直接搬入本仓。

## 执行摘要

1. Halide 最值得借鉴的是 algorithm 与 schedule 分离：计算定义保持纯语义，schedule 决定 loop order、tile、vectorize、parallel、compute_at、store_at。
2. bounds 推导是 Halide 能把局部 schedule 转成安全 loop / allocation 的关键基础；它把“需要多少输入区域 / 临时区域”做成编译期分析。
3. `compute_at` / `store_at` 把计算位置和存储位置分开，能显式权衡 locality、重复计算和 storage。
4. storage folding 展示了从访问窗口推导 circular buffer 的方法；storage flattening 则把高层 buffer 形状下沉成后端更容易处理的线性布局。
5. `simplify(...)` 支持在带 bounds / alignment / assumptions 的上下文中做表达式和 statement 化简，提示本仓 cleanup pass 应吃到上下文事实。
6. 对本仓最直接的迁移口径是：不要新增 Halide schedule language，而是把 tile / memory / storage 选择拆成可验证的 IR 属性、pass 和记录。

## 文档信息

- `文档`：[`ARCHITECTURE/reference/reference_project_halide_research.md`](reference_project_halide_research.md)
- `spec`：不适用；本文为外部参考项目调研文档，不对应本仓 `spec` 文件。
- `外部参考`：见下文“外部证据源”，只使用 Halide 官方文档和官方 GitHub 源码。
- `本仓影响`：不修改公开 API、`kernel_gen/`、`spec/`、`test/` 或 `expectation/`。

## 使用示例

- 讨论 tile pass 是否应同时决定算法和调度时，先读“algorithm / schedule 分离”。
- 讨论 dynamic shape、effective tile、memory planning 或 bounds 约束时，先读“bounds inference”。
- 讨论 memory buffer reuse、ring、folding 或 allocation lowering 时，先读“storage folding / flattening”。

## 调研对象与证据边界

本文只读查看官方文档和官方 GitHub 源码，不下载、不 clone、不编译外部项目。Halide `main` 与在线 docs 会持续变化，本文只记录能力类别和设计边界，不固定性能数字或内部 pass 顺序为本仓合同。

### 外部证据源

- Halide 官方仓库 README：<https://github.com/halide/Halide>
- Halide scheduling lesson 05：<https://halide-lang.org/docs/tutorial_2lesson_05_scheduling_1_8cpp-example.html>
- Halide scheduling lesson 08：<https://halide-lang.org/docs/tutorial_2lesson_08_scheduling_2_8cpp-example.html>
- `Halide::Func` API：<https://halide-lang.org/docs/class_halide_1_1_func.html>
- `Schedule.h`：<https://halide-lang.org/docs/_schedule_8h.html>
- `Bounds.h` 官方源码：<https://github.com/halide/Halide/blob/main/src/Bounds.h>
- `Simplify.h` 官方源码：<https://github.com/halide/Halide/blob/main/src/Simplify.h>
- `StorageFolding.cpp` 官方源码：<https://github.com/halide/Halide/blob/main/src/StorageFolding.cpp>
- `StorageFlattening.cpp` 官方源码：<https://github.com/halide/Halide/blob/main/src/StorageFlattening.cpp>
- `Lower.cpp` 官方源码：<https://github.com/halide/Halide/blob/main/src/Lower.cpp>

### 本仓对照点

- [`kernel_gen/passes/lowering/`](../../kernel_gen/passes/lowering)
- [`kernel_gen/passes/memory/`](../../kernel_gen/passes/memory)
- [`kernel_gen/passes/kernel/`](../../kernel_gen/passes/kernel)
- [`kernel_gen/symbol_variable/`](../../kernel_gen/symbol_variable)
- [`kernel/matmul/`](../../kernel/matmul)
- [`kernel/conv2d/`](../../kernel/conv2d)
- [`spec/pass/pipeline/npu_demo_lowering.md`](../../spec/pass/pipeline/npu_demo_lowering.md)

### 证据核对矩阵

| 文档结论 | 官方来源 | 证据边界 |
| --- | --- | --- |
| Halide 使用独立 schedule 改变 loop order、tile、vectorize、parallel | scheduling lesson 05、`Func` API | 只借鉴分层思想，不新增本仓 schedule language |
| `compute_at` / `store_at` 分离计算位置和存储位置 | scheduling lesson 08、`Func` API | 只作为 memory / tile placement 参考 |
| bounds 分析用于推导表达式范围和代码读写区域 | `Bounds.h` | 不说明本仓已有完整 bounds solver |
| storage folding 能把 producer storage 缩成 circular buffer | scheduling lesson 08、`StorageFolding.cpp` | 只借鉴窗口复用思路，不直接复制实现 |
| storage flattening 是后段 lowering 关注点 | `StorageFlattening.cpp`、`Lower.cpp` | 不把高层 IR 提前改成线性 pointer |
| simplify 可利用 bounds、alignment、assumptions | `Simplify.h` | 只提示 cleanup pass 输入事实要显式化 |

## 项目是什么 / 不是什么

| 问题 | 结论 | 本仓解释 |
| --- | --- | --- |
| Halide 是不是 schedule-driven DSL？ | 是 | 用户定义 algorithm，再用 schedule 决定执行组织 |
| Halide 是不是只做 loop 变换？ | 不是 | 它还包含 bounds、storage、simplify、lowering、target codegen 等链路 |
| bounds inference 是不是普通 shape 注释？ | 不是 | 它分析表达式和 statement 读写区域，影响 loop 和 allocation |
| storage folding 是不是简单 ring buffer 语法糖？ | 不是 | 它依赖访问窗口、单 producer、并行边界等安全条件 |
| 是否适合本仓直接接入 Halide？ | 当前不适合 | 会改变 DSL、runtime、schedule 和 target codegen 边界 |

## 可借鉴方法

### 1. algorithm / schedule 分离

Halide lesson 05 展示了同一个 `Func` 可以用 reorder、split、tile、vectorize、unroll、parallel 等 schedule 改变执行形态。对本仓来说，核心不是复制这些 API，而是坚持：

- DSL / high-level op 先表达“算什么”。
- tile、loop placement、memory stage、ring / folding 属于“怎么执行”。
- target resource 参数不要混入普通 runtime symbol。

### 2. compute_at / store_at 是 placement 合同

Halide lesson 08 清楚展示 `compute_at` 与 `store_at` 的差异：计算位置和分配位置可以不同，进而产生 locality、重复计算和 storage 之间的取舍。

本仓迁移时可以把类似信息表达为：

- op / buffer 的生产阶段。
- buffer 的存储生命周期和可复用范围。
- 是否允许跨 tile / loop 复用。
- 并行边界是否阻止复用。

### 3. bounds inference 应作为 pass 的输入事实

`Bounds.h` 中的接口关注表达式上下界、statement 读写区域、box union / overlap 等概念。当前本仓已有 `SymbolDim`、dynamic shape、tile / memory pass，但还缺少统一的 bounds 事实层。

后续计划可以先做小范围事实：

- 一个 tile view 的有效 offset / size / stride。
- 一个 loop 变量的静态 / symbolic 范围。
- 一个 buffer 在当前 stage 的读写 box。

不要一步到位做完整 solver；先让 pass 的前置事实可记录、可测试。

### 4. storage folding 要依赖安全条件

Halide lesson 08 说明 circular buffer folding 不能无条件跨 parallel / vectorized 边界。`StorageFolding.cpp` 也围绕 producer 个数、访问窗口、monotonic、extern consumer 等条件判断。

本仓的 multi-buffer / ring 化计划应借鉴这个态度：

- ring / folding 是 memory rewrite，不是简单把 alloc 名称改掉。
- 必须证明后续读不会被覆盖。
- 必须区分显式要求和自动推导。
- 并行 / target 边界不清时不能自动折叠。

### 5. simplify placement 要吃到上下文

`Simplify.h` 的接口允许传入 bounds、alignment、assumptions。对本仓来说，canonicalize 不能只做局部文本式规则；更稳的是让 simplify / fold 看到明确上下文，例如：

- loop induction var 范围。
- tile extent 和 alignment。
- memory layout / stride 事实。
- target 支持的 dtype / vector width。

## 对本仓的迁移口径

| Halide 方法 | 本仓可迁移口径 | 不改变的边界 |
| --- | --- | --- |
| algorithm / schedule 分离 | 高层 DSL 与 tile / memory / target pass 分层 | 不新增 Halide 式 schedule API |
| compute_at / store_at | 为 producer placement 和 storage lifetime 建立 IR / spec 合同 | 不把 placement 藏进 runner |
| bounds inference | 先记录 loop / tile / buffer box 事实 | 不引入完整外部 solver |
| storage folding | ring / folding 前证明窗口和并行安全 | 不无条件复用 buffer |
| simplify with bounds | cleanup pass 消费显式上下文事实 | 不靠 ad hoc 字符串规则 |

建议本仓按以下顺序吸收：

1. 先给 tile view 和 loop 写清 bounds 事实。
2. 再把 memory lifetime / storage stage 写进 pass 输出。
3. 最后才做 storage folding / ring 化和 target-specific flattening。

## 最不该直接照搬的点

- 不引入 Halide schedule language、autoscheduler 或 runtime。
- 不把 Halide bounds solver 当作本仓现成能力。
- 不把 storage folding 当作无条件 memory optimization。
- 不把高层 `Memory` / `SymbolDim` 过早降成线性 pointer。
- 不把 Halide target codegen 边界套到本仓 `npu_demo` / `cuda_sm86` 后端。

## 自检清单

- 后续计划引用本文时，是否保持 algorithm 和 schedule 分层？
- 是否为 tile / loop / memory rewrite 写清 bounds 输入事实？
- 是否证明 storage folding / ring 化不会覆盖仍会被读取的数据？
- 是否把 simplify 放在拥有足够上下文的阶段？
- 是否避免新增公开 API 或工具参数？
- 是否只把 Halide 作为方法参考，而不是依赖或 runtime 接入方案？
