"""tile-analysis public API tests.


功能说明:
- 覆盖 `kernel_gen.passes.tile.analysis` 的公开 pattern/getter/pass 合同。
- 锁定 `tile-analysis` 只为当前 op 补 `tile.analysis` 与 `tile.tile_exprs`，不生成 `symbol.for` 或 `dma.view`。

使用示例:
- pytest -q test/passes/tile/test_analysis.py

关联文件:
- spec: [spec/pass/tile/analysis.md](../../../spec/pass/tile/analysis.md)
- test: [test/passes/tile/test_analysis.py](../../../test/passes/tile/test_analysis.py)
- 功能实现: [kernel_gen/passes/tile/analysis.py](../../../kernel_gen/passes/tile/analysis.py)
"""

from __future__ import annotations

import importlib
import sys
from pathlib import Path

from xdsl.parser import Parser
from xdsl.context import Context
from xdsl.dialects import func
from xdsl.dialects.builtin import ArrayAttr, StringAttr
from xdsl.passes import ModulePass
from xdsl.pattern_rewriter import PatternRewriter

from kernel_gen.core.context import build_default_context

REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

shared_module = importlib.import_module("test.passes.tile.test_shared")
tile_analysis_module = importlib.import_module("kernel_gen.passes.tile.analysis")
registry_module = importlib.import_module("kernel_gen.passes.registry")
package_module = importlib.import_module("kernel_gen.passes")

build_broadcast_module = shared_module.build_broadcast_module
build_elementwise_module = shared_module.build_elementwise_module
build_matmul_module = shared_module.build_matmul_module
collect_ops = shared_module.collect_ops
TileAnalysisPass = tile_analysis_module.TileAnalysisPass
TileAnalysisBinaryPattern = tile_analysis_module.TileAnalysisBinaryPattern
TileAnalysisBroadcastPattern = tile_analysis_module.TileAnalysisBroadcastPattern
TileAnalysisMatmulPattern = tile_analysis_module.TileAnalysisMatmulPattern
get_tile_analysis_pass_patterns = tile_analysis_module.get_tile_analysis_pass_patterns
build_registered_pass = registry_module.build_registered_pass
load_builtin_passes = registry_module.load_builtin_passes


def test_tile_analysis_public_api_surface_is_stable() -> None:
    """锁定 tile-analysis 的公开导出与 getter 顺序。"""

    assert package_module.TileAnalysisBinaryPattern is TileAnalysisBinaryPattern
    assert package_module.TileAnalysisBroadcastPattern is TileAnalysisBroadcastPattern
    assert package_module.TileAnalysisMatmulPattern is TileAnalysisMatmulPattern
    assert package_module.get_tile_analysis_pass_patterns is get_tile_analysis_pass_patterns
    assert [type(pattern) for pattern in get_tile_analysis_pass_patterns()] == [
        TileAnalysisBinaryPattern,
        TileAnalysisBroadcastPattern,
        TileAnalysisMatmulPattern,
    ]


def test_tile_analysis_binary_pattern_adds_only_analysis_attrs() -> None:
    """锁定 BinaryPattern 只补 analysis attrs。"""

    module = build_elementwise_module()
    func_op = next(op for op in module.ops if isinstance(op, func.FuncOp))
    kernel_op = next(op for op in func_op.body.block.ops if op.name == "kernel.binary_elewise")

    TileAnalysisBinaryPattern().match_and_rewrite(kernel_op, PatternRewriter(kernel_op))

    ops = collect_ops(module)
    assert "tile.analysis" in kernel_op.attributes
    assert "tile.tile_exprs" in kernel_op.attributes
    assert not [op for op in ops if op.name == "symbol.for"]
    assert not [op for op in ops if op.name == "dma.view"]


