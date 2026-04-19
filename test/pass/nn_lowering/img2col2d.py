"""nn_lowering img2col2d tests.

创建者: 小李飞刀
最后一次更改: 朽木露琪亚

功能说明:
- 验证 nn.img2col2d -> kernel.img2col2d 的 lowering 目标与 symbol.int 参数约束。

使用示例:
- pytest -q test/pass/nn_lowering/img2col2d.py

关联文件:
- 功能实现: kernel_gen/passes/lowering/nn_lowering/matmul_img2col_lowering.py
- Spec 文档: spec/pass/lowering/nn_lowering/matmul_img2col_lowering.md
- 测试文件: test/pass/nn_lowering/img2col2d.py
"""

from __future__ import annotations

import sys
from pathlib import Path

from xdsl.dialects import func
from xdsl.dialects.builtin import ArrayAttr, FunctionType, IntAttr, ModuleOp, StringAttr, f32
from xdsl.ir import Block, Region

REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from kernel_gen.dialect.kernel import KernelImg2col2dOp
from kernel_gen.dialect.nn import NnImg2col2dOp, NnMemorySpaceAttr, NnMemoryType
from kernel_gen.dialect.symbol import SymbolConstOp, SymbolValueType
from kernel_gen.passes.lowering.nn_lowering import NnLoweringPass


# TC-PASS-NNL-022
# 创建者: 小李飞刀
# 最后一次更改: 朽木露琪亚
# 最近一次运行测试时间: 2026-04-12 09:19:46 +0800
# 最近一次运行成功时间: 2026-04-12 09:19:46 +0800
# 测试目的: 验证 nn.img2col2d lowering 目标为 kernel.img2col2d 且参数为 symbol.int。
# 使用示例: pytest -q test/pass/nn_lowering/img2col2d.py -k test_nn_lowering_img2col2d_target
# 对应功能实现文件路径: kernel_gen/passes/lowering/nn_lowering/matmul_img2col_lowering.py
# 对应 spec 文件路径: spec/pass/lowering/nn_lowering/matmul_img2col_lowering.md
# 对应测试文件路径: test/pass/nn_lowering/img2col2d.py
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

    NnLoweringPass().run(module)

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

    NnLoweringPass().run(module)
    module_text = str(module)

    kernel_ops = [op for op in module.walk() if isinstance(op, KernelImg2col2dOp)]
    assert len(kernel_ops) == 1
    assert not any(isinstance(op, NnImg2col2dOp) for op in module.walk())
    assert 'floor((-DIL_H_DIM*(KH_DIM - 1) + HEIGHT_DIM + PAD_H0_DIM + PAD_H1_DIM - 1)/STEP_H_DIM) + 1' in module_text
    assert 'floor((-DIL_W_DIM*(KW_DIM - 1) + PAD_W0_DIM + PAD_W1_DIM + WIDTH_DIM - 1)/STEP_W_DIM) + 1' in module_text
