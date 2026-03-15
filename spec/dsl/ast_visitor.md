# ast_visitor.md

用于定义 `ASTVisitor` 的设计规范。该组件负责把“带类型标注的 Python 函数”转换为项目内部可验证的 AST，并进一步生成 `nn dialect` IR 与 MLIR 风格 IR 文本。它是 DSL 前端的函数级入口。

## 文档信息

- 创建者：`榕`
- 最后一次更改：`榕`
- `spec`：[`spec/dsl/ast_visitor.md`](../../spec/dsl/ast_visitor.md)
- `关联 AST`：[`spec/dsl/ast.md`](../../spec/dsl/ast.md)
- `关联 IR`：[`spec/dsl/ir.md`](../../spec/dsl/ir.md)
- `关联 Lowering`：[`spec/dsl/lowering.md`](../../spec/dsl/lowering.md)
- `关联 Dialect`：[`spec/dialect/nn.md`](../../spec/dialect/nn.md)
- `关联总设计`：[`spec/dsl/memory_to_ir.md`](../../spec/dsl/memory_to_ir.md)
- `test`：[`test/dsl/test_ast_visitor.py`](../../test/dsl/test_ast_visitor.py)
- `功能实现`：[`python/dsl/ast_visitor.py`](../../python/dsl/ast_visitor.py)

## 背景

- 当前 DSL 已经有：
  - Python 函数式输入约束：[`spec/dsl/memory_to_ir.md`](../../spec/dsl/memory_to_ir.md)
  - 语义 AST 结构：[`spec/dsl/ast.md`](../../spec/dsl/ast.md)
  - IR 结构：[`spec/dsl/ir.md`](../../spec/dsl/ir.md)
  - AST -> IR lowering：[`spec/dsl/lowering.md`](../../spec/dsl/lowering.md)
- 但仍缺少一个明确的“函数源码 -> AST / nn dialect IR / MLIR 文本”前端组件规范。
- `ASTVisitor` 需要承担这个角色：接收 Python 函数，基于 Python `ast` 遍历函数体，构造项目 AST，并进一步产出 `nn dialect` IR 与对应的 MLIR 风格文本。

## 设计目标

- 支持从 Python 函数对象提取源码、签名、位置信息，并稳定转换为项目 AST。
- 支持在一次调用中完成：
  - `function -> FunctionAST`
  - `function -> nn dialect IR`
  - `function -> MLIR 风格 IR 文本`
- 保留源码位置信息，便于错误提示、审查与调试。
- 复用现有 AST / Lowering 规范，而不是额外定义一套并行表示。
- 借鉴 Triton 的“受限 Python 前端 + AST visitor + 明确错误”模式，以及 TorchInductor 的“逐节点 lowering / registry / 符号化处理”思路。

## 非目标

- 不负责文本 DSL 解析。
- 不在本阶段支持完整 Python 语法。
- 不支持任意闭包、类定义、生成器、异常处理、上下文管理器等复杂语言特性。
- 不在本阶段直接生成最终后端代码；本组件的终点是 `nn dialect` IR 及其 MLIR 风格文本表示。

## 设计参考

### Python `ast` / `inspect`

来自官方文档的关键约束：

- `inspect.getsource()` 可从函数对象提取源码；若源码不可获取，会抛 `OSError` 或 `TypeError`。
- `inspect.signature()` 可提取参数名、参数顺序与类型标注。
- `ast.NodeVisitor` 适合“遍历并返回值”；`visit()` 会分发到 `visit_<NodeType>()`，否则走 `generic_visit()`。
- 自定义 visitor 若不显式访问子节点，则这些子节点不会自动遍历。
- `ast.get_source_segment()` 可提取某个节点对应的原始源码片段，适合用于报错。

### Triton

从官方资料可提炼出以下前端设计点：

- `triton.jit` 面向 Python 函数入口，函数体只允许访问受控的 Python 原语、参数、Triton 内建和其他受支持函数。
- Triton 有独立的高层 MLIR 方言与类型系统，前端并不是直接发射 LLVM，而是先进入稳定方言 IR。
- Triton 编译链中存在清晰的“函数源码 -> AST visitor / code generator -> Triton IR”过程。

