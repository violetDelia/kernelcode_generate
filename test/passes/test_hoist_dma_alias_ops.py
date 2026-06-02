"""hoist-dma-alias-ops pass tests.

功能说明:
- 覆盖 `hoist-dma-alias-ops` 的公开 pass class、pattern getter、registry 与关键 rewrite/no-op 边界。
- 测试只通过公开 `run_ircheck_text(...)`、`HoistDmaAliasOpsPass` 与 registry 入口观察行为。

使用示例:
- pytest -q test/passes/test_hoist_dma_alias_ops.py

关联文件:
- spec: spec/pass/hoist_dma_alias_ops.md
- test: test/passes/test_hoist_dma_alias_ops.py
- 功能实现: kernel_gen/passes/hoist/dma_alias_ops.py
"""

from __future__ import annotations

import importlib
import inspect

from xdsl.context import Context
from xdsl.dialects.builtin import ModuleOp
from xdsl.pattern_rewriter import RewritePattern

from kernel_gen.core.error import KernelCodeError
from kernel_gen.passes.registry import build_registered_pass, load_builtin_passes
from kernel_gen.tools.ircheck import run_ircheck_text

pass_module = importlib.import_module("kernel_gen.passes.hoist.dma_alias_ops")

DmaAliasHoistPattern = pass_module.DmaAliasHoistPattern
DmaAliasThroughWriteNoReadPattern = pass_module.DmaAliasThroughWriteNoReadPattern
HoistDmaAliasOpsPass = pass_module.HoistDmaAliasOpsPass
get_hoist_dma_alias_ops_pass_patterns = pass_module.get_hoist_dma_alias_ops_pass_patterns


def _run_public_ircheck_case(case_text: str) -> str:
    """运行公开 ircheck inline case。

    功能说明:
    - 只调用公开 `run_ircheck_text(...)`。
    - 返回 actual IR 供测试补充检查。

    使用示例:
    - actual_ir = _run_public_ircheck_case(case_text)
    """

    result = run_ircheck_text(case_text, source_path="test/passes/test_hoist_dma_alias_ops.py:inline")
    assert result.ok is True, result.message
    assert result.exit_code == 0
    return result.actual_ir


def _pure_hoist_view_static_ir() -> str:
    """构造 P1 `dma.view` 纯外提正例 IR。

    功能说明:
    - `dma.fill(%dst)` 与 `dma.view(%src)` 触碰不同 memory。
    - 期望 P1 只移动 view，不改 fill target。

    使用示例:
    - _run_public_ircheck_case(_pure_hoist_view_static_ir())
    """

    return """// COMPILE_ARGS: --pass hoist-dma-alias-ops
// CHECK: func.func @pure_hoist_view_static
// CHECK: %[[VIEW:.*]] = "dma.view"(%[[SRC:.*]], %[[C0:.*]], %[[C0]], %[[C2:.*]], %[[C4:.*]], %[[C1:.*]], %[[C1]])
// CHECK: "dma.fill"(%[[DST:.*]], %[[ZERO:.*]]) : (!nn.memory<[#symbol.expr<2>, #symbol.expr<4>], [#symbol.expr<4>, #symbol.expr<1>], f32, #nn.space<tsm>>, f32) -> ()
// CHECK: "dma.deslice"(%[[DST]], %[[VIEW]], %[[C0]], %[[C0]], %[[C2]], %[[C4]], %[[C1]], %[[C1]])

builtin.module {
  func.func @pure_hoist_view_static(
      %src : !nn.memory<[#symbol.expr<8>, #symbol.expr<8>], [#symbol.expr<8>, #symbol.expr<1>], f32, #nn.space<global>>,
      %dst : !nn.memory<[#symbol.expr<2>, #symbol.expr<4>], [#symbol.expr<4>, #symbol.expr<1>], f32, #nn.space<tsm>>) {
    %c0 = symbol.const 0 : !symbol.int<#symbol.expr<0>>
    %c1 = symbol.const 1 : !symbol.int<#symbol.expr<1>>
    %c2 = symbol.const 2 : !symbol.int<#symbol.expr<2>>
    %c4 = symbol.const 4 : !symbol.int<#symbol.expr<4>>
    %zero = arith.constant 0.000000e+00 : f32
    "dma.fill"(%dst, %zero) : (!nn.memory<[#symbol.expr<2>, #symbol.expr<4>], [#symbol.expr<4>, #symbol.expr<1>], f32, #nn.space<tsm>>, f32) -> ()
    %view = "dma.view"(%src, %c0, %c0, %c2, %c4, %c1, %c1) <{operandSegmentSizes = array<i32: 1, 2, 2, 2>}> : (!nn.memory<[#symbol.expr<8>, #symbol.expr<8>], [#symbol.expr<8>, #symbol.expr<1>], f32, #nn.space<global>>, !symbol.int<#symbol.expr<0>>, !symbol.int<#symbol.expr<0>>, !symbol.int<#symbol.expr<2>>, !symbol.int<#symbol.expr<4>>, !symbol.int<#symbol.expr<1>>, !symbol.int<#symbol.expr<1>>) -> !nn.memory<[#symbol.expr<2>, #symbol.expr<4>], [#symbol.expr<8>, #symbol.expr<1>], f32, #nn.space<global>>
    "dma.deslice"(%dst, %view, %c0, %c0, %c2, %c4, %c1, %c1) <{operandSegmentSizes = array<i32: 2, 2, 2, 2>}> : (!nn.memory<[#symbol.expr<2>, #symbol.expr<4>], [#symbol.expr<4>, #symbol.expr<1>], f32, #nn.space<tsm>>, !nn.memory<[#symbol.expr<2>, #symbol.expr<4>], [#symbol.expr<8>, #symbol.expr<1>], f32, #nn.space<global>>, !symbol.int<#symbol.expr<0>>, !symbol.int<#symbol.expr<0>>, !symbol.int<#symbol.expr<2>>, !symbol.int<#symbol.expr<4>>, !symbol.int<#symbol.expr<1>>, !symbol.int<#symbol.expr<1>>) -> ()
    func.return
  }
}
"""


