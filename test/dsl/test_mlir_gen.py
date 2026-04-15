"""MLIR gen integration tests.

创建者: 小李飞刀
最后一次更改: jcc你莫辜负

功能说明:
- 覆盖 build_func_op/build_func_op_from_ast 及相关 lowering 集成回归。

使用示例:
- pytest -q test/dsl/test_mlir_gen.py

覆盖率信息:
- 覆盖率命令: coverage run -m pytest -q test/dsl/test_mlir_gen.py && coverage report --include=kernel_gen/dsl/mlir_gen.py -m
- 覆盖率结果: 未统计（待补充）
- 达标线: 95%

关联文件:
- 功能实现: [kernel_gen/dsl/mlir_gen.py](kernel_gen/dsl/mlir_gen.py)
- Spec 文档: [spec/dsl/mlir_gen.md](spec/dsl/mlir_gen.md)
- 测试文件: [test/dsl/test_mlir_gen.py](test/dsl/test_mlir_gen.py)
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
    SymbolRefAttr,
    f32,
    i1,
    i8,
    i32,
)
from xdsl.ir import Block
from xdsl.printer import Printer
from xdsl.utils.exceptions import VerifyException

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
    ArchBarrierOp,
    ArchGetDynamicMemoryOp,
    ArchGetBlockIdOp,
    ArchGetBlockNumOp,
    ArchGetSubthreadIdOp,
    ArchGetSubthreadNumOp,
    ArchGetThreadIdOp,
    ArchGetThreadNumOp,
    ArchLaunchKernelOp,
    ArchScopeAttr,
    ArchVisibilityAttr,
)
from kernel_gen.dialect.nn import (
    NnAddOp,
    NnBroadcastOp,
    NnCastOp,
    NnEqOp,
    NnExpOp,
    NnImg2col1dOp,
    NnImg2col2dOp,
    NnMatmulOp,
    NnMemorySpaceAttr,
    NnMemoryType,
    NnNeOp,
    NnReduceMaxOp,
    NnReduceMinOp,
    NnReduceSumOp,
    NnSoftmaxOp,
    NnSubOp,
    NnTrueDivOp,
)
from kernel_gen.dialect.symbol import (
    SymbolAddOp,
    SymbolDivOp,
    SymbolEqOp,
    SymbolFloorDivOp,
    SymbolForOp,
    SymbolIterType,
    SymbolGtOp,
    SymbolGeOp,
    SymbolGetDimOp,
    SymbolGetStrideOp,
    SymbolLeOp,
    SymbolLtOp,
    SymbolMulOp,
    SymbolNeOp,
    SymbolSubOp,
    SymbolToFloatOp,
    SymbolValueType,
)
from kernel_gen.dsl.ast import (
    AstParseError,
    ArchBarrierAST,
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
    SymbolToFloatAST,
    StoreAST,
    TensorAST,
    TensorAxisAccessAST,
    VarAST,
    ScalarArgAST,
    _ParseFailure,
    parse_function,
)
from kernel_gen.dsl.ast_visitor import AstVisitor, AstVisitorError
from kernel_gen.dsl.mlir_gen.emit.core import (
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
from kernel_gen.symbol_variable.type import Farmat, NumericType


def _tensor_arg(shape: list[object]) -> Memory:
    """构造默认使用 `f32` 的测试 tensor 参数。

    创建者: 朽木露琪亚
    最后一次更改: 朽木露琪亚

    功能说明:
    - 为 `test_mlir_gen.py` 中的 helper / case 统一生成连续布局的 `Memory`。
    - 默认使用 `NumericType.Float32`，避免各测试重复拼装基础参数。

    使用示例:
    - tensor = _tensor_arg([4, 8])

    关联文件:
    - spec: [spec/dsl/mlir_gen.md](spec/dsl/mlir_gen.md)
    - test: [test/dsl/test_mlir_gen.py](test/dsl/test_mlir_gen.py)
    - 功能实现: [kernel_gen/dsl/mlir_gen.py](kernel_gen/dsl/mlir_gen.py)
    """
    return Memory(shape, NumericType.Float32)

# 注意: 这些 helper 作为 `mlir_gen(...)` 的 callee 会被解析/下沉到 IR，
# 因此函数体内不能包含 docstring（否则会被解析为常量表达式并触发 lowering 错误）。
#
# 创建者: 小李飞刀
# 最后一次更改: 小李飞刀
# 功能说明: 作为最底层 callee，提供可被 mlir_gen 收集的最小加法函数体。
# 使用示例: _ = _mlir_gen_transitive_leaf(x)
# spec: spec/dsl/mlir_gen.md
# test: test/dsl/test_mlir_gen.py
# 功能实现: kernel_gen/dsl/mlir_gen.py
def _mlir_gen_transitive_leaf(x: "Tensor[f32, 4]") -> "Tensor[f32, 4]":
    return x + x


# 创建者: 小李飞刀
# 最后一次更改: 小李飞刀
# 功能说明: 作为中间层 callee，转调 leaf helper 形成可追踪调用链。
# 使用示例: _ = _mlir_gen_transitive_mid(x)
# spec: spec/dsl/mlir_gen.md
# test: test/dsl/test_mlir_gen.py
# 功能实现: kernel_gen/dsl/mlir_gen.py
def _mlir_gen_transitive_mid(x: "Tensor[f32, 4]") -> "Tensor[f32, 4]":
    return _mlir_gen_transitive_leaf(x)


# 创建者: 小李飞刀
# 最后一次更改: 小李飞刀
# 功能说明: 作为 DFS 左子树的 leaf，提供可序列化的最小算子体。
# 使用示例: _ = _mlir_gen_dfs_left_leaf(x)
# spec: spec/dsl/mlir_gen.md
# test: test/dsl/test_mlir_gen.py
# 功能实现: kernel_gen/dsl/mlir_gen.py
def _mlir_gen_dfs_left_leaf(x: "Tensor[f32, 4]") -> "Tensor[f32, 4]":
    return x + x


# 创建者: 小李飞刀
# 最后一次更改: 小李飞刀
# 功能说明: 作为 DFS 左分支节点，转调 left leaf 构成可稳定遍历的调用链。
# 使用示例: _ = _mlir_gen_dfs_left(x)
# spec: spec/dsl/mlir_gen.md
# test: test/dsl/test_mlir_gen.py
# 功能实现: kernel_gen/dsl/mlir_gen.py
def _mlir_gen_dfs_left(x: "Tensor[f32, 4]") -> "Tensor[f32, 4]":
    return _mlir_gen_dfs_left_leaf(x)


# 创建者: 小李飞刀
# 最后一次更改: 小李飞刀
# 功能说明: 作为 DFS 右子树的 leaf，提供可序列化的最小算子体。
# 使用示例: _ = _mlir_gen_dfs_right_leaf(x)
# spec: spec/dsl/mlir_gen.md
# test: test/dsl/test_mlir_gen.py
# 功能实现: kernel_gen/dsl/mlir_gen.py
def _mlir_gen_dfs_right_leaf(x: "Tensor[f32, 4]") -> "Tensor[f32, 4]":
    return x + x


# 创建者: 小李飞刀
# 最后一次更改: 小李飞刀
# 功能说明: 作为 DFS 右分支节点，转调 right leaf 构成可稳定遍历的调用链。
# 使用示例: _ = _mlir_gen_dfs_right(x)
# spec: spec/dsl/mlir_gen.md
# test: test/dsl/test_mlir_gen.py
# 功能实现: kernel_gen/dsl/mlir_gen.py
def _mlir_gen_dfs_right(x: "Tensor[f32, 4]") -> "Tensor[f32, 4]":
    return _mlir_gen_dfs_right_leaf(x)


# 创建者: 小李飞刀
# 最后一次更改: 小李飞刀
# 功能说明: 构造递归调用链用于验证 mlir_gen 拒绝递归 callee。
# 使用示例: _ = _mlir_gen_recursive_a(x)
# spec: spec/dsl/mlir_gen.md
# test: test/dsl/test_mlir_gen.py
# 功能实现: kernel_gen/dsl/mlir_gen.py
def _mlir_gen_recursive_a(x: "Tensor[f32, 4]") -> "Tensor[f32, 4]":
    return _mlir_gen_recursive_b(x)


# 创建者: 小李飞刀
# 最后一次更改: 小李飞刀
# 功能说明: 与 recursive_a 配对形成递归调用，用于触发递归拒绝路径。
# 使用示例: _ = _mlir_gen_recursive_b(x)
# spec: spec/dsl/mlir_gen.md
# test: test/dsl/test_mlir_gen.py
# 功能实现: kernel_gen/dsl/mlir_gen.py
def _mlir_gen_recursive_b(x: "Tensor[f32, 4]") -> "Tensor[f32, 4]":
    return _mlir_gen_recursive_a(x)


# 创建者: 小李飞刀
# 最后一次更改: 小李飞刀
# 功能说明: 作为签名不一致 helper，用于锁定 mlir_gen 的签名一致性检查。
# 使用示例: _ = _mlir_gen_inconsistent_signature_helper(x)
# spec: spec/dsl/mlir_gen.md
# test: test/dsl/test_mlir_gen.py
# 功能实现: kernel_gen/dsl/mlir_gen.py
def _mlir_gen_inconsistent_signature_helper(x: "Tensor[f32, 2, 2]") -> "Tensor[f32, 2, 2]":
    return x


def _module_from_func(fn: object, *runtime_args: object) -> ModuleOp:
    """将 DSL 函数 helper 包装为单函数 `ModuleOp`。

    创建者: 朽木露琪亚
    最后一次更改: 朽木露琪亚

    功能说明:
    - 调用 `build_func_op(...)` 生成 `func.func`。
    - 统一包装到 `ModuleOp` 中，便于后续打印与结构断言。

    使用示例:
    - module = _module_from_func(kernel, 16, 32)

    关联文件:
    - spec: [spec/dsl/mlir_gen.md](spec/dsl/mlir_gen.md)
    - test: [test/dsl/test_mlir_gen.py](test/dsl/test_mlir_gen.py)
    - 功能实现: [kernel_gen/dsl/mlir_gen.py](kernel_gen/dsl/mlir_gen.py)
    """
    return ModuleOp([build_func_op(fn, *runtime_args)])


def _module_from_ast(func_ast: FunctionAST) -> ModuleOp:
    """将已解析的 `FunctionAST` 包装为单函数 `ModuleOp`。

    创建者: 朽木露琪亚
    最后一次更改: 朽木露琪亚

    功能说明:
    - 调用 `build_func_op_from_ast(...)` 生成 `func.func`。
    - 供 AST 级断言复用，避免测试内部重复创建 `ModuleOp`。

    使用示例:
    - module = _module_from_ast(func_ast)

    关联文件:
    - spec: [spec/dsl/mlir_gen.md](spec/dsl/mlir_gen.md)
    - test: [test/dsl/test_mlir_gen.py](test/dsl/test_mlir_gen.py)
    - 功能实现: [kernel_gen/dsl/mlir_gen.py](kernel_gen/dsl/mlir_gen.py)
    """
    return ModuleOp([build_func_op_from_ast(func_ast)])


def _print_module(module: ModuleOp) -> str:
    """将 `ModuleOp` 打印为可断言的 MLIR 文本。

    创建者: 朽木露琪亚
    最后一次更改: 朽木露琪亚

    功能说明:
    - 通过 `Printer` 将 `ModuleOp` 渲染到字符串。
    - 供字符串匹配类测试复用，避免每个 case 手写打印逻辑。

    使用示例:
    - text = _print_module(module)

    关联文件:
    - spec: [spec/dsl/mlir_gen.md](spec/dsl/mlir_gen.md)
    - test: [test/dsl/test_mlir_gen.py](test/dsl/test_mlir_gen.py)
    - 功能实现: [kernel_gen/dsl/mlir_gen.py](kernel_gen/dsl/mlir_gen.py)
    """
    stream = StringIO()
    printer = Printer(stream=stream)
    printer.print_op(module)
    return stream.getvalue()


def _unwrap_index_cast(value: object) -> object:
    """解开测试中常见的单层 `arith.index_cast` 包装。

    创建者: 朽木露琪亚
    最后一次更改: 朽木露琪亚

    功能说明:
    - 若 `value.owner` 是 `arith.IndexCastOp`，返回其输入值。
    - 否则原样返回，便于测试同时兼容 cast 前后两种 IR 形态。

    使用示例:
    - raw_value = _unwrap_index_cast(result)

    关联文件:
    - spec: [spec/dsl/mlir_gen.md](spec/dsl/mlir_gen.md)
    - test: [test/dsl/test_mlir_gen.py](test/dsl/test_mlir_gen.py)
    - 功能实现: [kernel_gen/dsl/mlir_gen.py](kernel_gen/dsl/mlir_gen.py)
    """
    owner = getattr(value, "owner", None)
    if isinstance(owner, arith.IndexCastOp):
        return owner.input
    return value


def _parse_function_from_source(
    monkeypatch: pytest.MonkeyPatch,
    source: str,
    runtime_table: dict[str, object] | None = None,
) -> FunctionAST:
    """使用伪造源码与运行时表解析 DSL 函数。

    创建者: 朽木露琪亚
    最后一次更改: 朽木露琪亚

    功能说明:
    - 通过 monkeypatch 覆盖 `inspect.getsource(...)`，让测试可直接用字符串构造 DSL 函数源码。
    - 将 `runtime_table` 一并传入 `_parse_function_with_env(...)`，覆盖 runtime 参数参与签名/符号解析的场景。

    使用示例:
    - func_ast = _parse_function_from_source(monkeypatch, \"def kernel(x):\\n    return x\\n\")

    关联文件:
    - spec: [spec/dsl/ast.md](spec/dsl/ast.md)
    - test: [test/dsl/test_mlir_gen.py](test/dsl/test_mlir_gen.py)
    - 功能实现: [kernel_gen/dsl/ast.py](kernel_gen/dsl/ast.py)
    """
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
# 使用示例: pytest -q test/dsl/test_mlir_gen.py -k test_build_func_op_lowers_arch_get_block_id_query
# 对应功能实现文件路径: kernel_gen/dsl/ast.py, kernel_gen/dsl/mlir_gen.py
# 对应 spec 文件路径: spec/dsl/ast.md, spec/dsl/mlir_gen.md
# 对应测试文件路径: test/dsl/test_mlir_gen.py
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


# AST-015A / MGEN-041
# 创建者: 朽木露琪亚
# 最后一次更改: 朽木露琪亚
# 最近一次运行测试时间: 2026-04-05 00:00:00 +0800
# 最近一次运行成功时间: 2026-04-05 00:00:00 +0800
# 功能说明: 验证 DSL 函数体内 Import/ImportFrom 被忽略，不影响 AST 解析与 lowering。
# 测试目的: 确保 import 不进入 AST 语句列表，build_func_op 仍能生成 arch.get_block_id。
# 使用示例: pytest -q test/dsl/test_mlir_gen.py -k test_parse_function_ignores_import_statements
# 对应功能实现文件路径: kernel_gen/dsl/ast.py, kernel_gen/dsl/mlir_gen.py
# 对应 spec 文件路径: spec/dsl/ast.md, spec/dsl/mlir_gen.md
# 对应测试文件路径: test/dsl/test_mlir_gen.py
def test_parse_function_ignores_import_statements(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from kernel_gen.operation.arch import get_block_id

    def get_block_id_kernel() -> int:
        import kernel_gen.operation.arch as arch
        from kernel_gen.operation.arch import get_block_id

        return get_block_id()

    monkeypatch.setitem(get_block_id_kernel.__globals__, "get_block_id", get_block_id)

    func_ast = parse_function(get_block_id_kernel)
    if len(func_ast.body.statements) != 1:
        raise AssertionError("expected import statements to be skipped from AST body")
    stmt = func_ast.body.statements[0]
    if not isinstance(stmt, ArchQueryAST):
        raise AssertionError("expected get_block_id kernel to parse into ArchQueryAST")
    if stmt.query_name != "get_block_id":
        raise AssertionError("expected arch query name to stay get_block_id")

    func_op = build_func_op(get_block_id_kernel)
    body_ops = list(func_op.body.block.ops)
    query_ops = [op for op in body_ops if isinstance(op, ArchGetBlockIdOp)]
    return_ops = [op for op in body_ops if isinstance(op, func.ReturnOp)]
    if len(query_ops) != 1:
        raise AssertionError("expected exactly one arch.get_block_id op")
    if len(return_ops) != 1:
        raise AssertionError("expected exactly one func.return op")


# AST-014C / MGEN-029
# 创建者: 咯咯咯
# 最后一次更改: 咯咯咯
# 最近一次运行测试时间: 2026-03-26 00:27:39 +0800
# 最近一次运行成功时间: 2026-03-26 00:27:39 +0800
# 功能说明: 验证零入参 get_block_num DSL 函数可解析并 lowering 为 arch.get_block_num。
# 测试目的: 锁定 get_block_num 查询的 AST 解析、build_func_op 与 build_func_op_from_ast 返回类型为 !symbol.int<"block_num">。
# 使用示例: pytest -q test/dsl/test_mlir_gen.py -k test_build_func_op_lowers_arch_get_block_num_query
# 对应功能实现文件路径: kernel_gen/dsl/ast.py, kernel_gen/dsl/mlir_gen.py
# 对应 spec 文件路径: spec/dsl/ast.md, spec/dsl/mlir_gen.md
# 对应测试文件路径: test/dsl/test_mlir_gen.py
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


# AST-014E / MGEN-031
# 创建者: 我不是牛马
# 最后一次更改: 我不是牛马
# 最近一次运行测试时间: 2026-03-25 21:41:29 +0800
# 最近一次运行成功时间: 2026-03-25 21:41:29 +0800
# 功能说明: 验证零入参 get_subthread_id DSL 函数可解析并 lowering 为 arch.get_subthread_id。
# 测试目的: 锁定 get_subthread_id 查询的 AST 解析、build_func_op 与 build_func_op_from_ast 返回类型为 !symbol.int<"subthread_id">。
# 使用示例: pytest -q test/dsl/test_mlir_gen.py -k test_build_func_op_lowers_arch_get_subthread_id_query
# 对应功能实现文件路径: kernel_gen/dsl/ast.py, kernel_gen/dsl/mlir_gen.py
# 对应 spec 文件路径: spec/dsl/ast.md, spec/dsl/mlir_gen.md
# 对应测试文件路径: test/dsl/test_mlir_gen.py
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


# AST-014G / MGEN-032
# 创建者: 朽木露琪亚
# 最后一次更改: 朽木露琪亚
# 最近一次运行测试时间: 2026-03-27 01:38:30 +0800
# 最近一次运行成功时间: 2026-03-27 01:38:30 +0800
# 功能说明: 验证零入参 get_thread_id DSL 函数可解析并 lowering 为 arch.get_thread_id。
# 测试目的: 锁定 get_thread_id 查询的 AST 解析、build_func_op 与 build_func_op_from_ast 返回类型为 !symbol.int<"thread_id">。
# 使用示例: pytest -q test/dsl/test_mlir_gen.py -k test_build_func_op_lowers_arch_get_thread_id_query
# 对应功能实现文件路径: kernel_gen/dsl/ast.py, kernel_gen/dsl/mlir_gen.py
# 对应 spec 文件路径: spec/dsl/ast.md, spec/dsl/mlir_gen.md
# 对应测试文件路径: test/dsl/test_mlir_gen.py
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


# AST-014K / MGEN-038
# 创建者: OpenAI
# 最后一次更改: 小李飞刀
# 最近一次运行测试时间: 2026-03-31 03:20:00 +0800
# 最近一次运行成功时间: 2026-03-31 03:20:00 +0800
# 功能说明: 验证 `Memory.get_shape()[axis]` 可沿 build_func_op/build_func_op_from_ast lowering 为 symbol.get_dim。
# 测试目的: 锁定 get_shape 轴访问在函数构建阶段返回 `!symbol.int` 并发射单个 symbol.get_dim。
# 使用示例: pytest -q test/dsl/test_mlir_gen.py -k test_build_func_op_lowers_symbol_get_dim
# 对应功能实现文件路径: kernel_gen/dsl/ast.py, kernel_gen/dsl/mlir_gen/emit/core.py, kernel_gen/dsl/mlir_gen.py
# 对应 spec 文件路径: spec/dsl/ast.md, spec/dsl/emit_mlir.md, spec/dsl/mlir_gen.md
# 对应测试文件路径: test/dsl/test_mlir_gen.py
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
# 测试目的: 锁定 get_stride 轴访问在函数构建阶段返回 `!symbol.int` 并发射单个 symbol.get_stride。
# 使用示例: pytest -q test/dsl/test_mlir_gen.py -k test_build_func_op_lowers_symbol_get_stride
# 对应功能实现文件路径: kernel_gen/dsl/ast.py, kernel_gen/dsl/mlir_gen/emit/core.py, kernel_gen/dsl/mlir_gen.py
# 对应 spec 文件路径: spec/dsl/ast.md, spec/dsl/emit_mlir.md, spec/dsl/mlir_gen.md
# 对应测试文件路径: test/dsl/test_mlir_gen.py
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


# AST-014K / MGEN-035
# 创建者: 金铲铲大作战
# 最后一次更改: 小李飞刀
# 最近一次运行测试时间: 2026-03-29 18:04:37 +0800
# 最近一次运行成功时间: 2026-03-29 18:04:37 +0800
# 功能说明: 验证零入参 get_thread_num DSL 函数可解析并 lowering 为 arch.get_thread_num。
# 测试目的: 锁定 get_thread_num 查询的 AST 解析、build_func_op 与 build_func_op_from_ast 返回类型为 !symbol.int<"thread_num">。
# 使用示例: pytest -q test/dsl/test_mlir_gen.py -k test_build_func_op_lowers_arch_get_thread_num_query
# 对应功能实现文件路径: kernel_gen/dsl/ast.py, kernel_gen/dsl/mlir_gen.py
# 对应 spec 文件路径: spec/dsl/ast.md, spec/dsl/mlir_gen.md
# 对应测试文件路径: test/dsl/test_mlir_gen.py
def test_build_func_op_lowers_arch_get_thread_num_query(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from kernel_gen.operation.arch import get_thread_num

    def get_thread_num_kernel() -> int:
        return get_thread_num()

    monkeypatch.setitem(get_thread_num_kernel.__globals__, "get_thread_num", get_thread_num)

    func_ast = parse_function(get_thread_num_kernel)
    if len(func_ast.inputs) != 0:
        raise AssertionError("expected get_thread_num kernel to have no inputs")
    if len(func_ast.outputs) != 1:
        raise AssertionError("expected get_thread_num kernel to have one output annotation")
    if len(func_ast.body.statements) != 1:
        raise AssertionError("expected get_thread_num kernel to lower to one AST statement")
    if not isinstance(func_ast.body.statements[0], ArchQueryAST):
        raise AssertionError("expected get_thread_num kernel to parse into ArchQueryAST")
    if func_ast.body.statements[0].query_name != "get_thread_num":
        raise AssertionError("expected arch query name to stay get_thread_num")

    for func_op in (build_func_op(get_thread_num_kernel), build_func_op_from_ast(func_ast)):
        if len(tuple(func_op.body.block.args)) != 0:
            raise AssertionError("expected zero-argument func.func for get_thread_num kernel")
        body_ops = list(func_op.body.block.ops)
        query_ops = [op for op in body_ops if isinstance(op, ArchGetThreadNumOp)]
        return_ops = [op for op in body_ops if isinstance(op, func.ReturnOp)]
        if len(query_ops) != 1:
            raise AssertionError("expected exactly one arch.get_thread_num op")
        if query_ops[0].result.type != SymbolValueType.from_expr("thread_num"):
            raise AssertionError('expected arch.get_thread_num result type to be !symbol.int<"thread_num">')
        if len(return_ops) != 1:
            raise AssertionError("expected exactly one func.return op")
        if len(return_ops[0].arguments) != 1:
            raise AssertionError("expected func.return to carry one value")
        if return_ops[0].arguments[0].type != SymbolValueType.from_expr("thread_num"):
            raise AssertionError('expected func.return type to stay !symbol.int<"thread_num">')


# AST-014I / MGEN-033
# 创建者: 摸鱼小分队
# 最后一次更改: 摸鱼小分队
# 最近一次运行测试时间: 2026-03-27 02:08:59 +0800
# 最近一次运行成功时间: 2026-03-27 02:08:59 +0800
# 功能说明: 验证零入参 get_subthread_num DSL 函数可解析并 lowering 为 arch.get_subthread_num。
# 测试目的: 锁定 get_subthread_num 查询的 AST 解析、build_func_op 与 build_func_op_from_ast 返回类型为 !symbol.int<"subthread_num">。
# 使用示例: pytest -q test/dsl/test_mlir_gen.py -k test_build_func_op_lowers_arch_get_subthread_num_query
# 对应功能实现文件路径: kernel_gen/dsl/ast.py, kernel_gen/dsl/mlir_gen.py
# 对应 spec 文件路径: spec/dsl/ast.md, spec/dsl/mlir_gen.md
# 对应测试文件路径: test/dsl/test_mlir_gen.py
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


# MGEN-035A
# 创建者: 朽木露琪亚
# 最后一次更改: 朽木露琪亚
# 最近一次运行测试时间: 2026-04-02 14:55:00 +0800
# 最近一次运行成功时间: 2026-04-02 14:55:00 +0800
# 功能说明: 验证 get_dynamic_memory 在 import-bound helper 基线下支持 module alias 与 direct symbol alias 两类正向入口。
# 测试目的: 锁定 `arch_alias.get_dynamic_memory(...)` 与 `gdm(...)` 在 build_func_op / build_func_op_from_ast 集成层都能稳定 lowering 为 arch.get_dynamic_memory。
# 使用示例: pytest -q test/dsl/test_mlir_gen.py -k test_build_func_op_lowers_arch_get_dynamic_memory_via_import_bound_aliases
# 对应功能实现文件路径: kernel_gen/dsl/ast.py, kernel_gen/dsl/mlir_gen.py
# 对应 spec 文件路径: spec/dsl/ast.md, spec/dsl/mlir_gen.md
# 对应测试文件路径: test/dsl/test_mlir_gen.py
def test_build_func_op_lowers_arch_get_dynamic_memory_via_import_bound_aliases(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import kernel_gen.operation.arch as arch_module

    def module_alias_kernel() -> "Tensor[i8, ?]":
        return arch_ops.get_dynamic_memory(MemorySpace.TSM)

    def direct_alias_kernel() -> "Tensor[i8, ?]":
        return gdm(MemorySpace.TLM1)

    monkeypatch.setitem(module_alias_kernel.__globals__, "arch_ops", arch_module)
    monkeypatch.setitem(direct_alias_kernel.__globals__, "gdm", arch_module.get_dynamic_memory)

    cases = (
        (module_alias_kernel, MemorySpace.TSM, "tsm", "TSM_SIZE"),
        (direct_alias_kernel, MemorySpace.TLM1, "tlm1", "TLM1_SIZE"),
    )
    for fn, expected_space, expected_space_name, expected_symbol_name in cases:
        func_ast = parse_function(fn)
        if len(func_ast.body.statements) != 1:
            raise AssertionError("expected get_dynamic_memory alias kernel to lower to one AST statement")
        stmt = func_ast.body.statements[0]
        if not isinstance(stmt, ArchGetDynamicMemoryAST):
            raise AssertionError("expected get_dynamic_memory alias kernel to parse into ArchGetDynamicMemoryAST")
        if stmt.space is not expected_space:
            raise AssertionError("expected get_dynamic_memory alias to keep MemorySpace binding")

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
            if query_ops[0].result.type.shape.data[0] != StringAttr(expected_symbol_name):
                raise AssertionError("expected dynamic memory result shape to be rewritten to symbolic capacity name")
            if query_ops[0].result.type.stride.data[0] != IntAttr(1):
                raise AssertionError("expected dynamic memory result stride to stay [1]")
            if query_ops[0].result.type.space.space.data != expected_space_name:
                raise AssertionError("expected dynamic memory result space to match helper binding")
            if len(return_ops) != 1 or len(return_ops[0].arguments) != 1:
                raise AssertionError("expected func.return to carry one dynamic memory value")
            if return_ops[0].arguments[0].type != query_ops[0].result.type:
                raise AssertionError("expected func.return type to stay aligned with arch.get_dynamic_memory result")


# MGEN-004
# 创建者: 小李飞刀
# 最后一次更改: 金铲铲大作战
# 最近一次运行测试时间: 2026-03-22 15:38:56 +0800
# 最近一次运行成功时间: 2026-03-22 15:38:56 +0800
# 功能说明: 验证 build_func_op 生成 func.func 并包含 nn dialect IR。
# 测试目的: 验证 build_func_op 生成 func.func 并包含 nn dialect IR。
# 使用示例: pytest -q test/dsl/test_mlir_gen.py -k test_visit_to_nn_ir_builds_module
# 对应功能实现文件路径: kernel_gen/dsl/mlir_gen.py
# 对应 spec 文件路径: spec/dsl/mlir_gen.md
# 对应测试文件路径: test/dsl/test_mlir_gen.py
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
# 使用示例: pytest -q test/dsl/test_mlir_gen.py -k test_emit_mlir_output
# 对应功能实现文件路径: kernel_gen/dsl/mlir_gen.py
# 对应 spec 文件路径: spec/dsl/mlir_gen.md
# 对应测试文件路径: test/dsl/test_mlir_gen.py
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


# MGEN-001
# 创建者: 朽木露琪亚
# 最后一次更改: 金铲铲大作战
# 最近一次运行测试时间: 2026-03-22 15:38:56 +0800
# 最近一次运行成功时间: 2026-03-22 15:38:56 +0800
# 功能说明: 验证 build_func_op 返回 func.func 并生成正确参数类型。
# 测试目的: 验证 build_func_op 返回 func.func 并生成正确参数类型。
# 使用示例: pytest -q test/dsl/test_mlir_gen.py -k test_build_func_op_returns_func_op
# 对应功能实现文件路径: kernel_gen/dsl/mlir_gen.py
# 对应 spec 文件路径: spec/dsl/mlir_gen.md
# 对应测试文件路径: test/dsl/test_mlir_gen.py
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
# 使用示例: pytest -q test/dsl/test_mlir_gen.py -k test_build_func_op_signature_uses_runtime_args_not_parse_env
# 对应功能实现文件路径: kernel_gen/dsl/mlir_gen.py
# 对应 spec 文件路径: spec/dsl/mlir_gen.md
# 对应测试文件路径: test/dsl/test_mlir_gen.py
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
# 使用示例: pytest -q test/dsl/test_mlir_gen.py -k test_build_func_op_from_ast_preserves_arg_order
# 对应功能实现文件路径: kernel_gen/dsl/mlir_gen.py
# 对应 spec 文件路径: spec/dsl/mlir_gen.md
# 对应测试文件路径: test/dsl/test_mlir_gen.py
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
# 使用示例: pytest -q test/dsl/test_mlir_gen.py -k test_build_func_op_from_ast_uses_runtime_args_for_symbol_signature
# 对应功能实现文件路径: kernel_gen/dsl/mlir_gen.py
# 对应 spec 文件路径: spec/dsl/mlir_gen.md
# 对应测试文件路径: test/dsl/test_mlir_gen.py
def test_build_func_op_from_ast_uses_runtime_args_for_symbol_signature() -> None:
    def only_symbol(expr: int) -> int:
        return expr

    func_ast = parse_function(only_symbol)
    func_op = build_func_op_from_ast(func_ast, runtime_args=[SymbolDim("expr")])
    inputs = list(func_op.function_type.inputs)
    outputs = list(func_op.function_type.outputs)
    assert inputs == [SymbolValueType.from_expr("expr")]
    assert outputs == [SymbolValueType.from_expr("expr")]


# MGEN-002B
# 创建者: OpenAI
# 最后一次更改: 金铲铲大作战
# 最近一次运行测试时间: 2026-03-28 14:20:00 +0800
# 最近一次运行成功时间: 2026-03-28 14:20:00 +0800
# 功能说明: 验证 build_func_op_from_ast 在 runtime_args 省略时按 AST 注解生成签名。
# 测试目的: 证明 runtime_args 缺失时仍可通过 AST 注解构建 symbol 标量签名。
# 使用示例: pytest -q test/dsl/test_mlir_gen.py -k test_build_func_op_from_ast_rejects_symbol_scalar_missing_runtime_args
# 对应功能实现文件路径: kernel_gen/dsl/mlir_gen.py
# 对应 spec 文件路径: spec/dsl/mlir_gen.md
# 对应测试文件路径: test/dsl/test_mlir_gen.py
def test_build_func_op_from_ast_rejects_symbol_scalar_missing_runtime_args() -> None:
    def only_symbol(expr: int) -> int:
        return expr

    func_ast = parse_function(only_symbol)
    func_op = build_func_op_from_ast(func_ast)
    inputs = list(func_op.function_type.inputs)
    outputs = list(func_op.function_type.outputs)
    assert inputs == [SymbolValueType.from_expr("expr")]
    assert outputs == [SymbolValueType.from_expr("expr")]
    with pytest.raises(AstVisitorError, match="runtime_args must align"):
        build_func_op_from_ast(func_ast, runtime_args=[SymbolDim("expr"), SymbolDim("extra")])


# MGEN-002A
# 创建者: 朽木露琪亚
# 最后一次更改: 朽木露琪亚
# 最近一次运行测试时间: 2026-03-25 16:45:00 +0800
# 最近一次运行成功时间: 2026-03-25 16:45:00 +0800
# 功能说明: 验证 build_func_op_from_ast 会把 config 透传给 visitor 与 lowering context。
# 测试目的: 证明 build_func_op_from_ast(..., config=...) 的公开成功路径不是空签名兼容，而是可观察地把配置传入 visitor/context。
# 使用示例: pytest -q test/dsl/test_mlir_gen.py -k test_build_func_op_from_ast_forwards_config_to_visitor_and_context
# 对应功能实现文件路径: kernel_gen/dsl/mlir_gen.py
# 对应 spec 文件路径: spec/dsl/mlir_gen.md
# 对应测试文件路径: test/dsl/test_mlir_gen.py
def test_build_func_op_from_ast_forwards_config_to_visitor_and_context(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import kernel_gen.dsl.mlir_gen.function_builder as function_builder_module

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

    monkeypatch.setattr(function_builder_module, "AstVisitor", RecordingVisitor)
    func_ast = parse_function(identity)
    config: dict[str, object] = {"loop_vars": {"i": "outer"}}
    func_op = build_func_op_from_ast(func_ast, config=config)

    assert isinstance(func_op, func.FuncOp)
    assert captured["visitor_config"] == config
    assert captured["ctx_config"] == config


# MGEN-016
# 创建者: 金铲铲大作战
# 最后一次更改: 金铲铲大作战
# 最近一次运行测试时间: 2026-03-22 14:59:58 +0800
# 最近一次运行成功时间: 2026-03-22 14:59:58 +0800
# 功能说明: 验证 build_func_op 返回类型与 AST 返回注解一致。
# 测试目的: 验证 build_func_op 返回类型与 AST 返回注解一致。
# 使用示例: pytest -q test/dsl/test_mlir_gen.py -k test_build_func_op_return_type_matches_annotation
# 对应功能实现文件路径: kernel_gen/dsl/mlir_gen.py
# 对应 spec 文件路径: spec/dsl/mlir_gen.md
# 对应测试文件路径: test/dsl/test_mlir_gen.py
def test_build_func_op_return_type_matches_annotation() -> None:
    def add(x: "Tensor[f32, 2, 2]") -> "Tensor[f32, 2, 2]":
        return x

    func_ast = parse_function(add)
    func_op = build_func_op(add, _tensor_arg([2, 2]))
    outputs = list(func_op.function_type.outputs)
    assert outputs
    expected = _memory_to_nn_type(func_ast.outputs[0].memory)
    assert outputs[0] == expected


# MGEN-016
# 创建者: 小李飞刀
# 最后一次更改: 我不是牛马
# 最近一次运行测试时间: 2026-03-26 22:20:00 +0800
# 最近一次运行成功时间: 2026-03-26 22:20:00 +0800
# 功能说明: 覆盖 mlir_gen 的符号标量函数与签名构造分支。
# 测试目的: 验证符号标量函数识别与 runtime arg 到 symbol expr 的映射。
# 使用示例: pytest -q test/dsl/test_mlir_gen.py -k test_mlir_gen_symbol_scalar_helpers
# 对应功能实现文件路径: kernel_gen/dsl/mlir_gen.py
# 对应 spec 文件路径: spec/dsl/mlir_gen.md
# 对应测试文件路径: test/dsl/test_mlir_gen.py
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
# 使用示例: pytest -q test/dsl/test_mlir_gen.py -k test_mlir_gen_signature_validation_errors
# 对应功能实现文件路径: kernel_gen/dsl/mlir_gen.py
# 对应 spec 文件路径: spec/dsl/mlir_gen.md
# 对应测试文件路径: test/dsl/test_mlir_gen.py
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
        build_func_op_from_ast(single_tensor, runtime_args=[_tensor_arg([2, 2]), _tensor_arg([2, 2])])

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
# 使用示例: pytest -q test/dsl/test_mlir_gen.py -k test_build_func_op_accepts_joinedstr_tensor_annotation
# 对应功能实现文件路径: kernel_gen/dsl/ast.py
# 对应 spec 文件路径: spec/dsl/mlir_gen.md
# 对应测试文件路径: test/dsl/test_mlir_gen.py
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
# 使用示例: pytest -q test/dsl/test_mlir_gen.py -k test_build_func_op_rejects_invalid_joinedstr_tensor_annotation
# 对应功能实现文件路径: kernel_gen/dsl/ast.py
# 对应 spec 文件路径: spec/dsl/mlir_gen.md
# 对应测试文件路径: test/dsl/test_mlir_gen.py
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
# 最近一次运行测试时间: 2026-03-30 08:31:43 +0800
# 最近一次运行成功时间: 2026-03-30 08:31:43 +0800
# 功能说明: 验证 build_func_op 在 DMA helper 场景下按公开语义生成对应 memory 结果。
# 测试目的: 验证 alloc/copy/cast/view/reshape/flatten 六类 helper 在 build_func_op 链路中都能成功 lowering，且 dma.view 返回类型取自 DSL size/stride。
# 使用示例: pytest -q test/dsl/test_mlir_gen.py -k test_build_func_op_supports_dma_helper_calls
# 对应功能实现文件路径: kernel_gen/dsl/mlir_gen.py
# 对应 spec 文件路径: spec/dsl/mlir_gen.md
# 对应测试文件路径: test/dsl/test_mlir_gen.py
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
    view_ops = [op for op in view_func.body.block.ops if isinstance(op, DmaViewOp)]
    return_ops = [op for op in view_func.body.block.ops if isinstance(op, func.ReturnOp)]
    assert len(view_ops) == 1
    assert len(return_ops) == 1
    assert [attr.data for attr in view_ops[0].result.type.shape.data] == [2, 2]
    assert [attr.data for attr in view_ops[0].result.type.stride.data] == [1, 1]
    assert list(view_func.function_type.outputs) == [view_ops[0].result.type]
    assert return_ops[0].arguments[0].type == view_ops[0].result.type


# MGEN-026B
# 创建者: 朽木露琪亚
# 最后一次更改: 朽木露琪亚
# 最近一次运行测试时间: 2026-04-02 14:30:00 +0800
# 最近一次运行成功时间: 2026-04-02 14:30:00 +0800
# 功能说明: 验证 build_func_op 会拒绝未显式导入的 bare DMA helper 调用。
# 测试目的: 锁定 AST 入口在 import-bound helper 新边界下，对 `view(...)` / `slice(...)` 的未导入裸名字调用统一报 `Unsupported call expression`。
# 使用示例: pytest -q test/dsl/test_mlir_gen.py -k test_build_func_op_rejects_unimported_dma_view_and_slice_helpers
# 对应功能实现文件路径: kernel_gen/dsl/mlir_gen.py, kernel_gen/dsl/ast.py
# 对应 spec 文件路径: spec/dsl/mlir_gen.md, spec/dsl/ast.md
# 对应测试文件路径: test/dsl/test_mlir_gen.py
def test_build_func_op_rejects_unimported_dma_view_and_slice_helpers() -> None:
    source = Memory([4, 4], NumericType.Float32, space=MemorySpace.GM)

    def view_kernel(src: "Tensor[f32, 4, 4]") -> "Tensor[f32, 2, 2]":
        return view(src, [1, 1], [2, 2], [1, 1])

    def slice_kernel(src: "Tensor[f32, 4, 4]") -> "Tensor[f32, 2, 2]":
        return slice(src, [1, 1], [2, 2], [1, 1], MemorySpace.LM)

    for fn in (view_kernel, slice_kernel):
        with pytest.raises(AstVisitorError, match="Unsupported call expression"):
            build_func_op(fn, source)


# MGEN-026C
# 创建者: 小李飞刀
# 最后一次更改: 小李飞刀
# 功能说明: 验证 mlir_gen 对 slice helper 的非法 space 类型继续按 TypeError 对外暴露。
# 测试目的: 锁定 module_builder 的 parse-error 包装与 dma slice expectation 一致。
# 使用示例: pytest -q test/dsl/test_mlir_gen.py -k test_mlir_gen_rejects_dma_slice_invalid_space_type
# 对应功能实现文件路径: kernel_gen/dsl/mlir_gen/module_builder.py
# 对应 spec 文件路径: spec/dsl/mlir_gen.md
# 对应测试文件路径: test/dsl/test_mlir_gen.py
def test_mlir_gen_rejects_dma_slice_invalid_space_type(monkeypatch: pytest.MonkeyPatch) -> None:
    from kernel_gen.dsl.mlir_gen import mlir_gen
    from kernel_gen.operation.dma import slice

    source = Memory([4, 4], NumericType.Float32, space=MemorySpace.GM)

    def bad_slice(src: "Tensor[f32, 4, 4]") -> "Tensor[f32, 2, 2]":
        return slice(src, [0, 0], [2, 2], [1, 1], "LM")

    monkeypatch.setitem(bad_slice.__globals__, "slice", slice)

    with pytest.raises(TypeError, match="slice space must be MemorySpace"):
        mlir_gen(bad_slice, source)


# MGEN-026D
# 创建者: 小李飞刀
# 最后一次更改: 小李飞刀
# 功能说明: 验证 mlir_gen 对 cast helper 的非法 dtype 参数继续按 TypeError 对外暴露。
# 测试目的: 锁定 parser 恢复 cast dtype AST 校验后，module_builder 不再把该错误回包为 AstVisitorError。
# 使用示例: pytest -q test/dsl/test_mlir_gen.py -k test_mlir_gen_rejects_dma_cast_invalid_dtype
# 对应功能实现文件路径: kernel_gen/dsl/mlir_gen/module_builder.py
# 对应 spec 文件路径: spec/dsl/mlir_gen.md
# 对应测试文件路径: test/dsl/test_mlir_gen.py
def test_mlir_gen_rejects_dma_cast_invalid_dtype(monkeypatch: pytest.MonkeyPatch) -> None:
    from kernel_gen.dsl.mlir_gen import mlir_gen
    from kernel_gen.operation.dma import cast

    source = Memory([4, 4], NumericType.Float32, space=MemorySpace.GM)

    def bad_cast(src: "Tensor[f32, 4, 4]") -> "Tensor[f16, 4, 4]":
        return cast(src, "f16")

    monkeypatch.setitem(bad_cast.__globals__, "cast", cast)

    with pytest.raises(TypeError, match="cast dtype must be NumericType"):
        mlir_gen(bad_cast, source)


# MGEN-036
# 创建者: 金铲铲大作战
# 最后一次更改: jcc你莫辜负
# 最近一次运行测试时间: 2026-04-05 03:15:23 +0800
# 最近一次运行成功时间: 2026-04-05 03:15:23 +0800
# 功能说明: 验证 build_func_op 支持 img2col1d helper 并可被 -k 'img2col' 稳定选中。
# 测试目的: 验证 img2col1d 会 lowering 为 nn.img2col1d，且返回类型与注解一致，避免 img2col 过滤 过滤命令 exit 5。
# 使用示例: pytest -q test/dsl/test_mlir_gen.py -k test_build_func_op_supports_img2col1d_helper_call
# 对应功能实现文件路径: kernel_gen/dsl/mlir_gen.py
# 对应 spec 文件路径: spec/dsl/mlir_gen.md
# 对应测试文件路径: test/dsl/test_mlir_gen.py
def test_build_func_op_supports_img2col1d_helper_call() -> None:
    from kernel_gen.operation.nn import img2col1d

    source = Memory([1, 4, 8], NumericType.Float32, space=MemorySpace.GM)

    def img2col1d_kernel(src: "Tensor[f32, 1, 4, 8]") -> "Tensor[f32, 1, 4, 3, 8]":
        return img2col1d(src, kw=3, sw=1, dw=1, pl=1, pr=1)

    func_op = build_func_op(img2col1d_kernel, source)
    img2col_ops = [op for op in func_op.body.block.ops if isinstance(op, NnImg2col1dOp)]
    return_ops = [op for op in func_op.body.block.ops if isinstance(op, func.ReturnOp)]
    assert len(img2col_ops) == 1
    assert len(return_ops) == 1
    assert [attr.data for attr in img2col_ops[0].result.type.shape.data] == [1, 4, 3, 8]
    assert list(func_op.function_type.outputs) == [img2col_ops[0].result.type]
    assert return_ops[0].arguments[0].type == img2col_ops[0].result.type


# MGEN-036D
# 创建者: jcc你莫辜负
# 最后一次更改: jcc你莫辜负
# 最近一次运行测试时间: 2026-04-05 03:15:23 +0800
# 最近一次运行成功时间: 2026-04-05 03:15:23 +0800
# 功能说明: 验证 Tensor 注解中的符号表达式按 SymbolDim 语义解析。
# 测试目的: 锁定 img2col1d 动态维表达式可同时匹配注解与返回类型，避免动态表达式回退。
# 使用示例: pytest -q test/dsl/test_mlir_gen.py -k test_build_func_op_supports_img2col1d_symbolic_annotation
# 对应功能实现文件路径: kernel_gen/dsl/ast.py, kernel_gen/dsl/mlir_gen/emit/core.py, kernel_gen/dsl/mlir_gen.py
# 对应 spec 文件路径: spec/dsl/ast.md, spec/dsl/mlir_gen.md
# 对应测试文件路径: test/dsl/test_mlir_gen.py
def test_build_func_op_supports_img2col1d_symbolic_annotation() -> None:
    from kernel_gen.operation.nn import img2col1d

    w_symbol = SymbolDim("W")
    expected_expr = (w_symbol + 1 + 1 - 1 * (3 - 1) - 1) / 1 + 1
    source = Memory([1, w_symbol, 4], NumericType.Float32, space=MemorySpace.GM)

    def img2col1d_kernel(
        src: "Tensor[f32, 1, W, 4]",
    ) -> "Tensor[f32, 1, (W + 1 + 1 - 1*(3 - 1) - 1) / 1 + 1, 3, 4]":
        return img2col1d(src, kw=3, sw=1, dw=1, pl=1, pr=1)

    func_op = build_func_op(img2col1d_kernel, source)
    img2col_ops = [op for op in func_op.body.block.ops if isinstance(op, NnImg2col1dOp)]
    return_ops = [op for op in func_op.body.block.ops if isinstance(op, func.ReturnOp)]
    assert len(img2col_ops) == 1
    assert len(return_ops) == 1
    shape = img2col_ops[0].result.type.shape.data
    assert isinstance(shape[1], StringAttr)
    assert shape[1].data == expected_expr.get_value()
    assert list(func_op.function_type.outputs) == [img2col_ops[0].result.type]
    assert return_ops[0].arguments[0].type == img2col_ops[0].result.type


# MGEN-036E
# 创建者: 金铲铲大作战
# 最后一次更改: 金铲铲大作战
# 功能说明: 验证 img2col1d helper 支持符号 kernel 参数并保留为 symbol.int operand。
# 测试目的: 锁定 `img2col1d(src, kw=KW, ...)` 不再被当作纯静态整数路径，且输出类型仍按 operation 合同推导。
# 使用示例: pytest -q test/dsl/test_mlir_gen.py -k test_build_func_op_supports_img2col1d_symbolic_kernel_argument
# 对应功能实现文件路径: kernel_gen/dsl/emit_mlir.py, kernel_gen/dsl/mlir_gen.py
# 对应 spec 文件路径: spec/dsl/mlir_gen.md, spec/dsl/emit_mlir.md
# 对应测试文件路径: test/dsl/test_mlir_gen.py
def test_build_func_op_supports_img2col1d_symbolic_kernel_argument() -> None:
    from kernel_gen.operation.nn import img2col1d

    source = Memory([1, SymbolDim("W"), 4], NumericType.Float32, space=MemorySpace.GM, format=Farmat.CLast)
    kw_symbol = SymbolDim("KW")
    expected = img2col1d(source, kw=kw_symbol, sw=1, dw=1, pl=0, pr=0)

    def img2col1d_kernel(
        src: "Tensor[f32, 1, W, 4]",
        KW: int,
    ) -> "Tensor[f32, 1, (W - KW) / 1 + 1, KW, 4]":
        return img2col1d(src, kw=KW, sw=1, dw=1, pl=0, pr=0)

    func_op = build_func_op(img2col1d_kernel, source, kw_symbol)
    img2col_ops = [op for op in func_op.body.block.ops if isinstance(op, NnImg2col1dOp)]
    return_ops = [op for op in func_op.body.block.ops if isinstance(op, func.ReturnOp)]
    assert len(img2col_ops) == 1
    assert len(return_ops) == 1
    assert img2col_ops[0].kw.type == SymbolValueType.from_expr("KW")
    assert img2col_ops[0].result.type == _memory_to_nn_type(expected)
    assert list(func_op.function_type.outputs) == [img2col_ops[0].result.type]
    assert return_ops[0].arguments[0].type == img2col_ops[0].result.type


# MGEN-036A
# 创建者: 金铲铲大作战
# 最后一次更改: jcc你莫辜负
# 最近一次运行测试时间: 2026-04-05 03:15:23 +0800
# 最近一次运行成功时间: 2026-04-05 03:15:23 +0800
# 功能说明: 验证 build_func_op 支持 img2col2d helper 并可被 -k 'img2col' 稳定选中。
# 测试目的: 验证 img2col2d 会 lowering 为 nn.img2col2d，且返回类型与注解一致，避免 img2col 过滤 过滤命令 exit 5。
# 使用示例: pytest -q test/dsl/test_mlir_gen.py -k test_build_func_op_supports_img2col2d_helper_call
# 对应功能实现文件路径: kernel_gen/dsl/mlir_gen.py
# 对应 spec 文件路径: spec/dsl/mlir_gen.md
# 对应测试文件路径: test/dsl/test_mlir_gen.py
def test_build_func_op_supports_img2col2d_helper_call() -> None:
    from kernel_gen.operation.nn import img2col2d

    source = Memory([1, 3, 5, 5], NumericType.Float32, space=MemorySpace.GM)

    def img2col2d_kernel(src: "Tensor[f32, 1, 3, 5, 5]") -> "Tensor[f32, 1, 3, 3, 3, 3, 3]":
        return img2col2d(src, kh=3, kw=3)

    func_op = build_func_op(img2col2d_kernel, source)
    img2col_ops = [op for op in func_op.body.block.ops if isinstance(op, NnImg2col2dOp)]
    return_ops = [op for op in func_op.body.block.ops if isinstance(op, func.ReturnOp)]
    assert len(img2col_ops) == 1
    assert len(return_ops) == 1
    assert [attr.data for attr in img2col_ops[0].result.type.shape.data] == [1, 3, 3, 3, 3, 3]
    assert list(func_op.function_type.outputs) == [img2col_ops[0].result.type]
    assert return_ops[0].arguments[0].type == img2col_ops[0].result.type


# MGEN-036B
# 创建者: jcc你莫辜负
# 最后一次更改: jcc你莫辜负
# 最近一次运行测试时间: 2026-04-05 03:15:23 +0800
# 最近一次运行成功时间: 2026-04-05 03:15:23 +0800
# 功能说明: 验证 build_func_op 支持 exp helper 并下沉为 nn.exp。
# 测试目的: 锁定 exp lowering 生成 NnExpOp 且返回类型匹配，避免 element_unary expectation 回退。
# 使用示例: pytest -q test/dsl/test_mlir_gen.py -k test_build_func_op_supports_exp_helper_call
# 对应功能实现文件路径: kernel_gen/dsl/ast.py, kernel_gen/dsl/mlir_gen/emit/core.py, kernel_gen/dsl/mlir_gen.py
# 对应 spec 文件路径: spec/dsl/mlir_gen.md, spec/dialect/nn.md, spec/operation/nn.md
# 对应测试文件路径: test/dsl/test_mlir_gen.py
def test_build_func_op_supports_exp_helper_call() -> None:
    from kernel_gen.operation.nn import exp

    source = Memory([2, 3], NumericType.Float32, space=MemorySpace.GM)

    def exp_kernel(src: "Tensor[f32, 2, 3]") -> "Tensor[f32, 2, 3]":
        return exp(src)

    func_op = build_func_op(exp_kernel, source)
    exp_ops = [op for op in func_op.body.block.ops if isinstance(op, NnExpOp)]
    return_ops = [op for op in func_op.body.block.ops if isinstance(op, func.ReturnOp)]
    assert len(exp_ops) == 1
    assert len(return_ops) == 1
    assert list(func_op.function_type.outputs) == [exp_ops[0].result.type]
    assert return_ops[0].arguments[0].type == exp_ops[0].result.type


# MGEN-036E
# 创建者: 小李飞刀
# 最后一次更改: 小李飞刀
# 最近一次运行测试时间: 2026-04-06 23:36:32 +0800
# 最近一次运行成功时间: 2026-04-06 23:36:32 +0800
# 功能说明: 验证 build_func_op 支持 softmax helper 并下沉为 nn.softmax。
# 测试目的: 锁定 softmax 生成 NnSoftmaxOp 且 axis 属性稳定传递，避免 expectation 回退。
# 使用示例: pytest -q test/dsl/test_mlir_gen.py -k test_build_func_op_supports_softmax_helper_call
# 对应功能实现文件路径: kernel_gen/dsl/ast.py, kernel_gen/dsl/mlir_gen/emit/core.py, kernel_gen/dsl/mlir_gen.py
# 对应 spec 文件路径: spec/dsl/mlir_gen.md, spec/dialect/nn.md, spec/operation/nn.md
# 对应测试文件路径: test/dsl/test_mlir_gen.py
def test_build_func_op_supports_softmax_helper_call() -> None:
    from kernel_gen.operation.nn import softmax

    source = Memory([2, 3], NumericType.Float32, space=MemorySpace.GM)

    def softmax_kernel(src: "Tensor[f32, 2, 3]") -> "Tensor[f32, 2, 3]":
        return softmax(src, axis=1)

    func_op = build_func_op(softmax_kernel, source)
    softmax_ops = [op for op in func_op.body.block.ops if isinstance(op, NnSoftmaxOp)]
    return_ops = [op for op in func_op.body.block.ops if isinstance(op, func.ReturnOp)]
    assert len(softmax_ops) == 1
    assert len(return_ops) == 1
    assert softmax_ops[0].axis.value.data == 1
    assert list(func_op.function_type.outputs) == [softmax_ops[0].result.type]
    assert return_ops[0].arguments[0].type == softmax_ops[0].result.type


# MGEN-036C
# 创建者: jcc你莫辜负
# 最后一次更改: jcc你莫辜负
# 最近一次运行测试时间: 2026-04-05 03:15:23 +0800
# 最近一次运行成功时间: 2026-04-05 03:15:23 +0800
# 功能说明: 验证 build_func_op 支持 reduce_sum/min/max helper 并生成结构化输出类型。
# 测试目的: 锁定 reduce lowering 覆盖三类 helper 且返回类型匹配，避免 reduce expectation 回退。
# 使用示例: pytest -q test/dsl/test_mlir_gen.py -k test_build_func_op_supports_reduce_helper_calls
# 对应功能实现文件路径: kernel_gen/dsl/ast.py, kernel_gen/dsl/mlir_gen/emit/core.py, kernel_gen/dsl/mlir_gen.py
# 对应 spec 文件路径: spec/dsl/mlir_gen.md, spec/dialect/nn.md, spec/operation/nn.md
# 对应测试文件路径: test/dsl/test_mlir_gen.py
def test_build_func_op_supports_reduce_helper_calls() -> None:
    from kernel_gen.operation.nn import reduce_max, reduce_min, reduce_sum

    source = Memory([2, 3, 4], NumericType.Float32, space=MemorySpace.GM)

    def reduce_sum_kernel(src: "Tensor[f32, 2, 3, 4]") -> "Tensor[f32, 1]":
        return reduce_sum(src)

    def reduce_sum_axis_kernel(src: "Tensor[f32, 2, 3, 4]") -> "Tensor[f32, 2, 1, 4]":
        return reduce_sum(src, axis=1, keepdim=True)

    def reduce_min_kernel(src: "Tensor[f32, 2, 3, 4]") -> "Tensor[f32, 2, 3, 1]":
        return reduce_min(src, axis=[2], keepdim=True)

    def reduce_max_kernel(src: "Tensor[f32, 2, 3, 4]") -> "Tensor[f32, 3, 4]":
        return reduce_max(src, axis=0, keepdim=False)

    sum_op = build_func_op(reduce_sum_kernel, source)
    sum_ops = [op for op in sum_op.body.block.ops if isinstance(op, NnReduceSumOp)]
    sum_returns = [op for op in sum_op.body.block.ops if isinstance(op, func.ReturnOp)]
    assert len(sum_ops) == 1
    assert len(sum_returns) == 1
    assert [attr.data for attr in sum_ops[0].result.type.shape.data] == [1]
    assert sum_returns[0].arguments[0].type == sum_ops[0].result.type

    sum_axis_op = build_func_op(reduce_sum_axis_kernel, source)
    sum_axis_ops = [op for op in sum_axis_op.body.block.ops if isinstance(op, NnReduceSumOp)]
    sum_axis_returns = [op for op in sum_axis_op.body.block.ops if isinstance(op, func.ReturnOp)]
    assert len(sum_axis_ops) == 1
    assert len(sum_axis_returns) == 1
    assert [attr.data for attr in sum_axis_ops[0].result.type.shape.data] == [2, 1, 4]
    assert sum_axis_returns[0].arguments[0].type == sum_axis_ops[0].result.type

    min_op = build_func_op(reduce_min_kernel, source)
    min_ops = [op for op in min_op.body.block.ops if isinstance(op, NnReduceMinOp)]
    min_returns = [op for op in min_op.body.block.ops if isinstance(op, func.ReturnOp)]
    assert len(min_ops) == 1
    assert len(min_returns) == 1
    assert [attr.data for attr in min_ops[0].result.type.shape.data] == [2, 3, 1]
    assert min_returns[0].arguments[0].type == min_ops[0].result.type

    max_op = build_func_op(reduce_max_kernel, source)
    max_ops = [op for op in max_op.body.block.ops if isinstance(op, NnReduceMaxOp)]
    max_returns = [op for op in max_op.body.block.ops if isinstance(op, func.ReturnOp)]
    assert len(max_ops) == 1
    assert len(max_returns) == 1
    assert [attr.data for attr in max_ops[0].result.type.shape.data] == [3, 4]
    assert max_returns[0].arguments[0].type == max_ops[0].result.type


# MGEN-036D
# 创建者: jcc你莫辜负
# 最后一次更改: jcc你莫辜负
# 最近一次运行测试时间: 2026-04-05 00:00:00 +0800
# 最近一次运行成功时间: 2026-04-05 00:00:00 +0800
# 功能说明: 验证 reduce_* 在 axes/keepdim 非法时触发 verifier 失败短语。
# 测试目的: 锁定 reduce verifier 关键短语，避免静默通过或错误信息回退。
# 使用示例: pytest -q test/dsl/test_mlir_gen.py -k test_build_func_op_reduce_verifier_failures
# 对应功能实现文件路径: kernel_gen/dsl/mlir_gen/emit/core.py, kernel_gen/dialect/nn.py
# 对应 spec 文件路径: spec/dialect/nn.md
# 对应测试文件路径: test/dsl/test_mlir_gen.py
def test_build_func_op_reduce_verifier_failures() -> None:
    from kernel_gen.operation.nn import reduce_sum

    source = Memory([2, 3, 4], NumericType.Float32, space=MemorySpace.GM)

    def reduce_axes_oob_kernel(src: "Tensor[f32, 2, 3, 4]") -> "Tensor[f32, 2, 3, 4]":
        return reduce_sum(src, axis=3)

    def reduce_axes_empty_kernel(src: "Tensor[f32, 2, 3, 4]") -> "Tensor[f32, 2, 3, 4]":
        return reduce_sum(src, axis=[])

    def reduce_keepdim_invalid_kernel(src: "Tensor[f32, 2, 3, 4]") -> "Tensor[f32, 2, 3, 4]":
        return reduce_sum(src, axis=1, keepdim=2)

    with pytest.raises(VerifyException, match="axes-must-be-non-empty-unique-and-in-range"):
        build_func_op(reduce_axes_oob_kernel, source)
    with pytest.raises(VerifyException, match="axes-must-be-non-empty-unique-and-in-range"):
        build_func_op(reduce_axes_empty_kernel, source)
    with pytest.raises(VerifyException, match="keepdim-must-be-i1-bool-attr"):
        build_func_op(reduce_keepdim_invalid_kernel, source)


# MGEN-C1A
# 创建者: 朽木露琪亚
# 最后一次更改: 朽木露琪亚
# 功能说明: 验证 build_func_op 支持 nn.matmul helper 并生成单结果 raw func.func。
# 测试目的: 锁定 matmul helper 已纳入 AST/emit/mlir_gen 前端集合，不再因 Unsupported call expression 失败。
# 使用示例: pytest -q test/dsl/test_mlir_gen.py -k test_build_func_op_supports_matmul_helper_call
# 对应功能实现文件路径: kernel_gen/dsl/ast.py, kernel_gen/dsl/mlir_gen.py, kernel_gen/dsl/mlir_gen/emit/core.py
# 对应 spec 文件路径: spec/dsl/ast.md, spec/dsl/mlir_gen.md, spec/dsl/emit_mlir.md
# 对应测试文件路径: test/dsl/test_mlir_gen.py
def test_build_func_op_supports_matmul_helper_call() -> None:
    from kernel_gen.operation.nn import matmul

    lhs = Memory([16, 144], NumericType.Float32, space=MemorySpace.GM)
    rhs = Memory([144, 256], NumericType.Float32, space=MemorySpace.GM)

    def matmul_kernel(
        lhs: "Tensor[f32, 16, 144]",
        rhs: "Tensor[f32, 144, 256]",
    ) -> "Tensor[f32, 16, 256]":
        return matmul(lhs, rhs)

    func_op = build_func_op(matmul_kernel, lhs, rhs)
    matmul_ops = [op for op in func_op.body.block.ops if isinstance(op, NnMatmulOp)]
    return_ops = [op for op in func_op.body.block.ops if isinstance(op, func.ReturnOp)]
    assert len(matmul_ops) == 1
    assert len(return_ops) == 1
    assert [attr.data for attr in matmul_ops[0].result.type.shape.data] == [16, 256]
    assert list(func_op.function_type.outputs) == [matmul_ops[0].result.type]
    assert return_ops[0].arguments[0].type == matmul_ops[0].result.type


# MGEN-S2A
# 创建者: 朽木露琪亚
# 最后一次更改: 朽木露琪亚
# 功能说明: 验证 tiled matmul 前端显式声明的 `MemorySpace.TSM` 会在 raw IR 中保持为 `#nn.space<tsm>`。
# 测试目的: 锁定 execute_engine_npu_demo_matmul S2 的 tile memory 空间合同，避免 `TSM` 退化为 `shared`。
# 使用示例: pytest -q test/dsl/test_mlir_gen.py -k test_build_func_op_matmul_tsm_tile_memory_keeps_tsm_in_raw_ir
# 对应功能实现文件路径: kernel_gen/dsl/emit_mlir.py, kernel_gen/dsl/mlir_gen.py
# 对应 spec 文件路径: spec/dsl/emit_mlir.md, spec/dsl/mlir_gen.md
# 对应测试文件路径: test/dsl/test_mlir_gen.py
def test_build_func_op_matmul_tsm_tile_memory_keeps_tsm_in_raw_ir(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from kernel_gen.operation.dma import alloc, deslice, slice
    from kernel_gen.operation.nn import matmul
    from kernel_gen.operation.scf import loop

    lhs = Memory([32, 16], NumericType.Float32, space=MemorySpace.GM)
    rhs = Memory([16, 32], NumericType.Float32, space=MemorySpace.GM)

    def matmul_kernel(lhs: "Tensor[f32, 32, 16]", rhs: "Tensor[f32, 16, 32]") -> "Tensor[f32, 32, 32]":
        out = alloc([32, 32], NumericType.Float32, MemorySpace.GM)
        for m0 in loop(0, 32, 16):
            for n0 in loop(0, 32, 16):
                lhs_tile = slice(lhs, [m0, 0], [16, 16], [1, 1], MemorySpace.TSM)
                rhs_tile = slice(rhs, [0, n0], [16, 16], [1, 1], MemorySpace.TSM)
                partial = matmul(lhs_tile, rhs_tile)
                deslice(partial, out, [m0, n0], [16, 16], [1, 1])
        return out

    for name, value in (
        ("alloc", alloc),
        ("deslice", deslice),
        ("slice", slice),
        ("matmul", matmul),
        ("loop", loop),
        ("NumericType", NumericType),
        ("MemorySpace", MemorySpace),
    ):
        monkeypatch.setitem(matmul_kernel.__globals__, name, value)

    func_ast = parse_function(matmul_kernel)
    for func_op in (
        build_func_op(matmul_kernel, lhs, rhs),
        build_func_op_from_ast(func_ast, runtime_args=(lhs, rhs)),
    ):
        raw_text = str(func_op)
        assert "#nn.space<tsm>" in raw_text
        assert "#nn.space<shared>" not in raw_text
        assert 'space = #nn.space<tsm>' in raw_text


# MGEN-C1C
# 创建者: 朽木露琪亚
# 最后一次更改: 朽木露琪亚
# 功能说明: 验证 conv helper 会前端分解为 nn.img2col2d + nn.matmul，而不是生成 nn.conv。
# 测试目的: 锁定 conv 进入 AST/emit/mlir_gen 公开集合，并输出 raw nn.img2col2d/nn.matmul 链路。
# 使用示例: pytest -q test/dsl/test_mlir_gen.py -k test_build_func_op_supports_conv_helper_call
# 对应功能实现文件路径: kernel_gen/dsl/ast.py, kernel_gen/dsl/mlir_gen/emit/core.py, kernel_gen/dsl/mlir_gen.py
# 对应 spec 文件路径: spec/dsl/mlir_gen.md, spec/dsl/emit_mlir.md
# 对应测试文件路径: test/dsl/test_mlir_gen.py
def test_build_func_op_supports_conv_helper_call() -> None:
    from kernel_gen.operation.nn import conv

    value = Memory([1, 3, 5, 5], NumericType.Float32, space=MemorySpace.GM)
    weight = Memory([8, 3, 3, 3], NumericType.Float32, space=MemorySpace.GM)

    def conv_kernel(
        value: "Tensor[f32, 1, 3, 5, 5]",
        weight: "Tensor[f32, 8, 3, 3, 3]",
    ) -> "Tensor[f32, 1, 8, 5, 5]":
        return conv(value, weight, sh=1, sw=1, dh=1, dw=1, ph=1, pw=1, pl=1, pr=1)

    module = _module_from_func(conv_kernel, value, weight)
    mlir_text = _print_module(module)
    func_op = next(op for op in module.ops if isinstance(op, func.FuncOp))
    return_ops = [op for op in func_op.body.block.ops if isinstance(op, func.ReturnOp)]
    assert "nn.img2col2d" in mlir_text
    assert "nn.matmul" in mlir_text
    assert "nn.conv" not in mlir_text
    assert len([op for op in func_op.body.block.ops if isinstance(op, NnImg2col2dOp)]) == 1
    assert len([op for op in func_op.body.block.ops if isinstance(op, NnMatmulOp)]) == 1
    assert len(return_ops) == 1
    assert [attr.data for attr in return_ops[0].arguments[0].type.shape.data] == [1, 8, 5, 5]


# MGEN-C1D
# 创建者: 朽木露琪亚
# 最后一次更改: 朽木露琪亚
# 功能说明: 验证 conv helper 的符号输出维度可与等价返回注解对齐。
# 测试目的: 锁定 `(H - 1)/1 + 1` 与 `H` 这类等价符号维不会被错误判定为返回注解不一致。
# 使用示例: pytest -q test/dsl/test_mlir_gen.py -k test_build_func_op_supports_symbolic_conv_helper_call
# 对应功能实现文件路径: kernel_gen/dsl/mlir_gen/emit/core.py, kernel_gen/dsl/mlir_gen.py
# 对应 spec 文件路径: spec/dsl/mlir_gen.md, spec/dsl/emit_mlir.md
# 对应测试文件路径: test/dsl/test_mlir_gen.py
def test_build_func_op_supports_symbolic_conv_helper_call() -> None:
    from kernel_gen.operation.nn import conv

    value = Memory(["B", 3, "H", "W"], NumericType.Float32, space=MemorySpace.GM)
    weight = Memory([8, 3, 3, 3], NumericType.Float32, space=MemorySpace.GM)
    expected = conv(value, weight, sh=1, sw=1, dh=1, dw=1, ph=1, pw=1, pl=1, pr=1)

    def conv_kernel(
        value: 'Tensor[f32, "B", 3, "H", "W"]',
        weight: "Tensor[f32, 8, 3, 3, 3]",
    ) -> 'Tensor[f32, "B", 8, "H", "W"]':
        return conv(value, weight, sh=1, sw=1, dh=1, dw=1, ph=1, pw=1, pl=1, pr=1)

    func_op = build_func_op(conv_kernel, value, weight)
    return_ops = [op for op in func_op.body.block.ops if isinstance(op, func.ReturnOp)]
    assert len([op for op in func_op.body.block.ops if isinstance(op, NnImg2col2dOp)]) == 1
    assert len([op for op in func_op.body.block.ops if isinstance(op, NnMatmulOp)]) == 1
    assert len(return_ops) == 1
    assert return_ops[0].arguments[0].type == _memory_to_nn_type(expected)


# MGEN-C1F
# 创建者: 金铲铲大作战
# 最后一次更改: 金铲铲大作战
# 功能说明: 验证 conv helper 支持符号 kh/kw 与符号 padding 参数。
# 测试目的: 锁定 conv 前端分解在符号 kernel/padding 路径下仍输出 nn.img2col2d + nn.matmul，并保持 helper 参数为 symbol.int operand。
# 使用示例: pytest -q test/dsl/test_mlir_gen.py -k test_build_func_op_supports_symbolic_conv_helper_kernel_and_padding
# 对应功能实现文件路径: kernel_gen/dsl/emit_mlir.py, kernel_gen/dsl/mlir_gen.py
# 对应 spec 文件路径: spec/dsl/mlir_gen.md, spec/dsl/emit_mlir.md
# 对应测试文件路径: test/dsl/test_mlir_gen.py
def test_build_func_op_supports_symbolic_conv_helper_kernel_and_padding() -> None:
    from kernel_gen.operation.nn import conv

    value = Memory([1, 3, SymbolDim("H"), SymbolDim("W")], NumericType.Float32, space=MemorySpace.GM)
    weight = Memory([8, 3, SymbolDim("KH"), SymbolDim("KW")], NumericType.Float32, space=MemorySpace.GM)
    ph_symbol = SymbolDim("PH")
    expected = conv(value, weight, sh=1, sw=1, dh=1, dw=1, ph=ph_symbol, pw=ph_symbol, pl=0, pr=0)

    def conv_kernel(
        value: "Tensor[f32, 1, 3, H, W]",
        weight: "Tensor[f32, 8, 3, KH, KW]",
        PH: int,
    ) -> "Tensor[f32, 1, 8, (H + PH + PH - 1 * (KH - 1) - 1) / 1 + 1, (W - 1 * (KW - 1) - 1) / 1 + 1]":
        return conv(value, weight, sh=1, sw=1, dh=1, dw=1, ph=PH, pw=PH, pl=0, pr=0)

    func_op = build_func_op(conv_kernel, value, weight, ph_symbol)
    img2col_ops = [op for op in func_op.body.block.ops if isinstance(op, NnImg2col2dOp)]
    matmul_ops = [op for op in func_op.body.block.ops if isinstance(op, NnMatmulOp)]
    return_ops = [op for op in func_op.body.block.ops if isinstance(op, func.ReturnOp)]
    assert len(img2col_ops) == 1
    assert len(matmul_ops) == 1
    assert len(return_ops) == 1
    assert img2col_ops[0].kh.type == SymbolValueType.from_expr("KH")
    assert img2col_ops[0].kw.type == SymbolValueType.from_expr("KW")
    assert img2col_ops[0].ph.type == SymbolValueType.from_expr("PH")
    assert img2col_ops[0].pw.type == SymbolValueType.from_expr("PH")
    assert return_ops[0].arguments[0].type == _memory_to_nn_type(expected)


# MGEN-C1E
# 创建者: 朽木露琪亚
# 最后一次更改: 朽木露琪亚
# 功能说明: 验证 conv helper 的非法 stride 参数会在顶层 facade 显式失败。
# 测试目的: 锁定 build_func_op(...) 顶层 facade 对 helper 参数范围错误的公开短语，避免非法参数静默通过。
# 使用示例: pytest -q test/dsl/test_mlir_gen.py -k test_build_func_op_conv_helper_rejects_invalid_stride
# 对应功能实现文件路径: kernel_gen/dsl/mlir_gen/emit/core.py
# 对应 spec 文件路径: spec/dsl/emit_mlir.md
# 对应测试文件路径: test/dsl/test_mlir_gen.py
def test_build_func_op_conv_helper_rejects_invalid_stride() -> None:
    from kernel_gen.operation.nn import conv

    value = Memory([1, 3, 5, 5], NumericType.Float32, space=MemorySpace.GM)
    weight = Memory([8, 3, 3, 3], NumericType.Float32, space=MemorySpace.GM)

    def conv_kernel(
        value: "Tensor[f32, 1, 3, 5, 5]",
        weight: "Tensor[f32, 8, 3, 3, 3]",
    ) -> "Tensor[f32, 1, 8, 5, 5]":
        return conv(value, weight, sh=0, sw=1, dh=1, dw=1, ph=1, pw=1, pl=1, pr=1)

    with pytest.raises(AstVisitorError, match="conv sh must be positive|output height must be positive"):
        build_func_op(conv_kernel, value, weight)


# MGEN-C1F
# 创建者: 朽木露琪亚
# 最后一次更改: 朽木露琪亚
# 功能说明: 验证 conv helper 的参数个数错误在 build_func_op 阶段显式失败。
# 测试目的: 锁定 conv arity 错误路径不会回退为 generic unsupported 或静默通过。
# 使用示例: pytest -q test/dsl/test_mlir_gen.py -k test_build_func_op_conv_helper_rejects_invalid_arity
# 对应功能实现文件路径: kernel_gen/dsl/ast.py
# 对应 spec 文件路径: spec/dsl/mlir_gen.md
# 对应测试文件路径: test/dsl/test_mlir_gen.py
def test_build_func_op_conv_helper_rejects_invalid_arity() -> None:
    from kernel_gen.operation.nn import conv

    value = Memory([1, 3, 5, 5], NumericType.Float32, space=MemorySpace.GM)

    def conv_kernel(value: "Tensor[f32, 1, 3, 5, 5]") -> "Tensor[f32, 1, 8, 5, 5]":
        return conv(value)

    with pytest.raises(AstVisitorError, match="Unsupported conv arity"):
        build_func_op(conv_kernel, value)


# MGEN-C1B
# 创建者: 朽木露琪亚
# 最后一次更改: 朽木露琪亚
# 功能说明: 验证 conv2d_img2col2d_tiled_npu_demo 前端函数可直接生成 raw func.func。
# 测试目的: 锁定 `loop + slice + img2col2d + reshape + matmul + deslice + return` 链路在 build_func_op/build_func_op_from_ast 上完整可用。
# 使用示例: pytest -q test/dsl/test_mlir_gen.py -k test_build_func_op_supports_conv2d_img2col2d_tiled_npu_demo
# 对应功能实现文件路径: kernel_gen/dsl/ast.py, kernel_gen/dsl/mlir_gen.py, kernel_gen/dsl/mlir_gen/emit/core.py
# 对应 spec 文件路径: spec/dsl/ast.md, spec/dsl/mlir_gen.md, spec/dsl/emit_mlir.md
# 对应测试文件路径: test/dsl/test_mlir_gen.py
def test_build_func_op_supports_conv2d_img2col2d_tiled_npu_demo(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from kernel_gen.operation.dma import alloc, deslice, reshape, slice
    from kernel_gen.operation.nn import img2col2d, matmul
    from kernel_gen.operation.scf import loop

    input_memory = Memory([1, 16, 18, 18], NumericType.Float32, space=MemorySpace.GM)
    weight_memory = Memory([16, 16, 3, 3], NumericType.Float32, space=MemorySpace.GM)

    def conv2d_img2col2d_tiled_npu_demo(
        input: "Tensor[f32, 1, 16, 18, 18]",
        weight: "Tensor[f32, 16, 16, 3, 3]",
    ) -> "Tensor[f32, 1, 16, 16, 16]":
        out = alloc([1, 16, 16, 16], NumericType.Float32, MemorySpace.GM)
        for n0 in loop(0, 1, 1):
            for c0 in loop(0, 16, 16):
                for f0 in loop(0, 16, 16):
                    for ho0 in loop(0, 16, 16):
                        for wo0 in loop(0, 16, 16):
                            input_tile = slice(input, [n0, c0, 0, 0], [1, 16, 18, 18], [1, 1, 1, 1], MemorySpace.GM)
                            weight_tile = slice(weight, [f0, c0, 0, 0], [16, 16, 3, 3], [1, 1, 1, 1], MemorySpace.GM)
                            col = img2col2d(input_tile, kh=3, kw=3, sh=1, sw=1, dh=1, dw=1, ph=0, pw=0, pl=0, pr=0)
                            col2 = reshape(col, [144, 256])
                            weight2 = reshape(weight_tile, [16, 144])
                            out2 = matmul(weight2, col2)
                            out_tile = reshape(out2, [1, 16, 16, 16])
                            deslice(out_tile, out, [n0, f0, ho0, wo0], [1, 16, 16, 16], [1, 1, 1, 1])
        return out

    for name, value in (
        ("alloc", alloc),
        ("deslice", deslice),
        ("reshape", reshape),
        ("slice", slice),
        ("img2col2d", img2col2d),
        ("matmul", matmul),
        ("loop", loop),
        ("NumericType", NumericType),
        ("MemorySpace", MemorySpace),
    ):
        monkeypatch.setitem(conv2d_img2col2d_tiled_npu_demo.__globals__, name, value)

    func_ast = parse_function(conv2d_img2col2d_tiled_npu_demo)
    for func_op in (
        build_func_op(conv2d_img2col2d_tiled_npu_demo, input_memory, weight_memory),
        build_func_op_from_ast(func_ast, runtime_args=(input_memory, weight_memory)),
    ):
        module = ModuleOp([func_op])
        walked_ops = list(module.walk())
        assert any(isinstance(op, (scf.ForOp, SymbolForOp)) for op in walked_ops)
        assert any(isinstance(op, DmaAllocOp) for op in walked_ops)
        assert any(isinstance(op, DmaSliceOp) for op in walked_ops)
        assert any(isinstance(op, DmaReshapeOp) for op in walked_ops)
        assert any(isinstance(op, NnImg2col2dOp) for op in walked_ops)
        assert any(isinstance(op, NnMatmulOp) for op in walked_ops)
        assert any(isinstance(op, DmaDesliceOp) for op in walked_ops)
        assert any(isinstance(op, func.ReturnOp) for op in walked_ops)


# MGEN-C2A
# 创建者: 金铲铲大作战
# 最后一次更改: 金铲铲大作战
# 最近一次运行测试时间: 2026-04-04 18:08:02 +0800
# 最近一次运行成功时间: 2026-04-04 18:08:02 +0800
# 功能说明: 黑盒验证 conv2d_img2col2d_tiled_npu_demo 通过 build_func_op 生成 raw MLIR IR。
# 测试目的: 锁定最小 conv2d 正例仅走 build_func_op，且 raw IR 中临时 tile 被后续计算与最终 deslice 真实消费。
# 使用示例: pytest -q test/dsl/test_mlir_gen.py -k test_build_func_op_conv2d_npu_demo_blackbox_raw_ir
# 对应功能实现文件路径: kernel_gen/dsl/mlir_gen.py, kernel_gen/dsl/mlir_gen/emit/core.py
# 对应 spec 文件路径: spec/dsl/mlir_gen.md, spec/dsl/emit_mlir.md
# 对应测试文件路径: test/dsl/test_mlir_gen.py
def test_build_func_op_conv2d_npu_demo_blackbox_raw_ir(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from kernel_gen.operation.dma import alloc, deslice, reshape, slice
    from kernel_gen.operation.nn import img2col2d, matmul
    from kernel_gen.operation.scf import loop

    input_memory = Memory([1, 16, 18, 18], NumericType.Float32, space=MemorySpace.GM)
    weight_memory = Memory([16, 16, 3, 3], NumericType.Float32, space=MemorySpace.GM)

    def conv2d_img2col2d_tiled_npu_demo(
        input: "Tensor[f32, 1, 16, 18, 18]",
        weight: "Tensor[f32, 16, 16, 3, 3]",
    ) -> "Tensor[f32, 1, 16, 16, 16]":
        out = alloc([1, 16, 16, 16], NumericType.Float32, MemorySpace.GM)
        for n0 in loop(0, 1, 1):
            input_tile = slice(input, [n0, 0, 0, 0], [1, 16, 18, 18], [1, 1, 1, 1], MemorySpace.GM)
            weight_tile = slice(weight, [0, 0, 0, 0], [16, 16, 3, 3], [1, 1, 1, 1], MemorySpace.GM)
            col = img2col2d(input_tile, kh=3, kw=3, sh=1, sw=1, dh=1, dw=1, ph=0, pw=0, pl=0, pr=0)
            col2 = reshape(col, [144, 256])
            weight2 = reshape(weight_tile, [16, 144])
            out2 = matmul(weight2, col2)
            out_tile = reshape(out2, [1, 16, 16, 16])
            deslice(out_tile, out, [n0, 0, 0, 0], [1, 16, 16, 16], [1, 1, 1, 1])
        return out

    for name, value in (
        ("alloc", alloc),
        ("deslice", deslice),
        ("reshape", reshape),
        ("slice", slice),
        ("img2col2d", img2col2d),
        ("matmul", matmul),
        ("loop", loop),
        ("NumericType", NumericType),
        ("MemorySpace", MemorySpace),
    ):
        monkeypatch.setitem(conv2d_img2col2d_tiled_npu_demo.__globals__, name, value)

    func_op = build_func_op(conv2d_img2col2d_tiled_npu_demo, input_memory, weight_memory)
    module = ModuleOp([func_op])
    buffer = StringIO()
    Printer(buffer).print(module)
    raw_ir = buffer.getvalue()
    for token in (
        "func.func",
        "func.return",
        "dma.alloc",
        "dma.slice",
        "dma.reshape",
        "nn.img2col2d",
        "nn.matmul",
        "dma.deslice",
    ):
        if token not in raw_ir:
            raise AssertionError(f"expected {token} in raw MLIR IR")
    if "scf.for" not in raw_ir and "symbol.for" not in raw_ir:
        raise AssertionError("expected scf.for or symbol.for in raw MLIR IR")

    walked_ops = list(module.walk())
    if not any(isinstance(op, (scf.ForOp, SymbolForOp)) for op in walked_ops):
        raise AssertionError("expected scf.for or symbol.for in module ops")
    deslice_op = next(op for op in walked_ops if isinstance(op, DmaDesliceOp))
    matmul_op = next(op for op in walked_ops if isinstance(op, NnMatmulOp))
    img2col_op = next(op for op in walked_ops if isinstance(op, NnImg2col2dOp))
    slice_targets = {op.target for op in walked_ops if isinstance(op, DmaSliceOp)}
    if img2col_op.input not in slice_targets:
        raise AssertionError("expected img2col2d input to consume slice target")
    if not isinstance(matmul_op.lhs.owner, DmaReshapeOp):
        raise AssertionError("expected matmul lhs to come from dma.reshape")
    if not isinstance(matmul_op.rhs.owner, DmaReshapeOp):
        raise AssertionError("expected matmul rhs to come from dma.reshape")
    reshape_from_matmul = next(
        (
            op
            for op in walked_ops
            if isinstance(op, DmaReshapeOp) and op.source is matmul_op.result
        ),
        None,
    )
    if reshape_from_matmul is None:
        raise AssertionError("expected matmul result to be reshaped for deslice")
    if deslice_op.source is not reshape_from_matmul.result:
        raise AssertionError("expected deslice source to consume reshape(matmul) result")
    alloc_op = next(op for op in walked_ops if isinstance(op, DmaAllocOp))
    if deslice_op.target is not alloc_op.result:
        raise AssertionError("expected deslice target to consume alloc result")


# MGEN-C2B
# 创建者: 金铲铲大作战
# 最后一次更改: 金铲铲大作战
# 最近一次运行测试时间: 2026-04-04 18:08:02 +0800
# 最近一次运行成功时间: 2026-04-04 18:08:02 +0800
# 功能说明: 黑盒验证 conv2d_npu_demo helper 缺失时 build_func_op 统一报 unsupported。
# 测试目的: 锁定缺失 img2col2d/matmul 等 helper 时不回退 pipeline，直接抛 Unsupported call expression。
# 使用示例: pytest -q test/dsl/test_mlir_gen.py -k test_build_func_op_conv2d_npu_demo_missing_helper_reports_unsupported
# 对应功能实现文件路径: kernel_gen/dsl/mlir_gen.py, kernel_gen/dsl/ast.py
# 对应 spec 文件路径: spec/dsl/mlir_gen.md, spec/dsl/ast.md
# 对应测试文件路径: test/dsl/test_mlir_gen.py
def test_build_func_op_conv2d_npu_demo_missing_helper_reports_unsupported(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from kernel_gen.operation.dma import alloc, deslice, reshape, slice

    input_memory = Memory([1, 16, 18, 18], NumericType.Float32, space=MemorySpace.GM)
    weight_memory = Memory([16, 16, 3, 3], NumericType.Float32, space=MemorySpace.GM)

    def conv2d_img2col2d_tiled_npu_demo(
        input: "Tensor[f32, 1, 16, 18, 18]",
        weight: "Tensor[f32, 16, 16, 3, 3]",
    ) -> "Tensor[f32, 1, 16, 16, 16]":
        out = alloc([1, 16, 16, 16], NumericType.Float32, MemorySpace.GM)
        input_tile = slice(input, [0, 0, 0, 0], [1, 16, 18, 18], [1, 1, 1, 1], MemorySpace.GM)
        weight_tile = slice(weight, [0, 0, 0, 0], [16, 16, 3, 3], [1, 1, 1, 1], MemorySpace.GM)
        col = img2col2d(input_tile, kh=3, kw=3, sh=1, sw=1, dh=1, dw=1, ph=0, pw=0, pl=0, pr=0)
        col2 = reshape(col, [144, 256])
        weight2 = reshape(weight_tile, [16, 144])
        out2 = matmul(weight2, col2)
        out_tile = reshape(out2, [1, 16, 16, 16])
        deslice(out_tile, out, [0, 0, 0, 0], [1, 16, 16, 16], [1, 1, 1, 1])
        return out

    for name, value in (
        ("alloc", alloc),
        ("deslice", deslice),
        ("reshape", reshape),
        ("slice", slice),
        ("NumericType", NumericType),
        ("MemorySpace", MemorySpace),
    ):
        monkeypatch.setitem(conv2d_img2col2d_tiled_npu_demo.__globals__, name, value)

    with pytest.raises(AstVisitorError, match="Unsupported call expression"):
        build_func_op(conv2d_img2col2d_tiled_npu_demo, input_memory, weight_memory)


# MGEN-C2C
# 创建者: 金铲铲大作战
# 最后一次更改: 金铲铲大作战
# 最近一次运行测试时间: 2026-04-04 18:08:02 +0800
# 最近一次运行成功时间: 2026-04-04 18:08:02 +0800
# 功能说明: 黑盒验证计划外 conv2d helper/op 会触发 build_func_op 的 unsupported 报错。
# 测试目的: 锁定计划外 img2col3d op 不进入 pipeline/lowered IR，直接收敛 Unsupported call expression。
# 使用示例: pytest -q test/dsl/test_mlir_gen.py -k test_build_func_op_conv2d_npu_demo_unplanned_op_reports_unsupported
# 对应功能实现文件路径: kernel_gen/dsl/mlir_gen.py, kernel_gen/dsl/ast.py
# 对应 spec 文件路径: spec/dsl/mlir_gen.md, spec/dsl/ast.md
# 对应测试文件路径: test/dsl/test_mlir_gen.py
def test_build_func_op_conv2d_npu_demo_unplanned_op_reports_unsupported(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from kernel_gen.operation.dma import alloc, deslice, reshape, slice
    from kernel_gen.operation.nn import matmul

    def img2col3d(*_args: object, **_kwargs: object) -> None:
        raise AssertionError("img2col3d should not be executed during parsing")

    img2col3d.__module__ = "kernel_gen.operation.nn"

    input_memory = Memory([1, 16, 18, 18], NumericType.Float32, space=MemorySpace.GM)
    weight_memory = Memory([16, 16, 3, 3], NumericType.Float32, space=MemorySpace.GM)

    def conv2d_img2col2d_tiled_npu_demo(
        input: "Tensor[f32, 1, 16, 18, 18]",
        weight: "Tensor[f32, 16, 16, 3, 3]",
    ) -> "Tensor[f32, 1, 16, 16, 16]":
        out = alloc([1, 16, 16, 16], NumericType.Float32, MemorySpace.GM)
        input_tile = slice(input, [0, 0, 0, 0], [1, 16, 18, 18], [1, 1, 1, 1], MemorySpace.GM)
        weight_tile = slice(weight, [0, 0, 0, 0], [16, 16, 3, 3], [1, 1, 1, 1], MemorySpace.GM)
        col = img2col3d(input_tile, kh=3, kw=3, sh=1, sw=1, dh=1, dw=1, ph=0, pw=0, pl=0, pr=0)
        col2 = reshape(col, [144, 256])
        weight2 = reshape(weight_tile, [16, 144])
        out2 = matmul(weight2, col2)
        out_tile = reshape(out2, [1, 16, 16, 16])
        deslice(out_tile, out, [0, 0, 0, 0], [1, 16, 16, 16], [1, 1, 1, 1])
        return out

    for name, value in (
        ("alloc", alloc),
        ("deslice", deslice),
        ("reshape", reshape),
        ("slice", slice),
        ("matmul", matmul),
        ("img2col3d", img2col3d),
        ("NumericType", NumericType),
        ("MemorySpace", MemorySpace),
    ):
        monkeypatch.setitem(conv2d_img2col2d_tiled_npu_demo.__globals__, name, value)

    with pytest.raises(AstVisitorError, match="Unsupported call expression"):
        build_func_op(conv2d_img2col2d_tiled_npu_demo, input_memory, weight_memory)


# MGEN-026A
# 创建者: 小李飞刀
# 最后一次更改: 我不是牛马
# 最近一次运行测试时间: 2026-03-25 22:17:59 +0800
# 最近一次运行成功时间: 2026-03-25 22:17:59 +0800
# 功能说明: 验证 build_func_op 支持仅依赖标量 runtime_args 的 DMA alloc-only kernel。
# 测试目的: 验证 alloc-only kernel 会将 runtime shape 参数 lowering 为 symbol.int 输入，并保持 dma.alloc 结果类型与返回注解一致。
# 使用示例: pytest -q test/dsl/test_mlir_gen.py -k test_build_func_op_supports_dma_alloc_helper_with_runtime_shape_args
# 对应功能实现文件路径: kernel_gen/dsl/mlir_gen.py
# 对应 spec 文件路径: spec/dsl/mlir_gen.md
# 对应测试文件路径: test/dsl/test_mlir_gen.py
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


# MGEN-002B
# 创建者: 小李飞刀
# 最后一次更改: 小李飞刀
# 最近一次运行测试时间: 2026-03-25 22:17:59 +0800
# 最近一次运行成功时间: 2026-03-25 22:17:59 +0800
# 功能说明: 覆盖 alloc-only runtime_args 无法映射为 !symbol.int 时的错误分支。
# 测试目的: 验证 alloc-only kernel 遇到非法 runtime_args 类型会报错并与 MGEN-002B 保持一致。
# 使用示例: pytest -q test/dsl/test_mlir_gen.py -k test_build_func_op_rejects_dma_alloc_helper_with_invalid_runtime_shape_args
# 对应功能实现文件路径: kernel_gen/dsl/mlir_gen.py
# 对应 spec 文件路径: spec/dsl/mlir_gen.md
# 对应测试文件路径: test/dsl/test_mlir_gen.py
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
# 使用示例: pytest -q test/dsl/test_mlir_gen.py -k test_build_func_op_supports_dma_alloc_helper_with_symbol_shape_args
# 对应功能实现文件路径: kernel_gen/dsl/mlir_gen.py
# 对应 spec 文件路径: spec/dsl/mlir_gen.md
# 对应测试文件路径: test/dsl/test_mlir_gen.py
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
# 使用示例: pytest -q test/dsl/test_mlir_gen.py -k test_build_func_op_supports_dma_alloc_helper_with_symbol_plus_const_shape_args
# 对应功能实现文件路径: kernel_gen/dsl/mlir_gen.py
# 对应 spec 文件路径: spec/dsl/mlir_gen.md
# 对应测试文件路径: test/dsl/test_mlir_gen.py
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
# 使用示例: pytest -q test/dsl/test_mlir_gen.py -k test_build_func_op_supports_dma_alloc_helper_without_runtime_args
# 对应功能实现文件路径: kernel_gen/dsl/mlir_gen.py
# 对应 spec 文件路径: spec/dsl/mlir_gen.md
# 对应测试文件路径: test/dsl/test_mlir_gen.py
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
# 使用示例: pytest -q test/dsl/test_mlir_gen.py -k test_build_func_op_supports_dma_alloc_helper_with_explicit_stride
# 对应功能实现文件路径: kernel_gen/dsl/mlir_gen.py
# 对应 spec 文件路径: spec/dsl/mlir_gen.md
# 对应测试文件路径: test/dsl/test_mlir_gen.py
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
# 使用示例: pytest -q test/dsl/test_mlir_gen.py -k test_build_func_op_rejects_dma_alloc_helper_with_invalid_dtype
# 对应功能实现文件路径: kernel_gen/dsl/ast.py
# 对应 spec 文件路径: spec/dsl/mlir_gen.md
# 对应测试文件路径: test/dsl/test_mlir_gen.py
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
# 使用示例: pytest -q test/dsl/test_mlir_gen.py -k test_build_func_op_rejects_dma_alloc_helper_with_invalid_space
# 对应功能实现文件路径: kernel_gen/dsl/ast.py
# 对应 spec 文件路径: spec/dsl/mlir_gen.md
# 对应测试文件路径: test/dsl/test_mlir_gen.py
def test_build_func_op_rejects_dma_alloc_helper_with_invalid_space() -> None:
    from kernel_gen.operation.dma import alloc

    def alloc_kernel(rank1: int, rank2: int) -> "Tensor[f32, 2, 3]":
        return alloc([rank1, rank2], NumericType.Float32, "shared")

    with pytest.raises(TypeError, match="alloc space must be MemorySpace"):
        build_func_op(alloc_kernel, 2, 3)


# MGEN-026E
# 创建者: 金铲铲大作战
# 最后一次更改: 金铲铲大作战
# 最近一次运行测试时间: 2026-03-26 02:03:12 +0800
# 最近一次运行成功时间: 2026-03-26 02:03:12 +0800
# 功能说明: 验证 alloc-only kernel 拒绝非连续 stride。
# 测试目的: 锁定非连续 stride 报错信息与公开语义一致。
# 使用示例: pytest -q test/dsl/test_mlir_gen.py -k test_build_func_op_rejects_dma_alloc_helper_with_non_contiguous_stride
# 对应功能实现文件路径: kernel_gen/dsl/mlir_gen.py
# 对应 spec 文件路径: spec/dsl/mlir_gen.md
# 对应测试文件路径: test/dsl/test_mlir_gen.py
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
# 使用示例: pytest -q test/dsl/test_mlir_gen.py -k test_build_func_op_supports_dma_free_statement
# 对应功能实现文件路径: kernel_gen/dsl/mlir_gen.py
# 对应 spec 文件路径: spec/dsl/mlir_gen.md
# 对应测试文件路径: test/dsl/test_mlir_gen.py
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
# 功能说明: 验证 build_func_op 遇到 free 非 memory operand 时直接透传 operation.free 的类型错误。
# 测试目的: 锁定 dma.free helper 对非 Memory 输入保持构造阶段 TypeError 口径。
# 使用示例: pytest -q test/dsl/test_mlir_gen.py -k test_build_func_op_rejects_dma_free_non_memory_operand
# 对应功能实现文件路径: kernel_gen/dsl/mlir_gen.py
# 对应 spec 文件路径: spec/dsl/mlir_gen.md
# 对应测试文件路径: test/dsl/test_mlir_gen.py
def test_build_func_op_rejects_dma_free_non_memory_operand() -> None:
    from kernel_gen.operation.dma import free

    def free_kernel():
        free(1)

    with pytest.raises(TypeError, match="value must be Memory"):
        build_func_op(free_kernel)


# MGEN-026
# 创建者: 小李飞刀
# 最后一次更改: 小李飞刀
# 最近一次运行测试时间: 2026-03-30 03:03:30 +0800
# 最近一次运行成功时间: 2026-03-30 03:03:30 +0800
# 功能说明: 验证 build_func_op 遇到非法 free 参数个数时抛出错误。
# 测试目的: 锁定 build_func_op 链路在 AST 解析阶段保持 Unsupported free arity 诊断。
# 使用示例: pytest -q test/dsl/test_mlir_gen.py -k test_build_func_op_rejects_invalid_free_arity
# 对应功能实现文件路径: kernel_gen/dsl/mlir_gen.py
# 对应 spec 文件路径: spec/dsl/mlir_gen.md
# 对应测试文件路径: test/dsl/test_mlir_gen.py
def test_build_func_op_rejects_invalid_free_arity() -> None:
    from kernel_gen.operation.dma import free

    source = Memory([4, 4], NumericType.Float32, space=MemorySpace.GM)

    def free_kernel(src: "Tensor[f32, 4, 4]"):
        free()

    with pytest.raises(AstVisitorError, match="Unsupported free arity"):
        build_func_op(free_kernel, source)


# MGEN-026
# 创建者: 朽木露琪亚
# 最后一次更改: 朽木露琪亚
# 最近一次运行测试时间: 2026-03-25 10:18:40 +0800
# 最近一次运行成功时间: 2026-03-25 10:18:40 +0800
# 功能说明: 验证 build_func_op 在 load helper 场景下生成 dma.alloc + dma.slice。
# 测试目的: 验证 load(...) 在 build_func_op 链路中对齐公开 helper 语义，返回前置 dma.alloc 结果。
# 使用示例: pytest -q test/dsl/test_mlir_gen.py -k test_build_func_op_supports_dma_load_helper
# 对应功能实现文件路径: kernel_gen/dsl/mlir_gen.py
# 对应 spec 文件路径: spec/dsl/mlir_gen.md
# 对应测试文件路径: test/dsl/test_mlir_gen.py
def test_build_func_op_supports_dma_load_helper() -> None:
    from kernel_gen.operation.dma import load

    source = Memory([4, 4], NumericType.Float32, space=MemorySpace.GM)

    def load_kernel(src: "Tensor[f32, 4, 4]") -> "Tensor[f32, 2, 2]":
        return load(src, [1, 1], [2, 2], [1, 1], MemorySpace.SM)

    func_op = build_func_op(load_kernel, source)
    alloc_ops = [op for op in func_op.body.block.ops if isinstance(op, DmaAllocOp)]
    slice_ops = [op for op in func_op.body.block.ops if isinstance(op, DmaSliceOp)]
    return_ops = [op for op in func_op.body.block.ops if isinstance(op, func.ReturnOp)]
    assert isinstance(func_op, func.FuncOp)
    assert len(alloc_ops) == 1
    assert len(slice_ops) == 1
    assert len(return_ops) == 1
    assert slice_ops[0].target is alloc_ops[0].result
    assert return_ops[0].operands[0] is alloc_ops[0].result


# MGEN-026
# 创建者: 朽木露琪亚
# 最后一次更改: 朽木露琪亚
# 最近一次运行测试时间: 2026-03-25 10:18:40 +0800
# 最近一次运行成功时间: 2026-03-25 10:18:40 +0800
# 功能说明: 验证 build_func_op 在 store helper 场景下生成 dma.store。
# 测试目的: 验证 store(...) 在 build_func_op 链路中被直接识别并 lowering 为 DmaStoreOp。
# 使用示例: pytest -q test/dsl/test_mlir_gen.py -k test_build_func_op_supports_dma_store_helper
# 对应功能实现文件路径: kernel_gen/dsl/mlir_gen.py
# 对应 spec 文件路径: spec/dsl/mlir_gen.md
# 对应测试文件路径: test/dsl/test_mlir_gen.py
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
# 使用示例: pytest -q test/dsl/test_mlir_gen.py -k test_build_func_op_supports_dma_slice_helper
# 对应功能实现文件路径: kernel_gen/dsl/mlir_gen.py
# 对应 spec 文件路径: spec/dsl/mlir_gen.md
# 对应测试文件路径: test/dsl/test_mlir_gen.py
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
# 测试目的: 锁定 dynamic symbol slice 的 `dma.alloc` 结果 shape 与 `func.return` 类型保持符号表达式，不再报 `Unknown index symbol`。
# 使用示例: pytest -q test/dsl/test_mlir_gen.py -k test_build_func_op_supports_dynamic_symbol_dma_slice_helper
# 对应功能实现文件路径: kernel_gen/dsl/mlir_gen/emit/core.py, kernel_gen/dsl/mlir_gen.py
# 对应 spec 文件路径: spec/dsl/emit_mlir.md, spec/dsl/mlir_gen.md
# 对应测试文件路径: test/dsl/test_mlir_gen.py
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
    assert list(func_op.function_type.outputs) == [alloc_ops[0].result.type]
    assert slice_ops[0].target is alloc_ops[0].result
    assert return_ops[0].operands[0] is alloc_ops[0].result


# MGEN-026
# 创建者: 朽木露琪亚
# 最后一次更改: 朽木露琪亚
# 最近一次运行测试时间: 2026-03-25 10:18:40 +0800
# 最近一次运行成功时间: 2026-03-25 10:18:40 +0800
# 功能说明: 验证 build_func_op 在 deslice helper 场景下生成 dma.deslice。
# 测试目的: 验证 deslice(...) 在 build_func_op 链路中被直接识别并 lowering 为 DmaDesliceOp。
# 使用示例: pytest -q test/dsl/test_mlir_gen.py -k test_build_func_op_supports_dma_deslice_helper
# 对应功能实现文件路径: kernel_gen/dsl/mlir_gen.py
# 对应 spec 文件路径: spec/dsl/mlir_gen.md
# 对应测试文件路径: test/dsl/test_mlir_gen.py
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


# MGEN-001B
# 创建者: 小李飞刀
# 最后一次更改: 朽木露琪亚
# 最近一次运行测试时间: 2026-03-25 16:05:00 +0800
# 最近一次运行成功时间: 2026-03-25 16:05:00 +0800
# 功能说明: 覆盖解析失败时的错误包装路径。
# 测试目的: 验证 _parse_function_with_env 将 _ParseFailure 转换为 AstParseError。
# 使用示例: pytest -q test/dsl/test_mlir_gen.py -k test_mlir_gen_parse_failure_wrapped
# 对应功能实现文件路径: kernel_gen/dsl/mlir_gen.py
# 对应 spec 文件路径: spec/dsl/mlir_gen.md
# 对应测试文件路径: test/dsl/test_mlir_gen.py
def test_mlir_gen_parse_failure_wrapped(monkeypatch: pytest.MonkeyPatch) -> None:
    def fn(x: object) -> object:
        return x

    def _broken_parse(*args: object, **kwargs: object) -> object:
        raise _ParseFailure("broken", location=SourceLocation(1, 2))

    monkeypatch.setattr(mlir_gen_module, "_parse_function_impl", _broken_parse)
    with pytest.raises(AstParseError, match="broken"):
        _parse_function_with_env(fn, globals_table={}, builtins_table={}, runtime_table={}, config=None)


# MGEN-009
# 创建者: 小李飞刀
# 最后一次更改: 小李飞刀
# 最近一次运行测试时间: 2026-03-23 10:30:00 +0800
# 最近一次运行成功时间: 2026-03-23 10:30:00 +0800
# 功能说明: 覆盖返回类型校验的错误分支。
# 测试目的: 验证多返回、非法返回注解与不匹配类型时报错。
# 使用示例: pytest -q test/dsl/test_mlir_gen.py -k test_mlir_gen_validate_return_type_errors
# 对应功能实现文件路径: kernel_gen/dsl/mlir_gen.py
# 对应 spec 文件路径: spec/dsl/mlir_gen.md
# 对应测试文件路径: test/dsl/test_mlir_gen.py
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


# MGEN-040
# 创建者: 金铲铲大作战
# 最后一次更改: 金铲铲大作战
# 功能说明: 验证 `build_func_op` 在 `float(symbol.int)` 场景下返回 `f32` 并生成 `symbol.to_float`。
# 测试目的: 锁定函数级返回装配会直接使用 `symbol.to_float` 的 `f32` 结果。
# 使用示例: pytest -q test/dsl/test_mlir_gen.py -k test_build_func_op_lowers_symbol_to_float
# 对应功能实现文件路径: kernel_gen/dsl/mlir_gen.py
# 对应 spec 文件路径: spec/dsl/mlir_gen.md
# 对应测试文件路径: test/dsl/test_mlir_gen.py
def test_build_func_op_lowers_symbol_to_float() -> None:
    def to_float_func(value: int) -> float:
        return float(value)

    for runtime_arg in (3, SymbolDim("N")):
        func_op = build_func_op(to_float_func, runtime_arg)
        expected_arg_type = (
            SymbolValueType.from_expr(str(runtime_arg.get_symbol()))
            if isinstance(runtime_arg, SymbolDim)
            else SymbolValueType.from_expr(str(runtime_arg))
        )
        if [arg.type for arg in func_op.args] != [expected_arg_type]:
            raise AssertionError("expected symbol.to_float input to stay !symbol.int")
        to_float_ops = [op for op in func_op.body.block.ops if isinstance(op, SymbolToFloatOp)]
        if len(to_float_ops) != 1:
            raise AssertionError("expected exactly one SymbolToFloatOp")
        if to_float_ops[0].result.type != f32:
            raise AssertionError("expected symbol.to_float result type to be f32")
        return_op = next(op for op in func_op.body.block.ops if isinstance(op, func.ReturnOp))
        if return_op.arguments[0].type != f32:
            raise AssertionError("expected func.return type to stay f32")
        if list(func_op.function_type.outputs) != [f32]:
            raise AssertionError("expected function output type list to stay [f32]")


# MGEN-040A
# 创建者: 金铲铲大作战
# 最后一次更改: 金铲铲大作战
# 功能说明: 验证 `build_func_op_from_ast` 在 `symbol.to_float` 场景下按 I2 合同返回 `f32`。
# 测试目的: 锁定手工构造的 `FunctionAST` 也会经由 `SymbolToFloatAST` 路径装配 `func.return f32`。
# 使用示例: pytest -q test/dsl/test_mlir_gen.py -k test_build_func_op_from_ast_lowers_symbol_to_float
# 对应功能实现文件路径: kernel_gen/dsl/mlir_gen.py
# 对应 spec 文件路径: spec/dsl/mlir_gen.md
# 对应测试文件路径: test/dsl/test_mlir_gen.py
def test_build_func_op_from_ast_lowers_symbol_to_float() -> None:
    input_arg = ScalarArgAST("n", int)
    output_arg = ScalarArgAST("ret0", float)
    func_ast = FunctionAST(
        "to_float_ast",
        [input_arg],
        [output_arg],
        BlockAST([SymbolToFloatAST(source=input_arg)]),
    )

    for runtime_arg in (3, SymbolDim("N")):
        func_op = build_func_op_from_ast(func_ast, runtime_args=[runtime_arg])
        expected_arg_type = (
            SymbolValueType.from_expr(str(runtime_arg.get_symbol()))
            if isinstance(runtime_arg, SymbolDim)
            else SymbolValueType.from_expr(str(runtime_arg))
        )
        if [arg.type for arg in func_op.args] != [expected_arg_type]:
            raise AssertionError("expected build_func_op_from_ast input to stay !symbol.int")
        to_float_ops = [op for op in func_op.body.block.ops if isinstance(op, SymbolToFloatOp)]
        if len(to_float_ops) != 1:
            raise AssertionError("expected exactly one SymbolToFloatOp from FunctionAST")
        if to_float_ops[0].result.type != f32:
            raise AssertionError("expected SymbolToFloatOp result type to be f32")
        return_op = next(op for op in func_op.body.block.ops if isinstance(op, func.ReturnOp))
        if return_op.arguments[0].type != f32:
            raise AssertionError("expected func.return type to stay f32")
        if list(func_op.function_type.outputs) != [f32]:
            raise AssertionError("expected function output type list to stay [f32]")


# MGEN-R2A
# 创建者: 朽木露琪亚
# 最后一次更改: 朽木露琪亚
# 最近一次运行测试时间: 2026-04-04 00:00:00 +0800
# 最近一次运行成功时间: 2026-04-04 00:00:00 +0800
# 功能说明: 验证无返回注解但有显式 return 时，build_func_op 会按实际 return lowering 结果装配单结果 func.func。
# 测试目的: 锁定 add_memory / gt / cast_dim / view_kernel 四类函数都不再因为 outputs=[] 而退回零结果。
# 使用示例: pytest -q test/dsl/test_mlir_gen.py -k test_build_func_op_infers_return_type_from_body_without_return_annotation
# 对应功能实现文件路径: kernel_gen/dsl/mlir_gen.py
# 对应 spec 文件路径: spec/dsl/mlir_gen.md
# 对应测试文件路径: test/dsl/test_mlir_gen.py
def test_build_func_op_infers_return_type_from_body_without_return_annotation() -> None:
    from kernel_gen.operation.dma import view

    lhs = Memory([2, 3], NumericType.Int32)
    rhs = Memory([2, 3], NumericType.Int32)
    src = Memory([4, 4], NumericType.Float32, space=MemorySpace.GM)

    def add_memory(
        lhs: "Tensor[i32, 2, 3]",
        rhs: "Tensor[i32, 2, 3]",
    ):
        out = lhs + rhs
        return out

    def gt(lhs: int, rhs: int):
        return lhs > rhs

    def cast_dim(n: int):
        return float(n)

    def view_kernel(src: "Tensor[f32, 4, 4]"):
        return view(src, [1, 1], [2, 2], [1, 1])

    add_func = build_func_op(add_memory, lhs, rhs)
    add_ops = [op for op in add_func.body.block.ops if isinstance(op, NnAddOp)]
    add_return = next(op for op in add_func.body.block.ops if isinstance(op, func.ReturnOp))
    assert len(add_ops) == 1
    assert list(add_func.function_type.outputs) == [add_ops[0].result.type]
    assert add_return.arguments[0].type == add_ops[0].result.type

    gt_func = build_func_op(gt, SymbolDim("M"), SymbolDim("N"))
    gt_return = next(op for op in gt_func.body.block.ops if isinstance(op, func.ReturnOp))
    assert len(gt_return.arguments) == 1
    assert gt_return.arguments[0].type == i1
    assert list(gt_func.function_type.outputs) == [i1]

    cast_func = build_func_op(cast_dim, SymbolDim("K"))
    cast_ops = [op for op in cast_func.body.block.ops if isinstance(op, SymbolToFloatOp)]
    cast_return = next(op for op in cast_func.body.block.ops if isinstance(op, func.ReturnOp))
    assert len(cast_ops) == 1
    assert cast_ops[0].result.type == f32
    assert cast_return.arguments[0].type == f32
    assert list(cast_func.function_type.outputs) == [f32]

    view_func = build_func_op(view_kernel, src)
    view_ops = [op for op in view_func.body.block.ops if isinstance(op, DmaViewOp)]
    view_return = next(op for op in view_func.body.block.ops if isinstance(op, func.ReturnOp))
    assert len(view_ops) == 1
    assert list(view_func.function_type.outputs) == [view_ops[0].result.type]
    assert view_return.arguments[0].type == view_ops[0].result.type


# MGEN-R2B
# 创建者: 朽木露琪亚
# 最后一次更改: 朽木露琪亚
# 最近一次运行测试时间: 2026-04-04 00:00:00 +0800
# 最近一次运行成功时间: 2026-04-04 00:00:00 +0800
# 功能说明: 验证来自 parse_function(...) 的无返回注解 AST，会通过 has_explicit_return 元信息驱动 build_func_op_from_ast 的返回装配。
# 测试目的: 锁定 build_func_op_from_ast(...) 不再把 outputs=[] 直接解释成零结果。
# 使用示例: pytest -q test/dsl/test_mlir_gen.py -k test_build_func_op_from_ast_infers_return_type_from_return_syntax_metadata
# 对应功能实现文件路径: kernel_gen/dsl/mlir_gen.py
# 对应 spec 文件路径: spec/dsl/mlir_gen.md
# 对应测试文件路径: test/dsl/test_mlir_gen.py
def test_build_func_op_from_ast_infers_return_type_from_return_syntax_metadata() -> None:
    lhs = Memory([2, 3], NumericType.Int32)
    rhs = Memory([2, 3], NumericType.Int32)

    def add_memory(
        lhs: "Tensor[i32, 2, 3]",
        rhs: "Tensor[i32, 2, 3]",
    ):
        out = lhs + rhs
        return out

    def gt(lhs: int, rhs: int):
        return lhs > rhs

    def cast_dim(n: int):
        return float(n)

    add_ast = parse_function(add_memory)
    gt_ast = parse_function(gt)
    cast_ast = parse_function(cast_dim)

    assert add_ast.outputs == []
    assert add_ast.has_explicit_return is True
    assert gt_ast.outputs == []
    assert gt_ast.has_explicit_return is True
    assert cast_ast.outputs == []
    assert cast_ast.has_explicit_return is True

    add_func = build_func_op_from_ast(add_ast, runtime_args=[lhs, rhs])
    add_ops = [op for op in add_func.body.block.ops if isinstance(op, NnAddOp)]
    add_return = next(op for op in add_func.body.block.ops if isinstance(op, func.ReturnOp))
    assert len(add_ops) == 1
    assert list(add_func.function_type.outputs) == [add_ops[0].result.type]
    assert add_return.arguments[0].type == add_ops[0].result.type

    gt_func = build_func_op_from_ast(gt_ast, runtime_args=[SymbolDim("M"), SymbolDim("N")])
    gt_return = next(op for op in gt_func.body.block.ops if isinstance(op, func.ReturnOp))
    assert list(gt_func.function_type.outputs) == [i1]
    assert gt_return.arguments[0].type == i1

    cast_func = build_func_op_from_ast(cast_ast, runtime_args=[SymbolDim("K")])
    cast_return = next(op for op in cast_func.body.block.ops if isinstance(op, func.ReturnOp))
    assert list(cast_func.function_type.outputs) == [f32]
    assert cast_return.arguments[0].type == f32


# MGEN-R2C
# 创建者: 朽木露琪亚
# 最后一次更改: 朽木露琪亚
# 最近一次运行测试时间: 2026-04-04 00:00:00 +0800
# 最近一次运行成功时间: 2026-04-04 00:00:00 +0800
# 功能说明: 验证参数注解不会覆盖 runtime_args 决定的输入/输出 IR。
# 测试目的: 锁定参数注解写成 f16 时，若 runtime_args 传入 i32 memory，func.func 与 nn.add 结果都保持 i32 memory。
# 使用示例: pytest -q test/dsl/test_mlir_gen.py -k test_build_func_op_uses_runtime_args_not_parameter_annotations_for_ir
# 对应功能实现文件路径: kernel_gen/dsl/mlir_gen.py
# 对应 spec 文件路径: spec/dsl/mlir_gen.md
# 对应测试文件路径: test/dsl/test_mlir_gen.py
def test_build_func_op_uses_runtime_args_not_parameter_annotations_for_ir() -> None:
    lhs = Memory([2, 3], NumericType.Int32)
    rhs = Memory([2, 3], NumericType.Int32)
    expected_type = _memory_to_nn_type(lhs)

    def add_memory_param_hint(
        lhs: "Tensor[f16, 2, 3]",
        rhs: "Tensor[f16, 2, 3]",
    ):
        out = lhs + rhs
        return out

    func_op = build_func_op(add_memory_param_hint, lhs, rhs)
    add_ops = [op for op in func_op.body.block.ops if isinstance(op, NnAddOp)]
    return_op = next(op for op in func_op.body.block.ops if isinstance(op, func.ReturnOp))
    assert [arg.type for arg in func_op.args] == [expected_type, expected_type]
    assert len(add_ops) == 1
    assert add_ops[0].result.type == expected_type
    assert list(func_op.function_type.outputs) == [expected_type]
    assert return_op.arguments[0].type == expected_type


# MGEN-006
# 创建者: 小李飞刀
# 最后一次更改: 小李飞刀
# 最近一次运行测试时间: 2026-03-18 10:56:41 +0800
# 最近一次运行成功时间: 2026-03-18 10:56:41 +0800
# 功能说明: 验证 ScalarArgAST 会 lowering 为 func.func 标量参数。
# 测试目的: 验证 ScalarArgAST 会 lowering 为 func.func 标量参数。
# 使用示例: pytest -q test/dsl/test_mlir_gen.py -k test_scalar_arg_lowering_in_signature
# 对应功能实现文件路径: kernel_gen/dsl/mlir_gen.py
# 对应 spec 文件路径: spec/dsl/mlir_gen.md
# 对应测试文件路径: test/dsl/test_mlir_gen.py
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
# 使用示例: pytest -q test/dsl/test_mlir_gen.py -k test_symbol_scalar_function_uses_symbol_value_type_signature
# 对应功能实现文件路径: kernel_gen/dsl/mlir_gen.py
# 对应 spec 文件路径: spec/dsl/mlir_gen.md
# 对应测试文件路径: test/dsl/test_mlir_gen.py
def test_symbol_scalar_function_uses_symbol_value_type_signature() -> None:
    expr = SymbolDim("expr")

    def only_symbol(expr: int) -> int:
        return expr

    func_op = build_func_op(only_symbol, expr, globals={"expr": expr, "__builtins__": __builtins__})
    inputs = list(func_op.function_type.inputs)
    outputs = list(func_op.function_type.outputs)
    assert inputs == [SymbolValueType.from_expr("expr")]
    assert outputs == [SymbolValueType.from_expr("expr")]


# MGEN-002B
# 创建者: OpenAI
# 最后一次更改: 金铲铲大作战
# 最近一次运行测试时间: 2026-03-28 14:05:00 +0800
# 最近一次运行成功时间: 2026-03-28 14:05:00 +0800
# 功能说明: 验证纯 symbol 标量函数 runtime_args 类型校验，拒绝 float 等非法标量。
# 测试目的: 覆盖 build_func_op 纯 symbol 标量场景下的输入类型错误分支。
# 使用示例: pytest -q test/dsl/test_mlir_gen.py -k test_build_func_op_rejects_symbol_scalar_float_runtime_args
# 对应功能实现文件路径: kernel_gen/dsl/mlir_gen.py
# 对应 spec 文件路径: spec/dsl/mlir_gen.md
# 对应测试文件路径: test/dsl/test_mlir_gen.py
def test_build_func_op_rejects_symbol_scalar_float_runtime_args() -> None:
    def only_symbol(expr: int) -> int:
        return expr

    with pytest.raises(AstVisitorError, match="Unsupported scalar argument type"):
        build_func_op(only_symbol, 1.5)


# MGEN-018 / MGEN-021 / MGEN-022 / MGEN-023 / MGEN-024
# 创建者: OpenAI
# 最后一次更改: 金铲铲大作战
# 最近一次运行测试时间: 2026-03-25 04:33:06 +0800
# 最近一次运行成功时间: 2026-03-25 04:33:06 +0800
# 功能说明: 验证纯 symbol 标量算术 lowering 为对应的 symbol dialect op。
# 测试目的: 验证纯 symbol 标量加减乘除在静态、动态与混合输入下不会退回 nn dialect 或 builtin 整数算术。
# 使用示例: pytest -q test/dsl/test_mlir_gen.py -k test_symbol_scalar_function_lowers_symbol_binary_ops
# 对应功能实现文件路径: kernel_gen/dsl/mlir_gen.py
# 对应 spec 文件路径: spec/dsl/mlir_gen.md
# 对应测试文件路径: test/dsl/test_mlir_gen.py
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


test_symbol_scalar_function_lowers_symbol_binary_ops = pytest.mark.parametrize(
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
)(test_symbol_scalar_function_lowers_symbol_binary_ops)
test_symbol_scalar_function_lowers_symbol_binary_ops = pytest.mark.parametrize(
    "style",
    ["python", "nn"],
)(test_symbol_scalar_function_lowers_symbol_binary_ops)


# MGEN-028
# 创建者: 金铲铲大作战
# 最后一次更改: 金铲铲大作战
# 最近一次运行测试时间: 2026-03-28 12:10:00 +0800
# 最近一次运行成功时间: 2026-03-28 12:10:00 +0800
# 功能说明: 验证纯 symbol 标量比较 lowering 为 symbol.eq 并返回 i1。
# 测试目的: 覆盖 const/const 与 symbol/symbol 输入，锁定 return 与赋值后 return 两类形态。
# 使用示例: pytest -q test/dsl/test_mlir_gen.py -k test_build_func_op_lowers_symbol_eq
# 对应功能实现文件路径: kernel_gen/dsl/mlir_gen.py
# 对应 spec 文件路径: spec/dsl/mlir_gen.md
# 对应测试文件路径: test/dsl/test_mlir_gen.py
def test_build_func_op_lowers_symbol_eq() -> None:
    def eq_return(a: int, b: int) -> bool:
        return a == b

    def eq_assign(a: int, b: int) -> bool:
        result = a == b
        return result

    cases = (
        (eq_return, (3, 4)),
        (eq_assign, (3, 4)),
        (eq_return, (SymbolDim("M"), SymbolDim("N"))),
        (eq_assign, (SymbolDim("M"), SymbolDim("N"))),
    )

    for fn, runtime_args in cases:
        func_op = build_func_op(fn, *runtime_args)
        eq_ops = [op for op in func_op.body.block.ops if isinstance(op, SymbolEqOp)]
        assert len(eq_ops) == 1
        assert eq_ops[0].result.type == i1
        assert list(func_op.function_type.outputs) == [i1]
        arg_types = [arg.type for arg in func_op.args]
        expected_arg_types = [
            SymbolValueType.from_expr(str(value.get_value()) if isinstance(value, SymbolDim) else str(value))
            for value in runtime_args
        ]
        assert arg_types == expected_arg_types
        assert "symbol.eq" in _print_module(ModuleOp([func_op]))


# MGEN-020
# 创建者: 朽木露琪亚
# 最后一次更改: 朽木露琪亚
# 最近一次运行测试时间: 2026-03-25 16:05:00 +0800
# 最近一次运行成功时间: 2026-03-25 16:05:00 +0800
# 功能说明: 验证 Python int 运行时实参会 lowering 为携带具体整数值的 SymbolValueType。
# 测试目的: 验证 build_func_op(add, lhs, rhs) 在整型标量链路中生成 symbol.add，且赋值后 return 场景保持公开类型与结果口径稳定。
# 使用示例: pytest -q test/dsl/test_mlir_gen.py -k test_build_func_op_add_scalar_runtime_ints_lower_to_symbol_value_type
# 对应功能实现文件路径: kernel_gen/dsl/mlir_gen.py
# 对应 spec 文件路径: spec/dsl/mlir_gen.md
# 对应测试文件路径: test/dsl/test_mlir_gen.py
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
# 使用示例: pytest -q test/dsl/test_mlir_gen.py -k test_build_func_op_lowers_symbol_ge
# 对应功能实现文件路径: kernel_gen/dsl/mlir_gen.py, kernel_gen/dsl/mlir_gen/emit/core.py
# 对应 spec 文件路径: spec/dsl/mlir_gen.md
# 对应测试文件路径: test/dsl/test_mlir_gen.py
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


def _assert_build_func_op_lowers_symbol_compare(
    op_name: str,
    op_type: type[object],
    runtime_cases: list[tuple[object, tuple[object, object]]],
) -> None:
    """断言 build_func_op 会将符号 compare family lowering 到对应 symbol op。

    创建者: 朽木露琪亚
    最后一次更改: 朽木露琪亚

    功能说明:
    - 复用同一套断言逻辑覆盖 `gt/le/lt/ne`。

    使用示例:
    - _assert_build_func_op_lowers_symbol_compare("gt", SymbolGtOp, cases)

    关联文件:
    - spec: spec/dsl/mlir_gen.md
    - test: test/dsl/test_mlir_gen.py
    - 功能实现: kernel_gen/dsl/mlir_gen.py
    """

    for fn, runtime_args in runtime_cases:
        func_op = build_func_op(fn, *runtime_args)
        compare_ops = [op for op in func_op.body.block.ops if isinstance(op, op_type)]
        assert len(compare_ops) == 1
        assert compare_ops[0].result.type == i1
        return_op = next(op for op in func_op.body.block.ops if isinstance(op, func.ReturnOp))
        assert return_op.arguments[0].type == i1
        assert list(func_op.function_type.outputs) == [i1]
        assert f"symbol.{op_name}" in _print_module(ModuleOp([func_op]))


def test_build_func_op_lowers_symbol_gt() -> None:
    def gt_return(lhs: int, rhs: int) -> bool:
        return lhs > rhs

    def gt_assign(lhs: int, rhs: int) -> bool:
        result = lhs > rhs
        return result

    _assert_build_func_op_lowers_symbol_compare(
        "gt",
        SymbolGtOp,
        [
            (gt_return, (3, 1)),
            (gt_assign, (3, 1)),
            (gt_return, (SymbolDim("M"), SymbolDim("N"))),
            (gt_assign, (SymbolDim("M"), SymbolDim("N"))),
        ],
    )


def test_build_func_op_lowers_symbol_le() -> None:
    def le_return(lhs: int, rhs: int) -> bool:
        return lhs <= rhs

    def le_assign(lhs: int, rhs: int) -> bool:
        result = lhs <= rhs
        return result

    _assert_build_func_op_lowers_symbol_compare(
        "le",
        SymbolLeOp,
        [
            (le_return, (3, 1)),
            (le_assign, (3, 1)),
            (le_return, (SymbolDim("M"), SymbolDim("N"))),
            (le_assign, (SymbolDim("M"), SymbolDim("N"))),
        ],
    )


def test_build_func_op_lowers_symbol_lt() -> None:
    def lt_return(lhs: int, rhs: int) -> bool:
        return lhs < rhs

    def lt_assign(lhs: int, rhs: int) -> bool:
        result = lhs < rhs
        return result

    _assert_build_func_op_lowers_symbol_compare(
        "lt",
        SymbolLtOp,
        [
            (lt_return, (3, 1)),
            (lt_assign, (3, 1)),
            (lt_return, (SymbolDim("M"), SymbolDim("N"))),
            (lt_assign, (SymbolDim("M"), SymbolDim("N"))),
        ],
    )


def test_build_func_op_lowers_symbol_ne() -> None:
    def ne_return(lhs: int, rhs: int) -> bool:
        return lhs != rhs

    def ne_assign(lhs: int, rhs: int) -> bool:
        result = lhs != rhs
        return result

    _assert_build_func_op_lowers_symbol_compare(
        "ne",
        SymbolNeOp,
        [
            (ne_return, (3, 1)),
            (ne_assign, (3, 1)),
            (ne_return, (SymbolDim("M"), SymbolDim("N"))),
            (ne_assign, (SymbolDim("M"), SymbolDim("N"))),
        ],
    )


# MGEN-019
# 创建者: 金铲铲大作战
# 最后一次更改: 金铲铲大作战
# 最近一次运行测试时间: 2026-03-23 00:20:00 +0800
# 最近一次运行成功时间: 2026-03-23 00:20:00 +0800
# 功能说明: 验证 build_func_op 省略运行时实参会直接报错。
# 测试目的: 验证 build_func_op(fn) 不再允许省略函数实际输入参数。
# 使用示例: pytest -q test/dsl/test_mlir_gen.py -k test_build_func_op_requires_explicit_runtime_args
# 对应功能实现文件路径: kernel_gen/dsl/mlir_gen.py
# 对应 spec 文件路径: spec/dsl/mlir_gen.md
# 对应测试文件路径: test/dsl/test_mlir_gen.py
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
# 使用示例: pytest -q test/dsl/test_mlir_gen.py -k test_build_func_op_rejects_runtime_arg_count_mismatch
# 对应功能实现文件路径: kernel_gen/dsl/mlir_gen.py
# 对应 spec 文件路径: spec/dsl/mlir_gen.md
# 对应测试文件路径: test/dsl/test_mlir_gen.py
def test_build_func_op_rejects_runtime_arg_count_mismatch() -> None:
    def add(x: "Tensor[f32, 2, 2]", y: "Tensor[f32, 2, 2]") -> "Tensor[f32, 2, 2]":
        return x + y

    with pytest.raises(AstVisitorError, match="expected 2, got 1"):
        build_func_op(add, _tensor_arg([2, 2]))


# MGEN-019
# 创建者: 金铲铲大作战
# 最后一次更改: 金铲铲大作战
# 最近一次运行测试时间: 2026-03-23 00:20:00 +0800
# 最近一次运行成功时间: 2026-03-23 00:20:00 +0800
# 功能说明: 验证 globals/builtins 只参与解析，不能代替 runtime_args。
# 测试目的: 验证即使 globals/builtins 完整，也必须显式传入函数实际输入参数。
# 使用示例: pytest -q test/dsl/test_mlir_gen.py -k test_build_func_op_globals_and_builtins_cannot_replace_runtime_args
# 对应功能实现文件路径: kernel_gen/dsl/mlir_gen.py
# 对应 spec 文件路径: spec/dsl/mlir_gen.md
# 对应测试文件路径: test/dsl/test_mlir_gen.py
def test_build_func_op_globals_and_builtins_cannot_replace_runtime_args() -> None:
    expr = SymbolDim("expr")

    def only_symbol(expr: int) -> int:
        return expr

    with pytest.raises(AstVisitorError, match="globals/builtins cannot replace function runtime args") as exc_info:
        build_func_op(only_symbol, globals={"expr": expr}, builtins=__builtins__)

    assert exc_info.value.location is None


# MGEN-027A
# 创建者: 我不是牛马
# 最后一次更改: 我不是牛马
# 最近一次运行测试时间: 2026-03-25 22:18:52 +0800
# 最近一次运行成功时间: 2026-03-25 22:18:52 +0800
# 功能说明: 验证 build_func_op 会拒绝闭包外部值引用。
# 测试目的: 验证闭包捕获值不会被当作局部常量或隐式输入参与 lowering。
# 使用示例: pytest -q test/dsl/test_mlir_gen.py -k test_build_func_op_rejects_external_value_reference_inside_function_body
# 对应功能实现文件路径: kernel_gen/dsl/ast.py, kernel_gen/dsl/mlir_gen.py
# 对应 spec 文件路径: spec/dsl/mlir_gen.md
# 对应测试文件路径: test/dsl/test_mlir_gen.py
def test_build_func_op_rejects_external_value_reference_inside_function_body() -> None:
    outer_value = 7

    def use_outer_value() -> int:
        return outer_value

    with pytest.raises(AstVisitorError, match="cannot use external value inside function body") as exc_info:
        build_func_op(use_outer_value)

    assert exc_info.value.location is not None
    assert exc_info.value.location.line == 2


# MGEN-027A
# 创建者: 我不是牛马
# 最后一次更改: 我不是牛马
# 最近一次运行测试时间: 2026-03-25 22:18:52 +0800
# 最近一次运行成功时间: 2026-03-25 22:18:52 +0800
# 功能说明: 验证 build_func_op 会拒绝函数体中直接引用全局外部值。
# 测试目的: 验证全局名称不会被当作局部常量或隐式输入参与 lowering。
# 使用示例: pytest -q test/dsl/test_mlir_gen.py -k test_build_func_op_rejects_global_external_value_reference
# 对应功能实现文件路径: kernel_gen/dsl/ast.py, kernel_gen/dsl/mlir_gen.py
# 对应 spec 文件路径: spec/dsl/mlir_gen.md
# 对应测试文件路径: test/dsl/test_mlir_gen.py
def test_build_func_op_rejects_global_external_value_reference(monkeypatch: pytest.MonkeyPatch) -> None:
    def use_global_value() -> int:
        return GLOBAL_EXTERNAL_VALUE

    monkeypatch.setitem(use_global_value.__globals__, "GLOBAL_EXTERNAL_VALUE", 11)

    with pytest.raises(AstVisitorError, match="cannot use external value inside function body") as exc_info:
        build_func_op(use_global_value)

    assert exc_info.value.location is not None


# MGEN-027A
# 创建者: 我不是牛马
# 最后一次更改: 我不是牛马
# 最近一次运行测试时间: 2026-03-25 22:18:52 +0800
# 最近一次运行成功时间: 2026-03-25 22:18:52 +0800
# 功能说明: 验证 build_func_op 会拒绝函数体中直接引用 builtins 外部值。
# 测试目的: 验证 builtins 补充表中的外部值不会被当作局部常量或隐式输入参与 lowering。
# 使用示例: pytest -q test/dsl/test_mlir_gen.py -k test_build_func_op_rejects_builtins_external_value_reference
# 对应功能实现文件路径: kernel_gen/dsl/ast.py, kernel_gen/dsl/mlir_gen.py
# 对应 spec 文件路径: spec/dsl/mlir_gen.md
# 对应测试文件路径: test/dsl/test_mlir_gen.py
def test_build_func_op_rejects_builtins_external_value_reference() -> None:
    def use_builtin_value() -> int:
        return BUILTIN_EXTERNAL_VALUE

    with pytest.raises(AstVisitorError, match="cannot use external value inside function body") as exc_info:
        build_func_op(use_builtin_value, builtins={"BUILTIN_EXTERNAL_VALUE": 13})

    assert exc_info.value.location is not None


# MGEN-027A
# 创建者: 我不是牛马
# 最后一次更改: 我不是牛马
# 最近一次运行测试时间: 2026-03-25 22:18:52 +0800
# 最近一次运行成功时间: 2026-03-25 22:18:52 +0800
# 功能说明: 验证 build_func_op 会拒绝 Attribute 形式的外部值引用。
# 测试目的: 验证 `module.CONST` 这类外部属性值不会被当作局部常量或隐式输入参与 lowering。
# 使用示例: pytest -q test/dsl/test_mlir_gen.py -k test_build_func_op_rejects_attribute_external_value_reference
# 对应功能实现文件路径: kernel_gen/dsl/ast.py, kernel_gen/dsl/mlir_gen.py
# 对应 spec 文件路径: spec/dsl/mlir_gen.md
# 对应测试文件路径: test/dsl/test_mlir_gen.py
def test_build_func_op_rejects_attribute_external_value_reference() -> None:
    class ExternalModule:
        CONST = 17

    def use_attribute_value() -> int:
        return ExternalModule.CONST

    with pytest.raises(AstVisitorError, match="cannot use external value inside function body") as exc_info:
        build_func_op(use_attribute_value)

    assert exc_info.value.location is not None


# MGEN-007
# 创建者: 小李飞刀
# 最后一次更改: 小李飞刀
# 最近一次运行测试时间: 2026-03-18 10:56:41 +0800
# 最近一次运行成功时间: 2026-03-18 10:56:41 +0800
# 功能说明: 验证非法 Tensor 返回注解会抛出带诊断的错误。
# 测试目的: 验证非法 Tensor 返回注解会抛出带诊断的错误。
# 使用示例: pytest -q test/dsl/test_mlir_gen.py -k test_invalid_tensor_return_annotation_reports_diagnostics
# 对应功能实现文件路径: kernel_gen/dsl/mlir_gen.py
# 对应 spec 文件路径: spec/dsl/mlir_gen.md
# 对应测试文件路径: test/dsl/test_mlir_gen.py
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
# 使用示例: pytest -q test/dsl/test_mlir_gen.py -k test_mixed_dtype_return_annotation_requires_operand_element_type
# 对应功能实现文件路径: kernel_gen/dsl/mlir_gen.py
# 对应 spec 文件路径: spec/dsl/mlir_gen.md
# 对应测试文件路径: test/dsl/test_mlir_gen.py
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
# 使用示例: pytest -q test/dsl/test_mlir_gen.py -k test_constant_lowering_reports_diagnostics
# 对应功能实现文件路径: kernel_gen/dsl/mlir_gen.py
# 对应 spec 文件路径: spec/dsl/mlir_gen.md
# 对应测试文件路径: test/dsl/test_mlir_gen.py
def test_constant_lowering_reports_diagnostics() -> None:
    def bad(x: "Tensor[f32, 2, 2]") -> "Tensor[f32, 2, 2]":
        return 1

    with pytest.raises(AstVisitorError) as exc_info:
        build_func_op(bad, _tensor_arg([2, 2]))
    assert exc_info.value.location is not None


# MGEN-009
# 创建者: 小李飞刀
# 最后一次更改: 小李飞刀
# 最近一次运行测试时间: 2026-03-18 10:56:41 +0800
# 最近一次运行成功时间: 2026-03-18 10:56:41 +0800
# 功能说明: 验证返回类型不匹配会抛出带诊断的错误。
# 测试目的: 验证返回类型不匹配会抛出带诊断的错误。
# 使用示例: pytest -q test/dsl/test_mlir_gen.py -k test_return_type_mismatch_reports_diagnostics
# 对应功能实现文件路径: kernel_gen/dsl/mlir_gen.py
# 对应 spec 文件路径: spec/dsl/mlir_gen.md
# 对应测试文件路径: test/dsl/test_mlir_gen.py
def test_return_type_mismatch_reports_diagnostics() -> None:
    def bad(x: "Tensor[f32, 2, 2]", y: "Tensor[f32, 2, 2]") -> "Tensor[f32, 2, 2]":
        return x == y

    with pytest.raises(AstVisitorError) as exc_info:
        build_func_op(bad, _tensor_arg([2, 2]), _tensor_arg([2, 2]))
    assert exc_info.value.location is not None


# MGEN-010
# 创建者: 小李飞刀
# 最后一次更改: 小李飞刀
# 最近一次运行测试时间: 2026-03-18 10:56:41 +0800
# 最近一次运行成功时间: 2026-03-18 10:56:41 +0800
# 功能说明: 验证多语句 SSA 顺序与 value 复用。
# 测试目的: 验证多语句 SSA 顺序与 value 复用。
# 使用示例: pytest -q test/dsl/test_mlir_gen.py -k test_multi_statement_ssa_order_and_reuse
# 对应功能实现文件路径: kernel_gen/dsl/mlir_gen.py
# 对应 spec 文件路径: spec/dsl/mlir_gen.md
# 对应测试文件路径: test/dsl/test_mlir_gen.py
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


# MGEN-015
# 创建者: OpenAI
# 最后一次更改: 朽木露琪亚
# 最近一次运行测试时间: 2026-03-25 16:05:00 +0800
# 最近一次运行成功时间: 2026-03-25 16:05:00 +0800
# 功能说明: 验证 LoopRange + slice/deslice + 无 return 场景可生成 symbol.for + dma.slice/dma.deslice。
# 测试目的: 验证 LoopRange + slice/deslice + 无 return 场景会直接传递 symbol.int 循环变量，不生成 arith.index_cast。
# 使用示例: pytest -q test/dsl/test_mlir_gen.py -k test_build_func_op_supports_symbolic_for_loop_dma_without_return
# 对应功能实现文件路径: kernel_gen/dsl/mlir_gen.py
# 对应 spec 文件路径: spec/dsl/mlir_gen.md
# 对应测试文件路径: test/dsl/test_mlir_gen.py
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
    assert isinstance(loop_body.args[0].type, SymbolIterType)
    offsets = list(slice_ops[0].offsets)
    sizes = list(slice_ops[0].sizes)
    assert offsets[0] is loop_body.args[0]
    assert sizes[0] is func_op.body.block.args[5]
    assert list(deslice_ops[0].offsets)[0] is loop_body.args[0]


# MGEN-011 / MGEN-022A
# 创建者: 金铲铲大作战
# 最后一次更改: 小李飞刀
# 最近一次运行测试时间: 2026-04-06 22:22:19 +0800
# 最近一次运行成功时间: 2026-04-06 22:22:19 +0800
# 功能说明: 验证 singleton dim 隐式 broadcast lowering 为 nn.broadcast + nn.add。
# 测试目的: 验证 singleton dim 隐式 broadcast lowering 为 nn.broadcast + nn.add。
# 使用示例: pytest -q test/dsl/test_mlir_gen.py -k test_tensor_binary_implicit_broadcast_lowering
# 对应功能实现文件路径: kernel_gen/dsl/mlir_gen.py
# 对应 spec 文件路径: spec/dsl/mlir_gen.md
# 对应测试文件路径: test/dsl/test_mlir_gen.py
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


# MGEN-012 / MGEN-022A
# 创建者: 金铲铲大作战
# 最后一次更改: 小李飞刀
# 最近一次运行测试时间: 2026-03-19 03:24:32 +0800
# 最近一次运行成功时间: 2026-03-19 03:24:32 +0800
# 功能说明: 验证前置维隐式 broadcast lowering 为 nn.broadcast + nn.add。
# 测试目的: 验证前置维隐式 broadcast lowering 为 nn.broadcast + nn.add。
# 使用示例: pytest -q test/dsl/test_mlir_gen.py -k test_tensor_binary_prepend_broadcast_lowering
# 对应功能实现文件路径: kernel_gen/dsl/mlir_gen.py
# 对应 spec 文件路径: spec/dsl/mlir_gen.md
# 对应测试文件路径: test/dsl/test_mlir_gen.py
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


# MGEN-011A / EMIT-029
# 创建者: 小李飞刀
# 最后一次更改: 小李飞刀
# 最近一次运行测试时间: 2026-03-27 04:14:28 +0800
# 最近一次运行成功时间: 2026-03-27 04:14:28 +0800
# 功能说明: 验证 nn.truediv 在 dtype 不一致时插入 dma.cast 并使用固定优先级决议 dtype。
# 测试目的: 保证 truediv lowering 结果包含 dma.cast + nn.truediv 且输出类型一致。
# 使用示例: pytest -q test/dsl/test_mlir_gen.py -k test_tensor_truediv_dtype_promotion_lowering
# 对应功能实现文件路径: kernel_gen/dsl/mlir_gen/emit/core.py, kernel_gen/dsl/mlir_gen.py
# 对应 spec 文件路径: spec/dsl/emit_mlir.md, spec/dsl/mlir_gen.md
# 对应测试文件路径: test/dsl/test_mlir_gen.py
def test_tensor_truediv_dtype_promotion_lowering() -> None:
    def truediv(
        x: "Tensor[f32, 2, 2]",
        y: "Tensor[i32, 2, 2]",
    ) -> "Tensor[f32, 2, 2]":
        return x / y

    lhs_memory = Memory([2, 2], NumericType.Float32)
    rhs_memory = Memory([2, 2], NumericType.Int32)
    func_op = build_func_op(truediv, lhs_memory, rhs_memory)
    cast_ops = [op for op in func_op.body.block.ops if isinstance(op, NnCastOp)]
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
# 使用示例: pytest -q test/dsl/test_mlir_gen.py -k test_compare_implicit_broadcast_lowering
# 对应功能实现文件路径: kernel_gen/dsl/mlir_gen.py
# 对应 spec 文件路径: spec/dsl/mlir_gen.md
# 对应测试文件路径: test/dsl/test_mlir_gen.py
def test_compare_implicit_broadcast_lowering() -> None:
    lhs_memory = Memory([1, "N"], NumericType.Float32)
    rhs_memory = Memory(["M", "N"], NumericType.Float32)
    lhs = TensorAST(name="x", memory=lhs_memory, location=None)
    rhs = TensorAST(name="y", memory=rhs_memory, location=None)
    expr = CompareExprAST(op="eq", lhs=lhs, rhs=rhs, location=None)
    func_ast = FunctionAST(
        name="eq",
        inputs=[lhs, rhs],
        outputs=[],
        body=BlockAST([expr]),
        has_explicit_return=True,
    )
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
# 使用示例: pytest -q test/dsl/test_mlir_gen.py -k test_build_func_op_lowers_nn_ne_with_tensor_i1_return_annotation
# 对应功能实现文件路径: kernel_gen/dsl/ast.py, kernel_gen/dsl/mlir_gen/emit/core.py, kernel_gen/dsl/mlir_gen.py
# 对应 spec 文件路径: spec/dsl/ast.md, spec/dsl/emit_mlir.md, spec/dsl/mlir_gen.md
# 对应测试文件路径: test/dsl/test_mlir_gen.py
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


# MGEN-014 / MGEN-022B
# 创建者: 金铲铲大作战
# 最后一次更改: 小李飞刀
# 最近一次运行测试时间: 2026-03-19 03:24:32 +0800
# 最近一次运行成功时间: 2026-03-19 03:24:32 +0800
# 功能说明: 验证不可广播的逐元素表达式抛 LoweringError 且保留位置。
# 测试目的: 验证不可广播的逐元素表达式抛 LoweringError 且保留位置。
# 使用示例: pytest -q test/dsl/test_mlir_gen.py -k test_tensor_binary_implicit_broadcast_mismatch_reports_diagnostics
# 对应功能实现文件路径: kernel_gen/dsl/mlir_gen.py
# 对应 spec 文件路径: spec/dsl/mlir_gen.md
# 对应测试文件路径: test/dsl/test_mlir_gen.py
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
# 功能说明: 验证 nn.sub dtype promotion 会插入 nn.cast 并返回目标 dtype 的 nn.sub。
# 测试目的: 锁定 build_func_op 对 nn.sub 混合 dtype 的 cast lowering 与返回类型。
# 使用示例: pytest -q test/dsl/test_mlir_gen.py -k test_build_func_op_lowers_nn_sub_dtype_promotion_with_cast
# 对应功能实现文件路径: kernel_gen/dsl/mlir_gen.py, kernel_gen/dsl/mlir_gen/emit/core.py
# 对应 spec 文件路径: spec/dsl/mlir_gen.md, spec/dsl/emit_mlir.md
# 对应测试文件路径: test/dsl/test_mlir_gen.py
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
    cast_ops = [op for op in func_op.body.block.ops if isinstance(op, NnCastOp)]
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
# 功能说明: 验证 build_func_op 支持 nn.add 的 memory+symbol lowering。
# 测试目的: 锁定 MLIR 组装链路对 tensor + symbol.int 的 promotion 与标量 cast 发射，不额外生成 dma.cast。
# 使用示例: pytest -q test/dsl/test_mlir_gen.py -k test_build_func_op_lowers_nn_add_memory_symbol_with_scalar_promotion
# 对应功能实现文件路径: kernel_gen/dsl/mlir_gen.py, kernel_gen/dsl/mlir_gen/emit/core.py
# 对应 spec 文件路径: spec/dsl/emit_mlir.md
# 对应测试文件路径: test/dsl/test_mlir_gen.py
def test_build_func_op_lowers_nn_add_memory_symbol_with_scalar_promotion() -> None:
    def add(lhs: "Tensor[f16, 2, 2]", bias: int) -> "Tensor[f16, 2, 2]":
        return lhs + bias

    lhs_memory = Memory([2, 2], NumericType.Float16)
    expected_type = _memory_to_nn_type(lhs_memory)

    func_op = build_func_op(add, lhs_memory, SymbolDim("K"))
    add_ops = [op for op in func_op.body.block.ops if isinstance(op, NnAddOp)]
    dma_cast_ops = [op for op in func_op.body.block.ops if isinstance(op, DmaCastOp)]
    scalar_cast_ops = [op for op in func_op.body.block.ops if isinstance(op, SymbolToFloatOp)]
    return_ops = [op for op in func_op.body.block.ops if isinstance(op, func.ReturnOp)]

    assert list(func_op.function_type.inputs) == [expected_type, SymbolValueType.from_expr("K")]
    assert len(add_ops) == 1
    assert len(dma_cast_ops) == 0
    assert len(scalar_cast_ops) == 1
    assert len(return_ops) == 1
    assert add_ops[0].rhs is scalar_cast_ops[0].result
    assert add_ops[0].result.type == expected_type
    assert return_ops[0].arguments[0].type == expected_type

# MGEN-001B
# 创建者: 小李飞刀
# 最后一次更改: 朽木露琪亚
# 最近一次运行测试时间: 2026-03-25 17:10:00 +0800
# 最近一次运行成功时间: 2026-03-25 17:10:00 +0800
# 功能说明: 覆盖 build_func_op 对 builtins 与解析失败的处理。
# 测试目的: 验证非 dict builtins 作为解析环境补充可成功运行，且解析失败会收敛为 AstVisitorError。
# 使用示例: pytest -q test/dsl/test_mlir_gen.py -k test_mlir_gen_build_func_op_builtins_and_parse_error
# 对应功能实现文件路径: kernel_gen/dsl/mlir_gen.py
# 对应 spec 文件路径: spec/dsl/mlir_gen.md
# 对应测试文件路径: test/dsl/test_mlir_gen.py
def test_mlir_gen_build_func_op_builtins_and_parse_error() -> None:
    def add(x: "Tensor[f32, 2, 2]", y: "Tensor[f32, 2, 2]") -> "Tensor[f32, 2, 2]":
        return x + y

    func_op = build_func_op(add, _tensor_arg([2, 2]), _tensor_arg([2, 2]), builtins=object())
    assert isinstance(func_op, func.FuncOp)

    def bad(x: "Tensor[f32]") -> "Tensor[f32]":
        return x

    with pytest.raises(AstVisitorError, match="Tensor annotation missing dimensions"):
        build_func_op(bad, _tensor_arg([2]))


# MGEN-042
# 创建者: 小李飞刀
# 最后一次更改: 小李飞刀
# 最近一次运行测试时间: 2026-04-06 08:10:00 +0800
# 最近一次运行成功时间: 2026-04-06 08:10:00 +0800
# 功能说明: 验证 `barrier(visibility, scope)` 可沿 build_func_op / build_func_op_from_ast lowering 为 `arch.barrier`。
# 测试目的: 锁定 barrier 在 DSL 链路中保持 `scope=#arch.scope<block>` 与 `[tsm, tlm]` visibility 顺序，并作为零返回语句 helper 发射。
# 使用示例: pytest -q test/dsl/test_mlir_gen.py -k test_build_func_op_lowers_arch_barrier
# 对应功能实现文件路径: kernel_gen/dsl/ast.py, kernel_gen/dsl/mlir_gen/emit/core.py, kernel_gen/dsl/mlir_gen.py
# 对应 spec 文件路径: spec/dsl/ast.md, spec/dsl/emit_mlir.md, spec/dsl/mlir_gen.md
# 对应测试文件路径: test/dsl/test_mlir_gen.py
def test_build_func_op_lowers_arch_barrier(monkeypatch: pytest.MonkeyPatch) -> None:
    from kernel_gen.operation.arch import BarrierScope, BarrierVisibility, barrier

    def barrier_kernel() -> None:
        barrier(visibility=[BarrierVisibility.TSM, BarrierVisibility.TLM], scope=BarrierScope.THREAD)

    monkeypatch.setitem(barrier_kernel.__globals__, "barrier", barrier)
    monkeypatch.setitem(barrier_kernel.__globals__, "BarrierVisibility", BarrierVisibility)
    monkeypatch.setitem(barrier_kernel.__globals__, "BarrierScope", BarrierScope)

    func_ast = parse_function(barrier_kernel)
    if not isinstance(func_ast.body.statements[0], ArchBarrierAST):
        raise AssertionError("expected barrier kernel to parse into ArchBarrierAST")

    for func_op in (build_func_op(barrier_kernel), build_func_op_from_ast(func_ast)):
        body_ops = list(func_op.body.block.ops)
        barrier_ops = [op for op in body_ops if isinstance(op, ArchBarrierOp)]
        return_ops = [op for op in body_ops if isinstance(op, func.ReturnOp)]
        if len(barrier_ops) != 1:
            raise AssertionError("expected exactly one arch.barrier op")
        if barrier_ops[0].scope != ArchScopeAttr.from_name("thread"):
            raise AssertionError("expected barrier scope to lower as #arch.scope<thread>")
        if list(barrier_ops[0].visibility.data) != [
            ArchVisibilityAttr.from_name("tsm"),
            ArchVisibilityAttr.from_name("tlm"),
        ]:
            raise AssertionError("expected barrier visibility to lower as [#arch.visibility<tsm>, #arch.visibility<tlm>]")
        if len(return_ops) != 1 or len(return_ops[0].arguments) != 0:
            raise AssertionError("expected barrier kernel to end with empty func.return")
        printed = _print_module(ModuleOp([func_op]))
        if "arch.barrier {scope = #arch.scope<thread>, visibility = [#arch.visibility<tsm>, #arch.visibility<tlm>]}" not in printed:
            raise AssertionError("expected printed MLIR to contain arch.barrier custom syntax")


# MGEN-043
# 创建者: 小李飞刀
# 最后一次更改: 小李飞刀
# 最近一次运行测试时间: 2026-04-06 08:10:00 +0800
# 最近一次运行成功时间: 2026-04-06 08:10:00 +0800
# 功能说明: 验证 `launch_kernel(callee, block, thread, subthread, *args)` 可沿 DSL 链路 lowering 为 `arch.launch<...>(@callee, args...)`。
# 测试目的: 锁定 callee 以 symbol ref 进入 IR，尾部 args 保持透传，且 launched body 内 `get_thread_num()` 仍返回 `!symbol.int<\"thread_num\">`。
# 使用示例: pytest -q test/dsl/test_mlir_gen.py -k test_build_func_op_lowers_arch_launch_with_callee
# 对应功能实现文件路径: kernel_gen/dsl/ast.py, kernel_gen/dsl/mlir_gen/emit/core.py, kernel_gen/dsl/mlir_gen.py
# 对应 spec 文件路径: spec/dsl/ast.md, spec/dsl/emit_mlir.md, spec/dsl/mlir_gen.md
# 对应测试文件路径: test/dsl/test_mlir_gen.py
def test_build_func_op_lowers_arch_launch_with_callee(monkeypatch: pytest.MonkeyPatch) -> None:
    from kernel_gen.operation.arch import BarrierScope, BarrierVisibility, barrier, get_thread_num, launch_kernel

    tensor_args = [_tensor_arg([2, 2]), _tensor_arg([2, 2]), _tensor_arg([2, 2])]

    def add_barrier_body(
        lhs: "Tensor[f32, 2, 2]",
        rhs: "Tensor[f32, 2, 2]",
        out: "Tensor[f32, 2, 2]",
    ) -> int:
        barrier(visibility=[BarrierVisibility.TSM, BarrierVisibility.TLM], scope=BarrierScope.BLOCK)
        return get_thread_num()

    def launch_entry(
        lhs: "Tensor[f32, 2, 2]",
        rhs: "Tensor[f32, 2, 2]",
        out: "Tensor[f32, 2, 2]",
    ) -> None:
        launch_kernel(add_barrier_body, 1, 4, 1, lhs, rhs, out)

    for fn in (add_barrier_body, launch_entry):
        monkeypatch.setitem(fn.__globals__, "BarrierVisibility", BarrierVisibility)
        monkeypatch.setitem(fn.__globals__, "BarrierScope", BarrierScope)
        monkeypatch.setitem(fn.__globals__, "barrier", barrier)
        monkeypatch.setitem(fn.__globals__, "get_thread_num", get_thread_num)
        monkeypatch.setitem(fn.__globals__, "launch_kernel", launch_kernel)
        monkeypatch.setitem(fn.__globals__, "add_barrier_body", add_barrier_body)

    launcher_ast = parse_function(launch_entry)
    if not isinstance(launcher_ast.body.statements[0], ArchLaunchKernelAST):
        raise AssertionError("expected launch entry to parse into ArchLaunchKernelAST")

    for func_op in (
        build_func_op(launch_entry, *tensor_args),
        build_func_op_from_ast(launcher_ast, runtime_args=tensor_args),
    ):
        body_ops = list(func_op.body.block.ops)
        launch_ops = [op for op in body_ops if isinstance(op, ArchLaunchKernelOp)]
        return_ops = [op for op in body_ops if isinstance(op, func.ReturnOp)]
        if len(launch_ops) != 1:
            raise AssertionError("expected exactly one arch.launch op")
        launch_op = launch_ops[0]
        if launch_op.callee != SymbolRefAttr("add_barrier_body"):
            raise AssertionError("expected launch callee to lower as flat @add_barrier_body symbol ref")
        if len(tuple(launch_op.args)) != 3:
            raise AssertionError("expected launch op to forward three kernel args")
        if launch_op.block.type != SymbolValueType.from_expr("1"):
            raise AssertionError('expected block extent to lower as !symbol.int<"1">')
        if launch_op.thread.type != SymbolValueType.from_expr("4"):
            raise AssertionError('expected thread extent to lower as !symbol.int<"4">')
        if launch_op.subthread.type != SymbolValueType.from_expr("1"):
            raise AssertionError('expected subthread extent to lower as !symbol.int<"1">')
        if len(return_ops) != 1 or len(return_ops[0].arguments) != 0:
            raise AssertionError("expected launch entry to end with empty func.return")
        printed = _print_module(ModuleOp([func_op]))
        if "arch.launch<" not in printed or "@add_barrier_body" not in printed:
            raise AssertionError("expected printed MLIR to contain arch.launch custom syntax with @callee")

    callee_ast = parse_function(add_barrier_body)
    for func_op in (
        build_func_op(add_barrier_body, *tensor_args),
        build_func_op_from_ast(callee_ast, runtime_args=tensor_args),
    ):
        body_ops = list(func_op.body.block.ops)
        barrier_ops = [op for op in body_ops if isinstance(op, ArchBarrierOp)]
        query_ops = [op for op in body_ops if isinstance(op, ArchGetThreadNumOp)]
        return_ops = [op for op in body_ops if isinstance(op, func.ReturnOp)]
        if len(barrier_ops) != 1:
            raise AssertionError("expected launched body to lower one arch.barrier op")
        if len(query_ops) != 1:
            raise AssertionError("expected launched body to lower one arch.get_thread_num op")
        if query_ops[0].result.type != SymbolValueType.from_expr("thread_num"):
            raise AssertionError('expected launched body query type to stay !symbol.int<"thread_num">')
        if len(return_ops) != 1 or return_ops[0].arguments[0].type != SymbolValueType.from_expr("thread_num"):
            raise AssertionError("expected launched body return to keep thread_num symbol type")


# MGEN-042
# 创建者: 小李飞刀
# 最后一次更改: 小李飞刀
# 功能说明: 验证 `mlir_gen(...)` 返回 `builtin.module`，且包含根函数的 `func.func`。
# 测试目的: 覆盖单函数路径无需调用方手工包装 `ModuleOp([func_op])` 的公开契约。
# 使用示例: pytest -q test/dsl/test_mlir_gen.py -k test_mlir_gen_returns_builtin_module
# 对应功能实现文件路径: kernel_gen/dsl/mlir_gen.py
# 对应 spec 文件路径: spec/dsl/mlir_gen.md
# 对应测试文件路径: test/dsl/test_mlir_gen.py
def test_mlir_gen_returns_builtin_module() -> None:
    def main(x: "Tensor[f32, 4]") -> "Tensor[f32, 4]":
        return x

    module = mlir_gen_module.mlir_gen(main, _tensor_arg([4]))
    assert isinstance(module, ModuleOp)
    func_ops = [op for op in module.ops if isinstance(op, func.FuncOp)]
    assert len(func_ops) == 1

    text = _print_module(module)
    assert "func.func" in text
    assert "@main" in text


# MGEN-043
# 创建者: 小李飞刀
# 最后一次更改: 小李飞刀
# 功能说明: 验证 `mlir_gen(...)` 会收集根函数调用的 Python callee 的传递闭包并补齐到 module。
# 测试目的: 覆盖 `root -> mid -> leaf` 的 transitive callee 收集。
# 使用示例: pytest -q test/dsl/test_mlir_gen.py -k test_mlir_gen_collects_transitive_callees
# 对应功能实现文件路径: kernel_gen/dsl/mlir_gen.py
# 对应 spec 文件路径: spec/dsl/mlir_gen.md
# 对应测试文件路径: test/dsl/test_mlir_gen.py
def test_mlir_gen_collects_transitive_callees() -> None:
    def main(x: "Tensor[f32, 4]") -> "Tensor[f32, 4]":
        return _mlir_gen_transitive_mid(x)

    module = mlir_gen_module.mlir_gen(main, _tensor_arg([4]))
    func_ops = [op for op in module.ops if isinstance(op, func.FuncOp)]
    assert len(func_ops) == 3

    text = _print_module(module)
    assert "@main" in text
    assert "@_mlir_gen_transitive_mid" in text
    assert "@_mlir_gen_transitive_leaf" in text


# MGEN-044
# 创建者: 小李飞刀
# 最后一次更改: 小李飞刀
# 功能说明: 验证 `mlir_gen(...)` module 内函数顺序确定：root 在前，callee 按首次出现调用顺序做 DFS 追加。
# 测试目的: 锁定 `root -> left -> left_leaf` 与 `root -> right -> right_leaf` 的函数排列顺序。
# 使用示例: pytest -q test/dsl/test_mlir_gen.py -k test_mlir_gen_module_function_order_is_dfs
# 对应功能实现文件路径: kernel_gen/dsl/mlir_gen.py
# 对应 spec 文件路径: spec/dsl/mlir_gen.md
# 对应测试文件路径: test/dsl/test_mlir_gen.py
def test_mlir_gen_module_function_order_is_dfs() -> None:
    def main(x: "Tensor[f32, 4]") -> "Tensor[f32, 4]":
        y = _mlir_gen_dfs_left(x)
        _ = _mlir_gen_dfs_right(x)
        return y

    module = mlir_gen_module.mlir_gen(main, _tensor_arg([4]))
    ordered_func_names = [
        op.sym_name.data for op in module.ops if isinstance(op, func.FuncOp) and isinstance(op.sym_name, StringAttr)
    ]
    assert ordered_func_names == [
        "main",
        "_mlir_gen_dfs_left",
        "_mlir_gen_dfs_left_leaf",
        "_mlir_gen_dfs_right",
        "_mlir_gen_dfs_right_leaf",
    ]


# MGEN-045
# 创建者: 小李飞刀
# 最后一次更改: 小李飞刀
# 功能说明: 验证 `mlir_gen(...)` 遇到不支持的 callee 形式时失败并返回固定短语。
# 测试目的: 以本地闭包函数触发 `unsupported callee function` 失败路径。
# 使用示例: pytest -q test/dsl/test_mlir_gen.py -k test_mlir_gen_rejects_unsupported_callee
# 对应功能实现文件路径: kernel_gen/dsl/mlir_gen.py
# 对应 spec 文件路径: spec/dsl/mlir_gen.md
# 对应测试文件路径: test/dsl/test_mlir_gen.py
def test_mlir_gen_rejects_unsupported_callee() -> None:
    scale = 1

    def helper(x: "Tensor[f32, 4]") -> "Tensor[f32, 4]":
        if scale:
            return x
        return x

    def main(x: "Tensor[f32, 4]") -> "Tensor[f32, 4]":
        return helper(x)

    with pytest.raises(mlir_gen_module.MlirGenModuleError) as excinfo:
        mlir_gen_module.mlir_gen(main, _tensor_arg([4]))
    assert "MlirGenModuleError: unsupported callee function" in str(excinfo.value)


# MGEN-046
# 创建者: 小李飞刀
# 最后一次更改: 小李飞刀
# 功能说明: 验证 `mlir_gen(...)` 遇到递归 callee 图时失败并返回固定短语。
# 测试目的: 构造 `A -> B -> A` 递归图，锁定错误消息收敛为 `recursive callee graph is not supported`。
# 使用示例: pytest -q test/dsl/test_mlir_gen.py -k test_mlir_gen_rejects_recursive_callee_graph
# 对应功能实现文件路径: kernel_gen/dsl/mlir_gen.py
# 对应 spec 文件路径: spec/dsl/mlir_gen.md
# 对应测试文件路径: test/dsl/test_mlir_gen.py
def test_mlir_gen_rejects_recursive_callee_graph() -> None:
    def main(x: "Tensor[f32, 4]") -> "Tensor[f32, 4]":
        return _mlir_gen_recursive_a(x)

    with pytest.raises(mlir_gen_module.MlirGenModuleError) as excinfo:
        mlir_gen_module.mlir_gen(main, _tensor_arg([4]))
    assert "MlirGenModuleError: recursive callee graph is not supported" in str(excinfo.value)


# MGEN-047
# 创建者: 小李飞刀
# 最后一次更改: 小李飞刀
# 功能说明: 验证 `mlir_gen(...)` 同一 callee 在多个 call-site 下推导出不一致签名时失败并返回固定短语。
# 测试目的: 使用不同 shape 的 tensor 实参触发不一致签名，锁定错误消息收敛为 `inconsistent callee signature`。
# 使用示例: pytest -q test/dsl/test_mlir_gen.py -k test_mlir_gen_rejects_inconsistent_callee_signature
# 对应功能实现文件路径: kernel_gen/dsl/mlir_gen.py
# 对应 spec 文件路径: spec/dsl/mlir_gen.md
# 对应测试文件路径: test/dsl/test_mlir_gen.py
def test_mlir_gen_rejects_inconsistent_callee_signature() -> None:
    def main(x: "Tensor[f32, 2, 2]", y: "Tensor[f32, 4]") -> "Tensor[f32, 2, 2]":
        _ = _mlir_gen_inconsistent_signature_helper(x)
        _ = _mlir_gen_inconsistent_signature_helper(y)
        return x

    with pytest.raises(mlir_gen_module.MlirGenModuleError) as excinfo:
        mlir_gen_module.mlir_gen(main, _tensor_arg([2, 2]), _tensor_arg([4]))
    assert "MlirGenModuleError: inconsistent callee signature" in str(excinfo.value)
