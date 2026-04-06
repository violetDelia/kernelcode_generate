# memory_pool.md

## 功能简介

- 定义 `MemoryPoolPass` 的公开合同：基于 `dma.alloc/dma.free` 生成内存生命周期摘要结构。
- 提供 `MemoryPoolSummary/MemoryPoolInterval` 稳定接口，用于后续统计与验证。
- 当前阶段仅输出摘要信息，不执行 IR 改写。

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
- `bucket`：按 `(space, element_type, layout)` 聚合的分桶键。
- `peak`：同一 bucket 在词法序列上的最大并发元素数量。

## 目标

- 提供稳定的摘要结构用于统计与验证。
- 保持摘要输出稳定文本格式，便于直接比对。

## 限制与边界

- 仅处理 `builtin.module` 内的 `func.func`。
- 仅支持 `dma.alloc` 结果为 `nn.memory` 且布局为 contiguous。
- `dma.alloc` 必须存在且仅存在一个对应的 `dma.free`，且顺序合法。
- 动态维度仅允许 `IntAttr` 或具名 `StringAttr`，不接受匿名 `?`。
- `rewrite=True` 直接报错，本阶段不执行 IR 改写。

## 公开接口

### `class MemoryPoolPass(Pass)`

功能说明：

- 生成每个 `func.func` 的 `MemoryPoolSummary`。
- 缓存摘要以供查询。

参数说明：

- `rewrite (bool)`：是否执行 IR 改写；当前仅支持 `False`。

使用示例：

```python
from kernel_gen.passes.lowering.memory_pool import MemoryPoolPass

pass_obj = MemoryPoolPass(rewrite=False)
pass_obj.run(module)
summary = pass_obj.get_summary("main")
```

注意事项：

- `rewrite=True` 会触发显式失败。
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

- 不存在时抛出 `MemoryPoolError`。

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
- `peak_numel_by_bucket (dict[tuple[str, str, str], sympy.Basic])`：按 bucket 汇总的 peak 元素数。
- `peak_bytes_by_bucket (dict[tuple[str, str, str], sympy.Basic])`：按 bucket 汇总的 peak 字节数。
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
- `bucket_key (tuple[str, str, str])`：分桶键。
- `size_expr (sympy.Basic)`：元素数量表达式。
- `begin_index (int)`：开始索引。
- `end_index (int)`：结束索引。
- `offset_expr (sympy.Basic)`：偏移表达式。

使用示例：

```python
interval = summary.intervals[0]
```

注意事项：

- 目前 `offset_expr` 固定为 `0`。

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

## 测试

- 测试文件：[`test/pass/test_memory_pool.py`](../../../test/pass/test_memory_pool.py)
- 执行命令：`pytest -q test/pass/test_memory_pool.py -k "summary or interval or peak"`
- 测试目标：
  - 验证摘要生成与文本输出稳定。
  - 验证区间索引与 bucket 统计正确。
  - 验证 peak 统计在重叠区间时正确。
- 功能与用例清单：
  - `test_memory_pool_summary_basic`
  - `test_memory_pool_interval_indices`
  - `test_memory_pool_peak_overlap`
