# analysis_kernel

## 功能简介

定义兼容公式接口与 `analyze_kernel(...)` facade 的分析规范。长期主线入口已经迁移到 [`analysis_engine.md`](../../spec/analysis/analysis_engine.md) 中的 `analysis(op, config, otherargs=None)`；本文件只保留两类内容：一是基于 `Memory`/`Operation` 的兼容公式 helper，二是 `func.func` 级 facade `analyze_kernel(...)` 及其旧 summary/`value_traffic` 派生口径。当前已承接并在公开范围内的 DMA 分支仍是 `dma.load`、`dma.copy`、`dma.store`；`dma.slice`、`dma.deslice`、`dma.alloc`、`dma.free` 继续不纳入稳定统计合同。

## 文档信息

- 创建者：`摸鱼小分队`
- 最后一次更改：`睡觉小分队`
- `spec`：[`spec/analysis/analysis_kernel.md`](../../spec/analysis/analysis_kernel.md)
- `功能实现`：[`kernel_gen/analysis/analysis.py`](../../kernel_gen/analysis/analysis.py)
- `test`：[`test/analysis/test_analysis.py`](../../test/analysis/test_analysis.py)

## 依赖

- [`spec/operation/nn.md`](../../spec/operation/nn.md)：算子语义与 shape 规则。
- [`spec/dialect/nn.md`](../../spec/dialect/nn.md)：`nn.*` op 与 `nn.memory` 类型约定。
- [`spec/dialect/dma.md`](../../spec/dialect/dma.md)：`dma.*` op 的语义与类型约定。
- [`spec/dialect/kernel.md`](../../spec/dialect/kernel.md)：`kernel.*` op 的语义与类型约定。
- [`spec/symbol_variable/memory.md`](../../spec/symbol_variable/memory.md)：`Memory` 结构与 shape 表达。
- [`kernel_gen/symbol_variable/memory.py`](../../kernel_gen/symbol_variable/memory.py)：`Memory` 类型实现。
- `sympy`（外部模块）：符号表达式与统计公式构造。
- `xdsl`（外部模块）：IR/SSA/类型系统与 dialect 容器。

## 目标

- 给出逐元素算术、逐元素比较、显式 `broadcast`、`matmul` 的兼容公式口径。
- 冻结 `analyze_kernel(func_op: func.FuncOp, ...) -> AnalyzeKernelSummary` 为 `analysis(...)` 的 facade / adapter 与过渡兼容返回，而不是长期主入口或其他 pass 的稳定消费结构。
- 保留基于 `Memory`/`Operation` 的兼容公式接口，供公式复用与兼容场景使用，但不把 `analyze_function(...)` 重新定义为与统一入口并列的主线。
- 对形状不匹配、参数非法等情况提供一致的错误边界。

## 限制与边界

- 基于 `Memory`/`Operation` 的兼容公式接口（包括 `analyze_function(...)` 与各公式 helper）仅覆盖 `add/sub/mul/truediv/eq/ne/lt/le/gt/ge/broadcast/matmul`；在这一路径上传入其它算子必须拒绝。
- `analyze_kernel(...)` 只允许通过 `analysis(func_op, config, otherargs)` 聚合出 `AnalyzeKernelSummary`；不允许再维护第二套独立公式主线。
- `analyze_kernel(...)` 当前只对统一入口已承接的逐元素/`matmul` 成本统计，以及 `dma.load`、`dma.copy`、`dma.store` 的 DMA 分支统计产生结果；`arith.constant` 与 `func.return` 默认忽略。
- 逐元素算术/比较不允许隐式广播，输入与输出 `shape` 必须严格一致。
- `broadcast` 仅为显式操作，要求输出 rank 不小于输入 rank，尾维对齐且维度相等或输入维为静态 `1`。
- `matmul` 仅支持二维收缩：`lhs=[M,K]`、`rhs=[K,N]`、`out=[M,N]`。
- 仅提供理论计数口径，不建模缓存复用、分块或硬件执行细节。
- `dtype_size`/`predicate_size` 允许为 `None`，此时以符号 `S`/`P` 表示。
- 形状缺失、规则不满足或参数校验失败必须抛出 `AnalysisError`。
- `analyze_kernel(...)` 对未知 op 必须执行“skip + warning”，不计入总量；但对已承接公开分支（包括当前 DMA 分支）的前置条件不满足必须抛出 `AnalysisError`。
- 在当前计划与测试未同步前，`dma.slice`、`dma.deslice`、`dma.alloc`、`dma.free` 不纳入 `S1` 已承接公开合同；本规范当前不为这四类 DMA 分支建立测试映射或稳定统计细节。
- `analyze_function(...)` 仅作为基于 `Memory`/`Operation` 的兼容公式接口存在，不与统一入口并列为长期公开主入口。

