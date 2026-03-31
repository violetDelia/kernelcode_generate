# mlir_gen.md

## 功能简介

- 综合 AST 解析、AST 遍历与节点发射规则，将 Python 函数转换为 MLIR `func.func` op。
- 统一约束函数签名、参数与返回值的生成规则。
- 不生成 module，不负责文本打印。

## 文档信息

- 创建者：`榕`
- 最后一次更改：`不要啊教练`
- `spec`：[`spec/dsl/mlir_gen.md`](../../spec/dsl/mlir_gen.md)
- `功能实现`：[`kernel_gen/dsl/mlir_gen.py`](../../kernel_gen/dsl/mlir_gen.py)
- `test`：[`test/dsl/test_mlir_gen.py`](../../test/dsl/test_mlir_gen.py)

## 依赖

- AST 节点与解析入口：[`spec/dsl/ast.md`](../../spec/dsl/ast.md)
- AST 遍历访问器：[`spec/dsl/ast_visitor.md`](../../spec/dsl/ast_visitor.md)
- 节点发射规则：[`spec/dsl/emit_mlir.md`](../../spec/dsl/emit_mlir.md)
- arch dialect 结果类型与查询 op：[`spec/dialect/arch.md`](../../spec/dialect/arch.md)
- 符号值类型语义：[`spec/dialect/symbol.md`](../../spec/dialect/symbol.md)

## 目标

- 以统一入口生成 `func.func` op。
- 保证函数签名、参数顺序与返回类型与 AST 一致。
- 使用函数实际接收的运行时参数推导 `func.func` 输入签名。
- 为上层打印或封装提供稳定的 func op 结果。

## 限制与边界

