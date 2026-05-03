"""DSL AST attribute node definitions.


功能说明:
- 定义 DSL AST 源码诊断结构与属性节点。
- 属性节点负责把 Python/DSL 属性值递归发射为 xDSL attribute 或原始 Python 对象。

API 列表:
- `SourceLocation(line: int, column: int)`
- `SourceLocation.from_py_ast(node: ast.AST) -> SourceLocation`
- `Diagnostic(message: str, location: SourceLocation | None = None)`
- `AttrAST(attr: Attribute, location: SourceLocation | None = None)`
- `PythonObjectAttrAST(attr: PythonObjectAttrInput, location: SourceLocation | None = None)`
- `ListAST(items: list[DSLNode], location: SourceLocation | None = None)`
- `TupleAST(items: tuple[DSLNode, ...], location: SourceLocation | None = None)`
- `IntTypeAttrAST(bits: int = 32, signed: bool = True, location: SourceLocation | None = None)`
- `FloatTypeAttrAST(dtype: NumericType = NumericType.Float32, location: SourceLocation | None = None)`
- `BoolTypeAttrAST(location: SourceLocation | None = None)`
- `MemorySpaceAttrAST(space: MemorySpace, location: SourceLocation | None = None)`
- `MemorySpaceAttrAST.runtime_space_from_memory_type(memory_type: NnMemoryType) -> MemorySpace`

使用示例:
- from kernel_gen.dsl.ast.nodes.attr import IntTypeAttrAST, MemorySpaceAttrAST
- IntTypeAttrAST(32).emit_mlir(ctx, None)

关联文件:
- spec: spec/dsl/ast/nodes/attr.md
- test: test/dsl/ast/nodes/test_attr.py
- 功能实现: kernel_gen/dsl/ast/nodes/attr.py
"""

from __future__ import annotations

import ast as py_ast
from collections.abc import Callable
from dataclasses import dataclass
from typing import TypeAlias

from xdsl.context import Context
from xdsl.dialects.builtin import (
    BFloat16Type,
    Float16Type,
    Float32Type,
    Float64Type,
    IntAttr,
    IntegerType,
    Signedness,
    i1,
    i8,
    i32,
    i64,
    ModuleOp,
)
from xdsl.ir import Attribute, Block, Operation, Region, SSAValue

from kernel_gen.core.error import ErrorKind, ErrorModule, KernelCodeError
from kernel_gen.dialect.nn import NnMemorySpaceAttr, NnMemoryType
from kernel_gen.operation.arch import BarrierScope, BarrierVisibility
from kernel_gen.symbol_variable.memory import MemorySpace
from kernel_gen.symbol_variable.type import Farmat, NumericType
from .basic import DSLNode

PythonObjectAttrInput: TypeAlias = (
    "str | int | float | bool | NumericType | Farmat | MemorySpace | "
    "BarrierVisibility | BarrierScope | type | Callable[..., DSLNode | None] | "
    "tuple[PythonObjectAttrInput, ...] | list[PythonObjectAttrInput] | None"
)
EmitMlirResult: TypeAlias = (
    "Attribute | Operation | SSAValue | Block | Region | ModuleOp | PythonObjectAttrInput | "
    "list[EmitMlirResult] | tuple[EmitMlirResult, ...]"
)


__all__ = [
    "SourceLocation",
    "Diagnostic",
    "AttrAST",
    "PythonObjectAttrAST",
    "ListAST",
    "TupleAST",
    "IntTypeAttrAST",
    "FloatTypeAttrAST",
    "BoolTypeAttrAST",
    "MemorySpaceAttrAST",
]


@dataclass
class SourceLocation:
    """源码位置信息。


    功能说明:
    - 记录 AST 节点在源码中的行列位置。

    使用示例:
    - SourceLocation(line=1, column=0)

    关联文件:
    - spec: spec/dsl/ast/__init__.md
    - test: test/dsl/ast/test_mlir_gen.py
    - 功能实现: kernel_gen/dsl/ast/nodes/
    """

    line: int
    column: int

    @classmethod
    def from_py_ast(cls, node: py_ast.AST) -> "SourceLocation":
        """从 Python AST 节点读取源码位置。


        功能说明:
        - 使用 Python AST 标准 `lineno` / `col_offset` 字段构造位置。
        - 不使用反射兜底；调用方必须只传带位置的 AST 节点。

        使用示例:
        - location = SourceLocation.from_py_ast(name_node)

        关联文件:
        - spec: spec/dsl/ast/nodes/attr.md
        - test: test/dsl/ast/test_parser.py
        - 功能实现: kernel_gen/dsl/ast/nodes/attr.py
        """

        return cls(node.lineno, node.col_offset)

