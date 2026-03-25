"""MLIR function assembly entrypoints for DSL.

创建者: 小李飞刀
最后一次更改: 我不是牛马

功能说明:
- 负责将 `FunctionAST` 组装为 `func.func`。
- 统一函数签名、返回类型校验与 AST visitor 驱动。

使用示例:
- from kernel_gen.dsl.mlir_gen import build_func_op
- func_op = build_func_op(fn, *runtime_args)

关联文件:
- spec: spec/dsl/mlir_gen.md
- test: test/dsl/test_ast_visitor.py
- 功能实现: kernel_gen/dsl/mlir_gen.py
"""

from __future__ import annotations

import inspect
from typing import Callable

from xdsl.dialects import func
from xdsl.dialects.builtin import FunctionType, i1, i32
from xdsl.ir import Block, Region

from kernel_gen.dialect.nn import NnMemoryType
from kernel_gen.dialect.symbol import SymbolValueType
from kernel_gen.symbol_variable.memory import Memory
from kernel_gen.symbol_variable.symbol_dim import SymbolDim

from .ast import (
    AstParseError,
    ConstAST,
    DmaAllocAST,
    Diagnostic,
    FunctionAST,
    ScalarArgAST,
    TensorAST,
    _ParseFailure,
    _parse_function_impl,
)
from .emit_mlir import EmitContext, _LoweringError, _ensure_supported_statements, _expr_key, _infer_expr_type, _memory_to_nn_type


def _is_symbol_scalar_function(func_ast: FunctionAST) -> bool:
    if not func_ast.inputs:
        return False
    if not all(isinstance(item, ScalarArgAST) and item.value_type is int for item in func_ast.inputs):
        return False
    if not func_ast.outputs:
        return True
    return all(isinstance(item, ScalarArgAST) and item.value_type in {int, bool} for item in func_ast.outputs)


def _is_symbol_scalar_arg(item: ScalarArgAST, *, is_symbol_scalar_function: bool) -> bool:
    return is_symbol_scalar_function or item.is_symbolic


def _symbol_expr_from_runtime_arg(runtime_arg: object) -> str | None:
    if isinstance(runtime_arg, SymbolDim):
        return str(runtime_arg.get_symbol())
    if isinstance(runtime_arg, int):
        return str(runtime_arg)
    return None


def _is_dma_alloc_only_function(func_ast: FunctionAST) -> bool:
    statements = func_ast.body.statements
    if len(func_ast.outputs) != 1 or not statements:
        return False
    if not isinstance(func_ast.outputs[0], TensorAST):
        return False
    return isinstance(statements[-1], DmaAllocAST)


def _resolve_dma_alloc_shape_value(expr: object, runtime_values: dict[str, object]) -> int | str | SymbolDim:
    if isinstance(expr, ScalarArgAST):
        if expr.name in runtime_values:
            runtime_value = runtime_values[expr.name]
            if isinstance(runtime_value, int):
                return runtime_value
            if isinstance(runtime_value, SymbolDim):
                return runtime_value
            runtime_expr = _symbol_expr_from_runtime_arg(runtime_value)
            if runtime_expr is None:
                raise _LoweringError("Unsupported scalar argument type", location=expr.location)
            return runtime_expr
        return expr.name
    if isinstance(expr, ConstAST):
        if isinstance(expr.value, (int, str)):
            return expr.value
        raise _LoweringError("Index must be int or str", location=expr.location)
    if isinstance(expr, (int, str)):
        return expr
    raise _LoweringError("Unsupported index expression", location=getattr(expr, "location", None))


def _build_dma_alloc_only_result_type(
    func_ast: FunctionAST,
    alloc_expr: DmaAllocAST,
    runtime_args: tuple[object, ...] | list[object] | None,
) -> NnMemoryType:
    runtime_values: dict[str, object] = {}
    if runtime_args is not None:
        runtime_values = {
            input_arg.name: runtime_args[index]
            for index, input_arg in enumerate(func_ast.inputs)
            if isinstance(input_arg, ScalarArgAST)
        }
    if isinstance(alloc_expr.shape, (list, tuple)):
        shape_exprs = list(alloc_expr.shape)
    else:
        shape_exprs = [alloc_expr.shape]
    shape = [_resolve_dma_alloc_shape_value(entry, runtime_values) for entry in shape_exprs]
    stride = None
    if alloc_expr.stride is not None:
        if isinstance(alloc_expr.stride, (list, tuple)):
            stride_exprs = list(alloc_expr.stride)
        else:
            stride_exprs = [alloc_expr.stride]
        stride = [_resolve_dma_alloc_shape_value(entry, runtime_values) for entry in stride_exprs]
        default_stride = Memory._default_stride(Memory._normalize_shape(shape))
        if Memory._normalize_shape(stride).get_values() != default_stride.get_values():
            raise _LoweringError("dma.alloc only supports contiguous stride", location=alloc_expr.location)
    memory = Memory(shape, alloc_expr.dtype, space=alloc_expr.space, stride=stride)
    return _memory_to_nn_type(memory, location=alloc_expr.location)


