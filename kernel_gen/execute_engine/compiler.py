"""ExecutionEngine compiler implementation.


功能说明:
- 承接执行引擎的编译命令生成、target include 注入、entry shim 构造与 `ExecutionEngine` 编译/执行入口实现。
- 统一 target include、entry shim 与执行引擎编译/执行内部职责，避免 execute_engine 下多个无独立公开边界的实现文件。
- `kernel_gen.execute_engine` 包入口继续重导出执行引擎公开 API；target/compile/shim 细节仅作为本文件内部实现。

API 列表:
- `class CompileRequest(source: str, target: str, function: str, entry_point: str = "kg_execute_entry", compiler: str | None = None, compiler_flags: tuple[str, ...] = ("-std=c++17",), link_flags: tuple[str, ...] = ())`
- `class ExecuteRequest(args: tuple[RuntimeInput, ...], entry_point: str | None = None, capture_function_output: bool = False, stream: None = None)`
- `class ExecuteResult(ok: bool, status_code: int, failure_phrase: str | None, compile_stdout: str = "", compile_stderr: str = "", run_stdout: str = "", run_stderr: str = "", elapsed_ms: float = 0.0)`
- `class CompiledKernel(target: str, soname_path: str, function: str, entry_point: str, compile_stdout: str = "", compile_stderr: str = "")`
- `CompiledKernel.close() -> None`
- `CompiledKernel.execute(args: tuple[RuntimeInput, ...] | None = None, *, request: ExecuteRequest | None = None, entry_point: str | None = None, capture_function_output: bool = False, stream: None = None) -> ExecuteResult`
- `class ExecutionEngine(target: str, compiler: str | None = None, compiler_flags: tuple[str, ...] = ("-std=c++17",), link_flags: tuple[str, ...] = ())`
- `ExecutionEngine.compile(source: str | None = None, function: str | None = None, *, request: CompileRequest | None = None, entry_point: str = "kg_execute_entry") -> CompiledKernel`

helper 清单:
- 私有 helper 仅限本文件内部使用，不作为跨文件调用边界。

使用示例:
- from kernel_gen.execute_engine import ExecutionEngine, ExecuteRequest
- engine = ExecutionEngine(target="cpu")
- kernel = engine.compile(source="int main(){}", function="cpu::add")
- result = kernel.execute(request=ExecuteRequest(args=(1, 2.0)))

关联文件:
- spec: spec/execute_engine/execute_engine.md
- spec: spec/execute_engine/execute_engine_api.md
- spec: spec/execute_engine/execute_engine_target.md
- test: test/execute_engine/test_contract.py
- test: test/execute_engine/test_compile.py
- test: test/execute_engine/test_invoke.py
- 功能实现: kernel_gen/execute_engine/compiler.py
"""

from __future__ import annotations

from collections.abc import Iterable
import ctypes
from dataclasses import dataclass, field
from functools import partial
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
from typing import Callable, Literal, Protocol, TypeAlias

from kernel_gen.core.error import ErrorKind, ErrorModule, KernelCodeError

_COMPILER_ICE_MARKERS = (
    "internal compiler error",
    "Please submit a full bug report",
)


def _join_text_sections(*sections: str) -> str:
    """把多段源码文本按空行拼接。


    功能说明:
    - 过滤空字符串段，并统一去掉每段尾部空白。
    - 以空行分隔段落，保持编译单元源码的稳定换行口径。
    - 结果始终以单个换行结束。

    使用示例:
    - source = _join_text_sections("#include <a>", "int main() {}")

    关联文件:
    - spec: spec/execute_engine/execute_engine_target.md
    - test: test/execute_engine/test_compile.py
    - 功能实现: kernel_gen/execute_engine/compiler.py
    """

    normalized_sections = tuple(section.rstrip() for section in sections if section)
    if not normalized_sections:
        return "\n"
    return "\n\n".join(normalized_sections).rstrip() + "\n"


def _looks_like_internal_compiler_error(stderr: str) -> bool:
    """判断编译 stderr 是否命中编译器内部错误特征。


    功能说明:
    - 统一识别 GCC/Clang 常见的 internal compiler error 文本。
    - 供真实编译路径决定是否追加一次同命令重试，减少编译器偶发异常对回归结果的干扰。

    使用示例:
    - assert _looks_like_internal_compiler_error("internal compiler error: ...") is True

    关联文件:
    - spec: spec/execute_engine/execute_engine_target.md
    - test: test/execute_engine/test_compile.py
    - 功能实现: kernel_gen/execute_engine/compiler.py
    """

    if not isinstance(stderr, str):
        return False
    return any(marker in stderr for marker in _COMPILER_ICE_MARKERS)


def _run_compiler_command(command: Iterable[str]) -> subprocess.CompletedProcess[str]:
    """运行编译命令，并在编译器内部异常时追加一次重试。


    功能说明:
    - 统一真实编译路径的命令执行与 stderr 判定逻辑。
    - 当 stderr 命中编译器内部异常文本时，仅对同一命令追加一次重试。
    - 让执行引擎与本地编译回归测试复用同一控制流，避免两处维护不同分支。

    使用示例:
    - result = _run_compiler_command(["g++", "-std=c++17", "demo.cpp", "-o", "demo"])

    关联文件:
    - spec: spec/execute_engine/execute_engine_target.md
    - test: test/execute_engine/test_compile.py
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


def _compiler_default() -> str:
    """返回 P0 默认编译器名。


    功能说明:
    - 以固定值返回执行引擎 P0 的默认编译器名，用于生成可复现的编译命令骨架。

    使用示例:
    - assert _compiler_default() == "g++"

    关联文件:
    - spec: spec/execute_engine/execute_engine_target.md
    - test: test/execute_engine/test_contract.py
    - 功能实现: kernel_gen/execute_engine/compiler.py
    """

    return "g++"


@dataclass(frozen=True)
class _CompileResult:
    """编译产物描述（P0/S2）。


    功能说明:
    - 统一承载编译命令、产物路径与 stdout/stderr，便于测试与记录。
    - 当编译器内部创建临时工作目录时，会附带私有 cleanup 句柄，用于由上层在合适时机释放。

    使用示例:
    - artifacts = _CompileResult(
        soname_path="libkernel.so",
        source_path="kernel.cpp",
        command=("g++",),
        stdout="",
        stderr="",
        return_code=0,
      )

    关联文件:
    - spec: spec/execute_engine/execute_engine_target.md
    - test: test/execute_engine/test_compile.py
    - 功能实现: kernel_gen/execute_engine/compiler.py
    """

    soname_path: str
    source_path: str
    command: tuple[str, ...]
    stdout: str
    stderr: str
    return_code: int
    _cleanup: Callable[[], None] | None = field(default=None, repr=False, compare=False)


def _compose_compile_unit(
    *,
    source: str,
    _include_lines_for_target: tuple[str, ...],
    entry_shim_source: str,
) -> str:
    """拼接最终编译单元源码。


    功能说明:
    - 以 target include set + 原始 source + entry shim 的顺序拼接编译单元。
    - 若 source 已含部分 target include，则仅补齐缺失项。

    使用示例:
    - unit = _compose_compile_unit(
        source="int main(){}",
        _include_lines_for_target=('#include \"include/cpu/Memory.h\"',),
        entry_shim_source="// shim",
      )

    关联文件:
    - spec: spec/execute_engine/execute_engine_target.md
    - test: test/execute_engine/test_compile.py
    - 功能实现: kernel_gen/execute_engine/compiler.py
    """

    missing_includes = tuple(line for line in _include_lines_for_target if line not in source)
    sections: list[str] = []
    if missing_includes:
        sections.append("\n".join(missing_includes))
    sections.append(source.rstrip())
    if entry_shim_source:
        sections.append(entry_shim_source.rstrip())
    return _join_text_sections(*sections)


def _compose_compile_command(
    *,
    compiler: str,
    source_path: str,
    output_path: str,
    compiler_flags: Iterable[str],
    link_flags: Iterable[str],
    include_dirs: Iterable[str],
) -> tuple[str, ...]:
    """生成编译命令（P0/S2）。


    功能说明:
    - 按固定顺序拼装编译命令：compiler + flags + include dirs + source + -o output + link_flags。
    - 默认生成可共享库产物（-shared -fPIC），便于后续执行阶段载入。

    使用示例:
    - cmd = _compose_compile_command(
        compiler="g++",
        source_path="kernel.cpp",
        output_path="libkernel.so",
        compiler_flags=("-std=c++17",),
        link_flags=(),
        include_dirs=(".",),
      )

    关联文件:
    - spec: spec/execute_engine/execute_engine_target.md
    - test: test/execute_engine/test_compile.py
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


