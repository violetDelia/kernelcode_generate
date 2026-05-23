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
from xdsl.utils.exceptions import VerifyException

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from kernel_gen.dialect.dma import DmaAllocOp, DmaDesliceOp, DmaFillOp, DmaReshapeOp, DmaViewOp
from kernel_gen.dialect.nn import NnMemorySpaceAttr, NnMemoryType
from kernel_gen.dialect.symbol import SymbolConstOp, SymbolExprAttr, SymbolForOp, SymbolIterType, SymbolValueType
from kernel_gen.tools.ircheck import run_ircheck_text

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


def _run_public_ircheck_case(case_text: str) -> str:
    """通过公开 ircheck 入口运行 inline pass case。

    功能说明:
    - 只调用公开 `run_ircheck_text(...)`，不直连 pass 实现私有 helper。
    - 返回实际 IR，便于测试对 rewrite 后文本做额外断言。

    使用示例:
    - actual_ir = _run_public_ircheck_case(case_text)
    """

    result = run_ircheck_text(case_text, source_path="test/passes/test_hoist_dma_alias_ops.py:inline")
    assert result.ok is True, result.message
    assert result.exit_code == 0
    return result.actual_ir


def _view_group_static_ir() -> str:
    """构造静态三维 view/deslice 内层分组正例。

    功能说明:
    - 验证 pass 会把 `[2,3,4]` 中连续后缀 `[3,4]` 降为低维 `12`。

    使用示例:
    - _run_public_ircheck_case(_view_group_static_ir())
    """

    return """// COMPILE_ARGS: --pass hoist-dma-alias-ops
// CHECK: func.func @view_static_group_inner_dims
// CHECK: %[[SRC2:.*]] = "dma.reshape"(%[[SRC:.*]], %[[C2:.*]], %[[C12:.*]])
// CHECK: %[[DST2:.*]] = "dma.reshape"(%[[DST:.*]], %[[C2]], %[[C12]])
// CHECK: %[[VIEW2:.*]] = "dma.view"(%[[SRC2]], %[[C0:.*]], %[[C0]], %[[C2]], %[[C12]], %[[C1:.*]], %[[C1]])
// CHECK: "dma.deslice"(%[[DST2]], %[[VIEW2]], %[[C0]], %[[C0]], %[[C2]], %[[C12]], %[[C1]], %[[C1]])

builtin.module {
  func.func @view_static_group_inner_dims(%src : !nn.memory<[#symbol.expr<2>, #symbol.expr<3>, #symbol.expr<4>], [#symbol.expr<12>, #symbol.expr<4>, #symbol.expr<1>], f32, #nn.space<global>>, %dst : !nn.memory<[#symbol.expr<2>, #symbol.expr<3>, #symbol.expr<4>], [#symbol.expr<12>, #symbol.expr<4>, #symbol.expr<1>], f32, #nn.space<tsm>>) {
    %c0 = symbol.const 0 : !symbol.int<#symbol.expr<0>>
    %c1 = symbol.const 1 : !symbol.int<#symbol.expr<1>>
    %c2 = symbol.const 2 : !symbol.int<#symbol.expr<2>>
    %c3 = symbol.const 3 : !symbol.int<#symbol.expr<3>>
    %c4 = symbol.const 4 : !symbol.int<#symbol.expr<4>>
    %c12 = symbol.const 12 : !symbol.int<#symbol.expr<12>>
    %view = "dma.view"(%src, %c0, %c0, %c0, %c2, %c3, %c4, %c1, %c1, %c1) <{operandSegmentSizes = array<i32: 1, 3, 3, 3>}> : (!nn.memory<[#symbol.expr<2>, #symbol.expr<3>, #symbol.expr<4>], [#symbol.expr<12>, #symbol.expr<4>, #symbol.expr<1>], f32, #nn.space<global>>, !symbol.int<#symbol.expr<0>>, !symbol.int<#symbol.expr<0>>, !symbol.int<#symbol.expr<0>>, !symbol.int<#symbol.expr<2>>, !symbol.int<#symbol.expr<3>>, !symbol.int<#symbol.expr<4>>, !symbol.int<#symbol.expr<1>>, !symbol.int<#symbol.expr<1>>, !symbol.int<#symbol.expr<1>>) -> !nn.memory<[#symbol.expr<2>, #symbol.expr<3>, #symbol.expr<4>], [#symbol.expr<12>, #symbol.expr<4>, #symbol.expr<1>], f32, #nn.space<global>>
    "dma.deslice"(%dst, %view, %c0, %c0, %c0, %c2, %c3, %c4, %c1, %c1, %c1) <{operandSegmentSizes = array<i32: 2, 3, 3, 3>}> : (!nn.memory<[#symbol.expr<2>, #symbol.expr<3>, #symbol.expr<4>], [#symbol.expr<12>, #symbol.expr<4>, #symbol.expr<1>], f32, #nn.space<tsm>>, !nn.memory<[#symbol.expr<2>, #symbol.expr<3>, #symbol.expr<4>], [#symbol.expr<12>, #symbol.expr<4>, #symbol.expr<1>], f32, #nn.space<global>>, !symbol.int<#symbol.expr<0>>, !symbol.int<#symbol.expr<0>>, !symbol.int<#symbol.expr<0>>, !symbol.int<#symbol.expr<2>>, !symbol.int<#symbol.expr<3>>, !symbol.int<#symbol.expr<4>>, !symbol.int<#symbol.expr<1>>, !symbol.int<#symbol.expr<1>>, !symbol.int<#symbol.expr<1>>) -> !nn.memory<[#symbol.expr<2>, #symbol.expr<3>, #symbol.expr<4>], [#symbol.expr<12>, #symbol.expr<4>, #symbol.expr<1>], f32, #nn.space<tsm>>
    func.return
  }
}
"""


