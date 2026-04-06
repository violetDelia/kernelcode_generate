"""execute_engine invoke contract tests (P0 skeleton).

创建者: 朽木露琪亚
最后一次更改: 朽木露琪亚

功能说明:
- 验证 `CompiledKernel.execute(...)` 的输入校验与失败短语合同（P0）。
- 本阶段不要求真实运行，只固定：
  - runtime_throw_or_abort：参数形态错误/不支持 ArgSpec；
  - symbol_resolve_failed：entry_point 为空；
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
