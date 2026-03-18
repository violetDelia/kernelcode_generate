# 分析.md

## 功能简介

定义算子级与函数级的“计算量/搬运量”分析规范，用于根据函数签名与 `Memory` 形状推导运算规模、数据移动规模与统计口径。本规范覆盖逐元素算术、逐元素比较、显式 `broadcast` 与 `matmul`，并明确输入/输出/中间结果的计入规则。

## 文档信息

- 创建者：`摸鱼小分队`
- 最后一次更改：`摸鱼小分队`
- `spec`：[`spec/analysis/分析.md`](../../spec/analysis/分析.md)
- `关联语义`：[`spec/operation/nn.md`](../../spec/operation/nn.md)
- `关联类型`：[`spec/symbol_variable/memory.md`](../../spec/symbol_variable/memory.md)
- `test`：[`test/analysis/test_analysis.py`](../../test/analysis/test_analysis.py)
- `功能实现`：[`python/analysis/analysis.py`](../../python/analysis/analysis.py)

## 依赖

- `python.symbol_variable.memory.Memory`：作为输入/输出形状与 dtype 的载体。
- `spec/operation/nn.md`：算子语义与 shape 规则的来源。
- `sympy`：用于符号化计数表达式。

## 分层关系

- `spec/operation/nn.md` 定义算子语义、shape/dtype/space 规则与错误边界。
- 本规范只定义“规模估计”的统计口径，不改变算子语义。
- 本层不涉及方言或 IR 细节；若后续新增 IR 层分析入口，应在该层保持一致的计数口径。

## 限制与边界

- 本规范仅覆盖逐元素算术、逐元素比较、显式 `broadcast` 与 `matmul`。
- 不负责真实调度、缓存复用、分块优化或硬件层面模型。
- `dtype_size`/`predicate_size` 由调用方提供字节大小；未提供时以符号占位表达。
- 形状不满足算子约束时必须失败，不进行隐式修正或广播推断。

## 公开接口

### 数据结构

#### `AnalysisError`

功能说明：

- 分析模块对外公开的错误类型，用于报告形状不满足规则、算子不受支持或参数校验失败。

约束：

- 当输入形状、算子或参数不满足本规范约束时，分析入口必须抛出 `AnalysisError`。

#### `MemoryRef`

功能说明：

- 具名 Memory 引用，用于函数级算子输入/输出描述。

字段约束：

- `name: str`：用于在函数级统计中标识中间结果或输入。
- `memory: Memory`：绑定的 `Memory` 对象。

使用示例：

```python
from python.analysis.analysis import MemoryRef
from python.symbol_variable.memory import Memory
from python.symbol_variable.type import NumericType

ref = MemoryRef("A", Memory(["M", "N"], NumericType.Float32))
```

#### `Operation`

功能说明：

- 函数级算子描述，记录算子类型、输入/输出与物化策略。

字段约束：

- `op: str`：算子名称，仅支持 `add/sub/mul/truediv/eq/ne/lt/le/gt/ge/broadcast/matmul`。
- `inputs: Sequence[MemoryRef]`：
  - 逐元素算术/比较与 `matmul` 需要 2 个输入；
  - `broadcast` 需要 1 个输入。
- `output: MemoryRef`：该算子的输出。
- `materialize: bool`：是否将该算子输出物化为可被后续读取的结果。
  - `True` 表示输出写入并可被后续读取。
  - `False` 表示输出作为融合中间结果，不计入写回与后续读回。

校验约束：

- `inputs` 数量与 `op` 不匹配时必须抛出 `AnalysisError`。

使用示例：

```python
from python.analysis.analysis import MemoryRef, Operation
from python.symbol_variable.memory import Memory
from python.symbol_variable.type import NumericType

lhs = MemoryRef("A", Memory(["M", "N"], NumericType.Float32))
rhs = MemoryRef("B", Memory(["M", "N"], NumericType.Float32))
out = MemoryRef("C", Memory(["M", "N"], NumericType.Float32))

op = Operation("add", [lhs, rhs], out, materialize=True)
```

#### `OpStats`

功能说明：

- 算子级统计结果，保存计算量、读字节与写字节表达式。

字段约束：

- `compute: sympy.Basic`
- `read_bytes: sympy.Basic`
- `write_bytes: sympy.Basic`

#### `AnalysisSummary`