def test_tile_analysis_binary_pattern_marks_existing_tile_shape_inside_symbol_for() -> None:
    """锁定 loop 内已切分 elementwise 会把当前 tile 形状写回 `tile.tile_exprs`。"""

    module = Parser(
        build_default_context(),
        """
builtin.module {
  func.func @tile_binary_nested(
      %out : !nn.memory<[#symbol.expr<16>, #symbol.expr<32>], [#symbol.expr<32>, #symbol.expr<1>], i32, #nn.space<global>>,
      %lhs : !nn.memory<[#symbol.expr<16>, #symbol.expr<32>], [#symbol.expr<32>, #symbol.expr<1>], i32, #nn.space<global>>,
      %rhs : !nn.memory<[#symbol.expr<16>, #symbol.expr<32>], [#symbol.expr<32>, #symbol.expr<1>], i32, #nn.space<global>>) {
    %c0 = symbol.const 0 : !symbol.int<#symbol.expr<0>>
    %c4 = symbol.const 4 : !symbol.int<#symbol.expr<4>>
    %c8 = symbol.const 8 : !symbol.int<#symbol.expr<8>>
    symbol.for %it0 = %c0 to %c4 step %c4 {iter = #symbol.iter<start = #symbol.expr<0>, end = #symbol.expr<4>, step = #symbol.expr<4>>} {
      symbol.for %it1 = %c0 to %c8 step %c8 {iter = #symbol.iter<start = #symbol.expr<0>, end = #symbol.expr<8>, step = #symbol.expr<8>>} {
        %tile_out = "dma.alloc"() <{operandSegmentSizes = array<i32: 0>}> : () -> !nn.memory<[#symbol.expr<4>, #symbol.expr<8>], [#symbol.expr<8>, #symbol.expr<1>], i32, #nn.space<tsm>>
        %tile_lhs = "dma.alloc"() <{operandSegmentSizes = array<i32: 0>}> : () -> !nn.memory<[#symbol.expr<4>, #symbol.expr<8>], [#symbol.expr<8>, #symbol.expr<1>], i32, #nn.space<tsm>>
        %tile_rhs = "dma.alloc"() <{operandSegmentSizes = array<i32: 0>}> : () -> !nn.memory<[#symbol.expr<4>, #symbol.expr<8>], [#symbol.expr<8>, #symbol.expr<1>], i32, #nn.space<tsm>>
        "kernel.binary_elewise"(%tile_out, %tile_lhs, %tile_rhs) {kind = "add", space = #nn.space<tsm>} : (!nn.memory<[#symbol.expr<4>, #symbol.expr<8>], [#symbol.expr<8>, #symbol.expr<1>], i32, #nn.space<tsm>>, !nn.memory<[#symbol.expr<4>, #symbol.expr<8>], [#symbol.expr<8>, #symbol.expr<1>], i32, #nn.space<tsm>>, !nn.memory<[#symbol.expr<4>, #symbol.expr<8>], [#symbol.expr<8>, #symbol.expr<1>], i32, #nn.space<tsm>>) -> ()
      }
    }
    func.return
  }
}
""",
    ).parse_module()

    nested_binary = next(op for op in collect_ops(module) if op.name == "kernel.binary_elewise")
    TileAnalysisBinaryPattern().match_and_rewrite(nested_binary, PatternRewriter(nested_binary))

    assert nested_binary.attributes["tile.tile_exprs"] == ArrayAttr(
        [
            ArrayAttr([StringAttr("4"), StringAttr("8")]),
            ArrayAttr([StringAttr("4"), StringAttr("8")]),
            ArrayAttr([StringAttr("4"), StringAttr("8")]),
        ]
    )


