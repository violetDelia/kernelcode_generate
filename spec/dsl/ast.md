# ast.md

## 功能简介

- 定义 DSL AST 节点与字段语义。
- 提供解析入口，将 Python 函数解析为 AST 树。
- 不定义 MLIR 生成或文本输出。
- 提供 facade 导入路径，保持 `kernel_gen.dsl.ast` 的外部用法不变。

## 文档信息

- 创建者：`规格小队`
- 最后一次更改：`jcc你莫辜负`
- `spec`：[`spec/dsl/ast.md`](../../spec/dsl/ast.md)
- `功能实现`：[`kernel_gen/dsl/ast/__init__.py`](../../kernel_gen/dsl/ast/__init__.py)
- `test`：[`test/dsl/ast/test_parser.py`](../../test/dsl/ast/test_parser.py)

## 依赖

- Python `ast`/`inspect`：用于获取源码并解析语法树。
- [`spec/symbol_variable/memory.md`](../../spec/symbol_variable/memory.md)：提供 `MemorySpace` 枚举语义，供 `get_dynamic_memory(...)` 与 `barrier(...)` helper 校验。
- [`spec/include/api/Arch.md`](../../spec/include/api/Arch.md)：提供 `BarrierScope` 枚举名与 launch/barrier 的公开源码合同。
- [`spec/dsl/ast_nodes.md`](../../spec/dsl/ast_nodes.md)：AST 节点定义合同。
- [`spec/dsl/ast_parser.md`](../../spec/dsl/ast_parser.md)：解析入口合同。

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
- `kernel_gen/dsl/ast/__init__.py` 仅承担 facade 与 re-export；节点定义与解析实现分别归属 `kernel_gen/dsl/ast/nodes.py` 与 `kernel_gen/dsl/ast/parser.py`，对外导入路径仍为 `kernel_gen.dsl.ast`。
- [immutable]只提供ast节点定义以及将函数翻译为ast树的能力。
- AST 节点仅表达前端语义，不携带 `target` 或 `hardware` 字段；`target` 为目标后端名称，`hardware` 为硬件参数表（字段范围见 [`spec/target/registry.md`](../../spec/target/registry.md)）。
- target/硬件相关信息仅允许在后续 lowering 或 emit 阶段通过上下文注入，AST 不解析也不回写这些字段。
- AST -> MLIR owner 边界固定如下：
  - `ModuleAST` / `FunctionAST` / `BlockAST` 只承担结构容器职责，由 `mlir_gen` builder / `AstVisitor` 组织，不直接定义单个 node-level lowering。
  - `TensorAST` / `ScalarArgAST` 是当前 builder / signature 已支持的签名输入，决定 `func.func` 输入或 block args；emit 阶段只消费它们对应的既有 SSA 绑定。
  - `PtrArgAST` 是 AST 层的指针签名节点，但当前 builder / signature 尚未支持；若进入 `mlir_gen` / `signature`，必须按实现现状报 `Unsupported input type`，不得在 spec 中误写为已支持的 block arg 输入。
  - `ConstAST` / `VarAST` / `ForAST` / `LoadAST` / `StoreAST` / `DmaAllocAST` / `DmaCopyAST` / `DmaCastAST` / `DmaViewAST` / `DmaReshapeAST` / `DmaFlattenAST` / `DmaFreeAST` / `NnBroadcastAST` / `NnBroadcastToAST` / `NnTransposeAST` / `NnUnaryAST` / `NnReduceAST` / `NnSoftmaxAST` / `Img2ColAST` / `MatmulAST` / `FCAST` / `ConvAST` / `BinaryExprAST` / `CompareExprAST` / `PythonCalleeCallAST` / `SymbolToFloatAST` / `TensorAxisAccessAST` / `ArchQueryAST` / `ArchGetDynamicMemoryAST` / `ArchBarrierAST` / `ArchLaunchKernelAST` 都属于 node-level emit 输入，具体 lowering 合同以 [`spec/dsl/emit_mlir.md`](../../spec/dsl/emit_mlir.md) 为准。
