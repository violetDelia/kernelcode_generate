"""execute_engine public target API coverage tests.

创建者: 金铲铲大作战
最后一次更改: 朽木露琪亚

功能说明:
- 覆盖 execute_engine compile target 相关的公开 API 边界。
- 当前文件只验证 `target_registry / compiler / entry_shim_builder` 对外公开入口，不再直连私有 helper。

使用示例:
- pytest -q test/execute_engine/test_execute_engine_private_helpers.py

关联文件:
- 功能实现: kernel_gen/execute_engine/compiler.py
- 功能实现: kernel_gen/execute_engine/entry_shim_builder.py
- 功能实现: kernel_gen/execute_engine/target_registry.py
- Spec 文档: spec/execute_engine/execute_engine_target.md
- 测试文件: test/execute_engine/test_execute_engine_private_helpers.py
"""

from __future__ import annotations

from pathlib import Path

import pytest

from kernel_gen.execute_engine.compiler import (
    CompileArtifacts,
    build_compile_command,
    build_compile_unit,
    compile_source,
    default_compiler,
)
from kernel_gen.execute_engine.entry_shim_builder import (
    build_entry_shim_source,
    needs_entry_shim,
)
from kernel_gen.execute_engine.target_registry import target_includes


def test_execute_engine_public_target_api_target_includes_contract() -> None:
    """验证公开 target include 映射合同。

    创建者: 朽木露琪亚
    最后一次更改: 朽木露琪亚

    功能说明:
    - 校验 `target_includes` 只暴露当前公开 target 的 include family。
    - 不通过内部 helper 推断 include family。

    使用示例:
    - pytest -q test/execute_engine/test_execute_engine_private_helpers.py -k target_includes
    """

    assert target_includes("cpu") == (
        '#include "include/cpu/Memory.h"',
        '#include "include/cpu/Nn.h"',
    )
    assert target_includes("npu_demo") == ('#include "include/npu_demo/npu_demo.h"',)
    assert target_includes("unknown") == ()


def test_execute_engine_public_target_api_default_compiler_and_command_shape() -> None:
    """验证默认编译器与公开编译命令构造合同。

    创建者: 朽木露琪亚
    最后一次更改: 朽木露琪亚

    功能说明:
    - 通过 `default_compiler` 与 `build_compile_command` 校验公开编译入口的最小命令骨架。

    使用示例:
    - pytest -q test/execute_engine/test_execute_engine_private_helpers.py -k command_shape
    """

    assert default_compiler() == "g++"
    command = build_compile_command(
        compiler="clang++",
        source_path="kernel.cpp",
        output_path="libkernel.so",
        compiler_flags=("-std=c++17", "-O2"),
        link_flags=("-lm",),
        include_dirs=(".", "include"),
    )
    assert command[0] == "clang++"
    assert command[1:3] == ("-shared", "-fPIC")
    assert "-std=c++17" in command
    assert "-O2" in command
    assert "-I." in command
    assert "-Iinclude" in command
    assert "kernel.cpp" in command
    assert command[-3:] == ("-o", "libkernel.so", "-lm")


def test_execute_engine_public_target_api_compile_unit_injects_missing_includes_only() -> None:
    """验证公开编译单元拼装合同。

    创建者: 朽木露琪亚
    最后一次更改: 朽木露琪亚

    功能说明:
    - 校验 `build_compile_unit` 只补缺失 include，并把 shim 追加到源码尾部。

    使用示例:
    - pytest -q test/execute_engine/test_execute_engine_private_helpers.py -k compile_unit
    """

    unit = build_compile_unit(
        source='#include "include/cpu/Memory.h"\nint main() {\n  return 0;\n}\n',
        target_includes=(
            '#include "include/cpu/Memory.h"',
            '#include "include/cpu/Nn.h"',
        ),
        entry_shim_source="// shim\n",
    )
    assert unit.count('#include "include/cpu/Memory.h"') == 1
    assert '#include "include/cpu/Nn.h"' in unit
    assert unit.rstrip().endswith("// shim")


def test_execute_engine_public_target_api_entry_shim_contracts() -> None:
    """验证公开 entry shim 构造合同。

    创建者: 朽木露琪亚
    最后一次更改: 朽木露琪亚

    功能说明:
    - 只通过 `needs_entry_shim` 与 `build_entry_shim_source` 验证公开 shim 入口行为。

    使用示例:
    - pytest -q test/execute_engine/test_execute_engine_private_helpers.py -k entry_shim
    """

    source = """
    void add_kernel(
        npu_demo::KernelContext& ctx,
        Memory<GM, float>& out,
        const Memory<GM, float>& lhs,
        const Memory<GM, float>& rhs,
        int axis,
        double scale) {
      (void)ctx;
    }
    """
    assert needs_entry_shim(None, "kg_execute_entry") is True
    assert (
        needs_entry_shim(
            'extern "C" int kg_execute_entry(const void*, unsigned long long) { return 0; }',
            "kg_execute_entry",
        )
        is False
    )
    assert needs_entry_shim("int add(){}", "kg_execute_entry") is True

    runtime_source = build_entry_shim_source(
        function="add_kernel",
        entry_point="kg_execute_entry",
        source=source,
    )
    assert "runtime entry shim for add_kernel" in runtime_source
    assert "npu_demo::KernelContext ctx;" in runtime_source
    assert "return 0;" in runtime_source

    placeholder = build_entry_shim_source(
        function="add_kernel",
        entry_point="kg_execute_entry",
        source="void add_kernel(std::string name) {}",
    )
    assert "entry shim placeholder" in placeholder


def test_execute_engine_public_target_api_compile_source_dry_run_paths(
    tmp_path: Path,
) -> None:
    """验证公开 compile_source dry-run 合同。

    创建者: 朽木露琪亚
    最后一次更改: 朽木露琪亚

    功能说明:
    - 校验 `compile_source` 在 dry-run 与显式 `work_dir` 下的公开输出形态。

    使用示例:
    - pytest -q test/execute_engine/test_execute_engine_private_helpers.py -k compile_source
    """

    artifacts = compile_source(
        source="int main(){}",
        compiler="g++",
        compiler_flags=("-std=c++17",),
        link_flags=(),
        include_dirs=(str(tmp_path),),
        dry_run=True,
    )
    assert isinstance(artifacts, CompileArtifacts)
    assert artifacts.return_code == 0
    assert artifacts.stdout.startswith("dry-run: ")
    assert Path(artifacts.source_path).exists()
    assert Path(artifacts.soname_path).exists()

    explicit_dir = tmp_path / "compile-work"
    artifacts = compile_source(
        source="int main(){}",
        compiler="g++",
        compiler_flags=("-std=c++17",),
        link_flags=(),
        include_dirs=(str(tmp_path),),
        work_dir=explicit_dir,
        dry_run=True,
    )
    assert Path(artifacts.source_path).parent == explicit_dir
    assert Path(artifacts.soname_path).parent == explicit_dir
