"""dsl_cost_run public tool tests.


功能说明:
- 覆盖 `dsl_cost_run(func, real_args, pipeline, cost_kind)` 的公开入口保留、参数校验与错误合同。
- `LaunchKernelCostFuncPass` 下线后，当前入口不再为命名 pipeline 自动生成 cost sibling；缺 sibling 用例只用公开 `PassManager` 与命名 pipeline 观察稳定失败，不直连 lowering 或 emit 的非公开 helper。

使用示例:
- pytest -q test/tools/test_dsl_cost_run.py

关联文件:
- spec: [spec/tools/dsl_run.md](spec/tools/dsl_run.md)
- 功能实现: [kernel_gen/tools/dsl_run.py](kernel_gen/tools/dsl_run.py)
- test: [test/tools/test_dsl_cost_run.py](test/tools/test_dsl_cost_run.py)
"""

from __future__ import annotations

import importlib
import sys
from pathlib import Path

import numpy as np
import pytest
from xdsl.transforms.common_subexpression_elimination import CommonSubexpressionElimination

try:
    import torch
except ImportError as exc:  # pragma: no cover - tests require torch
    raise RuntimeError("test/tools/test_dsl_cost_run.py requires torch") from exc


def _find_repo_root(start: Path) -> Path:
    """向上定位当前仓库根目录。


    功能说明:
    - 兼容 worktree 与主仓两种执行环境，优先返回包含 `spec/tools/dsl_run.md` 的最近祖先目录。

    使用示例:
    - repo_root = _find_repo_root(Path(__file__).resolve())

    关联文件:
    - spec: [spec/tools/dsl_run.md](spec/tools/dsl_run.md)
    - test: [test/tools/test_dsl_cost_run.py](test/tools/test_dsl_cost_run.py)
    - 功能实现: [test/tools/test_dsl_cost_run.py](test/tools/test_dsl_cost_run.py)
    """

    for candidate in (start, *start.parents):
        if (candidate / "spec/tools/dsl_run.md").is_file():
            return candidate
    raise FileNotFoundError("cannot locate spec/tools/dsl_run.md")


REPO_ROOT = _find_repo_root(Path(__file__).resolve().parents[2])
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from kernel_gen.core.config import reset_config, set_target
from kernel_gen.core.error import KernelCodeError
from kernel_gen.operation import store
from kernel_gen.passes.arch.attach_arch_information import AttachArchInformationPass
from kernel_gen.passes.decompass import DecompassPass
from kernel_gen.passes.inline import InlinePass
from kernel_gen.passes.lowering import NnLoweringPass
from kernel_gen.passes.tuning.outline_device_kernel import OutlineDeviceKernelPass
from kernel_gen.passes.pass_manager import PassManager
from kernel_gen.passes.hoist.symbol_buffer_hoist import SymbolBufferHoistPass
from kernel_gen.passes.hoist.symbol_loop_hoist import SymbolLoopHoistPass
from kernel_gen.passes.tile.analysis import TileAnalysisPass
from kernel_gen.target import registry as target_registry
from kernel_gen.tools import dsl_cost_run


@pytest.fixture(autouse=True)
def _isolated_npu_demo_target() -> None:
    """隔离 `dsl_cost_run` 测试期间的 target registry 全局状态。


    功能说明:
    - 通过公开 target registry 入口加载当前仓库默认 target 定义。
    - 测试结束后恢复默认配置，避免影响同进程后续用例。

    使用示例:
    - 由 pytest 自动应用，无需手动调用。

    关联文件:
    - spec: [spec/tools/dsl_run.md](spec/tools/dsl_run.md)
    - test: [test/tools/test_dsl_cost_run.py](test/tools/test_dsl_cost_run.py)
    - 功能实现: [kernel_gen/tools/dsl_run.py](kernel_gen/tools/dsl_run.py)
    """

    importlib.reload(target_registry)
    target_registry.load_targets(REPO_ROOT / "kernel_gen" / "target" / "targets")
    target_registry.set_current_target(None)
    reset_config()
    set_target("npu_demo")
    try:
        yield
    finally:
        reset_config()
        importlib.reload(target_registry)
        target_registry.load_targets(REPO_ROOT / "kernel_gen" / "target" / "targets")
        target_registry.set_current_target(None)


