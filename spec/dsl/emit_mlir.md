# emit_mlir.md

## 功能简介

- 定义 AST 节点到 MLIR op/value 的转换规则。
- 为 `ast_visitor` 提供可调用的节点发射接口。
- 不负责 AST 解析与遍历，不负责 MLIR 文本输出。

## 文档信息

- 创建者：`规格小队`
- 最后一次更改：`大闸蟹`
- `spec`：[`spec/dsl/emit_mlir.md`](../../spec/dsl/emit_mlir.md)
- `功能实现`：
  - [`kernel_gen/dsl/mlir_gen/emit/core.py`](../../kernel_gen/dsl/mlir_gen/emit/core.py)
  - [`kernel_gen/dsl/mlir_gen/emit/__init__.py`](../../kernel_gen/dsl/mlir_gen/emit/__init__.py)
  - [`kernel_gen/dsl/mlir_gen/emit/call_arch.py`](../../kernel_gen/dsl/mlir_gen/emit/call_arch.py)
  - [`kernel_gen/dsl/mlir_gen/emit/call_dma.py`](../../kernel_gen/dsl/mlir_gen/emit/call_dma.py)
  - [`kernel_gen/dsl/mlir_gen/emit/call_symbol.py`](../../kernel_gen/dsl/mlir_gen/emit/call_symbol.py)
  - [`kernel_gen/dsl/mlir_gen/emit/context.py`](../../kernel_gen/dsl/mlir_gen/emit/context.py)
  - [`kernel_gen/dsl/mlir_gen/emit/dispatch.py`](../../kernel_gen/dsl/mlir_gen/emit/dispatch.py)
  - [`kernel_gen/dsl/mlir_gen/emit/control_flow.py`](../../kernel_gen/dsl/mlir_gen/emit/control_flow.py)
  - [`kernel_gen/dsl/mlir_gen/emit/value.py`](../../kernel_gen/dsl/mlir_gen/emit/value.py)
  - [`kernel_gen/dsl/mlir_gen/emit/type_utils.py`](../../kernel_gen/dsl/mlir_gen/emit/type_utils.py)
  - [`kernel_gen/dsl/mlir_gen/emit/shape_utils.py`](../../kernel_gen/dsl/mlir_gen/emit/shape_utils.py)
- `test`：
  - [`test/dsl/test_emit_mlir.py`](../../test/dsl/test_emit_mlir.py)
  - [`test/dsl/mlir_gen/emit/test_call_arch.py`](../../test/dsl/mlir_gen/emit/test_call_arch.py)
  - [`test/dsl/mlir_gen/emit/test_call_dma.py`](../../test/dsl/mlir_gen/emit/test_call_dma.py)
  - [`test/dsl/mlir_gen/emit/test_call_symbol.py`](../../test/dsl/mlir_gen/emit/test_call_symbol.py)
  - [`test/dsl/mlir_gen/emit/test_dispatch.py`](../../test/dsl/mlir_gen/emit/test_dispatch.py)
  - [`test/dsl/mlir_gen/emit/test_control_flow.py`](../../test/dsl/mlir_gen/emit/test_control_flow.py)
  - [`test/dsl/mlir_gen/emit/test_value.py`](../../test/dsl/mlir_gen/emit/test_value.py)
  - [`test/dsl/mlir_gen/emit/test_type_utils.py`](../../test/dsl/mlir_gen/emit/test_type_utils.py)
  - [`test/dsl/mlir_gen/emit/test_shape_utils.py`](../../test/dsl/mlir_gen/emit/test_shape_utils.py)

## 依赖

- AST 节点定义：[`spec/dsl/ast.md`](../../spec/dsl/ast.md)
- AST 访问器：[`spec/dsl/ast_visitor.md`](../../spec/dsl/ast_visitor.md)
- Arch DSL helper 公开入口：[`spec/include/api/Arch.md`](../../spec/include/api/Arch.md)
- arch 查询结果类型：[`spec/dialect/arch.md`](../../spec/dialect/arch.md)

## 术语

- `EmitContext`：发射上下文，包含 builder、类型映射与符号表。
- `MLIR Value`：MLIR SSA value 的抽象表示。
- `target`：目标后端名称（`str`），与 [`spec/target/registry.md`](../../spec/target/registry.md) 的 `TargetSpec.name` 一致。
- `hardware`：硬件参数表（`dict[str, int]`），字段范围见 [`spec/target/registry.md`](../../spec/target/registry.md)（如 `thread_num`、`block_num`、`subthread_num`、`*_memory_size`）。

## 目标

- 将 AST 表达式节点转换为 MLIR value。
- 将 AST 语句节点转换为 MLIR op 或控制流结构。
- 保证同一节点生成的 value 可被上游复用。

## emit 共享核心职责

- `kernel_gen/dsl/mlir_gen/emit/dispatch.py`
  - 仅负责节点类型到处理函数的路由。
  - `PythonCalleeCallAST` 的稳定入口通过 `call_dispatch(...)` 收口为 `func.call` 路径。
  - 不直接实现 nn/dma/arch/symbol family 细节。
- `kernel_gen/dsl/mlir_gen/emit/call_dma.py`
  - 只处理 `DmaAllocAST` / `DmaCopyAST` / `DmaCastAST` / `DmaViewAST` / `DmaReshapeAST` / `DmaFlattenAST` / `DmaFreeAST` / `LoadAST` / `StoreAST` 这组 DMA family AST。
  - 统一复用既有 lowering，作为 DMA family 的最小拆分入口。
- `kernel_gen/dsl/mlir_gen/emit/call_symbol.py`
  - 只处理 `SymbolToFloatAST` / `TensorAxisAccessAST`，以及最终走 `symbol.for` 路径的 `ForAST`。
  - 不直接承接 DMA / NN / arch family 细节。
- `kernel_gen/dsl/mlir_gen/emit/call_arch.py`
  - 只处理 `ArchQueryAST` / `ArchGetDynamicMemoryAST` / `ArchLaunchKernelAST` 这组 arch family AST。
  - `ArchBarrierAST` 仍由核心 emit 入口直接收口，不在该拆分入口内重复定义语义。
- `kernel_gen/dsl/mlir_gen/emit/control_flow.py`
  - 只处理控制流结构节点（当前聚焦 `ForAST`）。
  - Assign/Return 在 AST 解析阶段折叠，不作为 emit 输入节点。
- `kernel_gen/dsl/mlir_gen/emit/value.py`
  - 只处理变量取值、字面量与 `symbol.const`/index operand。
  - 不直接构造 nn/dma family op。
- `kernel_gen/dsl/mlir_gen/emit/type_utils.py`
  - 只处理 dtype/memory type/结果类型推导。
  - 不执行 builder 插入逻辑。
