"""AST visitor tests.

创建者: 小李飞刀
最后一次更改: 朽木露琪亚

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
    i8,
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
    DmaFreeOp,
    DmaDesliceOp,
    DmaLoadOp,
    DmaReshapeOp,
    DmaSliceOp,
    DmaStoreOp,
    DmaViewOp,
)
from kernel_gen.dialect.arch import (
    ArchGetDynamicMemoryOp,
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
    SymbolGtOp,
    SymbolGeOp,
    SymbolGetDimOp,
    SymbolGetStrideOp,
    SymbolLeOp,
    SymbolLtOp,
    SymbolMulOp,
    SymbolNeOp,
    SymbolSubOp,
    SymbolValueType,
)
from kernel_gen.dsl.ast import (
    AstParseError,
    ArchGetDynamicMemoryAST,
    ArchLaunchKernelAST,
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
    TensorAxisAccessAST,
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
def test_build_func_op_lowers_arch_get_block_id_query(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from kernel_gen.operation.arch import get_block_id

    def get_block_id_kernel() -> int:
        return get_block_id()

    monkeypatch.setitem(get_block_id_kernel.__globals__, "get_block_id", get_block_id)

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
# 功能说明: 验证未显式导入的 bare get_block_id 调用会在 AST 入口被统一拒绝。
# 测试目的: 锁定未导入的 get_block_id(1) 与 get_block_id(x=1) 不再进入 helper 语义校验，而是直接返回 Unsupported call expression。
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
        if diagnostics[0].message != "Unsupported call expression":
            raise AssertionError("expected Unsupported call expression diagnostic")


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


# AST-014K / MGEN-038
# 创建者: OpenAI
# 最后一次更改: 小李飞刀
# 最近一次运行测试时间: 2026-03-31 03:20:00 +0800
# 最近一次运行成功时间: 2026-03-31 03:20:00 +0800
# 功能说明: 验证 `Memory.get_shape()[axis]` 可沿 build_func_op/build_func_op_from_ast lowering 为 symbol.get_dim。
# 测试目的: 锁定 get_shape 轴访问在 AST visitor 路径返回 `!symbol.int` 并发射单个 symbol.get_dim。
# 使用示例: pytest -q test/dsl/test_ast_visitor.py -k test_build_func_op_lowers_symbol_get_dim
# 对应功能实现文件路径: kernel_gen/dsl/ast.py, kernel_gen/dsl/emit_mlir.py, kernel_gen/dsl/mlir_gen.py
# 对应 spec 文件路径: spec/dsl/ast.md, spec/dsl/emit_mlir.md, spec/dsl/mlir_gen.md
# 对应测试文件路径: test/dsl/test_ast_visitor.py
def test_build_func_op_lowers_symbol_get_dim() -> None:
    static_memory = Memory([4, 8], NumericType.Float32)

    def get_dim_static(value: "Tensor[f32, 4, 8]") -> int:
        return value.get_shape()[1]

    func_ast = parse_function(get_dim_static)
    if not isinstance(func_ast.body.statements[0], TensorAxisAccessAST):
        raise AssertionError("expected get_dim_static to parse into TensorAxisAccessAST")

    for func_op in (build_func_op(get_dim_static, static_memory), build_func_op_from_ast(func_ast, (static_memory,))):
        body_ops = list(func_op.body.block.ops)
        query_ops = [op for op in body_ops if isinstance(op, SymbolGetDimOp)]
        return_ops = [op for op in body_ops if isinstance(op, func.ReturnOp)]
        if len(query_ops) != 1:
            raise AssertionError("expected one symbol.get_dim op for static shape query")
        if query_ops[0].result.type != SymbolValueType.from_expr("8"):
            raise AssertionError('expected static get_shape result type to be !symbol.int<"8">')
        if len(return_ops) != 1 or len(return_ops[0].arguments) != 1:
            raise AssertionError("expected func.return to carry one symbol result")


# AST-014L / MGEN-039
# 创建者: OpenAI
# 最后一次更改: 小李飞刀
# 最近一次运行测试时间: 2026-03-31 03:20:00 +0800
# 最近一次运行成功时间: 2026-03-31 03:20:00 +0800
# 功能说明: 验证 `Memory.get_stride()[axis]` 可沿 build_func_op/build_func_op_from_ast lowering 为 symbol.get_stride。
# 测试目的: 锁定 get_stride 轴访问在 AST visitor 路径返回 `!symbol.int` 并发射单个 symbol.get_stride。
# 使用示例: pytest -q test/dsl/test_ast_visitor.py -k test_build_func_op_lowers_symbol_get_stride
# 对应功能实现文件路径: kernel_gen/dsl/ast.py, kernel_gen/dsl/emit_mlir.py, kernel_gen/dsl/mlir_gen.py
# 对应 spec 文件路径: spec/dsl/ast.md, spec/dsl/emit_mlir.md, spec/dsl/mlir_gen.md
# 对应测试文件路径: test/dsl/test_ast_visitor.py
def test_build_func_op_lowers_symbol_get_stride() -> None:
    static_memory = Memory([4, 8], NumericType.Float32, stride=[8, 1])

    def get_stride_static(value: "Tensor[f32, 4, 8]") -> int:
        return value.get_stride()[0]

    func_ast = parse_function(get_stride_static)
    if not isinstance(func_ast.body.statements[0], TensorAxisAccessAST):
        raise AssertionError("expected get_stride_static to parse into TensorAxisAccessAST")

    for func_op in (build_func_op(get_stride_static, static_memory), build_func_op_from_ast(func_ast, (static_memory,))):
        body_ops = list(func_op.body.block.ops)
        query_ops = [op for op in body_ops if isinstance(op, SymbolGetStrideOp)]
        return_ops = [op for op in body_ops if isinstance(op, func.ReturnOp)]
        if len(query_ops) != 1:
            raise AssertionError("expected one symbol.get_stride op for static stride query")
        if query_ops[0].result.type != SymbolValueType.from_expr("8"):
            raise AssertionError('expected static get_stride result type to be !symbol.int<"8">')
        if len(return_ops) != 1 or len(return_ops[0].arguments) != 1:
            raise AssertionError("expected func.return to carry one symbol result")


# AST-014C / MGEN-029
# 创建者: 咯咯咯
# 最后一次更改: 咯咯咯
# 最近一次运行测试时间: 2026-03-26 00:27:39 +0800
# 最近一次运行成功时间: 2026-03-26 00:27:39 +0800
# 功能说明: 验证零入参 get_block_num DSL 函数可解析并 lowering 为 arch.get_block_num。
# 测试目的: 锁定 get_block_num 查询的 AST 解析、build_func_op 与 build_func_op_from_ast 返回类型为 !symbol.int<"block_num">。
# 使用示例: pytest -q test/dsl/test_ast_visitor.py -k test_build_func_op_lowers_arch_get_block_num_query
# 对应功能实现文件路径: kernel_gen/dsl/ast.py, kernel_gen/dsl/mlir_gen.py
# 对应 spec 文件路径: spec/dsl/ast.md, spec/dsl/mlir_gen.md
# 对应测试文件路径: test/dsl/test_ast_visitor.py
def test_build_func_op_lowers_arch_get_block_num_query(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from kernel_gen.operation.arch import get_block_num

    def get_block_num_kernel() -> int:
        return get_block_num()

    monkeypatch.setitem(get_block_num_kernel.__globals__, "get_block_num", get_block_num)

    func_ast = parse_function(get_block_num_kernel)
    if len(func_ast.inputs) != 0:
        raise AssertionError("expected get_block_num kernel to have no inputs")
    if len(func_ast.outputs) != 1:
        raise AssertionError("expected get_block_num kernel to have one output annotation")
    if len(func_ast.body.statements) != 1:
        raise AssertionError("expected get_block_num kernel to lower to one AST statement")
    if not isinstance(func_ast.body.statements[0], ArchQueryAST):
        raise AssertionError("expected get_block_num kernel to parse into ArchQueryAST")
    if func_ast.body.statements[0].query_name != "get_block_num":
        raise AssertionError("expected arch query name to stay get_block_num")

    for func_op in (build_func_op(get_block_num_kernel), build_func_op_from_ast(func_ast)):
        if len(tuple(func_op.body.block.args)) != 0:
            raise AssertionError("expected zero-argument func.func for get_block_num kernel")
        body_ops = list(func_op.body.block.ops)
        query_ops = [op for op in body_ops if isinstance(op, ArchGetBlockNumOp)]
        return_ops = [op for op in body_ops if isinstance(op, func.ReturnOp)]
        if len(query_ops) != 1:
            raise AssertionError("expected exactly one arch.get_block_num op")
        if query_ops[0].result.type != SymbolValueType.from_expr("block_num"):
            raise AssertionError('expected arch.get_block_num result type to be !symbol.int<"block_num">')
        if len(return_ops) != 1:
            raise AssertionError("expected exactly one func.return op")
        if len(return_ops[0].arguments) != 1:
            raise AssertionError("expected func.return to carry one value")
        if return_ops[0].arguments[0].type != SymbolValueType.from_expr("block_num"):
            raise AssertionError('expected func.return type to stay !symbol.int<"block_num">')


# AST-014D
# 创建者: 咯咯咯
# 最后一次更改: 咯咯咯
# 最近一次运行测试时间: 2026-03-26 00:27:39 +0800
# 最近一次运行成功时间: 2026-03-26 00:27:39 +0800
# 功能说明: 验证未显式导入的 bare get_block_num 调用会在 AST 入口被统一拒绝。
# 测试目的: 锁定未导入的 get_block_num(1) 与 get_block_num(x=1) 不再进入 helper 语义校验，而是直接返回 Unsupported call expression。
# 使用示例: pytest -q test/dsl/test_ast_visitor.py -k test_parse_function_rejects_invalid_get_block_num_arity_variants
# 对应功能实现文件路径: kernel_gen/dsl/ast.py
# 对应 spec 文件路径: spec/dsl/ast.md
# 对应测试文件路径: test/dsl/test_ast_visitor.py
def test_parse_function_rejects_invalid_get_block_num_arity_variants(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    invalid_sources = (
        """\
def kernel() -> int:
    return get_block_num(1)
""",
        """\
def kernel() -> int:
    return get_block_num(x=1)
