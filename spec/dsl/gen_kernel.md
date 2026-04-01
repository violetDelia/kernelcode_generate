# gen_kernel.md

## 功能简介

- 定义将优化后的 MLIR `func.func` 转换为目标后端完整函数源码的规则。
- 负责函数签名生成、函数体遍历，以及调用 [`spec/dsl/emit_c.md`](../../spec/dsl/emit_c.md) 中定义的节点级生成规则。
- 输出完整函数源码文本，但不负责文件写盘、编译、链接或运行。

## 文档信息

- 创建者：`摸鱼小分队`
- 最后一次更改：`朽木露琪亚`
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
- 明确支持：`f32/f64` 类型在 `target=cpu` 下映射为 `float/double`，用于 `Memory<float>/Memory<double>` 与 `float/double` 标量参数生成。
- 支持 `!symbol.int<"...">` 标量返回在 `target=cpu` 下生成函数返回值文本。
- 对 `conv_cpu_tiled_v1` 当前子集，冻结 `conv2d_img2col2d_tiled(...)` 的函数级 CPU 骨架：固定 `Ntile=1`、`Ctile=16`、`Ftile=16`、`Hotile=16`、`Wotile=16`，包含外层分块循环、tile-local `col_buffer/acc_buffer`、`cpu::img2col2d(...)` 调用与最终写回 `out`。

## 限制与边界

- 输入必须是单个优化后的 MLIR `func.func`；不负责 `builtin.module` 级组织。
- 不负责 AST 解析、MLIR 构造、优化 pass、文件写盘、编译、链接、运行或性能调优。
- 不负责定义单个 op/value 的代码生成细节；这些由 [`spec/dsl/emit_c.md`](../../spec/dsl/emit_c.md) 负责。
- 输出源码必须保持函数名、参数名与 IR 定义一致，不能引入额外公开接口。
- 对于不支持的返回形式、未知 op 或无法映射到目标后端源码的 IR，必须明确报错。
- 除 `Memory` 结果外，仅允许单一 `!symbol.int<"...">` 标量结果生成返回值；其他非 `Memory` 结果仍需报错。
- 对 `conv2d_img2col2d_tiled(...)` 这一固定 CPU 子集，不允许把函数级结构写成“由实现决定”“结构自定”或“必要时改走 kernel dialect”；函数骨架、tile 常量、循环层次、局部 buffer 与 `out` 写回都必须在本层直接冻结。

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
- `!symbol.int<"...">` 结果在 `target=cpu` 下生成为 `long long` 返回值，不生成 `out` 参数。
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
- `func.return` 在当前恢复范围下仅支持无返回、`Memory` 结果写回 `out`，或 `!symbol.int<"...">` 标量返回。
- 不得在本层引入未在 `emit_c` 中定义的单 op 生成特例。
- 当 `func.return` 回写 `out` 的值未在 `EmitCContext` 中绑定名称，且该值为 `BlockArgument` 时，必须回退为 `arg{index}` 默认命名以保持与 `gen_signature` 一致。
- 当 `func.return` 返回 `!symbol.int<"...">` 时，必须生成 `return <expr>;` 并复用 `emit_c` 的命名/表达式规则。
- 对 `conv_cpu_tiled_v1` 子集，函数体骨架必须固定包含：`constexpr Ntile/Ctile/Ftile/Hotile/Wotile`、tile-local `col_buffer/acc_buffer`、`n -> f -> ho -> wo` 分块循环、循环体内的 `cpu::img2col2d(...)` 与 `c` 方向 tiled compute、以及最终写回 `out` 的显式循环或等价机械可判定写回语句。

返回与限制：

- 返回类型：`str`。
- 返回语义：函数体文本，不含函数签名。
- 限制条件：局部命名与片段生成策略必须与 `EmitCContext` 中状态保持一致。

## CPU `conv2d_img2col2d_tiled(...)` 固定骨架

### 适用范围

- 本节只适用于 `target=cpu` 的 `conv_cpu_tiled_v1` 子集。
- `emit_c` 已冻结 `img2col2d + DMA + tiled compute` 的节点级语句；`gen_kernel` 负责把这些节点拼成完整函数级骨架。
- 本节定义的目标不是“示意结构”，而是当前应冻结的函数级公开口径；后续实现不得改写为 `kernel dialect` 中转或旁路 codegen 文件。

### 目标结构

功能说明：

- 当优化后的 `func.func` 表达 `conv2d_img2col2d_tiled(...)` 时，`gen_kernel` 必须生成固定 tile 常量、固定外层循环层次、局部 `col_buffer/acc_buffer` 与最终写回 `out` 的完整 CPU 函数骨架。

使用示例：