## 公开接口

**AnalysisError**

- 功能说明：对外公开的分析错误类型。
- 参数说明：
  - `message: str`：错误说明文本（可选，透传至异常信息）。
- 使用示例：`raise AnalysisError("Shape mismatch")`
- 注意事项：用于形状不匹配、算子不支持或参数校验失败时。
- 返回与限制：抛出 `AnalysisError` 即终止分析流程；不返回统计结果。

**OpStats**

- 功能说明：算子级统计结果，包含计算量、读字节与写字节。
- 参数说明：
  - `compute: sympy.Basic`：计算量表达式。
  - `read_bytes: sympy.Basic`：读字节表达式。
  - `write_bytes: sympy.Basic`：写字节表达式。
- 使用示例：`OpStats(sp.Integer(1), sp.Integer(4), sp.Integer(2))`
- 注意事项：仅保存统计表达式，不负责校验或归一化。
- 返回与限制：可用于逐算子结果或总计结果。

**MemoryRef**

- 功能说明：具名 `Memory` 引用，用于函数级统计中的输入/输出标识。
- 参数说明：
  - `name: str`：引用名。
  - `memory: Memory`：绑定的 `Memory` 对象。
- 使用示例：`MemoryRef("A", Memory(["M", "N"], NumericType.Float32))`
- 注意事项：`name` 用于函数级中间结果追踪，需保持一致。
- 返回与限制：仅作为 `Operation` 的输入/输出引用。

**Operation**

- 功能说明：函数级算子描述，包含算子名称、输入/输出与物化策略。
- 参数说明：
  - `op: str`：支持 `add/sub/mul/truediv/eq/ne/lt/le/gt/ge/broadcast/matmul`。
  - `inputs: Sequence[MemoryRef]`：逐元素/比较/matmul 需要 2 个输入，`broadcast` 需要 1 个输入。
  - `output: MemoryRef`：算子输出。
  - `materialize: bool`：是否物化输出，默认 `True`。
- 使用示例：`Operation("add", [lhs_ref, rhs_ref], out_ref, materialize=True)`
- 注意事项：`inputs` 数量与 `op` 不匹配必须抛出 `AnalysisError`。
- 返回与限制：用于 `analyze_function` 的输入序列。

**AnalysisSummary**

- 功能说明：函数级统计聚合结果。
- 参数说明：
  - `ops: Sequence[OpStats]`：按输入顺序的逐算子统计结果。
  - `total: OpStats`：总计结果。
- 使用示例：`AnalysisSummary([stats], stats)`
- 注意事项：`total` 通过逐算子累加得到。
- 返回与限制：用于返回函数级分析结果。

**KernelOpCost**

- 功能说明：`analyze_kernel(...)` 的逐 op 成本结果。
- 参数说明：
  - `op_index: int`：纳入统计的 op 顺序索引（从 `0` 开始）。
  - `op_name: str`：op 名称（`Operation.name`），例如 `nn.add`。
  - `compute: sympy.Basic`：计算量表达式。
  - `read_bytes: sympy.Basic`：读字节表达式。
  - `write_bytes: sympy.Basic`：写字节表达式。
