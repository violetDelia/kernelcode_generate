"""dsl_run tests.

创建者: 朽木露琪亚
最后一次更改: 朽木露琪亚

功能说明:
- 覆盖 `dsl_run(func, real_args, pipeline, emitcconfig)` 的正向执行、错误合同与结果模型口径。
- 同时锁定 `dsl_run` 对正向、反向与 tiled matmul 样例的行为。

使用示例:
- pytest -q test/tools/test_dsl_run.py

关联文件:
- spec: [spec/tools/dsl_run.md](spec/tools/dsl_run.md)
- 功能实现: [kernel_gen/tools/dsl_run.py](kernel_gen/tools/dsl_run.py)
- test: [test/tools/test_dsl_run.py](test/tools/test_dsl_run.py)
"""

from __future__ import annotations

import re
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

    创建者: 朽木露琪亚
    最后一次更改: 朽木露琪亚

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

from kernel_gen.dsl.gen_kernel import EmitCContext
from kernel_gen.operation import deslice, loop, matmul, slice, store
from kernel_gen.passes.pass_manager import PassManager
from kernel_gen.passes.registry import build_registered_pipeline, load_builtin_passes
from kernel_gen.tools.dsl_run import DslRunError, dsl_run
from kernel_gen.tools.dsl_run import NPU_DEMO_WRAPPER_ERROR
from kernel_gen.target import registry as target_registry
from kernel_gen.symbol_variable.memory import MemorySpace

dsl_run_module = importlib.import_module("kernel_gen.tools.dsl_run")

try:
    import torch
except ImportError as exc:  # pragma: no cover - tests require torch
    raise RuntimeError("test/tools/test_dsl_run.py requires torch") from exc


RETURN_VALUE_ERROR = "DslRunReturnValueUnsupported: dsl_run only supports functions without DSL return values"
EMITCCONFIG_ERROR = "DslRunInvalidEmitCContext: emitcconfig must be EmitCContext"
PIPELINE_NAME_ERROR = "DslRunUnknownPipeline: unknown pipeline 'missing-pipeline'"
PIPELINE_TYPE_ERROR = "DslRunInvalidPipeline: pipeline must be str or PassManager"
REAL_ARG_TYPE_ERROR = "DslRunUnsupportedRealArg: real_args only supports torch.Tensor and numpy.ndarray"
ARITY_ERROR = "DslRunArityMismatch: real_args count does not match function signature"


@pytest.fixture(autouse=True)
def _isolated_target_registry() -> None:
    """隔离 `dsl_run` 测试期间的 target registry 全局状态。

    创建者: 金铲铲大作战
    最后更改: 金铲铲大作战

    功能说明:
    - 先清空 registry，再重新加载当前仓库的默认 target 定义。
    - 测试完成后恢复原始 registry / current target，避免与其他测试文件互相污染。

    使用示例:
    - 由 pytest 自动应用，无需手动调用。

    关联文件:
    - 功能实现: kernel_gen/target/registry.py
    - test: test/tools/test_dsl_run.py
    """

    registry_snapshot = dict(target_registry._TARGET_REGISTRY)
    current_target_snapshot = target_registry._CURRENT_TARGET
    target_registry._TARGET_REGISTRY.clear()
    target_registry.load_targets(REPO_ROOT / "kernel_gen" / "target" / "targets")
    try:
        yield
    finally:
        target_registry._TARGET_REGISTRY.clear()
        target_registry._TARGET_REGISTRY.update(registry_snapshot)
        target_registry._CURRENT_TARGET = current_target_snapshot


