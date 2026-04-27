"""mlir_gen module builder.

创建者: 朽木露琪亚
最后一次更改: 小李飞刀

功能说明:
- 负责从根函数生成 builtin.module，并收集 callee func.func。
- 管理 callee 的签名一致性、递归检测与排序规则。

API 列表:
- MlirGenModuleError(reason)
- mlir_gen(fn, *runtime_args, globals=None, builtins=None, config=None)

使用示例:
- module = mlir_gen(main, Memory([4], NumericType.Float32))

关联文件:
- spec: [spec/dsl/mlir_gen.md](spec/dsl/mlir_gen.md)
- test: [test/dsl/mlir_gen/test_module_builder.py](test/dsl/mlir_gen/test_module_builder.py)
- 功能实现: [kernel_gen/dsl/mlir_gen/module_builder.py](kernel_gen/dsl/mlir_gen/module_builder.py)
"""

from __future__ import annotations

import inspect
import re
from collections.abc import Callable

import sympy as sp
from xdsl.dialects import func
from xdsl.dialects.builtin import (
    ArrayAttr,
    BFloat16Type,
    Float16Type,
    Float64Type,
    IntAttr,
    IntegerType,
    ModuleOp,
    Signedness,
    StringAttr,
    f32,
    i1,
    i32,
)

from kernel_gen.dialect.nn import NnMemoryType
from kernel_gen.dialect.symbol import SymbolValueType
from kernel_gen.dsl.ast import AstParseError
from kernel_gen.dsl.ast.visitor import AstVisitorError
from kernel_gen.dsl.ast.parser import parse_function_with_env
from kernel_gen.dsl.mlir_gen.function_builder import build_func_op_from_ast
from kernel_gen.symbol_variable.memory import Memory, MemorySpace
from kernel_gen.symbol_variable.symbol_dim import SymbolDim
from kernel_gen.symbol_variable.type import NumericType

_CALLEE_REGISTRY_CONFIG_KEY = "__mlir_gen_callee_registry__"
_CALLEE_COMPILER_CONFIG_KEY = "__mlir_gen_callee_compiler__"


def _raise_visitor_error_from_parse_error(
    exc: AstParseError,
    *,
    value_messages: tuple[str, ...] = (),
) -> None:
    """把 AstParseError 翻译为当前文件沿用的公开错误合同。"""

    location = exc.diagnostics[0].location if exc.diagnostics else None
    if exc.message in value_messages:
        raise ValueError(exc.message) from exc
    if exc.message.endswith("space must be MemorySpace") or exc.message == "cast dtype must be NumericType":
        raise TypeError(exc.message) from exc
    raise AstVisitorError(exc.message, location=location) from exc


def _build_parse_environment(
    fn: Callable[..., object],
    globals_table: dict[str, object] | None,
    builtins_table: dict[str, object] | object | None,
) -> tuple[dict[str, object], dict[str, object]]:
    """构造 `mlir_gen(...)` 解析阶段使用的 globals/builtins 表。

    创建者: 小李飞刀
    最后一次更改: 小李飞刀

    功能说明:
    - 以 `fn.__globals__` 与 `inspect.getclosurevars(fn).nonlocals` 作为基础解析环境。
    - `globals_table` 允许追加或覆盖全局名称，`builtins_table` 允许覆盖内建表。
    - 只在当前文件内部使用，避免 `module_builder` 再跨文件依赖 `parse_env` 私有 helper。

    使用示例:
    - globals_map, builtins_map = _build_parse_environment(fn, globals_table=None, builtins_table=None)

    关联文件:
    - spec: [spec/dsl/mlir_gen.md](spec/dsl/mlir_gen.md)
    - test: [test/dsl/mlir_gen/test_module_builder.py](test/dsl/mlir_gen/test_module_builder.py)
    - 功能实现: [kernel_gen/dsl/mlir_gen/module_builder.py](kernel_gen/dsl/mlir_gen/module_builder.py)
    """

    merged_globals = dict(getattr(fn, "__globals__", {}) or {})
    merged_globals.update(inspect.getclosurevars(fn).nonlocals)
    if globals_table is not None:
        merged_globals.update(globals_table)
    builtins_obj = builtins_table if builtins_table is not None else merged_globals.get("__builtins__", {})
    if isinstance(builtins_obj, dict):
        merged_builtins = builtins_obj
    else:
        merged_builtins = getattr(builtins_obj, "__dict__", {})
    return merged_globals, merged_builtins


