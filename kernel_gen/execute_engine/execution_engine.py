"""ExecutionEngine skeleton (P0).

创建者: 朽木露琪亚
最后一次更改: jcc你莫辜负

功能说明:
- 提供 `ExecutionEngine.compile(...).execute(...)` 的最小壳层，以便在不实现真实编译/调用的前提下固定：
  - 公开 API 的命名与字段形态；
  - 7 个公共失败短语（failure_phrase）的固定集合；
  - `stream` 与 `capture_function_output` 在 P0 的禁用行为。

使用示例:
- from kernel_gen.execute_engine import ExecutionEngine, ExecuteRequest
- engine = ExecutionEngine(target="cpu")
- kernel = engine.compile(source="int main(){}", function="cpu::add")
- result = kernel.execute(request=ExecuteRequest(args=()))
- assert result.ok is True

关联文件:
- spec: spec/execute_engine/execute_engine.md
- spec: spec/execute_engine/execute_engine_api.md
- spec: spec/execute_engine/execute_engine_target.md
- test: test/execute_engine/test_execute_engine_contract.py
- 功能实现: kernel_gen/execute_engine/execution_engine.py
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Literal, TypeAlias

from kernel_gen.execute_engine.compiler import (
    build_compile_unit,
    compile_source,
    default_compiler,
)
from kernel_gen.execute_engine.entry_shim_builder import (
    build_entry_shim_source,
    needs_entry_shim,
)
from kernel_gen.execute_engine.target_registry import target_includes

FAILURE_TARGET_HEADER_MISMATCH = "target_header_mismatch"
FAILURE_SOURCE_EMPTY_OR_INVALID = "source_empty_or_invalid"
FAILURE_COMPILE_FAILED = "compile_failed"
FAILURE_SYMBOL_RESOLVE_FAILED = "symbol_resolve_failed"
FAILURE_RUNTIME_THROW_OR_ABORT = "runtime_throw_or_abort"
FAILURE_STREAM_NOT_SUPPORTED = "stream_not_supported"
FAILURE_FUNCTION_OUTPUT_CAPTURE_NOT_SUPPORTED = "function_output_capture_not_supported"

FAILURE_PHRASES: frozenset[str] = frozenset(
    {
        FAILURE_TARGET_HEADER_MISMATCH,
        FAILURE_SOURCE_EMPTY_OR_INVALID,
        FAILURE_COMPILE_FAILED,
        FAILURE_SYMBOL_RESOLVE_FAILED,
        FAILURE_RUNTIME_THROW_OR_ABORT,
        FAILURE_STREAM_NOT_SUPPORTED,
        FAILURE_FUNCTION_OUTPUT_CAPTURE_NOT_SUPPORTED,
    }
)

TargetName: TypeAlias = Literal["cpu", "npu_demo"]


def _source_include_family(source: str) -> str | None:
    """从 source 粗略推断 include family。

    创建者: 朽木露琪亚
    最后一次更改: 朽木露琪亚

    功能说明:
    - 用于在不执行真实编译的前提下，对 `target` 与源码 include family 的一致性进行最小校验。
    - 只识别仓库内约定路径片段：`include/cpu/` 与 `include/npu_demo/`。

    使用示例:
    - assert _source_include_family('#include \"include/cpu/Memory.h\"') == \"cpu\"

    关联文件:
    - spec: spec/execute_engine/execute_engine_target.md
    - test: test/execute_engine/test_execute_engine_compile.py
    - 功能实现: kernel_gen/execute_engine/execution_engine.py
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


REPO_ROOT = Path(__file__).resolve().parents[2]


def _ensure_compiler_flags(flags: tuple[str, ...]) -> tuple[str, ...]:
    """确保编译 flags 包含 -std=c++17 基线。

    创建者: jcc你莫辜负
    最后一次更改: jcc你莫辜负

    功能说明:
    - 若调用方未提供 `-std=c++17`，则按基线规则补齐。
    - 其余 flags 保持原有顺序。

    使用示例:
    - assert _ensure_compiler_flags(("-O2",)) == ("-std=c++17", "-O2")

    关联文件:
    - spec: spec/execute_engine/execute_engine_target.md
    - test: test/execute_engine/test_execute_engine_compile.py
    - 功能实现: kernel_gen/execute_engine/execution_engine.py
    """

    if "-std=c++17" in flags:
        return flags
    return ("-std=c++17", *flags)