功能说明：

- 函数级统计聚合结果。

字段约束：

- `ops: Sequence[OpStats]`：按输入算子顺序的统计结果。
- `total: OpStats`：总计结果。

### 统计入口

#### `analyze_elementwise`

功能说明：

- 统计逐元素算术或比较算子的计算量与搬运量。

参数约束：

- `dtype_size: int | None`：元素字节大小；`None` 以符号 `S` 表示。
- `predicate_size: int | None`：比较结果字节大小；`None` 以符号 `P` 表示。
- `read_mask: Sequence[bool] | None`：控制输入读计数。
  - 当 `rhs` 为 `Memory`：长度必须为 2。
  - 当 `rhs` 为标量：长度必须为 1，仅控制 `lhs`。
- `write_output: bool`：是否计入输出写回；`False` 时写字节为 0。

校验约束：

- `read_mask` 长度不满足约束时必须抛出 `AnalysisError`。

#### `analyze_broadcast`

功能说明：

- 统计显式 `broadcast` 的读写量。

参数约束：

- `dtype_size: int | None`：元素字节大小；`None` 以符号 `S` 表示。
- `read_mask: Sequence[bool] | None`：长度必须为 1，用于控制输入读。
- `write_output: bool`：是否计入输出写回；`False` 时写字节为 0。

校验约束：

- `read_mask` 长度不为 1 时必须抛出 `AnalysisError`。

#### `analyze_matmul`

功能说明：

- 统计 `matmul` 的计算量与读写量。

参数约束：

- `dtype_size: int | None`：元素字节大小；`None` 以符号 `S` 表示。
- `read_mask: Sequence[bool] | None`：长度必须为 2，分别控制 lhs/rhs 读。
- `write_output: bool`：是否计入输出写回；`False` 时写字节为 0。

校验约束：

- `read_mask` 长度不为 2 时必须抛出 `AnalysisError`。

#### `analyze_function`

功能说明：

- 按函数级算子序列聚合统计结果。

参数约束：

- `dtype_size: int | None`：传递给逐元素与 `matmul` 的字节大小。
- `predicate_size: int | None`：传递给比较算子的字节大小。

行为约束：

- `Operation.materialize` 控制输出是否计入写回。
- 若输入来自未物化的中间结果（`materialize=False`），该输入读不计入搬运量。
  - 在实现中体现为自动生成 `read_mask` 并传递给各算子统计入口。
- `Operation.inputs` 数量不匹配或算子不支持时必须抛出 `AnalysisError`。

#### 便捷入口

功能说明：

- 提供常用算子的简化入口，参数语义与对应的统计入口一致。

接口：

- `analyze_add(lhs, rhs, out, *, dtype_size=None)`
- `analyze_eq(lhs, rhs, out, *, dtype_size=None, predicate_size=None)`
- `analyze_broadcast_op(input_mem, output_mem, *, dtype_size=None)`
- `analyze_matmul_op(lhs, rhs, out, *, dtype_size=None)`

## 统计口径

### 统计单位

- 计算量：以“算子级操作数”计数。
  - 算术类（`add/sub/mul/truediv`）：每元素 1 次算术操作。
  - 比较类（`eq/ne/lt/le/gt/ge`）：每元素 1 次比较操作。
  - `matmul`：每个输出元素 1 次乘 + 1 次加，计作 2 次操作。
- 搬运量：以“字节”计数。
  - 输入读字节：`input_element_count * dtype_size`。
  - 输出写字节：`output_element_count * dtype_size`。
  - `dtype_size` 由实现或调用方提供；若未知，以符号 `S` 表示。

### 算子粒度

- 以 `operation/nn` 的算子实例为统计粒度。
- 链式表达式按显式算子拆分；每个算子独立统计。
- 统计对象包含：输入读、输出写、计算量。

### 输入/输出/中间结果计入口径

- 输入：对每个算子读取的 `Memory` 计入一次读流量。
- 输出：对每个算子写入的 `Memory` 计入一次写流量。
- 中间结果：
  - 若中间结果显式具名、被物化为 `Memory`，则视为输出写，并在后续消费时作为输入读。
  - 若为融合表达式且不落地（仅逻辑组合），则不计入额外写回，只按最终输出计写。

## 形状与符号推导