def _build_npu_demo_lowering_pipeline() -> PassManager:
    """构造 `npu-demo-lowering` pipeline。

    创建者: 朽木露琪亚
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


def _make_body_only_module() -> ModuleOp:
    """构造一个只有普通 `func.func` 的 lowered module。

    创建者: 金铲铲大作战
    最后一次更改: 金铲铲大作战

    功能说明:
    - 用于验证 `npu_demo` 在缺少唯一 `arch.launch` wrapper 时必须显式失败。
    - 该 module 不含任何 wrapper 语义，便于锁定“不得回退到首个普通 func.func”的机械边界。

    使用示例:
    - module = _make_body_only_module()

    关联文件:
    - spec: [spec/tools/dsl_run.md](spec/tools/dsl_run.md)
    - test: [test/tools/test_dsl_run.py](test/tools/test_dsl_run.py)
    - 功能实现: [kernel_gen/tools/dsl_run.py](kernel_gen/tools/dsl_run.py)
    """

    block = Block()
    block.add_op(func.ReturnOp())
    func_op = func.FuncOp("body_kernel", FunctionType.from_lists([], []), Region(block))
    return ModuleOp([func_op])


def add_kernel(
    out: "Tensor[i32, 6]",
    lhs: "Tensor[i32, 6]",
    rhs: "Tensor[i32, 6]",
) -> None:
    """最小 add 样例，仅通过显式 out 参数写回结果。

    创建者: 朽木露琪亚
    最后更改: 朽木露琪亚

    功能说明:
    - 为 `dsl_run(...)` 提供最小正向样例。
    - 本函数不返回 DSL 值，只通过 `store(...)` 写入 `out`。

    使用示例:
    - `dsl_run(add_kernel, (out, lhs, rhs), "npu-demo-lowering", EmitCContext(target="npu_demo"))`

    关联文件:
    - spec: [spec/tools/dsl_run.md](spec/tools/dsl_run.md)
    - test: [test/tools/test_dsl_run.py](test/tools/test_dsl_run.py)
    - 功能实现: [kernel_gen/tools/dsl_run.py](kernel_gen/tools/dsl_run.py)
    """

    store(lhs + rhs, out, [0], [6], [1])


def store_add_kernel(
    out: "Tensor[i32, 6]",
    lhs: "Tensor[i32, 6]",
    rhs: "Tensor[i32, 6]",
) -> None:
    """显式 out 参数版本的 add 样例。"""

    store(lhs + rhs, out, [0], [6], [1])


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
    store(lhs_tile + rhs_tile, out, [1], [4], [1])


def add_for_loop_kernel(
    out: "Tensor[i32, 6]",
    lhs: "Tensor[i32, 6]",
    rhs: "Tensor[i32, 6]",
) -> None:
    """固定可整除 tile 的 for-loop add 样例。"""

    for index in loop(0, 6, 3):
        lhs_tile = slice(lhs, [index], [3], [1], MemorySpace.TSM)
        rhs_tile = slice(rhs, [index], [3], [1], MemorySpace.TSM)
        store(lhs_tile + rhs_tile, out, [index], [3], [1])


def sub_store_kernel(
    out: "Tensor[i32, 6]",
    lhs: "Tensor[i32, 6]",
    rhs: "Tensor[i32, 6]",
) -> None:
    """显式 out 参数版本的 sub 样例。"""

    store(lhs - rhs, out, [0], [6], [1])


def mul_store_kernel(
    out: "Tensor[i32, 6]",
    lhs: "Tensor[i32, 6]",
    rhs: "Tensor[i32, 6]",
) -> None:
    """显式 out 参数版本的 mul 样例。"""

    store(lhs * rhs, out, [0], [6], [1])


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
            deslice(partial, out, [m0, n0], [16, 16], [1, 1])


def _assert_result_contract(
    result: object,
    out: object,
    expected: object,
    *,
    helper_snippet: str = "add<",
) -> None:
    """断言 `dsl_run(...)` 的最小公开结果合同。

    创建者: 朽木露琪亚
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
# 创建者: 朽木露琪亚
# 最后一次更改: 朽木露琪亚
# 最近一次运行测试时间: 未运行
# 最近一次运行成功时间: 未运行
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
        EmitCContext(target="npu_demo"),
    )

    _assert_result_contract(result, out, expected)


# TC-DSL-RUN-002
# 创建者: 朽木露琪亚
# 最后一次更改: 朽木露琪亚
# 最近一次运行测试时间: 未运行
# 最近一次运行成功时间: 未运行
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
        EmitCContext(target="npu_demo"),
    )

    _assert_result_contract(result, out, expected)


# TC-DSL-RUN-003
# 创建者: 朽木露琪亚
# 最后更改: 朽木露琪亚
# 最近一次运行测试时间: 未运行
# 最近一次运行成功时间: 未运行
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
        store_add_kernel,
        (out, lhs, rhs),
        "npu-demo-lowering",
        EmitCContext(target="npu_demo"),
    )

    _assert_result_contract(result, out, expected)


# TC-DSL-RUN-003A
# 创建者: 朽木露琪亚
# 最后更改: 朽木露琪亚
# 最近一次运行测试时间: 未运行
# 最近一次运行成功时间: 未运行
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
        EmitCContext(target="npu_demo"),
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
# 创建者: 朽木露琪亚
# 最后更改: 朽木露琪亚
# 最近一次运行测试时间: 未运行
# 最近一次运行成功时间: 未运行
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
        EmitCContext(target="npu_demo"),
    )

    lowered_text = str(result.func_op)
    assert result.execute_result.ok is True
    assert result.execute_result.failure_phrase is None
    assert "#nn.space<tsm>" in lowered_text
    assert "symbol.for" in lowered_text
    assert "kernel.binary_elewise" in lowered_text
    assert "kind = \"add\"" in lowered_text
    _assert_result_contract(result, out, expected, helper_snippet="add<")


