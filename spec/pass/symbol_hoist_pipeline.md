# symbol_hoist_pipeline.md

## 功能简介

- 定义 `symbol-hoist-pipeline` pass 的公开合同。
- 该 pass 在一个 `ModulePass` 内组合 alias 归一、symbol loop hoist、symbol buffer hoist 与 dma alias hoist pattern。
- 组合 pass 必须在 clone 上分两段执行：第一段只运行 `dma-alias-to-reinterpret`，把可归一的 `dma.view` / `dma.reshape` / `dma.subview` 改写为 `dma.reinterpret`；第二段按 `symbol-loop-hoist -> symbol-buffer-hoist -> hoist-dma-alias-ops` 固定 pattern 顺序收敛。
- 组合 rewrite 后按公开 `cse` / `canonicalize` 选项执行 pass-local cleanup；默认两者均开启，`fold` 不控制 cleanup。
- 旧根模块 `kernel_gen.passes.dma_alias_to_reinterpret`、`kernel_gen.passes.symbol_loop_hoist`、`kernel_gen.passes.hoist_dma_alias_ops`、`kernel_gen.passes.symbol_buffer_hoist` 不保留兼容 shim；hoist 真源路径统一为 `kernel_gen.passes.hoist.*`。

## API 列表

- `class SymbolHoistPipelinePass(fold: bool = True, cse: bool = True, canonicalize: bool = True)`
- `SymbolHoistPipelinePass.name: str`
- `SymbolHoistPipelinePass.from_options(options: dict[str, str]) -> SymbolHoistPipelinePass`
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
- Symbol buffer hoist pattern：`spec/pass/symbol_buffer_hoist.md`
- DMA alias hoist pattern：`spec/pass/hoist_dma_alias_ops.md`
- Pipeline 使用方：`spec/pass/pipeline/npu_demo_lowering.md`

## 术语

- `symbol-hoist-pipeline`：本 pass 的 registry 名称。
- `alias 归一`：把可精确表达的 `dma.view` / `dma.reshape` / `dma.subview` 收敛为 root source 上的 `dma.reinterpret`。
- `symbol loop hoist`：把 `symbol.for` 内 loop-invariant 的 symbol / tuner / memory query op 外提到 loop 前。
- `dma alias hoist`：把公开 MemoryEffect 可证明安全的 dma alias descriptor 上移，或把 alias 穿过 write-only/no-read writer。
- `fold`：registry 通用 pass option；只控制 pass 后通用 folding / DCE sweep，不控制本 pass 内嵌 cleanup。
- `cse`：本 pass 专属 bool option；默认 `True`，开启时在组合 rewrite 后运行 xDSL `CommonSubexpressionElimination`。
- `canonicalize`：本 pass 专属 bool option；默认 `True`，开启时在内嵌 CSE 后运行 xDSL `CanonicalizePass`。

## 目标

- 对外提供一个可注册的 hoist 组合 pass：`SymbolHoistPipelinePass(fold=True, cse=True, canonicalize=True)`。
- 不调用旧单 pass 的 `apply(...)`，而是复用公开 pattern getter 构造两段 pattern 列表。
- 在 clone 上执行 rewrite 并验证，验证成功后替换原 module，验证失败时保留原 module。
- 默认在 pass 内嵌 `cse -> canonicalize` cleanup，使单独运行本 pass 后即可观察 cleanup 后 IR。
- 允许 registry 通过 `cse=false` / `canonicalize=false` 独立关闭内嵌 cleanup；`fold=false` 不关闭 cleanup。

## API详细说明

### `class SymbolHoistPipelinePass(fold: bool = True, cse: bool = True, canonicalize: bool = True)`

- api：`class SymbolHoistPipelinePass(fold: bool = True, cse: bool = True, canonicalize: bool = True)`
- 参数：
  - `fold`：类型 `bool`；默认值 `True`；控制 pass 后通用 folding / DCE sweep 是否启用。
  - `cse`：类型 `bool`；默认值 `True`；控制组合 rewrite 后是否运行内嵌 CSE。
  - `canonicalize`：类型 `bool`；默认值 `True`；控制组合 rewrite 后是否运行内嵌 canonicalize。
- 返回值：`SymbolHoistPipelinePass` 实例。
- 使用示例：

  ```python
  from kernel_gen.passes.hoist.symbol_hoist_pipeline import SymbolHoistPipelinePass

  pass_obj = SymbolHoistPipelinePass(fold=False, cse=True, canonicalize=True)
  ```
- 功能说明：构造 `symbol-hoist-pipeline` pass。
- 注意事项：
  - registry 构造 `build_registered_pass("symbol-hoist-pipeline", {"fold": "false", "cse": "false", "canonicalize": "false"})` 必须成功。
  - registry 构造 `build_registered_pass("symbol-hoist-pipeline", {"hoist-ops": "dma.fill"})` 必须按 `PassRegistryError: pass 'symbol-hoist-pipeline' option error: symbol-hoist-pipeline options unknown: hoist-ops` 失败。
  - registry 构造 `build_registered_pass("symbol-hoist-pipeline", {"cse": "maybe"})` 必须按 `PassRegistryError: pass 'symbol-hoist-pipeline' option error: symbol-hoist-pipeline options cse expects bool` 失败。
  - 直接调用 `SymbolHoistPipelinePass.from_options({"fold": "false"})` 必须失败；`fold` 只由 registry 外层解析。

### `SymbolHoistPipelinePass.from_options(options: dict[str, str]) -> SymbolHoistPipelinePass`

