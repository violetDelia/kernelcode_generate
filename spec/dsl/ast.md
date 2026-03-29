# ast.md

## 功能简介

- 定义 DSL AST 节点与字段语义。
- 提供解析入口，将 Python 函数解析为 AST 树。
- 不定义 MLIR 生成或文本输出。

## 文档信息

- 创建者：`规格小队`
- 最后一次更改：`不要啊教练`
- `spec`：[`spec/dsl/ast.md`](../../spec/dsl/ast.md)
- `功能实现`：[`kernel_gen/dsl/ast.py`](../../kernel_gen/dsl/ast.py)
- `test`：[`test/dsl/test_ast.py`](../../test/dsl/test_ast.py)

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
- AST 节点仅表达前端语义，不携带 `target` 或 `hardware` 字段；`target` 为目标后端名称，`hardware` 为硬件参数表（字段范围见 [`spec/target/registry.md`](../../spec/target/registry.md)）。
- target/硬件相关信息仅允许在后续 lowering 或 emit 阶段通过上下文注入，AST 不解析也不回写这些字段。
- `MemorySpace` 由 [`spec/symbol_variable/memory.md`](../../spec/symbol_variable/memory.md) 定义；AST 仅在 helper 参数校验中引用该枚举，不定义成员或语义。
- `ArchQueryAST` 归属 AST 层，仅覆盖无参 arch builtin 查询入口，结果类型与 target/hardware 的解析由下游层负责。
- `for` 循环仅支持 `range(...)`、`LoopRange(...)` 或 `loop(...)` 的 1~3 参数形式，并解析为 `ForAST` 的 `start/end/step` 字段。
- `for` 循环体内不允许出现 `return`；出现即视为语法不支持并报错。
- 显式 `-> None` 返回注解表示函数无公开返回值；该场景允许函数体只包含语句且省略 `return`。
- DSL 解析入口必须覆盖 `arch` helper：无参 `get_block_id()` / `get_block_num()` / `get_subthread_id()` / `get_subthread_num()` / `get_thread_id()` / `get_thread_num()` 解析为 `ArchQueryAST`；`get_dynamic_memory(space)` 解析为 `ArchGetDynamicMemoryAST`；`launch_kernel(name, block, thread, subthread)` 解析为 `ArchLaunchKernelAST`。
- 比较表达式入口采用 Python 比较语法；`lhs != rhs` 必须解析为 `CompareExprAST(op="ne")`，以供下游 `nn.ne` lowering 复用同一 AST 语义。
- 二元乘法入口采用 Python `lhs * rhs` 与 `nn.mul(lhs, rhs)` 双入口；两者都必须解析为 `BinaryExprAST(op="mul")`，以复用后续统一 lowering 语义。

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
- `nn.add/sub/mul/truediv/floordiv` helper 仅允许 2 个位置参数且禁止关键字参数；参数个数或形态不匹配时必须返回 `Unsupported nn arithmetic arity` 诊断。
- `slice(...)` helper 仅允许 3~5 个位置参数；超出范围必须返回 `Unsupported slice arity` 诊断。
- `slice` 的首参必须解析为 `TensorAST`；否则必须返回 `slice source must be TensorAST` 诊断。
- `slice` 的 `space` 可选，但一旦提供必须为 `MemorySpace`；否则必须返回 `slice space must be MemorySpace` 诊断。
- `get_block_id/get_block_num/get_subthread_id/get_subthread_num/get_thread_id/get_thread_num` helper 仅允许 0 个参数且禁止关键字参数；不满足时必须返回 `Unsupported <helper> arity` 诊断。
- `get_dynamic_memory(...)` helper 仅允许 1 个位置参数且禁止关键字参数；参数必须是 `MemorySpace` 且仅允许片上空间（`SM/LM/TSM/TLM`），否则必须返回 `Unsupported get_dynamic_memory arity`、`get_dynamic_memory space must be MemorySpace` 或 `get_dynamic_memory space must be on-chip MemorySpace` 诊断。
- `launch_kernel(...)` helper 仅允许 4 个位置参数且禁止关键字参数；`name` 必须是非空字符串，`block/thread/subthread` 仅做 AST 入口语法校验（必须是正整数或 `SymbolDim` 语义），否则必须返回 `Unsupported launch_kernel arity`、`launch_kernel name must be non-empty str`、`launch_kernel <dim> must be int or SymbolDim` 或 `launch_kernel <dim> must be > 0` 诊断；AST 阶段不承诺 extent 已完成 `!symbol.int` 归一化。

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

