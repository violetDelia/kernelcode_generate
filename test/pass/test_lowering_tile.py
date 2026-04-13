"""tile pass tests.

创建者: 小李飞刀
最后一次更改: 朽木露琪亚

功能说明:
- 覆盖 TilePass elementwise/matmul 成功路径与关键错误短语。
- 校验 loop/view 结构与输入合同拒绝路径。

使用示例:
- pytest -q test/pass/test_lowering_tile.py

当前覆盖率信息:
- `kernel_gen.passes.lowering.tile`：待统计。

覆盖率命令:
- `pytest --cov=kernel_gen.passes.lowering.tile --cov-report=term-missing -q test/pass/test_lowering_tile.py`

关联文件:
- 功能实现: kernel_gen/passes/lowering/tile.py
- Spec 文档: spec/pass/lowering/tile.md
- 测试文件: test/pass/test_lowering_tile.py
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest
from xdsl.dialects import func
from xdsl.dialects.builtin import ArrayAttr, DictionaryAttr, FunctionType, IntAttr, ModuleOp, StringAttr, i32
from xdsl.ir import Attribute, Block, Operation, Region, SSAValue
from xdsl.irdl import IRDLOperation, attr_def, irdl_op_definition, operand_def
from xdsl.utils.exceptions import VerifyException

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from kernel_gen.dialect.dma import DmaAllocOp, DmaBroadcastOp, DmaViewOp
from kernel_gen.dialect.kernel import KernelAddOp, KernelBinaryElewiseOp
from kernel_gen.dialect.nn import NnAddOp, NnMemorySpaceAttr, NnMemoryType
from kernel_gen.dialect.symbol import SymbolForOp, SymbolGetDimOp
from kernel_gen.passes.lowering.tile import TilePass, TilePassError


def _make_memory_type(shape_names: list[str]) -> NnMemoryType:
    """构造测试用 nn.memory 类型。

    创建者: 小李飞刀
    最后一次更改: 小李飞刀

    功能说明:
    - 使用字符串维度生成 shape/stride，便于制造重复维度或 rank 差异。

    使用示例:
    - mem_type = _make_memory_type(["M", "N"])

    关联文件:
    - spec: spec/pass/lowering/tile.md
    - test: test/pass/test_lowering_tile.py
    - 功能实现: kernel_gen/passes/lowering/tile.py
    """

    shape = ArrayAttr([StringAttr(name) for name in shape_names])
    stride = ArrayAttr([StringAttr(f"S{axis}") for axis in range(len(shape_names))])
    space = NnMemorySpaceAttr.from_name("global")
    return NnMemoryType(shape, stride, i32, space)


def _build_elementwise_module(shape_names: list[str]) -> ModuleOp:
    """构造 elementwise 模块。

    创建者: 小李飞刀
    最后一次更改: 小李飞刀

    功能说明:
    - 生成 `kernel.add` 的单函数 IR。

    使用示例:
    - module = _build_elementwise_module(["M", "N"])

    关联文件:
    - spec: spec/pass/lowering/tile.md
    - test: test/pass/test_lowering_tile.py
    - 功能实现: kernel_gen/passes/lowering/tile.py
    """

    mem_type = _make_memory_type(shape_names)
    block = Block(arg_types=[mem_type, mem_type, mem_type])
    space = NnMemorySpaceAttr.from_name("global")
    block.add_ops([KernelAddOp(block.args[0], block.args[1], block.args[2], space), func.ReturnOp()])
    func_op = func.FuncOp(
        "tile_elementwise",
        FunctionType.from_lists([mem_type, mem_type, mem_type], []),
        Region(block),
    )
    return ModuleOp([func_op])


def _build_broadcast_module(target_shape_names: list[str], source_shape_names: list[str]) -> ModuleOp:
    """构造 broadcast 模块。

    创建者: 朽木露琪亚
    最后一次更改: 朽木露琪亚

    功能说明:
    - 生成 `dma.broadcast` 的单函数 IR。
    - 用于覆盖低 rank source 的 tile-only 改写路径。

    使用示例:
    - module = _build_broadcast_module(["M", "N"], ["N"])

    关联文件:
    - spec: spec/pass/lowering/tile.md
    - test: test/pass/test_lowering_tile.py
    - 功能实现: kernel_gen/passes/lowering/tile.py
    """

    target_type = _make_memory_type(target_shape_names)
    source_type = _make_memory_type(source_shape_names)
    block = Block(arg_types=[target_type, source_type])
    block.add_ops([DmaBroadcastOp(block.args[0], block.args[1]), func.ReturnOp()])
    func_op = func.FuncOp(
        "tile_broadcast",
        FunctionType.from_lists([target_type, source_type], []),
        Region(block),
    )
    return ModuleOp([func_op])


def _build_fc_chain_module() -> ModuleOp:
    """构造最小 fc 组合链路模块。

    创建者: 朽木露琪亚
    最后一次更改: 朽木露琪亚

    功能说明:
    - 构造 `dma.broadcast + kernel.matmul + kernel.binary_elewise` 的组合链路。
    - 为 matmul 输出与 bias broadcast 结果显式分配 carry memory。

    使用示例:
    - module = _build_fc_chain_module()

    关联文件:
    - spec: spec/pass/lowering/tile.md
    - test: test/pass/test_lowering_tile.py
    - 功能实现: kernel_gen/passes/lowering/tile.py
    """

    out_type = _make_memory_type(["M", "N"])
    lhs_type = _make_memory_type(["M", "K"])
    rhs_type = _make_memory_type(["K", "N"])
    bias_type = _make_memory_type(["N"])
    block = Block(arg_types=[out_type, lhs_type, rhs_type, bias_type])
    space = NnMemorySpaceAttr.from_name("global")
    dim_m = SymbolGetDimOp(block.args[0], 0)
    dim_n = SymbolGetDimOp(block.args[0], 1)
    bias_b = DmaAllocOp([dim_m.result, dim_n.result], out_type)
    mat_out = DmaAllocOp([dim_m.result, dim_n.result], out_type)
    block.add_ops(
        [
            dim_m,
            dim_n,
            bias_b,
            mat_out,
            DmaBroadcastOp(bias_b.result, block.args[3]),
            _KernelMatmulOp(block.args[1], block.args[2], mat_out.result, space),
            KernelBinaryElewiseOp(mat_out.result, bias_b.result, block.args[0], kind="add", space=space),
            func.ReturnOp(),
        ]
    )
    func_op = func.FuncOp(
        "tile_fc_chain",
        FunctionType.from_lists([out_type, lhs_type, rhs_type, bias_type], []),
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
    - spec: spec/pass/lowering/tile.md
    - test: test/pass/test_lowering_tile.py
    - 功能实现: kernel_gen/passes/lowering/tile.py
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


@irdl_op_definition
class _KernelMatmulOp(IRDLOperation):
    """测试用 kernel.matmul op。

    创建者: 小李飞刀
    最后一次更改: 小李飞刀

    功能说明:
    - 为 matmul 分支提供最小 kernel.matmul 语义。

    使用示例:
    - _KernelMatmulOp(lhs, rhs, out, space)

    关联文件:
    - spec: spec/pass/lowering/tile.md
    - test: test/pass/test_lowering_tile.py
    - 功能实现: kernel_gen/passes/lowering/tile.py
    """

    name = "kernel.matmul"

    lhs = operand_def(NnMemoryType)
    rhs = operand_def(NnMemoryType)
    out = operand_def(NnMemoryType)
    space = attr_def(NnMemorySpaceAttr)

    def __init__(
        self,
        lhs: Operation | Attribute,
        rhs: Operation | Attribute,
        out: Operation | Attribute,
        space: NnMemorySpaceAttr,
    ) -> None:
        """初始化测试用 kernel.matmul。

        创建者: 小李飞刀
        最后一次更改: 小李飞刀

        功能说明:
        - 绑定 lhs/rhs/out 与 space 属性。

        使用示例:
        - _KernelMatmulOp(lhs, rhs, out, space)

        关联文件:
        - spec: spec/pass/lowering/tile.md
        - test: test/pass/test_lowering_tile.py
        - 功能实现: kernel_gen/passes/lowering/tile.py
        """

        super().__init__(operands=[lhs, rhs, out], attributes={"space": space})

    def verify_(self) -> None:
        """校验测试用 kernel.matmul。

        创建者: 小李飞刀
        最后一次更改: 小李飞刀

        功能说明:
        - 校验 rank=2 与 `[M,K] x [K,N] -> [M,N]` 形状一致性。

        使用示例:
        - _KernelMatmulOp(...).verify_()

        关联文件:
        - spec: spec/pass/lowering/tile.md
        - test: test/pass/test_lowering_tile.py
        - 功能实现: kernel_gen/passes/lowering/tile.py
        """

        lhs_type = self.lhs.type
        rhs_type = self.rhs.type
        out_type = self.out.type
        if not isinstance(lhs_type, NnMemoryType) or not isinstance(rhs_type, NnMemoryType) or not isinstance(
            out_type, NnMemoryType
        ):
            raise VerifyException("kernel.matmul operands must be nn.memory")
        if len(lhs_type.shape.data) != 2 or len(rhs_type.shape.data) != 2 or len(out_type.shape.data) != 2:
            raise VerifyException("kernel.matmul operands must be rank-2")
        if lhs_type.shape.data[1] != rhs_type.shape.data[0]:
            raise VerifyException("kernel.matmul contracting dimensions must match")
        if lhs_type.shape.data[0] != out_type.shape.data[0] or rhs_type.shape.data[1] != out_type.shape.data[1]:
            raise VerifyException("kernel.matmul output shape must match lhs/rhs")


@irdl_op_definition
class _KernelReduceSumOp(IRDLOperation):
    """测试用 kernel.reduce_sum op。

    创建者: 小李飞刀
    最后一次更改: 小李飞刀

    功能说明:
    - 用于触发 TilePass 对 reduce 的拒绝路径。

    使用示例:
    - _KernelReduceSumOp(source, out, space)

    关联文件:
    - spec: spec/pass/lowering/tile.md
    - test: test/pass/test_lowering_tile.py
    - 功能实现: kernel_gen/passes/lowering/tile.py
    """

    name = "kernel.reduce_sum"

    source = operand_def(NnMemoryType)
    out = operand_def(NnMemoryType)
    space = attr_def(NnMemorySpaceAttr)

    def __init__(
        self,
        source: Operation | Attribute,
        out: Operation | Attribute,
        space: NnMemorySpaceAttr,
    ) -> None:
        """初始化测试用 reduce op。

        创建者: 小李飞刀
        最后一次更改: 小李飞刀

        功能说明:
        - 绑定 source/out 与 space 属性。

        使用示例:
        - _KernelReduceSumOp(source, out, space)

        关联文件:
        - spec: spec/pass/lowering/tile.md
        - test: test/pass/test_lowering_tile.py
        - 功能实现: kernel_gen/passes/lowering/tile.py
        """

        super().__init__(operands=[source, out], attributes={"space": space})


# TC-TILE-001
# 创建者: 小李飞刀
# 最后一次更改: 小李飞刀
# 最近一次运行测试时间: 2026-04-07 13:50:00 +0800
# 最近一次运行成功时间: 2026-04-07 13:50:00 +0800
# 功能说明: 验证 elementwise 会生成多层 symbol.for 与 dma.view。
# 测试目的: 覆盖 elementwise 成功路径的 loop/view 结构。
# 使用示例: pytest -q test/pass/test_lowering_tile.py -k test_tile_elementwise_builds_nested_loops
# 对应功能实现文件路径: kernel_gen/passes/lowering/tile.py
# 对应 spec 文件路径: spec/pass/lowering/tile.md
# 对应测试文件路径: test/pass/test_lowering_tile.py
def test_tile_elementwise_builds_nested_loops() -> None:
    module = _build_elementwise_module(["M", "N"])
    TilePass().run(module)
    ops = _collect_ops(module)
    loop_ops = [op for op in ops if isinstance(op, SymbolForOp)]
    view_ops = [op for op in ops if isinstance(op, DmaViewOp)]
    assert len(loop_ops) == 2
    assert len(view_ops) == 3


# TC-TILE-002
# 创建者: 小李飞刀
# 最后一次更改: 小李飞刀
# 最近一次运行测试时间: 2026-04-07 13:50:00 +0800
# 最近一次运行成功时间: 2026-04-07 13:50:00 +0800
# 功能说明: 验证 matmul 会生成 M/N/K 三层 loop 与 view。
# 测试目的: 覆盖 matmul 成功路径的 loop/view 结构。
# 使用示例: pytest -q test/pass/test_lowering_tile.py -k test_tile_matmul_builds_mnk_loops
# 对应功能实现文件路径: kernel_gen/passes/lowering/tile.py
# 对应 spec 文件路径: spec/pass/lowering/tile.md
# 对应测试文件路径: test/pass/test_lowering_tile.py
def test_tile_matmul_builds_mnk_loops() -> None:
    lhs_type = _make_memory_type(["M", "K"])
    rhs_type = _make_memory_type(["K", "N"])
    out_type = _make_memory_type(["M", "N"])
    block = Block(arg_types=[lhs_type, rhs_type, out_type])
    space = NnMemorySpaceAttr.from_name("global")
    block.add_ops([_KernelMatmulOp(block.args[0], block.args[1], block.args[2], space), func.ReturnOp()])
    func_op = func.FuncOp(
        "tile_matmul",
        FunctionType.from_lists([lhs_type, rhs_type, out_type], []),
        Region(block),
    )
    module = ModuleOp([func_op])
    TilePass().run(module)
    ops = _collect_ops(module)
    loop_ops = [op for op in ops if isinstance(op, SymbolForOp)]
    view_ops = [op for op in ops if isinstance(op, DmaViewOp)]
    assert len(loop_ops) == 3
    assert len(view_ops) == 3


# TC-TILE-008
# 创建者: 金铲铲大作战
# 最后一次更改: 小李飞刀
# 最近一次运行测试时间: 2026-04-13 01:25:30 +0800
# 最近一次运行成功时间: 2026-04-13 01:25:30 +0800
# 功能说明: 验证 analysis-only=true 仅输出 tile.analysis，不生成 loop/view。
# 测试目的: 覆盖 analysis-only=true 的公开行为。
# 使用示例: pytest -q test/pass/test_lowering_tile.py -k test_tile_analysis_only_true
# 对应功能实现文件路径: kernel_gen/passes/lowering/tile.py
# 对应 spec 文件路径: spec/pass/lowering/tile.md
# 对应测试文件路径: test/pass/test_lowering_tile.py
def test_tile_analysis_only_true() -> None:
    module = _build_elementwise_module(["M", "N"])
    TilePass.from_options({"analysis-only": "true", "tile-elewise": "true", "tile-reduce": "false"}).run(module)
    ops = _collect_ops(module)
    loop_ops = [op for op in ops if isinstance(op, SymbolForOp)]
    view_ops = [op for op in ops if isinstance(op, DmaViewOp)]
    kernel_ops = [op for op in ops if isinstance(op, KernelAddOp)]
    analysis_ops = [op for op in kernel_ops if "tile.analysis" in op.attributes]
    internal_ops = [op for op in ops if op.name in {"tile.symbol_literal", "tile.step_value"}]
    expected_roles = ArrayAttr(
        [
            ArrayAttr([StringAttr("elewise"), StringAttr("elewise")]),
            ArrayAttr([StringAttr("elewise"), StringAttr("elewise")]),
            ArrayAttr([StringAttr("elewise"), StringAttr("elewise")]),
        ]
    )
    assert loop_ops == []
    assert view_ops == []
    assert kernel_ops
    assert len(analysis_ops) == 1
    assert analysis_ops[0].attributes["tile.analysis"] == expected_roles
    assert internal_ops == []


# TC-TILE-009
# 创建者: 金铲铲大作战
# 最后一次更改: 小李飞刀
# 最近一次运行测试时间: 2026-04-13 01:25:30 +0800
# 最近一次运行成功时间: 2026-04-13 01:25:30 +0800
# 功能说明: 验证 analysis-only=false 仍生成 loop/view 结构。
# 测试目的: 覆盖 analysis-only=false 的公开行为。
# 使用示例: pytest -q test/pass/test_lowering_tile.py -k test_tile_analysis_only_false
# 对应功能实现文件路径: kernel_gen/passes/lowering/tile.py
# 对应 spec 文件路径: spec/pass/lowering/tile.md
# 对应测试文件路径: test/pass/test_lowering_tile.py
def test_tile_analysis_only_false() -> None:
    module = _build_elementwise_module(["M", "N"])
    TilePass.from_options(
        {
            "analysis-only": "false",
            "tile-only": "true",
            "tile-elewise": "true",
            "tile-reduce": "false",
        }
    ).run(module)
    ops = _collect_ops(module)
    loop_ops = [op for op in ops if isinstance(op, SymbolForOp)]
    view_ops = [op for op in ops if isinstance(op, DmaViewOp)]
    analysis_ops = [op for op in ops if "tile.analysis" in op.attributes]
    assert len(loop_ops) == 2
    assert len(view_ops) == 3
    assert analysis_ops == []


# TC-TILE-010
# 创建者: 金铲铲大作战
# 最后一次更改: 小李飞刀
# 最近一次运行测试时间: 2026-04-13 00:52:58 +0800
# 最近一次运行成功时间: 2026-04-13 00:52:58 +0800
# 功能说明: 验证 analysis-only 非法值会报告稳定错误短语。
# 测试目的: 覆盖 options 非法值的拒绝路径。
# 使用示例: pytest -q test/pass/test_lowering_tile.py -k test_tile_analysis_only_invalid_value
# 对应功能实现文件路径: kernel_gen/passes/lowering/tile.py
# 对应 spec 文件路径: spec/pass/lowering/tile.md
# 对应测试文件路径: test/pass/test_lowering_tile.py
def test_tile_analysis_only_invalid_value() -> None:
    with pytest.raises(TilePassError, match="TilePassInvalidOption"):
        TilePass.from_options({"analysis-only": "maybe"})


# TC-TILE-011
# 创建者: 小李飞刀
# 最后一次更改: 小李飞刀
# 最近一次运行测试时间: 2026-04-13 00:52:58 +0800
# 最近一次运行成功时间: 2026-04-13 00:52:58 +0800
# 功能说明: 验证 analysis-only 与 tile-only 同时为 true 时会报错。
# 测试目的: 覆盖互斥选项的错误短语。
# 使用示例: pytest -q test/pass/test_lowering_tile.py -k test_tile_analysis_only_and_tile_only_conflict
# 对应功能实现文件路径: kernel_gen/passes/lowering/tile.py
# 对应 spec 文件路径: spec/pass/lowering/tile.md
# 对应测试文件路径: test/pass/test_lowering_tile.py
def test_tile_analysis_only_and_tile_only_conflict() -> None:
    with pytest.raises(TilePassError, match="TilePassInvalidOption"):
        TilePass.from_options(
            {
                "analysis-only": "true",
                "tile-only": "true",
                "tile-elewise": "true",
                "tile-reduce": "false",
            }
        )


# TC-TILE-012
# 创建者: 朽木露琪亚
# 最后一次更改: 朽木露琪亚
# 最近一次运行测试时间: 2026-04-13 22:20:00 +0800
# 最近一次运行成功时间: 2026-04-13 22:20:00 +0800
# 功能说明: 验证 low-rank broadcast source 会保持 source 自身 rank 的 dma.view。
# 测试目的: 覆盖 fc/broadcast 场景中 rank-1 bias 不再被错误改写成 rank-2 dma.view。
# 使用示例: pytest -q test/pass/test_lowering_tile.py -k test_tile_broadcast_keeps_lower_rank_source_view
# 对应功能实现文件路径: kernel_gen/passes/lowering/tile.py
# 对应 spec 文件路径: spec/pass/lowering/tile.md
# 对应测试文件路径: test/pass/test_lowering_tile.py
def test_tile_broadcast_keeps_lower_rank_source_view() -> None:
    module = _build_broadcast_module(["M", "N"], ["N"])
    TilePass.from_options(
        {
            "tile-only": "true",
            "tile-elewise": "true",
            "tile-reduce": "false",
        }
    ).run(module)
    module.verify()
    ops = _collect_ops(module)
    view_ops = [op for op in ops if isinstance(op, DmaViewOp)]
    broadcast_ops = [op for op in ops if isinstance(op, DmaBroadcastOp)]
    assert len(view_ops) == 2
    assert len(broadcast_ops) == 1
    target_view_ranks = sorted(len(op.result.type.shape.data) for op in view_ops)
    assert target_view_ranks == [1, 2]
    broadcast_op = broadcast_ops[0]
    target_type = SSAValue.get(broadcast_op.operands[0]).type
    source_type = SSAValue.get(broadcast_op.operands[1]).type
    assert isinstance(target_type, NnMemoryType)
    assert isinstance(source_type, NnMemoryType)
    assert len(target_type.shape.data) == 2
    assert len(source_type.shape.data) == 1


# TC-TILE-013
# 创建者: 朽木露琪亚
# 最后一次更改: 朽木露琪亚
# 最近一次运行测试时间: 2026-04-13 22:20:00 +0800
# 最近一次运行成功时间: 2026-04-13 22:20:00 +0800
# 功能说明: 验证 TilePass.run 不会吞掉 verifier 失败。
# 测试目的: 覆盖 TilePassRequiresLoweredKernelIR 的 verifier 传播路径。
# 使用示例: pytest -q test/pass/test_lowering_tile.py -k test_tile_run_raises_on_verifier_failure
# 对应功能实现文件路径: kernel_gen/passes/lowering/tile.py
# 对应 spec 文件路径: spec/pass/lowering/tile.md
# 对应测试文件路径: test/pass/test_lowering_tile.py
def test_tile_run_raises_on_verifier_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    module = _build_elementwise_module(["M", "N"])

    def _raise_verify(_self: ModuleOp) -> None:
        raise VerifyException("forced verifier failure")

    monkeypatch.setattr(ModuleOp, "verify", _raise_verify)
    with pytest.raises(TilePassError, match="TilePassRequiresLoweredKernelIR: forced verifier failure"):
        TilePass().run(module)


# TC-TILE-014
# 创建者: 朽木露琪亚
# 最后一次更改: 朽木露琪亚
# 最近一次运行测试时间: 2026-04-13 22:35:00 +0800
# 最近一次运行成功时间: 2026-04-13 22:35:00 +0800
# 功能说明: 验证 fc 组合链路会保留 carry alloc 并通过 verifier。
# 测试目的: 覆盖 broadcast/matmul/elementwise 组合场景下的 carry memory 与 rank-1 bias tile 路径。
# 使用示例: pytest -q test/pass/test_lowering_tile.py -k test_tile_fc_chain_preserves_carry_allocs_and_verifies
# 对应功能实现文件路径: kernel_gen/passes/lowering/tile.py
# 对应 spec 文件路径: spec/pass/lowering/tile.md
# 对应测试文件路径: test/pass/test_lowering_tile.py
def test_tile_fc_chain_preserves_carry_allocs_and_verifies() -> None:
    module = _build_fc_chain_module()
    TilePass.from_options(
        {
            "tile-only": "true",
            "tile-elewise": "true",
            "tile-reduce": "false",
        }
    ).run(module)
    module.verify()
    ops = _collect_ops(module)
    alloc_ops = [op for op in ops if isinstance(op, DmaAllocOp)]
    broadcast_ops = [op for op in ops if isinstance(op, DmaBroadcastOp)]
    assert len(alloc_ops) == 2
    assert len(broadcast_ops) == 1
    source_type = SSAValue.get(broadcast_ops[0].operands[1]).type
    assert isinstance(source_type, NnMemoryType)
    assert len(source_type.shape.data) == 1


# TC-TILE-003
# 创建者: 小李飞刀
# 最后一次更改: 小李飞刀
# 最近一次运行测试时间: 2026-04-07 13:50:00 +0800
# 最近一次运行成功时间: 2026-04-07 13:50:00 +0800
# 功能说明: 验证 reduce kernel op 被显式拒绝。
# 测试目的: 覆盖 reduce 不支持路径的错误短语。
# 使用示例: pytest -q test/pass/test_lowering_tile.py -k test_tile_rejects_reduce_kernel_ops
# 对应功能实现文件路径: kernel_gen/passes/lowering/tile.py
# 对应 spec 文件路径: spec/pass/lowering/tile.md
# 对应测试文件路径: test/pass/test_lowering_tile.py
def test_tile_rejects_reduce_kernel_ops() -> None:
    mem_type = _make_memory_type(["M", "N"])
    block = Block(arg_types=[mem_type, mem_type])
    space = NnMemorySpaceAttr.from_name("global")
    block.add_ops([_KernelReduceSumOp(block.args[0], block.args[1], space), func.ReturnOp()])
    func_op = func.FuncOp(
        "tile_reduce",
        FunctionType.from_lists([mem_type, mem_type], []),
        Region(block),
    )
    module = ModuleOp([func_op])
    with pytest.raises(TilePassError, match="TilePassUnsupportedOp"):
        TilePass().run(module)


# TC-TILE-004
# 创建者: 小李飞刀
# 最后一次更改: 小李飞刀
# 最近一次运行测试时间: 2026-04-07 13:50:00 +0800
# 最近一次运行成功时间: 2026-04-07 13:50:00 +0800
# 功能说明: 验证重复 tile 名称会被拒绝。
# 测试目的: 覆盖重复 tile 参数的错误短语。
# 使用示例: pytest -q test/pass/test_lowering_tile.py -k test_tile_rejects_duplicate_tile_names
# 对应功能实现文件路径: kernel_gen/passes/lowering/tile.py
# 对应 spec 文件路径: spec/pass/lowering/tile.md
# 对应测试文件路径: test/pass/test_lowering_tile.py
def test_tile_rejects_duplicate_tile_names() -> None:
    module = _build_elementwise_module(["M", "M"])
    func_op = next(iter(module.ops))
    assert isinstance(func_op, func.FuncOp)
    func_op.attributes["kernel_split"] = DictionaryAttr(
        {
            "axis": IntAttr(1),
            "tile": StringAttr("TILE_D0"),
        }
    )
    with pytest.raises(TilePassError, match="TilePassDuplicateTileParam"):
        TilePass().run(module)


# TC-TILE-005
# 创建者: 小李飞刀
# 最后一次更改: 小李飞刀
# 最近一次运行测试时间: 2026-04-07 13:50:00 +0800
# 最近一次运行成功时间: 2026-04-07 13:50:00 +0800
# 功能说明: 验证残留 nn.* op 会触发输入合同错误。
# 测试目的: 覆盖 TilePassRequiresLoweredKernelIR 的输入合同拒绝路径。
# 使用示例: pytest -q test/pass/test_lowering_tile.py -k test_tile_rejects_nn_input_ops
# 对应功能实现文件路径: kernel_gen/passes/lowering/tile.py
# 对应 spec 文件路径: spec/pass/lowering/tile.md
# 对应测试文件路径: test/pass/test_lowering_tile.py
def test_tile_rejects_nn_input_ops() -> None:
    mem_type = _make_memory_type(["M", "N"])
    block = Block(arg_types=[mem_type, mem_type])
    space = NnMemorySpaceAttr.from_name("global")
    block.add_ops([NnAddOp(block.args[0], block.args[1], mem_type, space), func.ReturnOp()])
    func_op = func.FuncOp(
        "tile_nn_input",
        FunctionType.from_lists([mem_type, mem_type], []),
        Region(block),
    )
    module = ModuleOp([func_op])
    with pytest.raises(TilePassError, match="TilePassRequiresLoweredKernelIR"):
        TilePass().run(module)


# TC-TILE-006
# 创建者: 小李飞刀
# 最后一次更改: 小李飞刀
# 最近一次运行测试时间: 2026-04-07 13:50:00 +0800
# 最近一次运行成功时间: 2026-04-07 13:50:00 +0800
# 功能说明: 验证未被消费的 carry memory 会被拒绝。
# 测试目的: 覆盖 TilePassDeadCarryMemory 的错误短语。
# 使用示例: pytest -q test/pass/test_lowering_tile.py -k test_tile_rejects_dead_carry_memory
# 对应功能实现文件路径: kernel_gen/passes/lowering/tile.py
# 对应 spec 文件路径: spec/pass/lowering/tile.md
# 对应测试文件路径: test/pass/test_lowering_tile.py
def test_tile_rejects_dead_carry_memory() -> None:
    mem_type = _make_memory_type(["M", "N"])
    block = Block(arg_types=[mem_type, mem_type])
    shape_ops = [SymbolGetDimOp(block.args[0], axis) for axis in range(2)]
    alloc = DmaAllocOp([op.result for op in shape_ops], mem_type)
    space = NnMemorySpaceAttr.from_name("global")
    block.add_ops([*shape_ops, alloc, KernelAddOp(block.args[0], block.args[1], alloc.result, space), func.ReturnOp()])
    func_op = func.FuncOp(
        "tile_dead_carry",
        FunctionType.from_lists([mem_type, mem_type], []),
        Region(block),
    )
    module = ModuleOp([func_op])
    with pytest.raises(TilePassError, match="TilePassDeadCarryMemory"):
        TilePass().run(module)


# TC-TILE-007
# 创建者: 小李飞刀
# 最后一次更改: 小李飞刀
# 最近一次运行测试时间: 2026-04-07 13:50:00 +0800
# 最近一次运行成功时间: 2026-04-07 13:50:00 +0800
# 功能说明: 验证 elementwise memory rank 不一致时拒绝。
# 测试目的: 覆盖 TilePassRankMismatch 的错误短语。
# 使用示例: pytest -q test/pass/test_lowering_tile.py -k test_tile_rejects_rank_mismatch
# 对应功能实现文件路径: kernel_gen/passes/lowering/tile.py
# 对应 spec 文件路径: spec/pass/lowering/tile.md
# 对应测试文件路径: test/pass/test_lowering_tile.py
def test_tile_rejects_rank_mismatch() -> None:
    lhs_type = _make_memory_type(["M", "N"])
    rhs_type = _make_memory_type(["M"])
    out_type = _make_memory_type(["M", "N"])
    block = Block(arg_types=[lhs_type, rhs_type, out_type])
    space = NnMemorySpaceAttr.from_name("global")
    block.add_ops([KernelAddOp(block.args[0], block.args[1], block.args[2], space), func.ReturnOp()])
    func_op = func.FuncOp(
        "tile_rank_mismatch",
        FunctionType.from_lists([lhs_type, rhs_type, out_type], []),
        Region(block),
    )
    module = ModuleOp([func_op])
    with pytest.raises(TilePassError, match="TilePassRankMismatch"):
        TilePass().run(module)
