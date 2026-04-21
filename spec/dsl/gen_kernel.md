# gen_kernel.md

## 功能简介

- 定义将单个优化后的 MLIR op / `func.func` 转换为目标源码文本的规则。
- 对 `func.func` 负责函数签名生成、按 IR 顺序遍历函数体，并逐个调用 [`spec/dsl/emit_c.md`](../../spec/dsl/emit_c.md) 中定义的节点级公开发射接口。
- 对 `func.func` 的 rewrite-after-IR CPU kernel、`conv2d_img2col2d_tiled(...)`、以及 `target="npu_demo"` 的“launch wrapper + body kernel”受控 module 子集等函数级特化，必须通过统一 emitter 内部策略选择收口。
- 对已经过 tile family 的 split-after-IR 单函数输入，明确 `gen_kernel(...)` 的黑盒 codegen 合同：tile 因子由 `tuner.param : !symbol.int<"...">` 驱动、`symbol.for` 保留显式分块、malformed tile IR 必须显式失败。
- 对单个普通 op 直接复用 `emit_c` 的节点级公开接口返回源码片段；不负责文件写盘、编译、链接或运行。

## 文档信息

- 创建者：`摸鱼小分队`
- 最后一次更改：`金铲铲大作战`（2026-04-21）
- `spec`：[`spec/dsl/gen_kernel.md`](../../spec/dsl/gen_kernel.md)
- `功能实现`：[`kernel_gen/dsl/gen_kernel.py`](../../kernel_gen/dsl/gen_kernel.py)
- `test`：[`test/dsl/test_gen_kernel.py`](../../test/dsl/test_gen_kernel.py)

## 依赖

- [`spec/dsl/mlir_gen.md`](../../spec/dsl/mlir_gen.md)：优化后 `func.func` 的来源。
- [`spec/dsl/emit_c.md`](../../spec/dsl/emit_c.md)：单个 op/value 的源码片段生成规则。
- [`spec/include/api/Kernel.md`](../../spec/include/api/Kernel.md)：`target=npu_demo` 下 `Kernel` helper 的唯一公共接口合同。
- [`kernel_gen/dsl/gen_kernel.py`](../../kernel_gen/dsl/gen_kernel.py)：函数级源码生成实现。
- [`test/dsl/test_gen_kernel.py`](../../test/dsl/test_gen_kernel.py)：函数级源码生成测试。

## 目标

- 为优化后的单个 MLIR op / `func.func` 提供稳定的目标源码生成能力。
- 对 `func.func` 统一约束签名、参数顺序、输出参数风格、IR 顺序遍历与函数体拼装规则。
- 明确支持：只读 `Memory` 输入、rewrite 后前置 `arg0/arg1/...` memory 参数作为显式输出参数、标量参数顺序与默认命名保持、`emit_c` 错误向上抛出。
- 明确支持：mixed `memory + scalar` returns 经 rewrite 后，`memory` 作为前置 out 参数、`scalar` 继续保留为函数返回值。
- 明确支持：`f32/f64` 类型在 `target=cpu` 下映射为 `float/double`，用于 `Memory<MemorySpace::GM, float>/Memory<MemorySpace::GM, double>` 与 `float/double` 标量参数生成。
- 冻结 `target=cpu` 的 rewrite-after-IR 合同：`gen_kernel(...)` 只接受已经经过 `BufferResultsToOutParamsPass` 的 lowered IR；默认 CPU 路径不再从旧 `memory return` ABI 隐式推导 `out`。
- 明确 split-after-IR 的单函数 codegen 合同：目标源码仍为单个函数定义，tile 相关表达必须由 `tuner.param : !symbol.int<"...">` 与 `symbol.for` 承接。
- 冻结 `target="npu_demo"` 的完整源码合同：`gen_kernel(target="npu_demo")` 必须支持“launch wrapper + body kernel”的受控 `builtin.module` 子集，并生成包含 **body 函数 + launch wrapper 函数** 的双函数源码；body 函数内必须生成 `ctx.barrier(...)`，wrapper 函数必须生成 `npu_demo::launch<1, 4, 1>(...)`；当受控 module 中包含 `dma.alloc` 时，body 还必须稳定发射 `npu_demo::alloc<Space, T>(shape, stride)` helper 调用。
- 冻结 `target="npu_demo"` 生成源码的头部入口为 `#include "include/npu_demo/npu_demo.h"` 后紧跟 `using namespace npu_demo;`，并以“只编译”方式作为 compile gate 目标（`g++ -std=c++17 -I <repo> -c <source>`）。
- 冻结 `target="npu_demo"` 的计算 helper 只允许消费 [`spec/include/api/Kernel.md`](../../spec/include/api/Kernel.md) 已声明的公共接口；不得继续依赖公开 `Nn` 层。
- 支持单一非 `Memory` 标量返回生成函数返回值文本；`!symbol.int<"...">` 仍固定为 `target=cpu` 路径。
- 对 `conv_cpu_tiled_v1` 当前子集，冻结 `conv2d_img2col2d_tiled(...)` 的函数级 CPU 骨架：固定 `Ntile=1`、`Ctile=16`、`Ftile=16`、`Hotile=16`、`Wotile=16`，包含外层分块循环、tile-local `col_buffer/acc_buffer`、`cpu::img2col2d(...)` 调用与最终写回 `out`。