def test_tile_analysis_binary_pattern_marks_only_loop_covered_dim_inside_single_symbol_for() -> None:
    """锁定 rank-2 binary 若只存在一层 loop，则只写回被该 loop step 覆盖的维。"""

    module = Parser(
        build_default_context(),
        """
builtin.module {
  func.func @tile_binary_partial_nested(
      %out : !nn.memory<[#symbol.expr<16>, #symbol.expr<32>], [#symbol.expr<32>, #symbol.expr<1>], i32, #nn.space<global>>,
      %lhs : !nn.memory<[#symbol.expr<16>, #symbol.expr<32>], [#symbol.expr<32>, #symbol.expr<1>], i32, #nn.space<global>>,
      %rhs : !nn.memory<[#symbol.expr<16>, #symbol.expr<32>], [#symbol.expr<32>, #symbol.expr<1>], i32, #nn.space<global>>) {
    %c0 = symbol.const 0 : !symbol.int<#symbol.expr<0>>
    %c16 = symbol.const 16 : !symbol.int<#symbol.expr<16>>
    %c8 = symbol.const 8 : !symbol.int<#symbol.expr<8>>
    symbol.for %it = %c0 to %c16 step %c8 {iter = #symbol.iter<start = #symbol.expr<0>, end = #symbol.expr<16>, step = #symbol.expr<8>>} {
      %tile_out = "dma.alloc"() <{operandSegmentSizes = array<i32: 0>}> : () -> !nn.memory<[#symbol.expr<4>, #symbol.expr<8>], [#symbol.expr<8>, #symbol.expr<1>], i32, #nn.space<tsm>>
      %tile_lhs = "dma.alloc"() <{operandSegmentSizes = array<i32: 0>}> : () -> !nn.memory<[#symbol.expr<4>, #symbol.expr<8>], [#symbol.expr<8>, #symbol.expr<1>], i32, #nn.space<tsm>>
      %tile_rhs = "dma.alloc"() <{operandSegmentSizes = array<i32: 0>}> : () -> !nn.memory<[#symbol.expr<4>, #symbol.expr<8>], [#symbol.expr<8>, #symbol.expr<1>], i32, #nn.space<tsm>>
      "kernel.binary_elewise"(%tile_out, %tile_lhs, %tile_rhs) {kind = "add", space = #nn.space<tsm>} : (!nn.memory<[#symbol.expr<4>, #symbol.expr<8>], [#symbol.expr<8>, #symbol.expr<1>], i32, #nn.space<tsm>>, !nn.memory<[#symbol.expr<4>, #symbol.expr<8>], [#symbol.expr<8>, #symbol.expr<1>], i32, #nn.space<tsm>>, !nn.memory<[#symbol.expr<4>, #symbol.expr<8>], [#symbol.expr<8>, #symbol.expr<1>], i32, #nn.space<tsm>>) -> ()
    }
    func.return
  }
}
""",
    ).parse_module()

    nested_binary = next(op for op in collect_ops(module) if op.name == "kernel.binary_elewise")
    TileAnalysisBinaryPattern().match_and_rewrite(nested_binary, PatternRewriter(nested_binary))

    assert nested_binary.attributes["tile.tile_exprs"] == ArrayAttr(
        [
            ArrayAttr([StringAttr(""), StringAttr("8")]),
            ArrayAttr([StringAttr(""), StringAttr("8")]),
            ArrayAttr([StringAttr(""), StringAttr("8")]),
        ]
    )


def test_tile_analysis_broadcast_pattern_marks_expand_roles() -> None:
    """锁定 BroadcastPattern 的角色矩阵与空 tile 表达式。"""

    module = build_broadcast_module()
    func_op = next(op for op in module.ops if isinstance(op, func.FuncOp))
    broadcast_op = next(op for op in func_op.body.block.ops if op.name == "dma.broadcast")

    TileAnalysisBroadcastPattern().match_and_rewrite(broadcast_op, PatternRewriter(broadcast_op))

    expected_roles = ArrayAttr(
        [
            ArrayAttr([StringAttr("elewise"), StringAttr("elewise")]),
            ArrayAttr([StringAttr("expand"), StringAttr("elewise")]),
        ]
    )
    expected_exprs = ArrayAttr(
        [
            ArrayAttr([StringAttr(""), StringAttr("")]),
            ArrayAttr([StringAttr(""), StringAttr("")]),
        ]
    )

    assert broadcast_op.attributes["tile.analysis"] == expected_roles
    assert broadcast_op.attributes["tile.tile_exprs"] == expected_exprs


