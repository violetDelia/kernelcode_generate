"""loop-soft-pipeline pass tests.


功能说明:
- 覆盖 `LoopSoftPipelinePass` 的公开 API、ring-backed matmul soft-pipeline 改写和 no-op 边界。
- 通过公开 pass API 与 IR parser 验证行为，不读取 expectation 资产。

当前覆盖率信息:
- 当前覆盖率: 未统计（本任务验证未启用 coverage 统计）。
- 达标判定: 待后续补充统计结果。

覆盖率命令:
- `pytest -q --cov=kernel_gen.passes.schedule.loop_soft_pipeline --cov-branch --cov-report=term-missing test/passes/schedule/test_loop_soft_pipeline.py`

使用示例:
- pytest -q test/passes/schedule/test_loop_soft_pipeline.py

关联文件:
- 功能实现: kernel_gen/passes/schedule/loop_soft_pipeline.py
- Spec 文档: spec/pass/loop_soft_pipeline.md
- 测试文件: test/passes/schedule/test_loop_soft_pipeline.py
"""

from __future__ import annotations

import pytest
from xdsl.context import Context
from xdsl.parser import Parser

from kernel_gen.core.context import build_default_context
from kernel_gen.core.error import KernelCodeError
from kernel_gen.passes.schedule.loop_soft_pipeline import LoopSoftPipelinePass


def _run_loop_soft_pipeline(module_text: str) -> str:
    """运行 loop-soft-pipeline 并返回 IR 文本。

    功能说明:
    - 使用公开 `LoopSoftPipelinePass.apply(...)` 入口。
    - 返回 `str(module)`，用于验证 op 数量和结构顺序。

    使用示例:
    - actual = _run_loop_soft_pipeline(ir)
    """

    context = build_default_context()
    module = Parser(context, module_text).parse_module()
    pass_obj = LoopSoftPipelinePass(fold=False)
    pass_obj.apply(Context(), module)
    actual = str(module)
    return actual