def _compile_unit_source(
    *,
    source: str,
    compiler: str,
    compiler_flags: tuple[str, ...],
    link_flags: tuple[str, ...],
    include_dirs: tuple[str, ...],
    work_dir: Path | None = None,
    dry_run: bool = True,
) -> _CompileResult:
    """执行或模拟编译流程。


    功能说明:
    - 将编译单元写入工作目录，生成编译命令并执行或 dry-run。
    - dry_run 模式下仅创建产物占位文件并返回命令，避免依赖真实编译器环境。
    - 若内部自动创建临时工作目录，则通过返回值携带 cleanup 句柄，由上层在 close / 失败分支释放。

    使用示例:
    - artifacts = _compile_unit_source(
        source="int main(){}",
        compiler="g++",
        compiler_flags=("-std=c++17",),
        link_flags=(),
        include_dirs=(".",),
        dry_run=True,
      )

    关联文件:
    - spec: spec/execute_engine/execute_engine_target.md
    - test: test/execute_engine/test_compile.py
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
        command = _compose_compile_command(
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
            return _CompileResult(
                soname_path=str(soname_path),
                source_path=str(source_path),
                command=command,
                stdout=stdout,
                stderr="",
                return_code=0,
                _cleanup=cleanup,
            )

        result = _run_compiler_command(command)
        return _CompileResult(
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


def _include_lines_for_target(target: str) -> tuple[str, ...]:
    """返回 target 对应的 include set（P0 合同）。


    功能说明:
    - 返回执行引擎 P0 的 target->include family 映射，用于后续阶段把 include 注入到编译单元中。
    - S1 阶段只保证映射规则存在且可被测试机械检查，不负责解析源码中的 include。

    使用示例:
    - assert _include_lines_for_target("npu_demo") == ('#include "include/npu_demo/npu_demo.h"',)
    - assert '#include "include/cpu/Memory.h"' in _include_lines_for_target("cpu")

    关联文件:
    - spec: spec/execute_engine/execute_engine_target.md
    - test: test/execute_engine/test_contract.py
    - 功能实现: kernel_gen/execute_engine/compiler.py
    """

    if target == "npu_demo":
        return ('#include "include/npu_demo/npu_demo.h"',)
    if target == "cpu":
        return (
            '#include "include/cpu/Memory.h"',
            '#include "include/cpu/Nn.h"',
        )
    return ()


@dataclass(frozen=True)
class _ParamSpec:
    """函数形参的最小描述。


    功能说明:
    - 描述 entry shim 绑定所需的参数类别与类型信息。
    - 仅在本模块内部使用，不对外暴露。

    使用示例:
    - spec = _ParamSpec(kind="memory", ctype="int32_t", memory_space="GM")

    关联文件:
    - spec: spec/execute_engine/execute_engine_target.md
    - test: test/execute_engine/test_compile.py
    - 功能实现: kernel_gen/execute_engine/compiler.py
    """

    kind: str
    ctype: str
    memory_space: str | None = None


_INT_TYPE_PATTERN = re.compile(
    r"^(?:const\s+)?(?P<type>"
    r"S_INT|int|short|long|long\s+long|"
    r"unsigned\s+int|unsigned\s+long|unsigned\s+long\s+long|"
    r"int32_t|int64_t|uint32_t|uint64_t|size_t"
    r")(?:\s*&)?\s+\w+$"
)
_FLOAT_TYPE_PATTERN = re.compile(
    r"^(?:const\s+)?(?P<type>float|double)(?:\s*&)?\s+\w+$"
)
_KERNEL_CONTEXT_TYPE_PATTERN = re.compile(r"^(?:npu_demo::)?KernelContext\s*&\s+\w+$")
_MEMORY_TYPE_PATTERN = re.compile(
    r"^(?:const\s+)?Memory<\s*(?P<space>[^,\s>]+)\s*,\s*(?P<dtype>[^>\s]+)\s*>\s*&\s+\w+$"
)


def _split_params(params_text: str) -> tuple[str, ...]:
    """按顶层逗号切分函数形参。


    功能说明:
    - 对带模板参数的函数形参进行稳定切分。
    - 忽略 `<...>`、`(...)`、`[...]` 内部逗号，避免误拆。

    使用示例:
    - _split_params("Memory<GM, int32_t>& out, const Memory<GM, int32_t>& lhs")

    关联文件:
    - spec: spec/execute_engine/execute_engine_target.md
    - test: test/execute_engine/test_compile.py
    - 功能实现: kernel_gen/execute_engine/compiler.py
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


def _parse_param_spec(param_text: str) -> _ParamSpec | None:
    """把单个形参文本解析为最小参数规格。


    功能说明:
    - 支持 `Memory<Space, T>&`、整型标量、浮点标量三类参数。
    - 不支持的参数形态返回 `None`，由上层回退占位 shim。

    使用示例:
    - _parse_param_spec("const Memory<GM, int32_t>& lhs")

    关联文件:
    - spec: spec/execute_engine/execute_engine_target.md
    - test: test/execute_engine/test_compile.py
    - 功能实现: kernel_gen/execute_engine/compiler.py
    """

    normalized = " ".join(param_text.strip().split())
    memory_match = _MEMORY_TYPE_PATTERN.match(normalized)
    if memory_match is not None:
        return _ParamSpec(
            kind="memory",
            ctype=memory_match.group("dtype"),
            memory_space=memory_match.group("space"),
        )
    int_match = _INT_TYPE_PATTERN.match(normalized)
    if int_match is not None:
        return _ParamSpec(kind="int", ctype=int_match.group("type"))
    float_match = _FLOAT_TYPE_PATTERN.match(normalized)
    if float_match is not None:
        return _ParamSpec(kind="float", ctype=float_match.group("type"))
    if _KERNEL_CONTEXT_TYPE_PATTERN.match(normalized):
        return _ParamSpec(kind="kernel_context", ctype="npu_demo::KernelContext")
    return None


