# pass dump xdsl pipeline spec options 计划书 Draft 3-R2

## 文档信息

- 计划用途：让 `dump_dir` 生成的逐 pass IR dump 第一行不再只打印 pass 名称，而是打印 xDSL pipeline pass spec，并包含默认值在内的 pass 选项，方便从 dump 文件直接判断该阶段 IR 对应的 pass 配置。
- 当前状态：Draft 3-R2，已吸收两路 subagent strict review 对 registry frozen fold 写回、`None` option 输出、目标 spec 与门禁的最小需改项；用户已确认 DU1 选择 A，即把当前 spec 写作无参但实现继承接受 `fold` 的 pass 正式收口为 `class XxxPass(fold: bool = True)` 并在 dump marker 中打印 `fold=true/false`。Draft 3-R1 补齐 package/re-export API 快速索引清扫与 `nn_lowering` public-name pytest；Draft 3-R2 修正当前下发前置状态冲突；两路 subagent strict review 最终复核均通过且无阻断、无最小需改项、无待确认项，等待守护最终检验，通过前不得下发 execute。
- 用户确认来源：
  - 2026-06-07 用户指出：当前 dump 文件虽然打印 pass 名字，但没有打印 pass 选项，因此很难判断 IR 是否对应正确配置。
  - 2026-06-07 用户追问是否有类似 `print pass` 的机制，若 xDSL 已有类似能力，直接继承 / 复用会更好。
  - 2026-06-07 本地调研后向用户说明：xDSL `ModulePass.pipeline_pass_spec(include_default=True)` 可生成 `pass-name{field=value ...}`，但当前仓库 pass 多数手写 `__init__`，没有 dataclass 字段，必须按 xDSL 风格迁移具体 pass 才能打印选项。
  - 2026-06-07 用户确认：“可以，按照这个重构，非常好。按照计划书的流程。有冲突我决策。”
  - 2026-06-07 用户确认 DU1 选择 A：当前 spec 写作无参但实现继承接受 `fold` 的 pass，也正式收口为 `class XxxPass(fold: bool = True)`，dump marker 打印 `fold=true/false`。
- 计划文件位置：`ARCHITECTURE/plan/pass_dump_xdsl_pipeline_spec_options.md`。
- 与现有任务关系：
  - 本计划是新的独立计划，不塞入 `T-20260607-3318f2e2 / pass-directory-layout-refactor` 或已完成的 `multi-buffer-emitc-runtime-ring`。
  - 若执行时 `pass-directory-layout-refactor` 已合并，execute 必须先按 latest main 的 canonical pass/spec/test 路径重定位本计划列出的模块；不得恢复旧目录，也不得回退已合并公开 API。

## 目标 spec

- `spec/pass/pass_manager.md`
- `spec/pass/registry.md`
- 公开选项会进入 dump marker 的 pass spec，按 latest main 路径更新。当前根目录基线包括：
  - `spec/pass/arch_parallelize.md`
  - `spec/pass/attach_arch_information.md`
  - `spec/pass/kernel_aggregate.md`
  - `spec/pass/kernel_decompose.md`
  - `spec/pass/lowering/dma_memory_hierarchy/spec.md`
  - `spec/pass/lowering/memory_pool.md`
  - `spec/pass/lowering/nn_lowering/spec.md`
  - `spec/pass/memory_plan.md`
  - `spec/pass/multi_buffer.md`
  - `spec/pass/buffer_results_to_out_params.md`
  - `spec/pass/decompass.md`
  - `spec/pass/dma_alias_to_reinterpret.md`
  - `spec/pass/hoist_dma_alias_ops.md`
  - `spec/pass/inline.md`
  - `spec/pass/outline_device_kernel.md`
  - `spec/pass/producer_consumer_analysis.md`
  - `spec/pass/symbol_buffer_hoist.md`
  - `spec/pass/symbol_hoist_pipeline.md`
  - `spec/pass/symbol_loop_hoist.md`
  - `spec/pass/template_name_infer.md`
  - `spec/pass/tile/analysis.md`
  - `spec/pass/tile/elewise.md`
  - `spec/pass/tile/reduce.md`
  - `spec/pass/kernel_pattern_attach.md`
  - `spec/pass/transform_apply.md`
  - `spec/pass/pipeline/npu_demo_lowering.md`
  - `spec/pass/pipeline/cuda_sm86_lowering.md`
- 若目录重构已合并，上述路径应映射到 `spec/pass/{arch,kernel,memory,tuning}/...` 的最新 canonical 位置，并在任务记录中写明映射。

## 公开 API / 公开行为设计

- 不新增自定义 `print_pass(...)`、`dump_options(...)`、`pass_label(...)` 或同类 public API。
- 复用 xDSL 已有 public API：
  - `ModulePass.pipeline_pass_spec(include_default: bool = False) -> ArgSpec`
  - `ArgSpec.__str__() -> str`
- 本计划改变 `dump_dir` 诊断文件的公开文本行为：
  - pass 后 dump 文件第一行从 `memory-plan` 改为 xDSL pass spec，例如 `memory-plan{insert_free=true fold=false reuse=true auto_pad=false}`。
  - `multi-buffer` 示例：`multi-buffer{memory_stage=2 fold=true target="npu_demo"}`。
  - 无 dataclass 字段 / 无公开选项的 xDSL pass 仍打印 `canonicalize`、`cse` 这类裸 pass 名称。
  - dump 文件名继续使用 pass 名称，如 `02-memory-plan.mlir`，不把 option 写入文件名。