## 限制与边界

- 默认输入必须是单个优化后的 MLIR `func.func`，或单个当前 target 下可发射的普通 op；默认不负责 `builtin.module` 级组织。
- 例外：当 `target="npu_demo"` 时，允许输入为“launch wrapper + body kernel”的受控 `builtin.module` 子集；除此之外的 `builtin.module` 必须显式失败。
- 不负责 AST 解析、MLIR 构造、优化 pass、文件写盘、编译、链接、运行或性能调优。
- 不负责定义单个 op/value 的代码生成细节；这些由 [`spec/dsl/emit_c.md`](../../spec/dsl/emit_c.md) 负责。
- 输出源码必须保持函数名、参数名与 IR 定义一致，不能引入额外公开接口。
- 对于不支持的返回形式、未知 op 或无法映射到目标后端源码的 IR，必须明确报错。
- `func.return` / `out` 绑定不属于普通 `emit_c_op(...)` 的公开职责；`func.return` 只能在 `func.func` 的函数级主遍历流程中收尾处理。
- 默认路径下，旧 `memory return` ABI 必须显式失败并提示先运行 `BufferResultsToOutParamsPass`；不允许继续从 `func.return %mem` 或函数返回类型里偷推 `out`。
- 若 IR 已含前置 out 参数但仍保留 `memory return`（half-rewritten ABI），必须抛出 `GenKernelError` 且错误消息包含 `legacy memory return ABI is not supported`。
- rewrite 后 IR 中，只有最前面连续且由 `arg_attrs.name` 显式标记为 `arg0/arg1/...` 的 `Memory` 参数才视为 out 参数；其余 `Memory` 参数仍视为只读输入。
- 若输入号称 tile family split-after-IR 单函数，但缺少 `tuner.param`、`symbol.for` 或阶段间必需承接对象，`gen_kernel(...)` 必须抛出 `GenKernelError`，禁止静默回退到未切分源码。
- 若 split codegen 试图额外抽取 helper 函数或 `func.call` 承接阶段结果，必须显式失败；该类失败的错误消息必须包含 `KernelSplitUnexpectedHelperFunction`。
- `target="npu_demo"` 必须走受控 `builtin.module` 子集；若只提供单个 body-level `func.func`、或 module 内缺少 wrapper/body 之一，必须显式失败，禁止静默退化为“只输出 body 骨架”。
- `target="npu_demo"` 的计算节点只允许落到 `Kernel` 公共 helper family；不得回退到公开 `Nn` 别名或后端私造的平行 helper 名。
- `target="npu_demo"` 的 `dma.alloc` 节点必须发射为 `npu_demo::alloc<Space, T>(shape, stride)` helper 调用；不得展开为 backing storage + `Memory(...)` 构造。
- `target="npu_demo"` 不得回退到 `.view<T>()`、`load<...>`、`store<...>` 或表达式式 `auto tile = slice(source, ...)`。
- 对 `conv2d_img2col2d_tiled(...)` 这一固定 CPU 子集，不允许把函数级结构写成“由实现决定”“结构自定”或“必要时改走 kernel dialect”；函数骨架、tile 常量、循环层次、局部 buffer 与 `out` 写回都必须在本层直接冻结。

## 公开接口

### `gen_kernel(op_or_func, ctx)`

功能说明：

- 将单个优化后的 MLIR `func.func` 生成为完整的目标后端函数源码文本，或将单个普通 op 生成为节点级源码片段。
- 例外：当 `target="npu_demo"` 时，允许输入为受控 `builtin.module` 子集，并生成包含 body + wrapper 的双函数目标源码。
- 这是 `kernel_gen.dsl.gen_kernel` 唯一稳定公开入口；下游和测试主口径只允许稳定依赖 `gen_kernel(...)` 与错误类型 `GenKernelError`。
- 函数级签名拼装、IR 主遍历与 `func.return` 收尾仅可作为模块内部实现拆分继续存在，不再属于公开稳定接口。

参数说明：

- `op_or_func`（`object`）：待生成的 MLIR `func.func`、单个普通 op；当 `target="npu_demo"` 时也允许输入受控 `builtin.module` 子集。
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
- 若输入为 tile family split-after-IR 单函数，则 `gen_kernel(...)` 只接受已经具备 `tuner.param + symbol.for + 合法承接对象` 的函数体；缺任一要素都必须在函数级入口显式报错。
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

