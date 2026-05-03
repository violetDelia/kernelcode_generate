# tile elewise

## 功能简介

- `tile-elewise` 的实现与公开合同固定收口在 [`kernel_gen/passes/tile/elewise.py`](../../../kernel_gen/passes/tile/elewise.py)。
- 它消费已有 `tile.analysis` 与 `tile.tile_exprs`，继续对当前顶层 tile op 生成显式 `symbol.for + dma.view` 结构。
- 当前公开 pattern 只包含：
  - `TileElewiseBinaryPattern`
  - `TileElewiseBroadcastPattern`
  - `TileElewiseMatmulPattern`

## API 列表

- `build_registered_pass(name: str, options: dict[str, str] | None = None) -> ModulePass`
- `class TileElewiseBinaryPattern(RewritePattern)`
- `TileElewiseBinaryPattern.match_and_rewrite(op: KernelBinaryElewiseOp, rewriter: PatternRewriter) -> None`
- `class TileElewiseBroadcastPattern(RewritePattern)`
- `TileElewiseBroadcastPattern.match_and_rewrite(op: DmaBroadcastOp, rewriter: PatternRewriter) -> None`
- `class TileElewiseMatmulPattern(RewritePattern)`
- `TileElewiseMatmulPattern.match_and_rewrite(op: KernelMatmulOp, rewriter: PatternRewriter) -> None`
- `class TileElewisePass(ModulePass)`
- `TileElewisePass.__init__(fold: bool = True) -> None`
- `TileElewisePass.apply(ctx: Context, module: ModuleOp) -> None`
- `get_tile_elewise_pass_patterns() -> list[RewritePattern]`

## 文档信息

- 创建者：`未记录`
- 最后一次更改：`小李飞刀`
- `spec`：[`spec/pass/tile/elewise.md`](../../../spec/pass/tile/elewise.md)
- `功能实现`：
  - [`kernel_gen/passes/registry.py`](../../../kernel_gen/passes/registry.py)
  - [`kernel_gen/passes/tile/elewise.py`](../../../kernel_gen/passes/tile/elewise.py)
- `test`：
  - [`test/passes/tile/test_elewise.py`](../../../test/passes/tile/test_elewise.py)
  - [`test/dsl/gen_kernel/test_gen_kernel.py`](../../../test/dsl/gen_kernel/test_gen_kernel.py)

## 依赖

- tile family 合同：[`spec/pass/tile/analysis.md`](../../../spec/pass/tile/analysis.md)、[`spec/pass/tile/reduce.md`](../../../spec/pass/tile/reduce.md)
- `tile-analysis`：[`spec/pass/tile/analysis.md`](../../../spec/pass/tile/analysis.md)
- 后端代码生成：[`spec/dsl/gen_kernel/gen_kernel.md`](../../../spec/dsl/gen_kernel/gen_kernel.md)

## 目标

- 保持公开 pass 名固定为 `tile-elewise`。
- 保持当前文件内公开 API 只覆盖 pass、getter 和 3 个 pattern。
- 只消费顶层 `kernel.binary_elewise`、`dma.broadcast`、`kernel.matmul` 目标 op，不再公开额外 helper API。

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

### `class TileElewiseBinaryPattern(RewritePattern)`

- api：`class TileElewiseBinaryPattern(RewritePattern)`
- 参数：无。
- 返回值：`TileElewiseBinaryPattern` 实例。
- 使用示例：

  ```python
  tile_elewise_binary_pattern = TileElewiseBinaryPattern()
  ```
- 功能说明：定义 `TileElewiseBinaryPattern` rewrite pattern 对象。
- 注意事项：构造参数必须符合本条目参数说明；实例内部缓存、状态字典和派生字段不作为外部可变入口。

### `TileElewiseBinaryPattern.match_and_rewrite(op: KernelBinaryElewiseOp, rewriter: PatternRewriter) -> None`

- api：`TileElewiseBinaryPattern.match_and_rewrite(op: KernelBinaryElewiseOp, rewriter: PatternRewriter) -> None`
- 参数：
  - `op`：IR operation，作为 emit、rewrite、lowering 或校验的当前处理对象；类型 `KernelBinaryElewiseOp`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
  - `rewriter`：公开 rewrite 对象，用于替换、插入或删除 IR operation；类型 `PatternRewriter`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
- 返回值：无返回值；调用成功表示操作完成。
- 使用示例：

  ```python
  tile_elewise_binary_pattern = tile_elewise_binary_pattern
  tile_elewise_binary_pattern.match_and_rewrite(op=op, rewriter=rewriter)
  ```
- 功能说明：使用 `TileElewiseBinaryPattern` 匹配目标 operation 并执行 rewrite。
- 注意事项：非法输入必须按本条目参数说明和公开错误语义处理；调用方不得依赖实现内部状态。

### `class TileElewiseBroadcastPattern(RewritePattern)`

- api：`class TileElewiseBroadcastPattern(RewritePattern)`
- 参数：无。
- 返回值：`TileElewiseBroadcastPattern` 实例。
- 使用示例：

  ```python
  tile_elewise_broadcast_pattern = TileElewiseBroadcastPattern()
  ```
- 功能说明：定义 `TileElewiseBroadcastPattern` rewrite pattern 对象。
- 注意事项：构造参数必须符合本条目参数说明；实例内部缓存、状态字典和派生字段不作为外部可变入口。

### `TileElewiseBroadcastPattern.match_and_rewrite(op: DmaBroadcastOp, rewriter: PatternRewriter) -> None`

- api：`TileElewiseBroadcastPattern.match_and_rewrite(op: DmaBroadcastOp, rewriter: PatternRewriter) -> None`
- 参数：
  - `op`：IR operation，作为 emit、rewrite、lowering 或校验的当前处理对象；类型 `DmaBroadcastOp`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
  - `rewriter`：公开 rewrite 对象，用于替换、插入或删除 IR operation；类型 `PatternRewriter`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
