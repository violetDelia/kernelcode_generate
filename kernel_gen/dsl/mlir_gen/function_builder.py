"""mlir_gen function builder.

创建者: 朽木露琪亚
最后一次更改: jcc你莫辜负

功能说明:
- 提供 build_func_op/build_func_op_from_ast 的公开入口。
- 负责函数签名、返回类型与函数体装配，不处理 module 组装。

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
from collections.abc import Callable

from xdsl.dialects import func
from xdsl.dialects.builtin import ArrayAttr, FunctionType, IntAttr, StringAttr, i8
from xdsl.ir import Block, Region

from kernel_gen.dialect.arch import ArchGetDynamicMemoryOp
from kernel_gen.dialect.nn import NnMemoryType
from kernel_gen.dialect.symbol import SymbolValueType
from kernel_gen.dsl.ast import (
    AstParseError,
    DmaAllocAST,
    DmaViewAST,
    FunctionAST,
    NnReduceAST,
    ScalarArgAST,
    TensorAST,
)
from kernel_gen.dsl.ast_visitor import AstVisitor, AstVisitorError
from kernel_gen.dsl.mlir_gen.emit.core import (
    EmitContext,
    _LoweringError,
    _ensure_supported_statements,
    _expr_key,
    _infer_expr_type,
    _parse_reduce_axis_expr,
    _resolve_static_index_expr,
)
from kernel_gen.dsl.mlir_gen.parse_env import _parse_function_with_env
from kernel_gen.dsl.mlir_gen.signature import (
    _build_dma_alloc_only_result_type,
    _build_signature_types,
    _function_has_value_return,
    _is_dma_alloc_only_function,
    _is_zero_return_statement_expr,
    _validate_return_type,
)
from kernel_gen.symbol_variable.memory import Memory

_DYNAMIC_MEMORY_SYMBOL_NAMES = {
    "shared": "SM_SIZE",
    "local": "LM_SIZE",
    "tsm": "TSM_SIZE",
    "tlm1": "TLM1_SIZE",
    "tlm2": "TLM2_SIZE",
    "tlm3": "TLM3_SIZE",
}


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
        if (
            exc.message == "slice space must be MemorySpace"
            or exc.message == "cast dtype must be NumericType"
            or exc.message == "alloc space must be MemorySpace"
        ):
            raise TypeError(exc.message) from exc
        raise AstVisitorError(exc.message, location=location) from exc
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
    if has_value_return:
        return_expr = last_stmt
        if is_dma_alloc_only:
            if not isinstance(return_expr, DmaAllocAST):
                raise _LoweringError("Return type does not match annotation", location=func_ast.location)
            result_type = _build_dma_alloc_only_result_type(func_ast, return_expr, runtime_args)
        else:
            if isinstance(return_expr, NnReduceAST) and return_expr.kind == "reduce_max":
                input_type = _infer_expr_type(
                    return_expr.value, dict(type_map), runtime_values=runtime_values, config=config
                )
                if isinstance(input_type, NnMemoryType):
                    axes = _parse_reduce_axis_expr(return_expr.axis, return_expr.location)
                    if axes is not None:
                        rank = len(input_type.shape.data)
                        for axis_value in axes:
                            if axis_value < -rank or axis_value >= rank:
                                raise _LoweringError(
                                    f"{return_expr.kind} axis must be within [-{rank}, {rank - 1}]",
                                    location=return_expr.location,
                                )
            result_type = _infer_result_type_with_public_diagnostics(
                return_expr,
                dict(type_map),
                runtime_values=runtime_values,
                config=config,
                fallback_location=func_ast.location,
            )
        if func_ast.outputs:
            _validate_return_type(func_ast, result_type, return_expr, dict(type_map))
        type_map[_expr_key(return_expr)] = result_type
        result_types = [result_type]
    elif not func_ast.returns_none and not _is_zero_return_statement_expr(last_stmt):
        raise _LoweringError(
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
            raise _LoweringError("Function body is empty", location=func_ast.location)
        block.add_op(func.ReturnOp(return_value))
    else:
        block.add_op(func.ReturnOp())
    _rewrite_dynamic_memory_result_types(func_op)
    return func_op


def _infer_result_type_with_public_diagnostics(
    expr: object,
    type_map: dict[str, object],
    runtime_values: dict[str, object] | None,
    config: dict[str, object],
    fallback_location: object,
) -> object:
    """在 `build_func_op` 公开入口中规整返回类型推导诊断。

    创建者: 小李飞刀
    最后一次更改: 小李飞刀

    功能说明:
    - 调用 `_infer_expr_type(...)` 推导返回表达式类型。
    - 将隐式 broadcast 维度不匹配重新包装为带位置信息的 `_LoweringError`，
      以保持 `build_func_op(...) -> AstVisitorError` 的既有公开合同。

    使用示例:
    - result_type = _infer_result_type_with_public_diagnostics(expr, type_map, runtime_values, config, func_ast.location)

    关联文件:
    - spec: [spec/dsl/mlir_gen.md](spec/dsl/mlir_gen.md)
    - test: [test/dsl/test_ast_visitor.py](test/dsl/test_ast_visitor.py)
    - 功能实现: [kernel_gen/dsl/mlir_gen/function_builder.py](kernel_gen/dsl/mlir_gen/function_builder.py)
    """

    try:
        return _infer_expr_type(expr, type_map, runtime_values=runtime_values, config=config)
    except ValueError as exc:
        if "Implicit broadcast dimension mismatch" not in str(exc):
            raise
        raise _LoweringError(
            str(exc),
            location=getattr(expr, "location", None) or fallback_location,
        ) from exc


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
    - test: [test/dsl/mlir_gen/test_function_builder.py](test/dsl/mlir_gen/test_function_builder.py)
    - 功能实现: [kernel_gen/dsl/mlir_gen/function_builder.py](kernel_gen/dsl/mlir_gen/function_builder.py)
    """

    try:
        return _build_func_op_from_ast_impl(func_ast, runtime_args=runtime_args, config=config)
    except _LoweringError as exc:
        raise AstVisitorError(str(exc), location=exc.location) from exc