- `MemorySpace` 由 [`spec/symbol_variable/memory.md`](../../spec/symbol_variable/memory.md) 定义；AST 仅在 helper 参数校验中引用该枚举，不定义成员或语义。
- `ArchQueryAST` 归属 AST 层，仅覆盖无参 arch builtin 查询入口，结果类型与 target/hardware 的解析由下游层负责。
- `for` 循环仅支持 `range(...)`、`LoopRange(...)` 或 `loop(...)` 的 1~3 参数形式，并解析为 `ForAST` 的 `start/end/step` 字段。
- `for` 循环的 `step=0` 必须在解析阶段直接报错。
- `for` 循环体内不允许出现 `return`；出现即视为语法不支持并报错。
- 显式 `-> None` 返回注解表示函数无公开返回值；该场景允许函数体只包含语句且省略 `return`。
- AST 必须保留函数级返回语法元信息：`has_explicit_return`、`has_return_annotation`、`returns_none`。
- 无返回注解但有显式 `return expr` 时，`parse_function(...)` 必须解析成功；此时 `FunctionAST.outputs` 保持为空，但必须通过函数级元信息保留“显式 return 存在、未写返回注解、也不是 `-> None`”这一事实。
- DSL 解析入口必须覆盖 `arch` helper：无参 `get_block_id()` / `get_block_num()` / `get_subthread_id()` / `get_subthread_num()` / `get_thread_id()` / `get_thread_num()` 解析为 `ArchQueryAST`；`get_dynamic_memory(space)` 解析为 `ArchGetDynamicMemoryAST`；`barrier(visibility=[...], scope=BarrierScope.BLOCK)` 解析为 `ArchBarrierAST`；`launch_kernel[block, thread, subthread, shared_memory_size](callee, *args)` 解析为 `ArchLaunchKernelAST`。
- 当调用目标显式绑定到 `kernel_gen.operation.nn` 时，DSL 解析入口还必须覆盖 `img2col1d(...)`、`img2col2d(...)` 与 `matmul(...)` helper；其中 `matmul(lhs, rhs, memoryspace=...)` 解析为 `MatmulAST`。
- 比较表达式入口采用 Python 比较语法；`lhs != rhs` 必须解析为 `CompareExprAST(op="ne")`，以供下游 `nn.ne` lowering 复用同一 AST 语义。
- 二元乘法入口采用 Python `lhs * rhs` 与 `nn.mul(lhs, rhs)` 双入口；两者都必须解析为 `BinaryExprAST(op="mul")`，以复用后续统一 lowering 语义。
- 本轮仅为 `symbol.to_float` 链路开放 `-> float` 返回注解与 `float(symbol.int)` 的 AST 语法入口；不得顺手扩展 `double`、`complex` 或其他新注解体系。

## 公开接口

### `kernel_gen.dsl.ast` facade

功能说明：

- 对外导出 AST 节点类型与 `parse_function(...)`。
- 保持历史导入路径不变。

参数说明：无。

使用示例：

```python
from kernel_gen.dsl.ast import FunctionAST, parse_function
```

注意事项：

- 真实实现分别位于 `kernel_gen/dsl/ast/nodes.py` 与 `kernel_gen/dsl/ast/parser.py`，本模块只做导出。
- 导出的符号集合应覆盖下游使用的 AST 节点与解析入口。

返回与限制：

- 本模块不新增语义，只提供导出入口。

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
- `for` 循环的 `range/LoopRange/loop` 一旦出现 `step=0`，必须在解析阶段直接报错。
- 若函数显式标注 `-> None`，则返回列表必须为空，且函数体可只包含语句并省略 `return`。
- 若函数没有返回注解但存在显式 `return expr`，则 `FunctionAST.outputs` 必须保持为空，且：
  - `has_explicit_return == True`
  - `has_return_annotation == False`
  - `returns_none == False`
