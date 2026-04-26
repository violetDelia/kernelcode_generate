# tile analysis

## 功能简介

- `tile-analysis` 的实现与公开合同固定收口在 [`kernel_gen/passes/tile/analysis.py`](../../../kernel_gen/passes/tile/analysis.py)。
- 该 pass 只为当前 op 补 `tile.analysis` 与 `tile.tile_exprs`，不生成 `symbol.for`、`dma.view` 或其他 rewrite 结构。
- 当前公开 pattern 只包含：
  - `TileAnalysisBinaryPattern`
  - `TileAnalysisBroadcastPattern`
  - `TileAnalysisMatmulPattern`

## API 列表

- `build_registered_pass(name: str, options: dict[str, str] | None = None) -> ModulePass`
- `TileAnalysisBinaryPattern`
  - `—— match_and_rewrite(op: KernelBinaryElewiseOp, rewriter: PatternRewriter)`
- `TileAnalysisBroadcastPattern`
  - `—— match_and_rewrite(op: DmaBroadcastOp, rewriter: PatternRewriter)`
- `TileAnalysisMatmulPattern`
  - `—— match_and_rewrite(op: KernelMatmulOp, rewriter: PatternRewriter)`
- `TileAnalysisPass`
  - `—— apply(ctx: Context, module: ModuleOp)`
- `get_tile_analysis_pass_patterns() -> list[RewritePattern]`

## 文档信息

- 创建者：`朽木露琪亚`
- 最后一次更改：`OpenAI Codex`
- `spec`：[`spec/pass/tile/analysis.md`](../../../spec/pass/tile/analysis.md)
- `功能实现`：
  - [`kernel_gen/passes/registry.py`](../../../kernel_gen/passes/registry.py)
  - [`kernel_gen/passes/tile/analysis.py`](../../../kernel_gen/passes/tile/analysis.py)
- `test`：
  - [`test/pass/tile/test_analysis.py`](../../../test/pass/tile/test_analysis.py)
  - [`test/dsl/gen_kernel/test_gen_kernel.py`](../../../test/dsl/gen_kernel/test_gen_kernel.py)

## 依赖

- tile package 总览：[`spec/pass/tile/README.md`](../../../spec/pass/tile/README.md)
- pass 执行器：[`spec/pass/pass_manager.md`](../../../spec/pass/pass_manager.md)
- 注册表：[`spec/pass/registry.md`](../../../spec/pass/registry.md)

## 目标

- 保持公开 pass 名固定为 `tile-analysis`。
- 保持当前文件内公开 API 只覆盖 pass、getter 和 3 个 pattern。
- 只为当前命中的 op 补 analysis 属性，不隐式改写所属函数的 loop/view 结构。

## 公开接口

### `build_registered_pass("tile-analysis")`

功能说明：

- 构造 `tile-analysis` 的公开 `ModulePass`。

使用示例：

```python
from xdsl.context import Context
from xdsl.dialects.builtin import ModuleOp
from kernel_gen.passes.registry import build_registered_pass

module = ModuleOp([])
build_registered_pass("tile-analysis").apply(Context(), module)
```

### `kernel_gen.passes.tile.analysis`

功能说明：

- 当前文件公开对象集合固定为：
  - `TileAnalysisBinaryPattern`
  - `TileAnalysisBroadcastPattern`
  - `TileAnalysisMatmulPattern`
  - `TileAnalysisPass`
  - `get_tile_analysis_pass_patterns()`

使用示例：

```python
from kernel_gen.passes.tile.analysis import (
    TileAnalysisBinaryPattern,
    TileAnalysisPass,
    get_tile_analysis_pass_patterns,
)

patterns = get_tile_analysis_pass_patterns()
assert type(patterns[0]) is TileAnalysisBinaryPattern
```

返回与限制：

- pattern getter 的稳定顺序固定为 `Binary -> Broadcast -> Matmul`。
- 3 个 pattern 都是 op-level pattern，只处理当前命中的目标 op。

## helper 边界

- 当前文件内除上述 5 个公开对象外，不再承诺任何其他稳定 helper。
- 跨文件实现不得调用本文件未列入公开 API 集合的名字。
- 测试不得把未列入公开 API 集合的名字当作公开接口断言。

## 测试

- 测试文件：
  - [`test/pass/tile/test_analysis.py`](../../../test/pass/tile/test_analysis.py)
  - [`test/dsl/gen_kernel/test_gen_kernel.py`](../../../test/dsl/gen_kernel/test_gen_kernel.py)
- 执行命令：
  - `pytest -q test/pass/tile/test_analysis.py`
  - `pytest -q test/dsl/gen_kernel/test_gen_kernel.py -k "tile_analysis or tile"`
- 测试目标：
  - `tile-analysis` 可通过 registry 构造
  - 公开 getter 顺序稳定
  - 公开 pattern 只为当前 op 补 `tile.analysis` 与 `tile.tile_exprs`
