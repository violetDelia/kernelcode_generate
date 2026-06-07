"""kernel aggregate pass tests.

功能说明:
- 覆盖 `KernelAggregatePass` 的公开 registry 入口、matmul+add 聚合和保守失败边界。

使用示例:
- pytest -q test/passes/kernel/test_kernel_aggregate.py

关联文件:
- 功能实现: kernel_gen/passes/kernel/kernel_aggregate.py
- Spec 文档: spec/pass/kernel/kernel_aggregate.md
- 测试文件: test/passes/kernel/test_kernel_aggregate.py
"""

from __future__ import annotations

from kernel_gen.tools.ircheck import run_ircheck_text


def _run_kernel_aggregate_case(case_name: str, case_text: str) -> str:
    """运行 kernel-aggregate ircheck case。

    功能说明:
    - 通过公开 `run_ircheck_text(...)` 入口执行 registry pass。
    - 成功时返回实际 IR 文本，失败时把 message 带入断言。

    使用示例:
    - actual = _run_kernel_aggregate_case("case", text)
    """

    source_path = f"test/passes/kernel/test_kernel_aggregate.py#{case_name}"
    result = run_ircheck_text(case_text, source_path=source_path)
    actual_ir = result.actual_ir
    assert result.ok is True, result.message
    assert actual_ir
    return actual_ir


def _run_kernel_aggregate_failure(case_name: str, case_text: str) -> str:
    """运行预期失败的 kernel-aggregate ircheck case。

    功能说明:
    - 通过公开 `run_ircheck_text(...)` 入口执行 registry pass。
    - 返回稳定失败 message，供测试匹配公开错误短语。

    使用示例:
    - message = _run_kernel_aggregate_failure("case", text)
    """

    source_path = f"test/passes/kernel/test_kernel_aggregate.py#{case_name}"
    result = run_ircheck_text(case_text, source_path=source_path)
    message = result.message
    assert result.ok is False
    assert message is not None
    return message


def _aggregate_case_text(
    start_expr: str,
    end_expr: str,
    step_expr: str,
    *,
    contract_expr: str | None = None,
    extra_use: bool = False,
) -> str:
    """构造 kernel aggregate 基础 IR。

    功能说明:
    - 生成单个 K owner `symbol.for` 内的 tmp matmul + add 形态。
    - `extra_use=True` 时额外插入 dma.copy，验证 tmp extra use no-op。

    使用示例:
    - text = _aggregate_case_text("0", "32", "32")
    """

    extra = (
        '"dma.copy"(%out, %tmp) : (!nn.memory<[#symbol.expr<8>, #symbol.expr<16>], [#symbol.expr<16>, #symbol.expr<1>], f32, #nn.space<tsm>>, '
        '!nn.memory<[#symbol.expr<8>, #symbol.expr<16>], [#symbol.expr<16>, #symbol.expr<1>], f32, #nn.space<tsm>>) -> ()'
        if extra_use
        else ""
    )
    compile_args = '--pass "kernel-aggregate={matmul-acc=true}"'
    k_expr = contract_expr if contract_expr is not None else step_expr
    return f"""// COMPILE_ARGS: {compile_args}
#S = #symbol.expr<{start_expr}>
#E = #symbol.expr<{end_expr}>
#K = #symbol.expr<{k_expr}>
#Step = #symbol.expr<{step_expr}>
#ItK = #symbol.iter<start = #S, end = #E, step = #Step>
builtin.module {{
  func.func @aggregate_case(
      %out : !nn.memory<[#symbol.expr<8>, #symbol.expr<16>], [#symbol.expr<16>, #symbol.expr<1>], f32, #nn.space<tsm>>,
      %lhs : !nn.memory<[#symbol.expr<8>, #K], [#K, #symbol.expr<1>], f32, #nn.space<tsm>>,
      %rhs : !nn.memory<[#K, #symbol.expr<16>], [#symbol.expr<16>, #symbol.expr<1>], f32, #nn.space<tsm>>) {{
    %s = symbol.const {start_expr} : !symbol.int<#S>
    %e = symbol.const {end_expr} : !symbol.int<#E>
    %k = symbol.const {step_expr} : !symbol.int<#Step>
    symbol.for %ki = %s to %e step %k {{iter = #ItK}} {{
      %tmp = "dma.alloc"() <{{operandSegmentSizes = array<i32: 0>}}> : () -> !nn.memory<[#symbol.expr<8>, #symbol.expr<16>], [#symbol.expr<16>, #symbol.expr<1>], f32, #nn.space<tsm>>
      "kernel.matmul"(%tmp, %lhs, %rhs) {{space = #nn.space<tsm>}} : (!nn.memory<[#symbol.expr<8>, #symbol.expr<16>], [#symbol.expr<16>, #symbol.expr<1>], f32, #nn.space<tsm>>, !nn.memory<[#symbol.expr<8>, #K], [#K, #symbol.expr<1>], f32, #nn.space<tsm>>, !nn.memory<[#K, #symbol.expr<16>], [#symbol.expr<16>, #symbol.expr<1>], f32, #nn.space<tsm>>) -> ()
      "kernel.binary_elewise"(%out, %out, %tmp) {{kind = "add", space = #nn.space<tsm>}} : (!nn.memory<[#symbol.expr<8>, #symbol.expr<16>], [#symbol.expr<16>, #symbol.expr<1>], f32, #nn.space<tsm>>, !nn.memory<[#symbol.expr<8>, #symbol.expr<16>], [#symbol.expr<16>, #symbol.expr<1>], f32, #nn.space<tsm>>, !nn.memory<[#symbol.expr<8>, #symbol.expr<16>], [#symbol.expr<16>, #symbol.expr<1>], f32, #nn.space<tsm>>) -> ()
      {extra}
      "dma.free"(%tmp) : (!nn.memory<[#symbol.expr<8>, #symbol.expr<16>], [#symbol.expr<16>, #symbol.expr<1>], f32, #nn.space<tsm>>) -> ()
    }}
    func.return
  }}
}}"""