# TC-DSL-RUN-003B
# 创建者: 朽木露琪亚
# 最后更改: 朽木露琪亚
# 最近一次运行测试时间: 未运行
# 最近一次运行成功时间: 未运行
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
        EmitCContext(target="npu_demo"),
    )

    lowered_text = str(result.func_op)
    assert "kernel.binary_elewise" in lowered_text
    assert 'kind = "sub"' in lowered_text
    assert "nn.sub" not in lowered_text
    _assert_result_contract(result, out, expected, helper_snippet="sub<")


# TC-DSL-RUN-003C
# 创建者: 朽木露琪亚
# 最后更改: 朽木露琪亚
# 最近一次运行测试时间: 未运行
# 最近一次运行成功时间: 未运行
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
        EmitCContext(target="npu_demo"),
    )

    lowered_text = str(result.func_op)
    assert "kernel.binary_elewise" in lowered_text
    assert 'kind = "mul"' in lowered_text
    assert "nn.mul" not in lowered_text
    _assert_result_contract(result, out, expected, helper_snippet="mul<")


# TC-DSL-RUN-003D
# 创建者: 朽木露琪亚
# 最后更改: 朽木露琪亚
# 最近一次运行测试时间: 未运行
# 最近一次运行成功时间: 未运行
# 测试目的: 锁定 dsl_run + npu-demo-lowering 对 sub 的 out-param 正向链路，避免执行链路只剩手工分支有回归覆盖。
# 对应功能实现文件路径: kernel_gen/tools/dsl_run.py
# 对应 spec 文件路径: spec/tools/dsl_run.md
# 对应测试文件路径: test/tools/test_dsl_run.py
def test_dsl_run_supports_sub_store_kernel_on_npu_demo() -> None:
    out = torch.empty((6,), dtype=torch.int32)
    lhs = torch.tensor([10, 11, 12, 13, 14, 15], dtype=torch.int32)
    rhs = np.array([1, 2, 3, 4, 5, 6], dtype=np.int32)
    expected = lhs - torch.from_numpy(rhs)

    result = dsl_run(
        sub_store_kernel,
        (out, lhs, rhs),
        "npu-demo-lowering",
        EmitCContext(target="npu_demo"),
    )

    _assert_result_contract(result, out, expected, helper_snippet="sub<")
    assert 'kind = "sub"' in str(result.func_op)


# TC-DSL-RUN-003E
# 创建者: 朽木露琪亚
# 最后更改: 朽木露琪亚
# 最近一次运行测试时间: 未运行
# 最近一次运行成功时间: 未运行
# 测试目的: 锁定 dsl_run + npu-demo-lowering 对 mul 的 out-param 正向链路，避免执行链路只剩手工分支有回归覆盖。
# 对应功能实现文件路径: kernel_gen/tools/dsl_run.py
# 对应 spec 文件路径: spec/tools/dsl_run.md
# 对应测试文件路径: test/tools/test_dsl_run.py
def test_dsl_run_supports_mul_store_kernel_on_npu_demo() -> None:
    out = torch.empty((6,), dtype=torch.int32)
    lhs = torch.tensor([1, 2, 3, 4, 5, 6], dtype=torch.int32)
    rhs = np.array([6, 5, 4, 3, 2, 1], dtype=np.int32)
    expected = lhs * torch.from_numpy(rhs)

    result = dsl_run(
        mul_store_kernel,
        (out, lhs, rhs),
        "npu-demo-lowering",
        EmitCContext(target="npu_demo"),
    )

    _assert_result_contract(result, out, expected, helper_snippet="mul<")
    assert 'kind = "mul"' in str(result.func_op)


