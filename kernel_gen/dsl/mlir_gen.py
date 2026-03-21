"""MLIR function assembly entrypoints for DSL.

创建者: 小李飞刀
最后一次更改: 朽木露琪亚

功能说明:
- 负责将 `FunctionAST` 组装为 `func.func`。
- 统一函数签名、返回类型校验与 AST visitor 驱动。

使用示例:
- from kernel_gen.dsl.mlir_gen import build_func_op
- func_op = build_func_op(fn)

关联文件:
- spec: spec/dsl/mlir_gen.md
- test: test/dsl/test_ast_visitor.py
- 功能实现: kernel_gen/dsl/mlir_gen.py
"""

from __future__ import annotations

from typing import Callable

from xdsl.dialects import func
from xdsl.dialects.builtin import FunctionType, i32
from xdsl.ir import Block, Region

from .ast import AstParseError, FunctionAST, ScalarArgAST, TensorAST, _parse_function_impl
from .emit_mlir import EmitContext, _LoweringError, _ensure_supported_statements, _expr_key, _infer_expr_type, _memory_to_nn_type


def _build_signature_types(func_ast: FunctionAST) -> tuple[list[object], dict[int, object]]:
    if not func_ast.inputs:
        raise _LoweringError("Function has no inputs", location=func_ast.location)

    arg_types: list[object] = []
    type_map: dict[int, object] = {}
    tensor_input_count = 0
    for item in func_ast.inputs:
        if isinstance(item, TensorAST):
            arg_type = _memory_to_nn_type(item.memory)
            tensor_input_count += 1
        elif isinstance(item, ScalarArgAST):
            if item.value_type is not int:
                raise _LoweringError("Unsupported scalar argument type", location=item.location)
            arg_type = i32
        else:
            raise _LoweringError("Unsupported input type", location=getattr(item, "location", None))
        arg_types.append(arg_type)
        type_map[_expr_key(item)] = arg_type

    if tensor_input_count == 0:
        raise _LoweringError("At least one tensor input is required", location=func_ast.location)
    return arg_types, type_map


def _validate_return_type(func_ast: FunctionAST, result_type: object) -> None:
    if not func_ast.outputs:
        return
    if len(func_ast.outputs) != 1:
        raise _LoweringError("Only single return value is supported", location=func_ast.location)
    output = func_ast.outputs[0]
    if isinstance(output, TensorAST):
        expected_type = _memory_to_nn_type(output.memory)
    elif isinstance(output, ScalarArgAST):
        if output.value_type is not int:
            raise _LoweringError("Unsupported scalar return type", location=output.location)
        expected_type = i32
    else:
        raise _LoweringError("Unsupported return annotation type", location=getattr(output, "location", None))
    if result_type != expected_type:
        raise _LoweringError("Return type does not match annotation", location=func_ast.location)


def build_func_op(
    fn: Callable[..., object],
    globals: dict[str, object] | None = None,
    builtins: dict[str, object] | None = None,
    config: dict[str, object] | None = None,
) -> func.FuncOp:
    from .ast_visitor import AstVisitorError

    try:
        func_ast = _parse_function_impl(
            fn,
            globals_table=globals,
            builtins_table=builtins,
            config=config,
        )
    except AstParseError as exc:
        location = exc.diagnostics[0].location if exc.diagnostics else None
        raise AstVisitorError(exc.message, location=location) from exc
    return build_func_op_from_ast(func_ast, config=config)


def _build_func_op_from_ast_impl(
    func_ast: FunctionAST,
    config: dict[str, object] | None = None,
) -> func.FuncOp:
    from .ast_visitor import AstVisitor

    config = config or {}
    arg_types, type_map = _build_signature_types(func_ast)
    statements = _ensure_supported_statements(func_ast)
    return_expr = statements[-1]
    result_type = _infer_expr_type(return_expr, dict(type_map))
    _validate_return_type(func_ast, result_type)

    func_type = FunctionType.from_lists(arg_types, [result_type])
    block = Block(arg_types=arg_types)
    func_op = func.FuncOp(func_ast.name, func_type, Region(block))

    ctx = EmitContext(builder=block, symbols={}, types=dict(type_map), config=config)
    visitor = AstVisitor(config=config)
    return_value = visitor.visit_function(func_ast, ctx)
    if return_value is None:
        raise _LoweringError("Function body is empty", location=func_ast.location)
    block.add_op(func.ReturnOp(return_value))
    return func_op


def build_func_op_from_ast(
    func_ast: FunctionAST,
    config: dict[str, object] | None = None,
) -> func.FuncOp:
    from .ast_visitor import AstVisitorError

    try:
        return _build_func_op_from_ast_impl(func_ast, config=config)
    except _LoweringError as exc:
        raise AstVisitorError(str(exc), location=exc.location) from exc