- `kernel_gen/dsl/mlir_gen/emit/shape_utils.py`
  - 只处理 shape/stride/layout/index 规范化。
  - 不直接发射最终 operation。

## 限制与边界

- 不解析 Python 函数，不遍历 AST。
- 不做优化、常量折叠或后端特化。
- 不生成 MLIR 文本；文本输出由上游调用方负责。
- 发射阶段仅消费 AST 与上下文，不向 AST 注入 `target`/`hardware` 字段；相关信息只能通过 `EmitContext` 或外部上下文传入。
- 当 `ForAST` 来自 `LoopRange(start, end, step)` 且边界与循环变量保持 symbol 整数语义时，必须 lowering 为 `symbol.for`，不得回退为 `scf.for`；其循环块参数 `it` 必须为 `!symbol.iter<...>`。
- 在上述 `LoopRange` 场景中，循环变量以及传入 `dma.slice` / `dma.deslice` 的 `offsets`、`sizes`、`strides` 等 DMA 标量 operand 必须直接复用 symbol 语义 value，不得插入 `arith.index_cast`；其中 `start/end/step` 保持 `!symbol.int<"expr">`，循环变量 `it` 可直接以 `!symbol.iter<...>` 参与 DMA operand；若 `it` 退化为 `index`、普通整数、浮点类型或其他非 symbol 迭代类型，应视为 lowering 违规。
- 当 DSL AST 表达 `alloc`、`copy`、`cast`、`view`、`reshape`、`flatten`、`load`、`store`、`slice`、`deslice` 这组 DMA helper 调用时，`emit_mlir` 必须按对应 memory 语义 lowering；其中 `flatten` 公开上视为一维 `reshape` 语义，不要求生成独立 dialect op。
- 当 DSL AST 表达 `img2col1d(...)` 或 `img2col2d(...)` helper 调用时，`emit_mlir` 必须直接 lowering 为 `nn.img2col1d` 或 `nn.img2col2d`；不得在 emit 层引入 `kernel_dialect`、`nn_lowering` 或 `cpu::img2col2d` 相关语义。
- 当 DSL AST 表达 `matmul(lhs, rhs, memoryspace=...)` helper 调用时，`emit_mlir` 必须直接 lowering 为 `nn.matmul`；若左右操作数 `element_type` 不一致必须报错 `matmul element_type must match`，不得插入 `dma.cast`。
- 当 DSL AST 表达 `conv(value, weight, sh=..., sw=..., dh=..., dw=..., ph=..., pw=..., pl=..., pr=...)` helper 调用时，`emit_mlir` 必须在前端分解为 raw `nn.img2col2d + dma.reshape + nn.matmul + dma.reshape`；不得生成 `nn.conv`，也不得把该 helper 退回为 `Unsupported call expression`。
- `img2col2d` 的 emit 节点级流程允许并要求与循环/切片节点协作：窗口读取通过 `dma.slice`，窗口回写通过 `dma.deslice`，循环结构保持 `ForAST -> symbol.for`；该规则只约束 emit 节点映射，不扩展到 kernel/runtime 责任。
- `store(...)` / `deslice(...)` 的 target 允许来自前序 `alloc/view/reshape/flatten/cast/copy/img2col/matmul/get_dynamic_memory` 等 memory 表达式；emit 阶段必须对该 target 先求值再执行写回，不得退回只允许函数输入张量的旧口径。
- 当 `CompareExprAST(op="ne")` 来自 `lhs != rhs` 入口且两侧为 `nn.memory` 时，必须 lowering 为 `nn.ne`；允许按隐式 broadcast 规则插入 `nn.broadcast`，若无法广播必须报错 `Implicit broadcast dimension mismatch`，若 element type 不一致必须报错 `Binary op operands must have the same element_type`。
- 当 `BinaryExprAST(op="mul")` 来自 `lhs * rhs` 或 `nn.mul(lhs, rhs)` 入口且两侧为 `nn.memory` 时，必须 lowering 为 `nn.mul`；若 shape 不一致但可 broadcast，允许按需插入 `nn.broadcast`，若不可 broadcast 必须报错 `Implicit broadcast dimension mismatch`。当两侧 `element_type` 不一致但 `space` 一致时，必须按二元算术 dtype promotion（`i32 < f16 < f32`）决议目标 element_type，并仅对非目标侧插入 `dma.cast` 再发射 `nn.mul`；若 `space` 不一致必须报错 `Binary op operands must have the same space`。
- `free` 必须作为语句型 helper 处理，不产生新的 SSA 结果，并在 emit 阶段生成单个 `dma.free`。
- `_memory_to_nn_type(...)` / `_nn_memory_type_to_memory(...)` 的 dtype 映射必须覆盖 `NumericType.Int64 <-> i64`，避免 tensor memory 在 `i64` 场景下断链。
- `ArchQueryAST(query_name="get_block_id")` 必须 lowering 为单个 `arch.get_block_id`，并保持结果类型为 `!symbol.int<"block_id">`。
- `ArchQueryAST(query_name="get_block_num")` 必须 lowering 为单个 `arch.get_block_num`，并保持结果类型为 `!symbol.int<"block_num">`。
- `ArchQueryAST(query_name="get_subthread_id")` 必须 lowering 为单个 `arch.get_subthread_id`，并保持结果类型为 `!symbol.int<"subthread_id">`。
- `ArchQueryAST(query_name="get_subthread_num")` 必须 lowering 为单个 `arch.get_subthread_num`，并保持结果类型为 `!symbol.int<"subthread_num">`。
- `ArchQueryAST(query_name="get_thread_id")` 必须 lowering 为单个 `arch.get_thread_id`，并保持结果类型为 `!symbol.int<"thread_id">`。
- `ArchQueryAST(query_name="get_thread_num")` 必须 lowering 为单个 `arch.get_thread_num`，并保持结果类型为 `!symbol.int<"thread_num">`。
- `ArchGetDynamicMemoryAST(space=...)` 必须 lowering 为单个 `arch.get_dynamic_memory`，结果类型固定为 `!nn.memory<[?], [1], i8, #nn.space<space>>`；`space` 非 `SM/LM/TSM/TLM1/TLM2/TLM3` 时必须报错。
- `ArchBarrierAST(visibility, scope)` 必须 lowering 为单个无返回值 `arch.barrier {scope = #arch.scope<...>, visibility = [#arch.visibility<...>, ...]}`；`visibility` 必须保持源码顺序且非空，元素必须全为可 lowering 的 `BarrierVisibility`，`scope` 必须可 lowering 为 `#arch.scope<...>`。若 AST 形状违规，emit 必须报固定关键短语 `barrier visibility must be non-empty BarrierVisibility list` 或 `barrier scope must be BarrierScope`，不得退回 generic unsupported。
- `ArchLaunchKernelAST(callee, block, thread, subthread, args)` 必须 lowering 为单个无返回值 `arch.launch<%block, %thread, %subthread>(@callee, %arg0, %arg1, ...) : ... -> ()`；`callee` 必须是函数对象 / symbol ref，对外不得接受字符串字面量、属性访问、lambda、调用表达式或其他 runtime callable 结果。extent 公开语义统一为 `!symbol.int` 启动规模：AST 虽允许 `int | SymbolDim` 入口，但 emit 阶段若 extent 不是正整数 `!symbol.int<"...">` 必须报错；同时 launched body 内 `arch.get_thread_num` / `arch.get_block_num` / `arch.get_subthread_num` 的结果类型虽保持 `!symbol.int<"...">`，其数值语义由当前 `arch.launch` 的 extent 决定。
- `TensorAxisAccessAST(tensor, kind, axis)` 必须按节点语义降级为 symbol 方言查询：`kind="shape"` lowering 为 `symbol.get_dim`，`kind="stride"` lowering 为 `symbol.get_stride`。其中 `tensor` 必须为 `nn.memory` 值，`axis` 必须为静态非负整数且落在 rank 范围内；不满足约束时必须报错（例如 `get_shape source must be nn.memory`、`get_shape axis must be static int`、`get_shape axis out of range`、`Unsupported tensor axis access kind`）。

