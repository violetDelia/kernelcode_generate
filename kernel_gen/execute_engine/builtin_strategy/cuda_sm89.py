"""CUDA SM89 builtin compile strategy implementation.

功能说明:
- 承接 `target="cuda_sm89"` 的 SourceBundle 写盘、`nvcc` 命令生成和 `.so` 编译路径。
- SourceBundle aggregate 与 `.cu/.cuh` 文本 artifact 写出统一委托 `kernel_gen.core.tools.dump_dir.DumpDirWriter`。
- 只消费 generated source 中的 `kg_execute_entry(slots, count)` C ABI；具体业务 kernel 必须由 emit 生成。

API 列表:
- `build_cuda_sm89_compile_artifacts(request: "CompileRequest", compiler: str, compiler_flags: tuple[str, ...], link_flags: tuple[str, ...]) -> BuiltinCompileArtifacts`

使用示例:
- artifacts = build_cuda_sm89_compile_artifacts(request, "nvcc", ("-std=c++17",), ())

关联文件:
- spec: spec/execute_engine/strategy.md
- spec: spec/execute_engine/execute_engine_target.md
- test: test/execute_engine/test_cuda_sm89_strategy.py
- 功能实现: kernel_gen/execute_engine/builtin_strategy/__init__.py
"""

from __future__ import annotations

from collections.abc import Callable
from functools import partial
from pathlib import Path
import tempfile

from kernel_gen.core.tools.dump_dir import DumpDirWriter
from kernel_gen.execute_engine.builtin_strategy.common import (
    BUNDLE_MARKER_PREFIX,
    BuiltinCompileArtifacts,
    BuiltinStrategySupport,
    REPO_ROOT,
)


def build_cuda_sm89_compile_artifacts(
    request: "CompileRequest",
    compiler: str,
    compiler_flags: tuple[str, ...],
    link_flags: tuple[str, ...],
) -> BuiltinCompileArtifacts:
    """生成 CUDA SM89 target 编译产物。

    功能说明:
    - 解析公开 SourceBundle aggregate，写出真实 `.cu/.cuh` artifact。
    - 使用 `nvcc -arch=sm_89 -shared -Xcompiler -fPIC` 编译为 `.so`，并返回 slot C ABI 编译结果。

    使用示例:
    - artifacts = build_cuda_sm89_compile_artifacts(request, "nvcc", ("-std=c++17",), ())
    """

    cleanup: Callable[[], None] | None = None
    try:
        work_dir = Path(tempfile.mkdtemp(prefix="kg_execute_engine_cuda_sm89_"))
        cleanup = partial(BuiltinStrategySupport.remove_workdir, work_dir)
        work_writer = DumpDirWriter(work_dir)
        source_writer = work_writer.child("source")
        aggregate_path = source_writer.write("source.cpp", request.source)

        artifacts: dict[str, list[str]] = {}
        lines = request.source.splitlines()
        if lines and lines[0].startswith(BUNDLE_MARKER_PREFIX):
            current_path: str | None = None
            seen_paths: set[str] = set()
            for line in lines:
                if line.startswith(BUNDLE_MARKER_PREFIX):
                    path_text = line[len(BUNDLE_MARKER_PREFIX):]
                    if (
                        not path_text
                        or path_text.startswith("/")
                        or path_text in {".", ".."}
                        or "\\" in path_text
                        or "\x00" in path_text
                        or path_text in seen_paths
                        or any(part in {"", ".", ".."} for part in path_text.split("/"))
                    ):
                        raise BuiltinStrategySupport.builtin_compile_error("source_empty_or_invalid", "source_bundle_malformed")
                    seen_paths.add(path_text)
                    artifacts[path_text] = []
                    current_path = path_text
                    continue
                if current_path is None:
                    raise BuiltinStrategySupport.builtin_compile_error("source_empty_or_invalid", "source_bundle_malformed")
                artifacts[current_path].append(line)
        else:
            compile_unit = BuiltinStrategySupport.compose_compile_unit(
                source=request.source,
                include_lines_for_target=BuiltinStrategySupport.include_lines_for_target("cuda_sm89"),
                entry_shim_source="",
            )
            artifacts["kernel.cu"] = compile_unit.splitlines()

        written_paths: dict[str, Path] = {}
        for artifact_path, content_lines in artifacts.items():
            artifact_text = "\n".join(content_lines)
            try:
                output_path = source_writer.write(artifact_path, artifact_text)
            except ValueError as exc:
                raise BuiltinStrategySupport.builtin_compile_error("source_empty_or_invalid", "source_bundle_path_escape") from exc
            written_paths[artifact_path] = output_path

        main_path = written_paths.get("kernel.cu")
        if main_path is None:
            cuda_sources = [path for artifact_path, path in written_paths.items() if artifact_path.endswith(".cu")]
            if not cuda_sources:
                raise BuiltinStrategySupport.builtin_compile_error("source_empty_or_invalid", "source_bundle_missing_cuda_source")
            main_path = cuda_sources[0]
        soname_path = work_writer.root / "libkernel.so"
        cuda_flags = list(compiler_flags)
        if not any(flag.startswith("-arch=") for flag in cuda_flags) and not any(flag.startswith("-gencode") for flag in cuda_flags):
            cuda_flags.append("-arch=sm_89")
        if "-shared" not in cuda_flags:
            cuda_flags.append("-shared")
        if "-fPIC" not in cuda_flags and "-Xcompiler" not in cuda_flags:
            cuda_flags.extend(["-Xcompiler", "-fPIC"])
        command = (
            compiler,
            *tuple(cuda_flags),
            f"-I{REPO_ROOT}",
            f"-I{source_writer.root}",
            str(main_path),
            "-o",
            str(soname_path),
            *tuple(link_flags),
        )
        try:
            result = BuiltinStrategySupport.run_compiler_command(command)
        except FileNotFoundError as exc:
            raise BuiltinStrategySupport.builtin_compile_error("compile_failed", "nvcc failed: compiler not found") from exc
        if result.returncode != 0:
            raise BuiltinStrategySupport.builtin_compile_error("compile_failed", f"nvcc failed: compiler returned non-zero ({result.returncode})")
        if not soname_path.exists():
            raise BuiltinStrategySupport.builtin_compile_error("compile_failed", "compile output is missing")
        return BuiltinCompileArtifacts(
            soname_path=str(soname_path),
            source_path=str(aggregate_path),
            command=command,
            stdout=result.stdout or f"cuda-sm89 compile: {' '.join(command)}",
            stderr=result.stderr,
            return_code=result.returncode,
            allow_absent_memory_arg_specs=BuiltinStrategySupport.extract_allow_absent_memory_arg_specs(request.source),
            cleanup=cleanup,
        )
    except Exception:
        if cleanup is not None:
            cleanup()
        raise
