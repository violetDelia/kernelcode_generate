"""AST front-end visitor for DSL.

创建者: 小李飞刀
最后一次更改: 小李飞刀

功能说明:
- 从受限 Python 函数构建 DSL AST，并提供 nn dialect IR 与 MLIR 文本入口。

使用示例:
- from kernel_gen.dsl.ast_visitor import visit_function, visit_to_nn_ir, emit_mlir
- func_ast = visit_function(fn)
- module = visit_to_nn_ir(fn)
- text = emit_mlir(fn)

关联文件:
- spec: spec/dsl/ast_visitor.md
- test: test/dsl/test_ast_visitor.py
- 功能实现: kernel_gen/dsl/ast_visitor.py
"""

from __future__ import annotations

import ast as py_ast
import inspect
import textwrap
from dataclasses import dataclass
from typing import Callable

from io import StringIO
from xdsl.printer import Printer

from kernel_gen.symbol_variable.memory import Memory
from kernel_gen.symbol_variable.type import NumericType

from .ast import (
    BinaryExprAST,
    BlockAST,
    CompareExprAST,
    ConstAST,
    Diagnostic,
    FunctionAST,
    ScalarArgAST,
    SourceLocation,
    TensorAST,
    VarAST,
)
from .lowering import LoweringError, lower_to_nn_ir


@dataclass(frozen=True)
class AstVisitorError(Exception):
    """AST 前端错误，携带诊断信息。

    创建者: 小李飞刀
    最后一次更改: 小李飞刀

    功能说明:
    - 用于报告不支持语法或类型错误，并附带诊断信息。

    使用示例:
    - raise AstVisitorError("Unsupported syntax", diagnostics=[Diagnostic("...")])

    关联文件:
    - spec: spec/dsl/ast_visitor.md
    - test: test/dsl/test_ast_visitor.py
    - 功能实现: kernel_gen/dsl/ast_visitor.py
    """

    message: str
    diagnostics: list[Diagnostic]

    def __str__(self) -> str:
        return self.message


def _get_location(node: py_ast.AST | None) -> SourceLocation | None:
    """从 Python AST 节点提取位置信息。

    创建者: 小李飞刀
    最后一次更改: 小李飞刀

    功能说明:
    - 返回 `SourceLocation`，无位置信息时返回 None。

    使用示例:
    - _get_location(node)

    关联文件:
    - spec: spec/dsl/ast_visitor.md
    - test: test/dsl/test_ast_visitor.py
    - 功能实现: kernel_gen/dsl/ast_visitor.py
    """

    if node is None:
        return None
    if hasattr(node, "lineno") and hasattr(node, "col_offset"):
        return SourceLocation(line=int(node.lineno), column=int(node.col_offset))
    return None


def _make_diagnostic(message: str, node: py_ast.AST | None) -> Diagnostic:
    """创建诊断信息。

    创建者: 小李飞刀
    最后一次更改: 小李飞刀

    功能说明:
    - 将消息与位置信息组合成 `Diagnostic`。

    使用示例:
    - _make_diagnostic("Unsupported syntax", node)

    关联文件:
    - spec: spec/dsl/ast_visitor.md
    - test: test/dsl/test_ast_visitor.py
    - 功能实现: kernel_gen/dsl/ast_visitor.py
    """

    return Diagnostic(message=message, location=_get_location(node))


def _parse_tensor_annotation(text: str) -> Memory:
    """解析 Tensor 注解字符串为 Memory。

    创建者: 小李飞刀
    最后一次更改: 小李飞刀

    功能说明:
    - 解析形如 `Tensor[f32, 2, 2]` 的标注。

    使用示例:
    - _parse_tensor_annotation("Tensor[f32, 2, 2]")

    关联文件:
    - spec: spec/dsl/ast_visitor.md
    - test: test/dsl/test_ast_visitor.py
    - 功能实现: kernel_gen/dsl/ast_visitor.py
    """

    if not text.startswith("Tensor[") or not text.endswith("]"):
        raise ValueError(f"Invalid Tensor annotation: {text}")
    inner = text[len("Tensor[") : -1]
    parts = [part.strip() for part in inner.split(",") if part.strip()]
    if len(parts) < 2:
        raise ValueError("Tensor annotation requires dtype and shape")
    dtype_text = parts[0]
    dims: list[int | str] = []
    for dim in parts[1:]:
        if dim.isdigit():
            dims.append(int(dim))
        else:
            dims.append(dim)

    dtype_map = {
        "f32": NumericType.Float32,
        "float32": NumericType.Float32,
        "i32": NumericType.Int32,
        "int32": NumericType.Int32,
    }
    if dtype_text not in dtype_map:
        raise ValueError(f"Unsupported dtype annotation: {dtype_text}")
    return Memory(dims, dtype_map[dtype_text])


