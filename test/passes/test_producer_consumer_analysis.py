"""producer-consumer-analysis pass tests.


功能说明:
- 覆盖 `ProducerConsumerAnalysisPass` 的 MemoryEffect、alias、control-flow 和错误边界。
- 通过公开 pass API、registry API 与 IR parser 验证行为，不直连跨文件非公开 helper。

当前覆盖率信息:
- 当前覆盖率: 未统计（本任务验证未启用 coverage 统计）。
- 达标判定: 待后续补充统计结果。

覆盖率命令:
- `pytest -q --cov=kernel_gen.passes.producer_consumer_analysis --cov-branch --cov-report=term-missing test/passes/test_producer_consumer_analysis.py`

使用示例:
- pytest -q test/passes/test_producer_consumer_analysis.py

关联文件:
- 功能实现: kernel_gen/passes/producer_consumer_analysis.py
- Spec 文档: spec/pass/producer_consumer_analysis.md
- 测试文件: test/passes/test_producer_consumer_analysis.py
"""

from __future__ import annotations

import re

import pytest
from xdsl.context import Context
from xdsl.parser import Parser

from kernel_gen.core.context import build_default_context
from kernel_gen.core.error import KernelCodeError
from kernel_gen.passes.producer_consumer_analysis import ProducerConsumerAnalysisPass
from kernel_gen.passes.registry import build_registered_pass, load_builtin_passes

_LOCAL_TYPE = (
    "!nn.memory<[#symbol.expr<4>, #symbol.expr<4>], "
    "[#symbol.expr<4>, #symbol.expr<1>], f32, #nn.space<tsm>>"
)
_GLOBAL_TYPE = (
    "!nn.memory<[#symbol.expr<4>, #symbol.expr<4>], "
    "[#symbol.expr<4>, #symbol.expr<1>], f32, #nn.space<global>>"
)


def _run_producer_consumer_analysis(module_text: str) -> str:
    """运行 producer-consumer-analysis 并返回 IR 文本。

    功能说明:
    - 使用公开 `ProducerConsumerAnalysisPass.apply(...)` 入口。
    - 返回 `str(module)`，用于验证裸整数列表 attr 文本。

    使用示例:
    - actual = _run_producer_consumer_analysis(ir)
    """

    module = Parser(build_default_context(), module_text).parse_module()
    ProducerConsumerAnalysisPass(fold=False).apply(Context(), module)
    return str(module)


def _assert_line_matches(actual: str, op_name: str, pattern: str, *, occurrence: int = 1) -> None:
    """断言第 occurrence 条 op 文本匹配正则。

    功能说明:
    - 按行定位目标 op，避免把断言绑定到完整 IR 结构。
    - `pattern` 用于锁定 attr 组合和禁止项。

    使用示例:
    - _assert_line_matches(actual, "dma.copy", r"productor = \\[0\\]")
    """

    matched = [line for line in actual.splitlines() if f'"{op_name}"' in line]
    assert len(matched) >= occurrence, actual
    assert re.search(pattern, matched[occurrence - 1]), matched[occurrence - 1]


def test_producer_consumer_analysis_basic_memory_effect_chain() -> None:
    """验证基础 `dma.copy -> dma.copy` producer/consumer event。

    功能说明:
    - 第一个 `dma.copy` 通过 WRITE 生产 `%a`。
    - 第二个 `dma.copy` 通过 READ 消费 `%a`。

    使用示例:
    - pytest -q test/passes/test_producer_consumer_analysis.py -k basic_memory_effect_chain
    """

    actual = _run_producer_consumer_analysis(
        f"""builtin.module {{
  func.func @basic(%a : {_LOCAL_TYPE}, %gm : {_GLOBAL_TYPE}, %tmp : {_LOCAL_TYPE}) {{
    "dma.copy"(%a, %gm) : ({_LOCAL_TYPE}, {_GLOBAL_TYPE}) -> ()
    "dma.copy"(%tmp, %a) : ({_LOCAL_TYPE}, {_LOCAL_TYPE}) -> ()
    func.return
  }}
}}
"""
    )
    _assert_line_matches(actual, "dma.copy", r"productor = \[0\]", occurrence=1)
    _assert_line_matches(actual, "dma.copy", r"consumer = \[0\](?!.*productor)", occurrence=2)
    assert "#builtin.int" not in actual
    assert ": i64" not in actual
    assert "array<i64" not in actual


