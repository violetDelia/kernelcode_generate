"""hoist-dma-alias-ops pass tests.

功能说明:
- 覆盖 `hoist-dma-alias-ops` 的公开 pass class、registry 与 no-op 边界。
- 测试只通过公开 `HoistDmaAliasOpsPass.apply(...)` 观察行为，不直连实现文件私有 helper。

使用示例:
- pytest -q test/passes/test_hoist_dma_alias_ops.py

关联文件:
- spec: spec/pass/hoist_dma_alias_ops.md
- test: test/passes/test_hoist_dma_alias_ops.py
- 功能实现: kernel_gen/passes/hoist_dma_alias_ops.py
"""

from __future__ import annotations

import importlib
import sys
from pathlib import Path

from xdsl.context import Context
from xdsl.dialects import arith, func, scf
from xdsl.dialects.builtin import ArrayAttr, FunctionType, IntegerAttr, ModuleOp, i1, i32
from xdsl.ir import Attribute, Block, Operation, Region, SSAValue

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from kernel_gen.dialect.dma import DmaAllocOp, DmaFillOp, DmaReshapeOp
from kernel_gen.dialect.nn import NnMemorySpaceAttr, NnMemoryType
from kernel_gen.dialect.symbol import SymbolConstOp, SymbolExprAttr, SymbolForOp, SymbolIterType, SymbolValueType

pass_module = importlib.import_module("kernel_gen.passes.hoist_dma_alias_ops")
registry_module = importlib.import_module("kernel_gen.passes.registry")

HoistDmaAliasOpsPass = pass_module.HoistDmaAliasOpsPass
build_registered_pass = registry_module.build_registered_pass
load_builtin_passes = registry_module.load_builtin_passes


def _memory_type(shape: tuple[int | str, ...], *, element_type: Attribute = i32) -> NnMemoryType:
    """构造测试用 contiguous `nn.memory` 类型。

    功能说明:
    - 使用公开 `NnMemoryType` 与 `SymbolExprAttr` 构造静态或符号 shape。

    使用示例:
    - mem_type = _memory_type((4, 4))
    """

    strides: list[int | str] = []
    running: int | str = 1
    for dim in reversed(shape):
        strides.append(running)
        if isinstance(dim, int):
            running = running * dim if isinstance(running, int) else f"{dim}*{running}"
        elif running == 1:
            running = dim
        else:
            running = f"{dim}*{running}"
    strides.reverse()
    return NnMemoryType(
        ArrayAttr([SymbolExprAttr.from_expr(str(dim)) for dim in shape]),
        ArrayAttr([SymbolExprAttr.from_expr(str(stride)) for stride in strides]),
        element_type,
        NnMemorySpaceAttr.from_name("tsm"),
    )


def _symbol_const(value: int) -> SymbolConstOp:
    """构造测试用 symbol 常量。

    功能说明:
    - 用于 reshape shape operand 与 symbol.for 边界。

    使用示例:
    - four = _symbol_const(4)
    """

    return SymbolConstOp(value)


def _scalar_i32(value: int = 0) -> arith.ConstantOp:
    """构造测试用 i32 标量常量。

    功能说明:
    - 作为 `dma.fill` 的公开数值 operand。

    使用示例:
    - zero = _scalar_i32()
    """

    return arith.ConstantOp(IntegerAttr(value, i32))


def _module_with_block(name: str, block: Block) -> ModuleOp:
    """把 block 封装为单函数 module。

    功能说明:
    - 保持测试通过公开 `func.FuncOp` / `ModuleOp` 构造 IR。

    使用示例:
    - module = _module_with_block("case", block)
    """

    block.add_op(func.ReturnOp())
    func_op = func.FuncOp(
        name,
        FunctionType.from_lists([arg.type for arg in block.args], []),
        Region(block),
    )
    return ModuleOp([func_op])


def _function_body(module: ModuleOp) -> Block:
    """返回测试 module 的第一个函数 body。

    功能说明:
    - 用于按公开 IR 顺序检查 pass 改写结果。

    使用示例:
    - body = _function_body(module)
    """

    func_op = next(op for op in module.ops if isinstance(op, func.FuncOp))
    return func_op.body.block


def _body_ops(module: ModuleOp) -> list[Operation]:
    """返回测试函数体内 operation 列表。

    功能说明:
    - 将 xDSL block op 迭代器规整为 list，便于 order 断言。

    使用示例:
    - ops = _body_ops(module)
    """

    return list(_function_body(module).ops)


