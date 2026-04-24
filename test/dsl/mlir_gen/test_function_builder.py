"""mlir_gen function builder tests.

创建者: 朽木露琪亚
最后一次更改: 朽木露琪亚

功能说明:
- 覆盖 build_func_op/build_func_op_from_ast 的运行时参数与基础装配行为。

当前覆盖率信息:
- 当前覆盖率: 未统计（本任务验证未启用 coverage 统计）。
- 达标判定: 待后续补充统计结果。

覆盖率命令:
- pytest -q --cov=kernel_gen.dsl.mlir_gen.function_builder --cov-branch --cov-report=term-missing test/dsl/mlir_gen/test_function_builder.py

使用示例:
- pytest -q test/dsl/mlir_gen/test_function_builder.py

关联文件:
- 功能实现: kernel_gen/dsl/mlir_gen/function_builder.py
- Spec 文档: spec/dsl/mlir_gen.md
- 测试文件: test/dsl/mlir_gen/test_function_builder.py
"""

from __future__ import annotations

import importlib
import sys
from pathlib import Path

import pytest
from xdsl.dialects import func
from xdsl.dialects.builtin import ArrayAttr, FunctionType, IntAttr, StringAttr, i32, i8
from xdsl.ir import Block, Region

REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from kernel_gen.dialect.arch import ArchGetDynamicMemoryOp
from kernel_gen.dialect.nn import NnMemorySpaceAttr, NnMemoryType
from kernel_gen.dialect.symbol import SymbolValueType
from kernel_gen.dsl.ast import (
    BlockAST,
    ConstAST,
    DmaViewAST,
    FunctionAST,
    NnReduceAST,
    ScalarArgAST,
    TensorAST,
    VarAST,
    parse_function,
)
from kernel_gen.dsl.ast.visitor import AstVisitorError
from kernel_gen.dsl.mlir_gen import build_func_op, build_func_op_from_ast
from kernel_gen.operation.nn import reduce_max
from kernel_gen.symbol_variable.memory import Memory
from kernel_gen.symbol_variable.memory import MemorySpace
from kernel_gen.symbol_variable.type import NumericType

function_builder_module = importlib.import_module("kernel_gen.dsl.mlir_gen.function_builder")


def _tensor_arg(shape: list[int]) -> Memory:
    """构造 Memory 测试入参。

    创建者: 朽木露琪亚
    最后一次更改: 朽木露琪亚

    功能说明:
    - 简化 build_func_op_from_ast 的 runtime_args 构造。

    使用示例:
    - arg = _tensor_arg([2, 2])

    关联文件:
    - spec: [spec/dsl/mlir_gen.md](spec/dsl/mlir_gen.md)
    - test: [test/dsl/mlir_gen/test_function_builder.py](test/dsl/mlir_gen/test_function_builder.py)
    - 功能实现: [kernel_gen/dsl/mlir_gen/function_builder.py](kernel_gen/dsl/mlir_gen/function_builder.py)
    """

    return Memory(shape, NumericType.Float32)


def _memory_type(
    shape: list[int | str],
    stride: list[int | str],
    *,
    space: str = "global",
) -> NnMemoryType:
    def _attr(value: int | str) -> IntAttr | StringAttr:
        if isinstance(value, int):
            return IntAttr(value)
        return StringAttr(value)

    return NnMemoryType(
        ArrayAttr([_attr(dim) for dim in shape]),
        ArrayAttr([_attr(dim) for dim in stride]),
        i8,
        NnMemorySpaceAttr.from_name(space),
    )


# TC-MLIR-GEN-FUNC-001
# 创建者: 朽木露琪亚
# 最后一次更改: 朽木露琪亚
# 最近一次运行测试时间: 未运行
# 最近一次运行成功时间: 未运行
# 测试目的: 运行时参数缺失时必须报错。
# 对应功能实现文件路径: kernel_gen/dsl/mlir_gen/function_builder.py
# 对应 spec 文件路径: spec/dsl/mlir_gen.md
# 示例: pytest -q test/dsl/mlir_gen/test_function_builder.py -k test_build_func_op_requires_runtime_args
def test_build_func_op_requires_runtime_args() -> None:
    def kernel(x: "Tensor[f32, 4]") -> "Tensor[f32, 4]":
        return x

    with pytest.raises(AstVisitorError) as excinfo:
        build_func_op(kernel, globals={"X": 1})
    assert "globals/builtins cannot replace function runtime args" in str(excinfo.value)


# TC-MLIR-GEN-FUNC-002
# 创建者: 朽木露琪亚
# 最后一次更改: 朽木露琪亚
# 最近一次运行测试时间: 未运行
# 最近一次运行成功时间: 未运行
# 测试目的: build_func_op_from_ast 可生成 func.FuncOp。
# 对应功能实现文件路径: kernel_gen/dsl/mlir_gen/function_builder.py
# 对应 spec 文件路径: spec/dsl/mlir_gen.md
# 示例: pytest -q test/dsl/mlir_gen/test_function_builder.py -k test_build_func_op_from_ast_builds_func
def test_build_func_op_from_ast_builds_func() -> None:
    def identity(x: "Tensor[f32, 2, 2]") -> "Tensor[f32, 2, 2]":
        return x

    func_ast = parse_function(identity)
    func_op = build_func_op_from_ast(func_ast, runtime_args=[_tensor_arg([2, 2])])
    assert isinstance(func_op, func.FuncOp)
    assert func_op.sym_name.data == "identity"