- api：`SymbolHoistPipelinePass.from_options(options: dict[str, str]) -> SymbolHoistPipelinePass`
- 参数：
  - `options`：pass 专属选项；只允许 `cse` 与 `canonicalize`，合法值为 `true/false/1/0/yes/no/on/off`。
- 返回值：`SymbolHoistPipelinePass` 实例。
- 使用示例：

  ```python
  from kernel_gen.passes.hoist.symbol_hoist_pipeline import SymbolHoistPipelinePass

  pass_obj = SymbolHoistPipelinePass.from_options({"cse": "false"})
  ```
- 功能说明：承载 registry 透传的 pass 专属 cleanup 选项。
- 注意事项：
  - 未知 option 必须以 `symbol-hoist-pipeline options unknown: <name>` 失败。
  - 非法 bool 文本必须以 `symbol-hoist-pipeline options <name> expects bool` 失败。
  - 该入口不得接受通用 `fold` option。

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
  - 第一段 pattern 列表只能包含 alias 归一 pattern；第二段 pattern 列表必须按 `symbol-loop-hoist -> symbol-buffer-hoist -> hoist-dma-alias-ops` 固定顺序构造，确保 buffer 生命周期外提发生在 alias hoist 前。
  - 第二段 pattern 后按 `cse` / `canonicalize` 选项在 clone 上执行内嵌 cleanup，顺序固定为 `CommonSubexpressionElimination -> CanonicalizePass`。
  - 若 module verifier 或生成 op verifier 失败，必须抛出 `KernelCodeError(ErrorModule.PASS, "SymbolHoistPipelineVerifierError: ...")`。
  - 不得简单顺序调用 `DmaAliasToReinterpretPass.apply(...)`、`SymbolLoopHoistPass.apply(...)`、`SymbolBufferHoistPass.apply(...)` 或 `HoistDmaAliasOpsPass.apply(...)`。

## 测试

- 测试文件：`test/passes/test_symbol_hoist_pipeline.py`
- 执行命令：`pytest -q test/passes/test_symbol_hoist_pipeline.py`

### 测试目标

- 验证公开 registry 与 canonical import path。
- 验证 `cse` / `canonicalize` 专属 option、非法 option 和非法 bool 文本的稳定失败短语。
- 验证内嵌 cleanup 默认开启，且 `fold=False` 不关闭 cleanup。
- 验证 combined pass 具备 alias 归一、symbol loop hoist、symbol buffer hoist 与 dma alias hoist 能力，且失败时回滚原 module。
- 验证旧根模块路径不再可用，新 `kernel_gen.passes.hoist.*` 真源路径可导入。

### 功能与用例清单

| 用例 ID | 功能 | 场景 | 前置条件 | 操作 | 预期结果 | 建议测试 |
| --- | --- | --- | --- | --- | --- | --- |
| TC-PASS-SYMBOL-HOIST-PIPELINE-001 | 公开入口 | registry 构造 `symbol-hoist-pipeline` | 已加载内置 pass | 运行 `build_registered_pass("symbol-hoist-pipeline", {"fold": "false", "cse": "false", "canonicalize": "false"})` | 返回 `kernel_gen.passes.hoist.symbol_hoist_pipeline.SymbolHoistPipelinePass` 且 `fold/cse/canonicalize` 均为 `False` | `test_symbol_hoist_pipeline_registry_and_public_path` |
| TC-PASS-SYMBOL-HOIST-PIPELINE-002 | 边界/异常 | 未确认专属 option / 非法 bool / direct fold option | 已加载内置 pass | 运行 `build_registered_pass("symbol-hoist-pipeline", {"hoist-ops": "dma.fill"})`、`{"cse": "maybe"}` 与 `SymbolHoistPipelinePass.from_options({"fold": "false"})` | 分别按 `symbol-hoist-pipeline options unknown: hoist-ops`、`symbol-hoist-pipeline options cse expects bool`、`symbol-hoist-pipeline options unknown: fold` 失败 | `test_symbol_hoist_pipeline_registry_rejects_invalid_options` |
| TC-PASS-SYMBOL-HOIST-PIPELINE-003 | pass 改写 | 同一 pass 内 alias 归一 + symbol loop hoist | 输入包含 loop 内 `dma.view` 与 loop-invariant `symbol.add` | 运行 `ircheck --pass symbol-hoist-pipeline={fold=false,cse=false,canonicalize=false}` | 输出不再保留 `dma.view`；`dma.reinterpret` 与 `symbol.add` 位于 `symbol.for` 之前 | `test_symbol_hoist_pipeline_combines_reinterpret_and_loop_hoist` |
| TC-PASS-SYMBOL-HOIST-PIPELINE-004 | pass 改写 | 内嵌 cleanup option 独立控制 | monkeypatch xDSL CSE / canonicalize 公开 `apply(...)`。 | 运行 `SymbolHoistPipelinePass(fold=False/cse=False/canonicalize=False).apply(...)` | 默认与 `fold=False` 均调用 `cse -> canonicalize`；`cse=false` 只跳过 CSE；`canonicalize=false` 只跳过 canonicalize；两者 false 时都不调用。 | `test_symbol_hoist_pipeline_cleanup_options_are_independent` |
| TC-PASS-SYMBOL-HOIST-PIPELINE-005 | 导入边界 | 旧根路径删除、新路径可导入 | 当前 worktree 已删除旧四个根模块文件 | 运行 registry 导入矩阵测试 | 旧根模块 `find_spec/import_module` 失败，新 `kernel_gen.passes.hoist.*` 路径成功 | `test_hoist_old_root_modules_are_removed`, `test_hoist_new_package_modules_are_public_sources` |
