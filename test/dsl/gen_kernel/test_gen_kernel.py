"""gen_kernel tests.

创建者: 金铲铲大作战
最后一次更改: 金铲铲大作战

功能说明:
- 覆盖 func.func 到目标函数源码的组装行为。

使用示例:
- pytest -q test/dsl/gen_kernel/test_gen_kernel.py

覆盖率信息:
- 覆盖率命令: coverage run -m pytest -q test/dsl/gen_kernel/emit/test_emit.py test/dsl/gen_kernel/test_gen_kernel.py && coverage report --include=kernel_gen/dsl/gen_kernel/emit/__init__.py,kernel_gen/dsl/gen_kernel/gen_kernel.py -m
- 覆盖率结果: emit 100%, gen_kernel 100%（2026-03-23 22:45:14 +0800）
- 达标线: 95%

关联文件:
- 功能实现: kernel_gen/dsl/gen_kernel/gen_kernel.py
- Spec 文档: spec/dsl/gen_kernel/gen_kernel.md
- 测试文件: test/dsl/gen_kernel/test_gen_kernel.py
"""

from __future__ import annotations

from pathlib import Path
import os
import shutil
import sys
import importlib
import subprocess
import tempfile
from types import SimpleNamespace

import pytest
from xdsl.context import Context
from xdsl.dialects import arith, func, scf
from xdsl.dialects.builtin import (
    ArrayAttr,
    BFloat16Type,
    DictionaryAttr,
    FunctionType,
    IndexType,
    IntAttr,
    IntegerAttr,
    ModuleOp,
    StringAttr,
    SymbolRefAttr,
    UnrealizedConversionCastOp,
    f16,
    f32,
    f64,
    i1,
    i32,
)
from xdsl.ir import Block, Operation, Region
from xdsl.irdl import IRDLOperation, irdl_op_definition, result_def
from xdsl.parser import Parser

REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from kernel_gen.context import build_default_context
from kernel_gen.dialect.arch import (
    ArchBarrierOp,
    ArchGetDynamicMemoryOp,
    ArchGetThreadIdOp,
    ArchGetThreadNumOp,
    ArchLaunchOp,
    ArchScopeAttr,
    ArchVisibilityAttr,
)
from kernel_gen.dialect.dma import DmaAllocOp, DmaCopyOp, DmaDesliceOp, DmaFillOp, DmaSliceOp, DmaViewOp
from kernel_gen.dialect.kernel import KernelBinaryElewiseOp
from kernel_gen.dialect.nn import NnAddOp, NnMemorySpaceAttr, NnMemoryType
from kernel_gen.dialect.symbol import (
    SymbolAddOp,
    SymbolCastOp,
    SymbolConstOp,
    SymbolDimType,
    SymbolForOp,
    SymbolGetDimOp,
    SymbolIterType,
    SymbolValueType,
)
from kernel_gen.dialect.tuner import TunerCostOp, TunerParamOp
from kernel_gen.dsl.gen_kernel import EmitCContext, EmitCError, KernelEmitter, dsl_gen_kernel, emit_c, emit_c_op, emit_c_value, GenKernelError, gen_kernel
from kernel_gen.dsl.mlir_gen import build_func_op, mlir_gen
from kernel_gen.operation.dma import alloc, deslice, slice
from kernel_gen.operation.nn import matmul
from kernel_gen.operation.scf import loop
from kernel_gen.passes.buffer_results_to_out_params import BufferResultsToOutParamsPass
from kernel_gen.passes.lowering.nn_lowering import NnLoweringPass
from kernel_gen.passes.outline_device_kernel import OutlineDeviceKernelPass
from kernel_gen.symbol_variable.memory import Memory, MemorySpace
from kernel_gen.symbol_variable.symbol_dim import SymbolDim
from kernel_gen.symbol_variable.type import NumericType

gen_kernel_module = importlib.import_module("kernel_gen.dsl.gen_kernel")
gen_kernel_entry_module = importlib.import_module("kernel_gen.dsl.gen_kernel.gen_kernel")
emit_context_module = importlib.import_module("kernel_gen.dsl.gen_kernel.emit_context")
tile_test_shared = importlib.import_module("test.pass.tile.shared")
tile_analysis_helpers = SimpleNamespace(
    _build_module=tile_test_shared.build_elementwise_module,
    _build_broadcast_module=tile_test_shared.build_broadcast_module,
    _build_matmul_module=tile_test_shared.build_matmul_module,
)
tile_analysis_module = importlib.import_module("kernel_gen.passes.tile.analysis")
tile_elewise_module = importlib.import_module("kernel_gen.passes.tile.elewise")
tile_reduce_module = importlib.import_module("kernel_gen.passes.tile.reduce")
tile_analysis_impl = importlib.import_module("kernel_gen.passes.tile.analysis")
tile_reduce_impl = importlib.import_module("kernel_gen.passes.tile.reduce")
TileAnalysisPass = tile_analysis_module.TileAnalysisPass
TileElewisePass = tile_elewise_module.TileElewisePass
TileReducePass = tile_reduce_module.TileReducePass


@irdl_op_definition
class UnsupportedOp(IRDLOperation):
    name = "test.unsupported"
    result = result_def(i32)

    def __init__(self: "UnsupportedOp") -> None:
        super().__init__(result_types=[i32])


@irdl_op_definition
class FakeSymbolDimOp(IRDLOperation):
    """测试用的 `!symbol.dim<"...">` 产生 op。"""

    name = "test.fake_symbol_dim"
    result = result_def(SymbolDimType)

    def __init__(self: "FakeSymbolDimOp", name: str) -> None:
        super().__init__(result_types=[SymbolDimType.from_name(name)])


@irdl_op_definition
class FakeSymbolValueOp(IRDLOperation):
    """测试用的 `!symbol.int<"...">` 产生 op。"""

    name = "test.fake_symbol_value"
    result = result_def(SymbolValueType)

    def __init__(self: "FakeSymbolValueOp", expr: str) -> None:
        super().__init__(result_types=[SymbolValueType.from_expr(expr)])


def _ctx() -> EmitCContext:
    return EmitCContext(config={"target": "cpu"})


def _npu_ctx() -> EmitCContext:
    return EmitCContext(config={"target": "npu_demo"})


def test_gen_kernel_public_modules_exist_and_old_legacy_loader_path_is_gone() -> None:
    assert gen_kernel_entry_module is not None
    assert emit_context_module is not None
    assert importlib.util.find_spec("kernel_gen.dsl.gen_kernel._legacy") is None


def _parse_npu_demo_launch_module(text: str) -> ModuleOp:
    """解析 `npu_demo` launch 测试 IR。

    创建者: jcc你莫辜负
    最后一次更改: jcc你莫辜负

    功能说明:
    - 复用仓库默认 dialect 上下文解析单函数 launch module。
    - 为 outline -> gen_kernel 的回归测试提供最小文本入口。

    使用示例:
    - module = _parse_npu_demo_launch_module(ir_text)

    关联文件:
    - spec: spec/dsl/gen_kernel/gen_kernel.md
    - test: test/dsl/gen_kernel/test_gen_kernel.py
    - 功能实现: kernel_gen/dsl/gen_kernel/gen_kernel.py
    """

    return Parser(build_default_context(), text).parse_module()


def _make_memory_type(shape: list[int], stride: list[int], element_type: object = i32, space: str = "global") -> NnMemoryType:
    return NnMemoryType(
        ArrayAttr([IntAttr(dim) for dim in shape]),
        ArrayAttr([IntAttr(dim) for dim in stride]),
        element_type,
        NnMemorySpaceAttr.from_name(space),
    )


def _tensor_arg(shape: list[int | str], dtype: NumericType = NumericType.Int32) -> Memory:
    return Memory(shape, dtype)


def _arg_attrs(*names: str) -> ArrayAttr[DictionaryAttr]:
    return ArrayAttr([DictionaryAttr({"name": StringAttr(name)}) for name in names])


def _func(name: str, input_types: list[object], result_types: list[object], block: Block, arg_names: tuple[str, ...]) -> func.FuncOp:
    func_type = FunctionType.from_lists(input_types, result_types)
    return func.FuncOp(name, func_type, Region(block), arg_attrs=_arg_attrs(*arg_names))


def _alloc_ops(source_memory: object, mem_type: NnMemoryType) -> tuple[list[object], DmaAllocOp]:
    shape_ops = [SymbolGetDimOp(source_memory, axis) for axis, _ in enumerate(mem_type.shape.data)]
    alloc = DmaAllocOp([op.result for op in shape_ops], mem_type)
    return [*shape_ops, alloc], alloc


def _make_npu_demo_add_barrier_module(
    *,
    body_name: str = "add_barrier_body",
    wrapper_name: str = "add_barrier",
    callee_name: str | None = None,
    callee_attr: SymbolRefAttr | None = None,
    block_extent_expr: str = "1",
    thread_extent_expr: str = "1",
    subthread_extent_expr: str = "1",
    shared_memory_size_expr: str = "0",
    barrier_scope: str = "block",
    barrier_visibility_names: tuple[str, ...] = ("tsm", "tlm"),
    tlm_space: str = "tlm1",
    emit_wrapper_return: bool = True,
    include_body: bool = True,
    include_wrapper: bool = True,
    top_level_extra_ops: tuple[Operation, ...] = (),
) -> ModuleOp:
    """构造 `npu_demo` launch wrapper/body 受控 module。

    创建者: 小李飞刀
    最后一次更改: 金铲铲大作战

    功能说明:
    - 生成 `body + wrapper` 双函数 module，覆盖 `gen_kernel(target="npu_demo")` 的受控 `builtin.module` 子集。
    - 允许调用方追加 helper `func.func`，并按 module 中的出现顺序输出源码。
    - body 固定包含 `thread/view/slice/barrier/add/deslice` 骨架，wrapper 固定包含 `arch.launch + func.return`。
    - 允许调用方显式切换 `tlm1/tlm2/tlm3`，用于锁定 npu_demo output tile 的真实动态内存空间。

    使用示例:
    - module = _make_npu_demo_add_barrier_module()

    关联文件:
    - spec: spec/dsl/gen_kernel/gen_kernel.md
    - test: test/dsl/gen_kernel/test_gen_kernel.py
    - 功能实现: test/dsl/gen_kernel/test_gen_kernel.py
    """

    gm_type = _make_memory_type([64], [1], element_type=f32)
    tsm_buffer_type = _make_memory_type([128], [1], element_type=f32, space="tsm")
    tlm_buffer_type = _make_memory_type([64], [1], element_type=f32, space=tlm_space)
    tsm_tile_type = _make_memory_type([16], [1], element_type=f32, space="tsm")
    tlm_tile_type = _make_memory_type([16], [1], element_type=f32, space=tlm_space)
    gm_tile_type = _make_memory_type([16], [1], element_type=f32, space="global")
    barrier_visibility = ArrayAttr([ArchVisibilityAttr.from_name(space_name) for space_name in barrier_visibility_names])

    body_block = Block(arg_types=[IndexType(), gm_type, gm_type, gm_type])
    thread_offset = FakeSymbolValueOp("thread_id * 16")
    rhs_offset = FakeSymbolValueOp("64 + thread_id * 16")
    zero = FakeSymbolValueOp("0")
    size = FakeSymbolValueOp("16")
    stride = FakeSymbolValueOp("1")
    tid = ArchGetThreadIdOp()
    tnum = ArchGetThreadNumOp()
    tsm = ArchGetDynamicMemoryOp(NnMemorySpaceAttr.from_name("tsm"), tsm_buffer_type)
    tlm = ArchGetDynamicMemoryOp(NnMemorySpaceAttr.from_name(tlm_space), tlm_buffer_type)
    lhs_gm = DmaViewOp(body_block.args[1], [thread_offset.result], [size.result], [stride.result], gm_tile_type)
    rhs_gm = DmaViewOp(body_block.args[2], [thread_offset.result], [size.result], [stride.result], gm_tile_type)
    lhs_tsm = DmaViewOp(tsm.result, [thread_offset.result], [size.result], [stride.result], tsm_tile_type)
    rhs_tsm = DmaViewOp(tsm.result, [rhs_offset.result], [size.result], [stride.result], tsm_tile_type)
    out_tsm = DmaViewOp(tsm.result, [thread_offset.result], [size.result], [stride.result], tsm_tile_type)
    lhs_slice = DmaSliceOp(lhs_tsm.result, lhs_gm.result, [zero.result], [size.result], [stride.result])
    rhs_slice = DmaSliceOp(rhs_tsm.result, rhs_gm.result, [zero.result], [size.result], [stride.result])
    barrier0 = ArchBarrierOp(ArchScopeAttr.from_name(barrier_scope), barrier_visibility)
    add = KernelBinaryElewiseOp(
        out_tsm.result,
        lhs_tsm.result,
        rhs_tsm.result,
        kind="add",
        space=NnMemorySpaceAttr.from_name("tsm"),
    )
    barrier1 = ArchBarrierOp(ArchScopeAttr.from_name(barrier_scope), barrier_visibility)
    deslice = DmaDesliceOp(out_tsm.result, body_block.args[3], [thread_offset.result], [size.result], [stride.result], gm_type)
    body_block.add_ops(
        [
            thread_offset,
            rhs_offset,
            zero,
            size,
            stride,
            tid,
            tnum,
            tsm,
            tlm,
            lhs_gm,
            rhs_gm,
            lhs_tsm,
            rhs_tsm,
            out_tsm,
            lhs_slice,
            rhs_slice,
            barrier0,
            add,
            barrier1,
            deslice,
            func.ReturnOp(),
        ]
    )
    body_func = _func(body_name, [IndexType(), gm_type, gm_type, gm_type], [], body_block, ("ctx", "lhs", "rhs", "out"))

    wrapper_block = Block(arg_types=[gm_type, gm_type, gm_type])
    block_extent = FakeSymbolValueOp(block_extent_expr)
    thread_extent = FakeSymbolValueOp(thread_extent_expr)
    subthread_extent = FakeSymbolValueOp(subthread_extent_expr)
    shared_memory_size = FakeSymbolValueOp(shared_memory_size_expr)
    launch = ArchLaunchOp(
        callee_attr or SymbolRefAttr(callee_name or body_name),
        block_extent.result,
        thread_extent.result,
        subthread_extent.result,
        shared_memory_size.result,
        (wrapper_block.args[0], wrapper_block.args[1], wrapper_block.args[2]),
    )
    wrapper_ops: list[Operation] = [block_extent, thread_extent, subthread_extent, shared_memory_size, launch]
    if emit_wrapper_return:
        wrapper_ops.append(func.ReturnOp())
    wrapper_block.add_ops(wrapper_ops)
    wrapper_func = _func(wrapper_name, [gm_type, gm_type, gm_type], [], wrapper_block, ("lhs", "rhs", "out"))
    top_level_ops: list[Operation] = []
    if include_body:
        top_level_ops.append(body_func)
    if include_wrapper:
        top_level_ops.append(wrapper_func)
    top_level_ops.extend(top_level_extra_ops)
    return ModuleOp(top_level_ops)


def _make_npu_demo_helper_func(name: str = "npu_demo_helper") -> func.FuncOp:
    """构造 `npu_demo` 受控 module 的 helper `func.func`。

    创建者: 朽木露琪亚
    最后一次更改: 朽木露琪亚

    功能说明:
    - 为 `target="npu_demo"` 的 module 顺序输出测试提供一个最小 helper。
    - 该 helper 不含 `arch.launch`，因此必须走通用 `func.func` 发射路径。

    使用示例:
    - helper = _make_npu_demo_helper_func()

    关联文件:
    - spec: spec/dsl/gen_kernel/gen_kernel.md
    - test: test/dsl/gen_kernel/test_gen_kernel.py
    - 功能实现: test/dsl/gen_kernel/test_gen_kernel.py
    """

    block = Block()
    block.add_ops([func.ReturnOp()])
    return _func(name, [], [], block, ())


def _make_npu_demo_cost_func(name: str, cost_kind: str) -> func.FuncOp:
    """构造 `npu_demo` sibling cost `func.func`。

    创建者: 朽木露琪亚
    最后一次更改: 朽木露琪亚

    功能说明:
    - 为 `target="npu_demo"` 的 module 提供最小 sibling cost function，覆盖
      `tuner.cost -> symbol.add -> func.return !symbol.int` 的端到端源码路径。
    - 当前固定使用 `kernel.add` 对应的 cost helper，并通过 `%total` 累计值锁定
      `S_INT total = ...; return total;` 的公开源码合同。

    使用示例:
    - cost_func = _make_npu_demo_cost_func("_cost_compute_add_barrier_body", "compute")

    关联文件:
    - spec: spec/dsl/gen_kernel/gen_kernel.md
    - test: test/dsl/gen_kernel/test_gen_kernel.py
    - 功能实现: test/dsl/gen_kernel/test_gen_kernel.py
    """

    gm_type = _make_memory_type([64], [1], element_type=f32)
    local_cost_type = SymbolValueType.from_expr("LOCAL")
    total_type = SymbolValueType.from_expr("total")
    block = Block(arg_types=[gm_type, gm_type, gm_type])
    cost = TunerCostOp(
        [block.args[2], block.args[0], block.args[1]],
        cost_kind=StringAttr(cost_kind),
        op_name=StringAttr("kernel.add"),
        result_type=local_cost_type,
    )
    total = SymbolAddOp(cost.result, cost.result, total_type)
    block.add_ops([cost, total, func.ReturnOp(total.result)])
    return _func(name, [gm_type, gm_type, gm_type], [total_type], block, ("lhs", "rhs", "out"))


