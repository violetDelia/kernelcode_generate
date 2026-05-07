"""dsl_run tests.


功能说明:
- 覆盖 `dsl_run(func, real_args, pipeline)` 的正向执行、错误合同与结果模型口径。
- 同时锁定 `dsl_run` 对正向、反向与 tiled matmul 样例的行为。

使用示例:
- pytest -q test/tools/test_dsl_run.py

关联文件:
- spec: [spec/tools/dsl_run.md](spec/tools/dsl_run.md)
- 功能实现: [kernel_gen/tools/dsl_run.py](kernel_gen/tools/dsl_run.py)
- test: [test/tools/test_dsl_run.py](test/tools/test_dsl_run.py)
"""

from __future__ import annotations

import importlib
import sys
from pathlib import Path

import numpy as np
import pytest
from xdsl.dialects import func
from xdsl.dialects.builtin import FunctionType, ModuleOp
from xdsl.ir import Block, Region


def _find_repo_root(start: Path) -> Path:
    """向上定位当前仓库根目录。


    功能说明:
    - 兼容 worktree 与主仓两种执行环境，优先返回包含 `spec/tools/dsl_run.md` 的最近祖先目录。
    - 让合同检查始终指向当前主线实际落点，而不是写死某一级父目录。

    使用示例:
    - repo_root = _find_repo_root(Path(__file__).resolve().parents[2])

    关联文件:
    - spec: [spec/tools/dsl_run.md](spec/tools/dsl_run.md)
    - test: [test/tools/test_dsl_run.py](test/tools/test_dsl_run.py)
    - 功能实现: [kernel_gen/tools/dsl_run.py](kernel_gen/tools/dsl_run.py)
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
from kernel_gen.dialect.arch import ArchLaunchOp
from kernel_gen.dialect.symbol import SymbolConstOp
from kernel_gen.operation import deslice, loop, matmul, slice, store
from kernel_gen.passes.pass_manager import PassManager
from kernel_gen.passes.registry import build_registered_pipeline, load_builtin_passes
from kernel_gen.tools.dsl_run import DslRunResult, dsl_run
from kernel_gen.target import registry as target_registry
from kernel_gen.symbol_variable.memory import MemorySpace
from kernel_gen.symbol_variable.symbol_dim import SymbolDim

try:
    import torch
except ImportError as exc:  # pragma: no cover - tests require torch
    raise RuntimeError("test/tools/test_dsl_run.py requires torch") from exc


_EXPECTED_RETURN_VALUE_MESSAGE = "DslRunReturnValueUnsupported: dsl_run only supports functions without DSL return values"
_EXPECTED_TARGET_MESSAGE = "DslRunInvalidTarget: core config target must be non-empty str"
_EXPECTED_PIPELINE_NAME_MESSAGE = "DslRunUnknownPipeline: unknown pipeline 'missing-pipeline'"
_EXPECTED_PIPELINE_TYPE_MESSAGE = "DslRunInvalidPipeline: pipeline must be str or PassManager"
_EXPECTED_REAL_ARG_TYPE_MESSAGE = "DslRunUnsupportedRealArg: real_args only supports torch.Tensor, numpy.ndarray, int and float"
_EXPECTED_TILE_VALUE_MESSAGE = "DslRunInvalidTileValue: tile runtime scalar must be positive int"
_EXPECTED_ARITY_MESSAGE = "DslRunArityMismatch: real_args count does not match function signature"
_EXPECTED_NPU_DEMO_WRAPPER_MESSAGE = (
    "DslRunInternalError: lowered npu_demo module must contain exactly one wrapper func with arch.launch"
)

DslRunArray = torch.Tensor | np.ndarray


class _NonModulePipelineResult:
    """Sentinel result used to exercise public pipeline return validation."""


class _FallbackNamedCpuLaunchPipeline(PassManager):
    """自定义 pipeline：覆盖 `run(...)` 并返回最小 launch wrapper。"""

    name = ""

    def run(self, module: ModuleOp) -> ModuleOp:
        _ = module
        return _make_launch_only_module(callee="_device_kernel")


class _ClearingTargetPipeline(PassManager):
    """自定义 pipeline：模拟公开 pipeline 执行后 target 配置失效。"""

    def run(self, module: ModuleOp) -> ModuleOp:
        _ = module
        set_target("")
        return _make_launch_only_module(callee="_device_kernel")


class _NonModuleResultPipeline(PassManager):
    """自定义 pipeline：返回非 `ModuleOp` 以触发公开 pipeline 结果校验。"""

    def run(self, module: ModuleOp) -> _NonModulePipelineResult:
        _ = module
        return _NonModulePipelineResult()


@pytest.fixture(autouse=True)
def _isolated_target_registry() -> None:
    """隔离 `dsl_run` 测试期间的 target registry 全局状态。

    最后更改: 金铲铲大作战

    功能说明:
    - 通过 `importlib.reload(...)` 重置 registry 模块状态，再重新加载当前仓库的默认 target 定义。
    - 测试完成后再次 reload 并恢复默认目录加载，避免继续直连 registry 私有全局变量。

    使用示例:
    - 由 pytest 自动应用，无需手动调用。

    关联文件:
    - 功能实现: kernel_gen/target/registry.py
    - test: test/tools/test_dsl_run.py
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


def _build_npu_demo_lowering_pipeline() -> PassManager:
    """构造 `npu-demo-lowering` pipeline。

    最后更改: 朽木露琪亚

    功能说明:
    - 显式加载 builtin passes 后，再通过 registry 构造 `npu-demo-lowering` pipeline。
    - 便于测试同时覆盖字符串 pipeline 与现成 `PassManager` 两条入口。

    使用示例:
    - pipeline = _build_npu_demo_lowering_pipeline()

    关联文件:
    - spec: [spec/tools/dsl_run.md](spec/tools/dsl_run.md)
    - test: [test/tools/test_dsl_run.py](test/tools/test_dsl_run.py)
    - 功能实现: [kernel_gen/passes/registry.py](kernel_gen/passes/registry.py)
    """

    load_builtin_passes()
    pipeline = build_registered_pipeline("npu-demo-lowering")
    assert isinstance(pipeline, PassManager)
    return pipeline


