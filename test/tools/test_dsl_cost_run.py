"""dsl_cost_run public tool tests.


功能说明:
- 覆盖 `dsl_cost_run(func, real_args, pipeline, cost_kind)` 的公开入口、cost mode 正向执行、参数校验与错误合同。
- 当前入口不再查找 `_cost_<kind>_*` sibling，而是通过 `codegen_mode="cost"` 生成 cost host 并捕获 summary string。

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
from types import SimpleNamespace

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

from kernel_gen.core.config import get_codegen_mode, reset_config, set_codegen_mode, set_dump_dir, set_target
from kernel_gen.core.error import ErrorKind, ErrorModule, KernelCodeError
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
    """构造不生成旧 cost sibling 的公开 `PassManager` 链路。


    功能说明:
    - 复用 npu_demo lowering 的公开 pass 顺序，但不生成 `_cost_<kind>_*` sibling。
    - 用于验证 `dsl_cost_run(...)` 已不依赖旧 sibling。

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


class _FakeSummaryCompiledKernel:
    """为 summary 负向测试提供公开 execute 形态的最小 fake。"""

    def __init__(self, summary_text: str) -> None:
        """保存待返回的 summary 文本。

        功能说明:
        - 只服务当前测试文件的公开 `dsl_cost_run(...)` summary 负例。

        使用示例:
        - kernel = _FakeSummaryCompiledKernel("")
        """

        self.summary_text = summary_text

    def execute(self, args: tuple[object, ...], capture_function_output: bool = False) -> SimpleNamespace:
        """返回由测试配置的 captured summary 文本。

        功能说明:
        - 模拟 `CompiledKernel.execute(..., capture_function_output=True)` 的成功返回。

        使用示例:
        - result = kernel.execute(args=(out, lhs, rhs), capture_function_output=True)
        """

        assert len(args) == 3
        assert capture_function_output is True
        return SimpleNamespace(ok=True, run_stdout=self.summary_text)


class _FakeCaptureFailureCompiledKernel:
    """为 generated cost helper status 负例模拟 execute capture 失败。"""

    def execute(self, args: tuple[object, ...], capture_function_output: bool = False) -> SimpleNamespace:
        """抛出 execute_engine runtime failure，验证 `dsl_cost_run(...)` 的公开错误映射。

        功能说明:
        - 模拟 generated cost host 抛出 `kg_cost_unsupported` 后 capture companion 返回失败。

        使用示例:
        - kernel.execute(args=(out, lhs, rhs), capture_function_output=True)
        """

        assert len(args) == 3
        assert capture_function_output is True
        error = KernelCodeError(ErrorKind.CONTRACT, ErrorModule.EXECUTE_ENGINE, "runtime_throw_or_abort")
        error.failure_phrase = "runtime_throw_or_abort"
        raise error


class _FakeSummaryExecutionEngine:
    """为 `dsl_cost_run(...)` summary 解析负例替代真实编译执行。"""

    summary_text = ""

    def __init__(self, target: str) -> None:
        """校验目标为 npu_demo。

        功能说明:
        - 保留 `ExecutionEngine(target=...)` 的公开构造形态。

        使用示例:
        - engine = _FakeSummaryExecutionEngine("npu_demo")
        """

        assert target == "npu_demo"

    def compile(self, source: str, function: str) -> _FakeSummaryCompiledKernel:
        """验证 cost source 已生成，并返回固定 summary 的 fake kernel。

        功能说明:
        - 模拟 `ExecutionEngine.compile(...)`，确保 `dsl_cost_run(...)` 仍走真实 source 生成。

        使用示例:
        - kernel = engine.compile(source=source, function="add_kernel_cost")
        """

        assert "std::string& __kg_cost_summary" in source
        assert function.endswith("_cost")
        return _FakeSummaryCompiledKernel(self.summary_text)


class _FakeCaptureFailureExecutionEngine:
    """验证 generated cost source 带 helper status check 后模拟 capture 失败。"""

    def __init__(self, target: str) -> None:
        """校验目标为 npu_demo。

        功能说明:
        - 保留 `ExecutionEngine(target=...)` 的公开构造形态。

        使用示例:
        - engine = _FakeCaptureFailureExecutionEngine("npu_demo")
        """

        assert target == "npu_demo"

    def compile(self, source: str, function: str) -> _FakeCaptureFailureCompiledKernel:
        """断言 cost source 检查 helper 与 launch status，再返回 capture 失败 fake。

        功能说明:
        - 防止生成器忽略 `StatusCode::kError` 后继续格式化合法 0 summary。

        使用示例:
        - kernel = engine.compile(source=source, function="add_kernel_cost")
        """

        assert "std::string& __kg_cost_summary" in source
        assert function.endswith("_cost")
        assert "if (add<" in source
        assert "if (store<" in source
        assert "Status __kg_cost_status = npu_demo::launch" in source
        assert 'throw std::runtime_error("kg_cost_unsupported");' in source
        return _FakeCaptureFailureCompiledKernel()


