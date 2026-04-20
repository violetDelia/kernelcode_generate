"""dsl_run tests.

创建者: 朽木露琪亚
最后一次更改: 朽木露琪亚

功能说明:
- 覆盖 `dsl_run(func, real_args, pipeline, emitcconfig)` 的正向执行、错误合同与结果模型口径。
- 同时锁定 `expectation/tools/dsl_run` 对应的正向与反向样例。

使用示例:
- pytest -q test/tools/test_dsl_run.py

关联文件:
- spec: [spec/tools/dsl_run.md](spec/tools/dsl_run.md)
- 功能实现: [kernel_gen/tools/dsl_run.py](kernel_gen/tools/dsl_run.py)
- expectation: [expectation/tools/dsl_run/add.py](expectation/tools/dsl_run/add.py)
- expectation: [expectation/tools/dsl_run/invalid_contract.py](expectation/tools/dsl_run/invalid_contract.py)
"""

from __future__ import annotations

from contextlib import contextmanager
import re
import sys
from pathlib import Path

import numpy as np
import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from expectation.tools.dsl_run.add import add_kernel
from expectation.tools.dsl_run.invalid_contract import (
    ARITY_ERROR,
    EMITCCONFIG_ERROR,
    PIPELINE_NAME_ERROR,
    PIPELINE_TYPE_ERROR,
    REAL_ARG_TYPE_ERROR,
    RETURN_VALUE_ERROR,
    return_add_kernel,
    store_add_kernel,
)
from kernel_gen.dsl.emit_c import EmitCContext
from kernel_gen.passes.pass_manager import PassManager
from kernel_gen.passes.registry import build_registered_pipeline, load_builtin_passes
from kernel_gen.target import registry as target_registry
from kernel_gen.tools.dsl_run import DslRunError, dsl_run

try:
    import torch
except ImportError as exc:  # pragma: no cover - tests require torch
    raise RuntimeError("test/tools/test_dsl_run.py requires torch") from exc


_DSL_RUN_TEST_TARGET_NAME = "dsl_run_test_target"


def _ensure_dsl_run_test_target_registered() -> str:
    """确保测试用临时 target 已注册。

    创建者: 朽木露琪亚
    最后一次更改: 朽木露琪亚

    功能说明:
    - 复用内置 `npu_demo` 的 arch 能力，仅把 `sm_memory_size` / `lm_memory_size` 提升到可用值。
    - 只在当前进程注册一次，避免重复注册影响后续测试。

    使用示例:
    - target_name = _ensure_dsl_run_test_target_registered()

    关联文件:
    - spec: [spec/tools/dsl_run.md](spec/tools/dsl_run.md)
    - test: [test/tools/test_dsl_run.py](test/tools/test_dsl_run.py)
    - 功能实现: [kernel_gen/target/registry.py](kernel_gen/target/registry.py)
    """

    registry = getattr(target_registry, "_TARGET_REGISTRY", {})
    if _DSL_RUN_TEST_TARGET_NAME in registry:
        return _DSL_RUN_TEST_TARGET_NAME
    base_spec = registry["npu_demo"]
    hardware = dict(base_spec.hardware)
    hardware["sm_memory_size"] = 1024
    hardware["lm_memory_size"] = 1024
    target_registry.register_target(
        target_registry.TargetSpec(
            name=_DSL_RUN_TEST_TARGET_NAME,
            arch_supported_ops=set(base_spec.arch_supported_ops)
            if base_spec.arch_supported_ops is not None
            else None,
            arch_unsupported_ops=set(base_spec.arch_unsupported_ops),
            hardware=hardware,
        )
    )
    return _DSL_RUN_TEST_TARGET_NAME


@contextmanager
def _use_dsl_run_test_target() -> None:
    """切换到测试所需的临时 target，并在退出时恢复原状。

    创建者: 朽木露琪亚
    最后一次更改: 朽木露琪亚

    功能说明:
    - 让 `lower-dma-memory-hierarchy` 能读取到有效的 SM/LM 硬件参数。
    - 避免测试污染进程级 current target。

    使用示例:
    - with _use_dsl_run_test_target():
          dsl_run(...)

    关联文件:
    - spec: [spec/tools/dsl_run.md](spec/tools/dsl_run.md)
    - test: [test/tools/test_dsl_run.py](test/tools/test_dsl_run.py)
    - 功能实现: [kernel_gen/target/registry.py](kernel_gen/target/registry.py)
    """

    previous_target = target_registry._get_current_target()
    target_name = _ensure_dsl_run_test_target_registered()
    target_registry._set_current_target(target_name)
    try:
        yield
    finally:
        target_registry._set_current_target(previous_target)


