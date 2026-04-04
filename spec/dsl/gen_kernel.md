# gen_kernel.md

## 功能简介

- 定义将单个优化后的 MLIR op / `func.func` 转换为目标源码文本的规则。
- 对 `func.func` 负责函数签名生成、按 IR 顺序遍历函数体，并逐个调用 [`spec/dsl/emit_c.md`](../../spec/dsl/emit_c.md) 中定义的节点级公开发射接口。
- 对 `func.func` 的 rewrite-after-IR CPU kernel、`conv2d_img2col2d_tiled(...)`、`npu_demo` body-level kernel 等函数级特化，必须通过统一 emitter 内部策略选择收口。
- 对单个普通 op 直接复用 `emit_c` 的节点级公开接口返回源码片段；不负责文件写盘、编译、链接或运行。

## 文档信息

- 创建者：`摸鱼小分队`
- 最后一次更改：`jcc你莫辜负`
- `spec`：[`spec/dsl/gen_kernel.md`](../../spec/dsl/gen_kernel.md)
- `功能实现`：[`kernel_gen/dsl/gen_kernel.py`](../../kernel_gen/dsl/gen_kernel.py)
- `test`：[`test/dsl/test_gen_kernel.py`](../../test/dsl/test_gen_kernel.py)

## 依赖

- [`spec/dsl/mlir_gen.md`](../../spec/dsl/mlir_gen.md)：优化后 `func.func` 的来源。
- [`spec/dsl/emit_c.md`](../../spec/dsl/emit_c.md)：单个 op/value 的源码片段生成规则。
- [`kernel_gen/dsl/gen_kernel.py`](../../kernel_gen/dsl/gen_kernel.py)：函数级源码生成实现。
- [`test/dsl/test_gen_kernel.py`](../../test/dsl/test_gen_kernel.py)：函数级源码生成测试。

## 目标

- 为优化后的单个 MLIR op / `func.func` 提供稳定的目标源码生成能力。
- 对 `func.func` 统一约束签名、参数顺序、输出参数风格、IR 顺序遍历与函数体拼装规则。
- 明确支持：只读 `Memory` 输入、rewrite 后前置 `arg0/arg1/...` memory 参数作为显式输出参数、标量参数顺序与默认命名保持、`emit_c` 错误向上抛出。
- 明确支持：`f32/f64` 类型在 `target=cpu` 下映射为 `float/double`，用于 `Memory<float>/Memory<double>` 与 `float/double` 标量参数生成。
- 冻结 `target=cpu` 的 rewrite-after-IR 合同：`gen_kernel(...)` 只接受已经经过 `BufferResultsToOutParamsPass` 的 lowered IR；默认 CPU 路径不再从旧 `memory return` ABI 隐式推导 `out`。
- 冻结 `target="npu_demo"` 的函数级 body-level kernel 骨架：签名包含 `npu_demo::KernelContext& ctx`，函数体按 `thread_id/thread_num -> TSM/TLM dynamic memory -> view -> slice -> add -> deslice` 的顺序组织。
- 支持单一非 `Memory` 标量返回生成函数返回值文本；`!symbol.int<"...">` 仍固定为 `target=cpu` 路径。
- 对 `conv_cpu_tiled_v1` 当前子集，冻结 `conv2d_img2col2d_tiled(...)` 的函数级 CPU 骨架：固定 `Ntile=1`、`Ctile=16`、`Ftile=16`、`Hotile=16`、`Wotile=16`，包含外层分块循环、tile-local `col_buffer/acc_buffer`、`cpu::img2col2d(...)` 调用与最终写回 `out`。

## 限制与边界

