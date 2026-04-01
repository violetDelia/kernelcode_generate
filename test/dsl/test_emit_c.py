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
from xdsl.dialects.builtin import ArrayAttr, DenseIntOrFPElementsAttr, FloatAttr, IndexType, IntAttr, IntegerAttr, StringAttr, TensorType, f32, i32
from xdsl.ir import Block
from xdsl.irdl import IRDLOperation, irdl_op_definition, result_def

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from kernel_gen.dialect.dma import DmaAllocOp, DmaDesliceOp, DmaLoadOp, DmaSliceOp, DmaStoreOp, DmaViewOp
from kernel_gen.dialect.nn import NnAddOp, NnImg2col2dOp, NnMemorySpaceAttr, NnMemoryType
from kernel_gen.dialect.symbol import SymbolAddOp, SymbolForOp, SymbolValueType
from kernel_gen.dsl.ast import BlockAST, ConstAST, ForAST, FunctionAST, Img2ColAST, LoadAST, ScalarArgAST, StoreAST, TensorAST, VarAST
from kernel_gen.dsl.emit_c import EmitCContext, EmitCError, emit_c_op, emit_c_value
from kernel_gen.dsl.mlir_gen import build_func_op_from_ast
from kernel_gen.symbol_variable.memory import Memory, MemorySpace, NumericType


@irdl_op_definition
class UnsupportedOp(IRDLOperation):
    name = "test.unsupported"
    result = result_def(i32)

    def __init__(self: "UnsupportedOp") -> None:
        super().__init__(result_types=[i32])


def _ctx() -> EmitCContext:
    return EmitCContext(target="cpu")


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
# 最近一次运行测试时间: 2026-04-02 05:59:07 +0800
# 最近一次运行成功时间: 2026-04-02 05:59:07 +0800
# 功能说明: 验证预绑定 result 的 nn.add 可在 cpu target 下生成 cpu::add 调用。
# 测试目的: 锁定 nn.add 的 memory+memory、memory+const(i32)、memory+symbol.int 三条节点级 emit_c 收口路径，且 const 锚点固定为 `cpu::add(lhs, 1, out);`。
# 使用示例: pytest -q test/dsl/test_emit_c.py -k test_emit_c_op_lowers_prebound_nn_add_variants_to_cpu_add
# 对应功能实现文件路径: kernel_gen/dsl/emit_c.py
# 对应 spec 文件路径: spec/dsl/emit_c.md
# 对应测试文件路径: test/dsl/test_emit_c.py
def test_emit_c_op_lowers_prebound_nn_add_variants_to_cpu_add() -> None:
    memory_type = _make_memory_type([2, 3], [3, 1])
    space = NnMemorySpaceAttr.from_name("global")

    pair_block = Block(arg_types=[memory_type, memory_type])
    pair_ctx = _ctx()
    pair_ctx.bind_name(pair_block.args[0], "lhs")
    pair_ctx.bind_name(pair_block.args[1], "rhs")
    pair_add = NnAddOp(pair_block.args[0], pair_block.args[1], memory_type, space)
    pair_ctx.bind_name(pair_add.result, "out")
    assert emit_c_op(pair_add, pair_ctx) == "cpu::add(lhs, rhs, out);"

    const_block = Block(arg_types=[memory_type])
    const_ctx = _ctx()
    const_ctx.bind_name(const_block.args[0], "lhs")
    const_value = arith.ConstantOp(IntegerAttr(1, i32))
    const_add = NnAddOp(const_block.args[0], const_value.result, memory_type, space)
    const_ctx.bind_name(const_add.result, "out")
    assert emit_c_op(const_add, const_ctx) == "cpu::add(lhs, 1, out);"

    symbol_block = Block(arg_types=[memory_type, SymbolValueType.from_expr("K")])
    symbol_ctx = _ctx()
    symbol_ctx.bind_name(symbol_block.args[0], "lhs")
    symbol_ctx.bind_name(symbol_block.args[1], "bias")
    symbol_add = NnAddOp(symbol_block.args[0], symbol_block.args[1], memory_type, space)
    symbol_ctx.bind_name(symbol_add.result, "out")
    assert emit_c_op(symbol_add, symbol_ctx) == "cpu::add(lhs, bias, out);"


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
