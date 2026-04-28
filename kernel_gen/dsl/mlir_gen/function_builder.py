"""mlir_gen function builder.

创建者: 朽木露琪亚
最后一次更改: 榕

功能说明:
- 负责 `kernel_gen.dsl.mlir_gen` 包根公开 `build_func_op(...)` /
  `build_func_op_from_ast(...)` 背后的函数级 IR 装配逻辑。
- 当前文件只承载 package-root facade 背后的内部实现拆分，不单独扩展新的公开入口。

API 列表:
- 无；当前文件仅提供 `kernel_gen.dsl.mlir_gen` 包根公开
  `build_func_op(...)` / `build_func_op_from_ast(...)` 的内部实现拆分。

使用示例:
- from kernel_gen.dsl.mlir_gen import build_func_op, build_func_op_from_ast
- func_op = build_func_op(fn, *runtime_args)
- func_op = build_func_op_from_ast(func_ast, runtime_args=[...])

关联文件:
- spec: [spec/dsl/mlir_gen.md](spec/dsl/mlir_gen.md)
- test: [test/dsl/mlir_gen/test_function_builder.py](test/dsl/mlir_gen/test_function_builder.py)
- 功能实现: [kernel_gen/dsl/mlir_gen/function_builder.py](kernel_gen/dsl/mlir_gen/function_builder.py)
"""

from __future__ import annotations
from kernel_gen.core.error import ErrorKind, ErrorModule, KernelCodeError

import inspect
import re
from collections.abc import Callable

import sympy as sp
from xdsl.dialects import func
from xdsl.dialects.builtin import ArrayAttr, FunctionType, IntAttr, StringAttr, f32, i1, i32, i8
from xdsl.ir import Block, Region

from kernel_gen.dialect.arch import ArchGetDynamicMemoryOp
from kernel_gen.dialect.nn import NnMemoryType
from kernel_gen.dialect.symbol import SymbolValueType
from kernel_gen.dsl.ast import (
    ArchBarrierAST,
    ArchGetDynamicMemoryAST,
    ArchLaunchKernelAST,
    ArchQueryAST,
    BinaryExprAST,
    CompareExprAST,
    ConstAST,
    ConvAST,
    DmaAllocAST,
    DmaCastAST,
    DmaCopyAST,
    DmaFlattenAST,
    DmaFreeAST,
    DmaReshapeAST,
    DmaViewAST,
    FCAST,
    ForAST,
    FunctionAST,
    IfAST,
    Img2ColAST,
    LoadAST,
    MatmulAST,
    NnBroadcastAST,
    NnBroadcastToAST,
    NnReduceAST,
    NnSoftmaxAST,
    NnTransposeAST,
    NnUnaryAST,
    PythonCalleeCallAST,
    ScalarArgAST,
    StoreAST,
    SymbolToFloatAST,
    TensorAST,
    TensorAxisAccessAST,
    VarAST,
)
from kernel_gen.dsl.ast.parser import parse_function_with_env
from kernel_gen.dsl.ast.visitor import AstVisitor
from kernel_gen.dsl.mlir_gen.emit import EmitContext, emit_mlir, memory_type_from_memory
from kernel_gen.dsl.mlir_gen.emit.type_utils import infer_expr_type
from kernel_gen.symbol_variable.memory import Memory
from kernel_gen.symbol_variable.symbol_dim import SymbolDim

_DYNAMIC_MEMORY_SYMBOL_NAMES = {
    "shared": "SM_SIZE",
    "local": "LM_SIZE",
    "tsm": "TSM_SIZE",
    "tlm1": "TLM1_SIZE",
    "tlm2": "TLM2_SIZE",
    "tlm3": "TLM3_SIZE",
}




def _raise_visitor_error_from_parse_error(
    exc: KernelCodeError,
    *,
    value_messages: tuple[str, ...] = (),
) -> None:
    """把 AST 解析错误翻译为当前文件沿用的公开错误合同。"""

    diagnostics = getattr(exc, "diagnostics", ())
    location = diagnostics[0].location if diagnostics else getattr(exc, "location", None)
    message = exc.message()
    if message in value_messages:
        raise ValueError(message) from exc
    if message.endswith("space must be MemorySpace") or message == "cast dtype must be NumericType":
        raise TypeError(message) from exc
    raise KernelCodeError(ErrorKind.CONTRACT, ErrorModule.AST, message, location=location) from exc


def _expr_key(expr: object) -> int:
    """为 AST 节点生成当前文件内使用的缓存键。

    创建者: 小李飞刀
    最后一次更改: 朽木露琪亚

    功能说明:
    - 当前直接使用 `id(expr)` 作为当前文件内的类型/值缓存键。

    使用示例:
    - key = _expr_key(expr)

    关联文件:
    - spec: [spec/dsl/mlir_gen.md](spec/dsl/mlir_gen.md)
    - test: [test/dsl/mlir_gen/test_function_builder.py](test/dsl/mlir_gen/test_function_builder.py)
    - 功能实现: [kernel_gen/dsl/mlir_gen/function_builder.py](kernel_gen/dsl/mlir_gen/function_builder.py)
    """

    return id(expr)