- 输入必须是单个优化后的 MLIR `func.func`，或单个当前 target 下可发射的普通 op；不负责 `builtin.module` 级组织。
- 不负责 AST 解析、MLIR 构造、优化 pass、文件写盘、编译、链接、运行或性能调优。
- 不负责定义单个 op/value 的代码生成细节；这些由 [`spec/dsl/emit_c.md`](../../spec/dsl/emit_c.md) 负责。
- 输出源码必须保持函数名、参数名与 IR 定义一致，不能引入额外公开接口。
- 对于不支持的返回形式、未知 op 或无法映射到目标后端源码的 IR，必须明确报错。
- `func.return` / `out` 绑定不属于普通 `emit_c_op(...)` 的公开职责；`func.return` 只能在 `func.func` 的函数级主遍历流程中收尾处理。
- 默认路径下，旧 `memory return` ABI 必须显式失败并提示先运行 `BufferResultsToOutParamsPass`；不允许继续从 `func.return %mem` 或函数返回类型里偷推 `out`。
- rewrite 后 IR 中，只有最前面连续且由 `arg_attrs.name` 显式标记为 `arg0/arg1/...` 的 `Memory` 参数才视为 out 参数；其余 `Memory` 参数仍视为只读输入。
- `target="npu_demo"` 当前只冻结 body-level kernel 骨架，不定义 host wrapper、`launch`、`arch.launch_kernel`、`barrier` 或其他运行时调度骨架。
- `target="npu_demo"` 的目标终态不得回退到 `.view<T>()`、`load<...>`、`store<...>` 或表达式式 `auto tile = slice(source, ...)`。
- 对 `conv2d_img2col2d_tiled(...)` 这一固定 CPU 子集，不允许把函数级结构写成“由实现决定”“结构自定”或“必要时改走 kernel dialect”；函数骨架、tile 常量、循环层次、局部 buffer 与 `out` 写回都必须在本层直接冻结。

## 公开接口

### `gen_kernel(op_or_func, ctx)`

功能说明：

- 将单个优化后的 MLIR `func.func` 生成为完整的目标后端函数源码文本，或将单个普通 op 生成为节点级源码片段。
- 这是 `kernel_gen.dsl.gen_kernel` 唯一稳定公开入口；下游和测试主口径只允许稳定依赖 `gen_kernel(...)` 与错误类型 `GenKernelError`。
- 函数级签名拼装、IR 主遍历与 `func.return` 收尾仅可作为模块内部实现拆分继续存在，不再属于公开稳定接口。

参数说明：

- `op_or_func`（`object`）：待生成的 MLIR `func.func` 或单个普通 op。
- `ctx`（`EmitCContext`）：由 `emit_c` 定义并复用的源码生成上下文。

使用示例：

```python
from kernel_gen.dsl.emit_c import EmitCContext
from kernel_gen.dsl.gen_kernel import gen_kernel

source = gen_kernel(func_op, EmitCContext(target="cpu"))
```

注意事项：

- `func.func` 输入必须已经完成本仓库要求的合法化。
- 若输入为普通 op，则直接委托 `emit_c_op(...)` 的公开节点级接口发射，不补额外函数级前后文。
- `func.return` 不允许作为单独普通 op 走这条公开接口；它的 `out` 绑定与返回语义必须留在 `func.func` 的主遍历流程中处理。
- 若 IR 中仍含未支持 op，必须向上抛出对应失败原因。

返回与限制：

- 返回类型：`str`。
- 返回语义：输入为 `func.func` 时返回完整目标后端函数源码文本；输入为普通 op 时返回该 op 的节点级源码片段。
- 限制条件：仅支持当前 target 下可映射的 IR 子集；`func.return` 只允许在函数级主遍历路径中处理。

## 函数级主遍历规则（非公开稳定接口）

### 函数签名拼装

功能说明：

- 当输入为 `func.func` 时，内部流程必须先根据输入输出类型拼装目标函数签名。
- 这一步只服务于 `gen_kernel(...)` 的函数级主流程；实现可使用 `_gen_signature(...)` 一类私有 helper，但不得把它们暴露成公开稳定接口。

注意事项：

- rewrite 后 IR 中，最前面连续的显式 `arg0/arg1/...` memory 参数必须生成为非 `const` 的 `Memory<...>&` 输出参数；其余 `Memory` 输入参数保持 `const Memory<...>&`。
- 默认 CPU 路径不再接受 `-> (!nn.memory<...>)` 这类旧返回 ABI；memory 输出必须已经在 IR 中前移成参数。
- rewrite 后 `kernel.add` 的完整目标源码形态可接近以下形式：

```cpp
void add(Memory<int32_t>& arg0, const Memory<int32_t>& arg1, const Memory<int32_t>& arg2) {
    cpu::add(arg1, arg2, arg0);
}
```