- 使用示例：`KernelOpCost(0, "nn.add", A * B, 2 * A * B * 4, A * B * 4)`
- 注意事项：`op_index` 为统计序列索引；被忽略的 op（如 `arith.constant`、`func.return`）不分配 `op_index`。
- 返回与限制：作为 `AnalyzeKernelSummary.op_costs` 的元素类型。

**ValueTraffic**

- 功能说明：`analyze_kernel(...)` 的单个 SSA value 流量统计结果。
- 参数说明：
  - `value_key: str`：稳定 value 标识（见“额外补充”）。
  - `read_bytes: sympy.Basic`：读字节表达式。
  - `write_bytes: sympy.Basic`：写字节表达式。
- 使用示例：`ValueTraffic("arg0", sp.Integer(0), sp.Integer(16))`
- 注意事项：仅对已注册稳定 `value_key` 的 value 统计；未注册 value 不出现在结果中。
- 返回与限制：作为 `AnalyzeKernelSummary.value_traffic` 的元素类型。

**AnalyzeKernelSummary**

- 功能说明：`analyze_kernel(...)` facade 对统一入口结果的兼容汇总结构。
- 参数说明：
  - `func_name: str`：函数名（`func.func` 的 `sym_name`）。
  - `op_costs: Sequence[KernelOpCost]`：逐 op 成本列表。
  - `value_traffic: Sequence[ValueTraffic]`：逐 value 读写流量列表。
- `total_compute: sympy.Basic`：函数总计算量。
- `total_read_bytes: sympy.Basic`：函数总读取字节。
- `total_write_bytes: sympy.Basic`：函数总写入字节。
- 使用示例：`summary = analyze_kernel(func_op, dtype_size_overrides={"f32": 4}); summary.op_costs[0].op_name == "nn.add"`
- 注意事项：
  - `total_*` 必须等于统一入口 `AnalysisResult` derived alias 的对应总量。
  - `AnalyzeKernelSummary` 仅用于 `analyze_kernel(...)` facade 的兼容返回；`func_cost` 等下游 pass 不得把它视为稳定消费结构。
- 返回与限制：仅作为 `analyze_kernel(...)` 的兼容汇总返回值；不单独冻结新的 pass 消费合同。

**analyze_kernel**

- 功能说明：把 `analysis(func_op, config, otherargs)` 的结果适配为旧 `AnalyzeKernelSummary`。
- 参数说明：
  - `func_op: func.FuncOp`：待分析的函数 op。
  - `args: Iterable[object] | None`：可选运行时参数列表；若提供则必须为 iterable，且长度必须与函数参数位次一致。
  - `predicate_size: int`：比较输出写回字节数（默认 `1`；必须为正整数）。
  - `dtype_size_overrides: dict[str, int] | None`：可选 dtype 字节覆盖表（如 `{"f32": 4}`）。
  - `attach_attrs: bool`：是否将汇总结果写回到 `func.func` 属性中（见“额外补充”）。
- 使用示例：

```python
summary = analyze_kernel(func_op, dtype_size_overrides={"f32": 4})
assert summary.op_costs[0].op_name == "nn.add"
```

