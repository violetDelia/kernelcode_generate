"""mlir_gen signature helpers.

创建者: 朽木露琪亚
最后一次更改: 朽木露琪亚

功能说明:
- 负责 func.func 签名与返回类型相关的类型推导与校验。
- 提供 runtime_args、注解与 AST 之间的约束收敛入口。

使用示例:
- arg_types, type_map = _build_signature_types(func_ast, runtime_args=[...])
- _validate_return_type(func_ast, result_type, return_expr, type_map)

关联文件:
- spec: [spec/dsl/mlir_gen.md](spec/dsl/mlir_gen.md)
- test: [test/dsl/mlir_gen/test_signature.py](test/dsl/mlir_gen/test_signature.py)
- 功能实现: [kernel_gen/dsl/mlir_gen/signature.py](kernel_gen/dsl/mlir_gen/signature.py)
"""

from __future__ import annotations

import re

import sympy as sp
from xdsl.dialects.builtin import IntAttr, StringAttr, f32, i1, i32

from kernel_gen.dialect.nn import NnMemoryType
from kernel_gen.dialect.symbol import SymbolValueType
from kernel_gen.dsl.ast import (
    ArchBarrierAST,
    ArchLaunchKernelAST,
    ArchQueryAST,
    BinaryExprAST,
    ConstAST,
    DmaAllocAST,
    DmaFlattenAST,
    DmaFreeAST,
    ForAST,
    FunctionAST,
    NnReduceAST,
    ScalarArgAST,
    StoreAST,
    SymbolToFloatAST,
    TensorAST,
    TensorAxisAccessAST,
)
from kernel_gen.dsl.mlir_gen.emit.core import (
    _LoweringError,
    _expr_key,
    _infer_binary_memory_type,
    _infer_expr_type,
    _memory_to_nn_type,
    _resolve_symbolic_index_value,
)
from kernel_gen.symbol_variable.memory import Memory
from kernel_gen.symbol_variable.symbol_dim import SymbolDim


def _is_symbol_scalar_function(func_ast: FunctionAST) -> bool:
    """判断是否为纯 symbol 标量函数。

    创建者: 朽木露琪亚
    最后一次更改: 朽木露琪亚

    功能说明:
    - 识别仅包含 symbol 标量输入/输出的函数。
    - 允许无输出或 bool/float/int 标量输出。

    使用示例:
    - if _is_symbol_scalar_function(func_ast): ...

    关联文件:
    - spec: [spec/dsl/mlir_gen.md](spec/dsl/mlir_gen.md)
    - test: [test/dsl/mlir_gen/test_signature.py](test/dsl/mlir_gen/test_signature.py)
    - 功能实现: [kernel_gen/dsl/mlir_gen/signature.py](kernel_gen/dsl/mlir_gen/signature.py)
    """

    if not func_ast.inputs:
        return False
    if not all(isinstance(item, ScalarArgAST) and item.value_type is int for item in func_ast.inputs):
        return False
    if not func_ast.outputs:
        return True
    return all(isinstance(item, ScalarArgAST) and item.value_type in {int, bool, float} for item in func_ast.outputs)


def _is_symbol_scalar_arg(item: ScalarArgAST, *, is_symbol_scalar_function: bool) -> bool:
    """判断标量参数是否走 symbol 语义。

    创建者: 朽木露琪亚
    最后一次更改: 朽木露琪亚

    功能说明:
    - 纯 symbol 标量函数或标记为 is_symbolic 的标量参数应走 symbol 语义。

    使用示例:
    - if _is_symbol_scalar_arg(arg, is_symbol_scalar_function=True): ...

    关联文件:
    - spec: [spec/dsl/mlir_gen.md](spec/dsl/mlir_gen.md)
    - test: [test/dsl/mlir_gen/test_signature.py](test/dsl/mlir_gen/test_signature.py)
    - 功能实现: [kernel_gen/dsl/mlir_gen/signature.py](kernel_gen/dsl/mlir_gen/signature.py)
    """

    return is_symbol_scalar_function or item.is_symbolic


