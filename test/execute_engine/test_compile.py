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

import random
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from kernel_gen.core.config import reset_config, set_dump_dir, set_trance_enabled
from kernel_gen.core.error import KernelCodeError
from kernel_gen.execute_engine import (
    CompileRequest,
    ExecutionEngine,
)


_COMPILE_TARGET_SOURCE_CASES = tuple(
    random.Random(20260505).sample(
        [
            (
                "cpu-adds-missing-includes-and-runtime-shim",
                "cpu",
                "int add(int lhs, int rhs) { return lhs + rhs; }",
                "add",
                True,
                ('#include "include/cpu/Memory.h"', '#include "include/cpu/Nn.h"'),
                (),
            ),
            (
                "cpu-preserves-existing-extern-entry",
                "cpu",
                'extern "C" int kg_execute_entry(const void*, unsigned long long) { return 0; }\nint add(){ return 0; }',
                "add",
                False,
                ('#include "include/cpu/Memory.h"', '#include "include/cpu/Nn.h"'),
                (),
            ),
            (
                "cpu-only-injects-missing-include",
                "cpu",
                '#include "include/cpu/Memory.h"\nint add(){ return 0; }',
                "add",
                True,
                ('#include "include/cpu/Memory.h"', '#include "include/cpu/Nn.h"'),
                ('#include "include/npu_demo/npu_demo.h"',),
            ),
            (
                "npu-adds-npu-include-and-runtime-shim",
                "npu_demo",
                "int add(int lhs, int rhs) { return lhs + rhs; }",
                "add",
                True,
                ('#include "include/npu_demo/npu_demo.h"',),
                ('#include "include/cpu/Memory.h"', '#include "include/cpu/Nn.h"'),
            ),
            (
                "npu-preserves-existing-extern-entry",
                "npu_demo",
                'extern "C" int kg_execute_entry(const void*, unsigned long long) { return 0; }\nint add(){ return 0; }',
                "add",
                False,
                ('#include "include/npu_demo/npu_demo.h"',),
                ('#include "include/cpu/Memory.h"', '#include "include/cpu/Nn.h"'),
            ),
        ],
        5,
    )
)