- `float(value)`、`tensor.get_shape()[axis]` 与 `tensor.get_stride()[axis]` 等最小 DSL 表达式必须可解析为明确 AST 节点。
- `nn.add/sub/mul/truediv/floordiv` helper 仅允许 2 个位置参数且禁止关键字参数；参数个数或形态不匹配时必须返回 `Unsupported nn arithmetic arity` 诊断。
- `slice(...)` helper 仅允许 3~5 个位置参数；超出范围必须返回 `Unsupported slice arity` 诊断。
- `matmul(...)` helper 仅允许 2 个位置参数，或 `2` 个位置参数加 `memoryspace=`；`memoryspace` 一旦提供必须为 `MemorySpace`，否则必须返回 `Unsupported matmul arity` 或 `matmul memoryspace must be MemorySpace` 诊断。
- `slice` 的首参必须解析为 `TensorAST`；否则必须返回 `slice source must be TensorAST` 诊断。
- `slice` 的 `space` 可选，但一旦提供必须为 `MemorySpace`；否则必须返回 `slice space must be MemorySpace` 诊断。
- `store(...)` / `deslice(...)` 的 target 既可以是函数输入 `TensorAST`，也可以是 `alloc/view/reshape/flatten/cast/copy/img2col/matmul/get_dynamic_memory` 这类会产生 memory 结果的 AST 表达式；对纯标量或其他非 memory 目标，解析阶段继续保持 `store target must be TensorAST` / `deslice target must be TensorAST` 诊断口径。
- `get_block_id/get_block_num/get_subthread_id/get_subthread_num/get_thread_id/get_thread_num` helper 仅允许 0 个参数且禁止关键字参数；不满足时必须返回 `Unsupported <helper> arity` 诊断。
- `get_dynamic_memory(...)` helper 仅允许 1 个位置参数且禁止关键字参数；参数必须是 `MemorySpace` 且仅允许片上空间（`SM/LM/TSM/TLM1/TLM2/TLM3`），否则必须返回 `Unsupported get_dynamic_memory arity`、`get_dynamic_memory space must be MemorySpace` 或 `get_dynamic_memory space must be on-chip MemorySpace` 诊断。
- `barrier(...)` helper 的稳定 DSL 入口固定为 `barrier(visibility=[...], scope=BarrierScope.BLOCK)`；必须使用且只使用 `visibility` / `scope` 两个关键字参数，不接受位置参数、缺参、重复关键字或未知关键字。`visibility` 必须是非空 `BarrierVisibility` 列表，`scope` 必须是 `BarrierScope`；否则必须返回 `Unsupported barrier arity`、`barrier visibility must be non-empty BarrierVisibility list` 或 `barrier scope must be BarrierScope` 诊断。
- `launch_kernel` helper 的公开 DSL 入口固定为 `launch_kernel[block, thread, subthread, shared_memory_size](callee, *args)`；四个 launch 字段必须放在下标里，调用参数只允许 `callee, *args` 这一路径，且禁止任何关键字参数。`callee` 必须是函数对象对应的 bare symbol reference（例如 `add_barrier_body`），不允许字符串字面量、属性引用、lambda、调用表达式或其他运行时对象；否则必须返回 `launch_kernel callee must be function symbol reference` 诊断。`block/thread/subthread/shared_memory_size` 仅做 AST 入口语法校验（必须是正整数或 `SymbolDim` 语义，其中 `shared_memory_size` 允许静态 `0`），否则必须返回 `Unsupported launch_kernel arity`、`launch_kernel <dim> must be int or SymbolDim`、`launch_kernel <dim> must be > 0` 或 `launch_kernel shared_memory_size must be >= 0` 诊断；AST 阶段不承诺 extent 已完成 `!symbol.int` 归一化。额外的 `*args` 只要求可解析为值表达式，并按源码顺序原样保留给下游 lowering。
- `-> float` 返回注解在本轮是合法 AST 入口，但仅用于 `symbol.to_float` 链路；除 `float(symbol.int)` 之外，不在 AST 层扩展新的浮点返回注解体系。
- `float(value)` 在 AST 层当前仅作为 `symbol.int -> float` 的最小语法入口冻结；本轮只承诺 `def cast_dim(n: int) -> float: return float(n)` 这一类写法可进入后续链路，不在 AST 层扩展 `double`、`complex`、多参数 `float(...)`、关键字参数 `float(...)` 或其他 builtin cast 体系。

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
- `inputs` (`list[TensorAST|ScalarArgAST|PtrArgAST]`)：输入参数。
- `outputs` (`list[TensorAST|ScalarArgAST]`)：输出参数。
- `body` (`BlockAST`)：函数体。
- `location` (`SourceLocation|None`)：可选源码位置。
- `source` (`str|None`)：可选源码文本。
- `py_ast` (`object|None`)：可选 Python AST。
- `diagnostics` (`list[Diagnostic]`)：诊断信息。
- `has_explicit_return` (`bool`)：是否存在显式 `return expr`。
- `has_return_annotation` (`bool`)：是否显式写了返回注解。
- `returns_none` (`bool`)：是否显式写了 `-> None`。

使用示例：

```python
FunctionAST(name="kernel", inputs=[], outputs=[], body=BlockAST([]))
```

注意事项：

