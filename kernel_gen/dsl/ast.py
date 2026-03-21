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

import ast as py_ast
import inspect
import textwrap
from dataclasses import dataclass, field
from typing import Iterable

from kernel_gen.symbol_variable.memory import Memory
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

    def iter_inputs(self) -> Iterable[TensorAST | ScalarArgAST]:
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

    def __init__(self, message: str, diagnostics: list[Diagnostic]) -> None:
        super().__init__(message)
        self.message = message
        self.diagnostics = diagnostics

    def __str__(self) -> str:
        return self.message


class _ParseFailure(Exception):
    def __init__(self, message: str, location: SourceLocation | None) -> None:
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


def _split_tensor_annotation(text: str, node: object | None) -> tuple[NumericType, list[int | str]]:
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
    dims: list[int | str] = []
    for part in parts[1:]:
        if part.isdigit():
            dims.append(int(part))
        else:
            dims.append(part)
    return dtype, dims


def _parse_annotation_node(
    node: object | None,
    arg_name: str | None,
    globals_table: dict[str, object],
    builtins_table: dict[str, object],
) -> TensorAST | ScalarArgAST | None:
    if node is None:
        if arg_name is None:
            return None
        if arg_name in globals_table and isinstance(globals_table[arg_name], Memory):
            memory = globals_table[arg_name]
            return TensorAST(name=arg_name, memory=memory, location=None)
        if arg_name in builtins_table and isinstance(builtins_table[arg_name], Memory):
            memory = builtins_table[arg_name]
            return TensorAST(name=arg_name, memory=memory, location=None)
        _raise_parse_error("Missing annotation", node)

    if isinstance(node, py_ast.Constant) and isinstance(node.value, str):
        text = node.value
        if text.strip() == "int":
            return ScalarArgAST(name=arg_name or "ret0", value_type=int, location=_location_from_node(node))
        dtype, dims = _split_tensor_annotation(text, node)
        memory = Memory(dims, dtype)
        return TensorAST(name=arg_name or "ret0", memory=memory, location=_location_from_node(node))

    if isinstance(node, py_ast.Name):
        if node.id == "int":
            return ScalarArgAST(name=arg_name or "ret0", value_type=int, location=_location_from_node(node))
        if node.id in globals_table and isinstance(globals_table[node.id], Memory):
            memory = globals_table[node.id]
            return TensorAST(name=arg_name or node.id, memory=memory, location=_location_from_node(node))
        _raise_parse_error("Unsupported annotation", node)

    if isinstance(node, py_ast.Subscript) and isinstance(node.value, py_ast.Name) and node.value.id == "Tensor":
        slice_node = node.slice
        items: list[str] = []
        if isinstance(slice_node, py_ast.Tuple):
            elements = slice_node.elts
        else:
            elements = [slice_node]
        for elt in elements:
            if isinstance(elt, py_ast.Name):
                items.append(elt.id)
            elif isinstance(elt, py_ast.Constant):
                items.append(str(elt.value))
            else:
                _raise_parse_error("Unsupported tensor annotation element", elt)
        text = "Tensor[" + ", ".join(items) + "]"
        dtype, dims = _split_tensor_annotation(text, node)
        memory = Memory(dims, dtype)
        return TensorAST(name=arg_name or "ret0", memory=memory, location=_location_from_node(node))

    _raise_parse_error("Unsupported annotation", node)
    return None


def _parse_expr(expr: object, env: dict[str, object]) -> object:
    if isinstance(expr, py_ast.Name):
        if expr.id in env:
            return env[expr.id]
        _raise_parse_error("Unknown name", expr)

    if isinstance(expr, py_ast.Constant):
        if isinstance(expr.value, (int, float, str)):
            return ConstAST(value=expr.value, location=_location_from_node(expr))
        _raise_parse_error("Unsupported constant type", expr)

    if isinstance(expr, py_ast.UnaryOp) and isinstance(expr.op, py_ast.USub):
        if isinstance(expr.operand, py_ast.Constant) and isinstance(expr.operand.value, (int, float)):
            return ConstAST(value=-expr.operand.value, location=_location_from_node(expr))
        _raise_parse_error("Unsupported unary expression", expr)

    if isinstance(expr, py_ast.BinOp):
        op_type = type(expr.op)
        if op_type not in _BIN_OP_MAP:
            _raise_parse_error("Unsupported binary op", expr)
        lhs = _parse_expr(expr.left, env)
        rhs = _parse_expr(expr.right, env)
        return BinaryExprAST(op=_BIN_OP_MAP[op_type], lhs=lhs, rhs=rhs, location=_location_from_node(expr))

    if isinstance(expr, py_ast.Compare):
        if len(expr.ops) != 1 or len(expr.comparators) != 1:
            _raise_parse_error("Unsupported compare expression", expr)
        op_type = type(expr.ops[0])
        if op_type not in _CMP_OP_MAP:
            _raise_parse_error("Unsupported compare op", expr)
        lhs = _parse_expr(expr.left, env)
        rhs = _parse_expr(expr.comparators[0], env)
        return CompareExprAST(op=_CMP_OP_MAP[op_type], lhs=lhs, rhs=rhs, location=_location_from_node(expr))

    _raise_parse_error("Unsupported expression", expr)
    return expr


