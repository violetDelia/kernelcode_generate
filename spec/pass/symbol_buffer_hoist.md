# symbol_buffer_hoist

## 功能简介

- 定义 `symbol-buffer-hoist` pass 的公开合同。
- 该 pass 只在 `symbol.for` 的单 block 循环体内识别 `dma.alloc`、`dma.view`、`dma.reshape` 与 `dma.subview`，并在能够机械证明 operand 支配关系、使用方式和生命周期安全时，把单个 op 外提到所属 `symbol.for` 前一层。
- 当前公开语义覆盖输入 staging buffer 与 output scratch buffer 两类 `dma.alloc/free` 成对外提、`get_effects(op)` / `MemoryEffect` 可判定的 `dma.*` / `kernel.*` 读写生命周期证明、`dma.broadcast` target write reset、`symbol.get_dim` / `symbol.get_stride` Pure metadata query，以及 loop-invariant alias op 的 fixed-point 单 op 外提；没有唯一匹配 `dma.free` 时 `dma.alloc` 必须保持 loop 内 no-op。
- 本 pass 不做通用 LICM；在 `npu-demo-lowering` 中由 pipeline builder 固定接入，其它默认 pipeline 不隐式接入。

## API 列表

- `class SymbolBufferHoistPass(fold: bool = True)`
- `SymbolBufferHoistPass.name: str`
- `SymbolBufferHoistPass.apply(ctx: Context, module: ModuleOp) -> None`
- `class DmaAllocInSymbolForHoistPattern()`
- `DmaAllocInSymbolForHoistPattern.match_and_rewrite(op: DmaAllocOp, rewriter: PatternRewriter) -> None`
- `get_symbol_buffer_hoist_patterns() -> list[RewritePattern]`

## 文档信息

- 创建者：`未记录`
- 最后一次更改：`小李飞刀`
- `spec`：[`spec/pass/symbol_buffer_hoist.md`](../../spec/pass/symbol_buffer_hoist.md)
- `功能实现`：
  - [`kernel_gen/passes/symbol_buffer_hoist.py`](../../kernel_gen/passes/symbol_buffer_hoist.py)
  - [`kernel_gen/passes/__init__.py`](../../kernel_gen/passes/__init__.py)
  - [`kernel_gen/passes/registry.py`](../../kernel_gen/passes/registry.py)
- `test`：
  - [`test/passes/test_symbol_buffer_hoist.py`](../../test/passes/test_symbol_buffer_hoist.py)
  - [`test/passes/test_registry.py`](../../test/passes/test_registry.py)

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
- `alias op`：`dma.view`、`dma.reshape` 或 `dma.subview` 这类只生成 memory view/result 的 op；本 pass 只承接这三种 alias op 的单 op fixed-point 外提。
- `loop-carried`：来自当前 `symbol.for` 的 `iter_args`、loop iterator 或任何定义在当前 loop body 内的 SSA 值。
- `buffer escape`：`dma.alloc` 结果经 `symbol.yield`、`func.return` 或未知外部别名链暴露到当前 loop body 之外。
- `lifecycle free`：同一 owner `symbol.for` 直接 body 内唯一释放当前 alloc result 的 `dma.free`；只有位于所有支持的数据 use 之后时才允许随 alloc 成对外提。
- `lifecycle reset/write`：由公开 xDSL `MemoryEffect` 标注为 `WRITE` 且不同时读取当前 alloc result 的 use；当后续 `kernel.*` 或 `dma.*` 对同一 buffer 有 `READ` effect 时，首次 read 前必须已在同一个 parent block 中出现 reset/write。若同一 op 对同一 value 同时暴露 `READ+WRITE`，该 op 不能自证 reset/write，只有同一 block 内此前已有独立 `WRITE` 时才允许继续。
- `metadata query`：`symbol.get_dim` 与 `symbol.get_stride` 是 Pure 元信息查询；它们不阻断安全外提，也不进入生命周期 data use、reset/write 或 free 顺序证明。

## 目标