def _make_launch_only_module(*, callee: str) -> ModuleOp:
    """构造只含单个 launch wrapper 的最小 lowered module。"""

    launch_block = func.Block(arg_types=[]) if hasattr(func, "Block") else Block(arg_types=[])
    launch_grid = SymbolConstOp(1)
    launch_thread = SymbolConstOp(1)
    launch_subthread = SymbolConstOp(1)
    launch_shared_memory = SymbolConstOp(0)
    launch_op = ArchLaunchOp(
        callee,
        launch_grid.result,
        launch_thread.result,
        launch_subthread.result,
        launch_shared_memory.result,
        (),
    )
    launch_block.add_ops([launch_grid, launch_thread, launch_subthread, launch_shared_memory, launch_op, func.ReturnOp()])
    launch_region = func.Region(launch_block) if hasattr(func, "Region") else Region(launch_block)
    wrapper = func.FuncOp("wrapper", FunctionType.from_lists([], []), launch_region)
    return ModuleOp([wrapper])


def add_kernel(
    out: "Tensor[i32, 6]",
    lhs: "Tensor[i32, 6]",
    rhs: "Tensor[i32, 6]",
) -> None:
    """最小 add 样例，仅通过显式 out 参数写回结果。

    最后更改: 朽木露琪亚

    功能说明:
    - 为 `dsl_run(...)` 提供最小正向样例。
    - 本函数不返回 DSL 值，只通过 `store(...)` 写入 `out`。

    使用示例:
    - `dsl_run(add_kernel, (out, lhs, rhs), "npu-demo-lowering")`

    关联文件:
    - spec: [spec/tools/dsl_run.md](spec/tools/dsl_run.md)
    - test: [test/tools/test_dsl_run.py](test/tools/test_dsl_run.py)
    - 功能实现: [kernel_gen/tools/dsl_run.py](kernel_gen/tools/dsl_run.py)
    """

    store(out, lhs + rhs, [0], [6], [1])


def return_add_kernel(
    lhs: "Tensor[i32, 6]",
    rhs: "Tensor[i32, 6]",
) -> "Tensor[i32, 6]":
    """非法样例：存在 DSL 值返回。"""

    return lhs + rhs


def add_slice_store_kernel(
    out: "Tensor[i32, 6]",
    lhs: "Tensor[i32, 6]",
    rhs: "Tensor[i32, 6]",
) -> None:
    """slice + store 风格的 add 样例。"""

    lhs_tile = slice(lhs, [1], [4], [1], MemorySpace.TSM)
    rhs_tile = slice(rhs, [1], [4], [1], MemorySpace.TSM)
    store(out, lhs_tile + rhs_tile, [1], [4], [1])


def add_for_loop_kernel(
    out: "Tensor[i32, 6]",
    lhs: "Tensor[i32, 6]",
    rhs: "Tensor[i32, 6]",
) -> None:
    """固定可整除 tile 的 for-loop add 样例。"""

    for index in loop(0, 6, 3):
        lhs_tile = slice(lhs, [index], [3], [1], MemorySpace.TSM)
        rhs_tile = slice(rhs, [index], [3], [1], MemorySpace.TSM)
        store(out, lhs_tile + rhs_tile, [index], [3], [1])


def add_dynamic_tile_kernel(
    out: "Tensor[i32, 6]",
    lhs: "Tensor[i32, 6]",
    rhs: "Tensor[i32, 6]",
    tile_n: SymbolDim,
) -> None:
    """动态 tile runtime scalar 版本的 for-loop add 样例。"""

    for index in loop(0, 6, tile_n):
        cur_n = min(tile_n, 6 - index)
        lhs_tile = slice(lhs, [index], [cur_n], [1], MemorySpace.TSM)
        rhs_tile = slice(rhs, [index], [cur_n], [1], MemorySpace.TSM)
        store(out, lhs_tile + rhs_tile, [index], [cur_n], [1])


def sub_store_kernel(
    out: "Tensor[i32, 6]",
    lhs: "Tensor[i32, 6]",
    rhs: "Tensor[i32, 6]",
) -> None:
    """显式 out 参数版本的 sub 样例。"""

    store(out, lhs - rhs, [0], [6], [1])


def mul_store_kernel(
    out: "Tensor[i32, 6]",
    lhs: "Tensor[i32, 6]",
    rhs: "Tensor[i32, 6]",
) -> None:
    """显式 out 参数版本的 mul 样例。"""

    store(out, lhs * rhs, [0], [6], [1])


def matmul_out_kernel(
    out: "Tensor[f32, 32, 32]",
    lhs: "Tensor[f32, 32, 16]",
    rhs: "Tensor[f32, 16, 32]",
) -> None:
    """tiled matmul out-param 样例。"""

    for m0 in loop(0, 32, 16):
        for n0 in loop(0, 32, 16):
            lhs_tile = slice(lhs, [m0, 0], [16, 16], [1, 1], MemorySpace.TSM)
            rhs_tile = slice(rhs, [0, n0], [16, 16], [1, 1], MemorySpace.TSM)
            partial = matmul(lhs_tile, rhs_tile)
            deslice(out, partial, [m0, n0], [16, 16], [1, 1])


def _assert_result_contract(
    result: DslRunResult,
    out: DslRunArray,
    expected: DslRunArray,
    *,
    helper_snippet: str = "add<",
) -> None:
    """断言 `dsl_run(...)` 的最小公开结果合同。

    最后更改: 朽木露琪亚

    功能说明:
    - 锁定 `DslRunResult` 的字段可用性、执行成功标记与源码头部。
    - 同时验证显式 out 参数已经写回到期望结果。

    使用示例:
    - _assert_result_contract(result, out, expected)

    关联文件:
    - spec: [spec/tools/dsl_run.md](spec/tools/dsl_run.md)
    - test: [test/tools/test_dsl_run.py](test/tools/test_dsl_run.py)
    - 功能实现: [kernel_gen/tools/dsl_run.py](kernel_gen/tools/dsl_run.py)
    """

    for field_name in ("func_op", "module", "source", "compiled_kernel", "execute_result", "runtime_args"):
        assert hasattr(result, field_name), f"missing result field: {field_name}"

    assert result.func_op is not None
    assert result.module is not None
    assert callable(getattr(result.compiled_kernel, "execute", None))
    assert isinstance(result.runtime_args, tuple)
    assert len(result.runtime_args) == 3
    assert result.execute_result.ok is True
    assert result.execute_result.failure_phrase is None
    assert isinstance(result.source, str)
    assert result.source.startswith('#include "include/npu_demo/npu_demo.h"\n')
    assert helper_snippet in result.source
    assert not result.compiled_kernel.compile_stdout.startswith("dry-run: ")

    if isinstance(out, torch.Tensor):
        assert isinstance(expected, torch.Tensor)
        assert torch.equal(out, expected)
    else:
        assert isinstance(out, np.ndarray)
        assert isinstance(expected, np.ndarray)
        assert np.array_equal(out, expected)