@dataclass
class Diagnostic:
    """前端诊断信息。


    功能说明:
    - 记录错误消息与对应的源码位置信息。

    使用示例:
    - Diagnostic(message="Unsupported syntax", location=SourceLocation(3, 4))

    关联文件:
    - spec: spec/dsl/ast/nodes/attr.md
    - test: test/dsl/ast/test_mlir_gen.py
    - 功能实现: kernel_gen/dsl/ast/nodes/
    """

    message: str
    location: SourceLocation | None = None

@dataclass(eq=False)
class AttrAST(DSLNode):
    """MLIR attribute 节点。


    功能说明:
    - 承载已经构造好的 xDSL `Attribute`。
    - 作为类型、shape、stride、space 等属性进入 MLIR 的统一 AST 节点。

    使用示例:
    - AttrAST(IntAttr(4)).emit_mlir(ctx, None)

    关联文件:
    - spec: spec/dsl/ast/nodes/attr.md
    - test: test/dsl/ast/nodes/test_attr.py
    - 功能实现: kernel_gen/dsl/ast/nodes/attr.py
    """

    attr: Attribute
    location: SourceLocation | None = None

    def __eq__(self, other: AttrAST | EmitMlirResult) -> bool:
        """允许兼容比较 `AttrAST(value) == value`。"""

        if isinstance(other, AttrAST):
            return self.attr == other.attr
        return self.attr == other

    def emit_mlir(self, ctx: Context, block: Block | None = None) -> EmitMlirResult:
        """返回当前节点承载的 MLIR attribute。"""

        assert isinstance(ctx, Context)
        assert block is None or isinstance(block, Block)
        return self.attr

@dataclass(eq=False)
class PythonObjectAttrAST(AttrAST):
    """Python 对象属性节点。"""

    attr: PythonObjectAttrInput
    location: SourceLocation | None = None

@dataclass
class ListAST(DSLNode):
    """列表节点。"""

    items: list[DSLNode]
    location: SourceLocation | None = None

    def __post_init__(self) -> None:
        from .symbol import ConstValueAST

        self.items = [item if isinstance(item, DSLNode) else ConstValueAST(item, self.location) for item in self.items]

    def emit_mlir(self, ctx: Context, block: Block | None = None) -> EmitMlirResult:
        """返回逐项发射结果。"""

        assert isinstance(ctx, Context)
        assert block is None or isinstance(block, Block)
        values: list[EmitMlirResult] = []
        for item in self.items:
            values.append(item.emit_mlir(ctx, block))
        return values

@dataclass
class TupleAST(DSLNode):
    """元组节点。"""

    items: tuple[DSLNode, ...]
    location: SourceLocation | None = None

    def __post_init__(self) -> None:
        from .symbol import ConstValueAST

        self.items = tuple(item if isinstance(item, DSLNode) else ConstValueAST(item, self.location) for item in self.items)

    def emit_mlir(self, ctx: Context, block: Block | None = None) -> EmitMlirResult:
        """返回逐项发射结果。"""

        assert isinstance(ctx, Context)
        assert block is None or isinstance(block, Block)
        values: list[EmitMlirResult] = []
        for item in self.items:
            values.append(item.emit_mlir(ctx, block))
        return tuple(values)

@dataclass
class MemorySpaceAttrAST(DSLNode):
    """memory space attribute 节点。


    功能说明:
    - 将 `MemorySpace` 发射为 `NnMemorySpaceAttr`。

    使用示例:
    - MemorySpaceAttrAST(MemorySpace.GM).emit_mlir(ctx, None)

    关联文件:
    - spec: spec/dsl/ast/nodes/attr.md
    - test: test/dsl/ast/nodes/test_attr.py
    - 功能实现: kernel_gen/dsl/ast/nodes/attr.py
    """

    space: MemorySpace
    location: SourceLocation | None = None

    @classmethod
    def runtime_space_from_memory_type(cls, memory_type: NnMemoryType) -> MemorySpace:
        """把 `NnMemoryType.space` 还原为 runtime `MemorySpace`。


        功能说明:
        - 保持 `nn.memory` 中公开 space 文本与 DSL `MemorySpace` 枚举一致。

        使用示例:
        - space = MemorySpaceAttrAST.runtime_space_from_memory_type(memory_type)

        关联文件:
        - spec: spec/dsl/ast/nodes/attr.md
        - test: test/dsl/ast/nodes/test_attr.py
        - 功能实现: kernel_gen/dsl/ast/nodes/attr.py
        """

        space_name = memory_type.space.space.data
        space_map = {
            "global": MemorySpace.GM,
            "shared": MemorySpace.SM,
            "local": MemorySpace.LM,
            "tsm": MemorySpace.TSM,
            "tlm1": MemorySpace.TLM1,
            "tlm2": MemorySpace.TLM2,
            "tlm3": MemorySpace.TLM3,
        }
        if space_name not in space_map:
            raise KernelCodeError(ErrorKind.CONTRACT, ErrorModule.MLIR_GEN, f"Unsupported callee memory space: {space_name}")
        return space_map[space_name]

    def emit_mlir(self, ctx: Context, block: Block | None = None) -> EmitMlirResult:
        """发射 memory space attribute。"""

        assert isinstance(ctx, Context)
        assert block is None or isinstance(block, Block)
        if self.space is MemorySpace.GM:
            return NnMemorySpaceAttr.from_name("global")
        if self.space is MemorySpace.SM:
            return NnMemorySpaceAttr.from_name("shared")
        if self.space is MemorySpace.LM:
            return NnMemorySpaceAttr.from_name("local")
        if self.space is MemorySpace.TSM:
            return NnMemorySpaceAttr.from_name("tsm")
        if self.space is MemorySpace.TLM1:
            return NnMemorySpaceAttr.from_name("tlm1")
        if self.space is MemorySpace.TLM2:
            return NnMemorySpaceAttr.from_name("tlm2")
        if self.space is MemorySpace.TLM3:
            return NnMemorySpaceAttr.from_name("tlm3")
        raise KernelCodeError(ErrorKind.CONTRACT, ErrorModule.MLIR_GEN, "Unsupported memory space")


