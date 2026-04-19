"""S4 gen_kernel expectation helper.

创建者: 朽木露琪亚
最后一次更改: 朽木露琪亚

功能说明:
- 为 `script/run-op-mlir-s4-gen-kernel-expectation.sh` 提供 worktree 内可直接执行的 Python 入口。
- 在不修改只读 `expectation` 资产的前提下，复现当前 `npu_demo add+barrier` 受控 module 的固定源码合同。
- 锁定 `launch<1,4,1>`、双 `barrier`、`out_tsm` 写回与 `npu_demo::add<...>(out, lhs, rhs)` 的当前公开生成口径。

使用示例:
- `python3 script/run_op_mlir_s4_gen_kernel_expectation.py`

关联文件:
- spec: ARCHITECTURE/plan/operation_mlir_gen_expectation_green_plan.md
- test: test/script/test_run_op_mlir_s4_gen_kernel_expectation.py
- 功能实现: script/run_op_mlir_s4_gen_kernel_expectation.py
"""

from __future__ import annotations

from pathlib import Path
import sys

from xdsl.dialects import func
from xdsl.dialects.builtin import ArrayAttr, FunctionType, IndexType, IntAttr, ModuleOp, StringAttr, SymbolRefAttr, f32
from xdsl.ir import Block, Region, Operation
from xdsl.irdl import IRDLOperation, irdl_op_definition, result_def

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from kernel_gen.dialect.arch import (  # noqa: E402
    ArchBarrierOp,
    ArchGetDynamicMemoryOp,
    ArchGetThreadIdOp,
    ArchGetThreadNumOp,
    ArchLaunchOp,
    ArchScopeAttr,
    ArchVisibilityAttr,
)
from kernel_gen.dialect.dma import DmaDesliceOp, DmaSliceOp, DmaViewOp  # noqa: E402
from kernel_gen.dialect.nn import NnAddOp, NnMemorySpaceAttr, NnMemoryType  # noqa: E402
from kernel_gen.dialect.symbol import SymbolValueType  # noqa: E402
from kernel_gen.dsl.emit_c import EmitCContext  # noqa: E402
from kernel_gen.dsl.gen_kernel import gen_kernel  # noqa: E402


@irdl_op_definition
class FakeSymbolValueOp(IRDLOperation):
    """测试入口使用的 `!symbol.int<"...">` 产生 op。"""

    name = "test.fake_symbol_value"
    result = result_def(SymbolValueType)

    def __init__(self: "FakeSymbolValueOp", expr: str) -> None:
        super().__init__(result_types=[SymbolValueType.from_expr(expr)])


def _make_memory_type(shape: list[int], stride: list[int], *, space: str, element_type: object = f32) -> NnMemoryType:
    """构造当前入口使用的 `!nn.memory` 类型。"""

    return NnMemoryType(
        ArrayAttr([IntAttr(dim) for dim in shape]),
        ArrayAttr([IntAttr(dim) for dim in stride]),
        element_type,
        NnMemorySpaceAttr.from_name(space),
    )


def _arg_attrs(*names: str) -> ArrayAttr:
    """构造 `func.func` 的参数名属性。"""

    from xdsl.dialects.builtin import DictionaryAttr

    return ArrayAttr([DictionaryAttr({"name": StringAttr(name)}) for name in names])


def _func(name: str, input_types: list[object], block: Block, arg_names: tuple[str, ...]) -> func.FuncOp:
    """构造本入口使用的最小 `func.func`。"""

    func_type = FunctionType.from_lists(input_types, [])
    return func.FuncOp(name, func_type, Region(block), arg_attrs=_arg_attrs(*arg_names))


