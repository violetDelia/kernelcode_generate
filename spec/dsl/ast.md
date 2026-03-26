# ast.md

## 功能简介

- 定义 DSL AST 节点与字段语义。
- 提供解析入口，将 Python 函数解析为 AST 树。
- 不定义 MLIR 生成或文本输出。

## 文档信息

- 创建者：`规格小队`
- 最后一次更改：`李白`
- `spec`：[`spec/dsl/ast.md`](../../spec/dsl/ast.md)
- `功能实现`：[`kernel_gen/dsl/ast.py`](../../kernel_gen/dsl/ast.py)
- `test`：[`test/dsl/test_ast_visitor.py`](../../test/dsl/test_ast_visitor.py)

## 依赖

- Python `ast`/`inspect`：用于获取源码并解析语法树。

## 术语

- `FunctionAST`：函数级 AST 根节点。
- `Diagnostic`：带源码位置的诊断信息。
- `SourceLocation`：源码行列位置。

## 目标

- 提供稳定的 AST 节点定义。
- [immutable]提供 `parse_function(...)` 将 Python 函数解析为 AST。
- 为后续遍历与发射提供结构化输入。

## 限制与边界

- 只覆盖 AST 与解析入口，不负责 MLIR 生成与输出。
- 只支持受限语法子集，具体范围以测试清单为准。
- 不做优化、融合或后端相关行为。
- [immutable]只提供ast节点定义以及将函数翻译为ast树的能力。
- `for` 循环仅支持 `range(...)`、`LoopRange(...)` 或 `loop(...)` 的 1~3 参数形式，并解析为 `ForAST` 的 `start/end/step` 字段。
- `for` 循环体内不允许出现 `return`；出现即视为语法不支持并报错。
- 显式 `-> None` 返回注解表示函数无公开返回值；该场景允许函数体只包含语句且省略 `return`。
- DSL 解析入口当前仅将无参 `get_block_id()` / `get_block_num()` / `get_subthread_id()` / `get_subthread_num()` / `get_thread_id()` 识别为 `arch` 查询 builtin，并解析为专用 `ArchQueryAST` 节点。
- 比较表达式入口采用 Python 比较语法；`lhs != rhs` 必须解析为 `CompareExprAST(op="ne")`，以供下游 `nn.ne` lowering 复用同一 AST 语义。

## 公开接口

### `parse_function(fn)`

功能说明：

- 解析 Python 函数并构建 `FunctionAST`。
- 在解析阶段生成 `Diagnostic` 以承载错误定位信息。
- [immutable]不需要不必要的参数。

参数说明：

- `fn` (`callable`)：受限 Python 函数。

使用示例：

```python
def add(x: "Tensor[f32, 2, 2]", y: "Tensor[f32, 2, 2]"):
    return x + y

func_ast = parse_function(add)
```

注意事项：

- 必须能获取函数源码；否则应抛出解析错误。
- 注解解析规则以本文件与测试清单为准。
- 标量注解最小支持 `int`、`bool`、`float`；张量注解最小支持字符串形式 `Tensor[...]` 与 `JoinedStr` 形式 `f"Tensor[...]"`。
- 若参数未写注解，但在 `globals`/`builtins` 中存在同名 `SymbolDim` 或 `Memory` 对象，可按标量参数或张量参数推断。
- 若函数显式标注 `-> None`，则返回列表必须为空，且函数体可只包含语句并省略 `return`。
- `float(value)`、`tensor.get_shape()[axis]` 与 `tensor.get_stride()[axis]` 等最小 DSL 表达式必须可解析为明确 AST 节点。
- `slice(...)` helper 仅允许 3~5 个位置参数；超出范围必须返回 `Unsupported slice arity` 诊断。
- `slice` 的首参必须解析为 `TensorAST`；否则必须返回 `slice source must be TensorAST` 诊断。
- `slice` 的 `space` 可选，但一旦提供必须为 `MemorySpace`；否则必须返回 `slice space must be MemorySpace` 诊断。

返回与限制：

- 返回 `FunctionAST`。
- 解析失败时应抛出包含位置信息的错误或返回带 `Diagnostic` 的结果（以测试为准）。

### `SourceLocation`

功能说明：记录 AST 节点的源码位置信息。

参数说明：

- `line` (`int`)：行号。
- `column` (`int`)：列号。

使用示例：

```python
SourceLocation(line=1, column=0)
```

注意事项：仅用于诊断与定位，不参与语义计算。

返回与限制：返回不可变的数据结构实例。

### `Diagnostic`

功能说明：记录错误消息与对应源码位置。

参数说明：

- `message` (`str`)：诊断信息。
- `location` (`SourceLocation|None`)：可选源码位置。

使用示例：

```python
Diagnostic(message="Unsupported syntax", location=SourceLocation(3, 4))
```