""",
    )

    for source in invalid_sources:
        with pytest.raises(AstParseError) as exc_info:
            _parse_function_from_source(monkeypatch, source)
        diagnostics = exc_info.value.diagnostics
        if not diagnostics:
            raise AssertionError("expected diagnostics for invalid get_block_num arity")
        if diagnostics[0].message != "Unsupported call expression":
            raise AssertionError("expected Unsupported call expression diagnostic")


# EMIT-023
# 创建者: 咯咯咯
# 最后一次更改: 咯咯咯
# 最近一次运行测试时间: 2026-03-26 00:27:39 +0800
# 最近一次运行成功时间: 2026-03-26 00:27:39 +0800
# 功能说明: 验证 ArchQueryAST(query_name="get_block_num") lowering 为 arch.get_block_num。
# 测试目的: 锁定 emit_mlir 对 get_block_num 查询的发射语义与结果类型。
# 使用示例: pytest -q test/dsl/test_ast_visitor.py -k test_emit_mlir_lowers_arch_get_block_num_query
# 对应功能实现文件路径: kernel_gen/dsl/emit_mlir.py
# 对应 spec 文件路径: spec/dsl/emit_mlir.md
# 对应测试文件路径: test/dsl/test_ast_visitor.py
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


# AST-014E / MGEN-031
# 创建者: 我不是牛马
# 最后一次更改: 我不是牛马
# 最近一次运行测试时间: 2026-03-25 21:41:29 +0800
# 最近一次运行成功时间: 2026-03-25 21:41:29 +0800
# 功能说明: 验证零入参 get_subthread_id DSL 函数可解析并 lowering 为 arch.get_subthread_id。
# 测试目的: 锁定 get_subthread_id 查询的 AST 解析、build_func_op 与 build_func_op_from_ast 返回类型为 !symbol.int<"subthread_id">。
# 使用示例: pytest -q test/dsl/test_ast_visitor.py -k test_build_func_op_lowers_arch_get_subthread_id_query
# 对应功能实现文件路径: kernel_gen/dsl/ast.py, kernel_gen/dsl/mlir_gen.py
# 对应 spec 文件路径: spec/dsl/ast.md, spec/dsl/mlir_gen.md
# 对应测试文件路径: test/dsl/test_ast_visitor.py
def test_build_func_op_lowers_arch_get_subthread_id_query(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from kernel_gen.operation.arch import get_subthread_id

    def get_subthread_id_kernel() -> int:
        return get_subthread_id()

    monkeypatch.setitem(get_subthread_id_kernel.__globals__, "get_subthread_id", get_subthread_id)

    func_ast = parse_function(get_subthread_id_kernel)
    if len(func_ast.inputs) != 0:
        raise AssertionError("expected get_subthread_id kernel to have no inputs")
    if len(func_ast.outputs) != 1:
        raise AssertionError("expected get_subthread_id kernel to have one output annotation")
    if len(func_ast.body.statements) != 1:
        raise AssertionError("expected get_subthread_id kernel to lower to one AST statement")
    if not isinstance(func_ast.body.statements[0], ArchQueryAST):
        raise AssertionError("expected get_subthread_id kernel to parse into ArchQueryAST")
    if func_ast.body.statements[0].query_name != "get_subthread_id":
        raise AssertionError("expected arch query name to stay get_subthread_id")

    for func_op in (build_func_op(get_subthread_id_kernel), build_func_op_from_ast(func_ast)):
        if len(tuple(func_op.body.block.args)) != 0:
            raise AssertionError("expected zero-argument func.func for get_subthread_id kernel")
        body_ops = list(func_op.body.block.ops)
        query_ops = [op for op in body_ops if isinstance(op, ArchGetSubthreadIdOp)]
        return_ops = [op for op in body_ops if isinstance(op, func.ReturnOp)]
        if len(query_ops) != 1:
            raise AssertionError("expected exactly one arch.get_subthread_id op")
        if query_ops[0].result.type != SymbolValueType.from_expr("subthread_id"):
            raise AssertionError('expected arch.get_subthread_id result type to be !symbol.int<"subthread_id">')
        if len(return_ops) != 1:
            raise AssertionError("expected exactly one func.return op")
        if len(return_ops[0].arguments) != 1:
            raise AssertionError("expected func.return to carry one value")
        if return_ops[0].arguments[0].type != SymbolValueType.from_expr("subthread_id"):
            raise AssertionError('expected func.return type to stay !symbol.int<"subthread_id">')


# AST-014F
# 创建者: 我不是牛马
# 最后一次更改: 我不是牛马
# 最近一次运行测试时间: 2026-03-25 21:41:29 +0800
# 最近一次运行成功时间: 2026-03-25 21:41:29 +0800
# 功能说明: 验证未显式导入的 bare get_subthread_id 调用会在 AST 入口被统一拒绝。
# 测试目的: 锁定未导入的 get_subthread_id(1) 与 get_subthread_id(x=1) 不再进入 helper 语义校验，而是直接返回 Unsupported call expression。
# 使用示例: pytest -q test/dsl/test_ast_visitor.py -k test_parse_function_rejects_invalid_get_subthread_id_arity_variants
# 对应功能实现文件路径: kernel_gen/dsl/ast.py
# 对应 spec 文件路径: spec/dsl/ast.md
# 对应测试文件路径: test/dsl/test_ast_visitor.py
def test_parse_function_rejects_invalid_get_subthread_id_arity_variants(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    invalid_sources = (
        """\
def kernel() -> int:
    return get_subthread_id(1)
""",
        """\
def kernel() -> int:
    return get_subthread_id(x=1)
""",
    )

    for source in invalid_sources:
        with pytest.raises(AstParseError) as exc_info:
            _parse_function_from_source(monkeypatch, source)
        diagnostics = exc_info.value.diagnostics
        if not diagnostics:
            raise AssertionError("expected diagnostics for invalid get_subthread_id arity")
        if diagnostics[0].message != "Unsupported call expression":
            raise AssertionError("expected Unsupported call expression diagnostic")


# EMIT-025
# 创建者: 我不是牛马
# 最后一次更改: 我不是牛马
# 最近一次运行测试时间: 2026-03-25 21:41:29 +0800
# 最近一次运行成功时间: 2026-03-25 21:41:29 +0800
# 功能说明: 验证 ArchQueryAST(query_name="get_subthread_id") lowering 为 arch.get_subthread_id。
# 测试目的: 锁定 emit_mlir 对 get_subthread_id 查询的发射语义与结果类型。
# 使用示例: pytest -q test/dsl/test_ast_visitor.py -k test_emit_mlir_lowers_arch_get_subthread_id_query
# 对应功能实现文件路径: kernel_gen/dsl/emit_mlir.py
# 对应 spec 文件路径: spec/dsl/emit_mlir.md
# 对应测试文件路径: test/dsl/test_ast_visitor.py
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


# AST-014G / MGEN-032
# 创建者: 朽木露琪亚
# 最后一次更改: 朽木露琪亚
# 最近一次运行测试时间: 2026-03-27 01:38:30 +0800
# 最近一次运行成功时间: 2026-03-27 01:38:30 +0800
# 功能说明: 验证零入参 get_thread_id DSL 函数可解析并 lowering 为 arch.get_thread_id。
# 测试目的: 锁定 get_thread_id 查询的 AST 解析、build_func_op 与 build_func_op_from_ast 返回类型为 !symbol.int<"thread_id">。
# 使用示例: pytest -q test/dsl/test_ast_visitor.py -k test_build_func_op_lowers_arch_get_thread_id_query
# 对应功能实现文件路径: kernel_gen/dsl/ast.py, kernel_gen/dsl/mlir_gen.py
# 对应 spec 文件路径: spec/dsl/ast.md, spec/dsl/mlir_gen.md
# 对应测试文件路径: test/dsl/test_ast_visitor.py
def test_build_func_op_lowers_arch_get_thread_id_query(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from kernel_gen.operation.arch import get_thread_id

    def get_thread_id_kernel() -> int:
        return get_thread_id()

    monkeypatch.setitem(get_thread_id_kernel.__globals__, "get_thread_id", get_thread_id)

    func_ast = parse_function(get_thread_id_kernel)
    if len(func_ast.inputs) != 0:
        raise AssertionError("expected get_thread_id kernel to have no inputs")
    if len(func_ast.outputs) != 1:
        raise AssertionError("expected get_thread_id kernel to have one output annotation")
    if len(func_ast.body.statements) != 1:
        raise AssertionError("expected get_thread_id kernel to lower to one AST statement")
    if not isinstance(func_ast.body.statements[0], ArchQueryAST):
        raise AssertionError("expected get_thread_id kernel to parse into ArchQueryAST")
    if func_ast.body.statements[0].query_name != "get_thread_id":
        raise AssertionError("expected arch query name to stay get_thread_id")

    for func_op in (build_func_op(get_thread_id_kernel), build_func_op_from_ast(func_ast)):
        if len(tuple(func_op.body.block.args)) != 0:
            raise AssertionError("expected zero-argument func.func for get_thread_id kernel")
        body_ops = list(func_op.body.block.ops)
        query_ops = [op for op in body_ops if isinstance(op, ArchGetThreadIdOp)]
        return_ops = [op for op in body_ops if isinstance(op, func.ReturnOp)]
        if len(query_ops) != 1:
            raise AssertionError("expected exactly one arch.get_thread_id op")
        if query_ops[0].result.type != SymbolValueType.from_expr("thread_id"):
            raise AssertionError('expected arch.get_thread_id result type to be !symbol.int<"thread_id">')
        if len(return_ops) != 1:
            raise AssertionError("expected exactly one func.return op")
        if len(return_ops[0].arguments) != 1:
            raise AssertionError("expected func.return to carry one value")
        if return_ops[0].arguments[0].type != SymbolValueType.from_expr("thread_id"):
            raise AssertionError('expected func.return type to stay !symbol.int<"thread_id">')


# AST-014H
# 创建者: 朽木露琪亚
# 最后一次更改: 朽木露琪亚
# 最近一次运行测试时间: 2026-03-27 01:38:30 +0800
# 最近一次运行成功时间: 2026-03-27 01:38:30 +0800
# 功能说明: 验证未显式导入的 bare get_thread_id 调用会在 AST 入口被统一拒绝。
# 测试目的: 锁定未导入的 get_thread_id(1) 与 get_thread_id(x=1) 不再进入 helper 语义校验，而是直接返回 Unsupported call expression。
# 使用示例: pytest -q test/dsl/test_ast_visitor.py -k test_parse_function_rejects_invalid_get_thread_id_arity_variants
# 对应功能实现文件路径: kernel_gen/dsl/ast.py
# 对应 spec 文件路径: spec/dsl/ast.md
# 对应测试文件路径: test/dsl/test_ast_visitor.py
def test_parse_function_rejects_invalid_get_thread_id_arity_variants(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    invalid_sources = (
        """\
def kernel() -> int:
    return get_thread_id(1)
""",
        """\
def kernel() -> int:
    return get_thread_id(x=1)
""",
    )

    for source in invalid_sources:
        with pytest.raises(AstParseError) as exc_info:
            _parse_function_from_source(monkeypatch, source)
        diagnostics = exc_info.value.diagnostics
        if not diagnostics:
            raise AssertionError("expected diagnostics for invalid get_thread_id arity")
        if diagnostics[0].message != "Unsupported call expression":
            raise AssertionError("expected Unsupported call expression diagnostic")


# EMIT-026
# 创建者: 朽木露琪亚
# 最后一次更改: 朽木露琪亚
# 最近一次运行测试时间: 2026-03-27 01:38:30 +0800
# 最近一次运行成功时间: 2026-03-27 01:38:30 +0800
# 功能说明: 验证 ArchQueryAST(query_name="get_thread_id") lowering 为 arch.get_thread_id。
# 测试目的: 锁定 emit_mlir 对 get_thread_id 查询的发射语义与结果类型。
# 使用示例: pytest -q test/dsl/test_ast_visitor.py -k test_emit_mlir_lowers_arch_get_thread_id_query
# 对应功能实现文件路径: kernel_gen/dsl/emit_mlir.py
# 对应 spec 文件路径: spec/dsl/emit_mlir.md
# 对应测试文件路径: test/dsl/test_ast_visitor.py
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


# AST-014L
# 创建者: 金铲铲大作战
# 最后一次更改: 金铲铲大作战
# 最近一次运行测试时间: 2026-03-28 13:25:45 +0800
# 最近一次运行成功时间: 2026-03-28 13:25:45 +0800
# 功能说明: 验证未显式导入的 bare get_thread_num 调用会在 AST 入口被统一拒绝。
# 测试目的: 锁定未导入的 get_thread_num(1) 与 get_thread_num(x=1) 不再进入 helper 语义校验，而是直接返回 Unsupported call expression。
# 使用示例: pytest -q test/dsl/test_ast_visitor.py -k test_parse_function_rejects_invalid_get_thread_num_arity_variants
# 对应功能实现文件路径: kernel_gen/dsl/ast.py
# 对应 spec 文件路径: spec/dsl/ast.md
# 对应测试文件路径: test/dsl/test_ast_visitor.py
def test_parse_function_rejects_invalid_get_thread_num_arity_variants(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    invalid_sources = (
        """\