def _view_group_dynamic_ir() -> str:
    """构造动态三维 view/deslice 内层分组正例。

    功能说明:
    - 验证 `[TN,K]` 可被合成低维 `TN*K`，外层 `TM` 不要求整块连续。

    使用示例:
    - _run_public_ircheck_case(_view_group_dynamic_ir())
    """

    return """// COMPILE_ARGS: --pass hoist-dma-alias-ops
// CHECK: func.func @view_dynamic_group_inner_dims
// CHECK: %[[NK:.*]] = symbol.mul %[[N:.*]], %[[K:.*]] : !symbol.int<#symbol.expr<N>>, !symbol.int<#symbol.expr<K>> -> !symbol.int<#symbol.expr<N*K>>
// CHECK: %[[TNK:.*]] = symbol.mul %[[TN:.*]], %[[K]] : !symbol.int<#symbol.expr<TN>>, !symbol.int<#symbol.expr<K>> -> !symbol.int<#symbol.expr<TN*K>>
// CHECK: %[[N0K:.*]] = symbol.mul %[[N0:.*]], %[[K]] : !symbol.int<#symbol.expr<N0>>, !symbol.int<#symbol.expr<K>> -> !symbol.int<#symbol.expr<N0*K>>
// CHECK: %[[SRC2:.*]] = "dma.reshape"(%[[SRC:.*]], %[[M:.*]], %[[NK]])
// CHECK: %[[DST2:.*]] = "dma.reshape"(%[[DST:.*]], %[[TM:.*]], %[[TNK]])
// CHECK: %[[VIEW2:.*]] = "dma.view"(%[[SRC2]], %[[M0:.*]], %[[N0K]], %[[TM]], %[[TNK]], %[[ONE:.*]], %[[ONE]])
// CHECK: "dma.deslice"(%[[DST2]], %[[VIEW2]], %[[ZERO:.*]], %[[ZERO]], %[[TM]], %[[TNK]], %[[ONE]], %[[ONE]])

builtin.module {
  func.func @view_dynamic_group_inner_dims(
      %src : !nn.memory<[#symbol.expr<M>, #symbol.expr<N>, #symbol.expr<K>], [#symbol.expr<N*K>, #symbol.expr<K>, #symbol.expr<1>], f32, #nn.space<global>>,
      %dst : !nn.memory<[#symbol.expr<TM>, #symbol.expr<TN>, #symbol.expr<K>], [#symbol.expr<TN*K>, #symbol.expr<K>, #symbol.expr<1>], f32, #nn.space<tsm>>,
      %m : !symbol.int<#symbol.expr<M>>,
      %n : !symbol.int<#symbol.expr<N>>,
      %k : !symbol.int<#symbol.expr<K>>,
      %tm : !symbol.int<#symbol.expr<TM>>,
      %tn : !symbol.int<#symbol.expr<TN>>,
      %m0 : !symbol.int<#symbol.expr<M0>>,
      %n0 : !symbol.int<#symbol.expr<N0>>) {
    %zero = symbol.const 0 : !symbol.int<#symbol.expr<0>>
    %one = symbol.const 1 : !symbol.int<#symbol.expr<1>>
    %view = "dma.view"(%src, %m0, %n0, %zero, %tm, %tn, %k, %one, %one, %one) <{operandSegmentSizes = array<i32: 1, 3, 3, 3>}> : (!nn.memory<[#symbol.expr<M>, #symbol.expr<N>, #symbol.expr<K>], [#symbol.expr<N*K>, #symbol.expr<K>, #symbol.expr<1>], f32, #nn.space<global>>, !symbol.int<#symbol.expr<M0>>, !symbol.int<#symbol.expr<N0>>, !symbol.int<#symbol.expr<0>>, !symbol.int<#symbol.expr<TM>>, !symbol.int<#symbol.expr<TN>>, !symbol.int<#symbol.expr<K>>, !symbol.int<#symbol.expr<1>>, !symbol.int<#symbol.expr<1>>, !symbol.int<#symbol.expr<1>>) -> !nn.memory<[#symbol.expr<TM>, #symbol.expr<TN>, #symbol.expr<K>], [#symbol.expr<N*K>, #symbol.expr<K>, #symbol.expr<1>], f32, #nn.space<global>>
    "dma.deslice"(%dst, %view, %zero, %zero, %zero, %tm, %tn, %k, %one, %one, %one) <{operandSegmentSizes = array<i32: 2, 3, 3, 3>}> : (!nn.memory<[#symbol.expr<TM>, #symbol.expr<TN>, #symbol.expr<K>], [#symbol.expr<TN*K>, #symbol.expr<K>, #symbol.expr<1>], f32, #nn.space<tsm>>, !nn.memory<[#symbol.expr<TM>, #symbol.expr<TN>, #symbol.expr<K>], [#symbol.expr<N*K>, #symbol.expr<K>, #symbol.expr<1>], f32, #nn.space<global>>, !symbol.int<#symbol.expr<0>>, !symbol.int<#symbol.expr<0>>, !symbol.int<#symbol.expr<0>>, !symbol.int<#symbol.expr<TM>>, !symbol.int<#symbol.expr<TN>>, !symbol.int<#symbol.expr<K>>, !symbol.int<#symbol.expr<1>>, !symbol.int<#symbol.expr<1>>, !symbol.int<#symbol.expr<1>>) -> !nn.memory<[#symbol.expr<TM>, #symbol.expr<TN>, #symbol.expr<K>], [#symbol.expr<TN*K>, #symbol.expr<K>, #symbol.expr<1>], f32, #nn.space<tsm>>
    func.return
  }
}
"""