- 固定公开 pass 名称为 `symbol-buffer-hoist`。
- 固定 canonical module path 为 `kernel_gen.passes.symbol_buffer_hoist`，并要求 `kernel_gen.passes.SymbolBufferHoistPass` 作为包根 re-export 继续可用。
- 固定 `build_registered_pass("symbol-buffer-hoist")` 可构造出当前 pass 的 `ModulePass` 实例。
- 当前专题只公开一个 pass、一个 pattern 类和一个 pattern getter；不新增专题专属错误类型。
- 下游 `pytest` 只验证本文件 `API 列表` 中的公开接口，不跨文件直连任何非公开 helper。

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

- `test/passes/test_symbol_buffer_hoist.py` 只能通过 `SymbolBufferHoistPass`、`DmaAllocInSymbolForHoistPattern`、`get_symbol_buffer_hoist_patterns()` 和 `build_registered_pass("symbol-buffer-hoist")` 观察行为。
- `test/passes/test_registry.py` 只能通过 `kernel_gen.passes.symbol_buffer_hoist`、`kernel_gen.passes.SymbolBufferHoistPass` 与 pass registry 观察公开导入面。

### 最小改写合同

- 输入 staging buffer 正例：

```text
symbol.for value {
  %buf = "dma.alloc"(%tm, %k) : (value) -> !nn.memory<value>
  "dma.slice"(%buf, %src, value) : (value) -> ()
  "dma.free"(%buf) : (value) -> ()
}
```

必须改写为：

```text
%buf = "dma.alloc"(%tm, %k) : (value) -> !nn.memory<value>
symbol.for value {
  "dma.slice"(%buf, %src, value) : (value) -> ()
}
"dma.free"(%buf) : (value) -> ()
```

- output scratch 正例：

```text
symbol.for value {
  %buf = "dma.alloc"(%tm, %tn) : (value) -> !nn.memory<value>
  %out2 = "dma.deslice"(%out, %buf, value) : (value) -> !nn.memory<value>
  "dma.free"(%buf) : (value) -> ()
}
```

必须允许改写为：

```text
%buf = "dma.alloc"(%tm, %tn) : (value) -> !nn.memory<value>
symbol.for value {
  %out2 = "dma.deslice"(%out, %buf, value) : (value) -> !nn.memory<value>
}
"dma.free"(%buf) : (value) -> ()
```

- shape 依赖 loop-carried 反例：

```text
%res = symbol.for value iter_args(%acc = value) -> value {
  %buf = "dma.alloc"(%acc, %k) : (value) -> !nn.memory<value>
  value
}
```

必须保持 `%buf` 继续位于 loop 内，不得外提。

### 模块级补充

- 本小节只记录模块级非接口补充；接口级参数限制、错误语义、兼容要求与非目标必须维护在对应 API 的 `注意事项`。
- 本 pass 以当前 `symbol.for` 的直接 body 为生命周期证明起点，`dma.alloc/free` 仍只在直接 body 里判定外提；`dma.view`、`dma.reshape` 与 `dma.subview` 允许在该 owner 的 descendant region 内做 fixed-point 逐层外提到最近安全位置。loop 外 op、其他方言 op、其他 hoist 主题都不属于本轮公开语义。
- 当 `module` 中不存在 `symbol.for`，或某个 `symbol.for` 中不存在可安全外提的目标 op 时，pass 必须保持 no-op。
- 允许外提的最小前提固定为：
  - `dma.alloc` 的 shape operand 全部定义在当前 loop body 之外。
  - shape 不依赖当前 `symbol.for` 的 loop iterator、`iter_args` 或任何 loop 内中间 SSA 值。
  - 数据 use 可以是 legacy staging/scratch use（`dma.slice` target、`dma.deslice` source），也可以是公开 `MemoryEffect` 可判定且只包含 `READ/WRITE` 的 `dma.fill/copy/load/store/slice/deslice/broadcast` 或 `kernel.*` memory use。
  - `dma.alloc/free` 生命周期证明允许 `scf.if` 这类非 `symbol.for` descendant region 内的 effect-first data use；nested `symbol.for` body 内的 data use 只允许把 alloc/free 外提到该 nested loop 的最近外层，不得继续把同一 alloc/free 穿透外层 `symbol.for`。
  - 公开 `MemoryEffect` 可判定的 use 中，若当前 buffer 的首次 effect 包含 `READ` 且之前没有 reset/write，则必须保持 no-op；unknown effect、`ALLOC/FREE` data use 或未列入本文件的 effect 组合不得外提。
  - `symbol.get_dim` / `symbol.get_stride` 对当前 buffer 或 alias result 的读取只作为 Pure metadata query 处理；它们允许存在但不会加入数据 use 列表，也不能单独让 alloc/free 外提。
  - `dma.alloc` result 可以作为同一 owner `symbol.for` 直接 body 内 `dma.view`、`dma.reshape` 或 `dma.subview` 的 source；alias result 的最终 direct use 必须落在同一 owner body 或其 descendant region 内，并且属于 `dma.slice` target、`dma.deslice` source、`dma.fill` target、`dma.copy` target/source、公开 `MemoryEffect` 可判定的 `kernel.*` memory operand、`symbol.get_dim` / `symbol.get_stride` metadata query 或可继续处理的 alias op。
  - 若存在 `dma.free`，必须是同一 owner `symbol.for` 直接 body 内唯一释放当前 alloc result 的 op，并且顺序位于所有数据 use 之后。
  - output scratch 不经 `symbol.yield`、`func.return` 或未知外部别名链逃逸。
