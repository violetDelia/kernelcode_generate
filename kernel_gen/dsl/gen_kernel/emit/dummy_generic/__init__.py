"""Dummy generic backend fixture.


功能说明:
- 为 third-party generic backend 计划提供仓库内 dummy backend。
- 通过公开 `emit_c_impl(ModuleOp, target="dummy_generic")` 注册 ModuleOp handler。
- 通过公开 `register_compile_strategy("dummy_generic", ...)` 注册 compile-only 策略。

API 列表:
- 无公开 API。

使用示例:
- from kernel_gen.core.config import set_target
- set_target("dummy_generic")
- # 后续通过 `emit_c(module, EmitCContext())` 触发本 backend 注册的 handler。

关联文件:
- spec: spec/dsl/gen_kernel/backend_loader.md
- spec: spec/dsl/gen_kernel/source_bundle.md
- spec: spec/execute_engine/strategy.md
- test: test/dsl/gen_kernel/test_backend_loader.py
- test: test/execute_engine/test_compile_strategy.py
- 功能实现: kernel_gen/dsl/gen_kernel/emit/dummy_generic/__init__.py
"""

from __future__ import annotations

import os
from pathlib import Path
import tempfile

from xdsl.dialects.builtin import ModuleOp

from kernel_gen.core.config import get_dump_dir
from kernel_gen.core.error import ErrorKind, ErrorModule, KernelCodeError
from kernel_gen.dsl.gen_kernel.emit_context import EmitCContext
from kernel_gen.dsl.gen_kernel.emit.register import emit_c_impl
from kernel_gen.execute_engine import CompiledKernel, CompileRequest, register_compile_strategy

_TARGET = "dummy_generic"
_BUNDLE_MARKER_PREFIX = "// __KG_BUNDLE_FILE__:"


def _dummy_error(message: str) -> KernelCodeError:
    """构造 dummy backend 稳定错误。


    功能说明:
    - 把 dummy backend 的 source bundle 与 compile 策略错误归入 gen_kernel 或 execute_engine 合同错误。
    - 只在本文件内部使用。

    使用示例:
    - raise _dummy_error("source_bundle_malformed")
    """

    return KernelCodeError(ErrorKind.CONTRACT, ErrorModule.EXECUTE_ENGINE, message)


def _validate_bundle_path(path: str, seen_paths: set[str]) -> None:
    """校验 dummy backend bundle artifact 路径。


    功能说明:
    - 路径必须是安全 POSIX 相对路径。
    - 拒绝绝对路径、`.`、`..`、空 segment、反斜杠、NUL 与重复 path。

    使用示例:
    - _validate_bundle_path("kernel.cpp", set())
    """

    if (
        not path
        or path.startswith("/")
        or path in {".", ".."}
        or "\\" in path
        or "\x00" in path
        or path in seen_paths
    ):
        raise _dummy_error("source_bundle_malformed")
    if any(part in {"", ".", ".."} for part in path.split("/")):
        raise _dummy_error("source_bundle_malformed")
    seen_paths.add(path)


def _parse_source_bundle(source: str) -> dict[str, str] | None:
    """解析 SourceBundle aggregate string。


    功能说明:
    - 第一行不是 SourceBundle marker 时返回 `None`。
    - 第一行是 marker 时按 marker 切分为 artifact 映射。

    使用示例:
    - artifacts = _parse_source_bundle(source)
    """

    lines = source.splitlines()
    if not lines or not lines[0].startswith(_BUNDLE_MARKER_PREFIX):
        return None
    artifacts: dict[str, list[str]] = {}
    seen_paths: set[str] = set()
    current_path: str | None = None
    for line in lines:
        if line.startswith(_BUNDLE_MARKER_PREFIX):
            path = line[len(_BUNDLE_MARKER_PREFIX):]
            _validate_bundle_path(path, seen_paths)
            artifacts[path] = []
            current_path = path
            continue
        if current_path is None:
            raise _dummy_error("source_bundle_malformed")
        artifacts[current_path].append(line)
    return {path: "\n".join(content) for path, content in artifacts.items()}