def kernel() -> int:
    return get_thread_num(1)
""",
        """\
def kernel() -> int:
    return get_thread_num(x=1)
""",
    )

    for source in invalid_sources:
        with pytest.raises(AstParseError) as exc_info:
            _parse_function_from_source(monkeypatch, source)
        diagnostics = exc_info.value.diagnostics
        if not diagnostics:
            raise AssertionError("expected diagnostics for invalid get_thread_num arity")
        if diagnostics[0].message != "Unsupported call expression":
            raise AssertionError("expected Unsupported call expression diagnostic")


# AST-014N
# 创建者: 金铲铲大作战
# 最后一次更改: 金铲铲大作战
# 最近一次运行测试时间: 2026-03-28 13:25:45 +0800
# 最近一次运行成功时间: 2026-03-28 13:25:45 +0800
# 功能说明: 验证未显式导入的 bare get_dynamic_memory 调用会在 AST 入口被统一拒绝。
# 测试目的: 锁定未导入的 get_dynamic_memory(...) 不再进入 helper 语义校验，而是直接返回 Unsupported call expression。
# 使用示例: pytest -q test/dsl/test_ast_visitor.py -k test_parse_function_rejects_invalid_get_dynamic_memory_variants
# 对应功能实现文件路径: kernel_gen/dsl/ast.py
# 对应 spec 文件路径: spec/dsl/ast.md
# 对应测试文件路径: test/dsl/test_ast_visitor.py
def test_parse_function_rejects_invalid_get_dynamic_memory_variants(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    invalid_sources = (
        (
            """\
def kernel() -> "Tensor[i8, ?]":
    return get_dynamic_memory()
""",
            "Unsupported call expression",
        ),
        (
            """\
def kernel() -> "Tensor[i8, ?]":
    return get_dynamic_memory(1)
""",
            "Unsupported call expression",
        ),
        (
            """\
def kernel() -> "Tensor[i8, ?]":
    return get_dynamic_memory(MemorySpace.GM)
""",
            "Unsupported call expression",
        ),
    )

    for source, message in invalid_sources:
        with pytest.raises(AstParseError) as exc_info:
            _parse_function_from_source(monkeypatch, source)
        diagnostics = exc_info.value.diagnostics
        if not diagnostics:
            raise AssertionError("expected diagnostics for invalid get_dynamic_memory variants")
        if diagnostics[0].message != message:
            raise AssertionError(f"expected {message} diagnostic")


# EMIT-031
# 创建者: 金铲铲大作战
# 最后一次更改: 金铲铲大作战
# 最近一次运行测试时间: 2026-03-28 13:25:45 +0800
# 最近一次运行成功时间: 2026-03-28 13:25:45 +0800
# 功能说明: 验证 ArchGetDynamicMemoryAST lowering 对非法 space 报错。
# 测试目的: 锁定 emit_mlir 对 get_dynamic_memory 片上空间限制的诊断口径。
# 使用示例: pytest -q test/dsl/test_ast_visitor.py -k test_emit_mlir_rejects_invalid_arch_get_dynamic_memory_space
# 对应功能实现文件路径: kernel_gen/dsl/emit_mlir.py
# 对应 spec 文件路径: spec/dsl/emit_mlir.md
# 对应测试文件路径: test/dsl/test_ast_visitor.py
def test_emit_mlir_rejects_invalid_arch_get_dynamic_memory_space() -> None:
    node = ArchGetDynamicMemoryAST(space=MemorySpace.GM, location=None)
    ctx = EmitContext(builder=Block(), symbols={}, types={})
    with pytest.raises(_LoweringError, match="get_dynamic_memory space must be on-chip MemorySpace"):
        emit_node_mlir(node, ctx)


# MGEN-036
# 创建者: 金铲铲大作战
# 最后一次更改: 金铲铲大作战
# 最近一次运行测试时间: 2026-03-28 13:25:45 +0800
# 最近一次运行成功时间: 2026-03-28 13:25:45 +0800
# 功能说明: 验证 build_func_op 链路对非法 get_dynamic_memory space 报错。
# 测试目的: 锁定 build_func_op 对 get_dynamic_memory 片上空间限制的错误路径诊断。
# 使用示例: pytest -q test/dsl/test_ast_visitor.py -k test_build_func_op_rejects_invalid_arch_get_dynamic_memory_space
# 对应功能实现文件路径: kernel_gen/dsl/ast.py, kernel_gen/dsl/mlir_gen.py
# 对应 spec 文件路径: spec/dsl/mlir_gen.md
# 对应测试文件路径: test/dsl/test_ast_visitor.py
def test_build_func_op_rejects_invalid_arch_get_dynamic_memory_space() -> None:
    from kernel_gen.operation.arch import get_dynamic_memory

    def get_dynamic_memory_kernel() -> "Tensor[i8, ?]":
        return get_dynamic_memory(MemorySpace.GM)

    with pytest.raises(AstVisitorError, match="get_dynamic_memory space must be on-chip MemorySpace"):
        build_func_op(get_dynamic_memory_kernel)


# AST-014NA / MGEN-036A
# 创建者: 朽木露琪亚
# 最后一次更改: 朽木露琪亚
# 最近一次运行测试时间: 2026-04-02 14:55:00 +0800
# 最近一次运行成功时间: 2026-04-02 14:55:00 +0800
# 功能说明: 验证 get_dynamic_memory 在 import-bound helper 基线下支持 module alias 与 direct symbol alias 两类正向入口。
# 测试目的: 锁定 `arch_alias.get_dynamic_memory(...)` 与 `gdm(...)` 在 AST / build_func_op / build_func_op_from_ast 链路中都能稳定 lowering 为 arch.get_dynamic_memory。
# 使用示例: pytest -q test/dsl/test_ast_visitor.py -k test_build_func_op_lowers_arch_get_dynamic_memory_via_import_bound_aliases
# 对应功能实现文件路径: kernel_gen/dsl/ast.py, kernel_gen/dsl/mlir_gen.py
# 对应 spec 文件路径: spec/dsl/ast.md, spec/dsl/mlir_gen.md
# 对应测试文件路径: test/dsl/test_ast_visitor.py
def test_build_func_op_lowers_arch_get_dynamic_memory_via_import_bound_aliases(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import kernel_gen.operation.arch as arch_module

    def module_alias_kernel() -> "Tensor[i8, ?]":
        return arch_ops.get_dynamic_memory(MemorySpace.TSM)

    def direct_alias_kernel() -> "Tensor[i8, ?]":
        return gdm(MemorySpace.TLM)

    monkeypatch.setitem(module_alias_kernel.__globals__, "arch_ops", arch_module)
    monkeypatch.setitem(direct_alias_kernel.__globals__, "gdm", arch_module.get_dynamic_memory)

    cases = (
        (module_alias_kernel, "get_dynamic_memory", MemorySpace.TSM, "tsm"),
        (direct_alias_kernel, "gdm", MemorySpace.TLM, "tlm"),
    )
    for fn, helper_name, expected_space, expected_space_name in cases:
        func_ast = parse_function(fn)
        if len(func_ast.body.statements) != 1:
            raise AssertionError("expected get_dynamic_memory alias kernel to lower to one AST statement")
        stmt = func_ast.body.statements[0]
        if not isinstance(stmt, ArchGetDynamicMemoryAST):
            raise AssertionError("expected get_dynamic_memory alias kernel to parse into ArchGetDynamicMemoryAST")
        if stmt.space is not expected_space:
            raise AssertionError(f"expected {helper_name} to keep MemorySpace binding")

        for func_op in (build_func_op(fn), build_func_op_from_ast(func_ast)):
            if len(tuple(func_op.body.block.args)) != 0:
                raise AssertionError("expected zero-argument func.func for get_dynamic_memory alias kernel")
            body_ops = list(func_op.body.block.ops)
            query_ops = [op for op in body_ops if isinstance(op, ArchGetDynamicMemoryOp)]
            return_ops = [op for op in body_ops if isinstance(op, func.ReturnOp)]
            if len(query_ops) != 1:
                raise AssertionError("expected exactly one arch.get_dynamic_memory op")
            if query_ops[0].memory_space.space.data != expected_space_name:
                raise AssertionError("expected memory_space attr to match helper binding")
            if query_ops[0].result.type.element_type != i8:
                raise AssertionError("expected dynamic memory result element type to stay i8")
            if query_ops[0].result.type.shape.data[0] != StringAttr("?"):
                raise AssertionError('expected dynamic memory result shape to stay [?]')
            if query_ops[0].result.type.stride.data[0] != IntAttr(1):
                raise AssertionError("expected dynamic memory result stride to stay [1]")
            if query_ops[0].result.type.space.space.data != expected_space_name:
                raise AssertionError("expected dynamic memory result space to match helper binding")
            if len(return_ops) != 1 or len(return_ops[0].arguments) != 1:
                raise AssertionError("expected func.return to carry one dynamic memory value")
            if return_ops[0].arguments[0].type != query_ops[0].result.type:
                raise AssertionError("expected func.return type to stay aligned with arch.get_dynamic_memory result")


# AST-014I / MGEN-033
# 创建者: 摸鱼小分队
# 最后一次更改: 摸鱼小分队
# 最近一次运行测试时间: 2026-03-27 02:08:59 +0800
# 最近一次运行成功时间: 2026-03-27 02:08:59 +0800
# 功能说明: 验证零入参 get_subthread_num DSL 函数可解析并 lowering 为 arch.get_subthread_num。
# 测试目的: 锁定 get_subthread_num 查询的 AST 解析、build_func_op 与 build_func_op_from_ast 返回类型为 !symbol.int<"subthread_num">。
# 使用示例: pytest -q test/dsl/test_ast_visitor.py -k test_build_func_op_lowers_arch_get_subthread_num_query
# 对应功能实现文件路径: kernel_gen/dsl/ast.py, kernel_gen/dsl/mlir_gen.py
# 对应 spec 文件路径: spec/dsl/ast.md, spec/dsl/mlir_gen.md
# 对应测试文件路径: test/dsl/test_ast_visitor.py
def test_build_func_op_lowers_arch_get_subthread_num_query(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from kernel_gen.operation.arch import get_subthread_num

    def get_subthread_num_kernel() -> int:
        return get_subthread_num()

    monkeypatch.setitem(get_subthread_num_kernel.__globals__, "get_subthread_num", get_subthread_num)

    func_ast = parse_function(get_subthread_num_kernel)
    if len(func_ast.inputs) != 0:
        raise AssertionError("expected get_subthread_num kernel to have no inputs")
    if len(func_ast.outputs) != 1:
        raise AssertionError("expected get_subthread_num kernel to have one output annotation")
    if len(func_ast.body.statements) != 1:
        raise AssertionError("expected get_subthread_num kernel to lower to one AST statement")
    if not isinstance(func_ast.body.statements[0], ArchQueryAST):
        raise AssertionError("expected get_subthread_num kernel to parse into ArchQueryAST")
    if func_ast.body.statements[0].query_name != "get_subthread_num":
        raise AssertionError("expected arch query name to stay get_subthread_num")

    for func_op in (build_func_op(get_subthread_num_kernel), build_func_op_from_ast(func_ast)):
        if len(tuple(func_op.body.block.args)) != 0:
            raise AssertionError("expected zero-argument func.func for get_subthread_num kernel")
        body_ops = list(func_op.body.block.ops)
        query_ops = [op for op in body_ops if isinstance(op, ArchGetSubthreadNumOp)]
        return_ops = [op for op in body_ops if isinstance(op, func.ReturnOp)]
        if len(query_ops) != 1:
            raise AssertionError("expected exactly one arch.get_subthread_num op")
        if query_ops[0].result.type != SymbolValueType.from_expr("subthread_num"):
            raise AssertionError('expected arch.get_subthread_num result type to be !symbol.int<"subthread_num">')
        if len(return_ops) != 1:
            raise AssertionError("expected exactly one func.return op")
        if len(return_ops[0].arguments) != 1:
            raise AssertionError("expected func.return to carry one value")
        if return_ops[0].arguments[0].type != SymbolValueType.from_expr("subthread_num"):
            raise AssertionError('expected func.return type to stay !symbol.int<"subthread_num">')


# AST-014J
# 创建者: 摸鱼小分队
# 最后一次更改: 摸鱼小分队
# 最近一次运行测试时间: 2026-03-27 02:08:59 +0800
# 最近一次运行成功时间: 2026-03-27 02:08:59 +0800
# 功能说明: 验证未显式导入的 bare get_subthread_num 调用会在 AST 入口被统一拒绝。
# 测试目的: 锁定未导入的 get_subthread_num(1) 与 get_subthread_num(x=1) 不再进入 helper 语义校验，而是直接返回 Unsupported call expression。
# 使用示例: pytest -q test/dsl/test_ast_visitor.py -k test_parse_function_rejects_invalid_get_subthread_num_arity_variants
# 对应功能实现文件路径: kernel_gen/dsl/ast.py
# 对应 spec 文件路径: spec/dsl/ast.md
# 对应测试文件路径: test/dsl/test_ast_visitor.py
def test_parse_function_rejects_invalid_get_subthread_num_arity_variants(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    invalid_sources = (
        """\
