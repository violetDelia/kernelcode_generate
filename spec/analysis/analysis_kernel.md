# analysis_kernel

## 功能简介

定义算子级与函数级的“计算量/搬运量”分析规范，用于根据 `Memory` 形状推导运算规模、数据移动规模与统计口径。覆盖逐元素算术、逐元素比较、显式 `broadcast` 与 `matmul`，并提供函数级聚合入口与中间结果物化规则。

## 文档信息

- 创建者：`摸鱼小分队`
- 最后一次更改：`摸鱼小分队`
- `spec`：[`spec/analysis/analysis_kernel.md`](../../spec/analysis/analysis_kernel.md)
- `功能实现`：[`python/analysis/analysis.py`](../../python/analysis/analysis.py)
- `test`：[`test/analysis/test_analysis.py`](../../test/analysis/test_analysis.py)

## 依赖

- [`spec/operation/nn.md`](../../spec/operation/nn.md)：算子语义与 shape 规则。
- [`spec/symbol_variable/memory.md`](../../spec/symbol_variable/memory.md)：`Memory` 结构与 shape 表达。
- [`python/symbol_variable/memory.py`](../../python/symbol_variable/memory.py)：`Memory` 类型实现。
- `sympy`（外部模块）：符号表达式与统计公式构造。

## 目标

- 给出逐元素算术、逐元素比较、显式 `broadcast`、`matmul` 的计算量与读写字节口径。
- 提供函数级聚合入口，区分中间结果是否物化。
- 对形状不匹配、参数非法等情况提供一致的错误边界。

## 限制与边界

- 仅覆盖 `add/sub/mul/truediv/eq/ne/lt/le/gt/ge/broadcast/matmul`；其它算子必须拒绝。
- 逐元素算术/比较不允许隐式广播，输入与输出 `shape` 必须严格一致。
- `broadcast` 仅为显式操作，要求输出 rank 不小于输入 rank，尾维对齐且维度相等或输入维为静态 `1`。
- `matmul` 仅支持二维收缩：`lhs=[M,K]`、`rhs=[K,N]`、`out=[M,N]`。
- 仅提供理论计数口径，不建模缓存复用、分块或硬件执行细节。
- `dtype_size`/`predicate_size` 允许为 `None`，此时以符号 `S`/`P` 表示。
- 形状缺失、规则不满足或参数校验失败必须抛出 `AnalysisError`。

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

- 功能说明：按函数级算子序列聚合统计结果。
- 参数说明：
  - `ops: Sequence[Operation]`：算子序列。
  - `dtype_size: int | None`：传递给逐元素/广播/matmul 的字节大小。
  - `predicate_size: int | None`：传递给比较算子的字节大小。
- 使用示例：`analyze_function([Operation("add", [a, b], c)])`
- 注意事项：
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

## 测试

- 测试文件：[`test/analysis/test_analysis.py`](../../test/analysis/test_analysis.py)
- 执行命令：`pytest -q test/analysis/test_analysis.py`
- 测试目标：
  - 验证逐元素算术/比较计算量与搬运量公式。
  - 验证 `broadcast` 的尾维对齐规则与读写量。
  - 验证 `matmul` 的计算量与读写量公式。
  - 验证函数级聚合在物化与融合场景下的统计差异。
  - 验证参数校验错误（`read_mask` 长度与 `Operation.inputs` 数量）。
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