def test_tile_analysis_broadcast_pattern_marks_non_expand_tile_shape_inside_symbol_for() -> None:
    """锁定 loop 内 broadcast 会在 target/source 的非 expand 维写回 tile 形状。"""

    module = Parser(
        build_default_context(),
        """
builtin.module {
  func.func @tile_broadcast_nested(
      %target : !nn.memory<[#symbol.expr<16>, #symbol.expr<32>], [#symbol.expr<32>, #symbol.expr<1>], i32, #nn.space<global>>,
      %source : !nn.memory<[#symbol.expr<32>], [#symbol.expr<1>], i32, #nn.space<global>>) {
    %c0 = symbol.const 0 : !symbol.int<#symbol.expr<0>>
    %c32 = symbol.const 32 : !symbol.int<#symbol.expr<32>>
    %c8 = symbol.const 8 : !symbol.int<#symbol.expr<8>>
    symbol.for %it = %c0 to %c32 step %c8 {iter = #symbol.iter<start = #symbol.expr<0>, end = #symbol.expr<32>, step = #symbol.expr<8>>} {
      %tile_target = "dma.alloc"() <{operandSegmentSizes = array<i32: 0>}> : () -> !nn.memory<[#symbol.expr<4>, #symbol.expr<8>], [#symbol.expr<8>, #symbol.expr<1>], i32, #nn.space<tsm>>
      %tile_source = "dma.alloc"() <{operandSegmentSizes = array<i32: 0>}> : () -> !nn.memory<[#symbol.expr<1>, #symbol.expr<8>], [#symbol.expr<8>, #symbol.expr<1>], i32, #nn.space<tsm>>
      "dma.broadcast"(%tile_target, %tile_source) : (!nn.memory<[#symbol.expr<4>, #symbol.expr<8>], [#symbol.expr<8>, #symbol.expr<1>], i32, #nn.space<tsm>>, !nn.memory<[#symbol.expr<1>, #symbol.expr<8>], [#symbol.expr<8>, #symbol.expr<1>], i32, #nn.space<tsm>>) -> ()
    }
    func.return
  }
}
""",
    ).parse_module()

    nested_broadcast = next(op for op in collect_ops(module) if op.name == "dma.broadcast")
    TileAnalysisBroadcastPattern().match_and_rewrite(nested_broadcast, PatternRewriter(nested_broadcast))

    assert nested_broadcast.attributes["tile.tile_exprs"] == ArrayAttr(
        [
            ArrayAttr([StringAttr(""), StringAttr("8")]),
            ArrayAttr([StringAttr(""), StringAttr("8")]),
        ]
    )


def test_tile_analysis_matmul_pattern_marks_reduce_roles() -> None:
    """锁定 MatmulPattern 的角色矩阵与空 tile 表达式。"""

    module = build_matmul_module()
    func_op = next(op for op in module.ops if isinstance(op, func.FuncOp))
    matmul_op = next(op for op in func_op.body.block.ops if op.name == "kernel.matmul")

    TileAnalysisMatmulPattern().match_and_rewrite(matmul_op, PatternRewriter(matmul_op))

    expected_roles = ArrayAttr(
        [
            ArrayAttr([StringAttr("elewise"), StringAttr("reduce")]),
            ArrayAttr([StringAttr("reduce"), StringAttr("elewise")]),
            ArrayAttr([StringAttr("elewise"), StringAttr("elewise")]),
        ]
    )
    expected_exprs = ArrayAttr(
        [
            ArrayAttr([StringAttr(""), StringAttr("")]),
            ArrayAttr([StringAttr(""), StringAttr("")]),
            ArrayAttr([StringAttr(""), StringAttr("")]),
        ]
    )

    assert matmul_op.attributes["tile.analysis"] == expected_roles
    assert matmul_op.attributes["tile.tile_exprs"] == expected_exprs