def kernel() -> int:
    return get_subthread_num(1)
""",
        """\
def kernel() -> int:
    return get_subthread_num(x=1)
""",
    )

    for source in invalid_sources:
        with pytest.raises(AstParseError) as exc_info:
            _parse_function_from_source(monkeypatch, source)
        diagnostics = exc_info.value.diagnostics
        if not diagnostics:
            raise AssertionError("expected diagnostics for invalid get_subthread_num arity")
        if diagnostics[0].message != "Unsupported call expression":
            raise AssertionError("expected Unsupported call expression diagnostic")


# EMIT-027
# 创建者: 摸鱼小分队
# 最后一次更改: 摸鱼小分队
# 最近一次运行测试时间: 2026-03-27 02:08:59 +0800
# 最近一次运行成功时间: 2026-03-27 02:08:59 +0800
# 功能说明: 验证 ArchQueryAST(query_name="get_subthread_num") lowering 为 arch.get_subthread_num。
# 测试目的: 锁定 emit_mlir 对 get_subthread_num 查询的发射语义与结果类型。
# 使用示例: pytest -q test/dsl/test_ast_visitor.py -k test_emit_mlir_lowers_arch_get_subthread_num_query
# 对应功能实现文件路径: kernel_gen/dsl/emit_mlir.py
# 对应 spec 文件路径: spec/dsl/emit_mlir.md
# 对应测试文件路径: test/dsl/test_ast_visitor.py
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


# AST-014P
# 创建者: 小李飞刀
# 最后一次更改: 小李飞刀
# 最近一次运行测试时间: 2026-03-28 13:01:00 +0800
# 最近一次运行成功时间: 2026-03-28 13:01:00 +0800
# 功能说明: 验证未显式导入的 bare launch_kernel 调用会在 AST 入口被统一拒绝。
# 测试目的: 锁定未导入的 launch_kernel(...) 不再进入 helper 语义校验，而是直接返回 Unsupported call expression。
# 使用示例: pytest -q test/dsl/test_ast_visitor.py -k test_parse_function_rejects_invalid_launch_kernel_variants
# 对应功能实现文件路径: kernel_gen/dsl/ast.py
# 对应 spec 文件路径: spec/dsl/ast.md
# 对应测试文件路径: test/dsl/test_ast_visitor.py
def test_parse_function_rejects_invalid_launch_kernel_variants(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    invalid_sources = (
        (
            """\
def kernel() -> None:
    launch_kernel("k", 1, 2)
""",
            "Unsupported call expression",
        ),
        (
            """\
def kernel() -> None:
    launch_kernel("", 1, 2, 3)
""",
            "Unsupported call expression",
        ),
        (
            """\
def kernel() -> None:
    launch_kernel("k", 1.0, 2, 3)
""",
            "Unsupported call expression",
        ),
        (
            """\
def kernel() -> None:
    launch_kernel("k", 0, 2, 3)