def test_function_builder_private_helper_edges() -> None:
    tsm_type = _memory_type(["?"], [1], space="tsm")
    local_type = _memory_type(["LM_SIZE"], [1], space="local")
    global_type = _memory_type(["?"], [1], space="global")

    block = Block()
    tsm_op = ArchGetDynamicMemoryOp(NnMemorySpaceAttr.from_name("tsm"), tsm_type)
    local_op = ArchGetDynamicMemoryOp(NnMemorySpaceAttr.from_name("local"), local_type)
    global_op = ArchGetDynamicMemoryOp(NnMemorySpaceAttr.from_name("global"), global_type)
    non_memory_op = ArchGetDynamicMemoryOp(NnMemorySpaceAttr.from_name("tsm"), tsm_type)
    non_memory_op.result._type = i32
    block.add_ops([tsm_op, local_op, global_op, non_memory_op, func.ReturnOp(tsm_op.result)])
    func_op = func.FuncOp("dyn_mem", FunctionType.from_lists([], [tsm_type]), Region(block))

    function_builder_module._rewrite_dynamic_memory_result_types(func_op)

    assert list(tsm_op.result.type.shape.data) == [StringAttr("TSM_SIZE")]
    assert list(local_op.result.type.shape.data) == [StringAttr("LM_SIZE")]
    assert list(global_op.result.type.shape.data) == [StringAttr("?")]
    assert non_memory_op.result.type == i32
    assert list(func_op.function_type.outputs.data[0].shape.data) == [StringAttr("TSM_SIZE")]

    assert function_builder_module._resolve_static_index_list(ConstAST(3), None) == [3]

    ctx = function_builder_module.EmitContext(builder=Block(), symbols={}, types={})
    block_with_args = Block(arg_types=[SymbolValueType.from_expr("M"), i32])
    func_ast = FunctionAST(
        name="seed_aliases",
        inputs=[ScalarArgAST("m", int, is_symbolic=True), ScalarArgAST("n", int)],
        outputs=[],
        body=BlockAST(statements=[ConstAST(0)]),
        returns_none=True,
    )
    function_builder_module._seed_input_symbol_aliases(ctx, func_ast, block_with_args)
    assert ctx.symbols["m"] is block_with_args.args[0]
    assert ctx.symbols["M"] is block_with_args.args[0]
    assert ctx.symbols["n"] is block_with_args.args[1]


def test_function_builder_validates_dma_view_bounds_edges() -> None:
    def _func_ast(
        source: object,
        *,
        offset: object = [ConstAST(0)],
        size: object = [ConstAST(2)],
        stride: object = [ConstAST(1)],
    ) -> FunctionAST:
        return FunctionAST(
            name="view_kernel",
            inputs=[TensorAST("src", object())],
            outputs=[],
            body=BlockAST([DmaViewAST(source=source, offset=offset, size=size, stride=stride)]),
            returns_none=True,
        )

    function_builder_module._maybe_validate_dma_view_bounds(_func_ast(ConstAST(0)), runtime_args=[_tensor_arg([4])])
    function_builder_module._maybe_validate_dma_view_bounds(_func_ast(VarAST("src")), runtime_args=["not-memory"])
    function_builder_module._maybe_validate_dma_view_bounds(
        _func_ast(VarAST("src")),
        runtime_args=[Memory([4], NumericType.Float32, stride=None)],
    )
    function_builder_module._maybe_validate_dma_view_bounds(
        _func_ast(VarAST("src")),
        runtime_args=[Memory(["M"], NumericType.Float32, stride=[1])],
    )
    function_builder_module._maybe_validate_dma_view_bounds(
        _func_ast(VarAST("src")),
        runtime_args=[Memory([4], NumericType.Float32, stride=["S"])],
    )
    function_builder_module._maybe_validate_dma_view_bounds(
        _func_ast(VarAST("src"), offset=[VarAST("m")]),
        runtime_args=[Memory([4], NumericType.Float32, stride=[1]), 1],
    )

    with pytest.raises(ValueError, match="Invalid stride"):
        function_builder_module._maybe_validate_dma_view_bounds(
            _func_ast(VarAST("src"), stride=[ConstAST(0)]),
            runtime_args=[Memory([4], NumericType.Float32, stride=[1])],
        )

    with pytest.raises(ValueError, match="Index out of bounds"):
        function_builder_module._maybe_validate_dma_view_bounds(
            _func_ast(VarAST("src"), offset=[ConstAST(3)], size=[ConstAST(2)]),
            runtime_args=[Memory([4], NumericType.Float32, stride=[1])],
        )


def test_build_func_op_from_ast_error_edges(monkeypatch: pytest.MonkeyPatch) -> None:
    with pytest.raises(AstVisitorError, match="Function return requires explicit return syntax or annotation"):
        build_func_op_from_ast(
            FunctionAST(
                name="missing_return_contract",
                inputs=[],
                outputs=[],
                body=BlockAST([ConstAST(1)]),
                returns_none=False,
            ),
        )

    value_return_ast = FunctionAST(
        name="empty_value_body",
        inputs=[],
        outputs=[ScalarArgAST("out", int)],
        body=BlockAST([ConstAST(1)]),
        returns_none=False,
    )
    monkeypatch.setattr(function_builder_module.AstVisitor, "visit_function", lambda self, func_ast, ctx: None)
    with pytest.raises(AstVisitorError, match="Function body is empty"):
        build_func_op_from_ast(value_return_ast)


def test_build_func_op_from_ast_rejects_reduce_max_axis_out_of_range() -> None:
    def kernel(x: "Tensor[f32, 2, 2]") -> "Tensor[f32, 2]":
        return reduce_max(x, axis=3)

    func_ast = parse_function(kernel)

    with pytest.raises(AstVisitorError, match=r"reduce_max axis must be within \[-2, 1\]"):
        build_func_op_from_ast(func_ast, runtime_args=[_tensor_arg([2, 2])])