def _single_op(module: ModuleOp, op_type: type[Operation]) -> Operation:
    """返回 module 中唯一匹配类型的 operation。

    功能说明:
    - 用于读取改写后的 `dma.fill` 或 `dma.reshape`。

    使用示例:
    - fill = _single_op(module, DmaFillOp)
    """

    matches = [op for op in module.walk() if isinstance(op, op_type)]
    assert len(matches) == 1
    return matches[0]


def _apply_pass(module: ModuleOp, *, fold: bool = True) -> None:
    """通过公开 pass class 执行 pass。

    功能说明:
    - 测试 direct Python API，不使用实现文件私有 helper。

    使用示例:
    - _apply_pass(module)
    """

    HoistDmaAliasOpsPass(fold=fold).apply(Context(), module)


def _build_static_through_fill_module() -> ModuleOp:
    """构造静态 reshape 穿过 fill 正例。

    功能说明:
    - `dma.fill` 与 `dma.reshape` 紧邻且同源，shape 常量支配 fill。

    使用示例:
    - module = _build_static_through_fill_module()
    """

    flat_type = _memory_type((16,))
    tile_type = _memory_type((4, 4))
    block = Block()
    four = _symbol_const(4)
    sixteen = _symbol_const(16)
    zero = _scalar_i32()
    alloc = DmaAllocOp([sixteen.result], flat_type)
    fill = DmaFillOp(alloc.result, zero.result)
    reshape = DmaReshapeOp(alloc.result, [four.result, four.result], tile_type)
    block.add_ops([four, sixteen, zero, alloc, fill, reshape])
    return _module_with_block("static_through_fill", block)


def _build_dynamic_through_fill_module() -> ModuleOp:
    """构造动态 shape reshape 穿过 fill 正例。

    功能说明:
    - reshape shape 来自函数 block args，天然支配 fill。

    使用示例:
    - module = _build_dynamic_through_fill_module()
    """

    flat_type = _memory_type(("M*N",))
    tile_type = _memory_type(("M", "N"))
    block = Block(arg_types=[flat_type, SymbolValueType.from_expr("M"), SymbolValueType.from_expr("N")])
    zero = _scalar_i32()
    fill = DmaFillOp(block.args[0], zero.result)
    reshape = DmaReshapeOp(block.args[0], [block.args[1], block.args[2]], tile_type)
    block.add_ops([zero, fill, reshape])
    return _module_with_block("dynamic_through_fill", block)


def _build_non_adjacent_module() -> ModuleOp:
    """构造 fill 与 reshape 非紧邻反例。

    功能说明:
    - 中间插入无关 symbol.const，pass 必须保持 no-op。

    使用示例:
    - module = _build_non_adjacent_module()
    """

    flat_type = _memory_type((16,))
    tile_type = _memory_type((4, 4))
    block = Block(arg_types=[flat_type])
    four = _symbol_const(4)
    zero = _scalar_i32()
    fill = DmaFillOp(block.args[0], zero.result)
    separator = _symbol_const(1)
    reshape = DmaReshapeOp(block.args[0], [four.result, four.result], tile_type)
    block.add_ops([four, zero, fill, separator, reshape])
    return _module_with_block("non_adjacent", block)


def _build_source_mismatch_module() -> ModuleOp:
    """构造 reshape source 不是 fill target 的反例。

    功能说明:
    - `dma.fill(%a)` 后接 `dma.reshape(%b)`，pass 必须保持 no-op。

    使用示例:
    - module = _build_source_mismatch_module()
    """

    flat_type = _memory_type((16,))
    tile_type = _memory_type((4, 4))
    block = Block(arg_types=[flat_type, flat_type])
    four = _symbol_const(4)
    zero = _scalar_i32()
    fill = DmaFillOp(block.args[0], zero.result)
    reshape = DmaReshapeOp(block.args[1], [four.result, four.result], tile_type)
    block.add_ops([four, zero, fill, reshape])
    return _module_with_block("source_mismatch", block)


def _build_scf_region_cross_block_module() -> ModuleOp:
    """构造 fill 与 reshape 跨 scf.if region 的 no-op 反例。

    功能说明:
    - fill 位于函数 body，reshape 位于 scf.if true block，pass 不跨 block 匹配。

    使用示例:
    - module = _build_scf_region_cross_block_module()
    """

    flat_type = _memory_type((16,))
    tile_type = _memory_type((4, 4))
    block = Block(arg_types=[flat_type])
    four = _symbol_const(4)
    zero = _scalar_i32()
    condition = arith.ConstantOp(IntegerAttr(1, i1))
    fill = DmaFillOp(block.args[0], zero.result)
    true_block = Block()
    reshape = DmaReshapeOp(block.args[0], [four.result, four.result], tile_type)
    true_block.add_ops([reshape, scf.YieldOp()])
    if_op = scf.IfOp(condition.result, [], Region(true_block), None)
    block.add_ops([four, zero, condition, fill, if_op])
    return _module_with_block("scf_region_cross_block", block)


