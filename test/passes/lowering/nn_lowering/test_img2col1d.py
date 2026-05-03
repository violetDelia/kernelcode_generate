"""nn_lowering img2col1d tests.


功能说明:
- 验证 nn.img2col1d -> kernel.img2col1d 的 lowering 目标与 symbol.int 参数约束。

使用示例:
- pytest -q test/passes/lowering/nn_lowering/test_img2col1d.py

关联文件:
- 功能实现: kernel_gen/passes/lowering/nn_lowering/matmul_img2col_lowering.py
- Spec 文档: spec/pass/lowering/nn_lowering/matmul_img2col_lowering.md
- 测试文件: test/passes/lowering/nn_lowering/test_img2col1d.py
"""

from __future__ import annotations

import sys
from pathlib import Path

from xdsl.context import Context
from xdsl.dialects import func
from xdsl.dialects.builtin import ArrayAttr, FunctionType, IntAttr, ModuleOp, StringAttr, f32
from xdsl.ir import Block, Region

REPO_ROOT = Path(__file__).resolve().parents[4]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from kernel_gen.dialect.kernel import KernelImg2col1dOp
from kernel_gen.dialect.nn import NnImg2col1dOp, NnMemorySpaceAttr, NnMemoryType
from kernel_gen.dialect.symbol import SymbolConstOp, SymbolValueType
from kernel_gen.passes.lowering.nn_lowering import NnLoweringPass


# TC-PASS-NNL-021
# 测试目的: 验证 nn.img2col1d lowering 目标为 kernel.img2col1d 且参数为 symbol.int。
# 使用示例: pytest -q test/passes/lowering/nn_lowering/test_img2col1d.py -k test_nn_lowering_img2col1d_target
# 对应功能实现文件路径: kernel_gen/passes/lowering/nn_lowering/matmul_img2col_lowering.py
# 对应 spec 文件路径: spec/pass/lowering/nn_lowering/matmul_img2col_lowering.md
# 对应测试文件路径: test/passes/lowering/nn_lowering/test_img2col1d.py
def test_nn_lowering_img2col1d_target() -> None:
    space = NnMemorySpaceAttr(StringAttr("global"))
    input_type = NnMemoryType(
        ArrayAttr([IntAttr(1), IntAttr(3), IntAttr(5)]),
        ArrayAttr([IntAttr(15), IntAttr(5), IntAttr(1)]),
        f32,
        space,
    )
    result_type = NnMemoryType(
        ArrayAttr([IntAttr(1), IntAttr(3), IntAttr(3), IntAttr(5)]),
        ArrayAttr([IntAttr(45), IntAttr(15), IntAttr(5), IntAttr(1)]),
        f32,
        space,
    )

    block = Block(arg_types=[input_type])
    kw = SymbolConstOp(3)
    sw = SymbolConstOp(1)
    dw = SymbolConstOp(1)
    pl = SymbolConstOp(1)
    pr = SymbolConstOp(1)
    img2col = NnImg2col1dOp(
        block.args[0],
        result_type,
        kw=kw.result,
        sw=sw.result,
        dw=dw.result,
        pl=pl.result,
        pr=pr.result,
        space=space,
    )
    for op in [kw, sw, dw, pl, pr, img2col]:
        block.add_op(op)
    block.add_op(func.ReturnOp(img2col.result))
    func_type = FunctionType.from_lists([input_type], [result_type])
    func_op = func.FuncOp("main", func_type, Region(block))
    module = ModuleOp([func_op])

    NnLoweringPass().apply(Context(), module)

    kernel_ops = [op for op in module.walk() if isinstance(op, KernelImg2col1dOp)]
    assert len(kernel_ops) == 1
    assert not any(isinstance(op, NnImg2col1dOp) for op in module.walk())
    kernel_op = kernel_ops[0]
    assert isinstance(kernel_op.k.type, SymbolValueType)
    assert isinstance(kernel_op.s.type, SymbolValueType)
    assert isinstance(kernel_op.d.type, SymbolValueType)
    assert isinstance(kernel_op.p_left.type, SymbolValueType)
    assert isinstance(kernel_op.p_right.type, SymbolValueType)


def test_nn_lowering_img2col1d_accepts_noncanonical_symbol_names() -> None:
    """TC-PASS-NNL-021A: 动态 img2col1d 不应依赖固定符号名。"""

    space = NnMemorySpaceAttr(StringAttr("global"))
    input_type = NnMemoryType(
        ArrayAttr([StringAttr("BATCH_DIM"), StringAttr("CHANNEL_DIM"), StringAttr("WIDTH_DIM")]),
        ArrayAttr([StringAttr("CHANNEL_DIM*WIDTH_DIM"), StringAttr("WIDTH_DIM"), IntAttr(1)]),
        f32,
        space,
    )
    result_type = NnMemoryType(
        ArrayAttr(
            [
                StringAttr("BATCH_DIM"),
                StringAttr("CHANNEL_DIM"),
                StringAttr("WIN_DIM"),
                StringAttr("OUT_EXTENT_DIM"),
            ]
        ),
        ArrayAttr(
            [
                StringAttr("CHANNEL_DIM*WIN_DIM*OUT_EXTENT_DIM"),
                StringAttr("WIN_DIM*OUT_EXTENT_DIM"),
                StringAttr("OUT_EXTENT_DIM"),
                IntAttr(1),
            ]
        ),
        f32,
        space,
    )
    symbol_types = [
        SymbolValueType.from_expr("WIN_DIM"),
        SymbolValueType.from_expr("STEP_DIM"),
        SymbolValueType.from_expr("DILATION_DIM"),
        SymbolValueType.from_expr("PAD_LEFT_DIM"),
        SymbolValueType.from_expr("PAD_RIGHT_DIM"),
    ]

    block = Block(arg_types=[input_type, *symbol_types])
    img2col = NnImg2col1dOp(
        block.args[0],
        result_type,
        kw=block.args[1],
        sw=block.args[2],
        dw=block.args[3],
        pl=block.args[4],
        pr=block.args[5],
        space=space,
    )
    block.add_op(img2col)
    block.add_op(func.ReturnOp(img2col.result))
    func_type = FunctionType.from_lists([input_type, *symbol_types], [result_type])
    func_op = func.FuncOp("dynamic_img2col1d", func_type, Region(block))
    module = ModuleOp([func_op])

    NnLoweringPass().apply(Context(), module)
    module_text = str(module)

    kernel_ops = [op for op in module.walk() if isinstance(op, KernelImg2col1dOp)]
    assert len(kernel_ops) == 1
    assert not any(isinstance(op, NnImg2col1dOp) for op in module.walk())
    assert '(-DILATION_DIM*(WIN_DIM - 1) + PAD_LEFT_DIM + PAD_RIGHT_DIM + WIDTH_DIM - 1) // STEP_DIM + 1' in module_text