def test_tile_analysis_matmul_pattern_marks_existing_tile_shape_inside_symbol_for() -> None:
    """锁定 loop 内已切分 matmul 会把当前 tile 形状写回 `tile.tile_exprs`。"""

    module = Parser(
        build_default_context(),
        """
builtin.module {
  func.func @tile_matmul_nested(
      %out : !nn.memory<[#symbol.expr<16>, #symbol.expr<32>], [#symbol.expr<32>, #symbol.expr<1>], i32, #nn.space<global>>,
      %lhs : !nn.memory<[#symbol.expr<16>, #symbol.expr<8>], [#symbol.expr<8>, #symbol.expr<1>], i32, #nn.space<global>>,
      %rhs : !nn.memory<[#symbol.expr<8>, #symbol.expr<32>], [#symbol.expr<32>, #symbol.expr<1>], i32, #nn.space<global>>) {
    %c0 = symbol.const 0 : !symbol.int<#symbol.expr<0>>
    %c4 = symbol.const 4 : !symbol.int<#symbol.expr<4>>
    %c32 = symbol.const 32 : !symbol.int<#symbol.expr<32>>
    symbol.for %it0 = %c0 to %c4 step %c4 {iter = #symbol.iter<start = #symbol.expr<0>, end = #symbol.expr<4>, step = #symbol.expr<4>>} {
      symbol.for %it1 = %c0 to %c32 step %c32 {iter = #symbol.iter<start = #symbol.expr<0>, end = #symbol.expr<32>, step = #symbol.expr<32>>} {
        %tile_out = "dma.alloc"() <{operandSegmentSizes = array<i32: 0>}> : () -> !nn.memory<[#symbol.expr<4>, #symbol.expr<32>], [#symbol.expr<32>, #symbol.expr<1>], i32, #nn.space<tsm>>
        %tile_lhs = "dma.alloc"() <{operandSegmentSizes = array<i32: 0>}> : () -> !nn.memory<[#symbol.expr<4>, #symbol.expr<8>], [#symbol.expr<8>, #symbol.expr<1>], i32, #nn.space<tsm>>
        %tile_rhs = "dma.alloc"() <{operandSegmentSizes = array<i32: 0>}> : () -> !nn.memory<[#symbol.expr<8>, #symbol.expr<32>], [#symbol.expr<32>, #symbol.expr<1>], i32, #nn.space<tsm>>
        "kernel.matmul"(%tile_out, %tile_lhs, %tile_rhs) {space = #nn.space<tsm>} : (!nn.memory<[#symbol.expr<4>, #symbol.expr<32>], [#symbol.expr<32>, #symbol.expr<1>], i32, #nn.space<tsm>>, !nn.memory<[#symbol.expr<4>, #symbol.expr<8>], [#symbol.expr<8>, #symbol.expr<1>], i32, #nn.space<tsm>>, !nn.memory<[#symbol.expr<8>, #symbol.expr<32>], [#symbol.expr<32>, #symbol.expr<1>], i32, #nn.space<tsm>>) -> ()
      }
    }
    func.return
  }
}
""",
    ).parse_module()

    nested_matmul = next(op for op in collect_ops(module) if op.name == "kernel.matmul")
    TileAnalysisMatmulPattern().match_and_rewrite(nested_matmul, PatternRewriter(nested_matmul))

    assert nested_matmul.attributes["tile.analysis"] == ArrayAttr(
        [
            ArrayAttr([StringAttr("elewise"), StringAttr("reduce")]),
            ArrayAttr([StringAttr("reduce"), StringAttr("elewise")]),
            ArrayAttr([StringAttr("elewise"), StringAttr("elewise")]),
        ]
    )
    assert nested_matmul.attributes["tile.tile_exprs"] == ArrayAttr(
        [
            ArrayAttr([StringAttr("4"), StringAttr("")]),
            ArrayAttr([StringAttr(""), StringAttr("32")]),
            ArrayAttr([StringAttr("4"), StringAttr("32")]),
        ]
    )