- `target="npu_demo"` 的 body-level kernel 签名必须把 `npu_demo::KernelContext& ctx` 作为首个参数，随后依次保留只读 `Memory` 输入与显式 `Memory` 输出参数。
- `target="npu_demo"` 的完整目标签名形态可接近以下形式：

```cpp
void demo_kernel(
    npu_demo::KernelContext& ctx,
    const Memory<float>& source,
    Memory<float>& out) {
    /* body-level skeleton */
}
```

- 单一非 `Memory` 结果生成为函数返回值，不生成 `out` 参数；其中 `!symbol.int<"...">` 在 `target=cpu` 下映射为 `long long`。
- 不支持的返回形式必须明确报错。
- 参数名来自 `func.func` 的 `arg_attrs.name`；缺失或为空时必须使用 `arg{index}` 默认命名，保持与 `func.func` 参数顺序一致。

### IR 顺序遍历与收尾绑定

功能说明：

- 当输入为 `func.func` 时，内部流程必须按 `func.func` 中 block 与 op 的顺序遍历函数体。
- 在进入具体 body 发射前，实现必须先在单一 emitter 内部选择函数级策略，统一承接默认路径与当前已冻结的函数级特化。
- 非 `func.return` 的普通 op 必须逐个委托 `emit_c_op(...)` 的公开节点级接口发射。
- `func.return` / `out` 绑定属于函数级主遍历流程的收尾逻辑，不得作为普通 `emit_c_op(...)` 公开职责泄露给下游。

注意事项：

- 必须保持 IR 中 op 的语义顺序。
- 上述函数级策略只允许作为 emitter 内部实现细节存在；不得再扩成新的公开入口、公开 helper 或测试主口径。
- `func.return` 在默认 rewrite-after-IR 路径下仅支持无返回或单一非 `Memory` 标量返回；若仍返回 `Memory`，必须显式报错。
- 不得在本层引入未在 `emit_c` 中定义的单 op 生成特例。
- `target=cpu` 下的 lowered add 成功链路必须来自 `LowerNnToKernelPass -> BufferResultsToOutParamsPass` 之后的 rewrite 后 IR，例如：

```cpp
cpu::add(arg1, arg2, arg0);
cpu::add(arg1, v0, arg0);
```

- 不允许从旧 `func.return %mem`、旧 `function_type.outputs` 或隐式 alias 回退到 `out = tmp`、`return tmp` 或其他 generic fallback。
- `target="npu_demo"` 的 body-level kernel 骨架必须包含并保持如下顺序：

```cpp
void demo_kernel(
    npu_demo::KernelContext& ctx,
    const Memory<float>& source,
    Memory<float>& out) {
    long long tid = ctx.thread_id();
    long long tnum = ctx.thread_num();

    auto tsm = ctx.get_dynamic_memory<float>(MemorySpace::TSM);
    auto tlm = ctx.get_dynamic_memory<float>(MemorySpace::TLM);

    auto src_view = view(source, tid * 16, 16, 1);
    auto work_tile = view(tsm, 0, 16, 1);
    auto out_tile = view(tlm, 0, 16, 1);

    slice(work_tile, src_view, 0, 16, 1);
    add(work_tile, work_tile, out_tile);
    deslice(out_tile, out, tid * 16, 16, 1);
}
```

- 上述骨架顺序是 `thread_id/thread_num -> get_dynamic_memory(TSM/TLM) -> view -> slice -> add -> deslice`；不得插入 `launch(`、`arch.launch_kernel`、`barrier`、`.view<`、`load<`、`store<` 或表达式式 `slice(source, ...)`。
- 当 `func.return` 回写 `out` 的值未在 `EmitCContext` 中绑定名称，且该值为 `BlockArgument` 时，必须回退为 `arg{index}` 默认命名以保持与函数级签名一致。
- 当 `func.return` 返回 `!symbol.int<"...">` 时，必须生成 `return <expr>;` 并复用 `emit_c` 的命名/表达式规则。
- 对 `conv_cpu_tiled_v1` 子集，函数体骨架必须固定包含：`constexpr Ntile/Ctile/Ftile/Hotile/Wotile`、tile-local `col_buffer/acc_buffer`、`n -> f -> ho -> wo` 分块循环、循环体内的 `cpu::img2col2d(...)` 与 `c` 方向 tiled compute、以及最终写回 `out` 的显式循环或等价机械可判定写回语句。

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

