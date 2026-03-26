"""DSL AST definitions.

创建者: 小李飞刀
最后一次更改: 咯咯咯

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

import ast as py_ast
import inspect
import re
import textwrap
from dataclasses import dataclass, field
from typing import Iterable

import sympy as sp

from kernel_gen.symbol_variable.memory import Memory, MemorySpace
from kernel_gen.symbol_variable.symbol_dim import SymbolDim
from kernel_gen.symbol_variable.type import NumericType

_REJECT_EXTERNAL_VALUES_ENV_KEY = "__dsl_reject_external_values__"
_ALLOW_EXTERNAL_CONST_ENV_KEY = "__dsl_allow_external_const__"


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
class ArchQueryAST:
    """arch 查询表达式节点。

    创建者: 我不是牛马
    最后一次更改: 咯咯咯

    功能说明:
    - 表示 DSL 中最小 `arch` 查询调用。
    - 当前仅承载 `get_block_id()` / `get_block_num()` / `get_subthread_id()` / `get_subthread_num()` / `get_thread_id()` 查询名。

    使用示例:
    - ArchQueryAST(query_name="get_block_id")
    - ArchQueryAST(query_name="get_block_num")
    - ArchQueryAST(query_name="get_subthread_id")
    - ArchQueryAST(query_name="get_subthread_num")
    - ArchQueryAST(query_name="get_thread_id")

    关联文件:
    - spec: spec/dsl/ast.md
    - test: test/dsl/test_ast_visitor.py
    - 功能实现: kernel_gen/dsl/ast.py
    """

    query_name: str
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
    inputs: list[TensorAST | ScalarArgAST]
    outputs: list[TensorAST | ScalarArgAST]
    body: BlockAST
    location: SourceLocation | None = None
    source: str | None = None
    py_ast: object | None = None
    diagnostics: list[Diagnostic] = field(default_factory=list)

    def iter_inputs(self: FunctionAST) -> Iterable[TensorAST | ScalarArgAST]:
        """迭代输入参数。

        创建者: 小李飞刀
        最后一次更改: 小李飞刀

        功能说明:
        - 提供输入参数的统一迭代入口。

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


def _split_tensor_annotation(text: str, node: object | None) -> tuple[NumericType, list[int | str | SymbolDim]]:
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
        if part.isdigit():
            dims.append(int(part))
        elif any(op in part for op in ("+", "-", "*", "/")):
            names = set(re.findall(r"[A-Za-z_][A-Za-z0-9_]*", part))
            locals_map = {name: sp.Symbol(name) for name in names}
            expr = sp.sympify(part, locals=locals_map, evaluate=False)
            dims.append(SymbolDim(expr))
        else:
            dims.append(part)
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
    - 支持 `int`、`bool`、`SymbolDim` 与 `Tensor[...]` 四类公开注解文本。

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
    if text.strip() == "SymbolDim":
        return ScalarArgAST(name=arg_name or "ret0", value_type=int, is_symbolic=True, location=location)
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