- 为解决用户“看不到默认选项”的痛点，PassManager 必须使用 `include_default=True`。
- xDSL `ArgSpec.__str__()` 使用 Python dataclass 字段名输出 option key，因此 dump marker 使用下划线字段名，如 `memory_stage`、`insert_free`、`auto_pad`；registry / pipeline CLI 中既有的短横线 option spelling，如 `memory-stage`、`insert-free`、`auto-pad`，不因本计划改变。
- xDSL `None` option 使用裸 key 输出。`include_default=True` 下，`MultiBufferPass(target=None)` 应输出类似 `multi-buffer{memory_stage=2 fold=true target}`；`LowerDmaMemoryHierarchyPass(apply_op=None)` 应输出类似 `lower-dma-memory-hierarchy{fold=true apply_op}`。这是 xDSL 原生 `ArgSpec` 表达，不另行改写为 `target=null` 或 `target=None`。
- pass class 构造签名、默认值、`Pass.name`、registry pass name、pipeline name、`from_options(...)` 可接受 option、错误语义和返回值均不得改变。
- 迁移到 xDSL dataclass 风格时，不得把 `fold` 放入基类 dataclass 字段后破坏子类现有 positional 参数顺序；每个具体 pass 必须按当前公开构造签名声明 dataclass 字段。
- 当前 spec/API 列表写作无参但 runtime 已继承接受 `fold: bool = True` 的 pass，按用户 2026-06-07 确认正式补齐为 `class XxxPass(fold: bool = True)`；这属于 spec/API 列表对既有实现签名的收口，不允许顺带新增其它构造参数。
- 若执行发现某个公开构造签名、默认值、错误文本或稳定导入路径必须改变，必须暂停并交用户决策。

## 当前基线

- 本地 xDSL 版本为 `0.62.1`。
- `xdsl.passes.ModulePass` 是 `@dataclass(frozen=True)`，继承 `xdsl.utils.arg_spec.ArgSpecConvertible`。
- xDSL pass 参数模型：
  - 具体 pass 需要是 `@dataclass(frozen=True)`，参数来自 dataclass fields。
  - `pipeline_pass_spec(include_default=True)` 会把默认值也序列化。
  - `ArgSpec.__str__()` 输出 `pass-name{arg=value ...}`；字符串值带双引号，bool 使用 `true/false`。
  - `None` 值输出为裸 key，如 `target`。
  - `ArgSpec.from_spec` 支持把短横线参数名 normalize 成下划线字段名，但反向字符串化使用字段名本身。
- 当前仓库基线：
  - `kernel_gen/passes/pass_manager.py` 当前 dump 文本写法为 `f"{pass_name}\n{IR}"`，第一行不包含 option。
  - `Pass` 当前继承 xDSL `ModulePass`，但手写 `__init__(fold=True)`；多数具体 pass 也手写 `__init__` 并把 option 存入普通实例属性。
  - 因为具体 pass 没有 dataclass 字段，当前 `MemoryPlanPass(...).pipeline_pass_spec(include_default=True)`、`MemoryPoolPass(...)`、`MultiBufferPass(...)` 等只输出裸 pass 名。
  - `MemoryPoolPass` 有公开 summary API：`get_summary(func_name)` 与 `all_summaries()`；其 `_summaries` 是运行后状态，冻结 dataclass 迁移必须保持该公开状态行为。
  - `LowerDmaMemoryHierarchyPass` 有由 `apply_op` 派生的内部 `_rule`；冻结 dataclass 迁移必须用 `init=False` 字段或等价方式处理，不得把 `_rule` 打到 pass spec 中。
  - `test/passes/test_pass_manager.py`、`test/passes/pipeline/test_npu_demo_lowering.py` 和 `test/tools/test_dsl_run.py` 存在基于 dump 第一行 / stage marker 的断言，需要同步改成识别 xDSL pass spec。

## 非目标

- 不新增、修改、删除 `expectation/` 合同资产。
- 不把 `expectation.pass.pipeline` 或任何 pipeline expectation 纳入本计划验收。
- 不改变任何 pipeline pass 顺序或业务 pass 行为。
- 不改 registry option spelling，不把 registry / CLI 的短横线 option 改成下划线 option。
- 不把 dump 文件名改成包含 option 的动态文件名。
- 不引入自定义 pass 打印协议，也不让每个 pass 手写专属打印函数。
- 不重构与 dump option 无关的 pass 算法、IR rewrite、include API、dialect API 或 EmitC 行为。

## 方案比较与选型

### 方案 A：只在 PassManager 用 `__dict__` 拼 options

- 做法：保留当前 pass 手写 `__init__`，dump 时读取实例 `__dict__`。
- 优点：局部改动小。
- 问题：会把 `_summaries`、`_rule` 等内部状态误打印为 option；每个 pass 的 public option / internal state 分界需要重新维护一套规则；和 xDSL pass 生态不一致。
- 结论：不采用。

### 方案 B：新增 `print_pass()` / `dump_options()` public hook

- 做法：在本仓库定义新的 pass 打印 hook，让每个 pass 覆盖。
- 优点：输出格式可完全自定义。
- 问题：新增公开 API，且每个 pass 要维护额外重复逻辑；用户明确倾向复用 xDSL 已有能力。
- 结论：不采用。

### 方案 C：迁移具体 pass 到 xDSL dataclass 参数模型

- 做法：让承载公开构造选项的具体 pass 使用 `@dataclass(frozen=True)` 字段表达 option，PassManager 用 `str(pass_obj.pipeline_pass_spec(include_default=True))` 打 dump marker。
- 优点：直接复用 xDSL 公开 API；option 与 pass 构造字段单源；内部派生状态可用 `init=False` 字段排除；无 option pass 维持裸名称。
- 风险：冻结 dataclass 会影响实例赋值模式；必须保持现有构造签名、默认值、from_options 和 stateful summary 行为。
- 关键配套：registry 当前通用 `fold` 处理会在构造后写回 `pass_obj.fold`；frozen dataclass 迁移必须同步改造 registry fold 覆盖路径，不能让 `pass-specific option + fold=false` 组合失效。
- 本计划采用：方案 C。

## 完成态定义

- 开启 `kernel_gen.core.config.dump_dir` 后：
  - `01-first-ir.mlir` 保持只写初始 IR。
  - 每个 pass 后 dump 文件第一行是 `str(pass_obj.pipeline_pass_spec(include_default=True))`。
  - 文件名仍是 `{index:02d}-{pass-name}.mlir`，例如 `02-memory-plan.mlir`。