def _resolve_compiler_name(compiler: str | None) -> str:
    """解析编译器名称（P0/S2）。

    创建者: jcc你莫辜负
    最后一次更改: jcc你莫辜负

    功能说明:
    - 当 compiler 为空时回退到默认编译器。
    - 若 compiler 为空字符串或非字符串，则视为无效输入。

    使用示例:
    - assert _resolve_compiler_name(None) == "g++"

    关联文件:
    - spec: spec/execute_engine/execute_engine_target.md
    - test: test/execute_engine/test_execute_engine_compile.py
    - 功能实现: kernel_gen/execute_engine/execution_engine.py
    """

    if compiler is None:
        return default_compiler()
    if not isinstance(compiler, str) or not compiler.strip():
        raise ExecutionEngineError(
            FAILURE_COMPILE_FAILED,
            "compiler is empty",
        )
    return compiler


class ExecutionEngineError(RuntimeError):
    """对外可机械匹配的执行引擎错误。

    创建者: 朽木露琪亚
    最后一次更改: 朽木露琪亚

    功能说明:
    - 用固定 `failure_phrase` 承载失败原因，确保测试稳定匹配。

    使用示例:
    - raise ExecutionEngineError(FAILURE_SOURCE_EMPTY_OR_INVALID, "source is empty")

    关联文件:
    - spec: spec/execute_engine/execute_engine.md
    - test: test/execute_engine/test_execute_engine_contract.py
    - 功能实现: kernel_gen/execute_engine/execution_engine.py
    """

    def __init__(self, failure_phrase: str, detail: str = "") -> None:
        if failure_phrase not in FAILURE_PHRASES:
            raise ValueError(f"unknown failure_phrase: {failure_phrase}")
        super().__init__(f"{failure_phrase}: {detail}" if detail else failure_phrase)
        self.failure_phrase = failure_phrase


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

    args: tuple["ArgSpec", ...]
    entry_point: str | None = None
    capture_function_output: bool = False
    stream: object | None = None


@dataclass(frozen=True)
class MemoryArg:
    """内存参数模型（P0）。"""

    position: int
    param_name: str | None
    space: str
    dtype: str
    shape: tuple[int, ...]
    stride: tuple[int, ...] | None
    value: object


@dataclass(frozen=True)
class IntArg:
    """整数参数模型（P0）。"""

    position: int
    param_name: str | None
    dtype: str
    value: int


@dataclass(frozen=True)
class FloatArg:
    """浮点参数模型（P0）。"""

    position: int
    param_name: str | None
    dtype: str
    value: float


