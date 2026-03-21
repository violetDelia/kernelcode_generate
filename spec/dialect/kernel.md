# kernel.md

## 功能简介

- 定义 `kernel` dialect 的执行步骤层运算语义，用于描述逐元素计算、比较、选择与类型转换。
- 所有结果通过显式 `outs(...)` 写回，不产生 SSA result。
- 复用 `nn` dialect 的 memory type 与 space attribute，不新增独立 memory 类型体系。

## 文档信息

- 创建者：`榕`
- 最后一次更改：`摸鱼小分队`
- `spec`：[`spec/dialect/kernel.md`](../../spec/dialect/kernel.md)
- `功能实现`：[`kernel_gen/dialect/kernel.py`](../../kernel_gen/dialect/kernel.py)
- `test`：[`test/dialect/test_kernel_dialect.py`](../../test/dialect/test_kernel_dialect.py)

## 依赖

- [`spec/dialect/nn.md`](../../spec/dialect/nn.md)：`NnMemorySpaceAttr` 与 `NnMemoryType` 复用规则。

## 目标

- 提供可解析、可校验的逐元素计算与比较 op 集合。
- 明确 `ins(...)` / `outs(...)` 形式下的类型与空间一致性校验规则。
- 为后续实现提供最小可落地的 verifier 约束与测试目标。

## 限制与边界

- 只覆盖逐元素算术、比较、选择与类型转换，不定义 `matmul`、`reduce`、`conv`、控制流或同步语义。
- 不负责函数输出语义、module 组织、调度策略或 lowering 过程。
- 不支持隐式 broadcast；所有参与计算的 memory operand 必须形状一致。
- 本版仅支持 memory operand，不支持标量 operand；标量扩展留待后续版本。
- 所有 op 不产生 SSA result，结果必须写入 `outs(...)`。
- memory operand 的 `shape/stride/space` 必须在 verifier 阶段完成一致性校验。

## 公开接口

### NnMemorySpaceAttr

功能说明：

- 复用 `nn` dialect 的 memory space attribute。

参数说明：

- `name(str)`：space 名称，仅允许 `global/shared/local/tsm/tlm`。

使用示例：

```python
space = NnMemorySpaceAttr.from_name("global")
```

注意事项：

- 非法 space 名称必须在解析或校验阶段被拒绝。

返回与限制：

- 返回 `NnMemorySpaceAttr`。
- 仅接受 `global/shared/local/tsm/tlm` 五种取值。

### NnMemoryType

功能说明：

- 复用 `nn` dialect 的 memory 类型，统一建模 `shape/stride/element_type/space`。

参数说明：

- `shape(ArrayAttr[Attribute])`：每维为静态整数、符号或 `?`。
- `stride(ArrayAttr[Attribute])`：每维为静态整数、符号或 `?`。
- `element_type(Attribute)`：元素类型 attribute。
- `space(NnMemorySpaceAttr)`：memory 所在空间。

使用示例：

```python
mem_ty = NnMemoryType(shape, stride, element_type, space)
```

注意事项：

- `shape` 与 `stride` 的 rank 必须一致。
- `shape` 中的 `?` 表示动态维度。

返回与限制：

- 返回 `NnMemoryType`。
- `shape/stride/space` 必须满足 rank 与合法空间约束。

### kernel.add

功能说明：

- 逐元素加法，将输入 operand 的计算结果写入输出 operand。

参数说明：

- `lhs(!nn.memory<...>)`：左输入 operand。
- `rhs(!nn.memory<...>)`：右输入 operand。
- `out(!nn.memory<...>)`：输出 operand。
- `space(#nn.space<...>)`：op 的空间属性。

使用示例：

```python
op = KernelAddOp(lhs, rhs, out, NnMemorySpaceAttr.from_name("global"))
```

注意事项：

- `lhs/rhs/out` 的 `shape/stride/space` 必须一致。
- `lhs.element_type` 与 `rhs.element_type` 必须一致，且等于 `out.element_type`。
- op 不产生 SSA result。

返回与限制：

- 返回 `KernelAddOp`。
- 结果写入 `out`。

### kernel.sub

功能说明：

- 逐元素减法，将输入 operand 的计算结果写入输出 operand。

参数说明：

- 同 `kernel.add`。

使用示例：

```python
op = KernelSubOp(lhs, rhs, out, NnMemorySpaceAttr.from_name("global"))
```

注意事项：

- verifier 约束与 `kernel.add` 相同。

返回与限制：

- 返回 `KernelSubOp`。
- 结果写入 `out`。

### kernel.mul

功能说明：

- 逐元素乘法，将输入 operand 的计算结果写入输出 operand。

参数说明：

- 同 `kernel.add`。

使用示例：

```python
op = KernelMulOp(lhs, rhs, out, NnMemorySpaceAttr.from_name("global"))
```

注意事项：

- verifier 约束与 `kernel.add` 相同。

返回与限制：

- 返回 `KernelMulOp`。
- 结果写入 `out`。

### kernel.div

功能说明：

- 逐元素除法，将输入 operand 的计算结果写入输出 operand。

参数说明：

- 同 `kernel.add`。

使用示例：

