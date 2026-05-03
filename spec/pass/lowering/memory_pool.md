# memory_pool.md

## 功能简介

- 定义 `MemoryPoolPass` 的公开合同：基于 `dma.alloc/dma.free` 生成内存生命周期摘要结构。
- 提供 `MemoryPoolSummary/MemoryPoolInterval` 稳定接口，用于后续统计与验证。
- 支持直线路径的 pool 改写：将符合约束的 `dma.alloc/dma.free` 改写为 `i8` byte pool + `dma.view`。

## API 列表

- `class MemoryPoolPass(rewrite: bool = False)`
  - `name: str`
  - `__init__(rewrite: bool = False) -> None`
  - `apply(ctx: Context, op: ModuleOp) -> None`
  - `apply(ctx: Context, module: ModuleOp) -> None`
  - `get_summary(func_name: str) -> MemoryPoolSummary`
  - `all_summaries() -> dict[str, MemoryPoolSummary]`
- `class MemoryPoolSummary(func_name: str, intervals: tuple[MemoryPoolInterval, ...], peak_bytes_by_bucket: dict[tuple[str], sympy.Basic], pool_count: int)`
  - `to_text() -> str`
- `class MemoryPoolInterval(name: str, bucket_key: tuple[str], size_bytes_expr: sympy.Basic, begin_index: int, end_index: int, offset_bytes_expr: sympy.Basic)`

## 文档信息

- 创建者：`未记录`
- 最后一次更改：`小李飞刀`
- `spec`：[`spec/pass/lowering/memory_pool.md`](../../../spec/pass/lowering/memory_pool.md)
- `功能实现`：[`kernel_gen/passes/memory_pool.py`](../../../kernel_gen/passes/memory_pool.py)
- `test`：[`test/passes/test_memory_pool.py`](../../../test/passes/test_memory_pool.py)

## 依赖

- `dma` dialect：[`kernel_gen/dialect/dma.py`](../../../kernel_gen/dialect/dma.py)
- `nn` memory type：[`kernel_gen/dialect/nn.py`](../../../kernel_gen/dialect/nn.py)
- pass registry：[`spec/pass/registry.md`](../../../spec/pass/registry.md)
- `func.func`：`xdsl.dialects.func`
- `sympy` 表达式库

## 术语

- `interval`：单个 `dma.alloc` 对应的生命周期区间。
- `bucket`：按 `(space)` 聚合的分桶键。
- `peak`：同一 bucket 在词法序列上的最大并发字节数量。

## 目标

- 提供稳定的摘要结构用于统计与验证。
- 保持摘要输出稳定文本格式，便于直接比对。
- 在直线路径内完成同 bucket、非重叠生命周期的 pool 改写。

## 额外补充

### Helper 说明

- 公开 API 仅包含 `MemoryPoolPass`、`MemoryPoolSummary` 与 `MemoryPoolInterval`。
- alloc/free 配对、shape/stride 转符号表达式、slot 分配、byte-pool 改写等逻辑都属于当前文件内部实现细节。
- 其它实现文件与测试不得跨文件调用 `kernel_gen.passes.memory_pool` 中未列入 `API 列表` 的 helper。


### 失败短语

范围说明：

- 下列短语是 `KernelCodeError(message)` 的公开前缀集合；实现必须保证错误信息以 `<短语>: ` 开头，其后可追加上下文细节。
- 本清单覆盖 `MemoryPoolPass.apply(Context(), module)` 的摘要分析与（可选）IR 改写阶段，以及 `MemoryPoolPass.get_summary(func_name)` 的摘要查询阶段。
- 本清单不覆盖 `dma/nn/symbol` dialect verifier 的报错文本，也不覆盖其它 pass 的错误短语。

短语清单：

- `MemoryPoolInvalidModule`
  - 输入不是 `builtin.module`，或 module 结构无法被本 pass 处理（例如缺少可枚举的 `func.func`）。
- `MemoryPoolInvalidAlloc`
  - `dma.alloc` 本体或其结果类型不满足本 pass 的输入域约束（例如 alloc 结果不是 `nn.memory`），导致无法进入后续的生命周期分析与改写。
- `MemoryPoolEscapingAlloc`
  - alloc 结果逃逸出本 pass 可分析范围，例如被 return、被写入容器后跨出所在 `symbol.for` 的词法范围。