def _ring_preload_ir(
    *,
    old_attrs: bool = False,
    unsupported: bool = False,
    zero_trip: bool = False,
    single_trip: bool = False,
    dynamic_end: bool = False,
    staged_source: bool = False,
) -> str:
    """构造 loop 内 copy 后 matmul 的 ring staging 输入。

    功能说明:
    - 默认输入有 A/B 两条 TLM ring，loop 内先 copy current，再 matmul current。
    - `unsupported=True` 将 RHS 改为非 ring memory，验证 pass 保持 no-op。
    - `zero_trip=True` 将 loop end 改为 start，验证静态 zero-trip 保持原状。
    - `single_trip=True` 将静态 loop 改为一个正 tile，验证退化为 prologue/epilogue。
    - `dynamic_end=True` 使用符号 end，验证无法静态证明正 trip 时保持 no-op。
    - `staged_source=True` 让 copy source 先由 `dma.deslice` side effect 写入 staging ring。

    使用示例:
    - text = _ring_preload_ir(old_attrs=True)
    """

    copy_attrs = " {productor = [90], consumer = [91]}" if old_attrs else ""
    source_ring_setup = "" if not staged_source else """
    %tsm_a_pool = "dma.alloc"() <{operandSegmentSizes = array<i32: 0>}> : () -> !nn.memory<[#C128], [#C1], i8, #nn.space<tsm>>
    %tsm_b_pool = "dma.alloc"() <{operandSegmentSizes = array<i32: 0>}> : () -> !nn.memory<[#C128], [#C1], i8, #nn.space<tsm>>
    %tsm_a_ring = "dma.make_ring"(%tsm_a_pool, %c2, %c64) : (!nn.memory<[#C128], [#C1], i8, #nn.space<tsm>>, !symbol.int<#C2>, !symbol.int<#C64>) -> !dma.ring<!nn.memory<[#C4, #C4], [#C4, #C1], f32, #nn.space<tsm>>>
    %tsm_b_ring = "dma.make_ring"(%tsm_b_pool, %c2, %c64) : (!nn.memory<[#C128], [#C1], i8, #nn.space<tsm>>, !symbol.int<#C2>, !symbol.int<#C64>) -> !dma.ring<!nn.memory<[#C4, #C4], [#C4, #C1], f32, #nn.space<tsm>>>"""
    source_a_setup = "" if not staged_source else """
      %tsm_a_slot = "dma.current_ring"(%tsm_a_ring) : (!dma.ring<!nn.memory<[#C4, #C4], [#C4, #C1], f32, #nn.space<tsm>>>) -> !nn.memory<[#C4, #C4], [#C4, #C1], f32, #nn.space<tsm>>
      %tsm_a = "dma.reinterpret"(%tsm_a_slot, %c0, %c4, %c4, %c4, %c1) <{operandSegmentSizes = array<i32: 1, 1, 2, 2>}> : (!nn.memory<[#C4, #C4], [#C4, #C1], f32, #nn.space<tsm>>, !symbol.int<#C0>, !symbol.int<#C4>, !symbol.int<#C4>, !symbol.int<#C4>, !symbol.int<#C1>) -> !nn.memory<[#C4, #C4], [#C4, #C1], f32, #nn.space<tsm>>
      "dma.deslice"(%tsm_a, %src_a, %c0, %c0, %c4, %c4, %c1, %c1) <{operandSegmentSizes = array<i32: 1, 1, 2, 2, 2>}> : (!nn.memory<[#C4, #C4], [#C4, #C1], f32, #nn.space<tsm>>, !nn.memory<[#C4, #C4], [#C4, #C1], f32, #nn.space<tsm>>, !symbol.int<#C0>, !symbol.int<#C0>, !symbol.int<#C4>, !symbol.int<#C4>, !symbol.int<#C1>, !symbol.int<#C1>) -> ()"""
    source_b_setup = "" if not staged_source else """
      %tsm_b_slot = "dma.current_ring"(%tsm_b_ring) : (!dma.ring<!nn.memory<[#C4, #C4], [#C4, #C1], f32, #nn.space<tsm>>>) -> !nn.memory<[#C4, #C4], [#C4, #C1], f32, #nn.space<tsm>>
      %tsm_b = "dma.reinterpret"(%tsm_b_slot, %c0, %c4, %c4, %c4, %c1) <{operandSegmentSizes = array<i32: 1, 1, 2, 2>}> : (!nn.memory<[#C4, #C4], [#C4, #C1], f32, #nn.space<tsm>>, !symbol.int<#C0>, !symbol.int<#C4>, !symbol.int<#C4>, !symbol.int<#C4>, !symbol.int<#C1>) -> !nn.memory<[#C4, #C4], [#C4, #C1], f32, #nn.space<tsm>>
      "dma.deslice"(%tsm_b, %src_b, %c0, %c0, %c4, %c4, %c1, %c1) <{operandSegmentSizes = array<i32: 1, 1, 2, 2, 2>}> : (!nn.memory<[#C4, #C4], [#C4, #C1], f32, #nn.space<tsm>>, !nn.memory<[#C4, #C4], [#C4, #C1], f32, #nn.space<tsm>>, !symbol.int<#C0>, !symbol.int<#C0>, !symbol.int<#C4>, !symbol.int<#C4>, !symbol.int<#C1>, !symbol.int<#C1>) -> ()"""
    copy_a_source = "%tsm_a" if staged_source else "%src_a"
    copy_b_source = "%tsm_b" if staged_source else "%src_b"
    source_advances = "" if not staged_source else """
      "dma.advance_ring"(%tsm_a_ring) : (!dma.ring<!nn.memory<[#C4, #C4], [#C4, #C1], f32, #nn.space<tsm>>>) -> !nn.memory<[#C4, #C4], [#C4, #C1], f32, #nn.space<tsm>>
      "dma.advance_ring"(%tsm_b_ring) : (!dma.ring<!nn.memory<[#C4, #C4], [#C4, #C1], f32, #nn.space<tsm>>>) -> !nn.memory<[#C4, #C4], [#C4, #C1], f32, #nn.space<tsm>>"""
    rhs_setup = "" if unsupported else f"""{source_b_setup}
      %tlm_b_slot = "dma.current_ring"(%tlm_b_ring) : (!dma.ring<!nn.memory<[#C4, #C4], [#C4, #C1], f32, #nn.space<tlm2>>>) -> !nn.memory<[#C4, #C4], [#C4, #C1], f32, #nn.space<tlm2>>
      %tlm_b = "dma.reinterpret"(%tlm_b_slot, %c0, %c4, %c4, %c4, %c1) <{{operandSegmentSizes = array<i32: 1, 1, 2, 2>}}> : (!nn.memory<[#C4, #C4], [#C4, #C1], f32, #nn.space<tlm2>>, !symbol.int<#C0>, !symbol.int<#C4>, !symbol.int<#C4>, !symbol.int<#C4>, !symbol.int<#C1>) -> !nn.memory<[#C4, #C4], [#C4, #C1], f32, #nn.space<tlm2>>
      "dma.copy"(%tlm_b, {copy_b_source}) : (!nn.memory<[#C4, #C4], [#C4, #C1], f32, #nn.space<tlm2>>, !nn.memory<[#C4, #C4], [#C4, #C1], f32, #nn.space<tsm>>) -> ()"""
    matmul_rhs = "%src_b" if unsupported else "%tlm_b"
    matmul_rhs_type = "#nn.space<tsm>" if unsupported else "#nn.space<tlm2>"
    dynamic_end_arg = "%k_end : !symbol.int<#symbol.expr<K>>, " if dynamic_end else ""
    if dynamic_end:
        loop_end_ref = "%k_end"
        iter_attr = "#symbol.iter<start = #C0, end = #symbol.expr<K>, step = #C4>"
        iter_type = "!symbol.iter<start = #C0, end = #symbol.expr<K>, step = #C4>"
    elif zero_trip:
        loop_end_ref = "%c0"
        iter_attr = "#symbol.iter<start = #C0, end = #C0, step = #C4>"
        iter_type = "!symbol.iter<start = #C0, end = #C0, step = #C4>"
    elif single_trip:
        loop_end_ref = "%c4"
        iter_attr = "#symbol.iter<start = #C0, end = #C4, step = #C4>"
        iter_type = "!symbol.iter<start = #C0, end = #C4, step = #C4>"
    else:
        loop_end_ref = "%c8"
        iter_attr = "#ItK"
        iter_type = "!symbol.iter<start = #C0, end = #C8, step = #C4>"
    return f"""#C0 = #symbol.expr<0>
#C1 = #symbol.expr<1>
#C2 = #symbol.expr<2>
#C4 = #symbol.expr<4>
#C8 = #symbol.expr<8>
#C64 = #symbol.expr<64>
#C128 = #symbol.expr<128>
#ItK = #symbol.iter<start = #C0, end = #C8, step = #C4>

builtin.module {{
  func.func @matmul_dynamic_ring_pipeline({dynamic_end_arg}%src_a : !nn.memory<[#C4, #C4], [#C4, #C1], f32, #nn.space<tsm>>, %src_b : !nn.memory<[#C4, #C4], [#C4, #C1], f32, #nn.space<tsm>>, %acc : !nn.memory<[#C4, #C4], [#C4, #C1], f32, #nn.space<tsm>>) {{
    %c0 = symbol.const 0 : !symbol.int<#C0>
    %c1 = symbol.const 1 : !symbol.int<#C1>
    %c2 = symbol.const 2 : !symbol.int<#C2>
    %c4 = symbol.const 4 : !symbol.int<#C4>
    %c8 = symbol.const 8 : !symbol.int<#C8>
    %c64 = symbol.const 64 : !symbol.int<#C64>
    %tlm_a_pool = "dma.alloc"() <{{operandSegmentSizes = array<i32: 0>}}> : () -> !nn.memory<[#C128], [#C1], i8, #nn.space<tlm1>>
    %tlm_b_pool = "dma.alloc"() <{{operandSegmentSizes = array<i32: 0>}}> : () -> !nn.memory<[#C128], [#C1], i8, #nn.space<tlm2>>
    %tlm_a_ring = "dma.make_ring"(%tlm_a_pool, %c2, %c64) : (!nn.memory<[#C128], [#C1], i8, #nn.space<tlm1>>, !symbol.int<#C2>, !symbol.int<#C64>) -> !dma.ring<!nn.memory<[#C4, #C4], [#C4, #C1], f32, #nn.space<tlm1>>>
    %tlm_b_ring = "dma.make_ring"(%tlm_b_pool, %c2, %c64) : (!nn.memory<[#C128], [#C1], i8, #nn.space<tlm2>>, !symbol.int<#C2>, !symbol.int<#C64>) -> !dma.ring<!nn.memory<[#C4, #C4], [#C4, #C1], f32, #nn.space<tlm2>>>{source_ring_setup}
    symbol.for %k = %c0 to {loop_end_ref} step %c4 {{iter = {iter_attr}}} {{
{source_a_setup}
      %tlm_a_slot = "dma.current_ring"(%tlm_a_ring) : (!dma.ring<!nn.memory<[#C4, #C4], [#C4, #C1], f32, #nn.space<tlm1>>>) -> !nn.memory<[#C4, #C4], [#C4, #C1], f32, #nn.space<tlm1>>
      %tlm_a = "dma.reinterpret"(%tlm_a_slot, %c0, %c4, %c4, %c4, %c1) <{{operandSegmentSizes = array<i32: 1, 1, 2, 2>}}> : (!nn.memory<[#C4, #C4], [#C4, #C1], f32, #nn.space<tlm1>>, !symbol.int<#C0>, !symbol.int<#C4>, !symbol.int<#C4>, !symbol.int<#C4>, !symbol.int<#C1>) -> !nn.memory<[#C4, #C4], [#C4, #C1], f32, #nn.space<tlm1>>
      "dma.copy"(%tlm_a, {copy_a_source}){copy_attrs} : (!nn.memory<[#C4, #C4], [#C4, #C1], f32, #nn.space<tlm1>>, !nn.memory<[#C4, #C4], [#C4, #C1], f32, #nn.space<tsm>>) -> (){rhs_setup}
      %acc_flag = symbol.ne %k, %c0 : {iter_type}, !symbol.int<#C0> -> i1
      "kernel.matmul"(%acc, %tlm_a, {matmul_rhs}, %acc_flag) {{space = #nn.space<tsm>}} : (!nn.memory<[#C4, #C4], [#C4, #C1], f32, #nn.space<tsm>>, !nn.memory<[#C4, #C4], [#C4, #C1], f32, #nn.space<tlm1>>, !nn.memory<[#C4, #C4], [#C4, #C1], f32, {matmul_rhs_type}>, i1) -> ()
      "dma.advance_ring"(%tlm_a_ring) : (!dma.ring<!nn.memory<[#C4, #C4], [#C4, #C1], f32, #nn.space<tlm1>>>) -> !nn.memory<[#C4, #C4], [#C4, #C1], f32, #nn.space<tlm1>>
      "dma.advance_ring"(%tlm_b_ring) : (!dma.ring<!nn.memory<[#C4, #C4], [#C4, #C1], f32, #nn.space<tlm2>>>) -> !nn.memory<[#C4, #C4], [#C4, #C1], f32, #nn.space<tlm2>>{source_advances}
    }}
    func.return
  }}
}}
"""


