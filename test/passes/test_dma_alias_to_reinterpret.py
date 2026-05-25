"""dma-alias-to-reinterpret pass tests.

功能说明:
- 覆盖 `DmaAliasToReinterpretPass` 的公开 pass class、registry、rewrite 与 no-op 边界。
- 测试只通过公开 pass / registry API 观察 IR，不直连实现文件私有 helper。

使用示例:
- pytest -q test/passes/test_dma_alias_to_reinterpret.py

关联文件:
- spec: spec/pass/dma_alias_to_reinterpret.md
- 功能实现: kernel_gen/passes/hoist/dma_alias_to_reinterpret.py
- 测试文件: test/passes/test_dma_alias_to_reinterpret.py
"""

from __future__ import annotations

import importlib
import sys
from pathlib import Path

import pytest
from xdsl.context import Context
from xdsl.dialects import arith, func
from xdsl.dialects.builtin import ArrayAttr, FunctionType, IntegerAttr, ModuleOp, f32, i32, i8
from xdsl.ir import Attribute, Block, Operation, Region

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from kernel_gen.dialect.dma import DmaFillOp, DmaReinterpretOp, DmaReshapeOp, DmaSubviewOp, DmaViewOp
from kernel_gen.dialect.nn import NnMemorySpaceAttr, NnMemoryType
from kernel_gen.dialect.symbol import SymbolConstOp, SymbolExprAttr, SymbolValueType

pass_module = importlib.import_module("kernel_gen.passes.hoist.dma_alias_to_reinterpret")
registry_module = importlib.import_module("kernel_gen.passes.registry")

DmaAliasToReinterpretPass = pass_module.DmaAliasToReinterpretPass
build_registered_pass = registry_module.build_registered_pass
load_builtin_passes = registry_module.load_builtin_passes


def _memory_type(
    shape: tuple[int | str, ...],
    stride: tuple[int | str, ...],
    *,
    element_type: Attribute = i32,
    space: str = "shared",
) -> NnMemoryType:
    """构造测试用 `nn.memory` 类型。

    功能说明:
    - 使用公开 `NnMemoryType` 与 `SymbolExprAttr` 表达 layout。

    使用示例:
    - mem_type = _memory_type((2, 4), (4, 1))
    """

    return NnMemoryType(
        ArrayAttr([SymbolExprAttr.from_expr(str(dim)) for dim in shape]),
        ArrayAttr([SymbolExprAttr.from_expr(str(dim)) for dim in stride]),
        element_type,
        NnMemorySpaceAttr.from_name(space),
    )


def _symbol_const(value: int) -> SymbolConstOp:
    """构造 `symbol.const`。

    功能说明:
    - 用于 alias op 的 offset/shape/stride operand。

    使用示例:
    - zero = _symbol_const(0)
    """

    return SymbolConstOp(value)


def _scalar_i32(value: int) -> arith.ConstantOp:
    """构造 i32 标量常量。

    功能说明:
    - 作为 `dma.fill` 的 value operand，确保 alias result 有可观察 use。

    使用示例:
    - value = _scalar_i32(7)
    """

    return arith.ConstantOp(IntegerAttr(value, i32))


def _module(name: str, block: Block, ops: list[Operation]) -> ModuleOp:
    """把 op 列表封装为单函数 module。

    功能说明:
    - 使用公开 `func.FuncOp` / `ModuleOp` 构造 pass 输入。

    使用示例:
    - module = _module("case", block, ops)
    """

    block.add_ops([*ops, func.ReturnOp()])
    func_op = func.FuncOp(name, FunctionType.from_lists([arg.type for arg in block.args], []), Region(block))
    return ModuleOp([func_op])


def _apply(module: ModuleOp) -> None:
    """通过公开 pass class 执行 rewrite。

    功能说明:
    - 不绕过 pass API，不直连 pattern/helper。

    使用示例:
    - _apply(module)
    """

    DmaAliasToReinterpretPass(fold=False).apply(Context(), module)


def _ops(module: ModuleOp, op_type: type[Operation]) -> list[Operation]:
    """收集 module 中指定类型 op。

    功能说明:
    - 通过公开 `Operation.walk()` 黑盒观察 rewrite 结果。

    使用示例:
    - reinterprets = _ops(module, DmaReinterpretOp)
    """

    return [op for op in module.walk() if isinstance(op, op_type)]


def _func_block(module: ModuleOp) -> Block:
    """返回 module 的单个函数 body block。

    功能说明:
    - pass 会在 clone 验证后替换 module body，测试需读取替换后的 block arg。

    使用示例:
    - block = _func_block(module)
    """

    funcs = [op for op in module.ops if isinstance(op, func.FuncOp)]
    assert len(funcs) == 1
    return funcs[0].body.block


