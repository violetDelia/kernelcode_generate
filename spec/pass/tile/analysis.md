# tile analysis

## 功能简介

- `tile-analysis` 的实现与公开合同固定收口在 [`kernel_gen/passes/tile/analysis.py`](../../../kernel_gen/passes/tile/analysis.py)。
- 该 pass 只为当前 op 补 `tile.analysis` 与 `tile.tile_exprs`，不生成 `symbol.for`、`dma.view` 或其他 rewrite 结构。
- 对已位于外层 `symbol.for` 中、且 operand shape 已是切后 tile 形状的目标 op，`tile-analysis` 需要把当前 tile 形状直接写回 `tile.tile_exprs`，表达“这个 op 已经被切过”。
- 当前公开 pattern 只包含：
  - `TileAnalysisBinaryPattern`
  - `TileAnalysisBroadcastPattern`
  - `TileAnalysisMatmulPattern`

## API 列表

- `build_registered_pass(name: str, options: dict[str, str] | None = None) -> ModulePass`
- `class TileAnalysisBinaryPattern(RewritePattern)`
- `TileAnalysisBinaryPattern.match_and_rewrite(op: KernelBinaryElewiseOp, rewriter: PatternRewriter) -> None`
- `class TileAnalysisBroadcastPattern(RewritePattern)`
- `TileAnalysisBroadcastPattern.match_and_rewrite(op: DmaBroadcastOp, rewriter: PatternRewriter) -> None`
- `class TileAnalysisMatmulPattern(RewritePattern)`
- `TileAnalysisMatmulPattern.match_and_rewrite(op: KernelMatmulOp, rewriter: PatternRewriter) -> None`
- `class TileAnalysisPass(ModulePass)`
- `TileAnalysisPass.__init__(fold: bool = True) -> None`
- `TileAnalysisPass.apply(ctx: Context, module: ModuleOp) -> None`
- `get_tile_analysis_pass_patterns() -> list[RewritePattern]`

## 文档信息

- 创建者：`未记录`
- 最后一次更改：`小李飞刀`
- `spec`：[`spec/pass/tile/analysis.md`](../../../spec/pass/tile/analysis.md)
- `功能实现`：
  - [`kernel_gen/passes/registry.py`](../../../kernel_gen/passes/registry.py)
  - [`kernel_gen/passes/tile/analysis.py`](../../../kernel_gen/passes/tile/analysis.py)
- `test`：
  - [`test/passes/tile/test_analysis.py`](../../../test/passes/tile/test_analysis.py)
  - [`test/dsl/gen_kernel/test_gen_kernel.py`](../../../test/dsl/gen_kernel/test_gen_kernel.py)

## 依赖

- tile family 同级合同：[`spec/pass/tile/elewise.md`](../../../spec/pass/tile/elewise.md)、[`spec/pass/tile/reduce.md`](../../../spec/pass/tile/reduce.md)
- pass 执行器：[`spec/pass/pass_manager.md`](../../../spec/pass/pass_manager.md)
- 注册表：[`spec/pass/registry.md`](../../../spec/pass/registry.md)

## 目标

- 保持公开 pass 名固定为 `tile-analysis`。
- 保持当前文件内公开 API 只覆盖 pass、getter 和 3 个 pattern。
- 只为当前命中的 op 补 analysis 属性，不隐式改写所属函数的 loop/view 结构。
- 顶层未切分 op 保持空 `tile.tile_exprs`；已落在 `symbol.for` 内、且当前 memory shape 已收口为 tile 形状的目标 op，必须把当前 tile 形状写入其非 `expand` 维对应的 `tile.tile_exprs`。
- 对 `dma.broadcast`，`expand` 维不参与 `tile.tile_exprs` 写回：该维在 target/source 两行都必须保持空字符串；其余非 `expand` 维需要在 target/source 两行都写入当前 tile 形状。
- 若外层 loop 只切了部分维度，则 `tile.tile_exprs` 只能写入与祖先 `symbol.for step` 对应的那些维；未被 loop `step` 覆盖的维必须继续保持空字符串。
- 对 `kernel.matmul`，reduce(K) 轴的 loop step 不能写入 `tile.tile_exprs`；只有命中 `M/N` 的祖先 loop step 才能分别写回到 `lhs/out` 的 `M` 位与 `rhs/out` 的 `N` 位。若只切 K，3 行都必须保持空；若切 `K+N`，也只能写回 `N`。

## API详细说明

### `build_registered_pass(name: str, options: dict[str, str] | None = None) -> ModulePass`

- api：`build_registered_pass(name: str, options: dict[str, str] | None = None) -> ModulePass`
- 参数：
  - `name`：公开名称、符号名或注册名，用于查找、打印、注册或生成稳定标识；类型 `str`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
  - `options`：IR operation；类型 `dict[str, str] | None`；默认值 `None`；允许 `None`/空值仅用于签名或默认值显式声明的可选场景；按可变容器传入时，是否修改输入必须以本接口功能说明和注意事项为准；非法值按该 API 的公开错误语义处理。
- 返回值：`ModulePass`。
- 使用示例：

  ```python
  result = build_registered_pass(name=name, options=None)
  ```
- 功能说明：构建 `registered_pass`。
- 注意事项：注册名必须稳定；重复注册、未知名称或非法 options 必须按公开错误语义处理。

### `class TileAnalysisBinaryPattern(RewritePattern)`

- api：`class TileAnalysisBinaryPattern(RewritePattern)`
- 参数：无。
- 返回值：`TileAnalysisBinaryPattern` 实例。
- 使用示例：

  ```python
  tile_analysis_binary_pattern = TileAnalysisBinaryPattern()
  ```
- 功能说明：定义 `TileAnalysisBinaryPattern` rewrite pattern 对象。
- 注意事项：构造参数必须符合本条目参数说明；实例内部缓存、状态字典和派生字段不作为外部可变入口。

### `TileAnalysisBinaryPattern.match_and_rewrite(op: KernelBinaryElewiseOp, rewriter: PatternRewriter) -> None`

- api：`TileAnalysisBinaryPattern.match_and_rewrite(op: KernelBinaryElewiseOp, rewriter: PatternRewriter) -> None`
- 参数：
  - `op`：IR operation，作为 emit、rewrite、lowering 或校验的当前处理对象；类型 `KernelBinaryElewiseOp`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
  - `rewriter`：公开 rewrite 对象，用于替换、插入或删除 IR operation；类型 `PatternRewriter`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