对本设计的启发：

- `ASTVisitor` 应采用“受限 Python 子集”策略。
- visitor 必须具备严格的名称解析、类型检查和错误定位能力。
- 前端应先进入稳定 AST / IR，而不是一开始就绑定后端细节。

### TorchInductor

从官方资料可提炼出以下设计点：

- TorchInductor 先获得上游图，再对图做逐节点 lowering。
- lowering 是“逐 operator 的规则化转换”，支持符号维度、符号索引与分层 IR。
- 分析、lowering、codegen 三个阶段应分离，避免把所有逻辑耦合在一个 visitor 里。

对本设计的启发：

- `ASTVisitor` 应只解决“函数到 AST / nn dialect IR / MLIR 文本”的前端问题，不把优化、调度、代码生成混进来。
- 对 `load/store/add/...` 等节点，宜采用注册式 lowering / builder 机制，而不是在一个大分支里硬编码全部规则。
- 对符号 shape / stride / index，应优先保留符号表达，而不是过早求值。

## 组件定位

建议把 `ASTVisitor` 定位为 DSL 前端组件，位于：

- 上游：Python 函数对象
- 中间：项目 AST
- 下游：`nn dialect` IR / MLIR 风格文本

职责边界：

- 负责源码获取、Python AST 解析、语义节点构造、名称解析、类型绑定、位置跟踪。
- 负责调用已存在的 lowering / dialect builder 逻辑，把 `FunctionAST` 转为 `nn dialect` IR。
- 负责把 `nn dialect` IR 打印为 MLIR 风格文本，便于调试、测试与后续工具对接。
- 不负责调度、融合、自动优化、最终代码生成。

## 输入与输出

### 输入

- Python 函数对象
- 可选的全局符号表
- 可选的 DSL 内建函数注册表
- 可选的 visitor 配置项

### 输出

- `visit_function(fn)` -> `FunctionAST`
- `visit_to_nn_ir(fn)` -> `builtin.module` / `func.func` 风格的 `nn dialect` IR
- `visit_to_ir(fn)` -> `nn dialect` IR
- `emit_mlir(fn)` 或 `emit_mlir(module)` -> MLIR 风格文本
- 可选中间结果：
  - Python `ast.FunctionDef`
  - 源码位置信息表
  - visitor 诊断信息

## 总体流程

建议流程如下：

1. 通过 `inspect.getsource()` 和 `inspect.signature()` 获取函数源码与签名。
2. 对源码做缩进规范化，再调用 `ast.parse()` 获取 Python AST。
3. 定位顶层 `FunctionDef`。
4. 建立 visitor 上下文：
   - 全局符号表
   - 局部符号表
   - 参数表
   - 类型环境
   - 源码位置信息
5. 使用 `ASTVisitor(ast.NodeVisitor)` 遍历 Python AST，构造 `FunctionAST`。
6. 对构造出的 `FunctionAST` 执行 AST 级校验。
7. 调用既有 lowering / dialect builder 逻辑，生成 `nn dialect` IR。
8. 将 `nn dialect` IR 打印为 MLIR 风格文本。

## 核心接口

### `load_function_source(fn)`

功能说明：

- 从函数对象提取源码、文件路径、起始行号、签名和注解信息。

建议返回：

- `source`
- `file_path`
- `start_lineno`
- `signature`
- `annotations`

示例：

```python
def kernel(A: SymbolMemory, B: int):
    return load(A, B, A.get_stride())
```

返回结果至少应包含：

- `source="def kernel(...): ..."`
- `signature=(A: SymbolMemory, B: int)`
- `file_path`
- `start_lineno`

### `parse_function_ast(source)`

功能说明：

- 把函数源码解析为 Python `ast.Module` / `ast.FunctionDef`。

建议行为：

