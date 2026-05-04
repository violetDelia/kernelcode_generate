"""nn_lowering img2col2d tests.


功能说明:
- 验证 nn.img2col2d -> kernel.img2col2d 的 lowering 目标与 symbol.int 参数约束。

使用示例:
- pytest -q test/passes/lowering/nn_lowering/test_img2col2d.py

关联文件:
- 功能实现: kernel_gen/passes/lowering/nn_lowering/matmul_img2col_lowering.py
- Spec 文档: spec/pass/lowering/nn_lowering/matmul_img2col_lowering.md
- 测试文件: test/passes/lowering/nn_lowering/test_img2col2d.py
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest
from xdsl.context import Context
from xdsl.dialects import func
from xdsl.dialects.builtin import ArrayAttr, FunctionType, IntAttr, ModuleOp, StringAttr, f32, i32
from xdsl.ir import Block, Region

REPO_ROOT = Path(__file__).resolve().parents[4]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from kernel_gen.dialect.dma import DmaAllocOp
from kernel_gen.dialect.kernel import KernelImg2col2dOp
from kernel_gen.dialect.nn import NnImg2col2dOp, NnMemorySpaceAttr, NnMemoryType
from kernel_gen.dialect.symbol import SymbolConstOp, SymbolValueType
from kernel_gen.core.error import KernelCodeError
from kernel_gen.passes.lowering.nn_lowering import NnLoweringPass


# TC-PASS-NNL-022
# 测试目的: 验证 nn.img2col2d lowering 目标为 kernel.img2col2d 且参数为 symbol.int。
# 使用示例: pytest -q test/passes/lowering/nn_lowering/test_img2col2d.py -k test_nn_lowering_img2col2d_target
# 对应功能实现文件路径: kernel_gen/passes/lowering/nn_lowering/matmul_img2col_lowering.py
# 对应 spec 文件路径: spec/pass/lowering/nn_lowering/matmul_img2col_lowering.md
# 对应测试文件路径: test/passes/lowering/nn_lowering/test_img2col2d.py
def test_nn_lowering_img2col2d_target() -> None:
    space = NnMemorySpaceAttr(StringAttr("global"))
    input_type = NnMemoryType(
        ArrayAttr([IntAttr(1), IntAttr(3), IntAttr(5), IntAttr(5)]),
        ArrayAttr([IntAttr(75), IntAttr(25), IntAttr(5), IntAttr(1)]),
        f32,
        space,
    )
    result_type = NnMemoryType(
        ArrayAttr([IntAttr(1), IntAttr(3), IntAttr(3), IntAttr(3), IntAttr(3), IntAttr(3)]),
        ArrayAttr([IntAttr(243), IntAttr(81), IntAttr(27), IntAttr(9), IntAttr(3), IntAttr(1)]),
        f32,
        space,
    )

    block = Block(arg_types=[input_type])
    kh = SymbolConstOp(3)
    kw = SymbolConstOp(3)
    sh = SymbolConstOp(1)
    sw = SymbolConstOp(1)
    dh = SymbolConstOp(1)
    dw = SymbolConstOp(1)
    ph = SymbolConstOp(0)
    pw = SymbolConstOp(0)
    pl = SymbolConstOp(0)
    pr = SymbolConstOp(0)
    img2col = NnImg2col2dOp(
        block.args[0],
        result_type,
        kh=kh.result,
        kw=kw.result,
        sh=sh.result,
        sw=sw.result,
        dh=dh.result,
        dw=dw.result,
        ph=ph.result,
        pw=pw.result,
        pl=pl.result,
        pr=pr.result,
        space=space,
    )
    for op in [kh, kw, sh, sw, dh, dw, ph, pw, pl, pr, img2col]:
        block.add_op(op)
    block.add_op(func.ReturnOp(img2col.result))
    func_type = FunctionType.from_lists([input_type], [result_type])
    func_op = func.FuncOp("main", func_type, Region(block))
    module = ModuleOp([func_op])

    NnLoweringPass().apply(Context(), module)

    kernel_ops = [op for op in module.walk() if isinstance(op, KernelImg2col2dOp)]
    assert len(kernel_ops) == 1
    assert not any(isinstance(op, NnImg2col2dOp) for op in module.walk())
    kernel_op = kernel_ops[0]
    assert isinstance(kernel_op.kh.type, SymbolValueType)
    assert isinstance(kernel_op.kw.type, SymbolValueType)
    assert isinstance(kernel_op.sh.type, SymbolValueType)
    assert isinstance(kernel_op.sw.type, SymbolValueType)
    assert isinstance(kernel_op.dh.type, SymbolValueType)
    assert isinstance(kernel_op.dw.type, SymbolValueType)
    assert isinstance(kernel_op.ph.type, SymbolValueType)
    assert isinstance(kernel_op.pw.type, SymbolValueType)
    assert isinstance(kernel_op.pl.type, SymbolValueType)
    assert isinstance(kernel_op.pr.type, SymbolValueType)


def test_nn_lowering_img2col2d_accepts_noncanonical_symbol_names() -> None:
    """TC-PASS-NNL-022A: 动态 img2col2d 不应依赖固定符号名。"""

    space = NnMemorySpaceAttr(StringAttr("global"))
    input_type = NnMemoryType(
        ArrayAttr(
            [
                StringAttr("BATCH_DIM"),
                StringAttr("CHANNEL_DIM"),
                StringAttr("HEIGHT_DIM"),
                StringAttr("WIDTH_DIM"),
            ]
        ),
        ArrayAttr(
            [
                StringAttr("CHANNEL_DIM*HEIGHT_DIM*WIDTH_DIM"),
                StringAttr("HEIGHT_DIM*WIDTH_DIM"),
                StringAttr("WIDTH_DIM"),
                IntAttr(1),
            ]
        ),
        f32,
        space,
    )
    result_type = NnMemoryType(
        ArrayAttr(
            [
                StringAttr("BATCH_DIM"),
                StringAttr("CHANNEL_DIM"),
                StringAttr("KH_DIM"),
                StringAttr("KW_DIM"),
                StringAttr("OH_DIM"),
                StringAttr("OW_DIM"),
            ]
        ),
        ArrayAttr(
            [
                StringAttr("CHANNEL_DIM*KH_DIM*KW_DIM*OH_DIM*OW_DIM"),
                StringAttr("KH_DIM*KW_DIM*OH_DIM*OW_DIM"),
                StringAttr("KW_DIM*OH_DIM*OW_DIM"),
                StringAttr("OH_DIM*OW_DIM"),
                StringAttr("OW_DIM"),
                IntAttr(1),
            ]
        ),
        f32,
        space,
    )
    symbol_types = [
        SymbolValueType.from_expr("KH_DIM"),
        SymbolValueType.from_expr("KW_DIM"),
        SymbolValueType.from_expr("STEP_H_DIM"),
        SymbolValueType.from_expr("STEP_W_DIM"),
        SymbolValueType.from_expr("DIL_H_DIM"),
        SymbolValueType.from_expr("DIL_W_DIM"),
        SymbolValueType.from_expr("PAD_H0_DIM"),
        SymbolValueType.from_expr("PAD_H1_DIM"),
        SymbolValueType.from_expr("PAD_W0_DIM"),
        SymbolValueType.from_expr("PAD_W1_DIM"),
    ]

    block = Block(arg_types=[input_type, *symbol_types])
    img2col = NnImg2col2dOp(
        block.args[0],
        result_type,
        kh=block.args[1],
        kw=block.args[2],
        sh=block.args[3],
        sw=block.args[4],
        dh=block.args[5],
        dw=block.args[6],
        ph=block.args[7],
        pw=block.args[8],
        pl=block.args[9],
        pr=block.args[10],
        space=space,
    )
    block.add_op(img2col)
    block.add_op(func.ReturnOp(img2col.result))
    func_type = FunctionType.from_lists([input_type, *symbol_types], [result_type])
    func_op = func.FuncOp("dynamic_img2col2d", func_type, Region(block))
    module = ModuleOp([func_op])

    NnLoweringPass().apply(Context(), module)
    module_text = str(module)

    kernel_ops = [op for op in module.walk() if isinstance(op, KernelImg2col2dOp)]
    assert len(kernel_ops) == 1
    assert not any(isinstance(op, NnImg2col2dOp) for op in module.walk())
    assert '(-DIL_H_DIM*(KH_DIM - 1) + HEIGHT_DIM + PAD_H0_DIM + PAD_H1_DIM - 1) // STEP_H_DIM + 1' in module_text
    assert '(-DIL_W_DIM*(KW_DIM - 1) + PAD_W0_DIM + PAD_W1_DIM + WIDTH_DIM - 1) // STEP_W_DIM + 1' in module_text


def test_nn_lowering_img2col2d_runtime_dim_result_uses_full_rank_alloc_shape() -> None:
    """匿名 runtime 维度 img2col2d 结果通过 full-rank dma.alloc dynamic_shape 验证。"""

    space = NnMemorySpaceAttr(StringAttr("global"))
    input_type = NnMemoryType(
        ArrayAttr(
            [
                StringAttr("runtime_dim_0"),
                StringAttr("runtime_dim_1"),
                StringAttr("runtime_dim_2"),
                StringAttr("runtime_dim_3"),
            ]
        ),
        ArrayAttr(
            [
                StringAttr("runtime_dim_1*runtime_dim_2*runtime_dim_3"),
                StringAttr("runtime_dim_2*runtime_dim_3"),
                StringAttr("runtime_dim_3"),
                IntAttr(1),
            ]
        ),
        f32,
        space,
    )
    result_type = NnMemoryType(
        ArrayAttr(
            [
                StringAttr("runtime_dim_0"),
                StringAttr("runtime_dim_1"),
                IntAttr(3),
                IntAttr(3),
                StringAttr("runtime_dim_4"),
                StringAttr("runtime_dim_5"),
            ]
        ),
        ArrayAttr(
            [
                StringAttr("9*runtime_dim_1*runtime_dim_4*runtime_dim_5"),
                StringAttr("9*runtime_dim_4*runtime_dim_5"),
                StringAttr("3*runtime_dim_4*runtime_dim_5"),
                StringAttr("runtime_dim_4*runtime_dim_5"),
                StringAttr("runtime_dim_5"),
                IntAttr(1),
            ]
        ),
        f32,
        space,
    )
    block = Block(arg_types=[input_type])
    params = [
        SymbolConstOp(3),
        SymbolConstOp(3),
        SymbolConstOp(1),
        SymbolConstOp(1),
        SymbolConstOp(1),
        SymbolConstOp(1),
        SymbolConstOp(0),
        SymbolConstOp(0),
        SymbolConstOp(0),
        SymbolConstOp(0),
    ]
    img2col = NnImg2col2dOp(
        block.args[0],
        result_type,
        kh=params[0].result,
        kw=params[1].result,
        sh=params[2].result,
        sw=params[3].result,
        dh=params[4].result,
        dw=params[5].result,
        ph=params[6].result,
        pw=params[7].result,
        pl=params[8].result,
        pr=params[9].result,
        space=space,
    )
    for op in [*params, img2col]:
        block.add_op(op)
    block.add_op(func.ReturnOp(img2col.result))
    module = ModuleOp(
        [
            func.FuncOp(
                "runtime_dim_img2col2d",
                FunctionType.from_lists([input_type], [result_type]),
                Region(block),
            )
        ]
    )

    NnLoweringPass().apply(Context(), module)

    allocs = [op for op in module.walk() if isinstance(op, DmaAllocOp)]
    assert any(len(op.dynamic_shape) == 6 and len(op.results[0].type.shape.data) == 6 for op in allocs)
    assert len([op for op in module.walk() if isinstance(op, KernelImg2col2dOp)]) == 1


# TC-PASS-NNL-022B
# 测试目的: 验证 nn.img2col2d 参数类型、动态源轴和结果 rank 错误保持公开错误语义。
# 使用示例: pytest -q test/passes/lowering/nn_lowering/test_img2col2d.py -k test_nn_lowering_img2col2d_public_error_matrix
# 对应功能实现文件路径: kernel_gen/passes/lowering/nn_lowering/matmul_img2col_lowering.py
# 对应 spec 文件路径: spec/pass/lowering/nn_lowering/matmul_img2col_lowering.md
# 对应测试文件路径: test/passes/lowering/nn_lowering/test_img2col2d.py
def test_nn_lowering_img2col2d_public_error_matrix() -> None:
    space = NnMemorySpaceAttr(StringAttr("global"))
    input_type = NnMemoryType(
        ArrayAttr([IntAttr(1), IntAttr(3), IntAttr(5), IntAttr(5)]),
        ArrayAttr([IntAttr(75), IntAttr(25), IntAttr(5), IntAttr(1)]),
        f32,
        space,
    )
    result_type = NnMemoryType(
        ArrayAttr([IntAttr(1), IntAttr(3), IntAttr(3), IntAttr(3), StringAttr("OH_DIM"), StringAttr("OW_DIM")]),
        ArrayAttr([StringAttr("243"), StringAttr("81"), StringAttr("27"), StringAttr("9"), StringAttr("OW_DIM"), IntAttr(1)]),
        f32,
        space,
    )

    param_type_block = Block(arg_types=[input_type, i32])
    kw = SymbolConstOp(3)
    sh = SymbolConstOp(1)
    sw = SymbolConstOp(1)
    dh = SymbolConstOp(1)
    dw = SymbolConstOp(1)
    ph = SymbolConstOp(0)
    pw = SymbolConstOp(0)
    pl = SymbolConstOp(0)
    pr = SymbolConstOp(0)
    param_type_op = NnImg2col2dOp(
        param_type_block.args[0],
        result_type,
        kh=param_type_block.args[1],
        kw=kw.result,
        sh=sh.result,
        sw=sw.result,
        dh=dh.result,
        dw=dw.result,
        ph=ph.result,
        pw=pw.result,
        pl=pl.result,
        pr=pr.result,
        space=space,
    )
    for op in [kw, sh, sw, dh, dw, ph, pw, pl, pr, param_type_op]:
        param_type_block.add_op(op)
    param_type_block.add_op(func.ReturnOp(param_type_op.result))
    param_type_module = ModuleOp(
        [
            func.FuncOp(
                "img2col2d_param_type_error",
                FunctionType.from_lists([input_type, i32], [result_type]),
                Region(param_type_block),
            )
        ]
    )
    with pytest.raises(KernelCodeError, match="nn img2col parameters must be symbol.int"):
        NnLoweringPass().apply(Context(), param_type_module)

    static_source_block = Block(arg_types=[input_type])
    const_ops = [SymbolConstOp(value) for value in (3, 3, 1, 1, 1, 1, 0, 0, 0, 0)]
    static_source_op = NnImg2col2dOp(
        static_source_block.args[0],
        result_type,
        kh=const_ops[0].result,
        kw=const_ops[1].result,
        sh=const_ops[2].result,
        sw=const_ops[3].result,
        dh=const_ops[4].result,
        dw=const_ops[5].result,
        ph=const_ops[6].result,
        pw=const_ops[7].result,
        pl=const_ops[8].result,
        pr=const_ops[9].result,
        space=space,
    )
    for op in [*const_ops, static_source_op]:
        static_source_block.add_op(op)
    static_source_block.add_op(func.ReturnOp(static_source_op.result))
    static_source_module = ModuleOp(
        [
            func.FuncOp(
                "img2col2d_static_source_error",
                FunctionType.from_lists([input_type], [result_type]),
                Region(static_source_block),
            )
        ]
    )
    with pytest.raises(KernelCodeError, match="nn img2col symbolic dim must come from symbolic source axis"):
        NnLoweringPass().apply(Context(), static_source_module)

    dynamic_input_type = NnMemoryType(
        ArrayAttr([StringAttr("BATCH_DIM"), StringAttr("CHANNEL_DIM"), StringAttr("HEIGHT_DIM"), StringAttr("WIDTH_DIM")]),
        ArrayAttr([StringAttr("CHANNEL_DIM*HEIGHT_DIM*WIDTH_DIM"), StringAttr("HEIGHT_DIM*WIDTH_DIM"), StringAttr("WIDTH_DIM"), IntAttr(1)]),
        f32,
        space,
    )
    rank_result_type = NnMemoryType(
        ArrayAttr(
            [
                StringAttr("BATCH_DIM"),
                StringAttr("CHANNEL_DIM"),
                StringAttr("KH_DIM"),
                StringAttr("KW_DIM"),
                StringAttr("OH_DIM"),
                StringAttr("OW_DIM"),
                StringAttr("EXTRA_DIM"),
            ]
        ),
        ArrayAttr(
            [
                StringAttr("CHANNEL_DIM*KH_DIM*KW_DIM*OH_DIM*OW_DIM*EXTRA_DIM"),
                StringAttr("KH_DIM*KW_DIM*OH_DIM*OW_DIM*EXTRA_DIM"),
                StringAttr("KW_DIM*OH_DIM*OW_DIM*EXTRA_DIM"),
                StringAttr("OH_DIM*OW_DIM*EXTRA_DIM"),
                StringAttr("OW_DIM*EXTRA_DIM"),
                StringAttr("EXTRA_DIM"),
                IntAttr(1),
            ]
        ),
        f32,
        space,
    )
    rank_block = Block(arg_types=[dynamic_input_type])
    rank_const_ops = [SymbolConstOp(value) for value in (3, 3, 1, 1, 1, 1, 0, 0, 0, 0)]
    rank_op = NnImg2col2dOp(
        rank_block.args[0],
        rank_result_type,
        kh=rank_const_ops[0].result,
        kw=rank_const_ops[1].result,
        sh=rank_const_ops[2].result,
        sw=rank_const_ops[3].result,
        dh=rank_const_ops[4].result,
        dw=rank_const_ops[5].result,
        ph=rank_const_ops[6].result,
        pw=rank_const_ops[7].result,
        pl=rank_const_ops[8].result,
        pr=rank_const_ops[9].result,
        space=space,
    )
    for op in [*rank_const_ops, rank_op]:
        rank_block.add_op(op)
    rank_block.add_op(func.ReturnOp(rank_op.result))
    rank_module = ModuleOp(
        [
            func.FuncOp(
                "img2col2d_rank_error",
                FunctionType.from_lists([dynamic_input_type], [rank_result_type]),
                Region(rank_block),
            )
        ]
    )
    with pytest.raises(KernelCodeError, match="nn img2col2d result rank must be 6"):
        NnLoweringPass().apply(Context(), rank_module)
