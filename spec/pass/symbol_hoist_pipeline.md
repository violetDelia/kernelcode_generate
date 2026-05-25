# symbol_hoist_pipeline.md

## 功能简介

- 定义 `symbol-hoist-pipeline` pass 的公开合同。
- 该 pass 在一个 `ModulePass` 内组合 alias 归一、symbol loop hoist 与 dma alias hoist pattern。
- 组合 pass 必须先纳入 `dma-alias-to-reinterpret` 能力，把可归一的 `dma.view` / `dma.reshape` / `dma.subview` 改写为 `dma.reinterpret`，再让后续 hoist pattern 在同一 greedy rewrite 中收敛。
- 旧根模块 `kernel_gen.passes.dma_alias_to_reinterpret`、`kernel_gen.passes.symbol_loop_hoist`、`kernel_gen.passes.hoist_dma_alias_ops`、`kernel_gen.passes.symbol_buffer_hoist` 不保留兼容 shim；hoist 真源路径统一为 `kernel_gen.passes.hoist.*`。

## API 列表

- `class SymbolHoistPipelinePass(fold: bool = True)`
- `SymbolHoistPipelinePass.name: str`
- `SymbolHoistPipelinePass.apply(ctx: Context, module: ModuleOp) -> None`

## 文档信息

- `spec`：`spec/pass/symbol_hoist_pipeline.md`
- `功能实现`：`kernel_gen/passes/hoist/symbol_hoist_pipeline.py`
- `test`：`test/passes/test_symbol_hoist_pipeline.py`

## 依赖

- Pass 管理：`spec/pass/pass_manager.md`
- Pass registry：`spec/pass/registry.md`
- Alias 归一 pattern：`spec/pass/dma_alias_to_reinterpret.md`
- Symbol loop hoist pattern：`spec/pass/symbol_loop_hoist.md`
- DMA alias hoist pattern：`spec/pass/hoist_dma_alias_ops.md`
- Pipeline 使用方：`spec/pass/pipeline/npu_demo_lowering.md`

## 术语

- `symbol-hoist-pipeline`：本 pass 的 registry 名称。
- `alias 归一`：把可精确表达的 `dma.view` / `dma.reshape` / `dma.subview` 收敛为 root source 上的 `dma.reinterpret`。
- `symbol loop hoist`：把 `symbol.for` 内 loop-invariant 的 symbol / tuner / memory query op 外提到 loop 前。
- `dma alias hoist`：把公开 MemoryEffect 可证明安全的 dma alias descriptor 上移，或把 alias 穿过 write-only/no-read writer。
- `fold`：registry 通用 pass option；本 pass 不定义专属 option。

## 目标

- 对外提供一个可注册的 hoist 组合 pass：`SymbolHoistPipelinePass(fold=True)`。
- 不调用旧单 pass 的 `apply(...)`，而是复用公开 pattern getter 构造 combined pattern 列表。
- 在 clone 上执行 rewrite 并验证，验证成功后替换原 module，验证失败时保留原 module。
- 保持 `cse` / `canonicalize` 为 pipeline 外置阶段，不把它们注册或内嵌到本 pass。

## API详细说明

### `class SymbolHoistPipelinePass(fold: bool = True)`

- api：`class SymbolHoistPipelinePass(fold: bool = True)`
- 参数：
  - `fold`：类型 `bool`；默认值 `True`；控制 pass 后通用 folding / DCE sweep 是否启用。
- 返回值：`SymbolHoistPipelinePass` 实例。
- 使用示例：

  ```python
  from kernel_gen.passes.hoist.symbol_hoist_pipeline import SymbolHoistPipelinePass

  pass_obj = SymbolHoistPipelinePass(fold=False)
  ```
- 功能说明：构造 `symbol-hoist-pipeline` pass。
- 注意事项：
  - 本 pass 不接受 `hoist-ops`、`hoist_ops` 或其它专属 option。
  - registry 构造 `build_registered_pass("symbol-hoist-pipeline", {"fold": "false"})` 必须成功。
  - registry 构造 `build_registered_pass("symbol-hoist-pipeline", {"hoist-ops": "dma.fill"})` 必须按 `PassRegistryError: pass 'symbol-hoist-pipeline' does not accept options` 失败。

### `SymbolHoistPipelinePass.name: str`

