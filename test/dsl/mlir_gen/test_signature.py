"""mlir_gen signature tests.

创建者: 朽木露琪亚
最后一次更改: 朽木露琪亚

功能说明:
- 覆盖签名推导与符号表达式解析的基础路径。

当前覆盖率信息:
- 当前覆盖率: 未统计（本任务验证未启用 coverage 统计）。
- 达标判定: 待后续补充统计结果。

覆盖率命令:
- pytest -q --cov=kernel_gen.dsl.mlir_gen.signature --cov-branch --cov-report=term-missing test/dsl/mlir_gen/test_signature.py

使用示例:
- pytest -q test/dsl/mlir_gen/test_signature.py

关联文件:
- 功能实现: kernel_gen/dsl/mlir_gen/signature.py
- Spec 文档: spec/dsl/mlir_gen.md
- 测试文件: test/dsl/mlir_gen/test_signature.py
"""

from __future__ import annotations

import importlib
import sys
from pathlib import Path

import pytest
from xdsl.dialects.builtin import ArrayAttr, IntAttr, StringAttr, f16, f32, i1

REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from kernel_gen.dialect.nn import NnMemorySpaceAttr, NnMemoryType
from kernel_gen.dialect.symbol import SymbolValueType
from kernel_gen.dsl.ast import (
    ArchQueryAST,
    BinaryExprAST,
    BlockAST,
    ConstAST,
    DmaAllocAST,
    DmaFlattenAST,
    DmaFreeAST,
    FunctionAST,
    ScalarArgAST,
    SymbolToFloatAST,
    TensorAST,
    TensorAxisAccessAST,
    parse_function,
)
from kernel_gen.dsl.mlir_gen import _build_signature_types
from kernel_gen.dsl.mlir_gen.signature import _parse_symbolic_dim_expr
from kernel_gen.symbol_variable.memory import Memory, MemorySpace
from kernel_gen.symbol_variable.symbol_dim import SymbolDim
from kernel_gen.symbol_variable.type import NumericType

signature_module = importlib.import_module("kernel_gen.dsl.mlir_gen.signature")


def _memory_type(
    shape: list[int | str],
    stride: list[int | str],
    *,
    element_type: object = f32,
) -> NnMemoryType:
    def _dim_attr(value: int | str) -> IntAttr | StringAttr:
        if isinstance(value, int):
            return IntAttr(value)
        return StringAttr(value)

    return NnMemoryType(
        ArrayAttr([_dim_attr(dim) for dim in shape]),
        ArrayAttr([_dim_attr(dim) for dim in stride]),
        element_type,
        NnMemorySpaceAttr.from_name("global"),
    )


# TC-MLIR-GEN-SIG-001
# 创建者: 朽木露琪亚
# 最后一次更改: 朽木露琪亚
# 最近一次运行测试时间: 未运行
# 最近一次运行成功时间: 未运行
# 测试目的: runtime_args 为 SymbolDim 时参数类型必须落在 SymbolValueType。
# 对应功能实现文件路径: kernel_gen/dsl/mlir_gen/signature.py
# 对应 spec 文件路径: spec/dsl/mlir_gen.md
# 示例: pytest -q test/dsl/mlir_gen/test_signature.py -k test_build_signature_types_symbol_dim
def test_build_signature_types_symbol_dim() -> None:
    def kernel(s: "int") -> "int":
        return s

    func_ast = parse_function(kernel)
    arg_types, type_map = _build_signature_types(func_ast, runtime_args=[SymbolDim("S")])
    assert len(arg_types) == 1
    assert isinstance(arg_types[0], SymbolValueType)
    assert any(isinstance(value, SymbolValueType) for value in type_map.values())