- 若源码中包含多个顶层定义，只接受目标函数对应的 `FunctionDef`。
- 若源码无法解析，抛 `SyntaxError` 或包装后的 `ValueError`。

### `visit_function(fn)`

功能说明：

- 主入口：函数对象 -> `FunctionAST`。

建议流程：

- `load_function_source`
- `parse_function_ast`
- `visit_Module`
- `visit_FunctionDef`

### `visit_to_nn_ir(fn)`

功能说明：

- 组合入口：函数对象 -> `nn dialect` IR。

建议流程：

- `function -> FunctionAST`
- `validate_ast`
- `build_nn_dialect`

建议返回：

- `builtin.module`
- 内含 `func.func`
- 函数体中使用 `nn.add` / `nn.sub` / `nn.mul` / `nn.truediv` / `nn.eq` / `nn.ne` / `nn.lt` / `nn.le` / `nn.gt` / `nn.ge`

### `visit_to_ir(fn)`

功能说明：

- 兼容入口，语义等同于 `visit_to_nn_ir(fn)`。

### `emit_mlir(fn)` / `emit_mlir(module)`

功能说明：

- 把 `nn dialect` IR 打印为 MLIR 风格文本。

建议流程：

- `function -> nn dialect module`
- `module -> printer`
- 返回 MLIR 风格字符串

## Visitor 上下文设计

### `VisitorContext`

建议至少包含以下字段：

- `source`
- `file_path`
- `start_lineno`
- `globals`
- `locals`
- `arguments`
- `symbol_table`
- `type_env`
- `diagnostics`
- `current_function`
- `loop_stack`

### 设计原则

- visitor 过程中不使用隐式全局状态。
- 函数参数、局部变量、循环变量必须进入显式符号表。
- 源码位置信息必须跟随节点流转，便于报错。

## 支持的 Python AST 节点

第一阶段建议支持以下节点。

| Python AST 节点 | 作用 | ASTVisitor 产物 |
| --- | --- | --- |
| `Module` | 模块入口 | `ModuleAST` 或单函数入口 |
| `FunctionDef` | 顶层函数 | `FunctionAST` |
| `arguments` / `arg` | 参数 | `TensorAST` / `ScalarArgAST` |
| `Assign` | 局部绑定 | 局部符号表写入 |
| `Return` | 返回语句 | 输出表达式 / return 节点 |
| `Expr` | 独立表达式语句 | statement 节点 |
| `For` | 循环 | `ForAST` |
| `Call` | DSL 内建调用 | `LoadAST` / `StoreAST` / 内建表达式 |
| `Name` | 变量引用 | `VarAST` / 参数引用 |
| `Constant` | 常量 | `ConstAST` |
| `BinOp` | 算术表达式 | `BinaryExprAST` |
| `Compare` | 比较表达式 | `CompareExprAST` |
| `Attribute` | 受控属性 / 方法调用 | 例如 `A.get_stride()` |

## 节点访问规则

### `visit_Module`

功能说明：

- 校验模块中是否存在且只存在一个目标 `FunctionDef`。

约束：

- 不支持一个入口里同时传入多个可编译函数。
- 其他非目标顶层节点默认拒绝，除非是文档字符串。

### `visit_FunctionDef`

功能说明：

- 解析函数名、参数、返回值、函数体。

约束：

- 函数名不能为空。
- 参数类型必须可映射到 DSL 输入类型。
- 当前阶段优先支持：
  - `SymbolMemory`
  - `int`
  - 后续扩展的受支持标量类型

示例：

```python
def kernel(A: SymbolMemory, B: int):
    x = load(A, B, A.get_stride())
    return x
```

至少应构造：

- `FunctionAST("kernel", ...)`
- `TensorAST("A", ...)`
- `ScalarArgAST("B", int)`

### `visit_Assign`

功能说明：

- 处理局部变量绑定。

约束：

- 第一阶段只支持单目标赋值。
- 不支持解构赋值。
- 赋值右值必须能被访问器转换为表达式节点。

示例：

```python
x = load(A, i, A.get_stride())
```

语义：

