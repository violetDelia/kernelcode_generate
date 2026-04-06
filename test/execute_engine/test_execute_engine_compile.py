"""execute_engine compile contract tests (P0 skeleton).

创建者: 朽木露琪亚
最后一次更改: 朽木露琪亚

功能说明:
- 验证 `ExecutionEngine.compile(...)` 的输入校验与失败短语合同（P0）。
- 本阶段不要求真实编译器执行，仅要求 failure_phrase 可稳定机械匹配。

使用示例:
- pytest -q test/execute_engine/test_execute_engine_compile.py

当前覆盖率信息:
- `kernel_gen.execute_engine.execution_engine`：`70%`（Stmts=134 Miss=30 Branch=40 BrPart=7；最近一次统计：2026-04-07 02:12:00 +0800）。

覆盖率命令:
- `pytest -q --cov=kernel_gen.execute_engine.execution_engine --cov-branch --cov-report=term-missing test/execute_engine/test_execute_engine_compile.py`

关联文件:
- 功能实现: kernel_gen/execute_engine/execution_engine.py
- Spec 文档: spec/execute_engine/execute_engine.md
- Spec 文档: spec/execute_engine/execute_engine_target.md
- 测试文件: test/execute_engine/test_execute_engine_compile.py
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from kernel_gen.execute_engine import (
    FAILURE_COMPILE_FAILED,
    FAILURE_SOURCE_EMPTY_OR_INVALID,
    FAILURE_SYMBOL_RESOLVE_FAILED,
    FAILURE_TARGET_HEADER_MISMATCH,
    ExecutionEngine,
    ExecutionEngineError,
)


# EE-S1-C-001
# 创建者: 朽木露琪亚
# 最后一次更改: 朽木露琪亚
# 最近一次运行测试时间: 2026-04-07 02:12:00 +0800
# 最近一次运行成功时间: 2026-04-07 02:12:00 +0800
# 测试目的: 验证源码为空时返回 source_empty_or_invalid。
# 对应功能实现文件路径: kernel_gen/execute_engine/execution_engine.py
# 对应 spec 文件路径: spec/execute_engine/execute_engine.md
# 对应测试文件路径: test/execute_engine/test_execute_engine_compile.py
def test_execute_engine_compile_source_empty_or_invalid() -> None:
    engine = ExecutionEngine(target="cpu")
    with pytest.raises(ExecutionEngineError) as exc:
        engine.compile(source="  ", function="cpu::add")
    assert exc.value.failure_phrase == FAILURE_SOURCE_EMPTY_OR_INVALID


# EE-S1-C-002
# 创建者: 朽木露琪亚
# 最后一次更改: 朽木露琪亚
# 最近一次运行测试时间: 2026-04-07 02:12:00 +0800
# 最近一次运行成功时间: 2026-04-07 02:12:00 +0800
# 测试目的: 验证 function 为空时返回 symbol_resolve_failed。
# 对应功能实现文件路径: kernel_gen/execute_engine/execution_engine.py
# 对应 spec 文件路径: spec/execute_engine/execute_engine.md
# 对应测试文件路径: test/execute_engine/test_execute_engine_compile.py
def test_execute_engine_compile_function_empty_symbol_resolve_failed() -> None:
    engine = ExecutionEngine(target="cpu")
    with pytest.raises(ExecutionEngineError) as exc:
        engine.compile(source="int main(){}", function=" ")
    assert exc.value.failure_phrase == FAILURE_SYMBOL_RESOLVE_FAILED


# EE-S1-C-003
# 创建者: 朽木露琪亚
# 最后一次更改: 朽木露琪亚
# 最近一次运行测试时间: 2026-04-07 02:12:00 +0800
# 最近一次运行成功时间: 2026-04-07 02:12:00 +0800
# 测试目的: 验证 entry_point 为空时返回 symbol_resolve_failed。
# 对应功能实现文件路径: kernel_gen/execute_engine/execution_engine.py
# 对应 spec 文件路径: spec/execute_engine/execute_engine_target.md
# 对应测试文件路径: test/execute_engine/test_execute_engine_compile.py
def test_execute_engine_compile_entry_point_empty_symbol_resolve_failed() -> None:
    engine = ExecutionEngine(target="cpu")
    with pytest.raises(ExecutionEngineError) as exc:
        engine.compile(source="int main(){}", function="cpu::add", entry_point=" ")
    assert exc.value.failure_phrase == FAILURE_SYMBOL_RESOLVE_FAILED


# EE-S1-C-004
# 创建者: 朽木露琪亚
# 最后一次更改: 朽木露琪亚
# 最近一次运行测试时间: 2026-04-07 02:12:00 +0800
# 最近一次运行成功时间: 2026-04-07 02:12:00 +0800
# 测试目的: 验证 source 的 include family 与 target 不一致时返回 target_header_mismatch。
# 对应功能实现文件路径: kernel_gen/execute_engine/execution_engine.py
# 对应 spec 文件路径: spec/execute_engine/execute_engine_target.md
# 对应测试文件路径: test/execute_engine/test_execute_engine_compile.py
def test_execute_engine_compile_target_header_mismatch_on_source_include_family() -> None:
    engine = ExecutionEngine(target="npu_demo")
    cpu_source = '#include "include/cpu/Memory.h"\nint main(){}'
    with pytest.raises(ExecutionEngineError) as exc:
        engine.compile(source=cpu_source, function="npu_demo::add")
    assert exc.value.failure_phrase == FAILURE_TARGET_HEADER_MISMATCH


# EE-S1-C-005
# 创建者: 朽木露琪亚
# 最后一次更改: 朽木露琪亚
# 最近一次运行测试时间: 2026-04-07 02:12:00 +0800
# 最近一次运行成功时间: 2026-04-07 02:12:00 +0800
# 测试目的: 验证 source 含 #error 指令时返回 compile_failed。
# 对应功能实现文件路径: kernel_gen/execute_engine/execution_engine.py
# 对应 spec 文件路径: spec/execute_engine/execute_engine.md
# 对应测试文件路径: test/execute_engine/test_execute_engine_compile.py
def test_execute_engine_compile_failed_on_error_directive() -> None:
    engine = ExecutionEngine(target="cpu")
    source = "#error force compile failed\nint main(){}"
    with pytest.raises(ExecutionEngineError) as exc:
        engine.compile(source=source, function="cpu::add")
    assert exc.value.failure_phrase == FAILURE_COMPILE_FAILED
