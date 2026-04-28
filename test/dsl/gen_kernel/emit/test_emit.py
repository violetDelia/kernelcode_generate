"""emit_c tests.

创建者: 金铲铲大作战
最后一次更改: 朽木露琪亚

功能说明:
- 覆盖 emit_c 节点级源码片段生成与错误路径。

使用示例:
- pytest -q test/dsl/gen_kernel/emit/test_emit.py

覆盖率信息:
- 覆盖率命令: coverage run -m pytest -q test/dsl/gen_kernel/emit/test_emit.py test/dsl/gen_kernel/test_gen_kernel.py && coverage report --include=kernel_gen/dsl/gen_kernel/emit/__init__.py,kernel_gen/dsl/gen_kernel/gen_kernel.py -m
- 覆盖率结果: emit_c 100%, gen_kernel 100%（2026-03-23 22:45:14 +0800）
- 达标线: 95%

关联文件:
- 功能实现: kernel_gen/dsl/gen_kernel/emit/__init__.py
- Spec 文档: spec/dsl/gen_kernel/emit.md
- 测试文件: test/dsl/gen_kernel/emit/test_emit.py
"""

from __future__ import annotations

from pathlib import Path
import importlib
import re
import sys

import pytest
from xdsl.dialects import arith, func, scf
from xdsl.dialects.builtin import ArrayAttr, BFloat16Type, DenseIntOrFPElementsAttr, FloatAttr, Float16Type, FunctionType, IndexType, IntAttr, IntegerAttr, ModuleOp, StringAttr, TensorType, f16, f32, f64, i1, i32
from xdsl.ir import Block, Region
from xdsl.irdl import IRDLOperation, irdl_op_definition, result_def

REPO_ROOT = Path(__file__).resolve().parents[4]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from kernel_gen.dialect.arch import ArchGetDynamicMemoryOp, ArchGetThreadIdOp, ArchGetThreadNumOp
from kernel_gen.dialect.dma import DmaAllocOp, DmaBroadcastOp, DmaCastOp, DmaCopyOp, DmaDesliceOp, DmaFillOp, DmaFreeOp, DmaLoadOp, DmaReshapeOp, DmaSliceOp, DmaStoreOp, DmaTransposeOp, DmaViewOp
from kernel_gen.dialect.kernel import (
    KernelBinaryElewiseOp,
    KernelExpOp,
    KernelImg2col1dOp,
    KernelImg2col2dOp,
    KernelMatmulOp,
    KernelReduceMinOp,
    KernelReduceOp,
    KernelSelectOp,
)
from kernel_gen.dialect.nn import NnAddOp, NnImg2col2dOp, NnMemorySpaceAttr, NnMemoryType
from kernel_gen.dialect.symbol import SymbolAddOp, SymbolCastOp, SymbolConstOp, SymbolEqOp, SymbolForOp, SymbolGetDimOp, SymbolGetStrideOp, SymbolIterType, SymbolToFloatOp, SymbolToIntOp, SymbolValueType
from kernel_gen.dialect.tuner import TunerCostOp
from kernel_gen.dsl.ast import BlockAST, ConstAST, ForAST, FunctionAST, Img2ColAST, LoadAST, ScalarArgAST, StoreAST, TensorAST, VarAST
from kernel_gen.dsl.gen_kernel import EmitCContext, EmitCError, emit_c, emit_c_op, emit_c_value, gen_kernel
from kernel_gen.dsl.mlir_gen import build_func_op, build_func_op_from_ast
from kernel_gen.operation.dma import alloc, deslice, slice
from kernel_gen.operation.nn import matmul
from kernel_gen.operation.scf import loop
from kernel_gen.passes.lowering.nn_lowering import NnLoweringPass
from kernel_gen.symbol_variable.memory import Memory, MemorySpace, NumericType
from kernel_gen.symbol_variable.symbol_dim import SymbolDim

emit_c_package = importlib.import_module("kernel_gen.dsl.gen_kernel.emit")
emit_c_register = importlib.import_module("kernel_gen.dsl.gen_kernel.emit.register")


@irdl_op_definition
class UnsupportedOp(IRDLOperation):
    name = "test.unsupported"
    result = result_def(i32)

    def __init__(self: "UnsupportedOp") -> None:
        super().__init__(result_types=[i32])


def _ctx() -> EmitCContext:
    return EmitCContext(config={"target": "cpu"})


def _npu_ctx() -> EmitCContext:
    return EmitCContext(config={"target": "npu_demo"})


def test_emit_c_public_entry_matches_gen_kernel_for_empty_func() -> None:
    block = Block(arg_types=[])
    block.add_op(func.ReturnOp())
    func_type = FunctionType.from_lists([], [])
    func_op = func.FuncOp("empty_kernel", func_type, Region(block))

    assert emit_c(func_op, _ctx()) == gen_kernel(func_op, _ctx())


# EC-001A
# 创建者: 小李飞刀
# 最后一次更改: 小李飞刀
# 最近一次运行测试时间: 2026-04-21 00:00:00 +0800
# 最近一次运行成功时间: 2026-04-21 00:00:00 +0800
# 功能说明: 验证 emit_c 的 func / module 入口保持当前公开黑盒合同。
# 测试目的: 锁定 `emit_c(...)` 对单函数 `func.func` 与单函数 `builtin.module` 给出一致源码，不依赖内部 emitter helper。
# 使用示例: pytest -q test/dsl/gen_kernel/emit/test_emit.py -k test_emit_c_public_entry_lowers_func_and_single_func_module_consistently
# 对应功能实现文件路径: kernel_gen/dsl/gen_kernel/emit/__init__.py
# 对应 spec 文件路径: spec/dsl/gen_kernel/emit.md
# 对应测试文件路径: test/dsl/gen_kernel/emit/test_emit.py
def test_emit_c_public_entry_lowers_func_and_single_func_module_consistently() -> None:
    block = Block(arg_types=[])
    block.add_op(func.ReturnOp())
    func_type = FunctionType.from_lists([], [])
    func_op = func.FuncOp("empty_kernel", func_type, Region(block))
    module = ModuleOp([func_op.clone()])

    func_source = emit_c(func_op, _ctx())
    module_source = emit_c(module, _ctx())

    assert func_source == gen_kernel(func_op, _ctx())
    assert module_source == func_source
    assert "void empty_kernel(" in func_source


def test_emit_c_package_registers_common_op_and_value_types() -> None:
    assert callable(emit_c_package.emit_c_op)
    assert callable(emit_c_package.emit_c_value)
    alloc_type = _make_memory_type([4], [1])
    alloc_op = DmaAllocOp([], alloc_type)
    assert emit_c_package.emit_c_op(alloc_op, _ctx())

    block = Block(arg_types=[alloc_type, alloc_type, alloc_type])
    kernel_add = KernelBinaryElewiseOp(
        block.args[0],
        block.args[1],
        block.args[2],
        kind="add",
        space=NnMemorySpaceAttr.from_name("global"),
    )
    assert emit_c_register.dispatch_op(kernel_add, _npu_ctx()) is not None

    symbol_const = SymbolConstOp(4)
    assert emit_c_register.dispatch_value(symbol_const.result, _npu_ctx()) is not None
    assert emit_c_register.dispatch_value(ArchGetThreadIdOp().result, _npu_ctx()) is not None


def test_emit_c_context_type_helpers_delegate_to_context_converter() -> None:
    mem_type = _make_memory_type([2], [1])
    space = NnMemorySpaceAttr.from_name("global")
    calls: list[object] = []

    def _converter(value: object) -> str:
        calls.append(value)
        return "ttc"

    ctx = EmitCContext(config={"target": "cpu", "type_converter": _converter})

    assert ctx.dispatch_attr(space) == "GM"
    assert ctx.dispatch_attr(mem_type) == "GM"
    assert ctx.dispatch_attr("global") == "GM"
    assert ctx.dispatch_type(mem_type) == "ttc"
    assert calls == [mem_type]


def test_emit_c_context_type_helpers_dispatch_npu_demo_type_and_space_registry() -> None:
    mem_type = _make_memory_type([2], [1], space="tsm")
    ctx = _npu_ctx()

    assert ctx.dispatch_attr(NnMemorySpaceAttr.from_name("tlm2")) == "TLM2"
    assert ctx.dispatch_attr("tsm") == "TSM"
    assert ctx.dispatch_attr(mem_type) == "TSM"
    assert ctx.dispatch_type(SymbolValueType.from_expr("N")) == "S_INT"
    assert ctx.dispatch_type(mem_type) == "Memory<TSM, int32_t>"


def test_emit_c_context_accepts_target_keyword_and_rejects_conflicts() -> None:
    target_ctx = EmitCContext(target="npu_demo")
    same_target_ctx = EmitCContext(target="cpu", config={"target": "cpu"})

    assert target_ctx.config["target"] == "npu_demo"
    assert same_target_ctx.config["target"] == "cpu"

    with pytest.raises(EmitCError, match=r"target conflicts with config\['target'\]"):
        EmitCContext(target="cpu", config={"target": "npu_demo"})


def test_emit_c_package_value_fast_paths_and_legacy_kernel_add_rejects() -> None:
    block = Block(arg_types=[i32, i32, i32])
    ctx = _ctx()
    for name, arg in zip(("lhs", "rhs", "out"), block.args, strict=True):
        ctx.bind_name(arg, name)

    legacy_add = UnsupportedOp.create(operands=[block.args[0], block.args[1], block.args[2]], result_types=[i32])
    legacy_add.name = "builtin.unregistered"
    legacy_add.attributes["op_name__"] = StringAttr("kernel.add")
    with pytest.raises(EmitCError, match="unsupported op"):
        emit_c_package.emit_c_op(legacy_add, ctx)

    bad_target_ctx = _npu_ctx()
    for name, arg in zip(("lhs", "rhs", "out"), block.args, strict=True):
        bad_target_ctx.bind_name(arg, name)
    with pytest.raises(EmitCError, match="unsupported op"):
        emit_c_package.emit_c_op(legacy_add, bad_target_ctx)

    value_ctx = _ctx()
    value_ctx.bind_name(block.args[0], "bound")
    assert emit_c_package.emit_c_value(block.args[0], value_ctx) == "bound"
    assert emit_c_package.emit_c(block.args[0], value_ctx) == "bound"


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
    """构造单函数 module 并执行 `NnLoweringPass`。

    创建者: 小李飞刀
    最后一次更改: 朽木露琪亚

    功能说明:
    - 为 `emit_c` 的 pass-after IR 测试提供最小 lowering 包装。
    - 返回被 pass 改写后的 entry block，便于按顺序检查 lowered op。

    使用示例:
    - block = _lower_single_op_func([mem], mem, lambda block: [...])

    关联文件:
    - spec: spec/dsl/gen_kernel/emit.md
    - test: test/dsl/gen_kernel/emit/test_emit.py
    - 功能实现: test/dsl/gen_kernel/emit/test_emit.py
    """

    block = Block(arg_types=input_types)
    ops = build_ops(block)
    for op in ops:
        block.add_op(op)
    block.add_op(func.ReturnOp(ops[-1].results[0]))
    func_type = FunctionType.from_lists(input_types, [result_type])
    func_op = func.FuncOp("main", func_type, Region(block))
    module = ModuleOp([func_op])
    NnLoweringPass().run(module)
    return block


def _lower_built_func(fn: object, *runtime_args: object) -> Block:
    """对 `build_func_op(...)` 生成的 `func.func` 执行 pass 并返回 entry block。

    创建者: 小李飞刀
    最后一次更改: 朽木露琪亚

    功能说明:
    - 用于 I4 的公开链路 smoke：`build_func_op -> NnLoweringPass -> emit_c`。
    - 返回被 pass 改写后的 entry block，便于继续按 lowered op 发射节点级代码。

    使用示例:
    - block = _lower_built_func(add_kernel, Memory([2, 2], NumericType.Int32))

    关联文件:
    - spec: spec/dsl/gen_kernel/emit.md
    - test: test/dsl/gen_kernel/emit/test_emit.py
    - 功能实现: test/dsl/gen_kernel/emit/test_emit.py
    """

    func_op = build_func_op(fn, *runtime_args)
    module = ModuleOp([func_op])
    NnLoweringPass().run(module)
    return next(op for op in module.ops if isinstance(op, func.FuncOp)).body.block


