"""DSL AST kernel plugin tests.


功能说明:
- 覆盖 `kernel_gen.dsl.ast.plugin.kernel` 注册后的 kernel helper 解析行为。
- 测试只通过公开 `parse_function(...)` 与 `lookup_builtin(...)` 入口验证。

使用示例:
- pytest -q test/dsl/ast/plugin/test_kernel.py

关联文件:
- 功能实现: kernel_gen/dsl/ast/plugin/kernel.py
- Spec 文档: spec/dsl/ast/plugin/kernel.md
- 测试文件: test/dsl/ast/plugin/test_kernel.py
"""

from __future__ import annotations

import pytest

from kernel_gen.core.error import KernelCodeError
from kernel_gen.dsl.ast import FunctionAST, parse_function
from kernel_gen.dsl.ast.nodes import (
    KernelAddAST,
    KernelBinaryElewiseAST,
    KernelExpAST,
    KernelImg2Col1dAST,
    KernelImg2Col2dAST,
    KernelMatmulAST,
    KernelReduceAST,
)
from kernel_gen.dsl.ast.plugin import lookup_builtin
from kernel_gen.operation import kernel
from kernel_gen.symbol_variable.memory import Memory
from kernel_gen.symbol_variable.symbol_dim import SymbolDim
from kernel_gen.symbol_variable.type import NumericType


def _kernel_add_stmt(out: Memory, lhs: Memory, rhs: Memory) -> None:
    kernel.add(out, lhs, rhs)


def _kernel_binary_stmt(out: Memory, lhs: Memory, rhs: Memory) -> None:
    kernel.binary_elewise(out, lhs, rhs, kind=kernel.KernelBinaryElewiseKind.ADD)


def _kernel_matmul_return_stmt(out: Memory, lhs: Memory, rhs: Memory) -> None:
    return kernel.matmul(out, lhs, rhs)


def _kernel_exp_stmt(out: Memory, input_value: Memory) -> None:
    kernel.exp(out, input_value)


def _kernel_reduce_stmt(out: Memory, input_value: Memory) -> None:
    kernel.reduce(out, input_value, kind=kernel.KernelReduceKind.SUM, axis=1, keepdim=True)


def _kernel_img2col2d_stmt(out: Memory, input_value: Memory, kh: SymbolDim, kw: SymbolDim) -> None:
    kernel.img2col2d(out, input_value, kh=kh, kw=kw, ph=1, pw=1, pl=1, pr=1)


def _bad_kernel_img2col1d_duplicate_arg(out: Memory, input_value: Memory, k: SymbolDim) -> None:
    kernel.img2col1d(out, input_value, k, k=k)


def _bad_kernel_img2col2d_duplicate_arg(out: Memory, input_value: Memory, kh: SymbolDim, kw: SymbolDim) -> None:
    kernel.img2col2d(out, input_value, kh, kw, kh=kh)


def _bad_kernel_add_kwargs(out: Memory, lhs: Memory, rhs: Memory) -> None:
    kernel.add(out, lhs, rhs, kind=kernel.KernelBinaryElewiseKind.ADD)


def _bad_kernel_binary_kind_string(out: Memory, lhs: Memory, rhs: Memory) -> None:
    kernel.binary_elewise(out, lhs, rhs, kind="add")


def _bad_kernel_reduce_kind_string(out: Memory, input_value: Memory) -> None:
    kernel.reduce(out, input_value, kind="sum", axis=1)


def _matmul_memories() -> tuple[Memory, Memory, Memory]:
    """构造公开 matmul Memory 入参。"""

    return (
        Memory([2, 4], NumericType.Float32),
        Memory([2, 3], NumericType.Float32),
        Memory([3, 4], NumericType.Float32),
    )


# TC-AST-PLUGIN-KERNEL-001
# 功能说明: 验证 kernel builtin 注册表包含 out-first helper。
# 测试目的: 锁定 kernel.add 与 kernel.binary_elewise 分别注册到独立 AST 节点。
# 使用示例: pytest -q test/dsl/ast/plugin/test_kernel.py -k lookup
# 对应功能实现文件路径: kernel_gen/dsl/ast/plugin/kernel.py
# 对应 spec 文件路径: spec/dsl/ast/plugin/kernel.md
# 对应测试文件路径: test/dsl/ast/plugin/test_kernel.py
def test_kernel_plugin_registers_public_helpers() -> None:
    assert lookup_builtin(kernel.add).ast_node is KernelAddAST
    assert lookup_builtin(kernel.binary_elewise).ast_node is KernelBinaryElewiseAST
    assert lookup_builtin(kernel.exp).ast_node is KernelExpAST
    assert lookup_builtin(kernel.reduce).ast_node is KernelReduceAST
    assert lookup_builtin(kernel.matmul).ast_node is KernelMatmulAST
    assert lookup_builtin(kernel.img2col1d).ast_node is KernelImg2Col1dAST
    assert lookup_builtin(kernel.img2col2d).ast_node is KernelImg2Col2dAST


