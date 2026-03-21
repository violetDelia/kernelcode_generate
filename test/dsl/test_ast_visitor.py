"""AST visitor tests.

创建者: 小李飞刀
最后一次更改: 小李飞刀

功能说明:
- 覆盖 AST 前端、nn dialect IR 与 MLIR 文本入口的回归测试。

使用示例:
- pytest -q test/dsl/test_ast_visitor.py

关联文件:
- 功能实现: kernel_gen/dsl/ast_visitor.py
- Spec 文档: spec/dsl/ast_visitor.md
- 测试文件: test/dsl/test_ast_visitor.py
"""

from __future__ import annotations

from io import StringIO
import sys
from pathlib import Path

import pytest
from xdsl.dialects import func
from xdsl.dialects.builtin import ModuleOp, i32
from xdsl.ir import Block
from xdsl.printer import Printer

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from kernel_gen.dialect.dma import DmaLoadOp, DmaStoreOp
from kernel_gen.dialect.nn import NnAddOp, NnBroadcastOp, NnEqOp, NnMemoryType
from kernel_gen.dsl.ast import (
    AstParseError,
    BlockAST,
    BinaryExprAST,
    CompareExprAST,
    ConstAST,
    FunctionAST,
    ForAST,
    LoadAST,
    SourceLocation,
    StoreAST,
    TensorAST,
    VarAST,
    ScalarArgAST,
    parse_function,
)
from kernel_gen.dsl.ast_visitor import AstVisitor, AstVisitorError
from kernel_gen.dsl.emit_mlir import EmitContext, _LoweringError, _memory_to_nn_type, emit_mlir as emit_node_mlir
from kernel_gen.dsl.mlir_gen import build_func_op, build_func_op_from_ast
from kernel_gen.symbol_variable.memory import Memory
from kernel_gen.symbol_variable.type import NumericType


def _module_from_func(fn: object) -> ModuleOp:
    return ModuleOp([build_func_op(fn)])


def _module_from_ast(func_ast: FunctionAST) -> ModuleOp:
    return ModuleOp([build_func_op_from_ast(func_ast)])


def _print_module(module: ModuleOp) -> str:
    stream = StringIO()
    printer = Printer(stream=stream)
    printer.print_op(module)
    return stream.getvalue()


# AST-001
# 创建者: 小李飞刀
# 最后一次更改: 金铲铲大作战
# 最近一次运行测试时间: 2026-03-21 21:49:50 +0800
# 最近一次运行成功时间: 2026-03-21 21:49:50 +0800
# 功能说明: 验证 parse_function 生成 FunctionAST 并保留位置信息。
# 使用示例: pytest -q test/dsl/test_ast_visitor.py -k test_visit_function_builds_ast
# 对应功能实现文件路径: kernel_gen/dsl/ast.py
# 对应 spec 文件路径: spec/dsl/ast.md
# 对应测试文件路径: test/dsl/test_ast_visitor.py
def test_visit_function_builds_ast() -> None:
    def add(
        x: "Tensor[f32, 2, 2]",
        y: "Tensor[f32, 2, 2]",
    ) -> "Tensor[f32, 2, 2]":
        z = x + y
        return z

    func_ast = parse_function(add)
    assert func_ast.name == "add"
    assert len(func_ast.inputs) == 2
    assert len(func_ast.outputs) == 1
    assert len(func_ast.body.statements) == 2
    assert isinstance(func_ast.body.statements[0], BinaryExprAST)
    assert func_ast.body.location is not None


# AST-002
# 创建者: 金铲铲大作战
# 最后一次更改: 金铲铲大作战
# 最近一次运行测试时间: 2026-03-21 21:28:00 +0800
# 最近一次运行成功时间: 2026-03-21 21:28:00 +0800
# 功能说明: 验证 parse_function 解析 Tensor/Scalar 参数注解。
# 使用示例: pytest -q test/dsl/test_ast_visitor.py -k test_ast_parse_function_parses_annotations
# 对应功能实现文件路径: kernel_gen/dsl/ast.py
# 对应 spec 文件路径: spec/dsl/ast.md
# 对应测试文件路径: test/dsl/test_ast_visitor.py
def test_ast_parse_function_parses_annotations() -> None:
    def add(
        x: "Tensor[f32, 2, 2]",
        n: int,
    ) -> "Tensor[f32, 2, 2]":
        return x

    func_ast = parse_function(add)
    assert len(func_ast.inputs) == 2
    assert isinstance(func_ast.inputs[0], TensorAST)
    assert isinstance(func_ast.inputs[1], ScalarArgAST)


# AST-003
# 创建者: 金铲铲大作战
# 最后一次更改: 金铲铲大作战
# 最近一次运行测试时间: 2026-03-21 21:49:50 +0800
# 最近一次运行成功时间: 2026-03-21 21:49:50 +0800
# 功能说明: 验证 parse_function 对非法注解抛出带诊断信息的错误。
# 使用示例: pytest -q test/dsl/test_ast_visitor.py -k test_ast_parse_function_missing_annotation_reports_diagnostics
# 对应功能实现文件路径: kernel_gen/dsl/ast.py
# 对应 spec 文件路径: spec/dsl/ast.md
# 对应测试文件路径: test/dsl/test_ast_visitor.py
def test_ast_parse_function_missing_annotation_reports_diagnostics() -> None:
    def bad(x, y: "Tensor[f32, 2, 2]") -> "Tensor[f32, 2, 2]":
        return y

    with pytest.raises(AstParseError) as exc_info:
        parse_function(bad)
    diagnostics = exc_info.value.diagnostics
    assert diagnostics
    assert diagnostics[0].message == "Missing annotation"


