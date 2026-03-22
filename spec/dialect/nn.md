# nn.md

## 功能简介

`nn dialect` 定义方言层稳定接口，负责建模 memory space、memory type，以及逐元素算术、逐元素比较、显式 `broadcast` 和二维 `matmul` 的 IR 形态与 verifier 约束。本规范仅描述方言层字段、文本形式与校验语义，不包含上游高层 API 调度逻辑。

## 文档信息

- 创建者：`规格小队`
- 最后一次更改：`金铲铲大作战`
- `spec`：[`spec/dialect/nn.md`](../../spec/dialect/nn.md)
- `功能实现`：[`kernel_gen/dialect/nn.py`](../../kernel_gen/dialect/nn.py)
- `test`：[`test/dialect/test_nn_dialect.py`](../../test/dialect/test_nn_dialect.py)

## 依赖

- [`spec/operation/nn.md`](../../spec/operation/nn.md)：上游算子语义。
- [`spec/symbol_variable/memory.md`](../../spec/symbol_variable/memory.md)：`Memory` 的 `shape/stride/dtype/space` 基础语义。
- [`kernel_gen/dialect/nn.py`](../../kernel_gen/dialect/nn.py)：方言实现。
- [`test/dialect/test_nn_dialect.py`](../../test/dialect/test_nn_dialect.py)：方言测试。

## 目标

- 提供 `global/shared/local/tsm/tlm` 五种 memory space 的统一属性表示。
- 提供可解析、可打印、可校验的 `!nn.memory<...>` 类型表示。
- 为 `nn.add/sub/mul/truediv/eq/ne/lt/le/gt/ge/broadcast/matmul` 提供稳定的方言层接口。
- 明确 `nn dialect` 不支持逐元素隐式 broadcast，所有广播必须显式使用 `nn.broadcast`。
- 保证合法文本 IR 可以 round-trip，非法输入在 parse 或 verifier 阶段被拒绝。

## 限制与边界

- 本文件只定义 `kernel_gen/dialect/nn.py` 的方言层接口，不重复上游 `operation/nn` 的高层 API 语义。
- 上游若允许逐元素隐式 broadcast，进入 `nn dialect` 前必须显式展开为 `nn.broadcast`。
- `NnMemorySpaceAttr` 仅允许 `global/shared/local/tsm/tlm` 五种取值。
- `NnMemoryType.space` 与各 op 的 `space` attribute 必须使用同一语义口径。
- `NnMemoryType` 中 `shape` 与 `stride` 的 rank 必须一致；每一维支持静态整数、符号或 `?`。
- `shape` 中的 `?` 表示动态维度；`stride` 中的 `?` 不允许与同位置 `shape` 中的 `?` 直接成对出现。
- 二元逐元素 op 的 `lhs/rhs/result` 必须满足 `shape/stride/space` 的 verifier 约束，不能依赖方言层做隐式 broadcast。
- 比较 op 的结果 `element_type` 必须为 `i1`。
- `nn.matmul` 仅建模二维矩阵乘，`lhs.shape[1]` 与 `rhs.shape[0]` 必须语义一致。
- `space` 指 `nn dialect` 中 memory 所在的物理或逻辑空间，由 `NnMemorySpaceAttr` 表示。
- `memory type` 指 `NnMemoryType`，由 `shape/stride/element_type/space` 组成。
- `round-trip` 指文本 IR 在 parse 后再 print，得到稳定且等价的文本表示。
- 合法 `!nn.memory<...>`、`#nn.space<...>` 与包含公开 op 的模块文本必须支持 round-trip。

## 公开接口

### NnMemorySpaceAttr

功能说明：

- 表示 `nn dialect` 中唯一合法的 memory space attribute。

参数说明：

- `name: str`：space 名称，仅允许 `global/shared/local/tsm/tlm`。

使用示例：

```python
space = NnMemorySpaceAttr.from_name("tsm")
```

注意事项：

- 非法名称必须在解析或校验阶段被拒绝。

返回与限制：

- 返回 `NnMemorySpaceAttr`；只接受五种合法值。

### NnMemoryType

功能说明：

- 表示 `nn dialect` 的 memory 类型，统一建模 `shape/stride/element_type/space`。