def _build_signature_types(
    func_ast: FunctionAST,
    runtime_args: tuple[object, ...] | list[object] | None = None,
    *,
    allow_dma_alloc_only: bool = False,
) -> tuple[list[object], dict[int, object]]:
    if runtime_args is not None and len(runtime_args) != len(func_ast.inputs):
        raise _LoweringError("runtime_args must align with func_ast inputs", location=func_ast.location)

    is_symbol_scalar_function = _is_symbol_scalar_function(func_ast)
    arg_types: list[object] = []
    type_map: dict[int, object] = {}
    tensor_input_count = 0
    for index, item in enumerate(func_ast.inputs):
        runtime_arg = None if runtime_args is None else runtime_args[index]
        if isinstance(item, TensorAST):
            arg_type = _memory_to_nn_type(item.memory, location=item.location)
            tensor_input_count += 1
        elif isinstance(item, ScalarArgAST):
            if item.value_type is not int:
                raise _LoweringError("Unsupported scalar argument type", location=item.location)
            runtime_expr = _symbol_expr_from_runtime_arg(runtime_arg)
            if allow_dma_alloc_only:
                if runtime_args is not None:
                    if runtime_expr is None:
                        raise _LoweringError("Unsupported scalar argument type", location=item.location)
                    arg_type = SymbolValueType.from_expr(runtime_expr)
                else:
                    arg_type = SymbolValueType.from_expr(item.name)
            elif runtime_expr is not None and (is_symbol_scalar_function or isinstance(runtime_arg, SymbolDim)):
                arg_type = SymbolValueType.from_expr(runtime_expr)
            elif _is_symbol_scalar_arg(item, is_symbol_scalar_function=is_symbol_scalar_function):
                arg_type = SymbolValueType.from_expr(item.name)
            else:
                arg_type = i32
        else:
            raise _LoweringError("Unsupported input type", location=getattr(item, "location", None))
        arg_types.append(arg_type)
        type_map[_expr_key(item)] = arg_type

    if func_ast.inputs and tensor_input_count == 0 and not is_symbol_scalar_function and not allow_dma_alloc_only:
        raise _LoweringError("At least one tensor input is required", location=func_ast.location)
    return arg_types, type_map


def _parse_function_with_env(
    fn: Callable[..., object],
    globals_table: dict[str, object] | None,
    builtins_table: dict[str, object] | None,
    runtime_table: dict[str, object] | None,
    config: dict[str, object] | None,
) -> FunctionAST:
    try:
        return _parse_function_impl(
            fn,
            globals_table=globals_table,
            builtins_table=builtins_table,
            runtime_table=runtime_table,
            config=config,
        )
    except _ParseFailure as exc:
        diagnostics = [Diagnostic(exc.message, location=exc.location)]
        raise AstParseError(exc.message, diagnostics) from exc


def _validate_return_type(func_ast: FunctionAST, result_type: object) -> None:
    if not func_ast.outputs:
        return
    if len(func_ast.outputs) != 1:
        raise _LoweringError("Only single return value is supported", location=func_ast.location)
    output = func_ast.outputs[0]
    if isinstance(output, TensorAST):
        expected_type = _memory_to_nn_type(output.memory, location=output.location)
        if not isinstance(result_type, NnMemoryType):
            raise _LoweringError("Return type does not match annotation", location=func_ast.location)
        # Tensor 注解只公开约束 shape 与 element_type；DMA helper 允许返回不同的 space/stride。
        if result_type.shape != expected_type.shape or result_type.element_type != expected_type.element_type:
            raise _LoweringError("Return type does not match annotation", location=func_ast.location)
        return
    elif isinstance(output, ScalarArgAST):
        if output.value_type is bool:
            expected_type = i1
        elif output.value_type is int:
            if not func_ast.inputs and isinstance(result_type, SymbolValueType):
                return
            if _is_symbol_scalar_function(func_ast):
                if isinstance(result_type, SymbolValueType):
                    return
                expected_type = SymbolValueType.from_expr(output.name)
            else:
                expected_type = i32
        else:
            raise _LoweringError("Unsupported scalar return type", location=output.location)
    else:
        raise _LoweringError("Unsupported return annotation type", location=getattr(output, "location", None))
    if result_type != expected_type:
        raise _LoweringError("Return type does not match annotation", location=func_ast.location)