# MGEN-004
# 创建者: 小李飞刀
# 最后一次更改: 金铲铲大作战
# 最近一次运行测试时间: 2026-03-21 21:49:50 +0800
# 最近一次运行成功时间: 2026-03-21 21:49:50 +0800
# 功能说明: 验证 build_func_op 生成 func.func 并包含 nn dialect IR。
# 使用示例: pytest -q test/dsl/test_ast_visitor.py -k test_visit_to_nn_ir_builds_module
# 对应功能实现文件路径: kernel_gen/dsl/mlir_gen.py
# 对应 spec 文件路径: spec/dsl/mlir_gen.md
# 对应测试文件路径: test/dsl/test_ast_visitor.py
def test_visit_to_nn_ir_builds_module() -> None:
    def add(
        x: "Tensor[f32, 2, 2]",
        y: "Tensor[f32, 2, 2]",
    ) -> "Tensor[f32, 2, 2]":
        z = x + y
        return z

    module = _module_from_func(add)
    assert isinstance(module, ModuleOp)
    assert any(isinstance(op, func.FuncOp) for op in module.ops)
    assert any(isinstance(op, NnAddOp) for op in module.walk())


# MGEN-005
# 创建者: 小李飞刀
# 最后一次更改: 金铲铲大作战
# 最近一次运行测试时间: 2026-03-21 21:49:50 +0800
# 最近一次运行成功时间: 2026-03-21 21:49:50 +0800
# 功能说明: 验证 func.func 打印输出包含 nn dialect 文本。
# 使用示例: pytest -q test/dsl/test_ast_visitor.py -k test_emit_mlir_output
# 对应功能实现文件路径: kernel_gen/dsl/mlir_gen.py
# 对应 spec 文件路径: spec/dsl/mlir_gen.md
# 对应测试文件路径: test/dsl/test_ast_visitor.py
def test_emit_mlir_output() -> None:
    def add(
        x: "Tensor[f32, 2, 2]",
        y: "Tensor[f32, 2, 2]",
    ) -> "Tensor[f32, 2, 2]":
        z = x + y
        return z

    module = _module_from_func(add)
    text = _print_module(module)
    assert "nn.add" in text
    assert "func.func" in text


# AST-001A
# 创建者: 朽木露琪亚
# 最后一次更改: 金铲铲大作战
# 最近一次运行测试时间: 2026-03-21 21:49:50 +0800
# 最近一次运行成功时间: 2026-03-21 21:49:50 +0800
# 功能说明: 验证 parse_function 提供独立 AST 解析入口。
# 使用示例: pytest -q test/dsl/test_ast_visitor.py -k test_parse_function_entry
# 对应功能实现文件路径: kernel_gen/dsl/ast.py
# 对应 spec 文件路径: spec/dsl/ast.md
# 对应测试文件路径: test/dsl/test_ast_visitor.py
def test_parse_function_entry() -> None:
    def add(
        x: "Tensor[f32, 2, 2]",
        y: "Tensor[f32, 2, 2]",
    ) -> "Tensor[f32, 2, 2]":
        return x + y

    func_ast = parse_function(add)
    assert isinstance(func_ast, FunctionAST)
    assert [arg.name for arg in func_ast.iter_inputs()] == ["x", "y"]


# AST-001B
# 创建者: ChatGPT
# 最后一次更改: 金铲铲大作战
# 最近一次运行测试时间: 2026-03-21 21:49:50 +0800
# 最近一次运行成功时间: 2026-03-21 21:49:50 +0800
# 功能说明: 验证 parse_function 不依赖 ast_visitor.visit_function 的反向导入。
# 使用示例: pytest -q test/dsl/test_ast_visitor.py -k test_parse_function_does_not_depend_on_ast_visitor_entry
# 对应功能实现文件路径: kernel_gen/dsl/ast.py
# 对应 spec 文件路径: spec/dsl/ast.md
# 对应测试文件路径: test/dsl/test_ast_visitor.py
def test_parse_function_does_not_depend_on_ast_visitor_entry(monkeypatch: pytest.MonkeyPatch) -> None:
    def add(
        x: "Tensor[f32, 2, 2]",
        y: "Tensor[f32, 2, 2]",
    ) -> "Tensor[f32, 2, 2]":
        return x + y

    import kernel_gen.dsl.ast_visitor as ast_visitor_module

    def _broken_visit_function(*args: object, **kwargs: object) -> object:
        raise AssertionError("parse_function must not call AstVisitor.visit_function")

    monkeypatch.setattr(ast_visitor_module.AstVisitor, "visit_function", _broken_visit_function)
    func_ast = parse_function(add)
    assert isinstance(func_ast, FunctionAST)
    assert func_ast.name == "add"


# MGEN-001
# 创建者: 朽木露琪亚
# 最后一次更改: 金铲铲大作战
# 最近一次运行测试时间: 2026-03-21 21:49:50 +0800
# 最近一次运行成功时间: 2026-03-21 21:49:50 +0800
# 功能说明: 验证 build_func_op 返回 func.func 并生成正确参数类型。
# 使用示例: pytest -q test/dsl/test_ast_visitor.py -k test_build_func_op_returns_func_op
# 对应功能实现文件路径: kernel_gen/dsl/mlir_gen.py
# 对应 spec 文件路径: spec/dsl/mlir_gen.md
# 对应测试文件路径: test/dsl/test_ast_visitor.py
def test_build_func_op_returns_func_op() -> None:
    def add(
        x: "Tensor[f32, 2, 2]",
        y: "Tensor[f32, 2, 2]",
        n: int,
    ) -> "Tensor[f32, 2, 2]":
        return x + y

    func_op = build_func_op(add)
    assert isinstance(func_op, func.FuncOp)
    inputs = list(func_op.function_type.inputs)
    assert len(inputs) == 3
    assert inputs[2] == i32


# MGEN-002
# 创建者: 朽木露琪亚
# 最后一次更改: 金铲铲大作战
# 最近一次运行测试时间: 2026-03-21 21:49:50 +0800
# 最近一次运行成功时间: 2026-03-21 21:49:50 +0800
# 功能说明: 验证 build_func_op_from_ast 保留 AST 参数顺序。
# 使用示例: pytest -q test/dsl/test_ast_visitor.py -k test_build_func_op_from_ast_preserves_arg_order
# 对应功能实现文件路径: kernel_gen/dsl/mlir_gen.py
# 对应 spec 文件路径: spec/dsl/mlir_gen.md
# 对应测试文件路径: test/dsl/test_ast_visitor.py
def test_build_func_op_from_ast_preserves_arg_order() -> None:
    def add(
        x: "Tensor[f32, 2, 2]",
        y: "Tensor[f32, 2, 2]",
        n: int,
    ) -> "Tensor[f32, 2, 2]":
        return x + y

    func_ast = parse_function(add)
    func_op = build_func_op_from_ast(func_ast)
    assert isinstance(func_op, func.FuncOp)
    inputs = list(func_op.function_type.inputs)
    assert len(inputs) == 3
    assert inputs[2] == i32