- 公开 option-bearing pass 的 xDSL spec 可反映当前实例配置：
  - `MemoryPlanPass(insert_free=True, fold=False, reuse=True, auto_pad=True)` 输出包含 `insert_free=true fold=false reuse=true auto_pad=true`。
  - `MemoryPoolPass(rewrite=True, fold=True, alignment=1024)` 输出包含 `rewrite=true fold=true alignment=1024`，且不包含 `_summaries`。
  - `MultiBufferPass(memory_stage=2, fold=True, target="npu_demo")` 输出包含 `memory_stage=2 fold=true target="npu_demo"`。
  - `MultiBufferPass(memory_stage=2, fold=True, target=None)` 输出包含裸 `target` key，表示 xDSL `None`。
  - `LowerDmaMemoryHierarchyPass(apply_op=...)` 输出包含 `fold` 与 `apply_op`，且不包含 `_rule`。
  - 仅有 `fold` 的 pass 也必须在 dump marker 中打印 `fold=true/false`，但执行不得因此改变 pass 行为。
- 既有 registry 构造、direct constructor、pipeline builder、pytest 和公开错误语义保持兼容。
- dump stage lookup 测试 helper 必须按第一行的 base pass name 识别阶段：`line.split("{", 1)[0]` 应等于 pass name。
- 文件级说明和 `API 列表` 随 touched 实现文件同步更新，说明 dump marker 使用 xDSL pipeline spec。

## 计划级任务

- 计划级任务目标：把 PassManager dump marker 改为 xDSL `pipeline_pass_spec(include_default=True)`，并把 latest main registry / pipeline 可见的全部公开构造参数 pass 迁移为 xDSL dataclass 参数模型，使 dump 文件第一行稳定包含 pass 配置，同时保持构造 API、registry option、pipeline 行为、pytest 和敏感合同资产不变。
- 任务类型：`execute`。
- 固定流转：`execute -> review -> archive_acceptance / 计划书入档验收 -> merge/归档`。
- 当前下发前置：Draft 3-R1 / Draft 3-R2 记录写回与最终复核必须完成两路 subagent strict review 收敛，且所有已发起或计划要求的 subagent review 均无阻断、无最小需改项、无待确认项；随后由 `守护最好的爱莉希雅` 守护最终检验通过，管理员才允许创建唯一计划级 execute。

| 计划任务 | 任务类型 | worktree | 记录文件 |
| --- | --- | --- | --- |
| `pass-dump-xdsl-pipeline-spec-options` | `execute` | 管理员下发的新独立 worktree | `agents/codex-multi-agents/log/task_records/2026/<week>/YYYYMMDD-pass-dump-xdsl-pipeline-spec-options.md` |

## 计划内小任务

### S1：更新 dump marker spec

- 为什么做：先把外部可见 dump 格式写成合同，避免实现阶段只修测试或只拼局部字符串。
- 做什么：更新 `spec/pass/pass_manager.md`，明确 pass 后 dump 第一行为 xDSL pipeline pass spec 且包含默认 option；更新相关 pipeline spec 对 dump marker 的说明。
- 不做什么：不定义新的 pass 打印 API；不改变 dump 文件名；不把 `expectation.pass.pipeline` 纳入验收。
- 怎么验收：spec 中能找到 `pipeline_pass_spec(include_default=True)`、文件名保持 pass name、stage lookup 用 base pass name 的约束。
- 卡住问谁：dump 输出格式、字段名 spelling 或是否包含默认值存在争议时问用户。

详细执行：
1. 在 `spec/pass/pass_manager.md` 的 `dump_dir` 说明中加入 dump marker 格式。
2. 写清 marker 使用 `include_default=True`，并说明 xDSL 字段名使用下划线。
3. 写清 dump 文件名不包含 option，避免路径 churn。
4. 在 `spec/pass/pipeline/npu_demo_lowering.md` 与 `spec/pass/pipeline/cuda_sm86_lowering.md` 中，如已有 dump marker / pass order 说明，改为按 base pass name 识别阶段。
5. 记录本计划不新增 expectation，合同真源为 `spec > pytest > xDSL public API > 当前实现`。

