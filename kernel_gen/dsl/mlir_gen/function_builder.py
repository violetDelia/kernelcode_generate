"""mlir_gen function builder.

创建者: 朽木露琪亚
最后一次更改: 金铲铲大作战

功能说明:
- 提供 build_func_op/build_func_op_from_ast 的公开入口。
- 负责函数签名、返回类型与函数体装配，不处理 module 组装。

API 列表:
- build_func_op(fn, *runtime_args)
- build_func_op_from_ast(func_ast, runtime_args=None, config=None)

使用示例:
- func_op = build_func_op(fn, *runtime_args)
- func_op = build_func_op_from_ast(func_ast, runtime_args=[...])

关联文件:
- spec: [spec/dsl/mlir_gen.md](spec/dsl/mlir_gen.md)
- test: [test/dsl/mlir_gen/test_function_builder.py](test/dsl/mlir_gen/test_function_builder.py)
- 功能实现: [kernel_gen/dsl/mlir_gen/function_builder.py](kernel_gen/dsl/mlir_gen/function_builder.py)
"""

from __future__ import annotations

import inspect
import re
from collections.abc import Callable

import sympy as sp

from xdsl.dialects import func
from xdsl.dialects.builtin import ArrayAttr, FunctionType, IntAttr, StringAttr, f32, i1, i8, i32
from xdsl.ir import Block, Region

from kernel_gen.dialect.arch import ArchGetDynamicMemoryOp
from kernel_gen.dialect.nn import NnMemoryType
from kernel_gen.dialect.symbol import SymbolValueType
from kernel_gen.dsl.ast import (
    ArchBarrierAST,
    ArchLaunchKernelAST,
    BinaryExprAST,
    AstParseError,
    DmaAllocAST,
    DmaFlattenAST,
    DmaFreeAST,
    DmaViewAST,
    ForAST,
    FunctionAST,
    NnReduceAST,
    ScalarArgAST,
    StoreAST,
    SymbolToFloatAST,
    TensorAST,
    TensorAxisAccessAST,
    VarAST,
)
from kernel_gen.dsl.ast.parser import parse_function_with_env
from kernel_gen.dsl.ast.visitor import AstVisitor, AstVisitorError
from kernel_gen.dsl.mlir_gen.emit import EmitContext, memory_type_from_memory
from kernel_gen.dsl.mlir_gen.emit.context import LoweringError
from kernel_gen.symbol_variable.memory import Memory
from kernel_gen.symbol_variable.symbol_dim import SymbolDim
from kernel_gen.symbol_variable.type import NumericType

_DYNAMIC_MEMORY_SYMBOL_NAMES = {
    "shared": "SM_SIZE",
    "local": "LM_SIZE",
    "tsm": "TSM_SIZE",
    "tlm1": "TLM1_SIZE",
    "tlm2": "TLM2_SIZE",
    "tlm3": "TLM3_SIZE",
}

_ARITHMETIC_DTYPE_RANK = {
    NumericType.Bool: 0,
    NumericType.Int8: 1,
    NumericType.Uint8: 2,
    NumericType.Int16: 3,
    NumericType.Uint16: 4,
    NumericType.Int32: 5,
    NumericType.Uint32: 6,
    NumericType.Int64: 7,
    NumericType.Uint64: 8,
    NumericType.Float16: 9,
    NumericType.BFloat16: 10,
    NumericType.Float32: 11,
    NumericType.Float64: 12,
}


def _expr_key(expr: object) -> int:
    """为 AST 节点生成稳定缓存键。

    创建者: 金铲铲大作战
    最后一次更改: 金铲铲大作战

    功能说明:
    - 当前直接使用 `id(expr)` 作为单次构建流程内的缓存键。

    使用示例:
    - key = _expr_key(expr)

    关联文件:
    - spec: [spec/dsl/mlir_gen.md](spec/dsl/mlir_gen.md)
    - test: [test/dsl/mlir_gen/test_function_builder.py](test/dsl/mlir_gen/test_function_builder.py)
    - 功能实现: [kernel_gen/dsl/mlir_gen/function_builder.py](kernel_gen/dsl/mlir_gen/function_builder.py)
    """

    return id(expr)