- `MemoryPoolInvalidLifetime`
  - `dma.alloc/dma.free` 的配对关系或词法生命周期不合法（例如找不到 free、重复 free、free 出现在 alloc 之前、或 loop 内不成对），导致无法构建稳定 interval。
- `MemoryPoolUnsupportedShape`
  - `nn.memory` 的 `shape/stride` 含本 pass 不支持的维度表示（例如匿名动态维 `?`，或动态维分量不属于约定的 `IntAttr` / 具名 `StringAttr`），导致无法形成稳定的字节数量表达式。
- `MemoryPoolUnsupportedDtype`
  - `nn.memory` 的 `dtype` 无法映射到稳定的字节宽度（例如缺少 element byte size 的定义），导致无法形成 `size_bytes_expr`。
- `MemoryPoolUnsupportedNonLinearAlloc`
  - alloc 对应的 memory 不是 contiguous 布局，或需要 custom stride 解释，导致无法按本 pass 的字节池模型计算 size/offset。
- `MemoryPoolRewriteUnsupported`
  - `rewrite=True` 时输入 IR 不满足改写前提（例如非单 block、出现除 `symbol.for` 以外的 region/control-flow 结构、同 bucket 区间无法证明不重叠、或字节 size 表达式不一致），因此只能拒绝改写而不是静默跳过。
- `MemoryPoolUnsupportedRegionEscape`
  - 出现非 `symbol.for` 的 region/control-flow 结构，或出现会导致 interval 归属与索引模型失效的 region 逃逸场景。
- `MemoryPoolUnsupportedPoolBucket`
  - alloc 无法归入当前按 bucket（例如按 `space`）聚合的 byte pool，例如 space 不受支持或 bucket key 无法稳定构造。
- `MemoryPoolTypedViewOutOfBounds`
  - typed `dma.view` 的字节区间越界，或与 dtype 字节宽度不匹配。
- `MemoryPoolSummaryNotFound`
  - `get_summary(func_name)` 查询不到对应的摘要。

### 模块级补充

- 本小节只记录模块级非接口补充；接口级参数限制、错误语义、兼容要求与非目标必须维护在对应 API 的 `注意事项`。
- 仅处理 `builtin.module` 内的 `func.func`。
- 仅支持 `dma.alloc` 结果为 `nn.memory` 且布局为 contiguous。
- `dma.alloc` 必须存在且仅存在一个对应的 `dma.free`，且顺序合法。
- 动态维度仅允许 `IntAttr` 或具名 `StringAttr`，不接受匿名 `?`。
- `rewrite=True` 仅支持单 block，允许 `symbol.for`，其余 region 直接拒绝。
- `symbol.for` 内 alloc 的生命周期按 region 进入/退出索引统计；分析不按迭代次数展开为多份 interval。
- 当 interval 在上述索引模型中可证明不重叠时，允许它们共享同一个 `offset_bytes_expr`（体现 byte pool 的复用）。
- 参与改写的 alloc 必须同 bucket、相同字节 size 表达式；生命周期重叠会分配不同 offset。
- pool 采用 1-D `i8` byte pool，并通过 `dma.view` 恢复原始类型。
- 公开导入入口固定为 `kernel_gen.passes.memory_pool`；`kernel_gen.passes.lowering.memory_pool` 不再属于公开合同，必须以 `ModuleNotFoundError` 失败。
- 当 lowering pipeline 同时包含 tile family、`SymbolLoopHoistPass`、`LowerDmaMemoryHierarchyPass` 时，`MemoryPoolPass` 的相对顺序要求为：
  - `tile family -> SymbolLoopHoistPass -> MemoryPoolPass -> LowerDmaMemoryHierarchyPass`


### `class MemoryPoolPass(rewrite: bool = False)`

- 功能说明：

- 生成每个 `func.func` 的 `MemoryPoolSummary`。
- 缓存摘要以供查询。

- 参数：

- `rewrite (bool)`：是否执行 IR 改写；`True` 仅在直线路径与同 bucket 条件满足时生效。

- 使用示例：

```python
from kernel_gen.passes.memory_pool import MemoryPoolPass

pass_obj = MemoryPoolPass(rewrite=False)
pass_obj.apply(Context(), module)
summary = pass_obj.get_summary("main")
```

- 注意事项：

- `rewrite=True` 会对符合条件的 alloc/free 进行 pool 改写。
- 仅对 `func.func` 统计，其余 op 会被跳过。

- 返回值：