- 返回值：无返回值；调用成功表示操作完成。
- 使用示例：

  ```python
  tile_analysis_binary_pattern = tile_analysis_binary_pattern
  tile_analysis_binary_pattern.match_and_rewrite(op=op, rewriter=rewriter)
  ```
- 功能说明：使用 `TileAnalysisBinaryPattern` 匹配目标 operation 并执行 rewrite。
- 注意事项：非法输入必须按本条目参数说明和公开错误语义处理；调用方不得依赖实现内部状态。

### `class TileAnalysisBroadcastPattern(RewritePattern)`

- api：`class TileAnalysisBroadcastPattern(RewritePattern)`
- 参数：无。
- 返回值：`TileAnalysisBroadcastPattern` 实例。
- 使用示例：

  ```python
  tile_analysis_broadcast_pattern = TileAnalysisBroadcastPattern()
  ```
- 功能说明：定义 `TileAnalysisBroadcastPattern` rewrite pattern 对象。
- 注意事项：构造参数必须符合本条目参数说明；实例内部缓存、状态字典和派生字段不作为外部可变入口。

### `TileAnalysisBroadcastPattern.match_and_rewrite(op: DmaBroadcastOp, rewriter: PatternRewriter) -> None`

- api：`TileAnalysisBroadcastPattern.match_and_rewrite(op: DmaBroadcastOp, rewriter: PatternRewriter) -> None`
- 参数：
  - `op`：IR operation，作为 emit、rewrite、lowering 或校验的当前处理对象；类型 `DmaBroadcastOp`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
  - `rewriter`：公开 rewrite 对象，用于替换、插入或删除 IR operation；类型 `PatternRewriter`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
- 返回值：无返回值；调用成功表示操作完成。
- 使用示例：

  ```python
  tile_analysis_broadcast_pattern = tile_analysis_broadcast_pattern
  tile_analysis_broadcast_pattern.match_and_rewrite(op=op, rewriter=rewriter)
  ```
- 功能说明：使用 `TileAnalysisBroadcastPattern` 匹配目标 operation 并执行 rewrite。
- 注意事项：非法输入必须按本条目参数说明和公开错误语义处理；调用方不得依赖实现内部状态。

### `class TileAnalysisMatmulPattern(RewritePattern)`

- api：`class TileAnalysisMatmulPattern(RewritePattern)`
- 参数：无。
- 返回值：`TileAnalysisMatmulPattern` 实例。
- 使用示例：

  ```python
  tile_analysis_matmul_pattern = TileAnalysisMatmulPattern()
  ```
- 功能说明：定义 `TileAnalysisMatmulPattern` rewrite pattern 对象。
- 注意事项：构造参数必须符合本条目参数说明；实例内部缓存、状态字典和派生字段不作为外部可变入口。

### `TileAnalysisMatmulPattern.match_and_rewrite(op: KernelMatmulOp, rewriter: PatternRewriter) -> None`

- api：`TileAnalysisMatmulPattern.match_and_rewrite(op: KernelMatmulOp, rewriter: PatternRewriter) -> None`
- 参数：
  - `op`：IR operation，作为 emit、rewrite、lowering 或校验的当前处理对象；类型 `KernelMatmulOp`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
  - `rewriter`：公开 rewrite 对象，用于替换、插入或删除 IR operation；类型 `PatternRewriter`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
- 返回值：无返回值；调用成功表示操作完成。
- 使用示例：

  ```python
  tile_analysis_matmul_pattern = tile_analysis_matmul_pattern
  tile_analysis_matmul_pattern.match_and_rewrite(op=op, rewriter=rewriter)
  ```
- 功能说明：使用 `TileAnalysisMatmulPattern` 匹配目标 operation 并执行 rewrite。
- 注意事项：非法输入必须按本条目参数说明和公开错误语义处理；调用方不得依赖实现内部状态。

### `class TileAnalysisPass(ModulePass)`

- api：`class TileAnalysisPass(ModulePass)`
- 参数：无。
- 返回值：`TileAnalysisPass` 实例。
- 使用示例：

  ```python
  tile_analysis_pass = TileAnalysisPass()
  ```
- 功能说明：定义 `TileAnalysisPass` pass 对象。
- 注意事项：构造参数必须符合本条目参数说明；实例内部缓存、状态字典和派生字段不作为外部可变入口。

### `TileAnalysisPass.__init__(fold: bool = True) -> None`

- api：`TileAnalysisPass.__init__(fold: bool = True) -> None`
- 参数：
  - `fold`：`fold` 输入值，参与 `__init__` 的公开处理流程；类型 `bool`；默认值 `True`；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
- 返回值：无返回值；调用成功表示操作完成。
- 使用示例：

  ```python
  tile_analysis_pass = TileAnalysisPass(fold=True)
  ```
- 功能说明：执行 `__init__`。
- 注意事项：该特殊方法只承接 Python 对应协议语义；不得额外暴露内部字段。

### `TileAnalysisPass.apply(ctx: Context, module: ModuleOp) -> None`

- api：`TileAnalysisPass.apply(ctx: Context, module: ModuleOp) -> None`
- 参数：
  - `ctx`：公开上下文对象，提供代码生成、emit、pass 或工具执行所需的配置与状态；类型 `Context`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
  - `module`：模块级 IR 对象，作为 pass、校验或代码生成的处理主体；类型 `ModuleOp`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
- 返回值：无返回值；调用成功表示操作完成。
- 使用示例：

  ```python
  tile_analysis_pass = tile_analysis_pass
  tile_analysis_pass.apply(ctx=ctx, module=module)
  ```
- 功能说明：对模块执行 `TileAnalysisPass` pass。
- 注意事项：非法输入必须按本条目参数说明和公开错误语义处理；调用方不得依赖实现内部状态。

### `get_tile_analysis_pass_patterns() -> list[RewritePattern]`

- api：`get_tile_analysis_pass_patterns() -> list[RewritePattern]`
- 参数：无。
- 返回值：`list[RewritePattern]`。
- 使用示例：

  ```python
  from kernel_gen.passes.tile.analysis import get_tile_analysis_pass_patterns

  patterns = get_tile_analysis_pass_patterns()
  ```
