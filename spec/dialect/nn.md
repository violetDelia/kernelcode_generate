# nn.md

聚焦 `python/dialect/nn.py` 的设计语义，说明 `nn dialect` 在 space 建模、verifier 检查、parse/print 及 space mismatch 方面的约定。移除过程性描述，仅保留和实现直接对应的设计说明。

## 文档信息

- 创建者：`规格小队`
- 最后一次更改：`规格小队`
- `spec`：[`spec/dialect/nn.md`](../../spec/dialect/nn.md)
- `上游语义`：[`spec/operation/nn.md`](../../spec/operation/nn.md)
- `关联类型`：[`spec/symbol_variable/memory.md`](../../spec/symbol_variable/memory.md)
- `test`：[`test/dialect/test_nn_dialect.py`](../../test/dialect/test_nn_dialect.py)
- `功能实现`：[`python/dialect/nn.py`](../../python/dialect/nn.py)

## 范围与目标

- 聚焦 `python/dialect/nn.py` 对 `nn` dialect 的 space 建模与 verifier 规范；其他背景、过程性迁移描述一律去除。
- 明确 dialect 公开的 `space` attribute 与 `memory` type 语义，以及 verifier 应在方言层面提前检查的约束。
- 说明如何保证 parse/print round-trip、space mismatch 约束与现有测试契约保持一致。

## Space 建模

- `python/dialect/nn.py` 通过 `NnMemorySpaceAttr` 显式建模 `global`、`shared`、`local` 三个 memory space。
- `NnMemoryType` 需要记录 `shape`、`stride`、`element_type` 与 `space` 四类信息；任一字段违反规则都应由 verifier 报错。
- `shape` 和 `stride` 的 rank 必须匹配，且每一维支持静态整数、`?` 动态或符号；`stride` 中的 `?` 必须在 `shape` 允许的 `?` 对应位置存在符号或整数。
- `space` 只能取三者之一，不得接受未声明的值；对此，verifier 使用 `space_attr.space in {"global","shared","local"}`。
- 任何由 parse/print 产生的 `NnMemoryType` 必须包含上述四个字段，缺失字段视为 parse 错误或 verifier 报错。

## Verifier 约束

- Verifier 负责在 `python/dialect/nn.py` 的 op 定义层面执行：
  1. 操作数与结果必须是 `NnMemoryType`。
  2. 操作数 `element_type` 需与 expected dtype 兼容；比较 op 结果 `element_type` 固定 `i1`。
  3. 输入 `space` 必须一致；如 `lhs.space != rhs.space`，立即抛出 `verify_exception`.
  4. `shape` 与 `stride` rank 判断、`stride` 对齐检查（如 `stride` 长度等于 `shape`）。
  5. `NnMemorySpaceAttr` 与 `NnMemoryType.space` 之间的语义一致，若 op attribute `space` 为 `local`，对应 operand/result type 也必须标记 `space=local`。
- 所有这些检查应在 `python/dialect/nn.py` 中通过 `verify_` 方法入链，而不是在后续 lowering/solver 中延迟。

## API 示例

### `NnMemorySpaceAttr`

示例：

```python
space = NnMemorySpaceAttr.from_name("global")
```

预期行为：

- `space` 仅允许 `global/shared/local`
- 其他值触发 verifier 报错

### `NnMemoryType`

示例：

```python
shape = ArrayAttr([IntAttr(4), IntAttr(8)])
stride = ArrayAttr([IntAttr(8), IntAttr(1)])
element_type = IntegerType(32)
space = NnMemorySpaceAttr.from_name("global")
mem_ty = NnMemoryType(shape, stride, element_type, space)
```

预期行为：

- `shape` 与 `stride` rank 必须一致
- `space` 必须为 `global/shared/local`
- 违反约束时 verifier 报错

### `nn.add`

示例：