参数说明：

- `shape: ArrayAttr[Attribute]`：每维为静态整数、符号或 `?`。
- `stride: ArrayAttr[Attribute]`：每维为静态整数、符号或 `?`。
- `element_type: Attribute`：元素类型 attribute。
- `space: NnMemorySpaceAttr`：memory 所在空间。

使用示例：

```python
mem_ty = NnMemoryType(shape, stride, element_type, space)
```

注意事项：

- `shape` 与 `stride` 的 rank 必须一致。
- `shape` 中的 `?` 可表示动态维度；`stride` 中的 `?` 受同位约束限制。
- 缺失字段的文本类型必须在 parse 阶段失败。

返回与限制：

- 返回 `NnMemoryType`；`space` 必须合法，`shape/stride` 必须满足 rank 与同位约束。

### nn.add

功能说明：

- 逐元素加法。

参数说明：

- `lhs: !nn.memory<...>`：左操作数。
- `rhs: !nn.memory<...>`：右操作数。
- `result: !nn.memory<...>`：结果类型。
- `space: #nn.space<...>`：op 的空间属性。

使用示例：

```python
op = NnAddOp(lhs, rhs, result_type, NnMemorySpaceAttr.from_name("global"))
```

注意事项：

- `lhs/rhs/result` 必须为 `NnMemoryType`。
- `shape/stride/space` 必须一致。
- 不支持隐式 broadcast。

返回与限制：

- 返回 `NnAddOp`；`result.element_type` 必须与 operand 一致。

### nn.sub

功能说明：

- 逐元素减法。

参数说明：

- 同 `nn.add`。

使用示例：

```python
op = NnSubOp(lhs, rhs, result_type, NnMemorySpaceAttr.from_name("global"))
```

注意事项：

- verifier 约束与 `nn.add` 相同，不支持隐式 broadcast。

返回与限制：

- 返回 `NnSubOp`；`result.element_type` 必须与 operand 一致。

### nn.mul

功能说明：

- 逐元素乘法。

参数说明：

- 同 `nn.add`。

使用示例：

```python
op = NnMulOp(lhs, rhs, result_type, NnMemorySpaceAttr.from_name("global"))
```

注意事项：

- verifier 约束与 `nn.add` 相同，不支持隐式 broadcast。

返回与限制：

- 返回 `NnMulOp`；`result.element_type` 必须与 operand 一致。

### nn.truediv

功能说明：

- 逐元素真除法。

参数说明：

- 同 `nn.add`。

使用示例：

```python
op = NnTrueDivOp(lhs, rhs, result_type, NnMemorySpaceAttr.from_name("global"))
```

注意事项：

- verifier 约束与 `nn.add` 相同，不支持隐式 broadcast。

返回与限制：

- 返回 `NnTrueDivOp`；`result.element_type` 必须与 operand 一致。

### nn.eq

功能说明：

- 逐元素相等比较。

参数说明：

- 同 `nn.add`。

使用示例：

```python
op = NnEqOp(lhs, rhs, result_type, NnMemorySpaceAttr.from_name("global"))
```

注意事项：

- verifier 约束与算术二元 op 基本一致。
- `result.element_type` 必须为 `i1`。
- 不支持隐式 broadcast。

返回与限制：

- 返回 `NnEqOp`；结果元素类型固定为 `i1`。

### nn.ne

功能说明：

- 逐元素不等比较。

参数说明：

- 同 `nn.add`。

使用示例：

```python
op = NnNeOp(lhs, rhs, result_type, NnMemorySpaceAttr.from_name("global"))
```

注意事项：

- verifier 约束与 `nn.eq` 相同，不支持隐式 broadcast。

返回与限制：

- 返回 `NnNeOp`；结果元素类型固定为 `i1`。

### nn.lt

功能说明：

- 逐元素小于比较。

参数说明：

- 同 `nn.add`。

使用示例：

```python
op = NnLtOp(lhs, rhs, result_type, NnMemorySpaceAttr.from_name("global"))
```

注意事项：

- verifier 约束与 `nn.eq` 相同，不支持隐式 broadcast。

返回与限制：

