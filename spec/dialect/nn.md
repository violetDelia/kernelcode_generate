# nn.md

聚焦 [`python/dialect/nn.py`](../../python/dialect/nn.py) 的设计语义，说明 `nn dialect` 的类型系统、space 建模、当前已实现二元 op verifier、parse/print round-trip 与文本装配约束。本文档只描述方言层的稳定接口与校验规则，不包含过程性迁移描述。

## 文档信息

- 创建者：`规格小队`
- 最后一次更改：`朽木露琪亚`
- `spec`：[`spec/dialect/nn.md`](../../spec/dialect/nn.md)
- `上游语义`：[`spec/operation/nn.md`](../../spec/operation/nn.md)
- `关联类型`：[`spec/symbol_variable/memory.md`](../../spec/symbol_variable/memory.md)
- `test`：[`test/dialect/test_nn_dialect.py`](../../test/dialect/test_nn_dialect.py)
- `功能实现`：[`python/dialect/nn.py`](../../python/dialect/nn.py)

## 范围与目标

- 聚焦 `python/dialect/nn.py` 中 `nn` dialect 的稳定公开接口。
- 明确 `space` attribute、`memory` type 以及二元 op 的 verifier 语义。
- 约束 parse/print round-trip、space mismatch、compare result type 等当前方言层行为，并记录 `nn.matmul`/`nn.broadcast` 的待补方言约束。
- 不重复定义 `Memory` 上游逐元素语义；上游运算语义以 [`spec/operation/nn.md`](../../spec/operation/nn.md) 为准。

## 分层关系

- 上游 `spec/operation/nn.md` 负责高层算子语义与 API 约束，`nn dialect` 只定义 IR 层字段与 verifier。
- 当前 `main` 上的 [`python/dialect/nn.py`](../../python/dialect/nn.py) 尚未实现 `nn.matmul`/`nn.broadcast`；若后续引入，这些 op 必须作为上游 `operation/nn` 对应算子的方言层落地载体，并与 [`spec/operation/nn.md`](../../spec/operation/nn.md) 保持一致。

## 核心组成

`nn dialect` 当前由以下公开构件组成：

- `NnMemorySpaceAttr`：显式建模 `global/shared/local/tsm/tlm` 五种空间。
- `NnMemoryType`：建模 `shape`、`stride`、`element_type`、`space` 四元组。
- 二元算术 op：
  - `nn.add`
  - `nn.sub`
  - `nn.mul`
  - `nn.truediv`
- 二元比较 op：
  - `nn.eq`
  - `nn.ne`
  - `nn.lt`
  - `nn.le`
  - `nn.gt`
  - `nn.ge`

待补构件（当前 `main` 未实现、未测试）：

- 矩阵乘 op：
  - `nn.matmul`
- 广播 op：
  - `nn.broadcast`

## Space 建模

- `NnMemorySpaceAttr` 当前显式建模 `global/shared/local/tsm/tlm` 五个 memory space。
- `space` 只能取上述五者之一，不得接受未声明的值。
- `NnMemoryType.space` 与 op attribute `space` 必须保持同一语义口径。
- `tsm/tlm` 在当前方言层与 `global/shared/local` 一样只作为合法空间枚举值参与 parse/print 与 verifier；当前不会因为空间名称不同而引入额外的特判 verifier 分支。
- 未来若新增空间值，必须同步更新本 spec、实现 verifier 和测试清单。

### `NnMemorySpaceAttr`

功能说明：

- 表示 `nn` dialect 中的 memory space attribute。
- 是 `NnMemoryType` 和各 `nn` op `space` attribute 的唯一合法空间表示。

合法取值：

- `#nn.space<global>`
- `#nn.space<shared>`
- `#nn.space<local>`
- `#nn.space<tsm>`
- `#nn.space<tlm>`
使用示例：

```python
space = NnMemorySpaceAttr.from_name("tsm")
```

预期行为：

- 仅允许 `global/shared/local/tsm/tlm`
- 非法值在 verifier 阶段触发错误

## Memory Type 建模

### `NnMemoryType`

功能说明：

- 建模 `shape`、`stride`、`element_type` 与 `space` 四类信息。
- 是所有 `nn` 二元 op 的 operand/result 类型基础。

字段约束：