- `apply(ctx, module)` 原地更新摘要与可选 IR 改写，返回 `None`。
- 不满足公开合同的输入会报错，不会静默跳过。

### `MemoryPoolPass.apply(ctx: Context, module: ModuleOp) -> None`

- 功能说明：

- 对 `module` 中每个 `func.func` 生成摘要。

- 参数：

- `module (builtin.module)`：待处理的 module。

- 使用示例：

```python
pass_obj = MemoryPoolPass(rewrite=False)
pass_obj.apply(Context(), module)
```

- 注意事项：

- 输入必须是 `builtin.module`，否则报错。
- `rewrite=True` 时 summary 先于 IR 改写生成。

- 返回值：

- 返回 `module` 本体。

### `MemoryPoolPass.get_summary(func_name: str)`

- 功能说明：

- 根据函数名返回对应摘要。

- 参数：

- `func_name (str)`：函数名。

- 使用示例：

```python
summary = pass_obj.get_summary("main")
```

- 注意事项：

- 不存在时抛出 `KernelCodeError`，错误前缀必须为 `MemoryPoolSummaryNotFound:`。

- 返回值：

- 返回 `MemoryPoolSummary`。

### `MemoryPoolPass.all_summaries() -> dict[str, MemoryPoolSummary]`

- 功能说明：

- 返回全部摘要的拷贝。

- 参数：

- 无。

- 使用示例：

```python
summaries = pass_obj.all_summaries()
```

- 注意事项：

- 返回值为浅拷贝，避免外部直接修改内部缓存。

- 返回值：

- 返回 `dict[str, MemoryPoolSummary]`。

### `class MemoryPoolSummary(func_name: str, intervals: tuple[MemoryPoolInterval, ...], peak_bytes_by_bucket: dict[tuple[str], sympy.Basic], pool_count: int)`

- 功能说明：

- 描述单个 `func.func` 的生命周期摘要。

- 参数：

- `func_name (str)`：函数名。
- `intervals (tuple[MemoryPoolInterval, ...])`：生命周期区间列表。
- `peak_bytes_by_bucket (dict[tuple[str], sympy.Basic])`：按 bucket 汇总的 peak 字节数。
- `pool_count (int)`：bucket 数量。

- 使用示例：

```python
summary = pass_obj.get_summary("main")
text = summary.to_text()
```

- 注意事项：

- `to_text()` 输出稳定文本格式，便于对比。

- 返回值：

- `to_text()` 返回 `str`。

### `class MemoryPoolInterval(name: str, bucket_key: tuple[str], size_bytes_expr: sympy.Basic, begin_index: int, end_index: int, offset_bytes_expr: sympy.Basic)`

- 功能说明：

- 描述单个 alloc 的生命周期区间与偏移信息。

- 参数：

- `name (str)`：alloc 名称。
- `bucket_key (tuple[str])`：分桶键。
- `size_bytes_expr (sympy.Basic)`：字节数量表达式。
- `begin_index (int)`：开始索引。
- `end_index (int)`：结束索引。
- `offset_bytes_expr (sympy.Basic)`：字节偏移表达式。

- 使用示例：

```python
interval = summary.intervals[0]
```

- 注意事项：

- `offset_bytes_expr` 由 slot 分配，等于 `size_bytes_expr * slot_index`。

- 返回值：

- 数据结构本身不执行验证。

## API详细说明

### `class MemoryPoolPass(rewrite: bool = False)`

- api：`class MemoryPoolPass(rewrite: bool = False)`
- 参数：
  - `rewrite`：`rewrite` 输入值，参与 `MemoryPoolPass` 的公开处理流程；类型 `bool`；默认值 `False`；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
- 返回值：`MemoryPoolPass` 实例。
- 使用示例：

  ```python
  memory_pool_pass = MemoryPoolPass(rewrite=False)
  ```
- 功能说明：定义 `MemoryPoolPass` pass 对象。
- 注意事项：构造参数必须符合本条目参数说明；实例内部缓存、状态字典和派生字段不作为外部可变入口。

### `name: str`

- api：`name: str`
- 参数：无。
- 返回值：`str` 的返回值；返回类型以 API 签名为准。
- 使用示例：

  ```python
  from kernel_gen.passes.memory_pool import MemoryPoolPass

  assert MemoryPoolPass.name == "memory-pool"
  ```
- 功能说明：执行 `str`。
- 注意事项：非法输入必须按本条目参数说明和公开错误语义处理；调用方不得依赖实现内部状态。