def _parse_annotation_node(
    node: object | None,
    arg_name: str | None,
    globals_table: dict[str, object],
    builtins_table: dict[str, object],
    runtime_table: dict[str, object] | None = None,
) -> TensorAST | ScalarArgAST | None:
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

    if isinstance(node, (py_ast.Constant, py_ast.JoinedStr)):
        text = _normalize_annotation_text(node, globals_table, builtins_table, runtime_table)
        return _annotation_from_text(text, arg_name, node)

    if isinstance(node, py_ast.Name):
        if node.id == "int":
            return ScalarArgAST(name=arg_name or "ret0", value_type=int, location=_location_from_node(node))
        if node.id == "bool":
            return ScalarArgAST(name=arg_name or "ret0", value_type=bool, location=_location_from_node(node))
        if node.id == "SymbolDim":
            symbol_name = arg_name or "ret0"
            if (
                runtime_table is not None
                and arg_name is not None
                and arg_name in runtime_table
                and isinstance(runtime_table[arg_name], SymbolDim)
            ):
                symbol_name = str(runtime_table[arg_name].get_symbol())
            return ScalarArgAST(
                name=symbol_name,
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
    - 仅允许 `MemorySpace.*` 与 `NumericType.*` 这类 DSL 静态属性值参与函数体解析。
    - 拒绝将其他 Attribute 形式的外部值当作局部常量或隐式输入继续 lowering。

    使用示例:
    - _is_allowed_attribute_value(MemorySpace.LM)

    关联文件:
    - spec: spec/dsl/mlir_gen.md
    - test: test/dsl/test_ast_visitor.py
    - 功能实现: kernel_gen/dsl/ast.py
    """

    return isinstance(value, (MemorySpace, NumericType))


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
    offsets = _parse_expr(expr.args[1], env, globals_table, builtins_table)
    sizes = _parse_expr(expr.args[2], env, globals_table, builtins_table)
    stride = _parse_expr(expr.args[3], env, globals_table, builtins_table) if len(expr.args) >= 4 else None
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
    if not isinstance(tensor, TensorAST):
        _raise_parse_error(f"{call_name} target must be TensorAST", expr.args[1])
    allow_const_env = dict(env)
    allow_const_env[_ALLOW_EXTERNAL_CONST_ENV_KEY] = True
    offsets = _parse_expr(expr.args[2], allow_const_env, globals_table, builtins_table)
    sizes = _parse_expr(expr.args[3], allow_const_env, globals_table, builtins_table)
    stride = (
        _parse_expr(expr.args[4], allow_const_env, globals_table, builtins_table) if len(expr.args) >= 5 else None
    )
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
    最后一次更改: OpenAI

    功能说明:
    - 将 `load/slice/store/deslice/...` 解析为对应 AST 节点。
    - 将 `nn.add/sub/mul/truediv/floordiv(...)` 解析为对应的 `BinaryExprAST`。
    - 将 `get_block_id()` / `get_block_num()` / `get_subthread_id()` / `get_subthread_num()` / `get_thread_id()` 解析为 `ArchQueryAST`。

    使用示例:
    - _parse_dma_call(py_ast.parse("slice(A, [i], [n])").body[0].value, env, globals(), __builtins__)

    关联文件:
    - spec: spec/dsl/ast.md
    - test: test/dsl/test_ast_visitor.py
    - 功能实现: kernel_gen/dsl/ast.py
    """

    call_name: str | None = None
    if isinstance(expr.func, py_ast.Attribute):
        nn_expr = _parse_nn_arithmetic_call(expr, env, globals_table, builtins_table)
        if nn_expr is not None:
            return nn_expr
        base_object = _resolve_call_base_object(expr.func.value, globals_table, builtins_table)
        if getattr(base_object, "__name__", None) == "kernel_gen.operation.dma":
            call_name = expr.func.attr
        else:
            _raise_parse_error("Unsupported call expression", expr)

    elif isinstance(expr.func, py_ast.Name):
        call_name = expr.func.id
    else:
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
        offset = _parse_expr(expr.args[1], env, globals_table, builtins_table)
        size = _parse_expr(expr.args[2], env, globals_table, builtins_table)
        stride = _parse_expr(expr.args[3], env, globals_table, builtins_table)
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
        previous_allow_external = env.get(_ALLOW_EXTERNAL_CONST_ENV_KEY, False)
        env[_ALLOW_EXTERNAL_CONST_ENV_KEY] = True
        try:
            shape = _parse_expr(expr.args[1], env, globals_table, builtins_table)
        finally:
            if previous_allow_external:
                env[_ALLOW_EXTERNAL_CONST_ENV_KEY] = True
            else:
                env.pop(_ALLOW_EXTERNAL_CONST_ENV_KEY, None)
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

    _raise_parse_error("Unsupported call expression", expr)
    return expr


def _parse_expr(
    expr: object,
    env: dict[str, object],
    globals_table: dict[str, object],
    builtins_table: dict[str, object],
) -> object:
    if isinstance(expr, py_ast.Name):
        if expr.id in env:
            return env[expr.id]
        value = _lookup_python_name(expr.id, globals_table, builtins_table)
        if value is not None and bool(env.get(_REJECT_EXTERNAL_VALUES_ENV_KEY, False)):
            if bool(env.get(_ALLOW_EXTERNAL_CONST_ENV_KEY, False)) and isinstance(value, (int, float, str)):
                return ConstAST(value=value, location=_location_from_node(expr))
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
        return _parse_dma_call(expr, env, globals_table, builtins_table)

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
    reject_external_values = bool((config or {}).get("reject_external_values", False))
    if globals_table is None:
        globals_table = getattr(fn, "__globals__", {}) or {}
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
    if func_def.returns is not None:
        parsed = _parse_annotation_node(func_def.returns, None, globals_table, builtins_table, runtime_table)
        if parsed is None:
            _raise_parse_error("Unsupported return annotation", func_def.returns)
        if isinstance(parsed, (TensorAST, ScalarArgAST)):
            outputs.append(parsed)
        else:
            _raise_parse_error("Unsupported return annotation", func_def.returns)

    statements: list[object] = []
    has_return = False
    for stmt in func_def.body:
        parsed_stmt = _parse_stmt(stmt, env, globals_table, builtins_table)
        statements.append(parsed_stmt)
        if isinstance(stmt, py_ast.Return):
            has_return = True

    if func_def.returns is not None and not has_return:
        raise AstParseError("Missing return statement", [Diagnostic("Missing return statement", _location_from_node(func_def))])
    if has_return and not isinstance(func_def.body[-1], py_ast.Return):
        raise AstParseError("Return statement must be last", [Diagnostic("Return statement must be last", _location_from_node(func_def.body[-1]))])

    body_location = _location_from_node(func_def.body[0]) if func_def.body else _location_from_node(func_def)
    return FunctionAST(
        name=func_def.name,
        inputs=inputs,
        outputs=outputs,
        body=BlockAST(statements=statements, location=body_location),
        location=_location_from_node(func_def),
        source=source,
        py_ast=func_def,
        diagnostics=[],
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