def _symbol_expr_from_runtime_arg(runtime_arg: object) -> str | None:
    """从 runtime 参数提取 symbol 表达式文本。

    创建者: 朽木露琪亚
    最后一次更改: 朽木露琪亚

    功能说明:
    - 支持 `SymbolDim` 与 `int`。
    - 无法识别时返回 None。

    使用示例:
    - expr = _symbol_expr_from_runtime_arg(SymbolDim("M"))

    关联文件:
    - spec: [spec/dsl/mlir_gen.md](spec/dsl/mlir_gen.md)
    - test: [test/dsl/mlir_gen/test_signature.py](test/dsl/mlir_gen/test_signature.py)
    - 功能实现: [kernel_gen/dsl/mlir_gen/signature.py](kernel_gen/dsl/mlir_gen/signature.py)
    """

    if isinstance(runtime_arg, SymbolDim):
        return str(runtime_arg.get_symbol())
    if isinstance(runtime_arg, int):
        return str(runtime_arg)
    return None


def _is_dma_alloc_only_function(func_ast: FunctionAST) -> bool:
    """判断函数体是否仅包含 dma.alloc 返回。

    创建者: 朽木露琪亚
    最后一次更改: 朽木露琪亚

    功能说明:
    - 仅当函数输出为单个 Tensor 且最后一条语句是 DmaAllocAST 时返回 True。

    使用示例:
    - if _is_dma_alloc_only_function(func_ast): ...

    关联文件:
    - spec: [spec/dsl/mlir_gen.md](spec/dsl/mlir_gen.md)
    - test: [test/dsl/mlir_gen/test_signature.py](test/dsl/mlir_gen/test_signature.py)
    - 功能实现: [kernel_gen/dsl/mlir_gen/signature.py](kernel_gen/dsl/mlir_gen/signature.py)
    """

    statements = func_ast.body.statements
    if len(func_ast.outputs) != 1 or not statements:
        return False
    if not isinstance(func_ast.outputs[0], TensorAST):
        return False
    return isinstance(statements[-1], DmaAllocAST)


def _resolve_dma_alloc_shape_value(expr: object, runtime_values: dict[str, object]) -> int | SymbolDim:
    """解析 dma.alloc 形状/步长表达式为数值或 symbol 表达式。

    创建者: 朽木露琪亚
    最后一次更改: 朽木露琪亚

    功能说明:
    - 支持 ScalarArgAST/ConstAST/int/str。
    - runtime_values 提供标量参数的实际值推导。

    使用示例:
    - value = _resolve_dma_alloc_shape_value(expr, runtime_values)

    关联文件:
    - spec: [spec/dsl/mlir_gen.md](spec/dsl/mlir_gen.md)
    - test: [test/dsl/mlir_gen/test_signature.py](test/dsl/mlir_gen/test_signature.py)
    - 功能实现: [kernel_gen/dsl/mlir_gen/signature.py](kernel_gen/dsl/mlir_gen/signature.py)
    """

    return _resolve_symbolic_index_value(expr, location=getattr(expr, "location", None), runtime_values=runtime_values)


def _build_dma_alloc_only_result_type(
    func_ast: FunctionAST,
    alloc_expr: DmaAllocAST,
    runtime_args: tuple[object, ...] | list[object] | None,
) -> NnMemoryType:
    """构造 dma.alloc-only 场景的返回类型。

    创建者: 朽木露琪亚
    最后一次更改: 朽木露琪亚

    功能说明:
    - 依赖 runtime_args 推导标量 shape/stride 值。
    - 要求显式 stride 与默认连续布局一致。

    使用示例:
    - result_type = _build_dma_alloc_only_result_type(func_ast, alloc_expr, runtime_args)

    关联文件:
    - spec: [spec/dsl/mlir_gen.md](spec/dsl/mlir_gen.md)
    - test: [test/dsl/mlir_gen/test_signature.py](test/dsl/mlir_gen/test_signature.py)
    - 功能实现: [kernel_gen/dsl/mlir_gen/signature.py](kernel_gen/dsl/mlir_gen/signature.py)
    """

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
    """根据 runtime_args 与 AST 生成函数签名类型列表。

    创建者: 朽木露琪亚
    最后一次更改: 朽木露琪亚

    功能说明:
    - 以 runtime_args 驱动输入类型推导。
    - 兼容 dma.alloc-only 场景允许无 tensor 输入。

    使用示例:
    - arg_types, type_map = _build_signature_types(func_ast, runtime_args=[Memory(...)])

    关联文件:
    - spec: [spec/dsl/mlir_gen.md](spec/dsl/mlir_gen.md)
    - test: [test/dsl/mlir_gen/test_signature.py](test/dsl/mlir_gen/test_signature.py)
    - 功能实现: [kernel_gen/dsl/mlir_gen/signature.py](kernel_gen/dsl/mlir_gen/signature.py)
    """

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
    - spec: [spec/dsl/mlir_gen.md](spec/dsl/mlir_gen.md)
    - test: [test/dsl/mlir_gen/test_signature.py](test/dsl/mlir_gen/test_signature.py)
    - 功能实现: [kernel_gen/dsl/mlir_gen/signature.py](kernel_gen/dsl/mlir_gen/signature.py)
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
    - spec: [spec/dsl/mlir_gen.md](spec/dsl/mlir_gen.md)
    - test: [test/dsl/mlir_gen/test_signature.py](test/dsl/mlir_gen/test_signature.py)
    - 功能实现: [kernel_gen/dsl/mlir_gen/signature.py](kernel_gen/dsl/mlir_gen/signature.py)
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
    - spec: [spec/dsl/mlir_gen.md](spec/dsl/mlir_gen.md)
    - test: [test/dsl/mlir_gen/test_signature.py](test/dsl/mlir_gen/test_signature.py)
    - 功能实现: [kernel_gen/dsl/mlir_gen/signature.py](kernel_gen/dsl/mlir_gen/signature.py)
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


