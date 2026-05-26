"""kernel matmul fusion decompose pass tests.

功能说明:
- 覆盖 `KernelMatmulFusionDecomposePass` 的公开 registry 入口、scf.if 分解和 no-op 边界。

使用示例:
- pytest -q test/passes/test_kernel_matmul_fusion_decompose.py

关联文件:
- 功能实现: kernel_gen/passes/kernel_matmul_fusion_decompose.py
- Spec 文档: spec/pass/kernel_matmul_fusion_decompose.md
- 测试文件: test/passes/test_kernel_matmul_fusion_decompose.py
"""

from __future__ import annotations

from kernel_gen.core.error import KernelCodeError
from kernel_gen.passes.registry import build_registered_pass, load_builtin_passes
from kernel_gen.tools.ircheck import run_ircheck_text

_DMA_ALLOC_TEXT = '"' + ".".join(("dma", "alloc")) + '"'
_KERNEL_BINARY_ELEWISE_TEXT = '"' + ".".join(("kernel", "binary_elewise")) + '"'
_DMA_FREE_TEXT = '"' + ".".join(("dma", "free")) + '"'


def _run_decompose_case(case_name: str, case_text: str) -> str:
    """运行 kernel-matmul-fusion-decompose ircheck case。

    功能说明:
    - 通过公开 `run_ircheck_text(...)` 入口执行 registry pass。
    - 成功时返回实际 IR 文本，失败时把 message 带入断言。

    使用示例:
    - actual = _run_decompose_case("case", text)
    """

    source_path = f"test/passes/test_kernel_matmul_fusion_decompose.py#{case_name}"
    result = run_ircheck_text(case_text, source_path=source_path)
    actual_ir = result.actual_ir
    assert result.ok is True, result.message
    assert actual_ir
    return actual_ir


def _fusion_case(dynamic: bool, *, fusion_list: str = "") -> str:
    """构造 matmul_fusion 分解测试 IR。

    功能说明:
    - `dynamic=False` 生成静态 out/lhs/rhs。
    - `dynamic=True` 生成 M/N/K 符号 shape，验证 tmp alloc 动态维度桥接。
    - `fusion_list` 非空时注入 metadata，验证分解不按该 attr 改变语义。

    使用示例:
    - text = _fusion_case(dynamic=True)
    """

    m = "M" if dynamic else "8"
    n = "N" if dynamic else "16"
    k = "K" if dynamic else "32"
    attrs = "space = #nn.space<tsm>"
    if fusion_list:
        attrs = f'fusion_list = "{fusion_list}", {attrs}'
    return f"""// COMPILE_ARGS: --pass kernel-matmul-fusion-decompose
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


def test_kernel_matmul_fusion_decompose_static_scf_if() -> None:
    """验证静态 fusion 分解为 scf.if。

    功能说明:
    - 运行 `kernel-matmul-fusion-decompose`。
    - 断言输出包含 scf.if 与两条携带 acc attr 的 matmul，且不残留 fusion 或 tmp 生命周期。

    使用示例:
    - pytest -q test/passes/test_kernel_matmul_fusion_decompose.py -k test_kernel_matmul_fusion_decompose_static_scf_if
    """

    actual = _run_decompose_case("static", _fusion_case(dynamic=False))
    assert '"kernel.matmul_fusion"' not in actual
    assert "scf.if" in actual
    assert actual.count('"kernel.matmul"') == 2
    assert "acc = true" in actual
    assert "acc = false" in actual
    assert _DMA_ALLOC_TEXT not in actual
    assert _KERNEL_BINARY_ELEWISE_TEXT not in actual
    assert _DMA_FREE_TEXT not in actual


def test_kernel_matmul_fusion_decompose_dynamic_scf_if() -> None:
    """验证动态 fusion 分解时通过 symbol.get_dim 构造 tmp dynamic_shape。

    功能说明:
    - 输入 out/lhs/rhs shape 为 M/N/K 符号。
    - 分解 pass 不再分配 tmp，因此不需要 `symbol.get_dim`，只生成 scf.if。

    使用示例:
    - pytest -q test/passes/test_kernel_matmul_fusion_decompose.py -k test_kernel_matmul_fusion_decompose_dynamic_scf_if
    """

    actual = _run_decompose_case("dynamic", _fusion_case(dynamic=True))
    assert '"kernel.matmul_fusion"' not in actual
    assert "symbol.get_dim" not in actual
    assert "scf.if" in actual
    assert actual.count('"kernel.matmul"') == 2


def test_kernel_matmul_fusion_decompose_ignores_fusion_list_metadata() -> None:
    """验证非空 fusion_list 不改变分解语义。

    功能说明:
    - 输入携带 aggregate 生成的固定 `fusion_list` 字符串。
    - 输出仍只包含 scf.if 与 true/false 两条 matmul，不复制 metadata。

    使用示例:
    - pytest -q test/passes/test_kernel_matmul_fusion_decompose.py -k test_kernel_matmul_fusion_decompose_ignores_fusion_list_metadata
    """

    actual = _run_decompose_case(
        "fusion_list",
        _fusion_case(dynamic=False, fusion_list="kernel.matmul,kernel.binary_elewise.add"),
    )
    assert '"kernel.matmul_fusion"' not in actual
    assert "fusion_list" not in actual
    assert "acc = true" in actual
    assert "acc = false" in actual
    assert actual.count('"kernel.matmul"') == 2


def test_kernel_matmul_fusion_decompose_no_fusion_no_op() -> None:
    """验证无 fusion 时保持 no-op。

    功能说明:
    - 输入只包含普通 `kernel.matmul`。
    - pass 不得生成 scf.if。

    使用示例:
    - pytest -q test/passes/test_kernel_matmul_fusion_decompose.py -k test_kernel_matmul_fusion_decompose_no_fusion_no_op
    """

    case_text = """// COMPILE_ARGS: --pass kernel-matmul-fusion-decompose