def _parse_symbolic_dim_expr(expr: str) -> sp.Basic | None:
    """解析符号维度表达式字符串。

    创建者: 金铲铲大作战
    最后一次更改: 金铲铲大作战

    功能说明:
    - 使用最小 sympy 规整逻辑支持符号表达式等价性比较。

    使用示例:
    - _parse_symbolic_dim_expr("M * N")

    关联文件:
    - spec: [spec/dsl/mlir_gen.md](spec/dsl/mlir_gen.md)
    - test: [test/dsl/mlir_gen/test_function_builder.py](test/dsl/mlir_gen/test_function_builder.py)
    - 功能实现: [kernel_gen/dsl/mlir_gen/function_builder.py](kernel_gen/dsl/mlir_gen/function_builder.py)
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


def _dtype_from_xdsl(element_type: object, location: object | None) -> NumericType:
    """将 xDSL element_type 规整为 NumericType。"""

    if element_type == f32:
        return NumericType.Float32
    if element_type == i1:
        return NumericType.Bool
    if element_type == i32:
        return NumericType.Int32
    raise LoweringError("Return type does not match annotation", location=location)


def _resolve_symbolic_index_value(
    expr: object,
    *,
    location: object | None = None,
    runtime_values: dict[str, object] | None = None,
) -> int | SymbolDim:
    """解析静态 index 表达式为 `int|SymbolDim`。"""

    if isinstance(expr, IntAttr):
        return expr.data
    if hasattr(expr, "value") and isinstance(getattr(expr, "value", None), int):
        return getattr(expr, "value")
    if hasattr(expr, "value") and isinstance(getattr(expr, "value", None), str):
        return SymbolDim(getattr(expr, "value"))
    if isinstance(expr, VarAST):
        if runtime_values is not None and expr.name in runtime_values:
            runtime_value = runtime_values[expr.name]
            if isinstance(runtime_value, (int, SymbolDim)):
                return runtime_value
        return SymbolDim(expr.name)
    if isinstance(expr, ScalarArgAST):
        if runtime_values is not None and expr.name in runtime_values:
            runtime_value = runtime_values[expr.name]
            if isinstance(runtime_value, (int, SymbolDim)):
                return runtime_value
        return SymbolDim(expr.name)
    if isinstance(expr, BinaryExprAST):
        lhs = _resolve_symbolic_index_value(expr.lhs, location=location, runtime_values=runtime_values)
        rhs = _resolve_symbolic_index_value(expr.rhs, location=location, runtime_values=runtime_values)
        if expr.op == "add":
            return lhs + rhs
        if expr.op == "sub":
            return lhs - rhs
        if expr.op == "mul":
            return lhs * rhs
        if expr.op == "div":
            return lhs / rhs
        if expr.op == "floordiv":
            return lhs // rhs
        raise LoweringError("Unsupported index expression", location=location)
    if isinstance(expr, int):
        return expr
    if isinstance(expr, str):
        return SymbolDim(expr)
    raise LoweringError("Unsupported index expression", location=location or getattr(expr, "location", None))


def _resolve_static_index_expr(
    expr: object,
    location: object | None = None,
    runtime_values: dict[str, object] | None = None,
) -> int | str:
    """解析静态 index 表达式为 `int|str`。"""

    value = _resolve_symbolic_index_value(expr, location=location, runtime_values=runtime_values)
    if isinstance(value, SymbolDim):
        normalized = value.get_value()
        if not isinstance(normalized, (int, str)):
            raise LoweringError("Unsupported index expression", location=location or getattr(expr, "location", None))
        return normalized
    return value


def _build_default_stride(shape: list[int | str]) -> list[int | str]:
    """按行主序构造默认 stride。"""

    stride: list[int | str] = [1] * len(shape)
    running: int | str = 1
    for index in range(len(shape) - 1, -1, -1):
        stride[index] = running
        dim = shape[index]
        if index == 0:
            continue
        if isinstance(running, int) and isinstance(dim, int):
            running *= dim
        else:
            running = f"{dim}*{running}" if running != 1 else str(dim)
    return stride


def _is_symbol_scalar_function(func_ast: FunctionAST) -> bool:
    """判断是否为纯 symbol 标量函数。"""

    if not func_ast.inputs:
        return False
    if not all(isinstance(item, ScalarArgAST) and item.value_type is int for item in func_ast.inputs):
        return False
    if not func_ast.outputs:
        return True
    return all(isinstance(item, ScalarArgAST) and item.value_type in {int, bool, float} for item in func_ast.outputs)


def _is_symbol_scalar_arg(item: ScalarArgAST, *, is_symbol_scalar_function: bool) -> bool:
    """判断标量参数是否走 symbol 语义。"""

    return is_symbol_scalar_function or item.is_symbolic


def _symbol_expr_from_runtime_arg(runtime_arg: object) -> str | None:
    """从 runtime 参数提取 symbol 文本。"""

    if isinstance(runtime_arg, SymbolDim):
        return str(runtime_arg.get_symbol())
    if isinstance(runtime_arg, int):
        return str(runtime_arg)
    return None


def _build_runtime_args_required_error(func_name: str, expected: int, actual: int) -> str:
    """构造公开 `runtime_args` 缺失错误短语。

    创建者: 金铲铲大作战
    最后一次更改: 金铲铲大作战

    功能说明:
    - 统一 `build_func_op(...)` / `build_func_op_from_ast(...)` 的显式运行时参数缺失报错。

    使用示例:
    - reason = _build_runtime_args_required_error("kernel", 1, 0)

    关联文件:
    - spec: [spec/dsl/mlir_gen.md](spec/dsl/mlir_gen.md)
    - test: [test/dsl/mlir_gen/test_signature.py](test/dsl/mlir_gen/test_signature.py)
    - 功能实现: [kernel_gen/dsl/mlir_gen/function_builder.py](kernel_gen/dsl/mlir_gen/function_builder.py)
    """

    return f"build_func_op requires explicit runtime args for {func_name}: expected {expected}, got {actual}"


def _raise_build_error_from_parse_error(
    exc: AstParseError,
    *,
    value_messages: tuple[str, ...] = (),
) -> None:
    """把 parser 公开错误翻译为 builder 公开错误合同。

    创建者: 金铲铲大作战
    最后一次更改: 金铲铲大作战

    功能说明:
    - 命中 `value_messages` 时保持 `ValueError` 口径。
    - `space/dtype` 参数错误时保持 `TypeError` 口径。
    - 其余解析失败统一落到 `AstVisitorError`。

    使用示例:
    - _raise_build_error_from_parse_error(exc, value_messages=("x",))

    关联文件:
    - spec: [spec/dsl/mlir_gen.md](spec/dsl/mlir_gen.md)
    - test: [test/dsl/mlir_gen/test_function_builder.py](test/dsl/mlir_gen/test_function_builder.py)
    - 功能实现: [kernel_gen/dsl/mlir_gen/function_builder.py](kernel_gen/dsl/mlir_gen/function_builder.py)
    """

    location = exc.diagnostics[0].location if exc.diagnostics else None
    if exc.message in value_messages:
        raise ValueError(exc.message) from exc
    if exc.message.endswith("space must be MemorySpace") or exc.message == "cast dtype must be NumericType":
        raise TypeError(exc.message) from exc
    raise AstVisitorError(exc.message, location=location) from exc


def _is_dma_alloc_only_function(func_ast: FunctionAST) -> bool:
    """判断函数体是否仅包含 dma.alloc 返回。"""

    statements = func_ast.body.statements
    if len(func_ast.outputs) != 1 or not statements:
        return False
    if not isinstance(func_ast.outputs[0], TensorAST):
        return False
    return isinstance(statements[-1], DmaAllocAST)


def _resolve_runtime_shape_value(
    value: int | str,
    runtime_values: dict[str, object] | None,
) -> int | str:
    """按公开 `runtime_args` 解析 shape 注解维度。

    创建者: 金铲铲大作战
    最后一次更改: 金铲铲大作战

    功能说明:
    - 直接符号名优先读取 `runtime_values`。
    - 对简单符号表达式做最小替换与规整，保证返回注解可按公开 runtime 参数落到静态 shape。

    使用示例:
    - dim = _resolve_runtime_shape_value("size", {"size": 4})

    关联文件:
    - spec: [spec/dsl/mlir_gen.md](spec/dsl/mlir_gen.md)
    - test: [test/dsl/mlir_gen/test_signature.py](test/dsl/mlir_gen/test_signature.py)
    - 功能实现: [kernel_gen/dsl/mlir_gen/function_builder.py](kernel_gen/dsl/mlir_gen/function_builder.py)
    """

    if runtime_values is None or not isinstance(value, str):
        return value
    runtime_value = runtime_values.get(value)
    if isinstance(runtime_value, int):
        return runtime_value
    if isinstance(runtime_value, SymbolDim):
        public_value = runtime_value.get_value()
        if isinstance(public_value, (int, str)):
            return public_value
    parsed = _parse_symbolic_dim_expr(value)
    if parsed is None:
        return value
    substitutions: dict[sp.Symbol, object] = {}
    for symbol in sorted(parsed.free_symbols, key=lambda item: item.name):
        symbol_name = symbol.name
        if symbol_name not in runtime_values:
            return value
        runtime_value = runtime_values[symbol_name]
        if isinstance(runtime_value, SymbolDim):
            runtime_value = runtime_value.get_value()
        if isinstance(runtime_value, int):
            substitutions[symbol] = runtime_value
            continue
        if isinstance(runtime_value, str):
            inner_expr = _parse_symbolic_dim_expr(runtime_value)
            if inner_expr is None:
                substitutions[symbol] = sp.Symbol(runtime_value, integer=True, real=True)
            else:
                substitutions[symbol] = inner_expr
            continue
        return value
    resolved = sp.simplify(parsed.subs(substitutions))
    if getattr(resolved, "free_symbols", None):
        return str(resolved).replace(" ", "")
    if getattr(resolved, "is_integer", False):
        return int(resolved)
    return str(resolved).replace(" ", "")


def _build_expected_tensor_return_type(
    output: TensorAST,
    runtime_values: dict[str, object] | None,
) -> NnMemoryType:
    """构造返回注解对应的期望 tensor 类型。

    创建者: 金铲铲大作战
    最后一次更改: 金铲铲大作战

    功能说明:
    - 在公开 `runtime_args` 已知时，先把返回注解中的动态 shape 维度落成静态值。
    - 保持 element_type / space 与原注解一致，只收口 shape 对齐。

    使用示例:
    - expected = _build_expected_tensor_return_type(func_ast.outputs[0], {"size": 4})

    关联文件:
    - spec: [spec/dsl/mlir_gen.md](spec/dsl/mlir_gen.md)
    - test: [test/dsl/mlir_gen/test_signature.py](test/dsl/mlir_gen/test_signature.py)
    - 功能实现: [kernel_gen/dsl/mlir_gen/function_builder.py](kernel_gen/dsl/mlir_gen/function_builder.py)
    """

    resolved_shape = [
        _resolve_runtime_shape_value(dim, runtime_values)
        for dim in output.memory.get_shape()
    ]
    return memory_type_from_memory(
        Memory(
            resolved_shape,
            output.memory.dtype,
            space=output.memory.space,
        )
    )


def _build_signature_types(
    func_ast: FunctionAST,
    runtime_args: tuple[object, ...] | list[object] | None = None,
    *,
    allow_dma_alloc_only: bool = False,
) -> tuple[list[object], dict[int, object]]:
    """根据 runtime_args 与 AST 生成函数参数类型。"""

    is_symbol_scalar_function = _is_symbol_scalar_function(func_ast)
    if runtime_args is not None and len(runtime_args) != len(func_ast.inputs):
        raise LoweringError("runtime_args must align with func_ast inputs", location=func_ast.location)

    arg_types: list[object] = []
    type_map: dict[int, object] = {}
    tensor_input_count = 0
    for index, item in enumerate(func_ast.inputs):
        runtime_arg = None if runtime_args is None else runtime_args[index]
        if isinstance(item, TensorAST):
            runtime_memory = runtime_arg if isinstance(runtime_arg, Memory) else None
            arg_type = memory_type_from_memory(runtime_memory or item.memory)
            tensor_input_count += 1
        elif isinstance(item, ScalarArgAST):
            if item.value_type is not int:
                raise LoweringError("Unsupported scalar argument type", location=item.location)
            if runtime_args is not None and not isinstance(runtime_arg, (int, SymbolDim)):
                raise LoweringError("Unsupported scalar argument type", location=item.location)
            runtime_expr = _symbol_expr_from_runtime_arg(runtime_arg)
            if allow_dma_alloc_only:
                arg_type = SymbolValueType.from_expr(runtime_expr or item.name)
            elif runtime_expr is not None and (is_symbol_scalar_function or isinstance(runtime_arg, SymbolDim)):
                arg_type = SymbolValueType.from_expr(runtime_expr)
            elif _is_symbol_scalar_arg(item, is_symbol_scalar_function=is_symbol_scalar_function):
                arg_type = SymbolValueType.from_expr(item.name)
            else:
                arg_type = i32
        else:
            raise LoweringError("Unsupported input type", location=getattr(item, "location", None))
        arg_types.append(arg_type)
        type_map[_expr_key(item)] = arg_type

    if func_ast.inputs and tensor_input_count == 0 and not is_symbol_scalar_function and not allow_dma_alloc_only:
        statements = getattr(func_ast.body, "statements", None)
        if not statements:
            raise LoweringError("At least one tensor input is required", location=func_ast.location)
    return arg_types, type_map


def _shape_annotation_matches(result_type: NnMemoryType, expected_type: NnMemoryType) -> bool:
    """校验 tensor 返回 shape 是否在符号语义上等价。"""

    result_shape = result_type.shape.data
    expected_shape = expected_type.shape.data
    if len(result_shape) != len(expected_shape):
        return False
    for lhs, rhs in zip(result_shape, expected_shape, strict=True):
        if isinstance(lhs, IntAttr) and isinstance(rhs, IntAttr):
            if lhs.data != rhs.data:
                return False
            continue
        if isinstance(lhs, StringAttr) and isinstance(rhs, StringAttr):
            if lhs.data == rhs.data:
                continue
            lhs_expr = _parse_symbolic_dim_expr(lhs.data)
            rhs_expr = _parse_symbolic_dim_expr(rhs.data)
            if lhs_expr is None or rhs_expr is None or sp.simplify(lhs_expr - rhs_expr) != 0:
                return False
            continue
        return False
    return True


def _flatten_numel_annotation_matches(result_type: NnMemoryType, expected_type: NnMemoryType) -> bool:
    """校验 flatten 返回注解的 numel 表达式等价性。"""

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


def _allow_mixed_dtype_return(
    return_expr: object,
    type_map: dict[int, object],
    result_type: NnMemoryType,
    expected_type: NnMemoryType,
) -> bool:
    """判断是否允许 mixed dtype promotion 的返回注解差异。"""

    if not isinstance(return_expr, BinaryExprAST):
        return False
    if return_expr.op not in {"add", "sub", "mul", "div", "floordiv"}:
        return False
    lhs_type = type_map.get(_expr_key(return_expr.lhs))
    rhs_type = type_map.get(_expr_key(return_expr.rhs))
    if not isinstance(lhs_type, NnMemoryType) or not isinstance(rhs_type, NnMemoryType):
        return False
    if lhs_type.element_type == rhs_type.element_type:
        return False
    if expected_type.element_type not in {lhs_type.element_type, rhs_type.element_type}:
        return False
    return result_type.shape == expected_type.shape and result_type.element_type != expected_type.element_type


def _validate_return_type(
    func_ast: FunctionAST,
    result_type: object,
    return_expr: object | None = None,
    type_map: dict[int, object] | None = None,
    runtime_values: dict[str, object] | None = None,
) -> None:
    """校验函数返回类型与注解一致性。"""

    if not func_ast.outputs:
        return
    if len(func_ast.outputs) != 1:
        raise LoweringError("Only single return value is supported", location=func_ast.location)
    output = func_ast.outputs[0]
    if isinstance(output, TensorAST):
        expected_type = _build_expected_tensor_return_type(output, runtime_values)
        if not isinstance(result_type, NnMemoryType):
            raise LoweringError("Return type does not match annotation", location=func_ast.location)
        shape_matches = _shape_annotation_matches(result_type, expected_type)
        if not shape_matches and isinstance(return_expr, DmaFlattenAST):
            shape_matches = _flatten_numel_annotation_matches(result_type, expected_type)
        if not shape_matches:
            raise LoweringError("Return type does not match annotation", location=func_ast.location)
        if result_type.element_type != expected_type.element_type:
            if return_expr is not None and type_map is not None:
                if _allow_mixed_dtype_return(return_expr, type_map, result_type, expected_type):
                    return
            raise LoweringError("Return type does not match annotation", location=func_ast.location)
        return
    if isinstance(output, ScalarArgAST):
        if output.value_type is bool:
            expected_type = i1
        elif output.value_type is int:
            if isinstance(return_expr, TensorAxisAccessAST) and isinstance(result_type, SymbolValueType):
                return
            if _is_symbol_scalar_function(func_ast):
                if isinstance(result_type, SymbolValueType):
                    return
                expected_type = SymbolValueType.from_expr(output.name)
            else:
                expected_type = i32
        elif output.value_type is float and isinstance(return_expr, SymbolToFloatAST):
            expected_type = f32
        else:
            raise LoweringError("Unsupported scalar return type", location=output.location)
        if result_type != expected_type:
            raise LoweringError("Return type does not match annotation", location=func_ast.location)
        return
    raise LoweringError("Unsupported return annotation type", location=getattr(output, "location", None))


def _function_has_value_return(func_ast: FunctionAST) -> bool:
    """判断函数是否应装配单返回值。"""

    if func_ast.returns_none:
        return False
    if func_ast.outputs:
        return True
    return func_ast.has_explicit_return


def _is_zero_return_statement_expr(expr: object) -> bool:
    """判断表达式是否属于语句型零返回函数体。"""

    return isinstance(expr, (DmaFreeAST, StoreAST, ForAST, ArchBarrierAST, ArchLaunchKernelAST))


def _ensure_supported_statements(function_ast: FunctionAST) -> list[object]:
    """确保函数体非空并返回语句列表。"""

    statements = function_ast.body.statements
    if not statements:
        raise LoweringError("Function body is empty", location=function_ast.location)
    return statements


def _parse_reduce_axis_expr(axis_expr: object | None, location: object | None) -> list[int] | None:
    """解析 reduce 的 axis 表达式为轴列表。"""

    if axis_expr is None:
        return None
    if hasattr(axis_expr, "value") and isinstance(getattr(axis_expr, "value", None), int):
        return [getattr(axis_expr, "value")]
    if isinstance(axis_expr, int):
        return [axis_expr]
    if isinstance(axis_expr, (list, tuple)):
        axes: list[int] = []
        for entry in axis_expr:
            if hasattr(entry, "value") and isinstance(getattr(entry, "value", None), int):
                axes.append(getattr(entry, "value"))
                continue
            if isinstance(entry, int):
                axes.append(entry)
                continue
            raise LoweringError("reduce axis must be int", location=getattr(entry, "location", None) or location)
        return axes
    raise LoweringError("reduce axis must be int or list of int", location=location)


def _rewrite_dynamic_memory_result_types(func_op: func.FuncOp) -> None:
    """把动态内存入口的结果类型规整为固定 SymbolDim 名称。

    创建者: 朽木露琪亚
    最后一次更改: 朽木露琪亚

    功能说明:
    - 将 `arch.get_dynamic_memory` 的结果类型形状从 `?` 统一为 `SM_SIZE/LM_SIZE/...`。
    - 同步更新 `func.func` 的返回类型，保证 compare 输出一致。

    使用示例:
    - _rewrite_dynamic_memory_result_types(func_op)

    关联文件:
    - spec: [spec/dsl/mlir_gen.md](spec/dsl/mlir_gen.md)
    - test: [test/dsl/mlir_gen/test_function_builder.py](test/dsl/mlir_gen/test_function_builder.py)
    - 功能实现: [kernel_gen/dsl/mlir_gen/function_builder.py](kernel_gen/dsl/mlir_gen/function_builder.py)
    """

    changed = False
    for op in func_op.walk():
        if not isinstance(op, ArchGetDynamicMemoryOp):
            continue
        space_name = op.memory_space.space.data
        symbol_name = _DYNAMIC_MEMORY_SYMBOL_NAMES.get(space_name)
        if symbol_name is None:
            continue
        result_type = op.result.type
        if not isinstance(result_type, NnMemoryType):
            continue
        desired_shape = [StringAttr(symbol_name)]
        if list(result_type.shape.data) == desired_shape:
            continue
        new_type = NnMemoryType(
            ArrayAttr(desired_shape),
            ArrayAttr([IntAttr(1)]),
            result_type.element_type or i8,
            op.memory_space,
        )
        op.result._type = new_type
        changed = True
    if changed:
        func_op.update_function_type()


def _resolve_static_index_list(
    value: object,
    runtime_values: dict[str, object] | None,
) -> list[int | str]:
    """解析静态 index 列表为 `int | str` 列表。

    创建者: 朽木露琪亚
    最后一次更改: 朽木露琪亚

    功能说明:
    - 支持 list/tuple 或单值输入。
    - 借助 `_resolve_static_index_expr` 处理 `ConstAST/ScalarArgAST/VarAST`。

    使用示例:
    - values = _resolve_static_index_list([ConstAST(0), ConstAST(2)], runtime_values)

    关联文件:
    - spec: [spec/dsl/mlir_gen.md](spec/dsl/mlir_gen.md)
    - test: [test/dsl/mlir_gen/test_function_builder.py](test/dsl/mlir_gen/test_function_builder.py)
    - 功能实现: [kernel_gen/dsl/mlir_gen/function_builder.py](kernel_gen/dsl/mlir_gen/function_builder.py)
    """

    if isinstance(value, (list, tuple)):
        entries = value
    else:
        entries = [value]
    return [_resolve_static_index_expr(entry, runtime_values=runtime_values) for entry in entries]


def _maybe_validate_dma_view_bounds(
    func_ast: FunctionAST,
    runtime_args: tuple[object, ...] | list[object] | None,
) -> None:
    """对静态 `dma.view` 进行越界预检。

    创建者: 朽木露琪亚
    最后一次更改: 朽木露琪亚

    功能说明:
    - 若 `dma.view` 的输入 shape 与 offset/size/stride 均为静态整数，提前判定越界。
    - 命中越界时抛 `ValueError`，避免进入 MLIR compare。

    使用示例:
    - _maybe_validate_dma_view_bounds(func_ast, runtime_args)

    关联文件:
    - spec: [spec/dsl/mlir_gen.md](spec/dsl/mlir_gen.md)
    - test: [test/dsl/mlir_gen/test_function_builder.py](test/dsl/mlir_gen/test_function_builder.py)
    - 功能实现: [kernel_gen/dsl/mlir_gen/function_builder.py](kernel_gen/dsl/mlir_gen/function_builder.py)
    """

    if runtime_args is None:
        return
    runtime_values = {
        input_arg.name: runtime_args[index]
        for index, input_arg in enumerate(func_ast.inputs)
        if isinstance(input_arg, ScalarArgAST)
    }
    runtime_memories = {
        input_arg.name: runtime_args[index]
        for index, input_arg in enumerate(func_ast.inputs)
        if isinstance(input_arg, TensorAST)
    }
    statements = getattr(func_ast.body, "statements", ()) or ()
    for stmt in statements:
        if not isinstance(stmt, DmaViewAST):
            continue
        source_name = getattr(stmt.source, "name", None)
        if source_name is None or source_name not in runtime_memories:
            continue
        source_memory = runtime_memories[source_name]
        if not isinstance(source_memory, Memory):
            continue
        shape_values = source_memory.shape.get_values()
        source_stride = source_memory.stride.get_values() if source_memory.stride is not None else None
        if source_stride is None:
            continue
        if not all(isinstance(value, int) for value in shape_values):
            continue
        if not all(isinstance(value, int) for value in source_stride):
            continue
        offsets = _resolve_static_index_list(stmt.offset, runtime_values)
        sizes = _resolve_static_index_list(stmt.size, runtime_values)
        strides = _resolve_static_index_list(stmt.stride, runtime_values)
        if not all(isinstance(value, int) for value in offsets + sizes + strides):
            continue
        source_numel = 1
        for dim in shape_values:
            source_numel *= dim
        linear_start = 0
        linear_extent = 0
        for offset, size, stride, source_step in zip(offsets, sizes, strides, source_stride):
            if stride <= 0:
                raise ValueError("Invalid stride")
            linear_start += offset * source_step
            linear_extent += (size - 1) * stride
        if linear_start + linear_extent >= source_numel:
            raise ValueError("Index out of bounds")


def _seed_input_symbol_aliases(ctx: EmitContext, func_ast: FunctionAST, block: Block) -> None:
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
    - test: [test/dsl/mlir_gen/test_function_builder.py](test/dsl/mlir_gen/test_function_builder.py)
    - 功能实现: [kernel_gen/dsl/mlir_gen/function_builder.py](kernel_gen/dsl/mlir_gen/function_builder.py)
    """

    block_args = tuple(block.args)
    for index, item in enumerate(func_ast.inputs):
        if index >= len(block_args):
            break
        block_arg = block_args[index]
        ctx.symbols.setdefault(item.name, block_arg)
        if isinstance(item, ScalarArgAST) and isinstance(block_arg.type, SymbolValueType):
            ctx.symbols.setdefault(block_arg.type.expr.expr.data, block_arg)


