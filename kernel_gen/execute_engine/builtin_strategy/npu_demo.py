"""npu_demo builtin compile strategy implementation.

功能说明:
- 承接 `target="npu_demo"` 的 include 注入、entry shim 生成和真实 `g++` shared-object 编译。
- 保持 runtime trance、allow-absent memory metadata 与旧公开错误语义不变。

API 列表:
- `build_npu_demo_compile_artifacts(request: "CompileRequest", compiler: str, compiler_flags: tuple[str, ...], link_flags: tuple[str, ...]) -> BuiltinCompileArtifacts`

使用示例:
- artifacts = build_npu_demo_compile_artifacts(request, "g++", ("-std=c++17",), ())

关联文件:
- spec: spec/execute_engine/strategy.md
- spec: spec/execute_engine/execute_engine_target.md
- test: test/execute_engine/test_builtin_strategy.py
- 功能实现: kernel_gen/execute_engine/builtin_strategy/__init__.py
"""

from __future__ import annotations

from pathlib import Path

from kernel_gen.execute_engine.builtin_strategy.common import (
    BuiltinCompileArtifacts,
    BuiltinStrategySupport,
    REPO_ROOT,
)


def build_npu_demo_compile_artifacts(
    request: "CompileRequest",
    compiler: str,
    compiler_flags: tuple[str, ...],
    link_flags: tuple[str, ...],
) -> BuiltinCompileArtifacts:
    """生成 npu_demo target 编译产物。

    功能说明:
    - 为 npu_demo source 注入 include 与必要 entry shim。
    - 使用真实编译器生成 `.so`，并携带 allow-absent memory 参数 metadata。

    使用示例:
    - artifacts = build_npu_demo_compile_artifacts(request, "g++", ("-std=c++17",), ())
    """

    target_headers = BuiltinStrategySupport.include_lines_for_target("npu_demo")
    if not target_headers:
        raise BuiltinStrategySupport.builtin_compile_error("target_header_mismatch", "unsupported target: npu_demo")
    shim_source = ""
    if BuiltinStrategySupport.requires_entry_shim(request.source, request.entry_point):
        shim_source = BuiltinStrategySupport.compose_entry_shim_source(
            function=request.function,
            entry_point=request.entry_point,
            source=request.source,
        )
    compile_unit = BuiltinStrategySupport.compose_compile_unit(
        source=request.source,
        include_lines_for_target=target_headers,
        entry_shim_source=shim_source,
    )
    artifacts = BuiltinStrategySupport.compile_unit_source(
        source=compile_unit,
        compiler=compiler,
        compiler_flags=compiler_flags,
        link_flags=link_flags,
        include_dirs=(str(REPO_ROOT),),
        dry_run=False,
    )
    if artifacts.return_code != 0:
        if artifacts.cleanup is not None:
            artifacts.cleanup()
        raise BuiltinStrategySupport.builtin_compile_error("compile_failed", f"compiler returned non-zero ({artifacts.return_code})")
    if not Path(artifacts.soname_path).exists():
        if artifacts.cleanup is not None:
            artifacts.cleanup()
        raise BuiltinStrategySupport.builtin_compile_error("compile_failed", "compile output is missing")
    return BuiltinCompileArtifacts(
        soname_path=artifacts.soname_path,
        source_path=artifacts.source_path,
        command=artifacts.command,
        stdout=artifacts.stdout,
        stderr=artifacts.stderr,
        return_code=artifacts.return_code,
        allow_absent_memory_arg_specs=BuiltinStrategySupport.extract_allow_absent_memory_arg_specs(request.source),
        cleanup=artifacts.cleanup,
    )