def _through_write_broadcast_reshape_ir() -> str:
    """构造 P2 通过 MemoryEffect 识别 scalar broadcast writer 的正例 IR。

    功能说明:
    - `dma.broadcast(%flat, scalar)` 对 `%flat` 是 WRITE/no-READ。
    - 期望 P2 把 reshape 移到 broadcast 前，并把 writer target 改为 reshape result。

    使用示例:
    - _run_public_ircheck_case(_through_write_broadcast_reshape_ir())
    """

    return """// COMPILE_ARGS: --pass hoist-dma-alias-ops
// CHECK: func.func @through_write_reshape_broadcast
// CHECK: %[[TILE:.*]] = "dma.reshape"(%[[FLAT:.*]], %[[C4:.*]], %[[C4]])
// CHECK: "dma.broadcast"(%[[TILE]], %[[ZERO:.*]]) : (!nn.memory<[#symbol.expr<4>, #symbol.expr<4>], [#symbol.expr<4>, #symbol.expr<1>], f32, #nn.space<tsm>>, f32) -> ()
// CHECK: "kernel.binary_elewise"(%[[TILE]], %[[TILE]], %[[TILE]])

builtin.module {
  func.func @through_write_reshape_broadcast(%flat : !nn.memory<[#symbol.expr<16>], [#symbol.expr<1>], f32, #nn.space<tsm>>) {
    %c4 = symbol.const 4 : !symbol.int<#symbol.expr<4>>
    %zero = arith.constant 0.000000e+00 : f32
    "dma.broadcast"(%flat, %zero) : (!nn.memory<[#symbol.expr<16>], [#symbol.expr<1>], f32, #nn.space<tsm>>, f32) -> ()
    %tile = "dma.reshape"(%flat, %c4, %c4) <{operandSegmentSizes = array<i32: 1, 2>}> : (!nn.memory<[#symbol.expr<16>], [#symbol.expr<1>], f32, #nn.space<tsm>>, !symbol.int<#symbol.expr<4>>, !symbol.int<#symbol.expr<4>>) -> !nn.memory<[#symbol.expr<4>, #symbol.expr<4>], [#symbol.expr<4>, #symbol.expr<1>], f32, #nn.space<tsm>>
    "kernel.binary_elewise"(%tile, %tile, %tile) {kind = "add", space = #nn.space<tsm>} : (!nn.memory<[#symbol.expr<4>, #symbol.expr<4>], [#symbol.expr<4>, #symbol.expr<1>], f32, #nn.space<tsm>>, !nn.memory<[#symbol.expr<4>, #symbol.expr<4>], [#symbol.expr<4>, #symbol.expr<1>], f32, #nn.space<tsm>>, !nn.memory<[#symbol.expr<4>, #symbol.expr<4>], [#symbol.expr<4>, #symbol.expr<1>], f32, #nn.space<tsm>>) -> ()
    func.return
  }
}
"""


def _read_target_broadcast_noop_ir() -> str:
    """构造读取同一 target 的 writer no-op 反例 IR。

    功能说明:
    - `dma.broadcast(%flat, %flat)` 对 `%flat` 同时 READ/WRITE。
    - 期望 P2 不 retarget，P1 也不得把 alias 穿过该 source effect。

    使用示例:
    - _run_public_ircheck_case(_read_target_broadcast_noop_ir())
    """

    return """// COMPILE_ARGS: --pass hoist-dma-alias-ops
// CHECK: func.func @through_write_reshape_read_target_noop
// CHECK: "dma.broadcast"(%[[FLAT:.*]], %[[FLAT]]) : (!nn.memory<[#symbol.expr<16>], [#symbol.expr<1>], f32, #nn.space<tsm>>, !nn.memory<[#symbol.expr<16>], [#symbol.expr<1>], f32, #nn.space<tsm>>) -> ()
// CHECK: %[[TILE:.*]] = "dma.reshape"(%[[FLAT]], %[[C4:.*]], %[[C4]])
// CHECK: "kernel.binary_elewise"(%[[TILE]], %[[TILE]], %[[TILE]])

builtin.module {
  func.func @through_write_reshape_read_target_noop(%flat : !nn.memory<[#symbol.expr<16>], [#symbol.expr<1>], f32, #nn.space<tsm>>) {
    %c4 = symbol.const 4 : !symbol.int<#symbol.expr<4>>
    "dma.broadcast"(%flat, %flat) : (!nn.memory<[#symbol.expr<16>], [#symbol.expr<1>], f32, #nn.space<tsm>>, !nn.memory<[#symbol.expr<16>], [#symbol.expr<1>], f32, #nn.space<tsm>>) -> ()
    %tile = "dma.reshape"(%flat, %c4, %c4) <{operandSegmentSizes = array<i32: 1, 2>}> : (!nn.memory<[#symbol.expr<16>], [#symbol.expr<1>], f32, #nn.space<tsm>>, !symbol.int<#symbol.expr<4>>, !symbol.int<#symbol.expr<4>>) -> !nn.memory<[#symbol.expr<4>, #symbol.expr<4>], [#symbol.expr<4>, #symbol.expr<1>], f32, #nn.space<tsm>>
    "kernel.binary_elewise"(%tile, %tile, %tile) {kind = "add", space = #nn.space<tsm>} : (!nn.memory<[#symbol.expr<4>, #symbol.expr<4>], [#symbol.expr<4>, #symbol.expr<1>], f32, #nn.space<tsm>>, !nn.memory<[#symbol.expr<4>, #symbol.expr<4>], [#symbol.expr<4>, #symbol.expr<1>], f32, #nn.space<tsm>>, !nn.memory<[#symbol.expr<4>, #symbol.expr<4>], [#symbol.expr<4>, #symbol.expr<1>], f32, #nn.space<tsm>>) -> ()
    func.return
  }
}
"""


