"""CUDA SM86 fail-fast boundary tests.

功能说明:
- 通过公开 `emit_c(...)` 入口验证 unsupported / name-only / spoofed-token final IR 稳定失败。
- 静态锁定实现不做运行时 SM 探测或 target 切换，runtime gate 在非 SM89 设备上 skip。

使用示例:
- pytest -q test/dsl/gen_kernel/emit/test_cuda_sm86_fail_fast.py

关联文件:
- 功能实现: kernel_gen/dsl/gen_kernel/emit/cuda_sm86/source_bundle.py
- 测试文件: test/cuda/test_cuda_sm86_kernel_demos_runtime.py
- 测试文件: test/dsl/gen_kernel/emit/test_cuda_sm86_fail_fast.py
"""

from __future__ import annotations

from pathlib import Path
import sys

import pytest
from xdsl.dialects import func
from xdsl.dialects.builtin import ArrayAttr, ModuleOp, StringAttr, f32
from xdsl.ir import Block, Region

REPO_ROOT = Path(__file__).resolve().parents[4]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from kernel_gen.core.config import reset_config, set_target
from kernel_gen.core.error import KernelCodeError
from kernel_gen.dialect.nn import NnMemorySpaceAttr, NnMemoryType
from kernel_gen.dialect.symbol import SymbolExprAttr
from kernel_gen.dsl.gen_kernel import EmitCContext, emit_c


def _make_name_only_module(name: str) -> ModuleOp:
    """构造只有函数名、没有 supported compute op 的 module。

    功能说明:
    - 返回包含一个空 `func.func` 的 `ModuleOp`。
    - 用于证明 CUDA backend 不使用函数名选择 generated source。
    - 测试只通过公开 `emit_c(...)` 观察 fail-fast 结果。

    使用示例:
    - module = _make_name_only_module("matmul_name_only_kernel")
    """

    block = Block(arg_types=[])
    block.add_op(func.ReturnOp())
    func_op = func.FuncOp(name, ([], []), Region(block))
    module = ModuleOp([func_op])
    return module


def _make_spoofed_string_token_module() -> ModuleOp:
    """构造仅靠属性文本伪造 kernel op token 的 module。

    功能说明:
    - 函数类型伪造成 matmul rank pattern，但函数体没有 lowered kernel op。
    - 属性文本包含 `kernel.matmul` / `arch.launch`，用于证明 backend 不读取 printed IR 字符串做 source 判定。
    - 测试只通过公开 `emit_c(...)` 观察 fail-fast 结果。

    使用示例:
    - module = _make_spoofed_string_token_module()
    """

    mem2d = NnMemoryType(
        ArrayAttr([SymbolExprAttr.from_expr("2"), SymbolExprAttr.from_expr("4")]),
        ArrayAttr([SymbolExprAttr.from_expr("4"), SymbolExprAttr.from_expr("1")]),
        f32,
        NnMemorySpaceAttr.from_name("global"),
    )
    block = Block(arg_types=[mem2d, mem2d, mem2d])
    block.add_op(func.ReturnOp())
    func_op = func.FuncOp("spoofed_tokens", ([mem2d, mem2d, mem2d], []), Region(block))
    func_op.attributes["fake_lowered_ops"] = StringAttr("kernel.matmul arch.launch")
    module = ModuleOp([func_op])
    return module


@pytest.fixture(autouse=True)
def _reset_core_config_fixture() -> None:
    """重置公开 target 配置。

    功能说明:
    - 每个测试前恢复默认配置，避免 target 状态从其它测试泄漏。
    - 每个测试后再次 reset，保证失败路径也不会污染后续用例。

    使用示例:
    - 由 pytest 自动应用。
    """

    reset_config()
    try:
        yield
    finally:
        reset_config()


