"""Compiler hook for ExecutionEngine (P0/S2).

创建者: 朽木露琪亚
最后一次更改: 小李飞刀

功能说明:
- 提供编译命令生成与编译单元拼接的最小实现，使 S2 阶段可稳定覆盖“编译路径”合同。
- 默认以 dry-run 形式生成编译命令与产物占位文件，不强制依赖真实编译器环境。

使用示例:
- from kernel_gen.execute_engine.compiler import default_compiler, build_compile_unit
- assert default_compiler() == "g++"
- unit = build_compile_unit(source="int main(){}", target_includes=(), entry_shim_source="")

关联文件:
- spec: spec/execute_engine/execute_engine_target.md
- test: test/execute_engine/test_execute_engine_compile.py
- 功能实现: kernel_gen/execute_engine/compiler.py
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
import shutil
import subprocess
import tempfile
from typing import Callable, Iterable

from kernel_gen.common.text import join_text_sections

_COMPILER_ICE_MARKERS = (
    "internal compiler error",
    "Please submit a full bug report",
)


def _looks_like_internal_compiler_error(stderr: str) -> bool:
    """判断编译 stderr 是否命中编译器内部错误特征。

    创建者: 小李飞刀
    最后一次更改: 小李飞刀

    功能说明:
    - 统一识别 GCC/Clang 常见的 internal compiler error 文本。
    - 供真实编译路径决定是否追加一次同命令重试，减少编译器偶发异常对回归结果的干扰。

    使用示例:
    - assert _looks_like_internal_compiler_error("internal compiler error: ...") is True

    关联文件:
    - spec: spec/execute_engine/execute_engine_target.md
    - test: test/execute_engine/test_execute_engine_private_helpers.py
    - 功能实现: kernel_gen/execute_engine/compiler.py
    """

    if not isinstance(stderr, str):
        return False
    return any(marker in stderr for marker in _COMPILER_ICE_MARKERS)


def _run_compiler_command(command: Iterable[str]) -> subprocess.CompletedProcess[str]:
    """运行编译命令，并在编译器内部异常时追加一次重试。

    创建者: 小李飞刀
    最后一次更改: 小李飞刀

    功能说明:
    - 统一真实编译路径的命令执行与 stderr 判定逻辑。
    - 当 stderr 命中编译器内部异常文本时，仅对同一命令追加一次重试。
    - 让执行引擎与本地编译回归测试复用同一控制流，避免两处维护不同分支。

    使用示例:
    - result = _run_compiler_command(["g++", "-std=c++17", "demo.cpp", "-o", "demo"])

    关联文件:
    - spec: spec/execute_engine/execute_engine_target.md
    - test: test/execute_engine/test_execute_engine_private_helpers.py
    - test: test/dsl/gen_kernel/test_gen_kernel.py
    - 功能实现: kernel_gen/execute_engine/compiler.py
    """

    argv = list(command)
    result = subprocess.run(
        argv,
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0 and _looks_like_internal_compiler_error(result.stderr):
        result = subprocess.run(
            argv,
            capture_output=True,
            text=True,
            check=False,
        )
    return result


def default_compiler() -> str:
    """返回 P0 默认编译器名。

    创建者: 朽木露琪亚
    最后一次更改: 朽木露琪亚

    功能说明:
    - 以固定值返回执行引擎 P0 的默认编译器名，用于生成可复现的编译命令骨架。

    使用示例:
    - assert default_compiler() == "g++"

    关联文件:
    - spec: spec/execute_engine/execute_engine_target.md
    - test: test/execute_engine/test_execute_engine_contract.py
    - 功能实现: kernel_gen/execute_engine/compiler.py
    """

    return "g++"


@dataclass(frozen=True)
class CompileArtifacts:
    """编译产物描述（P0/S2）。

    创建者: jcc你莫辜负
    最后一次更改: jcc你莫辜负

    功能说明:
    - 统一承载编译命令、产物路径与 stdout/stderr，便于测试与记录。
    - 当编译器内部创建临时工作目录时，会附带私有 cleanup 句柄，用于由上层在合适时机释放。

    使用示例:
    - artifacts = CompileArtifacts(
        soname_path="libkernel.so",
        source_path="kernel.cpp",
        command=("g++",),
        stdout="",
        stderr="",
        return_code=0,
      )

    关联文件:
    - spec: spec/execute_engine/execute_engine_target.md
    - test: test/execute_engine/test_execute_engine_compile.py
    - 功能实现: kernel_gen/execute_engine/compiler.py
    """

    soname_path: str
    source_path: str
    command: tuple[str, ...]
    stdout: str
    stderr: str
    return_code: int
    _cleanup: Callable[[], None] | None = field(default=None, repr=False, compare=False)


def build_compile_unit(
    *,
    source: str,
    target_includes: tuple[str, ...],
    entry_shim_source: str,
) -> str:
    """拼接最终编译单元源码。

    创建者: jcc你莫辜负
    最后一次更改: jcc你莫辜负

    功能说明:
    - 以 target include set + 原始 source + entry shim 的顺序拼接编译单元。
    - 若 source 已含部分 target include，则仅补齐缺失项。

    使用示例:
    - unit = build_compile_unit(
        source="int main(){}",
        target_includes=('#include \"include/cpu/Memory.h\"',),
        entry_shim_source="// shim",
      )

    关联文件:
    - spec: spec/execute_engine/execute_engine_target.md
    - test: test/execute_engine/test_execute_engine_compile.py
    - 功能实现: kernel_gen/execute_engine/compiler.py
    """

    missing_includes = tuple(line for line in target_includes if line not in source)
    sections: list[str] = []
    if missing_includes:
        sections.append("\n".join(missing_includes))
    sections.append(source.rstrip())
    if entry_shim_source:
        sections.append(entry_shim_source.rstrip())
    return join_text_sections(*sections)


def build_compile_command(
    *,
    compiler: str,
    source_path: str,
    output_path: str,
    compiler_flags: Iterable[str],
    link_flags: Iterable[str],
    include_dirs: Iterable[str],
) -> tuple[str, ...]:
    """生成编译命令（P0/S2）。

    创建者: jcc你莫辜负
    最后一次更改: jcc你莫辜负

    功能说明:
    - 按固定顺序拼装编译命令：compiler + flags + include dirs + source + -o output + link_flags。
    - 默认生成可共享库产物（-shared -fPIC），便于后续执行阶段载入。

    使用示例:
    - cmd = build_compile_command(
        compiler="g++",
        source_path="kernel.cpp",
        output_path="libkernel.so",
        compiler_flags=("-std=c++17",),
        link_flags=(),
        include_dirs=(".",),
      )

    关联文件:
    - spec: spec/execute_engine/execute_engine_target.md
    - test: test/execute_engine/test_execute_engine_compile.py
    - 功能实现: kernel_gen/execute_engine/compiler.py
    """

    include_args = [f"-I{path}" for path in include_dirs]
    command = (
        compiler,
        "-shared",
        "-fPIC",
        *tuple(compiler_flags),
        *tuple(include_args),
        source_path,
        "-o",
        output_path,
        *tuple(link_flags),
    )
    return tuple(command)


def compile_source(
    *,
    source: str,
    compiler: str,
    compiler_flags: tuple[str, ...],
    link_flags: tuple[str, ...],
    include_dirs: tuple[str, ...],
    work_dir: Path | None = None,
    dry_run: bool = True,
) -> CompileArtifacts:
    """执行或模拟编译流程。

    创建者: jcc你莫辜负
    最后一次更改: 小李飞刀

    功能说明:
    - 将编译单元写入工作目录，生成编译命令并执行或 dry-run。
    - dry_run 模式下仅创建产物占位文件并返回命令，避免依赖真实编译器环境。
    - 若内部自动创建临时工作目录，则通过返回值携带 cleanup 句柄，由上层在 close / 失败分支释放。

    使用示例:
    - artifacts = compile_source(
        source="int main(){}",
        compiler="g++",
        compiler_flags=("-std=c++17",),
        link_flags=(),
        include_dirs=(".",),
        dry_run=True,
      )

    关联文件:
    - spec: spec/execute_engine/execute_engine_target.md
    - test: test/execute_engine/test_execute_engine_compile.py
    - 功能实现: kernel_gen/execute_engine/compiler.py
    """

    cleanup: Callable[[], None] | None = None
    try:
        if work_dir is None:
            work_dir = Path(tempfile.mkdtemp(prefix="kg_execute_engine_"))
            cleanup = lambda work_dir=work_dir: shutil.rmtree(work_dir, ignore_errors=True)
        work_dir.mkdir(parents=True, exist_ok=True)
        source_path = work_dir / "kernel.cpp"
        soname_path = work_dir / "libkernel.so"
        source_path.write_text(source, encoding="utf-8")
        command = build_compile_command(
            compiler=compiler,
            source_path=str(source_path),
            output_path=str(soname_path),
            compiler_flags=compiler_flags,
            link_flags=link_flags,
            include_dirs=include_dirs,
        )
        if dry_run:
            soname_path.write_text("", encoding="utf-8")
            stdout = f"dry-run: {' '.join(command)}"
            return CompileArtifacts(
                soname_path=str(soname_path),
                source_path=str(source_path),
                command=command,
                stdout=stdout,
                stderr="",
                return_code=0,
                _cleanup=cleanup,
            )

        result = _run_compiler_command(command)
        return CompileArtifacts(
            soname_path=str(soname_path),
            source_path=str(source_path),
            command=command,
            stdout=result.stdout,
            stderr=result.stderr,
            return_code=result.returncode,
            _cleanup=cleanup,
        )
    except Exception:
        if cleanup is not None:
            try:
                cleanup()
            except Exception:
                pass
        raise


__all__ = [
    "CompileArtifacts",
    "build_compile_command",
    "build_compile_unit",
    "compile_source",
    "default_compiler",
]