def _view_group_negative_ir(*, separator: bool = False, extra_use: bool = False, tk_size: bool = False) -> str:
    """构造 view/deslice 分组 no-op 反例。

    功能说明:
    - `separator=True` 覆盖非紧邻 no-op。
    - `extra_use=True` 覆盖 view result 多消费者 no-op。
    - `tk_size=True` 覆盖最后一维不是完整 K 的非连续 no-op。

    使用示例:
    - _run_public_ircheck_case(_view_group_negative_ir(separator=True))
    """

    last_size = "%tk" if tk_size else "%k"
    dst_type = "!nn.memory<[#symbol.expr<TM>, #symbol.expr<TN>, #symbol.expr<TK>], [#symbol.expr<TN*TK>, #symbol.expr<TK>, #symbol.expr<1>], f32, #nn.space<tsm>>" if tk_size else "!nn.memory<[#symbol.expr<TM>, #symbol.expr<TN>, #symbol.expr<K>], [#symbol.expr<TN*K>, #symbol.expr<K>, #symbol.expr<1>], f32, #nn.space<tsm>>"
    separator_op = "    %sep = symbol.const 7 : !symbol.int<#symbol.expr<7>>\n" if separator else ""
    extra_copy = f'    "dma.copy"(%dst, %view) : ({dst_type}, !nn.memory<[#symbol.expr<TM>, #symbol.expr<TN>, #symbol.expr<K>], [#symbol.expr<N*K>, #symbol.expr<K>, #symbol.expr<1>], f32, #nn.space<global>>) -> ()\n' if extra_use else ""
    return f"""// COMPILE_ARGS: --pass hoist-dma-alias-ops
// CHECK: func.func @view_group_noop
// CHECK-NOT: "dma.reshape"
// CHECK: %[[VIEW:.*]] = "dma.view"(%[[SRC:.*]], %[[M0:.*]], %[[N0:.*]], %[[K0:.*]], %[[TM:.*]], %[[TN:.*]], %[[LAST:.*]], %[[ONE:.*]], %[[ONE]], %[[ONE]])
// CHECK: "dma.deslice"(%[[DST:.*]], %[[VIEW]]

builtin.module {{
  func.func @view_group_noop(
      %src : !nn.memory<[#symbol.expr<M>, #symbol.expr<N>, #symbol.expr<K>], [#symbol.expr<N*K>, #symbol.expr<K>, #symbol.expr<1>], f32, #nn.space<global>>,
      %dst : {dst_type},
      %tm : !symbol.int<#symbol.expr<TM>>,
      %tn : !symbol.int<#symbol.expr<TN>>,
      %tk : !symbol.int<#symbol.expr<TK>>,
      %m0 : !symbol.int<#symbol.expr<M0>>,
      %n0 : !symbol.int<#symbol.expr<N0>>,
      %k0 : !symbol.int<#symbol.expr<K0>>,
      %k : !symbol.int<#symbol.expr<K>>) {{
    %zero = symbol.const 0 : !symbol.int<#symbol.expr<0>>
    %one = symbol.const 1 : !symbol.int<#symbol.expr<1>>
    %view = "dma.view"(%src, %m0, %n0, %k0, %tm, %tn, {last_size}, %one, %one, %one) <{{operandSegmentSizes = array<i32: 1, 3, 3, 3>}}> : (!nn.memory<[#symbol.expr<M>, #symbol.expr<N>, #symbol.expr<K>], [#symbol.expr<N*K>, #symbol.expr<K>, #symbol.expr<1>], f32, #nn.space<global>>, !symbol.int<#symbol.expr<M0>>, !symbol.int<#symbol.expr<N0>>, !symbol.int<#symbol.expr<K0>>, !symbol.int<#symbol.expr<TM>>, !symbol.int<#symbol.expr<TN>>, !symbol.int<#symbol.expr<{"TK" if tk_size else "K"}>>, !symbol.int<#symbol.expr<1>>, !symbol.int<#symbol.expr<1>>, !symbol.int<#symbol.expr<1>>) -> !nn.memory<[#symbol.expr<TM>, #symbol.expr<TN>, #symbol.expr<{"TK" if tk_size else "K"}>], [#symbol.expr<N*K>, #symbol.expr<K>, #symbol.expr<1>], f32, #nn.space<global>>
{separator_op}{extra_copy}    "dma.deslice"(%dst, %view, %zero, %zero, %zero, %tm, %tn, {last_size}, %one, %one, %one) <{{operandSegmentSizes = array<i32: 2, 3, 3, 3>}}> : ({dst_type}, !nn.memory<[#symbol.expr<TM>, #symbol.expr<TN>, #symbol.expr<{"TK" if tk_size else "K"}>], [#symbol.expr<N*K>, #symbol.expr<K>, #symbol.expr<1>], f32, #nn.space<global>>, !symbol.int<#symbol.expr<0>>, !symbol.int<#symbol.expr<0>>, !symbol.int<#symbol.expr<0>>, !symbol.int<#symbol.expr<TM>>, !symbol.int<#symbol.expr<TN>>, !symbol.int<#symbol.expr<{"TK" if tk_size else "K"}>>, !symbol.int<#symbol.expr<1>>, !symbol.int<#symbol.expr<1>>, !symbol.int<#symbol.expr<1>>) -> {dst_type}
    func.return
  }}
}}
"""