- 返回值：无返回值；调用成功表示操作完成。
- 使用示例：

  ```python
  tile_elewise_broadcast_pattern = tile_elewise_broadcast_pattern
  tile_elewise_broadcast_pattern.match_and_rewrite(op=op, rewriter=rewriter)
  ```
- 功能说明：使用 `TileElewiseBroadcastPattern` 匹配目标 operation 并执行 rewrite。
- 注意事项：非法输入必须按本条目参数说明和公开错误语义处理；调用方不得依赖实现内部状态。

### `class TileElewiseMatmulPattern(RewritePattern)`

- api：`class TileElewiseMatmulPattern(RewritePattern)`
- 参数：无。
- 返回值：`TileElewiseMatmulPattern` 实例。
- 使用示例：

  ```python
  tile_elewise_matmul_pattern = TileElewiseMatmulPattern()
  ```
- 功能说明：定义 `TileElewiseMatmulPattern` rewrite pattern 对象。
- 注意事项：构造参数必须符合本条目参数说明；实例内部缓存、状态字典和派生字段不作为外部可变入口。

### `TileElewiseMatmulPattern.match_and_rewrite(op: KernelMatmulOp, rewriter: PatternRewriter) -> None`

- api：`TileElewiseMatmulPattern.match_and_rewrite(op: KernelMatmulOp, rewriter: PatternRewriter) -> None`
- 参数：
  - `op`：IR operation，作为 emit、rewrite、lowering 或校验的当前处理对象；类型 `KernelMatmulOp`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
  - `rewriter`：公开 rewrite 对象，用于替换、插入或删除 IR operation；类型 `PatternRewriter`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
- 返回值：无返回值；调用成功表示操作完成。
- 使用示例：

  ```python
  tile_elewise_matmul_pattern = tile_elewise_matmul_pattern
  tile_elewise_matmul_pattern.match_and_rewrite(op=op, rewriter=rewriter)
  ```
- 功能说明：使用 `TileElewiseMatmulPattern` 匹配目标 operation 并执行 rewrite。
- 注意事项：非法输入必须按本条目参数说明和公开错误语义处理；调用方不得依赖实现内部状态。

### `class TileElewisePass(ModulePass)`

- api：`class TileElewisePass(ModulePass)`
- 参数：无。
- 返回值：`TileElewisePass` 实例。
- 使用示例：

  ```python
  tile_elewise_pass = TileElewisePass()
  ```
- 功能说明：定义 `TileElewisePass` pass 对象。
- 注意事项：构造参数必须符合本条目参数说明；实例内部缓存、状态字典和派生字段不作为外部可变入口。

### `TileElewisePass.__init__(fold: bool = True) -> None`

- api：`TileElewisePass.__init__(fold: bool = True) -> None`
- 参数：
  - `fold`：`fold` 输入值，参与 `__init__` 的公开处理流程；类型 `bool`；默认值 `True`；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
- 返回值：无返回值；调用成功表示操作完成。
- 使用示例：

  ```python
  tile_elewise_pass = TileElewisePass(fold=True)
  ```
- 功能说明：执行 `__init__`。
- 注意事项：该特殊方法只承接 Python 对应协议语义；不得额外暴露内部字段。

### `TileElewisePass.apply(ctx: Context, module: ModuleOp) -> None`

- api：`TileElewisePass.apply(ctx: Context, module: ModuleOp) -> None`
- 参数：
  - `ctx`：公开上下文对象，提供代码生成、emit、pass 或工具执行所需的配置与状态；类型 `Context`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
  - `module`：模块级 IR 对象，作为 pass、校验或代码生成的处理主体；类型 `ModuleOp`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
- 返回值：无返回值；调用成功表示操作完成。
- 使用示例：

  ```python
  tile_elewise_pass = tile_elewise_pass
  tile_elewise_pass.apply(ctx=ctx, module=module)
  ```
- 功能说明：对模块执行 `TileElewisePass` pass。
- 注意事项：非法输入必须按本条目参数说明和公开错误语义处理；调用方不得依赖实现内部状态。

### `get_tile_elewise_pass_patterns() -> list[RewritePattern]`

- api：`get_tile_elewise_pass_patterns() -> list[RewritePattern]`
- 参数：无。
- 返回值：`list[RewritePattern]`。
- 使用示例：

  ```python
  from kernel_gen.passes.tile.elewise import get_tile_elewise_pass_patterns

  patterns = get_tile_elewise_pass_patterns()
  ```
- 功能说明：返回 `tile-elewise` 使用的公开 pattern 列表。
- 注意事项：getter 的稳定顺序固定为 `Binary -> Broadcast -> Matmul`；pattern 命中后直接改写当前顶层 tile op，不再公开共享 rewrite helper；返回列表不承诺可被调用方原地修改后影响 pass 行为。


## 额外补充

### 模块级补充

### `build_registered_pass("tile-elewise")`

- 功能说明：

- 构造 `tile-elewise` 的公开 `ModulePass`。

- 使用示例：

```python
from xdsl.context import Context
from kernel_gen.passes.registry import build_registered_pass

build_registered_pass("tile-elewise").apply(Context(), module)
```

### `kernel_gen.passes.tile.elewise`

- 功能说明：

- 当前文件公开对象集合固定为：
  - `TileElewiseBinaryPattern`
  - `TileElewiseBroadcastPattern`
  - `TileElewiseMatmulPattern`
  - `TileElewisePass`
  - `get_tile_elewise_pass_patterns()`

- 使用示例：

```python
from kernel_gen.passes.tile.elewise import (
    TileElewiseBinaryPattern,
    TileElewisePass,
    get_tile_elewise_pass_patterns,
)

patterns = get_tile_elewise_pass_patterns()
assert type(patterns[0]) is TileElewiseBinaryPattern
```

