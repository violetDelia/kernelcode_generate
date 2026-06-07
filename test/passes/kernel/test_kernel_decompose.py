"""kernel decompose pass tests.

功能说明:
- 覆盖 `KernelDecomposePass` 的公开 registry 入口、动态 acc 分解和 no-op 边界。
- 覆盖 `kernel-decompose` 保留 existing `dma.fill` 的职责边界。

使用示例:
- pytest -q test/passes/kernel/test_kernel_decompose.py

关联文件:
- 功能实现: kernel_gen/passes/kernel/kernel_decompose.py
- Spec 文档: spec/pass/kernel/kernel_decompose.md
- 测试文件: test/passes/kernel/test_kernel_decompose.py
"""

from __future__ import annotations

from kernel_gen.core.error import KernelCodeError
from kernel_gen.passes.registry import build_registered_pass, load_builtin_passes
from kernel_gen.tools.ircheck import run_ircheck_text

_PASS = "--pass kernel-decompose"


def _run_decompose_case(case_name: str, case_text: str) -> str:
    """运行 kernel-decompose ircheck case。

    功能说明:
    - 通过公开 `run_ircheck_text(...)` 入口执行 registry pass。
    - 成功时返回实际 IR 文本，失败时把 message 带入断言。
    - source_path 绑定当前 pytest case，便于 ircheck 失败定位。

    使用示例:
    - actual = _run_decompose_case("case", text)
    """

    source_path = f"test/passes/kernel/test_kernel_decompose.py#{case_name}"
    result = run_ircheck_text(case_text, source_path=source_path)
    actual_ir = result.actual_ir
    assert result.ok is True, result.message
    assert actual_ir
    return actual_ir


def _fusion_case(dynamic: bool, *, fusion_list: str = "") -> str:
    """构造 matmul_fusion 分解测试 IR。

    功能说明:
    - `dynamic=False` 生成静态 out/lhs/rhs。
    - `dynamic=True` 生成 M/N/K 符号 shape。
    - `fusion_list` 非空时注入 metadata，验证分解不复制该 attr。

    使用示例:
    - text = _fusion_case(dynamic=True)
    """

    m = "M" if dynamic else "8"
    n = "N" if dynamic else "16"
    k = "K" if dynamic else "32"
    attrs = "space = #nn.space<tsm>"
    if fusion_list:
        attrs = f'fusion_list = "{fusion_list}", {attrs}'
    return f"""// COMPILE_ARGS: {_PASS}
#M = #symbol.expr<{m}>
#N = #symbol.expr<{n}>
#K = #symbol.expr<{k}>
#S1 = #symbol.expr<1>
builtin.module {{
  func.func @decompose_case(
      %out : !nn.memory<[#M, #N], [#N, #S1], f32, #nn.space<tsm>>,
      %lhs : !nn.memory<[#M, #K], [#K, #S1], f32, #nn.space<tsm>>,
      %rhs : !nn.memory<[#K, #N], [#N, #S1], f32, #nn.space<tsm>>,
      %acc : i1) {{
    "kernel.matmul_fusion"(%out, %lhs, %rhs, %acc) {{{attrs}}} : (!nn.memory<[#M, #N], [#N, #S1], f32, #nn.space<tsm>>, !nn.memory<[#M, #K], [#K, #S1], f32, #nn.space<tsm>>, !nn.memory<[#K, #N], [#N, #S1], f32, #nn.space<tsm>>, i1) -> ()
    func.return
  }}
}}"""


def test_kernel_decompose_static_dynamic_acc_matmul() -> None:
    """验证静态 shape fusion 分解为单条动态 acc matmul。

    功能说明:
    - 运行 `kernel-decompose`。
    - 断言输出不残留 fusion，不生成 scf.if，也不生成静态 acc attr。

    使用示例:
    - pytest -q test/passes/kernel/test_kernel_decompose.py -k static_dynamic_acc
    """

    actual = _run_decompose_case("static", _fusion_case(dynamic=False))
    assert '"kernel.matmul_fusion"' not in actual
    assert "scf.if" not in actual
    assert actual.count('"kernel.matmul"') == 1
    assert '"kernel.matmul"(%out, %lhs, %rhs, %acc)' in actual
    assert "acc = true" not in actual
    assert "acc = false" not in actual