def test_tile_analysis_matmul_pattern_marks_only_loop_covered_dim_inside_single_symbol_for() -> None:
    """锁定 rank-2 matmul 若只切 N 轴，则 M 维保持空，N 维写当前 loop step。"""

    module = Parser(
        build_default_context(),
        """
builtin.module {
  func.func @tile_matmul_partial_nested(
      %out : !nn.memory<[#symbol.expr<16>, #symbol.expr<32>], [#symbol.expr<32>, #symbol.expr<1>], i32, #nn.space<global>>,
      %lhs : !nn.memory<[#symbol.expr<16>, #symbol.expr<8>], [#symbol.expr<8>, #symbol.expr<1>], i32, #nn.space<global>>,
      %rhs : !nn.memory<[#symbol.expr<8>, #symbol.expr<32>], [#symbol.expr<32>, #symbol.expr<1>], i32, #nn.space<global>>) {
    %c0 = symbol.const 0 : !symbol.int<#symbol.expr<0>>
    %c64 = symbol.const 64 : !symbol.int<#symbol.expr<64>>
    %c32 = symbol.const 32 : !symbol.int<#symbol.expr<32>>
    symbol.for %it = %c0 to %c64 step %c32 {iter = #symbol.iter<start = #symbol.expr<0>, end = #symbol.expr<64>, step = #symbol.expr<32>>} {
      %tile_out = "dma.alloc"() <{operandSegmentSizes = array<i32: 0>}> : () -> !nn.memory<[#symbol.expr<4>, #symbol.expr<32>], [#symbol.expr<32>, #symbol.expr<1>], i32, #nn.space<tsm>>
      %tile_lhs = "dma.alloc"() <{operandSegmentSizes = array<i32: 0>}> : () -> !nn.memory<[#symbol.expr<4>, #symbol.expr<8>], [#symbol.expr<8>, #symbol.expr<1>], i32, #nn.space<tsm>>
      %tile_rhs = "dma.alloc"() <{operandSegmentSizes = array<i32: 0>}> : () -> !nn.memory<[#symbol.expr<8>, #symbol.expr<32>], [#symbol.expr<32>, #symbol.expr<1>], i32, #nn.space<tsm>>
      "kernel.matmul"(%tile_out, %tile_lhs, %tile_rhs) {space = #nn.space<tsm>} : (!nn.memory<[#symbol.expr<4>, #symbol.expr<32>], [#symbol.expr<32>, #symbol.expr<1>], i32, #nn.space<tsm>>, !nn.memory<[#symbol.expr<4>, #symbol.expr<8>], [#symbol.expr<8>, #symbol.expr<1>], i32, #nn.space<tsm>>, !nn.memory<[#symbol.expr<8>, #symbol.expr<32>], [#symbol.expr<32>, #symbol.expr<1>], i32, #nn.space<tsm>>) -> ()
    }
    func.return
  }
}
""",
    ).parse_module()

    nested_matmul = next(op for op in collect_ops(module) if op.name == "kernel.matmul")
    TileAnalysisMatmulPattern().match_and_rewrite(nested_matmul, PatternRewriter(nested_matmul))

    assert nested_matmul.attributes["tile.tile_exprs"] == ArrayAttr(
        [
            ArrayAttr([StringAttr(""), StringAttr("")]),
            ArrayAttr([StringAttr(""), StringAttr("32")]),
            ArrayAttr([StringAttr(""), StringAttr("32")]),
        ]
    )


