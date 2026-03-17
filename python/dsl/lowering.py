"""Lowering utilities for DSL AST to nn dialect IR.

创建者: 小李飞刀
最后一次更改: 小李飞刀

功能说明:
- 提供从 DSL AST 到 nn dialect IR 的最小 lowering 入口。

使用示例:
- from python.dsl.lowering import lower_to_nn_ir
- module = lower_to_nn_ir(func_ast)

关联文件:
- spec: spec/dsl/lowering.md
- test: test/dsl/test_ast_visitor.py
- 功能实现: python/dsl/lowering.py
"""

from __future__ import annotations

from typing import Iterable

from xdsl.dialects import func
from xdsl.dialects.builtin import ArrayAttr, FunctionType, IntAttr, ModuleOp, StringAttr, i1, i32, f32
from xdsl.ir import Block, Region

from python.dialect.nn import (
    NnAddOp,
    NnEqOp,
    NnGeOp,
    NnGtOp,
    NnLeOp,
    NnLtOp,
    NnMemorySpaceAttr,
    NnMemoryType,
    NnMulOp,
    NnNeOp,
    NnSubOp,
    NnTrueDivOp,
)
from python.symbol_variable.memory import Memory, MemorySpace
from python.symbol_variable.type import NumericType

from .ast import (
    BinaryExprAST,
    CompareExprAST,
    ConstAST,
    FunctionAST,
    ScalarArgAST,
    SourceLocation,
    TensorAST,
)


_MEMORY_SPACE_MAP = {
    MemorySpace.GM: "global",
    MemorySpace.SM: "shared",
    MemorySpace.LM: "local",
    MemorySpace.TSM: "shared",
    MemorySpace.TLM: "local",
}


class LoweringError(ValueError):
    """lowering 阶段错误。

    创建者: 小李飞刀
    最后一次更改: 小李飞刀

    功能说明:
    - 用于包装 lowering 中的输入错误或不支持路径。

    使用示例:
    - raise LoweringError("Unsupported AST node", location=None)

    关联文件:
    - spec: spec/dsl/lowering.md
    - test: test/dsl/test_ast_visitor.py
    - 功能实现: python/dsl/lowering.py
    """

    def __init__(self, message: str, location: SourceLocation | None = None) -> None:
        super().__init__(message)
        self.location = location


def _dtype_to_xdsl(dtype: NumericType) -> object:
    """将 NumericType 映射为 xdsl 类型。

    创建者: 小李飞刀
    最后一次更改: 小李飞刀

    功能说明:
    - 支持 int32 与 float32 的映射。

    使用示例:
    - _dtype_to_xdsl(NumericType.Float32)

    关联文件:
    - spec: spec/dsl/lowering.md
    - test: test/dsl/test_ast_visitor.py
    - 功能实现: python/dsl/lowering.py
    """

    if dtype is NumericType.Float32:
        return f32
    if dtype is NumericType.Int32:
        return i32
    raise LoweringError(f"Unsupported dtype: {dtype}")


def _build_stride(shape: list[int | str]) -> list[int | str]:
    """根据 shape 生成默认连续 stride。

    创建者: 小李飞刀
    最后一次更改: 小李飞刀

    功能说明:
    - 当遇到动态维度时使用 "?" 填充。

    使用示例:
    - _build_stride([2, 3])

    关联文件:
    - spec: spec/dsl/lowering.md
    - test: test/dsl/test_ast_visitor.py
    - 功能实现: python/dsl/lowering.py
    """

    stride: list[int | str] = []
    acc = 1
    for dim in reversed(shape):
        if isinstance(dim, int):
            stride.insert(0, acc)
            acc *= dim
        else:
            stride.insert(0, "?")
    return stride


def _dim_to_attr(value: int | str) -> object:
    """将维度值转换为 xdsl attribute。

    创建者: 小李飞刀
    最后一次更改: 小李飞刀

    功能说明:
    - 整数转 IntAttr，字符串转 StringAttr。

    使用示例:
    - _dim_to_attr(4)

    关联文件:
    - spec: spec/dsl/lowering.md
    - test: test/dsl/test_ast_visitor.py
    - 功能实现: python/dsl/lowering.py
    """

    if isinstance(value, int):
        return IntAttr(value)
    return StringAttr(value)


def _memory_to_nn_type(memory: Memory) -> NnMemoryType:
    """将 Memory 转换为 NnMemoryType。

    创建者: 小李飞刀
    最后一次更改: 小李飞刀

    功能说明:
    - shape/stride 映射为 ArrayAttr。
    - dtype/space 映射为 xdsl 类型与 space attribute。

    使用示例:
    - _memory_to_nn_type(Memory([1, 2], NumericType.Float32))

    关联文件:
    - spec: spec/dsl/lowering.md
    - test: test/dsl/test_ast_visitor.py
    - 功能实现: python/dsl/lowering.py
    """

    shape = memory.shape.get_values()
    stride_values = memory.stride.get_values() if memory.stride is not None else _build_stride(shape)
    shape_attr = ArrayAttr([_dim_to_attr(dim) for dim in shape])
    stride_attr = ArrayAttr([_dim_to_attr(dim) for dim in stride_values])
    element_type = _dtype_to_xdsl(memory.dtype)
    space_name = _MEMORY_SPACE_MAP.get(memory.space, "global")
    space = NnMemorySpaceAttr.from_name(space_name)
    return NnMemoryType(shape_attr, stride_attr, element_type, space)


