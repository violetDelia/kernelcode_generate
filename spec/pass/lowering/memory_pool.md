# memory_pool.md

## 功能简介

- 定义 `MemoryPoolPass` 的公开合同：基于 `dma.alloc/dma.free` 生成内存生命周期摘要结构。
- 提供 `MemoryPoolSummary/MemoryPoolInterval` 稳定接口，用于后续统计与验证。
- 支持直线路径的 pool 改写：将符合约束的 `dma.alloc/dma.free` 改写为 `i8` byte pool + `dma.view`。

## 文档信息

- 创建者：`金铲铲大作战`
- 最后一次更改：`金铲铲大作战`
- `spec`：[`spec/pass/lowering/memory_pool.md`](../../../spec/pass/lowering/memory_pool.md)
- `功能实现`：[`kernel_gen/passes/lowering/memory_pool.py`](../../../kernel_gen/passes/lowering/memory_pool.py)
- `test`：[`test/pass/test_memory_pool.py`](../../../test/pass/test_memory_pool.py)

## 依赖

- `dma` dialect：[`kernel_gen/dialect/dma.py`](../../../kernel_gen/dialect/dma.py)
- `nn` memory type：[`kernel_gen/dialect/nn.py`](../../../kernel_gen/dialect/nn.py)
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

## 限制与边界

- 仅处理 `builtin.module` 内的 `func.func`。
- 仅支持 `dma.alloc` 结果为 `nn.memory` 且布局为 contiguous。
- `dma.alloc` 必须存在且仅存在一个对应的 `dma.free`，且顺序合法。
- 动态维度仅允许 `IntAttr` 或具名 `StringAttr`，不接受匿名 `?`。
- `rewrite=True` 仅支持单 block，允许 `symbol.for`，其余 region 直接拒绝。
- `symbol.for` 内 alloc 的生命周期按 region 进入/退出索引统计；分析不按迭代次数展开为多份 interval。
- 当 interval 在上述索引模型中可证明不重叠时，允许它们共享同一个 `offset_bytes_expr`（体现 byte pool 的复用）。
- 参与改写的 alloc 必须同 bucket、相同字节 size 表达式；生命周期重叠会分配不同 offset。
- pool 采用 1-D `i8` byte pool，并通过 `dma.view` 恢复原始类型。
- 当 lowering pipeline 同时包含 tile family、`SymbolLoopHoistPass`、`LowerDmaMemoryHierarchyPass` 时，`MemoryPoolPass` 的相对顺序要求为：
  - `tile family -> SymbolLoopHoistPass -> MemoryPoolPass -> LowerDmaMemoryHierarchyPass`

## 公开接口

### `class MemoryPoolPass(Pass)`

功能说明：

- 生成每个 `func.func` 的 `MemoryPoolSummary`。
- 缓存摘要以供查询。

参数说明：

- `rewrite (bool)`：是否执行 IR 改写；`True` 仅在直线路径与同 bucket 条件满足时生效。

使用示例：

```python
from kernel_gen.passes.lowering.memory_pool import MemoryPoolPass

pass_obj = MemoryPoolPass(rewrite=False)
pass_obj.run(module)
summary = pass_obj.get_summary("main")
```

注意事项：

- `rewrite=True` 会对符合条件的 alloc/free 进行 pool 改写。
- 仅对 `func.func` 统计，其余 op 会被跳过。

返回与限制：

- `run(module)` 返回输入 `module`。
- 不满足公开合同的输入会报错，不会静默跳过。

### `MemoryPoolPass.run(module)`

功能说明：

- 对 `module` 中每个 `func.func` 生成摘要。

参数说明：

- `module (builtin.module)`：待处理的 module。

使用示例：

```python
pass_obj = MemoryPoolPass(rewrite=False)
module = pass_obj.run(module)
```

注意事项：

- 输入必须是 `builtin.module`，否则报错。
- `rewrite=True` 时 summary 先于 IR 改写生成。

返回与限制：

- 返回 `module` 本体。

### `MemoryPoolPass.get_summary(func_name)`

功能说明：

- 根据函数名返回对应摘要。

参数说明：

- `func_name (str)`：函数名。

使用示例：

```python
summary = pass_obj.get_summary("main")
```

注意事项：

- 不存在时抛出 `MemoryPoolError`，错误短语必须为 `MemoryPoolSummaryNotFound`。

返回与限制：

- 返回 `MemoryPoolSummary`。

### `MemoryPoolPass.all_summaries()`