def _extract_param_specs(source: str, function: str) -> tuple[_ParamSpec, ...] | None:
    """从源码中提取 function 定义对应的参数规格。


    功能说明:
    - 在源码中查找目标函数定义并解析参数。
    - 同时尝试完整名称与短名（去命名空间）匹配。

    使用示例:
    - _extract_param_specs("void add_kernel(...)", "add_kernel")

    关联文件:
    - spec: spec/execute_engine/execute_engine_target.md
    - test: test/execute_engine/test_compile.py
    - 功能实现: kernel_gen/execute_engine/compiler.py
    """

    candidates = [function]
    short_name = function.split("::")[-1]
    if short_name not in candidates:
        candidates.append(short_name)

    for function_name in candidates:
        pattern = re.compile(
            rf"\b{re.escape(function_name)}\s*\((?P<params>.*?)\)\s*\{{",
            re.DOTALL,
        )
        for match in pattern.finditer(source):
            params = _split_params(match.group("params"))
            specs: list[_ParamSpec] = []
            for param in params:
                spec = _parse_param_spec(param)
                if spec is None:
                    specs = []
                    break
                specs.append(spec)
            if specs or not params:
                return tuple(specs)
    return None


def _build_runtime_entry_shim_source(
    *,
    function: str,
    entry_point: str,
    params: tuple[_ParamSpec, ...],
) -> str:
    """根据参数规格生成可运行 entry shim。


    功能说明:
    - 生成稳定的 C ABI 入口：`extern "C" int <entry_point>(...)`。
    - 把 `ordered_args` 映射为函数形参并执行真实调用；若首参是 `npu_demo::KernelContext&`，
      则自动构造默认上下文并把它作为第一个实参传入 body。

    使用示例:
    - _build_runtime_entry_shim_source(function="add_kernel", entry_point="kg_execute_entry", params=(...))

    关联文件:
    - spec: spec/execute_engine/execute_engine_target.md
    - test: test/execute_engine/test_compile.py
    - 功能实现: kernel_gen/execute_engine/compiler.py
    """

    runtime_params = [spec for spec in params if spec.kind != "kernel_context"]
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
    ]
    call_args: list[str] = []
    runtime_arg_index = 0
    for spec in params:
        if spec.kind == "kernel_context":
            lines.append("  npu_demo::KernelContext ctx;")
            call_args.append("ctx")
            continue
        runtime_idx = runtime_arg_index
        runtime_arg_index += 1
        if spec.kind == "memory":
            lines.extend(
                [
                    f"  if (ordered_args[{runtime_idx}].kind != KG_ARG_MEMORY) {{",
                    "    return -1;",
                    "  }",
                    f"  if (ordered_args[{runtime_idx}].data == nullptr || ordered_args[{runtime_idx}].shape == nullptr || ordered_args[{runtime_idx}].stride == nullptr) {{",
                    "    return -1;",
                    "  }",
                    f"  Memory<{spec.memory_space}, {spec.ctype}> arg{runtime_idx}(",
                    f"      reinterpret_cast<{spec.ctype}*>(ordered_args[{runtime_idx}].data),",
                    f"      ordered_args[{runtime_idx}].shape,",
                    f"      ordered_args[{runtime_idx}].stride,",
                    f"      ordered_args[{runtime_idx}].rank);",
                ]
            )
            call_args.append(f"arg{runtime_idx}")
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
    call_args_text = ", ".join(call_args)
    lines.extend(
        [
            f"  {function}({call_args_text});",
            "  return 0;",
            "}",
            "",
        ]
    )
    return _join_text_sections("\n".join(lines))


def _requires_entry_shim(source: str, entry_point: str) -> bool:
    """判断是否需要生成 entry shim。


    功能说明:
    - 当源码未显式提供 `extern "C"` 且同名入口时，返回 True。
    - 用于避免重复生成已存在的稳定入口。

    使用示例:
    - assert _requires_entry_shim('extern "C" int kg_execute_entry(...) { return 0; }', "kg_execute_entry") is False

    关联文件:
    - spec: spec/execute_engine/execute_engine_target.md
    - test: test/execute_engine/test_compile.py
    - 功能实现: kernel_gen/execute_engine/compiler.py
    """

    if not isinstance(source, str) or not isinstance(entry_point, str):
        return True
    pattern = rf'extern\s+"C"\s+[^;{{]*\b{re.escape(entry_point)}\b'
    return re.search(pattern, source) is None