- 返回 `NnLtOp`；结果元素类型固定为 `i1`。

### nn.le

功能说明：

- 逐元素小于等于比较。

参数说明：

- 同 `nn.add`。

使用示例：

```python
op = NnLeOp(lhs, rhs, result_type, NnMemorySpaceAttr.from_name("global"))
```

注意事项：

- verifier 约束与 `nn.eq` 相同，不支持隐式 broadcast。

返回与限制：

- 返回 `NnLeOp`；结果元素类型固定为 `i1`。

### nn.gt

功能说明：

- 逐元素大于比较。

参数说明：

- 同 `nn.add`。

使用示例：

```python
op = NnGtOp(lhs, rhs, result_type, NnMemorySpaceAttr.from_name("global"))
```

注意事项：

- verifier 约束与 `nn.eq` 相同，不支持隐式 broadcast。

返回与限制：

- 返回 `NnGtOp`；结果元素类型固定为 `i1`。

### nn.ge

功能说明：

- 逐元素大于等于比较。

参数说明：

- 同 `nn.add`。

使用示例：

```python
op = NnGeOp(lhs, rhs, result_type, NnMemorySpaceAttr.from_name("global"))
```

注意事项：

- verifier 约束与 `nn.eq` 相同，不支持隐式 broadcast。

返回与限制：

- 返回 `NnGeOp`；结果元素类型固定为 `i1`。

### nn.broadcast

功能说明：

- 显式广播 op，用于把上游广播语义展开到方言层。

参数说明：

- `input: !nn.memory<...>`：输入 memory。
- `result: !nn.memory<...>`：广播后的结果类型。
- `space: #nn.space<...>`：op 的空间属性。

使用示例：

```python
op = NnBroadcastOp(inp, result_type, NnMemorySpaceAttr.from_name("global"))
```

注意事项：

- `input/result` 必须为 `NnMemoryType`。
- `input.element_type == result.element_type`。
- `input.space == result.space == op.space`。
- 广播按尾维对齐，`result.rank >= input.rank`。
- 对齐后维度要么相等，要么输入维度为静态整数 `1`；`?` 仅与同为 `?` 的维度视为一致。

返回与限制：

- 返回 `NnBroadcastOp`；广播必须显式建模。

### nn.matmul

功能说明：

- 二维矩阵乘 op。

参数说明：

- `lhs: !nn.memory<...>`：左矩阵。
- `rhs: !nn.memory<...>`：右矩阵。
- `result: !nn.memory<...>`：结果矩阵类型。
- `space: #nn.space<...>`：op 的空间属性。

使用示例：

```python
op = NnMatmulOp(lhs, rhs, result_type, NnMemorySpaceAttr.from_name("global"))
```

注意事项：

- `lhs/rhs/result` 必须为 `NnMemoryType`。
- 三者 `shape` 必须为 rank=2。
- `lhs.shape[1]` 与 `rhs.shape[0]` 必须语义一致。
- `result.shape[0] == lhs.shape[0]`，`result.shape[1] == rhs.shape[1]`。
- `element_type` 与 `space` 必须一致。

返回与限制：

- 返回 `NnMatmulOp`；仅定义二维矩阵乘语义。

## 测试

- 测试文件：[`test/dialect/test_nn_dialect.py`](../../test/dialect/test_nn_dialect.py)
- 执行命令：`pytest -q test/dialect/test_nn_dialect.py`

### 测试目标

- 验证 `NnMemorySpaceAttr` 的合法取值、非法输入与文本 round-trip。
- 验证 `NnMemoryType` 的字段完整性、rank 约束、`shape/stride` 合法性与文本 round-trip。
- 验证 `nn.add/sub/mul/truediv/eq/ne/lt/le/gt/ge` 的 operand/result/type/space verifier 约束。
- 验证 `nn.broadcast` 的显式广播规则、space 一致性、element type 一致性与文本 round-trip。
- 验证 `nn.matmul` 的 rank、shape、space、element type 约束与文本 round-trip。
- 验证逐元素链路拒绝隐式 broadcast。

### 功能与用例清单