验收：

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/passes/test_pass_manager.py -k dump
```

合同验收：

- 本计划不新增或修改 `expectation/`，S1 无必过 expectation。

### S2：把公开构造参数 pass 迁移到 xDSL dataclass 字段

- 为什么做：xDSL 只能从 dataclass fields 生成 pass spec；当前手写 `__init__` 或继承手写 `Pass.__init__` 会导致 `fold` 与业务 option 丢失。
- 做什么：把 latest main registry / pipeline 可见的公开构造参数 pass 按当前公开构造签名声明为 `@dataclass(frozen=True)`，让 `pipeline_pass_spec(include_default=True)` 可打印 option。
- 不做什么：不改变 pass constructor 参数顺序 / 默认值；不改变 `from_options` 可接受 option；不把内部状态字段打印到 pass spec。
- 怎么验收：相关 pass 的 direct constructor、from_options、registry 构造、pipeline 构造、dump marker 和业务 pytest 均通过；registry builtin pass 中带公开构造参数的 pass 不再输出空 spec。
- 卡住问谁：若 frozen dataclass 与现有公开 stateful API 或构造签名冲突，暂停并问用户决策。

详细执行：
1. 先用 `inspect.signature` 记录 latest main 中 registry builtin pass 与 pipeline 直接使用 pass 的公开构造签名，写入任务记录。
2. 对 latest main registry / pipeline 可见的公开构造参数 pass 迁移 dataclass 字段，当前根目录基线至少覆盖：
   - `AttachArchInformationPass(target: str = "npu_demo", fold: bool = True)`
   - `ArchParallelizePass(target: str = "npu_demo", parallel_level: str = "block")`
   - `BufferResultsToOutParamsPass(fold: bool = True)`
   - `DecompassPass(fold: bool = True)`
   - `DmaAliasToReinterpretPass(fold: bool = True)`
   - `HoistDmaAliasOpsPass(fold: bool = True)`
   - `InlinePass(fold: bool = True)`
   - `KernelAggregatePass(matmul_acc: bool = False, fold: bool = True)`
   - `KernelDecomposePass(fold: bool = True)`
   - `LowerDmaMemoryHierarchyPass(fold: bool = True, apply_op: str | None = None)`
   - `MemoryPlanPass(insert_free: bool = False, fold: bool = True, reuse: bool = False, auto_pad: bool = False)`
   - `MemoryPoolPass(rewrite: bool = False, fold: bool = True, alignment: int = 1024)`
   - `MultiBufferPass(memory_stage: int = 2, fold: bool = True, target: str | None = None)`
   - `NnLoweringPass(fold: bool = True)`
   - registry 内置 smoke pass `_NoOpPass(fold: bool = True)`；类名仍保持 private，不新增公开 import path。
   - `OutlineDeviceKernelPass(fold: bool = True)`
   - `ProducerConsumerAnalysisPass(fold: bool = True)`
   - `SymbolBufferHoistPass(fold: bool = True)`
   - `SymbolHoistPipelinePass(fold: bool = True)`
   - `SymbolLoopHoistPass(fold: bool = True)`
   - `TemplateNameInferPass(fold: bool = True)`
   - `TileAnalysisPass(fold: bool = True)`
   - `TileElewisePass(fold: bool = True)`
   - `TileReducePass(fold: bool = True)`
   - `KernelPatternAttachPass(fold: bool = True)`
   - `TransformApplyPass(fold: bool = True)`
3. 若 execute 发现 registry builtin pass 还有其它公开构造参数类，必须补入迁移与任务记录；若发现该类迁移会改变公开 API，必须暂停并问用户。
4. 对内部派生状态使用 `dataclasses.field(init=False, repr=False, compare=False)` 或等价结构，避免出现在 `pipeline_pass_spec`：
   - `MemoryPoolPass._summaries`
   - `LowerDmaMemoryHierarchyPass._rule`
5. `MemoryPoolPass.apply(...)` 若需要重置 `_summaries`，必须保持 `get_summary(...)` 与 `all_summaries()` 的公开行为；在 frozen dataclass 中可用 `object.__setattr__` 处理内部缓存，但不得把该模式扩散成运行时兼容探测。
6. `LowerDmaMemoryHierarchyPass` 应在 `__post_init__` 或等价结构中由 `apply_op` 计算 `_rule`，并保持非法 `apply_op` 的公开错误语义。
7. `from_options(...)` 继续作为 registry 专属 option 入口；不得用 xDSL `from_pass_spec` 取代已有 registry 错误包裹逻辑，除非能证明错误语义完全不变。
8. 同步改造 `kernel_gen/passes/registry.py` 的通用 `fold` 覆盖路径：
   - 当前 `_set_pass_fold_option(...)` 直接执行 `pass_obj.fold = bool(fold)`，对 frozen dataclass 会失败。
   - execute 必须改成可处理 frozen dataclass 的构造 / 替换策略，并保持非 dataclass 第三方 `ModulePass` 的既有行为。
   - 若采用 `dataclasses.replace(...)`，必须只用于 dataclass pass，且不得改变 pass class、业务 option、错误包装或返回对象类型。
   - 若某个 pass 不支持通用 `fold` 覆盖，必须暂停并问用户；不得静默忽略 `fold=false`。
9. 增加 registry 组合验收：至少覆盖 `build_registered_pass("memory-plan", {"insert-free": "true", "fold": "false"})`、`build_registered_pass("multi-buffer", {"memory-stage": "2", "fold": "false"})`、`build_registered_pass("lower-dma-memory-hierarchy", {"apply_op": "...", "fold": "false"})` 这类 “pass 专属 option + 通用 fold” 组合，确认对象 `fold is False` 且错误语义不变。
10. 更新 touched 实现文件的文件级 `功能说明 / API 列表 / 使用示例 / 关联文件`，并保持 `API 列表` 紧跟 `功能说明`。
11. 同步清扫 package / re-export API 快速索引文件。当前根目录基线至少包括 `kernel_gen/passes/__init__.py`、`kernel_gen/passes/lowering/__init__.py`，以及 touched pass 所在 family 的 `__init__.py` / compat re-export 文件；不得留下 `InlinePass()`、`NnLoweringPass()`、`TileAnalysisPass()`、`TileElewisePass()`、`TileReducePass()`、`OutlineDeviceKernelPass()` 这类与 DU1 A 冲突的旧无参 API 快速索引。
12. 增加旧无参签名残留扫描，至少覆盖：
   - `rg -n "InlinePass\\(\\)|NnLoweringPass\\(\\)|TileAnalysisPass\\(\\)|TileElewisePass\\(\\)|TileReducePass\\(\\)|OutlineDeviceKernelPass\\(\\)" kernel_gen/passes spec/pass test/passes`
   - 允许测试示例中实际构造 `Pass()` 的普通用法，但文件级 API 列表、spec API 列表和公开签名说明不得再把这些 pass 写成无参公开签名。
13. 迁移后用脚本打印每个 touched pass 的 `pipeline_pass_spec(include_default=True)`，确认 public option 出现、`None` 输出为裸 key、内部字段不出现。

验收：

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/passes/test_registry.py
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/passes/test_memory_plan.py test/passes/test_memory_pool.py test/passes/test_multi_buffer.py
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/passes/test_kernel_aggregate.py test/passes/test_kernel_decompose.py test/passes/test_attach_arch_information.py test/passes/test_arch_parallelize.py
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/passes/test_dma_memory_hierarchy.py test/passes/test_kernel_pattern_attach.py test/passes/test_transform_apply.py test/passes/test_producer_consumer_analysis.py
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/passes/test_buffer_results_to_out_params.py test/passes/test_inline.py test/passes/test_outline_device_kernel.py test/passes/test_template_name_infer.py
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/passes/test_dma_alias_to_reinterpret.py test/passes/test_hoist_dma_alias_ops.py test/passes/test_symbol_buffer_hoist.py test/passes/test_symbol_loop_hoist.py test/passes/test_symbol_hoist_pipeline.py
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/passes/tile/test_analysis.py test/passes/tile/test_elewise.py test/passes/tile/test_reduce.py
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/passes/lowering/nn_lowering/test_nn_lowering.py test/passes/lowering/nn_lowering/test_public_name.py
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/repo_conformance/test_private_api_boundaries.py
```

