"""tools package.


功能说明:
- 暴露面向脚本与测试的轻量工具模块（例如 ircheck）。
- 包根惰性暴露 `DslRunResult` 公开类型，以及稳定的 `dsl_run(...)` / `dsl_cost_run(...)` 公开函数入口。
- `RuntimeRealArg` 文档类型覆盖 tensor/ndarray 协议与整数 runtime scalar。

API 列表:
- `DslRunResult(func_op: func.FuncOp, module: ModuleOp, source: str, compiled_kernel: CompiledKernel, execute_result: ExecuteResult, runtime_args: tuple[RuntimeRealArg, ...])`
- `dsl_run(func_obj: Callable[..., DslFunctionReturn], real_args: tuple[RuntimeRealArg, ...] | list[RuntimeRealArg], pipeline: str | PassManager) -> DslRunResult`
- `dsl_cost_run(func_obj: Callable[..., DslFunctionReturn], real_args: tuple[RuntimeRealArg, ...] | list[RuntimeRealArg], pipeline: str | PassManager, cost_kind: str) -> int`

helper 清单:
- `_load_dsl_run_exports() -> tuple[type[DslRunResult], Callable[..., DslRunResult], Callable[..., int]]`
- `__getattr__(name: str) -> type[DslRunResult]`

使用示例:
- from kernel_gen.tools.ircheck import run_ircheck_text
- import kernel_gen.tools as tools
- result = run_ircheck_text(\"\"\"// COMPILE_ARGS: --pass no-op
// CHECK: builtin.module

builtin.module {}
\"\"\")
- assert result.ok is True
- result = tools.dsl_run(add_kernel, (out, lhs, rhs), "npu-demo-lowering")
- cost = tools.dsl_cost_run(add_kernel, (out, lhs, rhs), "npu-demo-lowering", "VECTOR1")

关联文件:
- spec: [spec/tools/ircheck.md](spec/tools/ircheck.md)
- test: [test/tools/test_ircheck_runner.py](test/tools/test_ircheck_runner.py)
- 功能实现: [kernel_gen/tools/ircheck.py](kernel_gen/tools/ircheck.py)
- spec: [spec/tools/dsl_run.md](spec/tools/dsl_run.md)
- test: [test/tools/test_dsl_run.py](test/tools/test_dsl_run.py)
- 功能实现: [kernel_gen/tools/dsl_run.py](kernel_gen/tools/dsl_run.py)
"""

from __future__ import annotations

from collections.abc import Callable, Iterable
from typing import TYPE_CHECKING, Protocol, TypeAlias

if TYPE_CHECKING:
    from kernel_gen.passes.pass_manager import PassManager
    from kernel_gen.symbol_variable.memory import Memory
    from kernel_gen.symbol_variable.symbol_dim import SymbolDim
    from .dsl_run import DslRunResult

class _StringLike(Protocol):
    """运行时 dtype 的最小字符串化协议。"""

    def __str__(self) -> str:
        """返回 dtype 文本。"""


class TensorRuntimeArg(Protocol):
    """`kernel_gen.tools.dsl_run(...)` 支持的真实运行时数组参数协议。"""

    shape: Iterable[int]
    dtype: _StringLike


RuntimeRealArg: TypeAlias = "TensorRuntimeArg | int"
DslFunctionReturn: TypeAlias = "Memory | SymbolDim | int | float | bool | str | None"

__all__ = ["DslRunResult"]
_PACKAGE_ROOT_DSL_RUN: Callable[..., "DslRunResult"] | None = None
_PACKAGE_ROOT_DSL_COST_RUN: Callable[..., int] | None = None


def _load_dsl_run_exports() -> tuple[type["DslRunResult"], Callable[..., "DslRunResult"], Callable[..., int]]:
    """加载 `dsl_run` 公开导出对象。


    功能说明:
    - 集中导入 `kernel_gen.tools.dsl_run` 模块中的稳定公开名。
    - 供包根 `DslRunResult` 惰性导出与 `dsl_run(...)` / `dsl_cost_run(...)` 包装函数共用，避免重复写导入语句。
    - 每次子模块导入后都会把包根工具函数重新绑定回公开函数，消除同名子模块覆盖带来的导入顺序差异。

    使用示例:
    - dsl_run_result, dsl_run_func, dsl_cost_run_func = _load_dsl_run_exports()

    关联文件:
    - spec: [spec/tools/dsl_run.md](spec/tools/dsl_run.md)
    - test: [test/tools/test_package.py](test/tools/test_package.py)
    - 功能实现: [kernel_gen/tools/__init__.py](.)
    """

    from .dsl_run import DslRunResult, dsl_cost_run as dsl_cost_run_func, dsl_run as dsl_run_func

    if _PACKAGE_ROOT_DSL_RUN is not None:
        globals()["dsl_run"] = _PACKAGE_ROOT_DSL_RUN
    if _PACKAGE_ROOT_DSL_COST_RUN is not None:
        globals()["dsl_cost_run"] = _PACKAGE_ROOT_DSL_COST_RUN
    return DslRunResult, dsl_run_func, dsl_cost_run_func