## 公开接口

### `EmitContext(builder, symbols, types, config=None)`

功能说明：

- 封装发射所需的构建器、符号表与类型映射。

参数说明：

- `builder` (`object`)：MLIR 构建器或等价接口。
- `symbols` (`dict`)：变量名到 MLIR value 的映射。
- `types` (`object`)：类型映射或类型系统入口。
- `config` (`dict|None`)：可选配置，可包含 `target`（`str`）与 `hardware`（`dict[str, int]`）。

使用示例：

```python
ctx = EmitContext(
    builder=builder,
    symbols={},
    types=types,
    config={"keep_location": True, "target": "gpu_a", "hardware": {"thread_num": 256}},
)
```

注意事项：

- `symbols` 必须在遍历过程中保持一致性。
- `config` 中的 `target`/`hardware` 若提供，必须满足 target registry 的字段约束；发射阶段不得修改这些值。

返回与限制：

- 返回上下文实例，用于发射函数调用。

### `emit_mlir(node, ctx)`

功能说明：

- 将单个 AST 节点转换为 MLIR op/value。
- 该函数按节点类型分发到对应的发射规则。

参数说明：

- `node` (`object`)：AST 节点。
- `ctx` (`EmitContext`)：发射上下文。

使用示例：

```python
value = emit_mlir(expr_ast, ctx)
```

注意事项：

- 表达式节点应返回 MLIR value。
- 语句节点可返回 `None` 或返回生成的 op（以实现为准）。
- 不支持的节点必须抛出可定位的错误。

返回与限制：

- 表达式节点返回 MLIR value。
- 语句节点返回 `None` 或 op 对象（以实现为准）。

## 额外补充

- `emit_mlir` 必须覆盖 AST 中每一种节点类型。
- AST -> MLIR owner 边界如下；除表中“结构/签名 owner”外，其余 node-level lowering 都不得在 `mlir_gen` / `ast_visitor` 里复制一套并行规则：

  | AST 家族 | 节点 | owner | lowering / 行为 |
  | --- | --- | --- | --- |
  | 结构容器 | `ModuleAST` / `FunctionAST` / `BlockAST` | `mlir_gen` builder / `AstVisitor` | 组织 `builtin.module`、`func.func` 与 block 顺序；不直接发射单个 emit op。 |
  | 签名输入 | `TensorAST` / `ScalarArgAST` | `signature.py` / `function_builder.py` | 决定当前已支持的 `func.func` 输入签名与 block args；emit 只读取既有 SSA 绑定。 |
  | AST-only 签名节点 | `PtrArgAST` | AST / parser | 当前不进入 builder/signature 支持面；若流入 `mlir_gen`，必须按实现现状报 `Unsupported input type`。 |
  | 值与索引 | `ConstAST` / `VarAST` | `value.py` + core emit | 生成 builtin literal / `symbol.const`，或从 cache / `ctx.symbols` 复用已有 SSA value。 |
  | symbol family | `ForAST` / `TensorAxisAccessAST` / `SymbolToFloatAST` | `control_flow.py` / `call_symbol.py` + core emit | 生成 `symbol.for`、`symbol.get_dim`、`symbol.get_stride`、`symbol.to_float`。 |
  | DMA family | `LoadAST` / `StoreAST` / `DmaAllocAST` / `DmaCopyAST` / `DmaCastAST` / `DmaViewAST` / `DmaReshapeAST` / `DmaFlattenAST` / `DmaFreeAST` | `call_dma.py` + core emit | 生成 `dma.load/store/slice/deslice/alloc/copy/cast/view/reshape/free`。 |
  | NN family | `BinaryExprAST` / `CompareExprAST` / `NnBroadcastAST` / `NnBroadcastToAST` / `NnTransposeAST` / `NnUnaryAST` / `NnReduceAST` / `NnSoftmaxAST` / `Img2ColAST` / `MatmulAST` / `FCAST` / `ConvAST` | core emit + `type_utils.py` / `shape_utils.py` | 生成 `nn.*` 或 raw `nn + dma` 组合；具体 helper 不再使用旧 `CallAST(...)` 口径。 |
  | arch family | `ArchQueryAST` / `ArchGetDynamicMemoryAST` / `ArchLaunchKernelAST` | `call_arch.py` + core emit | 生成 `arch.get_*` / `arch.get_dynamic_memory` / `arch.launch`。 |
  | arch barrier | `ArchBarrierAST` | core emit | 生成无返回值 `arch.barrier`，不在 `call_arch.py` 内重复定义。 |
  | Python callee | `PythonCalleeCallAST` | `dispatch.py` + core emit | 通过 callee registry 生成 `func.call`；不得混入 helper family 细节。 |

- 默认使用当前项目的目标 dialect（例如 `nn`），但节点到 op 的映射必须清晰可追踪。
- `LoopRange` 触发的 `ForAST` 必须走 `symbol.for` 分支，并保持 `SymbolValueType` / `SymbolIterType` 直接作为 DMA operand 传递。
- 当 `CompareExprAST` 的两侧均为 `!symbol.int<"expr">` 时，symbol compare family 必须一一 lowering 为对应 `symbol` dialect op，且结果类型统一为 `i1`：
  - `a == b` -> `symbol.eq`
  - `a != b` -> `symbol.ne`
  - `a < b` -> `symbol.lt`
  - `a <= b` -> `symbol.le`
  - `a > b` -> `symbol.gt`
  - `a >= b` -> `symbol.ge`