def _parse_annotation(
    annotation: py_ast.AST | None,
    *,
    globals_table: dict[str, object] | None,
    builtins_table: dict[str, object] | None,
    node: py_ast.AST | None,
) -> tuple[str, object]:
    """解析函数参数注解。

    创建者: 小李飞刀
    最后一次更改: 小李飞刀

    功能说明:
    - 返回 ("tensor", Memory) 或 ("scalar", type)。

    使用示例:
    - _parse_annotation(annotation)

    关联文件:
    - spec: spec/dsl/ast_visitor.md
    - test: test/dsl/test_ast_visitor.py
    - 功能实现: kernel_gen/dsl/ast_visitor.py
    """

    if annotation is None:
        raise AstVisitorError(
            "Missing type annotation",
            diagnostics=[_make_diagnostic("Missing type annotation", node)],
        )

    if isinstance(annotation, py_ast.Constant) and isinstance(annotation.value, str):
        text = annotation.value
        if text.startswith("Tensor["):
            try:
                return "tensor", _parse_tensor_annotation(text)
            except ValueError as exc:
                raise AstVisitorError(
                    str(exc),
                    diagnostics=[_make_diagnostic(str(exc), node)],
                ) from exc
        if text == "int":
            return "scalar", int
        raise AstVisitorError(
            "Unsupported annotation string",
            diagnostics=[_make_diagnostic("Unsupported annotation string", node)],
        )

    if isinstance(annotation, py_ast.Name):
        if annotation.id == "int":
            return "scalar", int
        raise AstVisitorError(
            f"Unsupported annotation: {annotation.id}",
            diagnostics=[_make_diagnostic("Unsupported annotation name", node)],
        )

    if isinstance(annotation, py_ast.Subscript):
        if isinstance(annotation.value, py_ast.Name):
            base_name = annotation.value.id
        else:
            base_name = None
        if base_name is None:
            raise AstVisitorError(
                "Unsupported annotation base",
                diagnostics=[_make_diagnostic("Unsupported annotation base", node)],
            )
        allowed = base_name == "Tensor"
        if globals_table and base_name in globals_table:
            allowed = True
        if builtins_table and base_name in builtins_table:
            allowed = True
        if not allowed:
            raise AstVisitorError(
                "Unknown annotation base",
                diagnostics=[_make_diagnostic("Unknown annotation base", node)],
            )

        slice_node = annotation.slice
        if isinstance(slice_node, py_ast.Tuple):
            elements = slice_node.elts
        else:
            elements = [slice_node]
        if not elements:
            raise AstVisitorError(
                "Empty Tensor annotation",
                diagnostics=[_make_diagnostic("Empty Tensor annotation", node)],
            )

        def _token_from_ast(token: py_ast.AST) -> str | int:
            if isinstance(token, py_ast.Name):
                return token.id
            if isinstance(token, py_ast.Constant) and isinstance(token.value, (int, str)):
                return token.value
            raise AstVisitorError(
                "Unsupported Tensor annotation token",
                diagnostics=[_make_diagnostic("Unsupported Tensor annotation token", token)],
            )

        tokens = [_token_from_ast(item) for item in elements]
        if len(tokens) < 2:
            raise AstVisitorError(
                "Tensor annotation requires dtype and shape",
                diagnostics=[_make_diagnostic("Tensor annotation requires dtype and shape", node)],
            )
        dtype_token = str(tokens[0])
        dims: list[int | str] = []
        for token in tokens[1:]:
            if isinstance(token, int):
                dims.append(token)
            else:
                dims.append(str(token))
        dtype_map = {
            "f32": NumericType.Float32,
            "float32": NumericType.Float32,
            "i32": NumericType.Int32,
            "int32": NumericType.Int32,
        }
        if dtype_token not in dtype_map:
            raise AstVisitorError(
                "Unsupported dtype annotation",
                diagnostics=[_make_diagnostic("Unsupported dtype annotation", node)],
            )
        return "tensor", Memory(dims, dtype_map[dtype_token])

    raise AstVisitorError(
        "Unsupported annotation type",
        diagnostics=[_make_diagnostic("Unsupported annotation type", node)],
    )