- `x` 进入局部符号表
- 其值绑定到对应表达式节点

### `visit_Return`

功能说明：

- 处理函数返回值。

约束：

- 第一阶段只支持单返回值。
- 不支持返回多个值的 tuple。
- 返回值必须是表达式节点或已绑定局部名。

### `visit_For`

功能说明：

- 处理循环。

建议支持形式：

```python
for i in range_for(0, N, 1):
    ...
```

或等价受控形式。

约束：

- 第一阶段只支持简单单层 `for` 结构。
- `iter` 必须是受支持的 DSL 循环构造。
- `target` 必须是单一循环变量。

### `visit_Call`

功能说明：

- 处理 DSL 内建调用和受控方法调用。

建议支持：

- `load(tensor, offset, stride=None)`
- `store(tensor, offset, value, stride=None)`
- `add/sub/mul/truediv`
- `eq/ne/lt/le/gt/ge`
- `range_for(start, end, step=1)`
- `tensor.get_stride()`

设计建议：

- 使用“调用注册表”维护 target -> lowering handler 的映射。
- 对每个 handler，输入是 Python AST call node 与 visitor 上下文，输出是项目 AST 节点、或后续可映射为 `nn dialect` op 的语义对象。

### `visit_Name`

功能说明：

- 处理变量查找。

查找顺序建议：

1. 局部符号表
2. 参数表
3. 受支持的全局常量 / DSL 内建

约束：

- 未定义名称必须抛 `NameError`。
- 不允许访问任意工作目录外项目中的全局实现对象。

### `visit_Constant`

功能说明：

- 处理常量。

建议支持：

- `int`
- `float`
- `bool`
- `None` 仅在有明确语义时支持

约束：

- `str` 只允许出现在少量受控元信息位置；若作为计算值，应拒绝。

### `visit_BinOp`

功能说明：

- 处理 `+ - * /`。

输出：

- `BinaryExprAST`

约束：

- 运算语义必须与 [`spec/operation/nn.md`](../../spec/operation/nn.md) 或已选定的 operation spec 保持一致。
- 若参与运算的是张量语义对象，则 shape / dtype 规则必须前置校验。

### `visit_Compare`

功能说明：

- 处理 `== != < <= > >=`。

输出：

- `CompareExprAST`

约束：

- 比较结果仍是张量语义比较，不是 Python 单个 `bool`。

## 名称解析与作用域规则

- 函数参数进入函数级作用域。
- 赋值语句创建局部绑定。
- 循环变量进入循环体局部作用域。
- 内部名称覆盖必须可追踪。
- 未定义名称立即报错，不做静默回退。

## 类型绑定规则

### 参数绑定

- `SymbolMemory` -> `TensorAST`
- `int` -> `ScalarArgAST`
- 其他未注册类型 -> `TypeError`

### 表达式绑定

- `load(...)` 返回张量元素表达式或等价值节点
- `add/sub/...` 返回算术表达式节点
- `eq/ne/...` 返回比较表达式节点

### 类型合法性

- 所有与 `Memory` 相关的运算，都必须遵循 [`spec/operation/nn.md`](../../spec/operation/nn.md) 中的 shape / dtype / scalar 兼容性规则
- 类型检查失败必须在 visitor 或 AST 校验阶段暴露，不应拖到后端代码生成阶段

## 源码位置信息

建议为每个 AST 节点保留：

- `file_path`
- `lineno`
- `col_offset`
- `end_lineno`
- `end_col_offset`
- `source_segment`

设计建议：

- 使用 `ast.get_source_segment()` 记录错误片段
- visitor 构造 AST 节点时同步附带位置元信息

作用：

- 提供更准确的错误定位
- 支持未来的源码映射、调试和可视化

## 错误模型

建议错误类型：

- `TypeError`
  - 参数类型不支持
  - 常量类型不支持
  - 运算类型不兼容
- `NameError`
  - 名称未定义
- `ValueError`
  - 结构不合法
  - 不支持的循环形式
  - 非法调用参数