- 不生成 `builtin.module`。
- 不负责 MLIR 文本打印或后端代码生成。
- 不定义节点级发射细节，节点发射规则由 `emit_mlir` 约束。
- 不做优化或自动修复非法 IR。
- `build_func_op` 的公开入口接收目标函数、运行时参数，以及仅用于补充源码解析环境的可选 `globals` / `builtins`；这些额外参数不得改变由 `runtime_args` 决定的函数输入签名，也不能代替必填的运行时参数。
- `build_func_op` 的公开契约仅覆盖可位置绑定的形参；`runtime_args` 必须按这些形参的顺序传入。
- 运行时参数必须按目标函数形参顺序传入；数量不一致、顺序不一致或类型无法映射时必须报错。
- 运行时参数的类型 lowering 必须基于“实际传入的参数对象”决定，而不是基于额外配置推断。
- `build_func_op_from_ast` 允许 `func_ast.inputs` 为空；若提供 `runtime_args`，其长度必须与 `func_ast.inputs` 一致；若输入包含未支持的 AST 类型、未支持的标量类型，或带输入函数既不属于纯 symbol 标量函数又缺少 tensor 输入时，必须报错。
- 当运行时参数为 `SymbolDim("s")` 这类 symbol 标量时，对应的 `func.func` 输入必须 lowering 为 `!symbol.int<"s">`；若为常量 symbol，例如 `SymbolDim(1)`，则必须 lowering 为 `!symbol.int<"1">`。
- 当运行时参数是 Python `int` 且函数场景属于 symbol 整型标量运算时，对应的 `func.func` 输入必须 lowering 为携带具体整数值的 `SymbolValueType`，不得退回 `i32`、`index` 或其他 builtin 标量类型；若整数值为负数，对外字符串表示必须直接表现为十进制负数字面量，例如 `symbol.int<-7>`。
- 当函数体仅包含 `for` 循环且没有 `return` 时，输出 `func.func` 允许零返回值。
- 当 `ForAST` 来源于 `LoopRange(start, end, step)` 且循环边界保持 symbol 整数语义时，lowering 后必须生成 `symbol.for`，不得退回 `scf.for`；其循环块参数 `it` 必须为 `!symbol.int<"expr">`。
- `LoopRange` 场景中的循环变量以及传入 `dma.slice` / `dma.deslice` 的 `offsets`、`sizes`、`strides` 等 DMA 标量 operand，必须直接保持 `!symbol.int<"expr">` 语义传递，不得额外生成 `arith.index_cast`。
- 对于纯 symbol 标量算术函数（仅符号标量入参/返回且返回为整型标量），函数签名中的输入与输出必须统一使用 `!symbol.int<"expr">`，不得降级为 `i32`、`index` 或其他 builtin 标量类型。
- 对于纯 symbol 标量比较函数（当前仅覆盖 `==`），函数签名中的输入必须保持 `!symbol.int<"expr">`，返回类型必须为 `i1`，不得退回 `!symbol.int<"expr">` 或其他 builtin 标量类型。
- memory 路径的比较表达式（`eq/ne/lt/le/gt/ge`）必须复用逐元素隐式 broadcast 规则，且 `lhs/rhs` 的 `element_type`/`space` 必须一致；当隐式 broadcast 失败或类型不一致时，`build_func_op(...)` 必须抛出 `AstVisitorError` 并保留位置（例如 `Implicit broadcast dimension mismatch`、`Binary op operands must have the same element_type`、`Binary op operands must have the same space`）。当函数体以 `return lhs != rhs` 承载 tensor 比较语义时，必须复用 `CompareExprAST(op=\"ne\")` lowering 链路生成 `nn.ne`，且结果 element type 为 `i1`。
- 当函数体以 `return lhs * rhs` 或 `return nn.mul(lhs, rhs)` 承载 tensor 乘法语义时，必须复用 `BinaryExprAST(op="mul")` lowering 链路生成 `nn.mul`；该链路允许 implicit broadcast，若 shape 不可 broadcast 必须报错 `Implicit broadcast dimension mismatch`。当两侧 `element_type` 不一致但 `space` 一致时，必须按二元算术 dtype promotion（`i32 < f16 < f32`）选择目标 element_type，并通过 `dma.cast` 将非目标侧对齐后再执行 `nn.mul`；若 `space` 不一致必须报错 `Binary op operands must have the same space`。
- Tensor 返回注解放宽仅适用于“二元算术 mixed dtype”场景：仅当 `return` 表达式是 tensor 二元算术且两操作数 `element_type` 不一致时，允许返回注解与最终 lowering 结果在 `element_type` 上暂不一致；且注解 `element_type` 必须是左右操作数 `element_type` 之一，否则必须报错 `Return type does not match annotation`。
- Tensor 注解既可使用普通字符串字面量 `"Tensor[...]"`，也可使用在源码层面可归一化为同等文本的 `f"Tensor[...]"`；归一化后的文本必须满足 Tensor 注解语法，若包含无法静态归一化的格式化片段或归一化后仍不符合语法，必须报错。
- 当函数体使用 `nn.sub` 且左右操作数 element_type 不一致时，必须插入 `dma.cast` 并按二元算术的 dtype promotion 结果生成 `nn.sub` 与 `func.return` 结果类型；当前公开覆盖仅限 `nn.sub` mixed dtype 场景。
- DSL 函数体内允许出现 `alloc`、`copy`、`cast`、`view`、`reshape`、`flatten`、`free`、`load`、`store`、`slice`、`deslice` 这组 DMA helper 调用；其公开语义由 `emit_mlir` 负责落实到具体 lowering。
- DSL 函数体内允许出现 `arch` helper 调用：`get_thread_num`（查询表达式）、`get_dynamic_memory`（返回 memory 表达式）与 `launch_kernel`（语句型启动描述）；其公开语义由 `emit_mlir` 负责落实到具体 lowering。
- 当函数体仅返回 `alloc(...)` 且没有 tensor 输入时，允许仅依赖标量 `runtime_args` 构建签名与结果类型；`alloc` 结果类型需由 `shape`/`stride`/`dtype`/`space` 与 `runtime_args` 共同决定，且显式 `stride` 必须与默认连续布局一致，否则必须报错。
- `flatten(x)` 在 DSL 公开契约中视为一维重排 helper，要求保留元素总数并输出一维 memory 结果；不要求存在独立的 dialect op。
- `free(x)` 在 DSL 公开契约中是语句型 helper，不产生新的 SSA 返回值，也不能作为函数返回值直接 lowering 为独立结果。
- 零入参 DSL 函数允许通过 `build_func_op` / `build_func_op_from_ast` 构建 `func.func`；当函数体返回 `get_block_id()` 查询结果时，lowering 必须生成 `arch.get_block_id`，并保持返回类型为 `!symbol.int<"block_id">`。
- 零入参 DSL 函数允许通过 `build_func_op` / `build_func_op_from_ast` 构建 `func.func`；当函数体返回 `get_block_num()` 查询结果时，lowering 必须生成 `arch.get_block_num`，并保持返回类型为 `!symbol.int<"block_num">`。
- 零入参 DSL 函数允许通过 `build_func_op` / `build_func_op_from_ast` 构建 `func.func`；当函数体返回 `get_subthread_id()` 查询结果时，lowering 必须生成 `arch.get_subthread_id`，并保持返回类型为 `!symbol.int<"subthread_id">`。
- 零入参 DSL 函数允许通过 `build_func_op` / `build_func_op_from_ast` 构建 `func.func`；当函数体返回 `get_subthread_num()` 查询结果时，lowering 必须生成 `arch.get_subthread_num`，并保持返回类型为 `!symbol.int<"subthread_num">`。
- 零入参 DSL 函数允许通过 `build_func_op` / `build_func_op_from_ast` 构建 `func.func`；当函数体返回 `get_thread_id()` 查询结果时，lowering 必须生成 `arch.get_thread_id`，并保持返回类型为 `!symbol.int<"thread_id">`。
- 零入参 DSL 函数允许通过 `build_func_op` / `build_func_op_from_ast` 构建 `func.func`；当函数体返回 `get_thread_num()` 查询结果时，lowering 必须生成 `arch.get_thread_num`，并保持返回类型为 `!symbol.int<"thread_num">`。
- 当函数体返回 `get_dynamic_memory(space)` 时，lowering 必须生成 `arch.get_dynamic_memory`，返回类型固定为 `!nn.memory<[?], [1], i8, #nn.space<space>>`；`space` 非片上空间（`SM/LM/TSM/TLM`）时必须报错。
- 当函数体包含 `launch_kernel(name, block, thread, subthread)` 语句时，lowering 必须生成无返回值 `arch.launch_kernel`；`name` 非空字符串约束与 extent 约束必须在链路中被校验：AST 入口要求 `block/thread/subthread` 为正整数或 `SymbolDim` 语义，emit 阶段进一步要求三者可归一化为正整数 `!symbol.int`，违规时必须报错。
- 当函数体包含 `tensor.get_shape()[axis]` 或 `tensor.get_stride()[axis]` 轴访问表达式时，必须复用 `TensorAxisAccessAST` 链路：`get_shape` 降级为 `symbol.get_dim`、`get_stride` 降级为 `symbol.get_stride`，并保持返回 `!symbol.int<"...">`；`tensor` 非 `nn.memory`、`axis` 非静态整数、负轴或越界必须报错。
- 如需 `builtin.module` 封装，由调用方完成。

