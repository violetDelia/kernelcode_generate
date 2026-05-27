"""execute_engine compile strategy registry.


功能说明:
- 承载 `ExecutionEngine.compile(...)` 的公开 compile strategy 协议与 registry 真源。
- 仅定义 target strategy 的注册、查询和缺失错误语义，不承载内置 target 编译实现。

API 列表:
- `class CompileStrategy(Protocol)`
- `CompileStrategy.compile(self, request: "CompileRequest") -> "CompiledKernel"`
- `register_compile_strategy(target: str, strategy: CompileStrategy, *, override: bool = False) -> None`
- `get_compile_strategy(target: str) -> CompileStrategy`

使用示例:
- from kernel_gen.execute_engine.strategy import get_compile_strategy
- strategy = get_compile_strategy("cpu")

关联文件:
- spec: spec/execute_engine/strategy.md
- spec: spec/execute_engine/execute_engine_api.md
- test: test/execute_engine/test_compile_strategy.py
- 功能实现: kernel_gen/execute_engine/compiler.py
"""

from __future__ import annotations

import re
from typing import Protocol, runtime_checkable

from kernel_gen.core.error import ErrorKind, ErrorModule, KernelCodeError
from kernel_gen.target import registry as target_registry


_TARGET_HEADER_MISMATCH = "target_header_mismatch"
_COMPILE_FAILED = "compile_failed"
_KNOWN_STRATEGY_ERROR_PHRASES: frozenset[str] = frozenset(
    {
        _TARGET_HEADER_MISMATCH,
        _COMPILE_FAILED,
    }
)
_TARGET_NAME_PATTERN = re.compile(r"^[a-z0-9_]+$")


class _StrategyRegistrySupport:
    """当前文件内部 registry 支持逻辑，不进入文件级 API 或包根 `__all__`。"""

    @staticmethod
    def error(failure_phrase: str, detail: str = "") -> KernelCodeError:
        """构造 compile strategy registry 错误对象。

        功能说明:
        - 使用 execute_engine 公开 failure phrase 承载 registry 失败语义。
        - 在对象上写入 `failure_phrase`，保持调用方观测行为与旧路径一致。

        使用示例:
        - err = _StrategyRegistrySupport.error("compile_failed", "duplicate compile strategy: cpu")
        """

        if failure_phrase not in _KNOWN_STRATEGY_ERROR_PHRASES:
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
    def validate_target(target: str) -> None:
        """校验 compile strategy target。

        功能说明:
        - target 名必须满足 `[a-z0-9_]+`。
        - target 必须已通过公开 target registry 注册。

        使用示例:
        - _StrategyRegistrySupport.validate_target("cpu")
        """

        if not isinstance(target, str) or not _TARGET_NAME_PATTERN.fullmatch(target):
            raise _StrategyRegistrySupport.error(_TARGET_HEADER_MISMATCH, "invalid target name")
        try:
            target_registry.get_target_hardware(target, "__compile_strategy_probe__")
        except ValueError as exc:
            raise _StrategyRegistrySupport.error(_TARGET_HEADER_MISMATCH, f"target not registered: {target}") from exc


@runtime_checkable
class CompileStrategy(Protocol):
    """编译策略公开协议。"""

    def compile(self, request: "CompileRequest") -> "CompiledKernel":
        """执行 target 专属编译。

        功能说明:
        - 使用公开 compile request 生成 compiled kernel。
        - 失败必须抛出带稳定 failure phrase 的 `KernelCodeError`。

        使用示例:
        - kernel = strategy.compile(request)
        """


_COMPILE_STRATEGIES: dict[str, CompileStrategy] = {}


def register_compile_strategy(target: str, strategy: CompileStrategy, *, override: bool = False) -> None:
    """注册 target 对应的编译策略。

    功能说明:
    - `target` 必须是已注册 target。
    - 默认拒绝重复注册；`override=True` 时显式覆盖。

    使用示例:
    - register_compile_strategy("cpu", strategy, override=True)
    """

    _StrategyRegistrySupport.validate_target(target)
    if not isinstance(strategy, CompileStrategy):
        raise _StrategyRegistrySupport.error(_COMPILE_FAILED, "compile strategy must define compile")
    if target in _COMPILE_STRATEGIES and not override:
        raise _StrategyRegistrySupport.error(_COMPILE_FAILED, f"duplicate compile strategy: {target}")
    _COMPILE_STRATEGIES[target] = strategy


def get_compile_strategy(target: str) -> CompileStrategy:
    """读取 target 对应编译策略。

    功能说明:
    - target 必须是已注册 target。
    - 未注册 strategy 不回退到 `cpu` 或 `npu_demo`，稳定失败为 `target_header_mismatch`。

    使用示例:
    - strategy = get_compile_strategy("cpu")
    """

    _StrategyRegistrySupport.validate_target(target)
    strategy = _COMPILE_STRATEGIES.get(target)
    if strategy is None:
        raise _StrategyRegistrySupport.error(_TARGET_HEADER_MISMATCH, f"missing compile strategy: {target}")
    return strategy


__all__ = [
    "CompileStrategy",
    "get_compile_strategy",
    "register_compile_strategy",
]