- `SyntaxError`
  - 源码解析失败
- `NotImplementedError`
  - 命中了当前 visitor 尚未支持的 Python 语法节点

建议错误输出至少包含：

- 函数名
- 文件路径
- 行列号
- 节点源码片段
- 错误摘要

## 与现有 AST / Lowering 的关系

- `ASTVisitor` 不重新定义项目 AST。
- visitor 产出的语义节点必须直接兼容 [`spec/dsl/ast.md`](../../spec/dsl/ast.md)。
- `visit_to_nn_ir()` 必须优先输出 [`spec/dialect/nn.md`](../../spec/dialect/nn.md) 约束下的 `nn dialect` IR。
- `emit_mlir()` 的文本输出必须是该 `nn dialect` IR 的 MLIR 风格打印结果。
- 若内部仍保留通用项目 IR 作为过渡层，该层只能作为内部中间结果，不能替代 visitor 的最终公开产物。

## 与 Triton / TorchInductor 的关系

### 借鉴 Triton 的部分

- 受限 Python 子集
- visitor 分派风格
- 清晰的前端错误
- 源码到高层方言 IR 的稳定映射
- 方言 IR 可打印为 MLIR 风格文本

### 借鉴 TorchInductor 的部分

- 逐节点 lowering / registry 设计
- 符号索引与符号 shape 处理
- 分析、visitor、lowering、codegen 分层
- 先生成稳定 IR，再导出到具体文本或后端形式

### 不直接照搬的部分

- 本项目不直接复用 Triton 的 `tt` dialect
- 本项目不直接采用 TorchInductor 的 define-by-run IR
- 本项目仍以自己的 AST / IR / dialect 规范为主

## 示例

### 示例 1：简单 load + return

输入：

```python
def kernel(A: SymbolMemory, i: int):
    x = load(A, i, A.get_stride())
    return x
```

visitor 结果至少应包含：

- `FunctionAST(name="kernel")`
- `TensorAST(name="A")`
- `ScalarArgAST(name="i", value_type=int)`
- `LoadAST(tensor=A, offset=i, stride=A.get_stride())`

若调用 `visit_to_nn_ir()`，结果至少应包含：

- 一个 `builtin.module`
- 一个 `func.func @kernel`
- 与输入 `Memory` 对应的参数或 buffer 表达
- 与 `load` 语义对应的 `nn dialect` / 兼容基础方言节点

若调用 `emit_mlir()`，结果至少应输出一段 MLIR 风格文本，例如：

```mlir
builtin.module {
  func.func @kernel(%A: !nn.memory<shape=[M], stride=[1], element_type=f32, space=global>, %i: index) -> !nn.memory<shape=[1], stride=[1], element_type=f32, space=global> {
    ...
  }
}
```

### 示例 2：pointwise add

输入：

```python
def kernel(A: SymbolMemory, B: SymbolMemory, i: int):
    x = load(A, i, A.get_stride())
    y = load(B, i, B.get_stride())
    z = add(x, y)
    return z
```

visitor 结果至少应包含：

- 两个 `LoadAST`
- 一个 `BinaryExprAST(op="add", lhs=x, rhs=y)`

### 示例 3：循环 store

输入：

```python
def kernel(A: SymbolMemory, B: SymbolMemory, N: int):
    for i in range_for(0, N, 1):
        x = load(A, i, A.get_stride())
        store(B, i, x, B.get_stride())
```

visitor 结果至少应包含：

- 一个 `ForAST`
- 循环体中的 `LoadAST`
- 一个 `StoreAST`

## 返回与错误

### 成功返回

- `visit_function(fn)` 返回 `FunctionAST`
- `visit_to_nn_ir(fn)` / `visit_to_ir(fn)` 返回 `nn dialect` module / function IR
- `emit_mlir(fn)` 返回 MLIR 风格文本字符串

### 失败返回

- 源码不可获取时抛 `OSError` / `TypeError`
- Python AST 解析失败时抛 `SyntaxError`
- 不支持的语法节点抛 `NotImplementedError`
- 名称或类型不合法时抛对应语义错误