- 当前公开正例固定为：
  - 输入 staging buffer：shape loop-invariant 且后接唯一合法 `dma.free` 时允许外提。
  - output scratch buffer：shape loop-invariant，且只作为 `dma.deslice(target, source, ...)` 的 `source` 使用并后接唯一合法 `dma.free` 时允许外提；`dma.deslice(target, source, ...)` 本身不构成 buffer escape。
  - 输入 staging 或 output scratch 没有唯一合法 `dma.free` 时必须保持 loop 内。
  - `dma.view`：source、offset、shape、stride 全部支配当前 owner `symbol.for`，且 result use 只在同一 owner body 或 descendant region 内流向 `dma.slice` target、`dma.deslice` source、`dma.fill` target、`dma.copy` target/source、公开 `MemoryEffect` 可判定的 `kernel.*` memory operand、`symbol.get_dim` / `symbol.get_stride` metadata query 或可继续处理的 alias op 时，单 op 外提一层；fixed-point 驱动可在 nested loop 中逐层外提到最近安全位置。
  - `dma.reshape`：source 与 shape 全部支配当前 owner `symbol.for`，且 result use 满足同一白名单时，单 op 外提一层；fixed-point 驱动可在 nested loop 中逐层外提到最近安全位置。
  - `dma.subview`：source、offset、size、stride 全部支配当前 owner `symbol.for`，且 result use 满足同一白名单时，单 op 外提一层；fixed-point 驱动可在 nested loop 中逐层外提到最近安全位置。
  - `dma.fill` 或 `dma.broadcast` target write reset 后的 `kernel.*` read/write use 可作为 alloc/free 生命周期证明的一部分；例如 `dma.broadcast(buf, scalar)` 后 `kernel.*(..., lhs=buf, ...)` 读取 `buf` 时，alloc/free 可以成对外提。
  - nested `scf.if` 的 conditional write 只有在同一个 region block 内且 textual order 上早于后续 read 时可作为 reset/write proof；分支内 write 不证明 merge 点 read，跨分支、sibling region、owner loop 外 region 或不可定位 parent chain 均必须 no-op。
- 当前公开反例固定为：
  - `dma.alloc` 的 shape 依赖 loop-carried 值时，alloc 必须保留在 loop 内。
  - 无法证明安全外提的 output scratch 必须保留在 loop 内，不得把行为做宽。
  - 没有唯一合法 `dma.free` 的输入 staging / output scratch 必须保持 loop 内。
  - `dma.free` 位于数据 use 前、存在多个 `dma.free`、`dma.free` 位于 nested region 或非 owner body、alloc result 有未知直接 use/alias escape 时，alloc/free 都必须保留原位。
  - alias op 任一 source、offset、shape、size 或 stride operand 来自当前 loop iterator、loop-carried block argument 或当前 loop body 内 op result 时，该 alias op 必须保留在 loop 内。
  - alias result 经 `symbol.yield`、`func.return`、sibling region、owner loop 外 region、未知 direct use、没有公开 `READ/WRITE` `MemoryEffect` 的 `kernel.*` memory operand，或无法机械判定顺序的 alias 链逃逸时，该 alias op 必须保留原位。
  - `kernel.*` 或 `dma.*` 对 alloc result 的首次可判定 effect 包含 `READ` 且之前没有 reset/write 时，alloc/free 必须保留原位，不得把未初始化 read 外提成跨迭代共享状态。
  - `dma.broadcast(buf, buf)` 这类同一 value 同时作为 target/source 的 `READ+WRITE` use 不得自证 reset/write；若没有此前同 block 独立 `WRITE`，alloc/free 必须保持原位。
  - 只有 `symbol.get_dim` / `symbol.get_stride` metadata query 与 `dma.free` 时，因为没有真实 data use，alloc/free 必须保持原位。
