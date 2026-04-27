# symbol_buffer_hoist

## 功能简介

- 定义 `symbol-buffer-hoist` pass 的公开合同。
- 该 pass 只在 `symbol.for` 的单 block 循环体内识别 `dma.alloc`，并在能够机械证明 shape 与使用方式安全时，把该 alloc 外提到所属 `symbol.for` 之前。
- 当前公开语义只覆盖输入 staging buffer 与 output scratch buffer 两类 `dma.alloc` 外提；不做通用 LICM，也不承诺接入任何默认 pipeline。

## API 列表

- `class SymbolBufferHoistPass()`
- `SymbolBufferHoistPass.name: str`
- `SymbolBufferHoistPass.apply(ctx: Context, module: ModuleOp) -> None`
- `SymbolBufferHoistPass.run(module: ModuleOp) -> ModuleOp`
- `class DmaAllocInSymbolForHoistPattern()`
- `DmaAllocInSymbolForHoistPattern.match_and_rewrite(op: DmaAllocOp, rewriter: PatternRewriter) -> None`
- `get_symbol_buffer_hoist_patterns() -> list[RewritePattern]`

## 文档信息

- 创建者：`睡觉小分队`
- 最后一次更改：`睡觉小分队`
- `spec`：[`spec/pass/symbol_buffer_hoist.md`](../../spec/pass/symbol_buffer_hoist.md)
- `功能实现`：
  - [`kernel_gen/passes/symbol_buffer_hoist.py`](../../kernel_gen/passes/symbol_buffer_hoist.py)
  - [`kernel_gen/passes/__init__.py`](../../kernel_gen/passes/__init__.py)
  - [`kernel_gen/passes/registry.py`](../../kernel_gen/passes/registry.py)
- `test`：
  - [`test/pass/test_symbol_buffer_hoist.py`](../../test/pass/test_symbol_buffer_hoist.py)
  - [`test/pass/test_pass_registry.py`](../../test/pass/test_pass_registry.py)

## 依赖

- pass 共享错误与基础校验：
  - [`kernel_gen/passes/common.py`](../../kernel_gen/passes/common.py)
  - [`spec/pass/pass_manager.md`](../../spec/pass/pass_manager.md)
- pass 注册入口：
  - [`spec/pass/registry.md`](../../spec/pass/registry.md)
  - [`kernel_gen/passes/registry.py`](../../kernel_gen/passes/registry.py)
- 相关方言：
  - [`spec/dialect/dma.md`](../../spec/dialect/dma.md)
  - [`spec/dialect/symbol.md`](../../spec/dialect/symbol.md)
  - [`spec/dialect/nn.md`](../../spec/dialect/nn.md)

## 术语

- `input staging buffer`：loop 内临时 `dma.alloc`，后续作为 `dma.slice` 的目标 buffer 使用。
- `output scratch buffer`：loop 内临时 `dma.alloc`，后续作为 `dma.deslice(target, source, ...)` 的 `source` buffer 使用。
- `loop-carried`：来自当前 `symbol.for` 的 `iter_args`、loop iterator 或任何定义在当前 loop body 内的 SSA 值。
- `buffer escape`：`dma.alloc` 结果经 `symbol.yield`、`func.return` 或未知外部别名链暴露到当前 loop body 之外。

## 目标

- 固定公开 pass 名称为 `symbol-buffer-hoist`。
- 固定 canonical module path 为 `kernel_gen.passes.symbol_buffer_hoist`，并要求 `kernel_gen.passes.SymbolBufferHoistPass` 作为包根 re-export 继续可用。
- 固定 `build_registered_pass("symbol-buffer-hoist")` 可构造出当前 pass 的 `ModulePass` 实例。
- 当前专题只公开一个 pass、一个 pattern 类和一个 pattern getter；不新增专题专属错误类型。
- 下游 `pytest` 只验证本文件 `API 列表` 中的公开接口，不跨文件直连任何非公开 helper。

## 限制与边界

- 本 pass 只处理当前 `symbol.for` 单 block 循环体内的 `dma.alloc`；loop 外 `dma.alloc`、其他方言 op、其他 hoist 主题都不属于本轮公开语义。
- 当 `module` 中不存在 `symbol.for`，或某个 `symbol.for` 中不存在可安全外提的 `dma.alloc` 时，pass 必须保持 no-op。
- 允许外提的最小前提固定为：
  - `dma.alloc` 的 shape operand 全部定义在当前 loop body 之外。
  - shape 不依赖当前 `symbol.for` 的 loop iterator、`iter_args` 或任何 loop 内中间 SSA 值。
  - output scratch 不经 `symbol.yield`、`func.return` 或未知外部别名链逃逸。
- 当前公开正例固定为：
  - 输入 staging buffer：shape loop-invariant 时允许外提。
  - output scratch buffer：shape loop-invariant，且只作为 `dma.deslice(target, source, ...)` 的 `source` 使用时允许外提；`dma.deslice(target, source, ...)` 本身不构成 buffer escape。
