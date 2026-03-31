# func_cost.md

## 功能简介

- 定义一个面向 `func.func` 的分析 pass：统计函数内计算量（compute）与访存量（read/write bytes）。
- 统计结果支持静态维度与符号维度（如 `A`、`B`），输出符号表达式。
- pass 只做分析，不改写 op 语义，不做 lowering、优化或代码生成。

## 文档信息

- 创建者：`榕`
- 最后一次更改：`榕`
- `spec`：[`spec/pass/analysis/func_cost.md`](../../../spec/pass/analysis/func_cost.md)
- `功能实现`：[`kernel_gen/passes/analysis/func_cost.py`](../../../kernel_gen/passes/analysis/func_cost.py)
- `test`：[`test/pass/test_analysis_func_cost.py`](../../../test/pass/test_analysis_func_cost.py)

## 依赖

- Pass 抽象与管理器：[`spec/pass/pass_manager.md`](../../../spec/pass/pass_manager.md)
- NN dialect：[`spec/dialect/nn.md`](../../../spec/dialect/nn.md)
- Kernel dialect：[`spec/dialect/kernel.md`](../../../spec/dialect/kernel.md)
- DMA dialect：[`spec/dialect/dma.md`](../../../spec/dialect/dma.md)
- 符号/内存模型：[`spec/symbol_variable/symbol_dim.md`](../../../spec/symbol_variable/symbol_dim.md)、[`spec/symbol_variable/symbol_shape.md`](../../../spec/symbol_variable/symbol_shape.md)、[`spec/symbol_variable/memory.md`](../../../spec/symbol_variable/memory.md)

## 目标

- 在函数级给出可落地的成本统计：`compute`、`read_bytes`、`write_bytes`。
- 支持逐 op 统计与函数总计统计。
- 支持以符号表达式展示结果，便于后续调度、分块、性能估算使用。

## 限制与边界

- 本 pass 仅分析，不负责：
  - IR 变换与重写；
  - 跨函数联动分析；
  - 缓存复用、并行度、带宽/延迟等硬件级建模。
- 默认口径为“理论访存量”，不扣除 cache 命中带来的实际流量减少。
- 默认只统计白名单 op；非白名单 op 一律跳过并输出告警信息，不中断分析流程。

## 统计口径

### 1. 计算量（compute）

- 逐元素算术/比较（`nn.add/sub/mul/truediv/eq/ne/lt/le/gt/ge`，`kernel.add/sub/mul/div/eq/lt/gt`）：
  - `compute = numel(output)`。
- `nn.matmul`：
  - `compute = 2 * M * N * K`（按乘加各 1 次计）。
- `nn.broadcast` 与纯 DMA 搬运类 op：
  - `compute = 0`。
- `dma.cast`：
  - `compute = numel(output)`（按逐元素类型转换计 1 次）。

### 2. 访存量（read/write bytes）

- 通用公式：
  - `read_bytes = 读取元素数 * element_size(bytes)`
  - `write_bytes = 写入元素数 * element_size(bytes)`
- 对于比较类输出，若结果 element type 为 `i1`，按 `predicate_size`（默认 1 byte）计写回。
- `rhs` 为标量常量时（如 `A + 1`），标量不计内存读取。
- 维度为符号时，元素数按符号乘积表示，如 `numel([A, B]) = A * B`。

### 3. 与用户示例对齐

- 场景：`A:[A,B]`，`B:[A,B]`，执行逐元素 `add`，再与常量 `1` 做逐元素 `add`。
- 结论：
  - 每个 `add` 的计算量都是 `A * B`。
  - 第一个 `add` 读 `2 * A * B` 个元素，写 `A * B` 个元素。
  - 第二个 `add`（`tensor + const`）读 `A * B` 个元素（常量不计读），写 `A * B` 个元素。

## 支持的 op 范围

- `nn`：`add/sub/mul/truediv/eq/ne/lt/le/gt/ge/broadcast/matmul`
- `kernel`：`add/sub/mul/div/eq/lt/gt/select/cast`
- `dma`：`copy/load/store/slice/deslice/view/reshape/flatten/cast/alloc/free`

### DMA 口径约定

- `dma.copy/load/store/slice/deslice/view/reshape/flatten`：按数据搬运计读写，`compute=0`。
- `dma.cast`：按数据转换计 `compute=numel(output)`，同时计读写。
- `dma.alloc/free`：默认 `compute=0`、`read=0`、`write=0`（仅资源管理，不计数据面流量）。

## 公开接口

### `class FuncCostAnalysisError(ValueError)`

功能说明：

- 分析失败时的统一异常类型。

参数说明：

- `message (str)`：错误说明。

使用示例：

```python
raise FuncCostAnalysisError("unsupported op: foo.bar")
```

注意事项：

- 该异常用于“输入非法或统计前置条件不满足”的失败场景（如类型信息缺失且无法推断）。

返回与限制：

- 抛错即终止当前函数分析。

### `class OpCost`

功能说明：

- 记录单个 op 的统计结果。

参数说明：

- `op_name (str)`：op 名称，如 `nn.add`。
- `compute (Expr)`：该 op 计算量表达式。
- `read_bytes (Expr)`：该 op 读取字节表达式。
- `write_bytes (Expr)`：该 op 写入字节表达式。

使用示例：

```python
OpCost("nn.add", compute=A * B, read_bytes=2 * A * B * 4, write_bytes=A * B * 4)
```

注意事项：

- `Expr` 可以是整数或符号表达式。

返回与限制：

- 仅承载统计值，不负责校验逻辑。

### `class FuncCostSummary`

功能说明：

- 函数级统计汇总。

参数说明：