- `Memory` 形状可含符号维度，如 `Memory(A, B)`。
- 元素个数以符号乘积表示，例如 `count(A,B)=A*B`。
- 若无法确定形状（缺失维度或不满足算子 shape 规则），分析必须失败并返回错误。

## 算子规则

### 逐元素算术

适用算子：`add/sub/mul/truediv`。

约束：

- 输入/输出 `shape` 必须严格一致。
- 不支持隐式广播。

统计：

- 元素数 `N = product(shape)`。
- 计算量：`N`。
- 搬运量：
  - 读：`2 * N * dtype_size`（双输入）或 `N * dtype_size`（与标量）。
  - 写：`N * dtype_size`。

### 逐元素比较

适用算子：`eq/ne/lt/le/gt/ge`。

约束：

- 输入/输出 `shape` 必须严格一致。

统计：

- 元素数 `N = product(shape)`。
- 计算量：`N`（比较操作）。
- 搬运量：
  - 读：`2 * N * dtype_size`（按输入 dtype）。
  - 写：`N * predicate_size`（默认与输出 dtype 对应）。

### `broadcast`

约束：

- `output.rank >= input.rank`。
- 尾维对齐；对齐维度满足“相等或 input 维为静态 1”。
- `broadcast` 为显式操作；不改变逐元素算术/比较的“禁隐式广播”规则。

统计：

- 输入元素数 `N_in = product(input.shape)`。
- 输出元素数 `N_out = product(output.shape)`。
- 计算量：`0`（纯数据扩张/复制语义）。
- 搬运量：
  - 读：`N_in * dtype_size`。
  - 写：`N_out * dtype_size`。

说明：若实现以视图共享或零拷贝方式表达广播，可在实现层标注“写回量为 0”的优化路径，但本规范的基线统计以物化输出为准。

### `matmul`

约束：

- `lhs.rank == 2` 且 `rhs.rank == 2`。
- `lhs.shape = [M, K]`，`rhs.shape = [K, N]`。
- 输出 `shape = [M, N]`。

统计：

- 计算量：`2 * M * N * K`。
- 搬运量：
  - 读：`(M * K + K * N) * dtype_size`。
  - 写：`M * N * dtype_size`。

说明：本规范不建模缓存复用或分块优化，计数为“理论最小读写路径”。

## 函数级分析

### 输入形式

- 函数签名示例：

```text
func(Memory(A, B) A1, Memory(A, B) A2, Memory(A, B) A3) -> Memory(A, B)
```

- 函数体由 `operation/nn` 的算子序列组成。
- 分析在函数级聚合各算子统计结果。

### 聚合规则

- 总计算量 = 所有算子计算量之和。
- 总搬运量 = 所有算子读写字节之和。
- 中间结果若显式物化，需计入写与后续读。

### 示例

```text
C = add(A1, A2)          # N = A*B
D = mul(C, A3)           # N = A*B

计算量 = N + N = 2AB
读写量 = (A1+A2+C) + (C+A3+D)
```

其中：

- 若 `C` 物化，写出一次并被读取一次。
- 若 `add` 与 `mul` 可融合且不落地 `C`，则不计 `C` 的写回与读回，仅计最终输出 `D` 的写回。

## 错误边界

- 输入 `Memory` 的 `shape` 缺失或不满足算子规则时，分析必须失败。
- `dtype_size` 未提供时，输出应保留符号 `S`，并标明“单位为元素字节大小的线性表达式”。
- 本规范不处理 `space` 不一致、非法 `stride` 或越界索引，调用方需保证输入合法。

## 测试

- 测试文件：[`test/analysis/test_analysis.py`](../../test/analysis/test_analysis.py)
- 测试命令：`pytest -q test/analysis/test_analysis.py`

### 测试目标

- 验证逐元素算术/比较的计算量与搬运量公式。
- 验证 `broadcast` 的读写量与尾维对齐规则。
- 验证 `matmul` 的计算量与读写量公式。
- 验证函数级聚合在有无中间物化时的计数差异。

### 测试清单

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

## 语义对齐

- 逐元素算术/比较与 `spec/operation/nn.md` 保持一致：禁止隐式广播，要求 shape 严格一致。
- `broadcast` 的尾维对齐规则与 `operation/nn.broadcast` 一致。
- `matmul` 的二维收缩规则与 `operation/nn.matmul` 一致；仅定义分析口径，不影响实现状态。