```python
lhs_type = NnMemoryType(
    ArrayAttr([IntAttr(4), IntAttr(8)]),
    ArrayAttr([IntAttr(8), IntAttr(1)]),
    IntegerType(32),
    NnMemorySpaceAttr.from_name("global"),
)
rhs_type = NnMemoryType(
    ArrayAttr([IntAttr(4), IntAttr(8)]),
    ArrayAttr([IntAttr(8), IntAttr(1)]),
    IntegerType(32),
    NnMemorySpaceAttr.from_name("global"),
)
result_type = lhs_type
# lhs/rhs 为具备 NnMemoryType 的 SSAValue（例如由上游 op 产生）
op = NnAddOp(lhs, rhs, result_type, NnMemorySpaceAttr.from_name("global"))
```

预期行为：

- `lhs`/`rhs`/`result` 类型必须是 `NnMemoryType`
- `lhs.space` 与 `rhs.space` 必须一致，且与 `op.space` 一致
- `shape`/`stride` 必须一致
- 不满足时 verifier 抛出 `VerifyException`

### `nn.eq`

示例：

```python
lhs_type = NnMemoryType(
    ArrayAttr([IntAttr(4), IntAttr(8)]),
    ArrayAttr([IntAttr(8), IntAttr(1)]),
    IntegerType(32),
    NnMemorySpaceAttr.from_name("global"),
)
rhs_type = NnMemoryType(
    ArrayAttr([IntAttr(4), IntAttr(8)]),
    ArrayAttr([IntAttr(8), IntAttr(1)]),
    IntegerType(32),
    NnMemorySpaceAttr.from_name("global"),
)
result_type = NnMemoryType(
    ArrayAttr([IntAttr(4), IntAttr(8)]),
    ArrayAttr([IntAttr(8), IntAttr(1)]),
    i1,
    NnMemorySpaceAttr.from_name("global"),
)
# lhs/rhs 为具备 NnMemoryType 的 SSAValue（例如由上游 op 产生）
op = NnEqOp(lhs, rhs, result_type, NnMemorySpaceAttr.from_name("global"))
```

预期行为：

- 结果 `element_type` 固定为 `i1`
- 其余 verifier 约束与 `nn.add` 相同

## Parse/Print 及 Space Mismatch 测试

- 设计文档必须指导测试团队确保 `python/dialect/nn.py` 的 parser 与 printer 支持 round-trip：任何合法 `!nn.memory` assembly 经过 parse 后再 print 回原始文本。
- 需要补充 `space mismatch` 的测试目标：比如 `nn.add` 两 operand 处于不同 space 时，verifier 必须报错；同样 op attribute `space` 与 `NnMemoryType.space` 不匹配的 assembly 也要被 parse/verify 捕获。
- `parse/print/space mismatch` 相关测试应至少覆盖：
  1. `Memory` type 解析/打印保持 `shape`、`stride`、`space` 信息一致。
  2. `nn.add` 的 operand/element type/space 验证期望行为（匹配 vs mismatch）。
  3. `NnMemorySpaceAttr` 提供的三种值在 text form 中可被 parse，且 parse 后 print 回相同文本。
  4. 文本 assembly 中 op attribute `space` 与 operand/result type `space` 不一致时，必须在 verify 阶段失败。
- 此外，`test/dialect/test_nn_dialect.py` 中应该包含 `space mismatch` 与 parse/print round-trip 故意失败用例。

## 测试标准

- 使用 `pytest -q test/dialect/test_nn_dialect.py` 覆盖上述 parse/print 与 verifier 目标。
- `space mismatch` 测试必须明确在 `nn` op 上触发 `verify_exception`，并确保错误信息指出 `space` 不一致。
- `parse/print` 测试要比较文本输出与输入严格一致，防止命名或 `space` 信息漏写。
- 任何对 `python/dialect/nn.py` 作出的修改都必须至少带来一条针对以上目标的测试说明。

## 兼容性细节

- 现有 `spec/operation/nn.md` 的逐元素 `Memory` 语义仍然是 `nn` dialect 的上游；本 spec 仅描述 `python/dialect/nn.py` 中哪些字段必须保留，不另加新的 semantic layer。
- 未来若新增 `space` 值（如 `tensorCore`/`register`），必须更新本 spec 的 `space modeling` 和 `verifier` 部分，并明确引入新测试。
