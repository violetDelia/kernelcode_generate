"""execute_engine package.

创建者: 朽木露琪亚
最后一次更改: 朽木露琪亚

功能说明:
- 提供执行引擎 `P0` 的最小骨架与公共失败短语常量。
- 本阶段仅冻结接口形态与失败短语，不要求真实编译/运行能力。

使用示例:
- from kernel_gen.execute_engine import ExecutionEngine, ExecuteRequest
- engine = ExecutionEngine(target="cpu")
- kernel = engine.compile(source="int main(){}", function="cpu::add")
- result = kernel.execute(args=())

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
    ArgSpec,
    CompiledKernel,
    CompileRequest,
    ExecuteRequest,
    ExecuteResult,
    ExecutionEngine,
    ExecutionEngineError,
    FloatArg,
    IntArg,
    MemoryArg,
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

