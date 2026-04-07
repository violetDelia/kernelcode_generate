"""execute_engine compile contract tests (P0 skeleton).

创建者: 朽木露琪亚
最后一次更改: jcc你莫辜负

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
    CompileRequest,
    ExecutionEngine,
    ExecutionEngineError,
)
from kernel_gen.execute_engine.compiler import build_compile_unit
from kernel_gen.execute_engine.entry_shim_builder import (
    build_entry_shim_source,
    needs_entry_shim,
)
from kernel_gen.execute_engine.target_registry import target_includes


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


# EE-S2-C-001
# 创建者: jcc你莫辜负
# 最后一次更改: jcc你莫辜负
# 最近一次运行测试时间: 2026-04-07 13:35:00 +0800
# 最近一次运行成功时间: 2026-04-07 13:35:00 +0800
# 功能说明: 覆盖编译单元拼装的 include 与 entry shim 注入规则。
# 使用示例: pytest -q test/execute_engine/test_execute_engine_compile.py -k "S2-C-001"
# 测试目的: 验证编译单元拼装包含 target include 与 entry shim。
# 对应功能实现文件路径: kernel_gen/execute_engine/compiler.py
# 对应 spec 文件路径: spec/execute_engine/execute_engine_target.md
# 对应测试文件路径: test/execute_engine/test_execute_engine_compile.py
def test_execute_engine_compile_unit_injects_includes_and_shim() -> None:
    source = "int add(int a, int b) { return a + b; }\n"
    entry_point = "kg_execute_entry"
    includes = target_includes("npu_demo")
    assert needs_entry_shim(source, entry_point) is True
    shim = build_entry_shim_source(function="npu_demo::add", entry_point=entry_point)
    unit = build_compile_unit(
        source=source,
        target_includes=includes,
        entry_shim_source=shim,
    )
    for include_line in includes:
        assert include_line in unit
    assert 'extern "C" int kg_execute_entry' in unit
    assert "int add" in unit


# EE-S2-C-002
# 创建者: jcc你莫辜负
# 最后一次更改: jcc你莫辜负
# 最近一次运行测试时间: 2026-04-07 13:35:00 +0800
# 最近一次运行成功时间: 2026-04-07 13:35:00 +0800
# 功能说明: 覆盖 compile 成功路径与编译命令生成。
# 使用示例: pytest -q test/execute_engine/test_execute_engine_compile.py -k "S2-C-002"
# 测试目的: 验证 compile 成功返回 CompiledKernel 并生成编译命令。
# 对应功能实现文件路径: kernel_gen/execute_engine/execution_engine.py
# 对应 spec 文件路径: spec/execute_engine/execute_engine_target.md
# 对应测试文件路径: test/execute_engine/test_execute_engine_compile.py
def test_execute_engine_compile_returns_kernel_with_command() -> None:
    engine = ExecutionEngine(target="cpu")
    kernel = engine.compile(source="int main(){}", function="cpu::add")
    assert kernel.target == "cpu"
    assert kernel.function == "cpu::add"
    assert kernel.entry_point == "kg_execute_entry"
    assert kernel.compile_stdout.startswith("dry-run: ")
    command = kernel.compile_stdout.replace("dry-run: ", "").split()
    assert command[0] == "g++"
    assert "-std=c++17" in command
    assert any(arg.startswith("-I") and str(REPO_ROOT) in arg for arg in command)
    assert "-o" in command
    assert Path(kernel.soname_path).is_file()


# EE-S2-C-003
# 创建者: jcc你莫辜负
# 最后一次更改: jcc你莫辜负
# 最近一次运行测试时间: 2026-04-07 13:35:00 +0800
# 最近一次运行成功时间: 2026-04-07 13:35:00 +0800
# 功能说明: 覆盖 CompileRequest 对编译器与 flags 的控制。
# 使用示例: pytest -q test/execute_engine/test_execute_engine_compile.py -k "S2-C-003"
# 测试目的: 验证 CompileRequest 的 compiler 与 flags 参与编译命令构造。
# 对应功能实现文件路径: kernel_gen/execute_engine/execution_engine.py
# 对应 spec 文件路径: spec/execute_engine/execute_engine_target.md
# 对应测试文件路径: test/execute_engine/test_execute_engine_compile.py
def test_execute_engine_compile_request_compiler_flags_order() -> None:
    req = CompileRequest(
        source="int main(){}",
        target="cpu",
        function="cpu::add",
        compiler="clang++",
        compiler_flags=("-O2",),
        link_flags=("-lm",),
    )
    engine = ExecutionEngine(target="cpu")
    kernel = engine.compile(request=req)
    command = kernel.compile_stdout.replace("dry-run: ", "").split()
    assert command[0] == "clang++"
    assert "-std=c++17" in command
    assert "-O2" in command
    assert command.index("-std=c++17") < command.index("-O2")
    assert "-lm" in command
