"""emit_c tests.

创建者: 金铲铲大作战
最后一次更改: 小李飞刀

功能说明:
- 覆盖 emit_c 节点级源码片段生成与错误路径。

使用示例:
- pytest -q test/dsl/test_emit_c.py

覆盖率信息:
- 覆盖率命令: coverage run -m pytest -q test/dsl/test_emit_c.py test/dsl/test_gen_kernel.py && coverage report --include=kernel_gen/dsl/emit_c.py,kernel_gen/dsl/gen_kernel.py -m
- 覆盖率结果: emit_c 100%, gen_kernel 100%（2026-03-23 22:45:14 +0800）
- 达标线: 95%

关联文件:
- 功能实现: kernel_gen/dsl/emit_c.py
- Spec 文档: spec/dsl/emit_c.md
- 测试文件: test/dsl/test_emit_c.py
"""

from __future__ import annotations

from pathlib import Path
import sys

import pytest
from xdsl.dialects import arith, func, scf
from xdsl.dialects.builtin import ArrayAttr, DenseIntOrFPElementsAttr, FloatAttr, FunctionType, IndexType, IntAttr, IntegerAttr, ModuleOp, StringAttr, TensorType, f32, i32
from xdsl.ir import Block, Region
from xdsl.irdl import IRDLOperation, irdl_op_definition, result_def

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from kernel_gen.dialect.arch import ArchGetDynamicMemoryOp, ArchGetThreadIdOp, ArchGetThreadNumOp
from kernel_gen.dialect.dma import DmaAllocOp, DmaDesliceOp, DmaFillOp, DmaLoadOp, DmaSliceOp, DmaStoreOp, DmaViewOp
from kernel_gen.dialect.kernel import KernelAddOp
from kernel_gen.dialect.nn import NnAddOp, NnImg2col2dOp, NnMemorySpaceAttr, NnMemoryType
from kernel_gen.dialect.symbol import SymbolAddOp, SymbolForOp, SymbolGetDimOp, SymbolValueType
from kernel_gen.dsl.ast import BlockAST, ConstAST, ForAST, FunctionAST, Img2ColAST, LoadAST, ScalarArgAST, StoreAST, TensorAST, VarAST
from kernel_gen.dsl.emit_c import EmitCContext, EmitCError, emit_c_op, emit_c_value
from kernel_gen.dsl.mlir_gen import build_func_op, build_func_op_from_ast
from kernel_gen.passes.lowering.nn_to_kernel import LowerNnToKernelPass
from kernel_gen.symbol_variable.memory import Memory, MemorySpace, NumericType
from kernel_gen.symbol_variable.symbol_dim import SymbolDim


@irdl_op_definition
class UnsupportedOp(IRDLOperation):
    name = "test.unsupported"
    result = result_def(i32)

    def __init__(self: "UnsupportedOp") -> None:
        super().__init__(result_types=[i32])


def _ctx() -> EmitCContext:
    return EmitCContext(target="cpu")


def _npu_ctx() -> EmitCContext:
    return EmitCContext(target="npu_demo")


def _make_memory_type(
    shape: list[int],
    stride: list[int],
    space: str = "global",
    *,
    element_type: object = i32,
) -> NnMemoryType:
    return NnMemoryType(
        ArrayAttr([IntAttr(dim) for dim in shape]),
        ArrayAttr([IntAttr(dim) for dim in stride]),
        element_type,
        NnMemorySpaceAttr.from_name(space),
    )


def _lower_single_op_func(
    input_types: list[object],
    result_type: object,
    build_ops,
) -> Block:
    """构造单函数 module 并执行 `LowerNnToKernelPass`。

    创建者: 小李飞刀
    最后一次更改: 小李飞刀

    功能说明:
    - 为 `emit_c` 的 pass-after IR 测试提供最小 lowering 包装。
    - 返回被 pass 改写后的 entry block，便于按顺序检查 lowered op。

    使用示例:
    - block = _lower_single_op_func([mem], mem, lambda block: [...])

    关联文件:
    - spec: spec/dsl/emit_c.md
    - test: test/dsl/test_emit_c.py
    - 功能实现: test/dsl/test_emit_c.py
    """

    block = Block(arg_types=input_types)
    ops = build_ops(block)
    for op in ops:
        block.add_op(op)
    block.add_op(func.ReturnOp(ops[-1].results[0]))
    func_type = FunctionType.from_lists(input_types, [result_type])
    func_op = func.FuncOp("main", func_type, Region(block))
    module = ModuleOp([func_op])
    LowerNnToKernelPass().run(module)
    return block


def _lower_built_func(fn: object, *runtime_args: object) -> Block:
    """对 `build_func_op(...)` 生成的 `func.func` 执行 pass 并返回 entry block。

    创建者: 小李飞刀
    最后一次更改: 小李飞刀

    功能说明:
    - 用于 I4 的公开链路 smoke：`build_func_op -> LowerNnToKernelPass -> emit_c`。
    - 返回被 pass 改写后的 entry block，便于继续按 lowered op 发射节点级代码。

    使用示例:
    - block = _lower_built_func(add_kernel, Memory([2, 2], NumericType.Int32))

    关联文件:
    - spec: spec/dsl/emit_c.md
    - test: test/dsl/test_emit_c.py
    - 功能实现: test/dsl/test_emit_c.py
    """

    func_op = build_func_op(fn, *runtime_args)
    module = ModuleOp([func_op])
    LowerNnToKernelPass().run(module)
    return next(op for op in module.ops if isinstance(op, func.FuncOp)).body.block


# EC-001
# 创建者: 金铲铲大作战
# 最后一次更改: 朽木露琪亚
# 最近一次运行测试时间: 2026-04-01 10:43:06 +0800
# 最近一次运行成功时间: 2026-04-01 10:43:06 +0800
# 功能说明: 验证算术 op 可生成赋值语句。
# 测试目的: 验证 emit_c_op 可把 addi 生成为右值赋值语句。
# 使用示例: pytest -q test/dsl/test_emit_c.py -k test_emit_c_op_lowers_arith_add
# 对应功能实现文件路径: kernel_gen/dsl/emit_c.py
# 对应 spec 文件路径: spec/dsl/emit_c.md
# 对应测试文件路径: test/dsl/test_emit_c.py

