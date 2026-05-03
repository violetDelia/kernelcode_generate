"""execute_engine compile contract tests (P0 skeleton).


功能说明:
- 验证 `ExecutionEngine.compile(...)` 的输入校验与失败短语合同（P0）。
- 本阶段不要求真实编译器执行，仅要求 failure_phrase 可稳定机械匹配。

使用示例:
- pytest -q test/execute_engine/test_compile.py

当前覆盖率信息:
- `kernel_gen.execute_engine.compiler`：`70%`（Stmts=134 Miss=30 Branch=40 BrPart=7；最近一次统计：2026-04-07 02:12:00 +0800）。

覆盖率命令:
- `pytest -q --cov=kernel_gen.execute_engine.compiler --cov-branch --cov-report=term-missing test/execute_engine/test_compile.py`

关联文件:
- 功能实现: kernel_gen/execute_engine/compiler.py
- Spec 文档: spec/execute_engine/execute_engine.md
- Spec 文档: spec/execute_engine/execute_engine_target.md
- 测试文件: test/execute_engine/test_compile.py
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from kernel_gen.core.error import KernelCodeError
from kernel_gen.execute_engine import (
    CompileRequest,
    ExecutionEngine,
)


# EE-S1-C-001
# 测试目的: 验证源码为空时返回 source_empty_or_invalid。
# 对应功能实现文件路径: kernel_gen/execute_engine/compiler.py
# 对应 spec 文件路径: spec/execute_engine/execute_engine.md
# 对应测试文件路径: test/execute_engine/test_compile.py
def test_execute_engine_compile_source_empty_or_invalid() -> None:
    engine = ExecutionEngine(target="cpu")
    with pytest.raises(KernelCodeError) as exc:
        engine.compile(source="  ", function="cpu::add")
    assert exc.value.failure_phrase == "source_empty_or_invalid"


# EE-S1-C-002
# 测试目的: 验证 function 为空时返回 symbol_resolve_failed。
# 对应功能实现文件路径: kernel_gen/execute_engine/compiler.py
# 对应 spec 文件路径: spec/execute_engine/execute_engine.md
# 对应测试文件路径: test/execute_engine/test_compile.py
def test_execute_engine_compile_function_empty_symbol_resolve_failed() -> None:
    engine = ExecutionEngine(target="cpu")
    with pytest.raises(KernelCodeError) as exc:
        engine.compile(source="int main(){}", function=" ")
    assert exc.value.failure_phrase == "symbol_resolve_failed"


# EE-S1-C-003
# 测试目的: 验证 entry_point 为空时返回 symbol_resolve_failed。
# 对应功能实现文件路径: kernel_gen/execute_engine/compiler.py
# 对应 spec 文件路径: spec/execute_engine/execute_engine_target.md
# 对应测试文件路径: test/execute_engine/test_compile.py
def test_execute_engine_compile_entry_point_empty_symbol_resolve_failed() -> None:
    engine = ExecutionEngine(target="cpu")
    with pytest.raises(KernelCodeError) as exc:
        engine.compile(source="int main(){}", function="cpu::add", entry_point=" ")
    assert exc.value.failure_phrase == "symbol_resolve_failed"


# EE-S1-C-004
# 测试目的: 验证 source 的 include family 与 target 不一致时返回 target_header_mismatch。
# 对应功能实现文件路径: kernel_gen/execute_engine/compiler.py
# 对应 spec 文件路径: spec/execute_engine/execute_engine_target.md
# 对应测试文件路径: test/execute_engine/test_compile.py
def test_execute_engine_compile_target_header_mismatch_on_source_include_family() -> None:
    engine = ExecutionEngine(target="npu_demo")
    cpu_source = '#include "include/cpu/Memory.h"\nint main(){}'
    with pytest.raises(KernelCodeError) as exc:
        engine.compile(source=cpu_source, function="npu_demo::add")
    assert exc.value.failure_phrase == "target_header_mismatch"


# EE-S1-C-005
# 测试目的: 验证 source 含 #error 指令时返回 compile_failed。
# 对应功能实现文件路径: kernel_gen/execute_engine/compiler.py
# 对应 spec 文件路径: spec/execute_engine/execute_engine.md
# 对应测试文件路径: test/execute_engine/test_compile.py
def test_execute_engine_compile_failed_on_error_directive() -> None:
    engine = ExecutionEngine(target="cpu")
    source = "#error force compile failed\nint main(){}"
    with pytest.raises(KernelCodeError) as exc:
        engine.compile(source=source, function="cpu::add")
    assert exc.value.failure_phrase == "compile_failed"


# EE-S2-C-001
# 功能说明: 覆盖编译单元拼装的 include 与 entry shim 注入规则。
# 使用示例: pytest -q test/execute_engine/test_compile.py -k "S2-C-001"
# 测试目的: 验证编译单元拼装包含 target include 与 entry shim。
# 对应功能实现文件路径: kernel_gen/execute_engine/compiler.py
# 对应 spec 文件路径: spec/execute_engine/execute_engine_target.md
# 对应测试文件路径: test/execute_engine/test_compile.py
def test_execute_engine_compile_unit_injects_includes_and_shim() -> None:
    source = "int add(int a, int b) { return a + b; }\n"
    engine = ExecutionEngine(target="cpu")
    kernel = engine.compile(source=source, function="cpu::add")
    try:
        unit = (Path(kernel.soname_path).parent / "kernel.cpp").read_text(encoding="utf-8")
        assert '#include "include/cpu/Memory.h"' in unit
        assert '#include "include/cpu/Nn.h"' in unit
        assert 'extern "C" int kg_execute_entry' in unit
        assert "int add" in unit
    finally:
        kernel.close()


# EE-S2-C-002
# 功能说明: 覆盖 compile 成功路径与编译命令生成。
# 使用示例: pytest -q test/execute_engine/test_compile.py -k "S2-C-002"
# 测试目的: 验证 compile 成功返回 CompiledKernel 并生成编译命令。
# 对应功能实现文件路径: kernel_gen/execute_engine/compiler.py
# 对应 spec 文件路径: spec/execute_engine/execute_engine_target.md
# 对应测试文件路径: test/execute_engine/test_compile.py
def test_execute_engine_compile_returns_kernel_with_command() -> None:
    engine = ExecutionEngine(target="cpu")
    kernel = engine.compile(source="int main(){}", function="cpu::add")
    try:
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
    finally:
        kernel.close()


# EE-S5-C-004
# 功能说明: 覆盖编译产物 close() 的临时工作区释放与幂等行为。
# 使用示例: pytest -q test/execute_engine/test_compile.py -k "S5-C-004"
# 测试目的: 验证 compile 过程中创建的临时工作区会在 close() 后被移除，且重复 close 安全。
# 对应功能实现文件路径: kernel_gen/execute_engine/compiler.py
# 对应 spec 文件路径: spec/execute_engine/execute_engine.md
# 对应测试文件路径: test/execute_engine/test_compile.py
def test_execute_engine_compile_close_releases_temp_workdir_and_is_idempotent() -> None:
    engine = ExecutionEngine(target="cpu")
    kernel = engine.compile(source="int main(){}", function="cpu::add")
    workdir = Path(kernel.soname_path).parent
    try:
        assert workdir.is_dir()

        kernel.close()
        kernel.close()

        assert not workdir.exists()
        with pytest.raises(KernelCodeError) as exc:
            kernel.execute(args=())
        assert exc.value.failure_phrase == "runtime_throw_or_abort"
    finally:
        kernel.close()


# EE-S2-C-003
# 功能说明: 覆盖 CompileRequest 对编译器与 flags 的控制。
# 使用示例: pytest -q test/execute_engine/test_compile.py -k "S2-C-003"
# 测试目的: 验证 CompileRequest 的 compiler 与 flags 参与编译命令构造。
# 对应功能实现文件路径: kernel_gen/execute_engine/compiler.py
# 对应 spec 文件路径: spec/execute_engine/execute_engine_target.md
# 对应测试文件路径: test/execute_engine/test_compile.py
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
    try:
        command = kernel.compile_stdout.replace("dry-run: ", "").split()
        assert command[0] == "clang++"
        assert "-std=c++17" in command
        assert "-O2" in command
        assert command.index("-std=c++17") < command.index("-O2")
        assert "-lm" in command
    finally:
        kernel.close()