def test_producer_consumer_analysis_alias_and_deslice_chain() -> None:
    """验证 alias op 与 `dma.deslice` 复合 read/write 模型。

    功能说明:
    - `dma.view` / `dma.reinterpret` 不生产、不消费，只让 result alias source。
    - `dma.deslice` 消费 source producer，同时生产 target，并让 result alias target。

    使用示例:
    - pytest -q test/passes/test_producer_consumer_analysis.py -k alias_and_deslice
    """

    actual = _run_producer_consumer_analysis(
        f"""builtin.module {{
  func.func @alias_chain(%lhs : {_LOCAL_TYPE}, %gm : {_GLOBAL_TYPE}, %rhs : {_LOCAL_TYPE}, %out : {_LOCAL_TYPE}, %dst : {_GLOBAL_TYPE}, %z : {_GLOBAL_TYPE}) {{
    %c0 = symbol.const 0 : !symbol.int<#symbol.expr<0>>
    %c1 = symbol.const 1 : !symbol.int<#symbol.expr<1>>
    %c4 = symbol.const 4 : !symbol.int<#symbol.expr<4>>
    "dma.copy"(%lhs, %gm) : ({_LOCAL_TYPE}, {_GLOBAL_TYPE}) -> ()
    %lhs_view = "dma.view"(%lhs, %c0, %c0, %c4, %c4, %c1, %c1) <{{operandSegmentSizes = array<i32: 1, 2, 2, 2>}}> : ({_LOCAL_TYPE}, !symbol.int<#symbol.expr<0>>, !symbol.int<#symbol.expr<0>>, !symbol.int<#symbol.expr<4>>, !symbol.int<#symbol.expr<4>>, !symbol.int<#symbol.expr<1>>, !symbol.int<#symbol.expr<1>>) -> {_LOCAL_TYPE}
    %lhs_reinterpret = "dma.reinterpret"(%lhs_view, %c0, %c4, %c4, %c4, %c1) <{{operandSegmentSizes = array<i32: 1, 1, 2, 2>}}> : ({_LOCAL_TYPE}, !symbol.int<#symbol.expr<0>>, !symbol.int<#symbol.expr<4>>, !symbol.int<#symbol.expr<4>>, !symbol.int<#symbol.expr<4>>, !symbol.int<#symbol.expr<1>>) -> {_LOCAL_TYPE}
    "kernel.matmul"(%out, %lhs_reinterpret, %rhs) {{space = #nn.space<tsm>}} : ({_LOCAL_TYPE}, {_LOCAL_TYPE}, {_LOCAL_TYPE}) -> ()
    %dst_after = "dma.deslice"(%dst, %out, %c0, %c0, %c4, %c4, %c1, %c1) <{{operandSegmentSizes = array<i32: 1, 1, 2, 2, 2>}}> : ({_GLOBAL_TYPE}, {_LOCAL_TYPE}, !symbol.int<#symbol.expr<0>>, !symbol.int<#symbol.expr<0>>, !symbol.int<#symbol.expr<4>>, !symbol.int<#symbol.expr<4>>, !symbol.int<#symbol.expr<1>>, !symbol.int<#symbol.expr<1>>) -> {_GLOBAL_TYPE}
    "dma.copy"(%z, %dst_after) : ({_GLOBAL_TYPE}, {_GLOBAL_TYPE}) -> ()
    func.return
  }}
}}
"""
    )
    _assert_line_matches(actual, "dma.copy", r"productor = \[0\]", occurrence=1)
    _assert_line_matches(actual, "dma.view", r'^(?!.*productor)(?!.*consumer).*"dma.view"', occurrence=1)
    _assert_line_matches(actual, "dma.reinterpret", r'^(?!.*productor)(?!.*consumer).*"dma.reinterpret"', occurrence=1)
    _assert_line_matches(actual, "kernel.matmul", r"consumer = \[0\].*productor = \[1\]", occurrence=1)
    _assert_line_matches(actual, "dma.deslice", r"consumer = \[1\].*productor = \[2\]", occurrence=1)
    _assert_line_matches(actual, "dma.copy", r"consumer = \[2\](?!.*productor)", occurrence=2)