- `diagnostics` 仅用于记录解析阶段问题。
- `inputs` 允许保留 `PtrArgAST` 这类 AST 层签名节点；但当前 builder / signature 只承诺支持 `TensorAST` / `ScalarArgAST`，`PtrArgAST` 流入 `mlir_gen` 时仍按实现现状报 `Unsupported input type`。
- `outputs` 只表示显式返回注解解析结果，不等价于“函数体是否显式返回值”。
- `returns_none=True` 仅表示函数显式写了 `-> None`；不能把“无返回注解”误判成 `returns_none=True`。

返回与限制：返回不可变的数据结构实例。

### `FunctionAST.iter_inputs()`

功能说明：迭代 `inputs` 中的 `TensorAST`、`ScalarArgAST` 与 `PtrArgAST`。

参数说明：无。

使用示例：

```python
list(func_ast.iter_inputs())
```

注意事项：返回迭代器视图，不拷贝列表。

返回与限制：返回 `Iterable[TensorAST|ScalarArgAST|PtrArgAST]`。

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

### `PtrArgAST`

功能说明：函数签名中的指针参数节点。

参数说明：

- `name` (`str`)：参数名。
- `dtype` (`object`)：pointee dtype。
- `location` (`SourceLocation|None`)：可选源码位置。

使用示例：

```python
PtrArgAST(name="data", dtype=f32)
```

注意事项：

- 该节点只承载 AST / parser 层的指针签名语义，不提供 shape/stride 信息。
- 当前 builder / signature 仍不支持把 `PtrArgAST` lowering 为 `func.func` 输入；若流入 `mlir_gen`，必须按实现现状报 `Unsupported input type`。

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
- 若 `step` 在解析阶段可判定为 `0`（例如 `range(0, 10, 0)`），解析直接报错，不生成 `ForAST`。
- 循环语义由下游生成阶段解释。

返回与限制：返回不可变的数据结构实例。

### `StoreAST`

功能说明：向张量写入的语义节点。

参数说明：

- `tensor` (`object`)：目标 memory AST，可为函数输入张量或 memory 结果表达式。
- `offset` (`object`)：访问偏移。
- `stride` (`object|None`)：可选步长。
- `value` (`object`)：写入值。
- `location` (`SourceLocation|None`)：可选源码位置。

使用示例：

```python
StoreAST(tensor=tensor, offset=offset, stride=None, value=expr)
```

注意事项：

- `stride` 允许为空，具体语义由下游定义。
- `tensor` 字段沿用历史命名，但公开语义已放宽为“可写 memory target”，不再局限于函数输入张量。

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

### `Img2ColAST`

功能说明：表示 `img2col1d/img2col2d` helper 调用的 AST 节点。

参数说明：

- `kind` (`str`)：helper 名，当前仅允许 `img2col1d` 或 `img2col2d`。
- `args` (`list[object]`)：位置参数 AST。
- `kwargs` (`dict[str, object]`)：关键字参数 AST。
- `location` (`SourceLocation|None`)：可选源码位置。

使用示例：

```python
Img2ColAST(kind="img2col2d", args=[tile], kwargs={"kh": ConstAST(3)})
```

注意事项：

- 该节点只保留 helper 语义，不在 AST 层提前决定 lowering 细节。

返回与限制：返回不可变的数据结构实例。

### `MatmulAST`

功能说明：表示 `matmul(lhs, rhs, memoryspace=...)` helper 调用的 AST 节点。

参数说明：

- `lhs` (`object`)：左操作数 AST。
- `rhs` (`object`)：右操作数 AST。
- `memoryspace` (`MemorySpace|None`)：可选结果 memoryspace。
- `location` (`SourceLocation|None`)：可选源码位置。

使用示例：

```python
MatmulAST(lhs=lhs, rhs=rhs, memoryspace=MemorySpace.GM)
```

注意事项：

- 该节点仅保留 helper 入口语义；dtype/shape/space 校验与 `nn.matmul` lowering 由下游处理。

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

- `space` (`MemorySpace`)：动态内存空间，公开语义仅允许 `SM/LM/TSM/TLM1/TLM2/TLM3`。
- `location` (`SourceLocation|None`)：可选源码位置。

使用示例：

```python
ArchGetDynamicMemoryAST(space=MemorySpace.SM)
```

注意事项：