- `func_name (str)`：函数名。
- `ops (list[OpCost])`：逐 op 统计。
- `total_compute (Expr)`：函数总计算量。
- `total_read_bytes (Expr)`：函数总读取字节。
- `total_write_bytes (Expr)`：函数总写入字节。

使用示例：

```python
summary = pass_obj.get_summary("my_func")
```

注意事项：

- `total_*` 必须等于 `ops` 中对应字段逐项求和。

返回与限制：

- 作为对外可查询分析结果。

### `class AnalyzeFuncCostPass(Pass)`

功能说明：

- 对 module 中每个 `func.func` 执行计算/访存分析。

参数说明：

- `predicate_size (int)`：比较结果字节数，默认 `1`。
- `attach_attrs (bool)`：默认 `False`。为 `True` 时将汇总结果写到 `func.func` 属性中（字符串形式）。
- `dtype_size_overrides (dict[str, int] | None)`：可选类型字节覆盖配置。

使用示例：

```python
from kernel_gen.passes.pass_manager import PassManager
from kernel_gen.passes.analysis.func_cost import AnalyzeFuncCostPass

pm = PassManager(name="analysis")
cost_pass = AnalyzeFuncCostPass(attach_attrs=True)
pm.add_pass(cost_pass)
module = pm.run(module)
summary = cost_pass.get_summary("func_B")
```

注意事项：

- `run(module)` 返回 `module` 本身（分析 pass，不改写语义）。
- 分析结果需在 pass 实例内可查询（例如 `get_summary()` / `all_summaries()`）。
- `attach_attrs=True` 时，建议附加：
  - `analysis.compute`
  - `analysis.read_bytes`
  - `analysis.write_bytes`

返回与限制：

- 返回输入 `module`。
- 未知自定义 op 会跳过并告警，不计入统计总量。

### `AnalyzeFuncCostPass.run(module)`

功能说明：

- 扫描 module 内所有 `func.func`，统计每个函数的成本。

参数说明：

- `module (builtin.module)`：待分析 module。

使用示例：

```python
pass_obj = AnalyzeFuncCostPass()
module = pass_obj.run(module)
```

注意事项：

- 必须支持符号维度表达式，不得将符号维强制转为具体整数。
- 函数内 `func.return`、`arith.constant` 等非业务 op 默认不计入成本。

返回与限制：

- 返回 `module`（允许附加统计属性）。

## 默认 dtype 字节映射

- `i1 -> 1`（比较结果按 `predicate_size` 优先）
- `i8/u8 -> 1`
- `i16/u16/f16/bf16 -> 2`
- `i32/u32/f32 -> 4`
- `i64/u64/f64 -> 8`
- 未识别类型：跳过该 op，并记录告警信息。

## 测试

- 测试文件：[`test/pass/test_analysis_func_cost.py`](../../../test/pass/test_analysis_func_cost.py)
- 执行命令：`pytest -q test/pass/test_analysis_func_cost.py`
- 覆盖 `FC-001` ~ `FC-008` 用例。

### 测试目标

- 验证逐元素 op 的计算量口径为输出元素数。
- 验证 `tensor + const` 时常量不计读流量。
- 验证 `matmul` 计算量公式与读写公式。
- 验证 DMA 搬运类 op 的读写统计。
- 验证未知 op 会被跳过并输出告警，不影响其余 op 统计。
- 验证符号维度表达式（如 `A*B`）可正确保留。
- 验证 compare 输出为 `i1` 时，`write_bytes` 按 `predicate_size` 统计，且优先于 `dtype_size_overrides["i1"]`。

### 功能与用例清单

| 用例 ID | 场景描述 | 测试文件 | 对应测试 | 状态说明 |
| --- | --- | --- | --- | --- |
| `FC-001` | 输入 `shape=[A,B]` 的 `nn.add`，预期 `compute=A*B`。 | `test/pass/test_analysis_func_cost.py` | `test_func_cost_nn_add_symbolic_shape` | 已闭环。 |
| `FC-002` | 输入 `tensor + const`，预期 `compute=A*B` 且常量不计读取流量。 | `test/pass/test_analysis_func_cost.py` | `test_func_cost_tensor_plus_const` | 已闭环。 |
| `FC-003` | 输入同一 `func` 内串联两个逐元素 op，预期函数总量为两 op 逐项求和。 | `test/pass/test_analysis_func_cost.py` | `test_func_cost_chain_accumulate` | 已闭环。 |
| `FC-004` | 输入 `lhs=[M,K], rhs=[K,N]` 的 `nn.matmul`，预期 `compute=2*M*N*K`。 | `test/pass/test_analysis_func_cost.py` | `test_func_cost_matmul_formula` | 已闭环。 |
| `FC-005` | 输入 `dma.copy/load/store`，预期 `compute=0` 且读写字节按元素数统计。 | `test/pass/test_analysis_func_cost.py` | `test_func_cost_dma_memory_traffic` | 已闭环。 |
| `FC-006` | 输入同时含未知 op 与受支持 op 的函数，预期未知 op 被跳过并告警，其余统计保持正常。 | `test/pass/test_analysis_func_cost.py` | `test_func_cost_skips_unknown_op_with_warning` | 已闭环。 |
| `FC-007` | 输入 `attach_attrs=True` 的分析 pass，预期 `func` 回写 `analysis.*` 属性。 | `test/pass/test_analysis_func_cost.py` | `test_func_cost_attach_attrs` | 已闭环。 |
| `FC-008` | 输入 `nn.eq` 输出 `i1`，预期 `write_bytes` 优先按 `predicate_size` 统计（高于 `dtype_size_overrides["i1"]`）。 | `test/pass/test_analysis_func_cost.py` | `test_func_cost_compare_i1_uses_predicate_size` | 已闭环。 |
