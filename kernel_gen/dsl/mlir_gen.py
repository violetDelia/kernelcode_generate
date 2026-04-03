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
import re
from typing import Callable

import sympy as sp
from xdsl.dialects import func
from xdsl.dialects.builtin import FunctionType, IntAttr, StringAttr, f32, i1, i32
from xdsl.ir import Block, Region

from kernel_gen.dialect.nn import NnMemoryType
from kernel_gen.dialect.symbol import SymbolValueType
from kernel_gen.symbol_variable.memory import Memory
from kernel_gen.symbol_variable.symbol_dim import SymbolDim

from .ast import (
    AstParseError,
    ArchLaunchKernelAST,
    BinaryExprAST,
    ConstAST,
    DmaAllocAST,
    DmaFlattenAST,
    DmaFreeAST,
    DmaReshapeAST,
    Diagnostic,
    FunctionAST,
    ScalarArgAST,
    SymbolToFloatAST,
    TensorAST,
    TensorAxisAccessAST,
    _ParseFailure,
    _parse_function_impl,
)
from .emit_mlir import (
    EmitContext,
    _LoweringError,
    _ensure_supported_statements,
    _expr_key,
    _infer_binary_memory_type,
    _infer_expr_type,
    _memory_to_nn_type,
)


def _is_symbol_scalar_function(func_ast: FunctionAST) -> bool:
    if not func_ast.inputs:
        return False
    if not all(isinstance(item, ScalarArgAST) and item.value_type is int for item in func_ast.inputs):
        return False
    if not func_ast.outputs:
        return True
    return all(isinstance(item, ScalarArgAST) and item.value_type in {int, bool, float} for item in func_ast.outputs)


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
    is_symbol_scalar_function = _is_symbol_scalar_function(func_ast)
    if runtime_args is not None and len(runtime_args) != len(func_ast.inputs):
        raise _LoweringError("runtime_args must align with func_ast inputs", location=func_ast.location)

    arg_types: list[object] = []
    type_map: dict[int, object] = {}
    tensor_input_count = 0
    for index, item in enumerate(func_ast.inputs):
        runtime_arg = None if runtime_args is None else runtime_args[index]
        if isinstance(item, TensorAST):
            runtime_memory = runtime_arg if isinstance(runtime_arg, Memory) else None
            arg_type = _memory_to_nn_type(runtime_memory or item.memory, location=item.location)
            tensor_input_count += 1
        elif isinstance(item, ScalarArgAST):
            if item.value_type is not int:
                raise _LoweringError("Unsupported scalar argument type", location=item.location)
            if runtime_args is not None:
                if not isinstance(runtime_arg, (int, SymbolDim)):
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
        statements = getattr(func_ast.body, "statements", None)
        if not statements:
            raise _LoweringError("At least one tensor input is required", location=func_ast.location)
    return arg_types, type_map


def _seed_input_symbol_aliases(
    ctx: EmitContext,
    func_ast: FunctionAST,
    block: Block,
) -> None:
    """为函数输入预灌参数名与 symbol expr 的双向别名。

    创建者: 金铲铲大作战
    最后一次更改: 金铲铲大作战

    功能说明:
    - 让 `ScalarArgAST` 在 `build_func_op_from_ast(...)` 路径中同时按参数名和 `!symbol.int<expr>` 文本被查到。
    - 为动态 `dma.slice/view/alloc` 这类通过结果 shape 反查 symbol 名称的 lowering 提供稳定绑定。

    使用示例:
    - _seed_input_symbol_aliases(ctx, func_ast, block)

    关联文件:
    - spec: [spec/dsl/mlir_gen.md](spec/dsl/mlir_gen.md)
    - test: [test/dsl/test_mlir_gen.py](test/dsl/test_mlir_gen.py)
    - 功能实现: [kernel_gen/dsl/mlir_gen.py](kernel_gen/dsl/mlir_gen.py)
    """

    block_args = tuple(block.args)
    for index, item in enumerate(func_ast.inputs):
        if index >= len(block_args):
            break
        block_arg = block_args[index]
        ctx.symbols.setdefault(item.name, block_arg)
        if isinstance(item, ScalarArgAST) and isinstance(block_arg.type, SymbolValueType):
            ctx.symbols.setdefault(block_arg.type.expr.expr.data, block_arg)


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