def dsl_run(
    func_obj: Callable[..., DslFunctionReturn],
    real_args: tuple[RuntimeRealArg, ...] | list[RuntimeRealArg],
    pipeline: str | "PassManager",
) -> "DslRunResult":
    """通过 `kernel_gen.tools` 包根转发 `dsl_run(...)` 公开入口。


    功能说明:
    - 为 `kernel_gen.tools` 包根提供稳定的 `dsl_run(...)` 公开函数。
    - 运行时按需加载 [`kernel_gen.tools.dsl_run`](dsl_run.py) 中的真实实现，避免包导入时直接拉起整条 lowering 链。
    - 诊断产物根目录统一由 `kernel_gen.core.config.set_dump_dir(...)` 配置。

    使用示例:
    - import kernel_gen.tools as tools
    - result = tools.dsl_run(add_kernel, (out, lhs, rhs), "npu-demo-lowering")

    关联文件:
    - spec: [spec/tools/dsl_run.md](spec/tools/dsl_run.md)
    - test: [test/tools/test_package.py](test/tools/test_package.py)
    - 功能实现: [kernel_gen/tools/__init__.py](.)
    """

    _, dsl_run_func, _ = _load_dsl_run_exports()
    return dsl_run_func(func_obj, real_args, pipeline)


_PACKAGE_ROOT_DSL_RUN = dsl_run


def dsl_cost_run(
    func_obj: Callable[..., DslFunctionReturn],
    real_args: tuple[RuntimeRealArg, ...] | list[RuntimeRealArg],
    pipeline: str | "PassManager",
    cost_kind: str,
) -> int:
    """通过 `kernel_gen.tools` 包根转发 `dsl_cost_run(...)` 公开入口。


    功能说明:
    - 为 `kernel_gen.tools` 包根提供稳定的 `dsl_cost_run(...)` 公开函数。
    - 运行时按需加载 [`kernel_gen.tools.dsl_run`](dsl_run.py) 中的真实实现，避免包导入时直接拉起整条 lowering 链。
    - `cost_kind` 必须由调用方显式提供，不在包根添加默认值。

    使用示例:
    - import kernel_gen.tools as tools
    - cost = tools.dsl_cost_run(add_kernel, (out, lhs, rhs), "npu-demo-lowering", "VECTOR1")

    关联文件:
    - spec: [spec/tools/dsl_run.md](spec/tools/dsl_run.md)
    - test: [test/tools/test_package.py](test_package_api.py)
    - 功能实现: [kernel_gen/tools/__init__.py](.)
    """

    _, _, dsl_cost_run_func = _load_dsl_run_exports()
    return dsl_cost_run_func(func_obj, real_args, pipeline, cost_kind)


_PACKAGE_ROOT_DSL_COST_RUN = dsl_cost_run


def __getattr__(name: str) -> type["DslRunResult"]:
    """按需加载 `dsl_run` 公开入口，避免导入无关工具时触发整条 lowering 链。


    功能说明:
    - 仅在调用方真正访问 `DslRunResult` 时导入 [`kernel_gen.tools.dsl_run`](dsl_run.py)。
    - 避免 `emitc_case_runner` 这类轻量 helper 在导入 `kernel_gen.tools.*` 时被 pass/pipeline 侧副作用拖起。

    使用示例:
    - from kernel_gen.tools import DslRunResult

    关联文件:
    - spec: [spec/tools/dsl_run.md](spec/tools/dsl_run.md)
    - test: [test/tools/test_dsl_run.py](test/tools/test_dsl_run.py)
    - 功能实现: [kernel_gen/tools/__init__.py](.)
    """

    if name == "DslRunResult":
        dsl_run_result, _, _ = _load_dsl_run_exports()
        return dsl_run_result
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
