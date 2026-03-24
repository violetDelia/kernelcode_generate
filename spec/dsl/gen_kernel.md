# gen_kernel.md

## 功能简介

- 定义将优化后的 MLIR `func.func` 转换为目标后端完整函数源码的规则。
- 负责函数签名生成、函数体遍历，以及调用 [`spec/dsl/emit_c.md`](../../spec/dsl/emit_c.md) 中定义的节点级生成规则。
- 输出完整函数源码文本，但不负责文件写盘、编译、链接或运行。

## 文档信息

- 创建者：`摸鱼小分队`
- 最后一次更改：`摸鱼小分队`
- `spec`：[`spec/dsl/gen_kernel.md`](../../spec/dsl/gen_kernel.md)
- `功能实现`：[`kernel_gen/dsl/gen_kernel.py`](../../kernel_gen/dsl/gen_kernel.py)
- `test`：[`test/dsl/test_gen_kernel.py`](../../test/dsl/test_gen_kernel.py)

## 依赖

- [`spec/dsl/mlir_gen.md`](../../spec/dsl/mlir_gen.md)：优化后 `func.func` 的来源。
- [`spec/dsl/emit_c.md`](../../spec/dsl/emit_c.md)：单个 op/value 的源码片段生成规则。
- [`kernel_gen/dsl/gen_kernel.py`](../../kernel_gen/dsl/gen_kernel.py)：函数级源码生成实现。
- [`test/dsl/test_gen_kernel.py`](../../test/dsl/test_gen_kernel.py)：函数级源码生成测试。

## 目标

- 为优化后的单个 MLIR `func.func` 提供稳定的函数级后端源码生成能力。
- 统一约束签名、参数顺序、输出参数风格与函数体拼装规则。
- 明确支持：只读 `Memory` 输入、`Memory` 结果降为显式输出参数、标量参数顺序与默认命名保持、`emit_c` 错误向上抛出。

## 限制与边界

- 输入必须是单个优化后的 MLIR `func.func`；不负责 `builtin.module` 级组织。
- 不负责 AST 解析、MLIR 构造、优化 pass、文件写盘、编译、链接、运行或性能调优。
- 不负责定义单个 op/value 的代码生成细节；这些由 [`spec/dsl/emit_c.md`](../../spec/dsl/emit_c.md) 负责。
- 输出源码必须保持函数名、参数名与 IR 定义一致，不能引入额外公开接口。
- 对于不支持的返回形式、未知 op 或无法映射到目标后端源码的 IR，必须明确报错。

## 公开接口

### `gen_kernel(func_op, ctx)`

功能说明：

- 将单个优化后的 MLIR `func.func` 生成为完整的目标后端函数源码文本。

参数说明：

- `func_op`（`object`）：待生成的 MLIR `func.func`。
- `ctx`（`EmitCContext`）：由 `emit_c` 定义并复用的源码生成上下文。

使用示例：

```python
from kernel_gen.dsl.emit_c import EmitCContext
from kernel_gen.dsl.gen_kernel import gen_kernel

source = gen_kernel(func_op, EmitCContext(target="cpu"))
```

注意事项：

- `func_op` 必须已经完成本仓库要求的合法化。
- 若 IR 中仍含未支持 op，必须向上抛出对应失败原因。

返回与限制：

- 返回类型：`str`。
- 返回语义：完整目标后端函数源码文本。
- 限制条件：仅支持当前 target 下可映射的 IR 子集。

### `gen_signature(func_op, ctx)`

功能说明：

- 根据 `func.func` 的输入输出类型生成目标后端函数签名。

参数说明：

- `func_op`（`object`）：待分析的 MLIR `func.func`。
- `ctx`（`EmitCContext`）：源码生成上下文。

使用示例：

```python
from kernel_gen.dsl.gen_kernel import gen_signature

signature = gen_signature(func_op, ctx)
```

注意事项：

- `Memory` 输入参数在当前恢复范围内必须生成为只读输入参数形式。
- `Memory` 结果在当前恢复范围内必须生成为显式 `out` 输出参数，而不是直接函数返回值。
- 不支持的返回形式必须明确报错。
- 参数名来自 `func.func` 的 `arg_attrs.name`；缺失或为空时必须使用 `arg{index}` 默认命名，保持与 `func.func` 参数顺序一致。

返回与限制：

- 返回类型：`str`。
- 返回语义：不含函数体的函数签名文本。
- 限制条件：签名生成必须与 `gen_kernel(...)`、`gen_body(...)` 的结果保持一致。

### `gen_body(func_op, ctx)`

功能说明：

- 按 `func.func` 中 block 与 op 的顺序遍历函数体，并调用 `emit_c` 规则生成函数体文本。

参数说明：

- `func_op`（`object`）：待遍历的 MLIR `func.func`。
- `ctx`（`EmitCContext`）：源码生成上下文。

使用示例：

```python
from kernel_gen.dsl.gen_kernel import gen_body

body = gen_body(func_op, ctx)
```

注意事项：

- 必须保持 IR 中 op 的语义顺序。
- `func.return` 在当前恢复范围下仅支持无返回或 `Memory` 结果写回 `out`。
- 不得在本层引入未在 `emit_c` 中定义的单 op 生成特例。
- 当 `func.return` 回写 `out` 的值未在 `EmitCContext` 中绑定名称，且该值为 `BlockArgument` 时，必须回退为 `arg{index}` 默认命名以保持与 `gen_signature` 一致。

返回与限制：

- 返回类型：`str`。
- 返回语义：函数体文本，不含函数签名。
- 限制条件：局部命名与片段生成策略必须与 `EmitCContext` 中状态保持一致。

## 测试

- 测试文件：[`test/dsl/test_gen_kernel.py`](../../test/dsl/test_gen_kernel.py)
- 执行命令：`pytest -q test/dsl/test_gen_kernel.py`

### 测试目标

- 验证 `func.func` 到完整目标后端函数源码的生成能力。
- 验证签名生成与函数体拼装的职责边界清晰。
- 验证 `Memory` 输入/输出参数规则、参数顺序、错误传播与名称保持行为。

### 功能与用例清单

- GK-001：可将单个优化后的 `func.func` 生成为完整后端函数源码。（`test_gen_kernel_returns_target_source`）
- GK-002：输入 `Memory` 参数生成只读输入参数。（`test_gen_signature_uses_readonly_memory_inputs`）
- GK-003：`Memory` 结果生成为显式输出参数。（`test_gen_signature_lowers_memory_result_to_out_param`）
- GK-004：标量参数顺序与 IR 参数顺序一致，缺失命名时使用 `arg{index}` 默认命名。（`test_gen_signature_preserves_scalar_arg_order`）
- GK-005：函数体按 op 顺序调用 `emit_c` 规则，回写 `out` 时保持 `gen_signature` 的默认命名规则。（`test_gen_body_emits_ops_in_order`）
- GK-006：循环片段可正确拼装到完整函数中。（`test_gen_kernel_assembles_loop_body`）
- GK-007：`emit_c` 错误向上抛出并保留失败原因。（`test_gen_kernel_propagates_emit_c_error`）
- GK-008：不支持的返回形式或输入类型明确报错。（`test_gen_signature_rejects_unsupported_return_form`）
- GK-009：生成源码保留函数名与已命名参数名；当 `gen_signature` 可观察到输入参数缺失 `arg_attrs.name` 时，生成源码沿用 `arg{index}` 默认名。（`test_gen_kernel_preserves_function_and_arg_names`）