ArgSpec: TypeAlias = MemoryArg | IntArg | FloatArg


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
    """编译产物的只读描述（P0）。"""

    target: str
    soname_path: str
    function: str
    entry_point: str
    compile_stdout: str = ""
    compile_stderr: str = ""

    def execute(
        self,
        args: tuple[ArgSpec, ...] | None = None,
        *,
        request: ExecuteRequest | None = None,
        entry_point: str | None = None,
        capture_function_output: bool = False,
        stream: object | None = None,
    ) -> ExecuteResult:
        """执行已编译 kernel（骨架版本）。

        创建者: 朽木露琪亚
        最后一次更改: 朽木露琪亚

        功能说明:
        - 本阶段不要求真实运行，仅固定：
          - `stream` / `capture_function_output` 的禁用行为与失败短语；
          - `ExecuteResult` 的成功判定口径。

        使用示例:
        - result = kernel.execute(args=())

        关联文件:
        - spec: spec/execute_engine/execute_engine.md
        - test: test/execute_engine/test_execute_engine_contract.py
        - 功能实现: kernel_gen/execute_engine/execution_engine.py
        """

        if request is not None:
            args = request.args
            entry_point = request.entry_point if entry_point is None else entry_point
            capture_function_output = request.capture_function_output
            stream = request.stream

        if stream is not None:
            raise ExecutionEngineError(
                FAILURE_STREAM_NOT_SUPPORTED,
                "ExecuteRequest.stream is not supported in P0",
            )
        if capture_function_output:
            raise ExecutionEngineError(
                FAILURE_FUNCTION_OUTPUT_CAPTURE_NOT_SUPPORTED,
                "ExecuteRequest.capture_function_output is not supported in P0",
            )

        if args is None:
            raise ExecutionEngineError(
                FAILURE_RUNTIME_THROW_OR_ABORT,
                "args must be provided",
            )
        if not isinstance(args, tuple):
            raise ExecutionEngineError(
                FAILURE_RUNTIME_THROW_OR_ABORT,
                "args must be a tuple",
            )
        for idx, arg in enumerate(args):
            if not isinstance(arg, (MemoryArg, IntArg, FloatArg)):
                raise ExecutionEngineError(
                    FAILURE_RUNTIME_THROW_OR_ABORT,
                    f"unsupported ArgSpec at position {idx}",
                )

        resolved_entry = self.entry_point if entry_point is None else entry_point
        if not isinstance(resolved_entry, str) or not resolved_entry.strip():
            raise ExecutionEngineError(
                FAILURE_SYMBOL_RESOLVE_FAILED,
                "entry_point is empty",
            )

        return ExecuteResult(ok=True, status_code=0, failure_phrase=None)


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

        创建者: 朽木露琪亚
        最后一次更改: jcc你莫辜负

        功能说明:
        - S2 阶段固定编译路径拼装：target include 选择 -> entry shim -> 编译命令生成 -> CompiledKernel。
        - S2 默认以 dry-run 方式生成编译命令与占位产物，不执行真实编译。
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
        - test: test/execute_engine/test_execute_engine_compile.py
        - 功能实现: kernel_gen/execute_engine/execution_engine.py
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
            raise ExecutionEngineError(
                FAILURE_TARGET_HEADER_MISMATCH,
                f"unsupported target: {target}",
            )
        if source is None or not isinstance(source, str) or not source.strip():
            raise ExecutionEngineError(
                FAILURE_SOURCE_EMPTY_OR_INVALID,
                "source is empty",
            )
        include_family = _source_include_family(source)
        if include_family == "mixed":
            raise ExecutionEngineError(
                FAILURE_TARGET_HEADER_MISMATCH,
                "source includes mixed target include families",
            )
        if include_family is not None and include_family != target:
            raise ExecutionEngineError(
                FAILURE_TARGET_HEADER_MISMATCH,
                f"source include family mismatch: source={include_family}, target={target}",
            )
        if "#error" in source:
            raise ExecutionEngineError(
                FAILURE_COMPILE_FAILED,
                "source contains #error directive",
            )
        if function is None or not isinstance(function, str) or not function.strip():
            raise ExecutionEngineError(
                FAILURE_SYMBOL_RESOLVE_FAILED,
                "function is empty",
            )
        if not isinstance(entry_point, str) or not entry_point.strip():
            raise ExecutionEngineError(
                FAILURE_SYMBOL_RESOLVE_FAILED,
                "entry_point is empty",
            )

        target_headers = target_includes(target)
        if not target_headers:
            raise ExecutionEngineError(
                FAILURE_TARGET_HEADER_MISMATCH,
                f"unsupported target: {target}",
            )
        shim_source = ""
        if needs_entry_shim(source, entry_point):
            shim_source = build_entry_shim_source(
                function=function,
                entry_point=entry_point,
            )
        compile_unit = build_compile_unit(
            source=source,
            target_includes=target_headers,
            entry_shim_source=shim_source,
        )
        artifacts = compile_source(
            source=compile_unit,
            compiler=compiler,
            compiler_flags=compiler_flags,
            link_flags=link_flags,
            include_dirs=(str(REPO_ROOT),),
            dry_run=True,
        )
        if artifacts.return_code != 0:
            raise ExecutionEngineError(
                FAILURE_COMPILE_FAILED,
                f"compiler returned non-zero ({artifacts.return_code})",
            )
        if not Path(artifacts.soname_path).exists():
            raise ExecutionEngineError(
                FAILURE_COMPILE_FAILED,
                "compile output is missing",
            )

        return CompiledKernel(
            target=target,
            soname_path=artifacts.soname_path,
            function=function,
            entry_point=entry_point,
            compile_stdout=artifacts.stdout,
            compile_stderr=artifacts.stderr,
        )


__all__ = [
    "FAILURE_TARGET_HEADER_MISMATCH",
    "FAILURE_SOURCE_EMPTY_OR_INVALID",
    "FAILURE_COMPILE_FAILED",
    "FAILURE_SYMBOL_RESOLVE_FAILED",
    "FAILURE_RUNTIME_THROW_OR_ABORT",
    "FAILURE_STREAM_NOT_SUPPORTED",
    "FAILURE_FUNCTION_OUTPUT_CAPTURE_NOT_SUPPORTED",
    "FAILURE_PHRASES",
    "ArgSpec",
    "CompiledKernel",
    "CompileRequest",
    "ExecuteRequest",
    "ExecuteResult",
    "ExecutionEngine",
    "ExecutionEngineError",
    "FloatArg",
    "IntArg",
    "MemoryArg",
]