- 功能说明：返回 `tile-analysis` 使用的公开 pattern 列表。
- 注意事项：pattern getter 的稳定顺序固定为 `Binary -> Broadcast -> Matmul`；3 个 pattern 都是 op-level pattern，只处理当前命中的目标 op；返回列表不承诺可被调用方原地修改后影响 pass 行为。


## 额外补充

### 模块级补充

### `build_registered_pass("tile-analysis")`

- 功能说明：

- 构造 `tile-analysis` 的公开 `ModulePass`。

- 使用示例：

```python
from xdsl.context import Context
from xdsl.dialects.builtin import ModuleOp
from kernel_gen.passes.registry import build_registered_pass

module = ModuleOp([])
build_registered_pass("tile-analysis").apply(Context(), module)
```

### `kernel_gen.passes.tile.analysis`

- 功能说明：

- 当前文件公开对象集合固定为：
  - `TileAnalysisBinaryPattern`
  - `TileAnalysisBroadcastPattern`
  - `TileAnalysisMatmulPattern`
  - `TileAnalysisPass`
  - `get_tile_analysis_pass_patterns()`

- 使用示例：

```python
from kernel_gen.passes.tile.analysis import (
    TileAnalysisBinaryPattern,
    TileAnalysisPass,
    get_tile_analysis_pass_patterns,
)

patterns = get_tile_analysis_pass_patterns()
assert type(patterns[0]) is TileAnalysisBinaryPattern
```

- 返回值：

- pattern getter 的稳定顺序固定为 `Binary -> Broadcast -> Matmul`。
- 3 个 pattern 都是 op-level pattern，只处理当前命中的目标 op。
- 对 `kernel.binary_elewise`，若当前 op 已位于 `symbol.for` 内，则三行 `tile.tile_exprs` 都直接写当前 memory shape 维度。
- 对 `dma.broadcast`，若当前 op 已位于 `symbol.for` 内，则 target 行写当前 target tile 形状，source 行仅在非 `expand` 维写当前 source tile 形状。
- `TileAnalysisMatmulPattern` 固定使用逻辑角色顺序 `lhs/rhs/out` 写入 matmul 三行属性：
  - `tile.analysis` 固定为 `["elewise", "reduce"] / ["reduce", "elewise"] / ["elewise", "elewise"]`
  - 顶层未切分 matmul 的 `tile.tile_exprs` 保持空字符串矩阵
  - 已位于 `symbol.for` 内、且当前 shape 已是 tile 形状的 matmul，`tile.tile_exprs` 必须写成 `lhs=[M_tile, ""] / rhs=["", N_tile] / out=[M_tile, N_tile]`

### helper 说明

- 当前文件内除上述 5 个公开对象外，不再承诺任何其他稳定 helper。
- 跨文件实现不得调用本文件未列入公开 API 集合的名字。
- 测试不得把未列入公开 API 集合的名字当作公开接口断言。

## 测试

- 测试文件：
  - `test/dsl/gen_kernel/test_gen_kernel.py`
  - `test/passes/tile/test_analysis.py`
- 执行命令：
  - `pytest -q test/passes/tile/test_analysis.py`
  - `pytest -q test/dsl/gen_kernel/test_gen_kernel.py -k "tile_analysis or tile"`

### 测试目标

- 验证 `spec/pass/tile/analysis.md` 对应公开 API 的正常路径、边界条件与错误语义。
- 验证 DSL、IR 或 EmitC 生成文本与编译链路符合公开合同。
- 验证公开导入、注册名、CLI 或命名空间入口只暴露 spec 定义的 API。
- 验证 pass 或 pipeline 对目标 IR 的改写、no-op 与顺序约束。


### 功能与用例清单