def _make_tuner_cost_op(
    op_name: str,
    cost_kind: str,
    operands: list[object],
) -> TunerCostOp:
    """构造 `tuner.cost` 测试节点。"""

    return TunerCostOp(
        operands,
        cost_kind=StringAttr(cost_kind),
        op_name=StringAttr(op_name),
        result_type=SymbolValueType.from_expr("COST"),
    )


# EC-001
# 创建者: 金铲铲大作战
# 最后一次更改: 朽木露琪亚
# 最近一次运行测试时间: 2026-04-01 10:43:06 +0800
# 最近一次运行成功时间: 2026-04-01 10:43:06 +0800
# 功能说明: 验证算术 op 可生成赋值语句。
# 测试目的: 验证 emit_c_op 可把 addi 生成为右值赋值语句。
# 使用示例: pytest -q test/dsl/gen_kernel/emit/test_emit.py -k test_emit_c_op_lowers_arith_add
# 对应功能实现文件路径: kernel_gen/dsl/gen_kernel/emit/__init__.py
# 对应 spec 文件路径: spec/dsl/gen_kernel/emit.md
# 对应测试文件路径: test/dsl/gen_kernel/emit/test_emit.py

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

    ctx_named = EmitCContext(config={"target": "cpu", "naming": _Allocator()})
    ctx_named.bind_name(block.args[0], "lhs")
    ctx_named.bind_name(block.args[1], "rhs")
    assert emit_c_op(op, ctx_named) == "int32_t named = (lhs + rhs);"

    ctx_callable = EmitCContext(config={"target": "cpu", "naming": lambda _value: "callable"})
    ctx_callable.bind_name(block.args[0], "lhs")
    ctx_callable.bind_name(block.args[1], "rhs")
    assert emit_c_op(op, ctx_callable) == "int32_t callable = (lhs + rhs);"

    ctx_converter = EmitCContext(config={"target": "cpu", "type_converter": lambda _attr: "custom"})
    ctx_converter.bind_name(block.args[0], "lhs")
    ctx_converter.bind_name(block.args[1], "rhs")
    assert emit_c_op(op, ctx_converter) == "custom v0 = (lhs + rhs);"

    class _Converter:
        def convert(self: "_Converter", _attr: object) -> str:
            return "custom2"

    ctx_convert = EmitCContext(config={"target": "cpu", "type_converter": _Converter()})
    ctx_convert.bind_name(block.args[0], "lhs")
    ctx_convert.bind_name(block.args[1], "rhs")
    assert emit_c_op(op, ctx_convert) == "custom2 v0 = (lhs + rhs);"

    ctx_bad_converter = EmitCContext(config={"target": "cpu", "type_converter": object()})
    ctx_bad_converter.bind_name(block.args[0], "lhs")
    ctx_bad_converter.bind_name(block.args[1], "rhs")
    with pytest.raises(EmitCError) as exc_info:
        emit_c_op(op, ctx_bad_converter)
    assert "unsupported type converter" in str(exc_info.value)

    ctx_bad_naming = EmitCContext(config={"target": "cpu", "naming": object()})
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
# 最后一次更改: 金铲铲大作战
# 最近一次运行测试时间: 2026-04-01 10:43:06 +0800
# 最近一次运行成功时间: 2026-04-01 10:43:06 +0800
# 功能说明: 验证比较 value 可生成比较表达式。
# 测试目的: 验证 emit_c_value 可把 cmpi 结果生成为布尔表达式。
# 使用示例: pytest -q test/dsl/gen_kernel/emit/test_emit.py -k test_emit_c_value_lowers_compare
# 对应功能实现文件路径: kernel_gen/dsl/gen_kernel/emit/__init__.py
# 对应 spec 文件路径: spec/dsl/gen_kernel/emit.md
# 对应测试文件路径: test/dsl/gen_kernel/emit/test_emit.py

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
# 使用示例: pytest -q test/dsl/gen_kernel/emit/test_emit.py -k test_emit_c_value_unbound_block_argument_uses_index
# 对应功能实现文件路径: kernel_gen/dsl/gen_kernel/emit/__init__.py
# 对应 spec 文件路径: spec/dsl/gen_kernel/emit.md
# 对应测试文件路径: test/dsl/gen_kernel/emit/test_emit.py
def test_emit_c_value_unbound_block_argument_uses_index() -> None:
    block = Block(arg_types=[i32, i32])
    ctx = _ctx()

    second_expr = emit_c_value(block.args[1], ctx)
    first_expr = emit_c_value(block.args[0], ctx)

    assert second_expr == "arg1"
    assert first_expr == "arg0"


# EC-003
# 创建者: 金铲铲大作战
# 最后一次更改: 金铲铲大作战
# 最近一次运行测试时间: 2026-03-23 22:45:14 +0800
# 最近一次运行成功时间: 2026-03-23 22:45:14 +0800
# 功能说明: 验证 scf.for 可生成目标循环结构。
# 测试目的: 验证 emit_c_op 可拼装 for 循环与循环体语句。
# 使用示例: pytest -q test/dsl/gen_kernel/emit/test_emit.py -k test_emit_c_op_lowers_scf_for
# 对应功能实现文件路径: kernel_gen/dsl/gen_kernel/emit/__init__.py
# 对应 spec 文件路径: spec/dsl/gen_kernel/emit.md
# 对应测试文件路径: test/dsl/gen_kernel/emit/test_emit.py

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
    assert "long long v0 = (i0 + i0);" in stmt
    assert return_stmt == "return v0;"
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
# 使用示例: pytest -q test/dsl/gen_kernel/emit/test_emit.py -k test_emit_c_op_lowers_memory_access
# 对应功能实现文件路径: kernel_gen/dsl/gen_kernel/emit/__init__.py
# 对应 spec 文件路径: spec/dsl/gen_kernel/emit.md
# 对应测试文件路径: test/dsl/gen_kernel/emit/test_emit.py