def _is_symbol_scalar_function(func_ast: FunctionAST) -> bool:
    """判断是否为纯 symbol 标量函数。

    创建者: 小李飞刀
    最后一次更改: 榕

    功能说明:
    - 识别仅包含 symbol 标量输入/输出的函数。
    - 允许无输出或 `bool/float/int` 标量输出。

    使用示例:
    - if _is_symbol_scalar_function(func_ast): ...

    关联文件:
    - spec: [spec/dsl/mlir_gen.md](spec/dsl/mlir_gen.md)
    - test: [test/dsl/mlir_gen/test_function_builder.py](test/dsl/mlir_gen/test_function_builder.py)
    - 功能实现: [kernel_gen/dsl/mlir_gen/function_builder.py](kernel_gen/dsl/mlir_gen/function_builder.py)
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

    创建者: 小李飞刀
    最后一次更改: 小李飞刀

    功能说明:
    - 纯 symbol 标量函数或标记为 `is_symbolic` 的标量参数应走 symbol 语义。

    使用示例:
    - if _is_symbol_scalar_arg(arg, is_symbol_scalar_function=True): ...

    关联文件:
    - spec: [spec/dsl/mlir_gen.md](spec/dsl/mlir_gen.md)
    - test: [test/dsl/mlir_gen/test_function_builder.py](test/dsl/mlir_gen/test_function_builder.py)
    - 功能实现: [kernel_gen/dsl/mlir_gen/function_builder.py](kernel_gen/dsl/mlir_gen/function_builder.py)
    """

    return is_symbol_scalar_function or item.is_symbolic


def _symbol_expr_from_runtime_arg(runtime_arg: object) -> str | None:
    """从 runtime 参数提取 symbol 表达式文本。

    创建者: 小李飞刀
    最后一次更改: 小李飞刀

    功能说明:
    - 支持 `SymbolDim` 与 `int`。
    - 无法识别时返回 `None`。

    使用示例:
    - expr = _symbol_expr_from_runtime_arg(SymbolDim("M"))

    关联文件:
    - spec: [spec/dsl/mlir_gen.md](spec/dsl/mlir_gen.md)
    - test: [test/dsl/mlir_gen/test_function_builder.py](test/dsl/mlir_gen/test_function_builder.py)
    - 功能实现: [kernel_gen/dsl/mlir_gen/function_builder.py](kernel_gen/dsl/mlir_gen/function_builder.py)
    """

    if isinstance(runtime_arg, SymbolDim):
        return str(runtime_arg.get_symbol())
    if isinstance(runtime_arg, int):
        return str(runtime_arg)
    return None


def _is_dma_alloc_only_function(func_ast: FunctionAST) -> bool:
    """判断函数体是否仅包含 dma.alloc 返回。

    创建者: 小李飞刀
    最后一次更改: 小李飞刀

    功能说明:
    - 仅当函数输出为单个 `Tensor` 且最后一条语句是 `DmaAllocAST` 时返回 `True`。

    使用示例:
    - if _is_dma_alloc_only_function(func_ast): ...

    关联文件:
    - spec: [spec/dsl/mlir_gen.md](spec/dsl/mlir_gen.md)
    - test: [test/dsl/mlir_gen/test_function_builder.py](test/dsl/mlir_gen/test_function_builder.py)
    - 功能实现: [kernel_gen/dsl/mlir_gen/function_builder.py](kernel_gen/dsl/mlir_gen/function_builder.py)
    """

    statements = func_ast.body.statements
    if len(func_ast.outputs) != 1 or not statements:
        return False
    if not isinstance(func_ast.outputs[0], TensorAST):
        return False
    return isinstance(statements[-1], DmaAllocAST)


def _apply_symbolic_index_binary_op(
    lhs_value: int | SymbolDim,
    rhs_value: int | SymbolDim,
    op: str,
    location: object | None,
) -> int | SymbolDim:
    """在当前文件内解析 shape/stride 的符号索引二元运算。

    创建者: 小李飞刀
    最后一次更改: 小李飞刀

    功能说明:
    - 支持 `+/-/*/div/floordiv`。
    - 整数除法仅接受当前公开合同允许的精确结果。

    使用示例:
    - value = _apply_symbolic_index_binary_op(SymbolDim("M"), 2, "mul", None)

    关联文件:
    - spec: [spec/dsl/mlir_gen.md](spec/dsl/mlir_gen.md)
    - test: [test/dsl/mlir_gen/test_function_builder.py](test/dsl/mlir_gen/test_function_builder.py)
    - 功能实现: [kernel_gen/dsl/mlir_gen/function_builder.py](kernel_gen/dsl/mlir_gen/function_builder.py)
    """

    if op == "add":
        return lhs_value + rhs_value
    if op == "sub":
        return lhs_value - rhs_value
    if op == "mul":
        return lhs_value * rhs_value
    if op == "div":
        if isinstance(lhs_value, int) and isinstance(rhs_value, int):
            if rhs_value == 0 or lhs_value % rhs_value != 0:
                raise KernelCodeError(ErrorKind.CONTRACT, ErrorModule.MLIR_GEN, "Unsupported index expression", location=location)
            return lhs_value // rhs_value
        if isinstance(lhs_value, int):
            lhs_value = SymbolDim(lhs_value)
        return lhs_value / rhs_value
    if op == "floordiv":
        if isinstance(lhs_value, int) and isinstance(rhs_value, int):
            if rhs_value == 0:
                raise KernelCodeError(ErrorKind.CONTRACT, ErrorModule.MLIR_GEN, "Unsupported index expression", location=location)
            return lhs_value // rhs_value
        if isinstance(lhs_value, int):
            lhs_value = SymbolDim(lhs_value)
        return lhs_value // rhs_value
    raise KernelCodeError(ErrorKind.CONTRACT, ErrorModule.MLIR_GEN, "Unsupported index expression", location=location)