- api：`SymbolHoistPipelinePass.name: str`
- 返回值：固定字符串 `"symbol-hoist-pipeline"`。
- 使用示例：

  ```python
  from kernel_gen.passes.hoist.symbol_hoist_pipeline import SymbolHoistPipelinePass

  assert SymbolHoistPipelinePass.name == "symbol-hoist-pipeline"
  ```
- 功能说明：公开 registry pass name。
- 注意事项：
  - 不得新增别名 pass name。

### `SymbolHoistPipelinePass.apply(ctx: Context, module: ModuleOp) -> None`

- api：`SymbolHoistPipelinePass.apply(ctx: Context, module: ModuleOp) -> None`
- 参数：
  - `ctx`：xDSL `Context`；用于 dialect 加载和 pattern rewrite。
  - `module`：`ModuleOp`；被改写的目标模块。
- 返回值：`None`。
- 使用示例：

  ```python
  from xdsl.context import Context
  from xdsl.dialects.builtin import ModuleOp
  from kernel_gen.passes.hoist.symbol_hoist_pipeline import SymbolHoistPipelinePass

  module = ModuleOp([])
  SymbolHoistPipelinePass().apply(Context(), module)
  ```
- 功能说明：执行 combined hoist rewrite。
- 注意事项：
  - pattern 列表顺序必须以 alias 归一 pattern 开头，确保后续 hoist pattern 优先看到 `dma.reinterpret` 形态。
  - 若 module verifier 或生成 op verifier 失败，必须抛出 `KernelCodeError(ErrorModule.PASS, "SymbolHoistPipelineVerifierError: ...")`。
  - 不得简单顺序调用 `DmaAliasToReinterpretPass.apply(...)`、`SymbolLoopHoistPass.apply(...)` 或 `HoistDmaAliasOpsPass.apply(...)`。

## 测试

- 测试文件：`test/passes/test_symbol_hoist_pipeline.py`
- 执行命令：`pytest -q test/passes/test_symbol_hoist_pipeline.py`

### 测试目标

- 验证公开 registry 与 canonical import path。
- 验证未知专属 option 的稳定失败短语。
- 验证 combined pass 同时具备 alias 归一与 symbol loop hoist 能力。
- 验证旧根模块路径不再可用，新 `kernel_gen.passes.hoist.*` 真源路径可导入。

### 功能与用例清单

| 用例 ID | 功能 | 场景 | 前置条件 | 操作 | 预期结果 | 建议测试 |
| --- | --- | --- | --- | --- | --- | --- |
| TC-PASS-SYMBOL-HOIST-PIPELINE-001 | 公开入口 | registry 构造 `symbol-hoist-pipeline` | 已加载内置 pass | 运行 `build_registered_pass("symbol-hoist-pipeline", {"fold": "false"})` | 返回 `kernel_gen.passes.hoist.symbol_hoist_pipeline.SymbolHoistPipelinePass` 且 `fold=False` | `test_symbol_hoist_pipeline_registry_and_public_path` |
| TC-PASS-SYMBOL-HOIST-PIPELINE-002 | 边界/异常 | 未确认专属 option | 已加载内置 pass | 运行 `build_registered_pass("symbol-hoist-pipeline", {"hoist-ops": "dma.fill"})` | 按 `PassRegistryError: pass 'symbol-hoist-pipeline' does not accept options` 失败 | `test_symbol_hoist_pipeline_rejects_private_options` |
| TC-PASS-SYMBOL-HOIST-PIPELINE-003 | pass 改写 | 同一 pass 内 alias 归一 + symbol loop hoist | 输入包含 loop 内 `dma.view` 与 loop-invariant `symbol.add` | 运行 `ircheck --pass symbol-hoist-pipeline={fold=false}` | 输出不再保留 `dma.view`；`dma.reinterpret` 与 `symbol.add` 位于 `symbol.for` 之前 | `test_symbol_hoist_pipeline_combines_reinterpret_and_loop_hoist` |
| TC-PASS-SYMBOL-HOIST-PIPELINE-004 | 导入边界 | 旧根路径删除、新路径可导入 | 当前 worktree 已删除旧四个根模块文件 | 运行 registry 导入矩阵测试 | 旧根模块 `find_spec/import_module` 失败，新 `kernel_gen.passes.hoist.*` 路径成功 | `test_hoist_old_root_modules_are_removed`, `test_hoist_new_package_modules_are_public_sources` |