def _single_reinterpret(module: ModuleOp) -> DmaReinterpretOp:
    """返回唯一 `DmaReinterpretOp`。

    功能说明:
    - 测试 rewrite 正例时读取 offset/shape/stride/source。

    使用示例:
    - reinterpret = _single_reinterpret(module)
    """

    matches = _ops(module, DmaReinterpretOp)
    assert len(matches) == 1
    return matches[0]


def test_dma_alias_to_reinterpret_registry_and_public_options() -> None:
    """验证 pass registry 公开入口。

    功能说明:
    - `dma-alias-to-reinterpret` 可通过 registry 构造。
    - 通用 `fold=false` option 保持可用。

    使用示例:
    - pytest -q test/passes/test_dma_alias_to_reinterpret.py -k registry
    """

    load_builtin_passes()
    pass_obj = build_registered_pass("dma-alias-to-reinterpret", {"fold": "false"})

    assert isinstance(pass_obj, DmaAliasToReinterpretPass)
    assert pass_obj.name == "dma-alias-to-reinterpret"
    assert pass_obj.fold is False


def test_dma_alias_to_reinterpret_rewrites_view_with_linear_offset() -> None:
    """验证 `dma.view` 被归一为线性 offset 的 `dma.reinterpret`。

    功能说明:
    - offset = `offsets dot source.stride`。
    - result shape/stride operand 与原 view/result type 对齐。

    使用示例:
    - pytest -q test/passes/test_dma_alias_to_reinterpret.py -k rewrites_view
    """

    source_type = _memory_type((4, 4), (4, 1))
    result_type = _memory_type((2, 2), (4, 1))
    block = Block(arg_types=[source_type])
    c0 = _symbol_const(0)
    c1 = _symbol_const(1)
    c2 = _symbol_const(2)
    c7 = _scalar_i32(7)
    view = DmaViewOp(block.args[0], [c1.result, c2.result], [c2.result, c2.result], [c1.result, c1.result], result_type)
    module = _module("view_case", block, [c0, c1, c2, c7, view, DmaFillOp(view.result, c7.result)])

    _apply(module)

    reinterpret = _single_reinterpret(module)
    assert reinterpret.source is _func_block(module).args[0]
    assert reinterpret.offset.type.get_value() == 6
    assert [value.type.get_value() for value in reinterpret.shape] == [2, 2]
    assert [value.type.get_value() for value in reinterpret.stride] == [4, 1]
    assert _ops(module, DmaViewOp) == []


def test_dma_alias_to_reinterpret_rewrites_reshape_to_zero_offset() -> None:
    """验证 `dma.reshape` 被归一为 zero-offset `dma.reinterpret`。

    功能说明:
    - reshape 不移动起点，offset 固定为 0。
    - result contiguous stride 来自 result type。

    使用示例:
    - pytest -q test/passes/test_dma_alias_to_reinterpret.py -k reshape
    """

    source_type = _memory_type((4, 4), (4, 1))
    result_type = _memory_type((2, 8), (8, 1))
    block = Block(arg_types=[source_type])
    c0 = _symbol_const(0)
    c1 = _symbol_const(1)
    c2 = _symbol_const(2)
    c8 = _symbol_const(8)
    c7 = _scalar_i32(7)
    reshape = DmaReshapeOp(block.args[0], [c2.result, c8.result], result_type)
    module = _module("reshape_case", block, [c0, c1, c2, c8, c7, reshape, DmaFillOp(reshape.result, c7.result)])

    _apply(module)

    reinterpret = _single_reinterpret(module)
    assert reinterpret.source is _func_block(module).args[0]
    assert reinterpret.offset.type.get_value() == 0
    assert [value.type.get_value() for value in reinterpret.shape] == [2, 8]
    assert [value.type.get_value() for value in reinterpret.stride] == [8, 1]
    assert _ops(module, DmaReshapeOp) == []


def test_dma_alias_to_reinterpret_preserves_unused_rewrite_result() -> None:
    """验证 pass 内部不把未使用 alias 的归一化结果 DCE 掉。

    功能说明:
    - `run_ircheck_text(...)` 的单 pass 路径直接调用 pass apply，不经过 PassManager 通用 DCE。
    - 未使用的 `dma.reshape` 仍应被替换成可观察的 `dma.reinterpret`，使合同验收能锁定 rewrite。

    使用示例:
    - pytest -q test/passes/test_dma_alias_to_reinterpret.py -k preserves_unused
    """

    source_type = _memory_type((16,), (1,), space="tsm")
    result_type = _memory_type((4, 4), (4, 1), space="tsm")
    block = Block(arg_types=[source_type])
    c1 = _symbol_const(1)
    c4 = _symbol_const(4)
    reshape = DmaReshapeOp(block.args[0], [c4.result, c4.result], result_type)
    module = _module("unused_reshape_case", block, [c1, c4, reshape])

    _apply(module)

    assert len(_ops(module, DmaReinterpretOp)) == 1
    assert _ops(module, DmaReshapeOp) == []