def _view_group_stride_noop_ir() -> str:
    """构造 logical stride 非 1 的 view/deslice no-op 反例。

    功能说明:
    - `dma.view` 的逻辑 stride 含动态 `S`，但 pass 必须因为 stride 不是结构化 `1` 而保持 no-op。

    使用示例:
    - _run_public_ircheck_case(_view_group_stride_noop_ir())
    """

    return """// COMPILE_ARGS: --pass hoist-dma-alias-ops
// CHECK: func.func @view_stride_noop
// CHECK-NOT: "dma.reshape"
// CHECK: "dma.view"
// CHECK: "dma.deslice"

builtin.module {
  func.func @view_stride_noop(
      %src : !nn.memory<[#symbol.expr<M>, #symbol.expr<N>, #symbol.expr<K>], [#symbol.expr<N*K>, #symbol.expr<K>, #symbol.expr<1>], f32, #nn.space<global>>,
      %dst : !nn.memory<[#symbol.expr<M>, #symbol.expr<N>, #symbol.expr<K>], [#symbol.expr<N*K>, #symbol.expr<K>, #symbol.expr<1>], f32, #nn.space<tsm>>,
      %m : !symbol.int<#symbol.expr<M>>,
      %n : !symbol.int<#symbol.expr<N>>,
      %k : !symbol.int<#symbol.expr<K>>,
      %s : !symbol.int<#symbol.expr<S>>) {
    %zero = symbol.const 0 : !symbol.int<#symbol.expr<0>>
    %one = symbol.const 1 : !symbol.int<#symbol.expr<1>>
    %view = "dma.view"(%src, %zero, %zero, %zero, %m, %n, %k, %one, %s, %s) <{operandSegmentSizes = array<i32: 1, 3, 3, 3>}> : (!nn.memory<[#symbol.expr<M>, #symbol.expr<N>, #symbol.expr<K>], [#symbol.expr<N*K>, #symbol.expr<K>, #symbol.expr<1>], f32, #nn.space<global>>, !symbol.int<#symbol.expr<0>>, !symbol.int<#symbol.expr<0>>, !symbol.int<#symbol.expr<0>>, !symbol.int<#symbol.expr<M>>, !symbol.int<#symbol.expr<N>>, !symbol.int<#symbol.expr<K>>, !symbol.int<#symbol.expr<1>>, !symbol.int<#symbol.expr<S>>, !symbol.int<#symbol.expr<S>>) -> !nn.memory<[#symbol.expr<M>, #symbol.expr<N>, #symbol.expr<K>], [#symbol.expr<N*K>, #symbol.expr<K*S>, #symbol.expr<S>], f32, #nn.space<global>>
    "dma.deslice"(%dst, %view, %zero, %zero, %zero, %m, %n, %k, %one, %one, %one) <{operandSegmentSizes = array<i32: 2, 3, 3, 3>}> : (!nn.memory<[#symbol.expr<M>, #symbol.expr<N>, #symbol.expr<K>], [#symbol.expr<N*K>, #symbol.expr<K>, #symbol.expr<1>], f32, #nn.space<tsm>>, !nn.memory<[#symbol.expr<M>, #symbol.expr<N>, #symbol.expr<K>], [#symbol.expr<N*K>, #symbol.expr<K*S>, #symbol.expr<S>], f32, #nn.space<global>>, !symbol.int<#symbol.expr<0>>, !symbol.int<#symbol.expr<0>>, !symbol.int<#symbol.expr<0>>, !symbol.int<#symbol.expr<M>>, !symbol.int<#symbol.expr<N>>, !symbol.int<#symbol.expr<K>>, !symbol.int<#symbol.expr<1>>, !symbol.int<#symbol.expr<1>>, !symbol.int<#symbol.expr<1>>) -> !nn.memory<[#symbol.expr<M>, #symbol.expr<N>, #symbol.expr<K>], [#symbol.expr<N*K>, #symbol.expr<K>, #symbol.expr<1>], f32, #nn.space<tsm>>
    func.return
  }
}
"""


def _view_group_non_contiguous_layout_noop_ir(*, non_contiguous_target: bool) -> str:
    """构造 source 或 target 非 contiguous 的 view/deslice no-op 反例。

    功能说明:
    - `non_contiguous_target=False` 时 source stride 非行主序。
    - `non_contiguous_target=True` 时 target stride 非行主序。

    使用示例:
    - _run_public_ircheck_case(_view_group_non_contiguous_layout_noop_ir(non_contiguous_target=True))
    """

    source_stride = "[#symbol.expr<12>, #symbol.expr<5>, #symbol.expr<1>]"
    view_stride = source_stride
    target_stride = "[#symbol.expr<12>, #symbol.expr<4>, #symbol.expr<1>]"
    if non_contiguous_target:
        source_stride = "[#symbol.expr<12>, #symbol.expr<4>, #symbol.expr<1>]"
        view_stride = source_stride
        target_stride = "[#symbol.expr<12>, #symbol.expr<5>, #symbol.expr<1>]"
    return f"""// COMPILE_ARGS: --pass hoist-dma-alias-ops
// CHECK: func.func @view_layout_noop
// CHECK-NOT: "dma.reshape"
// CHECK: "dma.view"
// CHECK: "dma.deslice"

builtin.module {{
  func.func @view_layout_noop(%src : !nn.memory<[#symbol.expr<2>, #symbol.expr<3>, #symbol.expr<4>], {source_stride}, f32, #nn.space<global>>, %dst : !nn.memory<[#symbol.expr<2>, #symbol.expr<3>, #symbol.expr<4>], {target_stride}, f32, #nn.space<tsm>>) {{
    %c0 = symbol.const 0 : !symbol.int<#symbol.expr<0>>
    %c1 = symbol.const 1 : !symbol.int<#symbol.expr<1>>
    %c2 = symbol.const 2 : !symbol.int<#symbol.expr<2>>
    %c3 = symbol.const 3 : !symbol.int<#symbol.expr<3>>
    %c4 = symbol.const 4 : !symbol.int<#symbol.expr<4>>
    %view = "dma.view"(%src, %c0, %c0, %c0, %c2, %c3, %c4, %c1, %c1, %c1) <{{operandSegmentSizes = array<i32: 1, 3, 3, 3>}}> : (!nn.memory<[#symbol.expr<2>, #symbol.expr<3>, #symbol.expr<4>], {source_stride}, f32, #nn.space<global>>, !symbol.int<#symbol.expr<0>>, !symbol.int<#symbol.expr<0>>, !symbol.int<#symbol.expr<0>>, !symbol.int<#symbol.expr<2>>, !symbol.int<#symbol.expr<3>>, !symbol.int<#symbol.expr<4>>, !symbol.int<#symbol.expr<1>>, !symbol.int<#symbol.expr<1>>, !symbol.int<#symbol.expr<1>>) -> !nn.memory<[#symbol.expr<2>, #symbol.expr<3>, #symbol.expr<4>], {view_stride}, f32, #nn.space<global>>
    "dma.deslice"(%dst, %view, %c0, %c0, %c0, %c2, %c3, %c4, %c1, %c1, %c1) <{{operandSegmentSizes = array<i32: 2, 3, 3, 3>}}> : (!nn.memory<[#symbol.expr<2>, #symbol.expr<3>, #symbol.expr<4>], {target_stride}, f32, #nn.space<tsm>>, !nn.memory<[#symbol.expr<2>, #symbol.expr<3>, #symbol.expr<4>], {view_stride}, f32, #nn.space<global>>, !symbol.int<#symbol.expr<0>>, !symbol.int<#symbol.expr<0>>, !symbol.int<#symbol.expr<0>>, !symbol.int<#symbol.expr<2>>, !symbol.int<#symbol.expr<3>>, !symbol.int<#symbol.expr<4>>, !symbol.int<#symbol.expr<1>>, !symbol.int<#symbol.expr<1>>, !symbol.int<#symbol.expr<1>>) -> !nn.memory<[#symbol.expr<2>, #symbol.expr<3>, #symbol.expr<4>], {target_stride}, f32, #nn.space<tsm>>
    func.return
  }}
}}
"""