# MGEN-003
# 创建者: 金铲铲大作战
# 最后一次更改: 金铲铲大作战
# 最近一次运行测试时间: 2026-03-21 21:49:50 +0800
# 最近一次运行成功时间: 2026-03-21 21:49:50 +0800
# 功能说明: 验证 build_func_op 返回类型与 AST 返回注解一致。
# 使用示例: pytest -q test/dsl/test_ast_visitor.py -k test_build_func_op_return_type_matches_annotation
# 对应功能实现文件路径: kernel_gen/dsl/mlir_gen.py
# 对应 spec 文件路径: spec/dsl/mlir_gen.md
# 对应测试文件路径: test/dsl/test_ast_visitor.py
def test_build_func_op_return_type_matches_annotation() -> None:
    def add(x: "Tensor[f32, 2, 2]") -> "Tensor[f32, 2, 2]":
        return x

    func_ast = parse_function(add)
    func_op = build_func_op(add)
    outputs = list(func_op.function_type.outputs)
    assert outputs
    expected = _memory_to_nn_type(func_ast.outputs[0].memory)
    assert outputs[0] == expected


# EMIT-001
# 创建者: 朽木露琪亚
# 最后一次更改: 金铲铲大作战
# 最近一次运行测试时间: 2026-03-21 21:49:50 +0800
# 最近一次运行成功时间: 2026-03-21 21:49:50 +0800
# 功能说明: 验证二元表达式节点生成对应 op/value 并复用缓存。
# 使用示例: pytest -q test/dsl/test_ast_visitor.py -k test_emit_context_reuses_cached_value
# 对应功能实现文件路径: kernel_gen/dsl/emit_mlir.py
# 对应 spec 文件路径: spec/dsl/emit_mlir.md
# 对应测试文件路径: test/dsl/test_ast_visitor.py
def test_emit_context_reuses_cached_value() -> None:
    memory = Memory([2, 2], NumericType.Float32)
    lhs = TensorAST(name="x", memory=memory, location=None)
    rhs = TensorAST(name="y", memory=memory, location=None)
    expr = BinaryExprAST(op="add", lhs=lhs, rhs=rhs, location=None)
    func_op = build_func_op_from_ast(FunctionAST("tmp", [lhs, rhs], [], BlockAST([expr])))
    arg_types = list(func_op.function_type.inputs)
    block = Block(arg_types=arg_types)
    ctx = EmitContext(builder=block, symbols={"x": block.args[0], "y": block.args[1]}, types={})
    emit_node_mlir(lhs, ctx)
    emit_node_mlir(rhs, ctx)

    first = emit_node_mlir(expr, ctx)
    second = emit_node_mlir(expr, ctx)
    assert first is second
    ops = [op for op in block.ops if isinstance(op, NnAddOp)]
    assert len(ops) == 1


# EMIT-004
# 创建者: ChatGPT
# 最后一次更改: 金铲铲大作战
# 最近一次运行测试时间: 2026-03-21 21:49:50 +0800
# 最近一次运行成功时间: 2026-03-21 21:49:50 +0800
# 功能说明: 验证 emit_mlir 可通过符号表直接解析 TensorAST 输入。
# 使用示例: pytest -q test/dsl/test_ast_visitor.py -k test_emit_mlir_tensor_uses_symbol_table
# 对应功能实现文件路径: kernel_gen/dsl/emit_mlir.py
# 对应 spec 文件路径: spec/dsl/emit_mlir.md
# 对应测试文件路径: test/dsl/test_ast_visitor.py
def test_emit_mlir_tensor_uses_symbol_table() -> None:
    memory = Memory([2, 2], NumericType.Float32)
    lhs = TensorAST(name="x", memory=memory, location=None)
    rhs = TensorAST(name="y", memory=memory, location=None)
    func_op = build_func_op_from_ast(FunctionAST("tmp", [lhs, rhs], [], BlockAST([lhs])))
    block = Block(arg_types=list(func_op.function_type.inputs))
    ctx = EmitContext(builder=block, symbols={"x": block.args[0], "y": block.args[1]}, types={})

    value = emit_node_mlir(lhs, ctx)
    assert value is block.args[0]
    assert emit_node_mlir(lhs, ctx) is block.args[0]


# EMIT-002
# 创建者: 金铲铲大作战
# 最后一次更改: 金铲铲大作战
# 最近一次运行测试时间: 2026-03-21 21:49:50 +0800
# 最近一次运行成功时间: 2026-03-21 21:49:50 +0800
# 功能说明: 验证比较表达式节点生成对应 op/value。
# 使用示例: pytest -q test/dsl/test_ast_visitor.py -k test_emit_mlir_compare_expr_emits_eq
# 对应功能实现文件路径: kernel_gen/dsl/emit_mlir.py
# 对应 spec 文件路径: spec/dsl/emit_mlir.md
# 对应测试文件路径: test/dsl/test_ast_visitor.py
def test_emit_mlir_compare_expr_emits_eq() -> None:
    memory = Memory([2, 2], NumericType.Float32)
    lhs = TensorAST(name="x", memory=memory, location=None)
    rhs = TensorAST(name="y", memory=memory, location=None)
    expr = CompareExprAST(op="eq", lhs=lhs, rhs=rhs, location=None)
    func_op = build_func_op_from_ast(FunctionAST("tmp", [lhs, rhs], [], BlockAST([expr])))
    block = Block(arg_types=list(func_op.function_type.inputs))
    ctx = EmitContext(builder=block, symbols={"x": block.args[0], "y": block.args[1]}, types={})
    emit_node_mlir(lhs, ctx)
    emit_node_mlir(rhs, ctx)

    result = emit_node_mlir(expr, ctx)
    ops = [op for op in block.ops if isinstance(op, NnEqOp)]
    assert len(ops) == 1
    assert result is ops[0].result