def test_producer_consumer_analysis_fanout_alloc_and_duplicate_read() -> None:
    """验证 fanout、alloc producer 与同 op 重复 read 去重。

    功能说明:
    - `dma.alloc` result 是 producer value。
    - 同一 produced memory version 的两个 user 分配两个 event。
    - 同一 consumer op 重复读取同一 memory 只消费一个 event。

    使用示例:
    - pytest -q test/passes/test_producer_consumer_analysis.py -k fanout_alloc
    """

    actual = _run_producer_consumer_analysis(
        f"""builtin.module {{
  func.func @fanout(%gm : {_GLOBAL_TYPE}, %a : {_LOCAL_TYPE}, %out1 : {_LOCAL_TYPE}, %out2 : {_LOCAL_TYPE}) {{
    %alloc = "dma.alloc"() <{{operandSegmentSizes = array<i32: 0>}}> : () -> {_LOCAL_TYPE}
    "dma.copy"(%a, %gm) : ({_LOCAL_TYPE}, {_GLOBAL_TYPE}) -> ()
    "kernel.binary_elewise"(%out1, %a, %a) {{kind = "add", space = #nn.space<tsm>}} : ({_LOCAL_TYPE}, {_LOCAL_TYPE}, {_LOCAL_TYPE}) -> ()
    "dma.copy"(%out2, %a) : ({_LOCAL_TYPE}, {_LOCAL_TYPE}) -> ()
    "dma.copy"(%out1, %alloc) : ({_LOCAL_TYPE}, {_LOCAL_TYPE}) -> ()
    func.return
  }}
}}
"""
    )
    _assert_line_matches(actual, "dma.alloc", r"productor = \[0\]", occurrence=1)
    _assert_line_matches(actual, "dma.copy", r"productor = \[1, 2\]", occurrence=1)
    _assert_line_matches(actual, "kernel.binary_elewise", r"consumer = \[1\](?!.*productor)", occurrence=1)
    _assert_line_matches(actual, "dma.copy", r"consumer = \[2\](?!.*productor)", occurrence=2)
    _assert_line_matches(actual, "dma.copy", r"consumer = \[0\](?!.*productor)", occurrence=3)


