# emit_c.md

## 功能简介

- 定义单个 MLIR op 或 SSA value 到目标后端源码片段的转换规则。
- 为 [`spec/dsl/gen_kernel.md`](../../spec/dsl/gen_kernel.md) 提供函数体拼装时可复用的节点级生成能力。
- 约束 `target=cpu` 下 `nn.add` 的节点级发射只输出已绑定目标的 `cpu::add(...)` 语句，不负责函数级 `out/return` 收口。
- 不负责 `func.func` 级签名拼装、完整函数输出或文件写盘。

## 文档信息

- 创建者：`摸鱼小分队`
- 最后一次更改：`金铲铲大作战`（2026-04-21）
- `spec`：[`spec/dsl/emit_c.md`](../../spec/dsl/emit_c.md)
- `功能实现`：[`kernel_gen/dsl/emit_c.py`](../../kernel_gen/dsl/emit_c.py)
- `test`：[`test/dsl/test_emit_c.py`](../../test/dsl/test_emit_c.py)

## 依赖

- [`spec/dsl/mlir_gen.md`](../../spec/dsl/mlir_gen.md)：MLIR `func.func` 生成来源。
- [`spec/dsl/gen_kernel.md`](../../spec/dsl/gen_kernel.md)：函数级源码生成入口。
- [`spec/include/api/Kernel.md`](../../spec/include/api/Kernel.md)：`target=npu_demo` 下 `Kernel` helper 的公开名字、模板顺序与参数顺序合同。
- [`kernel_gen/dsl/emit_c.py`](../../kernel_gen/dsl/emit_c.py)：节点级源码片段生成实现。
- [`test/dsl/test_emit_c.py`](../../test/dsl/test_emit_c.py)：节点级源码片段生成测试。

## 目标

- 为常见算术、比较、控制流与访存 op 提供稳定的节点级源码片段生成规则。
- 保证同一 SSA value 在同一 `EmitCContext` 中具备稳定命名与稳定表达式输出。
- 为后续实现恢复明确最小支持范围：`arith` 二元算术、`arith.cmpi`、`scf.for`、`symbol.for`、unit-tile `dma.load`/`dma.store`、`dma.alloc`/`dma.view`/`dma.slice`/`dma.deslice`、`symbol.add`（cpu 标量）、`nn.img2col2d`（cpu memory）、`nn.add`（cpu，需预绑定结果目标）与错误路径。
- 为 `target="npu_demo"` 冻结节点级文本映射合同，明确 `KernelContext` 查询、`TSM/TLM` dynamic memory、`view/slice/deslice` 与 `Kernel` helper family 在节点层的稳定发射形态，供后续实现与 `gen_kernel` 骨架拼装收口。

## 限制与边界