def test_kernel_decompose_dynamic_shape_dynamic_acc_matmul() -> None:
    """验证动态 shape fusion 分解为单条动态 acc matmul。

    功能说明:
    - 输入 out/lhs/rhs shape 为 M/N/K 符号。
    - 分解 pass 不需要 `symbol.get_dim`，只保留动态 acc operand。

    使用示例:
    - pytest -q test/passes/kernel/test_kernel_decompose.py -k dynamic_shape
    """

    actual = _run_decompose_case("dynamic", _fusion_case(dynamic=True))
    assert '"kernel.matmul_fusion"' not in actual
    assert "symbol.get_dim" not in actual
    assert "scf.if" not in actual
    assert actual.count('"kernel.matmul"') == 1
    assert '"kernel.matmul"(%out, %lhs, %rhs, %acc)' in actual


def test_kernel_decompose_reports_stable_error_for_invalid_fusion_acc() -> None:
    """验证 fusion acc 非 i1 时保持稳定 pass 错误。

    功能说明:
    - 输入故意把 `kernel.matmul_fusion` 的 acc operand 写成 i32。
    - pass 在生成动态 acc `kernel.matmul` 后触发局部 verifier 失败。
    - 断言失败文本为 `kernel-decompose matmul acc`，不得泄漏 NameError。

    使用示例:
    - pytest -q test/passes/kernel/test_kernel_decompose.py -k invalid_fusion_acc
    """

    case_text = f"""// COMPILE_ARGS: {_PASS}
builtin.module {{
  func.func @invalid_acc_case(
      %out : !nn.memory<[#symbol.expr<8>, #symbol.expr<16>], [#symbol.expr<16>, #symbol.expr<1>], f32, #nn.space<tsm>>,
      %lhs : !nn.memory<[#symbol.expr<8>, #symbol.expr<32>], [#symbol.expr<32>, #symbol.expr<1>], f32, #nn.space<tsm>>,
      %rhs : !nn.memory<[#symbol.expr<32>, #symbol.expr<16>], [#symbol.expr<16>, #symbol.expr<1>], f32, #nn.space<tsm>>,
      %acc : i32) {{
    "kernel.matmul_fusion"(%out, %lhs, %rhs, %acc) {{space = #nn.space<tsm>}} : (!nn.memory<[#symbol.expr<8>, #symbol.expr<16>], [#symbol.expr<16>, #symbol.expr<1>], f32, #nn.space<tsm>>, !nn.memory<[#symbol.expr<8>, #symbol.expr<32>], [#symbol.expr<32>, #symbol.expr<1>], f32, #nn.space<tsm>>, !nn.memory<[#symbol.expr<32>, #symbol.expr<16>], [#symbol.expr<16>, #symbol.expr<1>], f32, #nn.space<tsm>>, i32) -> ()
    func.return
  }}
}}"""
    result = run_ircheck_text(case_text, source_path="test/passes/kernel/test_kernel_decompose.py#invalid_acc")
    assert result.ok is False
    assert result.exit_code == 2
    assert result.message is not None
    assert "kernel-decompose matmul acc" in result.message
    assert "NameError" not in result.message