- 返回值：

- getter 的稳定顺序固定为 `Binary -> Broadcast -> Matmul`。
- `TileElewiseBinaryPattern` 覆盖当前实现支持的 binary / compare `kind`：
  - `add/sub/mul/div/truediv`
  - `eq/ne/lt/le/gt/ge`
- pattern 命中后直接改写当前顶层 tile op，不再公开共享 rewrite helper。

### helper 说明

- 当前文件内除上述 5 个公开对象外，不再承诺任何其他稳定 helper。
- 跨文件实现不得调用本文件未列入公开 API 集合的名字。
- 测试不得把未列入公开 API 集合的名字当作公开接口断言。

## 测试

- 测试文件：
  - `test/dsl/gen_kernel/test_gen_kernel.py`
  - `test/passes/tile/test_elewise.py`
- 执行命令：
  - `pytest -q test/passes/tile/test_elewise.py`
  - `pytest -q test/dsl/gen_kernel/test_gen_kernel.py -k "tile_elewise or tile"`

### 测试目标

- 验证 `spec/pass/tile/elewise.md` 对应公开 API 的正常路径、边界条件与错误语义。
- 验证 DSL、IR 或 EmitC 生成文本与编译链路符合公开合同。
- 验证公开导入、注册名、CLI 或命名空间入口只暴露 spec 定义的 API。
- 验证 pass 或 pipeline 对目标 IR 的改写、no-op 与顺序约束。


### 功能与用例清单