### `__init__(rewrite: bool = False) -> None`

- api：`__init__(rewrite: bool = False) -> None`
- 参数：
  - `rewrite`：`rewrite` 输入值，参与 `__init__` 的公开处理流程；类型 `bool`；默认值 `False`；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
- 返回值：无返回值；调用成功表示操作完成。
- 使用示例：

  ```python
  __init__(rewrite=False)
  ```
- 功能说明：执行 `__init__`。
- 注意事项：该特殊方法只承接 Python 对应协议语义；不得额外暴露内部字段。

### `apply(ctx: Context, op: ModuleOp) -> None`

- api：`apply(ctx: Context, op: ModuleOp) -> None`
- 参数：
  - `ctx`：公开上下文对象，提供代码生成、emit、pass 或工具执行所需的配置与状态；类型 `Context`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
  - `op`：IR operation，作为 emit、rewrite、lowering 或校验的当前处理对象；类型 `ModuleOp`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
- 返回值：无返回值；调用成功表示操作完成。
- 使用示例：

  ```python
  apply(ctx=ctx, op=op)
  ```
- 功能说明：执行 `apply`。
- 注意事项：非法输入必须按本条目参数说明和公开错误语义处理；调用方不得依赖实现内部状态。

### `apply(ctx: Context, module: ModuleOp) -> None`

- api：`apply(ctx: Context, module: ModuleOp) -> None`
- 参数：
  - `ctx`：公开上下文对象，提供代码生成、emit、pass 或工具执行所需的配置与状态；类型 `Context`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
  - `module`：模块级 IR 对象，作为 pass、校验或代码生成的处理主体；类型 `ModuleOp`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
- 返回值：无返回值；调用成功表示操作完成。
- 使用示例：

  ```python
  apply(ctx=ctx, module=module)
  ```
- 功能说明：执行 `apply`。
- 注意事项：非法输入必须按本条目参数说明和公开错误语义处理；调用方不得依赖实现内部状态。

### `get_summary(func_name: str) -> MemoryPoolSummary`

- api：`get_summary(func_name: str) -> MemoryPoolSummary`
- 参数：
  - `func_name`：公开名称或符号名；类型 `str`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
- 返回值：`MemoryPoolSummary`。
- 使用示例：

  ```python
  result = get_summary(func_name=func_name)
  ```
- 功能说明：读取 `summary`。
- 注意事项：该接口只读取公开状态；返回对象的内部可变结构不作为额外公开合同。

### `all_summaries() -> dict[str, MemoryPoolSummary]`

- api：`all_summaries() -> dict[str, MemoryPoolSummary]`
- 参数：无。
- 返回值：`dict[str, MemoryPoolSummary]`。
- 使用示例：

  ```python
  result = all_summaries()
  ```
- 功能说明：执行 `all_summaries`。
- 注意事项：非法输入必须按本条目参数说明和公开错误语义处理；调用方不得依赖实现内部状态。

### `class MemoryPoolSummary(func_name: str, intervals: tuple[MemoryPoolInterval, ...], peak_bytes_by_bucket: dict[tuple[str], sympy.Basic], pool_count: int)`

- api：`class MemoryPoolSummary(func_name: str, intervals: tuple[MemoryPoolInterval, ...], peak_bytes_by_bucket: dict[tuple[str], sympy.Basic], pool_count: int)`
- 参数：
  - `func_name`：公开名称或符号名；类型 `str`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
  - `intervals`：区间集合，定义 tiling、调度或符号范围的分段信息；类型 `tuple[MemoryPoolInterval, ...]`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
  - `peak_bytes_by_bucket`：`peak_bytes_by_bucket` 输入值，参与 `MemoryPoolSummary` 的公开处理流程；类型 `dict[tuple[str], sympy.Basic]`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按可变容器传入时，是否修改输入必须以本接口功能说明和注意事项为准；非法值按该 API 的公开错误语义处理。
  - `pool_count`：`pool_count` 输入值，参与 `MemoryPoolSummary` 的公开处理流程；类型 `int`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
- 返回值：`MemoryPoolSummary` 实例。
- 使用示例：

  ```python
  memory_pool_summary = MemoryPoolSummary(func_name=func_name, intervals=intervals, peak_bytes_by_bucket=peak_bytes_by_bucket, pool_count=pool_count)
  ```