## 公开接口

### `build_func_op(fn, *runtime_args, globals=None, builtins=None)`

功能说明：

- 解析 Python 函数并生成 `func.func` op。
- 内部依次调用 `parse_function(...)`、`AstVisitor` 与 `emit_mlir`。
- `func.func` 的输入签名由 `runtime_args` 的实际值语义决定。

参数说明：

- `fn` (`callable`)：受限 Python 函数。
- `runtime_args` (`tuple[object, ...]`)：目标函数实际传入的运行时参数，顺序必须与 `fn` 的形参顺序一致。
- `globals` (`dict[str, object] | None`)：可选的解析环境补充表，仅用于补充 `parse_function(...)` 所需的全局名称解析。
- `builtins` (`dict[str, object] | object | None`)：可选的内建名称补充表；若传入非 `dict` 对象，则按其 `__dict__` 参与解析环境构造。

使用示例：

```python
func_op = build_func_op(add, A, B)
```

```python
s = SymbolDim("s")
func_op = build_func_op(only_symbol, s)
```

注意事项：

- 解析失败或发射失败必须抛出可定位的错误。
- `globals` / `builtins` 只用于补充源码解析环境，不能改变函数签名推导行为，也不能替代 `runtime_args`。
- `build_func_op` 不接收 `config`；如需 `config`，应改用 `build_func_op_from_ast(...)`。
- `runtime_args` 的个数必须与函数形参数量一致。
- `build_func_op` 仅保证可位置绑定形参按位置顺序接收 `runtime_args`。
- 若 `fn` 没有可位置绑定形参，则允许以零个 `runtime_args` 调用，并由函数体内受支持的 DSL 表达式直接决定结果类型。
- 张量类运行时参数应按其对应 spec lowering 为项目内的 memory type。
- `SymbolDim("s")` 这类运行时参数必须 lowering 为 `!symbol.int<"s">`；`SymbolDim(1)` 这类常量 symbol 必须 lowering 为 `!symbol.int<"1">`。
- 当 `runtime_args` 为普通 Python `int` 且函数场景属于整型标量运算时，输入参数必须 lowering 为携带该整数值的 `SymbolValueType`，而不是 builtin 整数类型；负数实参的对外字符串表示必须保持 `symbol.int<-3>` 这类十进制负数字面量形式。
- 允许 `for` 循环内包含 `dma.slice`/`dma.deslice` 相关语义；当循环来自 `LoopRange` 且边界为 symbol 整数时，必须保留 `symbol.for` 结构，且迭代变量 `it` 不能退化为 `index`、`i32`、浮点或其他非 `SymbolValueType`。
- 当函数场景为纯 symbol 标量算术函数时，输入参数与返回值都必须 lowering 为 `!symbol.int<"expr">`。
- 当函数场景为纯 symbol 标量 `==` 比较且返回 `bool` 时，输入参数必须 lowering 为 `!symbol.int<"expr">`，函数体必须生成 `symbol.eq`，返回类型必须为 `i1`。
- 当函数场景为 tensor `!=` 比较时，返回注解必须与 `nn.ne` 结果类型一致（element type 为 `i1`，shape/space 按 broadcast 后结果确定）；若返回注解与实际 lowering 结果不一致必须报错。
- 当函数场景为纯 symbol 整型标量算术时，函数体中的 `+`、`-`、`*`、`/`、`//` 必须分别 lowering 为 `symbol.add`、`symbol.sub`、`symbol.mul`、`symbol.div`、`symbol.floordiv`，且结果类型保持为 `SymbolValueType`。
- 当函数体使用 `kernel_gen.operation.nn.add/sub/mul/truediv/floordiv` 包装同一组纯 symbol 整型标量算术时，lowering 结果必须与直接使用 Python 二元运算保持一致；`const/symbol` 与 `symbol/const` 的操作数顺序必须在结果表达式文本中原样保留。
- 当函数体包含 tensor `truediv` 且两侧 `dtype` 不一致时，必须按固定优先级决议目标 dtype，并在 lowering 中插入 `dma.cast`；`nn.truediv` 与 `func.return` 的结果类型必须与 promotion 结果一致。
- 当函数场景为 tensor 乘法时，返回注解默认必须与 `nn.mul` 实际结果一致（shape/space 按 broadcast 后结果确定）。仅在二元算术 mixed dtype 场景下允许 `element_type` 放宽，且注解 `element_type` 必须来自左右操作数之一；超出该边界必须报错 `Return type does not match annotation`。
- 纯 symbol 标量函数的参数/返回类型必须复用 `spec/dialect/symbol.md` 中定义的 `SymbolValueType`，不能退回 builtin 整数类型。
- `LoopRange` 场景中传给 `dma.slice` / `dma.deslice` 的标量 operand 必须直接复用 `!symbol.int<"expr">` value，不允许通过 `arith.index_cast` 做中间桥接。
- `"Tensor[...]"` 注解允许来自普通字符串字面量或可静态归一化的 `f"Tensor[...]"`；归一化后若不是合法 Tensor 注解，必须在解析阶段直接报错。
- 函数体内使用 DMA helper 调用时，`alloc/copy/cast/view/reshape/flatten` 必须作为有返回值表达式参与 lowering，`free` 必须作为无返回值语句参与 lowering，`load/store/slice/deslice` 继续遵循既有 memory 读写语义。
- `flatten(...)` 的 lowering 结果必须与一维 `reshape(...)` 的公开结果语义一致，即输出元素总数不变的一维 memory；不要求生成独立 `dma.flatten` op。
- 当零入参函数直接返回 `get_block_id()` 时，结果必须通过 `arch.get_block_id` 生成，并在 `func.func` 返回值中保持 `!symbol.int<"block_id">`。
- 当零入参函数直接返回 `get_block_num()` 时，结果必须通过 `arch.get_block_num` 生成，并在 `func.func` 返回值中保持 `!symbol.int<"block_num">`。
- 当零入参函数直接返回 `get_subthread_id()` 时，结果必须通过 `arch.get_subthread_id` 生成，并在 `func.func` 返回值中保持 `!symbol.int<"subthread_id">`。
- 当零入参函数直接返回 `get_subthread_num()` 时，结果必须通过 `arch.get_subthread_num` 生成，并在 `func.func` 返回值中保持 `!symbol.int<"subthread_num">`。
- 当零入参函数直接返回 `get_thread_id()` 时，结果必须通过 `arch.get_thread_id` 生成，并在 `func.func` 返回值中保持 `!symbol.int<"thread_id">`。
- 当零入参函数直接返回 `get_thread_num()` 时，结果必须通过 `arch.get_thread_num` 生成，并在 `func.func` 返回值中保持 `!symbol.int<"thread_num">`。
- 当函数体直接返回 `get_dynamic_memory(space)` 时，结果必须通过 `arch.get_dynamic_memory` 生成，并在 `func.func` 返回值中保持 `!nn.memory<[?], [1], i8, #nn.space<space>>`。
- 当函数体包含 `launch_kernel(name, block, thread, subthread)` 语句时，必须生成单个 `arch.launch_kernel` 且函数本身不引入额外返回值（除显式 `return` 以外）。
- 当函数体返回 `tensor.get_shape()[axis]` / `tensor.get_stride()[axis]` 时，`func.func` 的返回类型必须保持 `!symbol.int<"...">`，并分别通过 `symbol.get_dim` / `symbol.get_stride` 生成返回值。