# EMIT-003
# 创建者: 金铲铲大作战
# 最后一次更改: 金铲铲大作战
# 最近一次运行测试时间: 2026-03-21 21:49:50 +0800
# 最近一次运行成功时间: 2026-03-21 21:49:50 +0800
# 功能说明: 验证不支持节点抛出错误并携带位置信息。
# 使用示例: pytest -q test/dsl/test_ast_visitor.py -k test_emit_mlir_unsupported_node_reports_location
# 对应功能实现文件路径: kernel_gen/dsl/emit_mlir.py
# 对应 spec 文件路径: spec/dsl/emit_mlir.md
# 对应测试文件路径: test/dsl/test_ast_visitor.py
def test_emit_mlir_unsupported_node_reports_location() -> None:
    block = Block(arg_types=[])
    ctx = EmitContext(builder=block, symbols={}, types={})
    node = BlockAST(statements=[], location=SourceLocation(3, 2))

    with pytest.raises(_LoweringError) as exc_info:
        emit_node_mlir(node, ctx)
    assert exc_info.value.location == node.location


# AV-001
# 创建者: 朽木露琪亚
# 最后一次更改: 金铲铲大作战
# 最近一次运行测试时间: 2026-03-21 21:49:50 +0800
# 最近一次运行成功时间: 2026-03-21 21:49:50 +0800
# 功能说明: 验证 AstVisitor 顺序访问 block 并生成多语句 SSA。
# 使用示例: pytest -q test/dsl/test_ast_visitor.py -k test_ast_visitor_visit_block_preserves_order
# 对应功能实现文件路径: kernel_gen/dsl/ast_visitor.py
# 对应 spec 文件路径: spec/dsl/ast_visitor.md
# 对应测试文件路径: test/dsl/test_ast_visitor.py
def test_ast_visitor_visit_block_preserves_order() -> None:
    def add(
        x: "Tensor[f32, 2, 2]",
        y: "Tensor[f32, 2, 2]",
    ) -> "Tensor[f32, 2, 2]":
        z = x + y
        w = z + z
        return w

    func_ast = parse_function(add)
    func_op = build_func_op_from_ast(func_ast)
    visitor = AstVisitor()
    block = Block(arg_types=list(func_op.function_type.inputs))
    ctx = EmitContext(builder=block, symbols={}, types={})
    for idx, item in enumerate(func_ast.inputs):
        ctx.symbols[item.name] = block.args[idx]
        emit_node_mlir(item, ctx)

    result = visitor.visit_block(func_ast.body, ctx)
    assert result is not None
    ops = [op for op in block.ops if isinstance(op, NnAddOp)]
    assert len(ops) == 2
    assert ops[1].lhs is ops[0].result
    assert ops[1].rhs is ops[0].result


# AV-002
# 创建者: 金铲铲大作战
# 最后一次更改: 金铲铲大作战
# 最近一次运行测试时间: 2026-03-21 21:49:50 +0800
# 最近一次运行成功时间: 2026-03-21 21:49:50 +0800
# 功能说明: 验证同一表达式节点复用同一 value。
# 使用示例: pytest -q test/dsl/test_ast_visitor.py -k test_ast_visitor_reuses_expression_value
# 对应功能实现文件路径: kernel_gen/dsl/ast_visitor.py
# 对应 spec 文件路径: spec/dsl/ast_visitor.md
# 对应测试文件路径: test/dsl/test_ast_visitor.py
def test_ast_visitor_reuses_expression_value() -> None:
    memory = Memory([2, 2], NumericType.Float32)
    lhs = TensorAST(name="x", memory=memory, location=None)
    rhs = TensorAST(name="y", memory=memory, location=None)
    expr = BinaryExprAST(op="add", lhs=lhs, rhs=rhs, location=None)
    func_ast = FunctionAST(name="reuse", inputs=[lhs, rhs], outputs=[], body=BlockAST([expr, expr]))

    func_op = build_func_op_from_ast(func_ast)
    ops = [op for op in func_op.body.block.ops if isinstance(op, NnAddOp)]
    assert len(ops) == 1


# AST-004
# 创建者: 小李飞刀
# 最后一次更改: 小李飞刀
# 最近一次运行测试时间: 2026-03-18 10:56:41 +0800
# 最近一次运行成功时间: 2026-03-18 10:56:41 +0800
# 功能说明: 验证 parse_function 可解析标准 Tensor 注解。
# 使用示例: pytest -q test/dsl/test_ast_visitor.py -k test_globals_and_builtins_annotation_entry
# 对应功能实现文件路径: kernel_gen/dsl/ast.py
# 对应 spec 文件路径: spec/dsl/ast.md
# 对应测试文件路径: test/dsl/test_ast_visitor.py
def test_globals_and_builtins_annotation_entry() -> None:
    def add(x: "Tensor[f32, 2, 2]", y: "Tensor[f32, 2, 2]") -> "Tensor[f32, 2, 2]":
        return x + y

    func_ast = parse_function(add)
    assert func_ast.name == "add"


# MGEN-006
# 创建者: 小李飞刀
# 最后一次更改: 小李飞刀
# 最近一次运行测试时间: 2026-03-18 10:56:41 +0800
# 最近一次运行成功时间: 2026-03-18 10:56:41 +0800
# 功能说明: 验证 ScalarArgAST 会 lowering 为 func.func 标量参数。
# 使用示例: pytest -q test/dsl/test_ast_visitor.py -k test_scalar_arg_lowering_in_signature
# 对应功能实现文件路径: kernel_gen/dsl/mlir_gen.py
# 对应 spec 文件路径: spec/dsl/mlir_gen.md
# 对应测试文件路径: test/dsl/test_ast_visitor.py
def test_scalar_arg_lowering_in_signature() -> None:
    def add(
        x: "Tensor[f32, 2, 2]",
        y: "Tensor[f32, 2, 2]",
        n: int,
    ) -> "Tensor[f32, 2, 2]":
        return x + y

    func_op = build_func_op(add)
    inputs = list(func_op.function_type.inputs)
    assert len(inputs) == 3
    assert isinstance(inputs[0], NnMemoryType)
    assert isinstance(inputs[1], NnMemoryType)
    assert inputs[2] == i32


