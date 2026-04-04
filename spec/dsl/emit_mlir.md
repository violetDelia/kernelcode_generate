# emit_mlir.md

## 功能简介

- 定义 AST 节点到 MLIR op/value 的转换规则。
- 为 `ast_visitor` 提供可调用的节点发射接口。
- 不负责 AST 解析与遍历，不负责 MLIR 文本输出。

## 文档信息

- 创建者：`规格小队`
- 最后一次更改：`睡觉小分队`
- `spec`：[`spec/dsl/emit_mlir.md`](../../spec/dsl/emit_mlir.md)
- `功能实现`：[`kernel_gen/dsl/emit_mlir.py`](../../kernel_gen/dsl/emit_mlir.py)
- `test`：[`test/dsl/test_emit_mlir.py`](../../test/dsl/test_emit_mlir.py)

## 依赖

- AST 节点定义：[`spec/dsl/ast.md`](../../spec/dsl/ast.md)
- AST 访问器：[`spec/dsl/ast_visitor.md`](../../spec/dsl/ast_visitor.md)
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

## 限制与边界

- 不解析 Python 函数，不遍历 AST。
- 不做优化、常量折叠或后端特化。
- 不生成 MLIR 文本；文本输出由上游调用方负责。
- 发射阶段仅消费 AST 与上下文，不向 AST 注入 `target`/`hardware` 字段；相关信息只能通过 `EmitContext` 或外部上下文传入。
- 当 `ForAST` 来自 `LoopRange(start, end, step)` 且边界与循环变量保持 symbol 整数语义时，必须 lowering 为 `symbol.for`，不得回退为 `scf.for`；其循环块参数 `it` 必须为 `!symbol.int<"expr">`。
- 在上述 `LoopRange` 场景中，循环变量以及传入 `dma.slice` / `dma.deslice` 的 `offsets`、`sizes`、`strides` 等 DMA 标量 operand 必须直接复用 `!symbol.int<"expr">` value，不得插入 `arith.index_cast`；若循环变量 `it` 退化为 `index`、普通整数或浮点类型，应视为 lowering 违规。
- 当 DSL AST 表达 `alloc`、`copy`、`cast`、`view`、`reshape`、`flatten`、`load`、`store`、`slice`、`deslice` 这组 DMA helper 调用时，`emit_mlir` 必须按对应 memory 语义 lowering；其中 `flatten` 公开上视为一维 `reshape` 语义，不要求生成独立 dialect op。
- 当 DSL AST 表达 `img2col1d(...)` 或 `img2col2d(...)` helper 调用时，`emit_mlir` 必须直接 lowering 为 `nn.img2col1d` 或 `nn.img2col2d`；不得在 emit 层引入 `kernel_dialect`、`nn_to_kernel` 或 `cpu::img2col2d` 相关语义。
- 当 DSL AST 表达 `matmul(lhs, rhs, memoryspace=...)` helper 调用时，`emit_mlir` 必须直接 lowering 为 `nn.matmul`；若左右操作数 `element_type` 不一致但 `space` 一致，必须按二元算术 dtype promotion 决议目标 dtype，并仅对非目标侧插入最少 `dma.cast`。
- `img2col2d` 的 emit 节点级流程允许并要求与循环/切片节点协作：窗口读取通过 `dma.slice`，窗口回写通过 `dma.deslice`，循环结构保持 `ForAST -> symbol.for`；该规则只约束 emit 节点映射，不扩展到 kernel/runtime 责任。
- `store(...)` / `deslice(...)` 的 target 允许来自前序 `alloc/view/reshape/flatten/cast/copy/img2col/matmul/get_dynamic_memory` 等 memory 表达式；emit 阶段必须对该 target 先求值再执行写回，不得退回只允许函数输入张量的旧口径。
- 当 `CompareExprAST(op="ne")` 来自 `lhs != rhs` 入口且两侧为 `nn.memory` 时，必须 lowering 为 `nn.ne`；允许按隐式 broadcast 规则插入 `nn.broadcast`，若无法广播必须报错 `Implicit broadcast dimension mismatch`，若 element type 不一致必须报错 `Binary op operands must have the same element_type`。
- 当 `BinaryExprAST(op="mul")` 来自 `lhs * rhs` 或 `nn.mul(lhs, rhs)` 入口且两侧为 `nn.memory` 时，必须 lowering 为 `nn.mul`；若 shape 不一致但可 broadcast，允许按需插入 `nn.broadcast`，若不可 broadcast 必须报错 `Implicit broadcast dimension mismatch`。当两侧 `element_type` 不一致但 `space` 一致时，必须按二元算术 dtype promotion（`i32 < f16 < f32`）决议目标 element_type，并仅对非目标侧插入 `dma.cast` 再发射 `nn.mul`；若 `space` 不一致必须报错 `Binary op operands must have the same space`。
- `free` 必须作为语句型 helper 处理，不产生新的 SSA 结果，并在 emit 阶段生成单个 `dma.free`。
- `ArchQueryAST(query_name="get_block_id")` 必须 lowering 为单个 `arch.get_block_id`，并保持结果类型为 `!symbol.int<"block_id">`。
- `ArchQueryAST(query_name="get_block_num")` 必须 lowering 为单个 `arch.get_block_num`，并保持结果类型为 `!symbol.int<"block_num">`。
- `ArchQueryAST(query_name="get_subthread_id")` 必须 lowering 为单个 `arch.get_subthread_id`，并保持结果类型为 `!symbol.int<"subthread_id">`。
- `ArchQueryAST(query_name="get_subthread_num")` 必须 lowering 为单个 `arch.get_subthread_num`，并保持结果类型为 `!symbol.int<"subthread_num">`。
- `ArchQueryAST(query_name="get_thread_id")` 必须 lowering 为单个 `arch.get_thread_id`，并保持结果类型为 `!symbol.int<"thread_id">`。
- `ArchQueryAST(query_name="get_thread_num")` 必须 lowering 为单个 `arch.get_thread_num`，并保持结果类型为 `!symbol.int<"thread_num">`。
- `ArchGetDynamicMemoryAST(space=...)` 必须 lowering 为单个 `arch.get_dynamic_memory`，结果类型固定为 `!nn.memory<[?], [1], i8, #nn.space<space>>`；`space` 非 `SM/LM/TSM/TLM` 时必须报错。
- `ArchLaunchKernelAST(name, block, thread, subthread)` 必须 lowering 为单个无返回值 `arch.launch_kernel`；extent 公开语义统一为 `!symbol.int` 启动规模：AST 虽允许 `int | SymbolDim` 入口，但 emit 阶段若 extent 不是 `!symbol.int<"...">`（或可静态判定为 `<= 0`）必须报错。
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
- 默认使用当前项目的目标 dialect（例如 `nn`），但节点到 op 的映射必须清晰可追踪。
- `LoopRange` 触发的 `ForAST` 必须走 `symbol.for` 分支，并保持 symbol 整数值直接作为 DMA operand 传递。
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
- 当 `CallAST(name="img2col1d"| "img2col2d")` 进入 emit 阶段时，helper 参数必须一一映射到 `nn.img2col1d/nn.img2col2d` 属性与 operand；若参数个数或类型不匹配，必须在 emit 入口报错并保留位置。
- DMA/NN helper lowering 矩阵与失败边界如下（emit 阶段必须在入口校验并保留错误位置）：

  **DMA helper lowering**

  | helper | lowering | 结果 | 非法输入失败边界 |
  | --- | --- | --- | --- |
  | `alloc(...)` | `dma.alloc` | memory value | 参数个数/类型不匹配、`shape/stride/format` 不可规范化时必须报错。 |
  | `copy(...)` | `dma.alloc + dma.copy` | memory value（返回 alloc 结果） | `source` 不是 `nn.memory` 或目标空间参数非法时必须报错。 |
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
  | `matmul(...)` | `nn.matmul`（必要时插入 `dma.cast`） | memory value | `space` 不一致、rank 不是 `2` 或 contracting dim 不匹配时必须在 emit 入口报具体 lowering 错误。 |

  **固定诊断约定**
  - `free` 参数个数非法必须报错 `Unsupported free arity`。
  - `free` source 非 `nn.memory` 必须报错 `Operand must be nn.memory`。
