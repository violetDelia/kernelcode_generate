"""AST visitor tests.

创建者: 小李飞刀
最后一次更改: 我不是牛马

功能说明:
- 覆盖 AST 前端、nn dialect IR 与 MLIR 文本入口的回归测试。

使用示例:
- pytest -q test/dsl/test_ast_visitor.py

覆盖率信息:
- 覆盖率命令: pytest --cov=kernel_gen.dsl.ast_visitor --cov=kernel_gen.dsl.emit_mlir --cov=kernel_gen.dsl.mlir_gen --cov-report=term-missing -q test/dsl/test_ast_visitor.py
- 覆盖率结果: ast_visitor 98%, emit_mlir 98%, mlir_gen 99%（2026-03-24 03:29:58 +0800）
- 达标线: 95%

关联文件:
- 功能实现: kernel_gen/dsl/ast_visitor.py, kernel_gen/dsl/emit_mlir.py, kernel_gen/dsl/mlir_gen.py
- Spec 文档: spec/dsl/ast_visitor.md, spec/dsl/emit_mlir.md, spec/dsl/mlir_gen.md
- 测试文件: test/dsl/test_ast_visitor.py
"""

from __future__ import annotations

import inspect
from io import StringIO
import sys
from pathlib import Path

import pytest
from xdsl.dialects import arith, func, scf
from xdsl.dialects.builtin import (
    ArrayAttr,
    FloatAttr,
    IndexType,
    IntAttr,
    IntegerType,
    ModuleOp,
    StringAttr,
    f32,
    i1,
    i32,
)
from xdsl.ir import Block
from xdsl.printer import Printer

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from kernel_gen.dialect.dma import (
    DmaAllocOp,
    DmaCastOp,
    DmaCopyOp,
    DmaDesliceOp,
    DmaLoadOp,
    DmaReshapeOp,
    DmaSliceOp,
    DmaStoreOp,
    DmaViewOp,
)
from kernel_gen.dialect.arch import ArchGetBlockIdOp
from kernel_gen.dialect.nn import NnAddOp, NnBroadcastOp, NnEqOp, NnMemorySpaceAttr, NnMemoryType
from kernel_gen.dialect.symbol import (
    SymbolAddOp,
    SymbolDivOp,
    SymbolFloorDivOp,
    SymbolForOp,
    SymbolMulOp,
    SymbolSubOp,
    SymbolValueType,
)
from kernel_gen.dsl.ast import (
    AstParseError,
    ArchQueryAST,
    BlockAST,
    BinaryExprAST,
    CompareExprAST,
    ConstAST,
    DmaAllocAST,
    DmaCastAST,
    DmaCopyAST,
    DmaFlattenAST,
    DmaFreeAST,
    DmaReshapeAST,
    DmaViewAST,
    FunctionAST,
    ForAST,
    LoadAST,
    SourceLocation,
    StoreAST,
    TensorAST,
    VarAST,
    ScalarArgAST,
    _ParseFailure,
    parse_function,
)
from kernel_gen.dsl.ast_visitor import AstVisitor, AstVisitorError
from kernel_gen.dsl.emit_mlir import (
    EmitContext,
    _LoweringError,
    _build_default_stride_attrs,
    _build_index_operands_from_layout,
    _build_static_index_list,
    _build_stride,
    _build_stride_attrs,
    _build_index_attrs,
    _dtype_to_xdsl,
    _ensure_index_value,
    _ensure_supported_statements,
    _expr_key,
    _get_loop_vars,
    _infer_broadcast_memory_type,
    _infer_broadcast_shape,
    _infer_expr_type,
    _lower_loop_bound,
    _lower_expr,
    _lookup_symbol,
    _memory_space_from_ast,
    _memory_to_nn_type,
    _mul_symbol,
    _resolve_index_operand,
    _resolve_index_symbol,
    _resolve_static_index_expr,
    _resolve_index_expr,
    emit_mlir as emit_node_mlir,
)
from kernel_gen.dsl.mlir_gen import (
    _build_signature_types,
    _is_symbol_scalar_function,
    _parse_function_with_env,
    _symbol_expr_from_runtime_arg,
    _validate_return_type,
    build_func_op,
    build_func_op_from_ast,
)
from kernel_gen.dsl import mlir_gen as mlir_gen_module
from kernel_gen.dsl import ast_visitor as ast_visitor_module
import kernel_gen.operation.nn as nn
from kernel_gen.symbol_variable.memory import Memory, MemorySpace
from kernel_gen.symbol_variable.symbol_dim import SymbolDim
from kernel_gen.symbol_variable.type import NumericType


def _tensor_arg(shape: list[object]) -> Memory:
    return Memory(shape, NumericType.Float32)


def _module_from_func(fn: object, *runtime_args: object) -> ModuleOp:
    return ModuleOp([build_func_op(fn, *runtime_args)])


def _module_from_ast(func_ast: FunctionAST) -> ModuleOp:
    return ModuleOp([build_func_op_from_ast(func_ast)])


def _print_module(module: ModuleOp) -> str:
    stream = StringIO()
    printer = Printer(stream=stream)
    printer.print_op(module)
    return stream.getvalue()


def _unwrap_index_cast(value: object) -> object:
    owner = getattr(value, "owner", None)
    if isinstance(owner, arith.IndexCastOp):
        return owner.input
    return value


def _parse_function_from_source(
    monkeypatch: pytest.MonkeyPatch,
    source: str,
    runtime_table: dict[str, object] | None = None,
) -> FunctionAST:
    def kernel(*args: object, **kwargs: object) -> object:
        del args, kwargs
        return None

    def fake_getsource(_obj: object) -> str:
        return source

    monkeypatch.setattr(inspect, "getsource", fake_getsource)
    globals_table = dict(getattr(kernel, "__globals__", {}))
    builtins_obj = globals_table.get("__builtins__", __builtins__)
    builtins_table = builtins_obj if isinstance(builtins_obj, dict) else getattr(builtins_obj, "__dict__", {})
    return _parse_function_with_env(kernel, globals_table, builtins_table, runtime_table, config=None)


# AST-014A / MGEN-027
# 创建者: 我不是牛马
# 最后一次更改: 我不是牛马
# 最近一次运行测试时间: 2026-03-25 21:41:29 +0800
# 最近一次运行成功时间: 2026-03-25 21:41:29 +0800
# 功能说明: 验证零入参 get_block_id DSL 函数可解析并 lowering 为 arch.get_block_id。
# 测试目的: 锁定 get_block_id 查询的 AST 解析、build_func_op 与 build_func_op_from_ast 返回类型为 !symbol.int<"block_id">。
# 使用示例: pytest -q test/dsl/test_ast_visitor.py -k test_build_func_op_lowers_arch_get_block_id_query
# 对应功能实现文件路径: kernel_gen/dsl/ast.py, kernel_gen/dsl/mlir_gen.py
# 对应 spec 文件路径: spec/dsl/ast.md, spec/dsl/mlir_gen.md
# 对应测试文件路径: test/dsl/test_ast_visitor.py
def test_build_func_op_lowers_arch_get_block_id_query() -> None:
    def get_block_id_kernel() -> int:
        return get_block_id()

    func_ast = parse_function(get_block_id_kernel)
    if len(func_ast.inputs) != 0:
        raise AssertionError("expected get_block_id kernel to have no inputs")
    if len(func_ast.outputs) != 1:
        raise AssertionError("expected get_block_id kernel to have one output annotation")
    if len(func_ast.body.statements) != 1:
        raise AssertionError("expected get_block_id kernel to lower to one AST statement")
    if not isinstance(func_ast.body.statements[0], ArchQueryAST):
        raise AssertionError("expected get_block_id kernel to parse into ArchQueryAST")
    if func_ast.body.statements[0].query_name != "get_block_id":
        raise AssertionError("expected arch query name to stay get_block_id")

    for func_op in (build_func_op(get_block_id_kernel), build_func_op_from_ast(func_ast)):
        if len(tuple(func_op.body.block.args)) != 0:
            raise AssertionError("expected zero-argument func.func for get_block_id kernel")
        body_ops = list(func_op.body.block.ops)
        query_ops = [op for op in body_ops if isinstance(op, ArchGetBlockIdOp)]
        return_ops = [op for op in body_ops if isinstance(op, func.ReturnOp)]
        if len(query_ops) != 1:
            raise AssertionError("expected exactly one arch.get_block_id op")
        if query_ops[0].result.type != SymbolValueType.from_expr("block_id"):
            raise AssertionError('expected arch.get_block_id result type to be !symbol.int<"block_id">')
        if len(return_ops) != 1:
            raise AssertionError("expected exactly one func.return op")
        if len(return_ops[0].arguments) != 1:
            raise AssertionError("expected func.return to carry one value")
        if return_ops[0].arguments[0].type != SymbolValueType.from_expr("block_id"):
            raise AssertionError('expected func.return type to stay !symbol.int<"block_id">')


