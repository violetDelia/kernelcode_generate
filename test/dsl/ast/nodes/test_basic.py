"""DSL AST basic node tests.


功能说明:
- 覆盖 `kernel_gen.dsl.ast.nodes.basic` 的基础节点字段、block 结构与输入迭代。
- 测试结构对应 `spec/dsl/ast/nodes/basic.md` 与 `kernel_gen/dsl/ast/nodes/basic.py`。

使用示例:
- pytest -q test/dsl/ast/nodes/test_basic.py

关联文件:
- 功能实现: kernel_gen/dsl/ast/nodes/basic.py
- Spec 文档: spec/dsl/ast/nodes/basic.md
- 测试文件: test/dsl/ast/nodes/test_basic.py
"""

from __future__ import annotations

import importlib

import pytest
from xdsl.context import Context
from xdsl.ir import Block, Operation, SSAValue

from kernel_gen.core.error import KernelCodeError
from kernel_gen.dialect.dma import DmaAllocOp
from kernel_gen.dialect.nn import NnMemoryType
from kernel_gen.dsl.ast.nodes.attr import BoolTypeAttrAST, FloatTypeAttrAST, IntTypeAttrAST, MemorySpaceAttrAST, PythonObjectAttrAST, SourceLocation
from kernel_gen.dsl.ast.nodes.basic import (
    BlockAST,
    BoolValueAST,
    BoundExprAST,
    CallAST,
    DSLNode,
    FunctionAST,
    MemoryAST,
    ModuleAST,
    ReturnAST,
    ValueAST,
)
from kernel_gen.dsl.ast.nodes.symbol import ConstValueAST, SymbolAddAST, SymbolDimAST, SymbolListAST
from kernel_gen.symbol_variable.memory import Memory, MemorySpace
from kernel_gen.symbol_variable.symbol_dim import SymbolDim
from kernel_gen.symbol_variable.type import Farmat, NumericType


class DetachedConstValueAST(ValueAST):
    """测试公开 ValueAST 发射合同时返回未挂接常量 op 的节点。"""

    def __init__(self, value: int) -> None:
        self.value = value

    def emit_mlir(self, ctx: Context, block: Block | None = None) -> Operation:
        """返回未挂接常量 op，验证容器节点按公开合同接入。"""

        _ = block
        emitted = ConstValueAST(self.value).emit_mlir(ctx, None)
        assert isinstance(emitted, Operation)
        return emitted


class RawEmitValueAST(ValueAST):
    """测试公开 ValueAST 发射合同时返回非法结果的节点。"""

    def __init__(self, value: int | str | None) -> None:
        self.value = value

    def emit_mlir(self, ctx: Context, block: Block | None = None) -> int | str | None:
        """返回原始值，用于验证公开 emit 错误边界。"""

        _ = (ctx, block)
        return self.value


def test_basic_nodes_construct_expr_block() -> None:
    """构造表达式节点并挂载到 BlockAST。"""

    loc = SourceLocation(line=3, column=0)
    lhs = SymbolDimAST(SymbolDim("x"), location=loc)
    rhs = ConstValueAST(1, location=loc)
    expr = SymbolAddAST(lhs, rhs, location=loc)
    bound = BoundExprAST(name="tmp", target=SymbolDimAST("tmp", location=loc), value=expr, location=loc)
    block = BlockAST(statements=[bound], location=loc)

    assert block.statements[0] is bound
    assert bound.value is expr
    assert expr.rhs is rhs


def test_function_ast_iter_inputs_returns_declared_inputs() -> None:
    """FunctionAST.iter_inputs() 按声明顺序返回 tensor / scalar 输入。"""

    tensor = MemoryAST(
        "x",
        SymbolListAST([SymbolDim("N")]),
        SymbolListAST([1]),
        FloatTypeAttrAST(NumericType.Float32),
        MemorySpaceAttrAST(MemorySpace.GM),
    )
    scalar = SymbolDimAST("n")
    func_ast = FunctionAST("kernel", [tensor, scalar], [], BlockAST([]))

    assert list(func_ast.iter_inputs()) == [tensor, scalar]
    assert func_ast.name == "kernel"
    assert func_ast.body.statements == []