def build_func_op(
    fn: Callable[..., object],
    *runtime_args: object,
    globals: dict[str, object] | None = None,
    builtins: dict[str, object] | object | None = None,
) -> func.FuncOp:
    from .ast_visitor import AstVisitorError

    signature = inspect.signature(fn)
    positional_params = [
        param
        for param in signature.parameters.values()
        if param.kind in (inspect.Parameter.POSITIONAL_ONLY, inspect.Parameter.POSITIONAL_OR_KEYWORD)
    ]
    if len(runtime_args) != len(positional_params):
        if not runtime_args and (globals is not None or builtins is not None):
            reason = (
                "globals/builtins cannot replace function runtime args: "
                f"expected {len(positional_params)}, got 0"
            )
            raise AstVisitorError(reason, location=None)
        reason = (
            f"build_func_op requires explicit runtime args for {fn.__name__}: "
            f"expected {len(positional_params)}, got {len(runtime_args)}"
        )
        raise AstVisitorError(reason, location=None)

    runtime_table = {param.name: runtime_args[index] for index, param in enumerate(positional_params)}
    # globals/builtins 仅作为解析环境，不参与签名推导。
    globals_table = dict(getattr(fn, "__globals__", {}) or {})
    globals_table.update(inspect.getclosurevars(fn).nonlocals)
    if globals is not None:
        globals_table.update(globals)
    globals_table.update(runtime_table)
    builtins_obj = builtins if builtins is not None else globals_table.get("__builtins__", {})
    if isinstance(builtins_obj, dict):
        builtins_table = builtins_obj
    else:
        builtins_table = getattr(builtins_obj, "__dict__", {})

    try:
        func_ast = _parse_function_with_env(
            fn,
            globals_table,
            builtins_table,
            runtime_table,
            config={"reject_external_values": True},
        )
    except AstParseError as exc:
        location = exc.diagnostics[0].location if exc.diagnostics else None
        raise AstVisitorError(exc.message, location=location) from exc
    return build_func_op_from_ast(func_ast, runtime_args=runtime_args)


def _build_func_op_from_ast_impl(
    func_ast: FunctionAST,
    runtime_args: tuple[object, ...] | list[object] | None = None,
    config: dict[str, object] | None = None,
) -> func.FuncOp:
    from .ast_visitor import AstVisitor

    config = config or {}
    is_dma_alloc_only = _is_dma_alloc_only_function(func_ast)
    arg_types, type_map = _build_signature_types(
        func_ast,
        runtime_args=runtime_args,
        allow_dma_alloc_only=is_dma_alloc_only,
    )
    statements = _ensure_supported_statements(func_ast)
    result_types: list[object] = []
    infer_scalar_return = False
    if func_ast.outputs:
        return_expr = statements[-1]
        if is_dma_alloc_only:
            if not isinstance(return_expr, DmaAllocAST):
                raise _LoweringError("Return type does not match annotation", location=func_ast.location)
            result_type = _build_dma_alloc_only_result_type(func_ast, return_expr, runtime_args)
        else:
            result_type = _infer_expr_type(return_expr, dict(type_map))
        _validate_return_type(func_ast, result_type)
        type_map[_expr_key(return_expr)] = result_type
        result_types = [result_type]
    elif _is_symbol_scalar_function(func_ast):
        return_expr = statements[-1]
        result_type = _infer_expr_type(return_expr, dict(type_map))
        if not isinstance(result_type, SymbolValueType):
            raise _LoweringError("Symbol scalar function return must lower to !symbol.int", location=func_ast.location)
        result_types = [result_type]
        infer_scalar_return = True

    func_type = FunctionType.from_lists(arg_types, result_types)
    block = Block(arg_types=arg_types)
    func_op = func.FuncOp(func_ast.name, func_type, Region(block))

    ctx = EmitContext(builder=block, symbols={}, types=dict(type_map), config=config)
    visitor = AstVisitor(config=config)
    return_value = visitor.visit_function(func_ast, ctx)
    if func_ast.outputs or infer_scalar_return:
        if return_value is None:
            raise _LoweringError("Function body is empty", location=func_ast.location)
        block.add_op(func.ReturnOp(return_value))
    else:
        block.add_op(func.ReturnOp())
    return func_op


def build_func_op_from_ast(
    func_ast: FunctionAST,
    runtime_args: tuple[object, ...] | list[object] | None = None,
    config: dict[str, object] | None = None,
) -> func.FuncOp:
    from .ast_visitor import AstVisitorError

    try:
        return _build_func_op_from_ast_impl(func_ast, runtime_args=runtime_args, config=config)
    except _LoweringError as exc:
        raise AstVisitorError(str(exc), location=exc.location) from exc