返回与限制：

- 返回 `func.func` op。
- 不返回 module。

### `build_func_op_from_ast(func_ast, runtime_args=None, config=None)`

功能说明：

- 基于已构建的 `FunctionAST` 生成 `func.func` op。
- 不重复解析 Python 源码。
- `func.func` 的输入签名由 `runtime_args` 的实际值语义决定。

参数说明：

- `func_ast` (`FunctionAST`)：函数 AST。
- `runtime_args` (`tuple[object, ...] | list[object] | None`)：目标函数实际传入的运行时参数；若提供，则顺序必须与 `func_ast.inputs` 一致，并用于驱动 `func.func` 输入签名的 lowering。
- `config` (`dict[str, object] | None`)：可选的 visitor / lowering 配置，会透传给 `AstVisitor(config=...)` 与 `EmitContext(..., config=...)`，但不得改变 `runtime_args` 驱动签名的公开契约。

使用示例：

```python
func_ast = parse_function(add)
func_op = build_func_op_from_ast(func_ast, [A, B])
```

```python
func_ast = parse_function(loop_body)
func_op = build_func_op_from_ast(func_ast, runtime_args=[A], config={"loop_vars": {"i": "outer"}})
```

注意事项：

- 输入 AST 必须满足 `ast.md` 的结构约束。
- `runtime_args` 省略时，输入签名按 AST 注解 lowering；提供时，必须与 `func_ast.inputs` 一一对应，并以实际运行时参数语义驱动签名 lowering。
- `config` 只用于 visitor / lowering 配置透传，不得替代 `runtime_args`，也不得改变由 `runtime_args` 决定的输入签名。
- `func_ast.inputs` 可以为空；若提供 `runtime_args`，长度必须与 `func_ast.inputs` 一致。
- 若 AST 输入包含未支持的节点类型、未支持的标量类型，或函数既不属于纯 symbol 标量函数又缺少 tensor 输入，必须报错。
- 若 `runtime_args` 中存在 `SymbolDim("s")` 这类 symbol 标量，对应输入必须 lowering 为 `!symbol.int<"s">`。
- 若 AST 仅包含符号标量输入/输出，则生成的 `func.func` 签名必须保持 `!symbol.int<"expr">` 输入与返回，不得改写为 builtin 标量类型。
- 当 `func_ast` 没有输入且返回表达式为 `get_block_id()` 时，必须允许零参数签名，并生成返回 `!symbol.int<"block_id">` 的 `func.func`。
- 当 `func_ast` 没有输入且返回表达式为 `get_block_num()` 时，必须允许零参数签名，并生成返回 `!symbol.int<"block_num">` 的 `func.func`。
- 当 `func_ast` 没有输入且返回表达式为 `get_subthread_id()` 时，必须允许零参数签名，并生成返回 `!symbol.int<"subthread_id">` 的 `func.func`。
- 当 `func_ast` 没有输入且返回表达式为 `get_subthread_num()` 时，必须允许零参数签名，并生成返回 `!symbol.int<"subthread_num">` 的 `func.func`。
- 当 `func_ast` 没有输入且返回表达式为 `get_thread_id()` 时，必须允许零参数签名，并生成返回 `!symbol.int<"thread_id">` 的 `func.func`。
- 当 `func_ast` 没有输入且返回表达式为 `get_thread_num()` 时，必须允许零参数签名，并生成返回 `!symbol.int<"thread_num">` 的 `func.func`。

返回与限制：

- 返回 `func.func` op。

## 测试

