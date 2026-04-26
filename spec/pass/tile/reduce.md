# tile reduce

## 功能简介

- `tile-reduce` 的实现与公开合同固定收口在 [`kernel_gen/passes/tile/reduce.py`](../../../kernel_gen/passes/tile/reduce.py)。
- 它消费已有 `tile.analysis` 与 `tile.tile_exprs`，对当前顶层 `kernel.matmul` 只生成 reduce 轴一层 loop 的结构。
- 当前公开 pattern 只包含 `TileReduceMatmulPattern`。

## API 列表

- `build_registered_pass(name: str, options: dict[str, str] | None = None) -> ModulePass`
- `TileReduceMatmulPattern`
  - `—— match_and_rewrite(op: KernelMatmulOp, rewriter: PatternRewriter)`
- `TileReducePass`
  - `—— apply(ctx: Context, module: ModuleOp)`
- `get_tile_reduce_pass_patterns() -> list[RewritePattern]`

## 文档信息

- 创建者：`金铲铲大作战`
- 最后一次更改：`OpenAI Codex`
- `spec`：[`spec/pass/tile/reduce.md`](../../../spec/pass/tile/reduce.md)
- `功能实现`：
  - [`kernel_gen/passes/registry.py`](../../../kernel_gen/passes/registry.py)
  - [`kernel_gen/passes/tile/reduce.py`](../../../kernel_gen/passes/tile/reduce.py)
- `test`：
  - [`test/pass/tile/test_reduce.py`](../../../test/pass/tile/test_reduce.py)
  - [`test/dsl/gen_kernel/test_gen_kernel.py`](../../../test/dsl/gen_kernel/test_gen_kernel.py)

## 依赖

- tile package 总览：[`spec/pass/tile/README.md`](../../../spec/pass/tile/README.md)
- `tile-analysis`：[`spec/pass/tile/analysis.md`](../../../spec/pass/tile/analysis.md)
- 后端代码生成：[`spec/dsl/gen_kernel/gen_kernel.md`](../../../spec/dsl/gen_kernel/gen_kernel.md)

## 目标

- 保持公开 pass 名固定为 `tile-reduce`。
- 保持当前文件内公开 API 只覆盖 pass、getter 和 `TileReduceMatmulPattern`。
- 只处理顶层 `kernel.matmul` 的 reduce 轴切分，不引入输出轴 `tuner.param`，也不公开共享 rewrite helper。

## 公开接口

### `build_registered_pass("tile-reduce")`

功能说明：

- 构造 `tile-reduce` 的公开 `ModulePass`。

使用示例：

```python
from xdsl.context import Context
from kernel_gen.passes.registry import build_registered_pass

build_registered_pass("tile-reduce").apply(Context(), module)
```

### `kernel_gen.passes.tile.reduce`

功能说明：

- 当前文件公开对象集合固定为：
  - `TileReduceMatmulPattern`
  - `TileReducePass`
  - `get_tile_reduce_pass_patterns()`

使用示例：

```python
from kernel_gen.passes.tile.reduce import (
    TileReduceMatmulPattern,
    TileReducePass,
    get_tile_reduce_pass_patterns,
)

patterns = get_tile_reduce_pass_patterns()
assert type(patterns[0]) is TileReduceMatmulPattern
```

返回与限制：

- getter 当前只返回 `TileReduceMatmulPattern`。
- pattern 命中后直接改写当前顶层 `kernel.matmul`，并写出“一层 reduce `symbol.for`、两个 reduce `dma.view`、两个 `dma.fill`、一个临时 `dma.alloc`”结构。

## helper 边界

- 当前文件内除上述 3 个公开对象外，不再承诺任何其他稳定 helper。
- 跨文件实现不得调用本文件未列入公开 API 集合的名字。
- 测试不得把未列入公开 API 集合的名字当作公开接口断言。

## 测试

- 测试文件：
  - [`test/pass/tile/test_reduce.py`](../../../test/pass/tile/test_reduce.py)
  - [`test/dsl/gen_kernel/test_gen_kernel.py`](../../../test/dsl/gen_kernel/test_gen_kernel.py)
- 执行命令：
  - `pytest -q test/pass/tile/test_reduce.py`
  - `pytest -q test/dsl/gen_kernel/test_gen_kernel.py -k "tile_reduce or tile"`
- 测试目标：
  - `tile-reduce` 可通过 registry 构造
  - getter 只公开 `TileReduceMatmulPattern`
  - 公开 pattern 只通过本文件列出的公开 API 对外暴露