def test_kernel_decompose_ignores_fusion_list_metadata() -> None:
    """验证非空 fusion_list 不复制到动态 acc matmul。

    功能说明:
    - 输入携带 aggregate 生成的固定 `fusion_list` 字符串。
    - 输出仍只包含单条动态 acc matmul。

    使用示例:
    - pytest -q test/passes/kernel/test_kernel_decompose.py -k ignores_fusion_list
    """

    actual = _run_decompose_case(
        "fusion_list",
        _fusion_case(dynamic=False, fusion_list="kernel.matmul,kernel.binary_elewise.add"),
    )
    assert '"kernel.matmul_fusion"' not in actual
    assert "fusion_list" not in actual
    assert actual.count('"kernel.matmul"') == 1
    assert "acc = true" not in actual
    assert "acc = false" not in actual


def test_kernel_decompose_no_fusion_no_op() -> None:
    """验证无 fusion 时保持 no-op。

    功能说明:
    - 输入只包含普通 `kernel.matmul`。
    - pass 不得生成 scf.if 或 fusion。

    使用示例:
    - pytest -q test/passes/kernel/test_kernel_decompose.py -k no_fusion
    """

    case_text = f"""// COMPILE_ARGS: {_PASS}
builtin.module {{
  func.func @plain_case(
      %out : !nn.memory<[#symbol.expr<8>, #symbol.expr<16>], [#symbol.expr<16>, #symbol.expr<1>], f32, #nn.space<tsm>>,
      %lhs : !nn.memory<[#symbol.expr<8>, #symbol.expr<32>], [#symbol.expr<32>, #symbol.expr<1>], f32, #nn.space<tsm>>,
      %rhs : !nn.memory<[#symbol.expr<32>, #symbol.expr<16>], [#symbol.expr<16>, #symbol.expr<1>], f32, #nn.space<tsm>>) {{
    "kernel.matmul"(%out, %lhs, %rhs) {{space = #nn.space<tsm>}} : (!nn.memory<[#symbol.expr<8>, #symbol.expr<16>], [#symbol.expr<16>, #symbol.expr<1>], f32, #nn.space<tsm>>, !nn.memory<[#symbol.expr<8>, #symbol.expr<32>], [#symbol.expr<32>, #symbol.expr<1>], f32, #nn.space<tsm>>, !nn.memory<[#symbol.expr<32>, #symbol.expr<16>], [#symbol.expr<16>, #symbol.expr<1>], f32, #nn.space<tsm>>) -> ()
    func.return
  }}
}}"""
    actual = _run_decompose_case("no_fusion", case_text)
    assert '"kernel.matmul"' in actual
    assert '"kernel.matmul_fusion"' not in actual
    assert "scf.if" not in actual