# AST-005
# 创建者: 小李飞刀
# 最后一次更改: 小李飞刀
# 最近一次运行测试时间: 2026-03-18 10:56:41 +0800
# 最近一次运行成功时间: 2026-03-18 10:56:41 +0800
# 功能说明: 验证未知名称在 AST 阶段产生诊断信息。
# 使用示例: pytest -q test/dsl/test_ast_visitor.py -k test_unknown_name_reports_diagnostics
# 对应功能实现文件路径: kernel_gen/dsl/ast.py
# 对应 spec 文件路径: spec/dsl/ast.md
# 对应测试文件路径: test/dsl/test_ast_visitor.py
def test_unknown_name_reports_diagnostics() -> None:
    def bad(x: "Tensor[f32, 2, 2]") -> "Tensor[f32, 2, 2]":
        return y

    with pytest.raises(AstParseError) as exc_info:
        parse_function(bad)
    diagnostics = exc_info.value.diagnostics
    assert diagnostics
    assert diagnostics[0].location is not None


# AV-003
# 创建者: 小李飞刀
# 最后一次更改: 金铲铲大作战
# 最近一次运行测试时间: 2026-03-21 21:49:50 +0800
# 最近一次运行成功时间: 2026-03-21 21:49:50 +0800
# 功能说明: 验证不支持语句/表达式时抛 AstVisitorError 并携带位置信息。
# 使用示例: pytest -q test/dsl/test_ast_visitor.py -k test_lowering_failure_reports_diagnostics
# 对应功能实现文件路径: kernel_gen/dsl/ast_visitor.py
# 对应 spec 文件路径: spec/dsl/ast_visitor.md
# 对应测试文件路径: test/dsl/test_ast_visitor.py
def test_lowering_failure_reports_diagnostics() -> None:
    def bad(x: "Tensor[f32, 2, 2]") -> "Tensor[f32, 2, 2]":
        return x + 1

    with pytest.raises(AstVisitorError) as exc_info:
        build_func_op(bad)
    assert exc_info.value.location is not None


# AST-006
# 创建者: 小李飞刀
# 最后一次更改: 小李飞刀
# 最近一次运行测试时间: 2026-03-18 10:56:41 +0800
# 最近一次运行成功时间: 2026-03-18 10:56:41 +0800
# 功能说明: 验证非法返回注解会保留可定位诊断并向上抛出。
# 使用示例: pytest -q test/dsl/test_ast_visitor.py -k test_invalid_return_annotation_reports_diagnostics
# 对应功能实现文件路径: kernel_gen/dsl/ast.py
# 对应 spec 文件路径: spec/dsl/ast.md
# 对应测试文件路径: test/dsl/test_ast_visitor.py
def test_invalid_return_annotation_reports_diagnostics() -> None:
    def bad_return(x: "Tensor[f32, 2, 2]") -> "NotSupported":
        return x

    with pytest.raises(AstParseError) as exc_info:
        parse_function(bad_return)
    diagnostics = exc_info.value.diagnostics
    assert diagnostics
    assert diagnostics[0].location is not None


# MGEN-007
# 创建者: 小李飞刀
# 最后一次更改: 小李飞刀
# 最近一次运行测试时间: 2026-03-18 10:56:41 +0800
# 最近一次运行成功时间: 2026-03-18 10:56:41 +0800
# 功能说明: 验证非法 Tensor 返回注解会抛出带诊断的错误。
# 使用示例: pytest -q test/dsl/test_ast_visitor.py -k test_invalid_tensor_return_annotation_reports_diagnostics
# 对应功能实现文件路径: kernel_gen/dsl/mlir_gen.py
# 对应 spec 文件路径: spec/dsl/mlir_gen.md
# 对应测试文件路径: test/dsl/test_ast_visitor.py
def test_invalid_tensor_return_annotation_reports_diagnostics() -> None:
    def bad_return(x: "Tensor[f32, 2, 2]") -> "Tensor[f16, 2, 2]":
        return x

    with pytest.raises(AstVisitorError) as exc_info:
        build_func_op(bad_return)
    assert exc_info.value.location is not None


# MGEN-008
# 创建者: 小李飞刀
# 最后一次更改: 小李飞刀
# 最近一次运行测试时间: 2026-03-18 10:56:41 +0800
# 最近一次运行成功时间: 2026-03-18 10:56:41 +0800
# 功能说明: 验证常量 lowering 失败会抛出带诊断的错误。
# 使用示例: pytest -q test/dsl/test_ast_visitor.py -k test_constant_lowering_reports_diagnostics
# 对应功能实现文件路径: kernel_gen/dsl/mlir_gen.py
# 对应 spec 文件路径: spec/dsl/mlir_gen.md
# 对应测试文件路径: test/dsl/test_ast_visitor.py
def test_constant_lowering_reports_diagnostics() -> None:
    def bad(x: "Tensor[f32, 2, 2]") -> "Tensor[f32, 2, 2]":
        return 1

    with pytest.raises(AstVisitorError) as exc_info:
        build_func_op(bad)
    assert exc_info.value.location is not None


# AST-007
# 创建者: 小李飞刀
# 最后一次更改: 小李飞刀
# 最近一次运行测试时间: 2026-03-18 10:56:41 +0800
# 最近一次运行成功时间: 2026-03-18 10:56:41 +0800
# 功能说明: 验证缺失 return 会抛出带诊断的错误。
# 使用示例: pytest -q test/dsl/test_ast_visitor.py -k test_missing_return_reports_diagnostics
# 对应功能实现文件路径: kernel_gen/dsl/ast.py
# 对应 spec 文件路径: spec/dsl/ast.md
# 对应测试文件路径: test/dsl/test_ast_visitor.py
def test_missing_return_reports_diagnostics() -> None:
    def bad(x: "Tensor[f32, 2, 2]") -> "Tensor[f32, 2, 2]":
        y = x

    with pytest.raises(AstParseError) as exc_info:
        parse_function(bad)
    diagnostics = exc_info.value.diagnostics
    assert diagnostics
    assert diagnostics[0].location is not None