# AST-014B
# 创建者: 我不是牛马
# 最后一次更改: 我不是牛马
# 最近一次运行测试时间: 2026-03-25 21:41:29 +0800
# 最近一次运行成功时间: 2026-03-25 21:41:29 +0800
# 功能说明: 验证 get_block_id helper 拒绝位置参数与关键字参数。
# 测试目的: 锁定 get_block_id(1) 与 get_block_id(x=1) 在 AST 解析阶段保持 Unsupported get_block_id arity 诊断。
# 使用示例: pytest -q test/dsl/test_ast_visitor.py -k test_parse_function_rejects_invalid_get_block_id_arity_variants
# 对应功能实现文件路径: kernel_gen/dsl/ast.py
# 对应 spec 文件路径: spec/dsl/ast.md
# 对应测试文件路径: test/dsl/test_ast_visitor.py
def test_parse_function_rejects_invalid_get_block_id_arity_variants(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    invalid_sources = (
        """\
def kernel() -> int:
    return get_block_id(1)
""",
        """\
def kernel() -> int:
    return get_block_id(x=1)
""",
    )

    for source in invalid_sources:
        with pytest.raises(AstParseError) as exc_info:
            _parse_function_from_source(monkeypatch, source)
        diagnostics = exc_info.value.diagnostics
        if not diagnostics:
            raise AssertionError("expected diagnostics for invalid get_block_id arity")
        if diagnostics[0].message != "Unsupported get_block_id arity":
            raise AssertionError("expected Unsupported get_block_id arity diagnostic")


# EMIT-022
# 创建者: 我不是牛马
# 最后一次更改: 我不是牛马
# 最近一次运行测试时间: 2026-03-25 21:25:58 +0800
# 最近一次运行成功时间: 2026-03-25 21:25:58 +0800
# 功能说明: 验证 ArchQueryAST(query_name=\"get_block_id\") lowering 为 arch.get_block_id。
# 测试目的: 锁定 emit_mlir 对最小 arch 查询入口的发射语义与结果类型。
# 使用示例: pytest -q test/dsl/test_ast_visitor.py -k test_emit_mlir_lowers_arch_get_block_id_query
# 对应功能实现文件路径: kernel_gen/dsl/emit_mlir.py
# 对应 spec 文件路径: spec/dsl/emit_mlir.md
# 对应测试文件路径: test/dsl/test_ast_visitor.py
def test_emit_mlir_lowers_arch_get_block_id_query() -> None:
    block = Block()
    ctx = EmitContext(builder=block, symbols={}, types={})

    result = emit_node_mlir(ArchQueryAST(query_name="get_block_id"), ctx)

    body_ops = list(block.ops)
    if len(body_ops) != 1:
        raise AssertionError("expected one emitted op for get_block_id query")
    if not isinstance(body_ops[0], ArchGetBlockIdOp):
        raise AssertionError("expected emitted op to be ArchGetBlockIdOp")
    if result.type != SymbolValueType.from_expr("block_id"):
        raise AssertionError('expected emitted result type to be !symbol.int<"block_id">')


# AST-001
# 创建者: 小李飞刀
# 最后一次更改: 金铲铲大作战
# 最近一次运行测试时间: 2026-03-22 15:38:56 +0800
# 最近一次运行成功时间: 2026-03-22 15:38:56 +0800
# 功能说明: 验证 parse_function 生成 FunctionAST 并保留位置信息。
# 测试目的: 验证 parse_function 生成 FunctionAST 并保留位置信息。
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
# 测试目的: 验证 parse_function 解析 Tensor/Scalar 参数注解。
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
# 最后一次更改: 朽木露琪亚
# 最近一次运行测试时间: 2026-03-25 16:05:00 +0800
# 最近一次运行成功时间: 2026-03-25 16:05:00 +0800
# 功能说明: 验证 parse_function 对非法注解抛出带诊断信息的错误。
# 测试目的: 验证 parse_function 对非法注解抛出带诊断信息的错误。
# 使用示例: pytest -q test/dsl/test_ast_visitor.py -k test_ast_parse_function_missing_annotation_reports_diagnostics
# 对应功能实现文件路径: kernel_gen/dsl/ast.py
# 对应 spec 文件路径: spec/dsl/ast.md
# 对应测试文件路径: test/dsl/test_ast_visitor.py
def test_ast_parse_function_missing_annotation_reports_diagnostics(monkeypatch: pytest.MonkeyPatch) -> None:
    def bad(x: int, y: "Tensor[f32, 2, 2]") -> "Tensor[f32, 2, 2]":
        return y

    monkeypatch.setattr(
        inspect,
        "getsource",
        lambda _obj: """
def bad(x, y: "Tensor[f32, 2, 2]") -> "Tensor[f32, 2, 2]":
    return y
""",
    )

    with pytest.raises(AstParseError) as exc_info:
        parse_function(bad)
    diagnostics = exc_info.value.diagnostics
    assert diagnostics
    assert diagnostics[0].message == "Missing annotation"


# MGEN-004
# 创建者: 小李飞刀
# 最后一次更改: 金铲铲大作战
# 最近一次运行测试时间: 2026-03-22 15:38:56 +0800
# 最近一次运行成功时间: 2026-03-22 15:38:56 +0800
# 功能说明: 验证 build_func_op 生成 func.func 并包含 nn dialect IR。
# 测试目的: 验证 build_func_op 生成 func.func 并包含 nn dialect IR。
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

    module = _module_from_func(add, _tensor_arg([2, 2]), _tensor_arg([2, 2]))
    assert isinstance(module, ModuleOp)
    assert any(isinstance(op, func.FuncOp) for op in module.ops)
    assert any(isinstance(op, NnAddOp) for op in module.walk())


# MGEN-005
# 创建者: 小李飞刀
# 最后一次更改: 金铲铲大作战
# 最近一次运行测试时间: 2026-03-22 15:38:56 +0800
# 最近一次运行成功时间: 2026-03-22 15:38:56 +0800
# 功能说明: 验证 func.func 打印输出包含 nn dialect 文本。
# 测试目的: 验证 func.func 打印输出包含 nn dialect 文本。
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

    module = _module_from_func(add, _tensor_arg([2, 2]), _tensor_arg([2, 2]))
    text = _print_module(module)
    assert "nn.add" in text
    assert "func.func" in text


# AST-001A
# 创建者: 朽木露琪亚
# 最后一次更改: 金铲铲大作战
# 最近一次运行测试时间: 2026-03-22 15:38:56 +0800
# 最近一次运行成功时间: 2026-03-22 15:38:56 +0800
# 功能说明: 验证 parse_function 提供独立 AST 解析入口。
# 测试目的: 验证 parse_function 提供独立 AST 解析入口。
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
# 最近一次运行测试时间: 2026-03-22 15:38:56 +0800
# 最近一次运行成功时间: 2026-03-22 15:38:56 +0800
# 功能说明: 验证 parse_function 不依赖 ast_visitor.visit_function 的反向导入。
# 测试目的: 验证 parse_function 不依赖 ast_visitor.visit_function 的反向导入。
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
# 最近一次运行测试时间: 2026-03-22 15:38:56 +0800
# 最近一次运行成功时间: 2026-03-22 15:38:56 +0800
# 功能说明: 验证 build_func_op 返回 func.func 并生成正确参数类型。
# 测试目的: 验证 build_func_op 返回 func.func 并生成正确参数类型。
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

    func_op = build_func_op(add, _tensor_arg([2, 2]), _tensor_arg([2, 2]), 4)
    assert isinstance(func_op, func.FuncOp)
    inputs = list(func_op.function_type.inputs)
    assert len(inputs) == 3
    assert inputs[2] == i32


# MGEN-001A
# 创建者: 朽木露琪亚
# 最后一次更改: 朽木露琪亚
# 最近一次运行测试时间: 2026-03-25 17:10:00 +0800
# 最近一次运行成功时间: 2026-03-25 17:10:00 +0800
# 功能说明: 验证 build_func_op 的输入签名只由 runtime_args 决定，不受解析环境中同名对象影响。
# 测试目的: 证明即使 globals 中提供同名 shadow symbol，成功路径的 func.func 签名仍以 runtime_args 为准。
# 使用示例: pytest -q test/dsl/test_ast_visitor.py -k test_build_func_op_signature_uses_runtime_args_not_parse_env
# 对应功能实现文件路径: kernel_gen/dsl/mlir_gen.py
# 对应 spec 文件路径: spec/dsl/mlir_gen.md
# 对应测试文件路径: test/dsl/test_ast_visitor.py
def test_build_func_op_signature_uses_runtime_args_not_parse_env() -> None:
    runtime_expr = SymbolDim("runtime")
    shadow_expr = SymbolDim("shadow")

    def only_symbol(expr: int) -> int:
        return expr

    func_op = build_func_op(
        only_symbol,
        runtime_expr,
        globals={"expr": shadow_expr, "__builtins__": __builtins__},
        builtins=object(),
    )
    inputs = list(func_op.function_type.inputs)
    outputs = list(func_op.function_type.outputs)
    assert inputs == [SymbolValueType.from_expr("runtime")]
    assert outputs == [SymbolValueType.from_expr("runtime")]


# MGEN-002
# 创建者: 朽木露琪亚
# 最后一次更改: 金铲铲大作战
# 最近一次运行测试时间: 2026-03-22 15:38:56 +0800
# 最近一次运行成功时间: 2026-03-22 15:38:56 +0800
# 功能说明: 验证 build_func_op_from_ast 保留 AST 参数顺序。
# 测试目的: 验证 build_func_op_from_ast 保留 AST 参数顺序。
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


# MGEN-002
# 创建者: 朽木露琪亚
# 最后一次更改: 朽木露琪亚
# 最近一次运行测试时间: 2026-03-25 16:45:00 +0800
# 最近一次运行成功时间: 2026-03-25 16:45:00 +0800
# 功能说明: 验证 build_func_op_from_ast 在提供 runtime_args 时按运行时参数语义构造签名。
# 测试目的: 证明 build_func_op_from_ast 的公开成功路径会用 runtime_args 驱动 symbol 标量签名 lowering。
# 使用示例: pytest -q test/dsl/test_ast_visitor.py -k test_build_func_op_from_ast_uses_runtime_args_for_symbol_signature
# 对应功能实现文件路径: kernel_gen/dsl/mlir_gen.py
# 对应 spec 文件路径: spec/dsl/mlir_gen.md
# 对应测试文件路径: test/dsl/test_ast_visitor.py
def test_build_func_op_from_ast_uses_runtime_args_for_symbol_signature() -> None:
    def only_symbol(expr: int) -> int:
        return expr

    func_ast = parse_function(only_symbol)
    func_op = build_func_op_from_ast(func_ast, runtime_args=[SymbolDim("expr")])
    inputs = list(func_op.function_type.inputs)
    outputs = list(func_op.function_type.outputs)
    assert inputs == [SymbolValueType.from_expr("expr")]
    assert outputs == [SymbolValueType.from_expr("expr")]


# MGEN-002A
# 创建者: 朽木露琪亚
# 最后一次更改: 朽木露琪亚
# 最近一次运行测试时间: 2026-03-25 16:45:00 +0800
# 最近一次运行成功时间: 2026-03-25 16:45:00 +0800
# 功能说明: 验证 build_func_op_from_ast 会把 config 透传给 visitor 与 lowering context。
# 测试目的: 证明 build_func_op_from_ast(..., config=...) 的公开成功路径不是空签名兼容，而是可观察地把配置传入 visitor/context。
# 使用示例: pytest -q test/dsl/test_ast_visitor.py -k test_build_func_op_from_ast_forwards_config_to_visitor_and_context
# 对应功能实现文件路径: kernel_gen/dsl/mlir_gen.py
# 对应 spec 文件路径: spec/dsl/mlir_gen.md
# 对应测试文件路径: test/dsl/test_ast_visitor.py
def test_build_func_op_from_ast_forwards_config_to_visitor_and_context(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, object] = {}

    class RecordingVisitor(ast_visitor_module.AstVisitor):
        def __init__(self: "RecordingVisitor", config: dict[str, object] | None = None) -> None:
            super().__init__(config=config)
            captured["visitor_config"] = dict(self.config)

        def visit_function(self: "RecordingVisitor", func_ast: FunctionAST, ctx: EmitContext) -> object:
            captured["ctx_config"] = dict(ctx.config)
            return super().visit_function(func_ast, ctx)

    def identity(x: "Tensor[f32, 2, 2]") -> "Tensor[f32, 2, 2]":
        return x

    monkeypatch.setattr(ast_visitor_module, "AstVisitor", RecordingVisitor)
    func_ast = parse_function(identity)
    config: dict[str, object] = {"loop_vars": {"i": "outer"}}
    func_op = build_func_op_from_ast(func_ast, config=config)

    assert isinstance(func_op, func.FuncOp)
    assert captured["visitor_config"] == config
    assert captured["ctx_config"] == config


# MGEN-003
# 创建者: 金铲铲大作战
# 最后一次更改: 金铲铲大作战
# 最近一次运行测试时间: 2026-03-22 14:59:58 +0800
# 最近一次运行成功时间: 2026-03-22 14:59:58 +0800
# 功能说明: 验证 build_func_op 返回类型与 AST 返回注解一致。
# 测试目的: 验证 build_func_op 返回类型与 AST 返回注解一致。
# 使用示例: pytest -q test/dsl/test_ast_visitor.py -k test_build_func_op_return_type_matches_annotation
# 对应功能实现文件路径: kernel_gen/dsl/mlir_gen.py
# 对应 spec 文件路径: spec/dsl/mlir_gen.md
# 对应测试文件路径: test/dsl/test_ast_visitor.py
def test_build_func_op_return_type_matches_annotation() -> None:
    def add(x: "Tensor[f32, 2, 2]") -> "Tensor[f32, 2, 2]":
        return x

    func_ast = parse_function(add)
    func_op = build_func_op(add, _tensor_arg([2, 2]))
    outputs = list(func_op.function_type.outputs)
    assert outputs
    expected = _memory_to_nn_type(func_ast.outputs[0].memory)
    assert outputs[0] == expected


# MGEN-003
# 创建者: 小李飞刀
# 最后一次更改: 小李飞刀
# 最近一次运行测试时间: 2026-03-23 10:30:00 +0800
# 最近一次运行成功时间: 2026-03-23 10:30:00 +0800
# 功能说明: 覆盖 mlir_gen 的符号标量函数与签名构造分支。
# 测试目的: 验证符号标量函数识别与 runtime arg 到 symbol expr 的映射。
# 使用示例: pytest -q test/dsl/test_ast_visitor.py -k test_mlir_gen_symbol_scalar_helpers
# 对应功能实现文件路径: kernel_gen/dsl/mlir_gen.py
# 对应 spec 文件路径: spec/dsl/mlir_gen.md
# 对应测试文件路径: test/dsl/test_ast_visitor.py
def test_mlir_gen_symbol_scalar_helpers() -> None:
    func_ast = FunctionAST(
        name="only_symbol",
        inputs=[ScalarArgAST("n", int)],
        outputs=[ScalarArgAST("n", int)],
        body=BlockAST([]),
    )
    assert _is_symbol_scalar_function(func_ast)
    assert not _is_symbol_scalar_function(FunctionAST("no_inputs", [], [], BlockAST([])))

    assert _symbol_expr_from_runtime_arg(SymbolDim("S")) == "S"
    assert _symbol_expr_from_runtime_arg(4) == "4"
    assert _symbol_expr_from_runtime_arg("bad") is None

    arg_types, type_map = _build_signature_types(func_ast, runtime_args=[SymbolDim("S")])
    assert len(arg_types) == 1
    assert isinstance(arg_types[0], SymbolValueType)
    assert type_map[_expr_key(func_ast.inputs[0])] == arg_types[0]


# MGEN-002B
# 创建者: 小李飞刀
# 最后一次更改: 朽木露琪亚
# 最近一次运行测试时间: 2026-03-25 16:25:00 +0800
# 最近一次运行成功时间: 2026-03-25 16:25:00 +0800
# 功能说明: 覆盖 build_func_op_from_ast 签名构造与输入校验错误分支。
# 测试目的: 验证 build_func_op_from_ast 对空函数体、runtime_args 长度不匹配、未支持的输入类型与缺少 tensor 输入等约束都会报错。
# 使用示例: pytest -q test/dsl/test_ast_visitor.py -k test_mlir_gen_signature_validation_errors
# 对应功能实现文件路径: kernel_gen/dsl/mlir_gen.py
# 对应 spec 文件路径: spec/dsl/mlir_gen.md
# 对应测试文件路径: test/dsl/test_ast_visitor.py
def test_mlir_gen_signature_validation_errors() -> None:
    with pytest.raises(AstVisitorError, match="Function body is empty"):
        build_func_op_from_ast(FunctionAST("empty", [], [], BlockAST([])))

    single_tensor = FunctionAST(
        "one",
        [TensorAST("x", Memory([2, 2], NumericType.Float32))],
        [],
        BlockAST([]),
    )
    with pytest.raises(AstVisitorError, match="runtime_args must align"):
        build_func_op_from_ast(single_tensor, runtime_args=[])

    with pytest.raises(AstVisitorError, match="Unsupported scalar argument type"):
        build_func_op_from_ast(FunctionAST("bad", [ScalarArgAST("n", float)], [], BlockAST([])))

    with pytest.raises(AstVisitorError, match="Unsupported input type"):
        build_func_op_from_ast(FunctionAST("bad", [VarAST("x")], [], BlockAST([])))

    outputs_tensor = FunctionAST(
        "no_tensor",
        [ScalarArgAST("n", int)],
        [TensorAST("out", Memory([2], NumericType.Float32))],
        BlockAST([]),
    )
    with pytest.raises(AstVisitorError, match="At least one tensor input is required"):
        build_func_op_from_ast(outputs_tensor)


# MGEN-025
# 创建者: 朽木露琪亚
# 最后一次更改: 朽木露琪亚
# 最近一次运行测试时间: 2026-03-25 10:18:40 +0800
# 最近一次运行成功时间: 2026-03-25 10:18:40 +0800
# 功能说明: 验证 build_func_op 支持可静态归一化的 JoinedStr Tensor 注解。
# 测试目的: 验证 f"Tensor[...]" 形式的输入/输出注解可被归一化并成功参与 lowering。
# 使用示例: pytest -q test/dsl/test_ast_visitor.py -k test_build_func_op_accepts_joinedstr_tensor_annotation
# 对应功能实现文件路径: kernel_gen/dsl/ast.py
# 对应 spec 文件路径: spec/dsl/mlir_gen.md
# 对应测试文件路径: test/dsl/test_ast_visitor.py
def test_build_func_op_accepts_joinedstr_tensor_annotation(monkeypatch: pytest.MonkeyPatch) -> None:
    rows = 2
    cols = 3

    def identity(src: f"Tensor[f32, {ROWS}, {COLS}]") -> f"Tensor[f32, {ROWS}, {COLS}]":
        return src

    monkeypatch.setitem(identity.__globals__, "ROWS", rows)
    monkeypatch.setitem(identity.__globals__, "COLS", cols)
    func_op = build_func_op(identity, _tensor_arg([rows, cols]))
    assert isinstance(func_op, func.FuncOp)
    assert list(func_op.function_type.inputs) == [_memory_to_nn_type(Memory([rows, cols], NumericType.Float32))]
    assert list(func_op.function_type.outputs) == [_memory_to_nn_type(Memory([rows, cols], NumericType.Float32))]


# MGEN-025
# 创建者: 朽木露琪亚
# 最后一次更改: 朽木露琪亚
# 最近一次运行测试时间: 2026-03-25 10:18:40 +0800
# 最近一次运行成功时间: 2026-03-25 10:18:40 +0800
# 功能说明: 验证 build_func_op 会拒绝无法归一化为合法 Tensor 语法的 JoinedStr 注解。
# 测试目的: 验证 JoinedStr 注解归一化后缺少维度时会抛出带诊断的错误。
# 使用示例: pytest -q test/dsl/test_ast_visitor.py -k test_build_func_op_rejects_invalid_joinedstr_tensor_annotation
# 对应功能实现文件路径: kernel_gen/dsl/ast.py
# 对应 spec 文件路径: spec/dsl/mlir_gen.md
# 对应测试文件路径: test/dsl/test_ast_visitor.py
def test_build_func_op_rejects_invalid_joinedstr_tensor_annotation(monkeypatch: pytest.MonkeyPatch) -> None:
    bad_spec = "Tensor[f32]"

    def invalid(src: f"{BAD_SPEC}") -> f"{BAD_SPEC}":
        return src

    monkeypatch.setitem(invalid.__globals__, "BAD_SPEC", bad_spec)
    with pytest.raises(AstVisitorError, match="Tensor annotation missing dimensions"):
        build_func_op(invalid, _tensor_arg([2]))


# MGEN-026
# 创建者: 朽木露琪亚
# 最后一次更改: 朽木露琪亚
# 最近一次运行测试时间: 2026-03-25 10:04:04 +0800
# 最近一次运行成功时间: 2026-03-25 10:04:04 +0800
# 功能说明: 验证 build_func_op 在 DMA helper 场景下按公开语义生成对应 memory 结果。
# 测试目的: 验证 alloc/copy/cast/view/reshape/flatten 六类 helper 在 build_func_op 链路中都能成功 lowering。
# 使用示例: pytest -q test/dsl/test_ast_visitor.py -k test_build_func_op_supports_dma_helper_calls
# 对应功能实现文件路径: kernel_gen/dsl/mlir_gen.py
# 对应 spec 文件路径: spec/dsl/mlir_gen.md
# 对应测试文件路径: test/dsl/test_ast_visitor.py
def test_build_func_op_supports_dma_helper_calls() -> None:
    from kernel_gen.operation.dma import alloc, cast, copy, flatten, reshape, view

    source = Memory([4, 4], NumericType.Float32, space=MemorySpace.GM)

    def alloc_kernel() -> "Tensor[f32, 2, 3]":
        return alloc([2, 3], NumericType.Float32, MemorySpace.SM)

    def copy_kernel(src: "Tensor[f32, 4, 4]") -> "Tensor[f32, 4, 4]":
        return copy(src, MemorySpace.SM)

    def cast_kernel(src: "Tensor[f32, 4, 4]") -> "Tensor[f16, 4, 4]":
        return cast(src, NumericType.Float16, memoryspace=MemorySpace.SM)

    def view_kernel(src: "Tensor[f32, 4, 4]") -> "Tensor[f32, 2, 2]":
        return view(src, [1, 1], [2, 2], [1, 1])

    def reshape_kernel(src: "Tensor[f32, 4, 4]") -> "Tensor[f32, 2, 8]":
        return reshape(src, [2, 8])

    def flatten_kernel(src: "Tensor[f32, 4, 4]") -> "Tensor[f32, 16]":
        return flatten(src)

    alloc_func = build_func_op(alloc_kernel)
    copy_func = build_func_op(copy_kernel, source)
    cast_func = build_func_op(cast_kernel, source)
    view_func = build_func_op(view_kernel, source)
    reshape_func = build_func_op(reshape_kernel, source)
    flatten_func = build_func_op(flatten_kernel, source)

    assert any(isinstance(op, DmaAllocOp) for op in alloc_func.body.block.ops)
    assert any(isinstance(op, DmaCopyOp) for op in copy_func.body.block.ops)
    assert any(isinstance(op, DmaCastOp) for op in cast_func.body.block.ops)
    assert any(isinstance(op, DmaViewOp) for op in view_func.body.block.ops)
    assert any(isinstance(op, DmaReshapeOp) for op in reshape_func.body.block.ops)
    assert any(isinstance(op, DmaReshapeOp) for op in flatten_func.body.block.ops)


# MGEN-026A
# 创建者: 小李飞刀
# 最后一次更改: 小李飞刀
# 最近一次运行测试时间: 2026-03-25 22:17:59 +0800
# 最近一次运行成功时间: 2026-03-25 22:17:59 +0800
# 功能说明: 验证 build_func_op 支持仅依赖标量 runtime_args 的 DMA alloc-only kernel。
# 测试目的: 验证 alloc-only kernel 会将 runtime shape 参数 lowering 为 symbol.int 输入，并保持 dma.alloc 结果类型与返回注解一致。
# 使用示例: pytest -q test/dsl/test_ast_visitor.py -k test_build_func_op_supports_dma_alloc_helper_with_runtime_shape_args
# 对应功能实现文件路径: kernel_gen/dsl/mlir_gen.py
# 对应 spec 文件路径: spec/dsl/mlir_gen.md
# 对应测试文件路径: test/dsl/test_ast_visitor.py
def test_build_func_op_supports_dma_alloc_helper_with_runtime_shape_args(monkeypatch: pytest.MonkeyPatch) -> None:
    from kernel_gen.operation.dma import alloc

    rows = 2
    cols = 3
    source = """
def alloc_kernel(rank1, rank2) -> f"Tensor[f32, {ALLOC_ROWS}, {ALLOC_COLS}]":
    return alloc([rank1, rank2], NumericType.Float32, MemorySpace.SM)
"""
    namespace = {
        "alloc": alloc,
        "NumericType": NumericType,
        "MemorySpace": MemorySpace,
        "ALLOC_ROWS": rows,
        "ALLOC_COLS": cols,
    }
    exec(source, namespace)
    alloc_kernel = namespace["alloc_kernel"]

    def fake_getsource(_obj: object) -> str:
        return source

    monkeypatch.setattr(inspect, "getsource", fake_getsource)

    func_op = build_func_op(alloc_kernel, rows, cols)
    alloc_ops = [op for op in func_op.body.block.ops if isinstance(op, DmaAllocOp)]

    assert list(func_op.function_type.inputs) == [
        SymbolValueType.from_expr(str(rows)),
        SymbolValueType.from_expr(str(cols)),
    ]
    assert len(alloc_ops) == 1
    assert list(alloc_ops[0].dynamic_shape) == list(func_op.body.block.args)
    assert alloc_ops[0].result.type.space == NnMemorySpaceAttr.from_name("shared")
    assert [attr.data for attr in alloc_ops[0].result.type.shape.data] == [rows, cols]
    assert list(func_op.function_type.outputs) == [alloc_ops[0].result.type]


# MGEN-026A
# 创建者: 小李飞刀
# 最后一次更改: 小李飞刀
# 最近一次运行测试时间: 2026-03-25 22:17:59 +0800
# 最近一次运行成功时间: 2026-03-25 22:17:59 +0800
# 功能说明: 覆盖 alloc-only runtime_args 无法映射为 !symbol.int 时的错误分支。
# 测试目的: 验证 alloc-only kernel 遇到非法 runtime_args 类型会报错并与 MGEN-002B 保持一致。
# 使用示例: pytest -q test/dsl/test_ast_visitor.py -k test_build_func_op_rejects_dma_alloc_helper_with_invalid_runtime_shape_args
# 对应功能实现文件路径: kernel_gen/dsl/mlir_gen.py
# 对应 spec 文件路径: spec/dsl/mlir_gen.md
# 对应测试文件路径: test/dsl/test_ast_visitor.py
def test_build_func_op_rejects_dma_alloc_helper_with_invalid_runtime_shape_args(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from kernel_gen.operation.dma import alloc

    rows = 2
    cols = 3
    source = """
def alloc_kernel(rank1: int, rank2: int) -> f"Tensor[f32, {ALLOC_ROWS}, {ALLOC_COLS}]":
    return alloc([rank1, rank2], NumericType.Float32, MemorySpace.SM)
"""
    namespace = {
        "alloc": alloc,
        "NumericType": NumericType,
        "MemorySpace": MemorySpace,
        "ALLOC_ROWS": rows,
        "ALLOC_COLS": cols,
    }
    exec(source, namespace)
    alloc_kernel = namespace["alloc_kernel"]

    def fake_getsource(_obj: object) -> str:
        return source

    monkeypatch.setattr(inspect, "getsource", fake_getsource)

    with pytest.raises(AstVisitorError, match="Unsupported scalar argument type"):
        build_func_op(alloc_kernel, 1.5, cols)


# MGEN-026
# 创建者: 朽木露琪亚
# 最后一次更改: 朽木露琪亚
# 最近一次运行测试时间: 2026-03-25 10:04:04 +0800
# 最近一次运行成功时间: 2026-03-25 10:04:04 +0800
# 功能说明: 验证 build_func_op 在 free 语句场景下不会生成额外返回值。
# 测试目的: 验证 free 作为无返回值语句参与 lowering，函数体最终只保留 func.return。
# 使用示例: pytest -q test/dsl/test_ast_visitor.py -k test_build_func_op_supports_dma_free_statement
# 对应功能实现文件路径: kernel_gen/dsl/mlir_gen.py
# 对应 spec 文件路径: spec/dsl/mlir_gen.md
# 对应测试文件路径: test/dsl/test_ast_visitor.py
def test_build_func_op_supports_dma_free_statement() -> None:
    from kernel_gen.operation.dma import free

    source = Memory([4, 4], NumericType.Float32, space=MemorySpace.GM)

    def free_kernel(src: "Tensor[f32, 4, 4]"):
        free(src)

    func_op = build_func_op(free_kernel, source)
    assert isinstance(func_op, func.FuncOp)
    assert list(func_op.function_type.outputs) == []
    assert [type(op) for op in func_op.body.block.ops] == [func.ReturnOp]


# MGEN-026
# 创建者: 朽木露琪亚
# 最后一次更改: 朽木露琪亚
# 最近一次运行测试时间: 2026-03-25 10:18:40 +0800
# 最近一次运行成功时间: 2026-03-25 10:18:40 +0800
# 功能说明: 验证 build_func_op 在 load helper 场景下生成 dma.load。
# 测试目的: 验证 load(...) 在 build_func_op 链路中被直接识别并 lowering 为 DmaLoadOp。
# 使用示例: pytest -q test/dsl/test_ast_visitor.py -k test_build_func_op_supports_dma_load_helper
# 对应功能实现文件路径: kernel_gen/dsl/mlir_gen.py
# 对应 spec 文件路径: spec/dsl/mlir_gen.md
# 对应测试文件路径: test/dsl/test_ast_visitor.py
def test_build_func_op_supports_dma_load_helper() -> None:
    from kernel_gen.operation.dma import load

    source = Memory([4, 4], NumericType.Float32, space=MemorySpace.GM)

    def load_kernel(src: "Tensor[f32, 4, 4]") -> "Tensor[f32, 2, 2]":
        return load(src, [1, 1], [2, 2], [1, 1], MemorySpace.SM)

    func_op = build_func_op(load_kernel, source)
    load_ops = [op for op in func_op.body.block.ops if isinstance(op, DmaLoadOp)]
    assert isinstance(func_op, func.FuncOp)
    assert len(load_ops) == 1


# MGEN-026
# 创建者: 朽木露琪亚
# 最后一次更改: 朽木露琪亚
# 最近一次运行测试时间: 2026-03-25 10:18:40 +0800
# 最近一次运行成功时间: 2026-03-25 10:18:40 +0800
# 功能说明: 验证 build_func_op 在 store helper 场景下生成 dma.store。
# 测试目的: 验证 store(...) 在 build_func_op 链路中被直接识别并 lowering 为 DmaStoreOp。
# 使用示例: pytest -q test/dsl/test_ast_visitor.py -k test_build_func_op_supports_dma_store_helper
# 对应功能实现文件路径: kernel_gen/dsl/mlir_gen.py
# 对应 spec 文件路径: spec/dsl/mlir_gen.md
# 对应测试文件路径: test/dsl/test_ast_visitor.py
def test_build_func_op_supports_dma_store_helper() -> None:
    from kernel_gen.operation.dma import store

    source = Memory([2, 2], NumericType.Float32, space=MemorySpace.SM)
    target = Memory([4, 4], NumericType.Float32, space=MemorySpace.GM)

    def store_kernel(tile: "Tensor[f32, 2, 2]", dst: "Tensor[f32, 4, 4]"):
        store(tile, dst, [1, 1], [2, 2], [1, 1])

    func_op = build_func_op(store_kernel, source, target)
    store_ops = [op for op in func_op.body.block.ops if isinstance(op, DmaStoreOp)]
    assert isinstance(func_op, func.FuncOp)
    assert len(store_ops) == 1


# MGEN-026
# 创建者: 朽木露琪亚
# 最后一次更改: 朽木露琪亚
# 最近一次运行测试时间: 2026-03-25 10:18:40 +0800
# 最近一次运行成功时间: 2026-03-25 10:18:40 +0800
# 功能说明: 验证 build_func_op 在 slice helper 场景下生成 dma.slice。
# 测试目的: 验证 slice(...) 在 build_func_op 链路中被直接识别并 lowering 为 DmaSliceOp。
# 使用示例: pytest -q test/dsl/test_ast_visitor.py -k test_build_func_op_supports_dma_slice_helper
# 对应功能实现文件路径: kernel_gen/dsl/mlir_gen.py
# 对应 spec 文件路径: spec/dsl/mlir_gen.md
# 对应测试文件路径: test/dsl/test_ast_visitor.py
def test_build_func_op_supports_dma_slice_helper() -> None:
    from kernel_gen.operation.dma import slice

    source = Memory([4, 4], NumericType.Float32, space=MemorySpace.GM)

    def slice_kernel(src: "Tensor[f32, 4, 4]") -> "Tensor[f32, 2, 2]":
        return slice(src, [1, 1], [2, 2], [1, 1], MemorySpace.LM)

    func_op = build_func_op(slice_kernel, source)
    slice_ops = [op for op in func_op.body.block.ops if isinstance(op, DmaSliceOp)]
    assert isinstance(func_op, func.FuncOp)
    assert len(slice_ops) == 1


# MGEN-026
# 创建者: 朽木露琪亚
# 最后一次更改: 朽木露琪亚
# 最近一次运行测试时间: 2026-03-25 10:18:40 +0800
# 最近一次运行成功时间: 2026-03-25 10:18:40 +0800
# 功能说明: 验证 build_func_op 在 deslice helper 场景下生成 dma.deslice。
# 测试目的: 验证 deslice(...) 在 build_func_op 链路中被直接识别并 lowering 为 DmaDesliceOp。
# 使用示例: pytest -q test/dsl/test_ast_visitor.py -k test_build_func_op_supports_dma_deslice_helper
# 对应功能实现文件路径: kernel_gen/dsl/mlir_gen.py
# 对应 spec 文件路径: spec/dsl/mlir_gen.md
# 对应测试文件路径: test/dsl/test_ast_visitor.py
def test_build_func_op_supports_dma_deslice_helper() -> None:
    from kernel_gen.operation.dma import deslice

    source = Memory([2, 2], NumericType.Float32, space=MemorySpace.LM)
    target = Memory([4, 4], NumericType.Float32, space=MemorySpace.GM)

    def deslice_kernel(tile: "Tensor[f32, 2, 2]", dst: "Tensor[f32, 4, 4]"):
        deslice(tile, dst, [1, 1], [2, 2], [1, 1])

    func_op = build_func_op(deslice_kernel, source, target)
    deslice_ops = [op for op in func_op.body.block.ops if isinstance(op, DmaDesliceOp)]
    assert isinstance(func_op, func.FuncOp)
    assert len(deslice_ops) == 1


# MGEN-007
# 创建者: 小李飞刀
# 最后一次更改: 朽木露琪亚
# 最近一次运行测试时间: 2026-03-25 16:05:00 +0800
# 最近一次运行成功时间: 2026-03-25 16:05:00 +0800
# 功能说明: 覆盖解析失败时的错误包装路径。
# 测试目的: 验证 _parse_function_with_env 将 _ParseFailure 转换为 AstParseError。
# 使用示例: pytest -q test/dsl/test_ast_visitor.py -k test_mlir_gen_parse_failure_wrapped
# 对应功能实现文件路径: kernel_gen/dsl/mlir_gen.py
# 对应 spec 文件路径: spec/dsl/mlir_gen.md
# 对应测试文件路径: test/dsl/test_ast_visitor.py
def test_mlir_gen_parse_failure_wrapped(monkeypatch: pytest.MonkeyPatch) -> None:
    def fn(x: object) -> object:
        return x

    def _broken_parse(*args: object, **kwargs: object) -> object:
        raise _ParseFailure("broken", location=SourceLocation(1, 2))

    monkeypatch.setattr(mlir_gen_module, "_parse_function_impl", _broken_parse)
    with pytest.raises(AstParseError, match="broken"):
        _parse_function_with_env(fn, globals_table={}, builtins_table={}, runtime_table={}, config=None)


# MGEN-007
# 创建者: 小李飞刀
# 最后一次更改: 小李飞刀
# 最近一次运行测试时间: 2026-03-23 10:30:00 +0800
# 最近一次运行成功时间: 2026-03-23 10:30:00 +0800
# 功能说明: 覆盖返回类型校验的错误分支。
# 测试目的: 验证多返回、非法返回注解与不匹配类型时报错。
# 使用示例: pytest -q test/dsl/test_ast_visitor.py -k test_mlir_gen_validate_return_type_errors
# 对应功能实现文件路径: kernel_gen/dsl/mlir_gen.py
# 对应 spec 文件路径: spec/dsl/mlir_gen.md
# 对应测试文件路径: test/dsl/test_ast_visitor.py
def test_mlir_gen_validate_return_type_errors() -> None:
    memory = Memory([2, 2], NumericType.Float32)
    tensor_out = TensorAST("out", memory)
    scalar_out = ScalarArgAST("n", int)

    func_multi = FunctionAST("multi", [tensor_out], [tensor_out, tensor_out], BlockAST([]))
    with pytest.raises(_LoweringError, match="Only single return value is supported"):
        _validate_return_type(func_multi, _memory_to_nn_type(memory))

    func_scalar_bad = FunctionAST("bad", [scalar_out], [ScalarArgAST("f", float)], BlockAST([]))
    with pytest.raises(_LoweringError, match="Unsupported scalar return type"):
        _validate_return_type(func_scalar_bad, i32)

    func_unknown = FunctionAST("bad", [scalar_out], [VarAST("x")], BlockAST([]))
    with pytest.raises(_LoweringError, match="Unsupported return annotation type"):
        _validate_return_type(func_unknown, i32)

    func_mismatch = FunctionAST("bad", [tensor_out], [tensor_out], BlockAST([]))
    with pytest.raises(_LoweringError, match="Return type does not match annotation"):
        _validate_return_type(func_mismatch, i32)

    func_symbol = FunctionAST("sym", [scalar_out], [scalar_out], BlockAST([]))
    with pytest.raises(_LoweringError, match="Return type does not match annotation"):
        _validate_return_type(func_symbol, i32)


# EMIT-001
# 创建者: 朽木露琪亚
# 最后一次更改: 金铲铲大作战
# 最近一次运行测试时间: 2026-03-22 14:59:58 +0800
# 最近一次运行成功时间: 2026-03-22 14:59:58 +0800
# 功能说明: 验证二元表达式节点生成对应 op/value 并复用缓存。
# 测试目的: 验证二元表达式节点生成对应 op/value 并复用缓存。
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
# 最近一次运行测试时间: 2026-03-22 14:59:58 +0800
# 最近一次运行成功时间: 2026-03-22 14:59:58 +0800
# 功能说明: 验证 emit_mlir 可通过符号表直接解析 TensorAST 输入。
# 测试目的: 验证 emit_mlir 可通过符号表直接解析 TensorAST 输入。
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
# 最近一次运行测试时间: 2026-03-22 14:59:58 +0800
# 最近一次运行成功时间: 2026-03-22 14:59:58 +0800
# 功能说明: 验证比较表达式节点生成对应 op/value。
# 测试目的: 验证比较表达式节点生成对应 op/value。
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
# 最近一次运行测试时间: 2026-03-22 14:59:58 +0800
# 最近一次运行成功时间: 2026-03-22 14:59:58 +0800
# 功能说明: 验证不支持节点抛出错误并携带位置信息。
# 测试目的: 验证不支持节点抛出错误并携带位置信息。
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
# 最近一次运行测试时间: 2026-03-22 14:59:58 +0800
# 最近一次运行成功时间: 2026-03-22 14:59:58 +0800
# 功能说明: 验证 AstVisitor 顺序访问 block 并生成多语句 SSA。
# 测试目的: 验证 AstVisitor 顺序访问 block 并生成多语句 SSA。
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
# 最近一次运行测试时间: 2026-03-22 14:59:58 +0800
# 最近一次运行成功时间: 2026-03-22 14:59:58 +0800
# 功能说明: 验证同一表达式节点复用同一 value。
# 测试目的: 验证同一表达式节点复用同一 value。
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
# 测试目的: 验证 parse_function 可解析标准 Tensor 注解。
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
# 测试目的: 验证 ScalarArgAST 会 lowering 为 func.func 标量参数。
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

    func_op = build_func_op(add, _tensor_arg([2, 2]), _tensor_arg([2, 2]), 4)
    inputs = list(func_op.function_type.inputs)
    assert len(inputs) == 3
    assert isinstance(inputs[0], NnMemoryType)
    assert isinstance(inputs[1], NnMemoryType)
    assert inputs[2] == i32


# MGEN-016 / MGEN-017
# 创建者: OpenAI
# 最后一次更改: 朽木露琪亚
# 最近一次运行测试时间: 2026-03-25 16:05:00 +0800
# 最近一次运行成功时间: 2026-03-25 16:05:00 +0800
# 功能说明: 验证纯 symbol 标量函数的 func.func 输入与返回保持为 !symbol.int<"expr">。
# 测试目的: 验证纯 symbol 标量函数不会退回 builtin 整数类型。
# 使用示例: pytest -q test/dsl/test_ast_visitor.py -k test_symbol_scalar_function_uses_symbol_value_type_signature
# 对应功能实现文件路径: kernel_gen/dsl/mlir_gen.py
# 对应 spec 文件路径: spec/dsl/mlir_gen.md
# 对应测试文件路径: test/dsl/test_ast_visitor.py
def test_symbol_scalar_function_uses_symbol_value_type_signature() -> None:
    expr = SymbolDim("expr")

    def only_symbol(expr: int) -> int:
        return expr

    func_op = build_func_op(only_symbol, expr, globals={"expr": expr, "__builtins__": __builtins__})
    inputs = list(func_op.function_type.inputs)
    outputs = list(func_op.function_type.outputs)
    assert inputs == [SymbolValueType.from_expr("expr")]
    assert outputs == [SymbolValueType.from_expr("expr")]


# MGEN-018 / MGEN-021 / MGEN-022 / MGEN-023 / MGEN-024
# 创建者: OpenAI
# 最后一次更改: 金铲铲大作战
# 最近一次运行测试时间: 2026-03-25 04:33:06 +0800
# 最近一次运行成功时间: 2026-03-25 04:33:06 +0800
# 功能说明: 验证纯 symbol 标量算术 lowering 为对应的 symbol dialect op。
# 测试目的: 验证纯 symbol 标量加减乘除在静态、动态与混合输入下不会退回 nn dialect 或 builtin 整数算术。
# 使用示例: pytest -q test/dsl/test_ast_visitor.py -k test_symbol_scalar_function_lowers_symbol_binary_ops
# 对应功能实现文件路径: kernel_gen/dsl/mlir_gen.py
# 对应 spec 文件路径: spec/dsl/mlir_gen.md
# 对应测试文件路径: test/dsl/test_ast_visitor.py
@pytest.mark.parametrize("style", ["python", "nn"])
@pytest.mark.parametrize(
    ("name", "operator_token", "builder", "runtime_args"),
    [
        ("add", "symbol.add", SymbolAddOp, (4, 5)),
        ("add", "symbol.add", SymbolAddOp, (SymbolDim("s"), SymbolDim("t"))),
        ("add", "symbol.add", SymbolAddOp, (4, SymbolDim("t"))),
        ("add", "symbol.add", SymbolAddOp, (SymbolDim("s"), 5)),
        ("sub", "symbol.sub", SymbolSubOp, (9, 4)),
        ("sub", "symbol.sub", SymbolSubOp, (SymbolDim("s"), SymbolDim("t"))),
        ("sub", "symbol.sub", SymbolSubOp, (9, SymbolDim("t"))),
        ("sub", "symbol.sub", SymbolSubOp, (SymbolDim("s"), 4)),
        ("mul", "symbol.mul", SymbolMulOp, (3, 4)),
        ("mul", "symbol.mul", SymbolMulOp, (SymbolDim("s"), SymbolDim("t"))),
        ("mul", "symbol.mul", SymbolMulOp, (3, SymbolDim("t"))),
        ("mul", "symbol.mul", SymbolMulOp, (SymbolDim("s"), 4)),
        ("truediv", "symbol.div", SymbolDivOp, (6, 3)),
        ("truediv", "symbol.div", SymbolDivOp, (SymbolDim("s"), SymbolDim("t"))),
        ("truediv", "symbol.div", SymbolDivOp, (6, SymbolDim("t"))),
        ("truediv", "symbol.div", SymbolDivOp, (SymbolDim("s"), 3)),
        ("floordiv", "symbol.floordiv", SymbolFloorDivOp, (7, 3)),
        ("floordiv", "symbol.floordiv", SymbolFloorDivOp, (SymbolDim("s"), SymbolDim("t"))),
        ("floordiv", "symbol.floordiv", SymbolFloorDivOp, (7, SymbolDim("t"))),
        ("floordiv", "symbol.floordiv", SymbolFloorDivOp, (SymbolDim("s"), 3)),
    ],
)
def test_symbol_scalar_function_lowers_symbol_binary_ops(
    style: str,
    name: str,
    operator_token: str,
    builder: type[object],
    runtime_args: tuple[object, object],
) -> None:
    def normalize_runtime_value(value: object) -> int | str:
        if isinstance(value, SymbolDim):
            return value.get_value()
        if isinstance(value, float) and value.is_integer():
            return int(value)
        if isinstance(value, (int, str)):
            return value
        raise TypeError(f"Unsupported runtime result type: {type(value)!r}")

    def add(lhs: int, rhs: int) -> int:
        return lhs + rhs

    def sub(lhs: int, rhs: int) -> int:
        return lhs - rhs

    def mul(lhs: int, rhs: int) -> int:
        return lhs * rhs

    def truediv(lhs: int, rhs: int) -> int:
        return lhs / rhs

    def floordiv(lhs: int, rhs: int) -> int:
        return lhs // rhs

    def add_nn(lhs: int, rhs: int) -> int:
        return nn.add(lhs, rhs)

    def sub_nn(lhs: int, rhs: int) -> int:
        return nn.sub(lhs, rhs)

    def mul_nn(lhs: int, rhs: int) -> int:
        return nn.mul(lhs, rhs)

    def truediv_nn(lhs: int, rhs: int) -> int:
        return nn.truediv(lhs, rhs)

    def floordiv_nn(lhs: int, rhs: int) -> int:
        return nn.floordiv(lhs, rhs)

    functions: dict[tuple[str, str], object] = {
        ("python", "add"): add,
        ("python", "sub"): sub,
        ("python", "mul"): mul,
        ("python", "truediv"): truediv,
        ("python", "floordiv"): floordiv,
        ("nn", "add"): add_nn,
        ("nn", "sub"): sub_nn,
        ("nn", "mul"): mul_nn,
        ("nn", "truediv"): truediv_nn,
        ("nn", "floordiv"): floordiv_nn,
    }

    func_op = build_func_op(functions[(style, name)], *runtime_args)
    runtime_result = normalize_runtime_value(functions[(style, name)](*runtime_args))
    expected_result = SymbolValueType.from_expr(str(runtime_result))
    arg_types = [arg.type for arg in func_op.args]
    expected_arg_types = [
        SymbolValueType.from_expr(str(value.get_value()) if isinstance(value, SymbolDim) else str(value))
        for value in runtime_args
    ]
    assert arg_types == expected_arg_types
    ops = list(func_op.body.blocks[0].ops)
    symbol_ops = [op for op in ops if isinstance(op, builder)]
    return_ops = [op for op in ops if isinstance(op, func.ReturnOp)]
    assert len(symbol_ops) == 1
    assert len(return_ops) == 1
    assert symbol_ops[0].result.type == expected_result
    assert symbol_ops[0].result.type.get_value() == runtime_result
    assert len(return_ops[0].arguments) == 1
    assert return_ops[0].arguments[0].type == expected_result
    assert return_ops[0].arguments[0].type.get_value() == runtime_result
    assert list(func_op.function_type.outputs) == [expected_result]
    assert func_op.function_type.outputs.data[0].get_value() == runtime_result
    assert operator_token in _print_module(ModuleOp([func_op]))


# MGEN-020
# 创建者: 朽木露琪亚
# 最后一次更改: 朽木露琪亚
# 最近一次运行测试时间: 2026-03-25 16:05:00 +0800
# 最近一次运行成功时间: 2026-03-25 16:05:00 +0800
# 功能说明: 验证 Python int 运行时实参会 lowering 为携带具体整数值的 SymbolValueType。
# 测试目的: 验证 build_func_op(add, lhs, rhs) 在整型标量链路中生成 symbol.add，且赋值后 return 场景保持公开类型与结果口径稳定。
# 使用示例: pytest -q test/dsl/test_ast_visitor.py -k test_build_func_op_add_scalar_runtime_ints_lower_to_symbol_value_type
# 对应功能实现文件路径: kernel_gen/dsl/mlir_gen.py
# 对应 spec 文件路径: spec/dsl/mlir_gen.md
# 对应测试文件路径: test/dsl/test_ast_visitor.py
def test_build_func_op_add_scalar_runtime_ints_lower_to_symbol_value_type() -> None:
    def add(a: int, b: int) -> int:
        result = a + b
        return result

    func_op = build_func_op(add, -3, 5)
    arg_types = [arg.type for arg in func_op.args]
    assert arg_types == [SymbolValueType.from_expr("-3"), SymbolValueType.from_expr("5")]
    assert not arg_types[0].is_symbol()
    assert not arg_types[1].is_symbol()
    assert arg_types[0].get_value() == -3
    assert arg_types[1].get_value() == 5
    assert str(arg_types[0]) == "symbol.int<-3>"
    assert str(arg_types[1]) == "symbol.int<5>"

    add_ops = [op for op in func_op.body.block.ops if isinstance(op, SymbolAddOp)]
    assert len(add_ops) == 1
    assert list(func_op.function_type.outputs) == [SymbolValueType.from_expr("2")]
    assert add_ops[0].result.type == SymbolValueType.from_expr("2")
    assert not add_ops[0].result.type.is_symbol()
    assert add_ops[0].result.type.get_value() == 2
    assert str(add_ops[0].result.type) == "symbol.int<2>"
    return_op = next(op for op in func_op.body.block.ops if isinstance(op, func.ReturnOp))
    assert return_op.arguments[0].type == SymbolValueType.from_expr("2")
    assert "symbol.add" in _print_module(ModuleOp([func_op]))


# MGEN-019
# 创建者: 金铲铲大作战
# 最后一次更改: 金铲铲大作战
# 最近一次运行测试时间: 2026-03-23 00:20:00 +0800
# 最近一次运行成功时间: 2026-03-23 00:20:00 +0800
# 功能说明: 验证 build_func_op 省略运行时实参会直接报错。
# 测试目的: 验证 build_func_op(fn) 不再允许省略函数实际输入参数。
# 使用示例: pytest -q test/dsl/test_ast_visitor.py -k test_build_func_op_requires_explicit_runtime_args
# 对应功能实现文件路径: kernel_gen/dsl/mlir_gen.py
# 对应 spec 文件路径: spec/dsl/mlir_gen.md
# 对应测试文件路径: test/dsl/test_ast_visitor.py
def test_build_func_op_requires_explicit_runtime_args() -> None:
    def add(x: "Tensor[f32, 2, 2]") -> "Tensor[f32, 2, 2]":
        return x

    with pytest.raises(AstVisitorError, match="requires explicit runtime args") as exc_info:
        build_func_op(add)

    assert exc_info.value.location is None
    assert "expected 1, got 0" in str(exc_info.value)


# MGEN-019
# 创建者: 金铲铲大作战
# 最后一次更改: 朽木露琪亚
# 最近一次运行测试时间: 2026-03-25 16:25:00 +0800
# 最近一次运行成功时间: 2026-03-25 16:25:00 +0800
# 功能说明: 验证 build_func_op 的运行时实参数量必须与形参数量匹配。
# 测试目的: 验证多传或少传实参都属于调用错误。
# 使用示例: pytest -q test/dsl/test_ast_visitor.py -k test_build_func_op_rejects_runtime_arg_count_mismatch
# 对应功能实现文件路径: kernel_gen/dsl/mlir_gen.py
# 对应 spec 文件路径: spec/dsl/mlir_gen.md
# 对应测试文件路径: test/dsl/test_ast_visitor.py
def test_build_func_op_rejects_runtime_arg_count_mismatch() -> None:
    def add(x: "Tensor[f32, 2, 2]", y: "Tensor[f32, 2, 2]") -> "Tensor[f32, 2, 2]":
        return x + y

    with pytest.raises(AstVisitorError, match="expected 2, got 1"):
        build_func_op(add, _tensor_arg([2, 2]))


# 创建者: 金铲铲大作战
# 最后一次更改: 金铲铲大作战
# 最近一次运行测试时间: 2026-03-23 00:20:00 +0800
# 最近一次运行成功时间: 2026-03-23 00:20:00 +0800
# 功能说明: 验证 globals/builtins 只参与解析，不能代替 runtime_args。
# 测试目的: 验证即使 globals/builtins 完整，也必须显式传入函数实际输入参数。
# 使用示例: pytest -q test/dsl/test_ast_visitor.py -k test_build_func_op_globals_and_builtins_cannot_replace_runtime_args
# 对应功能实现文件路径: kernel_gen/dsl/mlir_gen.py
# 对应 spec 文件路径: spec/dsl/mlir_gen.md
# 对应测试文件路径: test/dsl/test_ast_visitor.py
def test_build_func_op_globals_and_builtins_cannot_replace_runtime_args() -> None:
    expr = SymbolDim("expr")

    def only_symbol(expr: int) -> int:
        return expr

    with pytest.raises(AstVisitorError, match="globals/builtins cannot replace function runtime args") as exc_info:
        build_func_op(only_symbol, globals={"expr": expr}, builtins=__builtins__)

    assert exc_info.value.location is None


# MGEN-027
# 创建者: 我不是牛马
# 最后一次更改: 我不是牛马
# 最近一次运行测试时间: 2026-03-25 22:18:52 +0800
# 最近一次运行成功时间: 2026-03-25 22:18:52 +0800
# 功能说明: 验证 build_func_op 会拒绝闭包外部值引用。
# 测试目的: 验证闭包捕获值不会被当作局部常量或隐式输入参与 lowering。
# 使用示例: pytest -q test/dsl/test_ast_visitor.py -k test_build_func_op_rejects_external_value_reference_inside_function_body
# 对应功能实现文件路径: kernel_gen/dsl/ast.py, kernel_gen/dsl/mlir_gen.py
# 对应 spec 文件路径: spec/dsl/mlir_gen.md
# 对应测试文件路径: test/dsl/test_ast_visitor.py
def test_build_func_op_rejects_external_value_reference_inside_function_body() -> None:
    outer_value = 7

    def use_outer_value() -> int:
        return outer_value

    with pytest.raises(AstVisitorError, match="cannot use external value inside function body") as exc_info:
        build_func_op(use_outer_value)

    assert exc_info.value.location is not None
    assert exc_info.value.location.line == 2


# MGEN-027
# 创建者: 我不是牛马
# 最后一次更改: 我不是牛马
# 最近一次运行测试时间: 2026-03-25 22:18:52 +0800
# 最近一次运行成功时间: 2026-03-25 22:18:52 +0800
# 功能说明: 验证 build_func_op 会拒绝函数体中直接引用全局外部值。
# 测试目的: 验证全局名称不会被当作局部常量或隐式输入参与 lowering。
# 使用示例: pytest -q test/dsl/test_ast_visitor.py -k test_build_func_op_rejects_global_external_value_reference
# 对应功能实现文件路径: kernel_gen/dsl/ast.py, kernel_gen/dsl/mlir_gen.py
# 对应 spec 文件路径: spec/dsl/mlir_gen.md
# 对应测试文件路径: test/dsl/test_ast_visitor.py
def test_build_func_op_rejects_global_external_value_reference(monkeypatch: pytest.MonkeyPatch) -> None:
    def use_global_value() -> int:
        return GLOBAL_EXTERNAL_VALUE

    monkeypatch.setitem(use_global_value.__globals__, "GLOBAL_EXTERNAL_VALUE", 11)

    with pytest.raises(AstVisitorError, match="cannot use external value inside function body") as exc_info:
        build_func_op(use_global_value)

    assert exc_info.value.location is not None


# MGEN-027
# 创建者: 我不是牛马
# 最后一次更改: 我不是牛马
# 最近一次运行测试时间: 2026-03-25 22:18:52 +0800
# 最近一次运行成功时间: 2026-03-25 22:18:52 +0800
# 功能说明: 验证 build_func_op 会拒绝函数体中直接引用 builtins 外部值。
# 测试目的: 验证 builtins 补充表中的外部值不会被当作局部常量或隐式输入参与 lowering。
# 使用示例: pytest -q test/dsl/test_ast_visitor.py -k test_build_func_op_rejects_builtins_external_value_reference
# 对应功能实现文件路径: kernel_gen/dsl/ast.py, kernel_gen/dsl/mlir_gen.py
# 对应 spec 文件路径: spec/dsl/mlir_gen.md
# 对应测试文件路径: test/dsl/test_ast_visitor.py
def test_build_func_op_rejects_builtins_external_value_reference() -> None:
    def use_builtin_value() -> int:
        return BUILTIN_EXTERNAL_VALUE

    with pytest.raises(AstVisitorError, match="cannot use external value inside function body") as exc_info:
        build_func_op(use_builtin_value, builtins={"BUILTIN_EXTERNAL_VALUE": 13})

    assert exc_info.value.location is not None


# MGEN-027
# 创建者: 我不是牛马
# 最后一次更改: 我不是牛马
# 最近一次运行测试时间: 2026-03-25 22:18:52 +0800
# 最近一次运行成功时间: 2026-03-25 22:18:52 +0800
# 功能说明: 验证 build_func_op 会拒绝 Attribute 形式的外部值引用。
# 测试目的: 验证 `module.CONST` 这类外部属性值不会被当作局部常量或隐式输入参与 lowering。
# 使用示例: pytest -q test/dsl/test_ast_visitor.py -k test_build_func_op_rejects_attribute_external_value_reference
# 对应功能实现文件路径: kernel_gen/dsl/ast.py, kernel_gen/dsl/mlir_gen.py
# 对应 spec 文件路径: spec/dsl/mlir_gen.md
# 对应测试文件路径: test/dsl/test_ast_visitor.py
def test_build_func_op_rejects_attribute_external_value_reference() -> None:
    class ExternalModule:
        CONST = 17

    def use_attribute_value() -> int:
        return ExternalModule.CONST

    with pytest.raises(AstVisitorError, match="cannot use external value inside function body") as exc_info:
        build_func_op(use_attribute_value)

    assert exc_info.value.location is not None


# AST-005
# 创建者: 小李飞刀
# 最后一次更改: 小李飞刀
# 最近一次运行测试时间: 2026-03-18 10:56:41 +0800
# 最近一次运行成功时间: 2026-03-18 10:56:41 +0800
# 功能说明: 验证未知名称在 AST 阶段产生诊断信息。
# 测试目的: 验证未知名称在 AST 阶段产生诊断信息。
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
# 最近一次运行测试时间: 2026-03-22 14:59:58 +0800
# 最近一次运行成功时间: 2026-03-22 14:59:58 +0800
# 功能说明: 验证不支持语句/表达式时抛 AstVisitorError 并携带位置信息。
# 测试目的: 验证不支持语句/表达式时抛 AstVisitorError 并携带位置信息。
# 使用示例: pytest -q test/dsl/test_ast_visitor.py -k test_lowering_failure_reports_diagnostics
# 对应功能实现文件路径: kernel_gen/dsl/ast_visitor.py
# 对应 spec 文件路径: spec/dsl/ast_visitor.md
# 对应测试文件路径: test/dsl/test_ast_visitor.py
def test_lowering_failure_reports_diagnostics() -> None:
    def bad(x: "Tensor[f32, 2, 2]") -> "Tensor[f32, 2, 2]":
        return x + 1

    with pytest.raises(AstVisitorError) as exc_info:
        build_func_op(bad, _tensor_arg([2, 2]))
    assert exc_info.value.location is not None


# AST-006
# 创建者: 小李飞刀
# 最后一次更改: 小李飞刀
# 最近一次运行测试时间: 2026-03-18 10:56:41 +0800
# 最近一次运行成功时间: 2026-03-18 10:56:41 +0800
# 功能说明: 验证非法返回注解会保留可定位诊断并向上抛出。
# 测试目的: 验证非法返回注解会保留可定位诊断并向上抛出。
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
# 测试目的: 验证非法 Tensor 返回注解会抛出带诊断的错误。
# 使用示例: pytest -q test/dsl/test_ast_visitor.py -k test_invalid_tensor_return_annotation_reports_diagnostics
# 对应功能实现文件路径: kernel_gen/dsl/mlir_gen.py
# 对应 spec 文件路径: spec/dsl/mlir_gen.md
# 对应测试文件路径: test/dsl/test_ast_visitor.py
def test_invalid_tensor_return_annotation_reports_diagnostics() -> None:
    def bad_return(x: "Tensor[f32, 2, 2]") -> "Tensor[f16, 2, 2]":
        return x

    with pytest.raises(AstVisitorError) as exc_info:
        build_func_op(bad_return, _tensor_arg([2, 2]))
    assert exc_info.value.location is not None


# MGEN-008
# 创建者: 小李飞刀
# 最后一次更改: 小李飞刀
# 最近一次运行测试时间: 2026-03-18 10:56:41 +0800
# 最近一次运行成功时间: 2026-03-18 10:56:41 +0800
# 功能说明: 验证常量 lowering 失败会抛出带诊断的错误。
# 测试目的: 验证常量 lowering 失败会抛出带诊断的错误。
# 使用示例: pytest -q test/dsl/test_ast_visitor.py -k test_constant_lowering_reports_diagnostics
# 对应功能实现文件路径: kernel_gen/dsl/mlir_gen.py
# 对应 spec 文件路径: spec/dsl/mlir_gen.md
# 对应测试文件路径: test/dsl/test_ast_visitor.py
def test_constant_lowering_reports_diagnostics() -> None:
    def bad(x: "Tensor[f32, 2, 2]") -> "Tensor[f32, 2, 2]":
        return 1

    with pytest.raises(AstVisitorError) as exc_info:
        build_func_op(bad, _tensor_arg([2, 2]))
    assert exc_info.value.location is not None


# AST-007
# 创建者: 小李飞刀
# 最后一次更改: 小李飞刀
# 最近一次运行测试时间: 2026-03-18 10:56:41 +0800
# 最近一次运行成功时间: 2026-03-18 10:56:41 +0800
# 功能说明: 验证缺失 return 会抛出带诊断的错误。
# 测试目的: 验证缺失 return 会抛出带诊断的错误。
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
# 测试目的: 验证返回类型不匹配会抛出带诊断的错误。
# 使用示例: pytest -q test/dsl/test_ast_visitor.py -k test_return_type_mismatch_reports_diagnostics
# 对应功能实现文件路径: kernel_gen/dsl/mlir_gen.py
# 对应 spec 文件路径: spec/dsl/mlir_gen.md
# 对应测试文件路径: test/dsl/test_ast_visitor.py
def test_return_type_mismatch_reports_diagnostics() -> None:
    def bad(x: "Tensor[f32, 2, 2]", y: "Tensor[f32, 2, 2]") -> "Tensor[f32, 2, 2]":
        return x == y

    with pytest.raises(AstVisitorError) as exc_info:
        build_func_op(bad, _tensor_arg([2, 2]), _tensor_arg([2, 2]))
    assert exc_info.value.location is not None


# AST-008
# 创建者: 小李飞刀
# 最后一次更改: 小李飞刀
# 最近一次运行测试时间: 2026-03-18 10:56:41 +0800
# 最近一次运行成功时间: 2026-03-18 10:56:41 +0800
# 功能说明: 验证缺少维度的 Tensor 注解会抛出带诊断的错误。
# 测试目的: 验证缺少维度的 Tensor 注解会抛出带诊断的错误。
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
# 测试目的: 验证多语句 SSA 顺序与 value 复用。
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

    func_op = build_func_op(add, _tensor_arg([2, 2]), _tensor_arg([2, 2]))
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
# 测试目的: 验证 LoadAST lowering 生成 dma.load。
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
# 测试目的: 验证 StoreAST lowering 生成 dma.store。
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
# 测试目的: 验证 LoadAST 非 unit stride 抛出带诊断的错误。
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
# 测试目的: 验证 index rank mismatch 抛错并保留位置信息。
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
# 测试目的: 验证 StoreAST 非 memory value 抛出带诊断的错误。
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


# EMIT-014
# 创建者: 摸鱼小分队
# 最后一次更改: 我不是牛马
# 最近一次运行测试时间: 2026-03-23 02:43:15 +0800
# 最近一次运行成功时间: 2026-03-23 02:43:15 +0800
# 功能说明: 验证 ForAST lowering 会保留循环结构并在循环体内生成 dma.load。
# 测试目的: 验证 ForAST lowering 会保留循环结构并在循环体内生成 dma.load。
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
    loop_ops = [op for op in func_op.body.block.ops if isinstance(op, scf.ForOp)]
    assert len(loop_ops) == 1
    ops = [op for op in loop_ops[0].body.block.ops if isinstance(op, DmaLoadOp)]
    assert len(ops) == 1
    offsets = list(ops[0].offsets)
    assert len(offsets) == 2
    assert _unwrap_index_cast(offsets[0]) is loop_ops[0].body.block.args[0]


# EMIT-010
# 创建者: 小李飞刀
# 最后一次更改: 小李飞刀
# 最近一次运行测试时间: 2026-03-23 02:43:15 +0800
# 最近一次运行成功时间: 2026-03-23 02:43:15 +0800
# 功能说明: 验证符号边界 ForAST lowering 为 symbol.for 并直接复用 symbol.int 作为 DMA operand。
# 测试目的: 验证符号边界 ForAST lowering 为 symbol.for 并直接复用 symbol.int 作为 DMA operand。
# 使用示例: pytest -q test/dsl/test_ast_visitor.py -k test_emit_mlir_symbolic_for_loop_avoids_index_cast
# 对应功能实现文件路径: kernel_gen/dsl/emit_mlir.py
# 对应 spec 文件路径: spec/dsl/emit_mlir.md
# 对应测试文件路径: test/dsl/test_ast_visitor.py
def test_emit_mlir_symbolic_for_loop_avoids_index_cast() -> None:
    memory = Memory([2, 2], NumericType.Float32)
    tensor = TensorAST(name="x", memory=memory, location=None)
    start = ScalarArgAST(name="start", value_type=int, is_symbolic=True, location=None)
    end = ScalarArgAST(name="end", value_type=int, is_symbolic=True, location=None)
    step = ScalarArgAST(name="step", value_type=int, is_symbolic=True, location=None)
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
    loop = ForAST(var=loop_var, start=start, end=end, step=step, body=body, location=None)
    func_ast = FunctionAST(
        name="symbol_loop",
        inputs=[tensor, start, end, step],
        outputs=[],
        body=BlockAST([loop, tensor]),
    )
    func_op = build_func_op_from_ast(func_ast)
    loop_ops = [op for op in func_op.body.block.ops if isinstance(op, SymbolForOp)]
    assert len(loop_ops) == 1
    loop_body_ops = list(loop_ops[0].body.block.ops)
    assert not any(isinstance(op, arith.IndexCastOp) for op in loop_body_ops)
    load_ops = [op for op in loop_body_ops if isinstance(op, DmaLoadOp)]
    assert len(load_ops) == 1
    offsets = list(load_ops[0].offsets)
    assert offsets[0] is loop_ops[0].body.block.args[0]


# EMIT-015
# 创建者: 朽木露琪亚
# 最后一次更改: 朽木露琪亚
# 最近一次运行测试时间: 2026-03-25 10:04:04 +0800
# 最近一次运行成功时间: 2026-03-25 10:04:04 +0800
# 功能说明: 验证 alloc AST lowering 为 dma.alloc。
# 测试目的: 验证 DmaAllocAST 直接 lowering 为 DmaAllocOp，且结果 memory space 与 dtype 正确。
# 使用示例: pytest -q test/dsl/test_ast_visitor.py -k test_emit_mlir_dma_alloc_lowering
# 对应功能实现文件路径: kernel_gen/dsl/emit_mlir.py
# 对应 spec 文件路径: spec/dsl/emit_mlir.md
# 对应测试文件路径: test/dsl/test_ast_visitor.py
def test_emit_mlir_dma_alloc_lowering() -> None:
    expr = DmaAllocAST(shape=[ConstAST(2), ConstAST(3)], dtype=NumericType.Float32, space=MemorySpace.SM, location=None)
    ctx = EmitContext(builder=Block(), symbols={}, types={})
    result = _lower_expr(expr, ctx)
    assert isinstance(result.owner, DmaAllocOp)
    assert result.type.space.space.data == "shared"
    assert result.type.element_type == f32


# EMIT-016
# 创建者: 朽木露琪亚
# 最后一次更改: 朽木露琪亚
# 最近一次运行测试时间: 2026-03-25 10:04:04 +0800
# 最近一次运行成功时间: 2026-03-25 10:04:04 +0800
# 功能说明: 验证 copy AST lowering 会先生成目标 alloc，再生成 dma.copy。
# 测试目的: 验证 DmaCopyAST 返回目标 memory value，并在块内发射 DmaCopyOp。
# 使用示例: pytest -q test/dsl/test_ast_visitor.py -k test_emit_mlir_dma_copy_lowering
# 对应功能实现文件路径: kernel_gen/dsl/emit_mlir.py
# 对应 spec 文件路径: spec/dsl/emit_mlir.md
# 对应测试文件路径: test/dsl/test_ast_visitor.py
def test_emit_mlir_dma_copy_lowering() -> None:
    source_memory = Memory([2, 3], NumericType.Float32, space=MemorySpace.GM)
    source = TensorAST(name="src", memory=source_memory, location=None)
    block = Block(arg_types=[_memory_to_nn_type(source_memory)])
    ctx = EmitContext(builder=block, symbols={"src": block.args[0]}, types={})
    ctx._set_cache(_expr_key(source), block.args[0])
    ctx.types[_expr_key(source)] = block.args[0].type

    result = _lower_expr(DmaCopyAST(source=source, space=MemorySpace.SM, location=None), ctx)
    assert isinstance(result.owner, DmaAllocOp)
    assert any(isinstance(op, DmaCopyOp) for op in block.ops)
    assert result.type.space.space.data == "shared"


# EMIT-017
# 创建者: 朽木露琪亚
# 最后一次更改: 朽木露琪亚
# 最近一次运行测试时间: 2026-03-25 10:04:04 +0800
# 最近一次运行成功时间: 2026-03-25 10:04:04 +0800
# 功能说明: 验证 cast AST lowering 为 dma.cast。
# 测试目的: 验证 DmaCastAST 生成 DmaCastOp，并允许覆盖目标 memory space。
# 使用示例: pytest -q test/dsl/test_ast_visitor.py -k test_emit_mlir_dma_cast_lowering
# 对应功能实现文件路径: kernel_gen/dsl/emit_mlir.py
# 对应 spec 文件路径: spec/dsl/emit_mlir.md
# 对应测试文件路径: test/dsl/test_ast_visitor.py
def test_emit_mlir_dma_cast_lowering() -> None:
    source_memory = Memory([2, 3], NumericType.Float32, space=MemorySpace.GM)
    source = TensorAST(name="src", memory=source_memory, location=None)
    block = Block(arg_types=[_memory_to_nn_type(source_memory)])
    ctx = EmitContext(builder=block, symbols={"src": block.args[0]}, types={})
    ctx._set_cache(_expr_key(source), block.args[0])
    ctx.types[_expr_key(source)] = block.args[0].type

    result = _lower_expr(
        DmaCastAST(source=source, dtype=NumericType.Float16, memoryspace=MemorySpace.SM, location=None),
        ctx,
    )
    assert isinstance(result.owner, DmaCastOp)
    assert result.type.element_type != block.args[0].type.element_type
    assert result.type.space.space.data == "shared"


# EMIT-018
# 创建者: 朽木露琪亚
# 最后一次更改: 朽木露琪亚
# 最近一次运行测试时间: 2026-03-25 10:04:04 +0800
# 最近一次运行成功时间: 2026-03-25 10:04:04 +0800
# 功能说明: 验证 view AST lowering 为 dma.view。
# 测试目的: 验证 DmaViewAST 生成 DmaViewOp，并按结果 shape 生成视图结果类型。
# 使用示例: pytest -q test/dsl/test_ast_visitor.py -k test_emit_mlir_dma_view_lowering
# 对应功能实现文件路径: kernel_gen/dsl/emit_mlir.py
# 对应 spec 文件路径: spec/dsl/emit_mlir.md
# 对应测试文件路径: test/dsl/test_ast_visitor.py
def test_emit_mlir_dma_view_lowering() -> None:
    source_memory = Memory([4, 4], NumericType.Float32, space=MemorySpace.GM)
    source = TensorAST(name="src", memory=source_memory, location=None)
    block = Block(arg_types=[_memory_to_nn_type(source_memory)])
    ctx = EmitContext(builder=block, symbols={"src": block.args[0]}, types={})
    ctx._set_cache(_expr_key(source), block.args[0])
    ctx.types[_expr_key(source)] = block.args[0].type

    result = _lower_expr(
        DmaViewAST(
            source=source,
            offset=[ConstAST(1), ConstAST(1)],
            size=[ConstAST(2), ConstAST(2)],
            stride=[ConstAST(1), ConstAST(1)],
            location=None,
        ),
        ctx,
    )
    assert isinstance(result.owner, DmaViewOp)
    assert [attr.data for attr in result.type.shape.data] == [2, 2]


# EMIT-019
# 创建者: 朽木露琪亚
# 最后一次更改: 朽木露琪亚
# 最近一次运行测试时间: 2026-03-25 10:04:04 +0800
# 最近一次运行成功时间: 2026-03-25 10:04:04 +0800
# 功能说明: 验证 reshape AST lowering 为 dma.reshape。
# 测试目的: 验证 DmaReshapeAST 生成 DmaReshapeOp，并输出目标 shape。
# 使用示例: pytest -q test/dsl/test_ast_visitor.py -k test_emit_mlir_dma_reshape_lowering
# 对应功能实现文件路径: kernel_gen/dsl/emit_mlir.py
# 对应 spec 文件路径: spec/dsl/emit_mlir.md
# 对应测试文件路径: test/dsl/test_ast_visitor.py
def test_emit_mlir_dma_reshape_lowering() -> None:
    source_memory = Memory([4, 4], NumericType.Float32, space=MemorySpace.GM)
    source = TensorAST(name="src", memory=source_memory, location=None)
    block = Block(arg_types=[_memory_to_nn_type(source_memory)])
    ctx = EmitContext(builder=block, symbols={"src": block.args[0]}, types={})
    ctx._set_cache(_expr_key(source), block.args[0])
    ctx.types[_expr_key(source)] = block.args[0].type

    result = _lower_expr(DmaReshapeAST(source=source, shape=[ConstAST(2), ConstAST(8)], location=None), ctx)
    assert isinstance(result.owner, DmaReshapeOp)
    assert [attr.data for attr in result.type.shape.data] == [2, 8]


# EMIT-020
# 创建者: 朽木露琪亚
# 最后一次更改: 朽木露琪亚
# 最近一次运行测试时间: 2026-03-25 10:04:04 +0800
# 最近一次运行成功时间: 2026-03-25 10:04:04 +0800
# 功能说明: 验证 flatten AST 按一维 reshape 语义 lowering。
# 测试目的: 验证 DmaFlattenAST 生成 DmaReshapeOp，且输出 shape 为元素总数的一维结果。
# 使用示例: pytest -q test/dsl/test_ast_visitor.py -k test_emit_mlir_dma_flatten_lowering
# 对应功能实现文件路径: kernel_gen/dsl/emit_mlir.py
# 对应 spec 文件路径: spec/dsl/emit_mlir.md
# 对应测试文件路径: test/dsl/test_ast_visitor.py
def test_emit_mlir_dma_flatten_lowering() -> None:
    source_memory = Memory([2, 3], NumericType.Float32, space=MemorySpace.GM)
    source = TensorAST(name="src", memory=source_memory, location=None)
    block = Block(arg_types=[_memory_to_nn_type(source_memory)])
    ctx = EmitContext(builder=block, symbols={"src": block.args[0]}, types={})
    ctx._set_cache(_expr_key(source), block.args[0])
    ctx.types[_expr_key(source)] = block.args[0].type

    result = _lower_expr(DmaFlattenAST(source=source, location=None), ctx)
    assert isinstance(result.owner, DmaReshapeOp)
    assert [attr.data for attr in result.type.shape.data] == [6]


# EMIT-021
# 创建者: 朽木露琪亚
# 最后一次更改: 朽木露琪亚
# 最近一次运行测试时间: 2026-03-25 10:04:04 +0800
# 最近一次运行成功时间: 2026-03-25 10:04:04 +0800
# 功能说明: 验证 free AST 作为无返回值语句处理。
# 测试目的: 验证 DmaFreeAST 不生成新的 SSA 结果，也不会向 block 中插入额外 DMA op。
# 使用示例: pytest -q test/dsl/test_ast_visitor.py -k test_emit_mlir_dma_free_statement
# 对应功能实现文件路径: kernel_gen/dsl/emit_mlir.py
# 对应 spec 文件路径: spec/dsl/emit_mlir.md
# 对应测试文件路径: test/dsl/test_ast_visitor.py
def test_emit_mlir_dma_free_statement() -> None:
    source_memory = Memory([2, 3], NumericType.Float32, space=MemorySpace.GM)
    source = TensorAST(name="src", memory=source_memory, location=None)
    block = Block(arg_types=[_memory_to_nn_type(source_memory)])
    ctx = EmitContext(builder=block, symbols={"src": block.args[0]}, types={})
    ctx._set_cache(_expr_key(source), block.args[0])
    ctx.types[_expr_key(source)] = block.args[0].type

    result = emit_node_mlir(DmaFreeAST(value=source, location=None), ctx)
    assert result is None
    assert list(block.ops) == []


# AST-009
# 创建者: OpenAI
# 最后一次更改: 朽木露琪亚
# 最近一次运行测试时间: 2026-03-25 16:05:00 +0800
# 最近一次运行成功时间: 2026-03-25 16:05:00 +0800
# 功能说明: 验证未注解 SymbolDim 参数可按标量参数解析。
# 测试目的: 验证未注解 SymbolDim 参数可按标量参数解析。
# 使用示例: pytest -q test/dsl/test_ast_visitor.py -k test_parse_function_infers_symboldim_arguments_without_annotations
# 对应功能实现文件路径: kernel_gen/dsl/ast.py
# 对应 spec 文件路径: spec/dsl/ast.md
# 对应测试文件路径: test/dsl/test_ast_visitor.py
def test_parse_function_infers_symboldim_arguments_without_annotations(monkeypatch: pytest.MonkeyPatch) -> None:
    def loop_fn(start: int, end: int, step: int, x: "Tensor[f32, N]") -> "Tensor[f32, N]":
        return x

    def fake_getsource(_obj: object) -> str:
        return """
def loop_fn(start, end, step, x: "Tensor[f32, N]"):
    return x
"""

    monkeypatch.setattr(
        inspect,
        "getsource",
        fake_getsource,
    )
    monkeypatch.setitem(loop_fn.__globals__, "start", SymbolDim("start"))
    monkeypatch.setitem(loop_fn.__globals__, "end", SymbolDim("end"))
    monkeypatch.setitem(loop_fn.__globals__, "step", SymbolDim("step"))
    func_ast = parse_function(loop_fn)
    assert [item.name for item in func_ast.inputs[:3]] == ["start", "end", "step"]
    assert all(isinstance(item, ScalarArgAST) for item in func_ast.inputs[:3])


# AST-010
# 创建者: 金铲铲大作战
# 最后一次更改: 金铲铲大作战
# 最近一次运行测试时间: 2026-03-25 12:01:58 +0800
# 最近一次运行成功时间: 2026-03-25 12:01:58 +0800
# 功能说明: 验证未注解 bool runtime 参数仍按整型标量参数解析。
# 测试目的: 锁定 bool runtime 参数在 AST 解析阶段继续复用整型推断分支，避免等价重构后发生类型漂移。
# 使用示例: pytest -q test/dsl/test_ast_visitor.py -k test_parse_function_infers_bool_runtime_arguments_without_annotations
# 对应功能实现文件路径: kernel_gen/dsl/ast.py
# 对应 spec 文件路径: spec/dsl/ast.md
# 对应测试文件路径: test/dsl/test_ast_visitor.py
def test_parse_function_infers_bool_runtime_arguments_without_annotations(monkeypatch: pytest.MonkeyPatch) -> None:
    func_ast = _parse_function_from_source(
        monkeypatch,
        """
def kernel(flag, x: "Tensor[f32, 2, 2]") -> "Tensor[f32, 2, 2]":
    return x
""",
        runtime_table={"flag": True},
    )

    if not isinstance(func_ast.inputs[0], ScalarArgAST):
        raise AssertionError("expected first input to be ScalarArgAST")
    if func_ast.inputs[0].name != "flag":
        raise AssertionError("expected first input name to stay flag")
    if func_ast.inputs[0].value_type is not int:
        raise AssertionError("expected bool runtime argument to infer int type")
    if func_ast.inputs[0].is_symbolic is not False:
        raise AssertionError("expected bool runtime argument to stay non-symbolic")
    if not isinstance(func_ast.inputs[1], TensorAST):
        raise AssertionError("expected annotated tensor input to remain TensorAST")


# AST-011
# 创建者: 金铲铲大作战
# 最后一次更改: 金铲铲大作战
# 最近一次运行测试时间: 2026-03-25 12:01:58 +0800
# 最近一次运行成功时间: 2026-03-25 12:01:58 +0800
# 功能说明: 验证未注解 float runtime 参数仍报 Missing annotation。
# 测试目的: 锁定 float runtime 参数不会被缺失注解回退推断为标量参数，避免重构放宽公开语义。
# 使用示例: pytest -q test/dsl/test_ast_visitor.py -k test_parse_function_rejects_float_runtime_arguments_without_annotations
# 对应功能实现文件路径: kernel_gen/dsl/ast.py
# 对应 spec 文件路径: spec/dsl/ast.md
# 对应测试文件路径: test/dsl/test_ast_visitor.py
def test_parse_function_rejects_float_runtime_arguments_without_annotations(monkeypatch: pytest.MonkeyPatch) -> None:
    with pytest.raises(AstParseError) as exc_info:
        _parse_function_from_source(
            monkeypatch,
            """
def kernel(scale, x: "Tensor[f32, 2, 2]") -> "Tensor[f32, 2, 2]":
    return x
""",
            runtime_table={"scale": 1.5},
        )

    diagnostics = exc_info.value.diagnostics
    if not diagnostics:
        raise AssertionError("expected diagnostics for missing annotation")
    if diagnostics[0].message != "Missing annotation":
        raise AssertionError("expected Missing annotation diagnostic for float runtime argument")


# AST-012
# 创建者: 金铲铲大作战
# 最后一次更改: 金铲铲大作战
# 最近一次运行测试时间: 2026-03-25 12:01:58 +0800
# 最近一次运行成功时间: 2026-03-25 12:01:58 +0800
# 功能说明: 验证 nn 算术 helper 非法参数个数保持 Unsupported nn arithmetic arity 报错。
# 测试目的: 锁定 _parse_nn_arithmetic_call 抽取后的 too-few/too-many arity 负路径诊断口径。
# 使用示例: pytest -q test/dsl/test_ast_visitor.py -k test_parse_function_rejects_unsupported_nn_arithmetic_arity_variants
# 对应功能实现文件路径: kernel_gen/dsl/ast.py
# 对应 spec 文件路径: spec/dsl/ast.md
# 对应测试文件路径: test/dsl/test_ast_visitor.py
def test_parse_function_rejects_unsupported_nn_arithmetic_arity_variants() -> None:
    def too_few(x: "Tensor[f32, 2, 2]") -> "Tensor[f32, 2, 2]":
        return nn.add(x)

    def too_many(
        x: "Tensor[f32, 2, 2]",
        y: "Tensor[f32, 2, 2]",
        z: "Tensor[f32, 2, 2]",
    ) -> "Tensor[f32, 2, 2]":
        return nn.add(x, y, z)

    for fn in (too_few, too_many):
        with pytest.raises(AstParseError) as exc_info:
            parse_function(fn)
        diagnostics = exc_info.value.diagnostics
        if not diagnostics:
            raise AssertionError("expected diagnostics for invalid nn arithmetic arity")
        if diagnostics[0].message != "Unsupported nn arithmetic arity":
            raise AssertionError("expected Unsupported nn arithmetic arity diagnostic")


# AST-013
# 创建者: 金铲铲大作战
# 最后一次更改: 金铲铲大作战
# 最近一次运行测试时间: 2026-03-25 12:01:58 +0800
# 最近一次运行成功时间: 2026-03-25 12:01:58 +0800
# 功能说明: 验证 load helper 的 arity/source/space 负路径报错口径不变。
# 测试目的: 锁定 _parse_load_like_call 在 load 分支上的非法参数个数、非法 source 与非法 space 诊断。
# 使用示例: pytest -q test/dsl/test_ast_visitor.py -k test_parse_function_rejects_invalid_load_helper_variants
# 对应功能实现文件路径: kernel_gen/dsl/ast.py
# 对应 spec 文件路径: spec/dsl/ast.md
# 对应测试文件路径: test/dsl/test_ast_visitor.py
def test_parse_function_rejects_invalid_load_helper_variants() -> None:
    def bad_arity(src: "Tensor[f32, 4, 4]") -> "Tensor[f32, 2, 2]":
        return load(src, [0, 0])

    def bad_source(src: int) -> "Tensor[f32, 2, 2]":
        return load(src, [0], [1])

    def bad_space(src: "Tensor[f32, 4, 4]") -> "Tensor[f32, 2, 2]":
        return load(src, [0, 0], [2, 2], [1, 1], 1)

    expected_messages = (
        ("Unsupported load arity", bad_arity),
        ("load source must be TensorAST", bad_source),
        ("load space must be MemorySpace", bad_space),
    )
    for expected_message, fn in expected_messages:
        with pytest.raises(AstParseError) as exc_info:
            parse_function(fn)
        diagnostics = exc_info.value.diagnostics
        if not diagnostics:
            raise AssertionError(f"expected diagnostics for load variant: {expected_message}")
        if diagnostics[0].message != expected_message:
            raise AssertionError(f"expected load diagnostic {expected_message!r}, got {diagnostics[0].message!r}")


# AST-014
# 创建者: 金铲铲大作战
# 最后一次更改: 金铲铲大作战
# 最近一次运行测试时间: 2026-03-25 12:01:58 +0800
# 最近一次运行成功时间: 2026-03-25 12:01:58 +0800
# 功能说明: 验证 slice helper 的 arity/source/space 负路径报错口径不变。
# 测试目的: 锁定 _parse_load_like_call 在 slice 分支上的非法参数个数、非法 source 与非法 space 诊断。
# 使用示例: pytest -q test/dsl/test_ast_visitor.py -k test_parse_function_rejects_invalid_slice_helper_variants
# 对应功能实现文件路径: kernel_gen/dsl/ast.py
# 对应 spec 文件路径: spec/dsl/ast.md
# 对应测试文件路径: test/dsl/test_ast_visitor.py
def test_parse_function_rejects_invalid_slice_helper_variants() -> None:
    def bad_arity(src: "Tensor[f32, 4, 4]") -> "Tensor[f32, 2, 2]":
        return slice(src, [0, 0], [2, 2], [1, 1], MemorySpace.SM, 1)

    def bad_source(src: int) -> "Tensor[f32, 2, 2]":
        return slice(src, [0], [1])

    def bad_space(src: "Tensor[f32, 4, 4]") -> "Tensor[f32, 2, 2]":
        return slice(src, [0, 0], [2, 2], [1, 1], 1)

    expected_messages = (
        ("Unsupported slice arity", bad_arity),
        ("slice source must be TensorAST", bad_source),
        ("slice space must be MemorySpace", bad_space),
    )
    for expected_message, fn in expected_messages:
        with pytest.raises(AstParseError) as exc_info:
            parse_function(fn)
        diagnostics = exc_info.value.diagnostics
        if not diagnostics:
            raise AssertionError(f"expected diagnostics for slice variant: {expected_message}")
        if diagnostics[0].message != expected_message:
            raise AssertionError(f"expected slice diagnostic {expected_message!r}, got {diagnostics[0].message!r}")


# AST-015
# 创建者: 金铲铲大作战
# 最后一次更改: 金铲铲大作战
# 最近一次运行测试时间: 2026-03-25 12:01:58 +0800
# 最近一次运行成功时间: 2026-03-25 12:01:58 +0800
# 功能说明: 验证 store helper 的 arity/target 负路径报错口径不变。
# 测试目的: 锁定 _parse_store_like_call 在 store 分支上的非法参数个数与非法 target 诊断。
# 使用示例: pytest -q test/dsl/test_ast_visitor.py -k test_parse_function_rejects_invalid_store_helper_variants
# 对应功能实现文件路径: kernel_gen/dsl/ast.py
# 对应 spec 文件路径: spec/dsl/ast.md
# 对应测试文件路径: test/dsl/test_ast_visitor.py
def test_parse_function_rejects_invalid_store_helper_variants() -> None:
    def bad_arity(tile: "Tensor[f32, 2, 2]", dst: "Tensor[f32, 4, 4]"):
        store(tile, dst, [0, 0])

    def bad_target(tile: "Tensor[f32, 2, 2]", dst: int):
        store(tile, dst, [0, 0], [2, 2])

    expected_messages = (
        ("Unsupported store arity", bad_arity),
        ("store target must be TensorAST", bad_target),
    )
    for expected_message, fn in expected_messages:
        with pytest.raises(AstParseError) as exc_info:
            parse_function(fn)
        diagnostics = exc_info.value.diagnostics
        if not diagnostics:
            raise AssertionError(f"expected diagnostics for store variant: {expected_message}")
        if diagnostics[0].message != expected_message:
            raise AssertionError(f"expected store diagnostic {expected_message!r}, got {diagnostics[0].message!r}")


# AST-016
# 创建者: 金铲铲大作战
# 最后一次更改: 金铲铲大作战
# 最近一次运行测试时间: 2026-03-25 12:01:58 +0800
# 最近一次运行成功时间: 2026-03-25 12:01:58 +0800
# 功能说明: 验证 deslice helper 的 arity/target/space 负路径报错口径不变。
# 测试目的: 锁定 _parse_store_like_call 在 deslice 分支上的非法参数个数、非法 target 与非法 space 诊断。
# 使用示例: pytest -q test/dsl/test_ast_visitor.py -k test_parse_function_rejects_invalid_deslice_helper_variants
# 对应功能实现文件路径: kernel_gen/dsl/ast.py
# 对应 spec 文件路径: spec/dsl/ast.md
# 对应测试文件路径: test/dsl/test_ast_visitor.py
def test_parse_function_rejects_invalid_deslice_helper_variants() -> None:
    def bad_arity(tile: "Tensor[f32, 2, 2]", dst: "Tensor[f32, 4, 4]"):
        deslice(tile, dst, [0, 0])

    def bad_target(tile: "Tensor[f32, 2, 2]", dst: int):
        deslice(tile, dst, [0, 0], [2, 2])

    def bad_space(tile: "Tensor[f32, 2, 2]", dst: "Tensor[f32, 4, 4]"):
        deslice(tile, dst, [0, 0], [2, 2], [1, 1], 1)

    expected_messages = (
        ("Unsupported deslice arity", bad_arity),
        ("deslice target must be TensorAST", bad_target),
        ("deslice space must be MemorySpace", bad_space),
    )
    for expected_message, fn in expected_messages:
        with pytest.raises(AstParseError) as exc_info:
            parse_function(fn)
        diagnostics = exc_info.value.diagnostics
        if not diagnostics:
            raise AssertionError(f"expected diagnostics for deslice variant: {expected_message}")
        if diagnostics[0].message != expected_message:
            raise AssertionError(f"expected deslice diagnostic {expected_message!r}, got {diagnostics[0].message!r}")


# MGEN-015
# 创建者: OpenAI
# 最后一次更改: 朽木露琪亚
# 最近一次运行测试时间: 2026-03-25 16:05:00 +0800
# 最近一次运行成功时间: 2026-03-25 16:05:00 +0800
# 功能说明: 验证 LoopRange + slice/deslice + 无 return 场景可生成 symbol.for + dma.slice/dma.deslice。
# 测试目的: 验证 LoopRange + slice/deslice + 无 return 场景会直接传递 symbol.int 循环变量，不生成 arith.index_cast。
# 使用示例: pytest -q test/dsl/test_ast_visitor.py -k test_build_func_op_supports_symbolic_for_loop_dma_without_return
# 对应功能实现文件路径: kernel_gen/dsl/mlir_gen.py
# 对应 spec 文件路径: spec/dsl/mlir_gen.md
# 对应测试文件路径: test/dsl/test_ast_visitor.py
def test_build_func_op_supports_symbolic_for_loop_dma_without_return(monkeypatch: pytest.MonkeyPatch) -> None:
    from kernel_gen.operation.dma import deslice, slice
    from kernel_gen.operation.scf import LoopRange

    A = Memory(["L"], NumericType.Float32)
    B = Memory(["L"], NumericType.Float32)
    C = Memory(["L"], NumericType.Float32)
    start = SymbolDim("start")
    end = SymbolDim("end")
    step = SymbolDim("step")

    def add(
        A: "Tensor[f32, L]",
        B: "Tensor[f32, L]",
        C: "Tensor[f32, L]",
        end: int,
        start: int,
        step: int,
    ):
        for index in LoopRange(start, end, step):
            SA = slice(A, [index], [step], [1], MemorySpace.LM)
            SB = slice(B, [index], [step], [1], MemorySpace.LM)
            SC = SA + SB
            deslice(SC, C, [index], [step], [1], MemorySpace.LM)

    monkeypatch.setitem(add.__globals__, "A", A)
    monkeypatch.setitem(add.__globals__, "B", B)
    monkeypatch.setitem(add.__globals__, "C", C)
    monkeypatch.setitem(add.__globals__, "start", start)
    monkeypatch.setitem(add.__globals__, "end", end)
    monkeypatch.setitem(add.__globals__, "step", step)
    monkeypatch.setitem(add.__globals__, "MemorySpace", MemorySpace)
    monkeypatch.setitem(add.__globals__, "slice", slice)
    monkeypatch.setitem(add.__globals__, "deslice", deslice)
    monkeypatch.setitem(add.__globals__, "LoopRange", LoopRange)

    func_op = build_func_op(add, A, B, C, end, start, step)
    assert isinstance(func_op, func.FuncOp)
    assert len(list(func_op.function_type.outputs)) == 0
    loop_ops = [op for op in func_op.body.block.ops if isinstance(op, SymbolForOp)]
    assert len(loop_ops) == 1
    loop_body_ops = list(loop_ops[0].body.block.ops)
    slice_ops = [op for op in loop_body_ops if isinstance(op, DmaSliceOp)]
    deslice_ops = [op for op in loop_body_ops if isinstance(op, DmaDesliceOp)]
    assert len(slice_ops) == 2
    assert len(deslice_ops) == 1
    assert not any(isinstance(op, DmaLoadOp) for op in loop_body_ops)
    assert not any(isinstance(op, DmaStoreOp) for op in loop_body_ops)
    assert not any(isinstance(op, arith.IndexCastOp) for op in loop_body_ops)
    assert slice_ops[0].space.space.data == "local"
    loop_body = loop_ops[0].body.block
    offsets = list(slice_ops[0].offsets)
    sizes = list(slice_ops[0].sizes)
    assert offsets[0] is loop_body.args[0]
    assert sizes[0] is func_op.body.block.args[5]
    assert list(deslice_ops[0].offsets)[0] is loop_body.args[0]


# MGEN-011
# 创建者: 金铲铲大作战
# 最后一次更改: 小李飞刀
# 最近一次运行测试时间: 2026-03-19 03:24:32 +0800
# 最近一次运行成功时间: 2026-03-19 03:24:32 +0800
# 功能说明: 验证 singleton dim 隐式 broadcast lowering 为 nn.broadcast + nn.add。
# 测试目的: 验证 singleton dim 隐式 broadcast lowering 为 nn.broadcast + nn.add。
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

    func_op = build_func_op(add, _tensor_arg([1, "N"]), _tensor_arg(["M", "N"]))
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
# 测试目的: 验证前置维隐式 broadcast lowering 为 nn.broadcast + nn.add。
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

    func_op = build_func_op(add, _tensor_arg(["N"]), _tensor_arg(["M", "N"]))
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
# 测试目的: 验证比较表达式隐式 broadcast lowering 为 nn.broadcast + nn.eq。
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
# 测试目的: 验证不可广播的逐元素表达式抛 LoweringError 且保留位置。
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
        build_func_op(add, _tensor_arg(["A", "B"]), _tensor_arg(["A", "C"]))
    assert exc_info.value.location is not None

# AST-009
# 创建者: 小李飞刀
# 最后一次更改: 小李飞刀
# 最近一次运行测试时间: 2026-03-18 10:56:41 +0800
# 最近一次运行成功时间: 2026-03-18 10:56:41 +0800
# 功能说明: 验证不支持语法会抛出带诊断的错误。
# 测试目的: 验证不支持语法会抛出带诊断的错误。
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


# AV-004
# 创建者: 不要啊教练
# 最后一次更改: 不要啊教练
# 最近一次运行测试时间: 2026-03-22 14:59:58 +0800
# 最近一次运行成功时间: 2026-03-22 14:59:58 +0800
# 功能说明: 覆盖 AstVisitor.visit_function 的符号表命中与跳过分支。
# 测试目的: 覆盖 AstVisitor.visit_function 的符号表命中与跳过分支。
# 使用示例: pytest -q test/dsl/test_ast_visitor.py -k test_ast_visitor_visit_function_skips_unbound_input
# 对应功能实现文件路径: kernel_gen/dsl/ast_visitor.py
# 对应 spec 文件路径: spec/dsl/ast_visitor.md
# 对应测试文件路径: test/dsl/test_ast_visitor.py
def test_ast_visitor_visit_function_skips_unbound_input() -> None:
    memory = Memory([2, 2], NumericType.Float32)
    lhs = TensorAST(name="x", memory=memory, location=None)
    rhs = TensorAST(name="y", memory=memory, location=None)
    func_ast = FunctionAST("tmp", [lhs, rhs], [], BlockAST([]))
    block = Block(arg_types=[i32])
    ctx = EmitContext(builder=block, symbols={"x": block.args[0]}, types={})
    visitor = AstVisitor()

    result = visitor.visit_function(func_ast, ctx)
    assert result is None
    assert ctx.symbols["x"] is block.args[0]
    assert "y" not in ctx.symbols


# AV-005
# 创建者: 不要啊教练
# 最后一次更改: 不要啊教练
# 最近一次运行测试时间: 2026-03-22 14:59:58 +0800
# 最近一次运行成功时间: 2026-03-22 14:59:58 +0800
# 功能说明: 验证 visit_block 遇到未知 block 节点会抛出 AstVisitorError。
# 测试目的: 验证 visit_block 遇到未知 block 节点会抛出 AstVisitorError。
# 使用示例: pytest -q test/dsl/test_ast_visitor.py -k test_ast_visitor_rejects_block_without_statements
# 对应功能实现文件路径: kernel_gen/dsl/ast_visitor.py
# 对应 spec 文件路径: spec/dsl/ast_visitor.md
# 对应测试文件路径: test/dsl/test_ast_visitor.py
def test_ast_visitor_rejects_block_without_statements() -> None:
    class DummyBlock:
        def __init__(self: "DummyBlock") -> None:
            self.location = SourceLocation(1, 1)

    visitor = AstVisitor()
    ctx = EmitContext(builder=Block(arg_types=[]), symbols={}, types={})

    with pytest.raises(AstVisitorError) as exc_info:
        visitor.visit_block(DummyBlock(), ctx)
    assert "Unsupported block node" in str(exc_info.value)


# AV-006
# 创建者: 不要啊教练
# 最后一次更改: 不要啊教练
# 最近一次运行测试时间: 2026-03-22 14:59:58 +0800
# 最近一次运行成功时间: 2026-03-22 14:59:58 +0800
# 功能说明: 验证 visit_stmt 捕获 _LoweringError 并转为 AstVisitorError。
# 测试目的: 验证 visit_stmt 捕获 _LoweringError 并转为 AstVisitorError。
# 使用示例: pytest -q test/dsl/test_ast_visitor.py -k test_ast_visitor_visit_stmt_wraps_lowering_error
# 对应功能实现文件路径: kernel_gen/dsl/ast_visitor.py
# 对应 spec 文件路径: spec/dsl/ast_visitor.md
# 对应测试文件路径: test/dsl/test_ast_visitor.py
def test_ast_visitor_visit_stmt_wraps_lowering_error() -> None:
    visitor = AstVisitor()
    ctx = EmitContext(builder=Block(arg_types=[]), symbols={}, types={})
    node = BlockAST(statements=[], location=SourceLocation(3, 2))

    with pytest.raises(AstVisitorError) as exc_info:
        visitor.visit_stmt(node, ctx)
    assert exc_info.value.location == node.location


# EMIT-011
# 创建者: 不要啊教练
# 最后一次更改: 不要啊教练
# 最近一次运行测试时间: 2026-03-22 14:59:58 +0800
# 最近一次运行成功时间: 2026-03-22 14:59:58 +0800
# 功能说明: 验证 loop_vars 初始化与非法配置报错路径。
# 测试目的: 验证 loop_vars 初始化与非法配置报错路径。
# 使用示例: pytest -q test/dsl/test_ast_visitor.py -k test_emit_mlir_loop_vars_validation
# 对应功能实现文件路径: kernel_gen/dsl/emit_mlir.py
# 对应 spec 文件路径: spec/dsl/emit_mlir.md
# 对应测试文件路径: test/dsl/test_ast_visitor.py
def test_emit_mlir_loop_vars_validation() -> None:
    ctx = EmitContext(builder=Block(arg_types=[]), symbols={}, types={}, config=None)
    loop_vars = _get_loop_vars(ctx)
    assert isinstance(loop_vars, dict)

    bad_ctx = EmitContext(builder=Block(arg_types=[]), symbols={}, types={}, config={"loop_vars": []})
    with pytest.raises(_LoweringError):
        _get_loop_vars(bad_ctx)


# EMIT-012A
# 创建者: 不要啊教练
# 最后一次更改: 不要啊教练
# 最近一次运行测试时间: 2026-03-22 14:59:58 +0800
# 最近一次运行成功时间: 2026-03-22 14:59:58 +0800
# 功能说明: 覆盖索引解析与 rank mismatch 的错误路径。
# 测试目的: 覆盖索引解析与 rank mismatch 的错误路径。
# 使用示例: pytest -q test/dsl/test_ast_visitor.py -k test_emit_mlir_index_expr_rejections
# 对应功能实现文件路径: kernel_gen/dsl/emit_mlir.py
# 对应 spec 文件路径: spec/dsl/emit_mlir.md
# 对应测试文件路径: test/dsl/test_ast_visitor.py
def test_emit_mlir_index_expr_rejections() -> None:
    ctx = EmitContext(builder=Block(arg_types=[]), symbols={}, types={}, config={})

    with pytest.raises(_LoweringError):
        _resolve_index_expr(ConstAST(1.5, location=SourceLocation(1, 1)), ctx)

    with pytest.raises(_LoweringError):
        _resolve_index_expr(VarAST(name="i", location=SourceLocation(2, 1)), ctx)

    with pytest.raises(_LoweringError):
        _build_index_attrs([ConstAST(1, location=None)], rank=2, ctx=ctx, location=SourceLocation(3, 1))


# EMIT-013
# 创建者: 不要啊教练
# 最后一次更改: 不要啊教练
# 最近一次运行测试时间: 2026-03-22 14:59:58 +0800
# 最近一次运行成功时间: 2026-03-22 14:59:58 +0800
# 功能说明: 覆盖默认 stride 推导遇到非 IntAttr/StringAttr 的分支。
# 测试目的: 覆盖默认 stride 推导遇到非 IntAttr/StringAttr 的分支。
# 使用示例: pytest -q test/dsl/test_ast_visitor.py -k test_emit_mlir_default_stride_handles_unknown_attr
# 对应功能实现文件路径: kernel_gen/dsl/emit_mlir.py
# 对应 spec 文件路径: spec/dsl/emit_mlir.md
# 对应测试文件路径: test/dsl/test_ast_visitor.py
def test_emit_mlir_default_stride_handles_unknown_attr() -> None:
    attrs = _build_default_stride_attrs([ArrayAttr([])])
    assert len(attrs) == 1


# EMIT-012C
# 创建者: 小李飞刀
# 最后一次更改: 小李飞刀
# 最近一次运行测试时间: 2026-03-23 10:30:00 +0800
# 最近一次运行成功时间: 2026-03-23 10:30:00 +0800
# 功能说明: 覆盖 emit_mlir stride/index/layout 等辅助函数分支。
# 测试目的: 覆盖 stride 构造、layout 解析与静态索引处理的错误分支。
# 使用示例: pytest -q test/dsl/test_ast_visitor.py -k test_emit_mlir_stride_and_layout_helpers
# 对应功能实现文件路径: kernel_gen/dsl/emit_mlir.py
# 对应 spec 文件路径: spec/dsl/emit_mlir.md
# 对应测试文件路径: test/dsl/test_ast_visitor.py
def test_emit_mlir_stride_and_layout_helpers() -> None:
    assert _build_stride([2, "N"]) == [1, "?"]
    assert _mul_symbol(1, "N") == "N"
    assert _mul_symbol("M", 1) == "M"
    assert _mul_symbol("M", "N") == "M*N"

    stride_attrs = _build_default_stride_attrs([StringAttr("N"), IntAttr(2)])
    assert all(isinstance(item, (IntAttr, StringAttr)) for item in stride_attrs)

    ctx = EmitContext(builder=Block(arg_types=[]), symbols={}, types={})
    attrs = _build_index_attrs(ConstAST(1), rank=2, ctx=ctx, location=None)
    assert len(attrs) == 2

    with pytest.raises(_LoweringError, match="Unsupported layout attribute"):
        _build_index_operands_from_layout(ArrayAttr([ArrayAttr([])]), ctx, location=None)

    with pytest.raises(_LoweringError, match="Only unit stride is supported"):
        _build_stride_attrs([ConstAST(2)], rank=1, ctx=ctx, location=None)

    with pytest.raises(_LoweringError, match="Index must be int or str"):
        _resolve_static_index_expr(ConstAST(1.5))

    with pytest.raises(_LoweringError, match="Index rank mismatch"):
        _build_static_index_list([ConstAST(1)], rank=2, default_value=0, location=None)

    fallback = NnMemorySpaceAttr.from_name("global")
    assert _memory_space_from_ast(MemorySpace.LM, fallback).space.data == "local"


# EMIT-012D
# 创建者: 小李飞刀
# 最后一次更改: 小李飞刀
# 最近一次运行测试时间: 2026-03-23 10:30:00 +0800
# 最近一次运行成功时间: 2026-03-23 10:30:00 +0800
# 功能说明: 覆盖索引解析与 loop_vars 的分支。
# 测试目的: 覆盖 index cast、符号索引解析、loop_vars 查表路径。
# 使用示例: pytest -q test/dsl/test_ast_visitor.py -k test_emit_mlir_index_resolution_helpers
# 对应功能实现文件路径: kernel_gen/dsl/emit_mlir.py
# 对应 spec 文件路径: spec/dsl/emit_mlir.md
# 对应测试文件路径: test/dsl/test_ast_visitor.py
def test_emit_mlir_index_resolution_helpers() -> None:
    block = Block(arg_types=[i32, SymbolValueType.from_expr("N")])
    ctx = EmitContext(builder=block, symbols={"n": block.args[1]}, types={}, config={})

    cast_value = _ensure_index_value(block.args[0], ctx, location=None)
    assert isinstance(cast_value.owner, arith.IndexCastOp)

    with pytest.raises(_LoweringError, match="Unknown index symbol"):
        _resolve_index_symbol("missing", ctx, location=None)

    const_value = _resolve_index_operand(ConstAST(3), ctx, location=None)
    assert isinstance(const_value.owner, arith.ConstantOp)

    symbol_value = _resolve_index_operand(ConstAST("n"), ctx, location=None)
    assert symbol_value is block.args[1]

    assert _resolve_index_expr(ScalarArgAST(name="k", value_type=int), ctx) == "k"
    ctx.config["loop_vars"] = {"i": "i"}
    assert _resolve_index_expr(VarAST(name="i", location=None), ctx) == "i"
    with pytest.raises(_LoweringError, match="Unknown loop variable"):
        _resolve_index_expr(VarAST(name="j", location=None), ctx)


# EMIT-012
# 创建者: 小李飞刀
# 最后一次更改: 小李飞刀
# 最近一次运行测试时间: 2026-03-23 10:30:00 +0800
# 最近一次运行成功时间: 2026-03-23 10:30:00 +0800
# 功能说明: 覆盖 emit_mlir 类型推导与 broadcast 错误分支。
# 测试目的: 覆盖常量类型、symbol binary op、broadcast mismatch 等路径。
# 使用示例: pytest -q test/dsl/test_ast_visitor.py -k test_emit_mlir_infer_expr_type_branches
# 对应功能实现文件路径: kernel_gen/dsl/emit_mlir.py
# 对应 spec 文件路径: spec/dsl/emit_mlir.md
# 对应测试文件路径: test/dsl/test_ast_visitor.py
def test_emit_mlir_infer_expr_type_branches() -> None:
    memory = Memory([2, 2], NumericType.Float32)
    tensor = TensorAST(name="x", memory=memory, location=None)
    type_map = {_expr_key(tensor): _memory_to_nn_type(memory)}

    assert _infer_expr_type(ConstAST(1.5), type_map) == f32
    with pytest.raises(_LoweringError, match="Unsupported constant type"):
        _infer_expr_type(ConstAST("bad"), type_map)

    load = LoadAST(
        tensor=tensor,
        offset=[ConstAST(0), ConstAST(0)],
        stride=None,
        sizes=[ConstAST(1), ConstAST(1)],
        location=None,
    )
    load_type = _infer_expr_type(load, type_map)
    assert isinstance(load_type, NnMemoryType)
    assert [dim.data for dim in load_type.shape.data] == [1, 1]

    with pytest.raises(_LoweringError, match="StoreAST does not produce a value"):
        _infer_expr_type(StoreAST(tensor=tensor, offset=ConstAST(0), stride=None, value=tensor), type_map)

    with pytest.raises(_LoweringError, match="ForAST does not produce a value"):
        loop = ForAST(var=VarAST("i"), start=ConstAST(0), end=ConstAST(1), body=BlockAST([]))
        _infer_expr_type(loop, type_map)

    sym_lhs = ScalarArgAST("a", int, is_symbolic=True)
    sym_rhs = ScalarArgAST("b", int, is_symbolic=True)
    type_map[_expr_key(sym_lhs)] = SymbolValueType.from_expr("A")
    type_map[_expr_key(sym_rhs)] = SymbolValueType.from_expr("B")
    for op_name in ("add", "mul", "div", "floordiv"):
        assert isinstance(_infer_expr_type(BinaryExprAST(op=op_name, lhs=sym_lhs, rhs=sym_rhs), type_map), SymbolValueType)

    with pytest.raises(_LoweringError, match="Unsupported symbol binary op"):
        _infer_expr_type(BinaryExprAST(op="mod", lhs=sym_lhs, rhs=sym_rhs), type_map)

    type_map[_expr_key(sym_lhs)] = i32
    type_map[_expr_key(sym_rhs)] = i32
    with pytest.raises(_LoweringError, match="Binary op operands must have nn.memory type"):
        _infer_expr_type(BinaryExprAST(op="add", lhs=sym_lhs, rhs=sym_rhs), type_map)

    with pytest.raises(_LoweringError, match="Compare op operands must have nn.memory type"):
        _infer_expr_type(CompareExprAST(op="eq", lhs=sym_lhs, rhs=sym_rhs), type_map)

    lhs_type = _memory_to_nn_type(Memory([2, 1], NumericType.Float32))
    with pytest.raises(_LoweringError, match="Implicit broadcast dimension mismatch"):
        _infer_broadcast_shape([StringAttr("?")], [IntAttr(2)], location=None)

    rhs_type_mismatch = _memory_to_nn_type(Memory([2, 1], NumericType.Int32))
    with pytest.raises(_LoweringError, match="Binary op operands must have the same element_type"):
        _infer_broadcast_memory_type(lhs_type, rhs_type_mismatch, location=None)

    rhs_space = _memory_to_nn_type(Memory([2, 1], NumericType.Float32, space=MemorySpace.LM))
    with pytest.raises(_LoweringError, match="Binary op operands must have the same space"):
        _infer_broadcast_memory_type(lhs_type, rhs_space, location=None)

    with pytest.raises(_LoweringError, match="Unsupported expression for lowering"):
        _infer_expr_type(object(), type_map)


# EMIT-012B
# 创建者: 小李飞刀
# 最后一次更改: 小李飞刀
# 最近一次运行测试时间: 2026-03-23 10:30:00 +0800
# 最近一次运行成功时间: 2026-03-23 10:30:00 +0800
# 功能说明: 覆盖 emit_mlir lowering 的错误与支路。
# 测试目的: 覆盖常量、load/store、symbol binary op 与 compare 错误分支。
# 使用示例: pytest -q test/dsl/test_ast_visitor.py -k test_emit_mlir_lower_expr_branches
# 对应功能实现文件路径: kernel_gen/dsl/emit_mlir.py
# 对应 spec 文件路径: spec/dsl/emit_mlir.md
# 对应测试文件路径: test/dsl/test_ast_visitor.py
def test_emit_mlir_lower_expr_branches() -> None:
    memory = Memory([2, 2], NumericType.Float32)
    tensor = TensorAST(name="x", memory=memory, location=None)
    tensor_type = _memory_to_nn_type(memory)
    block = Block(arg_types=[tensor_type, SymbolValueType.from_expr("N")])
    ctx = EmitContext(builder=block, symbols={"x": block.args[0]}, types={})
    ctx._set_cache(_expr_key(tensor), block.args[0])
    ctx.types[_expr_key(tensor)] = tensor_type

    float_value = _lower_expr(ConstAST(1.5), ctx)
    assert isinstance(float_value.owner, arith.ConstantOp)

    with pytest.raises(_LoweringError, match="Unsupported constant type"):
        _lower_expr(ConstAST("bad"), ctx)

    load = LoadAST(
        tensor=tensor,
        offset=[ConstAST(0), ConstAST(0)],
        stride=None,
        sizes=[ConstAST(1), ConstAST(1)],
        location=None,
    )
    load_value = _lower_expr(load, ctx)
    assert isinstance(load_value.owner, DmaLoadOp)

    bad_load = LoadAST(tensor=tensor, offset=ConstAST(0), stride=None, location=None)
    ctx.types[_expr_key(bad_load)] = i32
    with pytest.raises(_LoweringError, match="LoadAST result must be nn.memory"):
        _lower_expr(bad_load, ctx)

    sym_lhs = ScalarArgAST("a", int, is_symbolic=True)
    sym_rhs = ScalarArgAST("b", int, is_symbolic=True)
    ctx._set_cache(_expr_key(sym_lhs), block.args[1])
    ctx._set_cache(_expr_key(sym_rhs), block.args[1])
    ctx.types[_expr_key(sym_lhs)] = block.args[1].type
    ctx.types[_expr_key(sym_rhs)] = block.args[1].type
    bad_symbol = BinaryExprAST(op="add", lhs=sym_lhs, rhs=sym_rhs)
    ctx.types[_expr_key(bad_symbol)] = i32
    with pytest.raises(_LoweringError, match="Symbol binary op result must be !symbol.int"):
        _lower_expr(bad_symbol, ctx)

    bad_binary = BinaryExprAST(op="mod", lhs=tensor, rhs=tensor)
    with pytest.raises(_LoweringError, match="Unsupported binary op"):
        _lower_expr(bad_binary, ctx)

    bad_compare = CompareExprAST(op="foo", lhs=tensor, rhs=tensor)
    with pytest.raises(_LoweringError, match="Unsupported compare op"):
        _lower_expr(bad_compare, ctx)

    with pytest.raises(_LoweringError, match="StoreAST does not produce a value"):
        _lower_expr(StoreAST(tensor=tensor, offset=ConstAST(0), stride=None, value=tensor), ctx)

    with pytest.raises(_LoweringError, match="Unknown input reference"):
        _lookup_symbol(VarAST("missing"), EmitContext(builder=block, symbols={}, types={}))


# EMIT-022
# 创建者: 小李飞刀
# 最后一次更改: 小李飞刀
# 最近一次运行测试时间: 2026-03-23 10:30:00 +0800
# 最近一次运行成功时间: 2026-03-23 10:30:00 +0800
# 功能说明: 覆盖 StoreAST rank mismatch 与 deslice 分支。
# 测试目的: 验证 StoreAST rank mismatch 抛错，sizes 路径生成 dma.deslice。
# 使用示例: pytest -q test/dsl/test_ast_visitor.py -k test_emit_mlir_store_rank_mismatch_and_deslice
# 对应功能实现文件路径: kernel_gen/dsl/emit_mlir.py
# 对应 spec 文件路径: spec/dsl/emit_mlir.md
# 对应测试文件路径: test/dsl/test_ast_visitor.py
def test_emit_mlir_store_rank_mismatch_and_deslice() -> None:
    target_memory = Memory([2, 2], NumericType.Float32)
    value_memory = Memory([2], NumericType.Float32)
    target = TensorAST(name="t", memory=target_memory, location=None)
    value = TensorAST(name="v", memory=value_memory, location=None)
    block = Block(arg_types=[_memory_to_nn_type(target_memory), _memory_to_nn_type(value_memory)])
    ctx = EmitContext(builder=block, symbols={"t": block.args[0], "v": block.args[1]}, types={})
    ctx._set_cache(_expr_key(target), block.args[0])
    ctx._set_cache(_expr_key(value), block.args[1])
    ctx.types[_expr_key(target)] = block.args[0].type
    ctx.types[_expr_key(value)] = block.args[1].type

    with pytest.raises(_LoweringError, match="Store source rank mismatch"):
        emit_node_mlir(
            StoreAST(tensor=target, offset=[ConstAST(0), ConstAST(0)], stride=None, value=value),
            ctx,
        )

    same_value = TensorAST(name="sv", memory=target_memory, location=None)
    ctx.symbols["sv"] = block.args[0]
    ctx._set_cache(_expr_key(same_value), block.args[0])
    ctx.types[_expr_key(same_value)] = block.args[0].type
    deslice = emit_node_mlir(
        StoreAST(
            tensor=target,
            offset=[ConstAST(0), ConstAST(0)],
            stride=None,
            sizes=[ConstAST(1), ConstAST(1)],
            value=same_value,
            kind="deslice",
        ),
        ctx,
    )
    assert isinstance(deslice, DmaDesliceOp)


# EMIT-023
# 创建者: 小李飞刀
# 最后一次更改: 小李飞刀
# 最近一次运行测试时间: 2026-03-23 10:30:00 +0800
# 最近一次运行成功时间: 2026-03-23 10:30:00 +0800
# 功能说明: 覆盖 _ensure_supported_statements 的错误分支。
# 测试目的: 验证空函数体与不支持语句会抛出明确错误。
# 使用示例: pytest -q test/dsl/test_ast_visitor.py -k test_emit_mlir_ensure_supported_statements_errors
# 对应功能实现文件路径: kernel_gen/dsl/emit_mlir.py
# 对应 spec 文件路径: spec/dsl/emit_mlir.md
# 对应测试文件路径: test/dsl/test_ast_visitor.py
def test_emit_mlir_ensure_supported_statements_errors() -> None:
    memory = Memory([2, 2], NumericType.Float32)
    tensor = TensorAST(name="x", memory=memory, location=None)
    empty_func = FunctionAST(name="empty", inputs=[tensor], outputs=[], body=BlockAST([]))
    with pytest.raises(_LoweringError, match="Function body is empty"):
        _ensure_supported_statements(empty_func)

    bad_func = FunctionAST(name="bad", inputs=[tensor], outputs=[], body=BlockAST([object()]))
    with pytest.raises(_LoweringError, match="Unsupported AST expression for lowering"):
        _ensure_supported_statements(bad_func)


# EMIT-013
# 创建者: 小李飞刀
# 最后一次更改: 小李飞刀
# 最近一次运行测试时间: 2026-03-23 05:10:36 +0800
# 最近一次运行成功时间: 2026-03-23 05:10:36 +0800
# 功能说明: 覆盖缓存恢复与索引类型分支。
# 测试目的: 验证缓存快照/恢复与 IndexType 输入的处理路径。
# 使用示例: pytest -q test/dsl/test_ast_visitor.py -k test_emit_mlir_cache_restore_and_index_value_variants
# 对应功能实现文件路径: kernel_gen/dsl/emit_mlir.py
# 对应 spec 文件路径: spec/dsl/emit_mlir.md
# 对应测试文件路径: test/dsl/test_ast_visitor.py
def test_emit_mlir_cache_restore_and_index_value_variants() -> None:
    block = Block(arg_types=[IndexType()])
    ctx = EmitContext(builder=block, symbols={}, types={})
    ctx._set_cache(1, "value")
    snapshot = ctx._snapshot_cache()
    ctx._set_cache(2, "new")
    ctx._restore_cache(snapshot)
    assert ctx._get_cache(1) == "value"
    assert ctx._get_cache(2) is None

    index_value = _ensure_index_value(block.args[0], ctx, location=None)
    assert index_value is block.args[0]

    float_op = arith.ConstantOp(FloatAttr(1.0, f32))
    with pytest.raises(_LoweringError, match="Index operand must be integer or index"):
        _ensure_index_value(float_op.result, ctx, location=None)


# EMIT-014
# 创建者: 小李飞刀
# 最后一次更改: 小李飞刀
# 最近一次运行测试时间: 2026-03-23 05:10:36 +0800
# 最近一次运行成功时间: 2026-03-23 05:10:36 +0800
# 功能说明: 覆盖索引解析与 loop bound 的分支。
# 测试目的: 验证索引解析错误路径、直接值与 loop bound 解析。
# 使用示例: pytest -q test/dsl/test_ast_visitor.py -k test_emit_mlir_index_operand_variants_and_loop_bound
# 对应功能实现文件路径: kernel_gen/dsl/emit_mlir.py
# 对应 spec 文件路径: spec/dsl/emit_mlir.md
# 对应测试文件路径: test/dsl/test_ast_visitor.py
def test_emit_mlir_index_operand_variants_and_loop_bound() -> None:
    block = Block(arg_types=[IndexType()])
    ctx = EmitContext(builder=block, symbols={"n": block.args[0]}, types={}, config={})

    with pytest.raises(_LoweringError, match="Index must be int or str"):
        _resolve_index_operand(ConstAST(1.5), ctx, location=None)

    const_value = _resolve_index_operand(2, ctx, location=None)
    assert isinstance(const_value.owner, arith.ConstantOp)

    symbol_value = _resolve_index_operand("n", ctx, location=None)
    assert symbol_value is block.args[0]

    assert _resolve_index_expr(ConstAST("k"), ctx) == "k"
    assert _resolve_index_expr(ConstAST(3), ctx) == 3

    scalar_arg = ScalarArgAST(name="n", value_type=int)
    bound_value = _lower_loop_bound(scalar_arg, ctx)
    assert bound_value is block.args[0]


# EMIT-015
# 创建者: 小李飞刀
# 最后一次更改: 小李飞刀
# 最近一次运行测试时间: 2026-03-23 05:10:36 +0800
# 最近一次运行成功时间: 2026-03-23 05:10:36 +0800
# 功能说明: 覆盖 layout 解析与 stride 校验分支。
# 测试目的: 验证 layout 支持 StringAttr 并拒绝非 unit stride。
# 使用示例: pytest -q test/dsl/test_ast_visitor.py -k test_emit_mlir_layout_and_stride_helpers
# 对应功能实现文件路径: kernel_gen/dsl/emit_mlir.py
# 对应 spec 文件路径: spec/dsl/emit_mlir.md
# 对应测试文件路径: test/dsl/test_ast_visitor.py
def test_emit_mlir_layout_and_stride_helpers() -> None:
    block = Block(arg_types=[IndexType()])
    ctx = EmitContext(builder=block, symbols={"n": block.args[0]}, types={}, config={})
    layout = ArrayAttr([IntAttr(0), StringAttr("n")])
    operands = _build_index_operands_from_layout(layout, ctx, location=None)
    assert len(operands) == 2
    assert isinstance(operands[0].owner, arith.ConstantOp)
    assert operands[1] is block.args[0]

    with pytest.raises(_LoweringError, match="Only unit stride is supported"):
        _build_stride_attrs([ConstAST(2)], rank=1, ctx=ctx, location=None)


# EMIT-016
# 创建者: 小李飞刀
# 最后一次更改: 小李飞刀
# 最近一次运行测试时间: 2026-03-23 05:10:36 +0800
# 最近一次运行成功时间: 2026-03-23 05:10:36 +0800
# 功能说明: 覆盖静态索引与广播形状推导分支。
# 测试目的: 验证静态索引列表构造与广播维度分支。
# 使用示例: pytest -q test/dsl/test_ast_visitor.py -k test_emit_mlir_static_index_list_and_broadcast_shape
# 对应功能实现文件路径: kernel_gen/dsl/emit_mlir.py
# 对应 spec 文件路径: spec/dsl/emit_mlir.md
# 对应测试文件路径: test/dsl/test_ast_visitor.py
def test_emit_mlir_static_index_list_and_broadcast_shape() -> None:
    assert _resolve_static_index_expr(4) == 4
    assert _resolve_static_index_expr("n") == "n"

    default_attrs = _build_static_index_list(None, rank=2, default_value=1, location=None)
    assert [attr.data for attr in default_attrs] == [1, 1]

    scalar_attrs = _build_static_index_list(ConstAST(2), rank=3, default_value=1, location=None)
    assert [attr.data for attr in scalar_attrs] == [2, 2, 2]

    lhs_shape = [IntAttr(2), IntAttr(3)]
    rhs_shape = [IntAttr(3)]
    assert _infer_broadcast_shape(lhs_shape, rhs_shape, None)[0].data == 2

    wildcard_shape = [StringAttr("?")]
    assert _infer_broadcast_shape(wildcard_shape, wildcard_shape, None)[0].data == "?"

    with pytest.raises(_LoweringError, match="Implicit broadcast dimension mismatch"):
        _infer_broadcast_shape([IntAttr(2)], [StringAttr("?")], None)

    broadcast = _infer_broadcast_shape([IntAttr(2)], [IntAttr(1)], None)
    assert broadcast[0].data == 2


# EMIT-017
# 创建者: 小李飞刀
# 最后一次更改: 小李飞刀
# 最近一次运行测试时间: 2026-03-23 05:10:36 +0800
# 最近一次运行成功时间: 2026-03-23 05:10:36 +0800
# 功能说明: 覆盖类型推导中的未知输入路径。
# 测试目的: 验证 LoadAST 与 TensorAST 未登记时的报错。
# 使用示例: pytest -q test/dsl/test_ast_visitor.py -k test_emit_mlir_infer_expr_type_unknown_inputs
# 对应功能实现文件路径: kernel_gen/dsl/emit_mlir.py
# 对应 spec 文件路径: spec/dsl/emit_mlir.md
# 对应测试文件路径: test/dsl/test_ast_visitor.py
def test_emit_mlir_infer_expr_type_unknown_inputs() -> None:
    memory = Memory([2], NumericType.Float32)
    tensor = TensorAST(name="x", memory=memory, location=None)
    load = LoadAST(tensor=tensor, offset=[ConstAST(0)], stride=None, location=None)
    with pytest.raises(_LoweringError, match="Unknown input reference"):
        _infer_expr_type(load, {})
    with pytest.raises(_LoweringError, match="Unknown input reference"):
        _infer_expr_type(tensor, {})


# EMIT-018
# 创建者: 小李飞刀
# 最后一次更改: 小李飞刀
# 最近一次运行测试时间: 2026-03-23 05:10:36 +0800
# 最近一次运行成功时间: 2026-03-23 05:10:36 +0800
# 功能说明: 覆盖 lowering 的错误路径与符号运算分支。
# 测试目的: 验证未知输入、符号运算非法 op 与不支持表达式报错。
# 使用示例: pytest -q test/dsl/test_ast_visitor.py -k test_emit_mlir_lower_expr_unknown_and_symbol_errors
# 对应功能实现文件路径: kernel_gen/dsl/emit_mlir.py
# 对应 spec 文件路径: spec/dsl/emit_mlir.md
# 对应测试文件路径: test/dsl/test_ast_visitor.py
def test_emit_mlir_lower_expr_unknown_and_symbol_errors() -> None:
    ctx = EmitContext(builder=Block(), symbols={}, types={})
    tensor = TensorAST(name="x", memory=Memory([2], NumericType.Float32), location=None)
    with pytest.raises(_LoweringError, match="Unknown input reference"):
        _lower_expr(tensor, ctx)

    block = Block(arg_types=[SymbolValueType.from_expr("N"), SymbolValueType.from_expr("M")])
    symbol_ctx = EmitContext(builder=block, symbols={"a": block.args[0], "b": block.args[1]}, types={})
    lhs = ScalarArgAST(name="a", value_type=int)
    rhs = ScalarArgAST(name="b", value_type=int)
    symbol_ctx._set_cache(_expr_key(lhs), block.args[0])
    symbol_ctx._set_cache(_expr_key(rhs), block.args[1])
    symbol_ctx.types[_expr_key(lhs)] = block.args[0].type
    symbol_ctx.types[_expr_key(rhs)] = block.args[1].type
    expr_cases = [
        (BinaryExprAST(lhs=lhs, rhs=rhs, op="sub", location=None), SymbolSubOp),
        (BinaryExprAST(lhs=lhs, rhs=rhs, op="mul", location=None), SymbolMulOp),
        (BinaryExprAST(lhs=lhs, rhs=rhs, op="div", location=None), SymbolDivOp),
        (BinaryExprAST(lhs=lhs, rhs=rhs, op="floordiv", location=None), SymbolFloorDivOp),
    ]
    for expr, op_type in expr_cases:
        lowered = _lower_expr(expr, symbol_ctx)
        assert isinstance(lowered.owner, op_type)

    with pytest.raises(_LoweringError, match="Unsupported symbol binary op"):
        _lower_expr(BinaryExprAST(lhs=lhs, rhs=rhs, op="mod", location=None), symbol_ctx)

    with pytest.raises(_LoweringError, match="Unsupported expression for lowering"):
        _lower_expr(object(), symbol_ctx)


# EMIT-019
# 创建者: 小李飞刀
# 最后一次更改: 小李飞刀
# 最近一次运行测试时间: 2026-03-23 05:10:36 +0800
# 最近一次运行成功时间: 2026-03-23 05:10:36 +0800
# 功能说明: 覆盖广播路径中 rhs 需要扩展的分支。
# 测试目的: 验证 binary/compare 的 rhs 广播与 dtype 产物。
# 使用示例: pytest -q test/dsl/test_ast_visitor.py -k test_emit_mlir_binary_compare_broadcast_rhs
# 对应功能实现文件路径: kernel_gen/dsl/emit_mlir.py
# 对应 spec 文件路径: spec/dsl/emit_mlir.md
# 对应测试文件路径: test/dsl/test_ast_visitor.py
def test_emit_mlir_binary_compare_broadcast_rhs() -> None:
    lhs_memory = Memory([2, 2], NumericType.Float32)
    rhs_memory = Memory([1, 2], NumericType.Float32)
    lhs = TensorAST(name="lhs", memory=lhs_memory, location=None)
    rhs = TensorAST(name="rhs", memory=rhs_memory, location=None)
    block = Block(arg_types=[_memory_to_nn_type(lhs_memory), _memory_to_nn_type(rhs_memory)])
    ctx = EmitContext(builder=block, symbols={"lhs": block.args[0], "rhs": block.args[1]}, types={})
    ctx._set_cache(_expr_key(lhs), block.args[0])
    ctx._set_cache(_expr_key(rhs), block.args[1])
    ctx.types[_expr_key(lhs)] = block.args[0].type
    ctx.types[_expr_key(rhs)] = block.args[1].type

    add_expr = BinaryExprAST(lhs=lhs, rhs=rhs, op="add", location=None)
    add_value = _lower_expr(add_expr, ctx)
    assert add_value.owner is not None
    assert any(isinstance(op, NnBroadcastOp) for op in block.ops)

    compare_expr = CompareExprAST(lhs=lhs, rhs=rhs, op="eq", location=None)
    compare_value = _lower_expr(compare_expr, ctx)
    assert compare_value.type.element_type == i1


# EMIT-020
# 创建者: 小李飞刀
# 最后一次更改: 小李飞刀
# 最近一次运行测试时间: 2026-03-23 05:10:36 +0800
# 最近一次运行成功时间: 2026-03-23 05:10:36 +0800
# 功能说明: 覆盖 for 循环的 loop_vars 恢复逻辑与错误分支。
# 测试目的: 验证 for 循环恢复已有 loop_vars 并拒绝不支持的节点。
# 使用示例: pytest -q test/dsl/test_ast_visitor.py -k test_emit_mlir_for_loop_restores_loop_vars_and_errors
# 对应功能实现文件路径: kernel_gen/dsl/emit_mlir.py
# 对应 spec 文件路径: spec/dsl/emit_mlir.md
# 对应测试文件路径: test/dsl/test_ast_visitor.py
def test_emit_mlir_for_loop_restores_loop_vars_and_errors() -> None:
    ctx = EmitContext(builder=Block(), symbols={}, types={}, config={"loop_vars": {"i": "outer"}})
    for_ast = ForAST(
        var=VarAST(name="i", location=None),
        start=ConstAST(0),
        end=ConstAST(2),
        body=BlockAST([ConstAST(1)]),
    )
    loop_op = emit_node_mlir(for_ast, ctx)
    assert loop_op is not None
    assert ctx.config["loop_vars"]["i"] == "outer"

    with pytest.raises(_LoweringError, match="BlockAST must be lowered via AstVisitor"):
        emit_node_mlir(BlockAST([]), ctx)

    func_ast = FunctionAST(
        name="fn",
        inputs=[TensorAST(name="x", memory=Memory([1], NumericType.Float32), location=None)],
        outputs=[],
        body=BlockAST([ConstAST(1)]),
    )
    with pytest.raises(_LoweringError, match="FunctionAST must be lowered via AstVisitor"):
        emit_node_mlir(func_ast, ctx)

    return_op = func.ReturnOp()
    assert emit_node_mlir(return_op, ctx) is return_op

    with pytest.raises(_LoweringError, match="Unsupported expression for lowering"):
        emit_node_mlir(object(), ctx)


# MLIR-015
# 创建者: 小李飞刀
# 最后一次更改: 小李飞刀
# 最近一次运行测试时间: 2026-03-23 05:10:36 +0800
# 最近一次运行成功时间: 2026-03-23 05:10:36 +0800
# 功能说明: 覆盖符号标量函数的输出判断。
# 测试目的: 验证无输出时仍被视为符号标量函数。
# 使用示例: pytest -q test/dsl/test_ast_visitor.py -k test_mlir_gen_symbol_scalar_function_no_outputs
# 对应功能实现文件路径: kernel_gen/dsl/mlir_gen.py
# 对应 spec 文件路径: spec/dsl/mlir_gen.md
# 对应测试文件路径: test/dsl/test_ast_visitor.py
def test_mlir_gen_symbol_scalar_function_no_outputs() -> None:
    func_ast = FunctionAST(
        name="sym",
        inputs=[ScalarArgAST(name="n", value_type=int)],
        outputs=[],
        body=BlockAST([ConstAST(1)]),
    )
    assert _is_symbol_scalar_function(func_ast) is True


# MLIR-016
# 创建者: 小李飞刀
# 最后一次更改: 小李飞刀
# 最近一次运行测试时间: 2026-03-23 05:10:36 +0800
# 最近一次运行成功时间: 2026-03-23 05:10:36 +0800
# 功能说明: 覆盖返回类型校验的空输出与标量分支。
# 测试目的: 验证无输出直接返回、标量返回的 i32 约束。
# 使用示例: pytest -q test/dsl/test_ast_visitor.py -k test_mlir_gen_validate_return_type_variants
# 对应功能实现文件路径: kernel_gen/dsl/mlir_gen.py
# 对应 spec 文件路径: spec/dsl/mlir_gen.md
# 对应测试文件路径: test/dsl/test_ast_visitor.py
def test_mlir_gen_validate_return_type_variants() -> None:
    no_output_ast = FunctionAST(
        name="noop",
        inputs=[TensorAST(name="x", memory=Memory([1], NumericType.Float32), location=None)],
        outputs=[],
        body=BlockAST([ConstAST(1)]),
    )
    _validate_return_type(no_output_ast, i32)

    scalar_output_ast = FunctionAST(
        name="scalar_out",
        inputs=[TensorAST(name="x", memory=Memory([1], NumericType.Float32), location=None)],
        outputs=[ScalarArgAST(name="r", value_type=int)],
        body=BlockAST([ConstAST(1)]),
    )
    _validate_return_type(scalar_output_ast, i32)


# MGEN-001B
# 创建者: 小李飞刀
# 最后一次更改: 朽木露琪亚
# 最近一次运行测试时间: 2026-03-25 17:10:00 +0800
# 最近一次运行成功时间: 2026-03-25 17:10:00 +0800
# 功能说明: 覆盖 build_func_op 对 builtins 与解析失败的处理。
# 测试目的: 验证非 dict builtins 作为解析环境补充可成功运行，且解析失败会收敛为 AstVisitorError。
# 使用示例: pytest -q test/dsl/test_ast_visitor.py -k test_mlir_gen_build_func_op_builtins_and_parse_error
# 对应功能实现文件路径: kernel_gen/dsl/mlir_gen.py
# 对应 spec 文件路径: spec/dsl/mlir_gen.md
# 对应测试文件路径: test/dsl/test_ast_visitor.py
def test_mlir_gen_build_func_op_builtins_and_parse_error() -> None:
    def add(x: "Tensor[f32, 2, 2]", y: "Tensor[f32, 2, 2]") -> "Tensor[f32, 2, 2]":
        return x + y

    func_op = build_func_op(add, _tensor_arg([2, 2]), _tensor_arg([2, 2]), builtins=object())
    assert isinstance(func_op, func.FuncOp)

    def bad(x: "Tensor[f32]") -> "Tensor[f32]":
        return x

    with pytest.raises(AstVisitorError, match="Tensor annotation missing dimensions"):
        build_func_op(bad, _tensor_arg([2]))
