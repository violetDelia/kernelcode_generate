"""tools package.

创建者: 小李飞刀
最后一次更改: 大闸蟹

- 暴露面向脚本与测试的轻量工具模块（例如 ircheck）。
- 包根惰性暴露 `DslRunResult` 公开类型，以及稳定的 `dsl_run(...)` 公开函数入口。

API 列表:
- `DslRunResult(func_op: func.FuncOp, module: ModuleOp, source: str, compiled_kernel: CompiledKernel, execute_result: ExecuteResult, runtime_args: tuple[object, ...])`
- `dsl_run(func_obj: object, real_args: tuple[object, ...] | list[object], pipeline: str | PassManager) -> DslRunResult`

helper 清单:
- `_load_dsl_run_exports() -> tuple[type[object], object]`
- `__getattr__(name: str) -> object`

使用示例:
- from kernel_gen.tools.ircheck import run_ircheck_text
- import kernel_gen.tools as tools
- result = run_ircheck_text(\"\"\"// COMPILE_ARGS: --pass no-op
// CHECK: builtin.module

builtin.module {}
\"\"\")
- assert result.ok is True
- result = tools.dsl_run(add_kernel, (out, lhs, rhs), "npu-demo-lowering")

关联文件:
- spec: [spec/tools/ircheck.md](spec/tools/ircheck.md)
- test: [test/tools/test_ircheck_runner.py](test/tools/test_ircheck_runner.py)
- 功能实现: [kernel_gen/tools/ircheck.py](kernel_gen/tools/ircheck.py)
- spec: [spec/tools/dsl_run.md](spec/tools/dsl_run.md)
- test: [test/tools/test_dsl_run.py](test/tools/test_dsl_run.py)
- 功能实现: [kernel_gen/tools/dsl_run.py](kernel_gen/tools/dsl_run.py)
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from kernel_gen.passes.pass_manager import PassManager
    from .dsl_run import DslRunResult

__all__ = ["DslRunResult"]
_PACKAGE_ROOT_DSL_RUN: object | None = None


def _load_dsl_run_exports() -> tuple[type[object], object]:
    """加载 `dsl_run` 公开导出对象。

    创建者: 金铲铲大作战
    最后一次更改: 金铲铲大作战

    功能说明:
    - 集中导入 `kernel_gen.tools.dsl_run` 模块中的稳定公开名。
    - 供包根 `DslRunResult` 惰性导出与 `dsl_run(...)` 包装函数共用，避免重复写导入语句。
    - 每次子模块导入后都会把包根 `dsl_run` 重新绑定回公开函数，消除同名子模块覆盖带来的导入顺序差异。

    使用示例:
    - dsl_run_result, dsl_run_func = _load_dsl_run_exports()

    关联文件:
    - spec: [spec/tools/dsl_run.md](spec/tools/dsl_run.md)
    - test: [test/tools/test_package_api.py](test_package_api.py)
    - 功能实现: [kernel_gen/tools/__init__.py](.)
    """

    from .dsl_run import DslRunResult, dsl_run as dsl_run_func

    if _PACKAGE_ROOT_DSL_RUN is not None:
        globals()["dsl_run"] = _PACKAGE_ROOT_DSL_RUN
    return DslRunResult, dsl_run_func


def dsl_run(
    func_obj: object,
    real_args: tuple[object, ...] | list[object],
    pipeline: str | "PassManager",
) -> "DslRunResult":
    """通过 `kernel_gen.tools` 包根转发 `dsl_run(...)` 公开入口。

    创建者: OpenAI Codex
    最后一次更改: 大闸蟹

    功能说明:
    - 为 `kernel_gen.tools` 包根提供稳定的 `dsl_run(...)` 公开函数。
    - 运行时按需加载 [`kernel_gen.tools.dsl_run`](dsl_run.py) 中的真实实现，避免包导入时直接拉起整条 lowering 链。
    - 诊断产物根目录统一由 `kernel_gen.core.config.set_dump_dir(...)` 配置。

    使用示例:
    - import kernel_gen.tools as tools
    - result = tools.dsl_run(add_kernel, (out, lhs, rhs), "npu-demo-lowering")

    关联文件:
    - spec: [spec/tools/dsl_run.md](spec/tools/dsl_run.md)
    - test: [test/tools/test_package_api.py](test_package_api.py)
    - 功能实现: [kernel_gen/tools/__init__.py](.)
    """

    _, dsl_run_func = _load_dsl_run_exports()
    return dsl_run_func(func_obj, real_args, pipeline)


_PACKAGE_ROOT_DSL_RUN = dsl_run


def __getattr__(name: str) -> object:
    """按需加载 `dsl_run` 公开入口，避免导入无关工具时触发整条 lowering 链。

    创建者: OpenAI Codex
    最后一次更改: OpenAI Codex

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
        dsl_run_result, _ = _load_dsl_run_exports()
        return dsl_run_result
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