def _loop_invariant_reinterpret_ir() -> str:
    """构造 P1 loop-invariant `dma.reinterpret` 外提正例 IR。

    功能说明:
    - alias operands 全部定义在 `symbol.for` 外。
    - 期望 alias 从 direct loop body 提到 loop 前。

    使用示例:
    - _run_public_ircheck_case(_loop_invariant_reinterpret_ir())
    """

    return """// COMPILE_ARGS: --pass hoist-dma-alias-ops
// CHECK: func.func @loop_hoist_reinterpret_dynamic
// CHECK: %[[ALIAS:.*]] = "dma.reinterpret"(%[[SRC:.*]], %[[ZERO:.*]], %[[M:.*]], %[[N:.*]], %[[N]], %[[ONE:.*]])
// CHECK: symbol.for %[[IT:.*]] = %[[ZERO]] to %[[N]] step %[[N]]
// CHECK: "kernel.binary_elewise"(%[[ALIAS]], %[[ALIAS]], %[[ALIAS]])

builtin.module {
  func.func @loop_hoist_reinterpret_dynamic(
      %src : !nn.memory<[#symbol.expr<M*N>], [#symbol.expr<1>], f32, #nn.space<tsm>>,
      %m : !symbol.int<#symbol.expr<M>>,
      %n : !symbol.int<#symbol.expr<N>>) {
    %zero = symbol.const 0 : !symbol.int<#symbol.expr<0>>
    %one = symbol.const 1 : !symbol.int<#symbol.expr<1>>
    symbol.for %it = %zero to %n step %n {iter = #symbol.iter<start = #symbol.expr<0>, end = #symbol.expr<N>, step = #symbol.expr<N>>} {
      %alias = "dma.reinterpret"(%src, %zero, %m, %n, %n, %one) <{operandSegmentSizes = array<i32: 1, 1, 2, 2>}> : (!nn.memory<[#symbol.expr<M*N>], [#symbol.expr<1>], f32, #nn.space<tsm>>, !symbol.int<#symbol.expr<0>>, !symbol.int<#symbol.expr<M>>, !symbol.int<#symbol.expr<N>>, !symbol.int<#symbol.expr<N>>, !symbol.int<#symbol.expr<1>>) -> !nn.memory<[#symbol.expr<M>, #symbol.expr<N>], [#symbol.expr<N>, #symbol.expr<1>], f32, #nn.space<tsm>>
      "kernel.binary_elewise"(%alias, %alias, %alias) {kind = "add", space = #nn.space<tsm>} : (!nn.memory<[#symbol.expr<M>, #symbol.expr<N>], [#symbol.expr<N>, #symbol.expr<1>], f32, #nn.space<tsm>>, !nn.memory<[#symbol.expr<M>, #symbol.expr<N>], [#symbol.expr<N>, #symbol.expr<1>], f32, #nn.space<tsm>>, !nn.memory<[#symbol.expr<M>, #symbol.expr<N>], [#symbol.expr<N>, #symbol.expr<1>], f32, #nn.space<tsm>>) -> ()
    }
    func.return
  }
}
"""


def _byte_pool_reinterpret_noop_ir() -> str:
    """构造 byte-pool dtype-changing reinterpret no-op 反例 IR。

    功能说明:
    - P2 不得把 i8 pool writer target 改成 f32 alias。
    - P1 不得把 alias 穿过同一 source 的 writer。

    使用示例:
    - _run_public_ircheck_case(_byte_pool_reinterpret_noop_ir())
    """

    return """// COMPILE_ARGS: --pass hoist-dma-alias-ops
// CHECK: func.func @through_write_reinterpret_byte_pool_noop
// CHECK: "dma.fill"(%[[POOL:.*]], %[[ZERO:.*]]) : (!nn.memory<[#symbol.expr<64>], [#symbol.expr<1>], i8, #nn.space<tsm>>, i8) -> ()
// CHECK: %[[ALIAS:.*]] = "dma.reinterpret"(%[[POOL]], %[[C0:.*]], %[[C16:.*]], %[[C1:.*]])
// CHECK: "kernel.binary_elewise"(%[[ALIAS]], %[[ALIAS]], %[[ALIAS]])

builtin.module {
  func.func @through_write_reinterpret_byte_pool_noop(%pool : !nn.memory<[#symbol.expr<64>], [#symbol.expr<1>], i8, #nn.space<tsm>>) {
    %c0 = symbol.const 0 : !symbol.int<#symbol.expr<0>>
    %c1 = symbol.const 1 : !symbol.int<#symbol.expr<1>>
    %c16 = symbol.const 16 : !symbol.int<#symbol.expr<16>>
    %zero = arith.constant 0 : i8
    "dma.fill"(%pool, %zero) : (!nn.memory<[#symbol.expr<64>], [#symbol.expr<1>], i8, #nn.space<tsm>>, i8) -> ()
    %alias = "dma.reinterpret"(%pool, %c0, %c16, %c1) <{operandSegmentSizes = array<i32: 1, 1, 1, 1>}> : (!nn.memory<[#symbol.expr<64>], [#symbol.expr<1>], i8, #nn.space<tsm>>, !symbol.int<#symbol.expr<0>>, !symbol.int<#symbol.expr<16>>, !symbol.int<#symbol.expr<1>>) -> !nn.memory<[#symbol.expr<16>], [#symbol.expr<1>], f32, #nn.space<tsm>>
    "kernel.binary_elewise"(%alias, %alias, %alias) {kind = "add", space = #nn.space<tsm>} : (!nn.memory<[#symbol.expr<16>], [#symbol.expr<1>], f32, #nn.space<tsm>>, !nn.memory<[#symbol.expr<16>], [#symbol.expr<1>], f32, #nn.space<tsm>>, !nn.memory<[#symbol.expr<16>], [#symbol.expr<1>], f32, #nn.space<tsm>>) -> ()
    func.return
  }
}
"""