- `shape`：`ArrayAttr[Attribute]`
- `stride`：`ArrayAttr[Attribute]`
- `element_type`：任意合法 xDSL 元素类型 attribute
- `space`：`NnMemorySpaceAttr`

类型约束：

- `shape` 与 `stride` 的 rank 必须一致。
- `shape` 与 `stride` 的每一维支持静态整数、符号或 `?`。
- `shape` 中的 `?` 表示动态维度。
- `stride` 中的 `?` 不允许与同位置 `shape` 中的 `?` 直接成对出现；若 `stride` 为 `?`，同位置 `shape` 必须是符号或静态整数。
- `space` 必须是 `#nn.space<...>` 形式的 `NnMemorySpaceAttr`。

使用示例：

```python
shape = ArrayAttr([IntAttr(4), IntAttr(8)])
stride = ArrayAttr([IntAttr(8), IntAttr(1)])
element_type = IntegerType(32)
space = NnMemorySpaceAttr.from_name("tlm")
mem_ty = NnMemoryType(shape, stride, element_type, space)
```

预期行为：

- `shape` 与 `stride` rank 必须一致
- `space` 必须为 `global/shared/local/tsm/tlm`
- 缺失任一字段时 parse 失败
- 违反约束时 verifier 报错

## 二元 Op 共性约束

`nn.add/sub/mul/truediv/eq/ne/lt/le/gt/ge` 共用同一套二元 verifier 框架。

### 输入约束

- `lhs` 必须为 `NnMemoryType`
- `rhs` 必须为 `NnMemoryType`
- `result` 必须为 `NnMemoryType`
- `lhs.space == rhs.space`
- `lhs.space == op.space`
- `result.space == op.space`
- `lhs.shape == rhs.shape == result.shape`
- `lhs.stride == rhs.stride == result.stride`
- `lhs.element_type == rhs.element_type`

### 输出约束

- 算术 op：`result.element_type == lhs.element_type`
- 比较 op：`result.element_type == i1`

### 错误约束

- operand/result 不是 `NnMemoryType`：verifier 报错
- operand space 不一致：verifier 报错
- op attribute `space` 与 operand/result type space 不一致：verifier 报错
- `shape` 或 `stride` 不一致：verifier 报错
- operand `element_type` 不一致：verifier 报错
- 比较 op 结果类型不是 `i1`：verifier 报错

## Op 定义

### `nn.add`

功能说明：

- 表示逐元素加法。

输入：

- `lhs: !nn.memory<...>`
- `rhs: !nn.memory<...>`
- `space: #nn.space<...>`

输出：

- `result: !nn.memory<...>`

结果约束：

- `result.element_type` 必须与 operand `element_type` 一致。

使用示例：

```python
op = NnAddOp(lhs, rhs, result_type, NnMemorySpaceAttr.from_name("global"))
```

### `nn.sub`

功能说明：

- 表示逐元素减法。

输入与输出约束：

- 与 `nn.add` 相同。

使用示例：

```python
op = NnSubOp(lhs, rhs, result_type, NnMemorySpaceAttr.from_name("global"))
```

### `nn.mul`

功能说明：

- 表示逐元素乘法。

输入与输出约束：

- 与 `nn.add` 相同。

使用示例：

```python
op = NnMulOp(lhs, rhs, result_type, NnMemorySpaceAttr.from_name("global"))
```

### `nn.truediv`

功能说明：

- 表示逐元素真除法。

输入与输出约束：

- 与 `nn.add` 相同。

使用示例：

```python
op = NnTrueDivOp(lhs, rhs, result_type, NnMemorySpaceAttr.from_name("global"))
```

### `nn.eq`

功能说明：

- 表示逐元素相等比较。

结果约束：

- `result.element_type` 固定为 `i1`。

使用示例：

```python
op = NnEqOp(lhs, rhs, result_type, NnMemorySpaceAttr.from_name("global"))
```

### `nn.ne`

功能说明：

- 表示逐元素不等比较。

结果约束：

- `result.element_type` 固定为 `i1`。

使用示例：

```python
op = NnNeOp(lhs, rhs, result_type, NnMemorySpaceAttr.from_name("global"))
```

### `nn.lt`

功能说明：

- 表示逐元素小于比较。

结果约束：

- `result.element_type` 固定为 `i1`。