- 当比较表达式尝试进入 symbol 路径但任一操作数不是 `!symbol.int<"expr">` 时，必须报具体的 symbol compare operand 类型错误；不得继续使用笼统 `Unsupported symbol compare op` 作为 `ne/lt/le/gt` 的长期失败边界。
- 当 `CompareExprAST` 进入 memory 路径时，`lhs/rhs` 必须为 `nn.memory` 类型且 `element_type`/`space` 一致；必要时执行隐式 broadcast。若 `element_type`/`space` 不一致或 broadcast 失败，必须报错并保留位置（例如 `Binary op operands must have the same element_type`、`Binary op operands must have the same space`、`Implicit broadcast dimension mismatch`）。memory 路径的比较结果 element type 必须为 `i1`，并保持与 broadcast 对齐后的 shape/space 一致。
- 当 tensor `truediv` 两侧 dtype 不一致时，必须按固定优先级决议目标 dtype，并在 lowering 中插入 `dma.cast`；`nn.truediv` 的结果类型必须与决议 dtype 一致。
- 当二元算术 mixed dtype 需要插入显式 cast 时（由上游判定并生成 `DmaCastAST`），`emit_mlir` 必须发射 `dma.cast` 并保证 `nn.sub` 的结果类型与 dtype promotion 结果一致；当前公开覆盖仅限 `nn.sub` 的 mixed dtype 场景。
- 当 `BinaryExprAST(op="mul")` 走 memory 路径时，`emit_mlir` 必须负责 `dtype promotion + dma.cast + broadcast` 的完整对齐流程：`element_type` 不一致时按 `i32 < f16 < f32` 决议目标类型并插入最少 `dma.cast`，shape 不一致时按 implicit broadcast 对齐；若 `space` 不一致必须报错 `Binary op operands must have the same space`，若 dtype 组合不受支持则报错 `Binary op operands must have the same element_type`。
- 当 `Img2ColAST(kind="img2col1d" | "img2col2d")` 进入 emit 阶段时，helper 参数必须一一映射到 `nn.img2col1d/nn.img2col2d` 属性与 operand；若参数个数或类型不匹配，必须在 emit 入口报错并保留位置。
- DMA/NN helper lowering 矩阵与失败边界如下（emit 阶段必须在入口校验并保留错误位置）：

  **DMA helper lowering**

  | helper | lowering | 结果 | 非法输入失败边界 |
  | --- | --- | --- | --- |
  | `alloc(...)` | `dma.alloc` | memory value | 参数个数/类型不匹配、`shape/stride/format` 不可规范化时必须报错。 |
  | `copy(...)` | `dma.alloc + dma.copy(target, source)` | memory value（返回 alloc 结果） | `source` 不是 `nn.memory` 或目标空间参数非法时必须报错。 |
  | `cast(...)` | `dma.cast` | memory value | `source` 不是 `nn.memory` 或 `dtype` 非法时必须报错。 |
  | `view(...)` | `dma.view` | memory value | `source` 非 `nn.memory` 或 `offset/size/stride` 不满足 DMA helper 约束时必须报具体的 `view(...)` lowering 错误。 |
  | `reshape(...)` | `dma.reshape` | memory value | `source` 非 `nn.memory`、非连续布局或 `numel` 不一致时必须报错。 |
  | `flatten(...)` | `dma.reshape`（一维） | memory value | `source` 非 `nn.memory` 或非连续布局时必须报错。 |
  | `load(...)` | `dma.load` | memory value | `source` 非 `nn.memory` 或索引/space 参数非法时必须报错。 |
  | `slice(...)` | `dma.alloc + dma.slice` | memory value（返回 alloc 结果） | `source` 非 `nn.memory` 或索引/space 参数非法时必须报错。 |
  | `store(...)` | `dma.store` | 语句 | `source/target` 非 `nn.memory` 或索引参数非法时必须报错。 |
  | `deslice(...)` | `dma.deslice` | 语句 | 与 `store(...)` 相同。 |
  | `free(...)` | `dma.free` | 语句 | 见下方固定诊断约定。 |

  **NN helper lowering**

  | helper | lowering | 结果 | 非法输入失败边界 |
  | --- | --- | --- | --- |
  | `img2col1d(...)` | `nn.img2col1d` | memory value | 参数个数或类型不匹配时必须在 emit 入口报错并保留位置。 |
  | `img2col2d(...)` | `nn.img2col2d` | memory value | 参数个数或类型不匹配时必须在 emit 入口报错并保留位置；窗口化协同仅使用 `dma.slice/dma.deslice`。 |
  | `matmul(...)` | `nn.matmul` | memory value | `space` 不一致、rank 不是 `2`、contracting dim 不匹配或 `element_type` 不一致时必须在 emit 入口报具体 lowering 错误。 |
  | `conv(...)` | `nn.img2col2d + dma.reshape + nn.matmul + dma.reshape` | memory value | 参数个数错误必须在 AST/emit 入口显式失败；非法 stride/padding、dtype/space/rank 不匹配时必须报具体错误，不得生成 `nn.conv`。 |

  **固定诊断约定**
  - `free` 参数个数非法必须报错 `Unsupported free arity`。
  - `free` source 非 `nn.memory` 必须报错 `Operand must be nn.memory`。
- 当 AST 表达 `float(symbol.int)` 转换入口时，`emit_mlir` 必须 lowering 为 `symbol.to_float`，返回 `f32` 结果；`float(n) -> symbol.to_float` 是当前公开合同。若 source 不是 `!symbol.int<"expr">`，则必须报具体的 source 类型错误，而不是继续使用笼统 `Unsupported annotation` 或 generic unsupported 失败边界。
- img2col helper 的公开 lowering 约束如下：
  - `img2col1d(...)`：lowering 为 `nn.img2col1d`，返回 `nn.memory` 结果。
  - `img2col2d(...)`：lowering 为 `nn.img2col2d`，返回 `nn.memory` 结果。
  - 涉及窗口化分块时，`loop + dma.slice/dma.deslice` 仅作为节点级 emit 协同路径；不得在本层引入 kernel dialect 或 `nn_lowering` 语义。
- `matmul(...)` helper 的公开 lowering 约束如下：
  - `matmul(lhs, rhs)`：lowering 为 `nn.matmul`，返回 `nn.memory` 结果。
  - 若 `lhs/rhs` 的 `element_type` 不一致，emit 层必须报错 `matmul element_type must match`，不得插入 `dma.cast`。
  - 若 `space` 不一致、rank 不是 `2`、或 contracting dim 不匹配，必须在 emit 入口报具体 lowering 错误。