def _allow_mixed_dtype_return(
    return_expr: object,
    type_map: dict[int, object],
    result_type: NnMemoryType,
    expected_type: NnMemoryType,
) -> bool:
    """判断是否允许 mixed dtype promotion 的返回注解差异。

    创建者: 金铲铲大作战
    最后一次更改: 我不是牛马

    功能说明:
    - 仅在 return 表达式为 tensor 二元算术且左右 dtype 不一致时放宽。
    - 注解 element_type 必须来自左右操作数之一。
    - 要求推导出的目标类型与实际 result_type 对齐。

    使用示例:
    - _allow_mixed_dtype_return(return_expr, type_map, result_type, expected_type)

    关联文件:
    - spec: spec/dsl/mlir_gen.md
    - test: test/dsl/test_ast_visitor.py
    - 功能实现: kernel_gen/dsl/mlir_gen.py
    """
    if not isinstance(return_expr, BinaryExprAST):
        return False
    if return_expr.op not in {"add", "sub", "mul", "div", "floordiv"}:
        return False
    lhs_type = _infer_expr_type(return_expr.lhs, dict(type_map))
    rhs_type = _infer_expr_type(return_expr.rhs, dict(type_map))
    if not isinstance(lhs_type, NnMemoryType) or not isinstance(rhs_type, NnMemoryType):
        return False
    if lhs_type.element_type == rhs_type.element_type:
        return False
    if expected_type.element_type not in {lhs_type.element_type, rhs_type.element_type}:
        return False
    try:
        target_type = _infer_binary_memory_type(lhs_type, rhs_type, return_expr.location)
    except _LoweringError:
        return False
    return result_type.shape == target_type.shape and result_type.element_type == target_type.element_type


def _parse_symbolic_dim_expr(expr: str) -> sp.Basic | None:
    """解析符号维度表达式字符串。

    创建者: 小李飞刀
    最后一次更改: 小李飞刀

    功能说明:
    - 接受不含 `?` 的字符串并转为 sympy 表达式。
    - 解析失败时返回 None。

    使用示例:
    - _parse_symbolic_dim_expr("M*N*K")

    关联文件:
    - spec: spec/dsl/mlir_gen.md
    - test: test/dsl/test_ast_visitor.py
    - 功能实现: kernel_gen/dsl/mlir_gen.py
    """
    normalized = expr.strip()
    if not normalized or "?" in normalized:
        return None
    names = set(re.findall(r"[A-Za-z_][A-Za-z0-9_]*", normalized))
    locals_map = {name: sp.Symbol(name, integer=True, real=True) for name in names}
    try:
        return sp.sympify(normalized, locals=locals_map)
    except (sp.SympifyError, TypeError, ValueError):
        return None


def _flatten_numel_annotation_matches(result_type: NnMemoryType, expected_type: NnMemoryType) -> bool:
    """校验 flatten 返回注解的 numel 符号表达式等价性。

    创建者: 小李飞刀
    最后一次更改: 小李飞刀

    功能说明:
    - 仅在一维 shape 场景比较维度表达式是否等价。
    - 支持符号乘法的交换律判断。

    使用示例:
    - _flatten_numel_annotation_matches(result_type, expected_type)

    关联文件:
    - spec: spec/dsl/mlir_gen.md
    - test: test/dsl/test_ast_visitor.py
    - 功能实现: kernel_gen/dsl/mlir_gen.py
    """
    if len(result_type.shape.data) != 1 or len(expected_type.shape.data) != 1:
        return False
    lhs = result_type.shape.data[0]
    rhs = expected_type.shape.data[0]
    if isinstance(lhs, IntAttr) and isinstance(rhs, IntAttr):
        return lhs.data == rhs.data
    if isinstance(lhs, StringAttr) and isinstance(rhs, StringAttr):
        if lhs.data == rhs.data:
            return True
        lhs_expr = _parse_symbolic_dim_expr(lhs.data)
        rhs_expr = _parse_symbolic_dim_expr(rhs.data)
        if lhs_expr is None or rhs_expr is None:
            return False
        return sp.simplify(lhs_expr - rhs_expr) == 0
    return False