- 注意事项：
  - 该接口是 facade / adapter，不再是长期主入口；长期主入口见 [`analysis_engine.md`](../../spec/analysis/analysis_engine.md)。
  - 主入口签名固定为 `analyze_kernel(func_op: func.FuncOp, args: Iterable[object] | None = None, predicate_size: int = 1, dtype_size_overrides: dict[str, int] | None = None, attach_attrs: bool = False) -> AnalyzeKernelSummary`。
  - `func_cost` 若需要 `compute/read_bytes/write_bytes` 兼容字段，必须直接消费统一入口 `AnalysisResult` 的 derived alias，不再经过 `AnalyzeKernelSummary` 建立稳定依赖。
  - 未知 op 必须发出 `UserWarning`，warning 文本需包含 unknown op 信息，并执行 `skip + warning`：不计入 `op_costs`、`total_*` 或对应 `value_traffic`，但分析必须继续完成；当前已承接公开的 `dma.load`、`dma.copy`、`dma.store` 不属于该 warning 分支。
  - 当前公开 DMA 分支中，`dma.load` 作为产生结果 value 的 op，需要把结果写流量登记到对应 `value_traffic`；`dma.copy`、`dma.store` 记录源读/目标写流量。
  - 默认忽略 `arith.constant` 与 `func.return`。
  - 比较输出为 `i1` 时，`KernelOpCost.write_bytes`、对应结果的 `ValueTraffic.write_bytes` 与 `total_write_bytes` 必须统一使用 `predicate_size`，不使用 `dtype_size_overrides["i1"]`。
  - `attach_attrs=False` 时不得写任何新的 `analysis.*`；`attach_attrs=True` 只是显式开启 facade 层的 func attribute 写回。
- 返回与限制：返回 `AnalyzeKernelSummary`；参数/前置条件不满足时抛出 `AnalysisError`。

**analyze_elementwise**

- 功能说明：统计逐元素算术或比较算子的计算量与读写量。
- 参数说明：
  - `lhs: Memory`、`rhs: Memory | int`、`out: Memory`：输入/输出。
  - `dtype_size: int | None`：元素字节大小，`None` 表示符号 `S`。
  - `predicate_size: int | None`：比较结果字节大小，`None` 表示符号 `P`。
  - `op_kind: str`：`"arith"` 或 `"compare"`。
  - `read_mask: Sequence[bool] | None`：当 `rhs` 为 `Memory` 时长度必须为 2；当 `rhs` 为标量时长度必须为 1，仅控制 `lhs` 读取。
  - `write_output: bool`：是否计入输出写回。
- 使用示例：`analyze_elementwise(lhs, rhs, out, op_kind="compare", predicate_size=1)`
- 注意事项：
  - `rhs` 为 `Memory` 时需与 `lhs` 形状一致；`out` 形状必须与 `lhs` 一致。
  - 逐元素算术/比较禁止隐式广播。
- 返回与限制：
  - 计算量为 `product(out.shape)`。
  - 读字节为启用读输入的元素数乘以 `dtype_size`。
  - 写字节：算术用 `dtype_size`，比较用 `predicate_size`。

**analyze_broadcast**

- 功能说明：统计显式 `broadcast` 的读写量。
- 参数说明：
  - `input_mem: Memory`、`output_mem: Memory`：输入/输出。
  - `dtype_size: int | None`：元素字节大小，`None` 表示符号 `S`。
  - `read_mask: Sequence[bool] | None`：长度必须为 1，控制输入读取。
  - `write_output: bool`：是否计入输出写回。
- 使用示例：`analyze_broadcast(inp, out, dtype_size=4)`
- 注意事项：`output_mem.rank >= input_mem.rank`，尾维对齐且维度相等或输入维为静态 `1`。
- 返回与限制：
  - 计算量为 `0`。
  - 读字节为 `product(input_mem.shape) * dtype_size`。
  - 写字节为 `product(output_mem.shape) * dtype_size`。

**analyze_matmul**

- 功能说明：统计 `matmul` 的计算量与读写量。
- 参数说明：
  - `lhs: Memory`、`rhs: Memory`、`out: Memory`：输入/输出。
  - `dtype_size: int | None`：元素字节大小，`None` 表示符号 `S`。
  - `read_mask: Sequence[bool] | None`：长度必须为 2，分别控制 `lhs`/`rhs` 读取。
  - `write_output: bool`：是否计入输出写回。
