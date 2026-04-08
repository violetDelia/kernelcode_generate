"""execute_engine invoke contract tests (P0 skeleton).

创建者: 朽木露琪亚
最后一次更改: jcc你莫辜负

功能说明:
- 验证 `CompiledKernel.execute(...)` 的输入校验、参数绑定与失败短语合同（P0/S3）。
- 本阶段不要求真实运行，只固定：
  - runtime_throw_or_abort：参数形态错误/类型不匹配；
  - symbol_resolve_failed：entry_point 为空或不匹配；
  - ExecuteRequest 的字段覆盖优先级。

使用示例:
- pytest -q test/execute_engine/test_execute_engine_invoke.py

当前覆盖率信息:
- `kernel_gen.execute_engine.execution_engine`：`82%`（Stmts=134 Miss=17 Branch=40 BrPart=15；最近一次统计：2026-04-07 02:12:00 +0800）。

覆盖率命令:
- `pytest -q --cov=kernel_gen.execute_engine.execution_engine --cov-branch --cov-report=term-missing test/execute_engine/test_execute_engine_invoke.py`

关联文件:
- 功能实现: kernel_gen/execute_engine/execution_engine.py
- Spec 文档: spec/execute_engine/execute_engine.md
- Spec 文档: spec/execute_engine/execute_engine_api.md
- 测试文件: test/execute_engine/test_execute_engine_invoke.py
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from kernel_gen.execute_engine import (
    FAILURE_RUNTIME_THROW_OR_ABORT,
    FAILURE_SYMBOL_RESOLVE_FAILED,
    CompiledKernel,
    ExecuteRequest,
    ExecutionEngine,
    ExecutionEngineError,
)


def _compile_minimal_kernel() -> CompiledKernel:
    """编译最小可执行 kernel（P0）。

    创建者: 朽木露琪亚
    最后一次更改: 朽木露琪亚

    功能说明:
    - 为 invoke 侧测试提供稳定 `CompiledKernel` 实例，避免在每个 case 里重复样板代码。
    - 本阶段不要求真实编译，返回值来自 `ExecutionEngine.compile` 的骨架产物。

    使用示例:
    - kernel = _compile_minimal_kernel()
    - _ = kernel.execute(args=())

    关联文件:
    - spec: spec/execute_engine/execute_engine.md
    - test: test/execute_engine/test_execute_engine_invoke.py
    - 功能实现: kernel_gen/execute_engine/execution_engine.py
    """

    engine = ExecutionEngine(target="cpu")
    return engine.compile(source="int main(){}", function="cpu::add")


class _FakeTorchTensor:
    """最小 torch 张量占位（P0/S3）。

    创建者: jcc你莫辜负
    最后一次更改: jcc你莫辜负

    功能说明:
    - 提供 shape/dtype/stride/is_contiguous 的最小接口，避免测试依赖真实 torch。
    - 仅用于 RuntimeArg 路径校验，不承载真实数据。

    使用示例:
    - tensor = _FakeTorchTensor(shape=(2, 2), dtype="torch.float32")

    关联文件:
    - spec: spec/execute_engine/execute_engine_api.md
    - test: test/execute_engine/test_execute_engine_invoke.py
    - 功能实现: kernel_gen/execute_engine/execution_engine.py
    """

    __module__ = "torch"

    def __init__(
        self,
        *,
        shape: tuple[int, ...],
        dtype: str,
        stride: tuple[int, ...] | None = None,
        contiguous: bool = True,
    ) -> None:
        self.shape = shape
        self.dtype = dtype
        self._stride = stride
        self._contiguous = contiguous

    def stride(self) -> tuple[int, ...] | None:
        """返回 stride 信息。

        创建者: jcc你莫辜负
        最后一次更改: jcc你莫辜负

        功能说明:
        - 提供 stride 读取接口，供 RuntimeArg 校验使用。

        使用示例:
        - tensor = _FakeTorchTensor(shape=(1,), dtype="float32", stride=(1,))
        - assert tensor.stride() == (1,)

        关联文件:
        - spec: spec/execute_engine/execute_engine_api.md
        - test: test/execute_engine/test_execute_engine_invoke.py
        - 功能实现: kernel_gen/execute_engine/execution_engine.py
        """

        return self._stride

    def is_contiguous(self) -> bool:
        """返回是否连续布局。

        创建者: jcc你莫辜负
        最后一次更改: jcc你莫辜负

        功能说明:
        - 提供连续布局标记，供 RuntimeArg 校验使用。

        使用示例:
        - tensor = _FakeTorchTensor(shape=(1,), dtype="float32", contiguous=True)
        - assert tensor.is_contiguous() is True

        关联文件:
        - spec: spec/execute_engine/execute_engine_api.md
        - test: test/execute_engine/test_execute_engine_invoke.py
        - 功能实现: kernel_gen/execute_engine/execution_engine.py
        """

        return self._contiguous


class _FakeNumpyArray:
    """最小 numpy 数组占位（P0/S3）。

    创建者: jcc你莫辜负
    最后一次更改: jcc你莫辜负

    功能说明:
    - 提供 shape/dtype/strides/flags 的最小接口，避免测试依赖真实 numpy。
    - 仅用于 RuntimeArg 路径校验，不承载真实数据。

    使用示例:
    - array = _FakeNumpyArray(shape=(2, 2), dtype="float32")

    关联文件:
    - spec: spec/execute_engine/execute_engine_api.md
    - test: test/execute_engine/test_execute_engine_invoke.py
    - 功能实现: kernel_gen/execute_engine/execution_engine.py
    """

    __module__ = "numpy"

    def __init__(
        self,
        *,
        shape: tuple[int, ...],
        dtype: str,
        strides: tuple[int, ...] | None = None,
        contiguous: bool = True,
    ) -> None:
        self.shape = shape
        self.dtype = dtype
        self.strides = strides
        self.flags = {"C_CONTIGUOUS": contiguous}


# EE-S1-I-001
# 创建者: 朽木露琪亚
# 最后一次更改: 朽木露琪亚
# 最近一次运行测试时间: 2026-04-08 09:41:08 +0800
# 最近一次运行成功时间: 2026-04-08 09:41:08 +0800
# 测试目的: 验证 ExecuteRequest 路径下 args 能正常传入且成功返回 ok=True。
# 对应功能实现文件路径: kernel_gen/execute_engine/execution_engine.py
# 对应 spec 文件路径: spec/execute_engine/execute_engine_api.md
# 对应测试文件路径: test/execute_engine/test_execute_engine_invoke.py
def test_execute_engine_invoke_ok_via_request_args() -> None:
    kernel = _compile_minimal_kernel()
    result = kernel.execute(request=ExecuteRequest(args=()))
    assert result.ok is True
    assert result.failure_phrase is None


# EE-S1-I-002
# 创建者: 朽木露琪亚
# 最后一次更改: 朽木露琪亚
# 最近一次运行测试时间: 2026-04-08 09:41:08 +0800
# 最近一次运行成功时间: 2026-04-08 09:41:08 +0800
# 测试目的: 验证 args 未提供时触发 runtime_throw_or_abort。
# 对应功能实现文件路径: kernel_gen/execute_engine/execution_engine.py
# 对应 spec 文件路径: spec/execute_engine/execute_engine.md
# 对应测试文件路径: test/execute_engine/test_execute_engine_invoke.py
def test_execute_engine_invoke_runtime_throw_or_abort_on_args_none() -> None:
    kernel = _compile_minimal_kernel()
    with pytest.raises(ExecutionEngineError) as exc:
        kernel.execute()
    assert exc.value.failure_phrase == FAILURE_RUNTIME_THROW_OR_ABORT


# EE-S1-I-003
# 创建者: 朽木露琪亚
# 最后一次更改: 朽木露琪亚
# 最近一次运行测试时间: 2026-04-08 09:41:08 +0800
# 最近一次运行成功时间: 2026-04-08 09:41:08 +0800
# 测试目的: 验证 args 非 tuple 时触发 runtime_throw_or_abort。
# 对应功能实现文件路径: kernel_gen/execute_engine/execution_engine.py
# 对应 spec 文件路径: spec/execute_engine/execute_engine.md
# 对应测试文件路径: test/execute_engine/test_execute_engine_invoke.py
def test_execute_engine_invoke_runtime_throw_or_abort_on_args_not_tuple() -> None:
    kernel = _compile_minimal_kernel()
    with pytest.raises(ExecutionEngineError) as exc:
        kernel.execute(args=[])  # type: ignore[arg-type]
    assert exc.value.failure_phrase == FAILURE_RUNTIME_THROW_OR_ABORT


# EE-S1-I-004
# 创建者: 朽木露琪亚
# 最后一次更改: jcc你莫辜负
# 最近一次运行测试时间: 2026-04-08 09:41:08 +0800
# 最近一次运行成功时间: 2026-04-08 09:41:08 +0800
# 测试目的: 验证 args 元素不属于已支持 RuntimeArg 时触发 runtime_throw_or_abort。
# 对应功能实现文件路径: kernel_gen/execute_engine/execution_engine.py
# 对应 spec 文件路径: spec/execute_engine/execute_engine.md
# 对应测试文件路径: test/execute_engine/test_execute_engine_invoke.py
def test_execute_engine_invoke_runtime_throw_or_abort_on_unsupported_runtime_arg() -> None:
    kernel = _compile_minimal_kernel()
    with pytest.raises(ExecutionEngineError) as exc:
        kernel.execute(args=(True,))  # type: ignore[arg-type]
    assert exc.value.failure_phrase == FAILURE_RUNTIME_THROW_OR_ABORT


# EE-S1-I-005
# 创建者: 朽木露琪亚
# 最后一次更改: 朽木露琪亚
# 最近一次运行测试时间: 2026-04-08 09:41:08 +0800
# 最近一次运行成功时间: 2026-04-08 09:41:08 +0800
# 测试目的: 验证 entry_point 为空时触发 symbol_resolve_failed。
# 对应功能实现文件路径: kernel_gen/execute_engine/execution_engine.py
# 对应 spec 文件路径: spec/execute_engine/execute_engine_api.md
# 对应测试文件路径: test/execute_engine/test_execute_engine_invoke.py
def test_execute_engine_invoke_symbol_resolve_failed_on_empty_entry_point() -> None:
    kernel = _compile_minimal_kernel()
    with pytest.raises(ExecutionEngineError) as exc:
        kernel.execute(request=ExecuteRequest(args=(), entry_point=" "))
    assert exc.value.failure_phrase == FAILURE_SYMBOL_RESOLVE_FAILED


# EE-S3-I-001
# 创建者: jcc你莫辜负
# 最后一次更改: jcc你莫辜负
# 最近一次运行测试时间: 2026-04-08 09:41:08 +0800
# 最近一次运行成功时间: 2026-04-08 09:41:08 +0800
# 功能说明: 覆盖 torch/numpy/int/float 运行参数的顺序绑定与执行成功口径。
# 使用示例: pytest -q test/execute_engine/test_execute_engine_invoke.py -k "S3-I-001"
# 测试目的: 验证运行参数绑定成功时返回 ok=True 且 compile stdout/stderr 透传。
# 对应功能实现文件路径: kernel_gen/execute_engine/execution_engine.py
# 对应 spec 文件路径: spec/execute_engine/execute_engine_api.md
# 对应测试文件路径: test/execute_engine/test_execute_engine_invoke.py
def test_execute_engine_invoke_ok_with_memory_int_float_args() -> None:
    kernel = _compile_minimal_kernel()
    out = _FakeTorchTensor(shape=(2, 2), dtype="torch.float32")
    rhs = _FakeNumpyArray(shape=(2, 2), dtype="float32")
    result = kernel.execute(args=(out, rhs, 7, 1.25))
    assert result.ok is True
    assert result.status_code == 0
    assert result.failure_phrase is None
    assert result.compile_stdout == kernel.compile_stdout
    assert result.compile_stderr == kernel.compile_stderr


# EE-S3-I-002
# 创建者: jcc你莫辜负
# 最后一次更改: jcc你莫辜负
# 最近一次运行测试时间: 2026-04-08 09:41:08 +0800
# 最近一次运行成功时间: 2026-04-08 09:41:08 +0800
# 功能说明: 覆盖 entry_point 不匹配时的固定失败短语。
# 使用示例: pytest -q test/execute_engine/test_execute_engine_invoke.py -k "S3-I-002"
# 测试目的: 验证 entry_point 与编译产物不一致时返回 symbol_resolve_failed。
# 对应功能实现文件路径: kernel_gen/execute_engine/execution_engine.py
# 对应 spec 文件路径: spec/execute_engine/execute_engine_api.md
# 对应测试文件路径: test/execute_engine/test_execute_engine_invoke.py
def test_execute_engine_invoke_symbol_resolve_failed_on_entry_point_mismatch() -> None:
    kernel = _compile_minimal_kernel()
    with pytest.raises(ExecutionEngineError) as exc:
        kernel.execute(args=(), entry_point="kg_execute_entry_v2")
    assert exc.value.failure_phrase == FAILURE_SYMBOL_RESOLVE_FAILED


# EE-S3-I-003
# 创建者: jcc你莫辜负
# 最后一次更改: jcc你莫辜负
# 最近一次运行测试时间: 2026-04-08 09:41:08 +0800
# 最近一次运行成功时间: 2026-04-08 09:41:08 +0800
# 功能说明: 覆盖 memory 参数非连续布局的拒绝路径。
# 使用示例: pytest -q test/execute_engine/test_execute_engine_invoke.py -k "S3-I-003"
# 测试目的: 验证 memory 参数不可连续时返回 runtime_throw_or_abort。
# 对应功能实现文件路径: kernel_gen/execute_engine/execution_engine.py
# 对应 spec 文件路径: spec/execute_engine/execute_engine_api.md
# 对应测试文件路径: test/execute_engine/test_execute_engine_invoke.py
def test_execute_engine_invoke_runtime_throw_or_abort_on_memory_not_contiguous() -> None:
    kernel = _compile_minimal_kernel()
    value = _FakeTorchTensor(shape=(2, 2), dtype="float32", contiguous=False)
    with pytest.raises(ExecutionEngineError) as exc:
        kernel.execute(args=(value,))
    assert exc.value.failure_phrase == FAILURE_RUNTIME_THROW_OR_ABORT


# EE-S3-I-004
# 创建者: jcc你莫辜负
# 最后一次更改: jcc你莫辜负
# 最近一次运行测试时间: 2026-04-08 09:41:08 +0800
# 最近一次运行成功时间: 2026-04-08 09:41:08 +0800
# 功能说明: 覆盖 memory 参数 dtype 缺失的拒绝路径。
# 使用示例: pytest -q test/execute_engine/test_execute_engine_invoke.py -k "S3-I-004"
# 测试目的: 验证 memory 参数 dtype 为空时返回 runtime_throw_or_abort。
# 对应功能实现文件路径: kernel_gen/execute_engine/execution_engine.py
# 对应 spec 文件路径: spec/execute_engine/execute_engine_api.md
# 对应测试文件路径: test/execute_engine/test_execute_engine_invoke.py
def test_execute_engine_invoke_runtime_throw_or_abort_on_memory_dtype_missing() -> None:
    kernel = _compile_minimal_kernel()
    value = _FakeTorchTensor(shape=(2, 2), dtype="")
    with pytest.raises(ExecutionEngineError) as exc:
        kernel.execute(args=(value,))
    assert exc.value.failure_phrase == FAILURE_RUNTIME_THROW_OR_ABORT