def test_producer_consumer_analysis_if_branch_and_after_if_edges() -> None:
    """验证 `scf.if` incoming 与 after-if 分类 attr。

    功能说明:
    - if 前 producer 被 then/else 消费时共享 event。
    - then/else 都生产同一 memory 并被 if 后 consumer 使用时，consumer 记录两个 event。

    使用示例:
    - pytest -q test/passes/test_producer_consumer_analysis.py -k if_branch
    """

    incoming = _run_producer_consumer_analysis(
        f"""builtin.module {{
  func.func @if_incoming(%cond : i1, %a : {_LOCAL_TYPE}, %gm : {_GLOBAL_TYPE}, %b : {_LOCAL_TYPE}, %out : {_LOCAL_TYPE}, %tmp : {_LOCAL_TYPE}) {{
    "dma.copy"(%a, %gm) : ({_LOCAL_TYPE}, {_GLOBAL_TYPE}) -> ()
    scf.if %cond {{
      "kernel.matmul"(%out, %a, %b) {{space = #nn.space<tsm>}} : ({_LOCAL_TYPE}, {_LOCAL_TYPE}, {_LOCAL_TYPE}) -> ()
    }} else {{
      "dma.copy"(%tmp, %a) : ({_LOCAL_TYPE}, {_LOCAL_TYPE}) -> ()
    }}
    func.return
  }}
}}
"""
    )
    _assert_line_matches(
        incoming,
        "dma.copy",
        r"^(?!.*\bproductor\s*=)(?=.*if_branch_productor = \[0\]).*$",
        occurrence=1,
    )
    _assert_line_matches(
        incoming,
        "kernel.matmul",
        r"^(?!.*\bconsumer\s*=)(?=.*if_branch_consumer = \[0\]).*$",
        occurrence=1,
    )
    _assert_line_matches(
        incoming,
        "dma.copy",
        r"^(?!.*\bconsumer\s*=)(?=.*if_branch_consumer = \[0\]).*$",
        occurrence=2,
    )

    after_if = _run_producer_consumer_analysis(
        f"""builtin.module {{
  func.func @if_after(%cond : i1, %a : {_LOCAL_TYPE}, %gm1 : {_GLOBAL_TYPE}, %gm2 : {_GLOBAL_TYPE}, %b : {_LOCAL_TYPE}, %out : {_LOCAL_TYPE}) {{
    scf.if %cond {{
      "dma.copy"(%a, %gm1) : ({_LOCAL_TYPE}, {_GLOBAL_TYPE}) -> ()
    }} else {{
      "dma.copy"(%a, %gm2) : ({_LOCAL_TYPE}, {_GLOBAL_TYPE}) -> ()
    }}
    "kernel.matmul"(%out, %a, %b) {{space = #nn.space<tsm>}} : ({_LOCAL_TYPE}, {_LOCAL_TYPE}, {_LOCAL_TYPE}) -> ()
    func.return
  }}
}}
"""
    )
    _assert_line_matches(
        after_if,
        "dma.copy",
        r"^(?!.*\bproductor\s*=)(?=.*after_if_productor = \[0\]).*$",
        occurrence=1,
    )
    _assert_line_matches(
        after_if,
        "dma.copy",
        r"^(?!.*\bproductor\s*=)(?=.*after_if_productor = \[1\]).*$",
        occurrence=2,
    )
    _assert_line_matches(
        after_if,
        "kernel.matmul",
        r"^(?!.*\bconsumer\s*=)(?=.*after_if_consumer = \[0, 1\]).*$",
        occurrence=1,
    )


def test_producer_consumer_analysis_if_branch_internal_fanout_uses_distinct_events() -> None:
    """验证同一 `scf.if` 分支内部普通 fanout 使用主 event。

    功能说明:
    - 同一分支同一 block 内的普通顺序 edge 不写 `if_branch_*`。
    - 同一分支内部 producer 有多个 downstream consumer 时按同一路径 fanout 分配不同 event。

    使用示例:
    - pytest -q test/passes/test_producer_consumer_analysis.py -k if_branch_internal_fanout
    """

    actual = _run_producer_consumer_analysis(
        f"""builtin.module {{
  func.func @if_branch_internal_fanout(%cond : i1, %a : {_LOCAL_TYPE}, %gm : {_GLOBAL_TYPE}, %tmp1 : {_LOCAL_TYPE}, %tmp2 : {_LOCAL_TYPE}) {{
    scf.if %cond {{
      "dma.copy"(%a, %gm) : ({_LOCAL_TYPE}, {_GLOBAL_TYPE}) -> ()
      "dma.copy"(%tmp1, %a) : ({_LOCAL_TYPE}, {_LOCAL_TYPE}) -> ()
      "dma.copy"(%tmp2, %a) : ({_LOCAL_TYPE}, {_LOCAL_TYPE}) -> ()
    }} else {{
    }}
    func.return
  }}
}}
"""
    )
    _assert_line_matches(
        actual,
        "dma.copy",
        r"^(?!.*if_branch_productor)(?=.*\bproductor\s*= \[0, 1\]).*$",
        occurrence=1,
    )
    _assert_line_matches(
        actual,
        "dma.copy",
        r"^(?!.*if_branch_consumer)(?=.*\bconsumer\s*= \[0\]).*$",
        occurrence=2,
    )
    _assert_line_matches(
        actual,
        "dma.copy",
        r"^(?!.*if_branch_consumer)(?=.*\bconsumer\s*= \[1\]).*$",
        occurrence=3,
    )