def test_emit_c_op_lowers_arith_add() -> None:
    block = Block(arg_types=[i32, i32])
    ctx = _ctx()
    ctx.pop_indent()
    ctx.bind_name(block.args[0], "lhs")
    ctx.bind_name(block.args[1], "rhs")
    op = arith.AddiOp(block.args[0], block.args[1])
    sub = arith.SubiOp(block.args[0], block.args[1])

    stmt = emit_c_op(op, ctx)
    sub_stmt = emit_c_op(sub, ctx)
    repeated = emit_c_op(op, ctx)

    assert stmt == "int32_t v0 = (lhs + rhs);"
    assert sub_stmt == "int32_t v1 = (lhs - rhs);"
    assert repeated == "int32_t v0 = v0;"

    class _Allocator:
        def allocate(self: "_Allocator", _value: object) -> str:
            return "named"

    ctx_named = EmitCContext(target="cpu", naming=_Allocator())
    ctx_named.bind_name(block.args[0], "lhs")
    ctx_named.bind_name(block.args[1], "rhs")
    assert emit_c_op(op, ctx_named) == "int32_t named = (lhs + rhs);"

    ctx_callable = EmitCContext(target="cpu", naming=lambda _value: "callable")
    ctx_callable.bind_name(block.args[0], "lhs")
    ctx_callable.bind_name(block.args[1], "rhs")
    assert emit_c_op(op, ctx_callable) == "int32_t callable = (lhs + rhs);"

    ctx_converter = EmitCContext(target="cpu", type_converter=lambda _attr: "custom")
    ctx_converter.bind_name(block.args[0], "lhs")
    ctx_converter.bind_name(block.args[1], "rhs")
    assert emit_c_op(op, ctx_converter) == "custom v0 = (lhs + rhs);"

    class _Converter:
        def convert(self: "_Converter", _attr: object) -> str:
            return "custom2"

    ctx_convert = EmitCContext(target="cpu", type_converter=_Converter())
    ctx_convert.bind_name(block.args[0], "lhs")
    ctx_convert.bind_name(block.args[1], "rhs")
    assert emit_c_op(op, ctx_convert) == "custom2 v0 = (lhs + rhs);"

    ctx_bad_converter = EmitCContext(target="cpu", type_converter=object())
    ctx_bad_converter.bind_name(block.args[0], "lhs")
    ctx_bad_converter.bind_name(block.args[1], "rhs")
    with pytest.raises(EmitCError) as exc_info:
        emit_c_op(op, ctx_bad_converter)
    assert "unsupported type converter" in str(exc_info.value)

    ctx_bad_naming = EmitCContext(target="cpu", naming=object())
    ctx_bad_naming.bind_name(block.args[0], "lhs")
    ctx_bad_naming.bind_name(block.args[1], "rhs")
    with pytest.raises(EmitCError) as exc_info:
        emit_c_op(op, ctx_bad_naming)
    assert "unsupported naming strategy" in str(exc_info.value)

    float_block = Block(arg_types=[f32, f32])
    float_ctx = _ctx()
    float_ctx.bind_name(float_block.args[0], "flhs")
    float_ctx.bind_name(float_block.args[1], "frhs")
    float_add = arith.AddfOp(float_block.args[0], float_block.args[1])
    assert emit_c_op(float_add, float_ctx) == "float v0 = (flhs + frhs);"


# EC-002
# 创建者: 金铲铲大作战
# 最后一次更改: 小李飞刀
# 最近一次运行测试时间: 2026-04-01 10:43:06 +0800
# 最近一次运行成功时间: 2026-04-01 10:43:06 +0800
# 功能说明: 验证比较 value 可生成比较表达式。
# 测试目的: 验证 emit_c_value 可把 cmpi 结果生成为布尔表达式。
# 使用示例: pytest -q test/dsl/test_emit_c.py -k test_emit_c_value_lowers_compare
# 对应功能实现文件路径: kernel_gen/dsl/emit_c.py
# 对应 spec 文件路径: spec/dsl/emit_c.md
# 对应测试文件路径: test/dsl/test_emit_c.py

def test_emit_c_value_lowers_compare() -> None:
    block = Block(arg_types=[i32, i32])
    ctx = _ctx()
    ctx.bind_name(block.args[0], "lhs")
    ctx.bind_name(block.args[1], "rhs")
    op = arith.CmpiOp(block.args[0], block.args[1], "eq")
    literal = arith.ConstantOp(IntegerAttr(7, i32))
    float_literal = arith.ConstantOp(FloatAttr(1.5, f32))

    expr = emit_c_value(op.result, ctx)
    literal_expr = emit_c_value(literal.result, ctx)
    float_expr = emit_c_value(float_literal.result, ctx)
    stmt = emit_c_op(op, ctx)
    ctx_unbound = _ctx()
    arg_expr = emit_c_value(block.args[0], ctx_unbound)

    assert expr == "(lhs == rhs)"
    assert literal_expr == "7"
    assert float_expr == "1.5"
    assert stmt == "bool v0 = (lhs == rhs);"
    assert arg_expr == "arg0"

    bad_literal = arith.ConstantOp(DenseIntOrFPElementsAttr.from_list(TensorType(i32, [2]), [1, 2]))
    with pytest.raises(EmitCError) as exc_info:
        emit_c_value(bad_literal.result, ctx)
    assert "unsupported constant literal" in str(exc_info.value)

    bad_cmp = arith.CmpiOp(block.args[0], block.args[1], "ult")
    with pytest.raises(EmitCError) as exc_info:
        emit_c_value(bad_cmp.result, ctx)
    assert "unsupported comparison predicate" in str(exc_info.value)


# EC-002A
# 创建者: 李白
# 最后一次更改: 李白
# 最近一次运行测试时间: 2026-03-29 09:10:00 +0800
# 最近一次运行成功时间: 2026-03-29 09:10:00 +0800
# 功能说明: 验证未绑定 BlockArgument 默认命名按参数索引回退。
# 测试目的: 避免先访问高位参数时生成连续编号，确保命名稳定为 arg{index}。
# 使用示例: pytest -q test/dsl/test_emit_c.py -k test_emit_c_value_unbound_block_argument_uses_index
# 对应功能实现文件路径: kernel_gen/dsl/emit_c.py
# 对应 spec 文件路径: spec/dsl/emit_c.md
# 对应测试文件路径: test/dsl/test_emit_c.py
def test_emit_c_value_unbound_block_argument_uses_index() -> None:
    block = Block(arg_types=[i32, i32])
    ctx = _ctx()

    second_expr = emit_c_value(block.args[1], ctx)
    first_expr = emit_c_value(block.args[0], ctx)

    assert second_expr == "arg1"
    assert first_expr == "arg0"


# EC-003
# 创建者: 金铲铲大作战
# 最后一次更改: 小李飞刀
# 最近一次运行测试时间: 2026-03-23 22:45:14 +0800
# 最近一次运行成功时间: 2026-03-23 22:45:14 +0800
# 功能说明: 验证 scf.for 可生成目标循环结构。
# 测试目的: 验证 emit_c_op 可拼装 for 循环与循环体语句。
# 使用示例: pytest -q test/dsl/test_emit_c.py -k test_emit_c_op_lowers_scf_for
# 对应功能实现文件路径: kernel_gen/dsl/emit_c.py
# 对应 spec 文件路径: spec/dsl/emit_c.md
# 对应测试文件路径: test/dsl/test_emit_c.py