def test_function_ast_constructs_inputs_from_runtime_args() -> None:
    """FunctionAST.input_from_runtime_arg() 统一 runtime 参数到输入 AST 的构造。"""

    memory = Memory([SymbolDim("N")], NumericType.Float32, space=MemorySpace.TSM)
    memory_input = FunctionAST.input_from_runtime_arg("x", memory)
    symbol_input = FunctionAST.input_from_runtime_arg("n", SymbolDim("N"))
    int_input = FunctionAST.input_from_runtime_arg("tile", 8)
    float_input = FunctionAST.input_from_runtime_arg("scale", 1.5)
    bool_input = FunctionAST.input_from_runtime_arg("flag", True)

    assert isinstance(memory_input, MemoryAST)
    assert memory_input.memory == memory
    assert isinstance(symbol_input, SymbolDimAST)
    assert symbol_input.result_symbol() == SymbolDim("N")
    assert isinstance(int_input, SymbolDimAST)
    assert int_input.result_symbol() == 8
    assert isinstance(float_input, ConstValueAST)
    assert float_input.raw_value == 1.5
    assert isinstance(bool_input, BoolValueAST)
    assert bool_input.raw_value is True


def test_function_ast_constructs_inputs_from_bound_values() -> None:
    """FunctionAST.input_from_bound_value() 统一 caller 侧 DSL 值到 callee 输入 AST 的构造。"""

    source = MemoryAST(
        "tile",
        SymbolListAST([4]),
        SymbolListAST([1]),
        FloatTypeAttrAST(NumericType.Float32),
        MemorySpaceAttrAST(MemorySpace.TSM),
    )
    bound_memory = FunctionAST.input_from_bound_value("x", source)
    bound_symbol = FunctionAST.input_from_bound_value("n", SymbolDimAST("tile", runtime_symbol=SymbolDim("TILE")))
    bound_bool = FunctionAST.input_from_bound_value("flag", BoolValueAST(False))
    bound_const = FunctionAST.input_from_bound_value("scale", ConstValueAST(2.0))

    assert isinstance(bound_memory, MemoryAST)
    assert bound_memory.name == "x"
    assert bound_memory.memory == source.memory
    assert isinstance(bound_symbol, SymbolDimAST)
    assert bound_symbol.name == "n"
    assert bound_symbol.result_symbol() == SymbolDim("TILE")
    assert isinstance(bound_bool, BoolValueAST)
    assert bound_bool.raw_value is False
    assert isinstance(bound_const, ConstValueAST)
    assert bound_const.raw_value == 2.0


def test_value_result_semantics_are_owned_by_nodes() -> None:
    """ValueAST 子类通过公开 result_* 入口暴露解析期语义。"""

    runtime_symbol = SymbolDim("TILE")
    symbol = SymbolDimAST("step", runtime_symbol=runtime_symbol)
    const = ConstValueAST(4)
    shape = SymbolListAST([symbol, const])
    memory = MemoryAST(
        "x",
        shape,
        SymbolListAST([runtime_symbol, 1]),
        FloatTypeAttrAST(NumericType.Float32),
        MemorySpaceAttrAST(MemorySpace.GM),
    )

    assert symbol.name == "step"
    assert symbol.result_symbol() is runtime_symbol
    assert const.result_symbol() == 4
    assert const.result_scalar() == 4
    assert shape.result_symbols() == [runtime_symbol, 4]
    assert memory.result_memory() == memory.memory
    assert memory.binding_value() == memory.memory
    assert isinstance(memory.bind_target("alias", SourceLocation(line=8, column=2)), MemoryAST)
    assert isinstance(symbol.bind_target("tile", SourceLocation(line=9, column=2)), SymbolDimAST)
    assert isinstance(BoolValueAST(True).bind_target("flag", SourceLocation(line=10, column=2)), BoolValueAST)


