# pass_manager.md

## 功能简介

- 定义 Pass 管理与调度的最小可用规范，描述 legacy `Pass` 与 xdsl `ModulePass` 的组织、排序与执行规则。
- 面向上层 IR/DSL 的通用优化/规范化流程，不绑定具体 IR 类型或后端。
- 对 analysis pass 仍保持单返回路径：`run(module)` 返回值只承接最终 `module`，分析结果通过 pass 实例缓存或 `attrs` 可观察。

## 文档信息

- 创建者：`李白`
- 最后一次更改：`睡觉小分队`
- `spec`：[`spec/pass/pass_manager.md`](../../spec/pass/pass_manager.md)
- `功能实现`：[`kernel_gen/passes/pass_manager.py`](../../kernel_gen/passes/pass_manager.py)
- `test`：[`test/pass/test_pass_manager.py`](../../test/pass/test_pass_manager.py)

## 依赖

- 无（当前仅定义 Pass 管理抽象，不绑定具体 IR 类型）。

## 目标

- 提供可组合的 Pass 管理器，支持按顺序执行多个 Pass。
- 统一 Pass 的注册、执行与错误传播规则，便于后续实现与测试闭环。
- PassManager 只负责 Pass 编排与执行，不承载默认 pipeline builder；默认 builder 见 [`spec/pass/pipeline/default_lowering.md`](../../spec/pass/pipeline/default_lowering.md)。
- PassManager 在迁移期同时兼容 legacy `Pass.run(target)` 与 xdsl `ModulePass.apply(ctx, module)`；遇到 `ModulePass` 时内部创建并复用单个 `Context`。
- 冻结 analysis pass 在 manager 中的承接方式：`run(module)` 继续返回单一 `module`，不追加 summary 或第二返回值。
- 对 lowering 链固定公开一个可验证顺序示例：当模块内存在 `memory-return func.func + func.call` 链路时，`BufferResultsToOutParamsPass` 必须运行在 `NnLoweringPass` 之后，避免 caller/callee ABI 停留在双口径。
- 对 nn 分解 lowering 链固定公开一个顺序边界：`DecompassPass` 必须运行在 `NnLoweringPass` 之前，确保默认 lowering 链路不让 residual `nn.*` 直接进入 `nn_lowering`。
- 对下游 `gen_kernel` 合同固定明确：`gen_kernel` 仅接受已执行 `BufferResultsToOutParamsPass` 的 rewrite 后 ABI；若仍保留旧 `memory return` ABI，必须显式失败。
- 对显式 memory hierarchy lowering 链固定公开一个扩展顺序边界：当调用方注册 `LowerDmaMemoryHierarchyPass` 时，其位置必须在 `NnLoweringPass` 与 `BufferResultsToOutParamsPass` 之后。
- 对 tile family 固定公开一个顺序边界：`tile-analysis` / `tile-elewise` / `tile-reduce` 必须在 `BufferResultsToOutParamsPass` 之后、`LowerDmaMemoryHierarchyPass` 之前；若同时注册 `SymbolLoopHoistPass`，它必须位于 tile family 之后。

## 限制与边界

- 不定义任何具体 Pass 的业务逻辑，仅规范 Pass 组织与执行流程。
- 不引入跨模块依赖或后端 lowering 规则。
- 不要求 Pass 修改输入的方式（可返回新对象或就地修改），以 `run` 返回值为准。
- 不要求 `ModulePass.apply` 返回值；`PassManager` 以 `apply(ctx, module)` 的副作用作为结果，继续返回原 `module` 对象。
- 当管理器中无 Pass 时，执行结果必须等于输入（无副作用的空操作）。
- 对 analysis pass，manager 不负责聚合第二份分析结果对象；若需观察分析结果，只能经由 pass 实例侧接口或 `attrs` 等副作用读取。
- 当 lowering 链包含 `LowerDmaMemoryHierarchyPass` 时，manager 只冻结其排序边界；是否注册该 pass 仍由调用方决定。
- 当 lowering 链包含 tile family 时，manager 只固定 tile family 与 out-params / dma hierarchy / symbol-loop-hoist 的相对边界；是否注册具体 tile pass 仍由调用方决定。

## 当前调用边界

- `PassManager` 与 legacy `Pass` 的 canonical public path 固定为 `kernel_gen.passes.pass_manager`。
- default / npu-demo pipeline builder 的 canonical public path 固定为 `kernel_gen.passes.pipeline`。
- `LowerDmaMemoryHierarchyPass` 与 `MemoryPoolPass` 的 canonical public path 固定为 `kernel_gen.passes.dma_memory_hierarchy` 与 `kernel_gen.passes.memory_pool`。
- tile family 的 canonical public path 固定为：
  - `kernel_gen.tile.analysis`
  - `kernel_gen.tile.elewise`
  - `kernel_gen.tile.reduce`