# TC-MLIR-GEN-SIG-002
# 创建者: 朽木露琪亚
# 最后一次更改: 朽木露琪亚
# 最近一次运行测试时间: 未运行
# 最近一次运行成功时间: 未运行
# 测试目的: 符号表达式解析应返回可用的 sympy 表达式。
# 对应功能实现文件路径: kernel_gen/dsl/mlir_gen/signature.py
# 对应 spec 文件路径: spec/dsl/mlir_gen.md
# 示例: pytest -q test/dsl/mlir_gen/test_signature.py -k test_parse_symbolic_dim_expr
def test_parse_symbolic_dim_expr() -> None:
    assert _parse_symbolic_dim_expr("M*N") is not None


# TC-MLIR-GEN-SIG-003
# 创建者: 小李飞刀
# 最后一次更改: 小李飞刀
# 功能说明: 覆盖 signature helper 在 mixed dtype 返回、符号 shape 等价与零返回判定上的私有边界。
# 测试目的: 锁定 `_allow_mixed_dtype_return`、`_validate_return_type`、`_flatten_numel_annotation_matches` 与零返回 helper 的公开规则。
# 对应功能实现文件路径: kernel_gen/dsl/mlir_gen/signature.py
# 对应 spec 文件路径: spec/dsl/mlir_gen.md
# 示例: pytest -q test/dsl/mlir_gen/test_signature.py -k test_signature_private_helper_contracts_and_return_edges
def test_signature_private_helper_contracts_and_return_edges() -> None:
    tensor_f16 = TensorAST("lhs", Memory([2, 2], NumericType.Float16), location=None)
    tensor_f32 = TensorAST("rhs", Memory([2, 2], NumericType.Float32), location=None)
    binary_expr = BinaryExprAST("add", tensor_f16, tensor_f32, location=None)
    type_map = {
        signature_module._expr_key(tensor_f16): _memory_type([2, 2], [2, 1], element_type=f16),
        signature_module._expr_key(tensor_f32): _memory_type([2, 2], [2, 1], element_type=f32),
    }
    promoted_type = _memory_type([2, 2], [2, 1], element_type=f32)
    annotated_type = _memory_type([2, 2], [2, 1], element_type=f16)
    assert signature_module._allow_mixed_dtype_return(binary_expr, type_map, promoted_type, annotated_type) is True

    mixed_return_func = FunctionAST(
        "mixed_add",
        inputs=[tensor_f16, tensor_f32],
        outputs=[TensorAST("out", Memory([2, 2], NumericType.Float16), location=None)],
        body=BlockAST([binary_expr]),
        has_explicit_return=True,
        has_return_annotation=True,
    )
    signature_module._validate_return_type(mixed_return_func, promoted_type, binary_expr, type_map)

    assert signature_module._flatten_numel_annotation_matches(_memory_type(["M * N"], [1]), _memory_type(["N*M"], [1])) is True
    assert signature_module._shape_annotation_matches(_memory_type(["M + N"], [1]), _memory_type(["N + M"], [1])) is True
    assert signature_module._shape_annotation_matches(_memory_type([2, 3], [3, 1]), _memory_type([2, 4], [4, 1])) is False

    axis_tensor = TensorAST("value", Memory([4, 8], NumericType.Float32), location=None)
    axis_access = TensorAxisAccessAST(tensor=axis_tensor, kind="shape", axis=ConstAST(0), location=None)
    axis_func = FunctionAST(
        "shape_of",
        inputs=[axis_tensor],
        outputs=[ScalarArgAST("dim", int, location=None)],
        body=BlockAST([axis_access]),
        has_explicit_return=True,
        has_return_annotation=True,
    )
    signature_module._validate_return_type(axis_func, SymbolValueType.from_expr("N"), axis_access, {})

    query_expr = ArchQueryAST(query_name="get_thread_id", location=None)
    query_func = FunctionAST(
        "query",
        inputs=[],
        outputs=[ScalarArgAST("dim", int, location=None)],
        body=BlockAST([query_expr]),
        has_explicit_return=True,
        has_return_annotation=True,
    )
    signature_module._validate_return_type(query_func, SymbolValueType.from_expr("thread_id"), query_expr, {})

    float_input = ScalarArgAST("s", int, is_symbolic=True, location=None)
    float_return = SymbolToFloatAST(source=float_input, location=None)
    float_func = FunctionAST(
        "floatify",
        inputs=[float_input],
        outputs=[ScalarArgAST("f", float, location=None)],
        body=BlockAST([float_return]),
        has_explicit_return=True,
        has_return_annotation=True,
    )
    signature_module._validate_return_type(float_func, f32, float_return, {})

    with pytest.raises(signature_module._LoweringError, match="Unsupported scalar return type"):
        signature_module._validate_return_type(float_func, i1, ConstAST(1), {})

    assert signature_module._function_has_value_return(float_func) is True
    assert signature_module._function_has_value_return(FunctionAST("none", [], [], BlockAST([]), returns_none=True)) is False
    assert signature_module._is_zero_return_statement_expr(DmaFreeAST(value=tensor_f16, location=None)) is True
    assert signature_module._is_zero_return_statement_expr(ConstAST(0)) is False
    assert signature_module._parse_symbolic_dim_expr(" ? ") is None