# MGEN-009
# 创建者: 小李飞刀
# 最后一次更改: 小李飞刀
# 最近一次运行测试时间: 2026-03-18 10:56:41 +0800
# 最近一次运行成功时间: 2026-03-18 10:56:41 +0800
# 功能说明: 验证返回类型不匹配会抛出带诊断的错误。
# 使用示例: pytest -q test/dsl/test_ast_visitor.py -k test_return_type_mismatch_reports_diagnostics
# 对应功能实现文件路径: kernel_gen/dsl/mlir_gen.py
# 对应 spec 文件路径: spec/dsl/mlir_gen.md
# 对应测试文件路径: test/dsl/test_ast_visitor.py
def test_return_type_mismatch_reports_diagnostics() -> None:
    def bad(x: "Tensor[f32, 2, 2]", y: "Tensor[f32, 2, 2]") -> "Tensor[f32, 2, 2]":
        return x == y

    with pytest.raises(AstVisitorError) as exc_info:
        build_func_op(bad)
    assert exc_info.value.location is not None


# AST-008
# 创建者: 小李飞刀
# 最后一次更改: 小李飞刀
# 最近一次运行测试时间: 2026-03-18 10:56:41 +0800
# 最近一次运行成功时间: 2026-03-18 10:56:41 +0800
# 功能说明: 验证缺少维度的 Tensor 注解会抛出带诊断的错误。
# 使用示例: pytest -q test/dsl/test_ast_visitor.py -k test_missing_tensor_dimensions_reports_diagnostics
# 对应功能实现文件路径: kernel_gen/dsl/ast.py
# 对应 spec 文件路径: spec/dsl/ast.md
# 对应测试文件路径: test/dsl/test_ast_visitor.py
def test_missing_tensor_dimensions_reports_diagnostics() -> None:
    def bad_string(x: "Tensor[f32]") -> "Tensor[f32, 2, 2]":
        return x
    with pytest.raises(AstParseError) as exc_info:
        parse_function(bad_string)
    diagnostics = exc_info.value.diagnostics
    assert diagnostics
    assert diagnostics[0].location is not None


# MGEN-010
# 创建者: 小李飞刀
# 最后一次更改: 小李飞刀
# 最近一次运行测试时间: 2026-03-18 10:56:41 +0800
# 最近一次运行成功时间: 2026-03-18 10:56:41 +0800
# 功能说明: 验证多语句 SSA 顺序与 value 复用。
# 使用示例: pytest -q test/dsl/test_ast_visitor.py -k test_multi_statement_ssa_order_and_reuse
# 对应功能实现文件路径: kernel_gen/dsl/mlir_gen.py
# 对应 spec 文件路径: spec/dsl/mlir_gen.md
# 对应测试文件路径: test/dsl/test_ast_visitor.py
def test_multi_statement_ssa_order_and_reuse() -> None:
    def add(
        x: "Tensor[f32, 2, 2]",
        y: "Tensor[f32, 2, 2]",
    ) -> "Tensor[f32, 2, 2]":
        z = x + y
        w = z + z
        return w

    func_op = build_func_op(add)
    ops = [op for op in func_op.body.block.ops if isinstance(op, NnAddOp)]
    assert len(ops) == 2
    first, second = ops
    assert second.lhs is first.result
    assert second.rhs is first.result


# EMIT-005
# 创建者: 小李飞刀
# 最后一次更改: 小李飞刀
# 最近一次运行测试时间: 2026-03-18 10:56:41 +0800
# 最近一次运行成功时间: 2026-03-18 10:56:41 +0800
# 功能说明: 验证 LoadAST lowering 生成 dma.load。
# 使用示例: pytest -q test/dsl/test_ast_visitor.py -k test_load_ast_lowering_rejected
# 对应功能实现文件路径: kernel_gen/dsl/emit_mlir.py
# 对应 spec 文件路径: spec/dsl/emit_mlir.md
# 对应测试文件路径: test/dsl/test_ast_visitor.py
def test_load_ast_lowering_rejected() -> None:
    memory = Memory([2, 2], NumericType.Float32)
    tensor = TensorAST(name="x", memory=memory, location=None)
    load = LoadAST(tensor=tensor, offset=[ConstAST(0), ConstAST(0)], stride=None, location=None)
    func_ast = FunctionAST(name="load", inputs=[tensor], outputs=[], body=BlockAST([load]))
    func_op = build_func_op_from_ast(func_ast)
    ops = [op for op in func_op.body.block.ops if isinstance(op, DmaLoadOp)]
    assert len(ops) == 1


# EMIT-006
# 创建者: 小李飞刀
# 最后一次更改: 小李飞刀
# 最近一次运行测试时间: 2026-03-18 10:56:41 +0800
# 最近一次运行成功时间: 2026-03-18 10:56:41 +0800
# 功能说明: 验证 StoreAST lowering 生成 dma.store。
# 使用示例: pytest -q test/dsl/test_ast_visitor.py -k test_store_ast_lowering_rejected
# 对应功能实现文件路径: kernel_gen/dsl/emit_mlir.py
# 对应 spec 文件路径: spec/dsl/emit_mlir.md
# 对应测试文件路径: test/dsl/test_ast_visitor.py
def test_store_ast_lowering_rejected() -> None:
    memory = Memory([2, 2], NumericType.Float32)
    tensor = TensorAST(name="x", memory=memory, location=None)
    store = StoreAST(tensor=tensor, offset=[ConstAST(0), ConstAST(0)], stride=None, value=tensor, location=None)
    func_ast = FunctionAST(name="store", inputs=[tensor], outputs=[], body=BlockAST([store, tensor]))
    func_op = build_func_op_from_ast(func_ast)
    ops = [op for op in func_op.body.block.ops if isinstance(op, DmaStoreOp)]
    assert len(ops) == 1