def test_emit_c_op_lowers_scf_for() -> None:
    ctx = _ctx()
    start = arith.ConstantOp(IntegerAttr(0, IndexType()))
    end = arith.ConstantOp(IntegerAttr(4, IndexType()))
    step = arith.ConstantOp(IntegerAttr(1, IndexType()))
    body = Block(arg_types=[IndexType()])
    add = arith.AddiOp(body.args[0], body.args[0], result_type=IndexType())
    body.add_op(add)
    body.add_op(scf.YieldOp())
    loop = scf.ForOp(start.result, end.result, step.result, [], body)
    ret = func.ReturnOp(add.result)
    empty_return = func.ReturnOp()
    bad_return = func.ReturnOp(add.result, add.result)

    stmt = emit_c_op(loop, ctx)
    return_stmt = emit_c_op(ret, ctx)
    empty_stmt = emit_c_op(empty_return, ctx)

    assert "for (long long i0 = 0; i0 < 4; i0 += 1) {" in stmt
    assert "long long v1 = (i0 + i0);" in stmt
    assert return_stmt == "return v1;"
    assert empty_stmt == ""
    with pytest.raises(EmitCError) as exc_info:
        emit_c_op(bad_return, ctx)
    assert "unsupported return arity" in str(exc_info.value)


# EC-004
# 创建者: 金铲铲大作战
# 最后一次更改: 小李飞刀
# 最近一次运行测试时间: 2026-03-23 22:45:14 +0800
# 最近一次运行成功时间: 2026-03-23 22:45:14 +0800
# 功能说明: 验证访存 op 可生成索引访问代码。
# 测试目的: 验证 unit-tile dma.load/store 可生成索引读写语句。
# 使用示例: pytest -q test/dsl/test_emit_c.py -k test_emit_c_op_lowers_memory_access
# 对应功能实现文件路径: kernel_gen/dsl/emit_c.py
# 对应 spec 文件路径: spec/dsl/emit_c.md
# 对应测试文件路径: test/dsl/test_emit_c.py

def test_emit_c_op_lowers_memory_access() -> None:
    source_type = _make_memory_type([2, 4], [4, 1])
    tile_type = _make_memory_type([1, 1], [1, 1])
    block = Block(arg_types=[source_type, source_type])
    ctx = _ctx()
    ctx.bind_name(block.args[0], "source")
    ctx.bind_name(block.args[1], "target")
    c0 = arith.ConstantOp(IntegerAttr(0, IndexType()))
    c1 = arith.ConstantOp(IntegerAttr(1, IndexType()))
    load = DmaLoadOp(
        block.args[0],
        [c0.result, c1.result],
        [c1.result, c1.result],
        [c1.result, c1.result],
        tile_type,
        NnMemorySpaceAttr.from_name("global"),
    )
    load_stmt = emit_c_op(load, ctx)
    store = DmaStoreOp(
        load.result,
        block.args[1],
        [c0.result, c1.result],
        [c1.result, c1.result],
        [c1.result, c1.result],
    )

    store_stmt = emit_c_op(store, ctx)

    assert load_stmt == "int32_t v0 = source[0][1];"
    assert store_stmt == "target[0][1] = v0;"

    ctx_unbound = _ctx()
    load_unbound = DmaLoadOp(
        block.args[0],
        [c0.result, c1.result],
        [c1.result, c1.result],
        [c1.result, c1.result],
        tile_type,
        NnMemorySpaceAttr.from_name("global"),
    )
    store_unbound = DmaStoreOp(
        load_unbound.result,
        block.args[1],
        [c0.result, c1.result],
        [c1.result, c1.result],
        [c1.result, c1.result],
    )
    assert emit_c_op(store_unbound, ctx_unbound) == "arg1[0][1] = v0;"

    empty_type = _make_memory_type([], [])
    bad_load = DmaLoadOp(
        block.args[0],
        [c0.result, c1.result],
        [c1.result, c1.result],
        [c1.result, c1.result],
        empty_type,
        NnMemorySpaceAttr.from_name("global"),
    )
    with pytest.raises(EmitCError) as exc_info:
        emit_c_op(bad_load, _ctx())
    assert "only unit-tile dma.load is supported" in str(exc_info.value)

    bad_store = DmaStoreOp(
        block.args[0],
        block.args[1],
        [c0.result, c1.result],
        [c1.result, c1.result],
        [c1.result, c1.result],
    )
    with pytest.raises(EmitCError) as exc_info:
        emit_c_op(bad_store, _ctx())
    assert "only unit-tile dma.store source is supported" in str(exc_info.value)

    bad_source = arith.AddiOp(block.args[0], block.args[0])
    bad_source_load = DmaLoadOp(
        bad_source.result,
        [c0.result, c1.result],
        [c1.result, c1.result],
        [c1.result, c1.result],
        tile_type,
        NnMemorySpaceAttr.from_name("global"),
    )
    with pytest.raises(EmitCError) as exc_info:
        emit_c_op(bad_source_load, _ctx())
    assert "invalid dependency" in str(exc_info.value)


# EC-005
# 创建者: 金铲铲大作战
# 最后一次更改: 朽木露琪亚
# 最近一次运行测试时间: 2026-03-23 22:45:14 +0800
# 最近一次运行成功时间: 2026-03-23 22:45:14 +0800
# 功能说明: 验证不支持 op 时抛出带 op 名称的错误。
# 测试目的: 验证 emit_c_op 对未知 op 明确失败。
# 使用示例: pytest -q test/dsl/test_emit_c.py -k test_emit_c_op_rejects_unsupported_op
# 对应功能实现文件路径: kernel_gen/dsl/emit_c.py
# 对应 spec 文件路径: spec/dsl/emit_c.md
# 对应测试文件路径: test/dsl/test_emit_c.py

def test_emit_c_op_rejects_unsupported_op() -> None:
    with pytest.raises(EmitCError) as exc_info:
        emit_c_op(UnsupportedOp(), _ctx())

    assert "test.unsupported" in str(exc_info.value)

    bad_memory = NnMemoryType(
        ArrayAttr([IntAttr(1)]),
        ArrayAttr([IntAttr(1)]),
        TensorType(i32, [2]),
        NnMemorySpaceAttr.from_name("global"),
    )
    op = DmaAllocOp([], bad_memory)
    with pytest.raises(EmitCError) as exc_info:
        emit_c_op(op, _ctx())
    assert "unsupported type" in str(exc_info.value)


# EC-006
# 创建者: 金铲铲大作战
# 最后一次更改: 小李飞刀
# 最近一次运行测试时间: 2026-03-23 22:45:14 +0800
# 最近一次运行成功时间: 2026-03-23 22:45:14 +0800
# 功能说明: 验证依赖非法的 value 生成时报错。
# 测试目的: 验证 emit_c_value 不接受未知依赖来源。
# 使用示例: pytest -q test/dsl/test_emit_c.py -k test_emit_c_value_rejects_invalid_dependency
# 对应功能实现文件路径: kernel_gen/dsl/emit_c.py
# 对应 spec 文件路径: spec/dsl/emit_c.md
# 对应测试文件路径: test/dsl/test_emit_c.py

def test_emit_c_value_rejects_invalid_dependency() -> None:
    with pytest.raises(EmitCError) as exc_info:
        emit_c_value(UnsupportedOp().result, _ctx())

    assert "invalid dependency" in str(exc_info.value)
    assert "test.unsupported" in str(exc_info.value)


