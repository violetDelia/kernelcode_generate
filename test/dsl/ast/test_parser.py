"""DSL AST parser tests.

创建者: OpenAI
最后一次更改: 金铲铲大作战

功能说明:
- 覆盖 `parse_function(...)` 的基础解析与诊断路径。
- 覆盖 `parse_function_with_env(...)` 的显式环境入口。

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

import importlib
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from kernel_gen.dsl.ast import ConstAST, ForAST, FunctionAST, NnUnaryAST, ScalarArgAST, TensorAST, parse_function
from kernel_gen.dsl.ast.parser import AstParseError, parse_function_with_env
from kernel_gen.symbol_variable.memory import Memory
from kernel_gen.symbol_variable.symbol_dim import SymbolDim
from kernel_gen.symbol_variable.type import NumericType

NEG_ROWS = -4
ROWS = 6
COLS = 2
DIV_ROWS = 8

facade = importlib.import_module("kernel_gen.dsl.ast")


def test_parse_function_basic_assignment() -> None:
    """解析基础赋值函数并生成 FunctionAST。"""

    def copy_kernel(x: "Tensor[f32, 1]"):
        y = x
        return y

    func_ast = parse_function(copy_kernel)

    assert isinstance(func_ast, FunctionAST)
    assert func_ast.name == "copy_kernel"
    assert func_ast.has_explicit_return is True


def test_parse_function_for_loop() -> None:
    """解析 for range(...) 语法并生成 ForAST。"""

    def loop_kernel(x: "Tensor[f32, 1]"):
        for i in range(0, 4, 1):
            x = x
        return x

    func_ast = parse_function(loop_kernel)
    for_nodes = [node for node in func_ast.body.statements if isinstance(node, ForAST)]

    assert for_nodes, "expected ForAST in function body"
    step_node = for_nodes[0].step
    assert isinstance(step_node, ConstAST)
    assert step_node.value == 1


def test_parse_function_helper_call() -> None:
    """解析 helper 调用入口并生成相应 AST。"""

    def helper_kernel(x: "Tensor[f32, 1]"):
        from kernel_gen.operation.nn import relu

        return relu(x)

    func_ast = parse_function(helper_kernel)

    assert any(isinstance(node, NnUnaryAST) for node in func_ast.body.statements)


def test_parse_function_with_env_infers_runtime_annotation() -> None:
    """显式环境入口允许通过 runtime_table 推断缺失注解。"""

    memory = Memory([SymbolDim("M")], NumericType.Float32)

    def env_kernel(x):
        return x

    func_ast = parse_function_with_env(
        env_kernel,
        globals_table=dict(getattr(env_kernel, "__globals__", {})),
        builtins_table=(__builtins__ if isinstance(__builtins__, dict) else __builtins__.__dict__),
        runtime_table={"x": memory},
        config=None,
    )

    assert isinstance(func_ast.inputs[0], TensorAST)
    assert func_ast.inputs[0].memory == memory


def test_parse_function_reports_diagnostics() -> None:
    """缺失注解时返回带位置信息的 AstParseError。"""

    def kernel(x):
        return x

    with pytest.raises(AstParseError) as exc_info:
        parse_function(kernel)

    assert exc_info.value.diagnostics
    assert exc_info.value.diagnostics[0].message == "Missing annotation"


def test_parse_function_rejects_invalid_helper_arity() -> None:
    """解析 helper 非法参数形态并报稳定错误。"""

    def kernel(x: "Tensor[f32, 1]"):
        from kernel_gen.operation.arch import get_block_id

        return get_block_id(1)

    with pytest.raises(AstParseError, match="Unsupported get_block_id arity"):
        parse_function(kernel)


def test_parse_function_step_zero_rejected() -> None:
    """for range(..., step=0) 在解析阶段直接报错。"""

    def invalid_step_kernel(x: "Tensor[f32, 1]"):
        for i in range(0, 4, 0):
            x = x
        return x

    with pytest.raises(AstParseError, match="for range step must not be zero"):
        parse_function(invalid_step_kernel)


def test_ast_facade_does_not_export_parser_private_helpers() -> None:
    """facade 只暴露公开 AST API，不穿透 parser 私有 helper。"""

    assert hasattr(facade, "parse_function")
    assert not hasattr(facade, "_ParseFailure")
    assert not hasattr(facade, "_parse_function_impl")


def test_parse_function_supports_formatted_tensor_annotation_arithmetic_variants() -> None:
    """格式化 Tensor 注解支持 `- + - * / //` 的当前公开组合。"""

    def kernel(
        x: f"Tensor[f32, {-NEG_ROWS}, {ROWS + COLS}, {ROWS - COLS}, {ROWS * COLS}, {DIV_ROWS / 2}, {DIV_ROWS // 2}]"
    ):
        return x

    func_ast = parse_function(kernel)

    assert isinstance(func_ast.inputs[0], TensorAST)
    assert func_ast.inputs[0].memory.shape.get_values() == [4, 8, 4, 12, 4, 4]


@pytest.mark.parametrize(
    ("builder", "expected_message"),
    [
        pytest.param(
            lambda: (
                (lambda: None),
                f"Tensor[f32, {ROWS!r}]",
            ),
            "Unsupported annotation",
            id="repr-conversion",
        ),
        pytest.param(
            lambda: (
                (lambda: None),
                f"Tensor[f32, {ROWS:02d}]",
            ),
            "Unsupported annotation",
            id="format-spec",
        ),
        pytest.param(
            lambda: (
                (lambda: None),
                f"Tensor[f32, {DIV_ROWS / 3}]",
            ),
            "Unsupported annotation",
            id="non-exact-division",
        ),
    ],
)
def test_parse_function_rejects_unsupported_formatted_tensor_annotations(
    builder: object,
    expected_message: str,
) -> None:
    """格式化 Tensor 注解的 conversion / format-spec / 非整除当前必须失败。"""

    _, annotation = builder()

    def kernel(x: annotation):
        return x

    with pytest.raises(AstParseError) as exc_info:
        parse_function(kernel)

    assert exc_info.value.diagnostics
    assert exc_info.value.diagnostics[0].message == expected_message


def test_parse_function_rejects_direct_tensor_annotation_expression_element() -> None:
    """直接 `Tensor[...]` 注解不接受表达式元素。"""

    def kernel(x: Tensor[f32, ROWS + 1]):
        return x

    with pytest.raises(AstParseError) as exc_info:
        parse_function(kernel)

    assert exc_info.value.diagnostics
    assert exc_info.value.diagnostics[0].message == "Unsupported tensor annotation element"


def test_parse_function_supports_symboldim_union_annotations() -> None:
    """PEP 604 `int | SymbolDim` 继续收口为 symbolic int 标量。"""

    def kernel(x: int | SymbolDim) -> int | SymbolDim:
        return x

    func_ast = parse_function(kernel)

    assert isinstance(func_ast.inputs[0], ScalarArgAST)
    assert func_ast.inputs[0].value_type is int
    assert func_ast.inputs[0].is_symbolic is True
    assert isinstance(func_ast.outputs[0], ScalarArgAST)
    assert func_ast.outputs[0].value_type is int
    assert func_ast.outputs[0].is_symbolic is True


def test_parse_function_rejects_unsupported_union_annotation() -> None:
    """除 `int | SymbolDim` 外的 PEP 604 联合注解当前不属于公开合同。"""

    def kernel(x: int | float):
        return x

    with pytest.raises(AstParseError) as exc_info:
        parse_function(kernel)

    assert exc_info.value.diagnostics
    assert exc_info.value.diagnostics[0].message == "Unsupported annotation"