# TC-AST-PLUGIN-KERNEL-002
# 功能说明: 验证 parse_function 识别 kernel statement helper。
# 测试目的: kernel.add、binary_elewise、return kernel.matmul(...) 都应生成 statement AST。
# 使用示例: pytest -q test/dsl/ast/plugin/test_kernel.py -k parse
# 对应功能实现文件路径: kernel_gen/dsl/ast/plugin/kernel.py
# 对应 spec 文件路径: spec/dsl/ast/parser.md
# 对应测试文件路径: test/dsl/ast/plugin/test_kernel.py
def test_kernel_plugin_parse_function_builds_statement_nodes() -> None:
    out, lhs, rhs = _matmul_memories()

    add_ast = parse_function(_kernel_add_stmt, out, out, out)
    binary_ast = parse_function(_kernel_binary_stmt, out, out, out)
    exp_ast = parse_function(_kernel_exp_stmt, out, out)
    reduce_ast = parse_function(_kernel_reduce_stmt, Memory([2, 1], NumericType.Float32), Memory([2, 4], NumericType.Float32))
    matmul_ast = parse_function(_kernel_matmul_return_stmt, out, lhs, rhs)

    assert isinstance(add_ast, FunctionAST)
    assert isinstance(add_ast.body.statements[0], KernelAddAST)
    assert isinstance(binary_ast.body.statements[0], KernelBinaryElewiseAST)
    assert isinstance(exp_ast.body.statements[0], KernelExpAST)
    assert isinstance(reduce_ast.body.statements[0], KernelReduceAST)
    assert isinstance(matmul_ast.body.statements[0], KernelMatmulAST)
    assert matmul_ast.returns_none.value is True


# TC-AST-PLUGIN-KERNEL-003
# 功能说明: 验证 img2col2d 支持 keyword 窗口参数。
# 测试目的: 锁定 kh/kw 必填、其余窗口参数可通过 keyword 下沉到 AST。
# 使用示例: pytest -q test/dsl/ast/plugin/test_kernel.py -k img2col2d
# 对应功能实现文件路径: kernel_gen/dsl/ast/plugin/kernel.py
# 对应 spec 文件路径: spec/dsl/ast/plugin/kernel.md
# 对应测试文件路径: test/dsl/ast/plugin/test_kernel.py
def test_kernel_plugin_parses_img2col2d_keyword_parameters() -> None:
    input_value = Memory([1, 3, SymbolDim("H"), SymbolDim("W")], NumericType.Float32)
    out = Memory([1, 3, SymbolDim("KH"), SymbolDim("KW"), SymbolDim("H"), SymbolDim("W")], NumericType.Float32)
    function_ast = parse_function(_kernel_img2col2d_stmt, out, input_value, SymbolDim("KH"), SymbolDim("KW"))

    assert isinstance(function_ast.body.statements[0], KernelImg2Col2dAST)


# TC-AST-PLUGIN-KERNEL-004
# 功能说明: 验证非公开调用形态被拒绝。
# 测试目的: keyword 传给 add、字符串 kind 传给 binary_elewise 都不是公开 API。
# 使用示例: pytest -q test/dsl/ast/plugin/test_kernel.py -k rejects
# 对应功能实现文件路径: kernel_gen/dsl/ast/plugin/kernel.py
# 对应 spec 文件路径: spec/dsl/ast/plugin/kernel.md
# 对应测试文件路径: test/dsl/ast/plugin/test_kernel.py
def test_kernel_plugin_rejects_non_api_call_shapes() -> None:
    out, lhs, rhs = _matmul_memories()

    with pytest.raises(KernelCodeError, match="kwargs"):
        parse_function(_bad_kernel_add_kwargs, out, lhs, rhs)
    with pytest.raises(KernelCodeError, match="KernelBinaryElewiseKind"):
        parse_function(_bad_kernel_binary_kind_string, out, lhs, rhs)
    with pytest.raises(KernelCodeError, match="KernelReduceKind"):
        parse_function(
            _bad_kernel_reduce_kind_string,
            Memory([2], NumericType.Float32),
            Memory([2, 4], NumericType.Float32),
        )


# TC-AST-PLUGIN-KERNEL-005
# 功能说明: 验证 img2col 位置参数与 keyword 重复传入会失败。
# 测试目的: 锁定公开 DSL 调用不接受 Python runtime 会拒绝的重复实参形态。
# 使用示例: pytest -q test/dsl/ast/plugin/test_kernel.py -k duplicate
# 对应功能实现文件路径: kernel_gen/dsl/ast/plugin/kernel.py
# 对应 spec 文件路径: spec/dsl/ast/plugin/kernel.md
# 对应测试文件路径: test/dsl/ast/plugin/test_kernel.py
def test_kernel_plugin_rejects_img2col_duplicate_positional_keyword_parameters() -> None:
    input1d = Memory([1, 3, SymbolDim("W")], NumericType.Float32)
    out1d = Memory([1, 3, SymbolDim("K"), SymbolDim("OW")], NumericType.Float32)
    input2d = Memory([1, 3, SymbolDim("H"), SymbolDim("W")], NumericType.Float32)
    out2d = Memory([1, 3, SymbolDim("KH"), SymbolDim("KW"), SymbolDim("OH"), SymbolDim("OW")], NumericType.Float32)

    with pytest.raises(KernelCodeError, match="position and keyword"):
        parse_function(_bad_kernel_img2col1d_duplicate_arg, out1d, input1d, SymbolDim("K"))
    with pytest.raises(KernelCodeError, match="position and keyword"):
        parse_function(_bad_kernel_img2col2d_duplicate_arg, out2d, input2d, SymbolDim("KH"), SymbolDim("KW"))