def test_dma_alias_to_reinterpret_rewrites_subview_byte_pool() -> None:
    """验证 `dma.subview` 被归一为 byte offset `dma.reinterpret`。

    功能说明:
    - subview offset/size/stride 原样进入 reinterpret。
    - source 是 i8 byte pool 时 result 可为 typed memory。

    使用示例:
    - pytest -q test/passes/test_dma_alias_to_reinterpret.py -k subview
    """

    pool_type = _memory_type((64,), (1,), element_type=i8)
    result_type = _memory_type((4,), (1,), element_type=i32)
    block = Block(arg_types=[pool_type])
    c1 = _symbol_const(1)
    c4 = _symbol_const(4)
    c8 = _symbol_const(8)
    c7 = arith.ConstantOp(IntegerAttr(7, i32))
    subview = DmaSubviewOp(block.args[0], c8.result, c4.result, c1.result, result_type)
    module = _module("subview_case", block, [c1, c4, c8, c7, subview, DmaFillOp(subview.result, c7.result)])

    _apply(module)

    reinterpret = _single_reinterpret(module)
    assert reinterpret.source is _func_block(module).args[0]
    assert reinterpret.offset.type.get_value() == 8
    assert [value.type.get_value() for value in reinterpret.shape] == [4]
    assert [value.type.get_value() for value in reinterpret.stride] == [1]
    assert _ops(module, DmaSubviewOp) == []


def test_dma_alias_to_reinterpret_flattens_alias_chain_to_root() -> None:
    """验证 alias 链被压平成 root source 上的单个 `dma.reinterpret`。

    功能说明:
    - `reshape(view(root))` 不生成 `reinterpret(view(...))` 或嵌套 reinterpret。
    - offset 继承 view 的 root-relative offset。

    使用示例:
    - pytest -q test/passes/test_dma_alias_to_reinterpret.py -k flattens
    """

    source_type = _memory_type((4,), (1,))
    view_type = _memory_type((2,), (1,))
    reshape_type = _memory_type((1, 2), (2, 1))
    block = Block(arg_types=[source_type])
    c1 = _symbol_const(1)
    c2 = _symbol_const(2)
    c7 = _scalar_i32(7)
    view = DmaViewOp(block.args[0], [c1.result], [c2.result], [c1.result], view_type)
    reshape = DmaReshapeOp(view.result, [c1.result, c2.result], reshape_type)
    module = _module("chain_case", block, [c1, c2, c7, view, reshape, DmaFillOp(reshape.result, c7.result)])

    _apply(module)

    reinterpret = _single_reinterpret(module)
    assert reinterpret.source is _func_block(module).args[0]
    assert reinterpret.offset.type.get_value() == 1
    assert _ops(module, DmaViewOp) == []
    assert _ops(module, DmaReshapeOp) == []


def test_dma_alias_to_reinterpret_noops_when_stride_symbol_cannot_materialize() -> None:
    """验证无法 exact 物化 source stride 时保持 no-op。

    功能说明:
    - source type stride 使用动态表达式 `S`，但 block 内没有支配 alias op 的 `!symbol.int<S>`。
    - pass 不猜测 SSA 名称，也不生成不精确 offset。

    使用示例:
    - pytest -q test/passes/test_dma_alias_to_reinterpret.py -k noops
    """

    source_type = _memory_type(("M", "N"), ("S", 1))
    result_type = _memory_type((2, 3), ("S", 1))
    block = Block(arg_types=[source_type, SymbolValueType.from_expr("M0"), SymbolValueType.from_expr("N0")])
    c1 = _symbol_const(1)
    c7 = _scalar_i32(7)
    tm = _symbol_const(2)
    tn = _symbol_const(3)
    view = DmaViewOp(block.args[0], [block.args[1], block.args[2]], [tm.result, tn.result], [c1.result, c1.result], result_type)
    module = _module("noop_case", block, [c1, c7, tm, tn, view, DmaFillOp(view.result, c7.result)])

    _apply(module)

    assert _ops(module, DmaReinterpretOp) == []
    assert len(_ops(module, DmaViewOp)) == 1