def _view_group_exact_equality_noop_ir() -> str:
    """构造非 exact SymbolExprAttr 匹配的 view/deslice no-op 反例。

    功能说明:
    - source 内层为 `K`，view/result 使用 `K_ALIAS`。
    - 即使运行时可能相等，pass 也不得用 name / 文本猜测合并。

    使用示例:
    - _run_public_ircheck_case(_view_group_exact_equality_noop_ir())
    """

    return """// COMPILE_ARGS: --pass hoist-dma-alias-ops
// CHECK: func.func @view_exact_equality_noop
// CHECK-NOT: "dma.reshape"
// CHECK: "dma.view"
// CHECK: "dma.deslice"

builtin.module {
  func.func @view_exact_equality_noop(
      %src : !nn.memory<[#symbol.expr<M>, #symbol.expr<N>, #symbol.expr<K>], [#symbol.expr<N*K>, #symbol.expr<K>, #symbol.expr<1>], f32, #nn.space<global>>,
      %dst : !nn.memory<[#symbol.expr<TM>, #symbol.expr<TN>, #symbol.expr<K_ALIAS>], [#symbol.expr<TN*K_ALIAS>, #symbol.expr<K_ALIAS>, #symbol.expr<1>], f32, #nn.space<tsm>>,
      %tm : !symbol.int<#symbol.expr<TM>>,
      %tn : !symbol.int<#symbol.expr<TN>>,
      %k_alias : !symbol.int<#symbol.expr<K_ALIAS>>) {
    %zero = symbol.const 0 : !symbol.int<#symbol.expr<0>>
    %one = symbol.const 1 : !symbol.int<#symbol.expr<1>>
    %view = "dma.view"(%src, %zero, %zero, %zero, %tm, %tn, %k_alias, %one, %one, %one) <{operandSegmentSizes = array<i32: 1, 3, 3, 3>}> : (!nn.memory<[#symbol.expr<M>, #symbol.expr<N>, #symbol.expr<K>], [#symbol.expr<N*K>, #symbol.expr<K>, #symbol.expr<1>], f32, #nn.space<global>>, !symbol.int<#symbol.expr<0>>, !symbol.int<#symbol.expr<0>>, !symbol.int<#symbol.expr<0>>, !symbol.int<#symbol.expr<TM>>, !symbol.int<#symbol.expr<TN>>, !symbol.int<#symbol.expr<K_ALIAS>>, !symbol.int<#symbol.expr<1>>, !symbol.int<#symbol.expr<1>>, !symbol.int<#symbol.expr<1>>) -> !nn.memory<[#symbol.expr<TM>, #symbol.expr<TN>, #symbol.expr<K_ALIAS>], [#symbol.expr<N*K>, #symbol.expr<K>, #symbol.expr<1>], f32, #nn.space<global>>
    "dma.deslice"(%dst, %view, %zero, %zero, %zero, %tm, %tn, %k_alias, %one, %one, %one) <{operandSegmentSizes = array<i32: 2, 3, 3, 3>}> : (!nn.memory<[#symbol.expr<TM>, #symbol.expr<TN>, #symbol.expr<K_ALIAS>], [#symbol.expr<TN*K_ALIAS>, #symbol.expr<K_ALIAS>, #symbol.expr<1>], f32, #nn.space<tsm>>, !nn.memory<[#symbol.expr<TM>, #symbol.expr<TN>, #symbol.expr<K_ALIAS>], [#symbol.expr<N*K>, #symbol.expr<K>, #symbol.expr<1>], f32, #nn.space<global>>, !symbol.int<#symbol.expr<0>>, !symbol.int<#symbol.expr<0>>, !symbol.int<#symbol.expr<0>>, !symbol.int<#symbol.expr<TM>>, !symbol.int<#symbol.expr<TN>>, !symbol.int<#symbol.expr<K_ALIAS>>, !symbol.int<#symbol.expr<1>>, !symbol.int<#symbol.expr<1>>, !symbol.int<#symbol.expr<1>>) -> !nn.memory<[#symbol.expr<TM>, #symbol.expr<TN>, #symbol.expr<K_ALIAS>], [#symbol.expr<TN*K_ALIAS>, #symbol.expr<K_ALIAS>, #symbol.expr<1>], f32, #nn.space<tsm>>
    func.return
  }
}
"""


