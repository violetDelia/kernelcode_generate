"""DSL AST definitions.

创建者: 小李飞刀
最后一次更改: 小李飞刀

功能说明:
- 定义 DSL 前端使用的 AST 节点数据结构。
- 提供 `parse_function` 解析入口，将 Python 函数解析为 AST。

使用示例:
- from kernel_gen.dsl.ast import FunctionAST, BlockAST
- FunctionAST(name="kernel", inputs=[], outputs=[], body=BlockAST([]))

关联文件:
- spec: spec/dsl/ast.md
- test: test/dsl/test_ast_visitor.py
- 功能实现: kernel_gen/dsl/ast.py
"""

from __future__ import annotations

import gc as _gc

_gc_enabled = _gc.isenabled()
_gc.disable()
try:
    # NOTE: Some environments have observed an intermittent fatal assertion
    # during the very first `ast` import (related to `_ast` type initialization).
    # Disabling GC around the import reduces that window; `finally` guarantees
    # we never leak global GC state even if import fails.
    import ast as py_ast
finally:
    if _gc_enabled:
        _gc.enable()
    del _gc_enabled, _gc
import inspect
import re
import textwrap
import types
from dataclasses import dataclass, field
from typing import Iterable

import sympy as sp

from kernel_gen.operation import arch as _KG_OPERATION_ARCH
from kernel_gen.operation import dma as _KG_OPERATION_DMA
from kernel_gen.operation import nn as _KG_OPERATION_NN
from kernel_gen.symbol_variable.memory import Memory, MemorySpace
from kernel_gen.symbol_variable.symbol_dim import SymbolDim
from kernel_gen.symbol_variable.type import NumericType

_REJECT_EXTERNAL_VALUES_ENV_KEY = "__dsl_reject_external_values__"
_ALLOW_EXTERNAL_CONSTANTS_ENV_KEY = "__dsl_allow_external_constants__"
_LOCAL_IMPORT_SHADOW = object()
_ALLOWED_IMPORT_BOUND_HELPERS: dict[str, tuple[types.ModuleType, frozenset[str]]] = {
    "kernel_gen.operation.dma": (
        _KG_OPERATION_DMA,
        frozenset(
            {
                "load",
                "slice",
                "store",
                "deslice",
                "alloc",
                "copy",
                "cast",
                "view",
                "reshape",
                "flatten",
                "free",
            }
        ),
    ),
    "kernel_gen.operation.arch": (
        _KG_OPERATION_ARCH,
        frozenset(
            {
                "barrier",
                "get_block_id",
                "get_block_num",
                "get_subthread_id",
                "get_subthread_num",
                "get_thread_id",
                "get_thread_num",
                "get_dynamic_memory",
                "launch_kernel",
            }
        ),
    ),
    "kernel_gen.operation.nn": (
        _KG_OPERATION_NN,
        frozenset(
            {
                "img2col1d",
                "img2col2d",
                "matmul",
                "relu",
                "sigmoid",
                "tanh",
                "leaky_relu",
                "hard_sigmoid",
                "exp",
                "softmax",
                "broadcast",
                "broadcast_to",
                "reduce_sum",
                "reduce_min",
                "reduce_max",
            }
        ),
    ),
}


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
    - 功能实现: kernel_gen/dsl/ast.py
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
    - 功能实现: kernel_gen/dsl/ast.py
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
    - 功能实现: kernel_gen/dsl/ast.py
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
    - 功能实现: kernel_gen/dsl/ast.py
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
    - 功能实现: kernel_gen/dsl/ast.py
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
    - 功能实现: kernel_gen/dsl/ast.py
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
    - 功能实现: kernel_gen/dsl/ast.py
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
    - 功能实现: kernel_gen/dsl/ast.py
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
    - 功能实现: kernel_gen/dsl/ast.py
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
    - 功能实现: kernel_gen/dsl/ast.py
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
    - 功能实现: kernel_gen/dsl/ast.py
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
    - 功能实现: kernel_gen/dsl/ast.py
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
    - 功能实现: kernel_gen/dsl/ast.py
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
    - 功能实现: kernel_gen/dsl/ast.py
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
    - 功能实现: kernel_gen/dsl/ast.py
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
    - 功能实现: kernel_gen/dsl/ast.py
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
    - 功能实现: kernel_gen/dsl/ast.py
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
    - 功能实现: kernel_gen/dsl/ast.py
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
    - 功能实现: kernel_gen/dsl/ast.py
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
    - 功能实现: kernel_gen/dsl/ast.py
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
    - 功能实现: kernel_gen/dsl/ast.py
    """

    source: object
    target_shape: object
    space: object
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
    - 功能实现: kernel_gen/dsl/ast.py
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
    - 功能实现: kernel_gen/dsl/ast.py
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
    - 功能实现: kernel_gen/dsl/ast.py
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
    - 功能实现: kernel_gen/dsl/ast.py
    """

    lhs: object
    rhs: object
    memoryspace: MemorySpace | None = None
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
    - 功能实现: kernel_gen/dsl/ast.py
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
    - 功能实现: kernel_gen/dsl/ast.py
    """

    op: str
    lhs: object
    rhs: object
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
    - 功能实现: kernel_gen/dsl/ast.py
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
    - 功能实现: kernel_gen/dsl/ast.py
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
    - 功能实现: kernel_gen/dsl/ast.py
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
    - 仅允许片上空间 `SM/LM/TSM/TLM`。

    使用示例:
    - ArchGetDynamicMemoryAST(space=MemorySpace.SM)

    关联文件:
    - spec: spec/dsl/ast.md
    - test: test/dsl/test_ast_visitor.py
    - 功能实现: kernel_gen/dsl/ast.py
    """

    space: MemorySpace
    location: SourceLocation | None = None


@dataclass(frozen=True)
class ArchBarrierAST:
    """arch barrier 语句节点。

    创建者: 小李飞刀
    最后一次更改: 小李飞刀

    功能说明:
    - 表示 `barrier(visibility=[...], scope=BarrierScope.BLOCK)` 的同步语句。
    - 仅保存 visibility / scope 两个显式字段，具体 verifier 细节交由 lowering 负责。

    使用示例:
    - ArchBarrierAST(visibility=[MemorySpace.TSM, MemorySpace.TLM], scope=_KG_OPERATION_ARCH.BarrierScope.BLOCK)

    关联文件:
    - spec: spec/dsl/ast.md
    - test: test/dsl/test_ast.py
    - 功能实现: kernel_gen/dsl/ast.py
    """

    visibility: list[MemorySpace]
    scope: _KG_OPERATION_ARCH.BarrierScope
    location: SourceLocation | None = None