def test_loop_soft_pipeline_rewrites_ring_preload_to_prologue_steady_epilogue() -> None:
    """验证 A/B ring preload loop 改写为 prologue / steady / epilogue。

    功能说明:
    - 原 loop 内两条 copy 被拆为 loop 前 preload 与 steady body 中 preload next。
    - 原单个 matmul 被拆为 steady body matmul 与 loop 后 epilogue matmul。

    使用示例:
    - pytest -q test/passes/schedule/test_loop_soft_pipeline.py -k rewrites_ring_preload
    """

    actual = _run_loop_soft_pipeline(_ring_preload_ir())

    assert actual.count('"dma.copy"') == 4
    assert actual.count('"kernel.matmul"') == 2
    assert "symbol.sub" in actual
    assert "symbol.add" in actual
    first_copy = actual.find('"dma.copy"')
    second_copy = actual.find('"dma.copy"', first_copy + 1)
    loop_pos = actual.find("symbol.for")
    first_matmul = actual.find('"kernel.matmul"')
    first_advance = actual.find('"dma.advance_ring"')
    third_copy = actual.find('"dma.copy"', second_copy + 1)
    last_matmul = actual.rfind('"kernel.matmul"')
    assert 0 <= first_copy < second_copy < loop_pos < first_matmul < first_advance < third_copy < last_matmul