功能说明：

- 返回全部摘要的拷贝。

参数说明：

- 无。

使用示例：

```python
summaries = pass_obj.all_summaries()
```

注意事项：

- 返回值为浅拷贝，避免外部直接修改内部缓存。

返回与限制：

- 返回 `dict[str, MemoryPoolSummary]`。

### `class MemoryPoolSummary`

功能说明：

- 描述单个 `func.func` 的生命周期摘要。

参数说明：

- `func_name (str)`：函数名。
- `intervals (tuple[MemoryPoolInterval, ...])`：生命周期区间列表。
- `peak_bytes_by_bucket (dict[tuple[str], sympy.Basic])`：按 bucket 汇总的 peak 字节数。
- `pool_count (int)`：bucket 数量。

使用示例：

```python
summary = pass_obj.get_summary("main")
text = summary.to_text()
```

注意事项：

- `to_text()` 输出稳定文本格式，便于对比。

返回与限制：

- `to_text()` 返回 `str`。

### `class MemoryPoolInterval`

功能说明：

- 描述单个 alloc 的生命周期区间与偏移信息。

参数说明：

- `name (str)`：alloc 名称。
- `bucket_key (tuple[str])`：分桶键。
- `size_bytes_expr (sympy.Basic)`：字节数量表达式。
- `begin_index (int)`：开始索引。
- `end_index (int)`：结束索引。
- `offset_bytes_expr (sympy.Basic)`：字节偏移表达式。

使用示例：

```python
interval = summary.intervals[0]
```

注意事项：

- `offset_bytes_expr` 由 slot 分配，等于 `size_bytes_expr * slot_index`。

返回与限制：

- 数据结构本身不执行验证。

### `class MemoryPoolError(ValueError)`

功能说明：

- 统一摘要分析阶段的错误类型。

参数说明：

- `message (str)`：错误信息。

使用示例：

```python
raise MemoryPoolError("MemoryPoolInvalidLifetime: dma.free not found for alloc")
```

注意事项：

- 错误短语用于定位不满足公开合同的输入。

返回与限制：

- 继承 `ValueError`。

## 额外补充

### 失败短语

范围说明：

- 下列短语是 `MemoryPoolError(message)` 的公开前缀集合；实现必须保证错误信息以 `<短语>: ` 开头，其后可追加上下文细节。
- 本清单覆盖 `MemoryPoolPass.run(module)` 的摘要分析与（可选）IR 改写阶段，以及 `MemoryPoolPass.get_summary(func_name)` 的摘要查询阶段。
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

## 测试

- 测试文件：[`test/pass/test_memory_pool.py`](../../../test/pass/test_memory_pool.py)
- 执行命令：
  - `pytest -q test/pass/test_memory_pool.py`
  - `pytest -q test/pass/test_memory_pool.py -k "symbol_for or escape or layout or invalid_lifetime"`
  - `PYTHONPATH=. python -m expectation.pass.lowing.memory_pool`
  - `PYTHONPATH=. python expectation/pass/lowing/memory_pool/summary.py`
  - `PYTHONPATH=. python expectation/pass/lowing/memory_pool/loop_reuse.py`
- 测试目标：
  - 验证摘要生成与文本输出稳定。
  - 验证区间索引与 bucket 统计正确。
  - 验证 peak 统计在重叠区间时正确。
  - 验证直线路径改写生成 pool/view。
  - 验证 `symbol.for` 的 lifecycle 计算与 offset 复用。
  - 验证拒绝路径短语稳定。
- 功能与用例清单：
  - `test_memory_pool_summary_basic`
  - `test_memory_pool_interval_indices`
  - `test_memory_pool_peak_overlap`
  - `test_memory_pool_rewrite_straight_line_pool_reuse`
  - `test_memory_pool_rewrite_multiple_buckets`
  - `test_memory_pool_rewrite_size_mismatch`
  - `test_memory_pool_rewrite_overlap`
  - `test_memory_pool_rewrite_multiple_blocks`
  - `test_memory_pool_invalid_module`
  - `test_memory_pool_non_contiguous_layout`
  - `test_memory_pool_unpaired_alloc`
  - `test_memory_pool_anonymous_dim`
  - `test_memory_pool_alloc_non_memory`
  - `test_memory_pool_symbol_for_reuse`
  - `test_memory_pool_escape_return`
  - `test_memory_pool_invalid_lifetime_loop`
  - `test_memory_pool_unsupported_region_escape`