# TC-DSL-RUN-001
# 测试目的: 锁定 dsl_run 的正向结果模型与字符串 pipeline 行为。
# 对应功能实现文件路径: kernel_gen/tools/dsl_run.py
# 对应 spec 文件路径: spec/tools/dsl_run.md
# 对应测试文件路径: test/tools/test_dsl_run.py
def test_dsl_run_string_pipeline_with_torch_numpy_mix() -> None:
    out = torch.empty((6,), dtype=torch.int32)
    lhs = torch.tensor([1, 2, 3, 4, 5, 6], dtype=torch.int32)
    rhs = np.array([6, 5, 4, 3, 2, 1], dtype=np.int32)
    expected = lhs + torch.from_numpy(rhs)

    result = dsl_run(
        add_kernel,
        (out, lhs, rhs),
        "npu-demo-lowering",
    )

    _assert_result_contract(result, out, expected)


# TC-DSL-RUN-001A
# 测试目的: 锁定 dump_dir 会按 kernel 名写入初始 IR、逐 pass IR 与最终源码。
# 对应功能实现文件路径: kernel_gen/tools/dsl_run.py
# 对应 spec 文件路径: spec/tools/dsl_run.md
# 对应测试文件路径: test/tools/test_dsl_run.py
def test_dsl_run_dump_dir_writes_pass_ir_and_source(tmp_path: Path) -> None:
    out = torch.empty((6,), dtype=torch.int32)
    lhs = torch.tensor([1, 2, 3, 4, 5, 6], dtype=torch.int32)
    rhs = np.array([6, 5, 4, 3, 2, 1], dtype=np.int32)

    set_dump_dir(tmp_path)
    result = dsl_run(
        add_kernel,
        (out, lhs, rhs),
        "npu-demo-lowering",
    )

    kernel_dump_dir = tmp_path / "add_kernel"
    assert result.execute_result.ok is True
    assert (kernel_dump_dir / "01-first-ir.mlir").is_file()
    first_ir_text = (kernel_dump_dir / "01-first-ir.mlir").read_text(encoding="utf-8")
    assert "#C" in first_ir_text
    assert "#symbol.expr<" not in first_ir_text.split("builtin.module", 1)[1]
    pass_dumps = sorted(path for path in kernel_dump_dir.glob("*.mlir") if path.name != "01-first-ir.mlir")
    assert pass_dumps
    pass_dump_text = pass_dumps[0].read_text(encoding="utf-8")
    assert pass_dump_text.splitlines()[0]
    assert "#symbol.expr<" not in pass_dump_text.split("builtin.module", 1)[1]
    source_text = (kernel_dump_dir / "source.cpp").read_text(encoding="utf-8")
    assert source_text == result.source + ("\n" if not result.source.endswith("\n") else "")
    assert '#include "include/npu_demo/npu_demo.h"' in source_text


# TC-DSL-RUN-001A1
# 测试目的: 锁定 runtime trance 无 dump_dir 时通过 stdout 输出 entry 与真实运行参数摘要。
# 对应功能实现文件路径: kernel_gen/tools/dsl_run.py
# 对应 spec 文件路径: spec/tools/dsl_run.md
# 对应测试文件路径: test/tools/test_dsl_run.py
def test_dsl_run_trance_stdout_logs_entry_and_runtime_args(capfd: pytest.CaptureFixture[str]) -> None:
    out = torch.empty((6,), dtype=torch.int32)
    lhs = torch.tensor([1, 2, 3, 4, 5, 6], dtype=torch.int32)
    rhs = np.array([6, 5, 4, 3, 2, 1], dtype=np.int32)

    set_trance_enabled(True)
    result = dsl_run(add_kernel, (out, lhs, rhs), "npu-demo-lowering")
    captured = capfd.readouterr()
    entry_name = result.func_op.sym_name.data

    assert result.execute_result.ok is True
    assert f"in func: {entry_name} template=<none>" in captured.out
    assert "args =" in captured.out
    assert "arg0 = mem[" in captured.out
    assert "[6] [1] i32 GM" in captured.out


# TC-DSL-RUN-001A2
# 测试目的: 锁定 runtime trance 有 dump_dir 时写入 kernel 子目录下的 trace 文件并覆盖旧内容。
# 对应功能实现文件路径: kernel_gen/tools/dsl_run.py
# 对应 spec 文件路径: spec/tools/dsl_run.md
# 对应测试文件路径: test/tools/test_dsl_run.py
def test_dsl_run_trance_dump_dir_writes_and_overwrites_trace_file(tmp_path: Path) -> None:
    out = torch.empty((6,), dtype=torch.int32)
    lhs = torch.tensor([1, 2, 3, 4, 5, 6], dtype=torch.int32)
    rhs = np.array([6, 5, 4, 3, 2, 1], dtype=np.int32)

    set_dump_dir(tmp_path)
    set_trance_enabled(True)
    result = dsl_run(add_kernel, (out, lhs, rhs), "npu-demo-lowering")
    trace_path = tmp_path / "add_kernel" / f"{result.func_op.sym_name.data}_trace.txt"
    trace_text = trace_path.read_text(encoding="utf-8")

    trace_path.write_text("stale\n", encoding="utf-8")
    out.fill_(0)
    result = dsl_run(add_kernel, (out, lhs, rhs), "npu-demo-lowering")
    overwritten_text = trace_path.read_text(encoding="utf-8")

    assert result.execute_result.ok is True
    assert "in func:" in trace_text
    assert "arg0 = mem[" in trace_text
    assert "stale" not in overwritten_text
    assert "in func:" in overwritten_text
    assert "arg0 = mem[" in overwritten_text