def test_loop_soft_pipeline_single_tile_degenerates_to_prologue_epilogue() -> None:
    """验证静态单 tile loop 退化为 prologue preload 与 epilogue matmul。

    功能说明:
    - 输入 loop 为 `0..4 step 4`，可证明只有一个正 tile。
    - 输出不得生成 steady loop、boundary 算术或 preload next。

    使用示例:
    - pytest -q test/passes/schedule/test_loop_soft_pipeline.py -k single_tile
    """

    actual = _run_loop_soft_pipeline(_ring_preload_ir(single_trip=True))

    assert actual.count("symbol.for") == 0
    assert actual.count('"dma.copy"') == 2
    assert actual.count('"kernel.matmul"') == 1
    assert '"dma.advance_ring"' not in actual
    assert "symbol.sub" not in actual
    assert "symbol.add" not in actual
    first_copy = actual.find('"dma.copy"')
    second_copy = actual.find('"dma.copy"', first_copy + 1)
    matmul = actual.find('"kernel.matmul"')
    assert 0 <= first_copy < second_copy < matmul


def test_loop_soft_pipeline_clears_stale_producer_consumer_events() -> None:
    """验证结构改写后清理旧 producer/consumer event attrs。

    功能说明:
    - 输入带旧 `productor` / `consumer` 标注。
    - 输出由后续 producer-consumer-analysis 重新分析，因此旧标注不能泄漏。

    使用示例:
    - pytest -q test/passes/schedule/test_loop_soft_pipeline.py -k clears_stale
    """

    actual = _run_loop_soft_pipeline(_ring_preload_ir(old_attrs=True))

    assert "productor" not in actual
    assert "consumer" not in actual