def test_tile_analysis_matmul_pattern_ignores_reduce_only_loop_inside_symbol_for() -> None:
    """锁定 matmul 若只切 reduce(K) 轴，则 `tile.tile_exprs` 继续保持空。"""

    module = Parser(
        build_default_context(),
        """
builtin.module {
  func.func @tile_matmul_reduce_only_nested(
      %out : !nn.memory<[#symbol.expr<16>, #symbol.expr<32>], [#symbol.expr<32>, #symbol.expr<1>], i32, #nn.space<global>>,
      %lhs : !nn.memory<[#symbol.expr<16>, #symbol.expr<8>], [#symbol.expr<8>, #symbol.expr<1>], i32, #nn.space<global>>,
      %rhs : !nn.memory<[#symbol.expr<8>, #symbol.expr<32>], [#symbol.expr<32>, #symbol.expr<1>], i32, #nn.space<global>>) {
    %c0 = symbol.const 0 : !symbol.int<#symbol.expr<0>>
    %c16 = symbol.const 16 : !symbol.int<#symbol.expr<16>>
    %c8 = symbol.const 8 : !symbol.int<#symbol.expr<8>>
    symbol.for %it = %c0 to %c16 step %c8 {iter = #symbol.iter<start = #symbol.expr<0>, end = #symbol.expr<16>, step = #symbol.expr<8>>} {
      %tile_out = "dma.alloc"() <{operandSegmentSizes = array<i32: 0>}> : () -> !nn.memory<[#symbol.expr<4>, #symbol.expr<32>], [#symbol.expr<32>, #symbol.expr<1>], i32, #nn.space<tsm>>
      %tile_lhs = "dma.alloc"() <{operandSegmentSizes = array<i32: 0>}> : () -> !nn.memory<[#symbol.expr<4>, #symbol.expr<8>], [#symbol.expr<8>, #symbol.expr<1>], i32, #nn.space<tsm>>
      %tile_rhs = "dma.alloc"() <{operandSegmentSizes = array<i32: 0>}> : () -> !nn.memory<[#symbol.expr<8>, #symbol.expr<32>], [#symbol.expr<32>, #symbol.expr<1>], i32, #nn.space<tsm>>
      "kernel.matmul"(%tile_out, %tile_lhs, %tile_rhs) {space = #nn.space<tsm>} : (!nn.memory<[#symbol.expr<4>, #symbol.expr<32>], [#symbol.expr<32>, #symbol.expr<1>], i32, #nn.space<tsm>>, !nn.memory<[#symbol.expr<4>, #symbol.expr<8>], [#symbol.expr<8>, #symbol.expr<1>], i32, #nn.space<tsm>>, !nn.memory<[#symbol.expr<8>, #symbol.expr<32>], [#symbol.expr<32>, #symbol.expr<1>], i32, #nn.space<tsm>>) -> ()
    }
    func.return
  }
}
""",
    ).parse_module()

    nested_matmul = next(op for op in collect_ops(module) if op.name == "kernel.matmul")
    TileAnalysisMatmulPattern().match_and_rewrite(nested_matmul, PatternRewriter(nested_matmul))

    assert nested_matmul.attributes["tile.tile_exprs"] == ArrayAttr(
        [
            ArrayAttr([StringAttr(""), StringAttr("")]),
            ArrayAttr([StringAttr(""), StringAttr("")]),
            ArrayAttr([StringAttr(""), StringAttr("")]),
        ]
    )


