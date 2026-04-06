"""execute_engine contract tests (P0 skeleton).

创建者: 朽木露琪亚
最后一次更改: 朽木露琪亚

功能说明:
- 验证 execute_engine 的目录骨架、公开接口命名与公共失败短语合同（P0）。
- 本阶段不要求真实编译/运行，仅验证输入校验与失败短语稳定匹配。

使用示例:
- pytest -q test/execute_engine/test_execute_engine_contract.py

当前覆盖率信息:
- `kernel_gen.execute_engine.execution_engine`：`85%`（Stmts=117 Miss=12 Branch=28 BrPart=8；最近一次统计：2026-04-07 10:25:00 +0800）。

覆盖率命令:
- `pytest -q --cov=kernel_gen.execute_engine.execution_engine --cov-branch --cov-report=term-missing test/execute_engine/test_execute_engine_contract.py`

关联文件:
- 功能实现: kernel_gen/execute_engine/execution_engine.py
- Spec 文档: spec/execute_engine/execute_engine.md
- Spec 文档: spec/execute_engine/execute_engine_api.md
- Spec 文档: spec/execute_engine/execute_engine_target.md
- 测试文件: test/execute_engine/test_execute_engine_contract.py
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from kernel_gen.execute_engine import (
    FAILURE_FUNCTION_OUTPUT_CAPTURE_NOT_SUPPORTED,
    FAILURE_SOURCE_EMPTY_OR_INVALID,
    FAILURE_STREAM_NOT_SUPPORTED,
    FAILURE_TARGET_HEADER_MISMATCH,
    FAILURE_PHRASES,
    ExecuteRequest,
    ExecutionEngine,
    ExecutionEngineError,
)


# EE-S1-000
# 创建者: 朽木露琪亚
# 最后一次更改: 朽木露琪亚
# 最近一次运行测试时间: 2026-04-07 10:25:00 +0800
# 最近一次运行成功时间: 2026-04-07 10:25:00 +0800
# 测试目的: 确认 S1 约定的 spec/test 骨架文件存在。
# 对应功能实现文件路径: kernel_gen/execute_engine/execution_engine.py
# 对应 spec 文件路径: spec/execute_engine/execute_engine.md
# 对应测试文件路径: test/execute_engine/test_execute_engine_contract.py
def test_execute_engine_contract_files_exist() -> None:
    assert (REPO_ROOT / "spec/execute_engine/execute_engine.md").is_file()
    assert (REPO_ROOT / "spec/execute_engine/execute_engine_api.md").is_file()
    assert (REPO_ROOT / "spec/execute_engine/execute_engine_target.md").is_file()
    assert (REPO_ROOT / "test/execute_engine/test_execute_engine_contract.py").is_file()


# EE-S1-001
# 创建者: 朽木露琪亚
# 最后一次更改: 朽木露琪亚
# 最近一次运行测试时间: 2026-04-07 10:25:00 +0800
# 最近一次运行成功时间: 2026-04-07 10:25:00 +0800
# 测试目的: 验证 compile->execute 最小闭环的成功口径（骨架版）。
# 对应功能实现文件路径: kernel_gen/execute_engine/execution_engine.py
# 对应 spec 文件路径: spec/execute_engine/execute_engine.md
# 对应测试文件路径: test/execute_engine/test_execute_engine_contract.py
def test_execute_engine_compile_execute_ok() -> None:
    engine = ExecutionEngine(target="cpu")
    kernel = engine.compile(source="int main(){}", function="cpu::add")
    result = kernel.execute(args=())
    assert result.ok is True
    assert result.status_code == 0
    assert result.failure_phrase is None


# EE-S1-002
# 创建者: 朽木露琪亚
# 最后一次更改: 朽木露琪亚
# 最近一次运行测试时间: 2026-04-07 10:25:00 +0800
# 最近一次运行成功时间: 2026-04-07 10:25:00 +0800
# 测试目的: 验证 stream 非空会触发固定失败短语 stream_not_supported。
# 对应功能实现文件路径: kernel_gen/execute_engine/execution_engine.py
# 对应 spec 文件路径: spec/execute_engine/execute_engine.md
# 对应测试文件路径: test/execute_engine/test_execute_engine_contract.py
def test_execute_engine_stream_not_supported() -> None:
    engine = ExecutionEngine(target="cpu")
    kernel = engine.compile(source="int main(){}", function="cpu::add")
    with pytest.raises(ExecutionEngineError) as exc:
        kernel.execute(request=ExecuteRequest(args=(), stream=object()))
    assert exc.value.failure_phrase == FAILURE_STREAM_NOT_SUPPORTED


# EE-S1-003
# 创建者: 朽木露琪亚
# 最后一次更改: 朽木露琪亚
# 最近一次运行测试时间: 2026-04-07 10:25:00 +0800
# 最近一次运行成功时间: 2026-04-07 10:25:00 +0800
# 测试目的: 验证 capture_function_output=True 会触发固定失败短语 function_output_capture_not_supported。
# 对应功能实现文件路径: kernel_gen/execute_engine/execution_engine.py
# 对应 spec 文件路径: spec/execute_engine/execute_engine.md
# 对应测试文件路径: test/execute_engine/test_execute_engine_contract.py
def test_execute_engine_function_output_capture_not_supported() -> None:
    engine = ExecutionEngine(target="cpu")
    kernel = engine.compile(source="int main(){}", function="cpu::add")
    with pytest.raises(ExecutionEngineError) as exc:
        kernel.execute(request=ExecuteRequest(args=(), capture_function_output=True))
    assert exc.value.failure_phrase == FAILURE_FUNCTION_OUTPUT_CAPTURE_NOT_SUPPORTED


# EE-S1-004
# 创建者: 朽木露琪亚
# 最后一次更改: 朽木露琪亚
# 最近一次运行测试时间: 2026-04-07 10:25:00 +0800
# 最近一次运行成功时间: 2026-04-07 10:25:00 +0800
# 测试目的: 验证空/非法 source 会触发固定失败短语 source_empty_or_invalid。
# 对应功能实现文件路径: kernel_gen/execute_engine/execution_engine.py
# 对应 spec 文件路径: spec/execute_engine/execute_engine.md
# 对应测试文件路径: test/execute_engine/test_execute_engine_contract.py
def test_execute_engine_source_empty_or_invalid() -> None:
    engine = ExecutionEngine(target="cpu")
    with pytest.raises(ExecutionEngineError) as exc:
        engine.compile(source="  ", function="cpu::add")
    assert exc.value.failure_phrase == FAILURE_SOURCE_EMPTY_OR_INVALID


# EE-S1-005
# 创建者: 朽木露琪亚
# 最后一次更改: 朽木露琪亚
# 最近一次运行测试时间: 2026-04-07 10:25:00 +0800
# 最近一次运行成功时间: 2026-04-07 10:25:00 +0800
# 测试目的: 验证不支持的 target 会触发固定失败短语 target_header_mismatch。
# 对应功能实现文件路径: kernel_gen/execute_engine/execution_engine.py
# 对应 spec 文件路径: spec/execute_engine/execute_engine.md
# 对应测试文件路径: test/execute_engine/test_execute_engine_contract.py
def test_execute_engine_target_header_mismatch() -> None:
    engine = ExecutionEngine(target="unknown-target")
    with pytest.raises(ExecutionEngineError) as exc:
        engine.compile(source="int main(){}", function="cpu::add")
    assert exc.value.failure_phrase == FAILURE_TARGET_HEADER_MISMATCH


# EE-S1-006
# 创建者: 朽木露琪亚
# 最后一次更改: 朽木露琪亚
# 最近一次运行测试时间: 2026-04-07 10:25:00 +0800
# 最近一次运行成功时间: 2026-04-07 10:25:00 +0800
# 测试目的: 验证失败短语固定集合不变且可机械比较。
# 对应功能实现文件路径: kernel_gen/execute_engine/execution_engine.py
# 对应 spec 文件路径: spec/execute_engine/execute_engine.md
# 对应测试文件路径: test/execute_engine/test_execute_engine_contract.py
def test_execute_engine_failure_phrases_frozen() -> None:
    assert FAILURE_SOURCE_EMPTY_OR_INVALID in FAILURE_PHRASES
    assert FAILURE_STREAM_NOT_SUPPORTED in FAILURE_PHRASES
    assert FAILURE_FUNCTION_OUTPUT_CAPTURE_NOT_SUPPORTED in FAILURE_PHRASES
    assert FAILURE_TARGET_HEADER_MISMATCH in FAILURE_PHRASES
    assert len(FAILURE_PHRASES) == 7