- 本 pass 不是通用 LICM，不负责：
  - 推断未写入本文件的副作用规则。
  - 改写 `func.func` 签名、生成 helper function 或新增 control-flow 结构。
  - 为 `kernel_gen.passes.lowering.symbol_buffer_hoist` 之类额外 compat path 提供公开承诺。
- 显式失败统一复用 [`KernelCodeError`](../../kernel_gen/passes/common.py)；当前专题不新增 `SymbolBufferHoistError` 之类独立错误类。
- 稳定失败边界固定为：
  - 非 `builtin.module` 输入：`KernelCodeError("module must be builtin.module")`
  - pass 执行后 verifier 失败或生成非法 IR：错误消息前缀固定为 `SymbolBufferHoistVerifierError:`
- 文件内若存在 shape 判定、escape 判定、插入点选择、walker 组装、verifier 包装等 helper，它们都不是公开 API；实现与测试都不得跨文件直接导入这些 helper。
## API详细说明

### `class SymbolBufferHoistPass(fold: bool = True)`

- api：`class SymbolBufferHoistPass(fold: bool = True)`
- 参数：
  - `fold`：是否允许 pass 内 pattern walker 执行 folding；类型 `bool`；默认值 `True`。
- 返回值：`SymbolBufferHoistPass` 实例。
- 使用示例：

  ```python
  symbol_buffer_hoist_pass = SymbolBufferHoistPass()
  ```
- 功能说明：定义 `SymbolBufferHoistPass` pass 对象。
- 注意事项：构造参数必须符合本条目参数说明；实例内部缓存、状态字典和派生字段不作为外部可变入口。

### `SymbolBufferHoistPass.name: str`

- api：`SymbolBufferHoistPass.name: str`
- 参数：无。
- 返回值：当前 package 根导出的公开对象集合；只包含 API 列表中声明的名称。
- 使用示例：

  ```python
  from kernel_gen.passes.symbol_buffer_hoist import SymbolBufferHoistPass

  assert SymbolBufferHoistPass.name == "symbol-buffer-hoist"
  ```
- 功能说明：公开 `SymbolBufferHoistPass.name: str` 包根导入路径。
- 注意事项：非法输入必须按本条目参数说明和公开错误语义处理；调用方不得依赖实现内部状态。

### `SymbolBufferHoistPass.apply(ctx: Context, module: ModuleOp) -> None`

- api：`SymbolBufferHoistPass.apply(ctx: Context, module: ModuleOp) -> None`
- 参数：
  - `ctx`：公开上下文对象，提供代码生成、emit、pass 或工具执行所需的配置与状态；类型 `Context`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
  - `module`：模块级 IR 对象，作为 pass、校验或代码生成的处理主体；类型 `ModuleOp`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
- 返回值：无返回值；调用成功表示操作完成。
- 使用示例：

  ```python
  symbol_buffer_hoist_pass = symbol_buffer_hoist_pass
  symbol_buffer_hoist_pass.apply(ctx=ctx, module=module)
  ```
- 功能说明：对模块执行 `SymbolBufferHoistPass` pass。
- 注意事项：非法输入必须按本条目参数说明和公开错误语义处理；调用方不得依赖实现内部状态。

### `class DmaAllocInSymbolForHoistPattern()`

- api：`class DmaAllocInSymbolForHoistPattern()`
- 参数：无。
- 返回值：`DmaAllocInSymbolForHoistPattern` 实例。
- 使用示例：

  ```python
  dma_alloc_in_symbol_for_hoist_pattern = DmaAllocInSymbolForHoistPattern()
  ```