def _compose_entry_shim_source(*, function: str, entry_point: str, source: str | None = None) -> str:
    """构造 entry shim 源码片段。


    功能说明:
    - 可解析参数时生成真实参数绑定 shim，用于 `ExecutionEngine.execute` 的真实调用。
    - body 函数若以 `npu_demo::KernelContext&` 作为首参，会被桥接为默认构造上下文 + 真实 runtime 参数。
    - 参数不可解析时回退最小占位 shim，保持历史编译路径兼容。

    使用示例:
    - src = _compose_entry_shim_source(function="cpu::add", entry_point="kg_execute_entry", source="void add(){}")

    关联文件:
    - spec: spec/execute_engine/execute_engine_target.md
    - test: test/execute_engine/test_compile.py
    - 功能实现: kernel_gen/execute_engine/compiler.py
    """

    if isinstance(source, str) and source.strip():
        params = _extract_param_specs(source, function)
        if params is not None:
            return _build_runtime_entry_shim_source(
                function=function,
                entry_point=entry_point,
                params=params,
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

_TARGET_HEADER_MISMATCH = "target_header_mismatch"
_SOURCE_EMPTY_OR_INVALID = "source_empty_or_invalid"
_COMPILE_FAILED = "compile_failed"
_SYMBOL_RESOLVE_FAILED = "symbol_resolve_failed"
_RUNTIME_THROW_OR_ABORT = "runtime_throw_or_abort"
_STREAM_NOT_SUPPORTED = "stream_not_supported"
_FUNCTION_OUTPUT_CAPTURE_NOT_SUPPORTED = "function_output_capture_not_supported"

_KNOWN_ERROR_PHRASES: frozenset[str] = frozenset(
    {
        _TARGET_HEADER_MISMATCH,
        _SOURCE_EMPTY_OR_INVALID,
        _COMPILE_FAILED,
        _SYMBOL_RESOLVE_FAILED,
        _RUNTIME_THROW_OR_ABORT,
        _STREAM_NOT_SUPPORTED,
        _FUNCTION_OUTPUT_CAPTURE_NOT_SUPPORTED,
    }
)



class _StringValue(Protocol):
    """可稳定转为字符串的运行期值。"""

    def __str__(self) -> str:
        """返回字符串表示。"""


class _MemoryRuntimeInput(Protocol):
    """执行引擎支持的最小 memory runtime 参数协议。"""

    shape: Iterable[int]
    dtype: _StringValue


RuntimeInput: TypeAlias = "_MemoryRuntimeInput | int | float"
_RuntimeInputValue: TypeAlias = "RuntimeInput | _StringValue | None"


class _LoadedEntrySymbol(Protocol):
    """ctypes 动态库入口 symbol 的最小调用协议。"""

    argtypes: list[type]
    restype: type[ctypes.c_int]

    def __call__(self, slots: ctypes.Array, count: ctypes.c_ulonglong) -> int:
        """调用 C ABI entry symbol。"""


def _execution_engine_error(failure_phrase: str, detail: str = "") -> KernelCodeError:
    """构造执行引擎统一错误对象。

    创建者: OpenAI Codex
    最后一次更改: 大闸蟹

    功能说明:
    - 用 `KernelCodeError` 承载 execute_engine 的固定 `failure_phrase`。
    - 不通过 `KernelCodeError` 构造参数传递 metadata；固定短语由本 helper 在对象创建后写入。

    使用示例:
    - err = _execution_engine_error(_COMPILE_FAILED, "compiler is empty")
    - assert err.module() == "execute_engine"

    关联文件:
    - spec: spec/execute_engine/execute_engine_api.md
    - test: test/execute_engine/test_contract.py
    - 功能实现: kernel_gen/execute_engine/compiler.py
    """

    if failure_phrase not in _KNOWN_ERROR_PHRASES:
        raise KernelCodeError(
            ErrorKind.CONTRACT,
            ErrorModule.EXECUTE_ENGINE,
            f"unknown failure phrase: {failure_phrase}",
        )
    message = failure_phrase if not detail else f"{failure_phrase}: {detail}"
    error = KernelCodeError(
        ErrorKind.CONTRACT,
        ErrorModule.EXECUTE_ENGINE,
        message,
    )
    error.failure_phrase = failure_phrase
    return error


def _source_include_family(source: str) -> str | None:
    """从 source 粗略推断 include family。


    功能说明:
    - 用于在不执行真实编译的前提下，对 `target` 与源码 include family 的一致性进行最小校验。
    - 只识别仓库内约定路径片段：`include/cpu/` 与 `include/npu_demo/`。

    使用示例:
    - assert _source_include_family('#include \"include/cpu/Memory.h\"') == \"cpu\"

    关联文件:
    - spec: spec/execute_engine/execute_engine_target.md
    - test: test/execute_engine/test_compile.py
    - 功能实现: kernel_gen/execute_engine/compiler.py
    """

    has_cpu = "include/cpu/" in source
    has_npu = "include/npu_demo/" in source
    if has_cpu and has_npu:
        return "mixed"
    if has_cpu:
        return "cpu"
    if has_npu:
        return "npu_demo"
    return None


def _inject_npu_demo_namespace_aliases(source: str) -> str:
    """为 `npu_demo::foo` 生成最小命名空间别名，兼容全局实现。


    功能说明:
    - 识别源码中的 `npu_demo::` 调用，并注入 `namespace npu_demo { using ::foo; }` 别名。
    - 解决 `emit_c` 使用命名空间调用、但头文件只提供全局符号时的真实编译失败。

    使用示例:
    - _inject_npu_demo_namespace_aliases('#include "include/npu_demo/npu_demo.h"\\nvoid f(){ npu_demo::add(a,b,c); }')

    关联文件:
    - spec: spec/execute_engine/execute_engine_target.md
    - test: test/execute_engine/test_compile.py
    - 功能实现: kernel_gen/execute_engine/compiler.py
    """

    symbols = sorted(set(re.findall(r"npu_demo::([A-Za-z_]\w*)\s*\(", source)))
    if not symbols:
        return source
    alias_lines = ["namespace npu_demo {"]
    alias_lines.extend(f"using ::{symbol};" for symbol in symbols)
    alias_lines.append("}")
    alias_block = "\n".join(alias_lines) + "\n"
    include_match = re.match(r"((?:\s*#include[^\n]*\n)+)", source)
    if include_match is not None:
        return f"{source[:include_match.end()]}\n{alias_block}{source[include_match.end():]}"
    return f"{alias_block}\n{source}"


REPO_ROOT = Path(__file__).resolve().parents[2]


def _ensure_compiler_flags(flags: tuple[str, ...]) -> tuple[str, ...]:
    """确保编译 flags 包含 -std=c++17 基线。


    功能说明:
    - 若调用方未提供 `-std=c++17`，则按基线规则补齐。
    - 其余 flags 保持原有顺序。

    使用示例:
    - assert _ensure_compiler_flags(("-O2",)) == ("-std=c++17", "-O2")

    关联文件:
    - spec: spec/execute_engine/execute_engine_target.md
    - test: test/execute_engine/test_compile.py
    - 功能实现: kernel_gen/execute_engine/compiler.py
    """

    if "-std=c++17" in flags:
        return flags
    return ("-std=c++17", *flags)


def _resolve_compiler_name(compiler: str | None) -> str:
    """解析编译器名称（P0/S2）。


    功能说明:
    - 当 compiler 为空时回退到默认编译器。
    - 若 compiler 为空字符串或非字符串，则视为无效输入。

    使用示例:
    - assert _resolve_compiler_name(None) == "g++"

    关联文件:
    - spec: spec/execute_engine/execute_engine_target.md
    - test: test/execute_engine/test_compile.py
    - 功能实现: kernel_gen/execute_engine/compiler.py
    """

    if compiler is None:
        return _compiler_default()
    if not isinstance(compiler, str) or not compiler.strip():
        raise _execution_engine_error(
            _COMPILE_FAILED,
            "compiler is empty",
        )
    return compiler




@dataclass(frozen=True)
class CompileRequest:
    """编译请求模型（P0）。"""

    source: str
    target: str
    function: str
    entry_point: str = "kg_execute_entry"
    compiler: str | None = None
    compiler_flags: tuple[str, ...] = ("-std=c++17",)
    link_flags: tuple[str, ...] = ()


@dataclass(frozen=True)
class ExecuteRequest:
    """执行请求模型（P0）。"""

    args: tuple[RuntimeInput, ...]
    entry_point: str | None = None
    capture_function_output: bool = False
    stream: None = None


@dataclass(frozen=True)
class _ArgSlot:
    """entry shim 绑定槽位（P0/S3）。


    功能说明:
    - 承载 entry shim 的按位参数信息，用于在 Python 侧完成 P0/S3 的顺序绑定校验。
    - 仅用于参数绑定与校验，不承担执行结果与内存拷贝。

    使用示例:
    - slot = _ArgSlot(position=0, kind="memory", dtype="float32", shape=(2, 2), stride=None, value=tensor)

    关联文件:
    - spec: spec/execute_engine/execute_engine_api.md
    - test: test/execute_engine/test_invoke.py
    - 功能实现: kernel_gen/execute_engine/compiler.py
    """

    position: int
    kind: Literal["memory", "int", "float"]
    dtype: str | None
    shape: tuple[int, ...] | None
    stride: tuple[int, ...] | None
    value: RuntimeInput


def _normalize_dtype(value: _StringValue | None) -> str | None:
    """规范化 dtype 表达。


    功能说明:
    - 统一 dtype 的字符串格式，支持 str、numpy/torch 的 dtype 对象。
    - 仅做最小规范化（去除 torch. 前缀），不做类型映射。

    使用示例:
    - assert _normalize_dtype("float32") == "float32"

    关联文件:
    - spec: spec/execute_engine/execute_engine_api.md
    - test: test/execute_engine/test_invoke.py
    - 功能实现: kernel_gen/execute_engine/compiler.py
    """

    if value is None:
        return None
    if isinstance(value, str):
        dtype_str = value
    else:
        dtype_str = str(value)
    dtype_str = dtype_str.strip()
    if not dtype_str:
        return None
    if dtype_str.startswith("torch."):
        dtype_str = dtype_str.split(".", 1)[1]
    return dtype_str


def _normalize_shape(value: _MemoryRuntimeInput | None) -> tuple[int, ...] | None:
    """规范化 shape 表达。


    功能说明:
    - 统一 shape 为 tuple[int, ...]，用于 运行时参数的 memory 校验。
    - shape 不可解析时返回 None。

    使用示例:
    - assert _normalize_shape(type("T", (), {"shape": (2, 3)})()) == (2, 3)

    关联文件:
    - spec: spec/execute_engine/execute_engine_api.md
    - test: test/execute_engine/test_invoke.py
    - 功能实现: kernel_gen/execute_engine/compiler.py
    """

    if value is None or not hasattr(value, "shape"):
        return None
    try:
        return tuple(int(dim) for dim in getattr(value, "shape"))
    except TypeError:
        return None


def _normalize_stride(value: _MemoryRuntimeInput | None) -> tuple[int, ...] | None:
    """规范化 stride 表达。


    功能说明:
    - 统一 stride 为 tuple[int, ...]，用于 运行时参数的 memory 校验与记录。
    - stride 不可解析时返回 None。

    使用示例:
    - assert _normalize_stride(type("T", (), {"stride": lambda self: (1, 2)})()) == (1, 2)

    关联文件:
    - spec: spec/execute_engine/execute_engine_api.md
    - test: test/execute_engine/test_invoke.py
    - 功能实现: kernel_gen/execute_engine/compiler.py
    """

    if value is None:
        return None
    if hasattr(value, "stride"):
        stride_attr = getattr(value, "stride")
        stride = stride_attr() if callable(stride_attr) else stride_attr
        try:
            return tuple(int(dim) for dim in stride)
        except TypeError:
            return None
    if hasattr(value, "strides"):
        stride = getattr(value, "strides")
        try:
            stride_tuple = tuple(int(dim) for dim in stride)
        except TypeError:
            return None
        if _is_numpy_array(value):
            itemsize = getattr(value, "itemsize", None)
            if not isinstance(itemsize, int) or itemsize <= 0:
                return None
            if any(dim % itemsize != 0 for dim in stride_tuple):
                return None
            return tuple(int(dim // itemsize) for dim in stride_tuple)
        return stride_tuple
    return None


def _runtime_module_name(value: _RuntimeInputValue) -> str:
    """提取 运行时参数的模块前缀。


    功能说明:
    - 为 torch/numpy 类型识别提供最小、无需导入依赖的判断依据。
    - 返回空字符串表示无法识别模块信息。

    使用示例:
    - assert _runtime_module_name(type("T", (), {"__module__": "torch"})()) == "torch"

    关联文件:
    - spec: spec/execute_engine/execute_engine_api.md
    - test: test/execute_engine/test_invoke.py
    - 功能实现: kernel_gen/execute_engine/compiler.py
    """

    module_name = getattr(value.__class__, "__module__", "")
    return module_name or ""


def _is_torch_tensor(value: _RuntimeInputValue) -> bool:
    """判断是否为 torch 张量类 _RuntimeInput。


    功能说明:
    - 基于 __module__ 前缀做轻量识别，避免直接导入 torch 依赖。
    - 仅用于 运行时参数类型判定，不做数据合法性校验。

    使用示例:
    - assert _is_torch_tensor(type("T", (), {"__module__": "torch"})()) is True

    关联文件:
    - spec: spec/execute_engine/execute_engine_api.md
    - test: test/execute_engine/test_invoke.py
    - 功能实现: kernel_gen/execute_engine/compiler.py
    """

    return _runtime_module_name(value).startswith("torch")


def _is_numpy_array(value: _RuntimeInputValue) -> bool:
    """判断是否为 numpy 数组类 _RuntimeInput。


    功能说明:
    - 基于 __module__ 前缀做轻量识别，避免直接导入 numpy 依赖。
    - 仅用于 运行时参数类型判定，不做数据合法性校验。

    使用示例:
    - assert _is_numpy_array(type("T", (), {"__module__": "numpy"})()) is True

    关联文件:
    - spec: spec/execute_engine/execute_engine_api.md
    - test: test/execute_engine/test_invoke.py
    - 功能实现: kernel_gen/execute_engine/compiler.py
    """

    return _runtime_module_name(value).startswith("numpy")


def _is_runtime_int(value: _RuntimeInputValue) -> bool:
    """判断是否为合法 int _RuntimeInput（排除 bool）。


    功能说明:
    - 允许 int 作为 运行时参数的标量输入。
    - 显式排除 bool，避免把布尔值误判为整数。

    使用示例:
    - assert _is_runtime_int(3) is True
    - assert _is_runtime_int(True) is False

    关联文件:
    - spec: spec/execute_engine/execute_engine_api.md
    - test: test/execute_engine/test_invoke.py
    - 功能实现: kernel_gen/execute_engine/compiler.py
    """

    return isinstance(value, int) and not isinstance(value, bool)


def _is_runtime_float(value: _RuntimeInputValue) -> bool:
    """判断是否为合法 float _RuntimeInput（排除 bool）。


    功能说明:
    - 允许 float 作为 运行时参数的标量输入。
    - 显式排除 bool，确保失败路径可控。

    使用示例:
    - assert _is_runtime_float(1.25) is True
    - assert _is_runtime_float(False) is False

    关联文件:
    - spec: spec/execute_engine/execute_engine_api.md
    - test: test/execute_engine/test_invoke.py
    - 功能实现: kernel_gen/execute_engine/compiler.py
    """

    return isinstance(value, float) and not isinstance(value, bool)


def _is_memory_runtime_arg(value: _RuntimeInputValue) -> bool:
    """判断是否为 memory 运行时参数（torch/numpy）。


    功能说明:
    - 仅当对象符合 torch/numpy 模块前缀且包含 shape/dtype 字段时视为 memory 参数。
    - 不对 shape/dtype 的合法性做复杂推断，留给后续校验逻辑处理。

    使用示例:
    - value = type("T", (), {"__module__": "torch", "shape": (1,), "dtype": "float32"})()
    - assert _is_memory_runtime_arg(value) is True

    关联文件:
    - spec: spec/execute_engine/execute_engine_api.md
    - test: test/execute_engine/test_invoke.py
    - 功能实现: kernel_gen/execute_engine/compiler.py
    """

    if not (_is_torch_tensor(value) or _is_numpy_array(value)):
        return False
    return hasattr(value, "shape") and hasattr(value, "dtype")


def _is_contiguous_memory(value: _MemoryRuntimeInput) -> bool:
    """判断 memory 运行时参数 是否为连续布局。


    功能说明:
    - torch 路径优先使用 is_contiguous() 结果。
    - numpy 路径优先读取 flags["C_CONTIGUOUS"] 或 flags.c_contiguous。
    - 缺少相关信息时默认视为连续布局。

    使用示例:
    - value = type("T", (), {"__module__": "torch", "shape": (1,), "dtype": "float32", "is_contiguous": lambda self: True})()
    - assert _is_contiguous_memory(value) is True

    关联文件:
    - spec: spec/execute_engine/execute_engine_api.md
    - test: test/execute_engine/test_invoke.py
    - 功能实现: kernel_gen/execute_engine/compiler.py
    """

    if hasattr(value, "is_contiguous"):
        try:
            return bool(value.is_contiguous())
        except Exception:
            return False
    if hasattr(value, "flags"):
        flags = value.flags
        if isinstance(flags, dict) and "C_CONTIGUOUS" in flags:
            return bool(flags["C_CONTIGUOUS"])
        if hasattr(flags, "c_contiguous"):
            return bool(flags.c_contiguous)
    return True


def _build_arg_slots(args: tuple[RuntimeInput, ...]) -> tuple[_ArgSlot, ...]:
    """按顺序构建 entry shim 参数槽位。


    功能说明:
    - 校验 _RuntimeInput 的类型与最小 memory 约束（shape/dtype/连续性）。
    - 失败时抛出 runtime_throw_or_abort，保证失败短语稳定。

    使用示例:
    - slots = _build_arg_slots((1, 2.0))

    关联文件:
    - spec: spec/execute_engine/execute_engine_api.md
    - test: test/execute_engine/test_invoke.py
    - 功能实现: kernel_gen/execute_engine/compiler.py
    """

    slots: list[_ArgSlot] = []
    for idx, arg in enumerate(args):
        if _is_runtime_int(arg):
            slots.append(
                _ArgSlot(
                    position=idx,
                    kind="int",
                    dtype="int",
                    shape=None,
                    stride=None,
                    value=arg,
                )
            )
            continue
        if _is_runtime_float(arg):
            slots.append(
                _ArgSlot(
                    position=idx,
                    kind="float",
                    dtype="float",
                    shape=None,
                    stride=None,
                    value=arg,
                )
            )
            continue
        if _is_memory_runtime_arg(arg):
            if not _is_contiguous_memory(arg):
                raise _execution_engine_error(
                    _RUNTIME_THROW_OR_ABORT,
                    f"memory arg is not contiguous at position {idx}",
                )
            dtype = _normalize_dtype(getattr(arg, "dtype", None))
            shape = _normalize_shape(arg)
            if dtype is None or shape is None:
                raise _execution_engine_error(
                    _RUNTIME_THROW_OR_ABORT,
                    f"memory arg missing dtype/shape at position {idx}",
                )
            slots.append(
                _ArgSlot(
                    position=idx,
                    kind="memory",
                    dtype=dtype,
                    shape=shape,
                    stride=_normalize_stride(arg),
                    value=arg,
                )
            )
            continue
        raise _execution_engine_error(
            _RUNTIME_THROW_OR_ABORT,
            f"unsupported runtime arg at position {idx}",
        )
    return tuple(slots)


def _contiguous_stride(shape: tuple[int, ...]) -> tuple[int, ...]:
    """按 shape 生成连续布局 stride（元素步长）。


    功能说明:
    - 当运行时参数未显式提供 stride 时，生成行主序连续 stride。
    - 用于 memory 参数 ABI 封送前的兜底补全。

    使用示例:
    - _contiguous_stride((2, 3)) == (3, 1)

    关联文件:
    - spec: spec/execute_engine/execute_engine_api.md
    - test: test/execute_engine/test_invoke.py
    - 功能实现: kernel_gen/execute_engine/compiler.py
    """

    if not shape:
        return ()
    stride = [1 for _ in shape]
    for idx in range(len(shape) - 2, -1, -1):
        stride[idx] = stride[idx + 1] * int(shape[idx + 1])
    return tuple(stride)


def _runtime_data_pointer(value: _MemoryRuntimeInput) -> int:
    """读取运行时参数底层数据指针地址。


    功能说明:
    - 对 `torch.Tensor` 使用 `data_ptr()`，对 `numpy.ndarray` 使用 `ctypes.data`。
    - 不支持的对象触发 `runtime_throw_or_abort`。

    使用示例:
    - _runtime_data_pointer(torch.zeros((2,), dtype=torch.int32))

    关联文件:
    - spec: spec/execute_engine/execute_engine_api.md
    - test: test/execute_engine/test_invoke.py
    - 功能实现: kernel_gen/execute_engine/compiler.py
    """

    if _is_torch_tensor(value) and hasattr(value, "data_ptr"):
        data_ptr = value.data_ptr()
        return int(data_ptr)
    if _is_numpy_array(value) and hasattr(value, "ctypes"):
        return int(value.ctypes.data)
    raise _execution_engine_error(
        _RUNTIME_THROW_OR_ABORT,
        "memory arg data pointer is unavailable",
    )


def _marshal_slots_for_abi(
    ordered_slots: tuple[_ArgSlot, ...],
) -> tuple[ctypes.Array, type[ctypes.Structure], tuple[ctypes.Array, ...]]:
    """把 Python `_ArgSlot` 转为 C ABI 可调用结构。


    功能说明:
    - 将 memory/int/float 三类运行参数封送为 `_ArgSlot` C 结构数组。
    - 返回 keepalive 对象集合，保证 shape/stride 缓冲区在调用期间有效。

    使用示例:
    - _marshal_slots_for_abi(_build_arg_slots((1, 2.0)))

    关联文件:
    - spec: spec/execute_engine/execute_engine_api.md
    - test: test/execute_engine/test_invoke.py
    - 功能实现: kernel_gen/execute_engine/compiler.py
    """

    class _C_ArgSlot(ctypes.Structure):
        _fields_ = [
            ("kind", ctypes.c_int),
            ("data", ctypes.c_void_p),
            ("shape", ctypes.POINTER(ctypes.c_longlong)),
            ("stride", ctypes.POINTER(ctypes.c_longlong)),
            ("rank", ctypes.c_ulonglong),
            ("int_value", ctypes.c_longlong),
            ("float_value", ctypes.c_double),
        ]

    c_slots: list[_C_ArgSlot] = []
    keepalive: list[ctypes.Array] = []
    for slot in ordered_slots:
        if slot.kind == "memory":
            if slot.shape is None:
                raise _execution_engine_error(
                    _RUNTIME_THROW_OR_ABORT,
                    f"memory shape missing at position {slot.position}",
                )
            stride = slot.stride if slot.stride is not None else _contiguous_stride(slot.shape)
            if len(stride) != len(slot.shape):
                raise _execution_engine_error(
                    _RUNTIME_THROW_OR_ABORT,
                    f"memory stride rank mismatch at position {slot.position}",
                )
            shape_buffer_type = ctypes.c_longlong * len(slot.shape)
            stride_buffer_type = ctypes.c_longlong * len(stride)
            shape_buffer = shape_buffer_type(*slot.shape)
            stride_buffer = stride_buffer_type(*stride)
            keepalive.extend([shape_buffer, stride_buffer])
            c_slots.append(
                _C_ArgSlot(
                    kind=1,
                    data=ctypes.c_void_p(_runtime_data_pointer(slot.value)),
                    shape=ctypes.cast(shape_buffer, ctypes.POINTER(ctypes.c_longlong)),
                    stride=ctypes.cast(stride_buffer, ctypes.POINTER(ctypes.c_longlong)),
                    rank=ctypes.c_ulonglong(len(slot.shape)),
                    int_value=ctypes.c_longlong(0),
                    float_value=ctypes.c_double(0.0),
                )
            )
            continue
        if slot.kind == "int":
            c_slots.append(
                _C_ArgSlot(
                    kind=2,
                    data=ctypes.c_void_p(0),
                    shape=ctypes.POINTER(ctypes.c_longlong)(),
                    stride=ctypes.POINTER(ctypes.c_longlong)(),
                    rank=ctypes.c_ulonglong(0),
                    int_value=ctypes.c_longlong(int(slot.value)),
                    float_value=ctypes.c_double(0.0),
                )
            )
            continue
        if slot.kind == "float":
            c_slots.append(
                _C_ArgSlot(
                    kind=3,
                    data=ctypes.c_void_p(0),
                    shape=ctypes.POINTER(ctypes.c_longlong)(),
                    stride=ctypes.POINTER(ctypes.c_longlong)(),
                    rank=ctypes.c_ulonglong(0),
                    int_value=ctypes.c_longlong(0),
                    float_value=ctypes.c_double(float(slot.value)),
                )
            )
            continue
        raise _execution_engine_error(
            _RUNTIME_THROW_OR_ABORT,
            f"unsupported slot kind at position {slot.position}",
        )
    slot_array_type = _C_ArgSlot * len(c_slots)
    slot_array = slot_array_type(*c_slots)
    keepalive.append(slot_array)
    return (slot_array, _C_ArgSlot, tuple(keepalive))


def _invoke_placeholder_entry(_slots: tuple[_ArgSlot, ...]) -> int:
    """执行 dry-run 空产物占位入口。


    功能说明:
    - 保持空 `.so` 产物的历史成功行为。

    使用示例:
    - _invoke_placeholder_entry(())

    关联文件:
    - spec: spec/execute_engine/execute_engine.md
    - test: test/execute_engine/test_invoke.py
    - 功能实现: kernel_gen/execute_engine/compiler.py
    """

    return 0


def _invoke_loaded_entry_symbol(
    ordered_slots: tuple[_ArgSlot, ...],
    *,
    symbol: _LoadedEntrySymbol,
) -> int:
    """调用已解析出的 C ABI entry symbol。


    功能说明:
    - 将 Python 参数槽位封送为 `_ArgSlot` 数组。
    - 调用 `ctypes` symbol 并返回整数状态码。

    使用示例:
    - invoke = partial(_invoke_loaded_entry_symbol, symbol=symbol)
    - invoke(())

    关联文件:
    - spec: spec/execute_engine/execute_engine.md
    - test: test/execute_engine/test_invoke.py
    - 功能实现: kernel_gen/execute_engine/compiler.py
    """

    slot_array, slot_struct, keepalive = _marshal_slots_for_abi(ordered_slots)
    symbol.argtypes = [ctypes.POINTER(slot_struct), ctypes.c_ulonglong]
    symbol.restype = ctypes.c_int
    result = int(symbol(slot_array, ctypes.c_ulonglong(len(ordered_slots))))
    _ = keepalive
    return result


def _load_entry_point(soname_path: str, entry_point: str) -> Callable[[tuple[_ArgSlot, ...]], int]:
    """加载 entry point 并返回可调用对象（P0/S3）。


    功能说明:
    - 对真实 `.so` 执行动态加载，并把 Python 槽位转换为 C ABI 参数后调用入口。
    - 对 dry-run 生成的空产物，保留历史占位成功行为，避免破坏骨架测试。

    使用示例:
    - invoke = _load_entry_point("libkernel.so", "kg_execute_entry")
    - assert invoke(()) == 0

    关联文件:
    - spec: spec/execute_engine/execute_engine.md
    - test: test/execute_engine/test_invoke.py
    - 功能实现: kernel_gen/execute_engine/compiler.py
    """

    if not isinstance(soname_path, str) or not soname_path:
        raise _execution_engine_error(
            _RUNTIME_THROW_OR_ABORT,
            "soname_path is empty",
        )
    soname = Path(soname_path)
    if not soname.is_file():
        raise _execution_engine_error(
            _RUNTIME_THROW_OR_ABORT,
            "soname_path is missing",
        )
    if soname.stat().st_size == 0:
        return _invoke_placeholder_entry

    try:
        library = ctypes.CDLL(str(soname))
    except OSError as exc:
        raise _execution_engine_error(
            _SYMBOL_RESOLVE_FAILED,
            f"unable to load shared object: {exc}",
        ) from exc
    try:
        symbol = getattr(library, entry_point)
    except AttributeError as exc:
        raise _execution_engine_error(
            _SYMBOL_RESOLVE_FAILED,
            f"entry_point '{entry_point}' is missing",
        ) from exc

    return partial(_invoke_loaded_entry_symbol, symbol=symbol)


@dataclass(frozen=True)
class ExecuteResult:
    """执行引擎对外结果模型（P0）。"""

    ok: bool
    status_code: int
    failure_phrase: str | None
    compile_stdout: str = ""
    compile_stderr: str = ""
    run_stdout: str = ""
    run_stderr: str = ""
    elapsed_ms: float = 0.0


@dataclass(frozen=True)
class CompiledKernel:
    """编译产物的只读描述（P0）。


    功能说明:
    - 承载已编译产物的目标、共享库路径与入口名。
    - 若底层编译使用了内部临时工作目录，可通过 `close()` 显式释放；析构时也会兜底释放。

    使用示例:
    - kernel = engine.compile(source="int main(){}", function="cpu::add")
    - kernel.close()

    关联文件:
    - spec: spec/execute_engine/execute_engine.md
    - spec: spec/execute_engine/execute_engine_api.md
    - test: test/execute_engine/test_compile.py
    - 功能实现: kernel_gen/execute_engine/compiler.py
    """

    target: str
    soname_path: str
    function: str
    entry_point: str
    compile_stdout: str = ""
    compile_stderr: str = ""
    _cleanup: Callable[[], None] | None = field(default=None, repr=False, compare=False)
    _cleanup_state: list[Callable[[], None] | None] = field(default_factory=list, init=False, repr=False, compare=False)

    def __post_init__(self) -> None:
        """初始化关闭状态。


        功能说明:
        - 保持 `CompiledKernel` 对外 frozen，同时用私有可变状态记录 cleanup 是否已消费。

        使用示例:
        - kernel = engine.compile(source="int main(){}", function="cpu::add")
        - kernel.close()

        关联文件:
        - spec: spec/execute_engine/execute_engine.md
        - test: test/execute_engine/test_compile.py
        - 功能实现: kernel_gen/execute_engine/compiler.py
        """

        self._cleanup_state.append(self._cleanup)

    def close(self) -> None:
        """释放编译产物关联的内部临时工作区。


        功能说明:
        - 当 `compile()` 使用内部临时目录时，显式删除该目录，避免临时文件长期残留。
        - 重复调用是安全的，已关闭时不再重复释放。

        使用示例:
        - kernel = engine.compile(source="int main(){}", function="cpu::add")
        - kernel.close()

        关联文件:
        - spec: spec/execute_engine/execute_engine.md
        - spec: spec/execute_engine/execute_engine_api.md
        - test: test/execute_engine/test_compile.py
        - 功能实现: kernel_gen/execute_engine/compiler.py
        """

        cleanup = self._cleanup_state[0] if self._cleanup_state else None
        if cleanup is None:
            return
        self._cleanup_state[0] = None
        cleanup()

    def __del__(self) -> None:
        try:
            self.close()
        except Exception:
            pass

    def execute(
        self,
        args: tuple[RuntimeInput, ...] | None = None,
        *,
        request: ExecuteRequest | None = None,
        entry_point: str | None = None,
        capture_function_output: bool = False,
        stream: None = None,
    ) -> ExecuteResult:
        """执行已编译 kernel（骨架版本）。


        功能说明:
        - S3 补齐调用路径：参数绑定、entry shim 协议、动态加载与执行返回。
        - 保持 `stream` / `capture_function_output` 的禁用行为与失败短语。
        - 成功时返回 `ok=True/status_code=0/failure_phrase=None` 并带回编译 stdout/stderr。

        使用示例:
        - result = kernel.execute(args=(1, 2.0))

        关联文件:
        - spec: spec/execute_engine/execute_engine.md
        - test: test/execute_engine/test_contract.py
        - 功能实现: kernel_gen/execute_engine/compiler.py
        """

        if request is not None:
            args = request.args
            entry_point = request.entry_point if entry_point is None else entry_point
            capture_function_output = request.capture_function_output
            stream = request.stream

        if stream is not None:
            raise _execution_engine_error(
                _STREAM_NOT_SUPPORTED,
                "ExecuteRequest.stream is not supported in P0",
            )
        if capture_function_output:
            raise _execution_engine_error(
                _FUNCTION_OUTPUT_CAPTURE_NOT_SUPPORTED,
                "ExecuteRequest.capture_function_output is not supported in P0",
            )

        if args is None:
            raise _execution_engine_error(
                _RUNTIME_THROW_OR_ABORT,
                "args must be provided",
            )
        if not isinstance(args, tuple):
            raise _execution_engine_error(
                _RUNTIME_THROW_OR_ABORT,
                "args must be a tuple",
            )
        ordered_slots = _build_arg_slots(args)

        resolved_entry = self.entry_point if entry_point is None else entry_point
        if not isinstance(resolved_entry, str) or not resolved_entry.strip():
            raise _execution_engine_error(
                _SYMBOL_RESOLVE_FAILED,
                "entry_point is empty",
            )
        if resolved_entry != self.entry_point:
            raise _execution_engine_error(
                _SYMBOL_RESOLVE_FAILED,
                "entry_point mismatch",
            )

        invoke_entry = _load_entry_point(self.soname_path, resolved_entry)
        status_code = invoke_entry(ordered_slots)
        if status_code != 0:
            raise _execution_engine_error(
                _RUNTIME_THROW_OR_ABORT,
                f"entry_point returned non-zero ({status_code})",
            )

        return ExecuteResult(
            ok=True,
            status_code=0,
            failure_phrase=None,
            compile_stdout=self.compile_stdout,
            compile_stderr=self.compile_stderr,
        )


@dataclass(frozen=True)
class ExecutionEngine:
    """执行引擎入口（骨架版本，P0）。"""

    target: str
    compiler: str | None = None
    compiler_flags: tuple[str, ...] = ("-std=c++17",)
    link_flags: tuple[str, ...] = ()

    def compile(
        self,
        source: str | None = None,
        function: str | None = None,
        *,
        request: CompileRequest | None = None,
        entry_point: str = "kg_execute_entry",
    ) -> CompiledKernel:
        """编译 C++ 源码并返回 `CompiledKernel`（骨架版本）。


        功能说明:
        - S2 阶段固定编译路径拼装：target include 选择 -> entry shim -> 编译命令生成 -> CompiledKernel。
        - `target=cpu` 保持 dry-run；`target=npu_demo` 走真实编译，支持下游合同验收的真实执行。
        - 编译失败时会先回收内部临时工作区，再抛出 `compile_failed`。
        - 保持公共失败短语：
          - `target_header_mismatch`
          - `source_empty_or_invalid`
          - `compile_failed`
          - `symbol_resolve_failed`

        使用示例:
        - kernel = ExecutionEngine(target="cpu").compile(source="...", function="cpu::add")

        关联文件:
        - spec: spec/execute_engine/execute_engine.md
        - spec: spec/execute_engine/execute_engine_target.md
        - test: test/execute_engine/test_compile.py
        - 功能实现: kernel_gen/execute_engine/compiler.py
        """

        if request is not None:
            source = request.source
            function = request.function
            entry_point = request.entry_point
            target = request.target
            compiler = _resolve_compiler_name(request.compiler)
            compiler_flags = _ensure_compiler_flags(request.compiler_flags)
            link_flags = request.link_flags
        else:
            target = self.target
            compiler = _resolve_compiler_name(self.compiler)
            compiler_flags = _ensure_compiler_flags(self.compiler_flags)
            link_flags = self.link_flags

        if target not in ("cpu", "npu_demo"):
            raise _execution_engine_error(
                _TARGET_HEADER_MISMATCH,
                f"unsupported target: {target}",
            )
        if source is None or not isinstance(source, str) or not source.strip():
            raise _execution_engine_error(
                _SOURCE_EMPTY_OR_INVALID,
                "source is empty",
            )
        include_family = _source_include_family(source)
        if include_family == "mixed":
            raise _execution_engine_error(
                _TARGET_HEADER_MISMATCH,
                "source includes mixed target include families",
            )
        if include_family is not None and include_family != target:
            raise _execution_engine_error(
                _TARGET_HEADER_MISMATCH,
                f"source include family mismatch: source={include_family}, target={target}",
            )
        if "#error" in source:
            raise _execution_engine_error(
                _COMPILE_FAILED,
                "source contains #error directive",
            )
        if function is None or not isinstance(function, str) or not function.strip():
            raise _execution_engine_error(
                _SYMBOL_RESOLVE_FAILED,
                "function is empty",
            )
        if not isinstance(entry_point, str) or not entry_point.strip():
            raise _execution_engine_error(
                _SYMBOL_RESOLVE_FAILED,
                "entry_point is empty",
            )

        target_headers = _include_lines_for_target(target)
        if not target_headers:
            raise _execution_engine_error(
                _TARGET_HEADER_MISMATCH,
                f"unsupported target: {target}",
            )
        shim_source = ""
        if _requires_entry_shim(source, entry_point):
            shim_source = _compose_entry_shim_source(
                function=function,
                entry_point=entry_point,
                source=source,
            )
        compile_unit = _compose_compile_unit(
            source=source,
            _include_lines_for_target=target_headers,
            entry_shim_source=shim_source,
        )
        artifacts = _compile_unit_source(
            source=compile_unit,
            compiler=compiler,
            compiler_flags=compiler_flags,
            link_flags=link_flags,
            include_dirs=(str(REPO_ROOT),),
            dry_run=(target == "cpu"),
        )
        try:
            if artifacts.return_code != 0:
                raise _execution_engine_error(
                    _COMPILE_FAILED,
                    f"compiler returned non-zero ({artifacts.return_code})",
                )
            if not Path(artifacts.soname_path).exists():
                raise _execution_engine_error(
                    _COMPILE_FAILED,
                    "compile output is missing",
                )
        except Exception:
            if artifacts._cleanup is not None:
                try:
                    artifacts._cleanup()
                except Exception:
                    pass
            raise

        return CompiledKernel(
            target=target,
            soname_path=artifacts.soname_path,
            function=function,
            entry_point=entry_point,
            compile_stdout=artifacts.stdout,
            compile_stderr=artifacts.stderr,
            _cleanup=artifacts._cleanup,
        )


__all__ = [
    "CompiledKernel",
    "CompileRequest",
    "ExecuteRequest",
    "ExecuteResult",
    "ExecutionEngine",
]