- 该节点只表示 DSL 解析结果，不定义具体 lowering。
- `space` 必须是 `MemorySpace` 且属于片上空间；`global` 或其他非法输入必须在 AST 阶段报错。

返回与限制：返回不可变的数据结构实例。

### `ArchBarrierAST`

功能说明：表示 `barrier(visibility=[...], scope=BarrierScope.BLOCK)` 的 `arch` 同步语句节点。

参数说明：

- `visibility` (`list[BarrierVisibility]`)：需要保证可见性的聚合可见域列表。
- `scope` (`object`)：同步范围，公开语义要求是 `BarrierScope`。
- `location` (`SourceLocation|None`)：可选源码位置。

使用示例：

```python
ArchBarrierAST(
    visibility=[BarrierVisibility.TSM, BarrierVisibility.TLM],
    scope="BLOCK",
)
```

注意事项：

- 该节点属于语句型 helper，默认不产生独立返回值。
- AST 层必须保留 `visibility` 的源码顺序；不得在解析阶段偷偷重排、去重或补默认值。
- AST 层只冻结 `visibility / scope` 的结构化合同，不暴露 `BarrierScope` 的内部实现类型。

返回与限制：返回不可变的数据结构实例。

### `ArchLaunchKernelAST`

功能说明：表示 `launch_kernel[block, thread, subthread, shared_memory_size](callee, *args)` 的启动描述语句节点。

参数说明：

- `callee` (`str`)：由源级函数对象解析得到的 symbol reference 名称；禁止直接由字符串字面量构造。
- `block` (`object`)：block 规模，必须可解析为正整数或 `SymbolDim`。
- `thread` (`object`)：thread 规模，必须可解析为正整数或 `SymbolDim`。
- `subthread` (`object`)：subthread 规模，必须可解析为正整数或 `SymbolDim`。
- `shared_memory_size` (`object`)：共享内存规模，必须可解析为非负整数或 `SymbolDim`。
- `args` (`list[object]`)：按源码顺序转发给 launched body 的实参表达式。
- `location` (`SourceLocation|None`)：可选源码位置。

使用示例：

```python
ArchLaunchKernelAST(
    callee="add_barrier_body",
    block=ConstAST(1),
    thread=ConstAST(4),
    subthread=ConstAST(1),
    shared_memory_size=ConstAST(0),
    args=[TensorAST("lhs", ...), TensorAST("rhs", ...), TensorAST("out", ...)],
)
```

注意事项：

