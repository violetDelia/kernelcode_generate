"""execute_engine builtin strategy package.

功能说明:
- 保留内置 compile strategy 的文件级 API，并按 target 分发到 `cpu`、`npu_demo`、`cuda_sm89` 实现模块。
- 不进入 `kernel_gen.execute_engine` 包根公开 API，不运行期导入 `compiler.py`，不构造 `CompiledKernel`。

API 列表:
- `class BuiltinCompileArtifacts(soname_path: str, source_path: str, command: tuple[str, ...], stdout: str, stderr: str, return_code: int, allow_absent_memory_arg_specs: tuple[tuple[int, str, int], ...] = (), cleanup: Callable[[], None] | None = None)`
- `build_builtin_compile_artifacts(request: "CompileRequest") -> BuiltinCompileArtifacts`
- `install_builtin_compile_strategies(strategy_factory: Callable[[], CompileStrategy]) -> None`

使用示例:
- artifacts = build_builtin_compile_artifacts(request)
- install_builtin_compile_strategies(strategy_factory)

关联文件:
- spec: spec/execute_engine/strategy.md
- spec: spec/execute_engine/execute_engine_target.md
- test: test/execute_engine/test_contract.py
- test: test/execute_engine/test_builtin_strategy.py
- 功能实现: kernel_gen/execute_engine/compiler.py
- 功能实现: kernel_gen/execute_engine/builtin_strategy/cpu.py
- 功能实现: kernel_gen/execute_engine/builtin_strategy/npu_demo.py
- 功能实现: kernel_gen/execute_engine/builtin_strategy/cuda_sm89.py
"""

from __future__ import annotations

from collections.abc import Callable

from kernel_gen.execute_engine.builtin_strategy.common import (
    BuiltinCompileArtifacts,
    BuiltinStrategySupport,
)
from kernel_gen.execute_engine.builtin_strategy.cpu import build_cpu_compile_artifacts
from kernel_gen.execute_engine.builtin_strategy.cuda_sm89 import build_cuda_sm89_compile_artifacts
from kernel_gen.execute_engine.builtin_strategy.npu_demo import build_npu_demo_compile_artifacts
from kernel_gen.execute_engine.strategy import CompileStrategy, register_compile_strategy


def build_builtin_compile_artifacts(request: "CompileRequest") -> BuiltinCompileArtifacts:
    """生成内置 target 编译产物。

    功能说明:
    - 校验公共 compile request 边界后，按 target 分发到 `cpu`、`npu_demo` 或 `cuda_sm89` 模块。
    - 返回不依赖 `compiler.py` 类型的产物描述，由 facade 负责装配 `CompiledKernel`。

    使用示例:
    - artifacts = build_builtin_compile_artifacts(request)
    """

    source = request.source
    target = request.target
    function = request.function
    entry_point = request.entry_point
    if source is None or not isinstance(source, str) or not source.strip():
        raise BuiltinStrategySupport.builtin_compile_error("source_empty_or_invalid", "source is empty")
    include_family = BuiltinStrategySupport.source_include_family(source)
    if include_family == "mixed":
        raise BuiltinStrategySupport.builtin_compile_error("target_header_mismatch", "source includes mixed target include families")
    if include_family is not None and include_family != target:
        raise BuiltinStrategySupport.builtin_compile_error(
            "target_header_mismatch",
            f"source include family mismatch: source={include_family}, target={target}",
        )
    if "#error" in source:
        raise BuiltinStrategySupport.builtin_compile_error("compile_failed", "source contains #error directive")
    if function is None or not isinstance(function, str) or not function.strip():
        raise BuiltinStrategySupport.builtin_compile_error("symbol_resolve_failed", "function is empty")
    if not isinstance(entry_point, str) or not entry_point.strip():
        raise BuiltinStrategySupport.builtin_compile_error("symbol_resolve_failed", "entry_point is empty")

    if target == "cuda_sm89" and request.compiler is None:
        compiler = "nvcc"
    else:
        compiler = BuiltinStrategySupport.resolve_compiler_name(request.compiler)
    compiler_flags = BuiltinStrategySupport.ensure_compiler_flags(request.compiler_flags)
    compiler_flags = BuiltinStrategySupport.trance_compiler_flags(function=function, compiler_flags=compiler_flags)

    if target == "cpu":
        return build_cpu_compile_artifacts(request, compiler, compiler_flags, request.link_flags)
    if target == "npu_demo":
        return build_npu_demo_compile_artifacts(request, compiler, compiler_flags, request.link_flags)
    if target == "cuda_sm89":
        return build_cuda_sm89_compile_artifacts(request, compiler, compiler_flags, request.link_flags)
    raise BuiltinStrategySupport.builtin_compile_error("target_header_mismatch", f"unsupported target: {target}")


def install_builtin_compile_strategies(strategy_factory: Callable[[], CompileStrategy]) -> None:
    """安装内置 compile strategy。

    功能说明:
    - 使用调用方提供的 factory 为 `cpu`、`npu_demo` 与 `cuda_sm89` 分别创建 strategy 实例。
    - 安装时使用 `override=True`，保持模块重载或重复导入时的既有覆盖语义。

    使用示例:
    - install_builtin_compile_strategies(strategy_factory)
    """

    register_compile_strategy("cpu", strategy_factory(), override=True)
    register_compile_strategy("npu_demo", strategy_factory(), override=True)
    register_compile_strategy("cuda_sm89", strategy_factory(), override=True)


__all__ = [
    "BuiltinCompileArtifacts",
    "build_builtin_compile_artifacts",
    "install_builtin_compile_strategies",
]