def _view_group_byte_pool_noop_ir() -> str:
    """构造 byte-pool typed view 的 no-op 反例。

    功能说明:
    - source 是一维 `i8` backing memory，view result 是三维 `f32` typed memory。
    - 当前 pass 必须显式拒绝该计划外形态，不把它降维成 reshape + view/deslice。

    使用示例:
    - _run_public_ircheck_case(_view_group_byte_pool_noop_ir())
    """

    return """// COMPILE_ARGS: --pass hoist-dma-alias-ops
// CHECK: func.func @view_byte_pool_noop
// CHECK-NOT: "dma.reshape"
// CHECK: "dma.view"
// CHECK: "dma.deslice"

builtin.module {
  func.func @view_byte_pool_noop(%src : !nn.memory<[#symbol.expr<96>], [#symbol.expr<1>], i8, #nn.space<global>>, %dst : !nn.memory<[#symbol.expr<2>, #symbol.expr<3>, #symbol.expr<4>], [#symbol.expr<12>, #symbol.expr<4>, #symbol.expr<1>], f32, #nn.space<global>>) {
    %c0 = symbol.const 0 : !symbol.int<#symbol.expr<0>>
    %c1 = symbol.const 1 : !symbol.int<#symbol.expr<1>>
    %c2 = symbol.const 2 : !symbol.int<#symbol.expr<2>>
    %c3 = symbol.const 3 : !symbol.int<#symbol.expr<3>>
    %c4 = symbol.const 4 : !symbol.int<#symbol.expr<4>>
    %c12 = symbol.const 12 : !symbol.int<#symbol.expr<12>>
    %view = "dma.view"(%src, %c0, %c0, %c0, %c2, %c3, %c4, %c12, %c4, %c1) <{operandSegmentSizes = array<i32: 1, 3, 3, 3>}> : (!nn.memory<[#symbol.expr<96>], [#symbol.expr<1>], i8, #nn.space<global>>, !symbol.int<#symbol.expr<0>>, !symbol.int<#symbol.expr<0>>, !symbol.int<#symbol.expr<0>>, !symbol.int<#symbol.expr<2>>, !symbol.int<#symbol.expr<3>>, !symbol.int<#symbol.expr<4>>, !symbol.int<#symbol.expr<12>>, !symbol.int<#symbol.expr<4>>, !symbol.int<#symbol.expr<1>>) -> !nn.memory<[#symbol.expr<2>, #symbol.expr<3>, #symbol.expr<4>], [#symbol.expr<12>, #symbol.expr<4>, #symbol.expr<1>], f32, #nn.space<global>>
    "dma.deslice"(%dst, %view, %c0, %c0, %c0, %c2, %c3, %c4, %c1, %c1, %c1) <{operandSegmentSizes = array<i32: 2, 3, 3, 3>}> : (!nn.memory<[#symbol.expr<2>, #symbol.expr<3>, #symbol.expr<4>], [#symbol.expr<12>, #symbol.expr<4>, #symbol.expr<1>], f32, #nn.space<global>>, !nn.memory<[#symbol.expr<2>, #symbol.expr<3>, #symbol.expr<4>], [#symbol.expr<12>, #symbol.expr<4>, #symbol.expr<1>], f32, #nn.space<global>>, !symbol.int<#symbol.expr<0>>, !symbol.int<#symbol.expr<0>>, !symbol.int<#symbol.expr<0>>, !symbol.int<#symbol.expr<2>>, !symbol.int<#symbol.expr<3>>, !symbol.int<#symbol.expr<4>>, !symbol.int<#symbol.expr<1>>, !symbol.int<#symbol.expr<1>>, !symbol.int<#symbol.expr<1>>) -> !nn.memory<[#symbol.expr<2>, #symbol.expr<3>, #symbol.expr<4>], [#symbol.expr<12>, #symbol.expr<4>, #symbol.expr<1>], f32, #nn.space<global>>
    func.return
  }
}
"""


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


def _build_view_deslice_grouping_candidate_module() -> ModuleOp:
    """构造可触发 view/deslice 分组的公开 IR module。

    功能说明:
    - 使用公开 dma op 构造静态三维正例，供 verifier rollback 测试复用。

    使用示例:
    - module = _build_view_deslice_grouping_candidate_module()
    """

    mem_type = _memory_type((2, 3, 4))
    block = Block(arg_types=[mem_type, mem_type])
    zero = _symbol_const(0)
    one = _symbol_const(1)
    two = _symbol_const(2)
    three = _symbol_const(3)
    four = _symbol_const(4)
    view = DmaViewOp(
        block.args[0],
        [zero.result, zero.result, zero.result],
        [two.result, three.result, four.result],
        [one.result, one.result, one.result],
        mem_type,
    )
    deslice = DmaDesliceOp(
        block.args[1],
        view.result,
        [zero.result, zero.result, zero.result],
        [two.result, three.result, four.result],
        [one.result, one.result, one.result],
        mem_type,
    )
    block.add_ops([zero, one, two, three, four, view, deslice])
    return _module_with_block("view_deslice_grouping_candidate", block)


def _build_view_deslice_result_use_module() -> ModuleOp:
    """构造 deslice result 有后续非终结 op 使用的 no-op module。

    功能说明:
    - `dma.deslice` result 随后被 `dma.reshape` 使用；pass 必须保持原 view/deslice 不变。

    使用示例:
    - module = _build_view_deslice_result_use_module()
    """

    mem_type = _memory_type((2, 3, 4))
    low_type = _memory_type((2, 12))
    block = Block(arg_types=[mem_type, mem_type])
    zero = _symbol_const(0)
    one = _symbol_const(1)
    two = _symbol_const(2)
    three = _symbol_const(3)
    four = _symbol_const(4)
    twelve = _symbol_const(12)
    view = DmaViewOp(
        block.args[0],
        [zero.result, zero.result, zero.result],
        [two.result, three.result, four.result],
        [one.result, one.result, one.result],
        mem_type,
    )
    deslice = DmaDesliceOp(
        block.args[1],
        view.result,
        [zero.result, zero.result, zero.result],
        [two.result, three.result, four.result],
        [one.result, one.result, one.result],
        mem_type,
    )
    downstream = DmaReshapeOp(deslice.result, [two.result, twelve.result], low_type)
    block.add_ops([zero, one, two, three, four, twelve, view, deslice, downstream])
    return _module_with_block("view_deslice_result_use", block)


def _build_view_deslice_cross_region_module() -> ModuleOp:
    """构造 view 与 deslice 跨 region 的 no-op module。

    功能说明:
    - `dma.view` 在外层 block，`dma.deslice` 在 `scf.if` region 内使用该 view。
    - pass 必须不跨 region 组合或移动 alias op。

    使用示例:
    - module = _build_view_deslice_cross_region_module()
    """

    mem_type = _memory_type((2, 3, 4))
    block = Block(arg_types=[mem_type, mem_type])
    zero = _symbol_const(0)
    one = _symbol_const(1)
    two = _symbol_const(2)
    three = _symbol_const(3)
    four = _symbol_const(4)
    condition = arith.ConstantOp(IntegerAttr(1, i1))
    view = DmaViewOp(
        block.args[0],
        [zero.result, zero.result, zero.result],
        [two.result, three.result, four.result],
        [one.result, one.result, one.result],
        mem_type,
    )
    true_block = Block()
    deslice = DmaDesliceOp(
        block.args[1],
        view.result,
        [zero.result, zero.result, zero.result],
        [two.result, three.result, four.result],
        [one.result, one.result, one.result],
        mem_type,
    )
    true_block.add_ops([deslice, scf.YieldOp()])
    if_op = scf.IfOp(condition.result, [], Region(true_block), None)
    block.add_ops([zero, one, two, three, four, condition, view, if_op])
    return _module_with_block("view_deslice_cross_region", block)