def _view_deslice_grouping_deleted_noop_ir() -> str:
    """构造旧 view/deslice grouping 不再执行的 no-op IR。

    功能说明:
    - 旧合同会生成额外 `dma.reshape`。
    - 当前用户口径删除 grouping，期望仅保留原 view/deslice。

    使用示例:
    - actual_ir = _run_public_ircheck_case(_view_deslice_grouping_deleted_noop_ir())
    """

    return """// COMPILE_ARGS: --pass hoist-dma-alias-ops
// CHECK: func.func @view_static_grouping_deleted_noop
// CHECK: %[[VIEW:.*]] = "dma.view"(%[[SRC:.*]], %[[C0:.*]], %[[C0]], %[[C0]], %[[C2:.*]], %[[C3:.*]], %[[C4:.*]], %[[C1:.*]], %[[C1]], %[[C1]])
// CHECK-NOT: "dma.reshape"
// CHECK: "dma.deslice"(%[[DST:.*]], %[[VIEW]], %[[C0]], %[[C0]], %[[C0]], %[[C2]], %[[C3]], %[[C4]], %[[C1]], %[[C1]], %[[C1]])

builtin.module {
  func.func @view_static_grouping_deleted_noop(%src : !nn.memory<[#symbol.expr<2>, #symbol.expr<3>, #symbol.expr<4>], [#symbol.expr<12>, #symbol.expr<4>, #symbol.expr<1>], f32, #nn.space<global>>, %dst : !nn.memory<[#symbol.expr<2>, #symbol.expr<3>, #symbol.expr<4>], [#symbol.expr<12>, #symbol.expr<4>, #symbol.expr<1>], f32, #nn.space<tsm>>) {
    %c0 = symbol.const 0 : !symbol.int<#symbol.expr<0>>
    %c1 = symbol.const 1 : !symbol.int<#symbol.expr<1>>
    %c2 = symbol.const 2 : !symbol.int<#symbol.expr<2>>
    %c3 = symbol.const 3 : !symbol.int<#symbol.expr<3>>
    %c4 = symbol.const 4 : !symbol.int<#symbol.expr<4>>
    %view = "dma.view"(%src, %c0, %c0, %c0, %c2, %c3, %c4, %c1, %c1, %c1) <{operandSegmentSizes = array<i32: 1, 3, 3, 3>}> : (!nn.memory<[#symbol.expr<2>, #symbol.expr<3>, #symbol.expr<4>], [#symbol.expr<12>, #symbol.expr<4>, #symbol.expr<1>], f32, #nn.space<global>>, !symbol.int<#symbol.expr<0>>, !symbol.int<#symbol.expr<0>>, !symbol.int<#symbol.expr<0>>, !symbol.int<#symbol.expr<2>>, !symbol.int<#symbol.expr<3>>, !symbol.int<#symbol.expr<4>>, !symbol.int<#symbol.expr<1>>, !symbol.int<#symbol.expr<1>>, !symbol.int<#symbol.expr<1>>) -> !nn.memory<[#symbol.expr<2>, #symbol.expr<3>, #symbol.expr<4>], [#symbol.expr<12>, #symbol.expr<4>, #symbol.expr<1>], f32, #nn.space<global>>
    "dma.deslice"(%dst, %view, %c0, %c0, %c0, %c2, %c3, %c4, %c1, %c1, %c1) <{operandSegmentSizes = array<i32: 2, 3, 3, 3>}> : (!nn.memory<[#symbol.expr<2>, #symbol.expr<3>, #symbol.expr<4>], [#symbol.expr<12>, #symbol.expr<4>, #symbol.expr<1>], f32, #nn.space<tsm>>, !nn.memory<[#symbol.expr<2>, #symbol.expr<3>, #symbol.expr<4>], [#symbol.expr<12>, #symbol.expr<4>, #symbol.expr<1>], f32, #nn.space<global>>, !symbol.int<#symbol.expr<0>>, !symbol.int<#symbol.expr<0>>, !symbol.int<#symbol.expr<0>>, !symbol.int<#symbol.expr<2>>, !symbol.int<#symbol.expr<3>>, !symbol.int<#symbol.expr<4>>, !symbol.int<#symbol.expr<1>>, !symbol.int<#symbol.expr<1>>, !symbol.int<#symbol.expr<1>>) -> ()
    func.return
  }
}
"""


def broadcast_source_leading_unit_static_ir() -> str:
    """构造 static `[N] -> [1,N]` broadcast source alias 删除正例。

    功能说明:
    - 返回通过公开 `run_ircheck_text(...)` 执行的 inline IR case。

    使用示例:
    - actual_ir = _run_public_ircheck_case(broadcast_source_leading_unit_static_ir())
    """

    return """// COMPILE_ARGS: --pass hoist-dma-alias-ops
// CHECK: func.func @broadcast_reinterpret_leading_unit_static
// CHECK: %[[FLAT:.*]] = "dma.alloc"()
// CHECK-NOT: "dma.reinterpret"
// CHECK: "dma.fill"(%[[FLAT]], %[[ZERO:.*]])
// CHECK: "dma.broadcast"(%[[DST:.*]], %[[FLAT]])

builtin.module {
  func.func @broadcast_reinterpret_leading_unit_static() {
    %c0 = symbol.const 0 : !symbol.int<#symbol.expr<0>>
    %c1 = symbol.const 1 : !symbol.int<#symbol.expr<1>>
    %c56 = symbol.const 56 : !symbol.int<#symbol.expr<56>>
    %zero = arith.constant 0.000000e+00 : f32
    %flat = "dma.alloc"() <{operandSegmentSizes = array<i32: 0>}> : () -> !nn.memory<[#symbol.expr<56>], [#symbol.expr<1>], f32, #nn.space<tsm>>
    %alias = "dma.reinterpret"(%flat, %c0, %c1, %c56, %c56, %c1) <{operandSegmentSizes = array<i32: 1, 1, 2, 2>}> : (!nn.memory<[#symbol.expr<56>], [#symbol.expr<1>], f32, #nn.space<tsm>>, !symbol.int<#symbol.expr<0>>, !symbol.int<#symbol.expr<1>>, !symbol.int<#symbol.expr<56>>, !symbol.int<#symbol.expr<56>>, !symbol.int<#symbol.expr<1>>) -> !nn.memory<[#symbol.expr<1>, #symbol.expr<56>], [#symbol.expr<56>, #symbol.expr<1>], f32, #nn.space<tsm>>
    "dma.fill"(%alias, %zero) : (!nn.memory<[#symbol.expr<1>, #symbol.expr<56>], [#symbol.expr<56>, #symbol.expr<1>], f32, #nn.space<tsm>>, f32) -> ()
    %dst = "dma.alloc"() <{operandSegmentSizes = array<i32: 0>}> : () -> !nn.memory<[#symbol.expr<72>, #symbol.expr<56>], [#symbol.expr<56>, #symbol.expr<1>], f32, #nn.space<tsm>>
    "dma.broadcast"(%dst, %alias) : (!nn.memory<[#symbol.expr<72>, #symbol.expr<56>], [#symbol.expr<56>, #symbol.expr<1>], f32, #nn.space<tsm>>, !nn.memory<[#symbol.expr<1>, #symbol.expr<56>], [#symbol.expr<56>, #symbol.expr<1>], f32, #nn.space<tsm>>) -> ()
    func.return
  }
}
"""