def _resolve_symbolic_index_value(
    expr: object,
    *,
    location: object | None = None,
    runtime_values: dict[str, object] | None = None,
) -> int | SymbolDim:
    """解析索引表达式为静态 `int|SymbolDim`。

    创建者: 小李飞刀
    最后一次更改: 小李飞刀

    功能说明:
    - 支持 `ConstAST`、`ScalarArgAST`、`VarAST`、`BinaryExprAST`、`TensorAxisAccessAST` 以及直接的 `int|str`。
    - 当 `runtime_values` 提供 `int|SymbolDim` 时，优先使用运行时标量值。

    使用示例:
    - value = _resolve_symbolic_index_value(expr.axis, location=expr.location, runtime_values=runtime_values)

    关联文件:
    - spec: [spec/dsl/mlir_gen.md](spec/dsl/mlir_gen.md)
    - test: [test/dsl/mlir_gen/test_function_builder.py](test/dsl/mlir_gen/test_function_builder.py)
    - 功能实现: [kernel_gen/dsl/mlir_gen/function_builder.py](kernel_gen/dsl/mlir_gen/function_builder.py)
    """

    if isinstance(expr, ConstAST):
        if isinstance(expr.value, int):
            return expr.value
        if isinstance(expr.value, str):
            return SymbolDim(expr.value)
        raise KernelCodeError(ErrorKind.CONTRACT, ErrorModule.MLIR_GEN, "Index must be int or str", location=expr.location)
    if isinstance(expr, ScalarArgAST):
        if runtime_values is not None and expr.name in runtime_values:
            runtime_value = runtime_values[expr.name]
            if isinstance(runtime_value, (int, SymbolDim)):
                return runtime_value
        return SymbolDim(expr.name)
    if isinstance(expr, VarAST):
        if runtime_values is not None and expr.name in runtime_values:
            runtime_value = runtime_values[expr.name]
            if isinstance(runtime_value, (int, SymbolDim)):
                return runtime_value
        return SymbolDim(expr.name)
    if isinstance(expr, BinaryExprAST):
        lhs = _resolve_symbolic_index_value(expr.lhs, location=expr.location, runtime_values=runtime_values)
        rhs = _resolve_symbolic_index_value(expr.rhs, location=expr.location, runtime_values=runtime_values)
        return _apply_symbolic_index_binary_op(lhs, rhs, expr.op, expr.location)
    if isinstance(expr, TensorAxisAccessAST):
        if not isinstance(expr.axis, ConstAST) or not isinstance(expr.axis.value, int):
            raise KernelCodeError(ErrorKind.CONTRACT, ErrorModule.MLIR_GEN, "Unsupported index expression", location=location or getattr(expr, "location", None))
        dims = expr.tensor.memory.shape if expr.kind == "shape" else expr.tensor.memory.stride
        dim = dims[expr.axis.value]
        public_value = dim.get_value()
        return public_value if isinstance(public_value, int) else dim
    if isinstance(expr, int):
        return expr
    if isinstance(expr, str):
        return SymbolDim(expr)
    raise KernelCodeError(ErrorKind.CONTRACT, ErrorModule.MLIR_GEN, "Unsupported index expression", location=location or getattr(expr, "location", None))


def _resolve_static_index_expr(
    expr: object,
    location: object | None = None,
    runtime_values: dict[str, object] | None = None,
) -> int | str:
    """解析类型推导阶段使用的索引表达式。

    创建者: 小李飞刀
    最后一次更改: 小李飞刀

    功能说明:
    - 支持 `ConstAST`、`ScalarArgAST`、`VarAST` 以及直接的 `int|str`。
    - 将 `SymbolDim` 结果规整成当前公开文本合同使用的 `int|str`。

    使用示例:
    - value = _resolve_static_index_expr(ConstAST("N"))

    关联文件:
    - spec: [spec/dsl/mlir_gen.md](spec/dsl/mlir_gen.md)
    - test: [test/dsl/mlir_gen/test_function_builder.py](test/dsl/mlir_gen/test_function_builder.py)
    - 功能实现: [kernel_gen/dsl/mlir_gen/function_builder.py](kernel_gen/dsl/mlir_gen/function_builder.py)
    """

    value = _resolve_symbolic_index_value(expr, location=location, runtime_values=runtime_values)
    if isinstance(value, SymbolDim):
        normalized = value.get_value()
        if not isinstance(normalized, (int, str)):
            raise KernelCodeError(ErrorKind.CONTRACT, ErrorModule.MLIR_GEN, "Unsupported index expression", location=location or getattr(expr, "location", None))
        return normalized
    return value


def _resolve_dma_alloc_shape_value(expr: object, runtime_values: dict[str, object]) -> int | SymbolDim:
    """解析 dma.alloc 形状/步长表达式为数值或 symbol 表达式。

    创建者: 小李飞刀
    最后一次更改: 小李飞刀

    功能说明:
    - 支持 `ScalarArgAST/ConstAST/int/str`。
    - `runtime_values` 提供标量参数的实际值推导。

    使用示例:
    - value = _resolve_dma_alloc_shape_value(expr, runtime_values)

    关联文件:
    - spec: [spec/dsl/mlir_gen.md](spec/dsl/mlir_gen.md)
    - test: [test/dsl/mlir_gen/test_function_builder.py](test/dsl/mlir_gen/test_function_builder.py)
    - 功能实现: [kernel_gen/dsl/mlir_gen/function_builder.py](kernel_gen/dsl/mlir_gen/function_builder.py)
    """

    return _resolve_symbolic_index_value(expr, location=getattr(expr, "location", None), runtime_values=runtime_values)