@dataclass
class IntTypeAttrAST(AttrAST):
    """整数类型属性节点。

    创建者: 榕
    最后一次更改: 2026-05-02

    功能说明:
    - 表示 DSL AST 中的整数 dtype 属性。
    - `emit_mlir(...)` 返回对应 xDSL integer type attribute。

    使用示例:
    - IntTypeAttrAST(bits=32).emit_mlir(ctx, None)
    """

    bits: int = 32
    signed: bool = True
    location: SourceLocation | None = None

    def __init__(self, bits: int = 32, signed: bool = True, location: SourceLocation | None = None) -> None:
        self.attr = i32 if bits == 32 and signed else IntegerType(bits, Signedness.SIGNLESS if signed else Signedness.UNSIGNED)
        self.bits = bits
        self.signed = signed
        self.location = location

    def emit_mlir(self, ctx: Context, block: Block | None = None) -> EmitMlirResult:
        """发射整数类型 attribute。"""

        assert isinstance(ctx, Context)
        assert block is None or isinstance(block, Block)
        if self.bits == 1:
            return i1
        if self.bits == 8:
            return i8 if self.signed else IntegerType(8, Signedness.UNSIGNED)
        if self.bits == 32:
            return i32 if self.signed else IntegerType(32, Signedness.UNSIGNED)
        if self.bits == 64:
            return i64 if self.signed else IntegerType(64, Signedness.UNSIGNED)
        return IntegerType(self.bits, Signedness.SIGNLESS if self.signed else Signedness.UNSIGNED)


@dataclass
class FloatTypeAttrAST(AttrAST):
    """浮点类型属性节点。

    创建者: 榕
    最后一次更改: 2026-05-02

    功能说明:
    - 表示 DSL AST 中的浮点 dtype 属性。
    - `emit_mlir(...)` 返回对应 xDSL float type attribute。

    使用示例:
    - FloatTypeAttrAST(NumericType.Float32).emit_mlir(ctx, None)
    """

    dtype: NumericType = NumericType.Float32
    location: SourceLocation | None = None

    def __init__(self, dtype: NumericType = NumericType.Float32, location: SourceLocation | None = None) -> None:
        self.attr = Float32Type()
        self.dtype = dtype
        self.location = location

    def emit_mlir(self, ctx: Context, block: Block | None = None) -> EmitMlirResult:
        """发射浮点类型 attribute。"""

        assert isinstance(ctx, Context)
        assert block is None or isinstance(block, Block)
        if self.dtype is NumericType.Float16:
            return Float16Type()
        if self.dtype is NumericType.BFloat16:
            return BFloat16Type()
        if self.dtype is NumericType.Float32:
            return Float32Type()
        if self.dtype is NumericType.Float64:
            return Float64Type()
        raise KernelCodeError(ErrorKind.CONTRACT, ErrorModule.MLIR_GEN, "FloatTypeAttrAST dtype must be float NumericType")


@dataclass
class BoolTypeAttrAST(AttrAST):
    """布尔类型属性节点。

    创建者: 榕
    最后一次更改: 2026-05-02

    功能说明:
    - 表示 DSL AST 中的 bool dtype 属性。
    - `emit_mlir(...)` 固定返回 `i1`。

    使用示例:
    - BoolTypeAttrAST().emit_mlir(ctx, None)
    """

    location: SourceLocation | None = None

    def __init__(self, location: SourceLocation | None = None) -> None:
        self.attr = i1
        self.location = location

    def emit_mlir(self, ctx: Context, block: Block | None = None) -> EmitMlirResult:
        """发射 bool 类型 attribute。"""

        assert isinstance(ctx, Context)
        assert block is None or isinstance(block, Block)
        return i1