- 只负责单个 op 或单个 value 的源码片段生成，不负责遍历完整 `func.func`。
- 不负责函数签名、返回值/输出参数风格与完整函数文本组织；这些由 [`spec/dsl/gen_kernel.md`](../../spec/dsl/gen_kernel.md) 负责。
- 不负责 AST 解析、MLIR 构造、优化、文件写盘、编译、链接或运行。
- 同一接口可针对不同 `target` 生成不同源码，但参数与错误语义必须稳定。
- 对于无法映射的 op、value 依赖、类型或控制流，必须明确报错，不能静默忽略或降级。
- 仅新增 `symbol.add` 与 `symbol.for` 的 `target=cpu` 支持；其余 `symbol.*` 仍按不支持处理。
- `target=cpu` 下 `nn.add` 仅支持在调用方已为 `nn.add.result` 预绑定目标 memory 名称时发射 `cpu::add(...)` 语句；未预绑定结果时必须报错，不能在本层补建临时 `Memory` 变量，也不能生成 `out = temp` 之类的兜底语句。
- `nn.add` 当前仅覆盖 `memory + memory`、`memory + const(i32)` 与 `memory + !symbol.int` 三类 operand 组合；其余 operand 组合仍按不支持处理。
- `non-cpu target` 下 `nn.add` 必须按 `unsupported op` 报错，不能降级到其他 helper 或临时实现。
- 本阶段补齐 `dma.alloc`/`dma.view`/`dma.slice`/`dma.deslice` 与 `nn.img2col2d` 的节点级 CPU 文本映射，用于 conv 链路最小闭环；语义范围以本规范与测试用例为准。
- `dma.slice`/`dma.deslice` 当前仅支持发射显式 loop nest copy；不得生成 `slice(`/`deslice(` helper 调用，避免引入未声明依赖。
- 对于需要 backing storage 的 memory（例如 `dma.alloc` 结果、`nn.img2col2d` 结果），当前仅支持**静态** shape（type.shape 全为 `IntAttr`）；动态 shape 必须报错，避免 `new[]` 生命周期不明确导致泄漏。
- 当 value 类型为 `!symbol.int<"...">` 时，`target=cpu` 默认映射为 `long long`。
- 当前 `test/dsl/test_emit_c.py` 已定义并可直接映射的用例范围以本节 `EC-001` ~ `EC-011` 为准，另含 `EC-009A`；`EC-012` ~ `EC-016` 在本阶段仅冻结为 `nn.add` 的节点级验收标准，待下游测试落地后再补具体测试映射。
- 对 `target=npu_demo`，本层只冻结节点级文本映射，不定义完整函数签名或 `npu_demo::KernelContext& ctx` 的参数注入方式；上层 `gen_kernel` 需提供稳定上下文变量名 `ctx`，本层只消费该绑定。
- 对 `target=npu_demo`，当前只承认 `thread_id/thread_num` 查询、`TSM/TLM` dynamic memory、`view/slice/deslice` 与 [`spec/include/api/Kernel.md`](../../spec/include/api/Kernel.md) 已冻结的 helper family 的成功发射路径；不得回退到旧公开 `Nn` 层、`source.view<T>(...)`、`load<...>`、`store<...>`、`launch`、`barrier` 或 `arch.launch_kernel`。
- 当前 CPU 恢复范围继续以 `test/dsl/test_emit_c.py` 已定义用例为准；`target=npu_demo` 的专项验收目标先行冻结，留待后续实现阶段补齐对应测试。

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
- `symbol.for` 必须生成与 `scf.for` 同风格的循环语句块，并过滤循环体中的空语句（例如常量 op 产生的空行）。
- 当前恢复范围下，unit-tile `dma.load`/`dma.store` 必须保留索引顺序与读写方向。
- `target=cpu` 下 `symbol.add` 必须生成与二元算术等价的赋值语句。
- `target=cpu` 下 `nn.add` 仅在 `ctx` 已把 `nn.add.result` 绑定到目标 memory 名称时生成 `cpu::add(...)` 语句；若结果未绑定，必须直接报错。
- `target=cpu` 下 `nn.add` 的最小成功文本示例如下，分别对应 `memory + memory`、`memory + const(i32)` 与 `memory + !symbol.int`：

```cpp
cpu::add(lhs, rhs, out);
cpu::add(lhs, 1, out);
cpu::add(lhs, bias, out);
```

- `target=cpu` 下 `nn.add` 不得在本层偷偷声明临时 `Memory v0` 承接结果，也不得生成 `out = v0` 之类的二次收口语句。
- `non-cpu target` 下 `nn.add` 必须报错 `unsupported op`。
- `target=cpu` 下 `dma.alloc` 必须生成 `shape/stride` 数组与 `Memory<Space, T>` 声明；并为静态 shape 生成 backing buffer。
- `target=cpu` 下 `dma.view` 必须生成 `offset` 计算，并生成基于源 memory 的视图声明（复用 format）。
- `target=cpu` 下 `dma.slice`/`dma.deslice` 必须发射显式 loop nest copy，避免依赖外部 helper。
- `target=cpu` 下 `nn.img2col2d` 必须声明输出 memory（含 backing storage）并发射 `cpu::img2col2d(...)` 调用。

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
- `nn.add` 结果属于 memory 写入，不是纯右值表达式；不得通过 `emit_c_value(...)` 兜底生成。

