"""execute_engine package.

创建者: 朽木露琪亚
最后一次更改: jcc你莫辜负

功能说明:
- 提供执行引擎 `P0` 的最小骨架与公共失败短语常量。
- 本阶段仅固定接口形态与失败短语，不要求真实编译/运行能力。

API 列表:
- `FAILURE_COMPILE_FAILED: str`
- `FAILURE_FUNCTION_OUTPUT_CAPTURE_NOT_SUPPORTED: str`
- `FAILURE_RUNTIME_THROW_OR_ABORT: str`
- `FAILURE_SOURCE_EMPTY_OR_INVALID: str`
- `FAILURE_STREAM_NOT_SUPPORTED: str`
- `FAILURE_SYMBOL_RESOLVE_FAILED: str`
- `FAILURE_TARGET_HEADER_MISMATCH: str`
- `FAILURE_PHRASES: frozenset[str]`
- `class CompileRequest(source: str, target: str, function: str, entry_point: str = "kg_execute_entry", compiler: str | None = None, compiler_flags: tuple[str, ...] = ("-std=c++17",), link_flags: tuple[str, ...] = ())`
- `class ExecuteRequest(args: tuple[RuntimeArg, ...], entry_point: str | None = None, capture_function_output: bool = False, stream: object | None = None)`
- `class ExecuteResult(ok: bool, status_code: int, failure_phrase: str | None, compile_stdout: str = "", compile_stderr: str = "", run_stdout: str = "", run_stderr: str = "", elapsed_ms: float = 0.0)`
- `class ExecutionEngineError(failure_phrase: str, detail: str = "")`
- `class CompiledKernel(target: str, soname_path: str, function: str, entry_point: str, compile_stdout: str = "", compile_stderr: str = "")`
- `CompiledKernel.close() -> None`
- `CompiledKernel.execute(args: tuple[RuntimeArg, ...] | None = None, *, request: ExecuteRequest | None = None, entry_point: str | None = None, capture_function_output: bool = False, stream: object | None = None) -> ExecuteResult`
- `class ExecutionEngine(target: str, compiler: str | None = None, compiler_flags: tuple[str, ...] = ("-std=c++17",), link_flags: tuple[str, ...] = ())`
- `ExecutionEngine.compile(source: str | None = None, function: str | None = None, *, request: CompileRequest | None = None, entry_point: str = "kg_execute_entry") -> CompiledKernel`

helper 清单:
- 无；本文件只做公开包入口重导出，不承接私有 helper。

使用示例:
- from kernel_gen.execute_engine import ExecutionEngine, ExecuteRequest
- engine = ExecutionEngine(target="cpu")
- kernel = engine.compile(source="int main(){}", function="cpu::add")
- result = kernel.execute(args=(1, 2.0))

关联文件:
- spec: spec/execute_engine/execute_engine.md
- spec: spec/execute_engine/execute_engine_api.md
- spec: spec/execute_engine/execute_engine_target.md
- test: test/execute_engine/test_execute_engine_contract.py
- 功能实现: kernel_gen/execute_engine/execution_engine.py
"""

from .execution_engine import (
    FAILURE_COMPILE_FAILED,
    FAILURE_FUNCTION_OUTPUT_CAPTURE_NOT_SUPPORTED,
    FAILURE_RUNTIME_THROW_OR_ABORT,
    FAILURE_SOURCE_EMPTY_OR_INVALID,
    FAILURE_STREAM_NOT_SUPPORTED,
    FAILURE_SYMBOL_RESOLVE_FAILED,
    FAILURE_TARGET_HEADER_MISMATCH,
    FAILURE_PHRASES,
    CompiledKernel,
    CompileRequest,
    ExecuteRequest,
    ExecuteResult,
    ExecutionEngine,
    ExecutionEngineError,
    RuntimeArg,
)

__all__ = [
    "FAILURE_COMPILE_FAILED",
    "FAILURE_FUNCTION_OUTPUT_CAPTURE_NOT_SUPPORTED",
    "FAILURE_RUNTIME_THROW_OR_ABORT",
    "FAILURE_SOURCE_EMPTY_OR_INVALID",
    "FAILURE_STREAM_NOT_SUPPORTED",
    "FAILURE_SYMBOL_RESOLVE_FAILED",
    "FAILURE_TARGET_HEADER_MISMATCH",
    "FAILURE_PHRASES",
    "CompiledKernel",
    "CompileRequest",
    "ExecuteRequest",
    "ExecuteResult",
    "ExecutionEngine",
    "ExecutionEngineError",
    "RuntimeArg",
]