def _make_npu_demo_cost_function_module() -> ModuleOp:
    """构造同时包含 kernel 与 sibling cost functions 的 `npu_demo` module。

    创建者: 朽木露琪亚
    最后一次更改: 朽木露琪亚

    功能说明:
    - 复用 `body + wrapper` 受控 module 骨架，并追加 `compute/memory` 两个 sibling cost functions。
    - 供 `gen_kernel(target="npu_demo")` 的完整 module 源码与 compile-only 回归复用。

    使用示例:
    - module = _make_npu_demo_cost_function_module()

    关联文件:
    - spec: spec/dsl/gen_kernel/gen_kernel.md
    - test: test/dsl/gen_kernel/test_gen_kernel.py
    - 功能实现: test/dsl/gen_kernel/test_gen_kernel.py
    """

    return _make_npu_demo_add_barrier_module(
        top_level_extra_ops=(
            _make_npu_demo_cost_func("_cost_compute_add_barrier_body", "compute"),
            _make_npu_demo_cost_func("_cost_memory_add_barrier_body", "memory"),
        )
    )


def _lower_func(func_op: func.FuncOp) -> func.FuncOp:
    """对单个 `func.func` 执行 `NnLoweringPass` 并返回改写后的函数。

    创建者: 小李飞刀
    最后一次更改: 朽木露琪亚

    功能说明:
    - 为 I3 的 pass-after IR codegen 测试提供最小包装。
    - 直接在 module 内原地执行 lowering，并返回同一函数实例。

    使用示例:
    - lowered = _lower_func(func_op)

    关联文件:
    - spec: spec/dsl/gen_kernel/gen_kernel.md
    - test: test/dsl/gen_kernel/test_gen_kernel.py
    - 功能实现: test/dsl/gen_kernel/test_gen_kernel.py
    """

    module = ModuleOp([func_op])
    NnLoweringPass().run(module)
    return next(op for op in module.ops if isinstance(op, func.FuncOp))


def _rewrite_func(func_op: func.FuncOp) -> func.FuncOp:
    """对单个 `func.func` 执行 `BufferResultsToOutParamsPass` 并返回改写后的函数。

    创建者: jcc你莫辜负
    最后一次更改: 朽木露琪亚

    功能说明:
    - 为 O5 的 rewrite-after-IR codegen 测试提供最小包装。
    - 直接在 module 内原地执行 pass，并返回同一函数实例。

    使用示例:
    - rewritten = _rewrite_func(func_op)

    关联文件:
    - spec: spec/dsl/gen_kernel/gen_kernel.md
    - test: test/dsl/gen_kernel/test_gen_kernel.py
    - 功能实现: test/dsl/gen_kernel/test_gen_kernel.py
    """

    module = ModuleOp([func_op])
    BufferResultsToOutParamsPass().run(module)
    return next(op for op in module.ops if isinstance(op, func.FuncOp))


def _lower_and_rewrite_func(func_op: func.FuncOp) -> func.FuncOp:
    """对单个 `func.func` 先 lowering 再执行 out-param rewrite。

    创建者: jcc你莫辜负
    最后一次更改: jcc你莫辜负

    功能说明:
    - 固定公开成功链路为 `NnLoweringPass -> BufferResultsToOutParamsPass`。
    - 用于 O5 的 `build_func_op -> pass -> gen_kernel` 黑盒闭环测试。

    使用示例:
    - lowered = _lower_and_rewrite_func(func_op)

    关联文件:
    - spec: spec/dsl/gen_kernel/gen_kernel.md
    - test: test/dsl/gen_kernel/test_gen_kernel.py
    - 功能实现: test/dsl/gen_kernel/test_gen_kernel.py
    """

    module = ModuleOp([func_op])
    NnLoweringPass().run(module)
    BufferResultsToOutParamsPass().run(module)
    return next(op for op in module.ops if isinstance(op, func.FuncOp))


def _tile_analysis_func(module: ModuleOp) -> func.FuncOp:
    """对单个 `func.func` 执行 tile-analysis。

    创建者: 金铲铲大作战
    最后一次更改: 金铲铲大作战

    功能说明:
    - 为 tile after-IR 负例测试提供只带 `tile.analysis + tile.tile_exprs` 的最小包装。
    - 返回被 pass 标注后的函数，便于后续人为构造缺环路/缺 `tuner.param` 的 malformed IR。

    使用示例:
    - func_op = _tile_analysis_func(tile_analysis_helpers._build_module())

    关联文件:
    - spec: spec/dsl/gen_kernel/gen_kernel.md
    - test: test/dsl/gen_kernel/test_gen_kernel.py
    - 功能实现: test/dsl/gen_kernel/test_gen_kernel.py
    """

    ctx = Context()
    TileAnalysisPass().apply(ctx, module)
    return next(op for op in module.ops if isinstance(op, func.FuncOp))


def _tile_elewise_func(module: ModuleOp) -> func.FuncOp:
    """对单个 `func.func` 先执行 tile-analysis 再执行 tile-elewise。

    创建者: 小李飞刀
    最后一次更改: 小李飞刀

    功能说明:
    - 为 tile-elewise 代码生成测试提供最小组合包装。
    - 返回被 pass 改写后的函数，便于后续交给 `gen_kernel(...)`。

    使用示例:
    - func_op = _tile_elewise_func(tile_analysis_helpers._build_module())

    关联文件:
    - spec: spec/dsl/gen_kernel/gen_kernel.md
    - test: test/dsl/gen_kernel/test_gen_kernel.py
    - 功能实现: test/dsl/gen_kernel/test_gen_kernel.py
    """

    ctx = Context()
    TileAnalysisPass().apply(ctx, module)
    TileElewisePass().apply(ctx, module)
    return next(op for op in module.ops if isinstance(op, func.FuncOp))


def _tile_reduce_func(module: ModuleOp) -> func.FuncOp:
    """对单个 `func.func` 先执行 tile-analysis 再执行 tile-reduce。

    创建者: 金铲铲大作战
    最后一次更改: 金铲铲大作战

    功能说明:
    - 为 tile-reduce 代码生成/结构测试提供最小组合包装。
    - 返回被 pass 改写后的函数，便于后续交给 `gen_kernel(...)` 或直接断言 IR。

    使用示例:
    - func_op = _tile_reduce_func(tile_analysis_helpers._build_matmul_module())

    关联文件:
    - spec: spec/dsl/gen_kernel/gen_kernel.md
    - test: test/dsl/gen_kernel/test_gen_kernel.py
    - 功能实现: test/dsl/gen_kernel/test_gen_kernel.py
    """

    ctx = Context()
    TileAnalysisPass().apply(ctx, module)
    TileReducePass().apply(ctx, module)
    return next(op for op in module.ops if isinstance(op, func.FuncOp))


def test_tile_gen_kernel_paths_use_kernel_gen_tile_modules() -> None:
    """验证 tile family 的 canonical helper / implementation path 已收口到 `kernel_gen.passes.tile.*`。

    创建者: 金铲铲大作战
    最后一次更改: 金铲铲大作战

    功能说明:
    - 锁定 `tile-analysis` / `tile-elewise` / `tile-reduce` 的真实实现落点已迁到 `kernel_gen.passes.tile.*`。
    - 同时验证三个 `Tile*Pass` 的类定义也已经收口到 `kernel_gen.passes.tile.*`。

    使用示例:
    - pytest -q test/dsl/gen_kernel/test_gen_kernel.py -k test_tile_gen_kernel_paths_use_kernel_gen_tile_modules

    关联文件:
    - spec: [spec/pass/tile/README.md](spec/pass/tile/README.md)
    - test: [test/dsl/gen_kernel/test_gen_kernel.py](test/dsl/gen_kernel/test_gen_kernel.py)
    - 功能实现: [kernel_gen/passes/tile/analysis.py](kernel_gen/passes/tile/analysis.py)
    - 功能实现: [kernel_gen/passes/tile/elewise.py](kernel_gen/passes/tile/elewise.py)
    - 功能实现: [kernel_gen/passes/tile/reduce.py](kernel_gen/passes/tile/reduce.py)
    """

    assert callable(tile_analysis_impl.get_tile_analysis_pass_patterns)
    assert callable(tile_elewise_module.get_tile_elewise_pass_patterns)
    assert callable(tile_reduce_impl.get_tile_reduce_pass_patterns)
    assert TileAnalysisPass.__module__ == "kernel_gen.passes.tile.analysis"
    assert TileElewisePass.__module__ == "kernel_gen.passes.tile.elewise"
    assert TileReducePass.__module__ == "kernel_gen.passes.tile.reduce"


def _run_local_compile_command(command: list[str]) -> subprocess.CompletedProcess[str]:
    """执行当前测试文件使用的本地编译命令。

    创建者: 小李飞刀
    最后一次更改: 小李飞刀

    功能说明:
    - 为 `test_gen_kernel.py` 内的 compile-only / compile-and-run helper 提供统一的 `g++` 调用入口。
    - 固定返回 `subprocess.CompletedProcess[str]`，便于测试文件内集中处理 stdout / stderr / returncode。
    - 不依赖当前文件之外的非公开 API。

    使用示例:
    - result = _run_local_compile_command(["g++", "-std=c++17", "demo.cpp", "-o", "demo"])

    关联文件:
    - spec: spec/dsl/gen_kernel/gen_kernel.md
    - test: test/dsl/gen_kernel/test_gen_kernel.py
    - 功能实现: test/dsl/gen_kernel/test_gen_kernel.py
    """

    return subprocess.run(
        command,
        check=False,
        capture_output=True,
        text=True,
    )


def _compile_and_run(source: str) -> None:
    """编译并运行 `gen_kernel` 生成的 C++ 片段。

    创建者: 小李飞刀
    最后一次更改: 小李飞刀

    功能说明:
    - 使用 `g++ -std=c++17` 编译临时源码，并执行生成的可执行文件。
    - 编译步骤复用当前测试文件内的 `_run_local_compile_command(...)`。
    - 用于锁定 `gen_kernel` 生成的源码片段不仅可生成，而且可实际编译运行。

    使用示例:
    - _compile_and_run("#include <cstdint>\\nint main() { return 0; }")

    关联文件:
    - spec: spec/dsl/gen_kernel/gen_kernel.md
    - test: test/dsl/gen_kernel/test_gen_kernel.py
    - 功能实现: test/dsl/gen_kernel/test_gen_kernel.py
    """

    with tempfile.TemporaryDirectory() as tmpdir:
        source_path = Path(tmpdir) / "gen_kernel_conv_test.cpp"
        binary_path = Path(tmpdir) / "gen_kernel_conv_test"
        source_path.write_text(source, encoding="utf-8")

        compile_result = _run_local_compile_command(
            [
                "g++",
                "-std=c++17",
                "-I",
                str(REPO_ROOT),
                str(source_path),
                "-o",
                str(binary_path),
            ]
        )
        if compile_result.returncode != 0:
            raise AssertionError(
                "g++ compile failed:\n"
                f"stdout:\n{compile_result.stdout}\n"
                f"stderr:\n{compile_result.stderr}"
            )

        run_result = subprocess.run(
            [str(binary_path)],
            check=False,
            capture_output=True,
            text=True,
        )
        if run_result.returncode != 0:
            raise AssertionError(
                "compiled program failed:\n"
                f"stdout:\n{run_result.stdout}\n"
                f"stderr:\n{run_result.stderr}"
            )


def _compile_only(source: str) -> None:
    """仅编译 `gen_kernel` 生成的 C++ 片段。

    创建者: 金铲铲大作战
    最后一次更改: 小李飞刀

    功能说明:
    - 使用 `g++ -std=c++17 -c` 编译临时源码，验证目标 include/签名可通过编译。
    - 编译步骤复用当前测试文件内的 `_run_local_compile_command(...)`。
    - 用于 `target="npu_demo"` 的“只编译”验证，不执行链接与运行。

    使用示例:
    - _compile_only('#include "include/npu_demo/npu_demo.h"\\nvoid demo_kernel(...) {}')

    关联文件:
    - spec: spec/dsl/gen_kernel/gen_kernel.md
    - test: test/dsl/gen_kernel/test_gen_kernel.py
    - 功能实现: test/dsl/gen_kernel/test_gen_kernel.py
    """

    with tempfile.TemporaryDirectory() as tmpdir:
        source_path = Path(tmpdir) / "gen_kernel_npu_demo_test.cpp"
        object_path = Path(tmpdir) / "gen_kernel_npu_demo_test.o"
        source_path.write_text(source, encoding="utf-8")

        compile_result = _run_local_compile_command(
            [
                "g++",
                "-std=c++17",
                # GCC 13 在 npu_demo 的 DMA 模板上会在树优化/CFG cleanup 阶段触发 ICE；
                # 这里关闭几组相关优化，保留“可编译”校验本身，不影响源码语义检查。
                "-fno-tree-ccp",
                "-fno-tree-dce",
                "-fno-tree-forwprop",
                "-fno-tree-scev-cprop",
                "-fno-tree-vrp",
                "-fno-tree-ter",
                "-I",
                str(REPO_ROOT),
                "-c",
                str(source_path),
                "-o",
                str(object_path),
            ]
        )
        if compile_result.returncode != 0:
            raise AssertionError(
                "g++ compile failed:\n"
                f"stdout:\n{compile_result.stdout}\n"
                f"stderr:\n{compile_result.stderr}"
            )


def _compile_and_run_npu_demo_add_barrier_source(source: str, *, prove_barrier_runtime: bool) -> None:
    """编译并运行 `npu_demo add+barrier` 生成源码。

    创建者: 小李飞刀
    最后一次更改: 小李飞刀

    功能说明:
    - 把 `gen_kernel(target="npu_demo")` 生成的 `add_barrier` 双函数源码拼接到最小可执行程序中。
    - 在可执行程序里绑定 `add_barrier` / `add_barrier_body` 符号，锁定生成入口签名与源码可编译性。
    - 可选追加“线程 0 故意慢一步”的 barrier 探针，证明其他线程不会越过同一次 launch 的共享 barrier。
    - 编译失败时追加 g++ 版本与命令信息，便于复现链接异常。

    使用示例:
    - _compile_and_run_npu_demo_add_barrier_source(source, prove_barrier_runtime=True)

    关联文件:
    - spec: spec/dsl/gen_kernel/gen_kernel.md
    - test: test/dsl/gen_kernel/test_gen_kernel.py
    - 功能实现: test/dsl/gen_kernel/test_gen_kernel.py
    """

    barrier_probe = ""
    barrier_assert = ""
    if prove_barrier_runtime:
        barrier_probe = r"""
static void slow_barrier_probe(
    npu_demo::KernelContext& ctx,
    std::atomic<long long>* entered,
    long long* after_values) {
    const long long tid = ctx.thread_id();
    if (tid == 0) {
        std::this_thread::sleep_for(std::chrono::milliseconds(100));
    }
    entered->fetch_add(1);
    ctx.barrier({BarrierVisibility::TSM, BarrierVisibility::TLM}, BarrierScope::BLOCK);
    after_values[tid] = entered->load();
}
"""
        barrier_assert = r"""
    std::atomic<long long> entered(0);
    long long after_values[4] = {-1, -1, -1, -1};
    if (npu_demo::launch<1, 4, 1, 0>(slow_barrier_probe, &entered, after_values) != StatusCode::kOk) {
        return fail(4);
    }
    for (long long i = 0; i < 4; ++i) {
        if (after_values[i] != 4) {
            return fail(5);
        }
    }
"""

    cpp_source = f"""
#include <atomic>
#include <chrono>
#include <thread>

{source}

static int fail(int code) {{ return code; }}
{barrier_probe}

int main() {{
    float lhs_data[64];
    float rhs_data[64];
    float out_data[64] = {{0}};
    long long shape[1] = {{64}};
    long long stride[1] = {{1}};
    for (int i = 0; i < 64; ++i) {{
        lhs_data[i] = static_cast<float>(i + 1);
        rhs_data[i] = static_cast<float>(100 + i);
    }}

    Memory<MemorySpace::GM, float> lhs(lhs_data, shape, stride, 1, MemoryFormat::Norm);
    Memory<MemorySpace::GM, float> rhs(rhs_data, shape, stride, 1, MemoryFormat::Norm);
    Memory<MemorySpace::GM, float> out(out_data, shape, stride, 1, MemoryFormat::Norm);
    auto generated_entry = &add_barrier;
    auto generated_body = &add_barrier_body;
    if (generated_entry == nullptr || generated_body == nullptr) {{
        return fail(1);
    }}
    if (lhs.rank() == 0) {{
        generated_entry(lhs, rhs, out);
        return fail(2);
    }}
{barrier_assert}
    return 0;
}}
"""

    gpp_path = shutil.which("g++")
    if gpp_path is None:
        raise AssertionError("g++ not found in PATH; please install g++ to reproduce this test")

    gpp_version = subprocess.run(
        ["g++", "--version"],
        check=False,
        capture_output=True,
        text=True,
    )
    gpp_version_text = gpp_version.stdout.strip() or gpp_version.stderr.strip()

    with tempfile.TemporaryDirectory() as tmpdir:
        source_path = Path(tmpdir) / "gen_kernel_npu_demo_add_barrier.cpp"
        binary_path = Path(tmpdir) / "gen_kernel_npu_demo_add_barrier"
        source_path.write_text(cpp_source, encoding="utf-8")

        compile_cmd = [
            "g++",
            "-std=c++17",
            "-pthread",
            "-I",
            str(REPO_ROOT),
            str(source_path),
            "-o",
            str(binary_path),
        ]

        compile_result = _run_local_compile_command(compile_cmd)
        if compile_result.returncode != 0:
            fallback_cmd = [*compile_cmd, "-latomic"]
            fallback_result = _run_local_compile_command(fallback_cmd)
            if fallback_result.returncode != 0:
                raise AssertionError(
                    "g++ compile failed:\n"
                    f"command:\n{' '.join(compile_cmd)}\n"
                    f"fallback:\n{' '.join(fallback_cmd)}\n"
                    f"g++ version:\n{gpp_version_text}\n"
                    f"stdout:\n{compile_result.stdout}\n"
                    f"stderr:\n{compile_result.stderr}\n"
                    f"fallback stdout:\n{fallback_result.stdout}\n"
                    f"fallback stderr:\n{fallback_result.stderr}"
                )

        run_result = subprocess.run(
            [str(binary_path)],
            check=False,
            capture_output=True,
            text=True,
            timeout=5.0,
        )
        if run_result.returncode != 0:
            raise AssertionError(
                "compiled program failed:\n"
                f"returncode:\n{run_result.returncode}\n"
                f"stdout:\n{run_result.stdout}\n"
                f"stderr:\n{run_result.stderr}"
            )


