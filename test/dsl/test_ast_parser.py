"""ast_parser tests.

创建者: 朽木露琪亚
最后一次更改: 朽木露琪亚

功能说明:
- 覆盖 `kernel_gen.dsl.ast.parser` 的解析入口与诊断路径。
- 覆盖 for range(..., step=0) 的解析期拒绝诊断。

当前覆盖率信息:
- 当前覆盖率: 未统计（本任务验证未启用 coverage 统计）。
- 达标判定: 待后续补充统计结果。

覆盖率命令:
- `pytest -q --cov=kernel_gen.dsl.ast.parser --cov-branch --cov-report=term-missing test/dsl/test_ast_parser.py`

使用示例:
- pytest -q test/dsl/test_ast_parser.py

关联文件:
- 功能实现: kernel_gen/dsl/ast/parser.py
- Spec 文档: spec/dsl/ast_parser.md
- 测试文件: test/dsl/test_ast_parser.py
"""

from __future__ import annotations

import sys
from pathlib import Path

import importlib
import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

parser_module = importlib.import_module("kernel_gen.dsl.ast.parser")
parse_function = parser_module.parse_function
AstParseError = parser_module.AstParseError
FunctionAST = importlib.import_module("kernel_gen.dsl.ast").FunctionAST


# AST-P-001
# 创建者: 朽木露琪亚
# 最后一次更改: 朽木露琪亚
# 最近一次运行测试时间: 2026-04-12 00:35:00 +0800
# 最近一次运行成功时间: 2026-04-12 00:35:00 +0800
# 功能说明: 解析函数生成 FunctionAST。
# 使用示例: pytest -q test/dsl/test_ast_parser.py -k test_ast_parser_builds_function_ast
# 对应功能实现文件路径: kernel_gen/dsl/ast/parser.py
# 对应 spec 文件路径: spec/dsl/ast_parser.md
# 对应测试文件路径: test/dsl/test_ast_parser.py
def test_ast_parser_builds_function_ast() -> None:
    def kernel(x: "Tensor[f32, 1]"):
        return x

    func_ast = parse_function(kernel)
    assert isinstance(func_ast, FunctionAST)
    assert func_ast.name == "kernel"
    assert func_ast.has_explicit_return is True


# AST-P-002
# 创建者: 朽木露琪亚
# 最后一次更改: 朽木露琪亚
# 最近一次运行测试时间: 2026-04-12 00:35:00 +0800
# 最近一次运行成功时间: 2026-04-12 00:35:00 +0800
# 功能说明: 解析失败时返回带位置信息的诊断。
# 使用示例: pytest -q test/dsl/test_ast_parser.py -k test_ast_parser_reports_diagnostics
# 对应功能实现文件路径: kernel_gen/dsl/ast/parser.py
# 对应 spec 文件路径: spec/dsl/ast_parser.md
# 对应测试文件路径: test/dsl/test_ast_parser.py
def test_ast_parser_reports_diagnostics() -> None:
    def kernel(x):
        return x

    with pytest.raises(AstParseError) as exc_info:
        _ = parse_function(kernel)
    assert exc_info.value.diagnostics
    assert exc_info.value.diagnostics[0].message == "Missing annotation"


# AST-P-003
# 创建者: 朽木露琪亚
# 最后一次更改: 朽木露琪亚
# 最近一次运行测试时间: 2026-04-12 00:35:00 +0800
# 最近一次运行成功时间: 2026-04-12 00:35:00 +0800
# 功能说明: 解析 helper 非法参数形态并报稳定错误。
# 使用示例: pytest -q test/dsl/test_ast_parser.py -k test_ast_parser_rejects_invalid_helper_arity
# 对应功能实现文件路径: kernel_gen/dsl/ast/parser.py
# 对应 spec 文件路径: spec/dsl/ast_parser.md
# 对应测试文件路径: test/dsl/test_ast_parser.py
def test_ast_parser_rejects_invalid_helper_arity() -> None:
    def kernel(x: "Tensor[f32, 1]"):
        from kernel_gen.operation.arch import get_block_id

        return get_block_id(1)

    with pytest.raises(AstParseError, match="Unsupported get_block_id arity"):
        _ = parse_function(kernel)


# AST-P-004
# 创建者: 小李飞刀
# 最后一次更改: 小李飞刀
# 最近一次运行测试时间: 2026-04-13 09:40:00 +0800
# 最近一次运行成功时间: 2026-04-13 09:40:00 +0800
# 功能说明: for range(..., step=0) 在解析阶段直接报错。
# 使用示例: pytest -q test/dsl/test_ast_parser.py -k test_ast_parser_rejects_zero_step
# 对应功能实现文件路径: kernel_gen/dsl/ast/parser.py
# 对应 spec 文件路径: spec/dsl/ast.md
# 对应测试文件路径: test/dsl/test_ast_parser.py
def test_ast_parser_rejects_zero_step() -> None:
    def kernel(x: "Tensor[f32, 1]"):
        for i in range(0, 4, 0):
            x = x
        return x

    with pytest.raises(AstParseError, match="for range step must not be zero"):
        _ = parse_function(kernel)