# TC-DSL-COST-RUN-001
# 功能说明: 验证命名 npu-demo pipeline 通过 cost mode summary capture 返回 VECTOR1 成本。
# 使用示例: pytest -q test/tools/test_dsl_cost_run.py -k test_dsl_cost_run_named_pipeline_returns_vector1_cost
# 对应功能实现文件路径: kernel_gen/tools/dsl_run.py
# 对应 spec 文件路径: spec/tools/dsl_run.md
# 对应测试文件路径: test/tools/test_dsl_cost_run.py
def test_dsl_cost_run_named_pipeline_returns_vector1_cost() -> None:
    out = np.full((128,), -1, dtype=np.int32)
    original_out = out.copy()
    lhs = np.arange(128, dtype=np.int32)
    rhs = np.arange(128, dtype=np.int32)

    set_codegen_mode("cost")
    cost = dsl_cost_run(add_kernel, (out, lhs, rhs), "npu-demo-lowering", "VECTOR1")

    assert cost == 128
    assert np.array_equal(out, original_out)
    assert get_codegen_mode() == "cost"


# TC-DSL-COST-RUN-004
# 功能说明: 验证非 exact kind 与旧 DMA 聚合 kind 均被 `dsl_cost_run(...)` 拒绝。
# 使用示例: pytest -q test/tools/test_dsl_cost_run.py -k test_dsl_cost_run_rejects_old_cost_kind
# 对应功能实现文件路径: kernel_gen/tools/dsl_run.py
# 对应 spec 文件路径: spec/tools/dsl_run.md
# 对应测试文件路径: test/tools/test_dsl_cost_run.py
def test_dsl_cost_run_rejects_old_cost_kind() -> None:
    out = np.zeros((128,), dtype=np.int32)
    lhs = np.arange(128, dtype=np.int32)
    rhs = np.arange(128, dtype=np.int32)

    for invalid_kind in ("compute", "DMA"):
        with pytest.raises(
            KernelCodeError,
            match=(
                r"^DslCostRunInvalidCostKind: cost_kind must be one of "
                r"\['DMA1', 'DMA2', 'DMA3', 'DMA4', 'MAC', 'VECTOR1', 'VECTOR2'\]$"
            ),
        ):
            dsl_cost_run(add_kernel, (out, lhs, rhs), "npu-demo-lowering", invalid_kind)


# TC-DSL-COST-RUN-005
# 功能说明: 验证自定义公开 pipeline 不生成旧 cost sibling 时仍通过 cost mode 正向执行。
# 使用示例: pytest -q test/tools/test_dsl_cost_run.py -k test_dsl_cost_run_custom_pipeline_returns_cost_without_sibling
# 对应功能实现文件路径: kernel_gen/tools/dsl_run.py
# 对应 spec 文件路径: spec/tools/dsl_cost_run.md
# 对应测试文件路径: test/tools/test_dsl_cost_run.py
def test_dsl_cost_run_custom_pipeline_returns_cost_without_sibling() -> None:
    out = np.full((128,), -1, dtype=np.int32)
    original_out = out.copy()
    lhs = np.arange(128, dtype=np.int32)
    rhs = np.arange(128, dtype=np.int32)

    cost = dsl_cost_run(add_kernel, (out, lhs, rhs), _build_npu_demo_no_cost_pipeline(), "VECTOR1")

    assert cost == 128
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
# 功能说明: 验证 `dsl_cost_run(...)` 仍接受 numpy.ndarray 与 torch.Tensor 混用参数并正向返回成本。
# 使用示例: pytest -q test/tools/test_dsl_cost_run.py -k test_dsl_cost_run_accepts_numpy_torch_mixed_real_args
# 对应功能实现文件路径: kernel_gen/tools/dsl_run.py
# 对应 spec 文件路径: spec/tools/dsl_cost_run.md
# 对应测试文件路径: test/tools/test_dsl_cost_run.py
def test_dsl_cost_run_accepts_numpy_torch_mixed_real_args() -> None:
    out = torch.empty((128,), dtype=torch.int32)
    original_out = out.clone()
    lhs = np.arange(128, dtype=np.int32)
    rhs = torch.arange(128, dtype=torch.int32)

    cost = dsl_cost_run(add_kernel, (out, lhs, rhs), "npu-demo-lowering", "VECTOR1")

    assert cost == 128
    assert torch.equal(out, original_out)