# GK-S7-004
# 创建者: 小李飞刀
# 最后一次更改: 小李飞刀
# 功能说明: 直接锁定 test_gen_kernel 本地编译 helper 继续复用当前文件内统一编译入口。
# 测试目的: 防止 `_compile_only` / `_compile_and_run` 回退到各自维护独立编译流程，只靠人工读代码发现分叉。
# 使用示例: pytest -q test/dsl/gen_kernel/test_gen_kernel.py -k test_gen_kernel_local_compile_helpers_delegate_local_compile_runner
# 对应功能实现文件路径: test/dsl/gen_kernel/test_gen_kernel.py
# 对应 spec 文件路径: spec/dsl/gen_kernel/gen_kernel.md
# 对应测试文件路径: test/dsl/gen_kernel/test_gen_kernel.py
def test_gen_kernel_local_compile_helpers_delegate_local_compile_runner(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    compile_calls: list[tuple[str, ...]] = []
    runtime_calls: list[tuple[str, ...]] = []

    def _fake_run_local_compile_command(command: object) -> subprocess.CompletedProcess[str]:
        assert isinstance(command, list)
        compile_calls.append(tuple(str(part) for part in command))
        return subprocess.CompletedProcess(command, 0, stdout="", stderr="")

    def _fake_run(command: object, **kwargs: object) -> subprocess.CompletedProcess[str]:
        assert isinstance(command, list)
        runtime_calls.append(tuple(str(part) for part in command))
        assert kwargs["check"] is False
        assert kwargs["capture_output"] is True
        assert kwargs["text"] is True
        return subprocess.CompletedProcess(command, 0, stdout="", stderr="")

    monkeypatch.setattr(sys.modules[__name__], "_run_local_compile_command", _fake_run_local_compile_command)
    monkeypatch.setattr(subprocess, "run", _fake_run)

    _compile_only("int compiled_only() { return 0; }\n")
    _compile_and_run("#include <cstdint>\nint main() { return 0; }\n")

    assert len(compile_calls) == 2
    compile_only_cmd, compile_and_run_cmd = compile_calls

    assert compile_only_cmd[:2] == ("g++", "-std=c++17")
    assert "-c" in compile_only_cmd
    assert compile_only_cmd[compile_only_cmd.index("-I") + 1] == str(REPO_ROOT)
    assert compile_only_cmd[compile_only_cmd.index("-c") + 1].endswith("gen_kernel_npu_demo_test.cpp")
    assert compile_only_cmd[compile_only_cmd.index("-o") + 1].endswith("gen_kernel_npu_demo_test.o")

    assert compile_and_run_cmd[:2] == ("g++", "-std=c++17")
    assert "-c" not in compile_and_run_cmd
    assert compile_and_run_cmd[compile_and_run_cmd.index("-I") + 1] == str(REPO_ROOT)
    assert compile_and_run_cmd[compile_and_run_cmd.index("-I") + 2].endswith("gen_kernel_conv_test.cpp")
    assert compile_and_run_cmd[compile_and_run_cmd.index("-o") + 1].endswith("gen_kernel_conv_test")

    assert len(runtime_calls) == 1
    assert runtime_calls[0][0].endswith("gen_kernel_conv_test")


# GK-001
# 创建者: 金铲铲大作战
# 最后一次更改: 金铲铲大作战
# 最近一次运行测试时间: 2026-03-23 22:45:14 +0800
# 最近一次运行成功时间: 2026-03-23 22:45:14 +0800
# 功能说明: 验证 func.func 可生成完整后端源码。
# 测试目的: 验证 gen_kernel 返回签名与函数体文本。
# 使用示例: pytest -q test/dsl/gen_kernel/test_gen_kernel.py -k test_gen_kernel_returns_target_source
# 对应功能实现文件路径: kernel_gen/dsl/gen_kernel/gen_kernel.py
# 对应 spec 文件路径: spec/dsl/gen_kernel/gen_kernel.md
# 对应测试文件路径: test/dsl/gen_kernel/test_gen_kernel.py

def test_gen_kernel_returns_target_source() -> None:
    block = Block(arg_types=[i32, i32])
    add = arith.AddiOp(block.args[0], block.args[1])
    block.add_op(add)
    block.add_op(func.ReturnOp())
    func_op = _func("sum_kernel", [i32, i32], [], block, ("lhs", "rhs"))

    source = gen_kernel(func_op, _ctx())

    assert source.startswith("void sum_kernel(int32_t lhs, int32_t rhs)")
    assert "int32_t v0 = (lhs + rhs);" in source

    empty_block = Block(arg_types=[])
    empty_block.add_op(func.ReturnOp())
    empty_func = _func("empty_kernel", [], [], empty_block, ())
    empty_source = gen_kernel(empty_func, _ctx())
    assert empty_source == "void empty_kernel() {\n}"

    mem = _make_memory_type([2, 2], [2, 1])
    memory_block = Block(arg_types=[mem])
    memory_block.add_op(func.ReturnOp(memory_block.args[0]))
    memory_func = _func("memory_kernel", [mem], [mem], memory_block, ("input",))
    memory_source = gen_kernel(_rewrite_func(memory_func), _ctx())
    assert memory_source.startswith(
        "void memory_kernel(Memory<MemorySpace::GM, int32_t>& arg0, const Memory<MemorySpace::GM, int32_t>& input)"
    )
    assert "out = input;" not in memory_source


# GK-014B
# 创建者: 小李飞刀
# 最后一次更改: 小李飞刀
# 最近一次运行测试时间: 2026-04-22 00:00:00 +0800
# 最近一次运行成功时间: 2026-04-22 00:00:00 +0800
# 功能说明: 验证 `gen_kernel(...)` 直接使用模块本地 `emit_c_op` 时，仍会把 `EmitCError` 折回公开错误类型。
# 测试目的: 锁定 canonical `gen_kernel.py` 的直接 emit 绑定语义，避免错误类型泄漏。
# 使用示例: pytest -q test/dsl/gen_kernel/test_gen_kernel.py -k test_gen_kernel_converts_emit_c_error_to_gen_kernel_error
# 对应功能实现文件路径: kernel_gen/dsl/gen_kernel/__init__.py
# 对应 spec 文件路径: spec/dsl/gen_kernel/gen_kernel.md
# 对应测试文件路径: test/dsl/gen_kernel/test_gen_kernel.py
def test_gen_kernel_converts_emit_c_error_to_gen_kernel_error(monkeypatch: pytest.MonkeyPatch) -> None:
    def _boom(_op: object, _ctx: EmitCContext) -> str:
        raise EmitCError("boom")

    monkeypatch.setattr(gen_kernel_entry_module, "emit_c_op", _boom)

    with pytest.raises(GenKernelError, match="boom"):
        gen_kernel(UnsupportedOp(), _ctx())


# GK-014C
# 创建者: 小李飞刀
# 最后一次更改: 小李飞刀
# 最近一次运行测试时间: 2026-04-22 00:00:00 +0800
# 最近一次运行成功时间: 2026-04-22 00:00:00 +0800
# 功能说明: 验证 `gen_kernel.py` 模块本身只保留 `spec` 已定义的公开对象可达性。
# 测试目的: 锁定 `kernel_gen.dsl.gen_kernel.gen_kernel` 的公开面只保留 `gen_kernel(...)` 与 `GenKernelError`，避免内部 helper 或未入 `spec` 的模块元数据被当成跨文件入口。
# 使用示例: pytest -q test/dsl/gen_kernel/test_gen_kernel.py -k test_gen_kernel_entry_module_hides_internal_emitter_entry
# 对应功能实现文件路径: kernel_gen/dsl/gen_kernel/gen_kernel.py
# 对应 spec 文件路径: spec/dsl/gen_kernel/gen_kernel.md
# 对应测试文件路径: test/dsl/gen_kernel/test_gen_kernel.py
def test_gen_kernel_entry_module_hides_internal_emitter_entry() -> None:
    namespace: dict[str, object] = {}
    exec("from kernel_gen.dsl.gen_kernel.gen_kernel import GenKernelError, dsl_gen_kernel, gen_kernel", namespace)

    assert namespace["GenKernelError"] is GenKernelError
    assert namespace["dsl_gen_kernel"] is dsl_gen_kernel
    assert namespace["gen_kernel"] is gen_kernel
    assert gen_kernel_entry_module.GenKernelError is GenKernelError
    assert gen_kernel_entry_module.dsl_gen_kernel is dsl_gen_kernel
    assert gen_kernel_entry_module.gen_kernel is gen_kernel
    assert not hasattr(gen_kernel_entry_module, "KernelEmitter")
    with pytest.raises(ImportError):
        exec("from kernel_gen.dsl.gen_kernel.gen_kernel import KernelEmitter", {})


# GK-014
# 创建者: 朽木露琪亚
# 最后一次更改: 朽木露琪亚
# 最近一次运行测试时间: 2026-04-04 20:25:00 +0800
# 最近一次运行成功时间: 2026-04-04 20:25:00 +0800
# 功能说明: 验证 gen_kernel 包根与上下文子模块对外导出的公开对象可导入、可达。
# 测试目的: 锁定 `kernel_gen.dsl.gen_kernel`、`gen_kernel.py` 与 `emit_context.py` 的公开导入行为，避免旧双接口或未入 `spec` 的模块元数据被当成稳定合同。
# 使用示例: pytest -q test/dsl/gen_kernel/test_gen_kernel.py -k test_gen_kernel_is_the_package_public_entry
# 对应功能实现文件路径: kernel_gen/dsl/gen_kernel/__init__.py
# 对应 spec 文件路径: spec/dsl/gen_kernel/gen_kernel.md
# 对应测试文件路径: test/dsl/gen_kernel/test_gen_kernel.py

def test_gen_kernel_is_the_package_public_entry() -> None:
    namespace: dict[str, object] = {}
    exec("from kernel_gen.dsl.gen_kernel import *", namespace)
    public_names = {name for name in namespace if name != "__builtins__"}

    assert public_names == {
        "GenKernelError",
        "KernelEmitter",
        "dsl_gen_kernel",
        "gen_kernel",
        "EmitCContext",
        "EmitCError",
        "emit_c",
        "emit_c_op",
        "emit_c_value",
    }
    assert namespace["GenKernelError"] is GenKernelError
    assert namespace["KernelEmitter"] is KernelEmitter
    assert namespace["dsl_gen_kernel"] is dsl_gen_kernel
    assert namespace["gen_kernel"] is gen_kernel
    assert namespace["EmitCContext"] is EmitCContext
    assert namespace["EmitCError"] is EmitCError
    assert namespace["emit_c"] is emit_c
    assert namespace["emit_c_op"] is emit_c_op
    assert namespace["emit_c_value"] is emit_c_value
    assert gen_kernel_module.GenKernelError is GenKernelError
    assert gen_kernel_module.gen_kernel is gen_kernel_entry_module.gen_kernel
    assert gen_kernel_module.EmitCContext is EmitCContext
    assert gen_kernel_module.EmitCError is EmitCError
    assert gen_kernel_module.emit_c is emit_c
    assert gen_kernel_module.emit_c_op is emit_c_op
    assert gen_kernel_module.emit_c_value is emit_c_value
    assert "gen_signature" not in public_names
    assert "gen_body" not in public_names
    assert emit_context_module.EmitCContext is EmitCContext
    assert emit_context_module.EmitCError is EmitCError
    emit_context_namespace: dict[str, object] = {}
    exec(
        "from kernel_gen.dsl.gen_kernel.emit_context import EmitCContext, EmitCError",
        emit_context_namespace,
    )
    assert emit_context_namespace["EmitCContext"] is EmitCContext
    assert emit_context_namespace["EmitCError"] is EmitCError


# GK-014D
# 创建者: 朽木露琪亚
# 最后一次更改: 朽木露琪亚
# 最近一次运行测试时间: 未运行
# 最近一次运行成功时间: 未运行
# 功能说明: 验证 `dsl_gen_kernel(...)` 复用公开 `mlir_gen(...) + gen_kernel(...)` 路径，不改变旧 IR 入口合同。
# 测试目的: 锁定 callable 公开入口新增后，旧 `gen_kernel(module, ctx)` 链路仍是唯一源码生成后端。
# 使用示例: pytest -q test/dsl/gen_kernel/test_gen_kernel.py -k test_dsl_gen_kernel_matches_public_mlir_gen_plus_gen_kernel_path
# 对应功能实现文件路径: kernel_gen/dsl/gen_kernel/gen_kernel.py
# 对应 spec 文件路径: spec/dsl/gen_kernel/gen_kernel.md
# 对应测试文件路径: test/dsl/gen_kernel/test_gen_kernel.py
def test_dsl_gen_kernel_matches_public_mlir_gen_plus_gen_kernel_path() -> None:
    def add_scalar(lhs: int, rhs: int) -> int:
        return lhs + rhs

    module = mlir_gen(add_scalar, 3, 4, config={"reject_external_values": True})
    root_func = next(op for op in module.body.block.ops if isinstance(op, func.FuncOp))
    ir_source = gen_kernel(root_func, _ctx())
    callable_source = dsl_gen_kernel(
        add_scalar,
        3,
        4,
        ctx=_ctx(),
        config={"reject_external_values": True},
    )

    assert callable_source == ir_source
    assert callable_source.startswith("long long add_scalar(long long arg0, long long arg1)")
    assert "long long v0 = (arg0 + arg1);" in callable_source
    assert "return v0;" in callable_source


# GK-014A
# 创建者: 金铲铲大作战
# 最后一次更改: 金铲铲大作战
# 最近一次运行测试时间: 2026-04-04 00:00:00 +0800
# 最近一次运行成功时间: 2026-04-04 00:00:00 +0800
# 功能说明: 验证 legacy `gen_signature/gen_body` 双接口不再作为公开稳定入口存在。
# 测试目的: 锁定直接 attribute 访问和 `from ... import ...` 都不能再拿到旧双接口，避免“表面只测 gen_kernel，实际 legacy 双接口仍可直接使用”的假闭环。
# 使用示例: pytest -q test/dsl/gen_kernel/test_gen_kernel.py -k test_gen_kernel_has_no_legacy_double_interface
# 对应功能实现文件路径: kernel_gen/dsl/gen_kernel/gen_kernel.py
# 对应 spec 文件路径: spec/dsl/gen_kernel/gen_kernel.md
# 对应测试文件路径: test/dsl/gen_kernel/test_gen_kernel.py
def test_gen_kernel_has_no_legacy_double_interface() -> None:
    for legacy_name in ("gen_signature", "gen_body"):
        assert not hasattr(gen_kernel_module, legacy_name)
        with pytest.raises(AttributeError, match="no longer a public entry"):
            getattr(gen_kernel_module, legacy_name)
        with pytest.raises(ImportError):
            exec(f"from kernel_gen.dsl.gen_kernel import {legacy_name}", {})


# GK-001A
# 创建者: jcc你莫辜负
# 最后一次更改: 金铲铲大作战
# 最近一次运行测试时间: 2026-04-04 00:00:00 +0800
# 最近一次运行成功时间: 2026-04-04 00:00:00 +0800
# 功能说明: 验证单个普通 op 输入会直接委托给 canonical `gen_kernel.py` 的本地 `emit_c_op` 绑定。
# 测试目的: 锁定 gen_kernel(op_or_func, ctx) 不再经过包根额外包装，直接复用节点级公开接口。
# 使用示例: pytest -q test/dsl/gen_kernel/test_gen_kernel.py -k test_gen_kernel_delegates_single_op_input_to_emit_c
# 对应功能实现文件路径: kernel_gen/dsl/gen_kernel/gen_kernel.py
# 对应 spec 文件路径: spec/dsl/gen_kernel/gen_kernel.md
# 对应测试文件路径: test/dsl/gen_kernel/test_gen_kernel.py

def test_gen_kernel_delegates_single_op_input_to_emit_c(monkeypatch: pytest.MonkeyPatch) -> None:
    seen: list[str] = []

    def _fake_emit(op: object, _ctx: EmitCContext) -> str:
        seen.append(op.name)
        return "// single-op"

    monkeypatch.setattr(gen_kernel_entry_module, "emit_c_op", _fake_emit)

    source = gen_kernel(UnsupportedOp(), _ctx())

    assert source == "// single-op"
    assert seen == ["test.unsupported"]


# GK-002
# 创建者: 金铲铲大作战
# 最后一次更改: 金铲铲大作战
# 最近一次运行测试时间: 2026-03-23 22:45:14 +0800
# 最近一次运行成功时间: 2026-03-23 22:45:14 +0800
# 功能说明: 验证输入 Memory 参数使用只读签名。
# 测试目的: 验证 gen_kernel 生成的完整源码对 Memory 输入使用 const 引用。
# 使用示例: pytest -q test/dsl/gen_kernel/test_gen_kernel.py -k test_gen_kernel_uses_readonly_memory_inputs
# 对应功能实现文件路径: kernel_gen/dsl/gen_kernel/gen_kernel.py
# 对应 spec 文件路径: spec/dsl/gen_kernel/gen_kernel.md
# 对应测试文件路径: test/dsl/gen_kernel/test_gen_kernel.py

def test_gen_kernel_uses_readonly_memory_inputs() -> None:
    mem = _make_memory_type([2, 2], [2, 1])
    block = Block(arg_types=[mem])
    block.add_op(func.ReturnOp())
    func_op = _func("read_only", [mem], [], block, ("input",))

    source = gen_kernel(func_op, _ctx())

    assert source.startswith("void read_only(const Memory<MemorySpace::GM, int32_t>& input)")


# GK-O5-001
# 创建者: jcc你莫辜负
# 最后一次更改: 金铲铲大作战
# 最近一次运行测试时间: 2026-04-04 00:00:00 +0800
# 最近一次运行成功时间: 2026-04-04 00:00:00 +0800
# 功能说明: 验证 rewritten 单 output memory 函数可被 gen_kernel 消费。
# 测试目的: 锁定公开成功链路必须来自 rewrite 后 IR，源码签名使用前置 `arg0`，不再依赖旧 memory return ABI。
# 使用示例: pytest -q test/dsl/gen_kernel/test_gen_kernel.py -k test_gen_kernel_accepts_rewritten_single_output_function
# 对应功能实现文件路径: kernel_gen/dsl/gen_kernel/gen_kernel.py
# 对应 spec 文件路径: spec/dsl/gen_kernel/gen_kernel.md
# 对应测试文件路径: test/dsl/gen_kernel/test_gen_kernel.py
def test_gen_kernel_accepts_rewritten_single_output_function() -> None:
    mem = _make_memory_type([2, 2], [2, 1])
    block = Block(arg_types=[mem])
    block.add_op(func.ReturnOp(block.args[0]))
    func_op = _func("produce", [mem], [mem], block, ("input",))

    source = gen_kernel(_rewrite_func(func_op), _ctx())

    assert source.startswith(
        "void produce(Memory<MemorySpace::GM, int32_t>& arg0, const Memory<MemorySpace::GM, int32_t>& input)"
    )
    assert "out = input;" not in source


# GK-O5-002
# 创建者: jcc你莫辜负
# 最后一次更改: jcc你莫辜负
# 最近一次运行测试时间: 待运行
# 最近一次运行成功时间: 待运行
# 功能说明: 验证 rewritten `dma.deslice` memory return 会把可写 ABI 收口到前置 `arg0`。
# 测试目的: 锁定 `buffer-results-to-out-params` 不只替换 return SSA，还会把 deslice 的真实写回目标改成 out-first 参数。
# 使用示例: pytest -q test/dsl/gen_kernel/test_gen_kernel.py -k test_gen_kernel_rewritten_deslice_memory_result_uses_front_out_param
# 对应功能实现文件路径: kernel_gen/passes/buffer_results_to_out_params.py
# 对应 spec 文件路径: spec/dsl/gen_kernel/gen_kernel.md
# 对应测试文件路径: test/dsl/gen_kernel/test_gen_kernel.py
def test_gen_kernel_rewritten_deslice_memory_result_uses_front_out_param() -> None:
    source_type = _make_memory_type([2, 2], [2, 1], space="local")
    target_type = _make_memory_type([2, 2], [2, 1])
    block = Block(arg_types=[source_type, target_type])
    c0 = arith.ConstantOp(IntegerAttr(0, i32))
    c1 = arith.ConstantOp(IntegerAttr(1, i32))
    c2 = arith.ConstantOp(IntegerAttr(2, i32))
    deslice_op = DmaDesliceOp(
        block.args[0],
        block.args[1],
        [c0.result, c0.result],
        [c2.result, c2.result],
        [c1.result, c1.result],
        target_type,
    )
    block.add_ops([c0, c1, c2, deslice_op, func.ReturnOp(deslice_op.result)])
    func_op = _func("deslice_case", [source_type, target_type], [target_type], block, ("src", "target"))

    source = gen_kernel(_rewrite_func(func_op), _ctx())

    assert source.startswith(
        "void deslice_case(Memory<MemorySpace::GM, int32_t>& arg0, const Memory<MemorySpace::LM, int32_t>& src, const Memory<MemorySpace::GM, int32_t>& target)"
    )
    assert "arg0.at(dma0_dst_indices) = src.at(dma0_src_indices);" in source
    assert "target.at(dma0_dst_indices) = src.at(dma0_src_indices);" not in source


# GK-004
# 创建者: 金铲铲大作战
# 最后一次更改: jcc你莫辜负
# 最近一次运行测试时间: 2026-03-23 22:45:14 +0800
# 最近一次运行成功时间: 2026-03-23 22:45:14 +0800
# 功能说明: 验证缺失参数名时仍生成稳定默认命名。
# 测试目的: 验证 gen_kernel 在完整源码中保持标量参数顺序，并在缺失 `arg_attrs.name` 时使用 `arg{index}`。
# 使用示例: pytest -q test/dsl/gen_kernel/test_gen_kernel.py -k test_gen_kernel_uses_default_arg_names_when_missing_attrs
# 对应功能实现文件路径: kernel_gen/dsl/gen_kernel/gen_kernel.py
# 对应 spec 文件路径: spec/dsl/gen_kernel/gen_kernel.md
# 对应测试文件路径: test/dsl/gen_kernel/test_gen_kernel.py

def test_gen_kernel_uses_default_arg_names_when_missing_attrs() -> None:
    block = Block(arg_types=[i32, IndexType(), i32])
    block.add_op(func.ReturnOp())
    func_op = _func("ordered", [i32, IndexType(), i32], [], block, ("lhs", "index", "rhs"))

    source = gen_kernel(func_op, _ctx())

    assert source.startswith("void ordered(int32_t lhs, long long index, int32_t rhs)")

    unnamed_block = Block(arg_types=[i32])
    unnamed_block.add_op(func.ReturnOp())
    unnamed_type = FunctionType.from_lists([i32], [])
    unnamed_func = func.FuncOp(
        "unnamed",
        unnamed_type,
        Region(unnamed_block),
        arg_attrs=ArrayAttr([DictionaryAttr({})]),
    )
    unnamed_source = gen_kernel(unnamed_func, _ctx())
    assert unnamed_source.startswith("void unnamed(int32_t arg0)")

    default_block = Block(arg_types=[i1])
    default_block.add_op(func.ReturnOp())
    default_type = FunctionType.from_lists([i1], [])
    default_func = func.FuncOp("default_names", default_type, Region(default_block))
    default_source = gen_kernel(default_func, _ctx())
    assert default_source.startswith("void default_names(bool arg0)")


# GK-005
# 创建者: 金铲铲大作战
# 最后一次更改: jcc你莫辜负
# 最近一次运行测试时间: 2026-03-23 22:45:14 +0800
# 最近一次运行成功时间: 2026-03-23 22:45:14 +0800
# 功能说明: 验证完整源码中的普通 op 顺序与 IR 一致。
# 测试目的: 验证 gen_kernel 的函数级主遍历不改变 IR 中的 op 顺序。
# 使用示例: pytest -q test/dsl/gen_kernel/test_gen_kernel.py -k test_gen_kernel_emits_ops_in_order
# 对应功能实现文件路径: kernel_gen/dsl/gen_kernel/gen_kernel.py
# 对应 spec 文件路径: spec/dsl/gen_kernel/gen_kernel.md
# 对应测试文件路径: test/dsl/gen_kernel/test_gen_kernel.py

def test_gen_kernel_emits_ops_in_order() -> None:
    block = Block(arg_types=[i32, i32])
    first = arith.AddiOp(block.args[0], block.args[1])
    second = arith.SubiOp(block.args[0], block.args[1])
    block.add_op(first)
    block.add_op(second)
    block.add_op(func.ReturnOp())
    func_op = _func("ordered_body", [i32, i32], [], block, ("lhs", "rhs"))
    source = gen_kernel(func_op, _ctx())

    add_idx = source.index("int32_t v0 = (lhs + rhs);")
    sub_idx = source.index("int32_t v1 = (lhs - rhs);")
    assert add_idx < sub_idx


# GK-005A
# 创建者: jcc你莫辜负
# 最后一次更改: jcc你莫辜负
# 最近一次运行测试时间: 2026-04-04 00:00:00 +0800
# 最近一次运行成功时间: 2026-04-04 00:00:00 +0800
# 功能说明: 验证普通 op 逐个委托到 canonical `gen_kernel.py` 的本地 `emit_c_op`。
# 测试目的: 锁定 gen_kernel 的函数级主遍历只把非 return op 委托给节点级公开接口。
# 使用示例: pytest -q test/dsl/gen_kernel/test_gen_kernel.py -k test_gen_kernel_delegates_to_emit_c_for_non_return_ops
# 对应功能实现文件路径: kernel_gen/dsl/gen_kernel/gen_kernel.py
# 对应 spec 文件路径: spec/dsl/gen_kernel/gen_kernel.md
# 对应测试文件路径: test/dsl/gen_kernel/test_gen_kernel.py

def test_gen_kernel_delegates_to_emit_c_for_non_return_ops(monkeypatch: pytest.MonkeyPatch) -> None:
    block = Block(arg_types=[i32, i32])
    first = arith.AddiOp(block.args[0], block.args[1])
    second = arith.SubiOp(block.args[0], block.args[1])
    block.add_op(first)
    block.add_op(second)
    block.add_op(func.ReturnOp())
    func_op = _func("ordered_body", [i32, i32], [], block, ("lhs", "rhs"))
    seen: list[str] = []

    def _fake_emit(op: object, _ctx: EmitCContext) -> str:
        seen.append(op.name)
        return f"{_ctx.current_indent}// {op.name}"

    monkeypatch.setattr(gen_kernel_entry_module, "emit_c_op", _fake_emit)

    source = gen_kernel(func_op, _ctx())

    assert seen == ["arith.addi", "arith.subi"]
    assert "// arith.addi" in source
    assert "// arith.subi" in source
    assert "func.return" not in seen


# GK-005B
# 创建者: jcc你莫辜负
# 最后一次更改: jcc你莫辜负
# 最近一次运行测试时间: 2026-04-04 00:00:00 +0800
# 最近一次运行成功时间: 2026-04-04 00:00:00 +0800
# 功能说明: 验证 func.return/out 绑定由函数级主遍历流程处理。
# 测试目的: 锁定 return 收尾不走普通 emit_c_op 公开职责，避免 `func.return` 回流为节点级公开接口。
# 使用示例: pytest -q test/dsl/gen_kernel/test_gen_kernel.py -k test_gen_kernel_handles_func_return_and_out_binding_in_main_flow
# 对应功能实现文件路径: kernel_gen/dsl/gen_kernel/gen_kernel.py
# 对应 spec 文件路径: spec/dsl/gen_kernel/gen_kernel.md
# 对应测试文件路径: test/dsl/gen_kernel/test_gen_kernel.py

def test_gen_kernel_handles_func_return_and_out_binding_in_main_flow(monkeypatch: pytest.MonkeyPatch) -> None:
    mem = _make_memory_type([2, 2], [2, 1])
    second_block = Block(arg_types=[mem, mem])
    second_block.add_op(func.ReturnOp(second_block.args[1]))
    second_func = _rewrite_func(_func("return_second", [mem, mem], [mem], second_block, ("lhs", "rhs")))

    def _unexpected_emit(op: object, _ctx: EmitCContext) -> str:
        raise AssertionError(f"emit_c_op should not see {op}")

    monkeypatch.setattr(gen_kernel_entry_module, "emit_c_op", _unexpected_emit)

    source = gen_kernel(second_func, _ctx())

    assert source.startswith(
        "void return_second(Memory<MemorySpace::GM, int32_t>& arg0, "
        "const Memory<MemorySpace::GM, int32_t>& lhs, const Memory<MemorySpace::GM, int32_t>& rhs)"
    )
    assert "func.return" not in source
    assert "out = rhs;" not in source


# GK-006
# 创建者: 金铲铲大作战
# 最后一次更改: 金铲铲大作战
# 最近一次运行测试时间: 2026-03-23 22:45:14 +0800
# 最近一次运行成功时间: 2026-03-23 22:45:14 +0800
# 功能说明: 验证 loop 片段可拼装到完整函数中。
# 测试目的: 验证 gen_kernel 保留 scf.for 生成结果。
# 使用示例: pytest -q test/dsl/gen_kernel/test_gen_kernel.py -k test_gen_kernel_assembles_loop_body
# 对应功能实现文件路径: kernel_gen/dsl/gen_kernel/gen_kernel.py
# 对应 spec 文件路径: spec/dsl/gen_kernel/gen_kernel.md
# 对应测试文件路径: test/dsl/gen_kernel/test_gen_kernel.py

def test_gen_kernel_assembles_loop_body() -> None:
    block = Block(arg_types=[])
    c0 = arith.ConstantOp(IntegerAttr(0, IndexType()))
    c4 = arith.ConstantOp(IntegerAttr(4, IndexType()))
    c1 = arith.ConstantOp(IntegerAttr(1, IndexType()))
    for op in (c0, c4, c1):
        block.add_op(op)
    loop_body = Block(arg_types=[IndexType()])
    loop_body.add_op(arith.AddiOp(loop_body.args[0], loop_body.args[0], result_type=IndexType()))
    loop_body.add_op(scf.YieldOp())
    block.add_op(scf.ForOp(c0.result, c4.result, c1.result, [], loop_body))
    block.add_op(func.ReturnOp())
    func_op = _func("loop_kernel", [], [], block, ())

    source = gen_kernel(func_op, _ctx())

    assert "for (long long i0 = 0; i0 < 4; i0 += 1) {" in source
    assert "long long v0 = (i0 + i0);" in source


# GK-007
# 创建者: 金铲铲大作战
# 最后一次更改: 小李飞刀
# 最近一次运行测试时间: 2026-03-23 22:45:14 +0800
# 最近一次运行成功时间: 2026-03-23 22:45:14 +0800
# 功能说明: 验证 emit_c 错误可向上抛出。
# 测试目的: 验证 gen_kernel 不吞掉 emit_c 失败原因。
# 使用示例: pytest -q test/dsl/gen_kernel/test_gen_kernel.py -k test_gen_kernel_propagates_emit_c_error
# 对应功能实现文件路径: kernel_gen/dsl/gen_kernel/gen_kernel.py
# 对应 spec 文件路径: spec/dsl/gen_kernel/gen_kernel.md
# 对应测试文件路径: test/dsl/gen_kernel/test_gen_kernel.py

def test_gen_kernel_propagates_emit_c_error() -> None:
    block = Block(arg_types=[])
    block.add_op(UnsupportedOp())
    block.add_op(func.ReturnOp())
    func_op = _func("bad_kernel", [], [], block, ())

    with pytest.raises(ValueError) as exc_info:
        gen_kernel(func_op, _ctx())

    assert "test.unsupported" in str(exc_info.value)


# GK-008
# 创建者: 金铲铲大作战
# 最后一次更改: 小李飞刀
# 最近一次运行测试时间: 2026-03-23 22:45:14 +0800
# 最近一次运行成功时间: 2026-03-23 22:45:14 +0800
# 功能说明: 验证不合法返回形式时报错。
# 测试目的: 验证 gen_kernel 拒绝不支持的返回形式与输入类型。
# 使用示例: pytest -q test/dsl/gen_kernel/test_gen_kernel.py -k test_gen_kernel_rejects_unsupported_return_form
# 对应功能实现文件路径: kernel_gen/dsl/gen_kernel/gen_kernel.py
# 对应 spec 文件路径: spec/dsl/gen_kernel/gen_kernel.md
# 对应测试文件路径: test/dsl/gen_kernel/test_gen_kernel.py

def test_gen_kernel_rejects_unsupported_return_form() -> None:
    block = Block(arg_types=[i32])
    block.add_op(func.ReturnOp(block.args[0]))
    func_op = _func("scalar_return", [i32], [i32], block, ("value",))

    source = gen_kernel(func_op, _ctx())
    assert source.startswith("int32_t scalar_return(int32_t value)")
    assert "return value;" in source

    tuple_block = Block(arg_types=[])
    tuple_block.add_op(func.ReturnOp())
    tuple_type = FunctionType.from_lists([], [i32, i32])
    tuple_func = func.FuncOp("tuple_return", tuple_type, Region(tuple_block), arg_attrs=ArrayAttr([]))
    with pytest.raises(GenKernelError) as exc_info:
        gen_kernel(tuple_func, _ctx())
    assert "unsupported return form" in str(exc_info.value)

    float_block = Block(arg_types=[f16])
    float_block.add_op(func.ReturnOp())
    float_type = FunctionType.from_lists([f16], [])
    float_func = func.FuncOp("f16_arg", float_type, Region(float_block))
    source = gen_kernel(float_func, _ctx())
    assert source.startswith("void f16_arg(half arg0)")

# GK-012
# 创建者: jcc你莫辜负
# 最后一次更改: 金铲铲大作战
# 最近一次运行测试时间: 2026-04-01 15:07:50 +0800
# 最近一次运行成功时间: 2026-04-01 15:07:50 +0800
# 功能说明: 验证 f32/f64 标量与 Memory<Space, f32/f64> 可生成 float/double 与 Memory<MemorySpace::GM, float>/Memory<MemorySpace::GM, double> 形式签名。
# 测试目的: 锁定 gen_kernel 在完整源码签名中的 f32/f64 类型映射，避免 conv2d 链路在函数级入口阶段被 TypeError 阻断或类型退化。
# 使用示例: pytest -q test/dsl/gen_kernel/test_gen_kernel.py -k test_gen_kernel_supports_float32_scalar_and_memory
# 对应功能实现文件路径: kernel_gen/dsl/gen_kernel/gen_kernel.py
# 对应 spec 文件路径: spec/dsl/gen_kernel/gen_kernel.md
# 对应测试文件路径: test/dsl/gen_kernel/test_gen_kernel.py

def test_gen_kernel_supports_float32_scalar_and_memory() -> None:
    mem_f32 = _make_memory_type([2, 2], [2, 1], element_type=f32)
    block_f32 = Block(arg_types=[mem_f32, f32])
    block_f32.add_op(func.ReturnOp(block_f32.args[0]))
    func_op_f32 = _rewrite_func(_func("float_kernel", [mem_f32, f32], [mem_f32], block_f32, ("input", "alpha")))

    source_f32 = gen_kernel(func_op_f32, _ctx())

    assert source_f32.startswith(
        "void float_kernel(Memory<MemorySpace::GM, float>& arg0, const Memory<MemorySpace::GM, float>& input, float alpha)"
    )

    mem_f64 = _make_memory_type([2, 2], [2, 1], element_type=f64)
    block_f64 = Block(arg_types=[mem_f64, f64])
    block_f64.add_op(func.ReturnOp(block_f64.args[0]))
    func_op_f64 = _rewrite_func(_func("double_kernel", [mem_f64, f64], [mem_f64], block_f64, ("input", "alpha")))

    source_f64 = gen_kernel(func_op_f64, _ctx())

    assert source_f64.startswith(
        "void double_kernel(Memory<MemorySpace::GM, double>& arg0, const Memory<MemorySpace::GM, double>& input, double alpha)"
    )


# GK-009
# 创建者: 金铲铲大作战
# 最后一次更改: 金铲铲大作战
# 最近一次运行测试时间: 2026-03-25 17:10:00 +0800
# 最近一次运行成功时间: 2026-03-25 17:10:00 +0800
# 功能说明: 验证生成源码保留函数名与参数名，并在缺失参数名时沿用默认命名。
# 测试目的: 验证 gen_kernel 使用 IR 中定义的名称；当输入参数缺失 arg_attrs.name 时，源码中的签名参数名回退为 arg{index}。
# 使用示例: pytest -q test/dsl/gen_kernel/test_gen_kernel.py -k test_gen_kernel_preserves_function_and_arg_names
# 对应功能实现文件路径: kernel_gen/dsl/gen_kernel/gen_kernel.py
# 对应 spec 文件路径: spec/dsl/gen_kernel/gen_kernel.md
# 对应测试文件路径: test/dsl/gen_kernel/test_gen_kernel.py

def test_gen_kernel_preserves_function_and_arg_names() -> None:
    mem = _make_memory_type([2, 2], [2, 1])
    block = Block(arg_types=[mem, i32])
    block.add_op(func.ReturnOp(block.args[0]))
    func_op = _rewrite_func(_func("named_kernel", [mem, i32], [mem], block, ("tensor", "scale")))

    source = gen_kernel(func_op, _ctx())

    assert source.startswith(
        "void named_kernel(Memory<MemorySpace::GM, int32_t>& arg0, const Memory<MemorySpace::GM, int32_t>& tensor, int32_t scale)"
    )
    assert "out = tensor;" not in source

    unnamed_block = Block(arg_types=[i32])
    unnamed_block.add_op(func.ReturnOp())
    unnamed_type = FunctionType.from_lists([i32], [])
    unnamed_func = func.FuncOp(
        "unnamed_kernel",
        unnamed_type,
        Region(unnamed_block),
        arg_attrs=ArrayAttr([DictionaryAttr({})]),
    )

    unnamed_source = gen_kernel(unnamed_func, _ctx())

    assert unnamed_source.startswith("void unnamed_kernel(int32_t arg0)")


# GK-010
# 创建者: jcc你莫辜负
# 最后一次更改: jcc你莫辜负
# 最近一次运行测试时间: 2026-03-28 07:20:00 +0800
# 最近一次运行成功时间: 2026-03-28 07:20:00 +0800
# 功能说明: 验证 !symbol.int 返回在 cpu target 下可生成函数返回值。
# 测试目的: 锁定 gen_kernel 对 symbol 标量返回的契约，避免退化为 unsupported return form。
# 使用示例: pytest -q test/dsl/gen_kernel/test_gen_kernel.py -k test_gen_kernel_supports_symbol_scalar_return
# 对应功能实现文件路径: kernel_gen/dsl/gen_kernel/gen_kernel.py
# 对应 spec 文件路径: spec/dsl/gen_kernel/gen_kernel.md
# 对应测试文件路径: test/dsl/gen_kernel/test_gen_kernel.py
def test_gen_kernel_supports_symbol_scalar_return() -> None:
    lhs_type = SymbolValueType.from_expr("3")
    rhs_type = SymbolValueType.from_expr("4")
    out_type = SymbolValueType.from_expr("7")
    block = Block(arg_types=[lhs_type, rhs_type])
    add = SymbolAddOp(block.args[0], block.args[1], out_type)
    block.add_op(add)
    block.add_op(func.ReturnOp(add.result))
    func_op = _func("symbol_sum", [lhs_type, rhs_type], [out_type], block, ("lhs", "rhs"))

    source = gen_kernel(func_op, _ctx())

    assert source.startswith("long long symbol_sum(long long lhs, long long rhs)")
    assert "long long v0 = (lhs + rhs);" in source
    assert "return v0;" in source


# GK-011
# 创建者: 金铲铲大作战
# 最后一次更改: 金铲铲大作战
# 最近一次运行测试时间: 2026-03-28 04:12:37 +0800
# 最近一次运行成功时间: 2026-03-28 04:12:37 +0800
# 功能说明: 验证非 cpu/npu_demo target 下 !symbol.int 返回必须报错。
# 测试目的: 锁定 gen_kernel 对 symbol 标量返回的 target 白名单约束。
# 使用示例: pytest -q test/dsl/gen_kernel/test_gen_kernel.py -k test_gen_kernel_rejects_symbol_scalar_return_on_non_cpu
# 对应功能实现文件路径: kernel_gen/dsl/gen_kernel/gen_kernel.py
# 对应 spec 文件路径: spec/dsl/gen_kernel/gen_kernel.md
# 对应测试文件路径: test/dsl/gen_kernel/test_gen_kernel.py
def test_gen_kernel_rejects_symbol_scalar_return_on_non_cpu() -> None:
    lhs_type = SymbolValueType.from_expr("3")
    rhs_type = SymbolValueType.from_expr("4")
    out_type = SymbolValueType.from_expr("7")
    block = Block(arg_types=[lhs_type, rhs_type])
    add = SymbolAddOp(block.args[0], block.args[1], out_type)
    block.add_op(add)
    block.add_op(func.ReturnOp(add.result))
    func_op = _func("symbol_sum", [lhs_type, rhs_type], [out_type], block, ("lhs", "rhs"))
    ctx = EmitCContext(config={"target": "gpu"})

    with pytest.raises(GenKernelError, match="symbol scalar return is only supported on cpu and npu_demo"):
        gen_kernel(func_op, ctx)


# GK-013
# 创建者: jcc你莫辜负
# 最后一次更改: 金铲铲大作战
# 最近一次运行测试时间: 2026-04-02 23:04:42 +0800
# 最近一次运行成功时间: 2026-04-02 23:04:42 +0800
# 功能说明: 验证 `build_func_op -> pass -> gen_kernel` 的 memory+memory add 在 cpu target 下可生成源码。
# 测试目的: 清理 raw `nn.add` 直出源码的旧成功口径，锁定 pass 后逐元素加法已被消费为 `cpu::add(lhs, rhs, out)`。
# 使用示例: pytest -q test/dsl/gen_kernel/test_gen_kernel.py -k test_gen_kernel_supports_lowered_nn_add_memory_memory_on_cpu
# 对应功能实现文件路径: kernel_gen/dsl/gen_kernel/gen_kernel.py
# 对应 spec 文件路径: spec/dsl/gen_kernel/gen_kernel.md
# 对应测试文件路径: test/dsl/gen_kernel/test_gen_kernel.py
def test_gen_kernel_supports_lowered_nn_add_memory_memory_on_cpu() -> None:
    def add_direct(lhs: "Tensor[i32, 2, 2]", rhs: "Tensor[i32, 2, 2]") -> "Tensor[i32, 2, 2]":
        return lhs + rhs

    func_op = build_func_op(add_direct, _tensor_arg([2, 2]), _tensor_arg([2, 2]))
    source = gen_kernel(_lower_and_rewrite_func(func_op), _ctx())

    assert source.startswith(
        "void add_direct(Memory<MemorySpace::GM, int32_t>& arg0, const Memory<MemorySpace::GM, int32_t>& arg1, const Memory<MemorySpace::GM, int32_t>& arg2)"
    )
    assert "cpu::add(arg1, arg2, arg0);" in source
    assert "kernel." not in source
    assert "nn.add" not in source
    assert "out = " not in source


# GK-014
# 创建者: jcc你莫辜负
# 最后一次更改: 金铲铲大作战
# 最近一次运行测试时间: 2026-04-02 23:04:42 +0800
# 最近一次运行成功时间: 2026-04-02 23:04:42 +0800
# 功能说明: 验证 `build_func_op -> pass -> gen_kernel` 的 memory+const(i32) add 会先经 `dma.fill` 再生成源码。
# 测试目的: 清理 raw mixed `nn.add` 直接出源码的旧成功口径，锁定 pass 后 `dma.fill + cpu::add(lhs, v0, out)` 文本。
# 使用示例: pytest -q test/dsl/gen_kernel/test_gen_kernel.py -k test_gen_kernel_supports_lowered_nn_add_memory_const_on_cpu
# 对应功能实现文件路径: kernel_gen/dsl/gen_kernel/gen_kernel.py
# 对应 spec 文件路径: spec/dsl/gen_kernel/gen_kernel.md
# 对应测试文件路径: test/dsl/gen_kernel/test_gen_kernel.py
def test_gen_kernel_supports_lowered_nn_add_memory_const_on_cpu() -> None:
    def add_const_direct(lhs: "Tensor[i32, 2, 2]") -> "Tensor[i32, 2, 2]":
        return lhs + 1

    func_op = build_func_op(add_const_direct, _tensor_arg([2, 2]))
    source = gen_kernel(_lower_and_rewrite_func(func_op), _ctx())

    assert source.startswith(
        "void add_const_direct(Memory<MemorySpace::GM, int32_t>& arg0, const Memory<MemorySpace::GM, int32_t>& arg1)"
    )
    assert "cpu::add(arg1, v0, arg0);" in source
    assert "for (long long fill0_i = 0; fill0_i < v0.element_count(); ++fill0_i) {" in source
    assert "v0.data()[fill0_i] = 1;" in source
    assert "kernel." not in source
    assert "nn.add" not in source
    assert "out = " not in source


# GK-015
# 创建者: jcc你莫辜负
# 最后一次更改: 金铲铲大作战
# 最近一次运行测试时间: 2026-04-02 23:04:42 +0800
# 最近一次运行成功时间: 2026-04-02 23:04:42 +0800
# 功能说明: 验证 `build_func_op -> pass -> gen_kernel` 的 memory+symbol.int add 会先经 `dma.fill` 再生成源码。
# 测试目的: 清理 raw `nn.add(memory, symbol.int)` 直接出源码的旧成功口径，锁定 pass 后 `dma.fill + cpu::add(lhs, v0, out)` 文本与 long long bias 签名。
# 使用示例: pytest -q test/dsl/gen_kernel/test_gen_kernel.py -k test_gen_kernel_supports_lowered_nn_add_memory_symbol_on_cpu
# 对应功能实现文件路径: kernel_gen/dsl/gen_kernel/gen_kernel.py
# 对应 spec 文件路径: spec/dsl/gen_kernel/gen_kernel.md
# 对应测试文件路径: test/dsl/gen_kernel/test_gen_kernel.py
def test_gen_kernel_supports_lowered_nn_add_memory_symbol_on_cpu() -> None:
    def add_symbol_direct(lhs: "Tensor[i32, 2, 2]", bias: int) -> "Tensor[i32, 2, 2]":
        return lhs + bias

    func_op = build_func_op(add_symbol_direct, _tensor_arg([2, 2]), SymbolDim("bias"))
    source = gen_kernel(_lower_and_rewrite_func(func_op), _ctx())

    assert source.startswith(
        "void add_symbol_direct(Memory<MemorySpace::GM, int32_t>& arg0, const Memory<MemorySpace::GM, int32_t>& arg1, long long arg2)"
    )
    assert "cpu::add(arg1, v0, arg0);" in source
    assert "for (long long fill0_i = 0; fill0_i < v0.element_count(); ++fill0_i) {" in source
    assert "v0.data()[fill0_i] = arg2;" in source
    assert "kernel." not in source
    assert "nn.add" not in source
    assert "out = " not in source


class Test_buffer_results_to_out_params_gen_kernel:
    def test_gen_kernel_accepts_rewritten_single_output_function(self) -> None:
        test_gen_kernel_accepts_rewritten_single_output_function()

    # GK-O5-002
    # 创建者: jcc你莫辜负
    # 最后一次更改: 金铲铲大作战
    # 最近一次运行测试时间: 2026-04-04 00:00:00 +0800
    # 最近一次运行成功时间: 2026-04-04 00:00:00 +0800
    # 功能说明: 验证 rewritten mixed output 函数可被 gen_kernel 消费。
    # 测试目的: 锁定 memory 走前置 out、scalar 继续返回的 rewrite 后 ABI。
    # 使用示例: pytest -q test/dsl/gen_kernel/test_gen_kernel.py -k test_gen_kernel_accepts_rewritten_mixed_output_function
    # 对应功能实现文件路径: kernel_gen/dsl/gen_kernel/gen_kernel.py
    # 对应 spec 文件路径: spec/dsl/gen_kernel/gen_kernel.md
    # 对应测试文件路径: test/dsl/gen_kernel/test_gen_kernel.py
    def test_gen_kernel_accepts_rewritten_mixed_output_function(self) -> None:
        mem = _make_memory_type([2, 2], [2, 1])
        block = Block(arg_types=[mem, i1])
        block.add_op(func.ReturnOp(block.args[0], block.args[1]))
        func_op = _func("mixed_out", [mem, i1], [mem, i1], block, ("input", "flag"))

        source = gen_kernel(_rewrite_func(func_op), _ctx())

        assert source.startswith(
            "bool mixed_out(Memory<MemorySpace::GM, int32_t>& arg0, const Memory<MemorySpace::GM, int32_t>& input, bool flag)"
        )
        assert "return flag;" in source
        assert "Memory<MemorySpace::GM, int32_t>& out" not in source

    # GK-O5-003
    # 创建者: jcc你莫辜负
    # 最后一次更改: 金铲铲大作战
    # 最近一次运行测试时间: 2026-04-04 00:00:00 +0800
    # 最近一次运行成功时间: 2026-04-04 00:00:00 +0800
    # 功能说明: 验证 rewrite 后成功链路不再残留旧 memory return ABI。
    # 测试目的: 黑盒检查 rewritten IR 与生成源码都不再依赖旧 memory return/out 推导路径。
    # 使用示例: pytest -q test/dsl/gen_kernel/test_gen_kernel.py -k test_rewritten_pipeline_has_no_memory_return_abi_left
    # 对应功能实现文件路径: kernel_gen/dsl/gen_kernel/gen_kernel.py
    # 对应 spec 文件路径: spec/dsl/gen_kernel/gen_kernel.md
    # 对应测试文件路径: test/dsl/gen_kernel/test_gen_kernel.py
    def test_rewritten_pipeline_has_no_memory_return_abi_left(self) -> None:
        def add_direct(lhs: "Tensor[i32, 2, 2]", rhs: "Tensor[i32, 2, 2]") -> "Tensor[i32, 2, 2]":
            return lhs + rhs

        func_op = _lower_and_rewrite_func(build_func_op(add_direct, _tensor_arg([2, 2]), _tensor_arg([2, 2])))
        source = gen_kernel(func_op, _ctx())
        ir_text = str(func_op)

        assert "-> (!nn.memory" not in ir_text
        assert "func.return %" not in ir_text
        assert "cpu::add(arg1, arg2, arg0);" in source
        assert "Memory<MemorySpace::GM, int32_t>& out" not in source
        assert "out = " not in source

    # GK-O5-005
    # 创建者: 小李飞刀
    # 最后一次更改: 小李飞刀
    # 最近一次运行测试时间: 2026-04-05 00:00:00 +0800
    # 最近一次运行成功时间: 2026-04-05 00:00:00 +0800
    # 功能说明: 验证仅 lowering 的 IR 仍会触发 gen_kernel 的 legacy ABI 拒绝。
    # 测试目的: 锁定下游合同：未执行 BufferResultsToOutParamsPass 时，gen_kernel 必须显式报错。
    # 使用示例: pytest -q test/dsl/gen_kernel/test_gen_kernel.py -k test_gen_kernel_rejects_lowered_ir_without_buffer_results_to_out_params
    # 对应功能实现文件路径: kernel_gen/dsl/gen_kernel/gen_kernel.py
    # 对应 spec 文件路径: spec/dsl/gen_kernel/gen_kernel.md
    # 对应测试文件路径: test/dsl/gen_kernel/test_gen_kernel.py
    def test_gen_kernel_rejects_lowered_ir_without_buffer_results_to_out_params(self) -> None:
        def add_direct(lhs: "Tensor[i32, 2, 2]", rhs: "Tensor[i32, 2, 2]") -> "Tensor[i32, 2, 2]":
            return lhs + rhs

        func_op = _lower_func(build_func_op(add_direct, _tensor_arg([2, 2]), _tensor_arg([2, 2])))
        with pytest.raises(GenKernelError, match="legacy memory return ABI is not supported"):
            gen_kernel(func_op, _ctx())

    # GK-O5-004
    # 创建者: jcc你莫辜负
    # 最后一次更改: jcc你莫辜负
    # 最近一次运行测试时间: 2026-04-04 00:00:00 +0800
    # 最近一次运行成功时间: 2026-04-04 00:00:00 +0800
    # 功能说明: 验证 half-rewritten IR 会被 gen_kernel 显式拒绝。
    # 测试目的: 防止“函数签名改了，但 outputs/return 仍保留旧 memory return ABI”的假闭环。
    # 使用示例: pytest -q test/dsl/gen_kernel/test_gen_kernel.py -k test_rewritten_pipeline_fails_on_half_rewritten_ir
    # 对应功能实现文件路径: kernel_gen/dsl/gen_kernel/gen_kernel.py
    # 对应 spec 文件路径: spec/dsl/gen_kernel/gen_kernel.md
    # 对应测试文件路径: test/dsl/gen_kernel/test_gen_kernel.py
    def test_rewritten_pipeline_fails_on_half_rewritten_ir(self) -> None:
        mem = _make_memory_type([2, 2], [2, 1])
        block = Block(arg_types=[mem, mem, mem])
        space = NnMemorySpaceAttr.from_name("global")
        add = NnAddOp(block.args[1], block.args[2], mem, space)
        block.add_op(add)
        block.add_op(func.ReturnOp(block.args[0]))
        func_op = _func("half_rewritten", [mem, mem, mem], [mem], block, ("arg0", "lhs", "rhs"))

        with pytest.raises(GenKernelError, match="legacy memory return ABI is not supported"):
            gen_kernel(func_op, _ctx())


# GK-017
# 创建者: 朽木露琪亚
# 最后一次更改: 金铲铲大作战
# 最近一次运行测试时间: 2026-04-02 21:00:00 +0800
# 最近一次运行成功时间: 2026-04-02 21:00:00 +0800
# 功能说明: 验证 npu_demo target 可生成包含 KernelContext 与 free helper 查询的 body-level kernel 骨架。
# 测试目的: 锁定签名首参仍为 `npu_demo::KernelContext& ctx`，并且查询文本显式限定为 `npu_demo::thread_id()` / `npu_demo::thread_num()`。
# 使用示例: pytest -q test/dsl/gen_kernel/test_gen_kernel.py -k test_gen_kernel_emits_npu_demo_body_level_kernel
# 对应功能实现文件路径: kernel_gen/dsl/gen_kernel/gen_kernel.py
# 对应 spec 文件路径: spec/dsl/gen_kernel/gen_kernel.md
# 对应测试文件路径: test/dsl/gen_kernel/test_gen_kernel.py
def test_gen_kernel_emits_npu_demo_body_level_kernel() -> None:
    mem = _make_memory_type([64], [1], element_type=f32)
    block = Block(arg_types=[IndexType(), mem])
    func_op = _func("demo_kernel", [IndexType(), mem], [mem], block, ("ctx", "source"))

    source = gen_kernel(func_op, _npu_ctx())

    assert source.startswith('#include "include/npu_demo/npu_demo.h"\nusing namespace npu_demo;\n\n')
    assert (
        "void demo_kernel(npu_demo::KernelContext& ctx, const Memory<MemorySpace::GM, float>& source, Memory<MemorySpace::GM, float>& out)"
        in source
    )
    assert "S_INT tid = npu_demo::thread_id();" in source
    assert "S_INT tnum = npu_demo::thread_num();" in source
    assert "npu_demo::KernelContext& ctx" in source
    assert "launch" not in source
    assert "barrier" not in source
    assert "arch.launch_kernel" not in source


# GK-S12-001
# 创建者: 小李飞刀
# 最后一次更改: 小李飞刀
# 最近一次运行测试时间: N/A
# 最近一次运行成功时间: N/A
# 功能说明: 验证 npu_demo 单函数 kernel family 会把最前置 out 参数生成为可写引用，并通过 Kernel helper 发射。
# 测试目的: 锁定 `kernel.binary_elewise(kind="add")` 在 `target=npu_demo` 下的函数签名与 helper 调用都遵循 `out-first` 口径，防止把 out 误生成为 `const Memory&`。
# 使用示例: pytest -q test/dsl/gen_kernel/test_gen_kernel.py -k test_gen_kernel_emits_npu_demo_kernel_binary_signature_out_first
# 对应功能实现文件路径: kernel_gen/dsl/gen_kernel/gen_kernel.py
# 对应 spec 文件路径: spec/dsl/gen_kernel/gen_kernel.md
# 对应测试文件路径: test/dsl/gen_kernel/test_gen_kernel.py
def test_gen_kernel_emits_npu_demo_kernel_binary_signature_out_first() -> None:
    out_type = _make_memory_type([4], [1], element_type=f64, space="tlm1")
    input_type = _make_memory_type([4], [1], element_type=i32, space="tlm1")
    block = Block(arg_types=[out_type, input_type, input_type])
    block.add_op(
        KernelBinaryElewiseOp(
            block.args[0],
            block.args[1],
            block.args[2],
            kind="add",
            space=NnMemorySpaceAttr.from_name("tlm1"),
        )
    )
    block.add_op(func.ReturnOp())
    func_op = _func(
        "kernel_binary_add_case",
        [out_type, input_type, input_type],
        [],
        block,
        ("arg0", "arg1", "arg2"),
    )

    source = gen_kernel(func_op, _npu_ctx())

    assert (
        "void kernel_binary_add_case(Memory<TLM1, double>& arg0, const Memory<TLM1, int32_t>& arg1, const Memory<TLM1, int32_t>& arg2)"
        in source
    )
    assert "const Memory<TLM1, double>& arg0" not in source
    assert "add<TLM1, int32_t, double>(arg0 /*out*/, arg1 /*lhs*/, arg2 /*rhs*/);" in source


# GK-017A
# 创建者: 小李飞刀
# 最后一次更改: 小李飞刀
# 最近一次运行测试时间: N/A
# 最近一次运行成功时间: N/A
# 功能说明: 验证 target=npu_demo 下单函数 `dma.alloc` module 可生成 helper 形式源码。
# 测试目的: 锁定 `builtin.module -> func.func(dma.alloc)` 这条 `npu_demo` 子集会发射 `alloc<Space, T>(shape, stride)`，不再被 launch module 约束误拒绝。
# 使用示例: pytest -q test/dsl/gen_kernel/test_gen_kernel.py -k test_gen_kernel_emits_npu_demo_dma_alloc_module
# 对应功能实现文件路径: kernel_gen/dsl/gen_kernel/gen_kernel.py
# 对应 spec 文件路径: spec/dsl/gen_kernel/gen_kernel.md
# 对应测试文件路径: test/dsl/gen_kernel/test_gen_kernel.py
def test_gen_kernel_emits_npu_demo_dma_alloc_module() -> None:
    static_type = _make_memory_type([2, 3], [3, 1], space="tsm", element_type=f32)
    static_block = Block()
    static_alloc = DmaAllocOp([], static_type)
    static_block.add_ops([static_alloc, func.ReturnOp()])
    static_func = func.FuncOp(
        "dma_alloc_case",
        FunctionType.from_lists([], []),
        Region(static_block),
    )
    static_module = ModuleOp([static_func])

    static_source = gen_kernel(static_module, _npu_ctx())

    assert '#include "include/npu_demo/npu_demo.h"' in static_source
    assert "void dma_alloc_case()" in static_source
    assert "Memory<TSM, float> v0 = alloc<TSM, float>({2, 3} /*shape*/, {3, 1} /*stride*/);" in static_source

    dyn_m = SymbolValueType.from_expr("M")
    dyn_n = SymbolValueType.from_expr("N")
    dynamic_type = NnMemoryType(
        ArrayAttr([StringAttr("M"), StringAttr("N")]),
        ArrayAttr([StringAttr("N"), IntAttr(1)]),
        f32,
        NnMemorySpaceAttr.from_name("tsm"),
    )
    dynamic_block = Block(arg_types=[dyn_m, dyn_n])
    dynamic_alloc = DmaAllocOp([dynamic_block.args[0], dynamic_block.args[1]], dynamic_type)
    dynamic_block.add_ops([dynamic_alloc, func.ReturnOp()])
    dynamic_func = func.FuncOp(
        "dma_alloc_dynamic_case",
        FunctionType.from_lists([dyn_m, dyn_n], []),
        Region(dynamic_block),
    )
    dynamic_module = ModuleOp([dynamic_func])

    dynamic_source = gen_kernel(dynamic_module, _npu_ctx())

    assert "void dma_alloc_dynamic_case(S_INT arg0, S_INT arg1)" in dynamic_source
    assert "Memory<TSM, float> v0 = alloc<TSM, float>({arg0, arg1} /*shape*/, {arg1, 1} /*stride*/);" in dynamic_source
    _compile_only(dynamic_source)


# GK-017A
# 创建者: jcc你莫辜负
# 最后一次更改: jcc你莫辜负
# 最近一次运行测试时间: 2026-04-05 16:36:25 +0800
# 最近一次运行成功时间: 2026-04-05 16:36:25 +0800
# 功能说明: 验证 npu_demo target 的 gen_kernel 源码仅依赖 npu_demo.h 即可编译。
# 测试目的: 补齐 compile smoke，确保只包含 `include/npu_demo/npu_demo.h` 也可通过编译。
# 使用示例: pytest -q test/dsl/gen_kernel/test_gen_kernel.py -k test_gen_kernel_compiles_npu_demo_source_with_single_include
# 对应功能实现文件路径: kernel_gen/dsl/gen_kernel/gen_kernel.py
# 对应 spec 文件路径: spec/dsl/gen_kernel/gen_kernel.md
# 对应测试文件路径: test/dsl/gen_kernel/test_gen_kernel.py
def test_gen_kernel_compiles_npu_demo_source_with_single_include() -> None:
    mem = _make_memory_type([64], [1], element_type=f32)
    block = Block(arg_types=[IndexType(), mem])
    func_op = _func("demo_kernel", [IndexType(), mem], [mem], block, ("ctx", "source"))

    source = gen_kernel(func_op, _npu_ctx())

    include_lines = [line for line in source.splitlines() if line.startswith("#include ")]
    assert include_lines == ['#include "include/npu_demo/npu_demo.h"']
    _compile_only(source)


# GK-017A
# 创建者: 小李飞刀
# 最后一次更改: 小李飞刀
# 最近一次运行测试时间: 2026-04-15 11:10:00 +0800
# 最近一次运行成功时间: N/A
# 功能说明: 验证 npu_demo target 可生成并编译 tiled matmul 源码。
# 测试目的: 锁定二维 `slice/deslice`、`symbol.for` 与 `matmul<...>(...)` 的最小编译闭环。
# 使用示例: pytest -q test/dsl/gen_kernel/test_gen_kernel.py -k test_gen_kernel_compiles_npu_demo_tiled_matmul_source
# 对应功能实现文件路径: kernel_gen/dsl/gen_kernel/gen_kernel.py
# 对应 spec 文件路径: spec/dsl/gen_kernel/gen_kernel.md
# 对应测试文件路径: test/dsl/gen_kernel/test_gen_kernel.py
def test_gen_kernel_compiles_npu_demo_tiled_matmul_source() -> None:
    def tiled_matmul(lhs: "Tensor[f32, 32, 16]", rhs: "Tensor[f32, 16, 32]") -> "Tensor[f32, 32, 32]":
        out = alloc([32, 32], NumericType.Float32, MemorySpace.GM)
        for m0 in loop(0, 32, 16):
            for n0 in loop(0, 32, 16):
                lhs_tile = slice(lhs, [m0, 0], [16, 16], [1, 1], MemorySpace.TSM)
                rhs_tile = slice(rhs, [0, n0], [16, 16], [1, 1], MemorySpace.TSM)
                partial = matmul(lhs_tile, rhs_tile)
                deslice(partial, out, [m0, n0], [16, 16], [1, 1])
        return out

    func_op = build_func_op(
        tiled_matmul,
        Memory([32, 16], NumericType.Float32),
        Memory([16, 32], NumericType.Float32),
    )
    module = ModuleOp([func_op])
    NnLoweringPass().run(module)
    BufferResultsToOutParamsPass().run(module)
    rewritten_func = next(op for op in module.ops if isinstance(op, func.FuncOp))

    source = gen_kernel(rewritten_func, _npu_ctx())

    assert source.startswith('#include "include/npu_demo/npu_demo.h"\nusing namespace npu_demo;\n')
    assert "matmul<" in source
    assert "npu_demo::matmul(" not in source
    assert "slice(" in source
    assert "deslice(" in source
    assert "cpu::matmul(" not in source
    assert "nn.matmul" not in source
    _compile_only(source)


# GK-018
# 创建者: 朽木露琪亚
# 最后一次更改: 金铲铲大作战
# 最近一次运行测试时间: 2026-04-02 21:00:00 +0800
# 最近一次运行成功时间: 2026-04-02 21:00:00 +0800
# 功能说明: 验证 npu_demo target 可生成固定的 dynamic memory/view/slice/deslice/add 管线。
# 测试目的: 锁定 `TSM/TLM`、`view/slice/deslice/add` 固定顺序，并防止回退到 `.view/load/store` 风格。
# 使用示例: pytest -q test/dsl/gen_kernel/test_gen_kernel.py -k test_gen_kernel_emits_npu_demo_memory_pipeline
# 对应功能实现文件路径: kernel_gen/dsl/gen_kernel/gen_kernel.py
# 对应 spec 文件路径: spec/dsl/gen_kernel/gen_kernel.md
# 对应测试文件路径: test/dsl/gen_kernel/test_gen_kernel.py
def test_gen_kernel_emits_npu_demo_memory_pipeline() -> None:
    mem = _make_memory_type([64], [1], element_type=f32)
    block = Block(arg_types=[IndexType(), mem])
    func_op = _func("demo_kernel", [IndexType(), mem], [mem], block, ("ctx", "source"))

    source = gen_kernel(func_op, _npu_ctx())

    tsm_idx = source.index(
        "Memory<MemorySpace::TSM, float> tsm = npu_demo::get_dynamic_memory<MemorySpace::TSM>();"
    )
    tlm_idx = source.index(
        "Memory<MemorySpace::TLM1, float> tlm = npu_demo::get_dynamic_memory<MemorySpace::TLM1>();"
    )
    src_view_idx = source.index("auto src_view = view(source, tid * 16, 16, 1);")
    work_view_idx = source.index("auto work_tile = view(tsm, 0, 16, 1);")
    out_view_idx = source.index("auto out_tile = view(tsm, 0, 16, 1);")
    slice_idx = source.index("slice(work_tile, src_view, 0, 16, 1);")
    add_idx = source.index("add<MemorySpace::TSM, float, float>(out_tile, work_tile, work_tile);")
    deslice_idx = source.index("deslice(out, out_tile, tid * 16, 16, 1);")

    assert tsm_idx < tlm_idx < src_view_idx < work_view_idx < out_view_idx < slice_idx < add_idx < deslice_idx
    assert ".view<" not in source
    assert "load<" not in source
    assert "store<" not in source
    assert "slice(source" not in source
    assert "arch.launch_kernel" not in source


# GK-019
# 创建者: 朽木露琪亚
# 最后一次更改: 朽木露琪亚
# 最近一次运行测试时间: 2026-04-02 21:25:00 +0800
# 最近一次运行成功时间: 2026-04-02 21:25:00 +0800
# 功能说明: 验证 npu_demo body-level kernel 若 body 含未知 op，必须继续报错。
# 测试目的: 防止固定骨架静默吞掉非法 body 中的未知 op。
# 使用示例: pytest -q test/dsl/gen_kernel/test_gen_kernel.py -k test_gen_kernel_rejects_npu_demo_body_level_kernel_with_unknown_body_op
# 对应功能实现文件路径: kernel_gen/dsl/gen_kernel/gen_kernel.py
# 对应 spec 文件路径: spec/dsl/gen_kernel/gen_kernel.md
# 对应测试文件路径: test/dsl/gen_kernel/test_gen_kernel.py
def test_gen_kernel_rejects_npu_demo_body_level_kernel_with_unknown_body_op() -> None:
    mem = _make_memory_type([64], [1], element_type=f32)
    block = Block(arg_types=[IndexType(), mem])
    block.add_op(UnsupportedOp())
    func_op = _func("demo_kernel", [IndexType(), mem], [mem], block, ("ctx", "source"))

    with pytest.raises(GenKernelError) as exc_info:
        gen_kernel(func_op, _npu_ctx())

    assert "test.unsupported" in str(exc_info.value)


# GK-020
# 创建者: 朽木露琪亚
# 最后一次更改: 朽木露琪亚
# 最近一次运行测试时间: 2026-04-02 21:25:00 +0800
# 最近一次运行成功时间: 2026-04-02 21:25:00 +0800
# 功能说明: 验证 npu_demo body-level kernel 若 body 非空但不含未知 op，仍必须报错。
# 测试目的: 锁定当前冻结子集只接受空 body，避免非法 return 等结构被固定骨架吞掉。
# 使用示例: pytest -q test/dsl/gen_kernel/test_gen_kernel.py -k test_gen_kernel_rejects_npu_demo_body_level_kernel_with_nonempty_body
# 对应功能实现文件路径: kernel_gen/dsl/gen_kernel/gen_kernel.py
# 对应 spec 文件路径: spec/dsl/gen_kernel/gen_kernel.md
# 对应测试文件路径: test/dsl/gen_kernel/test_gen_kernel.py
def test_gen_kernel_rejects_npu_demo_body_level_kernel_with_nonempty_body() -> None:
    mem = _make_memory_type([64], [1], element_type=f32)
    block = Block(arg_types=[IndexType(), mem])
    block.add_op(func.ReturnOp())
    func_op = _func("demo_kernel", [IndexType(), mem], [mem], block, ("ctx", "source"))

    with pytest.raises(GenKernelError, match="body must match frozen subset"):
        gen_kernel(func_op, _npu_ctx())


# GK-021
# 创建者: jcc你莫辜负
# 最后一次更改: 金铲铲大作战
# 最近一次运行测试时间: 2026-04-04 00:00:00 +0800
# 最近一次运行成功时间: 2026-04-04 00:00:00 +0800
# 功能说明: 验证函数级特化在黑盒 `gen_kernel(...)` 输出上保持既有合同。
# 测试目的: 锁定 lowered add 与 `npu_demo` 两类函数级形态继续只通过 `gen_kernel(...)` 黑盒验证，不依赖内部 helper、内部策略函数或内部策略名。
# 使用示例: pytest -q test/dsl/gen_kernel/test_gen_kernel.py -k test_gen_kernel_black_box_lowered_add_and_npu_demo_contracts
# 对应功能实现文件路径: kernel_gen/dsl/gen_kernel/gen_kernel.py
# 对应 spec 文件路径: spec/dsl/gen_kernel/gen_kernel.md
# 对应测试文件路径: test/dsl/gen_kernel/test_gen_kernel.py
def test_gen_kernel_black_box_lowered_add_and_npu_demo_contracts() -> None:
    def add_direct(lhs: "Tensor[i32, 2, 2]", rhs: "Tensor[i32, 2, 2]") -> "Tensor[i32, 2, 2]":
        return lhs + rhs

    add_source = gen_kernel(
        _lower_and_rewrite_func(build_func_op(add_direct, _tensor_arg([2, 2]), _tensor_arg([2, 2]))),
        _ctx(),
    )
    assert "cpu::add(arg1, arg2, arg0);" in add_source
    assert "out = " not in add_source

    npu_mem = _make_memory_type([64], [1], element_type=f32)
    npu_block = Block(arg_types=[IndexType(), npu_mem])
    npu_func = _func("demo_kernel", [IndexType(), npu_mem], [npu_mem], npu_block, ("ctx", "source"))
    npu_source = gen_kernel(npu_func, _npu_ctx())
    assert "npu_demo::thread_id()" in npu_source
    assert "npu_demo::get_dynamic_memory<MemorySpace::TSM>()" in npu_source
    assert "deslice(out, out_tile, tid * 16, 16, 1);" in npu_source


# GK-I2-001
# 创建者: 大闸蟹
# 最后一次更改: 朽木露琪亚
# 功能说明: 验证 `build_func_op -> pass -> gen_kernel` 的三条 nn.add CPU 路径可生成源码并完成编译执行。
# 测试目的: 作为 I4 的统一 smoke，确认公开成功链路来自 `build_func_op -> NnLoweringPass -> gen_kernel`，而不是 raw `nn.add` direct-return 特化。
# 使用示例: pytest -q test/dsl/gen_kernel/test_gen_kernel.py -k test_gen_kernel_compiles_and_runs_lowered_nn_add_variants_on_cpu
# 对应功能实现文件路径: kernel_gen/dsl/gen_kernel/gen_kernel.py
# 对应 spec 文件路径: spec/dsl/gen_kernel/gen_kernel.md
# 对应测试文件路径: test/dsl/gen_kernel/test_gen_kernel.py
def test_gen_kernel_compiles_and_runs_lowered_nn_add_variants_on_cpu() -> None:
    def add_direct(lhs: "Tensor[i32, 2, 2]", rhs: "Tensor[i32, 2, 2]") -> "Tensor[i32, 2, 2]":
        return lhs + rhs

    def add_const_direct(lhs: "Tensor[i32, 2, 2]") -> "Tensor[i32, 2, 2]":
        return lhs + 1

    def add_symbol_direct(lhs: "Tensor[i32, 2, 2]", bias: int) -> "Tensor[i32, 2, 2]":
        return lhs + bias

    pair_source = gen_kernel(
        _lower_and_rewrite_func(build_func_op(add_direct, _tensor_arg([2, 2]), _tensor_arg([2, 2]))),
        _ctx(),
    )
    const_source = gen_kernel(
        _lower_and_rewrite_func(build_func_op(add_const_direct, _tensor_arg([2, 2]))),
        _ctx(),
    )
    symbol_source = gen_kernel(
        _lower_and_rewrite_func(build_func_op(add_symbol_direct, _tensor_arg([2, 2]), SymbolDim("bias"))),
        _ctx(),
    )

    assert "cpu::add(arg1, arg2, arg0);" in pair_source
    assert "kernel." not in pair_source
    assert "nn.add" not in pair_source
    if "arg1.shape()[0]" in const_source:
        assert "arg1.shape()[1]" in const_source
    else:
        assert "long long v0_shape[2] = {2, 2};" in const_source
    assert "cpu::add(arg1, v0, arg0);" in const_source
    assert "for (long long fill0_i = 0; fill0_i < v0.element_count(); ++fill0_i) {" in const_source
    assert "v0.data()[fill0_i] = 1;" in const_source
    assert "kernel." not in const_source
    assert "nn.add" not in const_source
    if "arg1.shape()[0]" in symbol_source:
        assert "arg1.shape()[1]" in symbol_source
    else:
        assert "long long v0_shape[2] = {2, 2};" in symbol_source
    assert "cpu::add(arg1, v0, arg0);" in symbol_source
    assert "for (long long fill0_i = 0; fill0_i < v0.element_count(); ++fill0_i) {" in symbol_source
    assert "v0.data()[fill0_i] = arg2;" in symbol_source
    assert "kernel." not in symbol_source
    assert "nn.add" not in symbol_source

    cpp_source = f"""\
#include <cstdint>
#include "include/cpu/Memory.h"
#include "include/cpu/Nn.h"

using cpu::Memory;
using cpu::MemoryFormat;
using cpu::MemorySpace;

{pair_source}

{const_source}

{symbol_source}

static int fail(int code) {{ return code; }}

int main() {{
    int32_t lhs_data[4] = {{1, 2, 3, 4}};
    int32_t rhs_data[4] = {{10, 20, 30, 40}};
    int32_t out_pair_data[4] = {{0, 0, 0, 0}};
    int32_t out_const_data[4] = {{0, 0, 0, 0}};
    int32_t out_symbol_data[4] = {{0, 0, 0, 0}};
    long long shape[2] = {{2, 2}};
    long long stride[2] = {{2, 1}};

    Memory<MemorySpace::GM, int32_t> lhs(lhs_data, 2, shape, stride);
    Memory<MemorySpace::GM, int32_t> rhs(rhs_data, 2, shape, stride);
    Memory<MemorySpace::GM, int32_t> out_pair(out_pair_data, 2, shape, stride);
    Memory<MemorySpace::GM, int32_t> out_const(out_const_data, 2, shape, stride);
    Memory<MemorySpace::GM, int32_t> out_symbol(out_symbol_data, 2, shape, stride);

    add_direct(out_pair, lhs, rhs);
    add_const_direct(out_const, lhs);
    add_symbol_direct(out_symbol, lhs, 7);

    int32_t expected_pair[4] = {{11, 22, 33, 44}};
    int32_t expected_const[4] = {{2, 3, 4, 5}};
    int32_t expected_symbol[4] = {{8, 9, 10, 11}};
    for (int i = 0; i < 4; ++i) {{
        if (out_pair_data[i] != expected_pair[i]) {{
            return fail(1);
        }}
        if (out_const_data[i] != expected_const[i]) {{
            return fail(2);
        }}
        if (out_symbol_data[i] != expected_symbol[i]) {{
            return fail(3);
        }}
    }}
    return 0;
}}
"""
    _compile_and_run(cpp_source)


# GK-S3-001
# 创建者: 金铲铲大作战
# 最后一次更改: 金铲铲大作战
# 最近一次运行测试时间: N/A
# 最近一次运行成功时间: N/A
# 功能说明: 验证 gen_kernel 支持 tile-elewise after-IR 的单函数 tile loop 代码生成。
# 测试目的: 锁定 tile 因子只能来自 `tuner.param : !symbol.int<...>`，并且必须在单函数内生成显式分块循环。
# 使用示例: pytest -q test/dsl/gen_kernel/test_gen_kernel.py -k test_gen_kernel_emits_tile_codegen_single_function_tile_loop
# 对应功能实现文件路径: kernel_gen/dsl/gen_kernel/gen_kernel.py
# 对应 spec 文件路径: spec/dsl/gen_kernel/gen_kernel.md
# 对应测试文件路径: test/dsl/gen_kernel/test_gen_kernel.py
def test_gen_kernel_emits_tile_codegen_single_function_tile_loop() -> None:
    func_op = _tile_elewise_func(tile_analysis_helpers._build_module())

    source = gen_kernel(func_op, _ctx())

    assert 'tuner_param("TILE_D0")' in source
    assert 'tuner_param("TILE_D1")' in source
    assert "+= tile_d0" in source
    assert "+= tile_d1" in source
    assert "for (long long" in source
    assert "TileCodegenMalformed" not in source
    assert "TileCodegenUnexpectedHelperFunction" not in source


# GK-S3-002
# 创建者: 金铲铲大作战
# 最后一次更改: 金铲铲大作战
# 最近一次运行测试时间: N/A
# 最近一次运行成功时间: N/A
# 功能说明: 验证 tile codegen 缺少 tuner.param 时必须显式失败。
# 测试目的: 禁止 silent fallback，确保失败短语包含 TileCodegenMalformed。
# 使用示例: pytest -q test/dsl/gen_kernel/test_gen_kernel.py -k test_gen_kernel_rejects_tile_codegen_missing_tuner_param
# 对应功能实现文件路径: kernel_gen/dsl/gen_kernel/gen_kernel.py
# 对应 spec 文件路径: spec/dsl/gen_kernel/gen_kernel.md
# 对应测试文件路径: test/dsl/gen_kernel/test_gen_kernel.py
def test_gen_kernel_rejects_tile_codegen_missing_tuner_param() -> None:
    func_op = _tile_analysis_func(tile_analysis_helpers._build_module())
    block = func_op.body.block
    start = FakeSymbolValueOp("0")
    end = FakeSymbolValueOp("8")
    step = FakeSymbolValueOp("1")
    loop_body = Block(arg_types=[SymbolIterType.from_bounds("0", "8", "1")])
    loop = SymbolForOp(start.result, end.result, step.result, Region(loop_body))
    block.insert_ops_before([start, end, step, loop], block.last_op)

    with pytest.raises(GenKernelError, match="missing tuner.param"):
        gen_kernel(func_op, _ctx())


# GK-S3-003
# 创建者: 金铲铲大作战
# 最后一次更改: 金铲铲大作战
# 最近一次运行测试时间: N/A
# 最近一次运行成功时间: N/A
# 功能说明: 验证 tile codegen 缺少显式分块结构（symbol.for）时必须失败。
# 测试目的: 锁定 malformed tile IR 的 fail-fast 路径，禁止退化成未切分源码生成。
# 使用示例: pytest -q test/dsl/gen_kernel/test_gen_kernel.py -k test_gen_kernel_rejects_tile_codegen_missing_loop
# 对应功能实现文件路径: kernel_gen/dsl/gen_kernel/gen_kernel.py
# 对应 spec 文件路径: spec/dsl/gen_kernel/gen_kernel.md
# 对应测试文件路径: test/dsl/gen_kernel/test_gen_kernel.py
def test_gen_kernel_rejects_tile_codegen_missing_loop() -> None:
    func_op = _tile_analysis_func(tile_analysis_helpers._build_module())

    with pytest.raises(GenKernelError, match="missing explicit tile loop"):
        gen_kernel(func_op, _ctx())


# GK-S3-004
# 创建者: 金铲铲大作战
# 最后一次更改: 金铲铲大作战
# 最近一次运行测试时间: N/A
# 最近一次运行成功时间: N/A
# 功能说明: 验证 tile codegen 不允许出现 helper/函数抽取式承接。
# 测试目的: 当 tile IR 中出现 func.call 时必须报 TileCodegenUnexpectedHelperFunction。
# 使用示例: pytest -q test/dsl/gen_kernel/test_gen_kernel.py -k test_gen_kernel_rejects_tile_codegen_with_helper_call
# 对应功能实现文件路径: kernel_gen/dsl/gen_kernel/gen_kernel.py
# 对应 spec 文件路径: spec/dsl/gen_kernel/gen_kernel.md
# 对应测试文件路径: test/dsl/gen_kernel/test_gen_kernel.py
def test_gen_kernel_rejects_tile_codegen_with_helper_call() -> None:
    func_op = _tile_elewise_func(tile_analysis_helpers._build_module())

    loop = next(op for op in func_op.body.block.ops if isinstance(op, SymbolForOp))
    loop_block = loop.body.blocks.first
    first_op = next(iter(loop_block.ops))
    loop_block.insert_op_before(func.CallOp("helper", [], []), first_op)

    with pytest.raises(GenKernelError, match="TileCodegenUnexpectedHelperFunction"):
        gen_kernel(func_op, _ctx())


# GK-S3-005
# 创建者: 金铲铲大作战
# 最后一次更改: 金铲铲大作战
# 最近一次运行测试时间: N/A
# 最近一次运行成功时间: N/A
# 功能说明: 验证旧 split bridge 合同不再被接受。
# 测试目的: 防止实现继续接受 `tuner.param : !symbol.dim<...>` 这类旧合同。
# 使用示例: pytest -q test/dsl/gen_kernel/test_gen_kernel.py -k test_gen_kernel_rejects_legacy_split_tuner_param_contract
# 对应功能实现文件路径: kernel_gen/dsl/gen_kernel/gen_kernel.py
# 对应 spec 文件路径: spec/dsl/gen_kernel/gen_kernel.md
# 对应测试文件路径: test/dsl/gen_kernel/test_gen_kernel.py
def test_gen_kernel_rejects_legacy_split_tuner_param_contract() -> None:
    mem_type = _make_memory_type([8, 4], [4, 1])
    block = Block(arg_types=[mem_type])
    tuner = TunerParamOp(SymbolDimType.from_name("TILE_M"))
    block.add_ops([tuner, func.ReturnOp()])
    func_op = func.FuncOp("legacy_split_contract", FunctionType.from_lists([mem_type], []), Region(block))

    with pytest.raises(GenKernelError, match="TileCodegenMalformed"):
        gen_kernel(func_op, _ctx())


# GK-S5-001
# 创建者: 小李飞刀
# 最后一次更改: 小李飞刀
# 最近一次运行测试时间: N/A
# 最近一次运行成功时间: N/A
# 功能说明: 验证 tile-elewise after-IR 的 elementwise/broadcast 可生成稳定的 CPU 源码绑定。
# 测试目的: 锁定 `tuner_param("TILE_D0")` 与 `cpu::add` / `cpu::broadcast` 的公开收口口径。
# 使用示例: pytest -q test/dsl/gen_kernel/test_gen_kernel.py -k test_gen_kernel_emits_tile_elewise_cpu_source_for_elementwise_and_broadcast
# 对应功能实现文件路径: kernel_gen/dsl/gen_kernel/gen_kernel.py
# 对应 spec 文件路径: spec/dsl/gen_kernel/gen_kernel.md
# 对应测试文件路径: test/dsl/gen_kernel/test_gen_kernel.py
@pytest.mark.parametrize(
    ("builder", "expected_tuners", "expected_fragment"),
    [
        pytest.param(
            tile_analysis_helpers._build_module,
            ("tuner_param(\"TILE_D0\")", "tuner_param(\"TILE_D1\")"),
            "cpu::add(",
            id="elementwise",
        ),
        pytest.param(
            tile_analysis_helpers._build_broadcast_module,
            ("tuner_param(\"TILE_D0\")",),
            "cpu::broadcast(",
            id="broadcast",
        ),
    ],
)
def test_gen_kernel_emits_tile_elewise_cpu_source_for_elementwise_and_broadcast(
    builder: object,
    expected_tuners: tuple[str, ...],
    expected_fragment: str,
) -> None:
    func_op = _tile_elewise_func(builder())
    source = gen_kernel(func_op, _ctx())

    assert source.count("tuner_param(") == len(expected_tuners)
    for needle in expected_tuners:
        assert needle in source
    assert expected_fragment in source
    assert "tile.step_value" not in source
    assert "kernel_split.tile_value" not in source


# GK-S4-001
# 创建者: 小李飞刀
# 最后一次更改: 金铲铲大作战
# 最近一次运行测试时间: 2026-04-06 12:40:00 +0800
# 最近一次运行成功时间: 2026-04-06 12:40:00 +0800
# 功能说明: 验证 `target=\"npu_demo\"` 的受控 module 输入可生成 wrapper + body 双函数源码，并允许 helper func.func 按 module 顺序输出。
# 测试目的: 让 gate `-k 'npu_demo and barrier'` 命中真实正例，锁定 `launch<1, 1, 1, 0>`、双 barrier、helper 顺序与固定 body 语义。
# 使用示例: pytest -q test/dsl/gen_kernel/test_gen_kernel.py -k test_gen_kernel_emits_npu_demo_launch_wrapper_and_barrier_body
# 对应功能实现文件路径: kernel_gen/dsl/gen_kernel/gen_kernel.py
# 对应 spec 文件路径: spec/dsl/gen_kernel/gen_kernel.md
# 对应测试文件路径: test/dsl/gen_kernel/test_gen_kernel.py
@pytest.mark.parametrize(
    ("tlm_space", "space_enum"),
    [("tlm1", "TLM1"), ("tlm2", "TLM2"), ("tlm3", "TLM3")],
)
def test_gen_kernel_emits_npu_demo_launch_wrapper_and_barrier_body(tlm_space: str, space_enum: str) -> None:
    module = _make_npu_demo_add_barrier_module(
        tlm_space=tlm_space,
        top_level_extra_ops=(_make_npu_demo_helper_func(),),
    )

    source = gen_kernel(module, _npu_ctx())

    assert source.startswith('#include "include/npu_demo/npu_demo.h"\nusing namespace npu_demo;\n\n')
    assert source.index("static void add_barrier_body(") < source.index("void add_barrier(") < source.index("void npu_demo_helper()")
    assert (
        "static void add_barrier_body(npu_demo::KernelContext& ctx, const Memory<GM, float>& lhs, "
        "const Memory<GM, float>& rhs, Memory<GM, float>& out)"
        in source
    )
    assert (
        "void add_barrier(const Memory<MemorySpace::GM, float>& lhs, "
        "const Memory<MemorySpace::GM, float>& rhs, Memory<MemorySpace::GM, float>& out)"
        in source
    )
    assert "npu_demo::launch<1, 1, 1, 0>(add_barrier_body, lhs, rhs, out);" in source
    assert source.count("ctx.barrier({BarrierVisibility::TSM, BarrierVisibility::TLM}, BarrierScope::BLOCK);") == 2
    assert source.index("S_INT v0 = npu_demo::thread_id();") < source.index(
        "Memory<TSM, float> v2 = npu_demo::get_dynamic_memory<TSM>();"
    )
    assert f"Memory<{space_enum}, float> v3 = npu_demo::get_dynamic_memory<{space_enum}>();" in source
    assert "npu_demo::thread_id() * 16" in source
    assert source.index("slice(v6 /*dst*/, v4 /*source*/, 0 /*offset*/, 16 /*size*/, 1 /*stride*/);") < source.index(
        "add<TSM, float, float>(v8 /*out*/, v6 /*lhs*/, v7 /*rhs*/);"
    ) < source.index(
        "deslice(out /*target*/, v8 /*source*/, npu_demo::thread_id() * 16 /*offset*/, 16 /*size*/, 1 /*stride*/);"
    )
    assert "arch.launch_kernel" not in source
    assert "ctx.sync_threads" not in source


# GK-S4-002
# 创建者: 小李飞刀
# 最后一次更改: 小李飞刀
# 最近一次运行测试时间: 2026-04-06 12:40:00 +0800
# 最近一次运行成功时间: 2026-04-06 12:40:00 +0800
# 功能说明: 验证 `npu_demo add+barrier` 双函数源码可仅依赖 `include/npu_demo/npu_demo.h` 通过编译。
# 测试目的: 防止 body/wrapper 输出在 include、签名、barrier 或 launch 模板参数上产生不可编译回退。
# 使用示例: pytest -q test/dsl/gen_kernel/test_gen_kernel.py -k test_gen_kernel_compiles_npu_demo_launch_wrapper_and_barrier_body
# 对应功能实现文件路径: kernel_gen/dsl/gen_kernel/gen_kernel.py
# 对应 spec 文件路径: spec/dsl/gen_kernel/gen_kernel.md
# 对应测试文件路径: test/dsl/gen_kernel/test_gen_kernel.py
def test_gen_kernel_compiles_npu_demo_launch_wrapper_and_barrier_body() -> None:
    module = _make_npu_demo_add_barrier_module()

    source = gen_kernel(module, _npu_ctx())

    include_lines = [line for line in source.splitlines() if line.startswith("#include ")]
    assert include_lines == ['#include "include/npu_demo/npu_demo.h"']
    _compile_only(source)


# GK-018A
# 创建者: 朽木露琪亚
# 最后一次更改: 朽木露琪亚
# 最近一次运行测试时间: 未运行
# 最近一次运行成功时间: 未运行
# 功能说明: 验证 `target="npu_demo"` 的完整 module 可继续输出普通 kernel 与 `compute/memory` sibling cost functions。
# 测试目的: 锁定 `gen_kernel` 会为 `_cost_compute_*` / `_cost_memory_*` 生成 `S_INT` 返回签名、对应 Kind 的 `cost::add` helper 调用，以及稳定的 `return total;`。
# 使用示例: pytest -q test/dsl/gen_kernel/test_gen_kernel.py -k test_gen_kernel_emits_npu_demo_cost_functions_for_compute_and_memory
# 对应功能实现文件路径: kernel_gen/dsl/gen_kernel/gen_kernel.py
# 对应 spec 文件路径: spec/dsl/gen_kernel/gen_kernel.md
# 对应测试文件路径: test/dsl/gen_kernel/test_gen_kernel.py
def test_gen_kernel_emits_npu_demo_cost_functions_for_compute_and_memory() -> None:
    module = _make_npu_demo_cost_function_module()

    source = gen_kernel(module, _npu_ctx())

    assert source.startswith('#include "include/npu_demo/npu_demo.h"\nusing namespace npu_demo;\n\n')
    assert source.index("static void add_barrier_body(") < source.index("void add_barrier(")
    assert source.index("void add_barrier(") < source.index("S_INT _cost_compute_add_barrier_body(")
    assert source.index("S_INT _cost_compute_add_barrier_body(") < source.index("S_INT _cost_memory_add_barrier_body(")
    assert "S_INT _cost_compute_add_barrier_body(" in source
    assert "S_INT _cost_memory_add_barrier_body(" in source
    assert "S_INT cost0 = cost::add<GM, float, float, compute>(out /*out*/, lhs /*lhs*/, rhs /*rhs*/);" in source
    assert "S_INT cost1 = cost::add<GM, float, float, memory>(out /*out*/, lhs /*lhs*/, rhs /*rhs*/);" in source
    assert "S_INT total = (cost0 + cost0);" in source
    assert "S_INT total = (cost1 + cost1);" in source
    assert source.count("return total;") == 2
    assert "using namespace npu_demo::cost;" not in source


# GK-018B
# 创建者: 朽木露琪亚
# 最后一次更改: 朽木露琪亚
# 最近一次运行测试时间: 未运行
# 最近一次运行成功时间: 未运行
# 功能说明: 验证包含 sibling cost functions 的 `npu_demo` module 只依赖 `include/npu_demo/npu_demo.h` 即可编译。
# 测试目的: 锁定 `wrapper/body + _cost_compute_* + _cost_memory_*` 共存时，`S_INT` 返回签名、`return total;` 和单入口 include 合同不会回退。
# 使用示例: pytest -q test/dsl/gen_kernel/test_gen_kernel.py -k test_gen_kernel_compiles_npu_demo_cost_function_module
# 对应功能实现文件路径: kernel_gen/dsl/gen_kernel/gen_kernel.py
# 对应 spec 文件路径: spec/dsl/gen_kernel/gen_kernel.md
# 对应测试文件路径: test/dsl/gen_kernel/test_gen_kernel.py
def test_gen_kernel_compiles_npu_demo_cost_function_module() -> None:
    module = _make_npu_demo_cost_function_module()

    source = gen_kernel(module, _npu_ctx())

    include_lines = [line for line in source.splitlines() if line.startswith("#include ")]
    assert include_lines == ['#include "include/npu_demo/npu_demo.h"']
    assert source.count("return total;") == 2
    _compile_only(source)


# GK-S4-002A
# 创建者: jcc你莫辜负
# 最后一次更改: jcc你莫辜负
# 最近一次运行测试时间: 未运行
# 最近一次运行成功时间: 未运行
# 功能说明: 验证单函数 `npu_demo` launch IR 经过 outline 后，gen_kernel 先输出 body 前置声明再输出 wrapper/definition，并保持可编译。
# 测试目的: 直接覆盖 outline 后 wrapper 先于 body 的源码顺序回退，防止 wrapper 先引用未声明 body。
# 使用示例: pytest -q test/dsl/gen_kernel/test_gen_kernel.py -k test_gen_kernel_compiles_outlined_npu_demo_launch_module
# 对应功能实现文件路径: kernel_gen/dsl/gen_kernel/gen_kernel.py
# 对应 spec 文件路径: spec/dsl/gen_kernel/gen_kernel.md
# 对应测试文件路径: test/dsl/gen_kernel/test_gen_kernel.py
def test_gen_kernel_compiles_outlined_npu_demo_launch_module() -> None:
    module = _parse_npu_demo_launch_module(
        """
builtin.module {
  func.func @kernel(
    %lhs : !nn.memory<[4], [1], f32, #nn.space<global>>,
    %rhs : !nn.memory<[4], [1], f32, #nn.space<global>>,
    %out : !nn.memory<[4], [1], f32, #nn.space<global>>
  ) attributes {
    launch_block = 1 : i64,
    launch_thread = 1 : i64,
    launch_subthread = 1 : i64,
    shared_memory_size = 0 : i64
  } {
    func.return
  }
}
"""
    )

    OutlineDeviceKernelPass().run(module)
    module.verify()

    source = gen_kernel(module, _npu_ctx())

    assert source.index("static void kernel_device(") < source.index("void kernel(")
    assert source.count("static void kernel_device(") == 2
    assert "npu_demo::launch<1, 1, 1, 0>(kernel_device" in source
    _compile_only(source)


# GK-S6-001
# 创建者: 小李飞刀
# 最后一次更改: 小李飞刀
# 最近一次运行测试时间: 2026-04-06 13:20:00 +0800
# 最近一次运行成功时间: 2026-04-06 13:20:00 +0800
# 功能说明: 验证 `npu_demo add+barrier` 受控 module 生成源码后可编译为真实可执行程序，并保留 barrier 运行时证明入口。
# 测试目的: 让 gate `-k 'npu_demo_add_barrier_runtime_smoke'` 命中 `DSL -> gen_kernel -> C++ 编译` 闭环，避免只停留在源码文本断言。
# 使用示例: pytest -q test/dsl/gen_kernel/test_gen_kernel.py -k test_gen_kernel_npu_demo_add_barrier_runtime_smoke
# 对应功能实现文件路径: kernel_gen/dsl/gen_kernel/gen_kernel.py
# 对应 spec 文件路径: spec/dsl/gen_kernel/gen_kernel.md
# 对应测试文件路径: test/dsl/gen_kernel/test_gen_kernel.py
def test_gen_kernel_npu_demo_add_barrier_runtime_smoke() -> None:
    module = _make_npu_demo_add_barrier_module()

    source = gen_kernel(module, _npu_ctx())

    assert "static void add_barrier_body" in source
    assert "ctx.barrier({BarrierVisibility::TSM, BarrierVisibility::TLM}, BarrierScope::BLOCK);" in source
    _compile_and_run_npu_demo_add_barrier_source(source, prove_barrier_runtime=False)


# GK-S4-003
# 创建者: 小李飞刀
# 最后一次更改: 小李飞刀
# 最近一次运行测试时间: 2026-04-06 12:40:00 +0800
# 最近一次运行成功时间: 2026-04-06 12:40:00 +0800
# 功能说明: 验证 wrapper 若引用缺失 body symbol，`gen_kernel` 必须显式失败且错误包含缺失 callee。
# 测试目的: 锁定受控 module 的 fail-fast 边界，避免 silent fallback 到单函数 npu_demo body-level 生成。
# 使用示例: pytest -q test/dsl/gen_kernel/test_gen_kernel.py -k test_gen_kernel_rejects_npu_demo_barrier_wrapper_missing_body_symbol
# 对应功能实现文件路径: kernel_gen/dsl/gen_kernel/gen_kernel.py
# 对应 spec 文件路径: spec/dsl/gen_kernel/gen_kernel.md
# 对应测试文件路径: test/dsl/gen_kernel/test_gen_kernel.py
def test_gen_kernel_rejects_npu_demo_barrier_wrapper_missing_body_symbol() -> None:
    module = _make_npu_demo_add_barrier_module(callee_name="missing_body")

    with pytest.raises(GenKernelError, match="missing body missing_body"):
        gen_kernel(module, _npu_ctx())


# GK-S4-004
# 创建者: 小李飞刀
# 最后一次更改: 小李飞刀
# 最近一次运行测试时间: 2026-04-06 10:52:00 +0800
# 最近一次运行成功时间: 2026-04-06 10:52:00 +0800
# 功能说明: 验证 `npu_demo` 受控 module 的关键 fail-fast 门禁与错误短语保持稳定。
# 测试目的: 锁定 module 顶层、wrapper 形态、callee、launch extent、barrier 属性与 target 边界，避免 silent fallback。
# 使用示例: pytest -q test/dsl/gen_kernel/test_gen_kernel.py -k test_gen_kernel_rejects_npu_demo_barrier_fail_fast_boundaries
# 对应功能实现文件路径: kernel_gen/dsl/gen_kernel/gen_kernel.py
# 对应 spec 文件路径: spec/dsl/gen_kernel/gen_kernel.md
# 对应测试文件路径: test/dsl/gen_kernel/test_gen_kernel.py
@pytest.mark.parametrize(
    ("module", "ctx", "pattern"),
    [
        pytest.param(
            _make_npu_demo_add_barrier_module(top_level_extra_ops=(FakeSymbolValueOp("9"),)),
            _npu_ctx(),
            r"must contain only func\.func",
            id="top-level-non-func",
        ),
        pytest.param(
            _make_npu_demo_add_barrier_module(include_wrapper=False),
            _npu_ctx(),
            r"must contain exactly one wrapper func with arch\.launch",
            id="func-count-not-two",
        ),
        pytest.param(
            _make_npu_demo_add_barrier_module(emit_wrapper_return=False),
            _npu_ctx(),
            r"must contain arch\.launch followed by func\.return",
            id="wrapper-not-launch-return",
        ),
        pytest.param(
            _make_npu_demo_add_barrier_module(callee_attr=SymbolRefAttr("add_barrier_body", ["nested"])),
            _npu_ctx(),
            r"must use flat @callee",
            id="callee-not-flat",
        ),
        pytest.param(
            _make_npu_demo_add_barrier_module(thread_extent_expr="THREADS"),
            _npu_ctx(),
            r"thread must be static integer",
            id="extent-not-static",
        ),
        pytest.param(
            _make_npu_demo_add_barrier_module(thread_extent_expr="8"),
            _npu_ctx(),
            r"must use npu_demo::launch<1, 1, 1, 0>; got block=1, thread=8, subthread=1, shared_memory_size=0",
            id="extent-not-1-1-1",
        ),
        pytest.param(
            _make_npu_demo_add_barrier_module(barrier_scope="thread"),
            _npu_ctx(),
            r"barrier scope must be block",
            id="barrier-scope-invalid",
        ),
        pytest.param(
            _make_npu_demo_add_barrier_module(barrier_visibility_names=("tlm", "tsm")),
            _npu_ctx(),
            r"barrier visibility must be \[tsm, tlm\]",
            id="barrier-visibility-invalid",
        ),
        pytest.param(
            _make_npu_demo_add_barrier_module(),
            _ctx(),
            r"builtin\.module is only supported for target=npu_demo",
            id="module-input-rejected-on-cpu",
        ),
    ],
)
def test_gen_kernel_rejects_npu_demo_barrier_fail_fast_boundaries(
    module: ModuleOp,
    ctx: EmitCContext,
    pattern: str,
) -> None:
    with pytest.raises(GenKernelError, match=pattern):
        gen_kernel(module, ctx)