- rewrite 后 IR 中，最前面连续的显式 `arg0/arg1/...` memory 参数必须生成为非 `const` 的 `Memory<Space, T>&` 输出参数；其余 `Memory` 输入参数保持 `const Memory<Space, T>&`。
- 默认 CPU 路径不再接受 `-> (!nn.memory<...>)` 这类旧返回 ABI；memory 输出必须已经在 IR 中前移成参数。
- 若函数已有前置 out 参数但仍声明 `memory` 作为返回类型，视为 half-rewritten ABI，必须抛出 `GenKernelError` 且错误消息包含 `legacy memory return ABI is not supported`。
- 当 rewrite 后函数返回类型仅包含 `scalar` 结果时（mixed returns 场景），函数应生成前置 out 参数与单一标量返回值并存的签名。
- rewrite 后的逐元素加法 kernel 目标源码形态可接近以下形式：

```cpp
void add(Memory<MemorySpace::GM, int32_t>& arg0, const Memory<MemorySpace::GM, int32_t>& arg1, const Memory<MemorySpace::GM, int32_t>& arg2) {
    cpu::add(arg1, arg2, arg0);
}
```

- `target="npu_demo"` 必须以受控 `builtin.module` 子集作为输入：module 内至少包含一个 body 函数与一个 wrapper 函数，wrapper 通过 `arch.launch<1, 4, 1>(@body, ...)`（或等价可机械识别的 launch 形态）调用 body。
- `target="npu_demo"` 的目标输出必须包含 **两个 C++ 函数定义**，其中：
  - body 函数必须包含 `npu_demo::KernelContext& ctx` 作为首参，并按只读 `Memory` 输入 + 显式 `Memory` 输出参数顺序生成签名；
  - wrapper 函数不包含 `KernelContext` 参数，负责调用 `npu_demo::launch<1, 4, 1>(body, ...)` 并透传其余参数。
- `target="npu_demo"` 的完整目标源码形态可接近以下形式：

```cpp
static void add_barrier_body(
    npu_demo::KernelContext& ctx,
    const Memory<MemorySpace::GM, float>& lhs,
    const Memory<MemorySpace::GM, float>& rhs,
    Memory<MemorySpace::GM, float>& out) {
    /* barrier + memory pipeline */
}

void add_barrier(
    const Memory<MemorySpace::GM, float>& lhs,
    const Memory<MemorySpace::GM, float>& rhs,
    Memory<MemorySpace::GM, float>& out) {
    npu_demo::launch<1, 4, 1>(add_barrier_body, lhs, rhs, out);
}
```

- 单一非 `Memory` 结果生成为函数返回值，不生成 `out` 参数；其中 `!symbol.int<"...">` 在 `target=cpu` 下映射为 `long long`。
- 不支持的返回形式必须明确报错。
- 参数名来自 `func.func` 的 `arg_attrs.name`；缺失或为空时必须使用 `arg{index}` 默认命名，保持与 `func.func` 参数顺序一致。

### IR 顺序遍历与收尾绑定

功能说明：

- 当输入为 `func.func` 时，内部流程必须按 `func.func` 中 block 与 op 的顺序遍历函数体。
- 当输入为受控 `builtin.module`（仅 `target="npu_demo"` 允许）时，内部流程必须按 module 内 `func.func` 的出现顺序发射函数定义；对每个 `func.func` 的函数体，仍必须保持 op 的语义顺序。
- 在进入具体 body 发射前，实现必须先在单一 emitter 内部选择函数级策略，统一承接默认路径与当前已冻结的函数级特化。
- 非 `func.return` 的普通 op 必须逐个委托 `emit_c_op(...)` 的公开节点级接口发射。
- `func.return` / `out` 绑定属于函数级主遍历流程的收尾逻辑，不得作为普通 `emit_c_op(...)` 公开职责泄露给下游。

注意事项：

- 必须保持 IR 中 op 的语义顺序。
- 上述函数级策略只允许作为 emitter 内部实现细节存在；不得再扩成新的公开入口、公开 helper 或测试主口径。
- `func.return` 在默认 rewrite-after-IR 路径下仅支持无返回或单一非 `Memory` 标量返回；若仍返回 `Memory`，必须显式报错并包含 `legacy memory return ABI is not supported` 关键字。
- 不得在本层引入未在 `emit_c` 中定义的单 op 生成特例。
- `target=cpu` 下的 lowered add 成功链路必须来自 `NnLoweringPass -> BufferResultsToOutParamsPass` 之后的 rewrite 后 IR，例如：