def _build_dma_alloc_only_result_type(
    func_ast: FunctionAST,
    alloc_expr: DmaAllocAST,
    runtime_args: tuple[object, ...] | list[object] | None,
) -> NnMemoryType:
    """构造 dma.alloc-only 场景的返回类型。

    创建者: 小李飞刀
    最后一次更改: 小李飞刀

    功能说明:
    - 依赖 `runtime_args` 推导标量 shape/stride 值。
    - 要求显式 stride 与默认连续布局一致。

    使用示例:
    - result_type = _build_dma_alloc_only_result_type(func_ast, alloc_expr, runtime_args)

    关联文件:
    - spec: [spec/dsl/mlir_gen.md](spec/dsl/mlir_gen.md)
    - test: [test/dsl/mlir_gen/test_function_builder.py](test/dsl/mlir_gen/test_function_builder.py)
    - 功能实现: [kernel_gen/dsl/mlir_gen/function_builder.py](kernel_gen/dsl/mlir_gen/function_builder.py)
    """

    runtime_values: dict[str, object] = {}
    if runtime_args is not None:
        runtime_values = {
            input_arg.name: runtime_args[index]
            for index, input_arg in enumerate(func_ast.inputs)
            if isinstance(input_arg, ScalarArgAST)
        }
    shape_exprs = list(alloc_expr.shape) if isinstance(alloc_expr.shape, (list, tuple)) else [alloc_expr.shape]
    shape = [_resolve_dma_alloc_shape_value(entry, runtime_values) for entry in shape_exprs]
    stride = None
    if alloc_expr.stride is not None:
        stride_exprs = (
            list(alloc_expr.stride) if isinstance(alloc_expr.stride, (list, tuple)) else [alloc_expr.stride]
        )
        stride = [_resolve_dma_alloc_shape_value(entry, runtime_values) for entry in stride_exprs]
        normalized_stride = list(Memory(shape, alloc_expr.dtype, stride=stride).stride.get_values())
        default_stride = list(Memory(shape, alloc_expr.dtype).stride.get_values())
        if normalized_stride != default_stride:
            raise KernelCodeError(ErrorKind.CONTRACT, ErrorModule.MLIR_GEN, "dma.alloc only supports contiguous stride", location=alloc_expr.location)
    memory = Memory(shape, alloc_expr.dtype, space=alloc_expr.space, stride=stride)
    return memory_type_from_memory(memory)


def _build_signature_types(
    func_ast: FunctionAST,
    runtime_args: tuple[object, ...] | list[object] | None = None,
    *,
    allow_dma_alloc_only: bool = False,
) -> tuple[list[object], dict[int, object]]:
    """根据 `runtime_args` 与 AST 生成函数签名类型列表。

    创建者: 小李飞刀
    最后一次更改: 小李飞刀

    功能说明:
    - 以 `runtime_args` 驱动输入类型推导。
    - 兼容 `dma.alloc-only` 场景允许无 tensor 输入。

    使用示例:
    - arg_types, type_map = _build_signature_types(func_ast, runtime_args=[Memory(...)])

    关联文件:
    - spec: [spec/dsl/mlir_gen.md](spec/dsl/mlir_gen.md)
    - test: [test/dsl/mlir_gen/test_function_builder.py](test/dsl/mlir_gen/test_function_builder.py)
    - 功能实现: [kernel_gen/dsl/mlir_gen/function_builder.py](kernel_gen/dsl/mlir_gen/function_builder.py)
    """

    is_symbol_scalar_function = _is_symbol_scalar_function(func_ast)
    if runtime_args is not None and len(runtime_args) != len(func_ast.inputs):
        raise KernelCodeError(ErrorKind.CONTRACT, ErrorModule.MLIR_GEN, "runtime_args must align with func_ast inputs", location=func_ast.location)

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
                raise KernelCodeError(ErrorKind.CONTRACT, ErrorModule.MLIR_GEN, "Unsupported scalar argument type", location=item.location)
            if runtime_args is not None and not isinstance(runtime_arg, (int, SymbolDim)):
                raise KernelCodeError(ErrorKind.CONTRACT, ErrorModule.MLIR_GEN, "Unsupported scalar argument type", location=item.location)
            runtime_expr = _symbol_expr_from_runtime_arg(runtime_arg)
            if allow_dma_alloc_only:
                if runtime_args is not None:
                    if runtime_expr is None:
                        raise KernelCodeError(ErrorKind.CONTRACT, ErrorModule.MLIR_GEN, "Unsupported scalar argument type", location=item.location)
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
            raise KernelCodeError(ErrorKind.CONTRACT, ErrorModule.MLIR_GEN, "Unsupported input type", location=getattr(item, "location", None))
        arg_types.append(arg_type)
        type_map[_expr_key(item)] = arg_type

    if func_ast.inputs and tensor_input_count == 0 and not is_symbol_scalar_function and not allow_dma_alloc_only:
        if not getattr(func_ast.body, "statements", None):
            raise KernelCodeError(ErrorKind.CONTRACT, ErrorModule.MLIR_GEN, "At least one tensor input is required", location=func_ast.location)
    return arg_types, type_map