def _ensure_supported_ast(function_ast: FunctionAST) -> BinaryExprAST | CompareExprAST | ConstAST | TensorAST:
    """校验并获取函数体的单一表达式。

    创建者: 小李飞刀
    最后一次更改: 小李飞刀

    功能说明:
    - 仅支持单个表达式节点作为函数体。

    使用示例:
    - _ensure_supported_ast(func_ast)

    关联文件:
    - spec: spec/dsl/lowering.md
    - test: test/dsl/test_ast_visitor.py
    - 功能实现: python/dsl/lowering.py
    """

    statements = function_ast.body.statements
    if len(statements) != 1:
        raise LoweringError(
            "Only single-expression function bodies are supported",
            location=function_ast.location,
        )
    expr = statements[0]
    if not isinstance(expr, (BinaryExprAST, CompareExprAST, ConstAST, TensorAST)):
        raise LoweringError(
            "Unsupported AST expression for lowering",
            location=getattr(expr, "location", None),
        )
    return expr


def lower_to_nn_ir(function_ast: FunctionAST) -> ModuleOp:
    """将 FunctionAST lowering 为 nn dialect IR module。

    创建者: 小李飞刀
    最后一次更改: 小李飞刀

    功能说明:
    - 将函数输入映射为 func.func 入口。
    - 将二元表达式映射为 nn dialect op。

    使用示例:
    - module = lower_to_nn_ir(function_ast)

    关联文件:
    - spec: spec/dsl/lowering.md
    - test: test/dsl/test_ast_visitor.py
    - 功能实现: python/dsl/lowering.py
    """

    if not function_ast.inputs:
        raise LoweringError("Function has no inputs", location=function_ast.location)

    arg_types: list[object] = []
    tensor_args: list[int] = []
    for idx, item in enumerate(function_ast.inputs):
        if isinstance(item, TensorAST):
            arg_types.append(_memory_to_nn_type(item.memory))
            tensor_args.append(idx)
        elif isinstance(item, ScalarArgAST):
            if item.value_type is int:
                arg_types.append(i32)
            else:
                raise LoweringError(
                    "Unsupported scalar argument type",
                    location=item.location,
                )
        else:
            raise LoweringError("Unsupported input type", location=getattr(item, "location", None))
    expr = _ensure_supported_ast(function_ast)
    if not tensor_args:
        raise LoweringError("At least one tensor input is required", location=function_ast.location)

    result_type = arg_types[tensor_args[0]]

    if isinstance(expr, CompareExprAST):
        result_type = NnMemoryType(
            result_type.shape,
            result_type.stride,
            i1,
            result_type.space,
        )

    func_type = FunctionType.from_lists(arg_types, [result_type])
    block = Block(arg_types=arg_types)
    region = Region(block)
    func_op = func.FuncOp(function_ast.name, func_type, region)

    tensor_values = [block.args[index] for index in tensor_args]
    op = _lower_expr_to_nn_op(expr, tensor_values, result_type)
    block.add_op(op)
    block.add_op(func.ReturnOp(op.result))

    return ModuleOp([func_op])


def _lower_expr_to_nn_op(
    expr: BinaryExprAST | CompareExprAST | ConstAST | TensorAST,
    args: Iterable[object],
    result_type: NnMemoryType,
):
    """将表达式 lowering 为 nn dialect 二元 op。

    创建者: 小李飞刀
    最后一次更改: 小李飞刀

    功能说明:
    - 支持二元算术与比较表达式。

    使用示例:
    - _lower_expr_to_nn_op(expr, args, result_type)

    关联文件:
    - spec: spec/dsl/lowering.md
    - test: test/dsl/test_ast_visitor.py
    - 功能实现: python/dsl/lowering.py
    """

    values = list(args)
    if isinstance(expr, TensorAST):
        if not values:
            raise LoweringError("No tensor operands provided", location=expr.location)
        lhs = values[0]
        return NnAddOp(lhs, lhs, result_type, result_type.space)

    if isinstance(expr, ConstAST):
        if not values:
            raise LoweringError("No tensor operands provided", location=expr.location)
        lhs = values[0]
        return NnAddOp(lhs, lhs, result_type, result_type.space)

    if isinstance(expr, BinaryExprAST):
        if len(values) < 2:
            raise LoweringError("Binary op requires two tensor operands", location=expr.location)
        lhs, rhs = values[:2]
        op_map = {
            "add": NnAddOp,
            "sub": NnSubOp,
            "mul": NnMulOp,
            "div": NnTrueDivOp,
        }
        if expr.op not in op_map:
            raise LoweringError(f"Unsupported binary op: {expr.op}", location=expr.location)
        return op_map[expr.op](lhs, rhs, result_type, result_type.space)

    if isinstance(expr, CompareExprAST):
        if len(values) < 2:
            raise LoweringError("Compare op requires two tensor operands", location=expr.location)
        lhs, rhs = values[:2]
        op_map = {
            "eq": NnEqOp,
            "ne": NnNeOp,
            "lt": NnLtOp,
            "le": NnLeOp,
            "gt": NnGtOp,
            "ge": NnGeOp,
        }
        if expr.op not in op_map:
            raise LoweringError(f"Unsupported compare op: {expr.op}", location=expr.location)
        return op_map[expr.op](lhs, rhs, result_type, result_type.space)

    raise LoweringError("Unsupported expression for lowering", location=getattr(expr, "location", None))