def _build_runtime_table(
    fn: Callable[..., object],
    runtime_args: tuple[object, ...] | list[object],
) -> dict[str, object] | None:
    """构造 `parse_function_with_env(...)` 需要的 runtime_table。

    创建者: 小李飞刀
    最后一次更改: 小李飞刀

    功能说明:
    - 仅在 `runtime_args` 非空且与所有可位置绑定参数一一对应时返回名称映射。
    - 参数数量不匹配时返回 None，保持解析阶段行为不被额外篡改。

    使用示例:
    - runtime_table = _build_runtime_table(fn, runtime_args)

    关联文件:
    - spec: [spec/dsl/mlir_gen.md](spec/dsl/mlir_gen.md)
    - test: [test/dsl/mlir_gen/test_module_builder.py](test/dsl/mlir_gen/test_module_builder.py)
    - 功能实现: [kernel_gen/dsl/mlir_gen/module_builder.py](kernel_gen/dsl/mlir_gen/module_builder.py)
    """

    if not runtime_args:
        return None
    signature = inspect.signature(fn)
    positional_params = [
        param
        for param in signature.parameters.values()
        if param.kind in (inspect.Parameter.POSITIONAL_ONLY, inspect.Parameter.POSITIONAL_OR_KEYWORD)
    ]
    if len(runtime_args) != len(positional_params):
        return None
    return {param.name: runtime_args[index] for index, param in enumerate(positional_params)}


