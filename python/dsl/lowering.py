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
    LoadAST,
    ScalarArgAST,
    SourceLocation,
    StoreAST,
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


def _ensure_supported_statements(function_ast: FunctionAST) -> list[object]:
    """校验并获取函数体语句列表。

    创建者: 小李飞刀
    最后一次更改: 小李飞刀

    功能说明:
    - 允许多个表达式节点，返回列表供 lowering 顺序处理。

    使用示例:
    - statements = _ensure_supported_statements(func_ast)

    关联文件:
    - spec: spec/dsl/lowering.md
    - test: test/dsl/test_ast_visitor.py
    - 功能实现: python/dsl/lowering.py
    """

    statements = function_ast.body.statements
    if not statements:
        raise LoweringError(
            "Function body is empty",
            location=function_ast.location,
        )
    for expr in statements:
        if isinstance(expr, LoadAST):
            raise LoweringError("LoadAST lowering is not supported", location=expr.location)
        if isinstance(expr, StoreAST):
            raise LoweringError("StoreAST lowering is not supported", location=expr.location)
        if not isinstance(expr, (BinaryExprAST, CompareExprAST, ConstAST, TensorAST, ScalarArgAST)):
            raise LoweringError(
                "Unsupported AST expression for lowering",
                location=getattr(expr, "location", None),
            )
    return statements


def _expect_memory_value(value: object, location: SourceLocation | None) -> NnMemoryType:
    """校验并获取 nn memory 类型。

    创建者: 小李飞刀
    最后一次更改: 小李飞刀

    功能说明:
    - 确保值类型为 NnMemoryType。

    使用示例:
    - mem_type = _expect_memory_value(value, location)

    关联文件:
    - spec: spec/dsl/lowering.md
    - test: test/dsl/test_ast_visitor.py
    - 功能实现: python/dsl/lowering.py
    """

    if not isinstance(value.type, NnMemoryType):
        raise LoweringError("Operand must be nn.memory", location=location)
    return value.type


def _expr_key(expr: object) -> int:
    """生成表达式映射键。

    创建者: 小李飞刀
    最后一次更改: 小李飞刀

    功能说明:
    - 以对象 id 作为键，避免不可 hash 的字段影响映射。

    使用示例:
    - key = _expr_key(expr)

    关联文件:
    - spec: spec/dsl/lowering.md
    - test: test/dsl/test_ast_visitor.py
    - 功能实现: python/dsl/lowering.py
    """

    return id(expr)


def _infer_expr_type(
    expr: object,
    type_map: dict[int, object],
) -> object:
    """推断表达式对应的结果类型。

    创建者: 小李飞刀
    最后一次更改: 小李飞刀

    功能说明:
    - 复用 type_map 缓存避免重复推断。
    - 二元算术返回 operand 类型，比较返回 i1 memory。

    使用示例:
    - result_type = _infer_expr_type(expr, type_map)

    关联文件:
    - spec: spec/dsl/lowering.md
    - test: test/dsl/test_ast_visitor.py
    - 功能实现: python/dsl/lowering.py
    """

    expr_key = _expr_key(expr)
    if expr_key in type_map:
        return type_map[expr_key]

    if isinstance(expr, ConstAST):
        raise LoweringError("Constant expressions are not supported", location=expr.location)

    if isinstance(expr, LoadAST):
        raise LoweringError("LoadAST lowering is not supported", location=expr.location)

    if isinstance(expr, StoreAST):
        raise LoweringError("StoreAST lowering is not supported", location=expr.location)

    if isinstance(expr, BinaryExprAST):
        lhs_type = _infer_expr_type(expr.lhs, type_map)
        rhs_type = _infer_expr_type(expr.rhs, type_map)
        if not isinstance(lhs_type, NnMemoryType) or lhs_type != rhs_type:
            raise LoweringError("Binary op operands must have the same nn.memory type", location=expr.location)
        type_map[expr_key] = lhs_type
        return lhs_type

    if isinstance(expr, CompareExprAST):
        lhs_type = _infer_expr_type(expr.lhs, type_map)
        rhs_type = _infer_expr_type(expr.rhs, type_map)
        if not isinstance(lhs_type, NnMemoryType) or lhs_type != rhs_type:
            raise LoweringError("Compare op operands must have the same nn.memory type", location=expr.location)
        result_type = NnMemoryType(lhs_type.shape, lhs_type.stride, i1, lhs_type.space)
        type_map[expr_key] = result_type
        return result_type

    if isinstance(expr, (TensorAST, ScalarArgAST)):
        if expr_key not in type_map:
            raise LoweringError("Unknown input reference", location=getattr(expr, "location", None))
        return type_map[expr_key]

    raise LoweringError("Unsupported expression for lowering", location=getattr(expr, "location", None))


