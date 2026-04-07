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
    FloatArg,
    IntArg,
    MemoryArg,
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


class _FakeTensor:
    """最小可用的张量占位（P0/S3）。

    创建者: jcc你莫辜负
    最后一次更改: jcc你莫辜负

    功能说明:
    - 用于模拟 torch/numpy 的最小 shape/dtype 接口，避免测试引入重依赖。
    - 仅覆盖 shape/dtype/stride 访问，不包含真实数据。

    使用示例:
    - tensor = _FakeTensor(shape=(2, 2), dtype="torch.float32")

    关联文件:
    - spec: spec/execute_engine/execute_engine_api.md
    - test: test/execute_engine/test_execute_engine_invoke.py
    - 功能实现: kernel_gen/execute_engine/execution_engine.py
    """

    def __init__(self, *, shape: tuple[int, ...], dtype: str, stride: tuple[int, ...] | None = None) -> None:
        self.shape = shape
        self.dtype = dtype
        self._stride = stride

    def stride(self) -> tuple[int, ...] | None:
        return self._stride


# EE-S1-I-001
# 创建者: 朽木露琪亚
# 最后一次更改: 朽木露琪亚
# 最近一次运行测试时间: 2026-04-07 02:12:00 +0800
# 最近一次运行成功时间: 2026-04-07 02:12:00 +0800
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
# 最近一次运行测试时间: 2026-04-07 02:12:00 +0800
# 最近一次运行成功时间: 2026-04-07 02:12:00 +0800
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
# 最近一次运行测试时间: 2026-04-07 02:12:00 +0800
# 最近一次运行成功时间: 2026-04-07 02:12:00 +0800
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
# 最后一次更改: 朽木露琪亚
# 最近一次运行测试时间: 2026-04-07 02:12:00 +0800
# 最近一次运行成功时间: 2026-04-07 02:12:00 +0800
# 测试目的: 验证 args 元素不属于已支持 ArgSpec 时触发 runtime_throw_or_abort。
# 对应功能实现文件路径: kernel_gen/execute_engine/execution_engine.py
# 对应 spec 文件路径: spec/execute_engine/execute_engine.md
# 对应测试文件路径: test/execute_engine/test_execute_engine_invoke.py
def test_execute_engine_invoke_runtime_throw_or_abort_on_unsupported_argspec() -> None:
    kernel = _compile_minimal_kernel()
    with pytest.raises(ExecutionEngineError) as exc:
        kernel.execute(args=(object(),))  # type: ignore[arg-type]
    assert exc.value.failure_phrase == FAILURE_RUNTIME_THROW_OR_ABORT


# EE-S1-I-005
# 创建者: 朽木露琪亚
# 最后一次更改: 朽木露琪亚
# 最近一次运行测试时间: 2026-04-07 02:12:00 +0800
# 最近一次运行成功时间: 2026-04-07 02:12:00 +0800
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
# 最近一次运行测试时间: 2026-04-07 14:35:00 +0800
# 最近一次运行成功时间: 2026-04-07 14:35:00 +0800
# 功能说明: 覆盖 memory/int/float 三类参数的顺序绑定与执行成功口径。
# 使用示例: pytest -q test/execute_engine/test_execute_engine_invoke.py -k "S3-I-001"
# 测试目的: 验证参数绑定成功时返回 ok=True 且 compile stdout/stderr 透传。
# 对应功能实现文件路径: kernel_gen/execute_engine/execution_engine.py
# 对应 spec 文件路径: spec/execute_engine/execute_engine_api.md
# 对应测试文件路径: test/execute_engine/test_execute_engine_invoke.py
def test_execute_engine_invoke_ok_with_memory_int_float_args() -> None:
    kernel = _compile_minimal_kernel()
    value = _FakeTensor(shape=(2, 2), dtype="torch.float32")
    memory_arg = MemoryArg(
        position=0,
        param_name="lhs",
        space="global",
        dtype="float32",
        shape=(2, 2),
        stride=None,
        value=value,
    )
    int_arg = IntArg(position=1, param_name="scale", dtype="int32", value=7)
    float_arg = FloatArg(position=2, param_name="alpha", dtype="float32", value=1.25)
    result = kernel.execute(args=(memory_arg, int_arg, float_arg))
    assert result.ok is True
    assert result.status_code == 0
    assert result.failure_phrase is None
    assert result.compile_stdout == kernel.compile_stdout
    assert result.compile_stderr == kernel.compile_stderr


# EE-S3-I-002
# 创建者: jcc你莫辜负
# 最后一次更改: jcc你莫辜负
# 最近一次运行测试时间: 2026-04-07 14:35:00 +0800
# 最近一次运行成功时间: 2026-04-07 14:35:00 +0800
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
# 最近一次运行测试时间: 2026-04-07 14:35:00 +0800
# 最近一次运行成功时间: 2026-04-07 14:35:00 +0800
# 功能说明: 覆盖 memory 参数 shape 不一致的拒绝路径。
# 使用示例: pytest -q test/execute_engine/test_execute_engine_invoke.py -k "S3-I-003"
# 测试目的: 验证 MemoryArg 与 value 不一致时返回 runtime_throw_or_abort。
# 对应功能实现文件路径: kernel_gen/execute_engine/execution_engine.py
# 对应 spec 文件路径: spec/execute_engine/execute_engine_api.md
# 对应测试文件路径: test/execute_engine/test_execute_engine_invoke.py
def test_execute_engine_invoke_runtime_throw_or_abort_on_memory_shape_mismatch() -> None:
    kernel = _compile_minimal_kernel()
    value = _FakeTensor(shape=(2, 2), dtype="float32")
    memory_arg = MemoryArg(
        position=0,
        param_name="lhs",
        space="global",
        dtype="float32",
        shape=(1, 2),
        stride=None,
        value=value,
    )
    with pytest.raises(ExecutionEngineError) as exc:
        kernel.execute(args=(memory_arg,))
    assert exc.value.failure_phrase == FAILURE_RUNTIME_THROW_OR_ABORT


# EE-S3-I-004
# 创建者: jcc你莫辜负
# 最后一次更改: jcc你莫辜负
# 最近一次运行测试时间: 2026-04-07 14:35:00 +0800
# 最近一次运行成功时间: 2026-04-07 14:35:00 +0800
# 功能说明: 覆盖 IntArg dtype 不一致的拒绝路径。
# 使用示例: pytest -q test/execute_engine/test_execute_engine_invoke.py -k "S3-I-004"
# 测试目的: 验证 IntArg dtype 不匹配时返回 runtime_throw_or_abort。
# 对应功能实现文件路径: kernel_gen/execute_engine/execution_engine.py
# 对应 spec 文件路径: spec/execute_engine/execute_engine_api.md
# 对应测试文件路径: test/execute_engine/test_execute_engine_invoke.py
def test_execute_engine_invoke_runtime_throw_or_abort_on_int_dtype_mismatch() -> None:
    kernel = _compile_minimal_kernel()
    int_arg = IntArg(position=0, param_name="rhs", dtype="float32", value=1)
    with pytest.raises(ExecutionEngineError) as exc:
        kernel.execute(args=(int_arg,))
    assert exc.value.failure_phrase == FAILURE_RUNTIME_THROW_OR_ABORT