def _parse_symbolic_dim_expr(expr: str) -> sp.Basic | None:
    """解析 `!symbol.int<expr>` 内的表达式文本。

    创建者: 小李飞刀
    最后一次更改: 小李飞刀

    功能说明:
    - 接受不含 `?` 的表达式字符串并尝试转为 `sympy` 表达式。
    - 解析失败时返回 None，供 `mlir_gen(...)` 退回按原始文本构造 `SymbolDim`。

    使用示例:
    - parsed = _parse_symbolic_dim_expr("M + 1")

    关联文件:
    - spec: [spec/dsl/mlir_gen.md](spec/dsl/mlir_gen.md)
    - test: [test/dsl/mlir_gen/test_module_builder.py](test/dsl/mlir_gen/test_module_builder.py)
    - 功能实现: [kernel_gen/dsl/mlir_gen/module_builder.py](kernel_gen/dsl/mlir_gen/module_builder.py)
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


def _shape_attr_to_symbol_dim(entry: IntAttr | StringAttr, location: object | None) -> SymbolDim:
    """将 `nn.memory` 的 shape/stride 条目转为 `SymbolDim`。

    创建者: 小李飞刀
    最后一次更改: 小李飞刀

    功能说明:
    - 支持静态整数和显式字符串表达式。
    - 命中匿名动态维 `?` 时拒绝转换，避免 callee runtime_args 带入不完整空间信息。

    使用示例:
    - dim = _shape_attr_to_symbol_dim(IntAttr(4), location=None)

    关联文件:
    - spec: [spec/dsl/mlir_gen.md](spec/dsl/mlir_gen.md)
    - test: [test/dsl/mlir_gen/test_module_builder.py](test/dsl/mlir_gen/test_module_builder.py)
    - 功能实现: [kernel_gen/dsl/mlir_gen/module_builder.py](kernel_gen/dsl/mlir_gen/module_builder.py)
    """

    if isinstance(entry, IntAttr):
        return SymbolDim(entry.data)
    if isinstance(entry, StringAttr) and entry.data != "?":
        return SymbolDim(entry.data)
    raise MlirGenModuleError("unsupported callee function")


def _xdsl_element_type_to_numeric_type(element_type: object) -> NumericType:
    """将 xDSL element type 还原为 `NumericType`。

    创建者: 小李飞刀
    最后一次更改: 小李飞刀

    功能说明:
    - 仅覆盖 `module_builder` 组装 callee runtime_args 所需的稳定数值类型映射。
    - 不支持的 element_type 统一按 `unsupported callee function` 处理。

    使用示例:
    - dtype = _xdsl_element_type_to_numeric_type(f32)

    关联文件:
    - spec: [spec/dsl/mlir_gen.md](spec/dsl/mlir_gen.md)
    - test: [test/dsl/mlir_gen/test_module_builder.py](test/dsl/mlir_gen/test_module_builder.py)
    - 功能实现: [kernel_gen/dsl/mlir_gen/module_builder.py](kernel_gen/dsl/mlir_gen/module_builder.py)
    """

    if isinstance(element_type, BFloat16Type):
        return NumericType.BFloat16
    if isinstance(element_type, Float16Type):
        return NumericType.Float16
    if element_type == f32:
        return NumericType.Float32
    if isinstance(element_type, Float64Type):
        return NumericType.Float64
    if element_type == i1:
        return NumericType.Bool
    if isinstance(element_type, IntegerType):
        width = element_type.width.data
        signedness = element_type.signedness.data
        if signedness == Signedness.UNSIGNED:
            if width == 8:
                return NumericType.Uint8
            if width == 16:
                return NumericType.Uint16
            if width == 32:
                return NumericType.Uint32
            if width == 64:
                return NumericType.Uint64
        if width == 8:
            return NumericType.Int8
        if width == 16:
            return NumericType.Int16
        if width == 32:
            return NumericType.Int32
        if width == 64:
            return NumericType.Int64
    raise MlirGenModuleError("unsupported callee function")


def _nn_memory_type_to_runtime_memory(memory_type: NnMemoryType, location: object | None) -> Memory:
    """将 `NnMemoryType` 还原为 `module_builder` 所需的运行时 `Memory`。

    创建者: 小李飞刀
    最后一次更改: 小李飞刀

    功能说明:
    - 读取 `nn.memory` 的 `shape/stride/element_type/space`，构造 callee 编译用 `runtime_args`。
    - 只承接当前公开合同允许的显式维度与公开 memory space。

    使用示例:
    - runtime_memory = _nn_memory_type_to_runtime_memory(memory_type, location=None)

    关联文件:
    - spec: [spec/dsl/mlir_gen.md](spec/dsl/mlir_gen.md)
    - test: [test/dsl/mlir_gen/test_module_builder.py](test/dsl/mlir_gen/test_module_builder.py)
    - 功能实现: [kernel_gen/dsl/mlir_gen/module_builder.py](kernel_gen/dsl/mlir_gen/module_builder.py)
    """

    shape = [_shape_attr_to_symbol_dim(dim_attr, location) for dim_attr in memory_type.shape.data]
    stride = [_shape_attr_to_symbol_dim(dim_attr, location) for dim_attr in memory_type.stride.data]
    dtype = _xdsl_element_type_to_numeric_type(memory_type.element_type)
    space_name = memory_type.space.space.data
    space_map = {
        "global": MemorySpace.GM,
        "shared": MemorySpace.SM,
        "local": MemorySpace.LM,
        "tsm": MemorySpace.TSM,
        "tlm1": MemorySpace.TLM1,
        "tlm2": MemorySpace.TLM2,
        "tlm3": MemorySpace.TLM3,
    }
    space = space_map.get(space_name)
    if space is None:
        raise MlirGenModuleError("unsupported callee function")
    return Memory(shape, dtype, space=space, stride=stride)


class MlirGenModuleError(ValueError):
    """`mlir_gen(...)` module 组装阶段错误。

    创建者: 小李飞刀
    最后一次更改: 小李飞刀

    功能说明:
    - 统一承载 `mlir_gen(...)` 公开合同中的失败短语。
    - 当前固定短语为：
      - `MlirGenModuleError: unsupported callee function`
      - `MlirGenModuleError: recursive callee graph is not supported`
      - `MlirGenModuleError: inconsistent callee signature`

    使用示例:
    - raise MlirGenModuleError("unsupported callee function")

    关联文件:
    - spec: [spec/dsl/mlir_gen.md](spec/dsl/mlir_gen.md)
    - test: [test/dsl/mlir_gen/test_module_builder.py](test/dsl/mlir_gen/test_module_builder.py)
    - 功能实现: [kernel_gen/dsl/mlir_gen/module_builder.py](kernel_gen/dsl/mlir_gen/module_builder.py)
    """

    def __init__(self, reason: str) -> None:
        super().__init__(f"MlirGenModuleError: {reason}")


def _is_supported_python_callee(fn: object) -> bool:
    """判断是否属于 `mlir_gen(...)` 支持的 Python callee。

    创建者: 小李飞刀
    最后一次更改: 小李飞刀

    功能说明:
    - 仅支持具备稳定名称的 Python function。
    - lambda 与本地闭包函数不在当前支持范围。

    使用示例:
    - assert _is_supported_python_callee(helper) is True

    关联文件:
    - spec: [spec/dsl/mlir_gen.md](spec/dsl/mlir_gen.md)
    - test: [test/dsl/mlir_gen/test_module_builder.py](test/dsl/mlir_gen/test_module_builder.py)
    - 功能实现: [kernel_gen/dsl/mlir_gen/module_builder.py](kernel_gen/dsl/mlir_gen/module_builder.py)
    """

    if not inspect.isfunction(fn):
        return False
    name = getattr(fn, "__name__", "")
    if not isinstance(name, str) or name == "" or name == "<lambda>":
        return False
    closure_vars = inspect.getclosurevars(fn).nonlocals
    if closure_vars:
        return False
    return True


def _runtime_args_from_callee_signature(
    arg_types: list[object],
    location: object | None,
) -> list[object]:
    """将 call-site 的 xDSL 类型列表转换为 callee 编译所需 runtime_args。

    创建者: 小李飞刀
    最后一次更改: 小李飞刀

    功能说明:
    - `nn.memory` 参数转换为 `Memory`，用于复用 `build_func_op_from_ast(...)` 的签名推导路径。
    - `!symbol.int<expr>` 参数转换为 `SymbolDim(expr)`，确保 symbol 语义不退回 `i32`。
    - 纯 `i32` 标量参数统一用 `0` 占位，仅用于类型分流。

    使用示例:
    - runtime_args = _runtime_args_from_callee_signature([nn_type], location=None)

    关联文件:
    - spec: [spec/dsl/mlir_gen.md](spec/dsl/mlir_gen.md)
    - test: [test/dsl/mlir_gen/test_module_builder.py](test/dsl/mlir_gen/test_module_builder.py)
    - 功能实现: [kernel_gen/dsl/mlir_gen/module_builder.py](kernel_gen/dsl/mlir_gen/module_builder.py)
    """

    runtime_args: list[object] = []
    for arg_type in arg_types:
        if isinstance(arg_type, NnMemoryType):
            runtime_args.append(_nn_memory_type_to_runtime_memory(arg_type, location))
            continue
        if isinstance(arg_type, SymbolValueType):
            expr_text = arg_type.expr.expr.data
            parsed = _parse_symbolic_dim_expr(expr_text)
            if parsed is None:
                runtime_args.append(SymbolDim(expr_text))
            else:
                runtime_args.append(SymbolDim(parsed))
            continue
        if arg_type == i32:
            runtime_args.append(0)
            continue
        raise MlirGenModuleError("unsupported callee function")
    return runtime_args


def mlir_gen(
    fn: Callable[..., object],
    *runtime_args: object,
    globals: dict[str, object] | None = None,
    builtins: dict[str, object] | object | None = None,
    config: dict[str, object] | None = None,
) -> ModuleOp:
    """从 Python 根函数生成 `builtin.module`。

    创建者: 小李飞刀
    最后一次更改: 小李飞刀

    功能说明:
    - 基于 `build_func_op_from_ast(...)` 生成根函数的 `func.func`，并包装为 `builtin.module`。
    - 当函数体出现“应当表达为 `func.call` 的 Python callee 调用”时，自动补齐 callee 的 `func.func`。
    - callee 收集范围为从根函数出发的传递闭包，module 内函数顺序为 root + DFS。
    - 递归调用、不一致签名与不支持 callee 形式必须失败并返回固定短语。

    使用示例:
    - module = mlir_gen(main, Memory([4], NumericType.Float32))

    关联文件:
    - spec: [spec/dsl/mlir_gen.md](spec/dsl/mlir_gen.md)
    - test: [test/dsl/mlir_gen/test_module_builder.py](test/dsl/mlir_gen/test_module_builder.py)
    - 功能实现: [kernel_gen/dsl/mlir_gen/module_builder.py](kernel_gen/dsl/mlir_gen/module_builder.py)
    """

    callee_registry: dict[object, func.FuncOp] = {}
    callee_dfs_order: list[object] = []
    callee_signatures: dict[object, tuple[object, ...]] = {}
    compiling: set[object] = set()

    lowering_config: dict[str, object] = dict(config or {})
    lowering_config[_CALLEE_REGISTRY_CONFIG_KEY] = callee_registry

    def _ensure_callee_compiled(callee: object, arg_types: list[object], location: object | None) -> None:
        """确保 Python callee 已编译为 `func.func` 并注册到当前 module 构建上下文。

        创建者: 小李飞刀
        最后一次更改: 金铲铲大作战

        功能说明:
        - 校验 callee 是否属于当前 `mlir_gen(...)` 支持的普通 Python 函数调用形式。
        - 基于 call-site 的 `arg_types` 推导并缓存 callee 的稳定签名；若同一 callee 在不同调用点推导出不一致签名则失败。
        - 维护 DFS 收集顺序与递归检测：避免重复编译，并显式拒绝递归 callee 图。
        - 将编译产物写入 `callee_registry`，供 `mlir_gen(...)` 最终组装 `builtin.module` 复用。
        - 调用当前文件内的 runtime-table helper 以支持无注解 callee 的解析。

        使用示例:
        - _ensure_callee_compiled(helper, [i32], location=None)

        关联文件:
        - spec: [spec/dsl/mlir_gen.md](spec/dsl/mlir_gen.md)
        - test: [test/dsl/mlir_gen/test_module_builder.py](test/dsl/mlir_gen/test_module_builder.py)
        - 功能实现: [kernel_gen/dsl/mlir_gen/module_builder.py](kernel_gen/dsl/mlir_gen/module_builder.py)
        """

        if not _is_supported_python_callee(callee):
            raise MlirGenModuleError("unsupported callee function")

        signature = tuple(arg_types)
        existing_signature = callee_signatures.get(callee)
        if existing_signature is not None and existing_signature != signature:
            raise MlirGenModuleError("inconsistent callee signature")

        if callee in compiling:
            raise MlirGenModuleError("recursive callee graph is not supported")
        if callee in callee_registry:
            return

        callee_signatures[callee] = signature
        callee_dfs_order.append(callee)
        compiling.add(callee)
        try:
            callee_runtime_args = _runtime_args_from_callee_signature(list(signature), location)
            callee_globals, callee_builtins = _build_parse_environment(callee, globals, builtins)
            callee_runtime_table = _build_runtime_table(callee, callee_runtime_args)
            parse_config: dict[str, object] = dict(config or {})
            parse_config["reject_external_values"] = True
            parse_config["allow_python_callee_calls"] = True
            try:
                callee_ast = parse_function_with_env(
                    callee,
                    globals_table=callee_globals,
                    builtins_table=callee_builtins,
                    runtime_table=callee_runtime_table,
                    config=parse_config,
                )
            except AstParseError as exc:
                _raise_visitor_error_from_parse_error(
                    exc,
                    value_messages=("get_dynamic_memory space must be on-chip MemorySpace",),
                )
            callee_registry[callee] = build_func_op_from_ast(
                callee_ast,
                runtime_args=callee_runtime_args,
                config=lowering_config,
            )
        finally:
            compiling.remove(callee)

    lowering_config[_CALLEE_COMPILER_CONFIG_KEY] = _ensure_callee_compiled

    root_globals, root_builtins = _build_parse_environment(fn, globals, builtins)
    root_runtime_table = _build_runtime_table(fn, runtime_args)
    parse_config = dict(config or {})
    parse_config["reject_external_values"] = True
    parse_config["allow_python_callee_calls"] = True
    try:
        func_ast = parse_function_with_env(
            fn,
            globals_table=root_globals,
            builtins_table=root_builtins,
            runtime_table=root_runtime_table,
            config=parse_config,
        )
    except AstParseError as exc:
        _raise_visitor_error_from_parse_error(
            exc,
            value_messages=("get_dynamic_memory space must be on-chip MemorySpace",),
        )

    compiling.add(fn)
    try:
        root_func_op = build_func_op_from_ast(func_ast, runtime_args=runtime_args, config=lowering_config)
    finally:
        compiling.remove(fn)

    ordered_ops = [root_func_op]
    for callee in callee_dfs_order:
        ordered_ops.append(callee_registry[callee])
    return ModuleOp(ordered_ops)
