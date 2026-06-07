# npu_demo_lowering.md

## 功能简介

- 定义 `npu-demo-lowering` pipeline 的公开合同与 pass 顺序。
- 当前文件只公开 pipeline builder：`build_npu_demo_lowering_pipeline(options: dict[str, str] | None = None) -> PassManager`。
- 该 pipeline 面向 `npu_demo` 的 pass/pipeline 正向链路，固定为最小可执行 lowering 组合，并在末尾输出可供 `gen_kernel(...)` / `emit_c(...)` 消费的 host wrapper + device body + `NnMemoryType.template_name` 注解 IR。
- registry 名称 `npu-demo-lowering` 仍属于 [`spec/pass/registry.md`](../../../spec/pass/registry.md) 的公开入口；当前文件不额外公开 builder 之外的模块级 helper。

## API 列表

- `build_npu_demo_lowering_pipeline(options: dict[str, str] | None = None) -> PassManager`

## 文档信息

- 创建者：`未记录`
- 最后一次更改：`小李飞刀`
- `spec`：[`spec/pass/pipeline/npu_demo_lowering.md`](../../../spec/pass/pipeline/npu_demo_lowering.md)
- `功能实现`：[`kernel_gen/pipeline/npu_demo_lowering.py`](../../../kernel_gen/pipeline/npu_demo_lowering.py)
- `test`：[`test/passes/pipeline/test_npu_demo_lowering.py`](../../../test/passes/pipeline/test_npu_demo_lowering.py)

## 依赖

- Pass 管理与排序：[`spec/pass/pass_manager.md`](../../../spec/pass/pass_manager.md)
- 注册表：[`spec/pass/registry.md`](../../../spec/pass/registry.md)
- `inline` 公开入口：[`spec/pass/inline.md`](../../../spec/pass/inline.md)
- xdsl `cse`：`xdsl.transforms.common_subexpression_elimination.CommonSubexpressionElimination`
- xdsl `canonicalize`：`xdsl.transforms.canonicalize.CanonicalizePass`，仅作为本 pipeline 内部阶段使用，不注册为仓库公开 pass。
- `decompass` 公开入口：[`spec/pass/decompass.md`](../../../spec/pass/decompass.md)
- `nn` lowering：[`spec/pass/lowering/nn_lowering/spec.md`](../../../spec/pass/lowering/nn_lowering/spec.md)
- `symbol-hoist-pipeline`：[`spec/pass/symbol_hoist_pipeline.md`](../../../spec/pass/symbol_hoist_pipeline.md)
- `memory-plan`：[`spec/pass/memory/memory_plan.md`](../../../spec/pass/memory/memory_plan.md)
- `tile-analysis`：[`spec/pass/tile/analysis.md`](../../../spec/pass/tile/analysis.md)
- `kernel-pattern-attach`：[`spec/pass/tuning/kernel_pattern_attach.md`](../tuning/kernel_pattern_attach.md)
- `transform-apply`：[`spec/pass/tuning/transform_apply.md`](../tuning/transform_apply.md)
- `lower-dma-memory-hierarchy`：[`spec/pass/tuning/dma_memory_hierarchy.md`](../../../spec/pass/tuning/dma_memory_hierarchy.md)，只由 pattern 函数上的 `kernel.transform_pipeline` 间接触发，不作为本 pipeline 顶层 pass 阶段。
- `symbol-buffer-hoist`：[`spec/pass/symbol_buffer_hoist.md`](../../../spec/pass/symbol_buffer_hoist.md)
- `multi-buffer`：[`spec/pass/memory/multi_buffer.md`](../../../spec/pass/memory/multi_buffer.md)
- `memory-pool`：[`spec/pass/memory/memory_pool.md`](../../../spec/pass/memory/memory_pool.md)
- `attach-arch-information` 公开入口：[`spec/pass/arch/attach_arch_information.md`](../../../spec/pass/arch/attach_arch_information.md)
- `outline-device-kernel` 公开入口：[`spec/pass/tuning/outline_device_kernel.md`](../../../spec/pass/tuning/outline_device_kernel.md)
- `template-name-infer` 公开入口：[`spec/pass/template_name_infer.md`](../../../spec/pass/template_name_infer.md)