| 用例 ID | 功能 | 场景 | 前置条件 | 操作 | 预期结果 | 建议测试 |
| --- | --- | --- | --- | --- | --- | --- |
| TC-PASS-TILE-ANALYSIS-001 | 生成/编译 | gen kernel dump dir writes source | 准备公开 DSL/IR 输入、目标配置与源码生成入口。 | 运行 `test_gen_kernel_dump_dir_writes_source`。 | 生成源码、IR 文本或编译结果体现“gen kernel dump dir writes source”场景。 | `test_gen_kernel_dump_dir_writes_source` |
| TC-PASS-TILE-ANALYSIS-002 | 公开入口 | gen kernel public modules exist and old legacy loader path is gone | 按 spec 声明的导入路径、CLI 参数、注册名或命名空间访问公开入口。 | 运行 `test_gen_kernel_public_modules_exist_and_old_legacy_loader_path_is_gone`。 | 公开入口在“gen kernel public modules exist and old legacy loader path is gone”场景下可导入、构造、注册或按名称发现。 | `test_gen_kernel_public_modules_exist_and_old_legacy_loader_path_is_gone` |
| TC-PASS-TILE-ANALYSIS-003 | pass 改写 | tile gen kernel paths use kernel gen tile modules | 准备包含目标 op、pass 名称或 pipeline 的公开 IR 输入。 | 运行 `test_tile_gen_kernel_paths_use_kernel_gen_tile_modules`。 | IR 改写后的 op、属性、顺序或 no-op 行为体现“tile gen kernel paths use kernel gen tile modules”场景。 | `test_tile_gen_kernel_paths_use_kernel_gen_tile_modules` |
| TC-PASS-TILE-ANALYSIS-004 | 生成/编译 | gen kernel local compile helpers delegate local compile runner | 准备公开 DSL/IR 输入、目标配置与源码生成入口。 | 运行 `test_gen_kernel_local_compile_helpers_delegate_local_compile_runner`。 | 生成源码、IR 文本或编译结果体现“gen kernel local compile helpers delegate local compile runner”场景。 | `test_gen_kernel_local_compile_helpers_delegate_local_compile_runner` |
| TC-PASS-TILE-ANALYSIS-005 | 生成/编译 | gen kernel returns target source | 准备公开 DSL/IR 输入、目标配置与源码生成入口。 | 运行 `test_gen_kernel_returns_target_source`。 | 生成源码、IR 文本或编译结果体现“gen kernel returns target source”场景。 | `test_gen_kernel_returns_target_source` |
| TC-PASS-TILE-ANALYSIS-006 | 边界/异常 | gen kernel converts emit error to gen kernel error | 准备触发该错误路径的公开输入或非法参数组合。 | 运行 `test_gen_kernel_converts_emit_error_to_gen_kernel_error`。 | “gen kernel converts emit error to gen kernel error”场景按公开错误语义失败或被拒绝。 | `test_gen_kernel_converts_emit_error_to_gen_kernel_error` |
| TC-PASS-TILE-ANALYSIS-007 | 生成/编译 | gen kernel entry module hides internal emitter entry | 准备公开 DSL/IR 输入、目标配置与源码生成入口。 | 运行 `test_gen_kernel_entry_module_hides_internal_emitter_entry`。 | 生成源码、IR 文本或编译结果体现“gen kernel entry module hides internal emitter entry”场景。 | `test_gen_kernel_entry_module_hides_internal_emitter_entry` |
| TC-PASS-TILE-ANALYSIS-008 | 公开入口 | gen kernel is the package public entry | 按 spec 声明的导入路径、CLI 参数、注册名或命名空间访问公开入口。 | 运行 `test_gen_kernel_is_the_package_public_entry`。 | 公开入口在“gen kernel is the package public entry”场景下可导入、构造、注册或按名称发现。 | `test_gen_kernel_is_the_package_public_entry` |
| TC-PASS-TILE-ANALYSIS-009 | 公开入口 | DSL gen kernel matches public MLIR gen plus gen kernel path | 按 spec 声明的导入路径、CLI 参数、注册名或命名空间访问公开入口。 | 运行 `test_dsl_gen_kernel_matches_public_mlir_gen_plus_gen_kernel_path`。 | 公开入口在“DSL gen kernel matches public MLIR gen plus gen kernel path”场景下可导入、构造、注册或按名称发现。 | `test_dsl_gen_kernel_matches_public_mlir_gen_plus_gen_kernel_path` |
| TC-PASS-TILE-ANALYSIS-010 | 生成/编译 | gen kernel has no legacy double interface | 准备公开 DSL/IR 输入、目标配置与源码生成入口。 | 运行 `test_gen_kernel_has_no_legacy_double_interface`。 | 生成源码、IR 文本或编译结果体现“gen kernel has no legacy double interface”场景。 | `test_gen_kernel_has_no_legacy_double_interface` |
| TC-PASS-TILE-ANALYSIS-011 | 生成/编译 | gen kernel delegates single op input to emit c | 准备公开 DSL/IR 输入、目标配置与源码生成入口。 | 运行 `test_gen_kernel_delegates_single_op_input_to_emit_c`。 | 生成源码、IR 文本或编译结果体现“gen kernel delegates single op input to emit c”场景。 | `test_gen_kernel_delegates_single_op_input_to_emit_c` |
| TC-PASS-TILE-ANALYSIS-012 | 生成/编译 | gen kernel uses mutable memory inputs | 准备公开 DSL/IR 输入、目标配置与源码生成入口。 | 运行 `test_gen_kernel_uses_mutable_memory_inputs`。 | 生成源码、IR 文本或编译结果体现“gen kernel uses mutable memory inputs”场景。 | `test_gen_kernel_uses_mutable_memory_inputs` |
| TC-PASS-TILE-ANALYSIS-013 | 生成/编译 | gen kernel accepts rewritten single output function | 准备公开 DSL/IR 输入、目标配置与源码生成入口。 | 运行 `test_gen_kernel_accepts_rewritten_single_output_function`。 | 生成源码、IR 文本或编译结果体现“gen kernel accepts rewritten single output function”场景。 | `test_gen_kernel_accepts_rewritten_single_output_function` |
| TC-PASS-TILE-ANALYSIS-014 | 生成/编译 | gen kernel rewritten deslice memory result uses front out param | 准备公开 DSL/IR 输入、目标配置与源码生成入口。 | 运行 `test_gen_kernel_rewritten_deslice_memory_result_uses_front_out_param`。 | 生成源码、IR 文本或编译结果体现“gen kernel rewritten deslice memory result uses front out param”场景。 | `test_gen_kernel_rewritten_deslice_memory_result_uses_front_out_param` |
| TC-PASS-TILE-ANALYSIS-015 | 生成/编译 | gen kernel uses default arg names when missing attrs | 准备公开 DSL/IR 输入、目标配置与源码生成入口。 | 运行 `test_gen_kernel_uses_default_arg_names_when_missing_attrs`。 | 生成源码、IR 文本或编译结果体现“gen kernel uses default arg names when missing attrs”场景。 | `test_gen_kernel_uses_default_arg_names_when_missing_attrs` |
| TC-PASS-TILE-ANALYSIS-016 | 生成/编译 | gen kernel emits ops in order | 准备公开 DSL/IR 输入、目标配置与源码生成入口。 | 运行 `test_gen_kernel_emits_ops_in_order`。 | 生成源码、IR 文本或编译结果体现“gen kernel emits ops in order”场景。 | `test_gen_kernel_emits_ops_in_order` |
| TC-PASS-TILE-ANALYSIS-017 | 生成/编译 | gen kernel delegates to emit c for non return ops | 准备公开 DSL/IR 输入、目标配置与源码生成入口。 | 运行 `test_gen_kernel_delegates_to_emit_c_for_non_return_ops`。 | 生成源码、IR 文本或编译结果体现“gen kernel delegates to emit c for non return ops”场景。 | `test_gen_kernel_delegates_to_emit_c_for_non_return_ops` |
| TC-PASS-TILE-ANALYSIS-018 | 生成/编译 | gen kernel handles func return and out binding in main flow | 准备公开 DSL/IR 输入、目标配置与源码生成入口。 | 运行 `test_gen_kernel_handles_func_return_and_out_binding_in_main_flow`。 | 生成源码、IR 文本或编译结果体现“gen kernel handles func return and out binding in main flow”场景。 | `test_gen_kernel_handles_func_return_and_out_binding_in_main_flow` |
| TC-PASS-TILE-ANALYSIS-019 | 边界/异常 | kernel emitter public dispatch error boundaries | 准备触发该错误路径的公开输入或非法参数组合。 | 运行 `test_kernel_emitter_public_dispatch_error_boundaries`。 | “kernel emitter public dispatch error boundaries”场景按公开错误语义失败或被拒绝。 | `test_kernel_emitter_public_dispatch_error_boundaries` |
| TC-PASS-TILE-ANALYSIS-020 | 公开入口 | kernel emitter public include and type dispatch | 按 spec 声明的导入路径、CLI 参数、注册名或命名空间访问公开入口。 | 运行 `test_kernel_emitter_public_include_and_type_dispatch`。 | 公开入口在“kernel emitter public include and type dispatch”场景下可导入、构造、注册或按名称发现。 | `test_kernel_emitter_public_include_and_type_dispatch` |
| TC-PASS-TILE-ANALYSIS-021 | 生成/编译 | gen kernel assembles loop body | 准备公开 DSL/IR 输入、目标配置与源码生成入口。 | 运行 `test_gen_kernel_assembles_loop_body`。 | 生成源码、IR 文本或编译结果体现“gen kernel assembles loop body”场景。 | `test_gen_kernel_assembles_loop_body` |
| TC-PASS-TILE-ANALYSIS-022 | 边界/异常 | gen kernel propagates emit error | 准备触发该错误路径的公开输入或非法参数组合。 | 运行 `test_gen_kernel_propagates_emit_error`。 | “gen kernel propagates emit error”场景按公开错误语义失败或被拒绝。 | `test_gen_kernel_propagates_emit_error` |
| TC-PASS-TILE-ANALYSIS-023 | 边界/异常 | gen kernel rejects unsupported return form | 准备触发该错误路径的公开输入或非法参数组合。 | 运行 `test_gen_kernel_rejects_unsupported_return_form`。 | “gen kernel rejects unsupported return form”场景按公开错误语义失败或被拒绝。 | `test_gen_kernel_rejects_unsupported_return_form` |
| TC-PASS-TILE-ANALYSIS-024 | 生成/编译 | gen kernel supports float32 scalar and memory | 准备公开 DSL/IR 输入、目标配置与源码生成入口。 | 运行 `test_gen_kernel_supports_float32_scalar_and_memory`。 | 生成源码、IR 文本或编译结果体现“gen kernel supports float32 scalar and memory”场景。 | `test_gen_kernel_supports_float32_scalar_and_memory` |
| TC-PASS-TILE-ANALYSIS-025 | 生成/编译 | gen kernel preserves function and arg names | 准备公开 DSL/IR 输入、目标配置与源码生成入口。 | 运行 `test_gen_kernel_preserves_function_and_arg_names`。 | 生成源码、IR 文本或编译结果体现“gen kernel preserves function and arg names”场景。 | `test_gen_kernel_preserves_function_and_arg_names` |
| TC-PASS-TILE-ANALYSIS-026 | 生成/编译 | gen kernel supports symbol scalar return | 准备公开 DSL/IR 输入、目标配置与源码生成入口。 | 运行 `test_gen_kernel_supports_symbol_scalar_return`。 | 生成源码、IR 文本或编译结果体现“gen kernel supports symbol scalar return”场景。 | `test_gen_kernel_supports_symbol_scalar_return` |
| TC-PASS-TILE-ANALYSIS-027 | 边界/异常 | gen kernel rejects symbol scalar return on non cpu | 准备触发该错误路径的公开输入或非法参数组合。 | 运行 `test_gen_kernel_rejects_symbol_scalar_return_on_non_cpu`。 | “gen kernel rejects symbol scalar return on non cpu”场景按公开错误语义失败或被拒绝。 | `test_gen_kernel_rejects_symbol_scalar_return_on_non_cpu` |
| TC-PASS-TILE-ANALYSIS-028 | pass 改写 | gen kernel supports lowered NN add memory memory on cpu | 准备包含目标 op、pass 名称或 pipeline 的公开 IR 输入。 | 运行 `test_gen_kernel_supports_lowered_nn_add_memory_memory_on_cpu`。 | IR 改写后的 op、属性、顺序或 no-op 行为体现“gen kernel supports lowered NN add memory memory on cpu”场景。 | `test_gen_kernel_supports_lowered_nn_add_memory_memory_on_cpu` |
| TC-PASS-TILE-ANALYSIS-029 | pass 改写 | gen kernel supports lowered NN add memory const on cpu | 准备包含目标 op、pass 名称或 pipeline 的公开 IR 输入。 | 运行 `test_gen_kernel_supports_lowered_nn_add_memory_const_on_cpu`。 | IR 改写后的 op、属性、顺序或 no-op 行为体现“gen kernel supports lowered NN add memory const on cpu”场景。 | `test_gen_kernel_supports_lowered_nn_add_memory_const_on_cpu` |
| TC-PASS-TILE-ANALYSIS-030 | pass 改写 | gen kernel supports lowered NN add memory symbol on cpu | 准备包含目标 op、pass 名称或 pipeline 的公开 IR 输入。 | 运行 `test_gen_kernel_supports_lowered_nn_add_memory_symbol_on_cpu`。 | IR 改写后的 op、属性、顺序或 no-op 行为体现“gen kernel supports lowered NN add memory symbol on cpu”场景。 | `test_gen_kernel_supports_lowered_nn_add_memory_symbol_on_cpu` |
| TC-PASS-TILE-ANALYSIS-031 | 生成/编译 | gen kernel accepts rewritten single output function | 准备公开 DSL/IR 输入、目标配置与源码生成入口。 | 运行 `test_gen_kernel_accepts_rewritten_single_output_function`。 | 生成源码、IR 文本或编译结果体现“gen kernel accepts rewritten single output function”场景。 | `test_gen_kernel_accepts_rewritten_single_output_function` |
| TC-PASS-TILE-ANALYSIS-032 | 生成/编译 | gen kernel accepts rewritten mixed output function | 准备公开 DSL/IR 输入、目标配置与源码生成入口。 | 运行 `test_gen_kernel_accepts_rewritten_mixed_output_function`。 | 生成源码、IR 文本或编译结果体现“gen kernel accepts rewritten mixed output function”场景。 | `test_gen_kernel_accepts_rewritten_mixed_output_function` |
| TC-PASS-TILE-ANALYSIS-033 | pass 改写 | rewritten pipeline has no memory return abi left | 准备包含目标 op、pass 名称或 pipeline 的公开 IR 输入。 | 运行 `test_rewritten_pipeline_has_no_memory_return_abi_left`。 | IR 改写后的 op、属性、顺序或 no-op 行为体现“rewritten pipeline has no memory return abi left”场景。 | `test_rewritten_pipeline_has_no_memory_return_abi_left` |
| TC-PASS-TILE-ANALYSIS-034 | 边界/异常 | gen kernel rejects lowered IR without buffer results to out params | 准备触发该错误路径的公开输入或非法参数组合。 | 运行 `test_gen_kernel_rejects_lowered_ir_without_buffer_results_to_out_params`。 | “gen kernel rejects lowered IR without buffer results to out params”场景按公开错误语义失败或被拒绝。 | `test_gen_kernel_rejects_lowered_ir_without_buffer_results_to_out_params` |
| TC-PASS-TILE-ANALYSIS-035 | 边界/异常 | rewritten pipeline fails on half rewritten IR | 准备触发该错误路径的公开输入或非法参数组合。 | 运行 `test_rewritten_pipeline_fails_on_half_rewritten_ir`。 | “rewritten pipeline fails on half rewritten IR”场景按公开错误语义失败或被拒绝。 | `test_rewritten_pipeline_fails_on_half_rewritten_ir` |
| TC-PASS-TILE-ANALYSIS-036 | 生成/编译 | gen kernel emits npu demo body level kernel | 准备公开 DSL/IR 输入、目标配置与源码生成入口。 | 运行 `test_gen_kernel_emits_npu_demo_body_level_kernel`。 | 生成源码、IR 文本或编译结果体现“gen kernel emits npu demo body level kernel”场景。 | `test_gen_kernel_emits_npu_demo_body_level_kernel` |
| TC-PASS-TILE-ANALYSIS-037 | 生成/编译 | gen kernel emits npu demo kernel binary signature out first | 准备公开 DSL/IR 输入、目标配置与源码生成入口。 | 运行 `test_gen_kernel_emits_npu_demo_kernel_binary_signature_out_first`。 | 生成源码、IR 文本或编译结果体现“gen kernel emits npu demo kernel binary signature out first”场景。 | `test_gen_kernel_emits_npu_demo_kernel_binary_signature_out_first` |
| TC-PASS-TILE-ANALYSIS-038 | 生成/编译 | gen kernel emits npu demo DMA alloc module | 准备公开 DSL/IR 输入、目标配置与源码生成入口。 | 运行 `test_gen_kernel_emits_npu_demo_dma_alloc_module`。 | 生成源码、IR 文本或编译结果体现“gen kernel emits npu demo DMA alloc module”场景。 | `test_gen_kernel_emits_npu_demo_dma_alloc_module` |
| TC-PASS-TILE-ANALYSIS-039 | 生成/编译 | gen kernel compiles npu demo source with single include | 准备公开 DSL/IR 输入、目标配置与源码生成入口。 | 运行 `test_gen_kernel_compiles_npu_demo_source_with_single_include`。 | 生成源码、IR 文本或编译结果体现“gen kernel compiles npu demo source with single include”场景。 | `test_gen_kernel_compiles_npu_demo_source_with_single_include` |
| TC-PASS-TILE-ANALYSIS-040 | pass 改写 | gen kernel compiles npu demo tiled matmul source | 准备包含目标 op、pass 名称或 pipeline 的公开 IR 输入。 | 运行 `test_gen_kernel_compiles_npu_demo_tiled_matmul_source`。 | IR 改写后的 op、属性、顺序或 no-op 行为体现“gen kernel compiles npu demo tiled matmul source”场景。 | `test_gen_kernel_compiles_npu_demo_tiled_matmul_source` |
| TC-PASS-TILE-ANALYSIS-041 | pass 改写 | gen kernel emits npu demo memory pipeline | 准备包含目标 op、pass 名称或 pipeline 的公开 IR 输入。 | 运行 `test_gen_kernel_emits_npu_demo_memory_pipeline`。 | IR 改写后的 op、属性、顺序或 no-op 行为体现“gen kernel emits npu demo memory pipeline”场景。 | `test_gen_kernel_emits_npu_demo_memory_pipeline` |
| TC-PASS-TILE-ANALYSIS-042 | 边界/异常 | gen kernel rejects npu demo body level kernel with unknown body op | 准备触发该错误路径的公开输入或非法参数组合。 | 运行 `test_gen_kernel_rejects_npu_demo_body_level_kernel_with_unknown_body_op`。 | “gen kernel rejects npu demo body level kernel with unknown body op”场景按公开错误语义失败或被拒绝。 | `test_gen_kernel_rejects_npu_demo_body_level_kernel_with_unknown_body_op` |
| TC-PASS-TILE-ANALYSIS-043 | 边界/异常 | gen kernel rejects npu demo body level kernel with nonempty body | 准备触发该错误路径的公开输入或非法参数组合。 | 运行 `test_gen_kernel_rejects_npu_demo_body_level_kernel_with_nonempty_body`。 | “gen kernel rejects npu demo body level kernel with nonempty body”场景按公开错误语义失败或被拒绝。 | `test_gen_kernel_rejects_npu_demo_body_level_kernel_with_nonempty_body` |
| TC-PASS-TILE-ANALYSIS-044 | pass 改写 | gen kernel black box lowered add and npu demo contracts | 准备包含目标 op、pass 名称或 pipeline 的公开 IR 输入。 | 运行 `test_gen_kernel_black_box_lowered_add_and_npu_demo_contracts`。 | IR 改写后的 op、属性、顺序或 no-op 行为体现“gen kernel black box lowered add and npu demo contracts”场景。 | `test_gen_kernel_black_box_lowered_add_and_npu_demo_contracts` |
| TC-PASS-TILE-ANALYSIS-045 | pass 改写 | gen kernel compiles and runs lowered NN add variants on cpu | 准备包含目标 op、pass 名称或 pipeline 的公开 IR 输入。 | 运行 `test_gen_kernel_compiles_and_runs_lowered_nn_add_variants_on_cpu`。 | IR 改写后的 op、属性、顺序或 no-op 行为体现“gen kernel compiles and runs lowered NN add variants on cpu”场景。 | `test_gen_kernel_compiles_and_runs_lowered_nn_add_variants_on_cpu` |
| TC-PASS-TILE-ANALYSIS-046 | pass 改写 | gen kernel emits tile codegen single function tile loop | 准备包含目标 op、pass 名称或 pipeline 的公开 IR 输入。 | 运行 `test_gen_kernel_emits_tile_codegen_single_function_tile_loop`。 | IR 改写后的 op、属性、顺序或 no-op 行为体现“gen kernel emits tile codegen single function tile loop”场景。 | `test_gen_kernel_emits_tile_codegen_single_function_tile_loop` |
| TC-PASS-TILE-ANALYSIS-047 | 边界/异常 | gen kernel rejects tile codegen missing tuner param | 准备触发该错误路径的公开输入或非法参数组合。 | 运行 `test_gen_kernel_rejects_tile_codegen_missing_tuner_param`。 | “gen kernel rejects tile codegen missing tuner param”场景按公开错误语义失败或被拒绝。 | `test_gen_kernel_rejects_tile_codegen_missing_tuner_param` |
| TC-PASS-TILE-ANALYSIS-048 | 边界/异常 | gen kernel rejects tile codegen missing loop | 准备触发该错误路径的公开输入或非法参数组合。 | 运行 `test_gen_kernel_rejects_tile_codegen_missing_loop`。 | “gen kernel rejects tile codegen missing loop”场景按公开错误语义失败或被拒绝。 | `test_gen_kernel_rejects_tile_codegen_missing_loop` |
| TC-PASS-TILE-ANALYSIS-049 | 边界/异常 | gen kernel rejects tile codegen with helper call | 准备触发该错误路径的公开输入或非法参数组合。 | 运行 `test_gen_kernel_rejects_tile_codegen_with_helper_call`。 | “gen kernel rejects tile codegen with helper call”场景按公开错误语义失败或被拒绝。 | `test_gen_kernel_rejects_tile_codegen_with_helper_call` |
| TC-PASS-TILE-ANALYSIS-050 | 边界/异常 | gen kernel rejects legacy split tuner param contract | 准备触发该错误路径的公开输入或非法参数组合。 | 运行 `test_gen_kernel_rejects_legacy_split_tuner_param_contract`。 | “gen kernel rejects legacy split tuner param contract”场景按公开错误语义失败或被拒绝。 | `test_gen_kernel_rejects_legacy_split_tuner_param_contract` |
| TC-PASS-TILE-ANALYSIS-051 | pass 改写 | gen kernel emits tile elewise cpu source for elementwise and broadcast | 准备包含目标 op、pass 名称或 pipeline 的公开 IR 输入。 | 运行 `test_gen_kernel_emits_tile_elewise_cpu_source_for_elementwise_and_broadcast`。 | IR 改写后的 op、属性、顺序或 no-op 行为体现“gen kernel emits tile elewise cpu source for elementwise and broadcast”场景。 | `test_gen_kernel_emits_tile_elewise_cpu_source_for_elementwise_and_broadcast` |
| TC-PASS-TILE-ANALYSIS-052 | 生成/编译 | gen kernel emits npu demo launch wrapper and barrier body | 准备公开 DSL/IR 输入、目标配置与源码生成入口。 | 运行 `test_gen_kernel_emits_npu_demo_launch_wrapper_and_barrier_body`。 | 生成源码、IR 文本或编译结果体现“gen kernel emits npu demo launch wrapper and barrier body”场景。 | `test_gen_kernel_emits_npu_demo_launch_wrapper_and_barrier_body` |
| TC-PASS-TILE-ANALYSIS-053 | 生成/编译 | gen kernel compiles npu demo launch wrapper and barrier body | 准备公开 DSL/IR 输入、目标配置与源码生成入口。 | 运行 `test_gen_kernel_compiles_npu_demo_launch_wrapper_and_barrier_body`。 | 生成源码、IR 文本或编译结果体现“gen kernel compiles npu demo launch wrapper and barrier body”场景。 | `test_gen_kernel_compiles_npu_demo_launch_wrapper_and_barrier_body` |
| TC-PASS-TILE-ANALYSIS-054 | 生成/编译 | gen kernel emits npu demo cost functions for compute and memory | 准备公开 DSL/IR 输入、目标配置与源码生成入口。 | 运行 `test_gen_kernel_emits_npu_demo_cost_functions_for_compute_and_memory`。 | 生成源码、IR 文本或编译结果体现“gen kernel emits npu demo cost functions for compute and memory”场景。 | `test_gen_kernel_emits_npu_demo_cost_functions_for_compute_and_memory` |
| TC-PASS-TILE-ANALYSIS-055 | 生成/编译 | gen kernel compiles npu demo cost function module | 准备公开 DSL/IR 输入、目标配置与源码生成入口。 | 运行 `test_gen_kernel_compiles_npu_demo_cost_function_module`。 | 生成源码、IR 文本或编译结果体现“gen kernel compiles npu demo cost function module”场景。 | `test_gen_kernel_compiles_npu_demo_cost_function_module` |
| TC-PASS-TILE-ANALYSIS-056 | pass 改写 | gen kernel compiles outlined npu demo launch module | 准备包含目标 op、pass 名称或 pipeline 的公开 IR 输入。 | 运行 `test_gen_kernel_compiles_outlined_npu_demo_launch_module`。 | IR 改写后的 op、属性、顺序或 no-op 行为体现“gen kernel compiles outlined npu demo launch module”场景。 | `test_gen_kernel_compiles_outlined_npu_demo_launch_module` |
| TC-PASS-TILE-ANALYSIS-057 | 生成/编译 | gen kernel npu demo add barrier runtime smoke | 准备公开 DSL/IR 输入、目标配置与源码生成入口。 | 运行 `test_gen_kernel_npu_demo_add_barrier_runtime_smoke`。 | 生成源码、IR 文本或编译结果体现“gen kernel npu demo add barrier runtime smoke”场景。 | `test_gen_kernel_npu_demo_add_barrier_runtime_smoke` |
| TC-PASS-TILE-ANALYSIS-058 | 边界/异常 | gen kernel rejects npu demo barrier wrapper missing body symbol | 准备触发该错误路径的公开输入或非法参数组合。 | 运行 `test_gen_kernel_rejects_npu_demo_barrier_wrapper_missing_body_symbol`。 | “gen kernel rejects npu demo barrier wrapper missing body symbol”场景按公开错误语义失败或被拒绝。 | `test_gen_kernel_rejects_npu_demo_barrier_wrapper_missing_body_symbol` |
| TC-PASS-TILE-ANALYSIS-059 | 边界/异常 | gen kernel rejects npu demo barrier fail fast boundaries | 准备触发该错误路径的公开输入或非法参数组合。 | 运行 `test_gen_kernel_rejects_npu_demo_barrier_fail_fast_boundaries`。 | “gen kernel rejects npu demo barrier fail fast boundaries”场景按公开错误语义失败或被拒绝。 | `test_gen_kernel_rejects_npu_demo_barrier_fail_fast_boundaries` |
| TC-PASS-TILE-ANALYSIS-060 | 公开入口 | tile analysis public API surface is stable | 按 spec 声明的导入路径、CLI 参数、注册名或命名空间访问公开入口。 | 运行 `test_tile_analysis_public_api_surface_is_stable`。 | 公开入口在“tile analysis public API surface is stable”场景下可导入、构造、注册或按名称发现。 | `test_tile_analysis_public_api_surface_is_stable` |
| TC-PASS-TILE-ANALYSIS-061 | pass 改写 | tile analysis binary pattern adds only analysis attrs | 准备包含目标 op、pass 名称或 pipeline 的公开 IR 输入。 | 运行 `test_tile_analysis_binary_pattern_adds_only_analysis_attrs`。 | IR 改写后的 op、属性、顺序或 no-op 行为体现“tile analysis binary pattern adds only analysis attrs”场景。 | `test_tile_analysis_binary_pattern_adds_only_analysis_attrs` |
| TC-PASS-TILE-ANALYSIS-062 | pass 改写 | tile analysis binary pattern marks existing tile shape inside symbol for | 准备包含目标 op、pass 名称或 pipeline 的公开 IR 输入。 | 运行 `test_tile_analysis_binary_pattern_marks_existing_tile_shape_inside_symbol_for`。 | IR 改写后的 op、属性、顺序或 no-op 行为体现“tile analysis binary pattern marks existing tile shape inside symbol for”场景。 | `test_tile_analysis_binary_pattern_marks_existing_tile_shape_inside_symbol_for` |
| TC-PASS-TILE-ANALYSIS-063 | pass 改写 | tile analysis binary pattern marks only loop covered dim inside single symbol for | 准备包含目标 op、pass 名称或 pipeline 的公开 IR 输入。 | 运行 `test_tile_analysis_binary_pattern_marks_only_loop_covered_dim_inside_single_symbol_for`。 | IR 改写后的 op、属性、顺序或 no-op 行为体现“tile analysis binary pattern marks only loop covered dim inside single symbol for”场景。 | `test_tile_analysis_binary_pattern_marks_only_loop_covered_dim_inside_single_symbol_for` |
| TC-PASS-TILE-ANALYSIS-064 | pass 改写 | tile analysis broadcast pattern marks expand roles | 准备包含目标 op、pass 名称或 pipeline 的公开 IR 输入。 | 运行 `test_tile_analysis_broadcast_pattern_marks_expand_roles`。 | IR 改写后的 op、属性、顺序或 no-op 行为体现“tile analysis broadcast pattern marks expand roles”场景。 | `test_tile_analysis_broadcast_pattern_marks_expand_roles` |
| TC-PASS-TILE-ANALYSIS-065 | pass 改写 | tile analysis broadcast pattern marks non expand tile shape inside symbol for | 准备包含目标 op、pass 名称或 pipeline 的公开 IR 输入。 | 运行 `test_tile_analysis_broadcast_pattern_marks_non_expand_tile_shape_inside_symbol_for`。 | IR 改写后的 op、属性、顺序或 no-op 行为体现“tile analysis broadcast pattern marks non expand tile shape inside symbol for”场景。 | `test_tile_analysis_broadcast_pattern_marks_non_expand_tile_shape_inside_symbol_for` |
| TC-PASS-TILE-ANALYSIS-066 | pass 改写 | tile analysis matmul pattern marks reduce roles | 准备包含目标 op、pass 名称或 pipeline 的公开 IR 输入。 | 运行 `test_tile_analysis_matmul_pattern_marks_reduce_roles`。 | IR 改写后的 op、属性、顺序或 no-op 行为体现“tile analysis matmul pattern marks reduce roles”场景。 | `test_tile_analysis_matmul_pattern_marks_reduce_roles` |
| TC-PASS-TILE-ANALYSIS-067 | pass 改写 | tile analysis matmul pattern marks existing tile shape inside symbol for | 准备包含目标 op、pass 名称或 pipeline 的公开 IR 输入。 | 运行 `test_tile_analysis_matmul_pattern_marks_existing_tile_shape_inside_symbol_for`。 | IR 改写后的 op、属性、顺序或 no-op 行为体现“tile analysis matmul pattern marks existing tile shape inside symbol for”场景。 | `test_tile_analysis_matmul_pattern_marks_existing_tile_shape_inside_symbol_for` |
| TC-PASS-TILE-ANALYSIS-068 | pass 改写 | tile analysis matmul pattern marks only loop covered dim inside single symbol for | 准备包含目标 op、pass 名称或 pipeline 的公开 IR 输入。 | 运行 `test_tile_analysis_matmul_pattern_marks_only_loop_covered_dim_inside_single_symbol_for`。 | IR 改写后的 op、属性、顺序或 no-op 行为体现“tile analysis matmul pattern marks only loop covered dim inside single symbol for”场景。 | `test_tile_analysis_matmul_pattern_marks_only_loop_covered_dim_inside_single_symbol_for` |
| TC-PASS-TILE-ANALYSIS-069 | 公开入口 | tile analysis pass is registry constructible module pass | 按 spec 声明的导入路径、CLI 参数、注册名或命名空间访问公开入口。 | 运行 `test_tile_analysis_pass_is_registry_constructible_module_pass`。 | 公开入口在“tile analysis pass is registry constructible module pass”场景下可导入、构造、注册或按名称发现。 | `test_tile_analysis_pass_is_registry_constructible_module_pass` |