def test_value_defaults_and_bind_target_public_edges() -> None:
    """ValueAST 默认结果语义与 bind_target 边界保持公开稳定。"""

    value = ValueAST()
    loc = SourceLocation(line=12, column=4)

    assert value.result_memory() is None
    assert value.result_symbol() is None
    assert value.result_scalar() is None
    assert value.binding_value() is None
    assert value.bind_target("same", loc) is value
    assert isinstance(ConstValueAST(3).bind_target("tile", loc), SymbolDimAST)
    assert isinstance(ConstValueAST(1.5).bind_target("scale", loc), ConstValueAST)

    with pytest.raises(NotImplementedError, match="DSLNode.emit_mlir not implemented"):
        DSLNode().emit_mlir(Context(), None)


def test_memory_ast_builds_mlir_type_from_runtime_memory() -> None:
    """MemoryAST.type_from_memory() 是 Memory -> NnMemoryType 的统一入口。"""

    memory = MemoryAST(
        "x",
        SymbolListAST([2, 4]),
        SymbolListAST([4, 1]),
        FloatTypeAttrAST(NumericType.Float32),
        MemorySpaceAttrAST(MemorySpace.TSM),
    )
    memory_type = MemoryAST.type_from_memory(Context(), memory.memory)

    assert isinstance(memory_type, NnMemoryType)
    assert str(memory_type) == "!nn.memory<[#symbol.expr<2>, #symbol.expr<4>], [#symbol.expr<4>, #symbol.expr<1>], f32, #nn.space<tsm>>"

    divided_memory = Memory([SymbolDim("M") // 2, 4], NumericType.Float32, space=MemorySpace.TSM)
    divided_type = MemoryAST.type_from_memory(Context(), divided_memory)
    assert str(divided_type) == "!nn.memory<[#symbol.expr<M floordiv 2>, #symbol.expr<4>], [#symbol.expr<4>, #symbol.expr<1>], f32, #nn.space<tsm>>"


def test_memory_ast_type_from_memory_names_anonymous_shape_stride_conflict() -> None:
    """MemoryAST.type_from_memory() 会规避匿名 shape/stride 同轴 `?` 组合。"""

    memory = Memory(
        ["?", "?", "?"],
        NumericType.Float32,
        space=MemorySpace.TSM,
    )
    memory_type = MemoryAST.type_from_memory(Context(), memory)

    assert isinstance(memory_type, NnMemoryType)
    assert str(memory_type) == (
        "!nn.memory<[#symbol.expr<runtime_dim_0>, #symbol.expr<runtime_dim_1>, #symbol.expr<runtime_dim_2>], "
        "[#symbol.expr<runtime_dim_1*runtime_dim_2>, #symbol.expr<runtime_dim_2>, #symbol.expr<1>], f32, #nn.space<tsm>>"
    )
    assert "?" not in str(memory_type)


def test_memory_ast_public_dtype_space_and_binding_edges() -> None:
    """MemoryAST 公开 dtype/space 映射、字段归一和 SSA 绑定查找保持稳定。"""

    ctx = Context()
    dtype_cases = [
        (NumericType.Bool, BoolTypeAttrAST),
        (NumericType.Int8, IntTypeAttrAST),
        (NumericType.Int16, IntTypeAttrAST),
        (NumericType.Int32, IntTypeAttrAST),
        (NumericType.Int64, IntTypeAttrAST),
        (NumericType.Uint8, IntTypeAttrAST),
        (NumericType.Uint16, IntTypeAttrAST),
        (NumericType.Uint32, IntTypeAttrAST),
        (NumericType.Uint64, IntTypeAttrAST),
        (NumericType.Float16, FloatTypeAttrAST),
        (NumericType.BFloat16, FloatTypeAttrAST),
        (NumericType.Float32, FloatTypeAttrAST),
        (NumericType.Float64, FloatTypeAttrAST),
    ]

    for dtype, attr_type in dtype_cases:
        dtype_attr = MemoryAST.dtype_attr_from_numeric_type(dtype)

        assert isinstance(dtype_attr, attr_type)
        assert MemoryAST.numeric_type_from_dtype_attr(dtype_attr) is dtype

    normalized = MemoryAST(
        "x",
        [SymbolAddAST(ConstValueAST(1), ConstValueAST(1)), SymbolDim("N")],
        [SymbolAddAST(ConstValueAST(2), ConstValueAST(2)), 1],
        FloatTypeAttrAST(NumericType.Float32),
        MemorySpace.GM,
        format="not-a-format",
    )
    memory_value = normalized.memory

    assert isinstance(normalized.shape, SymbolListAST)
    assert isinstance(normalized.stride, SymbolListAST)
    assert isinstance(normalized.space, MemorySpaceAttrAST)
    assert isinstance(normalized.format, PythonObjectAttrAST)
    assert memory_value.format is Farmat.Norm

    block = Block(arg_types=[normalized.to_mlir_type(ctx)])
    block.args[0].name_hint = "x"
    assert normalized.emit_mlir(ctx, block) is block.args[0]

    result_type = normalized.to_mlir_type(ctx)
    alloc = DmaAllocOp([], result_type)
    block.add_op(alloc)
    alloc.results[0].name_hint = "tmp"
    assert MemoryAST.from_memory("tmp", normalized.memory).emit_mlir(ctx, block) is alloc.results[0]

    with pytest.raises(KernelCodeError, match="Unsupported memory dtype"):
        MemoryAST.dtype_attr_from_numeric_type("bad")
    with pytest.raises(KernelCodeError, match="Unsupported memory dtype"):
        MemoryAST.numeric_type_from_dtype_attr(IntTypeAttrAST(7))
    with pytest.raises(KernelCodeError, match="Unbound memory value"):
        MemoryAST.from_memory("missing", normalized.memory).emit_mlir(ctx, Block())


def test_basic_emit_mlir_public_block_bound_return_and_bool_edges() -> None:
    """BlockAST/BoundExprAST/ReturnAST/BoolValueAST 通过公开 emit_mlir 协作。"""

    ctx = Context()
    block = Block()

    assert isinstance(BoolValueAST(False).emit_mlir(ctx, None), Operation)
    assert isinstance(BoolValueAST(True).emit_mlir(ctx, block), SSAValue)

    detached_bound = BoundExprAST("detached", SymbolDimAST("detached"), DetachedConstValueAST(4))
    detached_op = detached_bound.emit_mlir(ctx, block)
    assert isinstance(detached_op, Operation)
    assert detached_op.results[0].name_hint == "detached"

    ssa_bound = BoundExprAST("ssa", SymbolDimAST("ssa"), SymbolDimAST(5))
    ssa_value = ssa_bound.emit_mlir(ctx, block)
    assert isinstance(ssa_value, SSAValue)
    assert ssa_value.name_hint == "ssa"

    returned = ReturnAST([DetachedConstValueAST(1), SymbolDimAST(6)]).emit_mlir(ctx, block)
    assert isinstance(returned, tuple)
    assert len(returned) == 2

    last_value = BlockAST([DetachedConstValueAST(7), SymbolDimAST(8)]).emit_mlir(ctx, Block())
    assert isinstance(last_value, SSAValue)

    with pytest.raises(KernelCodeError, match="return values must be ValueAST"):
        ReturnAST([BlockAST([])])
    with pytest.raises(KernelCodeError, match="return value must lower to SSA value"):
        ReturnAST(RawEmitValueAST("bad")).emit_mlir(ctx, Block())


def test_function_and_module_emit_public_input_and_return_edges() -> None:
    """FunctionAST/ModuleAST 发射公开函数输入、返回和模块包装。"""

    ctx = Context()
    memory = MemoryAST.from_memory("x", Memory([2], NumericType.Float32, space=MemorySpace.GM))
    typed_inputs = [
        memory,
        SymbolDimAST("tile", runtime_symbol=4),
        BoolValueAST(True),
        ConstValueAST(1.25),
    ]
    typed_function = FunctionAST(
        "typed_kernel",
        typed_inputs,
        [],
        BlockAST([]),
        source="def typed_kernel(): ...",
        py_ast="py-ast",
        diagnostics=("diag",),
        has_explicit_return=False,
        returns_none=True,
        runtime_args=(1, "arg"),
    )
    typed_op = typed_function.emit_mlir(ctx, None)

    assert typed_op.name == "func.func"
    assert all(isinstance(arg, PythonObjectAttrAST) for arg in typed_function.runtime_args)

    return_function = FunctionAST(
        "return_symbol",
        [SymbolDimAST("n", runtime_symbol=SymbolDim("N"))],
        [],
        BlockAST([ReturnAST(SymbolDimAST("n"))]),
        has_explicit_return=True,
        returns_none=False,
    )
    return_op = return_function.emit_mlir(ctx, None)
    module_op = ModuleAST([return_function], runtime_args=(SymbolDim("N"),), source_fn="return_symbol").emit_mlir(ctx, None)

    assert return_op.name == "func.func"
    assert module_op.name == "builtin.module"

    with pytest.raises(KernelCodeError, match="NnMemoryType runtime argument is unsupported"):
        FunctionAST.input_from_runtime_arg("x", memory.to_mlir_type(ctx))
    with pytest.raises(KernelCodeError, match="Missing runtime argument"):
        FunctionAST.input_from_runtime_arg("x", object())
    with pytest.raises(KernelCodeError, match="Unsupported Python callee argument"):
        FunctionAST.input_from_bound_value("tmp", DetachedConstValueAST(1))


def test_call_ast_constructs_from_parsed_callee() -> None:
    """CallAST 只允许构造无返回 Python callee 语句调用。"""

    scalar = SymbolDimAST("n")
    callee = FunctionAST(
        "helper",
        [scalar],
        [],
        BlockAST([]),
        returns_none=True,
        runtime_args=(SymbolDim("N"),),
    )
    call = CallAST(callee, [scalar])

    assert call.callee is callee
    assert call.args == [scalar]


def test_call_ast_rejects_callee_return_value() -> None:
    """CallAST 不推导 callee 返回类型，显式返回值直接失败。"""

    scalar = SymbolDimAST("n")
    callee = FunctionAST(
        "helper",
        [scalar],
        [],
        BlockAST([scalar]),
        has_explicit_return=True,
        returns_none=False,
        runtime_args=(SymbolDim("N"),),
    )

    with pytest.raises(KernelCodeError, match="Python callee return value is unsupported"):
        CallAST(callee, [scalar])


def test_call_ast_emit_public_argument_and_error_edges() -> None:
    """CallAST 通过公开 ValueAST 参数发射 func.call 并校验错误边界。"""

    ctx = Context()
    block = Block()
    scalar = SymbolDimAST("n")
    callee = FunctionAST("helper", [scalar], [], BlockAST([]), returns_none=True)
    call = CallAST(callee, [DetachedConstValueAST(3)])

    assert call.emit_mlir(ctx, block) is None
    assert block.last_op is not None
    assert block.last_op.name == "func.call"

    with pytest.raises(KernelCodeError, match="CallAST callee must be FunctionAST"):
        CallAST("helper", [])
    with pytest.raises(KernelCodeError, match="Python callee arity mismatch"):
        CallAST(callee, [])
    with pytest.raises(KernelCodeError, match="Python callee arguments must lower to SSA values"):
        CallAST(callee, [RawEmitValueAST(None)]).emit_mlir(ctx, Block())


def test_return_ast_accepts_multiple_values() -> None:
    """ReturnAST 承接 0/1/N 个返回值，不再把函数返回压成最后一个表达式。"""

    lhs = SymbolDimAST("lhs")
    rhs = SymbolDimAST("rhs")
    empty_return = ReturnAST()
    single_return = ReturnAST(lhs)
    multi_return = ReturnAST([lhs, rhs])

    assert empty_return.values == ()
    assert single_return.values == (lhs,)
    assert multi_return.values == (lhs, rhs)


def test_basic_module_does_not_define_legacy_nodes() -> None:
    """basic.py 不再保留旧宽泛节点定义。"""

    basic = importlib.import_module("kernel_gen.dsl.ast.nodes.basic")

    for name in (
        "TensorAST",
        "ScalarArgAST",
        "PtrArgAST",
        "VarAST",
        "ConstAST",
        "BinaryExprAST",
        "CompareExprAST",
        "SymbolAddAST",
        "SymbolDimAST",
        "SymbolListAST",
        "IfAST",
    ):
        assert not hasattr(basic, name)