def _parse_for(stmt: py_ast.For, env: dict[str, object]) -> ForAST:
    if not isinstance(stmt.target, py_ast.Name):
        _raise_parse_error("Unsupported for target", stmt.target)
    if not isinstance(stmt.iter, py_ast.Call) or not isinstance(stmt.iter.func, py_ast.Name):
        _raise_parse_error("Unsupported for iterator", stmt.iter)
    if stmt.iter.func.id != "range":
        _raise_parse_error("Unsupported for iterator", stmt.iter)
    args = stmt.iter.args
    if len(args) == 1:
        start_expr = ConstAST(value=0, location=_location_from_node(stmt))
        end_expr = _parse_expr(args[0], env)
    elif len(args) == 2:
        start_expr = _parse_expr(args[0], env)
        end_expr = _parse_expr(args[1], env)
    else:
        _raise_parse_error("Unsupported range arity", stmt.iter)

    var = VarAST(name=stmt.target.id, location=_location_from_node(stmt.target))
    previous = env.get(var.name)
    env[var.name] = var
    body_statements: list[object] = []
    for body_stmt in stmt.body:
        if isinstance(body_stmt, py_ast.Return):
            _raise_parse_error("Return inside for-loop is unsupported", body_stmt)
        body_statements.append(_parse_stmt(body_stmt, env))
    if previous is None:
        env.pop(var.name, None)
    else:
        env[var.name] = previous
    body_location = _location_from_node(stmt.body[0]) if stmt.body else _location_from_node(stmt)
    body = BlockAST(statements=body_statements, location=body_location)
    return ForAST(var=var, start=start_expr, end=end_expr, body=body, location=_location_from_node(stmt))


def _parse_stmt(stmt: py_ast.stmt, env: dict[str, object]) -> object:
    if isinstance(stmt, py_ast.Assign):
        if len(stmt.targets) != 1 or not isinstance(stmt.targets[0], py_ast.Name):
            _raise_parse_error("Unsupported assignment target", stmt)
        value = _parse_expr(stmt.value, env)
        env[stmt.targets[0].id] = value
        return value
    if isinstance(stmt, py_ast.Return):
        if stmt.value is None:
            _raise_parse_error("Return value is required", stmt)
        return _parse_expr(stmt.value, env)
    if isinstance(stmt, py_ast.For):
        return _parse_for(stmt, env)
    if isinstance(stmt, py_ast.Expr):
        return _parse_expr(stmt.value, env)
    _raise_parse_error("Unsupported syntax", stmt)
    return stmt


def _parse_function_impl(
    fn: object,
    globals_table: dict[str, object] | None = None,
    builtins_table: dict[str, object] | None = None,
    config: dict[str, object] | None = None,
) -> FunctionAST:
    del config
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
    inputs: list[TensorAST | ScalarArgAST] = []
    for arg in func_def.args.args:
        parsed = _parse_annotation_node(arg.annotation, arg.arg, globals_table, builtins_table)
        if parsed is None:
            _raise_parse_error("Missing annotation", arg)
        if isinstance(parsed, (TensorAST, ScalarArgAST)):
            inputs.append(parsed)
            env[arg.arg] = parsed
        else:
            _raise_parse_error("Unsupported argument annotation", arg)

    outputs: list[TensorAST | ScalarArgAST] = []
    if func_def.returns is not None:
        parsed = _parse_annotation_node(func_def.returns, None, globals_table, builtins_table)
        if parsed is None:
            _raise_parse_error("Unsupported return annotation", func_def.returns)
        if isinstance(parsed, (TensorAST, ScalarArgAST)):
            outputs.append(parsed)
        else:
            _raise_parse_error("Unsupported return annotation", func_def.returns)

    statements: list[object] = []
    has_return = False
    for stmt in func_def.body:
        parsed_stmt = _parse_stmt(stmt, env)
        statements.append(parsed_stmt)
        if isinstance(stmt, py_ast.Return):
            has_return = True

    if not has_return:
        raise AstParseError("Missing return statement", [Diagnostic("Missing return statement", _location_from_node(func_def))])
    if not isinstance(func_def.body[-1], py_ast.Return):
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