- `conv(...)` helper 的公开 lowering 约束如下：
  - `conv(value, weight, ...)`：lowering 为 raw `nn.img2col2d + dma.reshape + nn.matmul + dma.reshape`，返回 `nn.memory` 结果。
  - `conv` 的输出类型必须与 `kernel_gen.operation.nn.conv(...)` 的公式保持一致；符号输出维度允许以等价表达式形式出现。
  - 非法 stride/padding、非法 rank、dtype/space 不一致、输入通道不匹配等情况必须在 emit 入口显式失败；不得生成 `nn.conv`。

节点映射补充示例：

- `ModuleAST` / `FunctionAST` / `BlockAST`：由 `mlir_gen` builder / `AstVisitor` 负责组织 `builtin.module`、`func.func` 与 block 顺序；它们不是单个 emit op 的 direct input。
- `TensorAST` / `ScalarArgAST`：由签名 builder 决定 block args / `func.func` 输入类型；emit 只消费 `ctx.symbols` / `ctx.types` 中已有绑定。
- `PtrArgAST`：当前只保留 AST / parser 层签名语义，不属于已支持的 emit 输入绑定；若误流入 builder/signature，必须报 `Unsupported input type`。
- `ConstAST`：生成常量或等价字面量 op/value；symbol 整数路径可生成 `symbol.const`。
- `VarAST`：从 `ctx.symbols` / cache 读取既有 SSA value，不得隐式制造新的变量 op。
- `BinaryExprAST(add/sub/mul/div/floordiv)`：生成对应的 symbol / `nn` 二元算术 op，并按本文件约束执行 promotion / broadcast。
- `CompareExprAST(eq/ne/lt/le/gt/ge)`：在 memory 路径生成对应 `nn` 比较 op（结果 `element_type` 为 `i1`），必要时隐式 broadcast；在 symbol 路径按 DSL 写法一一生成 `symbol.eq/symbol.ne/symbol.lt/symbol.le/symbol.gt/symbol.ge`。
- `LoadAST`：生成读取相关 op/value；无 `sizes` 时发射 `dma.load`，携带 `sizes` 时发射 `dma.slice` 并返回 alloc 结果。
- `StoreAST`：生成写入相关 op；无 `sizes` 时发射 `dma.store`，携带 `sizes` 时发射 `dma.deslice`。
- `DmaAllocAST` / `DmaCopyAST` / `DmaCastAST` / `DmaViewAST` / `DmaReshapeAST` / `DmaFlattenAST` / `DmaFreeAST`：分别生成 `dma.alloc` / `dma.copy` / `dma.cast` / `dma.view` / `dma.reshape` / 一维 `dma.reshape` / `dma.free`。
- `NnBroadcastAST`：生成 `nn.broadcast`，结果类型必须与 target memory type 一致。
- `NnBroadcastToAST`：按 `target_shape + space` 生成 `nn.broadcast`，输出 shape 由 `target_shape` 推导。
- `NnTransposeAST`：生成 `nn.transpose`。
- `NnUnaryAST`：当前公开覆盖至少包含 `kind="exp"` -> `nn.exp`；其余 unary kind 是否开放，以实现和测试的既有口径为准，本轮不新增新 unary 合同。
- `NnReduceAST`：按 `kind` 生成 `nn.reduce_sum` / `nn.reduce_min` / `nn.reduce_max`。
- `NnSoftmaxAST`：生成 `nn.softmax`。
- `Img2ColAST(kind="img2col1d" | "img2col2d")`：分别生成 `nn.img2col1d` / `nn.img2col2d` memory 结果。
- `MatmulAST`：生成 `nn.matmul` memory 结果；`element_type` 不一致必须报错，不得插入 `dma.cast`。
- `FCAST`：生成 `nn.transpose(weight) + nn.matmul(value, transposed_weight)` 的两段组合，输出 shape 为 `[M, N]`。
- `ConvAST`：生成 raw `nn.img2col2d + dma.reshape + nn.matmul + dma.reshape` memory 结果，不得生成 `nn.conv`。
- `SymbolToFloatAST`：生成 `symbol.to_float`，返回 `f32`。
- `TensorAxisAccessAST(kind="shape")`：生成 `symbol.get_dim`，返回 `!symbol.int<"...">`。
- `TensorAxisAccessAST(kind="stride")`：生成 `symbol.get_stride`，返回 `!symbol.int<"...">`。
- `ForAST`：当来源于 `LoopRange(start, end, step)` 且边界为 symbol 整数时，生成 `symbol.for`；`start/end/step` 保持 `!symbol.int<"expr">`，循环块参数 `it` 保持 `!symbol.iter<...>`；循环体内相关 DMA operand 直接复用这些 symbol value，不生成 `arith.index_cast`。
- `ArchQueryAST(query_name="get_block_id" | "get_block_num" | "get_subthread_id" | "get_subthread_num" | "get_thread_id" | "get_thread_num")`：生成对应 `arch.get_*`，返回匹配的 `!symbol.int<"...">`。
- `ArchGetDynamicMemoryAST(space=...)`：生成 `arch.get_dynamic_memory`，返回 `!nn.memory<[?], [1], i8, #nn.space<space>>`。
- `ArchBarrierAST(visibility, scope)`：生成无返回值 `arch.barrier {scope = #arch.scope<...>, visibility = [#arch.visibility<...>, ...]}`。
- `ArchLaunchKernelAST(callee, block, thread, subthread, args)`：生成无返回值 `arch.launch<%block, %thread, %subthread>(@callee, %arg0, %arg1, ...) : ... -> ()`。
- `PythonCalleeCallAST(callee, args)`：通过 callee registry 生成 `func.call @callee(args...)`，且 callee 必须预先存在于 `mlir_gen` 的闭包收集结果中。

## 测试

- 测试文件：[`test/dsl/test_emit_mlir.py`](../../test/dsl/test_emit_mlir.py)
- 拆分测试文件：
  - [`test/dsl/mlir_gen/emit/test_call_arch.py`](../../test/dsl/mlir_gen/emit/test_call_arch.py)
  - [`test/dsl/mlir_gen/emit/test_call_dma.py`](../../test/dsl/mlir_gen/emit/test_call_dma.py)
  - [`test/dsl/mlir_gen/emit/test_call_symbol.py`](../../test/dsl/mlir_gen/emit/test_call_symbol.py)
  - [`test/dsl/mlir_gen/emit/test_dispatch.py`](../../test/dsl/mlir_gen/emit/test_dispatch.py)
  - [`test/dsl/mlir_gen/emit/test_control_flow.py`](../../test/dsl/mlir_gen/emit/test_control_flow.py)
  - [`test/dsl/mlir_gen/emit/test_value.py`](../../test/dsl/mlir_gen/emit/test_value.py)
  - [`test/dsl/mlir_gen/emit/test_type_utils.py`](../../test/dsl/mlir_gen/emit/test_type_utils.py)
  - [`test/dsl/mlir_gen/emit/test_shape_utils.py`](../../test/dsl/mlir_gen/emit/test_shape_utils.py)
