"""execute_engine builtin target support tests.


功能说明:
- 验证 `ExecutionEngine.compile(...)` 公开入口下的 target include、entry shim、template shim 与 runtime trance 编译宏。
- 测试只调用执行引擎公开 API，不直连 `target_support.py` 的非公开 helper。

使用示例:
- pytest -q test/execute_engine/test_target_support.py

关联文件:
- 功能实现: kernel_gen/execute_engine/compiler.py
- 功能实现: kernel_gen/execute_engine/target_support.py
- Spec 文档: spec/execute_engine/execute_engine_target.md
- 测试文件: test/execute_engine/test_target_support.py
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
from kernel_gen.execute_engine import ExecutionEngine


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


# EE-S2-C-001
# 功能说明: 覆盖编译单元拼装的 include 与 entry shim 注入规则。
# 使用示例: pytest -q test/execute_engine/test_target_support.py -k "S2-C-001"
# 测试目的: 验证编译单元拼装包含 target include 与 entry shim。
# 对应功能实现文件路径: kernel_gen/execute_engine/target_support.py
# 对应 spec 文件路径: spec/execute_engine/execute_engine_target.md
# 对应测试文件路径: test/execute_engine/test_target_support.py
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


# EE-TRANCE-001
# 功能说明: 覆盖 `trance_enabled=True` 时 compile 公开入口追加 runtime trance 编译宏。
# 使用示例: pytest -q test/execute_engine/test_target_support.py -k "EE-TRANCE-001"
# 测试目的: 验证 `ExecutionEngine.compile(...)` 从 core config 注入 TRANCE、kernel name 与 block trace 目录宏。
# 对应功能实现文件路径: kernel_gen/execute_engine/target_support.py
# 对应 spec 文件路径: spec/execute_engine/execute_engine_target.md
# 对应测试文件路径: test/execute_engine/test_target_support.py
def test_execute_engine_compile_injects_trance_macros_from_core_config(tmp_path: Path) -> None:
    reset_config()
    set_trance_enabled(True)
    set_dump_dir(tmp_path)
    engine = ExecutionEngine(target="cpu")
    kernel = engine.compile(source="int main(){}", function="npu_demo::add_kernel")
    try:
        command = kernel.compile_stdout.replace("dry-run: ", "").split()
        trace_dir = tmp_path / "add_kernel" / "trance"
        assert "-DTRANCE" in command
        assert '-DKG_TRANCE_KERNEL_NAME="add_kernel"' in command
        assert f'-DKG_TRANCE_DIR_PATH="{trace_dir}"' in command
        assert '-DKG_TRANCE_FILE_PATH=""' in command
        assert not any("add_kernel_trace.txt" in item for item in command)
    finally:
        kernel.close()
        reset_config()


# EE-TRANCE-002
# 功能说明: 覆盖 runtime trance block 目录宏在真实 npu_demo 编译执行路径可用。
# 使用示例: pytest -q test/execute_engine/test_target_support.py -k "EE-TRANCE-002"
# 测试目的: 验证 g++ 直收 `KG_TRANCE_*` 字符串宏后可打开 block trace 文件并写入 launch 日志。
# 对应功能实现文件路径: kernel_gen/execute_engine/target_support.py
# 对应 spec 文件路径: spec/execute_engine/execute_engine_target.md
# 对应测试文件路径: test/execute_engine/test_target_support.py
def test_execute_engine_compile_trance_block_sink_runs_on_npu_demo(tmp_path: Path) -> None:
    reset_config()
    set_trance_enabled(True)
    set_dump_dir(tmp_path)
    source = """
static void kernel_body() {
}

void run_kernel() {
    npu_demo::launch<2, 1, 1, 0>(kernel_body);
}
"""
    kernel = ExecutionEngine(target="npu_demo").compile(source=source, function="run_kernel")
    try:
        result = kernel.execute(args=())
        trace_dir = tmp_path / "run_kernel" / "trance"
        block0_text = (trace_dir / "block_0000.log").read_text(encoding="utf-8")
        block1_text = (trace_dir / "block_0001.log").read_text(encoding="utf-8")
        assert result.ok is True
        assert "block_id = 0" in block0_text
        assert "block_id = 1" in block1_text
        assert "in func: npu_demo::launch template=<block=2, thread=1, subthread=1, shared_memory_size=0>" in block0_text
        assert "in func: npu_demo::launch template=<block=2, thread=1, subthread=1, shared_memory_size=0>" in block1_text
        assert not (tmp_path / "run_kernel_trace.txt").exists()
        assert not (tmp_path / "run_kernel" / "run_kernel_trace.txt").exists()
    finally:
        kernel.close()
        reset_config()


# EE-TGT-001/002/004/005
# 功能说明: 覆盖 target include、entry shim 注入/省略与 CPU/npu target 矩阵。
# 使用示例: pytest -q test/execute_engine/test_target_support.py -k "target_include_and_entry_shim_matrix"
# 测试目的: 验证公开 ExecutionEngine.compile 入口对 target/header/shim 合同的组合行为。
# 对应功能实现文件路径: kernel_gen/execute_engine/target_support.py
# 对应 spec 文件路径: spec/execute_engine/execute_engine_target.md
# 对应测试文件路径: test/execute_engine/test_target_support.py
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


def test_execute_engine_compile_template_shim_uses_generated_dtype_seed_aliases() -> None:
    """验证 generated source 的 dtype seed alias 能精确绑定模板实参。"""

    source = """
using __kernel_gen_template_instance_seed_templated_kernel__T1 = Memory<MemorySpace::GM, float>;
using __kernel_gen_template_instance_seed_templated_kernel__T2 = Memory<MemorySpace::GM, int32_t>;

template <typename T1, typename T2>
void templated_kernel(Memory<MemorySpace::GM, T1>& out, Memory<MemorySpace::GM, T2>& lhs) {
    (void)out;
    (void)lhs;
}
"""
    kernel = ExecutionEngine(target="npu_demo").compile(source=source, function="templated_kernel")
    try:
        unit = (Path(kernel.soname_path).parent / "kernel.cpp").read_text(encoding="utf-8")
        assert "Memory<MemorySpace::GM, float> arg0(" in unit
        assert "Memory<MemorySpace::GM, int32_t> arg1(" in unit
        assert "templated_kernel<float, int32_t>(arg0, arg1);" in unit
    finally:
        kernel.close()


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


# EE-TGT-008
# 功能说明: 覆盖 entry shim 对 memory/int/float/KernelContext 形参的公开源码拼装。
# 使用示例: pytest -q test/execute_engine/test_target_support.py -k "entry_shim_public_param_matrix"
# 测试目的: 验证公开 compile 入口按目标函数形参顺序生成 runtime entry shim。
# 对应功能实现文件路径: kernel_gen/execute_engine/target_support.py
# 对应 spec 文件路径: spec/execute_engine/execute_engine_target.md
# 对应测试文件路径: test/execute_engine/test_target_support.py
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
# 使用示例: pytest -q test/execute_engine/test_target_support.py -k "entry_shim_placeholder"
# 测试目的: 验证公开 compile 入口遇到未支持形参时仍生成稳定 C ABI 占位入口。
# 对应功能实现文件路径: kernel_gen/execute_engine/target_support.py
# 对应 spec 文件路径: spec/execute_engine/execute_engine_target.md
# 对应测试文件路径: test/execute_engine/test_target_support.py
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
