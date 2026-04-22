"""DSL AST node definitions.

创建者: 小李飞刀
最后一次更改: jcc你莫辜负

功能说明:
- 定义 DSL AST 节点与公共数据结构。
- 仅包含节点数据结构，不包含解析实现。

使用示例:
- from kernel_gen.dsl.ast import FunctionAST, BlockAST
- FunctionAST(name="kernel", inputs=[], outputs=[], body=BlockAST([]))

关联文件:
- spec: spec/dsl/ast_nodes.md
- test: test/dsl/test_ast_nodes.py
- 功能实现: kernel_gen/dsl/ast/nodes.py
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable

from kernel_gen.operation import arch as _KG_OPERATION_ARCH
from kernel_gen.symbol_variable.memory import MemorySpace
from kernel_gen.symbol_variable.type import NumericType


@dataclass(frozen=True)
class SourceLocation:
    """源码位置信息。

    创建者: 小李飞刀
    最后一次更改: 小李飞刀

    功能说明:
    - 记录 AST 节点在源码中的行列位置。

    使用示例:
    - SourceLocation(line=1, column=0)

    关联文件:
    - spec: spec/dsl/ast.md
    - test: test/dsl/test_ast_visitor.py
    - 功能实现: kernel_gen/dsl/ast/nodes.py
    """

    line: int
    column: int


@dataclass(frozen=True)
class Diagnostic:
    """前端诊断信息。

    创建者: 小李飞刀
    最后一次更改: 小李飞刀

    功能说明:
    - 记录错误消息与对应的源码位置信息。

    使用示例:
    - Diagnostic(message="Unsupported syntax", location=SourceLocation(3, 4))

    关联文件:
    - spec: spec/dsl/ast_visitor.md
    - test: test/dsl/test_ast_visitor.py
    - 功能实现: kernel_gen/dsl/ast/nodes.py
    """

    message: str
    location: SourceLocation | None = None


@dataclass(frozen=True)
class ModuleAST:
    """DSL 模块节点。

    创建者: 小李飞刀
    最后一次更改: 小李飞刀

    功能说明:
    - 聚合多个 `FunctionAST` 作为 DSL 模块入口。

    使用示例:
    - ModuleAST(functions=[FunctionAST(name="kernel", inputs=[], outputs=[], body=BlockAST([]))])

    关联文件:
    - spec: spec/dsl/ast.md
    - test: test/dsl/test_ast_visitor.py
    - 功能实现: kernel_gen/dsl/ast/nodes.py
    """

    functions: list[FunctionAST]


@dataclass(frozen=True)
class TensorAST:
    """张量参数节点。

    创建者: 小李飞刀
    最后一次更改: 小李飞刀

    功能说明:
    - 表示函数签名中的张量输入。

    使用示例:
    - TensorAST(name="A", memory=memory)

    关联文件:
    - spec: spec/dsl/ast.md
    - test: test/dsl/test_ast_visitor.py
    - 功能实现: kernel_gen/dsl/ast/nodes.py
    """

    name: str
    memory: object
    location: SourceLocation | None = None


@dataclass(frozen=True)
class ScalarArgAST:
    """标量参数节点。

    创建者: 小李飞刀
    最后一次更改: 小李飞刀

    功能说明:
    - 表示函数签名中的标量输入。

    使用示例:
    - ScalarArgAST(name="n", value_type=int)

    关联文件:
    - spec: spec/dsl/ast.md
    - test: test/dsl/test_ast_visitor.py
    - 功能实现: kernel_gen/dsl/ast/nodes.py
    """

    name: str
    value_type: type
    is_symbolic: bool = False
    location: SourceLocation | None = None


@dataclass(frozen=True)
class PtrArgAST:
    """指针参数节点。

    创建者: 金铲铲大作战
    最后一次更改: 朽木露琪亚

    功能说明:
    - 表示函数签名中的指针输入参数。
    - 仅承载 pointee dtype，不提供 shape/stride 语义。

    使用示例:
    - PtrArgAST(name="data", dtype=f32)

    关联文件:
    - spec: spec/dsl/ast.md
    - test: test/dsl/test_ast.py
    - 功能实现: kernel_gen/dsl/ast/nodes.py
    """

    name: str
    dtype: object
    location: SourceLocation | None = None


@dataclass(frozen=True)
class VarAST:
    """变量节点。

    创建者: 小李飞刀
    最后一次更改: 小李飞刀

    功能说明:
    - 表示循环变量或中间变量。

    使用示例:
    - VarAST(name="i")

    关联文件:
    - spec: spec/dsl/ast.md
    - test: test/dsl/test_ast_visitor.py
    - 功能实现: kernel_gen/dsl/ast/nodes.py
    """

    name: str
    location: SourceLocation | None = None


@dataclass(frozen=True)
class BlockAST:
    """语句块节点。

    创建者: 小李飞刀
    最后一次更改: 小李飞刀

    功能说明:
    - 有序保存 AST 语句节点。

    使用示例:
    - BlockAST(statements=[])

    关联文件:
    - spec: spec/dsl/ast.md
    - test: test/dsl/test_ast_visitor.py
    - 功能实现: kernel_gen/dsl/ast/nodes.py
    """

    statements: list[object]
    location: SourceLocation | None = None


@dataclass(frozen=True)
class ForAST:
    """循环节点。

    创建者: 小李飞刀
    最后一次更改: 小李飞刀

    功能说明:
    - 表示 DSL 中的 for 循环结构。

    使用示例:
    - ForAST(var=VarAST("i"), start=ConstAST(0), end=ConstAST(10), body=BlockAST([]))

    关联文件:
    - spec: spec/dsl/ast.md
    - test: test/dsl/test_ast_visitor.py
    - 功能实现: kernel_gen/dsl/ast/nodes.py
    """

    var: VarAST
    start: object
    end: object
    body: BlockAST
    step: object | None = None
    location: SourceLocation | None = None


@dataclass(frozen=True)
class StoreAST:
    """存储节点。

    创建者: 小李飞刀
    最后一次更改: 小李飞刀

    功能说明:
    - 描述向张量写入的语义。

    使用示例:
    - StoreAST(tensor=TensorAST("A", memory), offset=ConstAST(0), stride=None, value=ConstAST(1))

    关联文件:
    - spec: spec/dsl/ast.md
    - test: test/dsl/test_ast_visitor.py
    - 功能实现: kernel_gen/dsl/ast/nodes.py
    """

    tensor: TensorAST
    offset: object
    stride: object | None
    value: object
    sizes: object | None = None
    space: MemorySpace | None = None
    kind: str = "store"
    location: SourceLocation | None = None


@dataclass(frozen=True)
class LoadAST:
    """读取节点。

    创建者: 小李飞刀
    最后一次更改: 小李飞刀

    功能说明:
    - 描述从张量读取的语义。

    使用示例:
    - LoadAST(tensor=TensorAST("A", memory), offset=ConstAST(0), stride=None)

    关联文件:
    - spec: spec/dsl/ast.md
    - test: test/dsl/test_ast_visitor.py
    - 功能实现: kernel_gen/dsl/ast/nodes.py
    """

    tensor: TensorAST
    offset: object
    stride: object | None
    sizes: object | None = None
    space: MemorySpace | None = None
    kind: str = "load"
    location: SourceLocation | None = None


@dataclass(frozen=True)
class DmaAllocAST:
    """DMA alloc 节点。

    创建者: OpenAI
    最后一次更改: OpenAI

    功能说明:
    - 表示 `alloc(...)` 的 DSL 调用。

    使用示例:
    - DmaAllocAST(shape=[ConstAST(4)], dtype=NumericType.Float32, space=MemorySpace.SM)

    关联文件:
    - spec: spec/dsl/ast.md
    - test: test/dsl/test_ast_visitor.py
    - 功能实现: kernel_gen/dsl/ast/nodes.py
    """

    shape: object
    dtype: NumericType
    space: MemorySpace = MemorySpace.GM
    stride: object | None = None
    location: SourceLocation | None = None


@dataclass(frozen=True)
class DmaCopyAST:
    """DMA copy 节点。

    创建者: OpenAI
    最后一次更改: OpenAI

    功能说明:
    - 表示 `copy(...)` 的 DSL 调用。

    使用示例:
    - DmaCopyAST(source=TensorAST("src", memory), space=MemorySpace.SM)

    关联文件:
    - spec: spec/dsl/ast.md
    - test: test/dsl/test_ast_visitor.py
    - 功能实现: kernel_gen/dsl/ast/nodes.py
    """

    source: object
    space: MemorySpace
    location: SourceLocation | None = None


@dataclass(frozen=True)
class DmaCastAST:
    """DMA cast 节点。

    创建者: OpenAI
    最后一次更改: OpenAI

    功能说明:
    - 表示 `cast(...)` 的 DSL 调用。

    使用示例:
    - DmaCastAST(source=TensorAST("src", memory), dtype=NumericType.Float16)

    关联文件:
    - spec: spec/dsl/ast.md
    - test: test/dsl/test_ast_visitor.py
    - 功能实现: kernel_gen/dsl/ast/nodes.py
    """

    source: object
    dtype: NumericType
    memoryspace: MemorySpace | None = None
    location: SourceLocation | None = None


@dataclass(frozen=True)
class DmaViewAST:
    """DMA view 节点。

    创建者: OpenAI
    最后一次更改: OpenAI

    功能说明:
    - 表示 `view(...)` 的 DSL 调用。

    使用示例:
    - DmaViewAST(source=tensor, offset=[ConstAST(0)], size=[ConstAST(4)], stride=[ConstAST(1)])

    关联文件:
    - spec: spec/dsl/ast.md
    - test: test/dsl/test_ast_visitor.py
    - 功能实现: kernel_gen/dsl/ast/nodes.py
    """

    source: object
    offset: object
    size: object
    stride: object
    location: SourceLocation | None = None


@dataclass(frozen=True)
class DmaReshapeAST:
    """DMA reshape 节点。

    创建者: OpenAI
    最后一次更改: OpenAI

    功能说明:
    - 表示 `reshape(...)` 的 DSL 调用。

    使用示例:
    - DmaReshapeAST(source=tensor, shape=[ConstAST(8), ConstAST(8)])

    关联文件:
    - spec: spec/dsl/ast.md
    - test: test/dsl/test_ast_visitor.py
    - 功能实现: kernel_gen/dsl/ast/nodes.py
    """

    source: object
    shape: object
    location: SourceLocation | None = None


@dataclass(frozen=True)
class DmaFlattenAST:
    """DMA flatten 节点。

    创建者: OpenAI
    最后一次更改: OpenAI

    功能说明:
    - 表示 `flatten(...)` 的 DSL 调用。

    使用示例:
    - DmaFlattenAST(source=tensor)

    关联文件:
    - spec: spec/dsl/ast.md
    - test: test/dsl/test_ast_visitor.py
    - 功能实现: kernel_gen/dsl/ast/nodes.py
    """

    source: object
    location: SourceLocation | None = None


@dataclass(frozen=True)
class DmaFreeAST:
    """DMA free 节点。

    创建者: OpenAI
    最后一次更改: OpenAI

    功能说明:
    - 表示 `free(...)` 的 DSL 语句调用。

    使用示例:
    - DmaFreeAST(value=tensor)

    关联文件:
    - spec: spec/dsl/ast.md
    - test: test/dsl/test_ast_visitor.py
    - 功能实现: kernel_gen/dsl/ast/nodes.py
    """

    value: object
    location: SourceLocation | None = None


@dataclass(frozen=True)
class Img2ColAST:
    """img2col helper 节点。

    创建者: 金铲铲大作战
    最后一次更改: 金铲铲大作战

    功能说明:
    - 表示 `img2col1d/img2col2d` 的 DSL helper 调用。
    - 保留调用名、位置参数与关键字参数的 AST 表达式。

    使用示例:
    - Img2ColAST(kind="img2col2d", args=[tile], kwargs={"kh": ConstAST(3)})

    关联文件:
    - spec: spec/dsl/ast.md
    - test: test/dsl/test_ast.py
    - 功能实现: kernel_gen/dsl/ast/nodes.py
    """

    kind: str
    args: list[object]
    kwargs: dict[str, object]
    location: SourceLocation | None = None


@dataclass(frozen=True)
class NnBroadcastAST:
    """nn.broadcast helper 节点。

    创建者: 小李飞刀
    最后一次更改: 小李飞刀

    功能说明:
    - 表示 `broadcast(value, target)` 的 DSL helper 调用。
    - 保留输入与目标表达式，交由 lowering 阶段验证形状/类型。

    使用示例:
    - NnBroadcastAST(value=VarAST("x"), target=VarAST("y"))

    关联文件:
    - spec: spec/dsl/ast.md
    - test: test/dsl/test_ast.py
    - 功能实现: kernel_gen/dsl/ast/nodes.py
    """

    value: object
    target: object
    location: SourceLocation | None = None


@dataclass(frozen=True)
class NnBroadcastToAST:
    """nn.broadcast_to helper 节点。

    创建者: 小李飞刀
    最后一次更改: 小李飞刀

    功能说明:
    - 表示 `broadcast_to(source, target_shape, space)` 的 DSL helper 调用。
    - 记录源张量、目标 shape 表达式与 MemorySpace。

    使用示例:
    - NnBroadcastToAST(source=VarAST("x"), target_shape=[ConstAST(2)], space=MemorySpace.GM)

    关联文件:
    - spec: spec/dsl/ast.md
    - test: test/dsl/test_ast.py
    - 功能实现: kernel_gen/dsl/ast/nodes.py
    """

    source: object
    target_shape: object
    space: object
    location: SourceLocation | None = None


@dataclass(frozen=True)
class NnTransposeAST:
    """nn.transpose helper 节点。

    创建者: 小李飞刀
    最后一次更改: 小李飞刀

    功能说明:
    - 表示 `transpose(value, perm)` 的 DSL helper 调用。
    - 记录输入与 perm 表达式，交由 lowering 阶段校验。

    使用示例:
    - NnTransposeAST(value=VarAST("x"), perm=[ConstAST(1), ConstAST(0)])

    关联文件:
    - spec: spec/dsl/ast.md
    - test: test/dsl/test_ast.py
    - 功能实现: kernel_gen/dsl/ast/nodes.py
    """

    value: object
    perm: object
    location: SourceLocation | None = None


@dataclass(frozen=True)
class NnUnaryAST:
    """nn unary helper 节点。

    创建者: jcc你莫辜负
    最后一次更改: 小李飞刀

    功能说明:
    - 表示 `relu/sigmoid/tanh/leaky_relu/hard_sigmoid/exp` 的 DSL helper 调用。
    - 统一保留输入、alpha/beta 参数，供 lowering 阶段解析。

    使用示例:
    - NnUnaryAST(kind="relu", value=TensorAST("x", memory))
    - NnUnaryAST(kind="leaky_relu", value=VarAST("x"), alpha=ConstAST(0.1))

    关联文件:
    - spec: spec/dsl/ast.md
    - test: test/dsl/test_ast.py
    - 功能实现: kernel_gen/dsl/ast/nodes.py
    """

    kind: str
    value: object
    alpha: object | None = None
    beta: object | None = None
    location: SourceLocation | None = None


@dataclass(frozen=True)
class NnReduceAST:
    """nn reduce helper 节点。

    创建者: jcc你莫辜负
    最后一次更改: jcc你莫辜负

    功能说明:
    - 表示 `reduce_sum/reduce_min/reduce_max` 的 DSL helper 调用。
    - 保留 axis/keepdim 表达式，便于 lowering 阶段做静态推导与 verifier 兜底。

    使用示例:
    - NnReduceAST(kind="reduce_sum", value=VarAST("x"), axis=ConstAST(1), keepdim=ConstAST(True))

    关联文件:
    - spec: spec/dsl/ast.md
    - test: test/dsl/test_ast.py
    - 功能实现: kernel_gen/dsl/ast/nodes.py
    """

    kind: str
    value: object
    axis: object | None = None
    keepdim: object | None = None
    location: SourceLocation | None = None


@dataclass(frozen=True)
class NnSoftmaxAST:
    """nn.softmax helper 节点。

    创建者: 小李飞刀
    最后一次更改: 小李飞刀

    功能说明:
    - 表示 `softmax(value, axis=...)` 的 DSL helper 调用。
    - 记录输入与 axis 表达式，交由 lowering 阶段解析 axis。

    使用示例:
    - NnSoftmaxAST(value=VarAST("x"), axis=ConstAST(1))

    关联文件:
    - spec: spec/dsl/ast.md
    - test: test/dsl/test_ast.py
    - 功能实现: kernel_gen/dsl/ast/nodes.py
    """

    value: object
    axis: object | None = None
    location: SourceLocation | None = None


@dataclass(frozen=True)
class MatmulAST:
    """matmul helper 节点。

    创建者: 朽木露琪亚
    最后一次更改: 朽木露琪亚

    功能说明:
    - 表示 `matmul(lhs, rhs, memoryspace=...)` 的 DSL helper 调用。
    - 保留左右操作数与可选 memoryspace，供 raw `func.func` lowering 直接生成 `nn.matmul`。

    使用示例:
    - MatmulAST(lhs=VarAST("lhs"), rhs=VarAST("rhs"), memoryspace=MemorySpace.GM)

    关联文件:
    - spec: spec/dsl/ast.md
    - test: test/dsl/test_ast_visitor.py
    - 功能实现: kernel_gen/dsl/ast/nodes.py
    """

    lhs: object
    rhs: object
    memoryspace: MemorySpace | None = None
    location: SourceLocation | None = None


@dataclass(frozen=True)
class FCAST:
    """fc helper 节点。

    创建者: 小李飞刀
    最后一次更改: 小李飞刀

    功能说明:
    - 表示 `fc(value, weight)` 的 DSL helper 调用。
    - 保留输入与权重，用于 lowering 阶段生成 `nn.transpose + nn.matmul`。

    使用示例:
    - FCAST(value=VarAST("x"), weight=VarAST("w"))

    关联文件:
    - spec: spec/dsl/ast.md
    - test: test/dsl/test_mlir_gen.py
    - 功能实现: kernel_gen/dsl/ast/nodes.py
    """

    value: object
    weight: object
    location: SourceLocation | None = None


@dataclass(frozen=True)
class ConvAST:
    """conv helper 节点。

    创建者: 朽木露琪亚
    最后一次更改: 朽木露琪亚

    功能说明:
    - 表示 `conv(value, weight, sh=..., sw=..., ...)` 的 DSL helper 调用。
    - 当前仅承接前端分解路径，供 lowering 阶段展开为 `nn.img2col2d + dma.reshape + nn.matmul + dma.reshape`。

    使用示例:
    - ConvAST(value=VarAST("x"), weight=VarAST("w"), kwargs={"sh": ConstAST(1)})

    关联文件:
    - spec: spec/dsl/mlir_gen.md
    - test: test/dsl/test_mlir_gen.py
    - 功能实现: kernel_gen/dsl/ast/nodes.py
    """

    value: object
    weight: object
    kwargs: dict[str, object]
    location: SourceLocation | None = None


@dataclass(frozen=True)
class BinaryExprAST:
    """二元表达式节点。

    创建者: 小李飞刀
    最后一次更改: 小李飞刀

    功能说明:
    - 表示逐元素算术表达式。

    使用示例:
    - BinaryExprAST(op="add", lhs=VarAST("x"), rhs=VarAST("y"))

    关联文件:
    - spec: spec/dsl/ast.md
    - test: test/dsl/test_ast_visitor.py
    - 功能实现: kernel_gen/dsl/ast/nodes.py
    """

    op: str
    lhs: object
    rhs: object
    location: SourceLocation | None = None


@dataclass(frozen=True)
class CompareExprAST:
    """比较表达式节点。

    创建者: 小李飞刀
    最后一次更改: 小李飞刀

    功能说明:
    - 表示逐元素比较表达式。

    使用示例:
    - CompareExprAST(op="eq", lhs=VarAST("x"), rhs=VarAST("y"))

    关联文件:
    - spec: spec/dsl/ast.md
    - test: test/dsl/test_ast_visitor.py
    - 功能实现: kernel_gen/dsl/ast/nodes.py
    """

    op: str
    lhs: object
    rhs: object
    location: SourceLocation | None = None


@dataclass(frozen=True)
class PythonCalleeCallAST:
    """Python callee 调用表达式节点。

    创建者: 小李飞刀
    最后一次更改: 小李飞刀

    功能说明:
    - 表示 DSL 语义中“应当下沉为 `func.call`”的 Python 函数调用。
    - 仅用于 `mlir_gen(...)` 组装 module 的 callee 收集与 call lowering；不属于 DMA/NN helper 调用。

    使用示例:
    - PythonCalleeCallAST(callee=helper, args=[VarAST("x")])

    关联文件:
    - spec: [spec/dsl/mlir_gen.md](spec/dsl/mlir_gen.md)
    - test: [test/dsl/test_mlir_gen.py](test/dsl/test_mlir_gen.py)
    - 功能实现: [kernel_gen/dsl/ast/nodes.py](kernel_gen/dsl/ast/nodes.py)
    """

    callee: object
    args: list[object]
    location: SourceLocation | None = None


@dataclass(frozen=True)
class SymbolToFloatAST:
    """`float(symbol.int)` 转换节点。

    创建者: 金铲铲大作战
    最后一次更改: 金铲铲大作战

    功能说明:
    - 表示 DSL 中 `float(value)` 的最小公开入口。
    - 当前仅服务于 `symbol.int -> f32` 的 `symbol.to_float` lowering 链路。

    使用示例:
    - SymbolToFloatAST(source=ScalarArgAST(name="n", value_type=int))

    关联文件:
    - spec: spec/dsl/ast.md
    - test: test/dsl/test_ast.py
    - 功能实现: kernel_gen/dsl/ast/nodes.py
    """

    source: object
    location: SourceLocation | None = None


@dataclass(frozen=True)
class TensorAxisAccessAST:
    """张量 shape/stride 访问节点。

    创建者: 金铲铲大作战
    最后一次更改: 金铲铲大作战

    功能说明:
    - 表示 `tensor.get_shape()[axis]` 或 `tensor.get_stride()[axis]` 的入口语义。
    - 保留张量引用、访问类型与轴索引表达式，避免在 AST 层提前求值。

    使用示例:
    - TensorAxisAccessAST(tensor=TensorAST("value", memory), kind="shape", axis=ConstAST(0))

    关联文件:
    - spec: spec/dsl/ast.md
    - test: test/dsl/test_ast.py
    - 功能实现: kernel_gen/dsl/ast/nodes.py
    """

    tensor: TensorAST
    kind: str
    axis: object
    location: SourceLocation | None = None


@dataclass(frozen=True)
class ArchQueryAST:
    """arch 查询表达式节点。

    创建者: 我不是牛马
    最后一次更改: 咯咯咯

    功能说明:
    - 表示 DSL 中最小 `arch` 查询调用。
    - 当前仅承载 `get_block_id()` / `get_block_num()` / `get_subthread_id()` / `get_subthread_num()` / `get_thread_id()` / `get_thread_num()` 查询名。

    使用示例:
    - ArchQueryAST(query_name="get_block_id")
    - ArchQueryAST(query_name="get_block_num")
    - ArchQueryAST(query_name="get_subthread_id")
    - ArchQueryAST(query_name="get_subthread_num")
    - ArchQueryAST(query_name="get_thread_id")
    - ArchQueryAST(query_name="get_thread_num")

    关联文件:
    - spec: spec/dsl/ast.md
    - test: test/dsl/test_ast_visitor.py
    - 功能实现: kernel_gen/dsl/ast/nodes.py
    """

    query_name: str
    location: SourceLocation | None = None


@dataclass(frozen=True)
class ArchGetDynamicMemoryAST:
    """arch 动态内存入口表达式节点。

    创建者: 我不是牛马
    最后一次更改: 金铲铲大作战

    功能说明:
    - 表示 `get_dynamic_memory(space)` 的调用节点。
    - 仅允许片上空间 `SM/LM/TSM/TLM1/TLM2/TLM3`。

    使用示例:
    - ArchGetDynamicMemoryAST(space=MemorySpace.SM)

    关联文件:
    - spec: spec/dsl/ast.md
    - test: test/dsl/test_ast_visitor.py
    - 功能实现: kernel_gen/dsl/ast/nodes.py
    """

    space: MemorySpace
    location: SourceLocation | None = None


@dataclass(frozen=True)
class ArchBarrierAST:
    """arch barrier 语句节点。

    创建者: 小李飞刀
    最后一次更改: 小李飞刀

    功能说明:
    - 表示 `barrier(visibility=[...], scope=BarrierScope.THREAD)` 的同步语句。
    - 仅保存 visibility / scope 两个显式字段，具体 verifier 细节交由 lowering 负责。

    使用示例:
    - ArchBarrierAST(
    -     visibility=[_KG_OPERATION_ARCH.BarrierVisibility.TSM, _KG_OPERATION_ARCH.BarrierVisibility.TLM],
    -     scope=_KG_OPERATION_ARCH.BarrierScope.THREAD,
    - )

    关联文件:
    - spec: spec/dsl/ast.md
    - test: test/dsl/test_ast.py
    - 功能实现: kernel_gen/dsl/ast/nodes.py
    """

    visibility: list[_KG_OPERATION_ARCH.BarrierVisibility]
    scope: _KG_OPERATION_ARCH.BarrierScope
    location: SourceLocation | None = None


@dataclass(frozen=True)
class ArchLaunchKernelAST:
    """arch 启动描述语句节点。

    创建者: 小李飞刀
    最后一次更改: 小李飞刀

    功能说明:
    - 表示 `launch_kernel[block, thread, subthread, shared_memory_size](callee, *args)` 的启动描述。
    - 仅校验 callee symbol ref 与四字段 launch ABI 的基础约束，不承担 lowering 细节。

    使用示例:
    - ArchLaunchKernelAST(
    -     callee="kernel_body",
    -     block=ScalarArgAST("block", int),
    -     thread=ConstAST(128),
    -     subthread=ConstAST(4),
    -     args=[TensorAST("lhs", memory)],
    -     shared_memory_size=ConstAST(0),
    - )

    关联文件:
    - spec: spec/dsl/ast.md
    - test: test/dsl/test_ast.py
    - 功能实现: kernel_gen/dsl/ast/nodes.py
    """

    callee: str
    block: object
    thread: object
    subthread: object
    args: list[object] = field(default_factory=list)
    shared_memory_size: object = 0
    location: SourceLocation | None = None


@dataclass(frozen=True)
class ConstAST:
    """常量节点。

    创建者: 小李飞刀
    最后一次更改: 小李飞刀

    功能说明:
    - 表示常量值。

    使用示例:
    - ConstAST(value=1)

    关联文件:
    - spec: spec/dsl/ast.md
    - test: test/dsl/test_ast_visitor.py
    - 功能实现: kernel_gen/dsl/ast/nodes.py
    """

    value: object
    location: SourceLocation | None = None


@dataclass(frozen=True)
class FunctionAST:
    """函数节点。

    创建者: 小李飞刀
    最后一次更改: 小李飞刀

    功能说明:
    - 表示可 lowering 的 DSL 函数入口。

    使用示例:
    - FunctionAST(name="kernel", inputs=[], outputs=[], body=BlockAST([]))

    关联文件:
    - spec: spec/dsl/ast.md
    - test: test/dsl/test_ast_visitor.py
    - 功能实现: kernel_gen/dsl/ast/nodes.py
    """

    name: str
    inputs: list[TensorAST | ScalarArgAST | PtrArgAST]
    outputs: list[TensorAST | ScalarArgAST]
    body: BlockAST
    location: SourceLocation | None = None
    source: str | None = None
    py_ast: object | None = None
    diagnostics: list[Diagnostic] = field(default_factory=list)
    has_explicit_return: bool = False
    has_return_annotation: bool = False
    returns_none: bool = False

    def iter_inputs(self: FunctionAST) -> Iterable[TensorAST | ScalarArgAST | PtrArgAST]:
        """迭代输入参数。

        创建者: 小李飞刀
        最后一次更改: 小李飞刀

        功能说明:
        - 提供输入参数（Tensor/Scalar/Ptr）的统一迭代入口。

        使用示例:
        - list(func_ast.iter_inputs())

        关联文件:
        - spec: spec/dsl/ast.md
        - test: test/dsl/test_ast_visitor.py
        - 功能实现: kernel_gen/dsl/ast/nodes.py
        """

        return iter(self.inputs)
