"""execute_engine package.


功能说明:
- 提供执行引擎 `P0` 的公开入口。
- 重导出编译请求、执行结果、真实执行引擎与 third-party compile strategy 注册入口。
- 内置 `cpu` / `npu_demo` 真实执行能力；第三方 target 可注册 compile-only 或自定义 compile strategy。

API 列表:
- `class CompileRequest(source: str, target: str, function: str, entry_point: str = "kg_execute_entry", compiler: str | None = None, compiler_flags: tuple[str, ...] = ("-std=c++17",), link_flags: tuple[str, ...] = ())`
- `class ExecuteRequest(args: tuple[RuntimeInput, ...], entry_point: str | None = None, capture_function_output: bool = False, stream: None = None)`
- `class ExecuteResult(ok: bool, status_code: int, failure_phrase: str | None, compile_stdout: str = "", compile_stderr: str = "", run_stdout: str = "", run_stderr: str = "", elapsed_ms: float = 0.0)`
- `class CompiledKernel(target: str, soname_path: str, function: str, entry_point: str, compile_stdout: str = "", compile_stderr: str = "")`
- `CompiledKernel.close() -> None`
- `CompiledKernel.execute(args: tuple[RuntimeInput, ...] | None = None, *, request: ExecuteRequest | None = None, entry_point: str | None = None, capture_function_output: bool = False, stream: None = None) -> ExecuteResult`
- `class CompileStrategy(Protocol)`
- `CompileStrategy.compile(self, request: CompileRequest) -> CompiledKernel`
- `register_compile_strategy(target: str, strategy: CompileStrategy, *, override: bool = False) -> None`
- `get_compile_strategy(target: str) -> CompileStrategy`
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
- test: test/execute_engine/test_contract.py
- 功能实现: kernel_gen/execute_engine/compiler.py
"""

from .compiler import (
    CompileStrategy,
    CompiledKernel,
    CompileRequest,
    ExecuteRequest,
    ExecuteResult,
    ExecutionEngine,
    get_compile_strategy,
    register_compile_strategy,
)

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