def test_kernel_aggregate_fuses_zero_start_reduce_owner() -> None:
    """验证 zero-start K owner 聚合并删除 tmp 生命周期。

    功能说明:
    - 运行公开 registry pass `kernel-aggregate={matmul-acc=true}`。
    - 断言输出包含 `symbol.ne`、带固定 fusion_list 的 `kernel.matmul_fusion`，且原 tmp 形态消失。

    使用示例:
    - pytest -q test/passes/kernel/test_kernel_aggregate.py -k test_kernel_aggregate_fuses_zero_start_reduce_owner
    """

    actual = _run_kernel_aggregate_case("zero_start", _aggregate_case_text("0", "32", "32"))
    assert "symbol.ne" in actual
    assert '"kernel.matmul_fusion"' in actual
    assert 'fusion_list = "kernel.matmul,kernel.binary_elewise.add"' in actual
    assert '"kernel.matmul"' not in actual
    assert '"kernel.binary_elewise"' not in actual
    assert '"dma.free"' not in actual


def test_kernel_aggregate_fuses_nonzero_start_reduce_owner() -> None:
    """验证 nonzero start 使用真实 start SSA，不写死 0。

    功能说明:
    - 运行 start=8 的公开 IR。
    - 断言聚合后仍保留 start 常量并生成 fusion。

    使用示例:
    - pytest -q test/passes/kernel/test_kernel_aggregate.py -k test_kernel_aggregate_fuses_nonzero_start_reduce_owner
    """

    actual = _run_kernel_aggregate_case("nonzero_start", _aggregate_case_text("8", "40", "32"))
    assert "symbol.ne" in actual
    assert '"kernel.matmul_fusion"' in actual
    assert "symbol.const 8" in actual


