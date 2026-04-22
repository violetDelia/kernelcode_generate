"""tools package.

创建者: 小李飞刀
最后一次更改: 小李飞刀

- 暴露面向脚本与测试的轻量工具模块（例如 ircheck）。
- 暴露 `dsl_run` 的公开入口，供产品测试直接复用。
- 暴露 `case_runner` 的公开入口，供 case 化测试与工具汇总复用。

使用示例:
- from kernel_gen.tools.ircheck import run_ircheck_text
- from kernel_gen.tools import dsl_run
- from kernel_gen.tools.case_runner import run_case, raise_if_failures
- result = run_ircheck_text(\"\"\"// COMPILE_ARGS: --pass no-op
// CHECK: builtin.module

builtin.module {}
\"\"\")
- assert result.ok is True
- result = dsl_run(add_kernel, (out, lhs, rhs), "npu-demo-lowering", EmitCContext(target="npu_demo"))
- failures: list[tuple[str, BaseException]] = []
- run_case(failures, "CASE-1", lambda: None)
- raise_if_failures("tile reduce example", failures)

关联文件:
- spec: [spec/tools/ircheck.md](spec/tools/ircheck.md)
- test: [test/tools/test_ircheck_runner.py](test/tools/test_ircheck_runner.py)
- 功能实现: [kernel_gen/tools/ircheck.py](kernel_gen/tools/ircheck.py)
- spec: [spec/tools/dsl_run.md](spec/tools/dsl_run.md)
- test: [test/tools/test_dsl_run.py](test/tools/test_dsl_run.py)
- 功能实现: [kernel_gen/tools/dsl_run.py](kernel_gen/tools/dsl_run.py)
- spec: [spec/tools/case_runner.md](spec/tools/case_runner.md)
- test: [test/tools/test_case_runner.py](test/tools/test_case_runner.py)
- 功能实现: [kernel_gen/tools/case_runner.py](kernel_gen/tools/case_runner.py)
"""

from .dsl_run import DslRunError, DslRunResult, dsl_run
from .case_runner import raise_if_failures, run_case

__all__ = [
    "DslRunError",
    "DslRunResult",
    "dsl_run",
    "raise_if_failures",
    "run_case",
]
