"""mlir_gen error conversion helpers.

创建者: 金铲铲大作战
最后一次更改: 金铲铲大作战

功能说明:
- 收口 `AstParseError -> ValueError/TypeError/AstVisitorError` 的重复转换逻辑。
- 仅承载 mlir_gen 解析错误的统一翻译，不改动公开错误短语。

使用示例:
- from kernel_gen.dsl.mlir_gen.errors import raise_visitor_error_from_parse_error
- try:
    ...
  except AstParseError as exc:
    raise_visitor_error_from_parse_error(exc, value_messages=("x",))

关联文件:
- spec: [spec/dsl/mlir_gen.md](../../../spec/dsl/mlir_gen.md)
- test:
  - [test/dsl/mlir_gen/test_function_builder.py](../../../test/dsl/mlir_gen/test_function_builder.py)
  - [test/dsl/mlir_gen/test_module_builder.py](../../../test/dsl/mlir_gen/test_module_builder.py)
- 功能实现: [kernel_gen/dsl/mlir_gen/errors.py](kernel_gen/dsl/mlir_gen/errors.py)
"""

from __future__ import annotations

from kernel_gen.dsl.ast import AstParseError
from kernel_gen.dsl.ast.visitor import AstVisitorError

__all__ = ["raise_visitor_error_from_parse_error"]


def raise_visitor_error_from_parse_error(
    exc: AstParseError,
    *,
    value_messages: tuple[str, ...] = (),
) -> None:
    """把 AstParseError 翻译为既有的公开异常合同。

    创建者: 金铲铲大作战
    最后一次更改: 金铲铲大作战

    功能说明:
    - 命中 `value_messages` 时转换为 `ValueError`。
    - 命中 `space must be MemorySpace` 或 `cast dtype must be NumericType` 时转换为 `TypeError`。
    - 其余情况保持 `AstVisitorError`，并尽量保留原始 location。

    使用示例:
    - raise_visitor_error_from_parse_error(exc, value_messages=("get_dynamic_memory space must be on-chip MemorySpace",))

    关联文件:
    - spec: [spec/dsl/mlir_gen.md](../../../spec/dsl/mlir_gen.md)
    - test:
      - [test/dsl/mlir_gen/test_function_builder.py](../../../test/dsl/mlir_gen/test_function_builder.py)
      - [test/dsl/mlir_gen/test_module_builder.py](../../../test/dsl/mlir_gen/test_module_builder.py)
    - 功能实现: [kernel_gen/dsl/mlir_gen/errors.py](kernel_gen/dsl/mlir_gen/errors.py)
    """

    location = exc.diagnostics[0].location if exc.diagnostics else None
    if exc.message in value_messages:
        raise ValueError(exc.message) from exc
    if exc.message.endswith("space must be MemorySpace") or exc.message == "cast dtype must be NumericType":
        raise TypeError(exc.message) from exc
    raise AstVisitorError(exc.message, location=location) from exc
