"""dsl_cost_run public tool tests.


功能说明:
- 覆盖 `dsl_cost_run(func, real_args, pipeline, cost_kind)` 的公开入口、成功路径与错误合同。
- `dsl_cost_run(...)` 调用只走 `kernel_gen.tools` 包根公开 API；缺 sibling 用例只用公开 `PassManager` 与公开 pass class 构造 pipeline，不直连 lowering 或 emit 的非公开 helper。

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

from kernel_gen.core.config import reset_config, set_dump_dir, set_target, set_trance_enabled
from kernel_gen.core.error import KernelCodeError
from kernel_gen.operation import slice, store
from kernel_gen.passes.attach_arch_information import AttachArchInformationPass
from kernel_gen.passes.decompass import DecompassPass
from kernel_gen.passes.inline import InlinePass
from kernel_gen.passes.lowering import NnLoweringPass
from kernel_gen.passes.outline_device_kernel import OutlineDeviceKernelPass
from kernel_gen.passes.pass_manager import PassManager
from kernel_gen.passes.symbol_buffer_hoist import SymbolBufferHoistPass
from kernel_gen.passes.symbol_loop_hoist import SymbolLoopHoistPass
from kernel_gen.passes.tile.analysis import TileAnalysisPass
from kernel_gen.symbol_variable.memory import MemorySpace
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
    - 复用 npu_demo lowering 的公开 pass 顺序，但刻意不追加 `LaunchKernelCostFuncPass`。
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


def unaligned_add_kernel(
    out: "Tensor[i32, 360]",
    lhs: "Tensor[i32, 360]",
    rhs: "Tensor[i32, 360]",
) -> None:
    """为 `dsl_cost_run(...)` 提供 DMA 聚合取整样例。


    功能说明:
    - 单个 kernel 内有两路 GM->TSM slice，单路 `360 * sizeof(i32)` 字节不能整除 64。
    - 用于验证 DMA1 返回值按同一 cost function 内总字节数取整，而不是逐节点取整后相加。

    使用示例:
    - cost = dsl_cost_run(unaligned_add_kernel, (out, lhs, rhs), "npu-demo-lowering", "DMA1")

    关联文件:
    - spec: [spec/tools/dsl_run.md](spec/tools/dsl_run.md)
    - test: [test/tools/test_dsl_cost_run.py](test/tools/test_dsl_cost_run.py)
    - 功能实现: [kernel_gen/tools/dsl_run.py](kernel_gen/tools/dsl_run.py)
    """

    lhs_tile = slice(lhs, [0], [360], [1], MemorySpace.TSM)
    rhs_tile = slice(rhs, [0], [360], [1], MemorySpace.TSM)
    store(out, lhs_tile + rhs_tile, [0], [360], [1])


def rank2_add_kernel(
    out: "Tensor[f64, 2, 5]",
    lhs: "Tensor[f64, 2, 5]",
    rhs: "Tensor[f64, 2, 5]",
) -> None:
    """为 `dsl_cost_run(...)` 提供 rank=2 写回编译样例。


    功能说明:
    - 通过公开 `slice(...)` 与 `store(...)` operation 构造二维 elewise kernel。
    - 用于锁定 npu_demo `dma.store` 多维 layout 参数发射为可编译形态。

    使用示例:
    - cost = dsl_cost_run(rank2_add_kernel, (out, lhs, rhs), "npu-demo-lowering", "DMA1")

    关联文件:
    - spec: [spec/tools/dsl_cost_run.md](spec/tools/dsl_cost_run.md)
    - test: [test/tools/test_dsl_cost_run.py](test/tools/test_dsl_cost_run.py)
    - 功能实现: [kernel_gen/dsl/gen_kernel/emit/npu_demo/dma/store.py](kernel_gen/dsl/gen_kernel/emit/npu_demo/dma/store.py)
    """

    lhs_tile = slice(lhs, [0, 0], [2, 5], [1, 1], MemorySpace.TSM)
    rhs_tile = slice(rhs, [0, 0], [2, 5], [1, 1], MemorySpace.TSM)
    store(out, lhs_tile + rhs_tile, [0, 0], [2, 5], [1, 1])


# TC-DSL-COST-RUN-001
# 功能说明: 验证 `dsl_cost_run(...)` 可通过公开入口返回 VECTOR1 成本。
# 使用示例: pytest -q test/tools/test_dsl_cost_run.py -k test_dsl_cost_run_returns_public_vector1_cost
# 对应功能实现文件路径: kernel_gen/tools/dsl_run.py
# 对应 spec 文件路径: spec/tools/dsl_run.md
# 对应测试文件路径: test/tools/test_dsl_cost_run.py
def test_dsl_cost_run_returns_public_vector1_cost() -> None:
    out = np.zeros((128,), dtype=np.int32)
    lhs = np.arange(128, dtype=np.int32)
    rhs = np.arange(128, dtype=np.int32)

    cost = dsl_cost_run(add_kernel, (out, lhs, rhs), "npu-demo-lowering", "VECTOR1")

    assert isinstance(cost, int)
    assert cost >= 2


# TC-DSL-COST-RUN-001A
# 功能说明: 验证 runtime trance 打开时 `dsl_cost_run(...)` 会记录 cost wrapper 返回值。
# 使用示例: pytest -q test/tools/test_dsl_cost_run.py -k test_dsl_cost_run_trance_logs_return_value
# 对应功能实现文件路径: kernel_gen/tools/dsl_run.py
# 对应 spec 文件路径: spec/tools/dsl_run.md
# 对应测试文件路径: test/tools/test_dsl_cost_run.py
def test_dsl_cost_run_trance_logs_return_value(capfd: pytest.CaptureFixture[str]) -> None:
    out = np.zeros((128,), dtype=np.int32)
    lhs = np.arange(128, dtype=np.int32)
    rhs = np.arange(128, dtype=np.int32)

    set_trance_enabled(True)
    cost = dsl_cost_run(add_kernel, (out, lhs, rhs), "npu-demo-lowering", "VECTOR1")
    captured = capfd.readouterr()

    assert isinstance(cost, int)
    assert f"return = {cost}" in captured.out


# TC-DSL-COST-RUN-002
# 功能说明: 验证 DMA1/DMA2 在公开入口按匹配 DMA 总字节数统一取整。
# 使用示例: pytest -q test/tools/test_dsl_cost_run.py -k test_dsl_cost_run_returns_dma1_aggregate_cost
# 对应功能实现文件路径: kernel_gen/tools/dsl_run.py
# 对应 spec 文件路径: spec/tools/dsl_run.md
# 对应测试文件路径: test/tools/test_dsl_cost_run.py
def test_dsl_cost_run_returns_dma1_aggregate_cost() -> None:
    out = np.zeros((360,), dtype=np.int32)
    lhs = np.arange(360, dtype=np.int32)
    rhs = np.arange(360, dtype=np.int32)

    dma1_cost = dsl_cost_run(unaligned_add_kernel, (out, lhs, rhs), "npu-demo-lowering", "DMA1")
    dma2_cost = dsl_cost_run(unaligned_add_kernel, (out, lhs, rhs), "npu-demo-lowering", "DMA2")

    assert dma1_cost == 45
    assert dma2_cost == 23


# TC-DSL-COST-RUN-002A
# 功能说明: 验证 DMA 聚合源码不跨文件调用 npu_demo::cost::detail 非公开 helper。
# 使用示例: pytest -q test/tools/test_dsl_cost_run.py -k test_dsl_cost_run_dma_source_avoids_non_public_detail_helpers
# 对应功能实现文件路径: kernel_gen/tools/dsl_run.py
# 对应 spec 文件路径: spec/tools/dsl_run.md
# 对应测试文件路径: test/tools/test_dsl_cost_run.py
def test_dsl_cost_run_dma_source_avoids_non_public_detail_helpers(tmp_path: Path) -> None:
    set_dump_dir(tmp_path)
    out = np.zeros((360,), dtype=np.int32)
    lhs = np.arange(360, dtype=np.int32)
    rhs = np.arange(360, dtype=np.int32)

    cost = dsl_cost_run(unaligned_add_kernel, (out, lhs, rhs), "npu-demo-lowering", "DMA1")
    cost_sources = tuple(tmp_path.rglob("99-cost-source.cpp"))

    assert cost == 45
    assert len(cost_sources) == 1
    cost_source = cost_sources[0].read_text(encoding="utf-8")
    assert "npu_demo::cost::detail" not in cost_source
    assert "reset_dma_cost_accumulator" not in cost_source
    assert "finalize_dma_cost_accumulator" not in cost_source


# TC-DSL-COST-RUN-002B
# 功能说明: 验证 rank=2 `store(...)` 写回可通过 `dsl_cost_run(...)` 编译执行，且不再发射裸 `{..}` layout。
# 使用示例: pytest -q test/tools/test_dsl_cost_run.py -k test_dsl_cost_run_compiles_rank2_store_vector_layout
# 对应功能实现文件路径: kernel_gen/dsl/gen_kernel/emit/npu_demo/dma/store.py
# 对应 spec 文件路径: spec/tools/dsl_cost_run.md
# 对应测试文件路径: test/tools/test_dsl_cost_run.py
def test_dsl_cost_run_compiles_rank2_store_vector_layout(tmp_path: Path) -> None:
    set_dump_dir(tmp_path)
    out = np.zeros((2, 5), dtype=np.float64)
    lhs = np.arange(10, dtype=np.float64).reshape(2, 5)
    rhs = np.arange(10, dtype=np.float64).reshape(2, 5)

    dma1_cost = dsl_cost_run(rank2_add_kernel, (out, lhs, rhs), "npu-demo-lowering", "DMA1")
    dma2_cost = dsl_cost_run(rank2_add_kernel, (out, lhs, rhs), "npu-demo-lowering", "DMA2")
    cost_sources = tuple(tmp_path.rglob("99-cost-source.cpp"))

    assert dma1_cost == 3
    assert dma2_cost == 2
    assert cost_sources
    source_text = "\n".join(path.read_text(encoding="utf-8") for path in cost_sources)
    store_lines = [line for line in source_text.splitlines() if "store<GM, TSM, double, double>" in line]
    assert store_lines
    for store_line in store_lines:
        assert "{0, 0}" not in store_line
        assert "{2, 5}" not in store_line
        assert "{1, 1}" not in store_line


# TC-DSL-COST-RUN-003
# 功能说明: 验证当前 VECTOR2 保留 kind 在公开入口返回 0。
# 使用示例: pytest -q test/tools/test_dsl_cost_run.py -k test_dsl_cost_run_returns_zero_for_vector2_reserved_kind
# 对应功能实现文件路径: kernel_gen/tools/dsl_run.py
# 对应 spec 文件路径: spec/tools/dsl_run.md
# 对应测试文件路径: test/tools/test_dsl_cost_run.py
def test_dsl_cost_run_returns_zero_for_vector2_reserved_kind() -> None:
    out = np.zeros((128,), dtype=np.int32)
    lhs = np.arange(128, dtype=np.int32)
    rhs = np.arange(128, dtype=np.int32)

    cost = dsl_cost_run(add_kernel, (out, lhs, rhs), "npu-demo-lowering", "VECTOR2")

    assert cost == 0


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


# TC-DSL-COST-RUN-007
# 功能说明: 验证 `dsl_cost_run(...)` 接受 numpy.ndarray 与 torch.Tensor 混用的公开运行参数。
# 使用示例: pytest -q test/tools/test_dsl_cost_run.py -k test_dsl_cost_run_accepts_numpy_torch_mixed_real_args
# 对应功能实现文件路径: kernel_gen/tools/dsl_run.py
# 对应 spec 文件路径: spec/tools/dsl_cost_run.md
# 对应测试文件路径: test/tools/test_dsl_cost_run.py
def test_dsl_cost_run_accepts_numpy_torch_mixed_real_args() -> None:
    out = torch.empty((128,), dtype=torch.int32)
    lhs = np.arange(128, dtype=np.int32)
    rhs = torch.arange(128, dtype=torch.int32)

    cost = dsl_cost_run(add_kernel, (out, lhs, rhs), "npu-demo-lowering", "VECTOR1")

    assert isinstance(cost, int)
    assert cost >= 2