返回与限制：

- 返回类型：`str`。
- 返回语义：可嵌入右值位置的表达式文本。
- 限制条件：当前恢复范围覆盖算术表达式、比较表达式、常量、unit-tile `dma.load` 结果与 `symbol.add` 标量表达式（仅 cpu）。

## CPU 节点级发射规则

### 适用范围

- 以下规则仅适用于 `target=cpu`，且只定义单个 op 在函数体中的节点级语句/语句块形态。
- 本层只负责 tile-local `Memory<Space, T>` 声明、memory 视图重解释、显式 copy loop、`cpu::img2col2d(...)` 调用与局部计算节点本身。
- 本层不负责固定 tile 常量、外层分块循环、完整函数签名或最终写回 `out` 的整体骨架；这些由 [`spec/dsl/gen_kernel.md`](../../spec/dsl/gen_kernel.md) 负责。
- 本层不得通过 `kernel dialect` / `nn_lowering` 中转补语义，也不得引入新的 `slice(...)` / `deslice(...)` helper API。

### `dma.alloc`

功能说明：

- 为 tile-local buffer 或其他局部 `nn.memory` 结果生成独立的 `shape/stride` 数组、backing storage 与 `Memory<Space, T>` 声明。

使用示例：

```cpp
long long col_tile_shape[3] = {1, 4, 9};
long long col_tile_stride[3] = {36, 9, 1};
float col_tile_buffer[36] = {};
Memory<LM, float> col_tile(col_tile_buffer, 3, col_tile_shape, col_tile_stride, MemoryFormat::Norm);
```

注意事项：

- 发射结果必须是可直接被后续 `nn.img2col2d`、局部计算或 `dma.deslice` 消费的节点级语句，不能把 `alloc` 延后到 `gen_kernel` 再决定。
- 静态 shape 必须生成有效 backing storage；当前不支持动态 shape backing，遇到动态 shape 必须报错。
- `Memory<Space, T>` 的 `format` 取自结果 type，`Space` 来自 `nn.space` 模板参数，不在本层额外发明 CPU 专用旁路对象。

### `dma.view`

功能说明：

- 基于源 `Memory<Space, T>` 发射偏移计算与子视图声明，用于把已有 memory 重新解释为新的 shape/stride 视图。

使用示例：

```cpp
long long view_offset0 = (0 * source.stride()[0]) + (0 * source.stride()[1]);
long long v0_shape[2] = {2, 2};
long long v0_stride[2] = {1, 1};
Memory<GM, float> v0(const_cast<float*>(source.data()) + view_offset0, 2, v0_shape, v0_stride, source.format());
```

注意事项：

- `offset` 必须按源 memory 的 `stride()` 计算；目标视图复用源 memory 的 `format()`。
- `dma.view` 只负责节点级视图表达，不额外分配 backing storage，也不决定该视图是否最终对应 `out` 或 tile-local buffer。

### `dma.slice` / `dma.deslice`

功能说明：

- 将 DMA 拷贝节点发射为显式 loop nest copy，使用 `Memory::at(long long indices[])` 完成 source/target 间的数据搬运。

使用示例：

```cpp
long long dma0_src_indices[4] = {0, 0, 0, 0};
long long dma0_dst_indices[4] = {0, 0, 0, 0};
for (long long dma0_i0 = 0; dma0_i0 < 1; ++dma0_i0) {
    /* ... */
    tile_local.at(dma0_dst_indices) = input_tile.at(dma0_src_indices);
}
```

注意事项：