def test_kernel_decompose_keeps_zero_fill_before_dynamic_acc_matmul() -> None:
    """验证 kernel-decompose 保留 initial zero fill。

    功能说明:
    - `dma.fill(out, 0)` 位于 K loop 前。
    - fusion acc 是 `symbol.ne(k_iter, k_start)`。
    - 输出只分解 fusion，并保留 fill 供后续 canonicalization 判断。

    使用示例:
    - pytest -q test/passes/kernel/test_kernel_decompose.py -k keeps_zero_fill
    """

    case_text = f"""// COMPILE_ARGS: {_PASS}
#C0 = #symbol.expr<0>
#C1 = #symbol.expr<1>
#C32 = #symbol.expr<32>
#ItK = #symbol.iter<start = #C0, end = #C32, step = #C32>
builtin.module {{
  func.func @keep_initial_zero_fill_case(
      %out : !nn.memory<[#symbol.expr<8>, #symbol.expr<16>], [#symbol.expr<16>, #symbol.expr<1>], f32, #nn.space<tsm>>,
      %lhs : !nn.memory<[#symbol.expr<8>, #symbol.expr<32>], [#symbol.expr<32>, #symbol.expr<1>], f32, #nn.space<tsm>>,
      %rhs : !nn.memory<[#symbol.expr<32>, #symbol.expr<16>], [#symbol.expr<16>, #symbol.expr<1>], f32, #nn.space<tsm>>) {{
    %c0 = symbol.const 0 : !symbol.int<#C0>
    %c32 = symbol.const 32 : !symbol.int<#C32>
    %zero = arith.constant 0.000000e+00 : f32
    "dma.fill"(%out, %zero) : (!nn.memory<[#symbol.expr<8>, #symbol.expr<16>], [#symbol.expr<16>, #symbol.expr<1>], f32, #nn.space<tsm>>, f32) -> ()
    symbol.for %k = %c0 to %c32 step %c32 {{iter = #ItK}} {{
      %acc = symbol.ne %k, %c0 : !symbol.iter<start = #C0, end = #C32, step = #C32>, !symbol.int<#C0> -> i1
      "kernel.matmul_fusion"(%out, %lhs, %rhs, %acc) {{fusion_list = "kernel.matmul,kernel.binary_elewise.add", space = #nn.space<tsm>}} : (!nn.memory<[#symbol.expr<8>, #symbol.expr<16>], [#symbol.expr<16>, #symbol.expr<1>], f32, #nn.space<tsm>>, !nn.memory<[#symbol.expr<8>, #symbol.expr<32>], [#symbol.expr<32>, #symbol.expr<1>], f32, #nn.space<tsm>>, !nn.memory<[#symbol.expr<32>, #symbol.expr<16>], [#symbol.expr<16>, #symbol.expr<1>], f32, #nn.space<tsm>>, i1) -> ()
    }}
    func.return
  }}
}}"""
    actual = _run_decompose_case("keep_initial_zero_fill", case_text)
    assert actual.count('"dma.fill"') == 1
    assert '"kernel.matmul_fusion"' not in actual
    assert "scf.if" not in actual
    assert actual.count('"kernel.matmul"') == 1


def test_kernel_decompose_keeps_fill_with_pure_alias_setup_before_k_loop() -> None:
    """验证 loop 前纯 alias setup 下仍保留 fill。

    功能说明:
    - `dma.reshape` 仅建立 out 的 alias result，不读写 memory。
    - `kernel-decompose` 只分解 fusion，不依据 alias 或 trip count 删除 fill。

    使用示例:
    - pytest -q test/passes/kernel/test_kernel_decompose.py -k pure_alias_setup
    """

    case_text = f"""// COMPILE_ARGS: {_PASS}
#C0 = #symbol.expr<0>
#C8 = #symbol.expr<8>
#C16 = #symbol.expr<16>
#C32 = #symbol.expr<32>
#C128 = #symbol.expr<128>
#ItK = #symbol.iter<start = #C0, end = #C32, step = #C32>
builtin.module {{
  func.func @allow_alias_setup_case(
      %out : !nn.memory<[#C8, #C16], [#C16, #symbol.expr<1>], f32, #nn.space<tsm>>,
      %lhs : !nn.memory<[#C8, #C32], [#C32, #symbol.expr<1>], f32, #nn.space<tsm>>,
      %rhs : !nn.memory<[#C32, #C16], [#C16, #symbol.expr<1>], f32, #nn.space<tsm>>) {{
    %c0 = symbol.const 0 : !symbol.int<#C0>
    %c32 = symbol.const 32 : !symbol.int<#C32>
    %c128 = symbol.const 128 : !symbol.int<#C128>
    %zero = arith.constant 0.000000e+00 : f32
    "dma.fill"(%out, %zero) : (!nn.memory<[#C8, #C16], [#C16, #symbol.expr<1>], f32, #nn.space<tsm>>, f32) -> ()
    %alias = "dma.reshape"(%out, %c128) <{{operandSegmentSizes = array<i32: 1, 1>}}> : (!nn.memory<[#C8, #C16], [#C16, #symbol.expr<1>], f32, #nn.space<tsm>>, !symbol.int<#C128>) -> !nn.memory<[#C128], [#symbol.expr<1>], f32, #nn.space<tsm>>
    symbol.for %k = %c0 to %c32 step %c32 {{iter = #ItK}} {{
      %acc = symbol.ne %k, %c0 : !symbol.iter<start = #C0, end = #C32, step = #C32>, !symbol.int<#C0> -> i1
      "kernel.matmul_fusion"(%out, %lhs, %rhs, %acc) {{fusion_list = "kernel.matmul,kernel.binary_elewise.add", space = #nn.space<tsm>}} : (!nn.memory<[#C8, #C16], [#C16, #symbol.expr<1>], f32, #nn.space<tsm>>, !nn.memory<[#C8, #C32], [#C32, #symbol.expr<1>], f32, #nn.space<tsm>>, !nn.memory<[#C32, #C16], [#C16, #symbol.expr<1>], f32, #nn.space<tsm>>, i1) -> ()
    }}
    func.return
  }}
}}"""
    actual = _run_decompose_case("allow_alias_setup", case_text)
    assert actual.count('"dma.fill"') == 1
    assert '"kernel.matmul_fusion"' not in actual
    assert actual.count('"kernel.matmul"') == 1