def broadcast_source_leading_unit_dynamic_ir() -> str:
    """构造 dynamic `[N] -> [1,N]` broadcast source alias 删除正例。

    功能说明:
    - 返回通过公开 `run_ircheck_text(...)` 执行的 inline IR case。

    使用示例:
    - actual_ir = _run_public_ircheck_case(broadcast_source_leading_unit_dynamic_ir())
    """

    return """// COMPILE_ARGS: --pass hoist-dma-alias-ops
// CHECK: func.func @broadcast_reinterpret_leading_unit_dynamic
// CHECK: %[[FLAT:.*]] = "dma.alloc"(%[[N:.*]])
// CHECK-NOT: "dma.reinterpret"
// CHECK: "dma.fill"(%[[FLAT]], %[[ZERO:.*]])
// CHECK: "dma.broadcast"(%[[DST:.*]], %[[FLAT]])

builtin.module {
  func.func @broadcast_reinterpret_leading_unit_dynamic(%m : !symbol.int<#symbol.expr<M>>, %n : !symbol.int<#symbol.expr<N>>) {
    %c0 = symbol.const 0 : !symbol.int<#symbol.expr<0>>
    %c1 = symbol.const 1 : !symbol.int<#symbol.expr<1>>
    %zero = arith.constant 0.000000e+00 : f32
    %flat = "dma.alloc"(%n) <{operandSegmentSizes = array<i32: 1>}> : (!symbol.int<#symbol.expr<N>>) -> !nn.memory<[#symbol.expr<N>], [#symbol.expr<1>], f32, #nn.space<tsm>>
    %alias = "dma.reinterpret"(%flat, %c0, %c1, %n, %n, %c1) <{operandSegmentSizes = array<i32: 1, 1, 2, 2>}> : (!nn.memory<[#symbol.expr<N>], [#symbol.expr<1>], f32, #nn.space<tsm>>, !symbol.int<#symbol.expr<0>>, !symbol.int<#symbol.expr<1>>, !symbol.int<#symbol.expr<N>>, !symbol.int<#symbol.expr<N>>, !symbol.int<#symbol.expr<1>>) -> !nn.memory<[#symbol.expr<1>, #symbol.expr<N>], [#symbol.expr<N>, #symbol.expr<1>], f32, #nn.space<tsm>>
    "dma.fill"(%alias, %zero) : (!nn.memory<[#symbol.expr<1>, #symbol.expr<N>], [#symbol.expr<N>, #symbol.expr<1>], f32, #nn.space<tsm>>, f32) -> ()
    %dst = "dma.alloc"() <{operandSegmentSizes = array<i32: 0>}> : () -> !nn.memory<[#symbol.expr<M>, #symbol.expr<N>], [#symbol.expr<N>, #symbol.expr<1>], f32, #nn.space<tsm>>
    "dma.broadcast"(%dst, %alias) : (!nn.memory<[#symbol.expr<M>, #symbol.expr<N>], [#symbol.expr<N>, #symbol.expr<1>], f32, #nn.space<tsm>>, !nn.memory<[#symbol.expr<1>, #symbol.expr<N>], [#symbol.expr<N>, #symbol.expr<1>], f32, #nn.space<tsm>>) -> ()
    func.return
  }
}
"""


