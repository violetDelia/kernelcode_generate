"""nn_lowering cast tests.

创建者: 小李飞刀
最后一次更改: jcc你莫辜负

功能说明:
- 验证 nn.cast lower 为 dma.alloc + dma.cast。

使用示例:
- pytest -q test/pass/nn_lowering/cast.py

关联文件:
- 功能实现: kernel_gen/passes/lowering/nn_lowering/select_cast_lowering.py
- Spec 文档: spec/pass/lowering/nn_lowering/spec.md
- 测试文件: test/pass/nn_lowering/cast.py
"""

from __future__ import annotations

import sys
from pathlib import Path
from collections.abc import Callable

from xdsl.dialects import func
from xdsl.dialects.builtin import (
    ArrayAttr,
    BFloat16Type,
    FunctionType,
    IntAttr,
    ModuleOp,
    f32,
    i32,
)
from xdsl.ir import Attribute, Block, Operation, Region

REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from kernel_gen.dialect.dma import DmaAllocOp, DmaCastOp
from kernel_gen.dialect.nn import NnCastOp, NnMemorySpaceAttr, NnMemoryType
from kernel_gen.passes.lowering.nn_lowering import NnLoweringPass


def _make_memory_type(element_type: Attribute = i32) -> NnMemoryType:
    """构造默认 memory type。

    创建者: 小李飞刀
    最后一次更改: 小李飞刀

    功能说明:
    - 生成 rank=2 的 nn.memory 类型。

    使用示例:
    - mem_type = _make_memory_type()

    关联文件:
    - spec: spec/pass/lowering/nn_lowering/spec.md
    - test: test/pass/nn_lowering/cast.py
    - 功能实现: kernel_gen/passes/lowering/nn_lowering/select_cast_lowering.py
    """

    shape = ArrayAttr([IntAttr(4), IntAttr(8)])
    stride = ArrayAttr([IntAttr(8), IntAttr(1)])
    return NnMemoryType(shape, stride, element_type, NnMemorySpaceAttr.from_name("global"))


def _build_module(
    arg_types: list[Attribute],
    result_type: NnMemoryType,
    op_builder: Callable[[Block], list[Operation]],
) -> tuple[ModuleOp, Block]:
    """构造包含单个 func 的 module。

    创建者: 小李飞刀
    最后一次更改: 小李飞刀

    功能说明:
    - 按顺序插入 ops 并追加 func.return。

    使用示例:
    - module, block = _build_module([input_type], result_type, lambda block: [nn_op])

    关联文件:
    - spec: spec/pass/lowering/nn_lowering/spec.md
    - test: test/pass/nn_lowering/cast.py
    - 功能实现: kernel_gen/passes/lowering/nn_lowering/select_cast_lowering.py
    """

    block = Block(arg_types=arg_types)
    ops = op_builder(block)
    if not ops:
        raise ValueError("op_builder must return at least one operation")
    for op in ops:
        block.add_op(op)
    block.add_op(func.ReturnOp(ops[-1].results[0]))
    func_type = FunctionType.from_lists(arg_types, [result_type])
    func_op = func.FuncOp("main", func_type, Region(block))
    module = ModuleOp([func_op])
    return module, block


# TC-PASS-NNL-S2-013
# 创建者: 小李飞刀
# 最后一次更改: jcc你莫辜负
# 最近一次运行测试时间: 2026-04-12 06:47:55 +0800
# 最近一次运行成功时间: 2026-04-12 06:47:55 +0800
# 测试目的: 验证 nn.cast lower 为 dma.alloc + dma.cast。
# 使用示例: pytest -q test/pass/nn_lowering/cast.py -k test_lower_cast_to_dma_cast
# 对应功能实现文件路径: kernel_gen/passes/lowering/nn_lowering/select_cast_lowering.py
# 对应 spec 文件路径: spec/pass/lowering/nn_lowering/spec.md
# 对应测试文件路径: test/pass/nn_lowering/cast.py
def test_lower_cast_to_dma_cast() -> None:
    input_type = _make_memory_type(element_type=i32)
    result_type = _make_memory_type(element_type=f32)
    space = NnMemorySpaceAttr.from_name("global")

    module, block = _build_module(
        [input_type],
        result_type,
        lambda block: [NnCastOp(block.args[0], result_type, space)],
    )
    NnLoweringPass().run(module)

    ops = list(block.ops)
    assert any(isinstance(op, DmaCastOp) for op in ops)
    assert any(isinstance(op, DmaAllocOp) for op in ops)
    assert not any(op.name.startswith("nn.") for op in ops)


# TC-PASS-NNL-S3-001
# 创建者: jcc你莫辜负
# 最后一次更改: jcc你莫辜负
# 测试目的: 验证 nn.cast 支持 bfloat16 并 lower 为 dma.cast。
# 使用示例: pytest -q test/pass/nn_lowering/cast.py -k test_lower_cast_bfloat16_to_dma_cast
# 对应功能实现文件路径: kernel_gen/passes/lowering/nn_lowering/select_cast_lowering.py
# 对应 spec 文件路径: spec/pass/lowering/nn_lowering/spec.md
# 对应测试文件路径: test/pass/nn_lowering/cast.py
def test_lower_cast_bfloat16_to_dma_cast() -> None:
    input_type = _make_memory_type(element_type=i32)
    result_type = _make_memory_type(element_type=BFloat16Type())
    space = NnMemorySpaceAttr.from_name("global")

    module, block = _build_module(
        [input_type],
        result_type,
        lambda block: [NnCastOp(block.args[0], result_type, space)],
    )
    NnLoweringPass().run(module)

    ops = list(block.ops)
    assert any(isinstance(op, DmaCastOp) for op in ops)
    assert any(isinstance(op, DmaAllocOp) for op in ops)
    assert not any(op.name.startswith("nn.") for op in ops)