- 集成测试文件：[`test/dsl/test_mlir_gen.py`](../../test/dsl/test_mlir_gen.py)
- 补充测试文件：[`test/dsl/test_ast_visitor.py`](../../test/dsl/test_ast_visitor.py)
- 执行命令（emit 单测）：`pytest -q test/dsl/test_emit_mlir.py`
- 执行命令（emit 拆分单测）：`pytest -q test/dsl/mlir_gen/emit`
- 执行命令（emit 端到端回归）：`pytest -q test/dsl/test_mlir_gen.py`
- 执行命令（ast_visitor 负路径）：`pytest -q test/dsl/test_ast_visitor.py`
- 拆分归属：EMIT-001~EMIT-028、EMIT-033~EMIT-035 默认归属 [`test_emit_mlir.py`](../../test/dsl/test_emit_mlir.py)；EMIT-029 默认归属 [`test_mlir_gen.py`](../../test/dsl/test_mlir_gen.py)；EMIT-031/031A/032 归属 [`test_ast_visitor.py`](../../test/dsl/test_ast_visitor.py)、[`test_mlir_gen.py`](../../test/dsl/test_mlir_gen.py) 的联合回归。当前 `barrier/launch` 专项测试缺口在下游实现+补测阶段补齐。
- 编号口径：EMIT-001A/EMIT-001B/EMIT-030/EMIT-030A 为有效拆分编号，纳入本清单映射；其中 EMIT-030 绑定 `get_thread_num` helper 参数约束用例，EMIT-030A 绑定 `arch.get_thread_num` 正向 lowering 用例。
- 测试目标：
  - 覆盖常见表达式与语句节点的发射结果。
  - 覆盖 `lhs != rhs` 到 `CompareExprAST(op="ne")` 的 memory lowering：`nn.ne` 结果为 `i1`，并支持 implicit broadcast。
  - 覆盖 `CompareExprAST(op="ne")` memory 路径在不可 broadcast 与 element type 不一致时的错误分支与诊断文案。
  - 覆盖 `LoopRange` -> `symbol.for` 与 `it`/DMA operand 直接保持 `symbol.iter` / `symbol.int` 的发射规则。
  - 覆盖 `img2col1d/img2col2d` helper 的 emit 节点级规则：分别 lowering 为 `nn.img2col1d/nn.img2col2d`，且不引入 kernel dialect / `nn_lowering` / `cpu::img2col2d` 语义。
  - 覆盖 `img2col2d` 与 `loop + dma.slice/dma.deslice` 的协同 emit 规则，确保窗口读取/回写与循环节点映射保持一致。
  - 覆盖 `matmul(...)` helper 的 emit 节点级规则：lowering 为 `nn.matmul`，`element_type` 不一致必须报错。
  - 覆盖 `alloc target + deslice` 写回路径，确保 memory 表达式 target 可直接参与 emit，不退回旧的输入张量限定。
  - 覆盖 DMA helper 调用的 lowering 结果与语句/表达式边界：`alloc/copy/cast/view/reshape/flatten` 产生 memory 结果，`free` 为无返回值语句且会发射 `dma.free`。
  - 覆盖 `free` helper 的参数边界：非法参数个数与非法 source 类型分别保持 `Unsupported free arity`、`Operand must be nn.memory` 诊断口径。
  - 覆盖 `ArchQueryAST(query_name="get_block_id")` lowering 为 `arch.get_block_id` 的最小查询路径。
  - 覆盖 `ArchQueryAST(query_name="get_block_num")` lowering 为 `arch.get_block_num` 的最小查询路径。
  - 覆盖 `ArchQueryAST(query_name="get_subthread_id")` lowering 为 `arch.get_subthread_id` 的最小查询路径。
  - 覆盖 `ArchQueryAST(query_name="get_subthread_num")` lowering 为 `arch.get_subthread_num` 的最小查询路径。
  - 覆盖 `ArchQueryAST(query_name="get_thread_id")` lowering 为 `arch.get_thread_id` 的最小查询路径。
  - 覆盖 `ArchQueryAST(query_name="get_thread_num")` lowering 为 `arch.get_thread_num` 的最小查询路径。
  - 覆盖 `get_thread_num` helper 的参数约束错误路径，确保 `ArchQueryAST(query_name="get_thread_num")` 的入口边界稳定。
  - 覆盖 `ArchGetDynamicMemoryAST(space=...)` lowering 为 `arch.get_dynamic_memory` 的结果类型与 `space` 约束错误路径。
  - 覆盖 `ArchBarrierAST(visibility, scope)` lowering 为 `arch.barrier` 的语句语义与固定错误短语，确保 `barrier(...)` 不会被静默当成未知 helper。
  - 覆盖 `ArchLaunchKernelAST(callee, block, thread, subthread, args)` lowering 为 `arch.launch<...>(@callee, args...)` 的语句语义与参数错误路径，确保 `callee` 为函数对象 / symbol ref 而不是字符串。
  - 覆盖 `TensorAxisAccessAST(kind="shape")` lowering 为 `symbol.get_dim`，并校验 `axis` 与 `nn.memory` 前置约束。
  - 覆盖 `TensorAxisAccessAST(kind="stride")` lowering 为 `symbol.get_stride`，并校验 `axis` 与 `nn.memory` 前置约束。
  - 覆盖不支持节点的错误路径。