def _build_npu_demo_no_cost_pipeline() -> PassManager:
    """构造不生成 cost sibling 的公开 `PassManager` 链路。


    功能说明:
    - 复用 npu_demo lowering 的公开 pass 顺序，但不生成 `_cost_<kind>_*` sibling。
    - 用于验证 `dsl_cost_run(...)` 在缺少 `_cost_<kind>_*` sibling 时显式失败且不 fallback 到普通 kernel。

    使用示例:
    - pipeline = _build_npu_demo_no_cost_pipeline()

    关联文件:
    - spec: [spec/tools/dsl_cost_run.md](spec/tools/dsl_cost_run.md)
    - test: [test/tools/test_dsl_cost_run.py](test/tools/test_dsl_cost_run.py)
    - 功能实现: [kernel_gen/tools/dsl_run.py](kernel_gen/tools/dsl_run.py)
    """

    pipeline = PassManager(name="npu-demo-no-cost")
    pipeline.add_pass(InlinePass())
    pipeline.add_pass(CommonSubexpressionElimination())
    pipeline.add_pass(DecompassPass())
    pipeline.add_pass(NnLoweringPass())
    pipeline.add_pass(SymbolLoopHoistPass())
    pipeline.add_pass(CommonSubexpressionElimination())
    pipeline.add_pass(TileAnalysisPass())
    pipeline.add_pass(SymbolBufferHoistPass())
    pipeline.add_pass(AttachArchInformationPass(target="npu_demo"))
    pipeline.add_pass(OutlineDeviceKernelPass())
    return pipeline


def add_kernel(
    out: "Tensor[i32, 128]",
    lhs: "Tensor[i32, 128]",
    rhs: "Tensor[i32, 128]",
) -> None:
    """为 `dsl_cost_run(...)` 提供最小 add 样例。


    功能说明:
    - 通过公开 `store(...)` operation 写回结果，触发 npu_demo lowering 与 cost pass。

    使用示例:
    - cost = dsl_cost_run(add_kernel, (out, lhs, rhs), "npu-demo-lowering", "VECTOR1")

    关联文件:
    - spec: [spec/tools/dsl_run.md](spec/tools/dsl_run.md)
    - test: [test/tools/test_dsl_cost_run.py](test/tools/test_dsl_cost_run.py)
    - 功能实现: [kernel_gen/tools/dsl_run.py](kernel_gen/tools/dsl_run.py)
    """

    store(out, lhs + rhs, [0], [128], [1])


def _add_with_runtime_float_kernel(
    out: "Tensor[i32, 128]",
    lhs: "Tensor[i32, 128]",
    rhs: "Tensor[i32, 128]",
    alpha: float,
) -> None:
    """带 runtime float 参数的 add 样例，用于证明 dsl_cost_run 绑定层放行。"""

    alpha0 = alpha
    alpha1 = alpha0
    alpha2 = alpha1
    _alpha3 = alpha2
    store(out, lhs + rhs, [0], [128], [1])


# TC-DSL-COST-RUN-001
# 功能说明: 验证 LaunchKernelCostFuncPass 下线后，命名 npu-demo pipeline 不再自动生成 cost sibling。
# 使用示例: pytest -q test/tools/test_dsl_cost_run.py -k test_dsl_cost_run_named_pipeline_rejects_missing_cost_sibling
# 对应功能实现文件路径: kernel_gen/tools/dsl_run.py
# 对应 spec 文件路径: spec/tools/dsl_run.md
# 对应测试文件路径: test/tools/test_dsl_cost_run.py
def test_dsl_cost_run_named_pipeline_rejects_missing_cost_sibling() -> None:
    out = np.full((128,), -1, dtype=np.int32)
    original_out = out.copy()
    lhs = np.arange(128, dtype=np.int32)
    rhs = np.arange(128, dtype=np.int32)

    with pytest.raises(
        KernelCodeError,
        match=r"^DslCostRunMissingCostFunction: lowered module does not contain _cost_VECTOR1_ sibling function$",
    ):
        dsl_cost_run(add_kernel, (out, lhs, rhs), "npu-demo-lowering", "VECTOR1")

    assert np.array_equal(out, original_out)


# TC-DSL-COST-RUN-004
# 功能说明: 验证非工具公开 cost kind 仍被 `dsl_cost_run(...)` 拒绝。
# 使用示例: pytest -q test/tools/test_dsl_cost_run.py -k test_dsl_cost_run_rejects_old_cost_kind
# 对应功能实现文件路径: kernel_gen/tools/dsl_run.py
# 对应 spec 文件路径: spec/tools/dsl_run.md
# 对应测试文件路径: test/tools/test_dsl_cost_run.py
def test_dsl_cost_run_rejects_old_cost_kind() -> None:
    out = np.zeros((128,), dtype=np.int32)
    lhs = np.arange(128, dtype=np.int32)
    rhs = np.arange(128, dtype=np.int32)

    with pytest.raises(
        KernelCodeError,
        match=r"^DslCostRunInvalidCostKind: cost_kind must be one of \['DMA', 'MAC'\]$",
    ):
        dsl_cost_run(add_kernel, (out, lhs, rhs), "npu-demo-lowering", "compute")