| 用例 ID | 功能 | 场景 | 前置条件 | 操作 | 预期结果 | 建议测试 |
| --- | --- | --- | --- | --- | --- | --- |
| TC-PASS-TILE-ELEWISE-001 | 生成/编译 | gen kernel dump dir writes source | 准备公开 DSL/IR 输入、目标配置与源码生成入口。 | 运行 `test_gen_kernel_dump_dir_writes_source`。 | 生成源码、IR 文本或编译结果体现“gen kernel dump dir writes source”场景。 | `test_gen_kernel_dump_dir_writes_source` |
| TC-PASS-TILE-ELEWISE-002 | 公开入口 | gen kernel public modules exist and old legacy loader path is gone | 按 spec 声明的导入路径、CLI 参数、注册名或命名空间访问公开入口。 | 运行 `test_gen_kernel_public_modules_exist_and_old_legacy_loader_path_is_gone`。 | 公开入口在“gen kernel public modules exist and old legacy loader path is gone”场景下可导入、构造、注册或按名称发现。 | `test_gen_kernel_public_modules_exist_and_old_legacy_loader_path_is_gone` |
| TC-PASS-TILE-ELEWISE-003 | pass 改写 | tile gen kernel paths use kernel gen tile modules | 准备包含目标 op、pass 名称或 pipeline 的公开 IR 输入。 | 运行 `test_tile_gen_kernel_paths_use_kernel_gen_tile_modules`。 | IR 改写后的 op、属性、顺序或 no-op 行为体现“tile gen kernel paths use kernel gen tile modules”场景。 | `test_tile_gen_kernel_paths_use_kernel_gen_tile_modules` |
| TC-PASS-TILE-ELEWISE-004 | 生成/编译 | gen kernel local compile helpers delegate local compile runner | 准备公开 DSL/IR 输入、目标配置与源码生成入口。 | 运行 `test_gen_kernel_local_compile_helpers_delegate_local_compile_runner`。 | 生成源码、IR 文本或编译结果体现“gen kernel local compile helpers delegate local compile runner”场景。 | `test_gen_kernel_local_compile_helpers_delegate_local_compile_runner` |
| TC-PASS-TILE-ELEWISE-005 | 生成/编译 | gen kernel returns target source | 准备公开 DSL/IR 输入、目标配置与源码生成入口。 | 运行 `test_gen_kernel_returns_target_source`。 | 生成源码、IR 文本或编译结果体现“gen kernel returns target source”场景。 | `test_gen_kernel_returns_target_source` |
| TC-PASS-TILE-ELEWISE-006 | 边界/异常 | gen kernel converts emit error to gen kernel error | 准备触发该错误路径的公开输入或非法参数组合。 | 运行 `test_gen_kernel_converts_emit_error_to_gen_kernel_error`。 | “gen kernel converts emit error to gen kernel error”场景按公开错误语义失败或被拒绝。 | `test_gen_kernel_converts_emit_error_to_gen_kernel_error` |
| TC-PASS-TILE-ELEWISE-007 | 生成/编译 | gen kernel entry module hides internal emitter entry | 准备公开 DSL/IR 输入、目标配置与源码生成入口。 | 运行 `test_gen_kernel_entry_module_hides_internal_emitter_entry`。 | 生成源码、IR 文本或编译结果体现“gen kernel entry module hides internal emitter entry”场景。 | `test_gen_kernel_entry_module_hides_internal_emitter_entry` |
| TC-PASS-TILE-ELEWISE-008 | 公开入口 | gen kernel is the package public entry | 按 spec 声明的导入路径、CLI 参数、注册名或命名空间访问公开入口。 | 运行 `test_gen_kernel_is_the_package_public_entry`。 | 公开入口在“gen kernel is the package public entry”场景下可导入、构造、注册或按名称发现。 | `test_gen_kernel_is_the_package_public_entry` |
| TC-PASS-TILE-ELEWISE-009 | 公开入口 | DSL gen kernel matches public MLIR gen plus gen kernel path | 按 spec 声明的导入路径、CLI 参数、注册名或命名空间访问公开入口。 | 运行 `test_dsl_gen_kernel_matches_public_mlir_gen_plus_gen_kernel_path`。 | 公开入口在“DSL gen kernel matches public MLIR gen plus gen kernel path”场景下可导入、构造、注册或按名称发现。 | `test_dsl_gen_kernel_matches_public_mlir_gen_plus_gen_kernel_path` |
| TC-PASS-TILE-ELEWISE-010 | 生成/编译 | gen kernel has no legacy double interface | 准备公开 DSL/IR 输入、目标配置与源码生成入口。 | 运行 `test_gen_kernel_has_no_legacy_double_interface`。 | 生成源码、IR 文本或编译结果体现“gen kernel has no legacy double interface”场景。 | `test_gen_kernel_has_no_legacy_double_interface` |
| TC-PASS-TILE-ELEWISE-011 | 生成/编译 | gen kernel delegates single op input to emit c | 准备公开 DSL/IR 输入、目标配置与源码生成入口。 | 运行 `test_gen_kernel_delegates_single_op_input_to_emit_c`。 | 生成源码、IR 文本或编译结果体现“gen kernel delegates single op input to emit c”场景。 | `test_gen_kernel_delegates_single_op_input_to_emit_c` |
| TC-PASS-TILE-ELEWISE-012 | 生成/编译 | gen kernel uses mutable memory inputs | 准备公开 DSL/IR 输入、目标配置与源码生成入口。 | 运行 `test_gen_kernel_uses_mutable_memory_inputs`。 | 生成源码、IR 文本或编译结果体现“gen kernel uses mutable memory inputs”场景。 | `test_gen_kernel_uses_mutable_memory_inputs` |
| TC-PASS-TILE-ELEWISE-013 | 生成/编译 | gen kernel accepts rewritten single output function | 准备公开 DSL/IR 输入、目标配置与源码生成入口。 | 运行 `test_gen_kernel_accepts_rewritten_single_output_function`。 | 生成源码、IR 文本或编译结果体现“gen kernel accepts rewritten single output function”场景。 | `test_gen_kernel_accepts_rewritten_single_output_function` |
| TC-PASS-TILE-ELEWISE-014 | 生成/编译 | gen kernel rewritten deslice memory result uses front out param | 准备公开 DSL/IR 输入、目标配置与源码生成入口。 | 运行 `test_gen_kernel_rewritten_deslice_memory_result_uses_front_out_param`。 | 生成源码、IR 文本或编译结果体现“gen kernel rewritten deslice memory result uses front out param”场景。 | `test_gen_kernel_rewritten_deslice_memory_result_uses_front_out_param` |
| TC-PASS-TILE-ELEWISE-015 | 生成/编译 | gen kernel uses default arg names when missing attrs | 准备公开 DSL/IR 输入、目标配置与源码生成入口。 | 运行 `test_gen_kernel_uses_default_arg_names_when_missing_attrs`。 | 生成源码、IR 文本或编译结果体现“gen kernel uses default arg names when missing attrs”场景。 | `test_gen_kernel_uses_default_arg_names_when_missing_attrs` |
| TC-PASS-TILE-ELEWISE-016 | 生成/编译 | gen kernel emits ops in order | 准备公开 DSL/IR 输入、目标配置与源码生成入口。 | 运行 `test_gen_kernel_emits_ops_in_order`。 | 生成源码、IR 文本或编译结果体现“gen kernel emits ops in order”场景。 | `test_gen_kernel_emits_ops_in_order` |
| TC-PASS-TILE-ELEWISE-017 | 生成/编译 | gen kernel delegates to emit c for non return ops | 准备公开 DSL/IR 输入、目标配置与源码生成入口。 | 运行 `test_gen_kernel_delegates_to_emit_c_for_non_return_ops`。 | 生成源码、IR 文本或编译结果体现“gen kernel delegates to emit c for non return ops”场景。 | `test_gen_kernel_delegates_to_emit_c_for_non_return_ops` |
| TC-PASS-TILE-ELEWISE-018 | 生成/编译 | gen kernel handles func return and out binding in main flow | 准备公开 DSL/IR 输入、目标配置与源码生成入口。 | 运行 `test_gen_kernel_handles_func_return_and_out_binding_in_main_flow`。 | 生成源码、IR 文本或编译结果体现“gen kernel handles func return and out binding in main flow”场景。 | `test_gen_kernel_handles_func_return_and_out_binding_in_main_flow` |
| TC-PASS-TILE-ELEWISE-019 | 边界/异常 | kernel emitter public dispatch error boundaries | 准备触发该错误路径的公开输入或非法参数组合。 | 运行 `test_kernel_emitter_public_dispatch_error_boundaries`。 | “kernel emitter public dispatch error boundaries”场景按公开错误语义失败或被拒绝。 | `test_kernel_emitter_public_dispatch_error_boundaries` |
| TC-PASS-TILE-ELEWISE-020 | 公开入口 | kernel emitter public include and type dispatch | 按 spec 声明的导入路径、CLI 参数、注册名或命名空间访问公开入口。 | 运行 `test_kernel_emitter_public_include_and_type_dispatch`。 | 公开入口在“kernel emitter public include and type dispatch”场景下可导入、构造、注册或按名称发现。 | `test_kernel_emitter_public_include_and_type_dispatch` |
| TC-PASS-TILE-ELEWISE-021 | 生成/编译 | gen kernel assembles loop body | 准备公开 DSL/IR 输入、目标配置与源码生成入口。 | 运行 `test_gen_kernel_assembles_loop_body`。 | 生成源码、IR 文本或编译结果体现“gen kernel assembles loop body”场景。 | `test_gen_kernel_assembles_loop_body` |
| TC-PASS-TILE-ELEWISE-022 | 边界/异常 | gen kernel propagates emit error | 准备触发该错误路径的公开输入或非法参数组合。 | 运行 `test_gen_kernel_propagates_emit_error`。 | “gen kernel propagates emit error”场景按公开错误语义失败或被拒绝。 | `test_gen_kernel_propagates_emit_error` |
| TC-PASS-TILE-ELEWISE-023 | 边界/异常 | gen kernel rejects unsupported return form | 准备触发该错误路径的公开输入或非法参数组合。 | 运行 `test_gen_kernel_rejects_unsupported_return_form`。 | “gen kernel rejects unsupported return form”场景按公开错误语义失败或被拒绝。 | `test_gen_kernel_rejects_unsupported_return_form` |
| TC-PASS-TILE-ELEWISE-024 | 生成/编译 | gen kernel supports float32 scalar and memory | 准备公开 DSL/IR 输入、目标配置与源码生成入口。 | 运行 `test_gen_kernel_supports_float32_scalar_and_memory`。 | 生成源码、IR 文本或编译结果体现“gen kernel supports float32 scalar and memory”场景。 | `test_gen_kernel_supports_float32_scalar_and_memory` |
| TC-PASS-TILE-ELEWISE-025 | 生成/编译 | gen kernel preserves function and arg names | 准备公开 DSL/IR 输入、目标配置与源码生成入口。 | 运行 `test_gen_kernel_preserves_function_and_arg_names`。 | 生成源码、IR 文本或编译结果体现“gen kernel preserves function and arg names”场景。 | `test_gen_kernel_preserves_function_and_arg_names` |
| TC-PASS-TILE-ELEWISE-026 | 生成/编译 | gen kernel supports symbol scalar return | 准备公开 DSL/IR 输入、目标配置与源码生成入口。 | 运行 `test_gen_kernel_supports_symbol_scalar_return`。 | 生成源码、IR 文本或编译结果体现“gen kernel supports symbol scalar return”场景。 | `test_gen_kernel_supports_symbol_scalar_return` |
| TC-PASS-TILE-ELEWISE-027 | 边界/异常 | gen kernel rejects symbol scalar return on non cpu | 准备触发该错误路径的公开输入或非法参数组合。 | 运行 `test_gen_kernel_rejects_symbol_scalar_return_on_non_cpu`。 | “gen kernel rejects symbol scalar return on non cpu”场景按公开错误语义失败或被拒绝。 | `test_gen_kernel_rejects_symbol_scalar_return_on_non_cpu` |
| TC-PASS-TILE-ELEWISE-028 | pass 改写 | gen kernel supports lowered NN add memory memory on cpu | 准备包含目标 op、pass 名称或 pipeline 的公开 IR 输入。 | 运行 `test_gen_kernel_supports_lowered_nn_add_memory_memory_on_cpu`。 | IR 改写后的 op、属性、顺序或 no-op 行为体现“gen kernel supports lowered NN add memory memory on cpu”场景。 | `test_gen_kernel_supports_lowered_nn_add_memory_memory_on_cpu` |
| TC-PASS-TILE-ELEWISE-029 | pass 改写 | gen kernel supports lowered NN add memory const on cpu | 准备包含目标 op、pass 名称或 pipeline 的公开 IR 输入。 | 运行 `test_gen_kernel_supports_lowered_nn_add_memory_const_on_cpu`。 | IR 改写后的 op、属性、顺序或 no-op 行为体现“gen kernel supports lowered NN add memory const on cpu”场景。 | `test_gen_kernel_supports_lowered_nn_add_memory_const_on_cpu` |
| TC-PASS-TILE-ELEWISE-030 | pass 改写 | gen kernel supports lowered NN add memory symbol on cpu | 准备包含目标 op、pass 名称或 pipeline 的公开 IR 输入。 | 运行 `test_gen_kernel_supports_lowered_nn_add_memory_symbol_on_cpu`。 | IR 改写后的 op、属性、顺序或 no-op 行为体现“gen kernel supports lowered NN add memory symbol on cpu”场景。 | `test_gen_kernel_supports_lowered_nn_add_memory_symbol_on_cpu` |
| TC-PASS-TILE-ELEWISE-031 | 生成/编译 | gen kernel accepts rewritten single output function | 准备公开 DSL/IR 输入、目标配置与源码生成入口。 | 运行 `test_gen_kernel_accepts_rewritten_single_output_function`。 | 生成源码、IR 文本或编译结果体现“gen kernel accepts rewritten single output function”场景。 | `test_gen_kernel_accepts_rewritten_single_output_function` |
| TC-PASS-TILE-ELEWISE-032 | 生成/编译 | gen kernel accepts rewritten mixed output function | 准备公开 DSL/IR 输入、目标配置与源码生成入口。 | 运行 `test_gen_kernel_accepts_rewritten_mixed_output_function`。 | 生成源码、IR 文本或编译结果体现“gen kernel accepts rewritten mixed output function”场景。 | `test_gen_kernel_accepts_rewritten_mixed_output_function` |
| TC-PASS-TILE-ELEWISE-033 | pass 改写 | rewritten pipeline has no memory return abi left | 准备包含目标 op、pass 名称或 pipeline 的公开 IR 输入。 | 运行 `test_rewritten_pipeline_has_no_memory_return_abi_left`。 | IR 改写后的 op、属性、顺序或 no-op 行为体现“rewritten pipeline has no memory return abi left”场景。 | `test_rewritten_pipeline_has_no_memory_return_abi_left` |
| TC-PASS-TILE-ELEWISE-034 | 边界/异常 | gen kernel rejects lowered IR without buffer results to out params | 准备触发该错误路径的公开输入或非法参数组合。 | 运行 `test_gen_kernel_rejects_lowered_ir_without_buffer_results_to_out_params`。 | “gen kernel rejects lowered IR without buffer results to out params”场景按公开错误语义失败或被拒绝。 | `test_gen_kernel_rejects_lowered_ir_without_buffer_results_to_out_params` |
| TC-PASS-TILE-ELEWISE-035 | 边界/异常 | rewritten pipeline fails on half rewritten IR | 准备触发该错误路径的公开输入或非法参数组合。 | 运行 `test_rewritten_pipeline_fails_on_half_rewritten_ir`。 | “rewritten pipeline fails on half rewritten IR”场景按公开错误语义失败或被拒绝。 | `test_rewritten_pipeline_fails_on_half_rewritten_ir` |
| TC-PASS-TILE-ELEWISE-036 | 生成/编译 | gen kernel emits npu demo body level kernel | 准备公开 DSL/IR 输入、目标配置与源码生成入口。 | 运行 `test_gen_kernel_emits_npu_demo_body_level_kernel`。 | 生成源码、IR 文本或编译结果体现“gen kernel emits npu demo body level kernel”场景。 | `test_gen_kernel_emits_npu_demo_body_level_kernel` |
| TC-PASS-TILE-ELEWISE-037 | 生成/编译 | gen kernel emits npu demo kernel binary signature out first | 准备公开 DSL/IR 输入、目标配置与源码生成入口。 | 运行 `test_gen_kernel_emits_npu_demo_kernel_binary_signature_out_first`。 | 生成源码、IR 文本或编译结果体现“gen kernel emits npu demo kernel binary signature out first”场景。 | `test_gen_kernel_emits_npu_demo_kernel_binary_signature_out_first` |
| TC-PASS-TILE-ELEWISE-038 | 生成/编译 | gen kernel emits npu demo DMA alloc module | 准备公开 DSL/IR 输入、目标配置与源码生成入口。 | 运行 `test_gen_kernel_emits_npu_demo_dma_alloc_module`。 | 生成源码、IR 文本或编译结果体现“gen kernel emits npu demo DMA alloc module”场景。 | `test_gen_kernel_emits_npu_demo_dma_alloc_module` |
| TC-PASS-TILE-ELEWISE-039 | 生成/编译 | gen kernel compiles npu demo source with single include | 准备公开 DSL/IR 输入、目标配置与源码生成入口。 | 运行 `test_gen_kernel_compiles_npu_demo_source_with_single_include`。 | 生成源码、IR 文本或编译结果体现“gen kernel compiles npu demo source with single include”场景。 | `test_gen_kernel_compiles_npu_demo_source_with_single_include` |
| TC-PASS-TILE-ELEWISE-040 | pass 改写 | gen kernel compiles npu demo tiled matmul source | 准备包含目标 op、pass 名称或 pipeline 的公开 IR 输入。 | 运行 `test_gen_kernel_compiles_npu_demo_tiled_matmul_source`。 | IR 改写后的 op、属性、顺序或 no-op 行为体现“gen kernel compiles npu demo tiled matmul source”场景。 | `test_gen_kernel_compiles_npu_demo_tiled_matmul_source` |
| TC-PASS-TILE-ELEWISE-041 | pass 改写 | gen kernel emits npu demo memory pipeline | 准备包含目标 op、pass 名称或 pipeline 的公开 IR 输入。 | 运行 `test_gen_kernel_emits_npu_demo_memory_pipeline`。 | IR 改写后的 op、属性、顺序或 no-op 行为体现“gen kernel emits npu demo memory pipeline”场景。 | `test_gen_kernel_emits_npu_demo_memory_pipeline` |
| TC-PASS-TILE-ELEWISE-042 | 边界/异常 | gen kernel rejects npu demo body level kernel with unknown body op | 准备触发该错误路径的公开输入或非法参数组合。 | 运行 `test_gen_kernel_rejects_npu_demo_body_level_kernel_with_unknown_body_op`。 | “gen kernel rejects npu demo body level kernel with unknown body op”场景按公开错误语义失败或被拒绝。 | `test_gen_kernel_rejects_npu_demo_body_level_kernel_with_unknown_body_op` |
| TC-PASS-TILE-ELEWISE-043 | 边界/异常 | gen kernel rejects npu demo body level kernel with nonempty body | 准备触发该错误路径的公开输入或非法参数组合。 | 运行 `test_gen_kernel_rejects_npu_demo_body_level_kernel_with_nonempty_body`。 | “gen kernel rejects npu demo body level kernel with nonempty body”场景按公开错误语义失败或被拒绝。 | `test_gen_kernel_rejects_npu_demo_body_level_kernel_with_nonempty_body` |
| TC-PASS-TILE-ELEWISE-044 | pass 改写 | gen kernel black box lowered add and npu demo contracts | 准备包含目标 op、pass 名称或 pipeline 的公开 IR 输入。 | 运行 `test_gen_kernel_black_box_lowered_add_and_npu_demo_contracts`。 | IR 改写后的 op、属性、顺序或 no-op 行为体现“gen kernel black box lowered add and npu demo contracts”场景。 | `test_gen_kernel_black_box_lowered_add_and_npu_demo_contracts` |
| TC-PASS-TILE-ELEWISE-045 | pass 改写 | gen kernel compiles and runs lowered NN add variants on cpu | 准备包含目标 op、pass 名称或 pipeline 的公开 IR 输入。 | 运行 `test_gen_kernel_compiles_and_runs_lowered_nn_add_variants_on_cpu`。 | IR 改写后的 op、属性、顺序或 no-op 行为体现“gen kernel compiles and runs lowered NN add variants on cpu”场景。 | `test_gen_kernel_compiles_and_runs_lowered_nn_add_variants_on_cpu` |
| TC-PASS-TILE-ELEWISE-046 | pass 改写 | gen kernel emits tile codegen single function tile loop | 准备包含目标 op、pass 名称或 pipeline 的公开 IR 输入。 | 运行 `test_gen_kernel_emits_tile_codegen_single_function_tile_loop`。 | IR 改写后的 op、属性、顺序或 no-op 行为体现“gen kernel emits tile codegen single function tile loop”场景。 | `test_gen_kernel_emits_tile_codegen_single_function_tile_loop` |
| TC-PASS-TILE-ELEWISE-047 | 边界/异常 | gen kernel rejects tile codegen missing tuner param | 准备触发该错误路径的公开输入或非法参数组合。 | 运行 `test_gen_kernel_rejects_tile_codegen_missing_tuner_param`。 | “gen kernel rejects tile codegen missing tuner param”场景按公开错误语义失败或被拒绝。 | `test_gen_kernel_rejects_tile_codegen_missing_tuner_param` |
| TC-PASS-TILE-ELEWISE-048 | 边界/异常 | gen kernel rejects tile codegen missing loop | 准备触发该错误路径的公开输入或非法参数组合。 | 运行 `test_gen_kernel_rejects_tile_codegen_missing_loop`。 | “gen kernel rejects tile codegen missing loop”场景按公开错误语义失败或被拒绝。 | `test_gen_kernel_rejects_tile_codegen_missing_loop` |
| TC-PASS-TILE-ELEWISE-049 | 边界/异常 | gen kernel rejects tile codegen with helper call | 准备触发该错误路径的公开输入或非法参数组合。 | 运行 `test_gen_kernel_rejects_tile_codegen_with_helper_call`。 | “gen kernel rejects tile codegen with helper call”场景按公开错误语义失败或被拒绝。 | `test_gen_kernel_rejects_tile_codegen_with_helper_call` |
| TC-PASS-TILE-ELEWISE-050 | 边界/异常 | gen kernel rejects legacy split tuner param contract | 准备触发该错误路径的公开输入或非法参数组合。 | 运行 `test_gen_kernel_rejects_legacy_split_tuner_param_contract`。 | “gen kernel rejects legacy split tuner param contract”场景按公开错误语义失败或被拒绝。 | `test_gen_kernel_rejects_legacy_split_tuner_param_contract` |
| TC-PASS-TILE-ELEWISE-051 | pass 改写 | gen kernel emits tile elewise cpu source for elementwise and broadcast | 准备包含目标 op、pass 名称或 pipeline 的公开 IR 输入。 | 运行 `test_gen_kernel_emits_tile_elewise_cpu_source_for_elementwise_and_broadcast`。 | IR 改写后的 op、属性、顺序或 no-op 行为体现“gen kernel emits tile elewise cpu source for elementwise and broadcast”场景。 | `test_gen_kernel_emits_tile_elewise_cpu_source_for_elementwise_and_broadcast` |
| TC-PASS-TILE-ELEWISE-052 | 生成/编译 | gen kernel emits npu demo launch wrapper and barrier body | 准备公开 DSL/IR 输入、目标配置与源码生成入口。 | 运行 `test_gen_kernel_emits_npu_demo_launch_wrapper_and_barrier_body`。 | 生成源码、IR 文本或编译结果体现“gen kernel emits npu demo launch wrapper and barrier body”场景。 | `test_gen_kernel_emits_npu_demo_launch_wrapper_and_barrier_body` |
| TC-PASS-TILE-ELEWISE-053 | 生成/编译 | gen kernel compiles npu demo launch wrapper and barrier body | 准备公开 DSL/IR 输入、目标配置与源码生成入口。 | 运行 `test_gen_kernel_compiles_npu_demo_launch_wrapper_and_barrier_body`。 | 生成源码、IR 文本或编译结果体现“gen kernel compiles npu demo launch wrapper and barrier body”场景。 | `test_gen_kernel_compiles_npu_demo_launch_wrapper_and_barrier_body` |
| TC-PASS-TILE-ELEWISE-054 | 生成/编译 | gen kernel emits npu demo cost functions for compute and memory | 准备公开 DSL/IR 输入、目标配置与源码生成入口。 | 运行 `test_gen_kernel_emits_npu_demo_cost_functions_for_compute_and_memory`。 | 生成源码、IR 文本或编译结果体现“gen kernel emits npu demo cost functions for compute and memory”场景。 | `test_gen_kernel_emits_npu_demo_cost_functions_for_compute_and_memory` |
| TC-PASS-TILE-ELEWISE-055 | 生成/编译 | gen kernel compiles npu demo cost function module | 准备公开 DSL/IR 输入、目标配置与源码生成入口。 | 运行 `test_gen_kernel_compiles_npu_demo_cost_function_module`。 | 生成源码、IR 文本或编译结果体现“gen kernel compiles npu demo cost function module”场景。 | `test_gen_kernel_compiles_npu_demo_cost_function_module` |
| TC-PASS-TILE-ELEWISE-056 | pass 改写 | gen kernel compiles outlined npu demo launch module | 准备包含目标 op、pass 名称或 pipeline 的公开 IR 输入。 | 运行 `test_gen_kernel_compiles_outlined_npu_demo_launch_module`。 | IR 改写后的 op、属性、顺序或 no-op 行为体现“gen kernel compiles outlined npu demo launch module”场景。 | `test_gen_kernel_compiles_outlined_npu_demo_launch_module` |
| TC-PASS-TILE-ELEWISE-057 | 生成/编译 | gen kernel npu demo add barrier runtime smoke | 准备公开 DSL/IR 输入、目标配置与源码生成入口。 | 运行 `test_gen_kernel_npu_demo_add_barrier_runtime_smoke`。 | 生成源码、IR 文本或编译结果体现“gen kernel npu demo add barrier runtime smoke”场景。 | `test_gen_kernel_npu_demo_add_barrier_runtime_smoke` |
| TC-PASS-TILE-ELEWISE-058 | 边界/异常 | gen kernel rejects npu demo barrier wrapper missing body symbol | 准备触发该错误路径的公开输入或非法参数组合。 | 运行 `test_gen_kernel_rejects_npu_demo_barrier_wrapper_missing_body_symbol`。 | “gen kernel rejects npu demo barrier wrapper missing body symbol”场景按公开错误语义失败或被拒绝。 | `test_gen_kernel_rejects_npu_demo_barrier_wrapper_missing_body_symbol` |
| TC-PASS-TILE-ELEWISE-059 | 边界/异常 | gen kernel rejects npu demo barrier fail fast boundaries | 准备触发该错误路径的公开输入或非法参数组合。 | 运行 `test_gen_kernel_rejects_npu_demo_barrier_fail_fast_boundaries`。 | “gen kernel rejects npu demo barrier fail fast boundaries”场景按公开错误语义失败或被拒绝。 | `test_gen_kernel_rejects_npu_demo_barrier_fail_fast_boundaries` |
| TC-PASS-TILE-ELEWISE-060 | 公开入口 | tile elewise public API surface is stable | 按 spec 声明的导入路径、CLI 参数、注册名或命名空间访问公开入口。 | 运行 `test_tile_elewise_public_api_surface_is_stable`。 | 公开入口在“tile elewise public API surface is stable”场景下可导入、构造、注册或按名称发现。 | `test_tile_elewise_public_api_surface_is_stable` |
| TC-PASS-TILE-ELEWISE-061 | pass 改写 | tile elewise binary pattern rewrites single add op | 准备包含目标 op、pass 名称或 pipeline 的公开 IR 输入。 | 运行 `test_tile_elewise_binary_pattern_rewrites_single_add_op`。 | IR 改写后的 op、属性、顺序或 no-op 行为体现“tile elewise binary pattern rewrites single add op”场景。 | `test_tile_elewise_binary_pattern_rewrites_single_add_op` |
| TC-PASS-TILE-ELEWISE-062 | pass 改写 | tile elewise broadcast pattern rewrites single broadcast op | 准备包含目标 op、pass 名称或 pipeline 的公开 IR 输入。 | 运行 `test_tile_elewise_broadcast_pattern_rewrites_single_broadcast_op`。 | IR 改写后的 op、属性、顺序或 no-op 行为体现“tile elewise broadcast pattern rewrites single broadcast op”场景。 | `test_tile_elewise_broadcast_pattern_rewrites_single_broadcast_op` |
| TC-PASS-TILE-ELEWISE-063 | pass 改写 | tile elewise matmul pattern rewrites single matmul op | 准备包含目标 op、pass 名称或 pipeline 的公开 IR 输入。 | 运行 `test_tile_elewise_matmul_pattern_rewrites_single_matmul_op`。 | IR 改写后的 op、属性、顺序或 no-op 行为体现“tile elewise matmul pattern rewrites single matmul op”场景。 | `test_tile_elewise_matmul_pattern_rewrites_single_matmul_op` |
| TC-PASS-TILE-ELEWISE-064 | pass 改写 | tile elewise pass rewrites multiple top level plans | 准备包含目标 op、pass 名称或 pipeline 的公开 IR 输入。 | 运行 `test_tile_elewise_pass_rewrites_multiple_top_level_plans`。 | IR 改写后的 op、属性、顺序或 no-op 行为体现“tile elewise pass rewrites multiple top level plans”场景。 | `test_tile_elewise_pass_rewrites_multiple_top_level_plans` |
| TC-PASS-TILE-ELEWISE-065 | pass 改写 | tile elewise pass fc chain keeps reduce axis until tile reduce | 准备包含目标 op、pass 名称或 pipeline 的公开 IR 输入。 | 运行 `test_tile_elewise_pass_fc_chain_keeps_reduce_axis_until_tile_reduce`。 | IR 改写后的 op、属性、顺序或 no-op 行为体现“tile elewise pass fc chain keeps reduce axis until tile reduce”场景。 | `test_tile_elewise_pass_fc_chain_keeps_reduce_axis_until_tile_reduce` |
| TC-PASS-TILE-ELEWISE-066 | pass 改写 | tile elewise matmul pattern accepts legacy operand order without reordering | 准备包含目标 op、pass 名称或 pipeline 的公开 IR 输入。 | 运行 `test_tile_elewise_matmul_pattern_accepts_legacy_operand_order_without_reordering`。 | IR 改写后的 op、属性、顺序或 no-op 行为体现“tile elewise matmul pattern accepts legacy operand order without reordering”场景。 | `test_tile_elewise_matmul_pattern_accepts_legacy_operand_order_without_reordering` |
| TC-PASS-TILE-ELEWISE-067 | pass 改写 | tile elewise binary pattern covers compare/rank/no-op/error boundaries | 准备包含 compare kind、rank-1/rank-3、缺失或非法 `tile.analysis` 的公开 IR 输入。 | 运行 `test_tile_elewise_binary_pattern_public_compare_and_boundary_matrix`。 | compare rewrite 保持 `out/lhs/rhs` 公开 operand 顺序，rank-1/rank-3 正常重写，缺失 analysis no-op，非法 analysis 或 rank mismatch 按公开错误语义失败。 | `test_tile_elewise_binary_pattern_public_compare_and_boundary_matrix` |
| TC-PASS-TILE-ELEWISE-068 | pass 改写 | tile elewise broadcast pattern covers no-op/expand/error boundaries | 准备缺失 analysis、rank-0、all-expand、partial-expand 与非法 analysis 的公开 `dma.broadcast` 输入。 | 运行 `test_tile_elewise_broadcast_pattern_public_boundary_matrix`。 | broadcast no-op、tile expr、target/source view shape 与公开错误语义稳定。 | `test_tile_elewise_broadcast_pattern_public_boundary_matrix` |
| TC-PASS-TILE-ELEWISE-069 | pass 改写 | tile elewise matmul pattern keeps public no-op shape boundaries | 准备缺失 analysis、rank 不匹配或 shape 关系不匹配的公开 `kernel.matmul` 输入。 | 运行 `test_tile_elewise_matmul_pattern_public_noop_shape_boundaries`。 | 不满足 matmul role/shape 合同的输入保持 no-op，不生成 `symbol.for`。 | `test_tile_elewise_matmul_pattern_public_noop_shape_boundaries` |