def _allow_mixed_dtype_return(
    return_expr: object,
    type_map: dict[int, object],
    result_type: NnMemoryType,
    expected_type: NnMemoryType,
) -> bool:
    """判断是否允许 mixed dtype promotion 的返回注解差异。

    创建者: 小李飞刀
    最后一次更改: 小李飞刀

    功能说明:
    - 仅在 return 表达式为 tensor 二元算术且左右 dtype 不一致时放宽。
    - 注解 `element_type` 必须来自左右操作数之一。
    - 要求推导出的目标类型与实际 `result_type` 对齐。

    使用示例:
    - _allow_mixed_dtype_return(return_expr, type_map, result_type, expected_type)

    关联文件:
    - spec: [spec/dsl/mlir_gen.md](spec/dsl/mlir_gen.md)
    - test: [test/dsl/mlir_gen/test_function_builder.py](test/dsl/mlir_gen/test_function_builder.py)
    - 功能实现: [kernel_gen/dsl/mlir_gen/function_builder.py](kernel_gen/dsl/mlir_gen/function_builder.py)
    """

    if not isinstance(return_expr, BinaryExprAST):
        return False
    if return_expr.op not in {"add", "sub", "mul", "div", "floordiv"}:
        return False
    lhs_type = infer_expr_type(return_expr.lhs, dict(type_map))
    rhs_type = infer_expr_type(return_expr.rhs, dict(type_map))
    if not isinstance(lhs_type, NnMemoryType) or not isinstance(rhs_type, NnMemoryType):
        return False
    if lhs_type.element_type == rhs_type.element_type:
        return False
    if expected_type.element_type not in {lhs_type.element_type, rhs_type.element_type}:
        return False
    try:
        target_type = infer_expr_type(return_expr, dict(type_map))
    except KernelCodeError:
        return False
    return (
        isinstance(target_type, NnMemoryType)
        and result_type.shape == target_type.shape
        and result_type.element_type == target_type.element_type
    )


def _parse_symbolic_dim_expr(expr: str) -> sp.Basic | None:
    """解析符号维度表达式字符串。

    创建者: 小李飞刀
    最后一次更改: 小李飞刀

    功能说明:
    - 接受不含 `?` 的字符串并转为 `sympy` 表达式。
    - 解析失败时返回 `None`。

    使用示例:
    - _parse_symbolic_dim_expr("M*N*K")

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
    - test: [test/dsl/mlir_gen/test_function_builder.py](test/dsl/mlir_gen/test_function_builder.py)
    - 功能实现: [kernel_gen/dsl/mlir_gen/function_builder.py](kernel_gen/dsl/mlir_gen/function_builder.py)
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

    创建者: 小李飞刀
    最后一次更改: 小李飞刀

    功能说明:
    - 对 `IntAttr` 维度执行精确数值比较。
    - 对 `StringAttr` 维度先比较字面量；若不同，再执行 `sympy` 语义化简比较。

    使用示例:
    - _shape_annotation_matches(result_type, expected_type)

    关联文件:
    - spec: [spec/dsl/mlir_gen.md](spec/dsl/mlir_gen.md)
    - test: [test/dsl/mlir_gen/test_function_builder.py](test/dsl/mlir_gen/test_function_builder.py)
    - 功能实现: [kernel_gen/dsl/mlir_gen/function_builder.py](kernel_gen/dsl/mlir_gen/function_builder.py)
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

    创建者: 小李飞刀
    最后一次更改: 小李飞刀

    功能说明:
    - 检查 Tensor 返回的 shape 与 `element_type` 是否匹配注解。
    - mixed dtype 场景下允许返回注解 `element_type` 与实际结果不同，但仅限二元算术。
    - 允许 `Memory.get_shape/get_stride()[axis]` 在 `-> int` 注解下返回 `!symbol.int`。
    - 允许 `return float(symbol.int)` 在 `-> float` 注解下返回 `f32`。

    使用示例:
    - _validate_return_type(func_ast, result_type, return_expr, type_map)

    关联文件:
    - spec: [spec/dsl/mlir_gen.md](spec/dsl/mlir_gen.md)
    - test: [test/dsl/mlir_gen/test_function_builder.py](test/dsl/mlir_gen/test_function_builder.py)
    - 功能实现: [kernel_gen/dsl/mlir_gen/function_builder.py](kernel_gen/dsl/mlir_gen/function_builder.py)
    """

    if not func_ast.outputs:
        return
    if len(func_ast.outputs) != 1:
        raise KernelCodeError(ErrorKind.CONTRACT, ErrorModule.MLIR_GEN, "Only single return value is supported", location=func_ast.location)
    output = func_ast.outputs[0]
    if isinstance(output, TensorAST):
        expected_type = memory_type_from_memory(output.memory)
        if not isinstance(result_type, NnMemoryType):
            raise KernelCodeError(ErrorKind.CONTRACT, ErrorModule.MLIR_GEN, "Return type does not match annotation", location=func_ast.location)
        shape_matches = _shape_annotation_matches(result_type, expected_type)
        if not shape_matches and isinstance(return_expr, DmaFlattenAST):
            shape_matches = _flatten_numel_annotation_matches(result_type, expected_type)
        if not shape_matches:
            raise KernelCodeError(ErrorKind.CONTRACT, ErrorModule.MLIR_GEN, "Return type does not match annotation", location=func_ast.location)
        if result_type.element_type != expected_type.element_type:
            if return_expr is not None and type_map is not None:
                if _allow_mixed_dtype_return(return_expr, type_map, result_type, expected_type):
                    return
            raise KernelCodeError(ErrorKind.CONTRACT, ErrorModule.MLIR_GEN, "Return type does not match annotation", location=func_ast.location)
        return
    if isinstance(output, ScalarArgAST):
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
                raise KernelCodeError(ErrorKind.CONTRACT, ErrorModule.MLIR_GEN, "Unsupported scalar return type", location=output.location)
        else:
            raise KernelCodeError(ErrorKind.CONTRACT, ErrorModule.MLIR_GEN, "Unsupported scalar return type", location=output.location)
    else:
        raise KernelCodeError(ErrorKind.CONTRACT, ErrorModule.MLIR_GEN, "Unsupported return annotation type", location=getattr(output, "location", None))
    if result_type != expected_type:
        raise KernelCodeError(ErrorKind.CONTRACT, ErrorModule.MLIR_GEN, "Return type does not match annotation", location=func_ast.location)