合同验收：

- 本计划不新增或修改 `expectation/`，S2 无必过 expectation。

### S3：让 PassManager dump 使用 xDSL pass spec

- 为什么做：这是用户直接痛点；dump 文件第一行必须包含实际 pass 配置。
- 做什么：在 `kernel_gen/passes/pass_manager.py` 中把 pass 后 dump 第一行改为 `str(item.pipeline_pass_spec(include_default=True))`，并保留文件名用 `item.name`。
- 不做什么：不把 option 写入文件名；不为非 xDSL pass 添加 duck typing；不吞掉 `pipeline_pass_spec` 异常。
- 怎么验收：dump_dir 相关 pytest 覆盖无 option、有 option、默认 option、xDSL 原生 pass 和 fallback pipeline name。
- 卡住问谁：若第三方 `ModulePass` 无法稳定支持 `pipeline_pass_spec`，先问用户是否需要兼容 fallback。

详细执行：
1. 在 PassManager 内部新增仅本文件使用的 helper 或直接内联，生成 pass dump marker。
2. marker 生成优先使用 `item.pipeline_pass_spec(include_default=True)`；由于 `PassManager.add_pass` 已要求 `XdslModulePass`，正常对象都应具备该 API。
3. dump 文件名继续使用 `item.name` 与 `_sanitize_dump_name(...)`。
4. `KernelCodeError` 包裹语义保持不变；pass apply 失败消息仍使用 `item.name`。
5. 更新 `test/passes/test_pass_manager.py`：
   - 无 option pass 仍第一行为裸名称。
   - dataclass option pass 第一行包含全部默认 option。
   - `None` option 第一行按 xDSL 原生裸 key 输出。
   - 文件名不包含 `{...}`。
6. 更新 `test/tools/test_dsl_run.py` 中 dump 相关断言，保留自定义 pipeline fallback `02-pipeline.mlir` 的既有行为。

验收：

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/passes/test_pass_manager.py
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/tools/test_dsl_run.py -k "dump_dir or custom_pipeline_dump"
```

合同验收：

- 本计划不新增或修改 `expectation/`，S3 无必过 expectation。

### S4：更新 pipeline dump marker helper 与回归测试

- 为什么做：pipeline 测试会按 dump 文件第一行定位阶段；第一行带 `{...}` 后，测试应判断 base pass name。
- 做什么：更新 pipeline dump 解析 helper 和相关 pytest，使其既能断言 pass order，又能检查关键 option。
- 不做什么：不改变 pipeline 顺序；不新增或恢复 `expectation.pass.pipeline`；不把 multi-buffer 接入状态从其它计划中带入本计划。
- 怎么验收：npu-demo / cuda-sm86 pipeline dump 测试通过，且至少有一处断言能看到带 option 的 marker。
- 卡住问谁：若 latest main pipeline 顺序与当前 spec 不一致，先暂停并转架构 / 用户裁定，不在本计划顺手改业务 pipeline。

详细执行：
1. 把 stage marker helper 改为同时返回 raw marker 与 base name，或提供明确的 base-name 解析函数。
2. 既有 pass order 断言使用 base name；涉及 option 的新断言使用 raw marker。
3. npu-demo pipeline 中 `memory-plan`、`memory-pool`、`multi-buffer` 等若存在于 latest main，应断言关键 option 可见。
4. npu-demo / cuda-sm86 pipeline 中若出现 `target=None`、`apply_op=None` 或其它 `None` 默认 option，应断言 raw marker 使用裸 key。
5. cuda-sm86 pipeline 如使用 option-bearing pass，也应覆盖至少一个 raw marker。
6. 保持 custom pipeline fallback name、non-module result、source dump 等工具行为不变。

验收：

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/passes/pipeline/test_npu_demo_lowering.py -k "dump or pass_order"
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/passes/pipeline/test_cuda_sm86_lowering.py -k "dump or pass_order"
```

合同验收：

- 本计划不新增或修改 `expectation/`，S4 无必过 expectation。

### S5：Diff 反推自测、门禁与记录闭环

- 为什么做：dataclass 迁移触达多个公开 pass 构造入口，必须用 diff 反推测试证明没有行为回退。
- 做什么：按实际 diff 跑相关 pytest、conformance、文本门禁和 dump marker 脚本；任务记录写清自检、diff 反推自测和不改敏感资产证据。
- 不做什么：不把 expectation 当作 diff 反推测试；不修改 `TODO.md`、`DONE.md` 或本计划文件；不清理无关本地现场。
- 怎么验收：任务记录中 pytest 与文本门禁完整，`expectation/` 无 diff，公开构造签名对比无回退。
- 卡住问谁：若任何 diff 反推测试暴露公开 API 冲突，问用户决策；流程状态问管理员。

详细执行：
1. 运行最低计划 pytest 集合，并按实际 diff 增补 touched pass 的单测。
2. 运行 private API conformance，确保实现和测试没有跨文件调用非公开 helper。
3. 用 `inspect.signature` 对比 touched pass class 构造签名，确认参数顺序和默认值与计划前一致。
4. 用脚本打印 touched pass 的 xDSL spec，确认包含 public option，且不包含 `_summaries`、`_rule` 或其它内部字段。
5. 执行文本门禁：
   - `git diff --check`
   - `git diff --cached --check`
   - `git diff -- .skills expectation agents/standard AGENTS.md TODO.md DONE.md plan/1.md ARCHITECTURE/plan/pass_dump_xdsl_pipeline_spec_options.md`
   - `git status --short --untracked-files=all -- .skills expectation agents/standard AGENTS.md TODO.md DONE.md plan/1.md ARCHITECTURE/plan/pass_dump_xdsl_pipeline_spec_options.md`