- 使用示例：`analyze_matmul(lhs, rhs, out, dtype_size=2)`
- 注意事项：仅支持二维收缩，输入/输出形状需满足 `lhs=[M,K]`、`rhs=[K,N]`、`out=[M,N]`。
- 返回与限制：
  - 计算量为 `2*M*N*K`。
  - 读字节为 `(M*K + K*N) * dtype_size`。
  - 写字节为 `M*N * dtype_size`。

**analyze_function**

- 功能说明：按函数级算子序列聚合统计结果的兼容公式接口，不是与 `analyze_kernel(...)` 并列的长期主入口。
- 参数说明：
  - `ops: Sequence[Operation]`：算子序列。
  - `dtype_size: int | None`：传递给逐元素/广播/matmul 的字节大小。
  - `predicate_size: int | None`：传递给比较算子的字节大小。
- 使用示例：`analyze_function([Operation("add", [a, b], c)])`
- 注意事项：
  - 面向 `func.func` 的公开主入口仍是 `analyze_kernel(...)`；`analyze_function(...)` 仅用于 `Memory`/`Operation` 级公式复用与兼容场景。
  - `Operation.materialize=False` 的输出不计写回，且后续读取自动置为不计读。
  - `Operation.inputs` 数量与算子类型不匹配必须抛出 `AnalysisError`。
  - 不支持的 `op` 必须抛出 `AnalysisError`。
- 返回与限制：返回 `AnalysisSummary`，`total` 为逐算子累加结果。

**analyze_add**

- 功能说明：逐元素算术统计的便捷入口。
- 参数说明：
  - `lhs: Memory`、`rhs: Memory`、`out: Memory`：输入/输出。
  - `dtype_size: int | None`：元素字节大小，`None` 表示符号 `S`。
- 使用示例：`analyze_add(lhs, rhs, out, dtype_size=4)`
- 注意事项：形状必须严格一致，不允许隐式广播。
- 返回与限制：返回 `OpStats`；内部调用 `analyze_elementwise`。

**analyze_eq**

- 功能说明：逐元素比较统计的便捷入口。
- 参数说明：
  - `lhs: Memory`、`rhs: Memory`、`out: Memory`：输入/输出。
  - `dtype_size: int | None`：输入元素字节大小，`None` 表示符号 `S`。
  - `predicate_size: int | None`：比较结果字节大小，`None` 表示符号 `P`。
- 使用示例：`analyze_eq(lhs, rhs, out, predicate_size=1)`
- 注意事项：形状必须严格一致，不允许隐式广播。
- 返回与限制：返回 `OpStats`；内部调用 `analyze_elementwise`（`op_kind="compare"`）。

**analyze_broadcast_op**

- 功能说明：显式 `broadcast` 统计的便捷入口。
- 参数说明：
  - `input_mem: Memory`、`output_mem: Memory`：输入/输出。
  - `dtype_size: int | None`：元素字节大小，`None` 表示符号 `S`。
- 使用示例：`analyze_broadcast_op(inp, out, dtype_size=4)`
- 注意事项：要求尾维对齐，输入维度为 1 或与输出维度相等。
- 返回与限制：返回 `OpStats`；内部调用 `analyze_broadcast`。

**analyze_matmul_op**

- 功能说明：`matmul` 统计的便捷入口。
- 参数说明：
  - `lhs: Memory`、`rhs: Memory`、`out: Memory`：输入/输出。
  - `dtype_size: int | None`：元素字节大小，`None` 表示符号 `S`。
- 使用示例：`analyze_matmul_op(lhs, rhs, out, dtype_size=2)`
- 注意事项：仅支持二维收缩，输入/输出形状需满足 `lhs=[M,K]`、`rhs=[K,N]`、`out=[M,N]`。
- 返回与限制：返回 `OpStats`；内部调用 `analyze_matmul`。

## 额外补充