- 当前公开反例固定为：
  - `dma.alloc` 的 shape 依赖 loop-carried 值时，alloc 必须保留在 loop 内。
  - 无法证明安全外提的 output scratch 必须保留在 loop 内，不得把行为做宽。
- 本 pass 不是通用 LICM，不负责：
  - 推断未写入本文件的副作用规则。
  - 改写 `func.func` 签名、生成 helper function 或新增 control-flow 结构。
  - 为 `kernel_gen.passes.lowering.symbol_buffer_hoist` 之类额外 compat path 提供公开承诺。
- 显式失败统一复用 [`PassContractError`](../../kernel_gen/passes/common.py)；当前专题不新增 `SymbolBufferHoistError` 之类独立错误类。
- 稳定失败边界固定为：
  - 非 `builtin.module` 输入：`PassContractError("module must be builtin.module")`
  - pass 执行后 verifier 失败或生成非法 IR：错误消息前缀固定为 `SymbolBufferHoistVerifierError:`
- 文件内若存在 shape 判定、escape 判定、插入点选择、walker 组装、verifier 包装等 helper，它们都不是公开 API；实现与测试都不得跨文件直接导入这些 helper。

## 额外补充

### 公开导入与调用方式

- 当前专题只承诺以下公开入口：

```python
from xdsl.context import Context

from kernel_gen.passes import SymbolBufferHoistPass
from kernel_gen.passes.registry import build_registered_pass
from kernel_gen.passes.symbol_buffer_hoist import get_symbol_buffer_hoist_patterns

pass_obj = SymbolBufferHoistPass()
pass_obj.apply(Context(), module)

same_pass = build_registered_pass("symbol-buffer-hoist")
same_pass.apply(Context(), module)

patterns = get_symbol_buffer_hoist_patterns()
```

- `test/pass/test_symbol_buffer_hoist.py` 只能通过 `SymbolBufferHoistPass`、`DmaAllocInSymbolForHoistPattern`、`get_symbol_buffer_hoist_patterns()` 和 `build_registered_pass("symbol-buffer-hoist")` 观察行为。
- `test/pass/test_pass_registry.py` 只能通过 `kernel_gen.passes.symbol_buffer_hoist`、`kernel_gen.passes.SymbolBufferHoistPass` 与 pass registry 观察公开导入面。

### 最小改写合同

- 输入 staging buffer 正例：

```text
symbol.for ... {
  %buf = "dma.alloc"(%tm, %k) : (...) -> !nn.memory<...>
  "dma.slice"(%buf, %src, ...) : (...) -> ()
}
```

必须改写为：

```text
%buf = "dma.alloc"(%tm, %k) : (...) -> !nn.memory<...>
symbol.for ... {
  "dma.slice"(%buf, %src, ...) : (...) -> ()
}
```

- output scratch 正例：

```text
symbol.for ... {
  %buf = "dma.alloc"(%tm, %tn) : (...) -> !nn.memory<...>
  %out2 = "dma.deslice"(%out, %buf, ...) : (...) -> !nn.memory<...>
}
```

必须允许改写为：

```text
%buf = "dma.alloc"(%tm, %tn) : (...) -> !nn.memory<...>
symbol.for ... {
  %out2 = "dma.deslice"(%out, %buf, ...) : (...) -> !nn.memory<...>
}
```

- shape 依赖 loop-carried 反例：

```text
%res = symbol.for ... iter_args(%acc = ...) -> ... {
  %buf = "dma.alloc"(%acc, %k) : (...) -> !nn.memory<...>
  ...
}
```

必须保持 `%buf` 继续位于 loop 内，不得外提。

## 测试

- 测试文件：[`test/pass/test_symbol_buffer_hoist.py`](../../test/pass/test_symbol_buffer_hoist.py)
- 执行命令：`PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/pass/test_symbol_buffer_hoist.py`
- 测试目标：锁定 `SymbolBufferHoistPass`、`DmaAllocInSymbolForHoistPattern`、`get_symbol_buffer_hoist_patterns()` 与 `build_registered_pass("symbol-buffer-hoist")` 的公开行为。
- 功能与用例清单：
  - 输入 staging buffer 外提正例
  - output scratch 外提正例
  - shape 依赖 loop-carried 反例
  - `PassContractError("module must be builtin.module")`
  - `SymbolBufferHoistVerifierError:` 失败前缀

- 测试文件：[`test/pass/test_pass_registry.py`](../../test/pass/test_pass_registry.py)
- 执行命令：`PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/pass/test_pass_registry.py -k "symbol_buffer_hoist or symbol-buffer-hoist"`
- 测试目标：锁定 `symbol-buffer-hoist` 的 registry 名称、canonical import path 与包根 re-export。
- 功能与用例清单：
  - `build_registered_pass("symbol-buffer-hoist")` 返回 `ModulePass`
  - `kernel_gen.passes.symbol_buffer_hoist.SymbolBufferHoistPass` 导入成功
  - `kernel_gen.passes.SymbolBufferHoistPass` 包根导入成功
