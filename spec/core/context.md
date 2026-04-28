# context.md

## 功能简介

定义仓库统一的 xDSL `Context` 构造入口，用于 IR 文本解析与打印类工具共享 dialect 注册集合。

## API 列表

- `build_default_context() -> Context`

## 文档信息

- 创建者：`榕`
- 最后一次更改：`榕`
- `spec`：[`spec/core/context.md`](../../spec/core/context.md)
- `test`：[`test/tools/test_mlir_gen_compare.py`](../../test/tools/test_mlir_gen_compare.py)
- `功能实现`：[`kernel_gen/core/context.py`](../../kernel_gen/core/context.py)

## 依赖

- `xdsl.context.Context`：承载 dialect 注册集合。
- `xdsl.dialects.builtin.Builtin`
- `xdsl.dialects.func.Func`
- `xdsl.dialects.arith.Arith`
- `xdsl.dialects.scf.Scf`
- `kernel_gen.dialect.nn.Nn`
- `kernel_gen.dialect.kernel.Kernel`
- `kernel_gen.dialect.symbol.Symbol`
- `kernel_gen.dialect.tuner.Tuner`
- `kernel_gen.dialect.dma.Dma`
- `kernel_gen.dialect.arch.Arch`

## 公开接口

### `build_default_context() -> Context`

功能说明：

- 构造用于 IR 文本解析与打印的默认 xDSL `Context`。
- 默认加载基础 dialect：`builtin`、`func`、`arith`、`scf`。
- 默认加载仓库常用 dialect：`nn`、`kernel`、`symbol`、`tuner`、`dma`、`arch`。

使用示例：

```python
from xdsl.parser import Parser
from kernel_gen.core.context import build_default_context

ctx = build_default_context()
module = Parser(ctx, "builtin.module { func.func @main() { func.return } }").parse_module()
```

注意事项：

- 本接口只负责 dialect 注册，不运行 pass、不做 lowering、不修复非法 IR。
- 需要解析 `scf.if` / `symbol.for` / `dma.*` / `arch.*` 等项目内常见 IR 的工具应复用本接口，不得在工具内维护第二套默认 dialect 注册列表。
- `kernel_gen.core.context` 是公开导入路径；旧 `kernel_gen.context` 不再作为当前公开入口。

返回与限制：

- 返回新的 `Context` 实例。
- 调用方可以在返回的 `Context` 上按需加载额外 dialect，但不得反向修改本接口的默认注册语义。

## 测试

- `pytest -q test/tools/test_mlir_gen_compare.py`
- `pytest -q test/tools/test_ircheck_runner.py`