## 术语

- `npu-demo-lowering`：`npu_demo` 目标的公开 pipeline 名称。
- `inline`：该 pipeline 的首个内联/展开阶段。
- `cse`：公共子表达式消除阶段；本 pipeline 中五次均紧跟 `canonicalize`，分别服务 inline 展平、三段 `memory-plan -> symbol-hoist-pipeline` 收口和 `memory-pool` 后动态 backing 清理。
- `canonicalize`：xDSL 内置 canonicalization 阶段；只在本 pipeline 内直接实例化 `CanonicalizePass`，不得新增仓库 registry pass 名称；本 pipeline 中共运行五次。
- `lower-nn`：`NnLoweringPass` 的公开 pass 名称。
- `symbol-hoist-pipeline`：`SymbolHoistPipelinePass` 的公开 pass 名称；本 pipeline 中运行三次，内部固定先执行 `dma-alias-to-reinterpret`，再按 `symbol-loop-hoist -> symbol-buffer-hoist -> hoist-dma-alias-ops` 顺序收口 alias、loop-invariant symbol 与 buffer 生命周期。
- `memory-plan`：`MemoryPlanPass` 的公开 pass 名称；本 pipeline 中固定为 `insert_free=True, reuse=True, fold=False, auto_pad=True`，执行三次，均位于对应 `symbol-hoist-pipeline` 之前，用于补齐 `dma.free` 生命周期、启用 padded backing / logical alias 改写并做保守同 owner block 复用。
- `arch-parallelize`：`ArchParallelizePass` 的公开 pass 名称；本 pipeline 中位于 memory-pool 后的 `cse -> canonicalize` 之后、late `attach-arch-information` 之前，固定 `target=<pipeline target>` 与 `parallel_level="block"`；该阶段跳过带 `entry_point` 属性的 host dispatcher，pattern/device 函数继续按 block 级规则分发。
- `multi-buffer`：`MultiBufferPass` 的公开 pass 名称；本 pipeline 中位于第三段 `symbol-hoist-pipeline -> cse -> canonicalize` 之后、`producer-consumer-analysis` 之前，固定 `memory_stage=2` 且使用 pipeline `target` 走 target registry 自动容量口径。
- `producer-consumer-analysis`：`ProducerConsumerAnalysisPass` 的公开 pass 名称；本 pipeline 中位于 `multi-buffer` 之后、`memory-pool` 之前，只写普通或控制流分类分析 attr，不生成同步 op，并保留 typed `dma.alloc` 或 ring 化后的 typed current slot 形态供分析读取。
- `kernel-aggregate`：`KernelAggregatePass` 的公开 pass 名称；本 pipeline 中位于第二段 `symbol-hoist-pipeline -> cse -> canonicalize` 后，固定 `matmul_acc=True`。
- `kernel-decompose`：`KernelDecomposePass` 的公开 pass 名称；本 pipeline 中紧跟 `kernel-aggregate`，在 source/emit 前把 `kernel.matmul_fusion` 分解为动态 acc `kernel.matmul`，不删除 `dma.fill`。
- `tile-analysis`：`TileAnalysisPass` 的公开 pass 名称；本 pipeline 中紧跟第一段 `memory-plan -> symbol-hoist-pipeline -> cse -> canonicalize` cleanup，只补充 tile 分析属性。
- `kernel-pattern-attach`：`KernelPatternAttachPass` 的公开 pass 名称；本 pipeline 中位于 `tile-analysis` 后，负责生成 host dispatcher 与 pattern 函数。
- `transform-apply`：`TransformApplyPass` 的公开 pass 名称；本 pipeline 中位于 `kernel-pattern-attach` 后，负责消费 pattern 函数上的 `kernel.transform_pipeline` 并在 pattern 内执行 lower-dma-memory-hierarchy / canonicalize。
- `lower-dma-memory-hierarchy`：`LowerDmaMemoryHierarchyPass` 的公开 pass 名称；本 pipeline 顶层不直接加入该 pass，只允许由 `transform-apply` 按 pattern attr 间接执行。
- `symbol-buffer-hoist`：`SymbolBufferHoistPass` 的公开 pass 名称；本 pipeline 不再直接插入 standalone `SymbolBufferHoistPass`，只能由 `symbol-hoist-pipeline` 内部按固定 stage 调用公开 pattern 集合。
- `memory-pool`：`MemoryPoolPass` 的公开 pass 名称；本 pipeline 中固定为 `rewrite=True` 且 `alignment=1024`，将片上 `dma.alloc` 改写为 `arch.get_dynamic_memory + dma.reinterpret`，后续紧跟一轮 `cse -> canonicalize`。
- `attach-arch-information`：为目标函数附加 launch / shared memory 等 arch 元信息并特化动态内存容量的阶段；本 pipeline 中仅在 `arch-parallelize` 后、`outline-device-kernel` 前执行，用于特化 memory-pool 新生成的 `arch.get_dynamic_memory`。
- `outline-device-kernel`：将带 arch 元信息的函数 outline 成 host wrapper + device body 的阶段。
- `template-name-infer`：在 pipeline 末尾为 host wrapper 与 device body 的 `nn.memory` 签名写回稳定 C++ template name。