- 当 AST 表达 `float(symbol.int)` 转换入口时，`emit_mlir` 必须 lowering 为 `symbol.to_float`，返回 `f32` 结果；`float(n) -> symbol.to_float` 是当前公开合同。若 source 不是 `!symbol.int<"expr">`，则必须报具体的 source 类型错误，而不是继续使用笼统 `Unsupported annotation` 或 generic unsupported 失败边界。
- img2col helper 的公开 lowering 约束如下：
  - `img2col1d(...)`：lowering 为 `nn.img2col1d`，返回 `nn.memory` 结果。
  - `img2col2d(...)`：lowering 为 `nn.img2col2d`，返回 `nn.memory` 结果。
  - 涉及窗口化分块时，`loop + dma.slice/dma.deslice` 仅作为节点级 emit 协同路径；不得在本层引入 kernel dialect 或 `nn_to_kernel` 语义。
- `matmul(...)` helper 的公开 lowering 约束如下：
  - `matmul(lhs, rhs)`：lowering 为 `nn.matmul`，返回 `nn.memory` 结果。
  - 若 `lhs/rhs` 的 `element_type` 不一致但 `space` 一致，emit 层必须先按 promotion 结果插入必要的 `dma.cast` 再发射 `nn.matmul`。
  - 若 `space` 不一致、rank 不是 `2`、或 contracting dim 不匹配，必须在 emit 入口报具体 lowering 错误。