def broadcast_source_non_leading_unit_noop_ir() -> str:
    """构造 `[56] -> [2,28]` 非 leading-unit no-op 反例。

    功能说明:
    - 返回通过公开 `run_ircheck_text(...)` 执行的 inline IR case。

    使用示例:
    - actual_ir = _run_public_ircheck_case(broadcast_source_non_leading_unit_noop_ir())
    """

    return """// COMPILE_ARGS: --pass hoist-dma-alias-ops
// CHECK: func.func @broadcast_reinterpret_non_leading_unit_noop
// CHECK: %[[ALIAS:.*]] = "dma.reinterpret"(%[[FLAT:.*]], %[[C0:.*]], %[[C2:.*]], %[[C28:.*]], %[[C28]], %[[C1:.*]])
// CHECK: "dma.broadcast"(%[[DST:.*]], %[[ALIAS]])

builtin.module {
  func.func @broadcast_reinterpret_non_leading_unit_noop() {
    %c0 = symbol.const 0 : !symbol.int<#symbol.expr<0>>
    %c1 = symbol.const 1 : !symbol.int<#symbol.expr<1>>
    %c2 = symbol.const 2 : !symbol.int<#symbol.expr<2>>
    %c28 = symbol.const 28 : !symbol.int<#symbol.expr<28>>
    %zero = arith.constant 0.000000e+00 : f32
    %flat = "dma.alloc"() <{operandSegmentSizes = array<i32: 0>}> : () -> !nn.memory<[#symbol.expr<56>], [#symbol.expr<1>], f32, #nn.space<tsm>>
    %alias = "dma.reinterpret"(%flat, %c0, %c2, %c28, %c28, %c1) <{operandSegmentSizes = array<i32: 1, 1, 2, 2>}> : (!nn.memory<[#symbol.expr<56>], [#symbol.expr<1>], f32, #nn.space<tsm>>, !symbol.int<#symbol.expr<0>>, !symbol.int<#symbol.expr<2>>, !symbol.int<#symbol.expr<28>>, !symbol.int<#symbol.expr<28>>, !symbol.int<#symbol.expr<1>>) -> !nn.memory<[#symbol.expr<2>, #symbol.expr<28>], [#symbol.expr<28>, #symbol.expr<1>], f32, #nn.space<tsm>>
    "dma.fill"(%alias, %zero) : (!nn.memory<[#symbol.expr<2>, #symbol.expr<28>], [#symbol.expr<28>, #symbol.expr<1>], f32, #nn.space<tsm>>, f32) -> ()
    %dst = "dma.alloc"() <{operandSegmentSizes = array<i32: 0>}> : () -> !nn.memory<[#symbol.expr<72>, #symbol.expr<28>], [#symbol.expr<28>, #symbol.expr<1>], f32, #nn.space<tsm>>
    "dma.broadcast"(%dst, %alias) : (!nn.memory<[#symbol.expr<72>, #symbol.expr<28>], [#symbol.expr<28>, #symbol.expr<1>], f32, #nn.space<tsm>>, !nn.memory<[#symbol.expr<2>, #symbol.expr<28>], [#symbol.expr<28>, #symbol.expr<1>], f32, #nn.space<tsm>>) -> ()
    func.return
  }
}
"""


def broadcast_source_rank0_source_noop_ir() -> str:
    """构造 rank0 source reinterpret with use 的 no-op 反例。

    功能说明:
    - rank0 source 不是 `[N] -> [1,N]` broadcast source 化简候选。
    - alias result 仍被 `dma.fill` 使用时，pass 必须安全 no-op 而不是访问缺失维度崩溃。

    使用示例:
    - actual_ir = _run_public_ircheck_case(broadcast_source_rank0_source_noop_ir())
    """

    return """// COMPILE_ARGS: --pass hoist-dma-alias-ops
// CHECK: func.func @broadcast_reinterpret_rank0_source_noop
// CHECK: %[[ALIAS:.*]] = "dma.reinterpret"(%[[SCALAR:.*]], %[[C0:.*]], %[[C1:.*]])
// CHECK: "dma.fill"(%[[ALIAS]], %[[ZERO:.*]])

builtin.module {
  func.func @broadcast_reinterpret_rank0_source_noop() {
    %c0 = symbol.const 0 : !symbol.int<#symbol.expr<0>>
    %c1 = symbol.const 1 : !symbol.int<#symbol.expr<1>>
    %zero = arith.constant 0.000000e+00 : f32
    %scalar = "dma.alloc"() <{operandSegmentSizes = array<i32: 0>}> : () -> !nn.memory<[], [], f32, #nn.space<tsm>>
    %alias = "dma.reinterpret"(%scalar, %c0, %c1, %c1) <{operandSegmentSizes = array<i32: 1, 1, 1, 1>}> : (!nn.memory<[], [], f32, #nn.space<tsm>>, !symbol.int<#symbol.expr<0>>, !symbol.int<#symbol.expr<1>>, !symbol.int<#symbol.expr<1>>) -> !nn.memory<[#symbol.expr<1>], [#symbol.expr<1>], f32, #nn.space<tsm>>
    "dma.fill"(%alias, %zero) : (!nn.memory<[#symbol.expr<1>], [#symbol.expr<1>], f32, #nn.space<tsm>>, f32) -> ()
    func.return
  }
}
"""


def broadcast_source_retarget_rollback_noop_ir() -> str:
    """构造 writer target retarget 后 verifier 失败的 rollback 反例。

    功能说明:
    - 返回通过公开 `run_ircheck_text(...)` 执行的 inline IR case。

    使用示例:
    - actual_ir = _run_public_ircheck_case(broadcast_source_retarget_rollback_noop_ir())
    """

    return """// COMPILE_ARGS: --pass hoist-dma-alias-ops
// CHECK: func.func @broadcast_reinterpret_retarget_rollback_noop
// CHECK: %[[ALIAS:.*]] = "dma.reinterpret"(%[[FLAT:.*]], %[[C0:.*]], %[[C1:.*]], %[[N:.*]], %[[N]], %[[C1]])
// CHECK: "dma.broadcast"(%[[ALIAS]], %[[SRC:.*]])
// CHECK: "dma.broadcast"(%[[DST:.*]], %[[ALIAS]])

builtin.module {
  func.func @broadcast_reinterpret_retarget_rollback_noop(%n : !symbol.int<#symbol.expr<N>>) {
    %c0 = symbol.const 0 : !symbol.int<#symbol.expr<0>>
    %c1 = symbol.const 1 : !symbol.int<#symbol.expr<1>>
    %c2 = symbol.const 2 : !symbol.int<#symbol.expr<2>>
    %flat = "dma.alloc"(%n) <{operandSegmentSizes = array<i32: 1>}> : (!symbol.int<#symbol.expr<N>>) -> !nn.memory<[#symbol.expr<N>], [#symbol.expr<1>], f32, #nn.space<tsm>>
    %src = "dma.alloc"() <{operandSegmentSizes = array<i32: 0>}> : () -> !nn.memory<[#symbol.expr<2>, #symbol.expr<N>], [#symbol.expr<N>, #symbol.expr<1>], f32, #nn.space<tsm>>
    %alias = "dma.reinterpret"(%flat, %c0, %c1, %n, %n, %c1) <{operandSegmentSizes = array<i32: 1, 1, 2, 2>}> : (!nn.memory<[#symbol.expr<N>], [#symbol.expr<1>], f32, #nn.space<tsm>>, !symbol.int<#symbol.expr<0>>, !symbol.int<#symbol.expr<1>>, !symbol.int<#symbol.expr<N>>, !symbol.int<#symbol.expr<N>>, !symbol.int<#symbol.expr<1>>) -> !nn.memory<[#symbol.expr<1>, #symbol.expr<N>], [#symbol.expr<N>, #symbol.expr<1>], f32, #nn.space<tsm>>
    "dma.broadcast"(%alias, %src) : (!nn.memory<[#symbol.expr<1>, #symbol.expr<N>], [#symbol.expr<N>, #symbol.expr<1>], f32, #nn.space<tsm>>, !nn.memory<[#symbol.expr<2>, #symbol.expr<N>], [#symbol.expr<N>, #symbol.expr<1>], f32, #nn.space<tsm>>) -> ()
    %dst = "dma.alloc"() <{operandSegmentSizes = array<i32: 0>}> : () -> !nn.memory<[#symbol.expr<4>, #symbol.expr<N>], [#symbol.expr<N>, #symbol.expr<1>], f32, #nn.space<tsm>>
    "dma.broadcast"(%dst, %alias) : (!nn.memory<[#symbol.expr<4>, #symbol.expr<N>], [#symbol.expr<N>, #symbol.expr<1>], f32, #nn.space<tsm>>, !nn.memory<[#symbol.expr<1>, #symbol.expr<N>], [#symbol.expr<N>, #symbol.expr<1>], f32, #nn.space<tsm>>) -> ()
    func.return
  }
}
"""