def test_kernel_aggregate_fuses_dynamic_start_reduce_owner() -> None:
    """验证 dynamic start 使用公开 start operand。

    功能说明:
    - 输入 loop start 来自函数 block argument。
    - 聚合后通过 `symbol.ne` 比较 iterator 与该 start operand。

    使用示例:
    - pytest -q test/passes/kernel/test_kernel_aggregate.py -k test_kernel_aggregate_fuses_dynamic_start_reduce_owner
    """

    case_text = """// COMPILE_ARGS: --pass "kernel-aggregate={matmul-acc=true}"
#S = #symbol.expr<S>
#E = #symbol.expr<K>
#K = #symbol.expr<TILE_K>
#ItK = #symbol.iter<start = #S, end = #E, step = #K>
builtin.module {
  func.func @aggregate_dynamic_start(
      %out : !nn.memory<[#symbol.expr<8>, #symbol.expr<16>], [#symbol.expr<16>, #symbol.expr<1>], f32, #nn.space<tsm>>,
      %lhs : !nn.memory<[#symbol.expr<8>, #K], [#K, #symbol.expr<1>], f32, #nn.space<tsm>>,
      %rhs : !nn.memory<[#K, #symbol.expr<16>], [#symbol.expr<16>, #symbol.expr<1>], f32, #nn.space<tsm>>,
      %s : !symbol.int<#S>, %e : !symbol.int<#E>, %k : !symbol.int<#K>) {
    symbol.for %ki = %s to %e step %k {iter = #ItK} {
      %tmp = "dma.alloc"() <{operandSegmentSizes = array<i32: 0>}> : () -> !nn.memory<[#symbol.expr<8>, #symbol.expr<16>], [#symbol.expr<16>, #symbol.expr<1>], f32, #nn.space<tsm>>
      "kernel.matmul"(%tmp, %lhs, %rhs) {space = #nn.space<tsm>} : (!nn.memory<[#symbol.expr<8>, #symbol.expr<16>], [#symbol.expr<16>, #symbol.expr<1>], f32, #nn.space<tsm>>, !nn.memory<[#symbol.expr<8>, #K], [#K, #symbol.expr<1>], f32, #nn.space<tsm>>, !nn.memory<[#K, #symbol.expr<16>], [#symbol.expr<16>, #symbol.expr<1>], f32, #nn.space<tsm>>) -> ()
      "kernel.binary_elewise"(%out, %out, %tmp) {kind = "add", space = #nn.space<tsm>} : (!nn.memory<[#symbol.expr<8>, #symbol.expr<16>], [#symbol.expr<16>, #symbol.expr<1>], f32, #nn.space<tsm>>, !nn.memory<[#symbol.expr<8>, #symbol.expr<16>], [#symbol.expr<16>, #symbol.expr<1>], f32, #nn.space<tsm>>, !nn.memory<[#symbol.expr<8>, #symbol.expr<16>], [#symbol.expr<16>, #symbol.expr<1>], f32, #nn.space<tsm>>) -> ()
      "dma.free"(%tmp) : (!nn.memory<[#symbol.expr<8>, #symbol.expr<16>], [#symbol.expr<16>, #symbol.expr<1>], f32, #nn.space<tsm>>) -> ()
    }
    func.return
  }
}"""
    actual = _run_kernel_aggregate_case("dynamic_start", case_text)
    assert "symbol.ne" in actual
    assert '"kernel.matmul_fusion"' in actual