# EMIT-007
# 创建者: 小李飞刀
# 最后一次更改: 金铲铲大作战
# 最近一次运行测试时间: 2026-03-21 21:12:00 +0800
# 最近一次运行成功时间: 2026-03-21 21:12:00 +0800
# 功能说明: 验证 LoadAST 非 unit stride 抛出带诊断的错误。
# 使用示例: pytest -q test/dsl/test_ast_visitor.py -k test_load_ast_lowering_raises_lowering_error
# 对应功能实现文件路径: kernel_gen/dsl/emit_mlir.py
# 对应 spec 文件路径: spec/dsl/emit_mlir.md
# 对应测试文件路径: test/dsl/test_ast_visitor.py
def test_load_ast_lowering_raises_lowering_error() -> None:
    memory = Memory([2, 2], NumericType.Float32)
    tensor = TensorAST(name="x", memory=memory, location=SourceLocation(1, 0))
    load = LoadAST(
        tensor=tensor,
        offset=[ConstAST(0, location=SourceLocation(2, 2)), ConstAST(0, location=SourceLocation(2, 5))],
        stride=ConstAST(2, location=SourceLocation(2, 9)),
        location=SourceLocation(2, 0),
    )
    func_ast = FunctionAST(name="load", inputs=[tensor], outputs=[], body=BlockAST([load]))
    with pytest.raises(AstVisitorError, match="Only unit stride is supported") as exc_info:
        build_func_op_from_ast(func_ast)
    assert exc_info.value.location is not None


# EMIT-008
# 创建者: 金铲铲大作战
# 最后一次更改: 金铲铲大作战
# 最近一次运行测试时间: 2026-03-21 21:12:00 +0800
# 最近一次运行成功时间: 2026-03-21 21:12:00 +0800
# 功能说明: 验证 index rank mismatch 抛错并保留位置信息。
# 使用示例: pytest -q test/dsl/test_ast_visitor.py -k test_load_ast_index_rank_mismatch_reports_location
# 对应功能实现文件路径: kernel_gen/dsl/emit_mlir.py
# 对应 spec 文件路径: spec/dsl/emit_mlir.md
# 对应测试文件路径: test/dsl/test_ast_visitor.py
def test_load_ast_index_rank_mismatch_reports_location() -> None:
    memory = Memory([2, 2], NumericType.Float32)
    tensor = TensorAST(name="x", memory=memory, location=SourceLocation(1, 0))
    load = LoadAST(
        tensor=tensor,
        offset=[ConstAST(0, location=SourceLocation(2, 2))],
        stride=None,
        location=SourceLocation(2, 0),
    )
    func_ast = FunctionAST(name="load", inputs=[tensor], outputs=[], body=BlockAST([load]))
    with pytest.raises(AstVisitorError, match="Index rank mismatch") as exc_info:
        build_func_op_from_ast(func_ast)
    assert exc_info.value.location is not None


# EMIT-009
# 创建者: 小李飞刀
# 最后一次更改: 小李飞刀
# 最近一次运行测试时间: 2026-03-18 10:56:41 +0800
# 最近一次运行成功时间: 2026-03-18 10:56:41 +0800
# 功能说明: 验证 StoreAST 非 memory value 抛出带诊断的错误。
# 使用示例: pytest -q test/dsl/test_ast_visitor.py -k test_store_ast_lowering_raises_lowering_error
# 对应功能实现文件路径: kernel_gen/dsl/emit_mlir.py
# 对应 spec 文件路径: spec/dsl/emit_mlir.md
# 对应测试文件路径: test/dsl/test_ast_visitor.py
def test_store_ast_lowering_raises_lowering_error() -> None:
    memory = Memory([2, 2], NumericType.Float32)
    tensor = TensorAST(name="x", memory=memory, location=None)
    store = StoreAST(tensor=tensor, offset=[ConstAST(0), ConstAST(0)], stride=None, value=ConstAST(1), location=None)
    func_ast = FunctionAST(name="store", inputs=[tensor], outputs=[], body=BlockAST([store, tensor]))
    with pytest.raises(AstVisitorError, match="Operand must be nn.memory"):
        build_func_op_from_ast(func_ast)


# EMIT-010
# 创建者: 摸鱼小分队
# 最后一次更改: 摸鱼小分队
# 最近一次运行测试时间: 2026-03-21 00:00:00 +0800
# 最近一次运行成功时间: 2026-03-21 00:00:00 +0800
# 功能说明: 验证 ForAST lowering 会解析 loop var 并生成 dma.load。
# 使用示例: pytest -q test/dsl/test_ast_visitor.py -k test_for_ast_lowering_emits_loads
# 对应功能实现文件路径: kernel_gen/dsl/emit_mlir.py
# 对应 spec 文件路径: spec/dsl/emit_mlir.md
# 对应测试文件路径: test/dsl/test_ast_visitor.py
def test_for_ast_lowering_emits_loads() -> None:
    memory = Memory([2, 2], NumericType.Float32)
    tensor = TensorAST(name="x", memory=memory, location=None)
    loop_var = VarAST(name="i", location=None)
    body = BlockAST(
        [
            LoadAST(
                tensor=tensor,
                offset=[loop_var, ConstAST(0)],
                stride=None,
                location=None,
            )
        ]
    )
    loop = ForAST(var=loop_var, start=ConstAST(0), end=ConstAST(2), body=body, location=None)
    func_ast = FunctionAST(name="loop", inputs=[tensor], outputs=[], body=BlockAST([loop, tensor]))
    func_op = build_func_op_from_ast(func_ast)
    ops = [op for op in func_op.body.block.ops if isinstance(op, DmaLoadOp)]
    assert len(ops) == 2


