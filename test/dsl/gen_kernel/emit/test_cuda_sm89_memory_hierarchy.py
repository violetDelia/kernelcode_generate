"""CUDA SM89 memory hierarchy source tests.

功能说明:
- 通过公开 final IR / emit 入口验证 CUDA SM89 memory space marker 与 C5 all-TLM1 materialization。
- 锁定 `kernel.matmul` staging 必须写回原 out descriptor，避免内存层级语义只停留在 comment。

使用示例:
- pytest -q test/dsl/gen_kernel/emit/test_cuda_sm89_memory_hierarchy.py

关联文件:
- 功能实现: kernel_gen/dsl/gen_kernel/emit/cuda_sm89/source_bundle.py
- Spec 文档: spec/pass/pipeline/cuda_sm89_lowering.md
- 测试文件: test/dsl/gen_kernel/emit/test_cuda_sm89_memory_hierarchy.py
"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
import sys

import pytest
from xdsl.dialects import func
from xdsl.dialects.builtin import ArrayAttr, ModuleOp, f32
from xdsl.ir import Block, Region

REPO_ROOT = Path(__file__).resolve().parents[4]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from kernel.matmul.inputs_static_tile_static import matmul_inputs_static_tile_static_kernel
from kernel_gen.core.config import reset_config, set_target
from kernel_gen.core.error import KernelCodeError
from kernel_gen.dialect.dma import DmaAllocOp, DmaCopyOp, DmaFreeOp
from kernel_gen.dialect.kernel import KernelMatmulOp
from kernel_gen.dialect.nn import NnMemorySpaceAttr, NnMemoryType
from kernel_gen.dialect.symbol import SymbolExprAttr
from kernel_gen.dsl.ast.mlir_gen import mlir_gen
from kernel_gen.dsl.gen_kernel import EmitCContext, emit_c
from kernel_gen.pipeline import build_cuda_sm89_lowering_pipeline
from kernel_gen.symbol_variable.memory import Memory
from kernel_gen.symbol_variable.type import NumericType


def _emit_cuda_sm89_source(
    kernel_fn: Callable[..., None],
    annotations: dict[str, str],
    compile_args: tuple[object, ...],
) -> str:
    """通过公开入口生成 CUDA SM89 aggregate source。

    功能说明:
    - 临时设置 demo kernel annotations，生成公开 MLIR module。
    - 运行公开 `cuda-sm89-lowering` pipeline 后调用公开 `emit_c(...)`。
    - finally 恢复 annotations 和全局 target，避免污染其它用例。

    使用示例:
    - source = _emit_cuda_sm89_source(fn, annotations, args)
    """

    original_annotations = dict(kernel_fn.__annotations__)
    kernel_fn.__annotations__.update(annotations)
    try:
        reset_config()
        set_target("cuda_sm89")
        module = mlir_gen(kernel_fn, *compile_args)
        build_cuda_sm89_lowering_pipeline().run(module)
        source = emit_c(module, EmitCContext())
        if "// kg.cuda.ir.memory_spaces:" not in source:
            raise AssertionError("missing CUDA SM89 memory-space marker")
        return source
    finally:
        kernel_fn.__annotations__.clear()
        kernel_fn.__annotations__.update(original_annotations)
        reset_config()


def _make_minimal_c5_matmul_module(
    *,
    lhs_space: str = "tlm1",
    include_writeback: bool = True,
) -> ModuleOp:
    """构造最小 C5 `kernel.matmul` final IR module。

    功能说明:
    - 使用公开 dialect op 构造 `dma.alloc/copy/free + kernel.matmul` final IR 片段。
    - `lhs_space` 与 `include_writeback` 用于验证 materialization fail-fast 边界。
    - 不依赖 CUDA SM89 package-local helper，测试只通过公开 `emit_c(...)` 观察行为。

    使用示例:
    - module = _make_minimal_c5_matmul_module(lhs_space="tlm2")
    """

    out_shape = ArrayAttr([SymbolExprAttr.from_expr("2"), SymbolExprAttr.from_expr("4")])
    out_stride = ArrayAttr([SymbolExprAttr.from_expr("4"), SymbolExprAttr.from_expr("1")])
    lhs_shape = ArrayAttr([SymbolExprAttr.from_expr("2"), SymbolExprAttr.from_expr("3")])
    lhs_stride = ArrayAttr([SymbolExprAttr.from_expr("3"), SymbolExprAttr.from_expr("1")])
    rhs_shape = ArrayAttr([SymbolExprAttr.from_expr("3"), SymbolExprAttr.from_expr("4")])
    rhs_stride = ArrayAttr([SymbolExprAttr.from_expr("4"), SymbolExprAttr.from_expr("1")])
    out_type = NnMemoryType(out_shape, out_stride, f32, NnMemorySpaceAttr.from_name("global"))
    lhs_type = NnMemoryType(lhs_shape, lhs_stride, f32, NnMemorySpaceAttr.from_name("global"))
    rhs_type = NnMemoryType(rhs_shape, rhs_stride, f32, NnMemorySpaceAttr.from_name("global"))
    block = Block(arg_types=[out_type, lhs_type, rhs_type])
    staged_out_type = NnMemoryType(out_shape, out_stride, f32, NnMemorySpaceAttr.from_name("tlm1"))
    staged_lhs_type = NnMemoryType(lhs_shape, lhs_stride, f32, NnMemorySpaceAttr.from_name(lhs_space))
    staged_rhs_type = NnMemoryType(rhs_shape, rhs_stride, f32, NnMemorySpaceAttr.from_name("tlm1"))
    staged_out = DmaAllocOp([], staged_out_type)
    staged_lhs = DmaAllocOp([], staged_lhs_type)
    staged_rhs = DmaAllocOp([], staged_rhs_type)
    block.add_ops(
        [
            staged_out,
            staged_lhs,
            staged_rhs,
            DmaCopyOp(staged_out.result, block.args[0]),
            DmaCopyOp(staged_lhs.result, block.args[1]),
            DmaCopyOp(staged_rhs.result, block.args[2]),
            KernelMatmulOp(staged_out.result, staged_lhs.result, staged_rhs.result, NnMemorySpaceAttr.from_name("tlm1")),
        ]
    )
    if include_writeback:
        block.add_op(DmaCopyOp(block.args[0], staged_out.result))
    block.add_ops([DmaFreeOp(staged_out.result), DmaFreeOp(staged_lhs.result), DmaFreeOp(staged_rhs.result), func.ReturnOp()])
    func_op = func.FuncOp("minimal_c5_matmul", ([out_type, lhs_type, rhs_type], []), Region(block))
    module = ModuleOp([func_op])
    return module


@pytest.fixture(autouse=True)
def _reset_core_config_fixture() -> None:
    """重置公开 target 配置。

    功能说明:
    - 每个测试前恢复默认配置，避免 target 状态从其它测试泄漏。
    - 每个测试后再次 reset，保证失败路径也不会污染后续用例。

    使用示例:
    - 由 pytest 自动应用。
    """

    reset_config()
    try:
        yield
    finally:
        reset_config()


def test_cuda_sm89_lowered_matmul_exposes_memory_spaces_and_c5_writeback() -> None:
    """验证 lowered matmul source 暴露 memory hierarchy 与 C5 write-back。

    功能说明:
    - 从公开 matmul demo 入口生成 CUDA SM89 source。
    - 锁定 global/tlm1/tsm marker、all-TLM1 materialization marker 和 generated memory wrapper calls。

    使用示例:
    - pytest -q test/dsl/gen_kernel/emit/test_cuda_sm89_memory_hierarchy.py -k memory_spaces
    """

    source = _emit_cuda_sm89_source(
        matmul_inputs_static_tile_static_kernel,
        {
            "out": "Tensor[f32, 2, 4]",
            "lhs": "Tensor[f32, 2, 3]",
            "rhs": "Tensor[f32, 3, 4]",
            "bias": "Tensor[f32, 4]",
        },
        (
            Memory([2, 4], NumericType.Float32),
            Memory([2, 3], NumericType.Float32),
            Memory([3, 4], NumericType.Float32),
            Memory([4], NumericType.Float32),
        ),
    )

    assert "// kg.cuda.ir.memory_spaces: global,tlm1,tsm" in source
    assert "// kg.cuda.ir.matmul.materialization: out=tlm1,lhs=tlm1,rhs=tlm1,write_back=visible" in source
    assert "// kg.cuda.ir.op: dma.copy" in source
    assert "// kg.cuda.ir.op: dma.free" in source
    assert "cuda_sm89::alloc<MemorySpace::TLM1" in source
    assert "cuda_sm89::load<" in source
    assert "cuda_sm89::deslice<MemorySpace::GM" in source
    assert "cuda_sm89::matmul<" in source
    assert "get_dynamic_memory<TLM" not in source


def test_cuda_sm89_matmul_materialization_fails_fast_for_invalid_c5() -> None:
    """验证 C5 matmul materialization 不满足时 fail-fast。

    功能说明:
    - 使用公开 dialect op 构造非 all-TLM1 与缺失 write-back 的 final IR。
    - 通过公开 `emit_c(...)` 验证错误来自真实 memory/dataflow 检查。

    使用示例:
    - pytest -q test/dsl/gen_kernel/emit/test_cuda_sm89_memory_hierarchy.py -k invalid_c5
    """

    set_target("cuda_sm89")
    with pytest.raises(KernelCodeError, match="kernel.matmul C5 materialization requires out/lhs/rhs tlm1; got tlm1,tlm2,tlm1"):
        emit_c(_make_minimal_c5_matmul_module(lhs_space="tlm2"), EmitCContext())
    with pytest.raises(KernelCodeError, match="kernel.matmul C5 materialization requires visible out write-back"):
        emit_c(_make_minimal_c5_matmul_module(include_writeback=False), EmitCContext())