@dataclass(frozen=True)
class ArchLaunchKernelAST:
    """arch 启动描述语句节点。

    创建者: 小李飞刀
    最后一次更改: 小李飞刀

    功能说明:
    - 表示 `launch_kernel(callee, block, thread, subthread, *args)` 的启动描述。
    - 仅校验 callee symbol ref 与三层规模的基础约束，不承担 lowering 细节。

    使用示例:
    - ArchLaunchKernelAST(callee="kernel_body", block=ScalarArgAST("block", int), thread=ConstAST(128), subthread=ConstAST(4), args=[TensorAST("lhs", memory)])

    关联文件:
    - spec: spec/dsl/ast.md
    - test: test/dsl/test_ast.py
    - 功能实现: kernel_gen/dsl/ast.py
    """

    callee: str
    block: object
    thread: object
    subthread: object
    args: list[object] = field(default_factory=list)
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
    - 功能实现: kernel_gen/dsl/ast.py
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
    - 功能实现: kernel_gen/dsl/ast.py
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
        - 功能实现: kernel_gen/dsl/ast.py
        """

        return iter(self.inputs)


class AstParseError(Exception):
    """DSL AST 解析错误。

    创建者: 小李飞刀
    最后一次更改: 金铲铲大作战

    功能说明:
    - 统一解析阶段错误类型，并携带诊断信息列表。

    使用示例:
    - raise AstParseError("Unsupported syntax", [Diagnostic("...", SourceLocation(1, 0))])

    关联文件:
    - spec: spec/dsl/ast.md
    - test: test/dsl/test_ast_visitor.py
    - 功能实现: kernel_gen/dsl/ast.py
    """

    def __init__(self: AstParseError, message: str, diagnostics: list[Diagnostic]) -> None:
        super().__init__(message)
        self.message = message
        self.diagnostics = diagnostics

    def __str__(self: AstParseError) -> str:
        return self.message


class _ParseFailure(Exception):
    def __init__(self: _ParseFailure, message: str, location: SourceLocation | None) -> None:
        super().__init__(message)
        self.message = message
        self.location = location


_DTYPE_MAP: dict[str, NumericType] = {
    "f16": NumericType.Float16,
    "float16": NumericType.Float16,
    "bf16": NumericType.BFloat16,
    "bfloat16": NumericType.BFloat16,
    "f32": NumericType.Float32,
    "float32": NumericType.Float32,
    "f64": NumericType.Float64,
    "float64": NumericType.Float64,
    "i8": NumericType.Int8,
    "int8": NumericType.Int8,
    "i16": NumericType.Int16,
    "int16": NumericType.Int16,
    "i32": NumericType.Int32,
    "int32": NumericType.Int32,
    "i64": NumericType.Int64,
    "int64": NumericType.Int64,
    "u8": NumericType.Uint8,
    "uint8": NumericType.Uint8,
    "u16": NumericType.Uint16,
    "uint16": NumericType.Uint16,
    "u32": NumericType.Uint32,
    "uint32": NumericType.Uint32,
    "u64": NumericType.Uint64,
    "uint64": NumericType.Uint64,
    "i1": NumericType.Bool,
    "bool": NumericType.Bool,
}

_BIN_OP_MAP: dict[type, str] = {
    py_ast.Add: "add",
    py_ast.Sub: "sub",
    py_ast.Mult: "mul",
    py_ast.Div: "div",
    py_ast.FloorDiv: "floordiv",
}

_CMP_OP_MAP: dict[type, str] = {
    py_ast.Eq: "eq",
    py_ast.NotEq: "ne",
    py_ast.Lt: "lt",
    py_ast.LtE: "le",
    py_ast.Gt: "gt",
    py_ast.GtE: "ge",
}


def _location_from_node(node: object | None) -> SourceLocation | None:
    if node is None:
        return None
    lineno = getattr(node, "lineno", None)
    col = getattr(node, "col_offset", None)
    if lineno is None or col is None:
        return None
    return SourceLocation(lineno, col)


def _raise_parse_error(message: str, node: object | None) -> None:
    raise _ParseFailure(message, _location_from_node(node))


def _eval_symbolic_dim_node(expr: py_ast.AST, node: object | None) -> int | SymbolDim:
    """求值 tensor 维度表达式 AST 节点。

    创建者: jcc你莫辜负
    最后一次更改: jcc你莫辜负

    功能说明:
    - 仅接受 `int`、标识符与 `+ - * /` 基础算术。
    - 使用 `SymbolDim` 运算保持与运行时符号表达式一致。

    使用示例:
    - _eval_symbolic_dim_node(py_ast.parse("N + 1", mode="eval").body, None)

    关联文件:
    - spec: spec/dsl/ast.md
    - test: test/dsl/test_mlir_gen.py
    - 功能实现: kernel_gen/dsl/ast.py
    """
    if isinstance(expr, py_ast.Constant) and isinstance(expr.value, int):
        return expr.value
    if isinstance(expr, py_ast.Name):
        return SymbolDim(expr.id)
    if isinstance(expr, py_ast.UnaryOp) and isinstance(expr.op, py_ast.USub):
        value = _eval_symbolic_dim_node(expr.operand, node)
        if isinstance(value, SymbolDim):
            return SymbolDim(0) - value
        if isinstance(value, int):
            return -value
        _raise_parse_error("Unsupported tensor dimension expression", node)
    if isinstance(expr, py_ast.BinOp):
        lhs = _eval_symbolic_dim_node(expr.left, node)
        rhs = _eval_symbolic_dim_node(expr.right, node)
        if isinstance(expr.op, py_ast.Add):
            return lhs + rhs
        if isinstance(expr.op, py_ast.Sub):
            return lhs - rhs
        if isinstance(expr.op, py_ast.Mult):
            return lhs * rhs
        if isinstance(expr.op, py_ast.Div):
            if isinstance(lhs, int) and isinstance(rhs, int):
                if rhs == 0:
                    _raise_parse_error("Unsupported tensor dimension expression", node)
                if lhs % rhs != 0:
                    _raise_parse_error("Unsupported tensor dimension expression", node)
                return lhs // rhs
            if isinstance(lhs, int):
                lhs = SymbolDim(lhs)
            if isinstance(rhs, int):
                return lhs / rhs
            return lhs / rhs
        _raise_parse_error("Unsupported tensor dimension expression", node)
    _raise_parse_error("Unsupported tensor dimension expression", node)
    return 0


def _eval_symbolic_dim_expr(expr_text: str, node: object | None) -> int | SymbolDim:
    """解析 tensor 维度表达式文本为 `int` 或 `SymbolDim`。

    创建者: jcc你莫辜负
    最后一次更改: jcc你莫辜负

    功能说明:
    - 使用 Python AST 解析表达式，避免 `eval` 风险。
    - 仅支持 `+ - * /` 与 `int/名称` 组成的表达式。

    使用示例:
    - _eval_symbolic_dim_expr("(N + 1) / 2 + 1", None)

    关联文件:
    - spec: spec/dsl/ast.md
    - test: test/dsl/test_mlir_gen.py
    - 功能实现: kernel_gen/dsl/ast.py
    """
    try:
        parsed = py_ast.parse(expr_text, mode="eval").body
    except SyntaxError as exc:
        raise _ParseFailure("Unsupported tensor dimension expression", _location_from_node(node)) from exc
    return _eval_symbolic_dim_node(parsed, node)


def _split_tensor_annotation(text: str, node: object | None) -> tuple[NumericType, list[int | str | SymbolDim]]:
    """拆分 Tensor 注解并解析 dtype 与 shape 维度。

    创建者: jcc你莫辜负
    最后一次更改: jcc你莫辜负

    功能说明:
    - 解析 `Tensor[dtype, dim...]` 注解为 dtype 与维度列表。
    - 对包含算术表达式的维度使用 `SymbolDim` 运算求值，保持表达式语义。

    使用示例:
    - _split_tensor_annotation("Tensor[f32, N, (W + 1) / 2 + 1]", None)

    关联文件:
    - spec: spec/dsl/ast.md
    - test: test/dsl/test_mlir_gen.py
    - 功能实现: kernel_gen/dsl/ast.py
    """
    normalized = text.strip()
    if not normalized.startswith("Tensor[") or not normalized.endswith("]"):
        _raise_parse_error("Unsupported annotation", node)
    content = normalized[len("Tensor[") : -1].strip()
    parts = [item.strip() for item in content.split(",") if item.strip()]
    if len(parts) < 2:
        _raise_parse_error("Tensor annotation missing dimensions", node)
    dtype_key = parts[0].lower()
    if dtype_key not in _DTYPE_MAP:
        _raise_parse_error("Unsupported tensor dtype", node)
    dtype = _DTYPE_MAP[dtype_key]
    dims: list[int | str | SymbolDim] = []
    for part in parts[1:]:
        normalized = part
        if (
            len(normalized) >= 2
            and normalized[0] == normalized[-1]
            and normalized[0] in ("'", '"')
        ):
            normalized = normalized[1:-1].strip()
        if normalized.isdigit():
            dims.append(int(normalized))
        elif any(op in normalized for op in ("+", "-", "*", "/")):
            dims.append(_eval_symbolic_dim_expr(normalized, node))
        else:
            dims.append(normalized)
    return dtype, dims


def _format_joinedstr_value(
    node: py_ast.FormattedValue,
    globals_table: dict[str, object],
    builtins_table: dict[str, object],
    runtime_table: dict[str, object] | None,
) -> str:
    """静态归一化 f-string 中的表达式片段。

    创建者: OpenAI
    最后一次更改: 咯咯咯

    功能说明:
    - 仅接受可静态求值为 `int/str/SymbolDim` 的表达式。

    使用示例:
    - _format_joinedstr_value(node, globals(), __builtins__, {"N": 4})

    关联文件:
    - spec: spec/dsl/ast.md
    - test: test/dsl/test_ast_visitor.py
    - 功能实现: kernel_gen/dsl/ast.py
    """

    if node.conversion != -1 or node.format_spec is not None:
        _raise_parse_error("Unsupported formatted annotation", node)

    value_node = node.value
    if isinstance(value_node, py_ast.Name):
        if runtime_table is not None and value_node.id in runtime_table:
            value = runtime_table[value_node.id]
        else:
            value = _lookup_python_name(value_node.id, globals_table, builtins_table)
    elif isinstance(value_node, py_ast.Constant) and isinstance(value_node.value, (int, str)):
        value = value_node.value
    elif isinstance(value_node, py_ast.UnaryOp) and isinstance(value_node.op, py_ast.USub):
        operand = value_node.operand
        if isinstance(operand, py_ast.Constant) and isinstance(operand.value, int):
            value = -operand.value
        else:
            _raise_parse_error("Unsupported formatted annotation", value_node)
    else:
        _raise_parse_error("Unsupported formatted annotation", value_node)

    if isinstance(value, SymbolDim):
        return str(value.get_symbol())
    if isinstance(value, (int, str)):
        return str(value)
    _raise_parse_error("Unsupported formatted annotation", value_node)
    return ""


def _normalize_annotation_text(
    node: py_ast.Constant | py_ast.JoinedStr,
    globals_table: dict[str, object],
    builtins_table: dict[str, object],
    runtime_table: dict[str, object] | None,
) -> str:
    """将字符串或 JoinedStr 注解归一化为普通文本。

    创建者: OpenAI
    最后一次更改: OpenAI

    功能说明:
    - 支持普通字符串字面量与可静态归一化的 `f"Tensor[...]"`。

    使用示例:
    - _normalize_annotation_text(node, globals(), __builtins__, runtime_table)

    关联文件:
    - spec: spec/dsl/ast.md
    - test: test/dsl/test_ast_visitor.py
    - 功能实现: kernel_gen/dsl/ast.py
    """

    if isinstance(node, py_ast.Constant) and isinstance(node.value, str):
        return node.value
    if isinstance(node, py_ast.JoinedStr):
        parts: list[str] = []
        for value in node.values:
            if isinstance(value, py_ast.Constant) and isinstance(value.value, str):
                parts.append(value.value)
                continue
            if isinstance(value, py_ast.FormattedValue):
                parts.append(_format_joinedstr_value(value, globals_table, builtins_table, runtime_table))
                continue
            _raise_parse_error("Unsupported annotation", value)
        return "".join(parts)
    _raise_parse_error("Unsupported annotation", node)
    return ""


def _annotation_from_runtime_value(arg_name: str, runtime_value: object) -> TensorAST | ScalarArgAST | None:
    """根据 runtime 实参推断缺失注解。

    创建者: OpenAI
    最后一次更改: OpenAI

    功能说明:
    - 将 runtime 中的 `Memory`、`SymbolDim`、`int` 转为对应参数 AST。

    使用示例:
    - _annotation_from_runtime_value("n", 4)

    关联文件:
    - spec: spec/dsl/ast.md
    - test: test/dsl/test_ast_visitor.py
    - 功能实现: kernel_gen/dsl/ast.py
    """

    if isinstance(runtime_value, Memory):
        return TensorAST(name=arg_name, memory=runtime_value, location=None)
    if isinstance(runtime_value, SymbolDim):
        return ScalarArgAST(name=arg_name, value_type=int, is_symbolic=True, location=None)
    if isinstance(runtime_value, int):
        return ScalarArgAST(name=arg_name, value_type=int, location=None)
    return None


def _annotation_from_name_lookup(arg_name: str, namespace: dict[str, object]) -> TensorAST | ScalarArgAST | None:
    """根据名称查找结果推断缺失注解。

    创建者: OpenAI
    最后一次更改: OpenAI

    功能说明:
    - 将 globals/builtins 中的 `Memory`、`SymbolDim` 转为对应参数 AST。

    使用示例:
    - _annotation_from_name_lookup("A", {"A": Memory([4], NumericType.Float32)})

    关联文件:
    - spec: spec/dsl/ast.md
    - test: test/dsl/test_ast_visitor.py
    - 功能实现: kernel_gen/dsl/ast.py
    """

    value = namespace.get(arg_name)
    if isinstance(value, Memory):
        return TensorAST(name=arg_name, memory=value, location=None)
    if isinstance(value, SymbolDim):
        return ScalarArgAST(name=arg_name, value_type=int, is_symbolic=True, location=None)
    return None


def _annotation_from_text(
    text: str,
    arg_name: str | None,
    node: object | None,
) -> TensorAST | ScalarArgAST:
    """根据归一化注解文本构造参数 AST。

    创建者: OpenAI
    最后一次更改: OpenAI

    功能说明:
    - 支持 `int`、`bool`、`Tensor[...]` 与返回位 `float` 四类公开注解文本。
    - `float` 当前只允许用于返回注解，不扩展到输入参数注解。

    使用示例:
    - _annotation_from_text("Tensor[f32, 4]", "A", node)

    关联文件:
    - spec: spec/dsl/ast.md
    - test: test/dsl/test_ast_visitor.py
    - 功能实现: kernel_gen/dsl/ast.py
    """

    location = _location_from_node(node)
    if text.strip() == "int":
        return ScalarArgAST(name=arg_name or "ret0", value_type=int, location=location)
    if text.strip() == "bool":
        return ScalarArgAST(name=arg_name or "ret0", value_type=bool, location=location)
    if text.strip() == "float" and arg_name is None:
        return ScalarArgAST(name="ret0", value_type=float, location=location)
    dtype, dims = _split_tensor_annotation(text, node)
    memory = Memory(dims, dtype)
    return TensorAST(name=arg_name or "ret0", memory=memory, location=location)


def _tensor_annotation_text_from_subscript(node: py_ast.Subscript) -> str:
    """将 `Tensor[...]` 下标注解节点还原为文本。

    创建者: OpenAI
    最后一次更改: OpenAI

    功能说明:
    - 仅接受 `Name` 与 `Constant` 组成的张量注解元素。

    使用示例:
    - _tensor_annotation_text_from_subscript(py_ast.parse(\"Tensor[f32, M]\", mode=\"eval\").body)

    关联文件:
    - spec: spec/dsl/ast.md
    - test: test/dsl/test_ast_visitor.py
    - 功能实现: kernel_gen/dsl/ast.py
    """

    slice_node = node.slice
    elements = slice_node.elts if isinstance(slice_node, py_ast.Tuple) else [slice_node]
    items: list[str] = []
    for element in elements:
        if isinstance(element, py_ast.Name):
            items.append(element.id)
            continue
        if isinstance(element, py_ast.Constant):
            items.append(str(element.value))
            continue
        _raise_parse_error("Unsupported tensor annotation element", element)
    return "Tensor[" + ", ".join(items) + "]"


def _flatten_pep604_union_nodes(node: object) -> list[object]:
    """展开 PEP 604 联合注解节点。

    创建者: jcc你莫辜负
    最后一次更改: jcc你莫辜负

    功能说明:
    - 将 `int | SymbolDim` 这类 BitOr 链式注解扁平化为原子节点列表。

    使用示例:
    - _flatten_pep604_union_nodes(py_ast.parse("int | SymbolDim", mode="eval").body)

    关联文件:
    - spec: spec/dsl/ast.md
    - test: test/dsl/test_ast_visitor.py
    - 功能实现: kernel_gen/dsl/ast.py
    """

    if isinstance(node, py_ast.BinOp) and isinstance(node.op, py_ast.BitOr):
        return _flatten_pep604_union_nodes(node.left) + _flatten_pep604_union_nodes(node.right)
    return [node]


def _parse_annotation_node(
    node: object | None,
    arg_name: str | None,
    globals_table: dict[str, object],
    builtins_table: dict[str, object],
    runtime_table: dict[str, object] | None = None,
) -> TensorAST | ScalarArgAST | PtrArgAST | None:
    """解析单个注解节点为输入/输出 AST。

    创建者: 金铲铲大作战
    最后一次更改: 金铲铲大作战

    功能说明:
    - 支持 `int/bool/SymbolDim`、返回位 `float`、`Tensor[...]` 与 `Ptr(dtype)` 注解解析。
    - 对 `Ptr()` / `Ptr(f32, f32)` 等非法参数数量给出固定诊断。

    使用示例:
    - _parse_annotation_node(py_ast.parse("Ptr(f32)", mode="eval").body, "data", globals(), __builtins__)

    关联文件:
    - spec: spec/dsl/ast.md
    - test: test/dsl/test_ast.py
    - 功能实现: kernel_gen/dsl/ast.py
    """
    if node is None:
        if runtime_table is not None and arg_name is not None and arg_name in runtime_table:
            inferred = _annotation_from_runtime_value(arg_name, runtime_table[arg_name])
            if inferred is not None:
                return inferred
        if arg_name is None:
            return None
        inferred = _annotation_from_name_lookup(arg_name, globals_table)
        if inferred is not None:
            return inferred
        inferred = _annotation_from_name_lookup(arg_name, builtins_table)
        if inferred is not None:
            return inferred
        _raise_parse_error("Missing annotation", node)

    if isinstance(node, py_ast.Constant) and node.value is None:
        if arg_name is None:
            return None
        _raise_parse_error("Unsupported annotation", node)

    if isinstance(node, (py_ast.Constant, py_ast.JoinedStr)):
        text = _normalize_annotation_text(node, globals_table, builtins_table, runtime_table)
        return _annotation_from_text(text, arg_name, node)

    if isinstance(node, py_ast.BinOp) and isinstance(node.op, py_ast.BitOr):
        union_nodes = _flatten_pep604_union_nodes(node)
        union_name_set: set[str] = set()
        for union_node in union_nodes:
            if not isinstance(union_node, py_ast.Name):
                _raise_parse_error("Unsupported annotation", union_node)
            union_name_set.add(union_node.id)
        if union_name_set == {"int", "SymbolDim"}:
            return ScalarArgAST(
                name=arg_name or "ret0",
                value_type=int,
                is_symbolic=True,
                location=_location_from_node(node),
            )
        _raise_parse_error("Unsupported annotation", node)

    if isinstance(node, py_ast.Name):
        if node.id == "int":
            return ScalarArgAST(name=arg_name or "ret0", value_type=int, location=_location_from_node(node))
        if node.id == "bool":
            return ScalarArgAST(name=arg_name or "ret0", value_type=bool, location=_location_from_node(node))
        if node.id == "float" and arg_name is None:
            return ScalarArgAST(name="ret0", value_type=float, location=_location_from_node(node))
        if node.id == "SymbolDim":
            return ScalarArgAST(
                name=arg_name or "ret0",
                value_type=int,
                is_symbolic=True,
                location=_location_from_node(node),
            )
        if node.id in globals_table and isinstance(globals_table[node.id], Memory):
            memory = globals_table[node.id]
            return TensorAST(name=arg_name or node.id, memory=memory, location=_location_from_node(node))
        _raise_parse_error("Unsupported annotation", node)

    if isinstance(node, py_ast.Subscript) and isinstance(node.value, py_ast.Name) and node.value.id == "Tensor":
        return _annotation_from_text(_tensor_annotation_text_from_subscript(node), arg_name, node)

    _raise_parse_error("Unsupported annotation", node)
    return None


def _lookup_python_name(name: str, globals_table: dict[str, object], builtins_table: dict[str, object]) -> object | None:
    """从解析上下文查找 Python 名称。

    创建者: OpenAI
    最后一次更改: OpenAI

    功能说明:
    - 依次在 globals 与 builtins 中查找给定名称。

    使用示例:
    - _lookup_python_name("MemorySpace", globals(), __builtins__)

    关联文件:
    - spec: spec/dsl/ast.md
    - test: test/dsl/test_ast_visitor.py
    - 功能实现: kernel_gen/dsl/ast.py
    """

    if name in globals_table:
        return globals_table[name]
    if name in builtins_table:
        return builtins_table[name]
    return None


def _parse_attribute_object(
    expr: py_ast.Attribute,
    globals_table: dict[str, object],
    builtins_table: dict[str, object],
) -> object:
    """解析属性形式的静态对象引用。

    创建者: OpenAI
    最后一次更改: OpenAI

    功能说明:
    - 支持 `MemorySpace.LM` 这类属性访问。

    使用示例:
    - _parse_attribute_object(py_ast.parse("MemorySpace.LM").body[0].value, globals(), __builtins__)

    关联文件:
    - spec: spec/dsl/ast.md
    - test: test/dsl/test_ast_visitor.py
    - 功能实现: kernel_gen/dsl/ast.py
    """

    if isinstance(expr.value, py_ast.Name):
        base = _lookup_python_name(expr.value.id, globals_table, builtins_table)
        if base is None:
            _raise_parse_error("Unknown name", expr.value)
    elif isinstance(expr.value, py_ast.Attribute):
        base = _parse_attribute_object(expr.value, globals_table, builtins_table)
    else:
        _raise_parse_error("Unsupported attribute expression", expr)
    if not hasattr(base, expr.attr):
        _raise_parse_error("Unknown attribute", expr)
    return getattr(base, expr.attr)


def _is_allowed_attribute_value(value: object) -> bool:
    """判断属性表达式是否属于 DSL 允许的静态值。

    创建者: 我不是牛马
    最后一次更改: 我不是牛马

    功能说明:
    - 仅允许 `MemorySpace.*`、`BarrierScope.*` 与 `NumericType.*` 这类 DSL 静态属性值参与函数体解析。
    - 拒绝将其他 Attribute 形式的外部值当作局部常量或隐式输入继续 lowering。

    使用示例:
    - _is_allowed_attribute_value(MemorySpace.LM)

    关联文件:
    - spec: spec/dsl/mlir_gen.md
    - test: test/dsl/test_ast_visitor.py
    - 功能实现: kernel_gen/dsl/ast.py
    """

    return isinstance(value, (MemorySpace, NumericType, _KG_OPERATION_ARCH.BarrierScope))


def _is_memory_target_ast(node: object) -> bool:
    """判断 store/deslice 的 target 是否属于可写 memory AST。

    创建者: 朽木露琪亚
    最后一次更改: 小李飞刀

    功能说明:
    - 接受函数入参张量与会产生 memory 结果的前端 AST 节点。
    - 允许 `alloc/view/reshape/flatten/cast/copy` 等结果继续作为 `store/deslice` target。
    - 继续拒绝纯标量或其他非 memory AST，保持 target 入口的解析边界。

    使用示例:
    - _is_memory_target_ast(TensorAST(name="out", memory=memory))

    关联文件:
    - spec: spec/dsl/ast.md
    - test: test/dsl/test_ast_visitor.py
    - 功能实现: kernel_gen/dsl/ast.py
    """

    return isinstance(
        node,
        (
            TensorAST,
            DmaAllocAST,
            DmaCopyAST,
            DmaCastAST,
            DmaViewAST,
            DmaReshapeAST,
            DmaFlattenAST,
            Img2ColAST,
            NnBroadcastAST,
            NnBroadcastToAST,
            NnSoftmaxAST,
            MatmulAST,
            ArchGetDynamicMemoryAST,
        ),
    )


def _resolve_call_base_object(
    expr: py_ast.expr,
    globals_table: dict[str, object],
    builtins_table: dict[str, object],
) -> object:
    """解析 helper 调用的基对象。

    创建者: OpenAI
    最后一次更改: OpenAI

    功能说明:
    - 支持 `Name` 与嵌套 `Attribute` 两种基对象表达式。

    使用示例:
    - _resolve_call_base_object(py_ast.parse(\"dma.load\", mode=\"eval\").body.value, globals(), __builtins__)

    关联文件:
    - spec: spec/dsl/ast.md
    - test: test/dsl/test_ast_visitor.py
    - 功能实现: kernel_gen/dsl/ast.py
    """

    if isinstance(expr, py_ast.Name):
        return _lookup_python_name(expr.id, globals_table, builtins_table)
    if isinstance(expr, py_ast.Attribute):
        return _parse_attribute_object(expr, globals_table, builtins_table)
    _raise_parse_error("Unsupported call expression", expr)
    return None


def _resolve_import_bound_helper_call(
    expr: py_ast.expr,
    globals_table: dict[str, object],
    builtins_table: dict[str, object],
) -> str | None:
    """按 import 绑定关系解析 DSL helper 调用名。

    创建者: 金铲铲大作战
    最后一次更改: 小李飞刀

    功能说明:
    - 仅当调用目标显式绑定到 `kernel_gen.operation.dma`、`kernel_gen.operation.arch` 或 `kernel_gen.operation.nn` 时，才返回 helper 名。
    - 支持 module alias/package alias 的 `mod.helper(...)` 调用，以及 direct symbol alias 的 `alias(...)` 调用。
    - 拒绝未导入的裸 helper 名与来自其他模块的同名对象，避免误把普通名字当作 DSL helper。
    - 仅允许 `alias.helper(...)` 形式的 module 调用；拒绝 `kernel_gen.operation.dma.slice(...)` 这类链式属性访问绕过 import 绑定。
    - direct symbol alias 必须与真实模块导出的 helper 对象一致，拒绝伪造 `__module__`/`__name__` 的同名 callable。

    使用示例:
    - _resolve_import_bound_helper_call(py_ast.parse("cc.slice", mode="eval").body, globals(), __builtins__)

    关联文件:
    - spec: spec/dsl/ast.md
    - test: test/dsl/test_ast.py
    - 功能实现: kernel_gen/dsl/ast.py
    """

    if isinstance(expr, py_ast.Attribute):
        if not isinstance(expr.value, py_ast.Name):
            return None
        base_object = _lookup_python_name(expr.value.id, globals_table, builtins_table)
        if not isinstance(base_object, types.ModuleType):
            return None
        module_name = base_object.__name__
        helper_name = expr.attr
        module_info = _ALLOWED_IMPORT_BOUND_HELPERS.get(module_name)
        if module_info is None:
            return None
        if base_object is not module_info[0]:
            return None
    elif isinstance(expr, py_ast.Name):
        helper_object = _lookup_python_name(expr.id, globals_table, builtins_table)
        module_name = getattr(helper_object, "__module__", None)
        helper_name = getattr(helper_object, "__name__", None)
    else:
        return None

    module_info = _ALLOWED_IMPORT_BOUND_HELPERS.get(module_name)
    if module_info is None:
        return None
    if not isinstance(helper_name, str):
        return None
    if helper_name not in module_info[1]:
        return None
    if isinstance(expr, py_ast.Name) and getattr(module_info[0], helper_name, None) is not helper_object:
        return None
    return helper_name


def _bind_safe_local_import(stmt: py_ast.Import | py_ast.ImportFrom, globals_table: dict[str, object]) -> None:
    """按白名单绑定函数体内 import，避免解析阶段触发任意模块导入。

    创建者: 小李飞刀
    最后一次更改: 小李飞刀

    功能说明:
    - 仅对白名单中的 `kernel_gen.operation.{dma,arch,nn}` 建立安全绑定。
    - `import mod as alias` 仅在 `alias` 存在时绑定到白名单模块对象。
    - `from mod import helper` 仅在 helper 位于白名单时绑定到真实 helper 对象。
    - 其他导入一律绑定为本地遮蔽哨兵，防止回退命中全局同名对象，也不触发动态导入副作用。

    使用示例:
    - _bind_safe_local_import(py_ast.parse("from kernel_gen.operation.dma import load").body[0], globals())

    关联文件:
    - spec: spec/dsl/ast.md
    - test: test/dsl/test_ast.py
    - 功能实现: kernel_gen/dsl/ast.py
    """

    if isinstance(stmt, py_ast.Import):
        for alias in stmt.names:
            binding_name = alias.asname or alias.name.split(".", 1)[0]
            module_info = _ALLOWED_IMPORT_BOUND_HELPERS.get(alias.name)
            if alias.asname and module_info is not None:
                globals_table[binding_name] = module_info[0]
                continue
            globals_table[binding_name] = _LOCAL_IMPORT_SHADOW
        return

    module_info = _ALLOWED_IMPORT_BOUND_HELPERS.get(stmt.module or "")
    for alias in stmt.names:
        if alias.name == "*":
            continue
        binding_name = alias.asname or alias.name
        if module_info is not None and alias.name in module_info[1]:
            globals_table[binding_name] = getattr(module_info[0], alias.name)
            continue
        globals_table[binding_name] = _LOCAL_IMPORT_SHADOW


def _parse_symbol_to_float_call(
    expr: py_ast.Call,
    env: dict[str, object],
    globals_table: dict[str, object],
    builtins_table: dict[str, object],
) -> SymbolToFloatAST | None:
    """解析 `float(symbol.int)` 的最小 AST 入口。

    创建者: 金铲铲大作战
    最后一次更改: 金铲铲大作战

    功能说明:
    - 仅识别 builtin `float(...)` 的单参数调用。
    - 将参数表达式保留为 AST，具体 `symbol.int -> f32` 约束交由 lowering 阶段校验。

    使用示例:
    - _parse_symbol_to_float_call(expr, env, globals(), __builtins__)

    关联文件:
    - spec: spec/dsl/ast.md
    - test: test/dsl/test_ast.py
    - 功能实现: kernel_gen/dsl/ast.py
    """

    if not isinstance(expr.func, py_ast.Name) or expr.func.id != "float":
        return None
    if _lookup_python_name("float", globals_table, builtins_table) is not float:
        return None
    if len(expr.args) != 1 or expr.keywords:
        _raise_parse_error("Unsupported float arity", expr)
    source = _parse_expr(expr.args[0], env, globals_table, builtins_table)
    return SymbolToFloatAST(source=source, location=_location_from_node(expr))


def _parse_nn_arithmetic_call(
    expr: py_ast.Call,
    env: dict[str, object],
    globals_table: dict[str, object],
    builtins_table: dict[str, object],
) -> BinaryExprAST | None:
    """解析 `nn.*` 形式的二元算术 helper。

    创建者: OpenAI
    最后一次更改: OpenAI

    功能说明:
    - 将 `nn.add/sub/mul/truediv/floordiv` 统一映射为 `BinaryExprAST`。

    使用示例:
    - _parse_nn_arithmetic_call(expr, env, globals(), __builtins__)

    关联文件:
    - spec: spec/dsl/ast.md
    - test: test/dsl/test_ast_visitor.py
    - 功能实现: kernel_gen/dsl/ast.py
    """

    if not isinstance(expr.func, py_ast.Attribute):
        return None
    base_object = _resolve_call_base_object(expr.func.value, globals_table, builtins_table)
    symbol_binary_map = {
        "add": "add",
        "sub": "sub",
        "mul": "mul",
        "truediv": "div",
        "floordiv": "floordiv",
    }
    if getattr(base_object, "__name__", None) != "kernel_gen.operation.nn" or expr.func.attr not in symbol_binary_map:
        return None
    if len(expr.args) != 2 or expr.keywords:
        _raise_parse_error("Unsupported nn arithmetic arity", expr)
    lhs = _parse_expr(expr.args[0], env, globals_table, builtins_table)
    rhs = _parse_expr(expr.args[1], env, globals_table, builtins_table)
    return BinaryExprAST(
        op=symbol_binary_map[expr.func.attr],
        lhs=lhs,
        rhs=rhs,
        location=_location_from_node(expr),
    )


def _parse_unary_helper_call(
    call_name: str,
    expr: py_ast.Call,
    env: dict[str, object],
    globals_table: dict[str, object],
    builtins_table: dict[str, object],
) -> NnUnaryAST:
    """解析 nn unary helper 调用。

    创建者: jcc你莫辜负
    最后一次更改: jcc你莫辜负

    功能说明:
    - 解析 relu/sigmoid/tanh/leaky_relu/hard_sigmoid/exp 的调用参数。
    - 严格约束 arity，缺参或多参统一抛出 `Unsupported <name> arity`。

    使用示例:
    - _parse_unary_helper_call("relu", expr, env, globals(), __builtins__)

    关联文件:
    - spec: spec/dsl/ast.md
    - test: test/dsl/test_ast.py
    - 功能实现: kernel_gen/dsl/ast.py
    """

    simple_unary = {"relu", "sigmoid", "tanh", "exp"}
    if call_name in simple_unary:
        if len(expr.args) != 1 or expr.keywords:
            _raise_parse_error(f"Unsupported {call_name} arity", expr)
        value = _parse_expr(expr.args[0], env, globals_table, builtins_table)
        return NnUnaryAST(kind=call_name, value=value, location=_location_from_node(expr))

    if call_name == "leaky_relu":
        if len(expr.args) < 1 or len(expr.args) > 2:
            _raise_parse_error("Unsupported leaky_relu arity", expr)
        if len(expr.keywords) > 1:
            _raise_parse_error("Unsupported leaky_relu arity", expr)
        value = _parse_expr(expr.args[0], env, globals_table, builtins_table)
        alpha = _parse_expr(expr.args[1], env, globals_table, builtins_table) if len(expr.args) == 2 else None
        seen_alpha = alpha is not None
        for keyword in expr.keywords:
            if keyword.arg is None or keyword.arg != "alpha" or seen_alpha:
                _raise_parse_error("Unsupported leaky_relu arity", expr)
            alpha = _parse_expr(keyword.value, env, globals_table, builtins_table)
            seen_alpha = True
        if alpha is None:
            _raise_parse_error("Unsupported leaky_relu arity", expr)
        return NnUnaryAST(kind=call_name, value=value, alpha=alpha, location=_location_from_node(expr))

    if call_name == "hard_sigmoid":
        if len(expr.args) < 1 or len(expr.args) > 3:
            _raise_parse_error("Unsupported hard_sigmoid arity", expr)
        if len(expr.keywords) > 2:
            _raise_parse_error("Unsupported hard_sigmoid arity", expr)
        value = _parse_expr(expr.args[0], env, globals_table, builtins_table)
        alpha = _parse_expr(expr.args[1], env, globals_table, builtins_table) if len(expr.args) >= 2 else None
        beta = _parse_expr(expr.args[2], env, globals_table, builtins_table) if len(expr.args) == 3 else None
        seen_alpha = alpha is not None
        seen_beta = beta is not None
        for keyword in expr.keywords:
            if keyword.arg is None:
                _raise_parse_error("Unsupported hard_sigmoid arity", expr)
            if keyword.arg == "alpha":
                if seen_alpha:
                    _raise_parse_error("Unsupported hard_sigmoid arity", expr)
                alpha = _parse_expr(keyword.value, env, globals_table, builtins_table)
                seen_alpha = True
                continue
            if keyword.arg == "beta":
                if seen_beta:
                    _raise_parse_error("Unsupported hard_sigmoid arity", expr)
                beta = _parse_expr(keyword.value, env, globals_table, builtins_table)
                seen_beta = True
                continue
            _raise_parse_error("Unsupported hard_sigmoid arity", expr)
        if alpha is None or beta is None:
            _raise_parse_error("Unsupported hard_sigmoid arity", expr)
        return NnUnaryAST(kind=call_name, value=value, alpha=alpha, beta=beta, location=_location_from_node(expr))

    _raise_parse_error("Unsupported call expression", expr)
    return None


def _parse_softmax_helper_call(
    expr: py_ast.Call,
    env: dict[str, object],
    globals_table: dict[str, object],
    builtins_table: dict[str, object],
) -> NnSoftmaxAST:
    """解析 nn softmax helper 调用。

    创建者: 小李飞刀
    最后一次更改: 小李飞刀

    功能说明:
    - 解析 softmax 的 value/axis 参数。
    - 允许 axis 作为位置参数或关键字参数。

    使用示例:
    - _parse_softmax_helper_call(expr, env, globals(), __builtins__)

    关联文件:
    - spec: spec/dsl/ast.md
    - test: test/dsl/test_ast.py
    - 功能实现: kernel_gen/dsl/ast.py
    """

    if len(expr.args) < 1 or len(expr.args) > 2:
        _raise_parse_error("Unsupported softmax arity", expr)
    if len(expr.keywords) > 1:
        _raise_parse_error("Unsupported softmax arity", expr)
    value = _parse_expr(expr.args[0], env, globals_table, builtins_table)
    axis: object | None = None
    seen_axis = False
    if len(expr.args) == 2:
        axis = _parse_expr(expr.args[1], env, globals_table, builtins_table)
        seen_axis = True
    for keyword in expr.keywords:
        if keyword.arg is None or keyword.arg != "axis" or seen_axis:
            _raise_parse_error("Unsupported softmax arity", expr)
        axis = _parse_expr(keyword.value, env, globals_table, builtins_table)
        seen_axis = True
    return NnSoftmaxAST(value=value, axis=axis, location=_location_from_node(expr))


def _parse_reduce_helper_call(
    call_name: str,
    expr: py_ast.Call,
    env: dict[str, object],
    globals_table: dict[str, object],
    builtins_table: dict[str, object],
) -> NnReduceAST:
    """解析 nn reduce helper 调用。

    创建者: jcc你莫辜负
    最后一次更改: jcc你莫辜负

    功能说明:
    - 解析 reduce_sum/reduce_min/reduce_max 的 value/axis/keepdim 参数。
    - 严格约束 arity 与 keyword 名称，避免静默忽略非法参数。

    使用示例:
    - _parse_reduce_helper_call("reduce_sum", expr, env, globals(), __builtins__)

    关联文件:
    - spec: spec/dsl/ast.md
    - test: test/dsl/test_ast.py
    - 功能实现: kernel_gen/dsl/ast.py
    """

    if len(expr.args) < 1 or len(expr.args) > 3:
        _raise_parse_error(f"Unsupported {call_name} arity", expr)
    if len(expr.keywords) > 2:
        _raise_parse_error(f"Unsupported {call_name} arity", expr)

    value = _parse_expr(expr.args[0], env, globals_table, builtins_table)
    axis: object | None = None
    keepdim: object | None = None
    seen_axis = False
    seen_keepdim = False

    if len(expr.args) >= 2:
        axis = _parse_expr(expr.args[1], env, globals_table, builtins_table)
        seen_axis = True
    if len(expr.args) == 3:
        keepdim = _parse_expr(expr.args[2], env, globals_table, builtins_table)
        seen_keepdim = True

    for keyword in expr.keywords:
        if keyword.arg is None:
            _raise_parse_error(f"Unsupported {call_name} arity", expr)
        if keyword.arg == "axis":
            if seen_axis:
                _raise_parse_error(f"Unsupported {call_name} arity", expr)
            axis = _parse_expr(keyword.value, env, globals_table, builtins_table)
            seen_axis = True
            continue
        if keyword.arg == "keepdim":
            if seen_keepdim:
                _raise_parse_error(f"Unsupported {call_name} arity", expr)
            keepdim = _parse_expr(keyword.value, env, globals_table, builtins_table)
            seen_keepdim = True
            continue
        _raise_parse_error(f"Unsupported {call_name} arity", expr)

    return NnReduceAST(
        kind=call_name,
        value=value,
        axis=axis,
        keepdim=keepdim,
        location=_location_from_node(expr),
    )


def _parse_load_like_call(
    expr: py_ast.Call,
    call_name: str,
    env: dict[str, object],
    globals_table: dict[str, object],
    builtins_table: dict[str, object],
) -> LoadAST:
    """解析 `load/slice` 这类读取 helper。

    创建者: OpenAI
    最后一次更改: OpenAI

    功能说明:
    - 统一处理 `load` 与 `slice` 的参数解析和类型校验。

    使用示例:
    - _parse_load_like_call(expr, \"load\", env, globals(), __builtins__)

    关联文件:
    - spec: spec/dsl/ast.md
    - test: test/dsl/test_ast_visitor.py
    - 功能实现: kernel_gen/dsl/ast.py
    """

    if len(expr.args) < 3 or len(expr.args) > 5:
        _raise_parse_error(f"Unsupported {call_name} arity", expr)
    tensor = _parse_expr(expr.args[0], env, globals_table, builtins_table)
    if not isinstance(tensor, TensorAST):
        _raise_parse_error(f"{call_name} source must be TensorAST", expr.args[0])
    index_env = dict(env)
    if bool(index_env.get(_REJECT_EXTERNAL_VALUES_ENV_KEY, False)):
        index_env[_ALLOW_EXTERNAL_CONSTANTS_ENV_KEY] = True
    offsets = _parse_expr(expr.args[1], index_env, globals_table, builtins_table)
    sizes = _parse_expr(expr.args[2], index_env, globals_table, builtins_table)
    stride = _parse_expr(expr.args[3], index_env, globals_table, builtins_table) if len(expr.args) >= 4 else None
    space = _parse_expr(expr.args[4], env, globals_table, builtins_table) if len(expr.args) >= 5 else None
    if space is not None and not isinstance(space, MemorySpace):
        _raise_parse_error(f"{call_name} space must be MemorySpace", expr.args[4])
    return LoadAST(
        tensor=tensor,
        offset=offsets,
        sizes=sizes,
        stride=stride,
        space=space,
        kind=call_name,
        location=_location_from_node(expr),
    )


def _parse_store_like_call(
    expr: py_ast.Call,
    call_name: str,
    env: dict[str, object],
    globals_table: dict[str, object],
    builtins_table: dict[str, object],
) -> StoreAST:
    """解析 `store/deslice` 这类写回 helper。

    创建者: OpenAI
    最后一次更改: OpenAI

    功能说明:
    - 统一处理 `store` 与 `deslice` 的参数解析和类型校验。

    使用示例:
    - _parse_store_like_call(expr, \"store\", env, globals(), __builtins__)

    关联文件:
    - spec: spec/dsl/ast.md
    - test: test/dsl/test_ast_visitor.py
    - 功能实现: kernel_gen/dsl/ast.py
    """

    min_arity = 4
    max_arity = 5 if call_name == "store" else 6
    if len(expr.args) < min_arity or len(expr.args) > max_arity:
        _raise_parse_error(f"Unsupported {call_name} arity", expr)
    value = _parse_expr(expr.args[0], env, globals_table, builtins_table)
    tensor = _parse_expr(expr.args[1], env, globals_table, builtins_table)
    if not _is_memory_target_ast(tensor):
        _raise_parse_error(f"{call_name} target must be TensorAST", expr.args[1])
    index_env = dict(env)
    if bool(index_env.get(_REJECT_EXTERNAL_VALUES_ENV_KEY, False)):
        index_env[_ALLOW_EXTERNAL_CONSTANTS_ENV_KEY] = True
    offsets = _parse_expr(expr.args[2], index_env, globals_table, builtins_table)
    sizes = _parse_expr(expr.args[3], index_env, globals_table, builtins_table)
    stride = _parse_expr(expr.args[4], index_env, globals_table, builtins_table) if len(expr.args) >= 5 else None
    if call_name == "deslice" and len(expr.args) == 6:
        extra_space = _parse_expr(expr.args[5], env, globals_table, builtins_table)
        if not isinstance(extra_space, MemorySpace):
            _raise_parse_error("deslice space must be MemorySpace", expr.args[5])
    return StoreAST(
        tensor=tensor,
        offset=offsets,
        sizes=sizes,
        stride=stride,
        value=value,
        kind=call_name,
        location=_location_from_node(expr),
    )


def _parse_dma_call(
    expr: py_ast.Call,
    env: dict[str, object],
    globals_table: dict[str, object],
    builtins_table: dict[str, object],
) -> object:
    """解析 DSL 中的 DMA/NN helper 调用。

    创建者: OpenAI
    最后一次更改: 小李飞刀

    功能说明:
    - 仅接受当前函数显式导入绑定到 `kernel_gen.operation.dma/arch/nn` 的 helper 调用。
    - 将 `load/slice/store/deslice/...` 解析为对应 AST 节点。
    - 将 `nn.add/sub/mul/truediv/floordiv(...)` 解析为对应的 `BinaryExprAST`。
    - 将 `relu/sigmoid/tanh/leaky_relu/hard_sigmoid/exp(...)` 解析为 `NnUnaryAST`。
    - 将 `reduce_sum/reduce_min/reduce_max(...)` 解析为 `NnReduceAST`。
    - 将 `softmax(...)` 解析为 `NnSoftmaxAST`。
    - 将 `img2col1d/img2col2d(...)` 解析为对应的 `Img2ColAST`。
    - 将 `broadcast/broadcast_to(...)` 解析为对应的 `NnBroadcastAST/NnBroadcastToAST`。
    - 将 `get_block_id()` / `get_block_num()` / `get_subthread_id()` / `get_subthread_num()` / `get_thread_id()` / `get_thread_num()` 解析为 `ArchQueryAST`。
    - 将 `get_dynamic_memory(space)` 解析为 `ArchGetDynamicMemoryAST`。
    - 将 `barrier(visibility=[...], scope=BarrierScope.BLOCK)` 解析为 `ArchBarrierAST`。
    - 将 `launch_kernel(callee, block, thread, subthread, *args)` 解析为 `ArchLaunchKernelAST`。

    使用示例:
    - _parse_dma_call(py_ast.parse("slice(A, [i], [n])").body[0].value, env, globals(), __builtins__)

    关联文件:
    - spec: spec/dsl/ast.md
    - test: test/dsl/test_ast_visitor.py
    - 功能实现: kernel_gen/dsl/ast.py
    """

    if isinstance(expr.func, py_ast.Attribute):
        nn_expr = _parse_nn_arithmetic_call(expr, env, globals_table, builtins_table)
        if nn_expr is not None:
            return nn_expr
    call_name = _resolve_import_bound_helper_call(expr.func, globals_table, builtins_table)
    if call_name is None:
        _raise_parse_error("Unsupported call expression", expr)

    if call_name == "load":
        return _parse_load_like_call(expr, call_name, env, globals_table, builtins_table)

    if call_name == "slice":
        return _parse_load_like_call(expr, call_name, env, globals_table, builtins_table)

    if call_name == "store":
        return _parse_store_like_call(expr, call_name, env, globals_table, builtins_table)

    if call_name == "deslice":
        return _parse_store_like_call(expr, call_name, env, globals_table, builtins_table)

    if call_name == "alloc":
        if len(expr.args) < 2 or len(expr.args) > 4:
            _raise_parse_error("Unsupported alloc arity", expr)
        if len(expr.keywords) > 2:
            _raise_parse_error("Unsupported alloc arity", expr)
        shape = _parse_expr(expr.args[0], env, globals_table, builtins_table)
        dtype = _parse_expr(expr.args[1], env, globals_table, builtins_table)
        if not isinstance(dtype, NumericType):
            _raise_parse_error("alloc dtype must be NumericType", expr.args[1])
        space = _parse_expr(expr.args[2], env, globals_table, builtins_table) if len(expr.args) >= 3 else MemorySpace.GM
        stride = _parse_expr(expr.args[3], env, globals_table, builtins_table) if len(expr.args) >= 4 else None
        seen_space = len(expr.args) >= 3
        seen_stride = len(expr.args) >= 4
        for keyword in expr.keywords:
            if keyword.arg is None:
                _raise_parse_error("Unsupported alloc arity", expr)
            if keyword.arg == "space":
                if seen_space:
                    _raise_parse_error("Unsupported alloc arity", expr)
                space = _parse_expr(keyword.value, env, globals_table, builtins_table)
                seen_space = True
                continue
            if keyword.arg == "stride":
                if seen_stride:
                    _raise_parse_error("Unsupported alloc arity", expr)
                stride = _parse_expr(keyword.value, env, globals_table, builtins_table)
                seen_stride = True
                continue
            _raise_parse_error("Unsupported alloc arity", expr)
        if not isinstance(space, MemorySpace):
            _raise_parse_error("alloc space must be MemorySpace", expr.args[2] if len(expr.args) >= 3 else expr)
        return DmaAllocAST(shape=shape, dtype=dtype, space=space, stride=stride, location=_location_from_node(expr))

    if call_name == "copy":
        if len(expr.args) != 2 or expr.keywords:
            _raise_parse_error("Unsupported copy arity", expr)
        source = _parse_expr(expr.args[0], env, globals_table, builtins_table)
        space = _parse_expr(expr.args[1], env, globals_table, builtins_table)
        if not isinstance(space, MemorySpace):
            _raise_parse_error("copy space must be MemorySpace", expr.args[1])
        return DmaCopyAST(source=source, space=space, location=_location_from_node(expr))

    if call_name == "cast":
        if len(expr.args) < 2 or len(expr.args) > 3:
            _raise_parse_error("Unsupported cast arity", expr)
        if len(expr.keywords) > 1:
            _raise_parse_error("Unsupported cast arity", expr)
        source = _parse_expr(expr.args[0], env, globals_table, builtins_table)
        dtype = _parse_expr(expr.args[1], env, globals_table, builtins_table)
        if not isinstance(dtype, NumericType):
            _raise_parse_error("cast dtype must be NumericType", expr.args[1])
        memoryspace = _parse_expr(expr.args[2], env, globals_table, builtins_table) if len(expr.args) == 3 else None
        if expr.keywords:
            keyword = expr.keywords[0]
            if keyword.arg != "memoryspace" or len(expr.args) == 3:
                _raise_parse_error("Unsupported cast arity", expr)
            memoryspace = _parse_expr(keyword.value, env, globals_table, builtins_table)
        if memoryspace is not None and not isinstance(memoryspace, MemorySpace):
            location_node = expr.args[2] if len(expr.args) == 3 else expr.keywords[0].value
            _raise_parse_error("cast memoryspace must be MemorySpace", location_node)
        return DmaCastAST(source=source, dtype=dtype, memoryspace=memoryspace, location=_location_from_node(expr))

    if call_name == "view":
        if len(expr.args) != 4 or expr.keywords:
            _raise_parse_error("Unsupported view arity", expr)
        source = _parse_expr(expr.args[0], env, globals_table, builtins_table)
        index_env = dict(env)
        if bool(index_env.get(_REJECT_EXTERNAL_VALUES_ENV_KEY, False)):
            index_env[_ALLOW_EXTERNAL_CONSTANTS_ENV_KEY] = True
        offset = _parse_expr(expr.args[1], index_env, globals_table, builtins_table)
        size = _parse_expr(expr.args[2], index_env, globals_table, builtins_table)
        stride = _parse_expr(expr.args[3], index_env, globals_table, builtins_table)
        return DmaViewAST(
            source=source,
            offset=offset,
            size=size,
            stride=stride,
            location=_location_from_node(expr),
        )

    if call_name == "reshape":
        if len(expr.args) != 2 or expr.keywords:
            _raise_parse_error("Unsupported reshape arity", expr)
        source = _parse_expr(expr.args[0], env, globals_table, builtins_table)
        index_env = dict(env)
        if bool(index_env.get(_REJECT_EXTERNAL_VALUES_ENV_KEY, False)):
            index_env[_ALLOW_EXTERNAL_CONSTANTS_ENV_KEY] = True
        shape = _parse_expr(expr.args[1], index_env, globals_table, builtins_table)
        return DmaReshapeAST(source=source, shape=shape, location=_location_from_node(expr))

    if call_name == "flatten":
        if len(expr.args) != 1 or expr.keywords:
            _raise_parse_error("Unsupported flatten arity", expr)
        source = _parse_expr(expr.args[0], env, globals_table, builtins_table)
        return DmaFlattenAST(source=source, location=_location_from_node(expr))

    if call_name == "free":
        if len(expr.args) != 1 or expr.keywords:
            _raise_parse_error("Unsupported free arity", expr)
        value = _parse_expr(expr.args[0], env, globals_table, builtins_table)
        return DmaFreeAST(value=value, location=_location_from_node(expr))

    if call_name == "img2col":
        _raise_parse_error("Unsupported img2col call", expr)

    if call_name in {"relu", "sigmoid", "tanh", "leaky_relu", "hard_sigmoid", "exp"}:
        return _parse_unary_helper_call(call_name, expr, env, globals_table, builtins_table)

    if call_name in {"reduce_sum", "reduce_min", "reduce_max"}:
        return _parse_reduce_helper_call(call_name, expr, env, globals_table, builtins_table)

    if call_name == "softmax":
        return _parse_softmax_helper_call(expr, env, globals_table, builtins_table)

    if call_name in {"img2col1d", "img2col2d"}:
        if not expr.args:
            _raise_parse_error(f"Unsupported {call_name} arity", expr)
        args = [_parse_expr(arg, env, globals_table, builtins_table) for arg in expr.args]
        kwargs: dict[str, object] = {}
        for keyword in expr.keywords:
            if keyword.arg is None:
                _raise_parse_error(f"Unsupported {call_name} arity", expr)
            kwargs[keyword.arg] = _parse_expr(keyword.value, env, globals_table, builtins_table)
        return Img2ColAST(
            kind=call_name,
            args=args,
            kwargs=kwargs,
            location=_location_from_node(expr),
        )

    if call_name == "broadcast":
        if len(expr.args) != 2 or expr.keywords:
            _raise_parse_error("Unsupported broadcast arity", expr)
        value = _parse_expr(expr.args[0], env, globals_table, builtins_table)
        target = _parse_expr(expr.args[1], env, globals_table, builtins_table)
        return NnBroadcastAST(value=value, target=target, location=_location_from_node(expr))

    if call_name == "broadcast_to":
        if not expr.args or len(expr.args) > 3:
            _raise_parse_error("Unsupported broadcast_to arity", expr)
        source = _parse_expr(expr.args[0], env, globals_table, builtins_table)
        shape_env = dict(env)
        if bool(shape_env.get(_REJECT_EXTERNAL_VALUES_ENV_KEY, False)):
            shape_env[_ALLOW_EXTERNAL_CONSTANTS_ENV_KEY] = True
        target_shape = (
            _parse_expr(expr.args[1], shape_env, globals_table, builtins_table) if len(expr.args) >= 2 else None
        )
        space = _parse_expr(expr.args[2], env, globals_table, builtins_table) if len(expr.args) >= 3 else None
        for keyword in expr.keywords:
            if keyword.arg is None:
                _raise_parse_error("Unsupported broadcast_to arity", expr)
            if keyword.arg == "target_shape":
                if target_shape is not None:
                    _raise_parse_error("Unsupported broadcast_to arity", expr)
                target_shape = _parse_expr(keyword.value, shape_env, globals_table, builtins_table)
                continue
            if keyword.arg == "space":
                if space is not None:
                    _raise_parse_error("Unsupported broadcast_to arity", expr)
                space = _parse_expr(keyword.value, env, globals_table, builtins_table)
                continue
            _raise_parse_error("Unsupported broadcast_to arity", expr)
        if target_shape is None or space is None:
            _raise_parse_error("Unsupported broadcast_to arity", expr)
        return NnBroadcastToAST(
            source=source,
            target_shape=target_shape,
            space=space,
            location=_location_from_node(expr),
        )

    if call_name == "matmul":
        if len(expr.args) < 2 or len(expr.args) > 3:
            _raise_parse_error("Unsupported matmul arity", expr)
        if len(expr.keywords) > 1:
            _raise_parse_error("Unsupported matmul arity", expr)
        lhs = _parse_expr(expr.args[0], env, globals_table, builtins_table)
        rhs = _parse_expr(expr.args[1], env, globals_table, builtins_table)
        memoryspace = (
            _parse_expr(expr.args[2], env, globals_table, builtins_table)
            if len(expr.args) == 3
            else None
        )
        if expr.keywords:
            keyword = expr.keywords[0]
            if keyword.arg != "memoryspace" or len(expr.args) == 3:
                _raise_parse_error("Unsupported matmul arity", expr)
            memoryspace = _parse_expr(keyword.value, env, globals_table, builtins_table)
        if memoryspace is not None and not isinstance(memoryspace, MemorySpace):
            location_node = expr.args[2] if len(expr.args) == 3 else expr.keywords[0].value
            _raise_parse_error("matmul memoryspace must be MemorySpace", location_node)
        return MatmulAST(
            lhs=lhs,
            rhs=rhs,
            memoryspace=memoryspace,
            location=_location_from_node(expr),
        )

    if call_name == "get_block_id":
        if expr.args or expr.keywords:
            _raise_parse_error("Unsupported get_block_id arity", expr)
        return ArchQueryAST(query_name="get_block_id", location=_location_from_node(expr))
    if call_name == "get_block_num":
        if expr.args or expr.keywords:
            _raise_parse_error("Unsupported get_block_num arity", expr)
        return ArchQueryAST(query_name="get_block_num", location=_location_from_node(expr))
    if call_name == "get_subthread_id":
        if expr.args or expr.keywords:
            _raise_parse_error("Unsupported get_subthread_id arity", expr)
        return ArchQueryAST(query_name="get_subthread_id", location=_location_from_node(expr))
    if call_name == "get_subthread_num":
        if expr.args or expr.keywords:
            _raise_parse_error("Unsupported get_subthread_num arity", expr)
        return ArchQueryAST(query_name="get_subthread_num", location=_location_from_node(expr))
    if call_name == "get_thread_id":
        if expr.args or expr.keywords:
            _raise_parse_error("Unsupported get_thread_id arity", expr)
        return ArchQueryAST(query_name="get_thread_id", location=_location_from_node(expr))
    if call_name == "get_thread_num":
        if expr.args or expr.keywords:
            _raise_parse_error("Unsupported get_thread_num arity", expr)
        return ArchQueryAST(query_name="get_thread_num", location=_location_from_node(expr))

    if call_name == "get_dynamic_memory":
        if len(expr.args) != 1 or expr.keywords:
            _raise_parse_error("Unsupported get_dynamic_memory arity", expr)
        space = _parse_expr(expr.args[0], env, globals_table, builtins_table)
        if not isinstance(space, MemorySpace):
            _raise_parse_error("get_dynamic_memory space must be MemorySpace", expr.args[0])
        if space not in {MemorySpace.SM, MemorySpace.LM, MemorySpace.TSM, MemorySpace.TLM}:
            _raise_parse_error("get_dynamic_memory space must be on-chip MemorySpace", expr.args[0])
        return ArchGetDynamicMemoryAST(space=space, location=_location_from_node(expr))

    if call_name == "barrier":
        if expr.args or len(expr.keywords) != 2:
            _raise_parse_error("Unsupported barrier arity", expr)
        keyword_values: dict[str, object] = {}
        for keyword in expr.keywords:
            if keyword.arg is None or keyword.arg not in {"visibility", "scope"} or keyword.arg in keyword_values:
                _raise_parse_error("Unsupported barrier arity", expr)
            keyword_values[keyword.arg] = _parse_expr(keyword.value, env, globals_table, builtins_table)
        visibility = keyword_values.get("visibility")
        if not isinstance(visibility, list) or not visibility or not all(
            isinstance(space, MemorySpace) for space in visibility
        ):
            _raise_parse_error(
                "barrier visibility must be non-empty MemorySpace list",
                next(keyword.value for keyword in expr.keywords if keyword.arg == "visibility"),
            )
        scope = keyword_values.get("scope")
        if not isinstance(scope, _KG_OPERATION_ARCH.BarrierScope):
            _raise_parse_error(
                "barrier scope must be BarrierScope",
                next(keyword.value for keyword in expr.keywords if keyword.arg == "scope"),
            )
        return ArchBarrierAST(
            visibility=list(visibility),
            scope=scope,
            location=_location_from_node(expr),
        )

    if call_name == "launch_kernel":
        if len(expr.args) < 4 or expr.keywords:
            _raise_parse_error("Unsupported launch_kernel arity", expr)
        callee_node = expr.args[0]
        if not isinstance(callee_node, py_ast.Name):
            _raise_parse_error("launch_kernel callee must be function symbol reference", callee_node)
        callee_value = env.get(callee_node.id)
        if callee_value is None:
            callee_value = _lookup_python_name(callee_node.id, globals_table, builtins_table)
        if not inspect.isfunction(callee_value):
            _raise_parse_error("launch_kernel callee must be function symbol reference", callee_node)
        kernel_name = getattr(callee_value, "__name__", "")
        if not isinstance(kernel_name, str) or kernel_name == "":
            _raise_parse_error("launch_kernel callee must be function symbol reference", callee_node)

        def _validate_launch_extent(value: object, dim_name: str, node: object) -> None:
            if isinstance(value, ConstAST):
                if not isinstance(value.value, int):
                    _raise_parse_error(f"launch_kernel {dim_name} must be int or SymbolDim", node)
                if value.value <= 0:
                    _raise_parse_error(f"launch_kernel {dim_name} must be > 0", node)
                return
            if isinstance(value, ScalarArgAST):
                if value.value_type is not int:
                    _raise_parse_error(f"launch_kernel {dim_name} must be int or SymbolDim", node)
                return
            if isinstance(value, SymbolDim):
                return
            if isinstance(value, int):
                if value <= 0:
                    _raise_parse_error(f"launch_kernel {dim_name} must be > 0", node)
                return
            _raise_parse_error(f"launch_kernel {dim_name} must be int or SymbolDim", node)

        block = _parse_expr(expr.args[1], env, globals_table, builtins_table)
        thread = _parse_expr(expr.args[2], env, globals_table, builtins_table)
        subthread = _parse_expr(expr.args[3], env, globals_table, builtins_table)
        args = [_parse_expr(arg, env, globals_table, builtins_table) for arg in expr.args[4:]]
        _validate_launch_extent(block, "block", expr.args[1])
        _validate_launch_extent(thread, "thread", expr.args[2])
        _validate_launch_extent(subthread, "subthread", expr.args[3])
        return ArchLaunchKernelAST(
            callee=kernel_name,
            block=block,
            thread=thread,
            subthread=subthread,
            args=args,
            location=_location_from_node(expr),
        )

    _raise_parse_error("Unsupported call expression", expr)
    return expr


def _parse_expr(
    expr: object,
    env: dict[str, object],
    globals_table: dict[str, object],
    builtins_table: dict[str, object],
) -> object:
    """解析 DSL 表达式节点为 AST。

    创建者: 金铲铲大作战
    最后一次更改: 金铲铲大作战

    功能说明:
    - 解析 Name/Constant/List/Tuple/Attribute/Call/Subscript/UnaryOp/BinOp/Compare 等表达式节点。
    - 支持 `img2col1d/img2col2d` helper 与 `get_shape/get_stride` 轴访问入口解析。
    - 支持 `float(symbol.int)` 的最小 AST 入口解析。
    - 当开启外部值拒绝时，限定索引表达式仅可使用允许的常量。

    使用示例:
    - _parse_expr(py_ast.parse("value.get_shape()[0]").body[0].value, env, globals(), __builtins__)

    关联文件:
    - spec: spec/dsl/ast.md
    - test: test/dsl/test_ast.py
    - 功能实现: kernel_gen/dsl/ast.py
    """

    if isinstance(expr, py_ast.Name):
        if expr.id in env:
            return env[expr.id]
        value = _lookup_python_name(expr.id, globals_table, builtins_table)
        if value is not None and bool(env.get(_REJECT_EXTERNAL_VALUES_ENV_KEY, False)):
            allow_constants = bool(env.get(_ALLOW_EXTERNAL_CONSTANTS_ENV_KEY, False))
            if not (allow_constants and isinstance(value, (int, float, str))):
                _raise_parse_error("cannot use external value inside function body", expr)
        if isinstance(value, Memory):
            return TensorAST(name=expr.id, memory=value, location=_location_from_node(expr))
        if isinstance(value, SymbolDim):
            return ScalarArgAST(name=expr.id, value_type=int, is_symbolic=True, location=_location_from_node(expr))
        if isinstance(value, (int, float, str)):
            return ConstAST(value=value, location=_location_from_node(expr))
        if value is not None:
            return value
        _raise_parse_error("Unknown name", expr)

    if isinstance(expr, py_ast.Constant):
        if isinstance(expr.value, (int, float, str)):
            return ConstAST(value=expr.value, location=_location_from_node(expr))
        _raise_parse_error("Unsupported constant type", expr)

    if isinstance(expr, py_ast.List):
        return [_parse_expr(item, env, globals_table, builtins_table) for item in expr.elts]

    if isinstance(expr, py_ast.Tuple):
        return tuple(_parse_expr(item, env, globals_table, builtins_table) for item in expr.elts)

    if isinstance(expr, py_ast.Attribute):
        value = _parse_attribute_object(expr, globals_table, builtins_table)
        if bool(env.get(_REJECT_EXTERNAL_VALUES_ENV_KEY, False)) and not _is_allowed_attribute_value(value):
            _raise_parse_error("cannot use external value inside function body", expr)
        return value

    if isinstance(expr, py_ast.Call):
        symbol_to_float_expr = _parse_symbol_to_float_call(expr, env, globals_table, builtins_table)
        if symbol_to_float_expr is not None:
            return symbol_to_float_expr
        return _parse_dma_call(expr, env, globals_table, builtins_table)

    if isinstance(expr, py_ast.Subscript):
        if isinstance(expr.value, py_ast.Call) and isinstance(expr.value.func, py_ast.Attribute):
            accessor = expr.value.func
            if accessor.attr in {"get_shape", "get_stride"}:
                if expr.value.args or expr.value.keywords:
                    _raise_parse_error(f"Unsupported {accessor.attr} arity", expr.value)
                tensor_expr = _parse_expr(accessor.value, env, globals_table, builtins_table)
                if not isinstance(tensor_expr, TensorAST):
                    _raise_parse_error(f"{accessor.attr} source must be TensorAST", accessor.value)
                axis_env = dict(env)
                if bool(axis_env.get(_REJECT_EXTERNAL_VALUES_ENV_KEY, False)):
                    axis_env[_ALLOW_EXTERNAL_CONSTANTS_ENV_KEY] = True
                axis_expr = _parse_expr(expr.slice, axis_env, globals_table, builtins_table)
                return TensorAxisAccessAST(
                    tensor=tensor_expr,
                    kind="shape" if accessor.attr == "get_shape" else "stride",
                    axis=axis_expr,
                    location=_location_from_node(expr),
                )
        _raise_parse_error("Unsupported expression", expr)

    if isinstance(expr, py_ast.UnaryOp) and isinstance(expr.op, py_ast.USub):
        if isinstance(expr.operand, py_ast.Constant) and isinstance(expr.operand.value, (int, float)):
            return ConstAST(value=-expr.operand.value, location=_location_from_node(expr))
        _raise_parse_error("Unsupported unary expression", expr)

    if isinstance(expr, py_ast.BinOp):
        op_type = type(expr.op)
        if op_type not in _BIN_OP_MAP:
            _raise_parse_error("Unsupported binary op", expr)
        lhs = _parse_expr(expr.left, env, globals_table, builtins_table)
        rhs = _parse_expr(expr.right, env, globals_table, builtins_table)
        return BinaryExprAST(op=_BIN_OP_MAP[op_type], lhs=lhs, rhs=rhs, location=_location_from_node(expr))

    if isinstance(expr, py_ast.Compare):
        if len(expr.ops) != 1 or len(expr.comparators) != 1:
            _raise_parse_error("Unsupported compare expression", expr)
        op_type = type(expr.ops[0])
        if op_type not in _CMP_OP_MAP:
            _raise_parse_error("Unsupported compare op", expr)
        lhs = _parse_expr(expr.left, env, globals_table, builtins_table)
        rhs = _parse_expr(expr.comparators[0], env, globals_table, builtins_table)
        return CompareExprAST(op=_CMP_OP_MAP[op_type], lhs=lhs, rhs=rhs, location=_location_from_node(expr))

    _raise_parse_error("Unsupported expression", expr)
    return expr


def _parse_for(
    stmt: py_ast.For,
    env: dict[str, object],
    globals_table: dict[str, object],
    builtins_table: dict[str, object],
) -> ForAST:
    """解析 for 语句为 ForAST。

    创建者: 金铲铲大作战
    最后一次更改: 金铲铲大作战

    功能说明:
    - 解析 `for i in range/LoopRange/loop(...)` 语句，生成循环变量与起止步长。
    - 禁止循环体内直接 return，并将 body 递归交由 `_parse_stmt` 处理。

    使用示例:
    - _parse_for(py_ast.parse("for i in range(4):\n    x = i").body[0], env, globals(), __builtins__)

    关联文件:
    - spec: spec/dsl/ast.md
    - test: test/dsl/test_ast.py
    - 功能实现: kernel_gen/dsl/ast.py
    """

    if not isinstance(stmt.target, py_ast.Name):
        _raise_parse_error("Unsupported for target", stmt.target)
    if not isinstance(stmt.iter, py_ast.Call) or not isinstance(stmt.iter.func, py_ast.Name):
        _raise_parse_error("Unsupported for iterator", stmt.iter)
    if stmt.iter.func.id not in {"range", "LoopRange", "loop"}:
        _raise_parse_error("Unsupported for iterator", stmt.iter)
    args = stmt.iter.args
    if len(args) == 1:
        start_expr = ConstAST(value=0, location=_location_from_node(stmt))
        end_expr = _parse_expr(args[0], env, globals_table, builtins_table)
        step_expr = ConstAST(value=1, location=_location_from_node(stmt))
    elif len(args) == 2:
        start_expr = _parse_expr(args[0], env, globals_table, builtins_table)
        end_expr = _parse_expr(args[1], env, globals_table, builtins_table)
        step_expr = ConstAST(value=1, location=_location_from_node(stmt))
    elif len(args) == 3:
        start_expr = _parse_expr(args[0], env, globals_table, builtins_table)
        end_expr = _parse_expr(args[1], env, globals_table, builtins_table)
        step_expr = _parse_expr(args[2], env, globals_table, builtins_table)
    else:
        _raise_parse_error("Unsupported range arity", stmt.iter)

    var = VarAST(name=stmt.target.id, location=_location_from_node(stmt.target))
    previous = env.get(var.name)
    env[var.name] = var
    body_statements: list[object] = []
    for body_stmt in stmt.body:
        if isinstance(body_stmt, py_ast.Return):
            _raise_parse_error("Return inside for-loop is unsupported", body_stmt)
        body_statements.append(_parse_stmt(body_stmt, env, globals_table, builtins_table))
    if previous is None:
        env.pop(var.name, None)
    else:
        env[var.name] = previous
    body_location = _location_from_node(stmt.body[0]) if stmt.body else _location_from_node(stmt)
    body = BlockAST(statements=body_statements, location=body_location)
    return ForAST(var=var, start=start_expr, end=end_expr, step=step_expr, body=body, location=_location_from_node(stmt))


def _parse_stmt(
    stmt: py_ast.stmt,
    env: dict[str, object],
    globals_table: dict[str, object],
    builtins_table: dict[str, object],
) -> object:
    """解析 DSL 语句节点为 AST 语句。

    创建者: 金铲铲大作战
    最后一次更改: 金铲铲大作战

    功能说明:
    - 解析 Assign/Return/For/Expr 语句，并委托 `_parse_expr/_parse_for` 处理子节点。
    - 禁止嵌套 FunctionDef、通用 if 语句、`if bias is not None` 分支。

    使用示例:
    - _parse_stmt(py_ast.parse("x = y").body[0], env, globals(), __builtins__)

    关联文件:
    - spec: spec/dsl/ast.md
    - test: test/dsl/test_ast.py
    - 功能实现: kernel_gen/dsl/ast.py
    """

    if isinstance(stmt, py_ast.FunctionDef):
        _raise_parse_error("Nested function definition is not supported", stmt)
    if isinstance(stmt, py_ast.If):
        test = stmt.test
        if (
            isinstance(test, py_ast.Compare)
            and len(test.ops) == 1
            and isinstance(test.ops[0], py_ast.IsNot)
            and len(test.comparators) == 1
            and isinstance(test.left, py_ast.Name)
            and test.left.id == "bias"
            and isinstance(test.comparators[0], py_ast.Constant)
            and test.comparators[0].value is None
        ):
            _raise_parse_error("Unsupported if bias is not None", stmt)
        _raise_parse_error("Unsupported if statement", stmt)
    if isinstance(stmt, py_ast.Assign):
        if len(stmt.targets) != 1 or not isinstance(stmt.targets[0], py_ast.Name):
            _raise_parse_error("Unsupported assignment target", stmt)
        value = _parse_expr(stmt.value, env, globals_table, builtins_table)
        env[stmt.targets[0].id] = value
        return value
    if isinstance(stmt, py_ast.Return):
        if stmt.value is None:
            _raise_parse_error("Return value is required", stmt)
        return _parse_expr(stmt.value, env, globals_table, builtins_table)
    if isinstance(stmt, py_ast.For):
        return _parse_for(stmt, env, globals_table, builtins_table)
    if isinstance(stmt, py_ast.Expr):
        return _parse_expr(stmt.value, env, globals_table, builtins_table)
    _raise_parse_error("Unsupported syntax", stmt)
    return stmt


def _parse_function_impl(
    fn: object,
    globals_table: dict[str, object] | None = None,
    builtins_table: dict[str, object] | None = None,
    runtime_table: dict[str, object] | None = None,
    config: dict[str, object] | None = None,
) -> FunctionAST:
    """解析 Python 函数实现为 FunctionAST。

    创建者: 金铲铲大作战
    最后一次更改: 金铲铲大作战

    功能说明:
    - 从源码中定位唯一顶层 FunctionDef，并解析参数/返回注解为 TensorAST/ScalarArgAST。
    - 解析函数体语句，收集诊断并执行返回语句位置与缺失校验。
    - 可按配置拒绝外部值，确保 AST 合同与禁用项诊断一致。

    使用示例:
    - func_ast = _parse_function_impl(my_kernel)

    关联文件:
    - spec: spec/dsl/ast.md
    - test: test/dsl/test_ast.py
    - 功能实现: kernel_gen/dsl/ast.py
    """

    reject_external_values = bool((config or {}).get("reject_external_values", False))
    if globals_table is None:
        globals_table = getattr(fn, "__globals__", {}) or {}
    globals_table = dict(globals_table)
    if builtins_table is None:
        builtins_table = globals_table.get("__builtins__", {}) if globals_table else {}
        if isinstance(builtins_table, dict):
            builtins_table = builtins_table
        else:
            builtins_table = getattr(builtins_table, "__dict__", {})

    try:
        source = inspect.getsource(fn)
    except OSError as exc:
        raise AstParseError("Unable to get source", [Diagnostic(str(exc), location=None)]) from exc

    source = textwrap.dedent(source)
    module = py_ast.parse(source)
    function_defs = [node for node in module.body if isinstance(node, py_ast.FunctionDef)]
    if len(function_defs) != 1:
        target_node = function_defs[0] if function_defs else module
        _raise_parse_error("Multiple top-level function definitions are not supported", target_node)
    func_def = None
    for node in module.body:
        if isinstance(node, py_ast.FunctionDef) and node.name == getattr(fn, "__name__", ""):
            func_def = node
            break
    if func_def is None:
        raise AstParseError("Function definition not found", [Diagnostic("Function definition not found", None)])

    env: dict[str, object] = {}
    if reject_external_values:
        env[_REJECT_EXTERNAL_VALUES_ENV_KEY] = True
    inputs: list[TensorAST | ScalarArgAST] = []
    for arg in func_def.args.args:
        parsed = _parse_annotation_node(arg.annotation, arg.arg, globals_table, builtins_table, runtime_table)
        if parsed is None:
            _raise_parse_error("Missing annotation", arg)
        if isinstance(parsed, (TensorAST, ScalarArgAST)):
            inputs.append(parsed)
            env[arg.arg] = parsed
        else:
            _raise_parse_error("Unsupported argument annotation", arg)

    outputs: list[TensorAST | ScalarArgAST] = []
    has_return_annotation = func_def.returns is not None
    returns_none = False
    if has_return_annotation:
        parsed = _parse_annotation_node(func_def.returns, None, globals_table, builtins_table, runtime_table)
        if parsed is None:
            returns_none = True
        elif isinstance(parsed, (TensorAST, ScalarArgAST)):
            outputs.append(parsed)
        else:
            _raise_parse_error("Unsupported return annotation", func_def.returns)

    statements: list[object] = []
    parsed_body_statements: list[py_ast.stmt] = []
    has_explicit_return = False
    for stmt in func_def.body:
        if isinstance(stmt, (py_ast.Import, py_ast.ImportFrom)):
            if has_explicit_return:
                raise AstParseError(
                    "Return statement must be last",
                    [Diagnostic("Return statement must be last", _location_from_node(stmt))],
                )
            _bind_safe_local_import(stmt, globals_table)
            continue
        parsed_stmt = _parse_stmt(stmt, env, globals_table, builtins_table)
        statements.append(parsed_stmt)
        parsed_body_statements.append(stmt)
        if isinstance(stmt, py_ast.Return):
            has_explicit_return = True

    if has_return_annotation and not has_explicit_return and not returns_none:
        raise AstParseError("Missing return statement", [Diagnostic("Missing return statement", _location_from_node(func_def))])
    if has_explicit_return and func_def.body and not isinstance(func_def.body[-1], py_ast.Return):
        raise AstParseError(
            "Return statement must be last",
            [Diagnostic("Return statement must be last", _location_from_node(func_def.body[-1]))],
        )
    if outputs and isinstance(outputs[0], ScalarArgAST) and outputs[0].value_type is float:
        if not statements or not isinstance(statements[-1], SymbolToFloatAST):
            raise AstParseError(
                "Unsupported return annotation",
                [Diagnostic("Unsupported return annotation", _location_from_node(func_def.returns))],
            )

    body_location = (
        _location_from_node(parsed_body_statements[0]) if parsed_body_statements else _location_from_node(func_def)
    )
    return FunctionAST(
        name=func_def.name,
        inputs=inputs,
        outputs=outputs,
        body=BlockAST(statements=statements, location=body_location),
        location=_location_from_node(func_def),
        source=source,
        py_ast=func_def,
        diagnostics=[],
        has_explicit_return=has_explicit_return,
        has_return_annotation=has_return_annotation,
        returns_none=returns_none,
    )


def parse_function(fn: object) -> FunctionAST:
    """解析 Python 函数为 DSL AST。

    创建者: 小李飞刀
    最后一次更改: 金铲铲大作战

    功能说明:
    - 解析函数源码，构建 `FunctionAST` 并填充输入、输出与语句节点。

    使用示例:
    - func_ast = parse_function(add)

    关联文件:
    - spec: spec/dsl/ast.md
    - test: test/dsl/test_ast_visitor.py
    - 功能实现: kernel_gen/dsl/ast.py
    """

    try:
        return _parse_function_impl(fn)
    except _ParseFailure as exc:
        diagnostics = [Diagnostic(exc.message, location=exc.location)]
        raise AstParseError(exc.message, diagnostics) from exc