节点映射示例：

- `ConstAST`：生成常量或等价字面量 op/value。
- `BinaryExprAST(add/sub/mul/div/floordiv)`：生成对应的二元算术 op。
- `CompareExprAST(eq/ne/lt/le/gt/ge)`：在 memory 路径生成对应 `nn` 比较 op（结果 `element_type` 为 `i1`），必要时隐式 broadcast；在 symbol 路径按 DSL 写法一一生成 `symbol.eq/symbol.ne/symbol.lt/symbol.le/symbol.gt/symbol.ge`。
- `LoadAST`：生成张量读取相关 op/value；当携带 `sizes` 时发射 `dma.slice`。
- `StoreAST`：生成张量写入相关 op；当携带 `sizes` 时发射 `dma.deslice`。
- `CallAST(alloc/copy/cast/view/reshape/flatten)`：生成对应 DMA memory 结果。
- `CallAST(view)`：一一生成 `dma.view` memory 结果。
- `CallAST(float(symbol.int))`：生成 `symbol.to_float`，返回 `f32`。
- `CallAST(free)`：发射单个无返回值 `dma.free` 语句。
- `CallAST(img2col1d/img2col2d)`：分别生成 `nn.img2col1d/nn.img2col2d` memory 结果。
- `CallAST(matmul)`：生成 `nn.matmul` memory 结果，必要时伴随最少 `dma.cast`。
- `ForAST`：当来源于 `LoopRange(start, end, step)` 且边界为 symbol 整数时，生成 `symbol.for`；循环体内若包含 `dma.slice` / `dma.deslice`，其 DMA 标量 operand 直接使用 `!symbol.int<"expr">` value，不生成 `arith.index_cast`。
- `TensorAxisAccessAST(kind="shape")`：生成 `symbol.get_dim`，返回 `!symbol.int<"...">`。
- `TensorAxisAccessAST(kind="stride")`：生成 `symbol.get_stride`，返回 `!symbol.int<"...">`。
- `ArchQueryAST(query_name="get_block_id")`：生成 `arch.get_block_id`，返回 `!symbol.int<"block_id">`。
- `ArchQueryAST(query_name="get_block_num")`：生成 `arch.get_block_num`，返回 `!symbol.int<"block_num">`。
- `ArchQueryAST(query_name="get_subthread_id")`：生成 `arch.get_subthread_id`，返回 `!symbol.int<"subthread_id">`。
- `ArchQueryAST(query_name="get_subthread_num")`：生成 `arch.get_subthread_num`，返回 `!symbol.int<"subthread_num">`。
- `ArchQueryAST(query_name="get_thread_id")`：生成 `arch.get_thread_id`，返回 `!symbol.int<"thread_id">`。
- `ArchQueryAST(query_name="get_thread_num")`：生成 `arch.get_thread_num`，返回 `!symbol.int<"thread_num">`。
- `ArchGetDynamicMemoryAST(space=...)`：生成 `arch.get_dynamic_memory`，返回 `!nn.memory<[?], [1], i8, #nn.space<space>>`。
- `ArchLaunchKernelAST(name, block, thread, subthread)`：生成无返回值 `arch.launch_kernel`。