def test_hoist_dma_alias_ops_public_pattern_api_and_getter_order() -> None:
    """验证公开 pattern API 与 getter 顺序。

    功能说明:
    - 锁定公开 API 只保留 P2/P1 两个 pattern。
    - 防止旧 grouping / fill-only pattern 回流。

    使用示例:
    - pytest -q test/passes/test_hoist_dma_alias_ops.py -k public_pattern_api
    """

    exported = set(pass_module.__all__)
    assert exported == {
        "DmaAliasHoistPattern",
        "DmaAliasThroughWriteNoReadPattern",
        "get_hoist_dma_alias_ops_pass_patterns",
        "HoistDmaAliasOpsPass",
    }
    patterns = get_hoist_dma_alias_ops_pass_patterns(ModuleOp([]))
    assert [type(pattern).__name__ for pattern in patterns] == [
        "DmaAliasThroughWriteNoReadPattern",
        "DmaAliasHoistPattern",
    ]
    assert all(isinstance(pattern, RewritePattern) for pattern in patterns)
    assert not hasattr(pass_module, "DmaReshapeThroughFillPattern")
    assert not hasattr(pass_module, "DmaViewDesliceGroupingPattern")


def test_hoist_dma_alias_ops_static_source_uses_public_effects() -> None:
    """验证 P2/P1 静态边界。

    功能说明:
    - P2 class source 必须体现 `get_effects` 与 WRITE/no-READ 判定。
    - P1 class source 不得回退到 fill-only 或 writer target 特判。

    使用示例:
    - pytest -q test/passes/test_hoist_dma_alias_ops.py -k static_source
    """

    through_source = inspect.getsource(DmaAliasThroughWriteNoReadPattern)
    hoist_source = inspect.getsource(DmaAliasHoistPattern)
    for token in ("get_effects", "MemoryEffectKind.WRITE", "MemoryEffectKind.READ", "operands[0]"):
        assert token in through_source
    assert "DmaFillOp" not in through_source
    assert "DmaFillOp" not in hoist_source
    assert "operands[0]" not in hoist_source


def test_hoist_dma_alias_ops_pure_hoists_view_before_unrelated_fill() -> None:
    """验证 P1 纯 alias 外提。

    功能说明:
    - `dma.view` 可穿过不触碰 source 的无关 writer。

    使用示例:
    - pytest -q test/passes/test_hoist_dma_alias_ops.py -k pure_hoists_view
    """

    actual_ir = _run_public_ircheck_case(_pure_hoist_view_static_ir())

    assert actual_ir.index('"dma.view"') < actual_ir.index('"dma.fill"')


def test_hoist_dma_alias_ops_through_write_accepts_broadcast_writer() -> None:
    """验证 P2 不写死 `dma.fill`。

    功能说明:
    - scalar `dma.broadcast` 由公开 MemoryEffect 证明为 WRITE/no-READ writer。

    使用示例:
    - pytest -q test/passes/test_hoist_dma_alias_ops.py -k accepts_broadcast
    """

    _run_public_ircheck_case(_through_write_broadcast_reshape_ir())


def test_hoist_dma_alias_ops_keeps_read_write_target_noop() -> None:
    """验证 READ/WRITE 同 target writer 保持 no-op。

    功能说明:
    - 防止 P2 过宽 retarget。
    - 防止 P1 绕过 P2 把 alias 穿过触碰 source 的 writer。

    使用示例:
    - pytest -q test/passes/test_hoist_dma_alias_ops.py -k read_write_target
    """

    actual_ir = _run_public_ircheck_case(_read_target_broadcast_noop_ir())

    assert actual_ir.index('"dma.broadcast"') < actual_ir.index('"dma.reshape"')


def test_hoist_dma_alias_ops_loop_hoists_reinterpret() -> None:
    """验证 P1 loop-invariant alias 外提。

    功能说明:
    - `dma.reinterpret` operands 全部支配 `symbol.for` 时可提到 loop 前。

    使用示例:
    - pytest -q test/passes/test_hoist_dma_alias_ops.py -k loop_hoists
    """

    actual_ir = _run_public_ircheck_case(_loop_invariant_reinterpret_ir())

    assert actual_ir.index('"dma.reinterpret"') < actual_ir.index("symbol.for")