def test_emit_c_op_lowers_memory_access() -> None:
    source_type = _make_memory_type([2, 4], [4, 1])
    tile_type = _make_memory_type([1, 1], [1, 1])
    block = Block(arg_types=[source_type, source_type])
    ctx = _ctx()
    ctx.bind_name(block.args[0], "source")
    ctx.bind_name(block.args[1], "target")
    c0 = arith.ConstantOp(IntegerAttr(0, IndexType()))
    c1 = arith.ConstantOp(IntegerAttr(1, IndexType()))
    load_target = DmaAllocOp([], tile_type)
    ctx.bind_name(load_target.result, "tile")
    load = DmaLoadOp(
        load_target.result,
        block.args[0],
        [c0.result, c1.result],
        [c1.result, c1.result],
        [c1.result, c1.result],
    )
    load_stmt = emit_c_op(load, ctx)
    store = DmaStoreOp(
        load_target.result,
        block.args[1],
        [c0.result, c1.result],
        [c1.result, c1.result],
        [c1.result, c1.result],
    )

    store_stmt = emit_c_op(store, ctx)

    assert "tile" in load_stmt
    assert "_src_indices" in load_stmt
    assert "_dst_indices" in load_stmt
    assert "tile.at(" in load_stmt
    assert "source.at(" in load_stmt
    assert store_stmt == "target[0][1] = tile;"

    ctx_unbound = _ctx()
    load_unbound_target = DmaAllocOp([], tile_type)
    ctx_unbound.bind_name(load_unbound_target.result, "v0")
    load_unbound = DmaLoadOp(
        load_unbound_target.result,
        block.args[0],
        [c0.result, c1.result],
        [c1.result, c1.result],
        [c1.result, c1.result],
    )
    store_unbound = DmaStoreOp(
        load_unbound_target.result,
        block.args[1],
        [c0.result, c1.result],
        [c1.result, c1.result],
        [c1.result, c1.result],
    )
    assert emit_c_op(store_unbound, ctx_unbound) == "arg1[0][1] = v0;"

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
    bad_target = DmaAllocOp([], tile_type)
    bad_source_load = DmaLoadOp(
        bad_target.result,
        bad_source.result,
        [c0.result, c1.result],
        [c1.result, c1.result],
        [c1.result, c1.result],
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
# 使用示例: pytest -q test/dsl/gen_kernel/emit/test_emit.py -k test_emit_c_op_rejects_unsupported_op
# 对应功能实现文件路径: kernel_gen/dsl/gen_kernel/emit/__init__.py
# 对应 spec 文件路径: spec/dsl/gen_kernel/emit.md
# 对应测试文件路径: test/dsl/gen_kernel/emit/test_emit.py

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
# 使用示例: pytest -q test/dsl/gen_kernel/emit/test_emit.py -k test_emit_c_value_rejects_invalid_dependency
# 对应功能实现文件路径: kernel_gen/dsl/gen_kernel/emit/__init__.py
# 对应 spec 文件路径: spec/dsl/gen_kernel/emit.md
# 对应测试文件路径: test/dsl/gen_kernel/emit/test_emit.py

def test_emit_c_value_rejects_invalid_dependency() -> None:
    with pytest.raises(EmitCError) as exc_info:
        emit_c_value(UnsupportedOp().result, _ctx())

    assert "invalid dependency" in str(exc_info.value)
    assert "test.unsupported" in str(exc_info.value)


# EC-007
# 创建者: jcc你莫辜负
# 最后一次更改: 金铲铲大作战
# 最近一次运行测试时间: 2026-03-28 07:20:00 +0800
# 最近一次运行成功时间: 2026-03-28 07:20:00 +0800
# 功能说明: 验证 symbol.add 在 cpu target 下可生成标量表达式与赋值语句。
# 测试目的: 锁定 emit_c 对 symbol.add 的最小支持范围，保障 symbol 标量返回链路可用。
# 使用示例: pytest -q test/dsl/gen_kernel/emit/test_emit.py -k test_emit_c_op_lowers_symbol_add
# 对应功能实现文件路径: kernel_gen/dsl/gen_kernel/emit/__init__.py
# 对应 spec 文件路径: spec/dsl/gen_kernel/emit.md
# 对应测试文件路径: test/dsl/gen_kernel/emit/test_emit.py
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
# 功能说明: 验证不支持的后端目标仍会拒绝 symbol.add。
# 测试目的: 锁定 emit_c 只在 cpu/npu_demo 两类目标支持 symbol 标量运算。
# 使用示例: pytest -q test/dsl/gen_kernel/emit/test_emit.py -k test_emit_c_op_rejects_symbol_add_on_non_cpu
# 对应功能实现文件路径: kernel_gen/dsl/gen_kernel/emit/__init__.py
# 对应 spec 文件路径: spec/dsl/gen_kernel/emit.md
# 对应测试文件路径: test/dsl/gen_kernel/emit/test_emit.py
def test_emit_c_op_rejects_symbol_add_on_non_cpu() -> None:
    lhs_type = SymbolValueType.from_expr("L")
    rhs_type = SymbolValueType.from_expr("R")
    out_type = SymbolValueType.from_expr("L + R")
    block = Block(arg_types=[lhs_type, rhs_type])
    ctx = EmitCContext(config={"target": "cuda"})
    ctx.bind_name(block.args[0], "lhs")
    ctx.bind_name(block.args[1], "rhs")
    op = SymbolAddOp(block.args[0], block.args[1], out_type)

    with pytest.raises(EmitCError, match="unsupported target"):
        emit_c_value(op.result, ctx)


# EC-008A
# 创建者: jcc你莫辜负
# 最后修改人: jcc你莫辜负
# 测试目的: 验证 npu_demo 下 symbol.const/cast/to_float 可生成 `S_INT` 与目标结果类型局部变量语句。
# 对应功能实现文件路径: kernel_gen/dsl/gen_kernel/emit/__init__.py
# 对应 spec 文件路径: spec/dsl/gen_kernel/emit.md
# 对应测试文件路径: test/dsl/gen_kernel/emit/test_emit.py
def test_emit_c_op_lowers_npu_demo_symbol_const_cast_and_to_float() -> None:
    ctx = _npu_ctx()
    const = SymbolConstOp(7)
    cast = SymbolCastOp(const.result, i32)
    to_float = SymbolToFloatOp(const.result, f32)

    assert emit_c_op(const, ctx) == "S_INT c_7 = 7;"
    assert emit_c_op(cast, ctx) == "int32_t c_7_cast_int32_t = c_7;"
    assert emit_c_op(to_float, ctx) == "float v0 = c_7;"


# EC-008A-MODULE
# 创建者: 守护最好的爱莉希雅
# 最后修改人: 守护最好的爱莉希雅
# 测试目的: 验证 target=npu_demo 下单函数 plain module 的 symbol.const/cast 不需要 `arch.launch` wrapper 也能直接 emit。
# 对应功能实现文件路径: kernel_gen/dsl/gen_kernel/gen_kernel.py
# 对应 spec 文件路径: spec/dsl/gen_kernel/emit.md
# 对应测试文件路径: test/dsl/gen_kernel/emit/test_emit.py
def test_emit_c_lowers_npu_demo_plain_symbol_module_without_launch_wrapper() -> None:
    block = Block(arg_types=[])
    const = SymbolConstOp(9)
    cast = SymbolCastOp(const.result, i32)
    block.add_ops([const, cast, func.ReturnOp()])
    module = ModuleOp([func.FuncOp("symbol_cast_case", FunctionType.from_lists([], []), Region(block))])

    source = emit_c(module, _npu_ctx())

    assert "void symbol_cast_case()" in source
    assert "S_INT c_9 = 9;" in source
    assert "int32_t c_9_cast_int32_t = c_9;" in source
    assert "launch<" not in source


# EC-008A-MODULE-EMPTY
# 创建者: OpenAI Codex
# 最后修改人: OpenAI Codex
# 测试目的: 验证 target=npu_demo 下 return-only plain module 也不要求 `arch.launch` wrapper。
# 对应功能实现文件路径: kernel_gen/dsl/gen_kernel/emit/__init__.py
# 对应 spec 文件路径: spec/dsl/gen_kernel/emit.md
# 对应测试文件路径: test/dsl/gen_kernel/emit/test_emit.py
def test_emit_c_lowers_npu_demo_return_only_plain_module_without_launch_wrapper() -> None:
    block = Block(arg_types=[])
    block.add_op(func.ReturnOp())
    module = ModuleOp([func.FuncOp("npu_demo_header_case", FunctionType.from_lists([], []), Region(block))])

    source = emit_c(module, _npu_ctx())

    assert "void npu_demo_header_case()" in source
    assert "launch<" not in source


# EC-008B
# 创建者: jcc你莫辜负
# 最后修改人: jcc你莫辜负
# 测试目的: 验证 npu_demo 下 symbol 二元与比较 op 会生成 `S_INT/bool` 局部变量语句。
# 对应功能实现文件路径: kernel_gen/dsl/gen_kernel/emit/__init__.py
# 对应 spec 文件路径: spec/dsl/gen_kernel/emit.md
# 对应测试文件路径: test/dsl/gen_kernel/emit/test_emit.py
def test_emit_c_op_lowers_npu_demo_symbol_binary_and_compare() -> None:
    lhs_type = SymbolValueType.from_expr("L")
    rhs_type = SymbolValueType.from_expr("R")
    add_type = SymbolValueType.from_expr("L + R")
    block = Block(arg_types=[lhs_type, rhs_type])
    ctx = _npu_ctx()
    ctx.bind_name(block.args[0], "lhs")
    ctx.bind_name(block.args[1], "rhs")

    add = SymbolAddOp(block.args[0], block.args[1], add_type)
    eq = SymbolEqOp(block.args[0], block.args[1], i1)

    assert emit_c_op(add, ctx) == "S_INT v0 = (lhs + rhs);"
    assert emit_c_op(eq, ctx) == "bool v1 = (lhs == rhs);"


# EC-008C
# 创建者: jcc你莫辜负
# 最后修改人: jcc你莫辜负
# 测试目的: 验证 npu_demo 下 symbol.get_dim/get_stride 会生成 `S_INT` 成员查询局部变量语句。
# 对应功能实现文件路径: kernel_gen/dsl/gen_kernel/emit/__init__.py
# 对应 spec 文件路径: spec/dsl/gen_kernel/emit.md
# 对应测试文件路径: test/dsl/gen_kernel/emit/test_emit.py
def test_emit_c_op_lowers_npu_demo_symbol_queries() -> None:
    mem = _make_memory_type([4, 8], [8, 1], space="global")
    block = Block(arg_types=[mem])
    ctx = _npu_ctx()
    ctx.bind_name(block.args[0], "src")
    dim = SymbolGetDimOp(block.args[0], 1)
    stride = SymbolGetStrideOp(block.args[0], 0)

    assert emit_c_value(dim.result, ctx) == "src.get_shape(1)"
    assert emit_c_value(stride.result, ctx) == "src.get_stride(0)"
    assert emit_c_op(dim, ctx) == "S_INT v0 = src.get_shape(1);"
    assert emit_c_op(stride, ctx) == "S_INT v1 = src.get_stride(0);"


# EC-008D
# 创建者: jcc你莫辜负
# 最后修改人: jcc你莫辜负
# 测试目的: 验证 npu_demo 下 symbol.for 使用 `S_INT` 迭代变量，并复用前置 symbol.const 名称。
# 对应功能实现文件路径: kernel_gen/dsl/gen_kernel/emit/__init__.py
# 对应 spec 文件路径: spec/dsl/gen_kernel/emit.md
# 对应测试文件路径: test/dsl/gen_kernel/emit/test_emit.py
def test_emit_c_op_lowers_npu_demo_symbol_for() -> None:
    ctx = _npu_ctx()
    start = SymbolConstOp(0)
    end = SymbolConstOp(8)
    step = SymbolConstOp(2)
    body = Block(arg_types=[SymbolIterType.from_bounds("0", "8", "2")])
    loop = SymbolForOp(start.result, end.result, step.result, body)

    assert emit_c_op(start, ctx) == "S_INT c_0 = 0;"
    assert emit_c_op(end, ctx) == "S_INT c_8 = 8;"
    assert emit_c_op(step, ctx) == "S_INT c_2 = 2;"
    assert emit_c_op(loop, ctx) == "for (S_INT i0 = c_0; i0 < c_8; i0 += c_2) {\n}"


# EC-008E
# 创建者: 小李飞刀
# 最后一次更改: 小李飞刀
# 最近一次运行测试时间: 2026-04-02 23:04:42 +0800
# 最近一次运行成功时间: 2026-04-02 23:04:42 +0800
# 功能说明: 验证 `build_func_op -> pass -> emit_c` 的 add 三条 CPU 路径可生成 lowered IR 节点片段。
# 测试目的: 清理 raw `NnAddOp` 节点级直出源码的旧成功口径，锁定公开成功链路来自 pass 后 `kernel.binary_elewise` / `dma.fill`。
# 使用示例: pytest -q test/dsl/gen_kernel/emit/test_emit.py -k test_emit_c_op_lowers_build_func_op_nn_add_variants_after_pass
# 对应功能实现文件路径: kernel_gen/dsl/gen_kernel/emit/__init__.py
# 对应 spec 文件路径: spec/dsl/gen_kernel/emit.md
# 对应测试文件路径: test/dsl/gen_kernel/emit/test_emit.py
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
    pair_add = next(op for op in pair_block.ops if isinstance(op, KernelBinaryElewiseOp))
    assert emit_c_op(pair_add, pair_ctx) == "cpu::add(lhs, rhs, v0);"

    const_block = _lower_built_func(
        add_const_direct,
        Memory([2, 3], NumericType.Int32),
    )
    const_ctx = _ctx()
    const_ctx.bind_name(const_block.args[0], "lhs")
    const_fill = next(op for op in const_block.ops if isinstance(op, DmaFillOp))
    const_add = next(op for op in const_block.ops if isinstance(op, KernelBinaryElewiseOp))
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
    symbol_add = next(op for op in symbol_block.ops if isinstance(op, KernelBinaryElewiseOp))
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
# 使用示例: pytest -q test/dsl/gen_kernel/emit/test_emit.py -k test_emit_c_op_keeps_nn_add_unsupported_without_prebound_result_or_on_non_cpu
# 对应功能实现文件路径: kernel_gen/dsl/gen_kernel/emit/__init__.py
# 对应 spec 文件路径: spec/dsl/gen_kernel/emit.md
# 对应测试文件路径: test/dsl/gen_kernel/emit/test_emit.py
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

    non_cpu_ctx = EmitCContext(config={"target": "cuda"})
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
# 最后一次更改: 朽木露琪亚
# 最近一次运行测试时间: 2026-04-02 20:39:00 +0800
# 最近一次运行成功时间: 2026-04-02 20:39:00 +0800
# 功能说明: 验证 emit_c 可消费 pass 后 `symbol.get_dim + dma.alloc + kernel.binary_elewise` 的 memory+memory lowered IR。
# 测试目的: 锁定 CPU emitter 不再卡在 `symbol.get_dim: unsupported op`，且 `kernel.binary_elewise(kind="add")` 会收口为 `cpu::add(...)`。
# 使用示例: pytest -q test/dsl/gen_kernel/emit/test_emit.py -k test_emit_c_memory_space_template_alloc
# 对应功能实现文件路径: kernel_gen/dsl/gen_kernel/emit/__init__.py
# 对应 spec 文件路径: spec/dsl/gen_kernel/emit.md
# 对应测试文件路径: test/dsl/gen_kernel/emit/test_emit.py
def test_emit_c_memory_space_template_alloc() -> None:
    mem = _make_memory_type([2, 2], [2, 1])
    space = NnMemorySpaceAttr.from_name("global")
    block = _lower_single_op_func(
        [mem, mem],
        mem,
        lambda block: [NnAddOp(block.args[0], block.args[1], mem, space)],
    )
    ops = list(block.ops)
    dim0 = next((op for op in ops if isinstance(op, SymbolGetDimOp) and op.axis.data == 0), None)
    dim1 = next((op for op in ops if isinstance(op, SymbolGetDimOp) and op.axis.data == 1), None)
    alloc = next(op for op in ops if isinstance(op, DmaAllocOp))
    add = next(op for op in ops if isinstance(op, KernelBinaryElewiseOp))

    ctx = _ctx()
    ctx.bind_name(block.args[0], "lhs")
    ctx.bind_name(block.args[1], "rhs")

    alloc_text = emit_c_op(alloc, ctx)
    if dim0 is not None and dim1 is not None:
        assert emit_c_value(dim0.result, ctx) == "lhs.shape()[0]"
        assert emit_c_value(dim1.result, ctx) == "lhs.shape()[1]"
        assert emit_c_op(dim0, ctx) == ""
        assert emit_c_op(dim1, ctx) == ""
        assert "long long v0_shape[2] = {lhs.shape()[0], lhs.shape()[1]};" in alloc_text
    else:
        assert dim0 is None and dim1 is None
        assert "long long v0_shape[2] = {2, 2};" in alloc_text
    assert "long long v0_stride[2] = {2, 1};" in alloc_text
    assert "int32_t v0_buffer[4] = {};" in alloc_text
    assert "Memory<GM, int32_t> v0(v0_buffer, 2, v0_shape, v0_stride, MemoryFormat::Norm);" in alloc_text
    assert emit_c_op(add, ctx) == "cpu::add(lhs, rhs, v0);"


# EC-S7-001
# 创建者: 小李飞刀
# 最后一次更改: 小李飞刀
# 最近一次运行测试时间: N/A
# 最近一次运行成功时间: N/A
# 功能说明: 验证 kernel-family 节点在 emit_c 中会生成稳定 helper 文本，并对未实现的 reduce kind 显式失败。
# 测试目的: 覆盖 exp/select/reduce/reduce_min/img2col1d/img2col2d 的节点级源码出口，避免这些路径在 coverage 里长期空白。
# 使用示例: pytest -q test/dsl/gen_kernel/emit/test_emit.py -k test_emit_c_op_lowers_kernel_family_and_rejects_unsupported_reduce_kind
# 对应功能实现文件路径: kernel_gen/dsl/gen_kernel/emit/__init__.py, kernel_gen/dialect/kernel.py
# 对应 spec 文件路径: spec/dsl/gen_kernel/emit.md, spec/dialect/kernel.md
# 对应测试文件路径: test/dsl/gen_kernel/emit/test_emit.py
def test_emit_c_op_lowers_kernel_family_and_rejects_unsupported_reduce_kind() -> None:
    space = NnMemorySpaceAttr.from_name("global")
    mem = _make_memory_type([2, 2], [2, 1], element_type=f32)
    cond_mem = _make_memory_type([2, 2], [2, 1], element_type=i1)
    reduce_out = _make_memory_type([2, 1], [1, 1], element_type=f32)
    img2col1d_in = _make_memory_type([1, 3, 8], [24, 8, 1], element_type=f32)
    img2col1d_out = _make_memory_type([1, 3, 3, 6], [54, 18, 6, 1], element_type=f32)
    img2col2d_in = _make_memory_type([1, 3, 5, 5], [75, 25, 5, 1], element_type=f32)
    img2col2d_out = _make_memory_type([1, 3, 3, 3, 3, 3], [243, 81, 27, 9, 3, 1], element_type=f32)

    def _bind(*pairs: tuple[object, str]) -> EmitCContext:
        ctx = _npu_ctx()
        for value, name in pairs:
            ctx.bind_name(value, name)
        return ctx

    exp_block = Block(arg_types=[mem, mem])
    exp_op = KernelExpOp(exp_block.args[1], exp_block.args[0], space)
    exp_op.verify()
    exp_ctx = _bind((exp_block.args[0], "out"), (exp_block.args[1], "input"))
    assert emit_c_op(exp_op, exp_ctx) == "exp<GM, float, float>(out /*out*/, input /*input*/);"

    select_block = Block(arg_types=[mem, cond_mem, mem, mem])
    select_op = KernelSelectOp(
        select_block.args[0],
        select_block.args[1],
        select_block.args[2],
        select_block.args[3],
        space,
    )
    select_op.verify()
    select_ctx = _bind(
        (select_block.args[0], "out"),
        (select_block.args[1], "cond"),
        (select_block.args[2], "lhs"),
        (select_block.args[3], "rhs"),
    )
    assert (
        emit_c_op(select_op, select_ctx)
        == "select<GM, float, float>(out /*out*/, cond /*cond*/, lhs /*lhs*/, rhs /*rhs*/);"
    )

    reduce_block = Block(arg_types=[reduce_out, mem])
    reduce_sum_op = KernelReduceOp(
        reduce_block.args[0],
        reduce_block.args[1],
        kind="sum",
        axis=1,
        keepdim=True,
        space=space,
    )
    reduce_sum_op.verify()
    reduce_ctx = _bind((reduce_block.args[0], "out"), (reduce_block.args[1], "input"))
    assert (
        emit_c_op(reduce_sum_op, reduce_ctx)
        == "reduce_sum<GM, float, float>(out /*out*/, input /*input*/, 1 /*axis*/);"
    )

    reduce_min_op = KernelReduceMinOp(reduce_block.args[0], reduce_block.args[1], axis=1, keepdim=True, space=space)
    reduce_min_op.verify()
    assert (
        emit_c_op(reduce_min_op, reduce_ctx)
        == "reduce_min<GM, float, float>(out /*out*/, input /*input*/, 1 /*axis*/);"
    )

    unsupported_reduce_op = KernelReduceOp(
        reduce_block.args[0],
        reduce_block.args[1],
        kind="max",
        axis=1,
        keepdim=True,
        space=space,
    )
    unsupported_reduce_op.verify()
    with pytest.raises(EmitCError, match="kernel.reduce: unsupported kind=max"):
        emit_c_op(unsupported_reduce_op, reduce_ctx)

    c0 = arith.ConstantOp(IntegerAttr(0, i32))
    c1 = arith.ConstantOp(IntegerAttr(1, i32))
    c3 = arith.ConstantOp(IntegerAttr(3, i32))

    img2col1d_block = Block(arg_types=[img2col1d_out, img2col1d_in])
    img2col1d_op = KernelImg2col1dOp(
        img2col1d_block.args[0],
        img2col1d_block.args[1],
        c3.result,
        c1.result,
        c1.result,
        c0.result,
        c0.result,
        space,
    )
    img2col1d_op.verify()
    img2col1d_ctx = _bind((img2col1d_block.args[0], "out"), (img2col1d_block.args[1], "input"))
    assert (
        emit_c_op(img2col1d_op, img2col1d_ctx)
        == "img2col1d<GM, GM, float, float>(out /*out*/, input /*input*/, 3 /*k*/, 1 /*s*/, 1 /*d*/, 0 /*p_left*/, 0 /*p_right*/);"
    )

    img2col2d_block = Block(arg_types=[img2col2d_out, img2col2d_in])
    img2col2d_op = KernelImg2col2dOp(
        img2col2d_block.args[0],
        img2col2d_block.args[1],
        c3.result,
        c3.result,
        c1.result,
        c1.result,
        c1.result,
        c1.result,
        c0.result,
        c0.result,
        c0.result,
        c0.result,
        space,
    )
    img2col2d_op.verify()
    img2col2d_ctx = _bind((img2col2d_block.args[0], "out"), (img2col2d_block.args[1], "input"))
    assert (
        emit_c_op(img2col2d_op, img2col2d_ctx)
        == "img2col2d<GM, GM, float, float>(out /*out*/, input /*input*/, 3 /*kh*/, 3 /*kw*/, 1 /*sh*/, 1 /*sw*/, 1 /*dh*/, 1 /*dw*/, 0 /*ph*/, 0 /*pw*/, 0 /*pl*/, 0 /*pr*/);"
    )


# EC-I3-001A
# 创建者: 小李飞刀
# 最后一次更改: 小李飞刀
# 最近一次运行测试时间: N/A
# 最近一次运行成功时间: N/A
# 功能说明: 验证 target=npu_demo 下 `dma.alloc` 会发射 helper 形式的 `alloc<Space, T>(shape, stride)`。
# 测试目的: 锁定 `npu_demo` 下 `dma.alloc` 不再展开底层 buffer + `Memory(...)` 构造，而是走 `include/api` 约定的 helper 形态。
# 使用示例: pytest -q test/dsl/gen_kernel/emit/test_emit.py -k test_emit_c_lowers_npu_demo_dma_alloc_helper_contract
# 对应功能实现文件路径: kernel_gen/dsl/gen_kernel/emit/__init__.py
# 对应 spec 文件路径: spec/dsl/gen_kernel/emit.md
# 对应测试文件路径: test/dsl/gen_kernel/emit/test_emit.py
def test_emit_c_lowers_npu_demo_dma_alloc_helper_contract() -> None:
    alloc_type = _make_memory_type([2, 3], [3, 1], space="tsm", element_type=f32)
    alloc = DmaAllocOp([], alloc_type)

    alloc_stmt = emit_c_op(alloc, _npu_ctx())

    assert alloc_stmt == (
        "Memory<TSM, float> v0 = alloc<TSM, float>({2, 3} /*shape*/, {3, 1} /*stride*/);"
    )

    dyn_m = SymbolValueType.from_expr("M")
    dyn_n = SymbolValueType.from_expr("N")
    dyn_block = Block(arg_types=[dyn_m, dyn_n])
    dyn_ctx = _npu_ctx()
    dyn_ctx.bind_name(dyn_block.args[0], "m")
    dyn_ctx.bind_name(dyn_block.args[1], "n")
    dyn_alloc_type = NnMemoryType(
        ArrayAttr([StringAttr("M"), StringAttr("N")]),
        ArrayAttr([StringAttr("N"), IntAttr(1)]),
        f32,
        NnMemorySpaceAttr.from_name("tsm"),
    )
    dyn_alloc = DmaAllocOp([dyn_block.args[0], dyn_block.args[1]], dyn_alloc_type)

    dyn_stmt = emit_c_op(dyn_alloc, dyn_ctx)

    assert dyn_stmt == (
        "Memory<TSM, float> v0 = alloc<TSM, float>({m, n} /*shape*/, {n, 1} /*stride*/);"
    )


# EC-I3-001B
# 创建者: 小李飞刀
# 最后一次更改: 小李飞刀
# 最近一次运行测试时间: N/A
# 最近一次运行成功时间: N/A
# 功能说明: 验证 target=npu_demo 下 `dma.broadcast` 会发射 helper 形式的 `broadcast<...>(dst, source)`。
# 测试目的: 锁定 `dma.broadcast` 在 `npu_demo` 下不再保留 IR 名称，也不误落回 `unsupported op`。
# 使用示例: pytest -q test/dsl/gen_kernel/emit/test_emit.py -k test_emit_c_lowers_npu_demo_dma_broadcast_helper_contract
# 对应功能实现文件路径: kernel_gen/dsl/gen_kernel/emit/__init__.py
# 对应 spec 文件路径: spec/dsl/gen_kernel/emit.md
# 对应测试文件路径: test/dsl/gen_kernel/emit/test_emit.py
def test_emit_c_lowers_npu_demo_dma_broadcast_helper_contract() -> None:
    dst_type = _make_memory_type([4, 8], [8, 1], space="tsm", element_type=f32)
    src_type = _make_memory_type([1, 8], [8, 1], space="tsm", element_type=f32)
    block = Block(arg_types=[dst_type, src_type])
    ctx = _npu_ctx()
    ctx.bind_name(block.args[0], "dst")
    ctx.bind_name(block.args[1], "src")

    stmt = emit_c_op(DmaBroadcastOp(block.args[0], block.args[1]), ctx)

    assert stmt == "broadcast<TSM, TSM, float, float>(dst /*dst*/, src /*source*/);"


def test_emit_c_lowers_cpu_dma_broadcast_helper_contract() -> None:
    dst_type = _make_memory_type([4, 8], [8, 1], space="global", element_type=f32)
    src_type = _make_memory_type([1, 8], [8, 1], space="global", element_type=f32)
    block = Block(arg_types=[dst_type, src_type])
    ctx = _ctx()
    ctx.bind_name(block.args[0], "dst")
    ctx.bind_name(block.args[1], "src")

    stmt = emit_c_op(DmaBroadcastOp(block.args[0], block.args[1]), ctx)

    assert stmt == "cpu::broadcast(src, dst);"


def test_emit_c_lowers_npu_demo_dma_misc_helper_contracts() -> None:
    dst_type = _make_memory_type([2, 3], [3, 1], space="global", element_type=f32)
    src_type = _make_memory_type([2, 3], [3, 1], space="global", element_type=i32)
    reshape_dst_type = _make_memory_type([3, 2], [2, 1], space="global", element_type=f32)
    block = Block(arg_types=[dst_type, src_type])
    ctx = _npu_ctx()
    ctx.bind_name(block.args[0], "dst")
    ctx.bind_name(block.args[1], "src")

    cast_stmt = emit_c_op(DmaCastOp(block.args[0], block.args[1]), ctx)
    copy_stmt = emit_c_op(DmaCopyOp(block.args[0], block.args[0]), ctx)
    free_stmt = emit_c_op(DmaFreeOp(block.args[0]), ctx)
    transpose_stmt = emit_c_op(DmaTransposeOp(block.args[0], block.args[0], perm=[1, 0]), ctx)
    reshape_stmt = emit_c_op(
        DmaReshapeOp(
            block.args[0],
            [arith.ConstantOp(IntegerAttr(3, i32)).result, arith.ConstantOp(IntegerAttr(2, i32)).result],
            reshape_dst_type,
        ),
        ctx,
    )

    assert cast_stmt == "cast<GM, float, int32_t>(dst /*dst*/, src /*source*/);"
    assert copy_stmt == "copy<GM, GM, float, float>(dst /*dst*/, dst /*source*/);"
    assert free_stmt == "free<GM, float>(dst /*source*/);"
    assert transpose_stmt == "transpose<GM, GM, float, float>(dst /*dst*/, dst /*source*/, {1, 0} /*perm*/);"
    assert "Memory<GM, float> v0 = dst.reshape({3, 2} /*shape*/);" == reshape_stmt


# EC-S7-001
# 创建者: 小李飞刀
# 最后一次更改: 小李飞刀
# 功能说明: 覆盖 emit_c 上下文命名冲突、symbol.const 复用与公开发射接口的边界。
# 测试目的: 锁定 `EmitCContext` 与 `emit_c_op(...)` 的公开行为，不再依赖包根 private helper。
# 使用示例: pytest -q test/dsl/gen_kernel/emit/test_emit.py -k test_emit_c_private_helper_and_context_edges
# 对应功能实现文件路径: kernel_gen/dsl/gen_kernel/emit/__init__.py
# 对应 spec 文件路径: spec/dsl/gen_kernel/emit.md
# 对应测试文件路径: test/dsl/gen_kernel/emit/test_emit.py
def test_emit_c_private_helper_and_context_edges(monkeypatch: pytest.MonkeyPatch) -> None:
    naming_block = Block(arg_types=[i32, i32, i32])
    naming_ctx = _ctx()
    naming_ctx.bind_name(naming_block.args[0], "v0")
    assert naming_ctx.create_or_get_name(naming_block.args[1]) == "arg1"

    dedupe_ctx = EmitCContext(config={"target": "cpu", "naming": lambda _value: "lhs"})
    naming_mem = _make_memory_type([2], [1], element_type=f32)
    first_alloc = DmaAllocOp([], naming_mem)
    second_alloc = DmaAllocOp([], naming_mem)
    assert dedupe_ctx.create_or_get_name(naming_block.args[0]) == "arg0"
    assert dedupe_ctx.create_or_get_name(first_alloc.result) == "lhs"
    assert dedupe_ctx.create_or_get_name(second_alloc.result) == "lhs_1"

    npu_ctx = _npu_ctx()
    positive_const = SymbolConstOp(7)
    duplicate_const = SymbolConstOp(7)
    negative_const = SymbolConstOp(-3)
    assert emit_c_op(positive_const, npu_ctx) == "S_INT c_7 = 7;"
    assert emit_c_op(duplicate_const, npu_ctx) == ""
    assert npu_ctx.lookup_name(duplicate_const.result) == "c_7"
    assert emit_c_op(negative_const, npu_ctx) == "S_INT c_m3 = -3;"

    memory_type = _make_memory_type([2, 2], [2, 1], element_type=f32)
    mixed_block = Block(arg_types=[memory_type, i32, i1])
    mixed_ctx = _ctx()
    mixed_ctx.bind_name(mixed_block.args[0], "lhs")
    mixed_ctx.bind_name(mixed_block.args[1], "bias")
    mixed_ctx.bind_name(mixed_block.args[2], "flag")
    mixed_add = NnAddOp(mixed_block.args[0], mixed_block.args[1], memory_type, NnMemorySpaceAttr.from_name("global"))
    mixed_ctx.bind_name(mixed_add.result, "out")
    assert emit_c_op(mixed_add, mixed_ctx) == "cpu::add(lhs, bias, out);"

    invalid_add = NnAddOp(mixed_block.args[0], mixed_block.args[2], memory_type, NnMemorySpaceAttr.from_name("global"))
    mixed_ctx.bind_name(invalid_add.result, "bad_out")
    with pytest.raises(EmitCError, match="unsupported op"):
        emit_c_op(invalid_add, mixed_ctx)

    view_ctx = _npu_ctx()
    source_type = _make_memory_type([2, 2], [2, 1], element_type=f32)
    view_block = Block(arg_types=[source_type])
    view_ctx.bind_name(view_block.args[0], "src")
    view_op = DmaViewOp(
        view_block.args[0],
        [arith.ConstantOp(IntegerAttr(0, i32)).result, arith.ConstantOp(IntegerAttr(0, i32)).result],
        [arith.ConstantOp(IntegerAttr(2, i32)).result, arith.ConstantOp(IntegerAttr(2, i32)).result],
        [arith.ConstantOp(IntegerAttr(2, i32)).result, arith.ConstantOp(IntegerAttr(1, i32)).result],
        source_type,
    )
    view_ctx.config["naming"] = lambda _value: "src"
    stmt = emit_c_op(view_op, view_ctx)
    assert "src_1" in stmt

    with pytest.raises(EmitCError, match="unsupported op"):
        emit_c_op(
            DmaCastOp.create(operands=[], result_types=[]),
            _npu_ctx(),
        )


# EC-S7-002
# 创建者: 小李飞刀
# 最后一次更改: 小李飞刀
# 功能说明: 覆盖 emit_c 上下文提供的 layout 与 emitter 黑盒重排行为。
# 测试目的: 锁定 `EmitCContext` 公开行为和 emit 结果，不再把 operand normalization 当作 context API。
# 使用示例: pytest -q test/dsl/gen_kernel/emit/test_emit.py -k test_emit_c_private_layout_and_operand_helpers
# 对应功能实现文件路径: kernel_gen/dsl/gen_kernel/emit/__init__.py
# 对应 spec 文件路径: spec/dsl/gen_kernel/emit.md
# 对应测试文件路径: test/dsl/gen_kernel/emit/test_emit.py
def test_emit_c_private_layout_and_operand_helpers() -> None:
    cpu_ctx = _ctx()
    npu_ctx = _npu_ctx()
    mem_type = _make_memory_type([2, 3], [3, 1], element_type=f32)

    assert cpu_ctx.dispatch_attr(mem_type) == "GM"
    assert npu_ctx.dispatch_attr("tlm2") == "TLM2"
    with pytest.raises(EmitCError, match="unsupported memory space"):
        cpu_ctx.dispatch_attr("weird")

    memory_block = Block(arg_types=[mem_type, mem_type, mem_type, mem_type])
    assert emit_c_value(memory_block.args[0], cpu_ctx) == "arg0"
    cpu_ctx.bind_name(memory_block.args[1], "src")
    assert emit_c_value(memory_block.args[1], cpu_ctx) == "src"
    alloc_op = DmaAllocOp([], mem_type)
    assert emit_c_value(alloc_op.result, cpu_ctx) == "v0"
    with pytest.raises(EmitCError, match="invalid dependency"):
        emit_c_value(UnsupportedOp().result, cpu_ctx)

    space = NnMemorySpaceAttr.from_name("global")
    assert emit_c_op(
        KernelBinaryElewiseOp(
            memory_block.args[1],
            memory_block.args[2],
            memory_block.args[0],
            kind="add",
            space=space,
        ),
        cpu_ctx,
    ) == "cpu::add(src, arg2, arg0);"


# EC-S7-003
# 创建者: 小李飞刀
# 最后一次更改: 小李飞刀
# 功能说明: 补齐 emit_c 上下文与公开发射入口的错误矩阵。
# 测试目的: 锁定 type converter、非法 target、动态 memory 查询与 npu_demo kernel 错误场景通过公开入口稳定报错。
# 使用示例: pytest -q test/dsl/gen_kernel/emit/test_emit.py -k test_emit_c_private_additional_error_matrix
# 对应功能实现文件路径: kernel_gen/dsl/gen_kernel/emit/__init__.py
# 对应 spec 文件路径: spec/dsl/gen_kernel/emit.md
# 对应测试文件路径: test/dsl/gen_kernel/emit/test_emit.py
def test_emit_c_private_additional_error_matrix(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    mem_type = _make_memory_type([2, 2], [2, 1], element_type=f32)
    cpu_ctx = _ctx()
    npu_ctx = _npu_ctx()

    naming_block = Block(arg_types=[i32, i32, i32])
    naming_ctx = _ctx()
    naming_ctx.bind_name(naming_block.args[0], "tmp")
    naming_ctx.bind_name(naming_block.args[1], "tmp_1")
    naming_ctx.config["naming"] = lambda _value: "tmp"
    naming_mem = _make_memory_type([2], [1], element_type=f32)
    assert naming_ctx.create_or_get_name(DmaAllocOp([], naming_mem).result) == "tmp_2"

    invalid_naming_ctx = EmitCContext(config={"target": "cpu", "naming": object()})
    with pytest.raises(EmitCError, match="unsupported naming strategy"):
        invalid_naming_ctx.create_or_get_name(DmaAllocOp([], naming_mem).result)

    class _Converter:
        def convert(self, _attr: object) -> str:
            return "converted"

    assert cpu_ctx.dispatch_type(Float16Type()) == "half"
    assert cpu_ctx.dispatch_type(BFloat16Type()) == "bfloat16_t"
    assert EmitCContext(config={"target": "cpu", "type_converter": _Converter()}).dispatch_type(f32) == "converted"
    with pytest.raises(EmitCError, match="unsupported type converter"):
        EmitCContext(config={"target": "cpu", "type_converter": object()}).dispatch_type(f32)

    unit_tile_type = _make_memory_type([1], [1], element_type=f32)
    load_block = Block(arg_types=[unit_tile_type, unit_tile_type])
    load_op = DmaLoadOp(load_block.args[0], load_block.args[1], [], [], [])
    view_op = DmaViewOp(load_block.args[0], [], [], [], unit_tile_type)
    fill_value = arith.ConstantOp(FloatAttr(1.0, f32))
    fill_op = DmaFillOp(load_block.args[0], fill_value.result)
    for op in (load_op, view_op, fill_op):
        with pytest.raises(EmitCError, match="cpu-only"):
            emit_c_op(op, EmitCContext(config={"target": "gpu"}))
    store_block = Block(arg_types=[mem_type, mem_type])
    with pytest.raises(EmitCError, match="only unit-tile dma.store source is supported"):
        emit_c_op(DmaStoreOp(store_block.args[0], store_block.args[1], [], [], []), _ctx())

    alloc_op = DmaAllocOp([], mem_type)
    with pytest.raises(EmitCError, match="dma ops are cpu-only"):
        emit_c_op(alloc_op, EmitCContext(config={"target": "gpu"}))
    bad_alloc = DmaAllocOp([], i32)
    with pytest.raises(EmitCError, match="result must be nn.memory"):
        emit_c_op(bad_alloc, _ctx())
    with pytest.raises(EmitCError, match="unsupported op"):
        emit_c_op(
            NnImg2col2dOp(
                load_block.args[0],
                mem_type,
                arith.ConstantOp(IntegerAttr(1, i32)).result,
                arith.ConstantOp(IntegerAttr(1, i32)).result,
                arith.ConstantOp(IntegerAttr(1, i32)).result,
                arith.ConstantOp(IntegerAttr(1, i32)).result,
                arith.ConstantOp(IntegerAttr(1, i32)).result,
                arith.ConstantOp(IntegerAttr(1, i32)).result,
                arith.ConstantOp(IntegerAttr(0, i32)).result,
                arith.ConstantOp(IntegerAttr(0, i32)).result,
                arith.ConstantOp(IntegerAttr(0, i32)).result,
                arith.ConstantOp(IntegerAttr(0, i32)).result,
                NnMemorySpaceAttr.from_name("global"),
            ),
            EmitCContext(config={"target": "npu_demo"}),
        )

    view_ctx = _npu_ctx()
    view_block = Block(arg_types=[mem_type])
    view_ctx.bind_name(view_block.args[0], "src")
    view_ctx.bind_name(SymbolConstOp(0).result, "src_1")
    colliding_view = DmaViewOp(
        view_block.args[0],
        [],
        [arith.ConstantOp(IntegerAttr(2, i32)).result],
        [arith.ConstantOp(IntegerAttr(1, i32)).result],
        _make_memory_type([2], [1], element_type=f32),
    )
    view_ctx.config["naming"] = lambda _value: "src"
    assert "src_2" in emit_c_op(colliding_view, view_ctx)

    with pytest.raises(EmitCError, match="unsupported dynamic memory space"):
        emit_c_op(
            ArchGetDynamicMemoryOp(NnMemorySpaceAttr.from_name("global"), mem_type),
            _npu_ctx(),
        )

    rank3_type = _make_memory_type([2, 2, 2], [4, 2, 1], element_type=f32)
    rank3_block = Block(arg_types=[rank3_type, rank3_type])
    slice3 = DmaSliceOp(
        rank3_block.args[0],
        rank3_block.args[1],
        [SymbolConstOp(0).result] * 3,
        [SymbolConstOp(1).result] * 3,
        [SymbolConstOp(1).result] * 3,
    )
    deslice3 = DmaDesliceOp(rank3_block.args[1], rank3_block.args[0], [SymbolConstOp(0).result] * 3, [SymbolConstOp(1).result] * 3, [SymbolConstOp(1).result] * 3, rank3_type)
    rank3_ctx = _npu_ctx()
    rank3_ctx.bind_name(rank3_block.args[0], "dst")
    rank3_ctx.bind_name(rank3_block.args[1], "src")
    assert "{0, 0, 0}" in emit_c_op(slice3, rank3_ctx)
    assert "{0, 0, 0}" in emit_c_op(deslice3, rank3_ctx)

    kernel_block = Block(arg_types=[mem_type, mem_type, mem_type, i32])
    kernel_ctx = _npu_ctx()
    for index, arg in enumerate(kernel_block.args[:3]):
        kernel_ctx.bind_name(arg, f"m{index}")

    add_op = KernelBinaryElewiseOp(
        kernel_block.args[0],
        kernel_block.args[1],
        kernel_block.args[2],
        kind="add",
        space=NnMemorySpaceAttr.from_name("global"),
    )
    add_op.attributes["kind"] = StringAttr("pow")
    with pytest.raises(EmitCError, match="unsupported kind=pow"):
        emit_c_op(add_op, kernel_ctx)

    bad_add = KernelBinaryElewiseOp(
        kernel_block.args[0],
        kernel_block.args[1],
        kernel_block.args[3],
        kind="add",
        space=NnMemorySpaceAttr.from_name("global"),
    )
    with pytest.raises(EmitCError, match="unsupported op"):
        emit_c_op(bad_add, kernel_ctx)

    exp_bad = KernelExpOp(kernel_block.args[3], kernel_block.args[0], NnMemorySpaceAttr.from_name("global"))
    with pytest.raises(EmitCError, match="unsupported op"):
        emit_c_op(exp_bad, kernel_ctx)

    select_bad = KernelSelectOp(kernel_block.args[0], kernel_block.args[3], kernel_block.args[1], kernel_block.args[2], NnMemorySpaceAttr.from_name("global"))
    with pytest.raises(EmitCError, match="unsupported op"):
        emit_c_op(select_bad, kernel_ctx)

    reduce_bad = KernelReduceOp(
        kernel_block.args[3],
        kernel_block.args[0],
        kind=StringAttr("sum"),
        axis=IntegerAttr(0, i32),
        keepdim=False,
        space=NnMemorySpaceAttr.from_name("global"),
    )
    with pytest.raises(EmitCError, match="unsupported op"):
        emit_c_op(reduce_bad, kernel_ctx)

    reduce_min_bad = KernelReduceMinOp(
        kernel_block.args[3],
        kernel_block.args[0],
        IntegerAttr(0, i32),
        False,
        NnMemorySpaceAttr.from_name("global"),
    )
    with pytest.raises(EmitCError, match="unsupported op"):
        emit_c_op(reduce_min_bad, kernel_ctx)

    img2col1d_bad = KernelImg2col1dOp(
        kernel_block.args[3],
        kernel_block.args[0],
        SymbolConstOp(1).result,
        SymbolConstOp(1).result,
        SymbolConstOp(1).result,
        SymbolConstOp(0).result,
        SymbolConstOp(0).result,
        NnMemorySpaceAttr.from_name("global"),
    )
    with pytest.raises(EmitCError, match="unsupported op"):
        emit_c_op(img2col1d_bad, kernel_ctx)

    img2col2d_bad = KernelImg2col2dOp(
        kernel_block.args[3],
        kernel_block.args[0],
        SymbolConstOp(1).result,
        SymbolConstOp(1).result,
        SymbolConstOp(1).result,
        SymbolConstOp(1).result,
        SymbolConstOp(1).result,
        SymbolConstOp(1).result,
        SymbolConstOp(0).result,
        SymbolConstOp(0).result,
        SymbolConstOp(0).result,
        SymbolConstOp(0).result,
        NnMemorySpaceAttr.from_name("global"),
    )
    with pytest.raises(EmitCError, match="unsupported op"):
        emit_c_op(img2col2d_bad, kernel_ctx)

    broadcast_bad = DmaBroadcastOp(kernel_block.args[3], kernel_block.args[0])
    with pytest.raises(EmitCError, match="unsupported op"):
        emit_c_op(broadcast_bad, _ctx())
    with pytest.raises(EmitCError, match="unsupported op"):
        emit_c_op(broadcast_bad, _npu_ctx())

    one_operand_cast = DmaCastOp(kernel_block.args[0], kernel_block.args[1])
    assert "cast<GM, float, float>" in emit_c_op(one_operand_cast, kernel_ctx)
    bad_cast = DmaCastOp(kernel_block.args[0], kernel_block.args[3])
    with pytest.raises(EmitCError, match="unsupported op"):
        emit_c_op(bad_cast, kernel_ctx)


def test_emit_c_lowers_npu_demo_dma_indexed_and_fill_helpers() -> None:
    dst_type = _make_memory_type([2, 3], [3, 1], space="global", element_type=i32)
    src_type = _make_memory_type([4, 5], [5, 1], space="global", element_type=i32)
    block = Block(arg_types=[dst_type, src_type])
    ctx = _npu_ctx()
    ctx.bind_name(block.args[0], "dst")
    ctx.bind_name(block.args[1], "src")

    offset0 = SymbolConstOp(1)
    offset1 = SymbolConstOp(2)
    size0 = SymbolConstOp(2)
    size1 = SymbolConstOp(3)
    stride0 = SymbolConstOp(1)
    stride1 = SymbolConstOp(1)
    fill_value = SymbolConstOp(7)
    fill_cast = SymbolToIntOp(fill_value.result, i32)

    prologue = [
        emit_c_op(offset0, ctx),
        emit_c_op(offset1, ctx),
        emit_c_op(size0, ctx),
        emit_c_op(size1, ctx),
        emit_c_op(stride0, ctx),
        emit_c_op(stride1, ctx),
        emit_c_op(fill_value, ctx),
        emit_c_op(fill_cast, ctx),
    ]
    load_stmt = emit_c_op(
        DmaLoadOp(block.args[0], block.args[1], [offset0.result, offset1.result], [size0.result, size1.result], [stride0.result, stride1.result]),
        ctx,
    )
    store_stmt = emit_c_op(
        DmaStoreOp(block.args[0], block.args[1], [offset0.result, offset1.result], [size0.result, size1.result], [stride0.result, stride1.result]),
        ctx,
    )
    fill_stmt = emit_c_op(DmaFillOp(block.args[0], fill_cast.result), ctx)

    joined = "\n".join(prologue + [load_stmt, store_stmt, fill_stmt])
    assert "S_INT c_7 = 7;" in joined
    assert "int32_t c_7_cast_int32_t = c_7;" in joined
    assert "load<GM, GM, int32_t, int32_t>(dst /*dst*/, src /*source*/, {1, 2} /*offset*/, {2, 3} /*size*/, {1, 1} /*stride*/);" in joined
    assert "store<GM, GM, int32_t, int32_t>(src /*dst*/, dst /*source*/, {1, 2} /*offset*/, {2, 3} /*size*/, {1, 1} /*stride*/);" in joined
    assert "fill<GM, int32_t>(dst /*dst*/, c_7_cast_int32_t /*value*/);" in joined


# EC-I3-002
# 创建者: 小李飞刀
# 最后一次更改: 朽木露琪亚
# 最近一次运行测试时间: 2026-04-02 20:39:00 +0800
# 最近一次运行成功时间: 2026-04-02 20:39:00 +0800
# 功能说明: 验证 emit_c 可消费 pass 后 `dma.fill + kernel.binary_elewise` 的 mixed add lowered IR。
# 测试目的: 锁定 `memory+const(i32)` 与 `memory+symbol.int` 在 CPU emitter 中都走真实填充后再参与 `cpu::add(...)`。
# 使用示例: pytest -q test/dsl/gen_kernel/emit/test_emit.py -k test_emit_c_op_lowers_passed_mixed_add_pipeline_with_dma_fill
# 对应功能实现文件路径: kernel_gen/dsl/gen_kernel/emit/__init__.py
# 对应 spec 文件路径: spec/dsl/gen_kernel/emit.md
# 对应测试文件路径: test/dsl/gen_kernel/emit/test_emit.py
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
    const_add = next(op for op in const_ops if isinstance(op, KernelBinaryElewiseOp))

    const_ctx = _ctx()
    const_ctx.bind_name(const_block.args[0], "lhs")
    const_alloc_names = [emit_c_op(op, const_ctx) for op in const_ops if isinstance(op, DmaAllocOp)]
    assert len(const_alloc_names) == 2
    has_dim_ops = any(isinstance(op, SymbolGetDimOp) for op in const_ops)
    if has_dim_ops:
        assert "lhs.shape()[0]" in const_alloc_names[0]
        assert "lhs.shape()[0]" in const_alloc_names[1]
    else:
        assert "long long v0_shape[2] = {2, 2};" in const_alloc_names[0]
        assert "long long v1_shape[2] = {2, 2};" in const_alloc_names[1]
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
    symbol_add = next(op for op in symbol_ops if isinstance(op, KernelBinaryElewiseOp))

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
# 最后一次更改: 金铲铲大作战
# 最近一次运行测试时间: 2026-04-01 10:43:06 +0800
# 最近一次运行成功时间: 2026-04-01 10:43:06 +0800
# 功能说明: 验证 emit_c 可生成 dma.alloc/dma.view 的最小 CPU 文本片段。
# 测试目的: 锁定 tile-local buffer 分配与子视图重解释的节点级映射，避免 conv 主线在 alloc/view 处提前失败。
# 使用示例: pytest -q test/dsl/gen_kernel/emit/test_emit.py -k test_emit_c_op_lowers_dma_alloc_and_view
# 对应功能实现文件路径: kernel_gen/dsl/gen_kernel/emit/__init__.py
# 对应 spec 文件路径: spec/dsl/gen_kernel/emit.md
# 对应测试文件路径: test/dsl/gen_kernel/emit/test_emit.py
def test_emit_c_op_lowers_dma_alloc_and_view() -> None:
    alloc_type = _make_memory_type([2, 3], [3, 1], space="shared", element_type=f32)
    alloc = DmaAllocOp([], alloc_type)

    alloc_stmt = emit_c_op(alloc, _ctx())

    assert alloc_stmt == (
        "long long v0_shape[2] = {2, 3};\n"
        "long long v0_stride[2] = {3, 1};\n"
        "float v0_buffer[6] = {};\n"
        "Memory<SM, float> v0(v0_buffer, 2, v0_shape, v0_stride, MemoryFormat::Norm);"
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
        "Memory<GM, float> v0(const_cast<float*>(source.data()) + view_offset0, 2, v0_shape, v0_stride, source.format());"
    )


# EC-010
# 创建者: 朽木露琪亚
# 最后一次更改: 金铲铲大作战
# 最近一次运行测试时间: 2026-04-01 10:43:06 +0800
# 最近一次运行成功时间: 2026-04-01 10:43:06 +0800
# 功能说明: 验证 emit_c 可生成 symbol.for + dma.alloc + dma.slice + nn.img2col2d + dma.deslice 的真实链路片段。
# 测试目的: 锁定 conv_cpu_tiled_v1 P10 的最小节点级闭环，确保 img2col2d 与 DMA 协同路径在 CPU emitter 可落到稳定文本。
# 使用示例: pytest -q test/dsl/gen_kernel/emit/test_emit.py -k test_emit_c_op_lowers_img2col2d_dma_loop_pipeline
# 对应功能实现文件路径: kernel_gen/dsl/gen_kernel/emit/__init__.py
# 对应 spec 文件路径: spec/dsl/gen_kernel/emit.md
# 对应测试文件路径: test/dsl/gen_kernel/emit/test_emit.py
def test_emit_c_op_lowers_img2col2d_dma_loop_pipeline() -> None:
    input_memory = Memory([1, 1, 4, 4], NumericType.Float32, space=MemorySpace.GM)
    output_memory = Memory([1, 1, 2, 2, 3, 3], NumericType.Float32, space=MemorySpace.GM)
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
        offset=[
            loop_var,
            ConstAST(0),
            ConstAST(0),
            ConstAST(0),
            ConstAST(0),
            ConstAST(0),
        ],
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
    assert re.search(r"float v\d+_buffer\[16\] = \{\};", stmt)
    assert re.search(r"Memory<LM, float> v\d+\(v\d+_buffer, 4, v\d+_shape, v\d+_stride, MemoryFormat::Norm\);", stmt)
    assert re.search(r"v\d+\.at\(dma0_dst_indices\) = input\.at\(dma0_src_indices\);", stmt)
    assert re.search(r"float v\d+_buffer\[36\] = \{\};", stmt)
    assert re.search(r"Memory<LM, float> v\d+\(v\d+_buffer, 6, v\d+_shape, v\d+_stride, MemoryFormat::Norm\);", stmt)
    assert re.search(r"cpu::img2col2d\(v\d+, v\d+, 2, 2, 1, 1, 1, 1, 0, 0, 0, 0\);", stmt)
    assert re.search(r"output\.at\(dma1_dst_indices\) = v\d+\.at\(dma1_src_indices\);", stmt)
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
# 使用示例: pytest -q test/dsl/gen_kernel/emit/test_emit.py -k test_emit_c_op_assigns_unique_helper_names_for_repeated_dma_slice_and_deslice
# 对应功能实现文件路径: kernel_gen/dsl/gen_kernel/emit/__init__.py
# 对应 spec 文件路径: spec/dsl/gen_kernel/emit.md
# 对应测试文件路径: test/dsl/gen_kernel/emit/test_emit.py
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
# 创建者: 金铲铲大作战
# 最后一次更改: 金铲铲大作战
# 最近一次运行测试时间: 2026-04-24 12:00:00 +0800
# 最近一次运行成功时间: 2026-04-24 12:00:00 +0800
# 功能说明: 验证包式 emit_c 入口为 TunerCostOp 提供已注册处理函数。
# 测试目的: 锁定 `kernel_gen.dsl.gen_kernel.emit` 的注册表包含 `TunerCostOp`，且不影响既有 common op/value 注册结果。
# 使用示例: pytest -q test/dsl/gen_kernel/emit/test_emit.py -k test_emit_c_package_registers_tuner_cost_op
# 对应功能实现文件路径: kernel_gen/dsl/gen_kernel/emit/npu_demo/tuner/cost.py
# 对应 spec 文件路径: spec/dsl/gen_kernel/emit.md
# 对应测试文件路径: test/dsl/gen_kernel/emit/test_emit.py
def test_emit_c_package_registers_tuner_cost_op() -> None:
    memory_type = _make_memory_type([4, 4], [4, 1], space="global", element_type=f32)
    block = Block(arg_types=[memory_type, memory_type, memory_type])
    cost_op = TunerCostOp.create(
        operands=[block.args[0], block.args[1], block.args[2]],
        result_types=[SymbolValueType.from_expr("COST")],
        attributes={
            "space": NnMemorySpaceAttr.from_name("global"),
            "cost_kind": StringAttr("compute"),
            "op_name": StringAttr("kernel.add"),
        },
    )

    assert emit_c_register.dispatch_op(cost_op, _npu_ctx()) is not None
    assert emit_c_register.dispatch_value(SymbolConstOp(1).result, _npu_ctx()) is not None


# EC-018
# 创建者: 金铲铲大作战
# 最后一次更改: 金铲铲大作战
# 最近一次运行测试时间: 2026-04-24 12:00:00 +0800
# 最近一次运行成功时间: 2026-04-24 12:00:00 +0800
# 功能说明: 验证 npu_demo 下 `tuner.cost(op_name="kernel.add")` 发射为 `cost::add`。
# 测试目的: 锁定 `kernel.add -> cost::add`、`S_INT cost0` 和结果绑定合同。
# 使用示例: pytest -q test/dsl/gen_kernel/emit/test_emit.py -k test_emit_c_lowers_npu_demo_tuner_cost_kernel_add
# 对应功能实现文件路径: kernel_gen/dsl/gen_kernel/emit/__init__.py
# 对应 spec 文件路径: spec/dsl/gen_kernel/emit.md
# 对应测试文件路径: test/dsl/gen_kernel/emit/test_emit.py
def test_emit_c_lowers_npu_demo_tuner_cost_kernel_add() -> None:
    memory_type = _make_memory_type([4, 4], [4, 1], space="global", element_type=f32)
    block = Block(arg_types=[memory_type, memory_type, memory_type])
    ctx = _npu_ctx()
    ctx.bind_name(block.args[0], "out")
    ctx.bind_name(block.args[1], "lhs")
    ctx.bind_name(block.args[2], "rhs")
    op = _make_tuner_cost_op("kernel.add", "compute", [block.args[0], block.args[1], block.args[2]])

    stmt = emit_c_op(op, ctx)

    assert stmt == (
        "S_INT cost0 = cost::add<GM, float, float, compute>"
        "(out /*out*/, lhs /*lhs*/, rhs /*rhs*/);"
    )
    assert emit_c_value(op.result, ctx) == "cost0"


# EC-019
# 创建者: 金铲铲大作战
# 最后一次更改: 金铲铲大作战
# 最近一次运行测试时间: 2026-04-24 12:00:00 +0800
# 最近一次运行成功时间: 2026-04-24 12:00:00 +0800
# 功能说明: 验证 npu_demo 下 `tuner.cost(op_name="kernel.matmul")` 发射为 `cost::matmul`。
# 测试目的: 锁定 `kernel.matmul -> cost::matmul` 的模板顺序与 `out/lhs/rhs` 参数顺序。
# 使用示例: pytest -q test/dsl/gen_kernel/emit/test_emit.py -k test_emit_c_lowers_npu_demo_tuner_cost_kernel_matmul
# 对应功能实现文件路径: kernel_gen/dsl/gen_kernel/emit/__init__.py
# 对应 spec 文件路径: spec/dsl/gen_kernel/emit.md
# 对应测试文件路径: test/dsl/gen_kernel/emit/test_emit.py
def test_emit_c_lowers_npu_demo_tuner_cost_kernel_matmul() -> None:
    out_type = _make_memory_type([4, 4], [4, 1], space="tlm1", element_type=f32)
    lhs_type = _make_memory_type([4, 4], [4, 1], space="tsm", element_type=f32)
    rhs_type = _make_memory_type([4, 4], [4, 1], space="tsm", element_type=f32)
    block = Block(arg_types=[out_type, lhs_type, rhs_type])
    ctx = _npu_ctx()
    ctx.bind_name(block.args[0], "out")
    ctx.bind_name(block.args[1], "lhs")
    ctx.bind_name(block.args[2], "rhs")
    op = _make_tuner_cost_op("kernel.matmul", "memory", [block.args[0], block.args[1], block.args[2]])

    stmt = emit_c_op(op, ctx)

    assert stmt == (
        "S_INT cost0 = cost::matmul<TSM, TSM, TLM1, float, float, float, memory>"
        "(out /*out*/, lhs /*lhs*/, rhs /*rhs*/);"
    )
    assert emit_c_value(op.result, ctx) == "cost0"


# EC-020
# 创建者: 金铲铲大作战
# 最后一次更改: 金铲铲大作战
# 最近一次运行测试时间: 2026-04-24 12:00:00 +0800
# 最近一次运行成功时间: 2026-04-24 12:00:00 +0800
# 功能说明: 验证 npu_demo 下 `tuner.cost(op_name="dma.copy")` 发射为 `cost::copy`。
# 测试目的: 锁定 `dma.copy -> cost::copy` 的模板顺序与 `target/source` 参数顺序。
# 使用示例: pytest -q test/dsl/gen_kernel/emit/test_emit.py -k test_emit_c_lowers_npu_demo_tuner_cost_dma_copy
# 对应功能实现文件路径: kernel_gen/dsl/gen_kernel/emit/__init__.py
# 对应 spec 文件路径: spec/dsl/gen_kernel/emit.md
# 对应测试文件路径: test/dsl/gen_kernel/emit/test_emit.py
def test_emit_c_lowers_npu_demo_tuner_cost_dma_copy() -> None:
    target_type = _make_memory_type([4, 4], [4, 1], space="tsm", element_type=f32)
    source_type = _make_memory_type([4, 4], [4, 1], space="global", element_type=f32)
    block = Block(arg_types=[target_type, source_type])
    ctx = _npu_ctx()
    ctx.bind_name(block.args[0], "target")
    ctx.bind_name(block.args[1], "source")
    op = _make_tuner_cost_op("dma.copy", "memory", [block.args[0], block.args[1]])

    stmt = emit_c_op(op, ctx)

    assert stmt == (
        "S_INT cost0 = cost::copy<TSM, GM, float, memory>"
        "(target /*target*/, source /*source*/);"
    )
    assert emit_c_value(op.result, ctx) == "cost0"


# EC-021
# 创建者: 金铲铲大作战
# 最后一次更改: 金铲铲大作战
# 最近一次运行测试时间: 2026-04-24 12:00:00 +0800
# 最近一次运行成功时间: 2026-04-24 12:00:00 +0800
# 功能说明: 验证 `tuner.cost.result` 被 `symbol.add` 消费时复用已绑定 `costN` 变量名。
# 测试目的: 防止右值侧重复展开 `cost::<helper>(...)`。
# 使用示例: pytest -q test/dsl/gen_kernel/emit/test_emit.py -k test_emit_c_lowers_npu_demo_symbol_add_with_tuner_cost_value
# 对应功能实现文件路径: kernel_gen/dsl/gen_kernel/emit/__init__.py
# 对应 spec 文件路径: spec/dsl/gen_kernel/emit.md
# 对应测试文件路径: test/dsl/gen_kernel/emit/test_emit.py
def test_emit_c_lowers_npu_demo_symbol_add_with_tuner_cost_value() -> None:
    memory_type = _make_memory_type([4, 4], [4, 1], space="global", element_type=f32)
    block = Block(arg_types=[memory_type, memory_type, memory_type])
    ctx = _npu_ctx()
    ctx.bind_name(block.args[0], "out")
    ctx.bind_name(block.args[1], "lhs")
    ctx.bind_name(block.args[2], "rhs")
    cost_op = _make_tuner_cost_op("kernel.add", "compute", [block.args[0], block.args[1], block.args[2]])
    add_op = SymbolAddOp(cost_op.result, cost_op.result, SymbolValueType.from_expr("DOUBLE_COST"))

    stmt = "\n".join([emit_c_op(cost_op, ctx), emit_c_op(add_op, ctx)])

    assert stmt.count("cost::add<") == 1
    assert "S_INT cost0 = cost::add<GM, float, float, compute>" in stmt
    assert "(cost0 + cost0)" in stmt


# EC-022
# 创建者: 金铲铲大作战
# 最后一次更改: 金铲铲大作战
# 最近一次运行测试时间: 2026-04-24 12:00:00 +0800
# 最近一次运行成功时间: 2026-04-24 12:00:00 +0800
# 功能说明: 验证未知 `op_name` 的 `tuner.cost` 在 npu_demo 下必须报错。
# 测试目的: 锁定 `EmitCError` 消息包含 `tuner.cost` 与 `op_name`。
# 使用示例: pytest -q test/dsl/gen_kernel/emit/test_emit.py -k test_emit_c_rejects_unknown_npu_demo_tuner_cost_op_name
# 对应功能实现文件路径: kernel_gen/dsl/gen_kernel/emit/__init__.py
# 对应 spec 文件路径: spec/dsl/gen_kernel/emit.md
# 对应测试文件路径: test/dsl/gen_kernel/emit/test_emit.py
def test_emit_c_rejects_unknown_npu_demo_tuner_cost_op_name() -> None:
    memory_type = _make_memory_type([4, 4], [4, 1], space="global", element_type=f32)
    block = Block(arg_types=[memory_type, memory_type, memory_type])
    ctx = _npu_ctx()
    op = _make_tuner_cost_op("kernel.unknown", "compute", [block.args[0], block.args[1], block.args[2]])

    with pytest.raises(EmitCError, match=r"tuner\.cost: unsupported op_name=kernel\.unknown"):
        emit_c_op(op, ctx)


# EC-023
# 创建者: 金铲铲大作战
# 最后一次更改: 金铲铲大作战
# 最近一次运行测试时间: 2026-04-24 12:00:00 +0800
# 最近一次运行成功时间: 2026-04-24 12:00:00 +0800
# 功能说明: 验证 `tuner.cost.cost_kind` 在 npu_demo 下按原始文本透传，且缺失 memory 类型仍报错。
# 测试目的: 锁定 emit_c 不再映射或校验 `cost_kind` 内容，同时继续覆盖 memory 类型缺口边界。
# 使用示例: pytest -q test/dsl/gen_kernel/emit/test_emit.py -k test_emit_c_preserves_raw_npu_demo_tuner_cost_kind_and_rejects_invalid_memory_type
# 对应功能实现文件路径: kernel_gen/dsl/gen_kernel/emit/__init__.py
# 对应 spec 文件路径: spec/dsl/gen_kernel/emit.md
# 对应测试文件路径: test/dsl/gen_kernel/emit/test_emit.py
def test_emit_c_preserves_raw_npu_demo_tuner_cost_kind_and_rejects_invalid_memory_type() -> None:
    memory_type = _make_memory_type([4, 4], [4, 1], space="global", element_type=f32)
    scalar_block = Block(arg_types=[i32, i32])
    memory_block = Block(arg_types=[memory_type, memory_type, memory_type])
    ctx = _npu_ctx()
    invalid_kind = _make_tuner_cost_op("kernel.add", "kind2", [memory_block.args[0], memory_block.args[1], memory_block.args[2]])
    invalid_type = _make_tuner_cost_op("dma.copy", "memory", [scalar_block.args[0], scalar_block.args[1]])

    assert emit_c_op(invalid_kind, ctx) == (
        "S_INT cost0 = cost::add<GM, float, float, kind2>"
        "(arg0 /*out*/, arg1 /*lhs*/, arg2 /*rhs*/);"
    )
    with pytest.raises(EmitCError, match=r"tuner\.cost: target must be nn\.memory"):
        emit_c_op(invalid_type, ctx)


# EC-024
# 创建者: jcc你莫辜负
# 最后一次更改: 金铲铲大作战
# 最近一次运行测试时间: 2026-04-02 00:00:00 +0800
# 最近一次运行成功时间: 2026-04-02 00:00:00 +0800
# 功能说明: 验证 npu_demo 下 thread 查询节点发射为 free helper `thread_id/thread_num`。
# 测试目的: 锁定 target=npu_demo 的查询文本不再带 `ctx.`，避免回退到成员调用或 launch 语义。
# 使用示例: pytest -q test/dsl/gen_kernel/emit/test_emit.py -k test_emit_c_lowers_npu_demo_kernel_context_queries
# 对应功能实现文件路径: kernel_gen/dsl/gen_kernel/emit/__init__.py
# 对应 spec 文件路径: spec/dsl/gen_kernel/emit.md
# 对应测试文件路径: test/dsl/gen_kernel/emit/test_emit.py
def test_emit_c_lowers_npu_demo_kernel_context_queries() -> None:
    ctx = _npu_ctx()
    tid = ArchGetThreadIdOp()
    tnum = ArchGetThreadNumOp()
    ctx.bind_name(tid.result, "tid")
    ctx.bind_name(tnum.result, "tnum")

    tid_stmt = emit_c_op(tid, ctx)
    tnum_stmt = emit_c_op(tnum, ctx)

    assert tid_stmt == "S_INT tid = npu_demo::thread_id();"
    assert tnum_stmt == "S_INT tnum = npu_demo::thread_num();"
    assert "launch" not in tid_stmt
    assert "barrier" not in tnum_stmt


# EC-025
# 创建者: jcc你莫辜负
# 最后一次更改: 金铲铲大作战
# 最近一次运行测试时间: 2026-04-02 00:00:00 +0800
# 最近一次运行成功时间: 2026-04-02 00:00:00 +0800
# 功能说明: 验证 npu_demo 下 dynamic memory 查询发射为 free helper `get_dynamic_memory<TSM/TLM1>()`。
# 测试目的: 锁定 target=npu_demo 的 TSM/TLM1 动态片上内存入口文本不再带 `ctx.`，避免回退到 load/store/malloc。
# 使用示例: pytest -q test/dsl/gen_kernel/emit/test_emit.py -k test_emit_c_maps_nn_space_to_template_param
# 对应功能实现文件路径: kernel_gen/dsl/gen_kernel/emit/__init__.py
# 对应 spec 文件路径: spec/dsl/gen_kernel/emit.md
# 对应测试文件路径: test/dsl/gen_kernel/emit/test_emit.py
def test_emit_c_maps_nn_space_to_template_param() -> None:
    ctx = _npu_ctx()
    tsm_type = _make_memory_type([16], [1], space="tsm", element_type=f32)
    tlm_type = _make_memory_type([16], [1], space="tlm1", element_type=f32)
    tsm = ArchGetDynamicMemoryOp(NnMemorySpaceAttr.from_name("tsm"), tsm_type)
    tlm = ArchGetDynamicMemoryOp(NnMemorySpaceAttr.from_name("tlm1"), tlm_type)
    ctx.bind_name(tsm.result, "tsm")
    ctx.bind_name(tlm.result, "tlm")

    tsm_stmt = emit_c_op(tsm, ctx)
    tlm_stmt = emit_c_op(tlm, ctx)

    assert tsm_stmt == "Memory<TSM, float> tsm = npu_demo::get_dynamic_memory<TSM>();"
    assert tlm_stmt == "Memory<TLM1, float> tlm = npu_demo::get_dynamic_memory<TLM1>();"
    assert "load<" not in tsm_stmt
    assert "store<" not in tlm_stmt


# EC-026
# 创建者: jcc你莫辜负
# 最后一次更改: 金铲铲大作战
# 最近一次运行测试时间: 2026-04-02 00:00:00 +0800
# 最近一次运行成功时间: 2026-04-02 00:00:00 +0800
# 功能说明: 验证 npu_demo 下 view/slice/deslice/add 管线可发射稳定节点级文本。
# 测试目的: 锁定 target=npu_demo 的 DMA helper 只消费 `include/api` 的成员式 `view<T>(Vector,...)` 与 Vector 版 `slice/deslice` 接口。
# 使用示例: pytest -q test/dsl/gen_kernel/emit/test_emit.py -k test_emit_c_lowers_npu_demo_slice_deslice_add_pipeline
# 对应功能实现文件路径: kernel_gen/dsl/gen_kernel/emit/__init__.py
# 对应 spec 文件路径: spec/dsl/gen_kernel/emit.md
# 对应测试文件路径: test/dsl/gen_kernel/emit/test_emit.py
def test_emit_c_lowers_npu_demo_slice_deslice_add_pipeline() -> None:
    mem_type = _make_memory_type([16], [1], space="global", element_type=f32)
    tsm_type = _make_memory_type([16], [1], space="tsm", element_type=f32)
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
    src_view = DmaViewOp(block.args[0], [tid.result], [size.result], [stride.result], mem_type)
    work_tile_view = DmaViewOp(tsm.result, [zero.result], [size.result], [stride.result], tsm_type)
    out_tile_view = DmaViewOp(tsm.result, [zero.result], [size.result], [stride.result], tsm_type)
    slice_op = DmaSliceOp(work_tile_view.result, src_view.result, [zero.result], [size.result], [stride.result])
    add_op = NnAddOp(work_tile_view.result, work_tile_view.result, tsm_type, NnMemorySpaceAttr.from_name("tsm"))
    deslice_op = DmaDesliceOp(add_op.result, block.args[1], [tid.result], [size.result], [stride.result], mem_type)

    ctx.bind_name(tid.result, "tid")
    ctx.bind_name(tnum.result, "tnum")
    ctx.bind_name(tsm.result, "tsm")
    ctx.bind_name(src_view.result, "src_view")
    ctx.bind_name(work_tile_view.result, "work_tile")
    ctx.bind_name(out_tile_view.result, "out_tile")
    ctx.bind_name(add_op.result, "out_tile")

    stmt = "\n".join(
        [
            emit_c_op(tid, ctx),
            emit_c_op(tnum, ctx),
            emit_c_op(tsm, ctx),
            emit_c_op(src_view, ctx),
            emit_c_op(work_tile_view, ctx),
            emit_c_op(out_tile_view, ctx),
            emit_c_op(slice_op, ctx),
            emit_c_op(add_op, ctx),
            emit_c_op(deslice_op, ctx),
        ]
    )

    assert "S_INT tid = npu_demo::thread_id();" in stmt
    assert "S_INT tnum = npu_demo::thread_num();" in stmt
    assert "Memory<TSM, float> tsm = npu_demo::get_dynamic_memory<TSM>();" in stmt
    assert "Memory<GM, float> src_view = source.view<float>({tid} /*offset*/, {16} /*size*/, {1} /*stride*/);" in stmt
    assert "Memory<TSM, float> work_tile = tsm.view<float>({0} /*offset*/, {16} /*size*/, {1} /*stride*/);" in stmt
    assert "Memory<TSM, float> out_tile = tsm.view<float>({0} /*offset*/, {16} /*size*/, {1} /*stride*/);" in stmt
    assert "slice(work_tile /*dst*/, src_view /*source*/, 0 /*offset*/, 16 /*size*/, 1 /*stride*/);" in stmt
    assert "add<TSM, float, float>(out_tile /*out*/, work_tile /*lhs*/, work_tile /*rhs*/);" in stmt
    assert "deslice(out /*target*/, out_tile /*source*/, tid /*offset*/, 16 /*size*/, 1 /*stride*/);" in stmt
    assert ".view<float>(" in stmt
    assert "npu_demo::view(" not in stmt
    assert "load<" not in stmt
    assert "store<" not in stmt
    assert "launch" not in stmt
    assert "barrier" not in stmt


# EC-027
# 创建者: 小李飞刀
# 最后一次更改: 小李飞刀
# 最近一次运行测试时间: 2026-04-20 02:54:53 +0800
# 最近一次运行成功时间: 2026-04-20 02:54:53 +0800
# 功能说明: 验证 npu_demo 下 tiled matmul 可发射 symbol.for + 2D slice/deslice + kernel.matmul 管线，且多维 slice/deslice 采用 Vector 绑定合同。
# 测试目的: 锁定 target=npu_demo 的二维 tile helper 形态与 `matmul<...>(...)` 调用，确保多维参数不回退到 brace-list 文本并保持 deslice Vector 调用链稳定。
# 使用示例: pytest -q test/dsl/gen_kernel/emit/test_emit.py -k test_emit_c_lowers_npu_demo_tiled_matmul_pipeline
# 对应功能实现文件路径: kernel_gen/dsl/gen_kernel/emit/__init__.py
# 对应 spec 文件路径: spec/dsl/gen_kernel/emit.md
# 对应测试文件路径: test/dsl/gen_kernel/emit/test_emit.py
def test_emit_c_lowers_npu_demo_tiled_matmul_pipeline() -> None:
    def tiled_matmul(lhs: "Tensor[f32, 32, 16]", rhs: "Tensor[f32, 16, 32]") -> "Tensor[f32, 32, 32]":
        out = alloc([32, 32], NumericType.Float32, MemorySpace.GM)
        for m0 in loop(0, 32, 16):
            for n0 in loop(0, 32, 16):
                lhs_tile = slice(lhs, [m0, 0], [16, 16], [1, 1], MemorySpace.TSM)
                rhs_tile = slice(rhs, [0, n0], [16, 16], [1, 1], MemorySpace.TSM)
                partial = matmul(lhs_tile, rhs_tile)
                deslice(partial, out, [m0, n0], [16, 16], [1, 1])
        return out

    block = _lower_built_func(
        tiled_matmul,
        Memory([32, 16], NumericType.Float32),
        Memory([16, 32], NumericType.Float32),
    )
    ctx = _npu_ctx()
    ctx.bind_name(block.args[0], "lhs")
    ctx.bind_name(block.args[1], "rhs")

    stmt = "\n".join(
        filter(
            None,
            (emit_c_op(op, ctx) for op in block.ops if not isinstance(op, func.ReturnOp)),
        )
    )

    assert stmt.count("for (S_INT i") >= 2
    assert re.search(
        r"Memory<GM, float> v\d+ = alloc<GM, float>\(\{32, 32\} /\*shape\*/, \{32, 1\} /\*stride\*/\);",
        stmt,
    )
    assert "long long slice_offset" not in stmt
    assert "long long deslice_offset" not in stmt
    assert re.search(r"Vector\{i\d+, c_0(?:_\d+)?\}", stmt)
    assert re.search(r"Vector\{c_0(?:_\d+)?, i\d+\}", stmt)
    assert re.search(r"Vector\{c_16(?:_\d+)?, c_16(?:_\d+)?\}", stmt)
    assert re.search(r"Vector\{c_1(?:_\d+)?, c_1(?:_\d+)?\}", stmt)
    assert re.search(
        r"slice\(v\d+ /\*dst\*/, lhs /\*source\*/, Vector\{i\d+, c_0(?:_\d+)?\} /\*offset\*/, Vector\{c_16(?:_\d+)?, c_16(?:_\d+)?\} /\*size\*/, Vector\{c_1(?:_\d+)?, c_1(?:_\d+)?\} /\*stride\*/\);",
        stmt,
    )
    assert re.search(
        r"slice\(v\d+ /\*dst\*/, rhs /\*source\*/, Vector\{c_0(?:_\d+)?, i\d+\} /\*offset\*/, Vector\{c_16(?:_\d+)?, c_16(?:_\d+)?\} /\*size\*/, Vector\{c_1(?:_\d+)?, c_1(?:_\d+)?\} /\*stride\*/\);",
        stmt,
    )
    assert re.search(
        r"matmul<[^>]+>\(v\d+ /\*out\*/, v\d+ /\*lhs\*/, v\d+ /\*rhs\*/\);",
        stmt,
    )
    assert re.search(
        r"deslice\(v\d+ /\*target\*/, v\d+ /\*source\*/, Vector\{i\d+, i\d+\} /\*offset\*/, Vector\{c_16(?:_\d+)?, c_16(?:_\d+)?\} /\*size\*/, Vector\{c_1(?:_\d+)?, c_1(?:_\d+)?\} /\*stride\*/\);",
        stmt,
    )
    assert "nn.matmul" not in stmt
    assert "arch.launch_kernel" not in stmt