- 功能说明：定义 `MemoryPoolSummary` 公开类型。
- 注意事项：构造参数必须符合本条目参数说明；实例内部缓存、状态字典和派生字段不作为外部可变入口。

### `to_text() -> str`

- api：`to_text() -> str`
- 参数：无。
- 返回值：`str`，表示生成或格式化后的文本。
- 使用示例：

  ```python
  result = to_text()
  ```
- 功能说明：执行 `to_text`。
- 注意事项：非法输入必须按本条目参数说明和公开错误语义处理；调用方不得依赖实现内部状态。

### `class MemoryPoolInterval(name: str, bucket_key: tuple[str], size_bytes_expr: sympy.Basic, begin_index: int, end_index: int, offset_bytes_expr: sympy.Basic)`

- api：`class MemoryPoolInterval(name: str, bucket_key: tuple[str], size_bytes_expr: sympy.Basic, begin_index: int, end_index: int, offset_bytes_expr: sympy.Basic)`
- 参数：
  - `name`：公开名称、符号名或注册名，用于查找、打印、注册或生成稳定标识；类型 `str`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
  - `bucket_key`：`bucket_key` 输入值，参与 `MemoryPoolInterval` 的公开处理流程；类型 `tuple[str]`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
  - `size_bytes_expr`：大小或容量值；类型 `sympy.Basic`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
  - `begin_index`：`begin_index` 输入值，参与 `MemoryPoolInterval` 的公开处理流程；类型 `int`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
  - `end_index`：`end_index` 输入值，参与 `MemoryPoolInterval` 的公开处理流程；类型 `int`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
  - `offset_bytes_expr`：偏移量；类型 `sympy.Basic`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
- 返回值：`MemoryPoolInterval` 实例。
- 使用示例：

  ```python
  memory_pool_interval = MemoryPoolInterval(name=name, bucket_key=bucket_key, size_bytes_expr=size_bytes_expr, begin_index=begin_index, end_index=end_index, offset_bytes_expr=offset_bytes_expr)
  ```
- 功能说明：定义 `MemoryPoolInterval` 公开类型。
- 注意事项：构造参数必须符合本条目参数说明；实例内部缓存、状态字典和派生字段不作为外部可变入口。

## 测试

- 测试文件：
  - `test/passes/test_memory_pool.py`
  - `test/passes/test_registry.py`
- 执行命令：
  - `pytest -q test/passes/test_memory_pool.py`
  - `pytest -q test/passes/test_memory_pool.py -k "symbol_for or escape or layout or invalid_lifetime"`

### 测试目标

- 验证 `spec/pass/lowering/memory_pool.md` 对应公开 API 的正常路径、边界条件与错误语义。
- 验证 Memory/DMA 参数、布局、搬运或 verifier 行为。
- 验证 pass 或 pipeline 对目标 IR 的改写、no-op 与顺序约束。
- 验证非法输入、边界条件和错误语义按公开合同失败。


### 功能与用例清单