注意事项：可与 `FunctionAST.diagnostics` 配合使用。

返回与限制：返回不可变的数据结构实例。

### `FunctionAST`

功能说明：表示 DSL 函数入口。

参数说明：

- `name` (`str`)：函数名。
- `inputs` (`list[TensorAST|ScalarArgAST]`)：输入参数。
- `outputs` (`list[TensorAST|ScalarArgAST]`)：输出参数。
- `body` (`BlockAST`)：函数体。
- `location` (`SourceLocation|None`)：可选源码位置。
- `source` (`str|None`)：可选源码文本。
- `py_ast` (`object|None`)：可选 Python AST。
- `diagnostics` (`list[Diagnostic]`)：诊断信息。

使用示例：

```python
FunctionAST(name="kernel", inputs=[], outputs=[], body=BlockAST([]))
```

注意事项：`diagnostics` 仅用于记录解析阶段问题。

返回与限制：返回不可变的数据结构实例。

### `FunctionAST.iter_inputs()`

功能说明：迭代 `inputs` 中的 `TensorAST` 与 `ScalarArgAST`。

参数说明：无。

使用示例：

```python
list(func_ast.iter_inputs())
```

注意事项：返回迭代器视图，不拷贝列表。

返回与限制：返回 `Iterable[TensorAST|ScalarArgAST]`。

### `BlockAST`

功能说明：有序语句块容器。

参数说明：

- `statements` (`list[object]`)：语句列表。
- `location` (`SourceLocation|None`)：可选源码位置。

使用示例：

```python
BlockAST(statements=[])
```

注意事项：`statements` 可包含表达式与语句节点。

返回与限制：返回不可变的数据结构实例。

### `TensorAST`

功能说明：函数签名中的张量参数。

参数说明：

- `name` (`str`)：参数名。
- `memory` (`object`)：张量元信息载体。
- `location` (`SourceLocation|None`)：可选源码位置。

使用示例：

```python
TensorAST(name="A", memory=memory)
```

注意事项：`memory` 的具体类型由上层语义决定。

返回与限制：返回不可变的数据结构实例。

### `ScalarArgAST`

功能说明：函数签名中的标量参数。

参数说明：

- `name` (`str`)：参数名。
- `value_type` (`type`)：标量类型，最小支持 `int`、`bool`、`float`。
- `location` (`SourceLocation|None`)：可选源码位置。

使用示例：

```python
ScalarArgAST(name="n", value_type=int)
```

注意事项：仅保存类型信息，不负责类型转换。

返回与限制：返回不可变的数据结构实例。

### `VarAST`

功能说明：变量节点。

参数说明：

- `name` (`str`)：变量名。
- `location` (`SourceLocation|None`)：可选源码位置。

使用示例：

```python
VarAST(name="i")
```

注意事项：绑定关系由解析器维护。

返回与限制：返回不可变的数据结构实例。

### `ForAST`

功能说明：`for` 循环结构。

参数说明：

- `var` (`VarAST`)：迭代变量。
- `start` (`object`)：起始表达式。
- `end` (`object`)：结束表达式。
- `step` (`object`)：步长表达式。
- `body` (`BlockAST`)：循环体。
- `location` (`SourceLocation|None`)：可选源码位置。

使用示例：

```python
ForAST(
    var=VarAST("i"),
    start=ConstAST(0),
    end=ConstAST(10),
    step=ConstAST(1),
    body=BlockAST([])
)
```

注意事项：

- 解析 `range/LoopRange/loop` 的 1~3 参数时，`start`/`step` 省略值分别默认 `0/1`。
- 循环语义由下游生成阶段解释。

返回与限制：返回不可变的数据结构实例。

### `StoreAST`

功能说明：向张量写入的语义节点。

参数说明：

- `tensor` (`TensorAST`)：目标张量。
- `offset` (`object`)：访问偏移。
- `stride` (`object|None`)：可选步长。
- `value` (`object`)：写入值。
- `location` (`SourceLocation|None`)：可选源码位置。

使用示例：

```python
StoreAST(tensor=tensor, offset=offset, stride=None, value=expr)
```

注意事项：`stride` 允许为空，具体语义由下游定义。

返回与限制：返回不可变的数据结构实例。

### `LoadAST`

功能说明：从张量读取的语义节点。

参数说明：

- `tensor` (`TensorAST`)：源张量。
- `offset` (`object`)：访问偏移。
- `stride` (`object|None`)：可选步长。
- `location` (`SourceLocation|None`)：可选源码位置。

使用示例：

```python
LoadAST(tensor=tensor, offset=offset, stride=None)
```

注意事项：`stride` 允许为空，具体语义由下游定义。

返回与限制：返回不可变的数据结构实例。

### `BinaryExprAST`

