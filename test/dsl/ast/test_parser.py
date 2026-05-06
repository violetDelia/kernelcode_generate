"""DSL AST parser tests.


功能说明:
- 覆盖 `parse(...)` / `parse_function(...)` 的基础解析与诊断路径。
- 测试结构对应 `spec/dsl/ast/parser.md` 与 `kernel_gen/dsl/ast/parser.py`。

当前覆盖率信息:
- 当前覆盖率: 未统计（本任务验证未启用 coverage 统计）。
- 达标判定: 待后续补充统计结果。

覆盖率命令:
- `pytest -q --cov=kernel_gen.dsl.ast.parser --cov-branch --cov-report=term-missing test/dsl/ast/test_parser.py`

使用示例:
- `pytest -q test/dsl/ast/test_parser.py`

关联文件:
- 功能实现: `kernel_gen/dsl/ast/parser.py`
- Spec 文档: `spec/dsl/ast/parser.md`
- 测试文件: `test/dsl/ast/test_parser.py`
"""

from __future__ import annotations

from collections.abc import Callable

import pytest

from kernel_gen.core.error import KernelCodeError
from kernel_gen.dsl.ast import (
    ConstValueAST,
    ForAST,
    FunctionAST,
    IfAST,
    MemoryAST,
    SymbolDimAST,
    SymbolLtAST,
    parse,
    parse_function,
)
from kernel_gen.operation.dma import store
from kernel_gen.symbol_variable.memory import Memory
from kernel_gen.symbol_variable.symbol_dim import SymbolDim
from kernel_gen.symbol_variable.type import NumericType

NEG_ROWS = -4
ROWS = 6
COLS = 2
DIV_ROWS = 8


def test_parse_function_basic_assignment() -> None:
    """解析基础赋值函数并生成 FunctionAST。"""

    memory = Memory([1], NumericType.Float32)

    def copy_kernel(x):
        y = x
        return y

    func_ast = parse_function(copy_kernel, memory)

    assert isinstance(func_ast, FunctionAST)
    assert func_ast.name == "copy_kernel"
    assert func_ast.has_explicit_return.raw_value is True


def test_parse_rejects_non_callable_public_input() -> None:
    """parse 公开入口拒绝非 callable 输入并返回稳定错误。"""

    with pytest.raises(KernelCodeError, match="parse expects a callable"):
        parse(1)


def test_parse_function_for_loop() -> None:
    """解析 for range(...) 语法并生成 ForAST。"""

    memory = Memory([1], NumericType.Float32)

    def loop_kernel(x):
        for i in range(0, 4, 1):
            x = x
        return x

    func_ast = parse_function(loop_kernel, memory)
    for_nodes = [node for node in func_ast.body.statements if isinstance(node, ForAST)]

    assert for_nodes, "expected ForAST in function body"
    step_node = for_nodes[0].step
    assert isinstance(step_node, ConstValueAST)
    assert step_node.raw_value == 1


def test_parse_function_if_else() -> None:
    """解析 if/else 语法并生成 IfAST。"""

    target = Memory([4], NumericType.Float32)
    source = Memory([2], NumericType.Float32)

    def if_kernel(target, source, lhs, rhs):
        if lhs < rhs:
            store(target, source, [0], [2], [1])
        else:
            store(target, source, [1], [2], [1])

    func_ast = parse_function(if_kernel, target, source, 0, 1)
    if_nodes = [node for node in func_ast.body.statements if isinstance(node, IfAST)]

    assert if_nodes, "expected IfAST in function body"
    assert isinstance(if_nodes[0].condition, SymbolLtAST)
    assert len(if_nodes[0].true_body.statements) == 1
    assert if_nodes[0].false_body is not None
    assert len(if_nodes[0].false_body.statements) == 1


def test_parse_infers_runtime_annotation() -> None:
    """公开 parse 入口允许通过 runtime args 推断缺失注解。"""

    memory = Memory([SymbolDim("M")], NumericType.Float32)

    def env_kernel(x):
        return x

    func_ast = parse(env_kernel, memory).functions[0]

    assert isinstance(func_ast.inputs[0], MemoryAST)
    assert func_ast.inputs[0].memory == memory


def test_parse_function_reports_diagnostics() -> None:
    """缺失 runtime arg 时返回稳定 KernelCodeError 消息。"""

    def kernel(x):
        return x

    with pytest.raises(KernelCodeError) as exc_info:
        parse_function(kernel)

    assert exc_info.value.message() == "Missing runtime argument"