6. 任务记录必须写清：
   - 自检
   - Diff 反推自测
   - 合同验收：本计划无必过 expectation，且 `expectation/` 未改
   - 公开 API / 构造签名保持证据
   - dump marker 示例

验收：

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/passes/test_pass_manager.py test/passes/test_registry.py
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/tools/test_dsl_run.py -k "dump_dir or custom_pipeline_dump"
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/passes/pipeline/test_npu_demo_lowering.py -k "dump or pass_order"
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/passes/pipeline/test_cuda_sm86_lowering.py -k "dump or pass_order"
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/repo_conformance/test_private_api_boundaries.py
git diff --check
git diff --cached --check
```

合同验收：

- 本计划无必过 expectation。若 execute 认为必须新增 / 修改 / 删除 `expectation/`，必须暂停并取得用户或架构师明确授权。

## 验收设计

- 最低 pytest：

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/passes/test_pass_manager.py test/passes/test_registry.py
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/tools/test_dsl_run.py -k "dump_dir or custom_pipeline_dump"
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/passes/pipeline/test_npu_demo_lowering.py -k "dump or pass_order"
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/passes/pipeline/test_cuda_sm86_lowering.py -k "dump or pass_order"
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/passes/test_memory_plan.py test/passes/test_memory_pool.py test/passes/test_multi_buffer.py
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/passes/test_kernel_aggregate.py test/passes/test_kernel_decompose.py test/passes/test_attach_arch_information.py test/passes/test_arch_parallelize.py
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/passes/test_dma_memory_hierarchy.py test/passes/test_kernel_pattern_attach.py test/passes/test_transform_apply.py test/passes/test_producer_consumer_analysis.py
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/passes/test_buffer_results_to_out_params.py test/passes/test_inline.py test/passes/test_outline_device_kernel.py test/passes/test_template_name_infer.py
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/passes/test_dma_alias_to_reinterpret.py test/passes/test_hoist_dma_alias_ops.py test/passes/test_symbol_buffer_hoist.py test/passes/test_symbol_loop_hoist.py test/passes/test_symbol_hoist_pipeline.py
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/passes/tile/test_analysis.py test/passes/tile/test_elewise.py test/passes/tile/test_reduce.py
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/passes/lowering/nn_lowering/test_nn_lowering.py test/passes/lowering/nn_lowering/test_public_name.py
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/repo_conformance/test_private_api_boundaries.py
```

- 文本 / 状态门禁：

```bash
git diff --check
git diff --cached --check
git diff -- .skills expectation agents/standard AGENTS.md TODO.md DONE.md plan/1.md ARCHITECTURE/plan/pass_dump_xdsl_pipeline_spec_options.md
git status --short --untracked-files=all -- .skills expectation agents/standard AGENTS.md TODO.md DONE.md plan/1.md ARCHITECTURE/plan/pass_dump_xdsl_pipeline_spec_options.md
```

- 必过合同验收：
  - 本计划无必过 `expectation`。原因：本计划只改变 dump 诊断文本和 pass 参数序列化，当前 `expectation/` 未承载 dump_dir 合同资产；用户未授权本计划新增或修改 expectation。
  - `expectation/` 必须保持无 diff；若后续用户要求补 expectation，则需先修订计划、重跑 strict review 与守护复验。

## 禁止修改面

- `.skills/`
- `expectation/`
- `agents/standard/`
- `AGENTS.md`
- `TODO.md`
- `DONE.md`
- `plan/1.md`
- 本计划文件在 execute 阶段不得修改；若计划需改，暂停后由计划负责人修订并复验。
- 与 pass dump marker 无关的 dialect、EmitC、include runtime、pipeline 业务顺序和历史任务现场。

## 冲突与用户决策点

- 若 xDSL 字段名下划线输出被认为不适合作为 dump 文件可读合同，需要用户决定是否接受自定义映射；默认按用户确认采用 xDSL 原生输出。
- 若某个 pass 迁移 `@dataclass(frozen=True)` 会改变公开 constructor positional order、默认值、稳定错误语义或 import path，必须暂停并问用户。
- 若 registry 通用 `fold` 覆盖不能在 frozen dataclass 下保持 “pass 专属 option + fold=false” 组合语义，必须暂停并问用户。
- 若 `MemoryPoolPass` 的 public summary API 无法在 frozen dataclass 下保持现有行为，必须暂停并问用户。
- 若 latest main 已经因其它任务改动 pipeline 业务顺序，本计划只更新 dump marker 解析；是否同步业务 pipeline 另行问用户。
- 若 reviewer 认为必须新增 / 修改 expectation 才能锁定本计划合同，必须先问用户，不允许 execute 自行写 `expectation/`。

## 用户确认项

- DU1：当前存在若干 pass 的实现签名已接受 `fold: bool = True`，但 spec/API 列表仍写作无参或未显式公开 `fold`，例如 `InlinePass`、`NnLoweringPass`、`TileAnalysisPass`、`TileElewisePass`、`TileReducePass`、`OutlineDeviceKernelPass`。
- 已确认选择：A。
- 用户确认来源：2026-06-07 用户回复 “A”。
- 决策结果：按用户“每个 pass dump 都能看到选项”的目标，把这些实现已接受的继承 `fold` 正式收口进 spec/API 列表，dump marker 打印 `fold=true/false`；execute 同步更新对应 spec 与文件级 API 列表。该确认只覆盖既有实现签名中已接受的 `fold`，不允许顺带新增其它构造参数或改变默认值。
- 待用户确认项：无。

## 迭代审阅记录

### 收敛轮次 1：Draft 1-R1 subagent strict review