- **统计口径**：计算量以“元素级操作数”计数；逐元素算术/比较为每元素 1 次操作，`matmul` 为每输出元素 2 次操作（乘+加）。
- **搬运量口径**：读/写字节 = 参与读写的元素数 × 字节大小；`dtype_size`/`predicate_size` 为 `None` 时以符号 `S`/`P` 表示。
- **形状与符号推导**：`Memory.shape` 支持符号维度，元素个数以乘积表达式表示；形状缺失或不满足规则必须失败。
- **中间结果计入口径**：物化中间结果计一次写回并在后续消费时计读；未物化中间结果不计写回且不计后续读。
- **语义对齐**：逐元素/`broadcast`/`matmul` 形状规则与 `spec/operation/nn.md` 对齐，本规范仅定义统计口径。
- **主入口与兼容接口**：`analyze_kernel(...)` 是当前唯一公开主入口；`analyze_function(...)` 仅保留为基于 `Memory`/`Operation` 的兼容公式接口，不与前者并列为长期主入口。
- **稳定 value_key**：`value_traffic` 使用稳定 key：函数参数为 `arg{index}`，op 结果为 `op{op_index}.result{result_index}`。
- **未知 op 告警**：未知 op 必须 `skip + warning`（`UserWarning`），消息格式为 `analysis_kernel skip <op.name>: <reason>`，warning 中必须包含 unknown op 信息；跳过该 op 后分析继续完成，不中止整个 `func.func`。当前已承接公开的 `dma.load`、`dma.copy`、`dma.store` 不属于该分支。
- **compare i1 统计口径**：当比较结果 element type 为 `i1` 时，写回字节统一按 `predicate_size` 计入；`dtype_size_overrides["i1"]` 不能覆盖该口径。
- **属性回写**：当 `attach_attrs=True` 时，需写回 `analysis.compute`、`analysis.read_bytes`、`analysis.write_bytes` 到 `func.func` attributes（字符串化表达式）。

## 测试

- 测试文件：[`test/analysis/test_analysis.py`](../../test/analysis/test_analysis.py)
- 执行命令：`pytest -q test/analysis/test_analysis.py`
- 测试目标：
  - 验证逐元素算术/比较计算量与搬运量公式。
  - 验证 `broadcast` 的尾维对齐规则与读写量。
  - 验证 `matmul` 的计算量与读写量公式。
  - 验证函数级聚合在物化与融合场景下的统计差异。
  - 验证参数校验错误（`read_mask` 长度与 `Operation.inputs` 数量）。
  - 验证 `analyze_kernel(...)` 逐 op 统计、总量统计与 `value_traffic` 稳定 key。
  - 验证未知 op `skip + warning` 口径与 compare `i1` 写回 `predicate_size` 优先级；其中 unknown-op 的机械验收测试名统一为 `test_analyze_kernel_unknown_op_warns_and_skips`。
  - 验证当前 DMA 的公开机械验收示例仍以 `AK-005` 的 `dma.load` 用例为准；在计划与测试同步前，不为 `dma.slice`、`dma.deslice`、`dma.alloc`、`dma.free` 新增公开测试映射。
  - 验证 `analyze_kernel(...)` 的入参校验（`func_op` 类型、`args` 可迭代性与长度一致性）。
- 功能与用例清单：