def _build_symbol_for_cross_block_module() -> ModuleOp:
    """构造 fill 与 reshape 跨 symbol.for body 的 no-op 反例。

    功能说明:
    - fill 位于 owner block，reshape 位于 symbol.for body，pass 不跨 region 匹配。

    使用示例:
    - module = _build_symbol_for_cross_block_module()
    """

    flat_type = _memory_type((16,))
    tile_type = _memory_type((4, 4))
    block = Block(arg_types=[flat_type])
    zero = _symbol_const(0)
    one = _symbol_const(1)
    four = _symbol_const(4)
    scalar = _scalar_i32()
    fill = DmaFillOp(block.args[0], scalar.result)
    loop_block = Block(arg_types=[SymbolIterType.from_bounds("0", "1", "1")])
    reshape = DmaReshapeOp(block.args[0], [four.result, four.result], tile_type)
    loop_block.add_op(reshape)
    loop = SymbolForOp(zero.result, one.result, one.result, loop_block)
    block.add_ops([zero, one, four, scalar, fill, loop])
    return _module_with_block("symbol_for_cross_block", block)


def _build_shape_after_fill_module() -> ModuleOp:
    """构造 shape operand 不支配 fill 的 no-op 反例。

    功能说明:
    - IR 中 reshape 紧邻 fill，但 shape 常量定义在 reshape 之后。
    - pass 必须先做支配检查，避免产生部分改写。

    使用示例:
    - module = _build_shape_after_fill_module()
    """

    flat_type = _memory_type((16,))
    tile_type = _memory_type((4, 4))
    block = Block(arg_types=[flat_type])
    zero = _scalar_i32()
    late_four = _symbol_const(4)
    fill = DmaFillOp(block.args[0], zero.result)
    reshape = DmaReshapeOp(block.args[0], [late_four.result, late_four.result], tile_type)
    block.add_ops([zero, fill, reshape, late_four])
    return _module_with_block("shape_after_fill", block)


def _build_verifier_rejects_candidate_module() -> ModuleOp:
    """构造候选通过但 verifier 拒绝的回滚反例。

    功能说明:
    - `dma.fill` 与 `dma.reshape` 紧邻、同源，shape operand 也支配 fill。
    - reshape 结果类型与 shape operand 不一致，移动后 `module.verify()` 必须失败并回滚。

    使用示例:
    - module = _build_verifier_rejects_candidate_module()
    """

    flat_type = _memory_type((16,))
    invalid_tile_type = _memory_type((2, 8))
    block = Block(arg_types=[flat_type])
    four = _symbol_const(4)
    zero = _scalar_i32()
    fill = DmaFillOp(block.args[0], zero.result)
    reshape = DmaReshapeOp(block.args[0], [four.result, four.result], invalid_tile_type)
    block.add_ops([four, zero, fill, reshape])
    return _module_with_block("verifier_rejects_candidate", block)


def _build_alloc_to_reshape_module() -> ModuleOp:
    """构造 alloc 后接 reshape 的非目标反例。

    功能说明:
    - pass 不做 `dma.alloc -> dma.reshape` fold。

    使用示例:
    - module = _build_alloc_to_reshape_module()
    """

    flat_type = _memory_type((16,))
    tile_type = _memory_type((4, 4))
    block = Block()
    four = _symbol_const(4)
    sixteen = _symbol_const(16)
    alloc = DmaAllocOp([sixteen.result], flat_type)
    reshape = DmaReshapeOp(alloc.result, [four.result, four.result], tile_type)
    block.add_ops([four, sixteen, alloc, reshape])
    return _module_with_block("alloc_to_reshape", block)


def _build_reshape_to_reshape_module() -> ModuleOp:
    """构造 reshape 后接 reshape 的非目标反例。

    功能说明:
    - pass 不做 `dma.reshape -> dma.reshape` chain collapse。

    使用示例:
    - module = _build_reshape_to_reshape_module()
    """

    flat_type = _memory_type((16,))
    tile_type = _memory_type((4, 4))
    block = Block(arg_types=[flat_type])
    four = _symbol_const(4)
    sixteen = _symbol_const(16)
    first = DmaReshapeOp(block.args[0], [four.result, four.result], tile_type)
    second = DmaReshapeOp(first.result, [sixteen.result], flat_type)
    block.add_ops([four, sixteen, first, second])
    return _module_with_block("reshape_to_reshape", block)