def test_producer_consumer_analysis_if_incoming_same_branch_fanout_uses_distinct_events() -> None:
    """验证 if 外 producer 进入同一分支的 fanout 不共享 event。

    功能说明:
    - if 前 producer 被同一个 then 分支内两个 downstream consumer 读取。
    - 两个 consumer 位于同一路径，必须分配独立 event，而不是复用互斥分支共享 event。

    使用示例:
    - pytest -q test/passes/test_producer_consumer_analysis.py -k if_incoming_same_branch_fanout
    """

    actual = _run_producer_consumer_analysis(
        f"""builtin.module {{
  func.func @if_incoming_same_branch_fanout(%cond : i1, %a : {_LOCAL_TYPE}, %gm : {_GLOBAL_TYPE}, %tmp1 : {_LOCAL_TYPE}, %tmp2 : {_LOCAL_TYPE}) {{
    "dma.copy"(%a, %gm) : ({_LOCAL_TYPE}, {_GLOBAL_TYPE}) -> ()
    scf.if %cond {{
      "dma.copy"(%tmp1, %a) : ({_LOCAL_TYPE}, {_LOCAL_TYPE}) -> ()
      "dma.copy"(%tmp2, %a) : ({_LOCAL_TYPE}, {_LOCAL_TYPE}) -> ()
    }} else {{
    }}
    func.return
  }}
}}
"""
    )
    _assert_line_matches(
        actual,
        "dma.copy",
        r"^(?!.*\bproductor\s*=)(?=.*if_branch_productor = \[0, 1\]).*$",
        occurrence=1,
    )
    _assert_line_matches(
        actual,
        "dma.copy",
        r"^(?!.*\bconsumer\s*=)(?=.*if_branch_consumer = \[0\]).*$",
        occurrence=2,
    )
    _assert_line_matches(
        actual,
        "dma.copy",
        r"^(?!.*\bconsumer\s*=)(?=.*if_branch_consumer = \[1\]).*$",
        occurrence=3,
    )


def test_producer_consumer_analysis_symbol_for_body_and_after_loop_edges() -> None:
    """验证 `symbol.for` loop-body 与 after-loop 分类 attr。

    功能说明:
    - loop 前 producer 到 body consumer 标 `loop_body_*`。
    - loop body producer 到 loop 后 consumer 标 `after_loop_*`。

    使用示例:
    - pytest -q test/passes/test_producer_consumer_analysis.py -k symbol_for
    """

    actual = _run_producer_consumer_analysis(
        f"""builtin.module {{
  func.func @loop_edges(%a : {_LOCAL_TYPE}, %gm : {_GLOBAL_TYPE}, %b : {_LOCAL_TYPE}, %out : {_LOCAL_TYPE}, %tmp : {_LOCAL_TYPE}) {{
    %c0 = symbol.const 0 : !symbol.int<#symbol.expr<0>>
    %c1 = symbol.const 1 : !symbol.int<#symbol.expr<1>>
    %n = symbol.const 4 : !symbol.int<#symbol.expr<4>>
    "dma.copy"(%a, %gm) : ({_LOCAL_TYPE}, {_GLOBAL_TYPE}) -> ()
    symbol.for %i = %c0 to %n step %c1 {{iter = #symbol.iter<start = #symbol.expr<0>, end = #symbol.expr<4>, step = #symbol.expr<1>>}} {{
      "kernel.matmul"(%out, %a, %b) {{space = #nn.space<tsm>}} : ({_LOCAL_TYPE}, {_LOCAL_TYPE}, {_LOCAL_TYPE}) -> ()
    }}
    "dma.copy"(%tmp, %out) : ({_LOCAL_TYPE}, {_LOCAL_TYPE}) -> ()
    func.return
  }}
}}
"""
    )
    _assert_line_matches(
        actual,
        "dma.copy",
        r"^(?!.*\bproductor\s*=)(?=.*loop_body_productor = \[0\]).*$",
        occurrence=1,
    )
    _assert_line_matches(
        actual,
        "kernel.matmul",
        r"^(?!.*\bconsumer\s*=)(?!.*\bproductor\s*=)(?=.*loop_body_consumer = \[0\])(?=.*after_loop_productor = \[1\]).*$",
        occurrence=1,
    )
    _assert_line_matches(
        actual,
        "dma.copy",
        r"^(?!.*\bconsumer\s*=)(?=.*after_loop_consumer = \[1\]).*$",
        occurrence=2,
    )