# EC-007
# 创建者: jcc你莫辜负
# 最后一次更改: jcc你莫辜负
# 最近一次运行测试时间: 2026-03-28 07:20:00 +0800
# 最近一次运行成功时间: 2026-03-28 07:20:00 +0800
# 功能说明: 验证 symbol.add 在 cpu target 下可生成标量表达式与赋值语句。
# 测试目的: 锁定 emit_c 对 symbol.add 的最小支持范围，保障 symbol 标量返回链路可用。
# 使用示例: pytest -q test/dsl/test_emit_c.py -k test_emit_c_op_lowers_symbol_add
# 对应功能实现文件路径: kernel_gen/dsl/emit_c.py
# 对应 spec 文件路径: spec/dsl/emit_c.md
# 对应测试文件路径: test/dsl/test_emit_c.py
def test_emit_c_op_lowers_symbol_add() -> None:
    lhs_type = SymbolValueType.from_expr("L")
    rhs_type = SymbolValueType.from_expr("R")
    out_type = SymbolValueType.from_expr("L + R")
    block = Block(arg_types=[lhs_type, rhs_type])
    ctx = _ctx()
    ctx.bind_name(block.args[0], "lhs")
    ctx.bind_name(block.args[1], "rhs")
    op = SymbolAddOp(block.args[0], block.args[1], out_type)

    expr = emit_c_value(op.result, ctx)
    stmt = emit_c_op(op, ctx)

    assert expr == "(lhs + rhs)"
    assert stmt == "long long v0 = (lhs + rhs);"


# EC-008
# 创建者: 金铲铲大作战
# 最后一次更改: 金铲铲大作战
# 最近一次运行测试时间: 2026-03-28 04:12:37 +0800
# 最近一次运行成功时间: 2026-03-28 04:12:37 +0800
# 功能说明: 验证非 cpu target 下 symbol.add 必须报错。
# 测试目的: 锁定 emit_c 对 symbol.add 的 target=cpu 约束，避免错误下发。
# 使用示例: pytest -q test/dsl/test_emit_c.py -k test_emit_c_op_rejects_symbol_add_on_non_cpu
# 对应功能实现文件路径: kernel_gen/dsl/emit_c.py
# 对应 spec 文件路径: spec/dsl/emit_c.md
# 对应测试文件路径: test/dsl/test_emit_c.py
def test_emit_c_op_rejects_symbol_add_on_non_cpu() -> None:
    lhs_type = SymbolValueType.from_expr("L")
    rhs_type = SymbolValueType.from_expr("R")
    out_type = SymbolValueType.from_expr("L + R")
    block = Block(arg_types=[lhs_type, rhs_type])
    ctx = EmitCContext(target="cuda")
    ctx.bind_name(block.args[0], "lhs")
    ctx.bind_name(block.args[1], "rhs")
    op = SymbolAddOp(block.args[0], block.args[1], out_type)

    with pytest.raises(EmitCError, match="symbol scalar ops are cpu-only"):
        emit_c_value(op.result, ctx)


# EC-008A
# 创建者: 小李飞刀
# 最后一次更改: 小李飞刀
# 最近一次运行测试时间: 2026-04-02 23:04:42 +0800
# 最近一次运行成功时间: 2026-04-02 23:04:42 +0800
# 功能说明: 验证 `build_func_op -> pass -> emit_c` 的 add 三条 CPU 路径可生成 lowered IR 节点片段。
# 测试目的: 清理 raw `NnAddOp` 节点级直出源码的旧成功口径，锁定公开成功链路来自 pass 后 `kernel.add` / `dma.fill`。
# 使用示例: pytest -q test/dsl/test_emit_c.py -k test_emit_c_op_lowers_build_func_op_nn_add_variants_after_pass
# 对应功能实现文件路径: kernel_gen/dsl/emit_c.py
# 对应 spec 文件路径: spec/dsl/emit_c.md
# 对应测试文件路径: test/dsl/test_emit_c.py
def test_emit_c_op_lowers_build_func_op_nn_add_variants_after_pass() -> None:
    def add_direct(lhs: "Tensor[i32, 2, 3]", rhs: "Tensor[i32, 2, 3]") -> "Tensor[i32, 2, 3]":
        return lhs + rhs

    def add_const_direct(lhs: "Tensor[i32, 2, 3]") -> "Tensor[i32, 2, 3]":
        return lhs + 1

    def add_symbol_direct(lhs: "Tensor[i32, 2, 3]", bias: int) -> "Tensor[i32, 2, 3]":
        return lhs + bias

    pair_block = _lower_built_func(
        add_direct,
        Memory([2, 3], NumericType.Int32),
        Memory([2, 3], NumericType.Int32),
    )
    pair_ctx = _ctx()
    pair_ctx.bind_name(pair_block.args[0], "lhs")
    pair_ctx.bind_name(pair_block.args[1], "rhs")
    pair_add = next(op for op in pair_block.ops if isinstance(op, KernelAddOp))
    assert emit_c_op(pair_add, pair_ctx) == "cpu::add(lhs, rhs, v0);"

    const_block = _lower_built_func(
        add_const_direct,
        Memory([2, 3], NumericType.Int32),
    )
    const_ctx = _ctx()
    const_ctx.bind_name(const_block.args[0], "lhs")
    const_fill = next(op for op in const_block.ops if isinstance(op, DmaFillOp))
    const_add = next(op for op in const_block.ops if isinstance(op, KernelAddOp))
    for op in const_block.ops:
        if isinstance(op, DmaAllocOp):
            emit_c_op(op, const_ctx)
    assert emit_c_op(const_fill, const_ctx) == (
        "for (long long fill0_i = 0; fill0_i < v1.element_count(); ++fill0_i) {\n"
        "    v1.data()[fill0_i] = 1;\n"
        "}"
    )
    assert emit_c_op(const_add, const_ctx) == "cpu::add(lhs, v1, v0);"

    symbol_block = _lower_built_func(
        add_symbol_direct,
        Memory([2, 3], NumericType.Int32),
        SymbolDim("bias"),
    )
    symbol_ctx = _ctx()
    symbol_ctx.bind_name(symbol_block.args[0], "lhs")
    symbol_ctx.bind_name(symbol_block.args[1], "bias")
    symbol_fill = next(op for op in symbol_block.ops if isinstance(op, DmaFillOp))
    symbol_add = next(op for op in symbol_block.ops if isinstance(op, KernelAddOp))
    for op in symbol_block.ops:
        if isinstance(op, DmaAllocOp):
            emit_c_op(op, symbol_ctx)
    assert emit_c_op(symbol_fill, symbol_ctx) == (
        "for (long long fill0_i = 0; fill0_i < v1.element_count(); ++fill0_i) {\n"
        "    v1.data()[fill0_i] = bias;\n"
        "}"
    )
    assert emit_c_op(symbol_add, symbol_ctx) == "cpu::add(lhs, v1, v0);"