```python
op = KernelDivOp(lhs, rhs, out, NnMemorySpaceAttr.from_name("global"))
```

注意事项：

- verifier 约束与 `kernel.add` 相同。

返回与限制：

- 返回 `KernelDivOp`。
- 结果写入 `out`。

### kernel.eq

功能说明：

- 逐元素相等比较，将比较结果写入输出 operand。

参数说明：

- `lhs(!nn.memory<...>)`：左输入 operand。
- `rhs(!nn.memory<...>)`：右输入 operand。
- `out(!nn.memory<...>)`：输出 operand。
- `space(#nn.space<...>)`：op 的空间属性。

使用示例：

```python
op = KernelEqOp(lhs, rhs, out, NnMemorySpaceAttr.from_name("global"))
```

注意事项：

- `lhs/rhs/out` 的 `shape/stride/space` 必须一致。
- `out.element_type` 必须为 `i1`。
- op 不产生 SSA result。

返回与限制：

- 返回 `KernelEqOp`。
- 结果写入 `out`。

### kernel.lt

功能说明：

- 逐元素小于比较，将比较结果写入输出 operand。

参数说明：

- 同 `kernel.eq`。

使用示例：

```python
op = KernelLtOp(lhs, rhs, out, NnMemorySpaceAttr.from_name("global"))
```

注意事项：

- verifier 约束与 `kernel.eq` 相同。

返回与限制：

- 返回 `KernelLtOp`。
- 结果写入 `out`。

### kernel.gt

功能说明：

- 逐元素大于比较，将比较结果写入输出 operand。

参数说明：

- 同 `kernel.eq`。

使用示例：

```python
op = KernelGtOp(lhs, rhs, out, NnMemorySpaceAttr.from_name("global"))
```

注意事项：

- verifier 约束与 `kernel.eq` 相同。

返回与限制：

- 返回 `KernelGtOp`。
- 结果写入 `out`。

### kernel.select

功能说明：

- 逐元素条件选择，根据条件 operand 在两个输入 operand 间选择结果并写入输出 operand。

参数说明：

- `cond(!nn.memory<...>)`：条件 operand。
- `lhs(!nn.memory<...>)`：条件为真时的输入 operand。
- `rhs(!nn.memory<...>)`：条件为假时的输入 operand。
- `out(!nn.memory<...>)`：输出 operand。
- `space(#nn.space<...>)`：op 的空间属性。

使用示例：

```python
op = KernelSelectOp(cond, lhs, rhs, out, NnMemorySpaceAttr.from_name("global"))
```

注意事项：

- `cond.element_type` 必须为 `i1`。
- `cond/lhs/rhs/out` 的 `shape/stride/space` 必须一致。
- `lhs/rhs/out` 的 `element_type` 必须一致。

返回与限制：

- 返回 `KernelSelectOp`。
- 结果写入 `out`。

### kernel.cast

功能说明：

- 逐元素类型转换，将转换结果写入输出 operand。

参数说明：

- `input(!nn.memory<...>)`：输入 operand。
- `out(!nn.memory<...>)`：输出 operand。
- `space(#nn.space<...>)`：op 的空间属性。

使用示例：

```python
op = KernelCastOp(input_value, out, NnMemorySpaceAttr.from_name("global"))
```

注意事项：

- `input` 与 `out` 的 `shape/stride/space` 必须一致。
- `input.element_type` 与 `out.element_type` 必须为整数或浮点类型，且不允许 `i1`。

返回与限制：

- 返回 `KernelCastOp`。
- 结果写入 `out`。

## 测试

- 测试文件：[`test/dialect/test_kernel_dialect.py`](../../test/dialect/test_kernel_dialect.py)
- 执行命令：`pytest -q test/dialect/test_kernel_dialect.py`

### 测试目标

- 验证 `NnMemorySpaceAttr` 与 `NnMemoryType` 在 `kernel` 方言中的复用与校验行为。
- 验证基础逐元素算术、比较、选择与类型转换 op 的 verifier 约束。
- 验证“无 SSA result、显式输出 operand”约束。

### 功能与用例清单

| 用例 ID | 功能 | 对应测试 |
| --- | --- | --- |
| TC-KRN-001 | 合法 space 创建成功 | `test_kernel_space_attr_valid` |
| TC-KRN-002 | 非法 space 被拒绝 | `test_kernel_space_attr_invalid` |
| TC-KRN-003 | `shape/stride` rank 不一致 | `test_kernel_memory_type_rank_mismatch` |
| TC-KRN-004 | `kernel.add` 正常路径 | `test_kernel_add_success` |
| TC-KRN-005 | `kernel.add` shape 不一致报错 | `test_kernel_add_shape_mismatch` |
| TC-KRN-006 | `kernel.eq` 输出类型为 `i1` | `test_kernel_eq_output_type` |
| TC-KRN-007 | `kernel.eq` 输出类型非法 | `test_kernel_eq_output_type_error` |
| TC-KRN-008 | `kernel.select` 条件类型非法 | `test_kernel_select_cond_type_error` |
| TC-KRN-009 | `kernel.cast` 类型非法 | `test_kernel_cast_type_error` |
| TC-KRN-010 | op 不产生 SSA result | `test_kernel_ops_no_result` |