def test_kernel_aggregate_fuses_nested_k_owner() -> None:
    """验证 nested M/K loop 选择 contracting K owner。

    功能说明:
    - 在外层 M loop 内嵌 K loop。
    - 只有 K loop 的 step 与 contracting dimension 匹配，应被选作 acc owner。

    使用示例:
    - pytest -q test/passes/kernel/test_kernel_aggregate.py -k test_kernel_aggregate_fuses_nested_k_owner
    """

    case_text = """// COMPILE_ARGS: --pass "kernel-aggregate={matmul-acc=true}"
#M = #symbol.expr<8>
#N = #symbol.expr<16>
#K = #symbol.expr<32>
#S = #symbol.expr<0>
#E = #symbol.expr<32>
#ItM = #symbol.iter<start = #S, end = #E, step = #M>
#ItK = #symbol.iter<start = #S, end = #E, step = #K>
builtin.module {
  func.func @nested_k_case(
      %out : !nn.memory<[#M, #N], [#N, #symbol.expr<1>], f32, #nn.space<tsm>>,
      %lhs : !nn.memory<[#M, #K], [#K, #symbol.expr<1>], f32, #nn.space<tsm>>,
      %rhs : !nn.memory<[#K, #N], [#N, #symbol.expr<1>], f32, #nn.space<tsm>>) {
    %s = symbol.const 0 : !symbol.int<#S>
    %e = symbol.const 32 : !symbol.int<#E>
    %m = symbol.const 8 : !symbol.int<#M>
    %k = symbol.const 32 : !symbol.int<#K>
    symbol.for %mi = %s to %e step %m {iter = #ItM} {
      symbol.for %ki = %s to %e step %k {iter = #ItK} {
        %tmp = "dma.alloc"() <{operandSegmentSizes = array<i32: 0>}> : () -> !nn.memory<[#M, #N], [#N, #symbol.expr<1>], f32, #nn.space<tsm>>
        "kernel.matmul"(%tmp, %lhs, %rhs) {space = #nn.space<tsm>} : (!nn.memory<[#M, #N], [#N, #symbol.expr<1>], f32, #nn.space<tsm>>, !nn.memory<[#M, #K], [#K, #symbol.expr<1>], f32, #nn.space<tsm>>, !nn.memory<[#K, #N], [#N, #symbol.expr<1>], f32, #nn.space<tsm>>) -> ()
        "kernel.binary_elewise"(%out, %out, %tmp) {kind = "add", space = #nn.space<tsm>} : (!nn.memory<[#M, #N], [#N, #symbol.expr<1>], f32, #nn.space<tsm>>, !nn.memory<[#M, #N], [#N, #symbol.expr<1>], f32, #nn.space<tsm>>, !nn.memory<[#M, #N], [#N, #symbol.expr<1>], f32, #nn.space<tsm>>) -> ()
        "dma.free"(%tmp) : (!nn.memory<[#M, #N], [#N, #symbol.expr<1>], f32, #nn.space<tsm>>) -> ()
      }
    }
    func.return
  }
}"""
    actual = _run_kernel_aggregate_case("nested_k", case_text)
    assert '"kernel.matmul_fusion"' in actual


def test_kernel_aggregate_fuses_outer_tmp_lifetime_nested_k_owner() -> None:
    """验证外层 tmp 生命周期包住内层 K loop 时可聚合。

    功能说明:
    - tmp alloc/free 位于函数 block，matmul+add 位于嵌套 K loop block。
    - pass 通过 owner block 顺序证明 alloc < loop < free 后删除 tmp 生命周期。

    使用示例:
    - pytest -q test/passes/kernel/test_kernel_aggregate.py -k test_kernel_aggregate_fuses_outer_tmp_lifetime_nested_k_owner
    """

    case_text = """// COMPILE_ARGS: --pass "kernel-aggregate={matmul-acc=true}"
#M = #symbol.expr<8>
#N = #symbol.expr<16>
#K = #symbol.expr<32>
#S = #symbol.expr<0>
#E = #symbol.expr<32>
#ItK = #symbol.iter<start = #S, end = #E, step = #K>
builtin.module {
  func.func @outer_tmp_lifetime_case(
      %out : !nn.memory<[#M, #N], [#N, #symbol.expr<1>], f32, #nn.space<tsm>>,
      %lhs : !nn.memory<[#M, #K], [#K, #symbol.expr<1>], f32, #nn.space<tsm>>,
      %rhs : !nn.memory<[#K, #N], [#N, #symbol.expr<1>], f32, #nn.space<tsm>>) {
    %s = symbol.const 0 : !symbol.int<#S>
    %e = symbol.const 32 : !symbol.int<#E>
    %k = symbol.const 32 : !symbol.int<#K>
    %tmp = "dma.alloc"() <{operandSegmentSizes = array<i32: 0>}> : () -> !nn.memory<[#M, #N], [#N, #symbol.expr<1>], f32, #nn.space<tsm>>
    symbol.for %ki = %s to %e step %k {iter = #ItK} {
      "kernel.matmul"(%tmp, %lhs, %rhs) {space = #nn.space<tsm>} : (!nn.memory<[#M, #N], [#N, #symbol.expr<1>], f32, #nn.space<tsm>>, !nn.memory<[#M, #K], [#K, #symbol.expr<1>], f32, #nn.space<tsm>>, !nn.memory<[#K, #N], [#N, #symbol.expr<1>], f32, #nn.space<tsm>>) -> ()
      "kernel.binary_elewise"(%out, %out, %tmp) {kind = "add", space = #nn.space<tsm>} : (!nn.memory<[#M, #N], [#N, #symbol.expr<1>], f32, #nn.space<tsm>>, !nn.memory<[#M, #N], [#N, #symbol.expr<1>], f32, #nn.space<tsm>>, !nn.memory<[#M, #N], [#N, #symbol.expr<1>], f32, #nn.space<tsm>>) -> ()
    }
    "dma.free"(%tmp) : (!nn.memory<[#M, #N], [#N, #symbol.expr<1>], f32, #nn.space<tsm>>) -> ()
    func.return
  }
}"""

    actual = _run_kernel_aggregate_case("outer_tmp_lifetime", case_text)
    assert '"kernel.matmul_fusion"' in actual
    assert '"kernel.matmul"' not in actual
    assert '"kernel.binary_elewise"' not in actual
    assert '"dma.alloc"' not in actual
    assert '"dma.free"' not in actual


