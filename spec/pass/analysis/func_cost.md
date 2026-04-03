# func_cost.md

## 功能简介

- 定义一个面向 `func.func` 的分析 pass：通过统一入口 `analysis(func_op, AnalysisConfig, otherargs)` 读取函数级 `AnalysisResult`，并向外提供 `compute/read_bytes/write_bytes` 兼容 derived alias。
- 统计结果支持静态维度与符号维度（如 `A`、`B`），输出符号表达式。
- pass 只做分析，不改写 op 语义，不做 lowering、优化或代码生成。

## 文档信息

- 创建者：`榕`
- 最后一次更改：`睡觉小分队`
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

- 在函数级给出可查询的兼容字段：`compute`、`read_bytes`、`write_bytes`。
- 支持逐 op 统计与函数总计统计，但这些统计都必须来自统一入口结果的机械派生。
- 支持以符号表达式展示结果，便于后续调度、分块、性能估算使用。
- 明确 `func_cost` 只消费统一入口 `AnalysisResult` 的 derived alias，而不是单独维护第二套统计公式或支持范围。

## 限制与边界

- 本 pass 仅分析，不负责：
  - IR 变换与重写；
  - 跨函数联动分析；
  - 缓存复用、并行度、带宽/延迟等硬件级建模。
- 默认口径为“理论访存量”，不扣除 cache 命中带来的实际流量减少；该口径直接继承统一入口当前主线语义。
- `func_cost` 的稳定来源是 [`analysis_engine.md`](../../../spec/analysis/analysis_engine.md) 中的 `AnalysisResult`，以及统一入口对已承接 op 的当前公开合同；本文件不再独立冻结第二套 `compute/read_bytes/write_bytes` 公式。
- `func_cost` 也不单独冻结自己的支持 op 范围；凡是统一入口当前已承接并可生成 `AnalysisResult` 的场景，本 pass 才能消费；未承接 op 的 `skip + warning` 行为直接继承统一入口，不再额外定义第二套白名单。

## 消费口径

- `func_cost` 必须直接消费 `analysis(func_op, AnalysisConfig, otherargs)` 返回的 `AnalysisResult`。
- `OpCost.compute/read_bytes/write_bytes` 与 `FuncCostSummary.total_compute/total_read_bytes/total_write_bytes` 都只能是 `AnalysisResult` 的 derived alias：
  - `compute` 来自统一入口已产出的计算总量派生口径；
  - `read_bytes` / `write_bytes` 来自统一入口已产出的访存项派生口径。
- 比较结果 `i1` 的 `predicate_size`、`tensor + const` 是否计读、DMA 分支是否纳入统计、未知 op 是否 `skip + warning`，都继承统一入口当前主线行为；本文件不再重写这些规则。
- 若统一入口未来调整 item schema、derived alias 实现或承接范围，`func_cost` 必须跟随该主线更新；不得在本 pass 内保留旧公式分支以维持第二套稳定口径。

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
- 这些字段只承载从统一入口结果投影出的兼容 alias，不在本类中重新定义独立公式。

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

- `total_*` 必须等于 `ops` 中对应字段逐项求和，且与同一 `func.func` 的 `AnalysisResult` derived alias 保持一致。

返回与限制：

- 作为对外可查询分析结果。

### `class AnalyzeFuncCostPass(Pass)`

功能说明：

- 对 module 中每个 `func.func` 执行计算/访存分析。
- 内部消费统一入口 `AnalysisResult`，对外仍暴露 `FuncCostSummary.total_compute/read_bytes/write_bytes` derived alias。

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
- 支持范围、`skip + warning`、`predicate_size` 与 DMA 纳入口径都直接继承统一入口；本 pass 不再维护第二套统计规则。
- `attach_attrs=True` 时，建议附加：
  - `analysis.compute`
  - `analysis.read_bytes`
  - `analysis.write_bytes`
- `attach_attrs=False` 时不得写回 `analysis.*`。

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
- 返回的 `compute/read_bytes/write_bytes` 必须来自统一入口 `AnalysisResult` 的 derived alias，而不是重新走本地公式分支。

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

- 验证 `func_cost` 的 `compute/read_bytes/write_bytes` 来自统一入口 derived alias，而不是本地第二套统计公式。
- 验证 `tensor + const`、`matmul`、DMA 搬运与 compare `i1` 等场景的 alias 结果与统一入口保持一致。
- 验证未知 op 的 `skip + warning` 继承统一入口，不影响其余 op 统计。
- 验证符号维度表达式（如 `A*B`）可正确保留。
- 验证 `attach_attrs` 写回开关只控制属性落盘，不改变 derived alias 的来源。

### 功能与用例清单

| 用例 ID | 场景描述 | 测试文件 | 对应测试 | 状态说明 |
| --- | --- | --- | --- | --- |
| `FC-001` | 输入 `shape=[A,B]` 的 `nn.add`，验证 `func_cost` 读取的符号 `compute` alias 与统一入口一致。 | `test/pass/test_analysis_func_cost.py` | `test_func_cost_nn_add_symbolic_shape` | 已闭环；不额外定义本地公式。 |
| `FC-002` | 输入 `tensor + const`，验证常量不计读流量的 alias 结果继承统一入口。 | `test/pass/test_analysis_func_cost.py` | `test_func_cost_tensor_plus_const` | 已闭环；口径来自统一入口。 |
| `FC-003` | 输入同一 `func` 内串联两个逐元素 op，验证函数总量 alias 为逐 op alias 的累加。 | `test/pass/test_analysis_func_cost.py` | `test_func_cost_chain_accumulate` | 已闭环。 |
| `FC-004` | 输入 `lhs=[M,K], rhs=[K,N]` 的 `nn.matmul`，验证 `func_cost` 对 `matmul` 的 alias 结果与统一入口一致。 | `test/pass/test_analysis_func_cost.py` | `test_func_cost_matmul_formula` | 已闭环；不单独冻结 `matmul` 公式。 |
| `FC-005` | 输入 `dma.copy/load/store`，验证 DMA 读写 alias 结果继承统一入口当前公开分支。 | `test/pass/test_analysis_func_cost.py` | `test_func_cost_dma_memory_traffic` | 已闭环。 |
| `FC-006` | 输入同时含未知 op 与已承接 op 的函数，验证未知 op 的 `skip + warning` 继承统一入口。 | `test/pass/test_analysis_func_cost.py` | `test_func_cost_skips_unknown_op_with_warning` | 已闭环。 |
| `FC-007` | 输入 `attach_attrs=True` 的分析 pass，验证 `func` 回写 `analysis.*` 属性，同时不改变 alias 来源。 | `test/pass/test_analysis_func_cost.py` | `test_func_cost_attach_attrs` | 已闭环。 |
| `FC-008` | 输入 `nn.eq` 输出 `i1`，验证 `write_bytes` alias 优先按 `predicate_size` 继承统一入口。 | `test/pass/test_analysis_func_cost.py` | `test_func_cost_compare_i1_uses_predicate_size` | 已闭环。 |