| 用例 ID | 功能 | 场景 | 前置条件 | 操作 | 预期结果 | 建议测试 |
| --- | --- | --- | --- | --- | --- | --- |
| AN-001 | 逐元素算术 | add 统计 | `shape=[A,B]` | `add(A1, A2)` | 计算量 `A*B`，读 `2AB*S`，写 `AB*S` | `test_analysis_add_counts` |
| AN-002 | 逐元素比较 | eq 统计 | `shape=[A,B]` | `eq(A1, A2)` | 计算量 `A*B`，读 `2AB*S`，写 `AB*P` | `test_analysis_eq_counts` |
| AN-003 | broadcast | 扩张统计 | `input.shape=[1,N]`, `out.shape=[M,N]` | `broadcast(input, out)` | 读 `1*N*S`，写 `M*N*S` | `test_analysis_broadcast_counts` |
| AN-004 | matmul | 统计公式 | `lhs=[M,K]`, `rhs=[K,N]` | `matmul(lhs, rhs)` | 计算量 `2*M*N*K`，读 `(M*K+K*N)*S`，写 `M*N*S` | `test_analysis_matmul_counts` |
| AN-005 | 函数聚合 | 中间物化 | `C=add(A1,A2)` | `mul(C,A3)` | 计入 `C` 的读/写 | `test_analysis_materialized_intermediate` |
| AN-006 | 函数聚合 | 融合 | `mul(add(A1,A2),A3)` | 视为融合 | 不计 `C` 的读/写 | `test_analysis_fused_intermediate` |
| AN-007 | 参数校验 | read_mask 长度 | 逐元素/广播/matmul 传入错误长度 | 调用统计入口 | 抛 `AnalysisError` | `test_analysis_read_mask_length_mismatch` |
| AN-008 | 参数校验 | Operation.inputs 数量 | `Operation` 输入数量不匹配 | `analyze_function` | 抛 `AnalysisError` | `test_analysis_function_inputs_mismatch` |
| AK-001 | analyze_kernel | nn.add 符号 shape | `func.func` 参数为 `nn.memory` | `analyze_kernel(func_op)` | compute/read/write 与 `op_costs[0].op_name` 满足约定 | `test_analyze_kernel_nn_add_symbolic_shape` |
| AK-002 | analyze_kernel | tensor + const | rhs 为 `arith.constant` | `analyze_kernel(func_op)` | 常量不计读流量；`value_traffic` key 覆盖 `arg0/op0.result0` | `test_analyze_kernel_tensor_plus_const` |
| AK-003 | value_traffic | chain 读写归属 | 串联两次逐元素 op | `analyze_kernel(func_op)` | 中间结果 `op0.result0` 的 `read_bytes/write_bytes` 与链式中间值流量统计可机械判断一致 | `test_analyze_kernel_chain_value_traffic` |
| AK-004 | analyze_kernel | matmul 公式 | `lhs=[M,K]`、`rhs=[K,N]` | `analyze_kernel(func_op)` | compute/read/write 满足 `2*M*N*K` 等公式 | `test_analyze_kernel_matmul_formula` |
| AK-005 | analyze_kernel | dma.load 流量 | `dma.load` 参与链路 | `analyze_kernel(func_op)` | `value_traffic` 记录源与结果的读写流量 | `test_analyze_kernel_dma_load_tracks_source_and_result` |
| AK-006 | 参数校验 | func_op 类型 | 输入非 `func.FuncOp` | `analyze_kernel(non_func)` | 抛 `AnalysisError` | `test_analyze_kernel_rejects_non_func_input` |
| AK-007 | 参数校验 | args 可迭代性 | `args=object()` | `analyze_kernel(func_op, args=...)` | 抛 `AnalysisError` | `test_analyze_kernel_rejects_non_iterable_args` |
| AK-008 | 参数校验 | args 长度一致性 | `len(args) != len(func.args)` | `analyze_kernel(func_op, args=...)` | 抛 `AnalysisError` | `test_analyze_kernel_rejects_args_length_mismatch` |
| AK-009 | unknown op | skip + warning | 含未知 op | `analyze_kernel(func_op)` | 产生包含 unknown op 信息的 warning，未知 op 不计入 `op_costs`，且分析继续完成 | `test_analyze_kernel_unknown_op_warns_and_skips` |
| AK-010 | predicate_size | compare i1 | 输出 element type 为 `i1` | `analyze_kernel(..., predicate_size=2)` | `i1` 结果写回与总写流量按 `predicate_size` 计入 | `test_analyze_kernel_compare_i1_uses_predicate_size` |