```cpp
cpu::add(arg1, arg2, arg0);
cpu::add(arg1, v0, arg0);
```

- 不允许从旧 `func.return %mem`、旧 `function_type.outputs` 或隐式 alias 回退到 `out = tmp`、`return tmp` 或其他 generic fallback。
- `target="npu_demo"` 的受控 module 子集必须满足两项冻结点：
  - wrapper 函数必须生成可机械识别的 `npu_demo::launch<1, 4, 1>(body, ...)` 调用；不得生成注释占位或缺失 wrapper。
  - body 函数必须生成可机械识别的 `ctx.barrier(` 调用，且不得生成旧接口 `ctx.sync_threads(`。
- `target="npu_demo"` 的受控 `builtin.module` 子集必须收口为“严格双函数”形态：module 内只允许出现 **一个 body 函数 + 一个 wrapper 函数**（及必要的 symbol/attr），不得夹带额外 `func.func` 或其他顶层 op；否则必须抛出 `GenKernelError`，禁止 silent fallback。
- `target="npu_demo"` 必须显式拒绝“wrapper launch 指向不存在的 body 函数”的输入，并在错误消息中包含缺失 callee 的符号名（例如 `missing_body`）以便下游机械判断：

```text
// launch wrapper 指向不存在的 body 函数
arch.launch<%b, %t, %s>(@missing_body, %lhs, %rhs, %out) : (...) -> ()
```
- `target="npu_demo"` 的 body 函数骨架必须包含并保持如下顺序（说明性示例）：

```cpp
static void add_barrier_body(
    npu_demo::KernelContext& ctx,
    const Memory<MemorySpace::GM, float>& lhs,
    const Memory<MemorySpace::GM, float>& rhs,
    Memory<MemorySpace::GM, float>& out) {
    long long tid = ctx.thread_id();
    long long tnum = ctx.thread_num();

    auto tsm = ctx.get_dynamic_memory<MemorySpace::TSM, float>();

    auto lhs_gm = npu_demo::view(lhs, tid * 16, 16, 1);
    auto rhs_gm = npu_demo::view(rhs, tid * 16, 16, 1);

    auto lhs_tsm = npu_demo::view(tsm, tid * 16, 16, 1);
    auto rhs_tsm = npu_demo::view(tsm, 64 + tid * 16, 16, 1);
    auto out_tsm = npu_demo::view(tsm, 128 + tid * 16, 16, 1);

    npu_demo::slice(lhs_tsm, lhs_gm, 0, 16, 1);
    npu_demo::slice(rhs_tsm, rhs_gm, 0, 16, 1);
    ctx.barrier(/* visibility=[TSM, TLM], scope=BLOCK */);

    npu_demo::add<MemorySpace::TSM, float, float>(out_tsm, lhs_tsm, rhs_tsm);
    ctx.barrier(/* visibility=[TSM, TLM], scope=BLOCK */);

    npu_demo::deslice(out, out_tsm, tid * 16, 16, 1);
}
```

- 上述骨架顺序是 `thread_id/thread_num -> get_dynamic_memory<...> -> npu_demo::view -> npu_demo::slice -> barrier -> npu_demo::Kernel helper -> barrier -> npu_demo::deslice`；其中计算节点必须显式落到 [`spec/include/api/Kernel.md`](../../spec/include/api/Kernel.md) 已冻结的公共 helper，且参数顺序保持 `out-first`；不得回退到公开 `Nn` 别名、`.view<`、`load<`、`store<` 或表达式式 `auto tile = slice(source, ...)`。
- 当 `func.return` 回写 `out` 的值未在 `EmitCContext` 中绑定名称，且该值为 `BlockArgument` 时，必须回退为 `arg{index}` 默认命名以保持与函数级签名一致。
- 当 `func.return` 返回 `!symbol.int<"...">` 时，必须生成 `return <expr>;` 并复用 `emit_c` 的命名/表达式规则。
- 对 `conv_cpu_tiled_v1` 子集，函数体骨架必须固定包含：`constexpr Ntile/Ctile/Ftile/Hotile/Wotile`、tile-local `col_buffer/acc_buffer`、`n -> f -> ho -> wo` 分块循环、循环体内的 `cpu::img2col2d(...)` 与 `c` 方向 tiled compute、以及最终写回 `out` 的显式循环或等价机械可判定写回语句。

## tile family split-after-IR 单函数 codegen 合同

### 适用范围

- 本节适用于已经过 `tile-analysis -> tile-elewise` 或 `tile-analysis -> tile-reduce`、且仍保持单个 `func.func` 的 tile family after-IR 输入。
- 本节只定义 `gen_kernel(...)` 的黑盒源码合同，不定义 `emit_c` 内部 helper、host launch、多 stream 或并行调度细节。
- 输入 IR 必须同时满足三项前置条件：存在至少一个 `tuner.param : !symbol.int<"...">`、函数体中存在显式分块结构 `symbol.for`、跨阶段中间值已有合法承接对象（SSA 或显式 carry memory / 中间 buffer）。