def _build_parse_environment_for_function(
    fn: Callable[..., object],
    runtime_table: dict[str, object],
) -> tuple[dict[str, object], dict[str, object]]:
    """构造 `build_func_op(...)` 解析阶段使用的环境表。

    创建者: jcc你莫辜负
    最后一次更改: jcc你莫辜负

    功能说明:
    - 以 `fn.__globals__` 与闭包非局部变量为基础环境。
    - 再注入 `runtime_table`，保证公开 `runtime_args` 始终覆盖同名解析环境符号。
    - builtins 只从函数当前 `__builtins__` 绑定推导，不再通过公开参数覆写。

    使用示例:
    - globals_table, builtins_table = _build_parse_environment_for_function(fn, runtime_table)

    关联文件:
    - spec: [spec/dsl/mlir_gen.md](spec/dsl/mlir_gen.md)
    - test: [test/dsl/mlir_gen/test_function_builder.py](test/dsl/mlir_gen/test_function_builder.py)
    - 功能实现: [kernel_gen/dsl/mlir_gen/function_builder.py](kernel_gen/dsl/mlir_gen/function_builder.py)
    """

    globals_table = dict(getattr(fn, "__globals__", {}) or {})
    globals_table.update(inspect.getclosurevars(fn).nonlocals)
    globals_table.update(runtime_table)
    builtins_obj = globals_table.get("__builtins__", {})
    if isinstance(builtins_obj, dict):
        builtins_table = builtins_obj
    else:
        builtins_table = getattr(builtins_obj, "__dict__", {})
    return globals_table, builtins_table