- 功能与用例清单：
  - EMIT-001：二元表达式节点生成对应 op/value。（`test_emit_context_reuses_cached_value`）
  - EMIT-001A：`BinaryExprAST` 在 symbol 路径支持 `add/sub/mul/div/floordiv` 并对非法操作符报错。（`test_emit_mlir.py::test_emit_mlir_lower_expr_unknown_and_symbol_errors`、`test_ast_visitor.py::test_emit_mlir_lower_expr_unknown_and_symbol_errors`）
  - EMIT-001B：`BinaryExprAST` 类型推导需覆盖 symbol/memory 路径边界及 `broadcast/element_type/space` 错误分支。（`test_emit_mlir.py::test_emit_mlir_infer_expr_type_branches`、`test_ast_visitor.py::test_emit_mlir_infer_expr_type_branches`）
  - EMIT-002：比较表达式节点生成对应 op/value。（`test_emit_mlir_compare_expr_emits_eq`）
  - EMIT-003：不支持节点抛出错误并携带位置信息。（`test_emit_mlir_unsupported_node_reports_location`）
  - EMIT-004：`TensorAST` 可通过符号表直接解析。（`test_emit_mlir_tensor_uses_symbol_table`）
  - EMIT-005：`LoadAST` 生成 `dma.load`。（`test_load_ast_lowering_rejected`）
  - EMIT-006：`StoreAST` 生成 `dma.store`。（`test_store_ast_lowering_rejected`）
  - EMIT-007：非 unit stride 抛出可定位错误。（`test_load_ast_lowering_raises_lowering_error`）
  - EMIT-008：索引 rank mismatch 抛出可定位错误。（`test_load_ast_index_rank_mismatch_reports_location`）
  - EMIT-009：`StoreAST` 输入非 memory 抛出错误。（`test_store_ast_lowering_raises_lowering_error`）
  - EMIT-010：`ForAST` 在 `LoopRange` 场景下 lowering 为 `symbol.for`，其中 `start/end/step` 保持 `!symbol.int<"...">`、循环块参数 `it` 保持 `!symbol.iter<...>`，循环体内相关 DMA operand 直接复用这些 symbol value，不生成 `arith.index_cast`。（`test_emit_mlir_symbolic_for_loop_avoids_index_cast`）
  - EMIT-011：循环变量表初始化与非法配置报错路径。（`test_emit_mlir_loop_vars_validation`）
  - EMIT-011B：`EmitContext` 校验 `config.target` 命名约束的错误路径。（`test_emit_context_rejects_invalid_target_name`）
  - EMIT-011C：`EmitContext` 校验 `config.hardware` 字段约束的错误路径。（`test_emit_context_rejects_invalid_hardware_field`）
  - EMIT-012：类型推导与 broadcast 错误分支。（`test_emit_mlir_infer_expr_type_branches`）
  - EMIT-012B：`emit_mlir` lowering 的错误分支覆盖（常量、load/store、symbol binary op、compare 等）。（`test_emit_mlir.py::test_emit_mlir_lower_expr_branches`、`test_ast_visitor.py::test_emit_mlir_lower_expr_branches`）
  - EMIT-012A：索引解析与 rank mismatch 的错误路径。（`test_emit_mlir.py::test_emit_mlir_index_expr_rejections`、`test_ast_visitor.py::test_emit_mlir_index_expr_rejections`）
  - EMIT-012C：stride/layout/index 辅助函数与非 unit stride 拒绝路径。（`test_emit_mlir.py::test_emit_mlir_stride_and_layout_helpers`、`test_ast_visitor.py::test_emit_mlir_stride_and_layout_helpers`）
  - EMIT-012D：索引解析与 loop_vars 查表分支。（`test_emit_mlir.py::test_emit_mlir_index_resolution_helpers`、`test_ast_visitor.py::test_emit_mlir_index_resolution_helpers`）
  - EMIT-013：默认 stride 推导遇到未知 attr 的分支。（`test_emit_mlir.py::test_emit_mlir_default_stride_handles_unknown_attr`、`test_ast_visitor.py::test_emit_mlir_default_stride_handles_unknown_attr`）
  - EMIT-014：`ForAST` lowering 会保留循环结构并在循环体内生成 `dma.load`。（`test_for_ast_lowering_emits_loads`）
  - EMIT-015：`alloc(...)` lowering 为 `dma.alloc` 并返回 memory 结果。（`test_emit_mlir_dma_alloc_lowering`）
  - EMIT-016：`copy(...)` lowering 为 `dma.copy` 并返回目标 memory 结果。（`test_emit_mlir_dma_copy_lowering`）
  - EMIT-017：`cast(...)` lowering 为 `dma.cast` 并返回转换后的 memory 结果。（`test_emit_mlir_dma_cast_lowering`）
  - EMIT-018：`view(...)` lowering 为 `dma.view` 并返回视图 memory 结果；source 或 DMA 参数不合法时必须报具体 `view(...)` lowering 错误，而不是 generic unsupported。（`test_emit_mlir_dma_view_lowering`）
  - EMIT-019：`reshape(...)` lowering 为 `dma.reshape` 并返回重排后的 memory 结果。（`test_emit_mlir_dma_reshape_lowering`）
  - EMIT-020：`flatten(...)` 以一维 `reshape` 语义 lowering，返回一维 memory 结果。（`test_emit_mlir_dma_flatten_lowering`）
  - EMIT-021：`free(...)` 作为无返回值语句执行，不产生新的 SSA 结果。（`test_emit_mlir_dma_free_statement`）
  - EMIT-022：`ArchQueryAST(query_name="get_block_id")` lowering 为单个 `arch.get_block_id`，并返回 `!symbol.int<"block_id">`。（`test_emit_mlir_lowers_arch_get_block_id_query`）
  - EMIT-023：`ArchQueryAST(query_name="get_block_num")` lowering 为单个 `arch.get_block_num`，并返回 `!symbol.int<"block_num">`。（`test_emit_mlir_lowers_arch_get_block_num_query`）
  - EMIT-024：纯 symbol 标量 compare family 在 emit 阶段按 DSL 写法一一 lowering 为 `symbol.eq/ne/lt/le/gt/ge`，结果均为 `i1`；`ge` 已有回归测试，`gt/le/lt/ne` 当前冻结为下游待补测试映射。（现有映射：`test_emit_mlir.py::test_emit_mlir_lowers_symbol_ge`、`test_ast_visitor.py::test_emit_mlir_lowers_symbol_ge`；下游待补测试映射：`test_emit_mlir_lowers_symbol_gt`、`test_emit_mlir_lowers_symbol_le`、`test_emit_mlir_lowers_symbol_lt`、`test_emit_mlir_lowers_symbol_ne`）
  - EMIT-025：`ArchQueryAST(query_name="get_subthread_id")` lowering 为单个 `arch.get_subthread_id`，并返回 `!symbol.int<"subthread_id">`。（`test_emit_mlir_lowers_arch_get_subthread_id_query`）
  - EMIT-026：`ArchQueryAST(query_name="get_thread_id")` lowering 为单个 `arch.get_thread_id`，并返回 `!symbol.int<"thread_id">`。（`test_emit_mlir_lowers_arch_get_thread_id_query`）
  - EMIT-027：`ArchQueryAST(query_name="get_subthread_num")` lowering 为单个 `arch.get_subthread_num`，并返回 `!symbol.int<"subthread_num">`。（`test_emit_mlir_lowers_arch_get_subthread_num_query`）
  - EMIT-030A：`ArchQueryAST(query_name="get_thread_num")` lowering 为单个 `arch.get_thread_num`，并返回 `!symbol.int<"thread_num">`。（`test_emit_mlir.py::test_emit_mlir_lowers_arch_get_thread_num_query`）
  - EMIT-030：`get_thread_num` helper 仅允许零参数调用；非零参数必须报错 `Unsupported get_thread_num arity`，以保证 `ArchQueryAST(query_name="get_thread_num")` 的入口约束稳定。（`test_ast_visitor.py::test_parse_function_rejects_invalid_get_thread_num_arity_variants`）
  - EMIT-029：tensor `truediv` mixed dtype promotion 需插入 `dma.cast`，且 `nn.truediv` 结果类型与决议 dtype 一致。（`test_mlir_gen.py::test_tensor_truediv_dtype_promotion_lowering`、`test_ast_visitor.py::test_tensor_truediv_dtype_promotion_lowering`）
  - EMIT-031：`ArchGetDynamicMemoryAST(space=...)` lowering 为 `arch.get_dynamic_memory`，并固定返回 `!nn.memory<[?], [1], i8, #nn.space<space>>`；非法 `space` 必须报错。（`test_ast_visitor.py::test_emit_mlir_rejects_invalid_arch_get_dynamic_memory_space`）
  - EMIT-031A：`ArchBarrierAST(visibility=[BarrierVisibility.TSM, BarrierVisibility.TLM], scope=BarrierScope.BLOCK)` 必须 lowering 为单个无返回值 `arch.barrier {scope = #arch.scope<block>, visibility = [#arch.visibility<tsm>, #arch.visibility<tlm>]}`；空 visibility、非法元素类型或非法 scope 必须分别报 `barrier visibility must be non-empty BarrierVisibility list`、`barrier scope must be BarrierScope`。（下游待补测试映射：`test_emit_mlir_lowers_arch_barrier`）
  - EMIT-032：`ArchLaunchKernelAST(callee="add_barrier_body", block, thread, subthread, args=[lhs, rhs, out])` lowering 为单个无返回值 `arch.launch<%block, %thread, %subthread>(@add_barrier_body, %lhs, %rhs, %out) : ... -> ()`；extent 必须为正整数 `!symbol.int`，非法 `callee`/keyword args/extent 必须报错，并保持 launched body 的 `get_thread_num()` 语义来自当前 launch extent。（下游待补测试映射：`test_emit_mlir_lowers_arch_launch_with_callee`）
  - EMIT-033：`TensorAxisAccessAST(kind="shape")` 必须 lowering 为 `symbol.get_dim`，并保持 `axis` 为静态非负整数且未越界；非 `nn.memory` 来源或非法 `axis` 必须报错。（[`test_emit_mlir.py`](../../test/dsl/test_emit_mlir.py)）
  - EMIT-034：`TensorAxisAccessAST(kind="stride")` 必须 lowering 为 `symbol.get_stride`，并保持 `axis` 为静态非负整数且未越界；非 `nn.memory` 来源或非法 `axis` 必须报错。（[`test_emit_mlir.py`](../../test/dsl/test_emit_mlir.py)）
  - EMIT-002A：`CompareExprAST(op="ne")` 在 memory 路径必须生成 compare op（必要时带 `nn.broadcast`），结果 element type 为 `i1`。（`test_emit_mlir_binary_compare_broadcast_rhs`）
  - EMIT-002B：`CompareExprAST(op="ne")` memory 路径在不可 broadcast 或 element type/space 不一致时必须报错并保持固定诊断文案。（`test_emit_mlir_compare_memory_mismatch_reports_diagnostics`）
  - EMIT-028：`nn.sub` mixed dtype promotion 触发 `dma.cast` 并保持 `nn.sub` 与 `func.return` 的结果类型与 promotion 结果一致。（`test_build_func_op_lowers_nn_sub_dtype_promotion_with_cast`）
  - EMIT-033：`nn.add` mixed memory+const/symbol lowering 需按 `i32 < f16 < f32` 执行 dtype promotion，`!symbol.int` 按 `i32` 参与决议；仅允许一侧为 memory 并按需插入 `dma.cast`，纯 scalar/symbol 双侧输入必须拒绝。（`test/dialect/test_nn_dialect.py::test_add_op_accepts_memory_const_rhs`、`test/dialect/test_nn_dialect.py::test_add_op_accepts_memory_symbol_rhs`、`test/dialect/test_nn_dialect.py::test_add_op_rejects_pure_scalar_operands`）
  - EMIT-034：`Img2ColAST(kind="img2col1d")` 必须 lowering 为 `nn.img2col1d`，并保持参数到属性/operand 的节点级一一映射；禁止引入 kernel dialect / `nn_lowering` / `cpu::img2col2d` 语义。（`test/dsl/test_emit_mlir.py::test_emit_mlir_img2col1d_lowering`）
  - EMIT-035：`Img2ColAST(kind="img2col2d")` 必须 lowering 为 `nn.img2col2d`，并与 `ForAST + dma.slice/dma.deslice` 协同路径保持节点级映射一致，循环迭代与 DMA 标量 operand 继续保持 `!symbol.int` 语义。（`test/dsl/test_emit_mlir.py::test_emit_mlir_img2col2d_with_loop_slice_deslice_lowering`、`test/dsl/test_mlir_gen.py::test_build_func_op_supports_symbolic_for_loop_dma_without_return`、`test/dsl/test_ast_visitor.py::test_build_func_op_supports_symbolic_for_loop_dma_without_return`）
  - EMIT-036：`float(symbol.int)` 必须 lowering 为 `symbol.to_float`，结果类型固定为 `f32`；source 非 `!symbol.int<"...">` 时必须报具体类型错误。（下游待补测试映射：`test_emit_mlir_lowers_symbol_to_float`）
  - EMIT-C1A：`MatmulAST` 必须 lowering 为 `nn.matmul`，`element_type` 不一致必须报错 `matmul element_type must match`；不得回退为 `Unsupported call expression`。（`test_emit_mlir_matmul_lowering`、`test_build_func_op_supports_matmul_helper_call`）
  - EMIT-C1C：`ConvAST` 必须在 emit 层分解为 raw `nn.img2col2d + dma.reshape + nn.matmul + dma.reshape`，不得生成 `nn.conv`；符号输出维度与非法参数错误口径需保持稳定。（`test_build_func_op_supports_conv_helper_call`、`test_build_func_op_supports_symbolic_conv_helper_call`、`test_build_func_op_conv_helper_rejects_invalid_stride`、`test_build_func_op_conv_helper_rejects_invalid_arity`）
  - EMIT-C1B：`conv2d_img2col2d_tiled_npu_demo(...)` 这类 `loop + slice + img2col2d + reshape + matmul + deslice + return` 前端样例，emit 层必须允许 `alloc` 结果作为 `deslice` target，并生成 raw IR 中的循环、`dma.alloc/slice/reshape/deslice`、`nn.img2col2d`、`nn.matmul` 与 `func.return`。（`test_emit_mlir_supports_conv2d_img2col2d_tiled_npu_demo_chain`、`test_build_func_op_supports_conv2d_img2col2d_tiled_npu_demo`、`test_build_func_op_supports_conv2d_img2col2d_tiled_npu_demo_frontend`）