### 目标源码形态

功能说明：

- `gen_kernel(...)` 消费 tile family after-IR 输入时，目标源码必须仍然是单个函数定义；tile 遍历、阶段执行与中间值承接都必须留在该函数体内完成。
- `tuner.param` 对应的 tile 因子必须在源码中表现为非字面量 tile 绑定，供循环步长、切片长度或等价分段范围复用。

使用示例：

```cpp
void vec_add_exp(
    const Memory<MemorySpace::GM, float>& arg0,
    const Memory<MemorySpace::GM, float>& arg1,
    Memory<MemorySpace::GM, float>& arg2) {
    long long tile_d0 = tuner_param("TILE_D0");
    auto carry = alloc(...);
    for (long long i = 0; i < M; i += tile_d0) {
        auto lhs = slice(arg0, i, tile_d0, 1);
        auto rhs = slice(arg1, i, tile_d0, 1);
        auto out = slice(arg2, i, tile_d0, 1);
        add(lhs, rhs, carry);
        exp(carry, carry);
        deslice(out, carry);
    }
}
```

```text
// 对应 tile family after-IR 的最小显式分块结构
%tile_d0 = tuner.param : !symbol.int<"TILE_D0">
symbol.for %it = %c0 to %M step %tile_d0 {
  ...
}
```

注意事项：

- `tuner.param : !symbol.int<"TILE_D0">` 的公开源码占位口径是 `tuner_param("TILE_D0")` 风格的非字面量 tile 来源；例如 `long long tile_d0 = tuner_param("TILE_D0");`。
- `symbol.for` 是 tile family after-IR 的公开显式分块结构；在代码生成后必须保留为函数体内可机械识别的 tile 遍历顺序，不得静默退化成整块一次性执行。
- 与 tile 因子相关的循环步长、切片长度、回写长度或等价分段范围，必须复用同一 `tuner.param`-backed 绑定。
- 当 split 后 IR 需要跨阶段中间值承接时，生成源码必须保留显式承接对象，例如局部 `Memory` / `alloc(...)` / 命名中间 buffer；不能依赖代码生成阶段隐式重算。
- 本节禁止额外抽取 helper 函数、额外生成 `func.call` 风格承接或把 split 阶段外包给未公开的子函数；tile family after-IR 的公开合同仍是单函数源码。

### 失败边界

- 若 tile family after-IR 缺少必需的 `tuner.param`，`gen_kernel(...)` 必须抛出 `GenKernelError`，且错误消息包含 `TileCodegenMalformed: missing tuner.param`。
- 若 tile family after-IR 缺少显式分块结构 `symbol.for`，`gen_kernel(...)` 必须抛出 `GenKernelError`，且错误消息包含 `TileCodegenMalformed: missing explicit tile loop (symbol.for)`。
- 若 tile family after-IR 需要跨阶段承接对象但既无合法 SSA 承接、也无显式 carry memory / 中间 buffer，`gen_kernel(...)` 必须抛出 `GenKernelError`，且错误消息包含 `TileCodegenMalformed` 与具体缺失原因。
- 若源码生成阶段试图把 split 结果额外抽成 helper 函数或额外调用层，`gen_kernel(...)` 必须抛出 `GenKernelError`，且错误消息包含 `TileCodegenUnexpectedHelperFunction`。
- 上述失败都禁止 silent fallback：不得改为输出未切分源码、不得删掉 split 相关阶段。

## tile-elewise ModulePass codegen 合同

### 适用范围

- 本节适用于已经过 `tile-analysis -> tile-elewise` 的单个 `func.func` 输入。
- 函数体必须继续保留 `tile.analysis + tile.tile_exprs` 这两个公开合同属性，作为后续验收资产。
- `tile-elewise` 的公开输出仍以 tile-analysis 的分析合同为真源，只在 elewise 轴上做显式分块，不回退到历史桥接口径。

### 目标源码形态

功能说明：

- `gen_kernel(...)` 消费 tile-elewise after-IR 输入时，目标源码必须仍是单个函数定义；tile 因子通过 `tuner.param : !symbol.int<"...">` 进入源码，并以 `tuner_param("TILE_D0")` 这类非字面量绑定方式出现。
- `kernel.binary_elewise` 与 `dma.broadcast` 在 `target=cpu` 下分别收口到 `cpu::add(...)` 与 `cpu::broadcast(...)`，以便当前 tile-elewise 目录级验收可直接复现。
- `kernel.matmul` 的 tile-elewise 改写同样必须保留 `tile.analysis + tile.tile_exprs`，但当前 CPU codegen 不在本节额外承诺其 helper 形态；后续 target-specific contract 仍沿用既有 `emit_c` / `gen_kernel` 路径。

