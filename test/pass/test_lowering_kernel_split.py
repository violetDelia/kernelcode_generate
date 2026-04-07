"""kernel_split pass tests.

创建者: 小李飞刀
最后一次更改: 小李飞刀

功能说明:
- 验证 KernelSplitPass 与 TilePass 行为一致（生成 loop/view）。
- 保留兼容入口：name 固定为 "tile"，错误类型可用。

使用示例:
- pytest -q test/pass/test_lowering_kernel_split.py

当前覆盖率信息:
- `kernel_gen.passes.lowering.kernel_split`：待统计。

覆盖率命令:
- `pytest --cov=kernel_gen.passes.lowering.kernel_split --cov-report=term-missing -q test/pass/test_lowering_kernel_split.py`

关联文件:
- 功能实现: kernel_gen/passes/lowering/kernel_split.py
- Spec 文档: spec/pass/lowering/kernel_split.md
- 测试文件: test/pass/test_lowering_kernel_split.py
"""

from __future__ import annotations

import sys
from pathlib import Path

from xdsl.dialects import func
from xdsl.dialects.builtin import ArrayAttr, FunctionType, ModuleOp, StringAttr, i32
from xdsl.ir import Block, Operation, Region

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from kernel_gen.dialect.dma import DmaViewOp
from kernel_gen.dialect.kernel import KernelAddOp
from kernel_gen.dialect.nn import NnMemorySpaceAttr, NnMemoryType
from kernel_gen.dialect.symbol import SymbolForOp
from kernel_gen.passes.lowering.kernel_split import KernelSplitError, KernelSplitPass
from kernel_gen.passes.lowering.tile import TilePassError


def _make_memory_type(shape_names: list[str]) -> NnMemoryType:
    """构造测试用 `nn.memory` 类型。

    创建者: 小李飞刀
    最后一次更改: 小李飞刀

    功能说明:
    - 用字符串维度生成 shape/stride，保持符号维度表达。

    使用示例:
    - mem_type = _make_memory_type(["M", "N"])

    关联文件:
    - spec: spec/pass/lowering/kernel_split.md
    - test: test/pass/test_lowering_kernel_split.py
    - 功能实现: kernel_gen/passes/lowering/kernel_split.py
    """

    shape = ArrayAttr([StringAttr(name) for name in shape_names])
    stride = ArrayAttr([StringAttr(f"S{axis}") for axis in range(len(shape_names))])
    space = NnMemorySpaceAttr.from_name("global")
    return NnMemoryType(shape, stride, i32, space)


def _build_elementwise_module() -> ModuleOp:
    """构造 elementwise 示例 module。

    创建者: 小李飞刀
    最后一次更改: 小李飞刀

    功能说明:
    - 生成 `kernel.add` 的单函数 IR。

    使用示例:
    - module = _build_elementwise_module()

    关联文件:
    - spec: spec/pass/lowering/kernel_split.md
    - test: test/pass/test_lowering_kernel_split.py
    - 功能实现: kernel_gen/passes/lowering/kernel_split.py
    """

    mem_type = _make_memory_type(["M", "N"])
    block = Block(arg_types=[mem_type, mem_type, mem_type])
    space = NnMemorySpaceAttr.from_name("global")
    block.add_ops([KernelAddOp(block.args[0], block.args[1], block.args[2], space), func.ReturnOp()])
    func_op = func.FuncOp(
        "kernel_split_elementwise",
        FunctionType.from_lists([mem_type, mem_type, mem_type], []),
        Region(block),
    )
    return ModuleOp([func_op])


def _collect_ops(root: Operation) -> list[Operation]:
    """递归收集 operation 列表。

    创建者: 小李飞刀
    最后一次更改: 小李飞刀

    功能说明:
    - 遍历 region/block 结构，返回扁平化 op 列表。

    使用示例:
    - ops = _collect_ops(module)

    关联文件:
    - spec: spec/pass/lowering/kernel_split.md
    - test: test/pass/test_lowering_kernel_split.py
    - 功能实现: kernel_gen/passes/lowering/kernel_split.py
    """

    collected: list[Operation] = []

    def _visit(op: Operation) -> None:
        collected.append(op)
        for region in op.regions:
            for block in region.blocks:
                for inner in block.ops:
                    _visit(inner)

    _visit(root)
    return collected


# TC-KS-001
# 创建者: 小李飞刀
# 最后一次更改: 小李飞刀
# 最近一次运行测试时间: 2026-04-07 13:15:00 +0800
# 最近一次运行成功时间: 2026-04-07 13:15:00 +0800
# 功能说明: 验证 KernelSplitPass 与 TilePass 行为一致、name 固定且错误类型可用。
# 测试目的: 覆盖兼容入口的 name/错误类型与 elementwise 结构一致性。
# 使用示例: pytest -q test/pass/test_lowering_kernel_split.py -k test_kernel_split_pass_aliases_tile_pass
# 对应功能实现文件路径: kernel_gen/passes/lowering/kernel_split.py
# 对应 spec 文件路径: spec/pass/lowering/kernel_split.md
# 对应测试文件路径: test/pass/test_lowering_kernel_split.py
def test_kernel_split_pass_aliases_tile_pass() -> None:
    assert KernelSplitPass.name == "tile"
    assert issubclass(KernelSplitError, TilePassError)

    module = _build_elementwise_module()
    KernelSplitPass().run(module)
    ops = _collect_ops(module)
    assert any(isinstance(op, SymbolForOp) for op in ops)
    assert any(isinstance(op, DmaViewOp) for op in ops)
