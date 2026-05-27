"""ExecutionEngine public facade and stable compile/execute contracts.

功能说明:
- 定义 execute_engine 对外稳定的编译请求、执行请求、执行结果、编译产物和引擎入口。
- 保留 `compiler.py` 旧公开导入路径，并 re-export strategy registry 公开 API。
- 通过 `builtin_strategy.py` 生成内置后端编译产物，通过 `runtime_args.py` 完成运行时 ABI 调用。

API 列表:
- `class CompileRequest(source: str, target: str, function: str, entry_point: str = "kg_execute_entry", compiler: str | None = None, compiler_flags: tuple[str, ...] = ("-std=c++17",), link_flags: tuple[str, ...] = ())`
- `class ExecuteRequest(args: tuple[RuntimeInput, ...], entry_point: str | None = None, capture_function_output: bool = False, stream: None = None)`
- `class ExecuteResult(ok: bool, status_code: int, failure_phrase: str | None, compile_stdout: str = "", compile_stderr: str = "", run_stdout: str = "", run_stderr: str = "", elapsed_ms: float = 0.0)`
- `class CompiledKernel(target: str, soname_path: str, function: str, entry_point: str, compile_stdout: str = "", compile_stderr: str = "")`
- `CompiledKernel.close() -> None`
- `CompiledKernel.execute(args: tuple[RuntimeInput, ...] | None = None, *, request: ExecuteRequest | None = None, entry_point: str | None = None, capture_function_output: bool = False, stream: None = None) -> ExecuteResult`
- `class CompileStrategy`
- `CompileStrategy.compile(self, request: CompileRequest) -> CompiledKernel`
- `register_compile_strategy(target: str, strategy: CompileStrategy, *, override: bool = False) -> None`
- `get_compile_strategy(target: str) -> CompileStrategy`
- `class ExecutionEngine(target: str, compiler: str | None = None, compiler_flags: tuple[str, ...] = ("-std=c++17",), link_flags: tuple[str, ...] = ())`
- `ExecutionEngine.compile(source: str | None = None, function: str | None = None, *, request: CompileRequest | None = None, entry_point: str = "kg_execute_entry") -> CompiledKernel`

使用示例:
```python
from kernel_gen.execute_engine import ExecutionEngine, ExecuteRequest

engine = ExecutionEngine(target="cpu")
kernel = engine.compile(source="int main(){}", function="cpu::add")
result = kernel.execute(request=ExecuteRequest(args=()))
```

关联文件:
- spec/execute_engine/execute_engine.md
- spec/execute_engine/execute_engine_api.md
- spec/execute_engine/execute_engine_target.md
- spec/execute_engine/strategy.md
- kernel_gen/execute_engine/strategy.py
- kernel_gen/execute_engine/builtin_strategy.py
- kernel_gen/execute_engine/runtime_args.py
- test/execute_engine/test_contract.py
- test/execute_engine/test_compile.py
- test/execute_engine/test_builtin_strategy.py
- test/execute_engine/test_invoke.py
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field

from kernel_gen.core.error import ErrorKind, ErrorModule, KernelCodeError
import kernel_gen.execute_engine.runtime_args as _runtime_args
from kernel_gen.execute_engine.runtime_args import (
    invoke_compiled_kernel as _invoke_compiled_kernel,
)
from kernel_gen.execute_engine.strategy import (
    CompileStrategy,
    get_compile_strategy,
    register_compile_strategy,
)


_TARGET_HEADER_MISMATCH = "target_header_mismatch"
_SOURCE_EMPTY_OR_INVALID = "source_empty_or_invalid"
_COMPILE_FAILED = "compile_failed"
_TEMPLATE_INSTANCE_REQUIRED = "template_instance_required"
_SYMBOL_RESOLVE_FAILED = "symbol_resolve_failed"
_RUNTIME_THROW_OR_ABORT = "runtime_throw_or_abort"
_STREAM_NOT_SUPPORTED = "stream_not_supported"
_FUNCTION_OUTPUT_CAPTURE_NOT_SUPPORTED = "function_output_capture_not_supported"
_EXECUTION_UNSUPPORTED = "execution_unsupported"

_KNOWN_ERROR_PHRASES: frozenset[str] = frozenset(
    {
        _TARGET_HEADER_MISMATCH,
        _SOURCE_EMPTY_OR_INVALID,
        _COMPILE_FAILED,
        _TEMPLATE_INSTANCE_REQUIRED,
        _SYMBOL_RESOLVE_FAILED,
        _RUNTIME_THROW_OR_ABORT,
        _STREAM_NOT_SUPPORTED,
        _FUNCTION_OUTPUT_CAPTURE_NOT_SUPPORTED,
        _EXECUTION_UNSUPPORTED,
    }
)


class _ExecutionEngineSupport:
    """当前文件内部 facade 支持逻辑，不进入文件级 API 或包根 `__all__`。"""

    @staticmethod
    def error(failure_phrase: str, detail: str = "") -> KernelCodeError:
        """功能说明:
        构造 execute_engine 的稳定公开错误对象。

        使用示例:
        ```python
        err = _ExecutionEngineSupport.error("compile_failed", "compiler returned non-zero")
        ```
        """

        if failure_phrase not in _KNOWN_ERROR_PHRASES:
            raise KernelCodeError(
                ErrorKind.CONTRACT,
                ErrorModule.EXECUTE_ENGINE,
                f"unknown failure phrase: {failure_phrase}",
            )
        message = failure_phrase if not detail else f"{failure_phrase}: {detail}"
        error = KernelCodeError(ErrorKind.CONTRACT, ErrorModule.EXECUTE_ENGINE, message)
        error.failure_phrase = failure_phrase
        return error


@dataclass(frozen=True)
class CompileRequest:
    """编译请求模型。

    功能说明:
    描述待编译源码、target、被包装函数名、entry point 和编译器 flags。

    使用示例:
    ```python
    request = CompileRequest(source="int main(){}", target="cpu", function="cpu::add")
    ```
    """

    source: str
    target: str
    function: str
    entry_point: str = "kg_execute_entry"
    compiler: str | None = None
    compiler_flags: tuple[str, ...] = ("-std=c++17",)
    link_flags: tuple[str, ...] = ()


@dataclass(frozen=True)
class ExecuteRequest:
    """执行请求模型。

    功能说明:
    描述运行时参数、可选 entry point 和当前公开禁用的 stream / function output capture。

    使用示例:
    ```python
    request = ExecuteRequest(args=(runtime_arg,))
    ```
    """

    args: tuple[_runtime_args.RuntimeInput, ...]
    entry_point: str | None = None
    capture_function_output: bool = False
    stream: None = None


@dataclass(frozen=True)
class ExecuteResult:
    """执行结果模型。

    功能说明:
    返回执行是否成功、状态码、failure phrase 和编译/运行输出摘要。

    使用示例:
    ```python
    result = ExecuteResult(ok=True, status_code=0, failure_phrase=None)
    ```
    """

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
    """编译产物的只读描述。

    功能说明:
    保存已编译产物 target、共享库路径、函数名、entry point 和清理钩子。

    使用示例:
    ```python
    kernel = engine.compile(source="int main(){}", function="cpu::add")
    kernel.close()
    ```
    """

    target: str
    soname_path: str
    function: str
    entry_point: str
    compile_stdout: str = ""
    compile_stderr: str = ""
    allow_absent_memory_args: tuple[_runtime_args.AllowAbsentMemoryArg, ...] = field(
        default_factory=tuple,
        repr=False,
        compare=False,
    )
    _cleanup: Callable[[], None] | None = field(
        default=None,
        repr=False,
        compare=False,
    )
    _cleanup_state: list[Callable[[], None] | None] = field(
        default_factory=list,
        init=False,
        repr=False,
        compare=False,
    )

    def __post_init__(self) -> None:
        """功能说明:
        初始化 cleanup 状态，保持 `close()` 幂等。

        使用示例:
        ```python
        kernel = engine.compile(source="int main(){}", function="cpu::add")
        ```
        """

        self._cleanup_state.append(self._cleanup)

    def close(self) -> None:
        """功能说明:
        释放编译产物关联的内部临时工作区。

        使用示例:
        ```python
        kernel.close()
        ```
        """

        cleanup = self._cleanup_state[0] if self._cleanup_state else None
        if cleanup is None:
            return
        self._cleanup_state[0] = None
        cleanup()

    def __del__(self) -> None:
        """功能说明:
        析构时尽力释放内部临时工作区。

        使用示例:
        ```python
        del kernel
        ```
        """

        try:
            self.close()
        except Exception:
            pass

    def execute(
        self,
        args: tuple[_runtime_args.RuntimeInput, ...] | None = None,
        *,
        request: ExecuteRequest | None = None,
        entry_point: str | None = None,
        capture_function_output: bool = False,
        stream: None = None,
    ) -> ExecuteResult:
        """功能说明:
        执行已编译 kernel，并保留旧公开错误短语和结果字段。

        使用示例:
        ```python
        result = kernel.execute(args=(runtime_arg,))
        ```
        """

        if request is not None:
            args = request.args
            entry_point = request.entry_point if entry_point is None else entry_point
            capture_function_output = request.capture_function_output
            stream = request.stream
        if stream is not None:
            raise _ExecutionEngineSupport.error(
                _STREAM_NOT_SUPPORTED,
                "ExecuteRequest.stream is not supported in P0",
            )
        if capture_function_output:
            raise _ExecutionEngineSupport.error(
                _FUNCTION_OUTPUT_CAPTURE_NOT_SUPPORTED,
                "ExecuteRequest.capture_function_output is not supported in P0",
            )
        if self.target not in ("cpu", "npu_demo"):
            raise _ExecutionEngineSupport.error(
                _EXECUTION_UNSUPPORTED,
                "compiled target does not expose runtime execution",
            )
        if args is None:
            raise _ExecutionEngineSupport.error(_RUNTIME_THROW_OR_ABORT, "args must be provided")
        if not isinstance(args, tuple):
            raise _ExecutionEngineSupport.error(_RUNTIME_THROW_OR_ABORT, "args must be a tuple")

        resolved_entry = self.entry_point if entry_point is None else entry_point
        if not isinstance(resolved_entry, str) or not resolved_entry.strip():
            raise _ExecutionEngineSupport.error(_SYMBOL_RESOLVE_FAILED, "entry_point is empty")
        if resolved_entry != self.entry_point:
            raise _ExecutionEngineSupport.error(_SYMBOL_RESOLVE_FAILED, "entry_point mismatch")

        status_code = _invoke_compiled_kernel(
            self.soname_path,
            resolved_entry,
            args,
            self.allow_absent_memory_args,
        )
        if status_code != 0:
            raise _ExecutionEngineSupport.error(
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


class _BuiltinCompileStrategy:
    """功能说明:
    内置 CPU/npu_demo strategy，负责把 compile artifacts 包装为 CompiledKernel。

    使用示例:
    ```python
    strategy = _BuiltinCompileStrategy()
    ```
    """

    def compile(self, request: CompileRequest) -> CompiledKernel:
        """功能说明:
        调用 builtin_strategy 生成编译产物，再装配公开 CompiledKernel。

        使用示例:
        ```python
        kernel = _BuiltinCompileStrategy().compile(request)
        ```
        """

        artifacts = _build_builtin_compile_artifacts(request)
        allow_absent_memory_args = tuple(
            _runtime_args.AllowAbsentMemoryArg(index=index, dtype=dtype, rank=rank)
            for index, dtype, rank in artifacts.allow_absent_memory_arg_specs
        )
        return CompiledKernel(
            target=request.target,
            soname_path=artifacts.soname_path,
            function=request.function,
            entry_point=request.entry_point,
            compile_stdout=artifacts.stdout,
            compile_stderr=artifacts.stderr,
            allow_absent_memory_args=allow_absent_memory_args,
            _cleanup=artifacts.cleanup,
        )


@dataclass(frozen=True)
class ExecutionEngine:
    """执行引擎入口。

    功能说明:
    从 strategy registry 读取 target strategy，并按公开请求完成编译。

    使用示例:
    ```python
    kernel = ExecutionEngine(target="cpu").compile(source="...", function="cpu::add")
    ```
    """

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
        """功能说明:
        编译 C++ 源码并返回 CompiledKernel。

        使用示例:
        ```python
        kernel = engine.compile(source="...", function="cpu::add")
        ```
        """

        if request is not None:
            if source is not None or function is not None:
                raise _ExecutionEngineSupport.error(
                    _SOURCE_EMPTY_OR_INVALID,
                    "request cannot be combined with source or function",
                )
            target = request.target
            compile_request = request
        else:
            target = self.target
            compile_request = CompileRequest(
                source=source,
                target=target,
                function=function,
                entry_point=entry_point,
                compiler=self.compiler,
                compiler_flags=self.compiler_flags,
                link_flags=self.link_flags,
            )
        strategy = get_compile_strategy(target)
        return strategy.compile(compile_request)


__all__ = [
    "CompileStrategy",
    "CompiledKernel",
    "CompileRequest",
    "ExecuteRequest",
    "ExecuteResult",
    "ExecutionEngine",
    "get_compile_strategy",
    "register_compile_strategy",
]


from kernel_gen.execute_engine.builtin_strategy import (  # noqa: E402
    build_builtin_compile_artifacts as _build_builtin_compile_artifacts,
    install_builtin_compile_strategies as _install_builtin_compile_strategies,
)


_install_builtin_compile_strategies(_BuiltinCompileStrategy)
