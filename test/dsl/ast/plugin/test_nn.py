"""DSL AST NN plugin tests.


功能说明:
- 覆盖 `kernel_gen.dsl.ast.plugin.nn` 注册后的 NN helper 解析行为。
- 测试结构对应 `spec/dsl/ast/plugin/nn.md` 与 `kernel_gen/dsl/ast/plugin/nn.py`。

使用示例:
- pytest -q test/dsl/ast/plugin/test_nn.py

关联文件:
- 功能实现: kernel_gen/dsl/ast/plugin/nn.py
- Spec 文档: spec/dsl/ast/plugin/nn.md
- 测试文件: test/dsl/ast/plugin/test_nn.py
"""

from __future__ import annotations

from kernel_gen.dsl.ast import NnReluAST, ReturnAST, parse_function
from kernel_gen.operation.nn import relu
from kernel_gen.symbol_variable.memory import Memory
from kernel_gen.symbol_variable.type import NumericType


def test_nn_helper_call_uses_registered_specific_ast_node() -> None:
    """解析 NN helper 调用入口并生成相应 AST。"""

    memory = Memory([1], NumericType.Float32)

    def helper_kernel(x):
        return relu(x)

    func_ast = parse_function(helper_kernel, memory)

    return_nodes = [node for node in func_ast.body.statements if isinstance(node, ReturnAST)]
    assert len(return_nodes) == 1
    assert any(isinstance(value, NnReluAST) for value in return_nodes[0].values)