- 当前仍允许 pass manager caller 通过下列活跃模块导入 lowering family：
  - `kernel_gen.passes.lowering`
- 以下旧路径在当前基线中必须稳定失败：
  - `kernel_gen.passes.lowering.pass_manager`
  - `kernel_gen.passes.lowering.registry`
  - `kernel_gen.passes.lowering.dma_memory_hierarchy`
  - `kernel_gen.passes.lowering.memory_pool`
  - `kernel_gen.passes.lowering.tile_analysis`
  - `kernel_gen.passes.lowering.tile_elewise`
  - `kernel_gen.passes.lowering.tile_reduce`
- `LowerDmaMemoryHierarchyPass` 与 `MemoryPoolPass` 的调用方不得再把 lowering compat 路径当作主入口；若需要添加这两个 pass，应从上级模块导入后再交给 `PassManager`。

## 公开接口

### `class Pass`

功能说明：

- 表示可执行的单个 Pass。

参数说明：

- `name (str)`：Pass 标识名称，用于诊断与测试断言。

使用示例：

```python
class MyPass(Pass):
    name = "my-pass"
    def run(self, target):
        return target
```

注意事项：

- `run` 必须接收一个输入并返回一个输出对象。
- `name` 需可读且稳定，便于测试匹配。

前置条件：

- 传入 `run` 的对象必须满足该 Pass 的输入类型约束（由具体 Pass 规范定义）。

后置条件：

- `run` 返回值必须可作为下游 Pass 的输入；若无法继续传递必须显式抛错。

返回与限制：

- `run` 返回值作为下游 Pass 的输入。
- `run` 内抛出的异常应向上抛出，管理器不吞异常。

### `class PassManager`

功能说明：

- 维护 Pass 列表并按顺序执行。

参数说明：

- `name (str|None)`：管理器名称，可选，用于调试与日志。

使用示例：

```python
pm = PassManager(name="opt")
pm.add_pass(MyPass())
result = pm.run(ir)
```

```python
pm = PassManager(name="analysis")
cost_pass = AnalyzeFuncCostPass(attach_attrs=True)
pm.add_pass(cost_pass)
module = pm.run(module)
summary = cost_pass.get_summary("main")
```

```python
from xdsl.context import Context
from xdsl.passes import ModulePass

class MyModulePass(ModulePass):
    name = "my-module-pass"

    def apply(self, ctx: Context, module):
        return None

pm = PassManager(name="opt")
pm.add_pass(MyModulePass())
result = pm.run(module)
```

注意事项：

- Pass 执行顺序与添加顺序一致。
- `add_pass` 需要接受 legacy `Pass` 与 xdsl `ModulePass` 两类实例；`run` 执行时按实例类型分别调用 `run(target)` 或 `apply(ctx, module)`。
- 当列表中包含 analysis pass 时，manager 仍只负责串联 `run(target)` 的单返回值流，不新增 `(module, summary)` 一类包装协议。
- 对 `memory-return` lowering 链，当前固定示例顺序是：

```python
pm = PassManager(name="lowering")
pm.add_pass(DecompassPass())
pm.add_pass(NnLoweringPass())
pm.add_pass(BufferResultsToOutParamsPass())
module = pm.run(module)
```

- 当需要显式插入 DMA memory hierarchy lowering 时，顺序固定扩展为：

```python
pm = PassManager(name="lowering")
pm.add_pass(DecompassPass())
pm.add_pass(NnLoweringPass())
pm.add_pass(BufferResultsToOutParamsPass())
pm.add_pass(LowerDmaMemoryHierarchyPass())
module = pm.run(module)
```

前置条件：

- `run` 的输入必须是上游 AST/IR 发射已完成的对象；若输入尚未完成发射，必须由上游阶段抛出错误或中止。

后置条件：

- `run` 返回最后一个 Pass 的输出；当无 Pass 时，返回对象与输入为同一语义对象。

返回与限制：

- `run` 返回最后一个 Pass 的输出；无 Pass 时返回原输入。
- 不得返回 `(module, summary)`、`(target, analysis_result)` 等多返回值结构。

### `PassManager.add_pass(pass_obj)`

功能说明：

- 注册单个 Pass 到管理器。

参数说明：

- `pass_obj (Pass | ModulePass)`：待注册的 Pass 实例。

使用示例：

```python
pm.add_pass(MyPass())
```

注意事项：

- `pass_obj` 必须提供 `name` 属性与 `run(target)` 方法。
- 迁移期也允许 `pass_obj` 是 xdsl `ModulePass` 实例，并通过 `apply(ctx, module)` 执行。

返回与限制：

- 返回 `None`；非法类型应抛出 `TypeError`。

### `PassManager.extend(passes)`

功能说明：