""",
            "Unsupported call expression",
        ),
    )

    for source, message in invalid_sources:
        with pytest.raises(AstParseError) as exc_info:
            _parse_function_from_source(monkeypatch, source)
        diagnostics = exc_info.value.diagnostics
        if not diagnostics:
            raise AssertionError("expected diagnostics for invalid launch_kernel variants")
        if diagnostics[0].message != message:
            raise AssertionError(f"expected {message} diagnostic")


# EMIT-032
# 创建者: 小李飞刀
# 最后一次更改: 小李飞刀
# 最近一次运行测试时间: 2026-03-28 13:01:00 +0800
# 最近一次运行成功时间: 2026-03-28 13:01:00 +0800
# 功能说明: 验证 ArchLaunchKernelAST lowering 对非法 name/extent 报错。
# 测试目的: 锁定 emit_mlir 对 launch_kernel 的名称与 extent 约束诊断口径。
# 使用示例: pytest -q test/dsl/test_ast_visitor.py -k test_emit_mlir_rejects_invalid_arch_launch_kernel_args
# 对应功能实现文件路径: kernel_gen/dsl/emit_mlir.py
# 对应 spec 文件路径: spec/dsl/emit_mlir.md
# 对应测试文件路径: test/dsl/test_ast_visitor.py
def test_emit_mlir_rejects_invalid_arch_launch_kernel_args() -> None:
    invalid_nodes = (
        (
            ArchLaunchKernelAST(
                name="",
                block=ConstAST(1),
                thread=ConstAST(1),
                subthread=ConstAST(1),
            ),
            "launch_kernel name must be non-empty str",
        ),
        (
            ArchLaunchKernelAST(
                name="kernel",
                block=ConstAST(1),
                thread=ConstAST(1),
                subthread=ConstAST(1),
            ),
            "launch_kernel block must be !symbol.int",
        ),
    )

    for node, message in invalid_nodes:
        block = Block()
        ctx = EmitContext(builder=block, symbols={}, types={})
        with pytest.raises(_LoweringError, match=message):
            emit_node_mlir(node, ctx)


# MGEN-037
# 创建者: 小李飞刀
# 最后一次更改: 小李飞刀
# 最近一次运行测试时间: 2026-03-28 13:01:00 +0800
# 最近一次运行成功时间: 2026-03-28 13:01:00 +0800
# 功能说明: 验证 build_func_op 链路在 launch_kernel extent 无法归一化时返回错误。
# 测试目的: 锁定 build_func_op 对非法 launch_kernel extent 的错误路径诊断。
# 使用示例: pytest -q test/dsl/test_ast_visitor.py -k test_build_func_op_rejects_invalid_arch_launch_kernel_args
# 对应功能实现文件路径: kernel_gen/dsl/mlir_gen.py, kernel_gen/dsl/emit_mlir.py
# 对应 spec 文件路径: spec/dsl/mlir_gen.md
# 对应测试文件路径: test/dsl/test_ast_visitor.py
def test_build_func_op_rejects_invalid_arch_launch_kernel_args() -> None:
    from kernel_gen.operation.arch import launch_kernel

    def launch_kernel_kernel() -> None:
        launch_kernel("kernel", 1, 2, 3)

    with pytest.raises(AstVisitorError, match="launch_kernel block must be !symbol.int"):
        build_func_op(launch_kernel_kernel)


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


# AST-002B
# 创建者: 小李飞刀
# 最后一次更改: 小李飞刀
# 最近一次运行测试时间: 2026-03-27 03:15:10 +0800
# 最近一次运行成功时间: 2026-03-27 03:15:10 +0800
# 功能说明: 验证 parse_function 支持 Tensor[i1]/Tensor[bool] 注解解析。
# 测试目的: 确保 Tensor 注解可以解析为 Bool dtype，覆盖 i1 与 bool 两种写法。
# 使用示例: pytest -q test/dsl/test_ast_visitor.py -k test_ast_parse_function_accepts_tensor_bool_annotations
# 对应功能实现文件路径: kernel_gen/dsl/ast.py
# 对应 spec 文件路径: spec/dsl/ast.md
# 对应测试文件路径: test/dsl/test_ast_visitor.py
def test_ast_parse_function_accepts_tensor_bool_annotations() -> None:
    def kernel(
        x: "Tensor[i1, 2, 2]",
        y: "Tensor[bool, 2, 2]",
    ) -> "Tensor[i1, 2, 2]":
        return x

    func_ast = parse_function(kernel)
    assert len(func_ast.inputs) == 2
    assert isinstance(func_ast.inputs[0], TensorAST)
    assert isinstance(func_ast.inputs[1], TensorAST)
    assert func_ast.inputs[0].memory.dtype is NumericType.Bool
    assert func_ast.inputs[1].memory.dtype is NumericType.Bool
    assert len(func_ast.outputs) == 1
    assert isinstance(func_ast.outputs[0], TensorAST)
    assert func_ast.outputs[0].memory.dtype is NumericType.Bool


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
# 最后一次更改: 我不是牛马
# 最近一次运行测试时间: 2026-03-26 22:20:00 +0800
# 最近一次运行成功时间: 2026-03-26 22:20:00 +0800
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
# 最后一次更改: 小李飞刀
# 最近一次运行测试时间: 2026-03-30 03:03:30 +0800
# 最近一次运行成功时间: 2026-03-30 03:03:30 +0800
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


def test_build_func_op_supports_dma_view_helper() -> None:
    from kernel_gen.operation.dma import view

    source = Memory([4, 4], NumericType.Float32, space=MemorySpace.GM)

    def view_kernel(src: "Tensor[f32, 4, 4]") -> "Tensor[f32, 2, 2]":
        return view(src, [1, 1], [2, 2], [1, 1])

    func_op = build_func_op(view_kernel, source)
    view_ops = [op for op in func_op.body.block.ops if isinstance(op, DmaViewOp)]
    return_ops = [op for op in func_op.body.block.ops if isinstance(op, func.ReturnOp)]
    assert len(view_ops) == 1
    assert len(return_ops) == 1
    assert list(func_op.function_type.outputs) == [view_ops[0].result.type]
    assert return_ops[0].arguments[0].type == view_ops[0].result.type


# MGEN-026A
# 创建者: 小李飞刀
# 最后一次更改: 我不是牛马
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


# MGEN-026B
# 创建者: 金铲铲大作战
# 最后一次更改: 金铲铲大作战
# 最近一次运行测试时间: 2026-03-26 02:03:12 +0800
# 最近一次运行成功时间: 2026-03-26 02:03:12 +0800
# 功能说明: 验证 alloc-only kernel 可接受 SymbolDim runtime_args 并保持符号 shape 表达式。
# 测试目的: 锁定 SymbolDim runtime_args 会 lowering 为 !symbol.int 输入且结果类型 shape 保持符号名。
# 使用示例: pytest -q test/dsl/test_ast_visitor.py -k test_build_func_op_supports_dma_alloc_helper_with_symbol_shape_args
# 对应功能实现文件路径: kernel_gen/dsl/mlir_gen.py
# 对应 spec 文件路径: spec/dsl/mlir_gen.md
# 对应测试文件路径: test/dsl/test_ast_visitor.py
def test_build_func_op_supports_dma_alloc_helper_with_symbol_shape_args() -> None:
    from kernel_gen.operation.dma import alloc

    symbol_lhs = SymbolDim("M")
    symbol_rhs = SymbolDim("N")
    lhs_expr = str(symbol_lhs.get_symbol())
    rhs_expr = str(symbol_rhs.get_symbol())

    def alloc_kernel(rank1: int, rank2: int) -> f"Tensor[f32, {lhs_expr}, {rhs_expr}]":
        return alloc([rank1, rank2], NumericType.Float32, MemorySpace.SM)

    func_op = build_func_op(
        alloc_kernel,
        symbol_lhs,
        symbol_rhs,
        globals={"lhs_expr": lhs_expr, "rhs_expr": rhs_expr},
    )
    alloc_ops = [op for op in func_op.body.block.ops if isinstance(op, DmaAllocOp)]

    assert list(func_op.function_type.inputs) == [
        SymbolValueType.from_expr(lhs_expr),
        SymbolValueType.from_expr(rhs_expr),
    ]
    assert len(alloc_ops) == 1
    assert [attr.data for attr in alloc_ops[0].result.type.shape.data] == [lhs_expr, rhs_expr]
    assert list(func_op.function_type.outputs) == [alloc_ops[0].result.type]


# MGEN-026B
# 创建者: 金铲铲大作战
# 最后一次更改: 金铲铲大作战
# 最近一次运行测试时间: 2026-03-26 02:03:12 +0800
# 最近一次运行成功时间: 2026-03-26 02:03:12 +0800
# 功能说明: 验证 alloc-only kernel 支持 SymbolDim + const 的混合 shape runtime_args。
# 测试目的: 锁定符号表达式在输入与结果类型中保持一致。
# 使用示例: pytest -q test/dsl/test_ast_visitor.py -k test_build_func_op_supports_dma_alloc_helper_with_symbol_plus_const_shape_args
# 对应功能实现文件路径: kernel_gen/dsl/mlir_gen.py
# 对应 spec 文件路径: spec/dsl/mlir_gen.md
# 对应测试文件路径: test/dsl/test_ast_visitor.py
def test_build_func_op_supports_dma_alloc_helper_with_symbol_plus_const_shape_args() -> None:
    from kernel_gen.operation.dma import alloc

    symbol_lhs = SymbolDim("M") + 2
    symbol_rhs = SymbolDim("N") + 3
    lhs_expr = str(symbol_lhs.get_symbol())
    rhs_expr = str(symbol_rhs.get_symbol())

    def alloc_kernel(rank1: int, rank2: int) -> f"Tensor[f32, {lhs_expr}, {rhs_expr}]":
        return alloc([rank1, rank2], NumericType.Float32, MemorySpace.SM)

    func_op = build_func_op(
        alloc_kernel,
        symbol_lhs,
        symbol_rhs,
        globals={"lhs_expr": lhs_expr, "rhs_expr": rhs_expr},
    )
    alloc_ops = [op for op in func_op.body.block.ops if isinstance(op, DmaAllocOp)]

    assert list(func_op.function_type.inputs) == [
        SymbolValueType.from_expr(lhs_expr),
        SymbolValueType.from_expr(rhs_expr),
    ]
    assert len(alloc_ops) == 1
    assert [attr.data for attr in alloc_ops[0].result.type.shape.data] == [lhs_expr, rhs_expr]
    assert list(func_op.function_type.outputs) == [alloc_ops[0].result.type]


# MGEN-026C
# 创建者: 金铲铲大作战
# 最后一次更改: 金铲铲大作战
# 最近一次运行测试时间: 2026-03-26 02:03:12 +0800
# 最近一次运行成功时间: 2026-03-26 02:03:12 +0800
# 功能说明: 验证 alloc-only kernel 在零参数常量形状场景下生成正确结果类型。
# 测试目的: 锁定 func.func 无输入且 dma.alloc 结果类型与返回注解一致。
# 使用示例: pytest -q test/dsl/test_ast_visitor.py -k test_build_func_op_supports_dma_alloc_helper_without_runtime_args
# 对应功能实现文件路径: kernel_gen/dsl/mlir_gen.py
# 对应 spec 文件路径: spec/dsl/mlir_gen.md
# 对应测试文件路径: test/dsl/test_ast_visitor.py
def test_build_func_op_supports_dma_alloc_helper_without_runtime_args() -> None:
    from kernel_gen.operation.dma import alloc

    def alloc_kernel() -> "Tensor[f32, 3, 5]":
        return alloc([3, 5], NumericType.Float32, MemorySpace.SM)

    func_op = build_func_op(alloc_kernel)
    alloc_ops = [op for op in func_op.body.block.ops if isinstance(op, DmaAllocOp)]

    assert list(func_op.function_type.inputs) == []
    assert len(alloc_ops) == 1
    assert [attr.data for attr in alloc_ops[0].result.type.shape.data] == [3, 5]
    assert list(func_op.function_type.outputs) == [alloc_ops[0].result.type]


# MGEN-026D
# 创建者: 金铲铲大作战
# 最后一次更改: 金铲铲大作战
# 最近一次运行测试时间: 2026-03-26 02:03:12 +0800
# 最近一次运行成功时间: 2026-03-26 02:03:12 +0800
# 功能说明: 验证 alloc-only kernel 支持显式连续 stride 输入。
# 测试目的: 锁定显式 stride lowering 不改变结果类型与输入符号表达式。
# 使用示例: pytest -q test/dsl/test_ast_visitor.py -k test_build_func_op_supports_dma_alloc_helper_with_explicit_stride
# 对应功能实现文件路径: kernel_gen/dsl/mlir_gen.py
# 对应 spec 文件路径: spec/dsl/mlir_gen.md
# 对应测试文件路径: test/dsl/test_ast_visitor.py
def test_build_func_op_supports_dma_alloc_helper_with_explicit_stride() -> None:
    from kernel_gen.operation.dma import alloc

    rows = 2
    cols = 3
    row_stride = cols
    col_stride = 1

    def alloc_kernel(rank1: int, rank2: int, stride1: int, stride2: int) -> "Tensor[f32, 2, 3]":
        return alloc(
            [rank1, rank2],
            NumericType.Float32,
            MemorySpace.SM,
            stride=[stride1, stride2],
        )

    func_op = build_func_op(alloc_kernel, rows, cols, row_stride, col_stride)
    alloc_ops = [op for op in func_op.body.block.ops if isinstance(op, DmaAllocOp)]

    assert list(func_op.function_type.inputs) == [
        SymbolValueType.from_expr(str(rows)),
        SymbolValueType.from_expr(str(cols)),
        SymbolValueType.from_expr(str(row_stride)),
        SymbolValueType.from_expr(str(col_stride)),
    ]
    assert len(alloc_ops) == 1
    assert [attr.data for attr in alloc_ops[0].result.type.shape.data] == [rows, cols]
    assert [attr.data for attr in alloc_ops[0].result.type.stride.data] == [row_stride, col_stride]
    assert list(func_op.function_type.outputs) == [alloc_ops[0].result.type]


# MGEN-026E
# 创建者: 金铲铲大作战
# 最后一次更改: 金铲铲大作战
# 最近一次运行测试时间: 2026-03-26 02:03:12 +0800
# 最近一次运行成功时间: 2026-03-26 02:03:12 +0800
# 功能说明: 验证 alloc-only kernel 拒绝非法 dtype 参数。
# 测试目的: 锁定 alloc dtype 校验错误信息与公开语义一致。
# 使用示例: pytest -q test/dsl/test_ast_visitor.py -k test_build_func_op_rejects_dma_alloc_helper_with_invalid_dtype
# 对应功能实现文件路径: kernel_gen/dsl/ast.py
# 对应 spec 文件路径: spec/dsl/mlir_gen.md
# 对应测试文件路径: test/dsl/test_ast_visitor.py
def test_build_func_op_rejects_dma_alloc_helper_with_invalid_dtype() -> None:
    from kernel_gen.operation.dma import alloc

    def alloc_kernel(rank1: int, rank2: int) -> "Tensor[f32, 2, 3]":
        return alloc([rank1, rank2], "f32", MemorySpace.SM)

    with pytest.raises(AstVisitorError, match="alloc dtype must be NumericType"):
        build_func_op(alloc_kernel, 2, 3)


# MGEN-026E
# 创建者: 金铲铲大作战
# 最后一次更改: 金铲铲大作战
# 最近一次运行测试时间: 2026-03-26 02:03:12 +0800
# 最近一次运行成功时间: 2026-03-26 02:03:12 +0800
# 功能说明: 验证 alloc-only kernel 拒绝非法 space 参数。
# 测试目的: 锁定 alloc space 校验错误信息与公开语义一致。
# 使用示例: pytest -q test/dsl/test_ast_visitor.py -k test_build_func_op_rejects_dma_alloc_helper_with_invalid_space
# 对应功能实现文件路径: kernel_gen/dsl/ast.py
# 对应 spec 文件路径: spec/dsl/mlir_gen.md
# 对应测试文件路径: test/dsl/test_ast_visitor.py
def test_build_func_op_rejects_dma_alloc_helper_with_invalid_space() -> None:
    from kernel_gen.operation.dma import alloc

    def alloc_kernel(rank1: int, rank2: int) -> "Tensor[f32, 2, 3]":
        return alloc([rank1, rank2], NumericType.Float32, "shared")

    with pytest.raises(AstVisitorError, match="alloc space must be MemorySpace"):
        build_func_op(alloc_kernel, 2, 3)


# MGEN-026E
# 创建者: 金铲铲大作战
# 最后一次更改: 金铲铲大作战
# 最近一次运行测试时间: 2026-03-26 02:03:12 +0800
# 最近一次运行成功时间: 2026-03-26 02:03:12 +0800
# 功能说明: 验证 alloc-only kernel 拒绝非连续 stride。
# 测试目的: 锁定非连续 stride 报错信息与公开语义一致。
# 使用示例: pytest -q test/dsl/test_ast_visitor.py -k test_build_func_op_rejects_dma_alloc_helper_with_non_contiguous_stride
# 对应功能实现文件路径: kernel_gen/dsl/mlir_gen.py
# 对应 spec 文件路径: spec/dsl/mlir_gen.md
# 对应测试文件路径: test/dsl/test_ast_visitor.py
def test_build_func_op_rejects_dma_alloc_helper_with_non_contiguous_stride() -> None:
    from kernel_gen.operation.dma import alloc

    def alloc_kernel(rank1: int, rank2: int, stride1: int, stride2: int) -> "Tensor[f32, 2, 3]":
        return alloc(
            [rank1, rank2],
            NumericType.Float32,
            MemorySpace.SM,
            stride=[stride1, stride2],
        )

    with pytest.raises(AstVisitorError, match="dma.alloc only supports contiguous stride"):
        build_func_op(alloc_kernel, 2, 3, 3, 2)


# MGEN-026
# 创建者: 朽木露琪亚
# 最后一次更改: 朽木露琪亚
# 最近一次运行测试时间: 2026-03-25 10:04:04 +0800
# 最近一次运行成功时间: 2026-03-25 10:04:04 +0800
# 功能说明: 验证 build_func_op 在 free 语句场景下保留 dma.free。
# 测试目的: 验证 free 作为无返回值语句参与 lowering，函数体会保留 DmaFreeOp 与 func.return。
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
    block_ops = list(func_op.body.block.ops)
    assert [type(op) for op in block_ops] == [DmaFreeOp, func.ReturnOp]
    assert block_ops[0].source is func_op.body.block.args[0]


# MGEN-026
# 创建者: 小李飞刀
# 最后一次更改: 小李飞刀
# 最近一次运行测试时间: 2026-03-30 03:03:30 +0800
# 最近一次运行成功时间: 2026-03-30 03:03:30 +0800
# 功能说明: 验证 build_func_op 遇到 free 非 memory operand 时抛出错误。
# 测试目的: 锁定 AstVisitor/build_func_op 链路对 Operand must be nn.memory 的错误口径。
# 使用示例: pytest -q test/dsl/test_ast_visitor.py -k test_build_func_op_rejects_dma_free_non_memory_operand
# 对应功能实现文件路径: kernel_gen/dsl/mlir_gen.py
# 对应 spec 文件路径: spec/dsl/mlir_gen.md
# 对应测试文件路径: test/dsl/test_ast_visitor.py
def test_build_func_op_rejects_dma_free_non_memory_operand() -> None:
    from kernel_gen.operation.dma import free

    def free_kernel():
        free(1)

    with pytest.raises(AstVisitorError, match="Operand must be nn.memory"):
        build_func_op(free_kernel)


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
    alloc_ops = [op for op in func_op.body.block.ops if isinstance(op, DmaAllocOp)]
    slice_ops = [op for op in func_op.body.block.ops if isinstance(op, DmaSliceOp)]
    return_ops = [op for op in func_op.body.block.ops if isinstance(op, func.ReturnOp)]
    assert isinstance(func_op, func.FuncOp)
    assert len(alloc_ops) == 1
    assert len(slice_ops) == 1
    assert len(return_ops) == 1
    assert slice_ops[0].target is alloc_ops[0].result
    assert return_ops[0].operands[0] is alloc_ops[0].result


# MGEN-026C
# 创建者: 金铲铲大作战
# 最后一次更改: 金铲铲大作战
# 最近一次运行测试时间: 2026-04-03 00:00:00 +0800
# 最近一次运行成功时间: 2026-04-03 00:00:00 +0800
# 功能说明: 验证 dynamic symbol slice helper 在 build_func_op 链路中可直接 lowering。
# 测试目的: 锁定 `slice(..., [size_row, size_col], ...)` 不再因结果 shape 反查符号失败而报 `Unknown index symbol`。
# 使用示例: pytest -q test/dsl/test_ast_visitor.py -k test_build_func_op_supports_dynamic_symbol_dma_slice_helper
# 对应功能实现文件路径: kernel_gen/dsl/emit_mlir.py, kernel_gen/dsl/mlir_gen.py
# 对应 spec 文件路径: spec/dsl/emit_mlir.md, spec/dsl/mlir_gen.md
# 对应测试文件路径: test/dsl/test_ast_visitor.py
def test_build_func_op_supports_dynamic_symbol_dma_slice_helper() -> None:
    from kernel_gen.operation.dma import slice

    row_symbol = SymbolDim("TILE_M")
    col_symbol = SymbolDim("TILE_N")
    row_expr = str(row_symbol.get_symbol())
    col_expr = str(col_symbol.get_symbol())
    source = Memory([SymbolDim("SRC_M"), SymbolDim("SRC_N")], NumericType.Float32, space=MemorySpace.GM)

    def slice_symbol_kernel(
        src: f"Tensor[f32, SRC_M, SRC_N]",
        size_row: SymbolDim,
        size_col: SymbolDim,
    ) -> f"Tensor[f32, {row_expr}, {col_expr}]":
        return slice(src, [0, 0], [size_row, size_col], [1, 1], MemorySpace.LM)

    func_op = build_func_op(
        slice_symbol_kernel,
        source,
        row_symbol,
        col_symbol,
        globals={"row_expr": row_expr, "col_expr": col_expr},
    )
    alloc_ops = [op for op in func_op.body.block.ops if isinstance(op, DmaAllocOp)]
    slice_ops = [op for op in func_op.body.block.ops if isinstance(op, DmaSliceOp)]
    return_ops = [op for op in func_op.body.block.ops if isinstance(op, func.ReturnOp)]

    assert len(alloc_ops) == 1
    assert len(slice_ops) == 1
    assert len(return_ops) == 1
    assert list(func_op.function_type.inputs) == [
        _memory_to_nn_type(source),
        SymbolValueType.from_expr(row_expr),
        SymbolValueType.from_expr(col_expr),
    ]
    assert [attr.data for attr in alloc_ops[0].result.type.shape.data] == [row_expr, col_expr]
    assert slice_ops[0].target is alloc_ops[0].result
    assert return_ops[0].operands[0] is alloc_ops[0].result


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


# MGEN-030
# 创建者: 我不是牛马
# 最后一次更改: 我不是牛马
# 最近一次运行测试时间: 2026-03-26 22:20:00 +0800
# 最近一次运行成功时间: 2026-03-26 22:20:00 +0800
# 功能说明: 验证 symbol 标量 >= 比较 lowering 为 symbol.ge 且返回 i1。
# 测试目的: 覆盖 const/const 与 symbol/symbol 输入下的 return 与赋值返回形态。
# 使用示例: pytest -q test/dsl/test_ast_visitor.py -k test_build_func_op_lowers_symbol_ge
# 对应功能实现文件路径: kernel_gen/dsl/mlir_gen.py, kernel_gen/dsl/emit_mlir.py
# 对应 spec 文件路径: spec/dsl/mlir_gen.md
# 对应测试文件路径: test/dsl/test_ast_visitor.py
def test_build_func_op_lowers_symbol_ge() -> None:
    def ge_return(lhs: int, rhs: int) -> bool:
        return lhs >= rhs

    def ge_assign(lhs: int, rhs: int) -> bool:
        result = lhs >= rhs
        return result

    def _expected_expr(value: object) -> str:
        if isinstance(value, SymbolDim):
            return str(value.get_symbol())
        return str(value)

    runtime_cases = [
        (ge_return, (3, 1)),
        (ge_assign, (3, 1)),
        (ge_return, (SymbolDim("M"), SymbolDim("N"))),
        (ge_assign, (SymbolDim("M"), SymbolDim("N"))),
    ]
    for fn, runtime_args in runtime_cases:
        func_op = build_func_op(fn, *runtime_args)
        expected_arg_types = [SymbolValueType.from_expr(_expected_expr(arg)) for arg in runtime_args]
        assert [arg.type for arg in func_op.args] == expected_arg_types
        compare_ops = [op for op in func_op.body.block.ops if isinstance(op, SymbolGeOp)]
        assert len(compare_ops) == 1
        assert compare_ops[0].result.type == i1
        return_op = next(op for op in func_op.body.block.ops if isinstance(op, func.ReturnOp))
        assert return_op.arguments[0].type == i1
        assert list(func_op.function_type.outputs) == [i1]
        assert "symbol.ge" in _print_module(ModuleOp([func_op]))


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
        return x - 1

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


# MGEN-022C
# 创建者: 我不是牛马
# 最后一次更改: 我不是牛马
# 最近一次运行测试时间: 2026-03-27 06:03:53 +0800
# 最近一次运行成功时间: 2026-03-27 06:03:53 +0800
# 功能说明: 覆盖 mixed dtype 场景下非法返回注解的拒绝边界。
# 测试目的: 确认返回注解 element_type 不来自操作数时抛出错误。
# 使用示例: pytest -q test/dsl/test_ast_visitor.py -k test_mixed_dtype_return_annotation_requires_operand_element_type
# 对应功能实现文件路径: kernel_gen/dsl/mlir_gen.py
# 对应 spec 文件路径: spec/dsl/mlir_gen.md
# 对应测试文件路径: test/dsl/test_ast_visitor.py
def test_mixed_dtype_return_annotation_requires_operand_element_type() -> None:
    def mul_mixed_invalid(
        lhs: "Tensor[f32, 2, 2]",
        rhs: "Tensor[i32, 2, 2]",
    ) -> "Tensor[f16, 2, 2]":
        return lhs * rhs

    with pytest.raises(AstVisitorError, match="Return type does not match annotation"):
        build_func_op(
            mul_mixed_invalid,
            Memory([2, 2], NumericType.Float32),
            Memory([2, 2], NumericType.Int32),
        )


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
# 最后一次更改: 金铲铲大作战
# 最近一次运行测试时间: 2026-03-26 21:43:31 +0800
# 最近一次运行成功时间: 2026-03-26 21:43:31 +0800
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
# 最后一次更改: 小李飞刀
# 最近一次运行测试时间: 2026-03-30 03:03:30 +0800
# 最近一次运行成功时间: 2026-03-30 03:03:30 +0800
# 功能说明: 验证 free AST 作为 statement lowering 时发射单个 dma.free。
# 测试目的: 验证 DmaFreeAST 不生成新的 SSA 结果，但会向 block 中插入单个 DmaFreeOp。
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
    ops = list(block.ops)
    assert isinstance(result, DmaFreeOp)
    assert len(ops) == 1
    assert ops[0] is result
    assert result.source is block.args[0]


# EMIT-021
# 创建者: 小李飞刀
# 最后一次更改: 小李飞刀
# 最近一次运行测试时间: 2026-03-30 03:03:30 +0800
# 最近一次运行成功时间: 2026-03-30 03:03:30 +0800
# 功能说明: 验证 free AST 遇到非 memory operand 时抛出错误。
# 测试目的: 锁定 emit_mlir 在 dma.free statement lowering 中对 Operand must be nn.memory 的错误口径。
# 使用示例: pytest -q test/dsl/test_ast_visitor.py -k test_emit_mlir_dma_free_rejects_non_memory_operand
# 对应功能实现文件路径: kernel_gen/dsl/emit_mlir.py
# 对应 spec 文件路径: spec/dsl/emit_mlir.md
# 对应测试文件路径: test/dsl/test_ast_visitor.py
def test_emit_mlir_dma_free_rejects_non_memory_operand() -> None:
    block = Block()
    ctx = EmitContext(builder=block, symbols={}, types={})

    with pytest.raises(_LoweringError, match="Operand must be nn.memory"):
        emit_node_mlir(DmaFreeAST(value=ConstAST(1, location=None), location=None), ctx)


# AST-009
# 创建者: OpenAI
# 最后一次更改: 金铲铲大作战
# 最近一次运行测试时间: 2026-03-26 21:43:31 +0800
# 最近一次运行成功时间: 2026-03-26 21:43:31 +0800
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


# AST-011A
# 创建者: 摸鱼小分队
# 最后一次更改: 摸鱼小分队
# 最近一次运行测试时间: 2026-03-27 03:45:00 +0800
# 最近一次运行成功时间: 2026-03-27 03:45:00 +0800
# 功能说明: 验证 parse_function 支持 Tensor[i1, ...] 返回注解并解析为 Bool 张量类型。
# 测试目的: 锁定 Tensor[i1, ...] 在 AST 注解解析阶段不会再触发 Unsupported tensor dtype。
# 使用示例: pytest -q test/dsl/test_ast_visitor.py -k test_parse_function_supports_tensor_i1_return_annotation
# 对应功能实现文件路径: kernel_gen/dsl/ast.py
# 对应 spec 文件路径: spec/dsl/ast.md
# 对应测试文件路径: test/dsl/test_ast_visitor.py
def test_parse_function_supports_tensor_i1_return_annotation() -> None:
    def ne_kernel(
        lhs: "Tensor[f32, 2, 2]",
        rhs: "Tensor[f32, 2, 2]",
    ) -> "Tensor[i1, 2, 2]":
        return lhs != rhs

    func_ast = parse_function(ne_kernel)

    if len(func_ast.outputs) != 1:
        raise AssertionError("expected one output annotation for ne_kernel")
    if not isinstance(func_ast.outputs[0], TensorAST):
        raise AssertionError("expected TensorAST output annotation for ne_kernel")
    if func_ast.outputs[0].memory.dtype is not NumericType.Bool:
        raise AssertionError("expected Tensor[i1, ...] to parse as NumericType.Bool")
    if func_ast.outputs[0].memory.shape.get_values() != [2, 2]:
        raise AssertionError("expected Tensor[i1, ...] shape to stay [2, 2]")


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
def test_parse_function_rejects_invalid_load_helper_variants(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from kernel_gen.operation.dma import load

    def bad_arity(src: "Tensor[f32, 4, 4]") -> "Tensor[f32, 2, 2]":
        return load(src, [0, 0])

    def bad_source(src: int) -> "Tensor[f32, 2, 2]":
        return load(src, [0], [1])

    def bad_space(src: "Tensor[f32, 4, 4]") -> "Tensor[f32, 2, 2]":
        return load(src, [0, 0], [2, 2], [1, 1], 1)

    for fn in (bad_arity, bad_source, bad_space):
        monkeypatch.setitem(fn.__globals__, "load", load)

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


# AST-013A
# 创建者: 朽木露琪亚
# 最后一次更改: 朽木露琪亚
# 最近一次运行测试时间: 2026-04-02 14:30:00 +0800
# 最近一次运行成功时间: 2026-04-02 14:30:00 +0800
# 功能说明: 验证未显式导入的 bare dma helper 调用会在 AST 入口被统一拒绝。
# 测试目的: 锁定未导入的 `view(...)` / `slice(...)` 不再进入 DMA helper 语义校验，而是直接返回 `Unsupported call expression`。
# 使用示例: pytest -q test/dsl/test_ast_visitor.py -k test_parse_function_rejects_unimported_dma_view_and_slice_helpers
# 对应功能实现文件路径: kernel_gen/dsl/ast.py
# 对应 spec 文件路径: spec/dsl/ast.md
# 对应测试文件路径: test/dsl/test_ast_visitor.py
def test_parse_function_rejects_unimported_dma_view_and_slice_helpers(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    invalid_sources = (
        """\