- 审阅对象：Draft 1 / Draft 1-R1 全文；最终回执以 Draft 1-R1 为准。
- 输入标准包：
  - 根 `AGENTS.md`
  - 当前 Codex 计划负责人上下文与用户确认来源
  - `agents/standard/计划书标准.md`
  - `agents/standard/spec文件规范.md`
  - `agents/standard/实现文件规范.md`
  - `agents/standard/测试文件约定.md`
  - `agents/standard/任务记录约定.md`
  - `agents/standard/审查规范.md`
  - Draft 1 全文
  - xDSL 本地调研摘要：`ModulePass.pipeline_pass_spec(include_default=True)`、`ArgSpec.__str__()`、dataclass fields、下划线字段名输出
  - Draft 1-R1 自检修订摘要：S2 已从主要 option-bearing pass 扩展为 latest main registry / pipeline 可见的全部公开构造参数 pass，包括 fold-only pass；`MemoryPoolPass._summaries` 与 `LowerDmaMemoryHierarchyPass._rule` 是内部状态风险
  - 禁止修改面与必过 pytest / 文本门禁命令
- 严格通过口径：无未确认公开 API 变更；复用 xDSL public API 而非新增自定义 hook；dataclass 迁移范围足以解决用户痛点；构造签名、registry option 和错误语义保护明确；`expectation/` 只读且无必过入口口径合理；小任务卡可执行；仍有可读性、可维护性、测试有效性或边界完整性返工项则不得通过。
- 审阅任务：
  - `Kierkegaard / 019e9e16-782d-7451-a288-17ebffc15b4d`：最小需改。
  - `Ptolemy / 019e9e16-c5ff-7a42-b1c8-ab46d15020c1`：不通过。
- 发现问题：
  1. Draft 1-R1 要求迁移 frozen dataclass，但未写清 registry 当前通用 `fold` 覆盖仍直接写 `pass_obj.fold`，会导致 pass 专属 option + `fold=false` 组合失效。
  2. Draft 1-R1 未写明 xDSL `None` option 的裸 key 输出规则，`target=None` / `apply_op=None` 会影响公开 dump marker。
  3. Draft 1-R1 将部分当前 spec 写作无参但实现继承接受 `fold` 的 pass 纳入打印范围，公开 API / spec 口径需要用户明确确认或收窄。
  4. Draft 1-R1 目标 spec 漏列 `spec/pass/lowering/nn_lowering/spec.md`。
  5. 文本 / 状态门禁未包含当前计划文件和 untracked 检查。
- 主线处理：
  - Draft 2 已补 S2 registry frozen fold 收口步骤与 pass-specific option + `fold=false` 组合验收。
  - Draft 2 已补 `None` option 输出为裸 key 的公开 dump 合同和 pytest 断言要求。
  - Draft 2 已加入 `spec/pass/lowering/nn_lowering/spec.md`。
  - Draft 2 已补当前计划文件与 untracked 状态门禁。
  - Draft 2 将 fold-only spec/API 口径收为 DU1 待用户确认项，用户确认前不得进入下一轮通过状态。
- 状态：未收敛；等待用户确认 DU1 后修订并发起下一轮 strict review。

### subagent 收敛结论

- 当前状态：Draft 1-R1 两路 strict review 未收敛；Draft 2 已处理技术最小需改项；Draft 3 已按用户确认收口 DU1；Draft 3 strict review 中 Ptolemy 通过、Kierkegaard 提出最小需改；Draft 3-R1 已补 package / re-export API 快速索引清扫与 `nn_lowering` public-name pytest；Draft 3-R2 已补当前下发前置状态冲突。Kierkegaard 与 Ptolemy 两路最终复核均通过，阻断项无、最小需改项无、待确认项无。
- 遗留项：无；允许进入守护最终检验。

### 收敛轮次 2：Draft 3 subagent strict review

- 审阅对象：Draft 3 全文。
- 输入标准包：
  - 根 `AGENTS.md`
  - 当前 Codex 计划负责人上下文与用户确认来源
  - `agents/standard/计划书标准.md`
  - `agents/standard/spec文件规范.md`
  - `agents/standard/实现文件规范.md`
  - `agents/standard/测试文件约定.md`
  - `agents/standard/任务记录约定.md`
  - `agents/standard/审查规范.md`
  - Draft 1-R1 两路 strict review 发现问题
  - Draft 2 / Draft 3 主线处理摘要
  - 禁止修改面与必过 pytest / 文本门禁命令
- 严格通过口径：Draft 1-R1 的 registry frozen fold 写回、`None` option 输出、目标 spec 与门禁问题已被可执行地收口；DU1 已按用户选择 A 收口且不扩大到其它构造参数；无未确认公开 API 变更；`expectation/` 只读且无必过入口口径合理；仍有可读性、可维护性、测试有效性或边界完整性返工项则不得通过。
- 审阅任务：
  - `Kierkegaard / 019e9e16-782d-7451-a288-17ebffc15b4d`：最小需改。
  - `Ptolemy / 019e9e16-c5ff-7a42-b1c8-ab46d15020c1`：通过。
- 发现问题：
  1. Kierkegaard 指出 DU1 A 已要求 fold 签名同步到 spec/API 列表，但 S2 只写 touched 实现文件，未明确清扫 package / re-export API 快速索引；当前 `kernel_gen/passes/__init__.py`、`kernel_gen/passes/lowering/__init__.py` 等仍可能留下 `InlinePass()`、`NnLoweringPass()`、`TileAnalysisPass()` 等旧无参 API 列表。
  2. Kierkegaard 指出 S2 与总体验收未包含 `test/passes/lowering/nn_lowering/test_public_name.py`，`NnLoweringPass(fold: bool = True)` 这类公开名 / export / API 文档收口缺少最近的公开 API 回归。
  3. Ptolemy 核对 Draft 1-R1 的 registry frozen fold、`None` 裸 key、`nn_lowering` spec、DU1 用户确认、门禁和 expectation 口径后通过，无阻断、无最小需改、无待确认。