def _build_expr(node: py_ast.AST, symbols: dict[str, object]) -> object:
    """将 Python AST 表达式转换为 DSL AST。

    创建者: 小李飞刀
    最后一次更改: 小李飞刀

    功能说明:
    - 支持二元算术、比较、常量与名称引用。

    使用示例:
    - _build_expr(node, symbols)

    关联文件:
    - spec: spec/dsl/ast_visitor.md
    - test: test/dsl/test_ast_visitor.py
    - 功能实现: kernel_gen/dsl/ast_visitor.py
    """

    location = _get_location(node)

    if isinstance(node, py_ast.Name):
        if node.id not in symbols:
            raise AstVisitorError(
                "Unknown symbol",
                diagnostics=[_make_diagnostic(f"Unknown symbol: {node.id}", node)],
            )
        return symbols[node.id]

    if isinstance(node, py_ast.Constant):
        return ConstAST(value=node.value, location=location)

    if isinstance(node, py_ast.BinOp):
        op_map = {
            py_ast.Add: "add",
            py_ast.Sub: "sub",
            py_ast.Mult: "mul",
            py_ast.Div: "div",
        }
        for op_type, op_name in op_map.items():
            if isinstance(node.op, op_type):
                return BinaryExprAST(
                    op=op_name,
                    lhs=_build_expr(node.left, symbols),
                    rhs=_build_expr(node.right, symbols),
                    location=location,
                )
        raise AstVisitorError(
            "Unsupported binary operator",
            diagnostics=[_make_diagnostic("Unsupported binary operator", node)],
        )

    if isinstance(node, py_ast.Compare):
        if len(node.ops) != 1 or len(node.comparators) != 1:
            raise AstVisitorError(
                "Chained comparisons are not supported",
                diagnostics=[_make_diagnostic("Chained comparison", node)],
            )
        op_map = {
            py_ast.Eq: "eq",
            py_ast.NotEq: "ne",
            py_ast.Lt: "lt",
            py_ast.LtE: "le",
            py_ast.Gt: "gt",
            py_ast.GtE: "ge",
        }
        op_node = node.ops[0]
        for op_type, op_name in op_map.items():
            if isinstance(op_node, op_type):
                return CompareExprAST(
                    op=op_name,
                    lhs=_build_expr(node.left, symbols),
                    rhs=_build_expr(node.comparators[0], symbols),
                    location=location,
                )
        raise AstVisitorError(
            "Unsupported comparison operator",
            diagnostics=[_make_diagnostic("Unsupported comparison operator", node)],
        )

    raise AstVisitorError(
        "Unsupported expression",
        diagnostics=[_make_diagnostic("Unsupported expression", node)],
    )