def _shape_annotation_matches(result_type: NnMemoryType, expected_type: NnMemoryType) -> bool:
    """校验 tensor 返回 shape 是否在符号语义上等价。

    创建者: 朽木露琪亚
    最后一次更改: 朽木露琪亚

    功能说明:
    - 对 `IntAttr` 维度执行精确数值比较。
    - 对 `StringAttr` 维度先比较字面量；若不同，再执行 sympy 语义化简比较。
    - 用于返回注解校验，避免仅按字符串字面量比较符号维表达式。

    使用示例:
    - _shape_annotation_matches(result_type, expected_type)

    关联文件:
    - spec: [spec/dsl/mlir_gen.md](spec/dsl/mlir_gen.md)
    - test: [test/dsl/mlir_gen/test_signature.py](test/dsl/mlir_gen/test_signature.py)
    - 功能实现: [kernel_gen/dsl/mlir_gen/signature.py](kernel_gen/dsl/mlir_gen/signature.py)
    """

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
    - spec: [spec/dsl/mlir_gen.md](spec/dsl/mlir_gen.md)
    - test: [test/dsl/mlir_gen/test_signature.py](test/dsl/mlir_gen/test_signature.py)
    - 功能实现: [kernel_gen/dsl/mlir_gen/signature.py](kernel_gen/dsl/mlir_gen/signature.py)
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
        shape_matches = _shape_annotation_matches(result_type, expected_type)
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
            if isinstance(return_expr, ArchQueryAST) and isinstance(result_type, SymbolValueType):
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


def _function_has_value_return(func_ast: FunctionAST) -> bool:
    """判断函数是否应装配单返回值。

    创建者: 朽木露琪亚
    最后一次更改: 朽木露琪亚

    功能说明:
    - 显式返回注解始终视为值返回。
    - 无返回注解时，仅当 AST 标记存在显式 `return expr` 时才视为值返回。
    - 显式 `-> None` 不属于值返回。

    使用示例:
    - if _function_has_value_return(func_ast): ...

    关联文件:
    - spec: [spec/dsl/mlir_gen.md](spec/dsl/mlir_gen.md)
    - test: [test/dsl/mlir_gen/test_signature.py](test/dsl/mlir_gen/test_signature.py)
    - 功能实现: [kernel_gen/dsl/mlir_gen/signature.py](kernel_gen/dsl/mlir_gen/signature.py)
    """

    if func_ast.returns_none:
        return False
    if func_ast.outputs:
        return True
    return func_ast.has_explicit_return


def _is_zero_return_statement_expr(expr: object) -> bool:
    """判断表达式是否属于语句型零返回函数体。

    创建者: 金铲铲大作战
    最后一次更改: 金铲铲大作战

    功能说明:
    - 仅允许 `free/store/deslice/for/launch_kernel` 这类本来就不产生函数返回值的语句函数保持零结果。
    - 供函数级返回装配阶段拒绝“靠最后一个值表达式猜输出”的歧义路径。

    使用示例:
    - if _is_zero_return_statement_expr(last_stmt): ...

    关联文件:
    - spec: [spec/dsl/mlir_gen.md](spec/dsl/mlir_gen.md)
    - test: [test/dsl/mlir_gen/test_signature.py](test/dsl/mlir_gen/test_signature.py)
    - 功能实现: [kernel_gen/dsl/mlir_gen/signature.py](kernel_gen/dsl/mlir_gen/signature.py)
    """

    return isinstance(expr, (DmaFreeAST, StoreAST, ForAST, ArchBarrierAST, ArchLaunchKernelAST))
