"""tools package.

创建者: 小李飞刀
最后一次更改: 小李飞刀

功能说明:
- 暴露面向脚本与测试的轻量工具模块（例如 ircheck）。
- 暴露 `dsl_run` 的公开入口，供 expectation 与测试直接复用。

使用示例:
- from kernel_gen.tools.ircheck import run_ircheck_text
- from kernel_gen.tools import dsl_run
- result = run_ircheck_text(\"\"\"// COMPILE_ARGS: --pass no-op
// CHECK: builtin.module

builtin.module {}
\"\"\")
- assert result.ok is True
- result = dsl_run(add_kernel, (out, lhs, rhs), "default-lowering", EmitCContext(target="npu_demo"))

关联文件:
- spec: [spec/tools/ircheck.md](spec/tools/ircheck.md)
- test: [test/tools/test_ircheck_runner.py](test/tools/test_ircheck_runner.py)
- 功能实现: [kernel_gen/tools/ircheck.py](kernel_gen/tools/ircheck.py)
- spec: [spec/tools/dsl_run.md](spec/tools/dsl_run.md)
- test: [test/tools/test_dsl_run.py](test/tools/test_dsl_run.py)
- 功能实现: [kernel_gen/tools/dsl_run.py](kernel_gen/tools/dsl_run.py)
"""

from .dsl_run import DslRunError, DslRunResult, dsl_run

__all__ = [
    "DslRunError",
    "DslRunResult",
    "dsl_run",
]