## 目标

- 提供一条默认包含 tile 分析、pattern attach / transform apply 和 memory pool 摘要的公开 pipeline，供本轮 `pytest` 与 standalone 验收链直接复用。
- 明确 `symbol-hoist-pipeline` 在无 `symbol.for` 与无 alias op 时可以 no-op，因此可安全加入该最小 pipeline。
- 明确 `symbol-hoist-pipeline` 紧跟 `lower-nn`，并在同一个 pass 内先完成 lower-nn alias 归一化，再运行 symbol / dma alias hoist pattern。
- 明确 `CommonSubexpressionElimination` 后必须紧跟 `CanonicalizePass`，且 `CanonicalizePass` 只作为本 pipeline 内部 xDSL pass 直接使用，不进入仓库 pass registry。
- 明确每段 `memory-plan` 均固定 `MemoryPlanPass(insert_free=True, reuse=True, fold=False, auto_pad=True)` 并紧跟 `symbol-hoist-pipeline -> cse -> canonicalize`；本 pipeline 固定启用既有 `auto_pad` 能力，不新增 pipeline option。
- 明确 standalone `SymbolBufferHoistPass` 不再作为本 pipeline 顶层阶段出现；buffer 外提只通过 `symbol-hoist-pipeline` 内部 stage 完成。
- 明确 `tile-analysis` 位于第一段 `memory-plan -> symbol-hoist-pipeline -> cse -> canonicalize` 之后、`kernel-pattern-attach` 之前，只记录 tile 分析结果，不生成 tile 循环。
- 明确 `kernel-pattern-attach -> transform-apply` 位于 `tile-analysis` 之后，先生成 pattern dispatcher，再按 pattern attr 分别执行 `lower-dma-memory-hierarchy` 和 `canonicalize`。
- 明确顶层 pipeline 不再直接插入 standalone `LowerDmaMemoryHierarchyPass`；lower-dma 只通过 `kernel.transform_pipeline` 间接作用于 pattern 函数。
- 明确当前 pipeline 在第三段 cleanup 后接入 `MultiBufferPass(memory_stage=2, target=<pipeline target>)`；不新增 pipeline option。
- 明确 `transform-apply` 后再次运行 `memory-plan -> symbol-hoist-pipeline -> cse -> canonicalize -> kernel-aggregate -> kernel-decompose -> memory-plan -> symbol-hoist-pipeline -> cse -> canonicalize -> multi-buffer -> producer-consumer-analysis`，再进入 `MemoryPoolPass(rewrite=True, alignment=1024)`。
- 明确 `kernel-aggregate` 固定 `matmul_acc=True`，只在第二段 `symbol-hoist-pipeline` cleanup 后聚合 matmul tmp+add 中间形态。
- 明确 `kernel-decompose` 紧跟 `kernel-aggregate`，在 `producer-consumer-analysis` 前把 `kernel.matmul_fusion` 分解为动态 acc `kernel.matmul`，不得生成旧 `scf.if` 双分支，且不得删除 `dma.fill`。
- 明确 `kernel-decompose` 后的第三段 `memory-plan -> symbol-hoist-pipeline -> cse -> canonicalize` 负责让 `dma.fill` canonicalization 观察显式 dynamic acc `kernel.matmul`，并删除可证明 dead 的 acc/input/bias staging fill。
- static input + dynamic tile matmul 中，acc fill 删除依赖 runtime tile 参数正数合同；dynamic input + dynamic tile matmul 不假设 dynamic `K > 0`，因此 acc fill 不作为必删项。
- 明确 `producer-consumer-analysis` 位于 `multi-buffer` 之后、`memory-pool` 之前，并在 memory-pool 改写前读取 typed `dma.alloc` 或 ring current 形态。
- 明确 `memory-pool` 位于 `producer-consumer-analysis` 之后，并固定 `MemoryPoolPass(rewrite=True, alignment=1024)`，本 pipeline 默认执行 dynamic backing 改写；该改写直接生成 `dma.reinterpret`，再由后置 `cse -> canonicalize` 清理可合并的公共子表达式与规范化 IR。
- 明确 memory-pool 后运行 `cse -> canonicalize -> arch-parallelize -> attach-arch-information`，其中 late `attach-arch-information` 位于 `arch-parallelize` 后、`outline-device-kernel` 前，用于特化 memory-pool 后新生成的 `arch.get_dynamic_memory`。
- 明确公开 `arch-parallelize` 阶段仍委托 `ArchParallelizePass(target=<pipeline target>, parallel_level="block")` 改写。
- 带 `entry_point` 属性的 host dispatcher 保持 no-op。
- 无 `symbol.for` 的非入口直线 kernel 生成 block0 guard，memory-pool 生成的 loop 前 setup 前缀可通过，配置 / target / unsupported structure 错误仍失败。
- 明确该 pipeline 的最终输出为 host wrapper + device body + template-name 注解 IR，供 `gen_kernel(...)` 直接消费。
- 当输入 DSL callable 除 `lhs/rhs/out` 外还包含公开 `SymbolDim` tile / shape 参数时，pipeline 输出的 host wrapper 与 device body 必须继续保留这些 trailing `!symbol.int` 参数，供 `gen_kernel(...)` 直接消费。
- 保持 `default-lowering` 作为独立公开 builder，不与本 pipeline 混用。