使用示例：

```python
op = NnLtOp(lhs, rhs, result_type, NnMemorySpaceAttr.from_name("global"))
```

### `nn.le`

功能说明：

- 表示逐元素小于等于比较。

结果约束：

- `result.element_type` 固定为 `i1`。

使用示例：

```python
op = NnLeOp(lhs, rhs, result_type, NnMemorySpaceAttr.from_name("global"))
```

### `nn.gt`

功能说明：

- 表示逐元素大于比较。

结果约束：

- `result.element_type` 固定为 `i1`。

使用示例：

```python
op = NnGtOp(lhs, rhs, result_type, NnMemorySpaceAttr.from_name("global"))
```

### `nn.ge`

功能说明：

- 表示逐元素大于等于比较。

结果约束：

- `result.element_type` 固定为 `i1`。

使用示例：

```python
op = NnGeOp(lhs, rhs, result_type, NnMemorySpaceAttr.from_name("global"))
```

## Parse/Print 约束

- 任意合法 `!nn.memory<...>` 文本都必须支持 parse 后再 print 回稳定文本。
- 任意合法 `#nn.space<...>` 文本都必须支持 parse 后再 print 回稳定文本。
- 包含当前已实现 `nn.add/sub/mul/truediv/eq/ne/lt/le/gt/ge` 的合法模块文本必须支持 parse 后再 print 回稳定文本。
- `nn.memory` 缺少字段时必须在 parse 阶段失败。
- 当前 `main` 尚未提供 `nn.matmul` 的 parse/print round-trip；对应文本约束需在该 op 落地时与实现/测试一并补齐。
- 当前 `main` 尚未提供 `nn.broadcast` 的 parse/print round-trip；对应文本约束需在该 op 落地时与实现/测试一并补齐。

## 文本装配与 Verifier 约束

- 文本 assembly 中，如果两个 operand 的 `space` 不一致，必须在 verify 阶段失败。
- 文本 assembly 中，如果 op attribute `space` 与 operand/result type `space` 不一致，必须在 verify 阶段失败。
- 比较 op 的结果 type 若不是 `i1`，必须在 verify 阶段失败。

## `nn.matmul` 待补方言规范

功能说明：

- `nn.matmul` 是上游 [`spec/operation/nn.md`](../../spec/operation/nn.md) 中 `operation/nn.matmul` 的目标方言层承载 op。
- 当前 `main` 上的 [`python/dialect/nn.py`](../../python/dialect/nn.py) 与 [`test/dialect/test_nn_dialect.py`](../../test/dialect/test_nn_dialect.py) 尚未提供 `NnMatmulOp` 与对应测试；本节定义后续补齐实现/测试时必须满足的契约。

目标输入：

- `lhs: !nn.memory<...>`
- `rhs: !nn.memory<...>`
- `space: #nn.space<...>`

目标输出：

- `result: !nn.memory<...>`

目标 verifier 约束：

- `lhs`、`rhs`、`result` 必须为 `NnMemoryType`。
- `lhs.shape`、`rhs.shape`、`result.shape` 必须为 rank=2。
- `lhs.shape[1]` 必须与 `rhs.shape[0]` 语义一致。
- `result.shape[0] == lhs.shape[0]`，`result.shape[1] == rhs.shape[1]`。
- `lhs.element_type == rhs.element_type == result.element_type`。
- `lhs.space == rhs.space == result.space == op.space`。
- `stride` 的 verifier 规则不得复用逐元素 op 的“三侧完全相等”约束；结果 `stride` 应按 `matmul` 结果类型单独校验，不得要求简单等同 `lhs/rhs` 任一输入。

目标 parse/print 约束：

- 合法 `nn.matmul` 模块文本必须支持 parse 后再 print 回稳定文本。
- 非法 shape/rank/space 组合必须在 verifier 阶段报错，而不是静默接受。

目标示例（目标 op 形态，当前 `main` 尚未实现）：

```python
op = NnMatmulOp(lhs, rhs, result_type, NnMemorySpaceAttr.from_name("global"))
```

## `nn.broadcast` 待补方言规范

功能说明：