- `dma.slice` 负责把带 `offsets/sizes/strides` 的源区域拷贝到单位偏移的 tile-local target。
- `dma.deslice` 负责把单位偏移 source 拷回带 `offsets/sizes/strides` 的 target 区域；当 target 是最终 `out` 时，本层只发该节点自己的显式写回 loop，不负责定义整个 kernel 的输出骨架。
- 当前规范禁止生成 `slice(` / `deslice(` helper 调用；必须继续发显式 copy loop。
- 同一作用域重复发射 `dma.slice` / `dma.deslice` 时，辅助索引缓冲区与循环变量名必须保持唯一，避免节点级文本冲突。

### `nn.img2col2d`

功能说明：

- 发射 `nn.img2col2d` 的 CPU 节点级文本：先声明结果 `Memory<Space, T>`（含 backing storage），再发出 `cpu::img2col2d(...)` 调用。

使用示例：

```cpp
long long col_tile_shape[3] = {1, 4, 9};
long long col_tile_stride[3] = {36, 9, 1};
float col_tile_buffer[36] = {};
Memory<LM, float> col_tile(col_tile_buffer, 3, col_tile_shape, col_tile_stride, MemoryFormat::Norm);
cpu::img2col2d(input_tile, col_tile, kh, kw, sh, sw, dh, dw, ph, pw, pl, pr);
```

注意事项：

- 目标调用语句必须收敛为接近 `cpu::img2col2d(input_tile, col_tile, kh, kw, sh, sw, dh, dw, ph, pw, pl, pr);` 的形态。
- `input_tile` 与 `col_tile` 都是节点级 `Memory<Space, T>` 引用；`col_tile` 可来自前序 `dma.alloc`，不得在本层改写为其他 helper 或 `kernel dialect` 中转。
- `nn.img2col2d` 只负责当前节点的 tile-local 展开语句，不负责固定 tile 常量、外层分块循环或最终 `out` 写回。

## npu_demo 节点级发射规则

### 适用范围

- 以下规则仅适用于 `target=npu_demo`，且只定义单个查询/访存/算子节点如何发成 body-level kernel 内部的局部文本片段。
- 本层不声明 `npu_demo::KernelContext` 局部变量，也不定义完整函数签名；上层 `gen_kernel` 必须提供已绑定的上下文变量名 `ctx`，本层只负责引用 `ctx.thread_id()`、`ctx.thread_num()` 与 `ctx.get_dynamic_memory<Space, T>()`。
- 本层当前只收口 `thread_id/thread_num` 查询、`TSM/TLM` dynamic memory、`view`、目标式 `slice`、`deslice` 与 `Kernel` helper family。
- 本层不得回退到 CPU 风格 `.view<T>()`、`load<...>`、`store<...>`、显式 loop nest copy、`launch`、`barrier` 或 `arch.launch_kernel`。

### `arch.get_thread_id` / `arch.get_thread_num`

功能说明：

- 当节点表示 thread 维度查询时，必须发射为对当前上下文 `ctx` 的直接查询。

使用示例：

```cpp
long long tid = ctx.thread_id();
long long tnum = ctx.thread_num();
```

注意事项：

- `thread_id` 与 `thread_num` 的目标文本必须分别收敛为 `ctx.thread_id()` 与 `ctx.thread_num()`。
- 本层只负责节点级查询表达式或赋值语句，不在此处声明 `npu_demo::KernelContext& ctx` 签名。

### `arch.get_dynamic_memory(memory_space)`

功能说明：

- 当节点表示 `npu_demo` 的 dynamic memory 查询时，必须发射为 `ctx.get_dynamic_memory<Space, T>()`。

使用示例：

```cpp
auto tsm = ctx.get_dynamic_memory<TSM, float>();
auto tlm = ctx.get_dynamic_memory<TLM1, float>();
```

注意事项：

- 当前 `npu_demo` 成功路径只承认 `TSM` 与 `TLM1/TLM2/TLM3`。
- 元素类型模板参数 `T` 取自结果 `Memory<Space, T>` 的 element type，不得退回到字节级 `load/store` 组合。
- 不得把 `TSM/TLM1/TLM2/TLM3` dynamic memory 发射成 `malloc(...)`、`load<...>`、`store<...>` 或其他 CPU 旁路文本。