def _validate_return_type(
    func_ast: FunctionAST,
    result_type: object,
    return_expr: object | None = None,
    type_map: dict[int, object] | None = None,
) -> None:
    """校验函数返回类型与注解一致性。

    创建者: 我不是牛马
    最后一次更改: 小李飞刀

    功能说明:
    - 检查 Tensor 返回的 shape 与 element_type 是否匹配注解。
    - mixed dtype 场景下允许返回注解 element_type 与实际结果不同，但仅限二元算术。
    - 允许 `Memory.get_shape/get_stride()[axis]` 在 `-> int` 注解下返回 `!symbol.int`。
    - 允许 `return float(symbol.int)` 在 `-> float` 注解下返回 `f32`。

    使用示例:
    - _validate_return_type(func_ast, result_type, return_expr, type_map)

    关联文件:
    - spec: spec/dsl/mlir_gen.md
    - test: test/dsl/test_ast_visitor.py
    - 功能实现: kernel_gen/dsl/mlir_gen.py
    """
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
        shape_matches = result_type.shape == expected_type.shape
        if not shape_matches and isinstance(return_expr, DmaFlattenAST):
            shape_matches = _flatten_numel_annotation_matches(result_type, expected_type)
        if not shape_matches:
            raise _LoweringError("Return type does not match annotation", location=func_ast.location)
        if result_type.element_type != expected_type.element_type:
            if return_expr is not None and type_map is not None:
                if _allow_mixed_dtype_return(return_expr, type_map, result_type, expected_type):
                    return
            raise _LoweringError("Return type does not match annotation", location=func_ast.location)
        return
    elif isinstance(output, ScalarArgAST):
        if output.value_type is bool:
            expected_type = i1
        elif output.value_type is int:
            if isinstance(return_expr, TensorAxisAccessAST) and isinstance(result_type, SymbolValueType):
                return
            if not func_ast.inputs and isinstance(result_type, SymbolValueType):
                return
            if _is_symbol_scalar_function(func_ast):
                if isinstance(result_type, SymbolValueType):
                    return
                expected_type = SymbolValueType.from_expr(output.name)
            else:
                expected_type = i32
        elif output.value_type is float:
            if isinstance(return_expr, SymbolToFloatAST):
                expected_type = f32
            else:
                raise _LoweringError("Unsupported scalar return type", location=output.location)
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
    """从 Python 函数构建 MLIR `func.func`。

    创建者: 金铲铲大作战
    最后一次更改: 金铲铲大作战

    功能说明:
    - 解析 Python 函数为 `FunctionAST`，并生成 `func.FuncOp`。
    - 校验运行时参数数量，拒绝外部值引用。

    参数说明:
    - fn: 待解析的 Python 函数。
    - runtime_args: 与函数位置参数一一对应的运行时参数。
    - globals: 解析环境追加的全局变量（仅用于解析，不参与签名推导）。
    - builtins: 解析环境的内建对象覆盖（可为 dict 或内建模块对象）。

    返回说明:
    - 返回构建完成的 `func.FuncOp`。

    限制与异常:
    - 运行时参数数量不匹配会抛出 `AstVisitorError`。
    - 解析或下沉失败会抛出 `AstVisitorError`。

    使用示例:
    - func_op = build_func_op(fn, *runtime_args)

    关联文件:
    - spec: [spec/dsl/mlir_gen.md](spec/dsl/mlir_gen.md)
    - test: [test/dsl/test_ast_visitor.py](test/dsl/test_ast_visitor.py)
    - 功能实现: [kernel_gen/dsl/mlir_gen.py](kernel_gen/dsl/mlir_gen.py)
    """
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
    runtime_values: dict[str, object] | None = None
    if runtime_args is not None:
        runtime_values = {
            input_arg.name: runtime_args[index]
            for index, input_arg in enumerate(func_ast.inputs)
            if isinstance(input_arg, ScalarArgAST)
        }
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
            result_type = _infer_expr_type(return_expr, dict(type_map), runtime_values=runtime_values)
        _validate_return_type(func_ast, result_type, return_expr, dict(type_map))
        type_map[_expr_key(return_expr)] = result_type
        result_types = [result_type]
    elif _is_symbol_scalar_function(func_ast):
        return_expr = statements[-1]
        if isinstance(return_expr, (DmaFreeAST, ArchLaunchKernelAST)):
            result_types = []
        else:
            result_type = _infer_expr_type(return_expr, dict(type_map), runtime_values=runtime_values)
            if not isinstance(result_type, SymbolValueType):
                raise _LoweringError(
                    "Symbol scalar function return must lower to !symbol.int",
                    location=func_ast.location,
                )
            result_types = [result_type]
            infer_scalar_return = True

    func_type = FunctionType.from_lists(arg_types, result_types)
    block = Block(arg_types=arg_types)
    func_op = func.FuncOp(func_ast.name, func_type, Region(block))

    ctx = EmitContext(builder=block, symbols={}, types=dict(type_map), config=config)
    _seed_input_symbol_aliases(ctx, func_ast, block)
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
    """从 `FunctionAST` 生成 MLIR `func.func`。

    创建者: 金铲铲大作战
    最后一次更改: 金铲铲大作战

    功能说明:
    - 调用内部构建流程生成 `func.FuncOp`。
    - 将 `_LoweringError` 统一转换为 `AstVisitorError`。

    参数说明:
    - func_ast: 已解析的函数 AST。
    - runtime_args: 运行时参数，用于推导标量类型/符号表达式。
    - config: 构建配置（例如外部值拒绝策略）。

    返回说明:
    - 返回构建完成的 `func.FuncOp`。

    限制与异常:
    - 语义检查或下沉失败会抛出 `AstVisitorError`。

    使用示例:
    - func_op = build_func_op_from_ast(func_ast, runtime_args=runtime_args)

    关联文件:
    - spec: [spec/dsl/mlir_gen.md](spec/dsl/mlir_gen.md)
    - test: [test/dsl/test_mlir_gen.py](test/dsl/test_mlir_gen.py)
    - 功能实现: [kernel_gen/dsl/mlir_gen.py](kernel_gen/dsl/mlir_gen.py)
    """
    from .ast_visitor import AstVisitorError

    try:
        return _build_func_op_from_ast_impl(func_ast, runtime_args=runtime_args, config=config)
    except _LoweringError as exc:
        raise AstVisitorError(str(exc), location=exc.location) from exc