- `query_name` (`str`)：查询名，当前仅允许 `get_block_id` / `get_block_num` / `get_subthread_id` / `get_subthread_num` / `get_thread_id` / `get_thread_num`。
- `location` (`SourceLocation|None`)：可选源码位置。

使用示例：

```python
ArchQueryAST(query_name="get_block_id")
ArchQueryAST(query_name="get_block_num")
ArchQueryAST(query_name="get_subthread_id")
ArchQueryAST(query_name="get_subthread_num")
ArchQueryAST(query_name="get_thread_id")
ArchQueryAST(query_name="get_thread_num")
```

注意事项：

- 该节点只表示 DSL 解析结果，不定义结果类型或 lowering 细节。
- 当前仅允许 `get_block_id` / `get_block_num` / `get_subthread_id` / `get_subthread_num` / `get_thread_id` / `get_thread_num`；`get_dynamic_memory` 与 `launch_kernel` 不属于本节点职责。

返回与限制：返回不可变的数据结构实例。

### `ArchGetDynamicMemoryAST`

功能说明：表示 `get_dynamic_memory(space)` 的 `arch` 动态内存入口调用节点。

参数说明：

- `space` (`MemorySpace`)：动态内存空间，公开语义仅允许 `SM/LM/TSM/TLM`。
- `location` (`SourceLocation|None`)：可选源码位置。

使用示例：

```python
ArchGetDynamicMemoryAST(space=MemorySpace.SM)
```

注意事项：

- 该节点只表示 DSL 解析结果，不定义具体 lowering。
- `space` 必须是 `MemorySpace` 且属于片上空间；`global` 或其他非法输入必须在 AST 阶段报错。

返回与限制：返回不可变的数据结构实例。

### `ArchLaunchKernelAST`

功能说明：表示 `launch_kernel(name, block, thread, subthread)` 的启动描述语句节点。

参数说明：

- `name` (`str`)：kernel 名称，必须为非空字符串。
- `block` (`object`)：block 规模，必须可解析为正整数或 `SymbolDim`。
- `thread` (`object`)：thread 规模，必须可解析为正整数或 `SymbolDim`。
- `subthread` (`object`)：subthread 规模，必须可解析为正整数或 `SymbolDim`。
- `location` (`SourceLocation|None`)：可选源码位置。

使用示例：

```python
ArchLaunchKernelAST(name="k", block=ConstAST(1), thread=ConstAST(128), subthread=ConstAST(4))
```

注意事项：

- 该节点属于语句型 helper，默认不产生独立返回值。
- 启动规模参数类型与正值约束需在 AST 阶段给出可定位诊断。

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