功能说明：二元算术表达式。

参数说明：

- `op` (`str`)：操作符（例如 `add/sub/mul/div/floordiv`）。
- `lhs` (`object`)：左操作数。
- `rhs` (`object`)：右操作数。
- `location` (`SourceLocation|None`)：可选源码位置。

使用示例：

```python
BinaryExprAST(op="add", lhs=a, rhs=b)
```

注意事项：操作符集合由解析器限制。

返回与限制：返回不可变的数据结构实例。

### `CompareExprAST`

功能说明：比较表达式。

参数说明：

- `op` (`str`)：操作符（例如 `eq/ne/lt/le/gt/ge`）。
- `lhs` (`object`)：左操作数。
- `rhs` (`object`)：右操作数。
- `location` (`SourceLocation|None`)：可选源码位置。

使用示例：

```python
CompareExprAST(op="lt", lhs=a, rhs=b)
```

注意事项：

- `op` 仅允许 `eq/ne/lt/le/gt/ge`，分别对应 `==`/`!=`/`<`/`<=`/`>`/`>=`。
- 比较语义与错误路径由下游 `emit_mlir` / `mlir_gen` 定义；不支持的比较操作符必须在下游抛出可定位错误。

返回与限制：返回不可变的数据结构实例。

### `ConstAST`

功能说明：常量表达式节点。

参数说明：

- `value` (`object`)：常量值。
- `location` (`SourceLocation|None`)：可选源码位置。

使用示例：

```python
ConstAST(value=1)
```

注意事项：常量类型由解析器决定。

返回与限制：返回不可变的数据结构实例。

### `ArchQueryAST`

功能说明：表示无参 `arch` builtin 查询节点。

参数说明：

- `query_name` (`str`)：查询名，当前仅允许 `get_block_id` / `get_block_num` / `get_subthread_id` / `get_subthread_num` / `get_thread_id`。
- `location` (`SourceLocation|None`)：可选源码位置。

使用示例：

```python
ArchQueryAST(query_name="get_block_id")
ArchQueryAST(query_name="get_block_num")
ArchQueryAST(query_name="get_subthread_id")
ArchQueryAST(query_name="get_subthread_num")
ArchQueryAST(query_name="get_thread_id")
```

注意事项：

- 该节点只表示 DSL 解析结果，不定义结果类型或 lowering 细节。
- 当前仅允许 `get_block_id` / `get_block_num` / `get_subthread_id` / `get_subthread_num` / `get_thread_id`；其他 `arch` 调用不属于本节点职责。

返回与限制：返回不可变的数据结构实例。

### `ModuleAST`

功能说明：模块级 AST 容器。

参数说明：

- `functions` (`list[FunctionAST]`)：函数列表。

使用示例：

```python
ModuleAST(functions=[FunctionAST(name="kernel", inputs=[], outputs=[], body=BlockAST([]))])
```

注意事项：`parse_function(...)` 的直接输出为 `FunctionAST`，`ModuleAST` 仅用于扩展场景。

返回与限制：返回不可变的数据结构实例。

## 测试

- 测试文件：[`test/dsl/test_ast_visitor.py`](../../test/dsl/test_ast_visitor.py)
- 执行命令：`pytest -q test/dsl/test_ast_visitor.py`
- 测试目标：
  - 覆盖 `parse_function(...)` 的源码解析与 AST 构建。
  - 覆盖 AST 节点字段与诊断信息的构造。
  - 覆盖 `lhs != rhs` 解析为 `CompareExprAST(op="ne")` 的入口语义，并确保该语义可被下游 `nn.ne` lowering 直接消费。
  - 覆盖 `get_block_id()` 解析为 `ArchQueryAST` 的最小 arch 查询入口。
  - 覆盖 `get_block_id()` 的非法参数在 AST 解析阶段被拒绝。
  - 覆盖 `get_block_num()` 解析为 `ArchQueryAST` 的最小 arch 查询入口。
  - 覆盖 `get_block_num()` 的非法参数在 AST 解析阶段被拒绝。
  - 覆盖 `get_thread_id()` 解析为 `ArchQueryAST` 的最小 arch 查询入口。
  - 覆盖 `get_thread_id()` 的非法参数在 AST 解析阶段被拒绝。
  - 覆盖 `slice` helper 的参数数量、source 类型与 space 约束的错误路径。