# TC-DSL-RUN-001B
# 测试目的: 锁定 dump_dir 为空字符串时不会写出诊断产物。
# 对应功能实现文件路径: kernel_gen/tools/dsl_run.py
# 对应 spec 文件路径: spec/tools/dsl_run.md
# 对应测试文件路径: test/tools/test_dsl_run.py
def test_dsl_run_empty_dump_dir_disables_dump(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    out = torch.empty((6,), dtype=torch.int32)
    lhs = torch.tensor([1, 2, 3, 4, 5, 6], dtype=torch.int32)
    rhs = np.array([6, 5, 4, 3, 2, 1], dtype=np.int32)

    monkeypatch.chdir(tmp_path)
    set_dump_dir("")
    result = dsl_run(
        add_kernel,
        (out, lhs, rhs),
        "npu-demo-lowering",
    )

    assert result.execute_result.ok is True
    assert not (tmp_path / "add_kernel").exists()


# TC-DSL-RUN-001C
# 测试目的: 锁定 dump_dir 非空且函数名为空时使用 `kernel` 作为诊断子目录名，不影响后续公开 arity 校验。
# 对应功能实现文件路径: kernel_gen/tools/dsl_run.py
# 对应 spec 文件路径: spec/tools/dsl_run.md
# 对应测试文件路径: test/tools/test_dsl_run.py
def test_dsl_run_empty_function_name_uses_kernel_dump_fallback(tmp_path: Path) -> None:
    original_name = add_kernel.__name__
    set_dump_dir(tmp_path)
    add_kernel.__name__ = ""
    try:
        with pytest.raises(KernelCodeError, match=_EXPECTED_ARITY_MESSAGE):
            dsl_run(add_kernel, (), "npu-demo-lowering")
    finally:
        add_kernel.__name__ = original_name


# TC-DSL-RUN-001D
# 测试目的: 锁定覆盖 `run(...)` 的自定义 PassManager 仍写入初始 IR 与粗粒度 pipeline dump。
# 对应功能实现文件路径: kernel_gen/tools/dsl_run.py
# 对应 spec 文件路径: spec/tools/dsl_run.md
# 对应测试文件路径: test/tools/test_dsl_run.py
def test_dsl_run_custom_pipeline_dump_uses_public_fallback_name(tmp_path: Path) -> None:
    out = torch.empty((6,), dtype=torch.int32)
    lhs = torch.tensor([1, 2, 3, 4, 5, 6], dtype=torch.int32)
    rhs = np.array([6, 5, 4, 3, 2, 1], dtype=np.int32)

    set_target("cpu")
    set_dump_dir(tmp_path)
    with pytest.raises(KernelCodeError, match=r"^target=cpu: arch\.launch: unsupported op$"):
        dsl_run(add_kernel, (out, lhs, rhs), _FallbackNamedCpuLaunchPipeline())

    dump_dir = tmp_path / "add_kernel"
    assert (dump_dir / "01-first-ir.mlir").is_file()
    first_ir_text = (dump_dir / "01-first-ir.mlir").read_text(encoding="utf-8")
    assert "#symbol.expr<" not in first_ir_text.split("builtin.module", 1)[1]
    pipeline_dump = dump_dir / "02-pipeline.mlir"
    assert pipeline_dump.is_file()
    pipeline_dump_text = pipeline_dump.read_text(encoding="utf-8")
    assert pipeline_dump_text.splitlines()[0] == "pipeline"
    assert "#symbol.expr<" not in pipeline_dump_text.split("builtin.module", 1)[1]


# TC-DSL-RUN-002
# 测试目的: 锁定 dsl_run 对现成 PassManager 的直接接受能力，并覆盖 list real_args。
# 对应功能实现文件路径: kernel_gen/tools/dsl_run.py
# 对应 spec 文件路径: spec/tools/dsl_run.md
# 对应测试文件路径: test/tools/test_dsl_run.py
def test_dsl_run_pass_manager_with_list_real_args() -> None:
    pipeline = _build_npu_demo_lowering_pipeline()
    out = torch.empty((6,), dtype=torch.int32)
    lhs = np.array([11, 12, 13, 14, 15, 16], dtype=np.int32)
    rhs = torch.tensor([1, 2, 3, 4, 5, 6], dtype=torch.int32)
    expected = torch.from_numpy(lhs) + rhs

    result = dsl_run(
        add_kernel,
        [out, lhs, rhs],
        pipeline,
    )

    _assert_result_contract(result, out, expected)


# TC-DSL-RUN-003
# 最后更改: 朽木露琪亚
# 测试目的: 锁定 dsl_run 对 numpy 输出位的支持。
# 对应功能实现文件路径: kernel_gen/tools/dsl_run.py
# 对应 spec 文件路径: spec/tools/dsl_run.md
# 对应测试文件路径: test/tools/test_dsl_run.py
def test_dsl_run_numpy_output() -> None:
    out = np.empty((6,), dtype=np.int32)
    lhs = torch.tensor([7, 8, 9, 10, 11, 12], dtype=torch.int32)
    rhs = np.array([12, 11, 10, 9, 8, 7], dtype=np.int32)
    expected = lhs.numpy() + rhs

    result = dsl_run(
        add_kernel,
        (out, lhs, rhs),
        "npu-demo-lowering",
    )

    _assert_result_contract(result, out, expected)


# TC-DSL-RUN-003A
# 最后更改: 朽木露琪亚
# 测试目的: 锁定 slice + store add 在 worktree 实现下可通过主线合同真实执行。
# 对应功能实现文件路径: kernel_gen/tools/dsl_run.py
# 对应 spec 文件路径: spec/tools/dsl_run.md
# 对应测试文件路径: test/tools/test_dsl_run.py
def test_dsl_run_add_slice_store_matches_public_contract() -> None:
    out = torch.full((6,), -99, dtype=torch.int32)
    lhs = torch.tensor([1, 2, 3, 4, 5, 6], dtype=torch.int32)
    rhs = np.array([6, 5, 4, 3, 2, 1], dtype=np.int32)
    expected = out.clone()
    expected[1:5] = lhs[1:5] + torch.from_numpy(rhs)[1:5]

    result = dsl_run(
        add_slice_store_kernel,
        (out, lhs, rhs),
        "npu-demo-lowering",
    )

    lowered_text = str(result.func_op)
    assert result.execute_result.ok is True
    assert result.execute_result.failure_phrase is None
    assert "#nn.space<tsm>" in lowered_text
    assert "kernel.binary_elewise" in lowered_text
    assert "kind = \"add\"" in lowered_text
    assert "slice(" in result.source
    _assert_result_contract(result, out, expected, helper_snippet="add<")


# TC-DSL-RUN-003A2
# 最后更改: 朽木露琪亚
# 测试目的: 锁定可整除 tile 的 for-loop add 在 worktree 实现下可通过主线合同真实执行。
# 对应功能实现文件路径: kernel_gen/tools/dsl_run.py
# 对应 spec 文件路径: spec/tools/dsl_run.md
# 对应测试文件路径: test/tools/test_dsl_run.py
def test_dsl_run_add_for_loop_matches_public_contract() -> None:
    out = torch.full((6,), -7, dtype=torch.int32)
    lhs = torch.tensor([10, 11, 12, 13, 14, 15], dtype=torch.int32)
    rhs = np.array([1, 2, 3, 4, 5, 6], dtype=np.int32)
    expected = lhs + torch.from_numpy(rhs)

    result = dsl_run(
        add_for_loop_kernel,
        (out, lhs, rhs),
        "npu-demo-lowering",
    )

    lowered_text = str(result.func_op)
    assert result.execute_result.ok is True
    assert result.execute_result.failure_phrase is None
    assert "#nn.space<tsm>" in lowered_text
    assert "symbol.for" in lowered_text
    assert "kernel.binary_elewise" in lowered_text
    assert "kind = \"add\"" in lowered_text
    _assert_result_contract(result, out, expected, helper_snippet="add<")


# TC-DSL-RUN-003A3
# 测试目的: 锁定 dsl_run 支持 int runtime scalar tile，并通过 DSL min 处理尾块。
# 对应功能实现文件路径: kernel_gen/tools/dsl_run.py
# 对应 spec 文件路径: spec/tools/dsl_run.md
# 对应测试文件路径: test/tools/test_dsl_run.py
def test_dsl_run_add_dynamic_tile_scalar_matches_public_contract() -> None:
    out = torch.full((6,), -7, dtype=torch.int32)
    lhs = torch.tensor([10, 11, 12, 13, 14, 15], dtype=torch.int32)
    rhs = np.array([1, 2, 3, 4, 5, 6], dtype=np.int32)
    expected = lhs + torch.from_numpy(rhs)

    result = dsl_run(
        add_dynamic_tile_kernel,
        (out, lhs, rhs, 4),
        "npu-demo-lowering",
    )

    lowered_text = str(result.func_op)
    assert result.execute_result.ok is True
    assert result.execute_result.failure_phrase is None
    assert isinstance(result.runtime_args, tuple)
    assert result.runtime_args[-1] == 4
    assert "symbol.min" in lowered_text
    assert "? " in result.source
    assert torch.equal(out, expected)


# TC-DSL-RUN-003B
# 最后更改: 朽木露琪亚
# 测试目的: 锁定 execute_engine/npu_demo/sub.py 的 lowering 与 compile/execute 公开合同在当前 worktree 下可直接复现。
# 对应功能实现文件路径: kernel_gen/tools/dsl_run.py
# 对应 spec 文件路径: spec/tools/dsl_run.md
# 对应测试文件路径: test/tools/test_dsl_run.py
def test_dsl_run_sub_matches_public_contract() -> None:
    out = torch.empty((6,), dtype=torch.int32)
    lhs = torch.tensor([10, 11, 12, 13, 14, 15], dtype=torch.int32)
    rhs = np.array([1, 2, 3, 4, 5, 6], dtype=np.int32)
    expected = lhs - torch.from_numpy(rhs)

    result = dsl_run(
        sub_store_kernel,
        (out, lhs, rhs),
        "npu-demo-lowering",
    )

    lowered_text = str(result.func_op)
    assert "kernel.binary_elewise" in lowered_text
    assert 'kind = "sub"' in lowered_text
    assert "nn.sub" not in lowered_text
    _assert_result_contract(result, out, expected, helper_snippet="sub<")


# TC-DSL-RUN-003C
# 最后更改: 朽木露琪亚
# 测试目的: 锁定 execute_engine/npu_demo/mul.py 的 lowering 与 compile/execute 公开合同在当前 worktree 下可直接复现。
# 对应功能实现文件路径: kernel_gen/tools/dsl_run.py
# 对应 spec 文件路径: spec/tools/dsl_run.md
# 对应测试文件路径: test/tools/test_dsl_run.py
def test_dsl_run_mul_matches_public_contract() -> None:
    out = torch.empty((6,), dtype=torch.int32)
    lhs = torch.tensor([1, 2, 3, 4, 5, 6], dtype=torch.int32)
    rhs = np.array([6, 5, 4, 3, 2, 1], dtype=np.int32)
    expected = lhs * torch.from_numpy(rhs)

    result = dsl_run(
        mul_store_kernel,
        (out, lhs, rhs),
        "npu-demo-lowering",
    )

    lowered_text = str(result.func_op)
    assert "kernel.binary_elewise" in lowered_text
    assert 'kind = "mul"' in lowered_text
    assert "nn.mul" not in lowered_text
    _assert_result_contract(result, out, expected, helper_snippet="mul<")


# TC-DSL-RUN-003F
# 最后更改: 朽木露琪亚
# 测试目的: 锁定 dsl_run + npu-demo-lowering 对 tiled matmul 合同的正向链路，覆盖 TSM、kernel.matmul、npu_demo 源码和真实执行结果。
# 对应功能实现文件路径: kernel_gen/tools/dsl_run.py
# 对应 spec 文件路径: spec/tools/dsl_run.md
# 对应测试文件路径: test/tools/test_dsl_run.py
def test_dsl_run_supports_tiled_matmul_kernel_on_npu_demo() -> None:
    out = torch.empty((32, 32), dtype=torch.float32)
    lhs = torch.arange(32 * 16, dtype=torch.float32).reshape(32, 16) / 17.0
    rhs = (np.arange(16 * 32, dtype=np.float32).reshape(16, 32) - 11.0) / 19.0
    expected = torch.matmul(lhs, torch.from_numpy(rhs))

    result = dsl_run(
        matmul_out_kernel,
        (out, lhs, rhs),
        "npu-demo-lowering",
    )

    lowered_text = str(result.func_op)
    assert result.execute_result.ok is True
    assert result.execute_result.failure_phrase is None
    assert not result.compiled_kernel.compile_stdout.startswith("dry-run: ")
    assert "#nn.space<tsm>" in lowered_text
    assert "#nn.space<shared>" not in lowered_text
    assert "kernel.matmul" in lowered_text
    assert "nn.matmul" not in lowered_text
    assert result.source.startswith('#include "include/npu_demo/npu_demo.h"\n')
    assert "matmul<" in result.source
    assert "cpu::matmul(" not in result.source
    assert result.source.count("for (") >= 2
    assert "slice(" in result.source
    assert "deslice(" in result.source
    assert isinstance(out, torch.Tensor)
    assert out.dtype == torch.float32
    assert out.shape == (32, 32)
    assert torch.allclose(out, expected, atol=1e-5, rtol=1e-5)


# TC-DSL-RUN-003G
# 测试目的: 锁定 npu_demo lowered module 在 wrapper 不唯一/缺失时必须显式失败，避免静默回退到首个普通 func.func。
# 对应功能实现文件路径: kernel_gen/tools/dsl_run.py
# 对应 spec 文件路径: spec/tools/dsl_run.md
# 对应测试文件路径: test/tools/test_dsl_run.py
def test_dsl_run_rejects_npu_demo_module_without_unique_wrapper() -> None:
    out = torch.empty((6,), dtype=torch.int32)
    lhs = torch.tensor([1, 2, 3, 4, 5, 6], dtype=torch.int32)
    rhs = np.array([6, 5, 4, 3, 2, 1], dtype=np.int32)

    with pytest.raises(KernelCodeError, match=_EXPECTED_NPU_DEMO_WRAPPER_MESSAGE):
        dsl_run(
            add_kernel,
            (out, lhs, rhs),
            PassManager(),
        )


# TC-DSL-RUN-004
# 最后更改: 朽木露琪亚
# 测试目的: 锁定 DSL 值返回函数的固定失败短语。
# 对应功能实现文件路径: kernel_gen/tools/dsl_run.py
# 对应 spec 文件路径: spec/tools/dsl_run.md
# 对应测试文件路径: test/tools/test_dsl_run.py
def test_dsl_run_rejects_value_return_kernel() -> None:
    lhs = torch.tensor([1, 2, 3, 4, 5, 6], dtype=torch.int32)
    rhs = np.array([6, 5, 4, 3, 2, 1], dtype=np.int32)

    with pytest.raises(KernelCodeError, match=_EXPECTED_RETURN_VALUE_MESSAGE):
        dsl_run(
            return_add_kernel,
            (lhs, rhs),
            "npu-demo-lowering",
        )


# TC-DSL-RUN-004A
# 测试目的: 锁定 dsl_run 不再为 kernel 隐式注入 operation helper，缺少 import 时必须失败。
# 对应功能实现文件路径: kernel_gen/tools/dsl_run.py
# 对应 spec 文件路径: spec/tools/dsl_run.md
# 对应测试文件路径: test/tools/test_dsl_run.py
def test_dsl_run_rejects_missing_operation_helper_import() -> None:
    out = torch.empty((6,), dtype=torch.int32)
    lhs = torch.tensor([1, 2, 3, 4, 5, 6], dtype=torch.int32)
    rhs = np.array([6, 5, 4, 3, 2, 1], dtype=np.int32)
    original_store = globals().pop("store")
    try:
        with pytest.raises(KernelCodeError, match="Unsupported call expression"):
            dsl_run(add_kernel, (out, lhs, rhs), "npu-demo-lowering")
        assert "store" not in globals()
    finally:
        globals()["store"] = original_store


# TC-DSL-RUN-004B
# 测试目的: 锁定 dsl_run / AST visitor 不再隐式注入 MemorySpace 等 enum 名称，缺少 import 时必须失败。
# 对应功能实现文件路径: kernel_gen/tools/dsl_run.py
# 对应 spec 文件路径: spec/tools/dsl_run.md
# 对应测试文件路径: test/tools/test_dsl_run.py
def test_dsl_run_rejects_missing_memory_space_import() -> None:
    out = torch.empty((6,), dtype=torch.int32)
    lhs = torch.tensor([1, 2, 3, 4, 5, 6], dtype=torch.int32)
    rhs = np.array([6, 5, 4, 3, 2, 1], dtype=np.int32)
    original_memory_space = globals().pop("MemorySpace")
    try:
        with pytest.raises(KernelCodeError, match="Unknown name"):
            dsl_run(add_slice_store_kernel, (out, lhs, rhs), "npu-demo-lowering")
        assert "MemorySpace" not in globals()
    finally:
        globals()["MemorySpace"] = original_memory_space


# TC-DSL-RUN-005
# 最后更改: 朽木露琪亚
# 测试目的: 锁定未设置 core config target 的固定失败短语。
# 对应功能实现文件路径: kernel_gen/tools/dsl_run.py
# 对应 spec 文件路径: spec/tools/dsl_run.md
# 对应测试文件路径: test/tools/test_dsl_run.py
def test_dsl_run_rejects_missing_core_target() -> None:
    out = torch.empty((6,), dtype=torch.int32)
    lhs = torch.tensor([1, 2, 3, 4, 5, 6], dtype=torch.int32)
    rhs = np.array([6, 5, 4, 3, 2, 1], dtype=np.int32)

    reset_config()
    with pytest.raises(KernelCodeError, match=_EXPECTED_TARGET_MESSAGE):
        dsl_run(add_kernel, (out, lhs, rhs), "npu-demo-lowering")


# TC-DSL-RUN-006
# 最后更改: 朽木露琪亚
# 测试目的: 锁定 target 配置类型错误时仍会在公开入口显式失败。
# 对应功能实现文件路径: kernel_gen/tools/dsl_run.py
# 对应 spec 文件路径: spec/tools/dsl_run.md
# 对应测试文件路径: test/tools/test_dsl_run.py
def test_dsl_run_rejects_invalid_core_target_type() -> None:
    out = torch.empty((6,), dtype=torch.int32)
    lhs = torch.tensor([1, 2, 3, 4, 5, 6], dtype=torch.int32)
    rhs = np.array([6, 5, 4, 3, 2, 1], dtype=np.int32)

    set_target(None)
    with pytest.raises(KernelCodeError, match=_EXPECTED_TARGET_MESSAGE):
        dsl_run(add_kernel, (out, lhs, rhs), "npu-demo-lowering")


# TC-DSL-RUN-007
# 最后更改: 朽木露琪亚
# 测试目的: 锁定未知 pipeline 名称的固定失败短语。
# 对应功能实现文件路径: kernel_gen/tools/dsl_run.py
# 对应 spec 文件路径: spec/tools/dsl_run.md
# 对应测试文件路径: test/tools/test_dsl_run.py
def test_dsl_run_rejects_unknown_pipeline_name() -> None:
    out = torch.empty((6,), dtype=torch.int32)
    lhs = torch.tensor([1, 2, 3, 4, 5, 6], dtype=torch.int32)
    rhs = np.array([6, 5, 4, 3, 2, 1], dtype=np.int32)

    with pytest.raises(KernelCodeError, match=_EXPECTED_PIPELINE_NAME_MESSAGE):
        dsl_run(add_kernel, (out, lhs, rhs), "missing-pipeline")


# TC-DSL-RUN-008
# 最后更改: 朽木露琪亚
# 测试目的: 锁定非法 pipeline 类型的固定失败短语。
# 对应功能实现文件路径: kernel_gen/tools/dsl_run.py
# 对应 spec 文件路径: spec/tools/dsl_run.md
# 对应测试文件路径: test/tools/test_dsl_run.py
def test_dsl_run_rejects_invalid_pipeline_type() -> None:
    out = torch.empty((6,), dtype=torch.int32)
    lhs = torch.tensor([1, 2, 3, 4, 5, 6], dtype=torch.int32)
    rhs = np.array([6, 5, 4, 3, 2, 1], dtype=np.int32)

    with pytest.raises(KernelCodeError, match=_EXPECTED_PIPELINE_TYPE_MESSAGE):
        dsl_run(add_kernel, (out, lhs, rhs), object())


# TC-DSL-RUN-008A
# 测试目的: 锁定 real_args 容器本身必须是 tuple/list，避免把 dict 或其他对象静默当成参数序列。
# 对应功能实现文件路径: kernel_gen/tools/dsl_run.py
# 对应 spec 文件路径: spec/tools/dsl_run.md
# 对应测试文件路径: test/tools/test_dsl_run.py
def test_dsl_run_rejects_invalid_real_args_container() -> None:
    out = torch.empty((6,), dtype=torch.int32)
    lhs = torch.tensor([1, 2, 3, 4, 5, 6], dtype=torch.int32)
    rhs = np.array([6, 5, 4, 3, 2, 1], dtype=np.int32)

    with pytest.raises(KernelCodeError, match=r"^DslRunInvalidRealArgs: real_args must be tuple or list$"):
        dsl_run(
            add_kernel,
            {"out": out, "lhs": lhs, "rhs": rhs},
            "npu-demo-lowering",
        )


# TC-DSL-RUN-008B
# 测试目的: 锁定 core config target 为空字符串时仍会在公开入口显式失败。
# 对应功能实现文件路径: kernel_gen/tools/dsl_run.py
# 对应 spec 文件路径: spec/tools/dsl_run.md
# 对应测试文件路径: test/tools/test_dsl_run.py
def test_dsl_run_rejects_empty_core_target_name() -> None:
    out = torch.empty((6,), dtype=torch.int32)
    lhs = torch.tensor([1, 2, 3, 4, 5, 6], dtype=torch.int32)
    rhs = np.array([6, 5, 4, 3, 2, 1], dtype=np.int32)
    set_target("")

    with pytest.raises(
        KernelCodeError,
        match=r"^DslRunInvalidTarget: core config target must be non-empty str$",
    ):
        dsl_run(add_kernel, (out, lhs, rhs), "npu-demo-lowering")


# TC-DSL-RUN-008C
# 测试目的: 锁定 pipeline 执行后若 core target 失效，源码生成入口仍按公开 target 错误失败。
# 对应功能实现文件路径: kernel_gen/tools/dsl_run.py
# 对应 spec 文件路径: spec/tools/dsl_run.md
# 对应测试文件路径: test/tools/test_dsl_run.py
def test_dsl_run_rejects_target_cleared_after_pipeline() -> None:
    out = torch.empty((6,), dtype=torch.int32)
    lhs = torch.tensor([1, 2, 3, 4, 5, 6], dtype=torch.int32)
    rhs = np.array([6, 5, 4, 3, 2, 1], dtype=np.int32)

    with pytest.raises(KernelCodeError, match=_EXPECTED_TARGET_MESSAGE):
        dsl_run(add_kernel, (out, lhs, rhs), _ClearingTargetPipeline())


# TC-DSL-RUN-009
# 最后更改: 朽木露琪亚
# 测试目的: 锁定非法 runtime 参数类型的固定失败短语。
# 对应功能实现文件路径: kernel_gen/tools/dsl_run.py
# 对应 spec 文件路径: spec/tools/dsl_run.md
# 对应测试文件路径: test/tools/test_dsl_run.py
def test_dsl_run_rejects_unsupported_runtime_arg_type() -> None:
    out = torch.empty((6,), dtype=torch.int32)
    lhs = torch.tensor([1, 2, 3, 4, 5, 6], dtype=torch.int32)
    rhs = object()

    with pytest.raises(KernelCodeError, match=_EXPECTED_REAL_ARG_TYPE_MESSAGE):
        dsl_run(add_kernel, (out, lhs, rhs), "npu-demo-lowering")


# TC-DSL-RUN-009A
# 测试目的: 锁定 tile_* runtime scalar 必须是正整数。
# 对应功能实现文件路径: kernel_gen/tools/dsl_run.py
# 对应 spec 文件路径: spec/tools/dsl_run.md
# 对应测试文件路径: test/tools/test_dsl_run.py
def test_dsl_run_rejects_non_positive_tile_runtime_scalar() -> None:
    out = torch.empty((6,), dtype=torch.int32)
    lhs = torch.tensor([1, 2, 3, 4, 5, 6], dtype=torch.int32)
    rhs = np.array([6, 5, 4, 3, 2, 1], dtype=np.int32)

    with pytest.raises(KernelCodeError, match=_EXPECTED_TILE_VALUE_MESSAGE):
        dsl_run(add_dynamic_tile_kernel, (out, lhs, rhs, 0), "npu-demo-lowering")


# TC-DSL-RUN-009B
# 测试目的: 锁定不受支持的 numpy dtype 会在公开 real_args 转换阶段失败。
# 对应功能实现文件路径: kernel_gen/tools/dsl_run.py
# 对应 spec 文件路径: spec/tools/dsl_run.md
# 对应测试文件路径: test/tools/test_dsl_run.py
def test_dsl_run_rejects_unsupported_numpy_dtype() -> None:
    out = np.empty((6,), dtype=np.complex64)
    lhs = np.ones((6,), dtype=np.complex64)
    rhs = np.ones((6,), dtype=np.complex64)

    with pytest.raises(KernelCodeError, match=_EXPECTED_REAL_ARG_TYPE_MESSAGE):
        dsl_run(add_kernel, (out, lhs, rhs), "npu-demo-lowering")


# TC-DSL-RUN-009C
# 测试目的: 锁定 torch.bfloat16 运行时 dtype 映射到 DSL dtype 后再进入公开 pipeline 结果校验。
# 对应功能实现文件路径: kernel_gen/tools/dsl_run.py
# 对应 spec 文件路径: spec/tools/dsl_run.md
# 对应测试文件路径: test/tools/test_dsl_run.py
def test_dsl_run_maps_bfloat16_runtime_dtype_before_pipeline_validation() -> None:
    out = torch.empty((6,), dtype=torch.bfloat16)
    lhs = torch.ones((6,), dtype=torch.bfloat16)
    rhs = torch.ones((6,), dtype=torch.bfloat16)
    set_target("cpu")

    with pytest.raises(KernelCodeError, match=r"^DslRunInternalError: pipeline must return builtin\.module$"):
        dsl_run(add_kernel, (out, lhs, rhs), _NonModuleResultPipeline())


# TC-DSL-RUN-010
# 最后更改: 朽木露琪亚
# 测试目的: 锁定 runtime 参数数量不匹配的固定失败短语。
# 对应功能实现文件路径: kernel_gen/tools/dsl_run.py
# 对应 spec 文件路径: spec/tools/dsl_run.md
# 对应测试文件路径: test/tools/test_dsl_run.py
def test_dsl_run_rejects_arity_mismatch() -> None:
    out = torch.empty((6,), dtype=torch.int32)
    lhs = torch.tensor([1, 2, 3, 4, 5, 6], dtype=torch.int32)

    with pytest.raises(KernelCodeError, match=_EXPECTED_ARITY_MESSAGE):
        dsl_run(add_kernel, (out, lhs), "npu-demo-lowering")


# TC-DSL-RUN-010A
# 测试目的: 锁定 pipeline 若返回空 builtin.module，dsl_run 会在公开入口显式拒绝。
# 对应功能实现文件路径: kernel_gen/tools/dsl_run.py
# 对应 spec 文件路径: spec/tools/dsl_run.md
# 对应测试文件路径: test/tools/test_dsl_run.py
def test_dsl_run_rejects_pipeline_returning_empty_module() -> None:
    class EmptyModulePipeline(PassManager):
        def run(self, module: ModuleOp) -> ModuleOp:
            return ModuleOp([])

    out = torch.empty((6,), dtype=torch.int32)
    lhs = torch.tensor([1, 2, 3, 4, 5, 6], dtype=torch.int32)
    rhs = np.array([6, 5, 4, 3, 2, 1], dtype=np.int32)
    set_target("cpu")

    with pytest.raises(KernelCodeError, match=r"^DslRunInternalError: lowered module does not contain func\.func$"):
        dsl_run(add_kernel, (out, lhs, rhs), EmptyModulePipeline())


# TC-DSL-RUN-010B
# 测试目的: 锁定 npu_demo 唯一 wrapper 若指向缺失 body func，dsl_run 会在公开入口显式失败。
# 对应功能实现文件路径: kernel_gen/tools/dsl_run.py
# 对应 spec 文件路径: spec/tools/dsl_run.md
# 对应测试文件路径: test/tools/test_dsl_run.py
def test_dsl_run_rejects_npu_demo_wrapper_without_body_func() -> None:
    class MissingBodyPipeline(PassManager):
        def run(self, module: ModuleOp) -> ModuleOp:
            return _make_launch_only_module(callee="missing_kernel")

    out = torch.empty((6,), dtype=torch.int32)
    lhs = torch.tensor([1, 2, 3, 4, 5, 6], dtype=torch.int32)
    rhs = np.array([6, 5, 4, 3, 2, 1], dtype=np.int32)

    with pytest.raises(
        KernelCodeError,
        match=r"^DslRunInternalError: lowered module does not contain func\.func @missing_kernel$",
    ):
        dsl_run(add_kernel, (out, lhs, rhs), MissingBodyPipeline())


# TC-DSL-RUN-010C
# 测试目的: 锁定非 npu_demo target 若收到仅含 launch wrapper 的 module，会继续透传公开 gen_kernel 失败而不是静默吞掉。
# 对应功能实现文件路径: kernel_gen/tools/dsl_run.py
# 对应 spec 文件路径: spec/tools/dsl_run.md
# 对应测试文件路径: test/tools/test_dsl_run.py
def test_dsl_run_re_raises_codegen_failure_for_cpu_launch_wrapper() -> None:
    class CpuLaunchWrapperPipeline(PassManager):
        def run(self, module: ModuleOp) -> ModuleOp:
            return _make_launch_only_module(callee="_device_kernel")

    out = torch.empty((6,), dtype=torch.int32)
    lhs = torch.tensor([1, 2, 3, 4, 5, 6], dtype=torch.int32)
    rhs = np.array([6, 5, 4, 3, 2, 1], dtype=np.int32)
    set_target("cpu")

    with pytest.raises(KernelCodeError, match=r"^target=cpu: arch\.launch: unsupported op$"):
        dsl_run(add_kernel, (out, lhs, rhs), CpuLaunchWrapperPipeline())


# TC-DSL-RUN-010D
# 测试目的: 锁定 pipeline 若返回非 builtin.module，dsl_run 会在公开入口显式拒绝。
# 对应功能实现文件路径: kernel_gen/tools/dsl_run.py
# 对应 spec 文件路径: spec/tools/dsl_run.md
# 对应测试文件路径: test/tools/test_dsl_run.py
def test_dsl_run_rejects_pipeline_returning_non_module() -> None:
    class NonModulePipeline(PassManager):
        def run(self, module: ModuleOp) -> _NonModulePipelineResult:
            return _NonModulePipelineResult()

    out = torch.empty((6,), dtype=torch.int32)
    lhs = torch.tensor([1, 2, 3, 4, 5, 6], dtype=torch.int32)
    rhs = np.array([6, 5, 4, 3, 2, 1], dtype=np.int32)
    set_target("cpu")

    with pytest.raises(KernelCodeError, match=r"^DslRunInternalError: pipeline must return builtin\.module$"):
        dsl_run(add_kernel, (out, lhs, rhs), NonModulePipeline())


# TC-DSL-RUN-011
# 最后更改: 朽木露琪亚
# 测试目的: 确认 spec、实现与测试文件都已落到当前工作书。
# 对应功能实现文件路径: kernel_gen/tools/dsl_run.py
# 对应 spec 文件路径: spec/tools/dsl_run.md
# 对应测试文件路径: test/tools/test_dsl_run.py
def test_dsl_run_contract_files_exist() -> None:
    assert (REPO_ROOT / "spec/tools/dsl_run.md").is_file()
    assert (REPO_ROOT / "kernel_gen/tools/dsl_run.py").is_file()
    assert (REPO_ROOT / "test/tools/test_dsl_run.py").is_file()