# EC-008B
# 创建者: 小李飞刀
# 最后一次更改: 小李飞刀
# 最近一次运行测试时间: 2026-04-02 05:59:07 +0800
# 最近一次运行成功时间: 2026-04-02 05:59:07 +0800
# 功能说明: 验证未预绑定 result、反向 mixed 操作数顺序或非 cpu target 的 nn.add 继续报 unsupported op。
# 测试目的: 防止节点级 nn.add emitter 越界到函数级 result 分配，或错误接受 `const/symbol + memory` 与非 cpu target。
# 使用示例: pytest -q test/dsl/test_emit_c.py -k test_emit_c_op_keeps_nn_add_unsupported_without_prebound_result_or_on_non_cpu
# 对应功能实现文件路径: kernel_gen/dsl/emit_c.py
# 对应 spec 文件路径: spec/dsl/emit_c.md
# 对应测试文件路径: test/dsl/test_emit_c.py
def test_emit_c_op_keeps_nn_add_unsupported_without_prebound_result_or_on_non_cpu() -> None:
    memory_type = _make_memory_type([2, 3], [3, 1])
    space = NnMemorySpaceAttr.from_name("global")
    block = Block(arg_types=[memory_type, memory_type])
    op = NnAddOp(block.args[0], block.args[1], memory_type, space)

    missing_result_ctx = _ctx()
    missing_result_ctx.bind_name(block.args[0], "lhs")
    missing_result_ctx.bind_name(block.args[1], "rhs")
    with pytest.raises(EmitCError, match="nn.add: unsupported op"):
        emit_c_op(op, missing_result_ctx)

    non_cpu_ctx = EmitCContext(target="cuda")
    non_cpu_ctx.bind_name(block.args[0], "lhs")
    non_cpu_ctx.bind_name(block.args[1], "rhs")
    non_cpu_ctx.bind_name(op.result, "out")
    with pytest.raises(EmitCError, match="nn.add: unsupported op"):
        emit_c_op(op, non_cpu_ctx)

    reverse_const_block = Block(arg_types=[memory_type])
    reverse_const_ctx = _ctx()
    reverse_const_value = arith.ConstantOp(IntegerAttr(1, i32))
    reverse_const_op = NnAddOp(reverse_const_value.result, reverse_const_block.args[0], memory_type, space)
    reverse_const_ctx.bind_name(reverse_const_block.args[0], "rhs")
    reverse_const_ctx.bind_name(reverse_const_op.result, "out")
    with pytest.raises(EmitCError, match="nn.add: unsupported op"):
        emit_c_op(reverse_const_op, reverse_const_ctx)

    reverse_symbol_block = Block(arg_types=[SymbolValueType.from_expr("K"), memory_type])
    reverse_symbol_ctx = _ctx()
    reverse_symbol_ctx.bind_name(reverse_symbol_block.args[0], "bias")
    reverse_symbol_ctx.bind_name(reverse_symbol_block.args[1], "rhs")
    reverse_symbol_op = NnAddOp(reverse_symbol_block.args[0], reverse_symbol_block.args[1], memory_type, space)
    reverse_symbol_ctx.bind_name(reverse_symbol_op.result, "out")
    with pytest.raises(EmitCError, match="nn.add: unsupported op"):
        emit_c_op(reverse_symbol_op, reverse_symbol_ctx)


# EC-I3-001
# 创建者: 小李飞刀
# 最后一次更改: 小李飞刀
# 最近一次运行测试时间: 2026-04-02 20:39:00 +0800
# 最近一次运行成功时间: 2026-04-02 20:39:00 +0800
# 功能说明: 验证 emit_c 可消费 pass 后 `symbol.get_dim + dma.alloc + kernel.add` 的 memory+memory lowered IR。
# 测试目的: 锁定 CPU emitter 不再卡在 `symbol.get_dim: unsupported op`，且 `kernel.add` 会收口为 `cpu::add(...)`。
# 使用示例: pytest -q test/dsl/test_emit_c.py -k test_emit_c_op_lowers_passed_memory_add_pipeline
# 对应功能实现文件路径: kernel_gen/dsl/emit_c.py
# 对应 spec 文件路径: spec/dsl/emit_c.md
# 对应测试文件路径: test/dsl/test_emit_c.py
def test_emit_c_op_lowers_passed_memory_add_pipeline() -> None:
    mem = _make_memory_type([2, 2], [2, 1])
    space = NnMemorySpaceAttr.from_name("global")
    block = _lower_single_op_func(
        [mem, mem],
        mem,
        lambda block: [NnAddOp(block.args[0], block.args[1], mem, space)],
    )
    ops = list(block.ops)
    dim0 = next(op for op in ops if isinstance(op, SymbolGetDimOp) and op.axis.data == 0)
    dim1 = next(op for op in ops if isinstance(op, SymbolGetDimOp) and op.axis.data == 1)
    alloc = next(op for op in ops if isinstance(op, DmaAllocOp))
    add = next(op for op in ops if isinstance(op, KernelAddOp))

    ctx = _ctx()
    ctx.bind_name(block.args[0], "lhs")
    ctx.bind_name(block.args[1], "rhs")

    assert emit_c_value(dim0.result, ctx) == "lhs.shape()[0]"
    assert emit_c_value(dim1.result, ctx) == "lhs.shape()[1]"
    assert emit_c_op(dim0, ctx) == ""
    assert emit_c_op(dim1, ctx) == ""
    assert emit_c_op(alloc, ctx) == (
        "long long v0_shape[2] = {lhs.shape()[0], lhs.shape()[1]};\n"
        "long long v0_stride[2] = {2, 1};\n"
        "int32_t v0_buffer[4] = {};\n"
        "Memory<int32_t> v0(v0_buffer, 2, v0_shape, v0_stride, MemoryFormat::Norm, MemorySpace::GM);"
    )
    assert emit_c_op(add, ctx) == "cpu::add(lhs, rhs, v0);"