| 用例 ID | 功能 | 场景 | 前置条件 | 操作 | 预期结果 | 建议测试 |
| --- | --- | --- | --- | --- | --- | --- |
| TC-PASS-LOWERING-MEMORY-POOL-001 | 内存/DMA | `test_memory_pool_summary_basic` | 准备公开 Memory/DMA 参数，包括 shape、stride、dtype、space 或切片元信息。 | 运行 `test_memory_pool_summary_basic`。 | 内存类型、布局、搬运结果或 verifier 行为体现“`test_memory_pool_summary_basic`”场景。 | `test_memory_pool_summary_basic` |
| TC-PASS-LOWERING-MEMORY-POOL-002 | 内存/DMA | `test_memory_pool_interval_indices` | 准备公开 Memory/DMA 参数，包括 shape、stride、dtype、space 或切片元信息。 | 运行 `test_memory_pool_interval_indices`。 | 内存类型、布局、搬运结果或 verifier 行为体现“`test_memory_pool_interval_indices`”场景。 | `test_memory_pool_interval_indices` |
| TC-PASS-LOWERING-MEMORY-POOL-003 | 内存/DMA | `test_memory_pool_peak_overlap` | 准备公开 Memory/DMA 参数，包括 shape、stride、dtype、space 或切片元信息。 | 运行 `test_memory_pool_peak_overlap`。 | 内存类型、布局、搬运结果或 verifier 行为体现“`test_memory_pool_peak_overlap`”场景。 | `test_memory_pool_peak_overlap` |
| TC-PASS-LOWERING-MEMORY-POOL-004 | pass 改写 | `test_memory_pool_rewrite_straight_line_pool_reuse` | 准备包含目标 op、pass 名称或 pipeline 的公开 IR 输入。 | 运行 `test_memory_pool_rewrite_straight_line_pool_reuse`。 | IR 改写后的 op、属性、顺序或 no-op 行为体现“`test_memory_pool_rewrite_straight_line_pool_reuse`”场景。 | `test_memory_pool_rewrite_straight_line_pool_reuse` |
| TC-PASS-LOWERING-MEMORY-POOL-005 | pass 改写 | `test_memory_pool_rewrite_multiple_buckets` | 准备包含目标 op、pass 名称或 pipeline 的公开 IR 输入。 | 运行 `test_memory_pool_rewrite_multiple_buckets`。 | IR 改写后的 op、属性、顺序或 no-op 行为体现“`test_memory_pool_rewrite_multiple_buckets`”场景。 | `test_memory_pool_rewrite_multiple_buckets` |
| TC-PASS-LOWERING-MEMORY-POOL-006 | 边界/异常 | `test_memory_pool_rewrite_size_mismatch` | 准备触发该错误路径的公开输入或非法参数组合。 | 运行 `test_memory_pool_rewrite_size_mismatch`。 | “`test_memory_pool_rewrite_size_mismatch`”场景按公开错误语义失败或被拒绝。 | `test_memory_pool_rewrite_size_mismatch` |
| TC-PASS-LOWERING-MEMORY-POOL-007 | pass 改写 | `test_memory_pool_rewrite_overlap` | 准备包含目标 op、pass 名称或 pipeline 的公开 IR 输入。 | 运行 `test_memory_pool_rewrite_overlap`。 | IR 改写后的 op、属性、顺序或 no-op 行为体现“`test_memory_pool_rewrite_overlap`”场景。 | `test_memory_pool_rewrite_overlap` |
| TC-PASS-LOWERING-MEMORY-POOL-008 | pass 改写 | `test_memory_pool_rewrite_multiple_blocks` | 准备包含目标 op、pass 名称或 pipeline 的公开 IR 输入。 | 运行 `test_memory_pool_rewrite_multiple_blocks`。 | IR 改写后的 op、属性、顺序或 no-op 行为体现“`test_memory_pool_rewrite_multiple_blocks`”场景。 | `test_memory_pool_rewrite_multiple_blocks` |
| TC-PASS-LOWERING-MEMORY-POOL-009 | 边界/异常 | `test_memory_pool_invalid_module` | 准备触发该错误路径的公开输入或非法参数组合。 | 运行 `test_memory_pool_invalid_module`。 | “`test_memory_pool_invalid_module`”场景按公开错误语义失败或被拒绝。 | `test_memory_pool_invalid_module` |
| TC-PASS-LOWERING-MEMORY-POOL-010 | 内存/DMA | `test_memory_pool_non_contiguous_layout` | 准备公开 Memory/DMA 参数，包括 shape、stride、dtype、space 或切片元信息。 | 运行 `test_memory_pool_non_contiguous_layout`。 | 内存类型、布局、搬运结果或 verifier 行为体现“`test_memory_pool_non_contiguous_layout`”场景。 | `test_memory_pool_non_contiguous_layout` |
| TC-PASS-LOWERING-MEMORY-POOL-011 | 内存/DMA | `test_memory_pool_unpaired_alloc` | 准备公开 Memory/DMA 参数，包括 shape、stride、dtype、space 或切片元信息。 | 运行 `test_memory_pool_unpaired_alloc`。 | 内存类型、布局、搬运结果或 verifier 行为体现“`test_memory_pool_unpaired_alloc`”场景。 | `test_memory_pool_unpaired_alloc` |
| TC-PASS-LOWERING-MEMORY-POOL-012 | 内存/DMA | `test_memory_pool_anonymous_dim` | 准备公开 Memory/DMA 参数，包括 shape、stride、dtype、space 或切片元信息。 | 运行 `test_memory_pool_anonymous_dim`。 | 内存类型、布局、搬运结果或 verifier 行为体现“`test_memory_pool_anonymous_dim`”场景。 | `test_memory_pool_anonymous_dim` |
| TC-PASS-LOWERING-MEMORY-POOL-013 | 内存/DMA | `test_memory_pool_alloc_non_memory` | 准备公开 Memory/DMA 参数，包括 shape、stride、dtype、space 或切片元信息。 | 运行 `test_memory_pool_alloc_non_memory`。 | 内存类型、布局、搬运结果或 verifier 行为体现“`test_memory_pool_alloc_non_memory`”场景。 | `test_memory_pool_alloc_non_memory` |
| TC-PASS-LOWERING-MEMORY-POOL-014 | 内存/DMA | `test_memory_pool_symbol_for_reuse` | 准备公开 Memory/DMA 参数，包括 shape、stride、dtype、space 或切片元信息。 | 运行 `test_memory_pool_symbol_for_reuse`。 | 内存类型、布局、搬运结果或 verifier 行为体现“`test_memory_pool_symbol_for_reuse`”场景。 | `test_memory_pool_symbol_for_reuse` |
| TC-PASS-LOWERING-MEMORY-POOL-015 | 内存/DMA | `test_memory_pool_escape_return` | 准备公开 Memory/DMA 参数，包括 shape、stride、dtype、space 或切片元信息。 | 运行 `test_memory_pool_escape_return`。 | 内存类型、布局、搬运结果或 verifier 行为体现“`test_memory_pool_escape_return`”场景。 | `test_memory_pool_escape_return` |
| TC-PASS-LOWERING-MEMORY-POOL-016 | 边界/异常 | `test_memory_pool_invalid_lifetime_loop` | 准备触发该错误路径的公开输入或非法参数组合。 | 运行 `test_memory_pool_invalid_lifetime_loop`。 | “`test_memory_pool_invalid_lifetime_loop`”场景按公开错误语义失败或被拒绝。 | `test_memory_pool_invalid_lifetime_loop` |
| TC-PASS-LOWERING-MEMORY-POOL-017 | 内存/DMA | `test_memory_pool_unsupported_region_escape` | 准备公开 Memory/DMA 参数，包括 shape、stride、dtype、space 或切片元信息。 | 运行 `test_memory_pool_unsupported_region_escape`。 | 内存类型、布局、搬运结果或 verifier 行为体现“`test_memory_pool_unsupported_region_escape`”场景。 | `test_memory_pool_unsupported_region_escape` |
| TC-PASS-LOWERING-MEMORY-POOL-018 | 边界/异常 | `test_memory_pool_public_summary_access_edges` | 准备空函数 module、多 key bucket summary 与缺失函数名查询。 | 运行 `test_memory_pool_public_summary_access_edges`。 | `MemoryPoolPass` 跳过非函数 op、空函数摘要稳定输出、`all_summaries()` 返回拷贝、缺失 summary 按 `MemoryPoolSummaryNotFound` 公开错误失败。 | `test_memory_pool_public_summary_access_edges` |
| TC-PASS-LOWERING-MEMORY-POOL-019 | 内存/DMA | `test_memory_pool_dtype_and_symbolic_shape_matrix` | 准备公开 dtype 矩阵、非法 dtype 与具名符号 shape 的 contiguous memory。 | 运行 `test_memory_pool_dtype_and_symbolic_shape_matrix`。 | dtype 字节数、非法 dtype 错误、符号 size 表达式与 `rewrite=True` 生成的 `dma.view` 类型均按公开合同稳定。 | `test_memory_pool_dtype_and_symbolic_shape_matrix` |
| TC-PASS-LOWERING-MEMORY-POOL-020 | 边界/异常 | `test_memory_pool_public_invalid_shape_stride_and_free_edges` | 准备匿名 stride 与重复 dma.free 的公开 IR 输入。 | 运行 `test_memory_pool_public_invalid_shape_stride_and_free_edges`。 | `MemoryPoolPass.apply(...)` 按 `MemoryPoolUnsupportedNonLinearAlloc` 或 `MemoryPoolInvalidLifetime` 公开错误语义失败。 | `test_memory_pool_public_invalid_shape_stride_and_free_edges` |
| TC-PASS-LOWERING-MEMORY-POOL-021 | pass 改写 | `test_memory_pool_rewrite_non_alloc_noop` | 准备不含 `dma.alloc/dma.free` 的单 block 函数，并启用 `rewrite=True`。 | 运行 `test_memory_pool_rewrite_non_alloc_noop`。 | summary 为空且 IR 不新增 pool/view/free，保持公开 no-op 行为。 | `test_memory_pool_rewrite_non_alloc_noop` |