# TC-DSL-RUN-003F
# 创建者: 朽木露琪亚
# 最后更改: 朽木露琪亚
# 最近一次运行测试时间: 未运行
# 最近一次运行成功时间: 未运行
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
        EmitCContext(target="npu_demo"),
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
# 创建者: 金铲铲大作战
# 最后一次更改: 金铲铲大作战
# 最近一次运行测试时间: 未运行
# 最近一次运行成功时间: 未运行
# 测试目的: 锁定 npu_demo lowered module 在 wrapper 不唯一/缺失时必须显式失败，避免静默回退到首个普通 func.func。
# 对应功能实现文件路径: kernel_gen/tools/dsl_run.py
# 对应 spec 文件路径: spec/tools/dsl_run.md
# 对应测试文件路径: test/tools/test_dsl_run.py
def test_dsl_run_rejects_npu_demo_module_without_unique_wrapper(monkeypatch: pytest.MonkeyPatch) -> None:
    lowered_module = _make_body_only_module()

    def _unexpected_gen_kernel(*args: object, **kwargs: object) -> str:
        pytest.fail("npu_demo lowered module should not fall back to the first normal func.func")

    monkeypatch.setattr(dsl_run_module, "mlir_gen", lambda *args, **kwargs: lowered_module)
    monkeypatch.setattr(dsl_run_module.PassManager, "run", lambda self, module: lowered_module)
    monkeypatch.setattr(dsl_run_module, "gen_kernel", _unexpected_gen_kernel)

    out = torch.empty((6,), dtype=torch.int32)
    lhs = torch.tensor([1, 2, 3, 4, 5, 6], dtype=torch.int32)
    rhs = np.array([6, 5, 4, 3, 2, 1], dtype=np.int32)

    with pytest.raises(DslRunError, match=re.escape(NPU_DEMO_WRAPPER_ERROR)):
        dsl_run(
            store_add_kernel,
            (out, lhs, rhs),
            PassManager(),
            EmitCContext(target="npu_demo"),
        )


# TC-DSL-RUN-004
# 创建者: 朽木露琪亚
# 最后更改: 朽木露琪亚
# 最近一次运行测试时间: 未运行
# 最近一次运行成功时间: 未运行
# 测试目的: 锁定 DSL 值返回函数的固定失败短语。
# 对应功能实现文件路径: kernel_gen/tools/dsl_run.py
# 对应 spec 文件路径: spec/tools/dsl_run.md
# 对应测试文件路径: test/tools/test_dsl_run.py
def test_dsl_run_rejects_value_return_kernel() -> None:
    lhs = torch.tensor([1, 2, 3, 4, 5, 6], dtype=torch.int32)
    rhs = np.array([6, 5, 4, 3, 2, 1], dtype=np.int32)

    with pytest.raises(DslRunError, match=re.escape(RETURN_VALUE_ERROR)):
        dsl_run(
            return_add_kernel,
            (lhs, rhs),
            "npu-demo-lowering",
            EmitCContext(target="npu_demo"),
        )


# TC-DSL-RUN-005
# 创建者: 朽木露琪亚
# 最后更改: 朽木露琪亚
# 最近一次运行测试时间: 未运行
# 最近一次运行成功时间: 未运行
# 测试目的: 锁定 emitcconfig=None 的固定失败短语。
# 对应功能实现文件路径: kernel_gen/tools/dsl_run.py
# 对应 spec 文件路径: spec/tools/dsl_run.md
# 对应测试文件路径: test/tools/test_dsl_run.py
def test_dsl_run_rejects_none_emitcconfig() -> None:
    out = torch.empty((6,), dtype=torch.int32)
    lhs = torch.tensor([1, 2, 3, 4, 5, 6], dtype=torch.int32)
    rhs = np.array([6, 5, 4, 3, 2, 1], dtype=np.int32)

    with pytest.raises(DslRunError, match=re.escape(EMITCCONFIG_ERROR)):
        dsl_run(store_add_kernel, (out, lhs, rhs), "npu-demo-lowering", None)


# TC-DSL-RUN-006
# 创建者: 朽木露琪亚
# 最后更改: 朽木露琪亚
# 最近一次运行测试时间: 未运行
# 最近一次运行成功时间: 未运行
# 测试目的: 锁定 emitcconfig 不是 EmitCContext 的固定失败短语。
# 对应功能实现文件路径: kernel_gen/tools/dsl_run.py
# 对应 spec 文件路径: spec/tools/dsl_run.md
# 对应测试文件路径: test/tools/test_dsl_run.py
def test_dsl_run_rejects_invalid_emitcconfig_type() -> None:
    out = torch.empty((6,), dtype=torch.int32)
    lhs = torch.tensor([1, 2, 3, 4, 5, 6], dtype=torch.int32)
    rhs = np.array([6, 5, 4, 3, 2, 1], dtype=np.int32)

    with pytest.raises(DslRunError, match=re.escape(EMITCCONFIG_ERROR)):
        dsl_run(store_add_kernel, (out, lhs, rhs), "npu-demo-lowering", object())