def test_parse_function_step_zero_rejected() -> None:
    """for range(..., step=0) 在解析阶段直接报错。"""

    memory = Memory([1], NumericType.Float32)

    def invalid_step_kernel(x):
        for i in range(0, 4, 0):
            x = x
        return x

    with pytest.raises(KernelCodeError, match="for range step must not be zero"):
        parse_function(invalid_step_kernel, memory)


def test_ast_parse_function_uses_runtime_memory_not_annotation() -> None:
    """annotation 不参与 DSL 类型解析，runtime Memory 是唯一张量来源。"""

    memory = Memory([SymbolDim("N"), 4], NumericType.Float32)

    def kernel(x: "Tensor[f32, 1, 1]"):
        return x

    func_ast = parse_function(kernel, memory)

    assert isinstance(func_ast, FunctionAST)
    assert isinstance(func_ast.inputs[0], MemoryAST)
    assert func_ast.inputs[0].memory == memory


def test_ast_parse_requires_runtime_args_for_parameters() -> None:
    """缺少 runtime arg 时稳定失败，不回退到 annotation 解析。"""

    def kernel(x: "Tensor[f32, 4]"):
        return x

    with pytest.raises(KernelCodeError, match="Missing runtime argument"):
        parse_function(kernel)


def test_ast_parse_module_entry_returns_module_ast() -> None:
    """包根 parse 入口返回包含 FunctionAST 的 ModuleAST。"""

    memory = Memory([4], NumericType.Float32)

    def kernel(x):
        return x

    module_ast = parse(kernel, memory)

    assert len(module_ast.functions) == 1
    assert isinstance(module_ast.functions[0], FunctionAST)


def test_parse_function_ignores_formatted_tensor_annotation_arithmetic_variants() -> None:
    """annotation 不参与输入类型解析，runtime Memory 是唯一张量来源。"""

    memory = Memory([4, 8, 4, 12, 4, 4], NumericType.Float32)

    def kernel(
        x: f"Tensor[f32, {-NEG_ROWS}, {ROWS + COLS}, {ROWS - COLS}, {ROWS * COLS}, {DIV_ROWS / 2}, {DIV_ROWS // 2}]"
    ):
        return x

    func_ast = parse_function(kernel, memory)

    assert isinstance(func_ast.inputs[0], MemoryAST)
    assert func_ast.inputs[0].memory == memory


@pytest.mark.parametrize(
    ("builder", "case_label"),
    [
        pytest.param(
            lambda: (
                (lambda: None),
                f"Tensor[f32, {ROWS!r}]",
            ),
            "repr-conversion",
            id="repr-conversion",
        ),
        pytest.param(
            lambda: (
                (lambda: None),
                f"Tensor[f32, {ROWS:02d}]",
            ),
            "format-spec",
            id="format-spec",
        ),
        pytest.param(
            lambda: (
                (lambda: None),
                f"Tensor[f32, {DIV_ROWS / 3}]",
            ),
            "non-exact-division",
            id="non-exact-division",
        ),
    ],
)
def test_parse_function_ignores_unsupported_formatted_tensor_annotations(
    builder: Callable[[], tuple[Callable[[], None], str]],
    case_label: str,
) -> None:
    """格式化 Tensor annotation 不参与解析，runtime Memory 决定 AST 输入。"""

    del case_label
    _, annotation = builder()
    memory = Memory([ROWS], NumericType.Float32)

    def kernel(x: annotation):
        return x

    func_ast = parse_function(kernel, memory)

    assert isinstance(func_ast.inputs[0], MemoryAST)
    assert func_ast.inputs[0].memory == memory


def test_parse_function_ignores_direct_tensor_annotation_expression_element() -> None:
    """直接 `Tensor[...]` annotation 不参与 DSL 类型解析。"""

    memory = Memory([ROWS + 1], NumericType.Float32)

    def kernel(x: Tensor[f32, ROWS + 1]):
        return x

    func_ast = parse_function(kernel, memory)

    assert isinstance(func_ast.inputs[0], MemoryAST)
    assert func_ast.inputs[0].memory == memory


def test_parse_function_uses_runtime_symboldim_over_union_annotation() -> None:
    """PEP 604 annotation 不参与解析，runtime SymbolDim 决定 symbolic scalar。"""

    symbol = SymbolDim("N")

    def kernel(x: int | SymbolDim) -> int | SymbolDim:
        return x

    func_ast = parse_function(kernel, symbol)

    assert isinstance(func_ast.inputs[0], SymbolDimAST)


def test_parse_function_ignores_unsupported_union_annotation() -> None:
    """不支持的 annotation 不再触发诊断，runtime arg 决定输入。"""

    def kernel(x: int | float):
        return x

    func_ast = parse_function(kernel, 1)

    assert isinstance(func_ast.inputs[0], SymbolDimAST)