def test_kernel_decompose_keeps_fill_for_alias_write_before_k_loop() -> None:
    """验证 loop 前 alias 写入场景仍只分解 fusion。

    功能说明:
    - `dma.reshape` 把 out 纳入 alias 闭包。
    - loop 前对 alias 执行 `dma.fill`，`kernel-decompose` 不删除任一 fill。

    使用示例:
    - pytest -q test/passes/kernel/test_kernel_decompose.py -k alias_write_before_k_loop
    """

    case_text = f"""// COMPILE_ARGS: {_PASS}
#C0 = #symbol.expr<0>
#C8 = #symbol.expr<8>
#C16 = #symbol.expr<16>
#C32 = #symbol.expr<32>
#C128 = #symbol.expr<128>
#ItK = #symbol.iter<start = #C0, end = #C32, step = #C32>
builtin.module {{
  func.func @block_alias_write_case(
      %out : !nn.memory<[#C8, #C16], [#C16, #symbol.expr<1>], f32, #nn.space<tsm>>,
      %lhs : !nn.memory<[#C8, #C32], [#C32, #symbol.expr<1>], f32, #nn.space<tsm>>,
      %rhs : !nn.memory<[#C32, #C16], [#C16, #symbol.expr<1>], f32, #nn.space<tsm>>) {{
    %c0 = symbol.const 0 : !symbol.int<#C0>
    %c32 = symbol.const 32 : !symbol.int<#C32>
    %c128 = symbol.const 128 : !symbol.int<#C128>
    %zero = arith.constant 0.000000e+00 : f32
    "dma.fill"(%out, %zero) : (!nn.memory<[#C8, #C16], [#C16, #symbol.expr<1>], f32, #nn.space<tsm>>, f32) -> ()
    %alias = "dma.reshape"(%out, %c128) <{{operandSegmentSizes = array<i32: 1, 1>}}> : (!nn.memory<[#C8, #C16], [#C16, #symbol.expr<1>], f32, #nn.space<tsm>>, !symbol.int<#C128>) -> !nn.memory<[#C128], [#symbol.expr<1>], f32, #nn.space<tsm>>
    "dma.fill"(%alias, %zero) : (!nn.memory<[#C128], [#symbol.expr<1>], f32, #nn.space<tsm>>, f32) -> ()
    symbol.for %k = %c0 to %c32 step %c32 {{iter = #ItK}} {{
      %acc = symbol.ne %k, %c0 : !symbol.iter<start = #C0, end = #C32, step = #C32>, !symbol.int<#C0> -> i1
      "kernel.matmul_fusion"(%out, %lhs, %rhs, %acc) {{fusion_list = "kernel.matmul,kernel.binary_elewise.add", space = #nn.space<tsm>}} : (!nn.memory<[#C8, #C16], [#C16, #symbol.expr<1>], f32, #nn.space<tsm>>, !nn.memory<[#C8, #C32], [#C32, #symbol.expr<1>], f32, #nn.space<tsm>>, !nn.memory<[#C32, #C16], [#C16, #symbol.expr<1>], f32, #nn.space<tsm>>, i1) -> ()
    }}
    func.return
  }}
}}"""
    actual = _run_decompose_case("block_alias_write", case_text)
    assert actual.count('"dma.fill"') == 2
    assert '"kernel.matmul_fusion"' not in actual
    assert actual.count('"kernel.matmul"') == 1