def test_tile_analysis_matmul_pattern_ignores_reduce_loop_and_keeps_n_loop_inside_symbol_for() -> None:
    """锁定 matmul 若同时切 reduce(K)+N，则只把 N 写回 `tile.tile_exprs`。"""

    module = Parser(
        build_default_context(),
        """
builtin.module {
  func.func @tile_matmul_reduce_n_nested(
      %out : !nn.memory<[#symbol.expr<16>, #symbol.expr<32>], [#symbol.expr<32>, #symbol.expr<1>], i32, #nn.space<global>>,
      %lhs : !nn.memory<[#symbol.expr<16>, #symbol.expr<8>], [#symbol.expr<8>, #symbol.expr<1>], i32, #nn.space<global>>,
      %rhs : !nn.memory<[#symbol.expr<8>, #symbol.expr<32>], [#symbol.expr<32>, #symbol.expr<1>], i32, #nn.space<global>>) {
    %c0 = symbol.const 0 : !symbol.int<#symbol.expr<0>>
    %c16 = symbol.const 16 : !symbol.int<#symbol.expr<16>>
    %c8 = symbol.const 8 : !symbol.int<#symbol.expr<8>>
    %c64 = symbol.const 64 : !symbol.int<#symbol.expr<64>>
    %c32 = symbol.const 32 : !symbol.int<#symbol.expr<32>>
    symbol.for %itk = %c0 to %c16 step %c8 {iter = #symbol.iter<start = #symbol.expr<0>, end = #symbol.expr<16>, step = #symbol.expr<8>>} {
      symbol.for %itn = %c0 to %c64 step %c32 {iter = #symbol.iter<start = #symbol.expr<0>, end = #symbol.expr<64>, step = #symbol.expr<32>>} {
        %tile_out = "dma.alloc"() <{operandSegmentSizes = array<i32: 0>}> : () -> !nn.memory<[#symbol.expr<4>, #symbol.expr<32>], [#symbol.expr<32>, #symbol.expr<1>], i32, #nn.space<tsm>>
        %tile_lhs = "dma.alloc"() <{operandSegmentSizes = array<i32: 0>}> : () -> !nn.memory<[#symbol.expr<4>, #symbol.expr<8>], [#symbol.expr<8>, #symbol.expr<1>], i32, #nn.space<tsm>>
        %tile_rhs = "dma.alloc"() <{operandSegmentSizes = array<i32: 0>}> : () -> !nn.memory<[#symbol.expr<8>, #symbol.expr<32>], [#symbol.expr<32>, #symbol.expr<1>], i32, #nn.space<tsm>>
        "kernel.matmul"(%tile_out, %tile_lhs, %tile_rhs) {space = #nn.space<tsm>} : (!nn.memory<[#symbol.expr<4>, #symbol.expr<32>], [#symbol.expr<32>, #symbol.expr<1>], i32, #nn.space<tsm>>, !nn.memory<[#symbol.expr<4>, #symbol.expr<8>], [#symbol.expr<8>, #symbol.expr<1>], i32, #nn.space<tsm>>, !nn.memory<[#symbol.expr<8>, #symbol.expr<32>], [#symbol.expr<32>, #symbol.expr<1>], i32, #nn.space<tsm>>) -> ()
      }
    }
    func.return
  }
}
""",
    ).parse_module()

    nested_matmul = next(op for op in collect_ops(module) if op.name == "kernel.matmul")
    TileAnalysisMatmulPattern().match_and_rewrite(nested_matmul, PatternRewriter(nested_matmul))

    assert nested_matmul.attributes["tile.tile_exprs"] == ArrayAttr(
        [
            ArrayAttr([StringAttr(""), StringAttr("")]),
            ArrayAttr([StringAttr(""), StringAttr("32")]),
            ArrayAttr([StringAttr(""), StringAttr("32")]),
        ]
    )


def test_tile_analysis_pass_is_registry_constructible_module_pass() -> None:
    """锁定 TileAnalysisPass 的 pass 合同与无 rewrite 副作用。"""

    module = build_elementwise_module()
    load_builtin_passes()
    pass_obj = build_registered_pass("tile-analysis")

    assert isinstance(pass_obj, ModulePass)
    assert pass_obj.__class__ is TileAnalysisPass
    pass_obj.apply(Context(), module)

    ops = collect_ops(module)
    kernel_op = next(op for op in ops if op.name == "kernel.binary_elewise")
    assert "tile.analysis" in kernel_op.attributes
    assert "tile.tile_exprs" in kernel_op.attributes
    assert not [op for op in ops if op.name == "symbol.for"]
    assert not [op for op in ops if op.name == "dma.view"]