- `nn.broadcast` 是上游 [`spec/operation/nn.md`](../../spec/operation/nn.md) 中 `operation/nn.broadcast` 的目标方言层承载 op。
- 当前 `main` 上的 [`python/dialect/nn.py`](../../python/dialect/nn.py) 与 [`test/dialect/test_nn_dialect.py`](../../test/dialect/test_nn_dialect.py) 尚未提供 `NnBroadcastOp` 与对应测试；本节定义后续补齐实现/测试时必须满足的契约。

目标输入：

- `input: !nn.memory<...>`
- `space: #nn.space<...>`

目标输出：

- `result: !nn.memory<...>`

目标 verifier 约束：

- `input`、`result` 必须为 `NnMemoryType`。
- `input.element_type == result.element_type`。
- `input.space == result.space == op.space`。
- `input.shape` 与 `result.shape` 的广播兼容规则以上游 `operation/nn` 为准。

目标 parse/print 约束：

- 合法 `nn.broadcast` 模块文本必须支持 parse 后再 print 回稳定文本。
- 非法 `space/element_type` 组合必须在 verifier 阶段报错，而不是静默接受。

目标示例（目标 op 形态，当前 `main` 尚未实现）：

```python
op = NnBroadcastOp(inp, result_type, NnMemorySpaceAttr.from_name("global"))
```

## 测试

- 方言测试：[`test/dialect/test_nn_dialect.py`](../../test/dialect/test_nn_dialect.py)
- 上游运算测试：[`test/operation/test_operation_nn.py`](../../test/operation/test_operation_nn.py)
- 方言测试命令：`pytest -q test/dialect/test_nn_dialect.py`

### 测试目标

- 验证 `NnMemorySpaceAttr` 的合法取值、非法取值和 round-trip。
- 验证 `global/shared/local/tsm/tlm` 五种空间共用相同的 parse/print 与 verifier 口径。
- 验证 `NnMemoryType` 的 parse/print、rank 约束和缺失字段错误。
- 验证 `nn.add` 在合法输入下通过 verifier。
- 验证 `nn` 二元 op 的 space mismatch 与 attribute space mismatch 错误。
- 验证比较 op 结果类型必须为 `i1`。
- 验证模块级 parse/print round-trip。
- 当前 `main` 尚未覆盖 `nn.matmul`；后续实现/测试任务需补齐其 verifier 与 round-trip 测试。
- 当前 `main` 尚未覆盖 `nn.broadcast`；后续实现/测试任务需补齐其 verifier 与 round-trip 测试。

### 测试清单

| 用例 ID | 测试点 | 说明 | 对应测试 |
| --- | --- | --- | --- |
| TC-NN-001 | `NnMemoryType` round-trip | `!nn.memory<...>` parse/print 稳定 | `test_memory_type_round_trip` |
| TC-NN-002 | `NnMemorySpaceAttr` round-trip | `global/shared/local/tsm/tlm` 五种 text form 共用同一 parse/print 路径 | `test_space_attr_round_trip` |
| TC-NN-003 | 非法 space 拒绝 | 非法 `space` 在 verifier 阶段失败 | `test_invalid_space_attr_rejected` |
| TC-NN-004 | `shape/stride` rank 约束 | rank mismatch 被 verifier 拒绝 | `test_memory_type_rank_mismatch_rejected` |
| TC-NN-005 | `nn.add` 合法通过 | `operand/result/space` 一致时 verifier 通过 | `test_add_op_verify_success` |
| TC-NN-006 | operand space mismatch | operand space 不一致时报错 | `test_add_op_rejects_operand_space_mismatch` |
| TC-NN-007 | op attribute space mismatch | op attribute `space` 与 type `space` 不一致时报错 | `test_add_op_rejects_attr_space_mismatch` |
| TC-NN-008 | compare 结果类型约束 | 比较 op 结果 `element_type` 必须为 `i1` | `test_compare_op_requires_i1_result` |
| TC-NN-009 | 模块 round-trip | 含 `nn.add` 的模块文本 parse/print 稳定 | `test_module_round_trip` |
| TC-NN-010 | 文本 operand space mismatch | 文本装配后的 operand `space` mismatch 在 verify 阶段失败 | `test_space_mismatch_from_text_rejected` |
| TC-NN-011 | 文本 attribute space mismatch | 文本装配后的 op attribute `space` mismatch 在 verify 阶段失败 | `test_attr_space_mismatch_from_text_rejected` |
| TC-NN-012 | `nn.memory` 缺失字段 | 缺失字段在 parse 阶段失败 | `test_memory_type_parse_requires_all_fields` |