# TC-DSL-COST-RUN-005
# 功能说明: 验证缺少目标 cost sibling 时公开入口显式失败且不 fallback 到普通 kernel。
# 使用示例: pytest -q test/tools/test_dsl_cost_run.py -k test_dsl_cost_run_rejects_missing_cost_sibling_without_fallback
# 对应功能实现文件路径: kernel_gen/tools/dsl_run.py
# 对应 spec 文件路径: spec/tools/dsl_cost_run.md
# 对应测试文件路径: test/tools/test_dsl_cost_run.py
def test_dsl_cost_run_rejects_missing_cost_sibling_without_fallback() -> None:
    out = np.full((128,), -1, dtype=np.int32)
    original_out = out.copy()
    lhs = np.arange(128, dtype=np.int32)
    rhs = np.arange(128, dtype=np.int32)

    with pytest.raises(
        KernelCodeError,
        match=r"^DslCostRunMissingCostFunction: lowered module does not contain _cost_VECTOR1_ sibling function$",
    ):
        dsl_cost_run(add_kernel, (out, lhs, rhs), _build_npu_demo_no_cost_pipeline(), "VECTOR1")

    assert np.array_equal(out, original_out)


# TC-DSL-COST-RUN-006
# 功能说明: 验证非 npu_demo target 会按 `dsl_cost_run(...)` 公开 target 合同失败。
# 使用示例: pytest -q test/tools/test_dsl_cost_run.py -k test_dsl_cost_run_rejects_non_npu_demo_target
# 对应功能实现文件路径: kernel_gen/tools/dsl_run.py
# 对应 spec 文件路径: spec/tools/dsl_cost_run.md
# 对应测试文件路径: test/tools/test_dsl_cost_run.py
def test_dsl_cost_run_rejects_non_npu_demo_target() -> None:
    out = np.zeros((128,), dtype=np.int32)
    lhs = np.arange(128, dtype=np.int32)
    rhs = np.arange(128, dtype=np.int32)

    set_target("cpu")
    with pytest.raises(
        KernelCodeError,
        match=r"^DslCostRunInvalidTarget: dsl_cost_run only supports target 'npu_demo'$",
    ):
        dsl_cost_run(add_kernel, (out, lhs, rhs), "npu-demo-lowering", "VECTOR1")


# TC-DSL-COST-RUN-004
# 功能说明: 验证 `dsl_cost_run(...)` 仍接受 numpy.ndarray 与 torch.Tensor 混用参数，并在当前无 cost sibling 阶段稳定失败。
# 使用示例: pytest -q test/tools/test_dsl_cost_run.py -k test_dsl_cost_run_accepts_numpy_torch_mixed_real_args_before_missing_sibling
# 对应功能实现文件路径: kernel_gen/tools/dsl_run.py
# 对应 spec 文件路径: spec/tools/dsl_cost_run.md
# 对应测试文件路径: test/tools/test_dsl_cost_run.py
def test_dsl_cost_run_accepts_numpy_torch_mixed_real_args_before_missing_sibling() -> None:
    out = torch.empty((128,), dtype=torch.int32)
    lhs = np.arange(128, dtype=np.int32)
    rhs = torch.arange(128, dtype=torch.int32)

    with pytest.raises(
        KernelCodeError,
        match=r"^DslCostRunMissingCostFunction: lowered module does not contain _cost_VECTOR1_ sibling function$",
    ):
        dsl_cost_run(add_kernel, (out, lhs, rhs), "npu-demo-lowering", "VECTOR1")


@pytest.mark.parametrize("alpha", (1.25, np.float32(2.5)))
def test_dsl_cost_run_accepts_float_runtime_scalar_before_missing_sibling(alpha: float | np.floating) -> None:
    """普通 float / numpy floating 必须先通过 real_args 绑定，再按缺 cost sibling 失败。"""

    out = np.full((128,), -1, dtype=np.int32)
    original_out = out.copy()
    lhs = np.arange(128, dtype=np.int32)
    rhs = np.arange(128, dtype=np.int32)

    with pytest.raises(KernelCodeError) as exc:
        dsl_cost_run(_add_with_runtime_float_kernel, (out, lhs, rhs, alpha), "npu-demo-lowering", "VECTOR1")

    message = str(exc.value)
    assert message == "DslCostRunMissingCostFunction: lowered module does not contain _cost_VECTOR1_ sibling function"
    assert "DslRunUnsupportedRealArg" not in message
    assert "DslRunInvalidTileValue" not in message
    assert np.array_equal(out, original_out)
