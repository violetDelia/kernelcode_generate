"""AST parsing tests.

创建者: 小李飞刀
最后一次更改: 金铲铲大作战

功能说明:
- 覆盖 AST 解析入口、注解解析与诊断负路径的回归测试。

使用示例:
- pytest -q test/dsl/test_ast.py

覆盖率信息:
- 覆盖率命令: coverage run -m pytest -q test/dsl/test_ast.py && coverage report --include=kernel_gen/dsl/ast.py -m
- 覆盖率结果: 未统计（待补充）
- 达标线: 95%

关联文件:
- 功能实现: kernel_gen/dsl/ast.py
- Spec 文档: spec/dsl/ast.md
- 测试文件: test/dsl/test_ast.py
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
    SymbolGetDimOp,
    SymbolGetStrideOp,
    SymbolMulOp,
    SymbolSubOp,
    SymbolValueType,
)
from kernel_gen.dsl.ast import (
    AstParseError,
    ArchBarrierAST,
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


# AST-014B
# 创建者: 我不是牛马
# 最后一次更改: 我不是牛马
# 最近一次运行测试时间: 2026-03-25 21:41:29 +0800
# 最近一次运行成功时间: 2026-03-25 21:41:29 +0800
# 功能说明: 验证未显式导入的 bare get_block_id 调用会在 AST 入口被统一拒绝。
# 测试目的: 锁定未导入的 get_block_id(1) 与 get_block_id(x=1) 不再进入 helper 语义校验，而是直接返回 Unsupported call expression。
# 使用示例: pytest -q test/dsl/test_ast.py -k test_parse_function_rejects_invalid_get_block_id_arity_variants
# 对应功能实现文件路径: kernel_gen/dsl/ast.py
# 对应 spec 文件路径: spec/dsl/ast.md
# 对应测试文件路径: test/dsl/test_ast.py
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


# AST-014D
# 创建者: 咯咯咯
# 最后一次更改: 咯咯咯
# 最近一次运行测试时间: 2026-03-26 00:27:39 +0800
# 最近一次运行成功时间: 2026-03-26 00:27:39 +0800
# 功能说明: 验证未显式导入的 bare get_block_num 调用会在 AST 入口被统一拒绝。
# 测试目的: 锁定未导入的 get_block_num(1) 与 get_block_num(x=1) 不再进入 helper 语义校验，而是直接返回 Unsupported call expression。
# 使用示例: pytest -q test/dsl/test_ast.py -k test_parse_function_rejects_invalid_get_block_num_arity_variants
# 对应功能实现文件路径: kernel_gen/dsl/ast.py
# 对应 spec 文件路径: spec/dsl/ast.md
# 对应测试文件路径: test/dsl/test_ast.py
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


# AST-014F
# 创建者: 我不是牛马
# 最后一次更改: 我不是牛马
# 最近一次运行测试时间: 2026-03-25 21:41:29 +0800
# 最近一次运行成功时间: 2026-03-25 21:41:29 +0800
# 功能说明: 验证未显式导入的 bare get_subthread_id 调用会在 AST 入口被统一拒绝。
# 测试目的: 锁定未导入的 get_subthread_id(1) 与 get_subthread_id(x=1) 不再进入 helper 语义校验，而是直接返回 Unsupported call expression。
# 使用示例: pytest -q test/dsl/test_ast.py -k test_parse_function_rejects_invalid_get_subthread_id_arity_variants
# 对应功能实现文件路径: kernel_gen/dsl/ast.py
# 对应 spec 文件路径: spec/dsl/ast.md
# 对应测试文件路径: test/dsl/test_ast.py
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


# AST-014H
# 创建者: 朽木露琪亚
# 最后一次更改: 朽木露琪亚
# 最近一次运行测试时间: 2026-03-27 01:38:30 +0800
# 最近一次运行成功时间: 2026-03-27 01:38:30 +0800
# 功能说明: 验证未显式导入的 bare get_thread_id 调用会在 AST 入口被统一拒绝。
# 测试目的: 锁定未导入的 get_thread_id(1) 与 get_thread_id(x=1) 不再进入 helper 语义校验，而是直接返回 Unsupported call expression。
# 使用示例: pytest -q test/dsl/test_ast.py -k test_parse_function_rejects_invalid_get_thread_id_arity_variants
# 对应功能实现文件路径: kernel_gen/dsl/ast.py
# 对应 spec 文件路径: spec/dsl/ast.md
# 对应测试文件路径: test/dsl/test_ast.py
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


# AST-014I
# 创建者: OpenAI
# 最后一次更改: 小李飞刀
# 最近一次运行测试时间: 2026-03-31 03:20:00 +0800
# 最近一次运行成功时间: 2026-03-31 03:20:00 +0800
# 功能说明: 验证 `value.get_shape()[axis]` 可解析为 TensorAxisAccessAST。
# 测试目的: 锁定 AST 层对 Memory shape 轴访问语义的保留，不在解析阶段提前降级或求值。
# 使用示例: pytest -q test/dsl/test_ast.py -k test_parse_function_supports_memory_get_shape_index
# 对应功能实现文件路径: kernel_gen/dsl/ast.py
# 对应 spec 文件路径: spec/dsl/ast.md
# 对应测试文件路径: test/dsl/test_ast.py
def test_parse_function_supports_memory_get_shape_index() -> None:
    def kernel(value: "Tensor[f32, 4, 8]") -> int:
        return value.get_shape()[1]

    func_ast = parse_function(kernel)

    if len(func_ast.body.statements) != 1:
        raise AssertionError("expected one AST statement for get_shape()[axis]")
    stmt = func_ast.body.statements[0]
    if not isinstance(stmt, TensorAxisAccessAST):
        raise AssertionError("expected get_shape()[axis] to parse into TensorAxisAccessAST")
    if stmt.kind != "shape":
        raise AssertionError("expected TensorAxisAccessAST kind to be shape")
    if not isinstance(stmt.axis, ConstAST) or stmt.axis.value != 1:
        raise AssertionError("expected get_shape axis to stay ConstAST(1)")


# AST-014J
# 创建者: OpenAI
# 最后一次更改: 小李飞刀
# 最近一次运行测试时间: 2026-03-31 03:20:00 +0800
# 最近一次运行成功时间: 2026-03-31 03:20:00 +0800
# 功能说明: 验证 `value.get_stride()[axis]` 可解析为 TensorAxisAccessAST。
# 测试目的: 锁定 AST 层对 Memory stride 轴访问语义的保留，不在解析阶段提前降级或求值。
# 使用示例: pytest -q test/dsl/test_ast.py -k test_parse_function_supports_memory_get_stride_index
# 对应功能实现文件路径: kernel_gen/dsl/ast.py
# 对应 spec 文件路径: spec/dsl/ast.md
# 对应测试文件路径: test/dsl/test_ast.py
def test_parse_function_supports_memory_get_stride_index() -> None:
    def kernel(value: "Tensor[f32, 4, 8]") -> int:
        return value.get_stride()[0]

    func_ast = parse_function(kernel)

    if len(func_ast.body.statements) != 1:
        raise AssertionError("expected one AST statement for get_stride()[axis]")
    stmt = func_ast.body.statements[0]
    if not isinstance(stmt, TensorAxisAccessAST):
        raise AssertionError("expected get_stride()[axis] to parse into TensorAxisAccessAST")
    if stmt.kind != "stride":
        raise AssertionError("expected TensorAxisAccessAST kind to be stride")
    if not isinstance(stmt.axis, ConstAST) or stmt.axis.value != 0:
        raise AssertionError("expected get_stride axis to stay ConstAST(0)")


# AST-014J
# 创建者: 摸鱼小分队
# 最后一次更改: 摸鱼小分队
# 最近一次运行测试时间: 2026-03-27 02:08:59 +0800
# 最近一次运行成功时间: 2026-03-27 02:08:59 +0800
# 功能说明: 验证未显式导入的 bare get_subthread_num 调用会在 AST 入口被统一拒绝。
# 测试目的: 锁定未导入的 get_subthread_num(1) 与 get_subthread_num(x=1) 不再进入 helper 语义校验，而是直接返回 Unsupported call expression。
# 使用示例: pytest -q test/dsl/test_ast.py -k test_parse_function_rejects_invalid_get_subthread_num_arity_variants
# 对应功能实现文件路径: kernel_gen/dsl/ast.py
# 对应 spec 文件路径: spec/dsl/ast.md
# 对应测试文件路径: test/dsl/test_ast.py
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


# AST-014JA
# 创建者: 金铲铲大作战
# 最后一次更改: 金铲铲大作战
# 功能说明: 验证未显式导入的 bare DMA helper 调用会在 AST 入口被统一拒绝。
# 测试目的: 锁定裸 load/slice/store/deslice 不再回退为 helper 解析，而是统一报 Unsupported call expression。
# 使用示例: pytest -q test/dsl/test_ast.py -k test_parse_function_rejects_unimported_dma_helpers
# 对应功能实现文件路径: kernel_gen/dsl/ast.py
# 对应 spec 文件路径: spec/dsl/ast.md
# 对应测试文件路径: test/dsl/test_ast.py
def test_parse_function_rejects_unimported_dma_helpers(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    invalid_sources = (
        """\