### `nn.matmul` 待补测试清单

当前 [`test/dialect/test_nn_dialect.py`](../../test/dialect/test_nn_dialect.py) 尚无 `nn.matmul` 对应用例；以下为后续实现/测试任务必须补齐的建议清单。

| 用例 ID | 测试点 | 说明 | 建议测试 |
| --- | --- | --- | --- |
| TC-NN-MM-001 | `nn.matmul` 合法通过 | 合法矩阵乘输入通过 verifier | `test_matmul_op_verify_success` |
| TC-NN-MM-002 | `nn.matmul` 形状不匹配 | `lhs.shape[1] != rhs.shape[0]` 时 verifier 报错 | `test_matmul_op_shape_mismatch` |
| TC-NN-MM-003 | `nn.matmul` 结果 shape 不匹配 | 结果 shape 与 `lhs/rhs` 不一致时报错 | `test_matmul_op_result_shape_mismatch` |
| TC-NN-MM-004 | `nn.matmul` 模块 round-trip | 含 `nn.matmul` 的模块文本 parse/print 稳定 | `test_matmul_module_round_trip` |

### `nn.broadcast` 待补测试清单

当前 [`test/dialect/test_nn_dialect.py`](../../test/dialect/test_nn_dialect.py) 尚无 `nn.broadcast` 对应用例；以下为后续实现/测试任务必须补齐的建议清单。

| 用例 ID | 测试点 | 说明 | 建议测试 |
| --- | --- | --- | --- |
| TC-NN-BC-001 | `nn.broadcast` 合法通过 | 合法 broadcast 输入通过 verifier | `test_broadcast_op_verify_success` |
| TC-NN-BC-002 | `nn.broadcast` 空间不匹配 | input/result `space` 不一致时报错 | `test_broadcast_op_space_mismatch` |
| TC-NN-BC-003 | `nn.broadcast` 元素类型不匹配 | input/result `element_type` 不一致时报错 | `test_broadcast_op_element_type_mismatch` |
| TC-NN-BC-004 | `nn.broadcast` 模块 round-trip | 含 `nn.broadcast` 的模块文本 parse/print 稳定 | `test_broadcast_module_round_trip` |

### 用例与 Op 覆盖关系

- `nn.add`：已有直接方言级 verifier 测试覆盖。
- `nn.sub`、`nn.mul`、`nn.truediv`：当前实现复用相同二元算术 verifier，行为与 `nn.add` 同构；后续若出现独立 verifier 分支，必须补独立方言测试。
- `nn.eq`：已有比较结果类型约束覆盖。
- `nn.ne`、`nn.lt`、`nn.le`、`nn.gt`、`nn.ge`：当前实现复用相同比较 verifier，行为与 `nn.eq` 同构；后续若出现独立 verifier 分支，必须补独立方言测试。
- `nn.matmul`：当前 `main` 尚未实现；实现落地后必须新增独立 verifier/round-trip 测试，覆盖 rank、contracting dim、result shape 与 `space` 约束。
- `nn.broadcast`：当前 `main` 尚未实现；实现落地后必须新增独立 verifier/round-trip 测试，覆盖类型/空间一致性与广播规则对齐。

## 测试标准

- `pytest -q test/dialect/test_nn_dialect.py` 返回码必须为 `0`。
- `space mismatch` 测试必须明确在 `nn` op 上触发 `VerifyException`。
- `parse/print` 测试必须比较文本输出与输入保持稳定。
- 任何新增 `nn` op、修改 verifier 分支或新增 `space` 取值，都必须更新本文件的 op 定义与测试清单。
- `nn.matmul` 在未落地实现/测试前，不得在“当前测试清单”中伪装成已覆盖项。

## 兼容性细节

- 本 spec 仅描述 `python/dialect/nn.py` 中方言层必须保留的字段和 verifier 规则，不额外引入新的 semantic layer。
- 上游逐元素 `Memory` 运算语义仍以 [`spec/operation/nn.md`](../../spec/operation/nn.md) 为准。
- 未来若新增独立 verifier 逻辑或新增 op，必须把该 op 补入“Op 定义”与“测试清单”。
