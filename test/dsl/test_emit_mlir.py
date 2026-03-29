"""Emit MLIR visitor tests.

创建者: 小李飞刀
最后一次更改: 金铲铲大作战

功能说明:
- 覆盖 AstVisitor/emit_mlir 相关回归测试。

使用示例:
- pytest -q test/dsl/test_emit_mlir.py

覆盖率信息:
- 覆盖率命令: coverage run -m pytest -q test/dsl/test_emit_mlir.py && coverage report --include=kernel_gen/dsl/ast_visitor.py,kernel_gen/dsl/emit_mlir.py -m
- 覆盖率结果: 未统计（待补充）
- 达标线: 95%

关联文件:
- 功能实现: kernel_gen/dsl/ast_visitor.py, kernel_gen/dsl/emit_mlir.py
- Spec 文档: spec/dsl/ast_visitor.md, spec/dsl/emit_mlir.md
- 测试文件: test/dsl/test_emit_mlir.py
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
from kernel_gen.dialect.arch import (
    ArchGetBlockIdOp,
    ArchGetBlockNumOp,
    ArchGetSubthreadIdOp,
    ArchGetSubthreadNumOp,
    ArchGetThreadIdOp,
)
from kernel_gen.dialect.nn import (
    NnAddOp,
    NnBroadcastOp,
    NnEqOp,
    NnMemorySpaceAttr,
    NnMemoryType,
    NnNeOp,
    NnSubOp,
    NnTrueDivOp,
)
from kernel_gen.dialect.symbol import (
    SymbolAddOp,
    SymbolDivOp,
    SymbolFloorDivOp,
    SymbolForOp,
    SymbolGeOp,
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


# EMIT-022A
# 创建者: 我不是牛马
# 最后一次更改: 我不是牛马
# 最近一次运行测试时间: 2026-03-25 21:25:58 +0800
# 最近一次运行成功时间: 2026-03-25 21:25:58 +0800
# 功能说明: 验证 ArchQueryAST(query_name=\"get_block_id\") lowering 为 arch.get_block_id。
# 测试目的: 锁定 emit_mlir 对最小 arch 查询入口的发射语义与结果类型。
# 使用示例: pytest -q test/dsl/test_emit_mlir.py -k test_emit_mlir_lowers_arch_get_block_id_query
# 对应功能实现文件路径: kernel_gen/dsl/emit_mlir.py
# 对应 spec 文件路径: spec/dsl/emit_mlir.md
# 对应测试文件路径: test/dsl/test_emit_mlir.py
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


# EMIT-023A
# 创建者: 咯咯咯
# 最后一次更改: 咯咯咯
# 最近一次运行测试时间: 2026-03-26 00:27:39 +0800
# 最近一次运行成功时间: 2026-03-26 00:27:39 +0800
# 功能说明: 验证 ArchQueryAST(query_name="get_block_num") lowering 为 arch.get_block_num。
# 测试目的: 锁定 emit_mlir 对 get_block_num 查询的发射语义与结果类型。
# 使用示例: pytest -q test/dsl/test_emit_mlir.py -k test_emit_mlir_lowers_arch_get_block_num_query
# 对应功能实现文件路径: kernel_gen/dsl/emit_mlir.py
# 对应 spec 文件路径: spec/dsl/emit_mlir.md
# 对应测试文件路径: test/dsl/test_emit_mlir.py
def test_emit_mlir_lowers_arch_get_block_num_query() -> None:
    block = Block()
    ctx = EmitContext(builder=block, symbols={}, types={})

    result = emit_node_mlir(ArchQueryAST(query_name="get_block_num"), ctx)

    body_ops = list(block.ops)
    if len(body_ops) != 1:
        raise AssertionError("expected one emitted op for get_block_num query")
    if not isinstance(body_ops[0], ArchGetBlockNumOp):
        raise AssertionError("expected emitted op to be ArchGetBlockNumOp")
    if result.type != SymbolValueType.from_expr("block_num"):
        raise AssertionError('expected emitted result type to be !symbol.int<"block_num">')


# EMIT-025
# 创建者: 我不是牛马
# 最后一次更改: 我不是牛马
# 最近一次运行测试时间: 2026-03-25 21:41:29 +0800
# 最近一次运行成功时间: 2026-03-25 21:41:29 +0800
# 功能说明: 验证 ArchQueryAST(query_name="get_subthread_id") lowering 为 arch.get_subthread_id。
# 测试目的: 锁定 emit_mlir 对 get_subthread_id 查询的发射语义与结果类型。
# 使用示例: pytest -q test/dsl/test_emit_mlir.py -k test_emit_mlir_lowers_arch_get_subthread_id_query
# 对应功能实现文件路径: kernel_gen/dsl/emit_mlir.py
# 对应 spec 文件路径: spec/dsl/emit_mlir.md
# 对应测试文件路径: test/dsl/test_emit_mlir.py
def test_emit_mlir_lowers_arch_get_subthread_id_query() -> None:
    block = Block()
    ctx = EmitContext(builder=block, symbols={}, types={})

    result = emit_node_mlir(ArchQueryAST(query_name="get_subthread_id"), ctx)

    body_ops = list(block.ops)
    if len(body_ops) != 1:
        raise AssertionError("expected one emitted op for get_subthread_id query")
    if not isinstance(body_ops[0], ArchGetSubthreadIdOp):
        raise AssertionError("expected emitted op to be ArchGetSubthreadIdOp")
    if result.type != SymbolValueType.from_expr("subthread_id"):
        raise AssertionError('expected emitted result type to be !symbol.int<"subthread_id">')


# EMIT-026
# 创建者: 朽木露琪亚
# 最后一次更改: 朽木露琪亚
# 最近一次运行测试时间: 2026-03-27 01:38:30 +0800
# 最近一次运行成功时间: 2026-03-27 01:38:30 +0800
# 功能说明: 验证 ArchQueryAST(query_name="get_thread_id") lowering 为 arch.get_thread_id。
# 测试目的: 锁定 emit_mlir 对 get_thread_id 查询的发射语义与结果类型。
# 使用示例: pytest -q test/dsl/test_emit_mlir.py -k test_emit_mlir_lowers_arch_get_thread_id_query
# 对应功能实现文件路径: kernel_gen/dsl/emit_mlir.py
# 对应 spec 文件路径: spec/dsl/emit_mlir.md
# 对应测试文件路径: test/dsl/test_emit_mlir.py
def test_emit_mlir_lowers_arch_get_thread_id_query() -> None:
    block = Block()
    ctx = EmitContext(builder=block, symbols={}, types={})

    result = emit_node_mlir(ArchQueryAST(query_name="get_thread_id"), ctx)

    body_ops = list(block.ops)
    if len(body_ops) != 1:
        raise AssertionError("expected one emitted op for get_thread_id query")
    if not isinstance(body_ops[0], ArchGetThreadIdOp):
        raise AssertionError("expected emitted op to be ArchGetThreadIdOp")
    if result.type != SymbolValueType.from_expr("thread_id"):
        raise AssertionError('expected emitted result type to be !symbol.int<"thread_id">')


# EMIT-027
# 创建者: 摸鱼小分队
# 最后一次更改: 摸鱼小分队
# 最近一次运行测试时间: 2026-03-27 02:08:59 +0800
# 最近一次运行成功时间: 2026-03-27 02:08:59 +0800
# 功能说明: 验证 ArchQueryAST(query_name="get_subthread_num") lowering 为 arch.get_subthread_num。
# 测试目的: 锁定 emit_mlir 对 get_subthread_num 查询的发射语义与结果类型。
# 使用示例: pytest -q test/dsl/test_emit_mlir.py -k test_emit_mlir_lowers_arch_get_subthread_num_query
# 对应功能实现文件路径: kernel_gen/dsl/emit_mlir.py
# 对应 spec 文件路径: spec/dsl/emit_mlir.md
# 对应测试文件路径: test/dsl/test_emit_mlir.py
def test_emit_mlir_lowers_arch_get_subthread_num_query() -> None:
    block = Block()
    ctx = EmitContext(builder=block, symbols={}, types={})

    result = emit_node_mlir(ArchQueryAST(query_name="get_subthread_num"), ctx)

    body_ops = list(block.ops)
    if len(body_ops) != 1:
        raise AssertionError("expected one emitted op for get_subthread_num query")
    if not isinstance(body_ops[0], ArchGetSubthreadNumOp):
        raise AssertionError("expected emitted op to be ArchGetSubthreadNumOp")
    if result.type != SymbolValueType.from_expr("subthread_num"):
        raise AssertionError('expected emitted result type to be !symbol.int<"subthread_num">')


# EMIT-001
# 创建者: 朽木露琪亚
# 最后一次更改: 金铲铲大作战
# 最近一次运行测试时间: 2026-03-22 14:59:58 +0800
# 最近一次运行成功时间: 2026-03-22 14:59:58 +0800
# 功能说明: 验证二元表达式节点生成对应 op/value 并复用缓存。
# 测试目的: 验证二元表达式节点生成对应 op/value 并复用缓存。
# 使用示例: pytest -q test/dsl/test_emit_mlir.py -k test_emit_context_reuses_cached_value
# 对应功能实现文件路径: kernel_gen/dsl/emit_mlir.py
# 对应 spec 文件路径: spec/dsl/emit_mlir.md
# 对应测试文件路径: test/dsl/test_emit_mlir.py
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
# 使用示例: pytest -q test/dsl/test_emit_mlir.py -k test_emit_mlir_tensor_uses_symbol_table
# 对应功能实现文件路径: kernel_gen/dsl/emit_mlir.py
# 对应 spec 文件路径: spec/dsl/emit_mlir.md
# 对应测试文件路径: test/dsl/test_emit_mlir.py
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
# 使用示例: pytest -q test/dsl/test_emit_mlir.py -k test_emit_mlir_compare_expr_emits_eq
# 对应功能实现文件路径: kernel_gen/dsl/emit_mlir.py
# 对应 spec 文件路径: spec/dsl/emit_mlir.md
# 对应测试文件路径: test/dsl/test_emit_mlir.py
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
# 使用示例: pytest -q test/dsl/test_emit_mlir.py -k test_emit_mlir_unsupported_node_reports_location
# 对应功能实现文件路径: kernel_gen/dsl/emit_mlir.py
# 对应 spec 文件路径: spec/dsl/emit_mlir.md
# 对应测试文件路径: test/dsl/test_emit_mlir.py
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
# 使用示例: pytest -q test/dsl/test_emit_mlir.py -k test_ast_visitor_visit_block_preserves_order
# 对应功能实现文件路径: kernel_gen/dsl/ast_visitor.py
# 对应 spec 文件路径: spec/dsl/ast_visitor.md
# 对应测试文件路径: test/dsl/test_emit_mlir.py
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
# 使用示例: pytest -q test/dsl/test_emit_mlir.py -k test_ast_visitor_reuses_expression_value
# 对应功能实现文件路径: kernel_gen/dsl/ast_visitor.py
# 对应 spec 文件路径: spec/dsl/ast_visitor.md
# 对应测试文件路径: test/dsl/test_emit_mlir.py
def test_ast_visitor_reuses_expression_value() -> None:
    memory = Memory([2, 2], NumericType.Float32)
    lhs = TensorAST(name="x", memory=memory, location=None)
    rhs = TensorAST(name="y", memory=memory, location=None)
    expr = BinaryExprAST(op="add", lhs=lhs, rhs=rhs, location=None)
    func_ast = FunctionAST(name="reuse", inputs=[lhs, rhs], outputs=[], body=BlockAST([expr, expr]))

    func_op = build_func_op_from_ast(func_ast)
    ops = [op for op in func_op.body.block.ops if isinstance(op, NnAddOp)]
    assert len(ops) == 1


# AV-003
# 创建者: 小李飞刀
# 最后一次更改: 金铲铲大作战
# 最近一次运行测试时间: 2026-03-22 14:59:58 +0800
# 最近一次运行成功时间: 2026-03-22 14:59:58 +0800
# 功能说明: 验证不支持语句/表达式时抛 AstVisitorError 并携带位置信息。
# 测试目的: 验证不支持语句/表达式时抛 AstVisitorError 并携带位置信息。
# 使用示例: pytest -q test/dsl/test_emit_mlir.py -k test_lowering_failure_reports_diagnostics
# 对应功能实现文件路径: kernel_gen/dsl/ast_visitor.py
# 对应 spec 文件路径: spec/dsl/ast_visitor.md
# 对应测试文件路径: test/dsl/test_emit_mlir.py
def test_lowering_failure_reports_diagnostics() -> None:
    def bad(x: "Tensor[f32, 2, 2]") -> "Tensor[f32, 2, 2]":
        return x + 1

    with pytest.raises(AstVisitorError) as exc_info:
        build_func_op(bad, _tensor_arg([2, 2]))
    assert exc_info.value.location is not None


# EMIT-005
# 创建者: 小李飞刀
# 最后一次更改: 小李飞刀
# 最近一次运行测试时间: 2026-03-18 10:56:41 +0800
# 最近一次运行成功时间: 2026-03-18 10:56:41 +0800
# 功能说明: 验证 LoadAST lowering 生成 dma.load。
# 测试目的: 验证 LoadAST lowering 生成 dma.load。
# 使用示例: pytest -q test/dsl/test_emit_mlir.py -k test_load_ast_lowering_rejected
# 对应功能实现文件路径: kernel_gen/dsl/emit_mlir.py
# 对应 spec 文件路径: spec/dsl/emit_mlir.md
# 对应测试文件路径: test/dsl/test_emit_mlir.py
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
# 使用示例: pytest -q test/dsl/test_emit_mlir.py -k test_store_ast_lowering_rejected
# 对应功能实现文件路径: kernel_gen/dsl/emit_mlir.py
# 对应 spec 文件路径: spec/dsl/emit_mlir.md
# 对应测试文件路径: test/dsl/test_emit_mlir.py
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
# 使用示例: pytest -q test/dsl/test_emit_mlir.py -k test_load_ast_lowering_raises_lowering_error
# 对应功能实现文件路径: kernel_gen/dsl/emit_mlir.py
# 对应 spec 文件路径: spec/dsl/emit_mlir.md
# 对应测试文件路径: test/dsl/test_emit_mlir.py
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
# 使用示例: pytest -q test/dsl/test_emit_mlir.py -k test_load_ast_index_rank_mismatch_reports_location
# 对应功能实现文件路径: kernel_gen/dsl/emit_mlir.py
# 对应 spec 文件路径: spec/dsl/emit_mlir.md
# 对应测试文件路径: test/dsl/test_emit_mlir.py
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
# 使用示例: pytest -q test/dsl/test_emit_mlir.py -k test_store_ast_lowering_raises_lowering_error
# 对应功能实现文件路径: kernel_gen/dsl/emit_mlir.py
# 对应 spec 文件路径: spec/dsl/emit_mlir.md
# 对应测试文件路径: test/dsl/test_emit_mlir.py
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
# 使用示例: pytest -q test/dsl/test_emit_mlir.py -k test_for_ast_lowering_emits_loads
# 对应功能实现文件路径: kernel_gen/dsl/emit_mlir.py
# 对应 spec 文件路径: spec/dsl/emit_mlir.md
# 对应测试文件路径: test/dsl/test_emit_mlir.py
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
# 最后一次更改: 金铲铲大作战
# 最近一次运行测试时间: 2026-03-26 21:43:31 +0800
# 最近一次运行成功时间: 2026-03-26 21:43:31 +0800
# 功能说明: 验证符号边界 ForAST lowering 为 symbol.for 并直接复用 symbol.int 作为 DMA operand。
# 测试目的: 验证符号边界 ForAST lowering 为 symbol.for 并直接复用 symbol.int 作为 DMA operand。
# 使用示例: pytest -q test/dsl/test_emit_mlir.py -k test_emit_mlir_symbolic_for_loop_avoids_index_cast
# 对应功能实现文件路径: kernel_gen/dsl/emit_mlir.py
# 对应 spec 文件路径: spec/dsl/emit_mlir.md
# 对应测试文件路径: test/dsl/test_emit_mlir.py
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
    assert isinstance(loop_ops[0].body.block.args[0].type, SymbolValueType)
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
# 使用示例: pytest -q test/dsl/test_emit_mlir.py -k test_emit_mlir_dma_alloc_lowering
# 对应功能实现文件路径: kernel_gen/dsl/emit_mlir.py
# 对应 spec 文件路径: spec/dsl/emit_mlir.md
# 对应测试文件路径: test/dsl/test_emit_mlir.py
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
# 使用示例: pytest -q test/dsl/test_emit_mlir.py -k test_emit_mlir_dma_copy_lowering
# 对应功能实现文件路径: kernel_gen/dsl/emit_mlir.py
# 对应 spec 文件路径: spec/dsl/emit_mlir.md
# 对应测试文件路径: test/dsl/test_emit_mlir.py
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
# 使用示例: pytest -q test/dsl/test_emit_mlir.py -k test_emit_mlir_dma_cast_lowering
# 对应功能实现文件路径: kernel_gen/dsl/emit_mlir.py
# 对应 spec 文件路径: spec/dsl/emit_mlir.md
# 对应测试文件路径: test/dsl/test_emit_mlir.py
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
# 使用示例: pytest -q test/dsl/test_emit_mlir.py -k test_emit_mlir_dma_view_lowering
# 对应功能实现文件路径: kernel_gen/dsl/emit_mlir.py
# 对应 spec 文件路径: spec/dsl/emit_mlir.md
# 对应测试文件路径: test/dsl/test_emit_mlir.py
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
# 使用示例: pytest -q test/dsl/test_emit_mlir.py -k test_emit_mlir_dma_reshape_lowering
# 对应功能实现文件路径: kernel_gen/dsl/emit_mlir.py
# 对应 spec 文件路径: spec/dsl/emit_mlir.md
# 对应测试文件路径: test/dsl/test_emit_mlir.py
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
# 使用示例: pytest -q test/dsl/test_emit_mlir.py -k test_emit_mlir_dma_flatten_lowering
# 对应功能实现文件路径: kernel_gen/dsl/emit_mlir.py
# 对应 spec 文件路径: spec/dsl/emit_mlir.md
# 对应测试文件路径: test/dsl/test_emit_mlir.py
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
# 使用示例: pytest -q test/dsl/test_emit_mlir.py -k test_emit_mlir_dma_free_statement
# 对应功能实现文件路径: kernel_gen/dsl/emit_mlir.py
# 对应 spec 文件路径: spec/dsl/emit_mlir.md
# 对应测试文件路径: test/dsl/test_emit_mlir.py
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


# MGEN-034 / EMIT-028
# 创建者: 我不是牛马
# 最后一次更改: 我不是牛马
# 最近一次运行测试时间: 2026-03-27 04:16:44 +0800
# 最近一次运行成功时间: 2026-03-27 04:16:44 +0800
# 功能说明: 验证 nn.sub dtype promotion 会插入 dma.cast 并返回目标 dtype 的 nn.sub。
# 测试目的: 锁定 build_func_op 对 nn.sub 混合 dtype 的 cast lowering 与返回类型。
# 使用示例: pytest -q test/dsl/test_emit_mlir.py -k test_build_func_op_lowers_nn_sub_dtype_promotion_with_cast
# 对应功能实现文件路径: kernel_gen/dsl/mlir_gen.py, kernel_gen/dsl/emit_mlir.py
# 对应 spec 文件路径: spec/dsl/mlir_gen.md, spec/dsl/emit_mlir.md
# 对应测试文件路径: test/dsl/test_emit_mlir.py
def test_build_func_op_lowers_nn_sub_dtype_promotion_with_cast() -> None:
    def sub(
        lhs: "Tensor[f32, 2, 2]",
        rhs: "Tensor[i32, 2, 2]",
    ) -> "Tensor[f32, 2, 2]":
        return lhs - rhs

    lhs_memory = Memory([2, 2], NumericType.Float32)
    rhs_memory = Memory([2, 2], NumericType.Int32)
    expected_type = _memory_to_nn_type(lhs_memory - rhs_memory)

    func_op = build_func_op(sub, lhs_memory, rhs_memory)
    cast_ops = [op for op in func_op.body.block.ops if isinstance(op, DmaCastOp)]
    sub_ops = [op for op in func_op.body.block.ops if isinstance(op, NnSubOp)]
    return_ops = [op for op in func_op.body.block.ops if isinstance(op, func.ReturnOp)]

    assert len(cast_ops) == 1
    assert len(sub_ops) == 1
    assert len(return_ops) == 1
    assert cast_ops[0].result.type == expected_type
    assert sub_ops[0].result.type == expected_type
    assert return_ops[0].arguments[0].type == expected_type

# AV-004
# 创建者: 不要啊教练
# 最后一次更改: 不要啊教练
# 最近一次运行测试时间: 2026-03-22 14:59:58 +0800
# 最近一次运行成功时间: 2026-03-22 14:59:58 +0800
# 功能说明: 覆盖 AstVisitor.visit_function 的符号表命中与跳过分支。
# 测试目的: 覆盖 AstVisitor.visit_function 的符号表命中与跳过分支。
# 使用示例: pytest -q test/dsl/test_emit_mlir.py -k test_ast_visitor_visit_function_skips_unbound_input
# 对应功能实现文件路径: kernel_gen/dsl/ast_visitor.py
# 对应 spec 文件路径: spec/dsl/ast_visitor.md
# 对应测试文件路径: test/dsl/test_emit_mlir.py
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
# 使用示例: pytest -q test/dsl/test_emit_mlir.py -k test_ast_visitor_rejects_block_without_statements
# 对应功能实现文件路径: kernel_gen/dsl/ast_visitor.py
# 对应 spec 文件路径: spec/dsl/ast_visitor.md
# 对应测试文件路径: test/dsl/test_emit_mlir.py
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
# 使用示例: pytest -q test/dsl/test_emit_mlir.py -k test_ast_visitor_visit_stmt_wraps_lowering_error
# 对应功能实现文件路径: kernel_gen/dsl/ast_visitor.py
# 对应 spec 文件路径: spec/dsl/ast_visitor.md
# 对应测试文件路径: test/dsl/test_emit_mlir.py
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
# 使用示例: pytest -q test/dsl/test_emit_mlir.py -k test_emit_mlir_loop_vars_validation
# 对应功能实现文件路径: kernel_gen/dsl/emit_mlir.py
# 对应 spec 文件路径: spec/dsl/emit_mlir.md
# 对应测试文件路径: test/dsl/test_emit_mlir.py
def test_emit_mlir_loop_vars_validation() -> None:
    ctx = EmitContext(builder=Block(arg_types=[]), symbols={}, types={}, config=None)
    loop_vars = _get_loop_vars(ctx)
    assert isinstance(loop_vars, dict)

    bad_ctx = EmitContext(builder=Block(arg_types=[]), symbols={}, types={}, config={"loop_vars": []})
    with pytest.raises(_LoweringError):
        _get_loop_vars(bad_ctx)


# EMIT-011B
# 创建者: 小李飞刀
# 最后一次更改: 小李飞刀
# 最近一次运行测试时间: 2026-03-28 20:10:00 +0800
# 最近一次运行成功时间: 2026-03-28 20:10:00 +0800
# 功能说明: 验证 EmitContext 对非法 target 配置的报错路径。
# 测试目的: 覆盖 config.target 未满足 target registry 命名约束时的异常路径。
# 使用示例: pytest -q test/dsl/test_emit_mlir.py -k test_emit_context_rejects_invalid_target_name
# 对应功能实现文件路径: kernel_gen/dsl/emit_mlir.py
# 对应 spec 文件路径: spec/dsl/emit_mlir.md, spec/target/registry.md
# 对应测试文件路径: test/dsl/test_emit_mlir.py
def test_emit_context_rejects_invalid_target_name() -> None:
    with pytest.raises(_LoweringError) as exc_info:
        EmitContext(
            builder=Block(arg_types=[]),
            symbols={},
            types={},
            config={"target": "Bad-Name"},
        )
    assert "target name must match" in str(exc_info.value)


# EMIT-011C
# 创建者: 小李飞刀
# 最后一次更改: 小李飞刀
# 最近一次运行测试时间: 2026-03-28 20:10:00 +0800
# 最近一次运行成功时间: 2026-03-28 20:10:00 +0800
# 功能说明: 验证 EmitContext 对非法 hardware 配置的报错路径。
# 测试目的: 覆盖 config.hardware 未满足 target registry 字段约束时的异常路径。
# 使用示例: pytest -q test/dsl/test_emit_mlir.py -k test_emit_context_rejects_invalid_hardware_field
# 对应功能实现文件路径: kernel_gen/dsl/emit_mlir.py
# 对应 spec 文件路径: spec/dsl/emit_mlir.md, spec/target/registry.md
# 对应测试文件路径: test/dsl/test_emit_mlir.py
def test_emit_context_rejects_invalid_hardware_field() -> None:
    with pytest.raises(_LoweringError) as exc_info:
        EmitContext(
            builder=Block(arg_types=[]),
            symbols={},
            types={},
            config={"hardware": {"bad_key": 1}},
        )
    assert "hardware has unknown key" in str(exc_info.value)


# EMIT-012A
# 创建者: 不要啊教练
# 最后一次更改: 不要啊教练
# 最近一次运行测试时间: 2026-03-22 14:59:58 +0800
# 最近一次运行成功时间: 2026-03-22 14:59:58 +0800
# 功能说明: 覆盖索引解析与 rank mismatch 的错误路径。
# 测试目的: 覆盖索引解析与 rank mismatch 的错误路径。
# 使用示例: pytest -q test/dsl/test_emit_mlir.py -k test_emit_mlir_index_expr_rejections
# 对应功能实现文件路径: kernel_gen/dsl/emit_mlir.py
# 对应 spec 文件路径: spec/dsl/emit_mlir.md
# 对应测试文件路径: test/dsl/test_emit_mlir.py
def test_emit_mlir_index_expr_rejections() -> None:
    ctx = EmitContext(builder=Block(arg_types=[]), symbols={}, types={}, config={})

    with pytest.raises(_LoweringError):
        _resolve_index_expr(ConstAST(1.5, location=SourceLocation(1, 1)), ctx)

    with pytest.raises(_LoweringError):
        _resolve_index_expr(VarAST(name="i", location=SourceLocation(2, 1)), ctx)

    with pytest.raises(_LoweringError):
        _build_index_attrs([ConstAST(1, location=None)], rank=2, ctx=ctx, location=SourceLocation(3, 1))


# EMIT-013A
# 创建者: 不要啊教练
# 最后一次更改: 不要啊教练
# 最近一次运行测试时间: 2026-03-22 14:59:58 +0800
# 最近一次运行成功时间: 2026-03-22 14:59:58 +0800
# 功能说明: 覆盖默认 stride 推导遇到非 IntAttr/StringAttr 的分支。
# 测试目的: 覆盖默认 stride 推导遇到非 IntAttr/StringAttr 的分支。
# 使用示例: pytest -q test/dsl/test_emit_mlir.py -k test_emit_mlir_default_stride_handles_unknown_attr
# 对应功能实现文件路径: kernel_gen/dsl/emit_mlir.py
# 对应 spec 文件路径: spec/dsl/emit_mlir.md
# 对应测试文件路径: test/dsl/test_emit_mlir.py
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
# 使用示例: pytest -q test/dsl/test_emit_mlir.py -k test_emit_mlir_stride_and_layout_helpers
# 对应功能实现文件路径: kernel_gen/dsl/emit_mlir.py
# 对应 spec 文件路径: spec/dsl/emit_mlir.md
# 对应测试文件路径: test/dsl/test_emit_mlir.py
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
# 使用示例: pytest -q test/dsl/test_emit_mlir.py -k test_emit_mlir_index_resolution_helpers
# 对应功能实现文件路径: kernel_gen/dsl/emit_mlir.py
# 对应 spec 文件路径: spec/dsl/emit_mlir.md
# 对应测试文件路径: test/dsl/test_emit_mlir.py
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
# 最后一次更改: 我不是牛马
# 最近一次运行测试时间: 2026-03-26 22:20:00 +0800
# 最近一次运行成功时间: 2026-03-26 22:20:00 +0800
# 功能说明: 覆盖 emit_mlir 类型推导与 broadcast 错误分支。
# 测试目的: 覆盖常量类型、symbol binary op、broadcast mismatch 等路径。
# 使用示例: pytest -q test/dsl/test_emit_mlir.py -k test_emit_mlir_infer_expr_type_branches
# 对应功能实现文件路径: kernel_gen/dsl/emit_mlir.py
# 对应 spec 文件路径: spec/dsl/emit_mlir.md
# 对应测试文件路径: test/dsl/test_emit_mlir.py
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
    binary_exprs: list[BinaryExprAST] = []
    for op_name in ("add", "mul", "div", "floordiv"):
        expr = BinaryExprAST(op=op_name, lhs=sym_lhs, rhs=sym_rhs)
        binary_exprs.append(expr)
        assert isinstance(_infer_expr_type(expr, type_map), SymbolValueType)

    with pytest.raises(_LoweringError, match="Unsupported symbol binary op"):
        _infer_expr_type(BinaryExprAST(op="mod", lhs=sym_lhs, rhs=sym_rhs), type_map)

    assert _infer_expr_type(CompareExprAST(op="eq", lhs=sym_lhs, rhs=sym_rhs), type_map) == i1
    assert _infer_expr_type(CompareExprAST(op="ge", lhs=sym_lhs, rhs=sym_rhs), type_map) == i1
    with pytest.raises(_LoweringError, match="Unsupported symbol compare op"):
        _infer_expr_type(CompareExprAST(op="gt", lhs=sym_lhs, rhs=sym_rhs), type_map)

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
# 使用示例: pytest -q test/dsl/test_emit_mlir.py -k test_emit_mlir_lower_expr_branches
# 对应功能实现文件路径: kernel_gen/dsl/emit_mlir.py
# 对应 spec 文件路径: spec/dsl/emit_mlir.md
# 对应测试文件路径: test/dsl/test_emit_mlir.py
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


# EMIT-022A
# 创建者: 小李飞刀
# 最后一次更改: 小李飞刀
# 最近一次运行测试时间: 2026-03-23 10:30:00 +0800
# 最近一次运行成功时间: 2026-03-23 10:30:00 +0800
# 功能说明: 覆盖 StoreAST rank mismatch 与 deslice 分支。
# 测试目的: 验证 StoreAST rank mismatch 抛错，sizes 路径生成 dma.deslice。
# 使用示例: pytest -q test/dsl/test_emit_mlir.py -k test_emit_mlir_store_rank_mismatch_and_deslice
# 对应功能实现文件路径: kernel_gen/dsl/emit_mlir.py
# 对应 spec 文件路径: spec/dsl/emit_mlir.md
# 对应测试文件路径: test/dsl/test_emit_mlir.py
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


# EMIT-023A
# 创建者: 小李飞刀
# 最后一次更改: 小李飞刀
# 最近一次运行测试时间: 2026-03-23 10:30:00 +0800
# 最近一次运行成功时间: 2026-03-23 10:30:00 +0800
# 功能说明: 覆盖 _ensure_supported_statements 的错误分支。
# 测试目的: 验证空函数体与不支持语句会抛出明确错误。
# 使用示例: pytest -q test/dsl/test_emit_mlir.py -k test_emit_mlir_ensure_supported_statements_errors
# 对应功能实现文件路径: kernel_gen/dsl/emit_mlir.py
# 对应 spec 文件路径: spec/dsl/emit_mlir.md
# 对应测试文件路径: test/dsl/test_emit_mlir.py
def test_emit_mlir_ensure_supported_statements_errors() -> None:
    memory = Memory([2, 2], NumericType.Float32)
    tensor = TensorAST(name="x", memory=memory, location=None)
    empty_func = FunctionAST(name="empty", inputs=[tensor], outputs=[], body=BlockAST([]))
    with pytest.raises(_LoweringError, match="Function body is empty"):
        _ensure_supported_statements(empty_func)

    bad_func = FunctionAST(name="bad", inputs=[tensor], outputs=[], body=BlockAST([object()]))
    with pytest.raises(_LoweringError, match="Unsupported AST expression for lowering"):
        _ensure_supported_statements(bad_func)


# EMIT-013A
# 创建者: 小李飞刀
# 最后一次更改: 小李飞刀
# 最近一次运行测试时间: 2026-03-26 22:20:00 +0800
# 最近一次运行成功时间: 2026-03-26 22:20:00 +0800
# 功能说明: 覆盖缓存恢复与索引类型分支。
# 测试目的: 验证缓存快照/恢复与 IndexType 输入的处理路径。
# 使用示例: pytest -q test/dsl/test_emit_mlir.py -k test_emit_mlir_cache_restore_and_index_value_variants
# 对应功能实现文件路径: kernel_gen/dsl/emit_mlir.py
# 对应 spec 文件路径: spec/dsl/emit_mlir.md
# 对应测试文件路径: test/dsl/test_emit_mlir.py
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


# EMIT-014A
# 创建者: 小李飞刀
# 最后一次更改: 小李飞刀
# 最近一次运行测试时间: 2026-03-23 05:10:36 +0800
# 最近一次运行成功时间: 2026-03-23 05:10:36 +0800
# 功能说明: 覆盖索引解析与 loop bound 的分支。
# 测试目的: 验证索引解析错误路径、直接值与 loop bound 解析。
# 使用示例: pytest -q test/dsl/test_emit_mlir.py -k test_emit_mlir_index_operand_variants_and_loop_bound
# 对应功能实现文件路径: kernel_gen/dsl/emit_mlir.py
# 对应 spec 文件路径: spec/dsl/emit_mlir.md
# 对应测试文件路径: test/dsl/test_emit_mlir.py
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


# EMIT-015A
# 创建者: 小李飞刀
# 最后一次更改: 小李飞刀
# 最近一次运行测试时间: 2026-03-23 05:10:36 +0800
# 最近一次运行成功时间: 2026-03-23 05:10:36 +0800
# 功能说明: 覆盖 layout 解析与 stride 校验分支。
# 测试目的: 验证 layout 支持 StringAttr 并拒绝非 unit stride。
# 使用示例: pytest -q test/dsl/test_emit_mlir.py -k test_emit_mlir_layout_and_stride_helpers
# 对应功能实现文件路径: kernel_gen/dsl/emit_mlir.py
# 对应 spec 文件路径: spec/dsl/emit_mlir.md
# 对应测试文件路径: test/dsl/test_emit_mlir.py
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


# EMIT-016A
# 创建者: 小李飞刀
# 最后一次更改: 小李飞刀
# 最近一次运行测试时间: 2026-03-23 05:10:36 +0800
# 最近一次运行成功时间: 2026-03-23 05:10:36 +0800
# 功能说明: 覆盖静态索引与广播形状推导分支。
# 测试目的: 验证静态索引列表构造与广播维度分支。
# 使用示例: pytest -q test/dsl/test_emit_mlir.py -k test_emit_mlir_static_index_list_and_broadcast_shape
# 对应功能实现文件路径: kernel_gen/dsl/emit_mlir.py
# 对应 spec 文件路径: spec/dsl/emit_mlir.md
# 对应测试文件路径: test/dsl/test_emit_mlir.py
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


# EMIT-017A
# 创建者: 小李飞刀
# 最后一次更改: 小李飞刀
# 最近一次运行测试时间: 2026-03-23 05:10:36 +0800
# 最近一次运行成功时间: 2026-03-23 05:10:36 +0800
# 功能说明: 覆盖类型推导中的未知输入路径。
# 测试目的: 验证 LoadAST 与 TensorAST 未登记时的报错。
# 使用示例: pytest -q test/dsl/test_emit_mlir.py -k test_emit_mlir_infer_expr_type_unknown_inputs
# 对应功能实现文件路径: kernel_gen/dsl/emit_mlir.py
# 对应 spec 文件路径: spec/dsl/emit_mlir.md
# 对应测试文件路径: test/dsl/test_emit_mlir.py
def test_emit_mlir_infer_expr_type_unknown_inputs() -> None:
    memory = Memory([2], NumericType.Float32)
    tensor = TensorAST(name="x", memory=memory, location=None)
    load = LoadAST(tensor=tensor, offset=[ConstAST(0)], stride=None, location=None)
    with pytest.raises(_LoweringError, match="Unknown input reference"):
        _infer_expr_type(load, {})
    with pytest.raises(_LoweringError, match="Unknown input reference"):
        _infer_expr_type(tensor, {})


# EMIT-018A
# 创建者: 小李飞刀
# 最后一次更改: 我不是牛马
# 最近一次运行测试时间: 2026-03-26 22:20:00 +0800
# 最近一次运行成功时间: 2026-03-26 22:20:00 +0800
# 功能说明: 覆盖 lowering 的错误路径与符号运算分支。
# 测试目的: 验证未知输入、符号运算非法 op 与不支持表达式报错。
# 使用示例: pytest -q test/dsl/test_emit_mlir.py -k test_emit_mlir_lower_expr_unknown_and_symbol_errors
# 对应功能实现文件路径: kernel_gen/dsl/emit_mlir.py
# 对应 spec 文件路径: spec/dsl/emit_mlir.md
# 对应测试文件路径: test/dsl/test_emit_mlir.py
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

    with pytest.raises(_LoweringError, match="Unsupported symbol compare op"):
        _lower_expr(CompareExprAST(lhs=lhs, rhs=rhs, op="gt", location=None), symbol_ctx)

    with pytest.raises(_LoweringError, match="Unsupported symbol binary op"):
        _lower_expr(BinaryExprAST(lhs=lhs, rhs=rhs, op="mod", location=None), symbol_ctx)

    with pytest.raises(_LoweringError, match="Unsupported expression for lowering"):
        _lower_expr(object(), symbol_ctx)


# EMIT-024
# 创建者: 我不是牛马
# 最后一次更改: 我不是牛马
# 最近一次运行测试时间: 2026-03-26 22:20:00 +0800
# 最近一次运行成功时间: 2026-03-26 22:20:00 +0800
# 功能说明: 验证 symbol 标量 >= 比较在 emit 阶段生成 symbol.ge 并返回 i1。
# 测试目的: 锁定 symbol.ge lowering 与 i1 结果类型。
# 使用示例: pytest -q test/dsl/test_emit_mlir.py -k test_emit_mlir_lowers_symbol_ge
# 对应功能实现文件路径: kernel_gen/dsl/emit_mlir.py
# 对应 spec 文件路径: spec/dsl/emit_mlir.md
# 对应测试文件路径: test/dsl/test_emit_mlir.py
def test_emit_mlir_lowers_symbol_ge() -> None:
    block = Block(arg_types=[SymbolValueType.from_expr("A"), SymbolValueType.from_expr("B")])
    ctx = EmitContext(builder=block, symbols={"a": block.args[0], "b": block.args[1]}, types={})
    lhs = ScalarArgAST(name="a", value_type=int, is_symbolic=True)
    rhs = ScalarArgAST(name="b", value_type=int, is_symbolic=True)
    ctx._set_cache(_expr_key(lhs), block.args[0])
    ctx._set_cache(_expr_key(rhs), block.args[1])
    ctx.types[_expr_key(lhs)] = block.args[0].type
    ctx.types[_expr_key(rhs)] = block.args[1].type
    expr = CompareExprAST(op="ge", lhs=lhs, rhs=rhs, location=None)

    result = _lower_expr(expr, ctx)
    assert isinstance(result.owner, SymbolGeOp)
    assert result.type == i1


# EMIT-002A
# 创建者: 小李飞刀
# 最后一次更改: 咯咯咯
# 最近一次运行测试时间: 2026-03-27 04:40:00 +0800
# 最近一次运行成功时间: 2026-03-27 04:40:00 +0800
# 功能说明: 覆盖 compare 广播路径中 rhs 需要扩展的分支。
# 测试目的: 验证 CompareExprAST(op="ne") 的 rhs 广播与结果 element type 为 i1。
# 使用示例: pytest -q test/dsl/test_emit_mlir.py -k test_emit_mlir_binary_compare_broadcast_rhs
# 对应功能实现文件路径: kernel_gen/dsl/emit_mlir.py
# 对应 spec 文件路径: spec/dsl/emit_mlir.md
# 对应测试文件路径: test/dsl/test_emit_mlir.py
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

    compare_expr = CompareExprAST(lhs=lhs, rhs=rhs, op="ne", location=None)
    compare_value = _lower_expr(compare_expr, ctx)
    assert isinstance(compare_value.owner, NnNeOp)
    assert compare_value.type.element_type == i1


# EMIT-002B
# 创建者: 咯咯咯
# 最后一次更改: 咯咯咯
# 最近一次运行测试时间: 2026-03-27 04:40:00 +0800
# 最近一次运行成功时间: 2026-03-27 04:40:00 +0800
# 功能说明: 覆盖 compare memory 路径的 broadcast 与 dtype/space 错误分支。
# 测试目的: 验证 CompareExprAST(op="ne") 相关的 broadcast mismatch 与 element type/space 报错文案。
# 使用示例: pytest -q test/dsl/test_emit_mlir.py -k test_emit_mlir_compare_memory_mismatch_reports_diagnostics
# 对应功能实现文件路径: kernel_gen/dsl/emit_mlir.py
# 对应 spec 文件路径: spec/dsl/emit_mlir.md
# 对应测试文件路径: test/dsl/test_emit_mlir.py
def test_emit_mlir_compare_memory_mismatch_reports_diagnostics() -> None:
    lhs_type = _memory_to_nn_type(Memory([2, 1], NumericType.Float32))
    rhs_type_mismatch = _memory_to_nn_type(Memory([3, 1], NumericType.Float32))

    with pytest.raises(_LoweringError, match="Implicit broadcast dimension mismatch"):
        _infer_broadcast_memory_type(lhs_type, rhs_type_mismatch, location=None)

    rhs_element_mismatch = _memory_to_nn_type(Memory([2, 1], NumericType.Int32))
    with pytest.raises(_LoweringError, match="Binary op operands must have the same element_type"):
        _infer_broadcast_memory_type(lhs_type, rhs_element_mismatch, location=None)

    rhs_space_mismatch = _memory_to_nn_type(Memory([2, 1], NumericType.Float32, space=MemorySpace.LM))
    with pytest.raises(_LoweringError, match="Binary op operands must have the same space"):
        _infer_broadcast_memory_type(lhs_type, rhs_space_mismatch, location=None)


# EMIT-020A
# 创建者: 小李飞刀
# 最后一次更改: 小李飞刀
# 最近一次运行测试时间: 2026-03-23 05:10:36 +0800
# 最近一次运行成功时间: 2026-03-23 05:10:36 +0800
# 功能说明: 覆盖 for 循环的 loop_vars 恢复逻辑与错误分支。
# 测试目的: 验证 for 循环恢复已有 loop_vars 并拒绝不支持的节点。
# 使用示例: pytest -q test/dsl/test_emit_mlir.py -k test_emit_mlir_for_loop_restores_loop_vars_and_errors
# 对应功能实现文件路径: kernel_gen/dsl/emit_mlir.py
# 对应 spec 文件路径: spec/dsl/emit_mlir.md
# 对应测试文件路径: test/dsl/test_emit_mlir.py
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


# MGEN-016
# 创建者: 小李飞刀
# 最后一次更改: 小李飞刀
# 最近一次运行测试时间: 2026-03-23 05:10:36 +0800
# 最近一次运行成功时间: 2026-03-23 05:10:36 +0800
# 功能说明: 覆盖符号标量函数的输出判断。
# 测试目的: 验证无输出时仍被视为符号标量函数。
# 使用示例: pytest -q test/dsl/test_emit_mlir.py -k test_mlir_gen_symbol_scalar_function_no_outputs
# 对应功能实现文件路径: kernel_gen/dsl/mlir_gen.py
# 对应 spec 文件路径: spec/dsl/mlir_gen.md
# 对应测试文件路径: test/dsl/test_emit_mlir.py
def test_mlir_gen_symbol_scalar_function_no_outputs() -> None:
    func_ast = FunctionAST(
        name="sym",
        inputs=[ScalarArgAST(name="n", value_type=int)],
        outputs=[],
        body=BlockAST([ConstAST(1)]),
    )
    assert _is_symbol_scalar_function(func_ast) is True


# MGEN-003
# 创建者: 小李飞刀
# 最后一次更改: 小李飞刀
# 最近一次运行测试时间: 2026-03-23 05:10:36 +0800
# 最近一次运行成功时间: 2026-03-23 05:10:36 +0800
# 功能说明: 覆盖返回类型校验的空输出与标量分支。
# 测试目的: 验证无输出直接返回、标量返回的 i32 约束。
# 使用示例: pytest -q test/dsl/test_emit_mlir.py -k test_mlir_gen_validate_return_type_variants
# 对应功能实现文件路径: kernel_gen/dsl/mlir_gen.py
# 对应 spec 文件路径: spec/dsl/mlir_gen.md
# 对应测试文件路径: test/dsl/test_emit_mlir.py
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