| 用例 ID | 测试点 | 对应测试 |
| --- | --- | --- |
| NN-DIA-001 | `NnMemoryType` round-trip | `test_memory_type_round_trip` |
| NN-DIA-002 | `NnMemorySpaceAttr` round-trip | `test_space_attr_round_trip` |
| NN-DIA-003 | 非法 space 拒绝 | `test_invalid_space_attr_rejected` |
| NN-DIA-004 | memory type rank 不一致 | `test_memory_type_rank_mismatch_rejected` |
| NN-DIA-005 | `nn.add` 合法路径 | `test_add_op_verify_success` |
| NN-DIA-006 | `nn.add` operand space 不一致 | `test_add_op_rejects_operand_space_mismatch` |
| NN-DIA-007 | `nn.add` attribute space 不一致 | `test_add_op_rejects_attr_space_mismatch` |
| NN-DIA-008 | 比较结果必须为 `i1` | `test_compare_op_requires_i1_result` |
| NN-DIA-009 | 模块 round-trip | `test_module_round_trip` |
| NN-DIA-010 | 文本 operand space 不一致 | `test_space_mismatch_from_text_rejected` |
| NN-DIA-011 | 文本 attribute space 不一致 | `test_attr_space_mismatch_from_text_rejected` |
| NN-DIA-012 | memory type 缺失字段 | `test_memory_type_parse_requires_all_fields` |
| NN-DIA-013 | `nn.broadcast` 合法路径 | `test_broadcast_op_verify_success` |
| NN-DIA-014 | `nn.broadcast` space 不一致 | `test_broadcast_op_space_mismatch` |
| NN-DIA-015 | `nn.broadcast` element type 不一致 | `test_broadcast_op_element_type_mismatch` |
| NN-DIA-016 | broadcast 模块 round-trip | `test_broadcast_module_round_trip` |
| NN-DIA-017 | `nn.matmul` 合法路径 | `test_matmul_op_verify_success` |
| NN-DIA-018 | `nn.matmul` contracting 维不匹配 | `test_matmul_op_shape_mismatch` |
| NN-DIA-019 | `nn.matmul` 结果 shape 不匹配 | `test_matmul_op_result_shape_mismatch` |
| NN-DIA-020 | matmul 模块 round-trip | `test_matmul_module_round_trip` |
| NN-DIA-021 | `nn.matmul` operand space 不一致 | `test_matmul_op_space_mismatch` |
| NN-DIA-022 | `nn.matmul` attribute space 不一致 | `test_matmul_op_attr_space_mismatch` |
| NN-DIA-023 | `nn.matmul` rank 不匹配 | `test_matmul_op_rank_mismatch` |
| NN-DIA-024 | `nn.matmul` element type 不一致 | `test_matmul_op_element_type_mismatch` |
| NN-DIA-025 | `nn.add` 拒绝隐式 broadcast | `test_add_op_rejects_implicit_broadcast_shape_mismatch` |
| NN-DIA-026 | `nn.eq` 拒绝隐式 broadcast | `test_compare_op_rejects_implicit_broadcast_shape_mismatch` |
| NN-DIA-027 | memory type space 不是 `nn.space` | `test_memory_type_parse_rejects_non_space_attr` |
| NN-DIA-028 | memory type 非法维度条目 | `test_memory_type_rejects_invalid_dim_entry` |
| NN-DIA-029 | stride `?` 与 shape `?` 同位拒绝 | `test_memory_type_rejects_stride_question_dim_pair` |
| NN-DIA-030 | `nn.add` 非 memory operand 拒绝 | `test_add_op_rejects_non_memory_operand` |
| NN-DIA-031 | `nn.add` space/stride/element type 不一致 | `test_add_op_rejects_type_mismatch` |
| NN-DIA-032 | 算术 op(sub/mul/truediv) 合法路径 | `test_arithmetic_ops_verify_success` |
| NN-DIA-033 | 比较 op(ne/lt/le/gt/ge) 合法路径 | `test_compare_ops_verify_success` |
| NN-DIA-034 | `nn.broadcast` space/rank/shape 不一致 | `test_broadcast_op_rejects_invalid_inputs` |
| NN-DIA-035 | `nn.matmul` result space 不一致 | `test_matmul_op_result_space_mismatch` |
