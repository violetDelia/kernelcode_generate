# nodes.md

## 功能简介

- 定义 AST 节点与公共数据结构，作为解析与下游遍历的输入。
- 只提供数据结构，不负责语法解析或 MLIR 生成。

## API 列表

- `class SourceLocation(line: int, column: int)`
- `class Diagnostic(message: str, location: SourceLocation | None = None)`
- `class ModuleAST(functions: list[FunctionAST])`
- `class FunctionAST(name: str, inputs: list[TensorAST | ScalarArgAST | PtrArgAST], outputs: list[TensorAST | ScalarArgAST], body: BlockAST, location: SourceLocation | None = None, source: str | None = None, py_ast: object | None = None, diagnostics: list[Diagnostic] = field(default_factory=list), has_explicit_return: bool = False, has_return_annotation: bool = False, returns_none: bool = False)`
- `class BlockAST(statements: list[object], location: SourceLocation | None = None)`
- `class TensorAST(name: str, memory: object, location: SourceLocation | None = None)`
- `class ScalarArgAST(name: str, value_type: type, is_symbolic: bool = False, location: SourceLocation | None = None)`
- `class PtrArgAST(name: str, dtype: object, location: SourceLocation | None = None)`
- `class VarAST(name: str, location: SourceLocation | None = None)`
- `class ConstAST(value: object, location: SourceLocation | None = None)`
- `class ForAST(var: VarAST, start: object, end: object, body: BlockAST, step: object | None = None, location: SourceLocation | None = None)`
- `class StoreAST(tensor: TensorAST, offset: object, stride: object | None, value: object, sizes: object | None = None, space: MemorySpace | None = None, kind: str = "store", location: SourceLocation | None = None)`
- `class LoadAST(tensor: TensorAST, offset: object, stride: object | None, sizes: object | None = None, space: MemorySpace | None = None, kind: str = "load", location: SourceLocation | None = None)`
- `class DmaAllocAST(shape: object, dtype: NumericType, space: MemorySpace = MemorySpace.GM, stride: object | None = None, location: SourceLocation | None = None)`
- `class DmaCopyAST(source: object, space: MemorySpace, location: SourceLocation | None = None)`
- `class DmaCastAST(source: object, dtype: NumericType, memoryspace: MemorySpace | None = None, location: SourceLocation | None = None)`
- `class DmaViewAST(source: object, offset: object, size: object, stride: object, location: SourceLocation | None = None)`
- `class DmaReshapeAST(source: object, shape: object, location: SourceLocation | None = None)`
- `class DmaFlattenAST(source: object, location: SourceLocation | None = None)`
- `class DmaFreeAST(value: object, location: SourceLocation | None = None)`
- `class Img2ColAST(kind: str, args: list[object], kwargs: dict[str, object], location: SourceLocation | None = None)`
- `class NnBroadcastAST(value: object, target: object, location: SourceLocation | None = None)`
- `class NnBroadcastToAST(source: object, target_shape: object, space: object, location: SourceLocation | None = None)`
- `class NnTransposeAST(value: object, perm: object, location: SourceLocation | None = None)`
- `class NnUnaryAST(kind: str, value: object, alpha: object | None = None, beta: object | None = None, location: SourceLocation | None = None)`
- `class NnReduceAST(kind: str, value: object, axis: object | None = None, keepdim: object | None = None, location: SourceLocation | None = None)`
- `class NnSoftmaxAST(value: object, axis: object | None = None, location: SourceLocation | None = None)`
- `class MatmulAST(lhs: object, rhs: object, memoryspace: MemorySpace | None = None, location: SourceLocation | None = None)`
- `class FCAST(value: object, weight: object, location: SourceLocation | None = None)`
- `class ConvAST(value: object, weight: object, kwargs: dict[str, object], location: SourceLocation | None = None)`
- `class BinaryExprAST(op: str, lhs: object, rhs: object, location: SourceLocation | None = None)`
- `class CompareExprAST(op: str, lhs: object, rhs: object, location: SourceLocation | None = None)`
- `class PythonCalleeCallAST(callee: object, args: list[object], location: SourceLocation | None = None)`
- `class SymbolToFloatAST(source: object, location: SourceLocation | None = None)`
- `class TensorAxisAccessAST(tensor: TensorAST, kind: str, axis: object, location: SourceLocation | None = None)`
- `class ArchQueryAST(query_name: str, location: SourceLocation | None = None)`
- `class ArchGetDynamicMemoryAST(space: MemorySpace, location: SourceLocation | None = None)`
- `class ArchBarrierAST(visibility: list[BarrierVisibility], scope: BarrierScope, location: SourceLocation | None = None)`
- `class ArchLaunchKernelAST(callee: str, block: object, thread: object, subthread: object, args: list[object] = field(default_factory=list), shared_memory_size: object = 0, location: SourceLocation | None = None)`