- 测试文件：[`test/dsl/test_ast.py`](../../test/dsl/test_ast.py)
- 集成测试文件：[`test/dsl/test_mlir_gen.py`](../../test/dsl/test_mlir_gen.py)
- 补充测试文件：[`test/dsl/test_ast_visitor.py`](../../test/dsl/test_ast_visitor.py)
- 执行命令（AST 单测）：`pytest -q test/dsl/test_ast.py`
- 执行命令（AST→MLIR 集成）：`pytest -q test/dsl/test_mlir_gen.py`
- 执行命令（ast_visitor 负路径）：`pytest -q test/dsl/test_ast_visitor.py`
- 拆分归属：AST 解析入口、注解解析、诊断负路径与 helper arity 校验归属 `test_ast.py`；依赖 `build_func_op(...)` 观察 AST 语义透传的链路回归归属 `test_mlir_gen.py`；ast_visitor 负路径与 arch helper 入口校验归属 `test_ast_visitor.py`。
- 测试目标：
  - 覆盖 `parse_function(...)` 的源码解析与 AST 构建。
  - 覆盖 AST 节点字段与诊断信息的构造。
  - 覆盖 `lhs != rhs` 解析为 `CompareExprAST(op="ne")` 的入口语义，并确保该语义可被下游 `nn.ne` lowering 直接消费。
  - 覆盖 Python `lhs * rhs` 与 `nn.mul(lhs, rhs)` 共用 `BinaryExprAST(op="mul")` 入口语义，以及 `nn.mul` 非法参数个数诊断。
  - 覆盖 `get_block_id()` 解析为 `ArchQueryAST` 的最小 arch 查询入口。
  - 覆盖 `get_block_id()` 的非法参数在 AST 解析阶段被拒绝。
  - 覆盖 `get_block_num()` 解析为 `ArchQueryAST` 的最小 arch 查询入口。
  - 覆盖 `get_block_num()` 的非法参数在 AST 解析阶段被拒绝。
  - 覆盖 `get_thread_id()` 解析为 `ArchQueryAST` 的最小 arch 查询入口。
  - 覆盖 `get_thread_id()` 的非法参数在 AST 解析阶段被拒绝。
  - 覆盖 `get_thread_num()` 解析为 `ArchQueryAST` 的最小 arch 查询入口。
  - 覆盖 `get_thread_num()` 的非法参数在 AST 解析阶段被拒绝。
  - 覆盖 `get_dynamic_memory(space)` 的 AST 入口语义与 `MemorySpace` 约束错误路径。
  - 覆盖 `launch_kernel(name, block, thread, subthread)` 的语句解析入口语义与 arity/name/extent 错误路径。
  - 覆盖 `load` helper 的参数数量、source 类型与 space 约束的错误路径。
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
  - AST-013：支持 `bool` 返回注解与可静态归一化的 `JoinedStr` 张量注解。（`test_ast_parse_function_supports_symbol_scalar_and_joinedstr_annotations`）
  - AST-013A：`load` helper 的非法参数个数、非法 source 与非法 space 必须返回对应诊断。（`test_parse_function_rejects_invalid_load_helper_variants`）
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
  - AST-014K：零入参函数中的 `get_thread_num()` 可解析为 `ArchQueryAST`，并保留继续向下游 lowering 所需的查询名语义。（`test_build_func_op_lowers_arch_get_thread_num_query`）
  - AST-014L：`get_thread_num(1)` 与 `get_thread_num(x=1)` 必须在 AST 解析阶段返回 `Unsupported get_thread_num arity` 诊断。（`test_parse_function_rejects_invalid_get_thread_num_arity_variants`）
  - AST-014M：`get_dynamic_memory(MemorySpace.SM)` 必须在 AST 解析阶段生成 `ArchGetDynamicMemoryAST` 并保留 `space` 语义。
  - AST-014N：`get_dynamic_memory` 的参数个数或 `space` 类型/取值非法时，必须在 AST 解析阶段返回约定诊断。（`test_parse_function_rejects_invalid_get_dynamic_memory_variants`）
  - AST-014O：`launch_kernel("k", block, thread, subthread)` 必须在 AST 解析阶段生成 `ArchLaunchKernelAST` 语句节点。
  - AST-014P：`launch_kernel` 的参数个数、名称或启动规模非法时，必须在 AST 解析阶段返回约定诊断；合法路径需保留到下游 `arch.launch_kernel` lowering。（`test_parse_function_rejects_invalid_launch_kernel_variants`）
  - AST-015：`lhs != rhs` 必须在 AST 中保持 `CompareExprAST(op="ne")` 语义，并与其他比较表达式共享后续 lowering 入口。（`test_build_func_op_lowers_nn_ne_with_tensor_i1_return_annotation`）
  - AST-018：`nn.mul(lhs, rhs)` 与 `lhs * rhs` 必须共用 `BinaryExprAST(op="mul")` 入口；`nn.mul` 的 arity 负路径继续复用 `Unsupported nn arithmetic arity` 诊断口径。（`test_symbol_scalar_function_lowers_symbol_binary_ops`、`test_parse_function_rejects_unsupported_nn_arithmetic_arity_variants`）
