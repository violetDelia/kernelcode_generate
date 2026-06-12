"""execute_engine builtin strategy shared implementation.


功能说明:
- 承接内置 `cpu` / `npu_demo` / `cuda_sm86` 后端共享的源码校验、entry shim、编译命令和 SourceBundle 基础能力。
- 提供 `builtin_strategy` package 内部跨 target 复用的文件级 API。
- compile unit 源码、dry-run 占位产物和 runtime trance 目录路径派生统一委托 `kernel_gen.core.tools.dump_dir.DumpDirWriter`。
- 不运行期导入 `compiler.py`，不构造 `CompiledKernel`，不进入 `kernel_gen.execute_engine` 包根公开 API。

API 列表:
- `class BuiltinCompileArtifacts(soname_path: str, source_path: str, command: tuple[str, ...], stdout: str, stderr: str, return_code: int, allow_absent_memory_arg_specs: tuple[tuple[int, str, int], ...] = (), cleanup: Callable[[], None] | None = None)`
- `class BuiltinParamSpec(kind: str, ctype: str, memory_space: str | None = None, template_name: str | None = None)`
- `BuiltinStrategySupport: type`
- `BUNDLE_MARKER_PREFIX: str`
- `REPO_ROOT: Path`

helper 清单:
- package 内部 helper 只服务内置后端编译产物生成，不进入 `kernel_gen.execute_engine` 包根公开 API。

使用示例:
- unit = BuiltinStrategySupport.compose_compile_unit(source="int main(){}", include_lines_for_target=(), entry_shim_source="")
- metadata = BuiltinStrategySupport.extract_allow_absent_memory_arg_specs(source)

关联文件:
- spec: spec/execute_engine/execute_engine_target.md
- spec: spec/execute_engine/strategy.md
- test: test/execute_engine/test_builtin_strategy.py
- test: test/execute_engine/test_compile.py
- 功能实现: kernel_gen/execute_engine/builtin_strategy/__init__.py
- 功能实现: kernel_gen/execute_engine/builtin_strategy/cpu.py
- 功能实现: kernel_gen/execute_engine/builtin_strategy/npu_demo.py
- 功能实现: kernel_gen/execute_engine/builtin_strategy/cuda_sm86.py
"""

from __future__ import annotations

from collections.abc import Callable, Iterable
from dataclasses import dataclass, field
from functools import partial
from pathlib import Path
import re
import shutil
import subprocess
import tempfile

from kernel_gen.core.config import get_trance_enabled
from kernel_gen.core.error import ErrorKind, ErrorModule, KernelCodeError
from kernel_gen.core.tools.dump_dir import DumpDirWriter
_TARGET_HEADER_MISMATCH = "target_header_mismatch"
_SOURCE_EMPTY_OR_INVALID = "source_empty_or_invalid"
_COMPILE_FAILED = "compile_failed"
_TEMPLATE_INSTANCE_REQUIRED = "template_instance_required"
_SYMBOL_RESOLVE_FAILED = "symbol_resolve_failed"
_RUNTIME_THROW_OR_ABORT = "runtime_throw_or_abort"
_BUILTIN_KNOWN_ERROR_PHRASES: frozenset[str] = frozenset(
    {
        _TARGET_HEADER_MISMATCH,
        _SOURCE_EMPTY_OR_INVALID,
        _COMPILE_FAILED,
        _TEMPLATE_INSTANCE_REQUIRED,
        _SYMBOL_RESOLVE_FAILED,
        _RUNTIME_THROW_OR_ABORT,
    }
)

_COMPILER_ICE_MARKERS = (
    "internal compiler error",
    "Please submit a full bug report",
)
_INT_TYPE_PATTERN = re.compile(
    r"^(?:const\s+)?(?P<type>"
    r"S_INT|int|short|long|long\s+long|"
    r"unsigned\s+int|unsigned\s+long|unsigned\s+long\s+long|"
    r"int32_t|int64_t|uint32_t|uint64_t|size_t"
    r")(?:\s*&)?\s+\w+$"
)
_FLOAT_TYPE_PATTERN = re.compile(r"^(?:const\s+)?(?P<type>float|double)(?:\s*&)?\s+\w+$")
_KERNEL_CONTEXT_TYPE_PATTERN = re.compile(r"^(?:npu_demo::)?KernelContext\s*&\s+\w+$")
_COST_SUMMARY_TYPE_PATTERN = re.compile(r"^(?:std::)?string\s*&\s+\w+$")
_MEMORY_TYPE_PATTERN = re.compile(
    r"^(?:const\s+)?Memory<\s*(?P<space>[^,\s>]+)\s*,\s*(?P<dtype>[^>\s]+)\s*>\s*&\s+\w+$"
)
_TEMPLATE_PARAM_PATTERN = re.compile(r"\b(?:typename|class)\s+([A-Za-z_][A-Za-z0-9_]*)\b")
_TEMPLATE_DTYPE_OPTIONS: tuple[tuple[int, str], ...] = (
    (1, "float"),
    (2, "double"),
    (3, "int32_t"),
    (4, "int64_t"),
)
_CONCRETE_MEMORY_DTYPE_PATTERN = re.compile(
    r"Memory<\s*(?:MemorySpace::)?(?:GM|SM|LM|TSM|TLM1|TLM2|TLM3)\s*,\s*"
    r"(?P<dtype>float|double|int32_t|int64_t|int|long\s+long)\s*>"
)
_TEMPLATE_INSTANCE_SEED_PATTERN = re.compile(
    r"using\s+__kernel_gen_template_instance_seed_[A-Za-z0-9_]+__(?P<name>[A-Za-z_][A-Za-z0-9_]*)\s*=\s*"
    r"Memory<\s*(?:MemorySpace::)?(?:GM|SM|LM|TSM|TLM1|TLM2|TLM3)\s*,\s*"
    r"(?P<dtype>float|double|int32_t|int64_t|int|long\s+long)\s*>\s*;"
)
_ALLOW_ABSENT_MEMORY_ARGS_PATTERN = re.compile(r"//\s*kg\.allow_absent_memory_args:\s*(?P<body>[^\n]*)")
_BUNDLE_MARKER_PREFIX = "// __KG_BUNDLE_FILE__:"
_REPO_ROOT = Path(__file__).resolve().parents[3]