def kernel(src: "Tensor[f32, 4, 4]") -> "Tensor[f32, 2, 2]":
    return load(src, [0, 0], [2, 2])
""",
        """\
def kernel(src: "Tensor[f32, 4, 4]") -> "Tensor[f32, 2, 2]":
    return slice(src, [0, 0], [2, 2], [1, 1], MemorySpace.LM)
""",
        """\
def kernel(tile: "Tensor[f32, 2, 2]", dst: "Tensor[f32, 4, 4]") -> None:
    store(tile, dst, [0, 0], [2, 2])
""",
        """\
def kernel(tile: "Tensor[f32, 2, 2]", dst: "Tensor[f32, 4, 4]") -> None:
    deslice(tile, dst, [0, 0], [2, 2], [1, 1], MemorySpace.GM)
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


# AST-014JB
# 创建者: 小李飞刀
# 最后一次更改: 小李飞刀
# 功能说明: 验证 helper allowlist 仅允许 alias.helper(...) 形式的 import-bound 调用。
# 测试目的: 锁定 `kernel_gen.operation.dma.slice(...)` 这类链式属性访问不会绕过 helper 绑定检查。
# 使用示例: pytest -q test/dsl/test_ast.py -k test_parse_function_rejects_dma_helper_call_via_attribute_chain
# 对应功能实现文件路径: kernel_gen/dsl/ast.py
# 对应 spec 文件路径: spec/dsl/mlir_gen.md
# 对应测试文件路径: test/dsl/test_ast.py
def test_parse_function_rejects_dma_helper_call_via_attribute_chain(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import kernel_gen as kernel_gen_pkg

    def kernel(src: "Tensor[f32, 4, 4]") -> "Tensor[f32, 2, 2]":
        return kernel_gen.operation.dma.slice(src, [0, 0], [2, 2], [1, 1], MemorySpace.LM)

    monkeypatch.setitem(kernel.__globals__, "kernel_gen", kernel_gen_pkg)

    with pytest.raises(AstParseError) as exc_info:
        parse_function(kernel)

    diagnostics = exc_info.value.diagnostics
    if not diagnostics:
        raise AssertionError("expected diagnostics for helper call via attribute chain")
    if diagnostics[0].message != "Unsupported call expression":
        raise AssertionError("expected Unsupported call expression diagnostic")


# AST-014JC
# 创建者: 小李飞刀
# 最后一次更改: 小李飞刀
# 功能说明: 验证 direct symbol alias helper 必须匹配真实模块导出对象。
# 测试目的: 拒绝伪造 `__module__/__name__` 的同名 callable 通过 helper allowlist。
# 使用示例: pytest -q test/dsl/test_ast.py -k test_parse_function_rejects_spoofed_import_bound_helper_object
# 对应功能实现文件路径: kernel_gen/dsl/ast.py
# 对应 spec 文件路径: spec/dsl/mlir_gen.md
# 对应测试文件路径: test/dsl/test_ast.py
def test_parse_function_rejects_spoofed_import_bound_helper_object(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fake_slice(*_args: object, **_kwargs: object) -> object:
        raise AssertionError("fake slice should not execute during parsing")

    fake_slice.__module__ = "kernel_gen.operation.dma"
    fake_slice.__name__ = "slice"

    monkeypatch.setitem(globals(), "slice", fake_slice)

    source = """\
def kernel(src: "Tensor[f32, 4, 4]") -> "Tensor[f32, 2, 2]":
    return slice(src, [0, 0], [2, 2], [1, 1], MemorySpace.LM)
"""

    with pytest.raises(AstParseError) as exc_info:
        _parse_function_from_source(monkeypatch, source)
    diagnostics = exc_info.value.diagnostics
    if not diagnostics:
        raise AssertionError("expected diagnostics for spoofed helper object")
    if diagnostics[0].message != "Unsupported call expression":
        raise AssertionError("expected Unsupported call expression diagnostic")


# AST-014JD
# 创建者: 小李飞刀
# 最后一次更改: 小李飞刀
# 功能说明: 验证函数体内非白名单 ImportFrom 不会触发动态导入副作用。
# 测试目的: 锁定 `from definitely_missing_package import load` 仅遮蔽局部名字并返回 Unsupported call expression，而非抛出 ModuleNotFoundError。
# 使用示例: pytest -q test/dsl/test_ast.py -k test_parse_function_rejects_non_whitelisted_local_import_without_side_effect
# 对应功能实现文件路径: kernel_gen/dsl/ast.py
# 对应 spec 文件路径: spec/dsl/ast.md
# 对应测试文件路径: test/dsl/test_ast.py
def test_parse_function_rejects_non_whitelisted_local_import_without_side_effect(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source = """\
def kernel(src: "Tensor[f32, 4, 4]") -> "Tensor[f32, 2, 2]":
    from definitely_missing_package import load
    return load(src, [0, 0], [2, 2], [1, 1], MemorySpace.LM)
"""

    with pytest.raises(AstParseError) as exc_info:
        _parse_function_from_source(monkeypatch, source)
    diagnostics = exc_info.value.diagnostics
    if not diagnostics:
        raise AssertionError("expected diagnostics for non-whitelisted local import")
    if diagnostics[0].message != "Unsupported call expression":
        raise AssertionError("expected Unsupported call expression diagnostic")


# AST-014K
# 创建者: 朽木露琪亚
# 最后一次更改: 朽木露琪亚
# 最近一次运行测试时间: 2026-04-05 00:00:00 +0800
# 最近一次运行成功时间: 2026-04-05 00:00:00 +0800
# 功能说明: 验证 return 之后的 local import 仍触发末尾 return 约束。
# 测试目的: 锁定 return 后出现 Import/ImportFrom 触发 "Return statement must be last" 诊断。
# 使用示例: pytest -q test/dsl/test_ast.py -k test_parse_function_rejects_import_after_return
# 对应功能实现文件路径: kernel_gen/dsl/ast.py
# 对应 spec 文件路径: spec/dsl/ast.md
# 对应测试文件路径: test/dsl/test_ast.py
def test_parse_function_rejects_import_after_return(monkeypatch: pytest.MonkeyPatch) -> None:
    sources = (
        """\
def kernel(src: "Tensor[f32, 2, 2]") -> "Tensor[f32, 2, 2]":
    return src
    import kernel_gen.operation.dma as dma
""",
        """\
def kernel(src: "Tensor[f32, 2, 2]") -> "Tensor[f32, 2, 2]":
    return src
    from kernel_gen.operation.dma import load
""",
    )

    for source in sources:
        with pytest.raises(AstParseError) as exc_info:
            _parse_function_from_source(monkeypatch, source)
        diagnostics = exc_info.value.diagnostics
        if not diagnostics:
            raise AssertionError("expected diagnostics for import after return")
        if diagnostics[0].message != "Return statement must be last":
            raise AssertionError("expected Return statement must be last diagnostic")


# AST-001
# 创建者: 小李飞刀
# 最后一次更改: 金铲铲大作战
# 最近一次运行测试时间: 2026-03-22 15:38:56 +0800
# 最近一次运行成功时间: 2026-03-22 15:38:56 +0800
# 功能说明: 验证 parse_function 生成 FunctionAST 并保留位置信息。
# 测试目的: 验证 parse_function 生成 FunctionAST 并保留位置信息。
# 使用示例: pytest -q test/dsl/test_ast.py -k test_visit_function_builds_ast
# 对应功能实现文件路径: kernel_gen/dsl/ast.py
# 对应 spec 文件路径: spec/dsl/ast.md
# 对应测试文件路径: test/dsl/test_ast.py
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
# 使用示例: pytest -q test/dsl/test_ast.py -k test_ast_parse_function_parses_annotations
# 对应功能实现文件路径: kernel_gen/dsl/ast.py
# 对应 spec 文件路径: spec/dsl/ast.md
# 对应测试文件路径: test/dsl/test_ast.py
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
# 使用示例: pytest -q test/dsl/test_ast.py -k test_ast_parse_function_accepts_tensor_bool_annotations
# 对应功能实现文件路径: kernel_gen/dsl/ast.py
# 对应 spec 文件路径: spec/dsl/ast.md
# 对应测试文件路径: test/dsl/test_ast.py
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
# 使用示例: pytest -q test/dsl/test_ast.py -k test_ast_parse_function_missing_annotation_reports_diagnostics
# 对应功能实现文件路径: kernel_gen/dsl/ast.py
# 对应 spec 文件路径: spec/dsl/ast.md
# 对应测试文件路径: test/dsl/test_ast.py
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


# AST-001A
# 创建者: 朽木露琪亚
# 最后一次更改: 金铲铲大作战
# 最近一次运行测试时间: 2026-03-22 15:38:56 +0800
# 最近一次运行成功时间: 2026-03-22 15:38:56 +0800
# 功能说明: 验证 parse_function 提供独立 AST 解析入口。
# 测试目的: 验证 parse_function 提供独立 AST 解析入口。
# 使用示例: pytest -q test/dsl/test_ast.py -k test_parse_function_entry
# 对应功能实现文件路径: kernel_gen/dsl/ast.py
# 对应 spec 文件路径: spec/dsl/ast.md
# 对应测试文件路径: test/dsl/test_ast.py
def test_parse_function_entry() -> None:
    def add(
        x: "Tensor[f32, 2, 2]",
        y: "Tensor[f32, 2, 2]",
    ) -> "Tensor[f32, 2, 2]":
        return x + y

    func_ast = parse_function(add)
    assert isinstance(func_ast, FunctionAST)
    assert [arg.name for arg in func_ast.iter_inputs()] == ["x", "y"]


def _assert_parse_function_supports_symbol_compare(op_name: str, source_token: str) -> None:
    """断言 parse_function 支持符号 compare family 语法。

    创建者: 朽木露琪亚
    最后一次更改: 朽木露琪亚

    功能说明:
    - 复用同一断言逻辑检查 `gt/le/lt/ne` 的 AST 解析结果。

    使用示例:
    - _assert_parse_function_supports_symbol_compare("gt", ">")

    关联文件:
    - spec: spec/dsl/ast.md
    - test: test/dsl/test_ast.py
    - 功能实现: kernel_gen/dsl/ast.py
    """

    if source_token == ">":
        def kernel(a: int, b: int) -> bool:
            return a > b
    elif source_token == "<=":
        def kernel(a: int, b: int) -> bool:
            return a <= b
    elif source_token == "<":
        def kernel(a: int, b: int) -> bool:
            return a < b
    elif source_token == "!=":
        def kernel(a: int, b: int) -> bool:
            return a != b
    else:  # pragma: no cover
        raise AssertionError(f"unsupported compare token: {source_token}")

    func_ast = parse_function(kernel)
    assert isinstance(func_ast.body.statements[-1], CompareExprAST)
    assert func_ast.body.statements[-1].op == op_name
    assert isinstance(func_ast.outputs[0], ScalarArgAST)
    assert func_ast.outputs[0].value_type is bool


def test_parse_function_supports_symbol_gt() -> None:
    _assert_parse_function_supports_symbol_compare("gt", ">")


def test_parse_function_supports_symbol_le() -> None:
    _assert_parse_function_supports_symbol_compare("le", "<=")


def test_parse_function_supports_symbol_lt() -> None:
    _assert_parse_function_supports_symbol_compare("lt", "<")


def test_parse_function_supports_symbol_ne() -> None:
    _assert_parse_function_supports_symbol_compare("ne", "!=")


# AST-R1
# 创建者: 朽木露琪亚
# 最后一次更改: 朽木露琪亚
# 最近一次运行测试时间: 2026-04-04 00:00:00 +0800
# 最近一次运行成功时间: 2026-04-04 00:00:00 +0800
# 功能说明: 验证无返回注解但有显式 return 的函数会保留函数级返回语法元信息。
# 测试目的: 锁定 `FunctionAST.outputs == []` 时，AST 仍能区分“显式 return 存在、未写返回注解、也不是 -> None”。
# 使用示例: pytest -q test/dsl/test_ast.py -k test_parse_function_preserves_explicit_return_without_return_annotation
# 对应功能实现文件路径: kernel_gen/dsl/ast.py
# 对应 spec 文件路径: spec/dsl/ast.md
# 对应测试文件路径: test/dsl/test_ast.py
def test_parse_function_preserves_explicit_return_without_return_annotation() -> None:
    def add_memory(
        lhs: "Tensor[i32, 2, 3]",
        rhs: "Tensor[i32, 2, 3]",
    ):
        out = lhs + rhs
        return out

    func_ast = parse_function(add_memory)
    assert func_ast.outputs == []
    assert func_ast.has_explicit_return is True
    assert func_ast.has_return_annotation is False
    assert func_ast.returns_none is False


# AST-001B
# 创建者: ChatGPT
# 最后一次更改: 金铲铲大作战
# 最近一次运行测试时间: 2026-03-22 15:38:56 +0800
# 最近一次运行成功时间: 2026-03-22 15:38:56 +0800
# 功能说明: 验证 parse_function 不依赖 ast_visitor.visit_function 的反向导入。
# 测试目的: 验证 parse_function 不依赖 ast_visitor.visit_function 的反向导入。
# 使用示例: pytest -q test/dsl/test_ast.py -k test_parse_function_does_not_depend_on_ast_visitor_entry
# 对应功能实现文件路径: kernel_gen/dsl/ast.py
# 对应 spec 文件路径: spec/dsl/ast.md
# 对应测试文件路径: test/dsl/test_ast.py
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


# AST-004
# 创建者: 小李飞刀
# 最后一次更改: 小李飞刀
# 最近一次运行测试时间: 2026-03-18 10:56:41 +0800
# 最近一次运行成功时间: 2026-03-18 10:56:41 +0800
# 功能说明: 验证 parse_function 可解析标准 Tensor 注解。
# 测试目的: 验证 parse_function 可解析标准 Tensor 注解。
# 使用示例: pytest -q test/dsl/test_ast.py -k test_globals_and_builtins_annotation_entry
# 对应功能实现文件路径: kernel_gen/dsl/ast.py
# 对应 spec 文件路径: spec/dsl/ast.md
# 对应测试文件路径: test/dsl/test_ast.py
def test_globals_and_builtins_annotation_entry() -> None:
    def add(x: "Tensor[f32, 2, 2]", y: "Tensor[f32, 2, 2]") -> "Tensor[f32, 2, 2]":
        return x + y

    func_ast = parse_function(add)
    assert func_ast.name == "add"


# AST-005
# 创建者: 小李飞刀
# 最后一次更改: 小李飞刀
# 最近一次运行测试时间: 2026-03-18 10:56:41 +0800
# 最近一次运行成功时间: 2026-03-18 10:56:41 +0800
# 功能说明: 验证未知名称在 AST 阶段产生诊断信息。
# 测试目的: 验证未知名称在 AST 阶段产生诊断信息。
# 使用示例: pytest -q test/dsl/test_ast.py -k test_unknown_name_reports_diagnostics
# 对应功能实现文件路径: kernel_gen/dsl/ast.py
# 对应 spec 文件路径: spec/dsl/ast.md
# 对应测试文件路径: test/dsl/test_ast.py
def test_unknown_name_reports_diagnostics() -> None:
    def bad(x: "Tensor[f32, 2, 2]") -> "Tensor[f32, 2, 2]":
        return y

    with pytest.raises(AstParseError) as exc_info:
        parse_function(bad)
    diagnostics = exc_info.value.diagnostics
    assert diagnostics
    assert diagnostics[0].location is not None


# AST-006
# 创建者: 小李飞刀
# 最后一次更改: 小李飞刀
# 最近一次运行测试时间: 2026-03-18 10:56:41 +0800
# 最近一次运行成功时间: 2026-03-18 10:56:41 +0800
# 功能说明: 验证非法返回注解会保留可定位诊断并向上抛出。
# 测试目的: 验证非法返回注解会保留可定位诊断并向上抛出。
# 使用示例: pytest -q test/dsl/test_ast.py -k test_invalid_return_annotation_reports_diagnostics
# 对应功能实现文件路径: kernel_gen/dsl/ast.py
# 对应 spec 文件路径: spec/dsl/ast.md
# 对应测试文件路径: test/dsl/test_ast.py
def test_invalid_return_annotation_reports_diagnostics() -> None:
    def bad_return(x: "Tensor[f32, 2, 2]") -> "NotSupported":
        return x

    with pytest.raises(AstParseError) as exc_info:
        parse_function(bad_return)
    diagnostics = exc_info.value.diagnostics
    assert diagnostics
    assert diagnostics[0].location is not None


# AST-007
# 创建者: 小李飞刀
# 最后一次更改: 小李飞刀
# 最近一次运行测试时间: 2026-03-18 10:56:41 +0800
# 最近一次运行成功时间: 2026-03-18 10:56:41 +0800
# 功能说明: 验证缺失 return 会抛出带诊断的错误。
# 测试目的: 验证缺失 return 会抛出带诊断的错误。
# 使用示例: pytest -q test/dsl/test_ast.py -k test_missing_return_reports_diagnostics
# 对应功能实现文件路径: kernel_gen/dsl/ast.py
# 对应 spec 文件路径: spec/dsl/ast.md
# 对应测试文件路径: test/dsl/test_ast.py
def test_missing_return_reports_diagnostics() -> None:
    def bad(x: "Tensor[f32, 2, 2]") -> "Tensor[f32, 2, 2]":
        y = x

    with pytest.raises(AstParseError) as exc_info:
        parse_function(bad)
    diagnostics = exc_info.value.diagnostics
    assert diagnostics
    assert diagnostics[0].location is not None


# AST-008
# 创建者: 小李飞刀
# 最后一次更改: 小李飞刀
# 最近一次运行测试时间: 2026-03-18 10:56:41 +0800
# 最近一次运行成功时间: 2026-03-18 10:56:41 +0800
# 功能说明: 验证缺少维度的 Tensor 注解会抛出带诊断的错误。
# 测试目的: 验证缺少维度的 Tensor 注解会抛出带诊断的错误。
# 使用示例: pytest -q test/dsl/test_ast.py -k test_missing_tensor_dimensions_reports_diagnostics
# 对应功能实现文件路径: kernel_gen/dsl/ast.py
# 对应 spec 文件路径: spec/dsl/ast.md
# 对应测试文件路径: test/dsl/test_ast.py
def test_missing_tensor_dimensions_reports_diagnostics() -> None:
    def bad_string(x: "Tensor[f32]") -> "Tensor[f32, 2, 2]":
        return x
    with pytest.raises(AstParseError) as exc_info:
        parse_function(bad_string)
    diagnostics = exc_info.value.diagnostics
    assert diagnostics
    assert diagnostics[0].location is not None


# AST-009
# 创建者: OpenAI
# 最后一次更改: 金铲铲大作战
# 最近一次运行测试时间: 2026-03-26 21:43:31 +0800
# 最近一次运行成功时间: 2026-03-26 21:43:31 +0800
# 功能说明: 验证未注解 SymbolDim 参数可按标量参数解析。
# 测试目的: 验证未注解 SymbolDim 参数可按标量参数解析。
# 使用示例: pytest -q test/dsl/test_ast.py -k test_parse_function_infers_symboldim_arguments_without_annotations
# 对应功能实现文件路径: kernel_gen/dsl/ast.py
# 对应 spec 文件路径: spec/dsl/ast.md
# 对应测试文件路径: test/dsl/test_ast.py
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
# 使用示例: pytest -q test/dsl/test_ast.py -k test_parse_function_infers_bool_runtime_arguments_without_annotations
# 对应功能实现文件路径: kernel_gen/dsl/ast.py
# 对应 spec 文件路径: spec/dsl/ast.md
# 对应测试文件路径: test/dsl/test_ast.py
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
# 使用示例: pytest -q test/dsl/test_ast.py -k test_parse_function_rejects_float_runtime_arguments_without_annotations
# 对应功能实现文件路径: kernel_gen/dsl/ast.py
# 对应 spec 文件路径: spec/dsl/ast.md
# 对应测试文件路径: test/dsl/test_ast.py
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
# 使用示例: pytest -q test/dsl/test_ast.py -k test_parse_function_supports_tensor_i1_return_annotation
# 对应功能实现文件路径: kernel_gen/dsl/ast.py
# 对应 spec 文件路径: spec/dsl/ast.md
# 对应测试文件路径: test/dsl/test_ast.py
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
# 使用示例: pytest -q test/dsl/test_ast.py -k test_parse_function_rejects_unsupported_nn_arithmetic_arity_variants
# 对应功能实现文件路径: kernel_gen/dsl/ast.py
# 对应 spec 文件路径: spec/dsl/ast.md
# 对应测试文件路径: test/dsl/test_ast.py
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
# 最近一次运行测试时间: 2026-03-28 12:10:00 +0800
# 最近一次运行成功时间: 2026-03-28 12:10:00 +0800
# 功能说明: 验证 parse_function 支持 bool 返回注解与 JoinedStr Tensor 注解。
# 测试目的: 确保 f"Tensor[...]" 形式的注解可在 AST 阶段归一化并保留符号维度文本。
# 使用示例: pytest -q test/dsl/test_ast.py -k test_ast_parse_function_supports_symbol_scalar_and_joinedstr_annotations
# 对应功能实现文件路径: kernel_gen/dsl/ast.py
# 对应 spec 文件路径: spec/dsl/ast.md
# 对应测试文件路径: test/dsl/test_ast.py
def test_ast_parse_function_supports_symbol_scalar_and_joinedstr_annotations() -> None:
    symbol = SymbolDim("M")
    rows = 4

    def kernel(x: f"Tensor[f32, {SYMBOL}, {ROWS}]") -> bool:
        return True

    kernel.__globals__["SYMBOL"] = symbol
    kernel.__globals__["ROWS"] = rows
    func_ast = parse_function(kernel)
    if len(func_ast.inputs) != 1:
        raise AssertionError("expected one input annotation for kernel")
    if not isinstance(func_ast.inputs[0], TensorAST):
        raise AssertionError("expected TensorAST input annotation for kernel")
    if func_ast.inputs[0].memory.shape.get_values() != [str(symbol.get_symbol()), rows]:
        raise AssertionError("expected JoinedStr tensor annotation to preserve symbol/row dims")
    if len(func_ast.outputs) != 1:
        raise AssertionError("expected one output annotation for kernel")
    if not isinstance(func_ast.outputs[0], ScalarArgAST):
        raise AssertionError("expected ScalarArgAST output annotation for kernel")
    if func_ast.outputs[0].value_type is not bool:
        raise AssertionError("expected bool return annotation to parse as ScalarArgAST")


# AST-013B
# 创建者: 金铲铲大作战
# 最后一次更改: 金铲铲大作战
# 功能说明: 验证 `-> float` 返回注解与 `float(symbol.int)` 可进入 AST 主链。
# 测试目的: 锁定 `return float(n)` 在 AST 层会解析为 `SymbolToFloatAST`，且返回注解保留为 `float`。
# 使用示例: pytest -q test/dsl/test_ast.py -k test_ast_accepts_float_return_annotation_for_symbol_to_float
# 对应功能实现文件路径: kernel_gen/dsl/ast.py
# 对应 spec 文件路径: spec/dsl/ast.md
# 对应测试文件路径: test/dsl/test_ast.py
def test_ast_accepts_float_return_annotation_for_symbol_to_float() -> None:
    def cast_dim(n: int) -> float:
        return float(n)

    func_ast = parse_function(cast_dim)
    if len(func_ast.outputs) != 1:
        raise AssertionError("expected one float return annotation")
    if not isinstance(func_ast.outputs[0], ScalarArgAST):
        raise AssertionError("expected float return annotation to parse as ScalarArgAST")
    if func_ast.outputs[0].value_type is not float:
        raise AssertionError("expected return annotation type to stay float")
    if len(func_ast.body.statements) != 1:
        raise AssertionError("expected one AST statement for symbol.to_float")
    stmt = func_ast.body.statements[0]
    if not isinstance(stmt, SymbolToFloatAST):
        raise AssertionError("expected float(n) to parse into SymbolToFloatAST")
    if not isinstance(stmt.source, ScalarArgAST):
        raise AssertionError("expected symbol.to_float source to stay ScalarArgAST")
    if stmt.source.name != "n" or stmt.source.value_type is not int:
        raise AssertionError("expected symbol.to_float source to keep int parameter identity")


# AST-013C
# 创建者: 金铲铲大作战
# 最后一次更改: 金铲铲大作战
# 功能说明: 验证 `-> float` 返回注解不会放宽到非 `symbol.to_float` 返回形态。
# 测试目的: 锁定 `-> float` 当前只服务于 `return float(symbol.int)` 入口，其他返回形态仍固定报 `Unsupported return annotation`。
# 使用示例: pytest -q test/dsl/test_ast.py -k test_ast_rejects_non_float_annotation_for_symbol_to_float
# 对应功能实现文件路径: kernel_gen/dsl/ast.py
# 对应 spec 文件路径: spec/dsl/ast.md
# 对应测试文件路径: test/dsl/test_ast.py
def test_ast_rejects_non_float_annotation_for_symbol_to_float() -> None:
    def cast_dim(n: int) -> float:
        return n

    with pytest.raises(AstParseError) as exc_info:
        parse_function(cast_dim)
    diagnostics = exc_info.value.diagnostics
    if not diagnostics:
        raise AssertionError("expected diagnostics for unsupported return annotation")
    if diagnostics[0].message != "Unsupported return annotation":
        raise AssertionError("expected Unsupported return annotation diagnostic")


# AST-013A
# 创建者: 金铲铲大作战
# 最后一次更改: 金铲铲大作战
# 最近一次运行测试时间: 2026-03-25 12:01:58 +0800
# 最近一次运行成功时间: 2026-03-25 12:01:58 +0800
# 功能说明: 验证 load helper 的 arity/source/space 负路径报错口径不变。
# 测试目的: 锁定 _parse_load_like_call 在 load 分支上的非法参数个数、非法 source 与非法 space 诊断。
# 使用示例: pytest -q test/dsl/test_ast.py -k test_parse_function_rejects_invalid_load_helper_variants
# 对应功能实现文件路径: kernel_gen/dsl/ast.py
# 对应 spec 文件路径: spec/dsl/ast.md
# 对应测试文件路径: test/dsl/test_ast.py
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


# AST-014
# 创建者: 金铲铲大作战
# 最后一次更改: 金铲铲大作战
# 最近一次运行测试时间: 2026-03-25 12:01:58 +0800
# 最近一次运行成功时间: 2026-03-25 12:01:58 +0800
# 功能说明: 验证 slice helper 的 arity/source/space 负路径报错口径不变。
# 测试目的: 锁定 _parse_load_like_call 在 slice 分支上的非法参数个数、非法 source 与非法 space 诊断。
# 使用示例: pytest -q test/dsl/test_ast.py -k test_parse_function_rejects_invalid_slice_helper_variants
# 对应功能实现文件路径: kernel_gen/dsl/ast.py
# 对应 spec 文件路径: spec/dsl/ast.md
# 对应测试文件路径: test/dsl/test_ast.py
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


# AST-014A
# 创建者: 小李飞刀
# 最后一次更改: 小李飞刀
# 功能说明: 验证 copy helper 的非法 space 参数继续在 AST 阶段报错。
# 测试目的: 锁定 dma.copy 的 `space` 类型校验不回退。
# 使用示例: pytest -q test/dsl/test_ast.py -k test_parse_function_rejects_invalid_copy_helper_space
# 对应功能实现文件路径: kernel_gen/dsl/ast.py
# 对应 spec 文件路径: spec/dsl/ast.md
# 对应测试文件路径: test/dsl/test_ast.py
def test_parse_function_rejects_invalid_copy_helper_space(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from kernel_gen.operation.dma import copy

    def bad_space(src: "Tensor[f32, 4, 4]") -> "Tensor[f32, 4, 4]":
        return copy(src, 1)

    monkeypatch.setitem(bad_space.__globals__, "copy", copy)

    with pytest.raises(AstParseError) as exc_info:
        parse_function(bad_space)
    diagnostics = exc_info.value.diagnostics
    if not diagnostics:
        raise AssertionError("expected diagnostics for copy invalid space")
    if diagnostics[0].message != "copy space must be MemorySpace":
        raise AssertionError(f"expected copy diagnostic 'copy space must be MemorySpace', got {diagnostics[0].message!r}")


# AST-014B
# 创建者: 小李飞刀
# 最后一次更改: 小李飞刀
# 功能说明: 验证 cast helper 的非法 dtype/memoryspace 参数继续在 AST 阶段报错。
# 测试目的: 锁定 dma.cast 的 `dtype` 与 `memoryspace` 类型校验不回退。
# 使用示例: pytest -q test/dsl/test_ast.py -k test_parse_function_rejects_invalid_cast_helper_parameters
# 对应功能实现文件路径: kernel_gen/dsl/ast.py
# 对应 spec 文件路径: spec/dsl/ast.md
# 对应测试文件路径: test/dsl/test_ast.py
def test_parse_function_rejects_invalid_cast_helper_parameters(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from kernel_gen.operation.dma import cast

    def bad_dtype(src: "Tensor[f32, 4, 4]") -> "Tensor[f16, 4, 4]":
        return cast(src, "f16")

    def bad_memoryspace(src: "Tensor[f32, 4, 4]") -> "Tensor[f16, 4, 4]":
        return cast(src, NumericType.Float16, "LM")

    for fn in (bad_dtype, bad_memoryspace):
        monkeypatch.setitem(fn.__globals__, "cast", cast)

    expected_messages = (
        ("cast dtype must be NumericType", bad_dtype),
        ("cast memoryspace must be MemorySpace", bad_memoryspace),
    )
    for expected_message, fn in expected_messages:
        with pytest.raises(AstParseError) as exc_info:
            parse_function(fn)
        diagnostics = exc_info.value.diagnostics
        if not diagnostics:
            raise AssertionError(f"expected diagnostics for cast variant: {expected_message}")
        if diagnostics[0].message != expected_message:
            raise AssertionError(f"expected cast diagnostic {expected_message!r}, got {diagnostics[0].message!r}")


# AST-015
# 创建者: 金铲铲大作战
# 最后一次更改: 金铲铲大作战
# 最近一次运行测试时间: 2026-03-25 12:01:58 +0800
# 最近一次运行成功时间: 2026-03-25 12:01:58 +0800
# 功能说明: 验证 store helper 的 arity/target 负路径报错口径不变。
# 测试目的: 锁定 _parse_store_like_call 在 store 分支上的非法参数个数与非法 target 诊断。
# 使用示例: pytest -q test/dsl/test_ast.py -k test_parse_function_rejects_invalid_store_helper_variants
# 对应功能实现文件路径: kernel_gen/dsl/ast.py
# 对应 spec 文件路径: spec/dsl/ast.md
# 对应测试文件路径: test/dsl/test_ast.py
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
# 使用示例: pytest -q test/dsl/test_ast.py -k test_parse_function_rejects_invalid_deslice_helper_variants
# 对应功能实现文件路径: kernel_gen/dsl/ast.py
# 对应 spec 文件路径: spec/dsl/ast.md
# 对应测试文件路径: test/dsl/test_ast.py
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


# AST-009
# 创建者: 小李飞刀
# 最后一次更改: 小李飞刀
# 最近一次运行测试时间: 2026-03-18 10:56:41 +0800
# 最近一次运行成功时间: 2026-03-18 10:56:41 +0800
# 功能说明: 验证不支持语法会抛出带诊断的错误。
# 测试目的: 验证不支持语法会抛出带诊断的错误。
# 使用示例: pytest -q test/dsl/test_ast.py -k test_unsupported_syntax_reports_diagnostics
# 对应功能实现文件路径: kernel_gen/dsl/ast.py
# 对应 spec 文件路径: spec/dsl/ast.md
# 对应测试文件路径: test/dsl/test_ast.py
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


# AST-014I
# 创建者: 小李飞刀
# 最后一次更改: 小李飞刀
# 最近一次运行测试时间: 2026-04-06 08:10:00 +0800
# 最近一次运行成功时间: 2026-04-06 08:10:00 +0800
# 功能说明: 验证 `barrier(visibility, scope)` 可解析为 `ArchBarrierAST`。
# 测试目的: 锁定 barrier 只接受关键字形态，且 visibility / scope 字段在 AST 中按 spec 保留。
# 使用示例: pytest -q test/dsl/test_ast.py -k test_parse_function_parses_arch_barrier_statement
# 对应功能实现文件路径: kernel_gen/dsl/ast.py
# 对应 spec 文件路径: spec/dsl/ast.md
# 对应测试文件路径: test/dsl/test_ast.py
def test_parse_function_parses_arch_barrier_statement(monkeypatch: pytest.MonkeyPatch) -> None:
    from kernel_gen.operation.arch import BarrierScope, barrier

    def barrier_kernel() -> None:
        barrier(visibility=[MemorySpace.TSM, MemorySpace.TLM], scope=BarrierScope.BLOCK)

    monkeypatch.setitem(barrier_kernel.__globals__, "barrier", barrier)
    monkeypatch.setitem(barrier_kernel.__globals__, "MemorySpace", MemorySpace)
    monkeypatch.setitem(barrier_kernel.__globals__, "BarrierScope", BarrierScope)

    func_ast = parse_function(barrier_kernel)
    if len(func_ast.body.statements) != 1:
        raise AssertionError("expected barrier kernel to lower to one AST statement")
    stmt = func_ast.body.statements[0]
    if not isinstance(stmt, ArchBarrierAST):
        raise AssertionError("expected barrier kernel to parse into ArchBarrierAST")
    if stmt.visibility != [MemorySpace.TSM, MemorySpace.TLM]:
        raise AssertionError("expected barrier visibility to preserve MemorySpace order")
    if stmt.scope is not BarrierScope.BLOCK:
        raise AssertionError("expected barrier scope to stay BarrierScope.BLOCK")


# AST-014J
# 创建者: 小李飞刀
# 最后一次更改: 小李飞刀
# 最近一次运行测试时间: 2026-04-06 08:10:00 +0800
# 最近一次运行成功时间: 2026-04-06 08:10:00 +0800
# 功能说明: 验证 barrier 对非法 arity / visibility / scope 返回固定诊断。
# 测试目的: 锁定 `Unsupported barrier arity`、`barrier visibility must be non-empty MemorySpace list` 与 `barrier scope must be BarrierScope` 三类错误口径。
# 使用示例: pytest -q test/dsl/test_ast.py -k test_parse_function_rejects_invalid_arch_barrier_variants
# 对应功能实现文件路径: kernel_gen/dsl/ast.py
# 对应 spec 文件路径: spec/dsl/ast.md
# 对应测试文件路径: test/dsl/test_ast.py
def test_parse_function_rejects_invalid_arch_barrier_variants(monkeypatch: pytest.MonkeyPatch) -> None:
    from kernel_gen.operation.arch import BarrierScope, barrier

    def bad_positional() -> None:
        barrier([MemorySpace.TSM, MemorySpace.TLM], scope=BarrierScope.BLOCK)

    def bad_visibility_type() -> None:
        barrier(visibility=(MemorySpace.TSM, MemorySpace.TLM), scope=BarrierScope.BLOCK)

    def bad_visibility_empty() -> None:
        barrier(visibility=[], scope=BarrierScope.BLOCK)

    def bad_scope_type() -> None:
        barrier(visibility=[MemorySpace.TSM, MemorySpace.TLM], scope="block")

    for fn in (bad_positional, bad_visibility_type, bad_visibility_empty, bad_scope_type):
        monkeypatch.setitem(fn.__globals__, "barrier", barrier)
        monkeypatch.setitem(fn.__globals__, "MemorySpace", MemorySpace)
        monkeypatch.setitem(fn.__globals__, "BarrierScope", BarrierScope)

    expected_messages = (
        ("Unsupported barrier arity", bad_positional),
        ("barrier visibility must be non-empty MemorySpace list", bad_visibility_type),
        ("barrier visibility must be non-empty MemorySpace list", bad_visibility_empty),
        ("barrier scope must be BarrierScope", bad_scope_type),
    )
    for expected_message, fn in expected_messages:
        with pytest.raises(AstParseError) as exc_info:
            parse_function(fn)
        diagnostics = exc_info.value.diagnostics
        if not diagnostics:
            raise AssertionError(f"expected diagnostics for barrier variant: {expected_message}")
        if diagnostics[0].message != expected_message:
            raise AssertionError(f"expected barrier diagnostic {expected_message!r}, got {diagnostics[0].message!r}")


# AST-014K
# 创建者: 小李飞刀
# 最后一次更改: 小李飞刀
# 最近一次运行测试时间: 2026-04-06 08:10:00 +0800
# 最近一次运行成功时间: 2026-04-06 08:10:00 +0800
# 功能说明: 验证 `launch_kernel(callee, block, thread, subthread, *args)` 可解析为新版 `ArchLaunchKernelAST`。
# 测试目的: 锁定 callee 从函数对象规整为 symbol ref 名称，且尾部 args 顺序在 AST 中保留。
# 使用示例: pytest -q test/dsl/test_ast.py -k test_parse_function_parses_arch_launch_kernel_with_callee
# 对应功能实现文件路径: kernel_gen/dsl/ast.py
# 对应 spec 文件路径: spec/dsl/ast.md
# 对应测试文件路径: test/dsl/test_ast.py
def test_parse_function_parses_arch_launch_kernel_with_callee(monkeypatch: pytest.MonkeyPatch) -> None:
    from kernel_gen.operation.arch import launch_kernel

    def add_barrier_body(
        lhs: "Tensor[f32, 2, 2]",
        rhs: "Tensor[f32, 2, 2]",
        out: "Tensor[f32, 2, 2]",
    ) -> None:
        return None

    def launch_entry(
        lhs: "Tensor[f32, 2, 2]",
        rhs: "Tensor[f32, 2, 2]",
        out: "Tensor[f32, 2, 2]",
        thread_extent: int,
    ) -> None:
        launch_kernel(add_barrier_body, 1, thread_extent, 2, lhs, rhs, out)

    monkeypatch.setitem(launch_entry.__globals__, "launch_kernel", launch_kernel)
    monkeypatch.setitem(launch_entry.__globals__, "add_barrier_body", add_barrier_body)

    func_ast = parse_function(launch_entry)
    if len(func_ast.body.statements) != 1:
        raise AssertionError("expected launch entry to lower to one AST statement")
    stmt = func_ast.body.statements[0]
    if not isinstance(stmt, ArchLaunchKernelAST):
        raise AssertionError("expected launch entry to parse into ArchLaunchKernelAST")
    if stmt.callee != "add_barrier_body":
        raise AssertionError("expected launch callee to normalize to function symbol name")
    if not isinstance(stmt.block, ConstAST) or stmt.block.value != 1:
        raise AssertionError("expected block extent to stay constant 1")
    if not isinstance(stmt.thread, ScalarArgAST) or stmt.thread.name != "thread_extent":
        raise AssertionError("expected thread extent to stay scalar arg reference")
    if not isinstance(stmt.subthread, ConstAST) or stmt.subthread.value != 2:
        raise AssertionError("expected subthread extent to stay constant 2")
    if [getattr(arg, "name", None) for arg in stmt.args] != ["lhs", "rhs", "out"]:
        raise AssertionError("expected launch args to preserve positional order")


# AST-014L
# 创建者: 小李飞刀
# 最后一次更改: 小李飞刀
# 最近一次运行测试时间: 2026-04-06 08:10:00 +0800
# 最近一次运行成功时间: 2026-04-06 08:10:00 +0800
# 功能说明: 验证 launch_kernel 对非法 callee / arity / extent 返回固定诊断。
# 测试目的: 锁定字符串/属性 callee 禁止、关键字调用禁用与静态 extent 正数约束。
# 使用示例: pytest -q test/dsl/test_ast.py -k test_parse_function_rejects_invalid_arch_launch_kernel_variants
# 对应功能实现文件路径: kernel_gen/dsl/ast.py
# 对应 spec 文件路径: spec/dsl/ast.md
# 对应测试文件路径: test/dsl/test_ast.py
def test_parse_function_rejects_invalid_arch_launch_kernel_variants(monkeypatch: pytest.MonkeyPatch) -> None:
    from kernel_gen.operation.arch import launch_kernel

    def launched_body() -> None:
        return None

    class Holder:
        add_barrier_body = launched_body

    holder = Holder()

    def bad_string_callee() -> None:
        launch_kernel("add_barrier_body", 1, 2, 1)

    def bad_attribute_callee() -> None:
        launch_kernel(holder.add_barrier_body, 1, 2, 1)

    def bad_keyword_call() -> None:
        launch_kernel(launched_body, block=1, thread=2, subthread=1)

    def bad_zero_extent() -> None:
        launch_kernel(launched_body, 0, 2, 1)

    for fn in (bad_string_callee, bad_attribute_callee, bad_keyword_call, bad_zero_extent):
        monkeypatch.setitem(fn.__globals__, "launch_kernel", launch_kernel)
        monkeypatch.setitem(fn.__globals__, "launched_body", launched_body)
        monkeypatch.setitem(fn.__globals__, "holder", holder)

    expected_messages = (
        ("launch_kernel callee must be function symbol reference", bad_string_callee),
        ("launch_kernel callee must be function symbol reference", bad_attribute_callee),
        ("Unsupported launch_kernel arity", bad_keyword_call),
        ("launch_kernel block must be > 0", bad_zero_extent),
    )
    for expected_message, fn in expected_messages:
        with pytest.raises(AstParseError) as exc_info:
            parse_function(fn)
        diagnostics = exc_info.value.diagnostics
        if not diagnostics:
            raise AssertionError(f"expected diagnostics for launch_kernel variant: {expected_message}")
        if diagnostics[0].message != expected_message:
            raise AssertionError(
                f"expected launch_kernel diagnostic {expected_message!r}, got {diagnostics[0].message!r}"
            )