```cpp
void conv2d_img2col2d_tiled(
    const Memory<float>& input,
    const Memory<float>& weight,
    Memory<float>& out) {
    constexpr long long Ntile = 1;
    constexpr long long Ctile = 16;
    constexpr long long Ftile = 16;
    constexpr long long Hotile = 16;
    constexpr long long Wotile = 16;

    float col_buffer[/* tile-local img2col */];
    float acc_buffer[/* tile-local output */];

    for (long long n0 = 0; n0 < out.shape()[0]; n0 += Ntile) {
        for (long long f0 = 0; f0 < out.shape()[1]; f0 += Ftile) {
            for (long long ho0 = 0; ho0 < out.shape()[2]; ho0 += Hotile) {
                for (long long wo0 = 0; wo0 < out.shape()[3]; wo0 += Wotile) {
                    cpu::img2col2d(input_tile, col_tile, 3, 3, 1, 1, 1, 1, 0, 0, 0, 0);
                    for (long long c0 = 0; c0 < weight.shape()[1]; c0 += Ctile) {
                        /* tiled compute */
                    }
                    for (long long fi = 0; fi < Ftile; ++fi) {
                        for (long long hi = 0; hi < Hotile; ++hi) {
                            for (long long wi = 0; wi < Wotile; ++wi) {
                                long long out_indices[4] = {n0, f0 + fi, ho0 + hi, wo0 + wi};
                                out.at(out_indices) = acc_buffer[((fi * Hotile) + hi) * Wotile + wi];
                            }
                        }
                    }
                }
            }
        }
    }
}
```

注意事项：

- `Ntile/Ctile/Ftile/Hotile/Wotile` 必须固定为 `1/16/16/16/16`，并以 `constexpr long long` 形式出现在生成源码中；不能写成“由实现自行选择”或“按 target 自适应”。
- 外层循环层次必须固定为 `n -> f -> ho -> wo` 的 tile 循环；`c` 方向 tiled compute 位于 `cpu::img2col2d(...)` 之后、最终写回 `out` 之前。
- 局部 buffer 必须至少包含 tile-local `col_buffer` 与 tile-local `acc_buffer`；它们服务于当前 tile 的中间展开与输出累积，不能省略成“临时变量若干”。
- `out` 写回必须是函数级硬约束，生成源码中必须可机械判断存在最终写回 `out` 的语句或显式循环；不能只生成 `acc_buffer` 或局部 `Memory` 而没有写回。
- `cpu::img2col2d(...)` 的节点级调用由 [`spec/dsl/emit_c.md`](../../spec/dsl/emit_c.md) 负责，但本层必须把它安放在上述固定循环骨架中，不得改走 `kernel dialect`、`launch(...)`、`arch.launch_kernel(...)` 或其他旁路结构。

## 测试

- 测试文件：[`test/dsl/test_gen_kernel.py`](../../test/dsl/test_gen_kernel.py)
- 执行命令：`pytest -q test/dsl/test_gen_kernel.py`

### 测试目标

- 验证 `func.func` 到完整目标后端函数源码的生成能力。
- 验证签名生成与函数体拼装的职责边界清晰。
- 验证 `Memory` 输入/输出参数规则、参数顺序、错误传播与名称保持行为。
- 验证 `!symbol.int<"...">` 标量返回的签名与函数体生成规则。
- 验证 `!symbol.int<"...">` 标量返回仅允许 `target=cpu`；非 cpu target 必须报错。
- 对 `conv_cpu_tiled_v1` 下游实现阶段，验证 `conv2d_img2col2d_tiled(...)` 生成源码包含固定 tile 常量、`cpu::img2col2d(...)`、局部 `col_buffer/acc_buffer`、`n/f/ho/wo` 分块循环与最终写回 `out`。

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
- GK-010：`!symbol.int<"...">` 标量返回可生成函数返回值。（`test_gen_kernel_supports_symbol_scalar_return`）
- GK-011：非 cpu target 下 `!symbol.int<"...">` 标量返回必须报错，防止跨 target 误生成返回签名/函数体。（`test_gen_kernel_rejects_symbol_scalar_return_on_non_cpu`）
- GK-012：`f32/f64` 标量与 `Memory<f32/f64>` 可生成 `float/double` 与 `Memory<float>/Memory<double>` 形式签名。（`test_gen_signature_supports_float32_scalar_and_memory`）

### C2 下游验收标准

- GK-C2-001：静态 shape 的 `conv2d_img2col2d_tiled(...)` 可生成包含 `cpu::img2col2d(`、`Ntile = 1`、`Ctile = 16`、`Ftile = 16`、`Hotile = 16`、`Wotile = 16` 的 CPU 源码，并可编译运行。（`test_gen_kernel_compiles_conv2d_img2col2d_tiled_cpu_smoke`）
- GK-C2-002：同一静态 shape case 的生成源码中必须可机械判断存在最终写回 `out` 的语句或显式循环。（`test_gen_kernel_writes_back_conv_output_tile`）