- 功能与用例清单：
  - AST-001：解析函数生成 `FunctionAST`。（`test_visit_function_builds_ast`）
  - AST-001A：提供独立解析入口。（`test_parse_function_entry`）
  - AST-001B：解析不依赖 `AstVisitor` 入口。（`test_parse_function_does_not_depend_on_ast_visitor_entry`）
  - AST-002：解析参数与返回注解，生成 `TensorAST`/`ScalarArgAST`。（`test_ast_parse_function_parses_annotations`）
  - AST-003：缺失注解时返回诊断或抛出错误。（`test_ast_parse_function_missing_annotation_reports_diagnostics`）
  - AST-004：解析全局/内建注解入口。（`test_globals_and_builtins_annotation_entry`）
  - AST-005：未知名称返回诊断。（`test_unknown_name_reports_diagnostics`）
  - AST-006：非法返回注解返回诊断。（`test_invalid_return_annotation_reports_diagnostics`）
  - AST-007：缺失 return 返回诊断。（`test_missing_return_reports_diagnostics`）
  - AST-008：缺少 Tensor 维度返回诊断。（`test_missing_tensor_dimensions_reports_diagnostics`）
  - AST-009：未注解 SymbolDim 参数可按标量参数解析。（`test_parse_function_infers_symboldim_arguments_without_annotations`）
  - AST-010：不支持语法返回诊断。（`test_unsupported_syntax_reports_diagnostics`）
  - AST-011：未注解的 float runtime 参数仍视为缺失注解并返回 `Missing annotation` 诊断。（`test_parse_function_rejects_float_runtime_arguments_without_annotations`）
  - AST-011A：`Tensor[i1, ...]` 返回注解可被解析为 `NumericType.Bool` 且保持 shape 不变。（`test_parse_function_supports_tensor_i1_return_annotation`）
  - AST-012：`nn` 算术 helper 的非法参数个数必须返回 `Unsupported nn arithmetic arity` 诊断。（`test_parse_function_rejects_unsupported_nn_arithmetic_arity_variants`）
  - AST-013：支持 `bool/float` 返回注解、`JoinedStr` 张量注解，以及 `float(...)`、`get_shape()[axis]`、`get_stride()[axis]` 等最小 symbol 查询/转换表达式解析。（`test_ast_parse_function_supports_symbol_scalar_and_joinedstr_annotations`）
  - AST-014：`slice` helper 的非法参数个数、非法 source 与非法 space 必须返回对应诊断。（`test_parse_function_rejects_invalid_slice_helper_variants`）
  - AST-014A：零入参函数中的 `get_block_id()` 可解析为 `ArchQueryAST`，并保留继续向下游 lowering 所需的查询名语义。（`test_build_func_op_lowers_arch_get_block_id_query`）
  - AST-014B：`get_block_id(1)` 与 `get_block_id(x=1)` 必须在 AST 解析阶段返回 `Unsupported get_block_id arity` 诊断。（`test_parse_function_rejects_invalid_get_block_id_arity_variants`）
  - AST-014C：零入参函数中的 `get_block_num()` 可解析为 `ArchQueryAST`，并保留继续向下游 lowering 所需的查询名语义。（`test_build_func_op_lowers_arch_get_block_num_query`）
  - AST-014D：`get_block_num(1)` 与 `get_block_num(x=1)` 必须在 AST 解析阶段返回 `Unsupported get_block_num arity` 诊断。（`test_parse_function_rejects_invalid_get_block_num_arity_variants`）
  - AST-014E：零入参函数中的 `get_subthread_id()` 可解析为 `ArchQueryAST`，并保留继续向下游 lowering 所需的查询名语义。（`test_build_func_op_lowers_arch_get_subthread_id_query`）
  - AST-014F：`get_subthread_id(1)` 与 `get_subthread_id(x=1)` 必须在 AST 解析阶段返回 `Unsupported get_subthread_id arity` 诊断。（`test_parse_function_rejects_invalid_get_subthread_id_arity_variants`）
  - AST-014I：零入参函数中的 `get_subthread_num()` 可解析为 `ArchQueryAST`，并保留继续向下游 lowering 所需的查询名语义。（`test_build_func_op_lowers_arch_get_subthread_num_query`）
  - AST-014J：`get_subthread_num(1)` 与 `get_subthread_num(x=1)` 必须在 AST 解析阶段返回 `Unsupported get_subthread_num arity` 诊断。（`test_parse_function_rejects_invalid_get_subthread_num_arity_variants`）
  - AST-014G：零入参函数中的 `get_thread_id()` 可解析为 `ArchQueryAST`，并保留继续向下游 lowering 所需的查询名语义。（`test_build_func_op_lowers_arch_get_thread_id_query`）
  - AST-014H：`get_thread_id(1)` 与 `get_thread_id(x=1)` 必须在 AST 解析阶段返回 `Unsupported get_thread_id arity` 诊断。（`test_parse_function_rejects_invalid_get_thread_id_arity_variants`）
  - AST-015：`lhs != rhs` 必须在 AST 中保持 `CompareExprAST(op="ne")` 语义，并与其他比较表达式共享后续 lowering 入口。（`test_build_func_op_lowers_nn_ne_with_tensor_i1_return_annotation`）