# EC-I3-002
# 创建者: 小李飞刀
# 最后一次更改: 小李飞刀
# 最近一次运行测试时间: 2026-04-02 20:39:00 +0800
# 最近一次运行成功时间: 2026-04-02 20:39:00 +0800
# 功能说明: 验证 emit_c 可消费 pass 后 `dma.fill + kernel.add` 的 mixed add lowered IR。
# 测试目的: 锁定 `memory+const(i32)` 与 `memory+symbol.int` 在 CPU emitter 中都走真实填充后再参与 `cpu::add(...)`。
# 使用示例: pytest -q test/dsl/test_emit_c.py -k test_emit_c_op_lowers_passed_mixed_add_pipeline_with_dma_fill
# 对应功能实现文件路径: kernel_gen/dsl/emit_c.py
# 对应 spec 文件路径: spec/dsl/emit_c.md
# 对应测试文件路径: test/dsl/test_emit_c.py
def test_emit_c_op_lowers_passed_mixed_add_pipeline_with_dma_fill() -> None:
    mem = _make_memory_type([2, 2], [2, 1])
    space = NnMemorySpaceAttr.from_name("global")

    def _build_const_ops(block: Block) -> list[object]:
        const_op = arith.ConstantOp(IntegerAttr(1, i32))
        return [const_op, NnAddOp(block.args[0], const_op.result, mem, space)]

    const_block = _lower_single_op_func(
        [mem],
        mem,
        _build_const_ops,
    )
    const_ops = list(const_block.ops)
    const_fill = next(op for op in const_ops if isinstance(op, DmaFillOp))
    const_add = next(op for op in const_ops if isinstance(op, KernelAddOp))

    const_ctx = _ctx()
    const_ctx.bind_name(const_block.args[0], "lhs")
    const_alloc_names = [emit_c_op(op, const_ctx) for op in const_ops if isinstance(op, DmaAllocOp)]
    assert len(const_alloc_names) == 2
    assert "lhs.shape()[0]" in const_alloc_names[0]
    assert "lhs.shape()[0]" in const_alloc_names[1]
    assert emit_c_op(const_fill, const_ctx) == (
        "for (long long fill0_i = 0; fill0_i < v1.element_count(); ++fill0_i) {\n"
        "    v1.data()[fill0_i] = 1;\n"
        "}"
    )
    assert emit_c_op(const_add, const_ctx) == "cpu::add(lhs, v1, v0);"

    bias_type = SymbolValueType.from_expr("bias")
    symbol_block = _lower_single_op_func(
        [mem, bias_type],
        mem,
        lambda block: [NnAddOp(block.args[0], block.args[1], mem, space)],
    )
    symbol_ops = list(symbol_block.ops)
    symbol_fill = next(op for op in symbol_ops if isinstance(op, DmaFillOp))
    symbol_add = next(op for op in symbol_ops if isinstance(op, KernelAddOp))

    symbol_ctx = _ctx()
    symbol_ctx.bind_name(symbol_block.args[0], "lhs")
    symbol_ctx.bind_name(symbol_block.args[1], "bias")
    for op in symbol_ops:
        if isinstance(op, DmaAllocOp):
            emit_c_op(op, symbol_ctx)
    assert emit_c_op(symbol_fill, symbol_ctx) == (
        "for (long long fill0_i = 0; fill0_i < v1.element_count(); ++fill0_i) {\n"
        "    v1.data()[fill0_i] = bias;\n"
        "}"
    )
    assert emit_c_op(symbol_add, symbol_ctx) == "cpu::add(lhs, v1, v0);"


# EC-009
# 创建者: 朽木露琪亚
# 最后一次更改: 朽木露琪亚
# 最近一次运行测试时间: 2026-04-01 10:43:06 +0800
# 最近一次运行成功时间: 2026-04-01 10:43:06 +0800
# 功能说明: 验证 emit_c 可生成 dma.alloc/dma.view 的最小 CPU 文本片段。
# 测试目的: 锁定 tile-local buffer 分配与子视图重解释的节点级映射，避免 conv 主线在 alloc/view 处提前失败。
# 使用示例: pytest -q test/dsl/test_emit_c.py -k test_emit_c_op_lowers_dma_alloc_and_view
# 对应功能实现文件路径: kernel_gen/dsl/emit_c.py
# 对应 spec 文件路径: spec/dsl/emit_c.md
# 对应测试文件路径: test/dsl/test_emit_c.py
def test_emit_c_op_lowers_dma_alloc_and_view() -> None:
    alloc_type = _make_memory_type([2, 3], [3, 1], space="shared", element_type=f32)
    alloc = DmaAllocOp([], alloc_type)

    alloc_stmt = emit_c_op(alloc, _ctx())

    assert alloc_stmt == (
        "long long v0_shape[2] = {2, 3};\n"
        "long long v0_stride[2] = {3, 1};\n"
        "float v0_buffer[6] = {};\n"
        "Memory<float> v0(v0_buffer, 2, v0_shape, v0_stride, MemoryFormat::Norm, MemorySpace::SM);"
    )

    dyn_shape0 = SymbolValueType.from_expr("N")
    dyn_shape1 = SymbolValueType.from_expr("3")
    dyn_block = Block(arg_types=[dyn_shape0, dyn_shape1])
    dyn_ctx = _ctx()
    dyn_ctx.bind_name(dyn_block.args[0], "N")
    dyn_ctx.bind_name(dyn_block.args[1], "c3")
    dyn_alloc_type = NnMemoryType(
        ArrayAttr([StringAttr("N"), IntAttr(3)]),
        ArrayAttr([IntAttr(3), IntAttr(1)]),
        f32,
        NnMemorySpaceAttr.from_name("shared"),
    )
    dyn_alloc = DmaAllocOp([dyn_block.args[0], dyn_block.args[1]], dyn_alloc_type)
    with pytest.raises(EmitCError, match="dynamic shape backing is unsupported"):
        emit_c_op(dyn_alloc, dyn_ctx)

    source_type = _make_memory_type([2, 2], [2, 1], element_type=f32)
    view_type = _make_memory_type([2, 2], [1, 1], element_type=f32)
    block = Block(arg_types=[source_type])
    ctx = _ctx()
    ctx.bind_name(block.args[0], "source")
    c0 = arith.ConstantOp(IntegerAttr(0, i32))
    c1 = arith.ConstantOp(IntegerAttr(1, i32))
    c2 = arith.ConstantOp(IntegerAttr(2, i32))
    view = DmaViewOp(
        block.args[0],
        [c0.result, c0.result],
        [c2.result, c2.result],
        [c1.result, c1.result],
        view_type,
    )

    view_stmt = emit_c_op(view, ctx)

    assert view_stmt == (
        "long long view_offset0 = (0 * source.stride()[0]) + (0 * source.stride()[1]);\n"
        "long long v0_shape[2] = {2, 2};\n"
        "long long v0_stride[2] = {1, 1};\n"
        "Memory<float> v0(const_cast<float*>(source.data()) + view_offset0, 2, v0_shape, v0_stride, source.format(), source.space());"
    )