## 文档信息

- 创建者：`睡觉小分队`
- 最后一次更改：`小李飞刀`
- `spec`：[`spec/dsl/ast/nodes.md`](../../../spec/dsl/ast/nodes.md)
- `功能实现`：[`kernel_gen/dsl/ast/nodes.py`](../../../kernel_gen/dsl/ast/nodes.py)
- `test`：[`test/dsl/ast/test_nodes.py`](../../../test/dsl/ast/test_nodes.py)

## 依赖

- Python `dataclasses`/`typing`：节点容器与类型注解。
- [`spec/symbol_variable/memory.md`](../../../spec/symbol_variable/memory.md)：`MemorySpace` 枚举语义。
- [`spec/include/api/Arch.md`](../../../spec/include/api/Arch.md)：`BarrierScope` 枚举名与 arch helper 入口形态。
- [`spec/dsl/ast/__init__.md`](../../../spec/dsl/ast/__init__.md)：AST 节点字段语义与解析链路的整体合同。

## 术语

- `Node`：AST 节点数据结构。
- `Expr`：表达式节点。
- `Stmt`：语句节点。

## 目标

- 提供稳定的 AST 节点定义与字段语义。
- 支撑解析与下游遍历对节点类型的引用。

## 限制与边界

- 不解析源码，不生成 MLIR。
- 不做优化或后端相关行为。
- 节点不携带 `target` 或设备参数语义。
- 节点字段由解析入口填充，本模块不做语义校验。

## 公开接口

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

### AST 节点清单

功能说明：导出 AST 节点类型，字段语义与 `spec/dsl/ast/__init__.md` 的对应条目保持一致。

参数说明：

- 各节点字段由解析入口填充；本模块不对字段做语义计算。

使用示例：

```python
loc = SourceLocation(line=1, column=0)
lhs = VarAST(name="x", location=loc)
rhs = VarAST(name="y", location=loc)
expr = BinaryExprAST(op="add", lhs=lhs, rhs=rhs, location=loc)
block = BlockAST([expr], location=loc)
func = FunctionAST(name="add", inputs=[], outputs=[], body=block, location=loc)
```

注意事项：

- 节点对象仅承载结构化语义，不执行计算。
- 节点集合应通过 `kernel_gen.dsl.ast` facade 对外导出，以保持导入路径一致。

返回与限制：

- 公开节点类型清单如下（按用途分组）：
  - 基础与容器：`ModuleAST`、`FunctionAST`、`BlockAST`、`TensorAST`、`ScalarArgAST`、`PtrArgAST`、`VarAST`、`ConstAST`。
  - 控制与存取：`ForAST`、`StoreAST`、`LoadAST`。
  - DMA 入口：`DmaAllocAST`、`DmaCopyAST`、`DmaCastAST`、`DmaViewAST`、`DmaReshapeAST`、`DmaFlattenAST`、`DmaFreeAST`。
  - NN 入口：`Img2ColAST`、`NnBroadcastAST`、`NnBroadcastToAST`、`NnTransposeAST`、`NnUnaryAST`、`NnReduceAST`、`NnSoftmaxAST`、`MatmulAST`、`FCAST`、`ConvAST`。
  - 表达式与调用：`BinaryExprAST`、`CompareExprAST`、`PythonCalleeCallAST`、`SymbolToFloatAST`、`TensorAxisAccessAST`。
  - 架构入口：`ArchQueryAST`、`ArchGetDynamicMemoryAST`、`ArchBarrierAST`、`ArchLaunchKernelAST`。

## 测试

- 测试文件：[`test/dsl/ast/test_nodes.py`](../../../test/dsl/ast/test_nodes.py)
- 执行命令：`pytest -q test/dsl/ast/test_nodes.py`
- 测试目标：
  - 覆盖 `SourceLocation` 与 `Diagnostic` 的字段构造。
  - 覆盖核心 AST 节点的字段持有与类型归属。
  - 覆盖 `kernel_gen.dsl.ast` re-export 的节点类型可被导入。
- 功能与用例清单：
  - AST-N-001：构造基础节点并读取字段。（`test_ast_nodes_construct_basic_types`）
  - AST-N-002：构造表达式节点并挂载到 `BlockAST`。（`test_ast_nodes_construct_expr_block`）
  - AST-N-003：从 `kernel_gen.dsl.ast` 导入节点类型。（`test_ast_nodes_facade_reexport`）