## 测试

- 测试文件：[`test/dsl/test_ast_visitor.py`](../../test/dsl/test_ast_visitor.py)
- 执行命令：`pytest -q test/dsl/test_ast_visitor.py`

### 测试目标

- 验证函数源码可被正确提取与解析
- 验证函数签名可绑定为 `TensorAST` / `ScalarArgAST`
- 验证 `load/store/add/compare/for` 可生成正确 AST
- 验证 `visit_to_nn_ir()` 可生成合法 `nn dialect` IR
- 验证 `emit_mlir()` 可打印合法 MLIR 风格文本
- 验证源码位置信息被保留
- 验证不支持节点能稳定报错

### 测试标准

- AST 结构可稳定比较
- `nn dialect` IR 结构可稳定比较
- MLIR 风格文本可稳定比较或 round-trip
- 错误信息包含函数名与源码位置

### 功能与用例清单

| 用例 ID | 功能 | 场景 | 前置条件 | 操作 | 预期结果 |
| --- | --- | --- | --- | --- | --- |
| AV-001 | 源码加载 | 可获取源码的函数 | 普通 Python 函数 | `load_function_source(fn)` | 返回源码、签名、位置 |
| AV-002 | AST 构造 | `SymbolMemory + int` 参数 | 函数签名合法 | `visit_function(fn)` | 返回 `FunctionAST` |
| AV-003 | 表达式访问 | `load + add + return` | 调用均合法 | `visit_function(fn)` | 生成 `LoadAST` / `BinaryExprAST` |
| AV-004 | 循环访问 | `for i in range_for(...)` | 循环形式合法 | `visit_function(fn)` | 生成 `ForAST` |
| AV-005 | 直接产 `nn` IR | 简单 kernel | AST 合法 | `visit_to_nn_ir(fn)` | 返回 `nn dialect` module |
| AV-005A | 打印 MLIR | 简单 kernel | `nn dialect` IR 合法 | `emit_mlir(fn)` | 返回 MLIR 风格文本 |
| AV-006 | 名称错误 | 未定义变量 | 缺少绑定 | `visit_function(fn)` | 抛 `NameError` |
| AV-007 | 类型错误 | 非法参数类型 | 注解不支持 | `visit_function(fn)` | 抛 `TypeError` |
| AV-008 | 语法限制 | `try/with/lambda` | 命中不支持节点 | `visit_function(fn)` | 抛 `NotImplementedError` |
| AV-009 | 位置跟踪 | 多行函数体 | 节点有位置信息 | visitor | 返回 line/column/source segment |
| AV-010 | 形状校验 | `Memory + Memory` shape 不一致 | 输入类型已知 | `visit_to_nn_ir(fn)` | 在前端或 AST 校验阶段报错 |

## 推荐联网搜索

建议优先查以下网站：

- Python `ast` 官方文档：<https://docs.python.org/3/library/ast.html>
- Python `inspect` 官方文档：<https://docs.python.org/3/library/inspect.html>
- Triton 官方文档：
  - `triton.jit`: <https://triton-lang.org/main/python-api/generated/triton.jit.html>
  - Triton dialects: <https://triton-lang.org/main/dialects/dialects.html>
  - `tt` dialect: <https://triton-lang.org/main/dialects/TritonDialect.html>
- PyTorch 官方文档：
  - FX / ATen IR 变换：<https://docs.pytorch.org/docs/stable/user_guide/torch_compiler/torch.compiler_transformations.html>
  - PyTorch 2 论文 PDF（含 TorchInductor IR 章节）：<https://docs.pytorch.org/assets/pytorch2-2.pdf>

推荐关键词：

- `python ast.NodeVisitor inspect.getsource DSL frontend`
- `triton jit ast visitor ttir code generator`
- `triton tt dialect mlir tensor descriptor`
- `torchinductor lowering define-by-run IR symbolic interpretation`
- `torch fx transformer call_function lowering`
- `python ast get_source_segment source location diagnostics`