def _function_has_value_return(func_ast: FunctionAST) -> bool:
    """判断函数是否应装配单返回值。

    创建者: 小李飞刀
    最后一次更改: 小李飞刀

    功能说明:
    - 显式返回注解始终视为值返回。
    - 无返回注解时，仅当 AST 标记存在显式 `return expr` 时才视为值返回。
    - 显式 `-> None` 不属于值返回。

    使用示例:
    - if _function_has_value_return(func_ast): ...

    关联文件:
    - spec: [spec/dsl/mlir_gen.md](spec/dsl/mlir_gen.md)
    - test: [test/dsl/mlir_gen/test_function_builder.py](test/dsl/mlir_gen/test_function_builder.py)
    - 功能实现: [kernel_gen/dsl/mlir_gen/function_builder.py](kernel_gen/dsl/mlir_gen/function_builder.py)
    """

    if func_ast.returns_none:
        return False
    if func_ast.outputs:
        return True
    return func_ast.has_explicit_return


def _is_zero_return_statement_expr(expr: object) -> bool:
    """判断表达式是否属于语句型零返回函数体。

    创建者: 小李飞刀
    最后一次更改: 榕

    功能说明:
    - 仅允许 `free/store/deslice/if/for/launch_kernel` 这类本来就不产生函数返回值的语句函数保持零结果。

    使用示例:
    - if _is_zero_return_statement_expr(last_stmt): ...

    关联文件:
    - spec: [spec/dsl/mlir_gen.md](spec/dsl/mlir_gen.md)
    - test: [test/dsl/mlir_gen/test_function_builder.py](test/dsl/mlir_gen/test_function_builder.py)
    - 功能实现: [kernel_gen/dsl/mlir_gen/function_builder.py](kernel_gen/dsl/mlir_gen/function_builder.py)
    """

    return isinstance(expr, (DmaFreeAST, StoreAST, IfAST, ForAST, ArchBarrierAST, ArchLaunchKernelAST))


def _parse_reduce_axis_expr(axis_expr: object | None, location: object | None) -> list[int] | None:
    """解析 reduce 的 axis 表达式为轴列表。

    创建者: 小李飞刀
    最后一次更改: 小李飞刀

    功能说明:
    - 允许 `int / ConstAST[int] / list/tuple` 的轴值解析。
    - 未提供 axis 时返回 `None`，表示“reduce all axes”。

    使用示例:
    - axes = _parse_reduce_axis_expr(ConstAST(1), location=None)

    关联文件:
    - spec: [spec/dsl/mlir_gen.md](spec/dsl/mlir_gen.md)
    - test: [test/dsl/mlir_gen/test_function_builder.py](test/dsl/mlir_gen/test_function_builder.py)
    - 功能实现: [kernel_gen/dsl/mlir_gen/function_builder.py](kernel_gen/dsl/mlir_gen/function_builder.py)
    """

    if axis_expr is None:
        return None
    if isinstance(axis_expr, ConstAST):
        if isinstance(axis_expr.value, int):
            return [axis_expr.value]
        raise KernelCodeError(ErrorKind.CONTRACT, ErrorModule.MLIR_GEN, "reduce axis must be int", location=axis_expr.location)
    if isinstance(axis_expr, int):
        return [axis_expr]
    if isinstance(axis_expr, (list, tuple)):
        axes: list[int] = []
        for entry in axis_expr:
            if isinstance(entry, ConstAST) and isinstance(entry.value, int):
                axes.append(entry.value)
                continue
            if isinstance(entry, int):
                axes.append(entry)
                continue
            raise KernelCodeError(ErrorKind.CONTRACT, ErrorModule.MLIR_GEN, "reduce axis must be int", location=getattr(entry, "location", None) or location)
        return axes
    raise KernelCodeError(ErrorKind.CONTRACT, ErrorModule.MLIR_GEN, "reduce axis must be int or list of int", location=location)