## 额外补充

### 模块级补充

- 本小节只记录模块级非接口补充；接口级参数限制、错误语义、兼容要求与非目标必须维护在对应 API 的 `注意事项`。
- builder 必须返回 `PassManager`。
- builder 必须通过 `register_pipeline("npu-demo-lowering")` 注册。
- builder 允许 `options={"target": "npu_demo"}`，空字典与 `None` 表示默认 target；`only-kernel`、`only_kernel` 或其他选项都必须显式失败。
- 当前文件允许存在用于 pass 顺序、默认 target 或错误文本规整的当前文件内 helper，但这些 helper 不是公开 API；实现、其他模块与测试不得跨文件直连。
- 公开顺序必须固定为：
  1. `InlinePass`
  2. `CommonSubexpressionElimination`
  3. `CanonicalizePass`
  4. `DecompassPass`
  5. `NnLoweringPass`
  6. `MemoryPlanPass(insert_free=True, reuse=True, fold=False, auto_pad=True)`
  7. `SymbolHoistPipelinePass`
  8. `CommonSubexpressionElimination`
  9. `CanonicalizePass`
  10. `TileAnalysisPass`
  11. `KernelPatternAttachPass`
  12. `TransformApplyPass`
  13. `MemoryPlanPass(insert_free=True, reuse=True, fold=False, auto_pad=True)`
  14. `SymbolHoistPipelinePass`
  15. `CommonSubexpressionElimination`
  16. `CanonicalizePass`
  17. `KernelAggregatePass(matmul_acc=True)`
  18. `KernelDecomposePass`
  19. `MemoryPlanPass(insert_free=True, reuse=True, fold=False, auto_pad=True)`
  20. `SymbolHoistPipelinePass`
  21. `CommonSubexpressionElimination`
  22. `CanonicalizePass`
  23. `MultiBufferPass(memory_stage=2, target=<pipeline target>)`
  24. `ProducerConsumerAnalysisPass`
  25. `MemoryPoolPass(rewrite=True, alignment=1024)`
  26. `CommonSubexpressionElimination`
  27. `CanonicalizePass`
  28. `ArchParallelizePass(target=<pipeline target>, parallel_level="block")`
  29. `AttachArchInformationPass`
  30. `OutlineDeviceKernelPass`
  31. `TemplateNameInferPass`