- 主线处理：
  - Draft 3-R1 已在 S2 增加 package / re-export API 快速索引清扫，当前根目录基线至少包括 `kernel_gen/passes/__init__.py`、`kernel_gen/passes/lowering/__init__.py` 与 touched pass 所在 family 的 `__init__.py` / compat re-export 文件。
  - Draft 3-R1 已增加旧无参签名残留 `rg` 扫描，要求文件级 API 列表、spec API 列表和公开签名说明不得再把相关 pass 写成无参公开签名。
  - Draft 3-R1 已把 `test/passes/lowering/nn_lowering/test_public_name.py` 加入 S2 和总体验收。
- 状态：未完全收敛；Draft 3-R1 需发起记录写回复核。

### 收敛轮次 3：Draft 3-R1 记录写回复核

- 审阅对象：Draft 3-R1 全文。
- 输入标准包：
  - 根 `AGENTS.md`
  - Draft 3 strict review 结果
  - Draft 3-R1 主线处理摘要
  - 用户 DU1 选择 A 确认来源
  - 禁止修改面与必过 pytest / 文本门禁命令
- 严格通过口径：Draft 3-R1 已补齐 package / re-export API 快速索引清扫、旧无参签名残留扫描与 `nn_lowering` public-name pytest；未扩大 DU1 确认范围；无新增待确认项；仍有可执行返工项则不得通过。
- 审阅任务：
  - `Kierkegaard / 019e9e16-782d-7451-a288-17ebffc15b4d`：最小需改。
  - `Ptolemy / 019e9e16-c5ff-7a42-b1c8-ab46d15020c1`：通过。
- 发现问题：
  1. Kierkegaard 指出计划级任务的当前下发前置仍写 “Draft 1 必须完成两路 subagent strict review”，与 Draft 3-R1 当前状态冲突。
  2. Ptolemy 确认 Draft 3-R1 只新增 package / re-export API 快速索引清扫、旧无参签名残留扫描、`test_public_name.py` 验收和记录写回；无阻断、无最小需改、无待确认。
- 主线处理：
  - Draft 3-R2 已把当前下发前置改为：Draft 3-R1 / Draft 3-R2 记录写回复核必须完成两路 subagent strict review 收敛，且所有已发起或计划要求的 subagent review 均无阻断、无最小需改项、无待确认项；随后守护最终检验通过，管理员才允许创建唯一计划级 execute。
- 状态：未完全收敛；Draft 3-R2 需最终复核。

### 收敛轮次 4：Draft 3-R2 最终复核

- 审阅对象：Draft 3-R2 全文。
- 输入标准包：
  - 根 `AGENTS.md`
  - Draft 3-R1 记录写回复核结果
  - Draft 3-R2 当前下发前置修订摘要
  - 用户 DU1 选择 A 确认来源
  - 禁止修改面与必过 pytest / 文本门禁命令
- 严格通过口径：Draft 3-R2 已修正当前下发前置状态冲突；前序所有技术返工项仍收敛；无新增待确认项；仍有可执行返工项则不得通过。
- 审阅任务：
  - `Kierkegaard / 019e9e16-782d-7451-a288-17ebffc15b4d`：最小需改。
  - `Ptolemy / 019e9e16-c5ff-7a42-b1c8-ab46d15020c1`：通过。
- 发现问题：
  1. Kierkegaard 指出计划级任务“当前下发前置”仍只写 `Draft 3-R1 记录写回复核`，未包含 Draft 3-R2 最终复核；记录区已写 Draft 3-R1 / Draft 3-R2，但主任务下发前置仍不完全一致。
  2. Ptolemy 核对 Draft 3-R2 相对 Draft 3-R1 只改状态文字与审阅记录，前序技术收口未被破坏；无阻断、无最小需改、无待确认，并允许进入守护最终检验。
- 主线处理：
  - 已把计划级任务“当前下发前置”修正为：Draft 3-R1 / Draft 3-R2 记录写回与最终复核必须完成两路 subagent strict review 收敛，且所有已发起或计划要求的 subagent review 均无阻断、无最小需改项、无待确认项；随后守护最终检验通过，管理员才允许创建唯一计划级 execute。
- 状态：未完全收敛；需对当前下发前置修正做最终确认。

### 收敛轮次 5：Draft 3-R2 下发前置修正确认

- 审阅对象：Draft 3-R2 下发前置修正版。
- 输入标准包：
  - 根 `AGENTS.md`
  - Draft 3-R2 最终复核结果
  - 当前下发前置修订摘要
  - 禁止修改面与必过 pytest / 文本门禁命令
- 严格通过口径：计划级任务“当前下发前置”与迭代审阅记录均明确 Draft 3-R1 / Draft 3-R2 记录写回与最终复核收敛后才可进入守护；前序技术返工项未被破坏；无新增待确认项。
- 审阅任务：
  - `Kierkegaard / 019e9e16-782d-7451-a288-17ebffc15b4d`：通过。
  - `Ptolemy / 019e9e16-c5ff-7a42-b1c8-ab46d15020c1`：通过。
- 发现问题：无阻断、无最小需改项、无待确认项。
- 主线处理：
  - Kierkegaard 核对当前下发前置已修正为 Draft 3-R1 / Draft 3-R2 记录写回与最终复核需两路 subagent 收敛后才进入守护最终检验；前序技术收口未被破坏；允许进入守护最终检验。
  - Ptolemy 核对当前下发前置、审阅记录写回、xDSL public API 复用、fold 收口、`None` 裸 key合同、re-export/API 清扫、`nn_lowering` public-name pytest、`expectation/` 只读、敏感范围和 untracked 门禁均保留；允许进入守护最终检验。
- 状态：已收敛；允许进入守护最终检验。

### 守护最终检验

- 检验对象：`守护最好的爱莉希雅`。
- 当前状态：待发起。
- 必过门禁：所有已发起或计划要求的 subagent strict review 均无阻断、无最小需改项、无待确认项；用户待决策项为无；本计划不越权修改 `expectation/`；正式下发前计划位置符合 `ARCHITECTURE/plan/` 规则。
- 结论：待检验。