def kernel(src: "Tensor[f32, 4, 4]") -> "Tensor[f32, 2, 2]":
    return view(src, [1, 1], [2, 2], [1, 1])
""",
        """\
def kernel(src: "Tensor[f32, 4, 4]") -> "Tensor[f32, 2, 2]":
    return slice(src, [1, 1], [2, 2], [1, 1], MemorySpace.LM)
""",
    )

    for source in invalid_sources:
        with pytest.raises(AstParseError) as exc_info:
            _parse_function_from_source(monkeypatch, source)
        diagnostics = exc_info.value.diagnostics
        if not diagnostics:
            raise AssertionError("expected diagnostics for unimported dma helper")
        if diagnostics[0].message != "Unsupported call expression":
            raise AssertionError("expected Unsupported call expression diagnostic")


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
def test_parse_function_rejects_invalid_slice_helper_variants(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from kernel_gen.operation.dma import slice

    def bad_arity(src: "Tensor[f32, 4, 4]") -> "Tensor[f32, 2, 2]":
        return slice(src, [0, 0], [2, 2], [1, 1], MemorySpace.SM, 1)

    def bad_source(src: int) -> "Tensor[f32, 2, 2]":
        return slice(src, [0], [1])

    def bad_space(src: "Tensor[f32, 4, 4]") -> "Tensor[f32, 2, 2]":
        return slice(src, [0, 0], [2, 2], [1, 1], 1)

    for fn in (bad_arity, bad_source, bad_space):
        monkeypatch.setitem(fn.__globals__, "slice", slice)

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
def test_parse_function_rejects_invalid_store_helper_variants(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from kernel_gen.operation.dma import store

    def bad_arity(tile: "Tensor[f32, 2, 2]", dst: "Tensor[f32, 4, 4]"):
        store(tile, dst, [0, 0])

    def bad_target(tile: "Tensor[f32, 2, 2]", dst: int):
        store(tile, dst, [0, 0], [2, 2])

    for fn in (bad_arity, bad_target):
        monkeypatch.setitem(fn.__globals__, "store", store)

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
def test_parse_function_rejects_invalid_deslice_helper_variants(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from kernel_gen.operation.dma import deslice

    def bad_arity(tile: "Tensor[f32, 2, 2]", dst: "Tensor[f32, 4, 4]"):
        deslice(tile, dst, [0, 0])

    def bad_target(tile: "Tensor[f32, 2, 2]", dst: int):
        deslice(tile, dst, [0, 0], [2, 2])

    def bad_space(tile: "Tensor[f32, 2, 2]", dst: "Tensor[f32, 4, 4]"):
        deslice(tile, dst, [0, 0], [2, 2], [1, 1], 1)

    for fn in (bad_arity, bad_target, bad_space):
        monkeypatch.setitem(fn.__globals__, "deslice", deslice)

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
    alloc_ops = [op for op in loop_body_ops if isinstance(op, DmaAllocOp)]
    slice_ops = [op for op in loop_body_ops if isinstance(op, DmaSliceOp)]
    deslice_ops = [op for op in loop_body_ops if isinstance(op, DmaDesliceOp)]
    assert len(alloc_ops) == 2
    assert len(slice_ops) == 2
    assert len(deslice_ops) == 1
    assert not any(isinstance(op, DmaLoadOp) for op in loop_body_ops)
    assert not any(isinstance(op, DmaStoreOp) for op in loop_body_ops)
    assert not any(isinstance(op, arith.IndexCastOp) for op in loop_body_ops)
    assert alloc_ops[0].result.type.space.space.data == "local"
    loop_body = loop_ops[0].body.block
    assert isinstance(loop_body.args[0].type, SymbolValueType)
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


# MGEN-011A
# 创建者: 小李飞刀
# 最后一次更改: 小李飞刀
# 最近一次运行测试时间: 2026-03-27 04:14:28 +0800
# 最近一次运行成功时间: 2026-03-27 04:14:28 +0800
# 功能说明: 验证 nn.truediv 在 dtype 不一致时插入 dma.cast 并使用固定优先级决议 dtype。
# 测试目的: 保证 truediv lowering 结果包含 dma.cast + nn.truediv 且输出类型一致。
# 使用示例: pytest -q test/dsl/test_ast_visitor.py -k test_tensor_truediv_dtype_promotion_lowering
# 对应功能实现文件路径: kernel_gen/dsl/emit_mlir.py, kernel_gen/dsl/mlir_gen.py
# 对应 spec 文件路径: spec/dsl/emit_mlir.md, spec/dsl/mlir_gen.md
# 对应测试文件路径: test/dsl/test_ast_visitor.py
def test_tensor_truediv_dtype_promotion_lowering() -> None:
    # 功能说明: 构造 f32 / i32 的 truediv 场景，验证 lowering 后按 promotion 输出 f32。
    # 使用示例: 配合 build_func_op(truediv, lhs_memory, rhs_memory) 生成目标 IR。
    def truediv(
        x: "Tensor[f32, 2, 2]",
        y: "Tensor[i32, 2, 2]",
    ) -> "Tensor[f32, 2, 2]":
        return x / y

    lhs_memory = Memory([2, 2], NumericType.Float32)
    rhs_memory = Memory([2, 2], NumericType.Int32)
    func_op = build_func_op(truediv, lhs_memory, rhs_memory)
    cast_ops = [op for op in func_op.body.block.ops if isinstance(op, DmaCastOp)]
    div_ops = [op for op in func_op.body.block.ops if isinstance(op, NnTrueDivOp)]
    assert len(cast_ops) == 1
    assert len(div_ops) == 1
    expected_type = _memory_to_nn_type(Memory([2, 2], NumericType.Float32))
    assert cast_ops[0].result.type == expected_type
    assert div_ops[0].result.type == expected_type


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


# MGEN-013A
# 创建者: 摸鱼小分队
# 最后一次更改: 摸鱼小分队
# 最近一次运行测试时间: 2026-03-27 03:45:00 +0800
# 最近一次运行成功时间: 2026-03-27 03:45:00 +0800
# 功能说明: 验证 build_func_op 在 nn.ne 场景支持 Tensor[i1, ...] 返回注解。
# 测试目的: 锁定 nn.ne 的 dtype 解析与 lowering 闭环，确保结果 element type 为 i1。
# 使用示例: pytest -q test/dsl/test_ast_visitor.py -k test_build_func_op_lowers_nn_ne_with_tensor_i1_return_annotation
# 对应功能实现文件路径: kernel_gen/dsl/ast.py, kernel_gen/dsl/emit_mlir.py, kernel_gen/dsl/mlir_gen.py
# 对应 spec 文件路径: spec/dsl/ast.md, spec/dsl/emit_mlir.md, spec/dsl/mlir_gen.md
# 对应测试文件路径: test/dsl/test_ast_visitor.py
def test_build_func_op_lowers_nn_ne_with_tensor_i1_return_annotation() -> None:
    def ne_kernel(
        lhs: "Tensor[f32, 2, 2]",
        rhs: "Tensor[f32, 2, 2]",
    ) -> "Tensor[i1, 2, 2]":
        return lhs != rhs

    func_op = build_func_op(ne_kernel, _tensor_arg([2, 2]), _tensor_arg([2, 2]))

    ne_ops = [op for op in func_op.body.block.ops if isinstance(op, NnNeOp)]
    return_ops = [op for op in func_op.body.block.ops if isinstance(op, func.ReturnOp)]
    if len(ne_ops) != 1:
        raise AssertionError("expected exactly one nn.ne op")
    if len(return_ops) != 1:
        raise AssertionError("expected exactly one func.return op")
    if not isinstance(ne_ops[0].result.type, NnMemoryType):
        raise AssertionError("expected nn.ne result type to be nn.memory")
    if ne_ops[0].result.type.element_type != i1:
        raise AssertionError("expected nn.ne result element type to be i1")
    if return_ops[0].arguments[0].type != ne_ops[0].result.type:
        raise AssertionError("expected return type to match nn.ne result type")


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


# MGEN-034 / EMIT-028
# 创建者: 我不是牛马
# 最后一次更改: 我不是牛马
# 最近一次运行测试时间: 2026-03-27 04:16:44 +0800
# 最近一次运行成功时间: 2026-03-27 04:16:44 +0800
# 功能说明: 验证 nn.sub dtype promotion 会插入 dma.cast 并返回目标 dtype 的 nn.sub。
# 测试目的: 锁定 build_func_op 对 nn.sub 混合 dtype 的 cast lowering 与返回类型。
# 使用示例: pytest -q test/dsl/test_ast_visitor.py -k test_build_func_op_lowers_nn_sub_dtype_promotion_with_cast
# 对应功能实现文件路径: kernel_gen/dsl/mlir_gen.py, kernel_gen/dsl/emit_mlir.py
# 对应 spec 文件路径: spec/dsl/mlir_gen.md, spec/dsl/emit_mlir.md
# 对应测试文件路径: test/dsl/test_ast_visitor.py
def test_build_func_op_lowers_nn_sub_dtype_promotion_with_cast() -> None:
    def sub(
        lhs: "Tensor[f32, 2, 2]",
        rhs: "Tensor[i32, 2, 2]",
    ) -> "Tensor[i32, 2, 2]":
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


# EMIT-033
# 创建者: 小李飞刀
# 最后一次更改: 小李飞刀
# 功能说明: 验证 build_func_op 支持 nn.add 的 memory+const lowering。
# 测试目的: 锁定 AST visitor 链路对 tensor + const 的 nn.add 发射，并确保无需额外 dma.cast 时直接复用 memory dtype。
# 使用示例: pytest -q test/dsl/test_ast_visitor.py -k test_build_func_op_lowers_nn_add_memory_const_without_dma_cast
# 对应功能实现文件路径: kernel_gen/dsl/ast_visitor.py, kernel_gen/dsl/emit_mlir.py
# 对应 spec 文件路径: spec/dsl/emit_mlir.md
# 对应测试文件路径: test/dsl/test_ast_visitor.py
def test_build_func_op_lowers_nn_add_memory_const_without_dma_cast() -> None:
    def add(lhs: "Tensor[f32, 2, 2]") -> "Tensor[f32, 2, 2]":
        return lhs + 1

    lhs_memory = Memory([2, 2], NumericType.Float32)
    expected_type = _memory_to_nn_type(lhs_memory)

    func_op = build_func_op(add, lhs_memory)
    cast_ops = [op for op in func_op.body.block.ops if isinstance(op, DmaCastOp)]
    add_ops = [op for op in func_op.body.block.ops if isinstance(op, NnAddOp)]
    return_ops = [op for op in func_op.body.block.ops if isinstance(op, func.ReturnOp)]

    assert len(cast_ops) == 0
    assert len(add_ops) == 1
    assert len(return_ops) == 1
    assert isinstance(add_ops[0].rhs.owner, arith.SIToFPOp)
    assert add_ops[0].result.type == expected_type
    assert return_ops[0].arguments[0].type == expected_type

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
# 最后一次更改: 我不是牛马
# 最近一次运行测试时间: 2026-03-26 22:20:00 +0800
# 最近一次运行成功时间: 2026-03-26 22:20:00 +0800
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
    int_memory = Memory([2, 2], NumericType.Int32)
    int_tensor = TensorAST(name="xi", memory=int_memory, location=None)
    int_tensor_type = _memory_to_nn_type(int_memory)
    type_map[_expr_key(int_tensor)] = int_tensor_type
    half_memory = Memory([2, 2], NumericType.Float16)
    half_tensor = TensorAST(name="xh", memory=half_memory, location=None)
    half_tensor_type = _memory_to_nn_type(half_memory)
    type_map[_expr_key(half_tensor)] = half_tensor_type
    float_const = ConstAST(1.5)

    assert _infer_expr_type(float_const, type_map) == f32
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

    for compare_op in ("eq", "ge", "gt", "le", "lt", "ne"):
        assert _infer_expr_type(CompareExprAST(op=compare_op, lhs=sym_lhs, rhs=sym_rhs), type_map) == i1
    with pytest.raises(_LoweringError, match="Unsupported symbol compare op"):
        _infer_expr_type(CompareExprAST(op="cmp", lhs=sym_lhs, rhs=sym_rhs), type_map)

    mixed_type_map = {
        _expr_key(int_tensor): int_tensor_type,
        _expr_key(half_tensor): half_tensor_type,
    }
    mixed_const_type = _infer_expr_type(BinaryExprAST(op="add", lhs=int_tensor, rhs=float_const, location=None), mixed_type_map)
    assert isinstance(mixed_const_type, NnMemoryType)
    assert mixed_const_type.shape == int_tensor_type.shape
    assert mixed_const_type.stride == int_tensor_type.stride
    assert mixed_const_type.element_type == f32

    mixed_type_map[_expr_key(sym_lhs)] = SymbolValueType.from_expr("K")
    mixed_symbol_expr = BinaryExprAST(op="add", lhs=half_tensor, rhs=sym_lhs, location=None)
    mixed_symbol_type = _infer_expr_type(mixed_symbol_expr, mixed_type_map)
    assert isinstance(mixed_symbol_type, NnMemoryType)
    assert mixed_symbol_type.shape == half_tensor_type.shape
    assert mixed_symbol_type.stride == half_tensor_type.stride
    assert mixed_symbol_type.element_type == half_tensor_type.element_type

    scalar_only_type_map = {_expr_key(sym_lhs): i32, _expr_key(sym_rhs): i32}
    with pytest.raises(_LoweringError, match="nn.add requires at least one nn.memory operand"):
        _infer_expr_type(BinaryExprAST(op="add", lhs=sym_lhs, rhs=sym_rhs), scalar_only_type_map)

    invalid_scalar_type_map = {_expr_key(int_tensor): int_tensor_type, _expr_key(sym_lhs): i1}
    with pytest.raises(_LoweringError, match="nn.add scalar element_type must be i32/f16/f32 or symbol.int"):
        _infer_expr_type(BinaryExprAST(op="add", lhs=int_tensor, rhs=sym_lhs, location=None), invalid_scalar_type_map)

    compare_type_map = {_expr_key(sym_lhs): i32, _expr_key(sym_rhs): i32}
    with pytest.raises(_LoweringError, match="Compare op operands must have nn.memory type"):
        _infer_expr_type(CompareExprAST(op="eq", lhs=sym_lhs, rhs=sym_rhs), compare_type_map)

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

    mixed_int_memory = Memory([2, 2], NumericType.Int32)
    mixed_int_tensor = TensorAST(name="xi", memory=mixed_int_memory, location=None)
    mixed_int_type = _memory_to_nn_type(mixed_int_memory)
    mixed_block = Block(arg_types=[mixed_int_type])
    mixed_ctx = EmitContext(builder=mixed_block, symbols={"xi": mixed_block.args[0]}, types={})
    mixed_ctx._set_cache(_expr_key(mixed_int_tensor), mixed_block.args[0])
    mixed_ctx.types[_expr_key(mixed_int_tensor)] = mixed_int_type
    mixed_const_expr = BinaryExprAST(op="add", lhs=mixed_int_tensor, rhs=ConstAST(1.5), location=None)
    mixed_const_value = _lower_expr(mixed_const_expr, mixed_ctx)
    mixed_const_cast_ops = [op for op in mixed_block.ops if isinstance(op, DmaCastOp)]
    mixed_const_add_ops = [op for op in mixed_block.ops if isinstance(op, NnAddOp)]
    assert len(mixed_const_cast_ops) == 1
    assert len(mixed_const_add_ops) == 1
    assert mixed_const_value is mixed_const_add_ops[0].result
    assert mixed_const_cast_ops[0].result.type == mixed_const_add_ops[0].result.type
    assert mixed_const_add_ops[0].lhs is mixed_const_cast_ops[0].result
    assert isinstance(mixed_const_add_ops[0].rhs.owner, arith.ConstantOp)

    mixed_half_memory = Memory([2, 2], NumericType.Float16)
    mixed_half_tensor = TensorAST(name="xh", memory=mixed_half_memory, location=None)
    mixed_half_type = _memory_to_nn_type(mixed_half_memory)
    mixed_symbol = ScalarArgAST("k", int, is_symbolic=True)
    mixed_symbol_block = Block(arg_types=[mixed_half_type, SymbolValueType.from_expr("K")])
    mixed_symbol_ctx = EmitContext(
        builder=mixed_symbol_block,
        symbols={"xh": mixed_symbol_block.args[0], "k": mixed_symbol_block.args[1]},
        types={},
    )
    mixed_symbol_ctx._set_cache(_expr_key(mixed_half_tensor), mixed_symbol_block.args[0])
    mixed_symbol_ctx._set_cache(_expr_key(mixed_symbol), mixed_symbol_block.args[1])
    mixed_symbol_ctx.types[_expr_key(mixed_half_tensor)] = mixed_half_type
    mixed_symbol_ctx.types[_expr_key(mixed_symbol)] = mixed_symbol_block.args[1].type
    mixed_symbol_expr = BinaryExprAST(op="add", lhs=mixed_half_tensor, rhs=mixed_symbol, location=None)
    mixed_symbol_value = _lower_expr(mixed_symbol_expr, mixed_symbol_ctx)
    mixed_symbol_cast_ops = [op for op in mixed_symbol_block.ops if isinstance(op, arith.SIToFPOp)]
    mixed_symbol_add_ops = [op for op in mixed_symbol_block.ops if isinstance(op, NnAddOp)]
    assert len(mixed_symbol_cast_ops) == 1
    assert len(mixed_symbol_add_ops) == 1
    assert mixed_symbol_value is mixed_symbol_add_ops[0].result
    assert mixed_symbol_add_ops[0].rhs is mixed_symbol_cast_ops[0].result
    assert mixed_symbol_add_ops[0].result.type == mixed_half_type

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
# 最近一次运行测试时间: 2026-03-26 22:20:00 +0800
# 最近一次运行成功时间: 2026-03-26 22:20:00 +0800
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
# 最后一次更改: 我不是牛马
# 最近一次运行测试时间: 2026-03-26 22:20:00 +0800
# 最近一次运行成功时间: 2026-03-26 22:20:00 +0800
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

    with pytest.raises(_LoweringError, match="Unsupported symbol compare op"):
        _lower_expr(CompareExprAST(lhs=lhs, rhs=rhs, op="cmp", location=None), symbol_ctx)

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
# 使用示例: pytest -q test/dsl/test_ast_visitor.py -k test_emit_mlir_lowers_symbol_ge
# 对应功能实现文件路径: kernel_gen/dsl/emit_mlir.py
# 对应 spec 文件路径: spec/dsl/emit_mlir.md
# 对应测试文件路径: test/dsl/test_ast_visitor.py
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


def _assert_emit_mlir_lowers_symbol_compare(op_name: str, op_type: type[object]) -> None:
    """断言 ast_visitor 侧的 emit helper 会将符号 compare family lowering 到对应 symbol op。

    创建者: 朽木露琪亚
    最后一次更改: 朽木露琪亚

    功能说明:
    - 复用同一套 block/context 初始化逻辑覆盖 `gt/le/lt/ne`。

    使用示例:
    - _assert_emit_mlir_lowers_symbol_compare("gt", SymbolGtOp)

    关联文件:
    - spec: spec/dsl/emit_mlir.md
    - test: test/dsl/test_ast_visitor.py
    - 功能实现: kernel_gen/dsl/emit_mlir.py
    """

    block = Block(arg_types=[SymbolValueType.from_expr("A"), SymbolValueType.from_expr("B")])
    ctx = EmitContext(builder=block, symbols={"a": block.args[0], "b": block.args[1]}, types={})
    lhs = ScalarArgAST(name="a", value_type=int, is_symbolic=True)
    rhs = ScalarArgAST(name="b", value_type=int, is_symbolic=True)
    ctx._set_cache(_expr_key(lhs), block.args[0])
    ctx._set_cache(_expr_key(rhs), block.args[1])
    ctx.types[_expr_key(lhs)] = block.args[0].type
    ctx.types[_expr_key(rhs)] = block.args[1].type

    result = _lower_expr(CompareExprAST(op=op_name, lhs=lhs, rhs=rhs, location=None), ctx)
    assert isinstance(result.owner, op_type)
    assert result.type == i1


def test_emit_mlir_lowers_symbol_gt() -> None:
    _assert_emit_mlir_lowers_symbol_compare("gt", SymbolGtOp)


def test_emit_mlir_lowers_symbol_le() -> None:
    _assert_emit_mlir_lowers_symbol_compare("le", SymbolLeOp)


def test_emit_mlir_lowers_symbol_lt() -> None:
    _assert_emit_mlir_lowers_symbol_compare("lt", SymbolLtOp)


def test_emit_mlir_lowers_symbol_ne() -> None:
    _assert_emit_mlir_lowers_symbol_compare("ne", SymbolNeOp)


# EMIT-002A
# 创建者: 小李飞刀
# 最后一次更改: 咯咯咯
# 最近一次运行测试时间: 2026-03-27 04:40:00 +0800
# 最近一次运行成功时间: 2026-03-27 04:40:00 +0800
# 功能说明: 覆盖 compare 广播路径中 rhs 需要扩展的分支。
# 测试目的: 验证 CompareExprAST(op="ne") 的 rhs 广播与结果 element type 为 i1。
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
# 使用示例: pytest -q test/dsl/test_ast_visitor.py -k test_emit_mlir_compare_memory_mismatch_reports_diagnostics
# 对应功能实现文件路径: kernel_gen/dsl/emit_mlir.py
# 对应 spec 文件路径: spec/dsl/emit_mlir.md
# 对应测试文件路径: test/dsl/test_ast_visitor.py
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