## 测试

- 测试文件：[`test/dsl/test_emit_mlir.py`](../../test/dsl/test_emit_mlir.py)
- 集成测试文件：[`test/dsl/test_mlir_gen.py`](../../test/dsl/test_mlir_gen.py)
- 补充测试文件：[`test/dsl/test_ast_visitor.py`](../../test/dsl/test_ast_visitor.py)
- 执行命令（emit 单测）：`pytest -q test/dsl/test_emit_mlir.py`
- 执行命令（emit 端到端回归）：`pytest -q test/dsl/test_mlir_gen.py`
- 执行命令（ast_visitor 负路径）：`pytest -q test/dsl/test_ast_visitor.py`
- 拆分归属：EMIT-001~EMIT-028、EMIT-033~EMIT-035 默认归属 `test_emit_mlir.py`；EMIT-029 默认归属 `test_mlir_gen.py`；EMIT-031/EMIT-032 归属 `test_ast_visitor.py`。其中 EMIT-012A/012B/012C/012D/013/024 在 `test_ast_visitor.py` 有边界回归覆盖；若条目显式标注跨文件映射，以条目为准。
- 编号口径：EMIT-001A/EMIT-001B/EMIT-030/EMIT-030A 为有效拆分编号，纳入本清单映射；其中 EMIT-030 绑定 `get_thread_num` helper 参数约束用例，EMIT-030A 绑定 `arch.get_thread_num` 正向 lowering 用例。
- 测试目标：
  - 覆盖常见表达式与语句节点的发射结果。
  - 覆盖 `lhs != rhs` 到 `CompareExprAST(op="ne")` 的 memory lowering：`nn.ne` 结果为 `i1`，并支持 implicit broadcast。
  - 覆盖 `CompareExprAST(op="ne")` memory 路径在不可 broadcast 与 element type 不一致时的错误分支与诊断文案。
  - 覆盖 `LoopRange` -> `symbol.for` 与 `it`/DMA operand 直接保持 `symbol.int` 的发射规则。
  - 覆盖 `img2col1d/img2col2d` helper 的 emit 节点级规则：分别 lowering 为 `nn.img2col1d/nn.img2col2d`，且不引入 kernel dialect / `nn_to_kernel` / `cpu::img2col2d` 语义。
  - 覆盖 `img2col2d` 与 `loop + dma.slice/dma.deslice` 的协同 emit 规则，确保窗口读取/回写与循环节点映射保持一致。
  - 覆盖 `matmul(...)` helper 的 emit 节点级规则：lowering 为 `nn.matmul`，必要时插入最少 `dma.cast`。
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
  - 覆盖 `ArchLaunchKernelAST(name, block, thread, subthread)` lowering 为 `arch.launch_kernel` 的语句语义与参数错误路径。
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
  - EMIT-010：`ForAST` 在 `LoopRange` 场景下 lowering 为 `symbol.for`，循环块参数 `it` 与循环体内相关 DMA operand 直接复用 `!symbol.int<"...">`，不生成 `arith.index_cast`。（`test_emit_mlir_symbolic_for_loop_avoids_index_cast`）
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
  - EMIT-032：`ArchLaunchKernelAST(name, block, thread, subthread)` lowering 为单个无返回值 `arch.launch_kernel`；extent 必须为正整数 `!symbol.int`，非法 `name`/extent 必须报错。（`test_ast_visitor.py::test_emit_mlir_rejects_invalid_arch_launch_kernel_args`）
  - EMIT-033：`TensorAxisAccessAST(kind="shape")` 必须 lowering 为 `symbol.get_dim`，并保持 `axis` 为静态非负整数且未越界；非 `nn.memory` 来源或非法 `axis` 必须报错。（`expectation/dsl/mlir_gen/dialect/symbol/get_dim.py`）
  - EMIT-034：`TensorAxisAccessAST(kind="stride")` 必须 lowering 为 `symbol.get_stride`，并保持 `axis` 为静态非负整数且未越界；非 `nn.memory` 来源或非法 `axis` 必须报错。（`expectation/dsl/mlir_gen/dialect/symbol/get_stride.py`）
  - EMIT-002A：`CompareExprAST(op="ne")` 在 memory 路径必须生成 compare op（必要时带 `nn.broadcast`），结果 element type 为 `i1`。（`test_emit_mlir_binary_compare_broadcast_rhs`）
  - EMIT-002B：`CompareExprAST(op="ne")` memory 路径在不可 broadcast 或 element type/space 不一致时必须报错并保持固定诊断文案。（`test_emit_mlir_compare_memory_mismatch_reports_diagnostics`）
  - EMIT-028：`nn.sub` mixed dtype promotion 触发 `dma.cast` 并保持 `nn.sub` 与 `func.return` 的结果类型与 promotion 结果一致。（`test_build_func_op_lowers_nn_sub_dtype_promotion_with_cast`）
  - EMIT-033：`nn.add` mixed memory+const/symbol lowering 需按 `i32 < f16 < f32` 执行 dtype promotion，`!symbol.int` 按 `i32` 参与决议；仅允许一侧为 memory 并按需插入 `dma.cast`，纯 scalar/symbol 双侧输入必须拒绝。（`test/dialect/test_nn_dialect.py::test_add_op_accepts_memory_const_rhs`、`test/dialect/test_nn_dialect.py::test_add_op_accepts_memory_symbol_rhs`、`test/dialect/test_nn_dialect.py::test_add_op_rejects_pure_scalar_operands`）
  - EMIT-034：`CallAST(img2col1d)` 必须 lowering 为 `nn.img2col1d`，并保持参数到属性/operand 的节点级一一映射；禁止引入 kernel dialect / `nn_to_kernel` / `cpu::img2col2d` 语义。（`test/dsl/test_emit_mlir.py::test_emit_mlir_img2col1d_lowering`）
  - EMIT-035：`CallAST(img2col2d)` 必须 lowering 为 `nn.img2col2d`，并与 `ForAST + dma.slice/dma.deslice` 协同路径保持节点级映射一致，循环迭代与 DMA 标量 operand 继续保持 `!symbol.int` 语义。（`test/dsl/test_emit_mlir.py::test_emit_mlir_img2col2d_with_loop_slice_deslice_lowering`、`test/dsl/test_mlir_gen.py::test_build_func_op_supports_symbolic_for_loop_dma_without_return`、`test/dsl/test_ast_visitor.py::test_build_func_op_supports_symbolic_for_loop_dma_without_return`）
  - EMIT-036：`float(symbol.int)` 必须 lowering 为 `symbol.to_float`，结果类型固定为 `f32`；source 非 `!symbol.int<"...">` 时必须报具体类型错误。（下游待补测试映射：`test_emit_mlir_lowers_symbol_to_float`）
  - EMIT-C1A：`CallAST(matmul)` 必须 lowering 为 `nn.matmul`，并在 mixed dtype memory 路径按需插入最少 `dma.cast`；不得回退为 `Unsupported call expression`。（`test_emit_mlir_matmul_lowering`、`test_build_func_op_supports_matmul_helper_call`）
  - EMIT-C1B：`conv2d_img2col2d_tiled_npu_demo(...)` 这类 `loop + slice + img2col2d + reshape + matmul + deslice + return` 前端样例，emit 层必须允许 `alloc` 结果作为 `deslice` target，并生成 raw IR 中的循环、`dma.alloc/slice/reshape/deslice`、`nn.img2col2d`、`nn.matmul` 与 `func.return`。（`test_emit_mlir_supports_conv2d_img2col2d_tiled_npu_demo_chain`、`test_build_func_op_supports_conv2d_img2col2d_tiled_npu_demo`、`test_build_func_op_supports_conv2d_img2col2d_tiled_npu_demo_frontend`）
