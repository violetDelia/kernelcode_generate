"""mlir_gen error conversion tests.

创建者: 金铲铲大作战
最后一次更改: 金铲铲大作战

功能说明:
- 覆盖 kernel_gen.dsl.mlir_gen.errors 中的 AstParseError 翻译逻辑。

当前覆盖率信息:
- 当前覆盖率: 未统计（本任务验证未启用 coverage 统计）。
- 达标判定: 待后续补充统计结果。

覆盖率命令:
- pytest -q --cov=kernel_gen.dsl.mlir_gen.errors --cov-branch --cov-report=term-missing test/dsl/mlir_gen/test_errors.py

使用示例:
- pytest -q test/dsl/mlir_gen/test_errors.py

关联文件:
- 功能实现: [kernel_gen/dsl/mlir_gen/errors.py](kernel_gen/dsl/mlir_gen/errors.py)
- Spec 文档: [spec/dsl/mlir_gen.md](spec/dsl/mlir_gen.md)
- 测试文件: [test/dsl/mlir_gen/test_errors.py](test/dsl/mlir_gen/test_errors.py)
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from kernel_gen.dsl.ast import AstParseError, Diagnostic
from kernel_gen.dsl.ast.visitor import AstVisitorError
from kernel_gen.dsl.mlir_gen.errors import raise_visitor_error_from_parse_error


def _parse_error(message: str) -> AstParseError:
    """构造用于错误翻译测试的 AstParseError。

    创建者: 金铲铲大作战
    最后一次更改: 金铲铲大作战

    功能说明:
    - 生成只包含单条 diagnostic 的 AstParseError，便于直接覆盖翻译逻辑。

    使用示例:
    - exc = _parse_error("cast dtype must be NumericType")

    关联文件:
    - 功能实现: [kernel_gen/dsl/mlir_gen/errors.py](kernel_gen/dsl/mlir_gen/errors.py)
    - 测试文件: [test/dsl/mlir_gen/test_errors.py](test/dsl/mlir_gen/test_errors.py)
    """

    return AstParseError(message, [Diagnostic(message, location=None)])


def test_raise_visitor_error_from_parse_error_maps_value_message() -> None:
    exc = _parse_error("get_dynamic_memory space must be on-chip MemorySpace")

    with pytest.raises(ValueError) as excinfo:
        raise_visitor_error_from_parse_error(
            exc,
            value_messages=("get_dynamic_memory space must be on-chip MemorySpace",),
        )

    assert str(excinfo.value) == "get_dynamic_memory space must be on-chip MemorySpace"


def test_raise_visitor_error_from_parse_error_maps_type_message() -> None:
    exc = _parse_error("slice space must be MemorySpace")

    with pytest.raises(TypeError) as excinfo:
        raise_visitor_error_from_parse_error(exc)

    assert str(excinfo.value) == "slice space must be MemorySpace"


def test_raise_visitor_error_from_parse_error_falls_back_to_astvisitorerror() -> None:
    exc = _parse_error("unsupported parse shape")

    with pytest.raises(AstVisitorError) as excinfo:
        raise_visitor_error_from_parse_error(exc)

    assert "unsupported parse shape" in str(excinfo.value)
