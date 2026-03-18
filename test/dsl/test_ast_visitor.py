"""AST visitor tests.

创建者: 小李飞刀
最后一次更改: 小李飞刀

功能说明:
- 覆盖 AST 前端、nn dialect IR 与 MLIR 文本入口的回归测试。

使用示例:
- pytest -q test/dsl/test_ast_visitor.py

关联文件:
- 功能实现: python/dsl/ast_visitor.py
- Spec 文档: spec/dsl/ast_visitor.md
- 测试文件: test/dsl/test_ast_visitor.py
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest
from xdsl.dialects import func
from xdsl.dialects.builtin import ModuleOp, i32

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from python.dialect.nn import NnAddOp, NnMemoryType
from python.dsl.ast import BlockAST, BinaryExprAST, ConstAST, FunctionAST, LoadAST, StoreAST, TensorAST
from python.dsl.ast_visitor import AstVisitorError, emit_mlir, visit_function, visit_to_nn_ir
from python.dsl.lowering import LoweringError, lower_to_nn_ir
from python.symbol_variable.memory import Memory
from python.symbol_variable.type import NumericType


# AV-001
# 创建者: 小李飞刀
# 最后一次更改: 小李飞刀
# 最近一次运行测试时间: 2026-03-18 10:56:41 +0800
# 最近一次运行成功时间: 2026-03-18 10:56:41 +0800
# 功能说明: 验证函数解析生成 AST 与位置信息。
# 使用示例: pytest -q test/dsl/test_ast_visitor.py -k test_visit_function_builds_ast
# 对应功能实现文件路径: python/dsl/ast_visitor.py
# 对应 spec 文件路径: spec/dsl/ast_visitor.md
# 对应测试文件路径: test/dsl/test_ast_visitor.py
def test_visit_function_builds_ast() -> None:
    def add(
        x: "Tensor[f32, 2, 2]",
        y: "Tensor[f32, 2, 2]",
    ) -> "Tensor[f32, 2, 2]":
        z = x + y
        return z

    func_ast = visit_function(add, config={"keep_source": True})
    assert func_ast.name == "add"
    assert len(func_ast.inputs) == 2
    assert len(func_ast.outputs) == 1
    assert func_ast.source is not None
    assert len(func_ast.body.statements) == 2
    assert isinstance(func_ast.body.statements[0], BinaryExprAST)
    assert func_ast.body.location is not None


# AV-002
# 创建者: 小李飞刀
# 最后一次更改: 小李飞刀
# 最近一次运行测试时间: 2026-03-18 10:56:41 +0800
# 最近一次运行成功时间: 2026-03-18 10:56:41 +0800
# 功能说明: 验证 visit_to_nn_ir 生成 nn dialect IR。
# 使用示例: pytest -q test/dsl/test_ast_visitor.py -k test_visit_to_nn_ir_builds_module
# 对应功能实现文件路径: python/dsl/ast_visitor.py
# 对应 spec 文件路径: spec/dsl/ast_visitor.md
# 对应测试文件路径: test/dsl/test_ast_visitor.py
def test_visit_to_nn_ir_builds_module() -> None:
    def add(
        x: "Tensor[f32, 2, 2]",
        y: "Tensor[f32, 2, 2]",
    ) -> "Tensor[f32, 2, 2]":
        z = x + y
        return z

    module = visit_to_nn_ir(add)
    assert isinstance(module, ModuleOp)
    assert any(isinstance(op, func.FuncOp) for op in module.ops)
    assert any(isinstance(op, NnAddOp) for op in module.walk())


# AV-003
# 创建者: 小李飞刀
# 最后一次更改: 小李飞刀
# 最近一次运行测试时间: 2026-03-18 10:56:41 +0800
# 最近一次运行成功时间: 2026-03-18 10:56:41 +0800
# 功能说明: 验证 emit_mlir 输出包含 nn dialect 文本。
# 使用示例: pytest -q test/dsl/test_ast_visitor.py -k test_emit_mlir_output
# 对应功能实现文件路径: python/dsl/ast_visitor.py
# 对应 spec 文件路径: spec/dsl/ast_visitor.md
# 对应测试文件路径: test/dsl/test_ast_visitor.py
def test_emit_mlir_output() -> None:
    def add(
        x: "Tensor[f32, 2, 2]",
        y: "Tensor[f32, 2, 2]",
    ) -> "Tensor[f32, 2, 2]":
        z = x + y
        return z

    text = emit_mlir(add)
    assert "nn.add" in text
    assert "func.func" in text


# AV-003A
# 创建者: 小李飞刀
# 最后一次更改: 小李飞刀
# 最近一次运行测试时间: 2026-03-18 10:56:41 +0800
# 最近一次运行成功时间: 2026-03-18 10:56:41 +0800
# 功能说明: 验证 globals/builtins 入口可解析 Tensor 注解。
# 使用示例: pytest -q test/dsl/test_ast_visitor.py -k test_globals_and_builtins_annotation_entry
# 对应功能实现文件路径: python/dsl/ast_visitor.py
# 对应 spec 文件路径: spec/dsl/ast_visitor.md
# 对应测试文件路径: test/dsl/test_ast_visitor.py
def test_globals_and_builtins_annotation_entry() -> None:
    class TensorAlias:
        pass

    def add_global(x: TensorAlias[f32, 2, 2], y: TensorAlias[f32, 2, 2]) -> TensorAlias[f32, 2, 2]:
        return x + y

    def add_builtin(x: TensorAlias[f32, 2, 2], y: TensorAlias[f32, 2, 2]) -> TensorAlias[f32, 2, 2]:
        return x + y

    func_ast = visit_function(add_global, globals={"TensorAlias": TensorAlias})
    assert func_ast.name == "add_global"

    func_ast = visit_function(add_builtin, builtins={"TensorAlias": TensorAlias})
    assert func_ast.name == "add_builtin"


# AV-003B
# 创建者: 小李飞刀
# 最后一次更改: 小李飞刀
# 最近一次运行测试时间: 2026-03-18 10:56:41 +0800
# 最近一次运行成功时间: 2026-03-18 10:56:41 +0800
# 功能说明: 验证 ScalarArgAST 会 lowering 为 func.func 标量参数。
# 使用示例: pytest -q test/dsl/test_ast_visitor.py -k test_scalar_arg_lowering_in_signature
# 对应功能实现文件路径: python/dsl/lowering.py
# 对应 spec 文件路径: spec/dsl/ast_visitor.md
# 对应测试文件路径: test/dsl/test_ast_visitor.py
def test_scalar_arg_lowering_in_signature() -> None:
    def add(
        x: "Tensor[f32, 2, 2]",
        y: "Tensor[f32, 2, 2]",
        n: int,
    ) -> "Tensor[f32, 2, 2]":
        return x + y

    module = visit_to_nn_ir(add)
    func_op = next(op for op in module.ops if isinstance(op, func.FuncOp))
    inputs = list(func_op.function_type.inputs)
    assert len(inputs) == 3
    assert isinstance(inputs[0], NnMemoryType)
    assert isinstance(inputs[1], NnMemoryType)
    assert inputs[2] == i32


# AV-003C
# 创建者: 小李飞刀
# 最后一次更改: 小李飞刀
# 最近一次运行测试时间: 2026-03-18 10:56:41 +0800
# 最近一次运行成功时间: 2026-03-18 10:56:41 +0800
# 功能说明: 验证未知名称在 AST 阶段产生诊断信息。
# 使用示例: pytest -q test/dsl/test_ast_visitor.py -k test_unknown_name_reports_diagnostics
# 对应功能实现文件路径: python/dsl/ast_visitor.py
# 对应 spec 文件路径: spec/dsl/ast_visitor.md
# 对应测试文件路径: test/dsl/test_ast_visitor.py
def test_unknown_name_reports_diagnostics() -> None:
    def bad(x: "Tensor[f32, 2, 2]") -> "Tensor[f32, 2, 2]":
        return y

    with pytest.raises(AstVisitorError) as exc_info:
        visit_function(bad)
    diagnostics = exc_info.value.diagnostics
    assert diagnostics
    assert diagnostics[0].location is not None


# AV-003D
# 创建者: 小李飞刀
# 最后一次更改: 小李飞刀
# 最近一次运行测试时间: 2026-03-18 10:56:41 +0800
# 最近一次运行成功时间: 2026-03-18 10:56:41 +0800
# 功能说明: 验证 lowering 失败时诊断信息包含位置信息。
# 使用示例: pytest -q test/dsl/test_ast_visitor.py -k test_lowering_failure_reports_diagnostics
# 对应功能实现文件路径: python/dsl/lowering.py
# 对应 spec 文件路径: spec/dsl/ast_visitor.md
# 对应测试文件路径: test/dsl/test_ast_visitor.py
def test_lowering_failure_reports_diagnostics() -> None:
    def bad(x: "Tensor[f32, 2, 2]") -> "Tensor[f32, 2, 2]":
        return x + 1

    with pytest.raises(AstVisitorError) as exc_info:
        visit_to_nn_ir(bad)
    diagnostics = exc_info.value.diagnostics
    assert diagnostics
    assert diagnostics[0].location is not None


# AV-003E
# 创建者: 小李飞刀
# 最后一次更改: 小李飞刀
# 最近一次运行测试时间: 2026-03-18 10:56:41 +0800
# 最近一次运行成功时间: 2026-03-18 10:56:41 +0800
# 功能说明: 验证非法返回注解会保留可定位诊断并向上抛出。
# 使用示例: pytest -q test/dsl/test_ast_visitor.py -k test_invalid_return_annotation_reports_diagnostics
# 对应功能实现文件路径: python/dsl/ast_visitor.py
# 对应 spec 文件路径: spec/dsl/ast_visitor.md
# 对应测试文件路径: test/dsl/test_ast_visitor.py
def test_invalid_return_annotation_reports_diagnostics() -> None:
    def bad_return(x: "Tensor[f32, 2, 2]") -> "NotSupported":
        return x

    with pytest.raises(AstVisitorError) as exc_info:
        visit_function(bad_return)
    diagnostics = exc_info.value.diagnostics
    assert diagnostics
    assert diagnostics[0].location is not None


# AV-003F
# 创建者: 小李飞刀
# 最后一次更改: 小李飞刀
# 最近一次运行测试时间: 2026-03-18 10:56:41 +0800
# 最近一次运行成功时间: 2026-03-18 10:56:41 +0800
# 功能说明: 验证非法 Tensor 返回注解会抛出带诊断的错误。
# 使用示例: pytest -q test/dsl/test_ast_visitor.py -k test_invalid_tensor_return_annotation_reports_diagnostics
# 对应功能实现文件路径: python/dsl/ast_visitor.py
# 对应 spec 文件路径: spec/dsl/ast_visitor.md
# 对应测试文件路径: test/dsl/test_ast_visitor.py
def test_invalid_tensor_return_annotation_reports_diagnostics() -> None:
    def bad_return(x: "Tensor[f32, 2, 2]") -> "Tensor[f16, 2, 2]":
        return x

    with pytest.raises(AstVisitorError) as exc_info:
        visit_function(bad_return)
    diagnostics = exc_info.value.diagnostics
    assert diagnostics
    assert diagnostics[0].location is not None


# AV-003G
# 创建者: 小李飞刀
# 最后一次更改: 小李飞刀
# 最近一次运行测试时间: 2026-03-18 10:56:41 +0800
# 最近一次运行成功时间: 2026-03-18 10:56:41 +0800
# 功能说明: 验证常量 lowering 失败会抛出带诊断的错误。
# 使用示例: pytest -q test/dsl/test_ast_visitor.py -k test_constant_lowering_reports_diagnostics
# 对应功能实现文件路径: python/dsl/lowering.py
# 对应 spec 文件路径: spec/dsl/lowering.md
# 对应测试文件路径: test/dsl/test_ast_visitor.py
def test_constant_lowering_reports_diagnostics() -> None:
    def bad(x: "Tensor[f32, 2, 2]") -> "Tensor[f32, 2, 2]":
        return 1

    with pytest.raises(AstVisitorError) as exc_info:
        visit_to_nn_ir(bad)
    diagnostics = exc_info.value.diagnostics
    assert diagnostics
    assert diagnostics[0].location is not None


# AV-003H
# 创建者: 小李飞刀
# 最后一次更改: 小李飞刀
# 最近一次运行测试时间: 2026-03-18 10:56:41 +0800
# 最近一次运行成功时间: 2026-03-18 10:56:41 +0800
# 功能说明: 验证缺失 return 会抛出带诊断的错误。
# 使用示例: pytest -q test/dsl/test_ast_visitor.py -k test_missing_return_reports_diagnostics
# 对应功能实现文件路径: python/dsl/ast_visitor.py
# 对应 spec 文件路径: spec/dsl/ast_visitor.md
# 对应测试文件路径: test/dsl/test_ast_visitor.py
def test_missing_return_reports_diagnostics() -> None:
    def bad(x: "Tensor[f32, 2, 2]") -> "Tensor[f32, 2, 2]":
        y = x

    with pytest.raises(AstVisitorError) as exc_info:
        visit_function(bad)
    diagnostics = exc_info.value.diagnostics
    assert diagnostics
    assert diagnostics[0].location is not None


# AV-003I
# 创建者: 小李飞刀
# 最后一次更改: 小李飞刀
# 最近一次运行测试时间: 2026-03-18 10:56:41 +0800
# 最近一次运行成功时间: 2026-03-18 10:56:41 +0800
# 功能说明: 验证返回类型不匹配会抛出带诊断的错误。
# 使用示例: pytest -q test/dsl/test_ast_visitor.py -k test_return_type_mismatch_reports_diagnostics
# 对应功能实现文件路径: python/dsl/lowering.py
# 对应 spec 文件路径: spec/dsl/lowering.md
# 对应测试文件路径: test/dsl/test_ast_visitor.py
def test_return_type_mismatch_reports_diagnostics() -> None:
    def bad(x: "Tensor[f32, 2, 2]", y: "Tensor[f32, 2, 2]") -> "Tensor[f32, 2, 2]":
        return x == y

    with pytest.raises(AstVisitorError) as exc_info:
        visit_to_nn_ir(bad)
    diagnostics = exc_info.value.diagnostics
    assert diagnostics
    assert diagnostics[0].location is not None


# AV-003J
# 创建者: 小李飞刀
# 最后一次更改: 小李飞刀
# 最近一次运行测试时间: 2026-03-18 10:56:41 +0800
# 最近一次运行成功时间: 2026-03-18 10:56:41 +0800
# 功能说明: 验证缺少维度的 Tensor 注解会抛出带诊断的错误。
# 使用示例: pytest -q test/dsl/test_ast_visitor.py -k test_missing_tensor_dimensions_reports_diagnostics
# 对应功能实现文件路径: python/dsl/ast_visitor.py
# 对应 spec 文件路径: spec/dsl/ast_visitor.md
# 对应测试文件路径: test/dsl/test_ast_visitor.py
def test_missing_tensor_dimensions_reports_diagnostics() -> None:
    class TensorAlias:
        pass

    def bad_string(x: "Tensor[f32]") -> "Tensor[f32, 2, 2]":
        return x

    def bad_subscript(x: TensorAlias[f32]) -> TensorAlias[f32, 2, 2]:
        return x

    def bad_tensor(x: Tensor[f32]) -> Tensor[f32, 2, 2]:
        return x

    for fn, globals_table in [
        (bad_string, None),
        (bad_subscript, {"TensorAlias": TensorAlias}),
        (bad_tensor, None),
    ]:
        with pytest.raises(AstVisitorError) as exc_info:
            if globals_table:
                visit_function(fn, globals=globals_table)
            else:
                visit_function(fn)
        diagnostics = exc_info.value.diagnostics
        assert diagnostics
        assert diagnostics[0].location is not None


# AV-003K
# 创建者: 小李飞刀
# 最后一次更改: 小李飞刀
# 最近一次运行测试时间: 2026-03-18 10:56:41 +0800
# 最近一次运行成功时间: 2026-03-18 10:56:41 +0800
# 功能说明: 验证多语句 SSA 顺序与 value 复用。
# 使用示例: pytest -q test/dsl/test_ast_visitor.py -k test_multi_statement_ssa_order_and_reuse
# 对应功能实现文件路径: python/dsl/lowering.py
# 对应 spec 文件路径: spec/dsl/lowering.md
# 对应测试文件路径: test/dsl/test_ast_visitor.py
def test_multi_statement_ssa_order_and_reuse() -> None:
    def add(
        x: "Tensor[f32, 2, 2]",
        y: "Tensor[f32, 2, 2]",
    ) -> "Tensor[f32, 2, 2]":
        z = x + y
        w = z + z
        return w

    module = visit_to_nn_ir(add)
    func_op = next(op for op in module.ops if isinstance(op, func.FuncOp))
    ops = [op for op in func_op.body.block.ops if isinstance(op, NnAddOp)]
    assert len(ops) == 2
    first, second = ops
    assert second.lhs is first.result
    assert second.rhs is first.result


# AV-003L
# 创建者: 小李飞刀
# 最后一次更改: 小李飞刀
# 最近一次运行测试时间: 2026-03-18 10:56:41 +0800
# 最近一次运行成功时间: 2026-03-18 10:56:41 +0800
# 功能说明: 验证 LoadAST 在 lowering 阶段显式报错。
# 使用示例: pytest -q test/dsl/test_ast_visitor.py -k test_load_ast_lowering_rejected
# 对应功能实现文件路径: python/dsl/lowering.py
# 对应 spec 文件路径: spec/dsl/lowering.md
# 对应测试文件路径: test/dsl/test_ast_visitor.py
def test_load_ast_lowering_rejected() -> None:
    memory = Memory([2, 2], NumericType.Float32)
    tensor = TensorAST(name="x", memory=memory, location=None)
    load = LoadAST(tensor=tensor, offset=ConstAST(0), stride=None, location=None)
    func_ast = FunctionAST(name="load", inputs=[tensor], outputs=[], body=BlockAST([load]))
    with pytest.raises(LoweringError, match="LoadAST lowering is not supported"):
        lower_to_nn_ir(func_ast)


# AV-003M
# 创建者: 小李飞刀
# 最后一次更改: 小李飞刀
# 最近一次运行测试时间: 2026-03-18 10:56:41 +0800
# 最近一次运行成功时间: 2026-03-18 10:56:41 +0800
# 功能说明: 验证 StoreAST 在 lowering 阶段显式报错。
# 使用示例: pytest -q test/dsl/test_ast_visitor.py -k test_store_ast_lowering_rejected
# 对应功能实现文件路径: python/dsl/lowering.py
# 对应 spec 文件路径: spec/dsl/lowering.md
# 对应测试文件路径: test/dsl/test_ast_visitor.py
def test_store_ast_lowering_rejected() -> None:
    memory = Memory([2, 2], NumericType.Float32)
    tensor = TensorAST(name="x", memory=memory, location=None)
    store = StoreAST(tensor=tensor, offset=ConstAST(0), stride=None, value=ConstAST(1), location=None)
    func_ast = FunctionAST(name="store", inputs=[tensor], outputs=[], body=BlockAST([store]))
    with pytest.raises(LoweringError, match="StoreAST lowering is not supported"):
        lower_to_nn_ir(func_ast)


# AV-003L
# 创建者: 小李飞刀
# 最后一次更改: 小李飞刀
# 最近一次运行测试时间: 2026-03-18 10:56:41 +0800
# 最近一次运行成功时间: 2026-03-18 10:56:41 +0800
# 功能说明: 验证 lower_to_nn_ir 在 LoadAST 时抛 LoweringError 且不生成 IR。
# 使用示例: pytest -q test/dsl/test_ast_visitor.py -k test_load_ast_lowering_raises_lowering_error
# 对应功能实现文件路径: python/dsl/lowering.py
# 对应 spec 文件路径: spec/dsl/lowering.md
# 对应测试文件路径: test/dsl/test_ast_visitor.py
def test_load_ast_lowering_raises_lowering_error() -> None:
    memory = Memory([2, 2], NumericType.Float32)
    tensor = TensorAST(name="x", memory=memory, location=None)
    load = LoadAST(tensor=tensor, offset=ConstAST(0), stride=None, location=None)
    func_ast = FunctionAST(name="load", inputs=[tensor], outputs=[], body=BlockAST([load]))
    with pytest.raises(LoweringError, match="LoadAST lowering is not supported"):
        lower_to_nn_ir(func_ast)


# AV-003M
# 创建者: 小李飞刀
# 最后一次更改: 小李飞刀
# 最近一次运行测试时间: 2026-03-18 10:56:41 +0800
# 最近一次运行成功时间: 2026-03-18 10:56:41 +0800
# 功能说明: 验证 lower_to_nn_ir 在 StoreAST 时抛 LoweringError 且不生成 IR。
# 使用示例: pytest -q test/dsl/test_ast_visitor.py -k test_store_ast_lowering_raises_lowering_error
# 对应功能实现文件路径: python/dsl/lowering.py
# 对应 spec 文件路径: spec/dsl/lowering.md
# 对应测试文件路径: test/dsl/test_ast_visitor.py
def test_store_ast_lowering_raises_lowering_error() -> None:
    memory = Memory([2, 2], NumericType.Float32)
    tensor = TensorAST(name="x", memory=memory, location=None)
    store = StoreAST(tensor=tensor, offset=ConstAST(0), stride=None, value=ConstAST(1), location=None)
    func_ast = FunctionAST(name="store", inputs=[tensor], outputs=[], body=BlockAST([store]))
    with pytest.raises(LoweringError, match="StoreAST lowering is not supported"):
        lower_to_nn_ir(func_ast)


# AV-004
# 创建者: 小李飞刀
# 最后一次更改: 小李飞刀
# 最近一次运行测试时间: 2026-03-18 10:56:41 +0800
# 最近一次运行成功时间: 2026-03-18 10:56:41 +0800
# 功能说明: 验证不支持语法会抛出带诊断的错误。
# 使用示例: pytest -q test/dsl/test_ast_visitor.py -k test_unsupported_syntax_reports_diagnostics
# 对应功能实现文件路径: python/dsl/ast_visitor.py
# 对应 spec 文件路径: spec/dsl/ast_visitor.md
# 对应测试文件路径: test/dsl/test_ast_visitor.py
def test_unsupported_syntax_reports_diagnostics() -> None:
    def bad(x: "Tensor[f32, 2, 2]") -> "Tensor[f32, 2, 2]":
        if x:
            return x
        return x

    with pytest.raises(AstVisitorError) as exc_info:
        visit_function(bad)
    diagnostics = exc_info.value.diagnostics
    assert diagnostics
    assert diagnostics[0].location is not None
