# emit_c.md

## 功能简介

- 定义单个 MLIR op 或 value 到目标后端源码片段的转换规则。
- 为 [`spec/dsl/gen_kernel.md`](../../spec/dsl/gen_kernel.md) 提供可调用的源码生成规则。
- 不负责 MLIR 函数级组织、函数签名拼装与完整函数输出。

## 文档信息

- 创建者：`榕`
- 最后一次更改：`榕`
- `spec`：[`spec/dsl/emit_c.md`](../../spec/dsl/emit_c.md)
- `功能实现`：[`kernel_gen/dsl/emit_c.py`](../../kernel_gen/dsl/emit_c.py)
- `test`：[`test/dsl/test_emit_c.py`](../../test/dsl/test_emit_c.py)

## 依赖

- MLIR 函数生成入口：[`spec/dsl/mlir_gen.md`](../../spec/dsl/mlir_gen.md)
- 后端源码生成入口：[`spec/dsl/gen_kernel.md`](../../spec/dsl/gen_kernel.md)
- 统一 API 规范：[`spec/include/api/Core.md`](../../spec/include/api/Core.md)
- 统一内存视图 API：[`spec/include/api/Memory.md`](../../spec/include/api/Memory.md)
- 统一算子 API：[`spec/include/api/Nn.md`](../../spec/include/api/Nn.md)

## 术语

- `EmitCContext`：单次源码片段生成时使用的上下文，包含目标后端、命名状态、类型映射与局部缓存。
- `源码片段`：可拼接到目标函数中的表达式、语句或语句块文本。
- `纯表达式 value`：可直接转成右值表达式、不依赖额外副作用执行顺序的 value。

## 目标

- 为常见计算 op、比较 op、控制流 op 与访存 op 提供稳定的源码片段生成规则。
- 保证同一 MLIR value 在同一上下文中生成结果一致。
- 保证有副作用 op 的生成顺序可控，便于上层按 IR 顺序拼装函数体。

## 限制与边界

- 不负责从 Python 函数或 AST 直接生成源码。
- 不负责遍历完整 `func.func` 并组装完整函数。
- 不负责生成函数签名、返回约定与输出参数布局，这些由 `gen_kernel` 负责。
- 不负责优化、常量折叠、循环变换或目标相关性能调优。
- 同一个 op 在不同 target 下可有不同生成规则，但接口语义必须稳定。
- 对于无法映射的 op 或类型，必须明确报错，不能静默忽略。

## 公开接口

### `EmitCContext(target, indent="    ", naming=None, type_converter=None, config=None)`

功能说明：

- 封装单个源码片段生成时需要的目标后端、缩进、命名、类型映射与配置。

参数说明：

- `target` (`str`)：目标后端标识。
- `indent` (`str`)：缩进字符串。
- `naming` (`object|None`)：名称分配器或等价接口。
- `type_converter` (`object|None`)：MLIR 类型到目标后端类型的转换入口。
- `config` (`dict|None`)：生成配置。

使用示例：

```python
ctx = EmitCContext(target="cpu", indent="    ")
```

注意事项：

- 名称分配必须稳定，避免同一 value 被生成出不同变量名。
- `type_converter` 的输出必须满足目标后端代码生成要求。

返回与限制：

- 返回 `EmitCContext` 实例。
- 仅作为片段生成上下文，不持有 IR 所有权。

### `emit_c_op(op, ctx)`

功能说明：

- 将单个 MLIR op 生成为目标后端的一段语句或语句块文本。
- 适用于有副作用 op、控制流 op 或必须落地成语句的计算 op。

参数说明：

- `op` (`object`)：单个 MLIR op。
- `ctx` (`EmitCContext`)：源码片段生成上下文。

使用示例：

```python
stmt = emit_c_op(op, ctx)
```

注意事项：

- 有副作用 op 必须保留 IR 顺序。
- `emit_c_op` 不负责拼装函数签名或完整函数结构。

返回与限制：

- 返回类型：`str`。
- 返回语义：返回单条语句或语句块源码文本。
- 限制条件：不支持的 op 必须抛出带 op 名称的错误。

### `emit_c_value(value, ctx)`

功能说明：

- 将纯表达式化的 MLIR value 生成为目标后端右值表达式。
- 供算术、比较、索引计算等场景复用。

参数说明：

- `value` (`object`)：MLIR SSA value 或等价表达式节点。
- `ctx` (`EmitCContext`)：源码片段生成上下文。

使用示例：

```python
expr = emit_c_value(value, ctx)
```

注意事项：

- 仅纯表达式 value 允许使用该接口。
- 若 value 依赖尚未生成的副作用 op，必须报错。

返回与限制：

- 返回类型：`str`。
- 返回语义：返回可嵌入右值位置的表达式文本。
- 限制条件：必须与 `emit_c_op` 的局部变量命名策略保持一致。

## 额外补充

### 常见 op 生成约束

- `arith`、`nn`、`kernel` 等无副作用计算 op，应优先生成为表达式或赋值右值。
- `scf.for` 等循环结构，应生成目标后端中的循环结构。
- `func.return` 应生成返回语句或由上层转写为输出参数写回逻辑；具体采用哪种方式由 `gen_kernel` 决定。
- 访存 op 必须保留索引顺序与读写方向，不能隐式改变布局语义。

示例：

```text
%0 = arith.addi %a, %b
=> tmp0 = a + b;
```

### value 生成约束

- 同一个 SSA value 在同一上下文中必须生成一致的表达式文本或一致的局部变量名。
- 比较结果必须生成目标后端可表达的谓词或布尔表达式。
- 常量 value 必须转换为目标后端合法字面量。

示例：

```text
%0 = arith.cmpi eq, %a, %b
=> (a == b)
```

### 错误处理约束

- 不支持的 op、未知类型、非法 value 依赖关系、不可表达的控制流都必须在片段生成阶段报错。
- 错误信息至少应包含：op 或 value 标识、失败原因、目标后端标识。

## 测试

- 测试文件：[`test/dsl/test_emit_c.py`](../../test/dsl/test_emit_c.py)
- 执行命令：`pytest -q test/dsl/test_emit_c.py`
- 测试目标：
  - 验证单个 op 与 value 的片段生成规则。
  - 验证控制流、算术、比较与错误路径的生成行为。
- 功能与用例清单：
  - EC-001：算术 op 可生成合法右值表达式或赋值语句。（`test_emit_c_op_lowers_arith_add`）
  - EC-002：比较 value 可生成合法比较表达式。（`test_emit_c_value_lowers_compare`）
  - EC-003：`scf.for` 可生成目标循环结构。（`test_emit_c_op_lowers_scf_for`）
  - EC-004：访存 op 可生成合法索引访问代码。（`test_emit_c_op_lowers_memory_access`）
  - EC-005：不支持 op 时抛出带 op 名称的错误。（`test_emit_c_op_rejects_unsupported_op`）
  - EC-006：依赖非法的 value 生成时报错。（`test_emit_c_value_rejects_invalid_dependency`）