def test_producer_consumer_analysis_loop_body_plain_edge_uses_main_attrs() -> None:
    """验证同一 loop body block 内普通顺序 edge 使用主 event。

    功能说明:
    - loop body 内 producer 与 consumer 位于同一 block。
    - 该普通顺序 edge 只写 `productor` / `consumer`，不得误写 `loop_body_*`。

    使用示例:
    - pytest -q test/passes/test_producer_consumer_analysis.py -k loop_body_plain_edge
    """

    actual = _run_producer_consumer_analysis(
        f"""builtin.module {{
  func.func @loop_body_plain_edge(%a : {_LOCAL_TYPE}, %gm : {_GLOBAL_TYPE}, %b : {_LOCAL_TYPE}, %out : {_LOCAL_TYPE}) {{
    %c0 = symbol.const 0 : !symbol.int<#symbol.expr<0>>
    %c1 = symbol.const 1 : !symbol.int<#symbol.expr<1>>
    %n = symbol.const 4 : !symbol.int<#symbol.expr<4>>
    symbol.for %i = %c0 to %n step %c1 {{iter = #symbol.iter<start = #symbol.expr<0>, end = #symbol.expr<4>, step = #symbol.expr<1>>}} {{
      "dma.copy"(%a, %gm) : ({_LOCAL_TYPE}, {_GLOBAL_TYPE}) -> ()
      "kernel.matmul"(%out, %a, %b) {{space = #nn.space<tsm>}} : ({_LOCAL_TYPE}, {_LOCAL_TYPE}, {_LOCAL_TYPE}) -> ()
    }}
    func.return
  }}
}}
"""
    )
    _assert_line_matches(
        actual,
        "dma.copy",
        r"^(?!.*loop_body_productor)(?=.*\bproductor\s*= \[0\]).*$",
        occurrence=1,
    )
    _assert_line_matches(
        actual,
        "kernel.matmul",
        r"^(?!.*loop_body_consumer)(?!.*\bproductor\s*=)(?=.*\bconsumer\s*= \[0\]).*$",
        occurrence=1,
    )


def test_producer_consumer_analysis_rejects_invalid_event_attr_and_unknown_option() -> None:
    """验证非法旧 attr 与未知 option 失败。

    功能说明:
    - rerun 前发现负 event id 必须 fail-fast。
    - `from_options(...)` 第一阶段不接受 pass 专属 option。

    使用示例:
    - pytest -q test/passes/test_producer_consumer_analysis.py -k rejects_invalid
    """

    invalid_ir = f"""builtin.module {{
  func.func @invalid_attr(%a : {_LOCAL_TYPE}, %gm : {_GLOBAL_TYPE}) {{
    "dma.copy"(%a, %gm) {{productor = [-1]}} : ({_LOCAL_TYPE}, {_GLOBAL_TYPE}) -> ()
    func.return
  }}
}}
"""
    with pytest.raises(KernelCodeError, match=r"ProducerConsumerAnalysisPassError: invalid event attr"):
        _run_producer_consumer_analysis(invalid_ir)
    with pytest.raises(KernelCodeError, match=r"ProducerConsumerAnalysisPassError: unknown option: mode"):
        ProducerConsumerAnalysisPass.from_options({"mode": "strict"})


def test_producer_consumer_analysis_registry_entry_and_fold_option() -> None:
    """验证 registry 公开名称与通用 fold option。

    功能说明:
    - `producer-consumer-analysis` 必须通过内置 registry 构造。
    - registry 通用 `fold=false` 仍可透传。

    使用示例:
    - pytest -q test/passes/test_producer_consumer_analysis.py -k registry_entry
    """

    load_builtin_passes()
    pass_obj = build_registered_pass("producer-consumer-analysis", {"fold": "false"})
    assert isinstance(pass_obj, ProducerConsumerAnalysisPass)
    assert pass_obj.fold is False
    with pytest.raises(KernelCodeError, match=r"pass 'producer-consumer-analysis' option error"):
        build_registered_pass("producer-consumer-analysis", {"mode": "strict"})
