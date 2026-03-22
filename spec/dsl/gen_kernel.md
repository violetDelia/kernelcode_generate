# gen_kernel.md

## 功能简介

- 定义将优化后的 MLIR `func.func` 转换为目标后端源码的规则。
- 组织函数签名生成、函数体遍历与 [`spec/dsl/emit_c.md`](../../spec/dsl/emit_c.md) 中定义的单 op 生成规则，输出完整函数源码。
- 约束生成结果的函数签名、参数顺序、输出参数风格与 [`spec/include/api`](../../spec/include/api) 中的 API 规范保持一致。

## 文档信息

- 创建者：`榕`
- 最后一次更改：`榕`
- `spec`：[`spec/dsl/gen_kernel.md`](../../spec/dsl/gen_kernel.md)
- `功能实现`：[`kernel_gen/dsl/gen_kernel.py`](../../kernel_gen/dsl/gen_kernel.py)
- `test`：[`test/dsl/test_gen_kernel.py`](../../test/dsl/test_gen_kernel.py)

## 依赖

- MLIR 函数生成入口：[`spec/dsl/mlir_gen.md`](../../spec/dsl/mlir_gen.md)
- 单 op 源码生成规则：[`spec/dsl/emit_c.md`](../../spec/dsl/emit_c.md)
- 统一 API 规范：[`spec/include/api/Core.md`](../../spec/include/api/Core.md)
- 统一内存视图 API：[`spec/include/api/Memory.md`](../../spec/include/api/Memory.md)
- 统一算子 API：[`spec/include/api/Nn.md`](../../spec/include/api/Nn.md)

## 术语

- `IR 函数`：本仓库生成并经过优化 pass 处理后的 MLIR `func.func`。
- `目标后端源码`：由 `gen_kernel` 输出的完整函数级后端源码文本，例如 C++、CUDA、其他目标代码。
- `API 对齐`：生成函数的签名、参数含义、输出约定与 `spec/include/api` 中定义的接口语义一致。
- `EmitCContext`：由 [`spec/dsl/emit_c.md`](../../spec/dsl/emit_c.md) 定义的源码片段生成上下文，同时作为函数级源码生成上下文复用。

## 目标

- 为优化后的 MLIR `func.func` 提供稳定的函数级后端源码生成能力。
- 统一约束函数签名、参数布局、返回约定与函数体拼装规则。
- 通过调用 `emit_c` 的片段生成接口，保证函数体生成过程可组合、可维护。
- 保证生成的函数接口可直接对齐本仓库 `include/api` 规范。

## 限制与边界

- 输入必须是单个优化后的 MLIR `func.func`，不负责生成 `builtin.module`、构建脚本或完整工程目录。
- 不负责 AST 解析，不负责从 Python 函数直接生成后端源码。
- 不负责优化 pass；输入 IR 应视为已经完成合法化与必要优化。
- 不负责定义单个 op 到源码片段的细节规则；这些规则由 `emit_c` 负责。
- 不绑定某一个特定后端；同一套接口应允许针对不同 target 生成不同源码。
- 输出源码不能引入与目标 API 规范冲突的命名空间、异常机制或额外公开接口。
- `gen_kernel` 只描述完整函数源码生成规则，不负责文件写盘、编译、链接、运行与性能调优。
- 对于无法映射到目标后端源码的 IR，必须在生成阶段明确报错，不能静默降级或跳过。

## 公开接口

### `gen_kernel(func_op, ctx)`

功能说明：

- 将单个优化后的 MLIR `func.func` 生成为完整的目标后端函数源码文本。
- 内部依次完成签名生成、函数体遍历、调用 `emit_c_op`/`emit_c_value` 生成片段并拼装输出。

参数说明：

- `func_op` (`object`)：待生成的 MLIR `func.func`。
- `ctx` (`EmitCContext`)：由 `emit_c` 定义并复用的源码生成上下文。

使用示例：

```python
source = gen_kernel(func_op, EmitCContext(target="cpu"))
```

注意事项：

- 输入 `func_op` 必须已经通过本仓库 IR 合法性约束。
- 若 IR 中仍含未支持 op，必须报错并指出具体 op。
- 生成结果是单个函数对应的完整后端源码文本，不自动附带完整工程文件。

返回与限制：

- 返回类型：`str`。
- 返回语义：返回单个函数的完整目标后端源码文本。
- 限制条件：仅支持可映射到当前 `target` 的 IR 子集。

### `gen_signature(func_op, ctx)`

功能说明：

- 根据 MLIR `func.func` 的输入输出类型生成目标后端函数签名。
- 保证参数顺序、只读属性与输出参数风格符合 `spec/include/api` 约束。