使用示例：

```cpp
void tile_elewise_example(
    Memory<MemorySpace::GM, int32_t>& arg0,
    const Memory<MemorySpace::GM, int32_t>& arg1,
    const Memory<MemorySpace::GM, int32_t>& arg2) {
    long long tile_d0 = tuner_param("TILE_D0");
    long long tile_d1 = tuner_param("TILE_D1");
    for (long long d0 = 0; d0 < arg2.shape()[0]; d0 += tile_d0) {
        for (long long d1 = 0; d1 < arg2.shape()[1]; d1 += tile_d1) {
            cpu::add(arg1_tile, arg2_tile, arg0_tile);
            cpu::broadcast(src_tile, dst_tile);
        }
    }
}
```

注意事项：

- `tile.analysis` 与 `tile.tile_exprs` 必须在 rewritten op 上继续可见，不得在 `tile-elewise` 后被清理掉。
- `tile-elewise` 只消费 elewise 轴；reduce 轴必须继续保持未切分。
- 不得把 `tuner.param` 回退成历史桥接文本，也不得通过 helper 抽取规避本节合同。
- 当前本节只明确 elementwise / broadcast 的 CPU codegen 成功口径；matmul 仅要求保留公开合同属性与 tile 改写结构，不把 CPU helper 作为新增承诺。

## tile-reduce ModulePass codegen 合同

### 适用范围

- 本节适用于已经过 `tile-analysis -> tile-reduce` 的单个 `func.func` 输入。
- 函数体必须继续保留 `tile.analysis + tile.tile_exprs` 这两个公开合同属性，作为后续验收资产。
- `tile-reduce` 的公开输出仍以 tile-analysis 的分析合同为真源，对 matmul 的输出轴与 reduce 轴生成显式分块。

### 目标源码形态

功能说明：

- `gen_kernel(...)` 消费 tile-reduce after-IR 输入时，目标源码必须仍是单个函数定义；tile 因子通过 `tuner.param : !symbol.int<"...">` 进入源码，并以 `tuner_param("TILE_D0")`、`tuner_param("TILE_D1")`、`tuner_param("TILE_R0")` 这类非字面量绑定方式出现。
- reduce 输出结构必须可机械识别为 `symbol.for -> symbol.for -> dma.fill -> symbol.for -> dma.view/dma.alloc/kernel.matmul/kernel.binary_elewise`。
- rewritten `kernel.matmul` 必须继续保留 `tile.analysis + tile.tile_exprs`，其中 `tile.tile_exprs` 记录当前输出 tile 表达。

使用示例：

```cpp
void tile_reduce_matmul(
    Memory<MemorySpace::GM, int32_t>& out,
    const Memory<MemorySpace::GM, int32_t>& lhs,
    const Memory<MemorySpace::GM, int32_t>& rhs) {
    long long tile_d0 = tuner_param("TILE_D0");
    long long tile_d1 = tuner_param("TILE_D1");
    long long tile_r0 = tuner_param("TILE_R0");
    for (long long d0 = 0; d0 < out.shape()[0]; d0 += tile_d0) {
        for (long long d1 = 0; d1 < out.shape()[1]; d1 += tile_d1) {
            fill(out_tile, 0);
            for (long long r0 = 0; r0 < lhs.shape()[1]; r0 += tile_r0) {
                matmul(tmp, lhs_tile, rhs_tile);
                add(out_tile, tmp, out_tile);
            }
        }
    }
}
```

注意事项：

