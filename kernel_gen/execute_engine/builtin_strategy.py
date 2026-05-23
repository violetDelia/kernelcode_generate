"""execute_engine builtin strategy installer.


功能说明:
- 承载内置 `cpu` / `npu_demo` compile strategy 的包内安装逻辑。
- 不承接 target include、entry shim、编译单元、运行期 ABI 或 kernel 装配。
- 不进入 `kernel_gen.execute_engine` 包根公开 API。

API 列表:
- `install_builtin_compile_strategies(strategy_factory: Callable[[], CompileStrategy]) -> None`

使用示例:
- 编译器模块完成内置 strategy 类定义后，用本安装函数安装内置 target strategy。

关联文件:
- spec: spec/execute_engine/strategy.md
- spec: spec/execute_engine/execute_engine_target.md
- test: test/execute_engine/test_builtin_strategy.py
- 功能实现: kernel_gen/execute_engine/compiler.py
"""

from __future__ import annotations

from collections.abc import Callable

from kernel_gen.execute_engine.strategy import CompileStrategy, register_compile_strategy


def install_builtin_compile_strategies(strategy_factory: Callable[[], CompileStrategy]) -> None:
    """安装内置 compile strategy。

    功能说明:
    - 使用调用方提供的 factory 为 `cpu` 与 `npu_demo` 分别创建 strategy 实例。
    - 安装时使用 `override=True`，保持模块重载或重复导入时的既有覆盖语义。

    使用示例:
    - install_builtin_compile_strategies(strategy_factory)
    """

    register_compile_strategy("cpu", strategy_factory(), override=True)
    register_compile_strategy("npu_demo", strategy_factory(), override=True)


__all__ = ["install_builtin_compile_strategies"]