def test_hoist_dma_alias_ops_keeps_byte_pool_reinterpret_after_fill() -> None:
    """验证 byte-pool dtype-changing reinterpret 保持 no-op。

    功能说明:
    - i8 pool 到 f32 typed memory 不是 P2 full-cover retarget 候选。
    - P1 不跨过触碰 pool source 的 fill。

    使用示例:
    - pytest -q test/passes/test_hoist_dma_alias_ops.py -k byte_pool
    """

    actual_ir = _run_public_ircheck_case(_byte_pool_reinterpret_noop_ir())

    assert actual_ir.index('"dma.fill"') < actual_ir.index('"dma.reinterpret"')


def test_hoist_dma_alias_ops_keeps_view_deslice_grouping_deleted() -> None:
    """验证旧 view/deslice grouping 不再执行。

    功能说明:
    - 用户最新口径删除 grouping pattern。
    - 相同 IR 不应新增 `dma.reshape`。

    使用示例:
    - pytest -q test/passes/test_hoist_dma_alias_ops.py -k grouping_deleted
    """

    actual_ir = _run_public_ircheck_case(_view_deslice_grouping_deleted_noop_ir())

    assert '"dma.reshape"' not in actual_ir


def test_hoist_dma_alias_ops_removes_broadcast_source_leading_unit_reinterpret() -> None:
    """验证 broadcast source leading-unit reinterpret 可删除。

    功能说明:
    - 静态 `[56] -> [1,56]` 与动态 `[N] -> [1,N]` 都必须删除 alias。
    - `dma.fill(alias)` 与 `dma.broadcast(dst, alias)` 都改回 flat source。

    使用示例:
    - pytest -q test/passes/test_hoist_dma_alias_ops.py -k leading_unit
    """

    for case_text in (broadcast_source_leading_unit_static_ir(), broadcast_source_leading_unit_dynamic_ir()):
        actual_ir = _run_public_ircheck_case(case_text)
        assert '"dma.reinterpret"' not in actual_ir
        assert '"dma.fill"(%flat' in actual_ir
        assert '"dma.broadcast"(%dst, %flat)' in actual_ir


def test_hoist_dma_alias_ops_keeps_non_leading_unit_broadcast_source_alias() -> None:
    """验证非 leading-unit rank change 不会被误删。

    功能说明:
    - `[56] -> [2,28]` 不满足 leading-unit broadcast source 合同。
    - 该反例必须保留 reinterpret 和 broadcast source alias。

    使用示例:
    - pytest -q test/passes/test_hoist_dma_alias_ops.py -k non_leading_unit
    """

    actual_ir = _run_public_ircheck_case(broadcast_source_non_leading_unit_noop_ir())

    assert '"dma.reinterpret"' in actual_ir
    assert '"dma.broadcast"(%dst, %alias)' in actual_ir


def test_hoist_dma_alias_ops_keeps_rank0_reinterpret_source_noop() -> None:
    """验证 rank0 source reinterpret with use 安全 no-op。

    功能说明:
    - rank0 source 没有 `source_shape[0]`，不能进入 leading-unit `[N] -> [1,N]` 化简。
    - pass 应保留 alias 与 use，不得抛 `tuple index out of range`。

    使用示例:
    - pytest -q test/passes/test_hoist_dma_alias_ops.py -k rank0_reinterpret
    """

    actual_ir = _run_public_ircheck_case(broadcast_source_rank0_source_noop_ir())

    assert '"dma.reinterpret"' in actual_ir
    assert '"dma.fill"(%alias' in actual_ir


def test_hoist_dma_alias_ops_rolls_back_broadcast_source_retarget_verifier_failure() -> None:
    """验证 retarget 后 verifier 失败时完整 rollback。

    功能说明:
    - writer target retarget 后 verifier 不接受时，必须完整恢复 alias 与所有 use。

    使用示例:
    - pytest -q test/passes/test_hoist_dma_alias_ops.py -k retarget_verifier
    """

    actual_ir = _run_public_ircheck_case(broadcast_source_retarget_rollback_noop_ir())

    assert '"dma.reinterpret"' in actual_ir
    assert '"dma.broadcast"(%alias, %src)' in actual_ir
    assert '"dma.broadcast"(%dst, %alias)' in actual_ir


def test_hoist_dma_alias_ops_registry_builds_public_pass() -> None:
    """验证 registry 构造公开 pass。

    功能说明:
    - `hoist-dma-alias-ops` 支持默认构造与通用 `fold=false`。

    使用示例:
    - pytest -q test/passes/test_hoist_dma_alias_ops.py -k registry_builds
    """

    load_builtin_passes()

    default_pass = build_registered_pass("hoist-dma-alias-ops")
    no_fold_pass = build_registered_pass("hoist-dma-alias-ops", {"fold": "false"})

    assert isinstance(default_pass, HoistDmaAliasOpsPass)
    assert default_pass.fold is True
    assert isinstance(no_fold_pass, HoistDmaAliasOpsPass)
    assert no_fold_pass.fold is False


def test_hoist_dma_alias_ops_registry_rejects_private_options() -> None:
    """验证 registry 不接受专属 option。

    功能说明:
    - 第一阶段不提供 `hoist-ops` / `hoist_ops` 等专属 option。

    使用示例:
    - pytest -q test/passes/test_hoist_dma_alias_ops.py -k registry_rejects
    """

    load_builtin_passes()

    for option_name in ("hoist-ops", "hoist_ops"):
        try:
            build_registered_pass("hoist-dma-alias-ops", {option_name: "dma.fill"})
        except KernelCodeError as exc:
            assert "does not accept options" in str(exc)
        else:
            raise AssertionError(f"{option_name} must be rejected")


def test_hoist_dma_alias_ops_apply_accepts_empty_module() -> None:
    """验证公开 pass entry 可处理空 module。

    功能说明:
    - 最小 smoke 测试 `HoistDmaAliasOpsPass.apply(...)` 入口。

    使用示例:
    - pytest -q test/passes/test_hoist_dma_alias_ops.py -k empty_module
    """

    module = ModuleOp([])

    HoistDmaAliasOpsPass().apply(Context(), module)

    assert isinstance(module, ModuleOp)