# EC-010
# 创建者: 朽木露琪亚
# 最后一次更改: 朽木露琪亚
# 最近一次运行测试时间: 2026-04-01 10:43:06 +0800
# 最近一次运行成功时间: 2026-04-01 10:43:06 +0800
# 功能说明: 验证 emit_c 可生成 symbol.for + dma.alloc + dma.slice + nn.img2col2d + dma.deslice 的真实链路片段。
# 测试目的: 锁定 conv_cpu_tiled_v1 P10 的最小节点级闭环，确保 img2col2d 与 DMA 协同路径在 CPU emitter 可落到稳定文本。
# 使用示例: pytest -q test/dsl/test_emit_c.py -k test_emit_c_op_lowers_img2col2d_dma_loop_pipeline
# 对应功能实现文件路径: kernel_gen/dsl/emit_c.py
# 对应 spec 文件路径: spec/dsl/emit_c.md
# 对应测试文件路径: test/dsl/test_emit_c.py
def test_emit_c_op_lowers_img2col2d_dma_loop_pipeline() -> None:
    input_memory = Memory([1, 1, 4, 4], NumericType.Float32, space=MemorySpace.GM)
    output_memory = Memory([1, 4, 9], NumericType.Float32, space=MemorySpace.GM)
    input_tensor = TensorAST(name="x", memory=input_memory, location=None)
    output_tensor = TensorAST(name="y", memory=output_memory, location=None)
    start = ScalarArgAST(name="start", value_type=int, is_symbolic=True, location=None)
    end = ScalarArgAST(name="end", value_type=int, is_symbolic=True, location=None)
    step = ScalarArgAST(name="step", value_type=int, is_symbolic=True, location=None)
    loop_var = VarAST(name="i", location=None)
    slice_expr = LoadAST(
        tensor=input_tensor,
        offset=[loop_var, ConstAST(0), ConstAST(0), ConstAST(0)],
        stride=None,
        sizes=[ConstAST(1), ConstAST(1), ConstAST(4), ConstAST(4)],
        space=MemorySpace.LM,
        kind="slice",
        location=None,
    )
    img2col_expr = Img2ColAST(
        kind="img2col2d",
        args=[slice_expr],
        kwargs={"kh": ConstAST(2), "kw": ConstAST(2)},
        location=None,
    )
    store_expr = StoreAST(
        tensor=output_tensor,
        offset=[loop_var, ConstAST(0), ConstAST(0)],
        stride=None,
        value=img2col_expr,
        kind="deslice",
        location=None,
    )
    loop = ForAST(var=loop_var, start=start, end=end, step=step, body=BlockAST([store_expr]), location=None)
    func_ast = FunctionAST(
        name="img2col_loop",
        inputs=[input_tensor, output_tensor, start, end, step],
        outputs=[],
        body=BlockAST([loop]),
    )

    func_op = build_func_op_from_ast(func_ast)
    loop_op = next(op for op in func_op.body.block.ops if isinstance(op, SymbolForOp))
    ctx = _ctx()
    ctx.bind_name(func_op.args[0], "input")
    ctx.bind_name(func_op.args[1], "output")
    ctx.bind_name(func_op.args[2], "start")
    ctx.bind_name(func_op.args[3], "end")
    ctx.bind_name(func_op.args[4], "step")

    stmt = emit_c_op(loop_op, ctx)

    assert "for (long long i0 = start; i0 < end; i0 += step) {" in stmt
    assert "float v1_buffer[16] = {};" in stmt
    assert "Memory<float> v1(v1_buffer, 4, v1_shape, v1_stride, MemoryFormat::Norm, MemorySpace::LM);" in stmt
    assert "v1.at(dma0_dst_indices) = input.at(dma0_src_indices);" in stmt
    assert "float v2_buffer[36] = {};" in stmt
    assert "Memory<float> v2(v2_buffer, 3, v2_shape, v2_stride, MemoryFormat::Norm, MemorySpace::LM);" in stmt
    assert "cpu::img2col2d(v1, v2, 2, 2, 1, 1, 1, 1, 0, 0, 0, 0);" in stmt
    assert "output.at(dma1_dst_indices) = v2.at(dma1_src_indices);" in stmt
    assert "slice(" not in stmt
    assert "deslice(" not in stmt
    assert "nullptr" not in stmt


# EC-011
# 创建者: 朽木露琪亚
# 最后一次更改: 朽木露琪亚
# 最近一次运行测试时间: 2026-04-01 10:43:06 +0800
# 最近一次运行成功时间: 2026-04-01 10:43:06 +0800
# 功能说明: 验证重复 dma.slice/dma.deslice 发射时辅助变量名保持唯一。
# 测试目的: 防止同一作用域内重复生成同名索引缓冲区导致编译失败。
# 使用示例: pytest -q test/dsl/test_emit_c.py -k test_emit_c_op_assigns_unique_helper_names_for_repeated_dma_slice_and_deslice
# 对应功能实现文件路径: kernel_gen/dsl/emit_c.py
# 对应 spec 文件路径: spec/dsl/emit_c.md
# 对应测试文件路径: test/dsl/test_emit_c.py
def test_emit_c_op_assigns_unique_helper_names_for_repeated_dma_slice_and_deslice() -> None:
    memory_type = _make_memory_type([2, 2], [2, 1], element_type=f32)
    block = Block(arg_types=[memory_type, memory_type])
    ctx = _ctx()
    ctx.bind_name(block.args[0], "source")
    ctx.bind_name(block.args[1], "target")
    c0 = arith.ConstantOp(IntegerAttr(0, i32))
    c1 = arith.ConstantOp(IntegerAttr(1, i32))
    c2 = arith.ConstantOp(IntegerAttr(2, i32))
    slice0 = DmaSliceOp(
        block.args[1],
        block.args[0],
        [c0.result, c0.result],
        [c2.result, c2.result],
        [c1.result, c1.result],
    )
    slice1 = DmaSliceOp(
        block.args[1],
        block.args[0],
        [c0.result, c0.result],
        [c2.result, c2.result],
        [c1.result, c1.result],
    )
    deslice0 = DmaDesliceOp(
        block.args[0],
        block.args[1],
        [c0.result, c0.result],
        [c2.result, c2.result],
        [c1.result, c1.result],
        memory_type,
    )
    deslice1 = DmaDesliceOp(
        block.args[0],
        block.args[1],
        [c0.result, c0.result],
        [c2.result, c2.result],
        [c1.result, c1.result],
        memory_type,
    )

    slice_stmt0 = emit_c_op(slice0, ctx)
    slice_stmt1 = emit_c_op(slice1, ctx)
    deslice_stmt0 = emit_c_op(deslice0, ctx)
    deslice_stmt1 = emit_c_op(deslice1, ctx)

    assert "dma0_src_indices" in slice_stmt0
    assert "dma1_src_indices" in slice_stmt1
    assert "dma0_src_indices" not in slice_stmt1
    assert "dma2_src_indices" in deslice_stmt0
    assert "dma3_src_indices" in deslice_stmt1
    assert "dma2_src_indices" not in deslice_stmt1


# EC-017
# 创建者: jcc你莫辜负
# 最后一次更改: jcc你莫辜负
# 最近一次运行测试时间: 2026-04-02 00:00:00 +0800
# 最近一次运行成功时间: 2026-04-02 00:00:00 +0800
# 功能说明: 验证 npu_demo 下 thread 查询节点发射为 ctx.thread_id/thread_num。
# 测试目的: 锁定 target=npu_demo 的 KernelContext 查询文本，避免回退到其他 helper 或 launch 语义。
# 使用示例: pytest -q test/dsl/test_emit_c.py -k test_emit_c_lowers_npu_demo_kernel_context_queries
# 对应功能实现文件路径: kernel_gen/dsl/emit_c.py
# 对应 spec 文件路径: spec/dsl/emit_c.md
# 对应测试文件路径: test/dsl/test_emit_c.py
def test_emit_c_lowers_npu_demo_kernel_context_queries() -> None:
    ctx = _npu_ctx()
    tid = ArchGetThreadIdOp()
    tnum = ArchGetThreadNumOp()
    ctx.bind_name(tid.result, "tid")
    ctx.bind_name(tnum.result, "tnum")

    tid_stmt = emit_c_op(tid, ctx)
    tnum_stmt = emit_c_op(tnum, ctx)

    assert tid_stmt == "long long tid = ctx.thread_id();"
    assert tnum_stmt == "long long tnum = ctx.thread_num();"
    assert "launch" not in tid_stmt
    assert "barrier" not in tnum_stmt