- 功能说明：定义 `DmaAllocInSymbolForHoistPattern` rewrite pattern 对象。
- 注意事项：构造参数必须符合本条目参数说明；实例内部缓存、状态字典和派生字段不作为外部可变入口。

### `DmaAllocInSymbolForHoistPattern.match_and_rewrite(op: DmaAllocOp, rewriter: PatternRewriter) -> None`

- api：`DmaAllocInSymbolForHoistPattern.match_and_rewrite(op: DmaAllocOp, rewriter: PatternRewriter) -> None`
- 参数：
  - `op`：IR operation，作为 emit、rewrite、lowering 或校验的当前处理对象；类型 `DmaAllocOp`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
  - `rewriter`：公开 rewrite 对象，用于替换、插入或删除 IR operation；类型 `PatternRewriter`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
- 返回值：无返回值；调用成功表示操作完成。
- 使用示例：

  ```python
  dma_alloc_in_symbol_for_hoist_pattern = dma_alloc_in_symbol_for_hoist_pattern
  dma_alloc_in_symbol_for_hoist_pattern.match_and_rewrite(op=op, rewriter=rewriter)
  ```
- 功能说明：使用 `DmaAllocInSymbolForHoistPattern` 匹配目标 operation 并执行 rewrite。
- 注意事项：非法输入必须按本条目参数说明和公开错误语义处理；调用方不得依赖实现内部状态。

### `get_symbol_buffer_hoist_patterns() -> list[RewritePattern]`

- api：`get_symbol_buffer_hoist_patterns() -> list[RewritePattern]`
- 参数：无。
- 返回值：`list[RewritePattern]`。
- 使用示例：

  ```python
  result = get_symbol_buffer_hoist_patterns()
  ```
- 功能说明：读取 `symbol-buffer-hoist` 的 rewrite pattern 列表。
- 注意事项：该接口可返回用于 `dma.view` / `dma.reshape` / `dma.subview` 的私有 pattern 实例；调用方不得依赖这些私有类名或把它们作为公开 API。

## 测试

- 测试文件：
  - `test/passes/test_registry.py`
  - `test/passes/test_symbol_buffer_hoist.py`
- 执行命令：
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/passes/test_symbol_buffer_hoist.py`
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/passes/test_registry.py -k "symbol_buffer_hoist or symbol-buffer-hoist"`

### 测试目标

- 锁定 `SymbolBufferHoistPass`、`DmaAllocInSymbolForHoistPattern`、`get_symbol_buffer_hoist_patterns()` 与 `build_registered_pass("symbol-buffer-hoist")` 的公开行为。
- 锁定 `symbol-buffer-hoist` 的 registry 名称、canonical import path 与包根 re-export。

### 功能与用例清单