- 验证单个普通 op 输入会直接复用 `emit_c_op(...)` 节点级公开接口。
- 验证 `func.func` 到完整目标后端函数源码的生成能力。
- 验证 `gen_kernel(...)` 的函数级主遍历与 `emit_c_op(...)` 的节点级职责边界清晰。
- 验证 `Memory` 输入/输出参数规则、参数顺序、错误传播与名称保持行为。
- 验证普通非 return op 会逐个委托到 `emit_c_op(...)`，且 `func.return/out` 绑定继续留在函数级主遍历流程中处理。
- 验证 rewrite 后单 output / mixed output memory 函数可被 `gen_kernel(...)` 消费，且源码只走前置 `arg0/arg1/...` out 参数 ABI。
- 验证 rewrite 后成功链路不再残留旧 `memory return` ABI；IR / 源码中都不再出现“返回 memory 再隐式推导 out”的路径。
- 验证 half-rewritten IR 会被 `gen_kernel(...)` 显式拒绝。
- 验证 rewrite 后的 lowered add 只通过黑盒 `gen_kernel(...)` 输出验证，不依赖内部 helper 或内部策略名。
- 验证 `target="npu_demo"` 的函数级 body-level kernel 骨架包含 `npu_demo::KernelContext& ctx`、`ctx.thread_id()`、`ctx.thread_num()`、`ctx.get_dynamic_memory<float>(MemorySpace::TSM/TLM)` 与 `view/slice/deslice/add` 的固定顺序。
- 验证 `target="npu_demo"` 的函数级骨架不回退到 `.view<`、`load<`、`store<`、表达式式 `slice(source, ...)`、`launch` 或 `barrier`。
- 验证非 `Memory` 标量返回的签名与函数体生成规则；其中 `!symbol.int<"...">` 仅允许 `target=cpu`。
- 对 `conv_cpu_tiled_v1` 下游实现阶段，验证 `conv2d_img2col2d_tiled(...)` 生成源码包含固定 tile 常量、`cpu::img2col2d(...)`、局部 `col_buffer/acc_buffer`、`n/f/ho/wo` 分块循环与最终写回 `out`。
- 注：`S3` 计划中的四个 direct-return `nn.add` 验收用例当前先冻结为本 spec 的下游待补测试映射；在 `test/dsl/test_gen_kernel.py` 实际落地前，不把它们写成“当前已存在的可执行测试”。
- 注：`N3` 计划中的 `npu_demo` 两个验收用例当前先冻结为本 spec 的下游待补测试映射；在 `test/dsl/test_gen_kernel.py` 实际落地前，不把它们写成“当前已存在的可执行测试”。

### 功能与用例清单