def visit_function(
    fn: Callable[..., object],
    globals: dict[str, object] | None = None,
    builtins: dict[str, object] | None = None,
    config: dict[str, object] | None = None,
) -> FunctionAST:
    """解析 Python 函数并生成 FunctionAST。

    创建者: 小李飞刀
    最后一次更改: 小李飞刀

    功能说明:
    - 读取源码并构建 AST。
    - 提取函数签名、参数注解与返回注解。

    使用示例:
    - func_ast = visit_function(fn, globals={}, builtins={}, config={"keep_source": True})

    关联文件:
    - spec: spec/dsl/ast_visitor.md
    - test: test/dsl/test_ast_visitor.py
    - 功能实现: kernel_gen/dsl/ast_visitor.py
    """

    globals_table = globals or {}
    builtins_table = builtins or {}
    config = config or {}

    try:
        source = inspect.getsource(fn)
    except OSError as exc:
        raise OSError("Failed to load function source") from exc

    source = textwrap.dedent(source)
    try:
        module_ast = py_ast.parse(source)
    except SyntaxError as exc:
        raise SyntaxError("Failed to parse function source") from exc

    function_def = None
    for node in module_ast.body:
        if isinstance(node, py_ast.FunctionDef) and node.name == fn.__name__:
            function_def = node
            break

    if function_def is None:
        raise TypeError("Function definition not found in source")

    inputs: list[TensorAST | ScalarArgAST] = []
    symbol_table: dict[str, object] = {}
    for arg in function_def.args.args:
        kind, value = _parse_annotation(
            arg.annotation,
            globals_table=globals_table,
            builtins_table=builtins_table,
            node=arg,
        )
        if kind == "tensor":
            tensor = TensorAST(name=arg.arg, memory=value, location=_get_location(arg))
            inputs.append(tensor)
            symbol_table[arg.arg] = tensor
        else:
            scalar = ScalarArgAST(name=arg.arg, value_type=value, location=_get_location(arg))
            inputs.append(scalar)
            symbol_table[arg.arg] = scalar

    outputs: list[TensorAST | ScalarArgAST] = []
    if function_def.returns is not None:
        kind, value = _parse_annotation(
            function_def.returns,
            globals_table=globals_table,
            builtins_table=builtins_table,
            node=function_def.returns,
        )
        if kind == "tensor":
            outputs.append(TensorAST(name="return", memory=value, location=_get_location(function_def.returns)))
        elif kind == "scalar":
            outputs.append(ScalarArgAST(name="return", value_type=value, location=_get_location(function_def.returns)))

    statements: list[object] = []
    has_return = False
    for stmt in function_def.body:
        if isinstance(stmt, py_ast.Assign):
            if has_return:
                raise AstVisitorError(
                    "Statements after return are not supported",
                    diagnostics=[_make_diagnostic("Unsupported statement order", stmt)],
                )
            if len(stmt.targets) != 1 or not isinstance(stmt.targets[0], py_ast.Name):
                raise AstVisitorError(
                    "Unsupported assignment target",
                    diagnostics=[_make_diagnostic("Unsupported assignment target", stmt)],
                )
            try:
                assign_expr = _build_expr(stmt.value, symbol_table)
            except AstVisitorError as exc:
                raise AstVisitorError(exc.message, diagnostics=exc.diagnostics) from exc
            target_name = stmt.targets[0].id
            symbol_table[target_name] = assign_expr
            statements.append(assign_expr)
            continue

        if isinstance(stmt, py_ast.Return):
            if has_return:
                raise AstVisitorError(
                    "Multiple return statements are not supported",
                    diagnostics=[_make_diagnostic("Unsupported return statement", stmt)],
                )
            if stmt.value is None:
                raise AstVisitorError(
                    "Return value is required",
                    diagnostics=[_make_diagnostic("Missing return value", stmt)],
                )
            try:
                return_expr = _build_expr(stmt.value, symbol_table)
            except AstVisitorError as exc:
                raise AstVisitorError(exc.message, diagnostics=exc.diagnostics) from exc
            statements.append(return_expr)
            has_return = True
            continue

        raise AstVisitorError(
            "Unsupported statement",
            diagnostics=[_make_diagnostic("Unsupported statement", stmt)],
        )

    if not has_return:
        raise AstVisitorError(
            "Missing return statement",
            diagnostics=[_make_diagnostic("Missing return statement", function_def)],
        )

    body = BlockAST(statements=statements, location=_get_location(function_def))

    diagnostics: list[Diagnostic] = []
    if isinstance(return_expr, (BinaryExprAST, CompareExprAST)):
        diagnostics.extend([])

    return FunctionAST(
        name=function_def.name,
        inputs=inputs,
        outputs=outputs,
        body=body,
        location=_get_location(function_def),
        source=source if config.get("keep_source") else None,
        py_ast=function_def,
        diagnostics=diagnostics,
    )


def visit_to_nn_ir(
    fn: Callable[..., object],
    globals: dict[str, object] | None = None,
    builtins: dict[str, object] | None = None,
    config: dict[str, object] | None = None,
):
    """将 Python 函数 lowering 为 nn dialect IR。

    创建者: 小李飞刀
    最后一次更改: 小李飞刀

    功能说明:
    - 先构建 FunctionAST，再调用 lowering 入口生成 nn IR。

    使用示例:
    - module = visit_to_nn_ir(fn)

    关联文件:
    - spec: spec/dsl/ast_visitor.md
    - test: test/dsl/test_ast_visitor.py
    - 功能实现: kernel_gen/dsl/ast_visitor.py
    """

    func_ast = visit_function(fn, globals=globals, builtins=builtins, config=config)
    try:
        return lower_to_nn_ir(func_ast)
    except LoweringError as exc:
        diagnostic = Diagnostic(str(exc), location=exc.location)
        raise AstVisitorError(str(exc), diagnostics=[diagnostic]) from exc


def emit_mlir(
    value: Callable[..., object] | object,
    globals: dict[str, object] | None = None,
    builtins: dict[str, object] | None = None,
    config: dict[str, object] | None = None,
) -> str:
    """输出 nn dialect IR 的 MLIR 文本。

    创建者: 小李飞刀
    最后一次更改: 小李飞刀

    功能说明:
    - 输入函数时先生成 nn IR，再打印文本。
    - 输入 module 时直接打印文本。

    使用示例:
    - mlir_text = emit_mlir(fn)

    关联文件:
    - spec: spec/dsl/ast_visitor.md
    - test: test/dsl/test_ast_visitor.py
    - 功能实现: kernel_gen/dsl/ast_visitor.py
    """

    if callable(value):
        module = visit_to_nn_ir(value, globals=globals, builtins=builtins, config=config)
    else:
        module = value

    stream = StringIO()
    printer = Printer(stream=stream)
    printer.print_op(module)
    return stream.getvalue()