| 用例 ID | 功能 | 场景 | 前置条件 | 操作 | 预期结果 | 建议测试 |
| --- | --- | --- | --- | --- | --- | --- |
| TC-PASS-SYMBOL-BUFFER-HOIST-001 | no-op 边界 | 输入 staging buffer 无 matching free | 准备 loop 内 shape invariant 的输入 staging `dma.alloc`，但不提供 `dma.free`。 | 运行 `pytest -q test/passes/test_symbol_buffer_hoist.py::test_symbol_buffer_hoist_pass_keeps_input_staging_alloc_without_free`。 | alloc 保持在 loop 内，不外提。 | test/passes/test_symbol_buffer_hoist.py::test_symbol_buffer_hoist_pass_keeps_input_staging_alloc_without_free |
| TC-PASS-SYMBOL-BUFFER-HOIST-002 | no-op 边界 | output scratch 无 matching free | 准备 loop 内 output scratch `dma.alloc` 与 `dma.deslice`，但不提供 `dma.free`。 | 运行 `pytest -q test/passes/test_symbol_buffer_hoist.py::test_symbol_buffer_hoist_pass_keeps_output_scratch_alloc_without_free`。 | alloc 保持在 loop 内，不外提。 | test/passes/test_symbol_buffer_hoist.py::test_symbol_buffer_hoist_pass_keeps_output_scratch_alloc_without_free |
| TC-PASS-SYMBOL-BUFFER-HOIST-003 | 执行结果 | shape 依赖 loop-carried 反例 | 准备公开输入数据、执行入口或 CLI 状态文件。 | 运行 `pytest -q test/passes/test_symbol_buffer_hoist.py::test_symbol_buffer_hoist_keeps_loop_carried_shape_inside_loop`。 | 命令返回码、输出、执行结果或状态变更体现“shape 依赖 loop-carried 反例”场景。 | test/passes/test_symbol_buffer_hoist.py::test_symbol_buffer_hoist_keeps_loop_carried_shape_inside_loop |
| TC-PASS-SYMBOL-BUFFER-HOIST-004 | 边界/异常 | `KernelCodeError("module must be builtin.module")` | 准备触发该错误路径的公开输入或非法参数组合。 | 运行 `pytest -q test/passes/test_symbol_buffer_hoist.py::test_symbol_buffer_hoist_rejects_non_module_input`。 | “`KernelCodeError("module must be builtin.module")`”场景按公开错误语义失败或被拒绝。 | test/passes/test_symbol_buffer_hoist.py::test_symbol_buffer_hoist_rejects_non_module_input |
| TC-PASS-SYMBOL-BUFFER-HOIST-005 | 边界/异常 | `SymbolBufferHoistVerifierError:` 失败前缀 | 准备触发该错误路径的公开输入或非法参数组合。 | 运行 `pytest -q test/passes/test_symbol_buffer_hoist.py::test_symbol_buffer_hoist_wraps_verify_failure_prefix`。 | “`SymbolBufferHoistVerifierError:` 失败前缀”场景按公开错误语义失败或被拒绝。 | test/passes/test_symbol_buffer_hoist.py::test_symbol_buffer_hoist_wraps_verify_failure_prefix |
| TC-PASS-SYMBOL-BUFFER-HOIST-006 | pass 改写 | 输入 staging alloc/free 成对外提 | 准备同一 owner `symbol.for` 直接 body 内 `dma.slice` 后唯一 `dma.free`。 | 运行 `pytest -q test/passes/test_symbol_buffer_hoist.py::test_symbol_buffer_hoist_hoists_input_staging_alloc_and_matching_free`。 | alloc 位于 loop 前，free 位于 loop 后，slice 留在 loop 内。 | test/passes/test_symbol_buffer_hoist.py::test_symbol_buffer_hoist_hoists_input_staging_alloc_and_matching_free |
| TC-PASS-SYMBOL-BUFFER-HOIST-007 | pass 改写 | output scratch alloc/free 成对外提 | 准备同一 owner `symbol.for` 直接 body 内 `dma.deslice` 后唯一 `dma.free`。 | 运行 `pytest -q test/passes/test_symbol_buffer_hoist.py::test_symbol_buffer_hoist_hoists_output_scratch_alloc_and_matching_free`。 | alloc 位于 loop 前，free 位于 loop 后，deslice 留在 loop 内。 | test/passes/test_symbol_buffer_hoist.py::test_symbol_buffer_hoist_hoists_output_scratch_alloc_and_matching_free |
| TC-PASS-SYMBOL-BUFFER-HOIST-008 | no-op 边界 | free 早于数据 use、多 free、nested free、free 位于 owner loop 内 `scf.if` sibling region block、同值 `dma.broadcast` READ+WRITE | 准备对应公开 IR 输入。 | 运行 `test_symbol_buffer_hoist_keeps_alloc_when_free_precedes_data_use`、`test_symbol_buffer_hoist_keeps_alloc_when_multiple_free`、`test_symbol_buffer_hoist_keeps_alloc_when_free_is_nested`、`test_symbol_buffer_hoist_keeps_alloc_when_free_not_in_owner_loop_body`、`test_symbol_buffer_hoist_keeps_alloc_for_same_value_broadcast_read_write`。 | alloc/free 与 alias op 保持原位，不做不安全外提。 | `pytest -q test/passes/test_symbol_buffer_hoist.py -k "free_not_in_owner_loop_body or free_is_nested or multiple_free or free_precedes or same_value_broadcast"` |
| TC-PASS-SYMBOL-BUFFER-HOIST-009 | pass 改写 | loop-invariant alias op 单层外提 | 准备 alloc/free 成对安全，且 `dma.view` / `dma.reshape` / `dma.subview` 的 source 与布局 operand 全部支配当前 loop。 | 运行 `test_symbol_buffer_hoist_hoists_loop_invariant_dma_view_one_layer`、`test_symbol_buffer_hoist_hoists_loop_invariant_dma_reshape_one_layer`、`test_symbol_buffer_hoist_hoists_loop_invariant_dma_subview_one_layer`。 | alloc/free 成对外提；alias op 位于 loop 前；data use 留在 loop 内捕获 alias result。 | `pytest -q test/passes/test_symbol_buffer_hoist.py -k "loop_invariant_dma_view or loop_invariant_dma_reshape or loop_invariant_dma_subview"` |
| TC-PASS-SYMBOL-BUFFER-HOIST-010 | no-op 边界 | alias operand 依赖当前 loop | 准备 `dma.view` offset、`dma.reshape` shape 或 `dma.subview` size 依赖当前 iterator / loop-carried 值。 | 运行 `test_symbol_buffer_hoist_keeps_dma_view_when_offset_depends_on_loop_iterator`、`test_symbol_buffer_hoist_keeps_dma_reshape_when_shape_is_loop_carried`、`test_symbol_buffer_hoist_keeps_dma_subview_when_size_is_loop_carried`。 | alloc/free 可按自身规则成对外提；alias op 保持在 loop 内。 | `pytest -q test/passes/test_symbol_buffer_hoist.py -k "keeps_dma_view or keeps_dma_reshape or keeps_dma_subview"` |
| TC-PASS-SYMBOL-BUFFER-HOIST-011 | 公开入口 | `build_registered_pass("symbol-buffer-hoist")` 返回 `ModulePass` | 按 spec 声明的导入路径、CLI 参数、注册名或命名空间访问公开入口。 | 运行 `pytest -q test/passes/test_symbol_buffer_hoist.py::test_build_registered_symbol_buffer_hoist_pass`。 | 公开入口在“`build_registered_pass("symbol-buffer-hoist")` 返回 `ModulePass`”场景下可导入、构造、注册或按名称发现。 | test/passes/test_symbol_buffer_hoist.py::test_build_registered_symbol_buffer_hoist_pass |
| TC-PASS-SYMBOL-BUFFER-HOIST-012 | 公开入口 | `kernel_gen.passes.symbol_buffer_hoist.SymbolBufferHoistPass` 与包根 re-export 导入成功 | 准备包含目标 op、pass 名称或 pipeline 的公开 IR 输入。 | 运行 `pytest -q test/passes/test_symbol_buffer_hoist.py::test_symbol_buffer_hoist_public_patterns_are_reachable`。 | 公开入口可导入；公开 getter 返回 `RewritePattern` 实例集合且不要求测试直连私有 pattern 类。 | test/passes/test_symbol_buffer_hoist.py::test_symbol_buffer_hoist_public_patterns_are_reachable |
| TC-PASS-SYMBOL-BUFFER-HOIST-013 | pass 改写 | `kernel.*` read 在 reset/write 之后可纳入 alloc/free 生命周期证明 | 准备 loop 内 `dma.alloc`，先 `dma.fill` 写入该 buffer，再由 `kernel.*` 读取，最后唯一 `dma.free`。 | 运行 `pytest -q test/passes/test_symbol_buffer_hoist.py::test_symbol_buffer_hoist_hoists_alloc_when_kernel_read_is_reset_by_fill`。 | alloc 位于 loop 前，free 位于 loop 后，`dma.fill` 与 `kernel.*` use 留在 loop 内并捕获外提后的 buffer。 | test/passes/test_symbol_buffer_hoist.py::test_symbol_buffer_hoist_hoists_alloc_when_kernel_read_is_reset_by_fill |
| TC-PASS-SYMBOL-BUFFER-HOIST-014 | no-op 边界 | `kernel.*` read 早于 reset/write | 准备 loop 内 `dma.alloc` 直接被 `kernel.*` 作为输入读取，之后唯一 `dma.free`。 | 运行 `pytest -q test/passes/test_symbol_buffer_hoist.py::test_symbol_buffer_hoist_keeps_alloc_when_kernel_reads_before_reset`。 | alloc/free 保持 loop 内，避免把未初始化 read 变成跨迭代共享状态。 | test/passes/test_symbol_buffer_hoist.py::test_symbol_buffer_hoist_keeps_alloc_when_kernel_reads_before_reset |
| TC-PASS-SYMBOL-BUFFER-HOIST-015 | pass 改写 | nested loop 中 alias result 流向公开 `MemoryEffect` 可判定的 `kernel.*` operand | 准备 source/layout operand 全部支配当前 loop 的 `dma.reshape` / `dma.view` / `dma.subview`，其 result 在 nested loop 中被 `kernel.*` 捕获。 | 运行 `pytest -q test/passes/test_symbol_buffer_hoist.py::test_symbol_buffer_hoist_hoists_nested_alias_result_used_by_kernel_op`。 | alias op 通过 fixed-point 外提到最近安全位置；nested `kernel.*` use 保持原位并捕获外提 alias result。 | test/passes/test_symbol_buffer_hoist.py::test_symbol_buffer_hoist_hoists_nested_alias_result_used_by_kernel_op |
| TC-PASS-SYMBOL-BUFFER-HOIST-016 | pass 改写 | `dma.broadcast` target WRITE 作为 reset/write proof | 准备 loop 内 `dma.alloc` 先被 `dma.broadcast(target=alloc, source=scalar)` 处理，再由 `kernel.*` 读取，最后唯一 `dma.free`。 | 运行 `pytest -q test/passes/test_symbol_buffer_hoist.py::test_symbol_buffer_hoist_hoists_alloc_when_broadcast_resets_kernel_read`。 | alloc 位于 loop 前，free 位于 loop 后，broadcast 留在 loop 内并可证明后续 kernel read。 | test/passes/test_symbol_buffer_hoist.py::test_symbol_buffer_hoist_hoists_alloc_when_broadcast_resets_kernel_read |
| TC-PASS-SYMBOL-BUFFER-HOIST-017 | no-op 边界 | `symbol.get_dim/get_stride` 仅作为 Pure metadata query | 准备 loop 内 alloc result 仅出现 `symbol.get_dim` / `symbol.get_stride` 或它们与合法 data use 并存。 | 运行 `pytest -q test/passes/test_symbol_buffer_hoist.py::test_symbol_buffer_hoist_keeps_alloc_when_only_metadata_queries_exist`、`test_symbol_buffer_hoist_hoists_alloc_with_metadata_queries_and_slice_use`。 | metadata query 不参与 lifecycle data use；仅 metadata query 时 alloc/free 保持原位，metadata + 合法 data use 时仍可外提。 | `pytest -q test/passes/test_symbol_buffer_hoist.py -k "metadata_queries"` |
| TC-PASS-SYMBOL-BUFFER-HOIST-018 | pass 改写 | 同一 `scf.if` 分支内 write-before-read | 准备 loop 内 alloc result 在同一个 `scf.if` region block 中先被 write 再被 read，最后唯一 `dma.free`。 | 运行 `pytest -q test/passes/test_symbol_buffer_hoist.py::test_symbol_buffer_hoist_hoists_alloc_when_conditional_write_and_read_are_same_branch`。 | 分支内 write/read 证明生效，alloc 位于 loop 前，free 位于 loop 后。 | test/passes/test_symbol_buffer_hoist.py::test_symbol_buffer_hoist_hoists_alloc_when_conditional_write_and_read_are_same_branch |
| TC-PASS-SYMBOL-BUFFER-HOIST-019 | no-op 边界 | `scf.if` 分支写不能证明 merge 点 read | 准备 loop 内 alloc result 在分支内 write、在 merge 点 read，最后唯一 `dma.free`。 | 运行 `pytest -q test/passes/test_symbol_buffer_hoist.py::test_symbol_buffer_hoist_keeps_alloc_when_conditional_write_feeds_merge_read`。 | 分支写不证明 merge 点 read，alloc/free 保持原位。 | test/passes/test_symbol_buffer_hoist.py::test_symbol_buffer_hoist_keeps_alloc_when_conditional_write_feeds_merge_read |
