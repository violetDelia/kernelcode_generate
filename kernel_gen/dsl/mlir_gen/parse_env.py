"""mlir_gen parse environment helpers.

创建者: 朽木露琪亚
最后一次更改: 朽木露琪亚

功能说明:
    - 负责 runtime_args、globals 与 builtins 的解析环境拼装。
    - 提供基于 AST parser 公共 API 的统一入口。

使用示例:
- globals_table, builtins_table = _build_parse_environment(fn, globals_table=None, builtins_table=None)
- func_ast = _parse_function_with_env(fn, globals_table, builtins_table, runtime_table, config=None)

关联文件:
- spec: [spec/dsl/mlir_gen.md](spec/dsl/mlir_gen.md)
- test: [test/dsl/mlir_gen/test_parse_env.py](test/dsl/mlir_gen/test_parse_env.py)
- 功能实现: [kernel_gen/dsl/mlir_gen/parse_env.py](kernel_gen/dsl/mlir_gen/parse_env.py)
"""

from __future__ import annotations

import inspect
from collections.abc import Callable

from kernel_gen.dsl.ast import AstParseError, FunctionAST
from kernel_gen.dsl.ast.parser import parse_function_with_env as ast_parse_function_with_env


def _build_parse_environment(
    fn: Callable[..., object],
    globals_table: dict[str, object] | None,
    builtins_table: dict[str, object] | object | None,
) -> tuple[dict[str, object], dict[str, object]]:
    """构造解析所需的 globals/builtins 表。

    创建者: 小李飞刀
    最后一次更改: 小李飞刀

    功能说明:
    - 以 `fn.__globals__` 与 `inspect.getclosurevars(fn).nonlocals` 作为基础解析环境。
    - 允许通过 `globals_table` 追加覆盖解析环境名称。
    - `builtins_table` 为 dict 时直接使用；否则尝试读取其 `__dict__`；为空则回退到 globals 里的 `__builtins__`。

    使用示例:
    - globals_table, builtins_table = _build_parse_environment(fn, globals_table=None, builtins_table=None)

    关联文件:
    - spec: [spec/dsl/mlir_gen.md](spec/dsl/mlir_gen.md)
    - test: [test/dsl/mlir_gen/test_parse_env.py](test/dsl/mlir_gen/test_parse_env.py)
    - 功能实现: [kernel_gen/dsl/mlir_gen/parse_env.py](kernel_gen/dsl/mlir_gen/parse_env.py)
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


def _build_runtime_table_for_signature(
    fn: Callable[..., object],
    runtime_args: tuple[object, ...] | list[object],
) -> dict[str, object] | None:
    """构造 `mlir_gen(...)` 解析阶段使用的 runtime_table。

    创建者: 金铲铲大作战
    最后一次更改: 金铲铲大作战

    功能说明:
    - 仅在 `runtime_args` 非空且与可位置绑定形参数量一致时返回参数名映射。
    - `runtime_args` 为空或数量不匹配时返回 None，保持解析阶段行为不被额外篡改。
    - 仅覆盖可位置绑定形参，忽略仅关键字与可变参数。

    使用示例:
    - runtime_table = _build_runtime_table_for_signature(fn, runtime_args)

    关联文件:
    - spec: [spec/dsl/mlir_gen.md](spec/dsl/mlir_gen.md)
    - test: [test/dsl/mlir_gen/test_parse_env.py](test/dsl/mlir_gen/test_parse_env.py)
    - 功能实现: [kernel_gen/dsl/mlir_gen/parse_env.py](kernel_gen/dsl/mlir_gen/parse_env.py)
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


def _parse_function_with_env(
    fn: Callable[..., object],
    globals_table: dict[str, object] | None,
    builtins_table: dict[str, object] | None,
    runtime_table: dict[str, object] | None,
    config: dict[str, object] | None,
) -> FunctionAST:
    """解析函数并返回 FunctionAST。

    创建者: 朽木露琪亚
    最后一次更改: 朽木露琪亚

    功能说明:
    - 复用 `kernel_gen.dsl.ast.parser.parse_function_with_env(...)` 解析函数 AST。
    - 保持 `mlir_gen` 侧环境拼装逻辑与 AST 解析逻辑分离。

    使用示例:
    - func_ast = _parse_function_with_env(fn, globals_table, builtins_table, runtime_table, config=None)

    关联文件:
    - spec: [spec/dsl/mlir_gen.md](spec/dsl/mlir_gen.md)
    - test: [test/dsl/mlir_gen/test_parse_env.py](test/dsl/mlir_gen/test_parse_env.py)
    - 功能实现: [kernel_gen/dsl/mlir_gen/parse_env.py](kernel_gen/dsl/mlir_gen/parse_env.py)
    """
    return ast_parse_function_with_env(
        fn,
        globals_table=globals_table,
        builtins_table=builtins_table,
        runtime_table=runtime_table,
        config=config,
    )