- 该 pipeline 不包含 `tile-elewise`、`tile-reduce` 或 `buffer-results-to-out-params`。
- 若输入 module 中不存在 `symbol.for` 与 alias op，`SymbolHoistPipelinePass` 必须保持 no-op。
- 若输入 module 中不存在可安全外提的 `dma.alloc`，`symbol-hoist-pipeline` 内部 buffer-hoist stage 必须保持 no-op。
- builder 会把默认 `target` 收口为 `npu_demo`。
## API详细说明

### `build_npu_demo_lowering_pipeline(options: dict[str, str] | None = None) -> PassManager`

- api：`build_npu_demo_lowering_pipeline(options: dict[str, str] | None = None) -> PassManager`
- 参数：
  - `options`：pipeline 选项字典；类型 `dict[str, str] | None`；默认值 `None`；当前仅允许 `target` 键；`None` 与空字典表示使用默认 target `"npu_demo"`。
- 返回值：`PassManager`。
- 使用示例：

  ```python
  from kernel_gen.pipeline import build_npu_demo_lowering_pipeline

  pm = build_npu_demo_lowering_pipeline({"target": "npu_demo"})
  module = pm.run(module)
  ```
- 功能说明：构造 `npu-demo-lowering` pipeline，并返回 `PassManager`。
- 注意事项：
  - pipeline 名称必须固定为 `npu-demo-lowering`。
  - pass 顺序必须固定为本文件“公开顺序”列表，不允许由 options 改写。
  - `NnLoweringPass` 后必须先运行 `MemoryPlanPass(insert_free=True, reuse=True, fold=False, auto_pad=True)`，再运行 `SymbolHoistPipelinePass`；该 pass 内必须先纳入 alias 归一 pattern。
  - 每个 `cse` 后必须紧跟 xDSL `CanonicalizePass`；memory-pool 后必须额外运行一轮 `cse -> canonicalize`。
  - 每段 `symbol-hoist-pipeline` 后必须紧跟 `cse -> canonicalize`。
  - `memory-plan` 固定 `insert_free=True, reuse=True, fold=False, auto_pad=True`，并在本 pipeline 中执行三次，均位于对应 `symbol-hoist-pipeline` 前。
  - `auto_pad=True` 使用既有 `memory-plan` padded backing / logical alias 公开语义；pipeline 不接受 `auto-pad` 或 `auto_pad` 等新增 option。
  - `symbol-buffer-hoist` 不得作为 standalone 顶层阶段出现在本 pipeline；安全 `dma.alloc + dma.free` 成对外提只能通过 `symbol-hoist-pipeline` 内部 stage 完成。
  - `tile-analysis` 只添加 `tile.analysis` / `tile.tile_exprs` 等分析属性，不生成 `symbol.for` 或 `dma.view`。
  - 顶层 pipeline 不直接包含 standalone `lower-dma-memory-hierarchy`；该 pass 只由 `transform-apply` 消费 pattern 函数上的 `kernel.transform_pipeline` 间接执行。
  - 当前 pipeline 固定接入 `MultiBufferPass(memory_stage=2, target=<pipeline target>)`；不得为此新增 pipeline option。
  - `transform-apply` 后必须依次运行 `memory-plan -> symbol-hoist-pipeline -> cse -> canonicalize -> kernel-aggregate -> kernel-decompose -> memory-plan -> symbol-hoist-pipeline -> cse -> canonicalize -> multi-buffer -> producer-consumer-analysis -> memory-pool`。
  - `kernel-aggregate` 必须固定 `matmul_acc=True`，不得由 pipeline option 改写。
  - `kernel-decompose` 必须在 `producer-consumer-analysis` 前移除所有 `kernel.matmul_fusion`，输出动态 acc `kernel.matmul`，不得生成旧 `scf.if` 双分支，且不得删除 `dma.fill`。
  - `kernel-decompose` 后的后续 `canonicalize` 必须按 `dma.fill` 合同删除 static/static 与 static/dynamic 中可证明 dead 的 acc/input/bias fill；dynamic/dynamic 不把 acc fill 删除列为通过条件。
  - `producer-consumer-analysis` 位于 `multi-buffer` 之后、`memory-pool` 之前，只写普通或控制流分类分析 attr，不生成 `arch.wait` / `arch.sign`，且该阶段必须仍可观察 typed `dma.alloc` 或 ring current 形态。
  - `memory-pool` 固定 `rewrite=True` 与 `alignment=1024`，将片上 `dma.alloc` 改写为 `arch.get_dynamic_memory + dma.reinterpret`。
  - memory-pool 后必须依次运行 `cse -> canonicalize -> arch-parallelize -> attach-arch-information -> outline-device-kernel -> template-name-infer`。
  - `attach-arch-information` 在本 pipeline 中只保留一次，位于 `arch-parallelize` 后、`outline-device-kernel` 前，并特化 memory-pool 后新生成的 `arch.get_dynamic_memory`。
  - 公开 `arch-parallelize` 阶段必须支持结构改写为 block-strided IR，带 `entry_point` 属性的 host dispatcher 保持 no-op。
  - 无 `symbol.for` 的非入口直线 kernel 生成 block0 guard，memory-pool 生成的 loop 前 setup 前缀可通过，不支持结构按 `ArchParallelizePass` 公开错误失败。
  - `TemplateNameInferPass` 是最后一关注解 pass，之后不得再新增 memory value。
  - `LaunchKernelCostFuncPass` 不属于本 pipeline。
  - `only-kernel`、`only_kernel` 或其他未知 options 输入必须显式失败。
  - options 解析失败必须抛出 `KernelCodeError(ErrorModule.PIPELINE, ...)`，不暴露裸 Python 内置异常。