- GK-001A：单个普通 op 输入可直接复用 `emit_c` 节点级公开接口生成源码片段。（`test_gen_kernel_delegates_single_op_input_to_emit_c`）
- GK-001：可将单个优化后的 `func.func` 生成为完整后端函数源码。（`test_gen_kernel_returns_target_source`）
- GK-002：输入 `Memory` 参数生成只读输入参数。（`test_gen_kernel_uses_readonly_memory_inputs`）
- GK-003：rewrite 后单 output memory 函数可生成前置 `arg0` 输出参数签名。（`test_gen_kernel_accepts_rewritten_single_output_function`）
- GK-004：标量参数顺序与 IR 参数顺序一致，缺失命名时使用 `arg{index}` 默认命名。（`test_gen_kernel_uses_default_arg_names_when_missing_attrs`）
- GK-005：函数级主遍历按 IR 顺序发射普通 op。（`test_gen_kernel_emits_ops_in_order`）
- GK-005A：普通非 `func.return` 的 op 逐个委托到 `emit_c_op(...)`。（`test_gen_kernel_delegates_to_emit_c_for_non_return_ops`）
- GK-005B：`func.return/out` 绑定由函数级主遍历流程收尾，不走普通 `emit_c_op(...)` 公开职责。（`test_gen_kernel_handles_func_return_and_out_binding_in_main_flow`）
- GK-006：循环片段可正确拼装到完整函数中。（`test_gen_kernel_assembles_loop_body`）
- GK-007：`emit_c` 错误向上抛出并保留失败原因。（`test_gen_kernel_propagates_emit_c_error`）
- GK-008：不支持的返回形式或输入类型明确报错。（`test_gen_kernel_rejects_unsupported_return_form`）
- GK-009：生成源码保留函数名与已命名参数名；当函数级签名拼装观察到输入参数缺失 `arg_attrs.name` 时，生成源码沿用 `arg{index}` 默认名。（`test_gen_kernel_preserves_function_and_arg_names`）
- GK-010：`!symbol.int<"...">` 标量返回可生成函数返回值。（`test_gen_kernel_supports_symbol_scalar_return`）
- GK-011：非 cpu target 下 `!symbol.int<"...">` 标量返回必须报错，防止跨 target 误生成返回签名/函数体。（`test_gen_kernel_rejects_symbol_scalar_return_on_non_cpu`）
- GK-012：`f32/f64` 标量与 `Memory<f32/f64>` 可生成 `float/double` 与 `Memory<float>/Memory<double>` 形式签名。（`test_gen_kernel_supports_float32_scalar_and_memory`）
- GK-013：rewrite 后 `kernel.add(memory, memory)` 在 cpu target 下可生成 `Memory<int32_t>& arg0` 签名与 `cpu::add(arg1, arg2, arg0);` 函数体。（`test_gen_kernel_supports_lowered_nn_add_memory_memory_on_cpu`）
- GK-014：rewrite 后 `kernel.add(memory, const(i32))` 在 cpu target 下可生成 `cpu::add(arg1, v0, arg0);` 函数体。（`test_gen_kernel_supports_lowered_nn_add_memory_const_on_cpu`）
- GK-015：rewrite 后 `kernel.add(memory, symbol.int)` 在 cpu target 下可生成 `cpu::add(arg1, v0, arg0);` 函数体，并保留 `long long` 标量参数。（`test_gen_kernel_supports_lowered_nn_add_memory_symbol_on_cpu`）
- GK-016：rewrite 后 `memory + scalar` mixed output 函数中，memory 走前置 `arg0`，scalar 继续返回。（`test_gen_kernel_accepts_rewritten_mixed_output_function`）
- GK-017：`target="npu_demo"` 的最小 kernel 可生成包含 `npu_demo::KernelContext& ctx`、`ctx.thread_id()` 与 `ctx.thread_num()` 的 body-level 函数骨架。（下游待补测试映射：`test_gen_kernel_emits_npu_demo_body_level_kernel`）
- GK-018：`target="npu_demo"` 的 `view + slice + add + deslice` 链路可生成 `TSM/TLM` dynamic memory、`view(`、`slice(`、`add(`、`deslice(` 组成的函数体骨架，且不出现 `.view<`、`load<`、`store<`。（下游待补测试映射：`test_gen_kernel_emits_npu_demo_memory_pipeline`）
- GK-019：rewrite 后成功链路不再残留旧 memory return ABI。（`test_rewritten_pipeline_has_no_memory_return_abi_left`）
- GK-020：half-rewritten IR 会被 `gen_kernel(...)` 显式拒绝。（`test_rewritten_pipeline_fails_on_half_rewritten_ir`）
- GK-021：rewrite 后 lowered add、`conv2d_img2col2d_tiled(...)`、`npu_demo` body-level kernel 三类函数级形态继续只通过黑盒 `gen_kernel(...)` 验证源码合同；测试不得直接依赖内部 helper、内部策略函数或内部策略名。（`test_gen_kernel_black_box_direct_return_nn_add_conv2d_img2col2d_tiled_and_npu_demo_contracts`）

### C2 下游验收标准

- GK-C2-001：静态 shape 的 `conv2d_img2col2d_tiled(...)` 可生成包含 `cpu::img2col2d(`、`Ntile = 1`、`Ctile = 16`、`Ftile = 16`、`Hotile = 16`、`Wotile = 16` 的 CPU 源码，并可编译运行。（`test_gen_kernel_compiles_conv2d_img2col2d_tiled_cpu_smoke`）
- GK-C2-002：同一静态 shape case 的生成源码中必须可机械判断存在最终写回 `out` 的语句或显式循环。（`test_gen_kernel_writes_back_conv_output_tile`）
