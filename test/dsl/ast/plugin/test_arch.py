"""DSL AST arch plugin tests.


功能说明:
- 覆盖 `kernel_gen.dsl.ast.plugin.arch` 注册后的 arch helper 解析行为。
- 测试结构对应 `spec/dsl/ast/plugin/arch.md` 与 `kernel_gen/dsl/ast/plugin/arch.py`。

使用示例:
- pytest -q test/dsl/ast/plugin/test_arch.py

关联文件:
- 功能实现: kernel_gen/dsl/ast/plugin/arch.py
- Spec 文档: spec/dsl/ast/plugin/arch.md
- 测试文件: test/dsl/ast/plugin/test_arch.py
"""

from __future__ import annotations

import pytest

from kernel_gen.core.error import KernelCodeError
from kernel_gen.dsl.ast import ArchGetThreadNumAST, ReturnAST, parse_function
from kernel_gen.operation.arch import get_block_id, get_thread_num
from kernel_gen.symbol_variable.memory import Memory
from kernel_gen.symbol_variable.type import NumericType


def test_arch_query_helper_uses_specific_ast_node() -> None:
    """arch 查询 helper 解析为专用 AST，不再依赖 query 字符串字段。"""

    def arch_query_kernel():
        return get_thread_num()

    func_ast = parse_function(arch_query_kernel)

    return_nodes = [node for node in func_ast.body.statements if isinstance(node, ReturnAST)]
    assert len(return_nodes) == 1
    assert any(isinstance(value, ArchGetThreadNumAST) for value in return_nodes[0].values)


def test_arch_query_rejects_invalid_helper_arity() -> None:
    """arch 查询 helper 非法参数形态报稳定错误。"""

    memory = Memory([1], NumericType.Float32)

    def kernel(x):
        return get_block_id(1)

    with pytest.raises(KernelCodeError, match="Unsupported get_block_id arity"):
        parse_function(kernel, memory)