def test_kernel_aggregate_fuses_tail_reduce_owner_with_intervening_frees() -> None:
    """验证 tail K 维与 staging free 不阻断聚合。

    功能说明:
    - lhs/rhs 的 contracting 维为 `min(step, remaining)`，用于有效 tile 尾块。
    - `kernel.matmul` 与累加 add 中间夹着不触碰 tmp/out 的 `dma.free`。
    - 聚合后保留 lhs/rhs staging free，删除 tmp 生命周期并生成 fusion。

    使用示例:
    - pytest -q test/passes/kernel/test_kernel_aggregate.py -k test_kernel_aggregate_fuses_tail_reduce_owner_with_intervening_frees
    """

    case_text = """// COMPILE_ARGS: --pass "kernel-aggregate={matmul-acc=true}"
#M = #symbol.expr<8>
#N = #symbol.expr<16>
#Step = #symbol.expr<32>
#K = #symbol.expr<min(32, 96 - iter<0,96,32>)>
#S = #symbol.expr<0>
#E = #symbol.expr<96>
#ItK = #symbol.iter<start = #S, end = #E, step = #Step>
builtin.module {
  func.func @tail_with_intervening_free_case(
      %out : !nn.memory<[#M, #N], [#N, #symbol.expr<1>], f32, #nn.space<tsm>>) {
    %s = symbol.const 0 : !symbol.int<#S>
    %e = symbol.const 96 : !symbol.int<#E>
    %k = symbol.const 32 : !symbol.int<#Step>
    %m = symbol.const 8 : !symbol.int<#M>
    %n = symbol.const 16 : !symbol.int<#N>
    symbol.for %ki = %s to %e step %k {iter = #ItK} {
      %rem = symbol.sub %e, %ki : !symbol.int<#E>, !symbol.iter<start = #S, end = #E, step = #Step> -> !symbol.int<#symbol.expr<96 - iter<0,96,32>>>
      %cur = symbol.min %k, %rem : !symbol.int<#Step>, !symbol.int<#symbol.expr<96 - iter<0,96,32>>> -> !symbol.int<#K>
      %lhs = "dma.alloc"(%m, %cur) <{operandSegmentSizes = array<i32: 2>}> : (!symbol.int<#M>, !symbol.int<#K>) -> !nn.memory<[#M, #K], [#K, #symbol.expr<1>], f32, #nn.space<tlm1>>
      %rhs = "dma.alloc"(%cur, %n) <{operandSegmentSizes = array<i32: 2>}> : (!symbol.int<#K>, !symbol.int<#N>) -> !nn.memory<[#K, #N], [#N, #symbol.expr<1>], f32, #nn.space<tlm2>>
      %tmp = "dma.alloc"() <{operandSegmentSizes = array<i32: 0>}> : () -> !nn.memory<[#M, #N], [#N, #symbol.expr<1>], f32, #nn.space<tsm>>
      "kernel.matmul"(%tmp, %lhs, %rhs) {space = #nn.space<tsm>} : (!nn.memory<[#M, #N], [#N, #symbol.expr<1>], f32, #nn.space<tsm>>, !nn.memory<[#M, #K], [#K, #symbol.expr<1>], f32, #nn.space<tlm1>>, !nn.memory<[#K, #N], [#N, #symbol.expr<1>], f32, #nn.space<tlm2>>) -> ()
      "dma.free"(%lhs) : (!nn.memory<[#M, #K], [#K, #symbol.expr<1>], f32, #nn.space<tlm1>>) -> ()
      "dma.free"(%rhs) : (!nn.memory<[#K, #N], [#N, #symbol.expr<1>], f32, #nn.space<tlm2>>) -> ()
      "kernel.binary_elewise"(%out, %out, %tmp) {kind = "add", space = #nn.space<tsm>} : (!nn.memory<[#M, #N], [#N, #symbol.expr<1>], f32, #nn.space<tsm>>, !nn.memory<[#M, #N], [#N, #symbol.expr<1>], f32, #nn.space<tsm>>, !nn.memory<[#M, #N], [#N, #symbol.expr<1>], f32, #nn.space<tsm>>) -> ()
      "dma.free"(%tmp) : (!nn.memory<[#M, #N], [#N, #symbol.expr<1>], f32, #nn.space<tsm>>) -> ()
    }
    func.return
  }
}"""
    actual = _run_kernel_aggregate_case("tail_with_intervening_free", case_text)
    assert '"kernel.matmul_fusion"' in actual
    assert '"kernel.matmul"' not in actual
    assert '"kernel.binary_elewise"' not in actual
    assert actual.count('"dma.free"') == 2