def _lower_expr(
    expr: object,
    value_map: dict[int, object],
    block: Block,
) -> object:
    """递归 lowering 表达式为 SSA value。

    创建者: 小李飞刀
    最后一次更改: 小李飞刀

    功能说明:
    - 支持二元算术与比较表达式。
    - 复用 value_map 缓存避免重复生成 op。

    使用示例:
    - value = _lower_expr(expr, value_map, block)

    关联文件:
    - spec: spec/dsl/lowering.md
    - test: test/dsl/test_ast_visitor.py
    - 功能实现: python/dsl/lowering.py
    """

    expr_key = _expr_key(expr)
    if expr_key in value_map:
        return value_map[expr_key]

    if isinstance(expr, (TensorAST, ScalarArgAST)):
        if expr_key not in value_map:
            raise LoweringError("Unknown input reference", location=getattr(expr, "location", None))
        return value_map[expr_key]

    if isinstance(expr, ConstAST):
        raise LoweringError("Constant expressions are not supported", location=expr.location)

    if isinstance(expr, LoadAST):
        raise LoweringError("LoadAST lowering is not supported", location=expr.location)

    if isinstance(expr, StoreAST):
        raise LoweringError("StoreAST lowering is not supported", location=expr.location)

    if isinstance(expr, BinaryExprAST):
        lhs = _lower_expr(expr.lhs, value_map, block)
        rhs = _lower_expr(expr.rhs, value_map, block)
        lhs_type = _expect_memory_value(lhs, expr.location)
        rhs_type = _expect_memory_value(rhs, expr.location)
        if lhs_type != rhs_type:
            raise LoweringError("Binary op operands must have the same nn.memory type", location=expr.location)
        op_map = {
            "add": NnAddOp,
            "sub": NnSubOp,
            "mul": NnMulOp,
            "div": NnTrueDivOp,
        }
        if expr.op not in op_map:
            raise LoweringError(f"Unsupported binary op: {expr.op}", location=expr.location)
        op = op_map[expr.op](lhs, rhs, lhs_type, lhs_type.space)
        block.add_op(op)
        value_map[expr_key] = op.result
        return op.result

    if isinstance(expr, CompareExprAST):
        lhs = _lower_expr(expr.lhs, value_map, block)
        rhs = _lower_expr(expr.rhs, value_map, block)
        lhs_type = _expect_memory_value(lhs, expr.location)
        rhs_type = _expect_memory_value(rhs, expr.location)
        if lhs_type != rhs_type:
            raise LoweringError("Compare op operands must have the same nn.memory type", location=expr.location)
        result_type = NnMemoryType(lhs_type.shape, lhs_type.stride, i1, lhs_type.space)
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
        op = op_map[expr.op](lhs, rhs, result_type, lhs_type.space)
        block.add_op(op)
        value_map[expr_key] = op.result
        return op.result

    raise LoweringError("Unsupported expression for lowering", location=getattr(expr, "location", None))


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
    statements = _ensure_supported_statements(function_ast)
    if not tensor_args:
        raise LoweringError("At least one tensor input is required", location=function_ast.location)

    return_expr = statements[-1]
    type_map: dict[int, object] = {}
    for idx, item in enumerate(function_ast.inputs):
        type_map[_expr_key(item)] = arg_types[idx]

    result_type = _infer_expr_type(return_expr, type_map)
    if function_ast.outputs:
        if len(function_ast.outputs) != 1:
            raise LoweringError("Only single return value is supported", location=function_ast.location)
        output = function_ast.outputs[0]
        if isinstance(output, TensorAST):
            expected_type = _memory_to_nn_type(output.memory)
        elif isinstance(output, ScalarArgAST):
            if output.value_type is int:
                expected_type = i32
            else:
                raise LoweringError("Unsupported scalar return type", location=output.location)
        else:
            raise LoweringError("Unsupported return annotation type", location=getattr(output, "location", None))
        if result_type != expected_type:
            raise LoweringError("Return type does not match annotation", location=function_ast.location)

    func_type = FunctionType.from_lists(arg_types, [result_type])
    block = Block(arg_types=arg_types)
    region = Region(block)
    func_op = func.FuncOp(function_ast.name, func_type, region)

    value_map: dict[int, object] = {}
    for idx, item in enumerate(function_ast.inputs):
        value_map[_expr_key(item)] = block.args[idx]

    for expr in statements:
        _lower_expr(expr, value_map, block)

    return_value = _lower_expr(return_expr, value_map, block)
    block.add_op(func.ReturnOp(return_value))

    return ModuleOp([func_op])
