"""tools package.

创建者: 小李飞刀
最后一次更改: 小李飞刀

- 暴露面向脚本与测试的轻量工具模块（例如 ircheck）。
- 惰性暴露 `dsl_run` 的公开入口，供产品测试直接复用。

使用示例:
- from kernel_gen.tools.ircheck import run_ircheck_text
- from kernel_gen.tools import dsl_run
- result = run_ircheck_text(\"\"\"// COMPILE_ARGS: --pass no-op
// CHECK: builtin.module

builtin.module {}
\"\"\")
- assert result.ok is True
- result = dsl_run(add_kernel, (out, lhs, rhs), "npu-demo-lowering", EmitCContext(target="npu_demo"))

关联文件:
- spec: [spec/tools/ircheck.md](spec/tools/ircheck.md)
- test: [test/tools/test_ircheck_runner.py](test/tools/test_ircheck_runner.py)
- 功能实现: [kernel_gen/tools/ircheck.py](kernel_gen/tools/ircheck.py)
- spec: [spec/tools/dsl_run.md](spec/tools/dsl_run.md)
- test: [test/tools/test_dsl_run.py](test/tools/test_dsl_run.py)
- 功能实现: [kernel_gen/tools/dsl_run.py](kernel_gen/tools/dsl_run.py)
"""

from __future__ import annotations

__all__ = ["DslRunError", "DslRunResult", "dsl_run"]


def __getattr__(name: str) -> object:
    """按需加载 `dsl_run` 公开入口，避免导入无关工具时触发整条 lowering 链。

    创建者: OpenAI Codex
    最后一次更改: OpenAI Codex

    功能说明:
    - 仅在调用方真正访问 `dsl_run` 相关公开名时导入 [`kernel_gen.tools.dsl_run`](dsl_run.py)。
    - 避免 `emitc_case_runner` 这类轻量 helper 在导入 `kernel_gen.tools.*` 时被 pass/pipeline 侧副作用拖起。

    使用示例:
    - from kernel_gen.tools import dsl_run
    - result = dsl_run(...)

    关联文件:
    - spec: [spec/tools/dsl_run.md](spec/tools/dsl_run.md)
    - test: [test/tools/test_dsl_run.py](test/tools/test_dsl_run.py)
    - 功能实现: [kernel_gen/tools/__init__.py](.)
    """

    if name in __all__:
        from .dsl_run import DslRunError, DslRunResult, dsl_run

        return {
            "DslRunError": DslRunError,
            "DslRunResult": DslRunResult,
            "dsl_run": dsl_run,
        }[name]
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