# TC-DSL-RUN-007
# 创建者: 朽木露琪亚
# 最后更改: 朽木露琪亚
# 最近一次运行测试时间: 未运行
# 最近一次运行成功时间: 未运行
# 测试目的: 锁定未知 pipeline 名称的固定失败短语。
# 对应功能实现文件路径: kernel_gen/tools/dsl_run.py
# 对应 spec 文件路径: spec/tools/dsl_run.md
# 对应测试文件路径: test/tools/test_dsl_run.py
def test_dsl_run_rejects_unknown_pipeline_name() -> None:
    out = torch.empty((6,), dtype=torch.int32)
    lhs = torch.tensor([1, 2, 3, 4, 5, 6], dtype=torch.int32)
    rhs = np.array([6, 5, 4, 3, 2, 1], dtype=np.int32)

    with pytest.raises(DslRunError, match=re.escape(PIPELINE_NAME_ERROR)):
        dsl_run(store_add_kernel, (out, lhs, rhs), "missing-pipeline", EmitCContext(target="npu_demo"))


# TC-DSL-RUN-008
# 创建者: 朽木露琪亚
# 最后更改: 朽木露琪亚
# 最近一次运行测试时间: 未运行
# 最近一次运行成功时间: 未运行
# 测试目的: 锁定非法 pipeline 类型的固定失败短语。
# 对应功能实现文件路径: kernel_gen/tools/dsl_run.py
# 对应 spec 文件路径: spec/tools/dsl_run.md
# 对应测试文件路径: test/tools/test_dsl_run.py
def test_dsl_run_rejects_invalid_pipeline_type() -> None:
    out = torch.empty((6,), dtype=torch.int32)
    lhs = torch.tensor([1, 2, 3, 4, 5, 6], dtype=torch.int32)
    rhs = np.array([6, 5, 4, 3, 2, 1], dtype=np.int32)

    with pytest.raises(DslRunError, match=re.escape(PIPELINE_TYPE_ERROR)):
        dsl_run(store_add_kernel, (out, lhs, rhs), object(), EmitCContext(target="npu_demo"))


# TC-DSL-RUN-009
# 创建者: 朽木露琪亚
# 最后更改: 朽木露琪亚
# 最近一次运行测试时间: 未运行
# 最近一次运行成功时间: 未运行
# 测试目的: 锁定非法 runtime 参数类型的固定失败短语。
# 对应功能实现文件路径: kernel_gen/tools/dsl_run.py
# 对应 spec 文件路径: spec/tools/dsl_run.md
# 对应测试文件路径: test/tools/test_dsl_run.py
def test_dsl_run_rejects_unsupported_runtime_arg_type() -> None:
    out = torch.empty((6,), dtype=torch.int32)
    lhs = torch.tensor([1, 2, 3, 4, 5, 6], dtype=torch.int32)
    rhs = object()

    with pytest.raises(DslRunError, match=re.escape(REAL_ARG_TYPE_ERROR)):
        dsl_run(store_add_kernel, (out, lhs, rhs), "npu-demo-lowering", EmitCContext(target="npu_demo"))


# TC-DSL-RUN-010
# 创建者: 朽木露琪亚
# 最后更改: 朽木露琪亚
# 最近一次运行测试时间: 未运行
# 最近一次运行成功时间: 未运行
# 测试目的: 锁定 runtime 参数数量不匹配的固定失败短语。
# 对应功能实现文件路径: kernel_gen/tools/dsl_run.py
# 对应 spec 文件路径: spec/tools/dsl_run.md
# 对应测试文件路径: test/tools/test_dsl_run.py
def test_dsl_run_rejects_arity_mismatch() -> None:
    out = torch.empty((6,), dtype=torch.int32)
    lhs = torch.tensor([1, 2, 3, 4, 5, 6], dtype=torch.int32)

    with pytest.raises(DslRunError, match=re.escape(ARITY_ERROR)):
        dsl_run(store_add_kernel, (out, lhs), "npu-demo-lowering", EmitCContext(target="npu_demo"))


# TC-DSL-RUN-011
# 创建者: 朽木露琪亚
# 最后更改: 朽木露琪亚
# 最近一次运行测试时间: 未运行
# 最近一次运行成功时间: 未运行
# 测试目的: 确认 spec、实现与测试文件都已落到当前工作书。
# 对应功能实现文件路径: kernel_gen/tools/dsl_run.py
# 对应 spec 文件路径: spec/tools/dsl_run.md
# 对应测试文件路径: test/tools/test_dsl_run.py
def test_dsl_run_contract_files_exist() -> None:
    assert (REPO_ROOT / "spec/tools/dsl_run.md").is_file()
    assert (REPO_ROOT / "kernel_gen/tools/dsl_run.py").is_file()
    assert (REPO_ROOT / "test/tools/test_dsl_run.py").is_file()