def build_func_op(
    fn: Callable[..., object],
    *runtime_args: object,
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

    返回说明:
    - 返回构建完成的 `func.FuncOp`。

    限制与异常:
    - 运行时参数数量不匹配会抛出 `AstVisitorError`。
    - `slice/cast/alloc` 等前端参数类型错误会按公开合同抛出 `TypeError`。
    - 其余解析或下沉失败会抛出 `AstVisitorError`。

    使用示例:
    - func_op = build_func_op(fn, *runtime_args)

    关联文件:
    - spec: [spec/dsl/mlir_gen.md](spec/dsl/mlir_gen.md)
    - test: [test/dsl/mlir_gen/test_function_builder.py](test/dsl/mlir_gen/test_function_builder.py)
    - 功能实现: [kernel_gen/dsl/mlir_gen/function_builder.py](kernel_gen/dsl/mlir_gen/function_builder.py)
    """

    signature = inspect.signature(fn)
    positional_params = [
        param
        for param in signature.parameters.values()
        if param.kind in (inspect.Parameter.POSITIONAL_ONLY, inspect.Parameter.POSITIONAL_OR_KEYWORD)
    ]
    if len(runtime_args) != len(positional_params):
        reason = _build_runtime_args_required_error(fn.__name__, len(positional_params), len(runtime_args))
        raise AstVisitorError(reason, location=None)

    runtime_table = {param.name: runtime_args[index] for index, param in enumerate(positional_params)}
    globals_table, builtins_table = _build_parse_environment_for_function(fn, runtime_table)

    try:
        func_ast = parse_function_with_env(
            fn,
            globals_table=globals_table,
            builtins_table=builtins_table,
            runtime_table=runtime_table,
            config={"reject_external_values": True},
        )
    except AstParseError as exc:
        _raise_build_error_from_parse_error(
            exc,
            value_messages=(),
        )
    return build_func_op_from_ast(func_ast, runtime_args=runtime_args)


def _build_func_op_from_ast_impl(
    func_ast: FunctionAST,
    runtime_args: tuple[object, ...] | list[object] | None = None,
    config: dict[str, object] | None = None,
) -> func.FuncOp:
    """内部实现：从 FunctionAST 构建 func.FuncOp。

    创建者: 朽木露琪亚
    最后一次更改: 金铲铲大作战

    功能说明:
    - 统一签名推导、返回类型校验与函数体装配。
    - 仅处理函数级入口，不做 module 组装。

    使用示例:
    - func_op = _build_func_op_from_ast_impl(func_ast, runtime_args=None, config=None)

    关联文件:
    - spec: [spec/dsl/mlir_gen.md](spec/dsl/mlir_gen.md)
    - test: [test/dsl/mlir_gen/test_function_builder.py](test/dsl/mlir_gen/test_function_builder.py)
    - 功能实现: [kernel_gen/dsl/mlir_gen/function_builder.py](kernel_gen/dsl/mlir_gen/function_builder.py)
    """

    config = dict(config or {})
    _maybe_validate_dma_view_bounds(func_ast, runtime_args)
    if runtime_args is None and _is_symbol_scalar_function(func_ast):
        raise LoweringError(
            _build_runtime_args_required_error(func_ast.name, len(func_ast.inputs), 0),
            location=func_ast.location,
        )
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
        config.setdefault("__runtime_values__", dict(runtime_values))
    statements = _ensure_supported_statements(func_ast)
    last_stmt = statements[-1]
    has_value_return = _function_has_value_return(func_ast)
    if has_value_return:
        if is_dma_alloc_only:
            if not isinstance(last_stmt, DmaAllocAST):
                raise LoweringError("Return type does not match annotation", location=func_ast.location)
        elif isinstance(last_stmt, NnReduceAST) and last_stmt.kind == "reduce_max":
            input_type = type_map.get(_expr_key(last_stmt.value))
            if isinstance(input_type, NnMemoryType):
                axes = _parse_reduce_axis_expr(last_stmt.axis, last_stmt.location)
                if axes is not None:
                    rank = len(input_type.shape.data)
                    for axis_value in axes:
                        if axis_value < -rank or axis_value >= rank:
                            raise LoweringError(
                                f"{last_stmt.kind} axis must be within [-{rank}, {rank - 1}]",
                                location=last_stmt.location,
                            )
    elif not func_ast.returns_none and not _is_zero_return_statement_expr(last_stmt):
        raise LoweringError(
            "Function return requires explicit return syntax or annotation",
            location=getattr(last_stmt, "location", None) or func_ast.location,
        )

    func_type = FunctionType.from_lists(arg_types, [])
    block = Block(arg_types=arg_types)
    func_op = func.FuncOp(func_ast.name, func_type, Region(block))

    ctx = EmitContext(builder=block, symbols={}, types=dict(type_map), config=config)
    _seed_input_symbol_aliases(ctx, func_ast, block)
    visitor = AstVisitor(config=config)
    return_value = visitor.visit_function(func_ast, ctx)
    if has_value_return:
        if return_value is None:
            raise LoweringError("Function body is empty", location=func_ast.location)
        block.add_op(func.ReturnOp(return_value))
    else:
        block.add_op(func.ReturnOp())
    func_op.update_function_type()
    _rewrite_dynamic_memory_result_types(func_op)
    if has_value_return and func_ast.outputs:
        result_type = list(func_op.function_type.outputs.data)[0]
        _validate_return_type(
            func_ast,
            result_type,
            last_stmt,
            dict(type_map),
            runtime_values,
        )
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
    - 将 `LoweringError` 统一转换为 `AstVisitorError`。

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
    - test: [test/dsl/mlir_gen/test_function_builder.py](test/dsl/mlir_gen/test_function_builder.py)
    - 功能实现: [kernel_gen/dsl/mlir_gen/function_builder.py](kernel_gen/dsl/mlir_gen/function_builder.py)
    """

    try:
        return _build_func_op_from_ast_impl(func_ast, runtime_args=runtime_args, config=config)
    except LoweringError as exc:
        raise AstVisitorError(str(exc), location=exc.location) from exc