# EC-018
# 创建者: jcc你莫辜负
# 最后一次更改: jcc你莫辜负
# 最近一次运行测试时间: 2026-04-02 00:00:00 +0800
# 最近一次运行成功时间: 2026-04-02 00:00:00 +0800
# 功能说明: 验证 npu_demo 下 dynamic memory 查询发射为 ctx.get_dynamic_memory<T>(MemorySpace::TSM/TLM)。
# 测试目的: 锁定 target=npu_demo 的 TSM/TLM 动态片上内存入口文本，避免回退到 load/store/malloc。
# 使用示例: pytest -q test/dsl/test_emit_c.py -k test_emit_c_lowers_npu_demo_dynamic_memory_access
# 对应功能实现文件路径: kernel_gen/dsl/emit_c.py
# 对应 spec 文件路径: spec/dsl/emit_c.md
# 对应测试文件路径: test/dsl/test_emit_c.py
def test_emit_c_lowers_npu_demo_dynamic_memory_access() -> None:
    ctx = _npu_ctx()
    tsm_type = _make_memory_type([16], [1], space="tsm", element_type=f32)
    tlm_type = _make_memory_type([16], [1], space="tlm", element_type=f32)
    tsm = ArchGetDynamicMemoryOp(NnMemorySpaceAttr.from_name("tsm"), tsm_type)
    tlm = ArchGetDynamicMemoryOp(NnMemorySpaceAttr.from_name("tlm"), tlm_type)
    ctx.bind_name(tsm.result, "tsm")
    ctx.bind_name(tlm.result, "tlm")

    tsm_stmt = emit_c_op(tsm, ctx)
    tlm_stmt = emit_c_op(tlm, ctx)

    assert tsm_stmt == "Memory<float> tsm = ctx.get_dynamic_memory<float>(MemorySpace::TSM);"
    assert tlm_stmt == "Memory<float> tlm = ctx.get_dynamic_memory<float>(MemorySpace::TLM);"
    assert "load<" not in tsm_stmt
    assert "store<" not in tlm_stmt


# EC-019
# 创建者: jcc你莫辜负
# 最后一次更改: jcc你莫辜负
# 最近一次运行测试时间: 2026-04-02 00:00:00 +0800
# 最近一次运行成功时间: 2026-04-02 00:00:00 +0800
# 功能说明: 验证 npu_demo 下 view/slice/deslice/add 管线可发射稳定节点级文本。
# 测试目的: 锁定 target=npu_demo 的 helper 形态，确保不回退到 .view<T>()、load/store、launch/barrier 或 arch.launch_kernel。
# 使用示例: pytest -q test/dsl/test_emit_c.py -k test_emit_c_lowers_npu_demo_slice_deslice_add_pipeline
# 对应功能实现文件路径: kernel_gen/dsl/emit_c.py
# 对应 spec 文件路径: spec/dsl/emit_c.md
# 对应测试文件路径: test/dsl/test_emit_c.py
def test_emit_c_lowers_npu_demo_slice_deslice_add_pipeline() -> None:
    mem_type = _make_memory_type([16], [1], space="global", element_type=f32)
    tsm_type = _make_memory_type([16], [1], space="tsm", element_type=f32)
    tlm_type = _make_memory_type([16], [1], space="tlm", element_type=f32)
    block = Block(arg_types=[mem_type, mem_type])
    ctx = _npu_ctx()
    ctx.bind_name(block.args[0], "source")
    ctx.bind_name(block.args[1], "out")

    zero = arith.ConstantOp(IntegerAttr(0, i32))
    size = arith.ConstantOp(IntegerAttr(16, i32))
    stride = arith.ConstantOp(IntegerAttr(1, i32))
    tid = ArchGetThreadIdOp()
    tnum = ArchGetThreadNumOp()
    tsm = ArchGetDynamicMemoryOp(NnMemorySpaceAttr.from_name("tsm"), tsm_type)
    tlm = ArchGetDynamicMemoryOp(NnMemorySpaceAttr.from_name("tlm"), tlm_type)
    src_view = DmaViewOp(block.args[0], [tid.result], [size.result], [stride.result], mem_type)
    work_tile_view = DmaViewOp(tsm.result, [zero.result], [size.result], [stride.result], tsm_type)
    out_tile_view = DmaViewOp(tlm.result, [zero.result], [size.result], [stride.result], tlm_type)
    slice_op = DmaSliceOp(work_tile_view.result, src_view.result, [zero.result], [size.result], [stride.result])
    add_op = NnAddOp(work_tile_view.result, work_tile_view.result, tlm_type, NnMemorySpaceAttr.from_name("tlm"))
    deslice_op = DmaDesliceOp(add_op.result, block.args[1], [tid.result], [size.result], [stride.result], mem_type)

    ctx.bind_name(tid.result, "tid")
    ctx.bind_name(tnum.result, "tnum")
    ctx.bind_name(tsm.result, "tsm")
    ctx.bind_name(tlm.result, "tlm")
    ctx.bind_name(src_view.result, "src_view")
    ctx.bind_name(work_tile_view.result, "work_tile")
    ctx.bind_name(out_tile_view.result, "out_tile")
    ctx.bind_name(add_op.result, "out_tile")

    stmt = "\n".join(
        [
            emit_c_op(tid, ctx),
            emit_c_op(tnum, ctx),
            emit_c_op(tsm, ctx),
            emit_c_op(tlm, ctx),
            emit_c_op(src_view, ctx),
            emit_c_op(work_tile_view, ctx),
            emit_c_op(out_tile_view, ctx),
            emit_c_op(slice_op, ctx),
            emit_c_op(add_op, ctx),
            emit_c_op(deslice_op, ctx),
        ]
    )

    assert "long long tid = ctx.thread_id();" in stmt
    assert "long long tnum = ctx.thread_num();" in stmt
    assert "Memory<float> tsm = ctx.get_dynamic_memory<float>(MemorySpace::TSM);" in stmt
    assert "Memory<float> tlm = ctx.get_dynamic_memory<float>(MemorySpace::TLM);" in stmt
    assert "auto src_view = view(source, tid, 16, 1);" in stmt
    assert "auto work_tile = view(tsm, 0, 16, 1);" in stmt
    assert "auto out_tile = view(tlm, 0, 16, 1);" in stmt
    assert "slice(work_tile, src_view, 0, 16, 1);" in stmt
    assert "add(work_tile, work_tile, out_tile);" in stmt
    assert "deslice(out_tile, out, tid, 16, 1);" in stmt
    assert ".view<" not in stmt
    assert "load<" not in stmt
    assert "store<" not in stmt
    assert "launch" not in stmt
    assert "barrier" not in stmt
    assert "arch.launch_kernel" not in stmt