- `tile-reduce` 不承诺额外 helper 函数或调用层。
- `TILE_R0` 只作为 reduce loop 步长与 reduce tile view 尺寸，不写入 rewritten matmul 的输出 tile 表达矩阵。
- 当前 CPU codegen 仍只以可机械识别的 tile loop、tuner 参数与 kernel op 顺序为公开合同。

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
    const Memory<MemorySpace::GM, float>& input,
    const Memory<MemorySpace::GM, float>& weight,
    Memory<MemorySpace::GM, float>& out) {
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

## `execute_engine + npu_demo + matmul` 源码合同（S1）

功能说明：

- 本节定义 `CASE-3` 的函数级输出要求：当输入链路已命中 `kernel.matmul` 时，`gen_kernel(target="npu_demo")` 生成源码必须可直接交给 `ExecutionEngine` 继续编译执行。

使用示例：

```cpp
#include "include/npu_demo/npu_demo.h"
using namespace npu_demo;
...
npu_demo::matmul<TSM, TSM, TLM1, float, float, float>(out_tile, lhs_tile, rhs_tile);
```

注意事项：

- 本节只约束源码结构与关键调用，不扩展新的 target、运行时参数或调度接口。
- 命中 matmul 路径时不得回退到 `cpu::matmul(...)`，也不得只输出占位注释。
- `target="npu_demo"` 的头部入口保持 `include/npu_demo/npu_demo.h` 后紧跟 `using namespace npu_demo;`。
- 关联合同资产：[`expectation/execute_engine/npu_demo/kernel_only/matmul.py`](../../expectation/execute_engine/npu_demo/kernel_only/matmul.py) 与 [`expectation/execute_engine/npu_demo/default/matmul.py`](../../expectation/execute_engine/npu_demo/default/matmul.py) 的 `CASE-3`。
- 与 `CASE-2` 衔接：输入 IR 应已收口为 `kernel.matmul` 且不残留 `nn.matmul`。

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
- 验证 `target="npu_demo"` 支持受控 `builtin.module` 子集输入，并生成 **body + wrapper** 两个函数定义；wrapper 必须包含 `npu_demo::launch<1, 4, 1>(...)`，body 必须包含 `npu_demo::KernelContext& ctx` 与 `ctx.barrier(...)`，且 `dma.alloc` 仍按 `npu_demo::alloc<Space, T>(shape, stride)` 形式发射。
- 验证 `target="npu_demo"` 的 body 函数骨架必须包含 `ctx.thread_id()`、`ctx.thread_num()`、`ctx.get_dynamic_memory<...>()`，并保持 `npu_demo::view/npu_demo::slice/barrier/npu_demo::Kernel helper/barrier/npu_demo::deslice` 的固定顺序；不得回退到公开 `Nn` 别名、`.view<`、`load<`、`store<` 或表达式式 `auto tile = slice(source, ...)`，且不得生成旧接口 `ctx.sync_threads()`。
- 验证非 `Memory` 标量返回的签名与函数体生成规则；其中 `!symbol.int<"...">` 仅允许 `target=cpu`。
- 对 `conv_cpu_tiled_v1` 下游实现阶段，验证 `conv2d_img2col2d_tiled(...)` 生成源码包含固定 tile 常量、`cpu::img2col2d(...)`、局部 `col_buffer/acc_buffer`、`n/f/ho/wo` 分块循环与最终写回 `out`。
- 注：tile family split-after-IR 相关验收以本 spec 的下游测试映射为准；`test/dsl/test_gen_kernel.py` 已收口相应用例，后续修改不得绕过这些黑盒约束。
- 注：`S3` 计划中的四个 direct-return `nn.add` 验收用例当前先冻结为本 spec 的下游待补测试映射；在 `test/dsl/test_gen_kernel.py` 实际落地前，不把它们写成“当前已存在的可执行测试”。

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
- GK-012：`f32/f64` 标量与 `Memory<Space, f32/f64>` 可生成 `float/double` 与 `Memory<MemorySpace::GM, float>/Memory<MemorySpace::GM, double>` 形式签名。（`test_gen_kernel_supports_float32_scalar_and_memory`）
- GK-013：rewrite 后的逐元素加法 memory+memory 形态在 cpu target 下可生成 `Memory<MemorySpace::GM, int32_t>& arg0` 签名与 `cpu::add(arg1, arg2, arg0);` 函数体。（`test_gen_kernel_supports_lowered_nn_add_memory_memory_on_cpu`）
- GK-014：rewrite 后的逐元素加法 memory+const(i32) 形态在 cpu target 下可生成 `cpu::add(arg1, v0, arg0);` 函数体。（`test_gen_kernel_supports_lowered_nn_add_memory_const_on_cpu`）
- GK-015：rewrite 后的逐元素加法 memory+symbol.int 形态在 cpu target 下可生成 `cpu::add(arg1, v0, arg0);` 函数体，并保留 `long long` 标量参数。（`test_gen_kernel_supports_lowered_nn_add_memory_symbol_on_cpu`）
- GK-016：rewrite 后 `memory + scalar` mixed output 函数中，memory 走前置 `arg0`，scalar 继续返回。（`test_gen_kernel_accepts_rewritten_mixed_output_function`）
- GK-017：`target="npu_demo"` 可消费受控 `builtin.module` 子集并生成双函数源码：`static` body（首参 `npu_demo::KernelContext& ctx`）+ 非 `static` wrapper；wrapper 必须调用 `npu_demo::launch<1, 4, 1>(body, ...)`。（`test_gen_kernel_emits_npu_demo_launch_wrapper_and_barrier_body`）
- GK-017A：`target="npu_demo"` 的受控 `builtin.module` 若仅包含 `dma.alloc`，必须生成 `npu_demo::alloc<Space, T>(shape, stride)` helper 语句，静态与动态 shape 均保持同一命名空间与模板口径。（`test_gen_kernel_emits_npu_demo_dma_alloc_module`）
- GK-018：`target="npu_demo"` 的 body 函数可生成 `Kernel` 公共 helper 所需的 dynamic memory、`npu_demo::view/npu_demo::slice -> ctx.barrier -> npu_demo::Kernel helper -> ctx.barrier -> npu_demo::deslice` 的固定顺序，并且不出现公开 `Nn` 别名、`.view<`、`load<`、`store<`、`auto tile = slice(` 或 `ctx.sync_threads(`。（`test_gen_kernel_emits_npu_demo_launch_wrapper_and_barrier_body`、`test_gen_kernel_compiles_npu_demo_launch_wrapper_and_barrier_body`）
- GK-S4-003：`target="npu_demo"` 的受控 module 输入若越过顶层 `func.func`、wrapper 骨架、callee、extent、barrier scope/visibility 或 target 边界，必须 fail-fast 并保持稳定错误短语。（`test_gen_kernel_rejects_npu_demo_barrier_wrapper_missing_body_symbol`、`test_gen_kernel_rejects_npu_demo_barrier_fail_fast_boundaries`）
- GK-019：rewrite 后成功链路不再残留旧 memory return ABI。（`test_rewritten_pipeline_has_no_memory_return_abi_left`）
- GK-020：half-rewritten IR 会被 `gen_kernel(...)` 显式拒绝。（`test_rewritten_pipeline_fails_on_half_rewritten_ir`）
- GK-021：rewrite 后 lowered add、`conv2d_img2col2d_tiled(...)`、`target="npu_demo"` 的受控双函数 module 子集三类函数级形态继续只通过黑盒 `gen_kernel(...)` 验证源码合同；测试不得直接依赖内部 helper、内部策略函数或内部策略名。（`test_gen_kernel_black_box_direct_return_nn_add_conv2d_img2col2d_tiled_and_npu_demo_contracts`）
- GK-S3-001：tile family after-IR 进入 `gen_kernel(...)` 时，目标源码必须保持单个函数定义，切分逻辑位于函数体内部，且 tile 循环来自 `symbol.for` 的显式分块语义。（`test_gen_kernel_emits_tile_codegen_single_function_tile_loop`）
- GK-S3-002：tile codegen 缺少 `tuner.param` 时必须报 `TileCodegenMalformed`，禁止 silent fallback。（`test_gen_kernel_rejects_tile_codegen_missing_tuner_param`）
- GK-S3-003：tile codegen 缺少显式分块结构 `symbol.for` 时必须报 `TileCodegenMalformed`，不得退化成未切分源码。（`test_gen_kernel_rejects_tile_codegen_missing_loop`）
- GK-S3-004：tile codegen 不允许出现 helper/函数抽取式承接；出现 `func.call` 时必须报 `TileCodegenUnexpectedHelperFunction`。（`test_gen_kernel_rejects_tile_codegen_with_helper_call`）
- GK-S3-005：tile codegen 遇到历史 split tuner 参数合同必须报 `TileCodegenMalformed`。（`test_gen_kernel_rejects_legacy_split_tuner_param_contract`）
- GK-S5-001：tile-elewise after-IR 输入可继续保留 `tile.analysis + tile.tile_exprs`，并对 elementwise/broadcast 生成稳定的 `tuner_param("TILE_D0")` / `cpu::add(...)` / `cpu::broadcast(...)` 源码。（`test_gen_kernel_emits_tile_elewise_cpu_source_for_elementwise_and_broadcast`）
- GK-S5-002：tile-elewise after-IR 的 matmul 改写输出必须继续保留 `tile.analysis + tile.tile_exprs`，且 rewritten `kernel.matmul` 仍可机械识别为 tile family 成员。（`test_tile_elewise_pass_preserves_matmul_contract`）
- GK-S6-001：tile-reduce after-IR 输入可继续保留 `tile.analysis + tile.tile_exprs`，并生成稳定的 `TILE_D0/TILE_D1/TILE_R0`、三层 `symbol.for`、`dma.fill`、`kernel.matmul` 与累加结构。（`test_tile_reduce_pass_rewrites_matmul_and_preserves_contract`）

### C2 下游验收标准

- GK-C2-001：静态 shape 的 `conv2d_img2col2d_tiled(...)` 可生成包含 `cpu::img2col2d(`、`Ntile = 1`、`Ctile = 16`、`Ftile = 16`、`Hotile = 16`、`Wotile = 16` 的 CPU 源码，并可编译运行。（`test_gen_kernel_compiles_conv2d_img2col2d_tiled_cpu_smoke`）
- GK-C2-002：同一静态 shape case 的生成源码中必须可机械判断存在最终写回 `out` 的语句或显式循环。（`test_gen_kernel_writes_back_conv_output_tile`）