def test_kernel_aggregate_fuses_tmp_reinterpret_alias() -> None:
    """验证 tmp 经公开 alias op 后仍可聚合。

    功能说明:
    - tmp root alloc 只被单个 `dma.reinterpret` alias 和最终 free 使用。
    - matmul/add 只使用 alias SSA，满足受控生命周期时可删除 root alloc、alias 与 tmp free。

    使用示例:
    - pytest -q test/passes/kernel/test_kernel_aggregate.py -k test_kernel_aggregate_fuses_tmp_reinterpret_alias
    """

    case_text = """// COMPILE_ARGS: --pass "kernel-aggregate={matmul-acc=true}"
#M = #symbol.expr<8>
#N = #symbol.expr<16>
#K = #symbol.expr<32>
#S = #symbol.expr<0>
#E = #symbol.expr<32>
#ItK = #symbol.iter<start = #S, end = #E, step = #K>
builtin.module {
  func.func @tmp_reinterpret_alias_case(
      %out : !nn.memory<[#M, #N], [#N, #symbol.expr<1>], f32, #nn.space<tsm>>,
      %lhs : !nn.memory<[#M, #K], [#K, #symbol.expr<1>], f32, #nn.space<tsm>>,
      %rhs : !nn.memory<[#K, #N], [#N, #symbol.expr<1>], f32, #nn.space<tsm>>) {
    %s = symbol.const 0 : !symbol.int<#S>
    %e = symbol.const 32 : !symbol.int<#E>
    %k = symbol.const 32 : !symbol.int<#K>
    %zero = symbol.const 0 : !symbol.int<#S>
    %m = symbol.const 8 : !symbol.int<#M>
    %n = symbol.const 16 : !symbol.int<#N>
    %one = symbol.const 1 : !symbol.int<#symbol.expr<1>>
    symbol.for %ki = %s to %e step %k {iter = #ItK} {
      %tmp_root = "dma.alloc"() <{operandSegmentSizes = array<i32: 0>}> : () -> !nn.memory<[#M, #N], [#N, #symbol.expr<1>], f32, #nn.space<tsm>>
      %tmp = "dma.reinterpret"(%tmp_root, %zero, %m, %n, %n, %one) <{operandSegmentSizes = array<i32: 1, 1, 2, 2>}> : (!nn.memory<[#M, #N], [#N, #symbol.expr<1>], f32, #nn.space<tsm>>, !symbol.int<#S>, !symbol.int<#M>, !symbol.int<#N>, !symbol.int<#N>, !symbol.int<#symbol.expr<1>>) -> !nn.memory<[#M, #N], [#N, #symbol.expr<1>], f32, #nn.space<tsm>>
      "kernel.matmul"(%tmp, %lhs, %rhs) {space = #nn.space<tsm>} : (!nn.memory<[#M, #N], [#N, #symbol.expr<1>], f32, #nn.space<tsm>>, !nn.memory<[#M, #K], [#K, #symbol.expr<1>], f32, #nn.space<tsm>>, !nn.memory<[#K, #N], [#N, #symbol.expr<1>], f32, #nn.space<tsm>>) -> ()
      "kernel.binary_elewise"(%out, %out, %tmp) {kind = "add", space = #nn.space<tsm>} : (!nn.memory<[#M, #N], [#N, #symbol.expr<1>], f32, #nn.space<tsm>>, !nn.memory<[#M, #N], [#N, #symbol.expr<1>], f32, #nn.space<tsm>>, !nn.memory<[#M, #N], [#N, #symbol.expr<1>], f32, #nn.space<tsm>>) -> ()
      "dma.free"(%tmp_root) : (!nn.memory<[#M, #N], [#N, #symbol.expr<1>], f32, #nn.space<tsm>>) -> ()
    }
    func.return
  }
}"""
    actual = _run_kernel_aggregate_case("tmp_reinterpret_alias", case_text)
    assert '"kernel.matmul_fusion"' in actual
    assert '"dma.reinterpret"' not in actual
    assert '"dma.alloc"' not in actual
    assert '"dma.free"' not in actual


