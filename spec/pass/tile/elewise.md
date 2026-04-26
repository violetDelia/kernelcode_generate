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
- `TileElewiseBinaryPattern`
  - `—— match_and_rewrite(op: KernelBinaryElewiseOp, rewriter: PatternRewriter)`
- `TileElewiseBroadcastPattern`
  - `—— match_and_rewrite(op: DmaBroadcastOp, rewriter: PatternRewriter)`
- `TileElewiseMatmulPattern`
  - `—— match_and_rewrite(op: KernelMatmulOp, rewriter: PatternRewriter)`
- `TileElewisePass`
  - `—— apply(ctx: Context, module: ModuleOp)`
- `get_tile_elewise_pass_patterns() -> list[RewritePattern]`

## 文档信息

- 创建者：`小李飞刀`
- 最后一次更改：`OpenAI Codex`
- `spec`：[`spec/pass/tile/elewise.md`](../../../spec/pass/tile/elewise.md)
- `功能实现`：
  - [`kernel_gen/passes/registry.py`](../../../kernel_gen/passes/registry.py)
  - [`kernel_gen/passes/tile/elewise.py`](../../../kernel_gen/passes/tile/elewise.py)
- `test`：
  - [`test/pass/tile/test_elewise.py`](../../../test/pass/tile/test_elewise.py)
  - [`test/dsl/gen_kernel/test_gen_kernel.py`](../../../test/dsl/gen_kernel/test_gen_kernel.py)

## 依赖

- tile package 总览：[`spec/pass/tile/README.md`](../../../spec/pass/tile/README.md)
- `tile-analysis`：[`spec/pass/tile/analysis.md`](../../../spec/pass/tile/analysis.md)
- 后端代码生成：[`spec/dsl/gen_kernel/gen_kernel.md`](../../../spec/dsl/gen_kernel/gen_kernel.md)

## 目标

- 保持公开 pass 名固定为 `tile-elewise`。
- 保持当前文件内公开 API 只覆盖 pass、getter 和 3 个 pattern。
- 只消费顶层 `kernel.binary_elewise`、`dma.broadcast`、`kernel.matmul` 目标 op，不再公开额外 helper API。

## 公开接口

### `build_registered_pass("tile-elewise")`

功能说明：

- 构造 `tile-elewise` 的公开 `ModulePass`。

使用示例：

```python
from xdsl.context import Context
from kernel_gen.passes.registry import build_registered_pass

build_registered_pass("tile-elewise").apply(Context(), module)
```

### `kernel_gen.passes.tile.elewise`

功能说明：

- 当前文件公开对象集合固定为：
  - `TileElewiseBinaryPattern`
  - `TileElewiseBroadcastPattern`
  - `TileElewiseMatmulPattern`
  - `TileElewisePass`
  - `get_tile_elewise_pass_patterns()`

使用示例：

```python
from kernel_gen.passes.tile.elewise import (
    TileElewiseBinaryPattern,
    TileElewisePass,
    get_tile_elewise_pass_patterns,
)

patterns = get_tile_elewise_pass_patterns()
assert type(patterns[0]) is TileElewiseBinaryPattern
```

返回与限制：

- getter 的稳定顺序固定为 `Binary -> Broadcast -> Matmul`。
- `TileElewiseBinaryPattern` 覆盖当前实现支持的 binary / compare `kind`：
  - `add/sub/mul/div/truediv`
  - `eq/ne/lt/le/gt/ge`
- pattern 命中后直接改写当前顶层 tile op，不再公开共享 rewrite helper。

## helper 边界

- 当前文件内除上述 5 个公开对象外，不再承诺任何其他稳定 helper。
- 跨文件实现不得调用本文件未列入公开 API 集合的名字。
- 测试不得把未列入公开 API 集合的名字当作公开接口断言。

## 测试

- 测试文件：
  - [`test/pass/tile/test_elewise.py`](../../../test/pass/tile/test_elewise.py)
  - [`test/dsl/gen_kernel/test_gen_kernel.py`](../../../test/dsl/gen_kernel/test_gen_kernel.py)
- 执行命令：
  - `pytest -q test/pass/tile/test_elewise.py`
  - `pytest -q test/dsl/gen_kernel/test_gen_kernel.py -k "tile_elewise or tile"`
- 测试目标：
  - `tile-elewise` 可通过 registry 构造
  - 公开 getter 顺序稳定
  - 公开 pattern 只通过本文件列出的公开 API 对外暴露