# TC-MLIR-GEN-SIG-004
# 创建者: 小李飞刀
# 最后一次更改: 小李飞刀
# 功能说明: 覆盖 scalar/runtime 签名推导与 dma.alloc-only 形状/stride 推导边界。
# 测试目的: 锁定 `_is_symbol_scalar_function`、`_build_signature_types`、`_build_dma_alloc_only_result_type` 与 `_resolve_dma_alloc_shape_value` 在 runtime 场景下的收口行为。
# 对应功能实现文件路径: kernel_gen/dsl/mlir_gen/signature.py
# 对应 spec 文件路径: spec/dsl/mlir_gen.md
# 示例: pytest -q test/dsl/mlir_gen/test_signature.py -k test_signature_private_runtime_and_dma_alloc_only_edges
def test_signature_private_runtime_and_dma_alloc_only_edges(monkeypatch: pytest.MonkeyPatch) -> None:
    sym_arg = ScalarArgAST("n", int, is_symbolic=True, location=None)
    scalar_func = FunctionAST(
        "sym",
        [sym_arg],
        [ScalarArgAST("ok", bool, location=None)],
        BlockAST([]),
        has_return_annotation=True,
    )
    assert signature_module._is_symbol_scalar_function(scalar_func) is True
    assert signature_module._is_symbol_scalar_arg(sym_arg, is_symbol_scalar_function=False) is True
    assert signature_module._symbol_expr_from_runtime_arg(SymbolDim("M")) == "M"
    assert signature_module._symbol_expr_from_runtime_arg(7) == "7"
    assert signature_module._symbol_expr_from_runtime_arg(object()) is None

    runtime_symbol_types, runtime_symbol_map = signature_module._build_signature_types(
        scalar_func,
        runtime_args=[SymbolDim("S")],
    )
    assert isinstance(runtime_symbol_types[0], SymbolValueType)
    assert isinstance(runtime_symbol_map[signature_module._expr_key(sym_arg)], SymbolValueType)

    scalar_only = FunctionAST(
        "scalar_only",
        [ScalarArgAST("m", int, location=None)],
        [TensorAST("out", Memory([1], NumericType.Float32), location=None)],
        BlockAST([]),
    )
    with pytest.raises(signature_module._LoweringError, match="At least one tensor input is required"):
        signature_module._build_signature_types(scalar_only)
    with pytest.raises(signature_module._LoweringError, match="runtime_args must align with func_ast inputs"):
        signature_module._build_signature_types(scalar_only, runtime_args=[])
    with pytest.raises(signature_module._LoweringError, match="Unsupported scalar argument type"):
        signature_module._build_signature_types(scalar_func, runtime_args=["bad"])

    alloc_k = ScalarArgAST("k", int, location=None)
    alloc_expr = DmaAllocAST(
        shape=[ConstAST(2), alloc_k],
        dtype=NumericType.Float32,
        space=MemorySpace.GM,
        stride=[alloc_k, ConstAST(1)],
        location=None,
    )
    alloc_func = FunctionAST(
        "alloc_only",
        inputs=[alloc_k],
        outputs=[TensorAST("out", Memory([2, 4], NumericType.Float32), location=None)],
        body=BlockAST([alloc_expr]),
    )
    assert signature_module._is_dma_alloc_only_function(alloc_func) is True
    alloc_result = signature_module._build_dma_alloc_only_result_type(alloc_func, alloc_expr, runtime_args=[4])
    assert isinstance(alloc_result, NnMemoryType)
    assert [dim.data for dim in alloc_result.shape.data] == [2, 4]
    assert signature_module._resolve_dma_alloc_shape_value(alloc_k, {"k": SymbolDim("K")}) == SymbolDim("K")

    dma_alloc_only_types, _ = signature_module._build_signature_types(
        alloc_func,
        runtime_args=[4],
        allow_dma_alloc_only=True,
    )
    assert isinstance(dma_alloc_only_types[0], SymbolValueType)

    bad_alloc = DmaAllocAST(
        shape=[ConstAST(2), alloc_k],
        dtype=NumericType.Float32,
        stride=[ConstAST(1), ConstAST(1)],
        location=None,
    )
    with pytest.raises(signature_module._LoweringError, match="dma.alloc only supports contiguous stride"):
        signature_module._build_dma_alloc_only_result_type(alloc_func, bad_alloc, runtime_args=[4])

    flat_tensor = TensorAST("value", Memory([2, 2], NumericType.Float32), location=None)
    flatten_expr = DmaFlattenAST(source=flat_tensor, location=None)
    flatten_func = FunctionAST(
        "flatten",
        inputs=[flat_tensor],
        outputs=[TensorAST("out", Memory([4], NumericType.Float32), location=None)],
        body=BlockAST([flatten_expr]),
        has_explicit_return=True,
        has_return_annotation=True,
    )
    monkeypatch.setattr(signature_module, "_shape_annotation_matches", lambda *_args: False)
    monkeypatch.setattr(signature_module, "_flatten_numel_annotation_matches", lambda *_args: True)
    signature_module._validate_return_type(flatten_func, _memory_type([4], [1]), flatten_expr, {})