@pytest.mark.parametrize("alpha", (1.25, np.float32(2.5)))
def test_dsl_cost_run_accepts_float_runtime_scalar(alpha: float | np.floating) -> None:
    """普通 float / numpy floating 必须通过 real_args 绑定，并按 cost mode 正向返回。"""

    out = np.full((128,), -1, dtype=np.int32)
    original_out = out.copy()
    lhs = np.arange(128, dtype=np.int32)
    rhs = np.arange(128, dtype=np.int32)

    cost = dsl_cost_run(_add_with_runtime_float_kernel, (out, lhs, rhs, alpha), "npu-demo-lowering", "VECTOR1")

    assert cost == 128
    assert np.array_equal(out, original_out)


def test_dsl_cost_run_dump_writes_cost_source_and_no_old_sibling(tmp_path: Path) -> None:
    """dump 模式写出 cost mode source，且不残留旧 sibling / tuner.cost 主路径。"""

    out = np.full((128,), -1, dtype=np.int32)
    lhs = np.arange(128, dtype=np.int32)
    rhs = np.arange(128, dtype=np.int32)

    set_dump_dir(tmp_path)
    cost = dsl_cost_run(add_kernel, (out, lhs, rhs), "npu-demo-lowering", "VECTOR1")
    source_path = tmp_path / "add_kernel" / "99-cost-source.cpp"
    source = source_path.read_text(encoding="utf-8")

    assert cost == 128
    assert source_path.is_file()
    assert "void add_kernel_cost(" in source
    assert "std::string& __kg_cost_summary" in source
    assert "npu_demo::CostContext ctx;" in source
    assert "npu_demo::format_cost_summary(ctx.summary())" in source
    assert "npu_demo::launch<2, 1, 1, 0" in source
    assert "_cost_VECTOR1_" not in source
    assert "_cost_DMA" not in source
    assert "tuner.cost" not in source
    assert "npu_demo::detail" not in source
    assert "* 2" not in source
    assert not (tmp_path / "add_kernel" / "trance").exists()


def test_dsl_cost_run_maps_unsupported_cost_helper_to_capture_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    """CostContext helper/layout 失败不得静默返回合法 0 summary。

    功能说明:
    - 验证 generated cost source 包含 helper / launch status fail-fast，并把 capture failure 映射为公开工具错误。

    使用示例:
    - pytest -q test/tools/test_dsl_cost_run.py -k unsupported_cost_helper
    """

    dsl_run_module = importlib.import_module("kernel_gen.tools.dsl_run")
    out = np.full((128,), -1, dtype=np.int32)
    original_out = out.copy()
    lhs = np.arange(128, dtype=np.int32)
    rhs = np.arange(128, dtype=np.int32)

    monkeypatch.setattr(dsl_run_module, "ExecutionEngine", _FakeCaptureFailureExecutionEngine)
    with pytest.raises(KernelCodeError, match=r"^DslCostRunExecutionFailed: cost summary capture failed$"):
        dsl_run_module.dsl_cost_run(add_kernel, (out, lhs, rhs), "npu-demo-lowering", "VECTOR1")

    assert np.array_equal(out, original_out)


@pytest.mark.parametrize(
    "summary_text",
    (
        "",
        "{not-json",
        '{"DMA1":0,"DMA2":0,"DMA3":0,"DMA4":0,"MAC":0,"VECTOR1":128}',
        '{"DMA1":0,"DMA2":0,"DMA3":0,"DMA4":0,"MAC":0,"VECTOR1":"128","VECTOR2":0}',
    ),
)
def test_dsl_cost_run_rejects_invalid_summary_capture(monkeypatch: pytest.MonkeyPatch, summary_text: str) -> None:
    """summary 空、非 JSON、缺 key 或非整数均映射为公开 cost capture 失败。

    功能说明:
    - 通过公开 `dsl_cost_run(...)` 链路验证非法 captured summary 不会返回静默 0 cost。

    使用示例:
    - pytest -q test/tools/test_dsl_cost_run.py -k invalid_summary_capture
    """

    dsl_run_module = importlib.import_module("kernel_gen.tools.dsl_run")
    _FakeSummaryExecutionEngine.summary_text = summary_text
    monkeypatch.setattr(dsl_run_module, "ExecutionEngine", _FakeSummaryExecutionEngine)

    out = np.zeros((128,), dtype=np.int32)
    lhs = np.arange(128, dtype=np.int32)
    rhs = np.arange(128, dtype=np.int32)

    with pytest.raises(KernelCodeError, match=r"^DslCostRunExecutionFailed: cost summary capture failed$"):
        dsl_run_module.dsl_cost_run(add_kernel, (out, lhs, rhs), "npu-demo-lowering", "VECTOR1")