### `dma.view`

功能说明：

- `npu_demo` 下的视图节点必须发射为稳定的 `view(source, offset, size, stride)` 调用，用于表达 source memory 上的局部视图。

使用示例：

```cpp
auto src_view = view(source, tid * 16, 16, 1);
auto work_tile = view(tsm, 0, 16, 1);
```

注意事项：

- `view(...)` 的参数顺序必须保持 `source -> offset -> size -> stride`。
- 不得发射为 `source.view<float>(...)`、手写 `Memory<Space, T>` 构造旁路或 `load/store` 组合。

### `dma.broadcast`

功能说明：

- `target=cpu` 时必须发射为稳定的 `cpu::broadcast(source, target);` 调用。
- `target=npu_demo` 时必须发射为稳定的 `npu_demo::broadcast<DstSpace, SrcSpace, DstType, SrcType>(dst, source);` 调用。

使用示例：

```cpp
cpu::broadcast(src, dst);
npu_demo::broadcast<TSM, TSM, float, float>(dst /*dst*/, src /*source*/);
```

注意事项：

- 参数顺序必须分别固定为 `source -> target` 与 `dst -> source`。
- 不得回退到历史 tile 桥接名。

### `dma.slice`

功能说明：

- `npu_demo` 下的拷入节点必须发射为目标式 `slice(target, source, offset, size, stride);`。

使用示例：

```cpp
slice(work_tile, src_view, 0, 16, 1);
```

注意事项：

- 参数顺序必须固定为 `target -> source -> offset -> size -> stride`。
- 不得发射为 `auto tile = slice(source, ...)`、`target = slice(source, ...)` 或显式 loop nest copy。

### `dma.deslice`

功能说明：

- `npu_demo` 下的回写节点必须发射为目标式 `deslice(target, source, offset, size, stride);`。

使用示例：

```cpp
deslice(out, out_tile, tid * 16, 16, 1);
```

注意事项：

- 参数顺序必须固定为 `target -> source -> offset -> size -> stride`。
- 不得发射为显式 loop nest copy、`store<...>` 组合或其他 CPU 旁路文本。

### `kernel.binary_elewise(kind="add")`

功能说明：

- `npu_demo` 下的逐元素加法节点必须发射为稳定的公共 `Kernel` helper 调用 `npu_demo::add<...>(out, lhs, rhs);`。

使用示例：

```cpp
npu_demo::add<TSM, float, float>(out_tile, lhs_tile, rhs_tile);
```

注意事项：

- 参数顺序必须固定为 `out -> lhs -> rhs`。
- 模板顺序必须与 [`spec/include/api/Kernel.md`](../../spec/include/api/Kernel.md) 一致。
- 不得回退到公开 `Nn` helper、`cpu::add(...)`、运算符表达式拼接或 `load/store` 形式。

### `execute_engine + npu_demo + matmul` 节点文本合同（S1）

功能说明：

- 本节定义 `CASE-3` 在节点层的最小输出要求：当输入链路命中 `kernel.matmul` 时，`target=npu_demo` 的文本需落到 `npu_demo::matmul(...)` 调用。

使用示例：

```cpp
slice(lhs_tile, lhs, m0, 16, 1);
slice(rhs_tile, rhs, n0, 16, 1);
npu_demo::matmul<TSM, TSM, TLM1, float, float, float>(out_tile, lhs_tile, rhs_tile);
deslice(out_tile, out, m0, 16, 1);
```

注意事项：

- 本节只覆盖节点文本，不定义函数签名、wrapper 或编译执行流程。
- `npu_demo` 路径命中 matmul 时不得生成 `cpu::matmul(...)`。
- 若 `kernel.matmul` 在当前 target 下不可发射，必须报错并包含 `unsupported op`。
- 关联合同资产：[`expectation/execute_engine/npu_demo/matmul.py`](../../expectation/execute_engine/npu_demo/matmul.py) 的 `CASE-3`。