- 该节点属于语句型 helper，默认不产生独立返回值。
- `callee` 的公开语义是函数对象 / symbol ref；AST 只保留其稳定名称，不保留 Python 运行时 callable 对象本体。
- 启动规模参数类型与正值约束需在 AST 阶段给出可定位诊断。
- `args` 的长度可以为 `0`，但必须原样保留顺序；AST 阶段不校验 callee 形参数量是否匹配。

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
  - 覆盖 `kernel_gen.dsl.ast` 作为导入入口仍可导出 `FunctionAST` 与 `parse_function(...)`。
  - 覆盖 AST 节点字段与诊断信息的构造。
  - 覆盖 `lhs != rhs` 解析为 `CompareExprAST(op="ne")` 的入口语义，并确保该语义可被下游 `nn.ne` lowering 直接消费。
  - 覆盖 Python `lhs * rhs` 与 `nn.mul(lhs, rhs)` 共用 `BinaryExprAST(op="mul")` 入口语义，以及 `nn.mul` 非法参数个数诊断。
  - 覆盖 `img2col2d + reshape + matmul + deslice + return` 这类 conv2d 前端 helper 链可被解析为稳定 AST，并保留 `MatmulAST` 与 alloc target deslice 语义。
  - 覆盖 `get_block_id()` 解析为 `ArchQueryAST` 的最小 arch 查询入口。
  - 覆盖 `get_block_id()` 的非法参数在 AST 解析阶段被拒绝。
  - 覆盖 `get_block_num()` 解析为 `ArchQueryAST` 的最小 arch 查询入口。
  - 覆盖 `get_block_num()` 的非法参数在 AST 解析阶段被拒绝。
  - 覆盖 `get_thread_id()` 解析为 `ArchQueryAST` 的最小 arch 查询入口。
  - 覆盖 `get_thread_id()` 的非法参数在 AST 解析阶段被拒绝。
  - 覆盖 `get_thread_num()` 解析为 `ArchQueryAST` 的最小 arch 查询入口。
  - 覆盖 `get_thread_num()` 的非法参数在 AST 解析阶段被拒绝。
  - 覆盖 `get_dynamic_memory(space)` 的 AST 入口语义与 `MemorySpace` 约束错误路径。
  - 覆盖 `barrier(visibility=[...], scope=BarrierScope.BLOCK)` 的语句解析入口语义与 `visibility/scope` 错误路径。
  - 覆盖 `launch_kernel[block, thread, subthread, shared_memory_size](callee, *args)` 的语句解析入口语义与 arity/callee/extent/关键字参数错误路径。
  - 覆盖 `load` helper 的参数数量、source 类型与 space 约束的错误路径。
  - 覆盖 `slice` helper 的参数数量、source 类型与 space 约束的错误路径。
  - 覆盖 `-> float` 返回注解与 `float(symbol.int)` 的 AST 入口合同；当前下游验收标准建议使用 `test_ast_accepts_float_return_annotation_for_symbol_to_float` 与 `test_ast_rejects_non_float_annotation_for_symbol_to_float`，在专项测试落地前不将其写成已闭环映射。
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
  - AST-R1：无返回注解但有显式 `return` 的函数必须保留函数级返回语法元信息，且 `outputs` 保持为空。（`test_parse_function_preserves_explicit_return_without_return_annotation`）
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
  - AST-014O：`launch_kernel[block, thread, subthread, shared_memory_size](add_barrier_body, lhs, rhs, out)` 必须在 AST 解析阶段生成 `ArchLaunchKernelAST` 语句节点，并保留 `callee/extent/args` 顺序语义。（实现阶段补齐：`test_parse_function_parses_arch_launch_kernel_with_callee`）
  - AST-014P：`launch_kernel` 的参数个数、callee 形态、关键字参数或启动规模非法时，必须在 AST 解析阶段返回约定诊断；合法路径需保留到下游 `arch.launch` lowering。（实现阶段补齐：`test_parse_function_rejects_invalid_arch_launch_kernel_variants`）
  - AST-014Q：`barrier(visibility=[BarrierVisibility.TSM, BarrierVisibility.TLM], scope=BarrierScope.BLOCK)` 必须在 AST 解析阶段生成 `ArchBarrierAST` 语句节点，并保留 `visibility/scope` 源码顺序语义。（实现阶段补齐：`test_parse_function_parses_arch_barrier_statement`）
  - AST-014R：`barrier` 缺少 `scope`、传入空 `visibility`、非 `BarrierVisibility` 列表或非法 `scope` 时，必须在 AST 解析阶段返回约定诊断；合法路径需保留到下游 `arch.barrier` lowering。（实现阶段补齐：`test_parse_function_rejects_invalid_arch_barrier_variants`）
  - AST-015：`lhs != rhs` 必须在 AST 中保持 `CompareExprAST(op="ne")` 语义，并与其他比较表达式共享后续 lowering 入口。（`test_build_func_op_lowers_nn_ne_with_tensor_i1_return_annotation`）
  - AST-018：`nn.mul(lhs, rhs)` 与 `lhs * rhs` 必须共用 `BinaryExprAST(op="mul")` 入口；`nn.mul` 的 arity 负路径继续复用 `Unsupported nn arithmetic arity` 诊断口径。（`test_symbol_scalar_function_lowers_symbol_binary_ops`、`test_parse_function_rejects_unsupported_nn_arithmetic_arity_variants`）
  - AST-C1：`conv2d_img2col2d_tiled_npu_demo(...)` 这类 `loop + slice + img2col2d + reshape + matmul + deslice + return` 前端样例必须解析成功，innermost body 保留 `Img2ColAST`、`MatmulAST`，且 `deslice` target 允许绑定到前序 `alloc(...)` 结果 AST。（`test_build_func_op_supports_conv2d_img2col2d_tiled_npu_demo_frontend`）
  - E3 下游验收标准：`test_ast_accepts_float_return_annotation_for_symbol_to_float` 的输入应为 `def cast_dim(n: int) -> float: return float(n)`，预期 AST 解析通过；`test_ast_rejects_non_float_annotation_for_symbol_to_float` 的输入应为超出本轮范围的返回注解，预期固定报错。当前 `test/dsl/test_ast.py` 尚未落地这两个专项用例，因此此处仅冻结后续实现/测试链路应满足的验收口径，不将其写成已闭环映射。