- 批量注册 Pass。

参数说明：

- `passes (Sequence[Pass | ModulePass])`：Pass 列表。

使用示例：

```python
pm.extend([PassA(), PassB()])
```

注意事项：

- 任一元素不满足 `Pass` 约束时必须抛出 `TypeError`。
- 迁移期也必须接受 xdsl `ModulePass` 实例。

返回与限制：

- 返回 `None`。

### `PassManager.run(target)`

功能说明：

- 依序执行所有 Pass。

参数说明：

- `target (object)`：待处理对象（IR/AST 等）。

使用示例：

```python
result = pm.run(ir)
```

```python
module = pm.run(module)
summary = cost_pass.get_summary("main")
```

注意事项：

- Pass 的输出必须作为下一个 Pass 的输入。
- 任何 Pass 抛出的异常应原样传播。
- 若执行的是 analysis pass，分析结果不作为 `run(...)` 的第二返回值传出；调用方应通过 pass 实例或 `analysis.*` attrs 读取。
- 若调用方注册 `LowerDmaMemoryHierarchyPass`，不得把它前移到 `NnLoweringPass` 或 `BufferResultsToOutParamsPass` 之前。

前置条件：

- `target` 必须满足第一个 Pass 的输入约束。

后置条件：

- 若未抛出异常，输出必须满足最后一个 Pass 的输出约束，且可供后续验证/打印阶段使用。

返回与限制：

- 返回最终 Pass 的输出；无 Pass 时返回输入本身。
- 对 analysis pass 仍只返回最终 `module`；不得改为 `new_module, summary = pass_manager.run(module)`。

## 测试

- 测试文件：[`test/pass/test_pass_manager.py`](../../test/pass/test_pass_manager.py)
- 执行命令：`pytest -q test/pass/test_pass_manager.py`

### 测试目标

- 验证 Pass 注册与执行顺序一致。
- 验证空管理器执行返回原输入。
- 验证显式注册非法 Pass 时触发 `TypeError`。
- 验证 Pass 异常可向上抛出。
- 验证 `NnLoweringPass -> BufferResultsToOutParamsPass` 的 lowering 顺序在 `memory-return` 链路上可被测试锁定。
- 验证默认 lowering pipeline 的顺序为 `DecompassPass -> NnLoweringPass -> BufferResultsToOutParamsPass -> LowerDmaMemoryHierarchyPass`。
- 验证 `BufferResultsToOutParamsPass` 置于 `NnLoweringPass` 前会被显式拒绝。
- 当前下游验收标准建议补充 analysis pass 单返回路径验证：`test_pass_manager_runs_analysis_pass_without_second_return` 与 `test_pass_manager_preserves_analysis_side_effects`；在专项测试落地前，不将其写成当前已闭环映射。

### 功能与用例清单

| 用例 ID | 约束点 | 对应测试 |
| --- | --- | --- |
| TC-PASS-001 | 单 Pass 正常执行 | `test_pass_manager_single_pass` |
| TC-PASS-002 | 多 Pass 顺序执行 | `test_pass_manager_multiple_passes_order` |
| TC-PASS-003 | 空管理器返回原输入 | `test_pass_manager_empty_returns_input` |
| TC-PASS-004 | 非法 Pass 类型报错 | `test_pass_manager_invalid_pass_type` |
| TC-PASS-005 | Pass 异常向上抛出 | `test_pass_manager_exception_propagation` |
| TC-PASS-006 | 默认 lowering pipeline 固定顺序 | `test_pass_manager_builds_default_lowering_pipeline_for_buffer_results_to_out_params` |
| TC-PASS-007 | 错误 lowering 顺序显式拒绝 | `test_pass_manager_rejects_buffer_results_to_out_params_before_lowering` |

当前下游验收标准：

- `test_pass_manager_runs_analysis_pass_without_second_return`：输入包含 analysis pass 的 manager；预期 `run(module)` 保持单返回路径。
- `test_pass_manager_preserves_analysis_side_effects`：输入同上；预期分析结果通过 pass 实例或 `attrs` 可观察，而不是 manager 第二返回值。

## 失败归因

- AST 发射失败：上游 DSL/AST 构建阶段无法生成合法 IR，表现为进入 PassManager 前已抛错或传入 `target` 为空/类型不符。
- Dialect verify 失败：某 Pass 调用 verifier 或验证器抛错，原因通常为 IR 类型、attribute 或 operand 约束不满足。
- Lowering 失败：具体 lowering Pass 在 op 映射、类型转换或结果分配时抛错，PassManager 仅负责透传异常，不做吞并或重写。
- Analysis 结果读取失败：若调用方试图从 `run(...)` 第二返回值读取 summary，属于调用协议错误；analysis 结果应改由 pass 实例接口或 `analysis.*` attrs 获取。