def _build_default_lowering_pipeline() -> PassManager:
    """构造 `default-lowering` pipeline。

    创建者: 朽木露琪亚
    最后一次更改: 朽木露琪亚

    功能说明:
    - 显式加载 builtin passes 后，再通过 registry 构造默认 lowering pipeline。
    - 便于测试同时覆盖字符串 pipeline 与现成 `PassManager` 两条入口。

    使用示例:
    - pipeline = _build_default_lowering_pipeline()

    关联文件:
    - spec: [spec/tools/dsl_run.md](spec/tools/dsl_run.md)
    - test: [test/tools/test_dsl_run.py](test/tools/test_dsl_run.py)
    - 功能实现: [kernel_gen/passes/registry.py](kernel_gen/passes/registry.py)
    """

    load_builtin_passes()
    pipeline = build_registered_pipeline("default-lowering")
    assert isinstance(pipeline, PassManager)
    return pipeline


def _assert_result_contract(result: object, out: object, expected: object) -> None:
    """断言 `dsl_run(...)` 的最小公开结果合同。

    创建者: 朽木露琪亚
    最后一次更改: 朽木露琪亚

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
    assert "npu_demo::add<" in result.source

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

    with _use_dsl_run_test_target():
        result = dsl_run(
            add_kernel,
            (out, lhs, rhs),
            "default-lowering",
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
    pipeline = _build_default_lowering_pipeline()
    out = torch.empty((6,), dtype=torch.int32)
    lhs = np.array([11, 12, 13, 14, 15, 16], dtype=np.int32)
    rhs = torch.tensor([1, 2, 3, 4, 5, 6], dtype=torch.int32)
    expected = torch.from_numpy(lhs) + rhs

    with _use_dsl_run_test_target():
        result = dsl_run(
            add_kernel,
            [out, lhs, rhs],
            pipeline,
            EmitCContext(target="npu_demo"),
        )

    _assert_result_contract(result, out, expected)


# TC-DSL-RUN-003
# 创建者: 朽木露琪亚
# 最后一次更改: 朽木露琪亚
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

    with _use_dsl_run_test_target():
        result = dsl_run(
            add_kernel,
            (out, lhs, rhs),
            "default-lowering",
            EmitCContext(target="npu_demo"),
        )

    _assert_result_contract(result, out, expected)


# TC-DSL-RUN-004
# 创建者: 朽木露琪亚
# 最后一次更改: 朽木露琪亚
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
            "default-lowering",
            EmitCContext(target="npu_demo"),
        )


# TC-DSL-RUN-005
# 创建者: 朽木露琪亚
# 最后一次更改: 朽木露琪亚
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
        dsl_run(store_add_kernel, (out, lhs, rhs), "default-lowering", None)


# TC-DSL-RUN-006
# 创建者: 朽木露琪亚
# 最后一次更改: 朽木露琪亚
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
        dsl_run(store_add_kernel, (out, lhs, rhs), "default-lowering", object())


# TC-DSL-RUN-007
# 创建者: 朽木露琪亚
# 最后一次更改: 朽木露琪亚
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
# 最后一次更改: 朽木露琪亚
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
# 最后一次更改: 朽木露琪亚
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
        dsl_run(store_add_kernel, (out, lhs, rhs), "default-lowering", EmitCContext(target="npu_demo"))


# TC-DSL-RUN-010
# 创建者: 朽木露琪亚
# 最后一次更改: 朽木露琪亚
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
        dsl_run(store_add_kernel, (out, lhs), "default-lowering", EmitCContext(target="npu_demo"))


# TC-DSL-RUN-011
# 创建者: 朽木露琪亚
# 最后一次更改: 朽木露琪亚
# 最近一次运行测试时间: 未运行
# 最近一次运行成功时间: 未运行
# 测试目的: 确认 spec、expectation 与测试文件都已落到当前工作书。
# 对应功能实现文件路径: kernel_gen/tools/dsl_run.py
# 对应 spec 文件路径: spec/tools/dsl_run.md
# 对应测试文件路径: test/tools/test_dsl_run.py
def test_dsl_run_contract_files_exist() -> None:
    assert (REPO_ROOT / "spec/tools/dsl_run.md").is_file()
    assert (REPO_ROOT / "expectation/tools/dsl_run/add.py").is_file()
    assert (REPO_ROOT / "expectation/tools/dsl_run/invalid_contract.py").is_file()
    assert (REPO_ROOT / "expectation/tools/dsl_run/__main__.py").is_file()
    assert (REPO_ROOT / "kernel_gen/tools/dsl_run.py").is_file()