def _ensure_supported_statements(function_ast: FunctionAST) -> list[object]:
    """校验函数体中的 AST 语句是否属于当前 lowering 支持范围。

    创建者: 小李飞刀
    最后一次更改: 榕

    功能说明:
    - 拒绝空函数体。
    - 遍历并检查每条语句的 AST 类型，提前在发射前给出统一诊断。
    - 语句级 `IfAST` 允许进入后续 `emit_mlir(...)` 控制流 lowering。

    使用示例:
    - statements = _ensure_supported_statements(function_ast)

    关联文件:
    - spec: [spec/dsl/mlir_gen.md](spec/dsl/mlir_gen.md)
    - test: [test/dsl/mlir_gen/test_function_builder.py](test/dsl/mlir_gen/test_function_builder.py)
    - 功能实现: [kernel_gen/dsl/mlir_gen/function_builder.py](kernel_gen/dsl/mlir_gen/function_builder.py)
    """

    statements = function_ast.body.statements
    if not statements:
        raise KernelCodeError(ErrorKind.CONTRACT, ErrorModule.MLIR_GEN, "Function body is empty", location=function_ast.location)
    for expr in statements:
        if not isinstance(
            expr,
            (
                BinaryExprAST,
                CompareExprAST,
                ConstAST,
                TensorAST,
                ScalarArgAST,
                VarAST,
                LoadAST,
                StoreAST,
                DmaAllocAST,
                DmaCopyAST,
                DmaCastAST,
                DmaViewAST,
                DmaReshapeAST,
                DmaFlattenAST,
                ConvAST,
                Img2ColAST,
                FCAST,
                MatmulAST,
                NnBroadcastAST,
                NnBroadcastToAST,
                NnReduceAST,
                NnSoftmaxAST,
                NnTransposeAST,
                NnUnaryAST,
                DmaFreeAST,
                ForAST,
                IfAST,
                ArchBarrierAST,
                ArchGetDynamicMemoryAST,
                ArchLaunchKernelAST,
                ArchQueryAST,
                PythonCalleeCallAST,
                SymbolToFloatAST,
                TensorAxisAccessAST,
            ),
        ):
            raise KernelCodeError(ErrorKind.CONTRACT, ErrorModule.MLIR_GEN, "Unsupported AST expression for lowering", location=getattr(expr, "location", None))
    return statements


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
    - 借助当前文件内 `_resolve_static_index_expr(...)` 处理 `ConstAST/ScalarArgAST/VarAST`。

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