- 测试文件：[`test/dsl/test_mlir_gen.py`](../../test/dsl/test_mlir_gen.py)
- 依赖测试文件：[`test/dsl/test_ast.py`](../../test/dsl/test_ast.py)、[`test/dsl/test_emit_mlir.py`](../../test/dsl/test_emit_mlir.py)
- 补充测试文件：[`test/dsl/test_ast_visitor.py`](../../test/dsl/test_ast_visitor.py)
- 执行命令（mlir_gen 集成）：`pytest -q test/dsl/test_mlir_gen.py`
- 执行命令（依赖子链路）：`pytest -q test/dsl/test_ast.py && pytest -q test/dsl/test_emit_mlir.py`
- 执行命令（ast_visitor 负路径）：`pytest -q test/dsl/test_ast_visitor.py`
- 拆分归属：MGEN-001~MGEN-035 归属 `test_mlir_gen.py`；其中 AST/emit 的前置语义分别由 `test_ast.py` 与 `test_emit_mlir.py` 单测保证；MGEN-036/037 与 arch helper 负路径补充由 `test_ast_visitor.py` 覆盖。
- 测试目标：
  - 验证 `build_func_op(...)` 生成 `func.func`。
  - 验证 `build_func_op(fn, *runtime_args, globals=None, builtins=None)` 的输入签名仅由运行时参数决定。
  - 验证 `build_func_op(...)` 仅支持按位置参数传入运行时参数；缺少运行时参数、数量不匹配或试图以 `globals/builtins` 替代时必须报错。
  - 验证 `build_func_op_from_ast(func_ast, runtime_args=None, config=None)` 的公开接口与实现签名一致，且 `runtime_args` / `config` 成功路径可由测试直接观察。
  - 验证 `build_func_op_from_ast(...)` 的输入校验错误路径，包括空输入、`runtime_args` 长度不匹配、未支持的标量类型、未支持的输入节点类型，以及非纯 symbol 标量函数缺少 tensor 输入时报错。
  - 验证 `globals/builtins` 只补充解析环境，不替代运行时参数；缺少运行时参数、运行时实参数量不匹配或误用 `globals/builtins` 时必须报错。
  - 验证非 `dict` 的 `builtins` 实参可作为解析环境输入成功构建 `func.func`。
  - 验证函数签名与返回值类型与 AST 一致。
  - 通过测试辅助封装验证 `func.func` 的结构输出（不改变本模块的边界）。
  - 覆盖无返回 `for` 循环与 `slice/deslice` 的生成能力，并要求 `LoopRange` lowering 为 `symbol.for`，且循环迭代变量 `it` 保持 `!symbol.int<"...">`。
  - 验证纯 symbol 函数场景会生成 `!symbol.int<"...">` 输入与 `!symbol.int<"...">` 返回。
  - 验证纯 symbol 标量算术在 lowering 后生成 `symbol.add/sub/mul/div/floordiv`，不退回 builtin 算术或其他 dialect op；直接 Python 二元运算与 `kernel_gen.operation.nn` 对应包装必须共享同一 lowering 结果。
  - 验证 tensor 二元算术在 `build_func_op(...)` / `build_func_op_from_ast(...)` 链路中复用 implicit broadcast 路径。
  - 验证 tensor `truediv` 链路在 mixed dtype promotion + `dma.cast` 对齐时的行为与诊断文案。
  - 验证整型标量函数场景中，`build_func_op(add, lhs, rhs)` 会把 Python `int` 实参 lowering 为携带具体整数值的 `SymbolValueType` 输入，并生成 `symbol.add` 结果。
  - 验证负数 Python `int` 实参不会导致 lowering 失败；负值的 `SymbolValueType.__str__` 必须保持 `symbol.int<-3>` 这类十进制负数字面量口径，且 `get_value()` 可还原原始负数值。
  - 验证 `LoopRange + slice/deslice` 场景生成 `symbol.for + dma.slice/dma.deslice`，且循环相关 lowering 不生成 `arith.index_cast`。
  - 验证 Tensor 注解可接受普通字符串字面量与可静态归一化的 `f"Tensor[...]"` 两种源码形式，并在归一化失败时报错。
  - 验证 tensor `!=` 比较在 `build_func_op(...)` / `build_func_op_from_ast(...)` 链路中复用 `CompareExprAST(op="ne")`，并在 memory 路径生成 `nn.ne`（必要时带 `nn.broadcast`）。
  - 验证 tensor `!=` 比较链路在 shape 不可 broadcast、返回注解不匹配或 element type 不一致时的错误路径。
  - 验证 DMA helper 调用在 `build_func_op(...)` 链路中被识别为受支持 DSL 公开能力：`alloc/copy/cast/view/reshape/flatten` 作为返回值表达式参与 lowering，`free` 作为无返回值语句参与 lowering，`load/store/slice/deslice` 维持 memory 读写语义。
  - 验证 alloc-only helper 场景在运行时参数、显式 stride 与非法 dtype/space 输入时的返回类型与错误路径。
  - 验证零入参 DSL 函数可通过 `build_func_op(...)` / `build_func_op_from_ast(...)` 生成 `func.func`，并在返回 `get_block_id()` 时 lowering 为 `arch.get_block_id` 与 `!symbol.int<"block_id">` 返回类型。
  - 验证零入参 DSL 函数可通过 `build_func_op(...)` / `build_func_op_from_ast(...)` 生成 `func.func`，并在返回 `get_block_num()` 时 lowering 为 `arch.get_block_num` 与 `!symbol.int<"block_num">` 返回类型。
  - 验证零入参 DSL 函数可通过 `build_func_op(...)` / `build_func_op_from_ast(...)` 生成 `func.func`，并在返回 `get_subthread_id()` 时 lowering 为 `arch.get_subthread_id` 与 `!symbol.int<"subthread_id">` 返回类型。
  - 验证零入参 DSL 函数可通过 `build_func_op(...)` / `build_func_op_from_ast(...)` 生成 `func.func`，并在返回 `get_subthread_num()` 时 lowering 为 `arch.get_subthread_num` 与 `!symbol.int<"subthread_num">` 返回类型。
  - 验证零入参 DSL 函数可通过 `build_func_op(...)` / `build_func_op_from_ast(...)` 生成 `func.func`，并在返回 `get_thread_id()` 时 lowering 为 `arch.get_thread_id` 与 `!symbol.int<"thread_id">` 返回类型。
  - 验证零入参 DSL 函数可通过 `build_func_op(...)` / `build_func_op_from_ast(...)` 生成 `func.func`，并在返回 `get_thread_num()` 时 lowering 为 `arch.get_thread_num` 与 `!symbol.int<"thread_num">` 返回类型。
  - 验证 `get_dynamic_memory(space)` 在 `build_func_op(...)` / `build_func_op_from_ast(...)` 链路中 lowering 为 `arch.get_dynamic_memory`，并固定返回 `!nn.memory<[?], [1], i8, #nn.space<space>>`。
  - 验证 `launch_kernel(name, block, thread, subthread)` 在 `build_func_op(...)` / `build_func_op_from_ast(...)` 链路中 lowering 为无返回值 `arch.launch_kernel`，并覆盖名称/extent 非法输入错误路径。
  - 验证 `get_shape/get_stride` 轴访问在 `build_func_op(...)` / `build_func_op_from_ast(...)` 链路中分别 lowering 为 `symbol.get_dim/symbol.get_stride`，并覆盖非 memory 来源、负轴、越界轴与非静态轴错误路径。
  - 验证纯 symbol 标量 `==` 比较会生成 `symbol.eq`，返回类型为 `i1`，并覆盖静态整数与动态符号两类 runtime args。
  - 验证纯 symbol 标量 `>=` 比较会生成 `symbol.ge`，返回类型为 `i1`，并覆盖静态整数与动态符号两类 runtime args。