def test_kernel_aggregate_rejects_multiple_k_owner_candidates() -> None:
    """验证多个 K owner 候选 fail-fast。

    功能说明:
    - 构造两个 step 均匹配 K 维的嵌套 loop。
    - pass 必须拒绝歧义 acc owner。

    使用示例:
    - pytest -q test/passes/kernel/test_kernel_aggregate.py -k test_kernel_aggregate_rejects_multiple_k_owner_candidates
    """

    case_text = _aggregate_case_text("0", "32", "32").replace(
        'symbol.for %ki = %s to %e step %k {iter = #ItK} {',
        'symbol.for %ko = %s to %e step %k {iter = #ItK} {\n    symbol.for %ki = %s to %e step %k {iter = #ItK} {',
    ).replace(
        "    func.return",
        "    }\n    func.return",
    )
    message = _run_kernel_aggregate_failure("multiple_k", case_text)
    assert "kernel-aggregate matmul acc iterator" in message


def test_kernel_aggregate_rejects_m_or_n_loop_as_acc_owner() -> None:
    """验证 M/N loop 不能被误选为 K owner。

    功能说明:
    - 构造 loop step 与 matmul contracting dimension 不匹配的场景。
    - pass 必须 fail-fast，不能按最近 loop 猜测。

    使用示例:
    - pytest -q test/passes/kernel/test_kernel_aggregate.py -k test_kernel_aggregate_rejects_m_or_n_loop_as_acc_owner
    """

    message = _run_kernel_aggregate_failure(
        "wrong_owner",
        _aggregate_case_text("0", "8", "8", contract_expr="32"),
    )
    assert "kernel-aggregate matmul acc iterator" in message


def test_kernel_aggregate_keeps_extra_tmp_use_no_op() -> None:
    """验证 tmp 有额外 use 时保持 no-op。

    功能说明:
    - 为 tmp 追加 `dma.copy` data use。
    - pass 不得删除 tmp 生命周期或生成 fusion。

    使用示例:
    - pytest -q test/passes/kernel/test_kernel_aggregate.py -k test_kernel_aggregate_keeps_extra_tmp_use_no_op
    """

    actual = _run_kernel_aggregate_case("extra_use", _aggregate_case_text("0", "32", "32", extra_use=True))
    assert '"kernel.matmul_fusion"' not in actual
    assert '"dma.copy"' in actual


def test_kernel_aggregate_matmul_acc_false_no_op() -> None:
    """验证 matmul-acc=false 时保持 no-op。

    功能说明:
    - 通过 registry option 关闭聚合。
    - 原 `kernel.matmul` 应保留。

    使用示例:
    - pytest -q test/passes/kernel/test_kernel_aggregate.py -k test_kernel_aggregate_matmul_acc_false_no_op
    """

    case_text = _aggregate_case_text("0", "32", "32").replace("matmul-acc=true", "matmul-acc=false")
    actual = _run_kernel_aggregate_case("matmul_acc_false", case_text)
    assert '"kernel.matmul_fusion"' not in actual
    assert '"kernel.matmul"' in actual