def _prime_input_values(func_ast: FunctionAST, ctx: EmitContext) -> None:
    """通过公开 `emit_mlir(...)` 预热函数输入的 SSA/cache 绑定。

    创建者: 小李飞刀
    最后一次更改: 小李飞刀

    功能说明:
    - 复用公开 `emit_mlir(...)` 对输入参数做一次显式访问。
    - 让后续预发射返回表达式时，嵌套的 `TensorAST/ScalarArgAST/VarAST` 能命中已有输入绑定。

    使用示例:
    - _prime_input_values(func_ast, preview_ctx)

    关联文件:
    - spec: [spec/dsl/mlir_gen.md](spec/dsl/mlir_gen.md)
    - test: [test/dsl/mlir_gen/test_function_builder.py](test/dsl/mlir_gen/test_function_builder.py)
    - 功能实现: [kernel_gen/dsl/mlir_gen/function_builder.py](kernel_gen/dsl/mlir_gen/function_builder.py)
    """

    block_args = getattr(ctx.builder, "args", ())
    for index, item in enumerate(func_ast.inputs):
        if item.name not in ctx.symbols and index < len(block_args):
            ctx.symbols[item.name] = block_args[index]
        emit_mlir(item, ctx)


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
    - 运行时参数数量不匹配会抛出 `KernelCodeError`。
    - `slice/cast/alloc` 等前端参数类型错误会按公开合同抛出 `TypeError`。
    - 其余解析或下沉失败会抛出 `KernelCodeError`。

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
        if not runtime_args and (globals is not None or builtins is not None):
            reason = (
                "globals/builtins cannot replace function runtime args: "
                f"expected {len(positional_params)}, got 0"
            )
            raise KernelCodeError(ErrorKind.CONTRACT, ErrorModule.AST, reason, location=None)
        reason = (
            f"build_func_op requires explicit runtime args for {fn.__name__}: "
            f"expected {len(positional_params)}, got {len(runtime_args)}"
        )
        raise KernelCodeError(ErrorKind.CONTRACT, ErrorModule.AST, reason, location=None)

    runtime_table = {param.name: runtime_args[index] for index, param in enumerate(positional_params)}
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
        func_ast = parse_function_with_env(
            fn,
            globals_table,
            builtins_table,
            runtime_table,
        )
    except KernelCodeError as exc:
        _raise_visitor_error_from_parse_error(
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
    最后一次更改: 朽木露琪亚

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
    result_types: list[object] = []
    has_value_return = _function_has_value_return(func_ast)
    preview_block = Block(arg_types=arg_types)
    preview_ctx = EmitContext(builder=preview_block, symbols={}, types=dict(type_map), config=config)
    _seed_input_symbol_aliases(preview_ctx, func_ast, preview_block)
    _prime_input_values(func_ast, preview_ctx)
    if has_value_return:
        return_expr = last_stmt
        if is_dma_alloc_only:
            if not isinstance(return_expr, DmaAllocAST):
                raise KernelCodeError(ErrorKind.CONTRACT, ErrorModule.MLIR_GEN, "Return type does not match annotation", location=func_ast.location)
            result_type = _build_dma_alloc_only_result_type(func_ast, return_expr, runtime_args)
        else:
            if isinstance(return_expr, NnReduceAST) and return_expr.kind == "reduce_max":
                input_type = _emit_result_type_with_public_diagnostics(
                    return_expr.value,
                    preview_ctx,
                    fallback_location=func_ast.location,
                )
                if isinstance(input_type, NnMemoryType):
                    axes = _parse_reduce_axis_expr(return_expr.axis, return_expr.location)
                    if axes is not None:
                        rank = len(input_type.shape.data)
                        for axis_value in axes:
                            if axis_value < -rank or axis_value >= rank:
                                raise KernelCodeError(ErrorKind.CONTRACT, ErrorModule.MLIR_GEN, 
                                    f"{return_expr.kind} axis must be within [-{rank}, {rank - 1}]",
                                    location=return_expr.location,
                                )
            result_type = _emit_result_type_with_public_diagnostics(
                return_expr,
                preview_ctx,
                fallback_location=func_ast.location,
            )
        if func_ast.outputs:
            _validate_return_type(func_ast, result_type, return_expr, dict(type_map))
        type_map[_expr_key(return_expr)] = result_type
        result_types = [result_type]
    elif not func_ast.returns_none and not _is_zero_return_statement_expr(last_stmt):
        raise KernelCodeError(ErrorKind.CONTRACT, ErrorModule.MLIR_GEN, 
            "Function return requires explicit return syntax or annotation",
            location=getattr(last_stmt, "location", None) or func_ast.location,
        )

    func_type = FunctionType.from_lists(arg_types, result_types)
    block = Block(arg_types=arg_types)
    func_op = func.FuncOp(func_ast.name, func_type, Region(block))

    ctx = EmitContext(builder=block, symbols={}, types=dict(type_map), config=config)
    _seed_input_symbol_aliases(ctx, func_ast, block)
    visitor = AstVisitor(config=config)
    return_value = visitor.visit_function(func_ast, ctx)
    if has_value_return:
        if return_value is None:
            raise KernelCodeError(ErrorKind.CONTRACT, ErrorModule.MLIR_GEN, "Function body is empty", location=func_ast.location)
        block.add_op(func.ReturnOp(return_value))
    else:
        block.add_op(func.ReturnOp())
    _rewrite_dynamic_memory_result_types(func_op)
    return func_op


def _emit_result_type_with_public_diagnostics(
    expr: object,
    ctx: EmitContext,
    fallback_location: object,
) -> object:
    """在 `build_func_op` 公开入口中规整返回类型推导诊断。

    创建者: 小李飞刀
    最后一次更改: 小李飞刀

    功能说明:
    - 调用公开 `emit_mlir(...)` 预发射返回表达式并读取结果类型。
    - 仅将 `emit_mlir(...)` 抛出的带 lowering 语义的 `ValueError` 重新包装为带位置信息的 `KernelCodeError`，
      以保持 `build_func_op(...) -> KernelCodeError` 的既有公开合同。
    - 已带 `MlirGenModuleError: ...` 前缀的 module-builder 公开失败消息继续原样透传，不在这里被误改写。

    使用示例:
    - result_type = _emit_result_type_with_public_diagnostics(expr, preview_ctx, func_ast.location)

    关联文件:
    - spec: [spec/dsl/mlir_gen.md](spec/dsl/mlir_gen.md)
    - test: [test/dsl/ast/test_visitor_integration.py](test/dsl/ast/test_visitor_integration.py)
    - 功能实现: [kernel_gen/dsl/mlir_gen/function_builder.py](kernel_gen/dsl/mlir_gen/function_builder.py)
    """

    try:
        return emit_mlir(expr, ctx).type
    except ValueError as exc:
        if (
            not hasattr(exc, "location")
            and "Implicit broadcast dimension mismatch" not in str(exc)
        ):
            raise
        raise KernelCodeError(ErrorKind.CONTRACT, ErrorModule.MLIR_GEN, 
            str(exc),
            location=getattr(exc, "location", None)
            or getattr(expr, "location", None)
            or fallback_location,
        ) from exc


def build_func_op_from_ast(
    func_ast: FunctionAST,
    runtime_args: tuple[object, ...] | list[object] | None = None,
) -> func.FuncOp:
    """从 `FunctionAST` 生成 MLIR `func.func`。

    创建者: 金铲铲大作战
    最后一次更改: 金铲铲大作战

    功能说明:
    - 调用内部构建流程生成 `func.FuncOp`。
    - 将 `KernelCodeError` 统一转换为 `KernelCodeError`。

    参数说明:
    - func_ast: 已解析的函数 AST。
    - runtime_args: 运行时参数，用于推导标量类型/符号表达式。
    返回说明:
    - 返回构建完成的 `func.FuncOp`。

    限制与异常:
    - 语义检查或下沉失败会抛出 `KernelCodeError`。

    使用示例:
    - func_op = build_func_op_from_ast(func_ast, runtime_args=runtime_args)

    关联文件:
    - spec: [spec/dsl/mlir_gen.md](spec/dsl/mlir_gen.md)
    - test: [test/dsl/mlir_gen/test_function_builder.py](test/dsl/mlir_gen/test_function_builder.py)
    - 功能实现: [kernel_gen/dsl/mlir_gen/function_builder.py](kernel_gen/dsl/mlir_gen/function_builder.py)
    """

    try:
        return _build_func_op_from_ast_impl(func_ast, runtime_args=runtime_args)
    except KernelCodeError as exc:
        raise KernelCodeError(
            ErrorKind.CONTRACT,
            ErrorModule.AST,
            exc.message(),
            location=getattr(exc, "location", None),
        ) from exc