# MGEN-011
# 创建者: 金铲铲大作战
# 最后一次更改: 小李飞刀
# 最近一次运行测试时间: 2026-03-19 03:24:32 +0800
# 最近一次运行成功时间: 2026-03-19 03:24:32 +0800
# 功能说明: 验证 singleton dim 隐式 broadcast lowering 为 nn.broadcast + nn.add。
# 使用示例: pytest -q test/dsl/test_ast_visitor.py -k test_tensor_binary_implicit_broadcast_lowering
# 对应功能实现文件路径: kernel_gen/dsl/mlir_gen.py
# 对应 spec 文件路径: spec/dsl/mlir_gen.md
# 对应测试文件路径: test/dsl/test_ast_visitor.py
def test_tensor_binary_implicit_broadcast_lowering() -> None:
    def add(
        x: "Tensor[f32, 1, N]",
        y: "Tensor[f32, M, N]",
    ) -> "Tensor[f32, M, N]":
        return x + y

    func_op = build_func_op(add)
    broadcast_ops = [op for op in func_op.body.block.ops if isinstance(op, NnBroadcastOp)]
    assert len(broadcast_ops) == 1
    add_op = next(op for op in func_op.body.block.ops if isinstance(op, NnAddOp))
    assert add_op.lhs is broadcast_ops[0].result or add_op.rhs is broadcast_ops[0].result


# MGEN-012
# 创建者: 金铲铲大作战
# 最后一次更改: 小李飞刀
# 最近一次运行测试时间: 2026-03-19 03:24:32 +0800
# 最近一次运行成功时间: 2026-03-19 03:24:32 +0800
# 功能说明: 验证前置维隐式 broadcast lowering 为 nn.broadcast + nn.add。
# 使用示例: pytest -q test/dsl/test_ast_visitor.py -k test_tensor_binary_prepend_broadcast_lowering
# 对应功能实现文件路径: kernel_gen/dsl/mlir_gen.py
# 对应 spec 文件路径: spec/dsl/mlir_gen.md
# 对应测试文件路径: test/dsl/test_ast_visitor.py
def test_tensor_binary_prepend_broadcast_lowering() -> None:
    def add(
        x: "Tensor[f32, N]",
        y: "Tensor[f32, M, N]",
    ) -> "Tensor[f32, M, N]":
        return x + y

    func_op = build_func_op(add)
    broadcast_ops = [op for op in func_op.body.block.ops if isinstance(op, NnBroadcastOp)]
    assert len(broadcast_ops) == 1
    add_op = next(op for op in func_op.body.block.ops if isinstance(op, NnAddOp))
    assert add_op.lhs is broadcast_ops[0].result or add_op.rhs is broadcast_ops[0].result


# MGEN-013
# 创建者: 金铲铲大作战
# 最后一次更改: 小李飞刀
# 最近一次运行测试时间: 2026-03-19 03:24:32 +0800
# 最近一次运行成功时间: 2026-03-19 03:24:32 +0800
# 功能说明: 验证比较表达式隐式 broadcast lowering 为 nn.broadcast + nn.eq。
# 使用示例: pytest -q test/dsl/test_ast_visitor.py -k test_compare_implicit_broadcast_lowering
# 对应功能实现文件路径: kernel_gen/dsl/mlir_gen.py
# 对应 spec 文件路径: spec/dsl/mlir_gen.md
# 对应测试文件路径: test/dsl/test_ast_visitor.py
def test_compare_implicit_broadcast_lowering() -> None:
    lhs_memory = Memory([1, "N"], NumericType.Float32)
    rhs_memory = Memory(["M", "N"], NumericType.Float32)
    lhs = TensorAST(name="x", memory=lhs_memory, location=None)
    rhs = TensorAST(name="y", memory=rhs_memory, location=None)
    expr = CompareExprAST(op="eq", lhs=lhs, rhs=rhs, location=None)
    func_ast = FunctionAST(name="eq", inputs=[lhs, rhs], outputs=[], body=BlockAST([expr]))
    func_op = build_func_op_from_ast(func_ast)
    broadcast_ops = [op for op in func_op.body.block.ops if isinstance(op, NnBroadcastOp)]
    assert len(broadcast_ops) == 1
    eq_op = next(op for op in func_op.body.block.ops if isinstance(op, NnEqOp))
    assert eq_op.lhs is broadcast_ops[0].result or eq_op.rhs is broadcast_ops[0].result


# MGEN-014
# 创建者: 金铲铲大作战
# 最后一次更改: 小李飞刀
# 最近一次运行测试时间: 2026-03-19 03:24:32 +0800
# 最近一次运行成功时间: 2026-03-19 03:24:32 +0800
# 功能说明: 验证不可广播的逐元素表达式抛 LoweringError 且保留位置。
# 使用示例: pytest -q test/dsl/test_ast_visitor.py -k test_tensor_binary_implicit_broadcast_mismatch_reports_diagnostics
# 对应功能实现文件路径: kernel_gen/dsl/mlir_gen.py
# 对应 spec 文件路径: spec/dsl/mlir_gen.md
# 对应测试文件路径: test/dsl/test_ast_visitor.py
def test_tensor_binary_implicit_broadcast_mismatch_reports_diagnostics() -> None:
    def add(
        x: "Tensor[f32, A, B]",
        y: "Tensor[f32, A, C]",
    ) -> "Tensor[f32, A, B]":
        return x + y

    with pytest.raises(AstVisitorError, match="Implicit broadcast dimension mismatch") as exc_info:
        build_func_op(add)
    assert exc_info.value.location is not None

# AST-009
# 创建者: 小李飞刀
# 最后一次更改: 小李飞刀
# 最近一次运行测试时间: 2026-03-18 10:56:41 +0800
# 最近一次运行成功时间: 2026-03-18 10:56:41 +0800
# 功能说明: 验证不支持语法会抛出带诊断的错误。
# 使用示例: pytest -q test/dsl/test_ast_visitor.py -k test_unsupported_syntax_reports_diagnostics
# 对应功能实现文件路径: kernel_gen/dsl/ast.py
# 对应 spec 文件路径: spec/dsl/ast.md
# 对应测试文件路径: test/dsl/test_ast_visitor.py
def test_unsupported_syntax_reports_diagnostics() -> None:
    def bad(x: "Tensor[f32, 2, 2]") -> "Tensor[f32, 2, 2]":
        if x:
            return x
        return x

    with pytest.raises(AstParseError) as exc_info:
        parse_function(bad)
    diagnostics = exc_info.value.diagnostics
    assert diagnostics
    assert diagnostics[0].location is not None