def test_loop_soft_pipeline_clones_preload_source_writes() -> None:
    """验证 preload copy source 的 side-effect writer 一起克隆。

    功能说明:
    - 输入中 `dma.deslice` 通过 side effect 写入 staging source，再由 `dma.copy` 复制到 TLM ring。
    - 改写后 prologue 与 steady preload next 都必须保留对应 deslice，避免复制旧 staging 数据。

    使用示例:
    - pytest -q test/passes/schedule/test_loop_soft_pipeline.py -k source_writes
    """

    actual = _run_loop_soft_pipeline(_ring_preload_ir(staged_source=True))

    assert actual.count('"dma.deslice"') == 4
    assert actual.count('"dma.copy"') == 4
    first_deslice = actual.find('"dma.deslice"')
    first_copy = actual.find('"dma.copy"')
    third_deslice = actual.find('"dma.deslice"', first_copy + 1)
    third_copy = actual.find('"dma.copy"', first_copy + 1)
    assert 0 <= first_deslice < first_copy < third_deslice < third_copy


def test_loop_soft_pipeline_unsupported_and_zero_trip_keep_original_shape() -> None:
    """验证 unsupported 与静态 zero-trip loop 保持 no-op。

    功能说明:
    - RHS 非 ring-backed 时不满足 A/B ring preload 模式。
    - 静态 zero-trip loop 按任务边界保持原状。

    使用示例:
    - pytest -q test/passes/schedule/test_loop_soft_pipeline.py -k unsupported_and_zero_trip
    """

    unsupported_actual = _run_loop_soft_pipeline(_ring_preload_ir(unsupported=True))
    zero_trip_actual = _run_loop_soft_pipeline(_ring_preload_ir(zero_trip=True))

    assert unsupported_actual.count('"dma.copy"') == 1
    assert unsupported_actual.count('"kernel.matmul"') == 1
    assert "symbol.sub" not in unsupported_actual
    assert zero_trip_actual.count('"dma.copy"') == 2
    assert zero_trip_actual.count('"kernel.matmul"') == 1
    assert "symbol.sub" not in zero_trip_actual


def test_loop_soft_pipeline_dynamic_unknown_trip_keeps_original_shape() -> None:
    """验证动态未知 trip 不生成无条件 prologue。

    功能说明:
    - 输入 loop end 为符号 `K`，首版无法静态证明 `N > 0`。
    - pass 必须保持原 loop 形态，避免 K 为 0 时执行原 loop 不会执行的 copy。

    使用示例:
    - pytest -q test/passes/schedule/test_loop_soft_pipeline.py -k dynamic_unknown
    """

    actual = _run_loop_soft_pipeline(_ring_preload_ir(dynamic_end=True))

    assert actual.count("symbol.for") == 1
    assert actual.count('"dma.copy"') == 2
    assert actual.count('"kernel.matmul"') == 1
    assert '"dma.advance_ring"' in actual
    assert "symbol.sub" not in actual
    assert "symbol.add" not in actual


def test_loop_soft_pipeline_from_options_rejects_unknown_options() -> None:
    """验证 pass 专属 option 边界。

    功能说明:
    - 当前阶段 `LoopSoftPipelinePass.from_options(...)` 只接受空 dict。
    - 通用 `fold` 由 registry 层处理，不在该入口兼容。

    使用示例:
    - pytest -q test/passes/schedule/test_loop_soft_pipeline.py -k from_options
    """

    assert LoopSoftPipelinePass.from_options({}).name == "loop-soft-pipeline"
    with pytest.raises(KernelCodeError, match=r"unknown option: mode"):
        LoopSoftPipelinePass.from_options({"mode": "strict"})