参数说明：

- `func_op` (`object`)：待分析的 MLIR `func.func`。
- `ctx` (`EmitCContext`)：由 `emit_c` 定义并复用的源码生成上下文。

使用示例：

```python
signature = gen_signature(func_op, ctx)
```

注意事项：

- 当 IR 返回单个或多个 `Memory` 结果时，应优先转换为显式输出参数，而不是直接以函数返回值返回张量对象。
- 标量返回值是否允许保留为函数返回值，取决于目标后端对应 API 规范；若无对应规范，默认也应转为显式输出参数或报错。

返回与限制：

- 返回类型：`str`。
- 返回语义：返回不含函数体的函数签名文本。
- 限制条件：签名生成必须与 `gen_kernel` 的函数体结果保持一致。

### `gen_body(func_op, ctx)`

功能说明：

- 按 MLIR `func.func` 中 block 与 op 的顺序遍历函数体。
- 调用 `emit_c` 中定义的片段生成规则，拼装完整函数体文本。

参数说明：

- `func_op` (`object`)：待遍历的 MLIR `func.func`。
- `ctx` (`EmitCContext`)：由 `emit_c` 定义并复用的源码生成上下文。

使用示例：

```python
body = gen_body(func_op, ctx)
```

注意事项：

- 必须保持 op 的语义顺序。
- 不得在本层引入未在 `emit_c` 中定义的单 op 生成特例。

返回与限制：

- 返回类型：`str`。
- 返回语义：返回函数体文本，不含函数签名。
- 限制条件：函数体中的片段命名与局部变量策略必须与 `EmitCContext` 中的状态保持一致。

## 额外补充

### 与 `emit_c` 的职责关系

- `emit_c` 负责“单个 MLIR op/value 如何生成目标源码片段”。
- `gen_kernel` 负责“如何基于同一个 `EmitCContext`，把这些片段组织成完整函数源码”。
- 这组关系应与 `emit_mlir` 和 `mlir_gen` 的关系保持一致：
  - `emit_mlir` 负责节点级规则。
  - `mlir_gen` 负责函数级组织与输出 `func.func`。

### 签名生成约束

- 生成函数签名时，必须以 `spec/include/api` 为准。
- 对 `Memory` 类型参数：
  - 输入只读张量应生成目标后端的只读输入参数形式。
  - 输出张量应生成目标后端的显式输出参数形式。
- 对标量参数：
  - 使用与 IR 标量类型一致、且满足目标后端约束的目标类型。
  - 参数顺序必须与 `func.func` 参数顺序一致。
- 若 IR 中的返回值可以等价改写为输出参数，则应优先生成显式输出参数风格接口。

### 错误处理约束

- 不支持的函数签名映射、非法返回形式、未知 op 或无法组织成合法函数体的情况，都必须在函数级生成阶段报错。
- 错误信息至少应包含：函数名、失败原因、相关 op 名称或位置。

## 测试

- 测试文件：[`test/dsl/test_gen_kernel.py`](../../test/dsl/test_gen_kernel.py)
- 执行命令：`pytest -q test/dsl/test_gen_kernel.py`
- 测试目标：
  - 验证 MLIR `func.func` 到目标后端完整函数源码的生成能力。
  - 验证生成签名与 `spec/include/api` 约束一致。
  - 验证 `gen_kernel` 与 `emit_c` 的职责边界清晰。
- 功能与用例清单：
  - GK-001：可将单个优化后的 `func.func` 生成为完整后端函数源码。（`test_gen_kernel_returns_target_source`）
  - GK-002：输入 `Memory` 参数可生成目标后端只读输入参数。（`test_gen_signature_uses_readonly_memory_inputs`）
  - GK-003：结果 `Memory` 可生成为显式输出参数。（`test_gen_signature_lowers_memory_result_to_out_param`）
  - GK-004：标量参数顺序与 IR 参数顺序一致。（`test_gen_signature_preserves_scalar_arg_order`）
  - GK-005：函数体生成按 op 顺序调用 `emit_c` 规则。（`test_gen_body_emits_ops_in_order`）
  - GK-006：`scf.for` 函数体片段可正确拼装到完整函数中。（`test_gen_kernel_assembles_loop_body`）
  - GK-007：不支持 op 时向上抛出带 op 名称的错误。（`test_gen_kernel_propagates_emit_c_error`）
  - GK-008：不合法返回形式时报错。（`test_gen_signature_rejects_unsupported_return_form`）
  - GK-009：生成源码中函数名、参数名与 IR 定义保持一致。（`test_gen_kernel_preserves_function_and_arg_names`）