- 功能与用例清单：
  - MGEN-001：`build_func_op(...)` 返回 `func.func`。（`test_build_func_op_returns_func_op`）
  - MGEN-001A：`build_func_op(...)` 的输入签名只由 `runtime_args` 决定；即使 `globals` 中存在同名对象且额外传入 `builtins`，成功路径的签名推导也不得被解析环境覆盖。（`test_build_func_op_signature_uses_runtime_args_not_parse_env`）
  - MGEN-001B：非 `dict` 的 `builtins` 可作为解析环境补充输入，且解析失败必须收敛为 `AstVisitorError`。（`test_mlir_gen_build_func_op_builtins_and_parse_error`）
  - MGEN-002：`build_func_op_from_ast(...)` 保留 AST 参数顺序；当传入 `runtime_args` 时，输入签名仍由运行时参数语义驱动。（`test_build_func_op_from_ast_preserves_arg_order`、`test_build_func_op_from_ast_uses_runtime_args_for_symbol_signature`）
  - MGEN-002A：`build_func_op_from_ast(..., config=...)` 接收并透传 visitor / lowering 配置。（`test_build_func_op_from_ast_forwards_config_to_visitor_and_context`）
  - MGEN-002B：`build_func_op_from_ast(...)` 的公开入口必须覆盖空输入、`runtime_args` 长度不匹配、未支持的标量类型、未支持的输入节点类型，以及非纯 symbol 标量函数缺少 tensor 输入等错误路径。（`test_mlir_gen_signature_validation_errors`）
  - MGEN-003：返回值类型与 AST 对齐。（`test_build_func_op_return_type_matches_annotation`）
  - MGEN-004：经测试辅助封装后 module 含 `func.func`/`nn` op。（`test_visit_to_nn_ir_builds_module`）
  - MGEN-005：经测试辅助打印文本包含 `func.func`/`nn`。（`test_emit_mlir_output`）
  - MGEN-006：标量参数 lowering 为 `func.func` 标量输入。（`test_scalar_arg_lowering_in_signature`）
  - MGEN-007：Tensor 返回注解不匹配时报错。（`test_invalid_tensor_return_annotation_reports_diagnostics`）
  - MGEN-008：常量返回 lowering 失败时报错。（`test_constant_lowering_reports_diagnostics`）
  - MGEN-009：返回类型不匹配时报错。（`test_return_type_mismatch_reports_diagnostics`）
  - MGEN-010：多语句 SSA 顺序与复用。（`test_multi_statement_ssa_order_and_reuse`）
  - MGEN-011：逐元素二元隐式 broadcast。（`test_tensor_binary_implicit_broadcast_lowering`）
  - MGEN-011A：tensor `truediv` mixed dtype promotion 必须插入 `dma.cast`，并保持 `nn.truediv` 与返回类型一致。（`test_tensor_truediv_dtype_promotion_lowering`）
  - MGEN-012：前置维度隐式 broadcast。（`test_tensor_binary_prepend_broadcast_lowering`）
  - MGEN-013：比较表达式隐式 broadcast。（`test_compare_implicit_broadcast_lowering`）
  - MGEN-014：不可 broadcast 报错与定位。（`test_tensor_binary_implicit_broadcast_mismatch_reports_diagnostics`）
  - MGEN-013A：tensor `!=` 比较必须走 `CompareExprAST(op="ne")` lowering，生成 `nn.ne` 并保持 memory 返回 element type 为 `i1`。（`test_build_func_op_lowers_nn_ne_with_tensor_i1_return_annotation`）
  - MGEN-015：`LoopRange + slice/deslice + 无 return` 场景生成 `symbol.for + dma.slice/dma.deslice`，且循环迭代变量 `it` 与 DMA operand 直接保持 `!symbol.int<"...">`，不生成 `arith.index_cast`。（`test_build_func_op_supports_symbolic_for_loop_dma_without_return`）
  - MGEN-016：纯 symbol 函数参数 lowering 为 `func.func` 的 `!symbol.int<"...">` 输入。（`test_symbol_scalar_function_uses_symbol_value_type_signature`）
  - MGEN-017：纯 symbol 函数返回 lowering 为 `func.func` 的 `!symbol.int<"...">` 输出。（`test_symbol_scalar_function_uses_symbol_value_type_signature`）
  - MGEN-018：纯 symbol 标量加法 lowering 为 `symbol.add`；直接 Python `+` 与 `nn.add(...)` 包装在 `const/const`、`symbol/symbol`、`const/symbol`、`symbol/const` 四类输入下必须保持一致；比较公开结果时以 `SymbolValueType.get_value()` 与对应 Python/SymbolDim 运行时结果一致为准。（`test_symbol_scalar_function_lowers_symbol_binary_ops`）
  - MGEN-021：纯 symbol 标量减法 lowering 为 `symbol.sub`；直接 Python `-` 与 `nn.sub(...)` 包装在四类输入下必须保持一致；比较公开结果时以 `SymbolValueType.get_value()` 与对应 Python/SymbolDim 运行时结果一致为准。（`test_symbol_scalar_function_lowers_symbol_binary_ops`）
  - MGEN-022：纯 symbol 标量乘法 lowering 为 `symbol.mul`；直接 Python `*` 与 `nn.mul(...)` 包装在四类输入下必须保持一致；比较公开结果时以 `SymbolValueType.get_value()` 与对应 Python/SymbolDim 运行时结果一致为准。（`test_symbol_scalar_function_lowers_symbol_binary_ops`）
  - MGEN-022C：返回注解放宽仅限二元算术 mixed dtype，且注解 `element_type` 必须是操作数 `element_type` 之一；不满足条件时必须报错 `Return type does not match annotation`。（`test_invalid_tensor_return_annotation_reports_diagnostics`）
  - MGEN-023：纯 symbol 标量除法 lowering 为 `symbol.div`；直接 Python `/` 与 `nn.truediv(...)` 包装在四类输入下必须保持一致；`const/const` 输入按静态整除结果收敛为常量整数；比较公开结果时以 `SymbolValueType.get_value()` 与对应 Python/SymbolDim 运行时结果一致为准。（`test_symbol_scalar_function_lowers_symbol_binary_ops`）
  - MGEN-024：纯 symbol 标量整除 lowering 为 `symbol.floordiv`；直接 Python `//` 与 `nn.floordiv(...)` 包装在四类输入下必须保持一致；`const/const` 输入按 Python `//` 语义收敛；比较公开结果时以 `SymbolValueType.get_value()` 与对应 Python/SymbolDim 运行时结果一致为准。（`test_symbol_scalar_function_lowers_symbol_binary_ops`）
  - MGEN-019：`build_func_op` 的运行时参数为必填，且公开契约仅覆盖 `fn + runtime_args` 的可位置绑定形参；省略实参、实参数量不匹配，或试图以 `globals/builtins` 替代时必须报错。（`test_build_func_op_requires_explicit_runtime_args`、`test_build_func_op_rejects_runtime_arg_count_mismatch`、`test_build_func_op_globals_and_builtins_cannot_replace_runtime_args`）
  - MGEN-020：`build_func_op(add, lhs, rhs)` 对普通 Python `int` runtime args 的 lowering 必须产出携带具体整数值的 `SymbolValueType` 输入；若实参包含负数，其对外字符串表示必须保持 `symbol.int<-3>` 这类十进制负数字面量口径，并在函数体内生成 `symbol.add` 结果。（`test_build_func_op_add_scalar_runtime_ints_lower_to_symbol_value_type`）
  - MGEN-025：Tensor 注解支持普通字符串字面量与可静态归一化的 `f"Tensor[...]"` 两种源码形式；若归一化结果不满足 Tensor 语法则必须报错。（`test_build_func_op_accepts_joinedstr_tensor_annotation`、`test_build_func_op_rejects_invalid_joinedstr_tensor_annotation`）
  - MGEN-026：DMA helper 调用在 `build_func_op(...)` 链路中按公开语义分流：`alloc/copy/cast/view/reshape/flatten` 生成对应 memory 结果，`free` 作为无返回值语句参与 lowering，`load/store/slice/deslice` 保持既有 memory 读写行为。（`test_build_func_op_supports_dma_helper_calls`、`test_build_func_op_supports_dma_free_statement`、`test_build_func_op_supports_dma_load_helper`、`test_build_func_op_supports_dma_store_helper`、`test_build_func_op_supports_dma_slice_helper`、`test_build_func_op_supports_dma_deslice_helper`）
  - MGEN-026A：alloc-only kernel 的 runtime shape 参数会 lowering 为 `!symbol.int` 输入，并保持 `dma.alloc` 结果类型与返回注解一致。（`test_build_func_op_supports_dma_alloc_helper_with_runtime_shape_args`）
  - MGEN-026B：alloc-only kernel 支持 `SymbolDim` 运行时参数与 `SymbolDim + const` 混合场景，`dma.alloc` 结果 `shape` 保持符号表达式。（`test_build_func_op_supports_dma_alloc_helper_with_symbol_shape_args`、`test_build_func_op_supports_dma_alloc_helper_with_symbol_plus_const_shape_args`）
  - MGEN-026C：alloc-only kernel 允许零参数常量形状，`func.func` 无输入且结果类型与 `alloc` 返回一致。（`test_build_func_op_supports_dma_alloc_helper_without_runtime_args`）
  - MGEN-026D：alloc-only kernel 支持显式连续 `stride` 输入并保持结果类型一致。（`test_build_func_op_supports_dma_alloc_helper_with_explicit_stride`）
  - MGEN-026E：alloc-only kernel 遇到非法 dtype / space 或非连续 stride 时必须报错。（`test_build_func_op_rejects_dma_alloc_helper_with_invalid_dtype`、`test_build_func_op_rejects_dma_alloc_helper_with_invalid_space`、`test_build_func_op_rejects_dma_alloc_helper_with_non_contiguous_stride`）
  - MGEN-027：零入参函数直接返回 `get_block_id()` 时，`build_func_op(...)` / `build_func_op_from_ast(...)` 必须生成零参数 `func.func`、单个 `arch.get_block_id`，并返回 `!symbol.int<"block_id">`。（`test_build_func_op_lowers_arch_get_block_id_query`）
  - MGEN-028：纯 symbol 标量 `==` 比较 lowering 为 `symbol.eq`，返回类型为 `i1`；`const/const` 与 `symbol/symbol` 两类输入下均应保持 `SymbolValueType` 输入签名，并覆盖 `return a == b` 与 `c = a == b; return c` 两种函数体形态。（`test_build_func_op_lowers_symbol_eq`）
  - MGEN-029：零入参函数直接返回 `get_block_num()` 时，`build_func_op(...)` / `build_func_op_from_ast(...)` 必须生成零参数 `func.func`、单个 `arch.get_block_num`，并返回 `!symbol.int<"block_num">`。（`test_build_func_op_lowers_arch_get_block_num_query`）
  - MGEN-030：纯 symbol 标量 `>=` 比较 lowering 为 `symbol.ge`，返回类型为 `i1`；`const/const` 与 `symbol/symbol` 两类输入下均应保持 `SymbolValueType` 输入签名，并覆盖 `return a >= b` 与 `c = a >= b; return c` 两种函数体形态。（`test_build_func_op_lowers_symbol_ge`）
  - MGEN-031：零入参函数直接返回 `get_subthread_id()` 时，`build_func_op(...)` / `build_func_op_from_ast(...)` 必须生成零参数 `func.func`、单个 `arch.get_subthread_id`，并返回 `!symbol.int<"subthread_id">`。（`test_build_func_op_lowers_arch_get_subthread_id_query`）
  - MGEN-032：零入参函数直接返回 `get_thread_id()` 时，`build_func_op(...)` / `build_func_op_from_ast(...)` 必须生成零参数 `func.func`、单个 `arch.get_thread_id`，并返回 `!symbol.int<"thread_id">`。（`test_build_func_op_lowers_arch_get_thread_id_query`）
  - MGEN-033：零入参函数直接返回 `get_subthread_num()` 时，`build_func_op(...)` / `build_func_op_from_ast(...)` 必须生成零参数 `func.func`、单个 `arch.get_subthread_num`，并返回 `!symbol.int<"subthread_num">`。（`test_build_func_op_lowers_arch_get_subthread_num_query`）
  - MGEN-034：`nn.sub` mixed dtype promotion 需插入 `dma.cast`，并保持 `nn.sub` 与 `func.return` 的结果类型为 promotion 结果。（`test_build_func_op_lowers_nn_sub_dtype_promotion_with_cast`）
  - MGEN-035：零入参函数直接返回 `get_thread_num()` 时，`build_func_op(...)` / `build_func_op_from_ast(...)` 必须生成零参数 `func.func`、单个 `arch.get_thread_num`，并返回 `!symbol.int<"thread_num">`。（`test_build_func_op_lowers_arch_get_thread_num_query`）
  - MGEN-036：返回 `get_dynamic_memory(space)` 的 DSL 函数必须 lowering 为 `arch.get_dynamic_memory`，并固定返回 `!nn.memory<[?], [1], i8, #nn.space<space>>`；非法 `space` 必须报错。（`test_build_func_op_rejects_invalid_arch_get_dynamic_memory_space`）
  - MGEN-037：包含 `launch_kernel(name, block, thread, subthread)` 语句的 DSL 函数必须 lowering 为单个无返回值 `arch.launch_kernel`；非法 `name`/extent（含非 `!symbol.int` 或静态 `<= 0`）必须报错。（`test_build_func_op_rejects_invalid_arch_launch_kernel_args`）
  - MGEN-038：函数体返回 `tensor.get_shape()[axis]` 时，`build_func_op(...)` / `build_func_op_from_ast(...)` 必须通过 `TensorAxisAccessAST(kind="shape")` 降级为 `symbol.get_dim` 并返回 `!symbol.int<"...">`；非 memory 来源、负轴、越界轴与非静态轴必须报错。（`expectation/dsl/mlir_gen/dialect/symbol/get_dim.py`）
  - MGEN-039：函数体返回 `tensor.get_stride()[axis]` 时，`build_func_op(...)` / `build_func_op_from_ast(...)` 必须通过 `TensorAxisAccessAST(kind="stride")` 降级为 `symbol.get_stride` 并返回 `!symbol.int<"...">`；非 memory 来源、负轴、越界轴与非静态轴必须报错。（`expectation/dsl/mlir_gen/dialect/symbol/get_stride.py`）