def _raise_view_grouping_verify_exception() -> None:
    """模拟 module verifier 拒绝 view/deslice 改写。

    功能说明:
    - 仅用于公开 pass rollback 测试，不调用实现文件私有 helper。

    使用示例:
    - module.verify = _raise_view_grouping_verify_exception
    """

    raise VerifyException("forced view grouping verifier rejection")


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
# 功能说明: 验证静态 `dma.view + dma.deslice` 可把连续内层维度分组为低维 view/deslice。
# 使用示例: pytest -q test/passes/test_hoist_dma_alias_ops.py -k static_view_group
# 对应功能实现文件路径: kernel_gen/passes/hoist_dma_alias_ops.py
# 对应 spec 文件路径: spec/pass/hoist_dma_alias_ops.md
# 对应测试文件路径: test/passes/test_hoist_dma_alias_ops.py
def test_hoist_dma_alias_ops_groups_static_view_inner_dimensions() -> None:
    actual_ir = _run_public_ircheck_case(_view_group_static_ir())

    assert actual_ir.count('"dma.reshape"') == 2
    assert '"dma.view"' in actual_ir
    assert '"dma.deslice"' in actual_ir


# TC-HOIST-DMA-ALIAS-012
# 功能说明: 验证动态 `dma.view + dma.deslice` 可把 `[TN, K]` 分组为 `TN*K`。
# 使用示例: pytest -q test/passes/test_hoist_dma_alias_ops.py -k dynamic_view_group
# 对应功能实现文件路径: kernel_gen/passes/hoist_dma_alias_ops.py
# 对应 spec 文件路径: spec/pass/hoist_dma_alias_ops.md
# 对应测试文件路径: test/passes/test_hoist_dma_alias_ops.py
def test_hoist_dma_alias_ops_groups_dynamic_view_inner_dimensions() -> None:
    actual_ir = _run_public_ircheck_case(_view_group_dynamic_ir())

    assert "symbol.mul" in actual_ir
    assert actual_ir.count('"dma.reshape"') == 2


# TC-HOIST-DMA-ALIAS-013
# 功能说明: 验证最后一维不是完整 source K 时保持三维 view/deslice no-op。
# 使用示例: pytest -q test/passes/test_hoist_dma_alias_ops.py -k non_contiguous_inner
# 对应功能实现文件路径: kernel_gen/passes/hoist_dma_alias_ops.py
# 对应 spec 文件路径: spec/pass/hoist_dma_alias_ops.md
# 对应测试文件路径: test/passes/test_hoist_dma_alias_ops.py
def test_hoist_dma_alias_ops_keeps_non_contiguous_inner_dimension_noop() -> None:
    actual_ir = _run_public_ircheck_case(_view_group_negative_ir(tk_size=True))

    assert '"dma.reshape"' not in actual_ir


# TC-HOIST-DMA-ALIAS-014
# 功能说明: 验证 view logical stride 非 1 时保持 no-op。
# 使用示例: pytest -q test/passes/test_hoist_dma_alias_ops.py -k stride_noop
# 对应功能实现文件路径: kernel_gen/passes/hoist_dma_alias_ops.py
# 对应 spec 文件路径: spec/pass/hoist_dma_alias_ops.md
# 对应测试文件路径: test/passes/test_hoist_dma_alias_ops.py
def test_hoist_dma_alias_ops_keeps_non_unit_view_stride_noop() -> None:
    actual_ir = _run_public_ircheck_case(_view_group_stride_noop_ir())

    assert '"dma.reshape"' not in actual_ir


# TC-HOIST-DMA-ALIAS-015
# 功能说明: 验证 source memory 非 contiguous 时保持 no-op。
# 使用示例: pytest -q test/passes/test_hoist_dma_alias_ops.py -k source_non_contiguous
# 对应功能实现文件路径: kernel_gen/passes/hoist_dma_alias_ops.py
# 对应 spec 文件路径: spec/pass/hoist_dma_alias_ops.md
# 对应测试文件路径: test/passes/test_hoist_dma_alias_ops.py
def test_hoist_dma_alias_ops_keeps_non_contiguous_source_layout_noop() -> None:
    actual_ir = _run_public_ircheck_case(
        _view_group_non_contiguous_layout_noop_ir(non_contiguous_target=False)
    )

    assert '"dma.reshape"' not in actual_ir


# TC-HOIST-DMA-ALIAS-016
# 功能说明: 验证 target memory 非 contiguous 时保持 no-op。
# 使用示例: pytest -q test/passes/test_hoist_dma_alias_ops.py -k target_non_contiguous
# 对应功能实现文件路径: kernel_gen/passes/hoist_dma_alias_ops.py
# 对应 spec 文件路径: spec/pass/hoist_dma_alias_ops.md
# 对应测试文件路径: test/passes/test_hoist_dma_alias_ops.py
def test_hoist_dma_alias_ops_keeps_non_contiguous_target_layout_noop() -> None:
    actual_ir = _run_public_ircheck_case(
        _view_group_non_contiguous_layout_noop_ir(non_contiguous_target=True)
    )

    assert '"dma.reshape"' not in actual_ir