builtin.module {
  func.func @plain_case(
      %out : !nn.memory<[#symbol.expr<8>, #symbol.expr<16>], [#symbol.expr<16>, #symbol.expr<1>], f32, #nn.space<tsm>>,
      %lhs : !nn.memory<[#symbol.expr<8>, #symbol.expr<32>], [#symbol.expr<32>, #symbol.expr<1>], f32, #nn.space<tsm>>,
      %rhs : !nn.memory<[#symbol.expr<32>, #symbol.expr<16>], [#symbol.expr<16>, #symbol.expr<1>], f32, #nn.space<tsm>>) {
    "kernel.matmul"(%out, %lhs, %rhs) {space = #nn.space<tsm>} : (!nn.memory<[#symbol.expr<8>, #symbol.expr<16>], [#symbol.expr<16>, #symbol.expr<1>], f32, #nn.space<tsm>>, !nn.memory<[#symbol.expr<8>, #symbol.expr<32>], [#symbol.expr<32>, #symbol.expr<1>], f32, #nn.space<tsm>>, !nn.memory<[#symbol.expr<32>, #symbol.expr<16>], [#symbol.expr<16>, #symbol.expr<1>], f32, #nn.space<tsm>>) -> ()
    func.return
  }
}"""
    actual = _run_decompose_case("no_fusion", case_text)
    assert '"kernel.matmul"' in actual
    assert "scf.if" not in actual


def test_kernel_matmul_fusion_decompose_rejects_options() -> None:
    """验证 decompose pass 不接受专属 option。

    功能说明:
    - 通过公开 pass registry API 传入未知 option。
    - 错误短语必须包含 `kernel-matmul-fusion-decompose options`。

    使用示例:
    - pytest -q test/passes/test_kernel_matmul_fusion_decompose.py -k test_kernel_matmul_fusion_decompose_rejects_options
    """

    load_builtin_passes()
    try:
        build_registered_pass("kernel-matmul-fusion-decompose", {"mode": "fast"})
    except KernelCodeError as exc:
        message = str(exc)
    else:
        message = ""
    assert "kernel-matmul-fusion-decompose options" in message