## 测试

- 测试文件：[`test/dsl/test_emit_c.py`](../../test/dsl/test_emit_c.py)
- 执行命令：`pytest -q test/dsl/test_emit_c.py`

### 测试目标

- 验证节点级算术、比较、循环与访存 op 的源码片段生成规则。
- 验证 `EmitCContext` 下 SSA 命名与表达式生成的一致性。
- 验证不支持 op 与非法 value 依赖的错误路径。
- 验证 `symbol.add` 仅允许 `target=cpu`；非 cpu target 必须明确报错。
- 验证 `nn.add` 在 `target=cpu` 下仅对已预绑定目标的三类 operand 组合生成 `cpu::add(...)` 语句。
- 验证 `nn.add` 在结果未预绑定或 `non-cpu target` 下明确报错，不生成临时 memory 或其他兜底语句。
- 验证 `symbol.for`、`dma.alloc/view/slice/deslice` 与 `nn.img2col2d` 的最小 CPU 发射闭环，并锁定输出文本不引入 `slice/deslice` helper 与 `nullptr`。
- 验证重复 `dma.slice/dma.deslice` 发射时辅助变量名保持唯一，避免同一作用域命名冲突。
- 下游 `npu_demo` 专项验收至少应覆盖 `thread_id/thread_num` 查询，建议测试名为 `test_emit_c_lowers_npu_demo_kernel_context_queries`。
- 下游 `npu_demo` 专项验收至少应覆盖 `TSM/TLM1/TLM2/TLM3` dynamic memory 查询，建议测试名为 `test_emit_c_lowers_npu_demo_dynamic_memory_access`。
- 下游 `npu_demo` 专项验收至少应覆盖 `view + slice + add + deslice` 管线，建议测试名为 `test_emit_c_lowers_npu_demo_slice_deslice_add_pipeline`，且不得回退到 `.view<`、`load<`、`store<`。

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
- EC-009：`dma.alloc`/`dma.view` 在 cpu target 下可生成最小 CPU 文本片段。（`test_emit_c_op_lowers_dma_alloc_and_view`）
- EC-009A：`dma.broadcast` 在 cpu target 下可生成稳定的 `cpu::broadcast(source, target);` 片段。（`test_emit_c_lowers_cpu_dma_broadcast_helper_contract`）
- EC-010：`symbol.for + dma.alloc + dma.slice + nn.img2col2d + dma.deslice` 链路可发射稳定 CPU 文本片段，且不引入 `slice/deslice` helper 与 `nullptr`。（`test_emit_c_op_lowers_img2col2d_dma_loop_pipeline`）
- EC-011：重复 `dma.slice/dma.deslice` 发射时辅助变量名必须保持唯一。（`test_emit_c_op_assigns_unique_helper_names_for_repeated_dma_slice_and_deslice`）
- EC-012：当 `ctx` 已把结果预绑定为 `out` 时，`NnAddOp(memory, memory)` 在 cpu target 下必须精确生成 `cpu::add(lhs, rhs, out);`。（下游待补测试映射）
- EC-013：当 `ctx` 已把结果预绑定为 `out` 时，`NnAddOp(memory, i32 const)` 在 cpu target 下必须精确生成 `cpu::add(lhs, 1, out);`。（下游待补测试映射）
- EC-014：当 `ctx` 已把结果预绑定为 `out` 时，`NnAddOp(memory, !symbol.int)` 在 cpu target 下必须精确生成 `cpu::add(lhs, bias, out);`。（下游待补测试映射）
- EC-015：未预绑定 `nn.add.result` 时，合法 `NnAddOp` 在 cpu target 下必须抛出 `EmitCError`，错误消息包含 `target=cpu: nn.add: unsupported op`。（下游待补测试映射）
- EC-016：`non-cpu target` 下合法 `NnAddOp` 必须抛出 `EmitCError`，错误消息包含 `target=npu_demo: nn.add: unsupported op`。（下游待补测试映射）