_COMPILE_FAILURE_CASES = tuple(
    random.Random(20260505).sample(
        [
            (
                "mixed-include-family",
                ExecutionEngine(target="cpu"),
                '#include "include/cpu/Memory.h"\n#include "include/npu_demo/npu_demo.h"\nint add(){ return 0; }',
                "add",
                "kg_execute_entry",
                "target_header_mismatch",
            ),
            (
                "npu-source-with-cpu-include",
                ExecutionEngine(target="npu_demo"),
                '#include "include/cpu/Memory.h"\nint add(){ return 0; }',
                "add",
                "kg_execute_entry",
                "target_header_mismatch",
            ),
            (
                "cpu-source-with-npu-include",
                ExecutionEngine(target="cpu"),
                '#include "include/npu_demo/npu_demo.h"\nint add(){ return 0; }',
                "add",
                "kg_execute_entry",
                "target_header_mismatch",
            ),
            (
                "empty-compiler",
                ExecutionEngine(target="cpu", compiler=" "),
                "int add(){ return 0; }",
                "add",
                "kg_execute_entry",
                "compile_failed",
            ),
            (
                "compile-request-empty-entry",
                ExecutionEngine(target="cpu"),
                "int add(){ return 0; }",
                "add",
                " ",
                "symbol_resolve_failed",
            ),
            (
                "npu-namespaced-function-without-namespace-definition",
                ExecutionEngine(target="npu_demo"),
                "int add(){ return 0; }",
                "npu_demo::add",
                "kg_execute_entry",
                "compile_failed",
            ),
        ],
        6,
    )
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


def test_execute_engine_compile_unit_binds_npu_demo_s_int_arg() -> None:
    """EE-S2-C-001A: npu_demo 生成源码中的 S_INT 参数应作为 int runtime arg 绑定。"""

    source = """
#include "include/npu_demo/npu_demo.h"
using namespace npu_demo;

void scalar_kernel(S_INT tile_n) {
    (void)tile_n;
}
"""
    engine = ExecutionEngine(target="npu_demo")
    kernel = engine.compile(source=source, function="scalar_kernel")
    try:
        unit = (Path(kernel.soname_path).parent / "kernel.cpp").read_text(encoding="utf-8")
        assert "S_INT arg0 = static_cast<S_INT>(ordered_args[0].int_value);" in unit
        assert "scalar_kernel(arg0);" in unit
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


# EE-TRANCE-001
# 功能说明: 覆盖 `trance_enabled=True` 时 compile 公开入口追加 runtime trance 编译宏。
# 使用示例: pytest -q test/execute_engine/test_compile.py -k "EE-TRANCE-001"
# 测试目的: 验证 `ExecutionEngine.compile(...)` 从 core config 注入 TRANCE、kernel name 与 trace 文件路径宏。
# 对应功能实现文件路径: kernel_gen/execute_engine/compiler.py
# 对应 spec 文件路径: spec/execute_engine/execute_engine_target.md
# 对应测试文件路径: test/execute_engine/test_compile.py
def test_execute_engine_compile_injects_trance_macros_from_core_config(tmp_path: Path) -> None:
    reset_config()
    set_trance_enabled(True)
    set_dump_dir(tmp_path)
    engine = ExecutionEngine(target="cpu")
    kernel = engine.compile(source="int main(){}", function="npu_demo::add_kernel")
    try:
        command = kernel.compile_stdout.replace("dry-run: ", "").split()
        trace_path = tmp_path / "add_kernel_trace.txt"
        assert "-DTRANCE" in command
        assert '-DKG_TRANCE_KERNEL_NAME="add_kernel"' in command
        assert f'-DKG_TRANCE_FILE_PATH="{trace_path}"' in command
    finally:
        kernel.close()
        reset_config()


# EE-TRANCE-002
# 功能说明: 覆盖 runtime trance 字符串宏在真实 npu_demo 编译执行路径可用。
# 使用示例: pytest -q test/execute_engine/test_compile.py -k "EE-TRANCE-002"
# 测试目的: 验证 g++ 直收 `KG_TRANCE_*` 字符串宏后可打开 trace 文件并写入 entry 日志。
# 对应功能实现文件路径: kernel_gen/execute_engine/compiler.py
# 对应 spec 文件路径: spec/execute_engine/execute_engine_target.md
# 对应测试文件路径: test/execute_engine/test_compile.py
def test_execute_engine_compile_trance_file_sink_runs_on_npu_demo(tmp_path: Path) -> None:
    reset_config()
    set_trance_enabled(True)
    set_dump_dir(tmp_path)
    source = """
void no_arg_kernel() {
}
"""
    kernel = ExecutionEngine(target="npu_demo").compile(source=source, function="no_arg_kernel")
    try:
        result = kernel.execute(args=())
        trace_text = (tmp_path / "no_arg_kernel_trace.txt").read_text(encoding="utf-8")
        assert result.ok is True
        assert "in func: no_arg_kernel template=<none>" in trace_text
        assert "args =" in trace_text
    finally:
        kernel.close()
        reset_config()


# EE-TGT-001/002/004/005
# 功能说明: 覆盖 target include、entry shim 注入/省略与 CPU/npu target 矩阵。
# 使用示例: pytest -q test/execute_engine/test_compile.py -k "target_include_and_entry_shim_matrix"
# 测试目的: 验证公开 ExecutionEngine.compile 入口对 target/header/shim 合同的组合行为。
# 对应功能实现文件路径: kernel_gen/execute_engine/compiler.py
# 对应 spec 文件路径: spec/execute_engine/execute_engine_target.md
# 对应测试文件路径: test/execute_engine/test_compile.py
@pytest.mark.parametrize(
    ("case_id", "target", "source", "function", "expects_shim", "required_lines", "forbidden_lines"),
    _COMPILE_TARGET_SOURCE_CASES,
)
def test_execute_engine_compile_target_include_and_entry_shim_matrix(
    case_id: str,
    target: str,
    source: str,
    function: str,
    expects_shim: bool,
    required_lines: tuple[str, ...],
    forbidden_lines: tuple[str, ...],
) -> None:
    engine = ExecutionEngine(target=target)
    kernel = engine.compile(source=source, function=function)
    try:
        unit = (Path(kernel.soname_path).parent / "kernel.cpp").read_text(encoding="utf-8")
        assert kernel.target == target
        assert case_id
        for line in required_lines:
            assert line in unit
        for line in forbidden_lines:
            assert line not in unit
        assert ("runtime entry shim for" in unit) is expects_shim
        assert unit.count('#include "include/cpu/Memory.h"') <= 1
        assert unit.count('#include "include/cpu/Nn.h"') <= 1
        assert unit.count('#include "include/npu_demo/npu_demo.h"') <= 1
    finally:
        kernel.close()


def test_execute_engine_compile_rejects_template_memory_without_concrete_dtype() -> None:
    """验证手写 templated Memory 函数缺实例信息时稳定失败。"""

    source = "template <typename T1>\nvoid templated_kernel(Memory<GM, T1>& arg0) {}\n"
    with pytest.raises(KernelCodeError) as exc:
        ExecutionEngine(target="npu_demo").compile(source=source, function="templated_kernel")

    assert exc.value.failure_phrase == "template_instance_required"


def test_execute_engine_compile_template_shim_uses_nearest_wrapper_template_header() -> None:
    """验证前置 templated helper 声明不会遮蔽目标 wrapper 的模板参数。"""

    source = """
template <typename T1>
static void templated_kernel_device(Memory<GM, T1>& arg0);

static void template_instance_seed(Memory<GM, int32_t>& value) {
    (void)value;
}

template <typename T1>
void templated_kernel(Memory<MemorySpace::GM, T1>& arg0) {
    templated_kernel_device<T1>(arg0);
}

template <typename T1>
static void templated_kernel_device(Memory<GM, T1>& arg0) {
    (void)arg0;
}
"""
    kernel = ExecutionEngine(target="npu_demo").compile(source=source, function="templated_kernel")
    try:
        unit = (Path(kernel.soname_path).parent / "kernel.cpp").read_text(encoding="utf-8")
        assert "Memory<MemorySpace::GM, int32_t> arg0(" in unit
        assert "templated_kernel<int32_t>(arg0);" in unit
        assert "Memory<MemorySpace::GM, T1> arg0(" not in unit
    finally:
        kernel.close()


# EE-TGT-006/007
# 功能说明: 覆盖 compile 公开失败短语矩阵。
# 使用示例: pytest -q test/execute_engine/test_compile.py -k "failure_phrase_matrix"
# 测试目的: 验证 include family、compiler、entry_point 与真实 npu 编译失败均通过公开错误语义暴露。
# 对应功能实现文件路径: kernel_gen/execute_engine/compiler.py
# 对应 spec 文件路径: spec/execute_engine/execute_engine_target.md
# 对应测试文件路径: test/execute_engine/test_compile.py
@pytest.mark.parametrize(
    ("case_id", "engine", "source", "function", "entry_point", "failure_phrase"),
    _COMPILE_FAILURE_CASES,
)
def test_execute_engine_compile_failure_phrase_matrix(
    case_id: str,
    engine: ExecutionEngine,
    source: str,
    function: str,
    entry_point: str,
    failure_phrase: str,
) -> None:
    with pytest.raises(KernelCodeError) as exc:
        engine.compile(source=source, function=function, entry_point=entry_point)

    assert case_id
    assert exc.value.failure_phrase == failure_phrase


# EE-TGT-008
# 功能说明: 覆盖 entry shim 对 memory/int/float/KernelContext 形参的公开源码拼装。
# 使用示例: pytest -q test/execute_engine/test_compile.py -k "entry_shim_public_param_matrix"
# 测试目的: 验证公开 compile 入口按目标函数形参顺序生成 runtime entry shim。
# 对应功能实现文件路径: kernel_gen/execute_engine/compiler.py
# 对应 spec 文件路径: spec/execute_engine/execute_engine_target.md
# 对应测试文件路径: test/execute_engine/test_compile.py
def test_execute_engine_compile_entry_shim_public_param_matrix() -> None:
    source = (
        "void add(npu_demo::KernelContext& ctx, Memory<GM, float>& out, "
        "const Memory<GM, int32_t>& lhs, long count, double alpha) {}\n"
    )
    kernel = ExecutionEngine(target="cpu").compile(source=source, function="add")
    try:
        unit = (Path(kernel.soname_path).parent / "kernel.cpp").read_text(encoding="utf-8")

        assert "npu_demo::KernelContext ctx;" in unit
        assert "if (arg_count != 4ULL)" in unit
        assert "Memory<GM, float> arg0(" in unit
        assert "Memory<GM, int32_t> arg1(" in unit
        assert "long arg2 = static_cast<long>(ordered_args[2].int_value);" in unit
        assert "double arg3 = static_cast<double>(ordered_args[3].float_value);" in unit
        assert "add(ctx, arg0, arg1, arg2, arg3);" in unit
    finally:
        kernel.close()


# EE-TGT-009
# 功能说明: 覆盖不能解析的目标形参回退到占位 entry shim 的公开行为。
# 使用示例: pytest -q test/execute_engine/test_compile.py -k "entry_shim_placeholder"
# 测试目的: 验证公开 compile 入口遇到未支持形参时仍生成稳定 C ABI 占位入口。
# 对应功能实现文件路径: kernel_gen/execute_engine/compiler.py
# 对应 spec 文件路径: spec/execute_engine/execute_engine_target.md
# 对应测试文件路径: test/execute_engine/test_compile.py
def test_execute_engine_compile_entry_shim_placeholder_for_unsupported_params() -> None:
    kernel = ExecutionEngine(target="cpu").compile(source="void add(Custom value) {}\n", function="add")
    try:
        unit = (Path(kernel.soname_path).parent / "kernel.cpp").read_text(encoding="utf-8")

        assert "// entry shim placeholder for add as kg_execute_entry" in unit
        assert "struct _ArgSlot;" in unit
        assert "(void)arg_count;" in unit
        assert "return 0;" in unit
    finally:
        kernel.close()