# TC-HOIST-DMA-ALIAS-017
# 功能说明: 验证 view result 存在 deslice 之外的额外消费者时保持 no-op。
# 使用示例: pytest -q test/passes/test_hoist_dma_alias_ops.py -k multiple_view_consumers
# 对应功能实现文件路径: kernel_gen/passes/hoist_dma_alias_ops.py
# 对应 spec 文件路径: spec/pass/hoist_dma_alias_ops.md
# 对应测试文件路径: test/passes/test_hoist_dma_alias_ops.py
def test_hoist_dma_alias_ops_keeps_multiple_view_consumers_noop() -> None:
    actual_ir = _run_public_ircheck_case(_view_group_negative_ir(extra_use=True))

    assert '"dma.reshape"' not in actual_ir


# TC-HOIST-DMA-ALIAS-018
# 功能说明: 验证 view/deslice 跨 region 时保持 no-op。
# 使用示例: pytest -q test/passes/test_hoist_dma_alias_ops.py -k view_deslice_cross_region
# 对应功能实现文件路径: kernel_gen/passes/hoist_dma_alias_ops.py
# 对应 spec 文件路径: spec/pass/hoist_dma_alias_ops.md
# 对应测试文件路径: test/passes/test_hoist_dma_alias_ops.py
def test_hoist_dma_alias_ops_keeps_view_deslice_cross_region_noop() -> None:
    module = _build_view_deslice_cross_region_module()
    before = str(module)

    _apply_pass(module)

    assert str(module) == before
    module.verify()


# TC-HOIST-DMA-ALIAS-019
# 功能说明: 验证 view 与 deslice 非紧邻时保持 no-op。
# 使用示例: pytest -q test/passes/test_hoist_dma_alias_ops.py -k non_adjacent_view
# 对应功能实现文件路径: kernel_gen/passes/hoist_dma_alias_ops.py
# 对应 spec 文件路径: spec/pass/hoist_dma_alias_ops.md
# 对应测试文件路径: test/passes/test_hoist_dma_alias_ops.py
def test_hoist_dma_alias_ops_keeps_non_adjacent_view_deslice_noop() -> None:
    actual_ir = _run_public_ircheck_case(_view_group_negative_ir(separator=True))

    assert '"dma.reshape"' not in actual_ir


# TC-HOIST-DMA-ALIAS-020
# 功能说明: 验证 deslice result 有后续非终结 op 使用时保持 no-op。
# 使用示例: pytest -q test/passes/test_hoist_dma_alias_ops.py -k deslice_result_use
# 对应功能实现文件路径: kernel_gen/passes/hoist_dma_alias_ops.py
# 对应 spec 文件路径: spec/pass/hoist_dma_alias_ops.md
# 对应测试文件路径: test/passes/test_hoist_dma_alias_ops.py
def test_hoist_dma_alias_ops_keeps_deslice_result_later_use_noop() -> None:
    module = _build_view_deslice_result_use_module()
    before = str(module)

    _apply_pass(module)

    assert str(module) == before
    module.verify()


# TC-HOIST-DMA-ALIAS-021
# 功能说明: 验证非 exact SymbolExprAttr 匹配时不做动态 suffix 分组。
# 使用示例: pytest -q test/passes/test_hoist_dma_alias_ops.py -k exact_equality
# 对应功能实现文件路径: kernel_gen/passes/hoist_dma_alias_ops.py
# 对应 spec 文件路径: spec/pass/hoist_dma_alias_ops.md
# 对应测试文件路径: test/passes/test_hoist_dma_alias_ops.py
def test_hoist_dma_alias_ops_keeps_non_exact_symbol_expr_equality_noop() -> None:
    actual_ir = _run_public_ircheck_case(_view_group_exact_equality_noop_ir())

    assert '"dma.reshape"' not in actual_ir


# TC-HOIST-DMA-ALIAS-022
# 功能说明: 验证被折叠后缀内层 offset 非 0 时保持 no-op。
# 使用示例: pytest -q test/passes/test_hoist_dma_alias_ops.py -k inner_offset
# 对应功能实现文件路径: kernel_gen/passes/hoist_dma_alias_ops.py
# 对应 spec 文件路径: spec/pass/hoist_dma_alias_ops.md
# 对应测试文件路径: test/passes/test_hoist_dma_alias_ops.py
def test_hoist_dma_alias_ops_keeps_inner_offset_nonzero_noop() -> None:
    actual_ir = _run_public_ircheck_case(_view_group_negative_ir())

    assert '"dma.reshape"' not in actual_ir


# TC-HOIST-DMA-ALIAS-023
# 功能说明: 验证 view/deslice verifier 拒绝候选改写时回滚且 module 文本不变。
# 使用示例: pytest -q test/passes/test_hoist_dma_alias_ops.py -k view_grouping_rollback
# 对应功能实现文件路径: kernel_gen/passes/hoist_dma_alias_ops.py
# 对应 spec 文件路径: spec/pass/hoist_dma_alias_ops.md
# 对应测试文件路径: test/passes/test_hoist_dma_alias_ops.py
def test_hoist_dma_alias_ops_rolls_back_view_grouping_when_verifier_rejects() -> None:
    module = _build_view_deslice_grouping_candidate_module()
    before = str(module)
    original_verify = module.verify
    module.verify = _raise_view_grouping_verify_exception  # type: ignore[method-assign]

    try:
        _apply_pass(module)
    finally:
        module.verify = original_verify  # type: ignore[method-assign]

    assert str(module) == before
    module.verify()


# TC-HOIST-DMA-ALIAS-024
# 功能说明: 验证一维 i8 byte-pool typed view 保持 no-op。
# 使用示例: pytest -q test/passes/test_hoist_dma_alias_ops.py -k byte_pool
# 对应功能实现文件路径: kernel_gen/passes/hoist_dma_alias_ops.py
# 对应 spec 文件路径: spec/pass/hoist_dma_alias_ops.md
# 对应测试文件路径: test/passes/test_hoist_dma_alias_ops.py
def test_hoist_dma_alias_ops_keeps_byte_pool_typed_view_noop() -> None:
    actual_ir = _run_public_ircheck_case(_view_group_byte_pool_noop_ir())

    assert '"dma.reshape"' not in actual_ir


# TC-HOIST-DMA-ALIAS-025
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