def _build_module(tlm_space: str) -> ModuleOp:
    """构造当前 `npu_demo add+barrier` 的受控 module。"""

    gm_type = _make_memory_type([64], [1], space="global")
    tsm_buffer_type = _make_memory_type([256], [1], space="tsm")
    tlm_buffer_type = _make_memory_type([64], [1], space=tlm_space)
    tsm_tile_type = _make_memory_type([16], [1], space="tsm")
    visibility = ArrayAttr([ArchVisibilityAttr.from_name("tsm"), ArchVisibilityAttr.from_name("tlm")])

    body_block = Block(arg_types=[IndexType(), gm_type, gm_type, gm_type])
    lhs_offset = FakeSymbolValueOp("thread_id * 16")
    rhs_offset = FakeSymbolValueOp("64 + thread_id * 16")
    out_offset = FakeSymbolValueOp("128 + thread_id * 16")
    zero = FakeSymbolValueOp("0")
    size = FakeSymbolValueOp("16")
    stride = FakeSymbolValueOp("1")
    tid = ArchGetThreadIdOp()
    tnum = ArchGetThreadNumOp()
    tsm = ArchGetDynamicMemoryOp(NnMemorySpaceAttr.from_name("tsm"), tsm_buffer_type)
    tlm = ArchGetDynamicMemoryOp(NnMemorySpaceAttr.from_name(tlm_space), tlm_buffer_type)
    lhs_gm = DmaViewOp(body_block.args[1], [lhs_offset.result], [size.result], [stride.result], tsm_tile_type)
    rhs_gm = DmaViewOp(body_block.args[2], [lhs_offset.result], [size.result], [stride.result], tsm_tile_type)
    lhs_tsm = DmaViewOp(tsm.result, [lhs_offset.result], [size.result], [stride.result], tsm_tile_type)
    rhs_tsm = DmaViewOp(tsm.result, [rhs_offset.result], [size.result], [stride.result], tsm_tile_type)
    out_tsm = DmaViewOp(tsm.result, [out_offset.result], [size.result], [stride.result], tsm_tile_type)
    lhs_slice = DmaSliceOp(lhs_tsm.result, lhs_gm.result, [zero.result], [size.result], [stride.result])
    rhs_slice = DmaSliceOp(rhs_tsm.result, rhs_gm.result, [zero.result], [size.result], [stride.result])
    barrier0 = ArchBarrierOp(ArchScopeAttr.from_name("block"), visibility)
    add = NnAddOp(lhs_tsm.result, rhs_tsm.result, tsm_tile_type, NnMemorySpaceAttr.from_name("tsm"))
    barrier1 = ArchBarrierOp(ArchScopeAttr.from_name("block"), visibility)
    deslice = DmaDesliceOp(body_block.args[3], add.result, [lhs_offset.result], [size.result], [stride.result], gm_type)
    body_block.add_ops(
        [
            lhs_offset,
            rhs_offset,
            out_offset,
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
    body_func = _func("add_barrier_body", [IndexType(), gm_type, gm_type, gm_type], body_block, ("ctx", "lhs", "rhs", "out"))

    wrapper_block = Block(arg_types=[gm_type, gm_type, gm_type])
    block_extent = FakeSymbolValueOp("1")
    thread_extent = FakeSymbolValueOp("4")
    subthread_extent = FakeSymbolValueOp("1")
    wrapper_block.add_ops(
        [
            block_extent,
            thread_extent,
            subthread_extent,
            ArchLaunchOp(
                SymbolRefAttr("add_barrier_body"),
                block_extent.result,
                thread_extent.result,
                subthread_extent.result,
                (wrapper_block.args[0], wrapper_block.args[1], wrapper_block.args[2]),
            ),
            func.ReturnOp(),
        ]
    )
    wrapper_func = _func("add_barrier", [gm_type, gm_type, gm_type], wrapper_block, ("lhs", "rhs", "out"))
    return ModuleOp([body_func, wrapper_func])


def _expected(space_enum: str) -> str:
    """返回当前 worktree 约束下的固定源码文本。"""

    return f"""#include "include/npu_demo/npu_demo.h"

static void add_barrier_body(npu_demo::KernelContext& ctx, const Memory<MemorySpace::GM, float>& lhs, const Memory<MemorySpace::GM, float>& rhs, Memory<MemorySpace::GM, float>& out) {{
    long long tid = ctx.thread_id();
    long long tnum = ctx.thread_num();

    Memory<MemorySpace::TSM, float> tsm = ctx.get_dynamic_memory<MemorySpace::TSM, float>();
    Memory<MemorySpace::{space_enum}, float> tlm = ctx.get_dynamic_memory<MemorySpace::{space_enum}, float>();

    auto lhs_gm = view(lhs, tid * 16, 16, 1);
    auto rhs_gm = view(rhs, tid * 16, 16, 1);

    auto lhs_tsm = view(tsm, tid * 16, 16, 1);
    auto rhs_tsm = view(tsm, 64 + tid * 16, 16, 1);
    auto out_tsm = view(tsm, 128 + tid * 16, 16, 1);

    slice(lhs_tsm, lhs_gm, 0, 16, 1);
    slice(rhs_tsm, rhs_gm, 0, 16, 1);
    ctx.barrier({{BarrierVisibility::TSM, BarrierVisibility::TLM}}, BarrierScope::BLOCK);

    npu_demo::add<MemorySpace::TSM, float, float>(out_tsm, lhs_tsm, rhs_tsm);
    ctx.barrier({{BarrierVisibility::TSM, BarrierVisibility::TLM}}, BarrierScope::BLOCK);

    deslice(out, out_tsm, tid * 16, 16, 1);
}}

void add_barrier(const Memory<MemorySpace::GM, float>& lhs, const Memory<MemorySpace::GM, float>& rhs, Memory<MemorySpace::GM, float>& out) {{
    npu_demo::launch<1, 4, 1>(add_barrier_body, lhs, rhs, out);
}}"""


def main() -> None:
    """执行 `tlm1/tlm2/tlm3` 三组固定合同校验。"""

    for tlm_space, space_enum in (("tlm1", "TLM1"), ("tlm2", "TLM2"), ("tlm3", "TLM3")):
        source = gen_kernel(_build_module(tlm_space), EmitCContext(target="npu_demo"))
        assert source == _expected(space_enum)


if __name__ == "__main__":
    main()