def _assert_reshape_before_fill(module: ModuleOp) -> None:
    """断言 reshape 位于 fill 前且 fill target 已改为 alias result。

    功能说明:
    - 锁定本 pass 的最小正向公开改写行为。

    使用示例:
    - _assert_reshape_before_fill(module)
    """

    body_ops = _body_ops(module)
    fill = _single_op(module, DmaFillOp)
    reshape = _single_op(module, DmaReshapeOp)
    assert body_ops.index(reshape) < body_ops.index(fill)
    assert isinstance(fill, DmaFillOp)
    assert isinstance(reshape, DmaReshapeOp)
    assert fill.target is reshape.result


# TC-HOIST-DMA-ALIAS-001
# 功能说明: 验证静态 `fill(flat); reshape(flat)` 改写为 `reshape(flat); fill(tile)`。
# 使用示例: pytest -q test/passes/test_hoist_dma_alias_ops.py -k static_reshape
# 对应功能实现文件路径: kernel_gen/passes/hoist_dma_alias_ops.py
# 对应 spec 文件路径: spec/pass/hoist_dma_alias_ops.md
# 对应测试文件路径: test/passes/test_hoist_dma_alias_ops.py
def test_hoist_dma_alias_ops_static_reshape_through_fill() -> None:
    module = _build_static_through_fill_module()

    _apply_pass(module)

    _assert_reshape_before_fill(module)
    module.verify()


# TC-HOIST-DMA-ALIAS-002
# 功能说明: 验证动态 shape operand 已支配 fill 时仍可上移。
# 使用示例: pytest -q test/passes/test_hoist_dma_alias_ops.py -k dynamic_reshape
# 对应功能实现文件路径: kernel_gen/passes/hoist_dma_alias_ops.py
# 对应 spec 文件路径: spec/pass/hoist_dma_alias_ops.md
# 对应测试文件路径: test/passes/test_hoist_dma_alias_ops.py
def test_hoist_dma_alias_ops_dynamic_reshape_through_fill() -> None:
    module = _build_dynamic_through_fill_module()

    _apply_pass(module)

    _assert_reshape_before_fill(module)
    module.verify()


# TC-HOIST-DMA-ALIAS-003
# 功能说明: 验证非紧邻 fill/reshape 保持 no-op。
# 使用示例: pytest -q test/passes/test_hoist_dma_alias_ops.py -k non_adjacent
# 对应功能实现文件路径: kernel_gen/passes/hoist_dma_alias_ops.py
# 对应 spec 文件路径: spec/pass/hoist_dma_alias_ops.md
# 对应测试文件路径: test/passes/test_hoist_dma_alias_ops.py
def test_hoist_dma_alias_ops_keeps_non_adjacent_shape() -> None:
    module = _build_non_adjacent_module()
    before = str(module)

    _apply_pass(module)

    assert str(module) == before


# TC-HOIST-DMA-ALIAS-004
# 功能说明: 验证 reshape source 不是 fill target 时保持 no-op。
# 使用示例: pytest -q test/passes/test_hoist_dma_alias_ops.py -k source_mismatch
# 对应功能实现文件路径: kernel_gen/passes/hoist_dma_alias_ops.py
# 对应 spec 文件路径: spec/pass/hoist_dma_alias_ops.md
# 对应测试文件路径: test/passes/test_hoist_dma_alias_ops.py
def test_hoist_dma_alias_ops_keeps_source_mismatch_shape() -> None:
    module = _build_source_mismatch_module()
    before = str(module)

    _apply_pass(module)

    assert str(module) == before


# TC-HOIST-DMA-ALIAS-005
# 功能说明: 验证 pass 不跨 scf.if region 移动 alias op。
# 使用示例: pytest -q test/passes/test_hoist_dma_alias_ops.py -k scf_region
# 对应功能实现文件路径: kernel_gen/passes/hoist_dma_alias_ops.py
# 对应 spec 文件路径: spec/pass/hoist_dma_alias_ops.md
# 对应测试文件路径: test/passes/test_hoist_dma_alias_ops.py
def test_hoist_dma_alias_ops_keeps_scf_region_cross_block_shape() -> None:
    module = _build_scf_region_cross_block_module()
    before = str(module)

    _apply_pass(module)

    assert str(module) == before