def test_cuda_sm86_emit_fails_fast_for_name_only_modules() -> None:
    """验证 name-only module 不生成 CUDA SourceBundle。

    功能说明:
    - 输入函数名带 matmul / conv2d / flash_attention 字样但没有 supported compute op。
    - 通过公开 `emit_c(...)` 锁定稳定 `<none>` 失败文本。

    使用示例:
    - pytest -q test/dsl/gen_kernel/emit/test_cuda_sm86_fail_fast.py -k name_only
    """

    set_target("cuda_sm86")
    for name in ("matmul_name_only_kernel", "conv2d_name_only_kernel", "flash_attention_name_only_kernel"):
        with pytest.raises(KernelCodeError, match="unsupported cuda_sm86 final IR op: <none>"):
            emit_c(_make_name_only_module(name), EmitCContext())


def test_cuda_sm86_emit_fails_fast_for_spoofed_string_tokens() -> None:
    """验证 printed-token spoof 不生成 CUDA SourceBundle。

    功能说明:
    - 输入属性文本包含 supported kernel token，但真实 op sequence 不包含 compute op。
    - 通过公开 `emit_c(...)` 锁定 backend 必须读取真实 `Operation.name`。

    使用示例:
    - pytest -q test/dsl/gen_kernel/emit/test_cuda_sm86_fail_fast.py -k spoofed
    """

    set_target("cuda_sm86")
    with pytest.raises(KernelCodeError, match="unsupported cuda_sm86 final IR op: <none>"):
        emit_c(_make_spoofed_string_token_module(), EmitCContext())


def test_cuda_sm86_implementation_does_not_probe_or_switch_sm() -> None:
    """验证实现侧不做运行时 SM 探测或 target 切换。

    功能说明:
    - 只读取 CUDA SM86 implementation 相关文件，不读取任务记录或计划书文字。
    - 锁定 generated source、include 和 compile strategy 中没有设备属性探测或其它 SM flag。

    使用示例:
    - pytest -q test/dsl/gen_kernel/emit/test_cuda_sm86_fail_fast.py -k probe_or_switch
    """

    implementation_paths = (
        Path("kernel_gen/dsl/gen_kernel/emit/cuda_sm86/source_bundle.py"),
        Path("kernel_gen/dsl/gen_kernel/emit/cuda_sm86/runtime.py"),
        Path("kernel_gen/execute_engine/builtin_strategy/cuda_sm86.py"),
        Path("include/cuda_sm86/Arch.h"),
        Path("include/cuda_sm86/cuda_sm86.cuh"),
    )
    combined = "\n".join(path.read_text(encoding="utf-8") for path in implementation_paths)

    assert "cudaGet" + "DeviceProperties" not in combined
    assert "cudaDevice" + "GetAttribute" not in combined
    assert "-arch=sm_89" not in combined
    assert "-arch=sm_80" not in combined
    assert "-arch=sm_90" not in combined
    assert "target=\"npu_demo\"" not in combined
    assert "target='npu_demo'" not in combined
    assert "cu" + "blas" not in combined.lower()


def test_cuda_sm86_runtime_gate_requires_sm89_before_runtime_execution() -> None:
    """验证 runtime pytest gate 在非 SM89 环境下 skip。

    功能说明:
    - 静态核对 runtime 测试入口先查询 `nvidia-smi --query-gpu=compute_cap`。
    - 锁定缺少 SM89 device 时通过 `pytest.skip(...)` 停止，不进入 CUDA runtime execute。

    使用示例:
    - pytest -q test/dsl/gen_kernel/emit/test_cuda_sm86_fail_fast.py -k runtime_gate
    """

    runtime_test_source = Path("test/cuda/test_cuda_sm86_kernel_demos_runtime.py").read_text(encoding="utf-8")

    assert "--query-gpu=compute_cap" in runtime_test_source
    assert '"8.9" not in sm_versions' in runtime_test_source
    assert 'pytest.skip(f"SM89 CUDA device is not available; found {found}")' in runtime_test_source
    assert "_compile_cuda_demo_kernel(case)" in runtime_test_source