def test_kernel_decompose_keeps_fill_when_loop_body_reads_out_before_fusion() -> None:
    """验证 loop body 内 fusion 前读取 out 时保留 initial fill。

    功能说明:
    - `kernel.binary_elewise` 在同一 `symbol.for` body 内先读取并写回 out。
    - 该读取发生在首轮 `kernel.matmul_fusion` 覆盖之前，initial fill 仍是语义输入。
    - pass 只能分解 fusion，不得删除 loop 外 `dma.fill(out, 0)`。

    使用示例:
    - pytest -q test/passes/kernel/test_kernel_decompose.py -k reads_out_before_fusion
    """

    case_text = f"""// COMPILE_ARGS: {_PASS}
#C0 = #symbol.expr<0>
#C32 = #symbol.expr<32>
#ItK = #symbol.iter<start = #C0, end = #C32, step = #C32>
builtin.module {{
  func.func @keep_fill_loop_body_read_case(
      %out : !nn.memory<[#symbol.expr<8>, #symbol.expr<16>], [#symbol.expr<16>, #symbol.expr<1>], f32, #nn.space<tsm>>,
      %lhs : !nn.memory<[#symbol.expr<8>, #symbol.expr<32>], [#symbol.expr<32>, #symbol.expr<1>], f32, #nn.space<tsm>>,
      %rhs : !nn.memory<[#symbol.expr<32>, #symbol.expr<16>], [#symbol.expr<16>, #symbol.expr<1>], f32, #nn.space<tsm>>) {{
    %c0 = symbol.const 0 : !symbol.int<#C0>
    %c32 = symbol.const 32 : !symbol.int<#C32>
    %zero = arith.constant 0.000000e+00 : f32
    "dma.fill"(%out, %zero) : (!nn.memory<[#symbol.expr<8>, #symbol.expr<16>], [#symbol.expr<16>, #symbol.expr<1>], f32, #nn.space<tsm>>, f32) -> ()
    symbol.for %k = %c0 to %c32 step %c32 {{iter = #ItK}} {{
      %acc = symbol.ne %k, %c0 : !symbol.iter<start = #C0, end = #C32, step = #C32>, !symbol.int<#C0> -> i1
      "kernel.binary_elewise"(%out, %out, %out) {{kind = "add", space = #nn.space<tsm>}} : (!nn.memory<[#symbol.expr<8>, #symbol.expr<16>], [#symbol.expr<16>, #symbol.expr<1>], f32, #nn.space<tsm>>, !nn.memory<[#symbol.expr<8>, #symbol.expr<16>], [#symbol.expr<16>, #symbol.expr<1>], f32, #nn.space<tsm>>, !nn.memory<[#symbol.expr<8>, #symbol.expr<16>], [#symbol.expr<16>, #symbol.expr<1>], f32, #nn.space<tsm>>) -> ()
      "kernel.matmul_fusion"(%out, %lhs, %rhs, %acc) {{fusion_list = "kernel.matmul,kernel.binary_elewise.add", space = #nn.space<tsm>}} : (!nn.memory<[#symbol.expr<8>, #symbol.expr<16>], [#symbol.expr<16>, #symbol.expr<1>], f32, #nn.space<tsm>>, !nn.memory<[#symbol.expr<8>, #symbol.expr<32>], [#symbol.expr<32>, #symbol.expr<1>], f32, #nn.space<tsm>>, !nn.memory<[#symbol.expr<32>, #symbol.expr<16>], [#symbol.expr<16>, #symbol.expr<1>], f32, #nn.space<tsm>>, i1) -> ()
    }}
    func.return
  }}
}}"""
    actual = _run_decompose_case("keep_fill_loop_body_read", case_text)
    assert '"dma.fill"' in actual
    assert '"kernel.binary_elewise"' in actual
    assert '"kernel.matmul_fusion"' not in actual
    assert actual.count('"kernel.matmul"') == 1


