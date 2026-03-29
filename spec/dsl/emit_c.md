# emit_c.md

## 功能简介

- 定义单个 MLIR op 或 SSA value 到目标后端源码片段的转换规则。
- 为 [`spec/dsl/gen_kernel.md`](../../spec/dsl/gen_kernel.md) 提供函数体拼装时可复用的节点级生成能力。
- 不负责 `func.func` 级签名拼装、完整函数输出或文件写盘。

## 文档信息

- 创建者：`摸鱼小分队`
- 最后一次更改：`摸鱼小分队`
- `spec`：[`spec/dsl/emit_c.md`](../../spec/dsl/emit_c.md)
- `功能实现`：[`kernel_gen/dsl/emit_c.py`](../../kernel_gen/dsl/emit_c.py)
- `test`：[`test/dsl/test_emit_c.py`](../../test/dsl/test_emit_c.py)

## 依赖

- [`spec/dsl/mlir_gen.md`](../../spec/dsl/mlir_gen.md)：MLIR `func.func` 生成来源。
- [`spec/dsl/gen_kernel.md`](../../spec/dsl/gen_kernel.md)：函数级源码生成入口。
- [`kernel_gen/dsl/emit_c.py`](../../kernel_gen/dsl/emit_c.py)：节点级源码片段生成实现。
- [`test/dsl/test_emit_c.py`](../../test/dsl/test_emit_c.py)：节点级源码片段生成测试。

## 目标

- 为常见算术、比较、控制流与访存 op 提供稳定的节点级源码片段生成规则。
- 保证同一 SSA value 在同一 `EmitCContext` 中具备稳定命名与稳定表达式输出。
- 为后续实现恢复明确最小支持范围：`arith` 二元算术、`arith.cmpi`、`scf.for`、unit-tile `dma.load`/`dma.store`、`symbol.add`（cpu 标量）与错误路径。

## 限制与边界

- 只负责单个 op 或单个 value 的源码片段生成，不负责遍历完整 `func.func`。
- 不负责函数签名、返回值/输出参数风格与完整函数文本组织；这些由 [`spec/dsl/gen_kernel.md`](../../spec/dsl/gen_kernel.md) 负责。
- 不负责 AST 解析、MLIR 构造、优化、文件写盘、编译、链接或运行。
- 同一接口可针对不同 `target` 生成不同源码，但参数与错误语义必须稳定。
- 对于无法映射的 op、value 依赖、类型或控制流，必须明确报错，不能静默忽略或降级。
- 仅新增 `symbol.add` 的 cpu 标量支持；其余 `symbol.*` 仍按不支持处理。
- 当 value 类型为 `!symbol.int<"...">` 时，`target=cpu` 默认映射为 `long long`。
- 当前规范恢复范围仅覆盖 `test/dsl/test_emit_c.py` 已定义的用例映射，不在本阶段扩展到其他 dialect/op。

### 支持矩阵

| 范围 | 支持/限制 | 对应测试 |
| --- | --- | --- |
| `arith.addi` / `arith.subi` | 仅支持整型与 `index`；生成赋值语句并复用命名策略；不支持 `arith.addf` 或浮点算术，必须抛出 `EmitCError`。 | EC-001、EC-005 |
| `arith.cmpi` | 仅支持 `eq` 谓词；返回布尔表达式；其他谓词必须报错。 | EC-002 |
| 常量与参数 value | 支持整型/浮点常量与 `BlockArgument` 表达式；不支持 tensor 常量；未绑定参数名需回退为 `arg{index}`。 | EC-002 |
| `scf.for` / `func.return` | 仅支持 index 迭代变量与单块循环体；`func.return` 允许 0 或 1 返回值，2+ 必须报错。 | EC-003 |
| `dma.load` / `dma.store` | 仅支持 unit-tile（`shape=[1, 1]` 且 `stride=[1, 1]`）访存；`dma.load` 来源必须是合法 memory value；`dma.store` 仅支持 unit-tile load 结果作为源；非法依赖必须报错。 | EC-004 |
| `symbol.add` | 仅 `target=cpu`；生成 `long long` 标量表达式/赋值；非 cpu target 必须报错。 | EC-007、EC-008 |
| 未支持 op / 依赖 | 不支持的 op 或非法 value 依赖必须报错并包含 op 名称。 | EC-005、EC-006 |

## 公开接口

### `EmitCContext(target, indent="    ", naming=None, type_converter=None, config=None)`

功能说明：

- 封装单次源码片段生成所需的目标后端、缩进、命名策略、类型转换入口与局部状态。

参数说明：