def _safe_output_path(root: Path, artifact_path: str) -> Path:
    """生成位于 root 下的安全写出路径。


    功能说明:
    - 解析已有 symlink 后确认写出目标不逃逸 root。
    - 发现路径逃逸时稳定失败。

    使用示例:
    - path = _safe_output_path(Path("build"), "kernel.cpp")
    """

    root_resolved = root.resolve()
    output_path = (root / artifact_path).resolve(strict=False)
    if os.path.commonpath((str(root_resolved), str(output_path))) != str(root_resolved):
        raise _dummy_error("source_bundle_path_escape")
    return output_path


def _write_source_product(source: str, source_root: Path) -> None:
    """把普通源码或 SourceBundle 写入 source 工作目录。


    功能说明:
    - 普通源码写入 `source.cpp`。
    - SourceBundle 同时写入 aggregate `source.cpp` 和所有 artifact。

    使用示例:
    - _write_source_product(source, Path("source"))
    """

    source_root.mkdir(parents=True, exist_ok=True)
    source_text = source if source.endswith("\n") else f"{source}\n"
    (source_root / "source.cpp").write_text(source_text, encoding="utf-8")
    artifacts = _parse_source_bundle(source)
    if artifacts is None:
        return
    for artifact_path, content in artifacts.items():
        output_path = _safe_output_path(source_root, artifact_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        artifact_text = content if content.endswith("\n") else f"{content}\n"
        output_path.write_text(artifact_text, encoding="utf-8")


def _compile_root(function: str) -> Path:
    """返回 dummy compile 工作目录。


    功能说明:
    - `dump_dir` 非空时使用 `dump_dir/compile/dummy_generic/<function>`。
    - `dump_dir` 为空时创建临时目录。

    使用示例:
    - root = _compile_root("kernel")
    """

    dump_dir = get_dump_dir()
    safe_function = function.replace("::", "_").replace("/", "_")
    if dump_dir is not None:
        return dump_dir / "compile" / _TARGET / safe_function
    return Path(tempfile.mkdtemp(prefix="kg_dummy_compile_"))


@emit_c_impl(ModuleOp, target=_TARGET)
def _emit_dummy_module(module_op: ModuleOp, _ctx: EmitCContext) -> dict[str, str] | str:
    """发射 dummy backend ModuleOp。


    功能说明:
    - module 内含 `dummy_single` 函数名时返回单文件源码字符串。
    - 其它 module 返回多文件 SourceProduct mapping，用于验证 SourceBundle 编码。

    使用示例:
    - source = emit_c(module_op, EmitCContext())
    """

    func_names = [getattr(getattr(op, "sym_name", None), "data", "") for op in module_op.ops]
    if "dummy_single" in func_names:
        return "void dummy_single() {}\n"
    return {
        "kernel.cpp": "void dummy_bundle() {}\n",
        "include/kernel.h": "#pragma once\n",
    }


class _DummyCompileStrategy:
    """dummy backend compile-only 策略。"""

    def compile(self, request: CompileRequest) -> CompiledKernel:
        """执行 dummy backend compile-only 编译。


        功能说明:
        - 写出普通源码或 SourceBundle artifact。
        - 返回 compile-only `CompiledKernel`，执行阶段由 `CompiledKernel.execute(...)` 返回 `execution_unsupported`。

        使用示例:
        - kernel = _DummyCompileStrategy().compile(request)
        """

        if not isinstance(request.source, str) or not request.source.strip():
            raise _dummy_error("source_empty_or_invalid")
        if not isinstance(request.function, str) or not request.function.strip():
            raise _dummy_error("symbol_resolve_failed")
        root = _compile_root(request.function)
        source_root = root / "source"
        build_root = root / "build"
        _write_source_product(request.source, source_root)
        build_root.mkdir(parents=True, exist_ok=True)
        artifact = build_root / "libdummy.so"
        artifact.write_text("", encoding="utf-8")
        return CompiledKernel(
            target=request.target,
            soname_path=str(artifact),
            function=request.function,
            entry_point=request.entry_point,
            compile_stdout=f"dummy compile strategy: source={source_root} build={build_root}",
            compile_stderr="",
        )


register_compile_strategy(_TARGET, _DummyCompileStrategy(), override=True)

__all__: list[str] = []