# TC-MLIR-GEN-SIG-005
# 创建者: 小李飞刀
# 最后一次更改: 小李飞刀
# 功能说明: 继续覆盖 signature helper 的剩余 runtime/type/return 错误矩阵。
# 测试目的: 锁定 `_allow_mixed_dtype_return`、`_build_signature_types`、`_build_dma_alloc_only_result_type` 与 `_validate_return_type` 的剩余边界。
# 对应功能实现文件路径: kernel_gen/dsl/mlir_gen/signature.py
# 对应 spec 文件路径: spec/dsl/mlir_gen.md
# 示例: pytest -q test/dsl/mlir_gen/test_signature.py -k test_signature_private_additional_error_matrix
def test_signature_private_additional_error_matrix(monkeypatch: pytest.MonkeyPatch) -> None:
    tensor_f16 = TensorAST("lhs", Memory([2, 2], NumericType.Float16), location=None)
    tensor_f32 = TensorAST("rhs", Memory([2, 2], NumericType.Float32), location=None)
    tensor_f32_b = TensorAST("rhs_b", Memory([2, 2], NumericType.Float32), location=None)
    mismatch_type_map = {
        signature_module._expr_key(tensor_f16): _memory_type([2, 2], [2, 1], element_type=f16),
        signature_module._expr_key(tensor_f32): _memory_type([2, 2], [2, 1], element_type=f32),
        signature_module._expr_key(tensor_f32_b): _memory_type([2, 2], [2, 1], element_type=f32),
    }

    assert signature_module._allow_mixed_dtype_return(
        ConstAST(1),
        mismatch_type_map,
        _memory_type([2, 2], [2, 1], element_type=f32),
        _memory_type([2, 2], [2, 1], element_type=f16),
    ) is False
    assert signature_module._allow_mixed_dtype_return(
        BinaryExprAST("max", tensor_f16, tensor_f32, location=None),
        mismatch_type_map,
        _memory_type([2, 2], [2, 1], element_type=f32),
        _memory_type([2, 2], [2, 1], element_type=f16),
    ) is False
    assert signature_module._allow_mixed_dtype_return(
        BinaryExprAST("add", ConstAST(1), ConstAST(2), location=None),
        mismatch_type_map,
        _memory_type([2, 2], [2, 1], element_type=f32),
        _memory_type([2, 2], [2, 1], element_type=f16),
    ) is False
    assert signature_module._allow_mixed_dtype_return(
        BinaryExprAST("add", tensor_f32, tensor_f32_b, location=None),
        mismatch_type_map,
        _memory_type([2, 2], [2, 1], element_type=f32),
        _memory_type([2, 2], [2, 1], element_type=f16),
    ) is False
    assert signature_module._allow_mixed_dtype_return(
        BinaryExprAST("add", tensor_f16, tensor_f32, location=None),
        mismatch_type_map,
        _memory_type([2, 2], [2, 1], element_type=f32),
        _memory_type([2, 2], [2, 1], element_type=i1),
    ) is False

    monkeypatch.setattr(
        signature_module,
        "_infer_binary_memory_type",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(signature_module._LoweringError("bad", location=None)),
    )
    assert signature_module._allow_mixed_dtype_return(
        BinaryExprAST("add", tensor_f16, tensor_f32, location=None),
        mismatch_type_map,
        _memory_type([2, 2], [2, 1], element_type=f32),
        _memory_type([2, 2], [2, 1], element_type=f16),
    ) is False
    monkeypatch.undo()

    alloc_arg = ScalarArgAST("k", int, location=None)
    alloc_expr_scalar = DmaAllocAST(
        shape=alloc_arg,
        dtype=NumericType.Float32,
        space=MemorySpace.GM,
        stride=ConstAST(1),
        location=None,
    )
    alloc_func = FunctionAST(
        "alloc_scalar",
        inputs=[alloc_arg],
        outputs=[TensorAST("out", Memory([4], NumericType.Float32), location=None)],
        body=BlockAST([alloc_expr_scalar]),
    )
    alloc_only_type = signature_module._build_dma_alloc_only_result_type(alloc_func, alloc_expr_scalar, runtime_args=[4])
    assert [dim.data for dim in alloc_only_type.shape.data] == [4]

    alloc_only_types, _ = signature_module._build_signature_types(
        alloc_func,
        allow_dma_alloc_only=True,
    )
    assert isinstance(alloc_only_types[0], SymbolValueType)

    with pytest.raises(signature_module._LoweringError, match="Unsupported scalar argument type"):
        signature_module._build_signature_types(
            alloc_func,
            runtime_args=[object()],
            allow_dma_alloc_only=True,
        )

    float_input_func = FunctionAST(
        "float_input",
        [ScalarArgAST("f", float, location=None)],
        [],
        BlockAST([ConstAST(1)]),
    )
    with pytest.raises(signature_module._LoweringError, match="Unsupported scalar argument type"):
        signature_module._build_signature_types(float_input_func)

    class _UnsupportedInput:
        location = None

    with pytest.raises(signature_module._LoweringError, match="Unsupported input type"):
        signature_module._build_signature_types(
            FunctionAST("bad_input", [_UnsupportedInput()], [], BlockAST([ConstAST(1)])),
        )

    scalar_ok = FunctionAST(
        "scalar_ok",
        [ScalarArgAST("m", int, location=None)],
        [ScalarArgAST("out", int, location=None)],
        BlockAST([ConstAST(1)]),
    )
    scalar_ok_types, scalar_ok_map = signature_module._build_signature_types(scalar_ok)
    assert isinstance(scalar_ok_types[0], SymbolValueType)
    assert scalar_ok_map

    assert signature_module._parse_symbolic_dim_expr("M +") is None
    assert signature_module._flatten_numel_annotation_matches(_memory_type([4], [1]), _memory_type([4], [1])) is True
    assert signature_module._flatten_numel_annotation_matches(_memory_type(["M +"], [1]), _memory_type(["M"], [1])) is False
    assert signature_module._shape_annotation_matches(_memory_type([2], [1]), _memory_type([2, 1], [1, 1])) is False
    assert signature_module._shape_annotation_matches(_memory_type(["M +"], [1]), _memory_type(["M"], [1])) is False
    assert signature_module._shape_annotation_matches(_memory_type([2], [1]), _memory_type(["2"], ["1"])) is False

    no_output_func = FunctionAST("void", [tensor_f32], [], BlockAST([ConstAST(1)]))
    signature_module._validate_return_type(no_output_func, _memory_type([2, 2], [2, 1]), None, {})

    multi_output_func = FunctionAST(
        "pair",
        [tensor_f32],
        [
            TensorAST("a", Memory([2, 2], NumericType.Float32), location=None),
            TensorAST("b", Memory([2, 2], NumericType.Float32), location=None),
        ],
        BlockAST([tensor_f32]),
        has_explicit_return=True,
        has_return_annotation=True,
    )
    with pytest.raises(signature_module._LoweringError, match="Only single return value is supported"):
        signature_module._validate_return_type(multi_output_func, _memory_type([2, 2], [2, 1]), tensor_f32, {})

    tensor_output_func = FunctionAST(
        "tensor_out",
        [tensor_f32],
        [TensorAST("out", Memory([2, 2], NumericType.Float32), location=None)],
        BlockAST([tensor_f32]),
        has_explicit_return=True,
        has_return_annotation=True,
    )
    with pytest.raises(signature_module._LoweringError, match="Return type does not match annotation"):
        signature_module._validate_return_type(tensor_output_func, signature_module.i32, tensor_f32, {})
    with pytest.raises(signature_module._LoweringError, match="Return type does not match annotation"):
        signature_module._validate_return_type(tensor_output_func, _memory_type([3, 2], [2, 1]), tensor_f32, {})
    with pytest.raises(signature_module._LoweringError, match="Return type does not match annotation"):
        signature_module._validate_return_type(tensor_output_func, _memory_type([2, 2], [2, 1], element_type=f16), tensor_f32, {})

    bool_func = FunctionAST(
        "pred",
        [],
        [ScalarArgAST("pred", bool, location=None)],
        BlockAST([ConstAST(1)]),
        has_explicit_return=True,
        has_return_annotation=True,
    )
    signature_module._validate_return_type(bool_func, i1, ConstAST(1), {})

    symbol_int_input = ScalarArgAST("s", int, is_symbolic=True, location=None)
    symbol_scalar_func = FunctionAST(
        "symbolic",
        [symbol_int_input],
        [ScalarArgAST("out", int, location=None)],
        BlockAST([symbol_int_input]),
        has_explicit_return=True,
        has_return_annotation=True,
    )
    signature_module._validate_return_type(symbol_scalar_func, SymbolValueType.from_expr("s"), symbol_int_input, {})
    with pytest.raises(signature_module._LoweringError, match="Return type does not match annotation"):
        signature_module._validate_return_type(symbol_scalar_func, i1, symbol_int_input, {})

    weird_scalar_func = FunctionAST(
        "weird_scalar",
        [],
        [ScalarArgAST("value", complex, location=None)],
        BlockAST([ConstAST(1)]),
        has_explicit_return=True,
        has_return_annotation=True,
    )
    with pytest.raises(signature_module._LoweringError, match="Unsupported scalar return type"):
        signature_module._validate_return_type(weird_scalar_func, i1, ConstAST(1), {})

    class _UnsupportedOutput:
        location = None

    bad_output_func = FunctionAST(
        "bad_output",
        [],
        [_UnsupportedOutput()],
        BlockAST([ConstAST(1)]),
        has_explicit_return=True,
        has_return_annotation=True,
    )
    with pytest.raises(signature_module._LoweringError, match="Unsupported return annotation type"):
        signature_module._validate_return_type(bad_output_func, i1, ConstAST(1), {})