def test_kernel_decompose_keeps_fill_for_noncanonical_acc() -> None:
    """验证 acc 无法证明首轮覆盖时保留 fill。

    功能说明:
    - fusion acc 来自函数参数而非 `symbol.ne(k_iter,k_start)`。
    - pass 只能分解 fusion，不得删除 initial fill。

    使用示例:
    - pytest -q test/passes/kernel/test_kernel_decompose.py -k noncanonical_acc
    """

    case_text = f"""// COMPILE_ARGS: {_PASS}
#C0 = #symbol.expr<0>
#C32 = #symbol.expr<32>
#ItK = #symbol.iter<start = #C0, end = #C32, step = #C32>
builtin.module {{
  func.func @keep_fill_case(
      %out : !nn.memory<[#symbol.expr<8>, #symbol.expr<16>], [#symbol.expr<16>, #symbol.expr<1>], f32, #nn.space<tsm>>,
      %lhs : !nn.memory<[#symbol.expr<8>, #symbol.expr<32>], [#symbol.expr<32>, #symbol.expr<1>], f32, #nn.space<tsm>>,
      %rhs : !nn.memory<[#symbol.expr<32>, #symbol.expr<16>], [#symbol.expr<16>, #symbol.expr<1>], f32, #nn.space<tsm>>,
      %acc : i1) {{
    %c0 = symbol.const 0 : !symbol.int<#C0>
    %c32 = symbol.const 32 : !symbol.int<#C32>
    %zero = arith.constant 0.000000e+00 : f32
    "dma.fill"(%out, %zero) : (!nn.memory<[#symbol.expr<8>, #symbol.expr<16>], [#symbol.expr<16>, #symbol.expr<1>], f32, #nn.space<tsm>>, f32) -> ()
    symbol.for %k = %c0 to %c32 step %c32 {{iter = #ItK}} {{
      "kernel.matmul_fusion"(%out, %lhs, %rhs, %acc) {{fusion_list = "kernel.matmul,kernel.binary_elewise.add", space = #nn.space<tsm>}} : (!nn.memory<[#symbol.expr<8>, #symbol.expr<16>], [#symbol.expr<16>, #symbol.expr<1>], f32, #nn.space<tsm>>, !nn.memory<[#symbol.expr<8>, #symbol.expr<32>], [#symbol.expr<32>, #symbol.expr<1>], f32, #nn.space<tsm>>, !nn.memory<[#symbol.expr<32>, #symbol.expr<16>], [#symbol.expr<16>, #symbol.expr<1>], f32, #nn.space<tsm>>, i1) -> ()
    }}
    func.return
  }}
}}"""
    actual = _run_decompose_case("keep_fill_noncanonical_acc", case_text)
    assert '"dma.fill"' in actual
    assert '"kernel.matmul_fusion"' not in actual
    assert actual.count('"kernel.matmul"') == 1


def test_kernel_decompose_rejects_options() -> None:
    """验证 decompose pass 不接受专属 option。

    功能说明:
    - 通过公开 pass registry API 传入未知 option。
    - 错误短语必须包含 `kernel-decompose options`。

    使用示例:
    - pytest -q test/passes/kernel/test_kernel_decompose.py -k rejects_options
    """

    load_builtin_passes()
    try:
        build_registered_pass("kernel-decompose", {"mode": "fast"})
    except KernelCodeError as exc:
        message = str(exc)
    else:
        message = ""
    assert "kernel-decompose options" in message