@dataclass(frozen=True)
class BuiltinCompileArtifacts:
    """内置 target 编译产物描述。

    功能说明:
    - 承载编译命令、产物路径、stdout/stderr、返回码和 allow-absent memory 参数元数据。
    - `cleanup` 只负责释放本模块内部创建的临时工作目录；调用方决定何时消费。

    使用示例:
    - artifacts = BuiltinCompileArtifacts("libkernel.so", "kernel.cpp", ("g++",), "", "", 0)
    """

    soname_path: str
    source_path: str
    command: tuple[str, ...]
    stdout: str
    stderr: str
    return_code: int
    allow_absent_memory_arg_specs: tuple[tuple[int, str, int], ...] = ()
    cleanup: Callable[[], None] | None = field(default=None, repr=False, compare=False)


@dataclass(frozen=True)
class _ParamSpec:
    """函数形参的最小描述。

    功能说明:
    - 描述 entry shim 绑定所需的参数类别与类型信息。
    - 仅在本文件内部用于内置后端 entry shim 生成。

    使用示例:
    - spec = _ParamSpec(kind="memory", ctype="int32_t", memory_space="GM")
    """

    kind: str
    ctype: str
    memory_space: str | None = None
    template_name: str | None = None


class _BuiltinStrategySupport:
    """当前文件内部实现容器，不进入文件级 API 或包根 `__all__`。"""

    @staticmethod
    def builtin_compile_error(failure_phrase: str, detail: str = "") -> KernelCodeError:
        """构造内置后端编译路径的 execute_engine 错误对象。

        功能说明:
        - 使用 execute_engine 已公开 failure phrase，避免 backend 实现自造错误语义。
        - 在错误对象上写入 `failure_phrase`，保持旧 `compiler.py` 观测行为。

        使用示例:
        - err = _BuiltinStrategySupport.builtin_compile_error("compile_failed", "compiler returned non-zero")
        """

        if failure_phrase not in _BUILTIN_KNOWN_ERROR_PHRASES:
            raise KernelCodeError(
                ErrorKind.CONTRACT,
                ErrorModule.EXECUTE_ENGINE,
                f"unknown failure phrase: {failure_phrase}",
            )
        message = failure_phrase if not detail else f"{failure_phrase}: {detail}"
        error = KernelCodeError(ErrorKind.CONTRACT, ErrorModule.EXECUTE_ENGINE, message)
        error.failure_phrase = failure_phrase
        return error


    @staticmethod
    def dtype_code_from_name(dtype: str | None) -> int:
        """把 dtype 文本映射为 entry shim dtype code。

        功能说明:
        - 为模板实例和 allow-absent metadata 校验提供最小 dtype 编码。
        - 未识别 dtype 返回 0，由调用方按公开错误语义拒绝。

        使用示例:
        - assert _BuiltinStrategySupport.dtype_code_from_name("float32") == 1
        """

        if dtype is None:
            return 0
        normalized = dtype.strip().lower().replace(" ", "")
        if normalized in {"float", "float32", "f32"}:
            return 1
        if normalized in {"double", "float64", "f64"}:
            return 2
        if normalized in {"int", "int32", "int32_t", "i32"}:
            return 3
        if normalized in {"longlong", "longlongint", "int64", "int64_t", "i64"}:
            return 4
        return 0


    @staticmethod
    def join_text_sections(*sections: str) -> str:
        """把多段源码文本按空行拼接。

        功能说明:
        - 过滤空字符串段，并统一去掉每段尾部空白。
        - 结果始终以单个换行结束，保持编译单元文本稳定。

        使用示例:
        - source = _BuiltinStrategySupport.join_text_sections("#include <a>", "int main() {}")
        """

        normalized_sections = tuple(section.rstrip() for section in sections if section)
        if not normalized_sections:
            return "\n"
        return "\n\n".join(normalized_sections).rstrip() + "\n"


    @staticmethod
    def looks_like_internal_compiler_error(stderr: str) -> bool:
        """判断编译 stderr 是否命中编译器内部错误特征。

        功能说明:
        - 识别 GCC/Clang 常见 internal compiler error 文本。
        - 供真实编译路径决定是否追加一次同命令重试。

        使用示例:
        - assert _BuiltinStrategySupport.looks_like_internal_compiler_error("internal compiler error: ...") is True
        """

        if not isinstance(stderr, str):
            return False
        return any(marker in stderr for marker in _COMPILER_ICE_MARKERS)


    @staticmethod
    def run_compiler_command(command: Iterable[str]) -> subprocess.CompletedProcess[str]:
        """运行编译命令，并在编译器内部异常时追加一次重试。

        功能说明:
        - 统一真实编译路径的命令执行与 stderr 判定逻辑。
        - 内部编译器异常仅重试一次，避免隐藏稳定失败。

        使用示例:
        - result = _BuiltinStrategySupport.run_compiler_command(["g++", "-std=c++17", "demo.cpp", "-o", "demo"])
        """

        argv = list(command)
        result = subprocess.run(argv, capture_output=True, text=True, check=False)
        if result.returncode != 0 and _BuiltinStrategySupport.looks_like_internal_compiler_error(result.stderr):
            result = subprocess.run(argv, capture_output=True, text=True, check=False)
        return result


    @staticmethod
    def compiler_default() -> str:
        """返回默认编译器名。

        功能说明:
        - 固定返回执行引擎内置 target 的默认编译器名。
        - 当前内置后端统一使用 `g++` 作为默认编译器。

        使用示例:
        - assert _BuiltinStrategySupport.compiler_default() == "g++"
        """

        return "g++"


    @staticmethod
    def remove_workdir(work_dir: Path) -> None:
        """删除内置编译路径创建的临时工作目录。

        功能说明:
        - 作为 `cleanup` 回调的顶层函数，避免在函数体内创建闭包。
        - 删除失败按忽略处理，匹配临时产物释放语义。

        使用示例:
        - cleanup = partial(_BuiltinStrategySupport.remove_workdir, Path("/tmp/kg"))
        """

        shutil.rmtree(work_dir, ignore_errors=True)


    @staticmethod
    def compose_compile_unit(
        *,
        source: str,
        include_lines_for_target: tuple[str, ...],
        entry_shim_source: str,
    ) -> str:
        """拼接最终编译单元源码。

        功能说明:
        - 以 target include set、原始 source、entry shim 的顺序拼接编译单元。
        - 若 source 已含部分 target include，则仅补齐缺失项。

        使用示例:
        - unit = _BuiltinStrategySupport.compose_compile_unit(source="int main(){}", include_lines_for_target=(), entry_shim_source="")
        """

        missing_includes = tuple(line for line in include_lines_for_target if line not in source)
        sections: list[str] = []
        if missing_includes:
            sections.append("\n".join(missing_includes))
        sections.append(source.rstrip())
        if entry_shim_source:
            sections.append(entry_shim_source.rstrip())
        return _BuiltinStrategySupport.join_text_sections(*sections)


    @staticmethod
    def compose_compile_command(
        *,
        compiler: str,
        source_path: str,
        output_path: str,
        compiler_flags: Iterable[str],
        link_flags: Iterable[str],
        include_dirs: Iterable[str],
    ) -> tuple[str, ...]:
        """生成编译命令。

        功能说明:
        - 按 compiler、共享库参数、flags、include dirs、source、output、link flags 的顺序生成命令。
        - 固定生成 `-shared -fPIC` 产物，供执行引擎运行期加载。

        使用示例:
        - cmd = _BuiltinStrategySupport.compose_compile_command(compiler="g++", source_path="a.cpp", output_path="a.so", compiler_flags=(), link_flags=(), include_dirs=(".",))
        """

        include_args = [f"-I{path}" for path in include_dirs]
        return (
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


    @staticmethod
    def sanitize_trance_kernel_name(value: str) -> str:
        """规整 runtime trance 使用的 kernel 名称。

        功能说明:
        - 以公开编译入口 `function` 名为来源，去掉命名空间并替换路径不安全字符。
        - 空结果回退为 `kernel`。

        使用示例:
        - assert _BuiltinStrategySupport.sanitize_trance_kernel_name("npu_demo::add_kernel") == "add_kernel"
        """

        short_name = value.rsplit("::", 1)[-1].strip()
        safe_name = re.sub(r"[^A-Za-z0-9_.-]+", "_", short_name)
        return safe_name or "kernel"


    @staticmethod
    def cpp_string_define_arg(name: str, value: str) -> str:
        """生成 C++ 字符串宏的编译参数。

        功能说明:
        - 将 Python 字符串转成 `-DNAME="value"` 形式。
        - 仅转义反斜杠和双引号，避免路径字符改变宏语义。

        使用示例:
        - arg = _BuiltinStrategySupport.cpp_string_define_arg("KG_TRANCE_KERNEL_NAME", "add_kernel")
        """

        escaped = value.replace("\\", "\\\\").replace('"', '\\"')
        return f'-D{name}="{escaped}"'


    @staticmethod
    def trance_compiler_flags(
        *,
        function: str,
        compiler_flags: tuple[str, ...],
    ) -> tuple[str, ...]:
        """按公开 core config 追加 runtime trance 编译宏。

        功能说明:
        - `trance_enabled=False` 时保持原 flags 不变。
        - `trance_enabled=True` 时追加 `TRANCE`、kernel 名称、trace 目录和旧文件路径空宏。

        使用示例:
        - flags = _BuiltinStrategySupport.trance_compiler_flags(function="add", compiler_flags=("-std=c++17",))
        """

        if not get_trance_enabled():
            return compiler_flags
        kernel_name = _BuiltinStrategySupport.sanitize_trance_kernel_name(function)
        writer = DumpDirWriter.from_config()
        trace_dir = "" if writer is None else str(writer.child(kernel_name, fallback="kernel").child("trance").root)
        return (
            *compiler_flags,
            "-DTRANCE",
            _BuiltinStrategySupport.cpp_string_define_arg("KG_TRANCE_KERNEL_NAME", kernel_name),
            _BuiltinStrategySupport.cpp_string_define_arg("KG_TRANCE_DIR_PATH", trace_dir),
            _BuiltinStrategySupport.cpp_string_define_arg("KG_TRANCE_FILE_PATH", ""),
        )


    @staticmethod
    def compile_unit_source(
        *,
        source: str,
        compiler: str,
        compiler_flags: tuple[str, ...],
        link_flags: tuple[str, ...],
        include_dirs: tuple[str, ...],
        work_dir: Path | None = None,
        dry_run: bool = True,
    ) -> BuiltinCompileArtifacts:
        """执行或模拟编译流程。

        功能说明:
        - 将编译单元写入工作目录，生成编译命令并执行或 dry-run。
        - 内部自动创建临时目录时，通过返回值携带 cleanup 回调。

        使用示例:
        - artifacts = _BuiltinStrategySupport.compile_unit_source(source="int main(){}", compiler="g++", compiler_flags=("-std=c++17",), link_flags=(), include_dirs=(".",))
        """

        cleanup: Callable[[], None] | None = None
        try:
            if work_dir is None:
                work_dir = Path(tempfile.mkdtemp(prefix="kg_execute_engine_"))
                cleanup = partial(_BuiltinStrategySupport.remove_workdir, work_dir)
            writer = DumpDirWriter(work_dir)
            work_dir = writer.root
            source_path = writer.write("kernel.cpp", source)
            soname_path = work_dir / "libkernel.so"
            command = _BuiltinStrategySupport.compose_compile_command(
                compiler=compiler,
                source_path=str(source_path),
                output_path=str(soname_path),
                compiler_flags=compiler_flags,
                link_flags=link_flags,
                include_dirs=include_dirs,
            )
            if dry_run:
                soname_path = writer.write("libkernel.so", "")
                stdout = f"dry-run: {' '.join(command)}"
                return BuiltinCompileArtifacts(
                    soname_path=str(soname_path),
                    source_path=str(source_path),
                    command=command,
                    stdout=stdout,
                    stderr="",
                    return_code=0,
                    cleanup=cleanup,
                )

            result = _BuiltinStrategySupport.run_compiler_command(command)
            return BuiltinCompileArtifacts(
                soname_path=str(soname_path),
                source_path=str(source_path),
                command=command,
                stdout=result.stdout,
                stderr=result.stderr,
                return_code=result.returncode,
                cleanup=cleanup,
            )
        except Exception:
            if cleanup is not None:
                cleanup()
            raise


    @staticmethod
    def include_lines_for_target(target: str) -> tuple[str, ...]:
        """返回 target 对应的 include set。

        功能说明:
        - 固定 `cpu`、`npu_demo` 与 `cuda_sm86` 的 include 注入集合。
        - 不支持的 target 返回空集合，由上层转成稳定失败。

        使用示例:
        - assert _BuiltinStrategySupport.include_lines_for_target("npu_demo") == ('#include "include/npu_demo/npu_demo.h"',)
        """

        if target == "npu_demo":
            return ('#include "include/npu_demo/npu_demo.h"',)
        if target == "cuda_sm86":
            return ('#include "include/cuda_sm86/cuda_sm86.cuh"',)
        if target == "cpu":
            return (
                '#include "include/cpu/Memory.h"',
                '#include "include/cpu/Nn.h"',
            )
        return ()


    @staticmethod
    def extract_allow_absent_memory_arg_specs(source: str | None) -> tuple[tuple[int, str, int], ...]:
        """从源码注释提取 allow-absent memory 参数元数据。

        功能说明:
        - 解析 `// kg.allow_absent_memory_args: <index>:<dtype>:<rank>;...`。
        - 返回纯 tuple 元数据，避免本模块泄露调用方运行期结构。

        使用示例:
        - specs = _BuiltinStrategySupport.extract_allow_absent_memory_arg_specs("// kg.allow_absent_memory_args: 2:float:1")
        """

        if not isinstance(source, str) or not source.strip():
            return ()
        items: dict[int, tuple[int, str, int]] = {}
        for match in _ALLOW_ABSENT_MEMORY_ARGS_PATTERN.finditer(source):
            body = match.group("body").strip()
            if not body:
                continue
            for item in body.split(";"):
                text = item.strip()
                if not text:
                    continue
                parts = text.split(":")
                if len(parts) != 3:
                    raise _BuiltinStrategySupport.builtin_compile_error(_RUNTIME_THROW_OR_ABORT, "invalid allow-absent memory metadata")
                index_text, dtype_text, rank_text = parts
                try:
                    index = int(index_text)
                    rank = int(rank_text)
                except ValueError as exc:
                    raise _BuiltinStrategySupport.builtin_compile_error(_RUNTIME_THROW_OR_ABORT, "invalid allow-absent memory metadata") from exc
                dtype = dtype_text.strip()
                if index < 0 or rank <= 0 or not dtype or _BuiltinStrategySupport.dtype_code_from_name(dtype) == 0:
                    raise _BuiltinStrategySupport.builtin_compile_error(_RUNTIME_THROW_OR_ABORT, "invalid allow-absent memory metadata")
                items[index] = (index, dtype, rank)
        return tuple(items[index] for index in sorted(items))


    @staticmethod
    def allow_absent_memory_arg_specs_map(metadata: tuple[tuple[int, str, int], ...]) -> dict[int, tuple[int, str, int]]:
        """把 allow-absent 纯 metadata 转成按 runtime index 查询的字典。

        功能说明:
        - 只在生成 entry shim 时判断某个 memory 参数是否允许 data 为空。
        - metadata 已按 index 唯一化，字典便于按 runtime 参数下标查询。

        使用示例:
        - metadata_map = _BuiltinStrategySupport.allow_absent_memory_arg_specs_map(metadata)
        """

        return {index: item for index, item in ((entry[0], entry) for entry in metadata)}


    @staticmethod
    def split_params(params_text: str) -> tuple[str, ...]:
        """按顶层逗号切分函数形参。

        功能说明:
        - 对带模板参数的函数形参进行稳定切分。
        - 忽略 `<...>`、`(...)`、`[...]` 内部逗号，避免误拆。

        使用示例:
        - params = _BuiltinStrategySupport.split_params("Memory<GM, int32_t>& out, const Memory<GM, int32_t>& lhs")
        """

        if not params_text.strip():
            return ()
        parts: list[str] = []
        current: list[str] = []
        angle_depth = 0
        paren_depth = 0
        bracket_depth = 0
        for ch in params_text:
            if ch == "<":
                angle_depth += 1
            elif ch == ">":
                angle_depth = max(0, angle_depth - 1)
            elif ch == "(":
                paren_depth += 1
            elif ch == ")":
                paren_depth = max(0, paren_depth - 1)
            elif ch == "[":
                bracket_depth += 1
            elif ch == "]":
                bracket_depth = max(0, bracket_depth - 1)
            if ch == "," and angle_depth == 0 and paren_depth == 0 and bracket_depth == 0:
                item = "".join(current).strip()
                if item:
                    parts.append(item)
                current = []
                continue
            current.append(ch)
        tail = "".join(current).strip()
        if tail:
            parts.append(tail)
        return tuple(parts)


    @staticmethod
    def template_names_from_header(template_text: str | None) -> frozenset[str]:
        """解析 C++ template header 中的类型参数名。

        功能说明:
        - 仅识别 `typename T` / `class T` 形式。
        - 无 template header 时返回空集合。

        使用示例:
        - names = _BuiltinStrategySupport.template_names_from_header("typename T1, typename T2")
        """

        if template_text is None:
            return frozenset()
        return frozenset(_TEMPLATE_PARAM_PATTERN.findall(template_text))


    @staticmethod
    def template_names_before_function(source: str, function_start: int) -> frozenset[str]:
        """读取紧邻函数定义前的 C++ template header。

        功能说明:
        - 当正则从函数返回类型处开始匹配时，补充解析其前一段紧邻的 `template <...>`。
        - 只接受被 `;` / `{` / `}` 分隔后的最后一段文本。

        使用示例:
        - names = _BuiltinStrategySupport.template_names_before_function(source, function_start)
        """

        prefix = source[:function_start]
        boundary = max(prefix.rfind(";"), prefix.rfind("{"), prefix.rfind("}"))
        tail = prefix[boundary + 1 :].strip()
        match = re.search(r"template\s*<(?P<template>[^>]*)>\s*[^;{}]*$", tail, re.DOTALL)
        if match is None:
            return frozenset()
        return _BuiltinStrategySupport.template_names_from_header(match.group("template"))


    @staticmethod
    def parse_param_spec(param_text: str, template_names: frozenset[str] = frozenset()) -> _ParamSpec | None:
        """把单个形参文本解析为最小参数规格。

        功能说明:
        - 支持 `Memory<Space, T>&`、整型标量、浮点标量、`KernelContext&` 和 `std::string&` 输出捕获参数。
        - 不支持的参数形态返回 `None`，由上层回退占位 shim。

        使用示例:
        - spec = _BuiltinStrategySupport.parse_param_spec("const Memory<GM, int32_t>& lhs")
        """

        normalized = " ".join(param_text.strip().split())
        memory_match = _MEMORY_TYPE_PATTERN.match(normalized)
        if memory_match is not None:
            dtype = memory_match.group("dtype")
            return _ParamSpec(
                kind="memory",
                ctype=dtype,
                memory_space=memory_match.group("space"),
                template_name=dtype if dtype in template_names else None,
            )
        int_match = _INT_TYPE_PATTERN.match(normalized)
        if int_match is not None:
            return _ParamSpec(kind="int", ctype=int_match.group("type"))
        float_match = _FLOAT_TYPE_PATTERN.match(normalized)
        if float_match is not None:
            return _ParamSpec(kind="float", ctype=float_match.group("type"))
        if _KERNEL_CONTEXT_TYPE_PATTERN.match(normalized):
            return _ParamSpec(kind="kernel_context", ctype="npu_demo::KernelContext")
        if _COST_SUMMARY_TYPE_PATTERN.match(normalized):
            return _ParamSpec(kind="cost_summary", ctype="std::string")
        return None


    @staticmethod
    def extract_param_specs(source: str, function: str) -> tuple[_ParamSpec, ...] | None:
        """从源码中提取 function 定义对应的参数规格。

        功能说明:
        - 在源码中查找目标函数定义并解析参数。
        - 同时尝试完整名称与短名匹配。

        使用示例:
        - params = _BuiltinStrategySupport.extract_param_specs("void add_kernel(int x) {}", "add_kernel")
        """

        candidates = [function]
        short_name = function.split("::")[-1]
        if short_name not in candidates:
            candidates.append(short_name)

        for function_name in candidates:
            pattern = re.compile(
                rf"(?:template\s*<(?P<template>[^>]*)>\s*)?[^;{{}}]*\b{re.escape(function_name)}\s*\((?P<params>.*?)\)\s*\{{",
                re.DOTALL,
            )
            for match in pattern.finditer(source):
                params = _BuiltinStrategySupport.split_params(match.group("params"))
                template_names = _BuiltinStrategySupport.template_names_from_header(match.groupdict().get("template"))
                if not template_names:
                    function_start = source.rfind(function_name, match.start(), match.start("params"))
                    template_names = _BuiltinStrategySupport.template_names_before_function(
                        source,
                        function_start if function_start >= 0 else match.start(),
                    )
                specs: list[_ParamSpec] = []
                for param in params:
                    spec = _BuiltinStrategySupport.parse_param_spec(param, template_names)
                    if spec is None:
                        specs = []
                        break
                    specs.append(spec)
                if specs or not params:
                    return tuple(specs)
        return None


    @staticmethod
    def template_names_from_param_specs(params: tuple[_ParamSpec, ...]) -> tuple[str, ...]:
        """按参数顺序收集 template dtype 名称。

        功能说明:
        - 仅收集 memory 参数中出现的 `template_name`。
        - 保持首次出现顺序，供 shim 生成模板实参列表。

        使用示例:
        - names = _BuiltinStrategySupport.template_names_from_param_specs(params)
        """

        names: list[str] = []
        for spec in params:
            if spec.template_name is not None and spec.template_name not in names:
                names.append(spec.template_name)
        return tuple(names)


    @staticmethod
    def runtime_template_combinations_from_source(
        template_names: tuple[str, ...],
        source: str | None,
    ) -> tuple[dict[str, tuple[int, str]], ...]:
        """根据源码中的 concrete memory dtype 生成唯一模板实例。

        功能说明:
        - 优先使用源码中的 template dtype seed alias，按 template name 精确绑定 dtype。
        - 找不到 concrete dtype 时稳定失败，避免默认实例化为 `float`。

        使用示例:
        - combos = _BuiltinStrategySupport.runtime_template_combinations_from_source(("T1",), source)
        """

        if not template_names:
            return ()
        if isinstance(source, str):
            seed_types: dict[str, tuple[int, str]] = {}
            for match in _TEMPLATE_INSTANCE_SEED_PATTERN.finditer(source):
                name = match.group("name")
                if name not in template_names or name in seed_types:
                    continue
                code = _BuiltinStrategySupport.dtype_code_from_name(match.group("dtype"))
                if code == 0:
                    continue
                ctype = next((candidate for candidate_code, candidate in _TEMPLATE_DTYPE_OPTIONS if candidate_code == code), None)
                if ctype is not None:
                    seed_types[name] = (code, ctype)
            if seed_types:
                if all(name in seed_types for name in template_names):
                    return ({name: seed_types[name] for name in template_names},)
                raise _BuiltinStrategySupport.builtin_compile_error(
                    _TEMPLATE_INSTANCE_REQUIRED,
                    "templated memory function requires concrete memory dtype in source",
                )
            for match in _CONCRETE_MEMORY_DTYPE_PATTERN.finditer(source):
                code = _BuiltinStrategySupport.dtype_code_from_name(match.group("dtype"))
                if code == 0:
                    continue
                ctype = next((candidate for candidate_code, candidate in _TEMPLATE_DTYPE_OPTIONS if candidate_code == code), None)
                if ctype is not None:
                    return ({name: (code, ctype) for name in template_names},)
        raise _BuiltinStrategySupport.builtin_compile_error(
            _TEMPLATE_INSTANCE_REQUIRED,
            "templated memory function requires concrete memory dtype in source",
        )


    @staticmethod
    def runtime_param_declaration_lines(
        params: tuple[_ParamSpec, ...],
        template_types: dict[str, tuple[int, str]] | None = None,
        allow_absent_memory_arg_specs: tuple[tuple[int, str, int], ...] = (),
    ) -> tuple[list[str], list[str], list[str]]:
        """生成 runtime shim 参数校验、声明与调用实参。

        功能说明:
        - 普通函数与 templated 函数共用同一套 memory/int/float 参数封送文本。
        - 带 allow-absent metadata 的 memory 参数允许 `data == nullptr`。

        使用示例:
        - lines, call_args, trance_lines = _BuiltinStrategySupport.runtime_param_declaration_lines(params, {"T1": (1, "float")})
        """

        lines: list[str] = []
        call_args: list[str] = []
        trance_arg_lines: list[str] = []
        runtime_arg_index = 0
        allow_absent_map = _BuiltinStrategySupport.allow_absent_memory_arg_specs_map(allow_absent_memory_arg_specs)
        for spec in params:
            if spec.kind == "kernel_context":
                lines.append("  npu_demo::KernelContext ctx;")
                call_args.append("ctx")
                continue
            if spec.kind == "cost_summary":
                lines.append("  std::string __kg_cost_summary;")
                call_args.append("__kg_cost_summary")
                continue
            runtime_idx = runtime_arg_index
            runtime_arg_index += 1
            if spec.kind == "memory":
                ctype = spec.ctype
                if spec.template_name is not None and template_types is not None:
                    ctype = template_types[spec.template_name][1]
                null_data_check = "ordered_args[{idx}].data == nullptr || " if runtime_idx not in allow_absent_map else ""
                lines.extend(
                    [
                        f"  if (ordered_args[{runtime_idx}].kind != KG_ARG_MEMORY) {{",
                        "    return -1;",
                        "  }",
                        f"  if ({null_data_check.format(idx=runtime_idx)}ordered_args[{runtime_idx}].shape == nullptr || ordered_args[{runtime_idx}].stride == nullptr) {{",
                        "    return -1;",
                        "  }",
                        f"  Memory<{spec.memory_space}, {ctype}> arg{runtime_idx}(",
                        f"      reinterpret_cast<{ctype}*>(ordered_args[{runtime_idx}].data),",
                        f"      ordered_args[{runtime_idx}].shape,",
                        f"      ordered_args[{runtime_idx}].stride,",
                        f"      ordered_args[{runtime_idx}].rank);",
                    ]
                )
                call_args.append(f"arg{runtime_idx}")
                trance_arg_lines.append(f'  arg{runtime_idx}.trance_print(__kg_trance_sink, "arg{runtime_idx}");')
                continue
            if spec.kind == "int":
                lines.extend(
                    [
                        f"  if (ordered_args[{runtime_idx}].kind != KG_ARG_INT) {{",
                        "    return -1;",
                        "  }",
                        f"  {spec.ctype} arg{runtime_idx} = static_cast<{spec.ctype}>(ordered_args[{runtime_idx}].int_value);",
                    ]
                )
                call_args.append(f"arg{runtime_idx}")
                trance_arg_lines.append(f'  kernelcode::trance::print_value_arg(__kg_trance_sink, "arg{runtime_idx}", arg{runtime_idx});')
                continue
            lines.extend(
                [
                    f"  if (ordered_args[{runtime_idx}].kind != KG_ARG_FLOAT) {{",
                    "    return -1;",
                    "  }",
                    f"  {spec.ctype} arg{runtime_idx} = static_cast<{spec.ctype}>(ordered_args[{runtime_idx}].float_value);",
                ]
            )
            call_args.append(f"arg{runtime_idx}")
            trance_arg_lines.append(f'  kernelcode::trance::print_value_arg(__kg_trance_sink, "arg{runtime_idx}", arg{runtime_idx});')
        return lines, call_args, trance_arg_lines


    @staticmethod
    def template_condition_lines(
        params: tuple[_ParamSpec, ...],
        template_types: dict[str, tuple[int, str]],
    ) -> list[str]:
        """生成 template runtime dtype 分支条件。

        功能说明:
        - 每个携带 template name 的 memory 参数必须匹配当前实例化 dtype code。
        - 未携带 template name 的参数不参与分支条件。

        使用示例:
        - conditions = _BuiltinStrategySupport.template_condition_lines(params, {"T1": (1, "float")})
        """

        conditions: list[str] = []
        runtime_arg_index = 0
        for spec in params:
            if spec.kind == "kernel_context":
                continue
            runtime_idx = runtime_arg_index
            runtime_arg_index += 1
            if spec.kind == "memory" and spec.template_name is not None:
                code, _ctype = template_types[spec.template_name]
                conditions.append(f"ordered_args[{runtime_idx}].dtype_code == {code}")
        return conditions


    @staticmethod
    def build_runtime_entry_shim_source(
        *,
        function: str,
        entry_point: str,
        params: tuple[_ParamSpec, ...],
        source: str | None = None,
    ) -> str:
        """根据参数规格生成可运行 entry shim。

        功能说明:
        - 生成稳定的 C ABI 入口：`extern "C" int <entry_point>(...)`。
        - 把 `ordered_args` 映射为函数形参并执行真实调用。

        使用示例:
        - shim = _BuiltinStrategySupport.build_runtime_entry_shim_source(function="add_kernel", entry_point="kg_execute_entry", params=())
        """

        runtime_params = [spec for spec in params if spec.kind not in {"kernel_context", "cost_summary"}]
        has_cost_summary_param = any(spec.kind == "cost_summary" for spec in params)
        allow_absent_memory_arg_specs = _BuiltinStrategySupport.extract_allow_absent_memory_arg_specs(source)
        lines: list[str] = [
            f"// runtime entry shim for {function} as {entry_point}",
            "enum KgArgKind : int {",
            "  KG_ARG_MEMORY = 1,",
            "  KG_ARG_INT = 2,",
            "  KG_ARG_FLOAT = 3,",
            "};",
            "struct _ArgSlot {",
            "  int kind;",
            "  void* data;",
            "  const long long* shape;",
            "  const long long* stride;",
            "  unsigned long long rank;",
            "  int dtype_code;",
            "  long long int_value;",
            "  double float_value;",
            "};",
            f'extern "C" int {entry_point}(const _ArgSlot* ordered_args, unsigned long long arg_count) {{',
            "  if (ordered_args == nullptr) {",
            "    return -1;",
            "  }",
            f"  if (arg_count != {len(runtime_params)}ULL) {{",
            "    return -1;",
            "  }",
            "#ifdef TRANCE",
            "  const bool __kg_trance_entry_log_enabled = KG_TRANCE_DIR_PATH[0] == '\\0';",
            "  kernelcode::trance::ScopedTranceSink __kg_trance_scope;",
            "  const kernelcode::trance::TranceSink& __kg_trance_sink = kernelcode::trance::current_sink();",
            "  if (__kg_trance_entry_log_enabled) {",
            '    kernelcode::trance::print_func_begin(__kg_trance_sink, KG_TRANCE_KERNEL_NAME, "template=<none>");',
            '    kernelcode::trance::write_line(__kg_trance_sink, "args =");',
            "  }",
            "#endif",
        ]
        template_names = _BuiltinStrategySupport.template_names_from_param_specs(params)
        if template_names:
            for template_types in _BuiltinStrategySupport.runtime_template_combinations_from_source(template_names, source):
                conditions = _BuiltinStrategySupport.template_condition_lines(params, template_types)
                if not conditions:
                    continue
                lines.append(f"  if ({' && '.join(conditions)}) {{")
                branch_lines, call_args, trance_arg_lines = _BuiltinStrategySupport.runtime_param_declaration_lines(
                    params,
                    template_types,
                    allow_absent_memory_arg_specs,
                )
                lines.extend(f"  {line}" if line else line for line in branch_lines)
                if trance_arg_lines:
                    lines.extend(
                        [
                            "  #ifdef TRANCE",
                            "    if (__kg_trance_entry_log_enabled) {",
                            *(f"    {line}" for line in trance_arg_lines),
                            "    }",
                            "  #endif",
                        ]
                    )
                template_args = ", ".join(template_types[name][1] for name in template_names)
                lines.append(f"  {function}<{template_args}>({', '.join(call_args)});")
                lines.append("    return 0;")
                lines.append("  }")
            lines.extend(["  return -1;", "}", ""])
            regular_source = _BuiltinStrategySupport.join_text_sections("\n".join(lines))
            if not has_cost_summary_param:
                return regular_source
            capture_lines: list[str] = [
                f'extern "C" int {entry_point}_capture('
                "const _ArgSlot* ordered_args, unsigned long long arg_count, "
                "char* output, unsigned long long output_capacity, unsigned long long* output_size) {",
                "  if (ordered_args == nullptr || output == nullptr || output_size == nullptr || output_capacity == 0ULL) {",
                "    return -1;",
                "  }",
                f"  if (arg_count != {len(runtime_params)}ULL) {{",
                "    return -1;",
                "  }",
                "  *output_size = 0ULL;",
            ]
            for template_types in _BuiltinStrategySupport.runtime_template_combinations_from_source(template_names, source):
                conditions = _BuiltinStrategySupport.template_condition_lines(params, template_types)
                if not conditions:
                    continue
                capture_lines.append(f"  if ({' && '.join(conditions)}) {{")
                branch_lines, call_args, _trance_arg_lines = _BuiltinStrategySupport.runtime_param_declaration_lines(
                    params,
                    template_types,
                    allow_absent_memory_arg_specs,
                )
                capture_lines.extend(f"  {line}" if line else line for line in branch_lines)
                template_args = ", ".join(template_types[name][1] for name in template_names)
                capture_lines.extend(
                    [
                        "    try {",
                        f"      {function}<{template_args}>({', '.join(call_args)});",
                        "    } catch (...) {",
                        "      return -1;",
                        "    }",
                        "    const unsigned long long __kg_text_size = static_cast<unsigned long long>(__kg_cost_summary.size());",
                        "    if (__kg_text_size >= output_capacity) {",
                        "      return -1;",
                        "    }",
                        "    for (unsigned long long __kg_i = 0; __kg_i < __kg_text_size; ++__kg_i) {",
                        "      output[__kg_i] = __kg_cost_summary[__kg_i];",
                        "    }",
                        "    output[__kg_text_size] = '\\0';",
                        "    *output_size = __kg_text_size;",
                        "    return 0;",
                        "  }",
                    ]
                )
            capture_lines.extend(["  return -1;", "}", ""])
            return _BuiltinStrategySupport.join_text_sections(regular_source, "\n".join(capture_lines))

        decl_lines, call_args, trance_arg_lines = _BuiltinStrategySupport.runtime_param_declaration_lines(
            params,
            allow_absent_memory_arg_specs=allow_absent_memory_arg_specs,
        )
        lines.extend(decl_lines)
        if trance_arg_lines:
            lines.extend(
                [
                    "#ifdef TRANCE",
                    "  if (__kg_trance_entry_log_enabled) {",
                    *trance_arg_lines,
                    "  }",
                    "#endif",
                ]
            )
        lines.extend(
            [
                f"  {function}({', '.join(call_args)});",
                "  return 0;",
                "}",
                "",
            ]
        )
        regular_source = _BuiltinStrategySupport.join_text_sections("\n".join(lines))
        if not has_cost_summary_param:
            return regular_source
        capture_lines = [
            f'extern "C" int {entry_point}_capture('
            "const _ArgSlot* ordered_args, unsigned long long arg_count, "
            "char* output, unsigned long long output_capacity, unsigned long long* output_size) {",
            "  if (ordered_args == nullptr || output == nullptr || output_size == nullptr || output_capacity == 0ULL) {",
            "    return -1;",
            "  }",
            f"  if (arg_count != {len(runtime_params)}ULL) {{",
            "    return -1;",
            "  }",
            "  *output_size = 0ULL;",
        ]
        capture_lines.extend(decl_lines)
        capture_lines.extend(
            [
                "  try {",
                f"    {function}({', '.join(call_args)});",
                "  } catch (...) {",
                "    return -1;",
                "  }",
                "  const unsigned long long __kg_text_size = static_cast<unsigned long long>(__kg_cost_summary.size());",
                "  if (__kg_text_size >= output_capacity) {",
                "    return -1;",
                "  }",
                "  for (unsigned long long __kg_i = 0; __kg_i < __kg_text_size; ++__kg_i) {",
                "    output[__kg_i] = __kg_cost_summary[__kg_i];",
                "  }",
                "  output[__kg_text_size] = '\\0';",
                "  *output_size = __kg_text_size;",
                "  return 0;",
                "}",
                "",
            ]
        )
        return _BuiltinStrategySupport.join_text_sections(regular_source, "\n".join(capture_lines))


    @staticmethod
    def requires_entry_shim(source: str, entry_point: str) -> bool:
        """判断是否需要生成 entry shim。

        功能说明:
        - 当源码未显式提供 `extern "C"` 且同名入口时返回 True。
        - 用于避免重复生成已存在的稳定入口。

        使用示例:
        - assert _BuiltinStrategySupport.requires_entry_shim('extern "C" int kg_execute_entry(...) { return 0; }', "kg_execute_entry") is False
        """

        if not isinstance(source, str) or not isinstance(entry_point, str):
            return True
        pattern = rf'extern\s+"C"\s+[^;{{]*\b{re.escape(entry_point)}\b'
        return re.search(pattern, source) is None


    @staticmethod
    def compose_entry_shim_source(*, function: str, entry_point: str, source: str | None = None) -> str:
        """构造 entry shim 源码片段。

        功能说明:
        - 可解析参数时生成真实参数绑定 shim。
        - 参数不可解析时回退最小占位 shim，保持编译路径兼容。

        使用示例:
        - src = _BuiltinStrategySupport.compose_entry_shim_source(function="cpu::add", entry_point="kg_execute_entry", source="void add(){}")
        """

        if isinstance(source, str) and source.strip():
            params = _BuiltinStrategySupport.extract_param_specs(source, function)
            if params is not None:
                return _BuiltinStrategySupport.build_runtime_entry_shim_source(
                    function=function,
                    entry_point=entry_point,
                    params=params,
                    source=source,
                )
        return (
            f"// entry shim placeholder for {function} as {entry_point}\n"
            "struct _ArgSlot;\n"
            f'extern "C" int {entry_point}(const _ArgSlot* ordered_args, unsigned long long arg_count) {{\n'
            "  (void)ordered_args;\n"
            "  (void)arg_count;\n"
            "  return 0;\n"
            "}\n"
        )


    @staticmethod
    def source_include_family(source: str) -> str | None:
        """从 source 粗略推断 include family。

        功能说明:
        - 只识别仓库约定路径片段：`include/cpu/`、`include/npu_demo/` 与 `include/cuda_sm86/`。
        - 混合 include 返回 `mixed`，由上层转成稳定失败。

        使用示例:
        - assert _BuiltinStrategySupport.source_include_family('#include "include/cpu/Memory.h"') == "cpu"
        """

        has_cpu = "include/cpu/" in source
        has_npu = "include/npu_demo/" in source
        has_cuda_sm86 = "include/cuda_sm86/" in source
        if sum(1 for item in (has_cpu, has_npu, has_cuda_sm86) if item) > 1:
            return "mixed"
        if has_cpu:
            return "cpu"
        if has_npu:
            return "npu_demo"
        if has_cuda_sm86:
            return "cuda_sm86"
        return None


    @staticmethod
    def ensure_compiler_flags(flags: tuple[str, ...]) -> tuple[str, ...]:
        """确保编译 flags 包含 -std=c++17 基线。

        功能说明:
        - 若调用方未提供 `-std=c++17`，则按基线规则补齐。
        - 其余 flags 保持原有顺序。

        使用示例:
        - assert _BuiltinStrategySupport.ensure_compiler_flags(("-O2",)) == ("-std=c++17", "-O2")
        """

        if "-std=c++17" in flags:
            return flags
        return ("-std=c++17", *flags)


    @staticmethod
    def resolve_compiler_name(compiler: str | None) -> str:
        """解析编译器名称。

        功能说明:
        - 当 compiler 为 `None` 时回退到默认编译器。
        - 空字符串或非字符串会按 `compile_failed` 稳定失败。

        使用示例:
        - assert _BuiltinStrategySupport.resolve_compiler_name(None) == "g++"
        """

        if compiler is None:
            return _BuiltinStrategySupport.compiler_default()
        if not isinstance(compiler, str) or not compiler.strip():
            raise _BuiltinStrategySupport.builtin_compile_error(_COMPILE_FAILED, "compiler is empty")
        return compiler


BuiltinParamSpec = _ParamSpec
BuiltinStrategySupport = _BuiltinStrategySupport
BUNDLE_MARKER_PREFIX = _BUNDLE_MARKER_PREFIX
REPO_ROOT = _REPO_ROOT


__all__ = [
    "BuiltinCompileArtifacts",
    "BuiltinParamSpec",
    "BuiltinStrategySupport",
    "BUNDLE_MARKER_PREFIX",
    "REPO_ROOT",
]