# TC-HOIST-DMA-ALIAS-006
# 功能说明: 验证 pass 不跨 symbol.for region 移动 alias op。
# 使用示例: pytest -q test/passes/test_hoist_dma_alias_ops.py -k symbol_for_cross_block
# 对应功能实现文件路径: kernel_gen/passes/hoist_dma_alias_ops.py
# 对应 spec 文件路径: spec/pass/hoist_dma_alias_ops.md
# 对应测试文件路径: test/passes/test_hoist_dma_alias_ops.py
def test_hoist_dma_alias_ops_keeps_symbol_for_cross_block_shape() -> None:
    module = _build_symbol_for_cross_block_module()
    before = str(module)

    _apply_pass(module)

    assert str(module) == before


# TC-HOIST-DMA-ALIAS-007
# 功能说明: 验证 shape 不支配 fill 时保持 no-op 且不产生部分改写。
# 使用示例: pytest -q test/passes/test_hoist_dma_alias_ops.py -k shape_after_fill
# 对应功能实现文件路径: kernel_gen/passes/hoist_dma_alias_ops.py
# 对应 spec 文件路径: spec/pass/hoist_dma_alias_ops.md
# 对应测试文件路径: test/passes/test_hoist_dma_alias_ops.py
def test_hoist_dma_alias_ops_keeps_shape_after_fill_without_partial_rewrite() -> None:
    module = _build_shape_after_fill_module()
    before = str(module)

    _apply_pass(module)

    assert str(module) == before


# TC-HOIST-DMA-ALIAS-008
# 功能说明: 验证 verifier 拒绝候选改写时回滚且不产生部分改写。
# 使用示例: pytest -q test/passes/test_hoist_dma_alias_ops.py -k verifier_rejects_candidate
# 对应功能实现文件路径: kernel_gen/passes/hoist_dma_alias_ops.py
# 对应 spec 文件路径: spec/pass/hoist_dma_alias_ops.md
# 对应测试文件路径: test/passes/test_hoist_dma_alias_ops.py
def test_hoist_dma_alias_ops_rolls_back_when_verifier_rejects_candidate() -> None:
    module = _build_verifier_rejects_candidate_module()
    before = str(module)

    _apply_pass(module)

    assert str(module) == before


# TC-HOIST-DMA-ALIAS-009
# 功能说明: 验证 `dma.alloc -> dma.reshape` 不 fold。
# 使用示例: pytest -q test/passes/test_hoist_dma_alias_ops.py -k alloc_to_reshape
# 对应功能实现文件路径: kernel_gen/passes/hoist_dma_alias_ops.py
# 对应 spec 文件路径: spec/pass/hoist_dma_alias_ops.md
# 对应测试文件路径: test/passes/test_hoist_dma_alias_ops.py
def test_hoist_dma_alias_ops_does_not_fold_alloc_to_reshape() -> None:
    module = _build_alloc_to_reshape_module()
    before = str(module)

    _apply_pass(module)

    assert str(module) == before


# TC-HOIST-DMA-ALIAS-010
# 功能说明: 验证 `dma.reshape -> dma.reshape` 不 combine。
# 使用示例: pytest -q test/passes/test_hoist_dma_alias_ops.py -k reshape_to_reshape
# 对应功能实现文件路径: kernel_gen/passes/hoist_dma_alias_ops.py
# 对应 spec 文件路径: spec/pass/hoist_dma_alias_ops.md
# 对应测试文件路径: test/passes/test_hoist_dma_alias_ops.py
def test_hoist_dma_alias_ops_does_not_combine_reshape_chain() -> None:
    module = _build_reshape_to_reshape_module()
    before = str(module)

    _apply_pass(module)

    assert str(module) == before


# TC-HOIST-DMA-ALIAS-011
# 功能说明: 验证 registry 能构造 hoist-dma-alias-ops，并支持通用 fold=false。
# 使用示例: pytest -q test/passes/test_hoist_dma_alias_ops.py -k registry_builds
# 对应功能实现文件路径: kernel_gen/passes/registry.py
# 对应 spec 文件路径: spec/pass/registry.md
# 对应测试文件路径: test/passes/test_hoist_dma_alias_ops.py
def test_hoist_dma_alias_ops_registry_builds_public_pass() -> None:
    load_builtin_passes()

    default_pass = build_registered_pass("hoist-dma-alias-ops")
    no_fold_pass = build_registered_pass("hoist-dma-alias-ops", {"fold": "false"})

    assert isinstance(default_pass, HoistDmaAliasOpsPass)
    assert default_pass.fold is True
    assert isinstance(no_fold_pass, HoistDmaAliasOpsPass)
    assert no_fold_pass.fold is False