## 测试

- 测试文件：`test/passes/pipeline/test_npu_demo_lowering.py`
- 执行命令：`pytest -q test/passes/pipeline/test_npu_demo_lowering.py`

### 测试目标

- 验证 `spec/pass/pipeline/npu_demo_lowering.md` 对应公开 API 的正常路径、边界条件与错误语义。
- 验证 pass 或 pipeline 对目标 IR 的改写、no-op 与顺序约束。
- 验证非法输入、边界条件和错误语义按公开合同失败。
- 验证公开导入、注册名、CLI 或命名空间入口只暴露 spec 定义的 API。


### 功能与用例清单

| 用例 ID | 功能 | 场景 | 前置条件 | 操作 | 预期结果 | 建议测试 |
| --- | --- | --- | --- | --- | --- | --- |
| TC-PASS-PIPELINE-NPU-DEMO-LOWERING-001 | pass 改写 | npu demo lowering pipeline builds pass manager | 准备包含目标 op、pass 名称或 pipeline 的公开 IR 输入。 | 运行 `test_npu_demo_lowering_pipeline_builds_pass_manager`。 | IR 改写后的 op、属性、顺序或 no-op 行为体现“npu demo lowering pipeline builds pass manager”场景。 | `test_npu_demo_lowering_pipeline_builds_pass_manager` |
| TC-PASS-PIPELINE-NPU-DEMO-LOWERING-002 | pass 改写 | npu demo lowering pipeline pass order | 准备包含目标 op、pass 名称或 pipeline 的公开 IR 输入。 | 运行 `test_npu_demo_lowering_pipeline_pass_order`。 | 固定顺序包含 `lower-nn -> memory-plan(insert_free=true,reuse=true,fold=false,auto_pad=true) -> symbol-hoist-pipeline -> cse -> canonicalize -> tile-analysis`、`kernel-pattern-attach -> transform-apply -> memory-plan(insert_free=true,reuse=true,fold=false,auto_pad=true) -> symbol-hoist-pipeline -> cse -> canonicalize -> kernel-aggregate -> kernel-decompose -> memory-plan(insert_free=true,reuse=true,fold=false,auto_pad=true) -> symbol-hoist-pipeline -> cse -> canonicalize -> multi-buffer(memory_stage=2,target=npu_demo) -> producer-consumer-analysis -> memory-pool(rewrite=true,alignment=1024)`、`memory-pool -> cse -> canonicalize -> arch-parallelize -> attach-arch-information -> outline-device-kernel -> template-name-infer`，且不包含顶层 standalone `symbol-buffer-hoist`、`dma-alias-to-reinterpret`、`symbol-loop-hoist`、`hoist-dma-alias-ops`、`lower-dma-memory-hierarchy` 或旧 `kernel-matmul-fusion-decompose`。 | `test_npu_demo_lowering_pipeline_pass_order` |
| TC-PASS-PIPELINE-NPU-DEMO-LOWERING-003 | 边界/异常 | npu demo lowering pipeline rejects unknown option | 准备触发该错误路径的公开输入或非法参数组合。 | 运行 `test_npu_demo_lowering_pipeline_rejects_unknown_option`。 | “npu demo lowering pipeline rejects unknown option”场景按公开错误语义失败或被拒绝。 | `test_npu_demo_lowering_pipeline_rejects_unknown_option` |
| TC-PASS-PIPELINE-NPU-DEMO-LOWERING-004 | pass 改写 | npu demo lowering pipeline dynamic acc kernel decompose dump shows lifecycle and pool | 通过公开 dump 配置运行 npu-demo-lowering。 | 运行 `test_npu_demo_lowering_pipeline_dynamic_acc_kernel_decompose_dump_shows_lifecycle_and_pool`。 | 按 dump marker 定位三段 `memory-plan(auto_pad=true)`、三段 `symbol-hoist-pipeline`、`kernel-aggregate`、`kernel-decompose`、`multi-buffer(memory_stage=2,target=npu_demo)`、`producer-consumer-analysis`、`memory-pool(rewrite=true,alignment=1024)`、memory-pool 后 `cse -> canonicalize`、`arch-parallelize`、唯一 `attach-arch-information` 与 `outline-device-kernel`；memory-plan 含 `dma.free`，producer-consumer-analysis 位于 multi-buffer 与 memory-pool 之间，late attach 位于 arch-parallelize 后且 outline 前，并特化 memory-pool 后 `arch.get_dynamic_memory`。 | `test_npu_demo_lowering_pipeline_dynamic_acc_kernel_decompose_dump_shows_lifecycle_and_pool` |
| TC-PASS-PIPELINE-NPU-DEMO-LOWERING-005 | 公开入口 | npu demo lowering pipeline supports kernel contract style public chain | 按 spec 声明的导入路径、CLI 参数、注册名或命名空间访问公开入口。 | 运行 `test_npu_demo_lowering_pipeline_supports_kernel_contract_style_public_chain`。 | 公开入口在“npu demo lowering pipeline supports kernel contract style public chain”场景下可导入、构造、注册或按名称发现。 | `test_npu_demo_lowering_pipeline_supports_kernel_contract_style_public_chain` |
| TC-PASS-PIPELINE-NPU-DEMO-LOWERING-006 | block0 guard / 失败边界 / entry skip | npu demo lowering arch parallelize direct public behavior | 准备无 `symbol.for` 直线函数、多个顶层 `symbol.for`、入口 host + pattern 函数组合三类公开 IR，并在 pipeline 中保留真实 arch-parallelize 阶段。 | 运行 pipeline 中的 no-loop guard、unsupported structure 与入口 skip 三类测试。 | 默认 pipeline 直接使用公开 `ArchParallelizePass`；非入口无 loop 结构写入 block0 guard，不支持结构按公开错误失败，入口 host 不被 block-only guard 或 block-strided rewrite 改写且 pattern 函数仍 rewrite。 | `test_npu_demo_lowering_pipeline_arch_parallelize_wraps_no_loop_body_with_block0_guard`, `test_npu_demo_lowering_pipeline_arch_parallelize_propagates_unsupported_structure`, 入口 skip 测试 |
| TC-PASS-PIPELINE-NPU-DEMO-LOWERING-007 | pass 改写 | npu demo lowering static dump runs multi buffer before pool | 通过公开 dump 配置运行静态 tile matmul。 | 运行 `test_npu_demo_lowering_pipeline_static_dump_runs_multi_buffer_before_pool`。 | 静态 tile matmul 在 `lower-nn -> memory-plan(auto_pad=true) -> symbol-hoist-pipeline` 后先归一 lower-nn alias，并在第一段 cleanup 后进入 pattern attach；`transform-apply -> memory-plan(auto_pad=true) -> symbol-hoist-pipeline -> cse -> canonicalize -> kernel-aggregate -> kernel-decompose -> memory-plan(auto_pad=true) -> symbol-hoist-pipeline -> cse -> canonicalize -> multi-buffer -> producer-consumer-analysis -> memory-pool -> cse -> canonicalize` 后由 `arch.get_dynamic_memory + dma.reinterpret` 承接，static tail 产生的 alloc/free 位于最外层 supported loop 外，且顶层不接入 standalone `symbol-buffer-hoist` / `dma-alias-to-reinterpret` / `symbol-loop-hoist` / `hoist-dma-alias-ops` / `lower-dma-memory-hierarchy`、最终不残留 `kernel.matmul_fusion` 或 `dma.alloc/dma.free`。 | `test_npu_demo_lowering_pipeline_static_dump_runs_multi_buffer_before_pool` |
| TC-PASS-PIPELINE-NPU-DEMO-LOWERING-008 | pass 改写 | static/static、static/dynamic、dynamic/dynamic matmul alloc/free 最外提与 fill 完成态 | 通过公开 demo kernel 与公开 dump 配置运行三类 matmul npu-demo-lowering。 | 运行 `test_npu_demo_lowering_pipeline_matmul_demo_allocs_hoist_for_static_and_dynamic_tiles`。 | 第三段 `symbol-hoist-pipeline` 后三类 pattern 函数内 `dma.alloc/free` 均位于函数首层、`symbol.for` 内不残留 lifecycle op；三类 demo 的 `kernel.matmul` out 均继续消费 logical `dma.reinterpret` alias；static/static 与 static/dynamic 不残留可证明 dead fill；dynamic/dynamic 不做全局 no-fill 断言；`memory-pool` 后不残留 typed alloc/free。 | `test_npu_demo_lowering_pipeline_matmul_demo_allocs_hoist_for_static_and_dynamic_tiles` |