- `target`（`str`）：目标后端标识。
- `indent`（`str`）：缩进字符串。
- `naming`（`object | None`）：名称分配策略；可为可调用对象或具备 `allocate(...)` 的对象。
- `type_converter`（`object | None`）：类型转换策略；可为可调用对象或具备 `convert(...)` 的对象。
- `config`（`dict | None`）：生成配置。

使用示例：

```python
from kernel_gen.dsl.emit_c import EmitCContext

ctx = EmitCContext(target="cpu", indent="    ")
```

注意事项：

- 同一 SSA value 在同一上下文中必须获得稳定名称。
- 上下文可维护局部命名与缩进状态，但不持有 IR 所有权。

返回与限制：

- 返回 `EmitCContext` 实例。
- 仅用于节点级源码片段生成。

### `emit_c_op(op, ctx)`

功能说明：

- 将单个 MLIR op 生成为目标后端的单条语句或语句块文本。

参数说明：

- `op`（`object`）：待生成的 MLIR op。
- `ctx`（`EmitCContext`）：源码片段生成上下文。

使用示例：

```python
from kernel_gen.dsl.emit_c import EmitCContext, emit_c_op

stmt = emit_c_op(op, EmitCContext(target="cpu"))
```

注意事项：

- 有副作用 op 与控制流 op 必须保留 IR 顺序语义。
- `scf.for` 必须生成完整循环语句块。
- 当前恢复范围下，unit-tile `dma.load`/`dma.store` 必须保留索引顺序与读写方向。
- `target=cpu` 下 `symbol.add` 必须生成与二元算术等价的赋值语句。

返回与限制：

- 返回类型：`str`。
- 返回语义：单条语句或语句块源码文本。
- 限制条件：不支持的 op 必须抛出包含 op 名称与 target 的错误。

### `emit_c_value(value, ctx)`

功能说明：

- 将纯表达式化的 MLIR SSA value 生成为目标后端右值表达式。

参数说明：

- `value`（`object`）：MLIR SSA value 或等价 value 节点。
- `ctx`（`EmitCContext`）：源码片段生成上下文。

使用示例：

```python
from kernel_gen.dsl.emit_c import EmitCContext, emit_c_value

expr = emit_c_value(value, EmitCContext(target="cpu"))
```

注意事项：

- 仅纯表达式 value 允许使用该接口。
- 若 value 依赖未支持的 owner op 或非法依赖路径，必须报错。
- 输出表达式必须与 `emit_c_op(...)` 使用的命名策略保持一致。
- 当 value 为未绑定名称的 `BlockArgument` 时，必须回退为 `arg{index}` 默认命名，避免受访问顺序影响。
- `target=cpu` 下 `symbol.add` 结果可作为右值表达式生成。

返回与限制：

- 返回类型：`str`。
- 返回语义：可嵌入右值位置的表达式文本。
- 限制条件：当前恢复范围覆盖算术表达式、比较表达式、常量、unit-tile `dma.load` 结果与 `symbol.add` 标量表达式（仅 cpu）。

## 测试

- 测试文件：[`test/dsl/test_emit_c.py`](../../test/dsl/test_emit_c.py)
- 执行命令：`pytest -q test/dsl/test_emit_c.py`

### 测试目标

- 验证节点级算术、比较、循环与访存 op 的源码片段生成规则。
- 验证 `EmitCContext` 下 SSA 命名与表达式生成的一致性。
- 验证不支持 op 与非法 value 依赖的错误路径。
- 验证 `symbol.add` 仅允许 `target=cpu`；非 cpu target 必须明确报错。

### 功能与用例清单

- EC-001：算术 op 可生成合法赋值语句。（`test_emit_c_op_lowers_arith_add`）
- EC-002：比较 value 可生成合法比较表达式。（`test_emit_c_value_lowers_compare`）
- EC-002A：未绑定 `BlockArgument` 默认命名按参数索引回退为 `arg{index}`。（`test_emit_c_value_unbound_block_argument_uses_index`）
- EC-003：`scf.for` 可生成目标循环结构与循环体语句。（`test_emit_c_op_lowers_scf_for`）
- EC-004：unit-tile `dma.load`/`dma.store` 可生成合法索引访问代码。（`test_emit_c_op_lowers_memory_access`）
- EC-005：不支持 op 时抛出包含 op 名称的错误。（`test_emit_c_op_rejects_unsupported_op`）
- EC-006：非法 value 依赖生成时报错。（`test_emit_c_value_rejects_invalid_dependency`）
- EC-007：`symbol.add` 在 cpu target 下可生成标量赋值语句与右值表达式。（`test_emit_c_op_lowers_symbol_add`）
- EC-008：非 cpu target 下 `symbol.add` 必须报错，禁止跨 target 误下发。（`test_emit_c_op_rejects_symbol_add_on_non_cpu`）
